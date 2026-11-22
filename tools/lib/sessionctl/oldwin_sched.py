"""舊視窗關閉的重試排程、現查與回收（DES §7.1「重試」「現查與回收」；REQ-WP-57、101）。

· 重試工作名 `<前綴><舊 sid 8 碼>_<HHmm>`，前綴讀資料檔 `trace_dir()/oldwin/task_prefix`（缺＝出廠
  `AutoSDD_OldWinClose_`；RealVerify 沙盒由自己的 trace_dir 寫專屬前綴，不開測試用環境變數鉤）。
  憑證＝排程器自報的 NextRunTime，回讀不到即 rc≠0、不宣稱已排程（`arm_oneshot` 的既有契約）。
· 回收三處：重試行程結束時刪自己（`finally`）、登記新重試前先刪同舊 sid 前綴的既有工作、
  `handoff --ack`／
  `oldwin --retry` 啟動時順手 `sweep()`；各期收尾窗口另手跑 `sessionctl oldwin --sweep`。
· `stale`＝NextRunTime 為空且已執行過，或對應交接包已否決、已關閉、已放棄；`pending`＝其餘。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from . import handoff, oldwin, procstop, se_gate

DEFAULT_PREFIX = "AutoSDD_OldWinClose_"
_REPO = Path(__file__).resolve().parents[3]
_INDEX = "tasks.json"  # label → {handoff, old, new}：回收時要知道一個工作對應哪個交接包
_PS_INFO = (
    "[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);"
    "$t=Get-ScheduledTask -TaskName '{name}' -ErrorAction SilentlyContinue;"
    "if($t){{$i=$t|Get-ScheduledTaskInfo;"
    "$n=if($i.NextRunTime -and $i.NextRunTime.Year -gt 2000)"
    "{{$i.NextRunTime.ToString('o')}}else{{''}};"
    "$l=if($i.LastRunTime -and $i.LastRunTime.Year -gt 2000)"
    "{{$i.LastRunTime.ToString('o')}}else{{''}};"
    "@{{next=$n;last=$l;state=[string]$t.State}}|ConvertTo-Json -Compress}}")


def task_prefix() -> str:
    try:
        text = (oldwin._dir() / "task_prefix").read_text(encoding="utf-8").strip()
    except OSError:
        text = ""
    return text or DEFAULT_PREFIX


def task_info(label: str, runner=None) -> dict:
    """某工作的 `{next, last, state}`（Windows 走 Get-ScheduledTask；其餘平台回空 dict）。"""
    if not sys.platform.startswith("win"):
        return {}
    try:
        res = (runner or procstop.default_runner)(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
             _PS_INFO.format(name=label.replace("'", "''"))])
        return json.loads(res.stdout) if res.returncode == 0 and res.stdout.strip() else {}
    except (OSError, ValueError):
        return {}


def _backend(backend=None):
    import schedule_backend  # noqa: PLC0415 — lazy

    return backend or schedule_backend.select()


def _index(write: dict | None = None) -> dict:
    path = oldwin._dir(write is not None) / _INDEX
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        data = data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        data = {}
    if write is not None:
        data.update(write)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8", newline="\n")
        except OSError:
            pass
    return data


def job_argv(label: str, old_sid: str, new_sid: str, pkg, env, extra=()) -> list[str]:
    """重試工作的 argv：排程不帶環境變數 ⇒ trace_dir 與 quiet 分鐘數隨 argv 帶過去（沙盒才不會
    讀到真機的痕跡目錄）。`extra`＝`se_gate.register` 判決的 `--job-env`（居所與行為開關的允許表
    轉送；舊 `--trace-dir` 相容保留一版）。"""
    import endurance_env  # noqa: PLC0415
    import win_spawn  # noqa: PLC0415

    argv = [win_spawn.quiet_python(), str(_REPO / "tools" / "sessionctl.py"), "oldwin", "--retry",
            old_sid, "--pkg", str(pkg), "--new-sid", new_sid, "--job", label,
            "--trace-dir", str(endurance_env.trace_dir())]
    if env.get(oldwin.QUIET_ENV):
        argv += ["--quiet", str(env[oldwin.QUIET_ENV])]
    return argv + list(extra)


def schedule_retry(old_sid: str, new_sid: str, pkg, when: float, *, env=None,
                   now: datetime | None = None, arm=None, backend=None) -> tuple[int, str]:
    """登記一次性重試工作：先刪同舊 sid 前綴的既有工作（同一舊窗只留一個待觸發的重試），再註冊並回讀
    憑證。回 `(rc, 憑證)`；拿不到憑證 ⇒ `(1, "")`。"""
    import engine_resume_job as erj  # noqa: PLC0415

    env, now = os.environ if env is None else env, handoff._aware(now)
    fire = erj.fire_time(datetime.fromtimestamp(when).astimezone(), 0, now)
    reg = se_gate.register("oldwin_sched.schedule_retry", repo=_REPO, pkg=pkg, fire=fire, env=env,
                           sid=old_sid)
    if reg.rc:
        return reg.rc, ""  # L1 拒絕：不刪既有工作、不登記
    prefix = task_prefix()
    label = f"{prefix}{old_sid[:8]}_{fire:%H%M}"
    be = _backend(backend)
    for old in be.list_jobs(f"{prefix}{old_sid[:8]}") or []:
        if old != label:
            be.disarm(old)
    rc, cred = (arm or erj.arm_oneshot)(
        label, job_argv(label, old_sid, new_sid, pkg, env, reg.extra), str(_REPO), fire,
        **({"expire_at": reg.expire} if reg.expire else {}))
    if rc == 0 and str(cred).strip():
        _index({label: {"handoff": str(pkg), "old": old_sid, "new": new_sid}})
    return rc, str(cred)


def _is_stale(label: str, info: dict, pkg: str | None) -> bool:
    if not info.get("next") and info.get("last"):
        return True  # 已執行過、不會再觸發
    if pkg and (oldwin.vetoed(pkg) or any(
            rec.get("handoff") == pkg for rec in oldwin.events("oldwin_retry_abandoned"))
            or any(rec.get("handoff") == pkg for rec in oldwin.events("oldwin_closed"))):
        return True
    return False


def schedule_rows(*, backend=None, info=None) -> list[dict]:
    """現查：`AutoSDD_OldWinClose_*`（或沙盒前綴）全部工作 `{label, next, last, status}`；
    `status`＝`pending`／`stale`。量不到（無排程載具）回空 list。"""
    try:
        labels = _backend(backend).list_jobs(task_prefix()) or []
    except Exception:  # noqa: BLE001 — status 是唯讀診斷
        return []
    index = _index()
    rows = []
    for label in sorted(labels):
        meta = (info or task_info)(label)
        pkg = (index.get(label) or {}).get("handoff")
        rows.append({"label": label, "next": meta.get("next", ""), "last": meta.get("last", ""),
                     "status": "stale" if _is_stale(label, meta, pkg) else "pending"})
    return rows


def sweep(*, backend=None, info=None, env=None) -> list[str]:
    """刪除全部 `stale` 工作（不碰 `pending`、不碰否決檔）；回被刪的工作名。`env` 只為形態一致。"""
    removed = []
    be = _backend(backend)
    for row in schedule_rows(backend=be, info=info):
        if row["status"] == "stale" and be.disarm(row["label"]) == 0:
            removed.append(row["label"])
    return removed


def status_text(*, backend=None, info=None, env=None, sessions_dir=None) -> str:
    """`sessionctl status` 的舊窗區：重試排程列＋「只提醒」列（舊視窗仍開著）。"""
    lines = [f"舊窗重試排程：{r['label']}｜NextRunTime {r['next'] or '（空）'}｜"
             f"LastRunTime {r['last'] or '（無）'}｜{r['status']}"
             for r in schedule_rows(backend=backend, info=info)]
    lines += oldwin.reminder_lines(env, sessions_dir)
    return "\n".join(lines) + "\n" if lines else ""


def run_retry(opts, *, env=None, now: datetime | None = None, backend=None, **kw) -> int:
    """重試入口本體：先 `sweep`；有否決 ⇒ 刪自己、出聲一次、不再登記；否則五條件全部重判（可能再登記
    下一次重試）。不論結果，`finally` 刪除自己這一個工作。"""
    env = os.environ if env is None else env
    pkg, old, new = Path(opts.pkg), opts.retry, opts.new_sid or ""
    try:
        sweep(backend=backend, env=env)
        if oldwin.vetoed(pkg):
            oldwin.notice(new, "掌舵者以『留：』保留舊窗（不再自動關閉）。")
            oldwin.event("oldwin_retry_vetoed", old=old, new=new, handoff=str(pkg))
            return 0
        res = oldwin.close_if_eligible(old, new, pkg, env=env, now=now, **kw)
        print(res["text"] or f"舊窗未關閉（{res['reason']}）。")
        return 0  # 結局（關了／保留／再排程／放棄）都是正常結果，寫在輸出與 events.jsonl
    finally:
        if opts.job:
            try:
                _backend(backend).disarm(opts.job)
            except Exception:  # noqa: BLE001 — 自拆失敗留給 sweep
                pass


def cli(argv: list[str], *, env=None, **kw) -> int:
    """`sessionctl oldwin --retry <舊 sid> --pkg <包> [--new-sid][--job][--trace-dir][--quiet]`｜
    `--sweep`｜`--status`。"""
    ap = argparse.ArgumentParser(prog="sessionctl oldwin", allow_abbrev=False)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--retry", metavar="OLD_SID")
    group.add_argument("--sweep", action="store_true")
    group.add_argument("--status", action="store_true")
    for flag in ("pkg", "new-sid", "job", "trace-dir", "quiet"):
        ap.add_argument(f"--{flag}")
    try:
        opts = ap.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) and exc.code else 3
    if opts.trace_dir:
        os.environ["AUTOSDD_TRACE_DIR"] = opts.trace_dir  # 排程不帶環境：沿用排程當時的痕跡目錄
    if opts.quiet:
        os.environ[oldwin.QUIET_ENV] = opts.quiet
    env = os.environ if env is None else env
    if opts.sweep:
        removed = sweep(env=env)
        print(f"OLDWIN_SWEEP removed={len(removed)} labels={removed}")
        return 0
    if opts.status:
        sys.stdout.write(status_text(env=env) or "無舊窗重試排程。\n")
        return 0
    if not opts.pkg:
        print("❌ --retry 需要 --pkg <交接包>", file=sys.stderr)
        return 3
    return run_retry(opts, env=env, **kw)
