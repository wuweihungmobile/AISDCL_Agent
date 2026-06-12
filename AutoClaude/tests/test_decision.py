"""決策層單元測試（Playbook 修正模式）。"""
import json
import pytest
import httpx
from unittest.mock import MagicMock, patch

from autoclaude.models.decision import CorrectionDecision
from autoclaude.decision.minimax_client import MinimaxClient, MinimaxError


def _make_client() -> MinimaxClient:
    return MinimaxClient(
        api_key="test_key",
        base_url="https://example.com/v1",
        model="test-model",
        timeout=5,
    )


def _mock_response(payload: dict) -> dict:
    return {
        "choices": [{
            "message": {
                "content": json.dumps(payload),
            }
        }]
    }


def test_decide_correction_returns_decision():
    client = _make_client()
    with patch("httpx.post") as mock_post:
        mock_post.return_value.json.return_value = _mock_response({
            "correction_prompt": "請修正 line 12 的 IndentationError",
            "reasoning": "縮排錯誤",
        })
        mock_post.return_value.raise_for_status = MagicMock()
        decision = client.decide_correction(
            step_id="T01",
            task_name="implement",
            task_prompt="please implement foo",
            expected_regex=r"\[DONE\]",
            failure_reason="regex 不符合",
            eval_output="IndentationError at line 12",
            retry_count=1,
        )
    assert isinstance(decision, CorrectionDecision)
    assert "line 12" in decision.correction_prompt


def test_decide_correction_raises_on_invalid_json():
    client = _make_client()
    with patch("httpx.post") as mock_post:
        mock_post.return_value.json.return_value = {
            "choices": [{"message": {"content": "not json"}}]
        }
        mock_post.return_value.raise_for_status = MagicMock()
        with pytest.raises(MinimaxError):
            client.decide_correction(
                step_id="T01", task_name="x", task_prompt="p",
                expected_regex=None, failure_reason="r",
                eval_output="o", retry_count=1,
            )


def test_raises_when_api_key_empty():
    with pytest.raises(MinimaxError):
        MinimaxClient(api_key="", base_url="x", model="x", timeout=5)


def test_correction_decision_model_default():
    cd = CorrectionDecision(correction_prompt="fix it")
    assert cd.correction_prompt == "fix it"
    assert cd.reasoning == ""


def test_decide_correction_passes_convergence_hint_to_prompt():
    """history_summary 與 convergence_trend/reasoning 應出現在送出的 HTTP payload 中。"""
    client = _make_client()
    captured_payload: dict = {}

    def fake_post(_url, json=None, **kwargs):
        captured_payload.update(json or {})
        mock_resp = MagicMock()
        mock_resp.json.return_value = _mock_response({
            "correction_prompt": "fix it",
            "reasoning": "因為 stuck",
        })
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch("httpx.post", side_effect=fake_post):
        client.decide_correction(
            step_id="T01",
            task_name="step1",
            task_prompt="do something",
            expected_regex=r"\[DONE\]",
            failure_reason="fail",
            eval_output="SyntaxError at line 5",
            retry_count=2,
            history_summary="### 歷次失敗\n- Attempt 0: sig=X",
            convergence_trend="stuck",
            convergence_reasoning="特徵碼連續相同且無數量改善",
        )

    user_content = captured_payload["messages"][1]["content"]
    assert "歷次失敗" in user_content                    # history_summary 已帶入
    assert "收斂評估" in user_content                    # convergence hint
    assert "stuck" in user_content                       # trend 已帶入
    assert "特徵碼連續相同" in user_content              # reasoning 已帶入


def test_decide_correction_includes_test_file_hint_in_prompt():
    """eval_output 含 test_ 開頭檔案的 SyntaxError 時，Minimax prompt 應包含測試檔警告。"""
    client = _make_client()
    captured_payload: dict = {}

    def fake_post(_url, json=None, **kwargs):
        captured_payload.update(json or {})
        mock_resp = MagicMock()
        mock_resp.json.return_value = _mock_response({
            "correction_prompt": "修正 test_foo.py 語法錯誤",
            "reasoning": "測試檔有問題",
        })
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch("httpx.post", side_effect=fake_post):
        client.decide_correction(
            step_id="T01",
            task_name="run tests",
            task_prompt="pytest",
            expected_regex=None,
            failure_reason="regex 不符",
            eval_output="ERROR collecting tests/test_foo.py SyntaxError: invalid syntax",
            retry_count=0,
        )

    user_content = captured_payload["messages"][1]["content"]
    assert "test_" in user_content           # 測試檔警告已注入
    assert "測試檔" in user_content          # 中文警告存在


def test_decide_correction_strategy_hint_in_prompt():
    """strategy_hint 非空時，應注入到 Minimax 的 user message。"""
    client = _make_client()
    captured_payload: dict = {}

    def fake_post(_url, json=None, **kwargs):
        captured_payload.update(json or {})
        mock_resp = MagicMock()
        mock_resp.json.return_value = _mock_response({
            "correction_prompt": "嘗試重構",
            "reasoning": "策略切換",
        })
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch("httpx.post", side_effect=fake_post):
        client.decide_correction(
            step_id="T01",
            task_name="step1",
            task_prompt="do it",
            expected_regex=None,
            failure_reason="fail",
            eval_output="AssertionError",
            retry_count=2,
            strategy_hint="請嘗試完全不同的方法",
        )

    user_content = captured_payload["messages"][1]["content"]
    assert "策略切換指令" in user_content
    assert "請嘗試完全不同的方法" in user_content


def test_decide_correction_no_hint_when_trend_empty():
    """convergence_trend 為空時不應插入收斂評估 hint。"""
    client = _make_client()
    captured_payload: dict = {}

    def fake_post(_url, json=None, **kwargs):
        captured_payload.update(json or {})
        mock_resp = MagicMock()
        mock_resp.json.return_value = _mock_response({
            "correction_prompt": "fix",
            "reasoning": "",
        })
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch("httpx.post", side_effect=fake_post):
        client.decide_correction(
            step_id="T01", task_name="n", task_prompt="p",
            expected_regex=None, failure_reason="f",
            eval_output="error", retry_count=0,
            convergence_trend="",
        )

    user_content = captured_payload["messages"][1]["content"]
    assert "收斂評估" not in user_content


# ──────────────────────────────────────────────
# MinimaxClient 退避重試測試（Gap-MR）
# ──────────────────────────────────────────────

def test_decide_correction_retries_on_500_then_succeeds():
    """API 前 2 次回傳 500，第 3 次成功 → 應返回 decision，而非 raise。"""
    client = _make_client()
    call_count = 0

    def fake_post(_url, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_resp = MagicMock()
        if call_count < 3:
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "500 Server Error",
                request=MagicMock(),
                response=MagicMock(status_code=500, text="Internal Server Error"),
            )
        else:
            mock_resp.json.return_value = _mock_response({
                "correction_prompt": "retry success",
                "reasoning": "ok on third try",
            })
            mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch("httpx.post", side_effect=fake_post), patch("time.sleep"):
        decision = client.decide_correction(
            step_id="T01", task_name="x", task_prompt="p",
            expected_regex=None, failure_reason="r",
            eval_output="o", retry_count=1,
        )

    assert decision.correction_prompt == "retry success"
    assert call_count == 3


def test_decide_correction_raises_after_all_retries_exhausted():
    """連續 3 次失敗後應 raise MinimaxError，而非靜默忽略。"""
    client = _make_client()

    def fake_post(_url, **kwargs):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500, text="Server Error"),
        )
        return mock_resp

    with patch("httpx.post", side_effect=fake_post), patch("time.sleep"):
        with pytest.raises(MinimaxError):
            client.decide_correction(
                step_id="T01", task_name="x", task_prompt="p",
                expected_regex=None, failure_reason="r",
                eval_output="o", retry_count=1,
            )


def test_decide_correction_retries_exactly_max_times():
    """驗證重試次數恰好等於 _MAX_API_RETRIES（3）。"""
    client = _make_client()
    call_count = 0

    def fake_post(_url, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "503", request=MagicMock(),
            response=MagicMock(status_code=503, text="Service Unavailable"),
        )
        return mock_resp

    with patch("httpx.post", side_effect=fake_post), patch("time.sleep"):
        with pytest.raises(MinimaxError):
            client.decide_correction(
                step_id="T01", task_name="x", task_prompt="p",
                expected_regex=None, failure_reason="r",
                eval_output="o", retry_count=1,
            )

    assert call_count == 3  # 等於 _MAX_API_RETRIES


def test_decide_correction_retries_on_429_rate_limit():
    """HTTP 429 Rate Limit 應觸發退避重試，最終成功。"""
    client = _make_client()
    call_count = 0

    def fake_post(_url, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_resp = MagicMock()
        if call_count < 3:
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "429 Too Many Requests",
                request=MagicMock(),
                response=MagicMock(status_code=429, text="Rate limit exceeded"),
            )
        else:
            mock_resp.json.return_value = _mock_response({
                "correction_prompt": "rate limit retry success",
                "reasoning": "ok after rate limit",
            })
            mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch("httpx.post", side_effect=fake_post), patch("time.sleep"):
        decision = client.decide_correction(
            step_id="T01", task_name="x", task_prompt="p",
            expected_regex=None, failure_reason="r",
            eval_output="o", retry_count=1,
        )

    assert decision.correction_prompt == "rate limit retry success"
    assert call_count == 3


# ──────────────────────────────────────────────
# ErrorClass 整合場景測試（error_class 傳遞鏈驗證）
# ──────────────────────────────────────────────

def test_decide_correction_environment_error_class_hint_in_prompt():
    """eval_output 含 FileNotFoundError 時，error_class='environment' 提示應注入 Minimax user message。"""
    client = _make_client()
    captured_payload: dict = {}

    def fake_post(_url, json=None, **kwargs):
        captured_payload.update(json or {})
        mock_resp = MagicMock()
        mock_resp.json.return_value = _mock_response({
            "correction_prompt": "check environment",
            "reasoning": "env error",
        })
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch("httpx.post", side_effect=fake_post):
        client.decide_correction(
            step_id="T01",
            task_name="step1",
            task_prompt="run tests",
            expected_regex=None,
            failure_reason="FileNotFoundError",
            eval_output="FileNotFoundError: config.yaml not found",
            retry_count=1,
            error_class="environment",
        )

    user_content = captured_payload["messages"][1]["content"]
    assert "環境錯誤" in user_content
    assert "人工介入" in user_content


def test_decide_correction_syntax_error_class_hint_in_prompt():
    """error_class='syntax' 時，Minimax user message 應包含語法錯誤提示。"""
    client = _make_client()
    captured_payload: dict = {}

    def fake_post(_url, json=None, **kwargs):
        captured_payload.update(json or {})
        mock_resp = MagicMock()
        mock_resp.json.return_value = _mock_response({
            "correction_prompt": "fix syntax",
            "reasoning": "syntax error",
        })
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch("httpx.post", side_effect=fake_post):
        client.decide_correction(
            step_id="T01",
            task_name="step1",
            task_prompt="compile",
            expected_regex=None,
            failure_reason="SyntaxError",
            eval_output="SyntaxError: invalid syntax at line 10",
            retry_count=1,
            error_class="syntax",
        )

    user_content = captured_payload["messages"][1]["content"]
    assert "語法錯誤" in user_content


def test_decide_correction_import_error_class_hint_in_prompt():
    """error_class='import' 時，Minimax user message 應包含 Import 錯誤提示。"""
    client = _make_client()
    captured_payload: dict = {}

    def fake_post(_url, json=None, **kwargs):
        captured_payload.update(json or {})
        mock_resp = MagicMock()
        mock_resp.json.return_value = _mock_response({
            "correction_prompt": "check imports",
            "reasoning": "import error",
        })
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch("httpx.post", side_effect=fake_post):
        client.decide_correction(
            step_id="T01",
            task_name="step1",
            task_prompt="import modules",
            expected_regex=None,
            failure_reason="ImportError",
            eval_output="ImportError: cannot import name 'foo'",
            retry_count=1,
            error_class="import",
        )

    user_content = captured_payload["messages"][1]["content"]
    assert "Import 錯誤" in user_content


def test_decide_correction_unknown_error_class_no_hint():
    """error_class='unknown' 時，不應注入任何錯誤類型提示。"""
    client = _make_client()
    captured_payload: dict = {}

    def fake_post(_url, json=None, **kwargs):
        captured_payload.update(json or {})
        mock_resp = MagicMock()
        mock_resp.json.return_value = _mock_response({
            "correction_prompt": "fix it",
            "reasoning": "unknown",
        })
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch("httpx.post", side_effect=fake_post):
        client.decide_correction(
            step_id="T01",
            task_name="step1",
            task_prompt="do it",
            expected_regex=None,
            failure_reason="unknown error",
            eval_output="something went wrong",
            retry_count=1,
            error_class="unknown",
        )

    user_content = captured_payload["messages"][1]["content"]
    # 沒有語法/環境/Import 提示
    assert "語法錯誤" not in user_content
    assert "環境錯誤" not in user_content
    assert "Import 錯誤" not in user_content


# ──────────────────────────────────────────────
# Gap-008-D：Hallucination Guard 測試
# ──────────────────────────────────────────────

def test_validate_correction_quality_too_short():
    """correction_prompt 過短（< 50 字元）應返回 is_valid=False。"""
    from autoclaude.decision.minimax_client import _validate_correction_quality
    is_valid, reason = _validate_correction_quality("short msg", [])
    assert is_valid is False
    assert "過短" in reason


def test_validate_correction_quality_no_specific_reference():
    """correction_prompt 缺乏具體錯誤引用應返回 is_valid=False。"""
    from autoclaude.decision.minimax_client import _validate_correction_quality
    # 超過 50 字元，但沒有任何具體錯誤引用（無檔名/行號/函式名/錯誤類型）
    generic = (
        "Please try a different approach and ensure the logic is correct "
        "before running the tests again to verify the expected behavior."
    )
    is_valid, reason = _validate_correction_quality(generic, [])
    assert is_valid is False
    assert "具體錯誤引用" in reason


def test_validate_correction_quality_high_similarity():
    """與前次高度相似（Jaccard >= 90%）應返回 is_valid=False。"""
    from autoclaude.decision.minimax_client import _validate_correction_quality
    prompt = "請修正 line 12 的 AssertionError，assert result == 42 應改為 assert result == 0"
    is_valid, reason = _validate_correction_quality(prompt, [prompt])
    assert is_valid is False
    assert "相似" in reason


def test_validate_correction_quality_passes_good_prompt():
    """包含具體引用且長度足夠、無重複的 prompt 應通過驗證。"""
    from autoclaude.decision.minimax_client import _validate_correction_quality
    good = "請修正 test_foo.py:42 的 AssertionError：assert result == 10 失敗，實際值是 5。應修改 calculate() 函式的回傳邏輯。"
    is_valid, reason = _validate_correction_quality(good, [])
    assert is_valid is True
    assert reason == "ok"


def test_decide_correction_uses_last_correction_prompt_for_similarity():
    """last_correction_prompt 應作為相似度比對依據（而非 history_summary）。"""
    client = _make_client()
    # 第一次呼叫：回傳一個高品質 prompt
    first_prompt = "請修正 test_foo.py:42 的 AssertionError，assert result == 10 失敗，應修改 calculate()"

    with patch("httpx.post") as mock_post:
        mock_post.return_value.json.return_value = _mock_response({
            "correction_prompt": first_prompt,
            "reasoning": "修正 assertion",
        })
        mock_post.return_value.raise_for_status = MagicMock()
        decision = client.decide_correction(
            step_id="T01",
            task_name="test",
            task_prompt="pytest",
            expected_regex=None,
            failure_reason="fail",
            eval_output="AssertionError at line 42",
            retry_count=1,
            last_correction_prompt="完全不同的前次 prompt 內容",
        )
    assert decision.correction_prompt == first_prompt


# ──────────────────────────────────────────────
# Gap-011-A：Global Goal Anchor 測試
# ──────────────────────────────────────────────

def test_global_goal_appears_at_top_of_correction_message():
    """global_goal 非空時，應出現在 user message 的最頂端（系統總目標區段）。"""
    from autoclaude.decision.prompt_builder import build_correction_message
    msg = build_correction_message(
        step_id="T01",
        task_name="實作登入",
        task_prompt="實作 auth.py",
        expected_regex=r"\[DONE\]",
        failure_reason="assert 失敗",
        eval_output="AssertionError at line 5",
        retry_count=1,
        global_goal="建立一個符合 SDD 規格的 FastAPI JWT 驗證模組。",
    )
    # 應出現在訊息最前面
    assert msg.startswith("## 系統總目標")
    assert "FastAPI JWT" in msg


def test_global_goal_none_no_goal_section():
    """global_goal=None 時，訊息中不應出現「系統總目標」區段（向後相容）。"""
    from autoclaude.decision.prompt_builder import build_correction_message
    msg = build_correction_message(
        step_id="T01",
        task_name="n",
        task_prompt="p",
        expected_regex=None,
        failure_reason="fail",
        eval_output="SyntaxError at line 3",
        retry_count=0,
        global_goal=None,
    )
    assert "## 系統總目標" not in msg
    assert msg.startswith("## 失敗步驟")


def test_decide_correction_global_goal_in_user_message():
    """decide_correction 傳入 global_goal 時，應出現在 HTTP payload 的 user message 中。"""
    client = _make_client()
    captured_payload: dict = {}

    def fake_post(_url, json=None, **kwargs):
        captured_payload.update(json or {})
        mock_resp = MagicMock()
        mock_resp.json.return_value = _mock_response({
            "correction_prompt": "fix it",
            "reasoning": "goal aligned",
        })
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch("httpx.post", side_effect=fake_post):
        client.decide_correction(
            step_id="T01",
            task_name="step1",
            task_prompt="do it",
            expected_regex=None,
            failure_reason="fail",
            eval_output="SyntaxError at line 5",
            retry_count=1,
            global_goal="建立一個符合 SDD 規格的 FastAPI JWT 驗證模組。",
        )

    user_content = captured_payload["messages"][1]["content"]
    assert "系統總目標" in user_content
    assert "FastAPI JWT" in user_content


# ──────────────────────────────────────────────
# Gap-011-B：StepMutation 模型與 Schema 測試
# ──────────────────────────────────────────────

def test_step_mutation_model_revise_current():
    """StepMutation REVISE_CURRENT 應正確解析。"""
    from autoclaude.models.step_mutation import StepMutation, StepMutationType
    m = StepMutation(
        mutation_type=StepMutationType.REVISE_CURRENT,
        revised_prompt="新的步驟 prompt",
        reasoning="原 prompt 太寬泛",
    )
    assert m.mutation_type == StepMutationType.REVISE_CURRENT
    assert m.revised_prompt == "新的步驟 prompt"
    assert m.new_step_id is None


def test_step_mutation_model_inject_after():
    """StepMutation INJECT_AFTER 應正確解析。"""
    from autoclaude.models.step_mutation import StepMutation, StepMutationType
    m = StepMutation(
        mutation_type=StepMutationType.INJECT_AFTER,
        new_step_id="T02_FIX",
        new_step_name="修復輔助步驟",
        new_step_prompt="請修復測試環境",
        reasoning="需要先修復環境",
    )
    assert m.mutation_type == StepMutationType.INJECT_AFTER
    assert m.new_step_id == "T02_FIX"
    assert m.revised_prompt is None


def test_correction_decision_with_step_mutation_parsed():
    """CorrectionDecision 應能解析包含 step_mutation 的 JSON 回應。"""
    from autoclaude.models.decision import CorrectionDecision
    from autoclaude.models.step_mutation import StepMutationType
    data = {
        "correction_prompt": "fix it",
        "reasoning": "step design issue",
        "step_mutation": {
            "mutation_type": "REVISE_CURRENT",
            "revised_prompt": "更明確的步驟 prompt",
            "reasoning": "原 prompt 不夠具體",
        },
    }
    decision = CorrectionDecision.model_validate(data)
    assert decision.step_mutation is not None
    assert decision.step_mutation.mutation_type == StepMutationType.REVISE_CURRENT
    assert decision.step_mutation.revised_prompt == "更明確的步驟 prompt"


def test_correction_decision_step_mutation_null():
    """step_mutation=null 時，CorrectionDecision 應正常解析（向後相容）。"""
    from autoclaude.models.decision import CorrectionDecision
    data = {
        "correction_prompt": "fix it",
        "reasoning": "normal correction",
        "step_mutation": None,
    }
    decision = CorrectionDecision.model_validate(data)
    assert decision.step_mutation is None


def test_allow_step_mutation_false_no_schema_in_system_prompt():
    """allow_step_mutation=False 時，system prompt 不應包含 step_mutation schema（省 Token）。"""
    from autoclaude.decision.prompt_builder import build_correction_system_prompt
    prompt = build_correction_system_prompt(allow_step_mutation=False)
    assert "step_mutation" not in prompt
    assert "REVISE_CURRENT" not in prompt


def test_allow_step_mutation_true_adds_schema_to_system_prompt():
    """allow_step_mutation=True 時，system prompt 應包含 step_mutation schema。"""
    from autoclaude.decision.prompt_builder import build_correction_system_prompt
    prompt = build_correction_system_prompt(allow_step_mutation=True)
    assert "step_mutation" in prompt
    assert "REVISE_CURRENT" in prompt
    assert "INJECT_AFTER" in prompt


def test_decide_correction_with_step_mutation_response():
    """Minimax 回傳含 step_mutation 的 JSON 時，decision.step_mutation 應正確解析。"""
    client = _make_client()
    with patch("httpx.post") as mock_post:
        mock_post.return_value.json.return_value = _mock_response({
            "correction_prompt": "請修正 line 5 的 TypeError",
            "reasoning": "step 設計問題",
            "step_mutation": {
                "mutation_type": "REVISE_CURRENT",
                "revised_prompt": "請實作更簡單版本的 foo() 函式",
                "reasoning": "原 prompt 要求過多",
            },
        })
        mock_post.return_value.raise_for_status = MagicMock()
        decision = client.decide_correction(
            step_id="T01",
            task_name="implement",
            task_prompt="please implement foo",
            expected_regex=r"\[DONE\]",
            failure_reason="TypeError at line 5",
            eval_output="TypeError: foo() at line 5",
            retry_count=3,
            allow_step_mutation=True,
        )
    from autoclaude.models.step_mutation import StepMutationType
    assert decision.step_mutation is not None
    assert decision.step_mutation.mutation_type == StepMutationType.REVISE_CURRENT


# ──────────────────────────────────────────────
# Gap-036：Minimax schema 含評估欄位（INJECT 類型）
# ──────────────────────────────────────────────

def test_gap036_inject_before_schema_includes_evaluator_fields():
    """Gap-036：prompt_builder INJECT_BEFORE schema 包含 new_step_evaluator_command 等欄位。"""
    from autoclaude.decision.prompt_builder import _MUTATION_SCHEMA_SECTION
    assert "new_step_evaluator_command" in _MUTATION_SCHEMA_SECTION
    assert "new_step_expected_regex" in _MUTATION_SCHEMA_SECTION
    assert "new_step_max_retries" in _MUTATION_SCHEMA_SECTION


def test_gap036_inject_after_schema_includes_evaluator_fields():
    """Gap-036：prompt_builder INJECT_AFTER schema 同樣包含評估欄位。"""
    from autoclaude.decision.prompt_builder import _MUTATION_SCHEMA_SECTION
    inject_after_idx = _MUTATION_SCHEMA_SECTION.find("INJECT_AFTER")
    inject_before_idx = _MUTATION_SCHEMA_SECTION.find("INJECT_BEFORE")
    # 兩個 INJECT 類型的說明區塊都包含評估欄位
    assert inject_after_idx != -1
    assert inject_before_idx != -1


def test_gap036_decide_correction_with_inject_before_evaluator():
    """Gap-036：Minimax 回傳含評估欄位的 INJECT_BEFORE 能被正確解析。"""
    from autoclaude.models.step_mutation import StepMutationType
    client = _make_client()
    with patch("httpx.post") as mock_post:
        mock_post.return_value.json.return_value = _mock_response({
            "correction_prompt": "前置步驟已注入",
            "reasoning": "環境缺少 fastapi",
            "step_mutation": {
                "mutation_type": "INJECT_BEFORE",
                "new_step_id": "T01_PRE",
                "new_step_name": "安裝環境依賴",
                "new_step_prompt": "請執行 pip install fastapi 並確認安裝成功",
                "new_step_evaluator_command": "pip show fastapi && echo OK",
                "new_step_expected_regex": "OK",
                "new_step_max_retries": 2,
                "reasoning": "IMPORT error 需要前置安裝",
            },
        })
        mock_post.return_value.raise_for_status = MagicMock()
        decision = client.decide_correction(
            step_id="T01", task_name="build", task_prompt="build app",
            expected_regex=None, failure_reason="ImportError: fastapi",
            eval_output="ImportError: No module named fastapi", retry_count=2,
            allow_step_mutation=True,
        )
    assert decision.step_mutation is not None
    assert decision.step_mutation.mutation_type == StepMutationType.INJECT_BEFORE
    assert decision.step_mutation.new_step_evaluator_command == "pip show fastapi && echo OK"
    assert decision.step_mutation.new_step_expected_regex == "OK"
    assert decision.step_mutation.new_step_max_retries == 2


# ──────────────────────────────────────────────
# Gap-030：GoalAchievementDecision suggested_evaluator
# ──────────────────────────────────────────────

def test_gap030_goal_achievement_decision_has_suggested_evaluator():
    """Gap-030：GoalAchievementDecision 包含 suggested_evaluator 欄位。"""
    from autoclaude.models.decision import GoalAchievementDecision
    d = GoalAchievementDecision(
        is_achieved=False,
        completion_prompt="請補完整合測試",
        gap_analysis="缺少 integration test",
        suggested_evaluator="pytest tests/integration/ -v",
    )
    assert d.suggested_evaluator == "pytest tests/integration/ -v"


def test_gap030_goal_achievement_decision_suggested_evaluator_defaults_none():
    """Gap-030：GoalAchievementDecision.suggested_evaluator 預設為 None。"""
    from autoclaude.models.decision import GoalAchievementDecision
    d = GoalAchievementDecision(is_achieved=True)
    assert d.suggested_evaluator is None


def test_gap030_goal_validation_system_prompt_has_suggested_evaluator():
    """Gap-030：GOAL_VALIDATION_SYSTEM_PROMPT 包含 suggested_evaluator schema。"""
    from autoclaude.decision.prompt_builder import GOAL_VALIDATION_SYSTEM_PROMPT
    assert "suggested_evaluator" in GOAL_VALIDATION_SYSTEM_PROMPT


def test_gap030_validate_goal_achievement_returns_suggested_evaluator():
    """Gap-030：validate_goal_achievement 能解析含 suggested_evaluator 的 Minimax 回傳。"""
    from autoclaude.models.decision import GoalAchievementDecision
    client = _make_client()
    with patch("httpx.post") as mock_post:
        mock_post.return_value.json.return_value = _mock_response({
            "is_achieved": False,
            "completion_prompt": "請補完整合測試",
            "gap_analysis": "缺少 integration test",
            "suggested_evaluator": "pytest tests/integration/ -v",
        })
        mock_post.return_value.raise_for_status = MagicMock()
        result = client.validate_goal_achievement(
            global_goal="建立登入 API",
            step_summary="T01 完成",
            playbook_project="TestProject",
        )
    assert isinstance(result, GoalAchievementDecision)
    assert result.is_achieved is False
    assert result.suggested_evaluator == "pytest tests/integration/ -v"


# ──────────────────────────────────────────────
# Gap-032：mutation_pressure 偏置訊息
# ──────────────────────────────────────────────

def test_gap032_mutation_pressure_0_no_hint():
    """Gap-032：mutation_pressure=0 時不加入壓力提示。"""
    from autoclaude.decision.prompt_builder import build_correction_message
    msg = build_correction_message(
        step_id="T01", task_name="test", task_prompt="do it",
        expected_regex=None, failure_reason="fail", eval_output="error",
        retry_count=1, mutation_pressure=0,
    )
    assert "⚠️ 注意" not in msg
    assert "🚨 緊急" not in msg


def test_gap032_mutation_pressure_1_shows_warning():
    """Gap-032：mutation_pressure=1 時顯示注意提示。"""
    from autoclaude.decision.prompt_builder import build_correction_message
    msg = build_correction_message(
        step_id="T01", task_name="test", task_prompt="do it",
        expected_regex=None, failure_reason="fail", eval_output="error",
        retry_count=2, mutation_pressure=1,
    )
    assert "已有 1 次 correction 無效" in msg


def test_gap032_mutation_pressure_2_shows_strong_warning():
    """Gap-032：mutation_pressure=2 時顯示強烈建議。"""
    from autoclaude.decision.prompt_builder import build_correction_message
    msg = build_correction_message(
        step_id="T01", task_name="test", task_prompt="do it",
        expected_regex=None, failure_reason="fail", eval_output="error",
        retry_count=3, mutation_pressure=2,
    )
    assert "INJECT_BEFORE" in msg or "REVISE_CURRENT" in msg


def test_gap032_mutation_pressure_3_shows_emergency():
    """Gap-032：mutation_pressure>=3 時顯示緊急警告，禁止純 correction_prompt。"""
    from autoclaude.decision.prompt_builder import build_correction_message
    msg = build_correction_message(
        step_id="T01", task_name="test", task_prompt="do it",
        expected_regex=None, failure_reason="fail", eval_output="error",
        retry_count=4, mutation_pressure=3,
    )
    assert "🚨 緊急" in msg


def test_gap032_decide_correction_passes_mutation_pressure():
    """Gap-032：decide_correction 接受 mutation_pressure 參數。"""
    client = _make_client()
    with patch("httpx.post") as mock_post:
        mock_post.return_value.json.return_value = _mock_response({
            "correction_prompt": "請修正 ImportError，確認 requirements.txt 存在",
            "reasoning": "缺少依賴",
        })
        mock_post.return_value.raise_for_status = MagicMock()
        decision = client.decide_correction(
            step_id="T01", task_name="build", task_prompt="build",
            expected_regex=None, failure_reason="ImportError",
            eval_output="ImportError: fastapi", retry_count=3,
            mutation_pressure=2,
        )
    assert decision.correction_prompt != ""
