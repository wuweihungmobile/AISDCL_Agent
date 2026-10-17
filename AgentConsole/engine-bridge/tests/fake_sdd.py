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
                                     "delegate-enter", "delegate-exit"])
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
