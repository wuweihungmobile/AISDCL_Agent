"""舊視窗有條件自動關閉（DES §7.1；TCS REQ-WP-54～59、98；掌舵者 2026-11-19 裁決＝有條件自動關）。

判準與執行住這裡；呼叫端只有 `handoff.ack`（跨 sid：`--spawn`／forward／park 開新 sid）、`park_cli`
到點（同 sid：先關再 `claude -r`，見 `oldwin_park`）、重試入口 `sessionctl oldwin --retry`
（`oldwin_sched`）。
**五個條件全部成立才關**（`eligible` 純判準、回逐條證據）：①登記檔 `sessionId`＋`procStart` 與
GetProcessTimes 全等且 `entrypoint=cli`（只關互動視窗）；②登記檔 `status=idle`、名冊無
running 子代理、
逐字稿無 running 的非保溫背景 shell；③最後一次真人打字（`forward` 同一個
`is_forwardable_prompt`）距今
超過 `AUTOSDD_OLDWIN_QUIET_MINUTES`（出廠 5）；④跨 sid：交接包已 `.ack` 且新 sid 逐字稿已有
assistant
記錄；⑤Windows。另有否決（`留：`，永久、綁交接包）與整體開關。**看不懂就不關**（缺欄、值不認得、
讀不到逐字稿都算不成立）。關閉本體是 `procstop.terminate_tree_verified`（handle 驗身分＋TOCTOU
重驗）。
誠實劃界：舊視窗輸入框裡**還沒送出**的字不在逐字稿也不在登記檔，關了就沒了（③與 TOCTOU 只降低
風險）。
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import endurance_env
import transcript_activity

from . import handoff, procstop, roster, seal, switch

QUIET_ENV = "AUTOSDD_OLDWIN_QUIET_MINUTES"
QUIET_DEFAULT_MINUTES = 5.0
OFF_ENV = "AUTOSDD_OLDWIN_AUTOCLOSE_OFF"
MAX_RETRIES = 3  # 每個交接包至多重試次數（所有範圍同一數字，DES r4）
_BG_TOOLS = ("Bash", "PowerShell")
_TOOL_ID_RE = re.compile(r"<tool-use-id>([^<]+)</tool-use-id>")
_GONE_NOTE = "舊視窗輸入框中未送出的文字不會保留"


def _dir(write: bool = False) -> Path:
    return (endurance_env.trace_dir() if write else endurance_env.trace_dir_peek()[0]) / "oldwin"


def event(name: str, **fields) -> None:
    """追加一行 `oldwin/events.jsonl`（寫不進去不拋：痕跡是證據不是判準）。"""
    try:
        folder = _dir(True)
        folder.mkdir(parents=True, exist_ok=True)
        rec = {"event": name, "at": datetime.now().astimezone().isoformat(timespec="seconds"),
               **fields}
        with (folder / "events.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


def events(name: str | None = None) -> list[dict]:
    """讀 `oldwin/events.jsonl`（可只取某事件）。"""
    out = []
    try:
        for line in (_dir() / "events.jsonl").read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict) and (name is None or rec.get("event") == name):
                out.append(rec)
    except OSError:
        pass
    return out


def retry_count(pkg) -> int:
    return sum(1 for rec in events("oldwin_retry_scheduled") if rec.get("handoff") == str(pkg))


def veto_path(pkg, write: bool = False) -> Path:
    return _dir(write) / "veto" / f"{Path(pkg).stem}.json"


def vetoed(pkg) -> bool:
    return veto_path(pkg).is_file()


def record_keep_veto(sid: str, transcript_path, env=None,
                     now: datetime | None = None) -> Path | None:
    """`留：` 提示的否決（D-17）：本 sid 名下「自動關閉可能作用的交接包」（已封存、已 spawn、
    或已 ack 者中最新一份）寫 `veto/<包 stem>.json` 與 `oldwin_keep_veto`。名下沒有 ⇒ 不寫
    （沒有東西可否決）。
    永久、只綁該包；程式與 `--sweep` 都不刪。任何失敗回 `None`、不拋（hook 內呼叫）。"""
    try:
        env = os.environ if env is None else env
        for row in reversed(handoff.list_handoffs(None, None, env)):
            pkg = Path(row["path"])
            if row["sid"] == str(sid) and (seal.sealed_path(pkg).exists() or seal._spawned(pkg)
                                           or pkg.with_suffix(".ack").exists()):
                path = veto_path(pkg, True)
                path.parent.mkdir(parents=True, exist_ok=True)
                at = handoff._aware(now).isoformat(timespec="seconds")
                body = {"sid": sid, "handoff": str(pkg), "at": at,
                        "transcript": str(transcript_path)}
                path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8",
                                newline="\n")
                event("oldwin_keep_veto", sid=sid, handoff=str(pkg))
                return path
    except Exception:  # noqa: BLE001 — hook 內任何例外一律當沒寫
        pass
    return None


# ───────────────────────────────────────────────────────────── 逐字稿判準
def _epoch(raw) -> float | None:
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _transcript(sid: str, env, projects_dir=None) -> Path | None:
    if projects_dir is not None:
        path = Path(projects_dir) / f"{sid}.jsonl"
        return path if path.is_file() else None
    import harness_feed  # noqa: PLC0415 — lazy

    return harness_feed.pick_transcript(handoff._project_dir(handoff._REPO), sid, env)[0]


#: 背景 shell 的 task id 有兩條記錄路徑：啟動時 tool_result 回 `Command running in background with
#: ID: <task_id>`（對應 tool_use_id）；被 `TaskStop` 結束時 tool_result 回 `Successfully stopped
#: task: <task_id>`。TaskStop 結束**不會**產生 `<task-notification>`（2026-11-21 真機：舊視窗被
#: 已停的計時 shell 誤判成「還在跑」，三次重試後放棄、舊視窗沒關）。
_STARTED_RE = re.compile(r"Command running in background with ID: ([A-Za-z0-9_-]+)")
_STOPPED_RE = re.compile(r"Successfully stopped task: ([A-Za-z0-9_-]+)")
_BG_MARKS = ("run_in_background", "<task-notification>", "Command running in background",
             "Successfully stopped task")


def _result_text(content) -> str:
    """tool_result 的 content（字串或 text 區塊列）攤成純文字。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(str(b.get("text", "")) for b in content if isinstance(b, dict))
    return ""


def bg_shells(path: Path | None) -> tuple[dict[str, str], set[str]]:
    """`(running 的非保溫背景 shell {tool_use_id: 命令列}, 全部背景 shell 呼叫 id)`。running＝
    `run_in_background` 的 Bash／PowerShell 呼叫，扣掉已收到 `<task-notification>`（完成或
    killed）者、已被 `TaskStop` 結束者（tool_result `Successfully stopped task: <task_id>`，
    task_id 由啟動 tool_result 對回 tool_use_id），
    再扣掉 `roster.WATCH_CMD_RE`／`KEEPWARM_CMD_RE`（保溫與監督 shell 會隨行程樹結束，不算忙）。"""
    calls: dict[str, str] = {}
    done: set[str] = set()
    task_of: dict[str, str] = {}  # tool_use_id → harness task id
    stopped: set[str] = set()     # 被 TaskStop 結束的 task id
    try:
        with Path(path).open(encoding="utf-8", errors="replace") as handle:  # type: ignore[arg-type]
            for line in handle:
                if not any(mark in line for mark in _BG_MARKS):
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(rec, dict):
                    continue
                if rec.get("type") == "user":
                    content = (rec.get("message") or {}).get("content")
                    for blk in content if isinstance(content, list) else ():
                        if not (isinstance(blk, dict) and blk.get("type") == "tool_result"):
                            continue
                        text = _result_text(blk.get("content"))
                        if started := _STARTED_RE.search(text):
                            task_of[str(blk.get("tool_use_id"))] = started.group(1)
                        if stop := _STOPPED_RE.search(text):
                            stopped.add(stop.group(1))
                if rec.get("type") == "assistant" and not rec.get("isSidechain"):
                    for blk in (rec.get("message") or {}).get("content") or []:
                        inp = blk.get("input") if isinstance(blk, dict) else None
                        if (isinstance(inp, dict) and blk.get("type") == "tool_use"
                                and blk.get("name") in _BG_TOOLS and inp.get("run_in_background")):
                            calls[str(blk.get("id"))] = str(inp.get("command") or "")
                    continue
                att = rec.get("attachment")
                text = (rec.get("content") if rec.get("type") == "queue-operation" else
                        att.get("prompt") if isinstance(att, dict) else None)
                if isinstance(text, str) and text.startswith("<task-notification>"):
                    found = _TOOL_ID_RE.search(text)
                    if found:
                        done.add(found.group(1))
    except (OSError, TypeError):
        return {}, set()
    running = {tid: cmd for tid, cmd in calls.items() if tid not in done
               and task_of.get(tid) not in stopped
               and not roster.WATCH_CMD_RE.search(cmd) and not roster.KEEPWARM_CMD_RE.search(cmd)}
    return running, set(calls)


def human_prompts(path: Path | None) -> list[dict]:
    """可轉送的真人提示（沿用 `forward` 同一個判準函式 `is_forwardable_prompt`）。"""
    return [p for p in transcript_activity.all_human_prompts(path)
            if transcript_activity.is_forwardable_prompt(p["text"])]


def _has_assistant(path: Path | None) -> bool:
    return path is not None and any(
        rec.get("type") == "assistant" for rec in transcript_activity._records(path, '"assistant"'))


def quiet_seconds(env) -> float:
    try:
        return max(0.0, float(env.get(QUIET_ENV) or QUIET_DEFAULT_MINUTES)) * 60
    except (TypeError, ValueError):
        return QUIET_DEFAULT_MINUTES * 60


# ───────────────────────────────────────────────────────────── 五條件（純判準）
def eligible(old_sid: str, pkg, *, new_sid: str = "", same_sid: bool = False, env=None,
             now: datetime | None = None, sessions_dir=None, projects_dir=None, transcript=None,
             new_transcript=None, created_of=None, platform_name: str | None = None,
             roster_running=None) -> dict:
    """回 `{ok, reason, cond, terminal, retry_at, evidence, target, snap}`。`reason` 空＝可關；
    `cond`＝不成立的條件編號（1～5，否決／開關為 `None`）；`terminal`＝重試也沒用（身分驗不到、
    否決、
    開關、非 Windows）；`retry_at`（epoch）＝③ 會成立的最早時刻。`snap` 供 TOCTOU 重驗比對。"""
    env, now = os.environ if env is None else env, handoff._aware(now)
    out: dict = {"ok": False, "reason": "", "cond": None, "terminal": False, "retry_at": None,
                 "evidence": {}, "target": None, "snap": None}

    def no(reason: str, cond: int | None = None, terminal: bool = False) -> dict:
        out.update(reason=reason, cond=cond, terminal=terminal)
        return out

    if vetoed(pkg):
        return no("kept_by_user", terminal=True)
    if env.get(OFF_ENV) or env.get(handoff.UNATTENDED_ENV) or switch.switch_mode(env) != "auto":
        return no("disabled")
    if (platform_name or sys.platform) != "win32":
        return no("platform_not_windows", 5, True)
    wins = procstop.live_windows_of(old_sid, folder=sessions_dir, created_of=created_of)
    cli = [w for w in wins if w.get("entrypoint") == "cli"]
    out["evidence"][1] = {"live": [w["pid"] for w in wins], "cli": [w["pid"] for w in cli]}
    if len(cli) != 1:  # 缺登記檔、procStart 對不上、entrypoint 非 cli、或多個互動視窗 ⇒ 非目標
        return no("identity_unverified", 1, True)
    target = out["target"] = cli[0]
    if not same_sid:
        acked = Path(pkg).with_suffix(".ack").exists()
        spoke = _has_assistant(new_transcript or _transcript(new_sid, env, projects_dir))
        out["evidence"][4] = {"acked": acked, "new_session_has_assistant": spoke}
        if not (acked and spoke):
            return no("new_session_not_confirmed", 4)
    path = transcript or _transcript(old_sid, env, projects_dir)
    if path is None:
        return no("transcript_unreadable", 3)
    running = (roster_running or roster.running)(old_sid, projects_dir=projects_dir, now=now)
    shells, all_bg = bg_shells(path)
    out["evidence"][2] = {"status": target.get("status"), "agents": len(running),
                          "bg_shells": sorted(shells.values())}
    if target.get("status") != "idle":  # 缺欄或不認得的值（含 busy）一律不成立
        return no("not_idle", 2)
    if running or shells:
        return no("agents_or_shell_running", 2)
    prompts = human_prompts(path)
    last = _epoch(prompts[-1]["at"]) if prompts else None
    out["evidence"][3] = {"last_prompt_at": prompts[-1]["at"] if prompts else None,
                          "quiet_s": quiet_seconds(env)}
    out["snap"] = {"pid": target["pid"], "start": int(target["procStart"]), "path": str(path),
                   "prompts": len(prompts), "bg_ids": sorted(all_bg)}
    if prompts and last is None:
        return no("last_prompt_time_unknown", 3)
    if last is not None and now.timestamp() - last <= quiet_seconds(env):
        out["retry_at"] = last + quiet_seconds(env) + 60
        return no("recent_human_prompt", 3)
    out["ok"] = True
    return out


def recheck(old_sid: str, pkg, snap: dict, *, sessions_dir=None, created_of=None) -> str:
    """TOCTOU 重驗（DES §7.1 第 5 點）：五條件判斷之後、第一個 `TerminateProcess` 之前再看一次
    登記檔、
    逐字稿尾段與否決檔；回空字串＝沒變，否則 `toctou_<項>`。"""
    if vetoed(pkg):
        return "toctou_veto"
    now_row = next((w for w in procstop.live_windows_of(old_sid, folder=sessions_dir,
                                                        created_of=created_of)
                    if w["pid"] == snap["pid"]), None)
    if (now_row is None or now_row.get("status") != "idle"
            or int(now_row["procStart"]) != snap["start"]):
        return "toctou_registry"
    path = Path(snap["path"])
    if len(human_prompts(path)) > snap["prompts"]:
        return "toctou_prompt"
    if bg_shells(path)[1] - set(snap["bg_ids"]):
        return "toctou_bg"
    return ""


# ───────────────────────────────────────────────────────────── 出聲（notice）
def notice(sid: str, text: str) -> None:
    """追加給新 session 的出聲 `oldwin/<sid>.notice.jsonl`（hook 端擇先出聲一次、標已讀）。"""
    try:
        folder = _dir(True)
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / f"{sid}.notice.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
            at = datetime.now().astimezone().isoformat(timespec="seconds")
            handle.write(json.dumps({"at": at, "text": text}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def take_unread_notice(sid: str) -> str:
    """未讀 notice 全文（換行串接）並標已讀（`<sid>.notice.read` 記已讀行數）；沒有回空字串。"""
    try:
        lines = (_dir() / f"{sid}.notice.jsonl").read_text(encoding="utf-8").splitlines()
        marker = _dir(True) / f"{sid}.notice.read"
        seen = int(marker.read_text(encoding="utf-8").strip() or 0) if marker.exists() else 0
        texts = [json.loads(ln).get("text", "") for ln in lines[seen:]]
        if texts:
            marker.write_text(str(len(lines)), encoding="utf-8")
        return "\n".join(t for t in texts if t)
    except (OSError, ValueError):
        return ""


def pending_manual_close(sid: str, sessions_dir=None, created_of=None) -> str:
    """放棄／降級自動關閉後，本 session（新窗）每個回合都提醒、直到舊視窗真的關掉為止（不只一次性
    notice：2026-11-21 真機＝放棄只留一則可能沒被看到的 notice，掌舵者見兩個視窗問同一件事）。
    判準＝`oldwin_retry_abandoned`／`oldwin_close_degraded` 事件中 `new`＝本 sid、且該舊 sid 仍有
    活著的互動視窗（`procstop.live_windows_of`，procStart 驗過）。回空字串＝沒有待手動關的窗。"""
    seen: dict[str, dict] = {}
    for name in ("oldwin_retry_abandoned", "oldwin_close_degraded"):
        for rec in events(name):
            if rec.get("new") == sid and rec.get("old"):
                seen[str(rec["old"])] = rec
    lines = []
    for old in seen:
        for win in procstop.live_windows_of(old, folder=sessions_dir, created_of=created_of):
            if win.get("entrypoint") == "cli":
                lines.append(f"舊視窗（pid={win['pid']}，sid {old[:8]}）還開著，自動關閉沒成功，"
                             "請手動關閉舊視窗，以免兩個視窗問同樣的問題。")
    return "\n".join(lines)


def reminder_lines(env=None, sessions_dir=None, created_of=None) -> list[str]:
    """「只提醒、不關」的情形（開關停用、模式非 auto、非 Windows…）：已被別的 session `.ack` 的
    交接包，其舊 sid 若仍有活著的互動視窗，印一行請掌舵者手動關閉。給 SessionStart 與
    `sessionctl status` 用。"""
    env, out = os.environ if env is None else env, []
    for row in handoff.list_handoffs(None, None, env):
        pkg = Path(row["path"])
        if row["state"] != "acked" or seal.acker_sid(pkg) in (None, row["sid"]):
            continue
        for win in procstop.live_windows_of(row["sid"], folder=sessions_dir, created_of=created_of):
            if win.get("entrypoint") == "cli":
                out.append(f"舊視窗 pid={win['pid']} 仍開著（sid {row['sid'][:8]}），請手動關閉。")
    return out


# ───────────────────────────────────────────────────────────── 執行
def close_if_eligible(old_sid: str, new_sid: str, pkg, *, same_sid: bool = False,
                      notify: bool = True, env=None, now: datetime | None = None, api=None,
                      images=procstop.image_allowed, self_pid=None, schedule=None, sleep=None,
                      wait: float = procstop.TERMINATE_WAIT_SECONDS, **seams) -> dict:
    """判準通過就關（先寫 intent → handle 驗身分 → TOCTOU 重驗 → 由葉往根終止）。回
    `{closed, pid, reason, cond, retry_at, scheduled, abandoned, text}`：
    · 不成立且可重試 ⇒ 跨 sid 登記重試排程（`schedule`，缺省走 `oldwin_sched`）、同 sid 只回
      `retry_at`
      讓 park 重排；已重試 `MAX_RETRIES` 次 ⇒ `abandoned`（跨 sid 另寫 notice「舊窗保留」）。
    · `notify`＝是否寫 notice（`handoff --ack` 當下關閉時已直接印字，不重複）。"""
    env, now = os.environ if env is None else env, handoff._aware(now)
    ev = eligible(old_sid, pkg, new_sid=new_sid, same_sid=same_sid, env=env, now=now, **seams)
    res = {"closed": False, "pid": None, "reason": ev["reason"], "cond": ev["cond"],
           "retry_at": None, "scheduled": None, "abandoned": False, "text": ""}
    if ev["ok"]:
        target, win_sid = ev["target"], old_sid
        if not same_sid and win_sid == new_sid:
            ev.update(ok=False, reason="target_is_caller_session", terminal=True)
            res["reason"] = ev["reason"]
        else:
            return _terminate(ev, res, old_sid, new_sid, pkg, same_sid, notify, env, now, api,
                              images, self_pid, schedule, sleep, wait, seams, target)
    event("oldwin_close_refused" if ev["cond"] == 1 or ev["reason"] == "target_is_caller_session"
          else "oldwin_not_eligible", old=old_sid, new=new_sid, handoff=str(pkg),
          reason=ev["reason"], cond=ev["cond"], evidence=ev["evidence"])
    return _retry_or_note(ev, res, old_sid, new_sid, pkg, same_sid, notify, env, now, schedule)


def _manual_text(pid, reason: str, retries: int = 0) -> str:
    """自動關不掉時給人看的白話（放棄／降級共用）：指名 pid、寫明「請手動關閉舊視窗」與原因。"""
    who = f"（pid={pid}）" if pid else ""
    tried = f"已自動重試 {retries} 次仍不行，" if retries else "自動關閉沒有成功，"
    return (f"舊視窗{who}沒有被自動關閉：{tried}原因＝{reason}。"
            f"請手動關閉舊視窗，以免兩個視窗問同樣的問題；{_GONE_NOTE}。")


def _terminate(ev, res, old_sid, new_sid, pkg, same_sid, notify, env, now, api, images, self_pid,
               schedule, sleep, wait, seams, target) -> dict:
    from . import winproc  # noqa: PLC0415 — lazy

    pid, start = target["pid"], int(target["procStart"])
    done = procstop.terminate_tree_verified(
        pid, start, api=api or winproc.WinApi(), images=images, self_pid=self_pid, sleep=sleep,
        wait=wait,
        intent=lambda plan: event("oldwin_close_intent", old=old_sid, new=new_sid,
                                  handoff=str(pkg), evidence=ev["evidence"], **plan),
        recheck=lambda: recheck(old_sid, pkg, ev["snap"], sessions_dir=seams.get("sessions_dir"),
                                created_of=seams.get("created_of")))
    res.update(pid=pid, reason=done["reason"])
    if done["ok"]:
        res.update(closed=True, text=f"已關閉舊視窗 pid={pid}（sid {old_sid}）。{_GONE_NOTE}。")
        event("oldwin_closed", old=old_sid, new=new_sid, handoff=str(pkg), pid=pid,
              killed=done["killed"])
        if notify:
            notice(new_sid, res["text"])
        return res
    kind = "oldwin_close_failed" if done["reason"] == "still_running" else "oldwin_close_refused"
    event(kind, old=old_sid, new=new_sid, pid=pid, reason=done["reason"], killed=done["killed"])
    if done["reason"] in procstop.DEGRADABLE_REASONS:  # 關不了（≠不該關）：不排重試，出聲請人關
        res["text"] = _manual_text(pid, done["reason"])
        event("oldwin_close_degraded", old=old_sid, new=new_sid, handoff=str(pkg), pid=pid,
              reason=done["reason"])
        if notify and not same_sid:
            notice(new_sid, res["text"])
        return res
    retryable = done["reason"].startswith("toctou_")
    ev.update(reason=done["reason"], cond=None, terminal=not retryable)
    return _retry_or_note(ev, res, old_sid, new_sid, pkg, same_sid, notify, env, now, schedule)


def _retry_or_note(ev, res, old_sid, new_sid, pkg, same_sid, notify, env, now, schedule) -> dict:
    """不關時的後續：可重試者排程（跨 sid）或回 `retry_at`（同 sid）；滿 `MAX_RETRIES` 放棄。"""
    reason = ev["reason"]
    if ev["terminal"] or (reason in ("disabled", "platform_not_windows") and not same_sid):
        if reason == "kept_by_user":  # 其餘（身分驗不到、停用、非 Windows）沿用呼叫端的「只提醒」
            res["text"] = "舊視窗保留（掌舵者以『留：』保留，不自動關閉）。"
        return res
    quiet = quiet_seconds(env)
    when = max(ev["retry_at"] or 0.0, now.timestamp() + 60) if ev.get("retry_at") else (
        now.timestamp() + max(quiet, 60))
    res["retry_at"] = when
    if retry_count(pkg) >= MAX_RETRIES:
        res.update(abandoned=True, text=_manual_text((ev.get("target") or {}).get("pid"), reason,
                                                     MAX_RETRIES))
        event("oldwin_retry_abandoned", old=old_sid, new=new_sid, handoff=str(pkg), reason=reason)
        if notify and not same_sid:
            notice(new_sid, res["text"])
        return res
    if same_sid:  # park 自己重排到點排程；計數由呼叫端經 `note_retry` 記
        return res
    from . import oldwin_sched  # noqa: PLC0415 — lazy

    rc, cred = (schedule or oldwin_sched.schedule_retry)(old_sid, new_sid, pkg, when, env=env,
                                                         now=now)
    if rc != 0 or not str(cred).strip():
        res["text"] = f"舊視窗暫不關閉（{reason}），但重試排程沒有成立（憑證取不到）。"
        return res
    note_retry(pkg, when, old_sid, new_sid, str(cred))
    res.update(scheduled=str(cred), text=f"舊視窗暫不關閉（{reason}）；已排程重試（{cred}）。")
    return res


def note_retry(pkg, when: float, old_sid: str, new_sid: str, credential: str = "") -> None:
    """記一次重試（`oldwin_retry_scheduled`）：`retry_count` 與每交接包 3 次上限的唯一帳。"""
    event("oldwin_retry_scheduled", handoff=str(pkg), old=old_sid, new=new_sid,
          credential=credential,
          fire_at=datetime.fromtimestamp(when).astimezone().isoformat(timespec="seconds"))


def on_ack(pkg, me: str, env=None, **kw) -> str:
    """`handoff --ack` 當下（跨 sid）：順手清 stale 重試工作，再試著關舊窗；回 ack 要印的文字，
    空字串＝
    沒什麼可說（呼叫端沿用既有提示）。永不拋——ack 本身不得因這裡失敗。"""
    try:
        old = handoff._sid_of(Path(pkg))
        if not me or me == old:
            return ""
        from . import oldwin_sched  # noqa: PLC0415 — lazy

        oldwin_sched.sweep(env=env)
        return close_if_eligible(old, me, pkg, notify=False, env=env, **kw)["text"]
    except Exception:  # noqa: BLE001
        return ""
