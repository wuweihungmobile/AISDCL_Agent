"""主控快取保溫 `sessionctl keepwarm`＋watch 額度閂鎖（R216；設計 SessionSwitch_CostModel_Design
§3.3 F1、§4.1～§4.3、§5 D6／D7／D8／D14；掌舵者 2026-11-18：「專注在不要讓Cache過期!」）。

WHY：主控快取壽命 1 小時，且閒置約 55 分鐘 harness 會自動壓縮大上下文（9／17 次自動壓縮發生在閒置
54.6～56.5 分之後）。主控無背景工作、人離開時沒有任何事件源叫醒它——本檔補這個洞：
  · `anchor`／`deadline`：截止＝主控**最後一筆帶 usage 的 assistant 記錄**＋`T_kw`（出廠 45 分），
    不是任何程序的啟動時刻；`watch` 的保溫點與 `keepwarm` 共用同一個錨點函式。
  · 保溫帳（`trace_dir()/keepwarm/<sid>.json`）：`pings`／`n*`（F1 ski-rental 上限）；真人提示一出現
    即歸零。寫不進帳 ⇒ 判 `cap`（失效往少花走：停止保溫＝退回沒有保溫的現況，不是無界燒錢）。
  · `stop_verdict`（D6 保溫閘）：Stop 時無任何 running 背景任務 ∧ 非「不掛的情形」∧ pings < n*
    ⇒ 推回。
  · `quota_latch`（D14）：watch 的額度事件以 (sid, reset 分鐘, 帶級) 為鍵，同窗同帶只觸發一次。
全部純讀檔、零 token；時鐘／sleep 以參數注入（不開任何測試用環境變數）。
sessionctl 不得 import wastecensus；事件名常數由測試與量測端核對相等。
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import endurance_env

from . import procstop, roster, seal, switch

EV_VERDICT = "keepwarm_verdict"
EV_STOP_BLOCK = "keepwarm_stop_block"
EV_QUOTA_LATCHED = "watch_quota_latched"
SCHEMA = "autosdd.keepwarm/1"
MINUTES_KEY = "AUTOSDD_KEEPWARM_MINUTES"
MIN_CTX_KEY = "AUTOSDD_KEEPWARM_MIN_CTX_TOKENS"
OFF_ENV = "AUTOSDD_KEEPWARM_OFF"
#: 出廠值唯一的家是 `quota_policy_env.ENV_SPEC`；本常數供 `watch.Cfg` 預設用，由測試斷言兩者相等。
DEFAULT_MINUTES = 45
FLOOR_MINUTES = 15
CMD_MARK = "sessionctl.py keepwarm"
CMD = "python tools/sessionctl.py keepwarm"
#: 判決一律 rc 0、只看末行 `KEEPWARM_VERDICT=`（DEF-200-622：ping／cap 是設計內的正常叫醒，harness
#: 卻把非 0 的背景指令顯示成「failed」）。非 0 只留給真錯誤（缺 --sid／形態不合＝2）。
POLL_SECONDS = 60.0
#: F1 的單位（`tools/lib/wastecensus/reader.py` 同一組）：cache_read 0.1、主控 1h 層 cache_write
#: 2.0；P_FIX＝每次保溫的固定單位（叫醒＋重掛兩回合的輸出與新增上下文；推估值，M-K5 實測回寫）。
W_CR, W_CC1, P_FIX = 0.1, 2.0, 4500.0
DISPOSAL = {
    "ping": "什麼都不判、`python tools/sessionctl.py status` 不必跑；用同一條指令重掛 keepwarm"
            "（run_in_background、輸出導檔）後結束回合（本回合輸出 ≤ 50 token）",
    "cap": "已到保溫損益點（再保溫比放冷重寫更貴）：不重掛，直接結束回合讓快取過期",
    "skip": "本情形不需要保溫：什麼都不做、不要重掛",
}
_BANDS = {"prepare": 1, "halt": 2}


def _warn(msg: str) -> None:
    print(f"⚠️ {msg}", file=sys.stderr)


def _num(raw) -> float | None:
    try:
        return float(str(raw).strip())
    except ValueError:
        return None


def t_kw_minutes(env=None) -> float:
    """`T_kw`：env 缺席＝出廠 45；只准下修（大於 45／病態值退回 45 並出聲）、下限 15
    （低於夾到 15）。"""
    raw = str((os.environ if env is None else env).get(MINUTES_KEY) or "").strip()
    if not raw:
        return float(DEFAULT_MINUTES)
    val = _num(raw)
    if val is None or not math.isfinite(val) or val <= 0 or val > DEFAULT_MINUTES:
        _warn(f"{MINUTES_KEY}={raw!r} 不在 {FLOOR_MINUTES}～{DEFAULT_MINUTES} 分（只准下修）"
              f" ⇒ 退回出廠值 {DEFAULT_MINUTES}")
        return float(DEFAULT_MINUTES)
    if val < FLOOR_MINUTES:
        _warn(f"{MINUTES_KEY}={raw!r} 低於下限 {FLOOR_MINUTES} ⇒ 夾到 {FLOOR_MINUTES}")
        return float(FLOOR_MINUTES)
    return val


def n_star(ctx) -> int:
    """F1：最多保溫次數 `floor(R(c)/p(c))`，`R=W_CC1·c`（放冷後整份重寫）、`p=2·W_CR·c+P_FIX`
    （叫醒回合＋重掛回合各讀一次）。c=40 萬 ⇒ 9、15 萬 ⇒ 8、3 萬 ⇒ 5。"""
    c = max(int(ctx or 0), 0)
    return math.floor(W_CC1 * c / (2 * W_CR * c + P_FIX))


# ───────────────────────────────────────────────────────────── 錨點
def find_transcript(sid: str, projects_dir=None) -> Path | None:
    return roster._main_transcript(roster._projects(projects_dir), sid)


def anchor(transcript) -> float | None:
    """主控逐字稿**最後一筆帶 usage 的 assistant 記錄**時刻（epoch 秒；只讀尾端）。
    略過子代理側鏈與 `<synthetic>`（harness 補的零用量記錄，不代表真的打過 API）。
    讀不到 ⇒ `None`。"""
    if transcript is None:
        return None
    for rec in reversed(list(roster._records(Path(transcript), tail=True))):
        msg = rec.get("message")
        if rec.get("isSidechain") or roster._usage(rec) is None or (
                isinstance(msg, dict) and msg.get("model") == "<synthetic>"):
            continue
        stamp = procstop.parse_iso(rec.get("timestamp"))
        if stamp is not None:
            return stamp
    return None


def deadline(transcript, t_kw_min: float) -> float | None:
    at = anchor(transcript)
    return None if at is None else at + t_kw_min * 60


# ───────────────────────────────────────────────────────────── 保溫帳
def ledger_path(sid: str, *, write: bool = False) -> Path:
    root = endurance_env.trace_dir() if write else endurance_env.trace_dir_peek()[0]
    return root / "keepwarm" / f"{sid}.json"


def human_mark(transcript) -> str:
    """最後一則**可轉送真人提示**的標記（`時戳|行號`）；`<task-notification>` 等機器注入不算。"""
    import transcript_activity  # noqa: PLC0415 — lazy：只有帳上已有 ping 時才需要全檔掃描

    last = ""
    for p in transcript_activity.all_human_prompts(Path(transcript)):
        if transcript_activity.is_forwardable_prompt(p["text"]):
            last = f"{p['at']}|{p['line']}"
    return last


def read_ledger(sid: str) -> dict:
    """`{pings, human}`；缺檔＝零；壞檔／結構不符＝零並出聲。"""
    path = ledger_path(sid)
    try:
        row = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(row, dict) and type(row.get("pings")) is int and row["pings"] >= 0:
            return {"pings": row["pings"], "human": str(row.get("human") or "")}
        _warn(f"保溫帳 {path} 結構不符 ⇒ 當作零")
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as exc:
        _warn(f"保溫帳 {path} 讀不動（{type(exc).__name__}）⇒ 當作零")
    return {"pings": 0, "human": ""}


def load_ledger(sid: str, transcript) -> dict:
    """讀帳並套用「真人提示歸零」：帳上已有 ping 且最後一則真人提示標記變了 ⇒ pings 歸零。"""
    row = read_ledger(sid)
    if row["pings"] > 0 and human_mark(transcript) != row["human"]:
        row["pings"] = 0
    return row


def record_ping(sid: str, pings: int, ctx: int, star: int, mark: str) -> bool:
    """寫帳（pings 為新值）；寫不進去回 `False`（呼叫端判 cap）。"""
    path = ledger_path(sid, write=True)
    row = {"schema": SCHEMA, "sid": sid, "pings": pings, "n_star": star, "ctx": ctx, "human": mark}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8", newline="\n")
    except OSError as exc:
        _warn(f"保溫帳寫不進 {path}（{type(exc).__name__}）⇒ 判 cap（不保溫，退回沒有保溫的現況）")
        return False
    return True


# ───────────────────────────────────────────────────────────── 不掛的情形
def skip_reason(sid: str, env, *, ctx, now: datetime | None = None) -> str:
    """§4.1 不掛的情形；回原因代號，需要保溫 ⇒ `""`。無人窗口（print 模式背景上限會殺掉它）、模式非
    auto、`AUTOSDD_KEEPWARM_OFF`、已交棒、park 標記有效（park 接手）、上下文太小。"""
    if env.get("AUTOSDD_UNATTENDED"):
        return "unattended"
    if switch.switch_mode(env) != "auto":
        return "mode"
    if env.get(OFF_ENV):
        return "off"
    if seal.handed_over(sid, env) is not None:
        return "handed_over"
    from . import park  # noqa: PLC0415 — lazy

    if park.credential_ok(park.read_marker(sid), now or datetime.now().astimezone())[0]:
        return "park"
    if ctx is None:
        return "no_usage"
    return "small_ctx" if ctx < switch.threshold(MIN_CTX_KEY, env)[0] else ""


def is_keepwarm_task(task: dict) -> bool:
    """payload `background_tasks` 的一項是不是 keepwarm 背景 shell（冷叫醒閘豁免用）。"""
    cmd = str(task.get("command") or "")
    return task.get("type") == "shell" and roster.KEEPWARM_CMD_RE.search(cmd) is not None


# ───────────────────────────────────────────────────────────── Stop 保溫閘（D6）
def stop_verdict(payload: dict, env=None, now: datetime | None = None) -> str:
    """回 reason；不推回 ⇒ `""`；任何例外 `""`（fail-open）。推回 ⇔ 非 `stop_hook_active`、
    payload 有 `background_tasks` 欄且**沒有任何 running 項**（舊 harness 沒有該欄＝量不到＝
    不判）、非不掛的情形、保溫帳 pings < n*。不寫閂鎖：第二次 Stop 放行。"""
    env = os.environ if env is None else env
    try:
        if not isinstance(payload, dict) or payload.get("stop_hook_active"):
            return ""
        sid, raw = roster._payload_sid(payload), payload.get("transcript_path")
        tasks = roster._tasks(payload)
        if (not sid or not isinstance(raw, str) or not Path(raw).is_file() or tasks is None
                or any(str(t.get("status") or "running") == "running" for t in tasks)):
            return ""
        ctx = roster._scan(Path(raw), False)["ctx_tokens"]
        if skip_reason(sid, env, ctx=ctx, now=now):
            return ""
        star, pings = n_star(ctx), load_ledger(sid, raw)["pings"]
        if pings >= star:
            return ""
        switch.trace(EV_STOP_BLOCK, sid=sid, ctx=ctx, pings=pings, n_star=star)
        return (f"保溫閘（Stop）：本 session 上下文 {ctx:,} token，現在結束回合後沒有任何背景工作"
                "會叫醒它。主控快取壽命 1 小時、閒置約 55 分鐘 harness 還會自動壓縮——下次回來整份"
                "重寫甚至被砍掉。\n"
                f"請現在掛上：{CMD} --sid {sid}（Bash／PowerShell 工具用 run_in_background、"
                f"輸出導檔）。它每 {t_kw_minutes(env):g} 分鐘叫醒一次只讀快取，最多 {star} 次"
                f"（已 {pings} 次）。若同時被要求封存交接包，先封存再掛。"
                "（只推回這一次；第二次 Stop 放行。）")
    except Exception:  # noqa: BLE001 — hook 內任何例外一律放行
        return ""


# ───────────────────────────────────────────────────────────── 指令本體（D7／D8）
def _stamp(epoch: float) -> str:
    return datetime.fromtimestamp(epoch).astimezone().isoformat(timespec="seconds")


def run(sid: str, transcript, *, t_kw_min: float, env=None, now_fn=time.time, sleep_fn=time.sleep,
        poll_sec: float = POLL_SECONDS, out=None) -> int:
    """阻塞到截止才結束：不掛的情形 ⇒ `skip`；到截止 ⇒ `ping` 或 `cap`；一律 rc 0，判決看末行。
    每輪重讀逐字稿尾端的錨點，有新記錄就把截止往後延（人回來工作時不會提早叫醒）。"""
    env, out = os.environ if env is None else env, out or sys.stdout

    def finish(verdict: str, tail: str, detail: str, **fields) -> int:
        print(f"[{_stamp(now_fn())}] {verdict}：{detail}", file=out)
        print(f"處置：{DISPOSAL[verdict]}", file=out)
        switch.trace(EV_VERDICT, sid=sid, verdict=verdict, **fields)
        print(f"KEEPWARM_VERDICT={verdict} {tail}".rstrip(), file=out, flush=True)
        return 0

    ctx = roster._scan(Path(transcript), False)["ctx_tokens"] if transcript is not None else None
    why = "no_transcript" if transcript is None else skip_reason(sid, env, ctx=ctx)
    if why:
        return finish("skip", f"reason={why}", f"不掛保溫（{why}）", reason=why)
    row, star = load_ledger(sid, transcript), n_star(ctx)
    if row["pings"] >= star:
        return finish("cap", f"k={star}", f"保溫帳已達上限 {star} 次", k=star, n_star=star)
    while True:
        due, now = deadline(transcript, t_kw_min), now_fn()
        if due is None:
            return finish("skip", "reason=no_usage", "逐字稿尾端找不到帶 usage 的記錄",
                          reason="no_usage")
        if now >= due:
            break
        sleep_fn(max(min(poll_sec, due - now), 0.0))
    ctx = roster._scan(Path(transcript), False)["ctx_tokens"] or ctx
    star, row = n_star(ctx), load_ledger(sid, transcript)
    k = row["pings"] + 1
    saved = record_ping(sid, k, ctx, star, human_mark(transcript))
    if k >= star or not saved:
        return finish("cap", f"k={star}", f"第 {k} 次、上限 {star}（寫帳成功＝{saved}）",
                      k=k, n_star=star, ctx=ctx)
    return finish("ping", f"k={k} n={star}",
                  f"距主控最後一筆記錄已 ≥ {t_kw_min:g} 分，第 {k}／{star} 次",
                  k=k, n_star=star, ctx=ctx)


def cli(argv: list[str]) -> int:
    import argparse  # noqa: PLC0415

    ap = argparse.ArgumentParser(prog="sessionctl keepwarm")
    ap.add_argument("--sid")
    ap.add_argument("--min", type=float, help="截止分鐘數（1～生效值，只准下修；<15 出聲；E2E 用）")
    ap.add_argument("--poll-sec", type=float, default=POLL_SECONDS)
    ap.add_argument("--projects-dir", help="逐字稿根目錄（預設＝Claude home 的 projects；測試用）")
    args = ap.parse_args(argv)
    sid = args.sid or os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    if not sid or not roster._ID_RE.match(sid):
        print("sessionctl keepwarm：缺 --sid（或形態不合），且環境變數 CLAUDE_CODE_SESSION_ID 未設 "
              "⇒ 無法判定要保溫哪個 session", file=sys.stderr)
        return 2
    t_kw = t_kw_minutes()
    if args.min is not None:
        if not 1 <= args.min <= t_kw:
            _warn(f"--min={args.min:g} 不在 1～{t_kw:g}（只准下修）⇒ 沿用 {t_kw:g}")
        else:
            if args.min < FLOOR_MINUTES:
                _warn(f"--min={args.min:g} 低於建議下限 {FLOOR_MINUTES}（只該用於實測）")
            t_kw = args.min
    return run(sid, find_transcript(sid, args.projects_dir), t_kw_min=t_kw, poll_sec=args.poll_sec)


# ───────────────────────────────────────────────────────────── watch 額度閂鎖（D14）
RESET_JITTER_SECONDS = 300  # 只准下修；同一 reset 窗的觀測值抖動上界


def _same_reset(a: str, b: str) -> bool:
    """同一 reset 窗＝兩個觀測時刻相差 ≤ `RESET_JITTER_SECONDS`。

    WHY（DEF 立案證據，2026-11-19 主控真機）：端點回的 reset 落在 `…:59:59.99Z` 一帶，取到分鐘時
    在 03:59 與 04:00 之間來回跳；字串相等判準把同一窗當成新窗，watch 重掛又立刻 `quota rc=5`
    （痕跡 `watch_quota_latched` reset=04:00:00 → 閂鎖檔 03:59:00，相隔 6 分鐘）。視窗長度以小時計，
    數分鐘的容差不會把真的新窗誤當舊窗。字面相同即同窗；否則解析失敗 ⇒ 回 False
    （照觸發，PRD 原則 5）。"""
    if a == b:
        return True
    try:
        return abs((datetime.fromisoformat(a) - datetime.fromisoformat(b)).total_seconds()) \
            <= RESET_JITTER_SECONDS
    except (TypeError, ValueError):
        return False


def latch_path(sid: str) -> Path:
    return endurance_env.trace_dir() / "watch" / f"{sid}.quota.json"


def quota_latch(sid: str, band: str, reset: str) -> bool:
    """`True`＝該觸發（並記入閂鎖）；`False`＝同 reset 窗、同帶或更低帶已觸發過。帶升級
    （prepare→halt）或 reset 改變（新窗）⇒ 再觸發。閂鎖讀／寫失敗一律照觸發並出聲（寧可再吵一次，也
    不靜默吞掉額度事件；PRD 原則 5）。"""
    path, rank = latch_path(sid), _BANDS.get(band, 1)
    try:
        got = json.loads(path.read_text(encoding="utf-8"))
        if not (isinstance(got, dict) and isinstance(got.get("reset"), str)
                and got.get("band") in _BANDS):
            raise ValueError("結構不符")
        if _same_reset(got["reset"], reset) and _BANDS[got["band"]] >= rank:
            return False
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as exc:
        _warn(f"額度閂鎖 {path} 讀不動（{type(exc).__name__}: {exc}）⇒ 照觸發")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"schema": SCHEMA, "sid": sid, "band": band, "reset": reset}),
                        encoding="utf-8", newline="\n")
    except OSError as exc:
        _warn(f"額度閂鎖寫不進 {path}（{type(exc).__name__}）⇒ 照觸發")
    return True
