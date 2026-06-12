import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


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

    console_handler = logging.StreamHandler(sys.stdout)
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
