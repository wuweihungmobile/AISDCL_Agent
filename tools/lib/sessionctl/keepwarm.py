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

from . import kw_ledger, procstop, roster, seal, switch
from .kw_ledger import SCHEMA

EV_VERDICT = "keepwarm_verdict"
EV_STOP_BLOCK = "keepwarm_stop_block"
EV_QUOTA_LATCHED = "watch_quota_latched"
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
    "ping": "重掛同一指令並結束回合，不做任何判斷（`python tools/sessionctl.py status` 也不必跑；"
            "run_in_background、輸出導檔；本回合輸出 ≤ 50 token）",
    "cap": "已到保溫損益點（再保溫比放冷重寫更貴）：不重掛，直接結束回合讓快取過期",
    "skip": "本情形不需要保溫：什麼都不做、不要重掛",
    "resume": "已到預定時刻：照停工前計畫繼續；交接包已自動記為續跑（DES §8）；park 備援會自行讓路",
    "handed_over": "本視窗已交棒（備援已在別的 session 接手）：不得動工作樹、不得重掛，"
                   "直接結束回合",
}
#: watch 額度閂鎖的帶級（R218 Q2：四級 prepare＜nodispatch＜close＜halt；REQ-QW-17）。
_BANDS = {"prepare": 1, "nodispatch": 2, "close": 3, "halt": 4}


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
# 帳的讀寫與歸零標記住 kw_ledger.py（LOC 分級抽出）；此處重新匯出，呼叫端與測試不變。
ledger_path, human_mark, work_mark = (kw_ledger.ledger_path, kw_ledger.human_mark,
                                      kw_ledger.work_mark)
read_ledger, load_ledger, record_ping = (kw_ledger.read_ledger, kw_ledger.load_ledger,
                                         kw_ledger.record_ping)


# ───────────────────────────────────────────────────────────── 不掛的情形
def skip_reason(sid: str, env, *, ctx, now: datetime | None = None) -> str:
    """§5.1 不掛的情形；回原因代號，需要保溫 ⇒ `""`。次序 `unattended → mode → off → handed_over →
    no_usage → small_ctx`：無人窗口（print 模式背景上限會殺掉它）、模式非 auto、
    `AUTOSDD_KEEPWARM_OFF`、已交棒、量不到上下文、上下文太小。R218 Q2 起**沒有 `park`**：park 只是
    備援，主載具照掛（REQ-QW-20）；有 `wake_target` 時只有前四項會讓指令不掛，`no_usage`／
    `small_ctx` 只讓它不付費 ping、仍單跳到目標（`kw_run`）。`now` 保留供呼叫端相容。"""
    if env.get("AUTOSDD_UNATTENDED"):
        return "unattended"
    if switch.switch_mode(env) != "auto":
        return "mode"
    if env.get(OFF_ENV):
        return "off"
    if seal.handed_over(sid, env) is not None:
        return "handed_over"
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
def run(sid: str, transcript, **kw) -> int:
    """阻塞到叫醒時刻才結束；本體住 `kw_run.py`（LOC 分級抽出）。簽名見 `kw_run.run`：`t_kw_min`／
    `env`／`now_fn`／`sleep_fn`／`poll_sec`／`out`／`pid`／`idle_min`／`heartbeat_min`／
    `read_quota`／`refresh`／`platform_name`。"""
    from . import kw_run  # noqa: PLC0415 — kw_run 反向 import 本檔，頂層會成環

    return kw_run.run(sid, transcript, **kw)


class WakeBudget:
    """叫醒預算（REQ-WP-32）：`watch` 的 keepwarm 事件與 `keepwarm` 指令共用同一本保溫帳 `pings`
    與上限 `n*`。`check` 讀（不寫）、`charge` 才記一次叫醒；兩者各自重讀逐字稿與帳，不快取
    （主控在兩次叫醒之間可能說了話，真人提示會讓帳歸零）。"""

    def __init__(self, sid: str, projects_dir=None, env=None) -> None:
        self.sid, self.projects_dir = sid, projects_dir
        self.env = os.environ if env is None else env

    def check(self) -> tuple[str, int, int, int]:
        """`(不掛原因｜"", pings, n*, ctx)`；找不到逐字稿 ⇒ 原因 `no_transcript`。"""
        transcript = find_transcript(self.sid, self.projects_dir)
        if transcript is None:
            return "no_transcript", 0, 0, 0
        ctx = roster._scan(Path(transcript), False)["ctx_tokens"]
        why = skip_reason(self.sid, self.env, ctx=ctx)
        return why, load_ledger(self.sid, transcript)["pings"], n_star(ctx), int(ctx or 0)

    def charge(self, pings: int, ctx: int, star: int, *, plan=None,
               now: float | None = None) -> bool:
        """記一次叫醒（帳上 pings 設為 `pings+1`）；寫不進去／找不到逐字稿 ⇒ `False`。`plan`／`now`
        （叫醒當下補量後的 `Plan` 與時刻，watch 傳入）供 S-25 記相鄰兩次 ping 的實測 Δ。"""
        from . import (
            kw_wake,  # noqa: PLC0415 — kw_wake 不 import 本檔，但保持與 run 同一種 lazy 形態
        )

        transcript = find_transcript(self.sid, self.projects_dir)
        if transcript is None:
            return False
        row = load_ledger(self.sid, transcript)
        last, costs, last_reset = kw_wake.ping_cost(
            self.sid, row, plan, time.time() if now is None else now)
        return record_ping(self.sid, pings + 1, ctx, star, human_mark(transcript),
                           work=work_mark(transcript), last=last, costs=costs,
                           last_reset=last_reset)


def cli(argv: list[str]) -> int:
    import argparse  # noqa: PLC0415

    ap = argparse.ArgumentParser(prog="sessionctl keepwarm")
    ap.add_argument("--sid")
    ap.add_argument("--min", type=float, help="截止分鐘數（1～生效值，只准下修；<15 出聲；E2E 用）")
    ap.add_argument("--poll-sec", type=float, default=POLL_SECONDS)
    ap.add_argument("--idle-min", type=float,
                    help="最後一段閒置上限分鐘（只准下修，供 E2E 縮時；出廠 IDLE_LIMIT_MIN）")
    ap.add_argument("--heartbeat-min", type=float,
                    help="darwin 心跳間隔分鐘（只准下修，供 E2E 縮時；出廠 MAC_HEARTBEAT_MIN）")
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
    return run(sid, find_transcript(sid, args.projects_dir), t_kw_min=t_kw, poll_sec=args.poll_sec,
               idle_min=args.idle_min, heartbeat_min=args.heartbeat_min)


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
