"""追溯表、Release Tag、PR 的交付層（TCS AT-962-17-*、18-*、20-*、26-2、26-3；PKG-BR-P2）。

純函式部分（追溯表導出、摘要截斷、PR 模板）不需任何環境；整合部分用 P1 的真 git／假 gh／拋棄式庫夾具
（`renv`）與 `file://` 的 bare repo 當 origin。真 GitHub 全程不連（AT-962-28-E-3 的同一原則）。
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from app.research import delivery, scr

PRD_N = ("# PRD\n\n## 5. 功能需求\n\nFR-R2P-01 批次提交；FR-R2P-02 匯出。\n\n"
         "#### US-001 提交批次\n- **對應 AC**: AC-001-1、AC-001-2\n\n"
         "#### US-002 匯出結果\n- **對應 AC**: AC-002-1\n\n"
         "#### AC-001-1 提交合法批次\nGiven 合法批次 When 提交 Then 回 202。\n\n"
         "#### AC-001-2 提交不存在的樣板\nGiven 不存在的樣板 When 提交 Then 回 422。\n\n"
         "#### AC-002-1 匯出 CSV\nGiven 有結果 When 匯出 Then 得到 CSV。\n")
STAMP = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)


def task(task_id: str, status: str, covers: list[str], at: datetime | None = STAMP
         ) -> dict[str, Any]:
    return {"task_id": task_id, "status": status, "completed_at": at, "covers_ac": covers}


def decision(gate: str, verdict: str) -> dict[str, Any]:
    return {"gate": gate, "decision": verdict}


def trace(tasks: list[dict[str, Any]], decisions: list[dict[str, Any]] | None = None, *,
          prd: str = PRD_N, decomposed: bool = True) -> dict[str, Any]:
    return delivery.build_traceability(prd, decomposed=decomposed, tasks=tasks,
                                       decisions=decisions or [], impl_key="demo-app")


def by_ac(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {r["ac"]: r for r in result["rows"]}


# ── AT-962-17-1（純函式半）：一個 AC 一列、集合相等、欄位固定 ─────────────────
def test_AT_962_17_1_one_row_per_frozen_ac_with_the_fixed_columns() -> None:
    result = trace([task("T1", "COMPLETED", ["AC-001-1", "AC-001-2"])])
    expected = scr.parse_frozen_prd(PRD_N).acs
    assert {r["ac"] for r in result["rows"]} == set(expected) == {
        "AC-001-1", "AC-001-2", "AC-002-1"}
    assert len(result["rows"]) == len(expected), "無重複列"
    assert set(result["rows"][0]) == {"ac", "userStory", "gherkinSummary", "unitStatus",
                                      "e2eStatus", "lastRunAt", "source"}
    assert result["totals"]["acTotal"] == 3
    row = by_ac(result)["AC-001-1"]
    assert row["userStory"] == "US-001 提交批次"
    assert row["gherkinSummary"] == {"given": "合法批次", "when": "提交", "then": "回 202。"}


# ── AT-962-17-2：gherkinSummary 每段至多 120 字 ─────────────────────────────────────────────────
@pytest.mark.parametrize("length", [119, 120, 121])
def test_AT_962_17_2_each_gherkin_segment_is_clipped_to_120_characters(length: int) -> None:
    text = "字" * length
    summary = delivery.gherkin_summary(f"Given {text} When {text} Then {text}")
    for segment in summary.values():
        assert len(segment) <= 120
    if length <= 120:
        assert summary["given"] == text
    else:
        assert summary["given"].endswith("…") and len(summary["given"]) == 120


def test_AT_962_17_2_html_is_stripped_to_plain_text() -> None:
    summary = delivery.gherkin_summary("Given <script>alert(1)</script>有批次 When 提交 Then 成功")
    assert "<" not in summary["given"] and summary["given"].endswith("有批次")


# ── AT-962-17-3：unitStatus 導出 ────────────────────────────────────────────────────────────────
def test_AT_962_17_3_unit_status_follows_the_covering_tasks_terminal_states() -> None:
    later = datetime(2026, 11, 7, 13, 0, tzinfo=UTC)
    all_done = by_ac(trace([task("T1", "COMPLETED", ["AC-001-1"]),
                            task("T2", "COMPLETED", ["AC-001-1"], later)]))["AC-001-1"]
    assert all_done["unitStatus"] == "PASS" and all_done["lastRunAt"] == later.isoformat()
    assert set(all_done["source"]) == {"task:T1", "task:T2", "RTM-COVERAGE-demo-app.yaml"}
    for bad in ("FAILED", "ESCALATED"):
        mixed = by_ac(trace([task("T1", "COMPLETED", ["AC-001-1"]),
                             task("T2", bad, ["AC-001-1"])]))["AC-001-1"]
        assert mixed["unitStatus"] == "FAIL", bad
    for pending in ("PENDING", "RUNNING", "SKIPPED", "CANCELLED"):
        waiting = by_ac(trace([task("T1", "COMPLETED", ["AC-001-1"]),
                               task("T2", pending, ["AC-001-1"], None)]))["AC-001-1"]
        assert waiting["unitStatus"] == "NOT_RUN", pending
    none = by_ac(trace([task("T1", "COMPLETED", ["AC-001-1"])]))["AC-002-1"]
    assert none["unitStatus"] == "NONE" and none["lastRunAt"] is None and none["source"] == []


# ── AT-962-17-4：e2eStatus ──────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(("decisions", "expected"), [
    ([], "NOT_RUN"),
    ([decision("SCG5", "APPROVED")], "PASS"),
    ([decision("SCG5", "APPROVED"), decision("SCG5", "REJECTED")], "NOT_RUN"),
    ([decision("SCG5", "APPROVED"), decision("SCG6", "REJECTED")], "NOT_RUN"),
    ([decision("SCG4", "APPROVED")], "NOT_RUN"),
    ([decision("SCG5", "REJECTED"), decision("SCG5", "APPROVED")], "PASS"),
], ids=["none", "approved", "approved-then-rejected", "approved-then-ci-red", "scg4-only",
        "rejected-then-approved"])
def test_AT_962_17_4_e2e_is_pass_only_after_an_scg5_approval_with_no_later_rejection(
        decisions: list[dict[str, Any]], expected: str) -> None:
    assert delivery.e2e_status(decisions) == expected
    assert {r["e2eStatus"] for r in trace([], decisions)["rows"]} == {expected}


# ── AT-962-17-5：totals ────────────────────────────────────────────────────────────────────────
def test_AT_962_17_5_uncovered_counts_non_pass_rows_and_ignores_the_e2e_column() -> None:
    result = trace([task("T1", "COMPLETED", ["AC-001-1"]), task("T2", "FAILED", ["AC-001-2"])],
                   [decision("SCG5", "APPROVED")])
    totals = result["totals"]
    assert (totals["acTotal"], totals["covered"], totals["uncovered"]) == (3, 1, 2)
    assert totals["covered"] + totals["uncovered"] == totals["acTotal"]
    assert trace([])["totals"]["uncovered"] == 3, "零測試不是通過"
    assert trace([task("T1", "COMPLETED", ["AC-001-1", "AC-001-2", "AC-002-1"])])[
        "totals"] == {"acTotal": 3, "covered": 3, "uncovered": 0, "frTotal": 2}


def test_AT_962_17_5_fr_total_shares_the_ac_parsing_path_and_is_zero_without_fr_entries() -> None:
    assert trace([])["totals"]["frTotal"] == len(scr.parse_frozen_prd(PRD_N).frs) == 2
    no_fr = PRD_N.replace("FR-R2P-01 批次提交；FR-R2P-02 匯出。", "沒有任何功能需求編號。")
    assert trace([], prd=no_fr)["totals"]["frTotal"] == 0
    assert trace([], prd=PRD_N + "\nFR-R2P-01 又提一次\n")["totals"]["frTotal"] == 2, "去重"
    assert scr.parse_frozen_prd("FRX-1 與 AFR-2 不算").frs == frozenset()


# ── AT-962-17-E-2：拆解缺席或 stale ─────────────────────────────────────────────────────────────
def test_AT_962_17_E_2_without_a_valid_decomposition_every_row_is_none() -> None:
    result = trace([task("T1", "COMPLETED", ["AC-001-1"])], decomposed=False)
    assert {r["unitStatus"] for r in result["rows"]} == {"NONE"}
    assert result["totals"]["uncovered"] == result["totals"]["acTotal"] == 3


# ── AT-962-17-E-3：AC 數邊界 ────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("count", [1, 250])
def test_AT_962_17_E_3_the_row_count_equals_the_ac_count_without_paging(count: int) -> None:
    prd = "# PRD\n\n" + "".join(
        f"#### AC-{n:03d}-1 項目 {n}\nGiven a When b Then c\n\n" for n in range(1, count + 1))
    result = trace([], prd=prd)
    assert len(result["rows"]) == count == result["totals"]["acTotal"]


# ── AT-962-20-2：PR 標題與內文模板 ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("length", [59, 60, 61])
def test_AT_962_20_2_the_pr_title_truncates_the_project_title_at_sixty_characters(
        length: int) -> None:
    title = delivery.pr_title("RP-0007", "題" * length, 2, 3)
    assert title == f"feat: RP-0007 {'題' * min(length, 60)}（2 FR／3 AC）"


def test_AT_962_20_2_the_body_has_four_sections_in_order_and_stays_within_4000() -> None:
    from types import SimpleNamespace

    ctx = SimpleNamespace(
        ref=SimpleNamespace(semver="v1.0.0", sha256="a" * 64, rel="01_specs/PRD-v1.0.0.md"),
        trace=trace([task("T1", "COMPLETED", ["AC-001-1"])]))
    body = delivery.pr_body({"rp_no": "RP-0007", "id": "rid"}, ctx)   # type: ignore[arg-type]
    heads = [line for line in body.splitlines() if line.startswith("## ")]
    assert heads == ["## 摘要", "## 追溯表摘要", "## 規格依據", "## 確認"]
    assert "2 FR／3 AC" in body and "已覆蓋：1；未覆蓋：2" in body and len(body) <= 4000


@pytest.mark.parametrize("slack", [1, 0, -1])
def test_AT_962_20_2_an_oversized_body_is_cut_at_a_section_boundary(slack: int) -> None:
    """邊界：總長恰為上限＋slack（上限前一格、剛好、超過一格）；超過時整段移除而不是切半。"""
    first, second = "## 摘要\n" + "字" * 100, "## 確認\n" + "字" * 100
    limit = len(first) + 2 + len(second) - slack
    body = delivery.clip_body([first, second], limit=limit)
    assert len(body) <= limit
    assert body == (f"{first}\n\n{second}" if slack <= 0 else first)

def test_AT_962_20_2_a_single_oversized_section_is_hard_cut_to_the_limit() -> None:
    assert len(delivery.clip_body(["字" * 5000])) == 4000
    assert delivery.clip_body(["a", "b"]) == "a\n\nb"


# ── AT-962-20-3（純函式半）：title 只作預覽、ack 必須為 true ──────────────────────────────────────
def test_AT_962_20_3_title_must_equal_the_template_and_the_preview_ack_must_be_true() -> None:
    expected = delivery.pr_title("RP-0007", "標題", 1, 2)
    rules = lambda body: [v["rule"] for v in delivery.pr_request_violations(body, expected)]  # noqa: E731
    assert rules({"body_preview_ack": True}) == []
    assert rules({"body_preview_ack": True, "title": expected}) == []
    assert rules({"body_preview_ack": True, "title": "自訂標題"}) == ["title_not_template"]
    assert rules({"body_preview_ack": False}) == ["preview_ack_required"]
    assert rules({}) == ["preview_ack_required"]
    assert rules({"body_preview_ack": "true"}) == ["preview_ack_required"]
    assert rules({"body_preview_ack": True, "branch": "-x"}) == ["invalid_ref"]
    assert rules({"body_preview_ack": True, "branch": "a..b"}) == ["invalid_ref"]
    assert rules({"body_preview_ack": True, "branch": "feature/x"}) == []


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 整合：真 git（拋棄式 repo＋`file://` 的 bare origin）、假 gh、真 FSM、拋棄式庫
# ══════════════════════════════════════════════════════════════════════════════════════════════
import json as _json  # noqa: E402
import sys  # noqa: E402
import uuid  # noqa: E402
from pathlib import Path  # noqa: E402

from app.errors import ApiError  # noqa: E402
from app.research import db as db_module  # noqa: E402
from app.research import gitops, inner_gates  # noqa: E402
from app.research import settings as settings_mod  # noqa: E402
from app.research.outbox import DbBlocked, Op  # noqa: E402
from tests import research_git_support as rgs  # noqa: E402
from tests import test_research_healing as hs  # noqa: E402
from tests import test_research_inner_gates as ig  # noqa: E402
from tests import test_research_router as rt  # noqa: E402
from tests.test_research_scr import ADMIN, cli, inner, inner_to, post_scr, sdk_trigger  # noqa: E402

make_env = rt.make_env
route_db, real_tree, renv, fake_gh = rgs.route_db, rgs.real_tree, rgs.renv, rgs.fake_gh
rtm, verbs = ig.rtm, ig.verbs
PRD_FULL = (rgs.PRD_PLACEMENT.split("## 1. 背景")[0] + PRD_N.split("# PRD\n", 1)[1]
            + "\n## 9. 模組落點表\n\n| 元件 | 落點 |\n|---|---|\n| UI 與後端 | AgentConsole |\n")
TAG = "v1.2.3"
FORBIDDEN_VERBS = {"checkout", "restore", "reset", "clean", "stash"}


class Calls(list[tuple[str, ...]]):
    """Bridge 放行並 spawn 的每個 git／gh 呼叫（argv 去掉工具名之前的 `git`／`gh`）。"""

    def of(self, *prefix: str) -> list[tuple[str, ...]]:
        return [c for c in self if c[:len(prefix)] == prefix]

    def tools(self, tool: str) -> list[tuple[str, ...]]:
        return [c[1:] for c in self if c[0] == tool]


@pytest.fixture(autouse=True)
def direct_fake_gh(monkeypatch: pytest.MonkeyPatch) -> None:
    """Windows 的 `gh.cmd` 薄殼讓含換行的引數（PR 內文）在 cmd.exe 被截斷：整合測試改以同一支
    `gh_fake.py` 直接由 Python 啟動（argv 與環境照 Bridge 傳的；PATH 上的 gh 仍在）。"""
    real = gitops._spawn

    def spawn(argv: Any, cwd: Path, env: Any, timeout: float) -> Any:
        if argv[0] == "gh":
            argv = [sys.executable, str(rgs.FAKE_GH_DIR / "gh_fake.py"), *argv[1:]]
        return real(argv, cwd, env, timeout)

    monkeypatch.setattr(gitops, "_spawn", spawn)


@pytest.fixture
def calls() -> Any:
    log = Calls()

    def record(rec: gitops.CallRecord) -> None:
        log.append(tuple(rec.argv))

    gitops.OBSERVERS.append(record)
    yield log
    gitops.OBSERVERS.remove(record)


class Project:
    def __init__(self, renv: rgs.RouteEnv, rid: str, route: dict[str, Any], run_id: str) -> None:
        self.renv, self.rid, self.route, self.run_id = renv, rid, route, run_id
        self.cwd = Path(route["target_path"])

    def tag(self, **over: Any) -> Any:
        body: dict[str, Any] = {"tag_name": TAG, "message": "", "push": True, "approver": ADMIN,
                                "run_id": self.run_id, "requested_by": ADMIN}
        body.update(over)
        return self.renv.env.post(f"/research/projects/{self.rid}:tag", body)

    def pr(self, **over: Any) -> Any:
        body: dict[str, Any] = {"body_preview_ack": True, "approver": ADMIN,
                                "github_token": rgs.FAKE_TOKEN}
        body.update(over)
        return self.renv.env.post(f"/research/projects/{self.rid}:pr", body)

    def rows(self, kind: str | None = None) -> list[tuple[Any, ...]]:
        where = "research_id = %s" + ("" if kind is None else f" AND kind = '{kind}'")
        return self.renv.rdb.q(
            "SELECT kind, ref, commit_sha, url, rtm_run_id::text, rtm_report_ref, snapshot_sha256, "
            f"fsm_state_after, status, detail, created_by FROM console.research_deliveries "
            f"WHERE {where} ORDER BY created_at", self.rid)

    def state(self) -> str:
        return ig.inner_state(self.renv, self.route)

    def snapshot_path(self) -> Path:
        return Path(self.renv.env.db.get_project(self.rid)["workspace_path"]) / delivery.TRACE_REL

    def git(self, *args: str) -> str:
        return rgs.git(self.cwd, *args)


def seed_task(renv: rgs.RouteEnv, rid: str, key: str, status: str, covers: list[str]) -> None:
    project = hs.console_of(renv, rid)
    goal = renv.rdb.one("INSERT INTO console.goals (project_id, name, pass_criteria) VALUES "
                        "(%s, 'g', 'x') RETURNING id", project)
    assert goal is not None
    spec = _json.dumps({"source": "research_decomposition", "taskId": key, "coversAc": covers})
    renv.rdb.exec(
        "INSERT INTO console.tasks (goal_id, name, pass_criteria, status, pass_criteria_spec, "
        "completed_at) VALUES (%s, %s, 'x', %s, %s::jsonb, NOW())", goal[0], key, status, spec)


def build_project(renv: rgs.RouteEnv, slug: str = "demo", *, state: str = "RELEASE_READY",
                  covered: bool = True, origin: bool = True, signed: bool = True) -> Project:
    rid = rgs.seed_gate0(renv, slug, prd=PRD_FULL)
    resp = rgs.confirm(renv, rid, rgs.body_a(renv))
    assert resp.status_code == 200, resp.text
    route = renv.env.db.active_route(rid)
    assert route is not None
    if signed:
        sha = delivery.decompose_plan.frozen_prd(renv.env.db, rid).sha256   # type: ignore[attr-defined]
        renv.rdb.exec(
            "INSERT INTO console.research_decompositions (research_id, path, prd_sha256, "
            "tasks_count, status, created_by) VALUES (%s, 'C', %s, 1, 'SIGNED_OFF', 'seed')",
            rid, sha)
    if covered:
        seed_task(renv, rid, "T1", "COMPLETED", ["AC-001-1", "AC-001-2", "AC-002-1"])
    inner_to(renv, route, state)
    run_id = hs.seed_steps(renv, rid, [])
    project = Project(renv, rid, route, run_id)
    if origin:
        bare = renv.tmp / f"origin-{slug}.git"
        rgs.git(renv.tmp, "init", "--bare", "-b", "main", str(bare))
        # 各 worktree 共用同一個 .git 設定：remote 已存在就改指向本專案的 bare repo
        have = project.git("remote").split()
        project.git("remote", "set-url" if "origin" in have else "add", "origin", bare.as_uri())
        project.bare = bare                                          # type: ignore[attr-defined]
    return project


# ── AT-962-17-6／17-E-1／17-E-2：預覽 ───────────────────────────────────────────────────────────
def preview(project: Project) -> Any:
    return project.renv.env.post(f"/research/projects/{project.rid}:traceability-preview", {})


def tree_snapshot(project: Project) -> tuple[Any, ...]:
    ws = Path(project.renv.env.db.get_project(project.rid)["workspace_path"])
    return (rgs.tree_hash(ws), project.renv.rdb.count("research_events"),
            project.renv.rdb.count("research_deliveries"),
            project.renv.rdb.count("research_gate_decisions"))


def test_AT_962_17_E_1_an_unfrozen_project_answers_409_prd_not_frozen_without_writes(
        renv: rgs.RouteEnv) -> None:
    rid = rgs.seed_gate0(renv, "unfrozen", approve=False)
    before = (renv.rdb.count("research_events"), renv.rdb.count("research_deliveries"))
    resp = renv.env.post(f"/research/projects/{rid}:traceability-preview", {})
    assert (resp.status_code, resp.json()["reason"]) == (409, "fsm_state_conflict")
    assert resp.json()["details"]["unmet"] == ["prd_not_frozen"]
    assert (renv.rdb.count("research_events"), renv.rdb.count("research_deliveries")) == before


def test_AT_962_17_6_the_preview_changes_nothing_and_has_the_documented_shape(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture) -> None:
    project = build_project(renv, origin=False)
    before = tree_snapshot(project)
    for _ in range(3):
        resp = preview(project)
        assert resp.status_code == 200, resp.text
        assert set(resp.json()) == {"rows", "totals", "rtm", "generatedAt"}
    assert tree_snapshot(project) == before
    body = preview(project).json()
    assert body["totals"] == {"acTotal": 3, "covered": 3, "uncovered": 0, "frTotal": 2}
    with_rtm = renv.env.post(f"/research/projects/{project.rid}:traceability-preview",
                             {"run_id": project.run_id}).json()
    assert with_rtm["rtm"]["advisory"] is True and with_rtm["rtm"]["fullyCovered"] is True


@pytest.mark.parametrize("mode", ["absent", "stale"])
def test_AT_962_17_E_2_the_preview_endpoint_marks_every_row_none_without_a_valid_decomposition(
        renv: rgs.RouteEnv, mode: str) -> None:
    project = build_project(renv, f"nd-{mode}", origin=False, signed=mode == "stale")
    if mode == "stale":
        renv.rdb.exec("UPDATE console.research_decompositions SET status = 'STALE' "
                      "WHERE research_id = %s", project.rid)
    body = preview(project).json()
    assert {r["unitStatus"] for r in body["rows"]} == {"NONE"}
    assert body["totals"]["uncovered"] == body["totals"]["acTotal"] == 3


# ── AT-962-18-1／18-3／18-4／18-5：Tag 正控 ─────────────────────────────────────────────────────
def test_AT_962_18_1_the_tag_sequence_runs_in_order_and_ends_in_release(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: Calls, verbs: ig.VerbLog) -> None:
    project = build_project(renv)
    calls.clear(), verbs.clear()
    reconciles = len(ig.events_of(renv, project.rid, "research.reconcile"))
    resp = project.tag()
    assert resp.status_code == 201, resp.text
    git_calls = calls.tools("git")
    wanted = [("tag", "--list", TAG), ("rev-parse", "--verify", "HEAD"), ("tag", "-a", TAG),
              ("remote", "get-url", "origin"), ("ls-remote", "--tags", "origin", TAG),
              ("push", "origin", TAG)]
    positions = [next(i for i, c in enumerate(git_calls) if c[:len(w)] == w) for w in wanted]
    assert positions == sorted(positions)
    assert verbs.verbs() == ["transition"] and project.snapshot_path().is_file()
    assert resp.json()["fsmState"] == "RELEASE" and project.state() == "RELEASE"
    assert len(ig.events_of(renv, project.rid, "research.reconcile")) == reconciles + 1
    assert ig.events_of(renv, project.rid, "research.reconcile")[-1]["consistent"] is True
    assert project.git("ls-remote", "--tags", "origin").count(TAG) >= 1 or rgs.git(
        project.bare, "tag", "--list") == f"{TAG}\n"           # type: ignore[attr-defined]


def test_AT_962_18_3_4_the_snapshot_file_and_the_delivery_row_agree(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: Calls) -> None:
    project = build_project(renv)
    assert project.tag().status_code == 201
    raw = project.snapshot_path().read_bytes()
    doc = _json.loads(raw)
    assert list(doc)[:5] == ["research_id", "rp_no", "tag_name", "commit_sha", "prd_sha256"]
    assert set(doc) >= {"frozen_digests", "generated_at", "rows", "totals"}
    assert b"\r" not in raw and "追溯".encode() not in raw or b"\\u" not in raw
    assert doc["totals"]["frTotal"] == 2
    (row,) = project.rows("RELEASE_TAG")
    kind, ref, commit, url, run, report_ref, snap, after, status, detail, created_by = row
    assert (kind, ref, url, status, created_by) == ("RELEASE_TAG", TAG, None, "CREATED", ADMIN)
    assert len(commit) == 40 and run == project.run_id and after == "RELEASE_READY"
    assert report_ref == delivery.TRACE_REL and snap.strip() == hashlib_sha(raw)
    (event,) = [p for p in ig.events_of(renv, project.rid, "research.delivery")]
    assert event == {"kind": "RELEASE_TAG", "ref": TAG, "status": "CREATED",
                     "digest": snap.strip(), "reason": "", "failure_step": None}
    tag_call = calls.of("git", "tag", "-a")[0]
    message = " ".join(tag_call[tag_call.index("-m") + 1:])     # 紀錄以空白切 argv：重組訊息
    assert message == gitops.release_message(TAG, project.renv.env.db.get_project(
        project.rid)["rp_no"], snap.strip()[:12])


def hashlib_sha(raw: bytes) -> str:
    import hashlib

    return hashlib.sha256(raw).hexdigest()


def test_AT_962_18_5_the_release_transition_uses_the_documented_reason_and_writes_the_cursor(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, verbs: ig.VerbLog) -> None:
    project = build_project(renv)
    verbs.clear()
    assert project.tag().status_code == 201
    (verb, args), = verbs.writes()
    rp_no = renv.env.db.get_project(project.rid)["rp_no"]
    assert verb == "transition" and args == (
        "--to", "RELEASE", "--reason", f"release tag {TAG}; research={rp_no}", "--trigger",
        "research_bridge")
    # 規格字面（V22 起 flow_phase 可為 DELIVERED；V21 庫寫入會 23514＝LAST_VERSION 落後的機械鎖）
    assert ig.cursor(renv, project.rid)[:3] == ("deliver", "DELIVERED", "COMPLETED")
    manual = build_project(renv, "manual", origin=False)
    cli(renv, manual.route["impl_fsm_project"], manual.route["impl_state_dir"], "transition",
        "--to", "RELEASE", "--reason", "manual", "--trigger", sdk_trigger())
    assert ig.trace_tail(inner(renv, project.route), 1) == ig.trace_tail(
        inner(renv, manual.route), 1)


# ── AT-962-18-2／18-E-4：訊息只取模板 ────────────────────────────────────────────────────────────
@pytest.mark.parametrize("message", ["一般備註 ghp_FAKE_R2P2_TOKEN_000000000000000000 結尾",
                                     "--exec=evil", "line1\nline2", "$(touch pwned) `id`"])
def test_AT_962_18_2_the_user_message_never_reaches_argv_and_is_masked_in_detail(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: Calls, message: str) -> None:
    project = build_project(renv)
    assert project.tag(message=message).status_code == 201
    argv_text = "\n".join(" ".join(c) for c in calls)
    assert message not in argv_text and "touch pwned" not in argv_text
    template_args = calls.of("git", "tag", "-a")[0]
    sent = " ".join(template_args[template_args.index("-m") + 1:])
    assert sent.startswith(f"release: {TAG}（RP-") and sent.endswith("）")
    (row,) = project.rows("RELEASE_TAG")
    assert "ghp_FAKE_R2P2" not in row[9] and len(row[9]) <= 2000


@pytest.mark.parametrize("size", [2000, 2001])
def test_AT_962_18_2_detail_is_cut_at_2000_characters_by_the_record_operation(
        renv: rgs.RouteEnv, size: int) -> None:
    rid = rgs.seed_gate0(renv, f"det-{size}")
    renv.env.db.apply("delivery.record", {
        "research_id": rid, "actor": ADMIN, "event_ref": str(uuid.uuid4()),
        "row": {"kind": "RELEASE_TAG", "ref": "v0.0.1", "status": "CREATED", "created_by": ADMIN,
                "detail": "字" * size},
        "event": delivery.delivery_event("RELEASE_TAG", "CREATED", ref="v0.0.1")})
    assert renv.rdb.one("SELECT length(detail) FROM console.research_deliveries "
                        "WHERE research_id = %s", rid) == (2000,)


# ── AT-962-18-6／18-8：冪等續跑 ─────────────────────────────────────────────────────────────────
def test_AT_962_18_8_a_failed_release_transition_keeps_the_row_and_the_retry_only_transitions(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: Calls, verbs: ig.VerbLog,
        monkeypatch: pytest.MonkeyPatch) -> None:
    project = build_project(renv)
    real = inner_gates.fsm_ops.transition
    state = {"fail": True}

    def flaky(*a: Any, **k: Any) -> Any:
        if state["fail"]:
            state["fail"] = False
            raise ApiError(502, "sdd_cli_failed", detail="boom")
        return real(*a, **k)

    monkeypatch.setattr(inner_gates.fsm_ops, "transition", flaky)
    first = project.tag()
    assert (first.status_code, first.json()["reason"]) == (502, "delivery_step_failed")
    assert first.json()["details"]["failure_step"] == "fsm_release"
    assert len(project.rows("RELEASE_TAG")) == 1 and project.state() == "RELEASE_READY"
    failed = [p for p in ig.events_of(renv, project.rid, "research.delivery")
              if p["status"] == "FAILED"]
    assert failed and failed[0]["failure_step"] == "fsm_release" and failed[0]["ref"] is None
    calls.clear(), verbs.clear()
    second = project.tag()
    assert second.status_code == 201 and project.state() == "RELEASE"
    assert verbs.verbs() == ["transition"] and not calls.of("git", "tag", "-a")
    assert len(project.rows("RELEASE_TAG")) == 1


def test_AT_962_18_6_resending_after_a_full_success_writes_nothing_more(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: Calls, verbs: ig.VerbLog) -> None:
    project = build_project(renv)
    assert project.tag().status_code == 201
    calls.clear(), verbs.clear()
    again = project.tag()
    assert again.status_code == 201 and again.json()["fsmState"] == "RELEASE"
    assert verbs.writes() == [] and not calls.of("git", "tag", "-a")
    assert not calls.of("git", "push") and len(project.rows("RELEASE_TAG")) == 1


# ── AT-962-18-7：push 失敗與續跑 ────────────────────────────────────────────────────────────────
def test_AT_962_18_7_a_failed_push_keeps_the_local_tag_and_the_retry_succeeds_without_force(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: Calls) -> None:
    project = build_project(renv)
    good = rgs.git(project.cwd, "remote", "get-url", "origin").strip()
    project.git("remote", "set-url", "origin", (renv.tmp / "nowhere.git").as_uri())
    first = project.tag()
    assert (first.status_code, first.json()["reason"]) == (502, "delivery_step_failed")
    assert first.json()["details"]["failure_step"] == "push"
    assert project.git("tag", "--list", TAG).strip() == TAG
    assert project.rows("RELEASE_TAG") == [] and project.state() == "RELEASE_READY"
    project.git("remote", "set-url", "origin", good)
    second = project.tag()
    assert second.status_code == 201, second.text
    assert not [c for c in calls if "--force" in c or "-f" in c]
    assert len(project.rows("RELEASE_TAG")) == 1 and project.state() == "RELEASE"


# ── AT-962-18-9：push 確認規則 ──────────────────────────────────────────────────────────────────
def pushes(calls: Calls) -> list[tuple[str, ...]]:
    return [c for c in calls.tools("git") if c[0] == "push"]


@pytest.mark.parametrize("case", ["push-false", "no-origin"])
def test_AT_962_18_9_without_push_or_origin_nothing_is_pushed(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: Calls, case: str) -> None:
    project = build_project(renv, f"np-{case[:4]}", origin=case == "push-false")
    resp = project.tag(push=case != "push-false")
    assert resp.status_code == 201, resp.text
    assert pushes(calls) == [] and not calls.of("git", "ls-remote")


def test_AT_962_18_9_a_remote_tag_on_the_same_commit_counts_as_pushed(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: Calls) -> None:
    project = build_project(renv, "same")
    project.git("push", "origin", f"HEAD:refs/tags/{TAG}")
    calls.clear()
    assert project.tag().status_code == 201
    assert pushes(calls) == [] and calls.of("git", "ls-remote")


def test_AT_962_18_9_a_remote_tag_on_another_commit_is_refused_with_no_writes(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, verbs: ig.VerbLog) -> None:
    project = build_project(renv, "diff")
    project.git("push", "origin", f"HEAD~1:refs/tags/{TAG}")
    verbs.clear()
    resp = project.tag()
    assert (resp.status_code, resp.json()["reason"]) == (422, "invalid_request")
    assert resp.json()["violations"][0]["rule"] == "remote_tag_diverged"
    assert project.rows() == [] and verbs.writes() == [] and project.state() == "RELEASE_READY"


# ── AT-962-18-E-1／E-2／E-3／E-5 ────────────────────────────────────────────────────────────────
def test_AT_962_18_E_1_a_foreign_tag_of_the_same_name_is_409_tag_exists(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, verbs: ig.VerbLog) -> None:
    project = build_project(renv)
    project.git("tag", TAG)
    before = project.git("rev-parse", TAG)
    verbs.clear()
    resp = project.tag()
    assert (resp.status_code, resp.json()["reason"]) == (409, "tag_exists")
    assert project.rows() == [] and verbs.writes() == [] and project.git("rev-parse", TAG) == before


def test_AT_962_18_E_2_unmet_preconditions_are_409_without_any_git_call(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: Calls) -> None:
    not_ready = build_project(renv, "nr", state="IMPLEMENTATION")
    calls.clear()
    resp = not_ready.tag()
    assert (resp.status_code, resp.json()["reason"]) == (409, "fsm_state_conflict")
    assert "not_release_ready" in resp.json()["details"]["unmet"]
    uncovered = build_project(renv, "uc", covered=False)
    resp = uncovered.tag()
    assert resp.status_code == 409 and resp.json()["details"]["unmet"] == ["rtm_below_100"]
    opened = build_project(renv, "so")
    assert post_scr(renv, opened.rid, affected_sections=[]).status_code == 202
    resp = opened.tag()
    assert (resp.status_code, resp.json()["reason"]) == (409, "scr_open")
    assert calls.of("git", "tag") == [] and calls.of("git", "push") == []


def test_AT_962_18_E_3_requesting_a_github_release_is_422_without_side_effects(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: Calls) -> None:
    project = build_project(renv)
    calls.clear()
    resp = project.tag(create_github_release=True)
    assert (resp.status_code, resp.json()["reason"]) == (422, "invalid_request")
    assert resp.json()["violations"][0]["rule"] == "release_not_supported"
    assert not calls and project.rows() == []


def test_AT_962_18_E_5_drift_blocks_the_tag_before_the_state_check_and_any_git_call(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: Calls, verbs: ig.VerbLog) -> None:
    project = build_project(renv, state="IMPLEMENTATION")           # 現態也不合
    target = ig.frozen_prd(project.route)
    changed = target.read_bytes() + b"\nedited\n"
    target.write_bytes(changed)
    calls.clear(), verbs.clear()
    resp = project.tag()
    assert (resp.status_code, resp.json()["reason"]) == (422, "digest_mismatch")
    assert set(resp.json()["details"]["drift"][0]) == {"path", "expected_sha256", "actual_sha256"}
    assert not calls and project.rows() == [] and verbs.writes() == []
    assert not project.snapshot_path().exists() and target.read_bytes() == changed


# ── AT-962-17-E-4：零信任（不信請求帶入的列）────────────────────────────────────────────────────
def test_AT_962_17_E_4_forged_rows_in_the_request_are_ignored(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: Calls) -> None:
    project = build_project(renv, covered=False)
    forged = [{"ac": "AC-001-1", "unitStatus": "PASS", "e2eStatus": "PASS"}]
    calls.clear()
    resp = project.tag(rows=forged, totals={"uncovered": 0})
    assert resp.status_code == 409 and "rtm_below_100" in resp.json()["details"]["unmet"]
    assert not calls and "PASS" not in resp.text


# ── AT-962-20-1：PR 正控 ────────────────────────────────────────────────────────────────────────
def test_AT_962_20_1_the_pr_sequence_pushes_then_creates_and_records(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: Calls, fake_gh: rgs.FakeGh) -> None:
    project = build_project(renv)
    calls.clear(), fake_gh.clear()
    resp = project.pr()
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["created"] is True and body["delivery"]["url"].endswith("/pull/7")
    branch = project.route["git_branch"]
    ordered = [c for c in calls if c[:2] in (("git", "push"), ("gh", "pr"))]
    assert [c[:3] for c in ordered] == [("git", "push", "-u"), ("gh", "pr", "list"),
                                        ("gh", "pr", "create")] or [c[:2] for c in ordered]
    assert ("git", "push", "-u", "origin", branch) in ordered
    (row,) = project.rows("PULL_REQUEST")
    assert row[0] == "PULL_REQUEST" and row[1] == "7" and row[3].endswith("/pull/7")
    assert row[6] is None and row[8] == "CREATED"
    events = ig.events_of(renv, project.rid, "research.delivery")
    assert events[-1]["kind"] == "PULL_REQUEST" and events[-1]["ref"] == "7"
    created = [c for c in fake_gh.calls() if c["argv"][:2] == ["pr", "create"]]
    assert len(created) == 1 and created[0]["has_gh_token"] is True
    assert created[0]["argv"][created[0]["argv"].index("--head") + 1] == branch
    assert created[0]["argv"][created[0]["argv"].index("--title") + 1].startswith("feat: RP-")


# ── AT-962-20-3：title 與 ack ───────────────────────────────────────────────────────────────────
def test_AT_962_20_3_the_endpoint_refuses_a_foreign_title_and_a_missing_ack(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: Calls) -> None:
    project = build_project(renv)
    calls.clear()
    bad_title = project.pr(title="自訂標題")
    assert bad_title.status_code == 422
    assert bad_title.json()["violations"][0]["rule"] == "title_not_template"
    for ack in (False, None, "yes"):
        resp = project.pr(body_preview_ack=ack)
        assert (resp.status_code, resp.json()["violations"][0]["rule"]) == (
            422, "preview_ack_required")
    assert not calls and project.rows() == []


# ── AT-962-20-4：已有 PR 冪等 ───────────────────────────────────────────────────────────────────
def test_AT_962_20_4_an_existing_pr_is_returned_with_created_false(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: Calls, fake_gh: rgs.FakeGh,
        monkeypatch: pytest.MonkeyPatch) -> None:
    project = build_project(renv)
    monkeypatch.setenv("FAKE_GH_PR_LIST", '[{"url": "https://github.com/octocat/demo-app/pull/42"}]')
    calls.clear()
    first = project.pr()
    assert first.status_code == 200 and first.json()["created"] is False, first.text
    assert first.json()["delivery"]["url"].endswith("/pull/42")
    assert not calls.of("gh", "pr", "create")
    calls.clear()
    second = project.pr()                                   # 這次 DB 已有列：連 pr list 都不必呼叫
    assert second.status_code == 200 and second.json()["created"] is False
    assert not calls.of("gh", "pr") and len(project.rows("PULL_REQUEST")) == 1


# ── AT-962-20-5：前置缺項 ───────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("missing", ["gh", "gh_auth", "origin", "repo_writable"])
def test_AT_962_20_5_each_missing_prerequisite_is_422_with_its_item_and_no_side_effects(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: Calls, fake_gh: rgs.FakeGh,
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, missing: str) -> None:
    project = build_project(renv, f"pm-{missing[:5].replace('_', '-')}", origin=missing != "origin")
    if missing == "gh":
        rgs.hide_gh(monkeypatch, tmp_path)
    elif missing == "gh_auth":
        fake_gh.mode("unauth")
    elif missing == "repo_writable":
        monkeypatch.setattr(settings_mod, "repo_writable", lambda cfg=None: False)
    calls.clear()
    resp = project.pr()
    assert (resp.status_code, resp.json()["reason"]) == (422, "route_unsupported_in_deployment")
    assert missing in [m["item"] for m in resp.json()["details"]["missing"]]
    assert not calls.of("git", "push") and not calls.of("gh", "pr") and project.rows() == []


# ── AT-962-20-6／20-E-4：token 零外洩 ───────────────────────────────────────────────────────────
def test_AT_962_20_6_the_token_appears_nowhere_even_when_gh_leaks_it(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: Calls, fake_gh: rgs.FakeGh,
        caplog: pytest.LogCaptureFixture) -> None:
    project = build_project(renv)
    fake_gh.mode("leak")
    caplog.set_level("DEBUG")
    resp = project.pr()
    assert resp.status_code == 201, resp.text
    token = rgs.FAKE_TOKEN
    assert not rgs.contains_secret(resp.text, token)
    assert not rgs.contains_secret("\n".join(" ".join(c) for c in calls), token)
    assert not [hit for hit in rgs.all_text_columns(renv.rdb) if rgs.contains_secret(
        str(hit[2]), token)]
    assert not rgs.contains_secret(caplog.text, token)
    argv_logged = json_text(fake_gh.calls())
    created = [c for c in fake_gh.calls() if c["argv"][:2] == ["pr", "create"]]
    assert created and not rgs.contains_secret(json_text([c["argv"] for c in created]), token)
    assert token not in argv_logged


def json_text(value: Any) -> str:
    return _json.dumps(value, ensure_ascii=False)


# ── AT-962-20-7：失敗不補償 ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("failure", ["push", "pr_create"])
def test_AT_962_20_7_a_failed_step_is_502_with_a_failed_event_and_no_row(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: Calls, fake_gh: rgs.FakeGh,
        failure: str) -> None:
    project = build_project(renv, f"pf-{failure[:4].replace('_', '-')}")
    if failure == "push":
        project.git("remote", "set-url", "origin", (renv.tmp / "nowhere.git").as_uri())
    else:
        fake_gh.mode("fail-pr")
    resp = project.pr()
    assert (resp.status_code, resp.json()["reason"]) == (502, "delivery_step_failed")
    assert resp.json()["details"]["failure_step"] == failure
    assert "stderr_tail" in resp.json()["details"] and project.rows() == []
    failed = [p for p in ig.events_of(renv, project.rid, "research.delivery")]
    assert len(failed) == 1 and failed[0]["status"] == "FAILED" and failed[0]["ref"] is None
    assert failed[0]["failure_step"] == failure
    assert not [c for c in calls.tools("git") if c[0] in FORBIDDEN_VERBS | {"tag"}]


# ── AT-962-20-E-3：branch 驗證 ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("branch", ["-x", "a..b"])
def test_AT_962_20_E_3_an_invalid_branch_is_422_before_any_git_call(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: Calls, branch: str) -> None:
    project = build_project(renv, f"br-{len(branch)}")
    calls.clear()
    resp = project.pr(branch=branch)
    assert (resp.status_code, resp.json()["violations"][0]["rule"]) == (422, "invalid_ref")
    assert not calls


# ── AT-962-20-E-4：PR 標題與內文不含 token ──────────────────────────────────────────────────────
def test_AT_962_20_E_4_the_pr_title_and_body_carry_no_token(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, fake_gh: rgs.FakeGh) -> None:
    project = build_project(renv)
    assert project.pr().status_code == 201
    (created,) = [c for c in fake_gh.calls() if c["argv"][:2] == ["pr", "create"]]
    argv = created["argv"]
    title, body = argv[argv.index("--title") + 1], argv[argv.index("--body") + 1]
    assert rgs.FAKE_TOKEN not in title + body and "## 確認" in body and "2 FR／3 AC" in title


# ── AT-962-26-2／26-3：delivery.record ──────────────────────────────────────────────────────────
def record_payload(rid: str, ref: str, *, bad_event: bool = False) -> dict[str, Any]:
    event = (delivery.delivery_event("RELEASE_TAG", "CREATED", ref=ref)
             if not bad_event else {"kind": "RELEASE_TAG", "ref": ref, "status": "FAILED",
                                    "digest": None, "reason": "", "failure_step": "nope"})
    return {"research_id": rid, "actor": ADMIN, "event_ref": str(uuid.uuid4()), "event": event,
            "row": {"kind": "RELEASE_TAG", "ref": ref, "status": "CREATED", "created_by": ADMIN}}


def test_AT_962_26_2_the_row_and_the_event_commit_together_and_errors_are_not_swallowed(
        renv: rgs.RouteEnv) -> None:
    rid = rgs.seed_gate0(renv, "rec")
    db = renv.env.db
    events = renv.rdb.count("research_events")
    assert db.apply("delivery.record", record_payload(rid, "v0.0.1"))["applied"] is True
    assert renv.rdb.count("research_deliveries") == 1
    assert renv.rdb.count("research_events") == events + 1
    with pytest.raises(db_module.ResearchGuardError):
        db.apply("delivery.record", record_payload(rid, "v0.0.2", bad_event=True))
    assert renv.rdb.count("research_deliveries") == 1, "事件被拒＝同交易的列一併回滾"
    same = record_payload(rid, "v0.0.1")
    assert db.apply("delivery.record", same)["applied"] is False, "同 (研究, kind, ref) 冪等"
    assert renv.rdb.count("research_deliveries") == 1


def test_AT_962_26_3_a_blocked_database_parks_the_write_in_the_outbox_and_replay_writes_once(
        renv: rgs.RouteEnv) -> None:
    rid = rgs.seed_gate0(renv, "outbox")
    writer = ig.blocking_context(renv).writer
    renv.rdb.block()
    try:
        with pytest.raises(DbBlocked):
            writer.persist(Op("delivery.record", rid, record_payload(rid, "v0.0.9")))
    finally:
        renv.rdb.unblock()
    assert renv.rdb.count("research_deliveries") == 0
    assert not writer.replay().rejected
    assert renv.rdb.count("research_deliveries") == 1
    writer.replay()
    assert renv.rdb.count("research_deliveries") == 1
