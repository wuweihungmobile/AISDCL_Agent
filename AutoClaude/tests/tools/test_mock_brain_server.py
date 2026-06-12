"""tests/tools/test_mock_brain_server.py — 紀律 #4「驗證鏡子自身要被驗證」。

mock_brain_server 是外部 LLM API 的測試替身；其回應契約必須與
autoclaude/decision/minimax_client.py:_parse_response（choices[0].message.content
= JSON 字串）+ models/decision.py 的 schema 對齊，否則本機 e2e 假綠。

涵蓋：
  - envelope 形狀與 minimax_client._parse_response 契約一致
  - correction 決策可被 CorrectionDecision 解析且過 Hallucination Guard
  - is_achieved system → GoalAchievementDecision
  - evolution_type system → EvolutionDecision
  - 連續請求 correction_prompt 變化（不被相似度門檻誤殺）
"""
from __future__ import annotations

import json

from autoclaude.decision.minimax_client import _validate_correction_quality
from autoclaude.models.decision import (
    CorrectionDecision,
    EvolutionDecision,
    GoalAchievementDecision,
)
from tools.mock_brain_server import _envelope, build_decision


def _content(payload: dict) -> dict:
    """走完整路徑：build → envelope → 模擬 client 解析 content。"""
    env = _envelope(build_decision(payload))
    content = env["choices"][0]["message"]["content"]  # 對齊 _parse_response
    return json.loads(content)


def test_envelope_shape_matches_client_contract() -> None:
    env = _envelope(build_decision({"messages": []}))
    # minimax_client._parse_response: data["choices"][0]["message"]["content"]
    assert isinstance(env["choices"][0]["message"]["content"], str)
    json.loads(env["choices"][0]["message"]["content"])  # 必為合法 JSON


def test_correction_decision_parses_and_passes_guard() -> None:
    payload = {"messages": [{"role": "system", "content": "輸出修正 JSON"}]}
    data = _content(payload)
    decision = CorrectionDecision.model_validate(data)
    ok, reason = _validate_correction_quality(decision.correction_prompt, [])
    assert ok is True, reason


def test_goal_validation_detected() -> None:
    payload = {"messages": [{"role": "system", "content": 'JSON Schema: "is_achieved": ...'}]}
    data = _content(payload)
    decision = GoalAchievementDecision.model_validate(data)
    assert decision.is_achieved is True


def test_evolution_detected() -> None:
    payload = {"messages": [{"role": "system", "content": 'JSON Schema: "evolution_type": ...'}]}
    data = _content(payload)
    decision = EvolutionDecision.model_validate(data)
    assert decision.evolution_type == "INJECT_STEP"
    assert decision.new_step_id == "T00_PRE"


def test_post_non_utf8_body_returns_400() -> None:
    """P2 修復：非 UTF-8 / 非 JSON body 應回 400（而非未捕捉 decode 例外致 500）。"""
    import http.client
    import threading
    from http.server import ThreadingHTTPServer

    from tools.mock_brain_server import _Handler

    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("POST", "/v1/chat/completions", body=b"\xff\xfe\x00not-utf8")
        resp = conn.getresponse()
        assert resp.status == 400
    finally:
        srv.shutdown()
        srv.server_close()


def test_consecutive_corrections_differ() -> None:
    payload = {"messages": [{"role": "system", "content": "輸出修正 JSON"}]}
    p1 = _content(payload)["correction_prompt"]
    p2 = _content(payload)["correction_prompt"]
    assert p1 != p2
    # 第二次相對第一次仍須過相似度門檻（< 0.90）
    ok, reason = _validate_correction_quality(p2, [p1])
    assert ok is True, reason
