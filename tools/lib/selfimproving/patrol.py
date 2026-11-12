"""SelfImproving 巡邏器：一次性心跳（TCS-SelfImproving-P4 R148～R157、R166、R167）。

能力類別 `exec`。一次心跳依序：巡視進行中的無人運轉（步 0′）→入帳→到期判定→運轉→推進後退出；
不常駐、不等待無人主控（spawn 為脫離式）。外部行程只經 `runner`／`git`；對 CLI 動詞的呼叫集合
（`verbs`）⊆ R154 的可做集合：不 `decide`（入帳 Console 決定不是代決）、不 push、不用旁路旗標、
不全量暫存。環境變數 `AUTOSDD_SI_PATROL_OFF` 非空＝整次 no-op；有設無人值守＝rc 1。
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# `resume_route` 以頂層名 import 同層的 endurance_env，故先把 tools/lib 與 tools 放進 sys.path
# （兩句都寫成可靜態解析的形態：AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py
# 的 R67 鎖對迴圈變數形態 `sys.path.insert(0, _p)` 會判「無法解析」而紅）
_LIB = str(Path(__file__).resolve().parents[1])
_TOOLS = str(Path(__file__).resolve().parents[2])
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

from lib import apply_lock  # noqa: E402

from . import check as si_check  # noqa: E402
from . import (  # noqa: E402  # noqa: E402
    consoleaudit,
    evwrite,
    patrolreport,
    patrolrun,
    runner,
    sched,
    schedwrite,
    status,
    unattended,
)
from . import events as si_events  # noqa: E402
from . import fold as si_fold  # noqa: E402
from . import params as si_params  # noqa: E402
from . import writeverbs as wv  # noqa: E402
from .git import Git  # noqa: E402

OFF_ENV = "AUTOSDD_SI_PATROL_OFF"


@dataclass
class Deps:
    """依賴注入包（缺省＝真依賴）：`quota(now)`→帶 `.band` 的物件；`driver_quiet()`→True＝無人
    在開車；`verbs(argv)`→(rc, out, err)；`spawn_detached`、`pid_alive(pid, started_at)`、
    `kill_tree(pid)`。"""

    quota: Callable | None = None
    driver_quiet: Callable | None = None
    which: Callable | None = None
    preflight: Callable | None = None
    verbs: Callable | None = None
    spawn_detached: Callable | None = None
    pid_alive: Callable | None = None
    kill_tree: Callable | None = None


def _entry():
    """入口薄殼 tools/selfimproving.py，以檔案路徑載入、不靠名字：入口以腳本執行時上面把 tools/lib
    排在 tools 前，名字 `selfimproving` 先解析到同名套件 tools/lib/selfimproving/（2026-11-09 OS
    任務真機首跳起每心跳入帳 AttributeError；TCS-P4 D-IMP-9）。"""
    mod = sys.modules.get("selfimproving")
    if getattr(mod, "main", None) is None:
        path = Path(_TOOLS) / "selfimproving.py"
        spec = importlib.util.spec_from_file_location("selfimproving", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules["selfimproving"] = mod
    return mod


def _real_verbs(argv: list[str]) -> tuple[int, str, str]:
    entry = _entry()  # 入口薄殼：同一組動詞實作，行程內呼叫

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = entry.main(list(argv))
    return rc, out.getvalue(), err.getvalue()


def _quota(ctx) -> tuple[str, dict]:
    try:
        if ctx.deps.quota is not None:
            state = ctx.deps.quota(ctx.now)
        else:
            from lib import quota_policy  # 延遲：只有真讀額度才載入

            state = quota_policy.decide(sched.measured_state(ctx.now), ctx.now,
                                        quota_policy.DEFAULT_POLICY)
        return getattr(state, "band", "unmeasured"), sched.quota_verdict(state)
    except Exception:  # noqa: BLE001  # 量不到一律跳過（fail-closed）
        return "unmeasured", {"skip": True, "degrade": False}


class Ctx:
    def __init__(self, repo: Path, now: datetime, dry: bool, deps: Deps, params: dict) -> None:
        self.repo, self.now, self.dry, self.deps, self.params = repo, now, dry, deps, params
        self.si, self.environ = si_events.si_dir(), os.environ
        self.band, self.degrade = "unmeasured", False
        self.drafts: list[str] = []
        self._git = Git(repo)
        # 快照素材（TCS-P7 AC-SI-47-9／10／15）：只活一個心跳，由 `patrolreport` 讀、不進日誌
        self.notes, self.run_notes, self.ingest_rows, self.due_info = {}, {}, [], None

    def note(self, pid: str, code: str, detail: str = "") -> None:
        self.notes[pid] = (code, detail)

    def kill_skipped(self, run: str, pid: int) -> None:
        """逾牆但行程身分對不上：不殺，日誌一行，卡點記到該運轉的每個提案（快照 props[] 帶出）。"""
        self.log("巡視", 0, "RUN-KILL-SKIPPED", f"{run} pid={pid} 身分不符，不終止")
        for pid_ in getattr(self.fold().runs.get(run), "prop_ids", ()):
            self.note(pid_, "RUN-KILL-SKIPPED")

    def git(self) -> Git:
        return self._git

    def load(self) -> list[dict]:
        return si_events.load_sound_events(self.repo / si_events.LEDGER_REL) or []

    def fold(self):
        return si_fold.fold(self.load(), self.params.get("stop_after_bad"))

    def status_params(self) -> dict:
        return self.params

    def verb(self, *argv: str) -> tuple[int, str, str]:
        return (self.deps.verbs or _real_verbs)([*argv, "--repo", str(self.repo)])

    def spawn(self, argv, **kw) -> int:
        return (self.deps.spawn_detached or runner.spawn_detached)(argv, **kw)

    def log(self, step: str, rc: int, code: str | None, msg: str) -> None:
        if not self.dry:
            write_log(self.si, self.now, step, rc, code, msg)

    def logged(self, needle: str, code: str) -> bool:
        try:
            text = (self.si / "patrol" / "patrol.log").read_text(encoding="utf-8")
        except OSError:
            return False
        return any(needle in ln and f"code={code}" in ln for ln in text.splitlines())

    def draft(self, verb: str, code: str, why: str) -> str:
        row = " ".join(wv.draft_for(self.repo, verb, [(code, why)]).split())
        self.drafts.append(row)
        return row


def write_log(si: Path, now: datetime, step: str, rc: int, code: str | None, msg: str) -> None:
    """R157：`<ISO 帶 offset> step=<步驟> rc=<N> code=<碼或-> <一行說明>`。"""
    line = f"{sched.iso(now)} step={step} rc={rc} code={code or '-'} {sched.line1(msg, 400)}"
    path = si / "patrol" / "patrol.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")


# ── 步 1 入帳（R149）──────────────────────────────────────────────────────────────
def _audit_when(si: Path, ref: str) -> float:
    try:
        return datetime.fromisoformat(
            consoleaudit.parse(consoleaudit.audit_path(si, ref)).body["time"]).timestamp()
    except (consoleaudit.AuditError, ValueError, KeyError):
        return float("inf")


def _ingest_argv(ctx: Ctx, kind: str | None, ref: str) -> list[str] | None:
    car = ["--carrier", "console", "--audit-ref", ref]
    if kind == "decide":
        try:
            body = consoleaudit.parse(consoleaudit.audit_path(ctx.si, ref)).body
            target = body.get("run") if body.get("dkind") == "resume" else body.get("prop")
        except consoleaudit.AuditError:
            target = None
        return ["decide", target or "PROP-SI-000", *car, "--by", "patrol"]
    return {"obs-add": ["obs-add", *car, "--by", "patrol"],
            "src-registry": ["registry-ingest", *car, "--by", "patrol"],
            "obs-close": ["obs-close", *car, "--by", "patrol"],
            "sched-set": ["sched", "set", *car, "--by", "patrol"],
            "run-request": ["run-open", "--trigger", "a", *car, "--coord",
                            f"console_audit/{ref}.json", "--by", "console"]}.get(kind or "")


def ingest(ctx: Ctx) -> str:
    pend = status.console_pending(ctx.load(), True)
    if pend["status"] != "read" and pend["reason"] == "home-unavailable":
        pend = {"status": "read", "count": 0, "items": []}  # 稽核目錄還不存在＝沒有待入帳檔
    if pend["status"] != "read":
        ctx.log("入帳", 0, None, f"console_pending 量不到（{pend['reason']}）")
        return f"量不到（{pend['reason']}）"
    items = sorted(pend["items"], key=lambda i: (_audit_when(ctx.si, i["audit_ref"]),
                                                i["audit_ref"]))
    if ctx.dry:
        return "將入帳 " + ("、".join(f"{i['kind']}:{i['audit_ref']}" for i in items) or "無")
    done = bad = new_bad = 0
    for it in items:
        ref, kind = it["audit_ref"], it["kind"]
        argv = _ingest_argv(ctx, kind, ref)
        rc, out, err = ctx.verb(*argv) if argv else (1, "", "")
        if rc == 0:
            done += 1
            continue
        bad += 1
        code = patrolrun.first_code(out, err) if argv else "AUDIT-KIND-UNKNOWN"
        ctx.ingest_rows.append((ref, kind, code))  # 無狀態：每心跳重列，不受日誌去重影響
        if not ctx.logged(ref, code):
            new_bad += 1
            row = ctx.draft("patrol-ingest", code, f"{kind} 入帳被拒")
            ctx.log("入帳", rc or 1, code, f"{ref} {kind} 入帳被拒；稽核檔保留；obs-draft: {row}")
    if not new_bad:
        ctx.log("入帳", 0, None, f"入帳 {done} 件；已知拒收 {bad} 件（日誌已記）")
    return f"入帳 {done}、拒收 {bad}"


# ── 步 2 到期判定、步 3 運轉（R143、R144、R150、R166）──────────────────────────────
def _inputs(ctx: Ctx, events: list[dict], exclude: str | None) -> sched.Inputs:
    p = ctx.params
    ctx.band, verdict = _quota(ctx)
    ctx.degrade = verdict["degrade"]
    quiet = (ctx.deps.driver_quiet() if ctx.deps.driver_quiet
             else not sched.other_driver(ctx.repo, ctx.now, p))
    dirty = sched.dirty_paths(ctx.repo)
    opened = sched.open_runs(events, exclude)
    problem = sched.spawn_problem(ctx.repo, which=ctx.deps.which, preflight=ctx.deps.preflight)
    return sched.Inputs(
        enabled=True, blackout=sched.in_blackout(ctx.now, p), quota_skip=verdict["skip"],
        other_driver=not quiet, dirty=bool(dirty), run_open=bool(opened), spawn_problem=problem,
        details={"blackout": f"本機時分 {sched.local_hm(ctx.now)} 落在黑窗 "
                              f"{p['sched_blackout_local']}",
                 "quota-band": f"額度帶 {ctx.band}",
                 "other-driver": f"近 {p['sched_driver_quiet_minutes']} 分鐘內有對話記錄",
                 "dirty-tree": f"工作樹有非 SI 自有改動：{', '.join(dirty[:3])}",
                 "run-open": f"已有未關運轉 {'、'.join(opened)}", "spawn-failed": problem or ""})


def _origin_line(repo: Path, seq: int) -> int:
    raw = (repo / si_events.LEDGER_REL).read_bytes().decode("utf-8")
    for no, ln in enumerate(raw.split("\n"), 1):
        try:
            if ln.strip() and json.loads(ln).get("seq") == seq:
                return no
        except ValueError:
            continue
    return 1


def due(ctx: Ctx) -> tuple[str, str | None]:
    """回（結果, 到期的格起點或 None）；原因成立時寫 `sched.skip`（同格同因一筆）。"""
    events = ctx.load()
    st = sched.state_of(events, ctx.params["sched_period_minutes_default"])
    cell = sched.cell_bounds(st, ctx.now)
    if not st.enabled or cell is None:
        ctx.due_info = ("SCHED-DISABLED", "")
        ctx.log("到期", 0, None, "排程停用或無日曆格，不嘗試")
        return "停用", None
    if sched.cell_events(events, "run.open", cell, trigger="f"):
        ctx.due_info = ("SCHED-CELL-RAN", "")
        ctx.log("到期", 0, None, "本格已有 (f) 運轉")
        return "本格已執行", None
    inp = _inputs(ctx, events, None)
    reason = sched.decide_skip(inp)
    if reason is None:
        ctx.due_info = ("SCHED-DUE", "")
        ctx.log("到期", 0, None, f"本格 {sched.iso(cell[0])} 到期，七種跳過皆不成立")
        return "到期", sched.iso(cell[0])
    detail = (inp.details or {}).get(reason, reason)
    ctx.due_info = ("SKIP-" + reason.upper(), detail)  # 快照 schedule.current（TCS-P7 AC-SI-47-15）
    wrote = None if ctx.dry else schedwrite.append_skip(ctx.repo, ctx.now, reason, detail,
                                                        ctx.params)
    note = "（已記 sched.skip）" if wrote else "（同格同因已記）"
    ctx.log("到期", 0, reason, f"{reason}：{detail}{note}")
    return f"跳過 {reason}", None


def _pending(ctx: Ctx) -> list[str]:
    """已開、尚未 spawn 的巡邏器運轉：(f)＝by patrol；Console (a)＝帶 console 載體；有研究事件
    卻無任務目錄者視為他人處理中、不接手。"""
    f, out = ctx.fold(), []
    for e in ctx.load():
        run = f.runs.get(e.get("run", "")) if e["kind"] == "run.open" else None
        if run is None or run.closed_seq is not None:
            continue
        mine = (e["trigger"] == "f" and e["by"] == "patrol") or (
            e["trigger"] == "a" and e.get("carrier") == "console")
        tdir = ctx.si / "patrol" / e["run"]
        if mine and not (tdir / "spawn.json").exists() and (tdir.exists() or run.research is None):
            out.append(e["run"])
    return out


def _start(ctx: Ctx, run: str, trigger: str, due_at: str, first_f: bool) -> str:
    state, why = patrolrun.launch(ctx, run, trigger=trigger, due_at=due_at)
    if state == "spawned":
        ctx.log("運轉", 0, None, why)
        return why
    ctx.log("運轉", 1, why.split(":")[0].split(" ")[0], f"{run} 未 spawn：{why}")
    ctx.run_notes[run] = ("SKIP-SPAWN-FAILED", why)
    if first_f:  # (f) 才記 sched.skip；(a) 只寫日誌、運轉保持開啟下一心跳再試
        schedwrite.append_skip(ctx.repo, ctx.now, "spawn-failed", why, ctx.params)
    return f"{run} 未 spawn（{why}）"


def launch_all(ctx: Ctx, cell_start: str | None, busy: bool) -> str:
    if cell_start is not None:
        if ctx.dry:
            return "將 run-open(f)→research→scan→任務書→脫離式 spawn"
        st = sched.state_of(ctx.load(), ctx.params["sched_period_minutes_default"])
        coord = f"{si_events.LEDGER_REL}:{_origin_line(ctx.repo, st.origin['seq'])}"
        rc, out, err = ctx.verb("run-open", "--trigger", "f", "--coord", coord, "--due-at",
                                cell_start, "--by", "patrol")
        m = re.search(r"id=(RUN-SI-\d+)", out)
        if rc != 0 or m is None:
            code = patrolrun.first_code(out, err)
            ctx.log("運轉", rc or 1, code, f"(f) run-open 被拒：{code}")
            return f"run-open 被拒（{code}）"
        return _start(ctx, m.group(1), "f", cell_start, True)
    notes, waiting = [], _pending(ctx)
    if busy:  # 同一時間至多一個進行中的無人運轉：其他運轉的 spawn 延後（只寫日誌）
        names = "、".join(waiting) or "無待啟動者"
        ctx.run_notes.update(dict.fromkeys(waiting, ("RUN-BUSY", "")))
        ctx.log("運轉", 0, "BUSY", f"已有進行中的無人運轉，延後 spawn：{names}")
        return "已有進行中的無人運轉，延後"
    for run in waiting:
        events = ctx.load()
        inp = _inputs(ctx, events, run)
        reason = sched.decide_skip(inp)
        if reason is not None:
            why = (inp.details or {})[reason]
            ctx.run_notes[run] = ("SKIP-" + reason.upper(), why)
            ctx.log("運轉", 0, reason, f"{run} 被擋（只寫日誌、運轉保持開啟）：{why}")
            notes.append(f"{run} 被擋（{reason}）")
            continue
        if ctx.dry:
            notes.append(f"{run} 將 spawn")
            continue
        first = next(e for e in events if e["kind"] == "run.open" and e["run"] == run)
        notes.append(_start(ctx, run, first["trigger"], first.get("due_at", "-"), False))
        break
    if not notes:
        ctx.log("運轉", 0, None, "無待啟動的運轉")
    return "、".join(notes) or "無待啟動的運轉"


# ── 心跳 ─────────────────────────────────────────────────────────────────────────
def heartbeat(ctx: Ctx) -> list[dict]:
    steps = []
    cur = "巡視"
    try:
        res, busy = patrolrun.watch(ctx)
        steps.append({"step": cur, "result": res})
        cur = "入帳"
        steps.append({"step": cur, "result": ingest(ctx)})
        cur = "到期"
        res, cell = due(ctx)
        steps.append({"step": cur, "result": res})
        cur = "運轉"
        steps.append({"step": cur, "result": launch_all(ctx, cell, busy)})
        cur = "推進"
        steps.append({"step": cur, "result": patrolrun.advance(ctx)})
    except Exception as exc:  # noqa: BLE001  # 未預期例外：寫日誌、rc 1、不重試
        ctx.log(cur, 1, "PATROL-EXCEPTION", f"未預期例外 {type(exc).__name__}：{exc}；不重試")
        steps.append({"step": cur, "result": f"PATROL-EXCEPTION {type(exc).__name__}", "exc": True})
    return steps


@contextlib.contextmanager
def _locked(ctx: Ctx):
    stack = contextlib.ExitStack()
    if not ctx.dry:
        try:
            lock = evwrite.ensure_home(ctx.si) / "patrol.lock"
            stack.enter_context(apply_lock.acquire(lock, 0, 7200))
        except evwrite.HomeUnwritable as exc:
            raise si_check.InputError(f"HOME-UNWRITABLE {exc}") from exc
        except apply_lock.LockBusyError:
            yield None
            return
    with stack:
        yield ctx


def run(repo: Path, now: datetime, dry: bool, as_json: bool, deps: Deps) -> tuple[int, str, str]:
    codes = unattended.gate("patrol", None, os.environ)
    if codes:
        out = wv.reject(repo, "patrol", codes, as_json)
        return out.rc, out.text, ""
    si = si_events.si_dir()
    if os.environ.get(OFF_ENV):
        if not dry:
            write_log(si, now, "巡視", 0, "PATROL-OFF", f"{OFF_ENV} 有設，整次 no-op")
            patrolreport.emit_off(repo, si, now, write_log)  # 只多一份 off:true 快照（不取鎖）
        return 0, f"{OFF_ENV} 有設：整次 no-op\n", ""
    params = si_check.params_for(repo, *si_params.SCHED_KEYS, "stop_after_bad", "event_max_bytes",
                                 "max_proposals_per_run")
    ctx = Ctx(repo, now, dry, deps, params)
    before = max((e["seq"] for e in ctx.load()), default=0)
    with _locked(ctx) as held:
        if held is None:
            return 0, "已有巡邏在跑\n", ""
        steps = heartbeat(ctx)
        patrolreport.emit(ctx, steps, _pending, ctx.deps.pid_alive or patrolrun._alive)
    new =[e["seq"] for e in ctx.load() if e["seq"] > before]
    failed = any(s.get("exc") for s in steps)
    if as_json:
        text = json.dumps({"ok": not failed, "kind": "patrol", "dry_run": dry, "steps": [
            {"step": s["step"], "result": s["result"], "detail": ""} for s in steps],
            "events": new}, ensure_ascii=False) + "\n"
    else:
        text = "".join(f"step={s['step']} result={s['result']}\n" for s in steps)
        text += ("obs-draft:\n" + "\n".join(ctx.drafts) + "\n") if ctx.drafts else ""
    return (1 if failed else 0), text, ""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str):
        sys.stderr.write(f"selfimproving: 用法錯誤：{message}\n")
        sys.exit(3)


def main(argv: list[str] | None = None, deps: Deps | None = None) -> int:
    """CLI 與測試共用：`patrol [--repo DIR] [--now ISO] [--dry-run] [--json]`。"""
    try:
        p = _Parser(prog="selfimproving patrol", allow_abbrev=False)
        p.add_argument("--repo")
        p.add_argument("--now")
        p.add_argument("--dry-run", dest="dry_run", action="store_true")
        p.add_argument("--json", action="store_true")
        args = p.parse_args(argv)
        repo = Path(args.repo) if args.repo else Path(__file__).resolve().parents[3]
        if not repo.is_dir():
            raise si_check.InputError(f"--repo 不是目錄：{repo}")
        try:
            now = datetime.fromisoformat(args.now) if args.now else datetime.now().astimezone()
            sched.aware(now)
        except ValueError as exc:
            raise si_check.InputError("--now 須為帶 offset 的 ISO 8601") from exc
        rc, out, err = run(repo, now, args.dry_run, args.json, deps or Deps())
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 3
    except si_check.InputError as exc:
        sys.stderr.write(f"selfimproving: {exc}\n")
        return 3
    sys.stdout.write(out)
    sys.stderr.write(err)
    return rc
