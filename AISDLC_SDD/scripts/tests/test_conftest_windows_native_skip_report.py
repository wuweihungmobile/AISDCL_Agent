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

import ast
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import sdd_version  # isort: skip（同 test_copy_on_evolve.py 既有慣例）

pytest_plugins = ["pytester"]

_SDD_ROOT = Path(__file__).resolve().parent.parent.parent  # AISDLC_SDD/
_CONFTEST_SOURCE = (_SDD_ROOT / "conftest.py").read_text(encoding="utf-8")
_CROSS_VERSION_GUARD_SOURCE = (
    _SDD_ROOT / "scripts" / "cross_version_guard.py"
).read_text(encoding="utf-8")
_FROZEN_BASELINE = "AISDLC_SDD_v0.01"
_LATEST = sdd_version.latest_version_name(_SDD_ROOT, warn=lambda _m: None)


def _make_sandbox(pytester, *, tagged_skip: bool, plain_skip: bool,
                  posix_tagged_skip: bool | None = None) -> None:
    """在 pytester 沙盒內佈署「真實 conftest.py 原始碼」+ 其相依模組 + 一支迷你
    測試套件。`tagged_skip`/`plain_skip` 控制對應測試是否真的觸發 skip（True＝skip）。
    `posix_tagged_skip`（DEF-200-248）＝`None` 時**不**生成反方向探針（既有三案例的
    收集數逐字不變）；`True`／`False` 時多生成一支帶 `[POSIX-NATIVE-ONLY]` 標籤的測試。
    """
    pytester.makeconftest(_CONFTEST_SOURCE)
    scripts_dir = pytester.path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "cross_version_guard.py").write_text(
        _CROSS_VERSION_GUARD_SOURCE, encoding="utf-8"
    )
    posix_probe = "" if posix_tagged_skip is None else f'''
@pytest.mark.skipif({posix_tagged_skip!r}, reason="[POSIX-NATIVE-ONLY] 僅 POSIX 才具驗證價值")
def test_posix_tagged():
    pass
'''
    pytester.makepyfile(
        test_fixture_suite=f'''
import pytest

@pytest.mark.skipif({tagged_skip!r}, reason="[WINDOWS-NATIVE-ONLY] 僅原生 Windows 才具驗證價值")
def test_tagged():
    pass

@pytest.mark.skipif({plain_skip!r}, reason="本機缺某工具，一般性 skip")
def test_plain():
    pass
{posix_probe}
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


# ──────────────────────────────────────────────────────────────
# DEF-200-248（原 DEF-101-856 ③）：反方向（[POSIX-NATIVE-ONLY]／[MAC-NATIVE-ONLY]）報表
# ──────────────────────────────────────────────────────────────
# WHY：此前 AISDLC_SDD 側只彙整 [WINDOWS-NATIVE-ONLY]；在 Windows 上跑時真正失去的覆蓋
# （他平台專屬 skip）零訊號，「兩平台 skip 行為對齊」宣稱無從佐證。三支對稱 AutoClaude 側
# `tests/test_conftest_windows_native_skip_report.py` 的反方向設計：正向（真的印且點名）、
# 負向（沒 skip 就沉默）、雙向同時（兩個區塊各自獨立、互不吞掉）。


def test_posix_tagged_skip_prints_reverse_section(pytester):
    """帶反方向標籤的 skip 必須被獨立點名——區塊標題帶 POSIX/MAC，清單含該 nodeid，
    且**不得**被誤歸進 WINDOWS-NATIVE-ONLY 區塊。"""
    _make_sandbox(pytester, tagged_skip=False, plain_skip=False, posix_tagged_skip=True)
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=3, skipped=1)
    result.stdout.fnmatch_lines([
        "*POSIX/MAC-NATIVE-ONLY SKIPS*",
        "*1 *DEF-200-248*",
        "*test_posix_tagged*",
    ])
    assert "WINDOWS-NATIVE-ONLY SKIPS" not in result.stdout.str()


def test_posix_probe_that_runs_prints_no_reverse_section(pytester):
    """反方向探針真的跑了（沒 skip）⇒ 反方向區塊必須沉默（零 skip＝零雜訊，且證明區塊
    不是「有這個 reason 字串就印」而是真的看 skipped 統計）。"""
    _make_sandbox(pytester, tagged_skip=False, plain_skip=False, posix_tagged_skip=False)
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=4)
    assert "POSIX/MAC-NATIVE-ONLY" not in result.stdout.str()


def test_both_directions_print_two_independent_sections(pytester):
    """雙向同時 skip ⇒ 兩個區塊各自出現、各自只列自己那一邊（改成「全收」或漏印任一邊
    都會當場紅）。"""
    _make_sandbox(pytester, tagged_skip=True, plain_skip=False, posix_tagged_skip=True)
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=2, skipped=2)
    out = result.stdout.str()
    assert "WINDOWS-NATIVE-ONLY SKIPS" in out and "POSIX/MAC-NATIVE-ONLY SKIPS" in out
    win_section = out.split("WINDOWS-NATIVE-ONLY SKIPS", 1)[1].split("POSIX/MAC-NATIVE-ONLY", 1)[0]
    assert "test_tagged" in win_section and "test_posix_tagged" not in win_section
    posix_section = out.split("POSIX/MAC-NATIVE-ONLY SKIPS", 1)[1]
    assert "test_posix_tagged" in posix_section and "test_tagged\n" not in posix_section


# ──────────────────────────────────────────────────────────────
# R67-F27：機制必須覆蓋**官方閘門實際走的路徑**（版本樹 rootdir）
# ──────────────────────────────────────────────────────────────
# WHY：上面三支鎖驗的是 `rootdir=AISDLC_SDD` 的載入情境（＝`ci-gate.sh` 的
# `python -m pytest scripts/tests/` 那一軌）。但閘門另外兩軌是
# `cd vX && python -m pytest tools/fsm_runtime/tests/ -m "not chaos" -q -rs`，
# rootdir=vX，共用層 conftest 落在 confcutdir **之上**——本檔自己的 docstring
# 就寫著「不載入/不干擾」。於是 R44 宣稱的「未來新增的標籤 skip 在 AISDLC_SDD 側
# 也會被彙整凸顯」對版本樹**結構上不成立**：實測同一支帶標籤的探針檔複製到兩棵樹，
# `scripts/tests/` 印出區塊、版本樹零區塊；而 LATEST 樹本來就住著一支未被彙整的
# 真 Windows-only skip（`test_file_lock.py` 的 `skipUnless(sys.platform=="win32")`）。
# 修法＝版本樹 rootdir 自帶一支薄 conftest 借用共用層函式（見 `<LATEST>/conftest.py`
# 的 docstring 說明為何不改 ci-gate.sh、也不補進凍結基線）。


# 🔴 R68（windows-compat-ci 首度真跑才顯形）：探針的 skip 條件必須與**執行平台無關**。
#
# 原寫法是 `@pytest.mark.skipif(sys.platform != "win32", ...)`——借用真實平台判斷。
# 在 macOS/Linux 上它恆成立、探針被 skip、下面兩條鎖全綠；但在**原生 Windows** 上
# `sys.platform == "win32"`，條件為 False ⇒ 探針**執行並 pass 而非 skip** ⇒ 兩條鎖
# 的前提整個消失（實測輸出退化成 `1 passed`，見 CI run 30701321963）。
#
# 這裡要的是「一個必然被 skip、且 reason 帶得動彙整標籤的測試」——**被 skip 才是探針
# 的規格**，至於真實平台是什麼與本機制完全無關。故條件寫死 `True`，與本檔上半部
# `_make_sandbox()` 既有慣例（`skipif({tagged_skip!r}, ...)`，代入的同樣是字面 True）
# 一致。標籤仍留在 reason 最前面：彙整機制是靠 `_skip_reason()` 取
# `longrepr[2]`（形如 `"Skipped: <reason>"`）再比對 `WINDOWS_NATIVE_SKIP_TAG` 子字串
# 來認人的（見 `AISDLC_SDD/conftest.py::windows_native_skips`），與 skip 條件怎麼寫
# 無關——所以改成無條件 skip 不會讓探針從彙整清單裡消失。
_PROBE_SOURCE = (
    'import pytest\n'
    '\n'
    '\n'
    '@pytest.mark.skipif(True, reason="[WINDOWS-NATIVE-ONLY] R67-F27 探針")\n'
    'def test_win_only():\n'
    '    assert True\n'
)


def _version_tree_sandbox(tmp_path: Path, *, with_version_conftest: bool) -> Path:
    """複刻生產佈局：`<sdd>/conftest.py` ＋ `<sdd>/<vX>/{conftest.py,pytest.ini,tests}`。

    `with_version_conftest=False` 即「修復前」的形狀，供對照組使用——**這就是常駐的
    缺陷注入**：少了那支 conftest，同一份輸入必須印不出區塊。
    """
    sdd = tmp_path / "AISDLC_SDD"
    (sdd / "scripts").mkdir(parents=True)
    (sdd / "conftest.py").write_text(_CONFTEST_SOURCE, encoding="utf-8")
    (sdd / "scripts" / "cross_version_guard.py").write_text(
        _CROSS_VERSION_GUARD_SOURCE, encoding="utf-8"
    )
    version = sdd / "AISDLC_SDD_v9.99"
    tests = version / "tools" / "fsm_runtime" / "tests"
    tests.mkdir(parents=True)
    (version / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    if with_version_conftest:
        (version / "conftest.py").write_text(
            (_SDD_ROOT / str(_LATEST) / "conftest.py").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    (tests / "test_probe.py").write_text(_PROBE_SOURCE, encoding="utf-8")
    return version


# 只在 collection 期改 `sys.platform` 的沙箱 conftest（R68 回歸鎖用）。
# 為何不全域改：整個 session 都掛著假 platform 會讓 sysconfig 去找
# `_sysconfigdata__win32_darwin` 而直譯器當場炸掉（本機實測，非推測）。而
# `@pytest.mark.skipif(<非字串條件>)` 的條件正是在**測試模組 import＝collect 當下**
# 求值，故把假 platform 收斂在 `pytest_make_collect_report` 這個 wrapper 內即已足夠，
# 且副作用面最小。
_FAKE_PLATFORM_CONFTEST = '''\
import sys

import pytest

_ORIGINAL = sys.platform


@pytest.hookimpl(hookwrapper=True)
def pytest_make_collect_report(collector):
    sys.platform = "__FAKE_PLATFORM__"
    try:
        yield
    finally:
        sys.platform = _ORIGINAL
'''


def _run_official_gate_form(version_dir: Path, *, simulate_platform: str | None = None) -> str:
    """以 `scripts/ci-gate.sh` 逐字同款的呼叫形態跑（cwd=版本樹、相對 testpaths）。

    `simulate_platform` 不為 None 時，往沙箱 tests/ 丟一支 conftest，在 collection 期
    把子行程的 `sys.platform` 換成指定值——使「這支鎖在別的平台上會怎樣」成為**本機
    當場可跑**的事，而不是要等某個 runner 第一次跑到才知道。
    """
    if simulate_platform is not None:
        tests_dir = version_dir / "tools" / "fsm_runtime" / "tests"
        (tests_dir / "conftest.py").write_text(
            _FAKE_PLATFORM_CONFTEST.replace("__FAKE_PLATFORM__", simulate_platform),
            encoding="utf-8",
        )
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tools/fsm_runtime/tests/", "-q", "-rs"],
        cwd=str(version_dir), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=300,
    )
    return proc.stdout + proc.stderr


def test_official_gate_form_on_version_tree_prints_the_section(tmp_path: Path) -> None:
    version = _version_tree_sandbox(tmp_path, with_version_conftest=True)
    out = _run_official_gate_form(version)
    assert "WINDOWS-NATIVE-ONLY SKIPS" in out, (
        f"官方閘門形態（cd vX && pytest）必須看得到彙整區塊，實得：\n{out}"
    )
    assert "test_win_only" in out, "區塊必須點名該支測試的 nodeid"


def test_without_the_version_conftest_the_section_is_structurally_absent(tmp_path: Path) -> None:
    """常駐對照組（＝缺陷注入的另一半）：拿掉版本樹 conftest ⇒ 區塊必須消失。

    測意圖：證明上一條的綠燈**來自那支 conftest**，而不是恰好被別的機制蓋到。
    少了這條，把接線刪掉也可能因為某個無關 hook 仍在印東西而假綠。
    """
    version = _version_tree_sandbox(tmp_path, with_version_conftest=False)
    out = _run_official_gate_form(version)
    assert "1 skipped" in out, f"探針本身必須確實 skip（前提檢查），實得：\n{out}"
    assert "WINDOWS-NATIVE-ONLY SKIPS" not in out, (
        "沒有版本樹 conftest 時本來就印不出區塊——若這裡竟然印得出來，"
        "代表上一條測的不是這支 conftest"
    )


def test_probe_source_carries_no_platform_predicate() -> None:
    """🔴 R68 靜態後盾：探針原始碼裡不得出現任何平台判斷。

    WHY 兩條鎖並存（不是重複）：下一條是動態鎖（真跑三個模擬平台），鑑別力最強，但它
    本身依賴「collection 期換掉 `sys.platform` 不會弄壞子行程」這個前提——該前提在本機
    macOS 實測成立，在原生 Windows 上**尚未被驗證過**（誠實揭露）。本條是零風險的純字串
    斷言：即使動態鎖哪天在某平台上失效/被 skip，探針一旦被改回借用真實平台判斷，這裡仍
    會當場轉紅。探針的規格是「必然被 skip」，達成方式與作業系統無關。
    """
    offenders = [
        token
        for token in ("sys.platform", "os.name", "platform.system", "platform.machine")
        if token in _PROBE_SOURCE
    ]
    assert offenders == [], (
        f"探針原始碼含平台判斷 {offenders}——借用真實平台判斷等於把「探針必然被 skip」"
        f"這個前提綁死在特定平台上（原生 Windows 上 `sys.platform != 'win32'` 為 False，"
        f"探針會 pass 而非 skip，兩條版本樹鎖的前提整個消失）。請改用無條件 skip：\n"
        f"{_PROBE_SOURCE}"
    )


@pytest.mark.parametrize("fake_platform", ["win32", "linux", "darwin"])
def test_version_tree_locks_hold_under_every_simulated_platform(
    tmp_path: Path, fake_platform: str
) -> None:
    """🔴 R68：上面兩條版本樹鎖不得對「本機是哪個平台」做未言明的前提假設。

    WHY（Rule 9 — 測意圖）：那兩條驗的是「彙整機制在官方閘門形態下印不印得出來」，
    這件事與作業系統無關，故**每個平台上都必須得出同一個結果**。實際上探針原本借用
    `sys.platform != "win32"` 當 skip 條件，在原生 Windows 上條件為 False ⇒ 探針
    **執行並 pass 而非 skip** ⇒ 兩條鎖的前提整個蒸發（windows-compat-ci run
    30701321963 逐字：`1 passed in 0.19s`，期望的區塊與 `1 skipped` 皆不見）。
    借用真實平台判斷造探針＝把測試綁死在特定平台上——本鎖就是那個機械物。

    含 `linux`／`darwin` 而非只測 `win32`：三個平台**同時**綠才證明「與平台無關」；
    只測 win32 的話，一個寫成 `sys.platform == "win32"` 的反向錯誤仍會漏網。

    邊界（誠實劃界）：只注入 `sys.platform`。`os.name`、真實檔案系統、路徑分隔符、
    終端編碼皆**不在**模擬範圍 ⇒ 本鎖綠**不等於**「這兩條鎖在真 Windows 上必綠」，
    只等於「它們不因 `sys.platform` 而異」。對受測物而言這已是全部：探針的 skip 與否
    是唯一的平台相依輸入，而彙整機制本身只讀 skip reason 字串。
    """
    positive = _version_tree_sandbox(tmp_path / "pos", with_version_conftest=True)
    out = _run_official_gate_form(positive, simulate_platform=fake_platform)
    assert "WINDOWS-NATIVE-ONLY SKIPS" in out, (
        f"模擬 sys.platform={fake_platform!r} 下彙整區塊消失——探針的 skip 條件"
        f"（或彙整機制）對執行平台有未言明假設，實得：\n{out}"
    )
    assert "test_win_only" in out, "區塊必須點名該支測試的 nodeid"

    control = _version_tree_sandbox(tmp_path / "ctl", with_version_conftest=False)
    out = _run_official_gate_form(control, simulate_platform=fake_platform)
    assert "1 skipped" in out, (
        f"模擬 sys.platform={fake_platform!r} 下探針未被 skip ⇒ 對照組前提不成立，"
        f"實得：\n{out}"
    )
    assert "WINDOWS-NATIVE-ONLY SKIPS" not in out, (
        "沒有版本樹 conftest 時本來就印不出區塊——若這裡竟然印得出來，"
        "代表上一條測的不是這支 conftest"
    )


def test_latest_version_tree_has_the_summary_hook_wired() -> None:
    """真樹接線鎖：LATEST 版必須自帶 conftest 並真的曝出 `pytest_terminal_summary`。

    沙盒測的是「這份原始碼行為對」，本條測的是「它真的裝在生產樹上」——沙盒綠、
    生產樹沒接線是本 repo 最常見的假綠形狀（同 DEF-101-510／QA-R59-02 判例）。
    """
    conftest = _SDD_ROOT / str(_LATEST) / "conftest.py"
    assert conftest.is_file(), (
        f"LATEST 版 {_LATEST} 缺 conftest.py——官方閘門的兩軌版本樹會再度看不到"
        "[WINDOWS-NATIVE-ONLY] 彙整（R67-F27）"
    )
    tree = ast.parse(conftest.read_text(encoding="utf-8"))
    assigned = {
        target.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    assert "pytest_terminal_summary" in assigned, (
        "版本樹 conftest 必須曝出 pytest_terminal_summary（pytest 以名稱查 hook，"
        "只 import 不曝名＝沒接線）"
    )


def _windows_conditional_skips_without_tag(tree_root: Path) -> list[str]:
    """AST 掃描：以 `win32` 為條件的 skip，其 reason 未帶標籤者（`檔:行`）。

    用 AST 而非逐行 regex：reason 常是跨行隱式串接的多段字串，逐行比對會把
    「標籤在第一段、關鍵詞在第二段」誤判成漏標。
    """
    offenders: list[str] = []
    for path in sorted(tree_root.rglob("test_*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:  # pragma: no cover - 版本樹內不應有語法錯
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", getattr(node.func, "id", ""))
            if name not in ("skipUnless", "skipIf", "skipif", "skipTest", "skip"):
                continue
            if "win32" not in ast.dump(node):
                continue
            literals = [
                n.value for n in ast.walk(node)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
            ]
            if any("[WINDOWS-NATIVE-ONLY]" in lit for lit in literals):
                continue
            offenders.append(f"{path.relative_to(tree_root)}:{node.lineno}")
    return offenders


def test_every_windows_conditional_skip_in_latest_carries_the_tag() -> None:
    """前瞻鎖：LATEST 樹裡任何以 `win32` 為條件的 skip 都必須帶標籤。

    WHY：接了線但沒標籤 ⇒ 區塊照樣印不出那一支（R67 動工時 `test_file_lock.py`
    正是這個狀態：機制不可達 ＋ 標籤也沒帶，雙重不可見）。標籤是慣例、慣例沒有
    機械物就會被忘記——本條就是那個機械物。
    """
    offenders = _windows_conditional_skips_without_tag(_SDD_ROOT / str(_LATEST))
    assert offenders == [], (
        f"LATEST 版 {_LATEST} 有以 win32 為條件、卻未帶 [WINDOWS-NATIVE-ONLY] 標籤的 "
        f"skip：{offenders}——請在 reason 最前面加上該標籤"
    )


def test_the_scanner_actually_detects_a_missing_tag(tmp_path: Path) -> None:
    """鑑別力自證：上一條在真樹上為空集合（綠），必須另證掃描器**不是**恆空。"""
    (tmp_path / "test_bad.py").write_text(
        'import sys\nimport unittest\n\n\n'
        'class T(unittest.TestCase):\n'
        '    @unittest.skipUnless(sys.platform == "win32", "只在 Windows 成立")\n'
        '    def test_x(self):\n'
        '        pass\n',
        encoding="utf-8",
    )
    assert _windows_conditional_skips_without_tag(tmp_path) == ["test_bad.py:6"]
    (tmp_path / "test_bad.py").write_text(
        'import sys\nimport unittest\n\n\n'
        'class T(unittest.TestCase):\n'
        '    @unittest.skipUnless(sys.platform == "win32",\n'
        '                         "[WINDOWS-NATIVE-ONLY] 只在 Windows 成立")\n'
        '    def test_x(self):\n'
        '        pass\n',
        encoding="utf-8",
    )
    assert _windows_conditional_skips_without_tag(tmp_path) == [], "補上標籤後必須轉綠"


def test_frozen_baseline_has_no_windows_conditional_skips() -> None:
    """凍結基線未接線的正當性依據——它一支 Windows 條件式 skip 都沒有。

    ADR-XPLAT-001 Copy-on-Evolve 明令凍結版不得原地修改，故 `v0.01/` **刻意不補**
    conftest；本條把「所以曝險為零」這個前提釘成機械事實。凍結版永不新增測試，
    此前提不會腐化；萬一有人違規往凍結版塞了 Windows-only 測試，這條會紅並指出
    真正的問題（動了凍結版），而不是要求在凍結版補標籤。
    """
    frozen = _SDD_ROOT / _FROZEN_BASELINE
    if not frozen.is_dir():  # pragma: no cover - 凍結基線消失屬更嚴重的問題，另有鎖
        pytest.skip(f"凍結基線目錄不存在：{frozen}")
    hits = [
        f"{p.relative_to(frozen)}"
        for p in sorted(frozen.rglob("test_*.py"))
        if "win32" in p.read_text(encoding="utf-8", errors="replace")
    ]
    assert hits == [], (
        f"凍結基線 {_FROZEN_BASELINE} 出現含 win32 的測試：{hits}——它是 ci-gate 的凍結"
        "回歸基線，不得原地修改（ADR-XPLAT-001）；此處紅燈代表凍結版被動過，"
        "而非要求在該樹補標籤"
    )
