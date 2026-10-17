"""BR-30／BR-31（建立面）：含 `sdd` 區塊的 `POST /autoclaude/runs`——預檢順序、FSM 寫入順序、補償、
環境剝除。

真引擎＋mock claude＋假 SDD 樹（tests/sdd_run_support.py）。ADR-XPLAT-016 §6.3③、§7.3、§9、§10.2；
契約 v1.5 §3.1.6。每個「被拒」的案例都斷言**零副作用**：沒有 FSM 呼叫、沒有 run 目錄、鎖已釋放
（同一個 run_id 隨後可以成功建立）。終態同步、回收點、`resume`／`restore` 在
test_sdd_run_lifecycle.py。
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.runner import RunManager
from tests.conftest import TERMINAL, read_trace
from tests.fake_sdd import read_calls, seed_state, set_control
from tests.sdd_run_support import (
    FSM_REL,
    TCS_NAME,
    TCS_REL,
    TCS_TEXT,
    TOKEN,
    argv_of,
    audit_entries,
    contracts_dir,
    digest_of,
    events_of,
    flag,
    fsm_state,
    make_playbook,
    post,
    sdd_block,
    sdd_body,
    seed_frozen,
    verbs,
    wait_fsm,
    wait_sync,
    workspace_has,
)


def _clean(live, fake: Path, body: dict[str, Any]) -> None:
    """被拒請求的零副作用斷言：沒有 FSM 呼叫、沒有 run 目錄、也不認得這個 run。"""
    assert read_calls(fake) == [], "被拒的請求不得動 FSM"
    assert not workspace_has(live, body["run_id"]), "被拒的請求不得留下 run 目錄"
    assert live.client.get(f"/autoclaude/runs/{body['run_id']}").status_code == 404


# ── 成功路徑：首次批次（SPEC_FROZEN）走完談判與委派，終態交還控制權 ─────────────────────────────
def test_the_first_batch_negotiates_delegates_runs_and_hands_control_back(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body, monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path) -> None:
    seed_frozen(sdd_proj, "SPEC_FROZEN")
    # 開發機先在 SDD session 匯出、再起 Bridge 是常態：這些值不得走進引擎子行程（F-7）。
    monkeypatch.setenv("BRIDGE_SDD_WRITE_TOKEN", TOKEN)
    monkeypatch.setenv("SDD_STATE_DIR", str(tmp_path / "leaked-state-dir"))
    monkeypatch.setenv("SDD_PROJECT", "leaked-from-the-bridge-environment")
    trace = tmp_path / "trace.jsonl"
    body = sdd_body(run_body, sdd_proj, delay="1.2", env={"MOCK_CLAUDE_TRACE": str(trace)})
    resp = post(sdd_live, body, trace="run-trace-1")
    assert resp.status_code == 201, resp.text
    assert resp.json()["warnings"] == [], "摘要已驗證：沒有要出聲的事"
    rid = resp.json()["run_id"]

    seen: set[str] = set()
    while sdd_live.get_run(rid)["status"] not in TERMINAL:            # 執行中 FSM 是委派態（C4）
        seen.add(fsm_state(sdd_proj)["current_state"])
        time.sleep(0.1)
    assert "AUTOCLAUDE_DELEGATED" in seen
    assert sdd_live.get_run(rid)["status"] == "COMPLETED"
    final = wait_fsm(sdd_proj, "IMPLEMENTATION")                      # 終態同步在終態事件之後

    assert verbs(sdd_fake) == [
        "negotiate-enter", "negotiate-exit", "delegate-enter", "delegate-exit"]
    ref = f"run:{rid}"
    enter = argv_of(sdd_fake, "negotiate-enter")
    exit_negotiate = argv_of(sdd_fake, "negotiate-exit")
    assert flag(enter, "--reason") == f"console-signoff approver=operator; run={rid}"
    assert flag(enter, "--contract-ref") == TCS_REL
    assert flag(exit_negotiate, "--outcome") == "agreed"
    assert flag(exit_negotiate, "--reason") == (
        f"console-signoff approver=operator; oracle={TCS_REL}@{digest_of(TCS_TEXT)}; "
        "basis=import-draft-signoff; r9.20.3=not-satisfied")
    delegate = argv_of(sdd_fake, "delegate-enter")
    assert flag(delegate, "--reason") == f"console-run run={rid} START"
    assert flag(delegate, "--playbook-ref") == ref, "`run:<run_id>`：回收只認 Bridge 簽發的值"
    leave = argv_of(sdd_fake, "delegate-exit")
    assert (flag(leave, "--decision"), flag(leave, "--reason")) == (
        "done", f"console-run run={rid} COMPLETED")
    assert all(a[:4] == [a[0], "--project", "alpha", "--must-exist"]
               for a in (argv_of(sdd_fake, v) for v in set(verbs(sdd_fake))))

    hops = [(t["from"], t["to"]) for t in final["decision_trace"]]
    assert hops == [("SPEC_FROZEN", "TEST_CONTRACT_NEGOTIATED"),
                    ("TEST_CONTRACT_NEGOTIATED", "IMPLEMENTATION"),
                    ("IMPLEMENTATION", "AUTOCLAUDE_DELEGATED"),
                    ("AUTOCLAUDE_DELEGATED", "IMPLEMENTATION")]
    assert final["autoclaude_delegated_tracking"]["playbook_ref"] == ref

    record = wait_sync(Path(resp.json()["workspace"]))      # sync 在 FSM 回寫之後才 persist
    assert record["sdd"]["fsm_project"] == "alpha" and record["sdd"]["approver"] == "operator"
    assert record["sdd"]["sync"]["exit"] == "done" and record["sdd"]["sync"]["ok"] is True
    assert "MOCK_CLAUDE_TRACE" in record["env_keys"]
    assert not {"BRIDGE_SDD_WRITE_TOKEN", "SDD_PROJECT", "SDD_STATE_DIR"} & set(record["env_keys"])

    # 引擎子行程（mock claude 繼承它的環境）：只有 SDD_PROJECT＝本批次的鍵；沒有狀態目錄指標、
    # 沒有權杖
    probes = [r["sdd_env"] for r in read_trace(trace) if r["keywords"]]
    assert probes and all(p == {"SDD_PROJECT": "alpha", "SDD_STATE_DIR": None,
                                "has_write_token": False} for p in probes), probes


def test_the_playbook_is_stamped_with_the_server_side_governance_fields(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    """外部契約 `PlaybookIn.workflow_type` 只收 `auto`；有 `sdd` 區塊時由 Bridge **伺服端**覆寫成
    `aisdlc_sdd`＋已驗證的 `workflow_path`（D-115-06）。引擎的 PRE_RUN 因此真的載入規格。"""
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    resp = post(sdd_live, sdd_body(run_body, sdd_proj, delay="0.1"))
    assert resp.status_code == 201, resp.text
    workspace = Path(resp.json()["workspace"])
    sdd_live.wait_status(resp.json()["run_id"], TERMINAL)
    playbook = yaml.safe_load((workspace / "playbook.yaml").read_text(encoding="utf-8"))
    assert playbook["workflow_type"] == "aisdlc_sdd"
    assert Path(playbook["workflow_path"]) == contracts_dir(sdd_proj).resolve()
    assert all(t["spec_digest"] == digest_of(TCS_TEXT) for t in playbook["tasks"])


def test_a_spec_file_makes_the_workflow_path_the_file_itself(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    body = sdd_body(run_body, sdd_proj, sdd=sdd_block(sdd_proj, spec_file=TCS_NAME), delay="0.1")
    resp = post(sdd_live, body)
    assert resp.status_code == 201, resp.text
    rid = resp.json()["run_id"]
    assert sdd_live.wait_status(rid, TERMINAL)["status"] == "COMPLETED"
    playbook = yaml.safe_load(
        (Path(resp.json()["workspace"]) / "playbook.yaml").read_text(encoding="utf-8"))
    assert Path(playbook["workflow_path"]) == (contracts_dir(sdd_proj) / TCS_NAME).resolve()
    record = json.loads((Path(resp.json()["workspace"]) / "run.json").read_text("utf-8"))
    assert Path(record["sdd"]["spec_file"]) == (contracts_dir(sdd_proj) / TCS_NAME).resolve()


def test_a_non_sdd_run_is_exactly_v14_no_token_no_fsm_no_governance(
        sdd_live, sdd_fake: Path, run_body) -> None:
    """相容：沒有 `sdd` 區塊的請求不需要權杖（連錯的標頭也不看）、不碰 FSM、201 的 warnings 恆為
    空。"""
    resp = post(sdd_live, run_body(delay="0.1"), token="not-the-token")
    assert resp.status_code == 201, resp.text
    assert resp.json()["warnings"] == []
    assert sdd_live.wait_status(resp.json()["run_id"], TERMINAL)["status"] == "COMPLETED"
    assert read_calls(sdd_fake) == []
    playbook = yaml.safe_load(
        (Path(resp.json()["workspace"]) / "playbook.yaml").read_text(encoding="utf-8"))
    assert playbook.get("workflow_type") == "auto" and "workflow_path" not in playbook
    record = json.loads((Path(resp.json()["workspace"]) / "run.json").read_text("utf-8"))
    assert record["sdd"] is None


# ── 預檢表（§10.2）：每一列 FSM 現況對應的動詞序列 ────────────────────────────────────────────
@pytest.mark.parametrize(("state", "expected"), [
    ("IMPLEMENTATION", ["delegate-enter", "delegate-exit"]),
    ("TEST_CONTRACT_NEGOTIATED", ["negotiate-exit", "delegate-enter", "delegate-exit"]),
])
def test_the_preflight_table_rows(state: str, expected: list[str], sdd_live, sdd_fake: Path,
                                  sdd_proj: Path, run_body) -> None:
    seed_frozen(sdd_proj, state)
    resp = post(sdd_live, sdd_body(run_body, sdd_proj, delay="0.1"))
    assert resp.status_code == 201, resp.text
    sdd_live.wait_status(resp.json()["run_id"], TERMINAL)
    wait_fsm(sdd_proj, "IMPLEMENTATION")
    assert verbs(sdd_fake) == expected


@pytest.mark.parametrize("state", ["ESCALATION", "ESCALATION_FINAL", "HUMAN_PENDING", "PR_REVIEW",
                                   "SPEC_DRAFTING"])
def test_any_other_state_is_409_with_zero_side_effects(
        state: str, sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    """凍結過（frozen_stages 非空，adapter 的凍結閘放行）但 FSM 現況不是能開批次的狀態。
    ESCALATION 的出路在 SDD session 的 `resume-from-escalation`（Console 與 Bridge 沒有恢復動
    詞）。"""
    seed_frozen(sdd_proj, state)
    body = sdd_body(run_body, sdd_proj)
    resp = post(sdd_live, body)
    assert (resp.status_code, resp.json()["reason"]) == (409, "fsm_state_conflict")
    assert resp.json()["current_state"] == state
    assert resp.json()["expected_state"] == ["IMPLEMENTATION", "SPEC_FROZEN"]
    assert resp.json()["detail"]["current_state"] == state
    _clean(sdd_live, sdd_fake, body)
    seed_frozen(sdd_proj, "IMPLEMENTATION")                            # 鎖與 run_id 都沒被占用
    assert post(sdd_live, body).status_code == 201


def test_an_unfrozen_spec_is_422_before_the_fsm_state_is_even_looked_at(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    """預檢順序：規格與凍結（3）先於 FSM 狀態（5）。沒凍結過（frozen_stages 空、狀態也沒過
    SPEC_FROZEN）是 422 `spec_not_frozen`，不是 409；沒有狀態檔也是（adapter 找不到狀態檔＝未凍
    結）。"""
    seed_state(sdd_proj / FSM_REL, "alpha", "SPEC_DRAFTING")
    body = sdd_body(run_body, sdd_proj)
    resp = post(sdd_live, body)
    assert (resp.status_code, resp.json()["reason"]) == (422, "spec_not_frozen")
    _clean(sdd_live, sdd_fake, body)
    (sdd_proj / FSM_REL / "FSM-STATE-alpha.yaml").unlink()
    body = sdd_body(run_body, sdd_proj)
    assert post(sdd_live, body).json()["reason"] == "spec_not_frozen"
    _clean(sdd_live, sdd_fake, body)


def test_a_state_file_missing_where_the_bridge_looks_is_404_not_created(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body, tmp_path: Path) -> None:
    """Bridge 不 init 狀態檔（`--must-exist`）。adapter 沿祖先鏈找到子目錄裡的狀態檔、而
    `sdd.root` 底下沒有時（版面不一致），Bridge 回 404 `fsm_not_found`，也不替它建檔。"""
    nested = sdd_proj / "sub"
    (nested / "docs").mkdir(parents=True)
    (nested / "docs" / TCS_NAME).write_text(TCS_TEXT, encoding="utf-8", newline="")
    seed_frozen(nested, "IMPLEMENTATION", digests=False)               # 狀態在 <proj>/sub/build/…
    body = sdd_body(run_body, sdd_proj,
                    # root＝<proj>（底下沒有狀態）
                    sdd=sdd_block(sdd_proj, spec_dir=nested / "docs"))
    resp = post(sdd_live, body)
    assert (resp.status_code, resp.json()["reason"], resp.json()["project"]) == (
        404, "fsm_not_found", "alpha")
    _clean(sdd_live, sdd_fake, body)
    assert not (sdd_proj / FSM_REL).exists(), "沒有替不存在的專案建狀態檔"


# ── 三點摘要（§6.3③）：凍結時＝匯入時＝執行前 ────────────────────────────────────────────────
def test_tasks_without_an_import_digest_are_a_backend_bug_422(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    body = sdd_body(run_body, sdd_proj)
    body["playbook"] = make_playbook(None)
    resp = post(sdd_live, body)
    assert (resp.status_code, resp.json()["reason"]) == (422, "sdd_block_invalid")
    _clean(sdd_live, sdd_fake, body)
    body = sdd_body(run_body, sdd_proj)
    del body["playbook"]["tasks"][1]["spec_digest"]                    # 只有部分任務缺
    assert post(sdd_live, body).json()["reason"] == "sdd_block_invalid"


def test_a_stale_import_digest_is_409_naming_both_digests(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    stale = digest_of("# 匯入時的舊版規格\n")
    body = sdd_body(run_body, sdd_proj, digest=stale)
    resp = post(sdd_live, body)
    assert (resp.status_code, resp.json()["reason"]) == (409, "spec_digest_changed")
    got = resp.json()
    assert got["pair"] == "import_vs_file" and got["doc"] == TCS_REL
    assert got["import_digest"] == stale and got["current_digest"] == digest_of(TCS_TEXT)
    assert got["frozen_digest"] == digest_of(TCS_TEXT), "凍結摘要取自狀態檔，一併帶回"
    assert got["detail"]["pair"] == "import_vs_file"
    _clean(sdd_live, sdd_fake, body)


def test_a_spec_edited_after_the_freeze_is_409_frozen_vs_file_and_nothing_starts(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    """凍結後改檔（G-06）：adapter 的 `SpecDigestMismatchError`（`SpecNotFrozenError` 子類，必須先
    接）→ 409 `spec_digest_changed`，不是 422。有 `spec_file` 時回應補上 doc 與兩個摘要。"""
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    edited = TCS_TEXT + "\n<!-- 凍結後被改 -->\n"
    (contracts_dir(sdd_proj) / TCS_NAME).write_text(edited, encoding="utf-8", newline="")
    body = sdd_body(run_body, sdd_proj, digest=digest_of(edited),
                    sdd=sdd_block(sdd_proj, spec_file=TCS_NAME))
    resp = post(sdd_live, body)
    assert (resp.status_code, resp.json()["reason"]) == (409, "spec_digest_changed")
    got = resp.json()
    assert got["pair"] == "frozen_vs_file" and got["doc"] == TCS_REL
    assert got["frozen_digest"] == digest_of(TCS_TEXT)
    assert got["current_digest"] == digest_of(edited)
    _clean(sdd_live, sdd_fake, body)
    (contracts_dir(sdd_proj) / TCS_NAME).write_text(TCS_TEXT, encoding="utf-8", newline="")
    assert post(sdd_live, sdd_body(run_body, sdd_proj, sdd=sdd_block(sdd_proj, spec_file=TCS_NAME)
                                   )).status_code == 201, "還原內容後同一個請求通過"


def test_a_missing_frozen_digest_is_allowed_but_never_silent(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body, tmp_path: Path) -> None:
    """舊狀態檔（凍結時沒帶 --digest）：維持放行，只比對「匯入時＝現檔」；出聲的管道是 201 的
    `warnings[]`（`sdd_frozen_digest_absent`）。契約 v1.5 附錄決議 #11 捨棄了 run alert
    `SDD_FROZEN_DIGEST_MISSING`（改由 warnings 承擔），所以 run 的事件流裡不得出現它。"""
    seed_frozen(sdd_proj, "IMPLEMENTATION", digests=False)
    resp = post(sdd_live, sdd_body(run_body, sdd_proj, delay="0.1"))
    assert resp.status_code == 201, resp.text
    assert [w["code"] for w in resp.json()["warnings"]] == ["sdd_frozen_digest_absent"]
    rid = resp.json()["run_id"]
    sdd_live.wait_status(rid, TERMINAL)
    assert [a["code"] for a in events_of(sdd_live, rid, "alert")] == []


# ── 路徑閘與清理（§7.3、§4.4）：零副作用 ──────────────────────────────────────────────────────
@pytest.mark.parametrize(("sdd_edit", "reason", "field"), [
    ({"root": "OUTSIDE"}, "sanitization_failed", "sdd.root"),
    ({"spec_dir": "OUTSIDE"}, "sanitization_failed", "sdd.spec_dir"),
    ({"spec_file": "../escape.md"}, "sanitization_failed", "sdd.spec_file"),
    ({"spec_file": "notes.txt"}, "sanitization_failed", "sdd.spec_file"),
    ({"fsm_project": "   "}, "sanitization_failed", "sdd.fsm_project"),
    ({"root": "relative/path"}, "sanitization_failed", "sdd.root"),
])
def test_the_path_gate_rejects_with_the_sdd_field_name(
        sdd_edit: dict, reason: str, field: str, sdd_live, sdd_fake: Path, sdd_proj: Path,
        run_body, tmp_path: Path) -> None:
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    (contracts_dir(sdd_proj) / "notes.txt").write_text("not markdown", encoding="utf-8")
    (tmp_path / "not-allowed").mkdir()
    block = sdd_block(sdd_proj)
    block.update({k: (str(tmp_path / "not-allowed") if v == "OUTSIDE" else v)
                  for k, v in sdd_edit.items()})
    body = sdd_body(run_body, sdd_proj, sdd=block)
    resp = post(sdd_live, body)
    assert (resp.status_code, resp.json()["reason"]) == (422, reason)
    assert field in [v["field"] for v in resp.json()["violations"]]
    _clean(sdd_live, sdd_fake, body)


def test_a_missing_spec_file_is_spec_not_found_like_sdd_compile(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    """契約 §3.1.6：`sdd.spec_file` 的其餘規則同 `/sdd/compile`（§3.1.4 (e)）——檔不存在是 422
    `spec_not_found`（匯入後規格檔被刪是真實情形，訊息要指向「找不到規格」，不是路徑形狀不合）；
    路徑形狀不合（`..`、非 .md）仍是 `sanitization_failed`（上面那張表）。零副作用。"""
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    body = sdd_body(run_body, sdd_proj, sdd=sdd_block(sdd_proj, spec_file="nope.md"))
    resp = post(sdd_live, body)
    assert (resp.status_code, resp.json()["reason"]) == (422, "spec_not_found")
    assert "nope.md" in resp.json()["detail"]
    _clean(sdd_live, sdd_fake, body)


def test_a_spec_dir_outside_the_sdd_root_is_sdd_block_invalid(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body, tmp_path: Path) -> None:
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    other = tmp_path / "projects" / "other"
    other.mkdir()
    body = sdd_body(run_body, sdd_proj, sdd=sdd_block(sdd_proj, spec_dir=other))
    resp = post(sdd_live, body)
    assert (resp.status_code, resp.json()["reason"]) == (422, "sdd_block_invalid")
    _clean(sdd_live, sdd_fake, body)


@pytest.mark.parametrize("approver", ["a;b", "x" * 101, "bad\nname", " lead", "  "])
def test_a_bad_approver_is_422_sdd_invalid_argument(
        approver: str, sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    body = sdd_body(run_body, sdd_proj, sdd=sdd_block(sdd_proj, approver=approver))
    resp = post(sdd_live, body)
    assert (resp.status_code, resp.json()["reason"], resp.json()["field"]) == (
        422, "sdd_invalid_argument", "approver")
    _clean(sdd_live, sdd_fake, body)


def test_an_omitted_approver_is_recorded_as_the_service_identity(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    seed_frozen(sdd_proj, "SPEC_FROZEN")
    body = sdd_body(run_body, sdd_proj, sdd=sdd_block(sdd_proj, approver=None), delay="0.1")
    assert post(sdd_live, body).status_code == 201
    assert flag(argv_of(sdd_fake, "negotiate-enter"), "--reason").startswith(
        "console-signoff approver=console; run=")


def test_the_sdd_root_defaults_to_the_execution_path(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    body = sdd_body(run_body, sdd_proj, sdd=sdd_block(sdd_proj, with_root=False), delay="0.1")
    resp = post(sdd_live, body)
    assert resp.status_code == 201, resp.text
    record = json.loads((Path(resp.json()["workspace"]) / "run.json").read_text("utf-8"))
    assert Path(record["sdd"]["root"]) == sdd_proj.resolve()
    assert Path(record["sdd"]["state_dir"]) == (sdd_proj / FSM_REL).resolve()


def test_the_fsm_project_is_sanitized_once_and_used_everywhere(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body, tmp_path: Path) -> None:
    """原名 `Order: Sys` → 檔名鍵 `Order_ Sys`：狀態檔、CLI 的 `--project`、`SDD_PROJECT`、run 記
    錄全是同一個鍵。"""
    seed_frozen(sdd_proj, "IMPLEMENTATION", key="Order_ Sys")
    trace = tmp_path / "trace.jsonl"
    body = sdd_body(run_body, sdd_proj, sdd=sdd_block(sdd_proj, key="Order: Sys"), delay="0.1",
                    env={"MOCK_CLAUDE_TRACE": str(trace)})
    resp = post(sdd_live, body)
    assert resp.status_code == 201, resp.text
    sdd_live.wait_status(resp.json()["run_id"], TERMINAL)
    assert argv_of(sdd_fake, "delegate-enter")[:3] == ["delegate-enter", "--project", "Order_ Sys"]
    record = json.loads((Path(resp.json()["workspace"]) / "run.json").read_text("utf-8"))
    assert record["sdd"]["fsm_project"] == "Order_ Sys"
    projects = {r["sdd_env"]["SDD_PROJECT"] for r in read_trace(trace) if r["keywords"]}
    assert projects == {"Order_ Sys"}


@pytest.mark.parametrize("name", ["SDD_PROJECT", "SDD_STATE_DIR", "BRIDGE_SDD_WRITE_TOKEN",
                                  "sdd_project"])
def test_request_env_cannot_set_the_sdd_write_surface_names(
        name: str, sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    body = sdd_body(run_body, sdd_proj, env={name: "x"})
    resp = post(sdd_live, body)
    assert (resp.status_code, resp.json()["reason"]) == (422, "sanitization_failed")
    assert resp.json()["violations"][0]["rule"] == "forbidden_name"
    _clean(sdd_live, sdd_fake, body)


# ── 權杖（§9）：含 `sdd` 的請求才要；先於一切預檢 ─────────────────────────────────────────────
def test_a_bridge_without_a_token_refuses_sdd_runs_but_not_ordinary_ones(
        make_bridge, settings, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    disabled = make_bridge(replace(settings, sdd_root=sdd_fake, sdd_write_token=None))
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    body = sdd_body(run_body, sdd_proj)
    for header in (None, "", TOKEN):
        resp = post(disabled, body, token=header)
        assert (resp.status_code, resp.json()["reason"]) == (503, "sdd_write_disabled"), header
    _clean(disabled, sdd_fake, body)
    assert post(disabled, run_body(delay="0.1")).status_code == 201, "不含 sdd 的 run 照舊（相容）"


@pytest.mark.parametrize("header", [None, "", "wrong", TOKEN[:-1], TOKEN + "x"])
def test_a_missing_or_wrong_token_is_403_before_any_precheck(
        header: str | None, sdd_live, sdd_fake: Path, sdd_proj: Path, run_body,
        tmp_path: Path) -> None:
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    body = sdd_body(run_body, sdd_proj)
    resp = post(sdd_live, body, token=header)
    assert (resp.status_code, resp.json()) == (403, {"code": 403, "reason": "sdd_write_forbidden"})
    _clean(sdd_live, sdd_fake, body)
    bad_path = sdd_body(run_body, sdd_proj, sdd=sdd_block(sdd_proj, spec_dir=tmp_path / "nowhere"))
    assert post(sdd_live, bad_path, token=header).status_code == 403, \
        "壞路徑帶錯權杖也是 403：權杖檢查先於一切會碰檔案系統的檢查"
    assert read_calls(sdd_fake) == []
    assert TOKEN not in json.dumps(audit_entries(sdd_live))


def test_a_malformed_sdd_block_is_422_invalid_request_even_without_a_token(
        sdd_live, sdd_proj: Path, run_body) -> None:
    body = sdd_body(run_body, sdd_proj)
    del body["sdd"]["fsm_project"]
    resp = post(sdd_live, body, token=None)
    assert (resp.status_code, resp.json()["reason"]) == (422, "invalid_request")
    body = sdd_body(run_body, sdd_proj)
    body["sdd"]["surprise"] = 1
    assert post(sdd_live, body, token=None).json()["reason"] == "invalid_request"


# ── 原子性：FSM 寫入失敗時不留半成品；補償 ────────────────────────────────────────────────────
def test_a_failing_delegate_enter_leaves_no_run_and_the_retry_is_safe(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    """FSM 寫入在 `_materialize` 之前：失敗時沒有 run 目錄（否則 reconcile 下次啟動會把它當孤兒標成
    FAILED、憑空多一筆假紀錄）。首次批次的談判已完成而 enter 失敗＝FSM 停在 IMPLEMENTATION，重試安
    全。"""
    seed_frozen(sdd_proj, "SPEC_FROZEN")
    set_control(sdd_fake, rc={"delegate-enter": 1})
    body = sdd_body(run_body, sdd_proj, delay="0.1")
    resp = post(sdd_live, body)
    assert (resp.status_code, resp.json()["reason"]) == (502, "sdd_cli_failed")
    assert verbs(sdd_fake) == ["negotiate-enter", "negotiate-exit", "delegate-enter"]
    assert fsm_state(sdd_proj)["current_state"] == "IMPLEMENTATION"
    assert not workspace_has(sdd_live, body["run_id"])
    assert not list(sdd_live.settings.engine_workspace.glob("*/run.json")), "沒有任何 run.json"
    set_control(sdd_fake)
    resp = post(sdd_live, body)                                       # 同一個 run_id、同一個請求
    assert resp.status_code == 201, resp.text
    sdd_live.wait_status(body["run_id"], TERMINAL)
    wait_fsm(sdd_proj, "IMPLEMENTATION")                              # 終態同步在終態事件之後
    assert verbs(sdd_fake)[3:] == ["delegate-enter", "delegate-exit"], "第二次不再談判"


def test_a_conflict_between_precheck_and_write_is_caught_under_the_state_lock(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body,
        monkeypatch: pytest.MonkeyPatch) -> None:
    """預檢讀到 IMPLEMENTATION、但在取得鎖之前有人把 FSM 推走了（TOCTOU）：寫入前會在
    `state_guard` 內重讀重判，所以得到 409 而不是對錯的狀態硬寫。"""
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    real_precheck = RunManager._sdd_precheck

    def precheck_then_race(self, req, run_id, exec_path):
        check = real_precheck(self, req, run_id, exec_path)
        seed_frozen(sdd_proj, "ESCALATION")                            # 預檢之後、寫入之前
        return check

    monkeypatch.setattr(RunManager, "_sdd_precheck", precheck_then_race)
    body = sdd_body(run_body, sdd_proj)
    resp = post(sdd_live, body)
    assert (resp.status_code, resp.json()["reason"], resp.json()["current_state"]) == (
        409, "fsm_state_conflict", "ESCALATION")
    _clean(sdd_live, sdd_fake, body)
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    monkeypatch.undo()
    assert post(sdd_live, body).status_code == 201, "鎖已釋放、run_id 沒被占用"


def test_a_spawn_failure_exits_the_delegation_with_done_never_failed(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body,
        monkeypatch: pytest.MonkeyPatch) -> None:
    """補償：`delegate-enter` 已做、引擎從未啟動。以 `done` 離開（回 IMPLEMENTATION＝沒有進行中的
    委派）；
    🔴 不得用 `failed`——那會進阻塞態 ESCALATION，不可把基礎設施故障映成它。回應照舊是 500
    `spawn_failed`。"""
    seed_frozen(sdd_proj, "SPEC_FROZEN")
    real_popen = subprocess.Popen

    def popen(argv, *args, **kwargs):
        if isinstance(argv, list) and "autoclaude" in argv:           # 只讓引擎的 spawn 失敗
            raise OSError("simulated spawn failure")
        return real_popen(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", popen)
    body = sdd_body(run_body, sdd_proj)
    resp = sdd_live.post_on_fresh_connection(
        "/autoclaude/runs", json=body, headers={"X-Bridge-Token": TOKEN})
    assert (resp.status_code, resp.json()["reason"]) == (500, "spawn_failed")
    assert verbs(sdd_fake) == [
        "negotiate-enter", "negotiate-exit", "delegate-enter", "delegate-exit"]
    leave = argv_of(sdd_fake, "delegate-exit")
    assert (flag(leave, "--decision"), flag(leave, "--reason")) == (
        "done", f"console-run run={body['run_id']} SPAWN-FAILED delegation not started")
    state = fsm_state(sdd_proj)
    assert state["current_state"] == "IMPLEMENTATION" and not state["escalation_history"]
    run = sdd_live.get_run(body["run_id"])
    assert run["status"] == "FAILED" and "無法啟動引擎" in run["reason"]
    record = wait_sync(sdd_live.settings.engine_workspace / body["run_id"])
    assert record["sdd"]["sync"]["exit"] == "done" and record["sdd"]["sync"]["ok"] is True
    monkeypatch.undo()
    body["run_id"] = "00000000-0000-4000-8000-0000000000aa"
    assert post(sdd_live, body).status_code == 201, "鎖已釋放：同專案同路徑可再開"


def test_a_materialize_failure_after_the_enter_is_compensated(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body,
        monkeypatch: pytest.MonkeyPatch) -> None:
    seed_frozen(sdd_proj, "IMPLEMENTATION")

    def boom(self, *args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(RunManager, "_materialize", boom)
    body = sdd_body(run_body, sdd_proj)
    resp = sdd_live.post_on_fresh_connection(
        "/autoclaude/runs", json=body, headers={"X-Bridge-Token": TOKEN})
    assert resp.status_code == 500
    assert verbs(sdd_fake) == ["delegate-enter", "delegate-exit"]
    assert "SPAWN-FAILED" in flag(argv_of(sdd_fake, "delegate-exit"), "--reason")
    assert fsm_state(sdd_proj)["current_state"] == "IMPLEMENTATION"
    monkeypatch.undo()
    assert post(sdd_live, body).status_code == 201, "鎖已釋放、run_id 沒被占用"


def test_a_failing_compensation_does_not_change_the_callers_error(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body,
        monkeypatch: pytest.MonkeyPatch) -> None:
    """補償本身失敗只記 ERROR 與稽核，不改變對呼叫端的錯誤回應（仍是 `spawn_failed`）。"""
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    set_control(sdd_fake, rc={"delegate-exit": 1})
    real_popen = subprocess.Popen

    def popen(argv, *args, **kwargs):
        if isinstance(argv, list) and "autoclaude" in argv:
            raise OSError("simulated spawn failure")
        return real_popen(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", popen)
    body = sdd_body(run_body, sdd_proj)
    resp = sdd_live.post_on_fresh_connection(
        "/autoclaude/runs", json=body, headers={"X-Bridge-Token": TOKEN})
    assert (resp.status_code, resp.json()["reason"]) == (500, "spawn_failed")
    assert fsm_state(sdd_proj)["current_state"] == "AUTOCLAUDE_DELEGATED", "補償失敗：FSM 留在原態"
    record = wait_sync(sdd_live.settings.engine_workspace / body["run_id"])
    assert record["sdd"]["sync"]["ok"] is False
    alerts = events_of(sdd_live, body["run_id"], "alert")
    assert "SDD_FSM_SYNC_FAILED" in [a["code"] for a in alerts]


# ── 稽核（§9）：請求層決策與 CLI 層呼叫以 trace_id 對得上；絕不記權杖 ───────────────────────────
def test_a_run_request_is_audited_as_a_decision_without_the_token(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    resp = post(sdd_live, sdd_body(run_body, sdd_proj, delay="0.1"), trace="run-audit-9")
    rid = resp.json()["run_id"]
    sdd_live.wait_status(rid, TERMINAL)
    wait_fsm(sdd_proj, "IMPLEMENTATION")
    entries = audit_entries(sdd_live)
    (summary,) = [e for e in entries if e["event"] == "sdd_write" and e["verb"] == "run"]
    assert (summary["result"], summary["project"], summary["approver"], summary["run_id"]) == (
        "ok", "alpha", "operator", rid)
    assert summary["trace_id"] == "run-audit-9"
    cli = [e for e in entries if e["event"] == "sdd_cli"]
    assert [e["verb"] for e in cli] == ["delegate-enter", "delegate-exit"]
    assert cli[0]["trace_id"] == "run-audit-9" and cli[0]["run_id"] == rid
    assert cli[1]["trace_id"] == "run-audit-9", \
        ("終態同步在監督執行緒，沿用「觸發 spawn 的那個請求」的 trace id（契約 §3.1.1）："
         "整條鏈可 grep")
    raw = (sdd_live.settings.engine_workspace / "_audit.jsonl").read_text(encoding="utf-8")
    assert TOKEN not in raw


def test_a_rejected_sdd_run_is_audited_with_its_reason(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    seed_frozen(sdd_proj, "ESCALATION")
    post(sdd_live, sdd_body(run_body, sdd_proj))
    summary = [e for e in audit_entries(sdd_live) if e["verb"] == "run"][-1]
    assert summary["result"] == "rejected:fsm_state_conflict" and summary["project"] == "alpha"


# ── 工作區裡搜不到權杖（F-7 的檔案面）────────────────────────────────────────────────────────
def test_the_token_value_is_nowhere_in_the_run_workspace(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body,
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRIDGE_SDD_WRITE_TOKEN", TOKEN)
    seed_frozen(sdd_proj, "SPEC_FROZEN")
    resp = post(sdd_live, sdd_body(run_body, sdd_proj, delay="0.1"))
    rid = resp.json()["run_id"]
    sdd_live.wait_status(rid, TERMINAL)
    wait_fsm(sdd_proj, "IMPLEMENTATION")
    needle = TOKEN.encode("utf-8")
    hits = [str(p) for p in Path(resp.json()["workspace"]).rglob("*")
            if p.is_file() and needle in p.read_bytes()]
    assert hits == [], f"權杖值出現在 run 工作區：{hits}"
    assert needle not in b"".join(p.read_bytes() for p in sdd_fake.rglob("fake_calls.jsonl"))
    assert os.environ["BRIDGE_SDD_WRITE_TOKEN"] == TOKEN, "對照：Bridge 自己的環境確實有它"
    assert needle not in (sdd_live.settings.engine_workspace / "_audit.jsonl").read_bytes()
