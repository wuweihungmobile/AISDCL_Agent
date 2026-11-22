"""sessionctl_gates 家族：SendMessage 續棒冷熱閘（RV-M1）與收斂閘擋派工（RV-M2）。

真 `claude -p --model haiku`＋沙盒掛 repo 真 `sessionctl_guard.py`（PreToolUse）；判定讀真逐字稿裡
`PreToolUse:<tool> hook error` 的 tool_result。快取「冷」只靠改寫**沙盒自己的**代理逐字稿時間戳；
門檻只用 env 下修（方向鎖允許）。不動守衛判準。
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta

from ..sandbox import Sandbox
from . import CaseContext, case
from .sessionctl_watch import (
    BYPASS,
    _install_guard,
    _subagent_files,
    _tool_result_texts,
)

_ECHO_AGENT = (
    "Use the Agent tool exactly once with run_in_background=false, subagent_type general-purpose, "
    "model haiku, description 'rv echo', prompt: 'Reply with the single word PONG'. Then reply "
    "with the agentId it reported, nothing else."
)


def _hook_errors(tr, tool: str) -> list[tuple[int, str]]:
    return [(ln, t) for ln, t in _tool_result_texts(tr) if f"PreToolUse:{tool} hook error" in t]


def _send(ctx: CaseContext, sb: Sandbox, aid: str, text: str, env: dict):
    return ctx.run_claude(
        sb, f"Use the SendMessage tool to send the exact text below to agent id {aid}, then report "
            f"in one line what happened. Text:\n{text}",
        extra_args=BYPASS, env_extra=env, timeout_s=300)


def _make_agent(ctx: CaseContext, sb: Sandbox):
    r = ctx.run_claude(sb, _ECHO_AGENT, extra_args=BYPASS, timeout_s=300)
    ctx.check(r.rc == 0, f"建代理回合 rc={r.rc} {r.stderr[:200]}")
    files = _subagent_files(sb)
    ctx.check(len(files) == 1, f"沙盒代理檔數={len(files)}（要 1）")
    return files[0]


def _age(path, minutes: int) -> None:
    """把沙盒自己的（已交卷、靜止的）代理逐字稿所有時間戳往前推，造出「快取已冷」。"""
    out = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        d = json.loads(ln)
        if d.get("timestamp"):
            t = datetime.fromisoformat(str(d["timestamp"]).replace("Z", "+00:00")) - timedelta(minutes=minutes)  # noqa: E501
            d["timestamp"] = t.isoformat().replace("+00:00", "Z")
        out.append(json.dumps(d, ensure_ascii=False))
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


@case("RV-M1", "sessionctl_gates", refs=("V4",))
def rv_m1(ctx: CaseContext) -> None:
    """(1) 無人模式 ⇒ SendMessage 被 PreToolUse rc 2 擋，連 `續棒理由：` 也無效；
    (M1b) 互動＋快取冷＋上下文大 ⇒ 擋；訊息帶 `續棒理由：` ⇒ 放行（落 resume_gate_override 痕跡）。"""  # noqa: E501
    sb = ctx.sandbox()
    _install_guard(sb)
    agent = _make_agent(ctx, sb)
    aid = agent.stem.removeprefix("agent-")
    low = {"AUTOSDD_RESUME_AGENT_TOKENS": "1"}
    reason = "續棒理由：RV 實測放行路徑，確有必要"

    # (1) 無人窗口：不論冷熱、有無理由都擋
    r = _send(ctx, sb, aid, f"hello\n{reason}", {**low, "AUTOSDD_UNATTENDED": "1"})
    ctx.check(r.rc == 0, f"無人回合 rc={r.rc}")
    be = _hook_errors(ctx.transcript(sb), "SendMessage")
    ctx.check(any("已阻斷（無人窗口）" in t for _, t in be), f"無人模式沒有被擋（hook error={be[:1]}）")  # noqa: E501
    n_unatt = len(be)

    # M1b：互動＋冷
    _age(agent, 30)
    r = _send(ctx, sb, aid, "hello", low)
    ctx.check(r.rc == 0, f"互動冷回合 rc={r.rc}")
    be = _hook_errors(ctx.transcript(sb), "SendMessage")
    cold = [x for x in be[n_unatt:] if "快取已冷" in x[1]]
    ctx.check(bool(cold), f"互動＋冷＋上下文大沒有被擋（新 hook error={be[n_unatt:]}）")
    ctx.check("（無人窗口）" not in cold[0][1], "互動被擋卻是無人窗口字樣")

    # 反向：同樣冷，訊息帶合格 `續棒理由：` ⇒ 放行
    n_before = len(be)
    r = _send(ctx, sb, aid, f"hello\n{reason}", low)
    ctx.check(r.rc == 0, f"互動帶理由回合 rc={r.rc}")
    tr = ctx.transcript(sb)
    be2 = _hook_errors(tr, "SendMessage")
    ctx.check(len(be2) == n_before, f"帶 `續棒理由：` 仍被擋：{be2[n_before:]}")
    trace = sb.root / "traces" / "autosdd_session_switch.jsonl"
    rows = [json.loads(x) for x in trace.read_text(encoding="utf-8").splitlines()] if trace.is_file() else []  # noqa: E501
    ctx.check(any(x.get("event") == "resume_gate_override" for x in rows),
              f"沒有 resume_gate_override 痕跡（痕跡事件={[x.get('event') for x in rows]}）")
    ctx.check(any(x.get("event") == "resume_gate_block" for x in rows), "沒有 resume_gate_block 痕跡")  # noqa: E501
    ctx.evidence(f"RV-M1 {sb.sid[:8]}:{be[0][0]} 無人擋；:{cold[0][0]} 互動冷擋；帶理由放行（override 痕跡）")  # noqa: E501


@case("RV-M2", "sessionctl_gates")
def rv_m2(ctx: CaseContext) -> None:
    """收斂閘（R216）：主控上下文達硬線（env 下修）⇒ Agent 派工被擋，**不需要出聲閂鎖**（D12）；
    反向：出廠硬線（85 萬）下同樣派工放行。"""
    sb = ctx.sandbox()
    _install_guard(sb)
    env = {"AUTOSDD_SWITCH_HARD_CTX_TOKENS": "1"}
    # 反向：出廠硬線（85 萬）⇒ 放行
    r = ctx.run_claude(sb, _ECHO_AGENT, extra_args=BYPASS, timeout_s=300)
    ctx.check(r.rc == 0, f"出廠硬線回合 rc={r.rc}")
    ctx.check(not _hook_errors(ctx.transcript(sb), "Agent"), "出廠硬線下就被收斂閘擋了（25 萬換窗沒拿乾淨）")  # noqa: E501
    ctx.check(len(_subagent_files(sb)) == 1, "出廠硬線回合沒有真的派出代理")
    hd = sb.home / "handoff"  # 交接包居所＝沙盒自己的（Sandbox.env 的 AUTOSDD_HANDOFF_DIR；REQ-SE-23）  # noqa: E501
    ctx.check(not (hd.is_dir() and list(hd.glob(f"{sb.sid}*.advised"))), "前提：沒有任何出聲閂鎖（D12 不依賴它）")  # noqa: E501
    r = ctx.run_claude(sb, _ECHO_AGENT, extra_args=BYPASS, env_extra=env, timeout_s=300)
    ctx.check(r.rc == 0, f"硬線下修回合 rc={r.rc}")
    tr = ctx.transcript(sb)
    be = _hook_errors(tr, "Agent")
    ctx.check(bool(be) and "收斂閘" in be[0][1], f"達硬線（未出聲）沒有擋 Agent 派工（hook error={be}）")  # noqa: E501
    ctx.check(len(_subagent_files(sb)) == 1, "被擋後仍多出代理檔（擋失效）")
    trace = sb.root / "traces" / "autosdd_session_switch.jsonl"
    ctx.check(trace.is_file() and "converge_block" in trace.read_text(encoding="utf-8"), "沒有 converge_block 痕跡")  # noqa: E501
    ctx.evidence(f"RV-M2 {sb.sid[:8]}:{be[0][0]} 無出聲閂鎖仍擋 Agent；出廠硬線放行")


_ = re
