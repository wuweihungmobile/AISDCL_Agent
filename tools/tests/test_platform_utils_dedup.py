#!/usr/bin/env python3
"""tools/lib/platform_utils.py 收斂止血鎖（R16 架構最佳化 — Architect 建議 A/E）。

背景：`_init_utf8_streams()` 曾被複製貼上到至少 8 個檔案，其中 6 份漏了
`sys.platform != "win32"` 守衛、2 份有。8 個呼叫點已收斂為統一 import
`tools/lib/platform_utils.init_utf8_streams`——但收斂當下誤判「有守衛的 2 份
才是正確版本」，實際上 `test_hooks_stdin_utf8.py` 證明「無條件包裝（原本
6 份的行為）」才是正確版本：呼叫端可在任何平台以 `PYTHONIOENCODING` 覆寫
編碼，POSIX 上不強制重新包裝會讓阻斷級 hook 的中文錯誤訊息讀成亂碼。
本測試機械鎖住兩件事：
  1. `platform_utils` 模組本身提供的 API 存在且行為正確（兩平台皆包裝 / 三態標籤）。
  2. 8 個已知呼叫點不再各自定義 `_init_utf8_streams()`（防未來復發第 9 份複製貼上）。

R66 追加（ADR-XPLAT-002 §5 Phase 2-C 驗收判準③ 補齊，DEF-101-629）：Phase 2-C／
2-D 把 10 份消費者各自的 LATEST 版本解析／凍結版本 regex 樣板收斂進
`tools/lib/sdd_latest.py`（`DEF-101-624`）之後，ADR 原始驗收判準③「任一消費者
改回自帶 `_latest_root` ⇒ dedup 鎖須紅」指定的手法正是「擴充本檔既有的
`_scan_repo_py_for(pattern)` 機制」，但落地當下未真正補上（僅補了 `DEF-101-627`
的模組自身行為回歸鎖，未補「消費者不得復發自帶定義」這道鎖）。本輪比照既有
`_EXTRA_DEF_RES` 做法，補上 `resolve_latest_name`／`resolve_latest_root`／
`exclude_frozen_sdd_versions` 三個函式的 repo-wide 唯一定義鎖。

R70 訂正兩件事（`DEF-101-751` 實質／`DEF-101-752` 元層級，兩者由同一個事故顯形）：

**① 不變量本身錯了（`DEF-101-751`）**：R17 的鎖寫的是「全 repo 只有一個定義點」，
但 R69 的 `ADR-XPLAT-003` 讓 `AutoClaude/autoclaude/utils/platform_caps.py` 也必須
定義 `is_windows()`／`is_macos()`——`autoclaude` 是**可獨立 pip 安裝**的套件
（`AutoClaude/pyproject.toml`，hatchling 預設只打包 `AutoClaude/autoclaude/`），
根層 `tools/lib/` 不在 wheel 內，脫離 monorepo checkout 後 import 必然失敗。
這與 `DEF-101-295`（R33 Architect 裁決，見 `autoclaude/utils/logger.py` 檔內註解）
是**同一條結構事實**、同一個既有解法：**跨孤島各留一份 ＋ 以鎖釘住其一致性**。
故本檔的不變量改寫為「**每一個相依孤島內，各 helper 只准有一個定義點**」——
不是把 `platform_caps.py` 加進白名單（那是把鎖改鬆），而是把「孤島」這個真正的
邊界寫進斷言：任一島內出現第二個定義點、或某島出現它不該有的 helper，皆須紅。
孤島邊界不是說法而是**結構事實**，由 `test_autoclaude_package_island_cannot_reach_root_tools_lib`
機械證明（該島若哪天真的搆得到根層 SSOT，兩島就該合併、本檔的雙 SSOT 宣告同時失效）。

**② 掃描面 fail-open（`DEF-101-752`，本輪更有價值的一筆）**：本檔原本用
`git ls-files "*.py"` 當掃描面 ⇒ **未追蹤（untracked）的 .py 天然不可見**。
`platform_caps.py` 在 R69 全程都是 untracked，於是上述①的衝突躲過了**四輪四方
複審**與收尾者多次 `run_root_unittests.py` 全套實跑（皆 `Ran 1581 … OK`），
直到 `git add -A` 讓它變成 tracked 的**那一刻**才在 pre-push 顯形。
掃描面現改為 **tracked ∪ untracked-not-ignored**（`git ls-files` ＋
`git ls-files -o --exclude-standard`）——排除 venv/快取的效果原本就靠 `.gitignore`，
`--exclude-standard` 一樣排除得掉。盲區已封由
`TestScanSurfaceCoversUntrackedFiles` 以真實 untracked 探針證明
（修前的 tracked-only 掃描面看不到它／修後看得到且判紅）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import platform_utils as m  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]

# 已知呼叫點（R16 收斂範圍）；新增第 9 份複製貼上時本清單需連同修復一併擴充，
# 檔案消失（改名/刪除）亦會被 test_known_call_sites_exist fail-loud 抓到。
_KNOWN_CALL_SITES = (
    "AutoClaude/tools/scaffold_sprint_section.py",
    "AutoClaude/tools/snapshot_sync.py",
    "AutoClaude/tools/hooks/check_lang.py",
    "AutoClaude/tools/hooks/loc_budget_check.py",
    "AutoClaude/tools/hooks/check_ps1_encoding.py",
    "AutoClaude/tools/hooks/check_sh_eol.py",
    "AutoClaude/tools/hooks/enforce_docs_path.py",
    "AutoClaude/tools/hooks/claude_md_freshness.py",
)

# 只比對「函式定義」而非呼叫（呼叫點理應保留 `_init_utf8_streams()` 這行）。
_DEF_RE = re.compile(r"^\s*def\s+_?init_utf8_streams\s*\(")

# R17 DEF-101-231 觀察點 1+2：同一輪新增的 tools/bootstrap_core.py /
# tools/integration_gate_core.py / AutoClaude/tools/run_act_core.py 三份核心，與
# 既有 tools/dev_start.py，全都各自重寫過一份 `os.name == "nt"` 判斷邏輯／
# 「Scripts/python.exe vs bin/python」判斷邏輯，從未 import platform_utils——
# 收斂為 is_windows() / os_label() / venv_python_path() 三個函式後，同款掃描
# 手法（機械掃描 `def <name>(` 是否第二次出現）追加鎖住這三個函式名。
_EXTRA_DEF_RES = {
    name: re.compile(rf"^\s*def\s+{re.escape(name)}\s*\(")
    for name in ("is_windows", "is_macos", "os_label", "venv_python_path")
}

# ── 相依孤島（R70／`DEF-101-751`）────────────────────────────────────────────
# 「孤島」＝一組**彼此可以合法 import、對外不行**的樹。本 repo 目前有兩個與平台判斷
# 有關的孤島：
#
#   root-shared ......... 根層 `tools/`（含 `tools/lib/`）、`AutoClaude/tools/`、
#                         `AISDLC_SDD/scripts/`、各 `.claude/hooks/`。這些是**護欄／
#                         載具層**，一律以 `sys.path.insert(root/"tools"/"lib")` 取用
#                         唯一真相源，且只依賴 stdlib（hook 腳本執行環境不保證有
#                         第三方套件——見 platform_utils.py 檔頭）。
#   autoclaude-package .. `AutoClaude/autoclaude/`。**可獨立 pip 安裝的套件**
#                         （`AutoClaude/pyproject.toml`；hatchling 未宣告
#                         `[tool.hatch.build]`，預設只打包與專案同名的 `autoclaude/`），
#                         根層 `tools/lib/` 不在 wheel 內 ⇒ 純 pip 安裝、脫離 monorepo
#                         checkout 的情境下 import 它必然 ModuleNotFoundError。
#                         反方向同樣不可行：讓 `tools/lib/` 改 import `autoclaude`
#                         會把 pydantic 拉進 hook／AISDLC_SDD CI 的 import graph，
#                         正是 R68 讓 `aisdlc-sdd-ci` 恆紅的那個形態（見
#                         AISDLC_SDD/scripts/tests/test_cross_subproject_import_isolation.py）。
#
# ⇒ 兩島各留一份定義是**結構必然**，不是偷懶；本 repo 對同款情形早有既定解法與判例
#   （`DEF-101-295`：`autoclaude/utils/logger.py` 的 NTFS 判準與根層三處各留一份，
#   一致性由 `tools/tests/test_windows_forbidden_filename_parity.py` 鎖住）。
#   決策記錄見 `docs/04_planning/ADR/ADR-XPLAT-003-…md` §7。
_ROOT_ISLAND = "root-shared"
_AUTOCLAUDE_ISLAND = "autoclaude-package"

#: 孤島判定用的路徑前綴（唯一需要判定的邊界；其餘一律歸 root-shared，故「落在兩島
#: 之外的新樹」不會被靜默放行——它會被算進 root-shared 而成為該島的第二個定義點 ⇒ 紅）。
_AUTOCLAUDE_PACKAGE_PREFIX = "AutoClaude/autoclaude/"

_PLATFORM_UTILS_SSOT = "tools/lib/platform_utils.py"
_PLATFORM_CAPS_SSOT = "AutoClaude/autoclaude/utils/platform_caps.py"

#: helper 名 → {孤島: 該島唯一真相源}。孤島**沒有列在此處**的 helper 一個都不准定義
#: （例：`os_label` 不在 autoclaude-package 島 ⇒ 該島出現 `def os_label(` 即紅）。
_HELPER_ISLAND_SSOT: dict[str, dict[str, str]] = {
    "is_windows": {_ROOT_ISLAND: _PLATFORM_UTILS_SSOT, _AUTOCLAUDE_ISLAND: _PLATFORM_CAPS_SSOT},
    "is_macos": {_ROOT_ISLAND: _PLATFORM_UTILS_SSOT, _AUTOCLAUDE_ISLAND: _PLATFORM_CAPS_SSOT},
    "os_label": {_ROOT_ISLAND: _PLATFORM_UTILS_SSOT},
    "venv_python_path": {_ROOT_ISLAND: _PLATFORM_UTILS_SSOT},
}


def island_of(rel: str) -> str:
    """repo 相對路徑 → 所屬相依孤島（純函式，供合成注入自證共用）。"""
    return _AUTOCLAUDE_ISLAND if rel.startswith(_AUTOCLAUDE_PACKAGE_PREFIX) else _ROOT_ISLAND


def island_violations(helper: str, hits: list[str]) -> list[str]:
    """挑出「不是自己所屬孤島唯一真相源」的定義點（純函式，不碰磁碟）。

    兩種違規形態各對應一個真實風險：
      1. 島內第二個定義點（`rel != 該島 SSOT`）——即 R17 原本要防的複製貼上復發，
         只是判定範圍由「全 repo」收斂為「島內」。
      2. 該島根本不該有這個 helper（`ssot_by_island.get(island) is None`）——防
         「在 autoclaude 套件裡多寫一個 `os_label`」這種擴散。
    """
    ssot_by_island = _HELPER_ISLAND_SSOT[helper]
    bad: list[str] = []
    for rel in hits:
        expected = ssot_by_island.get(island_of(rel))
        if expected is None or rel != expected:
            bad.append(rel)
    return bad

# R66 DEF-101-629：ADR-XPLAT-002 §5 Phase 2-C 驗收判準③ 的機械化——
# `tools/lib/sdd_latest.py`（Phase 2-C／2-D，`DEF-101-624`）收斂了 10 份消費者
# 各自的 LATEST 版本解析／凍結版本 regex 樣板，此三個函式同樣只應定義一處；
# 任一消費者若復發自帶定義（即便邏輯不同），本鎖須紅。
_SDD_LATEST_DEF_RES = {
    name: re.compile(rf"^\s*def\s+{re.escape(name)}\s*\(")
    for name in ("resolve_latest_name", "resolve_latest_root", "exclude_frozen_sdd_versions")
}


def _git_py_paths(*extra_args: str) -> set[str]:
    """`git ls-files [extra_args] -z -- "*.py"` 的相對路徑集合（rc 非零即硬錯）。"""
    out = subprocess.run(
        ["git", "ls-files", *extra_args, "-z", "--", "*.py"],
        cwd=_REPO_ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=True,  # 非 UTF-8 終端下的 mojibake 防護
    ).stdout
    # `-z`：NUL 分隔，git 不做八進位 quote ⇒ 非 ASCII 路徑不需 core.quotepath 處理。
    return {p for p in out.split("\0") if p}


def _tracked_only_py_files() -> list[str]:
    """R70 修**前**的掃描面（只認 tracked）。保留為具名函式的唯一理由：讓
    `TestScanSurfaceCoversUntrackedFiles` 能對「舊掃描面看不到／新掃描面看得到」
    做**同一支測試內的對照實測**，把盲區封閉這件事變成可驗證的斷言，而不是
    改完就沒人再證明的宣稱。除該對照組外，任何斷言都不得用它當掃描面。"""
    return sorted(_git_py_paths())


def _repo_py_files() -> list[str]:
    """掃描面＝**tracked ∪ untracked-not-ignored** 的 `.py`（R70／`DEF-101-752`）。

    為何要納入 untracked：見檔頭②。`git ls-files` 的 tracked-only 語意讓「還沒
    `git add` 的新檔」對本鎖完全不存在，而**新檔正是複製貼上最可能發生的地方**；
    R69 的 `platform_caps.py` 全程 untracked，四輪四方複審＋多次全套實跑零訊號。
    `-o --exclude-standard` 仍尊重 `.gitignore`，故原本靠 `.gitignore` 排除
    `.venv/`／`__pycache__/`（實測 `AISDLC_SDD/` 下有 4,800+ 支這類 `.py`）的效果
    一個都沒少——實測本 repo untracked-not-ignored 的 `.py` 現為 0 支，
    即本次擴面對**耗時**同樣近乎零代價。
    """
    return sorted(_git_py_paths() | _git_py_paths("-o", "--exclude-standard"))


def _scan_repo_py_for(pattern: re.Pattern[str]) -> list[str]:
    """全 repo（tracked ∪ untracked-not-ignored 的 `.py`）機械掃描，回傳命中檔案的
    repo 相對路徑清單。

    R57 修正（A5）：兩支掃描測試的 docstring 都自稱「全 repo 機械掃描」，實際
    掃描面卻只有 `AutoClaude/` 與根層 `tools/` 兩棵樹——`AISDLC_SDD/`（含
    `scripts/`、`conftest.py`、各版 `tools/fsm_runtime/`）與 `.claude/hooks/`
    下的 `.py` 全部在外，第 9 份複製貼上落在那些位置時本鎖零訊號。名實不符的
    掃描面本身就是誤導：複審者讀 docstring 會以為已全域覆蓋而不再追查。

    改用 `git ls-files` 而非 `rglob`：`AISDLC_SDD/` 底下有數千個 venv/快取 `.py`
    （實測 4,829 支），rglob 全掃既慢又得維護排除清單；追蹤檔天然排除這些，且與
    同 repo 姊妹鎖（`test_windowsapps_guard_cross_consistency.py` 的 repo-wide
    掃描）採同一政策。R57 實測：擴面後三個函式名的命中集合皆不變（仍只有
    `tools/lib/platform_utils.py`），新增偽陽性 0，故擴面在**命中集合**上零代價
    （R57 round 1 QA-R57-06 訂正：健壯性與耗時上並非零代價——實測 5,427 支
    tracked `.py`、單次模組耗時約 2.7s，且 `git ls-files` 會列出「index 有、工作樹
    沒有」的檔案）。

    讀不到的檔案一律**紅燈**（SD-R57-04／QA-R57-06）：git 追蹤卻讀不到 ⇒ 本鎖
    宣稱的「全 repo 掃描面」已縮小，而縮小掉的內容無從得知（sparse checkout 下
    缺席的檔案在 repo 裡是有內容的，靜默跳過＝真 fail-open）。故收齊全部讀不到
    的路徑後以 AssertionError 給出可診斷訊息，而非裸 FileNotFoundError traceback
    （原行為），也不是 `except OSError: continue` 的靜默跳過。

    R70：掃描面已由 tracked-only 擴為 tracked ∪ untracked-not-ignored
    （見 `_repo_py_files()`）；上兩段的 `git ls-files` 敘述與耗時實測皆為當時原文，
    刻意保留為沿革。
    """
    offenders: list[str] = []
    unreadable: list[str] = []
    for rel in _repo_py_files():
        try:
            text = (_REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            unreadable.append(f"{rel}（{type(exc).__name__}）")
            continue
        for line in text.splitlines():
            if pattern.match(line):
                offenders.append(rel)
                break
    if unreadable:
        raise AssertionError(
            f"掃描面內的 .py 有 {len(unreadable)} 支讀不到，掃描面已縮小、本鎖無法"
            f"宣稱「全 repo 已掃」：{unreadable[:10]}"
            f"{' …' if len(unreadable) > 10 else ''}；常見成因：git mv 進行中／"
            "已 rm 未 stage（先完成或 `git checkout --`）、sparse checkout（本鎖需"
            "完整 checkout 才成立）、檔案權限"
        )
    return offenders


class TestPlatformUtilsApi(unittest.TestCase):
    def test_os_label_three_states(self) -> None:
        with mock.patch.object(sys, "platform", "win32"):
            self.assertEqual(m.os_label(), "windows")
        with mock.patch.object(sys, "platform", "darwin"):
            self.assertEqual(m.os_label(), "mac")
        with mock.patch.object(sys, "platform", "linux"):
            self.assertEqual(m.os_label(), "linux")

    def test_is_windows_is_macos_is_posix(self) -> None:
        with mock.patch.object(sys, "platform", "win32"):
            self.assertTrue(m.is_windows())
            self.assertFalse(m.is_macos())
            self.assertFalse(m.is_posix())
        with mock.patch.object(sys, "platform", "darwin"):
            self.assertFalse(m.is_windows())
            self.assertTrue(m.is_macos())
            self.assertTrue(m.is_posix())

    def test_init_utf8_streams_wraps_on_posix(self) -> None:
        """R16 訂正：POSIX 上也必須重新包裝（不再是 no-op）——
        `test_hooks_stdin_utf8.py::test_enforce_docs_path_blocks_chinese_path_under_cp950`
        證明呼叫端可在任何平台以 PYTHONIOENCODING 覆寫預設編碼，POSIX 若不強制
        重新包裝，阻斷級 hook 的中文錯誤訊息會被以覆寫編碼寫出而讀成亂碼。
        用 mock 物件而非真實 sys.stdout/stderr，避免污染 pytest 自身的擷取機制。"""
        import io

        fake_stdout = mock.Mock()
        fake_stdout.buffer = io.BytesIO()
        fake_stderr = mock.Mock()
        fake_stderr.buffer = io.BytesIO()
        with mock.patch.object(sys, "platform", "darwin"), \
                mock.patch.object(sys, "stdout", fake_stdout), \
                mock.patch.object(sys, "stderr", fake_stderr):
            m.init_utf8_streams()
            self.assertIsInstance(sys.stdout, io.TextIOWrapper)
            self.assertIsInstance(sys.stderr, io.TextIOWrapper)

    def test_init_utf8_streams_wraps_on_windows(self) -> None:
        """Windows 上同樣重新包裝（有 `.buffer` 屬性時）。"""
        import io

        fake_stdout = mock.Mock()
        fake_stdout.buffer = io.BytesIO()
        fake_stderr = mock.Mock()
        fake_stderr.buffer = io.BytesIO()
        with mock.patch.object(sys, "platform", "win32"), \
                mock.patch.object(sys, "stdout", fake_stdout), \
                mock.patch.object(sys, "stderr", fake_stderr):
            m.init_utf8_streams()
            self.assertIsInstance(sys.stdout, io.TextIOWrapper)
            self.assertIsInstance(sys.stderr, io.TextIOWrapper)


class TestNoDuplicateDefinitions(unittest.TestCase):
    def test_known_call_sites_exist(self) -> None:
        """清單本身不得腐化（檔案消失須 fail-loud，不得靜默縮小掃描面）。"""
        for rel in _KNOWN_CALL_SITES:
            self.assertTrue(
                (_REPO_ROOT / rel).is_file(), f"{rel} 不存在——清單需同步更新"
            )

    def test_call_sites_no_longer_define_init_utf8_streams(self) -> None:
        """8 個已知呼叫點不得再各自定義 `_init_utf8_streams`/`init_utf8_streams`
        （只允許 import 唯一真相源）——防未來又複製貼上出第 9 份。"""
        offenders: list[str] = []
        for rel in _KNOWN_CALL_SITES:
            path = _REPO_ROOT / rel
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
            ):
                if _DEF_RE.match(line):
                    offenders.append(f"{rel}:{lineno}: {line.strip()}")
        self.assertEqual(
            offenders,
            [],
            "以下檔案復發自行定義 _init_utf8_streams()——請改為 import "
            "tools/lib/platform_utils.init_utf8_streams：\n" + "\n".join(offenders),
        )

    def test_definition_exists_only_in_platform_utils(self) -> None:
        """全 repo 機械掃描：`def init_utf8_streams(` 只應出現在唯一真相源一處
        （tools/lib/platform_utils.py）。只釘選「命中檔案清單」而非行號——
        行號會隨模組內部改寫漂移，非本測試守護的契約。"""
        offenders = _scan_repo_py_for(_DEF_RE)
        self.assertEqual(
            offenders,
            ["tools/lib/platform_utils.py"],
            "init_utf8_streams 的定義只應出現在 tools/lib/platform_utils.py 一處；"
            f"實際命中：{offenders}",
        )

    def test_platform_judgment_helpers_have_one_definition_per_island(self) -> None:
        """R17 `DEF-101-231` 觀察點 1+2，R70 `DEF-101-751` 改寫射程：
        is_windows／is_macos／os_label／venv_python_path 這四個平台判斷 helper，
        在**每一個相依孤島內**只准有一個定義點。

        R17 原本寫的是「全 repo 一處」，R69 的 `ADR-XPLAT-003` 已把它推翻——
        `AutoClaude/autoclaude/` 是可獨立 pip 安裝的套件、結構上搆不到根層
        `tools/lib/`（見 `_HELPER_ISLAND_SSOT` 上方說明與 ADR §7）。改寫後的鎖
        對「島內第二個定義點」與「某島出現它不該有的 helper」兩種形態都須紅，
        `TestIslandInvariantIsNotAToothlessWhitelist` 以合成注入逐一自證。

        `tools/dev_start.py`、`tools/bootstrap_core.py`、
        `tools/integration_gate_core.py`、`AutoClaude/tools/run_act_core.py`
        四份核心（皆屬 root-shared 島）仍一律 import 呼叫、不得各自重寫第二份。
        """
        for name, pattern in _EXTRA_DEF_RES.items():
            with self.subTest(helper=name):
                hits = _scan_repo_py_for(pattern)
                self.assertEqual(
                    island_violations(name, hits),
                    [],
                    f"{name} 在某個相依孤島內出現了第二個定義點（或出現在不該有它的"
                    f"島）。各島唯一真相源＝{_HELPER_ISLAND_SSOT[name]}；實際命中："
                    f"{hits}。修法：同島者改 import 該島 SSOT；若你認為這是第三個"
                    "孤島，先更新 ADR-XPLAT-003 §7 再擴充 _HELPER_ISLAND_SSOT",
                )
                # 反方向的牙：SSOT 自己若不再定義（改名／regex 壞掉／檔案搬走），
                # 上面的斷言會「零違規」而全綠 ⇒ 恆綠空砲。此處要求每個宣告過的
                # 島 SSOT 都真的在命中集合裡。
                self.assertEqual(
                    sorted(set(hits)),
                    sorted(_HELPER_ISLAND_SSOT[name].values()),
                    f"{name} 的命中集合與宣告的島 SSOT 不符（少掉＝SSOT 已不定義它、"
                    f"本鎖成恆綠空砲；多出＝上一條斷言該抓到）；實際命中：{hits}",
                )

    def test_autoclaude_package_island_cannot_reach_root_tools_lib(self) -> None:
        """孤島邊界是**結構事實**，不是本檔的說法（R70 `DEF-101-751`）。

        本檔容許 `is_windows`／`is_macos` 存在兩份定義，唯一理由是
        `AutoClaude/autoclaude/`（可獨立 pip 安裝的套件）搆不到根層 `tools/lib/`。
        這個前提必須被機械看守：若哪天 `autoclaude/` 真的 import 了 `tools/lib/`
        的任一模組，前提就不成立、兩島應合併為一，屆時本鎖轉紅、逼人回來重新
        決策（並更新 ADR-XPLAT-003 §7），而不是讓雙份定義變成無人複查的既成事實。

        用 AST 而非字串比對：`autoclaude/utils/logger.py` 的**註解**逐字寫著
        「不可依賴 monorepo 根層 tools/lib/*.py」（`DEF-101-295` 的判例記錄），
        純文字掃描會把那句正確的說明誤判成違規。
        """
        lib_modules = sorted(
            p.stem for p in (_REPO_ROOT / "tools" / "lib").glob("*.py")
            if not p.stem.startswith("_")
        )
        # fail-loud 下限：glob 打空 ⇒ 禁用集合變空 ⇒ 本鎖恆綠空砲。
        self.assertGreaterEqual(
            len(lib_modules), 5,
            f"tools/lib/*.py 只取到 {lib_modules}，掃描面疑似縮小；集合若變空，"
            "本鎖會變成恆綠空砲，故此處硬錯不放行",
        )
        violations: list[str] = []
        for rel in _repo_py_files():
            if not rel.startswith(_AUTOCLAUDE_PACKAGE_PREFIX):
                continue
            try:
                tree = ast.parse((_REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:  # 語法錯誤另有 pytest collection 把關
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                    names = [node.module]
                else:
                    continue
                for mod in names:
                    if mod.split(".")[0] in lib_modules:
                        violations.append(f"{rel}:{node.lineno} → {mod}")
        self.assertEqual(
            violations, [],
            "AutoClaude/autoclaude/（可獨立 pip 安裝的套件）import 了根層 tools/lib/ "
            "的模組：\n" + "\n".join(violations)
            + "\n這會讓純 pip 安裝、脫離 monorepo checkout 的情境 ModuleNotFoundError"
            "（同 DEF-101-295 判例）。若這是有意的架構變更，兩個相依孤島已合併，"
            "請同步刪除 platform_caps 的重複定義並更新 ADR-XPLAT-003 §7",
        )

    def test_sdd_latest_helpers_defined_only_in_sdd_latest(self) -> None:
        """R66 DEF-101-629（ADR-XPLAT-002 §5 Phase 2-C 驗收判準③ 補齊）：
        `resolve_latest_name`／`resolve_latest_root`／`exclude_frozen_sdd_versions`
        （Phase 2-C／2-D 收斂目標，`DEF-101-624`）同樣只應在
        `tools/lib/sdd_latest.py` 定義一處；10 個消費者
        （`tools/tests/test_bash32_compat.py` 等）若復發自行定義同名函式
        （即便邏輯改寫，只要函式名相同即視為違反「呼叫端改 import、不留第二份
        定義」的收斂契約），本鎖須紅——即 ADR 原始驗收判準③「任一消費者改回
        自帶 `_latest_root`」的機械化版本。"""
        for name, pattern in _SDD_LATEST_DEF_RES.items():
            offenders = _scan_repo_py_for(pattern)
            self.assertEqual(
                offenders,
                ["tools/lib/sdd_latest.py"],
                f"{name} 的定義只應出現在 tools/lib/sdd_latest.py 一處；"
                f"實際命中：{offenders}",
            )


class TestIslandInvariantIsNotAToothlessWhitelist(unittest.TestCase):
    """鎖的鎖（R70 `DEF-101-751`）：證明「每島一個定義點」不是把 `platform_caps.py`
    加進白名單了事。

    白名單與孤島不變量的差別在**注入第三個定義點時會不會紅**：白名單只要再加一筆
    條目就放行，孤島不變量則不論加在哪一島都是違規。下面用合成路徑清單直接餵純函式
    `island_violations()`，兩個方向各鎖一次；不碰磁碟，故不受當下工作樹狀態影響。
    """

    _ROOT_SSOT = _PLATFORM_UTILS_SSOT
    _CAPS_SSOT = _PLATFORM_CAPS_SSOT

    def test_current_shape_is_clean(self) -> None:
        """對照組：兩島各一個定義點＝零違規（否則下面的注入測試證明不了任何事）。"""
        self.assertEqual(
            island_violations("is_windows", [self._ROOT_SSOT, self._CAPS_SSOT]), []
        )
        self.assertEqual(island_violations("os_label", [self._ROOT_SSOT]), [])

    def test_third_definition_inside_root_island_is_flagged(self) -> None:
        """根層孤島內再加第三個定義點 → 必須紅（R17 原本要防的複製貼上復發）。"""
        for injected in (
            "tools/dev_start.py",              # 曾真的自帶過一份（DEF-101-231）
            "tools/bootstrap_core.py",
            "AutoClaude/tools/run_act_core.py",  # AutoClaude 的**護欄層**仍屬根層孤島
            "AISDLC_SDD/scripts/sdd_version.py",
            "some_brand_new_tree/helper.py",   # 兩島之外的新樹一律歸 root-shared ⇒ 仍紅
        ):
            with self.subTest(injected=injected):
                self.assertEqual(
                    island_violations(
                        "is_windows", [self._ROOT_SSOT, self._CAPS_SSOT, injected]
                    ),
                    [injected],
                )

    def test_third_definition_inside_autoclaude_island_is_flagged(self) -> None:
        """AutoClaude 孤島（`AutoClaude/autoclaude/`）內再加第三個定義點 → 必須紅。

        這正是 R69 若有本鎖就會當場被抓到的形態：`platform_caps.py` 之外的任何
        `autoclaude/` 模組復發自帶平台判斷（`evaluator.py` 與 `pty_wrapper.py`
        改前就是各自一份，見 ADR-XPLAT-003 §1）。
        """
        for injected in (
            "AutoClaude/autoclaude/execution/evaluator.py",
            "AutoClaude/autoclaude/perception/pty_wrapper.py",
            "AutoClaude/autoclaude/utils/notifier.py",
        ):
            with self.subTest(injected=injected):
                self.assertEqual(
                    island_violations(
                        "is_windows", [self._ROOT_SSOT, self._CAPS_SSOT, injected]
                    ),
                    [injected],
                )

    def test_helper_not_owned_by_an_island_is_flagged_there(self) -> None:
        """`os_label`／`venv_python_path` 不屬於 autoclaude 孤島 ⇒ 出現在該島即紅
        （防「反正那邊也有一份平台模組」式的擴散）。"""
        self.assertEqual(
            island_violations("os_label", [self._ROOT_SSOT, self._CAPS_SSOT]),
            [self._CAPS_SSOT],
        )

    def test_island_classification_boundary(self) -> None:
        """孤島判定只認 `AutoClaude/autoclaude/` 前綴：AutoClaude 的**護欄層**
        （`AutoClaude/tools/`）屬 root-shared——它確實以 sys.path 取用根層 SSOT
        （見 `AutoClaude/tools/run_act_core.py`），把它劃進套件島會誤放行。"""
        self.assertEqual(island_of("AutoClaude/autoclaude/utils/platform_caps.py"),
                         _AUTOCLAUDE_ISLAND)
        self.assertEqual(island_of("AutoClaude/tools/run_act_core.py"), _ROOT_ISLAND)
        self.assertEqual(island_of("AutoClaude/tests/test_evaluator_kill_tree.py"), _ROOT_ISLAND)
        self.assertEqual(island_of("tools/lib/platform_utils.py"), _ROOT_ISLAND)


class TestScanSurfaceCoversUntrackedFiles(unittest.TestCase):
    """掃描面盲區封閉鎖（R70 `DEF-101-752`）——本輪最有價值的一筆證據的機械化。

    事故本身：`platform_caps.py` 在 R69 全程是 untracked，而本檔的掃描面是
    `git ls-files`（tracked-only）。於是它與 R17 不變量的衝突躲過了**四輪四方
    複審**、以及收尾者多次 `run_root_unittests.py` 全套實跑（皆 `Ran 1581 … OK`），
    直到 `git add -A` 讓它變成 tracked 的**那一刻**才在 pre-push 顯形。
    ⇒「驗證載具自己有盲區」的教科書級樣本：不是鎖寫錯，是鎖**看不到**該看的地方。

    本鎖造一支真的 untracked（且非 ignored）的違規 `.py`，同一支測試內對照兩個
    掃描面：修前的 tracked-only 看不到它／修後的看得到且判紅。缺任一半都證明不了
    「盲區已封」——只證明「現在掃得到」的話，掃描面被改回去時本鎖不會說話。
    """

    def test_untracked_offender_is_invisible_to_old_surface_and_caught_by_new(self) -> None:
        probe_dir = _REPO_ROOT / f"_scan_surface_probe_{os.getpid()}"
        self.assertFalse(probe_dir.exists(), f"探針目錄殘留：{probe_dir}（上次執行未清乾淨）")
        probe = probe_dir / "probe_platform_helper.py"
        rel = f"{probe_dir.name}/{probe.name}"
        probe_dir.mkdir()
        try:
            probe.write_text(
                "# R70 掃描面盲區探針（測試建立、測試刪除；殘留即為異常）\n"
                "def is_windows():\n"
                "    return False\n",
                encoding="utf-8",
            )
            # 前置條件：探針確實是 untracked 且未被 .gitignore 排除，否則本測試
            # 證明的東西與事故形態不同（fail-loud，不靜默 skip）。
            self.assertIn(rel, _git_py_paths("-o", "--exclude-standard"),
                          f"{rel} 未被 git 視為 untracked-not-ignored——探針失效")

            # ① 修**前**的掃描面：看不到它 ＝ 盲區的實測憑證
            self.assertNotIn(
                rel, _tracked_only_py_files(),
                "tracked-only 掃描面竟看得到未追蹤檔——本鎖賴以成立的前提不成立",
            )
            # ② 修**後**的掃描面：看得到，且被孤島不變量判為違規（根層第二個定義點）
            hits = _scan_repo_py_for(_EXTRA_DEF_RES["is_windows"])
            self.assertIn(rel, hits, "擴面後仍掃不到未追蹤的違規檔——盲區未封")
            self.assertIn(
                rel, island_violations("is_windows", hits),
                "未追蹤的違規檔進了掃描面卻沒被判違規——擴面白做",
            )
        finally:
            shutil.rmtree(probe_dir, ignore_errors=True)
        self.assertFalse(probe_dir.exists(), f"探針目錄未清除：{probe_dir}")


# ══════════════════════════════════════════════════════════════════════════════
# R74：島模型對「**行內語句**複本」結構性全盲 —— 先讓它可量測並上棘輪
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 缺陷本體：本檔的比對式一律是 `^\s*def <name>\(`（`_EXTRA_DEF_RES`／
# `_SDD_LATEST_DEF_RES`／`_HELPER_ISLAND_SSOT`），只認**函式定義**形態。於是同一份
# 知識若以「行內語句」複製，島模型一個都看不到——而本 repo 最常被複製的正是這種：
# `tools/_stdio_utf8.py` 已經是 SSOT（15 支 `import _stdio_utf8` 的消費者，現查），
# 但仍有檔案直接寫 `sys.stdout.reconfigure(encoding="utf-8", ...)` 就地重做一次。
#
# 誠實劃界（本輪刻意**不**收斂，只讓它可量測）：
#   · 有些行內複本是**合法的**——`tools/_stdio_utf8.py` 自己、以及刻意驗證行為的鎖
#     （`test_subprocess_encoding_hygiene.py`）、以及測試 fixture 的假 CLI。故判準是
#     **shrink-only 棘輪**而不是「零容忍」：現況凍結，只准變少。
#   · 診斷階段曾以「43 份行內複本 vs 19 個 SSOT 消費者」描述本筆。**本輪以下方判準
#     實測不複現**：`sys.std{out,err}.reconfigure(` 形態為 9 處／8 檔，`import
#     _stdio_utf8` 消費者 15 支（`PYTHONUTF8` 字樣另有 46 處／19 檔，那是環境變數
#     設定、不是本 SSOT 的行內複本，兩者不可混為一談）。故本棘輪釘的是**本輪實測值**，
#     不是任何轉述的數字——這正是本檔一貫的「不寫死轉述來的量」紀律。
_INLINE_STDIO_RE = re.compile(r"(?:sys\.)?std(?:out|err)\s*\.\s*reconfigure\s*\(")
_STDIO_SSOT_REL = "tools/_stdio_utf8.py"
_STDIO_SSOT_IMPORT_RE = re.compile(r"^\s*import\s+_stdio_utf8\b", re.M)

#: 行內複本的 shrink-only 棘輪：{檔案: 該檔命中數}。**只准變少**。
#: 新增一處行內複本（不論在哪一島）即紅，訊息指路 `import _stdio_utf8`。
_FROZEN_INLINE_STDIO_SITES: dict[str, int] = {
    "AISDLC_SDD/scripts/agent_template_lint.py": 1,
    "AutoClaude/tests/fixtures/dummy_cli.py": 2,
    "AutoClaude/tools/ab_compare_backends.py": 1,
    "AutoClaude/tools/ac4_progress_check.py": 1,
    "AutoClaude/tools/migrate_yaml_to_db.py": 1,
    "AutoClaude/tools/run_bridge_e2e.py": 1,
    "AutoClaude/tools/three_tier_to_playbook.py": 1,
    "tools/tests/test_subprocess_encoding_hygiene.py": 1,
}


def _read_scanned(rel: str) -> str:
    """讀掃描面內的一支 `.py`；讀不到即 fail-loud（比照 `_scan_repo_py_for`：靜默跳過
    等於掃描面無聲縮小，而縮小掉什麼無從得知）。"""
    try:
        return (_REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise AssertionError(
            f"掃描面內的 {rel} 讀不到（{type(exc).__name__}）⇒ 掃描面已縮小，"
            "本棘輪的凍結值不再有意義") from exc


def inline_stdio_sites() -> dict[str, int]:
    """全掃描面（含 untracked）的行內 stdio-UTF-8 複本；SSOT 自己不算。"""
    out: dict[str, int] = {}
    # 排除 SSOT 自己與**本檔**：本檔是判準的**定義側**（樣式字面 ＋ 判準自檢樣本各命中
    # 一次），把定義側算進使用側會讓判準自我循環——同 `sc7_every_used_scan_code_is_defined`
    # 刻意排除維度表自己的理由，逐字同型。
    skip = {_STDIO_SSOT_REL, Path(__file__).resolve().relative_to(_REPO_ROOT).as_posix()}
    for rel in _repo_py_files():
        if rel in skip:
            continue
        hits = len(_INLINE_STDIO_RE.findall(_read_scanned(rel)))
        if hits:
            out[rel] = hits
    return out


def inline_ratchet_problems(frozen: dict[str, int], current: dict[str, int]) -> list[str]:
    """棘輪判準（純函式，供合成注入自證）：任一檔命中數上升、或出現新檔，即違規。"""
    problems = [
        f"{rel}：行內 stdio-UTF-8 複本 {n} 處 > 凍結值 {frozen.get(rel, 0)} 處"
        for rel, n in sorted(current.items()) if n > frozen.get(rel, 0)
    ]
    return problems


class TestR74InlineCopyRatchetForStdioSsot(unittest.TestCase):
    """島模型看不到行內語句複本 ⇒ 先讓數量可量測、且只准往下。"""

    def test_inline_copies_do_not_grow(self) -> None:
        problems = inline_ratchet_problems(_FROZEN_INLINE_STDIO_SITES, inline_stdio_sites())
        self.assertEqual(
            problems, [],
            "行內 stdio-UTF-8 複本增加了：\n  " + "\n  ".join(problems)
            + f"\n修法＝改用 SSOT：`import _stdio_utf8`（{_STDIO_SSOT_REL}，import 期即生效）。"
            "本棘輪是 shrink-only：要新增一處必須先論證為何不能用 SSOT",
        )

    def test_frozen_map_matches_the_worktree(self) -> None:
        """自緊：刪掉一處而不下修凍結值 ⇒ 餘裕就是破口（同 `_FROZEN_GUARD_FILE_COUNT`）。"""
        self.assertEqual(
            inline_stdio_sites(), _FROZEN_INLINE_STDIO_SITES,
            "工作樹現況與 `_FROZEN_INLINE_STDIO_SITES` 已漂移——收斂掉一處後請同步下修")

    def test_the_ssot_has_real_consumers(self) -> None:
        """反空轉：SSOT 若零消費者，本棘輪守的就不是「該用 SSOT 卻沒用」而是別的事。"""
        consumers = [rel for rel in _repo_py_files()
                     if rel != _STDIO_SSOT_REL
                     and _STDIO_SSOT_IMPORT_RE.search(_read_scanned(rel))]
        self.assertGreaterEqual(len(consumers), 10,
                                f"`import _stdio_utf8` 消費者異常少（{len(consumers)}）")

    def test_the_ratchet_has_teeth(self) -> None:
        """合成注入（不碰磁碟）：新檔與既有檔命中數上升兩種形態都必須被點名。"""
        frozen = {"a.py": 1}
        self.assertTrue(inline_ratchet_problems(frozen, {"a.py": 2}))
        self.assertTrue(inline_ratchet_problems(frozen, {"a.py": 1, "b.py": 1}))
        self.assertEqual(inline_ratchet_problems(frozen, {"a.py": 1}), [])
        self.assertEqual(inline_ratchet_problems(frozen, {}), [],
                         "收斂到零不得被判違規——棘輪的方向只有一個")

    def test_the_pattern_recognises_both_written_forms(self) -> None:
        """判準自檢：兩種常見寫法都要抓到，否則棘輪的凍結值是假的。"""
        for sample in ('sys.stdout.reconfigure(encoding="utf-8")',
                       'stderr.reconfigure(encoding="utf-8", errors="replace")'):
            with self.subTest(sample=sample):
                self.assertIsNotNone(_INLINE_STDIO_RE.search(sample))
        self.assertIsNone(_INLINE_STDIO_RE.search("f.reconfigure(encoding='utf-8')"),
                          "非 stdio 串流不得誤觸（誤報的鎖最後一定被繞過）")


if __name__ == "__main__":
    unittest.main()
