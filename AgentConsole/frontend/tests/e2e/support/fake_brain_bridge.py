"""E2E 用：以「假 Brain」啟動 Engine Bridge（其餘與正式啟動完全相同）。

為什麼需要：匯入路徑 C（高階目標拆解）要真 Brain（MINIMAX_API_KEY＋MiniMax 服務），E2E 環境沒有。
本檔只替換 `brain_factory`，讓「後端 → 真 Bridge 的 /autoclaude/decompose 與草案 approve」兩段整合
也能在 E2E 驗證（Bridge 自己的三道有界閘、草案存檔、approver 硬閘都是真的；只有「拆解出什麼」是假的）。

假 Brain 依目標文字裡的標記回不同的拆解結果（沒有標記＝三步驟的正常鏈）：
  GATE_NONE  → 不回結果（Bridge：brain_failed）
  GATE_MAX   → 25 個步驟（max_steps 閘）
  GATE_CYCLE → S01 與 S02 互相依賴（cycle 閘）
  GATE_EMPTY → 第二步的 prompt 全空白（empty_prompt 閘）

啟動（環境與 README〈真 Bridge specs〉的 Bridge 相同；Bridge 套件已裝進根層 .venv，所以任何目錄都能 import app）：
    uvicorn --app-dir <本檔所在目錄> fake_brain_bridge:app --host 127.0.0.1 --port 18081
"""
from __future__ import annotations

from app.main import create_app
from autoclaude.core.ports.brain import BrainCapabilities, RetryPolicy
from autoclaude.models.decision import DecompositionDecision, DecompositionStep


def _step(i: int, deps: list[str] | None = None, prompt: str | None = None,
          evaluator: str | None = None) -> DecompositionStep:
    return DecompositionStep(
        step_id=f"S{i:02d}", name=f"步驟 {i}", depends_on=deps or [],
        prompt=f"請輸出 [S{i}_DONE]" if prompt is None else prompt, evaluator_command=evaluator)


class QaBrain:
    """最小的 IBrain：只有目標拆解用得到的兩個方法。"""

    def capabilities(self) -> BrainCapabilities:
        return BrainCapabilities(max_context_tokens=1000, supports_streaming=False,
                                 retry_policy=RetryPolicy(), model_id="qa-fake-brain",
                                 dimension=8, supports_decomposition=True)

    def decide_decomposition(self, *, goal: str, context: str = "") -> DecompositionDecision | None:
        if "GATE_NONE" in goal:
            return None
        if "GATE_MAX" in goal:
            steps = [_step(i) for i in range(1, 26)]
        elif "GATE_CYCLE" in goal:
            steps = [_step(1, ["S02"]), _step(2, ["S01"])]
        elif "GATE_EMPTY" in goal:
            steps = [_step(1), _step(2, ["S01"], prompt="   ")]
        else:
            steps = [_step(1), _step(2, ["S01"], evaluator="python --version"), _step(3, ["S02"])]
        return DecompositionDecision(steps=steps, reasoning="QA 假 Brain 的拆解理由")


app = create_app(brain_factory=lambda _settings: QaBrain())
