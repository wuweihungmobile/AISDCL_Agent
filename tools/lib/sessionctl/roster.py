"""sessionctl 名冊：背景代理三態、SendMessage 成本閘、Stop 出聲、`status`／`stop` 指令
（ADR-XPLAT-004 §2.13.6 D6／D7；TCS-SessionCtl AT-SC-61～76）。

資料源全是讀檔、零 token：`<projects>/<slug>/<sid>/subagents/agent-<id>.{meta.json,jsonl}`。
`projects_dir` 缺省＝`claude_home()/projects`；給 slug 目錄（內含 `<sid>/subagents`）也認，hook 從
payload 的 `transcript_path.parent` 傳入即屬此形。三態（只列 `finished` 不是 true 者——缺鍵與 false
同義，V-S4 實測 session 被砍時 meta 沒有該鍵）：
  · running：最後記錄 < `ROSTER_QUIET_MINUTES` 前；
  · quiet：超過該門檻；
  · residue（殘局）：quiet ∧ 擁有者逐字稿閒置 ≥ 巡邏間隔 ∧ 無 claude 行程命令列含該 sid（只在
    給了 `runner` 的 `snapshot` 判，因為要列舉行程）。🔴 殘局＝未收尾的記錄，**不是**還在燒額度的
    東西（子代理跑在擁有者行程內，擁有者死了它也死了），名冊明說，不讓人以為能去砍它。
hook 呼叫的 `running()`／`resume_gate()`／`stop_message()` 全部純讀檔、不 spawn。
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from . import procstop

OWNER_IDLE_SECONDS = 900  # 擁有者逐字稿閒置的「巡邏間隔」（哨兵每 15 分鐘巡邏一次）
_TAIL_BYTES = 262144
_LOOKBACK_SECONDS = 48 * 3600  # 無 sid 的全域名冊只看近 48 小時有動過的代理檔
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
STATES = ("running", "quiet", "residue")


def _projects(projects_dir) -> Path:
    if projects_dir is not None:
        return Path(projects_dir)
    import platform_utils  # noqa: PLC0415 — lazy

    return platform_utils.claude_home() / "projects"


def _agent_dirs(projects: Path, session_id: str | None):
    """`(owner_sid, subagents 目錄)`；給 slug 目錄（`<sid>/subagents`）或 projects 根皆可。"""
    seen: set[Path] = set()
    try:
        if session_id:
            pats = (f"{session_id}/subagents", f"*/{session_id}/subagents")
        else:
            pats = ("*/subagents", "*/*/subagents")
        for pat in pats:
            for path in projects.glob(pat):
                if path.is_dir() and path not in seen:
                    seen.add(path)
                    yield path.parent.name, path
    except OSError:
        return


def _records(path: Path, tail: bool):
    """逐行 JSON（壞行跳過）。`tail`＝只讀尾端 256 KB（丟掉被截斷的第一行）。"""
    try:
        with path.open("rb") as handle:
            if tail:
                size = handle.seek(0, os.SEEK_END)
                handle.seek(max(0, size - _TAIL_BYTES))
                chunk = handle.read()
                chunk = chunk.split(b"\n", 1)[-1] if size > _TAIL_BYTES else chunk
            else:
                chunk = handle.read()
    except OSError:
        return
    for line in chunk.decode("utf-8", errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict):
            yield rec


def _usage(rec: dict) -> dict | None:
    msg = rec.get("message")
    use = msg.get("usage") if isinstance(msg, dict) else None
    return use if rec.get("type") == "assistant" and isinstance(use, dict) else None


def _ctx(use: dict) -> int:
    """上下文＝input＋cache_read＋cache_creation（`context_budget_guard.used_of` 同式）。"""
    return sum(int(use.get(k) or 0) for k in
               ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
               if type(use.get(k)) is int)


def _scan(path: Path, full: bool) -> dict:
    """`last_at`（最後一筆記錄時刻 epoch）、`ctx_tokens`（最後一筆 assistant usage）、`started_at`
    與（`full` 時）`total_tokens`。讀不到的欄位為 `None`。"""
    out: dict = {"last_at": None, "ctx_tokens": None, "started_at": None, "total_tokens": None}
    recs = list(_records(path, tail=not full))
    for rec in reversed(recs):
        if out["last_at"] is None:
            out["last_at"] = procstop.parse_iso(rec.get("timestamp"))
        if out["ctx_tokens"] is None and (use := _usage(rec)) is not None:
            out["ctx_tokens"] = _ctx(use)
    first = next(_records_head(path), None)
    out["started_at"] = procstop.parse_iso(first.get("timestamp")) if first else None
    if full:
        seen: set[str] = set()
        total = 0
        for rec in recs:
            if (use := _usage(rec)) is None:
                continue
            key = str((rec.get("message") or {}).get("id") or id(rec))
            if key not in seen:  # 同一則回應常被串流寫多列，逐 id 去重
                seen.add(key)
                total += _ctx(use) + (int(use["output_tokens"]) if type(use.get("output_tokens")) is int else 0)  # noqa: E501
        out["total_tokens"] = total
    if out["last_at"] is None:
        try:
            out["last_at"] = path.stat().st_mtime
        except OSError:
            pass
    return out


def _records_head(path: Path):
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if isinstance(rec, dict) and rec.get("timestamp"):
                    yield rec
                    return
    except OSError:
        return


def _meta(path: Path) -> dict:
    try:
        data = json.loads(path.with_name(path.stem + ".meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _iso(epoch: float | None) -> str | None:
    return None if epoch is None else datetime.fromtimestamp(epoch).astimezone().isoformat(
        timespec="seconds")


def _owner_last(projects: Path, owner: str) -> float | None:
    """擁有者**主**逐字稿最後一筆 assistant／user 記錄時刻（不含 subagent 檔，否則代理一寫就算活著）。"""  # noqa: E501
    try:
        main = next(iter(projects.glob(f"{owner}.jsonl")), None) or next(
            iter(projects.glob(f"*/{owner}.jsonl")), None)
    except OSError:
        return None
    best = None
    for rec in _records(main, tail=True) if main else ():
        if rec.get("type") in ("assistant", "user"):
            stamp = procstop.parse_iso(rec.get("timestamp"))
            best = stamp if stamp is not None and (best is None or stamp > best) else best
    return best


def snapshot(session_id: str | None = None, *, projects_dir=None, now=None, env=None,
             runner=None, full: bool = True) -> dict:
    """名冊快照：`agents`／`windows`／`schedules`／`stale_sentinels`／`handoffs`。`runner=None`＝
    純讀檔（不列舉行程、不查排程；也就不判殘局）。"""
    from . import switch  # noqa: PLC0415 — lazy

    now_ts = (now or datetime.now().astimezone()).timestamp()
    quiet = switch.threshold(switch.ROSTER_QUIET_KEY, env)[0] * 60
    projects = _projects(projects_dir)
    procs = procstop.list_processes(runner) if runner is not None else None
    alive = {procstop.sid_of(p["cmd"]) for p in procs or () if procstop.is_claude(p)}
    agents: list[dict] = []
    for owner, folder in _agent_dirs(projects, session_id):
        for path in sorted(folder.glob("agent-*.jsonl")):
            meta = _meta(path)
            try:
                if meta.get("finished") is True or (
                        not session_id and now_ts - path.stat().st_mtime > _LOOKBACK_SECONDS):
                    continue
            except OSError:
                continue
            info = _scan(path, full)
            idle = now_ts - info["last_at"] if info["last_at"] is not None else None
            state = "running" if idle is not None and idle < quiet else "quiet"
            if state == "quiet" and procs is not None and owner not in alive:
                last = _owner_last(folder.parent.parent, owner)
                if last is not None and now_ts - last >= OWNER_IDLE_SECONDS:
                    state = "residue"
            agents.append({
                "id": path.stem.removeprefix("agent-"), "owner_sid": owner,
                "description": str(meta.get("description") or ""),
                "model": str(meta.get("model") or meta.get("pickedEffortModel") or ""),
                "state": state, "started_at": _iso(info["started_at"]),
                "last_at": _iso(info["last_at"]), "ctx_tokens": info["ctx_tokens"],
                "total_tokens": info["total_tokens"]})
    return {"agents": agents, "windows": _windows(procs), "schedules": _schedules(runner),
            "stale_sentinels": _stale_sentinels(runner), "handoffs": _handoffs(env)}


def _windows(procs) -> list[dict]:
    return [{"pid": p["pid"], "sid": procstop.sid_of(p["cmd"]),
             "created": _iso(p["created"]), "unattended": bool(procstop._PRINT_RE.search(p["cmd"]))}
            for p in procs or () if procstop.is_claude(p)]


def _schedules(runner) -> list[str]:
    if runner is None:
        return []
    try:
        import schedule_backend  # noqa: PLC0415 — lazy

        jobs = schedule_backend.select().list_jobs("AutoSDD_")
        return list(jobs or [])
    except Exception:  # noqa: BLE001 — 量不到不拋（status 是唯讀診斷）
        return []


def _stale_sentinels(runner) -> list[str]:
    """`waiting` 且 D3 判準成立者（§2.13.3 兜底）＝`sentinel_lifecycle.gc` 預演可收的哨兵。"""
    if runner is None:
        return []
    try:
        import sentinel_lifecycle  # noqa: PLC0415 — lazy

        return [r["task"] for r in sentinel_lifecycle.gc() or []
                if r.get("state") == "waiting" and r.get("reap")]
    except Exception:  # noqa: BLE001
        return []


def _handoffs(env) -> list[str]:
    """未 ack 且未過期的交接包路徑（唯讀、不 mkdir）。判準（檔名形態、`<stem>.ack` sidecar、過期、
    目錄解析）全住 `handoff.list_handoffs`——不在這裡抄第二份（舊版查 `<檔名>.md.ack`，與
    `handoff.ack` 實際寫的 `<stem>.ack` 對不上，已 ack 的包永遠被當成未接手）。"""
    try:
        from . import handoff  # noqa: PLC0415 — lazy：handoff 也 lazy import 本檔，避免環

        return [str(r["path"]) for r in handoff.list_handoffs(env=env) if r["state"] == "live"]
    except Exception:  # noqa: BLE001 — 名冊是唯讀診斷，量不到不拋
        return []


def running(session_id: str, *, projects_dir=None, now=None) -> list[dict]:
    """該 session 狀態為 `running` 的代理；**純讀檔**（hook 會呼叫：不 spawn、不讀全檔）。"""
    snap = snapshot(session_id, projects_dir=projects_dir, now=now, full=False)
    return [a for a in snap["agents"] if a["state"] == "running"]


def agent_context(session_id: str, agent_id: str, *, projects_dir=None) -> int | None:
    """該代理逐字稿最後一筆 assistant usage 的 input＋cache_read＋cache_creation；找不到／讀不動 ⇒
    `None`。不要求代理未結束——續一個已結束的代理一樣整份重讀（E1）。"""
    if not _ID_RE.match(str(agent_id or "")) or not _ID_RE.match(str(session_id or "")):
        return None
    for _owner, folder in _agent_dirs(_projects(projects_dir), session_id):
        path = folder / f"agent-{agent_id}.jsonl"
        if path.is_file():
            return _scan(path, False)["ctx_tokens"]
    return None


def _payload_projects(payload: dict):
    raw = payload.get("transcript_path")
    return Path(raw).parent if isinstance(raw, str) and raw.strip() else None


def _payload_sid(payload: dict) -> str:
    sid = payload.get("session_id")
    if isinstance(sid, str) and sid.strip():
        return sid.strip()
    raw = payload.get("transcript_path")
    return Path(raw).stem if isinstance(raw, str) and raw.strip() else ""


def resume_gate(payload: dict, env) -> tuple[int, str]:
    """PreToolUse／SendMessage 成本閘（D6）。目標＝`tool_input.to`（缺則 `recipient`）；解析不到、
    meta／逐字稿讀不動、payload 退化一律 `(0, "")`（fail-open：誤擋只差一步的代理代價更高）。
    上下文 ≥ `RESUME_AGENT_TOKENS`：互動 ⇒ `(0, 提醒)`；`AUTOSDD_UNATTENDED` 有設 ⇒ `(2, 訊息)`。"""
    try:
        from . import switch  # noqa: PLC0415 — lazy

        tool_input = payload.get("tool_input")
        target = (tool_input.get("to") or tool_input.get("recipient")) if isinstance(
            tool_input, dict) else None
        sid = _payload_sid(payload)
        if not isinstance(target, str) or not sid:
            return 0, ""
        ctx = agent_context(sid, target, projects_dir=_payload_projects(payload))
        limit = switch.threshold(switch.AGENT_TOKENS_KEY, env)[0]
        if ctx is None or ctx < limit:
            return 0, ""
        text = (f"續棒成本閘：代理 {target} 上下文約 {ctx:,} tokens（≥ {limit:,}），"
                "SendMessage 會把它整份重讀（E1：無人窗口續 40～60 萬 token 的舊代理 44 分鐘）。"
                "請改派新代理＋短任務書（handback／交卷檔路徑）。")
        if env.get("AUTOSDD_UNATTENDED"):
            return 2, "🔴 已阻斷（無人窗口）。" + text.replace("請改派", "改派") + "\n"
        return 0, "⚠️ " + text
    except Exception:  # noqa: BLE001 — hook 內任何例外一律放行
        return 0, ""


def _tasks(payload: dict) -> list[dict] | None:
    """payload 的 `background_tasks`（單元素時為物件非陣列）；欄位缺席回 `None`。"""
    if "background_tasks" not in payload:
        return None
    raw = payload["background_tasks"]
    rows = [raw] if isinstance(raw, dict) else raw if isinstance(raw, list) else []
    return [r for r in rows if isinstance(r, dict)]


def stop_message(payload: dict, *, env=None, now=None) -> str:
    """Stop 事件文字（D7a）：本回合結束時仍在跑的背景代理。優先讀 payload 的 `background_tasks`，
    缺席才退回 `running()` 讀檔；沒有就回空字串。只出聲、不阻斷。"""
    try:
        sid, projects = _payload_sid(payload), _payload_projects(payload)
        tasks = _tasks(payload)
        if tasks is not None:
            agents = [{"id": t.get("id"), "description": t.get("description") or "",
                       "model": t.get("agent_type") or ""}
                      for t in tasks if t.get("type") == "subagent"
                      and str(t.get("status") or "running") == "running"]
            shells = sum(1 for t in tasks if t.get("type") == "shell")
        else:
            agents, shells = (running(sid, projects_dir=projects, now=now) if sid else []), 0
        if not agents and not shells:
            return ""
        parts = []
        for agent in agents[:5]:
            ctx = agent_context(sid, str(agent.get("id") or ""), projects_dir=projects)
            parts.append(f"{agent.get('description') or agent.get('id')}"
                         f"（{agent.get('model') or '模型未知'}"
                         f"{f'，上下文 {ctx:,}' if ctx else ''}）")
        what = f"{len(agents)} 支背景代理" if agents else "背景任務"
        head = f"本回合結束時仍有 {what}在跑"
        tail = f"；另有 {shells} 個背景 shell" if shells and agents else (
            f"（{shells} 個背景 shell）" if shells else "")
        return (f"{head}：{'、'.join(parts)}{tail}。要停子代理請由擁有者 TaskStop；"
                "無人視窗用 python tools/sessionctl.py stop --window <sid>。")
    except Exception:  # noqa: BLE001 — 出聲失敗不得擋回合結束
        return ""


def render_snapshot(snap: dict) -> str:
    """給人看的名冊。殘局明說非燒額度中；每類為空也印一行（空＝量到的零，不是漏印）。"""
    names = {"running": "執行中", "quiet": "安靜", "residue": "殘局（未收尾記錄，非燒額度中）"}
    lines = ([f"背景代理 {len(snap['agents'])} 支："] if snap["agents"]
             else ["背景代理：無（量到的零）"])
    for a in snap["agents"]:
        total = f"、累計 {a['total_tokens']:,}" if a.get("total_tokens") else ""
        lines.append(f"  [{names[a['state']]}] {a['id']}｜{a['description'] or '（無描述）'}｜"
                     f"{a['model'] or '模型未知'}｜上下文 {a['ctx_tokens'] if a['ctx_tokens'] is not None else '量不到'}"  # noqa: E501
                     f"{total}｜最後 {a['last_at']}｜擁有者 {a['owner_sid'][:8]}")
    lines.append("視窗行程：" + ("；".join(
        f"pid {w['pid']} sid {w['sid'][:8] or '?'}{'（無人）' if w['unattended'] else ''}"
        for w in snap["windows"]) or "無（或未列舉）"))
    lines.append("排程：" + ("、".join(snap["schedules"]) or "無（或未查詢）"))
    lines.append("過期哨兵：" + ("、".join(snap["stale_sentinels"]) or "無"))
    lines.append("未 ack 交接包：" + ("、".join(snap["handoffs"]) or "無"))
    return "\n".join(lines) + "\n"


def stop_window(session_id: str, *, runner=None, platform_name=None, now=None, **seams) -> int:
    """停某 session 的視窗行程樹（先驗 pid 身分再砍，驗不到不砍）；本體在 `procstop`。"""
    return procstop.stop_window(session_id, runner=runner, platform_name=platform_name, now=now,
                                **seams)


def cli(argv: list[str]) -> int:
    """`status [--session <sid>]`｜`stop --window <sid>｜--all-unattended`。"""
    import argparse  # noqa: PLC0415

    parser = argparse.ArgumentParser(prog="sessionctl", description="名冊與停止")
    sub = parser.add_subparsers(dest="cmd", required=True)
    status = sub.add_parser("status", help="唯讀名冊")
    status.add_argument("--session", default=None)
    stop = sub.add_parser("stop", help="停無人／互動視窗行程樹（先驗身分）")
    group = stop.add_mutually_exclusive_group(required=True)
    group.add_argument("--window", metavar="SID")
    group.add_argument("--all-unattended", action="store_true")
    args = parser.parse_args(argv)
    if args.cmd == "status":
        sys.stdout.write(render_snapshot(snapshot(args.session, runner=procstop.default_runner)))
        return 0
    if args.window:
        return stop_window(args.window)
    return procstop.stop_all_unattended()
