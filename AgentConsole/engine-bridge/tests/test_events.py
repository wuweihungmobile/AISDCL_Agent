"""EventStore：seq 單調、JSONL 持久、環溢出後掃檔重播、重啟延續、SSE 喚醒。"""
from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path

import pytest

from app.events import EventStore, to_sse_data


def test_append_assigns_monotonic_seq_and_persists_each_line(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    store = EventStore(path)
    a = store.append("log", {"level": "INFO", "line": "第一行"})
    b = store.append("status", {"status": "RUNNING", "reason": ""})
    assert (a["seq"], b["seq"]) == (1, 2)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(x)["seq"] for x in lines] == [1, 2]
    assert json.loads(lines[0])["line"] == "第一行", "中文不得被轉成 \\u 跳脫"
    assert a["ts"].endswith("+00:00"), "時間戳必須帶時區"


def test_payload_cannot_override_reserved_keys(tmp_path: Path) -> None:
    ev = EventStore(tmp_path / "e.jsonl").append("log", {"seq": 99, "ts": "x", "event": "evil"})
    assert (ev["seq"], ev["event"]) == (1, "log")
    assert ev["ts"] != "x"


def test_only_the_contract_event_types_are_accepted(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "e.jsonl")
    for kind in ("log", "status", "step", "token", "review-request", "alert"):
        store.append(kind, {})
    with pytest.raises(ValueError, match="未知的事件類型"):
        store.append("stats-update", {})
    assert store.last_seq == 6, "被拒絕的事件不得佔用 seq"


def test_replay_after_and_limit(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "e.jsonl")
    for i in range(10):
        store.append("log", {"line": str(i)})
    assert [e["seq"] for e in store.replay(0)] == list(range(1, 11))
    assert [e["seq"] for e in store.replay(7)] == [8, 9, 10]
    assert [e["seq"] for e in store.replay(2, limit=3)] == [3, 4, 5]
    assert store.replay(10) == []


def test_replay_falls_back_to_the_file_when_the_ring_is_too_new(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "e.jsonl", ring_size=3)
    for i in range(10):
        store.append("log", {"line": str(i)})
    assert [e["seq"] for e in store.replay(0, limit=4)] == [1, 2, 3, 4]       # 環只剩 8..10
    assert [e["seq"] for e in store.replay(5)] == [6, 7, 8, 9, 10]


def test_reopen_continues_the_sequence_and_tolerates_a_truncated_tail(tmp_path: Path) -> None:
    path = tmp_path / "e.jsonl"
    first = EventStore(path)
    first.append("log", {"line": "a"})
    first.append("log", {"line": "b"})
    first.close()
    with path.open("a", encoding="utf-8") as fh:
        fh.write('{"seq":3,"ts":"x","ev')                # 崩潰時寫到一半的行
    second = EventStore(path)
    assert second.last_seq == 2
    nxt = second.append("log", {"line": "c"})
    assert nxt["seq"] == 3
    assert [e["seq"] for e in second.replay(0)] == [1, 2, 3]


def test_concurrent_appends_get_unique_contiguous_seqs(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "e.jsonl")

    def work() -> None:
        for _ in range(50):
            store.append("log", {"line": "x"})

    threads = [threading.Thread(target=work) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    seqs = [e["seq"] for e in store.replay(0)]
    assert seqs == list(range(1, 401))
    on_disk = [json.loads(x)["seq"] for x in (tmp_path / "e.jsonl").read_text("utf-8").splitlines()]
    assert on_disk == seqs


def test_write_failure_does_not_break_the_in_memory_stream(tmp_path: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    store = EventStore(blocker / "sub" / "e.jsonl")      # 父路徑是檔案 ⇒ 開檔必失敗
    store.append("log", {"line": "still works"})
    assert store.replay(0)[0]["line"] == "still works"


def test_to_sse_data_drops_only_the_event_name(tmp_path: Path) -> None:
    ev = EventStore(tmp_path / "e.jsonl").append("step", {"step_id": "T01", "status": "STARTED"})
    data = to_sse_data(ev)
    assert "event" not in data
    assert set(data) == {"seq", "ts", "step_id", "status"}


async def test_waiter_is_woken_by_an_append_from_another_thread(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "e.jsonl")
    loop = asyncio.get_running_loop()
    signal = asyncio.Event()
    token = store.add_waiter(loop, signal)
    try:
        threading.Timer(0.05, lambda: store.append("log", {"line": "x"})).start()
        await asyncio.wait_for(signal.wait(), timeout=3)
    finally:
        store.remove_waiter(token)
    assert store.last_seq == 1
