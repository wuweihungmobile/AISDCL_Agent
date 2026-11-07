"""軌道 A：獨立 worktree、發佈、落點 stub、主工作樹零擾動（TCS AT-961-5-*；PKG-BR-D1）。

真 git 只在 `tmp_path` 下的拋棄式迷你 monorepo（見 `tests/research_git_support.py`）；FSM 用真
SDD 樹（缺 `SDD_ROOT`＝`TOOL-ABSENCE` skip）；資料庫是拋棄式庫。內環鍵建檔需要 B1 補丁
（交卷「需主控處理」）。
"""
from __future__ import annotations

import ast
import hashlib
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from app import fsutil
from app.research import gitops, route
from app.research.orchestrator import BASELINE_REL
from tests import research_git_support as rgs
from tests import test_research_router as rt

make_env = rt.make_env
route_db, real_tree, renv, fake_gh = rgs.route_db, rgs.real_tree, rgs.renv, rgs.fake_gh
APP_DIR = Path(route.__file__).resolve().parents[1]


@pytest.fixture
def calls() -> Iterator[list[gitops.CallRecord]]:
    log: list[gitops.CallRecord] = []
    gitops.OBSERVERS.append(log.append)
    try:
        yield log
    finally:
        gitops.OBSERVERS.remove(log.append)


def rp_number(renv: rgs.RouteEnv, rid: str) -> str:
    return str(renv.env.db.get_project(rid)["rp_no"]).removeprefix("RP-")


def route_row(renv: rgs.RouteEnv, rid: str) -> dict[str, Any]:
    rows = renv.rdb.q("SELECT id, status, failure_step, console_project_id, impl_fsm_project, "
                      "impl_state_dir, published_docs, git_branch, base_ref FROM "
                      "console.research_route_decisions WHERE research_id = %s", rid)
    assert len(rows) == 1, rows
    keys = ("id", "status", "failure_step", "console_project_id", "impl_fsm_project",
            "impl_state_dir", "published_docs", "git_branch", "base_ref")
    return dict(zip(keys, rows[0], strict=True))


def dirty_main_tree(repo: Path) -> None:
    """三種髒狀態：已暫存的新增、未暫存的修改、已暫存的刪除（另有一個未追蹤檔）。"""
    (repo / "staged_new.txt").write_text("staged\n", encoding="utf-8", newline="\n")
    rgs.git(repo, "add", "staged_new.txt")
    (repo / "AgentConsole" / "README.md").write_text("modified\n", encoding="utf-8", newline="\n")
    rgs.git(repo, "rm", "-q", "tools/keep.txt")
    (repo / "untracked.txt").write_text("u\n", encoding="utf-8", newline="\n")


def file_state(repo: Path) -> dict[str, tuple[bytes, int]]:
    return {p.relative_to(repo).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in sorted(repo.rglob("*")) if p.is_file() and ".git" not in p.parts}


# ── AT-961-5-1 ─────────────────────────────────────────────────────────────────────────────
def test_AT_961_5_1_a_feature_branch_in_its_own_worktree_leaves_the_main_tree_untouched(
        renv: rgs.RouteEnv, calls: list[gitops.CallRecord]) -> None:
    rid = rgs.seed_gate0(renv)
    dirty_main_tree(renv.repo)
    before, files = rgs.snapshot(renv.repo), file_state(renv.repo)
    resp = rgs.confirm(renv, rid, rgs.body_a(renv))
    assert resp.status_code == 200, resp.text
    branch = f"feature/issue-{rp_number(renv, rid)}"
    after = rgs.snapshot(renv.repo)
    listed = after["worktrees"].count("worktree ") - before["worktrees"].count("worktree ")
    assert listed == 1, "多恰一個 worktree"
    assert after["head"] == before["head"] and after["status"] == before["status"]
    assert after["index"] == before["index"] and after["current"] == before["current"]
    assert file_state(renv.repo) == files, "未提交修改、已暫存修改與未追蹤檔的位元組與 mtime 不變"
    assert branch in after["branches"]
    wt = next(p for p in renv.worktrees.iterdir())
    assert rgs.git(wt, "rev-parse", "HEAD~1").strip() == before["head"] or (
        rgs.git(wt, "rev-parse", "HEAD").strip() != before["head"])
    adds = [c for c in calls if "worktree" in c.argv and "add" in c.argv]
    assert len(adds) == 1
    assert adds[0].argv[:5] == ("git", "-c", "core.longpaths=true", "worktree", "add")
    assert adds[0].argv[5] == "-b" and adds[0].argv[6] == branch and adds[0].argv[-1] == "main"
    for banned in ("checkout", "switch", "stash"):
        assert not [c for c in calls if banned in c.argv], banned


def test_AT_961_5_1_a_custom_base_ref_is_the_worktree_base(renv: rgs.RouteEnv) -> None:
    rid = rgs.seed_gate0(renv)
    rgs.git(renv.repo, "branch", "release-x")
    resp = rgs.confirm(renv, rid, rgs.body_a(renv, base_ref="release-x"))
    assert resp.status_code == 200, resp.text
    assert route_row(renv, rid)["base_ref"] == "release-x"


# ── AT-961-5-2 ─────────────────────────────────────────────────────────────────────────────
def test_AT_961_5_2_existing_branch_409_and_a_missing_base_ref_fails_at_git_switch(
        renv: rgs.RouteEnv) -> None:
    rid_a = rgs.seed_gate0(renv, "alpha")
    branch = f"feature/issue-{rp_number(renv, rid_a)}"
    rgs.git(renv.repo, "branch", branch)
    before = rgs.snapshot(renv.repo)
    resp = rgs.confirm(renv, rid_a, rgs.body_a(renv))
    assert (resp.status_code, resp.json()["reason"]) == (409, "branch_exists")
    assert resp.json()["details"]["branch"] == branch
    assert renv.rdb.count("research_route_decisions") == 0 and not list(renv.worktrees.glob("*"))
    assert rgs.snapshot(renv.repo) == before
    rid_b = rgs.seed_gate0(renv, "beta")
    body = rgs.body_a(renv, base_ref="no-such-ref")
    failed = rgs.confirm(renv, rid_b, body)
    assert (failed.status_code, failed.json()["reason"]) == (502, "route_step_failed")
    assert failed.json()["details"]["failure_step"] == "GIT_SWITCH"
    row = route_row(renv, rid_b)
    assert row["status"] == "FAILED" and row["failure_step"] == "GIT_SWITCH"
    steps = {s[0]: s[1] for s in renv.rdb.q(
        "SELECT step, status FROM console.research_route_steps WHERE route_id = %s", row["id"])}
    assert steps == {"VALIDATE_TARGET": "OK", "GIT_SWITCH": "FAILED"}
    assert not (renv.worktrees.exists() and list(renv.worktrees.rglob("*_PRD.md")))
    rgs.git(renv.repo, "branch", "no-such-ref")                         # 排除故障
    retried = rgs.confirm(renv, rid_b, body, retry=True, console_project_id=str(
        renv.rdb.one("SELECT console_project_id FROM console.research_route_decisions "
                     "WHERE id = %s", row["id"])[0]))
    assert retried.status_code == 200, retried.text
    assert route_row(renv, rid_b)["status"] == "SUCCEEDED"


# ── AT-961-5-3 ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("slug", ["demo-1", "x2-y3"])
def test_AT_961_5_3_the_prd_is_published_byte_identical_with_a_traditional_chinese_commit(
        renv: rgs.RouteEnv, slug: str) -> None:
    rid = rgs.seed_gate0(renv, slug)
    resp = rgs.confirm(renv, rid, rgs.body_a(renv))
    assert resp.status_code == 200, resp.text
    ws = Path(renv.env.db.get_project(rid)["workspace_path"])
    wt = next(renv.worktrees.iterdir())
    published = wt / "AgentConsole" / "docs" / "01_requirements" / f"{slug}_PRD.md"
    assert published.read_bytes() == (ws / BASELINE_REL).read_bytes()
    sha = hashlib.sha256(published.read_bytes()).hexdigest()
    frozen = {k: v.removeprefix("sha256:") for k, v in renv.env.db.gate0_digests(rid).items()}
    assert frozen[BASELINE_REL] == sha
    docs = route_row(renv, rid)["published_docs"]
    assert docs[f"docs/01_requirements/{slug}_PRD.md"] == sha
    message = rgs.git(wt, "log", "-1", "--format=%s%n%an%n%ae%n%cn")
    subject, author, email, committer = message.splitlines()
    assert "發佈" in subject and f"RP-{rp_number(renv, rid)}" in subject and sha[:12] in subject
    assert (author, committer) == gitops.DEFAULT_IDENTITY[:1] * 2
    assert email == gitops.DEFAULT_IDENTITY[1]
    assert len(rgs.git(wt, "log", "--oneline", "main..HEAD").strip().splitlines()) == 1


def test_AT_961_5_3_a_prd_that_no_longer_matches_the_frozen_digest_is_not_published(
        renv: rgs.RouteEnv) -> None:
    rid = rgs.seed_gate0(renv)
    ws = Path(renv.env.db.get_project(rid)["workspace_path"])
    with (ws / BASELINE_REL).open("a", encoding="utf-8", newline="\n") as fh:
        fh.write("\n偷改的一行\n")
    resp = rgs.confirm(renv, rid, rgs.body_a(renv))
    assert (resp.status_code, resp.json()["details"]["failure_step"]) == (502, "PUBLISH_DOCS")
    assert resp.json()["details"]["reason"] == "prd_digest_mismatch"
    wt = next(renv.worktrees.iterdir())
    assert not list(wt.rglob("*_PRD.md"))
    assert rgs.git(wt, "log", "--oneline", "main..HEAD").strip() == "", "不 commit"


# ── AT-961-5-4 ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("module", ["autoclaude", "agentconsole", "sdd", "monorepo"])
def test_AT_961_5_4_the_branch_changes_only_the_prd_and_the_placement_stub(
        renv: rgs.RouteEnv, module: str) -> None:
    rid = rgs.seed_gate0(renv, "demo")
    resp = rgs.confirm(renv, rid, rgs.body_a(renv, target_module=module))
    assert resp.status_code == 200, resp.text
    branch = route_row(renv, rid)["git_branch"]
    names = set(rgs.git(renv.repo, "diff", "--name-only", f"main..{branch}").split())
    sub = {"autoclaude": "AutoClaude/", "agentconsole": "AgentConsole/",
           "sdd": "AISDLC_SDD/AISDLC_SDD_v9.99/", "monorepo": ""}[module]
    expected = {f"{sub}docs/01_requirements/demo_PRD.md",
                f"{sub}docs/02_architecture/Module_Placement_Stub_demo.md"}
    assert names == expected, names
    forbidden = ("CLAUDE.md", ".claude/", "tools/",
                 "docs/02_architecture/Root_Layout_and_Module_Placement.md")
    assert not [n for n in names for bad in forbidden if n == bad or n.startswith(bad)]
    wt = next(renv.worktrees.iterdir())
    stub = (wt / sub.rstrip("/") / "docs" / "02_architecture" / "Module_Placement_Stub_demo.md"
            ).read_text(encoding="utf-8")
    for needle in (rid, hashlib.sha256((wt / sub.rstrip("/") / "docs" / "01_requirements"
                                         / "demo_PRD.md").read_bytes()).hexdigest(), module,
                   "請依 Root_Layout §2、§3 手動登記", "由 ResearchToPRD 產生，非落點 SSOT"):
        assert needle in stub, needle


# ── AT-961-5-5 ─────────────────────────────────────────────────────────────────────────────
def test_AT_961_5_5_the_console_project_binding_is_written_in_one_transaction(
        renv: rgs.RouteEnv) -> None:
    rid = rgs.seed_gate0(renv)
    missing = renv.env.post(f"/research/projects/{rid}:route", rgs.body_a(renv))
    assert (missing.status_code, missing.json()["reason"]) == (422, "invalid_request")
    assert any(v["field"] == "console_project_id" for v in missing.json()["violations"])
    ghost = renv.env.post(f"/research/projects/{rid}:route", {
        **rgs.body_a(renv), "console_project_id": str(uuid.uuid4())})
    assert ghost.status_code == 422 and ghost.json()["reason"] == "invalid_request", ghost.text
    assert renv.rdb.count("research_route_decisions") == 0
    project = renv.console_project("bound")
    resp = renv.env.post(f"/research/projects/{rid}:route", {
        **rgs.body_a(renv), "console_project_id": project})
    assert resp.status_code == 200, resp.text
    row = route_row(renv, rid)
    assert str(row["console_project_id"]) == project
    assert row["impl_fsm_project"] == "agentconsole-demo"
    bound = renv.rdb.one("SELECT console_project_id FROM console.research_projects WHERE id = %s",
                         rid)
    assert bound is not None and str(bound[0]) == project
    events = [e[1] for e in renv.rdb.events(rid)]
    assert events.count("research.step") >= 2 and "research.route" in events


# ── AT-961-5-6 ─────────────────────────────────────────────────────────────────────────────
def test_AT_961_5_6_two_routes_with_a_very_dirty_main_tree_leave_it_alone(
        renv: rgs.RouteEnv) -> None:
    first, second = rgs.seed_gate0(renv, "alpha"), rgs.seed_gate0(renv, "beta")
    dirty_main_tree(renv.repo)
    before, files = rgs.snapshot(renv.repo), file_state(renv.repo)
    assert rgs.confirm(renv, first, rgs.body_a(renv), n=1).status_code == 200
    assert rgs.confirm(renv, second, rgs.body_a(renv), n=2).status_code == 200
    after = rgs.snapshot(renv.repo)
    assert after["status"] == before["status"] and after["stash"] == "" == before["stash"]
    assert (after["current"], after["head"], after["index"]) == (
        before["current"], before["head"], before["index"])
    assert file_state(renv.repo) == files
    assert after["worktrees"].count("worktree ") - before["worktrees"].count("worktree ") == 2


# ── AT-961-5-E-1 ───────────────────────────────────────────────────────────────────────────
def test_AT_961_5_E_1_a_publish_failure_leaves_no_half_written_file(
        renv: rgs.RouteEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    rid = rgs.seed_gate0(renv)
    real = fsutil.write_text_atomic

    def flaky(path: Path, text: str) -> None:
        if path.name.endswith("_PRD.md"):
            raise OSError("injected write failure")
        real(path, text)

    monkeypatch.setattr(fsutil, "write_text_atomic", flaky)
    resp = rgs.confirm(renv, rid, rgs.body_a(renv))
    assert (resp.status_code, resp.json()["details"]["failure_step"]) == (502, "PUBLISH_DOCS")
    wt = next(renv.worktrees.iterdir())
    assert not list(wt.rglob("*_PRD.md")) and not list(wt.rglob("*.tmp"))
    assert route_row(renv, rid)["status"] == "FAILED"


def test_AT_961_5_E_1_no_new_directory_entry_primitives_in_the_p1_modules() -> None:
    """`os.replace` 與任何 `.rename(`／`.move(`（`str.replace` 不算）。"""
    for rel in ("research/route.py", "research/scaffold.py", "research/gitops.py",
                "research/adopt.py", "routers/research_route.py"):
        tree = ast.parse((APP_DIR / rel).read_text(encoding="utf-8"))
        hits = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute) and (
                    n.func.attr in {"rename", "move"}
                    or (n.func.attr == "replace" and isinstance(n.func.value, ast.Name)
                        and n.func.value.id == "os"))]
        assert hits == [], f"{rel} 行 {hits}：不得新增 os.replace／rename／move 站點"
