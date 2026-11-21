"""驅動器真機 E2E 探針（R217 A2；TCS E2E-WP-02／03／47／56 的載具入口，A6 包成 RealVerify 案例）。

不碰任何非沙盒排程：沙盒根在 repo 外、排程名一律 `AutoSDD_OpenItemSbx_<沙盒 8 碼>_`、結束必清並
斷言 0 殘留。流程（真 schtasks、真 `pythonw` 觸發的 `run-driver`、真 `--pace`）：
  1. 沙盒 OIR 三列 observe（A 必過、B 必敗、C 同時到點）；`openitems drive` 各掛一次性排程，
     **獨立**以排程器回讀 NextRunTime，必須非空且等於 `drive` 事件憑證（E2E-WP-02）。
  2. 等排程真的觸發：`start` 事件、每窗名額（A、B 拿到，C 因 `max_runs_per_window`＝2 而
     deferred window_cap）、A 關閉且自刪排程、B `attempt(fail)` 並重排新 drive（E2E-WP-03／47）。
     若當下 `--pace` 本身在收斂帶以上，三列應全 `deferred(quota)` 且重排——也是正確行為。
  3. 收尾：撤銷全部沙盒前綴排程、刪沙盒，現查殘留數。
末行 `OPENITEMS_DRIVE_E2E=pass|fail checks=<n> failed=<m>`；rc 0／1；非 Windows rc 2（不算綠）。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[1]
_REPO = _TOOLS.parent
sys.path.insert(0, str(_TOOLS))
sys.path.insert(0, str(_TOOLS / "lib"))

import _stdio_utf8  # noqa: E402, F401
from lib.openitems import ledger as oi_ledger  # noqa: E402
from lib.openitems import params as oi_params  # noqa: E402
from lib.openitems import schedcache, throttle  # noqa: E402
from lib.openitems.fold import fold  # noqa: E402

SOURCE = "docs/03_testing/contracts/TCS-WorkProgress-20261119.md:277"
WAIT_SECONDS = 420
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
SPECS = {"A": "regex:HELLO", "B": "regex:NEVER-MATCHES", "C": "regex:HELLO"}


class Report:
    def __init__(self) -> None:
        self.checks = 0
        self.failed: list[str] = []
        self.skipped: list[str] = []

    def check(self, ok: bool, what: str) -> None:
        self.checks += 1
        print(f"[{'PASS' if ok else 'FAIL'}] {what}", flush=True)
        if not ok:
            self.failed.append(what)


def cli(sandbox: Path, *args: str) -> subprocess.CompletedProcess:
    argv = [sys.executable, str(_TOOLS / "openitems.py"), "--root", str(sandbox),
            "--trace-dir", str(sandbox / "_trace"), *args]
    return subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=180, check=False, creationflags=NO_WINDOW)


def independent_next_run(task: str) -> str:
    """不經驅動器自己的後端：直接問排程器（憑證是 NextRunTime 這個值，不是 rc）。"""
    planner = schedcache.planner()
    proc = planner.run_powershell(planner._EVIDENCE_TEMPLATE.format(task=task) + "\n")
    return planner.next_run_time(proc.stdout or "")


def task_exists(task: str) -> bool:
    proc = schedcache.planner().run_powershell(
        f"if (Get-ScheduledTask -TaskName '{task}' -ErrorAction SilentlyContinue) "
        "{ 'YES' } else { 'NO' }\n")
    return "YES" in (proc.stdout or "")


def tasks_with(prefix: str) -> dict[str, str]:
    return schedcache.WindowsBackend().list_tasks(prefix) or {}


def events(sandbox: Path) -> list[dict]:
    return oi_ledger.read_events(oi_params.ledger_path(sandbox))[0]


def make_sandbox(prefix: str) -> tuple[Path, dict]:
    sandbox = Path(tempfile.mkdtemp(prefix="oi_e2e_"))
    dest = sandbox / oi_params.PARAMS_REL
    dest.parent.mkdir(parents=True)
    shutil.copyfile(_REPO / oi_params.PARAMS_REL, dest)
    cfg = json.loads(dest.read_text(encoding="utf-8"))
    cfg.update(task_prefix=prefix, stagger_minutes=0, busy_backoff_minutes=1,
               retry_backoff_minutes=3, max_runs_per_window=2)
    dest.write_text(json.dumps(cfg), encoding="utf-8")
    return sandbox, oi_params.load(sandbox)


def open_and_drive(sandbox: Path, rep: Report, now: datetime) -> tuple[dict, dict]:
    ids: dict[str, str] = {}
    drives: dict[str, dict] = {}
    due = (now - timedelta(minutes=1)).isoformat(timespec="seconds")
    for key, rule in SPECS.items():
        check = json.dumps({"argv": ["python", "-c", "print('HELLO')"], "pass": rule})
        out = cli(sandbox, "open", "--title", f"e2e-{key}", "--source", SOURCE, "--scope", "r217",
                  "--kind", "observe", "--check", check, "--due", due, "--by", "human")
        ids[key] = out.stdout.split()[-1] if out.returncode == 0 else ""
        rep.check(out.returncode == 0 and ids[key].startswith("OI-"), f"open {key} → {ids[key]}")
    for key, item_id in ids.items():
        out = cli(sandbox, "drive", item_id)
        tail = out.stdout.strip().splitlines()[-1:]
        rep.check(out.returncode == 0 and "OPENITEMS_DRIVE=ok" in out.stdout,
                  f"drive {key} rc={out.returncode} {tail}")
        ev = next((e for e in events(sandbox) if e["ev"] == "drive" and e["id"] == item_id), {})
        drives[key] = ev
        if ev:
            live = independent_next_run(ev["task"])
            rep.check(bool(live) and live == ev["credential"],
                      f"{key} 獨立回讀 NextRunTime={live!r} 等於 drive 憑證 {ev['credential']!r}")
    return ids, drives


def wait_for_attempts(sandbox: Path) -> None:
    deadline = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < deadline:
        if sum(1 for e in events(sandbox) if e["ev"] == "attempt") >= len(SPECS):
            time.sleep(20)  # 讓重排與自刪收尾
            return
        time.sleep(10)


def assert_outcomes(sandbox: Path, params: dict, rep: Report, ids: dict, drives: dict,
                    quota_hot: bool) -> None:
    evs = events(sandbox)
    folded = fold(evs, params, datetime.now().astimezone()).items
    by_id = {k: [e for e in evs if e["id"] == i] for k, i in ids.items()}
    for key in ids:
        rep.check(any(e["ev"] == "start" for e in by_id[key]), f"{key} 觸發後有 start 事件")
    first = {k: next((e for e in by_id[k] if e["ev"] == "attempt"), {}) for k in ids}
    reasons = {k: first[k].get("reason") for k in ids}
    results = {k: first[k].get("result") for k in ids}
    print(f"attempt 結果={results} 原因={reasons}")
    quota_hot = quota_hot or "quota" in reasons.values()  # 額度帶會在等待期間移動，以真實結果為準
    if quota_hot:
        ok = all(r in ("quota", "busy", "window_cap") for r in reasons.values())
        rep.check(ok, f"額度收斂帶：每列皆 deferred（quota／busy／window_cap）{reasons}")
    else:
        rep.check(folded[ids["A"]]["state"] == "closed", "A 通過並關閉")
        rep.check(results["B"] == "fail", "B 判 fail")
        rep.check(sorted(r for r in reasons.values() if r) == ["window_cap"],
                  "第三列因 max_runs_per_window＝2 deferred(window_cap)")
        runs_file = sandbox / "_trace" / "openitems" / "window_runs.jsonl"
        runs = runs_file.read_text(encoding="utf-8").splitlines()
        rep.check(len(runs) == 2, f"每窗只真跑 2 次（window_runs={len(runs)}）")
        rep.check(not task_exists(drives["A"].get("task", "")), "A 的一次性排程用完即刪")
    for key in (("A", "B", "C") if quota_hot else ("B", "C")):
        last = [e for e in by_id[key] if e["ev"] == "drive"][-1]
        if folded[ids[key]]["state"] == "driven":
            fresh = last["task"] != drives[key]["task"]
            rep.check(fresh and bool(independent_next_run(last["task"])),
                      f"{key} 已重排新 drive 且 NextRunTime 非空（{last['task']}）")
    lock = sandbox / "_trace" / "openitems" / "driver.lock"
    rep.check(not lock.exists(), "driver.lock 已釋放")


def direct_pass_path(sandbox: Path, params: dict, rep: Report) -> None:
    """真行程直跑一次（不等排程觸發）：pass、close、自刪排程。額度帶不是我們能放寬的
    （`AUTOSDD_QUOTA_PACE_BURST_PP` 等只准調小），當下額度帶偏高時誠實標 SKIP、不算 PASS。"""
    hot = throttle.read_pace(datetime.now().astimezone()).deferral()
    if hot:
        print(f"[SKIP] D 的 pass 路徑：當下額度帶 {hot}，驅動器依設計讓出（待額度空檔重跑）")
        rep.skipped.append("pass-path")
        return
    # 前三列已排隊（FIFO 的 O 項會擋住較新的 D）：沙盒名額放大，單獨驗 pass 路徑
    cfg_path = sandbox / oi_params.PARAMS_REL
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg["max_runs_per_window"] = 10
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    check = json.dumps({"argv": ["python", "-c", "print('HELLO')"], "pass": "regex:HELLO"})
    due = (datetime.now().astimezone() - timedelta(minutes=1)).isoformat(timespec="seconds")
    out = cli(sandbox, "open", "--title", "e2e-D", "--source", SOURCE, "--scope", "r217",
              "--kind", "observe", "--check", check, "--due", due, "--by", "human")
    item_id = out.stdout.split()[-1]
    cli(sandbox, "drive", item_id)
    ev = next(e for e in events(sandbox) if e["ev"] == "drive" and e["id"] == item_id)
    argv = [sys.executable, str(_TOOLS / "openitems.py"), "--root", str(sandbox), "--trace-dir",
            str(sandbox / "_trace"), "run-driver", item_id, "--task", ev["task"]]
    proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=300, check=False, creationflags=NO_WINDOW)
    last = proc.stdout.strip().splitlines()[-1:]
    rep.check(proc.returncode == 0 and "OPENITEMS_DRIVER=pass" in proc.stdout, f"D 真跑 {last}")
    state = fold(events(sandbox), params, datetime.now().astimezone()).items[item_id]["state"]
    rep.check(state == "closed", f"D 關閉（state={state}）")
    rep.check(not task_exists(ev["task"]), "D 的一次性排程用完即刪")


def main() -> int:
    if not sys.platform.startswith("win"):
        print("OPENITEMS_DRIVE_E2E=env-missing（真 schtasks 只在 Windows 成立）")
        return 2
    rep = Report()
    prefix = f"AutoSDD_OpenItemSbx_{uuid.uuid4().hex[:8]}_"
    sandbox, params = make_sandbox(prefix)
    real_before = sorted(tasks_with("AutoSDD_OpenItem_"))
    try:
        now = datetime.now().astimezone()
        pace = throttle.read_pace(now)
        print(f"沙盒={sandbox} 前綴={prefix} pace_deferral={pace.deferral() or '無（可執行）'}")
        ids, drives = open_and_drive(sandbox, rep, now)
        lst = cli(sandbox, "list", "--verify")
        rep.check(lst.returncode == 0 and "undriven=0" in lst.stdout,
                  f"list --verify：{lst.stdout.strip().splitlines()[-1:]}")
        wait_for_attempts(sandbox)
        assert_outcomes(sandbox, params, rep, ids, drives, bool(pace.deferral()))
        direct_pass_path(sandbox, params, rep)
        rep.check(sorted(tasks_with("AutoSDD_OpenItem_")) == real_before,
                  "真 AutoSDD_OpenItem_* 排程未被碰")
    finally:
        backend = schedcache.WindowsBackend()
        for name in list(tasks_with(prefix)):
            backend.unregister(name)
        rep.check(not tasks_with(prefix), f"收尾：前綴 {prefix} 殘留排程為 0")
        shutil.rmtree(sandbox, ignore_errors=True)
        rep.check(not sandbox.exists(), "收尾：沙盒目錄已刪")
    verdict = "pass" if not rep.failed else "fail"
    print(f"OPENITEMS_DRIVE_E2E={verdict} checks={rep.checks} failed={len(rep.failed)} "
          f"skipped={rep.skipped}")
    return 0 if verdict == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
