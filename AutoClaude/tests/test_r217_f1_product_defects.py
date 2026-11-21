"""R217 F1：PRD 逐列 E2E 揭露的三件 AutoClaude 產品缺陷回歸鎖。

意圖（Rule 9）：
  PX46  使用者設的 `playbook.step_timeout_seconds` 必須真的送到 executor（舊 getattr 恆落 600）。
  PX40  PTY 原始串流 log 不得明文落盤金鑰，含被切在兩個 chunk 之間的金鑰；正常輸出不被誤遮。
  空 repo  `git init` 後尚無 commit 的髒工作樹，救援要存下全部內容，不是記成「救援失敗」。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from autoclaude.core.event_bus import EventBus
from autoclaude.core.kernel import PlaybookKernel
from autoclaude.core.ports.executor import ExecutionOutput
from autoclaude.core.wiring import build_kernel
from autoclaude.infra.adapters import dirty_worktree_rescue as R
from autoclaude.infra.adapters.dry_run_executor import DryRunExecutor
from autoclaude.infra.adapters.shell_evaluator import ShellEvaluator
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.utils.config import AppConfig, PlaybookConfig
from autoclaude.utils.logger import RawStreamLogger

# secret-scan-ok: 合成假金鑰
_FAKE_KEY = "sk-ant-api03-" + "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789" * 2


# ───────────────────────── PX46：step_timeout ─────────────────────────
class _TimeoutSpy:
    def __init__(self):
        self.timeouts: list[int] = []

    def execute(self, prompt, *, maintain_context=True, timeout=600, label="", on_event=None):
        self.timeouts.append(timeout)
        return ExecutionOutput(text="OK")


class _Pass:
    def evaluate(self, task, output):
        return None, "", 0


def _pb() -> Playbook:
    return Playbook(
        version="1.0", project="px46",
        global_invariants=GlobalInvariants(max_retries_per_step=1),
        tasks=[PlaybookTask(step_id="S01", name="s", prompt="do")],
    )


def test_px46_kernel_passes_the_injected_step_timeout_to_the_executor():
    spy = _TimeoutSpy()
    PlaybookKernel(spy, _Pass(), bus=EventBus(), step_timeout_seconds=20).run(_pb())
    assert spy.timeouts == [20]


def test_px46_build_kernel_reads_the_user_configured_value_not_the_default():
    cfg = AppConfig()
    cfg.notification.enabled = False
    cfg.playbook.step_timeout_seconds = 37
    spy = _TimeoutSpy()
    kernel = build_kernel(cfg, executor=spy, evaluator=ShellEvaluator(PlaybookConfig()))
    kernel.run(_pb())
    assert spy.timeouts and set(spy.timeouts) == {37}


def test_px46_default_stays_600_when_nothing_is_configured():
    spy = _TimeoutSpy()
    PlaybookKernel(spy, _Pass(), bus=EventBus()).run(_pb())
    assert spy.timeouts == [600]


def test_px46_no_silent_getattr_default_on_global_invariants_remains():
    src = (Path(__file__).resolve().parents[1] / "autoclaude").rglob("*.py")
    needle = 'getattr(playbook.global_invariants, "step_timeout'
    hits = [str(p) for p in src if needle in p.read_text(encoding="utf-8")]
    assert hits == []


def test_px46_dry_run_executor_still_unaffected():
    # 零退化：DryRunExecutor 路徑經 wiring 照常完成
    cfg = AppConfig()
    cfg.notification.enabled = False
    k = build_kernel(cfg, executor=DryRunExecutor(), evaluator=ShellEvaluator(PlaybookConfig()))
    assert k.run(_pb()) is not None


# ───────────────────────── PX40：PTY 原始串流遮蔽 ─────────────────────────
def _logger(tmp_path) -> tuple[RawStreamLogger, Path]:
    p = tmp_path / "playbook_T01.log"
    return RawStreamLogger(p), p


def test_px40_a_whole_line_secret_is_masked_on_disk(tmp_path, monkeypatch):
    monkeypatch.delenv("REDACT_SECRETS_IN_LOGS", raising=False)
    lg, p = _logger(tmp_path)
    lg.write(f"key {_FAKE_KEY} used\n".encode())
    lg.close()
    assert b"AbCdEfGhIjKl" not in p.read_bytes()


def test_px40_a_secret_split_across_chunks_is_masked(tmp_path, monkeypatch):
    monkeypatch.delenv("REDACT_SECRETS_IN_LOGS", raising=False)
    lg, p = _logger(tmp_path)
    raw = f"key {_FAKE_KEY} used\n".encode()
    mid = raw.index(b"AbCdEf") + 3          # 切在金鑰正中央
    lg.write(raw[:mid])
    lg.write(raw[mid:])
    lg.close()
    assert b"AbCdEf" not in p.read_bytes()


def test_px40_unterminated_tail_is_flushed_and_masked_on_close(tmp_path, monkeypatch):
    monkeypatch.delenv("REDACT_SECRETS_IN_LOGS", raising=False)
    lg, p = _logger(tmp_path)
    lg.write(b"password=hunter2xyz")   # 無換行
    lg.close()
    data = p.read_bytes()
    assert b"hunter2xyz" not in data and data      # 有落盤、且已遮


def test_px40_ordinary_output_and_non_utf8_bytes_pass_through_unchanged(tmp_path, monkeypatch):
    monkeypatch.delenv("REDACT_SECRETS_IN_LOGS", raising=False)
    lg, p = _logger(tmp_path)
    body = "build ok 完成 TOKEN_HALT step=S01\n".encode() + b"\xff\xfe raw\n"
    lg.write(body)
    lg.close()
    assert p.read_bytes() == body


def test_px40_switch_off_writes_verbatim(tmp_path, monkeypatch):
    monkeypatch.setenv("REDACT_SECRETS_IN_LOGS", "0")
    lg, p = _logger(tmp_path)
    lg.write(b"password=hunter2xyz\n")
    lg.close()
    assert p.read_bytes() == b"password=hunter2xyz\n"


def test_px40_overlong_unterminated_stream_is_bounded_and_still_masked(tmp_path, monkeypatch):
    monkeypatch.delenv("REDACT_SECRETS_IN_LOGS", raising=False)
    lg, p = _logger(tmp_path)
    for _ in range(40):
        lg.write(b"x" * 1000)                   # 無換行 4 萬位元組
    lg.write(b" api_key=abc123def456 ")
    lg.close()
    data = p.read_bytes()
    assert b"abc123def456" not in data
    assert data.count(b"x") == 40000            # 內容不遺失


# ───────────────────────── 空 repo 髒污救援 ─────────────────────────
def _git(wt: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(wt), *args], check=True, capture_output=True)


def test_empty_repo_without_head_is_rescued_not_failed(tmp_path):
    wt = tmp_path / "wt"
    wt.mkdir()
    _git(wt, "init", "-q", ".")
    (wt / "new.py").write_text("print('x')\n", encoding="utf-8")
    (wt / "staged.txt").write_text("s\n", encoding="utf-8")
    _git(wt, "add", "staged.txt")
    res = R.rescue_dirty_worktree(wt, tmp_path / "ck", agent_id="agent-1")
    assert res.status == R.SAVED, res.reason
    patch = Path(res.patch_path).read_bytes()
    assert b"new.py" in patch and b"staged.txt" in patch


def test_resolve_base_with_head_is_unchanged(tmp_path):
    wt = tmp_path / "wt"
    wt.mkdir()
    _git(wt, "init", "-q", ".")
    _git(wt, "config", "user.email", "t@t")
    _git(wt, "config", "user.name", "t")
    (wt / "a.txt").write_text("a\n", encoding="utf-8")
    _git(wt, "add", "-A")
    _git(wt, "commit", "-qm", "i")
    ref, sha = R.resolve_base(wt)
    assert ref == "HEAD" and 7 <= len(sha) <= 12


def test_not_a_repo_still_fails_loud(tmp_path):
    d = tmp_path / "plain"
    d.mkdir()
    res = None
    try:
        res = R.rescue_dirty_worktree(d, tmp_path / "ck", agent_id="a")
    except Exception:  # noqa: BLE001 — 真錯誤必須照舊拋出或回非 SAVED
        return
    assert res.status != R.SAVED


# ───────────────────────── 全套不得寫進真 checkpoints ─────────────────────────
class TestDefaultCheckpointDirIsHermetic:
    def test_default_checkpoint_dir_is_not_the_repo_relative_directory(self):
        # WHY：預設 "checkpoints" 相對 cwd（AutoClaude/）＝真執行目錄；全套因此每次寫進 7～10 個檔
        assert AppConfig().checkpoint_dir != "checkpoints"
        assert Path(AppConfig().checkpoint_dir).is_absolute()

    def test_a_default_config_run_leaves_the_real_directory_untouched(self):
        real = Path("checkpoints")
        before = {p.name: p.stat().st_mtime_ns for p in real.glob("*")} if real.is_dir() else {}
        cfg = AppConfig()
        Path(cfg.checkpoint_dir, "probe.txt").write_text("x", encoding="utf-8")
        after = {p.name: p.stat().st_mtime_ns for p in real.glob("*")} if real.is_dir() else {}
        assert before == after
