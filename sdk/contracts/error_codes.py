from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    PATROL_SOURCE_UNAVAILABLE = "CIPM-PATROL-1001"
    PATROL_NOT_READY = "CIPM-PATROL-1002"
    PATROL_BAND_MISSING = "CIPM-PATROL-1003"
    PATROL_QUALITY_REJECTED = "CIPM-PATROL-1004"
    PATROL_RAW_FRAMES_REJECTED = "CIPM-PATROL-1005"
    PATROL_BLOCKED = "CIPM-PATROL-2001"
    PATROL_REVIEW_CONFLICT = "CIPM-PATROL-2002"
    PATROL_RESULT_FROZEN = "CIPM-PATROL-2003"

    DECISION_RESULT_UNAVAILABLE = "CIPM-DECISION-3001"
    DECISION_TRIPLET_INCOMPLETE = "CIPM-DECISION-3002"
    DECISION_VERSION_CONFLICT = "CIPM-DECISION-3003"

    WINDOW_DATA_UNAVAILABLE = "CIPM-WINDOW-4001"
    WINDOW_TEMPERATURE_REJECTED = "CIPM-WINDOW-4002"
    WINDOW_WIND_REJECTED = "CIPM-WINDOW-4003"

    RULE_INPUT_INVALID = "CIPM-RULE-5001"
    RULE_REGISTRY_ITEM_INVALID = "CIPM-RULE-5002"
    RULE_DOSE_OUT_OF_RANGE = "CIPM-RULE-5003"
    RULE_VOLUME_INCONSISTENT = "CIPM-RULE-5004"
    RULE_INVALID_INPUT = "CIPM-RULE-5005"

    EXEC_DEVICE_REJECTED = "CIPM-EXEC-6001"
    EXEC_DEVICE_OFFLINE = "CIPM-EXEC-6002"
    EXEC_MANDATORY_NOT_ACKED = "CIPM-EXEC-6003"
    EXEC_PRECONDITION_FAILED = "CIPM-EXEC-6004"
    IDEMPOTENCY_KEY_REQUIRED = "CIPM-EXEC-6005"
    WORK_ORDER_NOT_FOUND = "CIPM-EXEC-6006"
    WORK_ORDER_ALREADY_ACKED = "CIPM-EXEC-6007"
    WORK_ORDER_AMBIGUOUS = "CIPM-EXEC-6008"

    ASSESS_DATA_INCOMPLETE = "CIPM-ASSESS-7001"
    ASSESS_VERDICT_CONFLICT = "CIPM-ASSESS-7002"

    CONTRACT_VALIDATION_FAILED = "CIPM-CONTRACT-8001"
    CONTRACT_SCHEMA_DRIFT = "CIPM-CONTRACT-8002"

    SYSTEM_UNAVAILABLE = "CIPM-SYSTEM-9001"
    SYSTEM_TIMEOUT = "CIPM-SYSTEM-9002"
    SYSTEM_INTERNAL_ERROR = "CIPM-SYSTEM-9003"


DEFAULT_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.PATROL_SOURCE_UNAVAILABLE: "影像或传感数据源不可用，请稍后重试。",
    ErrorCode.PATROL_NOT_READY: "正射影像产品未就绪，暂不开始识别。",
    ErrorCode.PATROL_BAND_MISSING: "影像缺少近红外或红光波段，无法计算植被指数。",
    ErrorCode.PATROL_QUALITY_REJECTED: "影像云量或地面分辨率不满足解析要求。",
    ErrorCode.PATROL_RAW_FRAMES_REJECTED: "输入为原始帧，本系统仅接受已拼接、已定标的正射影像产品。",
    ErrorCode.PATROL_BLOCKED: "该巡田任务处于阻断待复核状态，暂不生成处方。",
    ErrorCode.PATROL_REVIEW_CONFLICT: "复核状态已变更或已冻结，无法覆盖。",
    ErrorCode.PATROL_RESULT_FROZEN: "识别结果已冻结，不可修改。",
    ErrorCode.DECISION_RESULT_UNAVAILABLE: "识别结果不可用或不满足处方生成条件。",
    ErrorCode.DECISION_TRIPLET_INCOMPLETE: "处方三元组不完整，必须同时给出药剂品类、制剂亩用量与喷液量或稀释浓度。",
    ErrorCode.DECISION_VERSION_CONFLICT: "处方版本冲突，请基于最新版本重试。",
    ErrorCode.WINDOW_DATA_UNAVAILABLE: "作业窗口所需气象或地块数据不可用，按不通过处理。",
    ErrorCode.WINDOW_TEMPERATURE_REJECTED: "作业窗口温度低于红线，禁止施药。",
    ErrorCode.WINDOW_WIND_REJECTED: "作业窗口风速超过红线，禁止起飞作业。",
    ErrorCode.RULE_INPUT_INVALID: "规则输入不合法。",
    ErrorCode.RULE_REGISTRY_ITEM_INVALID: "登记用药目录项无效或已停用。",
    ErrorCode.RULE_DOSE_OUT_OF_RANGE: "制剂亩用量超出登记目录区间。",
    ErrorCode.RULE_VOLUME_INCONSISTENT: "喷液量与稀释浓度换算不一致。",
    ErrorCode.RULE_INVALID_INPUT: "规则输入缺失或字段为空。",
    ErrorCode.EXEC_DEVICE_REJECTED: "植保设备拒绝受理作业指令。",
    ErrorCode.EXEC_DEVICE_OFFLINE: "植保设备离线，作业转入待重新排期。",
    ErrorCode.EXEC_MANDATORY_NOT_ACKED: "强制提示未确认，禁止下发作业。",
    ErrorCode.EXEC_PRECONDITION_FAILED: "下发前置校验未通过。",
    ErrorCode.IDEMPOTENCY_KEY_REQUIRED: "缺少幂等键：请在请求体 idempotencyKey 或 HTTP 头 Idempotency-Key 中提供每次逻辑操作的唯一标识；重试必须复用同一键，不同批次/不同次作业必须使用不同键。",
    ErrorCode.WORK_ORDER_NOT_FOUND: "工单不存在，或无法定位对应的幂等记录。",
    ErrorCode.WORK_ORDER_ALREADY_ACKED: "工单已下发成功，不能取消；如需撤回请走设备侧撤回流程。",
    ErrorCode.WORK_ORDER_AMBIGUOUS: "仅凭 workOrderNo 命中多条幂等记录，无法确定要取消哪一次作业，请改用 idempotencyKey 指定。",
    ErrorCode.ASSESS_DATA_INCOMPLETE: "作业回传数据不完整，暂不出具达标结论。",
    ErrorCode.ASSESS_VERDICT_CONFLICT: "评估结论与处方证据不一致。",
    ErrorCode.CONTRACT_VALIDATION_FAILED: "数据契约校验未通过。",
    ErrorCode.CONTRACT_SCHEMA_DRIFT: "契约 Schema 与基线不一致。",
    ErrorCode.SYSTEM_UNAVAILABLE: "服务暂不可用。",
    ErrorCode.SYSTEM_TIMEOUT: "调用超时，请稍后重试。",
    ErrorCode.SYSTEM_INTERNAL_ERROR: "系统内部错误。",
}

RETRYABLE: dict[ErrorCode, bool] = {
    ErrorCode.PATROL_SOURCE_UNAVAILABLE: True,
    ErrorCode.PATROL_NOT_READY: True,
    ErrorCode.PATROL_BAND_MISSING: False,
    ErrorCode.PATROL_QUALITY_REJECTED: False,
    ErrorCode.PATROL_RAW_FRAMES_REJECTED: False,
    ErrorCode.PATROL_BLOCKED: False,
    ErrorCode.PATROL_REVIEW_CONFLICT: False,
    ErrorCode.PATROL_RESULT_FROZEN: False,
    ErrorCode.DECISION_RESULT_UNAVAILABLE: True,
    ErrorCode.DECISION_TRIPLET_INCOMPLETE: False,
    ErrorCode.DECISION_VERSION_CONFLICT: True,
    ErrorCode.WINDOW_DATA_UNAVAILABLE: True,
    ErrorCode.WINDOW_TEMPERATURE_REJECTED: False,
    ErrorCode.WINDOW_WIND_REJECTED: False,
    ErrorCode.RULE_INPUT_INVALID: False,
    ErrorCode.RULE_REGISTRY_ITEM_INVALID: False,
    ErrorCode.RULE_DOSE_OUT_OF_RANGE: False,
    ErrorCode.RULE_VOLUME_INCONSISTENT: False,
    ErrorCode.RULE_INVALID_INPUT: False,
    ErrorCode.EXEC_DEVICE_REJECTED: False,
    ErrorCode.EXEC_DEVICE_OFFLINE: True,
    ErrorCode.EXEC_MANDATORY_NOT_ACKED: False,
    ErrorCode.EXEC_PRECONDITION_FAILED: False,
    ErrorCode.IDEMPOTENCY_KEY_REQUIRED: False,
    ErrorCode.WORK_ORDER_NOT_FOUND: False,
    ErrorCode.WORK_ORDER_ALREADY_ACKED: False,
    ErrorCode.WORK_ORDER_AMBIGUOUS: False,
    ErrorCode.ASSESS_DATA_INCOMPLETE: True,
    ErrorCode.ASSESS_VERDICT_CONFLICT: False,
    ErrorCode.CONTRACT_VALIDATION_FAILED: False,
    ErrorCode.CONTRACT_SCHEMA_DRIFT: False,
    ErrorCode.SYSTEM_UNAVAILABLE: True,
    ErrorCode.SYSTEM_TIMEOUT: True,
    ErrorCode.SYSTEM_INTERNAL_ERROR: True,
}


def message_of(code: ErrorCode) -> str:
    return DEFAULT_MESSAGES[code]


def retryable_of(code: ErrorCode) -> bool:
    return RETRYABLE[code]