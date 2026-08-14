#!/usr/bin/env python3
"""DEF-101-357 路徑穿越修復 — 29 版凍結基線 × 7 檔案回歸鎖（R44 Architect 二審建議）。

背景：R44 對 `AISDLC_SDD_v0.01`～`v0.29` 共 29 個凍結基線版本的 7 支
`tools/fsm_runtime/` 檔案（`hub_sync.py`／`production_monitor.py`／`hub_merge.py`／
`spec_patch_proposer.py`／`production_to_fpl.py`／`sandbox_runner.py`／
`counterfactual_replay.py`）逐版套用「呼叫該版本既有 `_sanitize_component()`」的
P0 路徑穿越修復（`rule_id`/`nfr_id`/`ac_id`/`fpl_id`/`divergence_kind`/`app_id`
等使用者可控字串未經淨化即組進檔案路徑 f-string，可逃出預期目錄讀到任意檔案）。
本輪由使用者明確核准、破例打破 Copy-on-Evolve 鐵律對 29 份凍結快照原地補丁
（見 `docs/06_quality/AutoSDD_Defect_Log.md::DEF-101-357`）。

Architect 二審發現：這 203 處改動（29 版 × 7 檔）完全沒有任何常駐測試鎖住——
每版 `tools/fsm_runtime/tests/` 目錄本身沒有對應測試（那些測試只存在於 v0.30/
LATEST），且既有 repo-wide 掃描（`tools/tests/test_windowsapps_guard_*.py`）
只涵蓋 WindowsApps python 可用性判斷、不涵蓋這個路徑穿越修復類別。若未來任一
版任一檔被意外還原（順手重構／merge 衝突誤解／另一支自動化腳本覆寫），目前
沒有任何測試會抓到。本檔補上對稱的 repo-wide 靜態鎖。

方法論選擇（**刻意不**直接搬 v0.30 端既有的
`test_sanitize_component_call_site_lock.py` 泛用 AST 掃描邏輯，而是改用逐檔
「已知淨化呼叫式必須存在」的正向斷言）：

  逐項理由（不搬 v0.30 泛用 AST 掃描的兩個實測盲點、bug-injection 的固定基線 SHA
  錨定、正向斷言對 7 支檔案的鑑別力驗證）原文逐字＝
  `docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`。

方法論邊界（誠實記載）：
  - 本檢查只驗證『已知淨化呼叫式的字面文字仍存在於檔案中（非注釋內）』，非
    真正的資料流/AST 語意驗證——若該呼叫式被複製到一個完全無關、不影響組
    檔名路徑的死碼分支，本鎖仍會判定通過（誤判為安全）。這類『刻意規避』手法
    需要真正的控制流分析才能封閉，比照 WindowsApps 鎖與
    `test_sanitize_component_call_site_lock.py` 既有記載的同級方法論邊界，
    此為已知限制而非本檔涵蓋範圍。
  - 只掃描凍結版本（`AISDLC_SDD_v0.01`～目前 LATEST 之前所有版本，動態排除
    LATEST——LATEST 由 `test_sanitize_component_call_site_lock.py` 用不同機制
    〔泛用 AST 掃描 + `_ADDITIONAL_RISKY_NAMES` 委派 wrapper 名單〕獨立守護，
    兩者分工互補，不重複亦不遺漏）。

R66 追加（Review round 1 QA 發現，DEF-101-627）：`tools/lib/sdd_latest.py`
（R66 新增，DEF-101-624）當時只做手動 bug-injection 驗證、未落成任何測試檔的
永久斷言。本應為它新增專屬 `tools/tests/test_sdd_latest.py`，但 `DEF-101-561③`
棘輪（`test_adr_xplat001_c1c2_lock.py::TestGuardLayerRatchet`）
自 R61 起要求 `tools/tests/` 擴充既有檔、或先合併／刪除等量舊物再加
（🔴 R78 ARCH-03 訂正：R66 當時量的是**檔數**、語意是「禁止新增」；R77 起改量逐檔
行數的**淨額**，新增檔案本身不違規，淨額上升才違規）
——故把本檔自己呼叫端（`_frozen_version_dirs`）的 `.fullmatch()` call-site 鎖
＋ `exclude_frozen_sdd_versions` 的過濾語意併入本檔（本檔是原始兩個肇事呼叫端
之一，且已 import `sdd_latest`）；`FROZEN_VERSION_DIR_RE` 本身的 `.fullmatch()`
行為回歸鎖與 `resolve_latest_name`/`resolve_latest_root` 覆蓋併入姊妹檔
`test_component_sanitizer_shared_layer_lock.py`（見該檔同款追加段）。

執行：python -m pytest tools/tests/test_sanitize_component_frozen_sdd_versions_lock.py -v
"""
from __future__ import annotations

import inspect
import re
import subprocess
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SDD_ROOT = _REPO_ROOT / "AISDLC_SDD"

sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
import sdd_latest  # noqa: E402

# 本輪 DEF-101-357 修復涵蓋的 7 支檔案（相對 <version>/tools/fsm_runtime/）。
_TARGET_FILES = (
    "hub_sync.py",
    "production_monitor.py",
    "hub_merge.py",
    "spec_patch_proposer.py",
    "production_to_fpl.py",
    "sandbox_runner.py",
    "counterfactual_replay.py",
)

# 每支檔案「已知修復呼叫式」的正則清單（皆逐版以 `git show <固定基線 commit>:<path>`
# 對修復前真實歷史內容重放驗證過：修復前一律不命中，見頂部 docstring 與下方
# TestExpectedSanitizeCallDiscriminatesRealHistoricalRegression）。允許呼叫式
# 前後有空白（`\s*`），不要求呼叫式週邊的外層程式碼結構（BinOp/BoolOp/兩段式
# 間接組檔名皆不影響——正向斷言只認呼叫式本身的字面文字是否存在）。
_EXPECTED_SANITIZE_CALLS: dict[str, tuple[str, ...]] = {
    "hub_sync.py": (r"_sanitize_component\(\s*rule_id\s*\)",),
    "production_monitor.py": (r"_sanitize_component\(\s*nfr_id\s*\)",),
    "hub_merge.py": (r"_sanitize_component\(\s*rule_id\s*\)",),
    "spec_patch_proposer.py": (r"_sanitize_component\(\s*ac_id\s*\)",),
    "production_to_fpl.py": (
        r"_sanitize_component\(\s*fpl_id\s*\)",
        r"_sanitize_component\(\s*ac_id\s*\)",
        r"_sanitize_component\(\s*divergence_kind\s*\)",
    ),
    "sandbox_runner.py": (r"_sanitize_component\(\s*spec\.app_id\s*\)",),
    "counterfactual_replay.py": (r"_sanitize_component\(\s*patch\.ac_id\s*\)",),
}

# 每支檔案須從 state_loader 匯入 _sanitize_component SSOT（防止有人另外重新
# 發明一個同名但無關的本地函式來滿足上面的文字比對）。
_IMPORT_LINE_RE = re.compile(r"from\s+\.state_loader\s+import\s+.*_sanitize_component")

# 已知需要達到的凍結版本下限（29；R44 建檔時的實際數量）。若未來新增版本，
# 此下限只會被超過、不會被打破；若數字倒退，代表掃描邊界被靜默縮小，須查明。
_MIN_EXPECTED_FROZEN_VERSIONS = 29

# bug-injection 鑑別力鎖的「修復前」重放基準點——固定錨定在本輪 DEF-101-357
# 修復（29 版 × 7 檔 203 處改動）尚未提交前的父提交（R43 收尾 commit），刻意
# 不用 `git show HEAD:<path>`（R44 QA 一審發現：HEAD 會隨每次 commit 移動，
# 一旦本輪修復——含本測試檔自身——被 commit，HEAD 就變成『修復後』內容，
# `TestExpectedSanitizeCallDiscriminatesRealHistoricalRegression` 會對全部 7
# 支檔案恆紅，而非只在本輪修復提交前這段短暫視窗內成立）。改用此固定 SHA 後，
# 該測試永遠重放同一段『修復前』真實歷史內容，不受後續任何 commit 影響；若此
# commit 在未來因淺層 clone（CI `actions/checkout` 預設 fetch-depth=1）或歷史
# 重寫而不可達，`_pre_fix_baseline_text()` 會 skipTest（非 fail-red）。
_PRE_FIX_BASELINE_SHA = "5ccccb065a8209e430eaba25c6e8e4ba1727e4e6"


def _latest_sdd_version_name() -> str:
    """LATEST 版本名（sdd_version.py SSOT；解析失敗即 fail-loud）。委派
    tools/lib/sdd_latest.py 單一真相源（ADR-XPLAT-002 Phase 2-C，R66 收斂）。"""
    return sdd_latest.resolve_latest_name(_SDD_ROOT)


def _frozen_version_dirs(latest_name: str) -> list[Path]:
    """全部凍結版本目錄（`AISDLC_SDD_v*`，排除 LATEST），依版本名稱排序。"""
    dirs = [
        p for p in _SDD_ROOT.iterdir()
        if p.is_dir()
        and sdd_latest.FROZEN_VERSION_DIR_RE.fullmatch(p.name)
        and p.name != latest_name
    ]
    return sorted(dirs, key=lambda p: p.name)


def _strip_comment_lines(text: str) -> str:
    """移除整行皆為 `#` 註解的行（逐行 lstrip 後判斷），避免修復呼叫式被搬進
    註解文字後仍被誤判為「呼叫式存在」。不處理行尾裝飾性註解——本檔 7 支目標
    檔案的既有寫法皆無此情境，比例原則下不需比照 .ps1 端更嚴謹的引號狀態機。"""
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )


def _missing_sanitize_call_patterns(text: str, filename: str) -> list[str]:
    """回傳該檔案文字中，`_EXPECTED_SANITIZE_CALLS[filename]` 內未命中的正則清單
    （非注釋文字）。純函式，供下方主鎖與 bug-injection 單元測試共用。"""
    non_comment = _strip_comment_lines(text)
    return [
        pat for pat in _EXPECTED_SANITIZE_CALLS[filename]
        if not re.search(pat, non_comment)
    ]


class TestFrozenVersionScanBoundary(unittest.TestCase):
    """掃描邊界防腐化：凍結版本數量與目標檔案存在性須符合預期，否則代表掃描
    範圍被靜默縮小（同 WindowsApps 鎖 fail-loud 精神）。"""

    def test_at_least_29_frozen_versions_found(self) -> None:
        latest_name = _latest_sdd_version_name()
        frozen = _frozen_version_dirs(latest_name)
        self.assertGreaterEqual(
            len(frozen), _MIN_EXPECTED_FROZEN_VERSIONS,
            f"凍結版本數量只有 {len(frozen)}（預期至少 {_MIN_EXPECTED_FROZEN_VERSIONS}），"
            f"LATEST={latest_name}——掃描邊界是否被靜默縮小？",
        )

    def test_all_target_files_exist_in_every_frozen_version(self) -> None:
        latest_name = _latest_sdd_version_name()
        missing = []
        for version_dir in _frozen_version_dirs(latest_name):
            for fname in _TARGET_FILES:
                p = version_dir / "tools" / "fsm_runtime" / fname
                if not p.is_file():
                    missing.append(str(p.relative_to(_REPO_ROOT)))
        self.assertEqual(
            missing, [],
            f"以下凍結版本缺少 DEF-101-357 目標檔案：{missing}",
        )


class TestSanitizeComponentFixPresentInEveryFrozenVersion(unittest.TestCase):
    """主鎖：DEF-101-357 的 29 版 × 7 檔修復呼叫式必須持續存在（repo-wide 靜態
    掃描，不需碰凍結版本本身即可驗證——符合 Copy-on-Evolve 鐵律的唯讀查驗）。"""

    def test_sanitize_component_imported_in_every_target_file(self) -> None:
        latest_name = _latest_sdd_version_name()
        offenders = []
        for version_dir in _frozen_version_dirs(latest_name):
            for fname in _TARGET_FILES:
                p = version_dir / "tools" / "fsm_runtime" / fname
                text = p.read_text(encoding="utf-8", errors="replace")
                if not _IMPORT_LINE_RE.search(text):
                    offenders.append(str(p.relative_to(_REPO_ROOT)))
        self.assertEqual(
            offenders, [],
            f"以下檔案未從 .state_loader 匯入 _sanitize_component SSOT："
            f"{offenders}——DEF-101-357 修復是否被回退？",
        )

    def test_no_frozen_version_regresses_the_def_101_357_path_traversal_fix(self) -> None:
        latest_name = _latest_sdd_version_name()
        offenders: list[str] = []
        for version_dir in _frozen_version_dirs(latest_name):
            for fname in _TARGET_FILES:
                p = version_dir / "tools" / "fsm_runtime" / fname
                text = p.read_text(encoding="utf-8", errors="replace")
                missing_patterns = _missing_sanitize_call_patterns(text, fname)
                for pat in missing_patterns:
                    offenders.append(
                        f"{p.relative_to(_REPO_ROOT)}: 找不到已知修復呼叫式 `{pat}`"
                    )
        self.assertEqual(
            offenders, [],
            "發現凍結版本疑似回退 DEF-101-357 路徑穿越修復（已知 "
            f"_sanitize_component() 呼叫式消失）：{offenders}——若為誤判（如"
            "呼叫式改寫但淨化效果不變），請同步更新本檔 _EXPECTED_SANITIZE_CALLS；"
            "若為真實回退，須恢復呼叫式或另尋等效淨化並記入缺陷帳本。",
        )


class TestExpectedSanitizeCallDiscriminatesRealHistoricalRegression(unittest.TestCase):
    """bug-injection 鑑別力鎖：直接對 `_missing_sanitize_call_patterns` 純函式
    重放全部 7 支檔案『修復前』的真實歷史內容（`git show <固定基線 commit>:<path>`，
    固定基線＝`_PRE_FIX_BASELINE_SHA`，本輪 DEF-101-357 修復的父提交），證實
    正向斷言對每一支檔案的真實歷史漏洞都會判定為「未通過」（非本檔虛構的合成
    範例）。這是頂部 docstring 宣稱『對 7 支檔案皆有鑑別力，含
    production_to_fpl.py／counterfactual_replay.py 兩個泛用 AST 掃描盲點案例』
    的直接證據，非事後臆測。

    R44 QA 一審發現並修正的時序缺陷：初版用 `git show HEAD:<path>` 而非固定
    SHA，這個假設只在『本輪修復尚未 commit』的當下短暫成立——一旦本輪修復
    （含本測試檔自身）被 commit，HEAD 就會變成『修復後』內容，導致
    `test_every_target_file_pre_fix_head_content_fails_the_lock` 對全部 7 個
    subTest 恆紅。改錨定固定 SHA 後，重放內容不再受後續任何 commit 影響。"""

    def _pre_fix_baseline_text(self, fname: str) -> str:
        rel = f"AISDLC_SDD/AISDLC_SDD_v0.01/tools/fsm_runtime/{fname}"
        proc = subprocess.run(
            ["git", "-C", str(_REPO_ROOT), "show", f"{_PRE_FIX_BASELINE_SHA}:{rel}"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if proc.returncode != 0:
            self.skipTest(
                f"無法讀取固定基線 commit {_PRE_FIX_BASELINE_SHA}:{rel}"
                f"（rc={proc.returncode}；stderr={proc.stderr.strip()!r}）——"
                "可能是淺層 clone（CI checkout 預設 fetch-depth=1）缺乏這段歷史，"
                "或該 commit 因歷史重寫不可達；本測試的鑑別力已在 R44 建檔當下"
                "驗證過（見本檔頂部 docstring），此為環境限制導致的一般性 skip，"
                "非新缺陷"
            )
        return proc.stdout

    def test_every_target_file_pre_fix_head_content_fails_the_lock(self) -> None:
        for fname in _TARGET_FILES:
            with self.subTest(file=fname):
                pre_fix_text = self._pre_fix_baseline_text(fname)
                missing = _missing_sanitize_call_patterns(pre_fix_text, fname)
                self.assertTrue(
                    missing,
                    f"{fname} 的固定基線 commit（修復前）內容竟然滿足所有已知"
                    "修復呼叫式——本鎖對此檔案可能已無鑑別力，或 "
                    "_PRE_FIX_BASELINE_SHA 指向的內容已經是修復後版本",
                )

    def test_current_working_tree_content_passes_the_lock(self) -> None:
        """對照組：確認目前工作樹（修復後）內容確實通過，避免上一測試只是因為
        正則寫錯而『恆為 missing』的偽陽性鑑別力。"""
        for fname in _TARGET_FILES:
            with self.subTest(file=fname):
                p = (
                    _REPO_ROOT / "AISDLC_SDD" / "AISDLC_SDD_v0.01"
                    / "tools" / "fsm_runtime" / fname
                )
                text = p.read_text(encoding="utf-8", errors="replace")
                missing = _missing_sanitize_call_patterns(text, fname)
                self.assertEqual(
                    missing, [],
                    f"{fname} 目前工作樹內容未通過本鎖：{missing}",
                )


class TestOwnCallSiteStaysOnFullmatch(unittest.TestCase):
    """R66 追加（DEF-101-627）：本檔自己的 `_frozen_version_dirs()` call-site
    鎖——只鎖 `FROZEN_VERSION_DIR_RE` 本身的行為不足以擋住「呼叫端自己把
    `.fullmatch(` 又改回 `.match(`」這種退步，regex 定義正確、呼叫端方法用錯
    一樣重現原缺陷（DEF-101-624）。手法同 `test_dev_start.py::
    TestVenvSelfHealCallSitesUseSafeRmtree`（`inspect.getsource` +
    `assertIn`/`assertNotIn` 原始碼字面檢查）。"""

    def test_frozen_version_dirs_uses_fullmatch(self) -> None:
        src = inspect.getsource(_frozen_version_dirs)
        self.assertIn(
            "FROZEN_VERSION_DIR_RE.fullmatch(", src,
            "_frozen_version_dirs() 不再呼叫 .fullmatch( — DEF-101-624 修復被還原")
        self.assertNotIn(
            "FROZEN_VERSION_DIR_RE.match(", src,
            "_frozen_version_dirs() 又改回裸 .match( — 帶尾隨換行字元的偽造目錄名"
            "會被誤判為合法版本目錄（DEF-101-624 迴歸）")


class TestExcludeFrozenSddVersions(unittest.TestCase):
    """R66 追加（DEF-101-627）：`sdd_latest.exclude_frozen_sdd_versions` 的過濾
    語意——凍結版本路徑剔除、LATEST 路徑保留、非 `AISDLC_SDD/` 前綴路徑不受
    影響、空輸入邊界。此函式收斂了 3 支消費者檔（`test_windows_forbidden_
    filename_parity.py`／`test_windowsapps_guard_bash_parity.py`／
    `test_windowsapps_guard_cross_consistency.py`）原本各自的複本，但收斂當下
    同樣沒有落成任何專屬測試——原因與影響範圍同本檔頂部 R66 追加段。"""

    _LATEST = "AISDLC_SDD_v0.30"

    def test_drops_frozen_version_paths(self) -> None:
        paths = ["AISDLC_SDD/AISDLC_SDD_v0.01/foo.py"]
        self.assertEqual(sdd_latest.exclude_frozen_sdd_versions(paths, self._LATEST), [])

    def test_keeps_latest_version_paths(self) -> None:
        paths = ["AISDLC_SDD/AISDLC_SDD_v0.30/foo.py"]
        self.assertEqual(sdd_latest.exclude_frozen_sdd_versions(paths, self._LATEST), paths)

    def test_keeps_paths_outside_aisdlc_sdd_prefix(self) -> None:
        paths = ["tools/foo.py", "AutoClaude/bar.py"]
        self.assertEqual(sdd_latest.exclude_frozen_sdd_versions(paths, self._LATEST), paths)

    def test_mixed_list_keeps_only_non_frozen(self) -> None:
        paths = [
            "AISDLC_SDD/AISDLC_SDD_v0.01/a.py",
            "AISDLC_SDD/AISDLC_SDD_v0.30/b.py",
            "tools/c.py",
            "AISDLC_SDD/AISDLC_SDD_v0.29/d.py",
        ]
        expected = ["AISDLC_SDD/AISDLC_SDD_v0.30/b.py", "tools/c.py"]
        self.assertEqual(sdd_latest.exclude_frozen_sdd_versions(paths, self._LATEST), expected)

    def test_empty_input_returns_empty(self) -> None:
        self.assertEqual(sdd_latest.exclude_frozen_sdd_versions([], self._LATEST), [])


if __name__ == "__main__":
    unittest.main()
