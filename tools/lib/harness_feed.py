"""D32b-2（DEF-200-275 第七輪修後複審 Q-1）：狀態列 feed 的合併與 `--check` 旁註，
從 `tools/session_resume_planner.py` 抽出——那支檔的 `guardrail_cli` tier（≤750
計價行）本輪破線（760），本檔是抽走的那一份職責，不是新主題。

stdlib only（同 `tools/lib/endurance_env.py` 的既有慣例）：不 import
`context_budget_guard`，一律由呼叫端注入（`guard` 參數）。理由同該檔既有的
`_AUTOCOMPACT_KILL_ENVS` 說明——這裡只是「怎麼合併證據／怎麼印旁註」這個主題
的家，不是第二個知道怎麼判定 window 的地方；也讓根層 hook 的零相依契約不必
反過來 import 本檔。
"""
from __future__ import annotations

from pathlib import Path


def measure(transcript: Path, guard) -> dict:
    """水位量測（純資料）。判定一律走 `guard`（`context_budget_guard`）的實作，
    本檔不重寫一份判準。

    `feed` 只讀一次（D32b-1a 同型修復）：`guard.window_evidence()` 收下已讀好的
    `feed`，不再自己重讀一次 status line 進料。
    """
    used, peak, model = guard.scan_transcript(transcript)
    sid = guard.session_id_of(transcript)
    feed = guard.read_context_feed(sid, model)
    window, source = guard.resolve_window(
        peak, **guard.window_evidence(model, feed=feed))
    return {
        "session_id": sid,
        "transcript": str(transcript),
        "used": used,
        "peak_used": peak,
        "model": model,
        "window": window,
        "window_source": source,
        "harness_used": feed["used"],
        "harness_reason": feed["reason"],
        "may_block": guard.may_block(source),
        "ratio": (used / window) if (used is not None and window > 0) else None,
        "tier": guard.tier_of(used, window) if used is not None else None,
    }


def check_lines(data: dict) -> list[str]:
    """`--check` 要印的 harness 相關旁註（D32-4／D32b-3，一份判準給 CLI 與 hook 共用
    的道理見 `context_budget_guard.cross_check_note()`）：feed 有可比的 `used` 時印
    分子交叉比對；沒有時把 `harness_reason` 印出來（沒有 feed 也是一種 reason，不
    得被悄悄吞掉）。兩者互斥（`harness_used` 有值時 `harness_reason` 恆為 `None`，
    見 `context_budget_guard.read_context_feed()`）。
    """
    if data.get("harness_used") is not None and data.get("used") is not None:
        diff = abs(data["harness_used"] - data["used"])
        return [f"harness used={data['harness_used']:,} 逐字稿 used={data['used']:,} 差={diff:,}"]
    if data.get("harness_reason"):
        return [f"harness feed 未採用：{data['harness_reason']}"]
    return []
