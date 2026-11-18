from __future__ import annotations

from dataclasses import asdict
from typing import Any

import streamlit as st

from agents.assessment.agent import AssessmentAgent
from agents.execution.agent import ExecutionAgent
from agents.execution.window_guard import build_window_input
from apps.console.components.compliance_icon import (
    render_safety_icon,
    render_window_icon,
)
from apps.console.components.metric_card import buffer_color, render_metric_card
from apps.console.components.stage_badge import badge_label, render_badge_html
from apps.console.components.stage_progress import render_stage_progress
from apps.console.services.runtime_state import set_stage
from apps.console.theme import (
    BLOCKED_BUTTON_HELP,
    NOT_APPROVED_HINT,
    ROW_BLOCKED_BG,
    ROW_DEGRADED_BG,
)
from domain.models.enums import label_of
from domain.rules.work_window import evaluate_work_window
from mock.loader import plot_bundle
from mock.services.recheck_stub import build_recheck
from mock.services.weather_stub import get_forecast
from workflows.local.pipeline import build_demo_feedback

STATE_SELECTED_PLOT = "cipm_selected_plot_no"
STATE_DISPATCH = "cipm_dispatch_feedback"

TABLE_COLUMNS = ["地块", "农场", "面积(亩)", "四阶段进度", "业务标识", "更新时间"]


def render_plot_table(plots: list[dict]) -> None:
    header = (
        '<table class="cipm-table"><thead><tr>'
        '<th>地块</th><th>农场</th><th>面积(亩)</th>'
        '<th>四阶段进度</th><th>业务标识</th><th>更新时间</th>'
        '</tr></thead><tbody>'
    )
    rows_html = []
    for plot in plots:
        stages = plot.get("stages") or {}
        badges = plot.get("badges") or []
        row_class = ""
        if "BLOCKED" in badges:
            row_class = "row-blocked"
        elif "DEGRADED" in badges:
            row_class = "row-degraded"

        progress_html = render_stage_progress(stages)
        badge_html = (
            "".join(render_badge_html(code) for code in badges)
            if badges
            else '<span style="color:#9E9E9E;font-size:11px">无</span>'
        )

        rows_html.append(
            f'<tr class="{row_class}">'
            f'<td><strong>{plot.get("plotNo", "")}</strong><br><span style="font-size:11px;color:#757575">{plot.get("plotName", "")}</span></td>'
            f'<td>{plot.get("farmName") or plot.get("farmNo") or ""}</td>'
            f'<td>{plot.get("areaMu", 0)}</td>'
            f'<td>{progress_html}</td>'
            f'<td>{badge_html}</td>'
            f'<td style="font-size:11px;color:#757575">{plot.get("updatedAt", "")}</td>'
            f'</tr>'
        )
    footer = '</tbody></table>'
    st.markdown(header + "".join(rows_html) + footer, unsafe_allow_html=True)


def render_action_entries(plots: list[dict]) -> None:
    for plot in plots:
        plot_no = plot.get("plotNo", "")
        stages = plot.get("stages") or {}
        badges = plot.get("badges") or []
        blocked = "BLOCKED" in badges
        approved = stages.get("prescription") == "已通过"

        cols = st.columns([4, 1, 1])
        cols[0].markdown(f"**{plot_no}** {plot.get('plotName', '')}")

        if cols[1].button(
            "查看处方",
            key=f"view_prescription_{plot_no}",
            disabled=blocked,
            help=BLOCKED_BUTTON_HELP if blocked else "查看处方三元组与合规校验结论",
        ):
            st.session_state[STATE_SELECTED_PLOT] = plot_no
            st.session_state.pop(STATE_DISPATCH, None)
            st.rerun()

        if approved:
            if cols[2].button(
                "下发作业",
                key=f"dispatch_{plot_no}",
                help="处方已通过审核，可进入执行前作业窗口校验",
            ):
                bundle = plot_bundle(plot_no)
                outcome = ExecutionAgent().dispatch(plot_no, bundle.get("prescription"))
                st.session_state[STATE_SELECTED_PLOT] = plot_no
                st.session_state[STATE_DISPATCH] = {
                    "plotNo": plot_no,
                    "outcome": asdict(outcome),
                }
                from domain.models.enums import WorkOrderStatus
                from domain.state_machines.work_order import can_transition as work_order_can_transition

                if outcome.status == "dispatched":
                    if not work_order_can_transition(
                        WorkOrderStatus.PENDING_DISPATCH, WorkOrderStatus.DISPATCHED
                    ):
                        st.error("作业单状态迁移被拦截：pending_dispatch → dispatched")
                    else:
                        set_stage(plot_no, "execution", "已下发")
                        feedback = build_demo_feedback(bundle)
                        feedback["workOrderNo"] = outcome.work_order_no
                        assessment = AssessmentAgent().assess(
                            plot_no,
                            bundle["stressResult"],
                            build_recheck(bundle["stressResult"]),
                            feedback,
                            bundle["prescription"],
                        )
                        set_stage(plot_no, "assessment", "达标" if assessment.qualified else "未达标")
                elif outcome.status == "rescheduled":
                    if not work_order_can_transition(
                        WorkOrderStatus.PENDING_DISPATCH, WorkOrderStatus.RESCHEDULED
                    ):
                        st.error("作业单状态迁移被拦截：pending_dispatch → rescheduled")
                    else:
                        set_stage(plot_no, "execution", "待重新排期")
                else:
                    set_stage(plot_no, "execution", "不可下发")
                st.rerun()
        else:
            cols[2].caption(NOT_APPROVED_HINT)


def evaluate_dispatch_window(bundle: dict[str, Any]):
    weather = get_forecast(bundle["plot"]["plotNo"])
    return evaluate_work_window(
        build_window_input(weather, bundle["plot"].get("region", "south"))
    )


def render_action_feedback() -> None:
    plot_no = st.session_state.get(STATE_SELECTED_PLOT)
    if not plot_no:
        return
    try:
        bundle = plot_bundle(plot_no)
    except KeyError:
        st.warning(f"未找到地块 {plot_no} 的演示数据。")
        return

    render_prescription_detail(bundle)

    feedback = st.session_state.get(STATE_DISPATCH)
    if feedback and feedback.get("plotNo") == plot_no:
        render_dispatch_feedback(feedback)


def render_prescription_detail(bundle: dict[str, Any]) -> None:
    plot = bundle["plot"]
    calendar = bundle["calendar"]
    stress = bundle.get("stressResult")
    prescription = bundle.get("prescription")
    plot_no = plot["plotNo"]

    if prescription is None:
        status = (stress or {}).get("taskBlock", {}).get("status")
        with st.expander(f"处方详情 · {plot_no} {plot.get('plotName', '')}", expanded=True):
            if status == "blocked_pending_review":
                blocking = (stress or {}).get("taskBlock", {}).get("blockingPartitions") or []
                st.warning(
                    "识别结果待人工复核，处方生成已暂停。"
                    + (f"待复核分区：{'、'.join(blocking)}" if blocking else "")
                )
            else:
                st.info("该地块暂无处方数据，暂不可查看。")
        return

    safety = prescription["safetyCheck"]
    window = prescription["windowCheck"]
    snapshot = prescription["registrySnapshot"]
    active_zones = [zone for zone in prescription["zones"] if not zone.get("zeroApplication")]
    first_zone = active_zones[0] if active_zones else None
    product = first_zone.get("product") if first_zone else None

    with st.expander(f"处方详情 · {plot_no} {plot.get('plotName', '')}", expanded=True):
        cols = st.columns(4)
        with cols[0]:
            render_metric_card("处方状态", label_of(prescription["status"]), "📋")
        with cols[1]:
            render_metric_card("剩余采收天数 R", safety["remainingDays"], "📅")
        with cols[2]:
            render_metric_card("安全间隔期 S", safety["safetyIntervalDays"], "🛡️")
        with cols[3]:
            b_color = buffer_color(safety["bufferDays"])
            render_metric_card(
                "buffer（R−S）", safety["bufferDays"], "⚠️",
                color_override=b_color,
            )

        if product:
            triple_cols = st.columns(3)
            triple_cols[0].markdown(
                f"**药剂品类**\n\n{product['category']['aiName']}·{product['category']['formulation']}"
            )
            triple_cols[1].markdown(f"**制剂亩用量**\n\n{first_zone['doseMlPerMu']} 毫升/亩")
            volume = (
                f"{first_zone['sprayVolumeLPerMu']} 升/亩"
                if first_zone.get("sprayVolumeLPerMu")
                else "—"
            )
            dilution = (
                f"{first_zone['dilutionRatio']} 倍液"
                if first_zone.get("dilutionRatio")
                else "—"
            )
            triple_cols[2].markdown(f"**喷液量 / 稀释浓度**\n\n{volume} / {dilution}")
            st.markdown(
                f"**登记用药目录项**：{product['registryItemNo']}（登记证号 {product.get('registrationNo', '—')}）　"
                f"**目录版本**：{snapshot['version']}"
            )
        else:
            st.info("当前处方为全零施药，未绑定药剂。")

        safety_cols = st.columns(2)
        with safety_cols[0]:
            st.markdown("**安全间隔结论**")
            render_safety_icon(safety["conclusion"])
        with safety_cols[1]:
            st.markdown("**作业窗口校验**")
            render_window_icon(window["conclusion"])
            st.caption(f"（{window['checkNo']}，阈值版本 {window['thresholdVersion']}）")

        st.caption(
            f"农事日历：物候期 {label_of(calendar.get('phenology', ''))}，"
            f"预计采收 {calendar.get('expectedHarvestDate', '未知')}"
        )

        if safety["conclusion"] == "refused":
            conflict = safety.get("conflictProduct") or {}
            category = conflict.get("category") or {}
            st.error(
                f"安全间隔校验拒绝：距采收 {safety['remainingDays']} 天，安全间隔期 "
                f"{safety['safetyIntervalDays']} 天，冲突药剂 "
                f"{category.get('aiName', '—')}·{category.get('formulation', '—')}"
            )
            alternatives = safety.get("alternatives") or []
            if alternatives:
                labels = [
                    f"{item['category']['aiName']}·{item['category']['formulation']}"
                    f"（安全间隔 {item['safetyIntervalDays']} 天）"
                    for item in alternatives
                ]
                st.caption("可选替代（仅供重新发起处方）：" + "、".join(labels))
        elif safety["conclusion"] == "degraded":
            reasons = "、".join(label_of(str(item)) for item in safety.get("degradeReasons") or [])
            st.warning(f"安全间隔校验降级：{reasons or '缓冲不足'}，需农技专家确认后方可进入审核。")

        zone_rows = []
        for zone in prescription["zones"]:
            zone_product = zone.get("product")
            zone_rows.append(
                {
                    "分区": zone["zoneNo"],
                    "药剂品类": (
                        f"{zone_product['category']['aiName']}·{zone_product['category']['formulation']}"
                        if zone_product
                        else "零施药"
                    ),
                    "制剂亩用量(毫升/亩)": zone["doseMlPerMu"],
                    "喷液量(升/亩)": zone.get("sprayVolumeLPerMu") or 0,
                    "稀释浓度(倍液)": zone.get("dilutionRatio") or 0,
                    "安全间隔期(天)": zone.get("safetyIntervalDays") or 0,
                }
            )
        st.dataframe(zone_rows, width="stretch", hide_index=True)


def render_dispatch_feedback(feedback: dict[str, Any]) -> None:
    plot_no = feedback["plotNo"]
    outcome = feedback["outcome"]
    with st.expander(f"下发前作业窗口校验 · {plot_no}", expanded=True):
        if outcome["status"] == "dispatched":
            st.success(outcome["message"])
        else:
            st.error(outcome["message"])
            for item in outcome.get("violations") or []:
                st.markdown(f"- {item}")
            if outcome["status"] == "rescheduled":
                st.caption("作业单状态：待重新排期（未下发）")
            else:
                st.caption("作业单状态：不可下发")
        for notice in outcome.get("notices") or []:
            st.warning(notice)
        st.caption(
            f"校验口径：逐日最低气温 ≥ 12.5℃、日均温 > 23℃、逐时风速 ≤ 3 级；"
            f"数据不可用按不通过处理。"
        )