"""PRD §11.3「凍結與喚醒」計時驗收：注入 95% 訊號後整段凍結 ≤ 5 秒；寫入中被殺仍是上一份有效版本。

PRD §11.3 原文兩條（📎 補件）：
  · 人工注入 95% 訊號，斷言 **5 秒內**完成 checkpoint 與 state.json 的原子寫入；
  · 在 state.json 寫入過程中 `kill -9` → 重啟後能以 checksum 偵測損壞並回退到上一有效版本。

既有的 `test_sigint_checkpoint.py` 只量**寫入那一步**（SLA 2 秒、在 signal handler 內）；
本檔量的是**整段**：從「95% 的 token 訊號被注入」起，經 kernel 的 halt 判定、
AutoResumeService 的 checkpoint 持久化（原子寫入＋fsync＋保留版本輪替＋排程恢復時刻的第二次
寫入），到「新行程視角讀得回一份通過 checksum 的 checkpoint」為止。真的 kernel、真的
TokenGuardPlugin、真的後端；只有 executor 是 dry-run 替身（不啟動 claude）、額度快取是空替身
（halt 的成因只准是 token%，不准被本機真實額度蓋過）。

實測秒數用 `print` 印出（`pytest -s` 可見）並寫進 junit 的 `record_property`。

誠實劃界：
  · PRD 原文「各 worktree `git status` 皆 clean」子句以逐 worktree commit 為前提，本實作無人窗口
    不 commit（救援是 patch、不動工作樹），不在本檔射程；
  · `os._exit` 是 `kill -9` 的跨平台等價物（立即終止、不跑 finally／atexit、不 flush）；
    它證明的是「行程在換名前死掉，主檔不變」，不是對檔案系統斷電行為的證明。
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from autoclaude.core import wiring
from autoclaude.core.ports.executor import ExecutionEvent, ExecutionEventKind
from autoclaude.core.ports.observability import NullObservability
from autoclaude.core.services.auto_resume import AutoResumeService
from autoclaude.infra.adapters.dry_run_executor import DryRunExecutor
from autoclaude.infra.adapters.shell_evaluator import ShellEvaluator
from autoclaude.infra.repositories.factory import canonical_playbook_id
from autoclaude.infra.repositories.file_state_repository import FileStateRepository
from autoclaude.infra.repositories.in_memory_state_repository import InMemoryStateRepository
from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint
from autoclaude.utils.config import AppConfig, PlaybookConfig

#: PRD §11.3：注入 95% 訊號後，凍結必須在此秒數內完成。
_SLA_SECONDS = 5.0

_PLAYBOOK = str(Path(__file__).parent.parent / "equivalence" / "fixtures" / "01_simple_2_step.yaml")


class _NoQuotaCache:
    """額度快取的空替身：halt 的成因只准是 token%（真實額度快取會讓本機狀態滲進測試）。"""

    def read(self):
        return None

    def read_worst_pct(self):
        return None


class _Pct95Executor(DryRunExecutor):
    """DryRunExecutor ＋ 在第一次執行注入 95% 的 token 訊號（PRD §11.3「人工注入 95% 訊號」）。

    `injected_at` 記下訊號被注入的那一刻——計時的起點。
    """

    def __init__(self):
        super().__init__()
        self.injected_at: float | None = None

    def execute(self, prompt, *, maintain_context=True, timeout=600, label="", on_event=None):
        if on_event is not None and self.injected_at is None:
            self.injected_at = time.perf_counter()
            on_event(ExecutionEvent(kind=ExecutionEventKind.TOKEN_PCT,
                                    payload={"pct": 95.0}, sequence=1))
        return super().execute(prompt, maintain_context=maintain_context, timeout=timeout,
                               label=label, on_event=on_event)


def _service(tmp_path: Path, monkeypatch, repo, executor) -> AutoResumeService:
    monkeypatch.setattr(wiring, "build_quota_meter", lambda *a, **k: _NoQuotaCache())
    cfg = AppConfig(checkpoint_dir=str(tmp_path / "ckpt"))
    cfg.notification.enabled = False          # 測試不產生桌面通知（背景執行緒會汙染計時）
    cfg.token_guard.auto_resume = False       # 存完 checkpoint 即返回，不進等待迴圈
    kernel = wiring.build_kernel(cfg, executor=executor,
                                 evaluator=ShellEvaluator(PlaybookConfig()),
                                 state_repository=repo, observability=NullObservability())
    return AutoResumeService(kernel, cfg, state_repository=repo)


def _playbook_id() -> str:
    return canonical_playbook_id(_PLAYBOOK, mode=AppConfig().storage.mode)


def _previous_valid(step_log_marker: str = "previous-valid") -> PlaybookCheckpoint:
    return PlaybookCheckpoint(playbook_path=_PLAYBOOK, step_idx=0, step_id="T01", total_steps=2,
                              completed_step_log=[step_log_marker], peak_token_pct=61.0)


# ══════════════════════════════════════════════════════════════════════════════
# 整段凍結計時
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("backend", ["file", "in_memory"])
def test_the_whole_freeze_after_a_95_percent_signal_is_durable_within_five_seconds(
        tmp_path, monkeypatch, record_property, backend):
    repo = (FileStateRepository(str(tmp_path / "ckpt")) if backend == "file"
            else InMemoryStateRepository())
    executor = _Pct95Executor()
    service = _service(tmp_path, monkeypatch, repo, executor)

    result = service.run(_PLAYBOOK, fresh=True)
    finished_at = time.perf_counter()

    # 先證明量到的真是「凍結」：halt 是 token 訊號造成的，而且進度真的落了盤。
    assert executor.injected_at is not None, "95% 訊號沒被注入 ⇒ 本次量測無效"
    elapsed = finished_at - executor.injected_at               # 訊號注入 → run() 返回
    assert result.halted is True and result.peak_token_pct == pytest.approx(95.0)
    saved = repo.load_latest_by_playbook(_playbook_id())
    assert saved is not None, "凍結完成卻沒有 checkpoint：耗時短的原因是根本沒寫"
    assert (saved.step_idx, saved.step_id, saved.peak_token_pct) == (0, "T01", 95.0)
    assert saved.scheduled_resume_at, "state 缺恢復時刻 ⇒ 喚醒端沒有東西可等"

    print(f"\n[PRD §11.3] backend={backend} 95% 訊號 → halt 判定 → checkpoint 原子寫入 → "
          f"state 落盤：{elapsed:.4f}s（門檻 ≤ {_SLA_SECONDS:.0f}s）")
    record_property("freeze_elapsed_seconds", f"{elapsed:.4f}")
    assert elapsed <= _SLA_SECONDS, (
        f"整段凍結耗時 {elapsed:.3f}s，超過 PRD §11.3 的 {_SLA_SECONDS}s")


def test_the_durable_state_is_readable_by_a_fresh_process_view_with_the_checksum_verified(
        tmp_path, monkeypatch):
    """「落盤」不能只是「呼叫回來了」：以新的 repository 實例（續跑時新行程的視角）讀回，
    `_read_verified` 會驗 checksum——內容被截斷或竄改會拋 CheckpointCorruptError 而非回傳。"""
    repo = FileStateRepository(str(tmp_path / "ckpt"))
    service = _service(tmp_path, monkeypatch, repo, _Pct95Executor())
    service.run(_PLAYBOOK, fresh=True)

    fresh_view = FileStateRepository(str(tmp_path / "ckpt"))
    restored = fresh_view.load_latest_by_playbook(_playbook_id())
    assert restored is not None and restored.step_idx == 0 and restored.peak_token_pct == 95.0
    assert restored.checksum_sha256, "落盤的檔沒有 checksum ⇒ 後續的損壞偵測沒有依據"
    assert list((tmp_path / "ckpt").glob("*.tmp")) == [], "凍結完成後不得留 .tmp 殘檔"


def test_the_stopwatch_really_wraps_the_freeze(tmp_path, monkeypatch):
    """本檔的自證：計時窗口真的包住持久化。包一層故意慢的 repository，量到的秒數必須不小於
    那段已知延遲——計時器若不再包住寫入，上面的 ≤5s 斷言就退化成裝飾。"""
    delay = 0.05
    inner = FileStateRepository(str(tmp_path / "ckpt"))

    class _Slow:
        def __getattr__(self, name):
            return getattr(inner, name)

        def save_checkpoint(self, playbook_id, checkpoint):
            time.sleep(delay)
            inner.save_checkpoint(playbook_id, checkpoint)

    executor = _Pct95Executor()
    _service(tmp_path, monkeypatch, _Slow(), executor).run(_PLAYBOOK, fresh=True)
    assert time.perf_counter() - executor.injected_at >= delay


# ══════════════════════════════════════════════════════════════════════════════
# 寫入中被殺 ⇒ 仍是上一份有效版本
# ══════════════════════════════════════════════════════════════════════════════
class _Killed(BaseException):
    """模擬行程在寫入中途死亡。刻意是 BaseException：`except Exception` 的清理分支不會跑，
    與真正的 kill 一樣會在原地留下 .tmp 殘檔。"""


def test_a_kill_in_the_middle_of_the_freeze_write_leaves_the_previous_valid_checkpoint(
        tmp_path, monkeypatch):
    """完整凍結路徑上、`os.fsync`（內容已寫進 tmp、尚未換名）的當下被殺：主檔一個位元組都沒動，
    「重啟」後讀回的是上一份有效的 checkpoint，不是 None（會靜默從頭重跑）、也不是 CORRUPT。"""
    ckpt = tmp_path / "ckpt"
    FileStateRepository(str(ckpt)).save_checkpoint(_playbook_id(), _previous_valid())
    main_file = ckpt / f"{_playbook_id()}.checkpoint.json"
    before = main_file.read_bytes()

    service = _service(tmp_path, monkeypatch, FileStateRepository(str(ckpt)), _Pct95Executor())

    def _die(fd):
        raise _Killed("kill -9 in the middle of the state write")
    monkeypatch.setattr("os.fsync", _die)
    with pytest.raises(_Killed):
        service.run(_PLAYBOOK, fresh=True)
    monkeypatch.undo()

    assert main_file.read_bytes() == before, "主檔在寫入中途被改動 ⇒ 不是原子寫入"
    assert list(ckpt.glob("*.tmp")), "前提：被殺的寫入確實留下了 .tmp 殘檔（本測試要證明殘檔無害）"
    restarted = FileStateRepository(str(ckpt)).load_latest_by_playbook(_playbook_id())
    assert restarted is not None, "被殺之後 checkpoint 看起來不存在 ⇒ 呼叫端會靜默從 step 0 重跑"
    assert restarted.completed_step_log == ["previous-valid"] and restarted.peak_token_pct == 61.0


_CHILD = textwrap.dedent('''
    import os, sys
    from autoclaude.infra.repositories.file_state_repository import FileStateRepository
    from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint
    from pathlib import Path

    point = sys.argv[2]
    def die(*a, **k):
        os._exit(137)          # 等價 kill -9：不跑 finally／atexit、不 flush
    if point == "json_dump_half":
        import json
        def half(obj, f, **kw):
            f.write('{"playbook_path": "x", "step_idx": 9, "tr')
            f.flush()
            os._exit(137)
        json.dump = half
    elif point == "fsync":
        os.fsync = die
    elif point == "replace":
        Path.replace = die
    repo = FileStateRepository(sys.argv[1])
    repo.save_checkpoint("pb", PlaybookCheckpoint(
        playbook_path="pb.yaml", step_idx=9, step_id="T10", total_steps=10, peak_token_pct=95.0))
    sys.exit(0)             # 走到這裡代表沒被殺：測試會因 returncode != 137 而紅
''')


@pytest.mark.parametrize("kill_point", ["json_dump_half", "fsync", "replace"])
def test_a_real_process_death_at_each_write_stage_leaves_the_previous_valid_checkpoint(
        tmp_path, kill_point):
    """真的子行程、真的在寫入的三個階段（JSON 寫到一半／fsync／換名）立即死亡。
    不論死在哪一格，重啟後讀回的都是上一份有效版本（step_idx=2），而不是 None 或 CORRUPT。"""
    ckpt = tmp_path / "ckpt"
    FileStateRepository(str(ckpt)).save_checkpoint("pb", PlaybookCheckpoint(
        playbook_path="pb.yaml", step_idx=2, step_id="T03", total_steps=10, peak_token_pct=61.0))

    proc = subprocess.run([sys.executable, "-c", _CHILD, str(ckpt), kill_point],
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=120, check=False)
    assert proc.returncode == 137, (proc.returncode, proc.stderr[-500:])

    restarted = FileStateRepository(str(ckpt)).load_latest_by_playbook("pb")
    assert restarted is not None
    assert (restarted.step_idx, restarted.step_id, restarted.peak_token_pct) == (2, "T03", 61.0)


def test_a_torn_main_file_is_detected_and_falls_back_to_the_previous_valid_version(tmp_path):
    """PRD §11.3 的另一半原文：寫入過程中被殺、主檔本身壞了（檔案系統不保證換名原子時的殘骸）
    ⇒ 重啟後以 checksum 偵測損壞並回退到上一有效版本。這是主檔被撕裂時的最後防線。"""
    repo = FileStateRepository(str(tmp_path / "ckpt"))
    repo.save_checkpoint("pb", PlaybookCheckpoint(
        playbook_path="pb.yaml", step_idx=2, step_id="T03", total_steps=10))
    repo.save_checkpoint("pb", PlaybookCheckpoint(
        playbook_path="pb.yaml", step_idx=7, step_id="T08", total_steps=10))
    main_file = tmp_path / "ckpt" / "pb.checkpoint.json"
    raw = main_file.read_text(encoding="utf-8")
    main_file.write_text(raw[: len(raw) // 2], encoding="utf-8")           # 撕裂

    restarted = FileStateRepository(str(tmp_path / "ckpt")).load_latest_by_playbook("pb")
    assert restarted is not None and restarted.step_idx == 2, "沒有回退到上一有效版本"
