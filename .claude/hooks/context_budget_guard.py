#!/usr/bin/env python
"""PostToolUse 守衛：Claude Code session 的 context 水位觀測者（本 repo 首見）。

WHY（沿革全文搬 scratchpad/dev-c/moved_lore.md；與 SDD `context_ledger` 的分工、
兩者同時觸發的殘餘限制、純文件約束對模型的攔阻力先例，皆見該檔）——一句話：把
harness 自己的 autocompact（姿態現查 `--check-autocompact`）之外，模型自己看得見
「現在幾 %」，並在 ≥94% 真的擋下展開型工具、產出可重啟點任務書供 `claude -r` 續跑。

量測面：hook payload 帶 `transcript_path`（本 session 逐字稿）。每筆 `type ==
"assistant"` 的 `message.usage` 下，**當前 context 佔用 ＝ input_tokens ＋
cache_creation_input_tokens ＋ cache_read_input_tokens**（`output_tokens` 不算：
下一回合才以 input 形式回到 context，重複計會高估）。

🔴 context window 判定：先可證、後推斷，來源字串原樣印給使用者。九階完整清單
（⓪ status line 進料 → ①~⑦ 各種釘值／查表 → ⑧ 保守下界，方向不對稱：猜小只是
早喊，猜大會讓守衛在真 90% 結構性靜默）與各階 WHY 全文搬 `CrossPlatform_
DEF200275_Context_Metering_Evidence.md`〈第七輪 史料搬遷（Dev-S8b）〉節，程式碼
本體＝`resolve_window()`。🔴 **⑧ 不得用來硬擋**（見〈PreToolUse 阻斷模式〉）。

行為契約（PostToolUse＝觀測模式；沿革搬 moved_lore.md）
------------------------------------------------------------------
· payload 讀不出來 → stderr 一行 ＋ **exit 1**（出聲不阻斷，見 `degraded_payload_verdict`）。
· 量不到 usage → exit 0 靜默（「量不到」≠「輸入壞掉」，混同會讓守衛被整支關掉）。
· `< 84%` 靜默；`>= 84%` stderr ＋ 送進模型 context（`emit_to_model`，逃生口
  `AUTOSDD_CONTEXT_SIGNAL_OFF`），內容依額度尺 `quota_gate.draining()` 三分。
· `>= 94%` stderr 強制指引 ＋ 寫任務書 ＋ **exit 2**。
· **同一門檻＋同一 window 只喊一次**（`latch_key` 含 window／epoch）。

🔴 PreToolUse 阻斷模式：`>= 94%` 且 window 非保守下界猜測時才擋（`may_block()`）；
只擋展開型工具（`BLOCKING_TOOLS`），Read／Edit／PowerShell 放行；不進閂鎖（水位掉下
去自動解除）；逃生口 `AUTOSDD_CONTEXT_GUARD_OFF=1`；任何非預期例外一律 exit 0。

相依規則：①能力提供者一律 try/except、不可達即退化「量不到」；②`quota_limits` hard
import；③`tools/lib/*` 只准裸名 import（反向依賴仍允許：planner import 本檔）。
本檔職責邊界（R82／Q2-02）：只剩一把尺（context 水位），額度尺整條住 `quota_gate.py`。

回歸鎖：`tools/tests/test_context_budget_guard.py`（合成 jsonl 注入，逐條驗紅）。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

#: `O_BINARY` 只有 Windows 的 `os` 有（鐵律三）；同 `tools/lib/quota_ledger.py` 既有慣例。
_BINARY = getattr(os, "O_BINARY", 0)

# 自己的 stdout/stderr 強制 UTF-8（缺這段：CJK locale 表達不了會逃脫成 \uXXXX、
# 非 UTF-8 locale 會亂碼；沿革全文搬證據檔〈第七輪 史料搬遷（Dev-S8b）〉節）。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001 — 模組層崩潰繞得過 main() 的保險，fail-open 是 P0
        pass

# 下面五個 import 共用同一種形態（同一條 sys.path、同一種 fail-open）：不可達時退化成
# `None`／存根函式，各自的職責整條退化成「量不到／不節流／不武裝／查不到」，絕不讓
# context 阻斷這條主線被一起帶走。逐支的家與退化方向全文搬證據檔同節。
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "tools", "lib"))
try:
    from platform_utils import emit_to_model, read_payload  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001 — 共用層不可達＝退化，不是崩潰（fail-open 是 P0）
    def read_payload() -> dict | None:  # type: ignore[misc]
        return None

    def emit_to_model(event: str, msg: str) -> bool:  # type: ignore[misc]
        return False  # 送不進模型 ⇒ 只剩 stderr 那一半

try:
    import quota_gate  # type: ignore[import-not-found]  # 額度水位節流閘，與 context 水位零交集
except Exception:  # noqa: BLE001 — 見上
    quota_gate = None  # type: ignore[assignment]

try:
    import sentinel_lifecycle  # type: ignore[import-not-found]  # 哨兵生命週期判準（值不值得一支 schtasks）
except Exception:  # noqa: BLE001 — 見上
    sentinel_lifecycle = None  # type: ignore[assignment]

# 🔴 R83／W2-A：四個武裝站點一律問 `_has_carrier()`（不再各自判一次平台），理由與
# 沿革全文搬證據檔同節。
try:
    import schedule_backend  # type: ignore[import-not-found]  # 排程載具（schtasks／launchd／沒有）
except Exception:  # noqa: BLE001 — 見上
    schedule_backend = None  # type: ignore[assignment]

try:
    import sdd_latest  # type: ignore[import-not-found]  # LATEST 版本路徑解析（查表資料的家）
except Exception:  # noqa: BLE001 — 見上
    sdd_latest = None  # type: ignore[assignment]


def _has_carrier() -> bool:
    """這台機器上有沒有排程載具（Windows schtasks／macOS launchd）。"""
    return schedule_backend is not None and schedule_backend.has_carrier()

# 額度**撞線判讀**唯一的家＝`tools/lib/quota_limits.py`。刻意 hard import（判讀原語
# 給 fallback stub 等於讓同一份字面有第二個家）。下面 11 個在本檔內不會被呼叫，是給
# `tools/session_resume_planner.py`（`guard.<name>` 取用）的純再匯出，刪任一個都會
# 在無人看管的排程路徑上 AttributeError。
from quota_limits import (  # noqa: E402,F401
    LIMIT_NONE,
    LIMIT_SESSION,
    LIMIT_SPEND,
    LIMIT_TRANSIENT,
    LIMIT_UNKNOWN,
    SYNTHETIC_MODEL,
    classify_limit,
    declared_zone,
    latest_limit_event,
    latest_success_at,
    newest_activity_at,
    parse_reset_at,
    session_transcripts,
    unhandled_limit_event,
)

#: 佔用當前 context 的三個 usage 欄。`output_tokens` 刻意不在內，理由見模組 docstring。
USAGE_FIELDS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")

#: 硬指定 context window 的環境變數（最高優先；唯一不含猜測的來源）。
WINDOW_ENV = "AUTOSDD_CONTEXT_WINDOW"

#: Claude Code 自己的 window 旋鈕（環境變數版）。二進位內與 `autoCompactWindow`
#: 設定鍵同一條判定鏈；有設就代表使用者已經替 harness 釘死了那個數字。
CC_WINDOW_ENV = "CLAUDE_CODE_AUTO_COMPACT_WINDOW"
#: 同上的 settings 鍵。schema 逐字：`number().int().min(1e5).max(1e6)`。
CC_WINDOW_KEY = "autoCompactWindow"
#: settings 的模型欄。本機實測值 `opus[1m]`。
CC_MODEL_KEY = "model"

#: 人為逃生口：守衛誤判時讓人一鍵放行（模型改不到 hook 行程的環境）。
GUARD_OFF_ENV = "AUTOSDD_CONTEXT_GUARD_OFF"

#: 哨兵的獨立逃生口。刻意**不**沿用上面那一個：兩者關掉的是不同的東西（一個是
#: context 阻斷、一個是額度續航），共用一個開關會讓「我只是想暫時別被擋」順手把
#: 續航保護一起關掉，而那件事沒有人會注意到。
SENTINEL_OFF_ENV = "AUTOSDD_SENTINEL_OFF"

#: 送達形態的獨立逃生口（R91）：只把 WARN 提示的 **stdout 那一半**關掉，退回純 stderr。
#: 判定、阻斷、哨兵一律不受影響。刻意**不**沿用上面兩個、也不沿用 `AUTOSDD_GIT_GUARD_OFF`
#: ——四者關掉的是四件不同的事，共用一個會讓「我只是不想看到那則 JSON」順手把阻斷或續航
#: 一起關掉。已登記進 `quota_policy.ENV_SPEC`（⇒ `.env` 也到得了，R82／C2 那條路）。
SIGNAL_OFF_ENV = "AUTOSDD_CONTEXT_SIGNAL_OFF"

#: 無 console 父行程下 spawn 子行程的**防彈窗**兩層防線（`NO_WINDOW` 旗標 ＋
#: `quiet_python()` 載具）唯一的家＝`tools/lib/win_spawn.py`（刻意沒有 try/except：
#: 原語不能有 fallback stub，給 `NO_WINDOW` 一個 `0` 備援等於在 Windows 上用錯答案
#: 靜默通過）。`session_resume_planner` 以 `guard.NO_WINDOW` 取用，理由全文搬證據檔。
from win_spawn import NO_WINDOW, quiet_python  # noqa: E402,F401

#: 🔴 送進 `powershell.exe`（5.1）的每一段腳本都要以這一行開頭——PS 5.1 以主控台
#: codepage 寫 stdout、Python 以 UTF-8 讀，取證憑證會逐位元組降解卻仍非空。立案實測
#: 全文搬 `CrossPlatform_R91_Scan_Findings.md` §A-7。
PS_UTF8_PRELUDE = ("$OutputEncoding = [Console]::OutputEncoding = "
                   "[Text.UTF8Encoding]::new($false)\n")

#: PreToolUse 模式會擋下的「展開型」工具。刻意不含 Read／Edit／PowerShell：收斂
#: （讀檔、寫任務書、跑 git）必須還做得到，否則守衛會被整個關掉。R80 立案（命中面
#: 原本是 0，本 harness 實際叫 `Agent`／`Workflow`）與保留舊名的理由見證據檔 §I-11。
BLOCKING_TOOLS = ("Task", "WebFetch", "WebSearch", "Agent", "Workflow")


def blocking_reach_problems(blocking: tuple[str, ...], observed: set[str]) -> list[str]:
    """阻斷臂的**有效性**判準（純函式）：圈到的名字必須真的會出現。回空 list ＝合格。

    `observed`＝實測逐字稿裡出現過的 `tool_use` 名稱集合。空集合時**不判**——那代表
    「這台機器上量不到」，不代表「命中面是 0」，而「量不到 ≠ 量到零」是本檔通篇的紀律。
    """
    if not observed or set(blocking) & observed:
        return []
    return [f"BLOCKING_TOOLS={blocking} 與實測出現過的工具名毫無交集"
            f"（實測看到 {len(observed)} 種）⇒ 阻斷臂命中面為 0，蓋好了但永遠不會觸發"]

#: 保守下界。實際是 1M 時只會早喊，方向安全。
CONSERVATIVE_WINDOW = 200_000
#: 已知的下一檔變體。觀測到 used > CONSERVATIVE_WINDOW 只證明「大於 200K」，
#: 取這個值是在已知變體裡選，不是證出來的——訊息必須標成推斷。
WIDE_WINDOW = 1_000_000

#: 🔴 R92 掌舵者裁決：84／94 各喊一次（取代 75／90）。84＝收斂前置訊號（repo settings
#: 已釘 `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=90`；其分母是 auto-compact window，「84 早於
#: 壓縮點」不可證、只有方向安全——ADR-XPLAT-008 §4）；94＝「壓縮沒發生」的失效警報
#: （autocompact 正常時結構上走不到）。**刻意與額度尺 85／95 錯開
#: 1pp**：分母不同，同值＝認錯尺（鎖：`test_quota_thresholds_are_not_the_context_thresholds`）。
WARN_RATIO = 0.84
HARD_RATIO = 0.94

TIER_WARN = "warn"
TIER_HARD = "hard"

#: D32／DEF-200-275 第七輪：status line 進料的分母階，優先於本檔一切釘值（見
#: `resolve_window` 的〈harness 回報〉節與 `tools/statusline_context_feed.py` 檔頭）。
SOURCE_HARNESS = "harness 回報（status line context_window.context_window_size）"

SOURCE_PINNED = f"指定值（環境變數 {WINDOW_ENV}）"
SOURCE_PINNED_CC_ENV = f"指定值（Claude Code 自己的 {CC_WINDOW_ENV}）"
SOURCE_PINNED_CC_SETTING = f"指定值（Claude Code settings 的 {CC_WINDOW_KEY}）"
SOURCE_MODEL_MARKER = (
    f"推斷值（settings 的 {CC_MODEL_KEY} 欄帶 1m 標記 ⇒ {WIDE_WINDOW:,}；"
    "已與逐字稿實際跑過的 model 交叉核對同族，非單方面採信設定）"
)
SOURCE_INFERRED_WIDE = (
    f"推斷值（本 session 曾觀測到 used > {CONSERVATIVE_WINDOW:,} ⇒ window 必然大於它；"
    f"取 {WIDE_WINDOW:,} 是在已知變體裡選下一檔，**不是**證出來的值）"
)
SOURCE_INFERRED_FLOOR = (
    f"推斷值・保守下界（未觀測到超過 {CONSERVATIVE_WINDOW:,} 的用量。"
    f"若實際是 {WIDE_WINDOW:,} 只會提早喊，方向安全；要精確就設 {WINDOW_ENV}）"
)
#: D27：查表階（⑥）來源前綴／缺表說明，與 SDD `context_window.py` 同名常數逐字同構。
SOURCE_KNOWN_MODEL_PREFIX = "查表值（Models API max_input_tokens"
_NO_TABLE_NOTE = "無表"

#: 每一則訊息都要帶的「這是哪一把尺」標籤。理由見模組 docstring 的〈洞〉那一段：
#: SDD `context_ledger` 也有一條 90% 線，兩邊的分子分母都不同，同一時刻會給出不同的
#: 百分比。不標示的話，讀者拿到兩個數字會以為其中一個壞了。
MEASURE_LABEL = "session 實測"

#: SDD 情境專屬的補充手法。**只在 `SDD_ACTIVE_VERSION` 有設時才印**——裸 `/compact`
#: 與「先產 Stage Summary 再壓縮」是兩種東西，後者綁 SDD 的 FSM 閉環，無條件推薦
#: 會讓純 AutoClaude session 收到一條它根本執行不了的指引。
SDD_STAGE_HINT = (
    "     （本 session 有設 SDD_ACTIVE_VERSION ⇒ 別裸 compact：先走 `stage-compaction`"
    " skill 產 Stage Summary 再壓縮，否則 FSM 閉環與已凍結文件的脈絡會一起掉。）\n"
)

#: state 檔前綴。放系統暫存而非 repo 內：逐字稿是機器本地資料，且 repo 內不得有
#: 可寫暫存目錄（`tools/tests/test_platform_neutral_paths.py` 有專屬判準）。
STATE_PREFIX = "autosdd_ctxguard_"
PLAN_PREFIX = "autosdd_resume_plan_"


def used_of(usage: object) -> int | None:
    """單筆 `message.usage` 的當前 context 佔用；`None`＝這筆不是可用的 usage。
    只認 `int`（`bool` 排除，避免 `True` 算成 1）；欄位缺一律當 0，但整筆零欄位
    時回 `None`——「量到零」與「量不到」分得開是本檔通篇的紀律。"""
    if not isinstance(usage, dict):
        return None
    total = 0
    seen = False
    for field in USAGE_FIELDS:
        value = usage.get(field)
        if isinstance(value, int) and not isinstance(value, bool):
            total += value
            seen = True
    return total if seen else None


def scan_transcript(path: Path) -> tuple[int | None, int, str | None]:
    """逐行掃 jsonl，回 `(最後一筆 used, 歷來最大 used, 最後一個實際跑過的 model)`。
    model 一起掃出是為了 window 判定的交叉否決（`window_from_model`），且必須與
    usage 同一趟掃完；`<synthetic>` 佔位值不採計。逐行覆寫 last 而非整檔排序的
    三段省法（子字串預篩／記憶體 O(1)／壞行跳過）全文搬證據檔〈第七輪 史料搬遷
    （Dev-S8b）〉節。"""
    last: int | None = None
    peak = 0
    model: str | None = None
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if '"usage"' not in line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(record, dict) or record.get("type") != "assistant":
                    continue
                message = record.get("message")
                if not isinstance(message, dict):
                    continue
                seen_model = message.get("model")
                if seen_model == SYNTHETIC_MODEL:
                    # 🔴 R79：合成記錄整筆退出**用量累計**，不只是退出 model 判定——
                    # 它的 usage 三欄都在且都是 0（佔位不是用量），採計會讓水位在額度
                    # 耗盡那一刻掉成 0.0% ⇒ 最需要任務書的那一刻守衛整支靜默。
                    # 完整立案敘事（全庫 135 筆實測）見
                    # `CrossPlatform_R91_Scan_Findings.md` §A-8（R92 搬出）。
                    continue
                if isinstance(seen_model, str):
                    model = seen_model
                value = used_of(message.get("usage"))
                if value is None:
                    continue
                last = value
                peak = max(peak, value)
    except OSError:
        return None, 0, None
    return last, peak, model


def compact_boundary_count(path: Path) -> int:
    """本 session 逐字稿裡 `type=="system" and subtype=="compact_boundary"` 的累計次數
    （`latch_key` 靠它重新武裝）。獨立成一支函式而非併入 `scan_transcript`——後者三元組
    回傳值已有多個三元解包呼叫端。完整立案敘事見證據檔 §I-10。"""
    count = 0
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if '"compact_boundary"' not in line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if (isinstance(record, dict) and record.get("type") == "system"
                        and record.get("subtype") == "compact_boundary"):
                    count += 1
    except OSError:
        return 0
    return count


def _positive_int(raw: object) -> int:
    """能讀成正整數就回它，否則回 0。壞值一律 0——0 會讓 `tier_of` 永遠沉默，
    所以它**不得**被當成 window 採用，只能是「這個來源說不出話」的表示。"""
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return 0
    return value if value > 0 else 0


def carries_wide_marker(model: object) -> bool:
    """model 字串是否帶 1M context 標記（`opus[1m]`／`…-1m`）。

    刻意只認這兩種寫法而不做模糊比對：`claude-opus-4-1` 這種尾碼帶 1 的模型名一旦
    被誤判成 1M，分母就會偏大＝往「到 90% 才喊時真實水位已 450%」的危險方向錯。
    """
    text = str(model or "").strip().lower()
    return "[1m]" in text or text.endswith("-1m")


def model_family(model: object) -> str:
    """取 model 字串裡的家族字（`opus[1m]` → `opus`；`claude-opus-5` → `opus`）。只
    用來做交叉否決（設定寫的與逐字稿實際跑的是不是同一族），不用來判 window；回空
    字串＝認不出來 ⇒ 呼叫端一律當「無法否決」處理（不敢否決就不否決）。"""
    text = str(model or "").strip().lower()
    for family in ("opus", "sonnet", "haiku", "fable"):
        if family in text:
            return family
    return ""


def window_from_model(hint: object, observed: object = None) -> int | None:
    """設定層 model 欄推出的 window；`None`＝這一階說不出話（往下一階走）。交叉否決：
    `observed` 認得出家族、且與 `hint` 的家族不同 ⇒ 放棄——少了它，一次 `claude
    --model sonnet` 覆寫就會讓分母偏大五倍。`<synthetic>` 認不出家族，不誤殺。"""
    if not carries_wide_marker(hint):
        return None
    want, got = model_family(hint), model_family(observed)
    if want and got and want != got:
        return None
    return WIDE_WINDOW


_DATE_SUFFIX_RE = re.compile(r"-\d{8}$")
#: 查表資料相對 LATEST 版根目錄的路徑（資料只有一個家，見 `known_model_windows_path()`）。
_KNOWN_MODEL_WINDOWS_REL = ("tools", "fsm_runtime", "data", "known_model_windows.json")


def normalize_model_id(model: object) -> str:
    """查表鍵：去 `[1m]`／尾碼 `-1m`、小寫、去 `-YYYYMMDD` 日期尾碼（同 SDD `context_window.py`
    同名函式逐字同構——查表資料共用同一份，鍵的正規化規則不能各算各的）。"""
    text = str(model or "").strip().lower().replace("[1m]", "").strip()
    if text.endswith("-1m"):
        text = text[:-3]
    return _DATE_SUFFIX_RE.sub("", text)


def _known_table_cache_path(session_id: str) -> Path:
    """D27／效能：per-session 快取檔，記已解出的表路徑——省掉每次工具呼叫都重跑一次
    `git ls-files`。住 `_latch_marker_dir()` 同一個目錄，生命週期跟著閂鎖檔走。"""
    return _latch_marker_dir(state_path(session_id)) / "known_model_windows_path.cache"


def known_model_windows_path(root: Path | None = None,
                             session_id: str | None = None) -> Path | None:
    """LATEST 版 `known_model_windows.json` 的路徑；解析不到／檔不存在一律 `None`（D21 fail-open，
    全文見 moved_lore.md）。`session_id` 有給時先查後寫 per-session 快取，命中即免解析。"""
    cache = _known_table_cache_path(session_id) if session_id else None
    if cache is not None:
        try:
            if (cached := Path(cache.read_text(encoding="utf-8").strip())).is_file():
                return cached
        except OSError:
            pass
    if sdd_latest is None:
        sys.stderr.write("⚠️  known_model_windows fail-open：sdd_latest 模組不可達，不收斂\n")
        return None
    sdd_root = (root or repo_root()) / "AISDLC_SDD"
    try:
        if not sdd_root.is_dir():
            sys.stderr.write(
                f"⚠️  known_model_windows fail-open：無 AISDLC_SDD 子專案（{sdd_root}），不收斂\n"
            )
            return None
        # D27：熱路徑版——本函式現改每次工具呼叫都會被叫到，見 `sdd_latest.py` 該函式 WHY。
        latest_root = sdd_latest.resolve_latest_root_fast(sdd_root)
    except Exception as exc:  # noqa: BLE001 — 解析失敗一律 fail-open、不收斂（D21）
        kind = "有子專案無版本目錄" if "找不到任何版本目錄" in str(exc) else "LATEST 解析失敗"
        sys.stderr.write(f"⚠️  known_model_windows fail-open：{kind}（{sdd_root}）：{exc}，不收斂\n")
        return None
    path = latest_root.joinpath(*_KNOWN_MODEL_WINDOWS_REL)
    if not path.is_file():
        sys.stderr.write(f"⚠️  known_model_windows fail-open：表檔不存在（{path}），不收斂\n")
        return None
    if cache is not None:
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(str(path), encoding="utf-8")
        except OSError:
            pass
    return path


def load_known_model_windows(path: Path | None) -> tuple[dict[str, int], str]:
    """回 `({正規化 model id: window}, 來源描述)`；讀不到／壞掉一律 `({}, _NO_TABLE_NOTE)`
    （fail-open）。tuple 形態同 SDD 同名函式，讓 `refreshed_at` 帶進 ⑥ 階的訊息。"""
    if path is None:
        return {}, _NO_TABLE_NOTE
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"⚠️  known_model_windows fail-open：JSON 損毀（{path}）：{exc}，不收斂\n")
        return {}, _NO_TABLE_NOTE
    if not isinstance(doc, dict) or not isinstance(doc.get("models"), dict):
        sys.stderr.write(f"⚠️  known_model_windows fail-open：JSON 形狀不對（{path}），不收斂\n")
        return {}, _NO_TABLE_NOTE
    table: dict[str, int] = {}
    for model_id, window in doc["models"].items():
        if (isinstance(model_id, str) and isinstance(window, int)
                and not isinstance(window, bool) and window > 0):
            table[normalize_model_id(model_id)] = window
    refreshed = doc.get("refreshed_at")
    note = (f"refreshed_at={refreshed}" if isinstance(refreshed, str) and refreshed
            else f"未刷新，seeded_from={doc.get('seeded_from') or '?'}")
    return table, note


def _not_converged_note(source: str, key: str, table_value: int) -> str:
    """查過表、沒收斂時附註的證據（D21／SD-09）。插進來源說明的括號內，讓 `--check`
    印得出「有沒有真的查過表、比較結果是什麼」，不論收不收斂。"""
    note = f"；查表 {key}={table_value:,} ≥ 指定值，不收斂"
    return source[:-1] + note + "）" if source.endswith("）") else source + note


def _converge_pinned_window(
    pinned: int, observed_model: object, known_models: dict[str, int] | None,
) -> tuple[int, str] | None:
    """釘值 vs 查表值的收斂（D21，鏡射 SDD 同名函式：查表值嚴格小於指定值才收斂）。
    `None`＝查不到表／認不出 model，呼叫端沿用原本來源說明。"""
    if not known_models:
        return None
    key = normalize_model_id(observed_model)
    if not key or key not in known_models:
        return None
    table_value = known_models[key]
    if table_value < pinned:
        return table_value, (
            f"{SOURCE_KNOWN_MODEL_PREFIX}，model={key}；"
            f"指定值 {pinned:,} 大於該模型上限，已收斂）"
        )
    return None  # 沒收斂——附註由呼叫端用 `_not_converged_note()` 補上（它還要原本的 source）


def known_model_window(
    model_hint: object, observed_model: object, known_models: dict[str, int] | None,
) -> tuple[int, str] | None:
    """D27：查表階（⑥），同 SDD 同名函式。逐字稿 model 優先於 hint；`None`＝說不出話。"""
    if not known_models:
        return None
    for candidate in (observed_model, model_hint):
        key = normalize_model_id(candidate)
        if key and key in known_models:
            return known_models[key], key
    return None


#: D32-2 SSOT：feed 檔目錄。與 `tools/statusline_context_feed.py`、SDD
#: `context_window.py` 的同名函式逐字同構（parity 見 `test_context_window_parity.py`）。
CONTEXT_FEED_DIR_ENV = "AUTOSDD_CONTEXT_FEED_DIR"


def context_feed_path(session_id: str) -> Path:
    """Feed 檔路徑（D32-2）。三份同名函式（本檔／SDD／status line 寫入端）逐字同構。"""
    base = os.environ.get(CONTEXT_FEED_DIR_ENV)
    root = Path(base) if base else Path(os.path.expanduser("~")) / ".autosdd" / "context_feed"
    return root / f"{session_id}.json"


def read_context_feed(session_id: str | None, observed_model: object) -> dict:
    """讀 status line feed（D32-3／D32-4／D32b-3）。回 `{window, note, used, reason}`；
    fail-open：解析失敗一律當「沒有 feed」，`reason` 給讀者一句能懂的話——**沒有
    feed 檔本身也是一種 reason**（statusLine 未設定或本 session 太新），不是壞事，
    但不採用的原因不該被悄悄吞掉（D32b-3：這句話要被 `cross_check_note()`／
    `tools/lib/harness_feed.py` 印出來）。
    """
    empty = {"window": None, "note": "", "used": None, "reason": None}
    if not session_id:
        return {**empty, "reason": "無 session_id"}
    try:
        raw = context_feed_path(session_id).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {**empty, "reason": "無 feed（statusLine 未設定或本 session 尚無 assistant 訊息）"}
    except OSError:
        return {**empty, "reason": "feed 讀不到（非不存在）"}
    try:
        doc = json.loads(raw)
    except ValueError:
        return {**empty, "reason": "feed 壞 JSON"}
    if not isinstance(doc, dict) or doc.get("session_id") != session_id:
        return {**empty, "reason": "feed 缺失或 session_id 不符"}
    cw = doc.get("context_window")
    size = _positive_int(cw.get("context_window_size")) if isinstance(cw, dict) else 0
    if size <= 0:
        return {**empty, "reason": "feed 缺 context_window_size（或非正整數）"}
    feed_model = doc.get("model") if isinstance(doc.get("model"), dict) else {}
    feed_model_id = feed_model.get("id")
    want, got = model_family(observed_model), model_family(feed_model_id)
    if want and got and want != got:
        return {**empty, "reason": f"feed model 家族（{got}）與逐字稿（{want}）不符"}
    used = None
    current_usage = cw.get("current_usage") if isinstance(cw, dict) else None
    if isinstance(current_usage, dict):
        used = used_of(current_usage)
    return {"window": size, "note": f"model={feed_model_id or '?'}", "used": used, "reason": None}


def _harness_source(harness_note: str, pinned_raw: object, hw: int) -> str:
    """`SOURCE_HARNESS` 附註：feed model 說明＋（釘值存在且與 harness 不同時）標出未採用。"""
    extra = [harness_note] if harness_note else []
    pinned = _positive_int(pinned_raw) if pinned_raw is not None else 0
    if pinned > 0 and pinned != hw:
        extra.append(f"釘值 {pinned:,} 未採用")
    if not extra:
        return SOURCE_HARNESS
    note = "；" + "；".join(extra)
    if SOURCE_HARNESS.endswith("）"):
        return SOURCE_HARNESS[:-1] + note + "）"
    return SOURCE_HARNESS + note


def resolve_window(
    peak_used: int,
    env_raw: str | None = None,
    *,
    cc_window_raw: object = None,
    settings_window: object = None,
    model_hint: object = None,
    observed_model: object = None,
    known_models: dict[str, int] | None = None,
    known_models_note: str = "",
    harness_window: object = None,
    harness_note: str = "",
) -> tuple[int, str]:
    """`(window, 來源說明)`。純函式——紅綠由注入自證，不讀環境／不讀檔（呼叫端傳入）。

    順序即優先序（詳見模組 docstring〈context window 判定〉）：⓪ harness 回報 →
    本檔旗標 → harness 旋鈕（皆與 `known_models` 收斂）→ model 標記（帶交叉否決）→
    ⑥ 查表 → 可證下界推論 → 保守值。新增的 `harness_*` 皆 keyword-only、預設 `None`
    即整階跳過，舊呼叫端行為逐位元組不變（parity 鎖不受影響）。
    """
    hw = _positive_int(harness_window) if harness_window is not None else 0
    if hw > 0:
        return hw, _harness_source(harness_note, env_raw, hw)
    for raw, source in (
        (env_raw, SOURCE_PINNED),
        (cc_window_raw, SOURCE_PINNED_CC_ENV),
        (settings_window, SOURCE_PINNED_CC_SETTING),
    ):
        if raw is None:
            continue
        pinned = _positive_int(raw)
        if pinned > 0:
            converged = _converge_pinned_window(pinned, observed_model, known_models)
            if converged is not None:
                return converged
            key = normalize_model_id(observed_model)
            if known_models and key and key in known_models:
                return pinned, _not_converged_note(source, key, known_models[key])
            return pinned, source
    from_model = window_from_model(model_hint, observed_model)
    if from_model is not None:
        return from_model, SOURCE_MODEL_MARKER
    from_table = known_model_window(model_hint, observed_model, known_models)
    if from_table is not None:
        window, key = from_table
        note = f"，{known_models_note}" if known_models_note else ""
        return window, f"{SOURCE_KNOWN_MODEL_PREFIX}，model={key}{note}）"
    if peak_used > CONSERVATIVE_WINDOW:
        return WIDE_WINDOW, SOURCE_INFERRED_WIDE
    return CONSERVATIVE_WINDOW, SOURCE_INFERRED_FLOOR


def may_block(source: str) -> bool:
    """這個 window 來源夠不夠格用來**硬擋**工具。

    只有保守下界（＝「我不知道，先給個安全的小數字」）不夠格：拿猜出來的分母去鎖
    工具，正是本輪要修的那個缺陷換個方向再犯一次（1M session 會在真實 18% 被鎖死）。
    `SOURCE_INFERRED_WIDE` 夠格——它猜大的方向只會讓阻斷**晚**發生，不會誤擋。
    """
    return source != SOURCE_INFERRED_FLOOR


def tier_of(used: int, window: int) -> str | None:
    """`None`／`TIER_WARN`／`TIER_HARD`。window 非正數一律 `None`（不對零做除法）。"""
    if window <= 0:
        return None
    ratio = used / window
    if ratio >= HARD_RATIO:
        return TIER_HARD
    if ratio >= WARN_RATIO:
        return TIER_WARN
    return None


def session_id_of(transcript: Path) -> str:
    """逐字稿檔名（去副檔名）即 session id；非英數字元一律換成 `-`——這個字串會變成
    暫存檔名的一部分，未清洗的路徑分隔符會讓 state 檔寫錯目錄（或 Windows 上寫檔失敗）。"""
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in transcript.stem)


def state_path(session_id: str, tmp_dir: str | None = None) -> Path:
    return Path(tmp_dir or tempfile.gettempdir()) / f"{STATE_PREFIX}{session_id}.json"


def latch_key(tier: str, window: int, epoch: int = 0) -> str:
    """閂鎖鍵＝(門檻, 分母, compact 週期)。分母必須進鍵（R79：誤報吃掉真正那一次）；
    `epoch`＝`compact_boundary_count()`（R92／D3：跨過一次真 compact 才重新武裝，
    同週期內 one-shot 語意零改變）。完整立案敘事見證據檔 §I-3／§I-10。"""
    return f"{tier}@{window}@{epoch}"


def _latch_marker_dir(state: Path) -> Path:
    """D22（SD-05）：`state` 對應的原子標記檔目錄——每個 key 一個檔，取代單一 JSON 檔。"""
    return state.parent / f"{state.stem}.latches.d"


def _latch_marker_name(key: str) -> str:
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:24] + ".key"


def announced_latches(state: Path) -> set[str]:
    """已喊過的 (門檻, 分母) 集合。讀不出來一律回空集合（寧可多喊一次，也不要靜默失聲）。"""
    out: set[str] = set()
    try:
        entries = list(_latch_marker_dir(state).iterdir())
    except OSError:
        return out
    for entry in entries:
        try:
            out.add(entry.read_text(encoding="utf-8"))
        except OSError:
            continue
    return out


def remember_latch(state: Path, key: str) -> None:
    """把 key 記進去（D22／SD-05：`O_CREAT|O_EXCL` 原子建檔，每個 key 一個檔天生不
    衝突，競爭輸的那邊安靜跳過）。寫失敗一律吞掉——最壞情況是下次再喊一次。"""
    marker_dir = _latch_marker_dir(state)
    try:
        marker_dir.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(marker_dir / _latch_marker_name(key)),
                     os.O_CREAT | os.O_EXCL | os.O_WRONLY | _BINARY, 0o600)
        try:
            os.write(fd, key.encode("utf-8"))
        finally:
            os.close(fd)
    except OSError:
        pass


def repo_root() -> Path:
    """monorepo 根。`CLAUDE_PROJECT_DIR` 由 Claude Code 注入，缺席時以本檔位置
    （`.claude/hooks/<本檔>` 上溯兩層）而不是 cwd 推——cwd 由註冊面的 shim 決定，
    那是別人的實作細節，被改掉時本檔不該跟著壞。"""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        candidate = Path(env)
        if candidate.is_dir():
            return candidate
    return Path(__file__).resolve().parents[2]


def settings_chain(root: Path | None = None) -> list[Path]:
    """Claude Code settings 檔，**由高優先到低優先**。刻意不含 enterprise policy
    層（讀它也沒意義：只會讓分母更小＝更早喊，方向安全）。誠實劃界：`--settings`
    旗標與 `/model` 的 session 內覆寫本檔看不到，這正是 `window_from_model` 要用
    逐字稿實跑 model 做交叉否決的原因。"""
    base = root or repo_root()
    return [
        base / ".claude" / "settings.local.json",
        base / ".claude" / "settings.json",
        Path(os.path.expanduser("~")) / ".claude" / "settings.json",
    ]


def settings_value(key: str, paths: list[Path] | None = None) -> object:
    """settings 鏈裡第一個有這個鍵的值；沒有就 `None`。任何讀檔／解析失敗一律跳過。"""
    for path in paths if paths is not None else settings_chain():
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get(key) is not None:
            return data[key]
    return None


def window_evidence(observed_model: str | None, session_id: str | None = None,
                    *, feed: dict | None = None) -> dict:
    """把 `resolve_window` 需要的證據一次收齊（I/O 都在這裡，判定仍是純函式）。
    D27：無條件查表，沿革見證據檔〈第七輪〉。`feed` 讓呼叫端重用已讀過一次的
    status line 進料（D32b-1a：消除 `main()` 內的重複讀檔），缺席才自己讀一次。
    """
    known_models, known_models_note = load_known_model_windows(
        known_model_windows_path(session_id=session_id))
    if feed is None:
        feed = read_context_feed(session_id, observed_model)
    return {
        "env_raw": os.environ.get(WINDOW_ENV),
        "cc_window_raw": os.environ.get(CC_WINDOW_ENV),
        "settings_window": settings_value(CC_WINDOW_KEY),
        "model_hint": settings_value(CC_MODEL_KEY),
        "observed_model": observed_model,
        "known_models": known_models,
        "known_models_note": known_models_note,
        "harness_window": feed["window"],
        "harness_note": feed["note"],
    }


def write_resume_plan(transcript: Path) -> str:
    """呼叫 `tools/session_resume_planner.py` 產出任務書骨架；回傳路徑（失敗回空字串）。
    走 subprocess 而不是 import（`tools/` 不在 hook 的 `sys.path` 上）；子行程 stdout/
    stderr 明確宣告 UTF-8，避免 zh-TW cp950 讀子行程輸出炸 UnicodeDecodeError；任何
    失敗一律吞掉——任務書寫不出來時，使用者仍該拿到那段強制指引。"""
    planner = repo_root() / "tools" / "session_resume_planner.py"
    if not planner.is_file():
        return ""
    out = Path(tempfile.gettempdir()) / f"{PLAN_PREFIX}{session_id_of(transcript)}.md"
    try:
        subprocess.run(
            [quiet_python(), str(planner), "--transcript", str(transcript),
             "--out", str(out)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            # 15s 遠大於實測（planner 對 1.18 MiB 逐字稿 < 1s），但**必須小於註冊面
            # 的 `timeout`**：CC 若先砍掉本 hook，那段強制指引就一個字都印不出來
            # ——為了寫任務書而弄丟指引，方向剛好相反。建議註冊 timeout 取 30。
            timeout=15,
            check=False,
            # 本 hook 行程沒有 console，而 planner 是 console 子系統的 python.exe
            # ⇒ 不帶這個旗標時每次越過硬線（HARD_RATIO）都會彈一個視窗（見 NO_WINDOW 的實測表）。
            creationflags=NO_WINDOW,
        )
    except Exception:  # noqa: BLE001 — 診斷輔助不得反過來變成守衛的故障源
        return ""
    return str(out) if out.is_file() else ""


# ───────── 預防性哨兵的**觸發層**（R82／HELM-02：SessionStart 只清閂鎖，真正註冊延後到
# PostToolUse 且要通過 `sentinel_lifecycle.should_arm()`；全文搬 moved_lore.md）。
def spawn_sentinel(transcript_raw: str, out: str, log: object = None) -> bool:
    """Detached 起 planner 的 `--arm-sentinel`；回「有沒有真的 spawn 出去」（R82／Q2-02 的
    減法：SessionStart 武裝與額度 95% 喚醒武裝共用同一份實作，避免各自演化漂移）。"""
    planner = repo_root() / "tools" / "session_resume_planner.py"
    if not _has_carrier() or not planner.is_file() or not transcript_raw or not out:
        return False
    try:
        subprocess.Popen(  # noqa: S603 — 參數全是本檔算出來的路徑，無 shell
            [quiet_python(), str(planner), "--transcript", transcript_raw,
             "--out", out, "--arm-sentinel"],
            stdout=log if log is not None else subprocess.DEVNULL,
            stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            # 🔴 R80：不帶 `DETACHED_PROCESS`（它在本 venv 的 trampoline 載具上會讓視窗回來，
            # 全文搬 moved_lore.md）；「不同步等它跑完」由不呼叫 `wait()` 提供，與旗標無關。
            creationflags=NO_WINDOW)
    except Exception:  # noqa: BLE001 — 見上方取捨③：武裝失敗不得反過來變成故障源
        return False
    return True


def arm_sentinel(payload: dict) -> None:
    """SessionStart：**不再直接武裝**，只把上一輪的武裝閂鎖清掉並留一行痕跡（`claude -r`
    續接已下班 session 時閂鎖若留著會讓續航靜默弄丟；boot log 是「有沒有被叫到」的痕跡）。"""
    if not _has_carrier() or os.environ.get(SENTINEL_OFF_ENV):
        return  # 沒有排程載具就沒有續航可言（見 `_has_carrier`）；人要關就關得掉
    if not isinstance(raw := payload.get("transcript_path"), str) or not raw.strip():
        return
    sid = session_id_of(Path(raw))
    if sentinel_lifecycle is not None:
        sentinel_lifecycle.clear_arm_latch(sid)
    swept = spawn_sentinel_gc(sid)
    with (Path(tempfile.gettempdir()) / f"autosdd_sentinel_boot_{sid}.log").open(
            "a", encoding="utf-8", errors="replace") as handle:
        handle.write(f"\n=== session-start {datetime.now().isoformat(timespec='seconds')}"
                     f" （閂鎖已清；武裝延後到累積夠工作量的那一刻）｜孤兒回收 spawn={swept} ===\n")


# 🔴 R84／C3-P4b：`sentinel_lifecycle.gc()` 此前零自動呼叫端，殘骸哨兵照樣醒來（全文搬
# moved_lore.md）。取捨同 `spawn_sentinel`：detached／自己的哨兵不能被自己收掉／吞例外。
def spawn_sentinel_gc(keep_sid: str) -> bool:
    """Detached 起 `sentinel_lifecycle --gc --apply`；回「有沒有真的 spawn 出去」。"""
    lifecycle = repo_root() / "tools" / "lib" / "sentinel_lifecycle.py"
    if not _has_carrier() or not lifecycle.is_file() or not keep_sid:
        return False
    try:
        subprocess.Popen(  # noqa: S603 — 參數全是本檔算出來的路徑／本 session 的 id
            # 🔴 沒有 `--gc` 這個旗標：回收**就是**這支 CLI 的唯一動作（`main()` 無子指令）。
            # 多送一個不存在的旗標會讓 argparse 直接 rc=2 而什麼都不收，且因為 stdout 全丟
            # DEVNULL，那個失敗**完全靜默**——正是本輪在治的那一族。
            [quiet_python(), str(lifecycle), "--apply", "--keep", keep_sid],
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
    except Exception:  # noqa: BLE001 — 見上方取捨③
        return False
    return True


def arm_when_earned(transcript: Path) -> str:
    """PostToolUse：夠格才武裝。回理由字串（呼叫端不讀，留給測試與未來的痕跡）。
    一切例外吞掉：武裝失敗最多是少一層保護，絕不可反過來變成故障源（hook 誤觸的
    P0 硬鎖見 `.claude/settings.json` description）。"""
    if (not _has_carrier() or os.environ.get(SENTINEL_OFF_ENV)
            or sentinel_lifecycle is None):
        return "disabled"
    sid = session_id_of(transcript)
    try:
        return sentinel_lifecycle.maybe_arm(
            transcript, sid, spawn=spawn_sentinel,
            plan_path=str(Path(tempfile.gettempdir()) / f"{PLAN_PREFIX}{sid}.md"))
    except Exception:  # noqa: BLE001 — 見上
        return "error"


def arm_quota_wakeup(transcript: Path | None, plan: str) -> dict:
    """額度 95%／`arm` 分支的喚醒武裝；回 `{armed, sentinel_off, posix}` 給訊息用。
    `armed`＝**真的 spawn 出去了**；`posix`＝這台機器沒有排程載具（mac 上為 False）。
    全文（含 R83／W2-A 沿革）逐字保全於 CrossPlatform_DEF200275_Context_Metering_
    Evidence.md〈第七輪 史料搬遷〉節。"""
    if not _has_carrier():
        return {"armed": False, "sentinel_off": False, "posix": True}
    if os.environ.get(SENTINEL_OFF_ENV):
        return {"armed": False, "sentinel_off": True, "posix": False}
    return {"armed": transcript is not None and spawn_sentinel(str(transcript), plan),
            "sentinel_off": False, "posix": False}


def _headline(used: int, window: int, source: str) -> str:
    return (f"{used / window:.1%}"
            f"（{MEASURE_LABEL}：used {used:,} / window {window:,}〔{source}〕）")


#: 84% 那一格的**下一步**，依額度相對 PRD `DRAIN_PERCENT` 的位置三分（`quota_gate.draining()`）；
#: PRD §4.3 三個 AND 條件與立案史全文搬 moved_lore.md（R91）。
_NEXT_STEP = {
    "no": ("   機械 autocompact 將於觸發點自動壓縮（模型自身打不了 `/compact`，人在旁可手動——"
           "ADR-XPLAT-008；額度現查：五小時軸連同 PRD `COMPACT_COST_BUDGET_PP` 邊際仍在 "
           "DRAIN 線下）。此時仍可開新工作。\n"),
    "yes": ("   🔴 **不要 `/compact`**——額度已越過 PRD `DRAIN_PERCENT`（prepare／halt 帶）。"
            "壓縮要模型讀完整段對話再產摘要 ⇒ 會顯著推升 U5h，在這一帶壓縮是反向操作"
            "（PRD §0 第 1 條：阻斷級）。\n"
            "   改走**交棒**（PRD §4.3 指定的替代路線「主動結束該 Step 並以新 session 交棒」）："
            "把狀態寫成磁碟任務書 `python tools/session_resume_planner.py`，結束本 Step，"
            "以 `claude -r <sessionId>` 或新 session 續作。\n"),
    "unknown": ("   ⚠️ 額度**量不到** ⇒ PRD §4.3 的第二個 AND 條件證不出成立，依 §0 第 6 條"
                "（遙測失效即 fail-safe）不得逕行壓縮。\n"
                "   先現查 `python tools/lib/quota_meter.py --json`：量得到且未越 DRAIN 線"
                "再 `/compact`；仍量不到就走交棒 `python tools/session_resume_planner.py`。\n"),
}


def cross_check_note(used: int, feed: dict) -> str:
    """D32-4／D32b-3：status line feed 的旁註，純函式（`feed` 由呼叫端傳入，
    不在此重複讀檔——D32b-1a）。未採用時把 `reason` 印出來（沒有 feed 也是一種
    reason，不得被悄悄吞掉）；已採用時做分子交叉比對，差 >5% 才出聲。"""
    if feed.get("reason") is not None:
        return f"   ℹ️  harness feed 未採用：{feed['reason']}\n"
    harness_used = feed.get("used")
    if harness_used is None or harness_used <= 0 or used <= 0:
        return ""
    diff = abs(used - harness_used)
    if diff / max(used, harness_used) <= 0.05:
        return ""
    return (f"   ℹ️  分子交叉比對：harness used={harness_used:,} 逐字稿 used={used:,}"
            f" 差={diff:,}（>5%，僅供參考，不影響本次判定）\n")


def warn_message(used: int, window: int, source: str, drain: str = "unknown") -> str:
    """84% 提示。`drain`＝`quota_gate.draining()` 的三態，未知一律走 fail-safe 那一格。"""
    return (
        f"⚠️  context 水位 {_headline(used, window, source)}——已越過 {WARN_RATIO:.0%}。\n"
        f"{_NEXT_STEP.get(drain, _NEXT_STEP['unknown'])}"
        f"   （根 CLAUDE.md〈Token 將耗盡時的無害暫停〉三段式水位，R92 起 {WARN_RATIO:.0%}"
        f"＝收斂前置、{HARD_RATIO:.0%}＝壓縮未發生警報、撞上限才重啟。"
        "🔴 該表量的是 context，額度是另一把尺——本行已把兩者都問過了。）\n"
        f"   要精確判定分母就設 {WINDOW_ENV}；本行的 window 來源已標在括號裡。\n"
        "   （同一門檻本 session 只喊這一次）\n"
    )


def hard_message(used: int, window: int, source: str, plan: str,
                 sdd_active: bool = False) -> str:
    plan_line = (
        f"  3. 「可重啟點」任務書骨架已寫到：{plan}\n"
        "     🔴 裡面帶 `TODO:` 的欄位本守衛**不會**替你填——它不知道你驗過什麼。\n"
        if plan else
        "  3. 任務書：`python tools/session_resume_planner.py`（本次自動產生失敗，請手動跑）\n"
    )
    return (
        f"🔴 context 水位 {_headline(used, window, source)}——已越過 {HARD_RATIO:.0%} 硬線。\n"
        "   機械 autocompact 已由 repo settings 釘住（autoCompactEnabled ＋"
        " CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=90 ⇒ 正常應在 ~90% 就自動壓縮）——"
        "你讀到這行代表壓縮**沒有發生**（或發生後又漲回來）。\n"
        "   此後**只做收斂，不做展開**（根 CLAUDE.md〈Token 將耗盡時的「無害暫停 →"
        " reset 後重啟」SOP〉）：\n"
        "  1. 立刻 `/compact`，並現查姿態找出它為何沒觸發："
        "`python tools/session_resume_planner.py --check-autocompact`。\n"
        f"{SDD_STAGE_HINT if sdd_active else ''}"
        "  2. 把工作樹收到「可重啟點」四條件：① 已 commit 且閘門全綠，或"
        " `git stash create` ＋ `git tag <輪次>-wip-preserved`（絕不留半套 edit 就走）；"
        "② 任務書落在**磁碟**（對話會被 compact、session 會換）；③ 任務書含四項"
        "（已驗證什麼＋實測數字與 rc／還沒做什麼／下一步的確切指令／禁止事項）；"
        "④ 重啟後第一件事是**重驗**，不採信任務書裡任何「已通過」宣稱。\n"
        f"{plan_line}"
        "  4. 撞上限後重啟：`claude -r <sessionId>`（session id 見上面那份任務書）。\n"
        "     🔴 **不要**用 `CronCreate`——`CronList` 對它的標記是 `[session-only]`，"
        "session 關掉就沒了，不是離線排程。要離線排程只有 `schtasks` 一條路，且\n"
        "     宣稱「已排程」的**同一則回覆**必須附排程器自己回報的 `NextRunTime` 實測"
        "輸出（根 CLAUDE.md〈反「事後諸葛」取證規則〉）；貼不出來就只能說「我做不到」。\n"
        "  （同一門檻本 session 只喊這一次——這是刻意的：每次工具呼叫都 exit 2 的守衛"
        "會被整個關掉。回歸鎖 tools/tests/test_context_budget_guard.py）\n"
    )


def block_message(used: int, window: int, source: str, tool: str) -> str:
    """PreToolUse 阻斷訊息。必須逐字給出下一步，否則擋下來只是製造挫折。"""
    return (
        f"🔴 context 水位 {_headline(used, window, source)}——已越過 {HARD_RATIO:.0%} 硬線，"
        f"`{tool}` 這類**展開型**工具已被擋下。\n"
        "   根 CLAUDE.md〈Token 將耗盡時的「無害暫停 → reset 後重啟」SOP〉：此後"
        "**只做收斂，不做展開**。Read／Edit／PowerShell 仍然放行，收斂做得完。\n"
        "   下一步（照順序做）：\n"
        "  1. `/compact`（本 session 的 harness autocompact 姿態現查："
        "`python tools/session_resume_planner.py --check-autocompact`）。\n"
        "     compact 之後 used 會真的掉下來，本阻斷**自動解除**，不需要任何人去關它。\n"
        "  2. 把工作樹收到「可重啟點」：已 commit 且閘門全綠，或 `git stash create`"
        " ＋ `git tag <輪次>-wip-preserved`。絕不留半套 edit 就走。\n"
        "  3. 任務書：`python tools/session_resume_planner.py`（含重啟指令）。\n"
        f"   誤判時的逃生口（給人用，不是給模型用）：設 {GUARD_OFF_ENV}=1 一律放行；"
        f"分母不對就設 {WINDOW_ENV}=<真實 window>。本次分母來源已標在上面括號裡。\n"
    )


def main() -> int:
    try:
        # 🔴 R82／C2：`.env` 裡我們自己宣告過的鍵（`ENV_SPEC` 白名單）填成行程級預設，
        # 缺席才填、真環境變數仍贏；放 `main()` 而非模組層（避免測試 import 被開發機 `.env`
        # 影響）。回歸鎖：`EnvFileReachesEveryEscapeHatchTest`。
        if quota_gate is not None:
            quota_gate.apply_env_defaults(os.environ)
        payload = read_payload()
        if payload is None:
            # 退化 payload：出聲但不阻斷（rc=1）。靜默放行會讓「送壞 payload」成為
            # 讓守衛整支消失的免費手段，且失效時沒有人看得見（判準見模組 docstring）。
            sys.stderr.write(
                "⚠️  context 水位守衛讀不出 hook payload（壞 JSON 或空 stdin）"
                "——本次不做任何量測。守衛沒有靜默失效，但它這一次確實沒看到東西。\n"
            )
            return 1
        event = str(payload.get("hook_event_name") or "")
        if event == "SessionStart":
            # 清武裝閂鎖（R82／HELM-02：真正武裝延後到 PostToolUse）＋ v2.1.13 G2 未讀
            # handback 以 additionalContext 出聲（本體住 sentinel_lifecycle，此處只接線）。
            arm_sentinel(payload)
            if sentinel_lifecycle is not None:
                sentinel_lifecycle.announce_handbacks(lambda m: emit_to_model(event, m))
            return 0
        blocking = event == "PreToolUse"
        # 🔴 R83：額度軸只在真的推理過的這兩個事件上動作（白名單，不是「不是 PreToolUse
        # 就當 PostToolUse」）；且必須在下面五道 context 早退**之前**求值（SA-B1 判過的
        # 死碼：撞額度那刻水位常只有 ~18%，掛在早退之後一次都到不了）。全文搬 moved_lore.md。
        measuring = event in ("PreToolUse", "PostToolUse")
        raw_path = payload.get("transcript_path")
        transcript = Path(raw_path) if isinstance(raw_path, str) and raw_path.strip() else None
        # 🔴 DEF-200-202：模型分軌軸需要 `active_model` 才進 cap 聚合；提前掃逐字稿讓兩把
        # 尺共用同一次結果（`model_family()` 正規化到與 `axis.scope_model` casefold 相等
        # 的家族字，依據見 `quota_gate.quota_gate` 檔頭）。
        scanned = (scan_transcript(transcript) if measuring and transcript
                  and transcript.is_file() else None)
        active_model = model_family(scanned[2]) if scanned and scanned[2] else None
        if measuring and quota_gate is not None and (quota_stop := quota_gate.quota_gate(
                payload, blocking=BLOCKING_TOOLS, latch_read=announced_latches,
                latch_write=remember_latch, plan_writer=write_resume_plan,
                waker=arm_quota_wakeup, event=event, active_model=active_model or None)):
            # 🔴 R83／Δ13：halt 帶在 PostToolUse 每次都回 2，本 hook 在這裡提早 return——
            # 下面的 `arm_when_earned()` 仍須在此補呼叫一次，否則整個 halt 期間 context
            # 續航哨兵會靜默失去所有武裝機會（兩層續航職責不同，全文搬 moved_lore.md）。
            if not blocking and transcript is not None and transcript.is_file():
                arm_when_earned(transcript)
            return quota_stop
        if transcript is None:
            return 0  # 量測暫時不可得 ≠ 輸入壞掉，見模組 docstring 的行為契約
        if not transcript.is_file():
            return 0
        # 🔴 哨兵武裝掛在這裡（不是 SessionStart，理由見 `arm_when_earned` 上方那段），而且
        # **必須在下面五道 context 早退之前**：`tier_of()` 在低於 WARN_RATIO 時一律回 `None`，掛在
        # 後面等於永遠不會被執行（同 SA-B1 判過的死碼形狀，只是換一把尺）。閂鎖已設時它只
        # 做一次 `Path.exists()`，所以放在每次工具呼叫都會經過的路徑上是付得起的。
        if not blocking:
            arm_when_earned(transcript)

        used, peak, model = scanned if scanned is not None else scan_transcript(transcript)
        if used is None:
            return 0  # 掃不到任何 usage：量不到 ≠ 量到零，不做任何宣稱
        sid = session_id_of(transcript)
        feed = read_context_feed(sid, model)  # D32b-1a：整回合只讀一次，餵給下面兩處消費端
        window, source = resolve_window(peak, **window_evidence(model, session_id=sid, feed=feed))
        tier = tier_of(used, window)
        if tier is None:
            return 0

        if blocking:
            return block_verdict(payload, used, window, source, tier)

        state = state_path(sid)
        key = latch_key(tier, window, compact_boundary_count(transcript))
        if key in announced_latches(state):
            return 0
        remember_latch(state, key)

        if tier == TIER_WARN:
            # 🔴 R91：發話**之前**先問額度那把尺（零網路，只讀快取）。順序不能倒過來——
            # 訊息內容本身取決於答案（見 `_NEXT_STEP` 的立案）。`quota_gate` 不可達時
            # 三態退化成 `"unknown"`＝fail-safe 那一格，與本檔既有的降級方向一致。
            drain = quota_gate.draining() if quota_gate is not None else "unknown"
            message = warn_message(used, window, source, drain) + cross_check_note(used, feed)
            sys.stderr.write(message)
            # stderr 在 exit 0 下**不進模型 context**（官方契約）⇒ 這一行才是本輪要修的
            # 那一半。事件名由 payload 傳，不得寫死（R83／D3：不符即整段被 CC 丟掉）。
            if not os.environ.get(SIGNAL_OFF_ENV):
                emit_to_model(event, message)
            return 0
        sys.stderr.write(hard_message(
            used, window, source, write_resume_plan(transcript),
            sdd_active=bool(os.environ.get("SDD_ACTIVE_VERSION")),
        ) + cross_check_note(used, feed))
        return 2
    except Exception:  # noqa: BLE001 — fail-open 是刻意的，見模組 docstring 的 P0
        return 0


def block_verdict(payload: dict, used: int, window: int, source: str, tier: str) -> int:
    """PreToolUse 模式的判定。四道放行條件缺一，才會真的擋。

    刻意抽成獨立函式：阻斷是本檔唯一有爆炸半徑的行為，它的每一個放行條件都要能被
    逐條注入驗紅，而不是埋在 `main()` 的 try 裡跟量測邏輯混在一起。
    """
    if os.environ.get(GUARD_OFF_ENV):
        return 0  # 人為逃生口（對 P0 的第二道保險）
    if tier != TIER_HARD:
        return 0
    if not may_block(source):
        return 0  # 分母是猜的就不擋——猜錯會在真實 18% 把工具鎖死
    tool = str(payload.get("tool_name") or "")
    if tool not in BLOCKING_TOOLS:
        return 0  # 註冊面的 matcher 被改寬時的第二道限縮（同 block_bash_on_windows）
    sys.stderr.write(block_message(used, window, source, tool))
    return 2


if __name__ == "__main__":
    sys.exit(main())
