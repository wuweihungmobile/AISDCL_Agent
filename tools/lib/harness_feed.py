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

import json
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

    `fresh_window`（DEF-200-425）＝新視窗首輪：逐字稿還沒有任何帶 usage 的 assistant 記錄（`used` 與
    `model` 皆 `None`），而 feed 這一側讀得通（`reason is None`＝存在、session 相符、window
    為正）。feed 有沒有 `current_usage` 不論：TUI 剛開時為 null；首輪自己的 `--check` 則實測
    遇到 feed 已有值、逐字稿仍無任何 usage 記錄（本機頂層逐字稿裡兩次真跑出 ❌ 的首輪
    `--check`，`check_lines()` 都回空，那只有 `harness_used` 非 None 才會發生；成因推測＝逐字稿
    要等整則回應收完才落盤，首輪的工具呼叫在那之前就跑了）。feed 不存在（reason 非空）分不出
    是新視窗還是欄位格式漂移 ⇒ 不算；逐字稿已見到 model 卻沒有可用 usage ⇒ 不算（格式漂移的
    警報要留著）。`endurance_env.check_report()` 只讀這個旗標，不 import 本檔。
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
        "fresh_window": (used is None and model is None and feed["reason"] is None
                         and not _has_any_assistant_record(transcript)),
        "may_block": guard.may_block(source),
        "ratio": (used / window) if (used is not None and window > 0) else None,
        "tier": guard.tier_of(used, window) if used is not None else None,
    }


def _has_any_assistant_record(transcript: Path) -> bool:
    """DEF-200-425 複審鏡 S1：`scan_transcript()` 只看含 `usage` 字樣的行，assistant 記錄若
    整個沒有 usage 鍵（欄位改名／只有 `<synthetic>` 記錄）`model` 也會是 None，`fresh_window`
    就把「欄位格式漂移」誤判成「新視窗」。這裡便宜地再掃一次：逐字稿裡**有任何** assistant
    記錄就不是新視窗（❌ 警報留著）。讀不到一律當「有」——方向是維持警報，不是靜音。"""
    try:
        with transcript.open(encoding="utf-8", errors="replace") as fh:
            return any('"type": "assistant"' in line or '"type":"assistant"' in line
                       for line in fh)
    except OSError:
        return True


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
    `read_context_feed()` 自己 docstring 的設計意圖——現在補一行明講原因。新視窗首輪
    （TUI 剛開、第一次 API 回應之前）同樣是 `current_usage: null`，措辭因此兩種成因並列，
    不把根本沒 compact 過的新視窗說成 compact 後空窗。
    """
    if data.get("harness_used") is not None and data.get("used") is not None:
        diff = abs(data["harness_used"] - data["used"])
        line = f"harness used={data['harness_used']:,} 逐字稿 used={data['used']:,} 差={diff:,}"
        return [line + (DIFF_HINT if diff else "")]
    if data.get("harness_reason"):
        return [f"harness feed 未採用：{data['harness_reason']}"]
    if data.get("harness_used") is None and data.get("harness_reason") is None:
        return ["harness feed 存在但當下無 current_usage"
                "（新視窗尚無第一次 API 回應，或 compact 後空窗），本次無交叉比對"]
    return []


def _feed_model_family(transcript: Path, guard) -> str | None:
    """DEF-200-424（DEF-200-420 延伸）：新視窗首輪逐字稿還沒有任何 assistant 記錄
    （`scan_transcript` 回不出 model），模型只有 status line feed 知道——feed 在 TUI 啟動時
    就寫了 `model.id`，`current_usage` 為 null 也一樣。`read_context_feed()` 的回傳沒有
    `model.id`（只回 `{window, note, used, reason}`），故這裡自己讀 feed 檔；路徑、sid、
    家族字一律走 `guard` 既有函式，`session_id` 比對式與 `read_context_feed()` 同一條。

    feed 不存在、壞 JSON、`session_id` 不符、缺 `model.id`、認不出家族一律回 `None`（fail-soft）。
    """
    sid = guard.session_id_of(transcript)
    try:
        doc = json.loads(guard.context_feed_path(sid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(doc, dict) or doc.get("session_id") != sid:
        return None
    model = doc.get("model")
    return (guard.model_family(model.get("id")) or None) if isinstance(model, dict) else None


def active_model_of(transcript: Path | None, guard) -> str | None:
    """DEF-200-420：本 session 逐字稿最後跑過的模型家族字——與 PreToolUse hook
    （`context_budget_guard.py` 的 `active_model = model_family(scanned[2]) if
    scanned and scanned[2] else None`）同一組轉換規則，讓 `--pace` 與守衛看同一把尺。
    此前 `--pace` 沒有這一步，模型分軌軸（`MODEL_SCOPED_KINDS`）就一律被排除出 cap
    聚合，給出比守衛寬鬆的假數字（同一份快取下 `--pace` 與 `--pace --model fable`
    七軸讀數逐字相同，差異全來自 active_model 有無）。

    逐字稿優先：它有 model 字串就以它為準（與 hook 同尺）；只有逐字稿還沒有任何 assistant
    記錄（新視窗首輪，hook 那一側此時也解不出）才退用 status line feed 的 `model.id`
    （`_feed_model_family`）。此前新視窗首輪 `--pace` 因此排除模型軸、印出比守衛寬鬆的
    cap，等到第一則回應落盤後 hook 才從逐字稿解到模型而收緊——同一個視窗前後兩種說法。

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
        if seen_model:
            return guard.model_family(seen_model) or None
        return _feed_model_family(transcript, guard)
    except Exception:
        return None
