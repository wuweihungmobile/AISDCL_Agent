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

  C. 全 `.github/workflows/*.yml`：凡 `shell: powershell` 的步驟，其 `run:`
     本體必須全 ASCII（R76-02）。詳見 `TestPowershellRunBodyIsAscii` 的
     docstring——含它**守不到**哪一面的誠實劃界。

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

【C 節為何**可以**用 pyyaml（與 B 節不同調，這是有據的差別不是矛盾）】上段
「根層全數 stdlib-only」寫於 R57；R68 之後該前提已由 repo 自己推翻並改成受管
相依——`tools/run_root_unittests.py` 的 `_THIRD_PARTY_PREREQS` 明列
`("yaml", "pyyaml")`，且由三道機械物看守：runner 開場 fail-fast、下限失敗訊息
歸因、以及 `test_run_root_unittests.py::CiPrereqInstallLockTest`（凡在 CI 跑本
runner 的 job 都必須先裝清單裡每一個 pip 名）。實查三個消費者皆已安裝：
`root-infra-ci.yml:396`、`windows-compat-ci.yml`／`macos-compat-ci.yml` 的
「tools/tests 第三方相依」步驟；本機 pre-push 走 `.venv`（AutoClaude runtime
本就相依 pyyaml）。C 節要判的是「run 本體」這個**值**，縮排掃描器對區塊純量的
續行、`|`／`>`／`|-` 變體、行內註解各有一套規則，自寫近似只會多一個新的失明
面——B 節當時付不起的相依成本，今天已經是既成事實，故不重複造輪。
B 節維持原樣（不改動既有綠鎖）。

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

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_gha_action_versions as m  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOW_DIR = _REPO_ROOT / ".github" / "workflows"
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


# ─── C 節：`shell: powershell` 步驟的 run 本體必須全 ASCII（R76-02）─────────────

# 🔴 判準**刻意只鎖 `powershell`、不鎖 `pwsh`**（這是有據的射程選擇，不是漏網）：
#   · `shell: powershell` → runner 叫的是 Windows 內建 `powershell.exe`＝
#     Windows PowerShell 5.1。它讀腳本檔時，**無 BOM 就退回作業系統的 ANSI
#     codepage**（zh-TW 機器＝CP950、多數 GitHub runner＝CP1252）。而 runner 是
#     把 `run:` 本體寫成一支**暫存 .ps1** 再交給它——那支檔的編碼由 runner 決定，
#     本 repo 無從控制。⇒ 非 ASCII 字元落在字串字面值裡，就會被解成別的字元，
#     引號可能整個對不起來，**整支腳本 ParserError、一行都不執行**。
#   · `shell: pwsh` → PowerShell 7（Core），**預設就以 UTF-8 讀無 BOM 檔**，
#     同一段中文完全正常。把 pwsh 也鎖進來只會逼二十餘個既有步驟改寫英文訊息，
#     買不到任何實害防護——那是拿可讀性換零收益。
# 判準若哪天要擴到 pwsh，先拿出「pwsh 也會誤讀」的實測，不要靠對稱性直覺。
#
# 這一格治的實害（不是假想）：`windows-compat-ci.yml::windows-nightly-full` 的
# 兩步 5.1 驗證自 R48 起「跑了四輪」，雲端 run 30803941764 逐字留下
# `Unexpected token` ＋ `CategoryInfo : ParserError`——驗證邏輯**從未執行過一次**。
_MIN_POWERSHELL_STEPS = 3

# 下限的**上緣**（同 `run_root_unittests.RATCHET_STALE_RATIO` 體例）：純下限會腐化
# ——掃描面長到 30 步時，下限 3 讓 27 步靜默蒸發仍綠。超過此倍數即要求重釘下限。
_POWERSHELL_STEPS_STALE_RATIO = 3


def nonascii_powershell_steps(text: str, source: str) -> list[str]:
    """回傳 `(source::job::step)` 清單：`shell` 解析為 `powershell` 且 run 本體
    含非 ASCII 字元的步驟。shell 解析順序＝step > job defaults > workflow defaults
    （與 GitHub 的覆寫順序一致）。"""
    data = yaml.safe_load(text) or {}
    wf_shell = (((data.get("defaults") or {}).get("run") or {}).get("shell"))
    flagged: list[str] = []
    for job_name, job in (data.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        job_shell = ((job.get("defaults") or {}).get("run") or {}).get("shell", wf_shell)
        for idx, step in enumerate(job.get("steps") or []):
            if not isinstance(step, dict):
                continue
            body = step.get("run")
            if body is None or step.get("shell", job_shell) != "powershell":
                continue
            if not body.isascii():
                offenders = sorted({c for c in body if not c.isascii()})
                flagged.append(
                    f"{source}::{job_name}::step[{idx}] {step.get('name')!r} "
                    f"non-ASCII={''.join(offenders)[:40]!r}"
                )
    return flagged


def _all_powershell_steps() -> list[str]:
    """全 workflow 的 `shell: powershell` run 步驟識別字（不論是否 ASCII）。"""
    found: list[str] = []
    for path in sorted(_WORKFLOW_DIR.glob("*.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        wf_shell = (((data.get("defaults") or {}).get("run") or {}).get("shell"))
        for job_name, job in (data.get("jobs") or {}).items():
            if not isinstance(job, dict):
                continue
            job_shell = ((job.get("defaults") or {}).get("run") or {}).get("shell", wf_shell)
            for idx, step in enumerate(job.get("steps") or []):
                if isinstance(step, dict) and step.get("run") is not None:
                    if step.get("shell", job_shell) == "powershell":
                        found.append(f"{path.name}::{job_name}::step[{idx}]")
    return found


class TestPowershellRunBodyIsAscii(unittest.TestCase):
    """C 節（R76-02）：`shell: powershell` 步驟的 `run:` 本體必須全 ASCII。

    🔴 **這道鎖守不到什麼（誠實劃界，不是免責聲明）**：
    `AutoClaude/tools/hooks/check_ps1_encoding.py` 是本 repo 治「無 BOM 的 .ps1
    被 5.1 以 ANSI codepage 誤讀」的既有機械物，但它以**副檔名**過濾
    （`PS_SUFFIXES = {".ps1", ".psm1", ".psd1"}`，非該三者一律 no-op）⇒ runner
    由 `run:` 本體**現生**的那支暫存 .ps1，副檔名雖是 .ps1 卻**不在磁碟上、也不
    經過任何 hook**，結構上不在任何既有鎖的視野內。本鎖補的正是這一格，但補法是
    「讓那支暫存檔的內容不含非 ASCII」——**不是**去控制它的編碼（我們控制不了）。
    因此：runner 若哪天改用 UTF-16 或加了 BOM，本鎖對此**零訊號**；同理，本鎖也
    管不到 `.ps1` 檔案本體的 BOM 政策（那是 `test_ps1_bom.py` 的職責）。
    另一段未涵蓋：`shell: powershell -Command …` 這類自訂 shell 字串（本 repo 現
    無此寫法），字串不等於 `powershell` 就不進射程。
    """

    def test_every_powershell_run_body_is_ascii(self) -> None:
        flagged: list[str] = []
        for path in sorted(_WORKFLOW_DIR.glob("*.yml")):
            flagged += nonascii_powershell_steps(
                path.read_text(encoding="utf-8"), path.name
            )
        self.assertEqual(
            flagged,
            [],
            "下列 `shell: powershell`（＝Windows PowerShell 5.1）步驟的 run 本體含非 "
            "ASCII 字元。runner 把 run 本體寫成無 BOM 暫存 .ps1，5.1 以 ANSI codepage "
            "誤讀 ⇒ 字串字面值 ParserError、整支腳本一行都不執行（R76-02：實害已在雲端 "
            "run 30803941764 兌現，兩步自 R48 起四輪從未真的執行過）。\n"
            "  處置：把 run 本體改成全 ASCII（訊息寫英文），中文 WHY 移到 step 上方的 "
            "YAML 註解——註解不會被執行，不受編碼影響。逐字範例見 "
            "windows-compat-ci.yml::windows-smoke 的 PS 5.1 核心驗證 step。\n"
            f"  命中：{flagged}",
        )

    def test_scan_surface_is_not_empty(self) -> None:
        """反向守門：解析式漂移導致 0 命中時，上一條會兩側同空而假綠——本 repo 已有
        「掃描面歸零靜默通過」的判例，故掃描面本身要有下限。"""
        steps = _all_powershell_steps()
        self.assertGreaterEqual(
            len(steps),
            _MIN_POWERSHELL_STEPS,
            f"全 workflow 只掃到 {len(steps)} 個 `shell: powershell` run 步驟 < 下限 "
            f"{_MIN_POWERSHELL_STEPS}——若真的刻意移除了 PS 5.1 覆蓋，請同步下修本下限"
            f"並在 commit 訊息寫明；否則就是解析式壞了。實抽：{steps}",
        )

    def test_scan_surface_floor_is_not_stale(self) -> None:
        """下限的上緣：純下限會腐化（掃描面長大後，蒸發一半仍在下限之上）。"""
        steps = _all_powershell_steps()
        ceiling = _MIN_POWERSHELL_STEPS * _POWERSHELL_STEPS_STALE_RATIO
        self.assertLessEqual(
            len(steps),
            ceiling,
            f"`shell: powershell` 步驟已達 {len(steps)} 個，超過下限 "
            f"{_MIN_POWERSHELL_STEPS} 的 {_POWERSHELL_STEPS_STALE_RATIO} 倍——請重釘 "
            "`_MIN_POWERSHELL_STEPS`，否則下限已失去鑑別力（同 run_root_unittests.py "
            "的 RATCHET_STALE_RATIO 體例）",
        )

    def test_criterion_flags_a_nonascii_powershell_body(self) -> None:
        """鑑別力（Rule 9：測意圖）——判準必須真的抓得到中文 run 本體。"""
        synthetic = (
            "jobs:\n"
            "  demo:\n"
            "    steps:\n"
            "      - name: x\n"
            "        shell: powershell\n"
            '        run: throw "找不到"\n'
        )
        self.assertEqual(len(nonascii_powershell_steps(synthetic, "syn.yml")), 1)

    def test_criterion_deliberately_ignores_pwsh(self) -> None:
        """射程宣告的機械化：同一段中文換成 `shell: pwsh` 必須**不**被判紅。
        pwsh 7 預設以 UTF-8 讀無 BOM 檔，本 repo 二十餘個 pwsh 步驟的中文訊息
        是安全的；把它們也鎖進來是拿可讀性換零收益。"""
        synthetic = (
            "jobs:\n"
            "  demo:\n"
            "    steps:\n"
            "      - name: x\n"
            "        shell: pwsh\n"
            '        run: throw "找不到"\n'
        )
        self.assertEqual(nonascii_powershell_steps(synthetic, "syn.yml"), [])

    def test_job_level_defaults_shell_is_honoured(self) -> None:
        """step 未宣告 `shell:` 時繼承 job defaults——不解析這一層就會漏掉整個 job。"""
        synthetic = (
            "jobs:\n"
            "  demo:\n"
            "    defaults:\n"
            "      run:\n"
            "        shell: powershell\n"
            "    steps:\n"
            "      - name: x\n"
            '        run: throw "找不到"\n'
        )
        self.assertEqual(len(nonascii_powershell_steps(synthetic, "syn.yml")), 1)


# ─── D 節：`runs-on:` runner 標籤白名單（本輪 R77-02）─────────────────────────
#
# 🔴 為何需要（與 C 節同一族，但守的是另一個欄位）：`uses:` 的版本漂移已有
# `check_gha_action_versions.py` 在守，而 **`runs-on:` 這個決定「這段 CI 在哪個作業
# 系統上跑」的欄位，全 repo 零機械物**。它的失效方式安靜且昂貴：
#   · 打錯字（`ubunut-latest`）⇒ GitHub 永遠找不到 runner，job 一直 queued 直到逾時，
#     而 workflow 檔本身完全合法、任何 YAML lint 都不會響；
#   · 悄悄改成已退役的映像標籤（`ubuntu-20.04`／`macos-11`）⇒ GitHub 直接讓該 job
#     failed，而本 repo 的雲端結論錨只記 run 層 conclusion，分不出「測試紅」與
#     「runner 標籤不存在」；
#   · 把某支跨平台驗證改成 `ubuntu-latest`（省時間）⇒ 該平台的覆蓋**靜默歸零**，
#     而 GitHub UI 上「跑過且通過」與「在錯的平台上跑過且通過」長得一模一樣。
# 本鎖刻意做成**白名單**而非黑名單：黑名單只擋得住已知的壞值，白名單擋得住打錯字
# （同 `TestNightlyAlertConclusionWhitelist` 對結論判讀所做的極性選擇）。
#
# 白名單內容＝GitHub 目前提供、且本 repo 真的用得到的標籤。要新增一個標籤請直接改
# 這個集合（那是一個看得見代價的動作），**不要**改成正則模糊比對。
_ALLOWED_RUNNER_LABELS = frozenset({
    "ubuntu-latest",
    "ubuntu-24.04",
    "ubuntu-22.04",
    "windows-latest",
    "macos-latest",
})
_RUNS_ON_RE = re.compile(r"^\s*runs-on:\s*(\S+)\s*$")
#: `${{ … }}` 運算式（matrix runner）——本鎖判不出它的真值，故不套白名單，改為
#: 要求「出現即需人裁定」。現況零筆；真要引入 matrix runner 時請擴充本鎖而不是
#: 加一條豁免（豁免清單本身即 fail-open 面，同 TestCompatCiScriptTriggerSymmetry）。
_RUNNER_EXPR_RE = re.compile(r"\$\{\{")
#: 掃描面下限（現況 25 筆宣告）＋上緣倍數（純下限會腐化，同 C 節體例）。
_MIN_RUNS_ON_DECLS = 20
_RUNS_ON_STALE_RATIO = 3


def runner_labels(text: str, source: str) -> list[tuple[str, str]]:
    """回傳 `(source:lineno, runs-on 值)`；共用 C 節同一套 YAML 註解剝除規則。"""
    out: list[tuple[str, str]] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        mt = _RUNS_ON_RE.match(m._strip_yaml_comment(raw))
        if mt:
            out.append((f"{source}:{lineno}", mt.group(1).strip("\"'")))
    return out


def _all_runner_labels() -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for path in sorted(set(_WORKFLOW_DIR.glob("*.yml")) | set(_WORKFLOW_DIR.glob("*.yaml"))):
        found += runner_labels(path.read_text(encoding="utf-8"), path.name)
    return found


class TestRunnerLabelWhitelist(unittest.TestCase):
    """D 節（R77-02）：`runs-on:` 只准出現白名單內的 runner 標籤。"""

    def test_every_runs_on_label_is_whitelisted(self) -> None:
        offenders = [
            f"{site} → {label!r}"
            for site, label in _all_runner_labels()
            if not _RUNNER_EXPR_RE.search(label) and label not in _ALLOWED_RUNNER_LABELS
        ]
        self.assertEqual(
            offenders, [],
            "下列 `runs-on:` 不在白名單內。打錯字的標籤不會讓 YAML 失效，只會讓 job "
            "永遠 queued 到逾時；退役標籤則讓 job 直接 failed，而本 repo 的雲端結論錨"
            "只記 run 層 conclusion，分不出這兩者與「測試真的紅了」。\n"
            f"  白名單：{sorted(_ALLOWED_RUNNER_LABELS)}\n"
            f"  命中：{offenders}\n"
            "  處置：確認那是 GitHub 現行提供的標籤後，把它加進 "
            "`_ALLOWED_RUNNER_LABELS`（那是一個看得見代價的動作）",
        )

    def test_no_unresolvable_matrix_runner_sneaks_in(self) -> None:
        """`${{ … }}` 形態本鎖判不出真值 ⇒ 出現即要求人裁定，不得靜默放行。"""
        exprs = [f"{s} → {v!r}" for s, v in _all_runner_labels() if _RUNNER_EXPR_RE.search(v)]
        self.assertEqual(
            exprs, [],
            "偵測到運算式形態的 `runs-on:`（matrix runner）。本鎖對它零判準——放行"
            "等於在白名單上開一個任意大的洞。處置：擴充本鎖去解析該 matrix 的取值面，"
            f"或改回字面標籤；不要加豁免。命中：{exprs}",
        )

    def test_scan_surface_is_not_empty(self) -> None:
        """反向守門：解析式漂移導致 0 命中時，上兩條會兩側同空而假綠。"""
        labels = _all_runner_labels()
        self.assertGreaterEqual(
            len(labels), _MIN_RUNS_ON_DECLS,
            f"全 workflow 只掃到 {len(labels)} 個 `runs-on:` 宣告 < 下限 "
            f"{_MIN_RUNS_ON_DECLS}——若真的刪了 job 請同步下修本下限；否則就是"
            f"解析式壞了。實抽：{labels}",
        )

    def test_scan_surface_floor_is_not_stale(self) -> None:
        """下限的上緣：掃描面長大後，蒸發一半仍在下限之上（同 C 節 stale ratio）。"""
        labels = _all_runner_labels()
        ceiling = _MIN_RUNS_ON_DECLS * _RUNS_ON_STALE_RATIO
        self.assertLessEqual(
            len(labels), ceiling,
            f"`runs-on:` 宣告已達 {len(labels)} 個，超過下限 {_MIN_RUNS_ON_DECLS} 的 "
            f"{_RUNS_ON_STALE_RATIO} 倍——請重釘 `_MIN_RUNS_ON_DECLS`，否則下限已"
            f"失去鑑別力",
        )

    def test_criterion_flags_a_typo_and_a_retired_label(self) -> None:
        """鑑別力（Rule 9）：判準必須真的抓得到打錯字與已退役的映像標籤。"""
        synthetic = (
            "jobs:\n"
            "  a:\n"
            "    runs-on: ubunut-latest\n"
            "  b:\n"
            "    runs-on: ubuntu-20.04\n"
            "  c:\n"
            "    runs-on: ubuntu-latest\n"
        )
        bad = [
            v for _s, v in runner_labels(synthetic, "syn.yml")
            if v not in _ALLOWED_RUNNER_LABELS
        ]
        self.assertEqual(bad, ["ubunut-latest", "ubuntu-20.04"])

    def test_commented_out_runs_on_is_not_counted(self) -> None:
        """被註解掉的舊 `runs-on:` 不得被當成現行宣告（同 C 節註解剝除紀律）。"""
        synthetic = "jobs:\n  a:\n    # runs-on: ubuntu-20.04\n    runs-on: ubuntu-latest\n"
        self.assertEqual(
            [v for _s, v in runner_labels(synthetic, "syn.yml")], ["ubuntu-latest"]
        )


# ─── E 節：`check_gha_action_versions.main()` 不得早退遮蔽（本輪 R77-17）────────
#
# 🔴 缺陷本體與端到端實測見主檔 `_CHECK_ORDER` 上方那段註解。這裡只放鎖。
# 為何鎖在**行為**而不只是「有沒有 `_CHECK_ORDER` 這個常數」：常數在場不等於它被用到
# （同 DEF-101-743「宣告的字串在場 ≠ 那件事會發生」）。下面兩支各自模擬一種前置失敗，
# 直接斷言「後面那幾道的輸出仍然出現」與「跑不了的那幾道被逐名列出」。
class TestNoEarlyExitMaskingInGhaChecker(unittest.TestCase):
    """E 節（R77-17）：四道檢查必須跑得完的全部跑完，跑不了的必須逐名自白。"""

    @staticmethod
    def _run() -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = m.main()
        return rc, out.getvalue(), err.getvalue()

    def test_check_order_is_declared_and_non_trivial(self) -> None:
        self.assertGreaterEqual(
            len(m._CHECK_ORDER), 4,
            "_CHECK_ORDER 少於 4 道——殘餘清單會把不存在的檢查算進去或漏掉真檢查",
        )

    def test_every_return_in_main_goes_through_the_reporter(self) -> None:
        """靜態面：`main()` 內不得有繞過 `_report()` 的裸 `return`。

        繞過 reporter 就等於繞過「綠／紅／未執行三塊各自印完」那件事，而那正是
        這次事故的機制本身（原版 7 個裸 `return 1`）。
        """
        src = (_REPO_ROOT / "tools" / "check_gha_action_versions.py").read_text(
            encoding="utf-8"
        )
        fn = next(
            n for n in ast.walk(ast.parse(src))
            if isinstance(n, ast.FunctionDef) and n.name == "main"
        )
        bare = [
            node.lineno for node in ast.walk(fn)
            if isinstance(node, ast.Return)
            and not (
                isinstance(node.value, ast.Call)
                and getattr(node.value.func, "id", "") == "_report"
            )
        ]
        self.assertEqual(
            bare, [],
            f"main() 這幾行直接 `return` 而未經 `_report()`：{bare}——該早退點不會"
            f"印出「尚有 N 道未執行」，輸出變短會被誤讀成「問題變少」",
        )

    def test_a_failing_first_check_does_not_swallow_the_later_ones(self) -> None:
        """鑑別力（本鎖存在的唯一理由）：①紅時，③④ 的輸出必須仍然在。

        修復前實測：控制組 7 行 stdout 整批消失、換成 2 行 stderr，且沒有任何一句話
        說「後面 3 道一行都沒跑」。
        """
        with mock.patch.object(
            m, "_audit_scan_surface",
            return_value=["AutoClaude/.github/workflows/synthetic-probe.yml"],
        ):
            rc, out, err = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("synthetic-probe.yml", err)
        self.assertIn(m._CHECK_ORDER[3], out,
                      f"①紅時 ④ 的結論不見了（stdout={out!r}）——早退遮蔽回歸")
        self.assertIn("巢狀排除區實查", out,
                      "①紅時 ② 的結論不見了——早退遮蔽回歸")

    def test_a_check_that_could_not_run_is_named_not_silently_dropped(self) -> None:
        """②因前置條件不成立而跑不了時，必須逐名列出——未執行 ≠ 通過。"""
        with mock.patch.object(m.subprocess, "run", side_effect=OSError("no git")):
            rc, out, err = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("未執行", err)
        self.assertIn(m._CHECK_ORDER[1], err)
        self.assertIn(m._CHECK_ORDER[3], out,
                      "git 不可用時 ④ 仍應照跑（它不依賴 git）")

    def test_green_run_says_how_many_checks_actually_ran(self) -> None:
        """全綠時也必須說出「幾道」——只印 ✅ 而不說數量，掃描面塌掉時看不出來。"""
        rc, out, err = self._run()
        self.assertEqual(rc, 0, err)
        self.assertIn(f"（{len(m._CHECK_ORDER)} 道）", out)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
