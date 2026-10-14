"""SSE 斷線重播（PRD §7.1.7，at-least-once）：游標只收 > N；REST 回補與 SSE 同一批；格式合契約。"""
from __future__ import annotations

import httpx
import pytest

from tests.conftest import TERMINAL


def _finished_run(bridge, run_body) -> str:
    rid = bridge.post_run(run_body(delay="0.2")).json()["run_id"]
    bridge.wait_status(rid, {"COMPLETED"})
    return rid


def test_reconnect_with_a_cursor_only_delivers_newer_events(bridge, run_body) -> None:
    rid = _finished_run(bridge, run_body)
    everything = bridge.sse(rid)
    ids = [e["id"] for e in everything]
    assert ids == list(range(1, len(ids) + 1))
    cut = ids[len(ids) // 2]

    by_query = bridge.sse(rid, after=cut)
    by_header = bridge.sse(rid, last_event_id=cut)
    expected = [i for i in ids if i > cut]
    assert [e["id"] for e in by_query] == expected
    assert [e["id"] for e in by_header] == expected, "瀏覽器的 EventSource 重連走 Last-Event-ID"
    assert bridge.sse(rid, after=ids[-1]) == [], "游標已追上終態＝立刻結束、不再等"

    rest = bridge.events(rid, after=cut)
    assert [e["seq"] for e in rest] == expected, "REST 回補必須與 SSE 重播同一批"
    assert [e["event"] for e in rest] == [e["event"] for e in by_query]


def test_disconnecting_mid_run_and_reconnecting_loses_and_duplicates_nothing(
        bridge, run_body) -> None:
    rid = bridge.post_run(run_body(delay="0.6")).json()["run_id"]
    first = bridge.sse(rid, stop_after=6)                   # 還在跑的時候主動斷線
    assert len(first) == 6
    cut = first[-1]["id"]
    rest = bridge.sse(rid, last_event_id=cut)                # 重連，直到終態串流自行結束
    final = bridge.wait_status(rid, TERMINAL)
    got = [e["id"] for e in first] + [e["id"] for e in rest]
    assert got == list(range(1, final["last_event_seq"] + 1))
    assert rest[-1]["event"] == "status"
    assert rest[-1]["data"]["status"] == "COMPLETED"


def test_the_larger_of_after_and_last_event_id_wins(bridge, run_body) -> None:
    rid = _finished_run(bridge, run_body)
    total = len(bridge.sse(rid))
    got = bridge.sse(rid, after=1, last_event_id=total - 1)
    assert [e["id"] for e in got] == [total]


def test_sse_frames_match_the_contract_shapes(bridge, run_body) -> None:
    rid = _finished_run(bridge, run_body)
    by_type: dict[str, dict] = {}
    for e in bridge.sse(rid):
        by_type.setdefault(e["event"], e["data"])
    assert set(by_type) >= {"log", "status", "step", "token"}
    assert set(by_type["log"]) == {"seq", "ts", "level", "line"}
    assert set(by_type["status"]) == {"seq", "ts", "status", "reason"}
    assert {"seq", "ts", "step_id", "step_number", "status", "attempt"} <= set(by_type["step"])
    assert set(by_type["token"]) == {"seq", "ts", "pct", "tokens_used"}
    everything = bridge.sse(rid)
    assert all("event" not in e["data"] for e in everything), "事件名在 event: 行，不重複進 data"


def test_the_stream_headers_disable_proxy_buffering(bridge, run_body) -> None:
    rid = _finished_run(bridge, run_body)
    with httpx.stream("GET", f"{bridge.base_url}/autoclaude/runs/{rid}/stream") as resp:
        assert resp.headers["content-type"].startswith("text/event-stream")
        assert resp.headers["cache-control"] == "no-cache"
        assert resp.headers["x-accel-buffering"] == "no"
        first = next(resp.iter_lines())
        assert first == "retry: 3000"


def test_events_endpoint_honours_limit_and_validates_the_cursor(bridge, run_body) -> None:
    rid = _finished_run(bridge, run_body)
    url = f"/autoclaude/runs/{rid}/events"
    assert len(bridge.client.get(url, params={"limit": 3}).json()) == 3
    assert bridge.client.get(url, params={"after": -1}).status_code == 422
    assert bridge.client.get(url, params={"limit": 0}).status_code == 422


def test_the_stream_stays_open_while_paused_and_ends_on_cancel(bridge, run_body) -> None:
    rid = bridge.post_run(run_body(delay="0.6")).json()["run_id"]
    bridge.client.post(f"/autoclaude/runs/{rid}:pause")
    paused = bridge.wait_status(rid, {"PAUSED"})
    # PAUSED 不是終態：串流把既有事件送完之後必須繼續開著（讀逾時＝證明沒被關掉）。
    seen: list[str] = []
    with pytest.raises(httpx.ReadTimeout):
        with httpx.stream("GET", f"{bridge.base_url}/autoclaude/runs/{rid}/stream",
                          timeout=httpx.Timeout(10.0, read=2.0)) as resp:
            seen.extend(line for line in resp.iter_lines() if line.startswith("id:"))
    assert seen[-1] == f"id: {paused['last_event_seq']}"

    bridge.client.post(f"/autoclaude/runs/{rid}:stop")
    assert bridge.wait_status(rid, {"CANCELLED"})["completed_at"]
    tail = bridge.sse(rid, after=paused["last_event_seq"])    # 終態後讀得到收尾事件並自行結束
    assert tail[-1]["data"]["status"] == "CANCELLED"
