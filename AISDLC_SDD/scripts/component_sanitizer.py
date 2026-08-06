"""跨 AISDLC_SDD 版本共用的檔名片段淨化 SSOT（R45 架構最佳化，DEF-101-358）。

背景：`_sanitize_component()` 曾在每個 Copy-on-Evolve 版本目錄（
`AISDLC_SDD_v0.01`~LATEST）下各自維護一份複本。R38 為 LATEST 強化了 Windows
禁用字元（`< > : " | ? *`）、保留裝置名（CON/PRN/AUX/NUL/COM1-9/LPT1-9）、控制
字元、超長字串四項防護，但凍結版本（v0.01~v0.29）依 Copy-on-Evolve 鐵律不可
原地修改，於是留著早期只擋路徑分隔符 `/`、`\\` 的弱化版（R44 DEF-101-358 記載此
落差）。只要淨化邏輯仍分散在 30 份複本，下一次再發現新的淨化盲點，就得重複打
30 次補丁。

本模組是這個 SSOT 的移出實作：不含任何版本特有狀態，是零業務語意的平台/安全
相容工具函式，比照既有 `AISDLC_SDD/scripts/`（`copy_on_evolve.sh`／
`sdd_version.py`／`cross_version_guard.py` 等）「共享 CI infra，免
Copy-on-Evolve」的既有先例（`EVOLUTION_LOG.md::DEF-15-001`）。每個版本目錄下的
`tools/fsm_runtime/state_loader.py` 改為透過 importlib 依絕對路徑載入本模組
（不透過 sys.path 插入，避免跨版本 import 汙染同一行程的模組快取），薄委派呼叫
`sanitize_component()`。往後同類淨化強化只需改這一處、30 個版本立即同步生效，
不必再逐版走例外補丁流程。

覆蓋強度比照 AutoClaude 側 `autoclaude/utils/logger.py::_sanitize_log_filename()`
（交叉一致性見根層 `tools/tests/test_windows_forbidden_filename_parity.py::
TestSddSanitizeComponentVsLoggerSecurityParity`：比較「危險輸入是否被同等程度擋下」，
不要求輸出完全一致。R69 自 `AISDLC_SDD_v0.30/tools/fsm_runtime/tests/
test_state_component_sanitizer_parity.py` 搬遷至根層整合層——原檔在 AISDLC_SDD 側
import autoclaude，CI 相依缺 pydantic 時被 `try/except ImportError` 收成「8 支永遠
skip」的殭屍）。AISDLC_SDD 與 AutoClaude 是兩個獨立可發布子專案（各自
`releases/` 打包發布機制），依既有先例（`bootstrap_core.py::
_is_windows_apps_stub()` 語言邊界獨立實作）不可跨子專案 import，故本模組獨立
實作、不與 logger.py 共用同一顆函式物件。
"""
from __future__ import annotations

import re
import unicodedata

_WIN_FORBIDDEN_CHARS = frozenset('<>:"|?*\\')
# R60：`CONIN$`／`CONOUT$` 補齊（四處同修）。納入的**證據來源**是 git for Windows 的
# `core.protectNTFS`（只是證據來源，不是本判準要對齊的模型——R77-51 以外接 oracle 逐名
# 對拍後證實兩者在四個樣本上判決相反；實測與裁決見根層 tools/check_ntfs_paths.py 的
# `_RESERVED_RE` 上方 R77-51 段落，本檔不複製第二份證據）
# ——本機實測（Win 11 Pro 26200，拋棄式 repo）`CONIN$.log`／
# `CONOUT$.txt`／`conin$.log`／`CONIN$.tar.gz`／`CONIN$ .log` 全數 Invalid path，
# 含此類檔名的 repo 在 Windows 上 clone rc=128 且工作樹全空；`CLOCK$.txt` 實測 ACCEPT
# 且 clone 正常，故刻意不納入（`CONIN`／`CONIN.log` 少了 `$` 亦非裝置名，正則要求完整 token）。
# 🔴 四個基本裝置名（CON、PRN、AUX、NUL）必須相鄰、新裝置名一律加在清單尾端——根層
# tools/tests/test_windows_forbidden_filename_parity.py 的 repo-wide 錨①要求四者依序出現
# 且間隙 ≤5 字元；R60 初版插在中間，實測讓另三處實作同時掉出該錨、卻因錨②仍命中而全綠。
# R68（四處同修）：追加 Microsoft《Naming Files, Paths, and Namespaces》保留名清單明列的
# 上標變體 `COM¹ COM² COM³ LPT¹ LPT² LPT³`（該文件與 ASCII 數字版並列，成因是 Windows
# 裝置名解析把上標數字視同數字；本機實測 `unicodedata.normalize("NFKC","COM¹")=="COM1"`
# 佐證兩者在相容性分解下同值）。取捨方向刻意選「擋」：若 Windows 實際 ACCEPT，代價僅是
# 對一個沒人會用的檔名多加一個 `_` 前綴；若實際 REJECT 而不擋，代價是整個 clone 壞掉。
# 🔴 R77-51 訂正：R68 當時的證據等級是「官方文件＋靜態分析」並附了一條「真機測到就四處
# 移除」的指示——本輪已在 Win 11 Pro 26200 真機補跑，該條件成立，而它導出的動作**被掌舵者
# 明文推翻**：上標變體與 COM0 的過攔一律保留（過攔是安全方向），只修失實的宣稱。實測數據、
# 裁決與外接 oracle 鎖的位置，見根層 tools/check_ntfs_paths.py 的 R77-51 段落（單一份）。
_WIN_RESERVED_NAME_RE = re.compile(
    r"^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9]|CONIN\$|CONOUT\$|COM[¹²³]|LPT[¹²³])$", re.IGNORECASE
)
# 🔴 R68 三站點長度政策（本處是其中一站，三者治理**不同域**、刻意不相等）：
#   · 本處 80        ← FSM state 檔名**單一 component**（前後綴 FSM-STATE-/-{track}.yaml 留餘裕）
#   · logger.py      ← runtime log 檔名，**刻意不截斷**（見該檔 `write_text_with_fallback`
#                       docstring：淨化字元即可，超長交由 OSError fallback 寫入暫存目錄）
#   · check_ntfs_paths.py 200 fail／180 warn ← tracked git **整條相對路徑**（MAX_PATH 260 減
#                       clone 前綴 59）
# 三者不是「同一政策的三份真相」，把 80 抄進 logger 只會改變既有輸出且無收益。此對照由
# AISDLC_SDD/scripts/tests/test_ntfs_length_gate.py::test_length_policy_three_sites_registry
# 機械釘住（任一數字或「不截斷」設計被單方面改動即紅）。
_MAX_COMPONENT_LEN = 80


def sanitize_component(name: str) -> str:
    """消毒檔名片段，防止誤傳整段路徑當 project/track_id/ac_id/rule_id 等。

    根因防護（arch_fitness FF-3）：曾有呼叫端把整段相對路徑
    （build/reports/fsm/FSM-STATE-AISDLC_SDD.yaml）當 project 傳入，使
    _default_state_path 產生巢狀 FSM-STATE-build/reports/fsm/...yaml.yaml，
    其 .tmp 殘留無法被 save_state 的 reap 回收。剝除路徑分隔符後，
    任何誤用都退化為單層平坦檔名，不再洩漏孤兒。

    R38 深化：本函式亦是 spec_patch_proposer.py 組 SPEC-PATCH-{ac_id}-{date}.md
    的共用消毒點（同目錄下同一缺陷類別的姊妹位置，收斂成單一函式，不各自另寫
    一份，避免重蹈 DEF-101-219/DEF-101-295 反覆復發的根因）。

    R38 四方複審 SD 發現（padding-bypass）：原本「淨化禁用字元 → 保留裝置名
    檢查 → 截斷 → 第二次獨立 rstrip」的順序，在「截斷前 rstrip 因結尾非空白
    不觸發、保留名檢查因此誤判放行」與「截斷後才把露出的空白 rstrip 掉、卻
    不重跑保留名檢查」之間存在順序缺口：輸入「保留名 + 大量空格 + 一個不會被
    rstrip 剝除的字元」且總長超過 `_MAX_COMPONENT_LEN` 時會讓保留名裸露輸出。
    修復：把「淨化禁用字元 → 截斷 → 最終 rstrip → 保留裝置名檢查」收斂成
    單一輪、只做一次，不再先查一次保留名又截斷後不重查。
    """
    # R60（前導空白四處統一決策的第 4 處）：本行的 `.strip()` 同時剝**前導**空白，使本
    # 函式對「前導空白 + 保留名」（' CON.txt'）比另三處**更嚴格**——' CON.txt' 在此變成
    # 'CON.txt' 而被加 `_` 前綴，而 tools/check_ntfs_paths.py、tools/git-hooks/pre-commit
    # 與 autoclaude/utils/logger.py 三處一律放行。此不對稱**刻意保留**，理由分兩層：
    #   ① 前導空白本身不是缺口：git（core.protectNTFS=true）與 Win32 實測皆視 ' CON.txt'
    #      為正常檔名（clone rc=0、四種變體可同時共存於同一目錄），故兩個 validator
    #      加擋它只會新增偽陽性（完整實測見 check_ntfs_paths.py `_RESERVED_RE` 上方註解）。
    #   ② 本函式是**產生**檔名的 sanitizer 而非 validator：多正規化一步永不產生更危險的
    #      輸出，且 `.strip()` 早於本判準存在、負責的是「呼叫端誤傳含前後空白的片段」，
    #      為對齊而拿掉它會改變所有合法輸入的既有輸出（例：' myproject' → ' myproject'）。
    # 此決策由 AISDLC_SDD/scripts/tests/test_component_sanitizer_reserved_trailing_space.py
    # 的 `LEADING_SPACE_RESERVED` 樣本（斷言本處**必須**加前綴）與根層
    # tools/tests/ 對另三處「必須放行」的斷言雙向釘住，任一側翻面即翻紅。
    # R68：先 NFC 正規化再淨化。WHY：本函式是**生成器**，其產物（FSM-STATE-*.yaml／
    # SPEC-PATCH-*.md 等，實查 69 筆已入庫）會被提交，而同 repo 的 tools/check_ntfs_paths.py
    # `_non_nfc_reason()` 對 index 內非 NFC 路徑 fail-closed。Linux／CI runner 上 git 無
    # `core.precomposeunicode`（該設定僅 macOS 生效），NFD 輸入會原樣入 index → 撞自家 NFC 閘。
    # macOS 側因 precomposeunicode 預設 true 而不顯形（實測 `git add` 後 index 恆 NFC），
    # 故此為 **Linux/CI 側**顯形的缺口，不是 macOS 側。對純 ASCII／CJK 零行為變更
    # （`is_normalized("NFC", s)` 對兩者恆真）。
    s = unicodedata.normalize("NFC", str(name)).strip()
    sanitized = "".join(
        "_" if ch in _WIN_FORBIDDEN_CHARS or ch == "/" or ord(ch) < 0x20 or ord(ch) == 0x7F else ch
        for ch in s
    )
    if len(sanitized) > _MAX_COMPONENT_LEN:
        sanitized = sanitized[:_MAX_COMPONENT_LEN]
    # 路徑穿越防禦：`/` `\` 已於上一步淨化；純句點片段（".."／"." 穿越 token）
    # 無其他字元可留，rstrip(" .") 會將其整段吃光，回退為安全的 "untitled"
    # （不會殘留 ".."／"." 這種在未來任何直接當路徑片段使用的呼叫端具穿越意義的字面值）。
    sanitized = sanitized.rstrip(" .") or "untitled"
    # R57 修正（DEF-101-B1 第 ③ 處）：stem 取出後必須再剝一次尾隨空白。上一行的
    # rstrip(" .") 作用於**整串**，對 "CON .txt" 不觸發（結尾是 t），使 stem 成為
    # 帶尾隨空白的 "CON " 而不匹配 ^CON$ → 保留裝置名整組逃逸（實測 'CON .txt'／
    # 'NUL .log'／'LPT1 .yaml' 原本皆原樣輸出、未加 "_" 前綴）。Win32 解析裝置名時
    # 會忽略基底名後的尾隨空白，故這類檔名在 Windows 上仍會撞到裝置。
    # 刻意只 rstrip(" ") 不含 "."：改成 rstrip(" .") 會讓純句點片段（".."／"."）的
    # stem 被吃空成 ""，破壞上方已收斂的路徑穿越退化為 "untitled" 的防禦。
    stem = sanitized.split(".", 1)[0].rstrip(" ")
    if _WIN_RESERVED_NAME_RE.match(stem):
        sanitized = f"_{sanitized}"
        # R57 round 2 QA（DEF-101-478 追加）：`_` 前綴是在**截斷之後**才加的，故加完可能
        # 達 `_MAX_COMPONENT_LEN + 1`（實測 `sanitize_component('CON' + ' '*3 + '.' + 'x'*100)`
        # 回傳 81 字元）。此為既有缺陷（`'CON.' + 'z'*100` 在 R57 之前就已 81 字元），R57 的
        # `.rstrip(" ")` 只是把「保留名 + 尾隨空白」也納入會觸發的輸入集合而擴大了暴露面。
        # 重新截斷後不會退回保留名——前綴 `_` 使 stem 成為 `_CON` 之類，不匹配 `^CON$`；
        # 尾端再 rstrip(" .") 是為了避免截斷剛好切在空白/句點上而違反 NTFS「不得以空白或
        # 句點結尾」的規則（開頭有 `_` 故不可能被剝成空字串）。
        if len(sanitized) > _MAX_COMPONENT_LEN:
            sanitized = sanitized[:_MAX_COMPONENT_LEN].rstrip(" .")
    return sanitized
