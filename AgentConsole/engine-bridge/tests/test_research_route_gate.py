"""分流輸入閘與預演（TCS AT-961-2-*、3-*；PKG-BR-D1）。

純函式驗證（`route.validate_request`）用表驅動；HTTP 面用活 Bridge、拋棄式庫、拋棄式 git 倉與真
SDD 樹（缺 `SDD_ROOT`＝`TOOL-ABSENCE` skip）。預演一律量「前後相同」：主工作樹、目錄樹、資料庫列數。
"""
from __future__ import annotations

import ast
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from autoclaude.utils.shell_deny_chars import BASE_DENY_CHARS

from app.research import gitops, route
from app.research import settings as research_settings
from tests import research_git_support as rgs
from tests import test_research_router as rt

make_env = rt.make_env
route_db, real_tree, renv, fake_gh = rgs.route_db, rgs.real_tree, rgs.renv, rgs.fake_gh
APP_DIR = Path(route.__file__).resolve().parents[1]
CAPS = route.RouteCaps(templates=("python-fastapi",), worktree_root=Path("/x/wt"),
                       scaffold_root=Path("/x/sc"), repo_root=Path("/x/repo"), rp_no="RP-0007",
                       slug="demo")
INFO = {"target_scope": "UNDECIDED", "default_target_module": "agentconsole"}
A = {"track": "A", "target_module": "agentconsole"}
B = {"track": "B", "project_name": "demo-app", "stack_template": "python-fastapi",
     "owner": "octocat"}


def rules(body: dict[str, Any], info: dict[str, Any] | None = None) -> list[tuple[str, str]]:
    return [(v["field"], v["rule"]) for v in route.validate_request(body, CAPS, info or INFO)]


@pytest.fixture
def calls() -> Iterator[list[gitops.CallRecord]]:
    log: list[gitops.CallRecord] = []
    gitops.OBSERVERS.append(log.append)
    try:
        yield log
    finally:
        gitops.OBSERVERS.remove(log.append)


def world(renv: rgs.RouteEnv) -> dict[str, Any]:
    """零副作用的量測面：主工作樹、worktree 根、scaffold 根、資料庫列數。"""
    return {"git": rgs.snapshot(renv.repo), "wt": rgs.tree_hash(renv.worktrees),
            "sc": rgs.tree_hash(renv.scaffold),
            "rows": {t: renv.rdb.count(t) for t in (
                "research_events", "research_route_decisions", "research_route_steps",
                "research_artifacts", "projects")}}


# ══ AT-961-2-1：欄位驗證表 ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize(("body", "expected"), [
    ({"track": "C"}, [("track", "invalid_track")]),
    ({}, [("track", "required")]),
    ({**A, "branch_name": "feature/issue-0007"}, []),
    ({**A, "branch_name": "feature/" + "a" * 40}, []),
    ({**A, "branch_name": "feature/" + "a" * 41}, [("branch_name", "branch_name_pattern")]),
    ({**A, "branch_name": "feature/Abc"}, [("branch_name", "branch_name_pattern")]),
    ({**A, "branch_name": "feature/a_b"}, [("branch_name", "branch_name_pattern")]),
    ({**A, "branch_name": "hotfix/x"}, [("branch_name", "branch_name_pattern")]),
    ({**A, "target_module": "other"}, [("target_module", "unknown_target_module")]),
    ({**B, "project_name": "ab"}, []),
    ({**B, "project_name": "a" * 62, "repo_name": "ab"}, []),
    ({**B, "project_name": "a"}, [("project_name", "project_name_pattern")]),
    ({**B, "project_name": "a" * 63, "repo_name": "ab"},
     [("project_name", "project_name_pattern")]),
    ({**B, "project_name": "Abc"}, [("project_name", "project_name_pattern")]),
    ({**B, "project_name": "1abc"}, [("project_name", "project_name_pattern")]),
    ({**B, "project_name": "research-x"}, [("project_name", "reserved_prefix")]),
    ({**B, "repo_name": "ab"}, []),
    ({**B, "repo_name": "a" * 39}, []),
    ({**B, "repo_name": "a"}, [("repo_name", "repo_name_pattern")]),
    ({**B, "repo_name": "a" * 40}, [("repo_name", "repo_name_pattern")]),
    ({**B, "repo_name": "Abc"}, [("repo_name", "repo_name_pattern")]),
    ({**B, "repo_name": "a_b"}, [("repo_name", "repo_name_pattern")]),
    ({**B, "owner": "o"}, []),
    ({**B, "owner": "o" * 39}, []),
    ({**B, "owner": "o" * 40}, [("owner", "owner_pattern")]),
    ({**B, "owner": "-o"}, [("owner", "owner_pattern")]),
    ({**B, "owner": "o_o"}, [("owner", "owner_pattern")]),
    ({**B, "visibility": "private"}, [("visibility", "invalid_visibility")]),
    ({**B, "stack_template": "node"}, [("stack_template", "unknown_template")]),
    ({**B, "stack_template": ""}, [("stack_template", "unknown_template")]),
    ({**B, "ci": "yes"}, [("ci", "invalid_type")]),
    ({**B, "docker_compose": "yes"}, [("docker_compose", "invalid_type")]),
    ({**A, "target_path": "/etc"}, [("target_path", "retired_field")]),
    ({**B, "create_github": True, "owner": None}, []),
], ids=lambda v: str(v)[:60])
def test_AT_961_2_1_the_field_table(body: dict[str, Any], expected: list[tuple[str, str]]) -> None:
    body = {k: v for k, v in body.items() if v is not None}
    if body.get("create_github") is True and "owner" not in body:
        expected = [("owner", "required")]
    assert rules(body) == expected


@pytest.mark.parametrize(("reason", "expected"), [
    ("x", []), ("x" * 200, []), ("x" * 201, [("scope_differs_reason", "scope_differs_reason_max")]),
    ("", [("scope_differs_reason", "scope_differs_reason_required")]),
    ("   ", [("scope_differs_reason", "scope_differs_reason_required")]),
    (None, [("scope_differs_reason", "scope_differs_reason_required")])])
def test_AT_961_2_1_the_scope_reason_bounds(reason: str | None,
                                           expected: list[tuple[str, str]]) -> None:
    info = {**INFO, "target_scope": "AISDLC_MODULE"}                 # 軌道 B 與 PRD 的範圍不同
    body = {**B, **({} if reason is None else {"scope_differs_reason": reason})}
    assert rules(body, info) == expected


def test_AT_961_2_1_several_violations_are_listed_in_field_order() -> None:
    body = {**B, "project_name": "A", "owner": "-", "visibility": "x", "target_path": "/x",
            "ci": 1}
    assert [f for f, _r in rules(body)] == ["project_name", "owner", "visibility", "ci",
                                           "target_path"]


def test_AT_961_2_1_the_default_visibility_is_private_and_the_default_branch_uses_rp_no() -> None:
    req = route.normalize_request(A, CAPS, INFO)
    assert req.branch_name == "feature/issue-0007" and req.base_ref == "main"
    assert route.normalize_request(B, CAPS, INFO).visibility == "PRIVATE"


# ══ AT-961-2-E-1：常數單一來源 ══════════════════════════════════════════════════════════════════
def test_AT_961_2_E_1_the_constants_equal_the_registry_table() -> None:
    assert route.BRANCH_PATTERN == r"^feature/[a-z0-9-]{1,40}$"
    assert route.REPO_NAME_PATTERN == r"^[a-z][a-z0-9-]{1,38}$"
    assert route.PROJECT_NAME_PATTERN == r"^[a-z][a-z0-9-]{1,61}$"
    assert route.OWNER_PATTERN == r"^[A-Za-z0-9][A-Za-z0-9-]{0,38}$"
    assert (route.SCOPE_REASON_MAX, route.SCR_REASON_MAX, route.WAIVER_REASON_MAX,
            route.COMPENSATE_REASON_MAX) == (200, 500, 500, 500)
    assert route.TEMPLATE_VAR_PATTERN == "[A-Za-z0-9_-]"
    assert set(route.PLACEMENT_TARGETS) == {"autoclaude", "agentconsole", "sdd", "monorepo"}
    assert route.SCOPE_REASON_MAX != route.SCR_REASON_MAX, "兩個獨立常數，互不借用"


# ══ AT-961-2-2：消毒鏈 ══════════════════════════════════════════════════════════════════════════
def test_AT_961_2_2_deny_chars_traversal_and_bad_refs_are_422_with_zero_side_effects(
        renv: rgs.RouteEnv) -> None:
    rid = rgs.seed_gate0(renv)
    before = world(renv)
    bad_names = [f"a{c}b" for c in sorted(BASE_DENY_CHARS)] + ["a..b", "a/b", "a\\b"]
    for name in bad_names:
        resp = rgs.preview(renv, rid, rgs.body_b(renv, project_name=name))
        assert (resp.status_code, resp.json()["reason"]) == (422, "sanitization_failed"), name
    refs = ["a..b", "a@{b", "a.lock", "a~b", "a^b", "a:b", "a?b", "a*b", "a[b", "a\\b"]
    for ref in refs:
        resp = rgs.preview(renv, rid, rgs.body_a(renv, branch_name=f"feature/{ref}"))
        assert resp.status_code == 422, ref
        rule_set = {v["rule"] for v in resp.json()["violations"]}
        assert "git_ref" in rule_set and resp.json()["reason"] == "sanitization_failed", ref
    resp = rgs.preview(renv, rid, rgs.body_a(renv, target_path="/etc"))
    assert resp.status_code == 422 and resp.json()["violations"][0]["rule"] == "retired_field"
    assert world(renv) == before


def test_AT_961_2_2_a_worktree_root_outside_the_allowed_roots_is_a_missing_item(
        renv: rgs.RouteEnv, tmp_path: Path, make_env: Any) -> None:
    rid = rgs.seed_gate0(renv)
    live = renv.env.live
    outside = tmp_path / "outside-root"
    outside.mkdir()
    live.app.state.settings = replace(renv.env.settings, research_worktree_root=outside)
    live.app.state.research.cfg = live.app.state.settings
    resp = rgs.preview(renv, rid, rgs.body_a(renv))
    assert resp.status_code == 422 and resp.json()["reason"] == "route_unsupported_in_deployment"
    assert [m["item"] for m in resp.json()["details"]["missing"]] == ["worktree_root"]


def test_AT_961_2_2_a_symlinked_root_that_resolves_outside_is_refused(
        renv: rgs.RouteEnv, tmp_path: Path) -> None:
    rid = rgs.seed_gate0(renv)
    target = tmp_path / "elsewhere"
    target.mkdir()
    link = tmp_path / "wt" / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("TOOL-ABSENCE: symlink")
    live = renv.env.live
    live.app.state.settings = replace(renv.env.settings, research_worktree_root=link)
    live.app.state.research.cfg = live.app.state.settings
    resp = rgs.preview(renv, rid, rgs.body_a(renv))
    assert resp.status_code == 422
    assert [m["item"] for m in resp.json()["details"]["missing"]] == ["worktree_root"]


# ══ AT-961-2-3：落點目標 ════════════════════════════════════════════════════════════════════════
def test_AT_961_2_3_placement_targets_default_override_and_check_constraint(
        renv: rgs.RouteEnv) -> None:
    rid = rgs.seed_gate0(renv)
    body = {k: v for k, v in rgs.body_a(renv).items() if k not in ("target_module", "approver")}
    default = rgs.preview(renv, rid, body)
    assert default.status_code == 200, default.text
    targets = default.json()["targets"]
    assert [t["module"] for t in targets] == ["autoclaude", "agentconsole", "sdd", "monorepo"]
    assert all(t["rule_source"] for t in targets)
    assert [t["module"] for t in targets if t["default"]] == ["agentconsole"]
    assert default.json()["execution_path"].endswith(str(Path("AgentConsole")))
    assert default.json()["overridden_default"] is False
    over = rgs.preview(renv, rid, {**body, "target_module": "autoclaude"})
    assert over.status_code == 200 and over.json()["overridden_default"] is True
    for bad in ("other", "free text", ""):
        resp = rgs.preview(renv, rid, {**body, "target_module": bad})
        assert resp.status_code == 422, bad
        assert resp.json()["violations"][0]["rule"] == "unknown_target_module"
    check = renv.rdb.one("SELECT string_agg(pg_get_constraintdef(oid), ' ') FROM pg_constraint "
                         "WHERE conrelid = 'console.research_route_decisions'::regclass "
                         "AND pg_get_constraintdef(oid) LIKE '%autoclaude%'")
    assert check is not None and check[0]
    assert all(module in check[0] for module in route.PLACEMENT_TARGETS), check[0]
    paths = set(renv.env.live.app.openapi()["paths"])
    assert not [p for p in paths if "placement" in p.lower() or "target" in p.lower()]


def test_AT_961_2_3_an_override_is_recorded_in_the_route_decision(renv: rgs.RouteEnv) -> None:
    rid = rgs.seed_gate0(renv)
    resp = rgs.confirm(renv, rid, rgs.body_a(renv, target_module="autoclaude"))
    assert resp.status_code == 200, resp.text
    ws = Path(renv.env.db.get_project(rid)["workspace_path"])
    text = (ws / "02_governance" / "route_decision.json").read_text(encoding="utf-8")
    assert '"overridden_default": true' in text and '"target_module": "autoclaude"' in text


# ══ AT-961-2-4：scope 差異 ══════════════════════════════════════════════════════════════════════
def test_AT_961_2_4_a_different_scope_needs_a_reason_and_the_prd_stays_frozen(
        renv: rgs.RouteEnv) -> None:
    same = rgs.seed_gate0(renv, "alpha", target_scope="AISDLC_MODULE")
    other = rgs.seed_gate0(renv, "beta", target_scope="STANDALONE_PROJECT")
    prd = Path(renv.env.db.get_project(same)["workspace_path"]) / "01_specs" / "PRD-v1.0.0.md"
    frozen = prd.read_bytes()
    ok = rgs.preview(renv, same, rgs.body_a(renv))
    assert ok.status_code == 200 and ok.json()["scope_differs"] is False
    for reason, status in ((None, 422), ("", 422), ("   ", 422), ("x", 200), ("x" * 200, 200),
                           ("x" * 201, 422)):
        body = rgs.body_b(renv) if reason is None else rgs.body_b(
            renv, scope_differs_reason=reason)
        resp = rgs.preview(renv, same, body)
        assert resp.status_code == status, (reason, resp.text)
    shown = rgs.preview(renv, same, rgs.body_b(renv, scope_differs_reason="需要獨立專案"))
    assert shown.json()["scope_differs"] is True
    assert (shown.json()["prd_target_scope"], shown.json()["route_track"]) == (
        "AISDLC_MODULE", "B")
    assert rgs.preview(renv, other, rgs.body_a(renv, scope_differs_reason="併入模組")
                       ).status_code == 200
    confirmed = rgs.confirm(renv, same, rgs.body_b(renv, scope_differs_reason="需要獨立專案"))
    assert confirmed.status_code == 200, confirmed.text
    stored = renv.rdb.one("SELECT scope_differs_reason FROM console.research_route_decisions "
                          "WHERE research_id = %s", same)
    assert stored is not None and stored[0] == "需要獨立專案"
    assert prd.read_bytes() == frozen


# ══ AT-961-2-5：範本登記制 ══════════════════════════════════════════════════════════════════════
def test_AT_961_2_5_the_template_list_comes_from_the_directory(
        renv: rgs.RouteEnv, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rid = rgs.seed_gate0(renv)
    caps = renv.env.get("/research/capabilities").json()
    assert caps["scaffold_templates"] == ["python-fastapi"]
    for bad in ("node", "java", "../python-fastapi", "PYTHON-FASTAPI"):
        resp = rgs.preview(renv, rid, rgs.body_b(renv, stack_template=bad))
        assert resp.status_code == 422, bad
        assert "unknown_template" in {v["rule"] for v in resp.json()["violations"]}
    tree = tmp_path / "tpl"
    for name in ("python-fastapi", "node", "Bad Name"):
        (tree / name).mkdir(parents=True)
        (tree / name / "f.txt.tmpl").write_text("x\n", encoding="utf-8")
    (tree / "empty").mkdir()
    monkeypatch.setattr(research_settings, "TEMPLATES_DIR", tree)
    assert renv.env.get("/research/capabilities").json()["scaffold_templates"] == [
        "node", "python-fastapi"]
    assert not list((APP_DIR / "research" / "scaffold_templates").rglob("*.py"))


# ══ AT-961-2-6：Public 確認 ═════════════════════════════════════════════════════════════════════
def test_AT_961_2_6_public_needs_the_exact_repo_name(renv: rgs.RouteEnv,
                                                     fake_gh: rgs.FakeGh) -> None:
    rid = rgs.seed_gate0(renv)
    before = world(renv)
    assert rgs.preview(renv, rid, rgs.body_b(renv)).json()["warnings"] == []
    for confirm_name in (None, "other", "Demo-App", "demo-app "):
        body = rgs.body_b(renv, visibility="PUBLIC")
        if confirm_name is not None:
            body["confirm_repo_name"] = confirm_name
        resp = rgs.preview(renv, rid, body)
        assert (resp.status_code, resp.json()["reason"]) == (422, "public_confirmation_required")
    ok = rgs.preview(renv, rid, rgs.body_b(renv, visibility="PUBLIC",
                                           confirm_repo_name="demo-app"))
    assert ok.status_code == 200
    assert [w["code"] for w in ok.json()["warnings"]] == ["public_repo_warning"]
    assert "PRD 與證據矩陣將公開" in ok.json()["warnings"][0]["message"]
    on_a = rgs.preview(renv, rid, rgs.body_a(renv, visibility="PUBLIC"))
    assert on_a.status_code == 422
    assert "public_requires_track_b" in {v["rule"] for v in on_a.json()["violations"]}
    assert world(renv) == before and fake_gh.calls() == []


# ══ AT-961-2-7：Gate 0 前置 ═════════════════════════════════════════════════════════════════════
def test_AT_961_2_7_only_a_gate0_project_can_be_routed(renv: rgs.RouteEnv) -> None:
    pending = rgs.seed_gate0(renv, "pending", approve=False)
    body_e = rt.project_body("escal")
    assert renv.env.post("/research/projects", body_e).status_code == 201
    escalated = str(body_e["research_id"])
    rt.to_escalation(renv.env, escalated)
    ready = rgs.seed_gate0(renv, "ready")
    for path in ("route-preview", "route"):
        body = {**rgs.body_a(renv), "console_project_id": renv.console_project("c")}
        resp = renv.env.post(f"/research/projects/{pending}:{path}", body)
        assert (resp.status_code, resp.json()["reason"]) == (409, "fsm_state_conflict"), path
        assert resp.json()["details"]["expected_state"] == "SPEC_FROZEN"
        assert resp.json()["details"]["current_state"] == "HUMAN_PENDING"
        stuck = renv.env.post(f"/research/projects/{escalated}:{path}", body)
        assert (stuck.status_code, stuck.json()["reason"]) == (409, "escalated"), path
    assert renv.rdb.count("research_route_decisions") == 0
    before = world(renv)
    assert rgs.preview(renv, ready, rgs.body_a(renv)).status_code == 200
    assert world(renv) == before
    assert rgs.confirm(renv, ready, rgs.body_a(renv)).status_code == 200
    again = rgs.preview(renv, ready, rgs.body_a(renv))
    assert (again.status_code, again.json()["reason"]) == (409, "route_conflict")


# ══ AT-961-3-1／3-2：動作清單 ═══════════════════════════════════════════════════════════════════
def test_AT_961_3_1_track_a_actions_have_the_fixed_order_and_shape(
        renv: rgs.RouteEnv, fake_gh: rgs.FakeGh) -> None:
    rid = rgs.seed_gate0(renv)
    resp = rgs.preview(renv, rid, rgs.body_a(renv))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert [a["step"] for a in body["actions"]] == [
        "VALIDATE_TARGET", "GIT_SWITCH", "PUBLISH_DOCS", "REGISTER_STUB", "GIT_COMMIT",
        "IMPL_KEY_INIT", "BASELINE_ADOPT"]
    assert all(set(a) == {"seq", "action", "step", "target", "touches_external", "detail"}
               for a in body["actions"])
    assert [a["seq"] for a in body["actions"]] == list(range(1, 8))
    assert not any(a["touches_external"] for a in body["actions"])
    switch = body["actions"][1]
    assert switch["action"] == "worktree_add" and "feature/issue-" in switch["target"]
    assert "main" in switch["target"] and str(renv.worktrees) in switch["target"]
    assert {"version_no", "semver", "sha256", "target_scope", "scope_differs"} <= set(body["prd"])
    assert body["impl_fsm_project"] == "agentconsole-demo"
    assert body["impl_state_dir"].endswith(str(Path("build/reports/fsm")))
    assert body["execution_path"].startswith(str(renv.worktrees))
    assert fake_gh.calls() == []


def test_AT_961_3_2_track_b_actions_and_the_external_flag(renv: rgs.RouteEnv,
                                                           fake_gh: rgs.FakeGh) -> None:
    rid = rgs.seed_gate0(renv)
    local = rgs.preview(renv, rid, rgs.body_b(renv))
    assert [a["step"] for a in local.json()["actions"]] == [
        "VALIDATE_TARGET", "SCAFFOLD_FILES", "COPY_WORKSPACE", "GIT_INIT", "GIT_COMMIT",
        "IMPL_KEY_INIT", "BASELINE_ADOPT"]
    assert not any(a["touches_external"] for a in local.json()["actions"])
    remote = rgs.preview(renv, rid, rgs.body_b(renv, create_github=True, repo_name="demo-app"))
    steps = [a["step"] for a in remote.json()["actions"]]
    assert steps == ["VALIDATE_TARGET", "SCAFFOLD_FILES", "COPY_WORKSPACE", "GIT_INIT",
                     "GIT_COMMIT", "GH_REPO_CREATE", "IMPL_KEY_INIT", "BASELINE_ADOPT"]
    create = remote.json()["actions"][5]
    assert create["touches_external"] is True and create["target"] == "octocat/demo-app"
    assert [a["step"] for a in remote.json()["actions"] if a["touches_external"]] == [
        "GH_REPO_CREATE"]
    body = local.json()
    assert body["execution_path"] == str(renv.scaffold / "demo-app")
    assert body["expected_tracked_files"] == sorted(body["expected_tracked_files"])
    assert not [f for f in body["expected_tracked_files"] if "/raw/" in f or f == ".env"]
    assert ".env.example" in body["expected_tracked_files"]
    assert local.json()["actions"][2]["target"].endswith("my-project/demo")


# ══ AT-961-3-3／3-4：零副作用 ═══════════════════════════════════════════════════════════════════
def test_AT_961_3_3_a_track_a_preview_changes_nothing(renv: rgs.RouteEnv,
                                                      calls: list[gitops.CallRecord]) -> None:
    rid = rgs.seed_gate0(renv)
    (renv.repo / "dirty.txt").write_text("u\n", encoding="utf-8")
    (renv.repo / "AgentConsole" / "README.md").write_text("m\n", encoding="utf-8")
    index_before = (renv.repo / ".git" / "index").read_bytes()
    before = world(renv)
    stamps = {p: p.stat().st_mtime_ns for p in (renv.repo / "dirty.txt",
                                                renv.repo / "AgentConsole" / "README.md")}
    calls.clear()
    for body in (rgs.body_a(renv), rgs.body_a(renv), rgs.body_a(renv, branch_name="Bad")):
        rgs.preview(renv, rid, body)
    assert world(renv) == before
    assert (renv.repo / ".git" / "index").read_bytes() == index_before
    assert {p: p.stat().st_mtime_ns for p in stamps} == stamps
    verbs = {c.argv[1] for c in calls if c.argv[0] == "git"}
    assert verbs <= {"branch", "rev-parse", "worktree", "status", "diff", "ls-files"}
    assert all(c.readonly for c in calls if c.argv[0] == "git")


def test_AT_961_3_4_a_track_b_preview_creates_nothing_and_gh_only_probes(
        renv: rgs.RouteEnv, fake_gh: rgs.FakeGh) -> None:
    rid = rgs.seed_gate0(renv)
    ws = Path(renv.env.db.get_project(rid)["workspace_path"])
    ws_before = rgs.tree_hash(ws)
    before = world(renv)
    for _ in range(2):
        resp = rgs.preview(renv, rid, rgs.body_b(renv, create_github=True))
        assert resp.status_code == 200, resp.text
    assert world(renv) == before and rgs.tree_hash(ws) == ws_before
    assert not list(renv.scaffold.iterdir())
    assert {tuple(c["argv"]) for c in fake_gh.calls()} == {("auth", "status")}
    assert not [c for c in fake_gh.calls() if c["has_gh_token"]]
    fake_gh.clear()
    assert rgs.preview(renv, rid, rgs.body_b(renv)).status_code == 200
    assert fake_gh.calls() == []


# ══ AT-961-3-5：部署不支援 ═══════════════════════════════════════════════════════════════════════
def test_AT_961_3_5_missing_items_are_listed_alphabetically_and_nothing_succeeds_silently(
        renv: rgs.RouteEnv, fake_gh: rgs.FakeGh, monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path) -> None:
    rid = rgs.seed_gate0(renv)
    live, base = renv.env.live, renv.env.settings

    def deploy(**fields: Any) -> None:
        live.app.state.settings = replace(base, **fields)
        live.app.state.research.cfg = live.app.state.settings

    def items(body: dict[str, Any]) -> list[str]:
        resp = rgs.preview(renv, rid, body)
        assert resp.status_code == 422, resp.text
        assert resp.json()["reason"] == "route_unsupported_in_deployment"
        return [m["item"] for m in resp.json()["details"]["missing"]]

    before = world(renv)
    deploy(research_repo_root=tmp_path / "no-such-repo")
    assert items(rgs.body_a(renv)) == ["repo_writable"]
    assert rgs.preview(renv, rid, rgs.body_b(renv)).status_code == 200
    deploy(research_scaffold_root=None)
    assert items(rgs.body_b(renv)) == ["scaffold_root"]
    assert rgs.preview(renv, rid, rgs.body_a(renv)).status_code == 200
    deploy(research_scaffold_root=None, research_repo_root=tmp_path / "no-such-repo")
    assert items(rgs.body_b(renv, create_github=True)) == ["scaffold_root"]
    assert items(rgs.body_a(renv)) == ["repo_writable"]
    deploy()
    fake_gh.mode("unauth")
    assert items(rgs.body_b(renv, create_github=True)) == ["gh_auth"]
    assert rgs.preview(renv, rid, rgs.body_b(renv)).status_code == 200
    fake_gh.mode("ok")
    rgs.hide_gh(monkeypatch)
    assert items(rgs.body_b(renv, create_github=True)) == ["gh"]
    assert rgs.preview(renv, rid, rgs.body_b(renv)).status_code == 200, "不建遠端時不要求 gh"
    assert world(renv) == before


# ══ AT-961-3-6／3-7 ═════════════════════════════════════════════════════════════════════════════
def test_AT_961_3_6_a_non_empty_target_is_422_and_an_empty_one_is_fine(
        renv: rgs.RouteEnv) -> None:
    rid = rgs.seed_gate0(renv)
    assert rgs.preview(renv, rid, rgs.body_b(renv)).status_code == 200
    (renv.scaffold / "demo-app").mkdir()
    assert rgs.preview(renv, rid, rgs.body_b(renv)).status_code == 200
    held = renv.scaffold / "demo-app" / "keep.txt"
    held.write_text("mine\n", encoding="utf-8")
    stamp = held.stat().st_mtime_ns
    for call in (lambda: rgs.preview(renv, rid, rgs.body_b(renv)),
                 lambda: rgs.confirm(renv, rid, rgs.body_b(renv))):
        resp = call()
        assert (resp.status_code, resp.json()["reason"]) == (422, "target_not_empty")
        assert resp.json()["details"]["path"] == "demo-app"
        assert str(renv.scaffold) not in resp.text, "不洩絕對路徑"
    assert held.read_text(encoding="utf-8") == "mine\n" and held.stat().st_mtime_ns == stamp
    assert [p.name for p in (renv.scaffold / "demo-app").iterdir()] == ["keep.txt"]
    assert renv.rdb.count("research_route_decisions") == 0


def test_AT_961_3_7_an_existing_branch_is_409_in_the_preview(renv: rgs.RouteEnv) -> None:
    rid = rgs.seed_gate0(renv)
    number = str(renv.env.db.get_project(rid)["rp_no"]).removeprefix("RP-")
    rgs.git(renv.repo, "branch", f"feature/issue-{number}")
    before = rgs.snapshot(renv.repo)
    resp = rgs.preview(renv, rid, rgs.body_a(renv))
    assert (resp.status_code, resp.json()["reason"]) == (409, "branch_exists")
    assert resp.json()["details"]["branch"] == f"feature/issue-{number}"
    assert rgs.snapshot(renv.repo) == before
    assert rgs.preview(renv, rid, rgs.body_a(renv, branch_name="feature/other-1")
                       ).status_code == 200


# ══ AT-961-3-E-1：預演與執行共用同一份計畫 ═══════════════════════════════════════════════════════
def calls_named(path: Path, name: str) -> int:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return sum(1 for n in ast.walk(tree) if isinstance(n, ast.Call) and (
        (isinstance(n.func, ast.Attribute) and n.func.attr == name)
        or (isinstance(n.func, ast.Name) and n.func.id == name)))


def test_AT_961_3_E_1_preview_and_execution_share_one_plan_and_one_validator() -> None:
    assert calls_named(APP_DIR / "research" / "route.py", "validate_request") == 1
    assert calls_named(APP_DIR / "routers" / "research_route.py", "validate_request") == 0
    assert calls_named(APP_DIR / "routers" / "research_route.py", "build_plan") == 1
    assert calls_named(APP_DIR / "research" / "route.py", "build_plan") >= 2


def test_AT_961_3_E_1_the_executed_steps_equal_the_previewed_steps(
        renv: rgs.RouteEnv, fake_gh: rgs.FakeGh) -> None:
    for slug, body in (("alpha", rgs.body_a(renv)),
                       ("beta", rgs.body_b(renv, create_github=True))):
        rid = rgs.seed_gate0(renv, slug)
        planned = [a["step"] for a in rgs.preview(renv, rid, body).json()["actions"]]
        extra = {"github_token": rgs.FAKE_TOKEN} if body["track"] == "B" else {}
        resp = rgs.confirm(renv, rid, body, **extra)
        assert resp.status_code == 200, resp.text
        assert [s["step"] for s in resp.json()["steps"]] == planned, slug
