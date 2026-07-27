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
# （< > : " | ? * \）、以空白/句點結尾、或恰為保留裝置名（CON/PRN/...），在 Windows
# 上會出問題，故一律淨化。
#
# R58 訂正（DEF-101-B13）：本段原文寫「Windows 上 open() 會拋出未捕捉的 OSError，
# 導致該 step 每次重試都對同一個壞檔名再炸一次」——這個機制敘述**已被實測部分證偽**，
# 三種輸入的真實下場不同（原生 Windows 11 + git 2.51.0.windows.1 以 raw Win32
# ctypes CreateFileW + GetFileType 實測；完整量測與覆核指令見
# tools/check_ntfs_paths.py 檔頭〈實測機制〉）：
#   ① 保留裝置名帶目錄前綴（log 檔一律帶 log_dir 前綴，即本函式的實際使用情境）：
#      Win32 **建成普通檔案**（`<dir>\CON`、`<dir>\CONIN$`、`<dir>\CON .txt` 實測皆
#      FILE_TYPE_DISK），open() **不會**拋 OSError。真正的危害是 git：`git add` 對
#      這些路徑實測 rc=128（`open(...): No such file or directory` + `unable to index
#      file`），log 產物在 Windows 上永久無法提交／無法被以 git 為載具的 CI 取證。
#      唯一仍是裝置的是 `NUL`（帶目錄前綴仍 FILE_TYPE_CHAR）——寫進去的內容會整份
#      靜默消失，比拋錯更難診斷。
#   ② 尾隨空白／句點：Win32 **靜默剝除改名**（`'x '` 落地成 `x`），不拋錯；後續要讀
#      回原檔名的呼叫端就找不到檔案。
#   ③ 禁用字元 `< > : " | ? * \` 與控制字元：這一類 open() 才真的拋 OSError。
# 淨化行為完全不變（三種下場都是真實危害），只訂正理由。
#
# 本檔與 tools/check_ntfs_paths.py（及 tools/git-hooks/pre-commit 的
# _ntfs_seg_bad()）三處各自獨立維護同一份禁用字元/保留裝置名判準（R33
# Architect 架構評估，DEF-101-295）：`autoclaude` 是可獨立 pip 安裝的套件
# （見 AutoClaude/pyproject.toml），不可依賴 monorepo 根層 tools/lib/*.py
# （會讓純 pip 安裝、脫離 monorepo checkout 的情境下失效），故不比照
# tools/lib/bash_probe_spec.py 的「共用資料規格」模式合併。三者一致性由
# tools/tests/test_windows_forbidden_filename_parity.py 機械鎖住。
#
# 套件內部（同屬 autoclaude 一個 pip 套件）的呼叫端則一律 import 本函式，
# 不得另寫一份：models/escalation.py（EscalationDump.save 組 escalation 檔名）
# 與 plugins/checkpoint/_escalation.py（last_log_path 顯示字串）皆 import
# `_sanitize_log_filename`，理由同上——同一規則被多處獨立實作正是本缺陷類別
# （DEF-101-219／DEF-101-295）反覆復發的根因。
_WIN_FORBIDDEN_CHARS = frozenset('<>:"|?*\\')
# R58 修正（DEF-101-B3，四處同修）：補 `CONIN$`／`CONOUT$`。原清單照「Win32 裝置名
# 解析」推導，漏掉這兩個真正會讓 git 失效的名字——實測 `_sanitize_log_filename('CONIN$')`
# 原樣回傳、未加 `_` 前綴，該 log 檔能在 NTFS 建立但 `git add` rc=128。
# 刻意不收 `CONERR$`（掃描員原提案含它，經實測證偽：裸名為 FILE_TYPE_DISK 普通檔案、
# `git add` rc=0 成功入 index）。`$` 需轉義成 `\$`；`CON` 分支不會搶先匹配 `CONIN$`
# ——pattern 以 `$` 錨定結尾，短分支匹配後錨定失敗會回溯（已實測）。
_WIN_RESERVED_NAME_RE = re.compile(
    r"^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9]|CONIN\$|CONOUT\$)$", re.IGNORECASE
)


def _sanitize_log_filename(name: str) -> str:
    """把檔名淨化為跨平台（含 Windows/NTFS）相容格式。

    `/` 不在 `_WIN_FORBIDDEN_CHARS`（該常數與 `check_ntfs_paths.py`／pre-commit
    的 `_ntfs_seg_bad()` 三處鎖定同一組「已切割路徑片段」的 NTFS 合法性判準，
    `/` 本就是切割用的分隔符，不會出現在單一片段內）；但本函式的輸入是**尚未
    切割**的任意字串（如呼叫端直接組出的完整檔名），`/` 在此脈絡下會被
    `pathlib.Path.__truediv__` 解讀為額外路徑層級，導致產生非預期子目錄，甚至
    `step_id="../../x"` 類輸入造成路徑穿越（R37 QA 一審實測 `PermissionError`）。
    故獨立於 `_WIN_FORBIDDEN_CHARS` 之外，於此額外淨化 `/`，不影響上述三方
    parity 鎖（該鎖比較的是常數本身，不比較本函式的實際淨化行為）。"""
    sanitized = "".join(
        "_" if ch in _WIN_FORBIDDEN_CHARS or ch == "/" or ord(ch) < 0x20 or ord(ch) == 0x7F else ch
        for ch in name
    )
    sanitized = sanitized.rstrip(" .") or "untitled"
    # R57 修正（DEF-101-B1 第 ④ 處，與 AISDLC_SDD/scripts/component_sanitizer.py 同修）：
    # 上一行 rstrip(" .") 作用於整串，對 "NUL .log" 不觸發（結尾是 g），stem 遂為帶
    # 尾隨空白的 "NUL " 而不匹配 ^NUL$ → 保留裝置名整組逃逸。
    # R58 訂正（DEF-101-B13）：本處原寫「Win32 解析裝置名會忽略基底名後的尾隨空白，故
    # 此類檔名在 Windows 上仍撞裝置」——實測證偽（`<dir>\NUL .log` 是 FILE_TYPE_DISK
    # 普通檔案，沒撞到裝置）。忽略尾隨空白的是 **Git for Windows** 的
    # `is_valid_win32_path()`：`git add "<dir>/CON .txt"` 實測 rc=128。攔截行為不變。
    # 只 rstrip(" ") 不含 "."，否則純句點片段的 stem 會被吃空、破壞既有路徑穿越退化為
    # "untitled" 的防禦。
    stem = sanitized.split(".", 1)[0].rstrip(" ")
    if _WIN_RESERVED_NAME_RE.match(stem):
        sanitized = f"_{sanitized}"
    return sanitized


def write_text_with_fallback(path: Path, content: str, fallback_prefix: str) -> Path:
    """原子寫入文字檔（tmp + replace）；`_sanitize_log_filename()` 只淨化禁用字元、
    不截斷長度，超長檔名等非字元因素仍可能讓 `open()` 拋出 OSError——失敗時改寫入
    系統暫存目錄的雜湊檔名，避免內容完全遺失（比照既有 `RawStreamLogger` 的
    fallback 精神，供其他一次性寫入的呼叫端共用，不再各自重寫一份）。"""
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)
        return path
    except OSError as exc:
        digest = hashlib.sha256(path.name.encode("utf-8", errors="replace")).hexdigest()[:12]
        fallback = Path(tempfile.gettempdir()) / f"{fallback_prefix}_{digest}{path.suffix}"
        logging.getLogger("autoclaude.utils.logger").warning(
            "write_text_with_fallback: 寫入 %s 失敗（%s），改用安全檔名 %s",
            path, exc, fallback,
        )
        fallback.write_text(content, encoding="utf-8")
        return fallback


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
