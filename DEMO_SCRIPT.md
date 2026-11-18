# 3 分钟答辩演示脚本（Demo Script）

> 目标：用 3 分钟讲清两件事——**四个 Agent 如何协作**，以及**大模型幻觉如何被本地规则沙箱拦截**。

## 0. 演示前 5 分钟准备

```bash
# Windows PowerShell
venv\Scripts\Activate.ps1
$env:CIPM_MOCK="1"

# Linux / macOS / Git Bash
# source venv/bin/activate
# export CIPM_MOCK=1
python -m mock.cli --write
python ops/start_dev.py
# Linux / macOS 也可直接：bash ops/start_demo.sh
```

打开两个窗口：

1. 浏览器：`http://127.0.0.1:8501`（仪表盘）
2. 终端 A：准备执行演示命令

备用终端 B（离线回放，不依赖网络）：

```bash
python -m workflows.local.runtime_demo --runtime agentarts --demo-llm --scenario normal_plot
```

## 1. 时间轴（总 180 秒）

| 时间 | 环节 | 画面 | 一句话讲稿 |
|---|---|---|---|
| 0:00–0:20 | 开场与定位 | 仪表盘顶部 | “这是面向新疆棉田的低空植保决策系统，四个 Agent 完成巡田到评估的闭环。” |
| 0:20–0:50 | 四阶段与四类标识 | 四阶段表格 | “5 个地块、四类业务标识：阻断、降级、拒绝、重排，一屏看清风险。” |
| 0:50–1:15 | 场景 3：置信度阻断 | PLOT-0913 行 | “Z03 置信度 0.62，任务级整体阻断，处方入口直接禁用。” |
| 1:15–1:40 | 场景 4：安全间隔拒绝 | PLOT-0914 行 | “距采收 5 天、安全间隔 7 天，系统直接拒绝，不给豁免入口。” |
| 1:40–2:20 | 多智能体流转 | 终端日志 | “巡检→决策→执行→评估，每条日志带同一个 AgentRun，流转可追溯。” |
| 2:20–2:50 | 幻觉拦截 | 终端 + 审计文件 | “真实大模型的建议也必须过本地规则；违规即拦截并写 LLM_ERROR。” |
| 2:50–3:00 | 收尾 | README_CLOUD 或架构图 | “同一份代码可打包上华为云 AgentArts，规则红线不随模型漂移。” |

## 2. 逐段操作与预期

### 0:00–0:20 开场

操作：不做操作，停在仪表盘首屏。

讲稿：

> “新疆棉田的植保难点不是缺数据，而是缺可执行、可合规的处方。我们把流程拆成四个角色 Agent：巡检负责识别，决策负责开方，执行负责下发，评估负责闭环。所有红线由本地确定性规则守住，大模型只提供建议。”

### 0:20–0:50 四阶段总览

操作：指向四阶段表与业务标识列。

预期：`PLOT-0912` 无标识；`PLOT-0915` 降级；`PLOT-0913` 阻断；`PLOT-0914` 拒绝；`PLOT-0916` 待重新排期。

讲稿：

> “四阶段是巡田、处方、作业、评估。异常不是弹窗，而是结构化标识，直接对应业务处置：复核、专家确认、重开处方、重新排期。”

### 0:50–1:15 置信度阻断

操作：指向 `PLOT-0913`，点击「查看处方」展示禁用态与提示。

预期：按钮不可点击，提示“识别结果待人工复核，处方生成已暂停”；待办区出现 Z03 复核。

讲稿：

> “巡检 Agent 输出等级时同时给出 NDVI 偏离或虫口密度证据。置信度低于 0.7，系统不是‘提醒一下’，而是任务级整体阻断，下游决策链完全暂停，杜绝部分分区偷偷开方。”

### 1:15–1:40 安全间隔拒绝

操作：指向 `PLOT-0914` 与异常提示。

预期：剩余 5 天、安全间隔 7 天，状态「已拒绝」。

讲稿：

> “这是最硬的一条红线：采收剩余天数小于安全间隔期，直接拒绝。替代药剂只作为提示，系统不会自动换药放行，也不存在‘强制下发’入口。”

### 1:40–2:20 多智能体流转

操作：终端执行

```bash
python -m workflows.local.runtime_demo --runtime agentarts --demo-llm --scenario normal_plot
```

预期日志：

```text
[AgentRun: run_local_xxx] 巡检Agent 正在解析影像... plot=PLOT-0912
[AgentRun: run_local_xxx] 巡检Agent 正在生成可解释指标与置信度...
[AgentRun: run_local_xxx] 巡检Agent 完成，流转至下一节点 -> 决策Agent（识别结果已冻结）
[AgentRun: run_local_xxx] 决策Agent 正在调用 LLM 生成处方建议... model=mock-replay
[AgentRun: run_local_xxx] 决策Agent 正在执行本地规则校验（单剂复配 + 安全间隔期）...
[AgentRun: run_local_xxx] 决策Agent 完成，流转至下一节点 -> 执行Agent（本地规则沙箱校验通过）
[AgentRun: run_local_xxx] 执行Agent 正在组装作业指令并下发...
[AgentRun: run_local_xxx] 评估Agent 正在回溯作业效果并计算缓解率...
```

讲稿：

> “注意每一行都带同一个 AgentRun 编号，这是答辩里最直观的多智能体协作证据。决策 Agent 先调用模型，再调用本地规则，最后才流转到执行。”

### 2:20–2:50 幻觉拦截

操作：终端执行

```bash
python -m workflows.local.runtime_demo --runtime agentarts --demo-llm --scenario safety_conflict_plot
```

预期：

```text
[AgentRun: ...] 决策Agent LLM 建议被安全沙箱拦截，已写入 LLM_ERROR 审计。 audit=AUD-xxxx
决策结论：refused；沙箱放行：False
```

随后打开 `data/audit/` 下当天 JSONL，展示 `eventType=LLM_ERROR`、`result=rejected`、`beforeValue.llmSuggestion` 与违规明细。

讲稿：

> “模型可以编，但编不过规则。它给的建议里安全间隔是 7 天，而地块只剩 5 天；沙箱用本地纯函数重算后直接拒绝，并把模型原始建议和违规原因一起写进只追加审计。这就是工业级 AI 的安全边界。”

### 2:50–3:00 收尾

操作：切到 README_CLOUD.md 或架构图。

讲稿：

> “同一份代码可以打包为 Docker 镜像推到华为云 SWR，接入 AgentArts 工作流；云端只切换运行时，红线判定始终在本地。”

## 3. 应急预案

| 风险 | 现场处理 |
|---|---|
| 网络不可用 / LLM 超时 | 使用 `--demo-llm` 离线回放，讲稿不变；说明内置回放与真实客户端共用同一沙箱 |
| 端口 8501/8000 被占用 | `python ops/start_dev.py` 会提示端口冲突，改用 `--ui-only` 或换端口 |
| 仪表盘未加载 | 直接展示 `curl http://127.0.0.1:8000/api/v1/dashboard` 的统一信封 |
| 审计文件为空 | 先跑一次场景 4 或拦截演示；审计只在拒绝/违规/业务变更时写入 |
| 时间被压缩到 2 分钟 | 保留 0:20–0:50、1:15–1:40、2:20–2:50 三段 |

## 4. 评委可能追问

1. **“大模型会不会绕过规则？”**
   不会。规则函数在进程内、只接受结构化输入，LLM 输出必须先通过 `PrescriptionSafetySandbox`；沙箱不读取模型自报的安全间隔期。
2. **“为什么不用 RAG 直接让模型判断？”**
   红线要求可复现、可审计、不可豁免，数值边界必须确定性实现；模型用于生成候选与解释。
3. **“复配怎么办？”**
   V1.0 硬拦截并转人工专家；安全间隔取组合最长值，由专家手工执行，不自动下发。
4. **“云端怎么部署？”**
   镜像推 SWR，CCE 多副本 + Secret；决策节点通过 `/api/v1/agents/decision/invoke` 接入 AgentArts。
5. **“数据从哪来？”**
   当前为固定种子 Mock 演示集；适配层已预留 OSS、MQTT、设备 REST 接口，P1 替换真实数据源。