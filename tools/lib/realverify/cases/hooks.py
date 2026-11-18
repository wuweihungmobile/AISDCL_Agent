"""hooks 家族：RV-L1（hook 活性）、RV-L2（`-p` 逐字稿的 block 記錄格式）。第二波案例的前置冒煙。"""

from __future__ import annotations

import re

from . import CaseContext, case

_FINISHED_OK = re.compile(r"Hooks: (\S+) \[(.*?)\] finished with status 0")


@case("RV-L1", "hooks", refs=("V8", "DEF-200-584"))
def rv_l1(ctx: CaseContext) -> None:
    """沙盒真 `claude -p --debug hooks`：debug 日誌有 hook 成功行、逐字稿有 hook 記錄、hook
    副作用檔真的被寫。

    🔴 同時掛 repo 的真守衛腳本（絕對路徑直接 spawn），證明它在沙盒裡是真的跑起來而非 fail-open。
    """
    sb = ctx.sandbox()
    sb.add_repo_hook("Stop", ".claude/hooks/check_claim_provenance.py")
    r = ctx.run_claude(sb, "Reply with exactly: ok")
    ctx.check(r.rc == 0 and not r.timed_out, f"claude -p rc={r.rc} timed_out={r.timed_out} stderr={r.stderr[:200]}")  # noqa: E501
    dbg = r.debug_text()
    oks = _FINISHED_OK.findall(dbg)
    ctx.check(any(ev.startswith("Stop") for ev, _ in oks), "debug 日誌沒有 Stop hook `finished with status 0` 行")  # noqa: E501
    ctx.check(any("check_claim_provenance.py" in cmd for _, cmd in oks), "repo 守衛 check_claim_provenance 沒有成功行（fail-open 假綠？）")  # noqa: E501
    ctx.check(any(ev.startswith("SessionStart") for ev, _ in oks), "debug 日誌沒有 SessionStart hook 成功行")  # noqa: E501
    evs = {e["ev"] for e in sb.events()}
    ctx.check({"SessionStart", "Stop"} <= evs, f"探針 hook 副作用檔缺事件，只有 {sorted(evs)}（hook 沒真的跑）")  # noqa: E501
    tr = ctx.transcript(sb)
    summ = [s for s in tr.stop_hook_summaries() if any("rv_probe_hook.py" in h.get("command", "") for h in s.data.get("hookInfos", []))]  # noqa: E501
    ctx.check(bool(summ), "逐字稿沒有 stop_hook_summary 記錄（含探針 hook）")
    ctx.evidence(f"RV-L1 {tr.coords(summ[0])} stop_hook_summary；debug ok 行 {len(oks)} 條")


@case("RV-L2", "hooks", refs=("V5", "V-W2", "V-PK4", "§0-2"))
def rv_l2(ctx: CaseContext) -> None:
    """實證 `-p` 逐字稿裡 Stop block／UserPromptSubmit block 的記錄格式（與互動模式比對的基準）。"""
    sb = ctx.sandbox()
    r1 = ctx.run_claude(sb, "Reply with exactly: one", env_extra={"RV_STOP_BLOCK": "1"})
    ctx.check(r1.rc == 0, f"第一輪 rc={r1.rc} {r1.stderr[:200]}")
    r2 = ctx.run_claude(sb, "RV_BLOCK_PROMPT hello")
    ctx.check(r2.rc == 0, f"第二輪 rc={r2.rc}")
    ctx.check("RV_UPS_BLOCK_REASON" in r2.stdout, f"-p stdout 沒回擋下理由：{r2.stdout[:200]!r}")
    tr = ctx.transcript(sb)
    be = tr.hook_blocking_errors("Stop", "RV_STOP_BLOCK_REASON")
    ctx.check(bool(be), "逐字稿沒有 attachment.type=hook_blocking_error（Stop）")
    a = be[0].data["attachment"]
    ctx.check(a.get("hookEvent") == "Stop" and "blockingError" in a, "hook_blocking_error 欄位形態與設計稿不符")  # noqa: E501
    ctx.check(any(s.data.get("hookErrors") for s in tr.stop_hook_summaries()), "stop_hook_summary 沒帶 hookErrors")  # noqa: E501
    ub = tr.blocked_user_prompts("RV_UPS_BLOCK_REASON")
    ctx.check(bool(ub), "逐字稿沒有 system/informational/preventContinuation 的 UserPromptSubmit 擋下記錄")  # noqa: E501
    ctx.check(ub[0].data.get("level") == "warning", f"level 非 warning：{ub[0].data.get('level')}")
    ctx.evidence(f"Stop block {tr.coords(be[0])}; UPS block {tr.coords(ub[0])}")
    ctx.notes.append("RAW Stop: " + tr.raw_line(be[0], 420))
    ctx.notes.append("RAW UPS: " + tr.raw_line(ub[0], 520))
