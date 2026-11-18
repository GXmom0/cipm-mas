# 华为云部署说明（CIPM-MAS）

本文说明如何把业务中台（FastAPI）打包为 Docker 镜像、推送到华为云 SWR，并接入 AgentArts / Agent Runtime。前端 Streamlit 可独立成第二个镜像。

## 1. 前置条件

- 华为云账号已开通 SWR、ECS 或 CCE、OBS、AgentArts
- 本地已安装 Docker 24+
- 已创建 SWR 组织（命名空间），例如 `cipm`
- 区域以 `cn-north-4`（北京四）为例，其他区域替换域名即可

## 2. 运行时环境变量

| 变量 | 示例 | 说明 |
|---|---|---|
| `CIPM_RUNTIME` | `agentarts` | `local` 为演示模式；其他值启用 LLM 决策链 |
| `CIPM_MOCK` | `0` | 云端关闭 Mock 数据源 |
| `CIPM_LLM_ENDPOINT` | `https://api.deepseek.com/v1` 或盘古/ModelArts 推理地址 | OpenAI 兼容端点，客户端自动拼 `/chat/completions` |
| `CIPM_LLM_MODEL` | `deepseek-chat` / 盘古模型名 | 推理模型 |
| `CIPM_LLM_API_KEY` | `cred://cipm-llm` | 密钥建议使用 CSMS 引用，由部署环境注入 |
| `CIPM_LLM_TIMEOUT_SECONDS` | `30` | 单次调用超时 |
| `CIPM_LLM_MAX_RETRIES` | `2` | 5xx/网络错误重试次数 |
| `CIPM_LLM_TEMPERATURE` | `0.2` | 采样温度 |
| `CIPM_AGENTARTS_ENDPOINT` | `https://agentarts.cn-north-4.myhuaweicloud.com` | 编排平台地址 |
| `CIPM_AGENTARTS_PROJECT_ID` | `proj-xxxx` | 工作空间/项目编号 |
| `CIPM_AUDIT_DIR` | `/app/data/audit` | 审计 JSONL 目录，建议挂载 EVS/OBS |
| `CIPM_TRACE_EXPORT` | `file` | 本地文件；云端可扩展 APM/LTS |

安全要求：

1. 镜像内不写入任何密钥；使用 CCE Secret、ECS 环境变量或 CSMS 引用注入。
2. `CIPM_LLM_API_KEY` 在日志中会被 `redact()` 脱敏，但不要在业务代码中打印。
3. 审计文件为只追加，生产环境需挂载持久卷并配置 WORM/归档策略（留存 ≥ 2 年）。

## 3. 本地构建与运行

```bash
docker build -t cipm-mas:0.1.0 .
docker run --rm -p 8000:8000 \
  -e CIPM_RUNTIME=local \
  -e CIPM_MOCK=1 \
  -v "%cd%/data:/app/data" \
  cipm-mas:0.1.0
```

验证：

```bash
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:8000/api/v1/dashboard
```

云端 LLM 模式（不要在命令行明文写密钥，示例仅用于本地联调）：

```bash
docker run --rm -p 8000:8000 \
  -e CIPM_RUNTIME=agentarts \
  -e CIPM_MOCK=0 \
  -e CIPM_LLM_ENDPOINT=https://api.deepseek.com/v1 \
  -e CIPM_LLM_MODEL=deepseek-chat \
  -e CIPM_LLM_API_KEY="$CIPM_LLM_API_KEY" \
  cipm-mas:0.1.0
```

## 4. 推送到华为云 SWR

```bash
docker tag cipm-mas:0.1.0 swr.cn-north-4.myhuaweicloud.com/cipm/cipm-mas:0.1.0
docker login -u cn-north-4@<AK> -p <登录密钥> swr.cn-north-4.myhuaweicloud.com
docker push swr.cn-north-4.myhuaweicloud.com/cipm/cipm-mas:0.1.0
```

登录密钥请在 SWR 控制台“长期登录指令”中获取，不要写入脚本或提交到仓库。

## 5. 部署到 CCE

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cipm-platform-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: cipm-platform-api
  template:
    metadata:
      labels:
        app: cipm-platform-api
    spec:
      containers:
        - name: api
          image: swr.cn-north-4.myhuaweicloud.com/cipm/cipm-mas:0.1.0
          ports:
            - containerPort: 8000
          env:
            - name: CIPM_RUNTIME
              value: agentarts
            - name: CIPM_MOCK
              value: "0"
            - name: CIPM_LLM_ENDPOINT
              value: https://api.deepseek.com/v1
            - name: CIPM_LLM_MODEL
              value: deepseek-chat
            - name: CIPM_LLM_API_KEY
              valueFrom:
                secretKeyRef:
                  name: cipm-llm
                  key: api-key
          readinessProbe:
            httpGet:
              path: /api/v1/health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 15
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: "2"
              memory: 2Gi
          volumeMounts:
            - name: audit
              mountPath: /app/data
      volumes:
        - name: audit
          persistentVolumeClaim:
            claimName: cipm-audit-pvc
```

创建 Secret：

```bash
kubectl create secret generic cipm-llm --from-literal=api-key="$CIPM_LLM_API_KEY"
```

## 6. 接入 AgentArts / Agent Runtime

1. 在 AgentArts 工作流中把四个 Agent 映射为节点：巡检 Agent（Tool/Agent 节点）、决策 Agent（Agent 节点，调用 `POST /api/v1/agents/decision/invoke`）、执行 Agent（Tool 节点）、人工复核（Human 节点）。
2. 决策节点请求体：

```json
{
  "taskNo": "PT-20261113-0001",
  "plotNo": "PLOT-0912",
  "plotName": "呼图壁示范田-东区",
  "areaMu": 120.0,
  "remainingDays": 20,
  "phenology": "flower_boll",
  "irrigation": "drip",
  "zones": [{"zoneNo": "Z01", "stressLevel": "heavy", "areaMu": 10.0}]
}
```

3. 平台返回统一信封；`data.allowed=false` 表示 LLM 建议被本地规则沙箱拦截，`data.auditEventId` 指向 `LLM_ERROR` 审计记录。工作流应在该分支进入人工专家节点，不得继续下发。
4. Agent Runtime 侧将 `sdk/agent_trace.py` 的 `agentRunId` 替换为平台真实运行 ID；当前本地实现生成 `run_local_*` / `run_platform_*` 前缀，便于日志检索。
5. 健康检查与就绪探针统一使用 `GET /api/v1/health`。

## 7. Streamlit 前端镜像（独立于 API 镜像）

仓库中的 `Dockerfile` **仅为 API 镜像**，只暴露 8000，不会启动 8501。前端请使用仓库已提供的 `Dockerfile.ui`：

```bash
docker build -f Dockerfile.ui -t cipm-mas-ui:0.1.0 .
docker run --rm -p 8501:8501 \
  -e CIPM_MOCK=1 \
  -e CIPM_API_BASE=http://<api-host>:8000 \
  cipm-mas-ui:0.1.0
```

- API：`docker build -t cipm-mas-api:0.1.0 .`
- 前端：`docker build -f Dockerfile.ui -t cipm-mas-ui:0.1.0 .`
- 本地不容器化时：`python ops/start_dev.py`（或 Linux/macOS 下 `bash ops/start_demo.sh`）会同时启动 8000 与 8501。

前端容器建议置于内网 ELB 之后，不对公网直接暴露。

## 8. 常见问题

| 问题 | 处理 |
|---|---|
| 镜像构建时 `pip install` 失败 | 确认基础镜像与 SWR 区域架构一致（x86_64 / ARM）；如需加速可配置华为云 PyPI 镜像源 |
| 健康检查失败 | 查看容器日志；确认 `CIPM_MOCK=0` 时 LLM 配置齐全，否则启动即失败 |
| 决策接口返回 409 | 说明 `CIPM_RUNTIME=local`；云端必须改为 `agentarts` |
| LLM 调用超时 | 调整 `CIPM_LLM_TIMEOUT_SECONDS`，并确认 VPC/安全组允许访问模型端点 |
| 审计文件权限不足 | 挂载卷需对容器用户可写；建议固定 UID 或在 PVC 初始化时授权 |
| 时区不一致 | 镜像已设置 `TZ=Asia/Shanghai`，接口时间统一 `+08:00` |

## 9. 发布检查清单

- [ ] `CIPM_RUNTIME=agentarts` 且 `CIPM_MOCK=0`
- [ ] LLM 密钥来自 Secret/CSMS，镜像与仓库中无明文
- [ ] `/api/v1/health` 就绪，`/api/v1/dashboard` 可读
- [ ] LLM 违反安全间隔期时返回 `allowed=false` 且产生 `LLM_ERROR` 审计
- [ ] 审计目录挂载持久卷
- [ ] 副本数 ≥2，就绪探针启用
- [ ] 前端 `CIPM_API_BASE` 指向后端内网地址