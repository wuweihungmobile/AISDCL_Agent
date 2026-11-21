# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""workprogress 家族（真 `claude -p`）：RV-L3（守衛推回／擋下／轉送送達 harness）、RV-PB1（無人 print 模式
背景上限）、RV-WB1（網頁讀取不進派發帳）。全部沙盒＋真 hook 子行程；證據鍵走 `ev()`。"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from ..sandbox import REPO
from . import CaseContext, case
from .prd_px_lib import ev
from .sessionctl_handoff import (
    backdate_transcript,
    blocking_texts,
    install_sessionctl,
    kill_verified,
    sc_env,
    seal_session,
    set_ctx,
    spawn_trace,
)
from .sessionctl_park import PY, axis, run, write_quota
from .sessionctl_watch import _tool_result_texts
from .wp_lib import tool_uses


def pre_errors(tr) -> list[tuple[int, str]]:
    """PreToolUse 阻斷在逐字稿的形態＝該工具呼叫的 tool_result 文字含 `PreToolUse:<tool> hook error`。"""
    return [(ln, t) for ln, t in _tool_result_texts(tr) if "PreToolUse:" in t and "hook error" in t]


AGENT_PROMPT = ("Call the Agent tool exactly once (subagent_type general-purpose, prompt: reply with the word ok). "
                "If the call is blocked or fails, do NOT retry and do NOT try another way: just reply BLOCKED. Otherwise reply DONE.")


@case("RV-L3", "workprogress", refs=("E2E-WP-18", "REQ-WP-52", "V-SS4", "V-PK4", "V5", "V-W2", "V-C2", "V-F1"))
def rv_l3(ctx: CaseContext) -> None:
    """產品守衛的訊息真的送達 harness（逐字稿機驗）：①Stop 封存閘推回＝`hook_blocking_error`（含「封存閘」「--finalize」）
    ＋`stop_hook_summary`；②PreToolUse 擋 `Agent`（主控上下文達硬線）＝`hook_blocking_error`（hookEvent＝PreToolUse，
    含守衛字樣）；③UserPromptSubmit 轉送＝擋下記錄含「已轉到新 session」。畫面渲染另由 RV-UI1 承接。"""
    sb = ctx.sandbox()
    install_sessionctl(sb)
    low = sc_env(sb, AUTOSDD_SWITCH_HARD_CTX_TOKENS="1000")
    r0 = ctx.run_claude(sb, "Reply with exactly: RV_L3_WARM", env_extra=sc_env(sb))
    ctx.check(r0.rc == 0, f"暖身輪 rc={r0.rc}")
    # ① Stop
    r1 = ctx.run_claude(sb, "Reply with exactly: RV_L3_STOP", env_extra=low)
    ctx.check(r1.rc == 0 and not r1.timed_out, f"Stop 回合 rc={r1.rc}")
    tr = ctx.transcript(sb)
    stops = [t for t in blocking_texts(tr, "Stop") if "封存閘" in t]
    ctx.check(len(stops) == 1 and "--finalize" in stops[0], f"Stop 推回應恰 1 次且含 --finalize：{[t[:60] for t in blocking_texts(tr, 'Stop')]}")  # noqa: E501
    ctx.check(any(s.data.get("hookErrors") for s in tr.stop_hook_summaries()), "stop_hook_summary 沒帶 hookErrors")
    ev(ctx, "stop_block_delivered", f"{tr.coords(tr.hook_blocking_errors('Stop', '封存閘')[0])} hook_blocking_error(Stop) 含 --finalize")  # noqa: E501
    # ② PreToolUse
    # 另一個沙盒只掛 PreToolUse 守衛：同一硬線下 Stop 封存閘會把模型帶去做交接，與本段無關
    sb3 = ctx.sandbox()
    install_sessionctl(sb3, guard_events=())
    sb3.add_hook("PreToolUse", sb3.root / ".claude" / "hooks" / "sessionctl_guard.py", matcher="Agent|Task|Workflow", timeout=30)
    w3 = ctx.run_claude(sb3, "Reply with exactly: RV_L3_WARM3", env_extra=sc_env(sb3))
    ctx.check(w3.rc == 0, f"暖身輪 rc={w3.rc}")
    r2 = ctx.run_claude(sb3, AGENT_PROMPT, env_extra=sc_env(sb3, AUTOSDD_SWITCH_HARD_CTX_TOKENS="1000"), timeout_s=200, extra_args=("--permission-mode", "bypassPermissions"))  # noqa: E501
    ctx.check(r2.rc == 0, f"PreToolUse 回合 rc={r2.rc} {r2.stderr[:200]}")
    tr = ctx.transcript(sb3)
    pre = [t for _, t in pre_errors(tr)]
    ctx.check(bool(pre) and any("Agent" in t or "硬線" in t or "封存" in t or "交接" in t for t in pre), f"PreToolUse 沒有擋 Agent（無 `PreToolUse:<tool> hook error` 的 tool_result）：{pre[:2]}；工具={[n for _, n, _ in tool_uses(tr)]}")  # noqa: E501
    ev(ctx, "pretooluse_block_delivered", f"tool_result 含 `PreToolUse:Agent hook error` 守衛字樣 {pre[0][:80]!r}")
    # ③ UserPromptSubmit 轉送（冷窗＋大上下文）；視窗卡信任框不等，收掉即可
    sb2 = ctx.sandbox()
    pkg = seal_session(ctx, sb2)
    try:
        tp = ctx.transcript(sb2).path
        set_ctx(tp, 600_000)
        backdate_transcript(tp, 3)
        r3 = ctx.run_claude(sb2, "RV_L3_FORWARD 這是掌舵者原文", env_extra=sc_env(sb2), timeout_s=150)
        ctx.check(r3.rc == 0, f"轉送回合 rc={r3.rc}")
        t3 = ctx.transcript(sb2)
        blk = t3.blocked_user_prompts("已轉到新 session")
        ctx.check(bool(blk), "UserPromptSubmit 轉送擋下記錄不存在")
        ev(ctx, "ups_forward_delivered", f"{t3.coords(blk[0])} informational/preventContinuation 含「已轉到新 session」（{pkg.name[:8]}）")  # noqa: E501
    finally:
        for row in spawn_trace(sb2, "session_switch_spawned"):
            if isinstance(row.get("pid"), int):
                kill_verified(row["pid"], sb2.sid)
        time.sleep(2)


@case("RV-PB1", "workprogress", refs=("E2E-WP-14", "REQ-WP-49", "ADR-XPLAT-004-§2.12"))
def rv_pb1(ctx: CaseContext) -> None:
    """真 `claude -p` 帶 `resume_route.spawn_env()` 的背景等待上限鍵：①鍵值＝`unattended_authz` SSOT 換算毫秒
    （真函式、子行程回讀）；②背景 shell 睡超過上限時行程在上限＋裕度內結束、stderr 帶 harness 停掉背景任務的標記。
    🔴 SSOT 值是 4 小時，不可能真等；所以②用同一個環境鍵、改成 20 秒（證明 harness 真的讀這個鍵並有序收尾），
    ①另釘正式值。這是縮「參數」而非縮「判準」，並在證據標明。"""
    sb = ctx.sandbox(probe_hooks=False)
    code = ("import sys,json;sys.path.insert(0,sys.argv[1]+'/tools/lib');sys.path.insert(0,sys.argv[1]+'/tools');"
            "import resume_route,unattended_authz as u;print('J='+json.dumps({'env':resume_route.spawn_env(),'k':u.HARNESS_BG_WAIT_ENV,'s':u.RESUME_BG_WAIT_CEILING_SECONDS}))")  # noqa: E501
    out = run([PY, "-c", code, str(REPO)], cwd=sb.root, env=sb.env(), timeout=60)
    m = re.search(r"^J=(.*)$", out.stdout, re.M)
    ctx.check(out.returncode == 0 and bool(m), f"spawn_env 子行程失敗：{out.stderr[-300:]}")
    j = json.loads(m.group(1))
    ctx.check(j["env"].get(j["k"]) == str(j["s"] * 1000), f"spawn_env 的上限鍵應＝SSOT×1000：{j}")
    ev(ctx, "spawn_env_ceiling", f"{j['k']}={j['env'][j['k']]}（SSOT {j['s']} 秒）")
    ceiling_ms = 30_000
    # DEF-200-575 的暴露形態是「背景子代理」（QA 鏡）。CLI 2.1.329 實測：背景 *shell* 不受此上限管
    # （本體 park() 在 holdForBackgroundShells 旗標開時對存活的背景 shell 豁免；兩次真跑 ping 睡 100／120 秒
    # 都等到它自然結束，上限 20／40 秒沒有生效），子代理仍受管。故本案例用背景子代理，shell 行為只記為觀察。
    prompt = ("Call the Agent tool exactly once with run_in_background=true, subagent_type general-purpose, prompt: "
              "'Run the shell command ping -n 101 127.0.0.1 and then reply done'. Do NOT wait for it. "
              "Then end your turn immediately with LAUNCHED.")
    t0 = time.monotonic()
    r = ctx.run_claude(sb, prompt, env_extra={j["k"]: str(ceiling_ms)}, timeout_s=230, extra_args=("--permission-mode", "bypassPermissions"))  # noqa: E501
    took = time.monotonic() - t0
    ctx.check(not r.timed_out, f"行程沒有在牆鐘內結束（上限鍵沒生效？）took={took:.0f}s")
    names = [n for _, n, _ in tool_uses(ctx.transcript(sb))]
    ctx.check("Agent" in names, f"模型沒有派背景子代理：{names}")
    ctx.check(took < 95, f"行程應在上限 30 秒＋回合時間內結束，不是等滿 100 秒的子代理：took={took:.0f}s")
    ctx.check("Background tasks still running" in r.stderr, f"stderr 沒有 harness 停掉背景任務的標記：{r.stderr[-200:]!r}")
    ev(ctx, "ended_within_ceiling", f"took={took:.0f}s（ceiling={ceiling_ms // 1000}s、背景子代理要 100s）rc={r.rc}")
    ev(ctx, "harness_kill_mark", "stderr 含「Background tasks still running … stopping them」")
    ctx.notes.append("觀察：CLI 2.1.329 背景 shell 不受 PRINT_BG_WAIT_CEILING 管（見 docstring）；無人窗口若靠背景 shell 等待會無上限")  # noqa: E501


@case("RV-WB1", "workprogress", refs=("E2E-WP-15", "REQ-WP-50", "ADR-XPLAT-004-§2.16"))
def rv_wb1(ctx: CaseContext) -> None:
    """沙盒掛真 `context_budget_guard.py`（PreToolUse）＋額度 converge 帶（cap 2）：真 `claude -p` 連續 WebFetch×2／
    WebSearch×1 再 Agent。判準：Web 三次沒有一次被扇出節流擋；Agent 沒被擋（若 Web 入帳，cap=2 早被吃光）；
    派發帳（沙盒 TEMP 的 `fanout` 目錄項）只多 Agent 那 1 筆。對照組同帶連派 3 次 Agent ⇒ 第 3 次被擋（證明 cap
    真的在管、斷言不是恆真）。"""
    sb = ctx.sandbox(probe_hooks=False)
    sb.add_repo_hook("PreToolUse", ".claude/hooks/context_budget_guard.py", matcher="Task|WebFetch|WebSearch|Agent|Workflow", timeout=30)  # noqa: E501
    tmp = sb.root / "tmp"
    tmp.mkdir()
    write_quota(sb, [axis("five_hour", 65, 200)])
    env = {"AUTOSDD_QUOTA_CACHE_DIR": str(sb.root / "qcache"), "TEMP": str(tmp), "TMP": str(tmp)}
    prompt = ("First call ToolSearch with query select:WebFetch,WebSearch so those tools are loaded. Then call, one call per step: "
              "WebSearch query alpha-example, WebSearch query bravo-example, WebFetch https://example.com (prompt: title). "
              "Then call the Agent tool exactly once (subagent_type general-purpose, prompt: reply ok). If any call is blocked or fails, do NOT retry; just continue with the next step. Then reply DONE.")
    r = ctx.run_claude(sb, prompt, env_extra=env, timeout_s=230, extra_args=("--permission-mode", "bypassPermissions"))  # noqa: E501
    ctx.check(r.rc == 0 and not r.timed_out, f"回合 rc={r.rc} timed_out={r.timed_out} {r.stderr[:200]}")
    tr = ctx.transcript(sb)
    names = [n for _, n, _ in tool_uses(tr)]
    webs = [n for n in names if n in ("WebFetch", "WebSearch")]
    ctx.check(len(webs) >= 2 and "Agent" in names, f"模型沒照順序呼叫（Web {len(webs)} 次、Agent {'有' if 'Agent' in names else '無'}）：{names}")  # noqa: E501
    throttled = [t for _, t in pre_errors(tr) if "扇出" in t]
    ctx.check(not throttled, f"Web／Agent 被扇出節流擋下（Web 又入帳了？）：{throttled[:2]}")
    ents = [p for p in tmp.rglob("*") if p.is_file() and re.match(r"^\d+-", p.name)]
    ctx.check(len(ents) == names.count("Agent"), f"派發帳筆數應＝Agent 呼叫數：帳 {len(ents)} 筆、Agent {names.count('Agent')} 次")  # noqa: E501
    ev(ctx, "web_not_in_ledger", f"Web {len(webs)} 次、帳 {len(ents)} 筆＝Agent {names.count('Agent')} 次；扇出節流擋下 0 次")
    # 對照：同帶連派 3 次 Agent，第 3 次應被擋（cap=2）
    sb2 = ctx.sandbox(probe_hooks=False)
    sb2.add_repo_hook("PreToolUse", ".claude/hooks/context_budget_guard.py", matcher="Task|WebFetch|WebSearch|Agent|Workflow", timeout=30)  # noqa: E501
    tmp2 = sb2.root / "tmp"
    tmp2.mkdir()
    write_quota(sb2, [axis("five_hour", 65, 200)])
    env2 = {"AUTOSDD_QUOTA_CACHE_DIR": str(sb2.root / "qcache"), "TEMP": str(tmp2), "TMP": str(tmp2)}
    p2 = ("Call the Agent tool three times in sequence (each: subagent_type general-purpose, prompt: reply ok), "
          "one call per step. If any call is blocked or fails, do NOT retry; just continue with the next step. Then reply DONE.")
    r2 = ctx.run_claude(sb2, p2, env_extra=env2, timeout_s=230, extra_args=("--permission-mode", "bypassPermissions"))
    ctx.check(r2.rc == 0, f"對照回合 rc={r2.rc}")
    t2 = ctx.transcript(sb2)
    n_agent = [n for _, n, _ in tool_uses(t2)].count("Agent")
    thr2 = [t for _, t in pre_errors(t2) if "扇出" in t]
    ctx.check(n_agent >= 3 and bool(thr2), f"對照組連派 {n_agent} 次 Agent 應有 ≥1 次被扇出節流擋：{thr2[:1]}")
    ev(ctx, "control_agent_throttled", f"連派 Agent {n_agent} 次、被擋 {len(thr2)} 次（cap=2）")
    _ = (Path, install_sessionctl)
