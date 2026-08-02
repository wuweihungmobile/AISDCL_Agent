"""子專案 import 邊界鎖：AISDLC_SDD ↮ AutoClaude 不得互相 import（R69）.

WHY 這道鎖存在（真實付出的代價，非前瞻假設）：
`AISDLC_SDD` 與 `AutoClaude` 是兩個**獨立可發布**子專案（各自 `releases/` 打包、各自
CI 相依清單），根 CLAUDE.md 明文載明。R68 有兩處測試越界直接 import AutoClaude 生產
套件，兩處**都在本機全綠、都在 CI 上失效**：

  1. `scripts/tests/test_ntfs_length_gate.py`（原 446-447 行）硬 import
     `autoclaude.utils.logger` ⇒ `autoclaude.utils.__init__` 連帶拉進 pydantic，而
     AISDLC_SDD 的 CI 相依只鎖 `AISDLC_SDD_v0.01/requirements-ci.txt`（pyyaml +
     pytest）⇒ `aisdlc-sdd-ci` 由綠轉紅（run 30720156045：
     `ModuleNotFoundError: No module named 'pydantic'`）。
  2. `AISDLC_SDD_v0.30/tools/fsm_runtime/tests/test_state_component_sanitizer_parity.py`
     同樣跨樹 import，但外面包了 `try/except ImportError` + `@unittest.skipIf` ⇒ 不會
     紅，而是**8 支測試在 CI 上永遠 skip**（乾淨 venv 實測 `8 skipped`）。這比紅更糟：
     R68 剛付過同款學費（「122 支迴歸鎖一支都沒跑」，見 root-infra-ci.yml 檔頭訂正段）。

兩者共同的根因不是「誰忘了裝套件」，而是**跨子專案 import 這個動作本身**——它讓「本機
能跑」與「CI 能跑」永久脫鉤，且脫鉤是靜默的。故本鎖不管相依裝了沒，直接禁止該動作。

**修好之後跨子專案一致性由誰承接**：monorepo 根層整合層
`tools/tests/test_windows_forbidden_filename_parity.py`——它本來就是「四處獨立實作漂移
即知」的載體，且根層 root-infra-ci 依 `tools/run_root_unittests.py::_THIRD_PARTY_PREREQS`
安裝第三方相依，import AutoClaude 生產套件在該層是合法且真的會跑的。上述兩處的斷言全數
搬遷至該檔（`TestLengthPolicySiteTwoLoggerNoTruncation` /
`TestSddSanitizeComponentVsLoggerSecurityParity`），一條沒少、且從「永遠 skip」變成
「真的跑」。

**為何用 AST 而非 grep**：AutoClaude 側 `tests/integration/test_sdd_bridge/` 以
subprocess 在 SDD 樹內跑腳本（`_PRODUCER` / `_STATE_SCRIPT` 字串常數內含
`from tools.fsm_runtime import ...`）——那是**正確**的隔離做法（另一個行程、不把對方
模組拉進自己的 import graph），純文字掃描會把它誤判成違規。AST 只認真正的 `Import`
/`ImportFrom` 節點，字串常數與註解天然不計。
"""
from __future__ import annotations

import ast
import os
import subprocess
from pathlib import Path

import pytest


def _monorepo_root() -> str:
    # scripts/tests/ → scripts/ → AISDLC_SDD/ → monorepo 根
    return os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )


# 對方子專案的可 import 頂層符號（以「模組路徑前綴」比對，非檔案路徑）。
_AUTOCLAUDE_ROOTS = ("autoclaude",)
# AISDLC_SDD 側可被 import 的模組前綴：版本目錄內的 `tools.fsm_runtime` /
# `tools.arch_fitness`（AutoClaude 自己的 `tools.` 底下無同名套件，故前綴比對不誤傷
# `from tools.mutation_analysis import ...` 這類 AutoClaude 自家 import）。
_SDD_VERSIONED_PREFIXES = ("tools.fsm_runtime", "tools.arch_fitness")

# 共享 infra `AISDLC_SDD/scripts/*.py`：這些檔被 `sys.path.insert` 後以**裸模組名**
# import（`import sdd_version` / `from component_sanitizer import ...`），沒有套件前綴，
# 故必須逐名列入。清單**動態自磁碟取得**，不硬編——硬編的下場是新增一支 scripts/*.py
# 後本鎖對它靜默失效（R69 修前實測：14 支全數不在集合內，反方向違規 100% 放行）。
#
# 🔴 fail-loud 下限：glob 打錯路徑／掃描面被縮小時，集合會變空 ⇒ 反方向的
# `foreign_imports` 恆回 []、`test_autoclaude_never_imports_aisdlc_sdd` 恆綠空砲。
# 恆綠的鎖與沒有鎖等價，故 import 期就硬錯（collection error），不留給人事後發現。
_MIN_SDD_SCRIPT_MODULES = 10


def _sdd_shared_script_modules() -> tuple[str, ...]:
    """`AISDLC_SDD/scripts/*.py` 的模組名（stem）；數量低於下限即 import 期硬錯。"""
    scripts_dir = Path(_monorepo_root()) / "AISDLC_SDD" / "scripts"
    stems = tuple(sorted(
        p.stem for p in scripts_dir.glob("*.py") if not p.stem.startswith("_")
    ))
    if len(stems) < _MIN_SDD_SCRIPT_MODULES:
        raise AssertionError(
            f"AISDLC_SDD/scripts/*.py 只取到 {len(stems)} 支模組（下限"
            f" {_MIN_SDD_SCRIPT_MODULES}）：{stems}\n"
            f"掃描目錄={scripts_dir}（exists={scripts_dir.is_dir()}）。集合若變空，反方向"
            "的跨子專案 import 鎖會變成恆綠空砲 ⇒ 此處 fail-loud，不得靜默放行。"
        )
    return stems


_SDD_PACKAGE_PREFIXES = _SDD_VERSIONED_PREFIXES + _sdd_shared_script_modules()


def imported_module_roots(source: str) -> list[tuple[int, str]]:
    """AST 取出模組層以外全部真實 import 的**完整點分模組名**（含行號）。

    純函式（不碰磁碟），供下方掃描與自我檢驗共用。相對 import（``level > 0``）永遠指向
    同一套件內部，不可能跨子專案，故略過。
    """
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # 相對 import
                continue
            if node.module:
                found.append((node.lineno, node.module))
    return found


def foreign_imports(source: str, forbidden_prefixes: tuple[str, ...]) -> list[tuple[int, str]]:
    """挑出命中 ``forbidden_prefixes`` 的 import（完全比對或點分前綴比對）。"""
    hits = []
    for lineno, module in imported_module_roots(source):
        for prefix in forbidden_prefixes:
            if module == prefix or module.startswith(prefix + "."):
                hits.append((lineno, module))
                break
    return hits


def _scanned_py_files(pathspec: str) -> list[str]:
    """掃描面＝**tracked ∪ untracked-not-ignored** 的 .py（掃描面不得靜默縮小 → rc 非零即硬錯）。

    🔴 R70（`DEF-101-752`）：本函式原名 `_tracked_py_files`、只跑 `git ls-files`
    ⇒ **還沒 `git add` 的新檔對本鎖完全不存在**。同一個盲區在 R69 已付過實帳：
    `AutoClaude/autoclaude/utils/platform_caps.py` 全程 untracked，於是它與
    `tools/tests/test_platform_utils_dedup.py` 的不變量衝突躲過**四輪四方複審**與
    多次全套閘門實跑，直到 `git add -A` 那一刻才在 pre-push 顯形。本鎖與該檔
    **結構同構**（repo-wide `*.py` ＋ 禁用樣式掃描），故同步封閉：新寫的 .py 若
    跨子專案 import，第一次跑測試就該紅——而不是等 commit 之後。
    `-o --exclude-standard` 仍尊重 `.gitignore`，`AISDLC_SDD/` 下 4,800+ 支
    venv/快取 `.py` 一樣排除得掉，`needles` 前置篩亦照舊。
    """
    paths: set[str] = set()
    for extra in ((), ("-o", "--exclude-standard")):
        proc = subprocess.run(
            ["git", "ls-files", *extra, "-z", "--", pathspec],
            cwd=_monorepo_root(),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if proc.returncode != 0:
            raise AssertionError(
                f"git ls-files 失敗（rc={proc.returncode}；stderr={proc.stderr.strip()!r}）"
            )
        paths.update(rel for rel in proc.stdout.split("\0") if rel)
    return sorted(paths)


def _scan(pathspec: str, forbidden_prefixes: tuple[str, ...], needles: tuple[str, ...]):
    """掃描 tracked ∪ untracked-not-ignored 的 .py，回傳 ``[(rel, lineno, module), ...]``。

    ``needles`` 只是**效能前置篩**（子字串必為 import 出現的充分必要前提之超集）：
    AISDLC_SDD 樹下有 4,800+ 支 .py，全量 AST parse 過慢；先以子字串排除絕不可能命中的
    檔案，不會漏判。
    """
    root = _monorepo_root()
    violations = []
    for rel in _scanned_py_files(pathspec):
        try:
            with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:  # pragma: no cover - tracked 檔應恆可讀
            continue
        if not any(n in text for n in needles):
            continue
        try:
            hits = foreign_imports(text, forbidden_prefixes)
        except SyntaxError:
            # 語法錯誤另有 py_compile / pytest collection 把關，不在本鎖責任範圍
            continue
        violations.extend((rel, lineno, module) for lineno, module in hits)
    return violations


def test_aisdlc_sdd_never_imports_autoclaude():
    """AISDLC_SDD/** 下任何 .py 都不得 import AutoClaude 生產套件。

    違反的代價是「本機綠 / CI 紅或永遠 skip」——見本檔 docstring 兩筆實證。
    """
    violations = _scan("AISDLC_SDD/*.py", _AUTOCLAUDE_ROOTS, ("autoclaude",))
    assert violations == [], (
        "AISDLC_SDD 側出現跨子專案 import（AutoClaude 生產套件）：\n"
        + "\n".join(f"  {rel}:{lineno} → {module}" for rel, lineno, module in violations)
        + "\n修法：需要與 AutoClaude 做一致性比對時，把斷言放到 monorepo 根層整合層"
        " tools/tests/（該層合法 import 兩側，且 root-infra-ci 會安裝第三方相依），"
        "**不要**在此處包 try/except ImportError + skipIf——那只會讓測試在 CI 上"
        "永遠不跑（R68 已付過此學費）。"
    )


def test_autoclaude_never_imports_aisdlc_sdd():
    """反方向同禁：AutoClaude/** 下任何 .py 不得 import AISDLC_SDD 的模組。

    目前唯一的跨樹互動是 `tests/integration/test_sdd_bridge/` 以 **subprocess** 在 SDD
    樹內執行腳本字串——那不進 AutoClaude 自己的 import graph，本鎖（AST 級）刻意放行，
    也正是越界時該改採的形態。
    """
    # needles 直接沿用 prefixes：任一 prefix 命中的前提必是該字串出現在原始碼裡
    # （import 敘述必然含完整模組名），故「needles == prefixes」在結構上恆為合法超集，
    # 不會隨 prefixes 動態擴充而漏配（修前是寫死兩枚 needle，擴充後就會靜默縮面）。
    violations = _scan("AutoClaude/*.py", _SDD_PACKAGE_PREFIXES, _SDD_PACKAGE_PREFIXES)
    assert violations == [], (
        "AutoClaude 側出現跨子專案 import（AISDLC_SDD 模組）：\n"
        + "\n".join(f"  {rel}:{lineno} → {module}" for rel, lineno, module in violations)
        + "\n修法：改以 subprocess 在 SDD 樹內執行（見 tests/integration/test_sdd_bridge/"
        " 既有做法），或把整合斷言放到 monorepo 根層 tools/tests/。"
    )


# ── 鎖的鎖：證明上面兩支不是恆綠的空砲 ────────────────────────────────────
# WHY 必要：本鎖的斷言是「掃不到東西」，一旦偵測函式退化（regex 打錯、AST 節點型別漏接、
# needles 前置篩把真違規也濾掉）就會靜默恆綠，而恆綠的鎖與沒有鎖等價。下面用合成原始碼
# 直接餵偵測純函式，正反例各鎖一次。

_SYNTHETIC_OFFENDERS = [
    "from autoclaude.utils.logger import _sanitize_log_filename\n",
    "import autoclaude\n",
    "import autoclaude.utils.logger as lg\n",
    "def f():\n    from autoclaude.utils import logger\n",  # 函式內 import 同樣算
]

_SYNTHETIC_CLEAN = [
    # 字串常數內的 import（subprocess 腳本形態）不算違規
    '_SCRIPT = """\nfrom autoclaude.utils import logger\n"""\n',
    "# from autoclaude.utils import logger（註解）\n",
    '"""docstring 提到 from autoclaude.utils import logger"""\n',
    "from autoclaude_lookalike import thing\n",   # 前綴比對須錨定，不可誤傷同前綴名
    "import os\nfrom pathlib import Path\n",
]


@pytest.mark.parametrize("source", _SYNTHETIC_OFFENDERS)
def test_detector_flags_real_cross_tree_imports(source):
    assert foreign_imports(source, _AUTOCLAUDE_ROOTS), (
        f"偵測函式漏判真實跨樹 import，本鎖已成恆綠空砲：{source!r}"
    )


@pytest.mark.parametrize("source", _SYNTHETIC_CLEAN)
def test_detector_ignores_non_import_mentions(source):
    assert foreign_imports(source, _AUTOCLAUDE_ROOTS) == [], (
        f"偵測函式誤判非 import 的提及，會逼出假紅：{source!r}"
    )


def test_needle_prefilter_does_not_hide_offenders():
    """前置篩（子字串）必須是 import 命中的超集——否則掃描面靜默縮小。"""
    for source in _SYNTHETIC_OFFENDERS:
        assert "autoclaude" in source, (
            "存在『會被偵測函式判為違規、卻不含 needle 子字串』的形態 ⇒ _scan 的效能"
            f"前置篩會把它濾掉、掃描面靜默縮小：{source!r}"
        )


# ── 反方向（AutoClaude → AISDLC_SDD）同樣要證明不是空砲 ──────────────────
# WHY 這組必要：反方向的前綴集合修前是**寫死的 2 元組**，而註解宣稱它會動態取
# `AISDLC_SDD/scripts/*.py` 的模組名 —— 註解代言了未實作的射程。實測修前
# `foreign_imports("from component_sanitizer import x", _SDD_PACKAGE_PREFIXES) == []`，
# 亦即共享 infra 那 14 支的越界 import 全數放行。以下正反例把射程釘住。

_SDD_SYNTHETIC_OFFENDERS = [
    "from component_sanitizer import sanitize_component\n",
    "import sdd_version\n",
    "from tools.fsm_runtime import state_loader\n",
    "def f():\n    import framework_status_snapshot\n",
]

_SDD_SYNTHETIC_CLEAN = [
    "from tools.mutation_analysis import run\n",   # AutoClaude 自家 tools. 套件
    "import component_sanitizer_lookalike\n",      # 前綴比對須錨定
    '_SCRIPT = """\nimport sdd_version\n"""\n',    # subprocess 腳本字串常數
    "import os\n",
]


@pytest.mark.parametrize("source", _SDD_SYNTHETIC_OFFENDERS)
def test_detector_flags_reverse_direction_imports(source):
    assert foreign_imports(source, _SDD_PACKAGE_PREFIXES), (
        f"反方向偵測漏判跨樹 import，本鎖已成恆綠空砲：{source!r}"
    )


@pytest.mark.parametrize("source", _SDD_SYNTHETIC_CLEAN)
def test_reverse_detector_ignores_non_violations(source):
    assert foreign_imports(source, _SDD_PACKAGE_PREFIXES) == [], (
        f"反方向偵測誤判，會逼出假紅：{source!r}"
    )


def test_sdd_prefixes_are_really_read_from_disk():
    """前綴集合必須真的含磁碟上的 scripts 模組名（不是註解在自說自話）。"""
    stems = _sdd_shared_script_modules()
    assert len(stems) >= _MIN_SDD_SCRIPT_MODULES
    assert set(stems) <= set(_SDD_PACKAGE_PREFIXES)
    # 抽兩支長期存在的共享 infra 當代表：整組若退化成空/硬編，這裡就會落空
    assert {"component_sanitizer", "sdd_version"} <= set(stems), stems


def test_empty_glob_is_fail_loud_not_silently_empty(tmp_path, monkeypatch):
    """glob 打空（路徑打錯／掃描面縮小）必須硬錯，不得回空集合讓鎖恆綠。"""
    (tmp_path / "AISDLC_SDD" / "scripts").mkdir(parents=True)
    # 以 globals() 換掉模組級 `_monorepo_root`（模組名隨 pytest rootdir 而異，
    # 用字串路徑指定 target 會在不同 invocation 下解析失敗）
    monkeypatch.setitem(globals(), "_monorepo_root", lambda: str(tmp_path))
    with pytest.raises(AssertionError, match="恆綠空砲"):
        _sdd_shared_script_modules()


def test_reverse_needle_prefilter_does_not_hide_offenders():
    """反方向前置篩（needles==prefixes）必須是命中的超集。"""
    for source in _SDD_SYNTHETIC_OFFENDERS:
        hits = foreign_imports(source, _SDD_PACKAGE_PREFIXES)
        assert hits, source
        assert any(n in source for n in _SDD_PACKAGE_PREFIXES), (
            f"存在『判為違規卻不含任何 needle 子字串』的形態 ⇒ _scan 掃描面靜默縮小：{source!r}"
        )


def test_scan_reads_the_real_worktree():
    """載具自檢：掃描面非空（git ls-files 若回空，上面兩支會空轉全綠）。"""
    assert len(_scanned_py_files("AISDLC_SDD/*.py")) > 100
    assert len(_scanned_py_files("AutoClaude/*.py")) > 100
