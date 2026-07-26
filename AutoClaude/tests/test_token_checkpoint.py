"""
Token Guard 與 Checkpoint 機制的單元測試。

涵蓋：
  - extract_context_pct：多種輸出格式的百分比解析
  - TokenUsageLogger：寫入與讀回
  - CheckpointManager：save / load / clear / schedule_resume / seconds_until_resume
  - PlaybookRunner：compact 觸發、halt 觸發、checkpoint 儲存、checkpoint 恢復
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from autoclaude.execution.failure_tracker import FailureTracker
from autoclaude.execution.playbook_runner import PlaybookRunner
from autoclaude.utils.checkpoint_manager import CheckpointManager, PlaybookCheckpoint
from autoclaude.utils.config import AppConfig, TokenGuardConfig
from autoclaude.utils.token_tracker import TokenUsageLogger, build_patterns, extract_context_pct

# ══════════════════════════════════════════════
# extract_context_pct
# ══════════════════════════════════════════════

class TestExtractContextPct:
    def test_percentage_context_used(self):
        assert extract_context_pct("Context 92% used") == 92.0

    def test_percentage_token_full(self):
        assert extract_context_pct("token 85% full") == 85.0

    def test_n_over_m_tokens(self):
        pct = extract_context_pct("190000 / 200000 tokens")
        assert pct is not None
        assert abs(pct - 95.0) < 0.01

    def test_autoclaude_marker(self):
        assert extract_context_pct("[CONTEXT_USAGE: 88.5%]") == 88.5

    def test_no_match_returns_none(self):
        assert extract_context_pct("Compiling source files...") is None
        assert extract_context_pct("") is None

    def test_takes_highest_value_in_line(self):
        # 同一行有兩個匹配，取最高值
        result = extract_context_pct("token 60% used, context 75% full")
        assert result == 75.0

    def test_custom_patterns(self):
        patterns = build_patterns([r"usage=(\d+)%"])
        assert extract_context_pct("usage=55%", patterns) == 55.0
        assert extract_context_pct("token 90%", patterns) is None

    def test_zero_division_safe(self):
        # 分母為 0 → 安全地回傳 None
        assert extract_context_pct("0 / 0 tokens") is None

    def test_decimal_percentage(self):
        assert extract_context_pct("context 89.7% used") == 89.7

    def test_n_over_m_exact(self):
        pct = extract_context_pct("100000/200000 tokens")
        assert pct is not None
        assert abs(pct - 50.0) < 0.01


# ══════════════════════════════════════════════
# TokenUsageLogger
# ══════════════════════════════════════════════

class TestTokenUsageLogger:
    def test_write_and_read(self, tmp_path):
        logger = TokenUsageLogger(str(tmp_path))
        logger.record("MyProject", "T01", 72.5, "continue", "success")
        logger.record("MyProject", "T02", 88.0, "compact", "in_progress")

        entries = logger.read_all()
        assert len(entries) == 2
        assert entries[0]["step_id"] == "T01"
        assert entries[0]["token_pct"] == 72.5
        assert entries[0]["action"] == "continue"
        assert entries[1]["action"] == "compact"

    def test_read_empty_when_no_file(self, tmp_path):
        logger = TokenUsageLogger(str(tmp_path / "nonexistent"))
        assert logger.read_all() == []

    def test_multiple_records_appended(self, tmp_path):
        logger = TokenUsageLogger(str(tmp_path))
        for i in range(5):
            logger.record("P", f"T{i:02d}", float(i * 10), "continue", "success")
        entries = logger.read_all()
        assert len(entries) == 5
        assert entries[4]["step_id"] == "T04"

    def test_record_roundtrip_fields(self, tmp_path):
        logger = TokenUsageLogger(str(tmp_path))
        logger.record("Proj", "T99", 91.2, "halt_checkpoint", "failed")
        entry = logger.read_all()[0]
        assert entry["playbook"] == "Proj"
        assert entry["step_id"] == "T99"
        assert entry["token_pct"] == 91.2
        assert entry["action"] == "halt_checkpoint"
        assert entry["step_result"] == "failed"
        assert "timestamp" in entry


# ══════════════════════════════════════════════
# CheckpointManager
# ══════════════════════════════════════════════

class TestCheckpointManager:
    def _make_cp(self) -> PlaybookCheckpoint:
        return PlaybookCheckpoint(
            playbook_path="scripts/test.yaml",
            step_idx=2,
            step_id="T03",
            total_steps=5,
            project="TestProject",
            completed_step_log=["[T01] done", "[T02] done"],
            peak_token_pct=88.0,
        )

    def test_save_creates_file(self, tmp_path):
        mgr = CheckpointManager(str(tmp_path))
        cp = self._make_cp()
        # save() 回傳 None（符合 StateRepositoryPort 契約）；改透過 checkpoint_path 驗證檔案存在
        mgr.save(cp, "scripts/test.yaml")
        assert mgr.checkpoint_path("scripts/test.yaml").exists()

    def test_load_roundtrip(self, tmp_path):
        mgr = CheckpointManager(str(tmp_path))
        cp = self._make_cp()
        mgr.save(cp, "scripts/test.yaml")
        loaded = mgr.load("scripts/test.yaml")
        assert loaded is not None
        assert loaded.step_idx == 2
        assert loaded.step_id == "T03"
        assert loaded.project == "TestProject"
        assert loaded.completed_step_log == ["[T01] done", "[T02] done"]
        assert loaded.peak_token_pct == 88.0

    def test_exists_false_when_no_file(self, tmp_path):
        mgr = CheckpointManager(str(tmp_path))
        assert mgr.exists("scripts/nonexistent.yaml") is False

    def test_exists_true_after_save(self, tmp_path):
        mgr = CheckpointManager(str(tmp_path))
        mgr.save(self._make_cp(), "scripts/test.yaml")
        assert mgr.exists("scripts/test.yaml") is True

    def test_clear_removes_file(self, tmp_path):
        mgr = CheckpointManager(str(tmp_path))
        mgr.save(self._make_cp(), "scripts/test.yaml")
        mgr.clear("scripts/test.yaml")
        assert mgr.exists("scripts/test.yaml") is False

    def test_clear_noop_when_no_file(self, tmp_path):
        mgr = CheckpointManager(str(tmp_path))
        mgr.clear("scripts/nonexistent.yaml")  # should not raise

    def test_load_returns_none_when_missing(self, tmp_path):
        mgr = CheckpointManager(str(tmp_path))
        assert mgr.load("scripts/nonexistent.yaml") is None

    def test_schedule_resume_sets_future_time(self, tmp_path):
        mgr = CheckpointManager(str(tmp_path))
        cp = self._make_cp()
        resume_at = mgr.schedule_resume(cp, delay_minutes=5)
        assert cp.scheduled_resume_at is not None
        assert resume_at > datetime.now()
        parsed = datetime.fromisoformat(cp.scheduled_resume_at)
        # 應在 now + 4min ~ now + 6min 範圍內
        assert timedelta(minutes=4) < (parsed - datetime.now()) < timedelta(minutes=6)

    def test_schedule_resume_zero_delay(self, tmp_path):
        mgr = CheckpointManager(str(tmp_path))
        cp = self._make_cp()
        resume_at = mgr.schedule_resume(cp, delay_minutes=0)
        # 0 分鐘 delay → 幾乎立即（< 2 秒差）
        assert abs((resume_at - datetime.now()).total_seconds()) < 2

    def test_seconds_until_resume_future(self, tmp_path):
        mgr = CheckpointManager(str(tmp_path))
        cp = self._make_cp()
        mgr.schedule_resume(cp, delay_minutes=10)
        secs = CheckpointManager.seconds_until_resume(cp)
        assert secs > 500  # 至少 > 8.5 分鐘

    def test_seconds_until_resume_past(self):
        cp = self._make_cp()
        # 設定為過去時間
        past = datetime.now() - timedelta(minutes=5)
        cp.scheduled_resume_at = past.isoformat(timespec="seconds")
        assert CheckpointManager.seconds_until_resume(cp) == 0.0

    def test_seconds_until_resume_none(self):
        cp = self._make_cp()
        cp.scheduled_resume_at = None
        assert CheckpointManager.seconds_until_resume(cp) == 0.0

    def test_checkpoint_path_naming(self, tmp_path):
        mgr = CheckpointManager(str(tmp_path))
        p = mgr.checkpoint_path("scripts/my_playbook.yaml")
        assert p.name == "my_playbook.checkpoint.json"

    def test_checkpoint_path_matches_actual_saved_filename_for_reserved_device_name(
        self, tmp_path
    ):
        """R48（DEF-101-390）回歸鎖：checkpoint_path()/exists() 曾繞過檔名淨化，
        與 save()/load()/clear()（委派 FileStateRepository._path() 走
        _sanitize_log_filename SSOT）不一致——playbook_path 帶 Windows 保留裝置名
        （如 "con.yaml"）時，checkpoint_path() 回傳未淨化檔名而 save() 實際寫入
        淨化後檔名，兩者不一致；exists() 因此對錯檔名判斷、恆回報 False（即使
        剛存過 checkpoint）。修復後兩者委派同一 SSOT，永遠一致。
        """
        mgr = CheckpointManager(str(tmp_path))
        mgr.save(self._make_cp(), "con.yaml")
        saved_files = list(tmp_path.glob("*.checkpoint.json"))
        assert len(saved_files) == 1, f"預期恰好一個 checkpoint 檔案，實際：{saved_files}"
        assert mgr.checkpoint_path("con.yaml") == saved_files[0], (
            "checkpoint_path() 回傳的路徑必須與 save() 實際寫入磁碟的檔名一致"
        )
        assert mgr.exists("con.yaml") is True

    def test_checkpoint_path_matches_actual_saved_filename_for_forbidden_char_stem(
        self, tmp_path
    ):
        """同上回歸鎖，換一種淨化情境：stem 本身含 NTFS 禁用字元（非保留裝置
        名）。`../evil` 這類路徑穿越字元經 `Path.stem` 取值後已不含 `..`（stem
        只取最後一段去除副檔名），故本測試改以 stem 本身即含禁用字元的檔名
        （`weird<name>.yaml`）驗證 checkpoint_path()/save() 一致性。
        """
        mgr = CheckpointManager(str(tmp_path))
        mgr.save(self._make_cp(), "weird<name>.yaml")
        saved_files = list(tmp_path.glob("*.checkpoint.json"))
        assert len(saved_files) == 1, f"預期恰好一個 checkpoint 檔案，實際：{saved_files}"
        assert mgr.checkpoint_path("weird<name>.yaml") == saved_files[0]
        assert mgr.exists("weird<name>.yaml") is True

    def test_corrupt_file_returns_none(self, tmp_path):
        mgr = CheckpointManager(str(tmp_path))
        bad = tmp_path / "corrupt.checkpoint.json"
        bad.write_text("NOT JSON", encoding="utf-8")
        result = mgr.load("corrupt.yaml")
        assert result is None


# ══════════════════════════════════════════════
# PlaybookRunner — Token Guard 整合測試
# ══════════════════════════════════════════════

def _cfg_with_token_guard(**overrides) -> AppConfig:
    """建立一個啟用 token_guard 的測試用 AppConfig。"""
    tg_fields = dict(
        enabled=True,
        compact_threshold_pct=80.0,
        halt_threshold_pct=90.0,
        resume_delay_minutes=0,    # 測試中不實際等待
        auto_resume=False,         # 測試中不進入外層 sleep 迴圈
        max_auto_resumes=3,
    )
    tg_fields.update(overrides)
    cfg = AppConfig()
    cfg.token_guard = TokenGuardConfig(**tg_fields)
    return cfg


def _write_playbook(tmp_path: Path, tasks: list[dict]) -> str:
    data = {"version": "1.0", "project": "TestProject", "tasks": tasks}
    p = tmp_path / "pb.yaml"
    p.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return str(p)


def _make_runner(tmp_path: Path, cfg: AppConfig | None = None, minimax=None):
    cfg = cfg or _cfg_with_token_guard()
    cfg.log_dir = str(tmp_path / "logs")
    cfg.checkpoint_dir = str(tmp_path / "checkpoints")
    minimax = minimax or MagicMock()
    hotkey = MagicMock()
    hotkey.triggered = False
    return PlaybookRunner(cfg, minimax, hotkey)


@patch("autoclaude.execution.playbook_runner.PtyWrapper")
def test_compact_triggered_when_threshold_reached(mock_pty_cls, tmp_path):
    """output 含有 compact 門檻訊息時，執行完步驟後應送出 /compact。"""
    call_count = [0]

    def make_mock_pty():
        mock_pty = MagicMock()
        # 第一次呼叫（正式 step）：輸出含 80% context + 成功關鍵字
        # 第二次呼叫（/compact 指令）：空輸出
        count = call_count[0]
        call_count[0] += 1
        if count == 0:
            mock_pty.readline.side_effect = [
                "Processing... context 82% used\n",
                "result: STEP_DONE\n",
                None,
            ]
        else:
            mock_pty.readline.return_value = None
        return mock_pty

    mock_pty_cls.side_effect = lambda **kwargs: make_mock_pty()

    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "step", "prompt": "go",
         "expected_output_regex": "STEP_DONE", "maintain_context": False},
    ])
    runner = _make_runner(tmp_path)
    with patch("autoclaude.execution.playbook_runner.notify"):
        result = runner.run(pb_path)

    assert result.success is True
    # /compact 應被呼叫一次（第二次 PtyWrapper 呼叫）
    assert call_count[0] == 2


@patch("autoclaude.execution.playbook_runner.PtyWrapper")
def test_halt_saves_checkpoint(mock_pty_cls, tmp_path):
    """output 含有 halt 門檻訊息時，應儲存 checkpoint 並回傳 halt_for_token=True。"""
    mock_pty = MagicMock()
    mock_pty.readline.side_effect = [
        "context 92% used — approaching limit\n",
        "partial output\n",
        None,
    ]
    mock_pty_cls.return_value = mock_pty

    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "step1", "prompt": "go", "maintain_context": False},
        {"step_id": "T02", "name": "step2", "prompt": "go2", "maintain_context": False},
    ])
    runner = _make_runner(tmp_path)
    with patch("autoclaude.execution.playbook_runner.notify"):
        result = runner.run(pb_path)

    assert result.halt_for_token is True
    assert result.success is False
    assert "checkpoint" in result.reason.lower() or "達限" in result.reason

    # 確認 checkpoint 檔案已建立
    mgr = CheckpointManager(str(tmp_path / "checkpoints"))
    cp = mgr.load(pb_path)
    assert cp is not None
    assert cp.step_idx == 0   # 第 0 步驟尚未完成
    assert cp.project == "TestProject"
    assert cp.peak_token_pct >= 90.0


@patch("autoclaude.execution.playbook_runner.PtyWrapper")
def test_resume_from_checkpoint(mock_pty_cls, tmp_path):
    """存在 checkpoint 時，runner 應從斷點繼續執行，跳過已完成的步驟。"""
    # 先手動建立 checkpoint（模擬 step 0 已完成，從 step 1 繼續）
    mgr = CheckpointManager(str(tmp_path / "checkpoints"))
    mgr._dir.mkdir(parents=True, exist_ok=True)

    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "s1", "prompt": "go1", "maintain_context": False,
         "expected_output_regex": "NEVER_MATCH"},  # 若從頭跑，T01 會失敗
        {"step_id": "T02", "name": "s2", "prompt": "go2", "maintain_context": False,
         "expected_output_regex": "STEP2_DONE"},
    ])
    cp = PlaybookCheckpoint(
        playbook_path=pb_path,
        step_idx=1,             # 從 T02 開始
        step_id="T02",
        total_steps=2,
        project="TestProject",
        completed_step_log=["[T01] done"],
        peak_token_pct=50.0,
    )
    mgr.save(cp, pb_path)

    mock_pty = MagicMock()
    mock_pty.readline.side_effect = ["output: STEP2_DONE\n", None]
    mock_pty_cls.return_value = mock_pty

    runner = _make_runner(tmp_path)
    with patch("autoclaude.execution.playbook_runner.notify"):
        result = runner.run(pb_path, fresh=False)

    assert result.success is True
    assert result.completed_steps == 2
    # 只呼叫了一次 PtyWrapper（T02），T01 被跳過
    assert mock_pty_cls.call_count == 1


@patch("autoclaude.execution.playbook_runner.PtyWrapper")
def test_fresh_flag_ignores_checkpoint(mock_pty_cls, tmp_path):
    """--fresh 時即使存在 checkpoint 也應從頭執行。"""
    mgr = CheckpointManager(str(tmp_path / "checkpoints"))
    mgr._dir.mkdir(parents=True, exist_ok=True)

    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "s1", "prompt": "go", "maintain_context": False,
         "expected_output_regex": "OK"},
    ])
    cp = PlaybookCheckpoint(
        playbook_path=pb_path,
        step_idx=1,             # 假裝已跑完（超出範圍）
        step_id="T01",
        total_steps=1,
        project="TestProject",
    )
    mgr.save(cp, pb_path)

    mock_pty = MagicMock()
    mock_pty.readline.side_effect = ["output: OK\n", None]
    mock_pty_cls.return_value = mock_pty

    runner = _make_runner(tmp_path)
    with patch("autoclaude.execution.playbook_runner.notify"):
        result = runner.run(pb_path, fresh=True)

    # fresh=True → 從 T01 重新執行，輸出符合 OK → 成功
    assert result.success is True
    assert mock_pty_cls.call_count == 1


@patch("autoclaude.execution.playbook_runner.PtyWrapper")
def test_checkpoint_cleared_on_success(mock_pty_cls, tmp_path):
    """所有步驟完成後，checkpoint 檔案應被清除。"""
    mgr = CheckpointManager(str(tmp_path / "checkpoints"))
    mgr._dir.mkdir(parents=True, exist_ok=True)

    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "s1", "prompt": "go", "maintain_context": False,
         "expected_output_regex": "DONE"},
    ])
    # 放一個舊 checkpoint
    cp = PlaybookCheckpoint(
        playbook_path=pb_path, step_idx=0, step_id="T01",
        total_steps=1, project="P",
    )
    mgr.save(cp, pb_path)
    assert mgr.exists(pb_path)

    mock_pty = MagicMock()
    mock_pty.readline.side_effect = ["output DONE here\n", None]
    mock_pty_cls.return_value = mock_pty

    runner = _make_runner(tmp_path)
    with patch("autoclaude.execution.playbook_runner.notify"):
        result = runner.run(pb_path)

    assert result.success is True
    assert not mgr.exists(pb_path)   # checkpoint 應已清除


@patch("autoclaude.execution.playbook_runner.PtyWrapper")
def test_token_guard_disabled_no_compact(mock_pty_cls, tmp_path):
    """token_guard.enabled=False 時，即使輸出有 context 百分比也不觸發 compact。"""
    call_count = [0]

    def make_pty():
        m = MagicMock()
        call_count[0] += 1
        if call_count[0] == 1:
            m.readline.side_effect = [
                "context 95% used\n",
                "output: OK\n",
                None,
            ]
        else:
            m.readline.return_value = None
        return m

    mock_pty_cls.side_effect = lambda **kwargs: make_pty()

    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "s", "prompt": "go",
         "expected_output_regex": "OK", "maintain_context": False},
    ])
    cfg = _cfg_with_token_guard(enabled=False)
    runner = _make_runner(tmp_path, cfg)
    with patch("autoclaude.execution.playbook_runner.notify"):
        result = runner.run(pb_path)

    assert result.success is True
    # 只呼叫了一次 PtyWrapper（不送 /compact）
    assert call_count[0] == 1


@patch("autoclaude.execution.playbook_runner.PtyWrapper")
def test_auto_resume_loop(mock_pty_cls, tmp_path):
    """halt 後若 auto_resume=True 且 resume_delay=0，應自動重新執行。"""
    # 第一次呼叫 → 輸出 92% (halt)，第二次 → 成功
    call_seq = [
        ["context 92% used\n", None],      # halt step
        ["output: DONE\n", None],           # resumed step succeeds
    ]
    call_idx = [0]

    def make_pty():
        m = MagicMock()
        seq = call_seq[call_idx[0] % len(call_seq)]
        call_idx[0] += 1
        m.readline.side_effect = list(seq)
        return m

    mock_pty_cls.side_effect = lambda **kwargs: make_pty()

    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "s", "prompt": "go",
         "expected_output_regex": "DONE", "maintain_context": False},
    ])
    cfg = _cfg_with_token_guard(
        halt_threshold_pct=90.0,
        resume_delay_minutes=0,
        auto_resume=True,
        max_auto_resumes=3,
    )
    runner = _make_runner(tmp_path, cfg)
    with patch("autoclaude.execution.playbook_runner.notify"):
        result = runner.run(pb_path)

    # 第一次 halt → 存 checkpoint；第二次 resume → 成功
    assert result.success is True
    # checkpoint 應被清除
    mgr = CheckpointManager(str(tmp_path / "checkpoints"))
    assert not mgr.exists(pb_path)


# ══════════════════════════════════════════════
# Checkpoint 一致性驗證（Gap-CV）
# ══════════════════════════════════════════════

@patch("autoclaude.execution.playbook_runner.PtyWrapper")
def test_checkpoint_step_id_mismatch_resets_to_start(mock_pty_cls, tmp_path):
    """Playbook 修改後 step_id 不吻合 → 應從頭開始，不靜默執行錯誤步驟。"""
    mgr = CheckpointManager(str(tmp_path / "checkpoints"))
    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "s1", "prompt": "go", "maintain_context": False,
         "expected_output_regex": "DONE"},
    ])
    # 存入一個 step_id 不吻合的 checkpoint（模擬 Playbook 被修改）
    cp = PlaybookCheckpoint(
        playbook_path=pb_path, step_idx=0, step_id="OLD_STEP",
        total_steps=1, project="P",
    )
    mgr.save(cp, pb_path)

    mock_pty = MagicMock()
    mock_pty.readline.side_effect = ["output DONE here\n", None]
    mock_pty_cls.return_value = mock_pty

    runner = _make_runner(tmp_path)
    with patch("autoclaude.execution.playbook_runner.notify"):
        result = runner.run(pb_path)

    # 應從頭執行並成功（不被錯誤 checkpoint 卡住）
    assert result.success is True
    # stale checkpoint 應被清除
    assert not mgr.exists(pb_path)


@patch("autoclaude.execution.playbook_runner.PtyWrapper")
def test_checkpoint_step_idx_out_of_bounds_resets_to_start(mock_pty_cls, tmp_path):
    """Checkpoint step_idx 超出步驟數 → 應從頭開始。"""
    mgr = CheckpointManager(str(tmp_path / "checkpoints"))
    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "s1", "prompt": "go", "maintain_context": False,
         "expected_output_regex": "DONE"},
    ])
    # step_idx=5 但 Playbook 只有 1 個步驟
    cp = PlaybookCheckpoint(
        playbook_path=pb_path, step_idx=5, step_id="T06",
        total_steps=1, project="P",
    )
    mgr.save(cp, pb_path)

    mock_pty = MagicMock()
    mock_pty.readline.side_effect = ["output DONE here\n", None]
    mock_pty_cls.return_value = mock_pty

    runner = _make_runner(tmp_path)
    with patch("autoclaude.execution.playbook_runner.notify"):
        result = runner.run(pb_path)

    assert result.success is True
    assert not mgr.exists(pb_path)


@patch("autoclaude.execution.playbook_runner.PtyWrapper")
def test_checkpoint_consistent_step_id_resumes_normally(mock_pty_cls, tmp_path):
    """Checkpoint step_id 與 Playbook 吻合 → 應從 checkpoint 正常恢復。"""
    mgr = CheckpointManager(str(tmp_path / "checkpoints"))
    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "s1", "prompt": "go1", "maintain_context": False,
         "expected_output_regex": "DONE1"},
        {"step_id": "T02", "name": "s2", "prompt": "go2", "maintain_context": False,
         "expected_output_regex": "DONE2"},
    ])
    # T01 已完成，checkpoint 指向 T02（step_idx=1）
    cp = PlaybookCheckpoint(
        playbook_path=pb_path, step_idx=1, step_id="T02",
        total_steps=2, project="P",
        completed_step_log=["[T01] done"],
    )
    mgr.save(cp, pb_path)

    mock_pty = MagicMock()
    mock_pty.readline.side_effect = ["output DONE2 here\n", None]
    mock_pty_cls.return_value = mock_pty

    runner = _make_runner(tmp_path)
    with patch("autoclaude.execution.playbook_runner.notify"):
        result = runner.run(pb_path)

    assert result.success is True
    # 只執行了 T02（PtyWrapper 只呼叫一次）
    assert mock_pty_cls.call_count == 1


# ══════════════════════════════════════════════
# Gap-007-A：TOKEN_HALT 保存 / 恢復 FailureTracker 歷史
# ══════════════════════════════════════════════

@patch("autoclaude.execution.playbook_runner.PtyWrapper")
def test_halt_saves_failure_history_in_checkpoint(mock_pty_cls, tmp_path):
    """TOKEN_HALT 時，checkpoint 應包含 failure_history 與 active_step_attempt。"""
    mock_pty = MagicMock()
    mock_pty.readline.side_effect = [
        "context 92% used\n",
        "partial output\n",
        None,
    ]
    mock_pty_cls.return_value = mock_pty

    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "step1", "prompt": "go", "maintain_context": False},
    ])
    runner = _make_runner(tmp_path)
    with patch("autoclaude.execution.playbook_runner.notify"):
        result = runner.run(pb_path)

    assert result.halt_for_token is True

    # 確認 checkpoint 包含 Gap-007-A 新增欄位
    mgr = CheckpointManager(str(tmp_path / "checkpoints"))
    cp = mgr.load(pb_path)
    assert cp is not None
    # failure_history 存在且為 list（本次尚無失敗記錄，應為空 list）
    assert isinstance(cp.failure_history, list)
    assert isinstance(cp.active_step_attempt, int)
    assert isinstance(cp.last_correction_prompt, str)


@patch("autoclaude.execution.playbook_runner.PtyWrapper")
def test_resume_restores_failure_tracker_from_checkpoint(mock_pty_cls, tmp_path):
    """恢復時，若 checkpoint 含 failure_history，runner 應重建 FailureTracker 歷史。"""
    mgr = CheckpointManager(str(tmp_path / "checkpoints"))
    mgr._dir.mkdir(parents=True, exist_ok=True)

    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "s1", "prompt": "go", "maintain_context": False,
         "expected_output_regex": "DONE"},
    ])
    # 手動建立含 failure_history 的 checkpoint（模擬 TOKEN_HALT 後恢復）
    failure_hist = [
        {
            "attempt": 0,
            "failure_reason": "regex 不符合",
            "eval_output": "ERROR collecting tests/test_foo.py\n  SyntaxError: invalid syntax",
            "exit_code": 2,
            "error_signature": "SyntaxError: invalid syntax",
            "minimax_reasoning": "測試檔有語法錯誤",
            "correction_prompt_sent": "請修正 test_foo.py",
            "error_class": "syntax",
        },
        {
            "attempt": 1,
            "failure_reason": "regex 不符合",
            "eval_output": "ERROR collecting tests/test_foo.py\n  SyntaxError: invalid syntax",
            "exit_code": 2,
            "error_signature": "SyntaxError: invalid syntax",
            "minimax_reasoning": "仍是相同錯誤",
            "correction_prompt_sent": "",
            "error_class": "syntax",
        },
    ]
    cp = PlaybookCheckpoint(
        playbook_path=pb_path,
        step_idx=0,
        step_id="T01",
        total_steps=1,
        project="TestProject",
        completed_step_log=[],
        failure_history=failure_hist,
        active_step_attempt=2,  # 前兩次已失敗（attempt 0, 1），從 attempt 2 繼續
    )
    mgr.save(cp, pb_path)

    # 讓步驟成功（輸出符合 DONE）
    mock_pty = MagicMock()
    mock_pty.readline.side_effect = ["output: DONE here\n", None]
    mock_pty_cls.return_value = mock_pty

    runner = _make_runner(tmp_path)
    with patch("autoclaude.execution.playbook_runner.notify"):
        result = runner.run(pb_path, fresh=False)

    # 步驟成功，整個 playbook 完成
    assert result.success is True
    # checkpoint 應被清除
    assert not mgr.exists(pb_path)


def test_checkpoint_failure_history_backward_compat(tmp_path):
    """舊格式 checkpoint（無 failure_history 欄位）載入後應使用預設值，不報錯。"""
    mgr = CheckpointManager(str(tmp_path))
    # 建立不含新欄位的舊格式 checkpoint
    cp = PlaybookCheckpoint(
        playbook_path="scripts/test.yaml",
        step_idx=1,
        step_id="T02",
        total_steps=3,
        project="OldProject",
    )
    mgr.save(cp, "scripts/test.yaml")

    loaded = mgr.load("scripts/test.yaml")
    assert loaded is not None
    # 新欄位應有預設值
    assert loaded.failure_history == []
    assert loaded.active_step_attempt == 0
    assert loaded.last_correction_prompt == ""


def test_resume_restores_failure_tracker_history_whitebox():
    """確認 FailureTracker.from_records() 正確重建歷史記錄（白箱驗證 Gap-007-A）。"""
    records = [
        {
            "attempt": 0,
            "failure_reason": "test fail A",
            "eval_output": "FAILED test_foo.py",
            "exit_code": 1,
            "error_signature": "sig_A",
            "minimax_reasoning": "try A",
            "correction_prompt_sent": "fix A",
            "error_class": "assertion",
        },
        {
            "attempt": 1,
            "failure_reason": "test fail B",
            "eval_output": "FAILED test_foo.py",
            "exit_code": 1,
            "error_signature": "sig_A",
            "minimax_reasoning": "try B",
            "correction_prompt_sent": "fix B",
            "error_class": "assertion",
        },
    ]
    tracker = FailureTracker.from_records("T02", records)

    assert len(tracker.history) == 2
    assert tracker.history[0].attempt == 0
    assert tracker.history[0].failure_reason == "test fail A"
    assert tracker.history[0].correction_prompt_sent == "fix A"
    assert tracker.history[1].attempt == 1
    assert tracker.history[1].error_signature == "sig_A"
    # is_stuck() 應觸發（兩個相同 error_signature）
    assert tracker.is_stuck()


# ══════════════════════════════════════════════
# Gap-008-A：is_worsening()
# ══════════════════════════════════════════════

def test_is_worsening_detects_increasing_fail_count():
    """失敗數 3→7→12（嚴格遞增且 > 1.5x）→ is_worsening=True。"""
    tracker = FailureTracker("T01")
    tracker.record(0, "fail", "3 failed\n1 error", 1, "")
    tracker.record(1, "fail", "7 failed\n2 errors", 1, "")
    tracker.record(2, "fail", "12 failed\n3 errors", 1, "")
    assert tracker.is_worsening() is True


def test_is_worsening_noise_tolerant():
    """2→3→3 不嚴格遞增（最後兩筆相同）→ is_worsening=False。"""
    tracker = FailureTracker("T01")
    tracker.record(0, "fail", "2 failed", 1, "")
    tracker.record(1, "fail", "3 failed", 1, "")
    tracker.record(2, "fail", "3 failed", 1, "")  # 不嚴格遞增，3 < 3 為 False
    assert tracker.is_worsening() is False


def test_is_worsening_requires_window():
    """少於 window=3 筆記錄 → is_worsening=False。"""
    tracker = FailureTracker("T01")
    tracker.record(0, "fail", "3 failed", 1, "")
    tracker.record(1, "fail", "12 failed", 1, "")
    assert tracker.is_worsening() is False  # window=3 但只有 2 筆


def test_is_worsening_false_when_count_missing():
    """有一筆無法解析失敗數 → is_worsening=False（保守判斷）。"""
    tracker = FailureTracker("T01")
    tracker.record(0, "fail", "3 failed", 1, "")
    tracker.record(1, "fail", "no count here", 1, "")
    tracker.record(2, "fail", "12 failed", 1, "")
    assert tracker.is_worsening() is False


def test_is_worsening_false_when_improving():
    """失敗數遞減 12→7→3 → is_worsening=False。"""
    tracker = FailureTracker("T01")
    tracker.record(0, "fail", "12 failed", 1, "")
    tracker.record(1, "fail", "7 failed", 1, "")
    tracker.record(2, "fail", "3 failed", 1, "")
    assert tracker.is_worsening() is False


# ══════════════════════════════════════════════
# Gap-008-B：build_history_summary() 去重
# ══════════════════════════════════════════════

def test_build_history_summary_deduplicates_same_signature():
    """相同 error_signature 的記錄應去重，並顯示出現次數。"""
    tracker = FailureTracker("T01")
    for i in range(5):
        tracker.record(i, "fail", f"3 failed\n{i}", 1, f"reasoning {i}",
                       error_class="assertion")
    # 手動設定相同 error_signature（record 會 normalize，5 次相同輸出結構）
    for rec in tracker.history:
        rec.error_signature = "same_sig"
        rec.correction_prompt_sent = "fix prompt"
    summary = tracker.build_history_summary()
    # 只應出現一個去重後的記錄（含「已出現 5 次」）
    assert "已出現 5 次" in summary
    assert summary.count("- Attempt") == 1


def test_build_history_summary_sorts_by_frequency():
    """出現次數多的錯誤排在前面。"""
    tracker = FailureTracker("T01")
    for i in range(3):
        tracker.record(i, "fail", "err A output", 1, "")
        tracker.history[-1].error_signature = "sig_A"
    tracker.record(3, "fail", "err B output", 1, "")
    tracker.history[-1].error_signature = "sig_B"
    summary = tracker.build_history_summary()
    pos_a = summary.find("sig_A")
    pos_b = summary.find("sig_B")
    assert pos_a < pos_b  # sig_A（3 次）應排在 sig_B（1 次）前


def test_build_history_summary_empty():
    """沒有歷史記錄 → 回傳空字串。"""
    tracker = FailureTracker("T01")
    assert tracker.build_history_summary() == ""


# ══════════════════════════════════════════════
# Gap-008-C：suspect_assertion_baseline_mismatch()
# ══════════════════════════════════════════════

def test_suspect_assertion_baseline_mismatch_triggers():
    """全部 assertion + 失敗數未減少 + 特徵碼變化 >= 2 → True。"""
    tracker = FailureTracker("T01")
    tracker.record(
        0, "fail", "FAILED test_foo.py - AssertionError: assert 100 == 42\n1 failed", 1, "",
        error_class="assertion",
    )
    tracker.record(
        1, "fail", "FAILED test_foo.py - AssertionError: assert 100 == 42\n1 failed", 1, "",
        error_class="assertion",
    )
    tracker.record(
        2, "fail", "FAILED test_bar.py - AssertionError: assert 50 == 42\n2 failed", 1, "",
        error_class="assertion",
    )
    # 手動設不同特徵碼
    tracker.history[0].error_signature = "sig_A"
    tracker.history[1].error_signature = "sig_B"
    tracker.history[2].error_signature = "sig_C"
    assert tracker.suspect_assertion_baseline_mismatch() is True


def test_suspect_assertion_baseline_mismatch_false_when_improving():
    """失敗數有在減少（3→1）→ False（不懷疑，可能是正在收斂）。"""
    tracker = FailureTracker("T01")
    tracker.record(0, "fail", "3 failed\nAssertionError", 1, "", error_class="assertion")
    tracker.record(1, "fail", "2 failed\nAssertionError", 1, "", error_class="assertion")
    tracker.record(2, "fail", "1 failed\nAssertionError", 1, "", error_class="assertion")
    tracker.history[0].error_signature = "sig_A"
    tracker.history[1].error_signature = "sig_B"
    tracker.history[2].error_signature = "sig_C"
    assert tracker.suspect_assertion_baseline_mismatch() is False


def test_suspect_assertion_baseline_mismatch_false_when_mixed_classes():
    """非全部都是 assertion 錯誤 → False。"""
    tracker = FailureTracker("T01")
    tracker.record(0, "fail", "AssertionError", 1, "", error_class="assertion")
    tracker.record(1, "fail", "SyntaxError", 2, "", error_class="syntax")
    tracker.record(2, "fail", "AssertionError", 1, "", error_class="assertion")
    tracker.history[0].error_signature = "sig_A"
    tracker.history[1].error_signature = "sig_B"
    tracker.history[2].error_signature = "sig_C"
    assert tracker.suspect_assertion_baseline_mismatch() is False


def test_suspect_assertion_baseline_mismatch_requires_min_attempts():
    """少於 min_attempts=3 → False。"""
    tracker = FailureTracker("T01")
    tracker.record(0, "fail", "AssertionError", 1, "", error_class="assertion")
    tracker.record(1, "fail", "AssertionError", 1, "", error_class="assertion")
    tracker.history[0].error_signature = "sig_A"
    tracker.history[1].error_signature = "sig_B"
    assert tracker.suspect_assertion_baseline_mismatch() is False


# ══════════════════════════════════════════════
# Gap-008-E：連續 compact 失敗升級測試
# ══════════════════════════════════════════════

@patch("autoclaude.execution.playbook_runner.PtyWrapper")
def test_consecutive_compact_failures_trigger_halt(mock_pty_cls, tmp_path):
    """連續 2 次 compact 失敗（compact 後 context 仍高）應觸發 halt，回傳 success=False。"""
    call_count = [0]

    def make_mock_pty():
        mock_pty = MagicMock()
        call_count[0] += 1
        # 每次呼叫都回傳 80%+ context（模擬 compact 無效 → triggered_compact=True）
        mock_pty.readline.side_effect = [
            "context 82% used\n",
            "output: STEP_DONE\n",
            None,
        ]
        return mock_pty

    mock_pty_cls.side_effect = lambda **kwargs: make_mock_pty()

    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "step", "prompt": "go",
         "expected_output_regex": "STEP_DONE", "maintain_context": False},
    ])
    runner = _make_runner(tmp_path)
    # 預設計數器為 1，讓第一次 compact 失敗就達到 >= 2
    # SD_07 W4-T4-2：plugin SSOT 直接設置
    # （原 _consecutive_compact_failures property/setter 已物理拔除）
    runner._token_guard_plugin._compact_failure_count = 1

    with patch("autoclaude.execution.playbook_runner.notify"):
        result = runner.run(pb_path)

    assert result.success is False
    assert "Gap-008-E" in result.reason


def test_consecutive_compact_counter_resets_on_success():
    """compact 成功（context 下降）後計數器應重置為 0。"""
    from autoclaude.execution.playbook_runner import PlaybookRunner, _StepOutput
    from autoclaude.plugins.token_guard_plugin import TokenGuardPlugin
    from autoclaude.utils.config import TokenGuardConfig

    runner_instance = PlaybookRunner.__new__(PlaybookRunner)
    # SD_07 W4-T4-2：plugin SSOT — __new__ 後須手動建立 plugin（原 setter 之 lazy 路徑已拔除）
    runner_instance._token_guard_plugin = TokenGuardPlugin(token_guard_cfg=TokenGuardConfig())
    runner_instance._token_guard_plugin._compact_failure_count = 1
    runner_instance._cfg = MagicMock()
    runner_instance._cfg.token_guard.enabled = False
    runner_instance._hotkey = MagicMock()
    runner_instance._hotkey.triggered = False

    # compact 後 triggered_compact=False → 代表成功
    success_out = _StepOutput(text="ok", triggered_compact=False, triggered_halt=False)

    with patch.object(runner_instance, "_execute_prompt", return_value=success_out):
        runner_instance._send_compact(False)

    assert runner_instance._token_guard_plugin.compact_failure_count == 0
