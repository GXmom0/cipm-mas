# 规则引擎口径说明（M05）

本包只包含确定性纯函数，**禁止 IO、随机、当前时间与大模型调用**。LLM 仅可解释结果，不得改变判定。

## 安全间隔判定 `evaluate_safety_interval`

设 `R = 采收剩余天数`，`S = 引用目录项安全间隔期`，`buffer = R − S`。

| 优先级 | 条件 | 结论 | reason_code |
|---|---|---|---|
| 1 | `candidates` 非空且不存在可用替代（`S' ≤ R`、低毒、季次数未超限、有效） | refused | NO_ELIGIBLE_ITEM |
| 2 | `R < S` | refused | INTERVAL_EXCEEDS_REMAINING |
| 3 | 同有效成分在间隔期内重复施用 | refused | REUSE_WITHIN_INTERVAL |
| 3 | 季使用次数已达上限 | refused | SEASON_LIMIT_REACHED |
| 4 | `0 ≤ buffer < 3` | degraded | BUFFER_LT_3 |
| 5 | 距上次同成分间隔 < 最小轮换间隔 | degraded | ROTATION_INTERVAL |
| 6 | 采收前敏感窗口 | degraded | PRE_HARVEST_SENSITIVE |
| 7 | 物候期为苗期或吐絮期 | degraded | PHENOLOGY_LOW_RISK |
| 8 | `buffer ≥ 3` 且无 5—7 触发 | satisfied | — |

实现约束：

1. 优先级 1—3 为拒绝，命中即短路，不再评估降级原因。
2. 优先级 4—7 为降级，命中项全部累加，顺序固定为 4→5→6→7。
3. `buffer_days` 由函数计算，恒等于 `R − S`，不接受外部传入。
4. `R < S` 一律拒绝，不得因存在更短安全间隔期替代药剂而自动改选放行；`alternatives` 仅供重新发起处方版本。

## 单剂复配拦截 `check_single_agent`

| 条件 | 结论 |
|---|---|
| 品类数 ≥ 2，唯一键 `(有效成分, 剂型)` | 硬拦截：`allowed=false`、`action=intercepted_to_expert`、`auto_dispatch_allowed=false`、`applies_to=expert_manual_only` |
| 登记混剂按单一品类使用 | 视为单剂，允许，保留 `formulationType` |
| 空列表或空品类 | 抛 `RuleInputError(CIPM-RULE-5005)` |
| 品类数 = 1 | 允许单剂处方 |

复配结果中的 `max_safety_interval_days` 仅作专家手工组合参考，**不得**据此自动写入处方、自动校验通过或自动下发。V1.0 不存在复配自动放行路径。

## 与设计文档对应

- 判定表来源：`design.md` 2.1.3.4「规则引擎判定表」
- 任务口径：`tasks.md` 第 3 节
- 规格依据：`spec.md` 5.3.1、6.5、6.10