# Engine Bridge 映像。🔴 build context 必須是 monorepo 根（要 COPY 兄弟目錄 AutoClaude/）：
#   docker build -f AgentConsole/engine-bridge/Dockerfile -t aisdlc-engine-bridge:dev .
# 實際進 context 的檔案由同目錄的 Dockerfile.dockerignore 限定（只放行 AutoClaude/ 與本目錄）。
#
# 映像**不含** Claude Code CLI（`claude`）：全棧 Docker 下的 E2E 一律用映像內建的確定性替身
# `aisdlc-mock-claude`（config_overrides.claude.command）；要跑真 Claude 請用本機模式
# （README〈本機模式〉），或自行在此映像之上擴充安裝 CLI。
# `/sdd/*` 需要 AISDLC_SDD 目錄：映像不含它，compose 以唯讀 volume 掛進來並設 SDD_ROOT。
# 基底映像可用 --build-arg PYTHON_IMAGE=… 覆寫（離線／只有快取映像的機器上驗證建置步驟用）。
ARG PYTHON_IMAGE=python:3.11-slim
FROM ${PYTHON_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    AUTOCLAUDE_ROOT=/opt/AutoClaude \
    ENGINE_WORKSPACE=/workspace \
    BRIDGE_PORT=8081

WORKDIR /opt
COPY AutoClaude/ /opt/AutoClaude/
COPY AgentConsole/engine-bridge/ /opt/engine-bridge/

# 兩個套件都用非 editable 安裝（deps 版本由各自 pyproject 鎖定）；以非 root 使用者執行。
RUN pip install /opt/AutoClaude /opt/engine-bridge \
 && useradd --create-home --uid 10001 bridge \
 && mkdir -p /workspace \
 && chown bridge:bridge /workspace

USER bridge
WORKDIR /opt/engine-bridge
VOLUME ["/workspace"]
EXPOSE 8081

# slim 映像沒有 curl，用 Python 標準庫探測 /health（以 BRIDGE_PORT 為準）。
HEALTHCHECK --interval=15s --timeout=4s --start-period=15s --retries=3 \
  CMD ["python", "-c", "import os,sys,urllib.request as u; sys.exit(0 if u.urlopen('http://127.0.0.1:%s/health' % os.environ.get('BRIDGE_PORT','8081'), timeout=3).status == 200 else 1)"]

# 單一 worker（run 登記表與行程監督都在記憶體內）；SSE 長連線給 5 秒優雅關閉。
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${BRIDGE_PORT:-8081} --timeout-graceful-shutdown 5"]
