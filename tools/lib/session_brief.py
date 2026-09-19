"""SessionStart 真實數字簡報（R158／P6；Q2「模型不查真實數據」的機制面）。 round-label-ok

WHY：`context_budget_guard.py` 檔頭原話——「根層 `context_budget_guard.py` 在
SessionStart 只做 `arm_sentinel` 與 handback 宣告，不量測、不出聲」——新開的 session
在第一次工具呼叫之前，模型手上完全沒有真實水位數字，只能靠自己想到要跑
`--check`／`--pace`（R158 主控裁決書〈P6〉節）。本檔把「組出這一行簡報」的邏輯抽出 round-label-ok
來，讓 guard 本體（special-tier raw-line 棘輪，R158 動工前 1087/1089，headroom 僅 round-label-ok
2 行）只留 import 與一次呼叫，不吃掉它僅剩的 headroom；搬出的史料見
scratchpad/r158/moved_lore_r158_p6.md，收尾窗口落證據檔。

相依由呼叫端注入（比照 `tools/lib/harness_feed.py` 慣例）：本檔不 import
`context_budget_guard`，避免循環相依，也避免這裡長出第二份「怎麼掃逐字稿／怎麼判
window」的邏輯。純 stdlib；任何一路量不到／組不出來都 fail-open 成一句人看得懂的
話，不得反過來讓 SessionStart 崩潰或整條 emit 消失。

回歸鎖：`tools/tests/test_session_brief.py`（四象限：有/無快取 × 有/無 usage）；
接線面：`tools/tests/test_context_budget_guard.py::HandbackSessionStartAnnounceTest`。
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

#: 查證指令，人／模型都看得到的兩條「現查」出口（根 CLAUDE.md〈現查指令速查表〉）。
_VERIFY_HINT = ("查證指令：context 現查 `python tools/session_resume_planner.py --check`；"
                "額度現查 `python tools/session_resume_planner.py --pace`。")

#: halt 帶反覆出現的 rc=2 紅字容易被誤讀成「全部工具被擋」（refute_q1q2.md §0 實測）；
#: 這句話固定跟簡報一起送出，讓模型從第一時間就有正確的心智模型。
_RC2_CLARIFY = ("hook 的 rc=2 紅字只代表扇出型工具（Task／Agent／Workflow／WebFetch／"
                "WebSearch）暫停；Read／Write／Edit／Bash／git 這類收斂型工具不受影響。")

_NO_MEASURE = "本 session 尚無量測（新視窗，尚未有 assistant usage 記錄）"
_QUOTA_UNAVAILABLE = "額度快取不可用，現查 `python tools/session_resume_planner.py --pace`"


def quota_line(quota_gate: object, now: datetime | None = None) -> str:
    """額度那一行。零網路、只讀快取；讀不到／判不出來一律 fail-open 成人話。

    `quota_gate`＝呼叫端已 import 好的 `tools/lib/quota_gate` 模組（它內部持有
    `quota_policy`），本函式不自己 import——理由同檔頭：不長出第二份「怎麼判額度」。
    """
    at = now or datetime.now().astimezone()
    try:
        policy, _problems = quota_gate.quota_policy.load_policy(quota_gate.policy_env())
        decision = quota_gate.quota_policy.decide(quota_gate.read_quota(at), at, policy)
        return quota_gate.quota_policy.describe(decision)
    except Exception:  # noqa: BLE001 — 簡報失敗不得反過來擋 SessionStart
        return _QUOTA_UNAVAILABLE


def context_line(
    transcript: Path | None,
    *,
    scan_transcript: Callable[[Path], tuple],
    resolve_window: Callable[..., tuple[int, str]],
    window_evidence: Callable[..., dict],
    read_context_feed: Callable[[str | None, object], dict],
) -> str:
    """context 那一行：新視窗給「尚無量測」，已有 usage 給 `used/window/百分比`。

    四個函式皆由呼叫端注入（guard 既有同名函式，本檔不重掃逐字稿的第二份邏輯）。
    任何一步失敗都收斂成 `_NO_MEASURE`——量不到就照實說，不猜。
    """
    if transcript is None or not transcript.is_file():
        return _NO_MEASURE
    try:
        used, peak, model = scan_transcript(transcript)
        if used is None:
            return _NO_MEASURE
        sid = transcript.stem
        feed = read_context_feed(sid, model)
        window, source = resolve_window(peak, **window_evidence(model, session_id=sid, feed=feed))
    except Exception:  # noqa: BLE001 — 見上
        return _NO_MEASURE
    if window <= 0:
        return _NO_MEASURE
    return f"used={used:,} window={window:,}（{used / window:.1%}，{source}）"


def sessionstart_brief(
    payload: dict,
    quota_gate: object,
    scan_transcript: Callable[[Path], tuple],
    resolve_window: Callable[..., tuple[int, str]],
    window_evidence: Callable[..., dict],
    read_context_feed: Callable[[str | None, object], dict],
    *,
    now: datetime | None = None,
) -> str:
    """組出 SessionStart 要 `emit_to_model` 的那一整行簡報（額度＋context＋查證指令）。"""
    raw = payload.get("transcript_path")
    transcript = Path(raw) if isinstance(raw, str) and raw.strip() else None
    ctx = context_line(transcript, scan_transcript=scan_transcript, resolve_window=resolve_window,
                       window_evidence=window_evidence, read_context_feed=read_context_feed)
    quota = quota_line(quota_gate, now)
    return (f"[SDD-CTX-GUARD] 本 session 啟動時真實水位——context：{ctx}；額度：{quota}。"
           f"{_VERIFY_HINT}{_RC2_CLARIFY}")
