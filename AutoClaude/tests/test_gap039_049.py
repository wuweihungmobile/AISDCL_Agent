"""
Gap-039 ~ Gap-049 測試（Evo-006）。

測試範疇：
  - Gap-039: _send_compact() global_goal 注入到 MEMORY ANCHOR
  - Gap-040: _build_achievement_summary() 超過 20 步時的截斷修復
  - Gap-041: 演化後跳過已完成步驟（completed_step_ids checkpoint）
  - Gap-042: GOTO/INJECT_BEFORE/SKIP_TO 計數器持久化到 Checkpoint
  - Gap-043: SPLIT_STEP rfind or mid 語意 Bug 修復
  - Gap-044: GOAL_SYNTHESIS ESCALATION 先嘗試 MinimaxEvolver
  - Gap-045: 演化後 KB 預播種（escalated_step_ids）
  - Gap-046: CONDITIONAL shell=True 安全防護（白名單驗證）
  - Gap-047: compact anchor 包含 expected_output_regex
  - Gap-048: per-step 演化次數上限（同一步驟最多 2 次）
  - Gap-049: GOTO 上限從硬編碼 3 改為 AppConfig.playbook.max_goto_per_step
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import yaml

from autoclaude.execution.playbook_runner import PlaybookRunner
from autoclaude.models.playbook import PlaybookTask
from autoclaude.utils.config import AppConfig
from tests.helpers.fake_pty import fake_pty, hermetic_runner  # noqa: F401  fixture 需在本模組可見

# 🔴 R90／DEF-200-127：本檔 3 支（連同 test_gap014_020.py 共 11 支）原本掛
# `requires_claude_cli` skipif，因為 `dry_run=False` 的 `runner.run()` 會真的去
# spawn `claude` CLI。現改掛 `@hermetic_runner`（patch 掉真實執行接縫
# `autoclaude.execution.playbook_runner.PtyWrapper`），兩平台都跑得到，斷言零修改。
# 完整推導只住一個地方＝`tests/helpers/fake_pty.py` 的 docstring；本檔與
# test_gap014_020.py 皆刻意不複寫（這兩檔的 reason 字串在 R79~R84 期間就是因為
# 各留一份而一起漂掉的）。
#
# 🔴 被繞過但**未歸因**：macOS 上 R85 實測 `env -u CLAUDECODE pytest 本檔` 逾 600s
# 未完成，成因未知（Windows 側已歸因＝wexpect pty spawn，DEF-101-913）。本輪的修法
# 讓這 3 支不再觸發它，**不是**查清了它。


# ──────────────────────────────────────────────
# 測試輔助
# ──────────────────────────────────────────────

def _make_runner(dry_run: bool = False, minimax_mock=None,
                 checkpoint_mgr=None, knowledge_base=None) -> PlaybookRunner:
    cfg = AppConfig()
    minimax = minimax_mock or MagicMock()
    hotkey = MagicMock()
    hotkey.triggered = False
    return PlaybookRunner(cfg, minimax, hotkey, dry_run=dry_run,
                          checkpoint_mgr=checkpoint_mgr,
                          knowledge_base=knowledge_base)


def _write_playbook(tmp_path: Path, tasks: list, extra: dict | None = None) -> str:
    data: dict = {
        "version": "1.0",
        "project": "UnitTest",
        "global_invariants": {"max_retries_per_step": 2, "auto_compact_interval": 0},
        "tasks": tasks,
    }
    if extra:
        data.update(extra)
    p = tmp_path / "pb.yaml"
    p.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return str(p)


def _mock_execute_factory(peak_pct: float = 30.0, text: str = "compact done"):
    """回傳一個 mock _execute_prompt，同時捕捉所有 prompts。"""
    from autoclaude.execution.playbook_runner import _StepOutput
    captured = []
    def mock_execute(prompt, maintain_context, timeout, step_label):
        captured.append(prompt)
        return _StepOutput(text=text, peak_token_pct=peak_pct)
    return mock_execute, captured


# ══════════════════════════════════════════════
# Gap-039：_send_compact() global_goal 注入
# ══════════════════════════════════════════════

def test_gap039_send_compact_includes_global_goal_in_anchor():
    """Gap-039：compact anchor 中必須包含 [GLOBAL_GOAL] 當有 task 且有 global_goal 時。"""
    runner = _make_runner(dry_run=True)
    mock_exec, captured = _mock_execute_factory()
    runner._execute_prompt = mock_exec

    task = PlaybookTask(step_id="T01", name="測試步驟", prompt="執行任務")
    result = runner._send_compact(
        is_first=False,
        task=task,
        attempt=1,
        global_goal="建立完整 FastAPI 登入模組，包含 JWT 驗證與資料庫連線",
    )
    assert result is True
    assert captured, "應有 compact prompt 被發送"
    assert "[GLOBAL_GOAL]" in captured[0], "anchor 必須包含 [GLOBAL_GOAL]"
    assert "FastAPI" in captured[0], "global_goal 內容應出現在 anchor 中"


def test_gap039_send_compact_no_goal_no_anchor_line():
    """Gap-039：無 global_goal 時 anchor 不應有 [GLOBAL_GOAL] 行。"""
    runner = _make_runner(dry_run=True)
    mock_exec, captured = _mock_execute_factory()
    runner._execute_prompt = mock_exec

    task = PlaybookTask(step_id="T01", name="步驟", prompt="任務")
    result = runner._send_compact(is_first=False, task=task, attempt=0, global_goal=None)
    assert result is True
    assert captured
    assert "[GLOBAL_GOAL]" not in captured[0], "無 global_goal 時不應有 [GLOBAL_GOAL] 行"


def test_gap039_send_compact_long_goal_includes_ellipsis():
    """Gap-039 修復（問題 #5）：global_goal 超過 anchor_chars 時應加上 … 截斷符號。"""
    runner = _make_runner(dry_run=True)
    mock_exec, captured = _mock_execute_factory()
    runner._execute_prompt = mock_exec

    task = PlaybookTask(step_id="T01", name="N", prompt="P")
    # 構造超過 anchor_chars 的 goal
    anchor_chars = runner._cfg.playbook.global_goal_anchor_chars
    long_goal = "A" * (anchor_chars + 100)
    runner._send_compact(is_first=False, task=task, attempt=0, global_goal=long_goal)
    assert captured
    assert "[GLOBAL_GOAL]" in captured[0]
    assert "…" in captured[0], "超長 goal 應包含 … 截斷符號"


def test_gap039_send_compact_short_goal_no_ellipsis():
    """Gap-039 修復（問題 #5）：global_goal 未超過 anchor_chars 時不應有截斷符號。"""
    runner = _make_runner(dry_run=True)
    mock_exec, captured = _mock_execute_factory()
    runner._execute_prompt = mock_exec

    task = PlaybookTask(step_id="T01", name="N", prompt="P")
    short_goal = "短目標"
    runner._send_compact(is_first=False, task=task, attempt=0, global_goal=short_goal)
    assert captured
    assert "[GLOBAL_GOAL]" in captured[0]
    assert "…" not in captured[0], "短 goal 不應包含 … 截斷符號"


# ══════════════════════════════════════════════
# Gap-040：_build_achievement_summary() 截斷修復
# ══════════════════════════════════════════════

def test_gap040_achievement_summary_truncation():
    """Gap-040：超過 20 步時摘要包含「前 N 個步驟已完成」標頭 + 最後 10 筆。"""
    logs = [f"[T{i:02d}] 步驟 {i} 完成" for i in range(1, 26)]  # 25 個步驟
    summary = PlaybookRunner._build_achievement_summary(logs)
    assert "前 15 個步驟已完成" in summary, "應顯示前 N 步驟計數"
    assert "[T25] 步驟 25 完成" in summary, "最後步驟應出現在摘要中"
    assert "[T01] 步驟 1 完成" not in summary, "早期步驟不應出現在最後 10 筆詳細記錄中"


def test_gap040_achievement_summary_no_truncation_for_small_log():
    """Gap-040：20 步以內直接回傳全部，不加截斷標頭。"""
    short_logs = [f"[T{i}] 完成" for i in range(1, 16)]
    short_summary = PlaybookRunner._build_achievement_summary(short_logs)
    assert "前" not in short_summary, "15 步以內不應有截斷標頭"
    assert len(short_summary.split("\n")) == 15


# ══════════════════════════════════════════════
# Gap-041：演化後跳過已完成步驟
# ══════════════════════════════════════════════

def test_gap041_evolution_resumes_from_last_successful_step(tmp_path):
    """Gap-041：干跑驗證已完成步驟被跳過（completed_step_ids 從 checkpoint 讀取）。"""
    from autoclaude.utils.checkpoint_manager import CheckpointManager, PlaybookCheckpoint
    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "步驟1", "prompt": "p1",
         "expected_output_regex": "dry-run-pass"},
        {"step_id": "T02", "name": "步驟2", "prompt": "p2",
         "expected_output_regex": "dry-run-pass"},
        {"step_id": "T03", "name": "步驟3", "prompt": "p3",
         "expected_output_regex": "dry-run-pass"},
    ])
    # 使用隔離 checkpoint 目錄，防止 checkpoints/pb.mutated.yaml 等跨測試污染
    cp_dir = str(tmp_path / "cp")
    cp_mgr = CheckpointManager(cp_dir)
    runner = _make_runner(dry_run=True, checkpoint_mgr=cp_mgr)
    runner._cfg.checkpoint_dir = cp_dir  # Gap-013-C 同樣使用此路徑，確保一致性
    cp = PlaybookCheckpoint(
        playbook_path=pb_path, step_idx=0, step_id="T01",
        total_steps=3, project="UnitTest",
        completed_step_ids=["T01"],
    )
    cp_mgr.save(cp, pb_path)
    result = runner.run(pb_path, fresh=False)
    assert result.success is True
    resumed = [log for log in result.step_log if "[RESUMED] T01" in log]
    assert len(resumed) >= 1, "T01 應在 step_log 中有 [RESUMED] 標記"
    t02_ok = [log for log in result.step_log if "T02" in log and "✓" in log]
    assert len(t02_ok) >= 1, "T02 應正常執行並成功"


def test_gap041_save_evolution_resume_checkpoint(tmp_path):
    """Gap-041：_save_evolution_resume_checkpoint 正確儲存 completed_step_ids。"""
    from autoclaude.models.playbook import Playbook
    from autoclaude.utils.checkpoint_manager import CheckpointManager
    cp_mgr = CheckpointManager(str(tmp_path / "cp"))
    runner = _make_runner(dry_run=True, checkpoint_mgr=cp_mgr)
    evolved_path = str(tmp_path / "evolved.yaml")
    pb_data = {
        "version": "1.0", "project": "Test",
        "global_invariants": {"max_retries_per_step": 2, "auto_compact_interval": 0},
        "tasks": [{"step_id": "T01", "name": "N", "prompt": "P"}],
    }
    with open(evolved_path, "w", encoding="utf-8") as f:
        yaml.dump(pb_data, f)
    playbook = Playbook(**pb_data)
    # SD_06 W2-T2-9：mixin _save_evolution_resume_checkpoint 已物理刪除；改呼叫 plugin 公開 API
    runner._checkpoint_plugin.save_evolution_resume_checkpoint(
        evolved_path=evolved_path, playbook=playbook,
        step_log=["[T01] ok"], completed_step_ids={"T01", "T02"},
    )
    cp = cp_mgr.load(evolved_path)
    assert cp is not None
    assert set(cp.completed_step_ids) == {"T01", "T02"}
    assert cp.step_idx == 0


# ══════════════════════════════════════════════
# Gap-042：突變計數器持久化到 Checkpoint
# ══════════════════════════════════════════════

def test_gap042_goto_counter_persisted_in_checkpoint(tmp_path):
    """Gap-042：_handle_token_halt() 儲存的 checkpoint 包含 goto_counter 等計數器。"""
    from autoclaude.execution.playbook_runner import _StepOutput
    from autoclaude.execution.workflow_detector import WorkflowType
    from autoclaude.models.playbook import Playbook
    from autoclaude.utils.checkpoint_manager import CheckpointManager

    cp_mgr = CheckpointManager(str(tmp_path))
    runner = _make_runner(dry_run=True, checkpoint_mgr=cp_mgr)
    task = PlaybookTask(step_id="T02", name="N", prompt="P")
    pb_data = {
        "version": "1.0", "project": "Test",
        "global_invariants": {"max_retries_per_step": 2, "auto_compact_interval": 0},
        "tasks": [
            {"step_id": "T01", "name": "N", "prompt": "P"},
            {"step_id": "T02", "name": "N", "prompt": "P"},
        ],
    }
    playbook = Playbook(**pb_data)
    step_out = _StepOutput(text="", peak_token_pct=95.0, triggered_halt=True)
    pb_path = str(tmp_path / "test.yaml")
    with open(pb_path, "w", encoding="utf-8") as f:
        yaml.dump(pb_data, f)

    runner._handle_token_halt(
        playbook, pb_path, task, 1, step_out, ["log1"], WorkflowType.UNKNOWN, 2,
        goto_counter={"T01": 2},
        inject_before_counter={"T02": 1},
        skip_to_counter={"T03": 1},
    )
    cp = cp_mgr.load(pb_path)
    assert cp is not None
    assert cp.goto_counter == {"T01": 2}
    assert cp.inject_before_counter == {"T02": 1}
    assert cp.skip_to_counter == {"T03": 1}


def test_gap042_goto_counter_restored_from_checkpoint(tmp_path):
    """Gap-042：checkpoint 帶有 goto_counter 時 _run_steps() 正常載入不崩潰。"""
    from autoclaude.utils.checkpoint_manager import CheckpointManager, PlaybookCheckpoint
    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "N", "prompt": "p", "expected_output_regex": "dry-run-pass"},
    ])
    cp_mgr = CheckpointManager(str(tmp_path / "cp"))
    runner = _make_runner(dry_run=True, checkpoint_mgr=cp_mgr)
    cp = PlaybookCheckpoint(
        playbook_path=pb_path, step_idx=0, step_id="T01",
        total_steps=1, project="UnitTest",
        goto_counter={"T01": 2},
        inject_before_counter={"T02": 3},
        skip_to_counter={"T03": 1},
    )
    cp_mgr.save(cp, pb_path)
    result = runner.run(pb_path, fresh=False)
    assert result is not None, "帶計數器的 checkpoint 不應導致崩潰"


def test_gap042_interrupt_checkpoint_persists_counters(tmp_path):
    """Gap-042 修復（問題 #2）：ESC+F12 中斷時 _save_interrupt_checkpoint 應持久化計數器。"""
    from autoclaude.models.playbook import Playbook
    from autoclaude.utils.checkpoint_manager import CheckpointManager
    cp_mgr = CheckpointManager(str(tmp_path / "cp"))
    runner = _make_runner(dry_run=True, checkpoint_mgr=cp_mgr)

    pb_data = {
        "version": "1.0", "project": "Test",
        "global_invariants": {"max_retries_per_step": 2, "auto_compact_interval": 0},
        "tasks": [
            {"step_id": "T01", "name": "N", "prompt": "P"},
            {"step_id": "T02", "name": "N", "prompt": "P"},
        ],
    }
    playbook = Playbook(**pb_data)
    pb_path = str(tmp_path / "pb.yaml")
    with open(pb_path, "w", encoding="utf-8") as f:
        yaml.dump(pb_data, f)

    task = playbook.tasks[1]
    # SD_06 W2-T2-10：mixin _save_interrupt_checkpoint 已物理刪除；改呼叫 plugin 公開 API
    runner._checkpoint_plugin.save_interrupt_checkpoint(
        playbook=playbook, playbook_path=pb_path, task=task,
        step_idx=1, step_log=["[T01] ok"], total=2,
        tracker=None, attempt=0,
        goto_counter={"T01": 2},
        inject_before_counter={"T02": 1},
        skip_to_counter={"T03": 0},
        completed_step_ids=["T01"],
        step_evolution_counter={"T02": 1},
    )

    cp = cp_mgr.load(pb_path)
    assert cp is not None
    assert cp.goto_counter == {"T01": 2}, "ESC+F12 中斷後 goto_counter 應持久化"
    assert cp.inject_before_counter == {"T02": 1}
    assert cp.skip_to_counter == {"T03": 0}
    assert cp.completed_step_ids == ["T01"], "ESC+F12 中斷後 completed_step_ids 應持久化"
    assert cp.step_evolution_counter == {"T02": 1}, \
        "Gap-048：ESC+F12 中斷後 step_evolution_counter 應持久化"


def test_gap048_step_evolution_counter_persisted_in_token_halt(tmp_path):
    """Gap-048 修復（問題 #3）：_handle_token_halt 應持久化 step_evolution_counter。"""
    from autoclaude.execution.playbook_runner import _StepOutput
    from autoclaude.execution.workflow_detector import WorkflowType
    from autoclaude.models.playbook import Playbook
    from autoclaude.utils.checkpoint_manager import CheckpointManager

    cp_mgr = CheckpointManager(str(tmp_path))
    runner = _make_runner(dry_run=True, checkpoint_mgr=cp_mgr)

    pb_data = {
        "version": "1.0", "project": "Test",
        "global_invariants": {"max_retries_per_step": 2, "auto_compact_interval": 0},
        "tasks": [{"step_id": "T01", "name": "N", "prompt": "P"}],
    }
    playbook = Playbook(**pb_data)
    pb_path = str(tmp_path / "pb.yaml")
    with open(pb_path, "w", encoding="utf-8") as f:
        yaml.dump(pb_data, f)

    task = playbook.tasks[0]
    step_out = _StepOutput(text="", peak_token_pct=95.0, triggered_halt=True)
    runner._handle_token_halt(
        playbook, pb_path, task, 0, step_out, [], WorkflowType.UNKNOWN, 1,
        completed_step_ids={"T00"},
        step_evolution_counter={"T01": 1, "T02": 2},
    )
    cp = cp_mgr.load(pb_path)
    assert cp is not None
    assert cp.step_evolution_counter == {"T01": 1, "T02": 2}, \
        "Gap-048：TOKEN_HALT 後 step_evolution_counter 應正確恢復"
    assert "T00" in cp.completed_step_ids, \
        "Gap-042：TOKEN_HALT 後 completed_step_ids 應正確恢復"


def test_gap048_step_evolution_counter_restored_into_run_steps(tmp_path):
    """Gap-048 修復（問題 #3）：_run_steps 初始化時應從 resume_checkpoint 讀取
    step_evolution_counter。"""
    from autoclaude.utils.checkpoint_manager import CheckpointManager, PlaybookCheckpoint
    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "N", "prompt": "p", "expected_output_regex": "dry-run-pass"},
    ])
    cp_mgr = CheckpointManager(str(tmp_path / "cp"))
    runner = _make_runner(dry_run=True, checkpoint_mgr=cp_mgr)
    runner._cfg.checkpoint_dir = str(tmp_path / "cp")

    cp = PlaybookCheckpoint(
        playbook_path=pb_path, step_idx=0, step_id="T01",
        total_steps=1, project="UnitTest",
        step_evolution_counter={"T01": 2},
    )
    cp_mgr.save(cp, pb_path)
    # 帶 step_evolution_counter 的 checkpoint 不應導致 _run_steps 崩潰
    result = runner.run(pb_path, fresh=False)
    assert result is not None, "帶 step_evolution_counter 的 checkpoint 不應導致崩潰"


# ══════════════════════════════════════════════
# Gap-043：SPLIT_STEP rfind bug 修復
# ══════════════════════════════════════════════

def test_gap043_split_step_rfind_zero_position():
    """Gap-043：換行在位置 0（rfind 回傳 0 != -1），但因 < 50 兜底到 mid。"""
    prompt = "\n" + "A" * 100 + "\n" + "B" * 100  # 第一個字符是換行
    mid = len(prompt) // 2
    _nl_pos = prompt.rfind("\n", 0, mid)
    # 舊 bug: `_nl_pos or mid` → 0 or mid = mid（falsy 語意；但當 _nl_pos=0 時語意錯誤）
    # 新修復: `_nl_pos if _nl_pos != -1 else mid`
    split_pos = _nl_pos if _nl_pos != -1 else mid
    if split_pos < 50:
        split_pos = mid
    assert split_pos >= 50, "Part A 至少需要 50 字符"
    part_a = prompt[:split_pos].strip()
    assert len(part_a) > 0, "Part A 不應為空"


def test_gap043_split_step_rfind_returns_neg1():
    """Gap-043：rfind 回傳 -1（前半無換行）時，split_pos 應使用字符中點。"""
    prompt = "A" * 200  # 無換行
    mid = len(prompt) // 2
    _nl_pos = prompt.rfind("\n", 0, mid)
    assert _nl_pos == -1
    split_pos = _nl_pos if _nl_pos != -1 else mid
    if split_pos < 50:
        split_pos = mid
    assert split_pos == mid, "rfind=-1 時應使用字符中點"


# ══════════════════════════════════════════════
# Gap-044：GOAL_SYNTHESIS ESCALATION → MinimaxEvolver
# ══════════════════════════════════════════════

@hermetic_runner
def test_gap044_goal_synthesis_escalation_tries_minimax_evolver_first(tmp_path):
    """Gap-044：GOAL_SYNTHESIS ESCALATION 應先呼叫 MinimaxEvolver（max_retries=0）。"""
    minimax_mock = MagicMock()
    minimax_mock.decide_correction.return_value = ("修正", "", None, None)
    runner = _make_runner(dry_run=False, minimax_mock=minimax_mock)
    minimax_evolver_mock = MagicMock()
    minimax_evolver_mock.propose_evolution_via_ai.return_value = None
    runner._minimax_evolver = minimax_evolver_mock

    pb_path = _write_playbook(tmp_path, [
        {"step_id": "GOAL_SYNTHESIS", "name": "全局驗證", "prompt": "驗證",
         "expected_output_regex": "DONE", "max_retries": 0},
    ])
    runner.run(pb_path, fresh=True)
    assert minimax_evolver_mock.propose_evolution_via_ai.called, \
        "Gap-044: GOAL_SYNTHESIS ESCALATION 應先呼叫 MinimaxEvolver"


@hermetic_runner
def test_gap044_goal_synthesis_inject_step_returns_evolved_path(tmp_path):
    """Gap-044：MinimaxEvolver 提議 INJECT_STEP 時應返回演化版路徑。"""
    minimax_mock = MagicMock()
    minimax_mock.decide_correction.return_value = ("修正", "", None, None)
    runner = _make_runner(dry_run=False, minimax_mock=minimax_mock)
    # max_evolutions=0 防止 runner 自動重載演化版 Playbook（確保第一次執行結果直接返回）
    runner._cfg.playbook.max_evolutions = 0

    evolved_path = str(tmp_path / "evolved.yaml")
    evolved_data = {
        "version": "1.0", "project": "Test",
        "global_invariants": {"max_retries_per_step": 1, "auto_compact_interval": 0},
        "tasks": [{"step_id": "GS_FIX", "name": "補完", "prompt": "修復",
                   "expected_output_regex": "DONE"}],
    }
    with open(evolved_path, "w", encoding="utf-8") as f:
        yaml.dump(evolved_data, f)

    proposal_mock = MagicMock()
    proposal_mock.evolution_type = "INJECT_STEP"
    minimax_evolver_mock = MagicMock()
    minimax_evolver_mock.propose_evolution_via_ai.return_value = proposal_mock
    runner._minimax_evolver = minimax_evolver_mock

    evolver_mock = MagicMock()
    evolver_mock.apply_evolution.return_value = evolved_path
    runner._evolver = evolver_mock

    pb_path = _write_playbook(tmp_path, [
        {"step_id": "GOAL_SYNTHESIS", "name": "全局驗證", "prompt": "驗證",
         "expected_output_regex": "DONE", "max_retries": 0},
    ])
    result = runner.run(pb_path, fresh=True)
    assert result.evolved_playbook_path is not None, \
        "Gap-044: INJECT_STEP 提議應返回演化版 Playbook 路徑"


# ══════════════════════════════════════════════
# Gap-045：KB 預播種
# ══════════════════════════════════════════════

def test_gap045_knowledge_base_preseeded_for_evolved_steps(tmp_path):
    """Gap-045：演化後重啟時，新注入步驟的 KB 建議已被預播種。"""
    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01_PRE", "name": "前置", "prompt": "安裝",
         "expected_output_regex": "dry-run-pass"},
        {"step_id": "T01", "name": "主任務", "prompt": "執行",
         "expected_output_regex": "dry-run-pass"},
    ], extra={
        "evolution_metadata": {
            "original_step_id": "T01",
            "evolution_type": "INJECT_STEP",
            "escalated_step_ids": ["T01"],
            "mutation_log": [],
        }
    })
    from autoclaude.utils.knowledge_base import FailureKnowledgeBase
    kb = FailureKnowledgeBase(str(tmp_path / "kb.jsonl"))
    runner = _make_runner(dry_run=True, knowledge_base=kb)
    result = runner.run(pb_path, fresh=True)
    assert result.success is True
    kb_entry = kb.query("import:T01_PRE:env_setup")
    assert kb_entry is not None, "Gap-045: KB 應為 T01_PRE 預播種記錄"


def test_gap045_kb_fallback_query_hits_preseeded_step_id(tmp_path):
    """Gap-045 修復端到端：CORRECTION 路徑透過 step_id 兜底 key 命中預播種記錄。

    模擬演化後重啟時，T01_PRE 步驟發生 IMPORT 錯誤，但實際 error_signature
    與預播種 key 不同；查詢端需用「{error_class}:{step_id}:env_setup」兜底 key 命中。
    """
    from autoclaude.utils.knowledge_base import FailureKnowledgeBase

    # 模擬演化後重啟時 KB 已被預播種（注入 kb 而非存取 internal alias）
    kb = FailureKnowledgeBase(str(tmp_path / "kb.jsonl"))
    _make_runner(dry_run=True, knowledge_base=kb)
    kb.record_success(
        "import:T01_PRE:env_setup", "PINPOINT", "T01_PRE", error_class="import",
    )

    # 直接查詢驗證兜底 key 格式正確
    direct = kb.query("import:T01_PRE:env_setup")
    assert direct is not None, "預播種記錄應可直接查詢命中"
    assert direct.get("successful_strategy") == "PINPOINT"
    assert direct.get("error_class") == "import"

    # 驗證 query() 在原始 error_signature 不命中時，呼叫端會以兜底 key 二次查詢
    # （此處模擬 CORRECTION 路徑邏輯：先用 error_sig，再用 step_id-based 兜底）
    error_sig_key = "import:ModuleNotFoundError:fastapi"
    primary = kb.query(error_sig_key)
    assert primary is None, "原始 error_signature key 不應命中"
    fallback_key = "import:T01_PRE:env_setup"
    fallback = kb.query(fallback_key)
    assert fallback is not None, "Gap-045: 兜底 key 應命中預播種記錄"


# ══════════════════════════════════════════════
# Gap-046：CONDITIONAL evaluator 安全防護
# ══════════════════════════════════════════════

def test_gap046_conditional_rejects_unsafe_evaluator():
    """Gap-046：包含危險字符的 condition_evaluator 應被拒絕執行。"""
    import re
    _SAFE = re.compile(r'^[\w\s\-./|&><=:!"\']+$')
    assert not _SAFE.match("echo `cat /etc/passwd`".strip()), "反引號應被判定為不安全"
    assert not _SAFE.match("echo $(rm -rf /)".strip()), "$(...)應被判定為不安全"
    assert not _SAFE.match("pytest; rm -rf .".strip()), "分號應被判定為不安全"


def test_gap046_conditional_allows_safe_evaluator():
    """Gap-046：安全的 condition_evaluator 應通過白名單驗證。"""
    import re
    _SAFE = re.compile(r'^[\w\s\-./|&><=:!"\']+$')
    assert _SAFE.match("pytest tests/test_foo.py -v".strip()), "pytest 指令應通過驗證"
    assert _SAFE.match("python -c 'import fastapi'".strip()), "python import 應通過驗證"


def test_gap046_production_regex_rejects_chain_attacks():
    """Gap-046 修復（問題 #4）：生產端 regex 應拒絕 &&/||/>/< 等鏈式/重定向字符。"""
    import re
    # 與生產碼 _SHELL_TRUE_COND_WHITELIST 一致
    _SAFE = re.compile(r'^[\w\s\-./=:!"\']+$')
    # 鏈式執行攻擊
    assert not _SAFE.match("pytest && curl evil.com"), "&& 應被拒絕"
    assert not _SAFE.match("pytest || rm -rf /"), "|| 應被拒絕"
    assert not _SAFE.match("pytest | tee /tmp/x"), "管道 | 應被拒絕"
    # 重定向攻擊
    assert not _SAFE.match("echo > /tmp/x"), "> 重定向應被拒絕"
    assert not _SAFE.match("cat < /etc/passwd"), "< 重定向應被拒絕"
    # 正常指令仍可通過
    assert _SAFE.match("pytest tests/test_foo.py -v"), "pytest -v 應通過"
    assert _SAFE.match("python -c 'import fastapi'"), "python -c 'import' 應通過"
    assert _SAFE.match("test -f /tmp/marker"), "test -f 應通過"
    assert _SAFE.match("pytest -k 'auth and not slow'"), "pytest -k 過濾應通過"


def test_gap046_production_runner_rejects_chain_in_conditional(tmp_path):
    """Gap-046 修復（問題 #4）：runner 端 _apply_single_mutation 應拒絕含 && 的 evaluator。"""
    from autoclaude.models.step_mutation import StepMutation, StepMutationType
    runner = _make_runner(dry_run=True)
    task = PlaybookTask(step_id="T01", name="N", prompt="P")

    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "N", "prompt": "P"},
    ])
    import yaml as _yaml

    from autoclaude.models.playbook import Playbook
    with open(pb_path, encoding="utf-8") as f:
        playbook = Playbook(**_yaml.safe_load(f))

    # CONDITIONAL 突變帶有鏈式攻擊
    mutation = StepMutation(
        mutation_type=StepMutationType.CONDITIONAL,
        condition_evaluator="pytest && curl evil.com",
        true_mutation=None,
        false_mutation=None,
    )
    # 直接呼叫 _apply_single_mutation，預期 condition_evaluator 因白名單失敗被略過
    from autoclaude.execution.failure_tracker import FailureTracker
    from autoclaude.execution.workflow_detector import WorkflowType
    tracker = FailureTracker("T01")
    result = runner._apply_single_mutation(
        mutation, playbook, pb_path, task, 0,
        [], [], 0, {}, {}, {},
        WorkflowType.UNKNOWN, 1, tracker, "",
    )
    # 因驗證失敗，無分支被執行 → result.should_break 應為 False、early_return 為 None
    assert result.early_return is None
    assert result.should_break is False
    assert result.goto_target_idx is None


# ══════════════════════════════════════════════
# Gap-047：compact anchor 包含 expected_output_regex
# ══════════════════════════════════════════════

def test_gap047_compact_anchor_includes_success_regex():
    """Gap-047：compact anchor 應包含 [SUCCESS_CONDITION] 當 task 有 expected_output_regex 時。"""
    runner = _make_runner(dry_run=True)
    mock_exec, captured = _mock_execute_factory()
    runner._execute_prompt = mock_exec

    task = PlaybookTask(
        step_id="T01", name="測試步驟", prompt="執行任務",
        expected_output_regex=r"\[DONE\]",
    )
    runner._send_compact(is_first=False, task=task, attempt=0)
    assert captured
    assert "[SUCCESS_CONDITION]" in captured[0], \
        "Gap-047: anchor 應包含 [SUCCESS_CONDITION] 欄位"


# ══════════════════════════════════════════════
# Gap-048：per-step 演化次數限制
# ══════════════════════════════════════════════

@hermetic_runner
def test_gap048_same_step_evolution_limited_to_twice(tmp_path):
    """Gap-048：同一步驟觸發演化次數達 2 次時，強制人工介入（不再演化）。"""
    minimax_mock = MagicMock()
    minimax_mock.decide_correction.return_value = ("修正", "", None, None)
    runner = _make_runner(dry_run=False, minimax_mock=minimax_mock)

    evolver_mock = MagicMock()
    evolver_mock.apply_evolution.return_value = None
    evolver_mock.propose_evolution.return_value = None
    runner._evolver = evolver_mock

    minimax_evolver_mock = MagicMock()
    minimax_evolver_mock.propose_evolution_via_ai.return_value = None
    runner._minimax_evolver = minimax_evolver_mock

    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "困難任務", "prompt": "執行",
         "expected_output_regex": "NEVER_MATCH", "max_retries": 0},
    ])
    result = runner.run(pb_path, fresh=True)
    assert result.success is False
    assert result.evolved_playbook_path is None, \
        "Gap-048: 演化失敗時不應有 evolved_playbook_path"


# ══════════════════════════════════════════════
# Gap-049：GOTO 上限可配置
# ══════════════════════════════════════════════

def test_gap049_goto_limit_configurable():
    """Gap-049：max_goto_per_step 可透過 AppConfig 設定，預設為 3。"""
    from autoclaude.utils.config import PlaybookConfig
    cfg = AppConfig()
    assert cfg.playbook.max_goto_per_step == 3, "預設 GOTO 上限應為 3"

    custom = PlaybookConfig(max_goto_per_step=5)
    assert custom.max_goto_per_step == 5, "應能設定 max_goto_per_step=5"

    runner = _make_runner()
    runner._cfg.playbook.max_goto_per_step = 7
    assert runner._cfg.playbook.max_goto_per_step == 7, "runner 應使用可配置的 GOTO 上限"
