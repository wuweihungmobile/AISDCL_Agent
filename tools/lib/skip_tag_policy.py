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
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path

# 本檔住 `<repo>/tools/lib/`：與 `sdd_latest` 同層，呼叫端一律已把 `tools/lib`
# 放上 sys.path（同 `skip_source_io` 的既有慣例）。此處仍自行補一次，讓「只 import
# 本模組」的呼叫端也成立。
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sdd_latest  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]

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

# 🔴 R79 新增（D-skipped #2）：把「為什麼這支沒跑」由散文升格為**可分群的標籤**。
# 掌舵者 S3 問的是「為何會有 skipped、如何徹底消除」，而在此之前那個數字沒有任何機械物
# 在替它說話（`PG_CONTRACT_MAX_SKIPPED` 是全 repo 唯一天花板、只覆蓋一個 CI job）。逐支
# 消除治不了復發——R76 把 224 壓到 158 之後，R77／R78 又各自新增 skip 站點，靠的全是人
# 記得。分群的用途是讓「哪一類可以清到 0、哪一類結構上不可能」變成可稽核的量，而不是
# 每輪由人重新盤點一次。
#   `[ENV-DISABLED]`   ＝環境**未啟用**（不是缺件）。與 `[TOOL-ABSENCE]` 的分野是本 repo
#                        既有的一條紀律：skip 理由寫「需要 X」不等於 X 缺席，多半只是環境
#                        變數沒設或 extras 沒裝。這一群是**唯一應該清到 0** 的那群——本輪
#                        實測：這台機器一件缺件都沒有，設好三個環境變數就消掉 92 支。
#   `[STRUCTURAL-PAIR]`＝absent／present 互斥對這類「結構上必有一支 skip」者，不可能歸零。
#   `[DEBT]`           ＝真欠債（斷言落點還沒建）。理由必須帶承接輪次，判準沿用
#                        `_EXEMPT_HANDOVER_RE`——沒有承接者的欠債就是永久欠債。
ENV_DISABLED_SKIP_TAG = "[ENV-DISABLED]"
STRUCTURAL_PAIR_SKIP_TAG = "[STRUCTURAL-PAIR]"
DEBT_SKIP_TAG = "[DEBT]"

ALL_SKIP_TAGS: tuple[str, ...] = (
    WINDOWS_NATIVE_SKIP_TAG, *NON_WINDOWS_SKIP_TAGS, TOOL_ABSENCE_SKIP_TAG,
    ENV_DISABLED_SKIP_TAG, STRUCTURAL_PAIR_SKIP_TAG, DEBT_SKIP_TAG,
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
#
# 🔴 本輪補上自檢（此前**零 stale 自檢、零牙**）：注入實測顯示，往本表塞一筆指向
# 不存在檔案的豁免、或一筆指向真檔但根本不需要豁免的條目，整支
# `tools/tests/test_run_root_unittests.py`（73 tests）仍然全綠——也就是說本表現在
# 是空的所以看起來乾淨，第一筆進去的那天起它就是一張**只進不出**的永久豁免表。
# 對照組：姊妹表 `_COLLECTION_EXEMPT` 早就有牙（多餘的豁免會被抓）。同一個 repo
# 對「豁免表要有 stale 自檢」有明確認知，卻只實作在兩張表中的一張。
_WINDOWS_SKIP_TAG_EXEMPT: dict[str, str] = {}

#: 豁免理由必須寫出**承接輪次**（形態＝大寫 R 後接兩位以上數字）。沒有承接輪次的
#: 豁免＝沒有人負責把它拿掉，也就是永久豁免——Scan-H 必跑項② 對每一個豁免的要求。
_EXEMPT_HANDOVER_RE = re.compile(r"R\d{2,}")


def exemption_problems(
    exempt: Mapping[str, str],
    *,
    flagged_without_exempt: Mapping[str, str] | None = None,
) -> list[str]:
    """`_WINDOWS_SKIP_TAG_EXEMPT` 的雙面自檢（純函式）。回空 list ＝合格。

    · **格式面**（不分平台）：值必須寫出承接輪次，否則就是只進不出的永久豁免。
    · **stale 面**（`flagged_without_exempt` 為 None 時**不判**）：該筆豁免若在
      「假裝豁免表是空的」的重掃結果裡根本不會被判違規，代表它壓的東西已經不在
      （測試改名／reason 改寫／已補標籤）⇒ 必須移除。

    🔴 為何 stale 面要能被關掉（Scan-H⑥ 互鎖）：它的資料來源
    `untagged_windows_like_skips` 在 **Windows 上整組早退回空清單**（那個早退本身
    是對的，理由見該函式）。若無條件套用，Windows 上每一筆豁免都會被判 stale ＝
    整片假紅。呼叫端只在該面真的有在說話時才把資料傳進來。
    """
    problems: list[str] = []
    for test_id, why in sorted(exempt.items()):
        if not _EXEMPT_HANDOVER_RE.search(why):
            problems.append(
                f"豁免 `{test_id}` 的理由沒有寫承接輪次——沒有承接者的豁免就是永久豁免。"
                "請在理由裡寫明由哪一輪回來複查（形態：大寫 R 加輪號）"
            )
        if flagged_without_exempt is not None and test_id not in flagged_without_exempt:
            problems.append(
                f"豁免 `{test_id}` 已 stale：把本表當成空的重掃，這一筆根本不會被判違規"
                "（測試改名／reason 改寫／已補標籤）⇒ 請自表中移除，不要留著佔位"
            )
    return problems

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
# 刻意**不含**凍結版 `AISDLC_SDD/AISDLC_SDD_v0.01`~`v0.29`（Copy-on-Evolve 政策下
# 一律不可改，納入等於一上線就要求修改不可改的樹）。
#
# 🔴 本輪補上 LATEST 版的 `tools/fsm_runtime/tests`（此前**整棵零覆蓋**：該樹的 4 個
# skip 站點對所有機械物隱形，新增第 2 個未標籤 posix-only 站點是零成本的）。原註記
# 給的理由是「LATEST 單獨納入會隨版本目錄改名而漂移，需先接 `tools/lib/sdd_latest.py`」
# ——那個理由成立，但它推導出的結論應該是「接上 `sdd_latest` 再納入」，而不是「不納」。
# 現在就接上了；下方四張表的鍵一律用同一個計算值，升版時四張表一起跟著移動。
def _latest_fsm_tests_rel() -> str:
    """LATEST 版 `tools/fsm_runtime/tests` 的 repo 相對路徑（SSOT＝`sdd_latest`）。

    🔴 解析失敗時**不**靜默丟掉這棵樹（那是 fail-open，正是本模組通篇在防的事），
    而是回一個磁碟上必然不存在的路徑：`scan_tree_sources` 對它取得空 dict，
    `report_untagged_windows_skip_decorators` 隨即報「掃描面為空」並讓 rc 為 1。
    """
    try:
        latest = sdd_latest.resolve_latest_root(_REPO_ROOT / "AISDLC_SDD")
        rel = latest.relative_to(_REPO_ROOT).as_posix()
    except (AssertionError, OSError, ValueError):
        rel = "AISDLC_SDD/LATEST-解析失敗"
    return f"{rel}/tools/fsm_runtime/tests"


LATEST_FSM_TESTS_TREE = _latest_fsm_tests_rel()

_EXTRA_SCAN_TREES: tuple[str, ...] = (
    "AutoClaude/tests",
    "AISDLC_SDD/scripts/tests",
    LATEST_FSM_TESTS_TREE,
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
#: 🔴 本輪重釘 `tools/tests` 42 → 44（本表宣告的八折語意所要求的動作，非放寬）：
#: 該樹自 R75 釘表時的 53 支長到 55 支（本輪 act 地端閘門的映像鎖 ＋ 另一包的
#: context budget guard 鎖各 +1），`int(55 × 0.8) = 44 > 42` ⇒ `tree_floor_problems()`
#: 的第三向（下限已過期）當場判紅並逐字指示重釘為 44——本行就是照著那個指示改的。
#: 方向是**上修**：下限愈高、對「掃描面靜默縮小」的鑑別力愈強，不是把門檻放寬。
#: 44 對 54 與 55 兩個檔數皆成立（`int(54 × 0.8) = 43 < 44`），故與同期並行的另一包
#: 是否落地無關——刻意選這個值，避免兩包互相把對方的閘門弄紅。
_TREE_FILE_FLOORS: dict[str, int] = {
    # 🔴 R82：44 → 45。**非本包造成**——`tools/tests` 由 56 支長到 57（並行包新增
    # `test_mac_readiness_r82.py`），下限只剩實測的 77% ⇒ 觸發 `TREE_FLOOR_RATIO` 的防腐
    # 那一向。這是**下限**（只准往上＝判準變嚴），不是上限放寬；不跟著調，對縮面的鑑別力
    # 就會愈來愈鬆而沒有任何東西說話。🔴 收輪者請以停工後的單人窗口重量一次再定案。
    # 🔴 R82 收輪重釘 45 → 46（本列上一段那句「收輪者請以停工後的單人窗口重量一次再定案」
    # 就是這個動作）：所有包停工後實測 `tools/tests` 已是 58 支（45 只剩實測的 78%，低於
    # `TREE_FLOOR_RATIO` 的 80%），判準逐字指示重釘為 46 ⇒ 本行照填，不做加減推算。
    # 成長來源全是並行包新增的鎖檔（`test_mac_readiness_r82.py`／
    # `test_negative_existence_claims_r82.py`／`test_quota_policy.py`），非本包。
    # 🔴 R83 收輪重釘 46 → 48（同上一段的機制，第三向「下限已過期」判紅並逐字指示重釘為
    # 48 ⇒ 本行照填，零加減推算）。成長來源全是並行包新增的鎖檔，非任一單包：
    # `test_block_destructive_git_r83.py`（毀滅性 git 指令阻斷器的回歸鎖）／
    # `test_mac_endurance_r83.py`（mac launchd 續航後端）／`test_skip_discoverability_r83.py`
    # （單平台指引掃描器）三支皆為本輪新增。
    # 🔴 **本值對 60 與 61 兩個檔數皆成立**（`int(60×0.8)=48`、`int(61×0.8)=48`，而
    # `int(62×0.8)=49`）——刻意選這個值，理由與上方 R75 那段相同：避免並行包是否落地
    # 決定本閘門的顏色。方向是**上修**（下限愈高、對「掃描面靜默縮小」的鑑別力愈強）。
    "tools/tests": 48,
    # 🔴 R82 包 A2（DEBT-01）：204 → 205。新增 `AutoClaude/tests/contract/test_w6_deletion.py`
    # （AC2-2 的真斷言落點）後掃描面變 257，下限只剩實測的 79% ⇒ 依 `TREE_FLOOR_RATIO` 的
    # 防腐那一向轉紅。這正是它的設計意圖：下限不跟著長就會愈來愈鬆而沒有任何東西說話。
    # 🔴 本輪 205 → 208（同一個機制第三度生效，方向同為**上修＝判準更嚴**，不是放寬）。
    # 成長來源逐檔具名，全部是 AC_MATRIX 剩下三筆欠債的真斷言落點（走出口①「把 target
    # 檔建起來」而非再推一輪）：`tests/integration/test_concurrent_runs.py`（AC3-4）／
    # `tests/integration/test_sigint_checkpoint.py`（AC5-4）／
    # `tests/integration/test_config_schema_api.py`（AC6-3）。實測掃描面 257 → 260，
    # 判準逐字指示「重釘為 208」⇒ 本行照填，零加減推算。
    # 🔴 **本值對 208~261 支皆成立**（`int(261×0.8)=208`、`int(262×0.8)=209`）——刻意記下
    # 這個區間，理由同上方 `tools/tests` 那段：本輪尚有並行包在跑，不讓「別的包有沒有再
    # 新增一支測試檔」決定本閘門的顏色。並行包合計再新增 ≥2 支就會再次過期 ⇒
    # 🔴 收輪者請在所有包停工後的單人窗口重量一次再定案（同 R82／R83 的既有紀律）。
    # 🔴 **R84 收輪重釘 208 → 209（就是上一行預告的那個動作）**：所有包停工後的單人窗口
    # 實測掃描面 **262** 支（208 只剩實測的 79%、低於 `TREE_FLOOR_RATIO` 的 80%），
    # `tree_floor_problems()` 第三向當場判紅並**逐字**指示「重釘為 209」⇒ 本行照填、零加減
    # 推算。方向是**上修＝判準更嚴**，不是放寬。成長來源是本輪並行包新增的真斷言落點
    # （`tests/plugins/test_notification_quiet_after_session_r84.py`／
    # `tests/tools/test_check_loc_budget_hub_tier_and_special_stale.py`）。
    # 🔴 與上兩列不同，**209 只在實測恰為 262 時成立**（`int(262×0.8)=209`、
    # `int(263×0.8)=210`）——刻意接受這個窄區間，因為本行是在**所有包停工後**量的，
    # 262 就是本輪定案值；下一輪只要 `AutoClaude/tests` 再多一支檔，第三向就會再次判紅
    # 並逐字給出新值，那正是這道棘輪該有的行為（防腐，不是防改）。
    "AutoClaude/tests": 209,
    # 🔴 R84 包 W5：23 → 24。**非本包造成**——`AISDLC_SDD/scripts/tests` 由 29 支長到 30
    # （並行包新增鎖檔），下限只剩實測的 77%、低於 `TREE_FLOOR_RATIO` 的 80% ⇒
    # `tree_floor_problems()` 的第三向（下限已過期）當場判紅並**逐字**指示重釘為 24，本行
    # 照填、零加減推算（同 `tools/tests` 那一列 R82／R83 兩度的既有紀律）。方向是**上修**
    # ＝判準更嚴（下限愈高、對「掃描面靜默縮小」的鑑別力愈強），不是放寬。
    # 🔴 24 對實測 30 與 31 支皆成立（`int(31×0.8)=24`、`int(32×0.8)=25`）——刻意記下這個
    # 區間，理由同上方兩列：本輪尚有並行包在跑，不讓「別的包有沒有再新增一支測試檔」決定
    # 本閘門的顏色。合計再新增 ≥2 支就會再次過期 ⇒
    # 🔴 收輪者請在所有包停工後的單人窗口重量一次再定案。
    "AISDLC_SDD/scripts/tests": 24,
    LATEST_FSM_TESTS_TREE: 60,   # 本輪納入；實測 76 × 0.8
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
#
# 🔴 R79（D-skipped #6）：`tools/tests` 由 1 下修為 **0**——最後一筆
# （`test_dev_start_ps1_lastexitcode.py` 的 `TestDevStartShShellCarrier` 類別層裝飾器）
# 已於本輪補標。**為何非補不可**：runner 的 skip 明細把它底下的 6 支測試印成「未標籤」，
# 與 5 筆真環境性 skip 同桶，讓「徹底消除 skipped」的分流者把可救回的工作量高估一倍。
_POSIX_TAG_RATCHET: dict[str, int] = {
    "tools/tests": 0,
    "AutoClaude/tests": 0,
    "AISDLC_SDD/scripts/tests": 1,
    # 🔴 R82 包 A2（SDD-01）：1 → **0**。那一筆（`test_post_commit_drift_worktree.py`
    # 的模組級 pytestmark）本輪已補上 `[POSIX-NATIVE-ONLY]`——連同該樹另外 4 支 TLC
    # opt-in（補 `[ENV-DISABLED]`）與 2 支 jar 缺件（補 `[TOOL-ABSENCE]`），這棵樹的
    # 6 支 skip 首次全部帶標籤。R79 立此列時寫「不當場補標，因為該檔不在本包所有權內」，
    # 本輪 SDD-01 的射程就是這棵樹，所以那個理由不再成立。
    LATEST_FSM_TESTS_TREE: 0,
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
    "tools/tests": 0,   # R79：連同基線一起下修（見 `_POSIX_TAG_RATCHET` 的 R79 註記）
    "AutoClaude/tests": 0,
    "AISDLC_SDD/scripts/tests": 1,
    LATEST_FSM_TESTS_TREE: 0,   # R82 SDD-01：連同基線一起下修（天花板不跟著降＝欠債額度留著）
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
#:
#: 🔴 本輪收斂重釘 `tools/tests` 的 `runtime-skipTest` 12 → 13：NTFS 保留名判準新增的
#: 外接 oracle 對拍測試（`test_windows_forbidden_filename_parity.py` 的 `setUp`）在
#: 「此 git 建置未啟用 NTFS 保留名檢查」時以函式體內 `self.skipTest(...)` 退場——沒有
#: 第三方裁判時對拍只會產生整批假分歧，跳過比假紅正確。定位方式：對每支 test 檔各以
#: HEAD 版與工作樹版跑一次 `site_class_counts()` 相減（探針不寫死期望值，差異由兩次量測得出）。
#: 🔴 R79 收尾重釘 `tools/tests` 的 `runtime-skipTest` 13 → 15：續航哨兵包在
#: `test_context_budget_guard.py` 新增兩支只在 Windows 有行為的分支測試（schtasks 武裝、
#: 以及與 context 阻斷刻意分開的那個逃生口），兩者都以函式體內 `self.skipTest(...)`
#: 對非 Windows 退場——鐵律三「單平台判準不外推」的正確形態，非隱藏失敗。定位方式同
#: 上一段：對每支 test 檔各以 HEAD 版與工作樹版跑一次 `site_class_counts()` 相減。
#: 🔴 R80 重釘 `tools/tests` 的 `windows-only` 13 → 14（**非放寬**，這張表的判準是「相等」，
#: 任一格變動都必須有人回來改；失敗訊息自己會印出該填的數字，重釘是設計好的流程）。
#: 新站點＝`test_context_budget_guard.py::NoWindowBehaviourTest` 的類別層
#: `@unittest.skipUnless(os.name == "nt", "[WINDOWS-NATIVE-ONLY] …")`：那是「無 console 父行程
#: 下 spawn 不得彈視窗」的**行為**鎖（靜態掃描只證得到「旗標有寫」，證不到「旗標有效」，而
#: R80 的缺陷本體正是旗標有寫但被 `DETACHED_PROCESS` 抵銷掉）。console 配置是 Windows 專屬
#: 概念、POSIX 上 `creationflags` 恆為 0 ⇒ 帶標籤的 skipUnless 是鐵律三要求的正確形態，
#: 不是隱藏失敗。同輪 `_POSIX_TAG_RATCHET`／其天花板皆**未動**（該站點已帶標籤 ⇒ 不計欠債）。
_SITE_CLASS_CENSUS: dict[str, dict[str, int]] = {
    # 🔴 R82 包 A2（CARRIER-02）重釘 `posix-only` 11→10／`tool-absence` 38→36／
    # `runtime-skipTest` 15→16：`test_dev_start_ps1_lastexitcode.py` 的
    # `TestDevStartShShellCarrier` class 級述詞由 `os.name == "nt"`（posix-only）改成
    # 「zsh 與 bash 都解不到」（tool-absence），三支 zsh method 級 skip 的理由改由一個
    # 模組常數供給（站點抽取形態隨之改變），並新增一支函式體內 `self.skipTest(...)`
    # 的載具判準（runtime-skipTest +1）。位移不是放寬——`unclassified` 仍是 0，
    # 而 bash 那 3 支由「永遠 skip」變成「在 Windows 上真的跑」。
    # 🔴 R82／HELM-02 重釘 `runtime-skipTest` 16→18（**非放寬**：本表判準是「相等」，
    # 任一格變動都必須有人回來改，而失敗訊息自己會印出該填的數字 ⇒ 重釘是設計好的流程）。
    # 哨兵武裝時機由 SessionStart 改到 PostToolUse，該包把
    # `test_context_budget_guard.py::SentinelWiringTest` 原本 2 支端到端分支測試拆成 4 支
    # （SessionStart 不武裝／夠格才武裝／短命不武裝／逃生口），四支都以函式體內
    # `self.skipTest("[WINDOWS-NATIVE-ONLY] …")` 對非 Windows 退場——schtasks 只在 Windows
    # 成立，是鐵律三要求的正確形態，不是隱藏失敗。定位方式同上：對每支 test 檔各以
    # HEAD 版與工作樹版跑一次 `site_class_counts()` 相減。
    # 🔴 同包再 +2（18→20）：`PS_UTF8_PRELUDE` 的**行為**鎖（哨兵取證憑證裡的「下午」被
    # cp950 降解成 `?`）帶兩個函式體內 `self.skipTest(...)`——① 非 Windows 退場
    # （powershell.exe 5.1 的主控台 codepage 行為只在 Windows 成立）；② 本機 codepage
    # 已是 UTF-8 時**缺陷重現不了**就明說跳過，而不是把「重現不了」讀成「已修好」。
    "tools/tests": {
        "windows-only": 14,
        "posix-only": 10,
        "tool-absence": 36,
        "runtime-skipTest": 20,
        "unclassified": 0,
    },
    # 🔴 R81 包 F 重釘 `windows-only` 9→10：並行包在
    # `AutoClaude/tests/test_perception_platform_honesty.py:330` 新增了一個
    # `skipif(sys.platform != "win32")` 站點（該檔的 skip reason 同輪由本包補上
    # `[WINDOWS-NATIVE-ONLY]`）。前一輪（R80）的重釘理由是另一個檔案
    # （`AutoClaude/tests/tools/test_run_local_nightly_static.py`，8→9）。
    # 這正是「相等」判準的設計意圖生效——新站點在落地當回合就被逼進帳。
    # 若後續再有包動這些檔，收輪者必須依當場實測重釘（同 `MIN_TESTS` 的紀律）。
    # 🔴 R82 包 A2（CARRIER-01）重釘 `posix-only` 6→5／`tool-absence` 16→17：
    # `tools/test_run_local_nightly_sh_static.py` 的 `_POSIX_ONLY` 由
    # `sys.platform == "win32" or shutil.which("bash") is None`（posix-only）改成
    # 「解不到可用 bash」（tool-absence）。這是**分類訂正**不是額度位移：那 12 支被
    # 標成「別的平台才有驗證價值」，而它們在 Windows 上實測全綠（25 passed）。
    "AutoClaude/tests": {
        "windows-only": 10,
        "posix-only": 5,
        "tool-absence": 17,
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
    LATEST_FSM_TESTS_TREE: {   # 本輪納入；此前整棵樹的 4 個站點對所有機械物隱形
        "windows-only": 1,
        "posix-only": 1,
        "tool-absence": 2,
        "runtime-skipTest": 0,
        "unclassified": 0,
    },
}

# ── 標籤詞彙表的**成員檢查**（本輪；R76 §3 finding F3 點名、當輪未修）──────────
# 缺陷本體：`ALL_SKIP_TAGS` 只被用來「比對已知標籤」，**沒有任何機械物反向檢查**
# 「reason 開頭出現了一個 `[XXX-YYY]` 形態、但它不在 `ALL_SKIP_TAGS`」。於是
# **發明一個新標籤是零成本的**：人看起來有標籤、機器看起來沒標籤，兩份報表對同一支
# skip 的分類會不一致。落地當回合實測：四棵活測試樹的 122 個字面 reason 站點中，
# 有 2 個用了未登記的標籤。
#
#: 未登記標籤的**存量棘輪**（{標籤字面: 站點數}）。判準是**相等**（同本檔其餘棘輪
#: 的理由）：清掉要回來下修、新增要回來上修並在 PR 說明——兩個方向都必須有人動手。
#: 現存這一筆住在 `tools/tests/test_bash_probe_spec_contract.py`，該檔不在本包的檔案
#: 所有權內；本包同輪已把自己那一筆（`test_subprocess_encoding_hygiene.py`）改成
#: `[TOOL-ABSENCE]`，故本表由 2 起始值降為 1。
_UNREGISTERED_TAG_DEBT: dict[str, int] = {
    "[CARRIER-NO-DISCRIMINATION]": 1,
}

#: 🔴 R79（D-skipped #3）：**非字面 reason**（f-string／`+` 串接）那一面的獨立存量帳。
#:
#: 為何獨立一張表而不是併進上表：兩者是**兩個不同的量測母體**。上表數的是
#: `skip_decorator_sites()` 抽得到字面值的站點，下表數的是
#: `windows_skip_tags.nonliteral_skip_reason_prefixes()` 補回來的那一批——後者此前對本鎖
#: 結構上隱形（`literal_eval` 失敗即整個站點丟掉），R76 指名的唯一已知實例
#: （`[TOOL-MISSING]`）正好長成那樣，於是「已知缺陷 → 建了鎖 → 鎖看不到那個已知缺陷」
#: 隱形三輪。把兩批塞進同一張表，會讓其中一面的站點增減去污染另一面的對帳
#: （落地當回合實測：併表當場弄紅 `test_run_root_unittests.UnregisteredSkipTagVocabularyTest`
#: 的 3 支合成語料測試——那 3 支的語料只含上表那一筆，本來就不該為下表的存量負責）。
#:
#: 🔴 R81 包 F：這張表**已清空**（三筆全部改成 `[TOOL-ABSENCE]`，純字串替換、零邏輯改動）：
#:   · `[TOOL-MISSING]`       `tools/tests/test_dev_start.py` 的 setUp（該站點同輪另有更大的
#:                            修正：它宣稱的「找不到舊直譯器」是假診斷，見 `_find_sub_min_
#:                            interpreter` 的 WHY；今天這兩支已經真的在跑，連 skip 都沒了）
#:   · `[PG-CORPUS-MISSING]`／`[PG-CORPUS-STALE]`
#:                            `AutoClaude/tests/integration/test_pgvector_real_recall.py`
#: 表空掉即**升級為零容忍**：任何新的未登記標籤（含把這三個字面寫回去）當場紅。
_NONLITERAL_TAG_DEBT: dict[str, int] = {}

#: reason 開頭的標籤形態：`[大寫段-大寫段…]`。刻意只認**開頭**——標籤的契約就是
#: 「加在 reason 的最前面」，句中提到某個 `[XXX]` 字樣不是在標記這支 skip。
_TAG_PREFIX_RE = re.compile(r"^\s*(\[[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+\])")


def unregistered_tag_problems(
    reasons: Iterable[str], *, debt: Mapping[str, int] | None = None
) -> list[str]:
    """純函式：reason 開頭用了不在 `ALL_SKIP_TAGS` 內的標籤 ⇒ 與棘輪對帳。

    回傳問題描述清單；空＝合格。判準對兩個方向都說話（見 `_UNREGISTERED_TAG_DEBT`）。

    `debt` 預設是字面 reason 那一面的帳（`_UNREGISTERED_TAG_DEBT`）；非字面那一面請顯式
    傳 `_NONLITERAL_TAG_DEBT`——兩批是不同的量測母體，混帳會互相污染對帳（見該常數 WHY）。
    """
    ledger = _UNREGISTERED_TAG_DEBT if debt is None else debt
    seen: dict[str, int] = {}
    for reason in reasons:
        found = _TAG_PREFIX_RE.match(reason)
        if found and found.group(1) not in ALL_SKIP_TAGS:
            seen[found.group(1)] = seen.get(found.group(1), 0) + 1
    problems: list[str] = []
    for tag in sorted(set(seen) | set(ledger)):
        got, want = seen.get(tag, 0), ledger.get(tag, 0)
        if got == want:
            continue
        fix = (
            f"改用 {TOOL_ABSENCE_SKIP_TAG}（或其他已登記標籤），"
            f"或把 `{tag}` 具名登記進 skip_tag_policy.ALL_SKIP_TAGS 並寫 WHY"
            if got > want else
            f"存量已清掉，請把 skip_tag_policy._UNREGISTERED_TAG_DEBT['{tag}'] 改為 {got}"
            "（清空時整列刪除；本表空掉即升級為零容忍）"
        )
        problems.append(
            f"未登記的 skip 標籤 `{tag}`：實測 {got} 個站點、棘輪 {want}——{fix}"
        )
    return problems


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
