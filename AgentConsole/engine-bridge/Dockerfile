# Engine Bridge 映像。🔴 build context 必須是 monorepo 根（要 COPY 兄弟目錄 AutoClaude/）：
#   docker build -f AgentConsole/engine-bridge/Dockerfile -t aisdlc-engine-bridge:dev .
# 實際進 context 的檔案由同目錄的 Dockerfile.dockerignore 限定（只放行 AutoClaude/ 與本目錄）。
#
# 映像**不含** Claude Code CLI（`claude`）：全棧 Docker 下的 E2E 一律用映像內建的確定性替身
# `aisdlc-mock-claude`（config_overrides.claude.command）；要跑真 Claude 請用本機模式
# （README〈本機模式〉），或自行在此映像之上擴充安裝 CLI。
# `/sdd/*` 需要 AISDLC_SDD 目錄：映像不含它，compose 以唯讀 volume 掛進來並設 SDD_ROOT。
# 基底映像可用 --build-arg PYTHON_IMAGE=… 覆寫（只有快取映像的機器上驗證建置步驟用；
# 但下方的 apt-get 步驟需要能連到 Debian 套件庫）。
ARG PYTHON_IMAGE=python:3.11-slim
FROM ${PYTHON_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    AUTOCLAUDE_ROOT=/opt/AutoClaude \
    ENGINE_WORKSPACE=/workspace \
    BRIDGE_PORT=8081

# 🔴 git 與 ca-certificates（QA DEF-AC-003，P1）：引擎內共 11 處 subprocess 呼叫 git（開機自檢
# boot_self_check 是其中之一）。python:3.11-slim 沒有 git ⇒ 全棧下任何批次一律 FAILED
# （FileNotFoundError: 'git'），而 /health 仍回 200。ca-certificates 供對 HTTPS 外呼（MiniMax）驗證憑證。
# 放在 COPY 之前：程式碼改動不會讓這一層（含 apt 下載）失效。
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*
# 建置期冒煙：git 裝不上或不能執行就讓 build 失敗，不要等到全棧真跑批次才現形。
RUN git --version

WORKDIR /opt
COPY AutoClaude/ /opt/AutoClaude/
COPY AgentConsole/engine-bridge/ /opt/engine-bridge/

# 兩個套件都用非 editable 安裝（deps 版本由各自 pyproject 鎖定）；以非 root 使用者執行。
# /app/logs＝BRIDGE_LOG_DIR 的落點（compose 與 backend 共用 app_logs 卷）。具名卷還空著時，Docker 會把容器映像內該目錄
# 的擁有者與權限複製進卷根；backend 以另一個 uid（1001）寫同一個卷，所以給 1777（同 /tmp：人人可寫、不可刪別人的檔），
# 且 compose 讓 backend 以 :nocopy 掛載——否則最後 create 的 backend 會把卷根蓋成它自己的 0755（docker/README.md〈9〉#32）。
RUN pip install /opt/AutoClaude /opt/engine-bridge \
 && useradd --create-home --uid 10001 bridge \
 && mkdir -p /workspace /app/logs \
 && chown bridge:bridge /workspace /app/logs \
 && chmod 1777 /app/logs

USER bridge
WORKDIR /opt/engine-bridge
VOLUME ["/workspace"]
EXPOSE 8081

# slim 映像沒有 curl，用 Python 標準庫探測（以 BRIDGE_PORT 為準）。探 /health/deep 而不是 /health：
# 深度探針實測 git／autoclaude／工作區可寫／DB（契約 §3.1.1），503 時 urlopen 拋 HTTPError ⇒ 非零離開碼。
# 最壞情況 git（5 秒）加 DB（3 秒）接近 8 秒，所以 urlopen 與 --timeout 都比舊版寬。
HEALTHCHECK --interval=15s --timeout=10s --start-period=15s --retries=3 \
  CMD ["python", "-c", "import os,sys,urllib.request as u; sys.exit(0 if u.urlopen('http://127.0.0.1:%s/health/deep' % os.environ.get('BRIDGE_PORT','8081'), timeout=9).status == 200 else 1)"]

# 單一 worker（run 登記表與行程監督都在記憶體內）；SSE 長連線給 5 秒優雅關閉。
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${BRIDGE_PORT:-8081} --timeout-graceful-shutdown 5"]
