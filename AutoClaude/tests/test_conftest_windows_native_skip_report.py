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
            "*2 * Windows *",
        ]
    )
    out = result.stdout.str()
    assert "test_posix_tagged" in out and "test_mac_tagged" in out, out


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
