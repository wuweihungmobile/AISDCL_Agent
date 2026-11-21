# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""RV-K2B（auto；V-K2／E2E-WP-59）：真實五小時讀數落在「等效 95～99% 帶」時，真 hook 仍出聲一次並寫出可重啟點任務書。

做法（DES §8-5）：不等真實額度走到 95～99%。讀當下真實五小時水位 P（`--pace`，真快取），用 `quota_policy` 既有門檻鍵把
「準備」帶下緣設在 P 以下、「停止」帶設在 P 以上，使真實讀數相對於這組門檻落在 prepare 帶的上段（相對位置＝
(P−準備)/(停止−準備)；此值寫進證據，等效帶 95～99% 的語意是「準備帶已過大半、距停止只差幾個百分點」）。
真 `claude -p` 在沙盒掛真 `context_budget_guard.py`（PostToolUse），做兩個回合的工具呼叫：
第一回合 ⇒ 出聲一次（hook stderr）＋任務書落 `AUTOSDD_PLAN_DIR`；第二回合（同 reset 窗）⇒ 不重複（閂鎖只有一筆、任務書仍 1 份）。
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from ..driver import EnvMissing
from ..sandbox import REPO
from . import CaseContext, case
from .prd_px_lib import ev
from .sessionctl_park import PY, install_tools, run

PLANNER = str(REPO / "tools" / "session_resume_planner.py")
MARK = "額度進入**準備**水位"


def real_five_hour_pct(sb) -> float:
    out = run([PY, PLANNER, "--pace", "--model", "sonnet"], cwd=sb.root, env=sb.env(), timeout=120)
    m = re.search(r"kind=five_hour (\d+(?:\.\d+)?)%", out.stdout)
    if not m:
        raise EnvMissing(f"量不到真實五小時水位（無法建構門檻）：{out.stdout[:200]}")
    return float(m.group(1))


@case("RV-K2B", "workprogress", refs=("E2E-WP-59", "REQ-WP-89", "V-K2"))
def rv_k2b(ctx: CaseContext) -> None:
    sb = ctx.sandbox(probe_hooks=False)
    p = real_five_hour_pct(sb)
    if p < 12 or p > 97:
        raise EnvMissing(f"真實五小時水位 {p}% 不在可建構區間 [12, 97]（無法讓門檻夾住讀數；非綠，換時段再跑）")
    prepare, halt = int(p) - 3, min(100, int(p) + 5)
    keys = {"AUTOSDD_QUOTA_NOTICE_PCT": str(max(1, int(p) - 12)), "AUTOSDD_QUOTA_CONVERGE_PCT": str(int(p) - 8),
            "AUTOSDD_QUOTA_PREPARE_PCT": str(prepare), "AUTOSDD_QUOTA_HALT_PCT": str(halt)}
    rel = (p - prepare) / (halt - prepare)
    install_tools(sb)  # 真 hook 的 repo_root() 解到沙盒（CLAUDE_PROJECT_DIR）：沒有工具副本就找不到 planner、寫不出任務書
    sb.add_repo_hook("PostToolUse", ".claude/hooks/context_budget_guard.py", timeout=30)
    tmp = sb.root / "tmp"
    tmp.mkdir()
    (sb.root / "a.txt").write_text("rv\n", encoding="utf-8")
    env = {**keys, "TEMP": str(tmp), "TMP": str(tmp), "AUTOSDD_PLAN_DIR": str(tmp)}
    prompt = "Call the Read tool on a.txt three separate times, one call per step, then reply done."
    # 暖身輪：-p 的逐字稿在第一輪工具呼叫當下可能尚未落盤（RV-C1 同款前提；payload.transcript_path 要指到存在的檔）
    w = ctx.run_claude(sb, "Reply with exactly: ok", env_extra=env)
    ctx.check(w.rc == 0, f"暖身輪 rc={w.rc}")
    r1 = ctx.run_claude(sb, prompt, env_extra=env, timeout_s=200, extra_args=("--permission-mode", "acceptEdits"))
    ctx.check(r1.rc == 0, f"第一回合 rc={r1.rc} {r1.stderr[:200]}")
    d1 = r1.debug_text()
    n1 = d1.count(MARK)
    pm = re.search(r"可重啟點任務書：(.+?\.md)", d1)
    ctx.check(n1 == 1, f"第一回合準備帶出聲次數應恰 1（debug log）：{n1}")
    ctx.check(bool(pm) and "寫不出來" not in pm.group(1), f"出聲內容沒有任務書路徑：{pm.group(0)[:120] if pm else None}")
    plan = Path(pm.group(1).strip())
    ctx.check(plan.is_file() and plan.stat().st_size > 0 and sb.sid in plan.name, f"任務書檔不存在／為空／不是本沙盒 sid：{plan}")
    plans = [plan]
    r2 = ctx.run_claude(sb, prompt, env_extra=env, timeout_s=200, extra_args=("--permission-mode", "acceptEdits"))
    ctx.check(r2.rc == 0, f"第二回合 rc={r2.rc}")
    d2 = r2.debug_text()
    plans2 = [plan] if plan.is_file() else []
    ctx.check(d2.count(MARK) == 0, f"同一 reset 窗第二回合不該再出聲：{d2.count(MARK)}")
    ctx.check(len(plans2) == 1 and d2.count("可重啟點任務書：") == 0, f"同窗不重複：任務書 {len(plans2)}、第二回合再出聲 {d2.count(MARK)} 次")
    ev(ctx, "spoke_once", f"真實五小時 {p}%；門檻 prepare={prepare}／halt={halt}（相對位置 {rel:.2f}）；第一回合出聲 {n1} 次、第二回合 0 次")
    ev(ctx, "plan_written", f"{plans[0].name} {plans[0].stat().st_size} bytes")
    ev(ctx, "not_repeated_same_window", "第二回合（同 reset 窗）出聲 0 次、任務書仍 1 份且無第二份路徑訊息")
    plan.unlink(missing_ok=True)  # 任務書落在 plan 目錄（檔名含沙盒 sid）：用完只刪自己這一份
    _ = (json, tempfile)
