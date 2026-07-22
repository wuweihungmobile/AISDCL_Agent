#!/usr/bin/env python3
"""SCAN-C-4／SCAN-C-5 裸修回歸鎖（R15 QA-R15-REV-4）。

WHY：`aisdlc-sdd-arch-fitness.yml` 的 workflow 層 `permissions: contents: read`
（SCAN-C-4：先前無宣告、`pr-advisory` job 繼承 repo 預設可能 write-all）與
`autoclaude-ci.yml` 的 `concurrency:`（SCAN-C-5：連續 push 疊跑洩額度）皆為
R15 裸修——本地測試/pre-push 對兩者零機械鎖，日後有人不慎刪掉這兩個區塊，
要等雲端 CI 才會被動發現（且帳務停擺中，見 DEF-101-081）。

比照 test_workflow_timeout_coverage.py／test_workflow_schedule_sync.py 既有
紀律：零第三方依賴（根層 unittest 環境不保證 pyyaml），以行級 regex 掃描，
不引入獨立 check_*.py 工具位（防線預算制搭載優先序：擴充/新增 unittest
掃描器 ＞ 新建獨立工具位，見 docs/04_planning/AutoSDD_Iteration_Prompt_Template.md）。
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ARCH_FITNESS = _REPO_ROOT / ".github" / "workflows" / "aisdlc-sdd-arch-fitness.yml"
_AUTOCLAUDE_CI = _REPO_ROOT / ".github" / "workflows" / "autoclaude-ci.yml"
_WINDOWS_COMPAT_CI = _REPO_ROOT / ".github" / "workflows" / "windows-compat-ci.yml"
_MACOS_COMPAT_CI = _REPO_ROOT / ".github" / "workflows" / "macos-compat-ci.yml"

# workflow 層 permissions（頂層、非 job 縮排下的 "permissions:" 起頭，後接
# 兩格縮排的 "contents: read"）——用行首錨定排除 job 層縮排版本誤中。
_TOP_LEVEL_PERMISSIONS_RE = re.compile(
    r"^permissions:\n(?:#.*\n)*  contents: read\s*$", re.MULTILINE
)
_JOB_LEVEL_WRITE_RE = re.compile(r"^\s{4,}permissions:\n\s{4,}contents: write", re.MULTILINE)

_CONCURRENCY_RE = re.compile(
    r"^concurrency:\n"
    r"  group: autoclaude-ci-\$\{\{ github\.ref \}\}-\$\{\{ github\.event_name \}\}"
    r"-\$\{\{ github\.event\.schedule \}\}\n"
    r"  cancel-in-progress: true\s*$",
    re.MULTILINE,
)

# R25 DEF-101-263③：windows-compat-ci.yml／macos-compat-ci.yml 各自 3 個 job 層
# concurrency 區塊（smoke／nightly-full／nightly-alert）先前無任何機械回歸鎖——
# 仿上方 _CONCURRENCY_RE 手法，逐 job 錨定 group/cancel-in-progress 字面值；
# nightly-alert 區塊在 concurrency: 與 group: 之間夾了說明性註解行（R13 CI-5／
# SCAN-C-11），用 `(?:\s*#.*\n)*` 容忍（比照 _TOP_LEVEL_PERMISSIONS_RE 既有作法）。
def _job_concurrency_re(group: str, cancel_in_progress: str, allow_comments: bool = False) -> re.Pattern[str]:
    comment_gap = r"(?:\s*#.*\n)*" if allow_comments else ""
    return re.compile(
        r"^    concurrency:\n"
        + comment_gap
        + rf"      group: {re.escape(group)}\n"
        rf"      cancel-in-progress: {cancel_in_progress}\s*$",
        re.MULTILINE,
    )


_WINDOWS_SMOKE_CONCURRENCY_RE = _job_concurrency_re(
    "windows-compat-ci-smoke-${{ github.ref }}", "true"
)
_WINDOWS_NIGHTLY_FULL_CONCURRENCY_RE = _job_concurrency_re(
    "windows-compat-ci-nightly-full", "false"
)
_WINDOWS_NIGHTLY_ALERT_CONCURRENCY_RE = _job_concurrency_re(
    "windows-compat-ci-nightly-alert", "false", allow_comments=True
)
_MACOS_SMOKE_CONCURRENCY_RE = _job_concurrency_re(
    "macos-compat-ci-smoke-${{ github.ref }}", "true"
)
_MACOS_NIGHTLY_FULL_CONCURRENCY_RE = _job_concurrency_re(
    "macos-compat-ci-nightly-full", "false"
)
_MACOS_NIGHTLY_ALERT_CONCURRENCY_RE = _job_concurrency_re(
    "macos-compat-ci-nightly-alert", "false", allow_comments=True
)


class TestArchFitnessWorkflowLevelPermissions(unittest.TestCase):
    """SCAN-C-4：workflow 層最小權限，nightly-strict job 層 write 覆寫仍在。"""

    def test_workflow_level_contents_read_present(self):
        text = _ARCH_FITNESS.read_text(encoding="utf-8")
        self.assertRegex(
            text, _TOP_LEVEL_PERMISSIONS_RE,
            "aisdlc-sdd-arch-fitness.yml 缺 workflow 層 permissions: contents: read"
            "（SCAN-C-4 回歸——pr-advisory job 將繼承 repo 預設，可能 write-all）",
        )

    def test_nightly_strict_job_level_write_override_still_present(self):
        text = _ARCH_FITNESS.read_text(encoding="utf-8")
        self.assertRegex(
            text, _JOB_LEVEL_WRITE_RE,
            "nightly-strict job 層 contents: write 覆寫缺失——回寫 TREND.yaml"
            "會被 workflow 層 read 權限擋下",
        )


class TestAutoclaudeCiConcurrencyLock(unittest.TestCase):
    """SCAN-C-5：push 閘 concurrency group 含 event_name/event.schedule 分組。"""

    def test_concurrency_group_and_cancel_present(self):
        text = _AUTOCLAUDE_CI.read_text(encoding="utf-8")
        self.assertRegex(
            text, _CONCURRENCY_RE,
            "autoclaude-ci.yml 缺 concurrency 區塊或 group 鍵值漂移（SCAN-C-5 回歸——"
            "連續 push 將疊跑洩額度；group 須含 event_name/event.schedule 使兩條"
            "nightly cron 各自成組、不互相取消）",
        )


class TestCompatCiConcurrencyLock(unittest.TestCase):
    """R25 DEF-101-263③：windows-compat-ci.yml／macos-compat-ci.yml 各 3 個 job
    層 concurrency 區塊（smoke／nightly-full／nightly-alert）先前完全未被任何
    機械測試鎖定——`_ARCH_FITNESS`/`_AUTOCLAUDE_CI` 僅覆蓋另兩份 workflow，本檔
    案名雖稱「concurrency lock」實際留有兩平台 compat CI 的治理縫隙（R25 Scan-C
    全面掃描坐實 R23 DEF-101-263 backlog）。"""

    def test_windows_smoke_concurrency_present(self):
        text = _WINDOWS_COMPAT_CI.read_text(encoding="utf-8")
        self.assertRegex(
            text, _WINDOWS_SMOKE_CONCURRENCY_RE,
            "windows-compat-ci.yml windows-smoke job 缺 concurrency 區塊或"
            "group/cancel-in-progress 字面值漂移（per-ref cancel，PR 疊跑省額度）",
        )

    def test_windows_nightly_full_concurrency_present(self):
        text = _WINDOWS_COMPAT_CI.read_text(encoding="utf-8")
        self.assertRegex(
            text, _WINDOWS_NIGHTLY_FULL_CONCURRENCY_RE,
            "windows-compat-ci.yml windows-nightly-full job 缺 concurrency 區塊或"
            "字面值漂移（固定 group，避免多次排程/手動觸發疊跑）",
        )

    def test_windows_nightly_alert_concurrency_present(self):
        text = _WINDOWS_COMPAT_CI.read_text(encoding="utf-8")
        self.assertRegex(
            text, _WINDOWS_NIGHTLY_ALERT_CONCURRENCY_RE,
            "windows-compat-ci.yml windows-nightly-alert job 缺獨立 concurrency"
            "group（SCAN-C-11——與 nightly-full 共用 group 會導致 pending 位互踩，"
            "告警路徑靜默蒸發）",
        )

    def test_macos_smoke_concurrency_present(self):
        text = _MACOS_COMPAT_CI.read_text(encoding="utf-8")
        self.assertRegex(
            text, _MACOS_SMOKE_CONCURRENCY_RE,
            "macos-compat-ci.yml macos-smoke job 缺 concurrency 區塊或"
            "group/cancel-in-progress 字面值漂移",
        )

    def test_macos_nightly_full_concurrency_present(self):
        text = _MACOS_COMPAT_CI.read_text(encoding="utf-8")
        self.assertRegex(
            text, _MACOS_NIGHTLY_FULL_CONCURRENCY_RE,
            "macos-compat-ci.yml macos-nightly-full job 缺 concurrency 區塊或"
            "字面值漂移",
        )

    def test_macos_nightly_alert_concurrency_present(self):
        text = _MACOS_COMPAT_CI.read_text(encoding="utf-8")
        self.assertRegex(
            text, _MACOS_NIGHTLY_ALERT_CONCURRENCY_RE,
            "macos-compat-ci.yml macos-nightly-alert job 缺獨立 concurrency"
            "group（R13 CI-5 同款設計，與 nightly-full 共用 group 會互踩）",
        )


if __name__ == "__main__":
    unittest.main()
