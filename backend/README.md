# backend（薄封装入口）

本目录不存放业务代码，仅作为后端入口的说明与后续启动脚本挂载点。

- 后端正式实现：`apps/platform_api/`（FastAPI 业务中台）
- 作业窗口独立服务：`apps/window_service/`（M06，T11）
- 归属模块：M11；计划任务：T04
- 本地启动：`CIPM_MOCK=1 python ops/start_dev.py --api-only`

禁止在本目录复制或另建一套中台实现，避免与 `apps/platform_api/` 出现双份代码。