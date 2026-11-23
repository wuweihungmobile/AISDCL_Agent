# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""sideeffect_selftest 家族：只由 `sideeffect` 案例以**子行程**呼叫的輔助案例（TCS §4 開頭；兩家族都不在
`run --all` 內，`runner.EXCLUDED_FROM_ALL`）。

控制協定（案例與子行程之間）：父案例把 JSON 規格寫在 `%TEMP%\\AutoSDD_RVctl_*` 的檔，路徑經環境變數
`RV_SE_SPEC` 帶給子行程；子行程做完佈置後寫 `spec["ready"]`（JSON：pid、sid、root、home…）再睡眠等父案例
`taskkill /F /PID`。這個環境變數只在**載具自己的子行程**之間用，不進任何產品判準（D-4）。
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

from lib.win_spawn import quiet_python

from .. import leases, sched
from ..sandbox import projects_dir, real_autosdd, slug_of
from . import CaseContext, case
from .sessionctl_park import PY, ps
from .sideeffect_lib import NOWIN, SPEC_ENV, arm_park, new_box, now

HOLD_DEFAULT_S = 1500  # 父案例沒來砍時的自然結束上限（25 分，小於租約 30 分）
# 直接登記的「未記帳」排程工作的 Action 載具：走 GUI 子系統（pythonw），即便到點觸發也不在桌面畫 console
# 視窗（`test_check_hooks_liveness` 的排程 Action 判準認 `quiet_python` 賦值來源）。
ACTION_PY = quiet_python()


def load_spec() -> dict:
    p = os.environ.get(SPEC_ENV, "")
    if not p or not Path(p).is_file():
        from ..driver import EnvMissing  # noqa: PLC0415
        raise EnvMissing(f"輔助案例缺 {SPEC_ENV} 規格檔（只能由 sideeffect 案例以子行程呼叫）")
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_ready(spec: dict, **info) -> None:
    """原子寫 ready 檔（先寫 .tmp 再 replace；父案例輪詢到才讀）。"""
    path = Path(spec["ready"])
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps({"pid": os.getpid(), **info}, ensure_ascii=False), encoding="utf-8", newline="\n")
    for attempt in range(20):  # Windows：父案例輪詢時可能正開著舊檔 ⇒ os.replace 會 PermissionError（WinError 5），短暫重試
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.1)


def hold(spec: dict) -> None:
    time.sleep(float(spec.get("hold_s") or HOLD_DEFAULT_S))


@case("RV-SE-OWNER", "sideeffect_selftest", refs=("E2E-SE-01",))
def rv_se_owner(ctx: CaseContext) -> None:
    """主人行程（TCS E2E-SE-01(a)）：建沙盒＋假 claude、授租約、`park --at <spec.at>`、寫 ready 後睡眠。
    父案例 `taskkill /F /PID <本行程>`（不帶 /T）殺掉它 ⇒ 身分檔的 owner_pid 已死、租約仍未過期。"""
    spec = load_spec()
    sb, exe = new_box(ctx, mode=spec.get("mode", "fail"), sleep=int(spec.get("sleep", 60)))
    at = datetime.fromisoformat(spec["at_iso"])
    armed = arm_park(ctx, sb, exe, at=at, ctx_tokens=spec.get("ctx_tokens"), extra_env=spec.get("env") or None,
                     grant_minutes=int(spec.get("grant_minutes", 30)))
    write_ready(spec, sid=sb.sid, root=str(sb.root), home=str(sb.home), label=armed.label,
                fire_at=armed.fire_at.isoformat(), pkg=str(armed.pkg), exe=str(exe))
    hold(spec)


@case("RV-SE-SEED", "sideeffect_selftest", refs=("E2E-SE-02",))
def rv_se_seed(ctx: CaseContext) -> None:
    """E2E-SE-02 的受害者：建沙盒（帳）、`register_once` 一支 `AutoSDD_RV_` 工作（+60 分）、經產品 `park --at`
    （+10 分；**不記帳**：它是產品自己登記的，由發現式掃描兜底）、啟動命令列含沙盒 sid 的睡眠行程，另以
    `Register-ScheduledTask` 直接建一支 Action 含沙盒根但不記帳的工作；寫 ready 後睡眠等被殺。"""
    spec = load_spec()
    sb, exe = new_box(ctx, mode="fail")
    rv_name = f"SE02a_{sb.sid[:8]}"
    local = (now() + timedelta(minutes=60)).replace(tzinfo=None).isoformat(timespec="seconds")
    ctx.sched_register(rv_name, local, '-c "pass"')
    armed = arm_park(ctx, sb, exe, at=now() + timedelta(minutes=10), ctx_tokens=60_000, grant_minutes=30, track=False)
    sleeper = subprocess.Popen([PY, "-c", "import time; time.sleep(3600)", sb.sid], cwd=str(sb.root),  # noqa: S603
                               creationflags=NOWIN)
    unacct = f"AutoSDD_RVunacct_{sb.sid[:8]}"
    rc, out = ps(f"$a = New-ScheduledTaskAction -Execute '{ACTION_PY}' -Argument '-c \"pass\" \"{sb.root}\"'; "
                 f"$t = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(90)); "
                 f"Register-ScheduledTask -TaskName '{unacct}' -Action $a -Trigger $t -Force | Out-Null")
    ctx.check(rc == 0, f"直接登記未記帳工作失敗 rc={rc} {out[:200]}")
    write_ready(spec, sid=sb.sid, root=str(sb.root), home=str(sb.home), rv_task=sched.rv_name(rv_name),
                park_task=armed.label, unaccounted_task=unacct, sleeper_pid=sleeper.pid,
                run_id=leases.current_run_id(), slug_dir=str(projects_dir() / slug_of(sb.root)))
    hold(spec)


@case("RV-SE-NOOP", "sideeffect_selftest", refs=("E2E-SE-02", "E2E-SE-18"))
def rv_se_noop(ctx: CaseContext) -> None:  # noqa: ARG001
    """什麼都不做就 PASS：只為了讓 `realverify run` 的開頭重放／發現式掃描／拒跑判決被執行並可觀察。"""


@case("RV-SE-LEAK", "sideeffect_selftest", refs=("E2E-SE-13",))
def rv_se_leak(ctx: CaseContext) -> None:
    """刻意外洩探針（E2E-SE-13）：繞過環境圍籬在**真** `~/.autosdd/handoff/<沙盒 sid>.probe` 寫檔，並以
    `Register-ScheduledTask` 建一支 Action 含沙盒根的工作且不記帳。runner 的每案快照必須抓到兩項而判 fail。
    父案例收尾刪探針檔、`sweep` 撤該工作。"""
    spec = load_spec()
    sb, _exe = new_box(ctx, tools=False)
    probe = real_autosdd("handoff") / f"{sb.sid}.probe"
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text("rv sideeffect leak probe\n", encoding="utf-8", newline="\n")
    task = f"AutoSDD_RVleak_{sb.sid[:8]}"
    rc, out = ps(f"$a = New-ScheduledTaskAction -Execute '{ACTION_PY}' -Argument '-c \"pass\" \"{sb.root}\"'; "
                 f"$t = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(90)); "
                 f"Register-ScheduledTask -TaskName '{task}' -Action $a -Trigger $t -Force | Out-Null")
    ctx.check(rc == 0, f"登記外洩探針工作失敗 rc={rc} {out[:200]}")
    write_ready(spec, sid=sb.sid, root=str(sb.root), home=str(sb.home), probe=str(probe), task=task, run_id=leases.current_run_id())


@case("RV-SE-LOCK", "sideeffect_selftest", refs=("E2E-SE-18",))
def rv_se_lock(ctx: CaseContext) -> None:
    """拒跑出口的受害者（E2E-SE-18）：建沙盒 X（帳）、記一列 `process`（睡眠行程 P1：命令列**不含**沙盒 sid
    與根、cwd 在 X 根內使 rmtree 失敗）；寫 ready 後睡眠等被殺。殺掉本行程後，X 根與 P1 撤不掉（驗不到身分
    ⇒ `unverified`），下一次 `run` 開頭應拒跑。"""
    spec = load_spec()
    sb, _exe = new_box(ctx, tools=False)
    p1 = subprocess.Popen([PY, "-c", "import time; time.sleep(3600)"], cwd=str(sb.root), creationflags=NOWIN)  # noqa: S603
    leases.track_process(["rv-se-lock-no-such-key"], pid=p1.pid)  # 命令列不含這個 key ⇒ 撤銷時驗不到身分 ⇒ unverified
    write_ready(spec, sid=sb.sid, root=str(sb.root), home=str(sb.home), p1_pid=p1.pid, run_id=leases.current_run_id())
    hold(spec)

