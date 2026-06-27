import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


class _EncodingSafeStreamHandler(logging.StreamHandler):
    """console handler：依目標 stream 編碼 sanitize，杜絕 Windows cp950 對非 ASCII
    （如 ✓ U+2713）丟 UnicodeEncodeError 的非致命噪音（DEF-87-002）。

    utf-8 環境 sanitize 為無損 → 零退化；sanitize 為純函式 → 冪等。
    可用 io.TextIOWrapper(BytesIO, encoding="cp950") 在 utf-8 平台重現 cp950 行為。
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            stream = self.stream
            enc = getattr(stream, "encoding", None) or "utf-8"
            # backslashreplace → 不可編碼字元轉 \uXXXX（純 ASCII），保證後續 write 必可編碼
            safe = msg.encode(enc, errors="backslashreplace").decode(enc, errors="replace")
            stream.write(safe + self.terminator)
            self.flush()
        except RecursionError:  # 鏡像 CPython StreamHandler.emit：RecursionError 須上拋防無限遞迴
            raise
        except Exception:
            self.handleError(record)


def setup_logger(log_dir: str = "logs", level: int = logging.DEBUG) -> logging.Logger:
    root = logging.getLogger("autoclaude")
    root.setLevel(level)

    # 避免重複註冊 handler（pytest / REPL 多次匯入時導致雙倍輸出）
    if root.handlers:
        return root

    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_path / "autoclaude.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.DEBUG)

    console_handler = _EncodingSafeStreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)
    console_handler.setLevel(logging.INFO)

    root.addHandler(file_handler)
    root.addHandler(console_handler)
    return root


# 串流寫入給 PTY 輸出的原始 log
class RawStreamLogger:
    def __init__(self, path: Path):
        self._file = open(path, "ab")

    def write(self, data: bytes) -> None:
        self._file.write(data)
        self._file.flush()

    def close(self) -> None:
        self._file.close()
