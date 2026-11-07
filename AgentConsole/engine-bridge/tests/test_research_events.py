"""研究事件帳：單調序號與 REST／SSE 重播（TCS AT-960-6-E-1、10-3；API 契約 §3、API-RP-05／06）。

事件的唯一來源是 `research_events`（Bridge 是唯一寫入者）；序號在「專案列 `last_event_seq`＋1」與
事件列同一交易內配發，所以單行程下單調連續、回滾不留洞（多行程配號不在範圍：L-R9 單 worker 假設）。
`GET …/events` 與 `GET …/stream` 的回放必須與 DB 逐列相等；P0 事件型別與 payload 鍵集合固定。
"""
from __future__ import annotations

import json
import threading
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from app.research.db import EVENT_PAYLOAD_KEYS, ResearchDb, ResearchGuardError, jsonable
from app.routers import research as router_module
from app.settings import Settings
from tests.fake_sdd import make_fake_sdd
from tests.research_pg_support import ThrowawayDb, make_research_db
from tests.test_research_router import ADMIN, ALICE, Env, build_env, create

P0_TYPES = {"research.step", "research.run", "research.source", "research.evidence",
            "research.prd", "research.review", "research.review_invalid", "research.defect",
            "research.gate", "research.reconcile", "research.alert"}


@pytest.fixture
def rdb() -> Iterator[ThrowawayDb]:
    db = make_research_db()
    try:
        yield db
    finally:
        db.drop()


def seed_project(rdb: ThrowawayDb, slug: str = "ev") -> str:
    """直接 INSERT 一個專案列（不經寫入器，所以沒有任何事件、`last_event_seq` 為 0）。"""
    rid = str(uuid.uuid4())
    rdb.exec("INSERT INTO console.research_projects (id, slug, title, topic, workspace_path, "
             "fsm_project, fsm_state_dir, created_by) VALUES (%s, %s, 't', 't', '/ws', "
             "'research-ev', '/ws/fsm', 'alice')", rid, slug)
    return rid


def alert(db: ResearchDb, rid: str, n: int) -> int:
    return db.append_event(research_id=rid, event_type="research.alert", actor="bridge",
                           payload={"kind": "STAGE_FAILED", "detail": str(n)})["seq"]


# ══ AT-960-6-E-1 ═══════════════════════════════════════════════════════════════════════════
def test_AT_960_6_E_1_eight_threads_writing_200_events_get_contiguous_unique_seqs(
        rdb: ThrowawayDb) -> None:
    rid, db = seed_project(rdb), ResearchDb(rdb.dsn)
    seqs: list[int] = []
    guard = threading.Lock()

    def writer(worker: int) -> None:
        for i in range(25):
            seq = alert(db, rid, worker * 100 + i)
            with guard:
                seqs.append(seq)

    threads = [threading.Thread(target=writer, args=(w,)) for w in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(120)
    assert sorted(seqs) == list(range(1, 201)), "seq 為 1 至 200 連續唯一"
    assert [r[0] for r in rdb.events(rid)] == list(range(1, 201))
    assert db.get_project(rid)["last_event_seq"] == 200


def test_AT_960_6_E_1_a_rolled_back_transaction_leaves_no_hole_in_the_sequence(
        rdb: ThrowawayDb) -> None:
    rid, db = seed_project(rdb), ResearchDb(rdb.dsn)
    assert [alert(db, rid, n) for n in range(3)] == [1, 2, 3]
    with pytest.raises(RuntimeError), db.transaction() as tx:
        tx.append_event(rid, "research.alert", {"kind": "QUOTA", "detail": "x"}, actor="bridge")
        raise RuntimeError("中途失敗：整個交易回滾")
    assert db.get_project(rid)["last_event_seq"] == 3, "last_event_seq 與事件列同交易回滾"
    assert alert(db, rid, 4) == 4, "回滾後下一筆接續、不留洞"


def test_AT_960_6_E_1_the_writer_refuses_events_outside_the_contract(rdb: ThrowawayDb) -> None:
    rid, db = seed_project(rdb), ResearchDb(rdb.dsn)
    bad = {"unknown type": ("research.route", {"routeId": "x"}),
           "replay gap is transport only": ("research.replay_gap", {"fromSeq": 1, "toSeq": 2}),
           "missing key": ("research.alert", {"kind": "QUOTA"}),
           "extra key": ("research.alert", {"kind": "QUOTA", "detail": "d", "extra": 1})}
    for label, (event_type, payload) in bad.items():
        with pytest.raises(ResearchGuardError):
            db.append_event(research_id=rid, event_type=event_type, actor="bridge",
                            payload=payload)
        assert rdb.count("research_events") == 0, label
    with pytest.raises(ResearchGuardError) as caught:
        db.append_event(research_id=str(uuid.uuid4()), event_type="research.alert",
                        actor="bridge", payload={"kind": "QUOTA", "detail": "d"})
    assert caught.value.rule == "project_not_found"


# ══ AT-960-10-3 ════════════════════════════════════════════════════════════════════════════
@pytest.fixture
def fake(tmp_path: Path) -> Path:
    return make_fake_sdd(tmp_path / "sdd")


@pytest.fixture
def make_env(make_bridge: Callable[..., Any], settings: Settings, tmp_path: Path
             ) -> Callable[..., Env]:
    def build(tree: Path, rdb: ThrowawayDb | None, **over: Any) -> Env:
        return build_env(make_bridge, settings, tmp_path, tree, rdb, **over)

    return build


def produce_every_event_type(env: Env) -> str:
    """經真的 HTTP 與寫入器產生 P0 的 11 種事件型別各至少一筆。"""
    rid = create(env, "evt")["research_id"]                        # research.step
    db, run_id, source_id = env.db, str(uuid.uuid4()), str(uuid.uuid4())
    db.insert_stage_run(research_id=rid, stage_run_id=run_id, stage="RESEARCH",
                        requested_by=ALICE, status="RUNNING")      # research.run
    db.update_stage_run(stage_run_id=run_id, status="SUCCEEDED", tokens_used=7, actor="bridge")
    db.insert_source(research_id=rid, actor="bridge", fetch_outcome="OK", source={
        "id": source_id, "source_no": "S-001", "layer": "ACADEMIC", "tier": "T1",
        "verification": "V1", "anchor_kind": "URL", "url": "https://arxiv.org/abs/1",
        "title": "A paper"})                                       # research.source
    items = json.dumps({"schema_rev": 1})
    db.record_evidence(
        research_id=rid, matrix_version=1, actor="bridge", stage_run_id=run_id,
        artifact={"rel_path": "00_research/evidence_items.json", "sha256": "a" * 64,
                  "bytes": len(items), "content": items, "created_by": "bridge"},
        items=[{"evidence_no": "E-001", "source_no": "S-001", "claim": "論點",
                "f1_mechanism": "m", "f2_evidence": "e", "f3_critique": "k",
                "f5_applicability": {"技術可行": "A"}, "f6_limits": "l",
                "f7_verification": "V1"}])                          # research.evidence
    put = env.put(f"/research/projects/{rid}/prd",
                  {"base_version": 0, "content": "# PRD\n見 [E-001]\n", "author": ALICE})
    assert put.status_code == 201                                  # research.prd
    review_run = str(uuid.uuid4())
    db.insert_stage_run(research_id=rid, stage_run_id=review_run, stage="REVIEW", round_no=1,
                        requested_by=ALICE, status="SUCCEEDED")
    defect_id = str(uuid.uuid4())
    db.insert_review_round(research_id=rid, actor="bridge", round={
        "round_no": 1, "prd_version_no": 1, "trigger_kind": "AUTO", "precheck_passed": True,
        "weighted_score": "79.90", "min_dimension_score": 70, "passed": False,
        "verdict": "REVISE", "fsm_gate_result": "FAIL", "fsm_retry_count": 1,
        "stage_run_id": review_run, "started_at": "2026-11-02T01:00:00+00:00",
        "finished_at": "2026-11-02T01:01:00+00:00"},
        defects=[{"id": defect_id, "defect_no": "D-1-001", "dimension": "QA", "severity": "P2",
                  "code": "AC_UNTESTABLE", "description": "d"}])   # review 與 defect 事件
    db.record_gate_decision(research_id=rid, decision_id=str(uuid.uuid4()), gate="GATE0",
                            decision="CHANGES", decided_by=ADMIN, fsm_project="research-evt",
                            fsm_state_after="HUMAN_PENDING")        # research.gate
    for event_type, payload in (
            ("research.review_invalid", {"stageRunId": review_run, "roundNo": 2, "attempt": 1,
                                         "reason": "QA 維度：rubric 加總不符"}),
            ("research.reconcile", {"consistent": True, "driftCount": 0}),
            ("research.alert", {"kind": "BLOCKED_DB", "detail": "測試"})):
        db.append_event(research_id=rid, event_type=event_type, actor="bridge", payload=payload)
    return rid


def parse_sse(lines: Iterator[str], stop_after_heartbeat: bool = True) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for line in lines:
        if line == "":
            if current:
                frames.append(current)
                if stop_after_heartbeat and current.get("event") == "heartbeat":
                    return frames
            current = {}
        elif line.startswith(":") or line.startswith("retry:"):
            continue
        else:
            key, _sep, value = line.partition(": ")
            current[key] = value
    return frames


def test_AT_960_10_3_rest_and_stream_replay_equal_the_db_rows_and_the_payload_shapes_are_fixed(
        make_env: Callable[..., Env], rdb: ThrowawayDb, fake: Path,
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(router_module, "STREAM_POLL_SECONDS", 0.05)
    monkeypatch.setattr(router_module, "STREAM_HEARTBEAT_SECONDS", 0.3)
    env = make_env(fake, rdb)
    rid = produce_every_event_type(env)
    rows = [jsonable(r) for r in env.db.list_events(rid, after_seq=0, limit=500)]
    assert {r["event_type"] for r in rows} == P0_TYPES, "P0 的 11 種事件型別都有"
    assert [r["seq"] for r in rows] == list(range(1, len(rows) + 1))
    for row in rows:
        assert set(row["payload"]) == EVENT_PAYLOAD_KEYS[row["event_type"]], row["event_type"]
    review = next(r for r in rows if r["event_type"] == "research.review")["payload"]
    assert (review["roundNo"], review["verdict"], review["passed"]) == (1, "REVISE", False)
    rest = env.get(f"/research/projects/{rid}/events?after=0&limit=500").json()
    assert rest["items"] == rows and rest["truncated"] is False
    assert rest["next_seq"] == rows[-1]["seq"]
    with env.client.stream("GET", f"/research/projects/{rid}/stream?after=0") as resp:
        assert resp.status_code == 200 and "text/event-stream" in resp.headers["content-type"]
        frames = parse_sse(resp.iter_lines())
    assert frames[-1]["event"] == "heartbeat" and "id" not in frames[-1]
    replayed = frames[:-1]
    assert [int(f["id"]) for f in replayed] == [r["seq"] for r in rows]
    assert [f["event"] for f in replayed] == [r["event_type"] for r in rows]
    assert [json.loads(f["data"]) for f in replayed] == rows
    assert {f["event"] for f in frames} <= P0_TYPES | {"heartbeat"}
    assert not {"research.route", "research.scr", "research.delivery", "research.replay_gap"} & {
        r["event_type"] for r in rows} and all(f["event"] != "research.replay_gap" for f in frames)


def test_AT_960_10_3_after_and_last_event_id_resume_without_gaps_and_limits_truncate(
        make_env: Callable[..., Env], rdb: ThrowawayDb, fake: Path,
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(router_module, "STREAM_POLL_SECONDS", 0.05)
    monkeypatch.setattr(router_module, "STREAM_HEARTBEAT_SECONDS", 0.3)
    env = make_env(fake, rdb)
    rid = produce_every_event_type(env)
    total = env.db.get_project(rid)["last_event_seq"]
    page = env.get(f"/research/projects/{rid}/events?after=0&limit=5").json()
    assert [e["seq"] for e in page["items"]] == [1, 2, 3, 4, 5]
    assert page["truncated"] is True and page["next_seq"] == 5
    rest = env.get(f"/research/projects/{rid}/events?after=5&limit=500").json()
    assert rest["truncated"] is False and [e["seq"] for e in rest["items"]] == list(
        range(6, total + 1))
    assert env.get(f"/research/projects/{rid}/events?after=0&limit=100000").status_code == 200
    with env.client.stream("GET", f"/research/projects/{rid}/stream",
                           headers={"Last-Event-ID": str(total - 2)}) as resp:
        frames = parse_sse(resp.iter_lines())
    assert [int(f["id"]) for f in frames[:-1]] == [total - 1, total]
    assert env.get(f"/research/projects/{uuid.uuid4()}/events").status_code == 404


def test_AT_960_10_3_the_events_page_size_is_capped_at_500_whatever_the_caller_asks(
        make_env: Callable[..., Env], rdb: ThrowawayDb, fake: Path) -> None:
    """`limit` 上限 500（API-RP-05）：要 500 給 500、要 501 與更大也只給 500（`truncated` 為真、
    `next_seq` 指向第 500 筆），續抓從第 501 筆接上（突變把上限放寬會讓 501 回 501 筆）。"""
    env = make_env(fake, rdb)
    rid = create(env, "evcap")["research_id"]
    assert router_module.EVENTS_MAX_LIMIT == 500
    for n in range(520):                                # 建立專案時已有 1 筆 research.step
        alert(env.db, rid, n)
    total = int(env.db.get_project(rid)["last_event_seq"])
    assert total == 521
    for asked in (500, 501, 1000, 100_000):
        body = env.get(f"/research/projects/{rid}/events?after=0&limit={asked}").json()
        assert len(body["items"]) == 500 and body["truncated"] is True, asked
        assert [e["seq"] for e in body["items"]] == list(range(1, 501)), asked
        assert body["next_seq"] == 500, asked
    rest = env.get(f"/research/projects/{rid}/events?after=500&limit=501").json()
    assert [e["seq"] for e in rest["items"]] == list(range(501, total + 1))
    assert rest["truncated"] is False and rest["next_seq"] == total


# ══════════════════════════════════════════════════════════════════════════════════════════════
# PKG-BR-C 附加（append-only；上方既有測試一字未動）：AT-960-10-3 的另一半——完整 research＋draft＋
# review 真流程（活 Bridge＋引擎＋假 claude）產生的事件，型別、payload 鍵集合與重播都符合契約。
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_AT_960_10_3_a_real_research_draft_review_flow_emits_only_contract_events(
        make_bridge: Callable[..., Any], settings: Settings, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch, rdb: ThrowawayDb) -> None:
    from tests import test_research_orchestrator as orch
    from tests.research_stage_support import install_framework

    monkeypatch.setattr(router_module, "STREAM_POLL_SECONDS", 0.05)
    monkeypatch.setattr(router_module, "STREAM_HEARTBEAT_SECONDS", 0.3)
    tree = install_framework(make_fake_sdd(tmp_path / "sdd"))
    rig = orch.build_rig(make_bridge, settings, tmp_path, monkeypatch, tree, rdb)
    rid = orch.create(rig)
    orch.to_draft(rig, rid)
    orch.run_stage(rig, rid, "review")
    rows = [jsonable(r) for r in rig.db.list_events(rid, after_seq=0, limit=500)]
    kinds = {r["event_type"] for r in rows}
    assert {"research.step", "research.run", "research.source", "research.evidence",
            "research.prd", "research.review", "research.defect"} <= kinds
    assert kinds <= P0_TYPES and not {"research.route", "research.scr", "research.delivery",
                                      "research.replay_gap"} & kinds
    assert [r["seq"] for r in rows] == list(range(1, len(rows) + 1))
    for row in rows:
        assert set(row["payload"]) == EVENT_PAYLOAD_KEYS[row["event_type"]], row["event_type"]
    reviews = [r for r in rows if r["event_type"] == "research.review"]
    assert len(reviews) == 1, "research.review 只在輪完成時送，審查進行中只以 research.run 表達"
    assert reviews[0]["payload"]["verdict"] == "REVISE" and reviews[0]["payload"]["roundNo"] == 1
    run_events = [r["payload"]["status"] for r in rows if r["event_type"] == "research.run"
                  and r["payload"]["stage"] == "REVIEW"]
    assert run_events[:2] == ["QUEUED", "RUNNING"] and run_events[-1] == "SUCCEEDED"
    review_at = rows.index(reviews[0])
    assert any(r["event_type"] == "research.run" and r["payload"]["status"] == "RUNNING"
               and r["payload"]["stage"] == "REVIEW" for r in rows[:review_at])
    rest = rig.client.get(f"/research/projects/{rid}/events?after=0&limit=500").json()
    assert rest["items"] == rows
    with rig.client.stream("GET", f"/research/projects/{rid}/stream?after=0") as resp:
        frames = parse_sse(resp.iter_lines())
    assert [json.loads(f["data"]) for f in frames[:-1]] == rows
    assert frames[-1]["event"] == "heartbeat" and all(
        f["event"] != "research.replay_gap" for f in frames)


# ══ P2（PKG-BR-P2；AT-962-26-5）：`research.delivery` 事件登記。以下 append-only ═════════
def test_AT_962_26_5_research_delivery_has_six_fixed_keys_and_fails_loud_outside_them(
        make_env: Callable[..., Env], rdb: ThrowawayDb, fake: Path) -> None:
    from app.research.db import (
        DELIVERY_FAILURE_STEPS,
        EVENT_OPTIONAL_KEYS,
        ResearchGuardError,
    )

    keys = {"kind", "ref", "status", "digest", "reason", "failure_step"}
    assert EVENT_PAYLOAD_KEYS["research.delivery"] == keys
    assert "research.delivery" not in EVENT_OPTIONAL_KEYS
    env = make_env(fake, rdb)
    rid = create(env, "ev-delivery")["research_id"]

    def add(payload: dict[str, Any]) -> dict[str, Any]:
        return env.db.append_event(research_id=rid, event_type="research.delivery",
                                   actor="bridge", payload=payload)

    ok = {"kind": "RELEASE_TAG", "ref": "v1.0.0", "status": "CREATED", "digest": "a" * 64,
          "reason": "", "failure_step": None}
    assert add(ok)["applied"] is True
    assert DELIVERY_FAILURE_STEPS == {"push", "pr_create", "fsm_release", "tag"}
    for step in sorted(DELIVERY_FAILURE_STEPS):
        failed = {**ok, "ref": None, "status": "FAILED", "failure_step": step, "reason": "x"}
        assert add(failed)["applied"] is True
    failed = {**ok, "ref": None, "status": "FAILED", "failure_step": "push"}
    for bad in ({k: v for k, v in failed.items() if k != "failure_step"}, {**ok, "extra": 1},
                {**failed, "failure_step": None}, {**failed, "failure_step": "nope"},
                {**ok, "ref": None}):
        with pytest.raises(ResearchGuardError):
            add(bad)
    payloads = [e["payload"] for e in env.db.list_events(rid, limit=500)
                if e["event_type"] == "research.delivery"]
    assert len(payloads) == 5 and all(set(p) == keys for p in payloads)
