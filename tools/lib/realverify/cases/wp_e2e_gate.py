# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""workprogress 家族（A6g；真 `claude -p` 完成閘類，自 wp_e2e_batch 拆出以守 LOC 分級）：以 TCS-WorkProgress 逐條 E2E-WP 補案例——真 CLI／真逐字稿／真 `claude -p`／真 git。
不開互動視窗、不登記任何排程。沙盒 OIR 走 `openitems --root <沙盒> --trace-dir <沙盒>/traces`。"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta

from ..sandbox import REPO, projects_dir, slug_of
from . import CaseContext, case
from .prd_px_lib import ev
from .sessionctl_park import PY, run
from .wp_lib import tool_uses
from .wp_oir import LEDGER_REL, oi, seed_docs

_NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


# ───────────────────────── 真 claude -p 類 ─────────────────────────
_WRITE_PROMPT = ("Use the Write tool to create a file named out.txt with the content hello, then reply DONE. "
                 "If a hook later tells you something is unfinished, do NOT run any tool or command; just reply DONE again.")


def _say(text: str) -> str:
    return f"Reply with exactly the following text and nothing else (no tools, no extra words):\n{text}"


def _ledger_append(sb, events: list[dict]) -> None:
    p = sb.root / LEDGER_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8", newline="\n") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def _iso(minutes_ago: float) -> str:
    return (datetime.now().astimezone() - timedelta(minutes=minutes_ago)).isoformat(timespec="seconds")


def _seed_undriven(sb, n: int = 1, *, driven: bool = False) -> list[str]:
    """沙盒 OIR 放 auto 列（RV-L1）；`driven`＝另補一筆未來時刻的 drive（憑證有效＝非 undriven）。"""
    ids = []
    day = datetime.now().astimezone().strftime("%Y%m%d")
    for k in range(n):
        oid = f"OI-{day}-{k + 1:03d}"
        ids.append(oid)
        rows = [{"ev": "open", "id": oid, "ts": _iso(30), "by": "human", "title": f"沙盒待驅動列{k}", "source": "docs/01_requirements/src.md", "scope": "REQ-X", "kind": "auto", "check": {"realverify": "RV-L1"}}]
        if driven:
            rows.append({"ev": "drive", "id": oid, "ts": _iso(1), "by": "human", "task": f"AutoSDD_OpenItemSbx_x_{oid}", "credential": "sandbox", "at": (datetime.now().astimezone() + timedelta(hours=2)).isoformat(timespec="seconds"), "seq": 1})
        _ledger_append(sb, rows)
    return ids


def _gate_sandbox(ctx: CaseContext, *, with_guard: bool = False):
    sb = ctx.sandbox()
    seed_docs(sb)
    sb.add_repo_hook("Stop", ".claude/hooks/check_pending_handoff.py")
    if with_guard:
        from .sessionctl_handoff import install_sessionctl  # noqa: PLC0415

        install_sessionctl(sb)
    return sb


def _gate_blocks(tr, contains: str):
    return tr.hook_blocking_errors("Stop", contains)


@case("RV-WP55", "workprogress", refs=("E2E-WP-55", "REQ-WP-28", "REQ-WP-24"))
def rv_wp55(ctx: CaseContext) -> None:
    """沙盒 OIR：一列 auto 帳上 `attempt(fail,n=1)`（20 分前）後無 `drive`；真 `list` 判 undriven；沙盒掛真 `check_pending_handoff.py`，
    真 `claude -p` 做一次寫檔回合 ⇒ Stop 被完成閘推回一次且訊息含該 id。"""
    sb = _gate_sandbox(ctx)
    ids = _seed_undriven(sb, 1)
    _ledger_append(sb, [{"ev": "attempt", "id": ids[0], "ts": _iso(20), "by": "driver:rv", "n": 1, "result": "fail", "drive_seq": 1}])
    lst = oi(sb, "list", "--undriven")
    ctx.check(lst.returncode == 0 and ids[0] in lst.stdout, f"真 list --undriven 應含 {ids[0]}：{lst.stdout[-300:]}")
    r = ctx.run_claude(sb, _WRITE_PROMPT, extra_args=("--permission-mode", "bypassPermissions"), timeout_s=420)
    ctx.check(r.rc == 0 and not r.timed_out, f"寫檔回合 rc={r.rc} {r.stderr[:200]}")
    tr = ctx.transcript(sb)
    ctx.check("Write" in [n for _, n, _ in tool_uses(tr)], f"模型沒有寫檔：{[n for _, n, _ in tool_uses(tr)]}")
    be = _gate_blocks(tr, "完成閘")
    ctx.check(len(be) == 1 and ids[0] in str(be[0].data.get("attachment")), f"完成閘應推回 1 次且含 {ids[0]}：{len(be)} {[str(b.data.get('attachment'))[:120] for b in be]}")
    ev(ctx, "gate_pushed_once", f"{tr.coords(be[0])} 完成閘推回 1 次、含 {ids[0]}；真 list 判 undriven")


@case("RV-WP06", "workprogress", refs=("E2E-WP-06", "REQ-WP-20", "REQ-WP-25"))
def rv_wp06(ctx: CaseContext) -> None:
    """真 `claude -p` 完成閘四變體（沙盒掛真 `check_pending_handoff.py`）：(a) 宣告完成＋1 undriven（寫檔回合）⇒ 推回一次含 OI id、
    第二次放行、`.gate` 標記存在；(b) 同 (a) 但已 drive ⇒ 無完成閘推回；(c) 只讀回合（無寫檔）⇒ 無推回；(d) 「接下來要做 X」＋髒工作樹、無背景工作 ⇒ 半路停工推回一次。
    （keepwarm 背景 shell 的共存由 RV-KW 系列與 RV-C 系列覆蓋；本案例釘完成閘本身的四個判準）"""
    # (a)
    sa = _gate_sandbox(ctx)
    ida = _seed_undriven(sa, 1)
    ra = ctx.run_claude(sa, _WRITE_PROMPT, extra_args=("--permission-mode", "bypassPermissions"), timeout_s=420)
    ctx.check(ra.rc == 0, f"(a) rc={ra.rc}")
    tra = ctx.transcript(sa)
    ba = _gate_blocks(tra, "完成閘")
    ctx.check(len(ba) == 1 and ida[0] in str(ba[0].data.get("attachment")), f"(a) 完成閘應推回 1 次含 {ida[0]}：{len(ba)}")
    stops = [e for e in sa.events() if e["ev"] == "Stop"]
    ctx.check(any(e["payload"].get("stop_hook_active") for e in stops), "(a) 沒有 stop_hook_active=True 的第二次 Stop（無法證明第二次放行）")
    gates = list((sa.root / "traces" / "openitems").glob("*.gate")) if (sa.root / "traces" / "openitems").is_dir() else []
    ctx.check(bool(gates), "(a) traces/openitems/<sid>.gate 標記不存在")
    # (b)
    sbb = _gate_sandbox(ctx)
    _seed_undriven(sbb, 1, driven=True)
    rb = ctx.run_claude(sbb, _WRITE_PROMPT, extra_args=("--permission-mode", "bypassPermissions"), timeout_s=420)
    ctx.check(rb.rc == 0 and not _gate_blocks(ctx.transcript(sbb), "完成閘"), "(b) 已 drive 的項目不應被完成閘推回")
    # (c)
    sc = _gate_sandbox(ctx)
    _seed_undriven(sc, 1)
    sc.write_file(".gitignore", "debug_*.log\nhook_events.jsonl\ntraces/\n.claude/\nprojects/\n")  # 只讀回合要工作樹乾淨：完成閘的佐證之一就是 git 髒
    for args in (["add", "-A"], ["commit", "-q", "-m", "seed"]):
        subprocess.run(["git", *args], cwd=str(sc.root), check=True, capture_output=True, creationflags=_NOWIN)
    rc_ =ctx.run_claude(sc, "Reply with exactly: READONLY_DONE (no tools).", timeout_s=120)
    ctx.check(rc_.rc == 0 and not _gate_blocks(ctx.transcript(sc), "完成閘"), "(c) 只讀回合不應被完成閘推回")
    # (d)
    sd = _gate_sandbox(ctx)
    sd.write_file("dirty.txt", "uncommitted\n")
    rd = ctx.run_claude(sd, _say("接下來我會跑整套測試，然後提交。"), timeout_s=120)
    ctx.check(rd.rc == 0, f"(d) rc={rd.rc}")
    bd = _gate_blocks(ctx.transcript(sd), "沒有任何背景工作會叫醒你")
    ctx.check(len(bd) == 1, f"(d) 半路停工應推回 1 次：{len(bd)}")
    ev(ctx, "gate_variants", f"(a){tra.coords(ba[0])} 推回1次含{ida[0]}且.gate存在；(b)已drive無推回；(c)只讀無推回；(d)半路停工推回1次")


@case("RV-WP21", "workprogress", refs=("E2E-WP-21", "REQ-WP-15", "REQ-WP-16", "REQ-WP-78"))
def rv_wp21(ctx: CaseContext) -> None:
    """沙盒 OIR 放 human×8、k1×1；沙盒掛真 `context_budget_guard.py`（SessionStart），真 `claude -p`：簡報含 7 項＋「另 2 項」，k1 列標「須掌舵者親打」。"""
    sb = ctx.sandbox(probe_hooks=False)
    seed_docs(sb)
    sb.add_repo_hook("SessionStart", ".claude/hooks/context_budget_guard.py", timeout=30)
    day = datetime.now().astimezone().strftime("%Y%m%d")
    rows = []
    for k in range(8):
        rows.append({"ev": "open", "id": f"OI-{day}-{k + 1:03d}", "ts": _iso(100 - k), "by": "human", "title": f"人工目視項{k}", "source": "docs/01_requirements/src.md", "scope": "REQ-X", "kind": "human", "why_not_auto": "需要真人在桌面目視畫面才能判定"})
    rows.append({"ev": "open", "id": f"OI-{day}-009", "ts": _iso(10), "by": "human", "title": "K=1 決定項", "source": "docs/01_requirements/src.md", "scope": "REQ-X", "kind": "k1", "why_not_auto": "只認掌舵者真人親打的決定"})
    _ledger_append(sb, rows)
    r = ctx.run_claude(sb, "Reply with exactly: BRIEF_OK", env_extra={"AUTOSDD_SENTINEL_OFF": "1"}, timeout_s=150)
    ctx.check(r.rc == 0, f"回合 rc={r.rc} {r.stderr[:200]}")
    tr = ctx.transcript(sb)
    blob = "\n".join(tr.raw_line(x, 100000) for x in tr.recs)
    m = re.search(r"掌舵者目視清單（OIR）：([^\"]*?)。", blob)
    ctx.check(m is not None, "SessionStart 簡報沒有「掌舵者目視清單（OIR）」段")
    seg = m[1]
    shown = re.findall(r"OI-\d{8}-\d{3}", seg)
    ctx.check(len(shown) == 7 and "另 2 項" in seg, f"應列 7 項＋「另 2 項」：{len(shown)} 項；{seg[:200]}")
    ev(ctx, "brief_cap_and_more", f"SessionStart 簡報列 {len(shown)} 項＋「另 2 項」")
    # k1 在 open 時間最晚 ⇒ 落在「另 2 項」之外也可能；單獨驗 k1 標記：另開一個只有 k1 的沙盒
    s2 = ctx.sandbox(probe_hooks=False)
    seed_docs(s2)
    s2.add_repo_hook("SessionStart", ".claude/hooks/context_budget_guard.py", timeout=30)
    _ledger_append(s2, [rows[-1]])
    r2 = ctx.run_claude(s2, "Reply with exactly: BRIEF_OK2", env_extra={"AUTOSDD_SENTINEL_OFF": "1"}, timeout_s=150)
    ctx.check(r2.rc == 0, f"k1 沙盒回合 rc={r2.rc}")
    t2 = ctx.transcript(s2)
    b2 = "\n".join(t2.raw_line(x, 100000) for x in t2.recs)
    ctx.check("須掌舵者親打" in b2, "k1 列沒有標「須掌舵者親打」")
    ev(ctx, "k1_marked", "k1 列在簡報標「須掌舵者親打」")


@case("RV-WP45", "workprogress", refs=("E2E-WP-45", "REQ-WP-25"))
def rv_wp45(ctx: CaseContext) -> None:
    """沙盒掛真 `check_pending_handoff.py`；OIR 帳本路徑改放成一個**目錄**（讀檔必失敗）；真 `claude -p --debug hooks` 做一次寫檔回合 ⇒
    Stop 未被完成閘推回；debug log 的 hook stderr 含 OIR 讀取失敗一行；hook `success`。"""
    sb = ctx.sandbox()
    seed_docs(sb)
    sb.add_repo_hook("Stop", ".claude/hooks/check_pending_handoff.py")
    (sb.root / LEDGER_REL).mkdir(parents=True)  # 帳本路徑是目錄
    r = ctx.run_claude(sb, _WRITE_PROMPT, extra_args=("--permission-mode", "bypassPermissions"), timeout_s=420)
    ctx.check(r.rc == 0 and not r.timed_out, f"回合 rc={r.rc}")
    tr = ctx.transcript(sb)
    ctx.check("Write" in [n for _, n, _ in tool_uses(tr)], "模型沒有寫檔")
    ctx.check(not _gate_blocks(tr, "完成閘"), "OIR 讀不到仍被完成閘推回（應 fail-open）")
    dbg = r.debug_text()
    ctx.check("OIR 讀取失敗" in dbg, f"debug log 沒有「OIR 讀取失敗」一行：{[ln[:120] for ln in dbg.splitlines() if 'openitems' in ln][:3]}")
    ctx.check(re.search(r"Stop.*check_pending_handoff.*success|Hook .*Stop.*success", dbg, re.S) is not None, "debug log 沒有 Stop hook success")
    ev(ctx, "fail_open_stderr", "完成閘未推回；debug log 含「openitems 完成閘：OIR 讀取失敗，本次放行」；Stop hook success")


@case("RV-WP41", "workprogress", refs=("E2E-WP-41", "REQ-WP-74", "REQ-WP-75"))
def rv_wp41(ctx: CaseContext) -> None:
    """真 `claude -p --model haiku --debug hooks` 於 repo 根：`check_pending_handoff` Stop hook `success`；根 CLAUDE.md 守衛表宣稱↔註冊
    雙向鎖（`TestR74…`、`TestR79…`）綠。該 session 的逐字稿於收尾刪除（不留在真專案目錄）。"""
    from ..driver import find_claude  # noqa: PLC0415

    sb = ctx.sandbox(probe_hooks=False)
    sid = sb.sid
    dbg = sb.root / "debug_real.log"
    env = sb.env()
    env["AUTOSDD_UNATTENDED"] = ""
    env.pop("AUTOSDD_UNATTENDED", None)
    p = subprocess.run([find_claude(), "-p", "--model", "haiku", "--debug", "hooks", "--debug-file", str(dbg), "--session-id", sid, "Reply with exactly: OK"],
                       cwd=str(REPO), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, timeout=200, creationflags=_NOWIN)
    try:
        text = dbg.read_text(encoding="utf-8", errors="replace") if dbg.is_file() else ""
        ctx.check(p.returncode == 0, f"claude rc={p.returncode} {p.stderr[-200:]}")
        stop_lines = [ln for ln in text.splitlines() if "check_pending_handoff" in ln]
        ctx.check(bool(stop_lines), "debug log 沒有提到 check_pending_handoff（hook 沒掛到？）")
        ok = [ln for ln in text.splitlines() if re.search(r"Hook (Stop|.*Stop).*success|Stop.*success", ln)]
        ctx.check(bool(ok), f"沒有 Stop hook success 行：{stop_lines[:2]}")
    finally:
        for f in projects_dir().glob(f"*/{sid}.jsonl"):
            try:
                f.unlink()
            except OSError:
                pass
    t = run([PY, "-m", "unittest", "tools.tests.test_doc_loc_baseline_freshness_r60.TestR74RootClaudeMdHookClaimsMatchRegistration", "tools.tests.test_doc_loc_baseline_freshness_r60.TestR79EveryRegisteredHookIsNamedInClaudeMd"],
            cwd=REPO, env={**os.environ, "PYTHONUTF8": "1"}, timeout=280)
    tail = (t.stdout + t.stderr).strip().splitlines()
    ctx.check(t.returncode == 0 and tail and tail[-1] == "OK", f"守衛表雙向鎖應綠：rc={t.returncode} {tail[-3:]}")
    ev(ctx, "stop_hook_success_and_locks", f"repo 根真 haiku 回合：{ok[0][:100]!r}；TestR74／TestR79 OK（{[x for x in tail if x.startswith('Ran')][-1:]}）")
    _ = (sys, time, slug_of)
