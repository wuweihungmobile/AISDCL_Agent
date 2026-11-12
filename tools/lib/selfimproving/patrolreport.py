"""SelfImproving 巡邏快照：每心跳原子覆寫 `<si>/console_report/patrol.json`
（TCS-SelfImproving-P7 §2.2；AC-SI-47-8～47-11、47-15）。

能力類別 `rw`：寫入只限 `<si>/console_report/`（同目錄 tmp 檔寫完→`os.replace`）與
`<si>/push/commits.jsonl`（O_APPEND 追加）；不 import
`runner`／`patrol`／`patrolrun`（存活判斷由呼叫端以 `alive` 注入）。快照是**無狀態**的現況描述：
每心跳整份重算、主機端從不讀回，只影響 Console 的顯示；寫入失敗只記日誌、不改心跳 rc。白話一律經
`nextstep`。
`push` 區塊依 §2.3 的 `push/` 檔案契約與附錄 A.4b 判定序組出；守門結果由 `push_inputs` 供給
（`pushguard.evaluate`）；巡邏提交紀錄 `commits.jsonl` 由 `record_commit` 追加（本檔唯一寫
入 `push/` 的處）。
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from . import check as si_check
from . import events as si_events
from . import nextstep, pushguard, sched

SCHEMA_REV = 1
COMMITS_NAME = "commits.jsonl"  # `<si>/push/` 內：巡邏提交紀錄（只由 `record_commit` 追加）
REPORT_MAX_BYTES = 524288
LIST_MAX = 200
TEXT_MAX = 120
REPORT_DIR, REPORT_NAME = "console_report", "patrol.json"
_LISTED = ("proposed", "returned", "approved", "sandboxed", "verified")
_POST = ("promoted", "measuring", "closed")
_NEVER = ("PUSH-HOOK-FAILED", "PUSH-REJECTED", "PUSH-AUTH")
_RETRY = ("PUSH-WALL-EXCEEDED", "PUSH-FAILED")
_BLOCKED = ("PUSH-REMOTE-DRIFT", "PUSH-REMOTE-DIVERGED")  # `push/blocked.json` 的碼
_NOTE_TOTAL = 130  # 帶 runner_note 後 push.text 的總長上限
_PUSH_KEYS = ("enabled", "state", "code", "text", "retry", "sha", "ahead", "attempts",
              "finished_at", "tick_at")


def _t(value) -> datetime | None:
    try:
        out = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return out if out.tzinfo is not None else None


def is_stale(report: dict, now: datetime) -> bool:
    """`now − generated_at > 2×heartbeat_minutes＋5 分`（嚴格大於）；缺欄或非 ISO＝True
    （fail-closed）；`now` 為 naive＝`ValueError`。"""
    sched.aware(now)
    gen = _t(report.get("generated_at") if isinstance(report, dict) else None)
    hb = report.get("heartbeat_minutes") if isinstance(report, dict) else None
    if gen is None or not isinstance(hb, int) or isinstance(hb, bool):
        return True
    return now - gen > timedelta(minutes=2 * hb + 5)


def _text(code: str, detail=None, *, step: bool = False) -> str:
    return sched.line1(nextstep.reason(code, detail or None, step=step).text, TEXT_MAX)


def _read_json(path: Path) -> dict | None:
    try:
        obj = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


# ── 各區塊 ────────────────────────────────────────────────────────────────────────
def _schedule(ctx, events: list[dict], steps: list[dict]) -> dict:
    st = sched.state_of(events, ctx.params["sched_period_minutes_default"])
    info = getattr(ctx, "due_info", None)
    broken = any(s["step"] == "到期" and s.get("exc") for s in steps)
    current = None if info is None or broken else {"code": info[0],
                                                   "text": _text(info[0], info[1])}
    skip = next((e for e in reversed(events) if e["kind"] == "sched.skip"), None)
    last = None
    if skip is not None:
        code = "SKIP-" + skip["reason"].upper()
        last = {"seq": skip["seq"], "t": skip["t"], "code": code,
                "text": _text(code, skip["detail"]), "audit_ref": skip.get("audit_ref")}
    return {"enabled": st.enabled, "current": current, "last_skip": last}


def _ingest(ctx) -> list[dict]:
    out = []
    for ref, kind, code in ctx.ingest_rows:
        r = nextstep.reason(code)
        out.append({"audit_ref": ref, "kind": kind, "status": "rejected" if r.permanent
                    else "deferred", "code": code, "text": _text(code),
                    "permanent": r.permanent})
    return out


def _props(ctx, events: list[dict], f) -> list[dict]:
    out = []
    for p in f.props.values():
        note = ctx.notes.get(p.id)
        cooling = p.state == "rejected" and any(c["prop"] == p.id for c in f.cooldowns)
        if not (note or p.state in _LISTED or cooling
                or (p.state in _POST and p.pending_rollbacks >= 1)):
            continue
        if note:
            r = nextstep.reason(note[0], note[1] or None, step=True)
            code, who, text = note[0], r.who, _text(note[0], note[1], step=True)
        else:
            n = nextstep.of(f, p, ctx.params, events)
            code, who, text = n["code"], n["who"], sched.line1(n["text"], TEXT_MAX)
        out.append({"id": p.id, "state": p.state, "code": code, "who": who, "text": text})
    return out


def _runs(ctx, events: list[dict], pending: list[str], alive) -> dict:
    opened = {e["run"]: e for e in events if e["kind"] == "run.open"}
    live = []
    for path in sorted((ctx.si / "patrol").glob("RUN-SI-*/spawn.json")):
        data, run = _read_json(path), path.parent.name
        if data is None or "closed_at" in data:
            continue
        wall = _t(data.get("wall_due_at"))
        try:
            running = wall is not None and ctx.now < wall and alive(data["pid"],
                                                                    data["started_at"])
        except (KeyError, TypeError, ValueError):
            running = False
        if not running:
            continue
        e = opened.get(run, {})
        purpose = ("scheduled" if e.get("trigger") == "f" else
                   "console" if e.get("trigger") == "a" and e.get("carrier") == "console"
                   else "manual")
        live.append({"run": run, "purpose": purpose, "started_at": data["started_at"],
                     "wall_due_at": data["wall_due_at"]})
    waiting = [{"run": run, "code": ctx.run_notes[run][0],
                "text": _text(*ctx.run_notes[run])} for run in pending if run in ctx.run_notes]
    return {"live": live, "waiting": waiting, "queued": []}


def push_inputs(ctx, alive=None) -> dict:
    """本心跳的推送守門結果 `{ahead:int, head:str|None, code:str|None, detail:str|None}`，供 `push`
    區塊；一個心跳只呼叫一次 `pushguard.evaluate`。放行與「無事可推」（`PUSH-OFF`、
    `PUSH-NOT-AHEAD`）的 `code` 為 None——這兩態由 `push_block` 依 `enabled`／`ahead` 判。"""
    got = pushguard.evaluate(ctx.repo, ctx.params, ctx.si, ctx.now, alive=alive, events=ctx.load())
    code = None if got["ok"] or got["code"] in ("PUSH-OFF", "PUSH-NOT-AHEAD") else got["code"]
    return {"ahead": got["ahead"], "head": got["head"], "code": code, "detail": got["detail"]}


def record_commit(si: Path, sha: str | None, app: str, prop: str, now: datetime) -> None:
    """巡邏提交成功後追加一行 `<si>/push/commits.jsonl`（`{sha,app,prop,at}`；O_APPEND 單行、LF；
    §2.3）。只有 `patrolrun._commit` 呼叫；沒有補寫機制（寫失敗＝該提交不可自動推送）。`sha` 須為
    完整 40 碼（`git rev-parse HEAD` 失敗傳進來的 None 亦拒）；一切失敗皆為 `OSError`。"""
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise OSError("sha 不是完整的 40 碼（rev-parse HEAD 失敗？）")
    folder = si / "push"
    folder.mkdir(parents=True, exist_ok=True)
    row = {"sha": sha, "app": app, "prop": prop, "at": sched.iso(sched.aware(now))}
    data = (json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    fd = os.open(folder / COMMITS_NAME, os.O_WRONLY | os.O_APPEND | os.O_CREAT
                 | getattr(os, "O_BINARY", 0), 0o644)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)


def _latest_ok(results: Path) -> dict | None:
    best = None
    for path in sorted(results.glob("*.json")):
        r = _read_json(path)
        if r and r.get("code") == "PUSH-OK" and (
                best is None or str(r.get("finished_at")) > str(best.get("finished_at"))):
            best = r
    return best


def push_block(home: Path, params: dict, now: datetime, enabled: bool, guard: dict | None,
               alive) -> dict:
    """`push` 區塊（十鍵；判定序＝TCS-P7 附錄 A.4b，先中者定案）。`alive(pid, started_at)` 注入。"""
    d = home / "push"
    cur, err, tick = (_read_json(d / n) for n in ("current.json", "last_error.json", "tick.json"))
    ahead = int(guard["ahead"]) if guard else 0
    head = guard.get("head") if guard else None
    last = _read_json(d / "results" / f"{head[:12]}.json") if head else None
    tick_at = tick.get("tick_at") if tick else None
    out = {"enabled": enabled, "state": "", "code": "", "text": "", "retry": None, "sha": None,
           "ahead": ahead, "attempts": int(last["attempts"]) if last else 0,
           "finished_at": last.get("finished_at") if last else None, "tick_at": tick_at}

    def done(state, code, detail=None, retry=None, sha=None):
        text = _text(code, detail)
        note = (last or {}).get("runner_note") if state == "failed" else None
        if note and isinstance(note, str):  # runner 的終止／Job 說明接在白話句後（總長 ≤130）
            text = sched.line1(f"{text}（備註：{nextstep.clip(note, 40)}）", _NOTE_TOTAL)
        out.update(state=state, code=code, text=text, retry=retry, sha=sha)
        return out
    if not enabled:
        return done("off", "PUSH-OFF")
    wall = _t(cur.get("wall_due_at")) if cur else None
    try:
        running = cur is not None and wall is not None and now < wall and alive(
            cur["pid"], cur["started_at"])
    except (KeyError, TypeError, ValueError):
        running = False
    if running:
        return done("running", "PUSH-RUNNING", sha=cur.get("sha"))
    if guard is None:
        return done("blocked", "PUSH-GIT-UNAVAILABLE")
    if ahead == 0:
        ok = _latest_ok(d / "results")
        out.update(attempts=int(ok["attempts"]) if ok else 0,
                   finished_at=ok.get("finished_at") if ok else None)
        return done("ok", "PUSH-OK", sha=ok.get("sha") if ok else None) if ok else done(
            "idle", "PUSH-NOT-AHEAD")
    if guard.get("code"):
        return done("blocked", guard["code"], guard.get("detail"), sha=head)
    fresh = _t(tick_at)
    limit = timedelta(minutes=2 * params["sched_heartbeat_minutes"] + 5)
    blk = _read_json(d / "blocked.json")
    if (blk and blk.get("head") == head and blk.get("code") in _BLOCKED  # HEAD 改變即自然失效
            and fresh is not None and now - fresh <= limit):  # push-run 仍在跑，否則視為過期（4b）
        return done("blocked", blk["code"], blk.get("detail"), sha=head)
    code, fin = (last or {}).get("code"), _t((last or {}).get("finished_at"))
    mx, gap = params.get("sched_push_attempts_max"), params.get("sched_push_retry_minutes")
    if code in _NEVER:
        return done("failed", code, retry="never", sha=head)
    if code in _RETRY:
        if isinstance(mx, int) and out["attempts"] >= mx:
            return done("failed", code, retry="exhausted", sha=head)
        if fin is not None and isinstance(gap, int) and now - fin < timedelta(minutes=gap):
            return done("failed", code, retry="wait", sha=head)
    if err is not None and (fin is None or (_t(err.get("at")) or fin) > fin):
        return done("failed", "PUSH-INTERNAL-ERROR", err.get("text"), sha=head)
    if fresh is not None and now - fresh <= limit:
        return done("pending", "PUSH-PENDING", sha=head)
    return done("waiting-login", "PUSH-WAITING-LOGIN", sha=head)


# ── 組裝與寫入 ────────────────────────────────────────────────────────────────────
def _ledger_seq(events: list[dict]) -> int:
    return max((e["seq"] for e in events), default=0)


def build(ctx, steps: list[dict], pending: list[str], alive) -> dict:
    """本心跳的快照（鍵序固定，欄位契約＝TCS-P7 §2.2）。"""
    events, f = ctx.load(), ctx.fold()
    enabled = ctx.params.get("sched_auto_push") is True
    report = {
        "schema_rev": SCHEMA_REV, "generated_at": sched.iso(ctx.now), "off": False,
        "heartbeat_minutes": ctx.params["sched_heartbeat_minutes"],
        "ledger_seq": _ledger_seq(events), "truncated": False,
        "steps": [{"step": s["step"], "result": sched.line1(s["result"], TEXT_MAX)}
                  for s in steps],
        "schedule": _schedule(ctx, events, steps), "ingest": _ingest(ctx),
        "props": _props(ctx, events, f), "runs": _runs(ctx, events, pending, alive),
        "push": push_block(ctx.si, ctx.params, ctx.now, enabled, push_inputs(ctx, alive), alive)}
    return _cap(report)


def _cap(report: dict) -> dict:
    """`ingest`、`props` 各截至前 `LIST_MAX` 筆；仍超過 `REPORT_MAX_BYTES` 時逐次減半。"""
    for key in ("ingest", "props"):
        if len(report[key]) > LIST_MAX:
            report[key], report["truncated"] = report[key][:LIST_MAX], True
    while len(dump(report)) > REPORT_MAX_BYTES and (report["ingest"] or report["props"]):
        for key in ("ingest", "props"):
            report[key] = report[key][:len(report[key]) // 2]
        report["truncated"] = True
    return report


def off_report(now: datetime, heartbeat: int, ledger_seq: int, enabled: bool) -> dict:
    """`AUTOSDD_SI_PATROL_OFF` 時的快照：`off:true`、其餘陣列皆空、`push.state:"off"`。"""
    push = {"enabled": enabled, "state": "off", "code": "PUSH-OFF", "text": _text("PUSH-OFF"),
            "retry": None, "sha": None, "ahead": 0, "attempts": 0, "finished_at": None,
            "tick_at": None}
    return {"schema_rev": SCHEMA_REV, "generated_at": sched.iso(now), "off": True,
            "heartbeat_minutes": heartbeat, "ledger_seq": ledger_seq, "truncated": False,
            "steps": [], "schedule": None, "ingest": [], "props": [],
            "runs": {"live": [], "waiting": [], "queued": []}, "push": push}


def dump(report: dict) -> bytes:
    """UTF-8 無 BOM、LF、結尾恰一個 LF（簡潔分隔、鍵序即組裝序）。"""
    return (json.dumps(report, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def write(si: Path, report: dict) -> None:
    """原子覆寫：同目錄 tmp 檔寫完→`os.replace`；`OSError` 一律清掉 tmp 後原樣拋出（舊檔不變）。"""
    folder = si / REPORT_DIR
    tmp = folder / f".{REPORT_NAME}.{os.getpid()}.tmp"
    try:
        folder.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(dump(report))
        os.replace(tmp, folder / REPORT_NAME)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def emit(ctx, steps: list[dict], pending, alive) -> None:
    """心跳之後寫快照（**不是第六步**：不進 stdout 與 `--json` 的 steps）。`pending` 為取待啟動運轉
    的呼叫；`--dry-run` 不寫；任何失敗只記日誌 `REPORT-WRITE-FAILED`、不改心跳 rc。"""
    if ctx.dry:
        return
    try:
        write(ctx.si, build(ctx, steps, pending(ctx), alive))
    except Exception as exc:  # noqa: BLE001  # 快照是顯示用的盡力而為，不得讓它改變心跳結果
        ctx.log("巡視", 0, "REPORT-WRITE-FAILED", f"快照寫入失敗：{type(exc).__name__}")


def emit_off(repo: Path, si: Path, now: datetime, log) -> None:
    """OFF 路徑：不取鎖、不呼叫守門、寫入成功不加日誌行（只失敗才經 `log` 記一行）。"""
    try:
        params = si_check.params_for(repo, "sched_heartbeat_minutes")
        events = si_events.load_sound_events(repo / si_events.LEDGER_REL) or []
        write(si, off_report(now, params["sched_heartbeat_minutes"], _ledger_seq(events),
                             params.get("sched_auto_push") is True))
    except Exception as exc:  # noqa: BLE001  # 同 emit
        log(si, now, "巡視", 0, "REPORT-WRITE-FAILED", f"快照寫入失敗：{type(exc).__name__}")


__all__ = ["SCHEMA_REV", "REPORT_MAX_BYTES", "is_stale", "push_block", "push_inputs",
           "record_commit", "build",
           "emit", "emit_off", "write", "dump", "off_report"]
