# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""sideeffect 家族（五）：RV-SE09＝正式目標回歸（拋棄式「正式」repo＋假 claude）。

正式目標＝名稱不是 `AutoSDD_RV_sbx_`、沒有身分檔的 repo（L1 對它不介入）。本案例用 `%TEMP%\\AutoSDD_RVprod_<run_id>-<x>` 拋棄式 repo 裝入
tools，證明：正式目標的 park 登記**不帶** EndBoundary、通知／哨兵只准關閉值且不合法值不得讓正式登記失敗（D-20）、到點行為與修改前逐字
相同（RESUME 正常走到假 claude）。🔴 安全：這類 repo **沒有 L1 保護**，所以①前置先跑 `test_sessionctl_se_isolation`（任一紅 ⇒ ENV、不登記
任何排程）；②一律 `--claude <假>`；③(b) 登記後在 repo 根放一個未追蹤檔使任何 FRESH 嘗試被 `handoff._refusals` 在 runner 之前拒絕。
全部先登記 L2 帳列（repo、projects slug、行程）才動作，收尾由帳撤銷。
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
import uuid
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

from .. import fakeclaude, leases
from ..driver import EnvMissing
from ..sandbox import REPO, Sandbox, projects_dir, slug_of
from . import CaseContext, case
from .sessionctl_park import PY, get_task, install_tools, run
from .sideeffect_lib import (
    NOWIN,
    calls,
    events,
    flip_task_arg,
    iso_at,
    kills_runners,
    names,
    now,
    pick_resume_ctx,
    plain_env,
    synth_transcript,
    task_xml,
    wait_gone,
    watch_no_window,
)

_AUTO = {"AUTOSDD_SESSION_SWITCH_MODE": "auto"}
PARK_ATTEMPTS = 0  # 同 sideeffect_replay：QW Q3 同 commit 改 1


def _prod_box(ctx: CaseContext, tag: str, *, mode: str) -> SimpleNamespace:
    """拋棄式正式 repo：先登記帳列（repo、projects slug、行程）、後建；裝 tools、基線 commit、假 claude、合成逐字稿、交接包。"""
    repo = Path(tempfile.gettempdir()).resolve() / f"AutoSDD_RVprod_{leases.current_run_id()}-{tag}"
    sid = str(uuid.uuid4())
    leases.track_kind("temp_file", repo)
    leases.track_kind("transcript_dir", projects_dir() / slug_of(repo))
    leases.track_process([sid, str(repo)])
    repo.mkdir()
    for args in (["init", "-q"], ["config", "user.email", "rv@example.invalid"], ["config", "user.name", "realverify"]):
        subprocess.run(["git", *args], cwd=str(repo), check=True, capture_output=True, creationflags=NOWIN)  # noqa: S603,S607
    box = SimpleNamespace(root=repo, home=repo, sid=sid)
    install_tools(box)  # 複製 tools／hooks、寫 .git/info/exclude（含居所與替身樣式）、基線 commit
    proj = projects_dir() / slug_of(repo)
    exe = fakeclaude.build(repo)
    fakeclaude.configure(repo, mode, sleep=60, projdir=proj)
    return SimpleNamespace(root=repo, home=repo, sid=sid, exe=exe, proj=proj, mode=mode)


def _env(box: SimpleNamespace, extra: dict | None = None) -> dict:
    return Sandbox.env(SimpleNamespace(home=box.home), extra)  # 7 居所指向 repo 之下、通知空、哨兵 1（與沙盒同一函式）


def _prepare(ctx: CaseContext, box: SimpleNamespace, ctx_tokens: int) -> Path:
    synth_transcript(box, ctx_tokens=ctx_tokens, age_s=10_800)
    r = run([PY, str(box.root / "tools" / "sessionctl.py"), "handoff", "--build", "--session-id", box.sid], cwd=box.root, env=_env(box), timeout=180)
    ctx.check(r.returncode == 0, f"handoff --build rc={r.returncode} {r.stderr[-300:]}")
    pkg = Path(r.stdout.strip().splitlines()[-1])
    pkg.write_text(re.sub(r"TODO:[^\n]*", "realverify 正式目標替身，無實際工作。", pkg.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    dirty = subprocess.run(["git", "status", "--short"], cwd=str(box.root), capture_output=True, text=True, creationflags=NOWIN, check=False).stdout.strip()  # noqa: S603,S607
    ctx.check(not dirty, f"正式替身 repo 髒（D-23 同一輔助函式應使其乾淨）：{dirty[:200]}")
    return pkg


def _park(ctx: CaseContext, box: SimpleNamespace, pkg: Path, at, env_extra: dict) -> str:
    r = run([PY, str(box.root / "tools" / "sessionctl.py"), "park", "--session-id", box.sid, "--at", iso_at(at), "--why", "realverify SE09 正式目標替身",
             "--pkg", str(pkg), "--claude", str(box.exe)], cwd=box.root, env=_env(box, env_extra), timeout=180)
    ctx.check(r.returncode == 0, f"正式目標登記應成功 rc={r.returncode} stderr={r.stderr[-300:]} stdout={r.stdout[-200:]}")
    ctx.check(not r.stderr.strip().replace("\n", "") or "known_model_windows" in r.stderr, f"正式目標登記不該有 stderr：{r.stderr[-300:]}")
    marker = box.home / "traces" / "park" / f"{box.sid}.json"
    label = json.loads(marker.read_text(encoding="utf-8"))["jobs"][0]["label"]
    ctx.sched_track(label)
    return label


def _guard_unit_tests(ctx: CaseContext) -> None:
    """前置（r5，B-P3-1）：先跑 AT-SE-44 所在的 `test_sessionctl_se_isolation`；任一紅 ⇒ ENV（不登記任何排程）。"""
    r = subprocess.run([PY, "-m", "unittest", "discover", "-s", str(REPO / "tools" / "tests"), "-p", "test_sessionctl_se_isolation.py"],  # noqa: S603
                       cwd=str(REPO), env=plain_env(), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900, creationflags=NOWIN, check=False)
    if r.returncode != 0:
        raise EnvMissing(f"前置單元測試（含 AT-SE-44）紅，不在無 L1 保護的正式替身 repo 上登記排程：{(r.stdout + r.stderr)[-300:]}")
    ctx.evidence("前置 test_sessionctl_se_isolation 全綠（AT-SE-44 守住「每次 spawn 嘗試都帶 --claude」）")


@case("RV-SE09", "sideeffect", refs=("E2E-SE-09",), sched=True)
@kills_runners
def rv_se09(ctx: CaseContext) -> None:
    """(a) 模式 notify（以 auto 登記後把工作 argv 改成 notify）、登記行程哨兵關：序列 park_job_start→park_route→模式拒絕、假 claude 0 次。
    (b) 模式 auto、替身 resume_ok：RESUME 恰 1 次（argv 含 -r、cwd＝替身 repo）、park_resumed、park_attempt＝QW Q3 前 0 筆、無失敗鏈；
    任何 FRESH 嘗試必被前置拒絕（repo 根有未追蹤檔）。(c) 登記行程另設 `AUTOSDD_DESKTOP_NOTIFY=1` 與顯式空 `AUTOSDD_SENTINEL_OFF=`：登記 rc 0、
    Arguments 不含這兩鍵、無 stderr（D-20：正式目標不得因不合法值而失敗）。三者工作 XML **無** EndBoundary、無 `sideeffect_*`。"""
    _guard_unit_tests(ctx)
    resume_ctx, _why = pick_resume_ctx()
    at = (now() + timedelta(seconds=170) + timedelta(minutes=1)).replace(second=0, microsecond=0)
    a, b, c = (_prod_box(ctx, t, mode=m) for t, m in (("a", "resume_ok"), ("b", "resume_ok"), ("c", "resume_ok")))
    off = {"AUTOSDD_SENTINEL_OFF": "1"}
    pk_a, pk_b, pk_c = (_prepare(ctx, x, resume_ctx) for x in (a, b, c))
    la = _park(ctx, a, pk_a, at, {**_AUTO, **off})
    flip_task_arg(la, "AUTOSDD_SESSION_SWITCH_MODE=auto", "AUTOSDD_SESSION_SWITCH_MODE=notify")  # park 政策閘登記時拒 notify：以 auto 登記、改 argv
    lb = _park(ctx, b, pk_b, at, {**_AUTO, **off})
    (b.root / "RVPROD_DIRTY.txt").write_text("rv sideeffect SE09(b)：使任何 FRESH 嘗試被 handoff._refusals 在 runner 前拒絕\n", encoding="utf-8", newline="\n")
    lc = _park(ctx, c, pk_c, at, {**_AUTO, "AUTOSDD_DESKTOP_NOTIFY": "1", "AUTOSDD_SENTINEL_OFF": ""})
    flip_task_arg(lc, "AUTOSDD_SESSION_SWITCH_MODE=auto", "AUTOSDD_SESSION_SWITCH_MODE=notify")
    for tag, label in (("a", la), ("b", lb), ("c", lc)):
        ctx.check("<EndBoundary>" not in task_xml(label), f"({tag}) 正式目標的工作 XML 不該有 EndBoundary（MU-SE-07）")
    args_c = (get_task(lc) or {}).get("arguments", "")
    ctx.check("AUTOSDD_DESKTOP_NOTIFY" not in args_c and "AUTOSDD_SENTINEL_OFF" not in args_c, f"(c) Arguments 不該含通知／哨兵鍵（不合法值不轉送）：{args_c[:400]}")
    watch_no_window(ctx, [a, b, c], at + timedelta(seconds=75))
    left = wait_gone([la, lb, lc], 90)
    ctx.check(not left, f"到點後工作應自拆：{left}")
    for tag, box in (("a", a), ("c", c)):
        ev = names(box)
        ctx.check("park_job_start" in ev and "park_route" in ev and not calls(box), f"({tag}) 序列應含 park_job_start→park_route 且假 claude 0 次：{ev} {calls(box)}")
        ctx.check(not [n for n in ev if n.startswith("sideeffect")], f"({tag}) 正式目標不該有 sideeffect_*：{ev}")
    ev = names(b)
    cs = calls(b)
    route = [e for e in events(b) if e.get("event") == "park_route"]
    ctx.check(len(route) == 1 and route[0]["route"] == "RESUME", f"(b) park_route 應為 RESUME：{route}")
    ctx.check(len(cs) == 1 and cs[0]["argv"][:2] == ["-r", b.sid], f"(b) 假 claude 應恰 1 次且 argv 含 -r <sid>（出現不含 -r 的行＝FRESH 漏過前置拒絕）：{cs}")
    ctx.check(Path(cs[0]["cwd"]).resolve() == b.root.resolve() and "park_resumed" in ev, f"(b) cwd 應為替身 repo 且 park_resumed：{cs[0]['cwd']} {ev}")
    ctx.check(sum(1 for n in ev if n == "park_attempt") == PARK_ATTEMPTS and "park_chain_failed" not in ev and not [n for n in ev if n.startswith("sideeffect")], f"(b) park_attempt／失敗鏈／sideeffect 不符：{ev}")
    ctx.evidence("(a) notify 序列 park_job_start→park_route→模式拒絕、替身 0 次；(b) RESUME×1（argv -r、cwd 替身 repo）；(c) 登記 rc 0、Arguments 無通知／哨兵鍵；三者無 EndBoundary、無 sideeffect_*")
    ctx.evidence("誠實劃界：QW Q3 前正式目標登記不武裝 `AutoSDD_Sentinel_<替身 sid>`（無 `sentinel=` 末欄）；Q3 同 commit 補斷言並把該工作記入 L2 帳")
