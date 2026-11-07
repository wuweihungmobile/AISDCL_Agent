"""整合 P2：內環走到交付、PR、對帳 delivery 項、SPEC_CHANGE 取證、hermetic 掃描（TCS AT-962-28-1、
28-2、28-6、28-E-1、28-E-3；PKG-INT-P2）。AT-962-28-3 以全棧為載具（D-153#1），見檔尾。

載具劃界（證據逐字，不得混淆）：
  · 引擎真：框架 FSM CLI 的每個動詞（transition／gate／show）、gitops 的 git 呼叫（真 git、
    `file://` bare origin）、DB 寫入（拋棄式庫）、對帳。
  · 構造：RTM 報告檔（`rtm` 夾具寫的 RTM-COVERAGE yaml）、`tasks` 列（`seed_task`）、
    `research_decompositions`
    SIGNED_OFF 列、內環鍵以 transition 推到 IMPLEMENTATION 的「夾具態」（非真實開發 run；V-H5 才是
    真人真機整串）、`gh` 是假夾具。
hermetic：真 git 只在 `tmp_path` 拋棄式 repo 與 `file://` bare repo；`gh` 假夾具；FSM 狀態目錄在
`tmp_path`；缺 `SDD_ROOT`／`BRIDGE_TEST_DSN`＝`TOOL-ABSENCE` skip（證據須 0 skipped）。
證據以 `print`
輸出，由 `-s` 擷取；機密樣式字面一律執行期拼接。
"""
from __future__ import annotations

import ast
import json
import os
import re
import socket
import uuid
from pathlib import Path
from typing import Any

import pytest

from app.research import fsm_ops
from tests import research_git_support as rgs
from tests import test_research_delivery as dl
from tests import test_research_healing as hs
from tests import test_research_inner_gates as ig
from tests import test_research_router as rt
from tests.test_research_scr import cli, inner, sdk_trigger

make_env = rt.make_env
route_db, real_tree, renv, fake_gh = rgs.route_db, rgs.real_tree, rgs.renv, rgs.fake_gh
rtm, verbs = ig.rtm, ig.verbs
calls, direct_fake_gh = dl.calls, dl.direct_fake_gh
BRIDGE_DIR = Path(__file__).resolve().parents[1]
# 假 token 字面（TCS §5.2）：`ghp_` 後接 FAKE 字樣的佔位值，不是真機密
FAKE_TOKEN = rgs.FAKE_TOKEN


def trace_triples(renv: rgs.RouteEnv, route: dict[str, Any]) -> list[tuple[Any, Any, Any]]:
    entries = fsm_ops.show(inner(renv, route))["decision_trace"]
    return [(e.get("from") or e.get("from_state"), e.get("to") or e.get("to_state"),
             e.get("trigger")) for e in entries]


def checks_of(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {c["id"]: c for c in result["checks"]}


# ── AT-962-28-1：gates → gates → tag，與人工等價序列 diff 為空 ───────────────────────────────
def test_AT_962_28_1_inner_loop_runs_to_release_and_equals_the_manual_equivalent_sequence(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: dl.Calls) -> None:
    """夾具態（構造）：內環鍵以 transition 推到 IMPLEMENTATION；其後三個 Bridge 動作都是引擎真。"""
    project = dl.build_project(renv, "int281", state="IMPLEMENTATION")
    rid, route = project.rid, project.route
    print("AT-962-28-1 [構造] 起點：內環鍵以 transition 推到", project.state())
    pr = ig.post_gate(renv, rid, "PR_REVIEW", "PASS", run_id=project.run_id)
    assert pr.status_code == 200, pr.text
    rtmv = ig.post_gate(renv, rid, "RTM_VERIFY", "PASS", run_id=project.run_id)
    assert rtmv.status_code == 200, rtmv.text
    print("AT-962-28-1 [引擎真] :gates PR_REVIEW →", pr.json()["fsm_state_before"], "→",
          pr.json()["next_state"], "| :gates RTM_VERIFY →", rtmv.json()["fsm_state_before"], "→",
          rtmv.json()["next_state"])
    assert (pr.json()["next_state"], rtmv.json()["next_state"]) == ("RTM_VERIFY", "RELEASE_READY")
    assert project.state() == "RELEASE_READY"
    tag = project.tag()
    assert tag.status_code == 201, tag.text
    assert tag.json()["fsmState"] == "RELEASE"
    shown = fsm_ops.show(inner(renv, route))
    print("AT-962-28-1 [引擎真] show current_state=" + str(shown["current_state"]))
    assert shown["current_state"] == "RELEASE"
    bare = project.bare                                         # type: ignore[attr-defined]
    git_tools = calls.tools("git")
    print("AT-962-28-1 [引擎真] gitops 呼叫序（節錄）:",
          [c[:3] for c in git_tools if c[0] in ("tag", "ls-remote", "push", "rev-parse", "remote")])
    for verb in (("tag", "--list", dl.TAG), ("tag", "-a", dl.TAG), ("ls-remote", "--tags", "origin",
                                                                      dl.TAG),
                 ("push", "origin", dl.TAG)):
        assert [c for c in git_tools if c[:len(verb)] == verb], verb
    bare_tags = rgs.git(bare, "tag", "--list").split()
    print("AT-962-28-1 [引擎真] file:// bare origin 的 tag:", bare_tags)
    assert bare_tags == [dl.TAG]
    # 人工等價序列：另一鍵、同一份 CLI（引擎真）
    manual = dl.build_project(renv, "int281m", state="IMPLEMENTATION", origin=False)
    key, sdir = manual.route["impl_fsm_project"], manual.route["impl_state_dir"]
    steps: list[tuple[str, tuple[str, ...]]] = [
        ("transition", ("--to", "PR_REVIEW", "--reason", "manual", "--trigger", sdk_trigger())),
        ("gate", ("--gate", "PR_REVIEW", "--result", "PASS", "--reason", "manual")),
        ("gate", ("--gate", "RTM_VERIFY", "--result", "PASS", "--reason", "manual")),
        ("transition", ("--to", "RELEASE", "--reason", "manual", "--trigger", sdk_trigger()))]
    for verb, args in steps:
        proc = cli(renv, key, sdir, verb, *args)
        print(f"AT-962-28-1 [引擎真] 人工 {verb} {args[1]} rc={proc.returncode} stdout=",
              proc.stdout.strip().replace("\n", " ")[:300])
    bridge_trace, manual_trace = trace_triples(renv, route), trace_triples(renv, manual.route)
    print("AT-962-28-1 decision_trace(from,to,trigger) Bridge:", bridge_trace)
    print("AT-962-28-1 decision_trace(from,to,trigger) 人工  :", manual_trace)
    assert bridge_trace == manual_trace, "decision_trace 與人工等價序列 diff 為空"
    assert fsm_ops.current_state(inner(renv, manual.route)) == "RELEASE"
    # M2（凍結一致）：對帳 prd_sha256 與 delivery 皆 ok；
    # M3 另取（console-api 的 records/audit，真棧）
    rec = renv.env.post(f"/research/projects/{rid}:reconcile", {})
    assert rec.status_code == 200, rec.text
    checks = checks_of(rec.json())
    print("AT-962-28-1 M2 對帳:", {k: checks[k]["status"] for k in checks}, "consistent=",
          rec.json()["consistent"])
    assert checks["prd_sha256"]["status"] == "ok" and checks["delivery"]["status"] == "ok"
    tables = ("research_gate_decisions", "research_deliveries", "research_events",
              "research_artifacts", "research_route_decisions")
    print("AT-962-28-1 M3 紀錄列數（拋棄式庫；官方指標＝records/audit 的 missing[]，見真棧段）:",
          {t: renv.rdb.count(t) for t in tables})
    assert [g[0] for g in ig.gate_rows(renv, rid)] == ["SCG4", "SCG5"]
    assert dl.hashlib_sha(project.snapshot_path().read_bytes()) == project.rows("RELEASE_TAG")[0][6]


# ── AT-962-28-2：PR（假 gh）與 token 零外洩、fail-pr 不寫 FAILED 列 ───────────────────────────
def test_AT_962_28_2_pr_via_the_fake_gh_records_the_row_and_leaks_no_token(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: dl.Calls, fake_gh: rgs.FakeGh,
        caplog: pytest.LogCaptureFixture) -> None:
    project = dl.build_project(renv, "int282")
    caplog.set_level("DEBUG")
    calls.clear(), fake_gh.clear()
    resp = project.pr()
    assert resp.status_code == 201, resp.text
    url = resp.json()["delivery"]["url"]
    print("AT-962-28-2 [引擎真/假 gh] PR URL:", url, "created=", resp.json()["created"])
    assert url.endswith("/pull/7")
    (row,) = project.rows("PULL_REQUEST")
    assert row[0] == "PULL_REQUEST" and row[3] == url and row[6] is None and row[8] == "CREATED"
    events = [p for p in ig.events_of(renv, project.rid, "research.delivery")]
    assert len(events) == 1 and set(events[0]) == {"kind", "ref", "status", "digest", "reason",
                                                   "failure_step"}
    print("AT-962-28-2 research.delivery 事件六鍵:", events[0])
    gh_calls = fake_gh.calls()
    assert [c["argv"][:2] for c in gh_calls] == [["auth", "status"], ["pr", "list"],
                                                 ["pr", "create"]]
    assert gh_calls[-1]["has_gh_token"] is True, "token 只在環境，不在 argv"
    # token 掃描：argv、假 gh 紀錄、DB 全表文字、回應、日誌
    blob = "\n".join(" ".join(c) for c in calls) + json.dumps(gh_calls) + resp.text + caplog.text
    assert not rgs.contains_secret(blob, FAKE_TOKEN)
    cells = list(rgs.all_text_columns(renv.rdb))
    assert len(cells) > 100
    hits = [(t, c) for t, c, v in cells if v and rgs.contains_secret(str(v), FAKE_TOKEN)]
    print(f"AT-962-28-2 token 掃描：DB 全表文字欄 {len(cells)} 格、命中 {len(hits)}；",
          "argv／紀錄／回應／日誌命中 0")
    assert hits == []
    # fail-pr：502 delivery_step_failed，不寫 FAILED 列、只發事件（D-138 Q-10）
    failing = dl.build_project(renv, "int282f")
    fake_gh.mode("fail-pr")
    bad = failing.pr()
    assert (bad.status_code, bad.json()["reason"]) == (502, "delivery_step_failed")
    assert bad.json()["details"]["failure_step"] == "pr_create"
    assert failing.rows() == []
    failed = ig.events_of(renv, failing.rid, "research.delivery")
    print("AT-962-28-2 fail-pr：502 delivery_step_failed、列 0、事件", failed)
    assert len(failed) == 1 and failed[0]["status"] == "FAILED" and failed[0]["ref"] is None


# ── AT-962-28-6：對帳 delivery 項（ok → 改一位元組 drift → 還原 ok；只報告不修復）────────────
def test_AT_962_28_6_reconcile_after_tag_is_consistent_and_a_tampered_snapshot_is_reported_only(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture) -> None:
    project = dl.build_project(renv, "int286")
    assert project.tag().status_code == 201
    last = ig.events_of(renv, project.rid, "research.reconcile")[-1]
    print("AT-962-28-6 :tag 後的對帳事件:", last)
    assert last["consistent"] is True
    snap = project.snapshot_path()
    original = snap.read_bytes()
    row_before = project.rows("RELEASE_TAG")
    tampered = bytearray(original)
    tampered[5] = tampered[5] ^ 0x01                             # 手改一個位元組（長度不變）
    snap.write_bytes(bytes(tampered))
    drift = renv.env.post(f"/research/projects/{project.rid}:reconcile", {})
    assert drift.status_code == 200, drift.text
    item = checks_of(drift.json())["delivery"]
    print("AT-962-28-6 手改一位元組後 delivery 項:", item["status"], item["drift"])
    assert item["status"] == "drift" and drift.json()["consistent"] is False
    (entry,) = item["drift"]
    assert entry["expectedSha256"] == dl.hashlib_sha(original)
    assert entry["actualSha256"] == dl.hashlib_sha(bytes(tampered))
    assert snap.read_bytes() == bytes(tampered), "只報告：檔位元組不被修復"
    assert project.rows("RELEASE_TAG") == row_before, "只報告：DB 列不被改"
    snap.write_bytes(original)
    ok = renv.env.post(f"/research/projects/{project.rid}:reconcile", {})
    assert checks_of(ok.json())["delivery"]["status"] == "ok" and ok.json()["consistent"] is True
    print("AT-962-28-6 還原後 delivery 項:", checks_of(ok.json())["delivery"]["status"])


# ── AT-962-28-E-1：SPEC_CHANGE 取證（偵測＋告警＋不還原；不聲稱被拒）──────────────────────────
def test_AT_962_28_E_1_a_hand_edited_frozen_file_is_detected_alerted_and_never_restored(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, verbs: ig.VerbLog) -> None:
    project = dl.build_project(renv, "int28e1", state="IMPLEMENTATION", origin=False)
    target = ig.frozen_prd(project.route)
    changed = target.read_bytes() + b"\n<!-- INT-P2 hand edit -->\n"
    target.write_bytes(changed)
    sha_after_edit = dl.hashlib_sha(changed)
    first = hs.sync(renv, project.rid)
    assert first.status_code == 200, first.text
    drift = first.json()["spec_change"]
    print("AT-962-28-E-1 :healing-sync 偵測:", drift)
    assert [d["path"] for d in drift] == ["docs/01_requirements/int28e1_PRD.md"]
    alerts = [p for p in ig.events_of(renv, project.rid, "research.alert")
              if p["kind"] == "SPEC_CHANGE_FORBIDDEN"]
    spec_lines = [ln for ln in hs.log_lines(renv, project.rid) if ln.get("spec_change")]
    print("AT-962-28-E-1 告警事件:", len(alerts),
          "healing_history.log spec_change 行:", len(spec_lines))
    assert len(alerts) == 1 and len(spec_lines) == 1
    assert dl.hashlib_sha(target.read_bytes()) == sha_after_edit, "Bridge 不還原檔"
    hs.sync(renv, project.rid)                                   # 同漂移不重複告警
    assert len([p for p in ig.events_of(renv, project.rid, "research.alert")
                if p["kind"] == "SPEC_CHANGE_FORBIDDEN"]) == 1
    assert len([ln for ln in hs.log_lines(renv, project.rid) if ln.get("spec_change")]) == 1
    # 同一夾具打 :gates／:tag：422 digest_mismatch（details.drift[]）、零 FSM 呼叫、零 DB 寫入
    counts = {t: renv.rdb.count(t) for t in ("research_gate_decisions", "research_deliveries")}
    verbs.clear()
    body = ig.post_gate(renv, project.rid, "PR_REVIEW", "PASS", run_id=project.run_id)
    tag = project.tag()
    for name, resp in (("gates", body), ("tag", tag)):
        assert (resp.status_code, resp.json()["reason"]) == (422, "digest_mismatch"), name
        assert set(resp.json()["details"]["drift"][0]) == {"path", "expected_sha256",
                                                           "actual_sha256"}
    print("AT-962-28-E-1 :gates／:tag →", body.status_code, body.json()["reason"], "／",
          tag.status_code, tag.json()["reason"], "；FSM 寫入動詞", verbs.writes())
    assert verbs.writes() == []
    assert {t: renv.rdb.count(t) for t in counts} == counts
    assert dl.hashlib_sha(target.read_bytes()) == sha_after_edit
    text = json.dumps(first.json()) + json.dumps(ig.events_of(renv, project.rid, "research.alert"))
    assert not re.search(r"reject|block|denied", text, re.IGNORECASE), "不聲稱『被拒』（V-S1）"


# ── AT-962-28-E-3：hermetic（socket 層攔截＋原始碼掃描）─────────────────────────────────────
P2_SOURCES = ("app/research/delivery.py", "app/research/inner_gates.py", "app/research/healing.py",
              "app/research/gitops.py", "app/routers/research_deliver.py")
P2_TEST_FILES = ("tests/test_research_inner_gates.py", "tests/test_research_delivery.py",
                 "tests/test_research_healing.py", "tests/test_research_deliver_router.py")
REAL_HOSTS = ("https://github.com", "api.github.com", "github.com")
# 掃描判準：只看「非 docstring 的字串常數」；假夾具資料與錯誤訊息文字不算呼叫。允許清單逐行登記。
ALLOWED_LITERAL = {
    ("app/research/gitops.py", "remote add origin <https://github.com/…>"),   # 拒絕訊息文字
    ("tests/test_research_delivery.py", "octocat/demo-app/pull/42"),            # 假 gh PR 清單夾具
}


def string_constants(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = {id(n.body[0].value) for n in ast.walk(tree)
                  if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                    ast.AsyncFunctionDef))
                  and n.body and isinstance(n.body[0], ast.Expr)
                  and isinstance(n.body[0].value, ast.Constant)}
    return [(n.lineno, n.value) for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings]


def test_AT_962_28_E_3_no_real_github_connection_in_sources_or_at_runtime(
        renv: rgs.RouteEnv, rtm: ig.RtmFixture, calls: dl.Calls, fake_gh: rgs.FakeGh,
        monkeypatch: pytest.MonkeyPatch) -> None:
    # ① 原始碼掃描（P2 產品碼五檔＋P2 四個 Bridge 測試檔；本檔自身含掃描詞表，不納入）
    hits: list[tuple[str, int, str]] = []
    for rel in (*P2_SOURCES, *P2_TEST_FILES):
        for line, text in string_constants(BRIDGE_DIR / rel):
            if any(host in text for host in REAL_HOSTS):
                hits.append((rel, line, text))
    unexplained = [h for h in hits if not any(rel == h[0] and frag in h[2]
                                              for rel, frag in ALLOWED_LITERAL)]
    print("AT-962-28-E-3 掃描判準：AST 非 docstring 字串常數含", REAL_HOSTS,
          "；允許清單", sorted(ALLOWED_LITERAL))
    print("AT-962-28-E-3 掃描命中（皆在允許清單）:", [(h[0], h[1]) for h in hits])
    assert unexplained == [], unexplained
    # ② 執行期：socket 層攔截所有非 loopback 連線與 github 名稱解析，跑交付與自癒案例
    outbound: list[Any] = []
    real_connect, real_gai = socket.socket.connect, socket.getaddrinfo

    def guarded_connect(self: socket.socket, address: Any) -> Any:
        host = address[0] if isinstance(address, tuple) else str(address)
        if host not in ("127.0.0.1", "::1", "localhost") and not str(host).startswith("\0"):
            outbound.append(("connect", address))
        return real_connect(self, address)

    def guarded_gai(host: Any, *a: Any, **k: Any) -> Any:
        if isinstance(host, str) and "github" in host.lower():
            outbound.append(("resolve", host))
        return real_gai(host, *a, **k)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_gai)
    project = dl.build_project(renv, "int28e3")
    assert project.pr().status_code == 201
    assert project.tag().status_code == 201
    assert hs.sync(renv, project.rid).status_code == 200
    argv_text = "\n".join(" ".join(c) for c in calls)
    print("AT-962-28-E-3 執行期 Bridge 放行的 git／gh 呼叫共", len(calls),
          "筆；非 loopback 連線／github 解析:",
          outbound)
    assert outbound == []
    assert not [h for h in REAL_HOSTS if h in argv_text.replace("file:///", "")], argv_text
    assert os.environ.get("FAKE_GH_MODE") == "ok" and fake_gh.calls(), "gh 是假夾具"
    assert uuid.UUID(project.rid)
