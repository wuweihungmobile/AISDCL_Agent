#!/usr/bin/env python3
"""測試樹原始碼「Windows 磁碟機假路徑」自我檢測（R11 A1c；R11 複審 SD-2/ARCH-2 補強；
R12 ARCH-R12-4 掃描面擴大至四個測試樹）.

WHY：R11 真 Mac 首跑實證——測試裡把 D:/repo 這種磁碟機假路徑字串塞給 Path()，
它只在 Windows 是絕對路徑；POSIX 上 `repo_root / 絕對路徑` 的 pathlib join 會退化
成串接（D:/repo/D:/repo/…）、resolve 後恆不相等 → Windows 全綠、Mac/Linux 假紅
（test_check_hooks_liveness.py TestIsHooksEffective 兩案例實際紅過）。修法是改用
_platform_helpers.ABS_FAKE_REPO 平台中立常數；本測試機械掃描測試樹原始碼，
防未來有人複製舊 pattern 再踩一次。

R11 四方複審補強（SD-2/ARCH-2）：原 regex 只抓「Path( 後緊接引號＋大寫磁碟機
＋正斜線」單一形態——漏抓 r/f 等字串前綴變體、反斜線形態 X:\\、小寫磁碟機，
以及**裸字串**磁碟機路徑常數（原病灶正是不經 Path( 直呼的裸字串）。改為抓
「任意字串字面值以磁碟機路徑開頭」（引號後緊接單一字母＋冒號＋斜線或反斜線；
匹配起點是引號本身，故 r/f/b 前綴一律涵蓋）。並：
  (a) 每行先剝 `#` 註解尾再掃（註解舉例不誤報；heuristic 不解析字串內的 #，
      字串內含 # 且其後才出現磁碟機路徑的極端形態會漏掃，屬可接受取捨）；
  (b) 豁免顯式平台語意 PureWindowsPath(/PurePosixPath(（該行本來就是在寫
      特定平台路徑）與逐檔豁免清單 _ALLOWED（附 WHY）；
  (c) 支援行尾 `# platform-ok: <理由>` 豁免標記（合法命中須逐行附理由明示處置）。

R12 掃描面（ARCH-R12-4；DEF-101-149 病灶類別在其他測試樹此前零守門）：
  1. tools/tests/（本目錄，非遞迴——維持 R11 現狀）
  2. AISDLC_SDD/scripts/tests/（非遞迴）
  3. AutoClaude/tests/（**遞迴**，含 plugins/core/contract/… 子樹）
  4. LATEST 版 tools/fsm_runtime/tests/（遞迴；LATEST 以 scripts/sdd_version.py
     SSOT subprocess 解析——手法對齊 check_script_parity；解析失敗 fail-loud，
     不得靜默縮小掃描邊界。凍結版 v0.01~v0.2X 依鐵律不掃、也不可修）
"""
from __future__ import annotations

import ast
import functools
import io
import os
import re
import subprocess
import sys
import tempfile
import tokenize
import unittest
from collections.abc import Callable
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[1]

# 🔴 姊妹鎖（`test_subprocess_encoding_hygiene`）的三支下限帶純函式**直接取用、
# 不複製**。WHY：兩支鎖守的是同一件事「掃描面不得靜默腐化」，判準各寫一份就是兩個
# 會漂移的真相——本輪立案的形態正是「藥已開好，卻只餵給兩個病人中的一個」。
sys.path.insert(0, str(_TESTS_DIR))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
import sdd_latest  # noqa: E402
import test_subprocess_encoding_hygiene as _sister  # noqa: E402
from test_subprocess_encoding_hygiene import (  # noqa: E402
    repin_ceiling,
    suggested_floor,
    tree_count_verdict,
)

# 任意字串字面值以「單一字母磁碟機 + 冒號 + / 或 \」開頭即命中；
# 匹配起點為引號本身，r/f/b 等前綴與 Path( 包裹與否皆無關（裸字串同樣命中）。
_DRIVE_STR_RE = re.compile(r"""["'][A-Za-z]:[/\\]""")
# 逐檔豁免（repo 相對路徑 → WHY）。豁免檔案消失時 fail-loud（防清單腐化）。
_ALLOWED: dict[str, str] = {
    "tools/tests/_platform_helpers.py": (
        "平台中立常數的單一定義點（win32 分支本來就該寫磁碟機路徑）"
    ),
    "AutoClaude/tests/test_perception.py": (
        "Windows 專屬 perception/cmd-shim 的 mock 回傳值與純字串斷言，"
        "無 pathlib join 語意（R12 親讀 20 筆命中逐一核可，非 DEF-101-149 病灶）"
    ),
    "AutoClaude/tests/test_perception_platform_honesty.py": (
        "上一列 test_perception.py 的姊妹檔（R68 新增，測 cmd.exe 8191 字元硬上限守門）："
        "三筆命中皆為 _build_cmd_shim_line() 的輸入字串字面值，直接進字串長度計算、"
        "不進 pathlib join；且 cmd shim 本來就只在 Windows 成立，改平台中立常數即失去測意"
    ),
}
_OK_MARKER = "platform-ok:"
_EXPLICIT_PLATFORM = ("PureWindowsPath(", "PurePosixPath(")


def _latest_root() -> Path:
    """LATEST 版根目錄（sdd_version.py SSOT；解析失敗即 AssertionError）。
    委派 tools/lib/sdd_latest.py 單一真相源（ADR-XPLAT-002 Phase 2-C，R66 收斂）。"""
    return sdd_latest.resolve_latest_root(_REPO_ROOT / "AISDLC_SDD")


def _latest_fsm_tests_dir() -> Path:
    """LATEST 版 fsm_runtime/tests。"""
    return _latest_root() / "tools" / "fsm_runtime" / "tests"


def _scan_roots() -> list[tuple[Path, bool, int]]:
    """（掃描根, 是否遞迴, 該樹檔數下限）清單；根缺席或**離開下限帶**由測試 fail-loud。

    per-tree 下限（R12 SD 一審 SD-3）：全域總數下限對「單樹靜默縮面」不敏感
    （如 LATEST 樹 rglob 被改 glob，總數 377→303 仍過全域 200）；逐樹釘選使任一
    樹縮面必紅。

    🔴 本輪三處修正（缺陷本體＝**同一份知識住兩個家、只有一個家被修好**）：

    ① **掃描面對稱化**。與姊妹鎖 `test_subprocess_encoding_hygiene._scan_roots()`
       逐檔對拍，本清單此前少看 44 支 active `.py`，而缺口**正好蓋住整層 hook**
       （`AutoClaude/tools/hooks/` 6 支＋LATEST `.claude/hooks/` 5 支）——hook 是本
       repo 唯一「會主動阻斷使用者操作」的一層，指路錯誤代價最高。兩個成因並存：
       `AutoClaude/tools` 一邊 flat glob 一邊 rglob；本清單少了 4 棵樹。修法＝改
       recursive ＋ 補齊 4 棵樹 ＋ 補 `_scan_single_files()`；對稱性此後由
       `TestScanSurfaceParityWithSisterLock` 機械看守（擴一邊沒擴另一邊即紅）。
       落地當回合實測：缺口內的存量債對本檔五道判準**全為 0**，屬零成本擴面。

    ② **下限改雙邊帶**。原下限是單邊的（只有 `assertGreaterEqual`），而單邊下限
       必然腐化：樹會長大、下限不會。落地當回合實測 `tools/tests` floor=10／
       actual=56 ⇒ **可靜默蒸發 82% 掃描面而全綠**，比姊妹鎖當初立案的 78% 更差。
       姊妹鎖已把藥開好（`repin_ceiling`／`suggested_floor`／`tree_count_verdict`
       三支純函式），本檔改為直接 import 那三支，兩鎖共用同一組上下界。
       🔴 下限值一律＝**落地當回合實測 × 0.95**（`suggested_floor()`），不再是
       「首掃數打八折」那種化石；實測值隨行註記於各列。

    ③ **一律遞迴**（落地當回合被上面那道對稱鎖自己抓到的第三個病灶）：本清單原本
       混用 flat／rglob，而 flat 的那幾棵對「有人在樹下新開一個子目錄」結構性隱形
       ——並行包當回合新增的 `tools/probe/` 就是這樣落在射程外。巢狀樹（如
       `tools/tests` 住在 `tools` 底下）仍各自保有自己的下限，由 `_scan_units()`
       的**最長前綴認領**分帳，不會被外層重複計算。

    🔴 **下方刻意不逐列寫「實測 N」**：那等於在每一列旁邊放一個沒有任何機械物看守的
    量測快照（同 ADR-XPLAT-002 §8 表頭規則 3）。當回合實際發生過：兩列的隨行實測值在
    寫下後幾分鐘內就被並行包改動的樹弄過期。下限本身受雙邊帶看守，實測值由失敗訊息
    當場印出——那才是唯一不會腐化的取值面。"""
    latest = _latest_root()
    return [
        (_TESTS_DIR, True, 53),
        (_REPO_ROOT / "AISDLC_SDD" / "scripts" / "tests", True, 28),
        (_REPO_ROOT / "AutoClaude" / "tests", True, 268),
        # LATEST fsm_runtime **整棵遞迴**（原本 tests/ 與頂層分兩列、頂層還是 flat
        # ⇒ `meta_halt/`／`modality/` 兩個子樹整組在射程外）。
        (latest / "tools" / "fsm_runtime", True, 158),
        # 🔴 R69（DEF-101-702／R68-34）：以上全是測試樹。於是「Windows 開發者把
        # `D:/…` 字面路徑寫進生產碼」這條路在 mac 側全套護欄全綠——掃描面與缺陷面
        # 錯位。R69 實測擴面後存量債為 0，屬零成本擴面：生產碼與測試碼受同一判準。
        (_REPO_ROOT / "AutoClaude" / "autoclaude", True, 194),
        (_REPO_ROOT / "AutoClaude" / "tools", True, 42),
        (_REPO_ROOT / "AutoClaude" / "scripts", True, 1),
        (_REPO_ROOT / "AutoClaude" / "alembic", True, 18),
        # `tools` 與 `.claude/hooks` 兩棵的下限刻意只認並行包動工前就存在的那些檔：
        # 把一個當下還在變動的量寫成常數，下一輪必然對不上。
        (_REPO_ROOT / "tools", True, 17),
        (_REPO_ROOT / ".claude" / "hooks", True, 2),
        (_REPO_ROOT / "AISDLC_SDD" / "scripts", True, 13),
        (_REPO_ROOT / "tools" / "lib", True, 10),
        (latest / "tools" / "arch_fitness", True, 2),
        (latest / ".claude" / "hooks", True, 5),
    ]


def _scan_single_files() -> list[Path]:
    """樹機制掃不到的零散活躍 `.py`（逐檔具名，與姊妹鎖同一份清單）。

    不能把整個 `AISDLC_SDD/` 根樹納入——rglob 會誤掃凍結版 v0.01~v0.29。
    """
    return [
        _REPO_ROOT / "AISDLC_SDD" / "conftest.py",
        _latest_root() / "tools" / "__init__.py",
    ]


#: 零散單檔的檔數下限（等於清單長度：少一支＝有人刪了具名檔，必須是寫下來的動作）。
_SINGLE_FILE_FLOOR = 2
#: 零散單檔在下限帶訊息裡的標籤。
_SINGLE_UNIT_LABEL = "<零散單檔>"


def _scan_units() -> list[tuple[str, list[Path], int]]:
    """（標籤, 檔案清單, 檔數下限）——樹與零散單檔統一形狀，本檔五道判準共用。

    🔴 統一成一支的理由：本檔原有五個各自展開的掃描迴圈，每一個都自帶一份
    「列舉檔案 ＋ 判下限」的複本。擴掃描面時只改其中幾份，就是①那個缺口的
    製造方式；五份複本也讓「下限只有下界」這件事要修五次。
    """
    specs: list[tuple[Path, int, list[Path]]] = []
    for root, recursive, floor in _scan_roots():
        if not root.is_dir():
            raise AssertionError(f"掃描根缺席：{root}（邊界不得靜默縮小）")
        found = root.rglob("*.py") if recursive else root.glob("*.py")
        specs.append((root, floor, sorted(p for p in found
                                          if "__pycache__" not in p.parts)))
    roots = [root for root, _floor, _files in specs]
    units: list[tuple[str, list[Path], int]] = []
    for root, floor, files in specs:
        owned = [p for p in files if _owning_root(p, roots) == root]
        units.append((root.relative_to(_REPO_ROOT).as_posix(), owned, floor))
    singles = sorted(p for p in _scan_single_files() if p.is_file())
    units.append((_SINGLE_UNIT_LABEL, singles, _SINGLE_FILE_FLOOR))
    return units


def _owning_root(py: Path, roots: list[Path]) -> Path:
    """巢狀掃描根之間由**最長前綴**（最具體的那棵）認領該檔。

    order-independent：不靠清單順序決定歸屬，改清單順序不會讓某棵樹的下限
    突然對不上。這是「全部改遞迴」得以成立的前提——否則 `tools` 遞迴會把
    `tools/tests` 的 56 支再算一次，兩邊下限都失去意義。
    """
    return max((r for r in roots if r == py.parent or r in py.parents),
               key=lambda r: len(r.parts))


def floor_band_problems(counts: list[tuple[str, int, int]]) -> list[str]:
    """（標籤, 實測, 下限）逐筆過姊妹鎖的雙邊帶；回問題清單，空＝合格。

    純函式（紅綠由合成注入自證，見 `TestScanRootFloorBand`）。
    """
    return [
        verdict
        for label, actual, floor in counts
        if (verdict := tree_count_verdict(label, actual, floor)) is not None
    ]


def run_unit_scan(
    scanner: Callable[[str, str], tuple[list[str], list[str]]],
) -> tuple[list[str], list[str], list[str], list[str]]:
    """對 `_scan_units()` 每一支檔跑 `scanner`；回 (違規, stale, parse 失敗, 下限帶)。

    🔴 早退不得遮蔽（Scan-H⑦）：單檔 parse 失敗只記一筆並續掃，下限帶在**全部**
    掃完之後才算——原本的寫法把下限斷言放在迴圈內，第一棵樹一失敗就同時吃掉
    「其他樹的下限」與「違規清單」兩份訊號，而失敗訊息只講第一棵樹。
    """
    offenders: list[str] = []
    stale: list[str] = []
    parse_failures: list[str] = []
    counts: list[tuple[str, int, int]] = []
    for label, files, floor in _scan_units():
        scanned = 0
        for py in files:
            rel = py.relative_to(_REPO_ROOT).as_posix()
            try:
                off, st = scanner(py.read_text(encoding="utf-8"), rel)
            except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
                parse_failures.append(f"{rel}: {type(exc).__name__}: {exc}")
                continue
            offenders.extend(off)
            stale.extend(st)
            scanned += 1
        counts.append((label, scanned, floor))
    return offenders, stale, parse_failures, floor_band_problems(counts)


def scan_drive_literal(source: str, rel: str) -> tuple[list[str], list[str]]:
    """純函式核心：回傳 (offenders, stale)。stale 恆空（本判準的標記不做 stale 偵測）。

    本輪抽出：第一道判準原本只有「吃 `Path`」的入口，於是它是本檔唯一無法用合成
    字串直接餵的判準——注入語料矩陣（`TestXplatInjectionMatrix`）需要對**每一道**
    判準問同一個問題，缺一個入口就等於那一格永遠量不到。
    """
    offenders: list[str] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        if _OK_MARKER in line:  # (c) 行尾豁免標記（附理由）
            continue
        code = line.split("#", 1)[0]  # (a) 剝註解尾（heuristic，見 docstring）
        if any(tok in code for tok in _EXPLICIT_PLATFORM):  # (b) 顯式平台語意
            continue
        if _DRIVE_STR_RE.search(code):
            offenders.append(f"{rel}:{lineno}: {line.strip()}")
    return offenders, []


def _scan_file(py: Path) -> list[str]:
    rel = py.relative_to(_REPO_ROOT).as_posix()
    return scan_drive_literal(py.read_text(encoding="utf-8"), rel)[0]


class TestPlatformNeutralPaths(unittest.TestCase):
    def test_no_windows_drive_fake_paths(self) -> None:
        offenders: list[str] = []
        counts: list[tuple[str, int, int]] = []
        for label, files, floor in _scan_units():
            tree_scanned = 0
            for py in files:
                if py.relative_to(_REPO_ROOT).as_posix() in _ALLOWED:
                    continue
                offenders.extend(_scan_file(py))
                tree_scanned += 1
            counts.append((label, tree_scanned, floor))
        self.assertEqual(
            offenders,
            [],
            "發現 Windows 磁碟機假路徑字面值（POSIX 上非絕對路徑 → join 語意分歧假紅）"
            "——請改用 tools/tests/_platform_helpers.ABS_FAKE_REPO；確屬合法用法時，"
            "改寫為顯式 PureWindowsPath(…) 或行尾加 `# platform-ok: <理由>` 豁免：\n"
            + "\n".join(offenders),
        )
        band = floor_band_problems(counts)
        self.assertEqual(band, [], "掃描面下限帶：\n" + "\n".join(band))

    def test_allowed_exemptions_not_stale(self) -> None:
        """豁免清單防腐化：登記的檔案消失即紅（比照 parity 清單 stale 檢查）。"""
        for rel, why in _ALLOWED.items():
            self.assertTrue(
                (_REPO_ROOT / rel).is_file(),
                f"_ALLOWED 豁免 stale：{rel} 已不存在（WHY={why}）——請自清單移除",
            )


# ══════════════════════════════════════════════════════════════════════════════
# R60 round 3 — 測試不得把「樹內固定路徑」當可寫暫存區（QA-R60R3-01／ARCH-R60R3-05）
# ══════════════════════════════════════════════════════════════════════════════
# WHY（這是本檔第二道判準，與磁碟機假路徑正交，但同屬「測試原始碼的路徑寫法」家族，
# 故共用本檔的掃描根／豁免／stale 慣例，不另開新檔）：
#   `tools/fsm_runtime/tests/test_slv_generator.py` 的四個測試類把暫存規則目錄寫死成
#   `Path(__file__).resolve().parent / "_tmp_*"`——**tracked 樹內的共用固定路徑**，且
#   `setUp` 清空它、`tearDown` `rmdir` 它。兩個行程同時跑（並行四方複審／並行閘門／
#   CI 與地端同時跑）必互刪，產生與被測邏輯無關的假紅：
#     · `FileNotFoundError: ..._tmp_rules\SLV-900.yaml.lock`（QA 實測，並行 2/2 重現）
#     · `PermissionError: [WinError 32] ..._tmp_rules\SLV-900.yaml`（integration_gate 實測）
#     · `FileNotFoundError: [WinError 2] ..._tmp_imm_rules\SLV-910.yaml.tmp`（ARCH 實測）
#   隔離重跑必綠 ⇒ 長期被誤讀成 flaky。本鎖把「別再這樣寫」變成機械事實。
#   修法慣例＝`tempfile.mkdtemp()`（根治：兩行程拿到不同目錄）；只加
#   `unlink(missing_ok=True)` **不算**修好——那只讓競態不拋例外，資料仍互相污染。
#
# 判準（AST，非行級 regex）：對「寫入類呼叫」的目標表達式判斷它是否指向樹內固定路徑：
#   寫入動作＝`.mkdir/.write_text/.write_bytes/.touch/.unlink/.rmdir`、
#             `shutil.rmtree/copytree/move(<目標>)`、`open(<目標>, 'w'|'a'|'x'|'+')`。
#   「樹內固定路徑」＝該表達式自身含 `__file__`，或其最左名稱是**模組層常數**／
#   **同一個 class 內的 `self.<attr>`**，而該名稱曾被指派為含 `__file__` 的表達式。
#
# 🔴 刻意劃界（誠實記錄，勿超譯）：
#   ❌ **函式區域變數不追**。這不是偷懶，是為了避開一個已知會誤報的形態：本鎖的原型
#      掃描器做了跨作用域的別名傳遞，於是
#      `tools/tests/test_git_hooks_install_common.py` 內同名的 `hooks_dir`（第 152 行是
#      `_REPO_ROOT` 衍生，第 45／176 行卻是 tempdir 衍生）被整支污染成假陽性。同型病灶
#      在本 repo 已有前科（R46 `build_alias_map` 的函式→ClassDef 作用域碰撞）。
#      模組常數與 `self.<attr>` 兩種形態就足以涵蓋本缺陷家族的全部已知站點。
#   ❌ 路徑「當引數交給生產碼、由生產碼去寫」的形態不追（如 `rules_dir=self.tmp`）——
#      靜態無法判定被呼叫端是否真的寫入；實掃證實 `project_root=FIXTURE_ROOT`
#      （multimodal_validator，全檔零寫入）正是這種唯讀傳遞，追了就是假陽性。
#      本缺陷家族在此形態下仍會被 `.mkdir()` 那一半抓到，鑑別力不因此喪失。
#   ❌ `str.replace` 等與 `Path` 同名的方法刻意不納入寫入動作集合（實掃三處皆假陽性）。
#   ❌ **凍結版 v0.02~v0.29 不在掃描面**（見 `_tmpdir_scan_roots` 的 WHY）——那 95 個
#      同型站點確實存在且**未修**，是待裁決項，不是本鎖宣稱乾淨的區域。
_TMPDIR_OK_MARKER = "tmpdir-ok:"
_WRITE_ATTRS = frozenset({"mkdir", "write_text", "write_bytes", "touch", "unlink", "rmdir"})
_SHUTIL_WRITE_FUNCS = frozenset({"rmtree", "copytree", "move"})
# 走 tempfile 的表達式一律放行（那正是本鎖要人改成的樣子）；`tmp_path`／`tmpdir` 是
# pytest 內建 fixture，語意同為行程獨立暫存目錄。
_TEMPFILE_MARKS = frozenset({
    "mkdtemp", "mkstemp", "TemporaryDirectory", "NamedTemporaryFile", "TemporaryFile",
    "gettempdir", "tmp_path", "tmpdir", "tmp_path_factory",
})


def _has_file_ref(node: ast.AST) -> bool:
    return any(isinstance(s, ast.Name) and s.id == "__file__" for s in ast.walk(node))


def _has_tempfile_ref(node: ast.AST) -> bool:
    for s in ast.walk(node):
        if isinstance(s, ast.Attribute) and s.attr in _TEMPFILE_MARKS:
            return True
        if isinstance(s, ast.Name) and s.id in _TEMPFILE_MARKS:
            return True
    return False


def _is_in_tree_seed(node: ast.AST) -> bool:
    """該表達式是否為「樹內固定路徑」的種子（由 `__file__` 推導且未走 tempfile）。"""
    return _has_file_ref(node) and not _has_tempfile_ref(node)


def _path_root_name(node: ast.AST) -> str | None:
    """取路徑表達式最左的名稱；`self.tmp / a / b` → `self.tmp`、`X / "y"` → `X`。"""
    cur: ast.AST = node
    for _ in range(40):  # 上界防病態巢狀導致無界迴圈
        if isinstance(cur, ast.BinOp) and isinstance(cur.op, ast.Div):
            cur = cur.left
        elif isinstance(cur, ast.Attribute):
            if isinstance(cur.value, ast.Name):
                return f"self.{cur.attr}" if cur.value.id == "self" else cur.value.id
            cur = cur.value
        elif isinstance(cur, ast.Name):
            return cur.id
        elif isinstance(cur, ast.Call):
            if isinstance(cur.func, ast.Attribute):
                cur = cur.func.value        # x.resolve() → x
            elif cur.args:
                cur = cur.args[0]           # Path(x) → x
            else:
                return None
        elif isinstance(cur, ast.Subscript):
            cur = cur.value                 # parents[3] → parents
        else:
            return None
    return None


def _module_level_tree_names(tree: ast.Module) -> set[str]:
    """模組層被指派為樹內固定路徑的常數名（只看 top-level，不看函式內）。"""
    out: set[str] = set()
    for stmt in tree.body:
        if not isinstance(stmt, (ast.Assign, ast.AnnAssign)) or stmt.value is None:
            continue
        if not _is_in_tree_seed(stmt.value):
            continue
        targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
        out.update(t.id for t in targets if isinstance(t, ast.Name))
    return out


def _self_attr_tree_names(cls: ast.ClassDef) -> set[str]:
    """該 class 內被指派為樹內固定路徑的 `self.<attr>`（逐類獨立，不跨類污染）。"""
    out: set[str] = set()
    for node in ast.walk(cls):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
            continue
        if not _is_in_tree_seed(node.value):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for t in targets:
            if (isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name)
                    and t.value.id == "self"):
                out.add(f"self.{t.attr}")
    return out


def _tmpdir_markers(source: str) -> dict[int, str]:
    """{行號: WHY}——僅認 COMMENT token 內的標記（字串字面值同形文字不誤判）。"""
    markers: dict[int, str] = {}
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT and _TMPDIR_OK_MARKER in tok.string:
            markers[tok.start[0]] = tok.string.split(_TMPDIR_OK_MARKER, 1)[1].strip()
    return markers


def _write_target(node: ast.Call) -> tuple[ast.AST, str] | None:
    """該呼叫若是寫入動作，回傳 (目標表達式, 動作描述)；否則 None。"""
    func = node.func
    if isinstance(func, ast.Attribute):
        if func.attr in _WRITE_ATTRS:
            return func.value, f".{func.attr}()"
        if (func.attr in _SHUTIL_WRITE_FUNCS and isinstance(func.value, ast.Name)
                and func.value.id == "shutil" and node.args):
            return node.args[0], f"shutil.{func.attr}()"
        return None
    if isinstance(func, ast.Name) and func.id == "open" and node.args:
        mode = ""
        if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
            mode = str(node.args[1].value)
        for kw in node.keywords:
            if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                mode = str(kw.value.value)
        if any(c in mode for c in "wax+"):
            return node.args[0], f"open(mode={mode!r})"
    return None


def scan_intree_tmpdir(source: str, rel: str) -> tuple[list[str], list[str]]:
    """純函式核心：回傳 (offenders, stale_markers)，元素皆為 `rel:行號: 說明`。

    stale＝標記存在但該行沒有被壓下的違規（含 WHY 留空）→ 必須清掉或補 WHY。
    這條自檢是本鎖不淪為「永久白名單」的唯一保障（R60 已有
    `_PENDING_MIGRATION_SITES` 掛 pending 名義卻刻意不加 stale 自檢的前科）。
    """
    tree = ast.parse(source)  # SyntaxError 由呼叫端 fail-loud
    markers = _tmpdir_markers(source)
    module_names = _module_level_tree_names(tree)
    # (掃描節點, 該範圍可見的樹內固定路徑名稱)；class 各自帶自己的 self.<attr>
    scopes: list[tuple[ast.AST, set[str]]] = [(tree, module_names)]
    scopes.extend(
        (node, module_names | _self_attr_tree_names(node))
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
    )

    offenders: dict[tuple[int, str], str] = {}
    used: set[int] = set()
    for scope_node, tracked in scopes:
        for node in ast.walk(scope_node):
            if not isinstance(node, ast.Call):
                continue
            hit = _write_target(node)
            if hit is None:
                continue
            target, op = hit
            if _has_tempfile_ref(target):
                continue
            if not (_has_file_ref(target) or _path_root_name(target) in tracked):
                continue
            if markers.get(node.lineno):
                used.add(node.lineno)
                continue
            expr = " ".join((ast.get_source_segment(source, target) or "?").split())[:70]
            offenders[(node.lineno, op)] = (
                f"{rel}:{node.lineno}: {op} 寫入樹內固定路徑 `{expr}`"
                "（並行兩行程必互踩 → 假紅；請改用 tempfile.mkdtemp()）"
            )
    stale = [
        f"{rel}:{lineno}: tmpdir-ok 標記 stale"
        f"（{'WHY 留空' if not why else '該行無被壓下的違規'}）"
        for lineno, why in sorted(markers.items())
        if lineno not in used
    ]
    return [offenders[k] for k in sorted(offenders)], stale


def _tmpdir_scan_roots() -> list[tuple[Path, bool, int]]:
    """（掃描根, 是否遞迴, 該樹檔數下限）；下限＝落地當回合實測 × 0.95。

    🔴 本輪重釘（與 `_scan_roots()` 同一筆缺陷的第二個病灶）：原下限是「首掃數打
    八折」的化石且**只有下界**。落地當回合實測三棵已越過腐化上界（56 對 44、
    282 對 223、54 對 43），也就是本判準的掃描面此前可以掉掉兩成而全綠。改用姊妹
    鎖的雙邊帶（`tree_count_verdict`）後，下限自己過期時會當場紅並印出該填的數字。

    🔴 掃描面比本檔第一道判準多一棵「**凍結基線 v0.01**」，這是刻意的，WHY：
      `AISDLC_SDD/scripts/ci-gate.sh` 的 `FROZEN_BASELINE="AISDLC_SDD_v0.01"` 是
      **雙軌閘門實際會執行的兩棵樹之一**（另一棵是 LATEST）。第一道判準（磁碟機假
      路徑）不掃凍結版是因為那是「不可修的舊碼」；但本判準守的是「閘門自己會不會
      假紅」——v0.01 的測試每次 ci-gate 都真的在跑，它踩到的並行假紅會直接讓閘門
      說謊。「不掃它」等於讓已修好的東西可以無聲退化回去。
      中間 28 版（v0.02~v0.29）不在此列：任何自動閘門都不執行它們（ADR-XPLAT-001
      §2 機械事實），且那 95 個同型站點依 Copy-on-Evolve 尚待裁決是否回補——
      把它們納進來會讓本鎖一上線就紅，而那紅燈反映的是待決策，不是新退化。
    """
    return [
        (_TESTS_DIR, False, 53),                                       # 實測 56
        (_REPO_ROOT / "AISDLC_SDD" / "scripts" / "tests", False, 28),  # 實測 29
        (_REPO_ROOT / "AutoClaude" / "tests", True, 268),              # 實測 282
        (_latest_fsm_tests_dir(), True, 74),                           # 實測 78
        (_REPO_ROOT / "AISDLC_SDD" / "AISDLC_SDD_v0.01"                # 實測 54
         / "tools" / "fsm_runtime" / "tests", True, 51),
    ]


class TestNoInTreeWritableTmpDir(unittest.TestCase):
    """測試檔不得把 tracked 樹內固定路徑當可寫暫存區（見上方區段 WHY）。"""

    def test_no_test_writes_into_a_fixed_in_tree_path(self) -> None:
        offenders: list[str] = []
        stale: list[str] = []
        parse_failures: list[str] = []
        counts: list[tuple[str, int, int]] = []
        for root, recursive, floor in _tmpdir_scan_roots():
            self.assertTrue(root.is_dir(), f"掃描根缺席：{root}（邊界不得靜默縮小）")
            files = sorted(root.rglob("*.py") if recursive else root.glob("*.py"))
            scanned = 0
            for py in files:
                rel = py.relative_to(_REPO_ROOT).as_posix()
                try:
                    off, st = scan_intree_tmpdir(py.read_text(encoding="utf-8"), rel)
                except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
                    parse_failures.append(f"{rel}: {type(exc).__name__}: {exc}")
                    continue
                offenders.extend(off)
                stale.extend(st)
                scanned += 1
            counts.append((root.relative_to(_REPO_ROOT).as_posix(), scanned, floor))
        self.assertEqual(
            parse_failures, [],
            "以下 .py 無法 parse——掃描面不得靜默縮小：\n" + "\n".join(parse_failures),
        )
        self.assertEqual(
            offenders, [],
            "發現測試寫入樹內固定路徑（兩行程並行時互刪 → 與被測邏輯無關的假紅）"
            "——請改用 tempfile.mkdtemp()＋tearDown shutil.rmtree(..., ignore_errors=True)；"
            f"確屬刻意者於該行行尾加 `# {_TMPDIR_OK_MARKER} <WHY>` 豁免：\n"
            + "\n".join(offenders),
        )
        self.assertEqual(
            stale, [],
            f"{_TMPDIR_OK_MARKER} 豁免標記 stale（防清單腐化）：\n" + "\n".join(stale),
        )
        band = floor_band_problems(counts)
        self.assertEqual(band, [], "掃描面下限帶：\n" + "\n".join(band))

    # ── 以下以注入 fixture 自證判準紅綠（fixture 僅存在於 tmp，不留違規樣本於 repo）──

    def _scan(self, source: str) -> tuple[list[str], list[str]]:
        return scan_intree_tmpdir(source, "fixture_case.py")

    def test_injected_self_attr_offender_is_detected(self) -> None:
        """本缺陷的原形態（`self.tmp` ← 樹內固定路徑，setUp mkdir）必紅。"""
        off, stale = self._scan(
            "from pathlib import Path\n"
            "class T:\n"
            "    def setUp(self):\n"
            "        self.tmp = Path(__file__).resolve().parent / '_tmp_rules'\n"
            "        self.tmp.mkdir(parents=True, exist_ok=True)\n"
        )
        self.assertEqual(len(off), 1, off)
        self.assertIn(".mkdir()", off[0])
        self.assertEqual(stale, [])

    def test_injected_module_const_offender_is_detected(self) -> None:
        """模組層常數形態（`OUT = Path(__file__).parent / 'x'` 後 write_text）必紅。"""
        off, _ = self._scan(
            "from pathlib import Path\n"
            "OUT = Path(__file__).parent / 'snapshots'\n"
            "def test_x():\n"
            "    (OUT / 'a.json').write_text('{}', encoding='utf-8')\n"
        )
        self.assertEqual(len(off), 1, off)
        self.assertIn(".write_text()", off[0])

    def test_mkdtemp_form_is_accepted(self) -> None:
        """修法慣例（mkdtemp）必綠——否則本鎖會逼人改回舊寫法。"""
        off, stale = self._scan(
            "import shutil, tempfile\n"
            "from pathlib import Path\n"
            "class T:\n"
            "    def setUp(self):\n"
            "        self.tmp = Path(tempfile.mkdtemp(prefix='x_'))\n"
            "        self.tmp.mkdir(parents=True, exist_ok=True)\n"
            "    def tearDown(self):\n"
            "        shutil.rmtree(self.tmp, ignore_errors=True)\n"
        )
        self.assertEqual((off, stale), ([], []))

    def test_read_only_use_of_a_tree_path_is_not_flagged(self) -> None:
        """唯讀取樣本檔（fixtures）不得誤報——否則整棵測試樹都會紅。"""
        off, _ = self._scan(
            "from pathlib import Path\n"
            "FIXTURES = Path(__file__).parent / 'fixtures'\n"
            "def test_x():\n"
            "    assert (FIXTURES / 'a.yaml').read_text(encoding='utf-8')\n"
        )
        self.assertEqual(off, [])

    def test_local_variable_form_is_declared_out_of_scope(self) -> None:
        """劃界釘死：函式區域變數**不追**（見區段 WHY 的作用域碰撞前車之鑑）。

        這支測試存在的意義不是「保護這個行為」，而是讓射程邊界**被寫下來且可被看見**
        ——哪天有人要把區域變數納入，必須先來改掉這支測試，於是那個決定不會是靜默的。
        """
        off, _ = self._scan(
            "from pathlib import Path\n"
            "ROOT = Path(__file__).resolve().parents[1]\n"
            "def test_x():\n"
            "    d = ROOT / 'build' / 'x'\n"
            "    d.mkdir(parents=True, exist_ok=True)\n"
        )
        self.assertEqual(off, [], "區域變數形態應在射程外——射程若被擴大請同步改本測試")

    def test_marker_suppresses_and_missing_violation_makes_it_stale(self) -> None:
        """豁免標記能壓下違規；標記在、違規不在（或 WHY 留空）→ stale 必紅。"""
        base = (
            "from pathlib import Path\n"
            "OUT = Path(__file__).parent / 'snapshots'\n"
            "def test_x():\n"
        )
        off, stale = self._scan(
            base + f"    OUT.mkdir(exist_ok=True)  # {_TMPDIR_OK_MARKER} golden 快照目錄\n")
        self.assertEqual((off, stale), ([], []), "附 WHY 的標記應壓下違規且不判 stale")

        off, stale = self._scan(
            base + f"    OUT.mkdir(exist_ok=True)  # {_TMPDIR_OK_MARKER}\n")
        self.assertEqual(len(off), 1, "WHY 留空的標記不得生效")
        self.assertEqual(len(stale), 1, stale)
        self.assertIn("WHY 留空", stale[0])

        off, stale = self._scan(
            base + f"    assert OUT.exists()  # {_TMPDIR_OK_MARKER} 已改用 mkdtemp\n")
        self.assertEqual(off, [])
        self.assertEqual(len(stale), 1, "違規已消失的標記必須被指名刪除")
        self.assertIn("該行無被壓下的違規", stale[0])

    def test_marker_inside_a_string_literal_is_not_honoured(self) -> None:
        """標記只認 COMMENT token——字串字面值裡的同形文字不得當豁免用。"""
        off, _ = self._scan(
            "from pathlib import Path\n"
            "OUT = Path(__file__).parent / 'snapshots'\n"
            "def test_x():\n"
            f"    s = '# {_TMPDIR_OK_MARKER} 假裝豁免'\n"
            "    OUT.mkdir(exist_ok=True)\n"
        )
        self.assertEqual(len(off), 1, "字串裡的標記不得生效")

    def test_scan_surface_is_not_silently_empty(self) -> None:
        """反空轉：判準在真實檔案上跑得動且掃描根皆存在（防路徑寫錯靜默零違規）。"""
        roots = _tmpdir_scan_roots()
        self.assertGreaterEqual(len(roots), 5, "掃描根被刪列？")
        for root, _recursive, floor in roots:
            self.assertTrue(root.is_dir(), f"掃描根缺席：{root}")
            self.assertGreater(floor, 0, f"{root} 的下限不得為 0（等於沒有下限）")

    def test_detector_survives_a_real_file_roundtrip(self) -> None:
        """判準對「真的寫在磁碟上的檔」也成立（非只在字串 fixture 上成立）。"""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "fixture_case.py"
            p.write_text(
                "from pathlib import Path\n"
                "OUT = Path(__file__).parent / '_tmp_x'\n"
                "OUT.mkdir(exist_ok=True)\n",
                encoding="utf-8",
            )
            off, stale = scan_intree_tmpdir(p.read_text(encoding="utf-8"), "fixture_case.py")
        self.assertEqual(len(off), 1, off)
        self.assertEqual(stale, [])


# ══════════════════════════════════════════════════════════════════════════════
# R69 — 反方向：測試不得拿 POSIX 絕對路徑字面值去斷言 Path 產物
# ══════════════════════════════════════════════════════════════════════════════
# WHY（本檔第三道判準；與第一道判準是**同一個病的兩個方向**）：
#   第一道守「Windows 磁碟機字面值 → Mac 假紅」，但反方向此前**零守門**：
#   `tools/tests/test_dev_start.py:2959` 寫
#       self.assertIn("/elsewhere", printed)
#   而 `printed` 的來源是生產碼把一個 `Path` 內插進訊息字串。`Path` 的 `str()`
#   在 Windows 是 `\elsewhere\AutoClaude\…`，POSIX 字面值必然落空 →
#   **Mac/Linux 全綠、windows-compat-ci 假紅**（R68 `375f291` 實紅，run 30720156050；
#   同 commit 前一版 `24c5f34` 為 success，故確定是新增測試帶進來的病，不是環境）。
#   本輪本機無 Windows 真機 ⇒ 這種病只能靠雲端 CI 才發現，一次來回數十分鐘；本鎖把它
#   拉到 macOS 本機的 `python tools/run_root_unittests.py` 就抓到。
#   修法慣例＝把字面值換成 `str(Path(<同一個字面值常數>))`（兩平台各自正規化後比對，
#   斷言強度不降反升——鎖的是**整條路徑**而非片段），或改用 `PurePosixPath`／
#   `as_posix()` 明示語意。
#
# 判準（AST）：`*.assert*(…)` 呼叫的引數（含 keyword 值、含巢狀於 list/tuple/set/dict
#   內的元素）出現 **POSIX 絕對路徑字面值**（以單一 `/` 開頭、次字元非 `/` 非空白）。
#
# 🔴 刻意劃界（誠實記錄，勿超譯 — 沿用本檔既有慣例）：
#   ❌ **不做值流分析**。「比對對象是不是 Path 產物」靜態不可判定：病灶站點的
#      `printed` 是由 helper method 回傳的區域變數，任何合理的 Path-來源推導都追不到它
#      （實測：以「名稱曾被指派為含 Path(/resolve()/os.fspath 的運算式」為條件時，
#      本病灶站點**漏抓**）。故採「assert 家族引數出現 POSIX 絕對路徑字面值」這個
#      過寬近似——代價由下面兩條劃界壓到實測零誤報。
#   ❌ **pytest 裸 `assert` 形態不在射程**。實測四棵樹裸 assert 命中 44 筆，絕大多數
#      不是路徑（`/compact` 是 Claude Code slash 指令、`/T` `/F` `/PID` 是 tasklist 欄位、
#      `/api/config/schema` 是 URL path、`/tmp/x.yaml` 是從未 Path 化的假字串）。納入
#      即等於一上線就要開 40 餘筆白名單——那會讓本鎖淪為永久白名單，反而失去鑑別力。
#      unittest 形態涵蓋四棵樹的實際病灶家族（實掃：修前 1 筆＝真陽性、修後 0 筆）。
#   ❌ **f-string 片段不算字面值**。`f"{parent}/archive/（小寫）復活了"` 這種訊息文字
#      被 AST 拆成 Constant，形狀與路徑字面值無法區分（實測 2 筆皆為訊息文字誤報）；
#      JoinedStr 內的 Constant 一律不計。
_POSIX_OK_MARKER = "posix-abs-ok:"
# 以單一 `/` 起頭、次字元非 `/`（排除 `//host` UNC 與註解式 `//`）非空白（排除純 "/"）。
_POSIX_ABS_RE = re.compile(r"^/(?![/\s])\S")


def _posix_abs_literal(node: ast.AST) -> bool:
    return (isinstance(node, ast.Constant) and isinstance(node.value, str)
            and bool(_POSIX_ABS_RE.match(node.value)))


def _posix_markers(source: str) -> dict[int, str]:
    """{行號: WHY}——僅認 COMMENT token（字串字面值內的同形文字不當豁免）。"""
    markers: dict[int, str] = {}
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT and _POSIX_OK_MARKER in tok.string:
            markers[tok.start[0]] = tok.string.split(_POSIX_OK_MARKER, 1)[1].strip()
    return markers


def _literal_args(call: ast.Call) -> list[ast.Constant]:
    """該 assert 呼叫的引數中所有 POSIX 絕對路徑字面值（含容器內巢狀；跳過 f-string）。"""
    out: list[ast.Constant] = []
    stack: list[ast.AST] = list(call.args) + [kw.value for kw in call.keywords]
    while stack:
        node = stack.pop()
        if isinstance(node, ast.JoinedStr):  # f-string 整棵子樹跳過（見劃界）
            continue
        if _posix_abs_literal(node):
            out.append(node)  # type: ignore[arg-type]
            continue
        stack.extend(ast.iter_child_nodes(node))
    return out


def scan_posix_abs_asserts(source: str, rel: str) -> tuple[list[str], list[str]]:
    """純函式核心：回傳 (offenders, stale_markers)，元素皆為 `rel:行號: 說明`。"""
    tree = ast.parse(source)  # SyntaxError 由呼叫端 fail-loud
    markers = _posix_markers(source)
    offenders: dict[tuple[int, int], str] = {}
    used: set[int] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if not node.func.attr.startswith("assert"):
            continue
        for lit in _literal_args(node):
            # WHY 留空的標記不生效（truthiness 判斷，對齊 tmpdir 判準）
            hit_line = next((ln for ln in (lit.lineno, node.lineno) if markers.get(ln)), None)
            if hit_line is not None:
                used.add(hit_line)
                continue
            offenders[(lit.lineno, lit.col_offset)] = (
                f"{rel}:{lit.lineno}: {node.func.attr}(…) 的引數是 POSIX 絕對路徑字面值 "
                f"`{lit.value}`（比對對象若由 Path/os.fspath 算出，Windows 上會渲染成"
                "反斜線 ⇒ 字面值必然落空、Mac 全綠 Windows 假紅）"
            )
    stale = [
        f"{rel}:{lineno}: {_POSIX_OK_MARKER} 標記 stale"
        f"（{'WHY 留空' if not why else '該行無被壓下的違規'}）"
        for lineno, why in sorted(markers.items())
        if lineno not in used or not why
    ]
    return [offenders[k] for k in sorted(offenders)], stale


class TestNoPosixAbsPathLiteralInAsserts(unittest.TestCase):
    """assert 引數不得寫死 POSIX 絕對路徑字面值（見上方區段 WHY）。"""

    def test_no_posix_abs_literal_asserted_against_path_output(self) -> None:
        offenders, stale, parse_failures, band = run_unit_scan(scan_posix_abs_asserts)
        self.assertEqual(
            parse_failures, [],
            "以下 .py 無法 parse——掃描面不得靜默縮小：\n" + "\n".join(parse_failures),
        )
        self.assertEqual(
            offenders, [],
            "發現 assert 拿 POSIX 絕對路徑字面值比對（Windows 上 Path 渲染成反斜線 ⇒ "
            "本機全綠、windows-compat-ci 假紅，R69 病灶實例）——請改成 "
            "`str(Path(<同一常數>))` 或 `PurePosixPath`／`as_posix()` 明示語意；"
            f"確屬刻意者於該行行尾加 `# {_POSIX_OK_MARKER} <WHY>` 豁免：\n"
            + "\n".join(offenders),
        )
        self.assertEqual(
            stale, [],
            f"{_POSIX_OK_MARKER} 豁免標記 stale（防清單腐化）：\n" + "\n".join(stale),
        )
        self.assertEqual(band, [], "掃描面下限帶：\n" + "\n".join(band))

    # ── 以下以注入 fixture 自證判準紅綠（fixture 僅存在於字串，不留違規樣本於 repo）──

    def _scan(self, source: str) -> tuple[list[str], list[str]]:
        return scan_posix_abs_asserts(source, "fixture_case.py")

    def test_injected_original_defect_shape_is_detected(self) -> None:
        """R69 病灶原形態（`assertIn("/elsewhere", printed)`）必紅。"""
        off, stale = self._scan(
            "class T:\n"
            "    def test_x(self):\n"
            '        self.assertIn("/elsewhere", printed, "須指出實際指向的路徑")\n'
        )
        self.assertEqual(len(off), 1, off)
        self.assertIn("/elsewhere", off[0])  # posix-abs-ok: 判準自己的訊息字串，非 Path 產物
        self.assertIn("assertIn", off[0])
        self.assertEqual(stale, [])

    def test_fixed_shape_is_accepted(self) -> None:
        """修法慣例（`str(Path(常數))`）必綠——否則本鎖會逼人改回舊寫法。"""
        off, stale = self._scan(
            "from pathlib import Path\n"
            "class T:\n"
            '    _ELSEWHERE = "/elsewhere/AutoClaude/tools/run_local_nightly.sh"\n'
            "    def test_x(self):\n"
            "        self.assertIn(str(Path(self._ELSEWHERE)), printed)\n"
        )
        self.assertEqual((off, stale), ([], []))

    def test_literal_nested_in_a_container_is_detected(self) -> None:
        """容器內的字面值同樣是病灶（`assertEqual(x, ["/a/b"])`）。"""
        off, _ = self._scan(
            "class T:\n"
            "    def test_x(self):\n"
            '        self.assertEqual(paths, ["/a/b", "rel/c"])\n'
        )
        self.assertEqual(len(off), 1, off)
        self.assertIn("/a/b", off[0])  # posix-abs-ok: 同上，比對判準自己的訊息字串

    def test_fstring_message_fragment_is_not_flagged(self) -> None:
        """f-string 訊息片段不算字面值（實測 2 筆誤報的形狀；見劃界）。"""
        off, _ = self._scan(
            "class T:\n"
            "    def test_x(self):\n"
            '        self.assertEqual(lower, 0, f"{parent}/archive/（小寫）復活了")\n'
        )
        self.assertEqual(off, [])

    def test_relative_and_bare_slash_are_not_flagged(self) -> None:
        """相對路徑與純 `/`／`//` 不在射程（前者無平台分歧，後者非路徑形狀）。"""
        off, _ = self._scan(
            "class T:\n"
            "    def test_x(self):\n"
            '        self.assertIn("docs/04_planning", out)\n'
            '        self.assertEqual(sep, "/")\n'
            '        self.assertIn("// 註解", src)\n'
        )
        self.assertEqual(off, [])

    def test_bare_pytest_assert_is_declared_out_of_scope(self) -> None:
        """劃界釘死：**本判準（過寬近似）**對 pytest 裸 assert 不追（見區段 WHY 的
        44 筆實測噪音；R69 P1 複測為 41 筆，仍全數是 slash 指令／CLI 旗標／URL）。

        這支測試存在的意義不是保護此行為，而是讓射程邊界**被寫下且可被看見**——
        哪天要納入裸 assert，必須先來改掉這支測試，於是那個決定不會是靜默的。

        🔴 R69 P1 更新：裸 assert 並非整體無守——本檔**第四道判準**
        （`scan_path_str_identity`，見下方區段）以「同句語法可見 Path 產物」為窄化
        條件，**涵蓋裸 assert**且實測零誤報。此處放行的只是「無 Path 產物在場」的
        過寬形態。
        """
        off, _ = self._scan('def test_x():\n    assert "/elsewhere" in printed\n')
        self.assertEqual(off, [], "裸 assert 形態應在射程外——射程若擴大請同步改本測試")

    def test_marker_suppresses_and_missing_violation_makes_it_stale(self) -> None:
        """豁免標記能壓下違規；標記在、違規不在（或 WHY 留空）→ stale 必紅。"""
        head = "class T:\n    def test_x(self):\n"
        off, stale = self._scan(
            head + f'        self.assertIn("/proc/self", out)  # {_POSIX_OK_MARKER} Linux 專屬\n')
        self.assertEqual((off, stale), ([], []), "附 WHY 的標記應壓下違規且不判 stale")

        off, stale = self._scan(
            head + f'        self.assertIn("/proc/self", out)  # {_POSIX_OK_MARKER}\n')
        self.assertEqual(len(off), 1, "WHY 留空的標記不得生效")
        self.assertIn("WHY 留空", stale[0])

        off, stale = self._scan(
            head + f'        self.assertIn("x", out)  # {_POSIX_OK_MARKER} 已改用 str(Path())\n')
        self.assertEqual(off, [])
        self.assertEqual(len(stale), 1, "違規已消失的標記必須被指名刪除")
        self.assertIn("該行無被壓下的違規", stale[0])

    def test_marker_inside_a_string_literal_is_not_honoured(self) -> None:
        """標記只認 COMMENT token——字串字面值裡的同形文字不得當豁免用。"""
        off, _ = self._scan(
            "class T:\n"
            "    def test_x(self):\n"
            f"        s = '# {_POSIX_OK_MARKER} 假裝豁免'\n"
            '        self.assertIn("/elsewhere", out)\n'
        )
        self.assertEqual(len(off), 1, "字串裡的標記不得生效")

    def test_detector_catches_the_pre_fix_form_of_the_real_file(self) -> None:
        """自我驗證（最重要的一支）：本鎖對**真實病灶檔案的修復前形態**必須紅。

        做法是把現行真檔的修復行「改寫回」R69 病灶當初的寫法再餵給判準——不查
        git（不能綁 HEAD：修復一 commit，綁 HEAD 的自證就會反過來變紅，等於埋定時
        炸彈；也不能綁固定 commit：淺 clone 取不到只能 skip＝在 CI 上空轉）。
        現行真檔同時必須是乾淨的，兩個方向一起鎖，本判準才不可能空轉。
        """
        real = _REPO_ROOT / "tools" / "tests" / "test_dev_start.py"
        src = real.read_text(encoding="utf-8")
        fixed_form = "self.assertIn(str(Path(self._ELSEWHERE)), printed,"
        self.assertIn(
            fixed_form, src,
            "R69 病灶的修復形態已不在 test_dev_start.py ⇒ 本自證失去對象——"
            "該處若被重寫，請同步更新這支測試指向新的修復形態，不要直接刪掉自證",
        )
        pre_fix = src.replace(fixed_form, 'self.assertIn("/elsewhere", printed,')
        off, _ = scan_posix_abs_asserts(pre_fix, "tools/tests/test_dev_start.py@修復前重建")
        self.assertTrue(
            any("/elsewhere" in o for o in off),  # posix-abs-ok: 比對判準訊息，非 Path 產物
            f"本鎖對修復前的真實病灶抓不到 ⇒ 判準空轉：{off}",
        )
        off_now, stale_now = scan_posix_abs_asserts(src, "tools/tests/test_dev_start.py")
        self.assertEqual((off_now, stale_now), ([], []), "現行真檔必須已無此病灶")


# ══════════════════════════════════════════════════════════════════════════════
# R69 — 第三道判準的姊妹：不得用 `mock.call` 物件的 repr 拼裝輸出再拿去斷言
# ══════════════════════════════════════════════════════════════════════════════
# WHY（與上一道判準是**同一個病的另一個入口**）：
#   上一道守「斷言側寫死 POSIX 字面值」，但病也可以從**被斷言的那一側**進來：
#       printed = " ".join(str(c) for c in fake_print.call_args_list)   # ← c 是 mock.call
#   `str(mock.call(x))` 走的是 `repr`，於是字串裡的反斜線被轉義成 `\\`、換行變成
#   `\n` 兩個字元。Windows 上生產碼印出的 `Path` 是 `\elsewhere\AutoClaude\…`，
#   拼進 repr 後變成 `\\elsewhere\\AutoClaude\\…` ⇒ 任何對路徑（或多行文案）的
#   `assertIn` 在 Windows 必然落空、Mac/Linux 全綠。實測（R69）：
#       str(mock.call(r"…\elsewhere\AutoClaude\…"))
#         → call('… \\elsewhere\\AutoClaude\\…')      ← 斷言 False
#       " ".join(str(a) for a in c.args)
#         → … \elsewhere\AutoClaude\…                 ← 斷言 True
#   A1 只修了 `test_dev_start.py` 的一處，姊妹站點（同檔 2656、
#   `AutoClaude/tests/test_perception.py` 三處）仍是舊寫法且零守門 ⇒ 本判準補上。
#   修法慣例：`str(a) for c in <mock>.call_args_list for a in c.args`（取實際引數）。
#
# 判準（AST）：迭代 `*.call_args_list` / `*.mock_calls` / `*.await_args_list` 的
#   comprehension 或 for 迴圈，其迴圈變數（`mock.call` 物件）被 `str()`／`repr()`／
#   f-string 內插**整個物件**。取 `.args` / `.kwargs` / `.args[0]` 的形態不在射程
#   （那正是修法本身）。
#
# 🔴 刻意劃界（誠實記錄）：
#   ❌ 不追「先把 call_args_list 指派給區域變數、再於另一處迭代」的跨陳述式形態
#      —— 那需要值流分析（同上一道判準的劃界理由）。實掃四棵樹＋生產碼樹此形態 0 筆，
#      納入的成本大於收益；哪天出現，靠 windows-compat-ci 兜底。
#   ❌ 不追 `assertIn(x, str(mock_obj.mock_calls))` 這種「整個 list 直接 repr」形態
#      —— 實掃 0 筆；同理留給 CI 兜底。射程若擴大，請同步改本區段測試。
_CALLREPR_OK_MARKER = "call-repr-ok:"
_CALL_LIST_ATTRS = ("call_args_list", "mock_calls", "await_args_list")


def _callrepr_markers(source: str) -> dict[int, str]:
    """{行號: WHY}——僅認 COMMENT token（對齊本檔其他判準）。"""
    markers: dict[int, str] = {}
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT and _CALLREPR_OK_MARKER in tok.string:
            markers[tok.start[0]] = tok.string.split(_CALLREPR_OK_MARKER, 1)[1].strip()
    return markers


def _bare_repr_uses(body: list[ast.AST], name: str) -> list[tuple[int, str]]:
    """`body` 子樹中把裸名 `name` 丟進 str()/repr()/f-string 的站點 [(行號, 形態)]。"""
    hits: list[tuple[int, str]] = []
    for root in body:
        for node in ast.walk(root):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in ("str", "repr")):
                for arg in node.args:
                    if isinstance(arg, ast.Name) and arg.id == name:
                        hits.append((node.lineno, f"{node.func.id}({name})"))
            elif (isinstance(node, ast.FormattedValue)
                  and isinstance(node.value, ast.Name) and node.value.id == name):
                hits.append((node.lineno, f'f"{{{name}}}"'))
    return hits


def _call_list_loops(tree: ast.AST):
    """產出 (迴圈變數名, 該迴圈的 body 子樹清單)——僅限迭代 mock 呼叫紀錄清單者。"""
    for node in ast.walk(tree):
        if isinstance(node, (ast.GeneratorExp, ast.ListComp, ast.SetComp)):
            pairs = [(node.elt, node.generators)]
        elif isinstance(node, ast.DictComp):
            pairs = [(node.key, node.generators), (node.value, node.generators)]
        elif isinstance(node, ast.For):
            pairs = [(None, [ast.comprehension(target=node.target, iter=node.iter,
                                               ifs=[], is_async=0)])]
        else:
            continue
        for elt, comps in pairs:
            for comp in comps:
                if not (isinstance(comp.iter, ast.Attribute)
                        and comp.iter.attr in _CALL_LIST_ATTRS):
                    continue
                if not isinstance(comp.target, ast.Name):
                    continue
                body = [elt] if elt is not None else list(getattr(node, "body", []))
                yield comp.target.id, [b for b in body if b is not None]


def scan_call_obj_repr(source: str, rel: str) -> tuple[list[str], list[str]]:
    """純函式核心：回傳 (offenders, stale_markers)，元素皆為 `rel:行號: 說明`。"""
    tree = ast.parse(source)  # SyntaxError 由呼叫端 fail-loud
    markers = _callrepr_markers(source)
    offenders: dict[int, str] = {}
    used: set[int] = set()
    for name, body in _call_list_loops(tree):
        for lineno, shape in _bare_repr_uses(body, name):
            if markers.get(lineno):
                used.add(lineno)
                continue
            offenders[lineno] = (
                f"{rel}:{lineno}: `{shape}` 把 mock.call 物件整個 repr 掉"
                "（反斜線被轉義成 `\\\\`、換行變 `\\n` 字面 ⇒ 對路徑／多行文案的斷言"
                "在 Windows 必假紅）——請改取實際引數 `str(a) for c in … for a in c.args`"
            )
    stale = [
        f"{rel}:{lineno}: {_CALLREPR_OK_MARKER} 標記 stale"
        f"（{'WHY 留空' if not why else '該行無被壓下的違規'}）"
        for lineno, why in sorted(markers.items())
        if lineno not in used or not why
    ]
    return [offenders[k] for k in sorted(offenders)], stale


class TestNoMockCallObjectRepr(unittest.TestCase):
    """拼裝斷言用輸出時不得 repr 整個 mock.call 物件（見上方區段 WHY）。"""

    def test_no_call_object_repr_used_to_build_asserted_output(self) -> None:
        offenders, stale, parse_failures, band = run_unit_scan(scan_call_obj_repr)
        self.assertEqual(
            parse_failures, [],
            "以下 .py 無法 parse——掃描面不得靜默縮小：\n" + "\n".join(parse_failures),
        )
        self.assertEqual(
            offenders, [],
            "發現以 mock.call 物件的 repr 拼裝斷言用輸出（R69 病灶家族，4 處實例）——"
            f"確屬刻意者於該行行尾加 `# {_CALLREPR_OK_MARKER} <WHY>` 豁免：\n"
            + "\n".join(offenders),
        )
        self.assertEqual(
            stale, [],
            f"{_CALLREPR_OK_MARKER} 豁免標記 stale（防清單腐化）：\n" + "\n".join(stale),
        )
        self.assertEqual(band, [], "掃描面下限帶：\n" + "\n".join(band))

    # ── 以注入 fixture 自證判準紅綠 ──────────────────────────────────────────

    def _scan(self, source: str) -> tuple[list[str], list[str]]:
        return scan_call_obj_repr(source, "fixture_case.py")

    def test_injected_original_defect_shape_is_detected(self) -> None:
        """病灶原形態（generator + `str(c)`）必紅。"""
        off, stale = self._scan(
            "class T:\n"
            "    def test_x(self):\n"
            '        printed = " ".join(str(c) for c in fake_print.call_args_list)\n'
        )
        self.assertEqual(len(off), 1, off)
        self.assertIn("str(c)", off[0])
        self.assertEqual(stale, [])

    def test_listcomp_and_for_loop_and_fstring_forms_are_detected(self) -> None:
        """三種等價寫法（list comp／for 迴圈／f-string 內插）同樣是病灶。"""
        for src in (
            "class T:\n    def t(self):\n"
            "        calls = [str(c) for c in proc.stdin.write.call_args_list]\n",
            "class T:\n    def t(self):\n"
            "        for c in m.mock_calls:\n            out.append(repr(c))\n",
            "class T:\n    def t(self):\n"
            '        out = [f"{c}" for c in m.await_args_list]\n',
        ):
            with self.subTest(src=src):
                off, _ = self._scan(src)
                self.assertEqual(len(off), 1, off)

    def test_fixed_shape_is_accepted(self) -> None:
        """修法慣例（取 `.args` 實際引數）必綠——否則本鎖會逼人改回舊寫法。"""
        off, stale = self._scan(
            "class T:\n"
            "    def test_x(self):\n"
            '        printed = " ".join(str(a) for c in fake_print.call_args_list'
            " for a in c.args)\n"
            '        other = "\\n".join(str(c.args[0]) for c in mp.call_args_list if c.args)\n'
        )
        self.assertEqual((off, stale), ([], []))

    def test_unrelated_iterables_are_not_flagged(self) -> None:
        """只認 mock 呼叫紀錄清單——迭代一般序列的 `str(x)` 不在射程。"""
        off, _ = self._scan(
            "class T:\n"
            "    def test_x(self):\n"
            "        joined = ' '.join(str(x) for x in some_list)\n"
        )
        self.assertEqual(off, [])

    def test_marker_suppresses_and_missing_violation_makes_it_stale(self) -> None:
        """豁免標記能壓下違規；標記在、違規不在（或 WHY 留空）→ stale 必紅。"""
        head = "class T:\n    def test_x(self):\n"
        line = "        calls = [str(c) for c in m.call_args_list]"
        off, stale = self._scan(f"{head}{line}  # {_CALLREPR_OK_MARKER} 只比對呼叫次數\n")
        self.assertEqual((off, stale), ([], []), "附 WHY 的標記應壓下違規且不判 stale")

        off, stale = self._scan(f"{head}{line}  # {_CALLREPR_OK_MARKER}\n")
        self.assertEqual(len(off), 1, "WHY 留空的標記不得生效")
        self.assertIn("WHY 留空", stale[0])

        off, stale = self._scan(
            f"{head}        x = 1  # {_CALLREPR_OK_MARKER} 已改取 .args\n")
        self.assertEqual(off, [])
        self.assertEqual(len(stale), 1, "違規已消失的標記必須被指名刪除")
        self.assertIn("該行無被壓下的違規", stale[0])

    def test_marker_inside_a_string_literal_is_not_honoured(self) -> None:
        """標記只認 COMMENT token——字串字面值裡的同形文字不得當豁免用。"""
        off, _ = self._scan(
            "class T:\n"
            "    def test_x(self):\n"
            f"        s = '# {_CALLREPR_OK_MARKER} 假裝豁免'\n"
            "        calls = [str(c) for c in m.call_args_list]\n"
        )
        self.assertEqual(len(off), 1, "字串裡的標記不得生效")

    def test_detector_catches_the_pre_fix_form_of_the_real_files(self) -> None:
        """自我驗證：對兩支真實病灶檔的**修復前形態**必須紅，現行真檔必須乾淨。

        做法與上一道判準相同——不查 git（綁 HEAD 會在修復 commit 後反過來變紅），
        而是把現行真檔的修復行改寫回病灶寫法再餵給判準。
        """
        cases = [
            ("tools/tests/test_dev_start.py",
             'str(a) for c in fake_print.call_args_list for a in c.args',
             'str(c) for c in fake_print.call_args_list'),
            ("AutoClaude/tests/test_perception.py",
             '[str(a) for c in proc.stdin.write.call_args_list for a in c.args]',
             '[str(c) for c in proc.stdin.write.call_args_list]'),
        ]
        for rel, fixed_form, pre_fix_form in cases:
            with self.subTest(rel=rel):
                src = (_REPO_ROOT / rel).read_text(encoding="utf-8")
                self.assertIn(
                    fixed_form, src,
                    f"{rel} 的修復形態已不在檔內 ⇒ 本自證失去對象——該處若被重寫，"
                    "請同步更新這支測試指向新的修復形態，不要直接刪掉自證",
                )
                off, _ = scan_call_obj_repr(src.replace(fixed_form, pre_fix_form),
                                            f"{rel}@修復前重建")
                self.assertTrue(off, f"本鎖對 {rel} 修復前的病灶抓不到 ⇒ 判準空轉")
                off_now, stale_now = scan_call_obj_repr(src, rel)
                self.assertEqual((off_now, stale_now), ([], []), f"{rel} 現行必須已無此病灶")


# ══════════════════════════════════════════════════════════════════════════════
# R69 P1 — 第四道判準：Path 的平台相依字串化不得當「識別鍵／比對值」
# ══════════════════════════════════════════════════════════════════════════════
# WHY（本判準是為了補上第三道判準結構性抓不到的洞——那個洞正好放走了一個 P1）：
#   `tools/tests/test_dev_start.py` 的 `_scoped_sources()` 曾寫
#       out[str(path.relative_to(_TOOLS_DIR.parent))] = src        # ← 產出側
#       ...
#       self.assertIn("tools/dev_start.py", scoped)                 # ← 斷言側
#       self.assertNotIn("tools/lib/ci_liveness.py", scoped)        # ← 斷言側
#   `str(PurePath)` 在 Windows 渲染成 `tools\dev_start.py`。於是 Windows 上：
#     · `assertIn` 必然落空 ⇒ **windows-compat-ci 再度轉紅**（Mac/Linux 全綠）；
#     · `assertNotIn` 更糟——它**恆真通過**，而它正是「ci_liveness 不得進入
#       下限版 prelude 射程」那道鎖本身 ⇒ Windows 側整條變成**假鎖**。
#   實測重現（ntpath 語意注入真實測試類）：
#       AssertionError: 'tools/dev_start.py' not found in
#       {'tools\\bootstrap_core.py': ...}
#   第三道判準抓不到它，原因是**結構性**的：它的正則要求字面值以 `/` 開頭，
#   而這裡的字面值是**相對路徑**（`tools/dev_start.py`）。
#
# 為什麼不是把第三道判準的正則放寬到相對路徑就好：
#   相對路徑形狀的字面值在四棵測試樹＋生產碼樹極為普遍（`docs/04_planning`、
#   URL path、套件名 `a/b`…），過寬近似在此形態下會爆量誤報。故本判準改採
#   **窄化條件**：必須有「語法上可判定的 Path 產物」在場。分兩個入口：
#
#   (4a) 產出側：`str(<Path 產物>)` 被當成**識別鍵**——dict 下標／dict/set 字面值
#        或推導式的鍵／`.add(...)`。這正是上面病灶的**源頭**那一行。修法＝
#        `.as_posix()`（或 `PurePosixPath`），兩平台同鍵。
#   (4b) 斷言側：同一個斷言（**含 pytest 裸 `assert`**）裡同時出現「路徑形狀字面值
#        （絕對或相對）」與「語法可見的 Path 產物」。修法＝`as_posix()` 或
#        `str(Path(<同一字面值>))`。
#
# 🔴 刻意劃界（誠實記錄，勿超譯）：
#   ❌ **4b 仍不做值流分析**。上面病灶的斷言側（`assertIn("tools/dev_start.py",
#      scoped)`）中 `scoped` 的 Path 血統藏在 helper method 裡，4b **抓不到它**；
#      該站點是由 4a 從產出側抓住的。兩個入口互補，但都不宣稱涵蓋「Path 血統
#      隔了任意層呼叫」的形態——那需要跨程序值流，本檔一貫不做。
#   ❌ **`PurePosixPath`／`PosixPath`／`PureWindowsPath` 產物不算違規**（顯式平台
#      語意，對齊本檔第一道判準的 `_EXPLICIT_PLATFORM` 慣例）。實掃唯一因此排除的
#      站點：`test_windowsapps_guard_bash_parity.py` 的
#      `str(PurePosixPath(rel).parent)`——恆為正斜線，本來就中立。
#   ❌ **`list.append(str(<Path>))` 不算識別鍵**（識別鍵＝下標／dict-set 鍵／`.add`）。
#      實掃全庫此形態 3 筆，皆只流向失敗訊息文字或與 `[]` 比對（`dev_start.py:812`
#      清理報告、`test_sanitize_component_frozen_sdd_versions_lock.py` 兩處、
#      `hub_sync.py:517` 鏡像檔清單），**下游無正斜線字面值斷言** ⇒ 今日無分歧，
#      故不納入以免把「顯示用字串」也一併判違規。若哪天有人拿它去比對字面值，
#      4b 會從斷言側接住（前提是 Path 血統在同句可見）。
#   ❌ **路徑建構子的引數不算「比對值」**（`Path("/nonexistent/a.png")`）。pathlib
#      會正規化輸入，那是路徑**輸入**不是平台相依**輸出**；不排除的話
#      `test_multimodal_validator.py` 的兩筆立刻變誤報（實測）。
#
# 📏 「擴到 pytest 裸 assert」的實測取捨（終審 P2 #7 指名項；此處誠實劃界）：
#   十一棵掃描根共 **9705** 個裸 `assert`。若把第三道判準（過寬近似）直接套上去，
#   命中 **41** 筆，逐筆親讀後**全部是噪音**（`/compact` slash 指令、`/T` `/F` `/PID`
#   tasklist 旗標、`/api/config/schema` URL、`/tmp/x.yaml` 從未 Path 化的假字串）
#   ⇒ 一上線就得開 41 筆白名單，鎖即淪為白名單，故**維持不擴**。
#   改以本判準的窄化條件（同句 Path 產物在場）套用裸 assert：實測命中 **0** 筆
#   ⇒ 零存量債、零誤報的擴面。**結論**：裸 assert 自此在射程內，但只在「Path 產物
#   語法可見」時；「純字面值 vs 不可見血統」的裸 assert 仍在射程外，靠
#   windows-compat-ci 兜底。宣稱到此為止，不多一分。
_PATHKEY_OK_MARKER = "path-key-ok:"
_PATH_CTORS = frozenset({"Path", "PurePath"})
_EXPLICIT_FLAVOUR_CTORS = frozenset({"PurePosixPath", "PosixPath",
                                     "PureWindowsPath", "WindowsPath"})
# 只認「唯 pathlib 才有」的屬性名，避免與一般物件的同名屬性碰撞。
_PATH_ATTRS = frozenset({
    "relative_to", "resolve", "with_suffix", "with_name", "with_stem",
    "joinpath", "expanduser", "iterdir", "rglob", "absolute",
})
# 路徑形狀字面值：至少一個 `/` 分隔的段落，各段僅 word/點/連字號；可有前導單一 `/`。
# （純 "/"、"//host" UNC、含空白的訊息文句一律不符。）
_PATH_LITERAL_RE = re.compile(r"^/?(?!/)[\w.\-]+(?:/[\w.\-]+)+$")


def _is_ctor(node: ast.AST, names: frozenset[str]) -> bool:
    return (isinstance(node, ast.Call)
            and ((isinstance(node.func, ast.Name) and node.func.id in names)
                 or (isinstance(node.func, ast.Attribute) and node.func.attr in names)))


def _is_path_expr(node: ast.AST) -> bool:
    """語法上可判定為 pathlib 產物（顯式平台 flavour 不算——見劃界）。"""
    for n in ast.walk(node):
        if _is_ctor(n, _EXPLICIT_FLAVOUR_CTORS):
            return False
        if _is_ctor(n, _PATH_CTORS):
            return True
        if isinstance(n, ast.Attribute) and n.attr in _PATH_ATTRS:
            return True
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "fspath"):
            return True
    return False


def _str_of_path(node: ast.AST) -> bool:
    """`str(<Path 產物>)` 形態。"""
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "str" and len(node.args) == 1
            and _is_path_expr(node.args[0]))


def _identity_key_positions(tree: ast.AST):
    """產出所有「被當識別鍵」的運算式節點（4a 的射程定義）。"""
    for n in ast.walk(tree):
        if isinstance(n, ast.Subscript):
            yield n.slice
        elif isinstance(n, ast.Dict):
            yield from (k for k in n.keys if k is not None)
        elif isinstance(n, ast.Set):
            yield from n.elts
        elif isinstance(n, ast.DictComp):
            yield n.key
        elif isinstance(n, ast.SetComp):
            yield n.elt
        elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
              and n.func.attr == "add" and len(n.args) == 1):
            yield n.args[0]


def _assert_payloads(tree: ast.AST):
    """產出每個斷言的「待檢運算式清單」——含 pytest 裸 assert 與 assert*() 呼叫。"""
    for n in ast.walk(tree):
        if isinstance(n, ast.Assert):
            yield [n.test]
        elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
              and n.func.attr.startswith("assert")):
            yield list(n.args) + [kw.value for kw in n.keywords]


def _literals_vs_path_expr(roots: list[ast.AST]) -> list[ast.Constant]:
    """該斷言若同時有「路徑形狀字面值」與「Path 產物」，回傳前者；否則空。"""
    lits: list[ast.Constant] = []
    pathy = False
    stack: list[ast.AST] = list(roots)
    while stack:
        node = stack.pop()
        if isinstance(node, ast.JoinedStr):  # f-string 訊息片段不算字面值（沿用慣例）
            continue
        if _is_ctor(node, _PATH_CTORS | _EXPLICIT_FLAVOUR_CTORS):
            pathy = pathy or _is_ctor(node, _PATH_CTORS)
            stack.extend(kw.value for kw in node.keywords)  # 建構子引數＝輸入，不算比對值
            continue
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and _PATH_LITERAL_RE.match(node.value)):
            lits.append(node)
            continue
        if _is_path_expr(node):
            pathy = True
        stack.extend(ast.iter_child_nodes(node))
    return lits if pathy else []


def _pathkey_markers(source: str) -> dict[int, str]:
    """{行號: WHY}——僅認 COMMENT token（對齊本檔其他判準）。"""
    markers: dict[int, str] = {}
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT and _PATHKEY_OK_MARKER in tok.string:
            markers[tok.start[0]] = tok.string.split(_PATHKEY_OK_MARKER, 1)[1].strip()
    return markers


def scan_path_str_identity(source: str, rel: str) -> tuple[list[str], list[str]]:
    """純函式核心：回傳 (offenders, stale_markers)，元素皆為 `rel:行號: 說明`。"""
    tree = ast.parse(source)  # SyntaxError 由呼叫端 fail-loud
    markers = _pathkey_markers(source)
    offenders: dict[tuple[int, int], str] = {}
    used: set[int] = set()

    def _record(node: ast.AST, msg: str) -> None:
        if markers.get(node.lineno):
            used.add(node.lineno)
            return
        offenders[(node.lineno, node.col_offset)] = f"{rel}:{node.lineno}: {msg}"

    for key in _identity_key_positions(tree):          # 4a 產出側
        if _str_of_path(key):
            _record(key, f"`{ast.unparse(key)}` 把 Path 以 str() 當識別鍵"
                         "（Windows 上鍵會是反斜線形態 ⇒ 對它的正斜線斷言在 Windows "
                         "落空／assertNotIn 恆真＝假鎖）——請改用 `.as_posix()`")
    for payload in _assert_payloads(tree):             # 4b 斷言側
        for lit in _literals_vs_path_expr(payload):
            _record(lit, f"斷言拿路徑字面值 `{lit.value}` 與同句的 Path 產物比對"
                         "（Windows 上 Path 渲染成反斜線 ⇒ 本機全綠、"
                         "windows-compat-ci 假紅）——請改用 `.as_posix()` 比對，"
                         "或把字面值換成 `str(Path(<同一常數>))`")
    stale = [
        f"{rel}:{lineno}: {_PATHKEY_OK_MARKER} 標記 stale"
        f"（{'WHY 留空' if not why else '該行無被壓下的違規'}）"
        for lineno, why in sorted(markers.items())
        if lineno not in used or not why
    ]
    return [offenders[k] for k in sorted(offenders)], stale


class TestNoPlatformDependentPathStringIdentity(unittest.TestCase):
    """Path 的平台相依字串化不得當識別鍵／比對值（見上方區段 WHY）。"""

    def test_no_platform_dependent_path_string_identity(self) -> None:
        offenders, stale, parse_failures, band = run_unit_scan(scan_path_str_identity)
        self.assertEqual(
            parse_failures, [],
            "以下 .py 無法 parse——掃描面不得靜默縮小：\n" + "\n".join(parse_failures),
        )
        self.assertEqual(
            offenders, [],
            "發現 Path 的平台相依字串化被當識別鍵／比對值（R69 P1 病灶家族）——"
            f"確屬刻意者於該行行尾加 `# {_PATHKEY_OK_MARKER} <WHY>` 豁免：\n"
            + "\n".join(offenders),
        )
        self.assertEqual(
            stale, [],
            f"{_PATHKEY_OK_MARKER} 豁免標記 stale（防清單腐化）：\n" + "\n".join(stale),
        )
        self.assertEqual(band, [], "掃描面下限帶：\n" + "\n".join(band))

    # ── 以注入 fixture 自證判準紅綠 ──────────────────────────────────────────

    def _scan(self, source: str) -> tuple[list[str], list[str]]:
        return scan_path_str_identity(source, "fixture_case.py")

    def test_injected_original_defect_shape_is_detected(self) -> None:
        """R69 P1 病灶原形態（`out[str(p.relative_to(root))] = src`）必紅。"""
        off, stale = self._scan(
            "def f(path, root, src, out):\n"
            "    out[str(path.relative_to(root))] = src\n"
        )
        self.assertEqual(len(off), 1, off)
        self.assertIn("as_posix", off[0])
        self.assertEqual(stale, [])

    def test_other_identity_key_positions_are_detected(self) -> None:
        """dict/set 字面值、推導式鍵、`.add()` 都是同一個病的入口。"""
        for src in (
            "def f(p, root):\n    d = {str(p.relative_to(root)): 1}\n",
            "def f(p, root):\n    s = {str(p.resolve())}\n",
            "def f(ps, root):\n    d = {str(p.relative_to(root)): 1 for p in ps}\n",
            "def f(ps, root, seen):\n"
            "    for p in ps:\n        seen.add(str(p.relative_to(root)))\n",
        ):
            with self.subTest(src=src):
                off, _ = self._scan(src)
                self.assertEqual(len(off), 1, off)

    def test_fixed_shape_is_accepted(self) -> None:
        """修法慣例（`.as_posix()`）必綠——否則本鎖會逼人改回舊寫法。"""
        off, stale = self._scan(
            "def f(path, root, src, out):\n"
            "    out[path.relative_to(root).as_posix()] = src\n"
        )
        self.assertEqual((off, stale), ([], []))

    def test_relative_literal_vs_path_expr_in_assert_is_detected(self) -> None:
        """4b：相對路徑字面值 vs 同句 Path 產物——第三道判準結構上抓不到的形態。"""
        src = ("class T:\n"
               "    def test_x(self, p, root):\n"
               '        self.assertEqual(str(p.relative_to(root)), "tools/dev_start.py")\n')
        off, _ = self._scan(src)
        self.assertEqual(len(off), 1, off)
        # 註：本行自身不會被本判準命中——`off[0]` 非 Path 產物，窄化條件不成立
        self.assertIn("tools/dev_start.py", off[0])
        # 交叉驗證劃界：第三道判準（要求 `/` 開頭）對同一段必然沉默——這正是本判準存在的理由
        self.assertEqual(scan_posix_abs_asserts(src, "fixture_case.py")[0], [])

    def test_bare_pytest_assert_is_in_scope(self) -> None:
        """4b **涵蓋裸 assert**（第三道判準對它劃界在外；本判準以窄化條件補上）。"""
        off, _ = self._scan(
            "def test_x(p, root):\n"
            '    assert str(p.relative_to(root)) == "tools/dev_start.py"\n'
        )
        self.assertEqual(len(off), 1, off)

    def test_explicit_flavour_and_constructor_inputs_are_not_flagged(self) -> None:
        """兩條劃界的實掃對應站點必須綠（否則本鎖一上線就是誤報）。"""
        off, _ = self._scan(
            "def f(rel, bk, tree):\n"
            "    dirs = {str(PurePosixPath(rel).parent)}\n"
            '    assert bk.extract_widget_tree(Path("/nonexistent/a.png")) is tree\n'
        )
        self.assertEqual(off, [])

    def test_non_path_literals_are_not_flagged(self) -> None:
        """無 Path 產物在場的路徑形狀字面值不在射程（避免爆量誤報）。"""
        off, _ = self._scan(
            "class T:\n"
            "    def test_x(self):\n"
            '        self.assertIn("docs/04_planning", out)\n'
            '        assert "/compact" in cmd\n'
        )
        self.assertEqual(off, [])

    def test_marker_suppresses_and_missing_violation_makes_it_stale(self) -> None:
        """豁免標記能壓下違規；標記在、違規不在（或 WHY 留空）→ stale 必紅。"""
        head = "def f(path, root, src, out):\n"
        line = "    out[str(path.relative_to(root))] = src"
        off, stale = self._scan(f"{head}{line}  # {_PATHKEY_OK_MARKER} 鍵只餵給 Windows API\n")
        self.assertEqual((off, stale), ([], []), "附 WHY 的標記應壓下違規且不判 stale")

        off, stale = self._scan(f"{head}{line}  # {_PATHKEY_OK_MARKER}\n")
        self.assertEqual(len(off), 1, "WHY 留空的標記不得生效")
        self.assertIn("WHY 留空", stale[0])

        off, stale = self._scan(f"{head}    x = 1  # {_PATHKEY_OK_MARKER} 已改用 as_posix\n")
        self.assertEqual(off, [])
        self.assertEqual(len(stale), 1, "違規已消失的標記必須被指名刪除")
        self.assertIn("該行無被壓下的違規", stale[0])

    def test_marker_inside_a_string_literal_is_not_honoured(self) -> None:
        """標記只認 COMMENT token——字串字面值裡的同形文字不得當豁免用。"""
        off, _ = self._scan(
            "def f(path, root, src, out):\n"
            f"    s = '# {_PATHKEY_OK_MARKER} 假裝豁免'\n"
            "    out[str(path.relative_to(root))] = src\n"
        )
        self.assertEqual(len(off), 1, "字串裡的標記不得生效")

    def test_detector_catches_the_pre_fix_form_of_the_real_file(self) -> None:
        """自我驗證（最重要的一支）：對**真實 P1 病灶檔的修復前形態**必須紅。

        做法沿用本檔慣例——不查 git（綁 HEAD 會在修復 commit 後反過來變紅），
        而是把現行真檔的修復行改寫回病灶寫法再餵給判準；現行真檔同時必須乾淨。
        """
        rel = "tools/tests/test_dev_start.py"
        src = (_REPO_ROOT / rel).read_text(encoding="utf-8")
        fixed_form = "out[path.relative_to(_TOOLS_DIR.parent).as_posix()] = src"
        self.assertIn(
            fixed_form, src,
            f"R69 P1 的修復形態已不在 {rel} ⇒ 本自證失去對象——該處若被重寫，"
            "請同步更新這支測試指向新的修復形態，不要直接刪掉自證",
        )
        pre_fix = src.replace(
            fixed_form, "out[str(path.relative_to(_TOOLS_DIR.parent))] = src")
        off, _ = scan_path_str_identity(pre_fix, f"{rel}@修復前重建")
        self.assertTrue(off, f"本鎖對 {rel} 修復前的 P1 病灶抓不到 ⇒ 判準空轉")
        off_now, stale_now = scan_path_str_identity(src, rel)
        self.assertEqual((off_now, stale_now), ([], []), f"{rel} 現行必須已無此病灶")


# ══════════════════════════════════════════════════════════════════════════════
# R74 — 第五道判準：平台專屬環境變數的讀取必須帶平台守衛（PKG-4 C）
# ══════════════════════════════════════════════════════════════════════════════
# WHY（本檔第五道判準；與前四道同屬「跨平台寫法」家族，故沿用本檔的掃描根／豁免／
# stale 慣例，不另開新檔——護欄層棘輪 `TestGuardLayerRatchet` 要求新鎖併入既有檔；
# 🔴 R78 ARCH-03 訂正：R74 當時它量的是檔數，R77 起改量逐檔行數的**淨額**）：
#   `DEF-101-766` 的病灶是 `WindowsAppsGuard.ps1::Resolve-NativeExecutable` **無條件**
#   照 `$env:PATHEXT` 過濾候選——PATHEXT 是 Windows-only 概念，PS Core 跑在
#   macOS/Linux 上該變數不存在、POSIX 執行檔又不帶副檔名 ⇒ 每個候選都被淘汰 ⇒
#   函式恆回 `$null` ⇒ macos-compat-ci 與 root-infra-ci(ubuntu) 必紅。
#
#   🔴 R74 要治的不是那個缺陷（R71 已修），而是**它的鎖只圈一個站點**：修復當時建的鎖
#   （`tools/tests/test_dev_start.py::TestResolveNativeExecutable*`）綁死在那一支
#   `.ps1` 的那一個函式上——換一支檔案、換一種語言（Python 的
#   `os.environ["PATHEXT"]`）寫同一個缺陷，全 repo 零掃描。這是 `DEF-101-757`／
#   `DEF-101-777` 判過的同一件事（已知的鎖射程缺口不得只以劃界結案），而本 repo 已經
#   為它付過三次代價。故本判準改成**形態掃描**：不問「哪一支檔案」，只問
#   「這一處讀 PATHEXT 的程式碼，有沒有先確認自己在 Windows 上」。
#
# 判準（逐行文字，射程含 `.py`／`.ps1`／`.psm1`／`.sh`）：
#   讀取形態＝`$env:PATHEXT`（PowerShell）／`PATHEXT` 出現在 `os.environ`、`getenv`
#   同一行（Python）／`$PATHEXT`（shell）。
#   「有守衛」＝同一個檔案內、該行**之前**出現過平台守衛述詞（見 `_PLATFORM_GUARDS`）。
#
# 🔴 刻意劃界（誠實記錄，勿超譯）：
#   ❌ **只看「之前出現過」，不做控制流分析**。靜態判不出守衛是否真的支配該行（R71 的
#      `DEF-101-766` 正是「守衛存在但排在過濾之後」）。那一半由既有的**順序鎖**
#      （`test_dev_start.py::TestResolveNativeExecutableShortCircuitOrder`）承接——
#      兩道鎖的射程刻意不同：本鎖問「有沒有」（廣、全庫），順序鎖問「排對了沒」
#      （窄、逐站點）。把兩者混成一道會兩頭都做不好。
#   ❌ **註解與 docstring 內提到 PATHEXT 不算讀取**（本 repo 有大量在地 WHY 逐字提到
#      它）。做法＝掃描前先剝行尾 `#` 之後的部分（heuristic，沿用本檔第一道判準
#      `_scan_file` 的既有取捨：不解析字串內的 `#`，代價是「字串內含 `#` 且其後才出現
#      讀取語法」會漏掃）。判準另要求出現**真正的讀取語法**，不只是出現這個字。
#   ❌ **注入／設定（`mock.patch.dict(os.environ, {"PATHEXT": …})`）不算讀取**。
#      實測本 repo 有這種站點（`tools/tests/test_bash_probe_spec_contract.py`），
#      它是在替被測碼**佈置**環境，本身不依賴本機平台。故 Python 側的形態刻意寫得窄
#      （下標／`.get`／`in`／`getenv` 四種真讀取），不用「同一行出現 os.environ」這種
#      寬判準——寬判準製造的假紅會逼下一輪的人把整條鎖關掉。
_PATHEXT_OK_MARKER = "pathext-ok:"
_PATHEXT_READ_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"\$env:PATHEXT", re.IGNORECASE),  # pathext-ok: 偵測器自己的形態表（PowerShell）
    re.compile(r"""os\.environ\[\s*["']PATHEXT"""),          # Python 下標讀取
    re.compile(r"""os\.environ\.get\(\s*["']PATHEXT"""),     # Python .get 讀取
    re.compile(r"""["']PATHEXT["']\s+in\s+os\.environ"""),   # Python 存在性判斷
    re.compile(r"""getenv\(\s*["']PATHEXT"""),               # os.getenv / C 風格
    re.compile(r"\$\{?PATHEXT\}?"),                          # POSIX shell
)
# 平台守衛述詞：出現任一即視為該檔已在判平台。刻意含 PowerShell 與 Python 兩套——
# 同一個判準要能對兩種語言說話，否則「換語言寫同一個缺陷」又是一個免費的繞道。
_PLATFORM_GUARDS: tuple[str, ...] = (
    # Python
    'os.name == "nt"', "os.name == 'nt'",
    'sys.platform == "win32"', "sys.platform == 'win32'",
    'sys.platform.startswith("win")', "sys.platform.startswith('win')",
    'platform.system() == "Windows"', "platform.system() == 'Windows'",
    "is_windows()", "IS_WINDOWS", "_is_windows",
    # PowerShell
    "$IsWindows", "$isWindowsHost", "PSVersion.Major -lt 6",
    "[System.Environment]::OSVersion", "$env:OS -eq",
    # POSIX shell
    "uname -s", "OSTYPE",
)


def _pathext_markers(source: str, *, is_python: bool) -> dict[int, str]:
    """{行號: WHY}——行尾豁免標記。

    🔴 Python 檔一律走 `tokenize`（沿用本檔前四道判準的既有慣例）：**本判準的射程含
    偵測器自己**，而偵測器的原始碼必然多處逐字提到標記字串（常數定義、docstring 說明、
    測試訊息）。純逐行文字掃描會把那些提及都當成真的豁免標記，於是每一處都被判 stale
    並要求刪除——鎖因為「說明自己」而翻紅，是最沒有說服力的一種紅（同
    `test_dev_start.py::ps_code_only` 剝行尾註解的理由）。
    `.ps1`／`.sh` 不是 Python，`tokenize` 會拋錯，故退回逐行掃描並要求標記出現在 `#`
    **之後**（那兩種語言沒有 docstring，此近似足夠）。
    """
    markers: dict[int, str] = {}
    if is_python:
        try:
            for tok in tokenize.generate_tokens(io.StringIO(source).readline):
                if tok.type == tokenize.COMMENT and _PATHEXT_OK_MARKER in tok.string:
                    markers[tok.start[0]] = tok.string.split(_PATHEXT_OK_MARKER, 1)[1].strip()
            return markers
        except (tokenize.TokenError, IndentationError, SyntaxError):
            markers.clear()  # 壞檔退回逐行，掃描面不得靜默縮小
    for lineno, line in enumerate(source.splitlines(), 1):
        head, sep, tail = line.partition("#")
        if sep and _PATHEXT_OK_MARKER in tail:
            markers[lineno] = tail.split(_PATHEXT_OK_MARKER, 1)[1].strip()
    return markers


def scan_unguarded_pathext(
    source: str, rel: str, *, is_python: bool | None = None
) -> tuple[list[str], list[str]]:
    """純函式核心：回傳 (offenders, stale_markers)，元素皆為 `rel:行號: 說明`。"""
    if is_python is None:
        is_python = rel.endswith(".py") or not rel.rpartition(".")[2]
    markers = _pathext_markers(source, is_python=is_python)
    lines = source.splitlines()
    guard_first_at: int | None = next(
        (n for n, line in enumerate(lines, 1) if any(g in line for g in _PLATFORM_GUARDS)),
        None,
    )
    offenders: list[str] = []
    used: set[int] = set()
    for lineno, line in enumerate(lines, 1):
        code = line.split("#", 1)[0]   # 剝行尾註解（heuristic，見區段劃界）
        if not any(rx.search(code) for rx in _PATHEXT_READ_RES):
            continue
        # 🔴 `used` 記在「這一行確實有讀取語法」之後、**與守衛判斷無關**：stale 的語意
        # 是「標記在、但這一行根本沒有要壓下的東西」。若把 `used` 記在守衛判斷之後，
        # 一支檔案只要在前面某處出現過守衛，其標記就會被判 stale 而要求刪除——刪掉之後
        # 那一行就只靠「檔案前面有守衛」這個寬判準撐著，鑑別力反而下降。
        if markers.get(lineno):
            used.add(lineno)
            continue
        if guard_first_at is not None and guard_first_at < lineno:
            continue
        offenders.append(
            f"{rel}:{lineno}: 讀取 PATHEXT 但該行之前全檔沒有任何平台守衛"
            f"（`{line.strip()[:70]}`）——PATHEXT 是 Windows-only 概念，POSIX 上不存在"
            "且執行檔不帶副檔名 ⇒ 依它過濾候選會把所有候選濾光（DEF-101-766 形態）"
        )
    stale = [
        f"{rel}:{lineno}: {_PATHEXT_OK_MARKER} 標記 stale"
        f"（{'WHY 留空' if not why else '該行無被壓下的違規'}）"
        for lineno, why in sorted(markers.items())
        if lineno not in used or not why
    ]
    return offenders, stale


def _pathext_scan_files() -> list[Path]:
    """全庫（**遞迴**）`.py`／`.ps1`／`.psm1`／`.sh`，排除快取／venv／版控目錄。

    射程刻意是**全庫**而不是「幾棵樹」：本判準治的正是「鎖只圈一個站點」，若又挑幾棵
    樹來圈，下一次同型缺陷只要寫在第 N+1 棵樹裡就免費過關。凍結版 v0.01~v0.29 亦在
    射程內——它們不可**修**，但若其中有未守衛的 PATHEXT 讀取，那是必須被看見的事實，
    不是可以從掃描面移除的事實（真要處置時再走 Copy-on-Evolve 例外核准）。
    """
    skip_parts = {"__pycache__", ".git", ".venv", "venv", ".pytest_cache",
                  ".ruff_cache", ".mypy_cache", "node_modules"}
    out: list[Path] = []
    for suffix in ("*.py", "*.ps1", "*.psm1", "*.sh"):
        for p in _REPO_ROOT.rglob(suffix):
            if skip_parts & set(p.parts):
                continue
            out.append(p)
    return sorted(out)


class TestPathextReadsAreePlatformGuarded(unittest.TestCase):
    """PATHEXT 讀取必須帶平台守衛（見上方區段 WHY）。"""

    def test_no_unguarded_pathext_read_in_repo(self) -> None:
        offenders: list[str] = []
        stale: list[str] = []
        scanned = 0
        for path in _pathext_scan_files():
            rel = path.relative_to(_REPO_ROOT).as_posix()
            off, st = scan_unguarded_pathext(
                path.read_text(encoding="utf-8-sig", errors="replace"), rel)
            offenders.extend(off)
            stale.extend(st)
            scanned += 1
        # 反空轉下限＝R74 實掃數打八折取整。射程若被縮小（改成幾棵樹、或漏了某個
        # 副檔名）必紅——「鎖只圈一個站點」正是本判準要治的病，不得原地復發。
        self.assertGreaterEqual(
            scanned, 1000, f"PATHEXT 掃描面只有 {scanned} 檔——射程疑似被縮小")
        self.assertEqual(
            offenders, [],
            "發現未帶平台守衛的 PATHEXT 讀取（DEF-101-766 形態；R74 把該缺陷的鎖從"
            "「一個站點」擴為全庫形態掃描）——請在讀取前先判平台，或於該行行尾加 "
            f"`# {_PATHEXT_OK_MARKER} <WHY>`：\n" + "\n".join(offenders),
        )
        self.assertEqual(
            stale, [],
            f"{_PATHEXT_OK_MARKER} 豁免標記 stale（防清單腐化）：\n" + "\n".join(stale),
        )

    # ── 以下以合成樣本自證判準紅綠（樣本只存在於字串，不留違規樣本於 repo）──

    def _scan(self, source: str) -> tuple[list[str], list[str]]:
        return scan_unguarded_pathext(source, "fixture_case")

    def test_injected_ps1_defect_shape_is_detected(self) -> None:
        """DEF-101-766 的原形態（.ps1 無條件照 PATHEXT 過濾）必紅。"""
        off, stale = self._scan(
            "function Resolve-NativeExecutable {\n"
            "  $exts = @($env:PATHEXT -split ';')\n"
            "  return $null\n"
            "}\n"
        )
        self.assertEqual(len(off), 1, off)
        self.assertEqual(stale, [])

    def test_injected_python_port_of_the_same_defect_is_detected(self) -> None:
        """🔴 換語言寫同一個缺陷也必紅——這正是「一個站點級鎖」抓不到的那條路。"""
        for sample in (
            'exts = os.environ["PATHEXT"].split(os.pathsep)\n',
            'exts = os.environ.get("PATHEXT", "").split(";")\n',
            'exts = os.getenv("PATHEXT", "").split(";")\n',
            'if "PATHEXT" in os.environ: pass\n',
        ):
            with self.subTest(sample=sample):
                off, _ = self._scan(sample)
                self.assertEqual(len(off), 1, f"{sample!r} 漏抓：{off}")

    def test_injected_shell_port_is_detected(self) -> None:
        off, _ = self._scan('echo "$PATHEXT" | tr ";" "\\n"\n')
        self.assertEqual(len(off), 1, off)

    def test_guarded_form_is_accepted(self) -> None:
        """修法慣例（先判平台）必綠——否則本鎖會逼人改回舊寫法。"""
        for sample in (
            "if (-not $isWindowsHost) { return $candidate }\n"
            "$exts = @($env:PATHEXT -split ';')\n",
            'if os.name == "nt":\n    exts = os.environ["PATHEXT"].split(";")\n',
            'if sys.platform.startswith("win"):\n'
            '    exts = os.environ.get("PATHEXT", "")\n',
        ):
            with self.subTest(sample=sample):
                off, stale = self._scan(sample)
                self.assertEqual((off, stale), ([], []), f"{sample!r} 誤報")

    def test_guard_after_the_read_does_not_count(self) -> None:
        """守衛排在讀取**之後**不算——順序反了等於沒守（與 DEF-101-766 同型）。"""
        off, _ = self._scan(
            "$exts = @($env:PATHEXT -split ';')\n"
            "if (-not $isWindowsHost) { return $candidate }\n"
        )
        self.assertEqual(len(off), 1, off)

    def test_mentioning_pathext_in_prose_is_not_flagged(self) -> None:
        """對照組：註解／docstring 提到 PATHEXT 不算讀取（本 repo 有大量在地 WHY）。"""
        off, _ = self._scan(
            "# PATHEXT 是 Windows-only 概念，POSIX 上不存在\n"
            '"""這個函式不再依 PATHEXT 過濾候選。"""\n'
        )
        self.assertEqual(off, [])

    def test_marker_suppresses_and_missing_violation_makes_it_stale(self) -> None:
        """豁免標記能壓下違規；標記在、違規不在（或 WHY 留空）→ stale 必紅。"""
        off, stale = self._scan(
            f'exts = os.environ["PATHEXT"]  # {_PATHEXT_OK_MARKER} 僅供 Windows 分支使用\n')
        self.assertEqual((off, stale), ([], []))

        off, stale = self._scan(f'exts = os.environ["PATHEXT"]  # {_PATHEXT_OK_MARKER}\n')
        self.assertEqual(len(off), 1, "WHY 留空的標記不得生效")
        self.assertEqual(len(stale), 1, stale)

        off, stale = self._scan(f"x = 1  # {_PATHEXT_OK_MARKER} 已改走平台守衛\n")
        self.assertEqual(off, [])
        self.assertEqual(len(stale), 1, "違規已消失的標記必須被指名刪除")

    def test_detector_catches_the_pre_fix_form_of_the_real_guard_ps1(self) -> None:
        """自我驗證（最重要的一支）：對**真實病灶檔的修復前形態**必須紅。

        沿用本檔慣例——不查 git（綁 HEAD 會在修復 commit 後反過來變紅），而是把現行
        真檔的短路整段移除再餵給判準；現行真檔同時必須乾淨，兩個方向一起鎖。
        """
        rel = "tools/lib/WindowsAppsGuard.ps1"
        src = (_REPO_ROOT / rel).read_text(encoding="utf-8-sig")
        guard_line = "if (-not $isWindowsHost)"
        self.assertIn(
            guard_line, src,
            f"{rel} 內找不到非 Windows 短路 `{guard_line}` ⇒ 本自證失去對象——"
            "該處若被重寫，請同步更新這支測試指向新的守衛形態，不要直接刪掉自證",
        )
        pre_fix = "\n".join(
            line for line in src.splitlines()
            if not any(g in line for g in _PLATFORM_GUARDS)
        )
        off, _ = scan_unguarded_pathext(pre_fix, f"{rel}@修復前重建")
        self.assertTrue(off, f"本鎖對 {rel} 修復前的病灶抓不到 ⇒ 判準空轉")
        off_now, stale_now = scan_unguarded_pathext(src, rel)
        self.assertEqual((off_now, stale_now), ([], []), f"{rel} 現行必須已無此病灶")


# ══════════════════════════════════════════════════════════════════════════════
# R74 — 第六道判準：平台專屬 skip 的**方向**與**標籤對稱性**（PKG-4 D‧E‧F）
# ══════════════════════════════════════════════════════════════════════════════
# WHY 放在本檔（不另開新檔，沿用本檔「跨平台寫法家族」的收納契約）：判準本體住在
# `tools/lib/windows_skip_tags.py`（供 `tools/run_root_unittests.py` 在閘門上消費
# rc），本節是它的**單元測試**——證明四格方向表算得對、證明 pytest 形態真的在射程內、
# 證明反方向棘輪不是空轉。沒有這一節，那些判準只有「repo 現況是綠的」這一個證據，
# 而綠可能只是因為它什麼都沒看見（本 repo 已有三次同型前例）。
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
import windows_skip_tags as _wst  # noqa: E402


class TestSkipDirectionAndTagSymmetry(unittest.TestCase):
    """skip 方向判準的四格與雙向標籤（`windows_skip_tags`）。"""

    def _sites(self, src: str) -> list[_wst.SkipSite]:
        return _wst.skip_decorator_sites({"fixture_case.py": src})

    def test_pytest_skipif_form_is_in_scope(self) -> None:
        """🔴 PKG-4 D 的核心：同一個缺陷改寫成 pytest 形態必須仍被看見。

        意圖（Rule 9）：R72 的方向判準只走 `unittest` 的 decorator 且只讀位置引數的
        reason，於是每一個 `@pytest.mark.skipif(cond, reason=...)` 站點在抽取階段就被
        整個丟掉——連「未登記述詞」那道 fail-open 守衛都看不到它。一道只認一種測試
        框架的判準，對「換框架寫同一個缺陷」零防護。
        """
        sites = self._sites(
            "import pytest, sys\n"
            '@pytest.mark.skipif(sys.platform != "win32", reason="需要 Windows")\n'
            "def test_x(): pass\n"
        )
        self.assertEqual(len(sites), 1, sites)
        self.assertEqual(sites[0].decorator, "skipif")
        self.assertEqual(sites[0].reason, "需要 Windows")
        self.assertEqual(
            _wst.skipped_platform(sites[0]), "non-windows",
            "pytest 形態的方向判錯——`skipif(sys.platform != \"win32\")` 是在**非** "
            "Windows 上 skip（Windows 專屬測試）",
        )

    def test_module_level_pytestmark_and_alias_are_in_scope(self) -> None:
        """模組級 `pytestmark` 與「先存成常數再當 decorator」兩種寫法都在射程內。

        意圖：這兩種寫法的**射程比 decorator 大**（前者整檔 skip），漏掉它們等於在
        覆蓋面最大的那一種寫法上失明。本 repo 兩種都真的在用。
        """
        sites = self._sites(
            "import pytest, sys\n"
            'pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX 專屬")\n'
            '_ALIAS = pytest.mark.skipif(sys.platform != "win32", reason="Windows 專屬")\n'
        )
        by_target = {s.target: s for s in sites}
        self.assertEqual(sorted(by_target), ["_ALIAS", "pytestmark"], sites)
        self.assertEqual(_wst.skipped_platform(by_target["pytestmark"]), "windows")
        self.assertEqual(_wst.skipped_platform(by_target["_ALIAS"]), "non-windows")

    def test_direction_table_covers_all_four_cells(self) -> None:
        """四格方向表逐格斷言（極性 × 述詞在 Windows 上的值）。

        意圖：R72 只有一格（`skipUnless` × Windows 述詞），其餘三格靜默判不出方向。
        任何人把某一格拿掉，本支當場紅。
        """
        cases = {
            ('skipIf', 'os.name == "nt"'): "windows",
            ('skipIf', 'os.name != "nt"'): "non-windows",
            ('skipUnless', 'os.name == "nt"'): "non-windows",
            ('skipUnless', 'os.name != "nt"'): "windows",
        }
        for (deco, cond), want in cases.items():
            site = _wst.SkipSite("f.py", 1, "t", deco, cond, "r")
            with self.subTest(deco=deco, cond=cond):
                self.assertEqual(_wst.skipped_platform(site), want)

    def test_negated_predicate_does_not_invert_the_direction(self) -> None:
        """🔴 `not <Windows 述詞>` 不得被判成 Windows 述詞（R74 落地時實測的方向反轉）。

        意圖：兩極模型只問「條件文字裡有沒有 Windows 述詞」，於是
        `skipif(not _windows_pwsh_available())` 被判成「Windows 上會 skip」，而它的
        語意恰恰相反。**方向算反比判不出方向更糟**——它會要求作者貼上錯的標籤。
        """
        site = _wst.SkipSite("f.py", 1, "t", "skipif", "not _windows_pwsh_available()", "r")
        self.assertEqual(_wst.skipped_platform(site), "non-windows")
        self.assertEqual(
            _wst.skipped_platform(
                _wst.SkipSite("f.py", 1, "t", "skipif", "_windows_pwsh_available()", "r")),
            "windows",
        )

    def test_untagged_non_windows_side_is_reported(self) -> None:
        """反方向（POSIX 側）漏標必須被回報，且兩種標籤都算已標籤。"""
        src = (
            "import unittest, os, sys\n"
            '@unittest.skipIf(os.name == "nt", "POSIX 專屬")\n'
            "def test_a(): pass\n"
            f'@unittest.skipIf(os.name == "nt", "{_wst.POSIX_NATIVE_SKIP_TAG} POSIX 專屬")\n'
            "def test_b(): pass\n"
            f'@unittest.skipUnless(sys.platform == "darwin", "{_wst.MAC_NATIVE_SKIP_TAG} mac")\n'
            "def test_c(): pass\n"
        )
        offenders = _wst.untagged_non_windows_skip_decorators({"fixture_case.py": src})
        self.assertEqual(
            [label for label, _ in offenders], ["fixture_case.py:2 test_a"],
            f"反方向漏標判準不對（實得 {offenders!r}）——已帶 POSIX／MAC 標籤者不得再被點名",
        )

    def test_ratchet_flags_both_directions_of_drift(self) -> None:
        """棘輪對「新增未標籤」與「已補標未下修基線」兩向都說話（防基線腐化）。

        意圖：只擋「不得增加」的棘輪會腐化——補完標籤後基線留在舊值，鑑別力靜默歸零
        （`MIN_TESTS` 的註記逐字記載腐化 11 輪的後果）。故判準是**相等**。
        """
        baseline = dict(_wst._POSIX_TAG_RATCHET)
        self.assertEqual(
            _wst.posix_tag_ratchet_problems(baseline), [],
            "基線自己對自己都不相等——表壞了",
        )
        tree = next(iter(baseline))
        worse = {**baseline, tree: baseline[tree] + 1}
        self.assertTrue(_wst.posix_tag_ratchet_problems(worse), "新增未標籤站點沒被擋下")
        # 🔴 R79：「已補標未下修」這一向必須挑一個**基線 > 0** 的樹來扣。原本寫的是
        # `next(iter(baseline))` 再 `max(0, v - 1)`——當第一格剛好是 0 時，扣完等於沒扣，
        # 這半題結構上恆綠。它在 R79 當回合真的發生了：另一個包把 `tools/tests` 由 1
        # 下修為 0（一個正確的動作），這支鎖的鑑別力就在別人還債的那一刻靜默歸零。
        # 判準因此不再依賴「哪一格排第一」這種偶然事實。
        payable = [t for t, v in baseline.items() if v > 0]
        self.assertTrue(
            payable,
            "基線全格為 0 ⇒ 「已補標未下修」這一向無從施測。欠債真的清乾淨是好事，"
            "但這支鎖必須改成別的施測法（例如整格移除），不得留一題恆綠的斷言",
        )
        better = {**baseline, payable[0]: baseline[payable[0]] - 1}
        self.assertTrue(
            _wst.posix_tag_ratchet_problems(better),
            "補標後基線未下修卻放行——棘輪會就地腐化",
        )
        self.assertTrue(
            _wst.posix_tag_ratchet_problems({}), "掃描面整組消失竟放行——fail-open")

    # ══════════════════════════════════════════════════════════════════════════
    # R75：SD 追加①（複合布林方向）＋ QA-R74-02（63 筆對所有機械物隱形）的注入式鎖
    # ══════════════════════════════════════════════════════════════════════════

    def test_composite_boolean_condition_is_evaluated_not_guessed(self) -> None:
        """🔴 SD 追加①：複合布林條件不得以「字串比對挑一個 marker」猜方向。

        意圖（Rule 9）：R74 的判準是「依 marker 長度遞減排序取第一個命中」，於是
        `skipIf(sys.platform == 'win32' or sys.platform == 'darwin')` 取到較長的
        `darwin`（24 字 > 23 字）⇒ 判成 `non-windows`，而它**實際在 Windows 上會 skip**。
        方向算反正是該檔自承「比判不出方向更糟」的形態（它會要求作者貼上錯的標籤）。
        修法是真值運算（`or`／`and`／`not` 逐層求值），故本支逐格斷言真值表——包含
        「一個葉判得出、另一個判不出」的短路情形，那是純字串比對絕對做不到的。
        """
        cases = {
            "sys.platform == 'win32' or sys.platform == 'darwin'": True,
            "sys.platform == 'win32' and sys.platform != 'darwin'": True,
            "not (sys.platform == 'win32' or sys.platform == 'darwin')": False,
            "os.name == 'nt' or _brand_new_probe()": True,       # True or 未知 == True
            "os.name != 'nt' and _brand_new_probe()": False,     # False and 未知 == False
            "_brand_new_probe() or _other()": None,              # 兩葉皆未知 ⇒ 不猜
            "os.name == 'nt' and _brand_new_probe()": None,      # True and 未知 ⇒ 不猜
        }
        for cond, want in cases.items():
            with self.subTest(cond=cond):
                self.assertIs(
                    _wst._predicate_value_on_windows(cond), want,
                    f"{cond!r} 在 Windows 上的值應為 {want}",
                )
        # 端到端：SD 舉的那一筆必須歸到 `posix-only`（Windows 上會 skip），而不是反方向。
        site = _wst.SkipSite(
            "f.py", 1, "t", "skipIf", "sys.platform == 'win32' or sys.platform == 'darwin'", "r")
        self.assertEqual(_wst.skipped_platform(site), "windows")
        self.assertEqual(_wst.site_class(site), "posix-only")

    def test_every_site_lands_in_exactly_one_census_class(self) -> None:
        """🔴 QA-R74-02：每個站點都必須落在某一格 ⇒ 沒有站點能對所有機械物隱形。

        意圖：修前三棵活測試樹共 103 個 decorator 站點、其中 63 筆（61%）方向判不出來，
        而 docstring 宣稱承接它們的收口網對這 63 筆命中 0 ⇒ 兩道方向判準與收口網**全部
        看不到**。本支鎖「分類是全覆蓋的」：站點總數 ＝ 各類別數字之和，且
        `unclassified` 有明細可查。
        """
        src = (
            "import os, shutil, sys, unittest, pytest\n"
            '@unittest.skipUnless(os.name == "nt", "Windows 專屬")\n'
            "def test_a(): pass\n"
            '@unittest.skipIf(os.name == "nt", "POSIX 專屬")\n'
            "def test_b(): pass\n"
            '@unittest.skipUnless(shutil.which("git"), "需 git")\n'
            "def test_c(): pass\n"
            '@unittest.skipUnless(_BASH, "需 bash")\n'
            "def test_d(): pass\n"
            "class T(unittest.TestCase):\n"
            "    def test_e(self):\n"
            '        self.skipTest("函式體內 skip")\n'
        )
        sources = {"fixture_case.py": src}
        counts = _wst.site_class_counts(sources)
        self.assertEqual(
            counts,
            {"windows-only": 1, "posix-only": 1, "tool-absence": 2,
             "runtime-skipTest": 1, "unclassified": 0},
            f"分類全覆蓋性壞了（實得 {counts}）",
        )
        self.assertEqual(
            sum(counts.values()), len(_wst.skip_decorator_sites(sources)),
            "各類別之和 ≠ 站點總數 ⇒ 有站點沒被歸類（那就是隱形）",
        )

    def test_runtime_skiptest_form_is_in_scope(self) -> None:
        """🔴 QA-R74-02 第 3 點：函式體內的 `self.skipTest()` 此前完全在射程外。

        意圖：`_SKIP_CALL_SKIPS_WHEN_TRUE` 只認 decorator，於是「把條件寫在 `if` 裡再
        `self.skipTest(...)`」這種寫法連站點都抽不到（R75 實測 `tools/tests/` 有 10 筆）。
        它們沒有條件引數、方向天生判不出來——但「判不出來」不等於「可以隱形」。
        """
        sites = self._sites(
            "import unittest\n"
            "class T(unittest.TestCase):\n"
            "    def test_x(self):\n"
            "        if not _HAS_TOOL:\n"
            '            self.skipTest("缺工具")\n'
        )
        self.assertEqual(len(sites), 1, sites)
        self.assertEqual(sites[0].decorator, "skipTest")
        self.assertEqual(sites[0].reason, "缺工具")
        self.assertEqual(sites[0].target, "test_x", "必須點名到那支測試")
        self.assertEqual(_wst.site_class(sites[0]), "runtime-skipTest")

    def test_unregistered_predicate_is_judged_per_leaf_not_whole_condition(self) -> None:
        """🔴 逐葉判「未登記」，不看整條條件（R75 落地時實測到假紅）。

        意圖：`os.name == "nt" and _real_pwsh7() is not None` 整條含 `nt` 字樣、整條方向
        判不出來，於是「整條」版判準把它報成「未登記的 Windows 述詞」——可它的兩個葉一個
        已登記、一個根本不像 Windows，**沒有任何述詞需要登記**，訊息給的修法是空的。
        逐葉之後假紅歸零，而真正的漏登記仍抓得到（下半段）。
        """
        self.assertEqual(
            _wst.suspect_unregistered_leaves('os.name == "nt" and _real_pwsh7() is not None'),
            [], "已登記葉 ＋ 非 Windows 葉的組合不得被報成漏登記",
        )
        self.assertEqual(
            _wst.suspect_unregistered_leaves("_brand_new_windows_probe()"),
            ["_brand_new_windows_probe()"], "真正的漏登記必須抓到",
        )
        # 端到端：前者歸 tool-absence（可見、可記帳），後者歸 unclassified（逐筆點名）。
        ok = _wst.SkipSite("f.py", 1, "t", "skipUnless",
                           'os.name == "nt" and _real_pwsh7() is not None', "r")
        bad = _wst.SkipSite("f.py", 2, "t", "skipUnless", "_brand_new_windows_probe()", "r")
        self.assertEqual(_wst.site_class(ok), "tool-absence")
        self.assertEqual(_wst.site_class(bad), "unclassified")

    def test_tree_floor_ratchet_flags_both_shrinkage_and_staleness(self) -> None:
        """🔴 SD 追加②要的**防腐機制**：下限過期本身必須是一筆 problem。

        意圖：下限只擋「縮面」時會單向腐化——樹長大、下限不動，鑑別力靜默歸零而沒有任何
        東西會說話（`MIN_TESTS` 腐化 11 輪就是這麼發生的）。下限的語意既然是「實測的
        八成」，那 `floor < actual × 0.8` 就該紅。
        """
        floors = dict(_wst._TREE_FILE_FLOORS)
        tree, floor = next(iter(floors.items()))
        # 對照組：實測恰為 floor/0.8 ⇒ 合格（下限剛好在設計比例上）。
        exact = int(floor / _wst.TREE_FLOOR_RATIO)
        self.assertEqual(
            _wst.tree_floor_problems({t: int(f / _wst.TREE_FLOOR_RATIO)
                                      for t, f in floors.items()}), [],
            "下限恰在設計比例上竟被判違規",
        )
        self.assertTrue(
            _wst.tree_floor_problems({**floors, tree: floor - 1}),
            "掃描面縮到下限以下沒被擋（原本就該有的那一向）",
        )
        stale = {t: int(f / _wst.TREE_FLOOR_RATIO) for t, f in floors.items()}
        stale[tree] = exact * 3
        problems = _wst.tree_floor_problems(stale)
        self.assertTrue(problems, "樹長大三倍、下限不動竟放行 ⇒ 下限會就地腐化")
        self.assertTrue(
            any("已過期" in p and tree in p for p in problems),
            f"訊息未指出是哪一棵樹的下限過期：{problems}",
        )
        self.assertTrue(_wst.tree_floor_problems({}), "掃描面整組消失竟放行——fail-open")

    def test_census_ratchet_flags_drift_in_both_directions(self) -> None:
        """普查棘輪對「新增」與「收斂後未下修」兩向都說話（同 `_POSIX_TAG_RATCHET` 政策）。"""
        baseline = {t: dict(c) for t, c in _wst._SITE_CLASS_CENSUS.items()}
        self.assertEqual(
            _wst.site_class_census_problems(baseline), [], "基線自己對自己不相等——表壞了")
        tree = next(iter(baseline))
        worse = {**baseline, tree: {**baseline[tree], "unclassified": 1}}
        better = {**baseline, tree: {**baseline[tree],
                                     "tool-absence": baseline[tree]["tool-absence"] - 1}}
        self.assertTrue(_wst.site_class_census_problems(worse), "新增 unclassified 沒被擋")
        self.assertTrue(
            _wst.site_class_census_problems(better), "收斂後未下修基線卻放行——會就地腐化")
        self.assertTrue(_wst.site_class_census_problems({}), "掃描面消失竟放行——fail-open")

    def test_scan_surface_spans_the_live_test_trees(self) -> None:
        """🔴 PKG-4 D 的射程面：判準必須看到全部活測試樹，不是只有一棵。

        意圖：R72 的射程只有 `tools/tests/`（實測 53 支檔），而 repo 活測試檔共 337 支
        ⇒ 84% 不在任何方向判準的射程內。射程若被縮回一棵樹，本支當場紅。
        本輪第四棵＝LATEST 版 `tools/fsm_runtime/tests`（此前整棵零覆蓋，該樹的 4 個
        skip 站點對所有機械物隱形）；版本目錄名以「LATEST」正規化，升版不失效。
        """
        latest_name = _latest_root().name
        trees = _wst.scan_tree_sources(_REPO_ROOT, _TESTS_DIR, "test_*.py")
        self.assertEqual(
            sorted(t.replace(latest_name, "LATEST") for t in trees),
            ["AISDLC_SDD/LATEST/tools/fsm_runtime/tests",
             "AISDLC_SDD/scripts/tests", "AutoClaude/tests", "tools/tests"],
            f"掃描面的樹清單不對（實得 {sorted(trees)}）",
        )
        for tree, sources in trees.items():
            floor = _wst._TREE_FILE_FLOORS[tree]
            self.assertGreaterEqual(
                len(sources), floor,
                f"{tree} 掃到 {len(sources)} 支 < 下限 {floor}——該樹掃描面疑似縮小",
            )


# ══════════════════════════════════════════════════════════════════════════════
# R76 — 第七道判準：文字讀寫必須指名 encoding（PKG-E 標的三；R76-09）
# ══════════════════════════════════════════════════════════════════════════════
# WHY（沿用本檔的掃描根／標記／stale 慣例，不另開新檔——護欄層棘輪
# `TestGuardLayerRatchet` 要求新增鎖併入既有檔；🔴 R78 ARCH-03 訂正：R76 當時它量的是
# 檔數，R77 起改量逐檔行數的**淨額**，新增檔案本身不違規）：
#   `Path.read_text()`／`write_text()`／`open()` 不帶 `encoding=` 時，用的是**本機
#   locale 預設編碼**。mac 上那是 UTF-8，所以在 mac 寫、在 mac 跑，永遠是綠的；
#   同一行程式碼在 zh-TW Windows 上是 cp950，讀到任何非 Big5 字元就 `UnicodeDecodeError`。
#   這是「mac→Windows 落差」最典型的一整類缺陷，而 R76 掃描實測它**零靜態掃描器**。
#
# 🔴 更麻煩的是它連**執行期**都看不見：根 `.claude/settings.json` 設了 `PYTHONUTF8=1`，
#   於是 agent 驅動的開發迴圈裡每一支 python 都跑在 UTF-8 模式下、這類缺陷在本機一次
#   都不會現形（而另有一道鎖在強制那個值存在）。把區分本機與雲端的變數全域正規化掉，
#   結果就是**唯一能看見它的環境被關掉了** ⇒ 只剩靜態判準這一條路。
#
# 判準（AST，非逐行文字）：
#   · `<expr>.read_text(...)`／`<expr>.write_text(...)` — 恆為文字 I/O，必須有 encoding。
#   · `open(...)`（builtin 形態）與 `<expr>.open(...)`（pathlib 形態）— mode 帶 `b`
#     即二進位，出射程；其餘要求 encoding。
#   · encoding 可以是關鍵字，也可以是**位置引數**（四種呼叫形態的位置各不相同，見
#     `_ENC_POS`）——只認關鍵字會對合法寫法製造假紅。
#   · 行尾 `<標記> <WHY>` 豁免（標記字串見 `_ENCODING_OK_MARKER`）＋ stale 自檢：
#     標記在而違規不在（或 WHY 留空）即紅，防清單腐化。
#
# 🔴 刻意劃界（誠實記錄，勿超譯）：
#   ❌ **mode 是非字面值運算式時出射程**（`open(p, mode_var)`）——靜態判不出它是不是
#      二進位，硬判會製造假紅。實測本 repo 現況零此形態；這是**已知可繞道**，不是沒想到。
#   ❌ **`**kwargs` 轉發視為已帶 encoding**（同樣判不出來，且該形態通常是包裝函式）。
#   ❌ **非 pathlib 的 `.open(`**（`os.open` 連 encoding 參數都沒有、`gzip`/`tarfile`/
#      `zipfile` 預設二進位）由 `_NON_TEXT_OPEN_OWNERS` 排除。R76 落地前實測：不排除
#      的話光 `os.open` 就製造 5 筆假紅，而寬判準製造的假紅會逼下一輪把整條鎖關掉
#      （同第五道判準對 `mock.patch.dict` 的取捨）。
#   ❌ **`errors=` 不在本判準射程內**（那是另一個軸，不混進來）。
#
# 🔴 標記字串為何取專屬主題名（值見下方常數；本註解刻意不逐字寫出它——寫出來就會被
#   自己的取標記函式當成一個真標記而判 stale，同 `_encoding_markers` docstring 的理由）：
#   R76 落地首版與 `tools/tests/test_subprocess_encoding_hygiene.py`
#   的判準一 `_OK_MARKER` **逐字相同**，而兩支掃描器的掃描面是包含關係（本判準 810 檔
#   全在對方 854 檔之內）⇒ 任一方的**合法**豁免會在另一方變成一筆 `標記 stale` 紅，
#   而那筆紅的訊息還寫著「該行無被壓下的違規」（對他那一行是誤導）。兩支的錯誤訊息都
#   主動教人加這個標記，所以第一個照做的人就會踩到。這正是本輪 PKG-0 在拆的「兩道鎖的
#   合法動作互為對方違規」死結，不可在同一輪又造一個。命名比照同檔既有的
#   `_PATHEXT_OK_MARKER`／`_TMPDIR_OK_MARKER`：**每道判準取專屬主題名**。
#   另：比對改用邊界正則（同姊妹檔 `_marker_lines`），裸子字串比對是縱深防禦缺的那一層
#   ——未來若再出現含本標記為子字串的第三個標記，改名這一層就擋不住了。
_ENCODING_OK_MARKER = "file-encoding-ok:"
#: 標記比對的邊界（前面不得是字母／數字／連字號）：與姊妹檔 `_marker_lines` 同一條，
#: 讓「某標記內含另一標記」這種形態不會被互相認領。`TestEncodingMarkersDoNotCollide`
#: 常駐守著編碼家族三個豁免標記彼此不認領。
#: 🔴 本區塊的註解**刻意不逐字寫出任何一個編碼家族標記字串**（連姊妹檔的也不行）：
#:   `#` 註解是 COMMENT token，兩支掃描器的取標記函式都只認 COMMENT ⇒ 在註解裡「提到」
#:   一個標記，與「登記」一個標記在機器眼中完全同形，當場多一筆 `標記 stale` 紅。
#:   R76 首版修法就是這樣把姊妹檔弄紅的（本檔 :2047 上方已為自家標記寫過同一條理由，
#:   卻只戒了自己那一個字串）。要引述標記字串，寫進 docstring／字串字面值（STRING token）。
_ENCODING_MARKER_RE = re.compile(r"(?<![\w-])" + re.escape(_ENCODING_OK_MARKER))
_TEXT_RW_ATTRS = frozenset({"read_text", "write_text"})
#: encoding 的**位置引數**索引（呼叫形態 → 索引）。四種形態的簽名各不相同：
#: `open(file, mode, buffering, encoding)`／`Path.open(mode, buffering, encoding)`／
#: `Path.read_text(encoding, errors)`／`Path.write_text(data, encoding, errors)`。
_ENC_POS = {"open": 3, "path_open": 2, "read_text": 0, "write_text": 1}
#: mode 的位置引數索引（只有兩種 open 形態有 mode）。
_MODE_POS = {"open": 1, "path_open": 0}
_NON_TEXT_OPEN_OWNERS = frozenset({
    "os", "gzip", "bz2", "lzma", "tarfile", "zipfile", "socket", "webbrowser",
    "shelve", "dbm", "sqlite3",
})


def _encoding_markers(source: str) -> dict[int, str]:
    """{行號: WHY}——行尾豁免標記（只認 COMMENT token，理由同 `_pathext_markers`）。

    本判準的射程含偵測器自己，而偵測器原始碼必然多處逐字提到標記字串（常數、docstring、
    測試訊息）。純文字掃描會把那些提及都當成真標記並判 stale ⇒ 鎖因為「說明自己」而翻紅。
    """
    markers: dict[int, str] = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type != tokenize.COMMENT:
                continue
            found = _ENCODING_MARKER_RE.search(tok.string)
            if found:
                markers[tok.start[0]] = tok.string[found.end():].strip()
    except (tokenize.TokenError, IndentationError, SyntaxError):
        markers.clear()          # 壞檔退回空集合；掃描面本身不縮小（下方 ast.parse 亦會失敗）
    return markers


def _call_kind(call: ast.Call) -> str | None:
    """呼叫形態分類；不在射程內回 None。"""
    f = call.func
    if isinstance(f, ast.Name):
        return "open" if f.id == "open" else None
    if not isinstance(f, ast.Attribute):
        return None
    if f.attr in _TEXT_RW_ATTRS:
        return f.attr
    if f.attr != "open":
        return None
    owner = f.value
    name = owner.id if isinstance(owner, ast.Name) else (
        owner.attr if isinstance(owner, ast.Attribute) else "")
    return None if name in _NON_TEXT_OPEN_OWNERS else "path_open"


def _binary_or_unknown_mode(call: ast.Call, kind: str) -> bool:
    """mode 帶 `b`（二進位）或 mode 是非字面值（判不出來）⇒ 出射程。"""
    pos = _MODE_POS.get(kind)
    if pos is None:
        return False                       # read_text/write_text 恆為文字
    mode: ast.AST | None = None
    if len(call.args) > pos:
        mode = call.args[pos]
    for kw in call.keywords:
        if kw.arg == "mode":
            mode = kw.value
    if mode is None:
        return False                       # 省略 mode ＝ 預設 "r" ＝ 文字
    if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
        return "b" in mode.value
    return True                            # 非字面值：見上方劃界，刻意出射程


def _declares_encoding(call: ast.Call, kind: str) -> bool:
    if any(kw.arg == "encoding" for kw in call.keywords):
        return True
    if any(kw.arg is None for kw in call.keywords):
        return True                        # `**kwargs` 轉發：判不出來，見劃界
    return len(call.args) > _ENC_POS[kind]


def scan_missing_encoding(source: str, rel: str) -> tuple[list[str], list[str]]:
    """純函式核心：回傳 (offenders, stale_markers)，元素皆為 `rel:行號: 說明`。"""
    markers = _encoding_markers(source)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return [], []
    offenders: list[str] = []
    used: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        kind = _call_kind(node)
        if kind is None or _binary_or_unknown_mode(node, kind) or _declares_encoding(node, kind):
            continue
        # `used` 記在「這一行確實有違規」之後（同第五道判準的 WHY）：stale 的語意是
        # 「標記在、但這一行根本沒有要壓下的東西」。
        if markers.get(node.lineno):
            used.add(node.lineno)
            continue
        shown = "open()" if kind in ("open", "path_open") else f".{kind}()"
        offenders.append(
            f"{rel}:{node.lineno}: {shown} 未指名 encoding ⇒ 用本機 locale 預設編碼"
            "（mac=UTF-8 恆綠／zh-TW Windows=cp950，讀到非 Big5 字元即 UnicodeDecodeError）"
        )
    stale = [
        f"{rel}:{lineno}: {_ENCODING_OK_MARKER} 標記 stale"
        f"（{'WHY 留空' if not why else '該行無被壓下的違規'}）"
        for lineno, why in sorted(markers.items())
        if lineno not in used or not why
    ]
    return offenders, stale


def _encoding_scan_files() -> list[Path]:
    """射程＝本檔共用的 `_scan_units()`（測試樹 ＋ 生產碼樹 ＋ 零散單檔）。

    刻意**共用**同一組掃描單位而不另列一份：兩份清單就是兩個會漂移的真相，而
    `_scan_units()` 已有逐單位檔數的雙邊帶在守「靜默縮面」與「下限自己過期」。
    """
    out: list[Path] = []
    for _label, files, _floor in _scan_units():
        out.extend(files)
    return sorted(set(out))


#: 🔴 **shrink-only 存量棘輪 — 承接輪次＝下一輪**（帳本 `DEF-101-845`；此處刻意**不寫死輪號**
#: ——寫死會在下一輪開始時當場過期，而且會被 `TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound`
#: 判成「程式碼自稱的輪號超前帳本當前輪」。落地當下的所有權只到本檔＋另四支，
#: 下列每一支都在別的包手上，當輪修改必然互踩）。語意與 `_POSIX_TAG_RATCHET` 同族：
#:   · 任何一支的違規數**變多**、或出現不在表上的檔 ⇒ 紅（新缺陷不得混進存量）。
#:   · 任何一支**變少**（含修光）⇒ 也紅，訊息會指名要把本表下修——**只准往下改**。
#: 這不是「凍結成永遠綠」：兩個方向都會響，而且表一空掉這道鎖就升級為零容忍。
#: 承接動作：逐支補 `encoding="utf-8"`（讀 `.md`／log 一律 UTF-8），每修好一支就把
#: 該列從本表刪掉；全部清空後把本表留成空 dict（空 dict ＝ 零容忍，不要連常數一起刪）。
#: 🔴 **本表釘的是「每支檔幾筆」而不是行號**：R76 落地當回合實測，並行包在 `test_perception.py`
#: 上游插了幾行、違規行號由 434 漂到 437 而筆數不變——釘行號的表會在別人動別的東西時假紅。
#: 🔴 **收輪時看到本鎖紅、訊息說「請把棘輪同步下修」＝正常且正確**（不是本包留下的破口）：
#: R76 是多包並行輪，別的包順手補了 `encoding=` 就會讓某一列變小（落地當回合就發生過一次：
#: `tools/tests/test_doc_loc_baseline_freshness_r60.py` 由 1 → 0，該列已據實移除）。照訊息
#: 印出的實得值下修即可，**不要**改成 `<=` 之類的單邊判準——那正是「凍結成永遠綠」的入口。
_ENCODING_DEBT_RATCHET: dict[str, int] = {
    "AutoClaude/tests/test_evaluator_kill_tree.py": 2,
    "AutoClaude/tests/test_perception.py": 4,
    "AutoClaude/tests/tools/test_run_act_core.py": 3,
}


class TestTextIoDeclaresEncoding(unittest.TestCase):
    """文字讀寫必須指名 encoding（見上方區段 WHY）。"""

    @staticmethod
    def _scan_repo() -> tuple[dict[str, int], list[str], list[str], int]:
        per_file: dict[str, int] = {}
        stale: list[str] = []
        detail: list[str] = []
        scanned = 0
        for path in _encoding_scan_files():
            rel = path.relative_to(_REPO_ROOT).as_posix()
            off, st = scan_missing_encoding(
                path.read_text(encoding="utf-8-sig", errors="replace"), rel)
            if off:
                per_file[rel] = len(off)
                detail.extend(off)
            stale.extend(st)
            scanned += 1
        return per_file, stale, detail, scanned

    def test_debt_ratchet_is_exact_and_shrink_only(self) -> None:
        per_file, stale, detail, scanned = self._scan_repo()
        # 反空轉下限＝落地當回合實測 × 0.95（本輪由「打八折的化石 648」重釘），
        # 並套與各掃描單位同一條腐化上界——單邊下限必然腐化，見 `_scan_roots` WHY。
        surface = tree_count_verdict("encoding 掃描面", scanned, 812)
        self.assertIsNone(surface, surface or "")
        self.assertEqual(
            stale, [],
            f"{_ENCODING_OK_MARKER} 豁免標記 stale（防清單腐化）：\n" + "\n".join(stale))
        grew = {
            rel: (n, _ENCODING_DEBT_RATCHET.get(rel, 0))
            for rel, n in sorted(per_file.items())
            if n > _ENCODING_DEBT_RATCHET.get(rel, 0)
        }
        self.assertEqual(
            grew, {},
            "新增（或增加）未指名 encoding 的文字讀寫——**不得調高棘輪**，請補上 "
            f"`encoding=\"utf-8\"`，或於該行行尾加標記（`{_ENCODING_OK_MARKER}` ＋ WHY）：\n"
            + "\n".join(detail),
        )
        shrank = {
            rel: (per_file.get(rel, 0), frozen)
            for rel, frozen in sorted(_ENCODING_DEBT_RATCHET.items())
            if per_file.get(rel, 0) < frozen
        }
        self.assertEqual(
            shrank, {},
            "存量已被修掉（實得, 棘輪）如上 ⇒ 請把 `_ENCODING_DEBT_RATCHET` 同步下修。"
            "棘輪只准往下改；不下修的話下一次退化會被舊值遮住",
        )

    # ── 以下以合成樣本自證判準紅綠（樣本只存在於字串，不留違規樣本於 repo）──

    def _scan(self, source: str) -> tuple[list[str], list[str]]:
        return scan_missing_encoding(source, "fixture_case")

    def test_injected_missing_encoding_shapes_are_detected(self) -> None:
        """三種文字 I/O 形態各自漏 encoding 都必紅。"""
        for sample in (
            "text = path.read_text()\n",
            'path.write_text("x")\n',
            'with open(path) as fh:\n    pass\n',
            'with path.open("w") as fh:\n    pass\n',
        ):
            with self.subTest(sample=sample):
                off, _ = self._scan(sample)
                self.assertEqual(len(off), 1, f"{sample!r} 漏抓：{off}")

    def test_declared_encoding_is_accepted(self) -> None:
        """修法慣例必綠——否則本鎖會逼人改回舊寫法。關鍵字與位置引數兩種都要接受。"""
        for sample in (
            'text = path.read_text(encoding="utf-8")\n',
            'text = path.read_text("utf-8")\n',
            'path.write_text("x", encoding="utf-8")\n',
            'path.write_text("x", "utf-8")\n',
            'with open(path, "r", encoding="utf-8") as fh:\n    pass\n',
            'with path.open("w", encoding="utf-8") as fh:\n    pass\n',
            "def wrap(p, **kw):\n    return p.read_text(**kw)\n",
        ):
            with self.subTest(sample=sample):
                off, stale = self._scan(sample)
                self.assertEqual((off, stale), ([], []), f"{sample!r} 誤報")

    def test_binary_and_non_pathlib_open_are_out_of_scope(self) -> None:
        """對照組：二進位模式與 `os.open` 等非文字 I/O 不得誤報（假紅會逼人關掉整條鎖）。"""
        for sample in (
            'with path.open("rb") as fh:\n    pass\n',
            'with open(path, "wb") as fh:\n    pass\n',
            'fd = os.open(path, os.O_RDONLY)\n',
            'with gzip.open(path) as fh:\n    pass\n',
            "data = path.read_bytes()\n",
            "path.write_bytes(b'x')\n",
            "with open(path, mode_var) as fh:\n    pass\n",
        ):
            with self.subTest(sample=sample):
                off, _ = self._scan(sample)
                self.assertEqual(off, [], f"{sample!r} 誤報：{off}")

    def test_marker_suppresses_and_missing_violation_makes_it_stale(self) -> None:
        """豁免標記能壓下違規；標記在、違規不在（或 WHY 留空）→ stale 必紅。"""
        off, stale = self._scan(
            f'text = path.read_text()  # {_ENCODING_OK_MARKER} 讀的是自己剛寫的純 ASCII\n')
        self.assertEqual((off, stale), ([], []))

        off, stale = self._scan(f"text = path.read_text()  # {_ENCODING_OK_MARKER}\n")
        self.assertEqual(len(off), 1, "WHY 留空的標記不得生效")
        self.assertEqual(len(stale), 1, stale)

        off, stale = self._scan(f"x = 1  # {_ENCODING_OK_MARKER} 已補上 encoding\n")
        self.assertEqual(off, [])
        self.assertEqual(len(stale), 1, "違規已消失的標記必須被指名刪除")

    def test_marker_inside_a_string_literal_is_not_honoured(self) -> None:
        """字串裡出現標記字樣不算豁免（否則寫一句說明就能買到免檢）。"""
        off, _ = self._scan(
            f'MSG = "{_ENCODING_OK_MARKER} 說明文字"\ntext = path.read_text()\n')
        self.assertEqual(len(off), 1, off)

    def test_detector_catches_the_pre_fix_form_of_a_real_file(self) -> None:
        """自我驗證（最重要的一支）：對**真實檔案的修復前形態**必須紅。

        沿用本檔慣例——不查 git（綁 HEAD 會在修復 commit 後反過來變紅），而是把現行真檔
        的 `encoding=` 拿掉再餵給判準；現行真檔同時必須乾淨，兩個方向一起鎖。
        取樣 `tools/check_gha_action_versions.py`＝R76-09 點名的代表站點。
        """
        rel = "tools/check_gha_action_versions.py"
        src = (_REPO_ROOT / rel).read_text(encoding="utf-8")
        fixed_form = 'path.read_text(encoding="utf-8")'
        self.assertIn(
            fixed_form, src,
            f"{rel} 內找不到 `{fixed_form}` ⇒ 本自證失去對象——該處若被重寫，請同步更新"
            "這支測試指向新的取樣站點，不要直接刪掉自證",
        )
        pre_fix = src.replace(fixed_form, "path.read_text()")
        off, _ = scan_missing_encoding(pre_fix, f"{rel}@修復前重建")
        self.assertTrue(off, f"本鎖對 {rel} 修復前的形態抓不到 ⇒ 判準空轉")
        off_now, stale_now = scan_missing_encoding(src, rel)
        self.assertEqual((off_now, stale_now), ([], []), f"{rel} 現行必須已無此病灶")


# ══════════════════════════════════════════════════════════════════════════════
# R76 複審 ARCH-01：豁免標記**不得跨判準互相認領**（本輪自造死結的根治面）
# ══════════════════════════════════════════════════════════════════════════════
# 缺陷本體（實測重現，非理論）：新落地的 file-IO 判準，其標記字串與
# `test_subprocess_encoding_hygiene.py` 判準一的 `_OK_MARKER` **逐字相同**（值不在此
# 逐字引述，理由見 :2048 那段），而兩者掃描面是包含關係 ⇒ 一個**合法**的 subprocess
# 豁免會在 file-IO 這邊多出一筆 `標記 stale`，反向亦然。兩支的錯誤訊息都主動教人加該
# 標記，所以第一個照訊息辦事的人就會撞上一筆指著自己剛加的合法豁免的紅——正是本輪
# PKG-0 在拆的那種死結。
#
# 這道鎖守的是**根因而非個案**：全庫每一個「行尾 `<slug>-ok:` 豁免標記」常數都必須
# 是各判準專屬的，且彼此不得互相認領。姊妹檔已有一支同型鎖
# （`test_the_two_criteria_markers_do_not_claim_each_other`），但它只驗自己那兩個，
# 對**跨檔**碰撞零射程——那個縫就是這次逃出去的地方。
#: 豁免標記常數的形態：模組層 `_XXX = "<slug>-ok:"`。
_MARKER_CONST_RE = re.compile(
    r'^(_[A-Z0-9_]+)\s*(?::\s*str\s*)?=\s*"([a-z0-9][a-z0-9-]*-ok:)"\s*$', re.MULTILINE)


def collect_exemption_markers() -> dict[str, set[str]]:
    """{標記字串: {"<檔名>::<常數名>", …}}——現查 `tools/tests/*.py` 的所有豁免標記。

    現查而非寫死清單：寫死的在「新增一支掃描器」那天靜默縮面，而那正是本鎖要防的事。
    """
    found: dict[str, set[str]] = {}
    for path in sorted((_REPO_ROOT / "tools" / "tests").glob("*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for const, value in _MARKER_CONST_RE.findall(text):
            found.setdefault(value, set()).add(f"{path.name}::{const}")
    return found


class TestEncodingMarkersDoNotCollide(unittest.TestCase):
    """豁免標記彼此不得互相認領（跨判準、跨檔）。"""

    def test_no_two_files_share_the_same_marker_string(self) -> None:
        """判準是**跨檔**共用，不是「任何共用」——這條界線是實測收斂出來的。

        `test_adr_xplat001_c1c2_lock.py` 的 SC-4／SC-9 **刻意**共用同一個
        `stale-premise-ok:`（該檔 `sc9_…` 的 docstring 逐字寫「豁免沿用 SC-4 的…」，
        且死信偵測的 `consumed` 集合把它算成同一個），那是**同一位擁有者**在同一份檔裡
        自己看得到的設計；把它判紅只會是自製誤報。真正會出事的是**跨檔**：兩支互不知情
        的掃描器各有一套 stale 偵測，其中一方的合法豁免就是另一方的紅——ARCH-01 那筆
        逃出去的縫正是這一格。

        誠實劃界：同檔內共用仍可能出錯（若該檔沒把 stale 偵測接起來），本條抓不到。
        """
        markers = collect_exemption_markers()
        self.assertGreaterEqual(
            len(markers), 10,
            f"只掃到 {len(markers)} 個豁免標記常數 ⇒ 射程疑似被縮小（形態改了？）")
        shared = {
            value: sorted(sites)
            for value, sites in sorted(markers.items())
            if len({s.split("::")[0] for s in sites}) > 1
        }
        self.assertEqual(
            shared, {},
            "以下豁免標記字串被 ≥2 **支檔**的判準共用 ⇒ 其中一方的**合法**豁免會在另一方"
            "變成一筆 `標記 stale` 紅（訊息還會說「該行無被壓下的違規」，對那一行是誤導）。"
            "處置：給每道判準取專屬主題名，比照 `pathext-ok:`／`tmpdir-ok:`：\n"
            f"{shared}",
        )

    @staticmethod
    def _claims(owner: str, other: str) -> bool:
        """`owner` 的邊界正則會不會把一行合法的 `other` 豁免認領走。"""
        pattern = re.compile(r"(?<![\w-])" + re.escape(owner))
        return pattern.search(f"# {other} 某個合法 WHY") is not None

    def test_markers_do_not_claim_each_other_under_the_boundary_regex(self) -> None:
        """縱深防禦：即使字串不同，含包關係也不得讓一個標記被兩個判準認領。

        判準沿用兩支掃描器實際在用的那條邊界正則；本測試對**全庫每一對**標記檢查，
        不是只驗手上這幾個（那正是姊妹檔那支鎖的射程缺口）。

        🔴 先自證判準有鑑別力再掃 repo：現行標記形態（`<slug>-ok:`，尾端有冒號）結構上
        不可能互為前綴，所以 repo 掃描那一半**今天必然全過**。只斷言「全過」的鎖看起來
        跟一個壞掉的鎖一模一樣——故先餵一對真的會互相認領的合成標記，確認它會抓到。
        """
        self.assertTrue(
            self._claims("tmpdir-ok:", "tmpdir-ok:extra"),
            "判準對一對明顯互相認領的標記都抓不到 ⇒ 下面那半是恆真的假綠")
        self.assertFalse(
            self._claims("encoding-ok:", "child-encoding-ok:"),
            "判準把既有的合法含包關係誤判成認領 ⇒ 會對現況製造假紅")
        markers = sorted(collect_exemption_markers())
        for owner in markers:
            for other in markers:
                if other == owner:
                    continue
                with self.subTest(owner=owner, other=other):
                    self.assertFalse(
                        self._claims(owner, other),
                        f"`{owner}` 的判準會把一行合法的 `{other}` 豁免認領走 ⇒ 跨鎖假紅",
                    )

    def test_the_three_encoding_family_markers_are_mutually_exclusive(self) -> None:
        """具名回歸（ARCH-01 的原案）：三個 `*encoding-ok:` 逐一互不認領。

        直接用**本檔真正在跑的**取標記函式，不是另寫一份等價實作——後者只會證明
        我重寫的那份是對的。
        """
        subprocess_marker, child_marker = "encoding-ok:", "child-encoding-ok:"
        self.assertNotEqual(
            _ENCODING_OK_MARKER, subprocess_marker,
            "file-IO 判準與 subprocess 判準一的標記又撞回同一字串")
        for foreign in (subprocess_marker, child_marker):
            with self.subTest(foreign=foreign):
                self.assertEqual(
                    _encoding_markers(f"x = 1  # {foreign} 走系統碼頁\n"), {},
                    f"本判準把 `{foreign}` 的合法豁免認領走了")


# ══════════════════════════════════════════════════════════════════════════════
# 本輪 — 掃描面對稱鎖 ＋ 下限雙邊帶自證（缺陷本體見 `_scan_roots()` 的 ① ②）
# ══════════════════════════════════════════════════════════════════════════════
class TestScanSurfaceParityWithSisterLock(unittest.TestCase):
    """本檔與姊妹鎖的掃描面必須逐檔對得起來（擴一邊沒擴另一邊即紅）。

    WHY 這道鎖非有不可：兩支鎖各自維護一份樹清單，而「擴掃描面」是一個**逐鎖**
    發生的動作。本輪實測到的落差是 44 支 active `.py`，且缺口正好蓋住整層 hook
    ——沒有任何機械物會在落差出現的當回合說話，兩份清單只會愈走愈遠。
    判準取**集合相等**而非「本檔 ⊇ 姊妹鎖」：後者允許本檔單向長大，於是下一次
    輪到姊妹鎖漏掉東西時同樣沒人說話（單邊判準必然腐化，與下限那筆同型）。
    """

    @staticmethod
    def _sister_files() -> set[Path]:
        files: set[Path] = set()
        for root, _floor in _sister._scan_roots():
            if not root.is_dir():
                continue
            files.update(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)
        files.update(p for p in _sister._scan_single_files() if p.is_file())
        return files

    def _own_files(self) -> set[Path]:
        return {p for _label, files, _floor in _scan_units() for p in files}

    def test_the_two_locks_see_exactly_the_same_python_files(self) -> None:
        mine, sister = self._own_files(), self._sister_files()
        only_sister = sorted(p.relative_to(_REPO_ROOT).as_posix() for p in sister - mine)
        only_mine = sorted(p.relative_to(_REPO_ROOT).as_posix() for p in mine - sister)
        self.assertEqual(
            (only_sister, only_mine), ([], []),
            "兩支姊妹平台鎖的掃描面已分岔——只有一邊看得到的檔就是「同一種缺陷換棵樹"
            "寫就免費過關」的那個縫。修法＝把缺的樹補進 `_scan_roots()`／"
            "`_scan_single_files()`（兩邊都要），不要縮小另一邊來湊相等。\n"
            f"只有姊妹鎖看得到：{only_sister}\n只有本檔看得到：{only_mine}",
        )

    def test_the_surface_is_not_trivially_small(self) -> None:
        """反空轉：兩邊同時崩塌成空集合時「相等」也會成立，故另釘絕對量。"""
        verdict = tree_count_verdict("兩鎖共同掃描面", len(self._own_files()), 812)
        self.assertIsNone(verdict, verdict or "")


class TestScanRootFloorBand(unittest.TestCase):
    """下限帶的紅綠自證（雙向）＋ 每個釘下去的下限都必須對當下實測成立。"""

    def test_the_band_is_red_in_both_directions(self) -> None:
        """人為**壓低**實測值與**抬高**實測值，兩個方向都必須轉紅。

        單邊下限只在往下掉時說話——這正是本輪立案的形態（實測 `tools/tests`
        floor=10／actual=56 ⇒ 可靜默蒸發 82% 掃描面而全綠）。
        """
        floor = 53
        shrink = floor_band_problems([("tools/tests", 10, floor)])
        self.assertEqual(len(shrink), 1, "壓低實測值竟未轉紅 ⇒ 下界那一半沒有牙")
        self.assertIn("疑似縮小", shrink[0])
        rot = floor_band_problems([("tools/tests", repin_ceiling(floor) + 1, floor)])
        self.assertEqual(len(rot), 1, "抬高實測值竟未轉紅 ⇒ 上界那一半沒有牙")
        self.assertIn("腐化上界", rot[0])
        self.assertIn(str(suggested_floor(repin_ceiling(floor) + 1)), rot[0],
                      "訊息必須直接給出該重釘的數字，否則「該重釘」只是一句期許")
        inside = floor_band_problems([
            ("tools/tests", floor, floor),
            ("tools/tests", repin_ceiling(floor), floor),
            ("tools/tests", 56, floor),
        ])
        self.assertEqual(inside, [], f"帶內組合被誤判為紅：{inside}")

    def test_every_pinned_floor_is_inside_its_own_band_right_now(self) -> None:
        """設定面複本：即使正職判準因別的原因沒跑，下限本身仍被量。"""
        counts = [(label, len(files), floor) for label, files, floor in _scan_units()]
        problems = floor_band_problems(counts)
        self.assertEqual(problems, [], "\n".join(problems))

    def test_tmpdir_floors_are_inside_their_band_too(self) -> None:
        """第二道判準的掃描根用的是另一份清單，同樣受雙邊帶管轄。"""
        counts = []
        for root, recursive, floor in _tmpdir_scan_roots():
            found = root.rglob("*.py") if recursive else root.glob("*.py")
            n = len([p for p in found if "__pycache__" not in p.parts])
            counts.append((root.relative_to(_REPO_ROOT).as_posix(), n, floor))
        problems = floor_band_problems(counts)
        self.assertEqual(problems, [], "\n".join(problems))

    def test_single_file_unit_is_pinned_by_name(self) -> None:
        """零散單檔清單釘選：刪一列即該檔靜默出界（同樹清單防護語意）。"""
        latest_name = _latest_root().name
        rels = {
            f.relative_to(_REPO_ROOT).as_posix().replace(latest_name, "LATEST")
            for f in _scan_single_files()
        }
        self.assertEqual(
            rels,
            {"AISDLC_SDD/conftest.py", "AISDLC_SDD/LATEST/tools/__init__.py"},
        )
        self.assertEqual(_SINGLE_FILE_FLOOR, len(_scan_single_files()),
                         "單檔下限與清單長度脫鉤 ⇒ 刪一列不會紅")


# ══════════════════════════════════════════════════════════════════════════════
# 本輪 — 第六道判準：對面平台專屬 API 必須帶平台守衛
# ══════════════════════════════════════════════════════════════════════════════
# 缺陷本體（雙向注入實測，注入點固定為**生產碼**路徑而非測試樹，R68-34 判例）：
#   方向 mac→Windows 的 10 題語料，被本 repo 全部靜態判準攔下的是 **0 題**；
#   方向 Windows→mac 的 12 題，攔下 5 題（扣掉順帶命中只有 4 題）。也就是
#   「在 mac 上寫出只有 POSIX 成立的程式碼」這一整類，本機四關全部放行，唯一的
#   發現通道是雲端 windows-compat-ci——而雲端額度正好停擺。
#
# 判準只問兩個問題（刻意窄，寬判準製造的假紅會逼下一輪把整條鎖關掉）：
#   ① 這個 symbol 是不是單平台專屬？（下方三張白名單，**不含**跨平台但語意不同的
#      `os.chmod`／`os.stat` 那類——落地當回合實測 `os.chmod` 帶執行位的站點有 9 個
#      合法用法在 `tools/tests`，納入即上線全紅，正是本 repo 判過的「永紅的閘門會被
#      整個關掉」形態）；
#   ② 它之前有沒有平台守衛？**直接複用**第五道判準已驗紅綠的 `_PLATFORM_GUARDS`
#      與「守衛必須排在讀取之前」那條順序判準，不另立一套。
#      另接受 `hasattr(os, "<名字>")` 這種明示能力探測——那正是修法慣例，判準不能
#      反過來懲罰它。
#
# 🔴 刻意劃界（勿超譯）：判準是 **AST** 的，故註解與 docstring 內提到這些名字不算
#   使用（落地當回合先寫過一版行掃描，實測 68 筆命中裡絕大多數是 docstring 舉例）；
#   也**不做值流分析**——`getattr(os, "fork")()` 這種動態取用抓不到。
#   字面值類（`/tmp` 硬編、`"/" `串接、`.exe` 後綴假設）**不在本判準內**，理由是
#   實測存量 52 筆且多為測試 fixture 的不透明字串；它們在下方注入語料矩陣裡以
#   `caught=False` 逐題記帳，於是「還沒被守住的是哪幾類」是可查的量測值而非散文。
_XPLAT_OK_MARKER = "xplat-ok:"
#: POSIX 專屬模組（Windows 上 import 即 ModuleNotFoundError）。
_POSIX_ONLY_MODULES = frozenset({"pwd", "grp", "fcntl", "termios", "resource"})
#: Windows 專屬模組（POSIX 上 import 即 ModuleNotFoundError）。
_WINDOWS_ONLY_MODULES = frozenset({"winreg", "msvcrt", "_winapi"})
#: `os.<名字>`：POSIX 專屬（Windows 上該屬性不存在）。
_POSIX_ONLY_OS_ATTRS = frozenset({
    "fork", "forkpty", "killpg", "getuid", "geteuid", "getgid", "getegid",
    "getlogin", "setsid", "chown", "uname", "getpgid", "symlink",
})
#: `os.<名字>`：Windows 專屬。
_WINDOWS_ONLY_OS_ATTRS = frozenset({"startfile", "O_BINARY", "O_NOINHERIT"})
#: `signal.<名字>`：POSIX 專屬訊號。
_POSIX_ONLY_SIGNALS = frozenset({"SIGKILL", "SIGUSR1", "SIGUSR2", "SIGHUP", "SIGQUIT"})


def _xplat_markers(source: str) -> dict[int, str]:
    """{行號: WHY}——只認 COMMENT token（字串內同形文字不得當豁免用）。"""
    markers: dict[int, str] = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.COMMENT and _XPLAT_OK_MARKER in tok.string:
                markers[tok.start[0]] = tok.string.split(_XPLAT_OK_MARKER, 1)[1].strip()
    except (tokenize.TokenError, IndentationError, SyntaxError):
        markers.clear()
    return markers


def _capability_probed(tree: ast.AST) -> set[str]:
    """`hasattr(<任何東西>, "<名字>")` 探測過的名字＝作者已明示這是可選能力。"""
    probed: set[str] = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "hasattr" and len(node.args) == 2
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)):
            probed.add(node.args[1].value)
    return probed


def _foreign_api_uses(
    tree: ast.AST, probed: set[str]
) -> list[tuple[ast.AST, int, str, str]]:
    """(節點, 行號, 方向, 說明)——AST 上所有單平台專屬 symbol 的使用點。

    🔴 R79：回傳**節點本體**而不只行號。站點級守衛判定必須沿 AST 祖先鏈往上走；
    只有行號時，能做的最多是「整檔有沒有出現守衛字樣」那種檔案級近似——而那正是
    本輪修掉的缺陷（同一組 5 筆注入只抓到 1 筆）。
    """
    found: list[tuple[ast.AST, int, str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in _POSIX_ONLY_MODULES:
                    found.append((node, node.lineno, "POSIX-only", f"import {top}"))
                elif top in _WINDOWS_ONLY_MODULES:
                    found.append((node, node.lineno, "Windows-only", f"import {top}"))
        elif isinstance(node, ast.ImportFrom) and node.module:
            top = node.module.split(".")[0]
            if top in _POSIX_ONLY_MODULES:
                found.append((node, node.lineno, "POSIX-only", f"from {top} import …"))
            elif top in _WINDOWS_ONLY_MODULES:
                found.append((node, node.lineno, "Windows-only", f"from {top} import …"))
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            owner, attr = node.value.id, node.attr
            if attr in probed:
                continue
            if owner == "os" and attr in _POSIX_ONLY_OS_ATTRS:
                found.append((node, node.lineno, "POSIX-only", f"os.{attr}"))
            elif owner == "os" and attr in _WINDOWS_ONLY_OS_ATTRS:
                found.append((node, node.lineno, "Windows-only", f"os.{attr}"))
            elif owner == "signal" and attr in _POSIX_ONLY_SIGNALS:
                found.append((node, node.lineno, "POSIX-only", f"signal.{attr}"))
        elif isinstance(node, ast.keyword) and node.arg == "preexec_fn":
            found.append((node, node.lineno, "POSIX-only", "preexec_fn=（Windows 不支援）"))
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
              and node.func.attr in {"set_start_method", "get_context"}
              and node.args and isinstance(node.args[0], ast.Constant)
              and node.args[0].value in {"fork", "forkserver"}):
            found.append((node, node.lineno, "POSIX-only",
                          f"{node.func.attr}('{node.args[0].value}')"))
    return found


# ── 站點級守衛（R79 修 P1：檔案級＋純文字特赦的鑑別力只有 20%）─────────────────
# 舊判準：「整檔第一個含守衛字樣的**行號** < 使用點行號 ⇒ 特赦」。三個結構性後果：
#   ① 檔案級——任何一段與違規完全無關的守衛（隔壁函式、檔頭的一句 `if
#      sys.platform == "win32"`）會把它後面**整檔**的違規全部赦免；
#   ② 純文字——守衛字樣寫在字串常數或訊息裡即可開後門，而本 repo 的中文 WHY
#      大量逐字提到 `sys.platform == "win32"` 這種字樣，開後門完全不像在繞過；
#   ③ 只看「之前出現過」——連「同一個作用域」都不要求。
# 新判準只問一句：**這個使用點在語法上被平台守衛罩住了嗎**。四種罩法（皆為
# repo 內既存的真實寫法，不是發明出來的）：
#   enclosing-if       祖先鏈上有 `If`/`IfExp`/`While`，其 test 在判平台
#   early-return-guard 同一個 block 內、排在它**之前**的 `if <守衛>: … return`
#                      （`platform_caps.kill_process_tree()` 就是這個形狀）
#   guarded-decorator  所在 def/class（含**同檔基底類別**）帶平台守衛 decorator
#                      （`@unittest.skipUnless(sys.platform == "darwin", …)`）
#   try-capability     使用點在 `try:` 本體、而 handler 捕 ImportError／
#                      ModuleNotFoundError／AttributeError＝作者明示這是可選能力
# 🔴 刻意劃界：不做方向判定（`if is_windows():` 的 else 分支放 POSIX 碼是對的、
#   body 放 POSIX 碼是錯的，兩者本判準都算「有守衛」）。方向那一半屬控制流語意，
#   靜態誤判的代價是假紅，而假紅會逼下一輪把整條鎖關掉（本檔第五道判準同樣取捨）。
#: 平台守衛在 **AST** 上的形狀：只認「決定平台的**程式碼符號**」。
#: 為何不沿用 `_PLATFORM_GUARDS`（行文字 SSOT）做比對：那份清單是給**行掃描**用的，
#: 在 AST 上照用會把 `if "IS_WINDOWS" in env:`／`if "OSTYPE" in line:` 這種**字串**
#: 判成守衛——正是本輪要修的後門。兩者不得漂移這件事由
#: `test_text_guard_ssot_is_fully_recognised_by_the_ast_predicate` 機械釘住。
_PLATFORM_DECIDING_SYMBOLS: tuple[str, ...] = (
    "sys.platform", "os.name", "platform.system", "os.uname",
    "is_windows", "is_macos", "is_posix",
    "IS_WINDOWS", "IS_MACOS", "_is_windows",
)
#: `_PLATFORM_GUARDS` 內「碰巧也是合法 Python 運算式、但語意屬別的語言」的項。
#: 釘住它＝新增任何 Python 側守衛字樣而忘了教 AST 判準時，上面那支鎖會紅。
_NON_PYTHON_GUARD_TOKENS: frozenset[str] = frozenset({"uname -s", "OSTYPE"})
#: 「對面平台上這個 symbol 根本不存在」會拋的例外——捕它＝作者明示可選能力。
_CAPABILITY_EXC_NAMES: frozenset[str] = frozenset(
    {"ImportError", "ModuleNotFoundError", "AttributeError"})
_BLOCK_FIELDS: tuple[str, ...] = ("body", "orelse", "finalbody")


def _dotted_name(node: ast.AST) -> str | None:
    """`a.b.c` 形態的節點還原成字串；不是 Name/Attribute 鏈則回 None。"""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


def is_platform_guard_expr(test: ast.AST) -> bool:
    """這個運算式是不是在**判平台**？只認程式碼符號，字串／註解一律不算。"""
    for sub in ast.walk(test):
        dotted = _dotted_name(sub)
        if dotted and any(
            dotted == sym or dotted.endswith("." + sym)
            for sym in _PLATFORM_DECIDING_SYMBOLS
        ):
            return True
    return False


def _flow_terminates(stmts: list[ast.stmt]) -> bool:
    """這個 block 的尾巴有沒有把控制流帶走（早退守衛成立的前提）。"""
    if not stmts:
        return False
    last = stmts[-1]
    if isinstance(last, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
        return True
    if isinstance(last, ast.Expr) and isinstance(last.value, ast.Call):
        return _dotted_name(last.value.func) in {"sys.exit", "os._exit", "exit", "quit"}
    return False


def _try_catches_capability(node: ast.Try) -> bool:
    for handler in node.handlers:
        if handler.type is None:
            continue
        exprs = (handler.type.elts if isinstance(handler.type, ast.Tuple)
                 else [handler.type])
        for exc in exprs:
            name = (_dotted_name(exc) or "").rsplit(".", 1)[-1]
            if name in _CAPABILITY_EXC_NAMES:
                return True
    return False


def _ast_scope_index(tree: ast.AST) -> tuple[dict, dict, dict]:
    """回 (parent, slot, classes)：slot[child] = (owner, field, index)。"""
    parent: dict = {}
    slot: dict = {}
    classes: dict[str, ast.ClassDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes[node.name] = node
        for field in _BLOCK_FIELDS:
            seq = getattr(node, field, None)
            if isinstance(seq, list):
                for index, child in enumerate(seq):
                    if isinstance(child, ast.AST):
                        slot[child] = (node, field, index)
        for child in ast.iter_child_nodes(node):
            parent[child] = node
    return parent, slot, classes


def _decorated_by_platform_guard(
    node: ast.AST, classes: dict[str, ast.ClassDef], seen: set | None = None
) -> bool:
    """def/class 自己或（同檔）任一祖先類別帶平台守衛 decorator。

    基底類別要跟著看，否則 `@unittest.skipUnless(sys.platform == "darwin", …)`
    放在共用夾具基底、子類別只寫測試（本 repo 的既有寫法）會被整批誤判。
    """
    if any(is_platform_guard_expr(dec) for dec in getattr(node, "decorator_list", [])):
        return True
    if not isinstance(node, ast.ClassDef):
        return False
    seen = set() if seen is None else seen
    for base in node.bases:
        dotted = _dotted_name(base)
        base_node = classes.get(dotted.rsplit(".", 1)[-1]) if dotted else None
        if base_node is not None and base_node not in seen:
            seen.add(base_node)
            if _decorated_by_platform_guard(base_node, classes, seen):
                return True
    return False


def guard_scope_for(node: ast.AST, parent: dict, slot: dict, classes: dict) -> str | None:
    """該使用點被哪一種**站點級**守衛罩住；None＝一種都沒有（＝違規）。"""
    cur = node
    while cur in parent:
        owner = parent[cur]
        if (isinstance(owner, (ast.If, ast.IfExp, ast.While))
                and is_platform_guard_expr(owner.test)):
            return "enclosing-if"
        if (isinstance(owner, ast.Try) and any(cur is s for s in owner.body)
                and _try_catches_capability(owner)):
            return "try-capability"
        if (isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and _decorated_by_platform_guard(owner, classes)):
            return "guarded-decorator"
        position = slot.get(cur)
        if position is not None:
            blk_owner, field, index = position
            for prev in getattr(blk_owner, field)[:index]:
                if (isinstance(prev, ast.If) and is_platform_guard_expr(prev.test)
                        and (_flow_terminates(prev.body) or _flow_terminates(prev.orelse))):
                    return "early-return-guard"
        cur = owner
    return None


def scan_foreign_platform_api(source: str, rel: str) -> tuple[list[str], list[str]]:
    """純函式核心：回傳 (offenders, stale_markers)，元素皆為 `rel:行號: 說明`。"""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return [], []
    markers = _xplat_markers(source)
    uses = _foreign_api_uses(tree, _capability_probed(tree))
    grouped: dict[tuple[int, str, str], list[ast.AST]] = {}
    for node, lineno, side, what in uses:
        grouped.setdefault((lineno, side, what), []).append(node)
    # 索引只在真有使用點時才建（掃描面 800+ 檔，絕大多數一個使用點都沒有）。
    parent, slot, classes = _ast_scope_index(tree) if grouped else ({}, {}, {})
    offenders: list[str] = []
    used: set[int] = set()
    for (lineno, side, what), nodes in sorted(grouped.items()):
        if markers.get(lineno):
            used.add(lineno)
            continue
        # 同一 (行, 方向, 說明) 有多個節點時，只要**其中一個**沒被罩住就算違規——
        # 取第一個判會讓「同行兩處、一處有守衛」把另一處免費藏起來。
        if all(guard_scope_for(n, parent, slot, classes) for n in nodes):
            continue
        offenders.append(
            f"{rel}:{lineno}: 使用 {side} 的 `{what}`，但這個**使用點**不在任何平台"
            "守衛的作用域內（可接受的四種：包住它的 if 判平台／同 block 排在它之前的"
            "早退守衛／所在 def-class 帶平台守衛 decorator／try 捕 ImportError 類）"
            "——對面平台上它不是「行為不同」而是「直接炸掉」（缺屬性／ImportError）"
        )
    stale = [
        f"{rel}:{lineno}: {_XPLAT_OK_MARKER} 標記 stale"
        f"（{'WHY 留空' if not why else '該行無被壓下的違規'}）"
        for lineno, why in sorted(markers.items())
        if lineno not in used or not why
    ]
    return offenders, stale


#: 站點級判準上線當回合的**存量**：檔案級特赦收成作用域級之後，仍未被任何作用域
#: 守衛罩住的使用點數，逐檔精確計數。
#: 判準是**雙向精確比對**：多一筆紅（新增了未守衛的使用點）、少一筆也紅（債已還，
#: 請把數字改小）——只准降不准升的單邊寫法會讓這張表變成一張永久保護傘。
#: 合法出口只有兩條：① 把站點改成作用域內守衛；② 該行行尾加 `_XPLAT_OK_MARKER` 標記。
#: （本註解刻意不寫出那個標記的字面值——本檔自己也在掃描面內，寫出來就會被
#:   `_xplat_markers()` 當成一個真的豁免標記而判 stale。）
#: 🔴 R79 誠實劃界：表內這支檔不屬 R79 XPLAT 包的所有權（`tools/dev_start.py` 的
#:   `_forward_signal_to_bootstrap()` 是 POSIX-only 的訊號 handler，只在 POSIX 側
#:   `signal.signal()` 註冊——那個註冊點在別的函式裡，靜態上罩不到它），故本輪只
#:   登記不代改；處置已列入交棒（加行尾豁免標記即可歸零）。
_FOREIGN_API_SCOPE_DEBT: dict[str, int] = {
    "tools/dev_start.py": 4,
}


class TestForeignPlatformApiIsGuarded(unittest.TestCase):
    """對面平台專屬 API 必須帶平台守衛（見上方區段 WHY）。"""

    def test_no_unguarded_foreign_platform_api(self) -> None:
        offenders, stale, parse_failures, band = run_unit_scan(scan_foreign_platform_api)
        self.assertEqual(
            parse_failures, [],
            "以下 .py 無法 parse——掃描面不得靜默縮小：\n" + "\n".join(parse_failures),
        )
        actual: dict[str, int] = {}
        for line in offenders:
            rel = line.split(":", 1)[0]
            actual[rel] = actual.get(rel, 0) + 1
        unregistered = [o for o in offenders
                        if o.split(":", 1)[0] not in _FOREIGN_API_SCOPE_DEBT]
        self.assertEqual(
            unregistered, [],
            "發現未守衛的單平台專屬 API——請加**作用域內**平台守衛、改用 `hasattr` "
            f"明示可選能力，或於該行行尾加 `# {_XPLAT_OK_MARKER} <WHY>`：\n"
            + "\n".join(unregistered),
        )
        self.assertEqual(
            actual, dict(_FOREIGN_API_SCOPE_DEBT),
            "`_FOREIGN_API_SCOPE_DEBT` 與實測不符。多一筆＝新增了未守衛的使用點；"
            "少一筆＝債已還請把數字改小（不改的話這張表會變成永久保護傘，"
            "下一筆新違規會被舊值遮住）：\n" + "\n".join(offenders),
        )
        self.assertEqual(
            stale, [],
            f"{_XPLAT_OK_MARKER} 豁免標記 stale（防清單腐化）：\n" + "\n".join(stale),
        )
        self.assertEqual(band, [], "掃描面下限帶：\n" + "\n".join(band))

    # ── 以合成樣本自證判準紅綠（樣本只存在於字串，不留違規樣本於 repo）──────

    def _scan(self, source: str) -> tuple[list[str], list[str]]:
        return scan_foreign_platform_api(source, _INJECTION_TARGET_REL)

    def test_each_whitelisted_symbol_family_is_detected(self) -> None:
        for sample in (
            "import pwd\n",
            "import winreg\n",
            "def f():\n    return os.fork()\n",
            "def f(p):\n    os.killpg(p, signal.SIGKILL)\n",
            "def f(p):\n    os.startfile(p)\n",
            "def f(c):\n    subprocess.run(c, preexec_fn=None)\n",
            'def f(mp):\n    mp.set_start_method("fork")\n',
        ):
            with self.subTest(sample=sample):
                off, _ = self._scan(sample)
                self.assertTrue(off, f"{sample!r} 漏抓 ⇒ 白名單那一半沒有牙")

    def test_a_guard_before_the_use_is_accepted(self) -> None:
        """修法慣例必綠——否則本鎖會逼人把守衛拿掉。"""
        for sample in (
            'import sys\nif sys.platform == "win32":\n    import winreg\n',
            'def f():\n    if os.name == "nt":\n        return None\n    return os.fork()\n',
            'def f():\n    if hasattr(os, "geteuid"):\n        return os.geteuid()\n'
            "    return 0\n",
        ):
            with self.subTest(sample=sample):
                off, stale = self._scan(sample)
                self.assertEqual((off, stale), ([], []), f"{sample!r} 誤報")

    def test_a_guard_after_the_use_does_not_count(self) -> None:
        """守衛排在使用之後不算（DEF-101-766 的形態，沿用第五道判準的順序語意）。"""
        off, _ = self._scan(
            'def f():\n    pid = os.fork()\n    if os.name == "nt":\n'
            "        return None\n    return pid\n"
        )
        self.assertEqual(len(off), 1, off)

    def test_mentions_in_comments_and_docstrings_are_not_uses(self) -> None:
        """對照組：註解／docstring 提到這些名字不算使用（假紅會逼人關掉整條鎖）。"""
        for sample in (
            "# 這裡本來想用 os.fork()，改走 subprocess\nx = 1\n",
            '"""說明：POSIX 上是 os.killpg + signal.SIGKILL。"""\nx = 1\n',
            'MSG = "import pwd 在 Windows 上會 ImportError"\n',
        ):
            with self.subTest(sample=sample):
                off, _ = self._scan(sample)
                self.assertEqual(off, [], f"{sample!r} 誤報：{off}")

    def test_marker_suppresses_and_a_dangling_marker_is_stale(self) -> None:
        off, stale = self._scan(
            f"def f():\n    return os.fork()  # {_XPLAT_OK_MARKER} 只在 POSIX 分支呼叫\n")
        self.assertEqual((off, stale), ([], []))
        off, stale = self._scan(f"x = 1  # {_XPLAT_OK_MARKER} 已改走 subprocess\n")
        self.assertEqual(off, [])
        self.assertEqual(len(stale), 1, "違規已消失的標記必須被指名刪除")
        off, stale = self._scan(f"def f():\n    return os.fork()  # {_XPLAT_OK_MARKER}\n")
        self.assertEqual(len(off), 1, "WHY 留空的標記不得生效")

    # ── R79：站點級特赦的紅綠自證（舊判準在這幾題上的實測值逐題記在斷言訊息裡）──

    #: 5 筆彼此獨立的違規，刻意分散在 4 個函式：`import pwd`／`os.killpg`／
    #: `signal.SIGKILL`／`os.getuid`／`os.fork`。
    _FIVE_VIOLATIONS = (
        "import pwd\n"
        "\n"
        "\n"
        "def kill(pgid):\n"
        "    os.killpg(pgid, signal.SIGKILL)\n"
        "\n"
        "\n"
        "def who():\n"
        "    return os.getuid()\n"
        "\n"
        "\n"
        "def spawn():\n"
        "    return os.fork()\n"
    )
    #: 與那 5 筆違規**完全無關**的一段守衛（隔壁函式），舊判準會拿它特赦整檔。
    _UNRELATED_GUARD = (
        "def unrelated():\n"
        '    if sys.platform == "win32":\n'
        "        return 1\n"
        "    return 0\n"
        "\n"
        "\n"
    )

    def test_an_unrelated_guard_elsewhere_no_longer_amnesties_the_whole_file(self) -> None:
        """情境 A：隔壁函式的守衛不得赦免整檔（舊判準此題只抓到 1/5）。"""
        head, _, tail = self._FIVE_VIOLATIONS.partition("\n\n\n")
        sample = head + "\n\n\n" + self._UNRELATED_GUARD + tail
        off, _ = self._scan(sample)
        self.assertEqual(
            len(off), 5,
            "同一組 5 筆違規只抓到部分 ⇒ 檔案級特赦仍在（舊判準實測 1/5）：\n"
            + "\n".join(off),
        )

    def test_the_same_five_violations_without_any_guard(self) -> None:
        """情境 B：對照組——沒有那段無關守衛時本來就該是 5/5。"""
        off, _ = self._scan(self._FIVE_VIOLATIONS)
        self.assertEqual(len(off), 5, "\n".join(off))

    def test_a_guard_phrase_inside_a_string_constant_is_not_a_guard(self) -> None:
        """情境 C：守衛字樣只出現在字串常數裡（舊判準此題 0/1）。"""
        off, _ = self._scan(
            'MSG = "設定 os.name == \'nt\' 時走另一條路"\n'
            "\n"
            "\n"
            "def spawn():\n"
            "    return os.fork()\n"
        )
        self.assertEqual(len(off), 1, f"字串常數不得構成守衛：{off}")

    def test_a_string_operand_inside_an_if_test_is_not_a_guard(self) -> None:
        """`if "IS_WINDOWS" in env:` 不是在判平台——這是文字比對留下的最後一個後門。"""
        off, _ = self._scan(
            'def f(env):\n    if "IS_WINDOWS" in env:\n        return os.fork()\n'
            "    return 0\n"
        )
        self.assertEqual(len(off), 1, f"字串運算元不得構成守衛：{off}")

    def test_each_accepted_scope_form_is_green(self) -> None:
        """四種罩法逐一必綠——任何一種掉了，repo 內既有的合法寫法會整批假紅。"""
        for label, sample in (
            ("enclosing-if",
             'def f():\n    if os.name != "nt":\n        return os.fork()\n    return 0\n'),
            ("early-return-guard",
             "def f(pid):\n    if platform_utils.is_windows():\n        return None\n"
             "    return os.getpgid(pid)\n"),
            ("guarded-decorator",
             '@unittest.skipIf(sys.platform == "win32", "POSIX only")\n'
             "class T:\n    def t(self):\n        return os.fork()\n"),
            ("inherited-decorator",
             '@unittest.skipUnless(sys.platform == "darwin", "mac only")\n'
             "class Base:\n    pass\n"
             "\n"
             "\n"
             "class T(Base):\n    def t(self):\n        return os.getuid()\n"),
            ("try-capability",
             "try:\n    import pwd\nexcept ImportError:\n    pwd = None\n"),
        ):
            with self.subTest(scope=label):
                off, _ = self._scan(sample)
                self.assertEqual(off, [], f"{label} 誤報：{off}")

    def test_a_terminating_guard_is_required_for_the_early_return_form(self) -> None:
        """早退守衛必須真的早退：`if is_windows(): pass` 罩不住後面的 POSIX 碼。"""
        off, _ = self._scan(
            "def f(pid):\n    if platform_utils.is_windows():\n        pass\n"
            "    return os.getpgid(pid)\n"
        )
        self.assertEqual(len(off), 1, f"沒有帶走控制流的 if 不算守衛：{off}")

    def test_text_guard_ssot_is_fully_recognised_by_the_ast_predicate(self) -> None:
        """鎖的鎖：`_PLATFORM_GUARDS` 的 Python 側每一項都必須被 AST 判準認得。

        兩份知識（行文字 SSOT ／ AST 符號表）不得單向漂移——有人往
        `_PLATFORM_GUARDS` 補一個新的 Python 守衛字樣卻忘了教 AST 判準時，
        那個字樣在本判準上會靜默失效（＝合法寫法假紅）。這裡把「解析得動、
        但 AST 判準不認」的集合精確釘死在已知的非 Python 項上。
        """
        unrecognised = set()
        for token in _PLATFORM_GUARDS:
            try:
                expr = ast.parse(token, mode="eval").body
            except SyntaxError:
                continue          # PowerShell／shell 專屬字樣，本判準射程外
            if not is_platform_guard_expr(expr):
                unrecognised.add(token)
        self.assertEqual(
            unrecognised, set(_NON_PYTHON_GUARD_TOKENS),
            "`_PLATFORM_GUARDS` 與 `_PLATFORM_DECIDING_SYMBOLS` 漂移了："
            f"{sorted(unrecognised)}",
        )

    def test_the_debt_table_only_names_files_that_exist(self) -> None:
        """存量債表不得指向幽靈檔（否則那一格永遠是 0，等同一張空白支票）。"""
        missing = [rel for rel in _FOREIGN_API_SCOPE_DEBT
                   if not (_REPO_ROOT / rel).is_file()]
        self.assertEqual(missing, [], f"債表指向不存在的檔：{missing}")


# ══════════════════════════════════════════════════════════════════════════════
# R79（D-ps1eol）— **工作樹**行尾閘：`.ps1` 必為 CRLF、`.sh` 必為 LF
# ══════════════════════════════════════════════════════════════════════════════
# 缺陷本體：`.ps1` 要 CRLF 這件事在三處被宣告（`.gitattributes` 的
# `*.ps1 text eol=crlf`、`.editorconfig`、`root-infra-ci.yml` 第 4 道 EOL 閘），
# **寫入端零強制**——而 R79 已把寫入者溯源到 Claude Code 的 `Write` 工具（新建與
# 覆寫既有 CRLF 檔都吐 LF）。R79 已為此把 PostToolUse 的 `check_ps1_encoding.py`
# 擴成位元組正規化器（BOM ＋ CRLF），但 hook 只罩得住「經由工具寫入」這一條路：
# 人工編輯器、GitHub web、外部腳本一律繞得過，所以必須另有一道**事後**閘。
#
# 🔴 方向不可照抄 `.sh` 那一道：`tools/git-hooks/pre-commit` 對 `.sh` 看的是
#   **blob**（index 內容），而 `.ps1` 因 `eol=crlf` 的 checkin 正規化，其 blob
#   **恆為 LF** ⇒ blob 判準對 `.ps1` 結構上恆綠。本閘因此讀 `git ls-files --eol`
#   的 `w/`（working tree）欄。同一個理由讓 CI 也看不見這件事：`actions/checkout`
#   必定重新 smudge，雲端的工作樹結構上永遠合規（R78 逐項實查的結論）。
#
# 為何連 `.sh` 一起看（射程刻意對稱）：`.sh` 方向今天乾淨，但乾淨的原因是三重
# 覆蓋裡沒有一層在看工作樹——CRLF `.sh` 一旦被 `git add` 前的人工編輯造出來，
# 本機同樣沒有訊號。一個判準覆蓋兩個方向，比兩個各自半殘的判準便宜。
# 🔴 R79 四方複審（SD nonblocking）訂正：本表原是一份**手抄**的副檔名→行尾映射，
#   也就是 `.gitattributes` 的第二個家——而它在落地當下就已經不完整（漏了同樣宣告
#   `eol=crlf` 的 `.cmd`／`.bat`）。字面表天生看不出「漏了什麼」，因為漏掉的那一格
#   在表裡不存在，任何只讀表的判準都掃不到它。改法不是補兩格，是**讓表變成量測值**：
#   下面的映射從 `.gitattributes` 現查產生，`.gitattributes` 因此維持唯一真相源。
_GITATTRIBUTES_PATH = _REPO_ROOT / ".gitattributes"
#: `*.<suffix>  <attrs>` 形態的宣告行（`#` 註解行不匹配；`* text=auto eol=lf` 這種
#: 無副檔名的兜底規則也不匹配——它涵蓋全庫，不是「腳本行尾」這個主題）。
_EOL_DECL_RE = re.compile(r"^\s*\*(\.[A-Za-z0-9]+)\s+([^#\n]*)", re.M)
#: LF 側刻意**不**全收（誠實劃界，不是漏看）：根 `.gitattributes` 對 `.py`／`.md`／
#: `.yaml` 等也宣告 `eol=lf`，全收會把本閘的主題從「腳本行尾」擴成「全庫文字檔行尾」
#: ——當回合實測全庫有五位數支檔案的工作樹行尾與宣告不符，絕大多數落在 AISDLC_SDD
#: 凍結版樹（Copy-on-Evolve 禁改面）。本閘的主題是腳本，故 LF 側只收 shell 腳本族；
#: 但**值仍向 `.gitattributes` 取**，本檔不寫死 `lf` 這兩個字。
_EOL_LF_SCOPE: tuple[str, ...] = (".sh", ".bash")


def declared_eol(gitattributes_text: str) -> dict[str, str]:
    """`.gitattributes` 裡每一條 `*.<副檔名> … eol=<lf|crlf>` 宣告。純函式。"""
    out: dict[str, str] = {}
    for suffix, attrs in _EOL_DECL_RE.findall(gitattributes_text):
        match = re.search(r"\beol=(lf|crlf)\b", attrs)
        if match:
            out[suffix.lower()] = match.group(1)
    return out


def worktree_eol_policy(declared: dict[str, str]) -> dict[str, str]:
    """本閘的政策映射＝**現查值**（見上方 WHY）。

    CRLF 側**全收**：`eol=crlf` 在本 repo 就是「Windows-only 腳本族」的同義詞，
    新增一個（例如日後的 `.cmd`）自動進射程，不需要有人記得同步第二份表。
    LF 側只收 `_EOL_LF_SCOPE`，理由見該常數。
    """
    policy = {suffix: eol for suffix, eol in declared.items() if eol == "crlf"}
    policy.update({s: declared[s] for s in _EOL_LF_SCOPE if s in declared})
    return policy


if not _GITATTRIBUTES_PATH.is_file():                  # fail-loud：沒有 SSOT 就沒有政策
    raise AssertionError(f"找不到 {_GITATTRIBUTES_PATH}——行尾政策的唯一真相源缺席")
_WORKTREE_EOL_POLICY: dict[str, str] = worktree_eol_policy(
    declared_eol(_GITATTRIBUTES_PATH.read_text(encoding="utf-8")))
#: 反空轉下限（**逐副檔名**，R79 收輪實測 `.ps1` 136 支／`.sh` 168 支，取約八折）。
#: 🔴 為何不是一個總數（R79 四方複審 SD nonblocking）：單一總數吃得下「某一個副檔名
#: 整片消失」——`.ps1` 全滅而 `.sh` 還在時，總數照樣過關，而那正是這道閘要抓的形態。
#: 只登記**現存母體夠大**的副檔名；`.psm1`／`.psd1`／`.cmd`／`.bat` 現況零支，
#: 給它們一個 0 下限等於沒登記，故刻意不入表（入表與否由下面的判準機械對帳）。
_WORKTREE_EOL_FLOORS: dict[str, int] = {".ps1": 108, ".sh": 134}


def parse_ls_files_eol(stdout: str) -> list[tuple[str, str]]:
    """`git ls-files --eol` 的輸出 → [(路徑, 工作樹行尾)]。純函式，供紅綠自證共用。

    格式（當回合實測逐字）：`i/lf    w/crlf  attr/text eol=crlf    \t<path>`
    ——三個欄位以**空白**右補、彼此不以 tab 分隔，整行只有**一個** tab 且它就在
    路徑前面。`attr/` 欄本身含空白（`text eol=crlf`），所以不能用空白切欄。
    """
    rows: list[tuple[str, str]] = []
    for line in stdout.splitlines():
        head, sep, path = line.partition("\t")
        if not sep or not path.strip():
            continue
        match = re.search(r"\bw/(\S*)", head)
        rows.append((path.strip(), match.group(1) if match else ""))
    return rows


def path_suffix(path: str) -> str:
    """repo 相對路徑的小寫副檔名（含點）。無副檔名回空字串。"""
    name = path.rsplit("/", 1)[-1]
    return "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""


def worktree_eol_problems(rows: list[tuple[str, str]]) -> list[str]:
    """逐列過政策表；回問題清單，空＝合格。純函式（紅綠由合成注入自證）。"""
    problems: list[str] = []
    for path, worktree in rows:
        want = _WORKTREE_EOL_POLICY.get(path_suffix(path))
        if want is None:
            continue
        if worktree in {want, "none"}:   # none＝空檔／無換行，無從違反
            continue
        problems.append(
            f"{path}: 工作樹行尾為 `{worktree or '未知'}`，政策要求 `{want}`"
            f"（.gitattributes 已宣告；index 側因 checkin 正規化恆為 lf，"
            "故只有工作樹這一欄看得到這種漂移）"
        )
    return problems


class TestWorktreeEolMatchesPolicy(unittest.TestCase):
    """工作樹行尾必須符合 `.gitattributes` 宣告（見上方區段 WHY）。"""

    @staticmethod
    def _ls_files_eol() -> str:
        proc = subprocess.run(
            ["git", "-C", str(_REPO_ROOT), "ls-files", "--eol", "--",
             *(f"*{suffix}" for suffix in sorted(_WORKTREE_EOL_POLICY))],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
        )
        if proc.returncode != 0:                      # 取數管道壞掉不得靜默變成「零違規」
            raise AssertionError(
                f"git ls-files --eol 失敗（rc={proc.returncode}；stderr="
                f"{proc.stderr.strip()!r}）——本閘的輸入沒了，不是「沒有違規」"
            )
        return proc.stdout

    def test_tracked_scripts_have_the_declared_worktree_eol(self) -> None:
        rows = parse_ls_files_eol(self._ls_files_eol())
        seen = {suffix: 0 for suffix in _WORKTREE_EOL_FLOORS}
        for path, _worktree in rows:
            suffix = path_suffix(path)
            if suffix in seen:
                seen[suffix] += 1
        for suffix, floor in _WORKTREE_EOL_FLOORS.items():
            self.assertGreaterEqual(
                seen[suffix], floor,
                f"`{suffix}` 的行尾掃描面只有 {seen[suffix]} 支（下限 {floor}）——該副檔名的"
                "射程疑似被縮小。🔴 下限刻意**逐副檔名**：一個吃得下整體的總數，會讓"
                "「某一個副檔名整片消失、另一個還在」照樣過關，而那正是本閘要抓的形態",
            )
        problems = worktree_eol_problems(rows)
        self.assertEqual(
            problems, [],
            "工作樹行尾與政策不符。🔴 `git status` 對這種漂移**結構上看不見**"
            "（兩側套同一份正規化規則），`git add` 之後連唯一的幽靈 `M` 列都會消失；"
            "修法：讓 PostToolUse 的 `AutoClaude/tools/hooks/check_ps1_encoding.py` "
            "再跑一次（`.ps1` 方向），或以正確行尾重存：\n" + "\n".join(problems),
        )

    # ── 紅綠自證（合成列，不動磁碟）────────────────────────────────────────────

    def test_the_parser_reads_the_worktree_column_not_the_index_column(self) -> None:
        """最關鍵的一題：讀錯欄位會讓整條閘門恆綠（index 側 `.ps1` 恆為 lf）。"""
        line = "i/lf    w/crlf  attr/text eol=crlf    \ttools/x.ps1"
        self.assertEqual(parse_ls_files_eol(line), [("tools/x.ps1", "crlf")])
        self.assertEqual(worktree_eol_problems(parse_ls_files_eol(line)), [])

    def test_an_lf_ps1_and_a_crlf_sh_both_turn_red(self) -> None:
        for path, worktree in (("tools/a.ps1", "lf"), ("tools/b.psm1", "mixed"),
                               ("tools/c.sh", "crlf"), ("tools/d.bash", "mixed")):
            with self.subTest(path=path):
                self.assertEqual(
                    len(worktree_eol_problems([(path, worktree)])), 1,
                    f"{path} 的 `w/{worktree}` 沒被判紅 ⇒ 該方向零鑑別力")

    def test_out_of_scope_suffixes_and_empty_files_are_green(self) -> None:
        """假紅會逼下一輪把整條閘關掉：政策外副檔名與空檔一律放行。"""
        self.assertEqual(worktree_eol_problems([("docs/a.md", "lf")]), [])
        self.assertEqual(worktree_eol_problems([("tools/a.py", "crlf")]), [])
        self.assertEqual(worktree_eol_problems([("tools/empty.ps1", "none")]), [])

    def test_the_policy_table_covers_both_directions(self) -> None:
        """政策表不得只剩一個方向——單向表會讓「對稱」這個設計意圖靜默消失。"""
        self.assertEqual(set(_WORKTREE_EOL_POLICY.values()), {"crlf", "lf"})
        self.assertIn(".ps1", _WORKTREE_EOL_POLICY)
        self.assertIn(".sh", _WORKTREE_EOL_POLICY)


class TestWorktreeEolPolicyIsMeasuredFromGitattributes(unittest.TestCase):
    """政策映射必須是 `.gitattributes` 的**現查值**，不是抄本（R79 四方複審 SD）。

    被守的缺陷：R79 落地的版本是一份手抄表，且**在落地當下就已經不完整**——同樣宣告
    `eol=crlf` 的 `.cmd`／`.bat` 不在表裡。這一類漏看用「再讀一次表」永遠找不出來，
    因為漏掉的那一格在表裡不存在；唯一有效的判準是拿它去跟真正的持有者對帳。
    """

    def setUp(self) -> None:
        self.declared = declared_eol(
            _GITATTRIBUTES_PATH.read_text(encoding="utf-8"))

    def test_the_parser_really_reads_the_current_gitattributes(self) -> None:
        """自錨：解析器垮掉（正則寫壞／檔案改名）時，下面每一條都會變成「對空氣全綠」。"""
        self.assertGreaterEqual(
            len(self.declared), 10,
            f"只解析出 {len(self.declared)} 條 eol 宣告 ⇒ 解析器疑似失效：{self.declared}")
        for suffix, eol in ((".ps1", "crlf"), (".sh", "lf"), (".cmd", "crlf")):
            self.assertEqual(self.declared.get(suffix), eol,
                             f"`.gitattributes` 對 {suffix} 的宣告解析成 "
                             f"{self.declared.get(suffix)!r}（預期 {eol!r}）")

    def test_every_crlf_declaration_is_in_scope(self) -> None:
        """缺陷本體那一向：`.gitattributes` 宣告 `eol=crlf` 的每一格都必須在射程內。

        R79 落地時漏掉的 `.cmd`／`.bat` 就是被這一向抓到的。
        """
        crlf = {s for s, e in self.declared.items() if e == "crlf"}
        self.assertEqual(
            sorted(crlf - set(_WORKTREE_EOL_POLICY)), [],
            "這些副檔名在 `.gitattributes` 宣告了 CRLF，卻不在本閘射程內 ⇒ 它們的工作樹"
            "行尾漂移**沒有任何人看得見**（`git status` 對這種漂移結構上盲）",
        )

    def test_every_policy_cell_equals_the_declaration(self) -> None:
        """反向：表內每一格的值都必須等於 `.gitattributes` 的宣告（不得自行改值）。"""
        mismatched = {
            suffix: (eol, self.declared.get(suffix))
            for suffix, eol in _WORKTREE_EOL_POLICY.items()
            if self.declared.get(suffix) != eol
        }
        self.assertEqual(mismatched, {}, f"政策與宣告不一致（本閘值, 宣告值）：{mismatched}")

    def test_the_policy_follows_the_declaration_instead_of_a_copy(self) -> None:
        """判準自證：換一份 `.gitattributes` 進去，映射必須跟著動。

        少了這一支，上面兩條在「政策其實是寫死的、只是剛好與現況相符」時仍全綠——
        那正是本 finding 的原始狀態（表與宣告當時對得上，只是少了兩格）。
        """
        fake = ("* text=auto eol=lf\n"
                "# *.ignored text eol=crlf   ← 註解行不得被讀成宣告\n"
                "*.sh   text eol=crlf\n"
                "*.zzz  text eol=crlf\n"
                "*.py   text eol=lf\n")
        policy = worktree_eol_policy(declared_eol(fake))
        self.assertEqual(policy.get(".sh"), "crlf",
                         "LF 側的值也必須取自宣告，不得寫死 ⇒ 這一格證明它不是抄本")
        self.assertEqual(policy.get(".zzz"), "crlf",
                         "新宣告的 CRLF 副檔名沒有自動進射程 ⇒ 又需要有人記得同步第二份表")
        self.assertNotIn(".ignored", policy, "註解行被讀成宣告")
        self.assertNotIn(".py", policy,
                         "LF 側不得全收（見 `_EOL_LF_SCOPE`：全收會把主題擴成全庫文字檔）")
        # 反向的代價要說清楚：把 `.ps1` 宣告成 LF，它會整個**掉出**射程（不是變成 LF 政策）
        # ——這正是上面 `test_the_two_p0_directions_are_pinned` 那道止血點在守的事。
        dropped = worktree_eol_policy(declared_eol("*.ps1 text eol=lf\n"))
        self.assertNotIn(".ps1", dropped)

    def test_the_two_p0_directions_are_pinned(self) -> None:
        """現查式 SSOT 的代價是「來源被改壞就跟著壞」——這一支是它的止血點。

        `.sh` 被改成 CRLF 在 Docker／act 內會 `$'\\r': command not found`（取證紀律 #8），
        `.ps1` 缺 CRLF 則是本閘立案的理由。這兩格無論 `.gitattributes` 怎麼寫都不准翻。
        """
        self.assertEqual(_WORKTREE_EOL_POLICY.get(".ps1"), "crlf")
        self.assertEqual(_WORKTREE_EOL_POLICY.get(".sh"), "lf")

    def test_every_floor_names_a_suffix_in_scope(self) -> None:
        """逐副檔名下限不得指向射程外的副檔名（那種下限永遠是 0 支、等於沒有）。"""
        orphan = sorted(set(_WORKTREE_EOL_FLOORS) - set(_WORKTREE_EOL_POLICY))
        self.assertEqual(orphan, [], f"下限表指向射程外的副檔名：{orphan}")


# ══════════════════════════════════════════════════════════════════════════════
# R79（S-xplat）— 「別人開著這個檔」在 Windows 會炸掉的**目錄項原語**
# ══════════════════════════════════════════════════════════════════════════════
# 缺陷本體：本 repo 已經正確登記了「Windows 刪不掉被開著的檔」，卻把它記成一條
# 關於 `unlink` 的知識，而不是一條關於「任何會改動目錄項的原語」的知識。換一個
# 原語就整片失明——**連錯誤碼都換了**。當回合在本機實測（三個案例同一支探針）：
#     os.replace 覆寫「被純讀者開著」的目的檔 → PermissionError winerror=5
#     同一組但目的檔已關閉                    → OK
#     os.unlink 一個被開著的檔                → PermissionError winerror=32
# POSIX 上前者恆成功 ⇒ 這是一個只在 Windows、只在並行時發生、且不留痕跡的落差。
# 本 repo 的常態作業型態正是它的觸發條件（多 agent 共用一棵工作樹，CONTEXT-LEDGER
# 與 trajectory/drift 那幾份 YAML 同時被多方讀寫）。
#
# 🔴 誠實劃界（這一節買到的是什麼、買不到什麼）：
#   · 買到：新增一個**未處置** `PermissionError/OSError` 的目錄項原語站點會轉紅。
#   · 買不到：「捕了但吞掉」不算修好——`context_ledger_pre.py` 外層那個
#     `except Exception` 會把它吞成靜默漏記（token 帳目變少，沒有人覺得不對）。
#     靜態判準看得到「有沒有處置」，看不到「處置得對不對」。
#   · 不代改：現存站點全在 `AISDLC_SDD/**`（Copy-on-Evolve 禁改凍結版；LATEST 的
#     那批也不在 R79 XPLAT 包的檔案所有權內），故本輪只誠實登記、逐筆可查。
#: 原語 → 本機實測到的 winerror（值為 None＝本輪未逐一實測，僅登記形態）。
_WINDOWS_OPEN_FILE_HOSTILE_PRIMITIVES: dict[str, int | None] = {
    "os.replace": 5,     # 覆寫「被開著」的目的檔（本節主角，R79 首次登記）
    "os.unlink": 32,     # 既有知識（DEF-101 系列已登記的那一個）
    "os.rename": None,
    "os.renames": None,
    "shutil.move": None,
    "shutil.rmtree": None,
}
#: 走 AST 抓得到的**檔案系統**目錄項原語（`shutil.rmtree`／`os.unlink` 屬刪除語意，
#: 已由既有知識覆蓋，本掃描只管「覆寫既有目的檔」這一族，避免與既有鎖射程重疊）。
_DIRENT_PRIMITIVES: frozenset[str] = frozenset(
    {"os.replace", "os.rename", "os.renames", "shutil.move"})
#: `<x>.replace(<單一引數>)`／`<x>.rename(...)` 這種 Path 方法形態的**排除**清單：
#: 這幾個模組的同名函式與檔案系統無關，納入即假紅（`dataclasses.replace(obj)` 實測
#: 會被單純的「1 個引數」啟發式命中）。
_NON_PATH_REPLACE_OWNERS: frozenset[str] = frozenset({"dataclasses", "attr", "attrs", "copy"})
#: 存量：**live 樹**內未處置 `PermissionError`／`OSError` 的站點數。
#: 判準是雙向精確比對（同本檔其餘欠債表的理由）。
#: 🔴 掃描面刻意不含凍結版 v0.01~v0.29，兩個理由缺一不可：① Copy-on-Evolve 禁改
#:   凍結版，那裡結構上不會出現「新寫的」違規，掃它得不到可行動的訊號；② 當回合
#:   實測含凍結版時整支測試要 **133 秒**（凍結版 1,131 筆是同一批程式碼被複製 29 次），
#:   而護欄層的執行時間本身已是本輪一筆獨立 finding。凍結版的那 1,131 筆是**已量到、
#:   刻意不進帳**的事實，不是沒看見。
_DIRENT_UNGUARDED_DEBT: dict[str, int] = {"live": 41}


def dirent_primitive_sites(source: str, rel: str) -> list[tuple[str, int, str, bool]]:
    """(檔, 行號, 原語, 是否已處置 PermissionError/OSError)。純函式，供紅綠自證共用。"""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    parent, _slot, _classes = _ast_scope_index(tree)
    out: list[tuple[str, int, str, bool]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _dotted_name(node.func)
        if name is None:
            continue
        if name in _DIRENT_PRIMITIVES:
            label = name
        elif (name.rsplit(".", 1)[-1] in {"replace", "rename"}
              and len(node.args) == 1 and not node.keywords
              and name.rsplit(".", 1)[0] not in _NON_PATH_REPLACE_OWNERS
              and "." in name):
            label = f"Path.{name.rsplit('.', 1)[-1]}"
        else:
            continue
        handled = False
        cur: ast.AST = node
        while cur in parent:
            owner = parent[cur]
            if isinstance(owner, ast.Try):
                for handler in owner.handlers:
                    text = ast.unparse(handler.type) if handler.type else ""
                    if "PermissionError" in text or "OSError" in text:
                        handled = True
            cur = owner
        out.append((rel, node.lineno, label, handled))
    return out


# ══════════════════════════════════════════════════════════════════════════════
# R79（S-xplat）— exec bit：Windows 上唯一還看得見的那個管道＝**git 索引模式**
# ══════════════════════════════════════════════════════════════════════════════
# 缺陷本體（兩半，同源）：
#  ① 索引模式在 Windows 上「不是沒人查，是 git 自己被設定成不看」——本機實測
#     `core.filemode=false`，於是檔案模式從不出現在 `git status`／`git diff`／任何
#     pre-commit 掃描裡。27,544 支 tracked 檔只有 7 支是 100755，而框架**給外部
#     使用者的第一條指令**（30 個版本樹的 `tools/README.md`「方法 3 → Mac / Linux」）
#     教人裸跑 `./…/init_project.sh`，該檔索引模式是 100644 ⇒ mac/Linux 使用者
#     一 clone 就死在第一步（POSIX execve 對非 x 檔回 EACCES，shell 回 rc=126）。
#     緊接的 Windows 欄用 `.\init_project.ps1` 照樣能跑 ⇒ 這份文件在 Windows 上
#     永遠讀起來是對的。**製造端與觀測端都在 Windows，受害端只在 mac/Linux。**
#  ② Windows 側那條 exec bit 治理鏈（`tools/git-hooks/post-commit` 的 `[ -x ]`
#     守衛、它的回歸鎖、macos-compat-ci 的 `test -x`）**一格覆蓋都沒有**。當回合
#     在 Git Bash（MINGW64）實測，比原判詞更糟：
#         with_shebang.sh  [ -x ]=EXECUTABLE  ls=-rwxr-xr-x
#         no_shebang.sh    [ -x ]=NOT-EXEC    ls=-rw-r--r--
#         bom_shebang.sh   [ -x ]=NOT-EXEC    ls=-rw-r--r--   ← 檔首多 3 個位元組就翻
#         no_shebang.sh 加 `chmod +x` 之後 → 仍然 NOT-EXEC
#     也就是說 `[ -x ]` 在這裡是**對檔首兩個位元組的內容猜測**，不是權限位元，
#     而且 `chmod` 動不了它 ⇒ 「加執行權限」在 Windows 側是一個做不到的動作。
#     反向失效（檔首多任何位元組 → dispatcher 靜默 exit 0）全 repo 零判準。
#
# 本判準因此**只讀 `git ls-files -s` 的索引模式**：那是 Windows 上唯一不受
# `core.filemode` 影響、也不依賴檔案系統權限位元的觀測管道，同一支判準在三個
# 平台上都跑得動、都給同一個答案。
_INDEX_MODE_EXEC = "100755"
#: 文件裡「教人裸跑」的形態：行首或空白後的 `./<path>.sh`（反引號／程式碼區塊皆同）。
_BARE_SH_INVOCATION_RE = re.compile(r"(?<![\w./-])\./([A-Za-z0-9_./-]+\.sh)\b")
#: 存量欠債：**凍結版**（v0.01~v0.29）`tools/README.md` 內教人裸跑、而標的索引模式
#: 不是 100755 的站點數。R79 實測 30 支 README × 3 行＝90，其中 LATEST 那一支
#: （3 筆）於本輪修掉 ⇒ 29 × 3 = 87 留在凍結版。
#: 🔴 為何只修 LATEST：Copy-on-Evolve 政策禁止改凍結版（歷來三次例外都經掌舵者
#:   明文核准）。這 87 筆是**可見的欠債**，不是豁免。
#: 判準是**雙向精確比對**：多一筆＝新增了同型缺陷；少一筆＝有人動了凍結版
#: （那本身就是需要被看見的事件），兩向都必須有人回來改這個數字。
_BARE_SH_DOC_DEBT_FROZEN = 87


def index_modes(repo_root: Path) -> dict[str, str]:
    """`git ls-files -s` → {repo 相對路徑: 模式}。空 dict ＝取數管道壞掉。"""
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "-s"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
    )
    if proc.returncode != 0:
        return {}
    modes: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        head, sep, path = line.partition("\t")
        if sep and head.split():
            modes[path.strip()] = head.split()[0]
    return modes


def resolve_doc_script(doc_rel: str, script_rel: str, tracked: set[str]) -> str | None:
    """把文件裡的 `./x.sh` 對應到一支 tracked 檔；對應不到回 None（＝不判）。

    刻意只判「對應得到 repo 內真實檔案」的站點：範本／情境樣稿裡大量出現的
    `./scripts/deploy/xxx.sh` 講的是**讀者自己專案**的腳本，判它們是假紅，而假紅
    會逼下一輪把整條鎖關掉（本檔既有判準一貫的取捨）。
    """
    parts = doc_rel.split("/")
    candidates = ["/".join(parts[:-1] + [script_rel]) if len(parts) > 1 else script_rel,
                  script_rel]
    candidates += ["/".join(parts[:i]) + "/" + script_rel for i in range(len(parts) - 1, 0, -1)]
    for cand in candidates:
        cand = cand.replace("//", "/")
        if cand in tracked:
            return cand
    return None


#: 🔴 DEF-101-205（R80 落地）：ONBOARDING §6「執行權限政策」那句散文即 SSOT，本正則把
#: 「755 入庫」範圍的那一段切出來。刻意**不**在程式裡另寫一份清單——那就是本 repo 反覆在
#: 治的「同一份知識住兩個家、只有一個家被改」（判例 DEF-101-778）。切段而非掃全句是必要的：
#: 同一句後半段還寫著「其他 `.sh` 工具…索引 644」，把整句的反引號都收進來會把 644 那一組
#: 也算成 755 白名單，判準當場失去鑑別力。錨定在 `範圍＝**…**` 這個**粗體跨度**而不是
#: 「到下一個『；其他』為止」：落地時實測後者會多吃到緊接在後的 rationale 括號，把
#: `/bin/bash`（那裡在解釋 plist 以誰為執行檔）誤收成一個 755 白名單項。
_EXEC_SCOPE_PROSE_RE = re.compile(r"「755 入庫」範圍＝\*\*(?P<scope>.*?)\*\*")


def exec_bit_prose_scope(onboarding_text: str) -> tuple[tuple[str, ...], str | None]:
    """從 ONBOARDING §6 政策句抽出「允許 100755」的路徑 token；抽不到回 `((), 說明)`。

    抽不到一律 fail-loud：靜默退回空集合會讓下面的雙向比對變成「每一支 755 都違規」
    （一次全紅），靜默放行則讓整道鎖蒸發——兩種都是壞的失敗模式（手法比照
    `tools/check_defect_log_crossref.py::_prose_status_first_words`）。

    🔴 反引號一律以**成對切分**取（`split("`")[1::2]`）而不是用正則抓
    `` `([^`]*/[^`]*)` ``：後者落地時實測會把「上一個 code span 的收尾反引號」跟
    「下一個的起始反引號」配成一對，於是兩個 token 之間那段散文（只要含一個 `/`）
    被當成一個路徑 token 收進白名單。奇數個反引號＝散文寫壞，同樣 fail-loud。
    """
    m = _EXEC_SCOPE_PROSE_RE.search(onboarding_text)
    if m is None:
        return (), (
            "ONBOARDING.md 抽不到「「755 入庫」範圍＝**…**」那個粗體跨度 —— exec bit 政策"
            "的權威散文不存在或被改寫，本判準便無從綁定。請在 §6「執行權限政策」條目補回"
            "該句式，或同步 _EXEC_SCOPE_PROSE_RE 的抽取樣式"
        )
    parts = m.group("scope").split("`")
    if len(parts) % 2 == 0:
        return (), (
            "ONBOARDING §6「755 入庫」範圍那段的反引號**數量為奇數**（未成對）⇒ 無法"
            "可靠切出 code span。請把該段的反引號補成對"
        )
    return tuple(dict.fromkeys(t for t in parts[1::2] if "/" in t)), None


def exec_bit_scope_problems(
    modes: dict[str, str], scope: tuple[str, ...]
) -> list[str]:
    """雙向比對：索引 100755 的集合 ↔ 散文具名的 755 範圍（純函式，可構造輸入驗牙）。

    兩向缺一都不成鎖：
      · 只判①（每支 755 都落在範圍內）⇒ 散文可以無限放寬，多寫幾個目錄就永遠綠。
      · 只判②（每個 token 都真的有 755）⇒ 範圍外冒出一支新 755 一句話都不會說，
        而那正是 `DEF-101-205` 原本擔心的「漂移無訊號」。
    """
    execs = sorted(p for p, mode in modes.items() if mode == _INDEX_MODE_EXEC)
    problems: list[str] = []

    def _covered(path: str) -> bool:
        return any(
            path.startswith(tok) if tok.endswith("/") else path == tok for tok in scope
        )

    for path in execs:
        if not _covered(path):
            problems.append(
                f"{path}：索引模式 100755，但不落在 ONBOARDING §6 政策句具名的範圍內"
                f"（現行範圍＝{list(scope)}）。二擇一：① 這支本來就不該帶 exec bit ⇒ "
                f"`git update-index --chmod=-x {path}`；② 它確實需要 exec bit ⇒ 先去改"
                f"**散文**（ONBOARDING §6 那一句才是 SSOT），本判準會自動跟上"
            )
    for tok in scope:
        if not any(
            (p.startswith(tok) if tok.endswith("/") else p == tok) for p in execs
        ):
            problems.append(
                f"{tok}：ONBOARDING §6 政策句把它列進「755 入庫」範圍，但索引裡該處"
                f"**一支 100755 都沒有** ⇒ 散文已過期。請把它從政策句移除"
                f"（留著就是日後無聲把 755 加回去的額度）"
            )
    return problems


def bare_sh_doc_offenders(
    docs: dict[str, str], modes: dict[str, str]
) -> list[tuple[str, int, str]]:
    """(文件, 行號, 標的) —— 文件教人裸跑、而標的索引模式不是 100755 的站點。"""
    tracked = set(modes)
    out: list[tuple[str, int, str]] = []
    for doc_rel, text in docs.items():
        for lineno, line in enumerate(text.splitlines(), 1):
            for match in _BARE_SH_INVOCATION_RE.finditer(line):
                target = resolve_doc_script(doc_rel, match.group(1), tracked)
                if target is not None and modes[target] != _INDEX_MODE_EXEC:
                    out.append((doc_rel, lineno, target))
    return out


@functools.lru_cache(maxsize=1)
def _live_sdd_prefix() -> str:
    """`AISDLC_SDD/<LATEST>/`——**快取**：`_latest_root()` 走 subprocess 解析 SSOT，
    逐檔呼叫會讓全庫掃描從數十秒暴增到數分鐘（本輪實測踩過一次）。"""
    return f"AISDLC_SDD/{_latest_root().name}/"


def _is_frozen_sdd_path(rel: str) -> bool:
    """凍結版 SDD 樹（v0.01~v0.NN，LATEST 除外）——Copy-on-Evolve 禁改的那一批。"""
    return rel.startswith("AISDLC_SDD/AISDLC_SDD_v0.") and not rel.startswith(
        _live_sdd_prefix())


class TestDirEntryPrimitivesAreAccountedFor(unittest.TestCase):
    """目錄項原語在 Windows 的「檔案被開著」落差（見上方區段 WHY）。"""

    def test_the_platform_gap_is_real_and_re_measurable(self) -> None:
        """兩個平台各自斷言自己那一半——刻意**不用 skip**：這一題在 POSIX 上不是
        「跳過」，而是「必須成功」，那正是落差本身。（用 skipUnless 會讓 POSIX 側
        一格覆蓋都沒有，也會多一個 skip 站點要進別包的普查表。）
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            dst = Path(tmpdir) / "ledger.yaml"
            src = Path(tmpdir) / "ledger.yaml.tmp"
            dst.write_text("old\n", encoding="utf-8")
            src.write_text("new\n", encoding="utf-8")
            with open(dst, encoding="utf-8"):        # 第三方**純讀者**持有 handle
                if sys.platform == "win32":
                    with self.assertRaises(PermissionError) as ctx:
                        os.replace(src, dst)
                    self.assertEqual(
                        ctx.exception.winerror,
                        _WINDOWS_OPEN_FILE_HOSTILE_PRIMITIVES["os.replace"],
                        "winerror 變了 ⇒ 上表登記的實測值已過期，請重新量並改表")
                else:
                    os.replace(src, dst)            # POSIX：恆成功，這就是落差
                    self.assertEqual(dst.read_text(encoding="utf-8"), "new\n")

    def test_the_primitive_inventory_covers_both_known_error_codes(self) -> None:
        """「換一個原語連錯誤碼都換了」這句話必須留在可查的形態裡。"""
        codes = {k: v for k, v in _WINDOWS_OPEN_FILE_HOSTILE_PRIMITIVES.items()
                 if v is not None}
        self.assertEqual(codes, {"os.replace": 5, "os.unlink": 32})
        self.assertTrue(_DIRENT_PRIMITIVES <= set(_WINDOWS_OPEN_FILE_HOSTILE_PRIMITIVES),
                        "掃描面出現了清單沒登記的原語 ⇒ 兩處會漂移")

    def test_unguarded_site_census_matches_the_ledger(self) -> None:
        skip_parts = {"__pycache__", ".git", ".venv", "venv", ".pytest_cache",
                      ".ruff_cache", ".mypy_cache", "node_modules"}
        # 🔴 R79 收斂包：**虛擬環境改以 `pyvenv.cfg` 這個標記偵測，不靠目錄名**。
        # 修前實況（當回合實測）：本掃描面是檔案系統 rglob，而排除清單只列了 `.venv`／`venv`
        # 兩個**我們剛好想得到的名字**；收斂包為了回填 ONBOARDING 快照建了一個叫
        # `cleanvenv` 的乾淨環境（gitignored、政策上就是該建的），這道普查的實測值當場由
        # 41 跳到 58 而閘門轉紅。也就是說這個數字是「這台機器上剛好有哪幾個 venv」的函數
        # ——換一台機器、換一個名字就換一個答案，而它被拿來當**雙向精確比對**的基準。
        # `pyvenv.cfg` 是 PEP 405 定義的 venv 根標記，與命名無關，也不必逐檔問 git。
        skip_roots = {
            cfg.parent for cfg in _REPO_ROOT.glob("*/pyvenv.cfg")
        } | {cfg.parent for cfg in _REPO_ROOT.glob("*/*/pyvenv.cfg")}
        census = {"live": 0}
        scanned = 0
        for py in _REPO_ROOT.rglob("*.py"):
            if skip_parts & set(py.parts):
                continue
            if any(root in py.parents for root in skip_roots):
                continue
            if _is_frozen_sdd_path(py.relative_to(_REPO_ROOT).as_posix()):
                continue
            scanned += 1
            data = py.read_bytes()
            # 先以 bytes 快篩再 AST 解析：全庫 .py 一次全解析實測要數分鐘，而帶這幾個
            # 名字的檔只有極少數。快篩的字面值是**必要條件**（AST 上的呼叫必然寫得出
            # 這個名字），不會讓射程縮小。
            if not any(tok in data for tok in (b"replace(", b"rename(", b"move(")):
                continue
            rel = py.relative_to(_REPO_ROOT).as_posix()
            for _rel, _ln, _prim, handled in dirent_primitive_sites(
                    data.decode("utf-8", errors="replace"), rel):
                if not handled:
                    census["live"] += 1
        self.assertGreaterEqual(
            scanned, 780,   # R79 實測 867 支 live `.py`（全庫 5,478 支裡其餘皆在凍結版）
            f"掃描面只有 {scanned} 支 .py——射程疑似被縮小（凍結版排除是刻意的，"
            "live 樹被排掉不是）")
        self.assertEqual(
            census, dict(_DIRENT_UNGUARDED_DEBT),
            "未處置站點數與帳不符。多一筆＝新增了一個在 Windows 上會被『別人開著這個"
            "檔』炸掉、且沒有任何處置的站點；少一筆＝有人修掉了，請把數字改小："
            f"實測 {census}",
        )

    # ── 紅綠自證（合成樣本）────────────────────────────────────────────────────

    def test_an_unhandled_replace_is_reported_and_a_handled_one_is_not(self) -> None:
        bare = "def f(tmp, path):\n    os.replace(tmp, path)\n"
        self.assertEqual(dirent_primitive_sites(bare, "x.py"),
                         [("x.py", 2, "os.replace", False)])
        handled = ("def f(tmp, path):\n    try:\n        os.replace(tmp, path)\n"
                   "    except PermissionError:\n        pass\n")
        self.assertEqual(dirent_primitive_sites(handled, "x.py"),
                         [("x.py", 3, "os.replace", True)])

    def test_a_timeouterror_only_handler_does_not_count_as_handling(self) -> None:
        """實際站點的形狀：包住它的 try 只捕 file_lock 的 TimeoutError。"""
        source = ("def f(tmp, path):\n    try:\n        os.replace(tmp, path)\n"
                  "    except TimeoutError:\n        pass\n")
        self.assertEqual(dirent_primitive_sites(source, "x.py")[0][3], False)

    def test_non_filesystem_replace_lookalikes_are_not_counted(self) -> None:
        """假紅會逼下一輪把整條鎖關掉：`dataclasses.replace(obj)` 與字串 replace 不算。"""
        for source in ("import dataclasses\n\n\ndef f(o):\n    return dataclasses.replace(o)\n",
                       'def f(s):\n    return s.replace("a", "b")\n'):
            with self.subTest(source=source):
                self.assertEqual(dirent_primitive_sites(source, "x.py"), [])

    def test_path_method_form_is_in_scope(self) -> None:
        """`tmp.replace(path)`（pathlib 形態）是本 repo 最常見的寫法，不得漏掃。"""
        self.assertEqual(
            dirent_primitive_sites("def f(tmp, path):\n    tmp.replace(path)\n", "x.py"),
            [("x.py", 2, "Path.replace", False)])


class TestExecBitIsGovernedViaTheGitIndex(unittest.TestCase):
    """exec bit 治理：只讀 git 索引模式（見上方區段 WHY）。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.modes = index_modes(_REPO_ROOT)

    def test_the_index_mode_channel_is_alive(self) -> None:
        """取數管道自證：壞掉時回空 dict，而空 dict 會讓下面兩題結構上恆綠。"""
        self.assertGreaterEqual(
            len(self.modes), 20000,
            f"`git ls-files -s` 只回 {len(self.modes)} 列——取數管道壞掉，"
            "本節其餘判準全部失去意義")
        self.assertIn(
            _INDEX_MODE_EXEC, set(self.modes.values()),
            "全 repo 一支 100755 都沒有 ⇒ 判準的『正例』側無從成立")

    def test_the_index_exec_set_matches_the_onboarding_policy_sentence(self) -> None:
        """🔴 DEF-101-205 自訂的解鎖條件本體（R80 落地）。

        該列自 R14 起 open 逾五十輪，逐字寫著解鎖條件＝「以 `git ls-files -s` 取出 mode
        `100755` 的檔案集合，與 `ONBOARDING.md` §6 執行權限政策句具名的 755 清單逐項互比
        （散文即 SSOT），不符即 rc=1」。**取數管道早就有了**（本類別 R79 落地時就在讀
        `git ls-files -s`），缺的一直是這一項比對——所以政策句與索引之間的漂移到今天為止
        一個訊號都沒有。

        Rule 9（為何這件事重要，而不只是「模式好看」）：exec bit 這一維在 Windows 上
        **結構性不可見**（本機 `core.filemode=false`，模式從不出現在 `git status`／
        `git diff`／任何 pre-commit 掃描裡），於是「哪支檔可以帶 755」這件事在本平台上
        只剩散文在守。散文不會轉紅。
        """
        scope, problem = exec_bit_prose_scope(
            (_REPO_ROOT / "ONBOARDING.md").read_text(encoding="utf-8")
        )
        self.assertIsNone(problem, problem)
        self.assertGreaterEqual(
            len(scope), 2,
            f"政策句只抽到 {list(scope)} —— 少於兩個 token 幾乎必然是抽取樣式壞掉，"
            "而不是政策真的縮到這麼小")
        self.assertEqual(exec_bit_scope_problems(self.modes, scope), [],
                         "\n".join(exec_bit_scope_problems(self.modes, scope)))

    def test_the_exec_scope_criterion_is_red_in_both_directions(self) -> None:
        """紅綠自證（合成輸入，不碰磁碟）：兩向各證一次，缺一向就不是雙向鎖。"""
        scope = ("tools/git-hooks/", "AutoClaude/tools/run_local_nightly.sh")
        green = {
            "tools/git-hooks/pre-push": _INDEX_MODE_EXEC,
            "AutoClaude/tools/run_local_nightly.sh": _INDEX_MODE_EXEC,
            "tools/x.sh": "100644",
        }
        self.assertEqual(exec_bit_scope_problems(green, scope), [])
        # 向①：範圍外冒出一支新的 100755。
        rogue = dict(green, **{"tools/x.sh": _INDEX_MODE_EXEC})
        self.assertEqual(len(exec_bit_scope_problems(rogue, scope)), 1)
        # 向②：散文列了一個「已經沒有任何 755」的住所 ⇒ 過期，必須被要求刪掉。
        self.assertEqual(
            len(exec_bit_scope_problems(green, (*scope, "AISDLC_SDD/.githooks/"))), 1)

    def test_the_prose_extractor_fails_loud_instead_of_silently_allowing(self) -> None:
        """散文被改寫時必須 fail-loud——靜默回空集合＝整道鎖蒸發（軟出口）。"""
        scope, problem = exec_bit_prose_scope("完全沒有那句政策的文件內容")
        self.assertEqual(scope, ())
        self.assertIsNotNone(problem)
        # 切段是必要的：不切段就會把同一句後半「其他 `.sh` 工具…索引 644」也收進白名單。
        scope, problem = exec_bit_prose_scope(
            "「755 入庫」範圍＝**`a/b/`**；其他 `c/d.sh` 工具一律索引 644")
        self.assertIsNone(problem)
        self.assertEqual(scope, ("a/b/",))
        # 成對切分：兩個 token 之間那段含 `/` 的散文**不得**被配成第三個 token。
        scope, problem = exec_bit_prose_scope(
            "「755 入庫」範圍＝**`a/b/` 由 x 執行、`bash` 呼叫 e/f 者除外＋`c/d.sh`**")
        self.assertIsNone(problem)
        self.assertEqual(scope, ("a/b/", "c/d.sh"))
        # 反引號未成對 ⇒ fail-loud，不得靜默給出一組看似合理的 token。
        scope, problem = exec_bit_prose_scope("「755 入庫」範圍＝**`a/b/ 忘了收尾**")
        self.assertEqual(scope, ())
        self.assertIsNotNone(problem)

    def test_docs_that_teach_bare_sh_invocation_point_at_executable_files(self) -> None:
        docs: dict[str, str] = {}
        for rel in self.modes:
            if not rel.lower().endswith(".md"):
                continue
            path = _REPO_ROOT / rel
            if not path.is_file():
                continue
            data = path.read_bytes()
            if b"./" not in data or b".sh" not in data:  # 先以 bytes 快篩再解碼
                continue
            docs[rel] = data.decode("utf-8", errors="replace")
        offenders = bare_sh_doc_offenders(docs, self.modes)
        live = [o for o in offenders if not _is_frozen_sdd_path(o[0])]
        frozen = [o for o in offenders if _is_frozen_sdd_path(o[0])]
        self.assertEqual(
            [f"{d}:{n} -> {t}" for d, n, t in live], [],
            "文件教 mac/Linux 使用者裸跑一支索引模式不是 100755 的腳本 ⇒ 對方一 clone "
            "就 `Permission denied`（rc=126），而 Windows 側因 core.filemode=false "
            "永遠看不到這件事。修法：把 `./x.sh` 改寫成 `bash x.sh`（與同批文件其餘"
            "各處一致），或以 `git update-index --chmod=+x` 把該檔改成 100755：\n"
            + "\n".join(f"{d}:{n} -> {t}" for d, n, t in live),
        )
        self.assertEqual(
            len(frozen), _BARE_SH_DOC_DEBT_FROZEN,
            f"凍結版存量由 {_BARE_SH_DOC_DEBT_FROZEN} 變成 {len(frozen)}。"
            "多一筆＝新增同型缺陷；少一筆＝有人動了 Copy-on-Evolve 禁改的凍結版"
            "（那本身就是必須被看見的事件）。兩向都請回來改這個數字並說明理由。",
        )

    def test_executable_shell_scripts_start_with_a_shebang_and_carry_no_bom(self) -> None:
        """`[ -x ]` 在 Windows 的 Git Bash 上是**檔首內容猜測**（當回合實測：加 BOM
        即由 EXECUTABLE 翻成 NOT-EXEC，且 `chmod +x` 動不了它）⇒ 檔首多任何位元組，
        dispatcher 那道 `if [ -x "$target" ]` 就靜默 exit 0，整條 hook 鏈無聲失效。
        這是那條治理鏈在 Windows 側唯一還測得到的一半。
        """
        problems: list[str] = []
        for rel, mode in sorted(self.modes.items()):
            if mode != _INDEX_MODE_EXEC:
                continue
            path = _REPO_ROOT / rel
            if not path.is_file():
                continue
            # 刻意不寫 `[:N]`：寫死的切片長度默默假設「我要看的東西一定在前 N 個
            # 位元組內」，而 `startswith` 本來就只比對前綴、不需要那個假設
            # （`test_archive_defect_log.py::TestNoAssertionSamplesALiveDocumentWholesale`
            #  在守這條紀律，R79 收斂包實測它會對 `[:4]` 轉紅）。
            head = path.read_bytes()
            if head.startswith(b"\xef\xbb\xbf"):
                problems.append(f"{rel}: 檔首有 UTF-8 BOM ⇒ Git Bash 的 `[ -x ]` 判為 NOT-EXEC")
            elif not head.startswith(b"#!"):
                problems.append(f"{rel}: 索引模式 100755 但檔首不是 `#!` ⇒ 同上")
        self.assertEqual(problems, [], "\n".join(problems))

    # ── 紅綠自證（合成輸入，不動磁碟）──────────────────────────────────────────

    def test_a_doc_pointing_at_a_100644_script_is_flagged(self) -> None:
        docs = {"tools/README.md": "跑 `./tools/x.sh -d ~/p` 即可\n"}
        modes = {"tools/README.md": "100644", "tools/x.sh": "100644"}
        self.assertEqual(bare_sh_doc_offenders(docs, modes),
                         [("tools/README.md", 1, "tools/x.sh")])
        modes["tools/x.sh"] = _INDEX_MODE_EXEC
        self.assertEqual(bare_sh_doc_offenders(docs, modes), [])

    def test_the_repo_approved_form_bash_x_sh_is_not_flagged(self) -> None:
        """對照組：`bash x.sh` 不需要 exec bit，判它是假紅。"""
        docs = {"a.md": "跑 `bash tools/x.sh` 即可\n"}
        self.assertEqual(bare_sh_doc_offenders(docs, {"a.md": "100644",
                                                      "tools/x.sh": "100644"}), [])

    def test_scripts_outside_the_repo_are_not_judged(self) -> None:
        """範本／樣稿講的是讀者自己專案的腳本，對應不到 tracked 檔 ⇒ 不判。"""
        docs = {"a.md": "./scripts/deploy/deploy-all.sh production\n"}
        self.assertEqual(bare_sh_doc_offenders(docs, {"a.md": "100644"}), [])

    def test_the_frozen_predicate_actually_separates_the_two_groups(self) -> None:
        latest = _latest_root().name
        self.assertTrue(_is_frozen_sdd_path("AISDLC_SDD/AISDLC_SDD_v0.01/tools/README.md"))
        self.assertFalse(_is_frozen_sdd_path(f"AISDLC_SDD/{latest}/tools/README.md"))
        self.assertFalse(_is_frozen_sdd_path("tools/README.md"))


#: `.editorconfig` 的 `.ps1` 區塊自述的機械執行者 → 它必須真的在談的主題關鍵詞。
#: 只斷言「檔案存在」抓不到「檔案在、但守的是別的東西」（R75 判過的形態：當時
#: 具名的是一支只管 BOM 的鎖，卻被寫在「行尾」那一列）。
_EDITORCONFIG_PS1_ENFORCERS: dict[str, tuple[str, ...]] = {
    "AutoClaude/tools/hooks/check_ps1_encoding.py": ("\\r\\n", "PS_SUFFIXES", "BOM"),
    "tools/tests/test_platform_neutral_paths.py": ("ls-files", "--eol", "crlf"),
    "tools/tests/test_ps1_bom.py": ("BOM", ".ps1"),
}


class TestEditorconfigPs1BlockNamesItsEnforcers(unittest.TestCase):
    """`.editorconfig` 的 `.ps1` 區塊不得是純裝飾——它自述的執行者必須真的在。

    缺陷本體（R79／D-ps1eol #32）：`end_of_line = crlf` 與 `charset = utf-8-bom`
    這兩行被三份文件各自宣告，而實際寫檔的工具兩項都不遵守；讀到任何一份的人都會
    合理推論「這件事有人在管」。R79 補上執行者之後，這支鎖負責讓那份自述**不能
    無聲過期**：具名檔被改名／刪掉／換成守別的主題的東西，都會在這裡紅。
    """

    _EDITORCONFIG = _REPO_ROOT / ".editorconfig"

    def test_the_ps1_block_declares_crlf_and_bom(self) -> None:
        text = self._EDITORCONFIG.read_text(encoding="utf-8")
        self.assertIn("[*.{ps1,psm1,psd1}]", text, "`.ps1` 區塊不見了")
        block = text.split("[*.{ps1,psm1,psd1}]", 1)[1].split("\n[", 1)[0]
        self.assertIn("end_of_line = crlf", block)
        self.assertIn("charset = utf-8-bom", block)

    def test_every_named_enforcer_exists_and_guards_its_topic(self) -> None:
        text = self._EDITORCONFIG.read_text(encoding="utf-8")
        problems: list[str] = []
        for rel, keywords in _EDITORCONFIG_PS1_ENFORCERS.items():
            if rel not in text:
                problems.append(f"{rel}：`.editorconfig` 已不再指名它——兩邊必須同步")
                continue
            path = _REPO_ROOT / rel
            if not path.is_file():
                problems.append(f"{rel}：`.editorconfig` 指名了一個不存在的執行者（幽靈機械物）")
                continue
            body = path.read_text(encoding="utf-8", errors="replace")
            missing = [k for k in keywords if k not in body]
            if missing:
                problems.append(
                    f"{rel}：檔案在，但內容沒有在談它被指派的主題（缺 {missing}）"
                    "——「檔案存在」是必要條件不是充分條件")
        self.assertEqual(problems, [], "\n".join(problems))


# ══════════════════════════════════════════════════════════════════════════════
# 本輪 — 雙向注入語料矩陣（M5 的可重跑載具；此前語料零落點、結構上不可逐輪比較）
# ══════════════════════════════════════════════════════════════════════════════
# 缺陷本體：M5「雙向注入攔截率」的量測配方寫著「每輪跑固定形制 N=10 注入矩陣」，
# 但語料本身**沒有任何落點**——每輪重新發明、量完就丟。R74 宣稱的六類基線全庫查無，
# 於是那個數字結構上不可跨輪比較（`DEF-101-018` 同型：不可重現的存量數字）。
#
# 本表把語料落成**字串常數**（不是檔案：違規樣本不留在樹裡）並逐題釘住「現在有沒有
# 被攔下」。兩個方向都會說話：
#   · 某題由攔得到變成攔不到 ⇒ 判準退化，紅；
#   · 某題由攔不到變成攔得到 ⇒ 有人補了判準，也紅，訊息要求把該題改成 True。
# 後者刻意不放行——「進步沒有被記錄」就是下一輪又要重新發明語料的起點。
#
# 🔴 注入點固定為**生產碼**路徑：R68-34 判過「只掃測試樹」的偏差，語料若掛在測試樹
#   路徑上，量到的是一個比實況樂觀的數字。
_INJECTION_TARGET_REL = "AutoClaude/autoclaude/infra/adapters/injected_probe.py"
#: 本檔自身也在掃描面內，故語料中會被**行掃描型**判準命中的字面值一律拆寫。
_DRIVE_FRAG = "D" + ":/repo/out"
_PATHEXT_FRAG = "PATH" + "EXT"


def _injection_criteria() -> dict[str, Callable[[str, str], tuple[list[str], list[str]]]]:
    """本檔全部判準的統一入口——語料逐題過**每一道**，不是只過一道。"""
    return {
        "drive-literal": scan_drive_literal,
        "intree-tmpdir": scan_intree_tmpdir,
        "posix-abs-assert": scan_posix_abs_asserts,
        "call-obj-repr": scan_call_obj_repr,
        "path-str-identity": scan_path_str_identity,
        "pathext-guard": scan_unguarded_pathext,
        "text-io-encoding": scan_missing_encoding,
        "foreign-platform-api": scan_foreign_platform_api,
    }


#: (題號, 方向, 語料, 目前是否至少被一道判準攔下)
_XPLAT_INJECTION_CORPUS: tuple[tuple[str, str, str, bool], ...] = (
    # ── 方向甲：在 mac 上寫得出來、到 Windows 會壞 ──────────────────────────
    ("a1-posix-sep-concat", "mac→Win",
     'def f(root, name):\n    return root + "/" + name\n', False),
    ("a2-tmp-hardcode", "mac→Win",
     'OUT = "/tmp/autoclaude.log"\n', False),
    ("a3-getlogin", "mac→Win",
     "def f():\n    return os.getlogin()\n", True),
    ("a4-pwd-module", "mac→Win",
     "import pwd\n\n\ndef f(uid):\n    return pwd.getpwuid(uid).pw_name\n", True),
    ("a5-chmod-exec", "mac→Win",
     "def f(p):\n    os.chmod(p, 0o755)\n", False),
    ("a6-fork", "mac→Win",
     "def f():\n    return os.fork()\n", True),
    ("a7-killpg-sigkill", "mac→Win",
     "def f(pgid):\n    os.killpg(pgid, signal.SIGKILL)\n", True),
    ("a8-shebang-exec", "mac→Win",
     'def f(sub):\n    return sub.run(["./tools/local_ci_gate.sh"])\n', False),
    ("a9-lf-only-write", "mac→Win",
     'def f(p, body):\n    p.write_text(body, encoding="utf-8")\n', False),
    ("a10-symlink", "mac→Win",
     "def f(src, dst):\n    os.symlink(src, dst)\n", True),
    # ── 方向乙：在 Windows 上寫得出來、到 mac 會壞 ──────────────────────────
    ("b1-drive-literal", "Win→mac", f'ROOT = "{_DRIVE_FRAG}"\n', True),
    ("b2-backslash-join", "Win→mac",
     'def f(root, name):\n    return root + "\\\\" + name\n', False),
    ("b3-pathext", "Win→mac",
     f'def f():\n    return os.environ["{_PATHEXT_FRAG}"].split(";")\n', True),
    ("b4-exe-suffix", "Win→mac",
     'def f(name):\n    return name + ".exe"\n', False),
    ("b5-cp950-encoding", "Win→mac",
     'def f(p):\n    return p.read_text(encoding="cp950")\n', False),
    ("b6-no-encoding", "Win→mac",
     "def f(p):\n    return p.read_text()\n", True),
    ("b7-winreg", "Win→mac",
     "import winreg\n\n\ndef f():\n    return winreg.HKEY_LOCAL_MACHINE\n", True),
    ("b8-schtasks", "Win→mac",
     'def f(sub):\n    return sub.run(["schtasks", "/query"], check=False)\n', False),
    ("b9-startfile", "Win→mac", "def f(p):\n    os.startfile(p)\n", True),
    ("b10-case-insensitive", "Win→mac",
     'def f(a, b):\n    return a.lower() == b.lower()\n', False),
    ("b11-powershell-shell", "Win→mac",
     'def f(sub, c):\n    return sub.run(["powershell.exe", "-Command", c],\n'
     "                   capture_output=True, text=True)\n", False),
    ("b12-msvcrt", "Win→mac",
     "import msvcrt\n\n\ndef f():\n    return msvcrt.getch()\n", True),
)


def live_interception() -> dict[str, tuple[int, int]]:
    """兩個方向各自的 `(攔截數, 題數)` **現場實算值**——M5 那個數字的唯一權威來源。

    抽成公開函式的理由（R78 ARCH-05）：M5 的攔截率此前只以散文寫在三份治理文件裡，
    而三處全部停在**修復前**的值（同一個 commit 落地的第六道判準已經把數字推上去，
    文件卻低報自己的成果）。文件低報看似無害，代價在下一輪：下一位讀者拿載具一跑，
    會看到「一輪暴衝」而去找一個不存在的原因。數字從此**只准由本函式產生**，
    文件寫指令不寫數字（同 M1 那一列 `[Scan-H triplet]` 的手法）。
    """
    totals: dict[str, list[int]] = {}
    for _case_id, direction, source, _expected in _XPLAT_INJECTION_CORPUS:
        slot = totals.setdefault(direction, [0, 0])
        slot[1] += 1
        if injection_hits(source):
            slot[0] += 1
    return {d: (v[0], v[1]) for d, v in totals.items()}


def injection_hits(source: str) -> list[str]:
    """語料被哪幾道判準攔下（排序後的判準名清單）。純函式，供矩陣與統計共用。"""
    hits: list[str] = []
    for name, scanner in _injection_criteria().items():
        try:
            offenders, _stale = scanner(source, _INJECTION_TARGET_REL)
        except (SyntaxError, ValueError):
            continue
        if offenders:
            hits.append(name)
    return sorted(hits)


class TestXplatInjectionMatrix(unittest.TestCase):
    """雙向注入語料矩陣——M5 那個數字的唯一落點。"""

    @classmethod
    def setUpClass(cls) -> None:
        # 報表行刻意全 ASCII（同 `[Scan-H triplet]` 的理由：消費者含 codepage 950 的排程環境）。
        # 這一行就是 M5「不寫死數字、指向載具」的那個載具出口。
        live = live_interception()
        cls.live = live
        print("[Xplat injection matrix] " + " ".join(
            f"{d.replace('→', '2')}={hit}/{total}" for d, (hit, total) in sorted(live.items())
        ))

    def test_every_sample_matches_its_recorded_verdict(self) -> None:
        drift: list[str] = []
        for case_id, direction, source, expected in _XPLAT_INJECTION_CORPUS:
            hits = injection_hits(source)
            if bool(hits) != expected:
                verb = "現在攔得到了（請把該題改成 True）" if hits else "現在攔不到了（判準退化）"
                drift.append(f"{case_id}［{direction}］{verb}；命中判準={hits}")
        self.assertEqual(
            drift, [],
            "注入語料矩陣與釘住的判決不符。兩個方向都必須回來改這張表——"
            "「進步沒有被記錄」就是下一輪又要重新發明語料的起點：\n" + "\n".join(drift),
        )

    def test_the_corpus_covers_both_directions_and_is_not_shrinking(self) -> None:
        """語料本身不得縮水（`每輪強制抽換 ≥2 題防過擬合` 的前提是題數不掉）。"""
        directions = {d for _c, d, _s, _e in _XPLAT_INJECTION_CORPUS}
        self.assertEqual(directions, {"mac→Win", "Win→mac"})
        self.assertGreaterEqual(len(_XPLAT_INJECTION_CORPUS), 22, "語料題數縮水")
        ids = [c for c, _d, _s, _e in _XPLAT_INJECTION_CORPUS]
        self.assertEqual(len(ids), len(set(ids)), "題號重複 ⇒ 逐題比較會對錯位")

    def test_the_interception_rate_only_improves(self) -> None:
        """逐輪可比的那個數字：兩個方向各自的攔截數，只准上升。

        釘的是**當回合實測**：下面 `floors` 那兩個數字**就是**那份實測，本 docstring
        刻意不再抄一份（R78 ARCH-05：M5 的攔截率此前散在三份文件裡各抄一份，三處全部
        停在修復前的值）。想知道現值就跑本測試——`setUpClass` 會印 `[Xplat injection
        matrix]`。R77 動工前 mac→Win 那一格是零：整類對面平台專屬 API 此前無任何判準。
        """
        floors = {"mac→Win": 5, "Win→mac": 6}
        caught = {d: hit for d, (hit, _total) in live_interception().items()}
        for direction, floor in floors.items():
            with self.subTest(direction=direction):
                self.assertGreaterEqual(
                    caught[direction], floor,
                    f"{direction} 攔截數由 {floor} 掉到 {caught[direction]} ⇒ 判準退化",
                )
                self.assertEqual(
                    caught[direction], floor,
                    f"{direction} 攔截數由 {floor} 升到 {caught[direction]}——"
                    "請把本表的下限同步上修，否則下一次退化會被舊值遮住",
                )
        self.assertEqual(
            _encoding_markers(f"x = 1  # {_ENCODING_OK_MARKER} 自家 WHY\n"),
            {1: "自家 WHY"}, "本判準認不出自己的標記 ⇒ 上一條變成恆真的假綠")


# ══════════════════════════════════════════════════════════════════════════════
# R80（包 B / S4）— 跨平台危害類：訂正兩筆假事實 ＋ 三個新家族上鎖
# ══════════════════════════════════════════════════════════════════════════════
# 本段一次處理四件同源的事，全部長在「鐵律三對照表」這個治理面上：
#
#  ① **低報分子**（S4-01，判準在本檔最後一節）。表上「大小寫敏感度」列自陳無機械物，
#     而 NTFS 大小寫碰撞判準 `tools/check_ntfs_paths.py` 的正規化鍵早就存在、且接在
#     pre-commit 與四支 CI workflow 上。舊的覆蓋率棘輪只讀那張表本身，於是「表說沒有、
#     實際有」這個方向**結構上失明**。
#
#  ② **有鎖在守假話**（S4-02）。表上「行尾（`.py` 方向）」列自陳無機械物——不真。
#     機械物在（`TestWorktreeEolMatchesPolicy`），只是被 `_EOL_LF_SCOPE` 這個常數窄化
#     成只看 `.sh`／`.bash`，而且 `test_the_policy_follows_the_declaration_instead_of_a_copy`
#     還有一條 `assertNotIn(".py", policy)` **釘死它必須放行**。這比沒有鎖更難看見：
#     檔案在、判準在、測試全綠，只有讀完那個常數才知道 `.py` 從來不在射程裡。
#
#  ③ **修法方向被規模否決**（S4-03）。全庫工作樹行尾與 `.gitattributes` 宣告不符者
#     **18,255 支**（不是表上那個只講 `.py` 的 4,176），其中**絕大多數**落在
#     Copy-on-Evolve 凍結面 ⇒「全部就地轉 LF」不是修法，是打破凍結政策。正解是把
#     凍結面與活躍面**分開處置**：活躍面止血（新漂移必紅）、凍結面誠實登記為欠債。
#
#  ④ 兩個此前零判準的新危害家族：**shebang ＋ 非 LF 行尾**（S4-08）與
#     **naive 本地時間戳被持久化**（S4-07），加上 PowerShell 側的**站點級**判準
#     （S4-04／S4-05）。三者共同的性質是「今天幾乎沒有存量，缺的是寫入面的門」。
#
# 🔴 本段所有數字都是**當回合實測**、不是常數：欠債釘子旁邊寫的就是那份實測，
#    判準失效時失敗訊息會把現值印出來（同本檔 `_scan_roots()` 的既有慣例）。


# ── 共用：tracked 檔案的工作樹行尾（現查一次）─────────────────────────────────
@functools.lru_cache(maxsize=1)
def tracked_eol_rows() -> tuple[tuple[str, str], ...]:
    """全庫 tracked 檔的 `(路徑, 工作樹行尾)`。取數管道壞掉即 fail-loud。

    與 `TestWorktreeEolMatchesPolicy._ls_files_eol()` 的差別：那一支只問政策表內那幾個
    副檔名（`--` pathspec 過濾），本支要**全庫**——③ 的規模判斷不能只看腳本族。
    """
    proc = subprocess.run(
        ["git", "-C", str(_REPO_ROOT), "ls-files", "--eol"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"git ls-files --eol 失敗（rc={proc.returncode}；stderr={proc.stderr.strip()!r}）"
            "——本段每一道判準的輸入沒了，不是「沒有違規」")
    return tuple(parse_ls_files_eol(proc.stdout))


def eol_drift_rows(
    rows: tuple[tuple[str, str], ...], declared: dict[str, str]
) -> tuple[list[str], list[str]]:
    """`(凍結面漂移, 活躍面漂移)`——工作樹行尾 ≠ `.gitattributes` 宣告的 tracked 檔。

    `none`（空檔／無換行）不算漂移：無從違反。分帳用本檔既有的 `_is_frozen_sdd_path`
    （LATEST **不算**凍結——它是活躍面，Copy-on-Evolve 只凍結歷史版）。
    """
    frozen_side: list[str] = []
    active_side: list[str] = []
    for path, worktree in rows:
        want = declared.get(path_suffix(path))
        if want is None or worktree in (want, "none", ""):
            continue
        (frozen_side if _is_frozen_sdd_path(path) else active_side).append(path)
    return frozen_side, active_side


def debt_band_verdict(label: str, actual: int, ceiling: int) -> str | None:
    """欠債的**雙邊帶**：超過上限＝新增漂移；掉太多＝該重釘。`None`＝在帶內。

    🔴 為何不用「雙向精確比對」（本檔其餘欠債釘子的慣例）：那個慣例成立的前提是欠債面
    **只有登記者會動**（凍結版文件、具名站點集合）。本判準的欠債面是數百支活躍原始碼的
    行尾，任何一個並行工作包用工具覆寫一支檔就會讓它 -1 ⇒ 精確比對會把「別人順手修好
    一支」判成紅燈，而假紅的下場一律是整道鎖被關掉。下界因此帶 slack；但 slack 是
    **有界**的（≥8 或上限的七分之一），大規模清理仍必須回來重釘，欠債不會靜靜地停在
    一個早就過期的數字上。
    """
    if actual > ceiling:
        return (f"{label}：實測 {actual} 超過欠債上限 {ceiling} ⇒ **新增**了行尾漂移。"
                "修法不是把上限調高——以宣告的行尾重存那幾支檔（`.py` 是 LF）")
    floor = ceiling - max(8, ceiling // 7)
    if actual < floor:
        return (f"{label}：實測 {actual} 已低於重釘下界 {floor}（上限 {ceiling}）⇒ 欠債"
                f"已清掉一大截，請把上限重釘為 {actual}，否則下一次退化會被舊值遮住")
    return None


# ── ②③ 活躍面原始碼行尾止血 ───────────────────────────────────────────────────
#: 本判準的射程：**活躍面**（非凍結 SDD 版）的 `.py`。
#: 刻意不擴到 `.md`／`.yaml`：本表這一列的主題是「原始碼行尾」，而 `.md` 的 CRLF 不會
#: 讓任何東西跑不起來——擴大主題會讓欠債數字失去可讀性，也讓止血點失焦。
_ACTIVE_SOURCE_EOL_SUFFIX = ".py"
#: 活躍面 `.py` 行尾漂移的欠債上限（落地當回合實測值；雙邊帶見 `debt_band_verdict`）。
_ACTIVE_PY_EOL_DEBT_CEILING = 220
#: 凍結面（v0.01~v0.29）`.py` 行尾漂移數——**不判、只登記**。Copy-on-Evolve 禁改；
#: 這個數字的用途是讓「為什麼不一次全轉 LF」變成可查的量，而不是散文。
_FROZEN_PY_EOL_DEBT_CEILING = 3956


class TestActiveSourceEolIsRatchetedSeparatelyFromTheFrozenSurface(unittest.TestCase):
    """活躍面 `.py` 行尾止血 ＋ 凍結面誠實登記（見本段 WHY ②③）。

    這一列此前在鐵律三對照表上寫「無機械物」——**不真**。機械物一直都在
    （`TestWorktreeEolMatchesPolicy`），只是 `_EOL_LF_SCOPE` 把射程窄化成 `.sh`／`.bash`，
    而且該類的 `test_the_policy_follows_the_declaration_instead_of_a_copy` 還有一條
    `assertNotIn(".py", policy)` 把「`.py` 必須被放行」釘成契約。本類別是那一格的牙齒：
    **不動那道腳本閘的射程**（擴進去會讓它一上線就吃四千筆凍結面欠債而必被關掉），
    改以獨立射程承接 `.py`，並把凍結／活躍分開記帳。
    """

    def _declared(self) -> dict[str, str]:
        return declared_eol(_GITATTRIBUTES_PATH.read_text(encoding="utf-8"))

    def test_active_surface_python_eol_does_not_grow(self) -> None:
        rows = tracked_eol_rows()
        self.assertGreater(len(rows), 20000,
                           f"tracked 列數異常少（{len(rows)}）⇒ 取數管道疑似壞掉")
        declared = self._declared()
        self.assertEqual(declared.get(_ACTIVE_SOURCE_EOL_SUFFIX), "lf",
                         "`.gitattributes` 對 .py 的宣告變了 ⇒ 本判準的前提要重新確認")
        frozen_side, active_side = eol_drift_rows(rows, declared)
        active_py = [p for p in active_side if p.endswith(_ACTIVE_SOURCE_EOL_SUFFIX)]
        frozen_py = [p for p in frozen_side if p.endswith(_ACTIVE_SOURCE_EOL_SUFFIX)]
        problems = [
            v for v in (
                debt_band_verdict("活躍面 .py 行尾漂移", len(active_py),
                                  _ACTIVE_PY_EOL_DEBT_CEILING),
                debt_band_verdict("凍結面 .py 行尾漂移", len(frozen_py),
                                  _FROZEN_PY_EOL_DEBT_CEILING),
            ) if v is not None
        ]
        self.assertEqual(
            problems, [],
            "🔴 `git status` 對這種漂移**結構上看不見**（checkin 正規化只作用於 index，"
            "兩側套同一份規則）；CI 也看不見（`actions/checkout` 必定重新 smudge）。"
            "唯一看得見的是本機工作樹這一欄：\n" + "\n".join(problems)
            + f"\n（現值：活躍 {len(active_py)} 支、凍結 {len(frozen_py)} 支）",
        )

    def test_the_repo_wide_scale_is_measured_not_quoted(self) -> None:
        """③：規模是量出來的。全庫漂移的**絕大多數**必須落在凍結面。

        這一條守的是一個修法方向：只要凍結面仍是大宗，「全部就地轉 LF」就不是修法而是
        打破 Copy-on-Evolve。哪天這個比例反轉（活躍面成為大宗），本測試會紅，而那個紅燈
        的意思是「該重新決定修法了」，不是「有人弄壞了什麼」。
        """
        frozen_side, active_side = eol_drift_rows(tracked_eol_rows(), self._declared())
        total = len(frozen_side) + len(active_side)
        self.assertGreater(total, 0, "全庫零漂移？請確認取數管道（本判準不該恆綠）")
        ratio = len(frozen_side) / total
        self.assertGreater(
            ratio, 0.8,
            f"凍結面佔比掉到 {ratio:.2%}（凍結 {len(frozen_side)}／活躍 {len(active_side)}"
            f"／全庫 {total}）⇒ 主要漂移已在可改的活躍面，"
            "「分開處置」這個修法前提不再成立，請重新裁決",
        )

    def test_the_narrowing_constant_is_still_the_reason_this_class_exists(self) -> None:
        """自錨：哪天有人把 `.py` 補進 `_EOL_LF_SCOPE`，本類別就重複了、該被刪。

        沒有這一條，兩道射程會靜靜地重疊，而重疊的鎖只有在其中一道紅的時候才會被發現。
        """
        self.assertNotIn(
            _ACTIVE_SOURCE_EOL_SUFFIX, _EOL_LF_SCOPE,
            "`.py` 已進入 `_EOL_LF_SCOPE` ⇒ 腳本閘已承接這個副檔名，"
            "請刪掉本類別（並確認它承接時有處理凍結面約四千支欠債）")

    def test_the_band_has_teeth_in_both_directions(self) -> None:
        """判準自證（合成值，不動磁碟）：兩個方向都要判得出來。"""
        self.assertIsNone(debt_band_verdict("x", 220, 220))
        self.assertIn("新增", debt_band_verdict("x", 221, 220) or "")
        self.assertIn("重釘", debt_band_verdict("x", 100, 220) or "")
        # slack 有下界：小欠債面掉 1 支不該逼人重釘（否則並行工作包一動就紅）
        self.assertIsNone(debt_band_verdict("x", 9, 10))


# ── ④-a shebang ⇒ 必須是 LF ──────────────────────────────────────────────────
# 缺陷本體：`#!/usr/bin/env python3` 加上 CRLF 行尾，POSIX kernel 會把 `\r` 一起當成
# 直譯器名的一部分 ⇒ `env: 'python3\r': No such file or directory`。本 repo 今天
# **30 支 `.py` 已同時成立**（shebang ＋ CRLF），沒有炸掉純粹是因為它們的 git 索引模式
# 都不是 100755 ⇒ 沒有人真的去 `./x.py` 執行它。**那是偶然，不是設計**：
# `TestExecBitIsGovernedViaTheGitIndex` 那一節記載的正是「文件教人裸跑、索引模式卻是
# 100644」這個家族——哪天有人把 exec bit 補對（那是**正確**的修法），這 30 支就會在
# mac/Linux 上一起變成 rc=127，而修 exec bit 的人完全看不到行尾這一半。
#
# 🔴 判準刻意是**shebang × 行尾**的交集而不是各自一半：單看行尾，凍結面上萬支要判
# （不可能）；單看 exec bit，今天零違規（已有鎖）。交集才是「一補另一半就炸」的那一組，
# 而它小到可以逐檔具名。
#: 活躍面（含 LATEST）今天仍成立的站點——**具名、雙向精確**：多一筆＝新增同型缺陷，
#: 少一筆＝已修好（請連同本集合一起刪，那是寫下來的動作）。
_SHEBANG_NON_LF_ACTIVE_DEBT: dict[str, str] = {
    "AISDLC_SDD/AISDLC_SDD_v0.30/tools/arch_fitness/arch_fitness.py": (
        "LATEST 版（非凍結、可改）。修法＝以 LF 重存該檔；未於本輪動手的理由是它不在"
        "本包的檔案所有權內，已列入交棒"
    ),
}
#: 凍結面（v0.01~v0.29）同型站點數——Copy-on-Evolve 禁改，只登記不判。
_SHEBANG_NON_LF_FROZEN_DEBT = 29


def shebang_non_lf_sites(
    rows: tuple[tuple[str, str], ...], repo_root: Path
) -> tuple[list[str], list[str]]:
    """`(凍結面, 活躍面)`——首行是 `#!` 而工作樹行尾不是 LF 的 tracked 檔。

    讀**位元組**而非文字：這一題問的就是位元組（`\\r` 有沒有黏在直譯器名後面），
    以 text mode 讀會被 universal newlines 就地吃掉，判準會恆綠。
    """
    frozen_side: list[str] = []
    active_side: list[str] = []
    for path, worktree in rows:
        if worktree in ("lf", "none", ""):
            continue
        try:
            with (repo_root / path).open("rb") as handle:
                head = handle.readline(256)
        except OSError:
            continue
        if not head.startswith(b"#!"):
            continue
        (frozen_side if _is_frozen_sdd_path(path) else active_side).append(path)
    return frozen_side, active_side


class TestShebangImpliesLfLineEndings(unittest.TestCase):
    """`#!` ＋ 非 LF ＝ POSIX 上 `env: '…\\r': No such file or directory`（見上方 WHY）。"""

    def test_no_new_shebang_file_carries_a_non_lf_line_ending(self) -> None:
        frozen_side, active_side = shebang_non_lf_sites(tracked_eol_rows(), _REPO_ROOT)
        self.assertEqual(
            sorted(active_side), sorted(_SHEBANG_NON_LF_ACTIVE_DEBT),
            "活躍面 shebang×非 LF 站點集合與登記不符。多出來的是**新增**的同型缺陷"
            "（請以 LF 重存該檔）；少掉的是已修好（請自 `_SHEBANG_NON_LF_ACTIVE_DEBT` "
            "刪除——欠債清單不得靠慣性活著）",
        )
        self.assertEqual(
            len(frozen_side), _SHEBANG_NON_LF_FROZEN_DEBT,
            f"凍結面同型站點由 {_SHEBANG_NON_LF_FROZEN_DEBT} 變成 {len(frozen_side)}"
            "——凍結面理應不動；若是 LATEST 版號推進造成整批位移，請重釘這個數字",
        )

    def test_the_criterion_reads_bytes_not_decoded_text(self) -> None:
        """判準自證：真的寫一支 CRLF shebang 檔，確認在位元組層看得到 `\\r`。

        不是為了測作業系統，是為了證明**這個判準讀的是位元組**——以 text mode 讀會被
        universal newlines 吃掉 `\\r`，判準會恆綠而沒有任何人發現。
        """
        with tempfile.TemporaryDirectory() as td:
            probe = Path(td) / "probe.py"
            probe.write_bytes(b"#!/usr/bin/env python3\r\nprint(1)\r\n")
            with probe.open("rb") as handle:
                raw = handle.readline(256)
            text_head = probe.read_text(encoding="utf-8").splitlines()[0]
        self.assertTrue(raw.startswith(b"#!"))
        self.assertTrue(raw.rstrip(b"\n").endswith(b"\r"),
                        "位元組層看不到 \\r ⇒ 本判準讀錯了層，會對整類缺陷恆綠")
        self.assertFalse(text_head.endswith("\r"),
                         "text mode 竟然留住了 \\r？那本註記的理由要重寫")

    def test_the_exec_bit_coincidence_is_named_not_relied_on(self) -> None:
        """今天沒炸的理由（索引模式不是 100755）必須是**可查的量**，不是口頭安慰。

        哪天 exec bit 被補對——那是正確的修法——這一條會紅，而它紅的意思是「另一半還沒
        修」。這正是本判準存在的理由：兩個各自正確的動作合起來會炸。
        """
        modes = index_modes(_REPO_ROOT)
        self.assertTrue(modes, "git ls-files -s 取數失敗 ⇒ 本條無從判定")
        frozen_side, active_side = shebang_non_lf_sites(tracked_eol_rows(), _REPO_ROOT)
        executable = [p for p in frozen_side + active_side
                      if modes.get(p) == _INDEX_MODE_EXEC]
        self.assertEqual(
            executable, [],
            "以下檔案同時具備 shebang、非 LF 行尾、100755 索引模式 ⇒ 三個條件到齊，"
            "mac/Linux 上 `./<檔>` 必 rc=127（`env: '…\\r'`）。行尾與 exec bit 兩半"
            "任一半修好都不夠：\n" + "\n".join(executable),
        )


# ── ④-b naive 本地時間戳被持久化 ─────────────────────────────────────────────
# 缺陷本體：`datetime.now()`（無 tz）產生的是**沒有 offset 的本地時間**，`.isoformat()`
# 之後寫進 checkpoint／YAML／JSON，讀回來再與另一個 naive `datetime.now()` 相減。那個
# 減法在**同一個 offset 內**是對的，跨 DST 切換就整整差一小時——而且是**靜默**的：
# 沒有例外、沒有 log，只是恢復時間錯一小時。AutoClaude Kernel 的 Token Guard 正是這個
# 形態（checkpoint 存 naive ISO、`auto_resume` 以 `resume_at - datetime.now()` 算還要等
# 幾秒）⇒ DST 那一天會**提早一小時**恢復。
#
# 🔴 為何本 repo 至今沒撞到：開發機時區是 Asia/Taipei（**不實施 DST**）。也就是說這個
# 缺陷在本機**結構上重現不了**——與 DEF-101-778「把一台機器的偶然事實寫成常數」同型，
# 只是這次的偶然事實是「我們的時區沒有夏令時間」。下面的自證測試因此**不動系統時區、
# 不動環境變數**，改以 `zoneinfo` 直接構造切換點：那是唯一在本機也跑得動、且對並行工作
# 包零副作用的重現方式。
#
# 判準（AST）：`datetime.now()`／`datetime.datetime.now()`／`utcnow()` **不帶任何引數**
# 且結果直接串 `.isoformat(...)` ⇒ 產出不帶 offset 的 ISO 字串。修法慣例＝
# `datetime.now().astimezone().isoformat()`（帶上 offset，字串自我描述）或
# `datetime.now(UTC).isoformat()`。
#
# 🔴 誠實劃界：
#   ❌ 測試檔不判（路徑含 `tests` 段或檔名 `test_*.py`）：測試造時間戳當 fixture，不進
#      持久層；納入會製造十餘筆需要逐一辯護的假紅。
#   ❌ 「存了 naive 再讀回來相減」的**讀**側不判——靜態追不到跨檔案的值流。本判準守的是
#      **產出端**，把不帶 offset 的字串擋在寫入之前；讀側今天由 `_NAIVE_TS_PERSIST_DEBT`
#      的具名站點承接（每一筆都寫明它餵給誰）。
_NAIVE_TS_OK_MARKER = "naive-ts-ok:"
_NAIVE_NOW_FUNCS = frozenset({"now", "utcnow"})


def _is_naive_now_call(node: ast.AST) -> bool:
    """`datetime.now()`／`datetime.datetime.now()`／`utcnow()`，且**未傳任何 tz**。"""
    if not (isinstance(node, ast.Call) and not node.args and not node.keywords):
        return False
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr in _NAIVE_NOW_FUNCS:
        return True
    return isinstance(func, ast.Name) and func.id in _NAIVE_NOW_FUNCS


def _naive_ts_markers(source: str) -> dict[int, str]:
    """{行號: WHY}——僅認 COMMENT token（字串字面值內的同形文字不當豁免）。"""
    markers: dict[int, str] = {}
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT and _NAIVE_TS_OK_MARKER in tok.string:
            markers[tok.start[0]] = tok.string.split(_NAIVE_TS_OK_MARKER, 1)[1].strip()
    return markers


def scan_naive_timestamp_persist(source: str, rel: str) -> tuple[list[str], list[str]]:
    """純函式核心：回傳 (offenders, stale_markers)。"""
    tree = ast.parse(source)
    markers = _naive_ts_markers(source)
    offenders: dict[int, str] = {}
    used: set[int] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr != "isoformat" or not _is_naive_now_call(node.func.value):
            continue
        if markers.get(node.lineno):
            used.add(node.lineno)
            continue
        offenders[node.lineno] = (
            f"{rel}:{node.lineno}: `now().isoformat()` 產出**不帶 offset** 的本地時間字串"
            "（存進 checkpoint／YAML 後讀回相減，跨 DST 切換整整差 3600 秒且完全靜默）"
            "——請改 `datetime.now().astimezone().isoformat()` 或 `datetime.now(UTC)`"
        )
    stale = [
        f"{rel}:{lineno}: {_NAIVE_TS_OK_MARKER} 標記 stale"
        f"（{'WHY 留空' if not why else '該行無被壓下的違規'}）"
        for lineno, why in sorted(markers.items())
        if lineno not in used or not why
    ]
    return [offenders[k] for k in sorted(offenders)], stale


def _is_test_file(rel: str) -> bool:
    parts = rel.split("/")
    return "tests" in parts or parts[-1].startswith("test_")


#: 具名欠債：今天仍在產出 naive ISO 字串的**生產**站點。逐筆寫明它餵給誰，讓「這一筆
#: 到底會不會害到人」是可讀的，而不是一個數字。雙向精確比對。
_NAIVE_TS_PERSIST_DEBT: dict[str, str] = {
    "AutoClaude/autoclaude/infra/repositories/file_state_repository.py": (
        "checkpoint.saved_at；讀側 auto_resume 以 `resume_at - datetime.now()` 相減 ⇒ "
        "這一筆就是 Kernel 會提早一小時恢復的那條路。不在本包所有權內，已交棒"
    ),
    "AutoClaude/autoclaude/infra/repositories/file_playbook_repository.py": (
        "playbook 快照時間戳；目前只做顯示與排序，同 offset 內排序不受影響"
    ),
    "AutoClaude/tools/pg_dump_to_yaml.py": (
        "dump metadata 的 started_at／finished_at（兩筆），只做人讀"
    ),
    "AISDLC_SDD/AISDLC_SDD_v0.30/tools/arch_fitness/arch_fitness.py": (
        "arch-fitness 報告的 timestamp 欄，只做人讀"
    ),
    ".claude/hooks/context_budget_guard.py": (
        "額度哨兵的武裝 log 行，只做人讀取證；但它是**跨時區可攜性**最差的一種"
        "——log 的讀者不一定在同一個 offset 下"
    ),
    # 🔴 以下七筆的處置說明刻意**不逐筆宣稱讀側行為**：本輪只逐檔確認了「產出端確實是
    # naive ISO」，沒有逐筆追讀側的消費者。寫「只做顯示」而沒真的追過，就是憑推測寫下
    # 一個看起來像結論的東西——那正是本 repo 反覆記載的失誤形態。逐筆追讀側列為交棒。
    "AutoClaude/autoclaude/infra/repositories/in_memory_playbook_repository.py":
        "與 file_playbook_repository 同形（記憶體後端）；讀側未逐一追，見上方註記",
    "AutoClaude/autoclaude/infra/repositories/in_memory_state_repository.py":
        "與 file_state_repository 同形（記憶體後端）；讀側未逐一追，見上方註記",
    "AutoClaude/autoclaude/models/escalation.py":
        "ESCALATION 事件時間戳；讀側未逐一追，見上方註記",
    "AutoClaude/autoclaude/plugins/sdd_governance_plugin.py":
        "SDD 治理事件時間戳；讀側未逐一追，見上方註記",
    "AutoClaude/autoclaude/utils/checkpoint_manager.py":
        "checkpoint 時間戳——與 file_state_repository 同一條恢復路徑，優先度同高",
    "AutoClaude/autoclaude/utils/notifier.py":
        "通知訊息時間戳；讀側未逐一追，見上方註記",
    "AutoClaude/autoclaude/utils/token_tracker.py":
        "token 用量紀錄時間戳；讀側未逐一追，見上方註記",
}


class TestNaiveLocalTimestampsAreNotPersisted(unittest.TestCase):
    """不帶 offset 的本地時間戳不得進持久層（見上方 WHY）。"""

    def test_no_new_site_persists_a_naive_local_timestamp(self) -> None:
        offenders: list[str] = []
        stale: list[str] = []
        parse_failures: list[str] = []
        hit_files: set[str] = set()
        scanned = 0
        for _label, files, _floor in _scan_units():
            for py in files:
                rel = py.relative_to(_REPO_ROOT).as_posix()
                if _is_test_file(rel):
                    continue
                try:
                    off, st = scan_naive_timestamp_persist(
                        py.read_text(encoding="utf-8"), rel)
                except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
                    parse_failures.append(f"{rel}: {type(exc).__name__}: {exc}")
                    continue
                scanned += 1
                stale.extend(st)
                if off:
                    hit_files.add(rel)
                    if rel not in _NAIVE_TS_PERSIST_DEBT:
                        offenders.extend(off)
        self.assertEqual(
            parse_failures, [],
            "以下 .py 無法 parse——掃描面不得靜默縮小：\n" + "\n".join(parse_failures))
        self.assertGreater(scanned, 300, f"只掃到 {scanned} 支非測試 .py ⇒ 掃描面疑似縮小")
        self.assertEqual(
            offenders, [],
            "新增了 naive 本地時間戳持久化站點（現行欠債見 `_NAIVE_TS_PERSIST_DEBT`）：\n"
            + "\n".join(offenders),
        )
        self.assertEqual(
            sorted(hit_files), sorted(_NAIVE_TS_PERSIST_DEBT),
            "欠債清單與實況不符：少掉的表示已修好（請自清單刪除，欠債不得靠慣性活著），"
            "多出來的表示新增了同型站點",
        )
        self.assertEqual(stale, [],
                         f"{_NAIVE_TS_OK_MARKER} 標記 stale：\n" + "\n".join(stale))

    def test_the_dst_gap_is_reproducible_without_touching_the_system_clock(self) -> None:
        """🔴 這一條是本判準的**理由本身**：跨 DST 的 naive 相減會差整整 3600 秒。

        本機時區 Asia/Taipei 不實施 DST ⇒ 這個缺陷在本機結構上重現不了。

        🔴 **不用 `zoneinfo.ZoneInfo("America/New_York")`**（第一版就是那樣寫的，當回合
        實測 `ZoneInfoNotFoundError`）：Windows 沒有系統 tz 資料庫，`zoneinfo` 要靠
        `tzdata` 這個**選配**套件，而本 repo 沒有裝它 ⇒ 那種寫法會讓這條在 Windows 上
        變成 ERROR、在 mac/Linux 上通過。本判準在守的就是「單平台判準不可無條件外推」，
        它自己第一版卻正是那個形態。改用固定 offset 直接構造 fall-back 的兩個瞬間：
        EDT(-04:00) 的 01:30 與 EST(-05:00) 的 01:30 相差正好一小時，而**丟掉 offset
        之後兩者完全相同**——這就是 DST 落回那一小時的全部語意，且零外部相依。
        """
        from datetime import datetime as _dt  # noqa: PLC0415
        from datetime import timedelta as _td  # noqa: PLC0415
        from datetime import timezone as _tz  # noqa: PLC0415

        # 2024-11-03 美東 fall back：01:30 出現兩次，先 EDT(-4) 後 EST(-5)。
        before = _dt(2024, 11, 3, 1, 30, tzinfo=_tz(-_td(hours=4)))
        after = _dt(2024, 11, 3, 1, 30, tzinfo=_tz(-_td(hours=5)))
        self.assertEqual((after - before).total_seconds(), 3600.0,
                         "帶 tz 的兩個時刻相減應為 3600 秒（真實經過的時間）")
        # 這就是 `.isoformat()` 沒有 offset 時，存檔／讀回之後剩下的東西：
        naive_before = before.replace(tzinfo=None)
        naive_after = after.replace(tzinfo=None)
        self.assertEqual(naive_before.isoformat(), naive_after.isoformat(),
                         "兩個相差一小時的時刻，naive ISO 字串**完全相同** ⇒ 資訊已遺失")
        self.assertEqual(
            (naive_after - naive_before).total_seconds(), 0.0,
            "naive 相減得到 0 秒（真實是 3600 秒）——Kernel 會據此提早一小時恢復")
        # 反向自證：修法慣例（帶 offset）把資訊留住，round-trip 後仍算得出 3600 秒
        self.assertNotEqual(before.isoformat(), after.isoformat())
        self.assertEqual(
            (_dt.fromisoformat(after.isoformat())
             - _dt.fromisoformat(before.isoformat())).total_seconds(),
            3600.0, "帶 offset 的 ISO 字串 round-trip 後仍算得出 3600 秒 ⇒ 修法真的有效")

    def test_the_criterion_has_teeth_and_does_not_overreach(self) -> None:
        """判準紅綠自證（合成字串，不留違規樣本於 repo）。"""
        red, stale = scan_naive_timestamp_persist(
            "from datetime import datetime\n"
            "def f():\n"
            "    return datetime.now().isoformat(timespec='seconds')\n", "fixture.py")
        self.assertEqual(len(red), 1, red)
        self.assertEqual(stale, [])
        for green in (
            "from datetime import datetime\n"
            "def f():\n    return datetime.now().astimezone().isoformat()\n",
            "from datetime import datetime, UTC\n"
            "def f():\n    return datetime.now(UTC).isoformat()\n",
            "from datetime import datetime\n"
            "def f():\n    return datetime.now()\n",
        ):
            with self.subTest(green=green.splitlines()[-1].strip()):
                self.assertEqual(scan_naive_timestamp_persist(green, "fixture.py")[0], [])
        marked, stale = scan_naive_timestamp_persist(
            "from datetime import datetime\n"
            "def f():\n"
            f"    return datetime.now().isoformat()  # {_NAIVE_TS_OK_MARKER} 純顯示\n",
            "fixture.py")
        self.assertEqual((marked, stale), ([], []))
        blank, stale = scan_naive_timestamp_persist(
            "from datetime import datetime\n"
            "def f():\n"
            f"    return datetime.now().isoformat()  # {_NAIVE_TS_OK_MARKER}\n",
            "fixture.py")
        self.assertEqual(len(blank), 1, "WHY 留空的標記不得生效")
        self.assertEqual(len(stale), 1, stale)


# ── ④-c PowerShell 站點級：Windows 專屬 `$env:` 與 `bash` 解析 ────────────────
# 缺陷本體（S4-04）：`$env:TEMP`／`$env:TMP` 在 Windows 一定有值，在 macOS/Linux 的
# PowerShell Core 上**不存在** ⇒ `Join-Path $env:TEMP '…'` 會直接
# `Cannot bind argument to parameter 'Path' because it is null` 拋例外（不是回空字串、
# 不是走 fallback，是整支腳本當場死掉）。命中的站點裡有一支是
# `AISDLC_SDD/<LATEST>/tools/init_project.ps1`——**框架發給使用者的安裝腳本**，也就是
# 別人第一次用這個框架跑的第一支程式。正解＝`[System.IO.Path]::GetTempPath()`
# （.NET API，三平台皆回真值）。
#
# 缺陷本體（S4-05）：`Get-Command bash` 在本機解析到 `C:\WINDOWS\system32\bash.exe`
# （WSL 佔位／真 WSL），repo 已為此立 SSOT `tools/lib/Find-GitBash.ps1`（含 system32
# 逐段排除）。今天**零違規**——所以這一格缺的不是存量掃描，是**站點級**的門：判準的
# 價值全部在「下一個人寫出裸解析時當場紅」，而不是在今天數出幾筆。
#
# 🔴 誠實劃界：
#   ❌ 只判 `$env:TEMP`／`$env:TMP` 這**兩個**變數，不判整個 `$env:*`。理由是「粗數」
#      本身就是這一格此前失真的原因：活躍 `.ps1` 剝註解後 `$env:` 粗抓 48 筆，其中
#      22 筆是**賦值**（`$env:X = …` 是設定不是讀取，任何平台都成立），剩下 26 筆讀取
#      分屬 11 個變數，而真正「在 POSIX 上會拋例外」的只有 TEMP／TMP 這一族。把 11 個
#      變數一起判會製造 20 餘筆需要逐一辯護的假紅，那種鎖活不過一輪。
#   ❌ 不判「這支腳本是不是 Windows 專用」——那件事沒有可靠的機械信號（檔名、路徑、
#      檔頭措辭都可以繞過）。改以具名欠債逐檔寫明「它是不是真的只在 Windows 跑」，讓那個
#      判斷是**寫下來的**而不是推斷出來的。
_PS_SITE_OK_MARKER = "ps-xplat-ok:"
#: 讀取（非賦值）Windows 專屬暫存目錄變數。`(?!\s*=)` 排除 `$env:TEMP = …` 的設定形態。
_WINDOWS_ONLY_ENV_READ_RE = re.compile(r"\$env:(TEMP|TMP)\b(?!\s*=)", re.IGNORECASE)
#: 裸解析 `bash`。唯一合法的家是下面那支 SSOT。
_BASH_RESOLUTION_RE = re.compile(
    r"Get-Command\s+['\"]?bash(?:\.exe)?['\"]?(?![\w.-])", re.IGNORECASE)
_BASH_RESOLUTION_SSOT = "tools/lib/Find-GitBash.ps1"
#: 具名欠債：今天仍直接讀 `$env:TEMP`／`$env:TMP` 的活躍 PowerShell 腳本。雙向精確比對。
_WINDOWS_ONLY_ENV_DEBT: dict[str, str] = {
    "tools/windows_smoke_local.ps1": (
        "Windows 專用（檔內自帶 MSYS 守衛與 PS 5.1 引擎守衛，在 POSIX 上本來就不執行）"
        "——保留現狀，但仍登記，避免它被當成「這種寫法沒問題」的樣板"
    ),
    "AISDLC_SDD/AISDLC_SDD_v0.30/tools/init_project.ps1": (
        "🔴 真曝險：框架發給使用者的安裝腳本，在 macOS/Linux 的 PS Core 上 "
        "`Join-Path $env:TEMP …` 直接拋 null 綁定例外。修法＝"
        "`[System.IO.Path]::GetTempPath()`。不在本包的檔案所有權內，已列入交棒"
    ),
}


def _active_ps_scripts() -> list[str]:
    """活躍面（非凍結 SDD 版）tracked PowerShell 腳本的 repo 相對路徑。"""
    return sorted(
        path for path, _eol in tracked_eol_rows()
        if path.lower().endswith((".ps1", ".psm1", ".psd1"))
        and not _is_frozen_sdd_path(path)
    )


def scan_ps_platform_sites(source: str, rel: str) -> tuple[list[str], list[str]]:
    """`(env 讀取站點, bash 裸解析站點)`——皆為 `rel:行號: 原行`。

    逐行剝 `#` 註解尾再判（與本檔第一道判準同一個 heuristic 與同一組取捨）；
    行尾 `# ps-xplat-ok: <WHY>` 豁免。
    """
    env_sites: list[str] = []
    bash_sites: list[str] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        if _PS_SITE_OK_MARKER in line:
            continue
        code = line.split("#", 1)[0]
        if _WINDOWS_ONLY_ENV_READ_RE.search(code):
            env_sites.append(f"{rel}:{lineno}: {line.strip()[:110]}")
        if _BASH_RESOLUTION_RE.search(code):
            bash_sites.append(f"{rel}:{lineno}: {line.strip()[:110]}")
    return env_sites, bash_sites


class TestPowerShellPlatformSensitiveSites(unittest.TestCase):
    """PowerShell 側的站點級跨平台判準（見上方 WHY）。"""

    def _scan_all(self) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        env_by_file: dict[str, list[str]] = {}
        bash_by_file: dict[str, list[str]] = {}
        scripts = _active_ps_scripts()
        # 下限＝落地當回合實測 20 支的八折。全庫 `.ps1` 有一百多支，但絕大多數住在凍結版
        # SDD 樹（本判準刻意不掃：Copy-on-Evolve 禁改，判了也只能開白名單）。
        self.assertGreater(len(scripts), 15,
                           f"活躍 PowerShell 腳本只掃到 {len(scripts)} 支 ⇒ 掃描面疑似縮小")
        for rel in scripts:
            source = (_REPO_ROOT / rel).read_text(encoding="utf-8-sig", errors="replace")
            env_sites, bash_sites = scan_ps_platform_sites(source, rel)
            if env_sites:
                env_by_file[rel] = env_sites
            if bash_sites:
                bash_by_file[rel] = bash_sites
        return env_by_file, bash_by_file

    def test_windows_only_temp_env_reads_are_all_accounted_for(self) -> None:
        env_by_file, _bash = self._scan_all()
        self.assertEqual(
            sorted(env_by_file), sorted(_WINDOWS_ONLY_ENV_DEBT),
            "`$env:TEMP`／`$env:TMP` 讀取站點與登記不符。多出來的是**新增**曝險"
            "（macOS/Linux 的 PS Core 上這兩個變數不存在，`Join-Path $env:TEMP …` 會直接"
            "拋 null 綁定例外）——請改用 `[System.IO.Path]::GetTempPath()`；少掉的表示"
            "已修好，請自 `_WINDOWS_ONLY_ENV_DEBT` 刪除。\n"
            + "\n".join(s for sites in env_by_file.values() for s in sites),
        )

    def test_bash_is_only_resolved_through_the_ssot(self) -> None:
        _env, bash_by_file = self._scan_all()
        offenders = {rel: sites for rel, sites in bash_by_file.items()
                     if rel != _BASH_RESOLUTION_SSOT}
        self.assertEqual(
            offenders, {},
            f"裸 `Get-Command bash` 只能出現在 `{_BASH_RESOLUTION_SSOT}`（唯一 SSOT，含"
            " system32／WSL 佔位版逐段排除）。本機實測裸解析拿到的是 WSL 佔位版，且反斜線"
            "路徑的分隔符會被吃掉（DEF-101-617/618）。請改用該 SSOT：\n"
            + "\n".join(f"{rel}: {sites}" for rel, sites in offenders.items()),
        )

    def test_the_ssot_itself_is_still_the_one_doing_the_resolution(self) -> None:
        """反空轉：SSOT 自己必須仍然命中，否則上一條是在對空集合宣布勝利。"""
        _env, bash_by_file = self._scan_all()
        self.assertIn(
            _BASH_RESOLUTION_SSOT, bash_by_file,
            f"{_BASH_RESOLUTION_SSOT} 內找不到 `Get-Command bash` ⇒ 要嘛 SSOT 換了實作"
            "（請把本判準的錨改掉），要嘛正則失效而整條判準已對全庫恆綠")

    def test_the_two_criteria_have_teeth(self) -> None:
        """判準紅綠自證（合成字串）。"""
        env_sites, bash_sites = scan_ps_platform_sites(
            "$tmp = Join-Path $env:TEMP 'x'\n"
            "$b = Get-Command bash -ErrorAction SilentlyContinue\n", "fixture.ps1")
        self.assertEqual((len(env_sites), len(bash_sites)), (1, 1))
        # 賦值不是讀取；`$env:TEMPDIR` 不是 TEMP；註解行與豁免標記行都不算
        clean, clean_bash = scan_ps_platform_sites(
            "$env:TEMP = 'tmpdir'\n"
            "$v = $env:TEMPDIR\n"
            "# $tmp = Join-Path $env:TEMP 'x'\n"
            f"$t = $env:TEMP  # {_PS_SITE_OK_MARKER} 合成豁免樣本\n"
            "$g = Get-Command bashful\n", "fixture.ps1")
        self.assertEqual((clean, clean_bash), ([], []))


# ══════════════════════════════════════════════════════════════════════════════
# R80（包 B / S4-01）— 鐵律三對照表：「無機械物」必須是**可證偽**的宣稱
# ══════════════════════════════════════════════════════════════════════════════
# 缺陷本體：覆蓋率棘輪（`test_doc_loc_baseline_freshness_r60.py` 的鐵律三對帳鎖）的分子
# 只讀那張表**自己說**有沒有機械物。於是它抓得到「有人把機械物欄改回無機械物」（分子
# 下降），也抓得到「指名一支不存在／守錯主題的檔」（過報分子），**唯獨抓不到一格從一
# 開始就填錯**——「表說沒有、實際有」這個方向結構上失明。
# 實例：「大小寫敏感度」列自陳無機械物，而 `tools/check_ntfs_paths.py` 的大小寫碰撞
# 正規化鍵早就存在（NFC → lowercase；`README.MD` 與 `README.md` 在 NTFS 上互相覆蓋），
# 且接在 pre-commit 與四支 CI workflow 上。低報分子的代價與過報一樣大：它讓下一輪有人
# 「補一支已經存在的鎖」，也讓「還有幾類沒人守」這個治理數字是假的。
#
# 判準：每一列自陳「無機械物」者，必須登記一組**證偽探針**——一組 token，凡在機械物的
# **已知住所**內出現於 `def`／`class` 定義行或模組層常數名，就是反證。命中落在「已審視
# 並判定不算」的檔案內時放行，但那個判定必須寫下來（考察軌跡本身就是產物）。
#
# 🔴 為何掃「定義名」而不是全文：全文比對對散文（註解裡順口提到主題）零抵抗力，而本檔
#    與 CLAUDE.md 自己就滿是這些詞——那種鎖第一天就會被假紅淹掉然後被整道關掉。機械物是
#    **被命名的東西**：它一定有 `def scan_*`／`class Test*`／`_DIRENT_UNGUARDED_DEBT`
#    這種識別字。
#    掃識別字是必要條件不是充分條件（抓得到「其實有人在守」，抓不到「守得很弱」），
#    與本 repo 既有的實質判準同一種誠實度。
_IRON_LAW3_MECHANISM_HOMES: tuple[str, ...] = (
    "tools/*.py", "tools/lib/*.py", "tools/tests/*.py", "tools/probe/*.py",
    ".claude/hooks/*.py", "AutoClaude/tools/hooks/*.py", "AutoClaude/tests/*.py",
)
#: 定義行／模組層常數名（機械物的識別字住所）。
_MECHANISM_DEF_RE = re.compile(
    r"^\s*(?:async\s+)?(?:def|class)\s+(\w+)|^(_?[A-Z][A-Z0-9_]{2,})\s*[:=]")
#: {表上的觸發項關鍵字: (證偽 token, {已審視並判定不算的檔案: 為什麼不算})}
#: 🔴 這張表與 CLAUDE.md 那張表**雙向**綁死（見下方兩條判準）：表上多一列「無機械物」
#: 卻沒登記探針 → 紅（不得靠新增一列來閃過證偽）；登記了探針而表上那列已補上機械物
#: → 紅（stale，考察軌跡不得靠慣性活著）。
_IRON_LAW3_UNCOVERED_EVIDENCE: dict[str, tuple[tuple[str, ...], dict[str, str]]] = {
    "副檔名判斷": (("副檔名", "file_extension", "extension_branch", "exe_suffix"), {}),
    "shell=True": (
        ("shell_true", "native_shell", "原生殼"),
        {"AutoClaude/tests/test_evaluator_kill_tree.py":
         "該鎖守的是「shell=True 逾時要 kill 整棵行程樹」，對 cmd.exe ⇄ /bin/sh 的"
         "**語意差異**（引號、`&&`、路徑分隔、rc 語意）零判準——同一個關鍵字、不同主題"},
    ),
}
#: 已知正例：本判準若對它失明，整條就是裝飾品。這組 token 指向的正是 S4-01 那一格
#: 被填錯的機械物本體（NTFS 大小寫碰撞鍵）。
_IRON_LAW3_KNOWN_POSITIVE_TOKENS: tuple[str, ...] = ("collision", "casefold", "大小寫")
_IRON_LAW3_KNOWN_POSITIVE_FILE = "tools/check_ntfs_paths.py"


def mechanism_definition_names(repo_root: Path) -> list[tuple[str, int, str]]:
    """機械物住所內所有 `(檔案, 行號, 識別字)`。現查，不寫死清單。"""
    out: list[tuple[str, int, str]] = []
    for glob in _IRON_LAW3_MECHANISM_HOMES:
        for path in sorted(repo_root.glob(glob)):
            rel = path.relative_to(repo_root).as_posix()
            text = path.read_text(encoding="utf-8", errors="replace")
            for lineno, line in enumerate(text.splitlines(), start=1):
                match = _MECHANISM_DEF_RE.match(line)
                if match:
                    out.append((rel, lineno, match.group(1) or match.group(2)))
    return out


def falsifying_hits(
    names: list[tuple[str, int, str]], tokens: tuple[str, ...], considered: dict[str, str]
) -> list[str]:
    """回傳「反證」清單：命中 token 且不在已審視檔案內的識別字。"""
    lowered = tuple(t.lower() for t in tokens)
    return [
        f"{rel}:{lineno}: `{name}`"
        for rel, lineno, name in names
        if rel not in considered and any(t in name.lower() for t in lowered)
    ]


class TestIronLaw3NoMechanismClaimsAreFalsifiable(unittest.TestCase):
    """鐵律三對照表的每一格「無機械物」都必須經得起證偽（見上方 WHY）。"""

    @staticmethod
    def _table_rows() -> list[list[str]]:
        import test_doc_loc_baseline_freshness_r60 as _acct  # noqa: PLC0415
        return _acct.iron_law3_trigger_rows(
            (_REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8-sig"))

    def _uncovered_first_cells(self) -> list[str]:
        return [cells[0] for cells in self._table_rows() if "無機械物" in cells[1]]

    def test_the_probe_has_discriminating_power_on_a_known_positive(self) -> None:
        """自錨（先看這一條）：拿 S4-01 那格真實存在的機械物餵進去，必須被找出來。

        少了這一條，下面兩條在「識別字掃描其實壞掉、永遠回空」時仍然全綠——而那正是
        本檔一貫在防的「靜默縮面」。
        """
        names = mechanism_definition_names(_REPO_ROOT)
        self.assertGreater(len(names), 800,
                           f"機械物住所只抽到 {len(names)} 個識別字 ⇒ 掃描面疑似壞掉")
        hits = falsifying_hits(names, _IRON_LAW3_KNOWN_POSITIVE_TOKENS, {})
        self.assertTrue(
            any(h.startswith(_IRON_LAW3_KNOWN_POSITIVE_FILE + ":") for h in hits),
            f"已知正例（{_IRON_LAW3_KNOWN_POSITIVE_FILE} 的大小寫碰撞鍵）沒被找出來 ⇒ "
            f"本判準對「表說沒有、實際有」這個方向是裝飾品。現有命中：{hits[:10]}")

    def test_every_no_mechanism_row_survives_its_own_falsification_probe(self) -> None:
        """缺陷本體那一向：宣稱「無機械物」而其實有 ⇒ 紅。"""
        names = mechanism_definition_names(_REPO_ROOT)
        problems: list[str] = []
        for cell in self._uncovered_first_cells():
            keys = [k for k in _IRON_LAW3_UNCOVERED_EVIDENCE if k in cell]
            if not keys:
                problems.append(
                    f"「{cell}」列自陳無機械物，卻沒有登記證偽探針 ⇒ 這一格的宣稱不可被"
                    "反駁。請在 `_IRON_LAW3_UNCOVERED_EVIDENCE` 補一組 token"
                    "（新增一列來閃過證偽是本判準第一個要擋的動作）")
                continue
            for key in keys:
                tokens, considered = _IRON_LAW3_UNCOVERED_EVIDENCE[key]
                hits = falsifying_hits(names, tokens, considered)
                if hits:
                    problems.append(
                        f"「{cell}」列自陳無機械物，但機械物住所裡有識別字命中 {tokens}："
                        f"{hits[:6]} ⇒ 要嘛它其實有人在守（請改機械物欄，分子 +1），"
                        "要嘛那幾支守的是別的主題（請寫進 "
                        "`_IRON_LAW3_UNCOVERED_EVIDENCE` 的已審視清單並寫明為什麼不算）")
        self.assertEqual(problems, [], "\n".join(problems))

    def test_the_evidence_registry_does_not_rot(self) -> None:
        """反向：登記了探針、表上那列卻已經有機械物（或整列不見了）⇒ stale。"""
        uncovered = self._uncovered_first_cells()
        self.assertTrue(uncovered, "表上一列『無機械物』都沒有？請確認表頭與解析仍相符")
        stale = [key for key in _IRON_LAW3_UNCOVERED_EVIDENCE
                 if not any(key in cell for cell in uncovered)]
        self.assertEqual(
            stale, [],
            f"這些證偽探針已 stale（表上對應列已補機械物或已被刪）：{stale}"
            "——請一併刪除，考察軌跡不得靠慣性活著")
        for key, (tokens, considered) in _IRON_LAW3_UNCOVERED_EVIDENCE.items():
            self.assertTrue(tokens, f"「{key}」的 token 是空的 ⇒ 探針恆不命中＝假綠")
            for rel, why in considered.items():
                self.assertTrue(
                    (_REPO_ROOT / rel).is_file(),
                    f"「{key}」的已審視檔案 {rel} 已不存在（WHY={why}）⇒ 請自清單移除")
                self.assertGreater(len(why), 10, f"{rel} 的『為什麼不算』寫得太短")

    def test_the_probe_would_catch_a_freshly_planted_mechanism(self) -> None:
        """注入自證：合成一個「表說沒有、其實有」的狀態，必須紅。"""
        names = [("tools/pretend_scanner.py", 12, "scan_file_extension_platform_branch")]
        self.assertTrue(
            falsifying_hits(names, ("file_extension",), {}),
            "新植入的機械物沒被找出來 ⇒ 低報分子那一向仍然失明")
        self.assertEqual(
            falsifying_hits(names, ("file_extension",),
                            {"tools/pretend_scanner.py": "已審視：守的是別的主題"}),
            [], "已審視清單沒有生效 ⇒ 這道鎖無法容納「同關鍵字、不同主題」而必被關掉")


if __name__ == "__main__":
    # R78：本檔被當 entry point 直接起（M5 的載具出口就在 TestXplatInjectionMatrix
    # 的 setUpClass），而檔內多處印中文 ⇒ `test_subprocess_encoding_hygiene` 判準要求
    # 入口點自帶 UTF-8 stdio 保護（非 CJK locale 逃脫成 \uXXXX、非 UTF-8 locale 亂碼、
    # stdout 更是 errors='strict' 直接崩潰）。用唯一實作而非就地 reconfigure，理由同
    # `test_adr_xplat001_c1c2_lock.py` 檔尾：後者會讓 stdio 複本棘輪 +1。
    # 放在 `__main__` 內 ⇒ 被當測試模組 import 時不付這個副作用代價。
    sys.path.insert(0, str(_REPO_ROOT / "tools"))
    import _stdio_utf8  # noqa: F401
    unittest.main()
