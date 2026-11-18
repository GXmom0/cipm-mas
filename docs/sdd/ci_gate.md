# CI 门禁（CIPM-MAS CI）

> 工作流文件：`.github/workflows/ci.yml`；运行环境：`ubuntu-latest` + Python 3.12。

## 触发条件

- `push` 到 `main` / `develop` 分支；
- `pull_request` 到 `main` 分支；
- `workflow_dispatch`（手动触发）。

运行名包含触发类型（`quality (push|pull_request|workflow_dispatch)`），可一眼区分触发来源。

## 三个校验步骤（任一失败 → 整体 CI 标红）

1. **Mock 数据集门禁**：`python -m mock.cli --check` → 期望输出「数据集一致」；
2. **Schema 契约门禁**：`python -m sdk.contracts.schema_export --check` → 期望输出「Schema 一致」；
3. **全量测试**：`python -m pytest -q` → 期望 **473 passed / 0 failed**。

## 预期结果

- 三项均退出码 0，CI 为绿；
- 任何一项失败，CI 为红（工作流未启用 `continue-on-error`，默认失败即标红）；
- `starlette` 对 `httpx` 的弃用 warning 属已知无害，**不阻断**（未加 `-W error`）；
- CI 不执行 Docker build，也不部署到华为云，仅做质量门禁。