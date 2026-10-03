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
  DEF-200-432：`quota_line()` 的 `decide()` 此前沒帶 `active_model` ⇒ 新鮮快取下簡報的
      cap 比 `--pace`／守衛寬（模型分軌軸被排除）；`_active_model()` 補上（payload `model`
      → 逐字稿 → feed，判準本體住 `harness_feed.start_model_of()`），缺席時行為逐字不變。

DEF-200-411：`statusline_line()` 的安裝提示改給**可直接貼上的絕對路徑指令**
（`_install_command()`）。舊提示是裸 `python tools/…`，依賴 cwd 與 PATH 上排前面的
python（Windows 的實況是 pyenv），而這句話要經 `additionalContext` 轉述給模型、
再由模型轉給人。
DEF-200-231①：`schtasks_trigger()`（手動排程路徑的觸發時刻只取實測 reset）與
`sdd_fsm_line()`（`--check` 末行的 SDD FSM 現況）也住這裡——`session_resume_planner.py`
的 `guardrail_cli` tier LOC 餘裕只有個位數；兩者皆循「呼叫端注入」慣例，不 import
quota_gate／SDD runtime。

回歸鎖：`tools/tests/test_session_brief.py`（額度×context 四象限＋G1 statusLine 三格＋
feed reason 一格＋G2 stale-cache 兩格＋DEF-200-432 active_model 各格＋可貼安裝指令三格＋
SDD FSM 行八格＋SA-01 查證指令安全形態三格＋SA-02 人看得到的 statusLine 一句三格）；接線面：
`tools/tests/test_context_budget_guard.py::HandbackSessionStartAnnounceTest`、
`::SessionStartTellsTheHumanTest`（SA-02 端到端：真 hook 的 stdout 多一個頂層 `systemMessage`）、
`tools/tests/test_wake_chain_halt_r278.py` 的
`RegisterSchtasksTimeIsObservedNotGuessedTest`（`schtasks_trigger`）與
`CheckPrintsTheSddFsmLineTest`（`sdd_fsm_line`）。

唯讀退路與單一導出：`verify_hint()` 尾端附「現查指令跑不起來時改用 Read 讀 feed 檔與額度快取」
（路徑由 `_read_targets()` 從既有 SSOT 解出；其後一句說明權限詢問是 harness 權限層、不是 hook
阻斷——Read 目標在 cwd 外、planner 現查也常要核准）；`rc2_clarify()` 的收斂型工具清單句只呼叫
`quota_messages.convergent_tools_clause()`；`AUTOSDD_UNATTENDED` 有設時簡報追加治理檔唯讀一句。
回歸鎖：`test_session_brief.py` 的 `ConvergentToolsClauseSingleHomeTest`／`ReadFallbackHintTest`。
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import sys
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from pathlib import Path

try:
    import harness_feed  # type: ignore[import-not-found]  # 同目錄：check_lines() 既有措辭來源
except Exception:  # noqa: BLE001 — 見檔頭 fail-open 紀律；不可達就不附註，不擋簡報
    harness_feed = None  # type: ignore[assignment]

try:
    import platform_utils  # type: ignore[import-not-found]  # 同目錄 SSOT：is_windows()
except Exception:  # noqa: BLE001 — 見檔頭 fail-open 紀律；不可達就回 POSIX 版澄清句
    platform_utils = None  # type: ignore[assignment]

try:
    import quota_messages  # type: ignore[import-not-found]  # 同目錄 SSOT：收斂型工具清單句
except Exception:  # noqa: BLE001 — 見檔頭 fail-open 紀律；不可達就省略清單句，不在這裡抄一份
    quota_messages = None  # type: ignore[assignment]

try:
    import unattended_authz  # type: ignore[import-not-found]  # 同目錄 SSOT：UNATTENDED_ENV
except Exception:  # noqa: BLE001 — 見檔頭 fail-open 紀律；不可達就不加無人值守那句
    unattended_authz = None  # type: ignore[assignment]

#: 查證指令，人／模型都看得到的兩條「現查」出口（根 CLAUDE.md〈現查指令速查表〉）。
_CHECK_PACE = ("context 現查 `python tools/session_resume_planner.py --check`；"
               "額度現查 `python tools/session_resume_planner.py --pace`。")
#: SA-01：兩條的輸出都很短，新視窗首個工具呼叫卻常寫 `… | head -40; echo "rc=$?"`，被鐵律六守衛
#: （判準④，判斷正確）擋下——缺的是行動點，所以簡報一併教安全形態。Windows 版對應 `cd` 開場與管線
#: 後讀 `$LASTEXITCODE`（`lint_powershell_command.py` 擋同形態），見 `verify_hint()`。
#: DEF-200-476：repo 權限白名單（.claude/settings.json permissions.allow）認的是下面這兩條的字面；
#: 模型改寫成絕對路徑或 `& '…'` 形式就會再跳權限詢問。兩個平台版共用同一句。
_LITERAL_NOTE = ("這兩條照字面執行（相對路徑、cwd 已是 repo 根；不要改寫成絕對路徑或 & '…' 形式"
                 "——權限白名單認的是這個字面）；")
_VERIFY_HINT = ("查證指令（輸出很短，直接跑；要 rc 先導檔再讀，"
                "別在 `| head`／`| tail` 之後讀 rc）：" + _LITERAL_NOTE + _CHECK_PACE)
_VERIFY_HINT_WINDOWS = (
    "查證指令（輸出很短，直接跑；不要用 `cd` 開場（要換目錄就用 `Push-Location …; …; "
    "Pop-Location` 同呼叫成對）；要 rc 先存變數或導檔，別在管線之後讀 `$LASTEXITCODE`）："
    + _LITERAL_NOTE + _CHECK_PACE)

#: halt 帶反覆出現的 rc=2 紅字容易被誤讀成「全部工具被擋」（refute_q1q2.md §0 實測）；
#: 這句話固定跟簡報一起送出，讓模型從第一時間就有正確的心智模型。三段組成：扇出暫停半句
#: （這裡）＋收斂型工具清單句（`quota_messages.convergent_tools_clause()`，單一導出，本檔不抄）
#: ＋平台尾句（POSIX 一個、Windows 一個）。寫壞的那一次呼叫被攔下不等於工具被停用，尾句講清楚。
_RC2_PAUSE = ("hook 的 rc=2 紅字只代表扇出型工具（Task／Agent／Workflow／WebFetch／"
              "WebSearch）暫停；")
_RC2_TAIL = ("（寫壞的那一次 Bash 呼叫會被攔下、不執行，stderr 附一行解法，照改重跑即可；"
             "Bash 本身仍可用。）")

#: DEF-200-412：Windows 上 Bash 工具由 `block_bash_on_windows.py`（鐵律一）整支 exit 2。新視窗
#: 的模型若先被「Bash 沒事」安撫、下一步撞牆後又把「Bash 被擋」誤讀成「寫檔被擋」（掌舵者 Q1
#: 原話：「才開新視窗，就說他被擋不能寫檔案用工具了」）。所以 Windows 尾句改列 PowerShell，
#: 並明列照常可用的工具；句中不引述症狀字面（引述即預示，DEF-200-476）。
_RC2_TAIL_WINDOWS = (
    "（Windows：Bash 工具另由鐵律一 hook 停用，跑指令用 PowerShell 工具、"
    "改檔用 Write／Edit，不要先試 Bash（PowerShell／Write／Edit 照常可用）；"
    "壞寫法的 PowerShell 指令會被 lint 擋下，訊息附出口，照改重跑即可）"
)


def _windows(windows: bool | None) -> bool:
    """平台判準的單一入口：`None` 時以同目錄 SSOT `platform_utils.is_windows()` 現查——本檔
    不得自己寫 `os.name`／`sys.platform` 分支（根 CLAUDE.md〈Windows 側單一載具原則〉鐵律三）。
    import 失敗時一律 fail-open 回 POSIX（`False`），理由同 `harness_feed`：hook 行程不保證
    `tools/lib` 以外的模組在 sys.path 上，簡報失敗不得反過來擋 SessionStart。"""
    if windows is None:
        try:
            return bool(platform_utils.is_windows())
        except Exception:  # noqa: BLE001 — 見上：fail-open 回 POSIX 版
            return False
    return windows


def rc2_clarify(windows: bool | None = None) -> str:
    """rc=2 誤讀澄清句，平台感知版（DEF-200-412）；平台判準見 `_windows()`。清單句只呼叫
    `quota_messages.convergent_tools_clause()`；該模組不可達時省略清單句（不在這裡抄第二份）。"""
    win = _windows(windows)
    try:
        clause = quota_messages.convergent_tools_clause(win) + "。"
    except Exception:  # noqa: BLE001 — 見檔頭 fail-open 紀律
        clause = ""
    return _RC2_PAUSE + clause + (_RC2_TAIL_WINDOWS if win else _RC2_TAIL)


#: 唯讀退路：兩條現查指令因權限詢問或分類器暫時不可用而跑不起來時，真實數據仍能用 Read 唯讀取得
#: ——沒有這句模型就同時「被擋」又「查不了」；條件句不預寫「寫檔被拒」劇本（DEF-200-476）。目標路徑由
#: `_read_targets()` 從既有 SSOT 解出；解不出時退回不帶路徑的措辭（`verify_hint()` 的缺省）。
_READ_FALLBACK = (
    "若上面兩條現查指令因權限詢問或分類器暫時不可用而跑不起來，真實數據仍可用 **Read** 工具"
    "唯讀取得：context 水位讀 {feed}（statusLine 寫的 JSON；`context_window.used_percentage`"
    "／`current_usage`／`context_window_size`），額度讀 {quota}（`axes[]` 的 `kind`／`pct`／"
    "`severity`）；不要憑簡報猜，也不要宣稱被擋。這兩條指令與兩個 Read 路徑已列在 repo "
    "權限白名單（.claude/settings.json permissions.allow），照字面執行不應再跳詢問；若跳出權限"
    "詢問，那是 harness 權限層、不是 hook 阻斷，核准即可。")


def verify_hint(windows: bool | None = None, *, feed: str | None = None,
                quota: str | None = None) -> str:
    """查證指令＋安全形態＋唯讀退路，平台感知版（SA-01；模式同 `rc2_clarify()`）。`feed`／
    `quota` 是已解出的 Read 目標（含反引號的字串，見 `_read_targets()`）；缺省＝不帶路徑。"""
    base = _VERIFY_HINT_WINDOWS if _windows(windows) else _VERIFY_HINT
    return base + _READ_FALLBACK.format(feed=feed or "本 session 的 statusLine feed 檔",
                                        quota=quota or "額度快取檔")


_NO_MEASURE = "本 session 尚無量測（新視窗，尚未有 assistant usage 記錄）"
_QUOTA_UNAVAILABLE = "額度快取不可用，現查 `python tools/session_resume_planner.py --pace`"

#: G2：額度量不到時固定追加的一句——退化政策值不是量測值，且 PreToolUse 會在第一次扇出型工具
#: 呼叫前自動補量一次（零 token），不必人介入。`stale-cache` 專屬說「陳舊快取」；其餘量不到
#: 的原因（無快取／壞檔／schema 不符／視窗已翻頁…）共用不帶原因的版本，判準是 band 而非 reason。
_DEGRADED_TAIL = (
    "不是量測值：第一次扇出型工具呼叫前 PreToolUse 會自動補量一次、零 token；"
    "要現在看：python tools/session_resume_planner.py --pace）"
)
_STALE_CACHE_NOTE = "（陳舊快取的退化政策值，" + _DEGRADED_TAIL
_UNMEASURED_NOTE = "（退化政策值，" + _DEGRADED_TAIL


def quota_line(quota_gate: object, now: datetime | None = None,
               active_model: str | None = None) -> str:
    """額度那一行。零網路、只讀快取；讀不到／判不出來一律 fail-open 成人話。

    `quota_gate`＝呼叫端已 import 好的 `tools/lib/quota_gate` 模組（它內部持有
    `quota_policy`），本函式不自己 import——理由同檔頭：不長出第二份「怎麼判額度」。

    G2：`describe()` 文字含 `stale-cache` 時（快取過期，`decide()` 回退到
    `degraded_cap`）追加 `_STALE_CACHE_NOTE`，避免模型把退化值誤讀成硬限制；其餘量不到的
    原因（`band == unmeasured`）追加 `_UNMEASURED_NOTE`——此前只有 `stale-cache` 附註，
    無快取／壞檔／schema 不符／視窗已翻頁時簡報只剩裸 `cap=2 band=unmeasured`。

    DEF-200-432：`active_model`（家族字，如 `fable`）傳給 `decide()`，模型分軌軸（`weekly_scoped`
    等）才會進 cap 聚合，簡報的 `⇒ cap=…` 才與 `--pace`／守衛同尺；此前缺席，新鮮快取下簡報
    印 `cap=4 band=notice`、同一份快取數秒後 `--pace` 印 `cap=1 band=prepare`。快取有量到軸
    時句尾附 ` active_model=<家族>`（讓人看得出這個 cap 是按哪個模型算的；`-p` 沒有 feed、
    payload 也不帶模型時 `active_model=None`，行為與此前逐字相同）。
    """
    at = now or datetime.now().astimezone()
    try:
        policy, _problems = quota_gate.quota_policy.load_policy(quota_gate.policy_env())
        decision = quota_gate.quota_policy.decide(
            quota_gate.read_quota(at), at, policy, active_model=active_model)
        text = quota_gate.quota_policy.describe(decision)
        if active_model and decision.per_axis:
            text += f"　active_model={active_model}"
        unmeasured = decision.band == quota_gate.quota_policy.BAND_UNMEASURED
    except Exception:  # noqa: BLE001 — 簡報失敗不得反過來擋 SessionStart
        return _QUOTA_UNAVAILABLE
    if "stale-cache" in text:
        return f"{text}{_STALE_CACHE_NOTE}"
    return f"{text}{_UNMEASURED_NOTE}" if unmeasured else text


def _active_model(payload: dict, transcript: Path | None, guard: object) -> str | None:
    """DEF-200-432：簡報額度行的 active model；判準本體住 `harness_feed.start_model_of()`。
    `guard`（`context_budget_guard` 模組）缺席、`harness_feed` 不可達、任何例外一律 `None`
    ＝維持此前行為（見檔頭 fail-open 紀律）。"""
    if guard is None or harness_feed is None:
        return None
    try:
        return harness_feed.start_model_of(payload, transcript, guard)
    except Exception:  # noqa: BLE001 — 見檔頭 fail-open 紀律
        return None


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


def _tools_on_path() -> None:
    """`tools/`（本檔的上一層）掛上 `sys.path`：`install_statusline`／`statusline_context_feed`
    不在 `tools/lib/`，延遲 import 前先掛（兩處共用）。"""
    tools_dir = str(Path(__file__).resolve().parent.parent)
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)


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
        _tools_on_path()
        import install_statusline  # noqa: PLC0415 — 見上：刻意延遲到呼叫當下
    except Exception as exc:  # noqa: BLE001 — 見檔頭 fail-open 紀律
        raise RuntimeError(f"install_statusline 模組不可達：{exc}") from exc
    return install_statusline.status()


#: DEF-200-411：`_install_command()` 組不出絕對路徑時的 fail-open 退路——裸指令（相對
#: 路徑、依賴 cwd 與 PATH）。外層文案（`statusline_line()`）已說「貼上即安裝；先預覽就
#: 在尾端加 --dry-run」（`--dry-run` 先預覽、去掉旗標才真的寫檔，見
#: `tools/install_statusline.py` 檔頭四模式），所以這裡**不得**自帶 `--dry-run` 或
#: 「預覽後去掉旗標」，否則同一句話自相矛盾。
_STATUSLINE_INSTALL_HINT = "python tools/install_statusline.py"


def _install_command(root: Path | None = None, windows: bool | None = None) -> str:
    """可直接貼上的安裝指令：絕對路徑＋本 checkout `.venv` 直譯器（無則
    `sys.executable`，與 `settings_snippet()` 同序），與 cwd、PATH 上的 python 無關
    （DEF-200-411 的兩個失敗面）。Windows 加 `& `（PowerShell 呼叫運算子：帶引號的首
    token 不加只會被當字串印出）並用**單引號**字串：雙引號內 `$`／反引號會被內插或跳脫、
    路徑被靜默改寫，單引號內全是字面（內嵌單引號寫成兩個，同 planner 的
    `_ps_single_quote`）。POSIX 維持雙引號。任何例外退回舊提示（fail-open）。`root`／
    `windows` 是測試注入縫，production 一律現查。"""
    try:
        base = root or Path(__file__).resolve().parents[2]
        win = platform_utils.is_windows() if windows is None else windows
        venv = platform_utils.venv_python_path(base / ".venv", win)
        py, script = (venv if venv.is_file() else Path(sys.executable),
                      base / "tools" / "install_statusline.py")
        if win:
            return "& " + " ".join(
                "'" + str(p).replace("'", "''") + "'" for p in (py, script))
        return f'"{py}" "{script}"'
    except Exception:  # noqa: BLE001 — 見檔頭 fail-open 紀律
        return _STATUSLINE_INSTALL_HINT


def _statusline_flags(report: dict) -> tuple[bool, bool]:
    """`(installed, matches_current_checkout)`；DEF-200-414：`matches` 鍵缺席時預設 `True`。
    給模型的 `statusline_line()` 與給人的 `statusline_system_message()` 共用這一個判準。"""
    return bool(report.get("installed")), bool(report.get("matches_current_checkout", True))


def statusline_line(check_status: Callable[[], dict] = _default_check_statusline) -> str:
    """G1：statusLine 安裝狀態那一行——重用 `tools/install_statusline.py::status()`
    既有的查現況邏輯，不重寫判準。`check_status` 由呼叫端／測試注入覆寫（預設值即
    真的呼叫該函式）；任何例外一律 fail-open 成「查不到」，不得讓 SessionStart 崩掉。

    DEF-200-414：`matches_current_checkout` 鍵缺席時預設 `True`（維持既有三格測試
    語意不變）；`installed` 為真但與本 checkout 不符時（repo 搬家／.venv 重建／被
    其他工具改寫都會這樣）另回第三種句子，不得誤報成「已安裝」。
    """
    try:
        installed, matches = _statusline_flags(check_status())
    except Exception as exc:  # noqa: BLE001 — 見上
        return f"statusLine：查不到（{exc}）"
    if not installed:
        return ("statusLine：未安裝（貼上即安裝；先預覽就在尾端加 --dry-run："
                f"{_install_command()}）")
    if not matches:
        return (
            "statusLine：已安裝但與本 checkout 不符"
            "（repo 搬家／.venv 重建／被改寫都會這樣；"
            f"重裝，貼上即可：{_install_command()}）"
        )
    return "statusLine：已安裝"


def statusline_system_message(
        payload: dict, check_status: Callable[[], dict] = _default_check_statusline) -> str | None:
    """SA-02／Q4：statusLine 沒裝好時給**人**看的一句（`systemMessage`）。簡報只進模型 context
    （`additionalContext`）、人看不到——Windows 11 沒有 `ctx NN% …` 那行時，人無從知道原因。
    未安裝、或已安裝但與本 checkout 不符 ⇒ 一句＋可貼安裝指令（同簡報的 `_install_command()`）；
    已裝好、查不到、`compact`（session 中途重注，人早看過）⇒ `None`——寧可少說，不每場吵。
    任何例外一律 `None`（fail-open：這句話壞了不得連累簡報本體）。"""
    try:
        if payload.get("source") == "compact":
            return None
        installed, matches = _statusline_flags(check_status())
    except Exception:  # noqa: BLE001 — 見檔頭 fail-open 紀律
        return None
    if installed and matches:
        return None
    return ("ℹ️ 畫面最下方沒有 `ctx NN% …` 狀態列（statusLine 未安裝或與本 checkout 不符）。"
            f"貼上即安裝：{_install_command()}")


_FSM_STATE_RE = re.compile(
    r"^ {2}current_state:[ \t]*([\"']?)([A-Za-z0-9_]+)\1", re.MULTILINE)


def sdd_fsm_line(env: Mapping[str, str] | None = None,
                 repo_root: Path | None = None) -> str:
    """`--check` 末行：SDD router 的 FSM 現況，給模型在 Q1「說被擋」時一條可外驗的
    機器級證據。**只印原始 `current_state`、不判是否阻斷**——阻斷態清單的唯一真相源在
    SDD 側（`fsm_runtime`），這裡抄一份就是第二個家。純文字 regex 讀，不 import SDD
    runtime、不需 yaml。版本號驗證同 router（去前導 v、須 `\\d+\\.\\d+`，否則放行不路由，
    且不得拼進路徑——DEF-CLDREV-028）；狀態檔鍵同 `state_loader.project_from_env`
    （`SDD_PROJECT`，否則版本目錄的上一層資料夾名）。"""
    e = os.environ if env is None else env
    raw = str(e.get("SDD_ACTIVE_VERSION", "")).strip()
    if not raw:
        return "SDD FSM：休眠（SDD_ACTIVE_VERSION 未設）"
    ver = raw[1:] if raw[:1] in ("v", "V") else raw
    if not re.fullmatch(r"\d+\.\d+", ver):
        return (f"SDD FSM：SDD_ACTIVE_VERSION={raw!r} 格式非法（須形如 0.19）"
                "⇒ router 放行、未套用守門")
    sdd = (repo_root or Path(__file__).resolve().parents[2]) / "AISDLC_SDD"
    path = (sdd / f"AISDLC_SDD_v{ver}" / "build" / "reports" / "fsm"
            / f"FSM-STATE-{e.get('SDD_PROJECT') or sdd.name}.yaml")
    try:
        body = path.read_text(encoding="utf-8")
        mtime = datetime.fromtimestamp(path.stat().st_mtime).astimezone()
    except (OSError, ValueError):
        return f"SDD FSM：無狀態檔（SDD_ACTIVE_VERSION={raw}；預期 {path}）"
    stamp = mtime.isoformat(timespec="seconds")
    state = _FSM_STATE_RE.search(body)
    if state is None:
        return f"SDD FSM：狀態檔讀不出 current_state（{path}，mtime {stamp}）"
    return f"SDD FSM：current_state={state.group(2)}（狀態檔 {path}，mtime {stamp}）"


#: DEF-200-231①：`--at` 缺席又解不出實測 reset 時的拒絕語（與 `_arm_endurance` 同族）。
_NO_OBSERVED_RESET = (
    "❌ 未給 --at，額度快取也給不出可等的 reset 時刻（{why}）"
    "⇒ **拒絕退回「假設 5 小時」**。\n"
    "   reset 是滾動視窗，只能觀測、不能算：猜出來的時刻會讓排程醒在錯的時間，"
    "而取證規則照樣是綠的。\n"
    "   快取過期先跑 `python tools/session_resume_planner.py --pace`"
    "（補量一次、零 token）再重試；已撞線請改用 --arm-endurance（從逐字稿原文觀測）；"
    "要自己指定時刻請顯式給 --at。\n"
)


#: `--at ""`（空白）不是時刻：照單全收會把它記成「操作者宣稱的 reset」，而宣稱的是空的。
_EMPTY_AT = (
    "❌ --at 是空字串 ⇒ 沒有時刻可排，拒絕。\n"
    "   要等額度 reset 請省略 --at（取額度快取的實測 reset）；要自己指定請給非空的時刻運算式。\n"
)


def trigger_basis(observed: bool) -> str:
    """`--print-schtasks-command` 標頭裡「這個觸發時刻從哪來」那句：只說這次真的走的那條路
    （`schtasks_trigger()` 缺 `--at` 取實測 reset；顯式 `--at` 是操作者宣稱的時刻）。"""
    return ("省略 --at＝額度快取的實測 resets_at＋緩衝（解不出即拒絕，不猜）" if observed
            else "以 --at 顯式指定（操作者宣稱的時刻，原樣下傳，未對照額度快取）")


def schtasks_trigger(
    given: str | None, quota_gate: object, *, skew_seconds: int,
    now: datetime | None = None,
) -> tuple[str | None, datetime | None, str]:
    """手動排程路徑的觸發時刻：回 `(at_expr, 結構化 at, 拒絕語)`。

    顯式 `--at`（`given`）＝操作者宣稱的時刻，原樣下傳、結構化 at 為 `None`（同此前）；
    空白字串不是時刻 ⇒ 回拒絕語。
    缺席時只取**實測**：額度快取 → `decide()` → `halt_resets_at()`（≥halt 各軸中最早
    可解析者，無則 binding）＋緩衝，且 `reset_branch()` 須判 arm（6 小時可等視界）。
    量不到／太舊／太遠／已過一律 `(None, None, 拒絕語)`，**不得退回猜的時刻**
    （ADR-XPLAT-014 的 L1＋L4 兩格；已撞線後的逐字稿觀測值是 `--arm-endurance` 那條
    路）。字面格式同 `register_endurance`（本機時區、單引號）。`quota_gate` 由呼叫端
    注入（同 `quota_line`）；`skew_seconds` 由呼叫端給——緩衝常數的唯一家是 planner
    的 `RESET_SKEW_SECONDS`，這裡不抄第二份。"""
    if given is not None:
        return (given, None, "") if given.strip() else (None, None, _EMPTY_AT)
    at_now = now or datetime.now().astimezone()
    try:
        policy, _problems = quota_gate.quota_policy.load_policy(quota_gate.policy_env())
        state = quota_gate.read_quota(at_now)
        decision = quota_gate.quota_policy.decide(state, at_now, policy)
        raw = quota_gate.halt_resets_at(decision)
        branch = quota_gate.reset_branch(raw, at_now)
        fire = None
        if branch == quota_gate.QUOTA_BRANCH_ARM:
            fire = datetime.fromisoformat(str(raw)).astimezone()
            fire += timedelta(seconds=skew_seconds)
        if fire is not None and fire > at_now:
            return f"'{fire:%Y-%m-%d %H:%M:%S}'", fire, ""
        why = (f"額度快取不可用：{state.reason}" if not state.usable() else
               f"觸發時刻 {fire:%H:%M:%S} 已過（額度應已回來，請跑 --probe-quota 確認）"
               if fire is not None else
               quota_gate.reset_horizon_phrase(branch, raw, at_now, state.measured_at))
    except Exception as exc:  # noqa: BLE001 — 讀不出一律走拒絕，不退回猜測
        why = f"讀額度快取失敗：{exc}"
    return None, None, _NO_OBSERVED_RESET.format(why=why)


def _read_targets(quota_gate: object, session_id: str | None) -> tuple[str | None, str | None]:
    """唯讀退路的兩個 Read 目標，皆取自既有 SSOT、本檔不拼路徑：feed＝寫入端
    `statusline_context_feed.context_feed_path()`（同 `_default_check_statusline` 的延遲
    import）；額度快取＝呼叫端注入的 `quota_gate.quota_cache_path()`（meter 的 `cache_path()`）。
    `session_id` 缺席時 feed 給範本路徑並註明取最新 mtime 那支。任何一路失敗各自回 `None`。"""
    feed = quota = None
    try:
        _tools_on_path()
        import statusline_context_feed  # noqa: PLC0415 — 見上：刻意延遲到呼叫當下
        path = statusline_context_feed.context_feed_path(session_id or "<session_id>")
        feed = f"`{path}`" + ("" if session_id else "（session_id 不明：取該目錄最新 mtime 那支）")
    except Exception:  # noqa: BLE001 — 見檔頭 fail-open 紀律
        pass
    try:
        quota = f"`{quota_gate.quota_cache_path()}`"
    except Exception:  # noqa: BLE001 — 見上
        pass
    return feed, quota


#: 無人值守回合（`AUTOSDD_UNATTENDED` 有設）：治理檔的 Write／Edit 會被 `block_destructive_git.py`
#: 的唯讀守衛擋下（exit 2）；簡報只說 Write／Edit 照常可用就與守衛自己的訊息互相矛盾。
_UNATTENDED_NOTE = ("（無人值守回合例外：治理檔（PRD 保護面）的 Write／Edit 會被唯讀守衛擋下，"
                    "改它請回報主控、不要硬繞。）")


def _unattended_note() -> str:
    try:
        return _UNATTENDED_NOTE if os.environ.get(unattended_authz.UNATTENDED_ENV) else ""
    except Exception:  # noqa: BLE001 — 見檔頭 fail-open 紀律
        return ""


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
    guard: object = None,
) -> str:
    """組出 SessionStart 要 `emit_to_model` 的那一整行簡報
    （額度＋context＋statusLine 安裝狀態＋查證指令＋唯讀退路；無人值守時另附治理檔唯讀一句）。

    `check_statusline` 是新增的 keyword-only 參數、帶預設值：`context_budget_guard.py`
    既有的六個位置引數呼叫（未傳這個新參數）逐字相容，不需要跟著改那一行呼叫。
    `guard`（DEF-200-432，同樣 keyword-only、預設 `None`）＝呼叫端的 `context_budget_guard`
    模組本身，供 `harness_feed.start_model_of()` 取 `model_family`／`scan_transcript` 等；
    缺席時額度行不帶 active_model，與此前逐字相同。

    DEF-200-344：注入函式（`resolve_window` 等）本身也可能 fail-open 出聲到
    stderr（如 `known_model_windows` 查表失手），本函式整段包
    `contextlib.redirect_stderr` 吞掉，不得漏到 SessionStart hook 的真實 stderr。
    """
    raw = payload.get("transcript_path")
    transcript = Path(raw) if isinstance(raw, str) and raw.strip() else None
    sid = payload.get("session_id")
    sid = sid if isinstance(sid, str) and sid.strip() else (transcript.stem if transcript else None)
    feed, quota_file = _read_targets(quota_gate, sid)
    with contextlib.redirect_stderr(io.StringIO()):
        ctx = context_line(
            transcript, scan_transcript=scan_transcript, resolve_window=resolve_window,
            window_evidence=window_evidence, read_context_feed=read_context_feed)
        quota = quota_line(quota_gate, now, _active_model(payload, transcript, guard))
        statusline = statusline_line(check_statusline)
    return (f"[SDD-CTX-GUARD] 本 session 啟動時真實水位——context：{ctx}；額度：{quota}；"
           f"{statusline}。"
           f"{verify_hint(feed=feed, quota=quota_file)}{rc2_clarify()}{_unattended_note()}")
