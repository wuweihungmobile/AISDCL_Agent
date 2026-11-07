"""整合 P1：拋棄式 clone、假 gh、拆解→TCS 草擬→SCR 的端到端串接（TCS AT-961-22-1～22-4、
22-E-1、22-E-2；PKG-INT-P1）。

hermetic：真 git 只在 `tmp_path` 下的拋棄式 clone／`git archive` 匯出倉；`gh` 一律假夾具；FSM 用真
SDD 樹（缺 `SDD_ROOT`＝`TOOL-ABSENCE` skip）、資料庫是拋棄式庫（缺 `BRIDGE_TEST_DSN`＝
`TOOL-ABSENCE` skip）；拆解引擎是 `FakeBrain` 夾具、claude 是 mock 劇本。證據（`show` 逐字、
git 量測）以 `print` 輸出，由 `-s` 執行時擷取；機密樣式字面一律執行期拼接。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from app import sdd_cli
from app.research import fsm_ops
from tests import research_git_support as rgs
from tests import test_research_router as rt
from tests.research_pg_support import REPO_ROOT, ThrowawayDb
from tests.test_decompose import FakeBrain, step
from tests.test_research_decompose import PRD, post_decompose, use_brain
from tests.test_research_scr import ADMIN, cursor, inner, inner_to, outer, post_scr
from tests.test_research_scr_fsm import TAIL, labels, outer_loop
from tests.test_research_tcs_draft import (
    OK_DRAFT,
    enable_claude,
    enable_freeze,
    freeze,
    published_tcs,
    set_script,
    start,
    trace,
)

make_env = rt.make_env
route_db, real_tree, fake_gh, renv = rgs.route_db, rgs.real_tree, rgs.fake_gh, rgs.renv


# ── 載具：拋棄式 clone（兩種來源）上的活 Bridge ─────────────────────────────────────────────
def real_repo_state() -> dict[str, str]:
    """真 repo 的唯讀摘要（HEAD、status、for-each-ref）；不比對 `.git` 位元組（多視窗並行會漂）。"""
    return {"head": rgs.git(REPO_ROOT, "rev-parse", "HEAD").strip(),
            "refs": rgs.git(REPO_ROOT, "for-each-ref", "--format=%(refname) %(objectname)"),
            "status": rgs.git(REPO_ROOT, "status", "--porcelain")}


def make_source(mode: str, dest: Path) -> Path:
    """`clone`＝git clone --no-hardlinks 真 repo；`archive`＝git archive HEAD 匯出再 git init。"""
    if mode == "clone":
        return rgs.clone_repo(REPO_ROOT, dest)
    dest.mkdir(parents=True)
    tar = dest.parent / f"{dest.name}.tar"
    rgs.git(REPO_ROOT, "archive", "--format=tar", "-o", str(tar), "HEAD")
    with tarfile.open(tar) as archive:           # Windows bsdtar 解不了非 ASCII 檔名，改用 tarfile
        archive.extractall(dest, filter="data")
    tar.unlink()
    rgs.git(dest, "init", "-b", "main")
    rgs.git(dest, "add", "-A")
    rgs.git(dest, "commit", "-q", "-m", "init from archive")
    return dest


def env_on(make: Callable[..., Any], rdb: ThrowawayDb, tmp: Path, tree: Path,
           repo: Path) -> rgs.RouteEnv:
    worktrees, scaffold = tmp / "wt", tmp / "scaffold"
    for d in (worktrees, scaffold):
        d.mkdir(exist_ok=True)
    roots = tuple(p.resolve() for p in (tmp / "workspace", tmp / "projects", repo, worktrees,
                                         scaffold))
    env = make(tree, rdb, research_repo_root=repo, research_worktree_root=worktrees,
               research_scaffold_root=scaffold, allowed_path_roots=roots)
    return rgs.RouteEnv(env=env, repo=repo, worktrees=worktrees, scaffold=scaffold, rdb=rdb,
                        tmp=tmp)


@pytest.fixture
def clone_env(make_env: Callable[..., Any], route_db: ThrowawayDb, tmp_path: Path,
              real_tree: Path, fake_gh: rgs.FakeGh) -> Any:
    repo = make_source("clone", tmp_path / "src-clone")
    built = env_on(make_env, route_db, tmp_path, real_tree, repo)
    try:
        yield built
    finally:
        rgs.cleanup_worktrees(repo)


def route_counts(renv: rgs.RouteEnv) -> dict[str, int]:
    return {t: renv.rdb.count(t) for t in (
        "research_route_decisions", "research_route_steps", "research_artifacts",
        "research_scr")}


def show_text(renv: rgs.RouteEnv, route: dict[str, Any]) -> str:
    return json.dumps(fsm_ops.show(inner(renv, route)), ensure_ascii=False, indent=2,
                      sort_keys=True)


# ── AT-961-22-1：軌道 A（拋棄式 clone）──────────────────────────────────────────────────────
def test_AT_961_22_1_track_a_on_a_disposable_clone_end_to_end(
        clone_env: rgs.RouteEnv, fake_gh: rgs.FakeGh) -> None:
    renv = clone_env
    real_before = real_repo_state()
    rid = rgs.seed_gate0(renv)
    body = rgs.body_a(renv)
    # 預演零副作用（出口 b）
    snap0, counts0 = rgs.snapshot(renv.repo), route_counts(renv)
    pre = rgs.preview(renv, rid, body)
    assert pre.status_code == 200, pre.text
    assert rgs.snapshot(renv.repo) == snap0 and route_counts(renv) == counts0
    assert not list(renv.worktrees.iterdir())
    # 確認（同步 200）：主工作樹零擾動（出口 c）
    ls_before = rgs.git(renv.repo, "ls-files", "-s")
    resp = rgs.confirm(renv, rid, body)
    assert resp.status_code == 200, resp.text
    snap1 = rgs.snapshot(renv.repo)
    assert snap1["head"] == snap0["head"] and snap1["status"] == snap0["status"]
    assert snap1["current"] == snap0["current"] and snap1["stash"] == snap0["stash"]
    assert rgs.git(renv.repo, "ls-files", "-s") == ls_before
    route = renv.env.db.active_route(rid)
    assert route is not None and route["status"] == "SUCCEEDED"
    branch = route["git_branch"]
    assert branch in snap1["branches"]
    changed = sorted(rgs.git(renv.repo, "diff", "--name-only", f"{route['base_ref']}..{branch}"
                             ).split())
    print("AT-961-22-1 diff --name-only", changed)
    assert changed and all(p.startswith("AgentConsole/") or "/docs/" in p or p.startswith(
        ("docs/", "AgentConsole/")) for p in changed), changed
    assert any(p.endswith("_PRD.md") for p in changed)
    assert route["impl_fsm_project"] and route["impl_state_dir"]
    text = show_text(renv, route)
    print("AT-961-22-1 inner show:\n" + text)
    shown = fsm_ops.show(inner(renv, route))
    assert fsm_ops.current_state(inner(renv, route)) == "SPEC_FROZEN"
    assert shown["frozen_stages"][-1]["stage"] == "Stage-1"
    def digests(view: dict[str, Any]) -> set[str]:
        return {v for s in view["frozen_stages"] for v in s["spec_doc_digests"].values()}

    inner_sha = digests(shown)
    outer_sha = digests(fsm_ops.show(outer(renv, rid)))
    print("AT-961-22-1 digests inner", inner_sha, "outer", outer_sha)
    assert inner_sha and inner_sha & outer_sha, "PRD 摘要等於外環 Gate 0 摘要"
    steps = renv.rdb.q("SELECT step, status FROM console.research_route_steps WHERE route_id = %s"
                       " ORDER BY step_no", route["id"])
    print("AT-961-22-1 route steps", steps)
    assert steps and all(s[1] == "OK" for s in steps)
    assert cursor(renv, rid)[:2] == ("build", "ROUTED")
    rec = renv.env.post(f"/research/projects/{rid}:reconcile", {})
    assert rec.status_code == 200 and rec.json()["consistent"] is True, rec.text
    assert fake_gh.calls() == [], "軌道 A 假 gh 呼叫 0 筆"
    assert real_repo_state() == real_before, "真 repo 唯讀"


# ── AT-961-22-2：軌道 B（scaffold 根＋假 gh）────────────────────────────────────────────────
def test_AT_961_22_2_track_b_scaffold_with_a_fake_gh_and_zero_token_leak(
        renv: rgs.RouteEnv, fake_gh: rgs.FakeGh) -> None:
    rid = rgs.seed_gate0(renv)
    ws = Path(renv.env.db.get_project(rid)["workspace_path"])
    (ws / "00_research" / "raw").mkdir(parents=True, exist_ok=True)
    (ws / "00_research" / "raw" / "page.html").write_text("raw\n", encoding="utf-8")
    (ws / "03_execution" / ".env").write_text("K=1\n", encoding="utf-8")
    body = rgs.body_b(renv, project_name="int-app", create_github=True, repo_name="int-app",
                      visibility="PRIVATE")
    pre = rgs.preview(renv, rid, body)
    assert pre.status_code == 200, pre.text
    expected = sorted(pre.json()["expected_tracked_files"])
    resp = rgs.confirm(renv, rid, body, github_token=rgs.FAKE_TOKEN)
    assert resp.status_code == 200, resp.text
    root = renv.scaffold / "int-app"
    tracked = sorted(rgs.git(root, "ls-files").split())
    assert tracked == expected
    assert not [t for t in tracked if "/raw/" in t or t.split("/")[-1] == ".env"]
    assert {".env.example", "docker-compose.yml", ".github/workflows/ci.yml"} <= set(tracked)
    assert len(rgs.git(root, "log", "--oneline").splitlines()) == 1
    assert list(root.glob("*/demo")) and ws.is_dir(), "原工作區原地保留"
    assert [c["argv"] for c in fake_gh.calls()][-1] == [
        "repo", "create", "octocat/int-app", "--private", "--source", ".", "--push"]
    assert [c["argv"] for c in fake_gh.calls()][0] == ["auth", "status"]
    route = renv.env.db.active_route(rid)
    assert route is not None
    print("AT-961-22-2 inner show:\n" + show_text(renv, route))
    assert fsm_ops.show(inner(renv, route))["frozen_stages"][-1]["stage"] == "Stage-1"
    rec = renv.env.post(f"/research/projects/{rid}:reconcile", {})
    assert rec.json()["consistent"] is True, rec.text
    # token 全面掃描（出口 f）
    cells = list(rgs.all_text_columns(renv.rdb))
    assert len(cells) > 100
    assert not [(t, c) for t, c, v in cells if v and rgs.contains_secret(str(v), rgs.FAKE_TOKEN)]
    roots = [renv.scaffold, Path(renv.env.settings.research_root),
             Path(renv.env.settings.engine_workspace)]
    assert not [h for r in roots for h in rgs.scan_files(r, rgs.FAKE_TOKEN)]
    assert not rgs.contains_secret(resp.text, rgs.FAKE_TOKEN)
    steps = renv.rdb.q("SELECT argv_redacted, stdout_tail, stderr_tail FROM "
                       "console.research_route_steps")
    assert steps and not [s for s in steps if any(rgs.contains_secret(c, rgs.FAKE_TOKEN)
                                                  for c in s)]


def test_AT_961_22_2_fail_create_keeps_local_steps_and_the_retry_redoes_only_the_remote_step(
        renv: rgs.RouteEnv, fake_gh: rgs.FakeGh) -> None:
    rid = rgs.seed_gate0(renv)
    body = rgs.body_b(renv, project_name="int-retry", create_github=True, repo_name="int-retry")
    project = renv.console_project("retry")
    fake_gh.mode("fail-create")
    failed = renv.env.post(f"/research/projects/{rid}:route", {
        **body, "console_project_id": project, "github_token": rgs.FAKE_TOKEN})
    assert failed.status_code == 502, failed.text
    assert not rgs.contains_secret(failed.text, rgs.FAKE_TOKEN)
    row = renv.rdb.one("SELECT status, failure_step, id::text FROM "
                       "console.research_route_decisions WHERE research_id = %s", rid)
    assert row is not None and row[:2] == ("FAILED", "GH_REPO_CREATE")
    done = dict(renv.rdb.q("SELECT step, status FROM console.research_route_steps WHERE "
                           "route_id = %s", row[2]))
    print("AT-961-22-2 fail-create steps", done)
    assert all(done[s] == "OK" for s in ("SCAFFOLD_FILES", "COPY_WORKSPACE", "GIT_INIT",
                                         "GIT_COMMIT")) and done["GH_REPO_CREATE"] == "FAILED"
    root = renv.scaffold / "int-retry"
    commit = rgs.git(root, "rev-parse", "HEAD").strip()
    fake_gh.mode("ok")
    retried = renv.env.post(f"/research/projects/{rid}:route", {
        **body, "console_project_id": project, "github_token": rgs.FAKE_TOKEN, "retry": True})
    assert retried.status_code == 200, retried.text
    assert rgs.git(root, "rev-parse", "HEAD").strip() == commit, "本地步驟不重做"
    assert not [(t, c) for t, c, v in rgs.all_text_columns(renv.rdb)
                if v and rgs.contains_secret(str(v), rgs.FAKE_TOKEN)]

# ── AT-961-22-3／22-4：同一條鏈（接 22-1）：拆解→tcs-draft→凍結 Stage-2→SCR MINOR ───────────
def chain_ready(renv: rgs.RouteEnv, monkeypatch: pytest.MonkeyPatch) -> tuple[str, dict[str, Any]]:
    rid = rgs.seed_gate0(renv, prd=PRD)
    assert rgs.confirm(renv, rid, rgs.body_a(renv)).status_code == 200
    use_brain(renv, FakeBrain([step(1), step(2, ["S01"])]), renv.tmp)
    enable_claude(renv)
    set_script(renv, monkeypatch, OK_DRAFT)
    route = renv.env.db.active_route(rid)
    assert route is not None
    return rid, route


def test_AT_961_22_3_decompose_then_tcs_draft_then_freeze_stage_2(
        renv: rgs.RouteEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    rid, route = chain_ready(renv, monkeypatch)
    # D-110：未拆解前 tcs-draft 前置不成立（409）
    early = renv.env.post(f"/research/projects/{rid}/stages/tcs-draft:start",
                          {"requested_by": rt.ALICE})
    assert early.status_code == 409, early.text
    print("AT-961-22-3 tcs-draft before decompose:", early.status_code, early.json().get("reason"))
    dec = post_decompose(renv, rid)
    assert dec.status_code == 200, dec.text
    start(renv, rid)
    dec_row = renv.rdb.one("SELECT tcs_rel_path, tcs_sha256 FROM console.research_decompositions "
                           "WHERE research_id = %s", rid)
    assert dec_row is not None and dec_row[0] and dec_row[1]
    tcs = published_tcs(route)
    assert (Path(route["target_path"]) / tcs).is_file()
    assert [t[1] for t in trace(renv, route)[-3:]] == ["SPEC_DRAFTING", "SCG_VALIDATION",
                                                       "HUMAN_PENDING"]
    print("AT-961-22-3 inner show (HUMAN_PENDING):\n" + show_text(renv, route))
    enable_freeze(renv)
    ok = freeze(renv, route, [tcs])
    assert ok.status_code == 200 and ok.json()["current_state"] == "SPEC_FROZEN", ok.text
    stages = [s["stage"] for s in fsm_ops.show(inner(renv, route))["frozen_stages"]]
    assert stages[-1] == "Stage-2" and "Stage-1" in stages
    print("AT-961-22-3 inner show (Stage-2 frozen):\n" + show_text(renv, route))


def test_AT_961_22_4_scr_minor_sequence_matches_the_manual_equivalent_on_a_fixture_state(
        renv: rgs.RouteEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    """夾具態：內環鍵以 transition 推到 IMPLEMENTATION（非真實開發 run，不充當真實演練）。"""
    rid, route = chain_ready(renv, monkeypatch)
    inner_to(renv, route, "IMPLEMENTATION")
    scr = post_scr(renv, rid, affected_sections=["1", "AC-001-1"])
    assert scr.status_code == 202, scr.text
    resp = outer_loop(renv, rid, PRD.replace("# PRD（拆解橋夾具", "# PRD v2（拆解橋夾具"))
    assert resp.status_code == 200, resp.text
    assert resp.json()["scr_apply"] == {"status": "APPLIED", "detail": ""}
    assert labels(renv, rid) == ["transition(SPEC_AUDIT)", *TAIL]
    assert fsm_ops.current_state(inner(renv, route)) == "IMPLEMENTATION"
    bridge = [(t[0], t[1]) for t in trace(renv, route)[-3:]]
    # 人工等價序列（另一鍵、同一份 CLI）
    from tests.test_research_scr import cli, routed

    rid2, route2 = routed(renv, "demo2")
    inner_to(renv, route2, "IMPLEMENTATION")
    key, sdir, root = route2["impl_fsm_project"], route2["impl_state_dir"], route2["target_path"]
    cli(renv, key, sdir, "transition", "--to", "SPEC_AUDIT", "--reason", "manual",
        "--trigger", sdd_cli.RESEARCH_TRIGGER)
    cli(renv, key, sdir, "spec-refreeze", "--doc", "docs/01_requirements/demo2_PRD.md",
        "--root", root, "--reason", "manual", "--approver", ADMIN)
    cli(renv, key, sdir, "transition", "--to", "PR_REVIEW", "--reason", "manual",
        "--trigger", sdd_cli.RESEARCH_TRIGGER)
    cli(renv, key, sdir, "gate", "--gate", "PR_REVIEW", "--result", "FAIL", "--reason", "manual")
    manual = [(t[0], t[1]) for t in trace(renv, route2)[-3:]]
    print("AT-961-22-4 bridge decision_trace tail", bridge, "manual", manual)
    assert bridge == manual, (bridge, manual)


# ── AT-961-22-E-1：假 gh 夾具可被 gitops 以 PATH 解析並執行 ────────────────────────────────
def test_AT_961_22_E_1_the_fake_gh_resolves_on_path_and_records_argv_and_env_keys(
        fake_gh: rgs.FakeGh, tmp_path: Path) -> None:
    found = shutil.which("gh")
    assert found is not None and Path(found).parent.resolve() == fake_gh.bin_dir.resolve()
    work = tmp_path / "w"
    work.mkdir()
    proc = subprocess.run([found, "auth", "status"], capture_output=True, text=True, cwd=work,
                          env={**os.environ, "GH_TOKEN": "x" * 3}, check=False)
    assert proc.returncode == 0 and "fake-user" in proc.stdout
    fake_gh.mode("unauth")
    assert subprocess.run([found, "auth", "status"], capture_output=True, text=True, cwd=work,
                          check=False).returncode == 1
    calls = fake_gh.calls()
    assert [c["argv"] for c in calls] == [["auth", "status"], ["auth", "status"]]
    assert calls[0]["has_gh_token"] is True and "PATH" in calls[0]["env_keys"]
    assert (rgs.FAKE_GH_DIR / "gh").is_file() and (rgs.FAKE_GH_DIR / "gh.cmd").is_file()
    assert sys.platform  # 另一平台那份標「未驗」


# ── AT-961-22-E-2：兩種來源（clone／archive）的最小路徑 ───────────────────────────────────────
@pytest.mark.parametrize("mode", ["clone", "archive"])
def test_AT_961_22_E_2_both_disposable_sources_pass_the_minimal_route(
        make_env: Callable[..., Any], route_db: ThrowawayDb, tmp_path: Path, real_tree: Path,
        fake_gh: rgs.FakeGh, mode: str) -> None:
    before = real_repo_state()
    repo = make_source(mode, tmp_path / f"src-{mode}")
    renv = env_on(make_env, route_db, tmp_path, real_tree, repo)
    try:
        rid = rgs.seed_gate0(renv)
        resp = rgs.confirm(renv, rid, rgs.body_a(renv))
        assert resp.status_code == 200, resp.text
        route = renv.env.db.active_route(rid)
        assert route is not None and route["base_ref"] == "main"
        wt = Path(route["target_path"]).parent
        assert wt.is_dir() and route["git_branch"] in rgs.git(repo, "branch", "--list")
        published = Path(route["target_path"]) / "docs" / "01_requirements" / "demo_PRD.md"
        assert published.is_file()
        if mode == "archive":
            assert len(rgs.git(repo, "log", "--oneline").splitlines()) == 1, "無歷史"
    finally:
        rgs.cleanup_worktrees(repo)
    assert real_repo_state() == before
