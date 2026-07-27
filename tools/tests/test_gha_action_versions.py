#!/usr/bin/env python3
"""R57 round 3 補的兩道 workflow 結構性機械鎖（本檔刻意與既有
`test_check_gha_action_versions.py` 分開，只因 R57 的檔案邊界切分；兩檔守的是
不同命題，日後可由主控決定是否合併）：

  A. `check_gha_action_versions._audit_scan_surface()` 的鑑別力測試
     （R57R2-QA-02）。該函式是 R57 新增的 fail-loud 結構性守門，價值全在
     「未來冒出新的巢狀 `.github/workflows/` 時發紅」；現況 happy path 恆綠，
     判定邏輯被改壞不會有任何訊號——正是它自己 docstring 抨擊的 fail-open 形態。
     本節以 mock `subprocess.run`（回傳合成的 `git ls-files -z` 輸出）驅動，
     不動 git index、不依賴真實 repo 現況。

  B. `.github/workflows/windows-compat-ci.yml` 檔頭「shell 分佈實測快照」表
     與 YAML 實況的鏡子自證鎖（DEF-101-486 的未竟項；ARCH-03 原建議）。
     期望值**從檔頭註解表本身抽出**、實況從 YAML 重算，兩側任一漂移即紅燈，
     避免「註解快照靜默過期」再度發生（R57 同一輪內已因此產生三處失實宣稱）。

【B 節為何不用 pyyaml】根層 `tools/`＋`tools/tests/` 全數 stdlib-only，
`root-infra-ci.yml` 的 root-infra job 沒有 `setup-python`、也沒有任何
`pip install` 步驟（實查該檔可證），引入 pyyaml 會替根層閘門新增一個此前不存在
的外部相依。故 B 節自帶一個**縮限用途**的縮排掃描器 `parse_shell_distribution()`，
並以下列實測建立等價性證據：

  已實測涵蓋：本 repo 根層 11 支 workflow 中，7 支（aisdlc-sdd-arch-fitness /
  aisdlc-sdd-artifact-cleanup / aisdlc-sdd-drift-daily / aisdlc-sdd-fsm-chaos-nightly
  / macos-compat-ci / root-infra-ci / windows-compat-ci）以本掃描器與
  `yaml.safe_load` 逐 job 比對 `runs-on` 與 run-step shell 分佈，結果**全部相等**。
  已知不涵蓋（掃描器主動 raise、不做靜默猜測）：帶 `defaults:` 區塊的檔案
  （aisdlc-sdd-ci / autoclaude-ci / autoclaude-mutation-on-change /
  autoclaude-pg-e2e-on-label 共 4 支）——本鎖只服務 windows-compat-ci.yml，
  而該檔檔頭自述「全檔無 workflow 層／job 層 defaults:」，因此把 `defaults:`
  的出現直接當成「快照前提已被推翻」而 fail-loud。
  未窮舉：非本 repo 的任意 YAML 寫法（流式對映 `{...}`、錨點/別名、`- run: |`
  以外的區塊純量寫法、tab 縮排等）一律不保證——掃描器對認不得的形狀是
  raise 而非猜測，故失效方向是紅燈不是綠燈。

執行：python3 -m unittest tools.tests.test_gha_action_versions -v
（亦由 tools/run_root_unittests.py discover 納入）
"""
from __future__ import annotations

import ast
import collections
import io
import re
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_gha_action_versions as m  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WINDOWS_CI = _REPO_ROOT / ".github" / "workflows" / "windows-compat-ci.yml"
_PS51_TEST = _REPO_ROOT / "tools" / "tests" / "test_ps51_compat.py"

# 檔頭那句交叉引用所指向的「符號錨點」（刻意不寫行號——本 repo 反覆的教訓是
# 行號必漂移；R57 round 2 的 SD 正是抓到檔頭寫死的 `L12` 已失實）。
_PS51_CORRECTION_ANCHOR = "R57 QA-R57-04 訂正"


def _git_ls_files_stdout(paths: list[str]) -> str:
    """合成 `git ls-files -z` 的輸出（NUL 分隔、結尾帶一個 NUL）。"""
    return "".join(f"{p}\0" for p in paths)


def _fake_run(paths: list[str]):
    return mock.Mock(return_value=mock.Mock(stdout=_git_ls_files_stdout(paths)))


class TestAuditScanSurface(unittest.TestCase):
    """A 節：掃描面邊界稽核的鑑別力（R57R2-QA-02）。"""

    def _audit(self, paths: list[str]) -> list[str]:
        with mock.patch.object(m.subprocess, "run", _fake_run(paths)):
            return m._audit_scan_surface()

    def test_unregistered_nested_workflow_is_flagged(self):
        """未登記的巢狀 workflow（例如 AutoClaude 側日後自建一份）必須被列出——
        這是本函式存在的唯一理由：不讓新冒出的巢狀 .github/ 退回「沒人想過」。"""
        self.assertEqual(
            self._audit([".github/workflows/a.yml", "AutoClaude/.github/workflows/x.yml"]),
            ["AutoClaude/.github/workflows/x.yml"],
        )

    def test_registered_frozen_exclusion_is_not_flagged(self):
        """已明文裁定排除的 AISDLC_SDD 凍結版快照不得被列出，否則本工具會因
        「凍結版不可改」政策而永久紅燈（見主檔〈掃描面邊界〉②）。"""
        self.assertEqual(
            self._audit(
                [
                    "AISDLC_SDD/AISDLC_SDD_v0.01/.github/workflows/hub-push.yml",
                    "AISDLC_SDD/AISDLC_SDD_v0.29/.github/workflows/hub-push.yml",
                    "AISDLC_SDD/AISDLC_SDD_v0.30/.github/workflows/hub-push.yaml",
                ]
            ),
            [],
        )

    def test_future_major_version_forces_re_adjudication(self):
        """排除樣式刻意只收 `v0.NN`：框架若升到 v1.00，新版目錄必須重新被裁定
        納管與否，不得靠舊樣式順帶豁免。"""
        self.assertEqual(
            self._audit(["AISDLC_SDD/AISDLC_SDD_v1.00/.github/workflows/hub-push.yml"]),
            ["AISDLC_SDD/AISDLC_SDD_v1.00/.github/workflows/hub-push.yml"],
        )

    def test_root_workflows_are_not_flagged(self):
        """根層 `.github/workflows/*.yml`／`*.yaml` 本來就在掃描面內，不是「面外」。"""
        self.assertEqual(
            self._audit([".github/workflows/a.yml", ".github/workflows/b.yaml"]),
            [],
        )

    def test_nested_yaml_extension_is_also_flagged(self):
        """`.yaml` 與 `.yml` 對 GitHub Actions 等效，偵測面不得只涵蓋 `.yml`。"""
        self.assertEqual(
            self._audit(["sub/.github/workflows/x.yaml"]),
            ["sub/.github/workflows/x.yaml"],
        )

    def test_non_workflow_paths_are_ignored(self):
        """`.github/` 底下的非 workflow 檔（如 ISSUE_TEMPLATE）不得被誤報。"""
        self.assertEqual(
            self._audit(
                [
                    "AutoClaude/.github/ISSUE_TEMPLATE/bug.md",
                    "docs/.github/workflows/nested/deep.yml",
                ]
            ),
            [],
        )

    def test_git_unavailable_is_fail_loud_not_silent_skip(self):
        """git 不可用時必須 raise（而非回空清單靜默放行）——這道守門若能被
        環境問題靜默關掉，等同不存在。"""
        with mock.patch.object(m.subprocess, "run", side_effect=OSError("no git")):
            with self.assertRaises(RuntimeError):
                m._audit_scan_surface()

    def test_main_returns_1_when_unregistered_file_exists(self):
        """端到端：未登記檔存在時 `main()` 必須回 1（而非只是印訊息）。"""
        with mock.patch.object(
            m.subprocess, "run", _fake_run(["AutoClaude/.github/workflows/x.yml"])
        ):
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                rc = m.main()
        self.assertEqual(rc, 1)
        self.assertIn("AutoClaude/.github/workflows/x.yml", err.getvalue())

    def test_main_returns_1_when_git_unavailable(self):
        with mock.patch.object(m.subprocess, "run", side_effect=OSError("no git")):
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                rc = m.main()
        self.assertEqual(rc, 1)
        self.assertIn("git ls-files", err.getvalue())

    def test_main_against_real_repo_is_green(self):
        """現況（真 git index、真 workflows）必須綠——確認上列紅燈案例是鑑別力
        而非常態紅。"""
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            rc = m.main()
        self.assertEqual(rc, 0)


# ─── B 節：windows-compat-ci.yml 檔頭 shell 分佈鏡子自證鎖 ──────────────────

_HEADER_ROW_RE = re.compile(r"^#\s{2,}([a-z0-9-]+)\s+(\S+)\s+(\{.*\})\s*$")


def parse_header_snapshot(text: str) -> dict[str, tuple[str, dict[str, int]]]:
    """從檔頭註解抽出「job 名 / runs-on / shell 分佈」快照表。"""
    rows: dict[str, tuple[str, dict[str, int]]] = {}
    for line in text.splitlines():
        if not line.startswith("#"):
            break  # 只掃前導註解區塊，避免誤吃 YAML 本體內的註解
        mt = _HEADER_ROW_RE.match(line)
        if mt:
            rows[mt.group(1)] = (mt.group(2), ast.literal_eval(mt.group(3)))
    return rows


def parse_shell_distribution(text: str) -> dict[str, tuple[str, dict[str, int]]]:
    """縮限用途的縮排掃描器：回傳 {job: (runs-on, {shell: 步驟數})}，只計有
    `run:` 的步驟（`uses:` 步驟不吃 shell）。認不得的形狀一律 raise
    AssertionError——失效方向必須是紅燈，不是靜默少算。等價性實測範圍見模組
    docstring。"""
    jobs: dict[str, dict] = {}
    job: str | None = None
    step: dict | None = None
    in_jobs = False
    in_steps = False

    def flush() -> None:
        nonlocal step
        if job is not None and step is not None and step["run"]:
            jobs[job]["shells"][step["shell"] or "<implicit>"] += 1
        step = None

    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        if re.match(r"^\s*defaults:\s*$", line):
            raise AssertionError(
                "windows-compat-ci.yml 出現 `defaults:` 區塊——檔頭快照的前提"
                "（全檔無 workflow 層／job 層 defaults）已被推翻，請重審檔頭表"
            )
        if not line.startswith(" "):  # 頂層鍵
            flush()
            in_jobs = line.rstrip() == "jobs:"
            in_steps = False
            job = None
            continue
        if not in_jobs:
            continue
        mt = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if mt:
            flush()
            job = mt.group(1)
            in_steps = False
            jobs[job] = {"runs-on": None, "shells": collections.Counter()}
            continue
        if job is None:
            raise AssertionError(f"jobs: 區塊內出現非 job 起始的縮排行：{line!r}")
        mt = re.match(r"^    runs-on:\s*(\S+)\s*$", line)
        if mt:
            jobs[job]["runs-on"] = mt.group(1)
            continue
        if re.match(r"^    steps:\s*$", line):
            flush()
            in_steps = True
            continue
        if re.match(r"^    [A-Za-z0-9_-]+:", line):
            flush()
            in_steps = False
            continue
        if not in_steps:
            continue
        mt = re.match(r"^      - ([A-Za-z0-9_-]+):(.*)$", line)
        if mt:
            flush()
            step = {"run": False, "shell": None}
        else:
            mt = re.match(r"^        ([A-Za-z0-9_-]+):(.*)$", line)
            if not mt or step is None:
                continue
        key, value = mt.group(1), mt.group(2)
        if key == "run":
            step["run"] = True
        elif key == "shell":
            step["shell"] = value.strip()
    flush()

    missing = [n for n, d in jobs.items() if d["runs-on"] is None]
    if missing:
        raise AssertionError(f"下列 job 沒有掃到 `runs-on:`（掃描器可能失效）：{missing}")
    return {n: (d["runs-on"], dict(d["shells"])) for n, d in jobs.items()}


class TestWindowsCiHeaderSnapshotLock(unittest.TestCase):
    """B 節：DEF-101-486 未竟的機械鎖。檔頭那張手工快照在 R57 同一輪內已造成
    三處失實宣稱，代價已兌現，故以鏡子自證固定住。"""

    @classmethod
    def setUpClass(cls):
        cls.text = _WINDOWS_CI.read_text(encoding="utf-8")

    def test_header_snapshot_matches_yaml_reality(self):
        snapshot = parse_header_snapshot(self.text)
        reality = parse_shell_distribution(self.text)
        self.assertEqual(
            snapshot,
            reality,
            "windows-compat-ci.yml 檔頭的 shell 分佈快照與 YAML 實況不符——"
            "改動步驟後請同步更新檔頭那張表（檔頭附有可重跑的 pyyaml 指令）",
        )

    def test_snapshot_table_is_actually_present(self):
        """反向守門：若檔頭那張表被刪掉／格式被改到抽不出來，上一個測試會因
        兩側同時為空而假綠。"""
        snapshot = parse_header_snapshot(self.text)
        self.assertEqual(
            len(snapshot), 3, f"檔頭快照表應有 3 個 job，實抽到 {sorted(snapshot)}"
        )

    def test_header_cross_reference_anchor_still_exists(self):
        """SD-R57R2-01：檔頭那句「同款過期宣稱已於 R57 一併訂正」指向
        test_ps51_compat.py 的訂正註記。改用符號錨定（不寫行號），並由本測試
        確保錨點與引用兩側同時存在——任一側被刪即紅燈。"""
        self.assertIn(_PS51_CORRECTION_ANCHOR, _PS51_TEST.read_text(encoding="utf-8"))
        self.assertIn(_PS51_CORRECTION_ANCHOR, self.text)

    def test_header_points_at_this_lock(self):
        """檔頭必須指名本鎖（而非停留在 R57 round 2 的「目前沒有機械鎖」誠實
        揭露）；本鎖若被改名／刪除，檔頭的指引也會被這條測試逼著同步。"""
        self.assertIn("tools/tests/test_gha_action_versions.py", self.text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
