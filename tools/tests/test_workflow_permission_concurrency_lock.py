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

R68 擴充（Pkg-4「CI／nightly 死亡通道」；檔名雖仍稱 permission/concurrency，
實質已是「compat-CI／root-infra-ci 的 workflow YAML 機械鎖聚落」——依鎖檔數
棘輪紀律〔DEF-101-561③，tools/tests/ shrink-only〕不另開新檔，一律擴充既有檔）：
  1. `TestNightlyAlertConclusionWhitelist` — 兩支 `*-nightly-alert` 的結論判讀
     必須是 **success 白名單**（fail-closed）。修復前為黑名單（只有字面
     "failure" 算紅），cancelled／timed_out／skipped／conclusion 為 null／job
     顯示名被加前綴 五種情境全部 fail-open 成「綠燈」，進而**自動關閉**一張
     仍然有效的 P1 issue 並留言「已恢復綠燈」——告警器主動抹除紅燈證據。
  2. `TestNightlyJobNameSelectorInterlock` — alert 的 jq `startswith("…")`
     選擇子字串必須是 nightly-full `name:` 的前綴。兩者是兩份手寫字面值，
     本 repo 慣例會在 job 名後綴輪次註記，一改名選擇子就落空成 "unknown"。
     GitHub Actions 的 `jobs.<id>.name` 不支援 `env` context，無法用共用變數
     消滅漂移面，故只能用機械鎖互鎖。
  3. `TestRootInfraNightlyStalenessSentinel` — root-infra-ci.yml 第 15 道
     （nightly-full 排程陳舊度哨兵）必須存在、必須阻斷、必須同時查兩支
     workflow 的 `--event schedule --status success`。此道是 R68 對「兩支
     nightly-full 自 2026-07-14 起 18 天零成功而三道既有哨兵結構上都偵測不到」
     的直接修復（誠實劃界見該 workflow 檔頭第 15 道：本道與被偵測者同計費平面）。
  4. `TestCompatCiScriptTriggerSymmetry` — 兩支 compat-CI 的 `paths` 白名單
     對全部 tracked `*.sh`／`*.ps1` 的觸發面必須**完全對稱、零豁免**。
     windows 側逐一列舉 `.sh`、macos 側用 `**/*.sh` 兜底（反之亦然）的不對稱
     設計本身保留（改成兩側都通配會讓凍結版樹下的腳本也觸發，代價不成比例），
     但「列舉面漏一支」從此有機械訊號。
"""
from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ARCH_FITNESS = _REPO_ROOT / ".github" / "workflows" / "aisdlc-sdd-arch-fitness.yml"
_AUTOCLAUDE_CI = _REPO_ROOT / ".github" / "workflows" / "autoclaude-ci.yml"
_WINDOWS_COMPAT_CI = _REPO_ROOT / ".github" / "workflows" / "windows-compat-ci.yml"
_MACOS_COMPAT_CI = _REPO_ROOT / ".github" / "workflows" / "macos-compat-ci.yml"
_ROOT_INFRA_CI = _REPO_ROOT / ".github" / "workflows" / "root-infra-ci.yml"

# workflow 層 permissions（頂層、非 job 縮排下的 "permissions:" 起頭，後接
# 兩格縮排的 "contents: read"）——用行首錨定排除 job 層縮排版本誤中。
_TOP_LEVEL_PERMISSIONS_RE = re.compile(
    r"^permissions:\n(?:#.*\n)*  contents: read\s*$", re.MULTILINE
)
_JOB_LEVEL_WRITE_RE = re.compile(r"^\s{4,}permissions:\n\s{4,}contents: write", re.MULTILINE)
_NIGHTLY_STRICT_JOB_RE = re.compile(r"^  nightly-strict:\n(?:.*\n)*?(?=^  \S|\Z)", re.MULTILINE)

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
    """SCAN-C-4：workflow 層最小權限。

    R40 更新：`nightly-strict` job 原本需要 job 層 `contents: write` 覆寫來
    回寫 `TREND.yaml`；R40 起該檔已 git-ignore（凍結基線 v0.01 不應再被回寫，
    見 DEF-101-329/330），`nightly-strict` 改用 `actions/upload-artifact` 取代
    commit/push，不再需要寫入權限，job 層 write 覆寫已隨之移除——本測試改為
    鎖「job 層不應再出現 write 覆寫」（read-only 已足夠），防止未來又不慎重新
    加回不必要的寫入權限（最小權限原則）。
    """

    def test_workflow_level_contents_read_present(self):
        text = _ARCH_FITNESS.read_text(encoding="utf-8")
        self.assertRegex(
            text, _TOP_LEVEL_PERMISSIONS_RE,
            "aisdlc-sdd-arch-fitness.yml 缺 workflow 層 permissions: contents: read"
            "（SCAN-C-4 回歸——pr-advisory job 將繼承 repo 預設，可能 write-all）",
        )

    def test_nightly_strict_job_no_longer_needs_write_override(self):
        text = _ARCH_FITNESS.read_text(encoding="utf-8")
        m = _NIGHTLY_STRICT_JOB_RE.search(text)
        self.assertIsNotNone(m, "找不到 nightly-strict job 區塊——workflow 結構是否變動？")
        job_text = m.group(0)
        self.assertNotRegex(
            job_text, _JOB_LEVEL_WRITE_RE,
            "nightly-strict job 層出現多餘的 contents: write 覆寫——R40 起本 job 已"
            "改用 upload-artifact 取代 commit/push（DEF-101-330），不應再宣告寫入權限"
            "（最小權限原則；若未來重新引入 push 行為，須連同本測試一併重新評估）",
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


# ---------------------------------------------------------------------------
# R68 Pkg-4：nightly 告警／陳舊度／paths 對稱性
# ---------------------------------------------------------------------------

# 兩平台的 (workflow 檔, nightly-full job id, alert job id, jq 選擇子前綴)。
_NIGHTLY_PLATFORMS = (
    ("windows-compat-ci.yml", _WINDOWS_COMPAT_CI, "windows-nightly-full",
     "windows-nightly-alert", "Windows nightly full"),
    ("macos-compat-ci.yml", _MACOS_COMPAT_CI, "macos-nightly-full",
     "macos-nightly-alert", "macOS nightly full"),
)

# 白名單判讀式（fail-closed）。修復前為黑名單 `= "failure"`，見檔頭 R68 擴充 1.。
_SUCCESS_WHITELIST_RE = re.compile(r'if \[ "\$conclusion" = "success" \]; then')
_FAILURE_BLACKLIST_RE = re.compile(r'\[ "\$conclusion" = "failure" \]')
# gh api 自身失敗時的降級（沒有它，step 會被 `set -e` 打死 ⇒ outputs 為空 ⇒
# 下游兩個分支的 == 'true'/'false' 皆不成立 ⇒ 告警靜默蒸發）。
_API_ERROR_FALLBACK_RE = re.compile(r'\|\| echo "api-error"')
_JQ_STARTSWITH_RE = re.compile(r'select\(\.name \| startswith\("([^"]+)"\)\)')
_CLOSE_GUARD_RE = re.compile(r"^        if: steps\.check\.outputs\.failed == 'false'\s*$",
                             re.MULTILINE)


def _job_block(text: str, job_id: str) -> str:
    """抽出 `  <job_id>:` 起、至下一個同層 job（兩格縮排的鍵）或檔尾為止的區塊。

    抽不到即 fail-loud（不得靜默降級成整檔比對——那會讓區塊內的漂移被檔案
    別處的巧合字串滿足；同 tools/tests/test_smoke_ci_sync.py::_region 慣例）。
    """
    m = re.search(rf"^  {re.escape(job_id)}:\n(?:.*\n)*?(?=^  [A-Za-z0-9_-]+:\n|\Z)",
                  text, re.MULTILINE)
    if m is None:
        raise AssertionError(f"抽不到 job 區塊 `{job_id}`——workflow 結構已變動")
    return m.group(0)


def _job_display_name(job_text: str) -> str:
    m = re.search(r"^    name: (.+?)\s*$", job_text, re.MULTILINE)
    if m is None:
        raise AssertionError("job 區塊內找不到 `name:`——結構已變動")
    return m.group(1)


class TestNightlyAlertConclusionWhitelist(unittest.TestCase):
    """R68（P2，兩平台同款）：`*-nightly-alert` 的結論判讀必須 fail-closed。

    Rule 9（測意圖）：這裡守的不是「有沒有一行 if」，而是**判讀的極性**——
    黑名單極性下，任何非 "failure" 的結論（含 cancelled／timed_out／
    conclusion 為 null／job 改名導致 startswith 落空的 "unknown"／gh api 掛掉）
    都會被當成綠燈，觸發 `gh issue close … --comment "已恢復綠燈"`，把一張
    描述真實故障的 P1 單關掉。極性一旦被改回黑名單，本測試必須紅。
    """

    def test_alert_uses_success_whitelist_not_failure_blacklist(self):
        for label, path, _full_id, alert_id, _prefix in _NIGHTLY_PLATFORMS:
            with self.subTest(workflow=label):
                block = _job_block(path.read_text(encoding="utf-8"), alert_id)
                self.assertRegex(
                    block, _SUCCESS_WHITELIST_RE,
                    f"{label} 的 {alert_id} 缺 success 白名單判讀式——"
                    f"判讀極性若退回黑名單（只有字面 failure 算紅），"
                    f"cancelled／timed_out／skipped／null／job 改名 五種情境都會被"
                    f"當成綠燈並自動關閉仍然有效的 P1 issue（R68 沙箱九情境實跑復現）",
                )
                self.assertNotRegex(
                    block, _FAILURE_BLACKLIST_RE,
                    f"{label} 的 {alert_id} 仍留有黑名單判讀式 "
                    f'`[ "$conclusion" = "failure" ]`——fail-open 極性回歸',
                )

    def test_alert_degrades_gh_api_failure_to_non_green(self):
        for label, path, _full_id, alert_id, _prefix in _NIGHTLY_PLATFORMS:
            with self.subTest(workflow=label):
                block = _job_block(path.read_text(encoding="utf-8"), alert_id)
                self.assertRegex(
                    block, _API_ERROR_FALLBACK_RE,
                    f"{label} 的 {alert_id} check step 缺 `|| echo \"api-error\"` 降級——"
                    f"該 step 是 `set -euo pipefail` + `gh api`，API 失敗會直接打死 step，"
                    f"outputs.failed 變空字串使下游 == 'true' / == 'false' 兩個分支都不成立，"
                    f"告警整條靜默蒸發（無任何 issue、無任何留言）",
                )

    def test_close_branch_guarded_by_check_output(self):
        for label, path, _full_id, alert_id, _prefix in _NIGHTLY_PLATFORMS:
            with self.subTest(workflow=label):
                block = _job_block(path.read_text(encoding="utf-8"), alert_id)
                self.assertEqual(
                    len(_CLOSE_GUARD_RE.findall(block)), 1,
                    f"{label} 的 {alert_id} 預期恰一個 `failed == 'false'` 關單守衛——"
                    f"守衛消失＝關單無條件執行；守衛變多＝出現第二條未經白名單判讀的關單路徑",
                )


class TestNightlyJobNameSelectorInterlock(unittest.TestCase):
    """R68：alert 的 jq `startswith("X")` ↔ nightly-full 的 `name:` 前綴互鎖。

    Rule 9：這兩處是兩份手寫字面值，中間沒有任何共用來源（GitHub Actions 的
    `jobs.<id>.name` 不支援 `env` context，抽成變數這條路不通）。本 repo 慣例
    會在 job 顯示名前後加輪次註記，一旦加在**前面**，`startswith` 就落空、
    conclusion 變 "unknown"——修復前那等於「綠燈」，修復後等於「開單」，
    兩種都不是實況。故必須有機械物看住「選擇子仍是顯示名的前綴」。
    """

    def test_jq_selector_is_prefix_of_nightly_full_job_name(self):
        for label, path, full_id, alert_id, expected_prefix in _NIGHTLY_PLATFORMS:
            with self.subTest(workflow=label):
                text = path.read_text(encoding="utf-8")
                alert_block = _job_block(text, alert_id)
                selectors = sorted(set(_JQ_STARTSWITH_RE.findall(alert_block)))
                self.assertEqual(
                    selectors, [expected_prefix],
                    f"{label} 的 {alert_id} 抽到的 jq startswith 選擇子為 {selectors}，"
                    f"預期恰一個 {expected_prefix!r}——抽取 pattern 或 jq 寫法已漂移，"
                    f"下方前綴斷言會失去鑑別力",
                )
                display_name = _job_display_name(_job_block(text, full_id))
                self.assertTrue(
                    display_name.startswith(selectors[0]),
                    f"{label}：{alert_id} 的 jq 選擇子 {selectors[0]!r} 不是 {full_id} "
                    f"顯示名 {display_name!r} 的前綴——alert 會查不到該 job、"
                    f"conclusion 降級成 'unknown'，告警指向錯誤的結論",
                )


class TestRootInfraNightlyStalenessSentinel(unittest.TestCase):
    """R68（P1）：root-infra-ci.yml 第 15 道「nightly-full 排程陳舊度哨兵」。

    Rule 9：兩支 `*-nightly-full` 是唯一會在真 Windows／真 macOS 上跑完整
    AutoClaude 測試樹的通道，卻是 `continue-on-error: true` 的非阻斷 job；
    2026-07-15～07-27 連續 5 次排程全紅、18 天零成功，而三道既有哨兵在結構上
    都偵測不到（alert 同計費平面、`_check_ci_liveness` 只取 --limit 1 且不分
    事件、`_check_nightly_heartbeat` 只讀本機 log mtime）。本哨兵是唯一會在
    每次 push 都問一次「那條真機通道還活著嗎」的機械物，且**必須阻斷**——
    非阻斷正是病因本身。
    """

    def _sentinel_step(self) -> str:
        text = _ROOT_INFRA_CI.read_text(encoding="utf-8")
        m = re.search(r"^      - name: nightly-full 排程陳舊度哨兵.*?(?=^      - name: |\Z)",
                      text, re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(
            m, "root-infra-ci.yml 找不到「nightly-full 排程陳舊度哨兵」step——"
               "第 15 道被移除或改名（該道是 R68 P1 修復的唯一載體）")
        return m.group(0)

    def test_sentinel_queries_both_workflows_scheduled_success(self):
        step = self._sentinel_step()
        exec_only = "\n".join(
            ln for ln in step.splitlines() if not ln.lstrip().startswith("#")
        )
        for wf in ("windows-compat-ci.yml", "macos-compat-ci.yml"):
            self.assertIn(
                wf, exec_only,
                f"陳舊度哨兵的**非註解**行未查 {wf}——單邊查詢等於另一平台的真機"
                f"通道回到零偵測狀態",
            )
        self.assertIn(
            "--event schedule --status success", exec_only,
            "陳舊度哨兵未以 `--event schedule --status success` 查詢——"
            "不分事件類型就會被 push 事件的綠燈滿足（R68 的整個缺陷就是"
            "「四支 CI 全綠」只涵蓋 push 事件）",
        )
        self.assertIn(
            "MAX_AGE_DAYS", exec_only,
            "陳舊度哨兵沒有陳舊門檻——只判「有沒有成功過」會讓 2026-07-14 那一次"
            "成功永遠滿足它",
        )

    def test_sentinel_is_blocking_not_advisory(self):
        step = self._sentinel_step()
        self.assertNotIn(
            "continue-on-error", step,
            "陳舊度哨兵被改成 continue-on-error——非阻斷正是 nightly-full 自己被"
            "忽略 18 天的機制，再加一層非阻斷等於複製病因",
        )
        self.assertIn(
            "exit 1", step,
            "陳舊度哨兵沒有 `exit 1`——只 echo `::error::` 不會讓 step 失敗，"
            "job 仍是綠的（GitHub 的 error annotation 不改變 exit code）",
        )

    def test_workflow_level_permissions_include_actions_read(self):
        text = _ROOT_INFRA_CI.read_text(encoding="utf-8")
        m = re.search(r"^permissions:\n((?:  \w+: \w+\n)+)", text, re.MULTILINE)
        self.assertIsNotNone(m, "root-infra-ci.yml 找不到 workflow 層 permissions 區塊")
        perms = m.group(1)
        self.assertIn(
            "  actions: read\n", perms,
            "root-infra-ci.yml 缺 `actions: read`——陳舊度哨兵的 `gh run list` 會 403，"
            "而它有 `|| echo` 降級路徑，403 會被判成「查無成功紀錄」而非啞掉（fail-closed，"
            "不會假綠），但那是持續假紅、無法區分真因",
        )
        self.assertNotIn(
            "write", perms,
            f"root-infra-ci.yml 出現寫入權限（現況應全唯讀）：{perms!r}——"
            f"本 workflow 純驗證不回寫，最小權限原則",
        )


# --- compat-CI paths 觸發面對稱性 ------------------------------------------

# 觸發面下限釘選：低於此數＝paths 抽取管線疑似壞掉（0 命中會讓下方覆蓋斷言
# 恆真而靜默假綠；同 tools/run_root_unittests.py MIN_TESTS／check_script_parity
# _MIN_EXTRACT_COUNTS 慣例）。現況 windows=65／macos=67。
_MIN_PATHS_ENTRIES = 60
# 全 repo tracked `.sh`/`.ps1` 數量下限（現況 305）——列舉器抓不到東西時同上。
_MIN_TRACKED_SCRIPTS = 250

_PATHS_BLOCK_HEADER_RE = re.compile(r"^    paths:\s*$")
_PATHS_ENTRY_RE = re.compile(r'^\s+- "(.+)"\s*$')


def _paths_blocks(path: Path) -> list[list[str]]:
    """抽出 workflow 內全部 `    paths:` 區塊（本 repo 慣例＝push 與 pull_request 各一）。"""
    lines = path.read_text(encoding="utf-8").splitlines()
    blocks: list[list[str]] = []
    for i, line in enumerate(lines):
        if not _PATHS_BLOCK_HEADER_RE.match(line):
            continue
        entries: list[str] = []
        j = i + 1
        while j < len(lines) and not re.match(r"^\s{0,4}\S", lines[j]):
            m = _PATHS_ENTRY_RE.match(lines[j])
            if m:
                entries.append(m.group(1))
            j += 1
        blocks.append(entries)
    return blocks


def _gh_filter_pattern_to_re(pattern: str) -> re.Pattern[str]:
    """GitHub Actions filter-pattern → regex（`*` 不跨 `/`、`**` 跨、`**/` 可為空）。

    刻意**不**用 `fnmatch`（姊妹鎖 AISDLC_SDD/scripts/tests/
    test_ci_paths_cover_root_consumers.py 用的是 fnmatch，那裡 `*` 會跨 `/` ⇒
    比 GitHub 實際語意寬鬆、會低估未覆蓋面）。`**/` 譯為 `(?:.*/)?` 而非
    `.*/`：GitHub 的 `**/*.ps1` 也匹配 repo 根層的 `foo.ps1`。
    """
    placeholder = "\x00"
    src = pattern.replace("**/", placeholder)
    out: list[str] = []
    i = 0
    while i < len(src):
        ch = src[i]
        if ch == placeholder:
            out.append("(?:.*/)?")
            i += 1
        elif src.startswith("**", i):
            out.append(".*")
            i += 2
        elif ch == "*":
            out.append("[^/]*")
            i += 1
        elif ch == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(ch))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def _tracked_scripts() -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(_REPO_ROOT), "ls-files", "--", "*.sh", "*.ps1"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise AssertionError(f"git ls-files 失敗（rc={proc.returncode}）：{proc.stderr}")
    return sorted(ln for ln in proc.stdout.splitlines() if ln)


class TestCompatCiScriptTriggerSymmetry(unittest.TestCase):
    """R68 SCAN-E（DOWNGRADED→P3）：兩支 compat-CI 對 `.sh`／`.ps1` 的觸發面對稱。

    Rule 9（測意圖）：windows 側對 `.ps1` 用 `**/*.ps1` 兜底、對 `.sh` 逐一列舉；
    macos 側恰好相反。逐一列舉的那一面**零機械完整性鎖**——新增一支腳本只要
    落在既有列舉之外，該平台的 CI 就靜默不觸發，而「靜默不觸發」在 GitHub UI
    上與「跑過且通過」長得一模一樣。實測（R68）全 repo 305 支腳本中確有 1 支
    （`AutoClaude/tools/run_mutmut_in_docker.sh`）只觸發 macOS 側；已補列，
    使本鎖得以維持**零豁免清單**形態——豁免清單本身即 fail-open 面。

    刻意不改成兩側都通配（原提案 A）：那會讓 30 個凍結版樹下的腳本也觸發兩支
    compat-CI，代價與效益不成比例，且與凍結版「不回改」政策相斥。
    """

    def test_paths_blocks_extractable_and_symmetric_within_each_workflow(self):
        for label, path in (("windows-compat-ci.yml", _WINDOWS_COMPAT_CI),
                            ("macos-compat-ci.yml", _MACOS_COMPAT_CI)):
            with self.subTest(workflow=label):
                blocks = _paths_blocks(path)
                self.assertEqual(
                    len(blocks), 2,
                    f"{label} 預期恰兩個 paths 區塊（push ＋ pull_request），實得 "
                    f"{len(blocks)}——抽取管線或 workflow 結構已變動",
                )
                for n, block in enumerate(blocks):
                    self.assertGreaterEqual(
                        len(block), _MIN_PATHS_ENTRIES,
                        f"{label} 第 {n + 1} 個 paths 區塊只抽到 {len(block)} 條 < 下限 "
                        f"{_MIN_PATHS_ENTRIES}——條目引號風格改變或區塊被腰斬時，"
                        f"下方覆蓋斷言會因清單過小而**全面翻紅或恆真**，先在這裡指路",
                    )
                self.assertEqual(
                    blocks[0], blocks[1],
                    f"{label} 的 push 與 pull_request paths 清單不一致——"
                    f"單側補條目時另一側的觸發面靜默落後（差集："
                    f"{sorted(set(blocks[0]) ^ set(blocks[1]))}）",
                )

    def test_every_tracked_script_triggers_both_compat_ci(self):
        scripts = _tracked_scripts()
        self.assertGreaterEqual(
            len(scripts), _MIN_TRACKED_SCRIPTS,
            f"git ls-files 只列舉到 {len(scripts)} 支 .sh/.ps1 < 下限 "
            f"{_MIN_TRACKED_SCRIPTS}——列舉器失效會讓下方覆蓋斷言恆真（假綠）",
        )
        matchers = {
            label: [_gh_filter_pattern_to_re(p) for p in _paths_blocks(path)[0]]
            for label, path in (("windows-compat-ci.yml", _WINDOWS_COMPAT_CI),
                                ("macos-compat-ci.yml", _MACOS_COMPAT_CI))
        }
        uncovered: dict[str, list[str]] = {}
        for label, pats in matchers.items():
            missing = [s for s in scripts if not any(r.match(s) for r in pats)]
            if missing:
                uncovered[label] = missing
        self.assertEqual(
            uncovered, {},
            "下列 tracked 腳本不會觸發對應的 compat-CI（改它時該平台 CI 靜默不跑，"
            "而 GitHub UI 上「沒觸發」與「跑過且通過」長得一樣）：\n"
            + "\n".join(f"  {k}: {v}" for k, v in sorted(uncovered.items()))
            + "\n  處置：在該 workflow 的 push ＋ pull_request 兩個 paths 區塊各補一條"
              "（本鎖刻意零豁免清單——豁免清單本身即 fail-open 面）",
        )

    def test_matcher_respects_github_slash_semantics(self):
        """列舉器/比對器自證：`*` 不得跨 `/`（用 fnmatch 會跨 ⇒ 高估覆蓋面）。"""
        self.assertIsNone(_gh_filter_pattern_to_re("tools/*.sh").match("tools/lib/a.sh"))
        self.assertIsNotNone(_gh_filter_pattern_to_re("tools/*.sh").match("tools/a.sh"))
        self.assertIsNotNone(_gh_filter_pattern_to_re("**/*.ps1").match("a/b/c.ps1"))
        self.assertIsNotNone(_gh_filter_pattern_to_re("**/*.ps1").match("root.ps1"))
        self.assertIsNotNone(_gh_filter_pattern_to_re("tools/tests/**").match("tools/tests/x/y.py"))


if __name__ == "__main__":
    unittest.main()
