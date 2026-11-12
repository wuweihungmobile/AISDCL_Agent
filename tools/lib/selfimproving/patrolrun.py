"""SelfImproving 無人運轉執行器：研究前置、任務書、脫離式 spawn（TCS-SelfImproving-P4 R150～R152、
R166、R167）。

能力類別 `exec`：外部行程只經 `runner.spawn_detached`（由 `patrol` 的依賴注入包提供）；
環境＝明示建構、不繼承（D-RT-4 白名單；絕不含金鑰、`AUTOSDD_SI_AUDIT_KEY`、含
KEY／TOKEN／SECRET／PASSWORD 的變數）。
本檔不等待無人主控：spawn 後寫 `patrol/<RUN>/spawn.json`（pid、啟動時刻、硬牆到期）即返回，收尾由
後續心跳的步 0′ 以事件帳本為憑。
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from datetime import timedelta
from pathlib import Path

# `resume_route` 以頂層名 import 同層的 endurance_env，故先把 tools/lib 放進 sys.path
_LIB = str(Path(__file__).resolve().parents[1])
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from lib import resume_route, unattended_authz  # noqa: E402

from . import events as si_events  # noqa: E402
from . import fold as si_fold  # noqa: E402
from . import (  # noqa: E402
    fourqparse,
    memdir,
    patrolbrief,
    patrolreport,
    pushguard,
    runner,
    sched,
)

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
    try:
        plan = _staged(ev)
    except ScansMismatch:  # 呼叫端（`launch`）隨後的 `stage_sources` 會以同一例外拒絕 spawn
        plan = []
    changed = sum(1 for s in ev["sources"] if s["changed"])
    note = f"來源 {len(ev['sources'])} 筆，changed {changed} 筆"
    files = [str(src) if tdir is None else str(tdir / "research" / name) for src, name in plan]
    return f"research.scan seq={ev['seq']}（{note}）", files, "scan"


class ScansMismatch(ValueError):
    """`_scans/<RUN>.json` 缺或位元組雜湊不等於事件的 `articles_sha256`（不 spawn）。"""


def _article_paths(ev: dict, si: Path) -> list[tuple[Path, str]]:
    """明細檔（先驗雜湊）中 changed=true 的文章檔：純文字旁檔優先，非 HTML 取原檔。"""
    if "articles_sha256" not in ev:
        return []
    try:
        raw = (si / "research" / "_scans" / f"{ev['run']}.json").read_bytes()
        items = json.loads(raw.decode("utf-8"))["items"]
    except (OSError, ValueError, KeyError):
        raise ScansMismatch("sources-scans-mismatch") from None
    if "sha256:" + hashlib.sha256(raw).hexdigest() != ev["articles_sha256"]:
        raise ScansMismatch("sources-scans-mismatch")
    out = []
    for it in items:
        if it.get("status") != "ok" or not it.get("changed"):
            continue
        sha12 = it["sha256"].split(":")[1][:12]
        folder = si / "research" / it["source"] / "articles"
        out.append((folder / (f"{sha12}.plain.txt" if it.get("plain_sha256") else f"{sha12}.txt"),
                    it["source"]))
    return out


def _staged(ev: dict) -> list[tuple[Path, str]]:
    """（原檔, 任務目錄內檔名）：changed=true 來源的 `<sha12>.txt` 與（若有）`.plain.txt`，再加
    changed=true 文章檔；檔名衝突者後來者以 `<id>__<檔名>` 前綴避開（AC-SI-30-10）。"""
    si = si_events.si_dir()
    pairs: list[tuple[Path, str]] = []
    for s in ev["sources"]:
        if not s["changed"]:
            continue
        base = si / "research" / s["id"] / f"{s['sha256'].split(':')[1][:12]}.txt"
        pairs.append((base, s["id"]))
        plain = base.with_name(base.stem + ".plain.txt")
        if plain.is_file():
            pairs.append((plain, s["id"]))
    pairs += _article_paths(ev, si)
    taken: set[str] = set()
    out = []
    for src, owner in pairs:
        name = src.name if src.name not in taken else f"{owner}__{src.name}"
        taken.add(name)
        out.append((src, name))
    return out


def stage_sources(events: list[dict], run: str, tdir: Path) -> None:
    """把 changed=true 來源檔（含純文字旁檔）與 changed=true 文章檔逐位元組複製到 `tdir/research/`
    （D-IMP-12、AC-SI-30-10）；任一檔失敗＝清掉半套副本並拋 `OSError`；明細雜湊不符拋
    `ScansMismatch`（呼叫端據此不 spawn）。"""
    r = si_fold.fold(events).runs.get(run)
    ev = next((e for e in events if r and r.research and e["seq"] == r.research[1]), None)
    plan = _staged(ev) if ev is not None and ev["kind"] == "research.scan" else []
    if not plan:
        return
    dest = tdir / "research"
    try:
        dest.mkdir(parents=True, exist_ok=True)
        for src, name in plan:
            (dest / name).write_bytes(src.read_bytes())
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
        "HANDBACK_PATH": str(tdir / "handback.md"),
        "MIN_HELDOUT": ctx.status_params().get("min_heldout", "未知")}
    return patrolbrief.render(tpl, fields, trigger=trigger)


def read_json(path: Path) -> dict | None:
    try:
        obj = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


_alive = runner.alive  # pid 存活且身分相符（被重用者視為已結束）；無法驗證視為活著（安全側）


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
        who = None if ctx.deps.pid_alive else runner.spawn_identity(data)
        alive = who in ("match", "unverified") if who else ctx.deps.pid_alive(
            data["pid"], data["started_at"])
        over = runner.overdue(ctx.now, data["wall_due_at"])  # 被竄改的記錄視為逾牆（E-46）
        if alive and not over:
            busy = True
            notes.append(f"{run} 進行中")
            continue
        notes.append(f"{run} {'逾牆終止' if alive else '已結束，依事件收尾'}")
        if ctx.dry:
            continue
        if who in ("mismatch", "unverified"):  # 身分對不上或缺建立時間：不殺（審查 F-07）
            ctx.kill_skipped(run, data["pid"])
        elif alive:
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
    except ScansMismatch as exc:  # 篇目明細與事件不符：不 spawn（AC-SI-30-10）
        return "failed", str(exc)
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
    wall = ctx.now + timedelta(seconds=unattended_authz.RESUME_HARD_WALL_SECONDS)
    (tdir / "spawn.json").write_bytes(json.dumps(runner.spawn_record(pid, ctx.now, wall),
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
    code = None if rc == 0 else first_code(out, err)
    ctx.log("推進", rc, code, f"{pid} {verb} rc={rc}")
    if code:
        ctx.note(pid, code)  # 本心跳的卡點（快照 props[] 覆蓋帳本推導，TCS-P7 AC-SI-47-10）
    return rc == 0


def _commit(ctx, pid: str, verb: str) -> None:
    """只 `git add` 該 PROP 的 touched 與 SI 自有路徑中**真有改動**者；不 push、不繞 hook、
    不重試。"""
    from . import sandbox  # 延遲：沙盒模組的 patch 解析（touched 的唯一來源）

    events = ctx.load()
    prop = next(e for e in reversed(events) if e["kind"] == "prop" and e["id"] == pid)
    allow = pushguard.commit_allow(pid, sandbox.prop_context(ctx.repo, prop)[1], prop["cls"])
    found, left = pushguard.pending(ctx.git(), allow)
    changed = [p for p, _ in found]
    if not changed:
        ctx.log("commit", 0, None, f"{pid} {verb}：沒有可提交的改動")
        return
    bad = pushguard.rule_problem(ctx.git(), ctx.repo, pid, found)  # git add 之前、與守門同一套
    if bad:
        ctx.log("commit", 0, "COMMIT-LEDGER-RULE", f"{pid} {verb} 不提交：{bad}；請人工檢查")
        ctx.note(pid, "COMMIT-LEDGER-RULE", bad)
        return
    dec = next(e["id"] for e in reversed(events) if e["kind"] == "dec" and e.get("prop") == pid
               and e.get("dkind") == verb)
    app = next(e["id"] for e in reversed(events) if e["kind"] == f"app.{verb}"
               and e.get("prop") == pid)
    msg = pushguard.commit_message(verb, pid, dec, app)
    add = ctx.git().run("add", "--", *changed)
    ok = add and add.returncode == 0
    done = ctx.git().run("commit", "-m", msg, "--", *changed) if ok else add
    rc = done.returncode if done else 1
    if rc != 0:
        row = ctx.draft("patrol-commit", "COMMIT-FAILED", f"{pid} {verb} 的 commit 失敗（rc={rc}）")
        ctx.log("commit", rc, "COMMIT-FAILED",
                f"{pid} {verb} commit 失敗，不重試；obs-draft: {row}")
        ctx.note(pid, "COMMIT-FAILED")
        return
    ctx.log("commit", 0, None, f"{pid} {verb} 已本機 commit（{dec}、{app}）")
    try:  # 紀錄的 sha 取自 commit 成功「之後」的 HEAD；寫入失敗＝該提交不可自動推送，不重試、不回滾
        patrolreport.record_commit(ctx.si, ctx.git().head(), app, pid, ctx.now)
    except OSError as exc:
        ctx.log("commit", 0, "COMMIT-RECORD-FAILED", f"{pid} {verb} 提交紀錄寫入失敗（{exc}）")
        ctx.note(pid, "COMMIT-RECORD-FAILED")
    else:
        if left:
            ctx.log("commit", 0, "COMMIT-LEFTOVER", f"{pid} {verb} 清單外髒檔留在工作樹：{left[0]}")
            ctx.note(pid, "COMMIT-LEFTOVER", left[0])


def _carded(events: list[dict], pid: str) -> bool:
    last = max((e["seq"] for e in events if e["kind"] == "app.verify" and e["prop"] == pid),
               default=0)
    return any(e["kind"] == "card" and e["prop"] == pid and e["seq"] > last for e in events)


def _advance_prop(ctx, pid: str) -> bool:
    """推進一個 PROP；回是否有成功的 promote（供 `measure`）。"""
    promoted = False
    for _ in range(4):
        p = ctx.fold().props[pid]
        # M 類只在真有待推進步驟時才解析記憶目錄（D-IMP-9 (d)）；解析不到＝不呼叫任何動詞（P7）
        want = memdir.pending(p)
        mem = memdir.resolve(ctx.repo) if want else None
        if want and mem is None:
            where = memdir.target(ctx.repo)
            ctx.log("推進", 0, "MEMORY-DIR-UNRESOLVED", f"{pid} 找不到記憶目錄：{where}")
            ctx.note(pid, "MEMORY-DIR-UNRESOLVED", where)
            return promoted
        mflag = ("--memory-dir", mem) if mem else ()
        if p.state == "approved":
            if p.freeze_seq is None:
                ctx.log("推進", 0, "NO-HELDOUT", f"{pid} 缺 heldout.freeze，跳過（不記 skip）")
                ctx.note(pid, "NO-HELDOUT")
                return promoted
            if not _step(ctx, pid, "sandbox", *mflag):
                return promoted
        elif p.state == "sandboxed":
            if not _step(ctx, pid, "verify", *mflag):
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
                ctx.note(pid, "NO-HELDOUT")
                return promoted
            if pushguard.running(ctx.si, ctx.now, ctx.deps.pid_alive or _alive):  # 推送中不改工作樹
                ctx.log("推進", 0, "PUSH-IN-PROGRESS", f"{pid} 推送進行中，不 {verb}")
                ctx.note(pid, "PUSH-IN-PROGRESS")
                return promoted
            if sched.dirty_paths(ctx.repo):
                ctx.log("推進", 0, "dirty-tree", f"{pid} {verb} 前樹不乾淨：不 {verb}，只寫日誌")
                ctx.note(pid, "dirty-tree")
                return promoted
            if not _step(ctx, pid, verb, *mflag):
                return promoted
            if mem and memdir.post_image_problems(ctx.repo, ctx.load(), pid, mem):
                ctx.log("推進", 0, "POSTIMAGE-MISMATCH", f"{pid} {verb} 後記憶檔不符（不回滾）")
                ctx.note(pid, "POSTIMAGE-MISMATCH")  # 回滾是人的決定；measure 與 commit 照做
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
