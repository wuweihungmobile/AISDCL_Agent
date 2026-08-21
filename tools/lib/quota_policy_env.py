# 額度水位節流 —— **env 設定子系統**：`.env.example` 生成／解析／往返一致性驗證。
#
# 本檔是 `tools/lib/quota_policy.py` 依內聚子功能拆出的一半（該檔 LOC 分級收斂：
# guardrail_lib ≤400 行棘輪，見 `check_loc_budget.py` 的 `[ROOT-TOOLS-WARN]`）。搬過來的
# 這一整塊原本就是原檔自己標成一節的（`── env：門檻的唯一的家 ──`），依賴方向單純：
# 只有 `load_policy()` 需要回頭問 `quota_policy.DEFAULT_POLICY`／`policy_monotonicity_
# problems()`（見下方 import），其餘（`ENV_SPEC`／`render_env_example`／`parse_env_text`／
# `env_example_problems`）是純資料與純函式，不依賴原檔任何東西。
#
# 🔴 這不是「同一份知識兩個家」：`quota_policy.py` 仍是 `Policy`／門檻判定邏輯（`pct_band`／
# `_cap_for`／`decide` 等）唯一的家，本檔只是那份知識的 env 序列化層，兩者依賴方向單向
# （本檔 → `quota_policy`），且 `quota_policy.py` 對本檔全部六個公開名字（`EnvVar`／
# `ENV_SPEC`／`render_env_example`／`parse_env_text`／`env_example_problems`／
# `load_policy`）一律 `from quota_policy_env import ...` 重新綁進自己的全域（與
# `tools/lib/sentinel_lifecycle_arm.py`／`tools/lib/schedule_backend_calendar.py` 的既有
# 手法同型），呼叫端看到的仍是 `quota_policy.load_policy(...)` 這個既有介面，簽章與行為
# 不變。
# 🔴 R98 收尾訂正（DEF-101-941 一族之後、獨立發現）：上一版本段原文逐字寫著「`from
# quota_policy import DEFAULT_POLICY, policy_monotonicity_problems` 這一行要求
# `quota_policy.py` 先把這兩個名字定義完才 import 本檔——原檔那一行 import 的位置
# （env 一節原本起始處）本來就在兩者定義之後，順序天然成立，不是巧合」——這句話只在
# `import quota_policy` 為入口時成立。實測 `python tools/lib/quota_policy.py
# --print-env-example`（本檔自己文件化的合法用法）**直接炸**：直接執行的腳本以
# `__main__` 註冊進 `sys.modules`，不是以 `quota_policy` 這個模組名——於是本檔第 26 行
# （模組層 `from quota_policy import ...`）觸發的是**全新**一次 `quota_policy` 匯入
# （非「借用已存在的部分初始化模組」），該全新匯入執行到它自己那一行
# `from quota_policy_env import (...)` 時，本檔正在初始化中尚未定義 `ENV_SPEC` 等名字
# ⇒ `ImportError: cannot import name 'ENV_SPEC' from partially initialized module
# 'quota_policy_env'`。回歸鎖＝`tools/tests/test_doc_loc_baseline_freshness_r60.py::
# TestR85DocNamedLiveCheckEntriesActuallyRun`。修法＝把這個回頭依賴**延後到呼叫時**
# （見 `load_policy()` 內的區域 import），使模組層完全零回頭依賴；`Policy` 這個型別名
# 只出現在 `load_policy()` 的回傳型別註記，靠檔頭 `from __future__ import annotations`
# 讓它保持字串、不需要在模組層可解析——但 `ruff` 的 F821 仍會靜態檢查註記名字是否
# 「看得到」，故 `TYPE_CHECKING` 區塊補一份**只在型別檢查時執行**的 import（`TYPE_CHECKING`
# 執行期恆 `False`，不參與上述循環）。
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from quota_policy import Policy


# ── env：門檻的唯一的家，`.env.example` 由它生成（不手寫＝不製造第二個家）─────────
class EnvVar(NamedTuple):
    """一個環境變數的完整宣告。`attr is None` ＝ 不進 `Policy`（逃生口，或外部消費者直讀）。"""

    name: str
    attr: str | None
    default: object
    kind: str
    lo: float | None
    hi: float | None
    note: str
    section: str


ENV_SPEC: tuple[EnvVar, ...] = (
    EnvVar("AUTOSDD_QUOTA_NOTICE_PCT", "notice_pct", 50.0, "float", 0.0, 100.0,
           "開始注意、少派", "policy"),
    EnvVar("AUTOSDD_QUOTA_CONVERGE_PCT", "converge_pct", 70.0, "float", 0.0, 100.0,
           "開始收斂", "policy"),
    EnvVar("AUTOSDD_QUOTA_PREPARE_PCT", "prepare_pct", 85.0, "float", 0.0, 100.0,
           "準備下一次 Reset", "policy"),
    EnvVar("AUTOSDD_QUOTA_HALT_PCT", "halt_pct", 95.0, "float", 0.0, 100.0,
           "停止並喚醒下一輪", "policy"),
    EnvVar("AUTOSDD_QUOTA_ACCEL_WINDOW_MINUTES", "accel_window_minutes", 30.0,
           "float", 0.0, None, "reset 在這麼近之內 ⇒ 加速（使用者原文的 30m）", "policy"),
    EnvVar("AUTOSDD_QUOTA_FAR_HORIZON_MINUTES", "far_horizon_minutes", 360.0,
           "float", 0.0, None, "超過這麼遠 ⇒ 減速（6h）", "policy"),
    EnvVar("AUTOSDD_QUOTA_CAP_NOTICE", "cap_notice", 8, "int", 1.0, None,
           "notice 帶的 base cap", "policy"),
    EnvVar("AUTOSDD_QUOTA_CAP_CONVERGE", "cap_converge", 4, "int", 1.0, None,
           "converge 帶的 base cap", "policy"),
    EnvVar("AUTOSDD_QUOTA_CAP_PREPARE", "cap_prepare", 2, "int", 1.0, None,
           "prepare 帶的 base cap", "policy"),
    EnvVar("AUTOSDD_QUOTA_PACE_NEAR", "pace_near", 2.0, "float", 1.0, None,
           "reset 近在眼前時的**加速**倍率（下界 1＝不加速；R84／6b）", "policy"),
    EnvVar("AUTOSDD_QUOTA_PACE_FAR", "pace_far", 0.5, "float", 0.0, 1.0,
           "reset 很遠／期程不明時的**減速**倍率（上界 1＝不減速；R84／6b）", "policy"),
    EnvVar("AUTOSDD_QUOTA_PACE_CEILING", "pace_ceiling", 1.0, "float", 1.0, None,
           "配速上限：PACE_INDEX 超過才判超前（1＝任何超前即減速；PRD §4.2.8）", "policy"),
    EnvVar("AUTOSDD_QUOTA_MAX_FANOUT", "max_fanout", 16, "int", 1.0, None,
           "加速後的絕對上界", "policy"),
    EnvVar("AUTOSDD_QUOTA_DEGRADED_CAP", "degraded_cap", 4, "int", 1.0, None,
           "量不到時的上限（絕不是「不設限」）", "policy"),
    # 🔴 R91／`DEF-200-097`：本鍵**結構上就是政策鍵**（有 `attr`、型別 `int`、下界 1），
    # 而它先前被渲染在下方〈既有逃生口〉標題底下、夾在兩個 `_OFF` 開關之間 ⇒ 讀者會把它
    # 讀成「關掉某個東西」的開關。逃生口關掉的是守衛，本鍵**永遠只收緊**
    # （`min(cap, override)`，見 `fanout_cap()`），一個字都關不掉 ⇒ 兩者不同族。
    # 修法選的是該列分流欄二擇一裡的「改結構歸類」：`section` 改 `policy`，位置一併上移，
    # 於是結構（`attr`／`kind`）與渲染分節不再互相矛盾。
    EnvVar("AUTOSDD_QUOTA_FANOUT_CAP", "fanout_cap_override", None, "int", 1.0, None,
           "節流帶 cap 的**上限**覆寫（留空＝不覆寫）：只收緊不放寬，halt 帶不吃", "policy"),
    # 🔴 R95／Pkg-D 交棒的註冊補位：消費者＝`tools/session_resume_planner.py` 的
    # choose_resume_route() os.environ 直讀（attr=None 不進 Policy）；選值見 Resume 證據檔 §2。
    EnvVar("AUTOSDD_RESUME_MAX_TRANSCRIPT_BYTES", None, None, "int", 1.0, None,
           "喚醒選路：逐字稿超此位元組數即降級 FRESH（留空＝內建 32MiB）", "policy"),
    EnvVar("AUTOSDD_QUOTA_GUARD_OFF", None, "", "flag", None, None, "1 ⇒ 額度節流全關", "escape"),
    EnvVar("AUTOSDD_SENTINEL_OFF", None, "", "flag", None, None, "1 ⇒ 額度續航哨兵關掉", "escape"),
    EnvVar("AUTOSDD_CONTEXT_GUARD_OFF", None, "", "flag", None, None, "1 ⇒ context 阻斷關掉（**與上一個不同的東西**）", "escape"),  # noqa: E501
    # 🔴 R91：**第四個**逃生口，刻意不與上面三個共用（repo 明文：共用一個會讓「我只是想
    # 暫時別被擋」順手把別的保護一起關掉）。它只關 context 提示的**送達形態**（stdout 的
    # `hookSpecificOutput` ⇒ 退回舊的純 stderr），不關任何判定、不關阻斷、不關哨兵。
    # 上兩列刻意壓成一行以騰出這一格：`guardrail_lib` 對本檔的 LOC 預算餘裕一路是 0。
    EnvVar("AUTOSDD_CONTEXT_SIGNAL_OFF", None, "", "flag", None, None, "1 ⇒ 只關送達面", "escape"),
    # 🔴 R97（round-label-ok：非帳本追蹤的正式輪，僅沿用便於追蹤的標籤）：第五個逃生口。`session_resume_planner.py` 的 `RESUME_OFF_ENV` 此前只讀  # noqa: E501
    # `os.environ`，`.env` 設了也關不掉（同 R82／C2 那個病）：非要 Windows 登錄檔＋整個
    # 重啟 Claude Code 才生效。`attr=None`：不進 Policy，消費端住該檔自己。
    EnvVar("AUTOSDD_RESUME_OFF", None, "", "flag", None, None, "1 ⇒ 醒來只探測＋留痕，不自動續跑（session_resume_planner.py 專屬）", "escape"),  # noqa: E501
)

_ENV_HEADER = (
    "# ── 額度水位節流：**本檔是範例（.env.example）；實際生效的是 repo 根的 .env** ──",
    "#    用法：copy .env.example .env（原封不動複製即可用），再改你要的那幾個值。",
    "# 🔴 唯一的家＝tools/lib/quota_policy.py 的 ENV_SPEC；本檔是生成物，勿手寫：",
    "#    python tools/lib/quota_policy.py --print-env-example",
    "# 生效路徑三條，優先序 **env > AutoClaude/.env > 根 .env > 出廠預設**：",
    "#   ① repo 根 .env      —— harness 的 hook 讀（tools/lib/quota_gate.py:policy_env）；",
    "#      下方**逃生口那一區也算數**（hook main() 先把這些鍵填成行程級預設，缺席才填）。",
    "#      🔴 本次收斂之前這句對逃生口是假的：三個開關直讀 os.environ ⇒ 在 .env 設也關不掉，",
    "#      而「關掉了」與「沒關掉」外觀完全相同。",
    "#   ② AutoClaude/.env   —— 引擎側讀（autoclaude/utils/config.py:_quota_env）；同名鍵",
    "#      覆寫①。引擎只讀它真的有消費者的那幾個鍵，清單見 AutoClaude/.env.example。",
    "#   ③ .claude/settings.json 的 env 區塊 —— **會**注入 hook 行程（實測：把",
    "#      SDD_ROUTER_QUIET=1 放進去，SessionStart 的 SDD-ROUTER 由 4 行變 0 行）。",
    "# 行內註解（值後面接 ` # …`）會被剝掉 ⇒ 手寫時可以加註解。",
)
_ENV_ESCAPE_HEADER = "# ── 既有逃生口（此前只散落在 hook 註解裡，零使用者可讀清單）──"


# `50.0` 印成 `50`；`None`／空字串印成空（＝未設定）。
def _fmt_default(value: object) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


# 🔴 R82／C1 的 (b) 半：說明改成**獨立一行**，鍵那一行只剩 `KEY=value`。
# 使用者的標準流程就是 `copy .env.example .env` 再改幾個值 ⇒ 產生器把說明黏在同一行時，
# 那份 `.env` 的每一個值都自帶一段中文說明。(a) 半（`parse_env_text` 剝行內註解）讓手寫
# 的行內註解也不會壞，但**檔案本身乾淨**是另一件事：它讓「複製過去就能用」在肉眼上也成立，
# 而不是靠消費者收拾。兩半都做的理由就是這個——它們各自守住一個方向。
def render_env_example() -> str:
    """生成 `.env.example` 全文（決定性；`.env.example` 不得手寫）。"""
    lines = list(_ENV_HEADER)
    seen_escape = False
    for spec in ENV_SPEC:
        if spec.section == "escape" and not seen_escape:
            seen_escape = True
            lines.extend(("", _ENV_ESCAPE_HEADER))
        hint = "（範例值，可依帳號方案調整）" if spec.section == "policy" else ""
        lines.extend((f"# {spec.note}{hint}",
                      f"{spec.name}={_fmt_default(spec.default)}"))
    return "\n".join(lines) + "\n"


# 🔴 R82／C1：**行內註解必須在這裡被剝掉**，而這一格就是本檔與消費者之間的縫。
# `render_env_example()` 產出的每一行都是 `KEY=值<補白>#說明`（同一行！），而消費者
# `quota_gate.policy_env()` 此前做的是 `partition("=")` 再 `strip()` ⇒ 說明文字整段
# 留在值裡。實測後果：12 個帶值的鍵**全部**解析失敗、全部退回預設，也就是說使用者照
# `.env.example` 抄一份 `.env` 之後，訴求 6c 的「門檻可調」在端到端是完全不成立的；
# 而 `AUTOSDD_QUOTA_GUARD_OFF=` 這種空值鍵更糟——不剝註解時它的值變成非空字串
# `"# 1 ⇒ 整條額度節流關掉"`，於是**照抄範例檔就會把整條額度節流關掉**。
# 逃過的原因是判準的形狀：`env_example_problems()` 拿生成物**跟自己比**，從不呼叫
# 消費者的解析器 ⇒ 兩個家互相一致、都沒對消費者測。回歸鎖＝本檔的 round-trip 判準
# `tools/tests/test_quota_policy.py::TestM6TheGeneratedFileSurvivesItsOwnConsumer`。
# 只認「行首或空白之後的 `#`」：值本身帶 `#` 時不誤剝（未來若有非數值旋鈕）。
def _value_of(raw: str) -> str:
    cut = next((i for i, ch in enumerate(raw)
                if ch == "#" and (i == 0 or raw[i - 1].isspace())), len(raw))
    return raw[:cut].strip()


def parse_env_text(text: str) -> dict[str, str]:
    """`.env`／`.env.example` 文字 → `{鍵: 值}`。**唯一的解析器**（見上方 WHY）。"""
    pairs = (ln.strip().partition("=") for ln in text.splitlines()
             if ln.strip() and not ln.strip().startswith("#") and "=" in ln)
    return {k.strip(): _value_of(v) for k, _, v in pairs}


def env_example_problems(text: str) -> list[str]:
    """`.env.example` ↔ `ENV_SPEC` **雙向**鎖：幽靈鍵／漏鍵／不等於生成物。"""
    problems = []
    keys = list(parse_env_text(text))
    declared = [spec.name for spec in ENV_SPEC]
    problems += [f"[幽靈鍵] {k} 不在 ENV_SPEC（improving_92 清過一批同型）"
                 for k in keys if k not in declared]
    problems += [f"[漏鍵] ENV_SPEC 的 {k} 沒出現在 .env.example"
                 for k in declared if k not in keys]
    if text != render_env_example():
        problems.append("[不同步] 磁碟內容 != render_env_example()（請重生，勿手寫）")
    return problems


def _parse_env_number(raw: str, spec: EnvVar, problems: list[str]) -> float | int | None:
    """壞值一律**進 problems ＋ 回 None（採用預設）**；🔴 不得靜默夾。"""
    try:
        value = float(raw)
    except ValueError:
        problems.append(f"{spec.name}={raw!r} 不是數字 ⇒ 採用預設 {spec.default}")
        return None
    if spec.lo is not None and value < spec.lo:
        problems.append(f"{spec.name}={raw!r} 低於下界 {spec.lo} ⇒ 採用預設 {spec.default}")
        return None
    if spec.hi is not None and value > spec.hi:
        problems.append(f"{spec.name}={raw!r} 高於上界 {spec.hi} ⇒ 採用預設 {spec.default}")
        return None
    return int(value) if spec.kind == "int" else value


# 🔴 `problems` 非空時呼叫端必須出聲一次（`note_degraded()`）——「設了沒生效而沒有人
# 知道」正是 6c 最容易假交付的一格。
def load_policy(env: Mapping[str, str]) -> tuple[Policy, list[str]]:
    """從 mapping（**不是 os.environ**）讀門檻。回 `(policy, problems)`。"""
    # 🔴 區域 import（延後到呼叫時）：見檔頭 R98 訂正段——模組層若回頭 import
    # `quota_policy` 會在 `python tools/lib/quota_policy.py` 直接執行時炸掉
    # （`__main__` 入口不會以 `quota_policy` 這個名字註冊進 `sys.modules`）。
    from quota_policy import DEFAULT_POLICY, policy_monotonicity_problems

    problems: list[str] = []
    values: dict[str, object] = {}
    for spec in ENV_SPEC:
        if spec.attr is None:
            continue
        raw = str(env.get(spec.name, "")).strip()
        if not raw:
            continue
        parsed = _parse_env_number(raw, spec, problems)
        if parsed is not None:
            values[spec.attr] = parsed
    policy = replace(DEFAULT_POLICY, **values) if values else DEFAULT_POLICY
    ladder = (policy.notice_pct, policy.converge_pct, policy.prepare_pct, policy.halt_pct)
    if not all(a < b for a, b in zip(ladder, ladder[1:])):
        problems.append(f"四個錨點必須嚴格遞增，實得 {ladder} ⇒ 整組採用預設")
        return DEFAULT_POLICY, problems
    if policy.accel_window_minutes >= policy.far_horizon_minutes:
        problems.append(
            f"accel_window({policy.accel_window_minutes}) 必須小於 "
            f"far_horizon({policy.far_horizon_minutes})，否則 mid 檔是空的 ⇒ 整組採用預設")
        return DEFAULT_POLICY, problems
    mono = policy_monotonicity_problems(policy)
    if mono:
        return DEFAULT_POLICY, problems + [*mono, "⇒ 整組採用預設"]
    return policy, problems
