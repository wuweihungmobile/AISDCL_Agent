"""`tcs-draft` stage：前置、編譯（spec-engineer 變體）、確定性驗證、發佈與登記、內環鍵序列（TCS
AT-961-9-*；PKG-BR-D2）。引擎的 claude 是 mock 劇本（`MOCK_CLAUDE_RESEARCH_SCRIPT`），真 git／真 FSM
CLI／拋棄式庫。機密樣式的字面一律在執行期拼接（commit 時的機密掃描閘會擋形狀像機密的字面）。
"""
from __future__ import annotations

import json
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from app import sdd_cli
from app.research import fsm_ops
from app.research.compile import StageRequest, compile_stage
from app.research.gates import tcs_schema
from tests import research_git_support as rgs
from tests import test_research_router as rt
from tests.fixtures.research import fake_claude
from tests.test_decompose import FakeBrain, step
from tests.test_research_decompose import PRD, post_decompose, use_brain
from tests.test_research_scr import ADMIN, cursor, inner

make_env = rt.make_env
route_db, real_tree, renv, fake_gh = rgs.route_db, rgs.real_tree, rgs.renv, rgs.fake_gh
FIXTURES = Path(__file__).parent / "fixtures" / "research" / "scripts"
OK_DRAFT = (FIXTURES / "content" / "tcs_ok.md").read_text(encoding="utf-8")
ALL_ACS = ["AC-001-1", "AC-001-2", "AC-002-1", "AC-003-1", "AC-003-2"]
ALICE = rt.ALICE


def set_script(renv: rgs.RouteEnv, monkeypatch: pytest.MonkeyPatch, draft: str,
               name: str = "script") -> None:
    """把 mock claude 的研究劇本換成「寫出 `draft`」（劇本與內容放在 tmp，位元組原樣）。"""
    directory = renv.tmp / f"tcs-{name}-{uuid.uuid4().hex[:6]}"
    (directory / "content").mkdir(parents=True)
    (directory / "content" / "draft.md").write_text(draft, encoding="utf-8", newline="\n")
    script = {"schema": 1, "steps": [{"role": "tcs-draft", "round": 0, "writes": [
        {"path": "03_execution/tcs_draft.md", "from": "content/draft.md"}]}]}
    (directory / "script.json").write_text(json.dumps(script), encoding="utf-8", newline="\n")
    monkeypatch.setenv("MOCK_CLAUDE_RESEARCH_SCRIPT", str(directory / "script.json"))
    monkeypatch.setenv("MOCK_CLAUDE_TRACE", str(renv.tmp / "fc_trace.jsonl"))
    monkeypatch.setenv("FAKE_CLAUDE_STATE", str(renv.tmp / "fc_state.json"))


def enable_claude(renv: rgs.RouteEnv) -> None:
    """引擎的 claude＝FC 啟動器（orchestrator 與 context 都改用新設定）。"""
    launcher = fake_claude.make_launcher(renv.tmp / "bin")
    app = renv.env.live.app
    cfg = replace(app.state.settings, research_claude_command=launcher,
                  research_step_timeout_seconds=60)
    app.state.settings = cfg
    app.state.research.cfg = cfg
    app.state.research.orchestrator.cfg = cfg


def ready(renv: rgs.RouteEnv, monkeypatch: pytest.MonkeyPatch, draft: str = OK_DRAFT,
          *, decompose: bool = True) -> str:
    """Given：已分流、（選）已有拆解列、mock claude 就緒。"""
    rid = rgs.seed_gate0(renv, prd=PRD)
    assert rgs.confirm(renv, rid, rgs.body_a(renv)).status_code == 200
    use_brain(renv, FakeBrain([step(1), step(2, ["S01"])]), renv.tmp)
    if decompose:
        assert post_decompose(renv, rid).status_code == 200
    enable_claude(renv)
    set_script(renv, monkeypatch, draft)
    return rid


def start(renv: rgs.RouteEnv, rid: str, *, expect: int = 202, wait: bool = True) -> Any:
    resp = renv.env.post(f"/research/projects/{rid}/stages/tcs-draft:start",
                         {"requested_by": ALICE})
    assert resp.status_code == expect, resp.text
    if wait and expect == 202:
        assert renv.env.live.app.state.research.orchestrator.join(rid, 240), "stage 鏈逾時"
    return resp


def tcs_runs(renv: rgs.RouteEnv, rid: str) -> list[tuple[Any, ...]]:
    return renv.rdb.q("SELECT stage, status, exit_reason, prompt_manifest FROM "
                      "console.research_stage_runs WHERE research_id = %s AND stage = 'TCS_DRAFT' "
                      "ORDER BY created_at", rid)


def trace(renv: rgs.RouteEnv, route: dict[str, Any]) -> list[tuple[Any, Any, Any]]:
    entries = fsm_ops.show(inner(renv, route))["decision_trace"]
    return [(e.get("from") or e.get("from_state"), e.get("to") or e.get("to_state"),
             e.get("trigger")) for e in entries]


# ── 驗證器（純函式）：AT-961-9-3 的規則 ────────────────────────────────────────────────────
def rules_of(text: str, name: str | None = None) -> list[str]:
    return sorted({v.rule for v in tcs_schema.validate(text, ALL_ACS, file_name=name)})


def secret_text() -> str:
    # 執行期拼接：commit 時的機密掃描閘會擋形狀像機密的字面
    token = "gh" + "p_" + "A" * 36
    return OK_DRAFT + f"\n密碼備忘：{token}\n"


def test_AT_961_9_3_the_validator_rules_on_the_five_bad_variants_and_the_good_one() -> None:
    assert rules_of(OK_DRAFT, "TCS-demo-20261107.md") == []
    no_last = OK_DRAFT.split("```gherkin\n# AT-003-2-1")[0].rstrip() + "\n"
    assert rules_of(no_last) == ["ac_uncovered"]
    assert rules_of(OK_DRAFT + "\n```gherkin\n# AT-009-1-1\n# 判定：x\n```\n") == ["at_orphan"]
    empty = OK_DRAFT.replace("# 判定：python -m pytest tests -k AT_001_1_1 -q", "# 判定：")
    assert rules_of(empty) == ["judge_command_empty"]
    assert rules_of(secret_text()) == ["secret"]
    assert rules_of(OK_DRAFT, "demo.md") == ["file_name"]
    assert rules_of("沒有任何 AT 標頭") == ["ac_uncovered", "no_at"]
    summary = tcs_schema.summarize(tcs_schema.validate(secret_text(), ALL_ACS))
    assert "gh" + "p_" not in json.dumps(summary), "摘要不含機密原文"


def test_the_evaluator_entry_point_reads_only_the_workspace_files(tmp_path: Path) -> None:
    (tmp_path / "03_execution").mkdir()
    inputs = {"acs": [{"id": a, "title": ""} for a in ALL_ACS]}
    (tmp_path / "03_execution" / "tcs_inputs.json").write_text(json.dumps(inputs),
                                                               encoding="utf-8")
    assert tcs_schema.main(["--workspace", str(tmp_path)]) == 1, "草稿缺席＝違規"
    (tmp_path / "03_execution" / "tcs_draft.md").write_text(OK_DRAFT, encoding="utf-8")
    assert tcs_schema.main(["--workspace", str(tmp_path)]) == 0
    (tmp_path / "03_execution" / "tcs_draft.md").write_text(secret_text(), encoding="utf-8")
    assert tcs_schema.main(["--workspace", str(tmp_path)]) == 1


def test_the_spec_engineer_tcs_variant_has_the_minimum_authority(real_tree: Path,
                                                                 tmp_path: Path) -> None:
    compiled = compile_stage(StageRequest(
        stage="tcs-draft", slug="demo", workspace=tmp_path, framework_root=real_tree,
        step_timeout_seconds=60, prd_rel="01_specs/PRD-v1.0.0.md"))
    tools = " ".join(compiled.tools)
    for forbidden in ("Bash", "PowerShell", "Task", "Agent", "WebSearch", "WebFetch"):
        assert forbidden not in tools
    [task] = compiled.playbook["tasks"]
    assert len(task["prompt"]) <= 1000 and ".prompts/tcs-draft.md" in task["prompt"]
    assert "\n" not in task["prompt"]
    assert "tcs_schema" in task["evaluator_command"]
    [persona] = compiled.personas
    assert persona.role == "tcs-draft" and "AT-" in persona.text
    assert compiled.prompt_manifest[0]["role"] == "tcs-draft"
    assert compiled.env["CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS"] == "60000"


# ── AT-961-9-1：前置 ─────────────────────────────────────────────────────────────────────────
def unmet(resp: Any) -> list[str]:
    return [u["rule"] for u in resp.json()["details"]["unmet"]]


def test_AT_961_9_1_unmet_preconditions_are_409_listed_one_by_one_with_zero_writes(
        renv: rgs.RouteEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    unrouted = rgs.seed_gate0(renv, "other", prd=PRD)
    resp = start(renv, unrouted, expect=409)
    assert resp.json()["reason"] == "fsm_state_conflict"
    assert unmet(resp) == ["route_not_succeeded", "decomposition_missing"]
    rid = ready(renv, monkeypatch, decompose=False)
    runs = renv.rdb.count("research_stage_runs")
    resp = start(renv, rid, expect=409)
    assert unmet(resp) == ["decomposition_missing"]
    assert renv.rdb.count("research_stage_runs") == runs, "所有 409 零寫入"
    renv.rdb.exec("INSERT INTO console.research_scr (research_id, scr_no, kind, source_kind, "
                  "reason, status, requested_by) VALUES (%s, 1, 'MINOR', 'HUMAN', 'x', 'OPEN', "
                  "'x')", rid)
    resp = start(renv, rid, expect=409)
    assert resp.json()["reason"] == "scr_open"
    assert tcs_runs(renv, rid) == []


def test_AT_961_9_1_an_active_stage_run_is_stage_conflict(
        renv: rgs.RouteEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    rid = ready(renv, monkeypatch)
    renv.env.db.insert_stage_run(research_id=rid, stage_run_id=str(uuid.uuid4()),
                                 stage="REVIEW", round_no=9, requested_by=ALICE,
                                 status="RUNNING")
    resp = start(renv, rid, expect=409)
    assert resp.json()["reason"] == "stage_conflict"


# ── AT-961-9-2／9-4／9-E-1：成功路徑 ─────────────────────────────────────────────────────────
def test_AT_961_9_4_success_publishes_registers_and_walks_the_inner_key_with_tcs_gate(
        renv: rgs.RouteEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    rid = ready(renv, monkeypatch)
    ws = Path(renv.env.db.get_project(rid)["workspace_path"])
    route = renv.env.db.active_route(rid)
    prd_before = (ws / "01_specs" / "PRD-v1.0.0.md").read_bytes()
    decision_before = (ws / "02_governance" / "route_decision.json").read_bytes()
    gates_before = renv.rdb.count("research_gate_decisions")
    seen: list[tuple[str, str]] = []
    real = sdd_cli.run_research_verb
    monkeypatch.setattr(sdd_cli, "run_research_verb", lambda verb, args, **k: (
        seen.append((verb, k.get("project", ""))), real(verb, args, **k))[1])
    resp = start(renv, rid)
    assert resp.json()["stage_run_id"] and resp.json()["engine_run_id"]
    [run] = tcs_runs(renv, rid)
    assert run[:3] == ("TCS_DRAFT", "SUCCEEDED", "")
    assert run[3][0]["role"] == "tcs-draft"
    # 內環鍵：先 SPEC_DRAFTING，通過後 SCG_VALIDATION、HUMAN_PENDING（理由前綴 tcs gate）
    assert fsm_ops.current_state(inner(renv, route)) == "HUMAN_PENDING"
    tail = trace(renv, route)[-3:]
    assert [t[1] for t in tail] == ["SPEC_DRAFTING", "SCG_VALIDATION", "HUMAN_PENDING"]
    last_reason = json.dumps(fsm_ops.show(inner(renv, route))["decision_trace"][-1],
                             ensure_ascii=False)
    assert "tcs gate" in last_reason
    verbs = [v for v, key in seen if key == route["impl_fsm_project"] and v != "show"]
    assert verbs == ["transition"] * 3, "Bridge 對內環鍵只做 transition（沒有 gate／凍結）"
    # 發佈與登記
    name = tcs_schema.target_name("demo", __import__("datetime").datetime.now(
        __import__("datetime").UTC).strftime("%Y%m%d"))
    published = Path(route["target_path"]) / "docs" / "03_testing" / "contracts" / name
    assert published.read_bytes() == (ws / "03_execution" / "tcs_draft.md").read_bytes()
    worktree = Path(route["target_path"]).parent
    assert rgs.git(worktree, "log", "-1", "--format=%s").startswith("docs: 發佈")
    art = renv.rdb.one("SELECT sha256, rel_path FROM console.research_artifacts WHERE "
                       "research_id = %s AND kind = 'TCS'", rid)
    assert art is not None and art[1].endswith(name)
    dec = renv.rdb.one("SELECT tcs_rel_path, tcs_sha256 FROM console.research_decompositions "
                       "WHERE research_id = %s", rid)
    assert dec is not None and dec[0] == art[1] and dec[1].strip() == art[0].strip()
    assert cursor(renv, rid)[:2] == ("build", "TCS_PENDING")
    phases = [e[6]["flowPhase"] for e in renv.rdb.events(rid) if e[1] == "research.step"]
    assert "TCS_DRAFTING" in phases and phases[-1] == "TCS_PENDING"
    assert [e[1] for e in renv.rdb.events(rid) if e[1] == "research.run"], "stage 事件在"
    # 9-E-1：已凍結的規格不被碰
    assert (ws / "01_specs" / "PRD-v1.0.0.md").read_bytes() == prd_before
    assert (ws / "02_governance" / "route_decision.json").read_bytes() == decision_before
    assert renv.rdb.count("research_gate_decisions") == gates_before


# ── AT-961-9-3／9-E-2：五個壞變體與重試 ───────────────────────────────────────────────────────
def test_AT_961_9_3_each_bad_draft_fails_as_tcs_invalid_and_keeps_the_inner_key_drafting(
        renv: rgs.RouteEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    rid = ready(renv, monkeypatch, secret_text())
    route = renv.env.db.active_route(rid)
    docs = Path(route["target_path"]) / "docs" / "03_testing" / "contracts"
    start(renv, rid)
    [run] = tcs_runs(renv, rid)
    assert run[1] == "FAILED" and run[2] == "tcs_invalid"
    assert not docs.exists() or not list(docs.glob("TCS-*.md")), "目標 docs 無新檔"
    assert renv.rdb.count("research_artifacts", "kind = 'TCS'") == 0
    assert fsm_ops.current_state(inner(renv, route)) == "SPEC_DRAFTING"
    alert = [e[6] for e in renv.rdb.events(rid) if e[1] == "research.alert"][-1]
    assert alert["kind"] == "tcs_invalid" and ("gh" + "p_") not in json.dumps(alert)
    flow = cursor(renv, rid)
    assert flow[2] == "FAILED" and flow[3].startswith("tcs_invalid: "), flow     # D-131
    assert "機密" in flow[3] and ("gh" + "p_") not in flow[3]
    bad_variants = {
        "missing_ac": OK_DRAFT.split("```gherkin\n# AT-003-2-1")[0].rstrip() + "\n",
        "orphan": OK_DRAFT + "\n```gherkin\n# AT-009-1-1\n# 判定：x\n```\n",
        "empty_judge": OK_DRAFT.replace(
            "# 判定：python -m pytest tests -k AT_001_1_1 -q", "# 判定：")}
    for name, draft in bad_variants.items():
        set_script(renv, monkeypatch, draft, name)
        start(renv, rid)
        assert tcs_runs(renv, rid)[-1][1:3] == ("FAILED", "tcs_invalid"), name
        assert fsm_ops.current_state(inner(renv, route)) == "SPEC_DRAFTING", name
        if name == "missing_ac":
            assert "AC-003-2" in cursor(renv, rid)[3], "游標說明帶缺項（D-131）"
    # 9-E-2：排除故障後再啟動成功，且 SPEC_DRAFTING 的 transition 不重複
    drafting_before = [t for t in trace(renv, route) if t[1] == "SPEC_DRAFTING"]
    set_script(renv, monkeypatch, OK_DRAFT, "fixed")
    start(renv, rid)
    assert tcs_runs(renv, rid)[-1][1] == "SUCCEEDED"
    assert fsm_ops.current_state(inner(renv, route)) == "HUMAN_PENDING"
    assert [t for t in trace(renv, route) if t[1] == "SPEC_DRAFTING"] == drafting_before
    assert len(drafting_before) == 2, "採納一次、Stage-2 一次（失敗後的重試不重複）"
    assert renv.rdb.count("research_artifacts", "kind = 'TCS'") == 1


def test_a_missing_mock_script_step_fails_loudly_instead_of_succeeding_silently(
        renv: rgs.RouteEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    rid = ready(renv, monkeypatch)
    monkeypatch.setenv("MOCK_CLAUDE_RESEARCH_SCRIPT", str(renv.tmp / "no-such-script.json"))
    start(renv, rid)
    assert tcs_runs(renv, rid)[-1][1] == "FAILED"
    assert ADMIN
