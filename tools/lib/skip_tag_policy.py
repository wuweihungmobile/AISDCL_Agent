#!/usr/bin/env python3
"""職責①：skip 標籤家族的**政策常數與棘輪基線**（唯一真相源）。

R75 拆分背景：本模組原本與 runtime 彙整／AST 靜態掃描／樹 I/O 四種職責同住
`tools/lib/windows_skip_tags.py`（508 code 行／727 raw 行）。R75 把 monorepo 根層
`tools/` 納入 `AutoClaude/tools/check_loc_budget.py` 的 LOC 分級後，`tools/lib/` 的
`guardrail_lib` tier ≤400 當場把它擋下——而那正是判準想表達的事：一支超過 400 行的
共用模組按定義已不只做一件事。

四個模組的分工（`windows_skip_tags.py` 退為 thin facade，公開 API 一律經它取用）：
  ① `skip_tag_policy`      本檔——常數與棘輪基線、以及只讀這些常數的純判準
  ② `skip_static_scan`     讀原始碼 AST，抽站點、判方向、分類
  ③ `skip_source_io`       檔案樹 I/O（`{檔名: 原始碼}`）
  ④ `skip_runtime_report`  讀 `unittest.TestResult`，彙整本次真的 skip 了什麼

WHY 常數要獨立成①而不是跟著某一面走：②與④是**同一個判準的兩種載具**，共用同一份
標籤／關鍵詞／述詞登記表。常數若住在其中一面，另一面就得跨模組取用它，等於宣告
「這份常數屬於那一面」——而它不屬於任何一面。放在共同的上游才不會各自漂移
（原檔頭「內聚」那段講的就是這件事，拆分後這句話仍然成立、只是換了實現方式）。
"""
from __future__ import annotations

import re
from collections.abc import Mapping

# ── 標籤字面 ────────────────────────────────────────────────────────────────────
# R43 Architect P1（DEF-101-348 方向①）：DEF-101-343~345 揪出 5 支 Windows 專屬
# 回歸測試連續 5+ 輪「全 APPROVE」卻從未在原生 Windows 上真正跑過——`unittest`
# 預設摘要（`skipped=N`）不區分「一般性 skip」與「這支測試的驗證價值僅在原生
# Windows 上成立、這次環境不符沒跑」，是造成該漏洞連續多輪未被發現的根因之一。
WINDOWS_NATIVE_SKIP_TAG = "[WINDOWS-NATIVE-ONLY]"

# R74：反方向的對稱標籤（PKG-4 E／F）。
#   `[POSIX-NATIVE-ONLY]`＝驗證價值只在非 Windows（POSIX）平台成立，**這次跑在
#                          Windows 上所以沒跑**。
#   `[MAC-NATIVE-ONLY]`  ＝更窄的 darwin 專屬版（`brew`／`launchd`／BSD `ps` 這類）。
# 兩者都視為「已標籤」——判準只問「作者有沒有標明這是哪一側的覆蓋損失」。
POSIX_NATIVE_SKIP_TAG = "[POSIX-NATIVE-ONLY]"
MAC_NATIVE_SKIP_TAG = "[MAC-NATIVE-ONLY]"
NON_WINDOWS_SKIP_TAGS: tuple[str, ...] = (POSIX_NATIVE_SKIP_TAG, MAC_NATIVE_SKIP_TAG)

# 🔴 R75 新增（QA-R74-02）：第三種語意——**這支測試沒跑是因為機器缺工具／缺環境**，
# 與平台無關。詳見 `skip_static_scan.site_class` 的 `tool-absence` 類別說明。
TOOL_ABSENCE_SKIP_TAG = "[TOOL-ABSENCE]"
ALL_SKIP_TAGS: tuple[str, ...] = (
    WINDOWS_NATIVE_SKIP_TAG, *NON_WINDOWS_SKIP_TAGS, TOOL_ABSENCE_SKIP_TAG,
)

# ── 關鍵詞面（標籤完整性的啟發式）───────────────────────────────────────────────
# R67-F11：`report_windows_native_skips` 只看得到「已經帶標籤」的 skip，對「該帶而
# 沒帶」結構性盲目。R67 動工時實測：macOS 上 15 支 skip 全數為 Windows 專屬，標題卻
# 只印 10，低報 33%。
# 判準邊界（誠實劃界）：關鍵詞掃描是啟發式，抓的是「reason 講的明明是 Windows 語意
# 卻沒帶標籤」。它抓不到「reason 完全沒提任何 Windows 字眼的 Windows-only skip」。
_WINDOWS_LIKE_SKIP_HINTS = ("windows", "win32", "pathext", "bash.exe", "mutex", "ntfs")

# 具名豁免：reason 命中關鍵詞但**確實不是** Windows 專屬的 skip（鍵＝test id，
# 值＝理由）。現況為空集合。刻意保留這個空常數而非省略——例外必須逐支具名並附
# 理由，不接受「整批略過」的通用開關。
_WINDOWS_SKIP_TAG_EXEMPT: dict[str, str] = {}

# ── 述詞方向登記表 ──────────────────────────────────────────────────────────────
# 「條件為真 ⇒ 執行環境是 Windows」的述詞。判準：
#   · `skipUnless(<Windows 述詞>)` → 非 Windows 才 skip → 正是標籤語意 ⇒ **該**帶
#   · `skipIf(<Windows 述詞>)`     → Windows 才 skip（POSIX-only 測試）⇒ **不該**帶
_WINDOWS_SKIP_PREDICATE_MARKERS: tuple[str, ...] = (
    'os.name == "nt"', "os.name == 'nt'",
    'platform.system() == "Windows"', "platform.system() == 'Windows'",
    'sys.platform == "win32"', "sys.platform == 'win32'",
    'sys.platform.startswith("win")', "sys.platform.startswith('win')",
    "_ps_windows_with_engine()",   # tools/tests/_ps_engine.windows_with_engine 的就地別名
    "_ps_windows_native_51()",     # 同上，windows_with_native_ps51 的就地別名
    "windows_with_native_ps51()",
    "windows_with_engine()",
    "_windows_pwsh_available()",   # tools/tests/test_bootstrap_ps1.py 的就地別名
)

# 「條件在 **Windows 上** 求值為 False」的述詞（R74 新增）。
#
# 🔴 WHY 判準要問「這個述詞在 Windows 上是什麼值」，而不是「它是不是 Windows 述詞」：
# R72 的兩極模型對否定形態**方向會算反**。R74 實測到 `skipif(not
# _windows_pwsh_available())` 被判成「Windows 上會 skip」，語意恰恰相反。方向算反比
# 判不出方向更糟：它會要求作者貼上**錯的**標籤。
_NON_WINDOWS_SKIP_PREDICATE_MARKERS: tuple[str, ...] = (
    'os.name != "nt"', "os.name != 'nt'",
    'platform.system() != "Windows"', "platform.system() != 'Windows'",
    'sys.platform != "win32"', "sys.platform != 'win32'",
    'sys.platform == "darwin"', "sys.platform == 'darwin'",
    'platform.system() == "Darwin"', "platform.system() == 'Darwin'",
)

# 在 Windows 上求值為 True 的述詞（上表 ＋ darwin 的否定）。
_TRUE_ON_WINDOWS_MARKERS: tuple[str, ...] = (
    *_WINDOWS_SKIP_PREDICATE_MARKERS,
    'sys.platform != "darwin"', "sys.platform != 'darwin'",
    'platform.system() != "Darwin"', "platform.system() != 'Darwin'",
)

#: `{marker: 該述詞在 Windows 上的值}`。
#:
#: 🔴 R75 訂正（SD 追加①）：本表原為「依 marker 長度遞減排序後**取第一個命中**」的
#: tuple，且註解逐字宣告「長度序是判準的一部分」。SD 實測那個設計對**複合布林條件**
#: 會算出反方向：`skipIf(sys.platform == 'win32' or sys.platform == 'darwin')` 實際在
#: Windows 上會 skip，但長度序取到較長的 `sys.platform == 'darwin'`（24 字 > 23 字）
#: ⇒ 判成 `non-windows`。方向算反正是上一段自承「比判不出方向更糟」的形態。
#: 現改為 dict ＋ `skip_static_scan` 側以 **AST 真值運算**處理 `or`／`and`／`not`，
#: 單一葉節點內若同時命中值相反的 marker 則回 `None`（不猜）。長度序因此不再是判準的
#: 一部分——本表現存 marker 之間也不存在「值相反且互為子串」的配對（`==` 與 `!=`
#: 互不為子串），故取集合語意不會退化。
_PREDICATE_WINDOWS_VALUE: dict[str, bool] = {
    **{m: True for m in _TRUE_ON_WINDOWS_MARKERS},
    **{m: False for m in _NON_WINDOWS_SKIP_PREDICATE_MARKERS},
}

# 「看起來像 Windows 述詞」的粗網。**只**用來抓上表的漏登記，不參與任何判紅／放行
# 決策——粗網天生會有偽陽性，讓它直接判紅會把本鎖變成噪音來源。
_WINDOWS_PREDICATE_SUSPECT_RE = re.compile(r"windows|win32|\bnt\b|darwin", re.IGNORECASE)

# 🔴 R75（QA-R74-02）：第三種語意「環境／工具缺席」的**分類方式**刻意不做成關鍵詞表。
#
# 缺陷本體（QA 當回合實測）：三棵活測試樹共 103 個 decorator 站點，其中 **63 筆（61%）**
# 的方向判不出來（`_predicate_value_on_windows` 回 `None`），而原 docstring 逐字宣稱
# 「未登記則 None（fail-open，由 `unregistered_windows_like_predicates` 收口）」——實測
# 那支對這 63 筆**命中 0**，因為它的粗網只認 `windows|win32|nt|darwin`，而這些述詞長
# 得像 `_BASH`／`_ZSH is None`／`_DSN is None`／`shutil.which("git")`／`_bash_exe()`／
# `any_engine_available()`。⇒ 兩道方向判準都看不到、宣稱的收口網也看不到 ＝
# 對**所有**機械物隱形。
#
# 為何不列一張「工具探針片段」的關鍵詞表（第一版寫過、當回合實測後拆掉）：實測 27 筆殘留
# 全是各檔自訂的探針常數／helper（`_BASH`／`_REAL_BIN_BASH`／`_PATH_HONOURING_BASH`／
# `_TTLCACHE_AVAILABLE`／`_SDD_PRESENT`／`_PG_REAL_ENABLED`／`_bash_exe()`／`_ps_engine()`
# ／`any_engine_available()` …）——每加一支新探針就要回來補表，那張表**保證會腐化**，
# 而它腐化的方式正好是「又一批站點靜默變隱形」。
# 改用結構判準（實作在 `skip_static_scan.site_class`）：
#   方向判得出來 ⇒ 平台語意兩格之一；
#   判不出來 ＋ 條件裡有「長得像 Windows 述詞卻未登記」的**葉節點** ⇒ `unclassified`
#            （可行動：把該述詞加進登記表）；
#   判不出來 ＋ 沒有那種葉 ⇒ `tool-absence`（值取決於這台機器裝了什麼，不是平台常數）。
# 這樣「新的探針寫法」天然落進 `tool-absence` 而不是變隱形，不需要任何人維護清單。

# ── 掃描面 ──────────────────────────────────────────────────────────────────────
#: 掃描面的快取目錄（不進版控，列進來會讓兩邊基準不同）。
_CACHE_DIR_NAMES = frozenset({"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"})

# R74：射程從「一棵樹」擴到「三棵活測試樹」。
# 🔴 為何非擴不可：R72 建立方向判準時射程只有 `tools/tests/`，而 repo 的活測試檔共
# 三百餘支——絕大多數不在任何方向判準的射程內。判準的價值是「同一個缺陷換個寫法／
# 換棵樹就必紅」，射程只圈一棵樹等於把成本降到「寫在另一個目錄」。
# 刻意**不含** `AISDLC_SDD/AISDLC_SDD_v0.NN/`（Copy-on-Evolve 政策下凍結版與中間版
# 一律不可改，納入等於一上線就要求修改不可改的樹；LATEST 版單獨納入則會讓射程隨版本
# 目錄改名而漂移，需先把 `tools/lib/sdd_latest.py` 的解析接進來，屬另一件事）。
_EXTRA_SCAN_TREES: tuple[str, ...] = (
    "AutoClaude/tests",
    "AISDLC_SDD/scripts/tests",
)

#: 逐樹檔數**下限**（防掃描面靜默縮小）。語意固定為「重釘當時實測值的八成」。
#:
#: 🔴 R75（SD 追加②）——**部分證偽 ＋ 補上真正缺的東西**：
#: SD 的實測數字對（掃描面 53／255／29 vs 下限 42／204／23），但「下限已 stale、鑑別力
#: 被吃掉一截」這個結論不成立：R75 當回合實測 `int(53×0.8)=42`、`int(255×0.8)=204`、
#: `int(29×0.8)=23`——**三個下限剛好就等於本模組宣告的八折語意**，也就是樹自 R74 釘表
#: 以來一支都沒長，下限沒有落後。若照 SD 的字面「重釘到當回合實測值」，得到的是同一組
#: 數字。故本表數值不動。
#: SD 真正指出的缺口是另一件事、而且成立：**沒有任何東西會在下限過期時說話**——R74 的
#: `MIN_TESTS` 腐化 11 輪就是這麼發生的。那個缺口由 `tree_floor_problems()` 的第三向補上：
#: 下限的語意既然是「實測的八成」，那 `floor < int(actual × 0.8)` 本身就是一筆 problem，
#: 會逼人回來重釘。餘裕取兩成的理由：一次收輪淨增／淨減十餘支測試檔是常態，兩成才不會
#: 天天紅；而縮面到八成以下就是真的該查。
_TREE_FILE_FLOORS: dict[str, int] = {
    "tools/tests": 42,
    "AutoClaude/tests": 204,
    "AISDLC_SDD/scripts/tests": 23,
}

#: 下限相對實測值的目標比例（`floor ≈ actual × 本值`）。兩個方向都由它定義：
#: `actual < floor` ＝縮面；`floor < actual × 本值` ＝下限已過期。
TREE_FLOOR_RATIO = 0.8

# 🔴 **棘輪基線**：`[POSIX-NATIVE-ONLY]`／`[MAC-NATIVE-ONLY]` 尚未補標的存量站點數
# （鍵＝相對 monorepo 根的樹名，值＝該樹**未標籤**的「Windows 上會 skip」站點數）。
#
# 為何是棘輪而不是直接判紅：存量分佈在多支檔案上，其中大部分不在單一包的檔案所有權內
# （跨界改動＝並行包互踩假紅）。棘輪讓「新增未標籤站點」當場紅、同時不假裝存量已清乾淨
# ——它是**可見的欠債**，不是豁免。判準刻意是**相等**而非「不得增加」：任一方向的變動
# 都必須有人回來改這張表，否則它會像 `MIN_TESTS` 那樣腐化。
#
# 🔴 R76（R76-15 ①）：`AutoClaude/tests` 由 6 下修為 **0**——那 6 筆已於本輪補標
# （`test_evaluator_kill_tree.py` ×3／`test_perception.py`／
# `test_perception_platform_honesty.py`〔darwin 專屬故用 `[MAC-NATIVE-ONLY]`〕／
# `tools/test_run_local_nightly_sh_static.py`）。**為何非補不可**：那 6 筆是
# `AutoClaude/tests` 唯一的反方向站點，未標籤 ⇒ `conftest.py::non_windows_native_skips()`
# 在 Windows 上恆回空清單 ⇒ R74 為此新增的「本次跑在 Windows 上失去的覆蓋」摘要區塊
# **結構性零輸出**，而本表把欠債凍結成 6 讓棘輪同時恆綠 ⇒ 一個為了看見覆蓋損失而建的
# 機制，與看著它的鎖，兩者一起沉默。
_POSIX_TAG_RATCHET: dict[str, int] = {
    "tools/tests": 1,
    "AutoClaude/tests": 0,
    "AISDLC_SDD/scripts/tests": 1,
}

#: 🔴 R76（R76-15 ①）：上表各格的 **shrink-only 天花板**（基線只准下修）。
#:
#: 為何上表自己不夠：它的判準是「相等」，而 `got > want` 的失敗訊息會誠實列出兩條
#: 出口，其中一條是「把基線改成實測值」。相等判準對那條出口**零阻力**——新增未標籤
#: 站點後把 6 改成 7，鎖當場全綠，欠債就這樣被合法地加大，而且看起來像在維護基線。
#: 本表讓「加大欠債」變成必須**同時**改兩個地方的顯式動作：一個會出現在 diff 裡、
#: 需要在 PR 說明的決定，而不是照著失敗訊息把數字改大就沒事。
#:
#: 誠實劃界：本表擋的是「上修基線」，擋不了「同一個 commit 把天花板也一起上修」——
#: 兩個常數住同一支檔，沒有任何機械物能阻止那個動作。本表買到的是**可見度**
#: （上修天花板是具名的、可被複審點名的），不是不可能性。真正的不可能性只有把欠債
#: 清成 0（`AutoClaude/tests` 本輪已做到）。
_POSIX_TAG_RATCHET_CEILING: dict[str, int] = {
    "tools/tests": 1,
    "AutoClaude/tests": 0,
    "AISDLC_SDD/scripts/tests": 1,
}

#: 🔴 R75 新增（QA-R74-02）：**站點分類普查**的棘輪基線 `{樹: {類別: 站點數}}`。
#:
#: 存在理由：上面那個棘輪只帳「Windows 上會 skip 且未標籤」這一格，於是方向判不出來的
#: 63 筆完全不在任何帳上。本表把**每一個**被抽到的站點都放進某一格 ⇒ 沒有任何站點能對
#: 所有機械物隱形。類別定義見 `skip_static_scan.site_class()`。
#: 判準是**相等**（同 `_POSIX_TAG_RATCHET` 的理由）：任一格變動都必須有人回來改。
#:
#: R75 落地實測（三棵活測試樹共 115 個站點，`unclassified` 為 0 ⇒ 沒有任何站點隱形）。
#: 對照 QA 量到的修**前**狀態：103 個 decorator 站點中 63 筆方向判不出來、且對所有機械物
#: 隱形（61%）。修後那 63 筆歸入 `tool-absence`（本表可見、可稽核），函式體內
#: `self.skipTest(...)`（此前完全在射程外，連站點都抽不到）歸入 `runtime-skipTest`。
#:
#: 🔴 R75 收輪重釘 `tools/tests` 的 `runtime-skipTest` 10 → 12：雲端錨判準改寫時新增兩條
#: 「shallow clone／無 git ⇒ 未驗證而不判紅」路徑，兩者都是函式體內 `self.skipTest(...)`。
#: 這正是本表的設計意圖生效——相等判準讓新站點在落地當回合就被逼進帳、不會靜默變隱形，
#: 且失敗訊息自己會印出該填的數字，所以重釘是**設計好的流程**而不是繞過判準。
_SITE_CLASS_CENSUS: dict[str, dict[str, int]] = {
    "tools/tests": {
        "windows-only": 13,
        "posix-only": 11,
        "tool-absence": 38,
        "runtime-skipTest": 12,
        "unclassified": 0,
    },
    "AutoClaude/tests": {
        "windows-only": 8,
        "posix-only": 6,
        "tool-absence": 16,
        "runtime-skipTest": 0,
        "unclassified": 0,
    },
    "AISDLC_SDD/scripts/tests": {
        "windows-only": 1,
        "posix-only": 1,
        "tool-absence": 11,
        "runtime-skipTest": 0,
        "unclassified": 0,
    },
}


def tree_floor_problems(counts: Mapping[str, int]) -> list[str]:
    """逐樹檔數下限的**雙向**判準（純函式）：縮面要紅、下限過期也要紅。

    回傳問題描述清單；空＝合格。三種形態：
      ① 樹在掃描面卻不在 `_TREE_FILE_FLOORS` ⇒ 新樹必須顯式釘下限（否則它的縮面
         靜默不計）。
      ② `actual < floor` ⇒ 該樹掃描面疑似縮小（原本就有的那一向）。
      ③ `floor < actual × TREE_FLOOR_RATIO` ⇒ **下限已過期**（R75 新增的防腐那一向）。
         沒有這一向，下限只會愈來愈鬆而沒有任何東西會說話——這正是 SD 追加②抓到的事。
    """
    problems: list[str] = []
    for tree in sorted(set(counts) | set(_TREE_FILE_FLOORS)):
        floor = _TREE_FILE_FLOORS.get(tree)
        actual = counts.get(tree)
        if floor is None:
            problems.append(
                f"{tree}：出現在掃描面卻不在 _TREE_FILE_FLOORS——新樹必須顯式釘下限"
                f"（建議值＝實測 {actual} × {TREE_FLOOR_RATIO} = "
                f"{int((actual or 0) * TREE_FLOOR_RATIO)}）"
            )
        elif actual is None:
            problems.append(f"{tree}：在下限表內卻不在掃描面（下限 {floor}）——射程疑似縮小")
        elif actual < floor:
            problems.append(
                f"{tree}：掃描到 {actual} 支 < 下限 {floor}——該樹掃描面疑似縮小（不得靜默）"
            )
        elif floor < int(actual * TREE_FLOOR_RATIO):
            problems.append(
                f"{tree}：下限 {floor} 已過期（實測 {actual}，下限只剩實測的 "
                f"{floor / actual:.0%}、低於 {TREE_FLOOR_RATIO:.0%}）——對縮面的鑑別力已鬆，"
                f"請把 _TREE_FILE_FLOORS['{tree}'] 重釘為 {int(actual * TREE_FLOOR_RATIO)}"
            )
    return problems


def posix_tag_ratchet_problems(counts: Mapping[str, int]) -> list[str]:
    """純函式：實測未標籤數與棘輪基線的差異；空清單＝合格。

    R76 增第二向（與 `counts` 無關、只看兩張常數表）：基線不得高於 shrink-only
    天花板 `_POSIX_TAG_RATCHET_CEILING`。沒有這一向，「相等」判準的合法修法之一
    就是把基線改大，欠債可以無聲增長（見該常數上方的 WHY）。
    """
    problems: list[str] = []
    for tree in sorted(set(_POSIX_TAG_RATCHET) | set(_POSIX_TAG_RATCHET_CEILING)):
        want = _POSIX_TAG_RATCHET.get(tree)
        ceiling = _POSIX_TAG_RATCHET_CEILING.get(tree)
        if want is None or ceiling is None:
            problems.append(
                f"{tree}：只出現在 _POSIX_TAG_RATCHET／_POSIX_TAG_RATCHET_CEILING 其中一張表"
                f"（基線 {want}／天花板 {ceiling}）——兩表必須逐格對位，否則天花板形同虛設"
            )
        elif want > ceiling:
            problems.append(
                f"{tree}：基線 {want} 高於 shrink-only 天花板 {ceiling}——"
                "反方向標籤欠債只准變少。要真的加大欠債，必須在同一個 commit 顯式上修 "
                f"skip_tag_policy._POSIX_TAG_RATCHET_CEILING['{tree}'] 並在 PR 說明理由"
            )
    for tree in sorted(set(counts) | set(_POSIX_TAG_RATCHET)):
        want = _POSIX_TAG_RATCHET.get(tree)
        got = counts.get(tree)
        if want is None:
            problems.append(
                f"{tree}：出現在掃描面卻不在 _POSIX_TAG_RATCHET 基線表內（實測 {got}）"
                "——新樹必須顯式入表，否則它的欠債靜默不計"
            )
        elif got is None:
            problems.append(f"{tree}：在基線表內卻不在掃描面（基線 {want}）——射程疑似縮小")
        elif got != want:
            if got > want:
                verb = "新增了未標籤站點"
                fix = (
                    f"在該 skip 的 reason 最前面加 {POSIX_NATIVE_SKIP_TAG}"
                    f"（darwin 專屬用 {MAC_NATIVE_SKIP_TAG}）。"
                    "🔴 R76 起「把基線改大」不再是等價出口——基線受 shrink-only 天花板"
                    "管轄，改大它必須同時顯式上修 _POSIX_TAG_RATCHET_CEILING"
                )
            else:
                verb = "已補標（請下修基線）"
                fix = (
                    f"把 skip_tag_policy._POSIX_TAG_RATCHET['{tree}'] 與 "
                    f"_POSIX_TAG_RATCHET_CEILING['{tree}'] **一起**改為 {got}"
                    "（天花板不跟著下修＝把剛還掉的欠債額度留著，日後可無聲用回去）"
                )
            problems.append(
                f"{tree}：未標籤的「Windows 上會 skip」站點實測 {got}、基線 {want}"
                f"——{verb}。修法：{fix}"
            )
    return problems


def site_class_census_problems(census: Mapping[str, Mapping[str, int]]) -> list[str]:
    """站點分類普查的棘輪判準（純函式）：任一格與基線不等即違規。

    比**全表相等**而不是「某幾格不得增加」：普查的價值就在「每個站點都在某一格」，
    只要有一格沒人維護，那一格就是新的隱形處。
    """
    problems: list[str] = []
    for tree in sorted(set(census) | set(_SITE_CLASS_CENSUS)):
        want = _SITE_CLASS_CENSUS.get(tree)
        got = census.get(tree)
        if want is None:
            problems.append(
                f"{tree}：出現在掃描面卻不在 _SITE_CLASS_CENSUS——新樹必須顯式入表"
                f"（實測 {dict(got or {})}）"
            )
        elif got is None:
            problems.append(f"{tree}：在普查表內卻不在掃描面（基線 {dict(want)}）——射程疑似縮小")
        elif dict(got) != dict(want):
            problems.append(
                f"{tree}：站點分類普查漂移。基線 {dict(want)}／實測 {dict(got)}"
                "——任一類別數字變動都必須回來改 skip_tag_policy._SITE_CLASS_CENSUS"
                "（這張表的用途就是讓「沒有站點對所有機械物隱形」可被驗證）"
            )
    return problems
