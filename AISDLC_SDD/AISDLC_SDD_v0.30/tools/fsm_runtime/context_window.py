"""Context window 量測（分子）與分母判定的共用純函式層（DEF-200-275 第四輪，2026-09-10）。

`context_ledger_pre.py`／`context_ledger_post.py` 兩支 hook 只 import 本模組，不再各自持有
任何 `200000`／`1000000` 字面值或分母邏輯。

分子：真實值，不是估算值
------------------------
Claude Code 每個 hook 的 stdin payload 帶 `transcript_path`（本 session 的 jsonl 逐字稿）。
每筆 `type=="assistant"` 記錄的 `message.usage` 有 `input_tokens`／`cache_creation_input_tokens`
／`cache_read_input_tokens`，三者之和＝該回合送進模型的 context 佔用（`/context` 顯示的就是
這個數字；`output_tokens` 是這一回合吐出來的量，下一回合才以 input 形式回到 context，重複計會
高估——與根層姊妹守衛同一算式）。`model=="<synthetic>"` 的佔位筆 usage 三欄都在且都是 0，
採計會讓水位在最需要守衛的那一刻掉成 0.0%，一律跳過。

第四輪之前 hook 拿 `CONTEXT-LEDGER-{date}.yaml` 的 `cumulative_tokens` 當分子——那是「當天所有
session 的估算式 I/O 總和」，跨 session 共用、單調遞增、compaction 後不會下降；新開的視窗一
開場就繼承同日別的 session 的 119 萬而被判 CRIT（掌舵者原話「才開新視窗就被擋」）。估算帳本
自本輪起降為稽核／校準紀錄，零決策權。

分母鏈（順序即優先序；「指定」與「推斷」必須分得開）
--------------------------------------------------
① `SDD_MAX_CONTEXT`（正整數才算釘住）→ ② `AUTOSDD_CONTEXT_WINDOW`（根層姊妹守衛的旗標）→
③ `CLAUDE_CODE_AUTO_COMPACT_WINDOW`／④ settings `autoCompactWindow`（harness 自己的旋鈕）→
⑤ settings `model` 帶 `[1m]`／`-1m` 標記且與逐字稿實跑 model 家族交叉否決通過 →
⑥ **以 model id 查表**（表值來源＝Anthropic Models API `GET /v1/models/{id}` 的
`max_input_tokens`；表住 `data/known_model_windows.json`，離線刷新腳本
`refresh_known_model_windows.py` 真的打 API 更新表；hook 路徑永不打網路）→
⑦ `peak_used > 200,000` 的可證下界推論 → 1,000,000 → ⑧ 保守值 200,000。

只有 ⑧ 不准硬擋（`may_block()`）：拿猜出來的分母去鎖工具，正是前三輪反覆修的那個缺陷換個方向
再犯一次。方向論證：猜小只是早喊（成本＝一次多餘的 compact）；猜大則到 90% 時真實水位已
450%＝根本喊不到。所以 ⑦ 夠格（它猜大的方向只會讓阻斷晚發生，不會誤擋），⑧ 不夠格。查表
（⑥）排在下界推論（⑦）之前，是為了讓 200K 模型（如 `claude-haiku-4-5`）在 peak 還沒過
200K 時就拿到正確分母，而不是先被 ⑧ 降級成只出聲。

量不到就放行（C3）
------------------
無 `transcript_path`／檔不存在／掃不到任何 usage ⇒ `measure()` 回 None 或 `used=None`，hook
不做任何 gating。若最後一個 `compact_boundary` 出現在最後一筆 usage 之後，量到的是壓縮前的舊值，
同樣 `used=None`（`stale_after_compact=True`）——寧可放行一次也不拿舊值擋人。

與根層姊妹守衛 `.claude/hooks/context_budget_guard.py` 的關係
---------------------------------------------------------------
`used_of`／`scan_transcript`／`compact_boundary_count`／`positive_int`／`carries_wide_marker`／
`model_family`／`window_from_model`／`known_model_window`／`may_block` 與該檔同名函式逐字同構，
且 `resolve_window` 在 SDD 專屬階（①`SDD_MAX_CONTEXT`）中和時與該檔結果逐項相等——由根層
`tools/tests/test_context_window_parity.py` 釘住。🔴 D27（DEF-200-275 第七輪）起 ⑥ 查表階
已**非**SDD 專屬：根層 `context_budget_guard.py` 同步補齊了「無釘值也無條件查表」這一階
（此前僅在有 pin 時才查，四方複審 ARCH-A4-01 判定該捷徑本身即為缺陷根因），兩檔對 ⑥ 的
判定同樣由上述 parity 測試逐項釘住。兩子專案刻意不跨 import（根 CLAUDE.md〈雙專案
monorepo〉），所以是「複製＋parity 鎖」而不是「共用一份」。
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

#: 佔用當前 context 的三個 usage 欄。`output_tokens` 刻意不在內（見模組 docstring）。
USAGE_FIELDS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
#: 逐字稿裡的合成佔位 model；整筆退出用量累計（見模組 docstring）。
SYNTHETIC_MODEL = "<synthetic>"

#: 保守下界。WHY：Claude 3 世代 200K；未確認時只出聲、不擋（`may_block` 對此階回 False）。
CONSERVATIVE_DEFAULT_MAX_CONTEXT = 200_000
#: 已知的下一檔變體。WHY：`[1m]` 標記／下界推論選的是「已知變體」，不是證出來的值。
WIDE_MAX_CONTEXT = 1_000_000

#: 四段門檻（自兩支 hook 搬入；兩支 hook 改 import，本檔是唯一的家）。
SOFT_RATIO = 0.70
WARN_RATIO = 0.85
AUTO_COMPACT_RATIO = 0.90
CRIT_RATIO = 0.95

SDD_WINDOW_ENV = "SDD_MAX_CONTEXT"
AUTOSDD_WINDOW_ENV = "AUTOSDD_CONTEXT_WINDOW"
CC_WINDOW_ENV = "CLAUDE_CODE_AUTO_COMPACT_WINDOW"
CC_WINDOW_KEY = "autoCompactWindow"
CC_MODEL_KEY = "model"

#: 八個來源字串。每則訊息都印 `used=… window=… 來源=…`，讀者要分得出「指定」與「推斷」。
SOURCE_PINNED_SDD = f"指定值（環境變數 {SDD_WINDOW_ENV}）"
SOURCE_PINNED_AUTOSDD = f"指定值（環境變數 {AUTOSDD_WINDOW_ENV}）"
SOURCE_PINNED_CC_ENV = f"指定值（harness 環境變數 {CC_WINDOW_ENV}）"
SOURCE_PINNED_CC_SETTING = f"指定值（settings {CC_WINDOW_KEY}）"
SOURCE_MODEL_MARKER = (
    f"模型標記（settings {CC_MODEL_KEY} 欄帶 1m 標記 ⇒ {WIDE_MAX_CONTEXT:,}；"
    "已與逐字稿實際跑過的 model 交叉核對同族）"
)
SOURCE_KNOWN_MODEL_PREFIX = "查表值（Models API max_input_tokens"
SOURCE_INFERRED_WIDE = (
    f"推斷值（本 session 曾觀測到 used > {CONSERVATIVE_DEFAULT_MAX_CONTEXT:,} ⇒ window 必然大於它；"
    f"取 {WIDE_MAX_CONTEXT:,} 是在已知變體裡選下一檔，不是證出來的值）"
)
SOURCE_INFERRED_FLOOR = (
    f"推斷值・保守下界（未確認，不硬擋；未觀測到超過 {CONSERVATIVE_DEFAULT_MAX_CONTEXT:,} 的用量，"
    f"要精確就設 {SDD_WINDOW_ENV}）"
)

KNOWN_MODEL_WINDOWS_PATH = Path(__file__).resolve().parent / "data" / "known_model_windows.json"
_NO_TABLE_NOTE = "無表"

_DATE_SUFFIX_RE = re.compile(r"-\d{8}$")


# ───────────────────────────── 純函式：分子 ─────────────────────────────
def used_of(usage: object) -> int | None:
    """單筆 `message.usage` 的當前 context 佔用；`None`＝這筆不是可用的 usage。

    只認 `int`（`bool` 排除——它是 `int` 子類，混進來會讓 `True` 算成 1）；欄位缺一律當 0，
    整筆一個欄位都沒有時回 `None`，讓「量到零」與「量不到」分得開。
    """
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


@dataclass(frozen=True)
class _Scan:
    last: int | None
    peak: int
    model: str | None
    boundaries: int
    last_usage_line: int | None
    last_boundary_line: int | None


def _scan(path: Path) -> _Scan | None:
    """單趟逐行掃描（C11）：`"usage"`／`"compact_boundary"` 子字串預篩、O(1) 記憶體、壞行跳過。

    回 None＝檔讀不到。逐字稿常有半截尾行（正在寫入時被讀到），一行壞掉不得讓整支 hook 崩潰。
    """
    last: int | None = None
    peak = 0
    model: str | None = None
    boundaries = 0
    last_usage_line: int | None = None
    last_boundary_line: int | None = None
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for lineno, line in enumerate(handle):
                has_usage = '"usage"' in line
                has_boundary = '"compact_boundary"' in line
                if not has_usage and not has_boundary:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(record, dict):
                    continue
                if has_boundary and record.get("type") == "system" \
                        and record.get("subtype") == "compact_boundary":
                    boundaries += 1
                    last_boundary_line = lineno
                if not has_usage or record.get("type") != "assistant":
                    continue
                message = record.get("message")
                if not isinstance(message, dict):
                    continue
                seen_model = message.get("model")
                if seen_model == SYNTHETIC_MODEL:
                    continue
                if isinstance(seen_model, str):
                    model = seen_model
                value = used_of(message.get("usage"))
                if value is None:
                    continue
                last = value
                peak = max(peak, value)
                last_usage_line = lineno
    except OSError:
        return None
    return _Scan(last, peak, model, boundaries, last_usage_line, last_boundary_line)


def scan_transcript(path: Path) -> tuple[int | None, int, str | None]:
    """`(最後一筆 used, 歷來最大 used, 最後一個實際跑過的 model)`——簽名與姊妹守衛逐字同構。"""
    scan = _scan(Path(path))
    if scan is None:
        return None, 0, None
    return scan.last, scan.peak, scan.model


def compact_boundary_count(path: Path) -> int:
    """本 session 逐字稿裡 `type=="system" and subtype=="compact_boundary"` 的累計次數。"""
    scan = _scan(Path(path))
    return 0 if scan is None else scan.boundaries


@dataclass(frozen=True)
class Measurement:
    used: int | None
    peak: int
    model: str | None
    compact_boundaries: int
    stale_after_compact: bool


def measure(transcript_path: object) -> Measurement | None:
    """量本 session 的真實 context 佔用。None＝無路徑／不存在／不可讀（C3：一律不 gating）。

    `stale_after_compact`：最後一個 compact_boundary 落在最後一筆 usage 之後 ⇒ 量到的是壓縮前的
    舊值，`used` 一律 None（拿舊值擋人比放行一次更糟）。
    """
    if not isinstance(transcript_path, (str, Path)):
        return None
    raw = str(transcript_path).strip()
    if not raw:
        return None
    path = Path(raw)
    try:
        if not path.is_file():
            return None
    except OSError:
        return None
    scan = _scan(path)
    if scan is None:
        return None
    stale = (
        scan.last_usage_line is not None
        and scan.last_boundary_line is not None
        and scan.last_boundary_line > scan.last_usage_line
    )
    return Measurement(
        used=None if stale else scan.last,
        peak=scan.peak,
        model=scan.model,
        compact_boundaries=scan.boundaries,
        stale_after_compact=stale,
    )


# ───────────────────────────── 純函式：分母 ─────────────────────────────
def positive_int(raw: object) -> int:
    """能讀成正整數就回它，否則回 0。壞值一律 0——0 不得被當成 window 採用，只能是
    「這個來源說不出話」的表示（`abc`／`1.5`／`12k`／``／`0`／`-5` 全部歸 0）。"""
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return 0
    return value if value > 0 else 0


def carries_wide_marker(model: object) -> bool:
    """model 字串是否帶 1M context 標記（`opus[1m]`／`…-1m`）。只認這兩種寫法：
    `claude-opus-4-1` 這種尾碼帶 1 的模型名一旦被誤判成 1M，分母就往危險方向偏大。"""
    text = str(model or "").strip().lower()
    return "[1m]" in text or text.endswith("-1m")


def model_family(model: object) -> str:
    """取 model 字串裡的家族字，只用來做交叉否決；回空字串＝認不出來 ⇒ 呼叫端當「無法否決」。"""
    text = str(model or "").strip().lower()
    for family in ("opus", "sonnet", "haiku", "fable"):
        if family in text:
            return family
    return ""


def window_from_model(hint: object, observed: object = None) -> int | None:
    """settings 的 model 欄推出的 window；None＝這一階說不出話。含交叉否決（settings 寫的家族
    與逐字稿實跑的家族不同 ⇒ 放棄，否則一次 `claude --model sonnet` 覆寫就讓分母偏大五倍）。"""
    if not carries_wide_marker(hint):
        return None
    want, got = model_family(hint), model_family(observed)
    if want and got and want != got:
        return None
    return WIDE_MAX_CONTEXT


def normalize_model_id(model: object) -> str:
    """查表鍵：去 `[1m]`／尾碼 `-1m`、小寫、去 `-YYYYMMDD` 日期尾碼；精確比對用。"""
    text = str(model or "").strip().lower().replace("[1m]", "").strip()
    if text.endswith("-1m"):
        text = text[:-3]
    return _DATE_SUFFIX_RE.sub("", text)


def load_known_model_windows(path: Path = KNOWN_MODEL_WINDOWS_PATH) -> tuple[dict[str, int], str]:
    """回 `(表, 來源描述)`。表讀不到／壞掉 ⇒ `({}, "無表")`（hook 路徑不得因表壞而崩潰）。"""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}, _NO_TABLE_NOTE
    if not isinstance(doc, dict) or not isinstance(doc.get("models"), dict):
        return {}, _NO_TABLE_NOTE
    table: dict[str, int] = {}
    for model_id, window in doc["models"].items():
        if isinstance(model_id, str) and isinstance(window, int) \
                and not isinstance(window, bool) and window > 0:
            table[normalize_model_id(model_id)] = window
    refreshed = doc.get("refreshed_at")
    if isinstance(refreshed, str) and refreshed:
        note = f"refreshed_at={refreshed}"
    else:
        note = f"未刷新，seeded_from={doc.get('seeded_from') or '?'}"
    return table, note


def known_model_window(
    model_hint: object, observed_model: object, known_models: dict[str, int] | None,
) -> tuple[int, str] | None:
    """查表階：逐字稿實跑的 model 優先於 settings 的 hint。None＝這一階說不出話。"""
    if not known_models:
        return None
    for candidate in (observed_model, model_hint):
        key = normalize_model_id(candidate)
        if key and key in known_models:
            return known_models[key], key
    return None


def _converge_pinned_window(
    pinned: int, observed_model: object, known_models: dict[str, int] | None,
) -> tuple[int, str] | None:
    """②③④ 階釘值 vs 逐字稿實跑 model 查表值的收斂（D14）。`None`＝不收斂（沿用釘值）。

    只認 `observed_model`——`model_hint` 是 settings 自己宣告的欄位，用它來否決同一份
    settings 宣告的釘值沒有意義。表值 `>=` 釘值時不收斂（保留使用者刻意設的較小指定值，
    即使模型上限更大也不放大分母）；只有表值嚴格小於釘值才收斂——避免一個大於模型真實
    上限的釘值繼續拿去餵 CRIT／AUTO_COMPACT 分母（方向論證同模組 docstring：猜小只是
    早喊，猜大會讓阻斷遲到）。
    """
    if not known_models:
        return None
    key = normalize_model_id(observed_model)
    if not key or key not in known_models:
        return None
    table_value = known_models[key]
    if table_value >= pinned:
        return None
    return table_value, (
        f"{SOURCE_KNOWN_MODEL_PREFIX}，model={key}；指定值 {pinned:,} 大於該模型上限，已收斂）"
    )


def resolve_window(
    peak_used: int,
    *,
    sdd_raw: object = None,
    autosdd_raw: object = None,
    cc_env_raw: object = None,
    settings_window: object = None,
    model_hint: object = None,
    observed_model: object = None,
    known_models: dict[str, int] | None = None,
    known_models_note: str = "",
) -> tuple[int, str]:
    """`(window, 來源說明)`。純函式——不讀環境／不讀檔（`window_evidence()` 負責收證據）。

    順序見模組 docstring。`sdd_raw=None, known_models={}` 時與姊妹守衛 `resolve_window` 結果
    逐項相等（parity 鎖）。

    D14：②③④ 階（`AUTOSDD_CONTEXT_WINDOW`／CC env／settings `autoCompactWindow`）的釘值
    若大於 `observed_model` 查表得到的上限，收斂到表值（見 `_converge_pinned_window`）；
    ① `SDD_MAX_CONTEXT` 是 session 手動釘值，永不收斂。
    """
    if sdd_raw is not None:
        pinned = positive_int(sdd_raw)
        if pinned > 0:
            return pinned, SOURCE_PINNED_SDD
    for raw, source in (
        (autosdd_raw, SOURCE_PINNED_AUTOSDD),
        (cc_env_raw, SOURCE_PINNED_CC_ENV),
        (settings_window, SOURCE_PINNED_CC_SETTING),
    ):
        if raw is None:
            continue
        pinned = positive_int(raw)
        if pinned > 0:
            converged = _converge_pinned_window(pinned, observed_model, known_models)
            if converged is not None:
                return converged
            return pinned, source
    from_model = window_from_model(model_hint, observed_model)
    if from_model is not None:
        return from_model, SOURCE_MODEL_MARKER
    from_table = known_model_window(model_hint, observed_model, known_models)
    if from_table is not None:
        window, key = from_table
        note = f"，{known_models_note}" if known_models_note else ""
        return window, f"{SOURCE_KNOWN_MODEL_PREFIX}，model={key}{note}）"
    if peak_used > CONSERVATIVE_DEFAULT_MAX_CONTEXT:
        return WIDE_MAX_CONTEXT, SOURCE_INFERRED_WIDE
    return CONSERVATIVE_DEFAULT_MAX_CONTEXT, SOURCE_INFERRED_FLOOR


def may_block(source: str) -> bool:
    """這個 window 來源夠不夠格拿來硬擋／trigger_auto_compact。只有保守下界不夠格。"""
    return source != SOURCE_INFERRED_FLOOR


def ratio_tier(used: int | None, window: int | None) -> str | None:
    """`None`／`soft`／`warn`／`auto_compact`／`crit`。window 非正數或 used 缺一律 None。"""
    if used is None or not window or window <= 0:
        return None
    ratio = used / window
    if ratio >= CRIT_RATIO:
        return "crit"
    if ratio >= AUTO_COMPACT_RATIO:
        return "auto_compact"
    if ratio >= WARN_RATIO:
        return "warn"
    if ratio >= SOFT_RATIO:
        return "soft"
    return None


def unconfirmed_notice(used: int, ratio: float, tier: str, source: str) -> str:
    """CRIT／AUTO_COMPACT 門檻在分母尚未確認時的降級提示：只出聲，FSM 狀態不變、不硬擋。"""
    return (
        f"[SDD-CTX][WARN][UNCONFIRMED-DENOM] {tier} 門檻在保守下界分母下 ratio={ratio:.2f}"
        f"（used={used:,} window={CONSERVATIVE_DEFAULT_MAX_CONTEXT:,} 來源={source}），"
        "分母尚未確認——本次僅示警，FSM 狀態不變、不硬擋。若這確是小視窗模型請設 "
        f"{SDD_WINDOW_ENV}；否則請以 /context 核對真實視窗（DEF-200-275）。"
    )


def auto_compact_exit_due(used: int | None, window: int | None) -> bool:
    """AUTO_COMPACT_PENDING 的出口條件：真實 used 已回落到 < WARN_RATIO × window（0.85 是遲滯帶，
    避免 89／91 抖動）。量不到（None）不算出口。"""
    if used is None or not window or window <= 0:
        return False
    return used < WARN_RATIO * window


# ───────────────────────────── I/O 收口（唯一讀環境／檔案的地方） ─────────────────────────────
def repo_root(env: os._Environ | dict | None = None) -> Path:
    """`CLAUDE_PROJECT_DIR`（Claude Code 注入）；缺席時以本檔位置推到 **SDD 版本根**（`parents[2]`＝
    `tools/fsm_runtime/context_window.py` 上溯兩層），那裡有本子專案自己的 `.claude/settings.json`。

    ARCH-07：此前寫死 `parents[4]`（monorepo 根）——把「本檔恰好被 checkout 在 monorepo 第幾層」
    這個偶然事實寫成常數；SDD 單獨部署時會指到檔案系統裡不相干的目錄。Claude Code 實際執行
    hook 時一律帶 `CLAUDE_PROJECT_DIR`，這個退路只在測試／手動探針缺該變數時才走到。"""
    source = os.environ if env is None else env
    raw = source.get("CLAUDE_PROJECT_DIR")
    if raw:
        candidate = Path(str(raw))
        try:
            if candidate.is_dir():
                return candidate
        except OSError:
            pass
    return Path(__file__).resolve().parents[2]


def settings_chain(root: Path | None = None, home: Path | str | None = None) -> list[Path]:
    """Claude Code settings 檔，由高優先到低優先（與姊妹守衛同一條鏈）。"""
    base = root or repo_root()
    home_dir = Path(home) if home else Path(os.path.expanduser("~"))
    return [
        base / ".claude" / "settings.local.json",
        base / ".claude" / "settings.json",
        home_dir / ".claude" / "settings.json",
    ]


def settings_value(key: str, paths: list[Path]) -> object:
    """settings 鏈裡第一個有這個鍵的值；沒有就 `None`。任何讀檔／解析失敗一律跳過。"""
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get(key) is not None:
            return data[key]
    return None


def window_evidence(
    observed_model: str | None,
    *,
    env: os._Environ | dict | None = None,
    root: Path | None = None,
    home: Path | str | None = None,
    known_models_path: Path = KNOWN_MODEL_WINDOWS_PATH,
) -> dict:
    """把 `resolve_window` 需要的全部證據一次收齊（I/O 都在這裡，判定仍是純函式）。"""
    source = os.environ if env is None else env
    paths = settings_chain(root or repo_root(source), home)
    known, note = load_known_model_windows(known_models_path)
    return {
        "sdd_raw": source.get(SDD_WINDOW_ENV),
        "autosdd_raw": source.get(AUTOSDD_WINDOW_ENV),
        "cc_env_raw": source.get(CC_WINDOW_ENV),
        "settings_window": settings_value(CC_WINDOW_KEY, paths),
        "model_hint": settings_value(CC_MODEL_KEY, paths),
        "observed_model": observed_model,
        "known_models": known,
        "known_models_note": note,
    }
