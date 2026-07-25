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

  對這 7 支檔案逐一用該既有 AST 掃描邏輯（掃描「風險識別字是否裸露出現在組
  檔名的 f-string/字串串接/`%`/`.format()` 表達式中」）做對抗式驗證時，實測發現
  兩個真實盲點，會讓搬過來的版本對兩支檔案完全失去鑑別力（bug-injection 用
  `git show <固定基線 commit>:<path>` 取得修復前的真實歷史內容重放驗證，証實
  下列兩者在修復前『0 offenders』——即該掃描法看不到真正的漏洞；此固定基線
  commit 的選擇理由見下方 `_PRE_FIX_BASELINE_SHA` 常數註解與
  `TestExpectedSanitizeCallDiscriminatesRealHistoricalRegression` docstring
  ——R44 QA 一審發現原本用 `git show HEAD:<path>` 會在本輪修復 commit 之後
  永久恆紅，已修正為錨定固定 SHA）：

    (a) `production_to_fpl.py::generate_fpl_draft()`：修復前寫法
        `fid = fpl_id or f"FPL-PROD-{ac_id}-{divergence_kind}"`——內層 f-string
        本身不以 `.md`/`.yaml` 等副檔名結尾（副檔名是下一行
        `f"{fid}.md"` 才組上去的兩段式間接組檔名），泛用掃描的
        『f-string 字面結尾是否像檔名』判準因此不會命中這個 f-string，风险
        識別字裸露完全被漏放。

    (b) `counterfactual_replay.py::write_report()`：修復前寫法
        `f"REPLAY-{patch.ac_id or 'unknown'}-{date}.md"`——`FormattedValue`
        內是 `patch.ac_id or 'unknown'`（`ast.BoolOp`），泛用掃描的
        `_raw_risky_reference()` 只認得裸 `Name`/`Attribute`/`Subscript`，
        不會拆解 `BoolOp` 找出裡面包的 `Attribute`，同樣被漏放。

  這兩個盲點目前也存在於 v0.30 端既有的 `test_sanitize_component_call_site_lock.py`
  本身（R44 對該檔案做同款 bug-injection 交叉驗證證實，非本檔新引入的缺陷；
  修復/回報該既有盲點超出本輪 P2 finding 的範圍，僅在此如實記載，供下一輪
  評估是否值得投入修復那份泛用掃描器）。若要讓泛用 AST 掃描器同時涵蓋這兩種
  形狀，需要遞迴拆解 `BoolOp`/追蹤『組檔名用到的中繼變數是否源自另一個本身不
  以副檔名結尾的 f-string』——複雜度與投入不成比例（Rule 2 比例原則），對
  **本質靜態、Copy-on-Evolve 之後不再變動**的 29 份凍結快照而言，改用下列
  更簡單也更精準的手法：直接對每支檔案的『已知修復呼叫式』（如
  `_sanitize_component(rule_id)`）做逐版正向存在性斷言——不管該呼叫式週邊的
  程式碼結構多複雜、外層是否為 `BoolOp`/兩段式間接組檔名，只要修復呼叫式本身
  被移除或還原，正向斷言必定測不到而失敗。本檔頂部 bug-injection 驗證
  （見下方 `TestExpectedSanitizeCallDiscriminatesRealHistoricalRegression`）
  逐一以 `git show <固定基線 commit>:<path>` 重放全部 7 支檔案修復前的真實
  歷史內容，證實這個更簡單的正向斷言對全部 7 支檔案、包含上述兩個泛用掃描
  盲點案例，均正確判定為「未通過」。

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

執行：python -m pytest tools/tests/test_sanitize_component_frozen_sdd_versions_lock.py -v
"""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SDD_ROOT = _REPO_ROOT / "AISDLC_SDD"

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

_FROZEN_VERSION_DIR_RE = re.compile(r"^AISDLC_SDD_v\d+\.\d+$")

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
    """LATEST 版本名（sdd_version.py SSOT）。手法同
    tools/tests/test_windowsapps_guard_bash_parity.py::_latest_sdd_version_name
    ——subprocess 呼叫 CLI，避免 sys.path 汙染；解析失敗即 fail-loud。"""
    resolver = _SDD_ROOT / "scripts" / "sdd_version.py"
    proc = subprocess.run(
        [sys.executable, str(resolver), "--sdd-root", str(_SDD_ROOT)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    name = proc.stdout.strip()
    if proc.returncode != 0 or not name:
        raise AssertionError(
            f"LATEST 解析失敗（sdd_version.py rc={proc.returncode}；stderr="
            f"{proc.stderr.strip()!r}）——掃描邊界不得靜默縮小"
        )
    return name


def _frozen_version_dirs(latest_name: str) -> list[Path]:
    """全部凍結版本目錄（`AISDLC_SDD_v*`，排除 LATEST），依版本名稱排序。"""
    dirs = [
        p for p in _SDD_ROOT.iterdir()
        if p.is_dir() and _FROZEN_VERSION_DIR_RE.match(p.name) and p.name != latest_name
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


if __name__ == "__main__":
    unittest.main()
