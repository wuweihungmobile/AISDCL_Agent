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

#: DEF-200-408：差值非 0 最常見的成因是 feed 與逐字稿**各自獨立落盤**的時序差——status line
#: 先把新一則的 usage 寫進 feed，逐字稿那一則 assistant 記錄還沒寫完，下一次呼叫即歸零
#: （Windows 真機實測：一次印 差=15,580 ＝該則的 cache_creation，下一次 差=0）。少了這句，
#: 一個瞬間差值會被讀成「數字不符＝新缺陷」；差=0 時不附，免得每次都多一截噪音。
DIFF_HINT = "（差值非 0 常見於 feed 與逐字稿寫入時序差，下一次呼叫通常歸零；持續非 0 才需查）"


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

    🔴 R158（refute_q3q4ci.md §1a／§1d 反駁者實測）：compact 後、下一次 API 回應前的 round-label-ok
    空窗（官方契約 `current_usage: null`）會讓 `read_context_feed()` 同時回
    `used=None, reason=None`——這是該函式**唯一**兩欄同時為 `None` 的分支（其餘每一個
    「不採用」分支都會賦一個非空 `reason` 字串，見該函式最後一行與上面兩行對照）。
    此前這個分支落到 `return []`，連「不採用」這件事本身都被悄悄吞掉，違反本函式與
    `read_context_feed()` 自己 docstring 的設計意圖——現在補一行明講原因。
    """
    if data.get("harness_used") is not None and data.get("used") is not None:
        diff = abs(data["harness_used"] - data["used"])
        line = f"harness used={data['harness_used']:,} 逐字稿 used={data['used']:,} 差={diff:,}"
        return [line + (DIFF_HINT if diff else "")]
    if data.get("harness_reason"):
        return [f"harness feed 未採用：{data['harness_reason']}"]
    if data.get("harness_used") is None and data.get("harness_reason") is None:
        return ["harness feed 存在但當下無 current_usage（compact 後空窗），本次無交叉比對"]
    return []


def active_model_of(transcript: Path | None, guard) -> str | None:
    """DEF-200-420：本 session 逐字稿最後跑過的模型家族字——與 PreToolUse hook
    （`context_budget_guard.py` 的 `active_model = model_family(scanned[2]) if
    scanned and scanned[2] else None`）同一組轉換規則，讓 `--pace` 與守衛看同一把尺。
    此前 `--pace` 沒有這一步，模型分軌軸（`MODEL_SCOPED_KINDS`）就一律被排除出 cap
    聚合，給出比守衛寬鬆的假數字（同一份快取下 `--pace` 與 `--pace --model fable`
    七軸讀數逐字相同，差異全來自 active_model 有無）。

    `transcript` 為 `None`／不是檔案，或掃描途中出任何例外，一律回 `None`（fail-soft：
    解不出就維持既有「不確定 → 保守排除」行為，不用猜的頂替）。呼叫端的顯式 `--model`
    優先於本函式——本函式只補「沒給 `--model` 時」的自動推導。
    """
    if transcript is None:
        return None
    try:
        if not transcript.is_file():
            return None
        _, _, seen_model = guard.scan_transcript(transcript)
        return guard.model_family(seen_model) or None if seen_model else None
    except Exception:
        return None
