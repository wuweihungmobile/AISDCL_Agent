"""S5 真行程 smoke（DES §5／TCS E2E-SE-02 的縮小版；**不算**正式 E2E，正式案例由 S6 落）。

真子行程（主人）建沙盒、啟動命令列含沙盒 sid 的睡眠行程、登記一支沙盒前綴排程；本程式 `taskkill /F`
殺主人（不帶 /T）後跑真 `tools/realverify.py sweep`：沙盒根、睡眠行程、排程都被撤，帳 `closed`，
第二次 sweep＝clean；同時一個**主人存活**的旁觀沙盒全程不被動（D-16）。全程只用沙盒前綴，結束時殘留 0。
"""  # noqa: E501

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "lib"))
import _stdio_utf8  # noqa: E402,F401  # stdout 強制 UTF-8（本檔印中文）
from lib.realverify import leases, sandbox, sched  # noqa: E402

PY = sys.executable
OWNER = r"""
import subprocess, sys, time
sys.path.insert(0, {tools!r}); sys.path.insert(0, {lib!r})
from datetime import datetime, timedelta
from lib.realverify import leases, sandbox
sb = sandbox.Sandbox.create(probe_hook=False)
sleeper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)", sb.sid])
leases.register_once({task!r}, (datetime.now() + timedelta(minutes=60)).isoformat(timespec="seconds"), "-c pass")
print("READY", sb.root, sleeper.pid, flush=True)
time.sleep(600)
"""  # noqa: E501


def sweep() -> str:
    return subprocess.run([PY, str(TOOLS / "realverify.py"), "sweep"], capture_output=True, text=True,  # noqa: E501
                          encoding="utf-8", errors="replace", timeout=240, check=False).stdout


def alive(pid: int) -> bool:
    if sys.platform != "win32":
        raise SystemExit("本 smoke 只在 Windows 跑（tasklist／taskkill）")
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False).stdout  # noqa: E501
    return str(pid) in out


def main() -> int:
    if sys.platform != "win32":
        print("本 smoke 只在 Windows 跑（tasklist／taskkill）；S5_SMOKE_VERDICT=skip")
        return 2
    results: list[tuple[str, bool, str]] = []
    task = f"AutoSDD_RV_s5smoke_{int(time.time()) % 100000}"
    bystander = sandbox.Sandbox.create(probe_hook=False)  # 主人＝本行程（存活）
    try:
        owner = subprocess.Popen([PY, "-c", OWNER.format(tools=str(TOOLS), lib=str(TOOLS / "lib"), task=task)],  # noqa: E501
                                 stdout=subprocess.PIPE, text=True,
                                 encoding="utf-8", errors="replace")
        line = owner.stdout.readline().split()
        root, sleeper = Path(line[1]), int(line[2])
        subprocess.run(["taskkill", "/F", "/PID", str(owner.pid)], capture_output=True, check=False)  # noqa: E501
        owner.wait(timeout=20)
        before = (root.exists(), alive(sleeper), sched.read_back(task) is not None)
        results.append(("kill 後三者皆在", before == (True, True, True), str(before)))
        out = sweep()
        after = (root.exists(), alive(sleeper), sched.read_back(task) is not None)
        results.append(("sweep 撤掉三者", after == (False, False, False), f"{after}｜{out.strip().splitlines()[-1]}"))  # noqa: E501
        results.append(("旁觀沙盒（主人存活）不動", bystander.root.exists(), str(bystander.root)))
        out2 = sweep()
        results.append(("第二次 sweep＝clean", out2.strip().splitlines()[-1] == "SWEEP_VERDICT=clean", out2.strip()))  # noqa: E501
    finally:
        bystander.cleanup()
        sched.remove(task)
        _ = (datetime, timedelta, tempfile)
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")
    left = [p for p in Path(tempfile.gettempdir()).glob("AutoSDD_RV_sbx_*") if str(p) == str(bystander.root)]  # noqa: E501
    print(f"殘留（本 smoke 的旁觀沙盒）={len(left)}｜排程 {sched.read_back(task)}｜帳 pending={leases.revoke_run()}")  # noqa: E501
    ok_all = all(r[1] for r in results) and not left
    print(f"S5_SMOKE_VERDICT={'pass' if ok_all else 'fail'}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
