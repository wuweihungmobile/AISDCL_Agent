"""mock_brain_server.py — 高擬真本地 Brain（Minimax/LLM）Mock 伺服器。

用途（對應「四、建立高擬真的 API 與 AI 模型模擬」）：
  - 在本機把外部 LLM（Minimax）API Mock 起來，給定可控回傳值測試系統邏輯，
    避免連正式環境（成本高 + 網路波動造成誤判）。
  - 回應採 **OpenAI-compatible chat completions** 格式
    （choices[0].message.content = 一段 JSON 字串），與 autoclaude/decision/
    minimax_client.py:_parse_response 的契約完全一致，故本機亦可直接指向
    vLLM / llama.cpp / Ollama 的 /v1/chat/completions（同一格式）。

接線（擇一）：
  config.yaml:
    minimax:
      base_url: "http://localhost:9100/v1/chat/completions"
      api_key: "mock"
  或環境變數：
    MINIMAX_BASE_URL=http://localhost:9100/v1/chat/completions
    MINIMAX_API_KEY=mock

啟動：
  python tools/mock_brain_server.py --port 9100
  curl -s http://localhost:9100/health           # → {"status":"ok"}

決策型別判定：以 system prompt 內 JSON Schema 關鍵字辨識（對齊 prompt_builder.py）：
  含 "is_achieved"   → GoalAchievementDecision
  含 "evolution_type"→ EvolutionDecision
  其餘                → CorrectionDecision（預設）

回傳的 correction_prompt 刻意滿足 minimax_client 的 Hallucination Guard：
  >= 50 字元 / 含具體引用（.py / line N）/ 每次請求變化（避免相似度門檻誤殺）。

注意：本伺服器為**確定性測試替身**，非真模型；需真模型推理請改用 vLLM/llama.cpp
（見 docker-compose.llm.yml + docs/08_deployment/Local_CI_Parity_Guide.md）。
"""
from __future__ import annotations

import argparse
import itertools
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# 請求序號 → 讓 correction_prompt 每次不同，繞過相似度幻覺防護
_COUNTER = itertools.count(1)


def _system_prompt(payload: dict) -> str:
    """取出 messages 中 role=system 的 content（找不到回空字串）。"""
    for msg in payload.get("messages", []):
        if msg.get("role") == "system":
            return str(msg.get("content", ""))
    return ""


def build_decision(payload: dict) -> dict:
    """依 system prompt 判定決策型別，回傳對應的決策 dict（將被序列化成 content 字串）。"""
    system = _system_prompt(payload)
    n = next(_COUNTER)

    if "is_achieved" in system:
        # GoalAchievementDecision — 預設判定已達成（讓本機 e2e 順利收斂）
        return {
            "is_achieved": True,
            "completion_prompt": "",
            "gap_analysis": "",
            "suggested_evaluator": None,
        }

    if "evolution_type" in system:
        # EvolutionDecision — 預設提議注入一個前置環境步驟
        return {
            "evolution_type": "INJECT_STEP",
            "reasoning": f"[mock #{n}] 偵測到缺少前置依賴，建議注入環境準備步驟。",
            "new_step_id": "T00_PRE",
            "new_step_name": "Mock 環境前置準備",
            "new_step_prompt": (
                "請先安裝缺少的依賴並建立必要的測試 fixture，"
                "確認 import 無誤後再重跑目標測試。"
            ),
            "split_context_bridge": "",
            "revised_evaluator": None,
        }

    # CorrectionDecision（預設）— correction_prompt 須過 Hallucination Guard
    correction_prompt = (
        f"[mock correction #{n}] 根據失敗輸出，請修正目標檔案中的錯誤："
        f"檢查相關 .py 模組於 line {20 + n} 的 assert 條件與回傳值是否一致，"
        "補上缺少的 import 後，重新執行單元測試直到通過。"
    )
    return {
        "correction_prompt": correction_prompt,
        "reasoning": f"[mock #{n}] 確定性測試替身回傳的修正建議。",
        "task_goal_summary": "讓目標測試全數通過",
        "step_mutation": None,
    }


def _envelope(decision: dict) -> dict:
    """包成 OpenAI-compatible chat completions 回應（content 為 JSON 字串）。"""
    return {
        "id": "mock-brain-0001",
        "object": "chat.completion",
        "model": "mock-brain",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": json.dumps(decision, ensure_ascii=False)},
                "finish_reason": "stop",
            }
        ],
    }


class _Handler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, body: dict) -> None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802 (stdlib 介面命名)
        if self.path.rstrip("/") == "/health":
            self._send_json(200, {"status": "ok", "server": "mock_brain_server"})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            # 非 UTF-8 / 非 JSON body → 回 400（而非未捕捉 decode 例外致 500）
            self._send_json(400, {"error": "invalid json or non-utf-8 body"})
            return
        decision = build_decision(payload)
        self._send_json(200, _envelope(decision))

    def log_message(self, *args) -> None:  # 靜音預設 access log
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="AutoClaude 本地 Brain Mock 伺服器")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9100)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), _Handler)
    print(f"[mock_brain_server] listening on http://{args.host}:{args.port} "
          f"(POST /v1/chat/completions, GET /health)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[mock_brain_server] 停止")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
