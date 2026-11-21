"""realverify 排程租約帳的 E2E（副作用隔離工作包 S5；真 schtasks、真行程；**不算單元測試**）。

E2E-S5-01（代理被殺）：真子行程用 `leases.register_once` 登記沙盒前綴排程後，**不經任何
finally** 就 `os._exit`（模擬被額度切斷）；排程仍在、XML 含 EndBoundary＋
DeleteExpiredTaskAfter；父行程 `replay` 依帳判主人已死 ⇒ 排程被撤並回讀確認不存在。
E2E-S5-02（主人存活不撤）：本行程自己登記的排程，`replay` 不動它；`revoke_run` 才撤。
E2E-S5-03（發現式掃描）：未登記的 `AutoSDD_RV_` 殘留被 `discover_sweep` 撤；帳上存活主人的不動。
全程帳目錄用暫存目錄（`LEASE_DIR` 換掉），不碰真 `~/.autosdd`；排程名 `AutoSDD_RV_leasee2e_*`、觸發
時刻在 2 小時後且 Action 為 `pythonw -c pass`，永不干擾真工作。結尾回讀確認殘留 0。
末行 `LEASES_E2E_VERDICT=pass|fail`；rc 0／1。
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

_TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_TOOLS))

from lib.realverify import leases, sched  # noqa: E402

CHILD = """
import os, sys
sys.path.insert(0, {tools!r})
from pathlib import Path
from lib.realverify import leases
leases.LEASE_DIR = Path({lease_dir!r})
leases.register_once({name!r}, {at!r}, "-c pass")
os._exit(0)  # 被殺：沒有 finally、沒有收尾
"""


def _xml(name: str) -> str:
    rc, out = sched._ps(f"(Export-ScheduledTask -TaskName '{name}')")  # noqa: SLF001
    return out if rc == 0 else ""


def main() -> int:
    results: list[tuple[str, bool, str]] = []
    tag = uuid.uuid4().hex[:8]
    names = {k: f"AutoSDD_RV_leasee2e_{k}_{tag}" for k in ("kill", "live", "stray")}
    fire = (datetime.now() + timedelta(hours=2)).replace(microsecond=0)
    at = fire.isoformat(timespec="seconds")
    lease_dir = Path(tempfile.mkdtemp(prefix="rv_leases_e2e_")) / "leases"
    with mock.patch.object(leases, "LEASE_DIR", lease_dir):
        try:
            # E2E-S5-01
            pr = subprocess.run([sys.executable, "-c", CHILD.format(
                tools=str(_TOOLS), lease_dir=str(lease_dir), name=names["kill"], at=at)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=120, check=False)
            xml = _xml(names["kill"])
            has_os_expiry = "EndBoundary" in xml and "DeleteExpiredTaskAfter" in xml
            results.append(("E2E-S5-01a 被殺的子行程留下排程且 XML 帶 OS 自毀設定",
                            pr.returncode == 0 and has_os_expiry,
                            f"child rc={pr.returncode} {pr.stderr[-200:]}"))
            stuck = leases.replay()
            gone_now = sched.read_back(names["kill"]) is None
            results.append(("E2E-S5-01b replay 依帳撤掉主人已死的排程（回讀不存在）",
                            not stuck and gone_now, f"stuck={stuck}"))
            # E2E-S5-02
            leases.register_once(names["live"], at, "-c pass")
            leases.replay()
            kept = sched.read_back(names["live"]) is not None
            results.append(("E2E-S5-02a 主人存活者 replay 不撤", kept, ""))
            left = leases.revoke_run()
            results.append(("E2E-S5-02b revoke_run 才撤",
                            not left and sched.read_back(names["live"]) is None, f"left={left}"))
            # E2E-S5-03
            sched.register_once(names["stray"], at, "-c pass")  # 繞過帳＝未登記殘留
            gone = leases.discover_sweep()
            results.append(("E2E-S5-03 未登記殘留被發現式掃描撤掉",
                            names["stray"] in gone and sched.read_back(names["stray"]) is None,
                            f"gone={gone}"))
        finally:
            for n in names.values():
                sched.remove(n)
            shutil.rmtree(lease_dir.parent, ignore_errors=True)
    residue = [n for n in names.values() if sched.read_back(n) is not None]
    results.append(("殘留 0", not residue, f"residue={residue}"))
    ok = True
    for title, passed, note in results:
        print(f"[{'PASS' if passed else 'FAIL'}] {title} {note if not passed else ''}")
        ok = ok and passed
    print(f"LEASES_E2E_VERDICT={'pass' if ok else 'fail'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
