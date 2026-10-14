"""入口消毒的 HTTP 行為：422 列出違規；被拒的請求不得留下任何 run 痕跡（NFR-SEC-03／SEC-04）。"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

from tests.conftest import TERMINAL, mock_playbook


def _violations(resp) -> list[dict]:
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["code"] == 422
    return body["violations"]


@pytest.mark.parametrize("cmd", ["pytest -q; rm -rf /", "pytest $(whoami)", "pytest `id`"])
def test_dangerous_evaluator_commands_are_rejected_with_the_offending_chars(
        bridge, run_body, cmd) -> None:
    playbook = mock_playbook()
    playbook["tasks"][1]["evaluator_command"] = cmd
    body = run_body(playbook=playbook)
    resp = bridge.post_run(body)
    violations = _violations(resp)
    assert resp.json()["reason"] == "sanitization_failed"
    assert len(violations) == 1
    bad = violations[0]
    assert (bad["step_id"], bad["rule"]) == ("T02", "deny_chars")
    assert bad["field"] == "playbook.tasks[1].evaluator_command"
    assert set(bad["chars"]) <= set("!`><~$&;")
    assert bad["chars"], "必須列出違規字元"
    assert bridge.client.get(f"/autoclaude/runs/{body['run_id']}").status_code == 404
    assert not (bridge.settings.engine_workspace / body["run_id"]).exists()


def test_every_violation_is_listed_at_once_not_just_the_first(bridge, run_body) -> None:
    playbook = mock_playbook()
    playbook["tasks"][0]["evaluator_command"] = "a; b"
    playbook["tasks"][2]["evaluator_command"] = "c $(d)"
    body = run_body(playbook=playbook)
    body["execution_path"] = "relative/path"
    rules = sorted((v["field"], v["rule"]) for v in _violations(bridge.post_run(body)))
    assert rules == [
        ("execution_path", "not_absolute"),
        ("playbook.tasks[0].evaluator_command", "deny_chars"),
        ("playbook.tasks[2].evaluator_command", "deny_chars"),
    ]


def test_execution_path_must_stay_inside_the_allowed_roots(bridge, run_body, tmp_path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    sneaky = f"{bridge.settings.engine_workspace}{os.sep}..{os.sep}outside"
    cases = {
        "outside_allowed_roots": str(outside),
        "contains_dotdot": sneaky,
        "not_found": str(tmp_path / "projects" / "nope"),
        "not_absolute": "projects/demo",
    }
    for rule, path in cases.items():
        resp = bridge.post_run(run_body(execution_path=Path(path)))
        assert [v["rule"] for v in _violations(resp)] == [rule], path


def test_a_symlink_that_escapes_the_root_is_rejected(bridge, run_body, tmp_path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "projects" / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("此環境無法建立 symlink（Windows 需開發人員模式或系統管理員）")
    resp = bridge.post_run(run_body(execution_path=link))
    assert [v["rule"] for v in _violations(resp)] == ["outside_allowed_roots"]


def test_schema_errors_are_422_in_the_same_envelope(bridge, run_body) -> None:
    body = run_body()
    body["playbook"]["tasks"][0]["unknown_field"] = 1
    body["playbook"]["tasks"].append(dict(body["playbook"]["tasks"][0], step_id="T01"))
    body["run_id"] = "not-a-uuid"
    resp = bridge.post_run(body)
    assert resp.json()["reason"] == "invalid_request"
    fields = {v["field"] for v in _violations(resp)}
    assert "run_id" in fields
    assert any("unknown_field" in f for f in fields), fields


def test_empty_playbooks_prompts_and_duplicate_step_ids_are_rejected(bridge, run_body) -> None:
    empty = run_body(playbook={**mock_playbook(), "tasks": []})
    assert _violations(bridge.post_run(empty))
    no_prompt = mock_playbook()
    no_prompt["tasks"][0]["prompt"] = ""
    assert _violations(bridge.post_run(run_body(playbook=no_prompt)))
    dupes = mock_playbook()
    dupes["tasks"][1]["step_id"] = "T01"
    resp = bridge.post_run(run_body(playbook=dupes))
    assert "step_id 重複" in str(_violations(resp))


def test_a_per_step_token_guard_typo_is_caught_by_the_engines_own_model(bridge, run_body) -> None:
    playbook = mock_playbook()
    playbook["tasks"][0]["token_guard"] = {"compact_threshold": 70}      # 漏了 _pct
    resp = bridge.post_run(run_body(playbook=playbook))
    assert "token_guard" in str(_violations(resp))


def test_bad_config_overrides_and_env_are_rejected(bridge, run_body) -> None:
    unknown = bridge.post_run(run_body(overrides={"claude": {"comand": "x"}}))
    assert [v["rule"] for v in _violations(unknown)] == ["unknown_key"]
    secret = bridge.post_run(run_body(overrides={"minimax": {"api_key": "sk-x"}}))
    assert [v["rule"] for v in _violations(secret)] == ["secret_in_config"]
    dsn = bridge.post_run(run_body(overrides={"storage": {"db_dsn": "postgresql://u:p@h/db"}}))
    assert [v["rule"] for v in _violations(dsn)] == ["secret_in_config"]
    loader = bridge.post_run(run_body(env={"LD_PRELOAD": "/x.so"}))
    assert [v["rule"] for v in _violations(loader)] == ["forbidden_name"]
    invariant = bridge.post_run(run_body(
        overrides={"token_guard": {"compact_threshold_pct": 95, "halt_threshold_pct": 90}}))
    assert _violations(invariant)[0]["rule"] == "invalid_value"


def test_a_duplicate_run_id_is_409(bridge, run_body) -> None:
    body = run_body(delay="0.1")
    assert bridge.post_run(body).status_code == 201
    bridge.wait_status(body["run_id"], {"COMPLETED"})
    again = bridge.post_run(body)
    assert (again.status_code, again.json()["reason"]) == (409, "run_exists")
    assert uuid.UUID(again.json()["run_id"]) == uuid.UUID(body["run_id"])


# ── 外呼白名單（NFR-SEC-04）──────────────────────────────────────────────────
def test_an_evil_brain_url_is_refused_and_a_localhost_mock_brain_is_allowed(
        bridge, run_body) -> None:
    evil = run_body(overrides={"minimax": {"base_url": "http://evil.example/v1/chat"}})
    resp = bridge.post_run(evil)
    violation = _violations(resp)[0]
    assert violation["rule"] == "outbound_not_allowed"
    assert violation["host"] == "evil.example"
    audit = (bridge.settings.engine_workspace / "_audit.jsonl").read_text(encoding="utf-8")
    assert "outbound_denied" in audit
    assert "evil.example" in audit

    ok = run_body(delay="0.1",
                  overrides={"minimax": {"base_url": "http://localhost:9100/v1/chat/completions"}})
    created = bridge.post_run(ok)
    assert created.status_code == 201, created.text
    bridge.wait_status(ok["run_id"], TERMINAL)


def test_the_env_route_cannot_bypass_the_allowlist(bridge, run_body) -> None:
    # 引擎的優先序是 env MINIMAX_BASE_URL > config：只擋 config 會被 env 繞過。
    resp = bridge.post_run(run_body(env={"MINIMAX_BASE_URL": "http://evil.example/"}))
    assert _violations(resp)[0]["field"] == "env.MINIMAX_BASE_URL"


def test_default_deny_applies_even_when_the_default_url_is_what_would_be_used(
        make_bridge, settings, run_body) -> None:
    from dataclasses import replace

    strict = replace(settings, outbound_allowlist=("localhost",))
    live = make_bridge(strict)
    with_key = run_body(env={"MINIMAX_API_KEY": "sk-test"})
    resp = live.post_run(with_key)
    assert _violations(resp)[0]["field"] == "effective.minimax.base_url"
    # 沒有金鑰＝引擎不會呼叫 Brain，不需要外呼：照常放行。
    assert live.post_run(run_body(delay="0.1")).status_code == 201

