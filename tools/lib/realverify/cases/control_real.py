# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
# ruff: noqa: E501
"""control 家族 C：RV-CTL26／27／28／29／31／34（WP-SW 真排程／真行程／真逐字稿案例；TCS-Control §8.4）。

沿用 `control_sched` 的工具副本沙盒與 pythonw 載具。排程器起的 job 其居所只靠 `--job-env` 帶進沙盒，
**`TEMP`／`TMP` 不在允許表**——要讓排程器真的起行程、又不碰真 `%TEMP%\\AUTOSDD_ATTENTION.md`，案例把沙盒哨兵
的 Action 改包成「沙盒內 .ps1：先設沙盒 TEMP，再 `Start-Process -Wait -PassThru` 原 pythonw、原樣轉出 exit code」
（`wrap_fire`）：行程仍是 pythonw（無 std handle）、排程器自報的 `LastTaskResult`／`LastRunTime`／`NextRunTime` 是真值。
所有排程名一律帶完整沙盒 sid，收尾經 `park_cleanup`／`leases.revoke_sched_like` 精確拆除；真實
`AutoSDD_Sentinel_*`（406454ea／4290bf58 殘骸）絕不碰，案例前後各取一次清單逐字比對。
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

from lib import platform_utils, sandbox_scope

from .. import leases
from ..driver import EnvMissing
from ..sandbox import Sandbox, real_autosdd
from . import CaseContext, case
from .control_sched import (
    run_nostd,
    sandbox_tick_argv,
    trace_events,
    write_old_account_world,
)
from .sentinel import _env, arm, grant_default, task_name
from .sessionctl_park import (
    PY,
    ctl,
    get_task,
    install_tools,
    make_package,
    park_cleanup,
    ps,
    remove_tasks_like,
    seed_session,
    wait_until,
)

OWNER = "406454ea-91fc-4481-9c11-b28ed7d9e95f"
OLD_ACCT, NEW_ACCT = "eaf5241f6fe2", "34cd3507237f"
_PROJECTS = platform_utils.claude_home() / "projects" / "D--CursorProject-AISDCL-Agent"
_REAL_TRACE = real_autosdd("traces", "autosdd_session_switch.jsonl")


def _q(text: str) -> str:
    return "'" + str(text).replace("'", "''") + "'"


def _norm(sb: Sandbox) -> Path:
    t = sb.root / "tmp"
    t.mkdir(exist_ok=True)
    return t


# ───────────────────────────────────────────────────────────── 排程器自報與真實清單
def task_info(name: str) -> dict | None:
    rc, out = ps(
        f"$t = Get-ScheduledTask -TaskName {_q(name)} -ErrorAction SilentlyContinue; if (-not $t) {{ exit 0 }}; "
        "$i = $t | Get-ScheduledTaskInfo; "
        "[pscustomobject]@{state=[string]$t.State; last_result=[int64]$i.LastTaskResult; "
        "last_run=if($i.LastRunTime){$i.LastRunTime.ToString('o')}else{''}; "
        "next_run=if($i.NextRunTime){$i.NextRunTime.ToString('o')}else{''}} | ConvertTo-Json -Compress")
    if rc != 0 or not out.startswith("{"):
        return None
    d = json.loads(out)
    d["last_run"] = "" if d["last_run"][:4] < "2000" else d["last_run"]
    d["next_run"] = "" if d["next_run"][:4] < "2000" else d["next_run"]
    return d


def real_sentinels(sb: Sandbox, *, with_next: bool = False) -> list[str]:
    """真實 `AutoSDD_Sentinel_*`（排除帶本沙盒 sid 者）清單，排序後逐列。預設列＝名稱｜活著或已死（NextRunTime 非空與否）：
    活著的真哨兵 NextRunTime 本來就每 15 分鐘前進（主控本場哨兵一直在巡邏），逐字比對 NextRunTime 會被它的正常巡邏誤判；
    殘骸（NextRunTime 空）被拆或被改會讓這一列變——那才是本案要守的性質。`with_next=True` 才列 NextRunTime|LastTaskResult 原值。"""
    rc, out = ps("Get-ScheduledTask | Where-Object TaskName -like 'AutoSDD_Sentinel_*' | ForEach-Object { $i = $_ | Get-ScheduledTaskInfo; "
                 "\"$($_.TaskName)|$($i.NextRunTime)|$($i.LastTaskResult)\" }")
    rows = sorted(x.strip() for x in out.splitlines() if x.strip() and sb.sid not in x) if rc == 0 else []
    return rows if with_next else [f"{r.split('|')[0]}|{'live' if r.split('|')[1] else 'dead'}" for r in rows]


def wrap_fire(ctx: CaseContext, sb: Sandbox, name: str, delay_s: int = 40, *, crash_exit: int | None = None) -> None:
    """把沙盒哨兵排程改成「沙盒 .ps1 包一層（先設沙盒 TEMP，`Start-Process -Wait -PassThru` 原 Action，轉出 exit code）」
    並把觸發改成 now+delay 的單次觸發；`crash_exit` 給定 ⇒ 改跑 `exit <N>`（造「排程器自己跑完、結果非 0、不重排」的殘骸）。"""
    ctx.check(name.startswith("AutoSDD_Sentinel_") and sb.sid in name, f"拒絕改寫非沙盒排程：{name}")
    t = get_task(name)
    ctx.check(t is not None, f"排程 {name} 不存在，無從改寫")
    tmp = _norm(sb)
    ps1 = tmp / f"fire_{re.sub(r'[^A-Za-z0-9]', '_', name)[-24:]}.ps1"
    if crash_exit is None:
        body = (f"$env:TEMP = {_q(tmp)}; $env:TMP = {_q(tmp)}\n"
                f"$p = Start-Process -FilePath {_q(t['execute'])} -ArgumentList {_q(t['arguments'])} "
                f"-WorkingDirectory {_q(t['workdir'] or str(sb.root))} -Wait -PassThru\nexit $p.ExitCode\n")
    else:
        body = f"exit {crash_exit}\n"
    ps1.write_text(body, encoding="utf-8", newline="\r\n")
    register_once(ctx, name, "powershell.exe", f'-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{ps1}"', delay_s, workdir=str(sb.root))


def register_once(ctx: CaseContext, name: str, exe: str, args: str, delay_s: float, *, workdir: str = "") -> None:
    """以 `Register-ScheduledTask -Force` 整支重登沙盒名稱任務（Interactive、單次觸發 now+delay、與 planner 同四項設定）。
    不用 `Set-ScheduledTask`：planner 登記的任務 XML 對它回「工作 XML 遺失必要的屬性」。"""
    ctx.check(name.startswith("AutoSDD_Sentinel_") and "-" in name[17:], f"拒絕改寫非沙盒排程：{name}")
    wd = f" -WorkingDirectory {_q(workdir)}" if workdir else ""
    rc, out = ps(
        f"$a = New-ScheduledTaskAction -Execute {_q(exe)} -Argument {_q(args)}{wd}; "
        f"$t = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddSeconds({delay_s:.0f})); "
        "$p = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive; "
        "$s = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries; "  # no-window-ok: 載具由呼叫端傳入、只准沙盒名稱任務（上方 ctx.check 擋）；呼叫端皆帶 -WindowStyle Hidden 或轉原 pythonw Action（判準窗取 4 行，註解須在窗末行）
        f"try {{ Register-ScheduledTask -TaskName {_q(name)} -Action $a -Trigger $t -Principal $p -Settings $s -Force -ErrorAction Stop | Out-Null }} "
        "catch { Write-Output ('ERR: ' + $_.Exception.Message); exit 1 }", 90)
    ctx.check(rc == 0, f"Register-ScheduledTask 失敗 rc={rc}：{out[-300:]}")

def wait_ran(name: str, before: str, timeout_s: float = 240) -> dict:
    """等排程器真的跑過（`last_run` 變新）且不在 Running；回排程器自報值。"""
    def _done():
        i = task_info(name)
        return i if i and i["last_run"] and i["last_run"] != before and i["state"] != "Running" else None
    got = wait_until(_done, timeout_s, 5.0)
    if not got:
        raise AssertionError(f"排程器 {timeout_s:.0f}s 內沒有跑過 {name}：{task_info(name)}")
    time.sleep(4)  # 沉澱：LastRunTime 在起行程時就更新，行程尾端的痕跡／重排還在寫
    for _ in range(30):  # 直到 State 非 Running 且自報值連續兩次相同
        again = task_info(name)
        if again and again["state"] != "Running" and again == got:
            return again
        got = again or got
        time.sleep(4)
    return got


def set_streak(plan: Path, n: int) -> None:
    """任務書狀態塊是檔案夾具（不是程式測試鉤）：把 `crash_streak` 預置成 n。"""
    text = plan.read_text(encoding="utf-8")
    b, e = text.index("<!-- AUTOSDD-RELAY-BEGIN -->"), text.index("<!-- AUTOSDD-RELAY-END -->")
    block = text[b:e]
    lo, hi = block.index("{"), block.rindex("}") + 1
    state = json.loads(block[lo:hi])
    state["crash_streak"] = n
    plan.write_text(text[:b] + block[:lo] + json.dumps(state, ensure_ascii=False, indent=2) + block[hi:] + text[e:], encoding="utf-8", newline="\n")


def streak_of(plan: Path) -> int:
    text = plan.read_text(encoding="utf-8")
    m = re.search(r'"crash_streak":\s*(\d+)', text)
    return int(m.group(1)) if m else 0


def seed_crash_world(sb: Sandbox) -> None:
    """真壞輸入：`acct_probe.json` 合法 JSON 但 `voiced` 是整數 ⇒ `acctswitch.reconcile` 的 `pair not in said` 拋 TypeError
    （搭配舊帳號 halt 標記走到作廢分支）。"""
    write_old_account_world(sb)
    (sb.home / "traces" / "acct_probe.json").write_text(json.dumps({"voiced": 5}), encoding="utf-8", newline="\n")


def regrant(sb: Sandbox, minutes: int) -> None:
    now = datetime.now().astimezone()
    sandbox_scope.grant(sb.home, until=now + timedelta(minutes=minutes), now=now, max_minutes=minutes)


def _ctl_cleanup(sb: Sandbox) -> None:
    remove_tasks_like(f"AutoSDD_Sentinel_{sb.sid}-ctl")


# ───────────────────────────────────────────────────────────── E2E-CTL-26
@case("RV-CTL26", "control", refs=("E2E-CTL-26", "REQ-CTL-50", "MU-CTL-51", "MU-CTL-52", "MU-CTL-53", "MU-CTL-74"), sched=True, lease_minutes=45)
def rv_ctl26(ctx: CaseContext) -> None:
    """真壞輸入致真崩潰（無測試鉤），**由真排程器起行程**：P1 排程器自報 LastTaskResult≠0 且 NextRunTime 非空（已重排）、
    痕跡 sentinel_crashed、note 檔含例外型別；P2（預置 streak=2）＝第 3 次崩潰：NextRunTime 空、sentinel_crash_loop(rearmed=false)、
    handback 存在、status 出聲；之後正常 tick 成功 ⇒ sentinel_crash_cleared、status 該列消失。"""
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    grant_default(sb)
    env = _env(sb)
    before_real = real_sentinels(sb)
    with park_cleanup(sb):
        tp = seed_session(ctx, sb)
        plan = arm(ctx, sb, tp)
        regrant(sb, 40)
        name = task_name(sb)
        note = _norm(sb) / "AUTOSDD_ATTENTION.md"
        # ── P1
        seed_crash_world(sb)
        i0 = task_info(name)
        wrap_fire(ctx, sb, name, 40)
        p1 = wait_ran(name, i0["last_run"] if i0 else "")
        ctx.check(p1["last_result"] != 0, f"P1 排程器自報 LastTaskResult 應非 0：{p1}")
        ctx.check(bool(p1["next_run"]), f"P1 已重排：NextRunTime 應非空（崩潰護欄重排）：{p1}")
        crashed = [e for e in trace_events(sb) if e.get("event") == "sentinel_crashed"]
        ctx.check(len(crashed) == 1 and crashed[0].get("exc_type") == "TypeError" and crashed[0].get("streak") == 1
                  and "acctswitch" in str(crashed[0].get("file")) and crashed[0].get("tb"), f"P1 痕跡 sentinel_crashed 不合：{crashed}")
        ctx.check(note.is_file() and "TypeError" in note.read_text(encoding="utf-8", errors="replace"), f"P1 note 檔缺例外型別：{note}")
        ctx.check(not list((sb.home / "handback").glob("*sentinel_crash_loop*")), "P1 不該產 crash_loop handback")
        ctx.check(streak_of(plan) == 1, f"P1 後任務書 crash_streak 應為 1：{streak_of(plan)}")
        # ── P2：預置 streak=2，同樣壞輸入，排程器起行程＝第 3 次崩潰
        set_streak(plan, 2)
        seed_crash_world(sb)
        i1 = task_info(name)
        wrap_fire(ctx, sb, name, 40)
        p2 = wait_ran(name, i1["last_run"] if i1 else "")
        ctx.check(p2["last_result"] != 0 and p2["next_run"] == "", f"P2 排程器自報應 LastTaskResult≠0 且 NextRunTime 空（406454ea 殘骸同形）：{p2}")
        evs = trace_events(sb)
        loops = [e for e in evs if e.get("event") == "sentinel_crash_loop"]
        ctx.check(len(loops) == 1 and loops[0].get("rearmed") is False and loops[0].get("streak") == 3, f"P2 痕跡 sentinel_crash_loop 不合：{loops}")
        ctx.check(len([e for e in evs if e.get("event") == "sentinel_crashed"]) == 1, "P2 不該再有第二筆 sentinel_crashed")
        hb = list((sb.home / "handback").glob("*sentinel_crash_loop*"))
        ctx.check(len(hb) == 1, f"P2 handback 檔應恰 1 個：{hb}")
        ctx.check("TypeError" in note.read_text(encoding="utf-8", errors="replace"), "P2 note 檔缺例外型別")
        st = ctl(sb, "status")
        ctx.check("哨兵因連續崩潰停止：" in st.stdout and "TypeError" in st.stdout, f"status 沒出聲「哨兵因連續崩潰停止」：{st.stdout[-600:]}")
        # ── 還原正常輸入、讓一次 tick 成功 ⇒ cleared、status 該列消失
        (sb.home / "traces" / "acct_probe.json").unlink()
        rc_ok = run_nostd(sandbox_tick_argv(sb, plan), cwd=sb.root, env=env)
        cleared = [e for e in trace_events(sb) if e.get("event") == "sentinel_crash_cleared"]
        ctx.check(rc_ok == 0 and len(cleared) == 1, f"還原後 tick rc={rc_ok}，sentinel_crash_cleared={cleared}")
        st2 = ctl(sb, "status")
        ctx.check("哨兵因連續崩潰停止：" not in st2.stdout, "streak 歸零後 status 該列應消失")
        ctx.check(real_sentinels(sb) == before_real, f"真實 AutoSDD_Sentinel_* 清單前後不同：{before_real} → {real_sentinels(sb)}")
        ctx.evidence(f"RV-CTL26 P1 LastTaskResult={p1['last_result']} NextRunTime={p1['next_run']}；P2 LastTaskResult={p2['last_result']} NextRunTime='{p2['next_run']}'（空）；"
                     f"crash_loop streak=3 rearmed=False；handback={hb[0].name}；status 出聲；cleared 後該列消失；真實哨兵 {len(before_real)} 筆前後逐字不變。"
                     "偏離：佇列斷言＝排程器 job 環境只准帶關閉值的 AUTOSDD_DESKTOP_NOTIFY（空）⇒ 佇列不增（AT 驗「設變數＝恰增一筆」）；P3 park --fire 崩潰以 AT 覆蓋")


# ───────────────────────────────────────────────────────────── E2E-CTL-29
def _copy_ack_world(ctx: CaseContext, sb: Sandbox) -> tuple[Path, str]:
    """真實痕跡第 1385～1390 行與真實封存包複本（owner sid 全文取代為沙盒 sid）；回 (沙盒包路徑, acker sid)。"""
    ctx.check(_REAL_TRACE.is_file(), "真實痕跡檔不在本機")
    lines = _REAL_TRACE.read_text(encoding="utf-8", errors="replace").splitlines()[1384:1390]
    rows = [json.loads(x) for x in lines]
    acker = next((r["acker"] for r in rows if r.get("event") == "park_acked_cancel"), "")
    ctx.check(bool(acker) and any(r.get("event") == "account_switch" for r in rows), f"第 1385～1390 行形狀不符：{[r.get('event') for r in rows]}")
    out = sb.home / "traces" / "autosdd_session_switch.jsonl"
    with out.open("a", encoding="utf-8", newline="\n") as fh:
        for ln in lines:
            fh.write(ln.replace(OWNER, sb.sid) + "\n")
    src = real_autosdd("handoff", f"{OWNER}_20261126T154649Z")
    if not src.with_suffix(".md").is_file():
        raise EnvMissing(f"真實封存包不在本機：{src}.md")
    stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%SZ")
    dst = sb.home / "handoff" / f"{sb.sid}_{stamp}"
    dst.parent.mkdir(exist_ok=True)
    dst.with_suffix(".md").write_text(src.with_suffix(".md").read_text(encoding="utf-8").replace(OWNER, sb.sid), encoding="utf-8", newline="\n")
    dst.with_suffix(".sealed").write_text(src.with_suffix(".sealed").read_text(encoding="utf-8").strip() + "\n", encoding="utf-8", newline="\n")
    return dst.with_suffix(".md"), acker


@case("RV-CTL29", "control", refs=("E2E-CTL-29", "REQ-CTL-53", "MU-CTL-58", "MU-CTL-59", "MU-CTL-75"), sched=True, lease_minutes=45)
def rv_ctl29(ctx: CaseContext) -> None:
    """真 `handoff --ack`：真痕跡列＋真封存包複本＋真崩潰過的沙盒舊哨兵（排程器自報 LastTaskResult≠0、NextRunTime 非空，如實呈現）
    ＋真存活行程當舊視窗；摘要含封存戳之後的事件，原 ack 輸出逐字在前、rc 0。"""
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    grant_default(sb)
    before_real = real_sentinels(sb)
    with park_cleanup(sb):
        tp = seed_session(ctx, sb)
        arm(ctx, sb, tp)
        regrant(sb, 40)
        name = task_name(sb)
        seed_crash_world(sb)
        i0 = task_info(name)
        wrap_fire(ctx, sb, name, 40)
        old = wait_ran(name, i0["last_run"] if i0 else "")
        ctx.check(old["last_result"] != 0 and bool(old["next_run"]), f"舊哨兵應：LastTaskResult≠0 且已重排（NextRunTime 非空）：{old}")
        pkg, acker = _copy_ack_world(ctx, sb)
        alive = subprocess.Popen([PY, "-c", f"import time; time.sleep(600)  # old-window {sb.sid}"], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        sb.procs.append(alive)
        try:
            before = task_info(name)
            r = ctl(sb, "handoff", "--ack", str(pkg), extra={"CLAUDE_CODE_SESSION_ID": acker})
            ctx.check(r.returncode == 0, f"ack rc={r.returncode}\n{r.stdout[-400:]}{r.stderr[-400:]}")
            out = r.stdout
            ctx.check("封存後事件摘要" in out and out.index("封存後事件摘要") > 0, f"缺摘要或摘要在 ack 輸出之前：{out[:300]}")
            ctx.check("park_acked_cancel" in out and "account_switch" in out and OLD_ACCT in out and NEW_ACCT in out, f"摘要缺 park_acked_cancel／account_switch：{out[-900:]}")
            ctx.check(not any(x in out for x in ("watch_verdict", "forward_pass", "watch_quota_latched")), "他 sid（acker）的事件不該出現在 owner 摘要")
            line2 = next((x for x in out.splitlines() if x.startswith("② 舊哨兵排程")), "")
            for token in (f"State={before['state']}", f"LastTaskResult={before['last_result']}", f"NextRunTime={before['next_run']}"):
                ctx.check(token in line2, f"② 列缺排程器自報值 {token}：{line2}")
            ctx.check(before["last_run"][:19] in line2, f"② 列缺 LastRunTime：{line2} vs {before['last_run']}")
            ctx.check(alive.poll() is None, "舊視窗行程不該被動")
            win = next((x for x in out.splitlines() if x.startswith("③")), "")
            ctx.check("③ 舊視窗行程：" in win, f"缺 ③ 列：{out[-400:]}")
            ctx.check(real_sentinels(sb) == before_real, f"真實 AutoSDD_Sentinel_* 清單前後不同：{before_real} → {real_sentinels(sb)}")
            ctx.evidence(f"RV-CTL29 ack rc=0；摘要含 park_acked_cancel、account_switch {OLD_ACCT}→{NEW_ACCT}；② {line2.strip()[:200]}；③ {win.strip()[:80]}；真實哨兵 {len(before_real)} 筆逐字不變")
        finally:
            alive.kill()
        time.sleep(0)


# ───────────────────────────────────────────────────────────── E2E-CTL-34
@case("RV-CTL34", "control", refs=("E2E-CTL-34", "REQ-CTL-58", "MU-CTL-66", "MU-CTL-67", "MU-CTL-68", "MU-CTL-75"), sched=True, lease_minutes=60, long=True)
def rv_ctl34(ctx: CaseContext) -> None:
    """真排程殘骸 GC 兩階段：殘骸＝排程器自己跑完、結果非 0、不再重排的沙盒名稱任務（NextRunTime 空）；對照＝NextRunTime 非空的沙盒哨兵。
    階段 1（LastRunTime 距今 < 1500 s）ack ⇒ 不拆；階段 2（等過 1500 s）ack ⇒ 拆、對照不動、sentinel_gc 恰 1 筆、再 ack 冪等。
    State=Running 夾具真排程不可達（備援 AT-CTL-136 夾具 E）。"""
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    grant_default(sb)
    before_real = real_sentinels(sb)
    ctl_name = f"AutoSDD_Sentinel_{sb.sid}-ctl"
    with park_cleanup(sb):
        try:
            tp = seed_session(ctx, sb)
            arm(ctx, sb, tp)
            regrant(sb, 58)
            control = task_name(sb)
            ct = get_task(control)
            register_once(ctx, control, ct['execute'], ct['arguments'], 6 * 3600, workdir=ct['workdir'] or str(sb.root))
            ctl_info0 = task_info(control)
            ctx.check(bool(ctl_info0 and ctl_info0["next_run"]), f"對照哨兵應有 NextRunTime：{ctl_info0}")
            ctx.sched_track(ctl_name)
            ps1 = _norm(sb) / "ctl_exit1.ps1"
            ps1.write_text("exit 1\r\n", encoding="utf-8", newline="")
            register_once(ctx, ctl_name, 'powershell.exe', f'-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{ps1}"', 40)
            rem = wait_ran(ctl_name, "")
            ctx.check(rem["last_result"] != 0 and rem["next_run"] == "" and rem["state"] == "Ready", f"殘骸應為 NextRunTime 空／結果非 0／Ready：{rem}")
            pk1 = make_package(ctx, sb)
            time.sleep(1.2)
            pk2 = make_package(ctx, sb)
            acker = "11111111-2222-4333-8444-555555555555"
            sess = {"CLAUDE_CODE_SESSION_ID": acker}
            # ── 階段 1
            a1 = ctl(sb, "handoff", "--ack", str(pk1), extra=sess)
            ctx.check(a1.returncode == 0, f"階段 1 ack rc={a1.returncode} {a1.stderr[-300:]}")
            ctx.check(task_info(ctl_name) is not None and task_info(control) is not None, "階段 1 殘骸與對照皆應仍在")
            ctx.check(not [e for e in trace_events(sb) if e.get("event") == "sentinel_gc"], "階段 1 不該有 sentinel_gc")
            ph1_age = (datetime.now().astimezone() - datetime.fromisoformat(rem["last_run"])).total_seconds()
            ctx.check(ph1_age < 1500, f"階段 1 時 LastRunTime 應 < 1500 s：{ph1_age}")
            # ── 等到 LastRunTime＋1500 s 之後（sleep 分段）
            due = datetime.fromisoformat(rem["last_run"]) + timedelta(seconds=1500 + 20)
            while datetime.now().astimezone() < due:
                time.sleep(min(30.0, max(1.0, (due - datetime.now().astimezone()).total_seconds())))
            # ── 階段 2
            a2 = ctl(sb, "handoff", "--ack", str(pk2), extra=sess)
            ctx.check(a2.returncode == 0, f"階段 2 ack rc={a2.returncode} {a2.stderr[-300:]}")
            ctx.check(task_info(ctl_name) is None, f"階段 2 殘骸應已拆（0 殘留）：{task_info(ctl_name)}")
            ctl_info1 = task_info(control)
            ctx.check(ctl_info1 is not None and ctl_info1["next_run"] == ctl_info0["next_run"], f"對照哨兵 NextRunTime 應逐字不變：{ctl_info0} → {ctl_info1}")
            gcs = [e for e in trace_events(sb) if e.get("event") == "sentinel_gc"]
            ctx.check(len(gcs) == 1 and gcs[0].get("next_run") == "" and gcs[0].get("state") and gcs[0].get("last_run"), f"sentinel_gc 痕跡不合：{gcs}")
            a3 = ctl(sb, "handoff", "--ack", str(pk2), extra=sess)
            ctx.check(len([e for e in trace_events(sb) if e.get("event") == "sentinel_gc"]) == 1, f"冪等：再 ack 不該有第二筆 sentinel_gc（rc={a3.returncode}）")
            ctx.check(real_sentinels(sb) == before_real, f"真實 AutoSDD_Sentinel_* 清單前後不同：{before_real} → {real_sentinels(sb)}")
            ctx.evidence(f"RV-CTL34 殘骸 LastRunTime={rem['last_run']} LastTaskResult={rem['last_result']}；階段 1（{ph1_age:.0f}s）不拆；階段 2 拆（Get-ScheduledTask 0 殘留）；"
                         f"對照 NextRunTime {ctl_info0['next_run']} 不變；sentinel_gc 恰 1 筆；再 ack 冪等；真實哨兵 {len(before_real)} 筆逐字不變。"
                         "偏離：殘骸以「沙盒名稱、排程器自己跑完 exit 1、不重排」造（非 sentinel 崩潰迴圈），GC 判準只讀排程器自報欄位；State=Running 夾具依規格備援 AT-CTL-136")
        finally:
            leases.revoke_sched_like(ctl_name)
