"""pending_handoff 家族：Stop 守衛 `check_pending_handoff.py` 的散文交棒（RV-P1）與半路停工（RV-P2）。

真 `claude -p --model haiku`＋沙盒掛 repo 真守衛腳本；判定讀真逐字稿的 Stop `hook_blocking_error`。
"""  # noqa: E501

from __future__ import annotations

from . import CaseContext, case

HOOK = ".claude/hooks/check_pending_handoff.py"


def _say(text: str) -> str:
    return f"Reply with exactly the following text and nothing else (no tools, no extra words):\n{text}"  # noqa: E501


def _setup(ctx: CaseContext):
    sb = ctx.sandbox()
    sb.add_repo_hook("Stop", HOOK)
    return sb


def _blocks(tr, contains: str):
    return tr.hook_blocking_errors("Stop", contains)


@case("RV-P1", "pending_handoff")
def rv_p1(ctx: CaseContext) -> None:
    """把決定用散文留給掌舵者 ⇒ 第一次 Stop 推回、第二次（stop_hook_active）放行；
    反向：句內寫明「須掌舵者親打」（K=1）⇒ 不推回。"""
    sb = _setup(ctx)
    r = ctx.run_claude(sb, _say("剩下的部署決定留給掌舵者處理。"))
    ctx.check(r.rc == 0, f"回合 rc={r.rc} {r.stderr[:200]}")
    tr = ctx.transcript(sb)
    be = _blocks(tr, "AskUserQuestion")
    ctx.check(len(be) == 1, f"散文交棒推回次數={len(be)}（要恰好 1）；assistant={tr.assistant_texts()[:2]}")  # noqa: E501
    ctx.check("留給掌舵者" in str(be[0].data["attachment"]), "推回理由沒有命中詞「留給掌舵者」")
    stops = [e for e in sb.events() if e["ev"] == "Stop"]
    ctx.check(any(e["payload"].get("stop_hook_active") for e in stops),
              "沒有 stop_hook_active=True 的第二次 Stop（無法證明第二次放行）")
    n = len(be)
    r = ctx.run_claude(sb, _say("這個 K=1 決定須掌舵者親打「晉升」，我不代決。"))
    ctx.check(r.rc == 0, f"反向回合 rc={r.rc}")
    ctx.check(len(_blocks(ctx.transcript(sb), "AskUserQuestion")) == n, "K=1 親打句仍被推回（可滿足性逃生口壞了）")  # noqa: E501
    ctx.evidence(f"RV-P1 {tr.coords(be[0])} 散文交棒推回 1 次；K=1 句放行")


@case("RV-P2", "pending_handoff")
def rv_p2(ctx: CaseContext) -> None:
    """沙盒工作樹髒（未提交檔）＋進行式句子＋無背景任務 ⇒ 半路停工推回；
    反向：同句帶已封存／handoff 合法換手標記 ⇒ 放行。"""
    sb = _setup(ctx)
    sb.write_file("dirty.txt", "uncommitted\n")
    r = ctx.run_claude(sb, _say("接下來我會跑整套測試，然後提交。"))
    ctx.check(r.rc == 0, f"回合 rc={r.rc} {r.stderr[:200]}")
    tr = ctx.transcript(sb)
    stop0 = [e for e in sb.events() if e["ev"] == "Stop"][0]["payload"]
    ctx.check("background_tasks" in stop0, f"-p 的 Stop payload 沒有 background_tasks 欄位：{sorted(stop0)}")  # noqa: E501
    be = _blocks(tr, "沒有任何背景工作會叫醒你")
    ctx.check(len(be) == 1, f"半路停工推回次數={len(be)}（要 1）；assistant={tr.assistant_texts()[:2]}")  # noqa: E501
    n = len(be)
    r = ctx.run_claude(sb, _say("接下來我會跑整套測試，然後提交。交接包已封存，已交棒。"))
    ctx.check(r.rc == 0, f"反向回合 rc={r.rc}")
    ctx.check(len(_blocks(ctx.transcript(sb), "沒有任何背景工作會叫醒你")) == n, "帶合法換手標記仍被推回")  # noqa: E501
    ctx.evidence(f"RV-P2 {tr.coords(be[0])} 半路停工推回 1 次；已封存標記放行")
