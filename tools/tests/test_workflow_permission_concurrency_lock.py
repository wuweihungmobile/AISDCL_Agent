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
     workflow 的成功紀錄。此道是 R68 對「兩支 nightly-full 自 2026-07-14 起
     18 天零成功而三道既有哨兵結構上都偵測不到」的直接修復（誠實劃界見該
     workflow 檔頭第 15 道：本道與被偵測者同計費平面）。
     **R69 訂正（DEF-101-703）**：R68 版寫死 `--event schedule`，與它自己印出的
     處置指令（`gh workflow run` ⇒ `event=workflow_dispatch`）實證互斥、照做也
     解不開；且無 `if:`／無豁免途徑 ⇒ 對每一次 push 都必紅＝死鎖。現行判準改為
     「兩事件都計入」＋「帶到期日／理由／長度上限的顯式豁免」，本類別同步鎖住
     **反 fail-open 三道保險**，確保豁免不能退化成永久假綠。
  4. `TestCompatCiScriptTriggerSymmetry` — 兩支 compat-CI 的 `paths` 白名單
     對全部 tracked `*.sh`／`*.ps1` 的觸發面必須**完全對稱、零豁免**。
     windows 側逐一列舉 `.sh`、macos 側用 `**/*.sh` 兜底（反之亦然）的不對稱
     設計本身保留（改成兩側都通配會讓凍結版樹下的腳本也觸發，代價不成比例），
     但「列舉面漏一支」從此有機械訊號。
"""
from __future__ import annotations

import datetime
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

# R69：豁免到期的本機示警門檻（天）。CI 上到期即自動轉紅是**設計正確**，但那是
# 「到期當天才在雲端炸」；本機此前只驗「不得超過 MAX_WAIVER_DAYS 上限」，過期後
# `(until - today).days` 變負數、恆 ≤ 上限 ⇒ 過期 51 天本機仍全綠（實測）。
_WAIVER_WARN_DAYS = 3


def waiver_expiry_verdict(
    until: datetime.date, today: datetime.date, warn_days: int = _WAIVER_WARN_DAYS
) -> tuple[str, str]:
    """純函式：回傳 (`ok` / `warn` / `expired`, 處置訊息)。

    處置一律相同：先查那兩個排程窗口是否已成功；成功 ⇒ 把 `WAIVER_UNTIL` 清成空字串
    （回到無豁免的阻斷態），而不是把日期往後推——往後推只是續買時間，缺陷還在。
    """
    left = (until - today).days
    action = (
        "處置：唯讀查 `gh run list --workflow windows-compat-ci.yml "
        "--workflow macos-compat-ci.yml --status success`（不得 rerun／dispatch）確認"
        f"{until} 前的排程窗口是否已成功；已成功 ⇒ 把 root-infra-ci.yml 的 "
        'WAIVER_UNTIL 清成 ""（恢復無豁免阻斷態），仍未成功 ⇒ 回 DEF-101-703 '
        "重新判根因後才續期，不得無腦往後推日期"
    )
    if left < 0:
        return "expired", (
            f"WAIVER_UNTIL={until} 已於 {-left} 天前到期（今天 {today}）——"
            f"root-infra-ci 的陳舊度哨兵已自動恢復阻斷，下一次 push 必紅。{action}"
        )
    if left <= warn_days:
        return "warn", (
            f"WAIVER_UNTIL={until} 只剩 {left} 天到期（今天 {today}）——"
            f"到期後 root-infra-ci 會自動轉紅。{action}"
        )
    return "ok", f"WAIVER_UNTIL={until} 尚有 {left} 天（今天 {today}）"

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

    #: 查詢迴圈的**被迭代清單**（`for wf in <清單>; do`）。
    #: 🔴 R69 終審 P1：本道原本只對整段非註解文字做 `assertIn(wf, ...)`，而該段文字裡
    #: 除了查詢迴圈之外還有**處置指令的 echo**（`gh workflow run windows-compat-ci.yml`）
    #: 也逐字含這兩個檔名 ⇒ 把 `windows-compat-ci.yml` 從查詢迴圈刪掉（`for wf in
    #: macos-compat-ci.yml; do`）後本類 9 支仍**全綠**（實測），Windows 真機通道退回
    #: 零偵測而無人察覺。字串「出現與否」不是「有沒有被查」的證據——鎖必須讀迴圈本身。
    _QUERY_LOOP_RE = re.compile(r"^\s*for wf in (?P<items>[^;]+);\s*do\s*$", re.MULTILINE)

    def _queried_workflows(self, step: str) -> list[str]:
        exec_only = self._exec_lines(step)
        matches = self._QUERY_LOOP_RE.findall(exec_only)
        self.assertEqual(
            len(matches), 1,
            f"陳舊度哨兵的 `for wf in …; do` 查詢迴圈應恰好一個，實得 {len(matches)} 個"
            f"（0＝迴圈被移除或改寫，本鎖失去唯一可信的判準；>1＝判準歧義）：{matches}",
        )
        return matches[0].split()

    def test_sentinel_queries_both_workflows_scheduled_success(self):
        step = self._sentinel_step()
        exec_only = self._exec_lines(step)
        queried = self._queried_workflows(step)
        for wf in ("windows-compat-ci.yml", "macos-compat-ci.yml"):
            self.assertIn(
                wf, queried,
                f"陳舊度哨兵的**查詢迴圈**未列 {wf}——單邊查詢等於另一平台的真機"
                f"通道回到零偵測狀態。實得迴圈清單：{queried}"
                f"（⚠️ 本道刻意讀 `for wf in …` 的被迭代清單，不是整段文字：處置指令的"
                f" echo 也含這兩個檔名，比對全文會被 echo 滿足＝假綠）",
            )
        self.assertIn(
            "--status success", exec_only,
            "陳舊度哨兵未以 `--status success` 查詢——不看結論就會被「有 run 但全紅」"
            "滿足（R68 的整個缺陷就是通道連續 5 次全紅卻無人察覺）",
        )
        self.assertRegex(
            exec_only, r"for ev in schedule workflow_dispatch\b",
            "陳舊度哨兵未同時計入 `schedule` 與 `workflow_dispatch`——DEF-101-703："
            "它印給人的處置指令 `gh workflow run <wf>.yml` 產生的是 "
            "workflow_dispatch 的 run，只查 schedule ⇒ 照著處置做也永遠解不開，"
            "閘門變成無法解除的死鎖（而不是可修復的訊號）",
        )
        self.assertNotIn(
            "--event schedule --status success", exec_only,
            "偵測到 R68 舊的單事件查詢字面（`--event schedule --status success`）——"
            "該寫法與處置指令實證互斥，是 DEF-101-703 死鎖的成因本身",
        )
        self.assertIn(
            "gh workflow run", exec_only,
            "陳舊度哨兵沒有印出可執行的處置指令——阻斷式閘門必須同時給出解除路徑",
        )
        self.assertIn(
            "MAX_AGE_DAYS", exec_only,
            "陳舊度哨兵沒有陳舊門檻——只判「有沒有成功過」會讓 2026-07-14 那一次"
            "成功永遠滿足它",
        )

    def test_sentinel_is_blocking_not_advisory(self):
        step = self._sentinel_step()
        exec_only = self._exec_lines(step)
        # 只掃**非註解**行：本 step 的誠實劃界註解會逐字提到被監控者自己的
        # `continue-on-error: true`（那正是它要補的洞），對整份文字做 assertNotIn
        # 會把「解釋病因」誤判成「犯病」。
        self.assertNotIn(
            "continue-on-error", exec_only,
            "陳舊度哨兵被改成 continue-on-error——非阻斷正是 nightly-full 自己被"
            "忽略 18 天的機制，再加一層非阻斷等於複製病因",
        )
        self.assertIn(
            "exit 1", exec_only,
            "陳舊度哨兵沒有 `exit 1`——只 echo `::error::` 不會讓 step 失敗，"
            "job 仍是綠的（GitHub 的 error annotation 不改變 exit code）",
        )
        self.assertNotIn(
            "|| true", exec_only,
            "陳舊度哨兵出現 `|| true`——那是把阻斷式閘門靜默改成永遠綠的最短路徑",
        )
        # `(?m)` 不可省：`assertNotRegex` 走 `re.search` 且**預設不含 MULTILINE**，
        # 而 `step` 是多行文字 ⇒ 沒有旗標時 `^` 只錨在整段的第一個字元（那裡永遠是
        # `      - name:`），任何後續行的 `if: false` 都匹配不到、本道恆綠。
        # R69 QA 實測：注入 `        if: false` 後本檔 23 支全綠、零人抓到。
        self.assertNotRegex(
            step, r"(?m)^        if:", "陳舊度哨兵被加上 step 層 `if:`——"
            "條件化執行等於在某些事件下完全不檢查，那是消音不是修復",
        )

    # --- R69（DEF-101-703）：豁免機制的反 fail-open 保險 --------------------

    _WAIVER_RE = re.compile(r'^          WAIVER_UNTIL: "([^"]*)"$', re.MULTILINE)

    @staticmethod
    def _exec_lines(step: str) -> str:
        return "\n".join(ln for ln in step.splitlines()
                         if not ln.lstrip().startswith("#"))

    def test_waiver_is_explicit_dated_and_reasoned(self):
        """豁免只准以「顯式到期日 + 具名理由」形式存在，且理由必須引缺陷編號。

        Rule 9：豁免的**意義**是「已知根因在本 repo 之外、需要時間自證」，不是
        「這道太吵先關掉」。沒有到期日的豁免＝永久關閉；沒有缺陷編號的理由＝
        三個月後沒人知道它為什麼還在，於是永遠沒人敢刪。
        """
        step = self._sentinel_step()
        m = self._WAIVER_RE.search(step)
        self.assertIsNotNone(
            m, "陳舊度哨兵找不到 `WAIVER_UNTIL:` 宣告——豁免途徑被移除的話，"
               "本道又會退回 R68 的死鎖（根因在帳務平面時無法解除）")
        until = m.group(1)
        if not until:
            return  # 空字串＝目前無豁免，行為等同 R68 原版阻斷，合法終態
        self.assertRegex(
            until, r"^\d{4}-\d{2}-\d{2}$",
            f"WAIVER_UNTIL={until!r} 不是 YYYY-MM-DD——非日期字面值無法被稽核，"
            f"且 runtime 會 fail-loud")
        rm = re.search(r'^          WAIVER_REASON: "([^"]+)"$', step, re.MULTILINE)
        self.assertIsNotNone(rm, "設了 WAIVER_UNTIL 卻沒有 WAIVER_REASON")
        self.assertRegex(
            rm.group(1), r"DEF-\d{3}-\d{3}",
            "WAIVER_REASON 未引任何缺陷編號——豁免必須可回溯到帳本上的一列，"
            "否則它就是一句沒有負責人的話")

    def test_waiver_window_is_bounded(self):
        """豁免視窗必須有上限，且宣告的到期日不得超出該上限。

        缺這條，`WAIVER_UNTIL: "2099-01-01"` 就是一鍵把阻斷式哨兵變永久假綠——
        比刪掉它更糟，因為表面上這道還在。
        """
        step = self._sentinel_step()
        exec_only = self._exec_lines(step)
        mm = re.search(r'^          MAX_WAIVER_DAYS: "(\d+)"$', step, re.MULTILINE)
        self.assertIsNotNone(mm, "陳舊度哨兵缺 MAX_WAIVER_DAYS 上限宣告")
        max_days = int(mm.group(1))
        self.assertLessEqual(
            max_days, 31,
            f"MAX_WAIVER_DAYS={max_days} 超過 31 天——一次能買超過一個月的豁免，"
            f"實務上等於沒有上限")
        self.assertIn(
            'if [ "$(( (waiver_deadline - now) / 86400 ))" -gt "${MAX_WAIVER_DAYS}" ]',
            exec_only,
            "MAX_WAIVER_DAYS 只宣告未執行——上限不被 runtime 檢查等於裝飾品")
        um = self._WAIVER_RE.search(step)
        if um and um.group(1):
            until = datetime.date.fromisoformat(um.group(1))
            today = datetime.date.today()
            self.assertLessEqual(
                (until - today).days, max_days,
                f"WAIVER_UNTIL={until} 距今超過 MAX_WAIVER_DAYS={max_days} 天——"
                f"CI 上會 fail-loud，這條鎖讓它在本機就被抓到")

    # --- R71：advisory 段（覆蓋面擴大，但不把主線抵押給雲端狀態）----------------
    #
    # 為何是**新增**判準而不是改 R69 那幾道：`_QUERY_LOOP_RE` 釘的「恰好一個
    # `for wf in …; do`」守的是**阻斷段**的判準可讀性（R69 終審 P1：處置指令的 echo
    # 也含那兩個檔名 ⇒ 比對全文會假綠）。advisory 段用不同的迭代變數（`advisory_wf`）
    # 且**不得**觸碰 `stale`，所以那道鎖的語意一字未改、仍然只讀阻斷迴圈；本區三支是
    # 疊在它上面的新防線，不是它的替代品。

    _ADVISORY_LOOP_RE = re.compile(r"^\s*for advisory_wf in \$advisory_list;\s*do\s*$",
                                   re.MULTILINE)
    #: advisory 掃描面的排除清單（`case "$wf_base" in a|b) continue;; esac`）。
    _ADVISORY_SKIP_RE = re.compile(
        r'^\s*case "\$wf_base" in ([^)]+)\) continue;;\s*esac\s*$', re.MULTILINE)
    #: 「現查含 cron 的 workflow」——與 workflow 內 grep 的語意同源（未被註解掉的 cron）。
    _CRON_LINE_RE = re.compile(r"^[ \t]*-[ \t]*cron:", re.MULTILINE)
    #: 掃描面塌陷下限（R71 現查 7 支；取 5 是為了容忍刻意減少排程軌，不是快照）。
    _MIN_CRON_WORKFLOWS = 5

    def _advisory_block(self, step: str) -> str:
        """advisory 迴圈本體（`for advisory_wf …` 到同縮排的 `done`）。"""
        lines = self._exec_lines(step).splitlines()
        starts = [i for i, ln in enumerate(lines)
                  if self._ADVISORY_LOOP_RE.match(ln)]
        self.assertEqual(
            len(starts), 1,
            f"advisory 迴圈應恰好一個，實得 {len(starts)} 個——0＝覆蓋面擴充被移除，"
            f"其餘含 cron 的排程軌回到零偵測；>1＝判準歧義")
        indent = len(lines[starts[0]]) - len(lines[starts[0]].lstrip())
        for i in range(starts[0] + 1, len(lines)):
            if lines[i].strip() == "done" and (len(lines[i]) - len(lines[i].lstrip())) == indent:
                return "\n".join(lines[starts[0]:i + 1])
        self.fail("advisory 迴圈找不到同縮排的 `done`——區塊界線抓不到，下面兩支鎖會空轉")

    def _cron_workflows(self) -> set[str]:
        wf_dir = _REPO_ROOT / ".github" / "workflows"
        found = {p.name for p in sorted(wf_dir.glob("*.yml"))
                 if self._CRON_LINE_RE.search(p.read_text(encoding="utf-8", errors="replace"))}
        self.assertGreaterEqual(
            len(found), self._MIN_CRON_WORKFLOWS,
            f"只掃到 {len(found)} 支含 cron 的 workflow（下限 {self._MIN_CRON_WORKFLOWS}）"
            f"——掃描面已塌，本區三支鎖會變成恆真")
        return found

    def test_every_cron_track_is_watched_by_one_of_the_two_tiers(self):
        """覆蓋面：每一支含 cron 的 workflow 都必須落在「阻斷段 ∪ advisory 段」。

        Rule 9（鎖意圖）：R68/R69 只看兩支真機軌，而同批陣亡的排程軌有四支——
        「阻斷射程收窄」是**有意的取捨**（見該 step 內註解：全掃即把全 repo 的 push
        綁在雲端狀態上），但收窄的代價必須是「降級為 advisory」，不是「不看」。
        本鎖釘住那個等式：阻斷清單與 advisory 的排除清單必須逐字相同 ⇒ 從阻斷段
        移除一支就會自動掉進 advisory 段；兩份清單一旦分歧，中間那幾支會**靜默失聯**。
        """
        step = self._sentinel_step()
        blocking = set(self._queried_workflows(step))
        m = self._ADVISORY_SKIP_RE.search(self._exec_lines(step))
        self.assertIsNotNone(
            m, "advisory 段找不到 `case \"$wf_base\" in …) continue;; esac` 排除清單——"
               "結構被改動，覆蓋面等式無從驗證（不得靜默略過）")
        skipped = {s.strip() for s in m.group(1).split("|")}
        self.assertEqual(
            skipped, blocking,
            f"advisory 的排除清單與阻斷清單不一致：只在阻斷段＝{sorted(blocking - skipped)}"
            f"（會被印兩次，無害）；只在排除清單＝{sorted(skipped - blocking)}"
            f"（**兩段都不看＝靜默失聯**，本鎖存在的唯一理由）",
        )
        cron_wfs = self._cron_workflows()
        self.assertEqual(
            blocking - cron_wfs, set(),
            f"阻斷清單列了不存在／已無 cron 的 workflow：{sorted(blocking - cron_wfs)}"
            f"——`gh run list --workflow <打錯的檔名>` 回零筆，哨兵會安靜地什麼都不查",
        )

    def test_advisory_survey_scans_the_directory_instead_of_a_second_hardcoded_list(self):
        """advisory 的掃描面必須**現查**，不得是第二份會腐化的字面清單。

        WHY：本 repo 反覆踩的形狀是「文件／腳本裡寫死機器算得出的清單」
        （DEF-101-289／515 同一家族）。若 advisory 也列舉檔名，新增一支排程
        workflow 時它不會自動納管，而「沒被列進去」在輸出上與「健康」無法區分。
        """
        block_src = self._exec_lines(self._sentinel_step())
        self.assertIn(
            "for wf_path in .github/workflows/*.yml; do", block_src,
            "advisory 掃描面不是現查 workflow 目錄——第二份字面清單＝第二個漂移站點")
        self.assertIn(
            "grep -qE '^[[:space:]]*-[[:space:]]*cron:'", block_src,
            "advisory 未以「未被註解掉的 cron」為納管判準——與本 repo 其他排程掃描器"
            "（dormant 軌不算期望軌）語意不一致，會把刻意停用的軌報成失聯")

    def test_advisory_survey_can_never_block_the_push(self):
        """advisory 段不得觸碰 `stale`、不得自己 `exit`——它是提醒，不是閘門。

        這是本輪取捨的**另一半**：覆蓋面擴大到 7 支的前提，就是多出來那 5 支
        （含 4 支日頻）不會讓「某條日頻軌紅一天」變成「全 repo 不能 push」。
        若哪天有人想把某一支升級成阻斷，正確做法是把它加進阻斷迴圈的清單並承擔
        代價，而不是讓 advisory 段偷偷長出 exit——後者沒有任何 diff 訊號說明代價。
        """
        block = self._advisory_block(self._sentinel_step())
        self.assertNotIn(
            "stale=", block,
            f"advisory 迴圈內指派了 `stale`——advisory 變成阻斷，且該轉變沒有經過"
            f"「加進阻斷清單」這個看得見代價的動作：\n{block}")
        self.assertNotRegex(
            block, r"(?m)^\s*exit\s",
            f"advisory 迴圈內出現 `exit`——同上，繞過了阻斷射程的取捨：\n{block}")
        self.assertIn(
            "::warning::", block,
            "advisory 迴圈完全不出聲＝只是把查詢跑一遍給機器看，人不會知道")
        # 🔴 上一句只擋得住「把 echo 刪掉」。鑑別力驗證當場證明它擋不住更常見的
        # 形態：把觸發條件改成 `if false; then`——echo 字面還在，`assertIn` 照樣綠
        # （實測 rc=0）。這與 DEF-101-743 同型：「宣告的字串在場」不等於「那件事會
        # 發生」。故再釘一條：出聲與否必須由**查回來的結論**驅動。
        self.assertRegex(
            block, r"(?m)^\s*if .*\$a_concl.*;\s*then\s*$",
            f"advisory 的出聲條件沒有引用查回來的結論（`$a_concl`）——條件被改成恆假／"
            f"恆真時 `::warning::` 這行仍在原地，只看字串在不在的鎖抓不到：\n{block}")

    def test_waiver_is_not_expired_and_warns_before_it_is(self):
        """豁免到期／即將到期必須**在本機**就被看見（R69）。

        WHY 這條與上一條不同：`test_waiver_window_is_bounded` 只驗「不得超過上限」，
        它比的是 `(until - today).days <= MAX_WAIVER_DAYS`——過期後這個差值變**負數**，
        恆滿足上限 ⇒ 本機恆綠。實測（修前）：假設今天 2026-09-30、豁免早在 08-10 過期
        51 天，現行三條鎖仍全數 PASS。於是「到期」這件事只有在雲端 push 那一刻才會
        現形，而 CI 額度紀律要求盡量本機驗完再 push ⇒ 一定是在最不方便的時刻炸。
        本條把示警左移：≤3 天 WARN（不擋，讓人有時間處置）、已過期即紅。
        """
        um = self._WAIVER_RE.search(self._sentinel_step())
        self.assertIsNotNone(um, "陳舊度哨兵找不到 WAIVER_UNTIL 宣告")
        if not um.group(1):
            return  # 空字串＝無豁免，無到期可言（合法終態）
        verdict, msg = waiver_expiry_verdict(
            datetime.date.fromisoformat(um.group(1)), datetime.date.today())
        if verdict == "expired":
            self.fail(msg)
        if verdict == "warn":
            # 不擋（還沒壞），但必須大聲——run_root_unittests 的輸出會帶出這行
            print(f"\n⚠️  [WAIVER 即將到期] {msg}\n")

    def test_waiver_expiry_verdict_red_warn_green_boundaries(self):
        """判準自證：三態邊界必須各自成立，否則上一條可能恆綠空轉。"""
        until = datetime.date(2026, 8, 10)
        for today, expect in (
            (datetime.date(2026, 8, 6), "ok"),       # 4 天 → 尚早
            (datetime.date(2026, 8, 7), "warn"),     # 3 天 → 門檻上
            (datetime.date(2026, 8, 10), "warn"),    # 當天 → 仍算警示不算過期
            (datetime.date(2026, 8, 11), "expired"),  # 隔天 → 紅
            (datetime.date(2026, 9, 30), "expired"),  # 過期 51 天 → 紅（修前恆綠的那一格）
        ):
            with self.subTest(today=today):
                verdict, msg = waiver_expiry_verdict(until, today)
                self.assertEqual(verdict, expect, msg)
                if verdict != "ok":
                    self.assertIn('WAIVER_UNTIL 清成 ""', msg,
                                  "訊息未指出正確處置（查排程成功即清空，而非往後推日期）")
                    self.assertIn("gh run list", msg, "訊息未指出查證方式")

    def test_waiver_misconfiguration_fails_loud(self):
        """豁免設定壞掉時必須當場 exit 1，不得靜默當成「沒豁免」或「永久豁免」。"""
        exec_only = self._exec_lines(self._sentinel_step())
        for needle, why in (
            ('date -u -d "${WAIVER_UNTIL} 23:59:59"',
             "未實際解析 WAIVER_UNTIL，無法判斷到期"),
            ('if [ -z "${WAIVER_REASON}" ]',
             "未擋下「有到期日卻無理由」的無法稽核豁免"),
        ):
            self.assertIn(needle, exec_only, f"反 fail-open 保險缺口：{why}")
        # 三道保險各自都要能讓 step 失敗：豁免區塊內至少三個 exit 1。
        waiver_block = exec_only.split('if [ "$waiver_deadline" -gt "$now" ]')[0]
        self.assertGreaterEqual(
            waiver_block.count("exit 1"), 3,
            "豁免合法性先驗區塊的 `exit 1` 少於三個——"
            "「無法解析／無理由／視窗過長」三種壞設定必須各自 fail-loud")

    def test_waived_run_still_reports_the_staleness_loudly(self):
        """豁免期內只降級為 ::warning::，**不得**跳過查詢或不印陳舊天數。

        豁免的正當性完全建立在「事實照樣每次 push 被印出來」之上；一旦變成消音，
        它就跟 R68 那個「非阻斷所以沒人看」的病因同構。
        """
        exec_only = self._exec_lines(self._sentinel_step())
        self.assertIn('if [ "$waiver_deadline" -gt "$now" ]; then lvl=warning; '
                      'else lvl=error; fi', exec_only,
                      "豁免未以「嚴重度降級」實作——若改成 skip 查詢就是消音")
        self.assertRegex(
            exec_only, r'echo "::\$\{lvl\}::.*天沒有成功執行',
            "陳舊訊息未走 ${lvl} 動態嚴重度——豁免期內仍必須印出陳舊天數")
        self.assertIn(
            "豁免到期後本道自動恢復阻斷", exec_only,
            "豁免通過時未聲明「到期自動恢復阻斷」——讀 log 的人會以為它被關掉了")

    # --- 本輪 R77-14：run 層看不見的那一半 ＋ 續期理由不得綁在日期上 ----------

    def test_sentinel_reads_the_job_layer_not_only_the_run_layer(self):
        """哨兵必須把 job 層 `steps` 長度算出來，不能只印 run 層 conclusion。

        Rule 9（測意圖）：run 層 `conclusion=failure` 在本 repo 有兩個**處置完全相反**
        的成因——(a) runner 從未被配置（帳務／額度平面，本 repo 內無可修處）、
        (b) 測試真的紅了（去看那次 run 紅在哪）。兩者在 run 層是同一個字，唯一分得
        出來的欄位是 job 的 `steps` 長度：帳務阻擋時 GitHub 連 step 都不會建立。
        修復前本道只印 run 層，於是它的「處置」段只能寫成一句要人自己去查的指示，
        而那句指示在整輪停擺期間**沒有任何一次被執行過**。
        """
        exec_only = self._exec_lines(self._sentinel_step())
        # 判準字串刻意不以 `/` 開頭：本樹另有一道鎖禁止 assert 拿 POSIX 絕對路徑
        # 字面值比對（Windows 上會渲染成反斜線 ⇒ Mac 全綠 Windows 假紅）。這裡比對
        # 的是 gh api 的**相對**路徑片段，不是檔案系統路徑。
        self.assertIn(
            "actions/runs/${run_id}/jobs", exec_only,
            "哨兵沒有查 job 層（gh api 的 actions/runs/<id>/jobs 端點）——只有 run 層 "
            "conclusion 時，「runner 從未配置」與「測試真的紅了」在輸出上無法分辨")
        self.assertIn(
            "(.steps|length)==0", exec_only,
            "哨兵沒有以 `steps` 長度為零判定 never-started——那是唯一分得出帳務"
            "阻擋與測試紅的欄位")
        self.assertIn(
            "never-started", exec_only,
            "哨兵沒有把 never-started 統計印出來——算了不印等於沒算")

    #: 續期理由內**不得**出現日曆日期（見下方測試的 WHY）。
    _CALENDAR_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
    #: 解除判準的必要標記——理由必須說「怎樣才算可以解除」，而不是「我猜它會好」。
    _RELEASE_CRITERION_MARK = "解除判準="

    def test_waiver_reason_states_a_checkable_release_criterion_not_a_dated_claim(self):
        """WAIVER_REASON 必須是可現查的解除判準，且不得夾帶日曆日期。

        Rule 9：豁免的正當性建立在「根因在本 repo 之外」這個**事實**上，而事實會變。
        修復前的理由把續期綁在一句對未來的預測上（斷言帳務已在某日恢復、再等兩個
        排程窗口即可自證）；後續量測推翻了那個預測，而**沒有任何機械物會說話**——
        豁免照樣自動生效到期滿。日期一旦寫進理由，它從被推翻的那一刻起就開始說謊。
        改法：理由只准描述「怎樣才算可以解除」，而那個判準必須是本 step 自己就會
        印出來的量測值（見 test_sentinel_reads_the_job_layer_not_only_the_run_layer）。

        射程劃界：`WAIVER_UNTIL` 本身**仍然是日期**且不受本條管——它是豁免視窗的
        界線（反 fail-open 三道保險之一），不是對世界的事實宣稱。
        """
        step = self._sentinel_step()
        if not self._WAIVER_RE.search(step).group(1):
            return  # 空字串＝無豁免，無理由可言（合法終態）
        rm = re.search(r'^          WAIVER_REASON: "([^"]+)"$', step, re.MULTILINE)
        self.assertIsNotNone(rm, "設了 WAIVER_UNTIL 卻沒有 WAIVER_REASON")
        reason = rm.group(1)
        self.assertNotRegex(
            reason, self._CALENDAR_DATE_RE,
            f"WAIVER_REASON 內出現日曆日期：{reason!r}——續期理由不得綁在對未來的"
            f"預測或某個時點的量測快照上（預測被推翻時沒有任何東西會響，豁免仍會"
            f"自動生效到期滿）。改寫成「怎樣才算可以解除」，並讓那個判準是本 step "
            f"自己會印出來的量測值。日期只准出現在 WAIVER_UNTIL")
        self.assertIn(
            self._RELEASE_CRITERION_MARK, reason,
            f"WAIVER_REASON 沒有寫出解除判準（缺 `{self._RELEASE_CRITERION_MARK}`）"
            f"——沒有解除判準的豁免只能靠日期到期，而到期＝硬紅，那正是 R68 死鎖"
            f"的形狀：現行理由＝{reason!r}")

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


# ══════════════════════════════════════════════════════════════════════════════
# 本輪 R77-55：concurrency 的 **repo-wide 枚舉**（不再只看 5 個具名常數）
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 缺陷本體：本檔上方全部 concurrency 斷言都綁在 `_ARCH_FITNESS`／`_AUTOCLAUDE_CI`／
# 兩支 compat-CI／`_ROOT_INFRA_CI` 這 5 個**具名常數**上，而且問的都是「那一段字面值
# 還在不在」。於是：
#   ① 沒被具名的 workflow 上，同一類缺陷完全隱形——實查 11 支，有 3 支的 workflow 層
#      group 只綁 `github.ref` 卻帶 `cancel-in-progress: true`，其中兩支同時被 schedule
#      與 workflow_dispatch 觸發；
#   ② 「group 分不分得出事件類型」這個**判準**本身，全 repo 沒有任何一支測試在問。
# 而這正是 R7／R15／R23 已經在 autoclaude-ci 與兩支 compat-CI 上各修過一次的缺陷——
# 修的是站點，不是判準，所以它在沒被具名的檔案上原封不動地活著。
#
# 為什麼「不分事件」會出事：`cancel-in-progress: true` 的語意是「同 group 的新 run
# 取消舊 run」。group 只綁 ref 時，在 main 上一次 workflow_dispatch 就會取消掉正在跑的
# push 閘門／排程強制閘門，而**被取消的 run 在結論欄不是紅色**——「沒跑完」與「跑過
# 且通過」幾乎無從分辨。這與本檔既有的 `TestNightlyAlertConclusionWhitelist` 是同一族：
# 非綠的東西被讀成綠。
#
# 射程劃界（誠實，不是免責）：本鎖只看**workflow 層** concurrency。job 層（兩支
# compat-CI 各三組）不納入，理由不是「懶得做」而是**該處不成立**：那三組要嘛是固定
# 字串＋`cancel-in-progress: false`（不取消，跨事件不可能互殺），要嘛是 per-ref cancel
# 而其觸發事件（push／pull_request）的 `github.ref` 天生不同（`refs/heads/*` vs
# `refs/pull/*/merge`）。job 層另有上方六支逐字面值鎖在守。
_WORKFLOW_DIR = _REPO_ROOT / ".github" / "workflows"
#: 掃描面下限（現況 11 支）——枚舉器抓不到東西時下方斷言恆真。
_MIN_WORKFLOWS = 9
#: 有取值面的 workflow 下限（現況 4 支：workflow 層 concurrency ＋ cancel:true ＋ 多事件）。
#: 沒有這一條，把全部 concurrency 區塊刪光反而會讓本鎖全綠。
_MIN_CANCELLING_WORKFLOWS = 3
_WF_LEVEL_CONCURRENCY_RE = re.compile(
    r"^concurrency:\n(?:\s*#.*\n)*  group:\s*(?P<group>.+?)[ \t]*\n"
    r"(?:\s*#.*\n)*  cancel-in-progress:\s*(?P<cancel>\S+)[ \t]*$",
    re.MULTILINE,
)
_EVENT_DIMENSION_RE = re.compile(r"github\.event_name")
_ON_EVENT_KEY_RE = re.compile(r"^  ([A-Za-z_]+):")


def workflow_events(text: str) -> list[str]:
    """該 workflow `on:` 區塊下宣告的事件名（2 空白縮排的鍵）。

    以行級掃描而非 yaml：本樹的根層 unittest 慣例是零第三方依賴（同本檔檔頭），
    且 YAML 會把 `on` 解析成布林 True 這個著名坑，行級掃描反而少一個失效面。
    """
    out: list[str] = []
    in_on = False
    for line in text.splitlines():
        if line.startswith("on:"):
            in_on = True
            continue
        if not in_on:
            continue
        if line and not line[0].isspace():
            break
        m = _ON_EVENT_KEY_RE.match(line)
        if m:
            out.append(m.group(1))
    return out


def cancelling_groups_without_event_dimension(workflow_dir: Path) -> tuple[list[str], int]:
    """回傳 (違規描述清單, 有取值面的 workflow 數)。

    有取值面＝同時滿足三條：有 workflow 層 concurrency、`cancel-in-progress: true`、
    `on:` 宣告 ≥2 種事件。三條缺一，「跨事件互殺」在該檔結構上不可能發生。
    """
    offenders: list[str] = []
    in_scope = 0
    for path in sorted(workflow_dir.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        m = _WF_LEVEL_CONCURRENCY_RE.search(text)
        if m is None or m.group("cancel").strip().lower() != "true":
            continue
        events = workflow_events(text)
        if len(events) < 2:
            continue
        in_scope += 1
        if not _EVENT_DIMENSION_RE.search(m.group("group")):
            offenders.append(
                f"{path.name}：group={m.group('group')!r}（事件 {events}，"
                f"cancel-in-progress: true）"
            )
    return offenders, in_scope


class TestConcurrencyGroupsAreEnumeratedRepoWide(unittest.TestCase):
    """R77-55：判準改成 repo-wide 枚舉，新增 workflow 自動納管。"""

    def test_scan_surface_is_not_empty(self) -> None:
        found = sorted(p.name for p in _WORKFLOW_DIR.glob("*.yml"))
        self.assertGreaterEqual(
            len(found), _MIN_WORKFLOWS,
            f"只枚舉到 {len(found)} 支 workflow（下限 {_MIN_WORKFLOWS}）——"
            f"掃描面已塌，本類其餘斷言會變成恆真：{found}")

    def test_every_cancelling_group_distinguishes_the_event(self) -> None:
        offenders, in_scope = cancelling_groups_without_event_dimension(_WORKFLOW_DIR)
        self.assertGreaterEqual(
            in_scope, _MIN_CANCELLING_WORKFLOWS,
            f"只有 {in_scope} 支 workflow 落在本判準的取值面（下限 "
            f"{_MIN_CANCELLING_WORKFLOWS}）——取值面歸零時下一條會恆真而假綠")
        self.assertEqual(
            offenders, [],
            "下列 workflow 的 concurrency group 分不出事件類型，而它同時帶 "
            "`cancel-in-progress: true` 且由多種事件觸發 ⇒ 一次手動 dispatch 就會"
            "取消掉進行中的 push／排程閘門，而被取消的 run 在結論欄不是紅色（與"
            "「跑過且通過」幾乎無從分辨）。\n"
            f"  命中：{offenders}\n"
            "  處置：在 group 尾端補 `-${{ github.event_name }}`"
            "（同 autoclaude-ci.yml 的既有寫法）；同檔多條 cron 另需補 "
            "`-${{ github.event.schedule }}`",
        )

    def test_criterion_flags_a_bare_ref_group_and_spares_the_safe_shapes(self) -> None:
        """鑑別力（Rule 9）：三種安全形狀不得誤報，唯一的危險形狀必須命中。"""
        import tempfile  # noqa: PLC0415

        d = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, d, True)
        head = "on:\n  push:\n    branches: [main]\n  workflow_dispatch:\n"
        single = "on:\n  push:\n    branches: [main]\n"
        cases = {
            # 危險：多事件 ＋ cancel ＋ group 只綁 ref
            "bad.yml": head + "concurrency:\n  group: x-${{ github.ref }}\n"
                              "  cancel-in-progress: true\njobs: {}\n",
            # 安全①：group 帶 event_name
            "ok_event.yml": head + "concurrency:\n"
                                   "  group: x-${{ github.ref }}-${{ github.event_name }}\n"
                                   "  cancel-in-progress: true\njobs: {}\n",
            # 安全②：不取消 ⇒ 跨事件不會互殺
            "ok_nocancel.yml": head + "concurrency:\n  group: x-${{ github.ref }}\n"
                                      "  cancel-in-progress: false\njobs: {}\n",
            # 安全③：只有一種事件 ⇒ 沒有跨事件可言
            "ok_single.yml": single + "concurrency:\n  group: x-${{ github.ref }}\n"
                                      "  cancel-in-progress: true\njobs: {}\n",
        }
        for name, body in cases.items():
            (d / name).write_text(body, encoding="utf-8", newline="\n")
        offenders, in_scope = cancelling_groups_without_event_dimension(d)
        self.assertEqual(in_scope, 2, f"取值面應為 bad.yml ＋ ok_event.yml：{offenders}")
        self.assertEqual(len(offenders), 1, offenders)
        self.assertIn("bad.yml", offenders[0])

    def test_event_extractor_reads_the_on_block_only(self) -> None:
        """`workflow_events` 自證：不得把 `on:` 之外的 2 空白縮排鍵算進來。"""
        text = ("name: demo\n"
                "on:\n"
                "  push:\n"
                "    branches: [main]\n"
                "  # 註解不算事件\n"
                "  schedule:\n"
                '    - cron: "0 0 * * *"\n'
                "jobs:\n"
                "  build:\n"
                "    runs-on: ubuntu-latest\n")
        self.assertEqual(workflow_events(text), ["push", "schedule"])


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


# ══════════════════════════════════════════════════════════════════════════════
# R74：`continue-on-error: true` 讓 CI 活性哨兵的 run 層判準**活體 fail-open**
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 為何併進本檔：本檔已是 DEF-101-703（`*-nightly-full` 18 天零成功而三道哨兵
# 結構上偵測不到）的鎖之家——見上方 `TestRootInfraNightlyStalenessSentinel`。
# 另立新檔會撞 `TestGuardLayerRatchet` shrink-only 棘輪（DEF-101-561③；🔴 R78 ARCH-03
# 訂正：R77 起它量的是逐檔行數的**淨額**而非檔數，新增檔案本身不再違規）。
#
# 🔴 缺陷本體（唯讀實查即可證，零網路）：`tools/lib/ci_liveness.py` 的活性判準是
# 「該 workflow 有沒有 `--status success` 的 run」。而兩支 compat-CI 的
# `*-nightly-full` 都帶 **job 層 `continue-on-error: true`**，語意逐字就是
# 「這個 job 紅了別影響 run 結論」⇒ 深度回歸整包爛掉，run 仍是 success，
# 哨兵照樣判新鮮、一聲不響。R69/R71 那三道偵測問的是「有沒有 run／是哪個事件帶來
# 的／run 結論代不代表這條軌」，都不是「run 結論代不代表那個 **job**」。
class TestRunLevelFailOpenOnNonBlockingNightly(unittest.TestCase):
    """哨兵必須自白「這支檔的 run 層綠燈不構成 nightly-full 健康的證據」。"""

    @staticmethod
    def _ci_liveness():
        import sys  # noqa: PLC0415

        sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
        import ci_liveness  # noqa: PLC0415

        return ci_liveness

    def test_both_compat_ci_are_flagged_as_run_level_fail_open(self) -> None:
        """活體：兩支 compat-CI 現況就命中。修前 `stale_schedule_tracks` 對此完全沉默。"""
        c = self._ci_liveness()
        for wf in (_WINDOWS_COMPAT_CI, _MACOS_COMPAT_CI):
            jobs = c.non_blocking_scheduled_jobs(wf)
            self.assertTrue(
                jobs,
                f"{wf.name} 的 nightly-full 帶 continue-on-error: true 卻沒被偵測到 ⇒ "
                "偵測器已與 workflow 形狀漂移（run 層假綠會回來）",
            )
            note = c.run_level_fail_open(_REPO_ROOT, wf.name)
            self.assertIsNotNone(note)
            self.assertIn("fail-open", note)
            self.assertIn("哨兵會把紅讀成綠", note,
                          "訊息必須逐字說出後果，否則讀者會把它當成無害的技術註記")

    def test_push_gated_non_blocking_job_is_not_flagged(self) -> None:
        """鑑別力（反向）：push 也會跑的非阻斷 job 紅了會讓 run 紅 ⇒ 不該報。

        沒有這一支，`non_blocking_scheduled_jobs` 可以退化成「只看
        continue-on-error」而照樣全綠——那會把大量無害站點報成盲區，
        而誤報的鎖最後一定被加豁免繞過（比沒有鎖更糟）。
        """
        c = self._ci_liveness()
        with self.subTest("排程閘 ＋ 非阻斷 ⇒ 命中"):
            self.assertEqual(
                c.non_blocking_scheduled_jobs(self._fixture(gated=True, soft=True)),
                ["nightly"])
        with self.subTest("非阻斷但無排程閘 ⇒ 不命中"):
            self.assertEqual(
                c.non_blocking_scheduled_jobs(self._fixture(gated=False, soft=True)), [])
        with self.subTest("有排程閘但阻斷 ⇒ 不命中"):
            self.assertEqual(
                c.non_blocking_scheduled_jobs(self._fixture(gated=True, soft=False)), [])

    def _fixture(self, *, gated: bool, soft: bool) -> Path:
        import tempfile  # noqa: PLC0415

        body = ["on:", "  schedule:", "    - cron: \"0 0 * * *\"", "jobs:", "  nightly:"]
        if gated:
            body.append("    if: github.event_name == 'schedule'")
        if soft:
            body.append("    continue-on-error: true")
        body += ["    runs-on: ubuntu-latest", "    steps:", "      - run: echo hi", ""]
        d = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, d, True)
        p = Path(d) / "fixture.yml"
        p.write_text("\n".join(body), encoding="utf-8", newline="\n")
        return p

    def test_the_finding_reaches_the_consumer(self) -> None:
        """接線鎖：偵測到卻沒接進 `stale_schedule_tracks` ⇒ 使用者一輩子看不到。

        這正是 DEF-101-786 那個形態（事實查證了、判定沒接上）在本模組的同款風險。
        """
        import shutil  # noqa: PLC0415
        import tempfile  # noqa: PLC0415
        import time  # noqa: PLC0415
        from unittest import mock  # noqa: PLC0415

        c = self._ci_liveness()
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        (root / ".github" / "workflows").mkdir(parents=True)
        shutil.copy(self._fixture(gated=True, soft=True),
                    root / ".github" / "workflows" / "demo.yml")
        with mock.patch.object(c, "_latest_success_run",
                               return_value=datetime.datetime.now(
                                   datetime.UTC).isoformat().replace("+00:00", "Z")), \
             mock.patch.object(c, "_latest_attempt", return_value=None):
            out = c.stale_schedule_tracks(root, time.monotonic() + 25)
        self.assertTrue(any("fail-open" in f for f in out),
                        f"run 層 fail-open 未進入回報清單（實得 {out}）")


# ══════════════════════════════════════════════════════════════════════════════
# 本輪 R77-06b：push 閘 never-started 比率（ci_liveness 原本結構上看不見的那一半）
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 併進本檔的理由與上一節同：本檔已是「CI 死亡通道」那一族鎖的家，另立新檔會推高
# `TestGuardLayerRatchet` 的淨行數（DEF-101-561③；R78 ARCH-03 訂正過的現行語意）。
#
# 缺陷本體（唯讀 gh 實查）：`ci_liveness` 的掃描面只認有 cron 的 workflow，而 push 軌的
# 主閘門（root-infra-ci／aisdlc-sdd-ci）沒有 cron ⇒ 一輩子不會被看到。實查近 100 筆／軌
# 的視窗，兩者分別有 73／42 筆 run 的 job 從未被配置 runner；同一時間本模組實跑的結論
# 是「零陳舊軌」。本節鎖三件事：判準有鑑別力、不誤報、而且**接得到消費者**。
class TestPushGateNeverStartedRatio(unittest.TestCase):
    """R77-06b：push 軌 never-started 比率的鑑別力與接線。"""

    @staticmethod
    def _ci_liveness():
        import sys  # noqa: PLC0415

        sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
        import ci_liveness  # noqa: PLC0415

        return ci_liveness

    @staticmethod
    def _run(concl: str, seconds: float) -> dict:
        start = datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC)
        end = start + datetime.timedelta(seconds=seconds)
        return {"conclusion": concl,
                "startedAt": start.isoformat().replace("+00:00", "Z"),
                "updatedAt": end.isoformat().replace("+00:00", "Z")}

    def test_never_started_proxy_separates_billing_block_from_a_real_red(self) -> None:
        """鑑別力（Rule 9）：判準要分得出「runner 沒被配置」與「測試真的紅了」。

        門檻取 10 秒不是隨手挑的：實測有一筆 15 秒的 failure 是**真紅**（steps=26）。
        若把上界放寬到 20 秒，那一筆會被誤判成帳務阻擋——判準會開始替真紅背書。
        """
        c = self._ci_liveness()
        self.assertEqual(c.never_started_count([self._run("failure", 2)]), 1)
        self.assertEqual(c.never_started_count([self._run("failure", 15)]), 0,
                         "15 秒的 failure 是真紅（實測 steps=26），不得算成 never-started")
        self.assertEqual(c.never_started_count([self._run("success", 2)]), 0)
        self.assertEqual(c.never_started_count([{"conclusion": "failure"}]), 0,
                         "缺時戳的 run 無從判斷，不得猜")
        self.assertEqual(c.never_started_count([{"nonsense": 1}, "not-a-dict"]), 0)

    def _probe(self, runs, *, push_yaml: bool = True):
        import shutil  # noqa: PLC0415
        import tempfile  # noqa: PLC0415
        import time  # noqa: PLC0415
        from unittest import mock  # noqa: PLC0415

        c = self._ci_liveness()
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        (root / ".github" / "workflows").mkdir(parents=True)
        head = "on:\n  push:\n    branches: [main]\n" if push_yaml else "on:\n  schedule:\n"
        (root / ".github" / "workflows" / "demo.yml").write_text(
            head + "jobs: {}\n", encoding="utf-8", newline="\n")
        with mock.patch.object(c, "_push_runs", return_value=runs):
            return c.push_gate_never_started(root, time.monotonic() + 25)

    def test_a_billing_stall_window_is_reported(self) -> None:
        """正向注入：73/100 的 never-started 比率必須出聲（實測過的真實比率）。"""
        runs = [self._run("failure", 2)] * 73 + [self._run("success", 300)] * 27
        out = self._probe(runs)
        self.assertEqual(len(out), 1, out)
        self.assertIn("73/100", out[0])
        self.assertIn("不是**測試紅", out[0],
                      "訊息必須說出後果，否則讀者會把它當成無害的技術註記")
        self.assertIn("視窗下緣不是問題的起點", out[0],
                      "取樣視窗是截斷的，判準必須自己說出這個邊界（不然下一個人會"
                      "把視窗下緣讀成停擺起點——本輪就有一份文件這樣寫）")

    def test_a_healthy_window_is_not_reported(self) -> None:
        """還原：偶發一兩筆抖動不得出聲（會出聲的哨兵天天喊就會被忽略）。"""
        runs = [self._run("failure", 2)] * 3 + [self._run("success", 300)] * 97
        self.assertEqual(self._probe(runs), [])

    def test_small_sample_and_no_signal_are_not_reported(self) -> None:
        """小樣本的比率是噪音；查不到是無訊號 ≠ 壞訊號。兩者都不得出聲。"""
        self.assertEqual(self._probe([self._run("failure", 2)] * 3), [])
        self.assertEqual(self._probe(None), [])

    def test_a_workflow_without_push_trigger_is_out_of_scope(self) -> None:
        """反向：沒有 `push:` 的 workflow 不進本判準（那是排程軌，另有三道在看）。"""
        runs = [self._run("failure", 2)] * 73 + [self._run("success", 300)] * 27
        self.assertEqual(self._probe(runs, push_yaml=False), [])

    def test_the_finding_reaches_the_consumer(self) -> None:
        """接線鎖：偵測到卻沒接進 `stale_schedule_tracks` ⇒ 使用者一輩子看不到。

        這正是本 repo 反覆吃過的形態（事實查證了、判定沒接上）。`dev_start.py` 只呼叫
        `stale_schedule_tracks`，新判準不接進那個出口就等於不存在。
        """
        import shutil  # noqa: PLC0415
        import tempfile  # noqa: PLC0415
        import time  # noqa: PLC0415
        from unittest import mock  # noqa: PLC0415

        c = self._ci_liveness()
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        (root / ".github" / "workflows").mkdir(parents=True)
        (root / ".github" / "workflows" / "demo.yml").write_text(
            "on:\n  push:\n    branches: [main]\njobs: {}\n",
            encoding="utf-8", newline="\n")
        runs = [self._run("failure", 2)] * 73 + [self._run("success", 300)] * 27
        with mock.patch.object(c, "_push_runs", return_value=runs):
            out = c.stale_schedule_tracks(root, time.monotonic() + 25)
        self.assertTrue(any("never-started" in f for f in out),
                        f"push 閘 never-started 未進入回報清單（實得 {out}）")

    def test_push_trigger_surface_on_the_real_repo_is_not_empty(self) -> None:
        """掃描面下限：現查本 repo 應有數支 push 軌，抓不到即判準恆真。"""
        c = self._ci_liveness()
        found = c.push_triggered_workflows(_REPO_ROOT)
        self.assertGreaterEqual(
            len(found), 4,
            f"只現查到 {len(found)} 支帶 `push:` 的 workflow——判準的掃描面已塌：{found}")
        self.assertIn("root-infra-ci.yml", found,
                      "push 閘主閘門不在掃描面內，本判準等於沒有射程")

    def test_the_ratio_threshold_is_not_silently_disarmed(self) -> None:
        """門檻自證：比率門檻若被調到 1.0（＝永遠不出聲），本條當場紅。

        沒有這一條，「把數字調到判準永遠不成立」是讓紅燈消失的最短路徑，而它在
        diff 上只有一個字元的差別。
        """
        c = self._ci_liveness()
        self.assertLess(c.PUSH_NEVER_STARTED_RATIO, 0.5,
                        "比率門檻 ≥50% 等於只在「一半以上的 run 都沒起來」時才出聲")
        self.assertGreater(c.PUSH_NEVER_STARTED_RATIO, 0.0,
                           "門檻 0 會讓任何一筆抖動都出聲 ⇒ 天天狼來了、然後被忽略")
        self.assertLessEqual(c.NEVER_STARTED_MAX_SECONDS, 10.0,
                             "上界放寬會開始把真紅（實測 15 秒 steps=26）誤判成帳務阻擋")


if __name__ == "__main__":
    unittest.main()
