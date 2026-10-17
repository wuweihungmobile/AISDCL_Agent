"""FSM 專案名規則（ADR-XPLAT-016 §7.4；體檢 S-10）：`sanitize_component` 的逐字鏡像＋輸出域判準。

為什麼自帶一份：Bridge 與 AISDLC_SDD 同屬 monorepo、不同子專案，不 import（ADR-XPLAT-010 §2.1）。
SDD 側 `AISDLC_SDD/scripts/component_sanitizer.py::sanitize_component` 產生狀態檔名
（`FSM-STATE-<名>.yaml`）；Bridge 要能列出、讀取它產生的**每一個**檔名，所以規則必須與它同源。
一致性由 tests/test_fsm_names.py 以「依路徑載入 component_sanitizer」逐樣本對拍（F-8），
SDD 側改規則時對拍會紅，不靠人記得同步。

兩個公開函式：
  · `fsm_component(name)`：淨化（一般情況冪等，唯一已知的上游例外見該函式）。進入 Bridge 的
    專案名（body、路徑參數、`sdd.fsm_project`）一律先過它，所以傳原名與傳已淨化的鍵等價。
  · `is_fsm_project_name(name)`：淨化輸出域的判準，用在「磁碟上的檔名片段」（`GET /sdd/fsm` 清單）。
    取代舊的 `^[A-Za-z0-9._-]{1,128}$`，那條會把 CJK、空白、括號、`+`、`@` 的專案名一律拒成 404／
    errors。

Windows 行為＝`< > : " | ? * \\` 與控制字元是 NTFS 禁用字元，淨化時換成 `_`；保留裝置名（CON、
NUL、COM1…）加 `_` 前綴。POSIX 上這些規則一樣套用（檔名要能被 Windows checkout，也要能被 git 的
NTFS 閘接受）。
"""
from __future__ import annotations

import re
import unicodedata

_WIN_FORBIDDEN_CHARS = frozenset('<>:"|?*\\')
_WIN_RESERVED_NAME_RE = re.compile(
    r"^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9]|CONIN\$|CONOUT\$|COM[¹²³]|LPT[¹²³])$", re.IGNORECASE)
#: FSM state 檔名單一 component 的長度上限（前後綴留餘裕；與 SDD 側同值，由對拍測試守）。
MAX_COMPONENT_LEN = 80


def _is_unsafe_char(ch: str) -> bool:
    return ch in _WIN_FORBIDDEN_CHARS or ch == "/" or ord(ch) < 0x20 or ord(ch) == 0x7F


def fsm_component(name: str) -> str:
    """淨化成可當 `FSM-STATE-<名>.yaml` 檔名片段的鍵；一般情況冪等（例外見下）。

    唯一已知例外是上游邊界：名稱長於 80 字、且第 80 字落在 Unicode 空白之前時，截斷後的
    結果以空白結尾，再淨化一次會被開頭的 `strip()` 吃掉。鏡像必須與 SDD 逐字同源，所以這
    裡不修，只在 tests/test_fsm_names.py 釘住現況。

    步驟（與 `sanitize_component` 逐步相同）：NFC → strip → 把禁用字元／分隔符／控制字元換成 `_`
    → 截 80 → `rstrip(" .")`（吃光就退成 `untitled`）→ 若 stem 是 Windows 保留裝置名則加 `_` 前綴
    並重截。
    """
    s = unicodedata.normalize("NFC", str(name)).strip()
    sanitized = "".join("_" if _is_unsafe_char(ch) else ch for ch in s)
    if len(sanitized) > MAX_COMPONENT_LEN:
        sanitized = sanitized[:MAX_COMPONENT_LEN]
    # 路徑穿越防禦：純句點片段（".."／"."）在這一步被吃光，退成 "untitled"，不會留下穿越 token。
    sanitized = sanitized.rstrip(" .") or "untitled"
    # 保留裝置名檢查看 stem（"CON .txt" 的 stem 帶尾隨空白，Win32 解析裝置名時會忽略它）。
    stem = sanitized.split(".", 1)[0].rstrip(" ")
    if _WIN_RESERVED_NAME_RE.match(stem):
        sanitized = f"_{sanitized}"
        if len(sanitized) > MAX_COMPONENT_LEN:
            sanitized = sanitized[:MAX_COMPONENT_LEN].rstrip(" .")
    return sanitized


def is_fsm_project_name(name: object) -> bool:
    """`name` 是否落在 `fsm_component` 的輸出域（可安全當狀態檔名片段）。

    判準（ADR §7.4）：非空；已是 NFC；長度 ≤ 80；不是 `.`／`..`；不含 `< > : " ? * \\ /`、豎線、
    控制字元、DEL；不以空白開頭；不以 `.` 或 ASCII 空白結尾。

    🔴 與 ADR 字面的一處刻意差異（交卷時列給主控）：ADR 寫「無前後空白」，但 `fsm_component` 在
    **截斷到 80 字之後**只做 `rstrip(" .")`——輸入 `a`＋大量全形空白（U+3000）時，輸出會以 U+3000
    結尾，照字面的「無尾端空白」判準會把 sanitizer 自己的輸出拒掉，違反 F-8（sanitizer 的任何輸出
    都被接受）。所以尾端判準取 `rstrip(" .")` 的不動點（與 sanitizer 同一個不動點）；前導空白一律
    拒（sanitizer輸出不可能以空白開頭，手工放進來的檔名才會）。尾端的 Unicode 空白不構成穿越或平台
    檔名風險。
    """
    if not isinstance(name, str) or not name or len(name) > MAX_COMPONENT_LEN:
        return False
    if not unicodedata.is_normalized("NFC", name):
        return False
    if any(_is_unsafe_char(ch) for ch in name):
        return False
    if name != name.lstrip():
        return False
    return name.rstrip(" .") == name
