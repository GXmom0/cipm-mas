FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Shanghai \
    CIPM_RUNTIME=local \
    CIPM_MOCK=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY apps ./apps
COPY agents ./agents
COPY domain ./domain
COPY adapters ./adapters
COPY sdk ./sdk
COPY mock ./mock
COPY knowledge ./knowledge
COPY workflows ./workflows
COPY ops ./ops

RUN pip install --no-cache-dir .

RUN mkdir -p /app/data/audit
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)"

CMD ["uvicorn", "apps.platform_api.main:app", "--host", "0.0.0.0", "--port", "8000"]