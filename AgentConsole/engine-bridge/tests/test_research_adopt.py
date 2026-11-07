"""內環鍵建立與 Stage-1 基線採納（TCS AT-961-7-1～7-6、7-E-1、7-E-2；PKG-BR-D1；D-126）。

真 FSM CLI 在 `tmp_path` 的暫存狀態目錄實跑（缺 `SDD_ROOT`＝`TOOL-ABSENCE` skip）；FSM 子行程的 argv
取自 `popen_log`（`tests.test_research_router`）。內環鍵建檔需要 B1 補丁（交卷「需主控處理」）。
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import pytest

from app import sdd_cli
from app.errors import ApiError
from app.research import adopt, fsm_ops
from app.sdd_state import read_state
from tests import research_git_support as rgs
from tests import test_research_router as rt

make_env = rt.make_env
popen_log = rt.popen_log
route_db, real_tree, renv, fake_gh = rgs.route_db, rgs.real_tree, rgs.renv, rgs.fake_gh
PRD_TEXT = "# PRD\n\n基線採納測試。\n"
PRD_SHA = hashlib.sha256(PRD_TEXT.encode("utf-8")).hexdigest()


def make_ctx(tree: Path, root: Path, *, key: str = "agentconsole-demo",
             prd_rel: str = "docs/01_requirements/demo_PRD.md") -> adopt.AdoptCtx:
    prd = root / prd_rel
    prd.parent.mkdir(parents=True, exist_ok=True)
    prd.write_text(PRD_TEXT, encoding="utf-8", newline="\n")
    return adopt.AdoptCtx(
        sdd_root=tree, state_dir=root / "build" / "reports" / "fsm", key=key, root=root,
        prd_rel=prd_rel, outer_key="research-demo", gate_decision_id="gd-0001",
        prd_sha256=PRD_SHA, approver="admin@example.com", allowed_roots=[root])


def argvs(log: list[list[str]]) -> list[list[str]]:
    return [a[a.index(sdd_cli.CLI_MODULE) + 1:] for a in log if sdd_cli.CLI_MODULE in a]


def verbs_of(log: list[list[str]]) -> list[str]:
    return [a[0] for a in argvs(log)]


def flag(argv: list[str], name: str) -> str:
    return argv[argv.index(name) + 1]


# ── AT-961-7-1／7-E-2 ──────────────────────────────────────────────────────────────────────
def test_AT_961_7_1_the_adoption_sequence_runs_for_real_and_ends_frozen(
        real_tree: Path, tmp_path: Path, popen_log: list[list[str]]) -> None:
    ctx = make_ctx(real_tree, tmp_path / "root")
    result = adopt.adopt_baseline(ctx)
    assert result["created"] is True and result["frozen"] is True
    calls = argvs(popen_log)
    assert [a[0] for a in calls] == ["show"] + ["transition"] * 5 + ["spec-frozen"]
    assert "--must-exist" not in calls[0], "建檔那一次不帶 --must-exist"
    targets = [flag(a, "--to") for a in calls[1:6]]
    assert targets == ["SCENARIO_DETECT", "AGENT_LOAD", "SPEC_DRAFTING", "SCG_VALIDATION",
                       "HUMAN_PENDING"]
    for call in calls[1:6]:
        reason = flag(call, "--reason")
        assert reason.startswith("baseline adoption") and "research-demo" in reason
        assert "gate_decision gd-0001" in reason and flag(call, "--trigger") == "research_bridge"
    freeze = calls[6]
    assert flag(freeze, "--stage") == "Stage-1" and flag(freeze, "--doc") == ctx.prd_rel
    assert flag(freeze, "--root") == str(ctx.root) and flag(freeze, "--approver") == ctx.approver
    assert "gd-0001" in flag(freeze, "--reason") and PRD_SHA in flag(freeze, "--reason")
    state = read_state(ctx.state_dir, ctx.key)[1]
    assert state["current_state"] == "SPEC_FROZEN"
    assert state["frozen_stages"][-1]["stage"] == "Stage-1"
    assert not [v for v in verbs_of(popen_log) if v in ("gate", "spec-refreeze",
                                                       "resume-from-escalation")]


def test_AT_961_7_E_2_the_verb_counts_are_pinned(real_tree: Path, tmp_path: Path,
                                                popen_log: list[list[str]]) -> None:
    adopt.adopt_baseline(make_ctx(real_tree, tmp_path / "root"))
    verbs = verbs_of(popen_log)
    assert (verbs.count("show"), verbs.count("transition"), verbs.count("spec-frozen")) == (
        1, 5, 1)
    assert not {"gate", "spec-refreeze", "resume-from-escalation"} & set(verbs)


# ── AT-961-7-2 ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(("key", "prd_rel"), [
    ("agentconsole-demo", "docs/01_requirements/demo_PRD.md"),
    ("demo-app", "my-project/demo/01_specs/PRD-v1.0.0.md")])
def test_AT_961_7_2_the_adopted_digest_equals_the_outer_frozen_digest(
        real_tree: Path, tmp_path: Path, key: str, prd_rel: str) -> None:
    ctx = make_ctx(real_tree, tmp_path / "root", key=key, prd_rel=prd_rel)
    adopt.adopt_baseline(ctx)
    state = read_state(ctx.state_dir, ctx.key)[1]
    frozen = state["frozen_stages"][-1]
    digests = frozen.get("spec_doc_digests") or {}
    got = {k: str(v).removeprefix("sha256:") for k, v in digests.items()}
    assert got[prd_rel] == PRD_SHA
    assert not Path(prd_rel).is_absolute() and "\\" not in prd_rel, "--doc 須是相對 POSIX 路徑"


# ── AT-961-7-3 ─────────────────────────────────────────────────────────────────────────────
def impl_columns(renv: rgs.RouteEnv, rid: str) -> tuple[Any, Any]:
    row = renv.rdb.one("SELECT impl_fsm_project, impl_state_dir FROM "
                       "console.research_route_decisions WHERE research_id = %s", rid)
    assert row is not None
    return row[0], row[1]


def test_AT_961_7_3_the_impl_key_and_state_dir_are_written_after_the_key_exists(
        renv: rgs.RouteEnv) -> None:
    failed = rgs.seed_gate0(renv, "alpha")
    assert rgs.confirm(renv, failed, rgs.body_a(renv, base_ref="no-such-ref")).status_code == 502
    assert impl_columns(renv, failed) == (None, None), "失敗時兩欄為 NULL"
    a = rgs.seed_gate0(renv, "beta")
    assert rgs.confirm(renv, a, rgs.body_a(renv), n=2).status_code == 200
    key, state_dir = impl_columns(renv, a)
    assert key == "agentconsole-beta" and Path(state_dir).name == "fsm"
    assert Path(state_dir).parts[-3:] == ("build", "reports", "fsm")
    b = rgs.seed_gate0(renv, "gamma")
    assert rgs.confirm(renv, b, rgs.body_b(renv), n=3).status_code == 200
    key_b, dir_b = impl_columns(renv, b)
    assert key_b == "demo-app" and Path(dir_b) == renv.scaffold / "demo-app" / "build" / (
        "reports") / "fsm"
    for value in (key, key_b):
        assert not sdd_cli.is_outer_key(value)


# ── AT-961-7-4 ─────────────────────────────────────────────────────────────────────────────
def drive(ctx: adopt.AdoptCtx, upto: str) -> fsm_ops.FsmCtx:
    adopt.adopt_baseline(ctx, stage="init")
    fctx = fsm_ops.FsmCtx(sdd_root=ctx.sdd_root, state_dir=ctx.state_dir, key=ctx.key,
                          actor=ctx.approver)
    for target in adopt.ADOPTION_PATH[: adopt.ADOPTION_PATH.index(upto) + 1]:
        fsm_ops.transition(fctx, to=target, reason=adopt.adoption_reason(ctx))
    return fctx


def test_AT_961_7_4_a_resume_continues_from_the_current_state(
        real_tree: Path, tmp_path: Path, popen_log: list[list[str]]) -> None:
    ctx = make_ctx(real_tree, tmp_path / "mid")
    drive(ctx, "SCG_VALIDATION")
    popen_log.clear()
    adopt.adopt_baseline(ctx)
    calls = argvs(popen_log)
    assert [a[0] for a in calls] == ["transition", "spec-frozen"]
    assert flag(calls[0], "--to") == "HUMAN_PENDING"


def test_AT_961_7_4_an_already_adopted_key_is_an_idempotent_no_op(
        real_tree: Path, tmp_path: Path, popen_log: list[list[str]]) -> None:
    ctx = make_ctx(real_tree, tmp_path / "done")
    adopt.adopt_baseline(ctx)
    before = (ctx.state_dir / f"FSM-STATE-{ctx.key}.yaml").read_bytes()
    popen_log.clear()
    again = adopt.adopt_baseline(ctx)
    assert again["frozen"] is True and argvs(popen_log) == []
    assert (ctx.state_dir / f"FSM-STATE-{ctx.key}.yaml").read_bytes() == before


def test_AT_961_7_4_a_state_off_the_adoption_path_is_a_409_with_zero_writes(
        real_tree: Path, tmp_path: Path, popen_log: list[list[str]]) -> None:
    ctx = make_ctx(real_tree, tmp_path / "off")
    fctx = drive(ctx, "HUMAN_PENDING")
    fsm_ops.transition(fctx, to="SPEC_REGRESSION_CHECK", reason="regression check")
    popen_log.clear()
    before = (ctx.state_dir / f"FSM-STATE-{ctx.key}.yaml").read_bytes()
    with pytest.raises(ApiError) as caught:
        adopt.adopt_baseline(ctx)
    assert (caught.value.status_code, caught.value.body["reason"]) == (409, "fsm_state_conflict")
    assert caught.value.body["details"]["current_state"] == "SPEC_REGRESSION_CHECK"
    assert argvs(popen_log) == []
    assert (ctx.state_dir / f"FSM-STATE-{ctx.key}.yaml").read_bytes() == before


def test_AT_961_7_4_the_outer_key_is_refused_outright(real_tree: Path, tmp_path: Path) -> None:
    ctx = make_ctx(real_tree, tmp_path / "outer", key="research-demo")
    with pytest.raises(ValueError):
        adopt.adopt_baseline(ctx)


# ── AT-961-7-5 ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(("key", "reason", "ok"), [
    ("agentconsole-demo", "baseline adoption: x", True),
    ("agentconsole-demo", "Baseline adoption", False),
    ("agentconsole-demo", "adopt baseline", False),
    ("research-demo", "baseline adoption: x", False)])
def test_AT_961_7_5_human_pending_is_only_the_inner_key_baseline_adoption_path(
        key: str, reason: str, ok: bool) -> None:
    args = sdd_cli.research_transition_args(to="HUMAN_PENDING", reason=reason)
    if ok:
        sdd_cli.check_research_allowed("transition", args, key=key)
    else:
        with pytest.raises(ApiError) as caught:
            sdd_cli.check_research_allowed("transition", args, key=key)
        assert caught.value.body["reason"] == "sdd_cli_usage"
    assert sdd_cli.RESEARCH_VERBS == {"show", "transition", "gate", "spec-frozen",
                                      "spec-refreeze"}


def test_AT_961_7_5_route_py_never_composes_a_human_pending_transition() -> None:
    root = Path(adopt.__file__).parent
    assert "HUMAN_PENDING" not in (root / "route.py").read_text(encoding="utf-8")
    assert "HUMAN_PENDING" in (root / "adopt.py").read_text(encoding="utf-8")


# ── AT-961-7-6 ─────────────────────────────────────────────────────────────────────────────
def test_AT_961_7_6_the_fsm_environment_is_rebuilt_and_only_outer_keys_pin_recovery_off(
        real_tree: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRIDGE_X", "1")
    monkeypatch.setenv("SDD_Y", "1")
    monkeypatch.setenv("PYTHONPATH", "x")
    monkeypatch.setenv("GH_TOKEN", "t")
    inner = sdd_cli.build_research_env(os.environ, sdd_root=real_tree, state_dir=tmp_path,
                                       project="agentconsole-demo")
    outer = sdd_cli.build_research_env(os.environ, sdd_root=real_tree, state_dir=tmp_path,
                                       project="research-demo")
    for env in (inner, outer):
        # GH_TOKEN 的剝除屬 `sdd_cli._is_stripped_name`（不在 BR-D1 集合）：交卷「需主控處理」
        assert "BRIDGE_X" not in env and "SDD_Y" not in env
        assert env["PYTHONPATH"] == str(real_tree), "PYTHONPATH 重建為框架樹（不繼承 Bridge 的值）"
    assert outer[sdd_cli.RESEARCH_AUTO_RECOVERY_ENV] == "0"
    assert sdd_cli.RESEARCH_AUTO_RECOVERY_ENV not in inner


# ── AT-961-7-E-1 ───────────────────────────────────────────────────────────────────────────
def test_AT_961_7_E_1_the_outer_key_is_untouched_by_a_route(
        renv: rgs.RouteEnv, popen_log: list[list[str]]) -> None:
    rid = rgs.seed_gate0(renv)
    row = renv.env.db.get_project(rid)
    state_file = Path(row["fsm_state_dir"]) / f"FSM-STATE-{row['fsm_project']}.yaml"
    before = state_file.read_bytes()
    popen_log.clear()
    assert rgs.confirm(renv, rid, rgs.body_a(renv)).status_code == 200
    assert state_file.read_bytes() == before
    assert fsm_ops.current_state(rt.fsm_ctx_of(renv.env, rid)) == "SPEC_FROZEN"
    outer_calls = [a for a in argvs(popen_log) if "--project" in a
                   and flag(a, "--project") == row["fsm_project"]]
    assert all(a[0] == "show" for a in outer_calls), "對外環鍵只准唯讀的 show"
