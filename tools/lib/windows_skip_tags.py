#!/usr/bin/env python3
"""skip 標籤家族的**公開門面**（thin facade）＋ 閘門編排（R43／R67-F11／R72／R74／R75）。

🔴 R75 拆分：本檔原本一檔身兼四種職責（508 code／727 raw 行）。把 monorepo 根層
`tools/` 納入 `AutoClaude/tools/check_loc_budget.py` 的 LOC 分級後，`tools/lib/` 的
`guardrail_lib` tier ≤400 當場把它擋下——而那正是判準想說的事。四種職責已拆為：

  ① `skip_tag_policy`      政策常數與棘輪基線（唯一真相源）
  ② `skip_static_scan`     讀原始碼 AST：抽站點、判方向、分類
  ③ `skip_source_io`       測試樹檔案 I/O
  ④ `skip_runtime_report`  讀 `unittest.TestResult` 的 runtime 彙整

本檔保留三件事，一件都不是業務邏輯：
  · **公開名再匯出**——`tools/run_root_unittests.py`、`tools/tests/test_run_root_unittests.py`、
    `tools/tests/test_platform_neutral_paths.py` 與文件裡的引用全部指向本檔的名字，改名
    的成本遠大於收益（Rule 3）。再匯出的是**同一個物件**，故既有
    `mock.patch.dict(run_root_unittests._WINDOWS_SKIP_TAG_EXEMPT, …)` 照常生效。
  · **常數注入**——`untagged_*` 幾支刻意做成「把**本檔命名空間**的常數傳進實作」的薄包裝。
    這是 `tools/tests/test_run_root_unittests.py::test_hints_and_tag_are_shared_with_the_
    runtime_lock_not_copied` 明文鎖住的契約：`mock.patch.object(windows_skip_tags,
    "_WINDOWS_LIKE_SKIP_HINTS", …)` 之後判定必須跟著變。若實作直接讀自己模組層的常數，
    那道注入會靜默失效（patch 到的是另一個名字）——這正是「再匯出退化成複製」的形態。
  · **閘門編排**——`report_untagged_windows_skip_decorators()` 把①②③串起來並收斂 rc。

判準的兩個面（互補，缺一即有結構性瞎點）仍然成立，只是各住各的模組：
  · **runtime**（④）：看本次真的 skip 了什麼。只在**非** Windows 上說話（在 Windows 上
    照掃必然假紅，理由見該模組）。
  · **靜態**（②）：讀原始碼、看 skip 條件的**方向**，與「現在跑在哪個平台」無關 ⇒ 三個
    平台都說話，補上 runtime 面在 Windows 的早退。
"""
from __future__ import annotations

import os  # 只由 `running_on_windows()` 讀（唯一站點）；**不再**是 patch 目標，WHY 見該函式
import sys
from collections.abc import Collection, Mapping
from pathlib import Path

# 本檔住 `<repo>/tools/lib/`：與四支實作模組同層，故直接以模組名 import（呼叫端一律
# 已把 `tools/lib` 放上 sys.path，見 `tools/lib/platform_utils.py` 檔頭的同一慣例）。
sys.path.insert(0, str(Path(__file__).resolve().parent))

# 下方 I001 的抑制＝本區塊刻意不讓 isort 重排：它必須整批留在上方那行 `sys.path.insert`
# **之後**（`tools/run_root_unittests.py` 對 `from lib.windows_skip_tags import (…)` 用的
# 是同一招）。逐名抑制 F401＝**再匯出**的意思。
# ⚠️ 本段刻意不逐字寫出抑制指示的字面，否則 ruff 會把註解裡那串當成真的指示去解析並警告。
from skip_runtime_report import (  # noqa: E402, I001
    all_skips,  # noqa: F401  ← 再匯出
    report_all_skips,
    report_untagged_windows_like_skips as _report_untagged_windows_like_skips,
    report_windows_native_skips,  # noqa: F401  ← 再匯出
    untagged_windows_like_skips as _untagged_windows_like_skips,
    windows_native_skips,  # noqa: F401  ← 再匯出
)
from skip_source_io import read_test_sources, scan_tree_sources  # noqa: E402,F401
from skip_static_scan import (  # noqa: E402
    SITE_CLASSES,  # noqa: F401  ← 再匯出
    SkipSite,  # noqa: F401  ← 再匯出
    _is_windows_predicate,  # noqa: F401  ← 再匯出（既有引用）
    _predicate_value_on_windows,  # noqa: F401  ← 再匯出（既有引用）
    is_tool_probe,  # noqa: F401  ← 再匯出
    site_class,  # noqa: F401  ← 再匯出
    site_class_counts,
    site_class_detail,  # noqa: F401  ← 再匯出
    skip_decorator_sites,  # noqa: F401  ← 再匯出
    skipped_platform,  # noqa: F401  ← 再匯出
    suspect_unregistered_leaves,  # noqa: F401  ← 再匯出
    unclassified_sites,
    unregistered_windows_like_predicates,
    untagged_non_windows_skip_decorators as _untagged_non_windows_skip_decorators,
    untagged_tool_absence_sites as _untagged_tool_absence_sites,
    untagged_windows_skip_decorators as _untagged_windows_skip_decorators,
)
from skip_tag_policy import (  # noqa: E402
    _CACHE_DIR_NAMES,  # noqa: F401  ← 再匯出（既有引用：test_ps_engine_ssot 引為先例）
    _EXEMPT_HANDOVER_RE,  # noqa: F401  ← 再匯出（本輪：豁免格式面的判準本體）
    _NONLITERAL_TAG_DEBT,  # R79：非字面 reason 那一面的獨立存量帳
    _POSIX_TAG_RATCHET,  # noqa: F401  ← 再匯出
    _SITE_CLASS_CENSUS,  # noqa: F401  ← 再匯出
    _TREE_FILE_FLOORS,  # noqa: F401  ← 再匯出
    _WINDOWS_LIKE_SKIP_HINTS,
    _WINDOWS_SKIP_PREDICATE_MARKERS,  # noqa: F401  ← 再匯出（訊息文字指向它）
    _WINDOWS_SKIP_TAG_EXEMPT,
    ALL_SKIP_TAGS,  # noqa: F401  ← 再匯出
    MAC_NATIVE_SKIP_TAG,  # noqa: F401  ← 再匯出
    NON_WINDOWS_SKIP_TAGS,
    POSIX_NATIVE_SKIP_TAG,
    TOOL_ABSENCE_SKIP_TAG,
    TREE_FLOOR_RATIO,  # noqa: F401  ← 再匯出
    WINDOWS_NATIVE_SKIP_TAG,
    exemption_problems,
    posix_tag_ratchet_problems,  # noqa: F401  ← 再匯出
    site_class_census_problems,
    tree_floor_problems,
    unregistered_tag_problems,
)

# 本模組住 `<repo>/tools/lib/`：parents[1]＝tools、parents[2]＝repo 根。
_REPO_ROOT = Path(__file__).resolve().parents[2]
_REPO_TESTS_DIR = _REPO_ROOT / "tools" / "tests"


def running_on_windows() -> bool:
    """本家族唯一的「現在跑在哪個平台」讀取點，同時是測試注入的**唯一**接縫。

    🔴 立案（`DEF-101-996`，R82 複審 SA B-1 當回合實測）：在它之前，唯一的注入手法是
    `mock.patch.object(windows_skip_tags.os, "name", "posix")`——而 `windows_skip_tags.os`
    **就是** stdlib 那一個 `os` 模組物件（本檔再匯出的一律是同一個物件，見檔頭），所以那
    一行改的是**整個行程**的 `os.name`，射程遠遠超出這個家族。CPython 3.11 的
    `pathlib.Path.__new__` 正是靠 `os.name == "nt"` 決定生 `WindowsPath` 還是 `PosixPath`
    ⇒ patch 生效期間，在 Windows 上**任何**一次 `Path(...)` 都會拋
    `NotImplementedError: cannot instantiate 'PosixPath' on your system`。

    代價不是「有點髒」，是**同一份判準依載具給出相反判決**（實測）：
      · `python -m unittest` 下沒有人在那段期間呼叫 `Path()` ⇒ 看起來完全無害、9 支全過；
      · `pytest` 下 `AssertionRewritingHook.find_spec()` 對**每一支新 import 的模組**都會走
        `_should_rewrite() → absolutepath() → Path()` ⇒ 常駐缺陷注入對照組合成出來的那棵樹
        import 失敗、塌成 `_FailedTest`、收集數低於下限 ⇒ **兩次** `run_with_floor` 都回 1：
        該紅的那一半紅得**理由是錯的**（是 import 炸掉，不是漏標），該綠的那一半永遠綠不了。
    ⇒ 「現在跑在哪個平台」必須有一個**模組層的名字**可以 patch；patch 它不會動到行程全域，
    兩個載具因此看到同一份行為。載具一致性本身已由
    `tools/tests/test_run_root_unittests.py::CarrierVerdictParityTest` 機械看守。
    """
    return os.name == "nt"


# ── 常數注入用的薄包裝（WHY 見檔頭第二點）─────────────────────────────────────────
def untagged_windows_like_skips(result, *, on_windows: bool | None = None):
    """runtime 面漏標檢查；把**本檔**的關鍵詞／豁免／標籤面傳進實作。

    `on_windows=None` 時取本檔的 `running_on_windows()`（**不是**實作模組自己的
    `os.name` 預設）：平台這一軸的注入接縫只能有一個，兩個家就會各自漂移。
    """
    return _untagged_windows_like_skips(
        result,
        on_windows=running_on_windows() if on_windows is None else on_windows,
        hints=_WINDOWS_LIKE_SKIP_HINTS,
        exempt=_WINDOWS_SKIP_TAG_EXEMPT, tag=WINDOWS_NATIVE_SKIP_TAG,
    )


def report_untagged_windows_like_skips(result):
    return _report_untagged_windows_like_skips(
        result, on_windows=running_on_windows(), hints=_WINDOWS_LIKE_SKIP_HINTS,
        exempt=_WINDOWS_SKIP_TAG_EXEMPT, tag=WINDOWS_NATIVE_SKIP_TAG,
    )


def untagged_windows_skip_decorators(sources: Mapping[str, str]):
    return _untagged_windows_skip_decorators(
        sources, hints=_WINDOWS_LIKE_SKIP_HINTS, tag=WINDOWS_NATIVE_SKIP_TAG)


def untagged_non_windows_skip_decorators(sources: Mapping[str, str]):
    return _untagged_non_windows_skip_decorators(sources, tags=NON_WINDOWS_SKIP_TAGS)


def untagged_tool_absence_sites(sources: Mapping[str, str]):
    return _untagged_tool_absence_sites(sources, tag=TOOL_ABSENCE_SKIP_TAG)


def report_windows_skip_tag_exemption_problems(
    result, known_ids: Collection[str] | None = None
) -> list[str]:
    """具名豁免表的自檢（本輪；回傳非空 ⇒ 呼叫端須讓 rc 為 1）。

    stale 那一面的資料由**同一支偵測器**在「豁免表當成空的」條件下重跑取得——
    不另寫一份等價實作，否則證明的只是我重寫的那份是對的。
    它在 Windows 上整組早退（見 `untagged_windows_like_skips`），故那一面只在
    非 Windows 上啟用；格式面不分平台。

    DEF-200-233：另傳兩份資料進判準——`skipped_here`（本次真的 skip 掉的 id，用來把「這支
    測試在本平台跑了」與「豁免過期」分開）與 `known_ids`（本次收集面的全部 id，接手「測試
    已改名／刪除」那一種真過期，**不分平台**）。WHY 全文＝`exemption_problems` 的立案段；
    `known_ids` 為 None 時消失面不判（合成樹呼叫端沿用既有契約）。

    🔴 呼叫端取 `known_ids` 的時機是有陷阱的：`unittest.TestSuite.run()` 會把跑完的每一支
    測試**就地換成 `None`**（`_removeTestAtIndex`，`_cleanup=True` 的預設行為）以釋放記憶體
    ⇒ 收集面必須在 `run()` **之前**取。放到之後取不是靜默的空集合，而是
    `AttributeError: 'NoneType' object has no attribute 'id'`（DEF-200-233 落地當回合被
    `test_run_root_unittests.py` 的端到端測試當場抓到）。
    """
    on_windows = running_on_windows()
    flagged = None
    if not on_windows:
        flagged = {
            test_id: reason
            for test_id, _hit, reason in _untagged_windows_like_skips(
                result, on_windows=False, hints=_WINDOWS_LIKE_SKIP_HINTS,
                exempt={}, tag=WINDOWS_NATIVE_SKIP_TAG,
            )
        }
    problems = exemption_problems(_WINDOWS_SKIP_TAG_EXEMPT,
                                  flagged_without_exempt=flagged,
                                  skipped_here={tid for tid, _ in all_skips(result)},
                                  known_ids=known_ids)
    if problems:
        print(
            f"❌ 具名豁免表 `_WINDOWS_SKIP_TAG_EXEMPT` 有 {len(problems)} 筆問題"
            "——沒有 stale 自檢的豁免表是只進不出的：",
            file=sys.stderr,
        )
        for msg in problems:
            print(f"   - {msg}", file=sys.stderr)
    return problems


# ── 詞彙鎖的輸入面加寬（R79／D-skipped #3）─────────────────────────────────────
#
# 🔴 缺陷本體：R77 為了防「發明一個新標籤是零成本的」而建了 `unregistered_tag_problems`，
# 但它的輸入只有 `skip_decorator_sites()` 抽得到的**字面** reason；而該抽取器對 f-string
# 一律 `literal_eval` 失敗 ⇒ 整個站點被丟掉。R76 指名的**唯一**已知違規實例
# （`tools/tests/test_dev_start.py` 的 `self.skipTest(f"[TOOL-MISSING] …")`）正好長成那樣，
# 於是「已知缺陷 → 建了鎖 → 鎖看不到那個已知缺陷」，隱形三輪。
# 這是 R77／R78 自己診斷出的頭號病（鎖存在但沒有鑑別力）在 skip 治理面上的實例。
#
# 修法就是抽取器的一句話：標籤依契約一定在 reason 的**最前面**，而 f-string 的第一段
# 若是常數就已經含住整個標籤（`ast.JoinedStr.values[0]`）⇒ 取那一段就夠判，不需要求值。
# `+` 串接同理（取最左端）。
#
# 🔴 為何住在這支 facade 而不是 `skip_static_scan`（它才是 AST 那一面的家）：本輪有六個
# 包並行改樹，`skip_static_scan.py` 不在本包的檔案所有權內，跨界改動＝互踩假紅。
# 本函式只做「把既有詞彙鎖的輸入補齊」＝閘門編排，與本檔第三項職責同性質；搬家已列入交棒。
_TAG_BEARING_SKIP_CALLS = frozenset({"skipIf", "skipif", "skipUnless", "skipTest", "skip"})


def _leading_constant(node: object) -> str | None:
    """reason 節點的**開頭常數片段**（f-string／`+` 串接皆可）；取不到回 None。"""
    import ast

    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else None
    if isinstance(node, ast.JoinedStr):
        return _leading_constant(node.values[0]) if node.values else None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _leading_constant(node.left)
    return None


def nonliteral_skip_reason_prefixes(sources: Mapping[str, str]) -> list[str]:
    """純函式：reason **不是**字面字串（f-string／串接）的 skip 站點，其開頭常數片段。

    與 `skip_decorator_sites()` 互補、刻意不重疊：那一支已經處理得到字面值的站點，
    這一支只補它結構上丟掉的那一批，兩者合起來才是「所有寫在原始碼裡的標籤」。
    """
    import ast

    out: list[str] = []
    for name, src in sorted(sources.items()):
        for node in ast.walk(ast.parse(src, filename=name)):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            kind = str(getattr(node.func, "attr", None) or getattr(node.func, "id", None) or "")
            if kind not in _TAG_BEARING_SKIP_CALLS:
                continue
            reason_node: object | None = None
            for kw in node.keywords:
                if kw.arg == "reason":
                    reason_node = kw.value
            if reason_node is None:
                reason_node = node.args[1] if len(node.args) > 1 else node.args[0]
            try:
                if isinstance(ast.literal_eval(reason_node), str):  # type: ignore[arg-type]
                    continue     # 字面值 ⇒ 已由 skip_decorator_sites 承接，不重複計
            except Exception:  # noqa: BLE001 — 取不到字面值正是本函式的射程
                pass
            prefix = _leading_constant(reason_node)
            if prefix:
                out.append(prefix)
    return out


def _is_repo_main_tests_dir(tests_dir: Path) -> bool:
    """呼叫端傳進來的是不是**這個 repo 真正的** `tools/tests`。

    🔴 WHY 這道判斷不可省（R74 落地時當場被既有測試抓到）：
    `report_untagged_windows_skip_decorators` 除了在閘門上被呼叫，也被
    `tools/tests/test_run_root_unittests.py::StaticWindowsSkipTagScanTest` 拿**合成樹**
    呼叫（造一棵含漏標的假樹、斷言 reporter 回恰 1 筆問題）。若把「三棵活測試樹＋逐樹
    檔數下限＋反方向棘輪＋分類普查」無條件套上去，那些合成樹會突然受 repo 專屬判準管轄
    ——實測回 10 筆問題而非 1 筆，合成樹的鑑別力被雜訊淹沒。
    **只有真的在掃這個 repo 時，才啟用 repo 專屬的那幾層。**
    """
    try:
        return tests_dir.resolve() == _REPO_TESTS_DIR.resolve()
    except OSError:  # pragma: no cover - 路徑不可解析時一律當「不是」（保守）
        return False


# ── 問題類別登記表：計數與明細的**唯一**共同來源（R83；缺陷本體與修法選型見下）──────
#
# 🔴 缺陷本體（舵手當回合實測：`python tools/run_root_unittests.py` 整份輸出只有 2 行）：
# `problems` 是**七個類別的總和**，而總表頭印的是 `len(problems)`、它後面那個明細迴圈
# 卻只涵蓋 `unregistered` 與 `offenders` 兩類 ⇒ 唯一的問題落在別的類別時，讀者看到
# 「發現 1 個問題：」之後**一片空白**，於是去找一個根本不存在的第二筆。七類之中
# `掃描面為空` 更是從頭到尾**沒有任何一段程式碼印它**（`test_empty_scan_surface_is_
# fail_closed` 只讀回傳值，結構上看不見這件事）。
#
# 🔴 修法選型（為何不是「把漏掉的那幾類補進那個明細迴圈」）：那只修掉今天這一筆，並把
# 同一個陷阱原封不動留給下一個新增類別的人——計數與明細各有一個家，而只有一個家會被改
# （本 repo 反覆付過學費的「同一份知識住兩個家」）。故改成**單一資料結構驅動**：問題一律
# 以 `{類別: [明細…]}` 累積、印列面**迭代它本身**，於是「新增一類卻忘了印」結構上不可能
# 發生；表頭數字取 `sum(len(v))`，與印出來的 `   - ` 行同一個來源，兩者脫鉤不可能。
# 剩下的唯一縫隙（新增類別卻沒在本表登記 WHY）由兩道鎖收口：
#   · runtime——未登記的類別**照印**，另加一行點名（漏登記本身是缺陷，但不得因此吃掉
#     問題本文：fail-loud，不是 fail-silent）；
#   · 測試——`tools/tests/test_run_root_unittests.py::ProblemReportItemizationTest` 以 AST
#     讀出生產端那個 dict literal 的鍵，與本表**雙向**比對（多一鍵沒登記＝紅、登記了卻
#     沒有生產者＝紅），所以「忘了印」在**寫出來的當回合**就轉紅，不必等那一類真的觸發。
#
# 值＝該類別的 WHY（原本散在各自的表頭裡，逐句搬進來，資訊不減）。順序即輸出與回傳
# 順序，刻意沿用修前的順序讓既有呼叫端與測試的字串比對不受影響。
_PROBLEM_CATEGORY_WHY: dict[str, str] = {
    "掃描面為空": "掃描面消失本身就是失敗（fail-closed）：讀到 0 份檔案時，"
                  "「沒發現違規」與「根本沒去看」的外觀完全相同",
    "未登記的 Windows 述詞": "述詞沒登記於 skip_tag_policy._WINDOWS_SKIP_PREDICATE_MARKERS "
                             "⇒ 方向判不出來 ⇒ 該站點落進 `unclassified` 而靜默漏掉漏標，"
                             "這是本掃描唯一的靜默失效路徑",
    "漏標": "runtime 那道鎖在 Windows 上整組早退，Windows 側三道閘門若沒有本靜態掃描"
            "就是同一個瞎點的三份複本（R72）",
    "反方向標籤棘輪": f"`{WINDOWS_NATIVE_SKIP_TAG}` 只照亮「非 Windows 上沒跑到的 Windows "
                      "專屬測試」，反方向（**因為跑在 Windows 而失去的覆蓋**）此前一個機械物"
                      "都沒有，複審者無法分辨哪幾筆是真的覆蓋損失（R74／PKG-4 E‧F）",
    "掃描面下限": "下限對「掃描面靜默縮小」的鑑別力會隨樹長大而單調衰減，過期即失去意義",
    "站點分類普查": "方向判不出來的站點此前對**所有**機械物隱形（實測曾有 61% 的站點落在此），"
                    "普查表的用途就是讓每一個站點都落在某一格、數字可被稽核（R75／QA-R74-02）",
    "標籤詞彙表": "`ALL_SKIP_TAGS` 此前只被用來「比對已知標籤」，沒有任何機械物反向問"
                  "「這個看起來像標籤的字面有沒有登記過」，於是**發明新標籤是零成本的**"
                  "（人看起來有標籤、機器看起來沒標籤）",
}


def render_problem_report(
    buckets: Mapping[str, list[str]],
    extra: Mapping[str, list[str]] | None = None,
) -> list[str]:
    """純函式（無列印副作用）：把 `{類別: [明細…]}` 攤成要印出去的每一行。

    🔴 本函式就是「每一筆問題都有人印」這個不變量的**唯一**擔保，故它刻意只迭代
    `buckets` 自己：任何進得了 buckets 的類別必然被走到，表頭數字亦取自同一份資料。
    `extra` 是各類別的補充明細（逐站點理由／修法指路），它自己也受同一條不變量管轄
    ——歸屬不到任何 bucket 的 extra 一律照印並點名，不得靜默丟棄。
    """
    total = sum(len(msgs) for msgs in buckets.values())
    # 這句「本掃描為何存在」修前掛在總表頭上、無條件印出，故仍留在無條件印出的這一行
    # （移進某一類的 WHY 會讓它只在那一類觸發時才看得到）。
    lines = [
        f"❌ 靜態標籤掃描（不分平台）發現 {total} 個問題，分屬 {len(buckets)} 類"
        f"（逐類明細如下，每一筆都在）——本掃描存在的理由是「runtime 那道鎖在 Windows 上"
        f"整組早退」，Windows 側三道閘門若沒有它就是同一個瞎點的三份複本（R72）："
    ]
    extra = dict(extra or {})
    for category, msgs in buckets.items():
        why = _PROBLEM_CATEGORY_WHY.get(category)
        if why is None:
            why = ("🔴 這個類別沒有登記在 windows_skip_tags._PROBLEM_CATEGORY_WHY——"
                   "漏登記本身是缺陷，請補上；問題本文照印於下，不因此被吃掉")
        lines.append(f"  ▍{category}（{len(msgs)} 筆）——{why}：")
        lines += [f"   - {msg}" for msg in msgs]
        lines += extra.pop(category, [])
    for category, msgs in extra.items():
        lines.append(f"  ▍🔴 補充明細 `{category}` 找不到對應的問題類別（鍵名疑似打錯），照印：")
        lines += list(msgs)
    return lines


def _ordered_buckets(raw: Mapping[str, list[str]]) -> dict[str, list[str]]:
    """丟掉空類別並依 `_PROBLEM_CATEGORY_WHY` 定序；未登記的鍵**保留**並排在最後。

    「未登記就丟掉」會讓漏登記變成靜默資訊損失——那正是本輪要修的病，故此處只排序。
    """
    out = {k: list(raw[k]) for k in _PROBLEM_CATEGORY_WHY if raw.get(k)}
    out.update({k: list(v) for k, v in raw.items() if v and k not in _PROBLEM_CATEGORY_WHY})
    return out


def report_untagged_windows_skip_decorators(tests_dir: Path, pattern: str) -> list[str]:
    """跑靜態掃描並印出問題；回傳問題描述清單（非空 ⇒ 呼叫端須讓 rc 為 1）。

    掃到 0 份檔案時 fail-closed（掃描面消失本身就是失敗，同 `collection_gaps` 精神）。
    R74：射程擴為三棵活測試樹、並同時跑**反方向**（POSIX 側）的標籤棘輪。
    R75：另跑**站點分類普查**棘輪——那是 QA-R74-02 的修法核心：讓每一個被抽到的站點都
    落在某一格，於是「方向判不出來」不再等於「對所有機械物隱形」。
    R83：問題改以 `{類別: [明細…]}` 累積、交給 `render_problem_report` 逐類印出，
    修掉「表頭報 N 筆、明細只涵蓋其中兩類」的低報（WHY 見 `_PROBLEM_CATEGORY_WHY`）。
    """
    empty_trees: list[str] = []
    repo_mode = _is_repo_main_tests_dir(tests_dir)
    if repo_mode:
        trees = scan_tree_sources(_REPO_ROOT, tests_dir, pattern)
    else:
        # 合成樹（單元測試注入）：維持 R72 的單棵樹契約，不套 repo 專屬的那幾層。
        trees = {tests_dir.name: read_test_sources(tests_dir, pattern)}
    sources: dict[str, str] = {}
    posix_counts: dict[str, int] = {}
    file_counts: dict[str, int] = {}
    census: dict[str, dict[str, int]] = {}
    for tree, tree_sources in trees.items():
        if not tree_sources:
            empty_trees.append(f"{tree} 底下找不到任何 {pattern}")
        file_counts[tree] = len(tree_sources)
        sources.update({f"{tree}/{rel}": src for rel, src in tree_sources.items()})
        posix_counts[tree] = len(untagged_non_windows_skip_decorators(tree_sources))
        census[tree] = site_class_counts(tree_sources)
    unregistered = unregistered_windows_like_predicates(sources)
    offenders = untagged_windows_skip_decorators(sources)
    ratchet = posix_tag_ratchet_problems(posix_counts) if repo_mode else []
    floors = tree_floor_problems(file_counts) if repo_mode else []
    census_problems = site_class_census_problems(census) if repo_mode else []
    # 本輪：標籤詞彙表的成員檢查。射程與上面三道一致（只在 repo 模式），資料取自
    # **同一批** sources 抽出的字面 reason，不另掃一次磁碟。
    # R79（D-skipped #3）：輸入面補上「reason 不是字面字串」的站點（f-string／串接）。
    # 修前那一批對本鎖結構上隱形，而唯一已知的違規實例正好落在裡面。
    # 兩面各自對自己的存量帳（WHY 見 `skip_tag_policy._NONLITERAL_TAG_DEBT`）。
    vocab = (
        unregistered_tag_problems([s.reason for s in skip_decorator_sites(sources)])
        + unregistered_tag_problems(nonliteral_skip_reason_prefixes(sources),
                                    debt=_NONLITERAL_TAG_DEBT)
    ) if repo_mode else []
    # 🔴 這個 dict literal 是**生產端的唯一入口**（不再有 `problems.append`／`problems +=`
    # 散在各處）：新增一類就是在這裡多一鍵，而少了 `_PROBLEM_CATEGORY_WHY` 的對應登記時，
    # `ProblemReportItemizationTest` 的 AST 雙向比對當場轉紅。鍵即輸出前綴，故回傳字串
    # 與修前逐字相同。
    buckets = _ordered_buckets({
        "掃描面為空": empty_trees,
        "未登記的 Windows 述詞": [f"{label} 條件 {cond!r}" for label, cond in unregistered],
        "漏標": [f"{label}（命中關鍵詞 {hit!r}）" for label, hit, _ in offenders],
        "反方向標籤棘輪": ratchet,
        "掃描面下限": floors,
        "站點分類普查": census_problems,
        "標籤詞彙表": vocab,
    })
    if not buckets:
        return []
    for line in render_problem_report(buckets, _problem_extra_detail(
            sources, unregistered, offenders, census_problems)):
        print(line, file=sys.stderr)
    return [f"{category}：{msg}" for category, msgs in buckets.items() for msg in msgs]


def _problem_extra_detail(
    sources: Mapping[str, str],
    unregistered: list[tuple[str, str]],
    offenders: list[tuple[str, str, str]],
    census_problems: list[str],
) -> dict[str, list[str]]:
    """各類別的補充明細（逐站點理由／修法指路）——與一行式的問題本文分開。

    🔴 只為**真的有問題**的類別生產（`census_problems` 為空時不去算 `unclassified`）：
    補充明細沒有自己的計數，混進沒有問題的類別只會讓讀者以為那一類也紅了。
    """
    extra: dict[str, list[str]] = {}
    if unregistered:
        extra["未登記的 Windows 述詞"] = [
            "       修法：把該述詞加進 skip_tag_policy._WINDOWS_SKIP_PREDICATE_MARKERS。"
        ]
    if offenders:
        extra["漏標"] = [f"       · {label} 的理由：{reason}" for label, _, reason in offenders] + [
            f"       修法：把 {WINDOWS_NATIVE_SKIP_TAG} 加在該 skip reason 的最前面"
            "（判準：方向為「非 Windows 上才 skip」⇒ 正是本標籤的語意）。"
        ]
    if census_problems:
        unclassified = unclassified_sites(sources)
        if unclassified:
            extra["站點分類普查"] = [
                f"       `unclassified` 明細（共 {len(unclassified)} 筆）："
            ] + [f"         · {label} {deco}({cond!r})" for label, deco, cond in unclassified]
    return extra


__all__ = [
    "ALL_SKIP_TAGS", "MAC_NATIVE_SKIP_TAG", "NON_WINDOWS_SKIP_TAGS",
    "POSIX_NATIVE_SKIP_TAG", "SITE_CLASSES", "SkipSite", "TOOL_ABSENCE_SKIP_TAG",
    "WINDOWS_NATIVE_SKIP_TAG", "all_skips", "is_tool_probe",
    "exemption_problems", "posix_tag_ratchet_problems",
    "read_test_sources", "render_problem_report", "report_all_skips",
    "report_untagged_windows_like_skips", "report_untagged_windows_skip_decorators",
    "report_windows_native_skips", "report_windows_skip_tag_exemption_problems",
    "running_on_windows", "scan_tree_sources", "site_class",
    "site_class_census_problems", "site_class_counts", "skip_decorator_sites",
    "skipped_platform", "tree_floor_problems", "unclassified_sites",
    "untagged_non_windows_skip_decorators", "untagged_tool_absence_sites",
    "untagged_windows_like_skips", "untagged_windows_skip_decorators",
    "unregistered_tag_problems", "unregistered_windows_like_predicates",
    "windows_native_skips",
]
