# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
# ruff: noqa: E501
"""control 家族 A：RV-CTL30／32／33／35（WP-SW，TCS-Control §8.4 E2E-CTL-30／32／33／35）。

載具：真 git 的真 `handoff --build`（沙盒倉庫）、真母體量測與真哨兵重放（只讀真逐字稿，不落任何狀態）、
接線型真跑（LOC／落點／登記鎖）。排程類與逐字稿重放類案例在 `control_sched.py`。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ..sandbox import REPO
from . import CaseContext, case
from .sessionctl_park import PY, ctl, install_tools, park_cleanup, run

OWNER = "406454ea-91fc-4481-9c11-b28ed7d9e95f"
_HOME_PROJECTS = Path.home() / ".claude" / "projects" / "D--CursorProject-AISDCL-Agent"
_NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _git(root: Path, *args: str) -> str:
    r = subprocess.run(["git", "-c", "user.name=rv", "-c", "user.email=rv@example.invalid", "-C", str(root), *args],  # noqa: S603, S607
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       stdin=subprocess.DEVNULL, creationflags=_NOWIN)
    if r.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} rc={r.returncode} {r.stderr[:200]}")
    return r.stdout.strip()


def _env() -> dict:
    import os
    e = dict(os.environ)
    e["PYTHONUTF8"] = "1"
    e["PYTHONIOENCODING"] = "utf-8"
    return e


@case("RV-CTL30", "control", refs=("E2E-CTL-30", "REQ-CTL-54", "MU-CTL-60"))
def rv_ctl30(ctx: CaseContext) -> None:
    """真 git：`git stash create` ＋ `git tag <sid8>-…-halfwork`（目標不在 HEAD）與 HEAD 上的 `*-wip-preserved`，
    真跑 `handoff --build`：第 3 欄含 worktree list、第 4 欄兩種標籤並存（halfwork 附 SHA 前 12 碼與「不在 HEAD」）。"""
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    with park_cleanup(sb):
        with (sb.root / "tools" / "sessionctl.py").open("a", encoding="utf-8", newline="\n") as fh:
            fh.write("\n# rv halfwork\n")  # 追蹤檔改動：stash create 的目標
        sha = _git(sb.root, "stash", "create")
        ctx.check(bool(sha), "git stash create 沒回 commit（工作樹沒有可保全的改動）")
        _git(sb.root, "tag", f"{OWNER[:8]}-20261126-flk5-halfwork", sha)
        _git(sb.root, "restore", "tools/sessionctl.py")
        _git(sb.root, "tag", f"{OWNER[:8]}-20261128-wip-preserved", "HEAD")
        r = ctl(sb, "handoff", "--build", "--session-id", OWNER)
        ctx.check(r.returncode == 0, f"handoff --build rc={r.returncode}\n{r.stdout[-300:]}{r.stderr[-300:]}")
        pkg = Path(r.stdout.strip().splitlines()[-1])
        ctx.check(pkg.is_file(), f"交接包不存在：{pkg}")
        text = pkg.read_text(encoding="utf-8")
        ctx.check("git worktree list" in text, "第 3 欄沒有 `git worktree list` 輸出")
        ctx.check(f"{OWNER[:8]}-20261126-flk5-halfwork → {sha[:12]}（不在 HEAD）" in text, f"第 4 欄缺 halfwork 附 SHA 與「不在 HEAD」：{text[:1200]}")
        ctx.check(f"{OWNER[:8]}-20261128-wip-preserved → " in text, "第 4 欄缺 wip-preserved 標籤")
        from lib.sessionctl import handoff_build  # noqa: PLC0415
        order = [text.find(h) for h in handoff_build.MECH_HEADINGS]
        ctx.check(len(order) == 13 and all(i >= 0 for i in order), f"13 欄標題缺漏：{order}")
        ctx.evidence(f"RV-CTL30 stash create {sha[:12]}；第 4 欄同列 halfwork（不在 HEAD）與 wip-preserved；機械層標題 {len(handoff_build.MECH_HEADINGS)} 欄全在")


@case("RV-CTL32", "control", refs=("E2E-CTL-32", "REQ-CTL-56", "MU-CTL-63"))
def rv_ctl32(ctx: CaseContext) -> None:
    """真母體量測（零 token、只讀真逐字稿；量測型不入閘）：M-W1 corrected 的 agent／shell 子集不變式與出聲字樣。"""
    sys.path.insert(0, str(REPO / "tools"))
    sys.path.insert(0, str(REPO / "tools" / "lib"))
    if not _HOME_PROJECTS.is_dir():
        from ..driver import EnvMissing
        raise EnvMissing(f"真逐字稿母體不存在：{_HOME_PROJECTS}")
    r = run([PY, str(REPO / "tools" / "probe" / "waste_census.py"), "--supervision-metrics", "--since-days", "14",
             "--base", str(_HOME_PROJECTS)], cwd=REPO, env=_env(), timeout=600)
    ctx.check(r.returncode == 0, f"waste_census rc={r.returncode}\n{r.stdout[-300:]}{r.stderr[-300:]}")
    line = next((x for x in r.stdout.splitlines() if "M-W1（修正" in x), "")
    ctx.check(bool(line), f"輸出沒有 M-W1（修正）列：{r.stdout[-400:]}")
    ctx.check("agent" in r.stdout or "shell" in r.stdout or ">30" in line, "M-W1 修正列缺 agent／shell／>30 判讀")
    # 不變式用函式層對同一母體重算（CLI 只印摘要列）：agent.n + shell.n == n；agent.gt_30min 並入帳
    from lib.wastecensus import supervision as sv  # noqa: PLC0415
    from lib.wastecensus import supervision_load as sl  # noqa: PLC0415
    got = sv.m_w1(sl.load_sessions(_HOME_PROJECTS, 14))
    ctx.check(got["agent"]["n"] + got["shell"]["n"] == got["n"], f"agent.n+shell.n≠n：{got}")
    ctx.check(got["agent"]["gt_30min"] <= got["agent"]["n"] and got["shell"]["gt_30min"] <= got["shell"]["n"], f"gt_30min 超過 n：{got}")
    ctx.evidence(f"RV-CTL32 真母體 n={got['n']} agent.n={got['agent']['n']} shell.n={got['shell']['n']} "
                 f"agent.gt_30min={got['agent']['gt_30min']}（量測型、母體會漂移，只斷言不變式）；CLI 列：{line.strip()[:120]}")


@case("RV-CTL33", "control", refs=("E2E-CTL-33", "REQ-CTL-57", "MU-CTL-64", "MU-CTL-65"))
def rv_ctl33(ctx: CaseContext) -> None:
    """真哨兵重放對真逐字稿（406454ea）：09:52 判 patrol（park 讓路）、10:22 as-of 標記為 cancelled 並與磁碟現值並列。"""
    base = [PY, str(REPO / "tools" / "probe" / "sentinel_decide_replay.py"), "--sid", OWNER, "--now"]
    if not (_HOME_PROJECTS / f"{OWNER}.jsonl").is_file():
        from ..driver import EnvMissing
        raise EnvMissing("406454ea 真逐字稿不在本機")
    r1 = run([*base, "2026-11-28T09:52:00+08:00"], cwd=REPO, env=_env(), timeout=180)
    r2 = run([*base, "2026-11-28T10:22:00+08:00"], cwd=REPO, env=_env(), timeout=180)
    for r in (r1, r2):
        ctx.check(r.returncode == 0, f"重放 rc={r.returncode}\n{r.stderr[-300:]}")
        ctx.check("不重現排程器 stdio 環境" in r.stdout, "標題缺「不重現排程器 stdio 環境」")
        ctx.check("舊判準 sentinel_decide" in r.stdout and "新判準 sentinel_decide" in r.stdout and "D3 單獨" in r.stdout, "既有三列缺漏")
    last1 = r1.stdout.strip().splitlines()[-1]
    ctx.check("patrol" in last1 and "park 排程待命" in last1 and "哨兵讓路" in last1, f"09:52 第四列應判 patrol 讓路：{last1}")
    t2 = r2.stdout
    ctx.check("park（as-of）=" in t2 and '"status": "cancelled"' in t2.split("park（as-of）=")[1].split("；")[0], f"10:22 as-of 標記應為 cancelled：{t2[-500:]}")
    ctx.check("park（磁碟現值）=" in t2, "10:22 缺磁碟現值（與 as-of 並列）")
    ctx.evidence(f"RV-CTL33 09:52⇒{last1[:80]}；10:22 as-of／磁碟並列；既有三列在（重放不落任何狀態＝無副作用可隔離）")


@case("RV-CTL35", "control", refs=("E2E-CTL-35", "REQ-CTL-59", "MU-CTL-69", "MU-CTL-70", "MU-CTL-71"))
def rv_ctl35(ctx: CaseContext) -> None:
    """接線型真跑：LOC 預算、realverify 登記齊全（RV-CTL25～35）、落點鎖、c1c2 鎖、engine-bridge 閉包相關測試。"""
    r = run([PY, str(REPO / "AutoClaude" / "tools" / "check_loc_budget.py"), "--json"], cwd=REPO, env=_env(), timeout=300)
    ctx.check(r.returncode == 0, f"check_loc_budget rc={r.returncode}\n{r.stdout[-300:]}")
    try:
        viol = json.loads(r.stdout).get("violations")
    except ValueError:
        viol = None
    ctx.check(viol in ([], None, 0), f"LOC violations：{viol}")
    cj = json.loads((REPO / "docs" / "06_quality" / "RealVerify_Protocol" / "cases.json").read_text(encoding="utf-8"))["cases"]
    from . import REGISTRY, discover  # noqa: PLC0415
    discover()
    want = [f"RV-CTL{n}" for n in range(25, 36)]
    ctx.check(all(w in cj for w in want), f"cases.json 缺登記：{[w for w in want if w not in cj]}")
    ctx.check(all(w in REGISTRY for w in want), f"cases/*.py 缺案例：{[w for w in want if w not in REGISTRY]}")
    for pattern in ("test_root_module_layout.py", "test_adr_xplat001_c1c2_lock.py", "test_sessionctl_crashguard.py"):
        u = run([PY, "-m", "unittest", "discover", "-s", "tools/tests", "-p", pattern], cwd=REPO, env=_env(), timeout=900)
        ctx.check(u.returncode == 0, f"{pattern} rc={u.returncode}\n{u.stderr[-400:]}")
    eb = [p.name for p in (REPO / "tools" / "tests").glob("test_*.py") if "si_repo_support" in p.read_text(encoding="utf-8", errors="replace")
          and "engine" in p.read_text(encoding="utf-8", errors="replace").lower()][:3]
    for name in eb:
        u = run([PY, "-m", "unittest", "discover", "-s", "tools/tests", "-p", name], cwd=REPO, env=_env(), timeout=900)
        ctx.check(u.returncode == 0, f"{name} rc={u.returncode}\n{u.stderr[-300:]}")
    ctx.evidence(f"RV-CTL35 LOC violations={viol}；RV-CTL25～35 登記齊全；落點鎖＋c1c2＋crashguard 綠；engine-bridge 相關測試 {eb}")
