"""`sessionctl park`：額度自願停工前掛好「到點由新 session 帶交接包接手」的排程（ADR §2.17）。

流程順序是契約（測試以呼叫序列斷言）：政策閘 → 讀 reset → 交接包 finalize＋spawn 預演 → 取代舊標記
→ 登記排程拿憑證 → 寫標記（寫失敗即回滾排程）。拿不到憑證一律不寫標記、不宣稱已排程。
job 本體 `--fire` 先查有沒有人在動（只信對話記錄，不信檔案 mtime）、再讓路主載具，最後走失敗鏈
（本檔只留 L1 站點首判，其餘在 `park_fire`／`park_chain`；QuotaWall R218 Q3）。
排程只經 `engine_resume_job.arm_oneshot`／`schedule_backend.select()`，本檔不含任何排程器原語。
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import sandbox_scope

from . import (
    handoff,
    park,
    park_fire,
    park_register,
    park_reset,
    park_spawn,
    park_status,
    parkprobe,
    se_gate,
    switch,
)

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
    reset, axis, skew, rc = park_reset.resolve(opts, sid, S, now, env)
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

    primary = erj.fire_time(reset, skew, now)  # 主載具預定醒來；備援排程在其後 BACKUP_GRACE_MIN
    fire = park_register.backup_time(primary)
    route, reason = park.park_route((primary - now).total_seconds(), unattended=False,
                                    mode="auto", carrier_ok=True)
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
                        "credential": str(cred)}], "reason": reason, "outcome": None,
              **park_register.marker_fields(primary, fire, at_mode=bool(opts.at), env=env),
              **parkprobe.baseline(S, now)}  # W6：parked_pct／parked_account（量不到 ⇒ 不寫）
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
    sentinel = park_register.ensure_sentinel(sid, env, S, transcript=_transcript_or_none(sid, env),
                                             claude=opts.claude)
    print(cred)
    print(f"park 已掛好：到點（{fire.isoformat(timespec='seconds')}）若這個 session 沒有人在動，"
          "就由新 session 帶交接包接手。現在可以結束回合；不要請人回這個視窗接手。")
    print("\n".join(parkprobe.with_token(park_register.verdict_lines(
        sid, primary, fire, cred, sentinel, platform_name=S.get("platform")), marker, sentinel)))
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


def cancel_marker(sid: str, S: dict | None = None, *, event: str = "cancel") -> int:
    """撤銷 `sid` 的 park：逐 job 驗證拆除後標記 `cancelled`（`event` 記進 outcome）。
    `park --cancel`（`event="cancel"`）與 `ackhook.on_ack`（`event="acked"`，D-CT-12）共用。"""
    S = S or {}
    marker = park.read_marker(sid)
    if marker is None:
        print("無 park 標記")
        return 0
    for job in marker["jobs"]:
        if not _disarm_verified(job["label"], S):
            _err(f"❌ {job['label']} 沒有真的被移除（仍在排程器裡）")
            return 1
    _settle(marker, "cancelled", event)
    switch.trace("park_cancelled", sid=sid, labels=[j["label"] for j in marker["jobs"]])
    print("park 已取消")
    return 0


def _cmd_status(opts, sid: str, S: dict) -> int:
    marker = park.read_marker(sid)
    if marker is None:
        print("無 park 標記")
        print("\n".join(park_status.lines(sid, None, S, platform_name=S.get("platform"))))
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
    print("\n".join([*park_status.lines(sid, marker, S, platform_name=S.get("platform")),
                     parkprobe.status_row(marker, S)]))
    return 0


def _find_transcript(sid: str, env):
    import harness_feed  # noqa: PLC0415

    return harness_feed.pick_transcript(handoff._project_dir(_REPO), sid, env)[0]


def _transcript_or_none(sid: str, env):
    try:
        return _find_transcript(sid, env)
    except Exception:  # noqa: BLE001 — 哨兵武裝的逐字稿只是輔助參數
        return None


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
FORK_PROMPT_TAIL = ("你是從舊視窗 fork 出來的新 session（舊視窗仍開著、已交棒）：先 "
                    "`{cmd} --ack {pkg}`"
                    "，再接手。")


def spawn_resume(sid: str, pkg, *, runner=None, platform_name: str | None = None, env=None,
                 repo: Path | None = None, projects_dir: Path | None = None, alive=None, sleep=None,
                 wait_seconds: float = handoff.SPAWN_WAIT_SECONDS, claude: str | None = None,
                 fork: bool = False) -> int:
    """F4 的 RESUME 路：另開可見互動視窗 `claude -r <sid> <提示>` 續原 session；`fork=True`（同 sid
    有活著的互動舊窗，QW §7.4）加 `--fork-session`，舊窗保留。成功憑證見 `park_spawn.finish`
    （普通＝行程活且原逐字稿變大；fork＝行程活且出現 stem ≠ 原 sid 的新逐字稿）。
    非 Windows／模式非 auto／無人窗口一律不外呼（同 `handoff.spawn` 的圍籬）。"""
    import subprocess  # noqa: PLC0415

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
    if fork:
        prompt += FORK_PROMPT_TAIL.format(cmd=handoff._CMD, pkg=pkg)  # noqa: SLF001
    started = datetime.now().astimezone()
    flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0x10)
    argv = [claude or "claude", "-r", sid, *(["--fork-session"] if fork else []), prompt]
    rc, out, pid = (runner or handoff.build.default_runner)(
        argv, cwd=str(repo), env=handoff.washed_env(env), creationflags=flags, wait=False)
    if rc != 0 or pid is None:
        _err(f"❌ 續跑視窗開啟失敗（rc={rc}）{out}")
        return 1
    return park_spawn.finish(sid, pkg, pid, fork=fork, proj=proj, tpath=tpath, size0=size0,
                             before=before, started=started, alive=alive, sleep=sleep,
                             wait_seconds=wait_seconds)


def _cmd_fire(opts, sid: str, env, S: dict, clock) -> int:
    """job 本體（排程呼叫，勿手動）：L1 首判（拒絕＝終局 refused）後交 `park_fire.run`。"""
    label, pkg, now = opts.job or "", Path(opts.pkg or ""), clock()
    try:
        late = (now - datetime.fromisoformat(opts.fire_at)).total_seconds()
    except (TypeError, ValueError):
        late = None
    switch.trace("park_job_start", job=label, sid=sid, fire_at=opts.fire_at, late_s=late)
    refusal = se_gate.check("park_cli._cmd_fire", repo=_REPO, pkg=pkg, sid=sid, claude=opts.claude,
                            job=label)  # L1：先於一切讀標記／讓路觀察／spawn；拒絕＝終局
    marker = parkprobe.early_view(park.read_marker(sid), env)  # early＝提前到點：停用 §7.3 分支 A
    if refusal is not None:
        if marker is not None and marker["status"] == "armed" and label in {
                j["label"] for j in marker["jobs"]}:
            _settle(marker, "refused", "sideeffect_refused", reason=refusal.reason)
        _disarm_verified(label, S)
        return 0
    return park_fire.run(opts, sid, env, S, clock, marker, label, pkg, now)


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
        return cancel_marker(sid, S)
    if opts.status:
        return _cmd_status(opts, sid, S)
    if opts.done:
        return _cmd_done(opts, sid, env, S, clock())
    return _cmd_park(opts, sid, env, S, clock())


def cli(argv: list[str] | None = None) -> int:
    return run(list(sys.argv[1:] if argv is None else argv))
