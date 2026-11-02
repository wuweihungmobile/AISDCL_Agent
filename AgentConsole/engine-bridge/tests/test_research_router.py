"""`/research/*` 路由（`app/routers/research.py`；API 契約 §2）。

TCS-ResearchToPRD-P0-20261102：AT-960-2-1／2-2／2-7（閘門與能力探針）、3-1／3-3／3-4（建立與
重試初始化）、6-1／6-3／6-4／6-5／6-6（游標、前置條件、並行上限、凍結、PRD 樂觀鎖）、
8-9／8-E-2（allowlist 與 Web 層）、15-5／15-6／15-8／15-E-1（ESCALATION 與換世代），另有
「尚未實作」骨架的形狀釘選。

活 Bridge＝`make_bridge`（真 uvicorn＋真 HTTP）；DB 型測試用 `research_pg_support` 的拋棄式資料庫
（`BRIDGE_TEST_DSN` 未設＝TOOL-ABSENCE 跳過）；FSM 樹有 `fake`（假 CLI）與 `real`（真 SDD 樹，
`SDD_ROOT` 不在＝TOOL-ABSENCE 跳過）兩種，同一組斷言各跑一次。
四類處理函式（stage 啟動、`:approve-baseline`、`:return`、`:reconcile`）的本體已由 PKG-BR-C 落地
（原為 501 骨架）：本檔對 stage 啟動只驗「請求被接受（202）」；引擎的 claude 一律設成不存在的指令
（`research_claude_command`＝`ABSENT_CLAUDE`：run 立刻失敗、絕不呼叫真正的模型），並以 `settle`
等 stage 鏈結束後才改列或拍快照；假 SDD 樹補上夾具框架檔（編譯層需要）。完整流程的測試在
`test_research_orchestrator.py`、Gate 0 在 `test_research_approve.py`。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import threading
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import httpx
import pytest

from app import sdd_cli
from app.errors import ApiError
from app.research import fsm_ops, layout
from app.research.db import ResearchDb
from app.settings import Settings
from tests.fake_sdd import make_fake_sdd, read_state
from tests.research_pg_support import ThrowawayDb, make_research_db
from tests.research_stage_support import ABSENT_CLAUDE, install_framework, settle
from tests.test_research_fsm_ops import fail_to_escalation, human_resume, real_sdd_root

TOKEN = "t0ken-" + "r" * 40
ALICE, ADMIN = "alice@example.com", "admin@example.com"
HEAD = {"X-Bridge-Token": TOKEN}
_REAL_POPEN = subprocess.Popen


# ── 夾具 ────────────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def rdb() -> Iterator[ThrowawayDb]:
    db = make_research_db()
    try:
        yield db
    finally:
        db.drop()


@pytest.fixture
def fake(tmp_path: Path) -> Path:
    return install_framework(make_fake_sdd(tmp_path / "sdd"))      # stage 啟動要編譯：需框架檔


@pytest.fixture(params=["fake", "real"])
def tree(request: pytest.FixtureRequest, fake: Path) -> Path:
    return fake if request.param == "fake" else real_sdd_root()


@pytest.fixture
def popen_log(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Bridge 與測試自己起的每個 FSM 子行程的 argv（子行程照常執行）。"""
    log: list[list[str]] = []

    class Recording(_REAL_POPEN):  # type: ignore[misc, valid-type]
        def __init__(self, args: Any, **kwargs: Any) -> None:
            log.append(list(args))
            super().__init__(args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", Recording)
    return log


def verbs(log: list[list[str]], since: int = 0) -> list[str]:
    return [a[a.index(sdd_cli.CLI_MODULE) + 1] for a in log[since:] if sdd_cli.CLI_MODULE in a]


@dataclass
class Env:
    live: Any
    settings: Settings
    rdb: ThrowawayDb | None
    root: Path
    tree: Path

    @property
    def client(self) -> httpx.Client:
        return self.live.client

    def post(self, path: str, body: Any = None, *, headers: dict[str, str] | None = HEAD,
             **kw: Any) -> httpx.Response:
        return self.client.post(path, json=body, headers=headers, **kw)

    def put(self, path: str, body: Any = None) -> httpx.Response:
        return self.client.put(path, json=body, headers=HEAD)

    def patch(self, path: str, body: Any = None) -> httpx.Response:
        return self.client.patch(path, json=body, headers=HEAD)

    def get(self, path: str, **kw: Any) -> httpx.Response:
        return self.client.get(path, **kw)

    @property
    def db(self) -> ResearchDb:
        assert self.rdb is not None
        return ResearchDb(self.rdb.dsn)


def build_env(make_bridge: Callable[..., Any], settings: Settings, tmp_path: Path, tree: Path,
              rdb: ThrowawayDb | None, **over: Any) -> Env:
    """活 Bridge＋研究設定（工作區根在允許根之下、權杖已設、DSN 指向拋棄式庫或缺省）。"""
    root = tmp_path / "workspace" / "my-project"
    fields: dict[str, Any] = {"db_dsn": rdb.dsn if rdb else None, "research_root": root,
                              "research_write_token": TOKEN, "sdd_root": tree,
                              "research_claude_command": ABSENT_CLAUDE}      # hermetic：不呼叫模型
    fields.update(over)
    cfg = replace(settings, **fields)
    return Env(live=make_bridge(cfg), settings=cfg, rdb=rdb, root=root, tree=tree)


@pytest.fixture
def make_env(make_bridge: Callable[..., Any], settings: Settings, tmp_path: Path
             ) -> Callable[..., Env]:
    def build(tree: Path, rdb: ThrowawayDb | None, **over: Any) -> Env:
        return build_env(make_bridge, settings, tmp_path, tree, rdb, **over)

    return build


@pytest.fixture
def env(make_env: Callable[..., Env], rdb: ThrowawayDb, tree: Path, popen_log: list[list[str]]
        ) -> Env:
    return make_env(tree, rdb)


def project_body(slug: str = "demo", rid: str | None = None, **over: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "research_id": rid or str(uuid.uuid4()), "slug": slug, "title": "Demo 研究",
        "topic": "一個研究議題", "scope": {
            "layers": {"academic": True, "industry": False, "oss": True, "community": False},
            "in_scope": ["記憶體回收"], "recency_years": 3},
        "depth_level": "STANDARD", "created_by": ALICE}
    body.update(over)
    return body


def create(env: Env, slug: str = "demo", **over: Any) -> dict[str, Any]:
    resp = env.post("/research/projects", project_body(slug, **over))
    assert resp.status_code == 201, resp.text
    return resp.json()


def tree_digest(root: Path) -> dict[str, tuple[str, int]]:
    return {p.relative_to(root).as_posix(): (hashlib.sha256(p.read_bytes()).hexdigest(),
                                             p.stat().st_mtime_ns)
            for p in sorted(root.rglob("*")) if p.is_file()} if root.exists() else {}


def project_row(env: Env, rid: str) -> dict[str, Any]:
    row = env.db.get_project(rid)
    assert row is not None
    return row


def db_snapshot(env: Env, rid: str) -> tuple[Any, ...]:
    row = project_row(env, rid)
    assert env.rdb is not None
    return (row["updated_at"], row["last_event_seq"], row["flow_phase"], row["flow_status"],
            env.rdb.count("research_events"), env.rdb.count("research_stage_runs"),
            env.rdb.count("research_prd_versions"), env.rdb.count("research_gate_decisions"))


def fsm_ctx_of(env: Env, rid: str) -> fsm_ops.FsmCtx:
    row = project_row(env, rid)
    return fsm_ops.FsmCtx(sdd_root=env.tree, state_dir=Path(row["fsm_state_dir"]),
                          key=row["fsm_project"])


def to_escalation(env: Env, rid: str) -> fsm_ops.FsmCtx:
    """把專案的外環鍵推到 ESCALATION（Plan 附錄 A；測試端直接呼叫 fsm_ops，不經 HTTP）。"""
    ctx = fsm_ctx_of(env, rid)
    fsm_ops.transition(ctx, to="SPEC_DRAFTING", reason="start drafting")
    fsm_ops.transition(ctx, to="SCG_VALIDATION", reason="ready for review")
    fail_to_escalation(ctx)
    assert fsm_ops.current_state(ctx) == "ESCALATION"
    return ctx


def seed_failed_review(env: Env, rid: str, rounds: int = 1, *, escalated: bool = False) -> None:
    """DB 內放 `rounds` 個未通過的審查輪（含所需的 PRD 版本與 REVIEW stage run）。"""
    db = env.db
    for n in range(1, rounds + 1):
        text = f"# PRD v0.{n}\n"
        db.save_prd(research_id=rid, version_no=n, author_kind="HUMAN", author=ALICE,
                    content=text, rel_path=f"01_specs/PRD-v0.{n}.0-draft.md",
                    sha256=layout.sha256_text(text), bytes=len(text.encode("utf-8")))
        run_id = str(uuid.uuid4())
        db.insert_stage_run(research_id=rid, stage_run_id=run_id, stage="REVIEW", round_no=n,
                            requested_by=ALICE, status="SUCCEEDED")
        last = n == rounds
        db.insert_review_round(research_id=rid, actor="bridge", round={
            "round_no": n, "prd_version_no": n, "trigger_kind": "AUTO", "precheck_passed": True,
            "weighted_score": "79.90", "min_dimension_score": 70, "passed": False,
            "verdict": "ESCALATE" if (escalated and last) else "REVISE", "fsm_gate_result": "FAIL",
            "fsm_retry_count": n, "escalated": escalated and last, "stage_run_id": run_id,
            "started_at": "2026-11-02T01:00:00+00:00", "finished_at": "2026-11-02T01:01:00+00:00"})


# ══ AT-960-2-1：無 DSN ＝ 除能力探針外一律 503 research_requires_db 且零寫入 ═════════════════════
def test_AT_960_2_1_without_a_dsn_every_research_endpoint_but_the_probe_is_503(
        make_env: Callable[..., Env], fake: Path) -> None:
    env = make_env(fake, None)
    env.root.mkdir(parents=True)
    before = tree_digest(env.root)
    rid, entry = str(uuid.uuid4()), str(uuid.uuid4())
    calls = [
        ("POST", "/research/projects", project_body()),
        ("POST", f"/research/projects/{rid}/stages/research:start", {"requested_by": ALICE}),
        ("PUT", f"/research/projects/{rid}/prd", {"base_version": 0, "content": "x",
                                                  "author": ALICE}),
        ("POST", f"/research/projects/{rid}:approve-baseline", {}),
        ("POST", f"/research/projects/{rid}:return", {}),
        ("POST", f"/research/projects/{rid}:cancel", {}),
        ("POST", f"/research/projects/{rid}:reconcile", {}),
        ("POST", f"/research/projects/{rid}:reinit", {}),
        ("POST", f"/research/projects/{rid}:archive", {}),
        ("POST", f"/research/projects/{rid}:restore", {}),
        ("POST", "/research/allowlist", {}),
        ("PATCH", f"/research/allowlist/{entry}", {}),
        ("GET", f"/research/projects/{rid}/events?after=0", None),
        ("GET", "/research/allowlist", None),
    ]
    for method, path, body in calls:
        resp = env.client.request(method, path, json=body, headers=HEAD)
        assert resp.status_code == 503, (method, path, resp.text)
        assert resp.json()["reason"] == "research_requires_db", (method, path)
    assert tree_digest(env.root) == before, "零檔案寫入"
    probe = env.get("/research/capabilities")
    assert probe.status_code == 200 and probe.json()["db"] is False


# ══ AT-960-2-2：權杖三態與先中者定案、稽核不含權杖 ═══════════════════════════════════════════════
def _audit_lines(env: Env) -> list[dict[str, Any]]:
    path = env.settings.engine_workspace / "_audit.jsonl"
    lines = path.read_text("utf-8").splitlines() if path.is_file() else []
    return [json.loads(x) for x in lines if '"research_write"' in x]


def test_AT_960_2_2_the_token_gate_comes_first_and_the_audit_never_holds_the_token(
        make_env: Callable[..., Env], fake: Path, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("DEBUG")
    path, body = "/research/projects", project_body()
    # 一、權杖未設（也沒有 DSN）：任何標頭都是 503 research_write_disabled（權杖關先於 DB 關）
    off = make_env(fake, None, research_write_token=None)
    for header in (None, TOKEN, "whatever"):
        resp = off.client.post(path, json=body, headers={"X-Bridge-Token": header} if header
                               else None)
        assert (resp.status_code, resp.json()["reason"]) == (503, "research_write_disabled")
    # 二、權杖已設（沒有 DSN）：缺、錯、大小寫或空白不同＝403；正確＝進入下一關（DB 關）
    on = make_env(fake, None)
    for label, header in (("missing", None), ("wrong", TOKEN + "x"), ("upper", TOKEN.upper()),
                          ("inner space", TOKEN[:6] + " " + TOKEN[6:]), ("empty", "")):
        resp = on.client.post(path, json=body, headers={"X-Bridge-Token": header}
                              if header is not None else None)
        assert (resp.status_code, resp.json()["reason"]) == (403, "research_write_forbidden"), label
    ok = on.post(path, body)
    assert (ok.status_code, ok.json()["reason"]) == (503, "research_requires_db")
    # 稽核與日誌：記了 verb／result／trace_id，且任何地方都沒有權杖
    entries = _audit_lines(off) + _audit_lines(on)
    assert entries and all({"verb", "research_id", "result", "trace_id"} <= set(e) for e in entries)
    assert {e["result"] for e in entries} >= {"rejected:research_write_disabled",
                                              "rejected:research_write_forbidden",
                                              "rejected:research_requires_db"}
    haystack = json.dumps(entries) + caplog.text + ok.text
    assert TOKEN not in haystack and TOKEN.upper() not in haystack


# ══ AT-960-2-7：capabilities 與 /health/deep 的 research 資訊欄 ═══════════════════════════════════
def test_AT_960_2_7_capabilities_and_health_deep_share_a_fixed_info_shape(
        make_env: Callable[..., Env], fake: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    keys = {"mode", "root", "db", "claude_cli", "gh_cli", "git", "web_layer_enabled",
            "scaffold_templates"}
    env = make_env(fake, None)

    def probe() -> tuple[dict[str, Any], dict[str, Any], int]:
        cap = env.get("/research/capabilities").json()
        deep = env.get("/health/deep")
        return cap, deep.json()["research"], deep.status_code

    import shutil

    real_which = shutil.which
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: (
        f"/fake/{name}" if name in ("claude", "git", "gh") else real_which(name, *a, **k)))
    cap, info, status_with = probe()
    assert set(cap) == keys and cap == info
    assert cap["mode"] == "local" and cap["claude_cli"]["ok"] and cap["git"]["ok"]
    assert cap["claude_cli"]["version"] == "NOT-EVALUABLE" and cap["db"] is False
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: (
        None if name == "claude" else real_which(name, *a, **k)))
    cap, info, status_without = probe()
    assert cap["mode"] == "mock-only" and set(info) == keys and cap == info
    assert status_with == status_without, "research 資訊欄不影響 /health/deep 的狀態碼"


# ══ AT-960-3-1：合法建立 ════════════════════════════════════════════════════════════════════
def test_AT_960_3_1_a_valid_request_creates_row_event_files_and_the_outer_fsm_key(
        env: Env, popen_log: list[list[str]]) -> None:
    body = project_body("agent-memory-gc")
    resp = env.post("/research/projects", body)
    assert resp.status_code == 201, resp.text
    out = resp.json()
    workspace = env.root / "agent-memory-gc"
    assert out["research_id"] == body["research_id"] and out["rp_no"] == "RP-0001"
    assert out["fsm_project"] == "research-agent-memory-gc"
    assert out["workspace_path"] == str(workspace.resolve())
    assert (out["flow"]["step"], out["flow"]["phase"], out["flow"]["status"]) == (
        "topic", "INGESTED", "IDLE")
    assert env.rdb is not None
    assert env.rdb.count("research_projects", "id = %s", body["research_id"]) == 1
    events = env.rdb.events(body["research_id"])
    assert [(e[0], e[1]) for e in events] == [(1, "research.step")]
    artifact = env.rdb.one("SELECT kind, version, rel_path, sha256, bytes FROM "
                           "console.research_artifacts WHERE research_id = %s",
                           body["research_id"])
    assert artifact[:3] == ("ISSUE_SCOPE", 1, layout.ISSUE_SCOPE_REL)
    for name in layout.WORKSPACE_DIRS:
        assert (workspace / name).is_dir(), name
    issue = (workspace / layout.ISSUE_SCOPE_REL).read_bytes()
    assert hashlib.sha256(issue).hexdigest() == artifact[3] and len(issue) == artifact[4]
    doc = json.loads(issue)
    row = project_row(env, body["research_id"])
    assert doc["scope"]["in_scope"] == row["scope"]["in_scope"] == ["記憶體回收"]
    assert doc["layers"] == row["scope"]["layers"] and doc["rp_no"] == row["rp_no"]
    fctx = fsm_ctx_of(env, body["research_id"])
    assert fsm_ops.show(fctx)["current_state"] == "AGENT_LOAD"
    assert read_state(Path(row["fsm_state_dir"]), "research-agent-memory-gc")[
        "current_state"] == "AGENT_LOAD"
    assert verbs(popen_log)[0] == "show" and "--must-exist" not in popen_log[0], \
        "第一個 CLI 呼叫是建檔專用的 show（不帶 --must-exist）"


def test_AT_960_3_1_bad_fields_are_422_and_leave_nothing_behind(env: Env) -> None:
    assert env.rdb is not None
    bad = {"empty title": {"title": ""}, "nul topic": {"topic": "a\x00b"},
           "unknown depth": {"depth_level": "DEEPEST"},
           "no layer": {"scope": {"layers": {"academic": False, "industry": False, "oss": False,
                                              "community": False}, "in_scope": ["x"]}},
           "no in_scope": {"scope": {"layers": {"academic": True, "industry": False, "oss": False,
                                                "community": False}}},
           "bad subject": {"created_by": ""}}
    for label, over in bad.items():
        resp = env.post("/research/projects", project_body(f"s-{abs(hash(label)) % 10 ** 6}",
                                                           **over))
        assert resp.status_code == 422, (label, resp.text)
    for slug in ("..", "a/../b", "A", "a b", "a" * 31):
        resp = env.post("/research/projects", project_body(slug))
        assert resp.status_code == 422, slug
    assert env.rdb.count("research_projects") == 0 and not list(env.root.glob("*"))


def test_AT_960_8_E_2_the_industry_layer_is_refused_while_the_web_layer_is_off(env: Env) -> None:
    assert env.rdb is not None and not env.settings.research_web_allowlist
    body = project_body("web-off")
    body["scope"]["layers"]["industry"] = True
    resp = env.post("/research/projects", body)
    assert resp.status_code == 422 and resp.json()["reason"] == "layer_unavailable"
    assert env.rdb.count("research_projects") == 0 and not (env.root / "web-off").exists()


# ══ AT-960-3-3：同 slug 二次建立 ═════════════════════════════════════════════════════════════
def test_AT_960_3_3_a_second_create_with_the_same_slug_is_409_and_touches_nothing(
        env: Env, popen_log: list[list[str]]) -> None:
    assert env.rdb is not None
    first = create(env, "dup")
    before, calls = tree_digest(env.root), len(popen_log)
    resp = env.post("/research/projects", project_body("dup"))
    assert (resp.status_code, resp.json()["reason"]) == (409, "slug_in_use")
    assert tree_digest(env.root) == before, "既有檔案的位元組與 mtime 不變"
    assert len(popen_log) == calls, "沒有起任何 FSM 子行程"
    nxt = create(env, "other")
    assert (first["rp_no"], nxt["rp_no"]) == ("RP-0001", "RP-0002"), "失敗請求不讓編號前進"
    assert env.rdb.count("research_projects") == 2


# ══ AT-960-3-4：初始化失敗與重試初始化 ═════════════════════════════════════════════════════════
def test_AT_960_3_4_a_failed_init_is_marked_and_only_retry_init_in_that_state_heals_it(
        env: Env, popen_log: list[list[str]]) -> None:
    assert env.rdb is not None
    workspace = env.root / "broken"
    (workspace).mkdir(parents=True)
    (workspace / "01_specs").write_text("占位檔案", encoding="utf-8")      # 故障注入：同名檔案占位
    first = env.post("/research/projects", project_body("broken"))
    assert first.status_code == 201, first.text
    rid = first.json()["research_id"]
    row = project_row(env, rid)
    assert row["flow_status"] == "FAILED" and row["flow_detail"].startswith("init_failed:")
    assert env.rdb.count("research_artifacts", "research_id = %s", rid) == 0
    rp_no = row["rp_no"]
    (workspace / "01_specs").unlink()                                      # 移除故障
    healed = env.post(f"/research/projects/{rid}:reinit", {})
    assert healed.status_code == 200, healed.text
    row = project_row(env, rid)
    assert (row["flow_status"], row["flow_detail"], row["rp_no"]) == ("IDLE", "", rp_no)
    for name in layout.WORKSPACE_DIRS:
        assert (workspace / name).is_dir()
    assert (workspace / layout.ISSUE_SCOPE_REL).is_file()
    assert env.rdb.count("research_artifacts", "research_id = %s AND kind = 'ISSUE_SCOPE'",
                         rid) == 1
    creations = [a for a in popen_log if "--must-exist" not in a and sdd_cli.CLI_MODULE in a]
    assert len(creations) == 1, "FSM 鍵只建一次"
    assert fsm_ops.current_state(fsm_ctx_of(env, rid)) == "AGENT_LOAD"
    before, calls, snap = tree_digest(env.root), len(popen_log), db_snapshot(env, rid)
    again = env.post(f"/research/projects/{rid}:reinit", {})
    assert (again.status_code, again.json()["reason"]) == (409, "stage_conflict")
    details = again.json()["details"]
    assert details["flowStatus"] == "IDLE" and not details["flowDetail"].startswith("init_failed:")
    assert tree_digest(env.root) == before and len(popen_log) == calls
    assert db_snapshot(env, rid) == snap, "零寫入"


def test_AT_960_3_4_retry_init_is_refused_in_every_other_state_with_zero_writes(
        env: Env, popen_log: list[list[str]]) -> None:
    assert env.rdb is not None
    cases = {"escalated": ("ESCALATED", ""), "failed-but-not-init": ("FAILED", "stage_failed:x")}
    for slug, (status, detail) in cases.items():
        rid = create(env, slug)["research_id"]
        env.rdb.exec("UPDATE console.research_projects SET flow_status = %s, flow_detail = %s "
                     "WHERE id = %s", status, detail, rid)
        before, calls, snap = tree_digest(env.root), len(popen_log), db_snapshot(env, rid)
        resp = env.post(f"/research/projects/{rid}:reinit", {})
        assert (resp.status_code, resp.json()["reason"]) == (409, "stage_conflict"), slug
        assert resp.json()["details"] == {"flowStatus": status, "flowDetail": detail}
        assert tree_digest(env.root) == before and len(popen_log) == calls
        assert db_snapshot(env, rid) == snap, slug


# ══ 四類處理函式（原 501 骨架，BR-C 已落地）：先驗證、後動作；被拒的請求不寫任何東西 ═════════════
def test_the_gate_0_return_and_start_handlers_validate_before_acting_and_p1_stays_501(
        env: Env) -> None:
    assert env.rdb is not None
    rid = create(env)["research_id"]
    snap = db_snapshot(env, rid)
    approve = {"prd_version": 1, "expected_digests": {}, "approver": ALICE}
    for path, body, want in (
            (f"/research/projects/{rid}:approve-baseline", approve, (409, "review_not_passed")),
            (f"/research/projects/{rid}:return", {"approver": ALICE, "reason": "補證據"},
             (409, "fsm_state_conflict")),
            (f"/research/projects/{rid}/stages/tcs-draft:start", {"requested_by": ALICE},
             (501, "not_implemented"))):                # P1 的 stage：形狀仍釘住，絕不是 2xx
        resp = env.post(path, body)
        assert (resp.status_code, resp.json()["reason"]) == want, (path, resp.text)
        if resp.status_code == 501:
            out = resp.json()
            assert out["code"] == 501 and out["endpoint"] and out["detail"]
    for bad in ("bridge", "Agent", "SYSTEM", "", "a b", "a+b", "x" * 101, "-rf"):
        resp = env.post(f"/research/projects/{rid}:approve-baseline", {**approve, "approver": bad})
        assert resp.status_code == 422, repr(bad)
    assert env.post(f"/research/projects/{rid}:return",
                    {"approver": ALICE, "reason": ""}).status_code == 422
    assert env.post(f"/research/projects/{uuid.uuid4()}:reconcile", {}).status_code == 404
    assert env.post(f"/research/projects/{rid}/stages/bogus:start",
                    {"requested_by": ALICE}).status_code == 422
    assert db_snapshot(env, rid) == snap, "被拒的請求都不寫任何東西"
    # 會動作的兩個：對帳回 200；research 啟動回 202（引擎沒有 claude、run 立刻失敗，等它結束）
    assert env.post(f"/research/projects/{rid}:reconcile", {}).status_code == 200
    started = env.post(f"/research/projects/{rid}/stages/research:start", {"requested_by": ALICE})
    assert started.status_code == 202, started.text
    settle(env.live, rid)


# ══ AT-960-6-1：游標持久化在 DB ═══════════════════════════════════════════════════════════════
def test_AT_960_6_1_the_cursor_lives_in_the_db_and_survives_a_bridge_restart(
        make_env: Callable[..., Env], rdb: ThrowawayDb, fake: Path) -> None:
    first = make_env(fake, rdb)
    rid = create(first)["research_id"]
    first.db.set_cursor(research_id=rid, actor="bridge", flow={
        "step": "studio", "phase": "REVIEWING", "status": "RUNNING", "detail": ""})
    keys = ("flow_step", "flow_phase", "flow_status", "flow_detail")
    before = {k: project_row(first, rid)[k] for k in keys}
    second = make_env(fake, rdb)             # 「重啟」：全新的 Bridge 行程狀態、同一個資料庫
    assert {k: project_row(second, rid)[k] for k in keys} == before
    events = second.get(f"/research/projects/{rid}/events?after=0&limit=500").json()["items"]
    steps = [e for e in events if e["event_type"] == "research.step"]
    assert steps[-1]["payload"] == {"flowStep": "studio", "flowPhase": "REVIEWING",
                                    "flowStatus": "RUNNING", "flowDetail": ""}
    paths = {r.path for r in second.live.app.routes if hasattr(r, "path")}
    assert not [p for p in paths if "advance" in p or p.endswith("/cursor")]


# ══ AT-960-6-3：stage 前置條件表 ════════════════════════════════════════════════════════════
def _start(env: Env, rid: str, stage: str, **body: Any) -> httpx.Response:
    return env.post(f"/research/projects/{rid}/stages/{stage}:start",
                    {"requested_by": ALICE, **body})


def test_AT_960_6_3_an_unmet_precondition_is_409_with_the_unmet_rules_and_changes_nothing(
        env: Env) -> None:
    assert env.rdb is not None
    rid = create(env)["research_id"]
    assert _start(env, rid, "research").status_code == 202, "INGESTED 滿足前置條件"
    settle(env.live, rid)                      # 啟動真的會動作：等 stage 鏈結束才手改列與拍快照
    env.rdb.exec("UPDATE console.research_projects SET flow_phase = 'DRAFTING' WHERE id = %s", rid)
    snap, expected = db_snapshot(env, rid), {
        "research": [("phase", "DRAFTING")], "draft": [("phase", "DRAFTING")],
        "review": [("head_prd", None)], "revise": [("last_round_failed", None)],
        "iterate": [("last_round_failed", None)]}
    for stage, rules in expected.items():
        resp = _start(env, rid, stage)
        assert (resp.status_code, resp.json()["reason"]) == (409, "stage_conflict"), stage
        got = [(u["rule"], u["current"]) for u in resp.json()["details"]["unmet"]]
        assert got == rules, stage
        assert db_snapshot(env, rid) == snap, f"{stage}：游標、事件帳、DB 皆不變"


def test_AT_960_6_3_an_active_stage_run_blocks_a_second_one_on_the_same_project(
        env: Env) -> None:
    rid = create(env)["research_id"]
    env.db.insert_stage_run(research_id=rid, stage_run_id=str(uuid.uuid4()), stage="RESEARCH",
                            requested_by=ALICE, status="RUNNING")
    resp = _start(env, rid, "research")
    assert (resp.status_code, resp.json()["reason"]) == (409, "stage_conflict")
    assert resp.json()["details"]["activeStage"] == "RESEARCH"


# ══ AT-960-6-4：同專案只有一個進行中的 stage；全站受並行上限節制 ═════════════════════════════════
def event_seqs(env: Env, rid: str) -> list[int]:
    items = env.get(f"/research/projects/{rid}/events?after=0&limit=500").json()["items"]
    return [e["seq"] for e in items]


def test_AT_960_6_4_a_second_start_on_one_project_is_409_and_seq_stays_contiguous(
        env: Env) -> None:
    rid = create(env)["research_id"]
    run_id = str(uuid.uuid4())
    env.db.insert_stage_run(research_id=rid, stage_run_id=run_id, stage="RESEARCH",
                            requested_by=ALICE, status="RUNNING")
    before = event_seqs(env, rid)
    assert before == list(range(1, len(before) + 1)) and len(before) >= 2
    for _ in range(2):
        resp = _start(env, rid, "research")
        assert (resp.status_code, resp.json()["reason"]) == (409, "stage_conflict")
        assert resp.json()["details"] == {"activeStageRunId": run_id, "activeStage": "RESEARCH"}
    assert event_seqs(env, rid) == before, "被拒的啟動不寫事件：seq 自 1 起連續、無重複"


def test_AT_960_6_4_the_site_wide_cap_rejects_a_stage_on_another_project(
        env: Env, make_env: Callable[..., Env]) -> None:
    assert env.rdb is not None
    alpha, beta = create(env, "alpha")["research_id"], create(env, "beta")["research_id"]
    env.db.insert_stage_run(research_id=alpha, stage_run_id=str(uuid.uuid4()), stage="RESEARCH",
                            requested_by=ALICE, status="RUNNING")
    runs = env.rdb.count("research_stage_runs")
    resp = _start(env, beta, "research")
    assert (resp.status_code, resp.json()["reason"]) == (409, "stage_conflict")
    assert resp.json()["details"] == {"cause": "max_concurrent_runs", "limit": 1, "active": 1}
    assert env.rdb.count("research_stage_runs") == runs, "沒有為 beta 建任何 stage run 列"
    # 上限調成 2：同一個請求通過上限這關（前置條件本來就滿足 ⇒ 202）
    wider = make_env(env.tree, env.rdb, research_max_concurrent_runs=2)
    assert _start(wider, beta, "research").status_code == 202
    settle(wider.live, beta)


def test_AT_960_6_4_a_finished_stage_run_no_longer_counts_against_the_cap(env: Env) -> None:
    alpha, beta = create(env, "alpha")["research_id"], create(env, "beta")["research_id"]
    env.db.insert_stage_run(research_id=alpha, stage_run_id=str(uuid.uuid4()), stage="RESEARCH",
                            requested_by=ALICE, status="SUCCEEDED")
    assert env.db.count_active_stage_runs() == 0
    assert _start(env, beta, "research").status_code == 202
    settle(env.live, beta)


def test_AT_960_15_6_in_escalation_new_reviews_and_automatic_revisions_are_blocked(
        env: Env) -> None:
    assert env.rdb is not None
    rid = create(env)["research_id"]
    seed_failed_review(env, rid, rounds=3, escalated=True)
    to_escalation(env, rid)
    runs = env.rdb.count("research_stage_runs")
    for stage in ("iterate", "review", "revise"):
        resp = _start(env, rid, stage)
        assert (resp.status_code, resp.json()["reason"]) == (409, "escalated"), stage
        recovery = resp.json()["details"]["recovery"]
        assert {"target", "powershell", "posix"} <= set(recovery), stage
        assert all(isinstance(recovery[k], str) and recovery[k] for k in ("target", "powershell",
                                                                           "posix"))
    assert env.rdb.count("research_stage_runs") == runs, "沒有新的 stage run 列"


def test_AT_960_15_5_after_escalation_only_reads_the_fsm_and_never_writes_it(
        env: Env, popen_log: list[list[str]]) -> None:
    rid = create(env)["research_id"]
    seed_failed_review(env, rid, rounds=3, escalated=True)
    fctx = to_escalation(env, rid)
    since = len(popen_log)
    flagged = _start(env, rid, "revise", after_escalation=True)
    assert (flagged.status_code, flagged.json()["reason"]) == (409, "fsm_state_conflict")
    assert flagged.json()["details"]["current_state"] == "ESCALATION"
    plain = _start(env, rid, "revise")
    assert (plain.status_code, plain.json()["reason"]) == (409, "escalated")
    human_resume(env.tree, fctx.state_dir, fctx.key)       # 人以框架 CLI 恢復（Bridge 沒有此動詞）
    after = _start(env, rid, "revise", after_escalation=True)
    assert after.status_code == 202, after.text                 # 前置已過 ⇒ 202
    settle(env.live, rid)                                       # 引擎沒有 claude：run 立刻失敗
    assert fsm_ops.current_state(fctx) == "SPEC_DRAFTING"
    assert set(verbs(popen_log, since)) <= {"show"}, "Bridge 的 FSM 呼叫只有唯讀的 show"


# ══ AT-960-6-5：Gate 0 之後一律 spec_frozen ═══════════════════════════════════════════════════
def test_AT_960_6_5_after_gate_0_every_write_action_is_409_spec_frozen(env: Env) -> None:
    assert env.rdb is not None
    rid = create(env)["research_id"]
    env.rdb.exec("UPDATE console.research_projects SET flow_step = 'route', flow_phase = 'FROZEN' "
                 "WHERE id = %s", rid)
    snap = db_snapshot(env, rid)
    put = env.put(f"/research/projects/{rid}/prd", {"base_version": 0, "content": "# x\n",
                                                   "author": ALICE})
    assert (put.status_code, put.json()["reason"]) == (409, "spec_frozen")
    for stage in ("revise", "review"):
        resp = _start(env, rid, stage)
        assert (resp.status_code, resp.json()["reason"]) == (409, "spec_frozen"), stage
    assert env.rdb.count("research_prd_versions") == 0
    assert db_snapshot(env, rid) == snap
    row = project_row(env, rid)
    assert (row["flow_step"], row["flow_phase"]) == ("route", "FROZEN")


# ══ AT-960-6-6：PUT prd 樂觀鎖 ════════════════════════════════════════════════════════════════
def test_AT_960_6_6_two_concurrent_puts_on_the_same_base_one_wins_and_one_conflicts(
        env: Env) -> None:
    assert env.rdb is not None
    rid = create(env)["research_id"]
    url = f"/research/projects/{rid}/prd"
    for base in range(3):
        resp = env.put(url, {"base_version": base, "content": f"# v{base + 1}\n", "author": ALICE})
        assert (resp.status_code, resp.json()["version_no"]) == (201, base + 1)
    old = env.rdb.q("SELECT version_no, sha256 FROM console.research_prd_versions ORDER BY 1")
    results: list[httpx.Response] = []

    def racer(n: int) -> None:
        results.append(env.client.put(url, json={"base_version": 3, "content": f"# racer {n}\n",
                                                 "author": ALICE}, headers=HEAD))

    threads = [threading.Thread(target=racer, args=(n,)) for n in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    assert sorted(r.status_code for r in results) == [201, 409]
    win = next(r for r in results if r.status_code == 201).json()
    lose = next(r for r in results if r.status_code == 409).json()
    assert (win["version_no"], win["semver"]) == (4, "v0.4.0-draft")
    assert (lose["reason"], lose["details"]["headVersion"]) == ("prd_version_conflict", 4)
    rows = env.rdb.q("SELECT version_no, author_kind, author, parent_version_no, sha256 FROM "
                     "console.research_prd_versions ORDER BY 1")
    assert len(rows) == 4 and rows[:3] == [(n, "HUMAN", ALICE, n - 1 or None, old[n - 1][1])
                                           for n in (1, 2, 3)]
    assert rows[3] == (4, "HUMAN", ALICE, 3, win["sha256"])
    on_disk = env.root / "demo" / "01_specs" / "PRD-v0.4.0-draft.md"
    assert hashlib.sha256(on_disk.read_bytes()).hexdigest() == win["sha256"]
    assert project_row(env, rid)["flow_phase"] == "DRAFTING"


def test_AT_960_6_6_bad_prd_content_is_422_and_adds_no_version(env: Env) -> None:
    assert env.rdb is not None
    rid = create(env)["research_id"]
    url = f"/research/projects/{rid}/prd"
    head = {**HEAD, "Content-Type": "application/json"}
    bad = {
        "nul": json.dumps({"base_version": 0, "content": "a\u0000b", "author": ALICE}).encode(),
        "lone surrogate": b'{"base_version":0,"content":"\\ud800","author":"a"}',
        "blank": json.dumps({"base_version": 0, "content": "  ", "author": ALICE}).encode(),
        "too large": json.dumps({"base_version": 0, "content": "a" * 1_048_577,
                                 "author": ALICE}).encode(),
        "no author": json.dumps({"base_version": 0, "content": "x", "author": ""}).encode(),
    }
    for label, raw in bad.items():
        resp = env.client.put(url, content=raw, headers=head)
        assert resp.status_code == 422, (label, resp.text[:200])
    exact = env.client.put(url, content=json.dumps({"base_version": 0, "content": "a" * 1_048_576,
                                                    "author": ALICE}).encode(), headers=head)
    assert exact.status_code == 201, "剛好 1 MiB 位元組可存"
    assert env.rdb.count("research_prd_versions") == 1


# ══ AT-960-8-9：allowlist（有效清單、條款確認、稽核、不寫事件）═══════════════════════════════════
def test_AT_960_8_9_the_allowlist_is_env_base_plus_enabled_admin_entries(env: Env) -> None:
    assert env.rdb is not None
    rid = create(env)["research_id"]
    got = env.get("/research/allowlist").json()
    env_entries = {e["host"]: e["min_interval_seconds"] for e in got["items"]
                   if e["source"] == "ENV"}
    assert env_entries == {"export.arxiv.org": 3, "arxiv.org": 3, "api.semanticscholar.org": 3,
                           "api.github.com": 60, "api.stackexchange.com": 3}
    assert got["effective"] == {"FETCH": list(env_entries), "WEB": []}
    assert "reddit" not in json.dumps(got).lower()
    events = env.rdb.count("research_events")
    audit = len([e for e in _audit_lines(env) if e["result"] == "ok"])
    added = env.post("/research/allowlist", {
        "list_kind": "FETCH", "host": "Docs.Example.com.", "layer": "INDUSTRY",
        "purpose": "官方文件", "min_interval_seconds": 5, "added_by": ADMIN})
    assert added.status_code == 201, added.text
    entry = added.json()
    assert (entry["host"], entry["added_by"], entry["enabled"], entry["source"]) == (
        "docs.example.com", ADMIN, True, "ADMIN")
    assert "docs.example.com" in env.get("/research/allowlist").json()["effective"]["FETCH"]
    refused = env.post("/research/allowlist", {
        "list_kind": "FETCH", "host": "reddit.com", "layer": "COMMUNITY", "added_by": ADMIN})
    assert (refused.status_code, refused.json()["reason"]) == (422, "terms_ack_required")
    acked = env.post("/research/allowlist", {
        "list_kind": "FETCH", "host": "reddit.com", "layer": "COMMUNITY", "added_by": ADMIN,
        "tos_acknowledged": True})
    assert acked.status_code == 201
    twice = env.post("/research/allowlist", {
        "list_kind": "FETCH", "host": "docs.example.com", "layer": "INDUSTRY", "added_by": ADMIN})
    assert (twice.status_code, twice.json()["reason"]) == (409, "allowlist_exists")
    for interval in (0, 3601):
        resp = env.post("/research/allowlist", {
            "list_kind": "WEB", "host": "x.example.org", "layer": "INDUSTRY", "added_by": ADMIN,
            "min_interval_seconds": interval})
        assert resp.status_code == 422, interval
    off = env.patch(f"/research/allowlist/{entry['id']}", {"enabled": False, "disabled_by": ADMIN})
    assert off.status_code == 200 and off.json()["enabled"] is False
    assert off.json()["disabled_by"] == ADMIN
    assert "docs.example.com" not in env.get("/research/allowlist").json()["effective"]["FETCH"]
    extra = env.patch(f"/research/allowlist/{entry['id']}",
                      {"enabled": True, "minIntervalSeconds": 1})
    assert extra.status_code == 422
    still = next(e for e in env.get("/research/allowlist").json()["items"]
                 if e["id"] == entry["id"])
    assert still["enabled"] is False and still["min_interval_seconds"] == 5, "條目不變"
    assert env.rdb.count("research_events") == events, "allowlist 變更不寫 research_events（D-52）"
    ok_after = len([e for e in _audit_lines(env) if e["result"] == "ok"])
    assert ok_after - audit == 3, "三次成功的變更（新增兩筆、停用一筆）各使 bridge.audit 多一筆"
    assert project_row(env, rid)["slug"] == "demo"


# ══ 取消、封存、復原 ═══════════════════════════════════════════════════════════════════════════
def test_cancel_archive_and_restore(env: Env) -> None:
    assert env.rdb is not None
    rid = create(env)["research_id"]
    idle = env.post(f"/research/projects/{rid}:cancel", {})
    assert idle.status_code == 200 and idle.json()["stopped_run_id"] is None
    run_id = str(uuid.uuid4())
    env.db.insert_stage_run(research_id=rid, stage_run_id=run_id, stage="RESEARCH",
                            requested_by=ALICE, status="RUNNING")
    assert env.post(f"/research/projects/{rid}:archive", {}).status_code == 409
    done = env.post(f"/research/projects/{rid}:cancel", {})
    assert done.status_code == 200 and done.json()["stopped_run_id"] == run_id
    assert env.rdb.one("SELECT status, exit_reason FROM console.research_stage_runs "
                       "WHERE id = %s", run_id) == ("CANCELLED", "cancelled")
    assert project_row(env, rid)["flow_status"] == "CANCELLED"
    assert env.post(f"/research/projects/{rid}:archive", {}).status_code == 200
    assert project_row(env, rid)["archived_at"] is not None
    assert create(env, "demo")["research_id"] != rid, "封存後 slug 可再用"
    taken = env.post(f"/research/projects/{rid}:restore", {})
    assert (taken.status_code, taken.json()["reason"]) == (409, "slug_in_use")


# ══ AT-960-15-8：換世代 ═══════════════════════════════════════════════════════════════════════
def _control_in_human_pending(env: Env) -> str:
    rid = create(env, "other")["research_id"]
    ctx = fsm_ctx_of(env, rid)
    fsm_ops.transition(ctx, to="SPEC_DRAFTING", reason="start drafting")
    fsm_ops.transition(ctx, to="SCG_VALIDATION", reason="ready for review")
    fsm_ops.gate(ctx, gate="SCG_VALIDATION", result="PASS", reason="the review passed")
    assert fsm_ops.current_state(ctx) == "HUMAN_PENDING"
    return rid


def test_AT_960_15_8_generation_next_abandons_the_old_key_in_one_transaction(
        env: Env, popen_log: list[list[str]]) -> None:
    assert env.rdb is not None
    rid = create(env, "demo")["research_id"]
    seed_failed_review(env, rid, rounds=3, escalated=True)
    env.db.record_gate_decision(research_id=rid, decision_id=str(uuid.uuid4()), gate="GATE0",
                                decision="CHANGES", decided_by=ALICE, fsm_project="research-demo",
                                fsm_state_after="HUMAN_PENDING", reason="人工退回")
    old = to_escalation(env, rid)
    other = _control_in_human_pending(env)
    url = f"/research/projects/{rid}:reinit"
    snap = db_snapshot(env, rid)
    for label, body in (("no reason", {"generation": "next", "decided_by": ADMIN}),
                        ("blank reason", {"generation": "next", "reason": "  ",
                                          "decided_by": ADMIN})):
        resp = env.post(url, body)
        assert (resp.status_code, resp.json()["reason"]) == (422, "invalid_request"), label
        assert db_snapshot(env, rid) == snap, label
    old_bytes = (old.state_dir / f"FSM-STATE-{old.key}.yaml").read_bytes()
    rounds_before = env.rdb.q("SELECT id, round_no, fsm_generation FROM "
                              "console.research_review_rounds ORDER BY round_no")
    prd_before = env.rdb.q("SELECT version_no, sha256 FROM console.research_prd_versions "
                           "ORDER BY 1")
    since = len(popen_log)
    ok = env.post(url, {"generation": "next", "reason": "重新來過", "decided_by": ADMIN})
    assert ok.status_code == 200, ok.text
    out = ok.json()
    assert (out["fsm_project"], out["fsm_generation"]) == ("research-demo-g2", 2)
    row = project_row(env, rid)
    assert (row["fsm_project"], row["fsm_generation"]) == ("research-demo-g2", 2)
    assert (row["flow_phase"], row["flow_status"]) == ("REVISING", "IDLE")
    decision = env.rdb.one(
        "SELECT id, gate, decision, decided_by, fsm_project, fsm_state_after, reason FROM "
        "console.research_gate_decisions WHERE gate = 'ABANDON_KEY'")
    assert str(decision[0]) == out["gate_decision_id"]
    assert decision[1:] == ("ABANDON_KEY", "ABANDONED", ADMIN, "research-demo", "ESCALATION",
                            "重新來過")
    assert env.rdb.q("SELECT version_no, sha256 FROM console.research_prd_versions ORDER BY 1") \
        == prd_before
    assert env.rdb.q("SELECT id, round_no, fsm_generation FROM console.research_review_rounds "
                     "ORDER BY round_no") == rounds_before
    assert all(r[2] == 1 for r in rounds_before), "既有輪列仍屬世代 1"
    tail = [(e[1], e[6]) for e in env.rdb.events(rid)][-2:]
    assert tail[0][0] == "research.gate" and tail[0][1]["gate"] == "ABANDON_KEY"
    assert (tail[0][1]["decision"], tail[0][1]["decidedBy"]) == ("ABANDONED", ADMIN)
    assert tail[1][0] == "research.step" and tail[1][1]["flowPhase"] == "REVISING"
    new = fsm_ops.FsmCtx(sdd_root=env.tree, state_dir=old.state_dir, key="research-demo-g2")
    shown = fsm_ops.show(new)
    assert shown["current_state"] == "AGENT_LOAD"
    assert shown["retry_history"]["SCG_VALIDATION"]["current_count"] == 0
    assert (old.state_dir / f"FSM-STATE-{old.key}.yaml").read_bytes() == old_bytes
    assert fsm_ops.current_state(old) == "ESCALATION"
    window = [a for a in popen_log[since:] if sdd_cli.CLI_MODULE in a]
    old_calls = [a for a in window if a[a.index("--project") + 1] == old.key]
    assert all(a[a.index(sdd_cli.CLI_MODULE) + 1] == "show" for a in old_calls)
    assert "resume-from-escalation" not in verbs(popen_log)
    view = env.get(f"/sdd/fsm/research-demo-g2?root={env.root / 'demo'}").json()
    assert all(g["current_count"] == 0 for g in view["retry_gates"].values())
    assert env.get(f"/sdd/fsm/research-demo?root={env.root / 'demo'}").json()["retry_gates"][
        "SCG_VALIDATION"]["current_count"] == 3
    assert env.rdb.count("research_gate_decisions", "research_id = %s AND gate = 'GATE0' AND "
                         "decision = 'CHANGES' AND fsm_project = 'research-demo-g2'", rid) == 0
    control_snap, calls = db_snapshot(env, other), len(popen_log)
    refused = env.post(f"/research/projects/{other}:reinit",
                       {"generation": "next", "reason": "不該成功", "decided_by": ADMIN})
    assert (refused.status_code, refused.json()["reason"]) == (409, "fsm_state_conflict")
    assert refused.json()["details"]["current_state"] == "HUMAN_PENDING"
    assert db_snapshot(env, other) == control_snap and len(popen_log) == calls


def test_AT_960_15_E_1_a_failed_new_key_leaves_the_db_ahead_and_retry_init_heals_it(
        env: Env, popen_log: list[list[str]], monkeypatch: pytest.MonkeyPatch) -> None:
    assert env.rdb is not None
    rid = create(env, "demo")["research_id"]
    seed_failed_review(env, rid, rounds=3, escalated=True)
    old = to_escalation(env, rid)
    old_bytes = (old.state_dir / f"FSM-STATE-{old.key}.yaml").read_bytes()
    real_create, flaky = fsm_ops.create_key, {"fail": True}

    def create_key(ctx: fsm_ops.FsmCtx, *, allowed_roots: Any) -> str:
        if flaky["fail"]:
            raise ApiError(502, "sdd_cli_failed", detail="injected")
        return real_create(ctx, allowed_roots=allowed_roots)

    monkeypatch.setattr(fsm_ops, "create_key", create_key)
    first = env.post(f"/research/projects/{rid}:reinit",
                     {"generation": "next", "reason": "重新來過", "decided_by": ADMIN})
    assert first.status_code == 200, first.text
    row = project_row(env, rid)
    assert (row["fsm_generation"], row["fsm_project"]) == (2, "research-demo-g2")
    assert (row["flow_status"], row["flow_detail"]) == ("FAILED", "init_failed:fsm")
    assert env.rdb.count("research_gate_decisions", "gate = 'ABANDON_KEY'") == 1
    assert not (old.state_dir / "FSM-STATE-research-demo-g2.yaml").exists(), "新鍵狀態檔不存在"
    assert (old.state_dir / f"FSM-STATE-{old.key}.yaml").read_bytes() == old_bytes
    flaky["fail"] = False
    healed = env.post(f"/research/projects/{rid}:reinit", {})
    assert healed.status_code == 200, healed.text
    new = fsm_ops.FsmCtx(sdd_root=env.tree, state_dir=old.state_dir, key="research-demo-g2")
    assert fsm_ops.current_state(new) == "AGENT_LOAD"
    row = project_row(env, rid)
    assert (row["flow_phase"], row["flow_status"], row["flow_detail"]) == ("REVISING", "IDLE", "")
    before, calls, snap = tree_digest(env.root), len(popen_log), db_snapshot(env, rid)
    third = env.post(f"/research/projects/{rid}:reinit", {})
    assert (third.status_code, third.json()["reason"]) == (409, "stage_conflict")
    assert third.json()["details"] == {"flowStatus": "IDLE", "flowDetail": ""}
    assert tree_digest(env.root) == before and len(popen_log) == calls
    assert db_snapshot(env, rid) == snap and env.rdb.count(
        "research_gate_decisions", "gate = 'ABANDON_KEY'") == 1
    assert "resume-from-escalation" not in verbs(popen_log)


# ══ AT-960-8-9（抓取面；PKG-BR-B 補，append-only）：端點與抓取層共用常數與有效清單 ═══════════
def test_AT_960_8_9_the_router_imports_the_single_interval_table_from_the_fetch_layer() -> None:
    import ast

    from app.research.fetch import allowlist as fetch_allowlist
    from app.routers import research as research_router

    assert research_router.ENV_MIN_INTERVALS is fetch_allowlist.ENV_MIN_INTERVALS
    assert research_router.DEFAULT_ENV_MIN_INTERVAL == fetch_allowlist.DEFAULT_ENV_MIN_INTERVAL
    tree = ast.parse(Path(research_router.__file__).read_text(encoding="utf-8"))
    assigned = {t.id for node in tree.body if isinstance(node, ast.Assign | ast.AnnAssign)
                for t in (node.targets if isinstance(node, ast.Assign) else [node.target])
                if isinstance(t, ast.Name)}
    assert not {"ENV_MIN_INTERVALS", "DEFAULT_ENV_MIN_INTERVAL"} & assigned, \
        "節流下限表的唯一定義在 research/fetch/allowlist.py；路由只 import"


def test_AT_960_8_9_the_fetch_layer_builds_its_list_from_the_endpoint_rows_and_values_only_lengthen(
        env: Env) -> None:
    from app.research.fetch import build_effective_allowlist

    assert env.rdb is not None
    entries = {}
    for host, layer, interval in (("export.arxiv.org", "ACADEMIC", 1),
                                  ("docs.example.com", "INDUSTRY", 20)):
        added = env.post("/research/allowlist", {
            "list_kind": "FETCH", "host": host, "layer": layer, "min_interval_seconds": interval,
            "added_by": ADMIN})
        assert added.status_code == 201, added.text
        entries[host] = added.json()["id"]
    got = env.get("/research/allowlist").json()
    fetch_list = build_effective_allowlist(env.settings.research_fetch_allowlist,
                                           env.db.list_allowlist())
    assert list(fetch_list.hosts) == got["effective"]["FETCH"]
    listed = {(e["host"], e["source"]): e["min_interval_seconds"] for e in got["items"]}
    assert listed[("export.arxiv.org", "ENV")] == 3 and listed[("export.arxiv.org", "ADMIN")] == 1
    assert (fetch_list.interval("export.arxiv.org"), fetch_list.interval("docs.example.com")) == (
        3, 20), "ADMIN 條目填 1 低於內建下限 3，仍以 3 執行；填 20 高於下限，以 20 執行"
    off = env.patch(f"/research/allowlist/{entries['docs.example.com']}",
                    {"enabled": False, "disabled_by": ADMIN})
    assert off.status_code == 200
    after = build_effective_allowlist(env.settings.research_fetch_allowlist,
                                      env.db.list_allowlist())
    assert "docs.example.com" not in after.hosts
    assert list(after.hosts) == env.get("/research/allowlist").json()["effective"]["FETCH"]
    assert [row["host"] for row in after.snapshot()] == [
        "export.arxiv.org", "arxiv.org", "api.semanticscholar.org", "api.github.com",
        "api.stackexchange.com", "export.arxiv.org"], "快照逐條列出基底與啟用中的 ADMIN 條目"
    assert "reddit.com" not in after.hosts, "Reddit 預設不在任何清單"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# PKG-BR-C 附加（append-only；上方既有測試只依「本體已落地」做必要同步，見檔頭）：
# AT-960-6-4（假 claude 延遲下兩專案真並行）、7-6（mock-only）、8-9（stage 快照）。
# ══════════════════════════════════════════════════════════════════════════════════════════════
def _stage_rig(make_bridge: Callable[..., Any], settings: Settings, tmp_path: Path,
               monkeypatch: pytest.MonkeyPatch, tree: Path, rdb: ThrowawayDb, **over: Any
               ) -> tuple[Any, str]:
    """活 Bridge＋FC（假 claude）＋注入假抓取層的 orchestrator；回 (rig, 劇本路徑)。"""
    from tests import test_research_orchestrator as orch

    script = orch.custom_script(tmp_path, lambda steps: None)
    return orch.build_rig(make_bridge, settings, tmp_path, monkeypatch, tree, rdb, script=script,
                          **over), script


def test_AT_960_6_4_two_projects_really_run_in_parallel_when_the_cap_is_two_and_conflicts_hold(
        make_bridge: Callable[..., Any], settings: Settings, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch, tree: Path, rdb: ThrowawayDb) -> None:
    from tests import test_research_orchestrator as orch

    rig, script = _stage_rig(make_bridge, settings, tmp_path, monkeypatch, tree, rdb,
                             research_max_concurrent_runs=2)
    orch.patch_step(script, "research", 0, delay=4)                  # 假 claude 延遲
    alpha, beta, gamma = (orch.create(rig, slug) for slug in ("alpha", "beta", "gamma"))
    orch.run_stage(rig, alpha, "research", wait=False)
    orch.run_stage(rig, beta, "research", wait=False)
    orch.wait_until(lambda: rig.db.count_active_stage_runs() == 2, 30)   # 兩專案同時在跑
    again = rig.post(f"/research/projects/{alpha}/stages/research:start", {"requested_by": ALICE})
    assert (again.status_code, again.json()["reason"]) == (409, "stage_conflict")
    assert set(again.json()["details"]) == {"activeStageRunId", "activeStage"}
    third = rig.post(f"/research/projects/{gamma}/stages/research:start", {"requested_by": ALICE})
    assert (third.status_code, third.json()["reason"]) == (409, "stage_conflict")
    assert third.json()["details"] == {"cause": "max_concurrent_runs", "limit": 2, "active": 2}
    assert rig.orch.join(alpha, 120) and rig.orch.join(beta, 120)
    for rid in (alpha, beta):
        assert [r["status"] for r in orch.runs_of(rig, rid, "RESEARCH")] == ["SUCCEEDED"]
        seqs = [e["seq"] for e in rig.db.list_events(rid, limit=500)]
        assert seqs == list(range(1, len(seqs) + 1)), "序號自 1 起連續、無重複"
    calls = [json.loads(x) for x in rig.trace.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len([c for c in calls if c.get("role") == "research"]) >= 2, "兩專案各起了一個假 claude"


def test_AT_960_7_6_mock_only_mode_still_accepts_the_research_stage(
        make_bridge: Callable[..., Any], settings: Settings, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch, tree: Path, rdb: ThrowawayDb) -> None:
    import shutil

    from tests import test_research_orchestrator as orch

    real_which = shutil.which
    monkeypatch.setattr(shutil, "which", lambda cmd, *a, **k: None if cmd == "claude" else
                        real_which(cmd, *a, **k))                  # PATH 上沒有 claude：mock-only
    rig, _script = _stage_rig(make_bridge, settings, tmp_path, monkeypatch, tree, rdb)
    assert rig.client.get("/research/capabilities").json()["mode"] == "mock-only"
    assert rig.client.get("/health/deep").json()["research"]["mode"] == "mock-only"
    rid = orch.create(rig)
    body = orch.run_stage(rig, rid, "research").json()               # 202 且 stage 完成
    assert body["stage_run_id"] and "reason" not in body, "沒有任何「停用」錯誤（停用只在 UI 層）"
    assert [r["status"] for r in orch.runs_of(rig, rid, "RESEARCH")] == ["SUCCEEDED"]
    assert rig.client.get("/research/capabilities").json()["mode"] == "mock-only"


def test_AT_960_8_9_the_stage_snapshot_follows_the_effective_allowlist_entry_by_entry(
        make_bridge: Callable[..., Any], settings: Settings, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch, tree: Path, rdb: ThrowawayDb) -> None:
    from tests import test_research_orchestrator as orch

    rig, _script = _stage_rig(make_bridge, settings, tmp_path, monkeypatch, tree, rdb,
                              research_web_allowlist=("base.example.org",))
    rid = orch.create(rig)

    def snapshot() -> set[tuple[str, str, str]]:
        run = orch.runs_of(rig, rid, "RESEARCH")[-1]
        return {(e["list_kind"], e["host"], e["source"]) for e in run["allowlist_snapshot"]}

    base = {("FETCH", host, "ENV") for host in rig.settings.research_fetch_allowlist}
    assert len(base) == 5 and not any("reddit" in host for _k, host, _s in base)
    orch.run_stage(rig, rid, "research")
    assert snapshot() == {*base, ("WEB", "base.example.org", "ENV")}, "預設：五個基底主機＋環境 WEB"
    audit = rig.settings.engine_workspace / "_audit.jsonl"
    audits = audit.read_text(encoding="utf-8").count("\n") if audit.is_file() else 0
    events = rig.rdb.count("research_events")
    added = rig.post("/research/allowlist", {
        "list_kind": "WEB", "host": "blog.example.org", "layer": "INDUSTRY", "purpose": "產業",
        "min_interval_seconds": 5, "tos_acknowledged": False, "added_by": ADMIN})
    assert added.status_code == 201, added.text
    assert added.json()["added_by"] == ADMIN
    reddit = rig.post("/research/allowlist", {
        "list_kind": "WEB", "host": "reddit.com", "layer": "COMMUNITY", "purpose": "社群",
        "min_interval_seconds": 5, "tos_acknowledged": False, "added_by": ADMIN})
    assert (reddit.status_code, reddit.json()["reason"]) == (422, "terms_ack_required")
    assert rig.post("/research/allowlist", {
        "list_kind": "WEB", "host": "reddit.com", "layer": "COMMUNITY", "purpose": "社群",
        "min_interval_seconds": 5, "tos_acknowledged": True, "added_by": ADMIN}).status_code == 201
    assert rig.rdb.count("research_events") == events, "allowlist 變更不寫 research_events（D-52）"
    assert (audit.read_text(encoding="utf-8").count("\n") if audit.is_file() else 0) > audits
    orch.run_stage(rig, rid, "research")
    assert ("WEB", "blog.example.org", "ADMIN") in snapshot(), "新增條目出現在下一個 stage 的快照"
    off = rig.client.patch(f"/research/allowlist/{added.json()['id']}",
                           json={"enabled": False, "disabled_by": ADMIN}, headers=HEAD)
    assert off.status_code == 200 and off.json()["disabled_by"] == ADMIN
    orch.run_stage(rig, rid, "research")
    assert ("WEB", "blog.example.org", "ADMIN") not in snapshot(), "停用後不再出現"
    assert {h for _k, h, _s in snapshot()} >= {h for _k, h, _s in base}
