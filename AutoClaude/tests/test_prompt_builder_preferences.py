"""F-C1 偏好區段 — prompt_builder 與 MinimaxClient pass-through 測試
（QA audit P2-2 歸檔 + P2-4 中段兩跳補驗）。

驗證意圖：偏好區段必須 (a) 完整出現在 correction message 且位於失敗細節前；
(b) 經 MinimaxClient.decide_correction 真實傳遞至送往 LLM 的 user message
（堵「端到端止於 FakeBrain kwargs」的中段斷鏈）。
"""
from __future__ import annotations

from autoclaude.decision.prompt_builder import build_correction_message

_SECTION = "## 使用者偏好\n- report_format: json\n\n"


class TestPromptBuilderPreferencesSection:
    def test_section_inserted_before_failure_block(self):
        msg = build_correction_message(
            step_id="T01", task_name="t", task_prompt="p",
            expected_regex=None, failure_reason="f", eval_output="e",
            retry_count=1, preferences_section=_SECTION,
        )
        assert _SECTION in msg
        assert msg.index("## 使用者偏好") < msg.index("## 失敗步驟")

    def test_default_empty_keeps_message_unchanged(self):
        kwargs = dict(
            step_id="T01", task_name="t", task_prompt="p",
            expected_regex=None, failure_reason="f", eval_output="e",
            retry_count=1,
        )
        assert build_correction_message(**kwargs) == build_correction_message(
            **kwargs, preferences_section=""
        )


class TestMinimaxClientPassThrough:
    """P2-4：MinimaxClient.decide_correction → build_correction_message 中段傳遞。"""

    def _client_capturing(self, captured: dict):
        from autoclaude.decision.minimax_client import MinimaxClient

        client = MinimaxClient(
            api_key="test-key", base_url="http://localhost:9", model="test-model",
        )

        def _fake_call(system_prompt, user_msg):
            captured["user_msg"] = user_msg
            return {"correction_prompt": "fix", "reasoning": "r"}

        client._call_with_retry = _fake_call  # type: ignore[method-assign]
        return client

    def test_preferences_section_reaches_llm_user_message(self):
        captured: dict = {}
        client = self._client_capturing(captured)
        client.decide_correction(
            step_id="T01", task_name="t", task_prompt="p",
            expected_regex=None, failure_reason="f", eval_output="e",
            retry_count=1, preferences_section=_SECTION,
        )
        assert _SECTION in captured["user_msg"]

    def test_omitted_section_absent_from_user_message(self):
        captured: dict = {}
        client = self._client_capturing(captured)
        client.decide_correction(
            step_id="T01", task_name="t", task_prompt="p",
            expected_regex=None, failure_reason="f", eval_output="e",
            retry_count=1,
        )
        assert "## 使用者偏好" not in captured["user_msg"]
