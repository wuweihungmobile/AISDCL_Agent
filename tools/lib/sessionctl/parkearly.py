"""park 提前到點的 early 入口與觸發本體（Control_Handover DES §8.3；REQ-CTL-31～38；W6，r3）。

哨兵每次巡邏（`session_resume_planner._sentinel_tick`，`tick_gate` 之後、`sentinel_decide` 之前）
呼叫一次 `tick`：前置不成立 ⇒ 靜默回 None；讀額度（`park._pace_state`，TTL 內讀快取）落
`park_early_probe` 痕跡；`parkprobe.evaluate` 判 recovered ⇒ `fire_early`。
`fire_early` 不另開 spawn 路：以**排程同 argv**（`park_cli.job_argv`）起一個 `park --fire` 子行程——
L1 副作用首判、讓路（`live_driver`／`handed_over`／`spawning` 去重）、F4 選路、活窗 fork、失敗鏈、
哨兵接手、出聲全照 Q3；**唯一差別**＝QW §7.3 分支 A（主載具活著且未到 ⇒ 重排）停用
（子行程環境 `EARLY_ENV=1`，`parkprobe.early_view`）。換帳號（`account_changed`）時另帶
`park.FORCE_COLD_ENV=1` 把快取視為已冷（D-CT-8）。

🔴 為什麼是子行程而不是行程內呼叫 `_cmd_fire`（真行程 smoke 才抓得到）：planner 主函式對
`--sentinel-tick` 無條件強制 `AUTOSDD_UNATTENDED=1`（DEF-200-272，排程叫起的 tick 結構上無人看管），
而 `park_fire.run`、`handoff.spawn`、`park_cli.spawn_resume` 全都在該旗標下拒絕開窗。行程內呼叫＝
永遠被自己的守衛擋下；子行程拿掉該旗標，環境與排程器到點跑 job 時一致（排程器環境本來就沒有它）。
同理本檔不以 `AUTOSDD_UNATTENDED` 當前置：在哨兵 tick 裡它恆為真，沒有鑑別力；真正的無人窗口
（`claude -p`）不會有 park 標記（`park` 拒絕無人窗口）。
import 方向：本檔 → {parkprobe, park_cli（惰性，它反向呼叫本套件）}；`parkprobe` 不 import 本檔。
任何例外一律吞掉並留痕跡——探針分支不得讓哨兵巡邏自己死掉。
"""
from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path

from . import handoff, holder, park, parkprobe, qw_schema, seal, switch

EV_ERROR = "park_early_error"
CHILD_TIMEOUT_SECONDS = 600  # 讓路觀察 180 s ＋兩條路的 spawn 等待；短於哨兵 15 分鐘巡邏


def _sid(args) -> str:
    """哨兵任務書檔名是 `<PLAN_PREFIX><sid>.md`（`session_resume_planner` 的武裝路徑）；park 標記以
    裸 sid 為鍵，所以先去前綴（不去就永遠讀不到標記——真行程 smoke 才抓得到的接線錯誤）。"""
    import quota_escalation  # noqa: PLC0415

    plan = getattr(args, "plan", None)
    stem = Path(str(plan)).stem.removeprefix(quota_escalation.guard.PLAN_PREFIX) if plan else ""
    return stem if park._SID_RE.match(stem) else ""  # noqa: SLF001


def _precheck(marker: dict, env, now: datetime, S: dict) -> str:
    """前置（REQ-CTL-31）：回不成立的原因，空字串＝成立。不碰額度、不寫任何東西。"""
    if switch.switch_mode(env) != "auto":  # 不查 AUTOSDD_UNATTENDED：見檔頭，哨兵 tick 裡它恆為真
        return "mode"
    if not park.yields(marker, now):  # armed ∧ route H ∧ 在 valid_until 內
        return "not_armed"
    fire = qw_schema.parse_epoch(marker.get("fire_at"))
    if fire is None or fire - now.timestamp() < parkprobe.EARLY_MIN_WAIT_MIN * 60:
        return "wait_short"
    if not marker.get("pkg"):
        return "no_pkg"
    pkg = Path(marker["pkg"])
    if pkg.with_suffix(".ack").exists():
        return "acked"
    row = next((r for r in handoff.list_handoffs(env=env) if r["path"] == pkg), None)
    if row is None or row["state"] != "live":
        return "pkg_not_live"
    if (handoff._duplicate_refusals(pkg, now, S.get("alive") or handoff._alive)  # noqa: SLF001
            or seal._spawned(pkg, now)):  # noqa: SLF001
        return "spawned"  # 已 handed_over、剛 spawn 過，或 spawning 意圖仍有效
    return ""


def _primary_handles(marker: dict, sid: str) -> bool:
    """QW S-19 的 `early_reset` 管「短窗 reset 型」主載具：標記 `primary_source=reset` 且主載具
    （keepwarm 持有者）還活著 ⇒ 由它處理，本分支不對同一事件再答一次（DES §8.3 步驟 4）。"""
    if qw_schema.marker_primary(marker).source != "reset":
        return False
    row = holder.read(sid)
    return row is not None and holder.is_live(row)


def _live_driver(sid: str, env, now: datetime, S: dict) -> bool:
    """有人在動這個 session（使用者回來了）⇒ 不提前接手；讀不到逐字稿當作沒人在動，交給
    `_cmd_fire` 的同一道判準再擋一次。"""
    import transcript_activity  # noqa: PLC0415

    from . import park_cli  # noqa: PLC0415 — 惰性：park_cli 反向呼叫本套件

    try:
        find = S.get("transcript") or (lambda s: park_cli._find_transcript(s, env))  # noqa: SLF001
        return transcript_activity.live_driver(find(sid), now) is not None
    except Exception:  # noqa: BLE001
        return False


def tick(args, now: datetime | None = None, S: dict | None = None, env=None) -> dict | None:
    """哨兵每次巡邏呼叫一次；回判決字典（供稽核）或 None（前置不成立／例外）。"""
    env, S = os.environ if env is None else env, dict(S or {})
    sid = _sid(args)
    try:
        now = now or datetime.now().astimezone()
        marker = park.read_marker(sid) if sid else None
        if marker is None or _precheck(marker, env, now, S):
            return None
        if _primary_handles(marker, sid) or _live_driver(sid, env, now, S):
            return None
        if not parkprobe.has_baseline(marker):
            verdict = parkprobe.evaluate(marker, None, None, now)  # state 不會被讀（無基準先返回）
        else:
            from . import park_reset  # noqa: PLC0415 — QVD C21：同 park 前置的當下判決

            snap = park_reset.ruling_for(sid, S, now, env, default_est=False)
            state = snap.state
            verdict = parkprobe.evaluate(marker, state, snap.ruling, now)
        extra = {} if not parkprobe.has_baseline(marker) else {"stale": not state.axes}
        switch.trace(parkprobe.EV_PROBE, sid=sid, reason=verdict["reason"], reading=verdict["cur"],
                     parked_pct=verdict["baseline"], recovered=verdict["recovered"],
                     account_changed=verdict["account_changed"], action=verdict["action"],
                     vid=verdict["vid"], **extra)
        if verdict["recovered"]:
            verdict["fired"] = fire_early(sid, marker, verdict, env, now, S)
        return verdict
    except Exception as exc:  # noqa: BLE001 — 探針不得讓哨兵巡邏死掉
        switch.trace(EV_ERROR, sid=sid, error=type(exc).__name__)
        return None


def _run_job(argv: list[str], env: dict) -> int:
    """真子行程（無視窗、有逾時）；起不來或逾時 ⇒ 127（呼叫端落 `park_early_error`）。"""
    import win_spawn  # noqa: PLC0415 — lazy

    try:
        return subprocess.run(argv, env=env, capture_output=True, timeout=CHILD_TIMEOUT_SECONDS,
                              check=False, stdin=subprocess.DEVNULL,
                              creationflags=win_spawn.NO_WINDOW).returncode
    except (OSError, subprocess.SubprocessError):
        return 127


def fire_early(sid: str, marker: dict, verdict: dict, env, now: datetime, S: dict) -> str:
    """以排程同 argv 起 `park --fire` 子行程（環境：拿掉 `AUTOSDD_UNATTENDED`、加 `EARLY_ENV`，
    換帳號再加 `FORCE_COLD_ENV`）；回標記的結局（fired／skipped／failed／refused；armed＝子行程
    沒動標記）。成功（fired）才落 `park_early_recovered`（`saved_min`＝距原 `fire_at` 的分鐘數）。
    事後把磁碟上標記的重排次數欄還原成呼叫前的值（early 借用該欄停用分支 A，不留痕在終態標記）。
    縫：`S["run_job"](argv, env) -> rc`（測試以行程內 `park_cli.run` 代替真子行程）。"""
    from . import park_cli, park_yield  # noqa: PLC0415

    job = next(j for j in marker["jobs"] if j.get("role") == "primary")
    claude = marker.get("claude")
    argv = park_cli.job_argv(job["label"], sid, marker["pkg"],
                             datetime.fromisoformat(marker["fire_at"]),
                             ["--claude", claude] if claude else [])
    child = {k: v for k, v in env.items() if k != park.UNATTENDED_ENV}
    child[parkprobe.EARLY_ENV] = "1"
    if verdict["account_changed"]:
        child[park.FORCE_COLD_ENV] = "1"
    key = park_yield.RESCHEDULES_KEY
    before = marker.get(key)
    try:
        rc = (S.get("run_job") or _run_job)(argv, child)
        if rc != 0:
            switch.trace(EV_ERROR, sid=sid, error="child_rc", rc=rc)
    finally:
        final = park.read_marker(sid)
        if final is not None:
            restored = {k: v for k, v in final.items() if k != key}
            park.write_marker(restored if before is None else dict(restored, **{key: before}))
    status = (park.read_marker(sid) or marker)["status"]
    if status == "fired":
        saved = (qw_schema.parse_epoch(marker["fire_at"]) - now.timestamp()) / 60
        switch.trace(parkprobe.EV_RECOVERED, sid=sid, saved_min=round(saved, 1),
                     account_changed=verdict["account_changed"], reading=verdict["cur"],
                     parked_pct=verdict["baseline"])
    return status
