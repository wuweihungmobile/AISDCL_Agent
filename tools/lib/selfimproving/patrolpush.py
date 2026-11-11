"""SelfImproving `push-run`：把已守門放行的巡邏提交推上遠端
（TCS-SelfImproving-P7 AC-SI-49-6～49-13）。

能力類別 `exec`：**整個套件 git 子命令 `push` 的唯一出處**，外部行程只經
`runner.run_argv`（明示環境、逾時殺行程樹）。巡邏器本體（S4U 任務）永不推送；本檔由
互動登入型任務 `AutoSDD_SI_Push` 每心跳執行一次（`tools/selfimproving.py push-run`），
沒有待推送就零動作。

流程：寫 `push/tick.json`→取 `locks/push.lock`（取不到＝`PUSH-RUNNING`）→
`pushguard.evaluate`（含重試判準）→放行才寫 `push/current.json` 並以**明寫的 sha**
`git push origin <sha>:refs/heads/main`（不推裸 HEAD、不 force、不帶 `--no-verify`）→
分類、遮罩、寫 `push/results/<sha12>.json`→刪 `current.json`。最外層攔住未處理例外並寫
`push/last_error.json`（`pythonw` 沒有 stderr，這是唯一可見痕跡）。

憑證面：不剔除使用者的憑證類環境變數（git 要用），但**不寫入任何檔**——落地的只有
tick／current／結果／last_error 四種 dict，結果文字一律經 `pushguard.mask`；名稱含
`AUDIT_KEY` 的變數不傳給 git。rc：0＝推成功或無事可做（含任何守門未放行碼）；1＝推送
失敗、結果檔寫失敗或未處理例外；授權拒收與用法錯誤由入口處理（1、3）。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from lib import apply_lock

from . import check as si_check
from . import events as si_events
from . import patrolrun, pushguard, runner, sched, unattended

AFTER_GUARD_HOOK = None  # 測試縫：守門之後、`run_argv` 之前呼叫 `hook(repo)`（僅測試設定）
WALL_SECONDS_OVERRIDE = None  # 測試縫：縮短牆鐘（秒）
LOCK_SLACK_SECONDS = 600  # 陳舊鎖＝牆鐘＋此值
LOCK_WAIT_SECONDS = 1  # 取鎖等待（秒）：逾時＝另一個 push-run 在跑；也讓陳舊鎖在一輪內回收
DROP_ENV = ("AUTOCLAUDE_SKIP_HOOKS", "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")
PARAM_KEYS = ("sched_auto_push", "sched_heartbeat_minutes", "sched_push_wall_minutes",
              "sched_push_attempts_max", "sched_push_retry_minutes")
TREE_CHANGED_NOTE = "；閘門期間工作樹有變動"
_FAILED = ("PUSH-AUTH", "PUSH-REJECTED", "PUSH-HOOK-FAILED", "PUSH-WALL-EXCEEDED", "PUSH-FAILED")


def push_env(parent) -> dict[str, str]:
    """傳給 git 的環境：父環境副本（pre-push 閘門要用人用的同一組變數；憑證類變數也保留，
    git 要用）剔除 `DROP_ENV` 與名稱含 `AUDIT_KEY` 者，另明示 `GIT_TERMINAL_PROMPT=0`、
    `GCM_INTERACTIVE=never`。"""
    kept = unattended.without_run_scope(parent)  # 去無人值守／運轉範圍變數（單一實作）
    env = {k: v for k, v in kept.items() if k not in DROP_ENV and "AUDIT_KEY" not in k}
    env.update(GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")
    return env


def push_argv(repo: Path, sha: str) -> list[str]:
    return ["git", "-C", str(repo), "push", "origin", f"{sha}:refs/heads/main"]


def _put(path: Path, obj: dict) -> None:
    """原子寫入（tmp→`os.replace`）；本檔唯一的寫檔站點，內容只來自四種 dict。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_bytes((json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")
                        .encode("utf-8"))
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


def _out(code: str, as_json: bool, rc: int, *, sha=None, ahead=0, attempts=0,
         text="") -> tuple[int, str]:
    if as_json:
        return rc, json.dumps({"ok": rc == 0, "kind": "push-run", "code": code, "sha": sha,
                               "ahead": ahead, "attempts": attempts}, ensure_ascii=False) + "\n"
    head = f"push-run code={code} sha={(sha or '-')[:12]} ahead={ahead} attempts={attempts}\n"
    return rc, head + (f"{text}\n" if text else "")


def _push(repo: Path, si: Path, res: dict, params: dict, now: datetime, run_argv, clock,
          as_json: bool) -> tuple[int, str]:
    """守門放行後的實推：current.json→`run_argv`→分類與結果檔；`current.json` 一律在
    `finally` 刪除。"""
    folder, sha = si / "push", res["sha"]
    prev = pushguard.result_of(si, sha)
    attempts = int((prev or {}).get("attempts") or 0) + 1
    wall = WALL_SECONDS_OVERRIDE or params["sched_push_wall_minutes"] * 60
    current = {"sha": sha, "pid": os.getpid(), "started_at": sched.iso(now),
               "wall_due_at": sched.iso(now + timedelta(seconds=wall))}
    _put(folder / "current.json", current)
    try:
        if AFTER_GUARD_HOOK is not None:
            AFTER_GUARD_HOOK(repo)
        run = run_argv(push_argv(repo, sha), env=push_env(os.environ), timeout=wall, cwd=repo)
        output = (getattr(run, "out", "") or "") + "\n" + (getattr(run, "err", "") or "")
        code = pushguard.classify(getattr(run, "rc", None), getattr(run, "timed_out", False),
                                  output)
        changed = bool(sched.dirty_paths(repo))  # 推送期間人的改動會影響閘門結果：只偵測、不改碼
        text = pushguard.last_line(output) + (TREE_CHANGED_NOTE if changed else "")
        result = {"sha": sha, "finished_at": sched.iso(sched.aware(clock())),
                  "rc": getattr(run, "rc", None), "code": code, "text": text,
                  "attempts": attempts, "tree_changed": changed}
        try:
            _put(folder / "results" / f"{sha[:12]}.json", result)
        except OSError:
            return _out("PUSH-RESULT-WRITE-FAILED", as_json, 1, sha=sha, ahead=res["ahead"],
                        attempts=attempts, text="結果檔寫入失敗（不重推）")
    finally:
        (folder / "current.json").unlink(missing_ok=True)
    return _out(code, as_json, 1 if code in _FAILED else 0, sha=sha, ahead=res["ahead"],
                attempts=attempts, text=text)


def _internal_error(si: Path, exc: Exception, as_json: bool, clock) -> tuple[int, str]:
    body = pushguard.mask(" ".join(str(exc).split()))
    text = f"{type(exc).__name__}: {body}"[:pushguard.TEXT_MAX]
    err = {"at": sched.iso(clock()), "code": "PUSH-INTERNAL-ERROR", "text": text}
    try:
        _put(si / "push" / "last_error.json", err)
        (si / "push" / "current.json").unlink(missing_ok=True)
    except OSError:
        pass
    return _out("PUSH-INTERNAL-ERROR", as_json, 1, text=text)


def run(repo: Path, *, as_json: bool = False, dry_run: bool = False,
        now: datetime | None = None, run_argv=None, alive=None) -> tuple[int, str]:
    """`push-run` 本體（授權閘由入口在呼叫前判）；回（rc, 輸出）。`InputError`（params
    缺鍵）原樣外拋＝rc 3；其餘未處理例外一律轉 `PUSH-INTERNAL-ERROR`。`run_argv` 缺省＝
    呼叫當下的 `runner.run_argv`。"""
    si = si_events.si_dir()
    params = si_check.params_for(repo, *PARAM_KEYS)
    alive = alive or patrolrun._alive  # noqa: SLF001  # 與巡邏器同一個「行程存活」判準
    run_argv = run_argv or runner.run_argv
    try:
        clock = (lambda: now) if now is not None else (lambda: datetime.now().astimezone())
        now = sched.aware(clock())
        if dry_run:
            res = pushguard.evaluate(repo, params, si, now, alive=alive, gate_retry=True)
            return _out(res["code"] or "PUSH-READY", as_json, 0, sha=res["sha"],
                        ahead=res["ahead"], text=res["text"])
        _put(si / "push" / "tick.json", {"tick_at": sched.iso(now), "by": "push-run"})
        wall = WALL_SECONDS_OVERRIDE or params["sched_push_wall_minutes"] * 60
        (si / "locks").mkdir(parents=True, exist_ok=True)
        try:
            with apply_lock.acquire(si / "locks" / "push.lock", LOCK_WAIT_SECONDS,
                                    wall + LOCK_SLACK_SECONDS):
                res = pushguard.evaluate(repo, params, si, now, alive=alive, gate_retry=True)
                if not res["ok"]:
                    return _out(res["code"], as_json, 0, ahead=res["ahead"], text=res["text"])
                return _push(repo, si, res, params, now, run_argv, clock, as_json)
        except apply_lock.LockBusyError:
            return _out("PUSH-RUNNING", as_json, 0, text="另一個 push-run 正在推送")
    except Exception as exc:  # noqa: BLE001  # 最外層：pythonw 沒有 stderr，改留 last_error.json
        return _internal_error(si, exc, as_json, clock)
