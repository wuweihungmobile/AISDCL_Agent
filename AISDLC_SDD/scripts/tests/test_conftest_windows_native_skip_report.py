"""AISDLC_SDD 根 conftest.py 的 `[WINDOWS-NATIVE-ONLY]` skip 可見度機制回歸鎖
（R44，DEF-101-368：接續 DEF-101-363 方向①——當時只在
`test_install_post_commit_windowsapps_guard.py::_WINDOWS_PATHEXT_SKIP` 補上標籤
字串，未在 AISDLC_SDD 側佈建對應的 `pytest_terminal_summary` hook，標籤純屬裝
飾性文字、不會真的被彙整凸顯）。

WHY（Rule 9，測意圖非僅行為）：純函式 `windows_native_skips()` 好測，但真正容易
被改壞而不被發現的是 `pytest_terminal_summary()` 這個「印出副作用」本身——例如
標籤比對邏輯被改壞、或印出時機被誤搬到不會在 `-q` 下觸發的 hook。只驗證純函式
回傳值鎖不住「真的有印到終端輸出上」這件事。本檔用 pytest 內建 `pytester`
fixture 以子行程方式真跑一個模擬迷你套件（沙盒 conftest.py 直接複製本套件真實
`AISDLC_SDD/conftest.py` 原始碼，而非重新實作一份等價邏輯——確保鎖住的是生產
程式碼本身，不是測試自己編造的替身），斷言真實終端輸出裡「該出現的醒目清單有
出現、不該出現時完全沉默」。三個案例對稱比照
`AutoClaude/tests/test_conftest_windows_native_skip_report.py` 的既有三案例設計
（tagged-only / plain-only / 全部不 skip）。

沙盒細節：真實 `AISDLC_SDD/conftest.py` 於模組載入時會 `sys.path.insert` 加入
`scripts/` 並 import `cross_version_guard`（DEF-02-001 跨版 guard，與本機制無
關）。為讓沙盒內複製的 conftest.py 能成功載入（而非重新實作一份簡化版，失去
「鎖生產程式碼本身」的意義），連同真實 `scripts/cross_version_guard.py` 原始碼
一併複製進沙盒的 `scripts/` 子目錄。
"""
from __future__ import annotations

from pathlib import Path

pytest_plugins = ["pytester"]

_SDD_ROOT = Path(__file__).resolve().parent.parent.parent  # AISDLC_SDD/
_CONFTEST_SOURCE = (_SDD_ROOT / "conftest.py").read_text(encoding="utf-8")
_CROSS_VERSION_GUARD_SOURCE = (
    _SDD_ROOT / "scripts" / "cross_version_guard.py"
).read_text(encoding="utf-8")


def _make_sandbox(pytester, *, tagged_skip: bool, plain_skip: bool) -> None:
    """在 pytester 沙盒內佈署「真實 conftest.py 原始碼」+ 其相依模組 + 一支迷你
    測試套件。`tagged_skip`/`plain_skip` 控制對應測試是否真的觸發 skip（True＝skip）。
    """
    pytester.makeconftest(_CONFTEST_SOURCE)
    scripts_dir = pytester.path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "cross_version_guard.py").write_text(
        _CROSS_VERSION_GUARD_SOURCE, encoding="utf-8"
    )
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
