# frontend（薄封装入口）

本目录不存放业务代码，仅作为前端入口的说明与后续启动脚本挂载点。

- 前端正式实现：`apps/console/`（Streamlit 四阶段仪表盘）
- 归属模块：M11；计划任务：T05
- 本地启动：`CIPM_MOCK=1 python ops/start_dev.py --ui-only`

禁止在本目录复制或另建一套前端实现，避免与 `apps/console/` 出现双份代码。