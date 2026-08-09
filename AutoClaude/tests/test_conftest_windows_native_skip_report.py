"""conftest.py 的 `[WINDOWS-NATIVE-ONLY]` skip 可見度機制回歸鎖
（R44，DEF-101-348 方向①補完：tools/tests/ 的 unittest 執行路徑 R43 已鎖住
`tools/run_root_unittests.py::report_windows_native_skips()`，但 AutoClaude/tests/
的 pytest 執行路徑此前完全沒有對等回歸鎖）。

WHY（Rule 9，測意圖非僅行為）：純函式 `windows_native_skips()` 好測，但真正容易
被改壞而不被發現的是 `pytest_terminal_summary()` 這個「印出副作用」本身——例如
標籤比對邏輯被改壞、或印出時機被誤搬到不會在 `-q` 下觸發的 hook。只驗證純函式
回傳值鎖不住「真的有印到終端輸出上」這件事。本檔用 pytest 內建 `pytester`
fixture 以子行程方式真跑一個模擬迷你套件（沙盒 conftest.py 直接複製本套件真實
`tests/conftest.py` 原始碼，而非重新實作一份等價邏輯——確保鎖住的是生產程式碼
本身，不是測試自己編造的替身），斷言真實終端輸出裡「該出現的醒目清單有出現、
不該出現時完全沉默」。三個案例對稱比照
`tools/tests/test_run_root_unittests.py::ReportWindowsNativeSkipsTest` 的既有
三案例設計（tagged-only / plain-only / 全部不 skip）。
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

pytest_plugins = ["pytester"]

_CONFTEST_SOURCE = (Path(__file__).resolve().parent / "conftest.py").read_text(encoding="utf-8")


def _make_sandbox(pytester, *, tagged_skip: bool, plain_skip: bool) -> None:
    """在 pytester 沙盒內佈署「真實 conftest.py 原始碼」+ 一支迷你測試套件。

    `tagged_skip`/`plain_skip` 控制對應測試是否真的觸發 skip（True＝skip）。
    """
    pytester.makeconftest(_CONFTEST_SOURCE)
    pytester.makepyfile(
        test_fixture_suite=f'''
import pytest

@pytest.mark.skipif({tagged_skip!r}, reason="[WINDOWS-NATIVE-ONLY] 僅原生 Windows 才具驗證價值")
def test_tagged():
    pass

@pytest.mark.skipif({plain_skip!r}, reason="本機缺某工具，一般性 skip")
def test_plain():
    pass

def test_always_runs():
    assert True
'''
    )


def test_tagged_skip_prints_highlighted_section(pytester):
    """帶標籤的 skip 必須被獨立點名，且清單裡要看得到該測試的 nodeid。"""
    _make_sandbox(pytester, tagged_skip=True, plain_skip=False)
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=2, skipped=1)
    result.stdout.fnmatch_lines(
        [
            "*WINDOWS-NATIVE-ONLY SKIPS*",
            "*1 * Windows *",
            "*test_tagged*",
        ]
    )


def test_plain_skip_alone_is_not_flagged(pytester):
    """無標籤的一般 skip 不應觸發醒目清單（不能把所有 skip 都誤標成 Windows 專屬）。"""
    _make_sandbox(pytester, tagged_skip=False, plain_skip=True)
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=2, skipped=1)
    assert "WINDOWS-NATIVE-ONLY" not in result.stdout.str()


def test_no_skips_prints_nothing(pytester):
    """沒有任何 skip 時，不應印出空的醒目清單區塊（零 skip＝零雜訊）。"""
    _make_sandbox(pytester, tagged_skip=False, plain_skip=False)
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=3)
    assert "WINDOWS-NATIVE-ONLY" not in result.stdout.str()


# ══════════════════════════════════════════════════════════════════════════════
# R76（R76-15 ③）：**反方向**區塊的回歸鎖——此前一個都沒有
# ══════════════════════════════════════════════════════════════════════════════
# WHY 這兩支非補不可（Rule 9）：R74 為「因為跑在 Windows 上而失去的覆蓋」新增了
# `non_windows_native_skips()` ＋ `POSIX/MAC-NATIVE-ONLY SKIPS` 區塊，但本檔三支既有
# 案例只覆蓋 Windows 那一向 ⇒ 反方向的純函式與印出副作用**零回歸鎖，整段刪掉仍全綠**。
# 更糟的是它在真實環境裡也沉默：R76 實測 `AutoClaude/tests` 的 6 個 posix-only 站點
# 0/6 帶標籤，於是這個為了「讓 Windows 側看見覆蓋損失」而建的區塊，在每天真的跑
# Windows 的那一側連續兩輪一行都沒印過——**機制在、鎖不在、輸出恆空**三者同時成立時，
# 沒有任何訊號會出現。R76 補標後同一批測試實測印出 17 行（見
# docs/06_quality/Skipped_Test_Inventory_R76.md §4.4）。


# ══════════════════════════════════════════════════════════════════════════════
# R82 包 A2（DEBT-01）：`[DEBT]` 的承接輪次不得停在**已經到了**的那一輪
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 缺陷本體（R82 掃描實測）：`AutoClaude/tests` 裡 7 支 `[DEBT]` skip 的承接輪次逐字
# 寫著 **R82**——而 R82 就是讀到這句話的那一輪。既有的格式判準
# （`tools/lib/skip_tag_policy._EXEMPT_HANDOVER_RE` ＝ `R\d{2,}`）只問「有沒有寫輪號」，
# 對「這個輪號已經過期」結構上失明 ⇒ 同一個數字可以永遠掛著，而每一輪讀到它的人都會
# 以為下一輪有人負責。這與本檔上半段治的病同型：**機制在、鎖不在，於是沉默的方向是
# 「看起來有人在管」**。
#
# 判準：全樹每一個字面 `承接輪次 R<n>` 的 n 必須 **>** 帳本推得的當前輪次
# （`tools/check_defect_log_crossref.current_round()`——本 repo 對「現在第幾輪」的既有
# 唯一真相源，刻意不寫死第二個常數）。追平的那一輪本支轉紅，逼出一個顯式決定。
#
# 🔴 判準面刻意是「**真的會被印給讀者看的那句 reason**」，不是整個檔案的文字：
# 第一版寫成全檔 regex，當場抓到 4 筆——全部是**訂正註記自己引述舊值**
# （「承接輪次由本輪推到下一輪」那類句子）與歷史敘述。那是 R73 已經判過的形態：訂正註記逐字
# 引述假話會被守著那句假話的鎖抓住，而正確的處置是把判準對準它真正該管的東西，
# 不是把註記寫得閃閃躲躲（那會讓下一個人讀不到「原本錯在哪」）。
# ⇒ 只判 `pytest.skip(...)` 與 `reason=` 這兩種位置裡的字串常數。
#
# 誠實劃界（本鎖抓不到什麼）：
#   · 以**常數／變數**組出輪號的站點（例：`test_ac_matrix_scaffolding.py` 的
#     `R{_AC_DEBT_HANDOVER_ROUND}`）不在本靜態掃描的射程內——那一支由它自己檔內的
#     `test_the_debt_handover_round_is_still_in_the_future` 在 runtime 比對。兩者刻意
#     不互相涵蓋，也刻意不互相取代。
#   · 本鎖只讀原始碼字面，不管那支測試這次有沒有真的 skip。
#   · 註解與 docstring 一律不判（見上段）。

_AUTOCLAUDE_TESTS = Path(__file__).resolve().parent
_HANDOVER_LITERAL_RE = re.compile(r"承接輪次\s*R(\d{2,})")


def _current_round() -> int | None:
    tools_dir = _AUTOCLAUDE_TESTS.parent.parent / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    import check_defect_log_crossref as crossref  # noqa: PLC0415

    ledger = (
        _AUTOCLAUDE_TESTS.parent.parent / "docs" / "06_quality" / "AutoSDD_Defect_Log.md"
    )
    if not ledger.is_file():
        return None
    return crossref.current_round(ledger.read_text(encoding="utf-8"))


def _is_skip_reason_site(node: ast.Call) -> bool:
    """這個 Call 是不是「在產生一句 skip reason」？（`pytest.skip(...)`／帶 `reason=`）"""
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr in {"skip", "skipif"}:
        return True
    return any(kw.arg == "reason" for kw in node.keywords)


def _handover_literals() -> list[tuple[str, int, int]]:
    """全樹掃描 skip reason 內的字面承接輪號：`(檔案相對路徑, 行號, 輪號)`。"""
    found: list[tuple[str, int, int]] = []
    for path in sorted(_AUTOCLAUDE_TESTS.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(_AUTOCLAUDE_TESTS).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and _is_skip_reason_site(node)):
                continue
            for inner in ast.walk(node):
                if not (isinstance(inner, ast.Constant) and isinstance(inner.value, str)):
                    continue
                for hit in _HANDOVER_LITERAL_RE.finditer(inner.value):
                    found.append((rel, inner.lineno, int(hit.group(1))))
    return found


def test_the_handover_scan_surface_is_not_silently_empty():
    """下限釘選：掃描面塌成 0 命中時，下一支會假綠（本 repo 對每道存量掃描的既有慣例）。

    這一支同時是「這個 repo 現在真的還有 `[DEBT]` 欠債」的憑證——欠債全部還清那天
    它會紅，那正確：屆時該把本組整組拿掉，而不是讓一個沒有分母的鎖繼續掛著。
    """
    assert _handover_literals(), (
        "全樹掃不到任何字面 `承接輪次 R<n>`——若欠債真的清光了，請連同本組鎖一起移除；"
        "若只是寫法變了（例如改用常數），請把本鎖的 regex 一併更新，"
        "否則它會在零分母上恆綠"
    )


def test_every_debt_handover_round_is_still_in_the_future():
    """每一筆字面承接輪次都必須指向**還沒到**的輪次。

    合法出口只有兩條，兩條都是決定：①把該欠債做掉；②在同一個 commit 顯式把輪號往後
    推並說明為什麼又推遲一輪。不接受的第三條是把本支刪掉——那會讓輪號退回裝飾字串。
    """
    now = _current_round()
    if now is None:
        import pytest  # noqa: PLC0415

        pytest.skip(
            "[TOOL-ABSENCE] 從缺陷帳本推不出當前輪次——量不到 ≠ 量到合格，本支不放行"
        )
    stale = [(rel, ln, r) for rel, ln, r in _handover_literals() if r <= now]
    assert stale == [], (
        f"以下 `[DEBT]` 的承接輪次已經追平／落後於當前輪 R{now}：{stale}"
        "——輪號到了卻什麼都沒發生，就是「有人負責」的假象（R82 實測 7 筆同時寫著 R82，"
        "而 R82 正是讀到它們的那一輪）。合法出口：做掉它，或顯式把輪號往後推並說明理由"
    )


def _make_reverse_sandbox(pytester, *, posix_tagged: bool, mac_tagged: bool,
                          untagged: bool) -> None:
    """反方向沙盒：`[POSIX-NATIVE-ONLY]`／`[MAC-NATIVE-ONLY]`／無標籤三種 skip。"""
    pytester.makeconftest(_CONFTEST_SOURCE)
    pytester.makepyfile(
        test_reverse_suite=f'''
import pytest

@pytest.mark.skipif({posix_tagged!r}, reason="[POSIX-NATIVE-ONLY] POSIX 專屬行為")
def test_posix_tagged():
    pass

@pytest.mark.skipif({mac_tagged!r}, reason="[MAC-NATIVE-ONLY] macOS 真機專屬")
def test_mac_tagged():
    pass

@pytest.mark.skipif({untagged!r}, reason="POSIX 專屬行為（作者忘了標）")
def test_untagged():
    pass
'''
    )


def test_reverse_direction_tagged_skips_print_their_own_section(pytester):
    """兩種反方向標籤都必須讓區塊印出，且逐支 nodeid 看得到。

    意圖：這一段的價值不在「有沒有 skip」——`skipped=N` 早就印了——而在「哪幾支是
    **因為跑在這個平台上**而失去的覆蓋」。少了本支，把 `NON_WINDOWS_SKIP_TAGS` 改成
    只認一種標籤、或把整個 `posix_ids` 分支刪掉，都不會有任何東西轉紅。
    """
    _make_reverse_sandbox(pytester, posix_tagged=True, mac_tagged=True, untagged=False)
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=1, skipped=2)
    result.stdout.fnmatch_lines(
        [
            "*POSIX/MAC-NATIVE-ONLY SKIPS*",
            # 🔴 R82（DOC-01）：錨點由 `*2 * Windows *` 改成 `*2 *{sys.platform}*`。
            # 舊錨點是把「寫死 Windows」這個缺陷同時釘進了鎖裡——修好標題，鎖會紅。
            f"*2 *{sys.platform}*",
        ]
    )
    out = result.stdout.str()
    assert "test_posix_tagged" in out and "test_mac_tagged" in out, out


def test_the_reverse_section_never_hardcodes_a_platform_name(pytester):
    """🔴 R82（DOC-01）：標題與說明行的平台名必須是**這次真的跑在哪**，不得寫死。

    WHY（Rule 9）：修前逐字是「本次跑在 Windows 上失去的覆蓋」，而 2026-08-05 那次
    真的執行過的 macOS CI 輸出裡照樣印著這句話（`gh run view 31021778241 --log`
    實測命中）。這一段的存在理由是「讓這個平台的讀者看見自己這一側的覆蓋損失」，
    標題寫死等於對 macOS 讀者說「這段與你無關」——與它要治的沉默是同一族，方向相反。

    判準刻意分兩半：①實際輸出必須帶 `sys.platform`（動態組字的證據）；②不得出現
    任何其他平台的字面名（否則「f-string 裡再補一句 Windows」照樣能滿足①）。
    """
    _make_reverse_sandbox(pytester, posix_tagged=True, mac_tagged=False, untagged=False)
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=2, skipped=1)
    section = [
        ln for ln in result.stdout.str().splitlines()
        if "POSIX/MAC-NATIVE-ONLY SKIPS" in ln or "失去的覆蓋" in ln or "而沒跑" in ln
    ]
    assert section, "反方向區塊一行都沒印出來"
    joined = "\n".join(section)
    assert sys.platform in joined, (
        f"區塊標題／說明行沒有帶本次的 `sys.platform`（{sys.platform}）：{joined!r}"
        "——平台名疑似又被寫死了"
    )
    others = {"Windows", "win32", "darwin", "macOS", "linux", "Linux"} - {sys.platform}
    for name in sorted(others):
        assert name not in joined, (
            f"區塊裡出現了別的平台名 `{name}`：{joined!r}——那是 DOC-01 的迴歸"
            "（在 macOS runner 上逐字印著「本次跑在 Windows 上」）"
        )


def test_reverse_section_stays_silent_without_tags(pytester):
    """未標籤的反方向 skip 不得觸發區塊（否則區塊會變成「所有 skip」的雜訊複本）。

    意圖：負向案例才是鑑別力的來源——沒有它，一支「無條件把每筆 skip 都印進反方向
    區塊」的假實作也會讓上一支通過。同時本支釘住 R76 的前提：**標籤是唯一入口**，
    所以「0/6 站點帶標籤」必然等於「區塊恆空」，那不是巧合而是結構。
    """
    _make_reverse_sandbox(pytester, posix_tagged=False, mac_tagged=False, untagged=True)
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=2, skipped=1)
    assert "POSIX/MAC-NATIVE-ONLY" not in result.stdout.str()
