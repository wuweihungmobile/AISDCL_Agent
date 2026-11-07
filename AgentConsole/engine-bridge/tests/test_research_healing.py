"""自癒監視器（TCS AT-962-6、7、8；PKG-BR-P2）。

純函式部分（導出、遮蔽、截尾、漂移偵測）不需環境；整合部分用 P1 的真 FSM／真 git／拋棄式庫夾具
（`renv`），視圖資料以 SQL 直接播進 `execution_runs`／`execution_steps`（引擎寫入面不在本包）。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import pytest

from app.research import healing

CASES_PATH = Path(__file__).resolve().parent / "fixtures" / "research" / (
    "healing_redaction_cases.json")
HEALING_SRC = Path(healing.__file__).read_text(encoding="utf-8")
FAKE_TOKEN = "ghp_FAKE_R2P2_TOKEN_000000000000000000"


def view_row(run: str, task: str, step: int, status: str = "RETRYING", message: str = "boom",
             run_number: int = 1) -> dict[str, Any]:
    return {"run_id": run, "run_number": run_number, "task_id": task, "step_number": step,
            "status": status, "error_message": message, "occurred_at": "2026-11-07T12:00:00+00:00"}


# ── AT-962-6-3：attempt 導出 ────────────────────────────────────────────────────────────────────
def test_AT_962_6_3_attempt_is_the_nth_step_of_the_same_run_and_task() -> None:
    rows = [view_row("r1", "A", 9), view_row("r1", "A", 3), view_row("r1", "B", 4),
            view_row("r1", "A", 5), view_row("r2", "A", 1, run_number=2)]
    out = healing.derive_entries(rows)
    pairs = [(e["run_id"], e["task_id"], e["step_number"], e["attempt"]) for e in out]
    assert pairs == [("r1", "A", 3, 1), ("r1", "B", 4, 1), ("r1", "A", 5, 2), ("r1", "A", 9, 3),
                     ("r2", "A", 1, 1)], "同 task 依 step_number 升冪；另一 task、另一 run 各自重數"
    assert set(out[0]) == set(healing.LOG_KEYS)


# ── AT-962-6-4：excerpt 取遮蔽後尾端 300 字元（字元不是位元組）────────────────
@pytest.mark.parametrize("length", [299, 300, 301])
def test_AT_962_6_4_excerpt_keeps_the_last_300_characters(length: int) -> None:
    text = "".join(chr(0x4E00 + i % 500) for i in range(length))
    out = healing.excerpt(text)
    assert out == (text if length <= 300 else text[-300:])
    assert len(out) == min(length, 300) and len(out.encode("utf-8")) > 300 * 2, "以字元計、非位元組"


def test_AT_962_6_4_empty_and_none_become_the_empty_string() -> None:
    assert healing.excerpt(None) == "" and healing.excerpt("") == ""


# ── AT-962-7-1／7-E-2：兩端對拍夾具逐筆（含誤殺負控）──────────────────────────
def load_cases() -> list[dict[str, Any]]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def test_AT_962_7_1_the_shared_fixture_covers_every_secret_category() -> None:
    cases = load_cases()
    joined = "\n".join(c["input"] for c in cases)
    for needle in ("ghp_", "github_pat_", "sk-ant-", "Bearer ", "AWS_SECRET=", "password=", "AKIA"):
        assert needle in joined, f"夾具缺少類別 {needle}"
    assert any(c.get("keep") for c in cases), "夾具須含誤殺負控（keep）"
    assert all(set(c) <= {"input", "expected", "keep"} for c in cases)


@pytest.mark.parametrize("case", [c for c in load_cases() if not c.get("keep")],
                         ids=lambda c: c["input"][:24])
def test_AT_962_7_1_mask_matches_the_fixture_expected_value(case: dict[str, Any]) -> None:
    assert healing.mask(case["input"]) == case["expected"]


@pytest.mark.parametrize("case", [c for c in load_cases() if c.get("keep")],
                         ids=lambda c: c["input"][:24])
def test_AT_962_7_E_2_non_secrets_are_not_masked(case: dict[str, Any]) -> None:
    assert healing.mask(case["input"]) == case["input"] == case["expected"]


# ── AT-962-7-2：研究面恆遮 ──────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("switch", ["false", "0", "", "off"])
def test_AT_962_7_2_masking_ignores_the_log_redaction_switch(
        switch: str, monkeypatch: pytest.MonkeyPatch) -> None:
    name = "REDACT_SECRETS_" + "IN_LOGS"
    monkeypatch.setenv(name, switch)
    assert FAKE_TOKEN not in healing.mask(f"x {FAKE_TOKEN} y")
    assert "hunter2" not in healing.mask("password=hunter2")
    assert name not in HEALING_SRC and "secrets_redaction_enabled" not in HEALING_SRC
    assert name in os.environ


# ── AT-962-7-E-1：先遮蔽再截尾 ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("start", [99, 90, 70, 285])
def test_AT_962_7_E_1_a_token_crossing_the_boundary_leaves_no_fragment(start: int) -> None:
    text = "a" * start + FAKE_TOKEN + "b" * (400 - start - len(FAKE_TOKEN))
    out = healing.excerpt(text)      # 總長 400：尾端 300 字元自第 100 字元起，token 跨過邊界
    assert len(out) <= 300
    for fragment in (FAKE_TOKEN[:8], "FAKE_R2P2", "000000"):
        assert fragment not in out, (start, out[-60:])


# ── AT-962-8-2／8-E-2：detect_spec_change ───────────────────────────────────────────────────────
def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_AT_962_8_2_clean_tree_is_quiet_union_covers_all_stages_overlap_counted_once(
        tmp_path: Path) -> None:
    (tmp_path / "a.md").write_bytes(b"A")
    (tmp_path / "b.md").write_bytes(b"B")
    (tmp_path / "c.md").write_bytes(b"C")
    stages = [{"stage": "Stage-1", "spec_doc_digests": {"a.md": f"sha256:{sha(b'A')}",
                                                         "b.md": f"sha256:{sha(b'B')}"}},
              {"stage": "Stage-2", "spec_doc_digests": {"b.md": f"sha256:{sha(b'B')}",
                                                         "c.md": sha(b"C")}}]
    union = healing.union_digests(stages)
    assert union == {"a.md": sha(b"A"), "b.md": sha(b"B"), "c.md": sha(b"C")}
    assert healing.detect_spec_change(union, tmp_path) == []
    (tmp_path / "b.md").write_bytes(b"B!")
    drift = healing.detect_spec_change(union, tmp_path)
    assert drift == [{"path": "b.md", "expected": sha(b"B"), "actual": sha(b"B!")}], "只報一次"


def test_AT_962_8_E_2_a_deleted_frozen_file_is_drift_not_an_exception(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_bytes(b"A")
    digests = {"a.md": sha(b"A"), "gone.md": sha(b"G"), "../escape.md": sha(b"E")}
    drift = healing.detect_spec_change(digests, tmp_path)
    assert {d["path"]: d["actual"] for d in drift} == {"gone.md": "missing",
                                                       "../escape.md": "missing"}


def test_AT_962_8_E_3_the_module_never_claims_a_patch_was_rejected() -> None:
    sample = healing.drift_line([{"path": "p", "expected": "e", "actual": "a"}])
    assert not re.search(r"reject|block|denied", json.dumps(sample), re.IGNORECASE)
    assert sample["spec_change"] is True and sample["paths"] == ["p"]
    assert healing.ALERT_SPEC_CHANGE == "SPEC_CHANGE_FORBIDDEN"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 整合：真 FSM／真 git／拋棄式庫（P1 的 `renv` 夾具）；視圖資料以 SQL 播進引擎的表
# ══════════════════════════════════════════════════════════════════════════════════════════════
import ast  # noqa: E402
import threading  # noqa: E402
import uuid  # noqa: E402
from concurrent.futures import ThreadPoolExecutor  # noqa: E402

from app.research import db as db_module  # noqa: E402
from app.research import gitops  # noqa: E402
from tests import research_git_support as rgs  # noqa: E402
from tests import test_research_inner_gates as ig  # noqa: E402
from tests import test_research_router as rt  # noqa: E402
from tests.test_research_scr import ADMIN, routed  # noqa: E402

make_env = rt.make_env
route_db, real_tree, renv, fake_gh = rgs.route_db, rgs.real_tree, rgs.renv, rgs.fake_gh
rtm = ig.rtm
LOG_REL = "03_execution/healing_history.log"


def console_of(renv: rgs.RouteEnv, rid: str) -> str:
    row = renv.rdb.one("SELECT console_project_id FROM console.research_projects WHERE id = %s",
                       rid)
    assert row is not None and row[0] is not None, "分流後研究專案應已綁 console 專案"
    return str(row[0])


def seed_steps(renv: rgs.RouteEnv, rid: str, steps: list[tuple[str, int, str, str]], *,
               run_number: int = 1, run_id: str | None = None) -> str:
    """在該研究專案綁定的 console 專案播一個 run 與其 execution_steps。`steps`＝
    `(task 代號, step_number, status, error_message)`；回 run id。"""
    project = console_of(renv, rid)
    if run_id is None:
        row = renv.rdb.one(
            "INSERT INTO console.execution_runs (project_id, run_number, status, autonomy_level, "
            "scope) VALUES (%s, %s, 'COMPLETED', 1, '{}'::jsonb) RETURNING id", project, run_number)
        assert row is not None
        run_id = str(row[0])
    goal = renv.rdb.one("INSERT INTO console.goals (project_id, name, pass_criteria) VALUES "
                        "(%s, 'g', 'x') RETURNING id", project)
    assert goal is not None
    tasks: dict[str, str] = {}
    for key, number, status, message in steps:
        if key not in tasks:
            made = renv.rdb.one("INSERT INTO console.tasks (goal_id, name, pass_criteria) VALUES "
                                "(%s, %s, 'x') RETURNING id", goal[0], key)
            assert made is not None
            tasks[key] = str(made[0])
        renv.rdb.exec(
            "INSERT INTO console.execution_steps (run_id, task_id, step_number, action, status, "
            "error_message) VALUES (%s, %s, %s, 'act', %s, %s)",
            run_id, tasks[key], number, status, message)
    return run_id


def sync(renv: rgs.RouteEnv, rid: str) -> Any:
    return renv.env.post(f"/research/projects/{rid}:healing-sync", {})


def log_path(renv: rgs.RouteEnv, rid: str) -> Path:
    return Path(renv.env.db.get_project(rid)["workspace_path"]) / LOG_REL


def log_lines(renv: rgs.RouteEnv, rid: str) -> list[dict[str, Any]]:
    path = log_path(renv, rid)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def view_keys(renv: rgs.RouteEnv, rid: str) -> set[tuple[str, int]]:
    return {(str(r[0]), int(r[1])) for r in renv.rdb.q(
        "SELECT run_id, step_number FROM console.v_research_healing_attempts "
        "WHERE research_id = %s", rid)}


# ── AT-962-6-1：視圖列與日誌行逐筆一致 ────────────────────────────────────────────────────────────
def test_AT_962_6_1_view_rows_and_log_lines_agree_key_for_key(renv: rgs.RouteEnv) -> None:
    rid, _route = routed(renv)
    for number in (1, 2, 3):
        seed_steps(renv, rid, [("A", 1, "RETRYING", f"第 {number} 次失敗"),
                               ("A", 2, "FAILED", "耗盡")], run_number=number)
    resp = sync(renv, rid)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body) == {"view_rows", "log_lines", "appended", "spec_change"}
    assert (body["view_rows"], body["log_lines"], body["appended"]) == (6, 6, 6)
    lines = log_lines(renv, rid)
    assert all(set(line) == set(healing.LOG_KEYS) for line in lines)
    assert {(line["run_id"], line["step_number"]) for line in lines} == view_keys(renv, rid)
    assert [line["attempt"] for line in lines if line["run_id"] == lines[0]["run_id"]] == [1, 2]


# ── AT-962-6-2：冪等 ────────────────────────────────────────────────────────────────────────────
def test_AT_962_6_2_a_repeated_sync_appends_only_the_missing_rows(renv: rgs.RouteEnv) -> None:
    rid, _route = routed(renv)
    run = seed_steps(renv, rid, [("A", 1, "RETRYING", "e1"), ("A", 2, "RETRYING", "e2")])
    assert sync(renv, rid).json()["appended"] == 2
    first = log_path(renv, rid).read_bytes()
    seed_steps(renv, rid, [("B", 3, "FAILED", "e3"), ("B", 4, "FAILED", "e4")], run_id=run)
    assert sync(renv, rid).json()["appended"] == 2
    grown = log_path(renv, rid).read_bytes()
    assert grown.startswith(first), "既有行不被改寫"
    assert sync(renv, rid).json()["appended"] == 0
    assert log_path(renv, rid).read_bytes() == grown


# ── AT-962-6-5：日誌上限 ────────────────────────────────────────────────────────────────────────
def test_AT_962_6_5_the_production_limit_is_two_mebibytes() -> None:
    assert healing.HEALING_LOG_MAX_BYTES == 2_097_152


@pytest.mark.parametrize(("delta", "fits"), [(-1, 1), (0, 2), (1, 2)],
                         ids=["one-byte-short", "exact", "one-over"])
def test_AT_962_6_5_the_log_stops_at_the_limit_with_one_truncated_line_and_one_alert(
        renv: rgs.RouteEnv, monkeypatch: pytest.MonkeyPatch, delta: int, fits: int) -> None:
    rid, _route = routed(renv)
    seed_steps(renv, rid, [("A", 1, "RETRYING", "e1"), ("A", 2, "RETRYING", "e2"),
                           ("A", 3, "RETRYING", "e3")])
    sizes = [len((healing._line(e) + "\n").encode("utf-8")) for e in healing.derive_entries(
        renv.env.db.list_healing_attempts(rid))]
    limit = sizes[0] + sizes[1] + delta
    monkeypatch.setattr(healing, "HEALING_LOG_MAX_BYTES", limit)
    body = sync(renv, rid).json()
    assert body["appended"] == fits
    data = log_path(renv, rid).read_bytes()
    assert data.endswith(b'{"truncated":true}\n') and data.count(b'"truncated"') == 1
    assert len(data) <= limit + len(b'{"truncated":true}\n')
    alerts = [p for p in ig.events_of(renv, rid, "research.alert")
              if p["kind"] == "HEALING_LOG_TRUNCATED"]
    assert len(alerts) == 1
    again = sync(renv, rid).json()
    assert again["appended"] == 0 and log_path(renv, rid).read_bytes() == data
    assert len([p for p in ig.events_of(renv, rid, "research.alert")
                if p["kind"] == "HEALING_LOG_TRUNCATED"]) == 1


# ── AT-962-6-6：寫檔形態 ────────────────────────────────────────────────────────────────────────
def test_AT_962_6_6_the_log_is_written_through_write_text_atomic_as_lf_utf8(
        renv: rgs.RouteEnv) -> None:
    tree = ast.parse(HEALING_SRC)
    names = {n.attr if isinstance(n, ast.Attribute) else n.id for n in ast.walk(tree)
             if isinstance(n, ast.Attribute | ast.Name)}
    assert not names & {"replace", "rename", "move"}, "不得新增目錄項原語站點"
    assert "write_text_atomic" in names
    for call in (n for n in ast.walk(tree) if isinstance(n, ast.Call)):
        if getattr(call.func, "attr", "") in {"read_text", "write_text"} or getattr(
                call.func, "id", "") == "open":
            assert any(k.arg == "encoding" for k in call.keywords), ast.unparse(call)
    rid, _route = routed(renv)
    seed_steps(renv, rid, [("A", 1, "RETRYING", "中文錯誤訊息")])
    assert sync(renv, rid).status_code == 200
    data = log_path(renv, rid).read_bytes()
    assert b"\r" not in data and "中文錯誤訊息".encode() in data and b"\\u" not in data


# ── AT-962-6-7：只多一個唯讀方法 ────────────────────────────────────────────────────────────────
def test_AT_962_6_7_the_new_read_methods_are_select_only_and_the_write_surface_is_unchanged(
        renv: rgs.RouteEnv) -> None:
    import inspect

    assert set(db_module.WRITE_METHODS) == set(db_module.METHOD_KINDS)
    assert "delivery.record" not in db_module.OPS and "delivery.record" in db_module.P2_OPS
    for method in ("list_healing_attempts", "get_gate_decision", "list_gate_decisions",
                   "list_deliveries", "list_task_states"):
        source = inspect.getsource(getattr(db_module.ResearchDb, method)).upper()
        writes = ("INSERT ", "UPDATE ", "DELETE ")
        assert "SELECT" in source and not any(w in source for w in writes)
    with pytest.raises(db_module.ResearchDbError):
        with renv.env.db.transaction(read_only=True) as tx:
            tx.run("INSERT INTO {s}.v_research_healing_attempts (research_id) VALUES (%s)",
                   (str(uuid.uuid4()),))


# ── AT-962-6-E-1：無資料＝無操作 ────────────────────────────────────────────────────────────────
def test_AT_962_6_E_1_nothing_to_sync_is_a_no_op_and_creates_no_file(renv: rgs.RouteEnv) -> None:
    unbound = rgs.seed_gate0(renv, "unbound")
    rid, _route = routed(renv, "bound-empty")
    for target in (unbound, rid):
        events = len(renv.rdb.events(target))
        body = sync(renv, target).json()
        assert (body["view_rows"], body["appended"], body["spec_change"]) == (0, 0, [])
        assert not log_path(renv, target).exists()
        assert len(renv.rdb.events(target)) == events


# ── AT-962-6-E-2：並行 ──────────────────────────────────────────────────────────────────────────
def test_AT_962_6_E_2_concurrent_syncs_never_duplicate_a_row(renv: rgs.RouteEnv) -> None:
    rid, _route = routed(renv)
    seed_steps(renv, rid, [("A", n, "RETRYING", f"e{n}") for n in range(1, 7)])
    barrier = threading.Barrier(2)

    def go() -> int:
        barrier.wait()
        return int(sync(renv, rid).json()["appended"])

    with ThreadPoolExecutor(2) as pool:
        counts = list(pool.map(lambda _i: go(), range(2)))
    assert sum(counts) == 6
    keys = [(line["run_id"], line["step_number"]) for line in log_lines(renv, rid)]
    assert len(keys) == len(set(keys)) == 6


# ── AT-962-6-E-3：DB 阻塞 ───────────────────────────────────────────────────────────────────────
def test_AT_962_6_E_3_a_blocked_database_answers_503_and_leaves_the_log_untouched(
        renv: rgs.RouteEnv) -> None:
    rid, _route = routed(renv)
    seed_steps(renv, rid, [("A", 1, "RETRYING", "e1")])
    assert sync(renv, rid).status_code == 200
    before = log_path(renv, rid).read_bytes()
    renv.rdb.block()
    try:
        resp = sync(renv, rid)
    finally:
        renv.rdb.unblock()
    assert (resp.status_code, resp.json()["reason"]) == (503, "db_blocked")
    assert log_path(renv, rid).read_bytes() == before


# ── AT-962-7-4：log 檔零明文 token ──────────────────────────────────────────────────────────────
def test_AT_962_7_4_the_log_file_holds_no_token_and_the_source_rows_are_untouched(
        renv: rgs.RouteEnv) -> None:
    rid, _route = routed(renv)
    seed_steps(renv, rid, [("A", 1, "RETRYING", f"push failed with {FAKE_TOKEN} at the end")])
    source_sql = ("SELECT error_message FROM console.execution_steps ORDER BY step_number")
    view_sql = ("SELECT error_message FROM console.v_research_healing_attempts "
                "WHERE research_id = %s")
    before = (renv.rdb.q(source_sql), renv.rdb.q(view_sql, rid))
    assert sync(renv, rid).status_code == 200
    assert FAKE_TOKEN.encode() not in log_path(renv, rid).read_bytes()
    assert (renv.rdb.q(source_sql), renv.rdb.q(view_sql, rid)) == before
    assert FAKE_TOKEN in before[0][0][0], "來源列本就保留原文（遮蔽只發生在輸出面）"


# ── AT-962-8-1／8-3／8-E-1／8-E-3：偵測、告警、不還原 ───────────────────────────────────────────
def drifted(renv: rgs.RouteEnv, slug: str = "demo") -> tuple[str, dict[str, Any], Path, bytes]:
    rid, route = routed(renv, slug)
    target = ig.frozen_prd(route)
    changed = target.read_bytes() + b"\n<!-- hand edit -->\n"
    target.write_bytes(changed)
    return rid, route, target, changed


def test_AT_962_8_1_a_hand_edited_frozen_file_is_reported_and_never_rewritten(
        renv: rgs.RouteEnv) -> None:
    rid, _route, target, changed = drifted(renv)
    resp = sync(renv, rid)
    assert resp.status_code == 200, resp.text
    drift = resp.json()["spec_change"]
    assert [d["path"] for d in drift] == ["docs/01_requirements/demo_PRD.md"]
    assert drift[0]["expected"] != drift[0]["actual"] == sha(changed)
    assert target.read_bytes() == changed


def test_AT_962_8_3_the_same_drift_is_logged_and_alerted_exactly_once(renv: rgs.RouteEnv) -> None:
    rid, _route, _target, _changed = drifted(renv)
    for _ in range(2):
        assert sync(renv, rid).status_code == 200
    spec_lines = [line for line in log_lines(renv, rid) if line.get("spec_change")]
    assert len(spec_lines) == 1 and set(spec_lines[0]) == {
        "spec_change", "paths", "expected", "actual"}
    alerts = [p for p in ig.events_of(renv, rid, "research.alert")
              if p["kind"] == "SPEC_CHANGE_FORBIDDEN"]
    assert len(alerts) == 1 and json.loads(alerts[0]["detail"])["spec_change"] is True


def test_AT_962_8_4_the_three_detection_points_behave_as_decided(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    real, calls = healing.detect_spec_change, []
    monkeypatch.setattr(healing, "detect_spec_change",
                        lambda *a, **k: (calls.append(1), real(*a, **k))[1])
    rid, route, _target, _changed = drifted(renv)
    ig.inner_to(renv, route, "IMPLEMENTATION")
    assert sync(renv, rid).status_code == 200 and len(calls) == 1
    for gate in ("PR_REVIEW", "RTM_VERIFY", "RELEASE_READY"):
        before = len(calls)
        resp = ig.post_gate(renv, rid, gate, "FAIL" if gate == "RELEASE_READY" else "PASS")
        assert (resp.status_code, resp.json()["reason"]) == (422, "digest_mismatch"), gate
        assert len(calls) == before + 1
    before = len(calls)
    tag = renv.env.post(f"/research/projects/{rid}:tag", {"tag_name": "v1.0.0",
                                                          "approver": ADMIN})
    assert (tag.status_code, tag.json()["reason"]) == (422, "digest_mismatch")
    assert len(calls) == before + 1
    assert tag.json()["details"]["drift"][0]["path"] == "docs/01_requirements/demo_PRD.md"
    assert renv.rdb.count("research_deliveries") == 0 and ig.gate_rows(renv, rid) == []
    clean, _croute = routed(renv, "clean")
    assert sync(renv, clean).json()["spec_change"] == []


def test_AT_962_8_E_1_detection_calls_no_git_command_at_all(renv: rgs.RouteEnv) -> None:
    rid, _route, target, changed = drifted(renv)
    seen: list[Any] = []
    gitops.OBSERVERS.append(seen.append)
    try:
        assert sync(renv, rid).status_code == 200
    finally:
        gitops.OBSERVERS.remove(seen.append)
    forbidden = {"checkout", "restore", "reset", "clean", "stash"}
    assert not [r for r in seen if forbidden & set(r.argv)]
    assert target.read_bytes() == changed


def test_AT_962_8_E_3_responses_and_events_never_claim_a_rejection(renv: rgs.RouteEnv) -> None:
    rid, _route, _target, _changed = drifted(renv)
    resp = sync(renv, rid)
    text = json.dumps(resp.json()) + json.dumps(ig.events_of(renv, rid, "research.alert"))
    assert not re.search(r"reject|block|denied", text, re.IGNORECASE)
    kinds = {p["kind"] for p in ig.events_of(renv, rid, "research.alert")}
    assert kinds == {"SPEC_CHANGE_FORBIDDEN"}
