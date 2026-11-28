"""排程入口崩潰護欄（WP-SW D-SW-2／REQ-CTL-50；DES §24.2）。

立案（暴露證據）：2026-11-28 10:21:52 舊哨兵在 pythonw 下崩潰，排程器自報 `LastTaskResult=1`、
`NextRunTime` 空白，續航日誌 `sentinel_woken` 後中斷——崩潰沒有任何痕跡與告警，死因只能靠實驗反推
（與 R-4.5.6-4（b）相反）。本檔讓「由排程器起的 Python 入口」未捕捉例外 ⇒ ①落痕跡
（`sentinel_crashed`／`park_job_crashed`／`sentinel_crash_loop`）②走既有告警管道 `alert(loud=True)`
③仍重排下一次巡邏；連續 `CRASH_STREAK_MAX` 次停止重排（鐵律六同族：不留每 15 分鐘的無聲空轉）並
留 handback；正常 tick 使 streak 歸零並落 `sentinel_crash_cleared`。

純轉接＋三件事，判準與常數全在本葉；planner 的分派處只寫一行呼叫（LOC 牆）。本檔自身不得拋。
`alert(loud=True)` 對 `dead_agents==0` 只寫紙（note 檔）＋入通知佇列、不敲桌面（HELM-01），故崩潰告警的
實際落點是 note＋佇列，不是 toast。
"""  # noqa: E501
from __future__ import annotations

import json
import traceback
from datetime import datetime, timedelta
from pathlib import Path

CRASH_STREAK_MAX = 3  # 只准不變或下修：瞬時環境問題 vs 結構性崩潰的最小分辨量
CRASH_TB_MAX_CHARS = 1500
EV_CRASHED, EV_PARK, EV_LOOP, EV_CLEARED = (
    "sentinel_crashed", "park_job_crashed", "sentinel_crash_loop", "sentinel_crash_cleared")
#: 排程入口清單（入口名 → 入口檔與旗標字面；新增排程入口而未入表＝AT-CTL-101 紅）
ENTRIES = {
    "sentinel-tick": ("session_resume_planner.py", "--sentinel-tick"),
    "resume-tick": ("session_resume_planner.py", "--resume-tick"),
    "park-fire": ("sessionctl.py", "--fire"),
    "oldwin-job": ("sessionctl.py", "--retry"),
}
_PARK_ENTRIES = ("park-fire", "oldwin-job")
_REPO = Path(__file__).resolve().parents[3]
_SHOWN = (EV_LOOP, EV_CLEARED, "sentinel_gc")


def _info(exc: BaseException) -> dict:
    frames = traceback.extract_tb(exc.__traceback__)
    last = frames[-1] if frames else None
    try:
        rel = str(Path(last.filename).resolve().relative_to(_REPO)).replace("\\", "/") if last else ""  # noqa: E501
    except (ValueError, OSError):
        rel = Path(last.filename).name if last else ""
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return {"exc_type": type(exc).__name__, "file": rel, "line": last.lineno if last else 0,
            "tb": tb[-CRASH_TB_MAX_CHARS:]}


def _trace(event: str, **fields) -> None:
    from . import switch  # noqa: PLC0415

    switch.trace(event, **fields)


def _alert(reason: str, state, plan, alert=None) -> None:
    if alert is None:
        import quota_escalation  # noqa: PLC0415

        alert = quota_escalation.alert
    alert(reason, state if isinstance(state, dict) else {}, loud=True, plan=plan)


def _handback(sid: str, info: dict) -> None:
    try:
        import resume_route  # noqa: PLC0415

        path = resume_route.handback_report(f"{sid}_sentinel_crash_loop")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"## 做了什麼\n哨兵連續 {CRASH_STREAK_MAX} 次崩潰，已停止重排（痕跡 `{EV_LOOP}`）。\n\n"
            f"## 驗了什麼\n最後一次崩潰：{info['exc_type']} @ {info['file']}:{info['line']}。\n\n"
            "## 卡在哪\n排程器自報 NextRunTime 空白＝不會再響；喚醒鏈已斷。\n\n"
            "## 下一步指令\n`python tools/session_resume_planner.py --arm-sentinel --session-id "
            f"{sid}` 手動重新武裝，或 `claude -r {sid}`。\n", encoding="utf-8", newline="\n")
    except Exception:  # noqa: BLE001 — 寫不進去不拋
        pass


def _crashed(entry: str, exc: BaseException, on_crash, state_ref, interval_s: int,
             now, alert) -> int:
    info = _info(exc)
    park = entry in _PARK_ENTRIES
    st = None
    try:
        st = state_ref.read() if state_ref is not None else None
    except Exception:  # noqa: BLE001
        st = None
    st = st if isinstance(st, dict) else None
    sid = str((st or {}).get("session_id") or getattr(state_ref, "sid", "") or "")
    task = str((st or {}).get("task_name") or getattr(state_ref, "task", "") or entry)
    streak = (int((st or {}).get("crash_streak") or 0) + 1) if st is not None and not park else 1
    plan = getattr(state_ref, "plan", None)
    common = {"entry": entry, "sid": sid, "task": task, "streak": streak, **info}
    where = f"{info['exc_type']} @ {info['file']}:{info['line']}"
    if park:
        _trace(EV_PARK, **common)
        if on_crash is not None:
            on_crash(st, None, info)
        _alert(f"排程到點 job 崩潰（{where}）", st, plan, alert)
        return 1
    stop = st is not None and streak >= CRASH_STREAK_MAX
    if st is not None:
        st["crash_streak"] = streak
        try:
            state_ref.write(st)
        except Exception:  # noqa: BLE001
            pass
    if stop:
        _trace(EV_LOOP, **common, rearmed=False)
        _alert(f"哨兵連續 {streak} 次崩潰（{where}）、已停止重排——喚醒鏈斷線，請手動重新武裝", st, plan, alert)  # noqa: E501
        _handback(sid, info)
        return 1
    _trace(EV_CRASHED, **common)
    _alert(f"哨兵崩潰（{where}）、已自動重排", st, plan, alert)
    if st is not None and on_crash is not None:
        at = (now or datetime.now().astimezone()) + timedelta(seconds=interval_s)
        try:
            on_crash(st, at, info)
        except Exception:  # noqa: BLE001 — on_crash 自身拋：退化為只落痕跡（已落）
            pass
    return 1


def run(entry: str, body, *, on_crash=None, state_ref=None, interval_s: int = 900,
        now: datetime | None = None, alert=None) -> int:
    """包住排程入口：`body()` 拋 `Exception` ⇒ 留痕＋告警＋重排（`on_crash(state, at, info)`）；
    正常回傳值原樣回傳（rc 不被吞）。`state_ref`＝帶 `read()`／`write(state)` 的物件（可含 `sid`／
    `task`／`plan`）；`SystemExit`／`KeyboardInterrupt` 不攔。本函式自身不拋。"""
    try:
        rc = body()
    except Exception as exc:  # noqa: BLE001 — 本檔的存在理由
        try:
            return _crashed(entry, exc, on_crash, state_ref, interval_s, now, alert)
        except Exception:  # noqa: BLE001 — 護欄自己不得拋；最壞退化為已落的痕跡
            return 1
    try:
        st = state_ref.read() if state_ref is not None and entry not in _PARK_ENTRIES else None
        prev = int((st or {}).get("crash_streak") or 0) if isinstance(st, dict) else 0
        if prev > 0:
            st["crash_streak"] = 0
            state_ref.write(st)
            _trace(EV_CLEARED, entry=entry, sid=str(st.get("session_id") or ""),
                   task=str(st.get("task_name") or ""), prev_streak=prev)
    except Exception:  # noqa: BLE001
        pass
    return rc


class PlanRef:
    """任務書狀態塊的讀寫（planner 注入，本葉不 import planner）。"""

    def __init__(self, plan: Path, planner) -> None:
        self.plan, self._p = plan, planner
        self.sid = self.task = ""

    def read(self):
        return self._p.parse_relay(Path(self.plan).read_text(encoding="utf-8"))

    def write(self, state: dict) -> None:
        self._p._write_relay_best_effort(Path(self.plan), state)  # noqa: SLF001


def planner_tick(entry: str, args, planner) -> int:
    """planner 的 `--sentinel-tick`／`--resume-tick` 分派（一行呼叫）。"""
    plan = Path(args.plan or "unknown")
    sentinel = entry == "sentinel-tick"
    body = planner._sentinel_tick if sentinel else planner._resume_tick  # noqa: SLF001
    tick = planner.SENTINEL_TICK if sentinel else planner.RESUME_TICK

    def rearm(state, at, _info):
        return planner._register_and_record(plan, state, at, tick)[0]  # noqa: SLF001

    return run(entry, lambda: body(args), on_crash=rearm, state_ref=PlanRef(plan, planner),
               interval_s=planner.SENTINEL_INTERVAL_SECONDS)


def _flag(argv: list[str], name: str) -> str:
    return argv[argv.index(name) + 1] if name in argv[:-1] else ""


def run_park(cli, argv: list[str]) -> int:
    """`sessionctl park --fire` 的外層兜底：崩潰 ⇒ `park_job_crashed`＋標記走既有失敗鏈
    （`park_chain.settle` 結算 failed＋`park_announce.announce`），不讓標記留 armed。"""
    sid, label, pkg = _flag(argv, "--session-id"), _flag(argv, "--job"), _flag(argv, "--pkg")

    def settle_failed(_st, _at, info):
        from . import park, park_announce, park_chain  # noqa: PLC0415

        marker = park.read_marker(sid) if sid else None
        if marker is not None and marker["status"] == "armed" and label in {
                j["label"] for j in marker["jobs"]}:
            park_chain.settle(marker, "failed", EV_PARK, None, exc_type=info["exc_type"])
            attempts = [{"route": "crash", "fork": False, "attempted": True, "rc": 1,
                         "reason": f"{info['exc_type']} @ {info['file']}:{info['line']}"}]
            park_announce.announce(sid, Path(pkg), marker, attempts, repo=_REPO)

    ref = type("ParkRef", (), {"sid": sid, "task": label, "plan": None, "read": lambda s: None})()
    return run("park-fire", lambda: cli(argv), on_crash=settle_failed, state_ref=ref)


def status_lines(env=None) -> list[str]:
    """每個 sid 最新一筆 `{crash_loop, crash_cleared, sentinel_gc}`；最新為 loop ⇒ 一行。唯讀、
    任何例外回空。讀持久痕跡目錄（狀態塊在停止／GC 後會被清掉，痕跡不會）。"""
    try:
        import endurance_env  # noqa: PLC0415

        path = endurance_env.trace_dir_peek()[0] / "autosdd_session_switch.jsonl"
        with path.open("rb") as handle:
            size = handle.seek(0, 2)
            handle.seek(max(0, size - 2_000_000))
            rows = handle.read().decode("utf-8", "replace").splitlines()
        last: dict[str, dict] = {}
        for raw in rows:
            try:
                row = json.loads(raw)
            except ValueError:
                continue
            if isinstance(row, dict) and row.get("event") in _SHOWN and row.get("sid"):
                last[str(row["sid"])] = row
        return [f"哨兵因連續崩潰停止：{r.get('task')}／{str(r['sid'])[:8]}／{r.get('exc_type')}@"
                f"{r.get('file')}:{r.get('line')}（{r.get('at')}）；手動重新武裝見 handback"
                for r in last.values() if r.get("event") == EV_LOOP]
    except Exception:  # noqa: BLE001
        return []


__all__ = ["run", "planner_tick", "run_park", "status_lines", "ENTRIES", "CRASH_STREAK_MAX",
           "CRASH_TB_MAX_CHARS", "EV_CRASHED", "EV_PARK", "EV_LOOP", "EV_CLEARED"]
