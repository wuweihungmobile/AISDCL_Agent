"""額度自願停工的續航判準：選路、原始讀數、標記讀寫、哨兵讓路、Stop 推回（ADR-XPLAT-004 §2.17）。

WHY：2026-11-15 事故——短窗額度 98%、43 分鐘後 reset，主控把「請回來說繼續」當成交棒結束回合，
舊視窗上下文已冷，一開口整份重寫（21.9 萬 token）。`park` 在停工前掛好
「到點由新 session 帶交接包接手」的排程憑證；本檔是它的純判準層。
Stop 路徑只讀檔、不 spawn、不打排程器。
🔴 fail-open／fail-closed 分界：任何例外 ⇒ Stop 放行（P0）；標記壞掉 ⇒ 無憑證（推回至多一次）。
🔴 (g) 的唯一入口是 `prepare_hits`：只讀 `Axis.pct`（伺服器原值），不碰 `quota_policy.decide` 的
band（攤提與配速床會把 23% 墊成 prepare，那不是「真的快撞線」）。
本輪只有 H 路（到點換手）；同 session 背景等待者（W 路）無暴露證據，不做（AMEND_MASTER M1）。
"""
from __future__ import annotations

import contextlib
import contextvars
import json
import math
import re
import time
from datetime import datetime
from pathlib import Path

import endurance_env

from . import costmodel, roster, switch

SCHEMA = "autosdd.park/1"
UNATTENDED_ENV = "AUTOSDD_UNATTENDED"
GUARD_OFF_ENV = "AUTOSDD_PARK_GUARD_OFF"  # 只關 Stop 推回；讀自 hook 行程環境
PARK_CMD = "python tools/sessionctl.py park"
ROUTE_H, ROUTE_DONE, ROUTE_REFUSE = "H", "DONE", "REFUSE"
FIRE_RESUME, FIRE_FRESH = "RESUME", "FRESH"  # 到點換手的兩種開法（設計 §4.6）
# `refused`＝到點被產品面（L1 副作用隔離）拒絕：終局、非失敗、非 armed（SE DES D-21）
STATUSES = ("armed", "fired", "skipped", "cancelled", "failed", "refused")
# parity：quota_gate._FIVE_HOUR_KINDS／_FIVE_HOUR_MINUTES
SHORT_WINDOW_KINDS = frozenset({"session", "five_hour", "5h"})
SHORT_WINDOW_MINUTES = 300.0
# 哨兵讓路與 H 憑證的尾端寬限；parity：quota_messages.HALT_QUIESCE_SECONDS
YIELD_GRACE_SECONDS = 900
MIN_WHY_CHARS = 8
DONE_MAX_SECONDS = 18000  # `--done` 戳記上限 5 小時
AT_MAX_SECONDS = 8 * 86400  # `--at` 上限 8 天
PARK_DIR = "park"
YIELD_REASON = "park 排程待命（標記 armed 且在窗內）⇒ 哨兵讓路，不搶駕駛；窗過後恢復原判準"
_SID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")  # 與 handoff._SID_RE 同；自帶以免 import 重量
_SPAWNED_LOG = "autosdd_session_switch.jsonl"


# ───────────────────────────────────────────────────────────────────────── 選路
def park_route(wait_s: float | None, *, unattended: bool, mode: str,
               carrier_ok: bool) -> tuple[str, str]:
    """回 `(route, reason)`；route ∈ {"H","REFUSE"}。REFUSE：無人窗口｜模式非 auto｜無載具｜
    reset 不明（wait_s 為 None；reason 含「reset」與「不假設」）。其餘一律 H（到點換手）。"""
    if unattended:
        return ROUTE_REFUSE, "無人窗口（AUTOSDD_UNATTENDED 有設）"
    if mode != "auto":
        return ROUTE_REFUSE, f"AUTOSDD_SESSION_SWITCH_MODE={mode}（H 路需要 auto）"
    if not carrier_ok:
        return ROUTE_REFUSE, "本平台沒有已實作的排程載具"
    if wait_s is None:
        return ROUTE_REFUSE, "量不到 reset 時刻：reset 是滾動視窗、只能觀測不能算，不假設 5 小時"
    return ROUTE_H, f"到點（約 {max(0.0, float(wait_s)) / 60:.0f} 分鐘後）由新 session 帶交接包接手"


_FORCE_COLD: contextvars.ContextVar[bool] = contextvars.ContextVar("park_force_cold", default=False)


@contextlib.contextmanager
def force_cold():
    """換帳號的提前到點（Control DES D-CT-8）：區塊內 `fire_route` 一律把快取視為已冷。用
    ContextVar 而不用環境變數／猴子補丁——不會漏進 spawn 出去的子行程環境、執行緒各自獨立。"""
    token = _FORCE_COLD.set(True)
    try:
        yield
    finally:
        _FORCE_COLD.reset(token)


def fire_route(held: int | float | None, cold: bool, env=None) -> tuple[str, str]:
    """到點（reset 後）怎麼接手：回 `(FIRE_RESUME | FIRE_FRESH, 理由)`（R216 設計 §4.6、F4）。
    `force_cold()` 區塊內 `cold` 一律為真，理由前綴 `account_changed`（REQ-CTL-34）。"""
    route, why = _fire_route(held, cold or _FORCE_COLD.get(), env)
    return route, (f"account_changed：{why}" if _FORCE_COLD.get() else why)


def _fire_route(held: int | float | None, cold: bool, env=None) -> tuple[str, str]:
    """· 上下文量不到 ⇒ FRESH：`claude -r` 需要讀得到逐字稿，量不到就不冒險，走已封存交接包這條
      既有的路（也保住 AT-PK-57～64 的既有契約）；
    · 快取仍熱 ⇒ RESUME（讀價必小於接手成本 F）；
    · 快取已冷 ⇒ `costmodel.fresh_is_cheaper`（`W_CC1·c > F(1+q)`，與喚醒選路、轉送同一條判準）：
      命中 ⇒ FRESH，否則 RESUME（小上下文續跑重寫比接手便宜，且不丟上下文）。"""
    if held is None or held <= 0:
        return FIRE_FRESH, "上下文量不到（-r 需要讀得到逐字稿）⇒ 沿用交接包換手"
    if costmodel.fresh_is_cheaper(held, cold=cold, env=env):
        return FIRE_FRESH, costmodel.f4_reason(held, env)
    if not cold:
        return FIRE_RESUME, f"快取仍熱（上下文 {held:,} tokens），續跑只付讀價，保留上下文"
    rewrite = costmodel.W_CC1 * held
    return FIRE_RESUME, (f"快取已冷但上下文 {held:,} tokens 續跑重寫 {rewrite:,.0f} 單位"
                         f" ≤ 換新 {costmodel.fresh_total(env):,.0f} 單位，保留上下文")


# ───────────────────────────────────────────────────────────────────── 原始讀數
def _aware_future(text, now: datetime) -> datetime | None:
    """ISO 字串 → aware 且在 `now` 之後的時刻；naive／壞值／已過 ⇒ None。"""
    try:
        when = datetime.fromisoformat(str(text).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return when if when.tzinfo is not None and when > now else None


def short_axes(axes: tuple) -> list:
    """kind ∈ `SHORT_WINDOW_KINDS`，或窗長由 `quota_pace.windows` 導出為 300 分；
    FALLBACK／模型分軌／週軸一律不是。"""
    import quota_pace  # noqa: PLC0415 — lazy
    import quota_policy  # noqa: PLC0415

    axes = tuple(axes)
    wins = quota_pace.windows(tuple((a.kind, a.resets_at) for a in axes))
    banned = quota_policy.FALLBACK_KINDS | quota_policy.MODEL_SCOPED_KINDS
    return [a for a, win in zip(axes, wins)
            if a.kind not in banned
            and (a.kind in SHORT_WINDOW_KINDS or win == SHORT_WINDOW_MINUTES)]


def _real_pct(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def prepare_hits(state, policy, now: datetime) -> list | None:
    """🔴 (g) 的唯一入口。`None`＝量不到（`state.axes == ()`）；`[]`＝量到了但沒有短窗軸達標。
    命中＝短窗軸 ∧ 有限 int／float（排除 bool）∧ `axis.pct >= policy.prepare_pct` ∧ reset 在未來。
    只讀 `Axis.pct`；**嚴禁**呼叫 `decide`／`axes_of` 或讀 band（吃攤提與配速床墊高後的水位）。"""
    if not state.axes:
        return None
    return [a for a in measured_short(state, now) if a.pct >= policy.prepare_pct]


def measured_short(state, now: datetime) -> list:
    """短窗軸 ∧ 有限讀數 ∧ reset 在未來（不看門檻）。`park --why` 未達門檻時的 reset 來源：
    「下一棒放不下」是相對下一棒大小的判斷，不是固定門檻；Stop 推回仍只走 `prepare_hits`。"""
    return [a for a in short_axes(state.axes)
            if _real_pct(a.pct) and _aware_future(a.resets_at, now) is not None]


def recovered(marker: dict, state, policy, now: datetime) -> bool:
    """提前恢復（Control DES §8.2）：`parked_pct` 存在 ∧ 讀數 ≤ 它 − 5pp ∧ 讀數 < 準備門檻。
    判準與基準欄常數住葉模組 `parkprobe`（惰性匯入：它反向 import 本檔取讀數輔助）。"""
    from . import parkprobe  # noqa: PLC0415

    return parkprobe.evaluate(marker, state, policy, now)["recovered"]


def reset_of(hits: list) -> datetime | None:
    """命中軸 `resets_at` 的**最大值**（所有達標軸都翻頁才醒）；解不出的軸不參與；全無 ⇒ None。"""
    stamps = []
    for axis in hits:
        try:
            when = datetime.fromisoformat(str(axis.resets_at).strip().replace("Z", "+00:00"))
        except ValueError:
            continue
        if when.tzinfo is not None:
            stamps.append(when)
    return max(stamps) if stamps else None


# ───────────────────────────────────────────────────────────────────────── 標記
def _aware_text(text) -> bool:
    try:
        return datetime.fromisoformat(str(text).strip().replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def _job_ok(job) -> bool:
    return (isinstance(job, dict) and isinstance(job.get("label"), str) and job["label"]
            and job.get("role") == "primary" and _aware_text(job.get("fire_at"))
            and isinstance(job.get("credential"), str))


def marker_problem(marker, sid: str | None = None) -> str:
    """標記結構驗證（讀寫兩端同一份）：空字串＝合格，否則回第一個問題。"""
    if not isinstance(marker, dict) or marker.get("schema") != SCHEMA:
        return "schema 不符"
    msid = marker.get("sid")
    if not isinstance(msid, str) or not _SID_RE.match(msid) or (sid is not None and msid != sid):
        return "sid 不合"
    if marker.get("route") not in (ROUTE_H, ROUTE_DONE) or marker.get("status") not in STATUSES:
        return "route／status 不在表內"
    if not (_aware_text(marker.get("parked_at")) and _aware_text(marker.get("valid_until"))):
        return "parked_at／valid_until 缺或 naive"
    if any(marker.get(k) is not None and not _aware_text(marker[k])
           for k in ("reset_at", "fire_at")):
        return "reset_at／fire_at 為 naive"
    if marker["route"] == ROUTE_DONE and (
            not isinstance(marker.get("why"), str) or len(marker["why"].strip()) < MIN_WHY_CHARS):
        return f"DONE 的 why 須至少 {MIN_WHY_CHARS} 字"
    jobs = marker.get("jobs")
    if not isinstance(jobs, list) or not all(_job_ok(j) for j in jobs):
        return "jobs 結構不合"
    return ""


def marker_path(sid: str, *, write: bool = False, base: Path | None = None) -> Path | None:
    """`<trace>/park/<sid>.json`；sid 形態不合 ⇒ None。`write=True` 才用 `trace_dir()` 並 mkdir。"""
    if not isinstance(sid, str) or not _SID_RE.match(sid):
        return None
    root = Path(base) if base is not None else (
        endurance_env.trace_dir() if write else endurance_env.trace_dir_peek()[0])
    folder = root / PARK_DIR
    if write:
        folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{sid}.json"


def read_marker(sid: str, *, base: Path | None = None) -> dict | None:
    """讀＋驗證；任何異常一律 None（fail-closed＝無憑證）。壞 JSON 重試一次以吃掉半寫。"""
    path = marker_path(sid, base=base)
    if path is None:
        return None
    for attempt in (0, 1):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, ValueError):
            if attempt == 0:
                time.sleep(0.05)
            continue
        return data if not marker_problem(data, sid) else None
    return None


def write_marker(marker: dict, *, base: Path | None = None) -> tuple[bool, str]:
    """同一組驗證先過才寫（拒寫勝過寫讀不回來的標記）；不用 os.replace（非原子，同 quota_rush）。"""
    problem = marker_problem(marker)
    if problem:
        return False, f"標記不合格：{problem}"
    try:
        path = marker_path(marker["sid"], write=True, base=base)
        path.write_text(json.dumps(marker, ensure_ascii=False), encoding="utf-8", newline="\n")
    except OSError as exc:
        return False, str(exc)
    return True, str(path)


def credential_ok(marker: dict | None, now: datetime) -> tuple[bool, str]:
    """D4：標記是不是有效的續航憑證。順序：armed → 未過 valid_until → DONE 即有效；
    H 須有 primary job 且憑證非空。"""
    if not isinstance(marker, dict):
        return False, "無標記"
    if marker.get("status") != "armed":
        return False, f"標記狀態={marker.get('status')}"
    try:
        valid = datetime.fromisoformat(str(marker["valid_until"]).replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return False, "valid_until 解不出"
    if now > valid:
        return False, "標記已過 valid_until"
    if marker.get("route") == ROUTE_DONE:
        return True, "DONE 標記有效"
    if marker.get("pkg"):  # QW REQ-QW-31：交接包已被接手／自續跑／過期 ⇒ 到點不會有動作，不是憑證
        import os  # noqa: PLC0415

        from . import handoff  # noqa: PLC0415 — lazy：handoff 重，且反向依賴本檔

        state = handoff._state(Path(marker["pkg"]), now, os.environ)  # noqa: SLF001
        if state != "live":
            return False, f"交接包已不是 live（{state}）"
    jobs =[j for j in marker.get("jobs") or [] if j.get("role") == "primary"]
    if jobs and str(jobs[0].get("credential") or "").strip():
        return True, "H 排程憑證有效"
    return False, "H 標記沒有排程憑證"


def yields(marker: dict | None, now: datetime) -> bool:
    """哨兵讓路：標記非 None ∧ armed ∧ route == H ∧ now <= valid_until。"""
    try:
        valid = datetime.fromisoformat(str(marker["valid_until"]).replace("Z", "+00:00"))
        return (marker.get("status") == "armed" and marker.get("route") == ROUTE_H
                and now <= valid)
    except (KeyError, TypeError, ValueError):
        return False


# ─────────────────────────────────────────────────────────────────────── Stop 判準
def handed_off(sid: str, env=None) -> bool:
    """本 session 的交接包已 `--spawn`：痕跡有 `session_switch_spawned ∧ sid ∧ ok` 且在 TTL 內。"""
    try:
        ttl = switch.threshold(switch.HANDOFF_TTL_KEY, env)[0] * 3600
        lines = (endurance_env.trace_dir_peek()[0] / _SPAWNED_LOG).read_text(
            encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False
    now = datetime.now().astimezone().timestamp()
    for line in lines:
        try:
            rec = json.loads(line)
            age = now - datetime.fromisoformat(rec["at"]).timestamp()
        except (ValueError, KeyError, TypeError):
            continue
        if (isinstance(rec, dict) and rec.get("event") == "session_switch_spawned"
                and rec.get("sid") == sid and rec.get("ok") is True and age <= ttl):
            return True
    return False


def _block_text(hits: list, now: datetime, reset: datetime, why: str, policy) -> str:
    top = max(hits, key=lambda a: a.pct)
    mins = max(0, int((reset - now).total_seconds() // 60))
    return (f"額度停工守衛（Stop）：短窗額度 {top.kind} 已 {top.pct:.0f}pp"
            f"（≥ 準備門檻 {policy.prepare_pct:.0f}pp），{mins} 分鐘後"
            f"（{reset.isoformat()}）reset，"
            f"但本 session 沒有任何續航憑證（{why}）。現在結束回合，reset 後沒有東西叫醒工作，"
            "只剩人回來說「繼續」——而那個舊視窗上下文已冷，一開口整份重寫。請現在執行：\n"
            f"  {PARK_CMD}\n"
            "它會掛好「到點由新 session 帶交接包接手」的排程並印出排程憑證"
            "（交接包須先 handoff --finalize）。\n"
            f"若真的沒有剩餘工作：{PARK_CMD} --done --why \"<至少 8 字的原因>\"\n"
            "回覆裡不要叫掌舵者回這個視窗說繼續。（只推回這一次；第二次 Stop 放行。）")


def stop_verdict(payload: dict, env=None, *, now: datetime | None = None, read_quota=None,
                 policy_fn=None, carrier_fn=None, spawned_fn=None) -> str:
    """回要放進 `decision:block` 的 reason；不推回 ⇒ `""`。任何例外 `""`（fail-open，P0）。
    縫：read_quota(now)->QuotaState、policy_fn()->Policy、carrier_fn()->bool、
    spawned_fn(sid, env)->bool。
    前一步不成立即回 `""`，且不做後面的 I/O。"""
    try:
        import os  # noqa: PLC0415

        env = os.environ if env is None else env
        if not isinstance(payload, dict) or payload.get("stop_hook_active"):
            return ""
        if env.get(UNATTENDED_ENV) or env.get(GUARD_OFF_ENV) or switch.switch_mode(env) != "auto":
            return ""
        if not (carrier_fn or _has_carrier)():
            return ""
        sid = roster._payload_sid(payload)
        if not _SID_RE.match(sid):
            return ""
        now = now or datetime.now().astimezone()
        state = (read_quota or _pace_state)(now)
        policy = (policy_fn or _policy)()
        hits = prepare_hits(state, policy, now)
        if hits is None:
            switch.trace("park_verdict_unmeasured", sid=sid, source=state.source,
                         reason=state.reason)
            return ""
        reset = reset_of(hits) if hits else None
        if reset is None or (spawned_fn or handed_off)(sid, env):
            return ""
        marker = read_marker(sid)
        ok, why = credential_ok(marker, now)
        if ok:
            return ""
        top = max(hits, key=lambda a: a.pct)
        switch.trace("park_stop_block", sid=sid, kind=top.kind, pct=top.pct,
                     reset_at=reset.isoformat(),
                     marker=None if marker is None else
                     {"route": marker["route"], "status": marker["status"]}, why=why)
        return _block_text(hits, now, reset, why, policy)
    except Exception:  # noqa: BLE001 — fail-open（P0）
        return ""


def _has_carrier() -> bool:
    import schedule_backend  # noqa: PLC0415 — lazy

    return schedule_backend.has_carrier()


def _pace_state(now: datetime):
    import quota_gate  # noqa: PLC0415

    return quota_gate.pace_state(now)


def _policy():
    import quota_gate  # noqa: PLC0415
    import quota_policy  # noqa: PLC0415

    return quota_policy.load_policy(quota_gate.policy_env())[0]
