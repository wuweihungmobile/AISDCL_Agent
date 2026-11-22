"""`run-driver <id>`：排程觸發後的一次執行（DES §5.1 第 0～7 步；
REQ-WP-08／11／12／13／19／27／28／102）。

判決一律寫進 OIR 事件、末行 `OPENITEMS_DRIVER=<result> id=<id> n=<n> [extra…]`、**rc 0**
（harness 把背景
指令任何非 0 結束顯示成「failed」，判決只看末行；非 0 只留給真錯誤＝例外）。所有外部效應（排程器、
`--pace`、讓路、行程身分、子行程、時鐘）都從 `Deps` 注入，單元測試走假縫、E2E 走預設真值。
"""
from __future__ import annotations

import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from . import drive, evidence, schedcache, throttle
from . import ledger as oi_ledger
from . import params as oi_params
from .fold import fold

_TOOLS = Path(__file__).resolve().parents[2]
COVERAGE_TIMEOUT_SECONDS = 60


@dataclass
class Deps:
    backend: object | None = None
    now: Callable[[], datetime] = lambda: datetime.now().astimezone()  # noqa: E731
    pace: Callable[[datetime], throttle.Pace] = throttle.read_pace
    interactive: Callable[[Path, datetime], bool] = throttle.interactive_active
    identity: Callable = throttle.proc_identity
    run: Callable = drive.console_run
    case_info: Callable = drive.case_info
    stale: Callable | None = None  # (root, params, now) -> list[id]；None＝不跑 stale-pass
    coverage: Callable[[Path], str] | None = None  # 預設：呼叫 `realverify coverage --write`
    pid: int = field(default_factory=os.getpid)


def log(item_id: str, message: str, now: datetime | None = None) -> None:
    path = throttle.oi_dir() / f"driver_{item_id}.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.now().astimezone()).isoformat(timespec="seconds")
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"{stamp} {message}\n")


def _coverage(root: Path, deps: Deps) -> str:
    argv = ["python", str(_TOOLS / "realverify.py"), "coverage", "--write"]
    rc, _out = deps.run(argv, COVERAGE_TIMEOUT_SECONDS, dict(os.environ), root)
    return "ok" if rc == 0 else "failed"


def _tail(text: str, limit: int = 200) -> str:
    lines = [ln for ln in (text or "").strip().splitlines() if ln.strip()]
    return (lines[-1] if lines else "")[:limit]


def _rule_ok(check: dict, rc: int, out: str) -> bool:
    rule = check["pass"]
    return rc == 0 if rule == "rc0" else bool(re.search(rule[6:], out))


def _judge(item: dict, root: Path, rc: int, out: str, now: datetime) -> tuple[bool, str]:
    """執行結果→`(通過, 證據或失敗理由)`。realverify 案例：子行程 rc 0 且帳本有晚於 open 的
    pass 列；
    帳本在別的根（沙盒）時退認 `REALVERIFY_VERDICT=pass` 末行（誠實標出證據不是帳列）。"""
    check = item["check"]
    if "realverify" not in check:
        return _rule_ok(check, rc, out), f"argv rc={rc} pass={check['pass']} {_tail(out)}".strip()
    ok_run = rc == 0 and "REALVERIFY_VERDICT=pass" in out
    ok_row, proof = evidence.run_check(item, root, now)
    if ok_run and ok_row:
        return True, proof
    if ok_run and Path(root).resolve() != _TOOLS.parent.resolve():
        return True, f"{check['realverify']} stdout REALVERIFY_VERDICT=pass rc=0（本根帳本未更新）"
    return False, f"rc={rc} {_tail(out) or proof}"


def _redrive(root, params, item_id, deps, now, at) -> bool:
    try:
        drive.drive_item(root, params, item_id, backend=deps.backend, now=now,
                         by=f"driver:{item_id}", at=at)
        return True
    except (drive.DriveFailed, oi_ledger.Reject) as exc:
        log(item_id, f"redrive failed: {exc}", now)
        return False


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def _delay(now: datetime, minutes: int) -> datetime:
    return now + timedelta(minutes=minutes)


def _after_reset(now: datetime, pace: throttle.Pace | None, fallback_minutes: int) -> datetime:
    """量到短窗 reset ⇒ reset＋1 分；量不到 ⇒ 退避分鐘（不假設 5 小時）。"""
    if pace is not None and pace.ok and pace.short_reset_min is not None:
        return now + timedelta(minutes=pace.short_reset_min + 1)
    return _delay(now, fallback_minutes)


def run_driver(root: Path, params: dict, item_id: str, task: str | None, deps: Deps) -> str:
    """跑一次驅動器；回末行字串。例外代表真錯誤（呼叫端 rc 1），判決一律在末行。

    `start` 之後不論怎麼結束（任何例外、`KeyboardInterrupt`、`SystemExit`）帳本都補一筆 `attempt`
    再重拋——否則帳本停在「有 start 無 attempt」，要靠讀端對帳才發現（W5-FIX1）。被外力硬殺（關機、
    `taskkill /F`）行內補不到，那一面由 `fold.driven_verdict` 的 `run_died` 判準負責。"""
    guard: dict = {}
    try:
        return _run(root, params, item_id, task, deps, guard)
    except BaseException as exc:
        _seal_attempt(root, params, item_id, deps, guard, exc)
        raise


def _seal_attempt(root: Path, params: dict, item_id: str, deps: Deps, guard: dict,
                  exc: BaseException) -> None:
    """例外離開時，若本次的 `start` 還沒有任何 `attempt` ⇒ 補寫（中斷＝deferred，不耗重試預算；
    其他例外＝fail，計入 attempts、達上限即升級）。補寫自己失敗只落 driver log，不遮蔽原例外。"""
    if not guard:
        return
    try:
        now = deps.now()
        item = fold(oi_ledger.read_events(oi_params.ledger_path(root))[0], params, now
                    ).items.get(item_id)
        start = item["start"] if item else None
        if (not item or item["state"] != "driven" or item["attempt"] is not None or not start
                or start.get("pid") != deps.pid or item["drive"]["seq"] != guard["seq"]):
            return
        interrupted = not isinstance(exc, Exception)
        base = {"ev": "attempt", "id": item_id, "by": guard["who"], "ts": _iso(now),
                "n": guard["n"], "drive_seq": guard["seq"]}
        if interrupted:
            batch = [{**base, "result": "deferred", "reason": "interrupted"}]
        else:
            batch = [{**base, "result": "fail", "reason": f"error:{type(exc).__name__}",
                      "evidence": f"driver exception {type(exc).__name__}: {str(exc)[:160]}"}]
            if guard["n"] >= params["max_attempts"]:
                batch.append({"ev": "escalate", "id": item_id, "by": guard["who"],
                              "ts": _iso(now), "reason": "attempts_exhausted"})
        oi_ledger.append(root, lambda _e: batch)
        log(item_id, f"sealed attempt after {type(exc).__name__}", now)
        if interrupted:
            _redrive(root, params, item_id, deps, now, _delay(now, params["retry_backoff_minutes"]))
    except Exception as inner:  # noqa: BLE001 — 補寫失敗不得遮蔽原例外
        log(item_id, f"seal attempt failed: {inner!r}", None)


def _run(root: Path, params: dict, item_id: str, task: str | None, deps: Deps,
         guard: dict) -> str:
    root = Path(root)
    now = deps.now()
    events, _bad = oi_ledger.read_events(oi_params.ledger_path(root))
    item = fold(events, params, now).items.get(item_id)
    extra_tags: list[str] = []

    def finish(result: str, n: int, *extra: str) -> str:
        end = deps.now()
        schedcache.refresh(params, deps.backend, end)
        if task and deps.backend is not None:
            deps.backend.unregister(task)  # 一次性排程：自己這一次的工作用完即刪
        line = f"OPENITEMS_DRIVER={result} id={item_id} n={n}" + "".join(
            f" {e}" for e in (*extra, *extra_tags))
        log(item_id, line, end)
        return line

    d = item["drive"] if item else None
    if item is None or item["state"] != "driven" or d is None or (task and d.get("task") != task):
        why = "missing" if item is None else f"state={item['state']}"
        log(item_id, f"noop: {why}", now)
        return finish("noop", item["attempts"] if item else 0)

    n = item["attempts"] + 1
    info = deps.case_info(drive.case_of(item))
    budget = drive.budget_minutes(item, info, params)
    who = f"driver:{task or 'manual'}"

    def event(name: str, **fields) -> dict:
        """帶注入時鐘時間戳的事件（測試撥得動時鐘；生產即真時鐘）。"""
        stamp = _iso(deps.now())
        return {"ev": name, "id": item_id, "by": who, "ts": stamp, **fields}

    guard.update(seq=d["seq"], n=n, who=who)  # 從這裡起，任何例外都由 run_driver 補 attempt
    oi_ledger.append(root, lambda _e: [event(
        "start", drive_seq=d["seq"], pid=deps.pid, proc_start=deps.identity(deps.pid) or "",
        budget_minutes=budget)])
    schedcache.refresh(params, deps.backend, now)
    if deps.stale is not None:
        try:
            log(item_id, f"stale-pass opened {deps.stale(root, params, now)}", now)
        except Exception as exc:  # noqa: BLE001 — 附帶掃描失敗不得吃掉本次驅動
            log(item_id, f"stale-pass failed: {exc!r}", now)

    def attempt(result: str, evidence_text: str = "", reason: str = "") -> dict:
        extra = {k: v for k, v in (("reason", reason), ("evidence", evidence_text)) if v}
        return event("attempt", n=n, result=result, drive_seq=d["seq"], **extra)

    def defer(reason: str, at: datetime) -> str:
        spent = item["deferrals"] + 1 >= params["max_deferrals"] and reason == "interactive"
        batch = [attempt("deferred", reason=reason)]
        if spent:
            batch.append(event("escalate", reason="deferrals_exhausted"))
        oi_ledger.append(root, lambda _e: batch)
        if not spent:
            ok = _redrive(root, params, item_id, deps, deps.now(), at)
            extra_tags.extend([] if ok else ["redrive=failed"])
        return finish("escalated" if spent else "deferred", n, f"reason={reason}")

    if deps.interactive(root, now):
        return defer("interactive", _delay(now, params["retry_backoff_minutes"]))
    soak = info.kind == "soak"
    lane = "soak" if soak else "normal"
    if not throttle.acquire(lane, item_id, budget, now, identity=deps.identity, pid=deps.pid):
        return defer("busy", _delay(now, params["busy_backoff_minutes"]))
    held = True
    try:
        pace = deps.pace(now)
        if not soak:
            reset = (now + timedelta(minutes=pace.short_reset_min)
                     if pace.ok and pace.short_reset_min is not None else None)
            w_start, w_end = throttle.window(now, reset, params)
            fresh = fold(oi_ledger.read_events(oi_params.ledger_path(root))[0], params, now)
            if not throttle.window_slot(fresh.items[item_id], fresh.items,
                                        throttle.runs_in_window(w_start), w_end, now, params):
                throttle.release(lane, deps.pid)
                held = False
                return defer("window_cap", _after_reset(now, pace, params["retry_backoff_minutes"]))
        if (why := pace.deferral()):
            log(item_id, f"quota deferral: {why}", now)
            throttle.release(lane, deps.pid)
            held = False
            return defer("quota", _after_reset(now, pace, params["retry_backoff_minutes"]))
        if not soak:
            throttle.record_run(now, item_id)
        check = item["check"]
        if "realverify" in check:
            argv = ["python", str(_TOOLS / "realverify.py"), "run", "--case", check["realverify"],
                    *(["--long"] if info.long else [])]
        else:
            argv = list(check["argv"])
        wall = params["observe_timeout_minutes"] if item["kind"] == "observe" else info.wall_minutes
        env = {**os.environ, **_spawn_env(), "AUTOSDD_UNATTENDED": "1", "PYTHONUTF8": "1"}
        rc, out = deps.run(argv, wall * 60, env, root)
    finally:
        if held:
            throttle.release(lane, deps.pid)
    end = deps.now()
    ok, proof = _judge(item, root, rc, out, end)
    exhausted = n >= params["max_attempts"]
    if ok:
        oi_ledger.append(root, lambda _e: [attempt("pass", proof), event("close", evidence=proof)])
    else:
        batch = [attempt("fail", proof), *([event("escalate", reason="attempts_exhausted")]
                                           if exhausted else [])]
        oi_ledger.append(root, lambda _e: batch)
        if not exhausted:
            again = _redrive(root, params, item_id, deps, end,
                                                _delay(end, params["retry_backoff_minutes"]))
            extra_tags.extend([] if again else ["redrive=failed"])
    cov = (deps.coverage or (lambda r: _coverage(r, deps)))(root)
    extra_tags.extend(["coverage=failed"] if cov != "ok" else [])
    return finish("pass" if ok else ("escalated" if exhausted else "fail"), n)


def _spawn_env() -> dict[str, str]:
    try:
        from lib import resume_route  # noqa: PLC0415 — 取不到只少一組 harness 上限，不擋驅動
        return resume_route.spawn_env()
    except Exception:  # noqa: BLE001
        return {}
