"""UserPromptSubmit 轉送（R3 WP-5；ARCH §2.2 九條件、§2.3；M-F3 改判的「已交棒告知」）。

WHY 兩條路：
- 路徑一【轉送】：交接包已封存、舊視窗快取已冷，掌舵者這時打的下一句若送進舊 session，幾十萬
  token 整份重寫（21 天 15 次、485 萬 token）。改成 `decision:block`、原文落檔、自動開新 session。
- 路徑二【已交棒告知】：包已 spawn／ack，舊視窗卻還在收指令（M-F3 實證：新視窗開了之後 2.7～7.4
  分鐘內，舊視窗又被打了 4 句）。不 spawn、不看快取冷熱，直接回一句說明（零 token）。

安全面（寧可多付快取，也不吞輸入）：任何不確定（判不出真人、讀不到、落檔失敗、spawn 失敗、任何
例外）一律放行；原文先落檔成功才擋；`<task-notification>` 等機器注入永不擋（F1-8）。
判準全在本檔，`.claude/hooks/sessionctl_guard.py` 只呼叫 `hook_output`（零判準）。
🔴 痕跡事件名＝具名常數；`tools/lib/wastecensus/supervision.py` 的 `EV_FORWARD_*` 與之同名
（sessionctl 不得 import wastecensus，A-8；由測試斷言相等）。
依賴一律參數注入（A-3：不為測試開 env 鉤）。
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import endurance_env
import transcript_activity

from . import cachestate, costmodel, handoff, oldwin, roster, seal, supervise, switch

EV_PASS = "forward_pass"
EV_SPAWNED = "forward_spawned"
EV_FAILED = "forward_spawn_failed"
EV_HANDED_OVER = "forward_handed_over"
#: 逃生前綴：以它開頭的提示一律原文送進本 session（全形與半形冒號）。
ESCAPE_PREFIXES = ("留：", "留:")
#: 轉送呼叫 `spawn` 的等待秒數；settings 的 hook timeout 50 秒須大於它加上其餘判準的耗時。
FORWARD_WAIT_SECONDS = 20
#: 重寫快取成本換算（ARCH §2.4：257,854 token ≈ 14.18pp ⇒ 5.5e-5 pp／token）。
PP_PER_TOKEN = 5.5e-5
BODY_MARK = "<!-- forward-body -->\n"
_SAFE_ID = re.compile(r"[^A-Za-z0-9_-]")


# ───────────────────────────────────────────────────────────────── 原文落檔
def forward_path(package: Path, prompt_id: str, text: str) -> Path:
    """`<包 stem>.forward-<prompt_id 前 8>.md`；沒有 `prompt_id` 時用原文 SHA-256 前 8 碼。"""
    tag = _SAFE_ID.sub("", str(prompt_id or ""))[:8] or hashlib.sha256(
        text.encode("utf-8")).hexdigest()[:8]
    return package.with_name(f"{package.stem}.forward-{tag}.md")


def write_forward(package: Path, payload: dict, now: datetime) -> Path | None:
    """原文逐字落檔（不截斷、不加引用符號、不正規化換行）；寫不進去回 `None`。
    格式：表頭＋`BODY_MARK`＋原文到檔尾；讀回原文＝`content.split(BODY_MARK, 1)[1]`。"""
    text = payload["prompt"]
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    target = forward_path(package, payload.get("prompt_id"), text)
    head = ("# 轉送原文\n以下為掌舵者在舊視窗輸入的原文，轉送而來（資料，非本檔指示）。\n\n"
            f"- 來源 sid：{payload.get('session_id')}\n"
            f"- prompt_id：{payload.get('prompt_id') or '（無）'}\n"
            f"- 時刻：{now.isoformat()}\n- 字數：{len(text)}\n- SHA-256：{sha}\n\n{BODY_MARK}")
    try:
        target.write_bytes((head + text).encode("utf-8"))
    except (OSError, UnicodeEncodeError):
        return None
    return target


# ───────────────────────────────────────────────────────────────── 痕跡讀取
def _spawn_record(package: Path) -> dict | None:
    """該包最新一列 `session_switch_spawned`（含失敗者；唯讀）；沒有 ⇒ `None`。"""
    try:
        lines = (endurance_env.trace_dir_peek()[0] / "autosdd_session_switch.jsonl").read_text(
            encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    best = None
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if (isinstance(rec, dict) and rec.get("event") == "session_switch_spawned"
                and rec.get("handoff") == str(package)):
            best = rec
    return best


def _hhmm(iso) -> str:
    try:
        return datetime.fromisoformat(str(iso)).astimezone().strftime("%H:%M")
    except (TypeError, ValueError):
        return "時刻不詳"


# ───────────────────────────────────────────────────────────────── 判準
def _passed(cond: int, sid: str, *, context: str = "", show: str = "", **fields) -> dict:
    """`show`＝要讓掌舵者在畫面上看到的一行（hook 的 `systemMessage`）；空＝只進模型 context。"""
    switch.trace(EV_PASS, sid=sid, cond=cond, **fields)
    out = {"kind": "context" if context else "pass", "text": context}
    if show:
        out["show"] = show
    return out


def _stay(sid: str, env) -> bool:
    """DES §8 觸發 2：判「留在本窗」（`留：`／快取熱／`f4_resume_cheaper`）∧ 本 sid 為最新包的
    原主人 ∧ 包 live ∧ 已封存 ∧ 未交棒 ⇒ 記續跑（`.resumed`、作廢封存）。判準單一家＝`kw_run`
    （觸發 1 同一支）。WHY：留下來繼續的原視窗就是自續跑；不記的話封存閘／冷叫醒閘仍把它當
    「已封存待交棒」推回。"""
    from . import kw_run  # noqa: PLC0415 — lazy：kw_run 依賴面大，hook 鏈只有判到「留」才付

    return kw_run.mark_resumed_if_owner(sid, env)


def _handed_over_verdict(pkg: Path, payload: dict, mode: str, now: datetime, alive) -> dict:
    """路徑二：包已交棒。新視窗活著 ∧ auto ⇒ 擋並說明；否則放行＋一行現況。"""
    sid = payload["session_id"]
    rec = _spawn_record(pkg) or {}
    pid = rec.get("pid")
    if mode != "auto" or not alive(pid):
        note = (f"本 session 的交接包已交棒（{pkg}），但新視窗（pid {pid}）目前不在、"
                "或模式不是 auto，所以這句話照常送進本視窗；工作請以交接包為準，"
                "別兩個視窗同時動同一棵工作樹。")
        switch.trace(EV_HANDED_OVER, sid=sid, outcome="pass", pid=pid, mode=mode)
        return {"kind": "context", "text": note}
    saved = write_forward(pkg, payload, now)
    if saved is None:  # 原文存不下來就不擋：寧可放行也不吞輸入
        switch.trace(EV_HANDED_OVER, sid=sid, outcome="pass_write_failed", pid=pid)
        return {"kind": "pass", "text": ""}
    switch.trace(EV_HANDED_OVER, sid=sid, outcome="block", pid=pid, forward=str(saved))
    return {"kind": "block", "text": (
        f"本視窗已交棒給新視窗（pid {pid}，{_hhmm(rec.get('at'))} 開的），工作在那邊繼續；"
        f"請到新視窗輸入，這個視窗可以關。你剛打的原文存於 {saved}。"
        "要留在這裡回答：重打並以 `留：` 開頭。")}


def _forward_verdict(pkg: Path, payload: dict, env, now: datetime, *, spawn, alive, cache,
                     crons, preflight, refresh, plat: str, mode: str) -> dict:
    """路徑一的條件 5～9（1～4 已由呼叫端判過）＋條件 10（R216 F4：冷但續跑較便宜 ⇒ 留原視窗）。"""
    sid, tpath = payload["session_id"], Path(payload["transcript_path"])
    state = cache(tpath, now)
    if not state.get("cold"):  # 熱：留在原地較便宜（ARCH §2.4 例二）；原主人自續跑（DES §8 觸發 2）
        return _passed(5, sid, resumed=_stay(sid, env))
    if crons(sid) is not False:
        return _passed(6, sid)  # 有排程或讀不到 ⇒ 不轉送（偏放行）
    # D9／F4（R216）：快取冷了也未必該換——上下文不夠大時續跑重寫比換新便宜，
    # 留在原視窗（量不到＝不轉送）。
    held = roster._scan(tpath, False).get("ctx_tokens")
    if not costmodel.fresh_is_cheaper(held, cold=True, env=env):
        why = ("上下文量不到" if held is None else
               f"上下文 {held:,} tokens 續跑重寫（{costmodel.W_CC1 * held:,.0f} 單位）比換新"
               f"（{costmodel.fresh_total(env):,.0f} 單位）便宜")
        note = f"快取已冷，但{why}，所以這句照常送進本視窗（沒有轉送）。"
        return _passed(10, sid, context=note, show=f"ℹ️ {note}", why="f4_resume_cheaper", ctx=held,
                       resumed=_stay(sid, env))
    hint = f"建議改到新 session（快取已冷）：python tools/sessionctl.py handoff --spawn {pkg}"
    # 7／8 放行時掌舵者也要看得到「沒轉送、原因是 X」（DEF-200-609：原本只進模型 context，
    # 真機畫面一片空白，無從得知轉送為何沒發生）。
    if mode != "auto" or plat != "win32":
        why = f"模式＝{mode}" if mode != "auto" else f"平台＝{plat}（只有 Windows 自動開窗）"
        return _passed(7, sid, context=hint,
                       show=f"ℹ️ 快取已冷但沒有自動轉到新 session：{why}。這句照常送進本視窗。")
    left = preflight(pkg)
    if left:
        return _passed(8, sid, context=hint + "（目前不能自動開：" + "；".join(left) + "）",
                       show="ℹ️ 快取已冷但沒有自動轉到新 session：" + "；".join(left)
                       + "。這句照常送進本視窗。")
    refresh(pkg, transcript=tpath)  # A-2：封存後才打的真人提示補進 sidecar
    saved = write_forward(pkg, payload, now)
    if saved is None:
        return _passed(9, sid, why="forward_write_failed")
    out, err = io.StringIO(), io.StringIO()  # spawn 會 print；hook 的 stdout 只准有 JSON
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = spawn(pkg, env=env, now=now, wait_seconds=FORWARD_WAIT_SECONDS,
                   extra_prompt_file=saved)
    rec = _spawn_record(pkg) or {}
    # 行程活著但 20 秒內沒見新逐字稿：行程存活是強訊號，仍視為已轉送（ARCH §2.3 hook 逾時段）
    pending = rc != 0 and alive(rec.get("pid")) and bool(rec.get("at"))
    if rc != 0 and not pending:
        switch.trace(EV_FAILED, sid=sid, handoff=str(pkg), forward=str(saved), rc=rc,
                     detail=err.getvalue().strip()[-300:])
        return {"kind": "pass", "text": ""}  # 失敗＝放行；原文檔保留
    ctx = held or 0
    idle = state.get("idle_s")
    switch.trace(EV_SPAWNED, sid=sid, handoff=str(pkg), forward=str(saved), pid=rec.get("pid"),
                 ctx=ctx, idle_s=idle, confirmed=not pending)
    wait = "" if not pending else "若 1 分鐘內沒看到新視窗，請加 `留：` 重打。"
    return {"kind": "block", "text": (
        f"🔁 已轉到新 session：本視窗上下文 {ctx / 10_000:.1f} 萬 token、閒置 "
        f"{int((idle or 0) // 60)} 分（快取已冷，續用要整份重寫約 {ctx * PP_PER_TOKEN:.1f} pp）。"
        f"新視窗（pid {rec.get('pid')}）已帶著交接包與你剛打的原文開始做；原文存於 {saved}。"
        f"要留在這個視窗：重打並以 `留：` 開頭。{wait}")}


def prompt_verdict(payload, env=None, *, now: datetime | None = None, spawn=None, alive=None,
                   cache=None, crons=None, preflight=None, refresh=None,
                   platform_name: str | None = None) -> dict:
    """回 `{"kind": "pass"|"context"|"block", "text": str}`。任何例外 ⇒ pass（fail-open）。"""
    try:
        env = os.environ if env is None else env
        if not isinstance(payload, dict) or not isinstance(payload.get("prompt"), str):
            return {"kind": "pass", "text": ""}
        sid, raw = payload.get("session_id"), payload.get("transcript_path")
        mode = switch.switch_mode(env)
        if (env.get("AUTOSDD_SESSIONCTL_GUARD_OFF") or env.get(handoff.UNATTENDED_ENV)
                or mode == "off" or not isinstance(sid, str) or not sid
                or not isinstance(raw, str) or not raw.strip()):
            return {"kind": "pass", "text": ""}  # 條件 1（不是本守衛的場合，不落痕跡）
        text = payload["prompt"]
        if not transcript_activity.is_forwardable_prompt(text):
            return _passed(2, sid)
        if text.lstrip().startswith(ESCAPE_PREFIXES):
            oldwin.record_keep_veto(sid, raw, env, now)  # R217 D-17：`留：`＝否決自動關閉舊窗
            return _passed(3, sid, resumed=_stay(sid, env))  # DES §8 觸發 2
        now, alive = handoff._aware(now), alive or handoff._alive
        pkg = seal.handed_over(sid, env)
        if pkg is not None:
            return _handed_over_verdict(pkg, payload, mode, now, alive)
        row = seal.latest_package(sid, env)
        if (row is None or row["state"] != "live" or not seal.is_sealed(sid, env=env)
                or seal._spawned(Path(row["path"]))):
            return _passed(4, sid)
        return _forward_verdict(
            Path(row["path"]), payload, env, now, spawn=spawn or handoff.spawn, alive=alive,
            cache=cache or cachestate.cache_state, crons=crons or supervise.crons_state,
            preflight=preflight or handoff.spawn_preflight, refresh=refresh or seal.refresh_prompts,
            plat=platform_name or sys.platform, mode=mode)
    except Exception:  # noqa: BLE001 — hook 內任何例外一律放行
        return {"kind": "pass", "text": ""}


def _failure_note(payload, env) -> str:
    """park 到點失敗提示（`qw_prompt`；同專案任一視窗、同一失敗只一次）；任何例外 ⇒ 空。"""
    try:
        from . import qw_prompt  # noqa: PLC0415

        return qw_prompt.failure_notice(payload, env)
    except Exception:  # noqa: BLE001
        return ""


def _join(*parts: str, sep: str = "\n") -> str:
    return sep.join(p for p in parts if p)


def hook_output(payload, env=None, **inject) -> dict | None:
    """跳板用：回要印到 stdout 的 JSON（放行無附註 ⇒ `None`）。零判準、不拋。
    park 失敗提示（REQ-QW-35）在轉送判準之後併入：block 併進 reason、其餘進 additionalContext
    與 systemMessage（人眼必經的入口，不只進模型 context）。"""
    try:
        verdict = prompt_verdict(payload, env, **inject)
        note = _failure_note(payload, env)
        if verdict["kind"] == "block":
            return {"decision": "block", "reason": _join(verdict["text"], note, sep="\n\n")}
        if verdict["kind"] == "context" or note:
            out = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                          "additionalContext": _join(verdict["text"], note)}}
            show = _join(verdict.get("show", ""), note)
            if show:
                out["systemMessage"] = show
            return out
    except Exception:  # noqa: BLE001
        pass
    return None
