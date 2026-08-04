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
import inspect
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Mapping
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

    # 🔴 R75：下面三支取代原本的 `test_init_utf8_streams_wraps_on_{posix,windows}`。
    # 原斷言是 `assertIsInstance(sys.stdout, io.TextIOWrapper)`——那**釘住的是手法**
    # （「一定要換掉串流物件」），不是意圖（「兩個平台都必須變成 UTF-8/replace」）。
    # R75 去重把唯一實作改成「先就地 `.reconfigure()`、沒有該方法時才包 wrapper」，是先前
    # 兩份實作的嚴格聯集且對真實串流更安全（保留物件同一性與 line_buffering）；照原斷言
    # 會紅，但那是**斷言選錯了層次**，不是行為退化。故改為釘意圖：無論走哪條路徑，
    # 結果都必須是 UTF-8 ＋ `errors="replace"`。
    # 三支合起來覆蓋實作的三條分支（有 reconfigure／只有 buffer／兩者皆無），缺任一支
    # 都會讓另兩條分支可以悄悄壞掉。

    def _fake_std_pair(self, **attrs: object) -> tuple[object, object]:
        """造一對假串流；`spec` 明列屬性，避免 `mock.Mock` 自動長出 `reconfigure`
        （那正是「有 reconfigure」與「沒有 reconfigure」兩條分支分不開的原因）。"""
        return (mock.Mock(**attrs), mock.Mock(**attrs))

    def test_init_utf8_streams_forces_utf8_on_both_platforms(self) -> None:
        """R16 訂正的意圖不變、只是斷言換層次：POSIX 上也必須生效（不是 no-op）——
        `AutoClaude/tests/tools/hooks/test_hooks_stdin_utf8.py` 的
        `test_enforce_docs_path_blocks_chinese_path_under_cp950`
        證明呼叫端可在任何平台以 PYTHONIOENCODING 覆寫預設編碼，POSIX 若不強制改，
        阻斷級 hook 的中文錯誤訊息會被以覆寫編碼寫出而讀成亂碼。

        `errors="replace"` 是斷言的一部分而非細節：R74 的 P0 就是 `sys.stderr` 預設
        `errors='backslashreplace'`，中文指引在非 CJK codepage 降解成 `\\uXXXX` 字面。
        用假串流而非真實 sys.stdout/stderr，避免污染 pytest 自身的擷取機制。
        """
        # 先把委派解析好（`_stdio_utf8` 的 import **本身**就會套用一次——那是它的契約）。
        # 不先暖機的話，第一個 subTest 會量到「import 期那次 ＋ 委派呼叫那次」＝2 次，
        # 讓斷言變成在量「這支測試是不是第一個 import 它的人」而不是在量行為。
        m._stdio_utf8_impl()
        for platform in ("darwin", "win32", "linux"):
            with self.subTest(platform=platform):
                fake_stdout, fake_stderr = self._fake_std_pair()
                with mock.patch.object(sys, "platform", platform), \
                        mock.patch.object(sys, "stdout", fake_stdout), \
                        mock.patch.object(sys, "stderr", fake_stderr):
                    m.init_utf8_streams()
                for stream in (fake_stdout, fake_stderr):
                    stream.reconfigure.assert_called_once_with(
                        encoding="utf-8", errors="replace")

    def test_init_utf8_streams_wraps_when_stream_has_no_reconfigure(self) -> None:
        """回退路徑：沒有 `.reconfigure` 但有 `.buffer` 的串流仍必須被強制成 UTF-8。

        這一路正是去重前 8 支 AutoClaude hook 走的唯一路徑，保留它才叫「嚴格聯集」；
        少了它，遇到非 `TextIOWrapper` 的 stdout 時保護會靜默消失。
        """
        import io

        class _NoReconfigure:  # 刻意不是 Mock：Mock 會自動長出 reconfigure
            def __init__(self) -> None:
                self.buffer = io.BytesIO()

        fake_stdout, fake_stderr = _NoReconfigure(), _NoReconfigure()
        with mock.patch.object(sys, "stdout", fake_stdout), \
                mock.patch.object(sys, "stderr", fake_stderr):
            m.init_utf8_streams()
            for name in ("stdout", "stderr"):
                stream = getattr(sys, name)
                self.assertIsInstance(stream, io.TextIOWrapper, f"sys.{name} 未被包裝")
                self.assertEqual(stream.encoding, "utf-8")
                self.assertEqual(stream.errors, "replace")

    def test_init_utf8_streams_is_a_safe_noop_without_reconfigure_or_buffer(self) -> None:
        """`io.StringIO`（測試替身最常見的形態）兩者皆無 ⇒ 安全 no-op，不拋
        AttributeError。這是 `tools/_stdio_utf8.py` 原本以 `hasattr` 守門承諾的行為，
        去重後必須一字不差地保留（`tools/tests/test_stdio_utf8.py` 亦鎖同一條）。"""
        import io

        fake_stdout, fake_stderr = io.StringIO(), io.StringIO()
        self.assertFalse(hasattr(fake_stdout, "reconfigure"))
        self.assertFalse(hasattr(fake_stdout, "buffer"))
        with mock.patch.object(sys, "stdout", fake_stdout), \
                mock.patch.object(sys, "stderr", fake_stderr):
            m.init_utf8_streams()  # 不應拋例外
            self.assertIs(sys.stdout, fake_stdout, "no-op 路徑不得換掉串流物件")


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
# 有一支公認的共用入口（`import _stdio_utf8`，R74 實測 15 支消費者），但仍有檔案直接寫
# `sys.stdout.reconfigure(encoding="utf-8", ...)` 就地重做一次。
#
# 🔴 **R75 訂正（本段原文自己就是那個病）**：上一行原本逐字寫「`tools/_stdio_utf8.py`
# **已經是 SSOT**」。那句話在寫下的當時就是假的——同一份知識當時有**兩個各自宣稱是
# SSOT 的家**：`tools/_stdio_utf8.py::reconfigure_stdio_utf8`（`.reconfigure()` 就地改、
# import 期生效）與 `tools/lib/platform_utils.py::init_utf8_streams`（`TextIOWrapper`
# 換掉串流、只在 `__main__` 呼叫），實作／啟用時機／對測試替身的行為三者皆不同，而
# 本檔的兩把鎖（`:335` 的 def 唯一性、下方這個行內複本棘輪）**都只守自己那一支**。
# 把「其中一支是 SSOT」寫成註解，正是讓那個衝突躲過複審的原因（同 R73「訂正註記逐字
# 引述假話＝製造新假話」）。R75 已真正去重（唯一實作＝`tools/lib/platform_utils.py`，
# `_stdio_utf8` 逐字委派同一個函式物件），並補上
# `TestR75StdioUtf8HasOneImplementation`——**兩把鎖從此看得見彼此**。
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
#: 🔴 R75：**唯一實作**所在（`reconfigure_stdio_utf8`，import 期即生效）。
#: 選它而非 `tools/lib/platform_utils.py` 的理由＝**可搬遷契約**（見該檔檔頭與下方
#: `test_the_ssot_survives_being_copied_out_of_the_repo`）。
_STDIO_IMPL_REL = "tools/_stdio_utf8.py"
#: 委派方（公開名 `init_utf8_streams` 沿用，8 支 AutoClaude hook／工具的呼叫端不動）。
_STDIO_DELEGATE_REL = "tools/lib/platform_utils.py"
_STDIO_SSOT_REL = _STDIO_IMPL_REL  # 沿用舊名（訊息文字與既有斷言引用它）
_STDIO_SSOT_IMPORT_RE = re.compile(r"^\s*import\s+_stdio_utf8\b", re.M)
#: 走委派那個公開名的消費者。
_STDIO_DELEGATE_IMPORT_RE = re.compile(r"^\s*from\s+platform_utils\s+import\b", re.M)

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


#: 唯一實作的住址 ＋ 判準的**定義側**（本檔）——只有這兩者不算「複本」。
#: 🔴 委派方（`tools/lib/platform_utils.py`）**刻意不在此列**：它只准委派、不准自帶機制，
#: 一旦有人在那裡再寫一份就必須被算進棘輪而轉紅。
#: 本檔是判準的定義側（樣式字面 ＋ 判準自檢樣本各命中數次），把定義側算進使用側會讓
#: 判準自我循環——同 `sc7_every_used_scan_code_is_defined` 刻意排除維度表自己的理由。
_SELF_REL = Path(__file__).resolve().relative_to(_REPO_ROOT).as_posix()
_STDIO_LEGIT_HOMES = frozenset({_STDIO_IMPL_REL, _SELF_REL})


def inline_stdio_sites() -> dict[str, int]:
    """全掃描面（含 untracked）的行內 stdio-UTF-8 複本；SSOT 自己不算。"""
    out: dict[str, int] = {}
    skip = set(_STDIO_LEGIT_HOMES)
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


# ══════════════════════════════════════════════════════════════════════════════
# R75：「強制 stdio 為 UTF-8」只准有一份實作 —— 讓兩把鎖看得見彼此
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 缺陷本體（本輪主題正中靶心）：同一份知識先前有**兩個各自宣稱是 SSOT 的家**，
# 手法／啟用時機／對測試替身的行為三者皆不同，消費端分屬兩群（8 支 AutoClaude hook 走
# `from platform_utils import init_utf8_streams`、15 支根層 tools 走 `import _stdio_utf8`），
# 換用另一支會**靜默改變行為**；而既有兩把鎖（`:335` def 唯一性、上方行內複本棘輪）
# 都只守自己那一支，沒有任何機械物在看「這兩者是同一份知識」。
# R74 的 P0（`sys.stderr` 預設 `errors='backslashreplace'` 讓 hook 中文指引在非 CJK
# codepage 降解）正好就落在這一層。
#
# 本節是「去重之後不准再散開」的機械物，三個方向各一把牙：
#   ① **委派不可退化**：兩個公開名必須是**同一個函式物件**，且 shim 檔內不得有任何
#      `def`——「保留公開名以免動消費端」與「其實各自寫了一份」在原始碼上長得很像，
#      物件同一性是唯一分得清的判準（同 `test_hints_and_tag_are_shared_with_the_
#      runtime_lock_not_copied` 既有手法）。
#   ② **SSOT 必須真的實作**：唯一實作那一支若哪天被改成也去 import 別人（或實作被搬走），
#      ①會照樣成立而整組變成恆綠空砲。故正向釘住「實作的兩條路徑都在該函式體內」。
#   ③ **第三份實作長出來即紅**：判準面刻意比上方 `_INLINE_STDIO_RE` **寬**——它只認
#      `sys.stdout.reconfigure(` 這一種寫法，對 `for s in (sys.stdout, sys.stderr):
#      s.reconfigure(encoding=…)` 這個**實際上最普遍的寫法**結構性全盲（R75 實測：窄判準
#      看得到 9 處／8 檔，寬判準看得到 81 處／77 檔——也就是既有棘輪只看到約一成）。
#      這正是 R73「已知的鎖射程缺口不得只以劃界結案」的形態，故本節補上寬判準。
_STDIO_FORCE_RE = re.compile(
    # a) 任何串流的 `reconfigure(encoding=…)`（含 `for s in (sys.stdout, sys.stderr)`
    #    迴圈變數、以及唯一實作內的裸區域名呼叫）
    r"(?:\breconfigure\s*\(\s*encoding)"
    # b) 直接拿 std 串流的 `.buffer` 包 TextIOWrapper（去重前 `init_utf8_streams` 的手法）
    r"|(?:TextIOWrapper\s*\(\s*(?:sys\.)?std(?:out|err)\s*\.\s*buffer)"
)

#: 凍結版 SDD 樹（Copy-on-Evolve 政策：一律不可改）——單獨成一格，讓「不可修的存量」
#: 與「可修的存量」在基線表上就分得開，而不是混成一個數字之後沒人分得清哪些其實能收斂。
_FROZEN_SDD_TREE_KEY = "AISDLC_SDD/<frozen-versions>"
_FROZEN_SDD_PREFIX = "AISDLC_SDD/AISDLC_SDD_v"
_STDIO_TREE_PREFIXES: tuple[str, ...] = (
    ".claude/hooks", "AISDLC_SDD/scripts", "AutoClaude", "tools",
)

#: 🔴 **shrink-only 棘輪（per-tree）**：R75 實測值，只准變少。
#: 為何是 per-tree 而非 per-file（與上方窄判準的取捨差異，必須寫下來）：寬判準命中 77 檔，
#: 逐檔列名會讓本檔多出近八十行**且大半落在其他包的所有權內**（並行包互踩＝假紅）。
#: per-tree 仍保有「新增一處即紅」的牙，失去的只是「訊息逐字指名哪一支」——而那個由
#: 斷言失敗時當場現查的明細補回（見 `stdio_force_problems` 的訊息）。
_FROZEN_STDIO_FORCE_TREES: dict[str, int] = {
    ".claude/hooks": 2,
    _FROZEN_SDD_TREE_KEY: 36,
    "AISDLC_SDD/scripts": 10,
    # R75 收輪下修 26→24：`AutoClaude/tmp_lint_check.py` 是 tracked 的一次性除錯腳本
    # （內容＝重跑 `lint-imports` CLI 已有的行為），本輪依「暫存檔直接刪」慣例 `git rm`，
    # 連帶少掉它自帶的 2 處行內複本。棘輪只准變少，故同步下修而非留餘裕。
    "AutoClaude": 24,
    "tools": 6,
}


def stdio_force_tree_of(rel: str) -> str:
    """repo 相對路徑 → 棘輪基線表的樹名（純函式，供合成注入自證）。

    落在所有已知前綴之外的新樹回 `"<other>"`——**不是靜默放行**：`"<other>"` 不在基線表
    內，`stdio_force_problems` 會要求它顯式入表（同 `posix_tag_ratchet_problems` 對
    「出現在掃描面卻不在基線表」的處置）。
    """
    if rel.startswith(_FROZEN_SDD_PREFIX):
        return _FROZEN_SDD_TREE_KEY
    for prefix in _STDIO_TREE_PREFIXES:
        if rel.startswith(prefix + "/"):
            return prefix
    return "<other>"


def stdio_force_sites() -> dict[str, list[str]]:
    """全掃描面（含 untracked）的「強制 stdio 為 UTF-8」複本：`{樹名: [檔(命中數), …]}`。

    兩個公開名的合法住址與本檔（判準定義側）一律排除，見 `_STDIO_LEGIT_HOMES`。
    """
    out: dict[str, list[str]] = {}
    for rel in _repo_py_files():
        if rel in _STDIO_LEGIT_HOMES:
            continue
        hits = len(_STDIO_FORCE_RE.findall(_read_scanned(rel)))
        if hits:
            out.setdefault(stdio_force_tree_of(rel), []).append(f"{rel}({hits})")
    return out


def stdio_force_counts(sites: Mapping[str, list[str]]) -> dict[str, int]:
    """`stdio_force_sites()` → `{樹名: 命中總數}`（純函式）。"""
    return {
        tree: sum(int(entry.rsplit("(", 1)[1].rstrip(")")) for entry in entries)
        for tree, entries in sites.items()
    }


def stdio_force_problems(
    frozen: Mapping[str, int], counts: Mapping[str, int]
) -> list[str]:
    """棘輪判準（純函式，供合成注入自證）：任一樹命中數上升、新樹未入表、
    或樹在表內卻從掃描面消失（＝射程疑似縮小），皆為違規。"""
    problems: list[str] = []
    for tree in sorted(set(frozen) | set(counts)):
        want = frozen.get(tree)
        got = counts.get(tree)
        if want is None:
            problems.append(
                f"{tree}：出現在掃描面卻不在基線表內（實測 {got}）"
                "——新樹必須顯式入表，否則它的複本靜默不計"
            )
        elif got is None:
            problems.append(f"{tree}：在基線表內卻不在掃描面（基線 {want}）——射程疑似縮小")
        elif got > want:
            problems.append(f"{tree}：強制 stdio-UTF-8 的複本 {got} 處 > 凍結值 {want} 處")
    return problems


class TestR75StdioUtf8HasOneImplementation(unittest.TestCase):
    """「強制 stdio 為 UTF-8」的**唯一實作**不變量（R75）。"""

    @staticmethod
    def _ssot():
        """唯一實作（`tools/_stdio_utf8.py`）。

        ⚠️ import 它會**真的**對本進程的 stdout/stderr 動手（那就是它存在的理由）——
        但同一件事 `tools/tests/test_stdio_utf8.py` 早已在同一輪 discovery 裡做過，
        故本測試不引入新的副作用，只是共用它。
        """
        sys.path.insert(0, str(_REPO_ROOT / "tools"))
        import _stdio_utf8

        return _stdio_utf8

    def test_the_delegate_resolves_to_the_ssot_function(self) -> None:
        """① 委派不可退化成獨立複本：委派方解析出來的必須就是 SSOT 那個函式物件。

        驗「同一性」而非「行為等價」：行為等價可以由兩份各自寫對的複本滿足，而那正是
        R75 前的狀態（兩份**都能**強制 UTF-8，差別在啟用時機與測試替身行為，於是沒人
        發現它們是兩份）。同一性是唯一能把「委派」與「巧合一致」分開的判準。
        """
        self.assertIs(
            m._stdio_utf8_impl(), self._ssot().reconfigure_stdio_utf8,
            f"{_STDIO_DELEGATE_REL} 的委派沒有解析到 {_STDIO_IMPL_REL} 的 "
            "reconfigure_stdio_utf8 ⇒ 退化成第二份實作或解析壞了",
        )

    def test_the_delegate_holds_no_mechanism_of_its_own(self) -> None:
        """① 的另一半（原始碼側）：委派方檔內不得出現任何強制 stdio 的**機制**。

        只驗同一性不夠：有人可以在委派方新寫一支「解析失敗時的內建回退」當補強，
        同一性斷言照樣綠，而第二份實作已經進來了。判準用的是與③同一個寬樣式
        ——共用判準才不會兩邊各自漂移。
        """
        hits = _STDIO_FORCE_RE.findall(_read_scanned(_STDIO_DELEGATE_REL))
        self.assertEqual(
            hits, [],
            f"{_STDIO_DELEGATE_REL} 出現了 {len(hits)} 處強制 stdio 的機制（{hits}）"
            f"——它只准委派到 {_STDIO_IMPL_REL}。若真的需要回退，回退本身就是第二份實作，"
            "請改成讓 SSOT 自我完備（那正是 R75 選它當 SSOT 的理由）",
        )

    def test_the_ssot_really_holds_the_implementation(self) -> None:
        """② 反空砲：唯一實作那一支必須真的三條分支都在它體內。

        缺這條時，把 SSOT 改成「去 import 別人」也能讓①全綠——整組鎖變成恆綠空砲
        （同本檔 `test_platform_judgment_helpers_*` 的「反方向的牙」）。
        """
        src = inspect.getsource(self._ssot().reconfigure_stdio_utf8)
        self.assertIn("reconfigure(", src, "SSOT 內找不到就地 reconfigure 那條路徑")
        self.assertIn("TextIOWrapper(", src, "SSOT 內找不到 wrapper 回退那條路徑")
        self.assertIn('errors="replace"', src,
                      "errors 必須顯式為 replace——R74 P0 的成因正是 stderr 預設 "
                      "backslashreplace 讓中文指引降解成 \\uXXXX 字面")

    def test_the_ssot_only_imports_stdlib(self) -> None:
        """🔴 **可搬遷契約（原始碼側）**：SSOT 一個本地 import 都不准有。

        WHY 這條是 blocking 級（R75 第一版當回合實測付過代價）：本檔的既有契約包含
        「被複製到別處單獨執行」——`AISDLC_SDD/scripts/tests/test_copy_on_evolve.py`／
        `test_ntfs_length_gate.py` 會把 `tools/check_ntfs_paths.py` 連同它複製進 tmp
        沙箱 repo（**不含 `tools/lib/`**）再以子行程執行。R75 第一版把實作搬去
        `tools/lib/platform_utils.py`、讓它改成 `from platform_utils import …`，沙箱裡
        import 期 `ModuleNotFoundError`，6 支測試當場紅。
        ⇒ 去重方案不得讓這支基礎件相依於 repo 佈局。
        """
        allowed = {"io", "sys", "__future__"}
        tree = ast.parse((_REPO_ROOT / _STDIO_IMPL_REL).read_text(encoding="utf-8"))
        bad: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                bad += [a.name for a in node.names if a.name.split(".")[0] not in allowed]
            elif isinstance(node, ast.ImportFrom):
                mod_name = node.module or ""
                if node.level or mod_name.split(".")[0] not in allowed:
                    bad.append(f"{'.' * node.level}{mod_name}")
        self.assertEqual(
            bad, [],
            f"{_STDIO_IMPL_REL} import 了非 stdlib 的 {bad} ⇒ 破壞可搬遷契約"
            "（被複製到不含 tools/lib/ 的沙箱時 import 期就會爆，連帶讓消費端全滅）",
        )

    def test_the_ssot_survives_being_copied_out_of_the_repo(self) -> None:
        """🔴 **可搬遷契約（行為側）**：把 SSOT 單獨複製到 tmp 後 import 必須成功，
        且在 R74 P0 的重現環境（`PYTHONIOENCODING=cp1252` ＋剝掉 `PYTHONUTF8`）下
        中文仍不降解。

        只驗「import 不爆」不夠：no-op 降級也能讓 import 成功，但保護就靜默消失了
        ——而沙箱裡那些子行程正是靠這道保護在印中文。故連保護效果一起驗。
        """
        with tempfile.TemporaryDirectory() as td:
            box = Path(td)
            shutil.copy(_REPO_ROOT / _STDIO_IMPL_REL, box / "_stdio_utf8.py")
            probe = box / "probe.py"
            # 探針刻意不帶 lint 抑制註解：`test_no_invalid_escape_sequences.py` 會掃本檔的
            # 字串字面、把「規則碼後緊接非空白」判為非法抑制（實測當回合被它抓到）。
            probe.write_text(
                "import _stdio_utf8\n"
                "import sys\n"
                "assert _stdio_utf8.reconfigure_stdio_utf8 is not None\n"
                "print('中文')\n"
                "print('中文', file=sys.stderr)\n",
                encoding="utf-8", newline="\n",
            )
            env = dict(os.environ)
            env.pop("PYTHONUTF8", None)
            env["PYTHONIOENCODING"] = "cp1252"
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            done = subprocess.run(
                [sys.executable, str(probe)], cwd=str(box), capture_output=True, env=env
            )
        want = "中文".encode()
        self.assertEqual(
            done.returncode, 0,
            f"單獨複製到 tmp 後 import 失敗（rc={done.returncode}）："
            f"{done.stderr.decode('utf-8', 'replace')[:400]}",
        )
        self.assertIn(want, done.stdout, "複製版的 stdout 保護失效（中文降解）")
        self.assertIn(want, done.stderr, "複製版的 stderr 保護失效（中文降解）")

    def test_both_public_names_have_real_consumers(self) -> None:
        """兩個公開名都必須有真消費者，否則「保留兩個名字」的理由不成立。"""
        ssot_users, delegate_users = [], []
        for rel in _repo_py_files():
            if rel in _STDIO_LEGIT_HOMES:
                continue
            text = _read_scanned(rel)
            if _STDIO_SSOT_IMPORT_RE.search(text):
                ssot_users.append(rel)
            if _STDIO_DELEGATE_IMPORT_RE.search(text) and "init_utf8_streams" in text:
                delegate_users.append(rel)
        self.assertGreaterEqual(len(ssot_users), 10,
                                f"`import _stdio_utf8` 消費者異常少（{len(ssot_users)}）")
        self.assertGreaterEqual(
            len(delegate_users), 6,
            f"`from platform_utils import init_utf8_streams` 消費者異常少"
            f"（{len(delegate_users)}：{delegate_users}）——若真的歸零，該刪掉的是那個公開名",
        )

    def test_no_third_implementation_grows(self) -> None:
        """③ shrink-only 棘輪：任一樹再長出一處「自己重做一次」即紅。"""
        sites = stdio_force_sites()
        problems = stdio_force_problems(_FROZEN_STDIO_FORCE_TREES, stdio_force_counts(sites))
        self.assertEqual(
            problems, [],
            "強制 stdio-UTF-8 的複本增加了：\n  " + "\n  ".join(problems)
            + "\n現況明細：\n  "
            + "\n  ".join(f"{tree}: {entries}" for tree, entries in sorted(sites.items()))
            + f"\n修法＝改用唯一實作：根層工具 `import _stdio_utf8`（{_STDIO_IMPL_REL}，"
            f"import 期即生效）／其他樹 `from platform_utils import init_utf8_streams`"
            f"（{_STDIO_DELEGATE_REL} 的委派，於 `__main__` 呼叫）。本棘輪是 shrink-only：要新增"
            "一處必須先論證為何不能用它（例：`.claude/hooks/block_bash_on_windows.py` "
            "的 fail-open 契約，該檔已就地寫明理由）",
        )

    def test_frozen_trees_match_the_worktree(self) -> None:
        """自緊：收斂掉一處而不下修基線 ⇒ 餘裕就是破口（同 `_FROZEN_INLINE_STDIO_SITES`）。"""
        self.assertEqual(
            stdio_force_counts(stdio_force_sites()), dict(_FROZEN_STDIO_FORCE_TREES),
            "工作樹現況與 `_FROZEN_STDIO_FORCE_TREES` 已漂移——收斂掉一處後請同步下修")

    def test_the_wide_pattern_sees_what_the_narrow_one_cannot(self) -> None:
        """判準自檢：寬判準必須抓到窄判準結構性看不到的那種寫法，否則③白做。"""
        loop_form = (
            "for _stream in (sys.stdout, sys.stderr):\n"
            '    _stream.reconfigure(encoding="utf-8")\n'
        )
        self.assertIsNone(_INLINE_STDIO_RE.search(loop_form),
                          "窄判準竟看得到迴圈形態——本節的立論前提不成立")
        self.assertIsNotNone(_STDIO_FORCE_RE.search(loop_form), "寬判準漏掉迴圈形態")
        self.assertIsNotNone(
            _STDIO_FORCE_RE.search('io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")'),
            "寬判準漏掉 wrapper 形態（去重前 init_utf8_streams 的手法）")
        self.assertIsNone(
            _STDIO_FORCE_RE.search("f.reconfigure(errors='replace')"),
            "沒帶 encoding= 的 reconfigure 不是本判準的對象（誤報的鎖最後一定被繞過）")

    def test_the_tree_ratchet_has_teeth(self) -> None:
        """合成注入（不碰磁碟）：上升／新樹／樹消失三種形態都必須被點名。"""
        frozen = {"tools": 1}
        self.assertTrue(stdio_force_problems(frozen, {"tools": 2}))
        self.assertTrue(stdio_force_problems(frozen, {"tools": 1, "<other>": 1}))
        self.assertTrue(stdio_force_problems(frozen, {}))
        self.assertEqual(stdio_force_problems(frozen, {"tools": 1}), [])
        self.assertEqual(stdio_force_problems(frozen, {"tools": 0}), [],
                         "收斂到零不得被判違規——棘輪的方向只有一個")

    def test_tree_classification_boundary(self) -> None:
        """樹分類：凍結版 SDD 與活躍樹必須分得開，未知樹不得被靜默歸進既有樹。"""
        self.assertEqual(
            stdio_force_tree_of("AISDLC_SDD/AISDLC_SDD_v0.01/tools/arch_fitness/arch_fitness.py"),
            _FROZEN_SDD_TREE_KEY)
        self.assertEqual(stdio_force_tree_of("AISDLC_SDD/scripts/sdd_version.py"),
                         "AISDLC_SDD/scripts")
        self.assertEqual(stdio_force_tree_of("AutoClaude/tools/local_ci_gate.py"), "AutoClaude")
        self.assertEqual(stdio_force_tree_of("tools/bootstrap_core.py"), "tools")
        self.assertEqual(stdio_force_tree_of("brand_new_tree/helper.py"), "<other>")


if __name__ == "__main__":
    unittest.main()
