"""`sessionctl park`：額度自願停工前掛好「到點由新 session 帶交接包接手」的排程（ADR §2.17）。

流程順序是契約（測試以呼叫序列斷言）：政策閘 → 讀 reset → 交接包 finalize＋spawn 預演 → 取代舊標記
→ 登記排程拿憑證 → 寫標記（寫失敗即回滾排程）。拿不到憑證一律不寫標記、不宣稱已排程。
job 本體 `--fire` 先查有沒有人在動（只信對話記錄，不信檔案 mtime）再 `handoff.spawn`。
排程只經 `engine_resume_job.arm_oneshot`／`schedule_backend.select()`，本檔不含任何排程器原語。
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import sandbox_scope

from . import handoff, park, park_reset, se_gate, switch

PARK_CMD = park.PARK_CMD
_REPO = Path(__file__).resolve().parents[3]
_RC_PRECOND, _RC_REFUSED, _RC_NOSID = 2, 4, 3


def job_label(sid: str, fire: datetime) -> str:
    """每次新名字（含觸發分鐘），避免對正在跑的自己 bootout（DEF-200-526 的形狀）。"""
    return f"AutoSDD_HandoffSpawn_{sid[:8]}_{fire:%Y%m%d%H%M}"


def job_argv(label: str, sid: str, pkg, fire: datetime, extra=()) -> list[str]:
    """`extra`＝`se_gate.register` 判決的 `--job-env`／`--claude`（無顯式值 ⇒ 空 ⇒ 逐字不變）。"""
    import win_spawn  # noqa: PLC0415 — lazy

    return [win_spawn.quiet_python(), str(_REPO / "tools" / "sessionctl.py"), "park", "--fire",
            "--job", label, "--session-id", sid, "--pkg", str(pkg), "--fire-at",
            fire.isoformat(timespec="seconds"), *extra]


def _err(text: str) -> None:
    print(text, file=sys.stderr)


def _backend(S: dict):
    import schedule_backend  # noqa: PLC0415 — lazy

    return S.get("backend") or schedule_backend.select()


def _disarm_verified(label: str, S: dict) -> bool:
    """`disarm` rc==0 且 `list_jobs` 量得到、且不再列出——量不到不宣稱已移除。"""
    backend = _backend(S)
    rc = (S.get("disarm") or backend.disarm)(label)
    listed = (S.get("jobs") or backend.list_jobs)(label)
    return rc == 0 and listed is not None and label not in listed


def _settle(marker: dict, status: str, event: str, **detail) -> None:
    """標記改終態＋outcome；寫不進去不拋（痕跡已落，讀取端寧可當無憑證）。"""
    stamp = datetime.now().astimezone().isoformat()
    park.write_marker(dict(marker, status=status,
                           outcome={"at": stamp, "event": event, "detail": str(detail)}))


def _supersede(sid: str, S: dict) -> bool:
    """取代舊標記前先撤舊排程（逐 job 驗證）；任一失敗 ⇒ False（不登記新的）。"""
    old = park.read_marker(sid)
    if old is None or old.get("status") != "armed":
        return True
    results = [_disarm_verified(job["label"], S) for job in old["jobs"]]
    if all(results):
        _settle(old, "cancelled", "superseded")
    return all(results)


def _refusal_text(env, S: dict) -> tuple[int, str]:
    """政策閘：`(0, "")` 通過；否則 `(4, 訊息)`。"""
    if env.get(park.UNATTENDED_ENV):
        return _RC_REFUSED, ("❌ park 拒絕：無人窗口（AUTOSDD_UNATTENDED 有設）。無人續跑由 "
                             "planner 的 FRESH 路與 DEF-200-575 牆鐘負責，不在這裡掛排程。")
    mode = switch.switch_mode(env)
    if mode != "auto":
        return _RC_REFUSED, (f"❌ park 拒絕：AUTOSDD_SESSION_SWITCH_MODE={mode}"
                             "（park 的 H 路需要 auto）。")
    backend = _backend(S)
    if backend.name == "none":
        return _RC_REFUSED, ("❌ park 拒絕：本平台沒有已實作的排程載具（載具＝none）："
                             "Windows 走 schtasks、macOS 走 launchd。")
    return 0, ""


def _pick_package(sid: str, opts, env):
    if opts.pkg:
        return Path(opts.pkg)
    rows = [r for r in handoff.list_handoffs(env=env) if r["sid"] == sid and r["state"] == "live"]
    return rows[-1]["path"] if rows else None


def _cmd_park(opts, sid: str, env, S: dict, now: datetime) -> int:
    rc, text = _refusal_text(env, S)
    if rc:
        _err(text)
        switch.trace("park_refused", sid=sid, why=text, code=rc)
        return rc
    reset, axis, skew, rc = park_reset.resolve(opts, sid, S, now)
    if rc:
        return rc
    pkg = _pick_package(sid, opts, env)
    if pkg is None or not Path(pkg).is_file():
        _err(f"❌ park 前置不成立：session {sid} 沒有 live 的交接包。先 python tools/sessionctl.py "
             "handoff --build，補完主控層，再 --finalize。")
        return _RC_PRECOND
    frc, problems = handoff.finalize(pkg)
    if frc:
        _err("❌ park 前置不成立：交接包主控層未通過 finalize：\n"
             + "\n".join(f"  - {p}" for p in problems))
        return _RC_PRECOND
    refused = handoff.spawn_preflight(pkg, runner=S.get("runner"), roster_mod=S.get("roster"))
    if refused:
        _err("❌ park 前置不成立：spawn 前置預演未過（到點必失敗，所以現在就拒絕）：\n"
             + "\n".join(f"  - {r}" for r in refused))
        return _RC_PRECOND
    import engine_resume_job as erj  # noqa: PLC0415

    fire = erj.fire_time(reset, skew, now)
    route, reason = park.park_route((fire - now).total_seconds(), unattended=False, mode="auto",
                                    carrier_ok=True)
    reg = se_gate.register("park_cli._cmd_park", repo=_REPO, pkg=pkg, fire=fire, env=env,
                           sid=sid, claude=opts.claude)
    if reg.rc:
        return reg.rc  # L1 拒絕：不取代舊標記、不登記（rc 4／job 環境值不合法 2）
    if not _supersede(sid, S):
        _err("❌ 舊的 park 排程沒有真的被移除 ⇒ 不登記新的（避免雙排程）。")
        return 1
    label = job_label(sid, fire)
    arm = S.get("arm") or erj.arm_oneshot
    arc, cred = arm(label, job_argv(label, sid, pkg, fire, reg.extra), str(_REPO), fire,
                    interactive=True, **({"expire_at": reg.expire} if reg.expire else {}))
    if arc != 0 or not str(cred).strip():
        _err(f"❌ 排程沒有成立（rc={arc}，憑證取不到）⇒ 本工具不會說它已排程。")
        switch.trace("park_arm_failed", sid=sid, label=label, rc=arc, why="no-credential",
                     rolled_back=False)
        return 1
    marker = {"schema": park.SCHEMA, "sid": sid, "route": park.ROUTE_H, "status": "armed",
              "parked_at": now.isoformat(), "reset_at": reset.isoformat(),
              "fire_at": fire.isoformat(), "axis": axis, "pkg": str(pkg), "why": opts.why,
              "valid_until": (fire + timedelta(seconds=park.YIELD_GRACE_SECONDS)).isoformat(),
              "jobs": [{"label": label, "role": "primary", "fire_at": fire.isoformat(),
                        "credential": str(cred)}], "reason": reason, "outcome": None}
    if opts.claude:
        marker["claude"] = opts.claude  # 供 QW §7.6 哨兵接手沿用同一執行檔（未給 ⇒ 標記逐字不變）
    ok, msg = park.write_marker(marker)
    if not ok:
        gone = _disarm_verified(label, S)
        _err(f"❌ park 標記寫不進去：{msg}；已回滾剛登記的排程 {label}"
             f"（驗證：{'已移除' if gone else '還在'}）。")
        switch.trace("park_arm_failed", sid=sid, label=label, rc=1, why=msg, rolled_back=gone)
        return 1
    switch.trace("park_armed", sid=sid, route=park.ROUTE_H, reason=reason,
                 fire_at=fire.isoformat(), reset_at=reset.isoformat(), labels=[label],
                 credentials=[str(cred)])
    at_text = fire.isoformat(timespec="seconds")
    print(cred)
    print(f"park 已掛好：到點（{at_text}）若這個 session 沒有人在動，就由新 session 帶交接包接手。"
          "現在可以結束回合；不要請人回這個視窗接手。")
    print(f"PARK_VERDICT=armed route=H sid={sid[:8]} fire_at={at_text} "
          f"credential={str(cred).split('（')[0].strip()}")
    return 0


def _cmd_done(opts, sid: str, env, S: dict, now: datetime) -> int:
    if len((opts.why or "").strip()) < park.MIN_WHY_CHARS:
        _err(f"❌ --done 需要 --why（至少 {park.MIN_WHY_CHARS} 字的原因）。")
        return _RC_PRECOND
    if env.get(park.UNATTENDED_ENV):
        _err("❌ park 拒絕：無人窗口不宣告收工。")
        return _RC_REFUSED
    limit = now + timedelta(seconds=park.DONE_MAX_SECONDS)
    try:
        import quota_gate  # noqa: PLC0415

        axes = (S.get("quota") or quota_gate.pace_state)(now).axes
        resets = [w for a in park.short_axes(axes)
                  if (w := park._aware_future(a.resets_at, now)) is not None]
        limit = min([limit, *resets])
    except Exception:  # noqa: BLE001 — 量不到 reset 就用 5 小時上限
        pass
    if not _supersede(sid, S):
        _err("❌ 舊的 park 排程沒有真的被移除 ⇒ 不改寫標記。")
        return 1
    marker = {"schema": park.SCHEMA, "sid": sid, "route": park.ROUTE_DONE, "status": "armed",
              "parked_at": now.isoformat(), "reset_at": None, "fire_at": None, "axis": None,
              "pkg": None, "why": opts.why.strip(), "valid_until": limit.isoformat(), "jobs": [],
              "reason": "收工宣告", "outcome": None}
    ok, msg = park.write_marker(marker)
    if not ok:
        _err(f"❌ park 標記寫不進去：{msg}")
        return 1
    switch.trace("park_done", sid=sid, why=opts.why.strip(), valid_until=limit.isoformat())
    print(f"有效到 {limit.isoformat()}（reset 或 5 小時，取早者）；到期後 Stop 守衛恢復判準")
    return 0


def _cmd_cancel(sid: str, S: dict) -> int:
    marker = park.read_marker(sid)
    if marker is None:
        print("無 park 標記")
        return 0
    for job in marker["jobs"]:
        if not _disarm_verified(job["label"], S):
            _err(f"❌ {job['label']} 沒有真的被移除（仍在排程器裡）")
            return 1
    _settle(marker, "cancelled", "cancel")
    switch.trace("park_cancelled", sid=sid, labels=[j["label"] for j in marker["jobs"]])
    print("park 已取消")
    return 0


def _cmd_status(opts, sid: str, S: dict) -> int:
    marker = park.read_marker(sid)
    if marker is None:
        print("無 park 標記")
        return 0
    print(f"route={marker['route']} status={marker['status']} fire_at={marker['fire_at']} "
          f"valid_until={marker['valid_until']}")
    if marker["status"] == "refused":
        print(f"  refused：{(marker.get('outcome') or {}).get('detail', '')}")
    for job in marker["jobs"]:
        live = ""
        if opts.verify:
            listed = (S.get("jobs") or _backend(S).list_jobs)(job["label"])
            where = "量不到" if listed is None else "在" if job["label"] in listed else "不在"
            live = f"｜排程器中：{where}"
        print(f"  job {job['label']}｜憑證 {job['credential']}{live}")
    return 0


def _write_failed_handback(sid: str, pkg: Path, rc: int, route: str = park.FIRE_FRESH) -> None:
    import resume_route  # noqa: PLC0415

    what = "續跑原 session（claude -r）" if route == park.FIRE_RESUME else "spawn 新 session"
    body = (f"## 做了什麼\npark 排程到點，{what}失敗（rc={rc}）。\n\n"
            "## 驗了什麼\n標記 armed、交接包 live、舊 session 無人在動後才動手。\n\n"
            f"## 卡在哪\n{route} 路 rc={rc}（原因見 autosdd_session_switch 痕跡）。\n\n"
            f"## 下一步指令\n`claude -r {sid}` 手動回舊 session，或 "
            f"`python tools/sessionctl.py handoff --spawn {pkg}`。\n")
    try:
        path = resume_route.handback_report(f"{sid}_park_failed")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8", newline="\n")
    except OSError:
        pass


def _find_transcript(sid: str, env):
    import harness_feed  # noqa: PLC0415

    return harness_feed.pick_transcript(handoff._project_dir(_REPO), sid, env)[0]


def _fire_route(transcript, env, now: datetime) -> tuple[str, str, int | None]:
    """到點選路（`park.fire_route`）：讀上下文與快取冷熱；任何讀取問題 ⇒ 量不到 ⇒ FRESH。"""
    from . import cachestate, roster  # noqa: PLC0415 — lazy：只有 job 本體需要

    held, cold = None, False
    try:
        if transcript is not None and Path(transcript).is_file():
            held = roster._scan(Path(transcript), False).get("ctx_tokens")
            cold = bool(cachestate.cache_state(transcript, now).get("cold"))
    except Exception:  # noqa: BLE001 — 讀不動不等於可以續跑，走既有交接包路
        held = None
    route, why = park.fire_route(held, cold, env)
    return route, why, held


RESUME_PROMPT = ("park 排程到點（額度已 reset）：續跑停工前的工作。停工前封存的交接包在 {pkg}"
                 "（供參考；以本 session 的上下文為主）。{rules}")


def spawn_resume(sid: str, pkg, *, runner=None, platform_name: str | None = None, env=None,
                 repo: Path | None = None, projects_dir: Path | None = None, alive=None, sleep=None,
                 wait_seconds: float = handoff.SPAWN_WAIT_SECONDS,
                 claude: str | None = None) -> int:
    """F4 的 RESUME 路：另開可見互動視窗 `claude -r <sid> <提示>` 續原 session。成功憑證＝行程
    存活**且**原逐字稿變大（或專案目錄出現新檔）；沒出現就照實回非零，不報成功。
    非 Windows／模式非 auto／無人窗口一律不外呼（同 `handoff.spawn` 的圍籬）。"""
    import subprocess  # noqa: PLC0415
    import time  # noqa: PLC0415

    env = os.environ if env is None else env
    if env.get(park.UNATTENDED_ENV):
        _err("❌ 無人窗口不開互動視窗。")
        return 1
    if se_gate.check("park_cli.spawn_resume", repo=repo or _REPO, pkg=pkg, sid=sid, claude=claude,
                     projects_dir=projects_dir):  # L1：早於 runner；與無人旗標互不相依
        return sandbox_scope.RC_SIDEEFFECT_REFUSED
    if switch.switch_mode(env) != "auto" or (platform_name or sys.platform) != "win32":
        _err("❌ 不自動續跑：只有 Windows 且 AUTOSDD_SESSION_SWITCH_MODE=auto 才開窗。"
             f"手動做法：在 repo 根執行 `claude -r {sid}`。")
        return 1
    repo = Path(repo or _REPO)
    proj = Path(projects_dir) if projects_dir is not None else handoff._project_dir(repo)
    tpath = proj / f"{sid}.jsonl"
    before = {p.name for p in proj.glob("*.jsonl")} if proj.is_dir() else set()
    size0 = tpath.stat().st_size if tpath.is_file() else 0
    prompt = RESUME_PROMPT.format(pkg=pkg, rules=switch.FRESH_HARD_RULES)
    flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0x10)
    rc, out, pid = (runner or handoff.build.default_runner)(
        [claude or "claude", "-r", sid, prompt], cwd=str(repo), env=handoff.washed_env(env),
        creationflags=flags, wait=False)
    if rc != 0 or pid is None:
        _err(f"❌ 續跑視窗開啟失敗（rc={rc}）{out}")
        return 1
    sleep, alive = sleep or time.sleep, alive or handoff._alive

    def grew() -> bool:
        return (tpath.is_file() and tpath.stat().st_size > size0) or bool(
            handoff._new_files(proj, before))

    deadline = time.monotonic() + wait_seconds
    ok = grew()
    while not ok and time.monotonic() < deadline and alive(pid):
        sleep(1)
        ok = grew()
    up = alive(pid)
    switch.trace("session_resume_spawned", sid=sid, pid=pid, handoff=str(pkg), ok=ok and up)
    if not (ok and up):
        _err(f"❌ 已起行程 pid={pid} 但{'逐字稿未增長' if up else '行程已不在'}"
             f"（{wait_seconds:g}s 內）⇒ 不報成功；請自行檢視新視窗。")
        return 1
    from . import seal  # noqa: PLC0415
    seal.mark_resumed(pkg)  # 同 sid 自續跑不算交棒：作廢封存（失敗不影響續跑結果，見 mark_resumed）
    print(f"✅ 已續跑原 session（pid={pid}，claude -r {sid[:8]}）。")
    return 0


def _cmd_fire(opts, sid: str, env, S: dict, clock) -> int:
    """job 本體（排程呼叫，勿手動）：先查再 spawn；結局只有 skipped／fired／failed 三種。"""
    label, pkg, now = opts.job or "", Path(opts.pkg or ""), clock()
    try:
        late = (now - datetime.fromisoformat(opts.fire_at)).total_seconds()
    except (TypeError, ValueError):
        late = None
    switch.trace("park_job_start", job=label, sid=sid, fire_at=opts.fire_at, late_s=late)
    refusal = se_gate.check("park_cli._cmd_fire", repo=_REPO, pkg=pkg, sid=sid, claude=opts.claude,
                            job=label)  # L1：先於一切讀標記／讓路觀察／spawn；拒絕＝終局
    marker = park.read_marker(sid)
    if refusal is not None:
        if marker is not None and marker["status"] == "armed" and label in {
                j["label"] for j in marker["jobs"]}:
            _settle(marker, "refused", "sideeffect_refused", reason=refusal.reason)
        _disarm_verified(label, S)
        return 0

    def finish(rc: int, status: str | None = None, event: str = "", **extra) -> int:
        if marker is not None and marker["status"] == "armed" and status:
            _settle(marker, status, event, **extra)
        _disarm_verified(label, S)  # 自拆（失敗不影響 rc：job 一次性，下次也不會被標記認作 armed）
        return rc

    def skip(reason: str, **extra) -> int:
        switch.trace("handoff_spawn_skipped", sid=sid, job=label, reason=reason, **extra)
        return finish(0, "skipped", reason)

    mine = marker is not None and label in {j["label"] for j in marker["jobs"]}
    if not mine or marker["status"] != "armed":
        return skip("cancelled" if marker and marker["status"] == "cancelled" else "not_armed")
    if env.get(park.UNATTENDED_ENV):
        return finish(_RC_REFUSED)
    if pkg.with_suffix(".ack").exists():
        return skip("acked")
    row = next((r for r in handoff.list_handoffs(env=env) if r["path"] == pkg), None)
    if row is None or row["state"] != "live":
        return skip("expired")
    import transcript_activity  # noqa: PLC0415

    find = S.get("transcript") or (lambda s: _find_transcript(s, env))
    transcript = find(sid)
    driver = transcript_activity.live_driver(transcript, now)
    if driver is not None:
        return skip("live_driver", driver_kind=driver["kind"], driver_at=driver["timestamp"])
    if handoff._duplicate_refusals(pkg, now, S.get("alive") or handoff._alive):
        return skip("spawned")  # forward／--spawn 已開出新 session、對方還沒 ack：不再動舊 sid
    claude_kw = {"claude": opts.claude} if opts.claude else {}  # 每次 spawn 嘗試同一執行檔（D-14）
    route, why, held = _fire_route(transcript, env, now)
    switch.trace("park_route", sid=sid, job=label, route=route, why=why, ctx=held)
    if route == park.FIRE_RESUME:
        from . import oldwin_park  # noqa: PLC0415 — lazy：舊視窗處置只有 job 本體需要

        gate = oldwin_park.resume_gate(sid, pkg, env, now, S)  # 先關舊窗再開，不讓同 sid 有兩個行程
        if gate["act"] == "retry":
            _disarm_verified(label, S)  # park 已把自己的到點排程重排到下一個觸發時刻
            return 0
        if gate["act"] == "skip":
            return skip(gate["reason"])
        if gate["act"] == "fail":
            _write_failed_handback(sid, pkg, 1, route)
            return finish(1, "failed", "park_resume_failed", spawn_rc=1, route=route)
        rc = (S.get("resume") or spawn_resume)(sid, pkg, env=env, **claude_kw)
        done, failed = "park_resumed", "park_resume_failed"
    else:
        rc = (S.get("spawn") or handoff.spawn)(pkg, **claude_kw)
        done, failed = "park_spawned", "park_spawn_failed"
    if rc == sandbox_scope.RC_SIDEEFFECT_REFUSED:  # spawn 站點 L1 拒絕＝終局，不算失敗、不走另一路
        return finish(0, "refused", "sideeffect_refused", route=route)
    if rc == 0:
        switch.trace(done, sid=sid, job=label, pkg=str(pkg), rc=rc, route=route)
        return finish(0, "fired", done)
    switch.trace(failed, sid=sid, job=label, pkg=str(pkg), rc=rc, route=route)
    _write_failed_handback(sid, pkg, rc, route)
    return finish(1, "failed", failed, spawn_rc=rc, route=route)


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="sessionctl park", allow_abbrev=False)
    group = ap.add_mutually_exclusive_group()
    for flag in ("done", "cancel", "status", "fire"):
        group.add_argument(f"--{flag}", action="store_true")
    for flag in ("session-id", "pkg", "at", "why", "job", "fire-at", "claude"):
        ap.add_argument(f"--{flag}")
    ap.add_argument("--verify", action="store_true")
    return ap


def run(argv: list[str], *, env=None, now: datetime | None = None,
        seams: dict | None = None) -> int:
    env, S = os.environ if env is None else env, dict(seams or {})
    args = argv[1:] if argv[:1] == ["park"] else list(argv)
    try:
        opts = _parser().parse_args(args)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) and exc.code else _RC_PRECOND
    import harness_feed  # noqa: PLC0415

    sid = opts.session_id or env.get(harness_feed.SESSION_ID_ENV, "")
    if not sid:
        _err("❌ 需要 --session-id 或環境變數 CLAUDE_CODE_SESSION_ID")
        return _RC_NOSID
    if not park._SID_RE.match(sid):
        _err("❌ session id 格式不合（只收英數與 -_）")
        return _RC_PRECOND
    clock = S.get("clock") or (lambda: now or datetime.now().astimezone())
    if opts.fire:
        return _cmd_fire(opts, sid, env, S, clock)
    if opts.cancel:
        return _cmd_cancel(sid, S)
    if opts.status:
        return _cmd_status(opts, sid, S)
    if opts.done:
        return _cmd_done(opts, sid, env, S, clock())
    return _cmd_park(opts, sid, env, S, clock())


def cli(argv: list[str] | None = None) -> int:
    return run(list(sys.argv[1:] if argv is None else argv))
