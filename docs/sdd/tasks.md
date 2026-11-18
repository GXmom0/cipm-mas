# 棉田植保决策多智能体系统 仪表盘 UI 优化编码任务规划

- 功能标识：`cotton_ipm_mas` — UI 优化
- 依据文档：`ui_optimization_spec.md`（需求规格）、`ui_optimization_design.md`（实现方案）
- 文档作用：将 UI 优化技术设计转化为可逐条编码、可逐条验收的工作项

**编号与复杂度规则**

- 任务组按 Phase 编号 `P1—P6`；子任务编号为 `P{Phase}.{序号}`（如 `P1.3`）。
- 复杂度：`简单`（≤1 人日）、`中等`（2—4 人日）、`复杂`（5—8 人日）。
- 所有颜色值必须引用 `theme.py` 常量，禁止在组件文件中硬编码 hex 颜色值。
- 禁止引入需要本地回环套接字的组件（如 Streamlit AgGrid）。
- 禁止修改业务逻辑，所有交互必须产生真实业务反馈。

---

## Phase 1：主题基础设施

**任务组目标**：建立主题配置文件、扩展主题常量、实现 CSS 注入机制，为后续所有组件提供统一的视觉基础。
**任务组依赖**：无。
**任务组验收**：页面加载后整体配色统一（主色绿色系），自定义 CSS 注入不阻塞渲染，所有后续组件可引用 theme.py 常量。

### P1.1 新建 `.streamlit/config.toml` 主题配置文件（复杂度：简单）

- **文件路径**：`.streamlit/config.toml`
- **修改内容**：新建文件，定义 Streamlit 主题配置：
  - `primaryColor = "#2E7D32"`（Material Green 800，绿色系主色）
  - `backgroundColor = "#FAFAFA"`（浅灰背景）
  - `secondaryBackgroundColor = "#E8F5E9"`（浅绿辅助背景）
  - `textColor = "#212121"`（深灰文字，对比度 ≥ 4.5:1）
  - `font = "sans serif"`（兼容中文字体）
  - `[server] maxUploadSize = 10`
- **验收条件**：页面加载后不再使用 Streamlit 默认粉色主题；主色为绿色系；文字与背景对比度 ≥ 4.5:1
- **依赖**：无

### P1.2 扩展 `apps/console/theme.py` 常量定义（复杂度：简单）

- **文件路径**：`apps/console/theme.py`
- **修改内容**：在现有 `BADGE_COLORS`、`BADGE_LABELS`、`COLUMNS`、`PAGE_TITLE` 等常量之后追加以下新增常量：
  - 进度条节点颜色：`NODE_DONE_COLOR="#4CAF50"`、`NODE_ACTIVE_COLOR="#1976D2"`、`NODE_BLOCKED_COLOR="#D32F2F"`、`NODE_PENDING_COLOR="#9E9E9E"`
  - 行高亮颜色：`ROW_BLOCKED_BG="#FFEBEE"`、`ROW_DEGRADED_BG="#FFF3E0"`
  - 卡片样式：`CARD_BORDER_RADIUS="8px"`、`CARD_PADDING="16px"`、`CARD_BOX_SHADOW="0 2px 4px rgba(0,0,0,0.1)"`、`CARD_MARGIN_BOTTOM="16px"`
  - 间距规范：`SECTION_GAP="24px"`、`CARD_GAP="16px"`
  - 状态色独立命名：`STATUS_BLOCKED="#D32F2F"`、`STATUS_DEGRADED="#F57C00"`、`STATUS_REFUSED="#B71C1C"`、`STATUS_RESCHEDULED="#1976D2"`
  - 批次队列状态色映射：`BATCH_STATE_COLORS`（6种状态色）、`BATCH_STATE_LABELS`（6种中文标签）
  - 紧迫度热力色阶：`URGENCY_HEAT_LOW="#FFF9C4"`、`URGENCY_HEAT_HIGH="#D32F2F"`
  - 待办优先级色：`PRIORITY_HIGH_COLOR="#D32F2F"`、`PRIORITY_MEDIUM_COLOR="#F57C00"`、`PRIORITY_LOW_COLOR="#1976D2"`
  - 安全间隔 buffer 色：`BUFFER_DANGER_COLOR="#D32F2F"`、`BUFFER_WARNING_COLOR="#F57C00"`、`BUFFER_SAFE_COLOR="#4CAF50"`
  - 分区名称：`TAB_OVERVIEW="总览"`、`TAB_PRESCRIPTION="处方与作业"`、`TAB_TODO_BATCH="待办与批次"`、`TAB_ALERT="异常与告警"`、`TAB_SETTINGS="设置"`
- **验收条件**：所有新增常量可被 `from apps.console.theme import *` 导入；不修改现有常量值；与 `BADGE_COLORS` 中相同语义的颜色值一致
- **依赖**：无

### P1.3 新建 `apps/console/components/css_inject.py` CSS 样式注入组件（复杂度：中等）

- **文件路径**：`apps/console/components/css_inject.py`
- **修改内容**：新建文件，实现 `inject_custom_css() -> None` 函数，通过 `st.markdown(unsafe_allow_html=True)` 注入以下 CSS 样式：
  - **卡片样式**：`stContainer[data-testid="stVerticalBlockBorderWrapper"]` 增加圆角 `border-radius: 8px`、阴影 `box-shadow: 0 2px 4px rgba(0,0,0,0.1)`、内边距 `padding: 16px`
  - **进度条样式**：`.stage-progress-container`（flex 水平布局）、`.stage-node`（圆形节点 40px 直径）、`.stage-node.node-done`（绿色背景）、`.stage-node.node-active`（蓝色背景）、`.stage-node.node-blocked`（红色背景）、`.stage-node.node-pending`（灰色背景）、`.stage-connector`（节点间连接线 4px 高度）、`.stage-label`（节点下方文字标签）
  - **紧迫度热力标识样式**：`.urgency-cell`（表格单元格背景色渐变）
  - **Badge 胶囊样式增强**：`.badge-pill`（`padding: 4px 12px; border-radius: 16px; font-size: 11px; box-shadow: 0 1px 2px rgba(0,0,0,0.08); font-weight: 500`）
  - **表格行高亮样式**：`.row-blocked`（`background-color: #FFEBEE`）、`.row-degraded`（`background-color: #FFF3E0`）
  - **折叠面板样式增强**：Streamlit `st.expander` 默认样式增强（圆角、阴影）
- **验收条件**：`inject_custom_css()` 在 `st.set_page_config` 之后调用不抛异常；注入的 CSS 包含卡片、进度条、badge 等关键样式类；CSS 注入不阻塞 Streamlit 主线程渲染
- **依赖**：P1.2（引用 theme.py 中的颜色常量）

---

## Phase 2：可视化组件

**任务组目标**：新建 4 个独立可视化组件（指标卡片、四阶段进度条、胁迫等级图表、合规校验图标），不依赖现有组件改造。
**任务组依赖**：P1（主题基础设施）。
**任务组验收**：4 个组件均可独立渲染，颜色引用 theme.py 常量，不引入需要额外端口的图表库。

### P2.1 新建 `apps/console/components/metric_card.py` 指标卡片组件（复杂度：中等）

- **文件路径**：`apps/console/components/metric_card.py`
- **修改内容**：新建文件，实现两个函数：
  - `render_metric_card(label, value, icon, trend="", description="", color_override="") -> None`：渲染单张指标卡片，使用 `st.container(border=True)` 包裹，内部 `st.columns([1, 3])` 分为图标列和内容列；图标列渲染 emoji；内容列渲染指标名称（caption 样式）、数值（大字号 markdown）、说明文字；`color_override` 参数用于 buffer 卡片变色
  - `render_metric_cards_row(plots_count, todos_count, alerts_count, batches_count) -> None`：使用 `st.columns(4)` 横向排列 4 张卡片（🌾 地块总数、📋 待办总数、⚠️ 异常总数、📦 批次总数）
- **验收条件**：4 张指标卡片横向排列，每张卡片有图标、数值与简短说明；`color_override` 参数可控制卡片强调色（buffer < 0 红色、0-3 橙色、≥ 3 绿色）
- **依赖**：P1.2（引用 BUFFER_DANGER_COLOR 等常量）、P1.3（依赖 CSS 注入）

### P2.2 新建 `apps/console/components/stage_progress.py` 四阶段进度条组件（复杂度：中等）

- **文件路径**：`apps/console/components/stage_progress.py`
- **修改内容**：新建文件，实现以下内容：
  - 常量：`STAGE_ORDER=("patrol", "prescription", "execution", "assessment")`、`STAGE_LABELS`（中文标签映射）、`NODE_COLOR_MAP`（状态值 → CSS 颜色类映射，覆盖所有可能的状态值）
  - `classify_stage_status(status: str) -> str`：将阶段状态文字分类为颜色类别（`node-done`/`node-active`/`node-blocked`/`node-pending`），未知状态回退到 `node-pending`
  - `render_stage_progress(stages: dict[str, str]) -> str`：返回 HTML 字符串，包含 4 个圆形节点和 3 条连接线，节点颜色通过 CSS class 控制，节点下方显示阶段名称标签
- **验收条件**：`classify_stage_status("已完成")` 返回 `"node-done"`；`classify_stage_status("已阻断")` 返回 `"node-blocked"`；`render_stage_progress` 返回包含 4 个节点的 HTML 字符串；未知状态映射为 `node-pending`
- **依赖**：P1.2（引用 NODE_DONE_COLOR 等常量）、P1.3（依赖进度条 CSS 样式）

### P2.3 新建 `apps/console/components/stress_chart.py` 胁迫等级分布图表组件（复杂度：中等）

- **文件路径**：`apps/console/components/stress_chart.py`
- **修改内容**：新建文件，实现以下内容：
  - 常量：`STRESS_LEVELS=("无", "轻度", "中度", "重度")`、`STRESS_COLORS`（各等级对应颜色，引用 theme.py 常量）
  - `build_stress_data(plots: list[dict]) -> dict[str, int]`：统计各胁迫等级的地块数量
  - `render_stress_chart(plots: list[dict]) -> None`：使用 `plotly.graph_objects.Bar` 创建柱状图，X 轴为胁迫等级、Y 轴为地块数量、每个柱子颜色对应 `STRESS_COLORS`，通过 `st.plotly_chart(fig, use_container_width=True)` 渲染；所有地块胁迫等级为"无"时正常渲染单色柱并添加注释文字"全部地块无胁迫"
- **验收条件**：图表展示各胁迫等级的地块数量，颜色区分等级；全部地块无胁迫时图表正常渲染并标注说明文字；使用 `st.plotly_chart` 而非需要额外端口的组件
- **依赖**：P1.2（引用颜色常量）

### P2.4 新建 `apps/console/components/compliance_icon.py` 合规校验图标组件（复杂度：简单）

- **文件路径**：`apps/console/components/compliance_icon.py`
- **修改内容**：新建文件，实现以下内容：
  - 常量：`SAFETY_ICON_MAP`（`satisfied` → ✅ 绿色、`degraded` → ⚠️ 橙色、`refused` → ❌ 红色）、`WINDOW_ICON_MAP`（`pass` → ✅ 绿色、`pass_with_mandatory_notice` → ⚠️ 橙色、`fail` → ❌ 红色）
  - `render_safety_icon(conclusion: str) -> None`：使用 `st.markdown` 渲染 emoji 图标 + 文字，颜色通过 inline style 设置（引用 theme.py 常量）
  - `render_window_icon(conclusion: str) -> None`：同上，用于作业窗口校验结论
- **验收条件**：`satisfied` 结论渲染绿色勾号；`degraded` 结论渲染橙色感叹号；`pass_with_mandatory_notice` 渲染橙色感叹号；图标和文字使用 `<span>` 标签包裹
- **依赖**：P1.2（引用 STATUS_BLOCKED 等常量）

---

## Phase 3：交互组件

**任务组目标**：新建地块筛选器和异常告警卡片两个交互组件。
**任务组依赖**：P1（主题基础设施）。
**任务组验收**：筛选器支持搜索+阶段筛选+标识筛选，状态在 session_state 中保持；告警卡片按严重程度分色展示。

### P3.1 新建 `apps/console/components/plot_filter.py` 地块筛选器组件（复杂度：中等）

- **文件路径**：`apps/console/components/plot_filter.py`
- **修改内容**：新建文件，实现以下函数：
  - `FILTER_STATE_KEY = "cipm_filter_state_v1"`
  - `get_filter_state() -> dict`：从 session_state 获取筛选状态 `{"search": str, "stage_filter": list[str], "badge_filter": list[str]}`
  - `set_filter_state(search, stage_filter, badge_filter) -> None`：写入 session_state
  - `clear_filter_state() -> None`：清除筛选状态
  - `filter_plots(plots, search, stage_filter, badge_filter) -> list[dict]`：搜索匹配 plotNo/plotName 模糊匹配；阶段筛选检查 stages 值是否在筛选集合中；标识筛选检查 badges 是否包含筛选值
  - `render_plot_filter(plots: list[dict]) -> list[dict]`：使用 `st.columns([2, 1, 1])` 布局 3 个控件（搜索框 `st.text_input`、阶段筛选 `st.multiselect`、标识筛选 `st.multiselect`），所有控件使用 `key` 参数绑定 session_state 自动保持状态，返回过滤后的地块列表
- **验收条件**：搜索框按地块编号模糊匹配；阶段筛选下拉框过滤匹配地块；标识筛选下拉框过滤匹配地块；筛选状态在 session_state 中保持，页面刷新或分区切换后筛选条件不丢失
- **依赖**：P1.2（引用标识筛选选项常量）

### P3.2 新建 `apps/console/components/alert_card.py` 异常告警卡片组件（复杂度：中等）

- **文件路径**：`apps/console/components/alert_card.py`
- **修改内容**：新建文件，实现以下函数：
  - `ALERT_SEVERITY_COLORS`（`high` → 红色、`medium` → 橙色、`low` → 蓝色，引用 theme.py 常量）
  - `classify_alert_severity(alert: dict, plots: list[dict]) -> str`：关联地块有 BLOCKED 标识 → `high`；关联地块有 DEGRADED/RESCHEDULED 标识 → `medium`；其他 → `low`
  - `render_alert_card(alert: dict, plots: list[dict]) -> None`：使用 `st.container(border=True)` 包裹，卡片内部左侧图标列 + 右侧内容列；图标根据严重程度（high → ❌、medium → ⚠️、low → ℹ️）；背景色根据严重程度区分
  - `render_alert_cards(alerts: list[dict], plots: list[dict]) -> None`：渲染全部异常告警卡片列表
- **验收条件**：关联地块有 BLOCKED 标识的告警判定为 high 并以红色卡片展示；关联地块有 DEGRADED 标识的告警判定为 medium 并以橙色卡片展示；每条告警为独立卡片含图标+地块编号+告警文字
- **依赖**：P1.2（引用 PRIORITY_HIGH_COLOR 等常量）

---

## Phase 4：现有组件改造

**任务组目标**：改造 5 个现有组件以集成新可视化组件和新交互方式，保持业务逻辑不变。
**任务组依赖**：P1（主题基础设施）、P2（可视化组件）、P3（交互组件）。
**任务组验收**：所有改造组件保持原有业务逻辑不变，仅改变展示形式和交互方式；颜色统一引用 theme.py 常量。

### P4.1 改造 `apps/console/components/stage_badge.py` Badge 渲染组件（复杂度：简单）

- **文件路径**：`apps/console/components/stage_badge.py`
- **修改内容**：
  - `render_badge()` 中 CSS 样式字符串优化：增加 `padding: 4px 12px`、`font-weight: 500`、`box-shadow: 0 1px 2px rgba(0,0,0,0.08)`，改为更精致的胶囊样式
  - 新增 `render_badge_html(code: str) -> str` 函数：返回 badge HTML 字符串（不直接渲染），用于表格内嵌展示
  - 颜色值继续引用 `theme.py` 的 `BADGE_COLORS` 常量
- **验收条件**：badge 渲染为胶囊形状（圆角矩形），有适当内边距，字号与周围文字协调；`render_badge_html` 返回的 HTML 字符串可用于表格内嵌；`unsafe_allow_html=True` 保留
- **依赖**：P1.2（BADGE_COLORS 已在 theme.py 中定义）、P1.3（badge 胶囊样式 CSS）

### P4.2 改造 `apps/console/components/plot_table.py` 地块表格与操作入口（复杂度：复杂）

- **文件路径**：`apps/console/components/plot_table.py`
- **修改内容**：
  - **`build_rows()` 重构**：将"巡田""处方""作业""评估"4列合并为"四阶段进度"1列，列值为 `render_stage_progress(stages)` 返回的 HTML 字符串；"业务标识"列改为 badge 标签 HTML（使用 `render_badge_html`）；列数从9列减少为6列（地块/农场/面积(亩)/四阶段进度/业务标识/更新时间）；`COLUMNS` 常量同步更新
  - **`render_plot_table()` 重构**：由于 `st.dataframe` 不支持单元格内嵌 HTML，改为使用自定义 HTML 表格渲染（`st.markdown(html_table, unsafe_allow_html=True)`）；表格行根据 badges 添加高亮 CSS class（`row-blocked`/`row-degraded`）；支持排序（通过列头按钮触发，排序状态存储在 session_state）
  - **`render_action_entries()` 重构**：从逐地块三列布局改为表格内嵌按钮形式；在四阶段总览表格中增加"操作"列，内嵌"查看处方"和"下发作业"按钮；阻断地块的"查看处方"按钮灰色禁用 + tooltip；未审核地块的"下发作业"按钮灰色禁用
  - **`render_prescription_detail()` 重构**：使用 `st.expander("处方详情 · {plotNo}", expanded=True)` 包裹；4张指标卡片使用 `render_metric_card()` 渲染，buffer 卡片根据值变色（< 0 红色、0-3 橙色、≥ 3 绿色）；合规校验结论使用 `render_safety_icon()` 和 `render_window_icon()` 渲染；拒绝/降级提示使用 `st.error`/`st.warning` 卡片突出展示；分区表格中零施药行文字灰色标识
  - **`render_dispatch_feedback()` 重构**：使用 `st.expander("下发前作业窗口校验 · {plot_no}", expanded=True)` 包裹，与处方详情面板独立
  - **`_close_button()` 调整**：折叠面板的关闭通过 `st.expander` 的内置折叠机制实现，不再需要单独的"收起详情"按钮
- **保留不变**：`evaluate_dispatch_window()` 函数签名与逻辑、`STATE_SELECTED_PLOT`/`STATE_DISPATCH` session_state 键名、`ExecutionAgent().dispatch()` 调用链、`AssessmentAgent().assess()` 调用链、`build_demo_feedback()` 调用
- **验收条件**：表格列数为 6（地块、农场、面积、四阶段进度、业务标识、更新时间），四阶段进度列为可视化进度条；阻断地块行背景为浅红色，降级地块行背景为浅橙色；处方详情展开时显示 4 张指标卡片（buffer 卡片颜色随值变化）和合规校验图标；同一时间只有一个地块的处方详情展开；点击"查看处方"展开、点击 expander 标题折叠
- **依赖**：P1.3（CSS 样式）、P2.1（metric_card）、P2.2（stage_progress）、P2.4（compliance_icon）、P4.1（render_badge_html）

### P4.3 改造 `apps/console/components/todo_panel.py` 待办面板（复杂度：中等）

- **文件路径**：`apps/console/components/todo_panel.py`
- **修改内容**：
  - **新增优先级判定**：`classify_todo_priority(todo: dict, plots: list[dict]) -> str`：关联地块有 BLOCKED 标识或类型为 review/confirm → "高"；关联地块有 DEGRADED/RESCHEDULED 标识或类型为 audit/replan → "中"；其他 → "低"。需扩展 `render_todos()` 入参增加 `plots` 参数
  - **待办卡片化**：每条待办使用 `st.container(border=True)` 包裹，卡片内包含优先级标签（badge 样式，引用 PRIORITY_HIGH_COLOR 等）+ 地块编号 + 待办内容文字，卡片之间有间距
  - **角色组折叠**：每个角色组使用 `st.expander(f"{role}（{count}）", expanded=has_items)` 包裹；有待办的组默认展开，无待办的组默认折叠
  - **待办计数**：角色组标题旁显示数量，如"农技专家（3）"
- **保留不变**：`group_todos()` 分组逻辑、`ROLE_ORDER`、`ROLE_BY_TYPE` 类型映射
- **验收条件**：关联地块有 BLOCKED 标识的待办展示红色"高"标签；类型为 audit 的待办展示橙色"中"标签；每个角色组标题旁显示待办数量；有待办的组默认展开、无待办的组默认折叠；每条待办为独立卡片而非表格行
- **依赖**：P1.2（引用 PRIORITY_HIGH_COLOR 等常量）

### P4.4 改造 `apps/console/components/batch_queue.py` 批次队列（复杂度：中等）

- **文件路径**：`apps/console/components/batch_queue.py`
- **修改内容**：
  - **紧迫度热力标识**：由于 `st.dataframe` 不支持单元格样式，改为自定义 HTML 表格渲染；紧迫度单元格背景色按数值线性渐变（从 `URGENCY_HEAT_LOW` 到 `URGENCY_HEAT_HIGH` 插值）；数值文字同时显示
  - **状态 badge**：状态列改为 badge 标签形式，使用 `BATCH_STATE_COLORS` 和 `BATCH_STATE_LABELS` 映射（草稿灰色、待确认蓝色、已入队绿色、执行中橙色、已完成深绿色、已取消红色）
  - **批次队列标题**：改为 `st.subheader(f"批次队列（{len(batches)}）")`
  - **排序控件**：新增排序下拉框 `st.selectbox("排序", ["位次", "紧迫度", "状态"])`，排序状态存储在 `session_state["cipm_batch_sort_v1"]`，默认按位次升序
- **保留不变**：`build_batch_rows()` 行数据构建逻辑（仅改变渲染方式）、空批次 `st.info("暂无批次")` 逻辑
- **验收条件**：紧迫度最高值单元格背景为深红色，最低值为浅黄色，中间值渐变过渡；状态列展示 badge 标签（执行中为橙色 badge）；标题包含数量"批次队列（N）"；无批次时展示"暂无批次"
- **依赖**：P1.2（引用 BATCH_STATE_COLORS、URGENCY_HEAT_LOW/HIGH 等常量）、P1.3（紧迫度热力 CSS 样式）

### P4.5 改造 `apps/console/services/runtime_state.py` 运行时状态（复杂度：简单）

- **文件路径**：`apps/console/services/runtime_state.py`
- **修改内容**：
  - 新增 `clear_filter_state() -> None`：清除 `cipm_filter_state_v1` 键
  - 新增 `clear_ui_state() -> None`：清除所有 UI 相关状态键（筛选 `cipm_filter_state_v1`、折叠 `cipm_prescription_expanded_v1`/`cipm_dispatch_expanded_v1`/`cipm_todo_collapsed_v1`、Tab `cipm_active_tab_v1`、排序 `cipm_batch_sort_v1`），保留运行时状态 `cipm_runtime_state_v1` 和基线状态 `cipm_patrol_baseline_v1`
  - `clear_runtime_state()` 保持不变
- **保留不变**：`STATE_KEY="cipm_runtime_state_v1"`、`BASELINE_KEY="cipm_patrol_baseline_v1"`、`STAGES` 定义、`set_stage()`/`stage_of()`/`merge_stages()`/`apply_patrol_baseline()` 函数
- **验收条件**：`clear_filter_state()` 清除筛选状态后筛选条件为空；`clear_ui_state()` 清除所有 UI 状态但保留运行时状态和基线状态；现有 `clear_runtime_state()` 行为不变
- **依赖**：无（仅新增函数，不修改现有函数）

---

## Phase 5：主入口重构

**任务组目标**：将 `app.py` 重构为分区导航布局，将所有组件组装到 5 个 Tab 分区中。
**任务组依赖**：P1（主题基础设施）、P2（可视化组件）、P3（交互组件）、P4（现有组件改造）。
**任务组验收**：页面加载后默认展示"总览"分区；切换 Tab 时顶部固定区域不闪烁；刷新按钮清除筛选条件与折叠状态并回到总览分区。

### P5.1 重构 `apps/console/app.py` 主入口为分区导航布局（复杂度：复杂）

- **文件路径**：`apps/console/app.py`
- **修改内容**：整体重构为分区导航布局，新结构如下：
  - `st.set_page_config(page_title=PAGE_TITLE, layout="wide")` 之后调用 `inject_custom_css()`
  - **顶部固定区域**：`st.title` + 模式说明 + 快照时间 + 刷新按钮（使用 `st.columns` 布局在一行内），切换任意分区时始终可见
  - **分区导航**：使用 `st.tabs([TAB_OVERVIEW, TAB_PRESCRIPTION, TAB_TODO_BATCH, TAB_ALERT, TAB_SETTINGS])` 实现 5 个分区
  - **总览分区**（`tabs[0]`）：`render_metric_cards_row()` → `render_stress_chart()` → `render_plot_filter()` → `render_plot_table()`（含进度条列和操作按钮），按"核心指标→详细数据→操作入口"层次排列
  - **处方与作业分区**（`tabs[1]`）：处方详情折叠面板 + 下发反馈折叠面板
  - **待办与批次分区**（`tabs[2]`）：`render_todos(todos, plots)` + `render_batch_queue(batches)`
  - **异常与告警分区**（`tabs[3]`）：`render_alert_cards(alerts, plots)`，标题旁显示异常总数
  - **设置分区**（`tabs[4]`）：运行模式信息展示
  - **刷新按钮逻辑更新**：`get_dashboard.clear()` + `clear_runtime_state()` + `clear_filter_state()` + `clear_ui_state()` + `st.rerun()`
- **保留不变**：`st.set_page_config` 调用、数据加载逻辑 `get_dashboard(mock=mock_mode, api_base=api_base)`、`apply_patrol_baseline(plots)` + `merge_stages(plots)` 调用、降级提示 `st.warning`、空状态处理 `render_empty_state()`、底部声明 `st.caption`
- **验收条件**：页面首次加载默认展示"总览"分区，无需操作即可看到指标卡片、胁迫图表、筛选器、四阶段表格；切换 Tab 时顶部固定区域不闪烁，仅内容区域变化；刷新按钮点击后筛选条件清空、数据重新加载、回到总览分区默认状态；各分区空数据时展示空状态提示
- **依赖**：P1.3（inject_custom_css）、P2.1（metric_card）、P2.3（stress_chart）、P3.1（plot_filter）、P3.2（alert_card）、P4.2（plot_table 改造）、P4.3（todo_panel 改造）、P4.4（batch_queue 改造）、P4.5（runtime_state 改造）

---

## Phase 6：测试

**任务组目标**：为所有新增组件编写单元测试，更新现有测试以适配新布局。
**任务组依赖**：P1—P5（所有编码任务）。
**任务组验收**：新增 9 个测试文件全部通过；现有 3 个测试文件更新后通过；纯函数测试不依赖 AppTest，涉及 Streamlit 渲染的测试使用 AppTest 框架。

### P6.1 新增 `tests/unit/console/test_css_inject.py` CSS 注入测试（复杂度：简单）

- **文件路径**：`tests/unit/console/test_css_inject.py`
- **测试内容**：
  - `test_inject_custom_css_no_exception`：`inject_custom_css()` 不抛异常
  - `test_inject_custom_css_contains_key_styles`：注入的 CSS 包含卡片、进度条、badge 等关键样式类
- **对应编码任务**：P1.3
- **依赖**：P1.3

### P6.2 新增 `tests/unit/console/test_metric_card.py` 指标卡片测试（复杂度：简单）

- **文件路径**：`tests/unit/console/test_metric_card.py`
- **测试内容**：
  - `test_metric_card_renders_value`：指标卡片正确渲染数值
  - `test_metric_cards_row_shows_four_cards`：4 张指标卡片横向排列，数值正确
  - `test_metric_card_buffer_color_override`：buffer 卡片根据值变色（< 0 红/0-3 橙/≥ 3 绿）
- **对应编码任务**：P2.1
- **依赖**：P2.1

### P6.3 新增 `tests/unit/console/test_stage_progress.py` 四阶段进度条测试（复杂度：简单）

- **文件路径**：`tests/unit/console/test_stage_progress.py`
- **测试内容**：
  - `test_classify_stage_status_done`：已完成类状态映射为 `node-done`
  - `test_classify_stage_status_blocked`：阻断类状态映射为 `node-blocked`
  - `test_render_stage_progress_returns_html`：`render_stage_progress` 返回包含 4 个节点的 HTML 字符串
  - `test_render_stage_progress_unknown_status`：未知状态值映射为 `node-pending`
- **对应编码任务**：P2.2
- **依赖**：P2.2

### P6.4 新增 `tests/unit/console/test_plot_filter.py` 地块筛选器测试（复杂度：中等）

- **文件路径**：`tests/unit/console/test_plot_filter.py`
- **测试内容**：
  - `test_filter_by_search_plotNo`：搜索框按地块编号模糊匹配
  - `test_filter_by_search_plotName`：搜索框按地块名称模糊匹配
  - `test_filter_by_stage`：阶段筛选下拉框过滤匹配地块
  - `test_filter_by_badge`：标识筛选下拉框过滤匹配地块
  - `test_filter_state_persistence`：筛选状态在 session_state 中保持
- **对应编码任务**：P3.1
- **依赖**：P3.1

### P6.5 新增 `tests/unit/console/test_stress_chart.py` 胁迫等级图表测试（复杂度：简单）

- **文件路径**：`tests/unit/console/test_stress_chart.py`
- **测试内容**：
  - `test_build_stress_data_counts`：胁迫等级统计正确
  - `test_render_stress_chart_no_exception`：渲染图表不抛异常
  - `test_render_stress_chart_all_zero_stress`：全部地块无胁迫时图表正常渲染
- **对应编码任务**：P2.3
- **依赖**：P2.3

### P6.6 新增 `tests/unit/console/test_compliance_icon.py` 合规校验图标测试（复杂度：简单）

- **文件路径**：`tests/unit/console/test_compliance_icon.py`
- **测试内容**：
  - `test_safety_icon_satisfied`：`satisfied` 结论渲染绿色勾号
  - `test_safety_icon_degraded`：`degraded` 结论渲染橙色感叹号
  - `test_window_icon_pass_with_notice`：`pass_with_mandatory_notice` 渲染橙色感叹号
- **对应编码任务**：P2.4
- **依赖**：P2.4

### P6.7 新增 `tests/unit/console/test_alert_card.py` 异常告警卡片测试（复杂度：简单）

- **文件路径**：`tests/unit/console/test_alert_card.py`
- **测试内容**：
  - `test_classify_alert_severity_high`：关联地块有 BLOCKED 标识的告警判定为 high
  - `test_classify_alert_severity_medium`：关联地块有 DEGRADED 标识的告警判定为 medium
  - `test_render_alert_cards_no_exception`：渲染告警卡片列表不抛异常
- **对应编码任务**：P3.2
- **依赖**：P3.2

### P6.8 新增 `tests/unit/console/test_batch_queue.py` 批次队列测试（复杂度：中等）

- **文件路径**：`tests/unit/console/test_batch_queue.py`
- **测试内容**：
  - `test_batch_state_badge_colors`：批次状态 badge 颜色映射正确
  - `test_urgency_heat_gradient`：紧迫度热力标识颜色渐变正确
  - `test_batch_queue_title_with_count`：批次队列标题包含数量
  - `test_batch_queue_empty_state`：无批次时展示空状态提示
- **对应编码任务**：P4.4
- **依赖**：P4.4

### P6.9 新增 `tests/unit/console/test_todo_priority.py` 待办优先级测试（复杂度：简单）

- **文件路径**：`tests/unit/console/test_todo_priority.py`
- **测试内容**：
  - `test_priority_high_for_blocked_plot`：关联地块有 BLOCKED 标识的待办判定为高优先级
  - `test_priority_high_for_review_type`：类型为 review 的待办判定为高优先级
  - `test_priority_medium_for_degraded_plot`：关联地块有 DEGRADED 标识的待办判定为中优先级
  - `test_priority_low_default`：其他待办判定为低优先级
- **对应编码任务**：P4.3
- **依赖**：P4.3

### P6.10 更新 `tests/unit/console/test_dashboard_smoke.py` 仪表盘冒烟测试（复杂度：中等）

- **文件路径**：`tests/unit/console/test_dashboard_smoke.py`
- **更新内容**：
  - 适配新表格列定义（6 列而非 9 列）
  - 适配分区 Tab 导航（5 个分区）
  - 适配指标卡片（4 张而非 1 张）
  - 适配 CSS 注入调用
- **对应编码任务**：P5.1
- **依赖**：P5.1

### P6.11 更新 `tests/unit/console/test_plot_actions.py` 地块操作测试（复杂度：中等）

- **文件路径**：`tests/unit/console/test_plot_actions.py`
- **更新内容**：
  - 适配折叠面板交互（expander 而非按钮 rerun）
  - 适配处方详情卡片化（4 张指标卡片）
  - 适配合规校验图标化
- **对应编码任务**：P4.2
- **依赖**：P4.2

### P6.12 更新 `tests/unit/console/test_runtime_state.py` 运行时状态测试（复杂度：简单）

- **文件路径**：`tests/unit/console/test_runtime_state.py`
- **更新内容**：
  - 新增 `clear_filter_state()` 测试
  - 新增 `clear_ui_state()` 测试
  - 验证 `clear_ui_state()` 保留运行时状态和基线状态
- **对应编码任务**：P4.5
- **依赖**：P4.5

---

## 任务依赖关系总览

```
Phase 1（主题基础设施）
  P1.1 config.toml ─────────────────────────────────────┐
  P1.2 theme.py 扩展 ──┬── P1.3 css_inject.py ──────────┤
                       │                                 │
Phase 2（可视化组件）   │                                 │
  P2.1 metric_card ────┤                                 │
  P2.2 stage_progress ─┤                                 │
  P2.3 stress_chart ───┤                                 │
  P2.4 compliance_icon ┤                                 │
                       │                                 │
Phase 3（交互组件）     │                                 │
  P3.1 plot_filter ────┤                                 │
  P3.2 alert_card ─────┤                                 │
                       │                                 │
Phase 4（现有组件改造） │                                 │
  P4.1 stage_badge ────┤                                 │
  P4.2 plot_table ─────┤（依赖 P1.3, P2.1, P2.2, P2.4, P4.1）
  P4.3 todo_panel ────┤                                 │
  P4.4 batch_queue ───┤                                 │
  P4.5 runtime_state ─┤                                 │
                       │                                 │
Phase 5（主入口重构）   │                                 │
  P5.1 app.py ────────┤（依赖 P1.3, P2.1, P2.3, P3.1, P3.2, P4.2, P4.3, P4.4, P4.5）
                       │                                 │
Phase 6（测试）         │                                 │
  P6.1—P6.9 新增测试 ─┤（各自依赖对应编码任务）          │
  P6.10—P6.12 更新测试 ┘                                │
```

## 复杂度汇总

| Phase | 简单 | 中等 | 复杂 | 总计 |
|-------|------|------|------|------|
| P1 主题基础设施 | 2 | 1 | 0 | 3 |
| P2 可视化组件 | 1 | 3 | 0 | 4 |
| P3 交互组件 | 0 | 2 | 0 | 2 |
| P4 现有组件改造 | 2 | 2 | 1 | 5 |
| P5 主入口重构 | 0 | 0 | 1 | 1 |
| P6 测试 | 6 | 3 | 0 | 9 |
| **合计** | **11** | **11** | **2** | **24** |