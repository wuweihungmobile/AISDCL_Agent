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
from collections.abc import Mapping
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


def report_windows_skip_tag_exemption_problems(result) -> list[str]:
    """具名豁免表的自檢（本輪；回傳非空 ⇒ 呼叫端須讓 rc 為 1）。

    stale 那一面的資料由**同一支偵測器**在「豁免表當成空的」條件下重跑取得——
    不另寫一份等價實作，否則證明的只是我重寫的那份是對的。
    它在 Windows 上整組早退（見 `untagged_windows_like_skips`），故那一面只在
    非 Windows 上啟用；格式面不分平台。
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
                                  flagged_without_exempt=flagged)
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


def report_untagged_windows_skip_decorators(tests_dir: Path, pattern: str) -> list[str]:
    """跑靜態掃描並印出問題；回傳問題描述清單（非空 ⇒ 呼叫端須讓 rc 為 1）。

    掃到 0 份檔案時 fail-closed（掃描面消失本身就是失敗，同 `collection_gaps` 精神）。
    R74：射程擴為三棵活測試樹、並同時跑**反方向**（POSIX 側）的標籤棘輪。
    R75：另跑**站點分類普查**棘輪——那是 QA-R74-02 的修法核心：讓每一個被抽到的站點都
    落在某一格，於是「方向判不出來」不再等於「對所有機械物隱形」。
    """
    problems: list[str] = []
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
            problems.append(f"掃描面為空：{tree} 底下找不到任何 {pattern}")
        file_counts[tree] = len(tree_sources)
        sources.update({f"{tree}/{rel}": src for rel, src in tree_sources.items()})
        posix_counts[tree] = len(untagged_non_windows_skip_decorators(tree_sources))
        census[tree] = site_class_counts(tree_sources)
    unregistered = unregistered_windows_like_predicates(sources)
    offenders = untagged_windows_skip_decorators(sources)
    problems += [f"未登記的 Windows 述詞：{label} 條件 {cond!r}" for label, cond in unregistered]
    problems += [f"漏標：{label}（命中關鍵詞 {hit!r}）" for label, hit, _ in offenders]
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
    problems += [f"反方向標籤棘輪：{msg}" for msg in ratchet]
    problems += [f"掃描面下限：{msg}" for msg in floors]
    problems += [f"站點分類普查：{msg}" for msg in census_problems]
    problems += [f"標籤詞彙表：{msg}" for msg in vocab]
    if not problems:
        return []
    if census_problems:
        print(
            f"❌ 站點分類普查 {len(census_problems)} 筆（R75／QA-R74-02）——方向判不出來的"
            f"站點此前對**所有**機械物隱形（實測曾有 61% 的站點落在此），普查表的用途就是"
            f"讓每一個站點都落在某一格、數字可被稽核：",
            file=sys.stderr,
        )
        for msg in census_problems:
            print(f"   - {msg}", file=sys.stderr)
        unclassified = unclassified_sites(sources)
        if unclassified:
            print(f"   `unclassified` 明細（共 {len(unclassified)} 筆）：", file=sys.stderr)
            for label, deco, cond in unclassified:
                print(f"     · {label} {deco}({cond!r})", file=sys.stderr)
    if floors:
        for msg in floors:
            print(f"❌ 掃描面下限：{msg}", file=sys.stderr)
    if vocab:
        print(
            f"❌ 標籤詞彙表 {len(vocab)} 筆——`ALL_SKIP_TAGS` 此前只被用來「比對已知"
            f"標籤」，沒有任何機械物反向問「這個看起來像標籤的字面有沒有登記過」，"
            f"於是**發明新標籤是零成本的**（人看起來有標籤、機器看起來沒標籤）：",
            file=sys.stderr,
        )
        for msg in vocab:
            print(f"   - {msg}", file=sys.stderr)
    if ratchet:
        print(
            f"❌ 反方向（POSIX 側）標籤棘輪 {len(ratchet)} 筆——`{WINDOWS_NATIVE_SKIP_TAG}` "
            f"只照亮「非 Windows 上沒跑到的 Windows 專屬測試」，反方向（**因為跑在 "
            f"Windows 而失去的覆蓋**）此前一個機械物都沒有，複審者無法分辨哪幾筆是真的"
            f"覆蓋損失（R74／PKG-4 E‧F）：",
            file=sys.stderr,
        )
        for msg in ratchet:
            print(f"   - {msg}", file=sys.stderr)
    print(
        f"❌ 靜態標籤掃描（不分平台）發現 {len(problems)} 個問題——本掃描存在的理由是"
        f"「runtime 那道鎖在 Windows 上整組早退」，Windows 側三道閘門若沒有它就是同一個"
        f"瞎點的三份複本（R72）：",
        file=sys.stderr,
    )
    for label, condition in unregistered:
        print(
            f"   - {label}\n       條件 {condition!r} 看起來像 Windows 述詞、卻未登記於 "
            f"skip_tag_policy._WINDOWS_SKIP_PREDICATE_MARKERS ⇒ 方向判不出來、該站點會"
            f"落進 `unclassified`。修法：把該述詞加進登記表。",
            file=sys.stderr,
        )
    for label, hit, reason in offenders:
        print(f"   - {label}（命中關鍵詞 {hit!r}）\n       理由：{reason}", file=sys.stderr)
    if offenders:
        print(
            f"   修法：把 {WINDOWS_NATIVE_SKIP_TAG} 加在該 skip reason 的最前面"
            "（判準：方向為「非 Windows 上才 skip」⇒ 正是本標籤的語意）。",
            file=sys.stderr,
        )
    return problems


__all__ = [
    "ALL_SKIP_TAGS", "MAC_NATIVE_SKIP_TAG", "NON_WINDOWS_SKIP_TAGS",
    "POSIX_NATIVE_SKIP_TAG", "SITE_CLASSES", "SkipSite", "TOOL_ABSENCE_SKIP_TAG",
    "WINDOWS_NATIVE_SKIP_TAG", "all_skips", "is_tool_probe",
    "exemption_problems", "posix_tag_ratchet_problems",
    "read_test_sources", "report_all_skips",
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
