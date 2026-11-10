"""SelfImproving 無人運轉執行器：研究前置、任務書、脫離式 spawn（TCS-SelfImproving-P4 R150～R152、
R166、R167）。

能力類別 `exec`：外部行程只經 `runner.spawn_detached`（由 `patrol` 的依賴注入包提供）；
環境＝明示建構、不繼承（D-RT-4 白名單；絕不含金鑰、`AUTOSDD_SI_AUDIT_KEY`、含
KEY／TOKEN／SECRET／PASSWORD 的變數）。
本檔不等待無人主控：spawn 後寫 `patrol/<RUN>/spawn.json`（pid、啟動時刻、硬牆到期）即返回，收尾由
後續心跳的步 0′ 以事件帳本為憑。
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

# `resume_route` 以頂層名 import 同層的 endurance_env，故先把 tools/lib 放進 sys.path
_LIB = str(Path(__file__).resolve().parents[1])
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from lib import resume_route, unattended_authz  # noqa: E402

from . import check as si_check  # noqa: E402
from . import events as si_events  # noqa: E402
from . import fold as si_fold  # noqa: E402
from . import fourqparse, patrolbrief, runner, sched  # noqa: E402

ENV_ALLOW = (*runner._ENV_KEYS, "APPDATA", "LOCALAPPDATA", "CLAUDE_CONFIG_DIR", "AUTOSDD_SI_DIR")
_SECRET_RE = re.compile(r"KEY|TOKEN|SECRET|PASSWORD", re.IGNORECASE)


def task_dir(si: Path, run: str) -> Path:
    return si / "patrol" / run


def child_env(run: str, parent) -> dict[str, str]:
    """子行程環境（R151、D-RT-4）：白名單加四個必含鍵；名稱含機密字樣者一律剔除。"""
    env = {k: parent[k] for k in ENV_ALLOW if k in parent and not _SECRET_RE.search(k)}
    env.update(resume_route.spawn_env())
    env[unattended_authz.UNATTENDED_ENV] = "1"
    env["AUTOSDD_SI_PATROL_RUN"] = run
    return env


def _research_text(events: list[dict], run: str,
                   tdir: Path | None = None) -> tuple[str, list[str], str]:
    """（研究結果一句、changed=true 來源檔路徑、研究狀態）；原檔在
    `<si>/research/<id>/<sha12>.txt`。帶 `tdir` 時列任務目錄下的副本路徑（D-IMP-12：
    研究者與四問審視者只讀得到 `--add-dir` 的任務目錄）。"""
    r = si_fold.fold(events).runs.get(run)
    ev = next((e for e in events if r and r.research and e["seq"] == r.research[1]), None)
    if ev is None:
        return "尚無研究事件", [], "none"
    if ev["kind"] == "research.skip":
        return f"research.skip（reason={ev['reason']}）", [], "skip"
    si = si_events.si_dir()
    files = [str(si / "research" / s["id"] / f"{s['sha256'].split(':')[1][:12]}.txt")
             for s in ev["sources"] if s["changed"]]
    note = f"來源 {len(ev['sources'])} 筆，changed {len(files)} 筆"
    if tdir is not None:
        files = [str(tdir / "research" / Path(f).name) for f in files]
    return f"research.scan seq={ev['seq']}（{note}）", files, "scan"


def stage_sources(events: list[dict], run: str, tdir: Path) -> None:
    """把 changed=true 來源檔逐位元組複製到 `tdir/research/`（D-IMP-12）；任一檔失敗＝
    清掉半套副本並拋 `OSError`（呼叫端據此不 spawn）。"""
    srcs = _research_text(events, run)[1]
    if not srcs:
        return
    dest = tdir / "research"
    try:
        dest.mkdir(parents=True, exist_ok=True)
        for s in srcs:
            (dest / Path(s).name).write_bytes(Path(s).read_bytes())
    except OSError:
        shutil.rmtree(dest, ignore_errors=True)
        raise


def _events_text(ctx) -> str:
    """偵測到的啟動事件（`status` 的 `events_detected`）；量不到＝如實寫。"""
    try:
        from . import status

        got = status.build(ctx.repo, ctx.git(), ctx.status_params(), now=ctx.now)["events_detected"]
    except Exception as exc:  # noqa: BLE001  # 任務書的資料欄量不到不擋 spawn，但要說出口
        return f"（status 量不到：{type(exc).__name__}）"
    text = "、".join(f"{e['trigger']} {e['subject']}" for e in got)
    return text or "無（排程或 Console 立即啟動）"


def _scan_rows(ctx) -> list[str]:
    rc, out, _ = ctx.verb("scan", "--json")
    try:
        return [c["row"] for c in json.loads(out)["candidates"]] if rc == 0 else []
    except (ValueError, KeyError, TypeError):
        return []


def compose(ctx, run: str, trigger: str, due_at: str, scan_rows: list[str]) -> str:
    """生成任務書全文（讀 `--repo` 內的 SOP 範本；缺必含項即 `ValueError`）。"""
    events = ctx.load()
    sop = (ctx.repo / sched.SOP_REL).read_text(encoding="utf-8")
    tpl = patrolbrief.template_of(sop)
    if tpl is None or patrolbrief.template_problems(sop):
        raise ValueError("sop-template:" + ",".join(patrolbrief.template_problems(sop)))
    tdir = task_dir(ctx.si, run)
    result, files, _ = _research_text(events, run, tdir)
    fields = {
        "RUN": run, "HEAD_SHA": ctx.git().head() or "unknown", "NOW_ISO": sched.iso(ctx.now),
        "DUE_AT": due_at, "BAND": ctx.band,
        "DEGRADE_NOTE": patrolbrief.DEGRADE_TEXT.format(band=ctx.band) if ctx.degrade else "",
        "BUDGET_MINUTES": ctx.params["sched_run_budget_minutes"], "EVENTS": _events_text(ctx),
        "RESEARCH_RESULT": result, "SOURCE_FILES": "、".join(files) or "無",
        "SCAN_CANDIDATES": f"{len(scan_rows)} 筆：" + " ／ ".join(scan_rows) if scan_rows else "無",
        "MAX_PROPOSALS": ctx.status_params().get("max_proposals_per_run", 3),
        "HANDBACK_PATH": str(tdir / "handback.md")}
    return patrolbrief.render(tpl, fields, trigger=trigger)


def read_json(path: Path) -> dict | None:
    try:
        obj = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


def _alive(pid: int, started_at: str) -> bool:
    """pid 存活且啟動時刻與 `spawn.json` 記的相近（pid 被重用者視為已結束）。"""
    start = runner.pid_started_at(pid)
    want = datetime.fromisoformat(started_at).timestamp()
    return start is not None and want - 120 <= start <= want + 3600


def _finish(ctx, run: str, path: Path, data: dict) -> None:
    """依事件帳本收尾（R156）：無 `prop`⇒`run-close`；handback 缺節與 harness 殺行程只記日誌、
    不重 spawn。"""
    tdir = path.parent
    try:
        lines = (tdir / "handback.md").read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    miss = [m for m in resume_route.HANDBACK_MARKERS
            if not any(resume_route.heading_hit(ln, m) for ln in lines)]
    if miss:
        ctx.log("巡視", 0, "HANDBACK-INCOMPLETE", f"{run} handback 不完整：缺 {'、'.join(miss)}")
    try:
        err = (tdir / "stderr.txt").read_text(encoding="utf-8", errors="replace")
    except OSError:
        err = ""
    if resume_route.harness_bg_kill(err):
        ctx.log("巡視", 0, "HARNESS-BG-KILL", f"{run} harness 背景殺行程（背景等待上限）")
    if fourqparse.applicable(run, ctx.params) and run not in fourqparse.fourq_events(ctx.load()):
        ctx.log("巡視", 0, "FOURQ-NOT-RUN", f"{run} 適用運轉結束而無 fourq 事件（不重 spawn）")
    r = ctx.fold().runs.get(run)
    if r is not None and r.closed_seq is None and not r.prop_ids:
        rc, _, _ = ctx.verb("run-close", "--run", run, "--by", "patrol")
        ctx.log("巡視", rc, None if rc == 0 else "RUN-CLOSE-FAILED",
                f"{run} 零提案，run-close(no_event)")
    data["closed_at"] = sched.iso(ctx.now)
    path.write_bytes(json.dumps(data, ensure_ascii=False).encode("utf-8") + b"\n")


def watch(ctx) -> tuple[str, bool]:
    """步 0′（R167）：巡視 `spawn.json` 未結案的運轉；回（結果說明, 是否有進行中且未逾牆者）。"""
    busy, notes = False, []
    for path in sorted((ctx.si / "patrol").glob("RUN-SI-*/spawn.json")):
        data, run = read_json(path), path.parent.name
        if data is None or "closed_at" in data:
            continue
        alive = (ctx.deps.pid_alive or _alive)(data["pid"], data["started_at"])
        over = ctx.now >= datetime.fromisoformat(data["wall_due_at"])
        if alive and not over:
            busy = True
            notes.append(f"{run} 進行中")
            continue
        notes.append(f"{run} {'逾牆終止' if alive else '已結束，依事件收尾'}")
        if ctx.dry:
            continue
        if alive:
            ctx.log("巡視", 0, "WALL-EXCEEDED", f"{run} 逾牆終止（pid={data['pid']}）")
            (ctx.deps.kill_tree or runner.kill_pid_tree)(data["pid"])
        _finish(ctx, run, path, data)
    ctx.log("巡視", 0, None, f"巡視完成（{len(notes)} 個未結案的無人運轉；進行中={busy}）")
    return "、".join(notes) or "無進行中的無人運轉", busy


def launch(ctx, run: str, *, trigger: str, due_at: str) -> tuple[str, str]:
    """對一個已開的運轉走前置序（research→scan→任務書）後脫離式 spawn；回 (狀態, 說明)：
    `spawned`；`failed`（spawn 被拒或任務書不可用；說明以 `breakaway-denied` 或
    `sop-template:` 起頭）。"""
    tdir = task_dir(ctx.si, run)
    tdir.mkdir(parents=True, exist_ok=True)
    if _research_text(ctx.load(), run)[2] == "none":
        rc, _, _ = ctx.verb("research", "--fetch", "--run", run)
        if rc not in (0, 2):  # rc 1（含網路例外）：改記離線免掃；rc 2 照常繼續
            ctx.verb("research", "--skip", "--run", run, "--reason", "offline", "--note",
                     f"巡邏器研究抓取失敗（rc={rc}），改記離線免掃")
    rows = _scan_rows(ctx)
    for row in rows:
        ctx.log("運轉", 0, "-", f"{run} scan 候選：{row}")
    try:
        stage_sources(ctx.load(), run, tdir)
    except OSError as exc:  # 副本不齊就不 spawn：研究者讀不到來源檔等於白跑
        return "failed", f"sources-copy-failed: {type(exc).__name__}"
    try:
        brief = compose(ctx, run, trigger, due_at, rows)
    except (OSError, ValueError) as exc:
        return "failed", f"sop-template:{exc}"
    path = tdir / "brief.md"
    path.write_bytes(brief.encode("utf-8"))
    claude = (ctx.deps.which or shutil.which)("claude") or "claude"
    prompt = (f"你是無人運轉 {run} 的主控：先完整讀任務書 {path}，依其角色序與禁止事項執行；"
              f"handback 寫到 {tdir / 'handback.md'}（四節標題逐字，邊做邊寫）。")
    argv = resume_route.fresh_argv(claude, prompt, tdir)
    try:
        pid = ctx.spawn(argv, env=child_env(run, ctx.environ), cwd=ctx.repo, out_dir=tdir)
    except OSError as exc:  # PermissionError 亦屬之：脫離旗標被拒＝fail-closed，不留 spawn.json
        return "failed", f"breakaway-denied: {type(exc).__name__}"
    started = ctx.now
    wall = started + timedelta(seconds=unattended_authz.RESUME_HARD_WALL_SECONDS)
    (tdir / "spawn.json").write_bytes(json.dumps(
        {"pid": pid, "started_at": sched.iso(started), "wall_due_at": sched.iso(wall)},
        ensure_ascii=False).encode("utf-8") + b"\n")
    return "spawned", f"{run} pid={pid}"


def first_code(out: str, err: str) -> str:
    m = re.search(r"^reject \S+ (\S+)", out, re.MULTILINE)
    if m:
        return m.group(1).split(",")[0]
    return "USAGE" if err.startswith("selfimproving:") else "REJECTED"


_TERMINAL = ("rejected", "handed-off", "returned", "promoted", "measuring", "closed")
_POST = ("promoted", "measuring", "closed")


# ── 步 4 推進（R154、R155）────────────────────────────────────────────────────────
def _step(ctx, pid: str, verb: str, *extra: str) -> bool:
    rc, out, err = ctx.verb(verb, pid, *extra, "--by", "patrol")
    ctx.log("推進", rc, None if rc == 0 else first_code(out, err), f"{pid} {verb} rc={rc}")
    return rc == 0


def _commit(ctx, pid: str, verb: str) -> None:
    """只 `git add` 該 PROP 的 touched 與 SI 自有路徑中**真有改動**者；不 push、不繞 hook、
    不重試。"""
    from . import sandbox  # 延遲：沙盒模組的 patch 解析（touched 的唯一來源）

    events = ctx.load()
    prop = next(e for e in reversed(events) if e["kind"] == "prop" and e["id"] == pid)
    own = [si_events.LEDGER_REL, si_check.LEDGER_REL, si_events.PROPOSALS_REL]
    cands = list(dict.fromkeys([*sandbox.prop_context(ctx.repo, prop)[1], *own]))
    cp = ctx.git().run("-c", "core.quotepath=false", "status", "--porcelain", "-z",
                       "--untracked-files=all", "--", *cands)
    toks, changed, i = ((cp.stdout.split("\0") if cp else []), [], 0)
    while i < len(toks):
        tok, i = toks[i], i + 1
        if len(tok) < 4:
            continue
        changed.append(tok[3:])
        if tok[0] in "RC":
            changed.append(toks[i])
            i += 1
    if not changed:
        ctx.log("commit", 0, None, f"{pid} {verb}：沒有可提交的改動")
        return
    dec = next(e["id"] for e in reversed(events) if e["kind"] == "dec" and e.get("prop") == pid
               and e.get("dkind") == verb)
    app = next(e["id"] for e in reversed(ctx.load()) if e["kind"] == f"app.{verb}"
               and e.get("prop") == pid)
    msg = (f"chore(selfimproving): {verb} {pid}（{dec}、{app}）\n\n"
           "巡邏器依人的決定機械推進後的本機 commit；不 push。")
    add = ctx.git().run("add", "--", *changed)
    done = ctx.git().run("commit", "-m", msg) if add and add.returncode == 0 else add
    rc = done.returncode if done else 1
    if rc != 0:
        row = ctx.draft("patrol-commit", "COMMIT-FAILED", f"{pid} {verb} 的 commit 失敗（rc={rc}）")
        ctx.log("commit", rc, "COMMIT-FAILED",
                f"{pid} {verb} commit 失敗，不重試；obs-draft: {row}")
    else:
        ctx.log("commit", 0, None, f"{pid} {verb} 已本機 commit（{dec}、{app}）")


def _carded(events: list[dict], pid: str) -> bool:
    last = max((e["seq"] for e in events if e["kind"] == "app.verify" and e["prop"] == pid),
               default=0)
    return any(e["kind"] == "card" and e["prop"] == pid and e["seq"] > last for e in events)


def _advance_prop(ctx, pid: str) -> bool:
    """推進一個 PROP；回是否有成功的 promote（供 `measure`）。"""
    promoted = False
    for _ in range(4):
        p = ctx.fold().props[pid]
        # 已晉升／量測中／已關且無待回滾＝無事可做，不得每心跳要人給 --memory-dir（D-IMP-9 (d)）
        if p.cls == "M" and (p.state in ("approved", "verified")
                             or (p.state in _POST and p.pending_rollbacks >= 1)):
            ctx.log("推進", 0, "MEMORY-DIR", f"{pid} 為 M 類，須人工給 --memory-dir")
            return promoted
        if p.state == "approved":
            if p.freeze_seq is None:
                ctx.log("推進", 0, "NO-HELDOUT", f"{pid} 缺 heldout.freeze，跳過（不記 skip）")
                return promoted
            if not _step(ctx, pid, "sandbox"):
                return promoted
        elif p.state == "sandboxed":
            if not _step(ctx, pid, "verify"):
                return promoted
        elif (p.state == "verified" and p.pending_promote is None) or (
                p.state in _POST and p.pending_rollbacks < 1):
            if p.state == "verified" and not _carded(ctx.load(), pid):
                _step(ctx, pid, "card", "--issue")
            return promoted
        elif p.state in ("verified", *_POST):
            verb = "promote" if p.state == "verified" else "rollback"
            if p.freeze_seq is None:
                ctx.log("推進", 0, "NO-HELDOUT", f"{pid} 缺 heldout.freeze，不 {verb}（不記 skip）")
                return promoted
            if sched.dirty_paths(ctx.repo):
                ctx.log("推進", 0, "dirty-tree", f"{pid} {verb} 前樹不乾淨：不 {verb}，只寫日誌")
                return promoted
            if not _step(ctx, pid, verb):
                return promoted
            promoted = promoted or verb == "promote"
            if ctx.params["sched_auto_commit"]:
                _commit(ctx, pid, verb)
        else:
            return promoted
    return promoted


def _live(ctx) -> set[str]:
    live = set()
    for path in (ctx.si / "patrol").glob("RUN-SI-*/spawn.json"):
        data = read_json(path)
        if data is not None and "closed_at" not in data:
            live.add(path.parent.name)
    return live


def advance(ctx) -> str:
    if ctx.dry:
        n = sum(1 for p in ctx.fold().props.values() if p.state in ("approved", "sandboxed",
                                                                   "verified", *_POST))
        return f"將檢查 {n} 個 PROP 的待推進步驟"
    measured = False
    for pid in list(ctx.fold().props):
        measured = _advance_prop(ctx, pid) or measured
    if measured:
        _step_measure(ctx)
    f, live, closed = ctx.fold(), _live(ctx), 0
    for run in f.runs.values():
        props = [f.props[i].state for i in run.prop_ids if i in f.props]
        if run.closed_seq is None and props and run.id not in live and all(
                s in _TERMINAL for s in props):
            rc, out, err = ctx.verb("run-close", "--run", run.id, "--by", "patrol")
            ctx.log("推進", rc, None if rc == 0 else first_code(out, err),
                    f"{run.id} 各提案已離開待決態，run-close")
            closed += rc == 0
    ctx.log("推進", 0, None, f"推進完成（run-close {closed}）")
    return f"完成（run-close {closed}）"


def _step_measure(ctx) -> None:
    rc, out, err = ctx.verb("measure", "--by", "patrol")
    ctx.log("推進", rc, None if rc == 0 else first_code(out, err), f"measure rc={rc}")
