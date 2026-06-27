"""tests/tools/test_correction_loop_verify.py — improving_87 W-87-1 載具自身驗證。

紀律 #4「驗證鏡子自身要被驗證」：correction_loop_verify 的 log 解析（RTM-87-1/3）與
mock_brain_server 的 /stats 計數（RTM-87-2）是 self-correction 閉環真跑判定的依據，
其邏輯必須以確定性合成輸入單元測，否則真跑誤判（假綠 / 假紅）。

涵蓋：
  - parse_correction_evidence 正確數 CORRECTION marker（RTM-87-1）
  - parse_correction_evidence 區分 success / escalation 兩態（RTM-87-3 誠實兩態）
  - 無 marker / 無結果行時的退化行為（不臆測）
  - mock_brain_server /stats 隨 POST 累計 post_count 與 decision_types（RTM-87-2）
"""
from __future__ import annotations

import http.client
import json
import threading
from http.server import ThreadingHTTPServer

from tools.correction_loop_verify import parse_correction_evidence

# --- 合成 log 片段（對齊 kernel.py:255-258 marker 與 main.py:140 結果行）---------------

_CORRECTION_MARKER = "2026-06-27 10:00:01 [INFO] autoclaude: === STATE: CORRECTION | step=S02 attempt=2 ==="
_RESULT_SUCCESS = (
    "2026-06-27 10:00:09 [INFO] autoclaude: Playbook 結束 | "
    "KernelResult(success=True, completed_steps=2, total_steps=2, escalated=False)"
)
_RESULT_FAIL_ESCALATED = (
    "2026-06-27 10:00:09 [INFO] autoclaude: Playbook 結束 | "
    "KernelResult(success=False, completed_steps=1, total_steps=2, "
    "reason='max_retries_exhausted: 評估指令失敗', escalated=True)"
)


def test_parse_correction_evidence_counts_markers() -> None:
    """RTM-87-1：每出現一次 CORRECTION marker 即計數一次（Brain 真被呼叫的唯一發 marker 路徑）。"""
    log = "\n".join(["...preamble...", _CORRECTION_MARKER, "...retry...", _RESULT_SUCCESS])
    ev = parse_correction_evidence(log)
    assert ev["correction_count"] == 1
    assert ev["final_success"] is True
    assert ev["escalated"] is False


def test_parse_correction_evidence_counts_multiple_markers() -> None:
    """多次 attempt → 多個 marker，計數須累加（不去重）。"""
    m1 = _CORRECTION_MARKER
    m2 = _CORRECTION_MARKER.replace("attempt=2", "attempt=3")
    log = "\n".join([m1, m2, _RESULT_SUCCESS])
    assert parse_correction_evidence(log)["correction_count"] == 2


def test_parse_correction_evidence_detects_escalation() -> None:
    """RTM-87-3 誠實兩態：達 max_retries 誠實 escalate（success=False / escalated=True），不虛報成功。"""
    log = "\n".join([_CORRECTION_MARKER, _CORRECTION_MARKER, _RESULT_FAIL_ESCALATED])
    ev = parse_correction_evidence(log)
    assert ev["correction_count"] == 2
    assert ev["final_success"] is False
    assert ev["escalated"] is True


def test_parse_correction_evidence_no_result_line_returns_none() -> None:
    """無結果行時 final_success 留 None（誠實：不臆測成功）。"""
    ev = parse_correction_evidence("only preamble, no markers, no result")
    assert ev["correction_count"] == 0
    assert ev["final_success"] is None
    assert ev["escalated"] is False
    assert ev["regex_contract_preserved"] == 0


_REGEX_PRESERVED_MARKER = (
    "2026-06-27 10:00:03 [INFO] autoclaude: === REGEX CONTRACT PRESERVED | step=S02 ==="
)


def test_parse_counts_regex_contract_preserved() -> None:
    """RTM-90-3：parse 正確計數 `REGEX CONTRACT PRESERVED` marker（improving_90 W-90-2：Kernel
    在 regex+evaluator 雙閘 step 套用 CORRECTION 後仍保留 regex 約束的唯一路徑 → >=1 即證
    DEF-87-001 修復在真模型迴圈被觸發）。"""
    log = "\n".join([_CORRECTION_MARKER, _REGEX_PRESERVED_MARKER, _RESULT_SUCCESS])
    ev = parse_correction_evidence(log)
    assert ev["regex_contract_preserved"] == 1
    assert ev["correction_count"] == 1
    assert ev["final_success"] is True
    # 既有三欄位語意不退化（RTM-90-4 additive）：無此 marker 時計數為 0
    assert parse_correction_evidence(_RESULT_SUCCESS)["regex_contract_preserved"] == 0


def test_parse_uses_last_result_line() -> None:
    """多筆 Playbook 結束時，以最後一筆判定（避免被前段殘留結果誤導）。"""
    log = "\n".join([_RESULT_FAIL_ESCALATED, _CORRECTION_MARKER, _RESULT_SUCCESS])
    ev = parse_correction_evidence(log)
    assert ev["final_success"] is True
    assert ev["escalated"] is False


# --- mock_brain_server /stats（RTM-87-2 Brain 端互動客觀觀測）---------------------------


def _start_mock_server() -> tuple[ThreadingHTTPServer, int]:
    # 每測試獨立 server 實例（_STATS 為模組級，故同程序須留意；本測試以單次序列驗證計數遞增）
    from tools.mock_brain_server import _Handler

    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


def _post_correction(port: int) -> None:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    body = json.dumps({"messages": [{"role": "system", "content": "輸出修正 JSON"}]})
    conn.request("POST", "/v1/chat/completions", body=body.encode("utf-8"))
    assert conn.getresponse().status == 200


def _get_stats(port: int) -> dict:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", "/stats")
    resp = conn.getresponse()
    assert resp.status == 200
    return json.loads(resp.read().decode("utf-8"))


def test_mock_server_stats_counts_posts() -> None:
    """RTM-87-2：/stats.post_count 隨 POST 累計，decision_types 記錄型別（Brain 端互動客觀觀測）。"""
    import tools.mock_brain_server as mbs

    # 重置模組級計數，避免與其他測試的同程序 POST 串擾（顯式隔離）。
    mbs._STATS["post_count"] = 0
    mbs._STATS["decision_types"] = []

    srv, port = _start_mock_server()
    try:
        before = _get_stats(port)["post_count"]
        _post_correction(port)
        _post_correction(port)
        after = _get_stats(port)
        assert after["post_count"] == before + 2
        assert after["decision_types"][-2:] == ["correction", "correction"]
    finally:
        srv.shutdown()
        srv.server_close()


def test_stats_endpoint_separate_from_health() -> None:
    """/health 與 /stats 各自獨立回應（/stats 不影響既有 /health 契約）。"""
    srv, port = _start_mock_server()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/health")
        resp = conn.getresponse()
        assert resp.status == 200
        assert json.loads(resp.read().decode("utf-8"))["status"] == "ok"
    finally:
        srv.shutdown()
        srv.server_close()
