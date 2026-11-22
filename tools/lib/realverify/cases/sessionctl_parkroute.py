"""sessionctl_parkroute 家族：park 到點選路 F4（R216 WP-F；TCS-SessionSwitch-CostModel REQ-SS-19、
E2E-SS-14 的選路部分）。

載具：工具副本沙盒（見 `sessionctl_park` 模組 docstring）＋真 `claude -p` 產的沙盒逐字稿（只改
**沙盒自己**的 usage 數字與時間戳）＋真 schtasks 登記的 park job ＋真行程跑 job 本體
`sessionctl.py park --fire`（排程器到點會跑的同一條命令列）。

🔴 劃界（誠實）：到點「真的開出 `claude -r <sid>` 互動視窗並續寫原逐字稿」不在本家族——新目錄的互動
claude 會卡 folder trust 對話框，且本輪禁止再開窗（同 RV-K1 的劃界）。所以 job 本體以
`AUTOSDD_SESSION_SWITCH_MODE=notify` 跑：選路、痕跡、失敗 handback 全是真的，只有最後「開窗」那一步被
模式圍籬擋下（拒絕訊息與 rc 都是真的被測行為）。開窗那一步由掌舵者目視（V-SS5）。
`claude -p -r <sid> "<提示>"` 的 argv 形態（-r 後接 sid、提示為位置參數）已由 RV-K2 的真 `-r` 呼叫驗過。
單案 token：一個真 `claude -p`（haiku、一句回覆；≤ 約 1 萬）。
"""  # noqa: E501
from __future__ import annotations

from ..sandbox import Sandbox
from . import CaseContext, case
from .sessionctl_handoff import set_ctx
from .sessionctl_park import (
    claude_procs,
    ctl,
    get_task,
    install_tools,
    park_arm,
    park_cleanup,
    read_marker,
    trace_lines,
    transcript_path,
)

_COLD_HOURS = 3  # 逐字稿時間戳往前推：快取已冷（>1h）且遠超 15 分鐘的「有人在動」寬限
_NOTIFY = {"AUTOSDD_SESSION_SWITCH_MODE": "notify"}  # 擋下「開窗」這最後一步（見模組劃界）
_F4_FACTORY = {"AUTOSDD_SWITCH_FRESH_COST_UNITS": "480000", "AUTOSDD_SWITCH_CONTEXT_VALUE_Q": "1"}


def _fire(ctx: CaseContext, sb: Sandbox, ctx_tokens: int, why: str):
    """arm（真 schtasks）→ 改沙盒逐字稿上下文 → 以真行程跑 job 本體；回 (fire 結果, 標記, 路徑)。"""
    pkg, mk = park_arm(ctx, sb, lead_s=300, age_s=_COLD_HOURS * 3600, why=why)
    label = mk["jobs"][0]["label"]
    ctx.check(get_task(label) is not None, f"fire 前排程器查不到 {label}（arm 沒真的掛上）")
    tpath = transcript_path(sb)
    ctx.check(set_ctx(tpath, ctx_tokens) >= 1, "逐字稿沒有帶 usage 的 assistant 記錄可改")
    r = ctl(sb, "park", "--fire", "--job", label, "--session-id", sb.sid, "--pkg", str(pkg),
            "--fire-at", mk["fire_at"], extra={**_NOTIFY, **_F4_FACTORY})
    return r, mk, label


def _route_event(ctx: CaseContext, sb: Sandbox) -> dict:
    rows = [r for r in trace_lines(sb.root / "traces", "autosdd_session_switch.jsonl", sb.sid)
            if r.get("event") == "park_route"]
    ctx.check(len(rows) == 1, f"park_route 痕跡應恰一筆：{rows}")
    return rows[0]


@case("RV-PR1", "sessionctl_parkroute", refs=("REQ-SS-19", "E2E-SS-14"), sched=True)
def rv_pr1(ctx: CaseContext) -> None:
    """快取已冷（3 小時）＋上下文 17 萬：續跑重寫 34 萬 < 換新 96 萬 ⇒ job 選 RESUME（痕跡
    `park_route route=RESUME ctx=170000`），走續跑路（拒絕訊息指向 `claude -r`、痕跡
    `park_resume_failed`、**沒有** `park_spawned`）；標記 failed、失敗 handback 寫明「續跑原 session」；
    job 自拆（排程器查不到）；沒有任何含沙盒 sid 的 claude 行程。舊判準（R3／一律 spawn）會走交接包。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    with park_cleanup(sb):
        r, _mk, label = _fire(ctx, sb, 170_000, "realverify PR1 小上下文續跑")
        ctx.check(r.returncode == 1, f"notify 模式下續跑開窗被擋，job 應 rc 1：rc={r.returncode} {r.stderr[-300:]}")  # noqa: E501
        ev = _route_event(ctx, sb)
        ctx.check(ev["route"] == "RESUME" and ev["ctx"] == 170_000, f"選路不符（要 RESUME、ctx 170000）：{ev}")  # noqa: E501
        ctx.check("續跑重寫" in ev["why"] and "換新" in ev["why"], f"理由缺兩個成本數字：{ev['why']}")  # noqa: E501
        base = sb.root / "traces"
        names = {x["event"] for x in trace_lines(base, "autosdd_session_switch.jsonl", sb.sid)}
        ctx.check("park_resume_failed" in names and "park_spawned" not in names, f"痕跡不符：{names}")  # noqa: E501
        ctx.check("claude -r" in r.stderr, f"拒絕訊息沒有指向 claude -r：{r.stderr[-300:]}")
        mk2 = read_marker(sb.sid, base)
        ctx.check(mk2 and mk2["status"] == "failed", f"標記應為 failed：{mk2 and mk2['status']}")
        hb = next((p for p in ((sb.home / "handback").glob(f"{sb.sid}_park_failed.md"))), None)
        ctx.check(hb is not None and "續跑原 session" in hb.read_text(encoding="utf-8"), "沒有寫明續跑路的失敗 handback")  # noqa: E501
        ctx.check(get_task(label) is None, "job 沒有自拆（排程器仍查得到）")
        ctx.check(not claude_procs(sb.sid), "不該有任何含沙盒 sid 的 claude 行程（本案例不開窗）")
        ctx.evidence(f"RV-PR1 {sb.sid[:8]} 冷＋170,000 ⇒ route=RESUME；{ev['why']}；job 自拆；標記 failed（開窗被 notify 擋）")  # noqa: E501


@case("RV-PR2", "sessionctl_parkroute", refs=("REQ-SS-19", "E2E-SS-14"), sched=True)
def rv_pr2(ctx: CaseContext) -> None:
    """反向：同樣冷快取、上下文 60 萬：續跑重寫 120 萬 > 換新 96 萬 ⇒ job 選 FRESH（`park_route
    route=FRESH`，理由含 F4），走既有交接包 spawn 路（痕跡 `park_spawn_failed`、沒有 `park_resume_*`、
    拒絕訊息指向交接包而不是 `claude -r`）。同一支程式、只差上下文大小，選路必須翻轉。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    with park_cleanup(sb):
        r, _mk, label = _fire(ctx, sb, 600_000, "realverify PR2 大上下文換新")
        ctx.check(r.returncode == 1, f"notify 模式下開窗被擋，job 應 rc 1：rc={r.returncode} {r.stderr[-300:]}")  # noqa: E501
        ev = _route_event(ctx, sb)
        ctx.check(ev["route"] == "FRESH" and ev["ctx"] == 600_000 and "F4" in ev["why"], f"選路不符（要 FRESH、含 F4）：{ev}")  # noqa: E501
        names = {x["event"] for x in trace_lines(sb.root / "traces", "autosdd_session_switch.jsonl", sb.sid)}  # noqa: E501
        ctx.check("park_spawn_failed" in names and not {n for n in names if n.startswith("park_resume")}, f"痕跡不符：{names}")  # noqa: E501
        ctx.check("交接包" in r.stderr or "handoff" in r.stderr, f"拒絕訊息沒有指向交接包：{r.stderr[-300:]}")  # noqa: E501
        ctx.check(get_task(label) is None, "job 沒有自拆（排程器仍查得到）")
        ctx.check(not claude_procs(sb.sid), "不該有任何含沙盒 sid 的 claude 行程（本案例不開窗）")
        ctx.evidence(f"RV-PR2 {sb.sid[:8]} 冷＋600,000 ⇒ route=FRESH；{ev['why'][:80]}；job 自拆")


