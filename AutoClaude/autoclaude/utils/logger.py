import hashlib
import logging
import re
import sys
import tempfile
from logging.handlers import RotatingFileHandler
from pathlib import Path


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


# DEF-101（Mac/Windows 相容性 R16）：raw log 檔名由 playbook 作者自訂的
# task.step_id 組成（見 pty_executor.py / prompt_dispatcher.py），在 macOS/Linux
# 上檔名規則寬鬆（僅 / 與 NUL 不合法）完全合法；同一字串若含 Windows 禁用字元
# （< > : " | ? * \）、以空白/句點結尾、或恰為保留裝置名（CON/PRN/...），Windows
# 上 open() 會拋出未捕捉的 OSError，導致該 step 每次重試都對同一個壞檔名再炸一次。
#
# 本檔與 tools/check_ntfs_paths.py（及 tools/git-hooks/pre-commit 的
# _ntfs_seg_bad()）三處各自獨立維護同一份禁用字元/保留裝置名判準（R33
# Architect 架構評估，DEF-101-295）：`autoclaude` 是可獨立 pip 安裝的套件
# （見 AutoClaude/pyproject.toml），不可依賴 monorepo 根層 tools/lib/*.py
# （會讓純 pip 安裝、脫離 monorepo checkout 的情境下失效），故不比照
# tools/lib/bash_probe_spec.py 的「共用資料規格」模式合併。三者一致性由
# tools/tests/test_windows_forbidden_filename_parity.py 機械鎖住。
_WIN_FORBIDDEN_CHARS = frozenset('<>:"|?*\\')
_WIN_RESERVED_NAME_RE = re.compile(r"^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])$", re.IGNORECASE)


def _sanitize_log_filename(name: str) -> str:
    """把檔名淨化為跨平台（含 Windows/NTFS）相容格式。"""
    sanitized = "".join(
        "_" if ch in _WIN_FORBIDDEN_CHARS or ord(ch) < 0x20 or ord(ch) == 0x7F else ch
        for ch in name
    )
    sanitized = sanitized.rstrip(" .") or "untitled"
    stem = sanitized.split(".", 1)[0]
    if _WIN_RESERVED_NAME_RE.match(stem):
        sanitized = f"_{sanitized}"
    return sanitized


# 串流寫入給 PTY 輸出的原始 log
class RawStreamLogger:
    def __init__(self, path: Path):
        safe_path = path.with_name(_sanitize_log_filename(path.name))
        try:
            self._file = open(safe_path, "ab")
        except OSError as exc:
            # 縱深防禦：淨化後仍失敗（如目標目錄不存在等非檔名成因）時，fallback
            # 改寫入系統暫存目錄（幾乎必存在可寫），避免整個 playbook 執行崩潰。
            digest = hashlib.sha256(path.name.encode("utf-8", errors="replace")).hexdigest()[:12]
            fallback = Path(tempfile.gettempdir()) / f"playbook_fallback_{digest}.log"
            logging.getLogger("autoclaude.utils.logger").warning(
                "RawStreamLogger: 開啟 log 檔 %s 失敗（%s），改用安全檔名 %s",
                safe_path, exc, fallback,
            )
            self._file = open(fallback, "ab")

    def write(self, data: bytes) -> None:
        self._file.write(data)
        self._file.flush()

    def close(self) -> None:
        self._file.close()
