# Python 3.14 依赖兼容性实测记录

实测环境：Windows 11 / Python 3.14.4

| 依赖 | 结论 | 说明 |
|------|------|------|
| pydantic | 可导入 | 契约层与 Mock 数据自检使用 |
| fastapi | 可导入 | 中台骨架（T04）使用 |
| uvicorn | 可导入 | 本地服务启动 |
| httpx | 可导入 | 后续外部适配层使用 |
| pytest | 可导入 | 单测与门禁 |
| pydantic_settings | 未安装 | 配置层改用标准库 os + .env 解析，不引入该依赖 |
| streamlit | 未安装 | 列入 `[project.optional-dependencies].ui`，前端 T05 前安装；3.14 无 wheel 时在 3.12 虚拟环境运行 |
| rasterio / gdal / numpy / faiss | 未安装 | 列入 `geo` 可选组，影像解析服务后续单独容器化并固定 Python 3.11 |

## 结论

本批（T01/T02/T03/T10.0）全部代码仅依赖标准库 + pydantic + pytest，零外部服务即可运行与测试。科学计算二进制库不进入本机依赖，避免 3.14 无预编译 wheel 导致的安装失败。