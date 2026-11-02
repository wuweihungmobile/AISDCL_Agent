"""假 SDD 樹：暫存目錄內放一支只依 ADR-XPLAT-016 §4 的契約回放 JSON 的
`tools/fsm_runtime/fsm_runtime.py`。

ADR §15：Bridge 的測試以「假 SDD 樹」真起子行程，斷言 argv、cwd、環境集合、逾時殺樹與整條流程，
不依賴真 CLI（真 CLI 由 SDD 側的 `test_cli_bridge_verbs.py` 守；兩邊的契約對拍在
`test_sdd_integration_parity.py` 檔尾，以真 CLI 子行程驗）。

假 CLI 是一台迷你狀態機（只實作 Bridge 會呼叫的五個動詞，轉態與 rc 表照 ADR §4.1／§4.2／乾跑
#3～#21）：狀態檔寫在 `SDD_STATE_DIR/FSM-STATE-<--project>.yaml`（形狀照真檔：`fsm_state` 根
節點），所以 `GET /sdd/fsm/{project}` 與 adapter 讀得到它的效果。每次呼叫把 argv、cwd 與
BRIDGE_*／SDD_*／PYTHON* 環境 append 到 `<sdd 版本目錄>/fake_calls.jsonl`（測試用 `read_calls`
取回）；`<版本目錄>/fake_control.json` 可讓指定動詞 sleep（逾時）、強制 rc、或回非 JSON（測試用
`set_control`）。

研究面（ResearchToPRD；TCS-ResearchToPRD-P0-20261102 §5.2）另增五個動詞的行為——`show`（缺檔且不帶
`--must-exist`＝建出 INIT 狀態檔）、`transition`、`gate`、`spec-refreeze`、
`resume-from-escalation`——以及 `spec-frozen` 對 `Gate-0*` 階段的前置（HUMAN_PENDING 或
SPEC_REGRESSION_CHECK）。重試規則逐步對齊真 CLI（D-60）：第 N 次 FAIL 先加計數再判上限、達上限
即 ESCALATION、`resume-from-escalation` 不動計數、再 FAIL 立即再 ESCALATION、PASS 歸零；
`SDD_ENABLE_AUTO_RECOVERY` 未設時耗盡的 gate 會進 AUTO_RECOVERY_ATTEMPT（與真 CLI 的預設一致，
所以外環鍵的環境固定 `=0` 才擋得住）。既有五個動詞的行為一字不動。

這支檔本身不是測試（檔名不以 test_ 開頭）；它被測試 import 來造樹與讀紀錄。
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import yaml

FAKE_VERSION_DIR = "AISDLC_SDD_v9.99"

_FAKE_CLI = r'''
"""fake FSMRuntime CLI（測試替身）。"""
import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CALLS = ROOT / "fake_calls.jsonl"
CONTROL = ROOT / "fake_control.json"


def now():
    return datetime.now(timezone.utc).isoformat()


def emit(obj, rc=0):
    print(json.dumps(obj, ensure_ascii=True, separators=(",", ":")))
    sys.exit(rc)


def fail(error, detail, rc, **extra):
    print("[SDD-FSM] %s failed: %s: %s" % (VERB, error, detail), file=sys.stderr)
    emit({"ok": False, "error": error, "detail": detail[:200], **extra}, rc)


parser = argparse.ArgumentParser()
parser.add_argument("verb", choices=["spec-frozen", "negotiate-enter", "negotiate-exit",
                                     "delegate-enter", "delegate-exit",
                                     "show", "transition", "gate", "spec-refreeze",
                                     "resume-from-escalation"])
parser.add_argument("--project", required=True)
parser.add_argument("--must-exist", action="store_true")
parser.add_argument("--reason", default="")
parser.add_argument("--stage")
parser.add_argument("--doc", action="append", default=[])
parser.add_argument("--digest", action="store_true")
parser.add_argument("--root")
parser.add_argument("--approver")
parser.add_argument("--json", action="store_true")
parser.add_argument("--contract-ref")
parser.add_argument("--outcome", choices=["agreed", "underspecified"])
parser.add_argument("--playbook-ref")
parser.add_argument("--decision", choices=["done", "failed"])
parser.add_argument("--to")
parser.add_argument("--gate")
parser.add_argument("--result", choices=["PASS", "FAIL", "pass", "fail"])
parser.add_argument("--trigger", default="cli_manual")
args = parser.parse_args()
VERB = args.verb

with CALLS.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps({
        "verb": VERB, "argv": sys.argv[1:], "cwd": os.getcwd(), "executable": sys.executable,
        "pid": os.getpid(), "warnoptions": list(sys.warnoptions),
        "env": {k: v for k, v in os.environ.items()
                if k.upper().startswith(("BRIDGE_", "SDD_", "PYTHON"))},
        "env_names": sorted(os.environ)}, ensure_ascii=False) + "\n")

control = json.loads(CONTROL.read_text(encoding="utf-8")) if CONTROL.is_file() else {}
if control.get("sleep", {}).get(VERB):
    time.sleep(float(control["sleep"][VERB]))
if VERB in control.get("raw_stdout", {}):
    print(control["raw_stdout"][VERB])
    sys.exit(0)
if VERB in control.get("rc", {}):
    forced = control["rc"][VERB]
    if forced == 1:
        raise RuntimeError("forced traceback")
    fail("forced", "forced rc %d" % forced, forced, **control.get("rc_extra", {}))

state_dir = Path(os.environ["SDD_STATE_DIR"])
path = state_dir / ("FSM-STATE-%s.yaml" % args.project)
if VERB == "show" and not path.is_file() and not args.must_exist:
    state_dir.mkdir(parents=True, exist_ok=True)
    fresh = {"fsm_state": {
        "project": args.project, "session_id": "sid-fake", "created_at": now(),
        "updated_at": now(), "current_state": "INIT", "current_sprint": 1,
        "decision_trace": [], "frozen_stages": [], "escalation_history": [],
        "human_pending_tracking": {"entered_at": None, "reminder_sent_at": None,
                                   "reminder_hours": 72, "escalation_hours": 168},
        "retry_history": {
            "SCG_VALIDATION": {"current_count": 0, "max_limit": 3, "history": []},
            "PR_REVIEW": {"current_count": 0, "max_limit": 5, "spec_audit_count": 0,
                          "history": [], "patterns": []},
            "RTM_VERIFY": {"current_count": 0, "max_limit": 2, "history": []}},
        "cumulative_history": {}}}
    path.write_text(yaml.safe_dump(fresh, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(json.dumps(fresh, indent=2, ensure_ascii=False, default=str))
    sys.exit(0)
if not path.is_file():
    if args.must_exist:
        fail("state_not_found", "no state file for %s" % args.project, 5)
    sys.exit(5)
try:
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    st = doc["fsm_state"]
except Exception:
    fail("state_unreadable", "state file is not readable", 5)

if VERB in ("negotiate-enter", "negotiate-exit", "delegate-enter", "delegate-exit"):
    if not args.reason.strip():
        fail("invalid_argument", "--reason is required", 4)


def save(to, trigger, reason):
    frm = st["current_state"]
    st["current_state"] = to
    st["updated_at"] = now()
    st.setdefault("decision_trace", []).append(
        {"ts": now(), "from": frm, "to": to, "trigger": trigger, "reason": reason})
    path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")


def ok(frm, **extra):
    emit({"ok": True, "verb": VERB, "project": args.project, "from_state": frm,
          "current_state": st["current_state"], **extra})


def conflict(expected):
    fail("transition_not_allowed", "%s called in state=%s, expected %s" % (
        VERB, st["current_state"], expected), 3, current_state=st["current_state"])


# ── 研究面（ResearchToPRD）：五個動詞與 spec-frozen 的 Gate-0* 階段；對齊真 CLI 的行為 ────────────
EDGES = {
    "INIT": {"SCENARIO_DETECT"}, "SCENARIO_DETECT": {"AGENT_LOAD"},
    "AGENT_LOAD": {"SPEC_DRAFTING", "BACKLOG_PRIORITIZED", "INTENT_DECOMPOSITION"},
    "SPEC_DRAFTING": {"SCG_VALIDATION"}, "SCG_VALIDATION": {"HUMAN_PENDING", "SPEC_DRAFTING"},
    "HUMAN_PENDING": {"SPEC_REGRESSION_CHECK", "SPEC_FROZEN", "REMINDER"},
    "SPEC_REGRESSION_CHECK": {"SPEC_FROZEN", "HUMAN_PENDING"}, "REMINDER": {"HUMAN_PENDING"},
    "SPEC_FROZEN": {"IMPLEMENTATION", "SPEC_DRAFTING", "TEST_CONTRACT_NEGOTIATED"},
    "IMPLEMENTATION": {"PR_REVIEW", "SPEC_AUDIT", "EXECUTION_EVALUATION"},
    "PR_REVIEW": {"RTM_VERIFY", "SPEC_AUDIT", "IMPLEMENTATION"}, "SPEC_AUDIT": {"PR_REVIEW"},
    "RTM_VERIFY": {"RELEASE_READY", "IMPLEMENTATION"},
    "RELEASE_READY": {"RELEASE", "IMPLEMENTATION"}, "RELEASE": set(),
    "ESCALATION": {"TERMINATED", "RESUME_VERIFICATION", "AUTO_RECOVERY_ATTEMPT",
                   "ESCALATION_FINAL"},
    "RESUME_VERIFICATION": {"SPEC_DRAFTING", "IMPLEMENTATION", "PR_REVIEW", "ESCALATION"},
    "ESCALATION_FINAL": {"TERMINATED", "RESUME_VERIFICATION"},
}
EMERGENCY = {"ESCALATION", "TOKEN_BUDGET_CRITICAL", "TERMINATED"}
LIMITS = {"SCG_VALIDATION": 3, "PR_REVIEW": 5, "RTM_VERIFY": 2, "SPEC_REGRESSION_CHECK": 2,
          "RELEASE_READY": 2}
PASS_NEXT = {"SCG_VALIDATION": "HUMAN_PENDING", "SPEC_REGRESSION_CHECK": "SPEC_FROZEN",
             "PR_REVIEW": "RTM_VERIFY", "RTM_VERIFY": "RELEASE_READY", "RELEASE_READY": "RELEASE"}
FAIL_NEXT = {"SCG_VALIDATION": "SPEC_DRAFTING", "PR_REVIEW": "IMPLEMENTATION",
             "RTM_VERIFY": "IMPLEMENTATION", "RELEASE_READY": "IMPLEMENTATION",
             "SPEC_REGRESSION_CHECK": "HUMAN_PENDING"}
RESUMABLE = {"SCG_VALIDATION", "PR_REVIEW", "RTM_VERIFY", "SPEC_REGRESSION_CHECK"}
RESUME_TARGETS = ("SPEC_DRAFTING", "IMPLEMENTATION", "PR_REVIEW")


def persist():
    path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")


def trace(frm, to, reason, trigger):
    st.setdefault("decision_trace", []).append(
        {"ts": now(), "from": frm, "to": to, "reason": reason, "spec_refs": [],
         "agents_consulted": [], "trigger": trigger})
    st["updated_at"] = now()


def move(dst, reason, trigger):
    """真 CLI 的 transition()：非法邊＝未捕捉的例外（traceback、rc 1、狀態檔不動）。"""
    frm = st["current_state"]
    if not (dst in EMERGENCY or dst in EDGES.get(frm, ())):
        raise RuntimeError("transition not allowed: %s -> %s" % (frm, dst))
    st["current_state"] = dst
    st["updated_at"] = now()
    tracking = st.setdefault("human_pending_tracking", {})
    if dst == "HUMAN_PENDING" and frm != "HUMAN_PENDING":
        tracking["entered_at"] = now()
    elif frm == "HUMAN_PENDING" and dst != "HUMAN_PENDING":
        tracking["entered_at"] = None
    trace(frm, dst, reason, trigger)
    persist()


def retry_entry(gate):
    return st.setdefault("retry_history", {}).setdefault(gate, {})


def reset_retry(gate):
    entry = retry_entry(gate)
    entry["current_count"] = 0
    entry.setdefault("history", [])


def increment_retry(gate, failure_reason):
    """真 CLI 的 increment_retry：事前計數已達上限＝夾在上限並在歷史列標 tamper 字樣。"""
    entry = retry_entry(gate)
    try:
        prior = int(entry.get("current_count", 0))
    except (TypeError, ValueError):
        prior = 0
    limit = LIMITS.get(gate)
    note = ""
    tamper = False
    if prior < 0:
        tamper, note, prior = True, "(tamper detected: prior_count=%s, floored to 0)" % prior, 0
    elif limit is not None and prior >= limit:
        tamper, note = True, "(tamper detected: prior_count=%s >= limit=%s)" % (prior, limit)
    current = limit if tamper and limit is not None else prior + 1
    entry["current_count"] = current
    history = entry.setdefault("history", []) or []
    history.append({"attempt": current, "date": now(), "scg_gate": None,
                    "failure_reason": ("%s %s" % (failure_reason, note)).strip() if note
                    else failure_reason})
    entry["history"] = history
    return current


def digests_of(root, docs):
    base = Path(root).resolve()
    out = {}
    for item in docs:
        target = (base / item).resolve()
        try:
            target.relative_to(base)
        except ValueError:
            fail("doc_outside_root", item, 4)
        if not target.is_file():
            fail("doc_not_found", item, 4)
        text = target.read_text(encoding="utf-8")
        out[target.relative_to(base).as_posix()] = (
            "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest())
    return out


def research_main():
    cur = st["current_state"]
    if VERB == "show":
        print(json.dumps(doc, indent=2, ensure_ascii=False, default=str))
    elif VERB == "transition":
        if not args.to:
            parser.error("--to required")
        move(args.to, args.reason or "cli transition to %s" % args.to, args.trigger)
        print("OK transitioned to %s" % st["current_state"])
    elif VERB == "gate":
        if not args.gate or not args.result:
            parser.error("--gate and --result required")
        gate, result = args.gate, args.result.upper()
        out = {"gate": gate, "result": result}
        if result == "PASS":
            reset_retry(gate)
            move(PASS_NEXT[gate], "%s PASS" % gate, "gate_pass")
            out["next_state"] = PASS_NEXT[gate]
        else:
            count = increment_retry(gate, args.reason or "%s FAIL" % gate)
            escalate = count >= LIMITS[gate]
            if escalate:
                reason = "%s retry_count %s >= %s" % (gate, count, LIMITS[gate])
                st.setdefault("escalation_history", []).append(
                    {"triggered_at": now(), "trigger_reason": reason, "resolved_at": None,
                     "resolution": None})
                st["current_state"] = "ESCALATION"
                st["updated_at"] = now()
                st["escalation_provenance"] = {
                    "session_id": "unknown", "at": now(), "reason": reason, "rule_id": "R-9.1",
                    "source": "gate_retry_budget:%s" % gate}
                persist()
                enabled = os.environ.get("SDD_ENABLE_AUTO_RECOVERY", "").strip().lower()
                if (enabled == "" or enabled in ("1", "true", "yes", "on")) and gate in RESUMABLE:
                    move("AUTO_RECOVERY_ATTEMPT", reason, "auto_recovery")
                    out["auto_recovery"] = {"entered": True}
            else:
                try:
                    move(FAIL_NEXT[gate], "%s FAIL (retry %s) - %s" % (gate, count, args.reason),
                         "gate_fail")
                except RuntimeError as exc:
                    trace(st["current_state"], st["current_state"],
                          "gate_fail transition rejected: %s -> %s: %s" % (
                              gate, FAIL_NEXT[gate], exc), "gate_fail_blocked")
                    persist()
            out["retry_count"] = count
            out["next_state"] = st["current_state"]
            if escalate:
                out["escalated"] = True
        print(json.dumps(out, ensure_ascii=False))
    elif VERB == "spec-refreeze":
        if not args.reason.strip():
            fail("invalid_argument", "spec-refreeze requires a non-blank --reason", 4)
        if not args.doc:
            fail("invalid_argument", "spec-refreeze requires at least one --doc", 4)
        if cur not in ("SPEC_AUDIT", "RELEASE_READY", "RELEASE"):
            conflict("one of ['RELEASE', 'RELEASE_READY', 'SPEC_AUDIT']")
        if not st.get("frozen_stages"):
            conflict("an existing frozen stage")
        digests = digests_of(args.root, args.doc)
        prev = st["frozen_stages"][-1]
        st["frozen_stages"].append({
            "stage": prev.get("stage"), "frozen_at": now(), "spec_docs": list(digests),
            "spec_doc_digests": digests, "approved_by": args.approver, "kind": "refreeze",
            "supersedes": prev.get("frozen_at"), "reason": args.reason})
        trace(cur, cur, args.reason, "spec_refreeze")
        persist()
        emit({"ok": True, "verb": VERB, "project": args.project, "from_state": cur,
              "current_state": cur, "refrozen": True, "stage": prev.get("stage"),
              "spec_doc_digests": digests})
    elif VERB == "resume-from-escalation":
        if not args.to or args.to not in RESUME_TARGETS:
            parser.error("--to must be one of %s" % sorted(RESUME_TARGETS))
        if not args.reason.strip():
            parser.error("--reason required")
        if cur not in ("ESCALATION", "ESCALATION_FINAL"):
            print(json.dumps({"noop": True, "reason": "state=%s is not an escalation state" % cur}))
            sys.exit(0)
        move("RESUME_VERIFICATION", args.reason, "human_resume")
        move(args.to, args.reason, "human_resume")
        history = st.get("escalation_history") or []
        if history and history[-1].get("resolved_at") is None:
            history[-1]["resolved_at"] = now()
            history[-1]["resolution"] = "human_resume -> %s: %s" % (args.to, args.reason)
        persist()
        print(json.dumps({"from": cur, "via": "RESUME_VERIFICATION", "to": args.to,
                          "resolved_at": now()}))
    else:  # spec-frozen --stage Gate-0*
        if cur not in ("HUMAN_PENDING", "SPEC_REGRESSION_CHECK"):
            conflict("HUMAN_PENDING")
        if not args.digest or not args.doc or not args.root:
            fail("invalid_argument", "--digest, --doc and --root are required", 4)
        digests = digests_of(args.root, args.doc)
        st.setdefault("frozen_stages", []).append({
            "stage": args.stage, "frozen_at": now(), "compaction_report": None,
            "spec_docs": list(digests), "spec_doc_digests": digests,
            "approved_by": args.approver})
        cum = st.setdefault("cumulative_history", {})
        cum["total_spec_frozen_count"] = int(cum.get("total_spec_frozen_count", 0)) + 1
        for gate in ("SCG_VALIDATION", "PR_REVIEW", "RTM_VERIFY", "RELEASE_READY"):
            reset_retry(gate)
        move("SPEC_FROZEN", args.reason or "Stage frozen: %s" % args.stage, "spec_frozen")
        emit({"ok": True, "verb": VERB, "project": args.project, "from_state": cur,
              "current_state": "SPEC_FROZEN", "stage": args.stage, "spec_doc_digests": digests})
    sys.exit(0)


if VERB in ("show", "transition", "gate", "spec-refreeze", "resume-from-escalation") or (
        VERB == "spec-frozen" and (args.stage or "").startswith("Gate-0")):
    research_main()


cur = st["current_state"]
if VERB == "spec-frozen":
    if cur != "HUMAN_PENDING":
        conflict("HUMAN_PENDING")
    if not args.stage:
        fail("invalid_argument", "--stage is required", 4)
    digests = {}
    docs = []
    if args.digest:
        base = Path(args.root).resolve() if args.root else None
        if base is None:
            fail("invalid_argument", "--root is required with --digest", 4)
        for item in args.doc:
            target = (base / item).resolve()
            try:
                target.relative_to(base)
            except ValueError:
                fail("doc_outside_root", item, 4)
            if not target.is_file():
                fail("doc_not_found", item, 4)
            try:
                text = target.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                fail("doc_not_utf8", item, 4)
            rel = target.relative_to(base).as_posix()
            docs.append(rel)
            digests[rel] = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    else:
        docs = list(args.doc)
    entry = {"stage": args.stage, "frozen_at": now(), "compaction_report": None, "spec_docs": docs}
    if digests:
        entry["spec_doc_digests"] = digests
        entry["approved_by"] = args.approver
    st.setdefault("frozen_stages", []).append(entry)
    save("SPEC_FROZEN", "spec_frozen", args.reason or "Stage frozen: %s" % args.stage)
    extra = {"stage": args.stage}
    if digests:
        extra["spec_doc_digests"] = digests
    ok(cur, **extra)
elif VERB == "negotiate-enter":
    if cur == "TEST_CONTRACT_NEGOTIATED":
        ok(cur, noop=True, entered=False)
    if cur != "SPEC_FROZEN":
        conflict("SPEC_FROZEN")
    save("TEST_CONTRACT_NEGOTIATED", "test_contract_enter", args.reason)
    ok(cur, entered=True, **{"from": cur, "to": "TEST_CONTRACT_NEGOTIATED"})
elif VERB == "negotiate-exit":
    if args.outcome is None:
        fail("invalid_argument", "--outcome is required", 4)
    if cur != "TEST_CONTRACT_NEGOTIATED":
        conflict("TEST_CONTRACT_NEGOTIATED")
    to = "IMPLEMENTATION" if args.outcome == "agreed" else "SPEC_DRAFTING"
    save(to, "test_contract_exit", args.reason)
    ok(cur, exited=True, outcome=args.outcome, to=to)
elif VERB == "delegate-enter":
    if cur == "AUTOCLAUDE_DELEGATED":
        ok(cur, noop=True, entered=False)
    if cur != "IMPLEMENTATION":
        conflict("IMPLEMENTATION")
    tracking = {"entered_at": now(), "resume_state": "IMPLEMENTATION"}
    if args.playbook_ref:
        tracking["playbook_ref"] = args.playbook_ref
    st["autoclaude_delegated_tracking"] = tracking
    save("AUTOCLAUDE_DELEGATED", "autoclaude_delegated_enter", args.reason)
    ok(cur, entered=True, **{"from": cur, "to": "AUTOCLAUDE_DELEGATED"})
else:
    if args.decision is None:
        fail("invalid_argument", "--decision is required", 4)
    if cur != "AUTOCLAUDE_DELEGATED":
        conflict("AUTOCLAUDE_DELEGATED")
    if args.decision == "failed":
        st.setdefault("escalation_history", []).append(
            {"triggered_at": now(), "trigger_reason": args.reason, "resolved_at": None,
             "resolution": None})
        st["escalation_provenance"] = {
            "session_id": "unknown", "at": now(), "reason": args.reason, "rule_id": "unknown",
            "source": "autoclaude_delegated_failed"}
        save("ESCALATION", "autoclaude_delegated_exit", args.reason)
        ok(cur, exited=True, decision="failed", to="ESCALATION")
    save("IMPLEMENTATION", "autoclaude_delegated_exit", args.reason)
    ok(cur, exited=True, decision="done", to="IMPLEMENTATION")
'''


def make_fake_sdd(parent: Path, name: str = FAKE_VERSION_DIR) -> Path:
    """在 `parent/name` 造假 SDD 版本目錄，回傳它。"""
    root = parent / name
    cli_dir = root / "tools" / "fsm_runtime"
    cli_dir.mkdir(parents=True, exist_ok=True)
    (root / "tools" / "__init__.py").write_text("", encoding="utf-8")
    (cli_dir / "__init__.py").write_text("", encoding="utf-8")
    (cli_dir / "fsm_runtime.py").write_text(_FAKE_CLI, encoding="utf-8", newline="\n")
    return root


def read_calls(sdd_root: Path) -> list[dict[str, Any]]:
    path = sdd_root / "fake_calls.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def set_control(sdd_root: Path, **control: Any) -> None:
    (sdd_root / "fake_control.json").write_text(json.dumps(control), encoding="utf-8")


def state_path(state_dir: Path, project: str) -> Path:
    return state_dir / f"FSM-STATE-{project}.yaml"


def seed_state(state_dir: Path, project: str, current_state: str = "HUMAN_PENDING",
               **fsm: Any) -> Path:
    """測試端直接放一份狀態檔（扮演「人在 SDD session 把專案推到某個狀態」）。形狀照真檔。"""
    state_dir.mkdir(parents=True, exist_ok=True)
    body: dict[str, Any] = {
        "project": project, "session_id": "sid-fake", "created_at": "2026-10-17T00:00:00+00:00",
        "updated_at": "2026-10-17T00:00:00+00:00", "current_state": current_state,
        "current_sprint": 1, "decision_trace": [], "frozen_stages": [], "escalation_history": [],
        "human_pending_tracking": {"entered_at": None, "reminder_sent_at": None,
                                   "reminder_hours": 72, "escalation_hours": 168},
        "retry_history": {"SCG_VALIDATION": {"current_count": 0, "max_limit": 3, "history": []}},
    }
    body.update(fsm)
    path = state_path(state_dir, project)
    path.write_text(yaml.safe_dump({"fsm_state": body}, allow_unicode=True, sort_keys=False),
                    encoding="utf-8")
    return path


def read_state(state_dir: Path, project: str, *, retries: int = 20) -> dict[str, Any]:
    """讀狀態檔。假 CLI 寫檔不是原子的，測試端的直接讀取可能撞上寫到一半：短暫重試。"""
    for attempt in range(retries):
        try:
            doc = yaml.safe_load(state_path(state_dir, project).read_text(encoding="utf-8"))
            return doc["fsm_state"]
        except (OSError, yaml.YAMLError, KeyError, TypeError):
            if attempt == retries - 1:
                raise
            time.sleep(0.05)
    raise AssertionError("unreachable")
