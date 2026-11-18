# 变更记录（CHANGELOG）

## [Unreleased] 2026-11-16

### Added
- 作业下发服务端幂等：新增 `IdempotencyRepo`（`apps/platform_api/repository/idempotency_repo.py`），进程内 + JSON 持久化，接口可平滑替换为 PostgreSQL。
- 新增 `POST /api/v1/agents/execution/dispatch` 下发入口（`apps/platform_api/api/v1/execution.py`），路由层幂等包裹：重复键返回首次结果并带 `data.replayed=true`，不再下发设备。
- 新增 `tests/unit/platform_api/test_idempotency.py`：首次下发、重复键 replayed、failed 后可重试、并发同键只下发一次、超时需显式 cancel、JSON 持久化重载。
- 新增错误码 `IDEMPOTENCY_KEY_REQUIRED`（`CIPM-EXEC-6005`）：缺少幂等键时显式返回 400，并说明键的生成/复用方式。
- 新增 `POST /api/v1/agents/execution/cancel` 取消入口；新增错误码 `WORK_ORDER_NOT_FOUND`（`CIPM-EXEC-6006`）、`WORK_ORDER_ALREADY_ACKED`（`CIPM-EXEC-6007`）。
- 新增错误码 `WORK_ORDER_AMBIGUOUS`（`CIPM-EXEC-6008`）：cancel 仅凭 `workOrderNo` 命中多条记录时返回 409，提示改用 `idempotencyKey`。
- 幂等仓库支持 `pending` 超 TTL（`CIPM_IDEMPOTENCY_TTL_SECONDS`，默认 600 秒）自动置 `expired` 并允许同 key 重发，历史记录保留供审计。
- 审计事件 `workorder.dispatch`（成功/重放）与 `workorder.cancel` 的 `afterValue` 载写入 `idempotencyKey`（重放另带 `replayed=true`），不新增 AuditEvent 字段、不改 JSON 结构。
- dispatch 失败分支（`rejected` / `rescheduled`）也写 `workorder.dispatch` 审计，`afterValue` 含 `status / workOrderNo（可空）/ idempotencyKey / reason`。

### Changed
- **API 路由面扩展（合同变更）**：`/api/v1` 路由集合由 3 条扩展为 4 条（新增 `/agents/execution/dispatch`）。`test_p00_app_constructible_and_expected_routes` 期望集合同步为 4 条，保留 `assert paths == {...}` 精确相等；其余 418 用例断言不变。
- **幂等键语义修正**：`idempotencyKey` 必填（请求体或 HTTP 头 `Idempotency-Key` 二选一），不再回落 `workOrderNo`；缺失时显式返回 `400 / IDEMPOTENCY_KEY_REQUIRED`（非 pydantic 422）；禁止服务端自动生成随机 UUID。
- **路由面再次扩展（合同变更）**：新增 `/api/v1/agents/execution/cancel`，路径集合由 4 条扩为 5 条；`test_p00` 期望集合同步为 5 条，仍 `assert paths == {...}` 精确相等。
- **状态机**：固定 `pending → acked | failed | cancelled | expired`，终态不回退。
- **cancel 定位优先级**：`idempotencyKey` > `workOrderNo`；仅 `workOrderNo` 命中多条 → `409 / WORK_ORDER_AMBIGUOUS`，禁止任选一条；成功取消写 `workorder.cancel` 审计（operator / reason / 原状态 / 新状态）。

### Unchanged
- `domain/rules` 纯函数、`ExecutionAgent` 判定逻辑、既有契约字段语义均不变。
- 未引入需要本地回环端口或额外守护进程的新依赖。