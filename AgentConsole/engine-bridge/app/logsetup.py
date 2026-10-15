"""Bridge 的日誌設定：每一行都帶 `trace_id`，可選寫滾動檔案（契約 v1.2 §3.1.1；C-12、C-16）。

此前 `bridge.*` logger 沒有任何 handler（Python 的 lastResort 只印 WARNING 以上的裸訊息），
uvicorn 的存取日誌又是另一套格式、也沒有 traceId——NFR-9.4-04「日誌帶 traceId」無從落實。做法：

  · root logger 掛 stderr handler（`docker compose logs` 看得到）；`BRIDGE_LOG_DIR` 有值時另掛
    `bridge.log` 滾動檔（UTC 午夜切檔、保留 7 份，與 console-api 的 `console.log` 同義）。
    兩個 handler 共用同一個 filter＋formatter，所以每一行都有 `trace_id=…`。
    filter 掛在 **handler** 而不是 logger：logger 層的 filter 對子 logger 傳上來的 record 不生效。
  · uvicorn 的 `uvicorn`／`uvicorn.access` 本來各有 handler 與格式：清掉、改傳播到 root，存取日誌
    （`POST /autoclaude/runs … 201`）因此同格式、同樣帶 trace_id。
  · 一筆日誌一行：訊息與 traceback 內的換行改寫成字面的 `\\n`，所以「每一行」真的每一行都有
    trace_id（否則 `logger.exception` 的 traceback 續行會沒有）。
  · 時間戳為 UTC、帶 `Z`。

寫檔失敗（卷唯讀、權限不對）只在 stderr 留一則警告，Bridge 照常啟動：日誌檔不是服務可用性的前提。
Windows 行為＝TimedRotatingFileHandler 換檔時以 rename 改名；只有 Bridge 一個行程開著該檔。
"""
from __future__ import annotations

import logging
import logging.handlers
import sys
import time
from pathlib import Path
from typing import Any

from .tracing import trace_id_var

LOG_FILE_NAME = "bridge.log"
LOG_BACKUP_COUNT = 7
LOG_FORMAT = "%(asctime)s %(levelname)-5s [%(name)s] trace_id=%(trace_id)s %(message)s"
_INSTALLED_ATTR = "_bridge_log_handler"


class TraceIdFilter(logging.Filter):
    """把當下 contextvar 的 trace id 寫進 record（沒有請求上下文＝`-`）。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = trace_id_var.get()
        return True


class OneLineFormatter(logging.Formatter):
    """UTC＋`Z` 的時間戳；訊息與 traceback 的換行寫成字面 `\\n`（一筆日誌恆為一行）。"""

    converter = time.gmtime

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        stamp = time.strftime("%Y-%m-%dT%H:%M:%S", self.converter(record.created))
        return f"{stamp}.{int(record.msecs):03d}Z"

    def format(self, record: logging.LogRecord) -> str:
        return super().format(record).replace("\r", "").replace("\n", "\\n")


class _StderrHandler(logging.StreamHandler):
    """每次寫入才取 `sys.stderr`：測試框架與 uvicorn 會換掉它，建立時就綁住會寫進已關閉的串流。"""

    def __init__(self) -> None:
        logging.Handler.__init__(self)

    @property
    def stream(self) -> Any:
        return sys.stderr


def teardown_logging() -> None:
    """移除（並關閉）本模組裝的 handler；別人（pytest caplog 等）裝的不動。"""
    root = logging.getLogger()
    for handler in [h for h in root.handlers if getattr(h, _INSTALLED_ATTR, False)]:
        root.removeHandler(handler)
        handler.close()


def setup_logging(log_dir: Path | None) -> None:
    """冪等：每次呼叫都先拆掉上一套再裝新的（lifespan 啟動時呼叫；測試間用 teardown 清場）。"""
    teardown_logging()
    handlers: list[logging.Handler] = [_StderrHandler()]
    file_error: OSError | None = None
    if log_dir is not None:
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.handlers.TimedRotatingFileHandler(
                log_dir / LOG_FILE_NAME, when="midnight", utc=True,
                backupCount=LOG_BACKUP_COUNT, encoding="utf-8"))
        except OSError as exc:
            file_error = exc
    formatter = OneLineFormatter(LOG_FORMAT)
    root = logging.getLogger()
    for handler in handlers:
        handler.setFormatter(formatter)
        handler.addFilter(TraceIdFilter())
        setattr(handler, _INSTALLED_ATTR, True)
        root.addHandler(handler)
    logging.getLogger("bridge").setLevel(logging.INFO)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
    uvicorn_logger = logging.getLogger("uvicorn")
    if uvicorn_logger.level == logging.NOTSET:       # `python -m app.main` 時沒人設過等級
        uvicorn_logger.setLevel(logging.INFO)
    if file_error is not None:
        logging.getLogger("bridge.logsetup").warning(
            "BRIDGE_LOG_DIR=%s 無法寫入（%s）：只輸出到 stderr，沒有檔案日誌", log_dir, file_error)
