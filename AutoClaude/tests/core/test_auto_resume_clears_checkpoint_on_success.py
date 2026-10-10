"""AutoResumeService 成功收尾清除 checkpoint 測試（DEF-200-510）。

驗證意圖（Rule 9）：checkpoint 是「續跑點」，生命週期有三件事——讀（`_resolve_start`）、寫
（`_persist_halt_checkpoint`）、清。清的這一件在生產路徑上**零呼叫**：`IStateRepository.
clear_checkpoint` 契約寫「步驟完成或 --fresh 時呼叫」，唯一的呼叫者在已無建構點的舊
PlaybookRunner 路徑。後果：
  playbook 因 TOKEN_HALT 存了 checkpoint → 續跑成功跑完 → checkpoint 原封不動 →
  下一次不加 `--fresh` 再跑同一支 playbook，`_resolve_start` 讀到那份舊 checkpoint，從舊斷點
  重跑（SA 實測 completed_step_ids=['T02','T03']——T01 被靜默跳過）。
本檔守兩個方向，缺一不可：
  ① 「成功收尾」必須把用過的 checkpoint 清掉（否則下一輪從舊斷點重跑）；
  ② 「只有成功才清」——HALT／ESCALATION／中斷／演化重載留下的 checkpoint 就是使用者的續跑點，
     修法若寫成「run() 結束就清」會把進度丟掉，比原缺陷更糟。
另兩條安全邊界：清不掉只是降級（結果／rc 不變）；別支 playbook 撞名的 checkpoint 絕不誤刪。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from autoclaude.core.event_bus import EventBus
from autoclaude.core.kernel import PlaybookKernel
from autoclaude.core.kernel_state import KernelResult
from autoclaude.core.ports.executor import (
    ExecutionEvent,
    ExecutionEventKind,
    ExecutionOutput,
)
from autoclaude.core.ports.state_repository import (
    CheckpointCorruptError,
    StateRepositoryError,
)
from autoclaude.core.services.auto_resume import AutoResumeService
from autoclaude.infra.repositories.factory import canonical_playbook_id
from autoclaude.infra.repositories.file_state_repository import FileStateRepository
from autoclaude.infra.repositories.in_memory_state_repository import (
    InMemoryStateRepository,
)
from autoclaude.plugins.token_guard.policy import TokenGuardPlugin
from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint
from autoclaude.utils.config import AppConfig
from tests.helpers.fake_ports import FakeEvaluator

_SVC_LOGGER = "autoclaude.core.services.auto_resume"

_THREE_STEPS = """\
version: "1.0"
project: "clear-on-success"
tasks:
  - {step_id: T01, name: first, prompt: do-first}
  - {step_id: T02, name: second, prompt: do-second}
  - {step_id: T03, name: third, prompt: do-third}
"""


# ── 夾具 ───────────────────────────────────────────────────────────────────────
def _write_playbook(directory: Path, name: str = "three_step.yaml") -> str:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(_THREE_STEPS, encoding="utf-8")
    return str(path)


def _cfg(*, auto_resume: bool = True, delay_minutes: int = 0) -> AppConfig:
    cfg = AppConfig()
    cfg.token_guard.auto_resume = auto_resume
    cfg.token_guard.resume_delay_minutes = delay_minutes  # 0＝立即續跑；本檔不測等待語意
    return cfg


def _pid(path: str, cfg: AppConfig) -> str:
    return canonical_playbook_id(path, mode=cfg.storage.mode)


def _seed(repo, path: str, cfg: AppConfig, *, step_idx: int = 1,
          recorded_path: str | None = None, scheduled: str | None = None) -> str:
    """預先放一份 checkpoint（模擬先前某次 HALT／演化留下的續跑點），回傳它的 playbook_id。"""
    pid = _pid(path, cfg)
    repo.save_checkpoint(pid, PlaybookCheckpoint(
        playbook_path=recorded_path or path, step_idx=step_idx,
        step_id=f"T{step_idx + 1:02d}", total_steps=3,
        completed_step_log=[f"[T{i + 1:02d}] done" for i in range(step_idx)],
        completed_step_ids=[f"T{i + 1:02d}" for i in range(step_idx)],
        scheduled_resume_at=scheduled,
    ))
    return pid


class _TokenScriptExecutor:
    """假 executor：第 N 次 execute 回報腳本指定的 token%（None＝無訊號）；不打真 claude。

    `calls` 記下每次執行的 step_id（Kernel 以 label=step_id 呼叫），＝「實際跑了哪幾步」。
    """

    def __init__(self, pcts: list[float | None]):
        self._pcts = list(pcts)
        self.calls: list[str] = []

    def execute(self, prompt, *, maintain_context=True, timeout=600, label="", on_event=None):
        n = len(self.calls)
        self.calls.append(label)
        pct = self._pcts[n] if n < len(self._pcts) else None
        if on_event is not None and pct is not None:
            on_event(ExecutionEvent(
                kind=ExecutionEventKind.TOKEN_PCT, payload={"pct": pct}, sequence=1,
            ))
        return ExecutionOutput(text="OK")


class _SpyKernel:
    """包住 kernel，記下每次 run() 收到的 start_idx——「這一輪從哪一步開始」就是本缺陷的可觀測面。"""

    def __init__(self, inner):
        self._inner = inner
        self.bus = inner.bus  # service 以 kernel.bus 發 ON_AUTO_RESUME_WAKE；缺它會印 ERROR 噪音
        self.start_idxs: list[int] = []

    def run(self, playbook, start_idx: int = 0) -> KernelResult:
        self.start_idxs.append(start_idx)
        return self._inner.run(playbook, start_idx=start_idx)


def _real_kernel(executor, evaluator=None) -> _SpyKernel:
    bus = EventBus()
    bus.register(TokenGuardPlugin())  # 真 plugin：預設 halt 門檻 90%
    return _SpyKernel(PlaybookKernel(executor, evaluator or FakeEvaluator(), bus=bus))


class _ScriptKernel:
    """依序回傳預先編好的結果（用完重複最後一個）；`on_run` 讓測試在「kernel 執行當下」動手腳。"""

    def __init__(self, *results: KernelResult, on_run=None):
        self._results = list(results)
        self._on_run = on_run
        self.bus = EventBus()  # 演化重載會以 kernel.bus 發 ON_AUTO_RESUME_WAKE；缺它會印 ERROR 噪音
        self.start_idxs: list[int] = []

    def run(self, playbook, start_idx: int = 0) -> KernelResult:
        self.start_idxs.append(start_idx)
        if self._on_run is not None:
            self._on_run(len(self.start_idxs))
        return self._results[min(len(self.start_idxs), len(self._results)) - 1]


def _ok() -> KernelResult:
    return KernelResult.success_(
        completed_steps=3, total_steps=3, step_log=[],
        completed_step_ids=["T01", "T02", "T03"], contributors=[],
    )


# ── ① 缺陷本體：HALT → 續跑成功 → checkpoint 必須不在 → 再跑從 step 0 ─────────────
class TestHaltThenResumeSuccessRetiresTheCheckpoint:
    def test_auto_resume_to_success_leaves_no_checkpoint_and_next_run_starts_at_step_0(
        self, tmp_path,
    ):
        """SA 的完整場景：T02 撞 token halt → 自動續跑成功 → 再跑一次必須從 T01 開始。

        修前：第二次 run 的 start_idx=1、completed_step_ids=['T02','T03']（T01 被靜默跳過）。
        """
        cfg = _cfg(auto_resume=True)
        ckdir = tmp_path / "ck"
        repo = FileStateRepository(str(ckdir))
        playbook = _write_playbook(tmp_path)
        executor = _TokenScriptExecutor([None, 95.0])  # T01 無訊號；T02 首次嘗試 95%（> 90 門檻）
        kernel = _real_kernel(executor)
        svc = AutoResumeService(kernel, cfg, state_repository=repo)

        first = svc.run(playbook)

        assert first.success is True
        assert executor.calls == ["T01", "T02", "T02", "T03"], "T02 被 halt 一次、續跑重做一次"
        assert kernel.start_idxs == [0, 1], "續跑必須從 halt 點接（續跑機制本身沒壞）"
        assert repo.load_checkpoint(_pid(playbook, cfg)) is None, (
            "成功跑完卻留著 HALT 的 checkpoint ⇒ 下一次不加 --fresh 的執行會從舊斷點重跑"
        )
        assert list(ckdir.glob("*.checkpoint.json")) == []

        second = svc.run(playbook)  # 不加 --fresh

        assert second.success is True
        assert kernel.start_idxs == [0, 1, 0], "第二次執行必須從頭開始"
        assert second.completed_step_ids == ["T01", "T02", "T03"], "T01 不得被靜默跳過"
        assert executor.calls[4:] == ["T01", "T02", "T03"]

    def test_a_separate_invocation_that_resumes_to_success_also_retires_it(self, tmp_path):
        """halt 後行程退出（auto_resume 關閉），日後**另一次**啟動續跑到成功——同樣要清。"""
        cfg = _cfg(auto_resume=False)
        repo = FileStateRepository(str(tmp_path / "ck"))
        playbook = _write_playbook(tmp_path)
        pid = _pid(playbook, cfg)
        executor = _TokenScriptExecutor([None, 95.0])

        halted = AutoResumeService(
            _real_kernel(executor), cfg, state_repository=repo).run(playbook)
        assert halted.halted is True and halted.success is False
        assert repo.load_checkpoint(pid).step_idx == 1, "halt 的 checkpoint 是續跑點，必須還在"

        resumed_kernel = _real_kernel(executor)
        resumed = AutoResumeService(resumed_kernel, cfg, state_repository=repo).run(playbook)
        assert resumed.success is True and resumed_kernel.start_idxs == [1]
        assert repo.load_checkpoint(pid) is None

        again_kernel = _real_kernel(executor)
        again = AutoResumeService(again_kernel, cfg, state_repository=repo).run(playbook)
        assert again_kernel.start_idxs == [0]
        assert again.completed_step_ids == ["T01", "T02", "T03"]

    def test_without_a_state_repository_success_is_a_silent_noop(self, tmp_path, caplog):
        """向後相容（dry-run／舊測試）：沒注入 repo ⇒ 沒有東西可清、也不出任何警告。"""
        with caplog.at_level(logging.WARNING, logger=_SVC_LOGGER):
            result = AutoResumeService(
                _ScriptKernel(_ok()), _cfg(), state_repository=None,
            ).run(_write_playbook(tmp_path))
        assert result.success is True
        assert [r for r in caplog.records if r.name == _SVC_LOGGER] == []


# ── ② 只有成功才清：其餘結束形態一律保留續跑點 ────────────────────────────────────
_NOT_A_CLEAN_FINISH = {
    "escalated": lambda: KernelResult.escalated_(
        1, 3, ["[T01] ✓"], ["T01"], reason="max_retries_exhausted: boom"),
    "plain_failure": lambda: KernelResult(
        success=False, completed_steps=1, total_steps=3, reason="step failed"),
    "vetoed_at_pre_run": lambda: KernelResult.vetoed(3, ["veto"]),
    "token_halt": lambda: KernelResult.halted_(
        1, 3, ["[T01] ✓"], ["T01"], halt_step_idx=1, peak_token_pct=93.0),
    "halt_without_idx": lambda: KernelResult(
        success=False, completed_steps=1, total_steps=3, halted=True, reason="halted"),
    "interrupted": lambda: KernelResult(
        success=False, completed_steps=1, total_steps=3, reason="interrupted"),
    # 旗標互斥由工廠方法保證；以下兩個是「success 與 halted／escalated 自相矛盾」的雙重確認：
    # 清除使用者進度不可逆，不能只信單一旗標。
    "success_but_halted": lambda: KernelResult(
        success=True, completed_steps=1, total_steps=3, halted=True, reason="halted"),
    "success_but_escalated": lambda: KernelResult(
        success=True, completed_steps=1, total_steps=3, escalated=True, reason="escalated"),
}


class TestOnlyACleanFinishClears:
    @pytest.mark.parametrize("make_result", list(_NOT_A_CLEAN_FINISH.values()),
                             ids=list(_NOT_A_CLEAN_FINISH))
    def test_anything_but_a_clean_finish_keeps_the_resume_point(self, tmp_path, make_result):
        cfg = _cfg(auto_resume=False)  # halted 時就地返回，不進等待／續跑迴圈
        repo = FileStateRepository(str(tmp_path / "ck"))
        playbook = _write_playbook(tmp_path)
        pid = _seed(repo, playbook, cfg, step_idx=1)
        kernel = _ScriptKernel(make_result())

        AutoResumeService(kernel, cfg, state_repository=repo).run(playbook)

        assert kernel.start_idxs == [1], "先決條件：本輪確實是從那份 checkpoint 續跑"
        ck = repo.load_checkpoint(pid)
        assert ck is not None, "非成功收尾就清掉 checkpoint ⇒ 使用者的續跑點被丟掉"
        assert ck.step_idx == 1

    def test_a_real_escalation_keeps_the_resume_point(self, tmp_path):
        """不只手工組出的 KernelResult：真 Kernel 重試耗盡 ESCALATION，續跑點也要留著。"""
        cfg = _cfg(auto_resume=False)
        repo = FileStateRepository(str(tmp_path / "ck"))
        playbook = _write_playbook(tmp_path)
        pid = _seed(repo, playbook, cfg, step_idx=1)
        kernel = _real_kernel(_TokenScriptExecutor([]), FakeEvaluator(always_pass=False))

        result = AutoResumeService(kernel, cfg, state_repository=repo).run(playbook)

        assert result.escalated is True and result.success is False
        assert kernel.start_idxs == [1]
        assert repo.load_checkpoint(pid).step_idx == 1

    def test_interrupt_during_the_wait_keeps_the_halt_checkpoint(self, tmp_path):
        """中斷（等待途中 is_interrupted）：halt 存下的 checkpoint 是續跑點，不得被清。"""
        cfg = _cfg(auto_resume=True, delay_minutes=30)
        repo = FileStateRepository(str(tmp_path / "ck"))
        playbook = _write_playbook(tmp_path)
        kernel = _real_kernel(_TokenScriptExecutor([None, 95.0]))
        svc = AutoResumeService(
            kernel, cfg, state_repository=repo, is_interrupted=lambda: True)

        with patch("autoclaude.core.services.auto_resume.time.sleep"):  # 保險：絕不真睡 30 分
            result = svc.run(playbook)

        assert result.reason == "interrupted_during_wait" and result.success is False
        assert repo.load_checkpoint(_pid(playbook, cfg)).step_idx == 1

    def test_evolution_reload_keeps_the_checkpoint_until_the_final_success(self, tmp_path):
        """演化重載不是成功：重載當下不清（演化版的續跑點要給下一輪讀）；整條鏈最終成功才全清。"""
        cfg = _cfg()
        repo = FileStateRepository(str(tmp_path / "ck"))
        original = _write_playbook(tmp_path, "pb.yaml")
        evolved = _write_playbook(tmp_path, "pb.mutated.yaml")
        pid_original = _seed(repo, original, cfg, step_idx=1)  # 演化前某次 HALT 留下的續跑點

        def save_evolution_resume_point(call_no: int) -> None:
            if call_no == 1:  # 模擬 EvolutionPlugin 為演化版存「演化後 checkpoint」
                _seed(repo, evolved, cfg, step_idx=1)

        evolved_result = KernelResult(
            success=False, completed_steps=1, total_steps=3, reason="escalated",
            escalated=True, evolved_playbook_path=evolved, evolution_fresh_required=False,
        )
        kernel = _ScriptKernel(evolved_result, _ok(), on_run=save_evolution_resume_point)

        result = AutoResumeService(kernel, cfg, state_repository=repo).run(original)

        assert result.success is True
        assert kernel.start_idxs == [1, 1], "重載當下就清掉演化版 checkpoint ⇒ 第二輪會變成 0"
        assert repo.load_checkpoint(_pid(evolved, cfg)) is None
        assert repo.load_checkpoint(pid_original) is None, (
            "整條鏈成功了，演化前留下的原版 checkpoint 也已過期：留著＝下次跑原版從舊斷點重跑"
        )


# ── ③ 清不掉是降級，不是失敗 ───────────────────────────────────────────────────────
class _ClearFailsRepo(InMemoryStateRepository):
    def __init__(self, exc: Exception):
        super().__init__()
        self._exc = exc
        self.clear_calls = 0

    def clear_checkpoint(self, playbook_id: str) -> None:
        self.clear_calls += 1
        raise self._exc


class TestAFailingClearDegradesToAWarning:
    @pytest.mark.parametrize("exc", [
        StateRepositoryError("shadow PG clear 失敗"),
        PermissionError(13, "Permission denied"),            # Windows 檔案鎖形態
        RuntimeError("DualStateRepository strict 重拋的任意例外"),
    ], ids=["StateRepositoryError", "OSError", "arbitrary"])
    def test_clear_failure_warns_and_leaves_the_result_untouched(self, tmp_path, caplog, exc):
        cfg = _cfg()
        repo = _ClearFailsRepo(exc)
        playbook = _write_playbook(tmp_path)
        pid = _seed(repo, playbook, cfg, step_idx=1)
        ok = _ok()

        with caplog.at_level(logging.WARNING, logger=_SVC_LOGGER):
            result = AutoResumeService(
                _ScriptKernel(ok), cfg, state_repository=repo).run(playbook)

        assert result == ok and result.success is True, "playbook 已成功；善後失敗不得改 rc"
        assert repo.clear_calls == 1, "先決條件：確實嘗試過清除"
        assert any(r.name == _SVC_LOGGER and r.levelno == logging.WARNING
                   and "清除 checkpoint 失敗" in r.getMessage() for r in caplog.records), (
            "降級必須出聲，靜默會讓人以為已經清掉了"
        )
        assert repo.load_checkpoint(pid) is not None, "清不掉＝checkpoint 留著（降級）"

    def test_a_read_failure_at_clear_time_degrades_the_same_way(self, tmp_path, caplog):
        class _ReadFailsAfterRun(InMemoryStateRepository):
            armed = False

            def load_checkpoint(self, playbook_id):
                if self.armed:
                    raise CheckpointCorruptError("收尾時讀不回來")
                return super().load_checkpoint(playbook_id)

        cfg = _cfg()
        repo = _ReadFailsAfterRun()
        playbook = _write_playbook(tmp_path)
        _seed(repo, playbook, cfg, step_idx=1)
        ok = _ok()
        kernel = _ScriptKernel(ok, on_run=lambda _n: setattr(repo, "armed", True))

        with caplog.at_level(logging.WARNING, logger=_SVC_LOGGER):
            result = AutoResumeService(kernel, cfg, state_repository=repo).run(playbook)

        assert result == ok and result.success is True
        assert any("清除 checkpoint 失敗" in r.getMessage() for r in caplog.records)


# ── ④ --fresh 既有行為不變 ───────────────────────────────────────────────────────
class TestFreshIsUnchanged:
    def test_fresh_ignores_the_checkpoint_and_a_failed_fresh_run_leaves_it_alone(self, tmp_path):
        cfg = _cfg(auto_resume=False)
        repo = FileStateRepository(str(tmp_path / "ck"))
        playbook = _write_playbook(tmp_path)
        future = (datetime.now() + timedelta(hours=1)).isoformat(timespec="seconds")
        pid = _seed(repo, playbook, cfg, step_idx=1, scheduled=future)
        kernel = _ScriptKernel(KernelResult.escalated_(
            0, 3, [], [], reason="max_retries_exhausted: x"))

        with patch("autoclaude.core.services.auto_resume.time.sleep") as slept:
            result = AutoResumeService(kernel, cfg, state_repository=repo).run(
                playbook, fresh=True)

        assert result.escalated is True
        assert kernel.start_idxs == [0], "--fresh 必須忽略 checkpoint、從頭開始"
        assert slept.call_count == 0, "--fresh 不得去等舊 checkpoint 的排程時刻"
        ck = repo.load_checkpoint(pid)
        assert ck is not None and ck.step_idx == 1 and ck.scheduled_resume_at == future, (
            "--fresh 只是『不讀』，不是『清掉』；失敗的 fresh run 不得動它"
        )

    def test_a_successful_fresh_run_also_retires_the_stale_checkpoint(self, tmp_path):
        """fresh 成功＝整支 playbook 走完，舊 checkpoint 同樣過期；留著就是同一個缺陷換條路。"""
        cfg = _cfg(auto_resume=False)
        repo = FileStateRepository(str(tmp_path / "ck"))
        playbook = _write_playbook(tmp_path)
        pid = _seed(repo, playbook, cfg, step_idx=1)
        kernel = _ScriptKernel(_ok())

        result = AutoResumeService(kernel, cfg, state_repository=repo).run(playbook, fresh=True)

        assert result.success is True and kernel.start_idxs == [0]
        assert repo.load_checkpoint(pid) is None


# ── ⑤ 別支 playbook 撞名的 checkpoint 絕不誤刪 ──────────────────────────────────────
class TestAnotherPlaybooksCheckpointIsNeverDeleted:
    def test_same_stem_different_directory(self, tmp_path):
        """R69 的對偶面：`a/same.yaml` 與 `b/same.yaml` 共用 playbook_id。本次不採信別支的
        checkpoint（從頭跑），而成功收尾更不能順手把別支的續跑點刪掉。"""
        cfg = _cfg(auto_resume=False)
        repo = FileStateRepository(str(tmp_path / "ck"))
        mine = _write_playbook(tmp_path / "a", "same.yaml")
        theirs = _write_playbook(tmp_path / "b", "same.yaml")
        pid = _seed(repo, mine, cfg, step_idx=2, recorded_path=theirs)
        assert _pid(mine, cfg) == _pid(theirs, cfg), "先決條件：兩者確實撞 id"
        kernel = _ScriptKernel(_ok())

        result = AutoResumeService(kernel, cfg, state_repository=repo).run(mine)

        assert result.success is True
        assert kernel.start_idxs == [0], "別支的 checkpoint 不採信、從頭跑（R69 既有行為）"
        ck = repo.load_checkpoint(pid)
        assert ck is not None, "別支 playbook 的續跑點被本次成功收尾誤刪"
        assert (ck.step_idx, ck.playbook_path) == (2, theirs)
