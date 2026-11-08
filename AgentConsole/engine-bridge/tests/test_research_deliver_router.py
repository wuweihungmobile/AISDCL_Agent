"""P2 五個 Bridge 端點的路由層（TCS AT-962-1-8、6-8、17-6、18-E-6、26-E-1；PKG-BR-P2）。

檢查序（先中者定案）：權杖→資料庫→專案存在→請求本文→（`:gates`／`:tag`）凍結 digest 漂移→前置。
共用夾具與助手來自同包其他測試檔（P1 的 `renv`、`build_project` 等）。
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import pytest

from app.research import db as db_module
from app.research import delivery
from app.research import settings as settings_mod
from tests import research_git_support as rgs
from tests import test_research_delivery as dl
from tests import test_research_healing as hs
from tests import test_research_inner_gates as ig
from tests import test_research_router as rt
from tests.research_pg_support import LAST_VERSION, make_research_db, migration_files
from tests.test_research_scr import ADMIN

make_env = rt.make_env
route_db, real_tree, renv, fake_gh = rgs.route_db, rgs.real_tree, rgs.renv, rgs.fake_gh
rtm, verbs = ig.rtm, ig.verbs
calls = dl.calls


# ── AT-962-1-8：Bridge 兩個 INSERT 帶 V21 新欄 ───────────────────────────────────────────────────
def test_AT_962_1_8_the_throwaway_db_reaches_last_version_and_inserts_use_new_columns() -> None:
    assert LAST_VERSION >= 21 and len(migration_files()) == LAST_VERSION
    db = make_research_db()
    try:
        from app.research.db import ResearchDb

        store = ResearchDb(db.dsn)
        rid = str(uuid.uuid4())
        store.create_project(research_id=rid, slug="v21", title="t", topic="t", scope={},
                             workspace_path="x", fsm_project="research-v21", fsm_state_dir="y",
                             created_by=ADMIN)
        base = dict(research_id=rid, gate="SCG6", decision="REJECTED", decided_by=ADMIN,
                    fsm_project="demo-app", reason="r")
        with_details = {"reviewer_independent": True, "review_report_ref": None, "ci_red": True}
        store.apply("gate.decision", {**base, "decision_id": str(uuid.uuid4()),
                                      "details": with_details})
        store.apply("gate.decision", {**base, "decision_id": str(uuid.uuid4())})
        rows = db.q("SELECT details FROM console.research_gate_decisions WHERE gate = 'SCG6' "
                    "ORDER BY decided_at, id")
        assert [r[0] for r in rows] == [with_details, {}]
        url = "https://ci.example.com/run/9"
        for evidence in (url, None):
            payload = {"research_id": rid, "scr_id": str(uuid.uuid4()), "kind": "MINOR",
                       "source_kind": "HUMAN", "reason": "x", "requested_by": ADMIN}
            if evidence is not None:
                payload["evidence_url"] = evidence
            store.apply("scr.open", payload)
            db.exec("UPDATE console.research_scr SET status = 'REJECTED' WHERE research_id = %s",
                    rid)
        stored = db.q("SELECT evidence_url FROM console.research_scr ORDER BY scr_no")
        assert [r[0] for r in stored] == [url, None]
    finally:
        db.drop()


# ── AT-962-6-8：`:healing-sync` 的檢查序與形狀 ──────────────────────────────────────────────────
def test_AT_962_6_8_healing_sync_is_internal_and_checks_in_the_documented_order(
        renv: rgs.RouteEnv) -> None:
    rid, route = hs.routed(renv)
    url = f"/research/projects/{rid}:healing-sync"
    assert renv.env.post(url, {}, headers=None).status_code in (401, 403)
    assert renv.env.post(f"/research/projects/{uuid.uuid4()}:healing-sync", {}).status_code == 404
    extra = renv.env.post(url, {"surprise": 1})
    assert (extra.status_code, extra.json()["reason"]) == (422, "invalid_request")
    assert renv.env.post(url, {"requested_by": "alice@example.com"}).status_code == 422
    ok = renv.env.post(url, {"requested_by": "system"})
    assert ok.status_code == 200 and set(ok.json()) == {
        "view_rows", "log_lines", "appended", "spec_change"}
    target = ig.frozen_prd(route)
    target.write_bytes(target.read_bytes() + b"!")
    assert renv.env.post(url, {}).status_code == 200
    alerts = [e for e in renv.rdb.events(rid) if e[1] == "research.alert"]
    assert alerts and {a[3] for a in alerts} == {"system"}


# ── AT-962-17-6：預覽零副作用 ───────────────────────────────────────────────────────────────────
def test_AT_962_17_6_the_traceability_preview_leaves_db_and_files_unchanged(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture) -> None:
    project = dl.build_project(renv, origin=False)
    before = dl.tree_snapshot(project)
    for _ in range(3):
        resp = renv.env.post(f"/research/projects/{project.rid}:traceability-preview", {})
        assert resp.status_code == 200
        assert set(resp.json()) == {"rows", "totals", "rtm", "generatedAt"}
    assert dl.tree_snapshot(project) == before


# ── AT-962-18-E-6：容器模式 ─────────────────────────────────────────────────────────────────────
def test_AT_962_18_E_6_a_read_only_deployment_refuses_the_tag_without_side_effects(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: dl.Calls, verbs: ig.VerbLog,
        monkeypatch: pytest.MonkeyPatch) -> None:
    project = dl.build_project(renv)
    monkeypatch.setattr(settings_mod, "repo_writable", lambda cfg=None: False)
    calls.clear(), verbs.clear()
    resp = project.tag()
    assert (resp.status_code, resp.json()["reason"]) == (422, "route_unsupported_in_deployment")
    assert [m["item"] for m in resp.json()["details"]["missing"]] == ["repo_writable"]
    assert not calls and project.rows() == [] and verbs.writes() == []


# ── AT-962-26-E-1：五個端點的檢查序 ─────────────────────────────────────────────────────────────
def endpoint_body(name: str, project: dl.Project | None = None) -> dict[str, Any]:
    run = project.run_id if project else str(uuid.uuid4())
    return {"gates": ig.gate_body("PR_REVIEW", "PASS", run_id=run),
            "tag": {"tag_name": dl.TAG, "approver": ADMIN, "push": False, "run_id": run},
            "pr": {"body_preview_ack": True, "approver": ADMIN},
            "traceability-preview": {}, "healing-sync": {}}[name]


ENDPOINTS = ["gates", "tag", "pr", "traceability-preview", "healing-sync"]


def url_of(rid: str, name: str) -> str:
    return f"/research/projects/{rid}:{name}"


@pytest.mark.parametrize("name", ENDPOINTS)
def test_AT_962_26_E_1_token_then_db_then_project_then_body(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, name: str) -> None:
    project = dl.build_project(renv, f"o-{name[:5]}", origin=False)
    body = endpoint_body(name, project)
    assert renv.env.post(url_of(project.rid, name), body, headers=None).status_code in (401, 403)
    assert renv.env.post(url_of(str(uuid.uuid4()), name), body).status_code == 404
    renv.rdb.block()
    try:
        blocked = renv.env.post(url_of(project.rid, name), body)
    finally:
        renv.rdb.unblock()
    assert (blocked.status_code, blocked.json()["reason"]) == (503, "db_blocked")
    bad = {"gates": {**body, "gate": "NOPE"}, "tag": {**body, "tag_name": "-x"},
           "pr": {**body, "body_preview_ack": False}, "healing-sync": {"surprise": 1},
           "traceability-preview": []}[name]
    resp = renv.env.post(url_of(project.rid, name), bad)
    assert resp.status_code == 422, (name, resp.text)


@pytest.mark.parametrize("name", ["gates", "tag"])
def test_AT_962_26_E_1_drift_beats_the_state_check_and_the_state_check_gives_409(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, name: str) -> None:
    project = dl.build_project(renv, f"d-{name}", state="IMPLEMENTATION", origin=False)
    body = endpoint_body(name, project)
    if name == "gates":
        body = {**body, "gate": "RTM_VERIFY"}                       # 現態是 IMPLEMENTATION：不合
    resp = renv.env.post(url_of(project.rid, name), body)
    assert (resp.status_code, resp.json()["reason"]) == (409, "fsm_state_conflict")
    target = ig.frozen_prd(project.route)
    target.write_bytes(target.read_bytes() + b"!")
    drifted = renv.env.post(url_of(project.rid, name), body)
    assert (drifted.status_code, drifted.json()["reason"]) == (422, "digest_mismatch")


def test_AT_962_26_E_1_preview_and_pr_answer_409_when_their_prerequisites_are_missing(
        renv: rgs.RouteEnv) -> None:
    unfrozen = rgs.seed_gate0(renv, "no-freeze", approve=False)
    resp = renv.env.post(url_of(unfrozen, "traceability-preview"), {})
    assert (resp.status_code, resp.json()["reason"]) == (409, "fsm_state_conflict")
    unrouted = rgs.seed_gate0(renv, "no-route")
    resp = renv.env.post(url_of(unrouted, "pr"), {"body_preview_ack": True, "approver": ADMIN})
    assert (resp.status_code, resp.json()["details"]["cause"]) == (409, "route_not_succeeded")


@pytest.mark.parametrize("push", [1, 0, "true", "false", None, [], {}])
def test_AT_962_19_1_push_must_be_a_real_boolean_so_integers_and_strings_are_422(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: dl.Calls, push: Any) -> None:
    """F-13（SCG-4 一審）：`1 == True` 讓成員檢查放行整數 1／0；`push` 只准 JSON 布林。零副作用。"""
    project = dl.build_project(renv, "pushbool", origin=False)
    calls.clear()
    resp = project.tag(push=push)
    assert (resp.status_code, resp.json()["reason"]) == (422, "invalid_request"), resp.text
    assert [v["rule"] for v in resp.json()["violations"]] == ["invalid_boolean"]
    assert not calls and project.rows() == []


def _routes_after_importing(module: str) -> list[str]:
    """乾淨行程只匯入 `module`，把 `app.routers.research.router` 掛上空 app 後回 OpenAPI 的
    `METHOD path` 清單（排序；FastAPI 的 `router.routes` 對 include 進來的子 router 是惰性物件，
    OpenAPI 才是展開後的真實路由面）。"""
    import json
    import subprocess
    import sys

    root = Path(delivery.__file__).resolve().parents[2]
    code = ("import json, sys, importlib; importlib.import_module(sys.argv[1]); "
            "from fastapi import FastAPI; from app.routers import research; "
            "app = FastAPI(); app.include_router(research.router); "
            "print(json.dumps(sorted(f'{m} {p}' for p, ops in app.openapi()['paths'].items() "
            "for m in ops)))")
    done = subprocess.run([sys.executable, "-c", code, module], cwd=root, capture_output=True,
                          text=True, encoding="utf-8", timeout=120, check=False)
    assert done.returncode == 0, done.stderr[-800:]
    return json.loads(done.stdout.strip().splitlines()[-1])        # type: ignore[no-any-return]


@pytest.mark.parametrize("module", ["app.routers.research_deliver", "app.routers.research_scr"])
def test_AT_962_26_E_1_importing_a_sub_router_module_first_neither_raises_nor_changes_the_routes(
        module: str) -> None:
    """F-17 D-3（SCG-4 一審）：單獨 `import app.routers.research_deliver`（或 `_scr`）曾因循環匯入拋
    AttributeError；子模組改為自掛回父 router 後，兩種匯入順序得到同一組路由。"""
    via_parent = _routes_after_importing("app.routers.research")
    first = _routes_after_importing(module)
    assert first == via_parent
    assert any(":tag" in r for r in first) and any(":scr" in r for r in first)


def test_the_new_reasons_are_exactly_the_two_registered_ones() -> None:
    """未登記四方鎖的字面不得流出（AT-962-24-E-2 的 Bridge 半）：本包新增的 reason 只有兩個。"""
    import re

    sources = ""
    for rel in ("app/research/delivery.py", "app/research/inner_gates.py",
                "app/research/healing.py", "app/routers/research_deliver.py"):
        sources += (Path(delivery.__file__).resolve().parents[2] / rel).read_text(encoding="utf-8")
    reasons = set(re.findall(r'ApiError\(\s*\d{3},\s*"([a-z_]+)"', sources))
    known = {"tag_exists", "delivery_step_failed", "fsm_state_conflict", "invalid_request",
             "digest_mismatch", "route_unsupported_in_deployment", "scr_open", "sdd_cli_failed"}
    assert reasons <= known, reasons - known
    assert {"tag_exists", "delivery_step_failed"} <= reasons
    assert db_module.DELIVERY_FAILURE_STEPS == {"push", "pr_create", "fsm_release", "tag"}
