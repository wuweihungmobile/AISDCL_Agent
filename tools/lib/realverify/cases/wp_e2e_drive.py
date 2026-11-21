# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""workprogress 家族（A6g；驅動器真排程與真視窗類，自 wp_e2e_batch 拆出以守 LOC 分級）：以 TCS-WorkProgress 逐條 E2E-WP 補案例——真 CLI／真逐字稿／真 `claude -p`／真 git。
不開互動視窗、不登記任何排程。沙盒 OIR 走 `openitems --root <沙盒> --trace-dir <沙盒>/traces`。"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from datetime import datetime, timedelta

from ..driver import EnvMissing
from ..sandbox import REPO
from . import CaseContext, case
from .prd_px_lib import ev
from .sessionctl_park import PY, run
from .wp_e2e_batch import _last
from .wp_oir import CLI, LEDGER_REL, oi, seed_docs

_NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


# ───────────────────────── E2E-WP-02：驅動器真排程（沙盒前綴） ─────────────────────────
@case("RV-WP02", "workprogress", refs=("E2E-WP-02", "REQ-WP-10", "REQ-WP-18"), sched=True)
def rv_wp02(ctx: CaseContext) -> None:
    """真 schtasks＋真 `drive`：載具＝`tools/probe/openitems_drive_e2e.py`（排程名一律沙盒前綴 `AutoSDD_OpenItemSbx_<8 碼>_`、
    finally 撤銷並斷言 0 殘留、前後各列一次真 `AutoSDD_OpenItem_*` 須相同）。逐列獨立回讀 NextRunTime 等於 `drive` 憑證；
    等排程真觸發後 start／每窗名額／重排。只認載具 `OPENITEMS_DRIVE_E2E=pass`；額度帶偏高時 pass 路徑被載具標 SKIP（屬 E2E-WP-03），
    本案例不宣稱它（記在 notes），E2E-WP-03 另案待額度空檔。"""
    if os.name != "nt":
        raise EnvMissing("真 schtasks 載具只在 Windows")
    p = subprocess.run([PY, str(REPO / "tools" / "probe" / "openitems_drive_e2e.py")], cwd=str(REPO), env={**os.environ, "PYTHONUTF8": "1"},
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1500, creationflags=_NOWIN)
    out = p.stdout + p.stderr
    last = _last(out)
    m = re.match(r"OPENITEMS_DRIVE_E2E=(\w[\w-]*) checks=(\d+) failed=(\d+) skipped=(.*)", last)
    ctx.check(m is not None, f"載具末行格式不符（rc={p.returncode}）：{last!r}\n{out[-500:]}")
    fails = [ln for ln in out.splitlines() if ln.startswith("[FAIL]")]
    ctx.check(m[1] == "pass" and not fails, f"載具判 {m[1]}：{fails[:4]}")
    # 額度帶偏高時載具把 pass 路徑標 SKIP（驅動器讓路）——那是 E2E-WP-03 的內容，不是本案例（E2E-WP-02：憑證＝NextRunTime、可撤銷）的判準；如實寫進證據、不宣稱 pass 路徑
    if m[4].strip() != "[]":
        ctx.notes.append(f"載具 skipped={m[4]}（額度讓路；pass 路徑屬 E2E-WP-03，未在本案例宣稱）")
    ev(ctx, "drive_credential_and_cleanup", f"{m[0]}（獨立回讀 NextRunTime＝drive 憑證；沙盒前綴排程 0 殘留；真 AutoSDD_OpenItem_* 未碰）")


# ───────────────────────── 驅動器讓路（真 run-driver 行程；沙盒前綴排程） ─────────────────────────
def _drive_setup(ctx: CaseContext, sb) -> str:
    """沙盒 OIR＋沙盒前綴；前綴寫進 `traces/oldwin/task_prefix`，讓 runner 的 `Sandbox.cleanup` 也會撤掉該前綴全部排程。"""
    import uuid  # noqa: PLC0415

    seed_docs(sb)
    prefix = f"AutoSDD_OpenItemSbx_{uuid.uuid4().hex[:8]}_"
    sb.write_file("traces/oldwin/task_prefix", prefix + "\n")
    pp = sb.root / "docs" / "06_quality" / "OpenItems_Protocol" / "params.json"
    cfg = json.loads(pp.read_text(encoding="utf-8"))
    cfg.update(task_prefix=prefix, stagger_minutes=0, retry_backoff_minutes=3, busy_backoff_minutes=3)
    pp.write_text(json.dumps(cfg), encoding="utf-8", newline="\n")
    return prefix


def _prefix_tasks(prefix: str) -> dict:
    from lib.openitems import schedcache  # noqa: PLC0415

    return schedcache.WindowsBackend().list_tasks(prefix) or {}


def _disarm_prefix(prefix: str) -> list[str]:
    from lib.openitems import schedcache  # noqa: PLC0415

    be = schedcache.WindowsBackend()
    for name in list(_prefix_tasks(prefix)):
        be.unregister(name)
    return sorted(_prefix_tasks(prefix))


def _open_and_drive(sb) -> tuple[str, dict]:
    o = oi(sb, "open", "--title", "沙盒驅動列", "--source", "docs/01_requirements/src.md", "--scope", "REQ-X", "--kind", "auto", "--check", '{"realverify":"RV-L1"}', "--by", "human")
    m = re.search(r"(OI-\d{8}-\d{3})", o.stdout + o.stderr)
    if o.returncode != 0 or m is None:
        raise AssertionError(f"立案失敗 rc={o.returncode} {o.stdout[-200:]}{o.stderr[-200:]}")
    d = oi(sb, "drive", m[1])
    if d.returncode != 0 or "OPENITEMS_DRIVE=ok" not in d.stdout:
        raise AssertionError(f"drive 失敗 rc={d.returncode} {d.stdout[-300:]}{d.stderr[-300:]}")
    rows = [json.loads(ln) for ln in (sb.root / LEDGER_REL).read_text(encoding="utf-8").splitlines() if ln.strip()]
    return m[1], [r for r in rows if r["ev"] == "drive" and r["id"] == m[1]][-1]


def _run_driver(sb, item: str, task: str, env_extra: dict | None = None):
    return run([PY, CLI, "--root", str(sb.root), "--trace-dir", str(sb.root / "traces"), "run-driver", item, "--task", task], cwd=sb.root, env=sb.env(env_extra), timeout=300)


def _events_of(sb, item: str) -> list[dict]:
    rows = [json.loads(ln) for ln in (sb.root / LEDGER_REL).read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [r for r in rows if r["id"] == item]


@case("RV-WP24", "workprogress", refs=("E2E-WP-24", "REQ-WP-12"), sched=True)
def rv_wp24(ctx: CaseContext) -> None:
    """沙盒：真 `claude -p` 剛做完一回合（沙盒 slug 下有近期主控對話記錄）時，真 `run-driver` 行程觸發 ⇒ 讓路
    `attempt(deferred, interactive)`、失敗次數不變、重排新 drive（排程器現查 NextRunTime）。排程名一律沙盒前綴、finally 全撤並斷言 0 殘留。"""
    if os.name != "nt":
        raise EnvMissing("真 schtasks 載具只在 Windows")
    sb = ctx.sandbox(probe_hooks=False)
    prefix = _drive_setup(ctx, sb)
    try:
        r = ctx.run_claude(sb, "Reply with exactly: RV_WP24_BUSY", timeout_s=150)
        ctx.check(r.rc == 0, f"主控回合 rc={r.rc}")
        item, drv = _open_and_drive(sb)
        out = _run_driver(sb, item, drv["task"])
        last = _last(out.stdout)
        ctx.check(out.returncode == 0 and "OPENITEMS_DRIVER=deferred" in last and "reason=interactive" in last, f"run-driver 應讓路 deferred(interactive)：rc={out.returncode} {last!r} {out.stderr[-200:]}")
        evs = _events_of(sb, item)
        att = [e for e in evs if e["ev"] == "attempt"]
        ctx.check(len(att) == 1 and att[0]["result"] == "deferred" and att[0].get("reason") == "interactive", f"attempt 應只有一筆 deferred(interactive)：{att}")
        drives = [e for e in evs if e["ev"] == "drive"]
        ctx.check(len(drives) == 2 and drives[-1]["task"] != drv["task"], f"應重排出新的 drive：{[d['task'] for d in drives]}")
        live = _prefix_tasks(prefix)
        ctx.check(drives[-1]["task"] in live and bool(live[drives[-1]["task"]]), f"排程器現查：新工作應存在且 NextRunTime 非空：{live}")
        ev(ctx, "deferred_interactive_redrive", f"run-driver 末行 {last}；attempt(deferred,interactive)×1、無 fail；重排新 drive {drives[-1]['task']} NextRunTime={live[drives[-1]['task']]}")
    finally:
        left = _disarm_prefix(prefix)
    ctx.check(not left, f"前綴 {prefix} 殘留排程：{left}")


@case("RV-WP25", "workprogress", refs=("E2E-WP-25", "REQ-WP-13"), sched=True)
def rv_wp25(ctx: CaseContext) -> None:
    """沙盒：真 `run-driver` 行程環境把額度收斂門檻設為 1（`AUTOSDD_QUOTA_CONVERGE_PCT=1`、NOTICE=0；`quota_policy` 既有鍵）⇒
    `deferred(quota)`；重排時刻 ≥ 該行程觀測到的 reset（以同環境另跑 `--pace` 取短窗剩餘分鐘）。前綴排程 finally 全撤。"""
    if os.name != "nt":
        raise EnvMissing("真 schtasks 載具只在 Windows")
    sb = ctx.sandbox(probe_hooks=False)
    prefix = _drive_setup(ctx, sb)
    envx = {"AUTOSDD_QUOTA_CONVERGE_PCT": "1", "AUTOSDD_QUOTA_NOTICE_PCT": "0"}
    try:
        item, drv = _open_and_drive(sb)
        pace = run([PY, str(REPO / "tools" / "session_resume_planner.py"), "--pace"], cwd=REPO, env=sb.env(envx), timeout=120)
        mins = [float(x) for x in re.findall(r"kind=(?:session|five_hour) \d+% 剩 (\d+) 分鐘", pace.stdout)]
        ctx.check(bool(mins), f"--pace 取不到短窗剩餘分鐘：{pace.stdout[:200]}")
        t0 = datetime.now().astimezone()
        out = _run_driver(sb, item, drv["task"], envx)
        last = _last(out.stdout)
        ctx.check(out.returncode == 0 and "OPENITEMS_DRIVER=deferred" in last and "reason=quota" in last, f"應 deferred(quota)：rc={out.returncode} {last!r} {out.stderr[-200:]}")
        drives = [e for e in _events_of(sb, item) if e["ev"] == "drive"]
        ctx.check(len(drives) == 2, f"應重排新 drive：{len(drives)}")
        at = datetime.fromisoformat(drives[-1]["at"])
        floor = t0 + timedelta(minutes=min(mins)) - timedelta(minutes=2)  # --pace 兩次呼叫間的分鐘取整裕度
        ctx.check(at >= floor, f"重排時刻 {at.isoformat()} 應 ≥ 觀測 reset（約 {floor.isoformat()}）")
        ev(ctx, "deferred_quota_after_reset", f"{last}；重排 at={drives[-1]['at']} ≥ reset≈{(t0 + timedelta(minutes=min(mins))).isoformat(timespec='minutes')}（短窗剩 {min(mins):.0f} 分）")
    finally:
        left = _disarm_prefix(prefix)
    ctx.check(not left, f"前綴 {prefix} 殘留排程：{left}")


# ───────────────────────── E2E-WP-35：AutoClaude 測試不污染 checkpoints ─────────────────────────
@case("RV-WP35", "workprogress", refs=("E2E-WP-35", "REQ-WP-62"), long=True)
def rv_wp35(ctx: CaseContext) -> None:
    """真跑 AutoClaude `tests/`（xdist，全套）：跑前跑後 `AutoClaude/checkpoints/` 檔數相同（REQ-WP-62：測試不得把 checkpoint 寫進真目錄）。
    全套 pytest 的 rc／摘要列入證據（不以 rc 取代檔數判準，但失敗一律揭露）。"""
    ck = REPO / "AutoClaude" / "checkpoints"

    def count() -> int:
        return sum(1 for p in ck.rglob("*") if p.is_file()) if ck.is_dir() else 0

    before = count()
    p = subprocess.run([PY, "-m", "pytest", "tests/", "-q", "--no-header", "--dist", "loadgroup", "-p", "no:cacheprovider"], cwd=str(REPO / "AutoClaude"),
                       env={**os.environ, "PYTHONUTF8": "1"}, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3300, creationflags=_NOWIN)
    after = count()
    tail = _last(p.stdout) or _last(p.stderr)
    ev(ctx, "checkpoints_before_after", f"AutoClaude/checkpoints 檔數 {before}→{after}；pytest rc={p.returncode} 摘要：{tail}")
    ctx.check(before == after, f"跑全套後 checkpoints 檔數改變：{before}→{after}")
    ctx.check(p.returncode == 0, f"AutoClaude 全套 rc={p.returncode}（檔數判準已過，但全套非綠）：{tail}")


# ───────────────────────── 互動視窗類（只經 interactive.trusted_sandbox；宿主未信任＝ENV） ─────────────────────────
def _new_window_transcript(sb, timeout_s: float = 240):
    from ..transcript import Transcript  # noqa: PLC0415
    from .wp_lib import other_transcript, wait_until  # noqa: PLC0415

    p = wait_until(lambda: other_transcript(sb), timeout_s, 3.0)
    return Transcript(p, None) if p else None


def _close_windows(sb, extra_pids=()) -> list[int]:
    from .sessionctl_handoff import kill_verified, pid_alive, spawn_trace  # noqa: PLC0415

    pids = sorted({*extra_pids, *(int(x["pid"]) for ev_ in ("session_switch_spawned", "forward_spawned") for x in spawn_trace(sb, ev_) if isinstance(x.get("pid"), int))})
    for p in pids:
        kill_verified(p, sb.sid)
    time.sleep(2)
    return [p for p in pids if pid_alive(p)]


@case("RV-WP13", "workprogress", refs=("E2E-WP-13", "REQ-WP-48", "V3"))
def rv_wp13(ctx: CaseContext) -> None:
    """（RV-H6）互動視窗：宿主 worktree 沙盒（信任鍵＝宿主，不跳信任框）封存後真 `handoff --spawn`：新視窗（haiku）自己的逐字稿出現
    SessionStart 公告「未接手的交接包」與 Read 該交接包路徑的工具記錄；不改任何全域設定（宿主信任由掌舵者一次性同意）。"""
    from .. import interactive  # noqa: PLC0415
    from .sessionctl_handoff import run_cli, seal_session, spawn_trace  # noqa: PLC0415
    from .wp_lib import reads_of, wait_until  # noqa: PLC0415

    sb = interactive.trusted_sandbox(ctx, probe_hooks=False)
    pkg = seal_session(ctx, sb, announce=True)
    pids: list[int] = []
    try:
        rc, out, err = run_cli(sb, "handoff", "--spawn", str(pkg), timeout=120)
        rows = spawn_trace(sb, "session_switch_spawned")
        ctx.check(bool(rows), f"沒有 session_switch_spawned 痕跡：rc={rc} {err[:300]}")
        pids = [int(x["pid"]) for x in rows if isinstance(x.get("pid"), int)]
        tr = _new_window_transcript(sb)
        ctx.check(tr is not None, f"新視窗沒有在時限內產生自己的逐字稿（rc={rc} {err[:200]}）")
        ok = wait_until(lambda: reads_of(_reload(tr), pkg.name), 240, 5.0)
        tr = _reload(tr)
        blob = "\n".join(tr.raw_line(x, 100000) for x in tr.recs)
        ctx.check("未接手的交接包" in blob, "新視窗逐字稿沒有 SessionStart 公告「未接手的交接包」")
        ctx.check(bool(ok), f"新視窗沒有 Read 交接包 {pkg.name} 的工具記錄")
        ev(ctx, "new_window_read_package", f"新視窗逐字稿 {tr.path.name[:8]} 含公告與 Read {pkg.name}（spawn rc={rc}、pid={pids}）")
    finally:
        left = _close_windows(sb, pids)
    ctx.check(not left, f"視窗沒收乾淨：{left}")


def _reload(tr):
    from ..transcript import Transcript  # noqa: PLC0415

    return Transcript(tr.path, None)


@case("RV-WP62", "workprogress", refs=("E2E-WP-62", "REQ-WP-92", "V-F1"))
def rv_wp62(ctx: CaseContext) -> None:
    """（RV-F4）互動視窗：宿主 worktree 沙盒封存後，冷窗＋大上下文的真人提示 ⇒ UserPromptSubmit 轉送真開新視窗（haiku）；
    新視窗自己的逐字稿有 Read 該 `forward-*.md` 的工具記錄（原文逐字送到新 session）。視窗收尾依 pid＋命令列驗身分。"""
    from .. import interactive  # noqa: PLC0415
    from .sessionctl_handoff import (  # noqa: PLC0415
        backdate_transcript,
        sc_env,
        seal_session,
        set_ctx,
        spawn_trace,
    )
    from .wp_lib import reads_of, wait_until  # noqa: PLC0415

    sb = interactive.trusted_sandbox(ctx, probe_hooks=False)
    pkg = seal_session(ctx, sb)
    pids: list[int] = []
    try:
        tp = ctx.transcript(sb).path
        set_ctx(tp, 600_000)
        backdate_transcript(tp, 3)
        r = ctx.run_claude(sb, "RV_F4_ORIGINAL 這是掌舵者原文，要逐字轉送", env_extra=sc_env(sb), timeout_s=180)
        ctx.check(r.rc == 0, f"轉送回合 rc={r.rc}")
        files = sorted(pkg.parent.glob(f"{pkg.stem}.forward-*.md"))
        ctx.check(len(files) == 1, f"原文應落檔 1 份：{files}")
        pids = [int(x["pid"]) for x in spawn_trace(sb, "session_switch_spawned") if isinstance(x.get("pid"), int)]
        tr = _new_window_transcript(sb)
        ctx.check(tr is not None, "轉送開出的新視窗沒有在時限內產生自己的逐字稿")
        ok = wait_until(lambda: reads_of(_reload(tr), files[0].name), 240, 5.0)
        ctx.check(bool(ok), f"新視窗沒有 Read {files[0].name} 的工具記錄")
        ev(ctx, "forward_file_read", f"新視窗逐字稿 {tr.path.name[:8]} Read {files[0].name}（pid={pids}）")
    finally:
        left = _close_windows(sb, pids)
    ctx.check(not left, f"視窗沒收乾淨：{left}")
