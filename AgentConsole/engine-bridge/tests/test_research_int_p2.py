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
import subprocess
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


# ══════════════════════════════════════════════════════════════════════════════════════════════
# AT-962-28-3：全棧載具（D-153#1、D-166）——pytest 作 HTTP 客戶端，打第二套拋棄式棧（project r2p2int：  # noqa: E501
# nginx＋backend＋frontend＋PG；Bridge 在主機 local mode）。引擎真：run 的重試耗盡、review_requests 由  # noqa: E501
# console-api 自然產生、視圖列由真資料；claude 為 mock 可執行檔（D-140 #13）。構造：內環鍵的 Stage-2 凍結  # noqa: E501
# （框架 CLI 動詞＋Bridge 的 :freeze 端點，因真拆解需 Brain）、目標與任務由 API 建立。
# 啟用：E2E_STACK=1、E2E_ADMIN_USER／E2E_ADMIN_PASSWORD、E2E_LOCAL_BRIDGE=1、INT_P2_PG_DSN、INT_P2_BRIDGE_URL、  # noqa: E501
# INT_P2_SDD_TOKEN、INT_P2_MOCK_CLAUDE（缺＝TOOL-ABSENCE skip，證據須 0 skipped）。
# ══════════════════════════════════════════════════════════════════════════════════════════════
def stack_absence() -> str:
    need = ("E2E_ADMIN_USER", "E2E_ADMIN_PASSWORD", "INT_P2_PG_DSN", "INT_P2_BRIDGE_URL",
            "INT_P2_SDD_TOKEN", "INT_P2_MOCK_CLAUDE")
    missing = [n for n in need if not os.environ.get(n)]
    if os.environ.get("E2E_STACK") != "1":
        missing.insert(0, "E2E_STACK=1")
    if os.environ.get("E2E_LOCAL_BRIDGE") != "1":
        missing.insert(0, "E2E_LOCAL_BRIDGE=1")
    return f"TOOL-ABSENCE：缺 {', '.join(missing)}（第二套棧＋本機模式 Bridge）" if missing else ""


class StackClient:
    """console-api 的最小 HTTP 客戶端（登入、429 重試、輪詢）；帳密只來自環境。"""

    def __init__(self) -> None:
        import httpx

        self.base = os.environ.get("E2E_API_URL", "http://127.0.0.1:18080").rstrip("/")
        self.http = httpx.Client(timeout=120)
        self.token = ""
        self.token_at = 0.0
        self.created: list[str] = []

    def call(self, method: str, path: str, body: Any = None) -> tuple[int, dict[str, Any]]:
        import time

        for attempt in range(5):
            if time.time() - self.token_at > 1200:
                login = self.http.post(f"{self.base}/api/v1/auth/login", json={
                    "username": os.environ["E2E_ADMIN_USER"],
                    "password": os.environ["E2E_ADMIN_PASSWORD"]})
                assert login.status_code == 200, login.status_code
                self.token, self.token_at = login.json()["data"]["accessToken"], time.time()
            resp = self.http.request(method, f"{self.base}{path}", json=body,
                                     headers={"Authorization": f"Bearer {self.token}"})
            if resp.status_code == 429 and attempt < 4:
                time.sleep(21)
                continue
            try:
                return resp.status_code, resp.json()
            except ValueError:
                return resp.status_code, {}
        raise AssertionError("429 重試用盡")

    def data(self, method: str, path: str, body: Any = None, expect: int = 200) -> Any:
        status, doc = self.call(method, path, body)
        assert status == expect, f"{method} {path} → {status} {json.dumps(doc, ensure_ascii=False)[:400]}"  # noqa: E501
        return doc.get("data")

    def poll(self, fn: Any, done: Any, what: str, timeout: float = 300, interval: float = 3.0) -> Any:  # noqa: E501
        import time

        end, last = time.time() + timeout, None
        while time.time() < end:
            last = fn()
            if done(last):
                return last
            time.sleep(interval)
        raise AssertionError(f"等待逾時：{what}；最後值＝{json.dumps(last, ensure_ascii=False)[:300]}")  # noqa: E501

    # ── 研究專案：建立、四個階段到 Gate 0、API 核准（沿 Playwright helper `driveToGate0`）──────────  # noqa: E501
    def research_stage(self, rid: str, stage: str) -> dict[str, Any]:
        started = self.data("POST", f"/api/v1/research/projects/{rid}/stages/{stage}", {}, 202)
        run_id = started["stageRunId"]

        def progress() -> tuple[str, str]:
            items = self.data("GET", f"/api/v1/research/projects/{rid}/events?afterSeq=0&limit=500")["items"]  # noqa: E501
            runs = [e["payload"].get("status") for e in items if e["eventType"] == "research.run"
                    and e["payload"].get("stageRunId") == run_id]
            steps = [e["payload"].get("flowStatus") for e in items if e["eventType"] == "research.step"]  # noqa: E501
            return (runs[-1] if runs else "", steps[-1] if steps else "")

        self.poll(progress, lambda p: p[0] in ("SUCCEEDED", "FAILED", "CANCELLED") and p[1] not in ("", "RUNNING"),  # noqa: E501
                  f"{stage} 結束", 300)
        return self.data("GET", f"/api/v1/research/projects/{rid}")

    def drive_to_gate0(self, tag: str) -> str:
        slug = f"int28-{tag}-{uuid.uuid4().hex[:6]}"[:30]
        axes = ["技術可行", "授權相容", "維護風險", "效能邊界", "資安", "成本"]
        made = self.data("POST", "/api/v1/research/projects", {
            "slug": slug, "title": f"INT-P2 {tag}", "topic": f"INT-P2 整合 {tag}",
            "scope": {"layers": {"academic": True, "industry": False, "oss": True, "community": False},  # noqa: E501
                      "techStack": "Python / PostgreSQL", "inScope": ["INT"], "outOfScope": ["其他"],  # noqa: E501
                      "recencyYears": 2, "applicabilityAxes": axes}, "depthLevel": "QUICK"}, 201)
        rid = str(made["id"])
        self.created.append(rid)
        for stage in ("research", "draft", "review", "iterate"):
            detail = self.research_stage(rid, stage)
        assert (detail["flowPhase"], detail["flowStatus"]) == ("GATE0_PENDING", "WAITING_HUMAN"), detail  # noqa: E501
        return rid

    def approve(self, rid: str) -> None:
        versions = self.data("GET", f"/api/v1/research/projects/{rid}/prd/versions")
        head = max(versions, key=lambda v: v["versionNo"])
        matrix = self.data("GET", f"/api/v1/research/projects/{rid}/evidence")

        def sha(hex_: str) -> str:
            return hex_ if hex_.startswith("sha256:") else f"sha256:{hex_}"

        done = self.data("POST", f"/api/v1/research/projects/{rid}/approve", {
            "prdVersion": head["versionNo"], "reason": "INT-P2 Gate 0 以 API 核准（代驗）",
            "expectedDigests": {"01_specs/PRD-v1.0.0.md": sha(head["sha256"]),
                                "00_research/evidence_matrix.md": sha(matrix["sha256"])}})
        assert done["fsmState"] == "SPEC_FROZEN"

    def archive_all(self) -> None:
        for rid in self.created:
            self.call("POST", f"/api/v1/research/projects/{rid}/archive", {})


def stack_pg() -> Any:
    import psycopg

    return psycopg.connect(os.environ["INT_P2_PG_DSN"], autocommit=True)


def inner_verb(route: dict[str, Any], tree: Path, verb: str, *args: str) -> str:
    """框架 CLI 動詞（與 Bridge 同一組 argv／環境形狀；構造夾具態用）；回 stdout。"""
    from app import sdd_cli

    key = route["impl_fsm_project"]
    argv = sdd_cli.build_research_argv(verb, list(args), key)
    env = sdd_cli.build_research_env(os.environ, sdd_root=tree, state_dir=Path(route["impl_state_dir"]),  # noqa: E501
                                     project=key)
    proc = subprocess.run(argv, cwd=str(tree), env=env, capture_output=True, text=True,
                          encoding="utf-8", check=False)
    assert proc.returncode == 0, f"{verb} {args} rc={proc.returncode}: {proc.stderr[:300]}"
    return proc.stdout


def construct_stage2(rid: str, route: dict[str, Any], tree: Path) -> None:
    """構造：內環鍵 SPEC_FROZEN(Stage-1)→SPEC_DRAFTING→SCG_VALIDATION→
    HUMAN_PENDING（框架 CLI 動詞），再以 Bridge 的 `:freeze` 端點凍結 Stage-2
    （真拆解需 Brain，載具不具備；證據標「構造」）。"""
    import httpx

    from app import sdd_cli

    key, target = route["impl_fsm_project"], Path(route["target_path"])
    for to in ("SPEC_DRAFTING", "SCG_VALIDATION", "HUMAN_PENDING"):
        inner_verb(route, tree, "transition", "--to", to, "--reason", "INT-P2 構造 Stage-2",
                   "--trigger", sdd_cli.RESEARCH_TRIGGER)
    tcs_rel ="docs/03_testing/contracts/TCS-IntP2-20261108.md"
    tcs = target / tcs_rel
    tcs.parent.mkdir(parents=True, exist_ok=True)
    tcs.write_text("# TCS（INT-P2 構造夾具）\n\n- **AT-001-1** 構造夾具\n", encoding="utf-8", newline="\n")  # noqa: E501
    resp = httpx.post(f"{os.environ['INT_P2_BRIDGE_URL']}/sdd/fsm/{key}:freeze", timeout=120,
                      headers={"X-Bridge-Token": os.environ["INT_P2_SDD_TOKEN"]},
                      json={"root": str(target), "docs": [tcs_rel], "approver": "admin@example.com",
                            "reason": "INT-P2 構造 Stage-2 凍結（夾具）"})
    assert resp.status_code == 200, resp.text[:400]


def inner_route(rid: str) -> dict[str, Any]:
    with stack_pg() as conn:
        row = conn.execute("SELECT impl_fsm_project, impl_state_dir, target_path FROM console."
                           "research_route_decisions WHERE research_id = %s", (rid,)).fetchone()
    assert row is not None
    return {"impl_fsm_project": row[0], "impl_state_dir": row[1], "target_path": row[2]}


@pytest.mark.skipif(stack_absence() != "", reason=stack_absence())
def test_AT_962_28_3_engine_retry_exhaustion_escalates_and_the_view_has_the_failed_step(
        real_tree: Path) -> None:
    """引擎真、claude 為 mock：一個必失敗的任務→RETRYING→FAILED→ESCALATED，
    console-api 自然建 review request，
    `v_research_healing_attempts` 對真失敗步驟有列（非手寫列）。內環鍵 Stage-2 凍結為構造。"""
    stack = StackClient()
    try:
        rid = stack.drive_to_gate0("e3")
        stack.approve(rid)
        route = stack.data("POST", f"/api/v1/research/projects/{rid}/route", {
            "track": "A", "targetModule": "autoclaude", "branchName": f"feature/int28-3-{uuid.uuid4().hex[:5]}",  # noqa: E501
            "scopeDiffersReason": "INT-P2 28-3"})
        assert route["status"] == "SUCCEEDED", route["status"]
        pid = route["consoleProjectId"]
        with stack_pg() as conn:
            row = conn.execute("SELECT impl_fsm_project, impl_state_dir, target_path FROM console."
                               "research_route_decisions WHERE research_id = %s", (rid,)).fetchone()
        assert row is not None
        construct_stage2(rid, {"impl_fsm_project": row[0], "impl_state_dir": row[1],
                               "target_path": row[2]}, real_tree)
        print("AT-962-28-3 [構造] 內環鍵已構造到 Stage-2 凍結（框架 CLI＋:freeze）；[引擎真] 分流 SUCCEEDED、console 專案", pid)  # noqa: E501
        # 系統參數（第二套棧自己的庫）：claude＝mock 可執行檔、關自動續跑、重試一次
        for cat, key, value in (("autoclaude", "claudeCommand", os.environ["INT_P2_MOCK_CLAUDE"]),
                                ("execution", "autoResume", "false"), ("agent", "maxRetries", "1")):
            stack.data("PUT", f"/api/v1/settings/{cat}/{key}", {"value": value})
        goal = stack.data("POST", f"/api/v1/projects/{pid}/goals", {
            "name": "INT-P2 目標", "passCriteria": "任務完成", "description": "", "dependsOn": [],
            "draft": False}, 201)
        for number, (name, extra) in enumerate((("可成功", ""), ("必失敗", " [FAIL_ME]")), start=1):
            stack.data("POST", f"/api/v1/goals/{goal['id']}/tasks", {
                "name": name, "description": f"請輸出 [T{number}_DONE]{extra}", "passCriteria": "x",
                "expectedOutputRegex": f"\\[T{number}_DONE\\]", "maxRetries": 1, "draft": False}, 201)  # noqa: E501
        stack.data("POST", f"/api/v1/projects/{pid}/signoff", {"approver": "admin"})   # 分流建的專案是草案  # noqa: E501
        run = stack.data("POST", f"/api/v1/projects/{pid}/execute",
                         {"autonomyLevel": 4, "tokenBudget": 100000, "scope": {"mode": "ALL"}}, 201)
        run_id = run["id"]

        def view() -> dict[str, Any]:
            return stack.data("GET", f"/api/v1/executions/{run_id}")

        final = stack.poll(view, lambda r: r["status"] in ("FAILED", "COMPLETED") and bool(
            r.get("pendingReviews")), "run 失敗且出現待審項", 180)
        review = final["pendingReviews"][0]
        print("AT-962-28-3 [引擎真，claude 為 mock] run 終態", final["status"], "原因", final.get("reason"),  # noqa: E501
              "待審", review["kind"], review["allowedDecisions"])
        assert final["status"] == "FAILED" and review["kind"] == "ESCALATED"
        steps = stack.data("GET", f"/api/v1/executions/{run_id}/steps?size=200")["content"]
        print("AT-962-28-3 步驟列:", [(s["stepId"], s["status"]) for s in steps])
        assert "RETRYING" in {s["status"] for s in steps} and "FAILED" in {s["status"] for s in steps}  # noqa: E501
        with stack_pg() as conn:
            rr = conn.execute("SELECT kind, status FROM console.review_requests WHERE run_id = %s",
                              (run_id,)).fetchall()
            count = conn.execute("SELECT count(*) FROM console.v_research_healing_attempts WHERE "
                                 "research_id = %s", (rid,)).fetchone()
        print("AT-962-28-3 review_requests:", rr, "｜v_research_healing_attempts 列數:", count)
        assert rr and rr[0][0] == "ESCALATED" and count is not None and count[0] >= 1
        seen = stack.data("GET", f"/api/v1/research/projects/{rid}/healing")
        print("AT-962-28-3 GET healing:", {k: seen[k] for k in ("retryingSteps", "escalatedTasks", "logLag")},  # noqa: E501
              "列數", len(seen["rows"]))
        assert seen["escalatedTasks"] >= 1 and seen["rows"]
    finally:
        stack.archive_all()

def script_scr_round(prd_sha256: str, round_no: int) -> list[str]:
    """構造：SCR 之後外環要再審一輪，pass 劇本只有第 1、2 輪。
    把第 2 輪 PASS 審查卡複製成第 `round_no` 輪
    （改 `round` 與 `prd_sha256`），並在劇本追加四個審查步驟（劇本目錄在 repo 外的暫存副本）。"""
    root = Path(os.environ["INT_P2_SCRIPT_DIR"])
    script_path = root / "mock_claude_script_pass.json"
    script = json.loads(script_path.read_text(encoding="utf-8"))
    written = []
    for dim in ("architecture", "product", "qa", "security"):
        role = f"review-{dim}"
        card = json.loads((root / "content" / "reviews" / "pass" / "round-2" / f"{dim}.json"
                           ).read_text(encoding="utf-8"))
        card["round"], card["prd_sha256"] = round_no, prd_sha256
        out = root / "content" / "reviews" / "scr" / f"round-{round_no}" / f"{dim}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")  # noqa: E501
        script["steps"] = [s for s in script["steps"] if not (s["role"] == role and s["round"] == round_no)]  # noqa: E501
        script["steps"].append({"role": role, "round": round_no, "writes": [{
            "path": f"02_governance/reviews/round-{round_no}/{dim}.json",
            "from": f"content/reviews/scr/round-{round_no}/{dim}.json"}]})
        written.append(out.name)
    script_path.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")  # noqa: E501
    return written


def scr_draft_review(stack: StackClient, rid: str) -> dict[str, Any]:
    """SCR 之後外環的起草（人工存新版 PRD）與審查（劇本第 N 輪，PASS）；Gate 0 核准留給呼叫端（API 代驗）。"""  # noqa: E501
    versions = stack.data("GET", f"/api/v1/research/projects/{rid}/prd/versions")
    head = max(versions, key=lambda v: v["versionNo"])
    body = stack.data("GET", f"/api/v1/research/projects/{rid}/prd/versions/{head['versionNo']}")
    saved = stack.data("PUT", f"/api/v1/research/projects/{rid}/prd", {
        "baseVersion": head["versionNo"],
        "content": body["content"] + "\n\n<!-- INT-P2 MINOR SCR 修訂 -->\n"}, 201)
    rounds = stack.data("GET", f"/api/v1/research/projects/{rid}/review-rounds")
    script_scr_round(saved["sha256"], len(rounds) + 1)
    stack.research_stage(rid, "review")
    return saved


def prepare_routed(stack: StackClient, tree: Path, tag: str, *, implementation: bool) -> dict[str, Any]:  # noqa: E501
    """Gate 0 核准（API 代驗）→分流軌道 A→（構造）內環鍵 Stage-2 凍結→（選）IMPLEMENTATION。"""
    rid = stack.drive_to_gate0(tag)
    stack.approve(rid)
    route = stack.data("POST", f"/api/v1/research/projects/{rid}/route", {
        "track": "A", "targetModule": "autoclaude",
        "branchName": f"feature/int28-{tag}-{uuid.uuid4().hex[:5]}", "scopeDiffersReason": f"INT-P2 {tag}"})  # noqa: E501
    assert route["status"] == "SUCCEEDED", route["status"]
    inner = inner_route(rid)
    construct_stage2(rid, inner, tree)
    if implementation:
        from app import sdd_cli

        inner_verb(inner, tree, "transition", "--to", "IMPLEMENTATION", "--reason", "INT-P2 構造",
                   "--trigger", sdd_cli.RESEARCH_TRIGGER)
    return {"rid": rid, "pid": route["consoleProjectId"], "route": inner}


def make_escalation(stack: StackClient, pid: str) -> dict[str, Any]:
    """引擎真、claude 為 mock：建目標與任務（含必失敗任務）、簽核、啟動 run，等到 ESCALATED 待審項。"""  # noqa: E501
    for cat, key, value in (("autoclaude", "claudeCommand", os.environ["INT_P2_MOCK_CLAUDE"]),
                            ("execution", "autoResume", "false"), ("agent", "maxRetries", "1")):
        stack.data("PUT", f"/api/v1/settings/{cat}/{key}", {"value": value})
    goal = stack.data("POST", f"/api/v1/projects/{pid}/goals", {
        "name": "INT-P2 目標", "passCriteria": "任務完成", "description": "", "dependsOn": [],
        "draft": False}, 201)
    for number, (name, extra) in enumerate((("可成功", ""), ("必失敗", " [FAIL_ME]")), start=1):
        stack.data("POST", f"/api/v1/goals/{goal['id']}/tasks", {
            "name": name, "description": f"請輸出 [T{number}_DONE]{extra}", "passCriteria": "x",
            "expectedOutputRegex": f"\\[T{number}_DONE\\]", "maxRetries": 1, "draft": False}, 201)
    stack.data("POST", f"/api/v1/projects/{pid}/signoff", {"approver": "admin"})
    run = stack.data("POST", f"/api/v1/projects/{pid}/execute",
                     {"autonomyLevel": 4, "tokenBudget": 100000, "scope": {"mode": "ALL"}}, 201)
    final = stack.poll(lambda: stack.data("GET", f"/api/v1/executions/{run['id']}"),
                       lambda r: r["status"] in ("FAILED", "COMPLETED") and bool(r.get("pendingReviews")),  # noqa: E501
                       "run 失敗且出現待審項", 180)
    return {"runId": run["id"], "reviewId": final["pendingReviews"][0]["id"],
            "kind": final["pendingReviews"][0]["kind"], "status": final["status"]}


def stack_setup(kind: str, tag: str) -> dict[str, Any]:
    """Playwright spec 的 Given 佈置（以 `python -c` 呼叫）：回 JSON 可序列化的字典。"""
    from tests.test_research_fsm_ops import real_sdd_root

    stack = StackClient()
    tree = Path(real_sdd_root())
    made = prepare_routed(stack, tree, tag, implementation=kind == "scr")
    if kind == "escalated":
        made.update(make_escalation(stack, made["pid"]))
    elif kind == "scr-draft-review":
        raise AssertionError("用 scr_draft_review_cli")
    return made


def scr_draft_review_cli(rid: str) -> dict[str, Any]:
    stack = StackClient()
    saved = scr_draft_review(stack, rid)
    return {"versionNo": saved["versionNo"], "sha256": saved["sha256"]}


def fsm_step(rid: str, step: str, reason: str = "INT-P2 V-D5") -> dict[str, Any]:
    """V-D5 量測用：對內環鍵做一個 FSM 動作（框架 CLI），回完成時刻（epoch 毫秒）與動作後的現態。"""
    import time

    from app import sdd_cli
    from tests.test_research_fsm_ops import real_sdd_root

    tree, route = Path(real_sdd_root()), inner_route(rid)
    verbs = {"to_pr_review": ("transition", "--to", "PR_REVIEW", "--reason", reason, "--trigger",
                              sdd_cli.RESEARCH_TRIGGER),
             "pr_fail": ("gate", "--gate", "PR_REVIEW", "--result", "FAIL", "--reason", reason),
             "pr_pass": ("gate", "--gate", "PR_REVIEW", "--result", "PASS", "--reason", reason),
             "rtm_pass": ("gate", "--gate", "RTM_VERIFY", "--result", "PASS", "--reason", reason)}
    verb, *args = verbs[step]
    out = inner_verb(route, tree, verb, *args)
    return {"doneMs": int(time.time() * 1000), "out": out.strip()[:200]}
