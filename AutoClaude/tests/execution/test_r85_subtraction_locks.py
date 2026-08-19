"""R85（減法輪）回歸鎖：AC-(b) 啟動阻塞、GoalSynthesis fail-open 可觀測性、_notify_enabled。

本檔的每一支測試都在鎖「**為什麼**這個行為重要」，不是鎖「它現在長什麼樣」——
一支不會因為業務語意改變而轉紅的測試是壞測試（12-Rule Rule 9）。
"""
from __future__ import annotations

import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from autoclaude import main as main_mod
from autoclaude.execution.playbook_runner import PlaybookRunner
from autoclaude.infra.adapters.dry_run_executor import DryRunExecutor
from autoclaude.plugins.goal_synthesis_plugin import GoalSynthesisPlugin
from autoclaude.utils.config import AppConfig

_REPO_PB = Path(__file__).resolve().parents[2] / "scripts" / "example_playbook.yaml"


# 🔴 R96：凡「在 tempdir 裡跑 `main()`、跑完就刪那個 tempdir」的測試，都必須先把 log 的
# 檔案握把放掉。病徵（本輪 Windows 側首跑實測）：`main()` 建的 `RotatingFileHandler` 一直
# 握著 `<tmp>\logs\autoclaude.log`，而 Windows **不允許刪除仍被開啟的檔** ⇒ tempdir 清理拋
# `PermissionError: [WinError 32] 程序無法存取檔案，因為檔案正由另一個程序使用`，於是測試在
# **本體已經通過之後**才紅（同一段 captured stdout 裡就有 `KernelResult(success=True,
# completed_steps=4, ...)`）。POSIX 允許 unlink 開啟中的檔 ⇒ mac 上結構上重現不了，正是根
# CLAUDE.md 鐵律三「Windows 檔案鎖：會改動目錄項的原語」那一列的形態。
# 🔴 刻意**不用** `TemporaryDirectory(ignore_cleanup_errors=True)`：那會把所有清理失敗一起
# 吞掉（包含真正的資源洩漏），而這裡要治的就是「handler 沒被關」這個真實洩漏——形態是**殘留
# 一個指向已被刪除的 tempdir 的握把**，不是累積：`setup_logger` 開頭即
# `if root.handlers: return root`（`autoclaude/utils/logger.py:39-40` 實查）⇒ 整個行程只會掛
# 上那**一組**（`RotatingFileHandler` ＋ console 各一），多跑幾支 playbook 也不會變多；洩漏的
# 是那組裡的檔案 handler 仍握著它**第一次**落腳的那個 tempdir 底下的
# `logs/autoclaude.log`，而那個 tempdir 正要被刪掉。只動本專案自己的 logger（handler 掛在
# `getLogger("autoclaude")`），不碰 pytest 自己的 handler。
# 🔴 **一個家**：本檔有兩個站點會在 tempdir 內跑 `main()`，而第二個站點先前是靠
# 「handler 已存在 ⇒ `setup_logger` 不重建」僥倖躲過的——第一個站點修好、handler 被正確卸下
# 之後，第二個站點的 `main()` 才會真的建出指向它自己 tempdir 的 handler 並當場翻紅（本輪實測
# 就是這個順序）。所以這件事只准有一份實作，不得在兩處各寫一次迴圈。
# 🔴 誠實劃界（R96 四方複審 QA 的覆蓋面指摘；本輪**刻意不修**）：本修法整個落在**測試側**。
# 生產側那個行為——第二次 `setup_logger(log_dir=<另一個目錄>)` 靜默沿用前一次留下的檔案握把、
# **不**為新的 `log_dir` 重建 handler——**一個鎖都沒有**；而測試側修好之後，原本唯一會讓它
# 現形的訊號（Windows 清理 tempdir 時的 WinError 32）就消失了。不在此補生產側的鎖，是因為
# 那是**行為改動**、本輪已無複審可以接住它；承接載體＝缺陷帳本 `DEF-200-154`（該列目前只
# 記到測試側，生產側這一半需另立）。
def _release_autoclaude_log_handles() -> None:
    """關閉並卸下 `autoclaude` logger 的 handler（Windows 檔案鎖；理由見上方註解）。"""
    log = logging.getLogger("autoclaude")
    for handler in list(log.handlers):
        handler.close()
        log.removeHandler(handler)


# ──────────────────────────────────────────────────────────────────────────
# 1. _notify_enabled — R85 前**零回歸鎖**（P3 交下時判為「約 15 個呼叫點」，
#    本輪實測駁回：`self._notify(` 在 playbook_runner.py 只有 2 個站點，
#    另 2 個在 tool_invocation_adapter.py 且走的是**另一個**旗標
#    `_notification_enabled` ⇒ 本鎖射程只涵蓋 playbook_runner 那 2 個）。
# ──────────────────────────────────────────────────────────────────────────
class TestNotifyEnabledIsHonoured:
    """`config.notification.enabled` 必須真的決定「桌面通知送不送」。

    為什麼這件事值得一支鎖：這個旗標的兩個失效方向**都是靜默的**——
      · 恆開：使用者關掉通知卻仍被 ESCALATION 洗版，而 log 一切正常；
      · 恆關：ESCALATION 從此無人知曉，而 playbook 看起來只是「跑得比較久」。
    兩種都不會有任何測試轉紅，所以必須由這支鎖把「旗標→行為」釘死。
    """

    def _runner(self, enabled: bool) -> PlaybookRunner:
        cfg = AppConfig()
        cfg.notification.enabled = enabled
        return PlaybookRunner(cfg, MagicMock(), MagicMock(triggered=False), dry_run=True)

    @pytest.mark.parametrize("enabled", [True, False])
    def test_flag_is_forwarded_to_the_notifier(self, enabled: bool) -> None:
        runner = self._runner(enabled)
        with patch("autoclaude.execution.playbook_runner.notify") as spy:
            runner._notify("標題", "內容")
        spy.assert_called_once()
        assert spy.call_args.kwargs["enabled"] is enabled, (
            "notification.enabled 沒有被轉發給 notifier ⇒ 旗標變成裝飾品"
        )

    def test_the_two_escalation_sites_go_through_the_gated_helper(self) -> None:
        """兩個 ESCALATION 站點必須走 `self._notify`，不可直接呼叫 notify()。

        繞過 helper 就等於繞過旗標——而那正是「恆開」那個失效方向的入口。
        """
        src = Path(main_mod.__file__).with_name("execution") / "playbook_runner.py"
        text = src.read_text(encoding="utf-8")
        assert text.count("self._notify(") == 2, "站點數變了，請連同本鎖的射程一起重新判斷"
        # 「繞過」的定義：直接呼叫 notify() 卻**沒有**把旗標帶進去。
        # `_notify` 自己那一行 `notify(title, message, enabled=self._notify_enabled)`
        # 正是閘門本體，不是繞過——第一版判準把它也算進去，是假陽性（本輪自證修正）。
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("notify(") and "enabled=self._notify_enabled" not in stripped:
                pytest.fail(f"發現繞過 _notify 閘的直接呼叫：{stripped}")


# ──────────────────────────────────────────────────────────────────────────
# 2. GoalSynthesis：Brain 諮詢失敗**不得**與「目標已達成」長成同一個表徵
# ──────────────────────────────────────────────────────────────────────────
class TestGoalSynthesisFailureIsDistinguishableFromSuccess:
    """R85：舊碼在 except 裡逐字「視為達成」且只留一行 WARNING。

    失效表徵與成功完全相同＝本 repo 最忌諱的形態。本鎖要求：無論 fail_closed
    取哪個值，「其實沒驗證成功」這件事都必須是**可查的事實**，而不是只存在於 log。
    """

    def _plugin(self, *, fail_closed: bool) -> GoalSynthesisPlugin:
        client = MagicMock()
        client.validate_goal_achievement.side_effect = RuntimeError("API 失敗")
        return GoalSynthesisPlugin(minimax_client=client, fail_closed=fail_closed)

    def test_failure_is_recorded_even_when_it_does_not_block(self) -> None:
        plugin = self._plugin(fail_closed=False)
        assert plugin.validation_failed is False, "初始狀態必須是「沒失敗過」"
        result = plugin.validate_global_goal_achievement(
            MagicMock(project="P", global_goal="G"), ["T01 ✓"], "G",
        )
        # 預設仍 fail-open（不阻斷）——但失敗這件事必須留下痕跡
        assert result is None
        assert plugin.validation_failed is True, (
            "諮詢失敗卻沒有留下任何可查痕跡 ⇒ 又退回「失效與成功同表徵」"
        )

    def test_fail_closed_refuses_to_silently_claim_achievement(self) -> None:
        plugin = self._plugin(fail_closed=True)
        result = plugin.validate_global_goal_achievement(
            MagicMock(project="P", global_goal="G"), ["T01 ✓"], "G",
        )
        assert result is not None, "fail_closed=True 時不得回 None（那就是視為達成）"
        assert "無法向 Brain 確認" in result[0]
        assert plugin.validation_failed is True

    def test_a_healthy_client_does_not_set_the_failure_flag(self) -> None:
        """鑑別力自證：旗標不能是恆真的（恆真等於沒有鑑別力）。"""
        client = MagicMock()
        client.validate_goal_achievement.return_value = MagicMock(is_achieved=True)
        plugin = GoalSynthesisPlugin(minimax_client=client)
        plugin.validate_global_goal_achievement(
            MagicMock(project="P", global_goal="G"), ["T01 ✓"], "G",
        )
        assert plugin.validation_failed is False


# ──────────────────────────────────────────────────────────────────────────
# 3. AC-(b)：example_playbook.yaml 的 global_goal 與 tasks 真的被跑起來
# ──────────────────────────────────────────────────────────────────────────
def _run_example_playbook(tmp: Path, *, storage_yaml: str = "") -> tuple[int, list[str]]:
    """在隔離 cwd 內以 production main() 跑 example_playbook，回 (rc, 執行過的 step)。

    只替換「真的會外呼 Claude CLI」那一個邊界（build_executor）；load_config →
    MinimaxClient 閘 → build_kernel → AutoResumeService.run 全部走原路。
    T03 的 evaluator_command 是**真的** pytest，故備妥它要跑的檔讓它真的執行。
    """
    spec = yaml.safe_load(_REPO_PB.read_text(encoding="utf-8"))
    outputs = {
        t["step_id"]: DryRunExecutor.keyword_from_regex(t.get("expected_output_regex"))
        for t in spec["tasks"]
    }
    executed: list[str] = []

    class Tracing(DryRunExecutor):
        def execute(self, prompt, **kw):
            executed.append(kw.get("label", "?"))
            return super().execute(prompt, **kw)

    ws = tmp / "scripts" / "example_workspace" / "tests"
    ws.mkdir(parents=True)
    (ws / "test_auth.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    shutil.copy(_REPO_PB, tmp / "scripts" / "example_playbook.yaml")
    cfgp = tmp / "config.yaml"
    cfgp.write_text(
        f"log_dir: {tmp}/logs\ncheckpoint_dir: {tmp}/ckpt\n{storage_yaml}",
        encoding="utf-8",
    )
    origin = Path.cwd()
    os.chdir(tmp)
    try:
        argv = ["autoclaude", "scripts/example_playbook.yaml", "--config", str(cfgp), "--fresh"]
        with patch.object(main_mod, "build_executor", lambda *a, **k: Tracing(outputs)), \
             patch.object(sys, "argv", argv):
            rc = main_mod.main()
    finally:
        os.chdir(origin)
        _release_autoclaude_log_handles()   # Windows 檔案鎖，理由見該函式上方註解
    return rc, executed


class TestExamplePlaybookRunsWithoutAMinimaxAccount:
    """AC-(b)：沒有 Minimax 帳號的人必須能跑完整支 playbook。

    R85 前的實況（本輪實測）：`main.py` 無條件建 MinimaxClient，空金鑰時
    `MinimaxClient.__init__` 拋 MinimaxError、被 main() 接住後 **return 1**
    ⇒ 不是 crash，是**一步都跑不了**地乾淨退出，且預設組態
    `enable_kernel_brain=False` 根本不需要 Brain。這是連續三輪零交付的直接原因。
    """

    def test_all_four_tasks_execute_and_the_run_succeeds(self, monkeypatch) -> None:
        monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
        with tempfile.TemporaryDirectory() as td:
            rc, executed = _run_example_playbook(Path(td))
        assert rc == 0, "無 MINIMAX_API_KEY 時 playbook 必須仍能跑完（AC-(b) 的本體）"
        assert executed == ["T01", "T02", "T03", "T04"], (
            f"四個 task 必須都真的被執行，實際：{executed}"
        )

    def test_the_playbook_still_carries_a_global_goal(self) -> None:
        """AC-(b) 逐字要求 global_goal 與 tasks 都被「應用起來」。"""
        spec = yaml.safe_load(_REPO_PB.read_text(encoding="utf-8"))
        assert spec.get("global_goal", "").strip(), "example_playbook 必須帶 global_goal"
        assert [t["step_id"] for t in spec["tasks"]] == ["T01", "T02", "T03", "T04"]

    def test_an_explicitly_requested_brain_still_fails_closed(self, monkeypatch) -> None:
        """缺金鑰**不得**靜默降級成「Brain 沒開」——顯式要 Brain 就必須拿到 Brain。

        這支鎖守的是修法的邊界：把啟動閘拿掉時很容易順手把 fail-closed 也拿掉。
        """
        monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "scripts").mkdir()
            shutil.copy(_REPO_PB, tmp / "scripts" / "example_playbook.yaml")
            cfgp = tmp / "config.yaml"
            cfgp.write_text(
                f"log_dir: {tmp}/logs\ncheckpoint_dir: {tmp}/ckpt\n"
                "minimax:\n  enable_kernel_brain: true\n",
                encoding="utf-8",
            )
            origin = Path.cwd()
            os.chdir(tmp)
            try:
                argv = ["autoclaude", "scripts/example_playbook.yaml",
                        "--config", str(cfgp), "--fresh"]
                with patch.object(sys, "argv", argv):
                    rc = main_mod.main()
            finally:
                os.chdir(origin)
                _release_autoclaude_log_handles()   # 同上：Windows 檔案鎖，見該函式註解
        assert rc == 1, "enable_kernel_brain=True 但無金鑰時必須停機，不可靜默降級"


@pytest.mark.pg_real
class TestExamplePlaybookAgainstPostgres:
    """AC-(b) 的「有使用 PostgreSQL DB」那一半：同一支 playbook 走 PG 影子寫入。

    `storage.mode: both` ＝ File 主寫 + PG 影子，是 PG 上線灰度的正式姿態；
    選它而非 db_only，是因為它同時證明「PG 真的被寫到」與「PG 掛掉不會拖垮主線」。
    """

    def test_run_succeeds_with_pg_dual_write(self, monkeypatch, real_pg_dsn) -> None:
        monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
        # TLS 強制：本機 CI 容器為明文連線，需顯式放行（否則 factory 直接拒絕建 PG backend）
        monkeypatch.setenv("AUTOCLAUDE_ALLOW_INSECURE_DB", "1")
        # `real_pg_dsn` 只當**啟用閘**（它會把 `+asyncpg` 去掉以配合 contract test）；
        # 這裡要的是 factory 認得的 asyncpg 形態，故仍讀原始 env。
        dsn = os.environ.get("AUTOCLAUDE_TEST_PG_DSN") or os.environ["AUTOCLAUDE_DB_DSN"]
        storage = f"storage:\n  mode: both\n  db_dsn: {dsn}\n"
        with tempfile.TemporaryDirectory() as td:
            rc, executed = _run_example_playbook(Path(td), storage_yaml=storage)
        assert rc == 0, "storage.mode=both 下無金鑰仍須跑完"
        assert executed == ["T01", "T02", "T03", "T04"]
