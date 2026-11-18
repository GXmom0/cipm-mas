# 增量规格：作业下发服务端幂等（路由面扩展 + 幂等键语义修正）

> 增量编号：INC-2026-11-16-01（含 1-A 语义修正）
> 基线：419 用例全部通过的 cipm-mas。本增量只新增服务端下发入口与幂等，不改 `domain/rules`、不改 `ExecutionAgent` 判定逻辑。

## 1. 变更性质（合同变更：路由面扩展）

- **API 路由面扩展**：新增 `POST /api/v1/agents/execution/dispatch`。
- `/api/v1` 路径集合由 3 条扩展为 4 条：
  1. `/api/v1/health`
  2. `/api/v1/dashboard`
  3. `/api/v1/agents/decision/invoke`
  4. `/api/v1/agents/execution/dispatch`（新增）
- 受影响的既有用例：`tests/unit/platform/test_envelope.py::test_p00_app_constructible_and_readonly_routes` → 已改名 `test_p00_app_constructible_and_expected_routes`，期望集合扩为上述 4 条，**仍为 `assert paths == {...}` 精确相等**；其余断言不变，其他 418 用例断言不变。

## 2. 幂等键语义（1-A 修正）

- **`idempotencyKey` 必填**：请求体 `idempotencyKey` 或 HTTP 头 `Idempotency-Key` 二选一，取其一。
- 语义固定：`key` = **一次逻辑操作（一次点击）的唯一标识**；重试必须复用同一 key；不同批次/不同次作业必须使用不同 key。
- **不再回落 `workOrderNo`**：因为 `ExecutionAgent` 对同一地块的 `workOrderNo` 确定性生成（`agents/execution/agent.py:76-77`），若回落会把「同一地块第二次合法作业」误判为重复。
- **禁止服务端自动生成随机 UUID**：缺失时必须显式返回 `400 / IDEMPOTENCY_KEY_REQUIRED`，并说明生成方式；不得静默生成新键导致幂等失效。

### 缺失键响应

- HTTP `400`，错误码 `CIPM-EXEC-6005`（`IDEMPOTENCY_KEY_REQUIRED`）。
- **不是** pydantic 必填校验的 `422`：`ExecutionDispatchRequest.idempotencyKey` 保留默认空串（兼容契约），由路由层显式判空后抛 `BizError(400)`。

## 3. 需求（其余）

- 重复键（已 `acked`）：不得再次下发设备，直接返回首次结果，响应 `data.replayed=true`。
- 下发状态机：`pending → acked / failed / cancelled`。
- `pending` 超 TTL 未 `acked` 时必须走显式 cancel，禁止静默重发；`failed / cancelled` 允许重试。（HTTP cancel 端点留到 1-B。）
- 存储：进程内 + JSON 文件持久化；接口与存储解耦，可平滑替换为 PostgreSQL。

## 4. 幂等仓库接口

```text
claim(key, payload) -> ClaimResult(claimed: bool, record, expired: bool)
mark_acked(key, workOrderNo, *, result=None)
mark_failed(key, reason, *, result=None)
mark_cancelled(key, reason)
get(key) -> IdempotencyRecord | None
```

## 5. 约束

- `domain/rules` 零改动；`ExecutionAgent` 判定逻辑零改动；UI 层零改动。
- 契约字段只增不改：`replayed` 放 `Envelope.data`；新增错误码 `IDEMPOTENCY_KEY_REQUIRED` 为枚举新增，不重命名既有项。
- 路由层只做参数校验 + 调用，幂等判断全部在 `IdempotencyRepo`。

## 6. 测试

`tests/unit/platform_api/test_idempotency.py`：
- 仓库层：首次 pending→acked、重复键不重放、failed 可重试、并发同键只放行一次、超时需显式 cancel、未知键 None、JSON 持久化重载。
- 路由层：同键重试 `replayed=true` 且设备只调一次；**同地块两个不同 key 均真实执行且 workOrderNo 各自独立（隔离 fake）**；**缺失 key → 400 + `CIPM-EXEC-6005`**；Header `Idempotency-Key` 生效。
- 失败路径审计：
  - `tests/unit/platform_api/test_idempotency.py::test_dispatch_route_rejected_writes_audit`
  - `tests/unit/platform_api/test_idempotency.py::test_dispatch_route_rejected_audit_queryable_by_plot_no`（验证 `query_by_biz_id(plotNo)` 可查回，且 `after.reason` 非空）

### 回归口径

- 本机：450 passed / 0 failed；
- 沙箱：409 passed + 41 skipped（loopback 受限），合计 450，与本机一致。

> 说明：ExecutionAgent.dispatch 已支持可选参数 work_order_no（默认 None，不改变既有行为），但路由层当前不传该参数；工单号唯一化需配合状态持久化，否则页面展示与实际下发会不一致，故留待持久化落地后启用。
## 7. 1-B：cancel 端点 + TTL 显式失效

### 7.1 路由

- 新增 `POST /api/v1/agents/execution/cancel`，入参 `{workOrderNo | idempotencyKey, reason}`，二者至少给一个；响应沿用统一信封。
- 错误映射：
  - 工单/幂等记录不存在 → `404 / WORK_ORDER_NOT_FOUND`（`CIPM-EXEC-6006`）
  - 当前为 `acked` → `409 / WORK_ORDER_ALREADY_ACKED`（`CIPM-EXEC-6007`；已下发撤回属设备侧，不在本轮）
  - 当前为 `failed/expired` → `409 / EXEC_PRECONDITION_FAILED`（不可取消）
  - 当前为 `cancelled` 再次取消 → `200` 且 `data.replayed=true`（幂等，不报错）；重复取消（`CANCEL_ALREADY_CANCELLED`）**不产生新的审计记录**——审计只记录状态变更，重复调用无状态变更故不落痕。
- 仅 `pending` 可转 `cancelled`。

### 7.2 TTL

- `pending` 超过 `CIPM_IDEMPOTENCY_TTL_SECONDS`（默认 600 秒）→ 自动置 `expired`，允许同 key 重新 claim 并重新下发。
- 记录不删除：同一 key 保留历史轮次（`[expired, pending, ...]`），供审计。

### 7.3 状态机

`pending → acked | failed | cancelled | expired`，终态不回退；同一 key 的新一轮 claim 追加新记录，不改写旧终态记录。

### 7.4 测试

仓库层：cancel 后可重发、TTL 过期后可重发（旧记录保留 expired）、cancel 不存在、acked cancel 返回 already_acked、重复 cancel 幂等。
路由层：cancel 404、acked cancel 409、重复 cancel 200 幂等、TTL 后可重发。

### 7.5 cancel 定位优先级与歧义守卫（永久）

- 定位优先级：`idempotencyKey` > `workOrderNo`。两者都给时以 `idempotencyKey` 为准；仅当该 key 无记录时才用 `workOrderNo`。
- 仅给 `workOrderNo` 且该号命中**多条**记录（含 `pending/acked/cancelled/expired` 与历史轮次）时，返回 `409 / WORK_ORDER_AMBIGUOUS`（`CIPM-EXEC-6008`），禁止任选一条处理，提示改用 `idempotencyKey`。
- 该校验永久保留，不因后续 `workOrderNo` 变唯一而删除（历史数据与设备回执仍按旧号索引，删除会重新引入错取消）。
- 审计事件 `workorder.cancel`：`operator` 为取消人、`before={"status": 原状态}`、`after={"status":"cancelled","reason": 取消原因}`、`biz_id=workOrderNo`，`AuditRepo` 按天 append-only 落 JSONL。
## 8. cancel 接口调用约定（生产）

1. **生产调用方必须携带 `idempotencyKey`**（请求体 `idempotencyKey` 或 HTTP 头 `Idempotency-Key`）。仅传 `workOrderNo` 且该号在历史中命中多条记录时，返回 `409 / WORK_ORDER_AMBIGUOUS`（`CIPM-EXEC-6008`），message 提示改用 `idempotencyKey`。
2. **永久语义**：定位优先级 `idempotencyKey > workOrderNo` 与歧义守卫长期有效，**不因后续 `workOrderNo` 唯一化而改变**（历史数据与设备回执仍按旧号索引）。
3. **按 key 查工单（运维排查）**：

```bash
# 查幂等存储，按 idempotencyKey 定位工单（只读，无副作用）
python -c "import json; d=json.load(open('data/idempotency.json',encoding='utf-8')); print(d['OP-2026-11-16-0001'][-1]['workOrderNo'])"

# 或用 cancel 定位（注意：pending 命中会被取消，仅确认归属时请优先查 JSON）
curl -s -X POST http://127.0.0.1:8000/api/v1/agents/execution/cancel \
  -H "Content-Type: application/json" \
  -d '{"idempotencyKey":"OP-2026-11-16-0001","reason":"运维确认"}'
```

### 审计字段样例（`workorder.cancel`）

```json
{
  "eventType": "workorder.cancel",
  "operator": "manager_li",
  "bizId": "WO-20261113-0912",
  "beforeValue": {"status": "pending"},
  "afterValue": {"status": "cancelled", "reason": "窗口变化", "idempotencyKey": "OP-2026-11-16-0001"},
  "occurredAt": "2026-11-13T08:00:00+08:00",
  "result": "success"
}
```

字段映射：`operator=谁取消`，`afterValue.reason=取消原因`，`beforeValue.status=原状态(fromStatus)`，`afterValue.status=新状态(toStatus)`，`bizId=workOrderNo；rejected 场景无工单号时回落为 plotNo，便于按地块反查`，`afterValue.idempotencyKey=触发该操作的幂等键`。

`workorder.dispatch` 审计覆盖**成功 / 重放 / 失败**三态：
- 成功（dispatched）：`afterValue` 含 `status / workOrderNo / idempotencyKey / replayed=false`；
- 重放（replayed）：`afterValue` 含 `status / workOrderNo / idempotencyKey / replayed=true`；
- 失败（`rejected` / `rescheduled`）：`afterValue` 含 `status / workOrderNo（可为空）/ idempotencyKey / reason（=outcome.message）`。

### 设备适配层幂等前置约束（接入真机时必须满足）

服务端幂等只能防止"重复提交下发请求"；若下发请求**已送达设备但回执丢失**，客户端重试仍可能造成重复作业。因此设备适配层（`adapters/`）**必须**以 `workOrderNo` 作为设备侧唯一指令号做去重——同一 `workOrderNo` 重复到达设备只执行一次，由设备侧幂等兜底。这是接入真机的前置约束，服务端一旦生成并下发 `workOrderNo` 就不再变化（本轮不做工单号唯一化）。
## 9. 遗留（下一步）

1. 鉴权与 RBAC
2. 业务状态持久化
3. LLM 兜底处方
4. 登记目录真实同步
5. UI 改走中台与设备侧幂等