# SD_07 W2 Brain/Executor e2e Samples

5 種失敗情境 fixture，供 `tests/integration/test_brain_executor_e2e.py`（W2）
以參數化方式驅動 OrchestrationCoordinator + BrainPort + ExecutorPort 完整往返。

對應 ADR-SD07-001 議題 0：Minimax/Claude Code 完美協作驗證。

| 檔案 | 情境 | 預期觸發 phase | 對應 AC |
|------|------|----------------|---------|
| `token_halt.yaml` | Claude Code context 達 90% → 觸發 /compact + checkpoint | BEFORE_EXEC → EXEC → ON_TOKEN_HALT → ON_CHECKPOINT_SAVE_REQUEST | AC0-1 |
| `esc_f12_interrupt.yaml` | 使用者 ESC+F12 中斷 → CheckpointPlugin 儲存 → restart | EXEC → ON_INTERRUPT_REQUEST → ON_CHECKPOINT_SAVE_REQUEST | AC0-3 |
| `decide_correction.yaml` | 步驟失敗 → Brain decide_correction → ExecutorPort.execute(on_event) | AFTER_EXEC → DECIDE → BEFORE_EXEC → EXEC | AC0-2 |
| `decide_escalation.yaml` | 重試耗盡 → Brain decide_escalation → EvolutionPlugin | AFTER_EXEC → ON_ESCALATION → ON_ESCALATION_DUMP_REQUEST | AC0-2 |
| `dry_run_mode.yaml` | dry_run 模式完整 phase 序驗證；不呼叫真實 Brain/Executor | 全部 phase（含 capabilities() cache）| AC0-1~AC0-3 |

## 使用方式

```python
from pathlib import Path
import pytest, yaml

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sd07_e2e_samples"

@pytest.mark.parametrize(
    "fixture_name", ["token_halt", "esc_f12_interrupt", "decide_correction",
                     "decide_escalation", "dry_run_mode"]
)
def test_brain_executor_e2e(fixture_name):
    spec = yaml.safe_load((FIXTURE_DIR / f"{fixture_name}.yaml").read_text())
    # 走 OrchestrationCoordinator + KernelResult 比對
    ...
```

## Fixture 結構

每個 fixture 為單一 step playbook，含：

- `playbook`：標準 Playbook YAML（global_goal / global_invariants / tasks）
- `brain_decisions`：Brain 預定回傳序列（capabilities + decide_correction/escalation）
- `executor_events`：Executor 預定 emit 的事件序列（ExecutionEvent）
- `expected_phases`：期望 EventBus 廣播的 KernelPhase 序列
- `expected_kernel_result`：期望最終 KernelResult 欄位（success / halted / scheduled_resume_at / ...）
