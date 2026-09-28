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

ctx5 輪兩個缺口（掌舵者五問 Q1／Q4 的機制面補強）：
  G1. `context_line()` 此前拿到 `read_context_feed()` 的 `feed["reason"]`（例如
      「無 feed（statusLine 未設定或本 session 尚無 assistant 訊息）」）後靜默丟棄；
      且簡報從未告訴模型「這台機器的 statusLine 有沒有安裝」——Windows 上從未安裝，
      模型在 session 內完全不知道、也不知道要跑什麼安裝。`statusline_line()` 補上
      安裝狀態那一句（重用 `tools/install_statusline.py::status()`，不重寫判準）；
      `_harness_reason_note()` 把 `feed["reason"]` 非空時的那句接進 context 行（比照
      `tools/lib/harness_feed.py::check_lines()` 的既有措辭）。
  G2. `quota_line()` 在快取陳舊（`describe()` 文字含 `stale-cache`）時印出的
      `cap=2 recommended=2 band=unmeasured` 是退化政策值、不是量測值，容易被模型誤讀
      成硬限制；含 `stale-cache` 時追加固定文案，講清楚「PreToolUse 會自動補量、
      零 token」，不含時不動。

回歸鎖：`tools/tests/test_session_brief.py`（額度×context 四象限＋G1 statusLine
三格＋feed reason 一格＋G2 stale-cache 兩格）；接線面：
`tools/tests/test_context_budget_guard.py::HandbackSessionStartAnnounceTest`。
"""
from __future__ import annotations

import contextlib
import io
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

try:
    import harness_feed  # type: ignore[import-not-found]  # 同目錄：check_lines() 既有措辭來源
except Exception:  # noqa: BLE001 — 見檔頭 fail-open 紀律；不可達就不附註，不擋簡報
    harness_feed = None  # type: ignore[assignment]

try:
    import platform_utils  # type: ignore[import-not-found]  # 同目錄 SSOT：is_windows()
except Exception:  # noqa: BLE001 — 見檔頭 fail-open 紀律；不可達就回 POSIX 版澄清句
    platform_utils = None  # type: ignore[assignment]

#: 查證指令，人／模型都看得到的兩條「現查」出口（根 CLAUDE.md〈現查指令速查表〉）。
_VERIFY_HINT = ("查證指令：context 現查 `python tools/session_resume_planner.py --check`；"
                "額度現查 `python tools/session_resume_planner.py --pace`。")

#: halt 帶反覆出現的 rc=2 紅字容易被誤讀成「全部工具被擋」（refute_q1q2.md §0 實測）；
#: 這句話固定跟簡報一起送出，讓模型從第一時間就有正確的心智模型。POSIX 版原文；
#: Windows 版見 `_RC2_CLARIFY_WINDOWS`（DEF-200-412：這句話在 Windows 上對模型是假話
#: ——Bash 另由鐵律一 hook 停用，見 `rc2_clarify()` 的平台判準）。
_RC2_CLARIFY = ("hook 的 rc=2 紅字只代表扇出型工具（Task／Agent／Workflow／WebFetch／"
                "WebSearch）暫停；Read／Write／Edit／Bash／git 這類收斂型工具不受影響。")

#: DEF-200-412：Windows 上 `_RC2_CLARIFY` 那句「Bash…不受影響」對模型是假話——
#: `block_bash_on_windows.py`（鐵律一）對 Bash 工具整支 exit 2。新視窗的模型先被
#: 這句安撫、下一步撞牆後又把「Bash 被擋」誤讀成「寫檔被擋」（掌舵者 Q1 原話：
#: 「才開新視窗，就說他被擋不能寫檔案用工具了」）。改列 PowerShell，並點破那個誤讀。
_RC2_CLARIFY_WINDOWS = (
    "hook 的 rc=2 紅字只代表扇出型工具（Task／Agent／Workflow／WebFetch／"
    "WebSearch）暫停；Read／Write／Edit／PowerShell／git 這類收斂型工具不受影響。"
    "（Windows：Bash 工具另由鐵律一 hook 停用，跑指令用 PowerShell 工具、"
    "改檔用 Write／Edit，不要先試 Bash——那個阻斷不是「不能寫檔」）"
)


def rc2_clarify(windows: bool | None = None) -> str:
    """rc=2 誤讀澄清句，平台感知版（DEF-200-412）。

    `windows=None` 時以同目錄 SSOT `platform_utils.is_windows()` 現查——本檔不得
    自己寫 `os.name`／`sys.platform` 分支（根 CLAUDE.md〈Windows 側單一載具原則〉
    鐵律三）。import 失敗時一律 fail-open 回 POSIX 版（`_RC2_CLARIFY`），理由同
    `harness_feed`：hook 行程不保證 `tools/lib` 以外的模組在 sys.path 上，簡報
    失敗不得反過來擋 SessionStart。
    """
    if windows is None:
        try:
            windows = bool(platform_utils.is_windows())
        except Exception:  # noqa: BLE001 — 見上：fail-open 回 POSIX 版
            windows = False
    return _RC2_CLARIFY_WINDOWS if windows else _RC2_CLARIFY


_NO_MEASURE = "本 session 尚無量測（新視窗，尚未有 assistant usage 記錄）"
_QUOTA_UNAVAILABLE = "額度快取不可用，現查 `python tools/session_resume_planner.py --pace`"

#: G2：`describe()` 文字含 `stale-cache` 時固定追加的一句——退化政策值不是量測值，
#: 且 PreToolUse 會在第一次扇出型工具呼叫前自動補量一次（零 token），不必人介入。
_STALE_CACHE_NOTE = (
    "（陳舊快取的退化政策值，不是量測值：第一次扇出型工具呼叫前 PreToolUse 會自動補量"
    "一次、零 token；要現在看：python tools/session_resume_planner.py --pace）"
)


def quota_line(quota_gate: object, now: datetime | None = None) -> str:
    """額度那一行。零網路、只讀快取；讀不到／判不出來一律 fail-open 成人話。

    `quota_gate`＝呼叫端已 import 好的 `tools/lib/quota_gate` 模組（它內部持有
    `quota_policy`），本函式不自己 import——理由同檔頭：不長出第二份「怎麼判額度」。

    G2：`describe()` 文字含 `stale-cache` 時（快取過期，`decide()` 回退到
    `degraded_cap`）追加 `_STALE_CACHE_NOTE`，避免模型把退化值誤讀成硬限制。
    """
    at = now or datetime.now().astimezone()
    try:
        policy, _problems = quota_gate.quota_policy.load_policy(quota_gate.policy_env())
        decision = quota_gate.quota_policy.decide(quota_gate.read_quota(at), at, policy)
        text = quota_gate.quota_policy.describe(decision)
    except Exception:  # noqa: BLE001 — 簡報失敗不得反過來擋 SessionStart
        return _QUOTA_UNAVAILABLE
    return f"{text}{_STALE_CACHE_NOTE}" if "stale-cache" in text else text


def _harness_reason_note(feed: object) -> str:
    """G1：`feed["reason"]`（`read_context_feed()` 回的欄位）非空時，比照
    `tools/lib/harness_feed.py::check_lines()` 的既有措辭附一句——直接呼叫它，只把
    `data` 組成只會命中該分支的形狀（`harness_used`／`used` 固定給 `None`，避免順帶
    觸發它另外兩個與本行主題無關的分支：跨稿 diff、與「compact 後空窗」），不重寫
    第二份判準。`feed` 不是 dict 或沒有 `reason` 一律靜默回空字串（沒什麼好附的）。
    """
    if harness_feed is None or not isinstance(feed, dict):
        return ""
    reason = feed.get("reason")
    if not reason:
        return ""
    try:
        lines = harness_feed.check_lines(
            {"harness_reason": reason, "harness_used": None, "used": None})
    except Exception:  # noqa: BLE001 — 見檔頭 fail-open 紀律
        return ""
    return f"；{lines[0]}" if lines else ""


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

    G1：`feed["reason"]` 非空時（例如 statusLine 未設定），附一句
    `_harness_reason_note()`，不再靜默丟棄這個欄位。
    """
    if transcript is None or not transcript.is_file():
        return _NO_MEASURE
    note = ""
    try:
        used, peak, model = scan_transcript(transcript)
        if used is None:
            return _NO_MEASURE
        sid = transcript.stem
        feed = read_context_feed(sid, model)
        note = _harness_reason_note(feed)
        window, source = resolve_window(peak, **window_evidence(model, session_id=sid, feed=feed))
    except Exception:  # noqa: BLE001 — 見上
        return _NO_MEASURE
    if window <= 0:
        return _NO_MEASURE
    return f"used={used:,} window={window:,}（{used / window:.1%}，{source}）{note}"


def _default_check_statusline() -> dict:
    """`statusline_line()` 的預設 `check_status`：真的呼叫
    `tools/install_statusline.py::status()`（唯讀查現況、零網路，`home` 用它自己的
    預設值）。延遲到**呼叫當下**才 import：production（`context_budget_guard.py`
    沒有傳 `check_statusline`）走到這裡才第一次付 import 成本；測試一律注入替身，
    不會執行到這一行，維持本檔既有的「測試零 I/O」紀律。`tools/install_statusline.py`
    不在 `tools/lib/`（本檔所在目錄）上，故先確保其父目錄在 `sys.path` 上——同目錄的
    `_stdio_utf8`／`statusline_context_feed`／`_cli_flags` 三個同伴模組才解得到。
    """
    try:
        tools_dir = str(Path(__file__).resolve().parent.parent)
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        import install_statusline  # noqa: PLC0415 — 見上：刻意延遲到呼叫當下
    except Exception as exc:  # noqa: BLE001 — 見檔頭 fail-open 紀律
        raise RuntimeError(f"install_statusline 模組不可達：{exc}") from exc
    return install_statusline.status()


#: G1：statusLine 未安裝時附的一句安裝提示（`--dry-run` 先預覽、去掉旗標才真的寫檔，
#: 見 `tools/install_statusline.py` 檔頭四模式）。
_STATUSLINE_INSTALL_HINT = "`python tools/install_statusline.py --dry-run` 預覽後去掉旗標安裝"


def statusline_line(check_status: Callable[[], dict] = _default_check_statusline) -> str:
    """G1：statusLine 安裝狀態那一行——重用 `tools/install_statusline.py::status()`
    既有的查現況邏輯，不重寫判準。`check_status` 由呼叫端／測試注入覆寫（預設值即
    真的呼叫該函式）；任何例外一律 fail-open 成「查不到」，不得讓 SessionStart 崩掉。

    DEF-200-414：`matches_current_checkout` 鍵缺席時預設 `True`（維持既有三格測試
    語意不變）；`installed` 為真但與本 checkout 不符時（repo 搬家／.venv 重建／被
    其他工具改寫都會這樣）另回第三種句子，不得誤報成「已安裝」。
    """
    try:
        report = check_status()
        installed = bool(report.get("installed"))
        matches = bool(report.get("matches_current_checkout", True))
    except Exception as exc:  # noqa: BLE001 — 見上
        return f"statusLine：查不到（{exc}）"
    if not installed:
        return f"statusLine：未安裝（安裝：{_STATUSLINE_INSTALL_HINT}）"
    if not matches:
        return (
            "statusLine：已安裝但與本 checkout 不符"
            f"（repo 搬家／.venv 重建／被改寫都會這樣；重裝：{_STATUSLINE_INSTALL_HINT}）"
        )
    return "statusLine：已安裝"


def sessionstart_brief(
    payload: dict,
    quota_gate: object,
    scan_transcript: Callable[[Path], tuple],
    resolve_window: Callable[..., tuple[int, str]],
    window_evidence: Callable[..., dict],
    read_context_feed: Callable[[str | None, object], dict],
    *,
    now: datetime | None = None,
    check_statusline: Callable[[], dict] = _default_check_statusline,
) -> str:
    """組出 SessionStart 要 `emit_to_model` 的那一整行簡報
    （額度＋context＋statusLine 安裝狀態＋查證指令）。

    `check_statusline` 是新增的 keyword-only 參數、帶預設值：`context_budget_guard.py`
    既有的六個位置引數呼叫（未傳這個新參數）逐字相容，不需要跟著改那一行呼叫。

    DEF-200-344：注入函式（`resolve_window` 等）本身也可能 fail-open 出聲到
    stderr（如 `known_model_windows` 查表失手），本函式整段包
    `contextlib.redirect_stderr` 吞掉，不得漏到 SessionStart hook 的真實 stderr。
    """
    raw = payload.get("transcript_path")
    transcript = Path(raw) if isinstance(raw, str) and raw.strip() else None
    with contextlib.redirect_stderr(io.StringIO()):
        ctx = context_line(
            transcript, scan_transcript=scan_transcript, resolve_window=resolve_window,
            window_evidence=window_evidence, read_context_feed=read_context_feed)
        quota = quota_line(quota_gate, now)
        statusline = statusline_line(check_statusline)
    return (f"[SDD-CTX-GUARD] 本 session 啟動時真實水位——context：{ctx}；額度：{quota}；"
           f"{statusline}。"
           f"{_VERIFY_HINT}{rc2_clarify()}")
