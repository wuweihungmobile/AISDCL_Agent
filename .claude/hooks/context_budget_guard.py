#!/usr/bin/env python
"""PostToolUse 守衛：Claude Code session 的 context 水位觀測者（本 repo 首見）。

WHY
---
掌舵者連續多輪指名要兩件事：「注意上下文是否超出 90%，進行 /compact，不要爆」與
「注意 Token 限制，適當進行排程再喚醒繼續處理」。動工前實查三處，結論是這兩件事
在**這一層**零機械物：
  · 根 `.claude/settings.json`：SessionStart/PreToolUse/PostToolUse 全部條目裡
    沒有任何一支在看 token 或 context；
  · `AutoClaude` Kernel 的 Token Guard（≥80% `/compact`、≥90% checkpoint ＋
    `scheduled_resume_at`）活在 **playbook 執行迴圈**裡，對 Claude Code session
    本身一行都不生效——它守的是被驅動的那個東西，不是驅動者；
  · 根 `CLAUDE.md`〈Token 將耗盡時的「無害暫停 → reset 後重啟」SOP〉是**純人工程序**。

🔴 與 SDD `context_ledger` 的分工邊界（**先查過再寫，本檔不是重複造輪子**）
------------------------------------------------------------------------
repo 內確實已有一套帶 90% 門檻的 context 機制，而且**已經橋接在根註冊面上**：
`AISDLC_SDD/AISDLC_SDD_v0.30/.claude/hooks/context_ledger_pre.py`（各版目錄各一份），
經根 `.claude/settings.json` 的 `sdd_hook_router.py` 以 `context_ledger_pre`／
`context_ledger_post` 掛在 PreToolUse／PostToolUse。實查其常數：`WARN_RATIO = 0.85`／
`AUTO_COMPACT_RATIO = 0.90`／`CRIT_RATIO = 0.95`（95% 發 `permissionDecision=deny`），
分母 `MAX_CONTEXT` 來自 `SDD_MAX_CONTEXT`、預設 200000。**它不該被廢、也不該被改**
（30 個版目錄、Copy-on-Evolve 凍結、FSM 有依賴）。

本檔與它**量的不是同一個東西**，三點皆逐項實查過：
  ① **估算 vs 實測**：ledger 的分子是 `_estimate_tokens(tool, tool_input)`，
     委派 `conversation_ledger.estimate_tool_tokens`，回退 `len(text) // 4`。
     它的輸入**只有 tool_input**——看不到工具**輸出**、subagent 回傳、對話本身、
     system prompt，而真正把 context 撐爆的正是那些。本檔的分子是逐字稿裡
     API 自己回報的 `message.usage`，是實測值。
  ② **生效條件不相交**：router 以 `SDD_ACTIVE_VERSION` 為守衛，未設時
     PreToolUse／PostToolUse **完全靜默放行**（SessionStart 印一行 dormant 提示）。
     純 AutoClaude／monorepo 根 session（＝本檔要守的那一種）ledger 一行都不跑。
  ③ **分母不同**：ledger 的分母是 SDD 專案的 Stage 預算，不是 Claude Code 的
     context window。兩者同為 200000 是巧合（一個是預設值、一個是保守下界）。

🔴 這個分工論證的**洞**，照實寫（不粉飾）
------------------------------------------
`SDD_ACTIVE_VERSION` 有設時兩者同時活著，而**兩邊都有一條 90% 線**。它們的分子分母
都不同，所以同一時刻的兩個百分比會**不一樣**——「同一份 repo 對同一個數字兩種說法」
正是本 repo 反覆判過的缺陷形態。本檔採取的處置是**標示而非收編**：
  · 每一則訊息都印出 `MEASURE_LABEL`，讓讀者一眼分得出這是哪一把尺量的；
  · 不去讀、也不去寫 ledger 的檔案（耦合會讓凍結版被拖下水）；
  · 不因 ledger 存在而讓路——它結構上看不到讓 context 爆掉的那部分。
**未解的那一半**：兩者同時觸發時使用者會連拿兩則語氣相近的告警。本檔不試圖去重
（去重需要跨 30 個凍結版的協議），僅以標籤讓它們可分辨。這一段是已知且已接受的
限制，不是漏看。

而「純文件約束對當下的模型零攔阻力」在本 repo 已被實證：`block_bash_on_windows.py`
那條規則寫進 CLAUDE.md 之後，同一個回合內仍再犯一次；換成 PreToolUse hook 之後
一次嘗試、一次攔下。水位這件事同型且更嚴重——CLAUDE.md 由 session **開場**載入，
而「現在幾 % 了」是每回合都在變的量，靠模型主動想起來去算它，正是決策負荷第一個
擠掉的東西。姊妹檔 `lint_powershell_command.py` 的立案量測寫得更直白：**有觀測者
的規則違規 1 次且被當場擋下，沒有觀測者的規則違規率 20~35%**。context 水位在本檔
出現之前是「沒有觀測者」那一類。

量測面（本輪實測確認，不是推測）
--------------------------------
Claude Code 的 hook payload 帶 `transcript_path`，指向本 session 的 jsonl。該檔每筆
`type == "assistant"` 的記錄在 `message.usage` 下有四個計數欄。**當前 context 佔用
＝ `input_tokens` ＋ `cache_creation_input_tokens` ＋ `cache_read_input_tokens`**
（`output_tokens` 不算：它是這一則回覆吐出來的量，下一回合才會以 input 的形式回到
context 裡，重複計會高估）。

🔴 context window 判定：這是本檔唯一「無法從資料證出來」的一格，故刻意誠實劃界
--------------------------------------------------------------------------------
逐字稿的 `message.model` 實測是 `"claude-opus-5"`——**看不出是不是 1M context 變體**，
而 200K 與 1M 差五倍，猜錯的代價完全不對稱：
  · 猜小（實際 1M、當成 200K）⇒ 提早喊。成本＝一次多餘的 `/compact`。
  · 猜大（實際 200K、當成 1M）⇒ 到 90% 才喊時真實水位已是 450%，**根本喊不到**。
故判定順序刻意是「指定 → 可證的下界 → 保守值」，且**三種來源都必須印在訊息裡**，
讓讀者知道那個分母是被指定的還是被推斷的（本 repo 的既有教訓：把推斷寫成已知，
下一個人 grep 到它會以為是查過的事實）：
  ① `AUTOSDD_CONTEXT_WINDOW` 環境變數（最高優先）＝**指定值**，唯一不含猜測的來源。
  ② 本 session 歷來觀測到的 `used` 曾超過 200,000 ⇒ window **必然**大於 200K。
     這一步是可證的；但「所以它是 1,000,000」不是——那是在已知變體裡取下一檔。
     訊息因此標成「推斷值」並寫出推論依據，不寫成事實。
  ③ 其餘一律 200,000（保守下界）。這個方向只會早喊，安全。

行為契約
--------
· payload 讀不出來／沒有 `transcript_path`／檔案不存在／掃不到任何 usage → exit 0。
· `< 75%` → exit 0 且**完全靜默**（每次工具呼叫都出聲的守衛會被關掉）。
· `>= 75%` → stderr 一行建議 `/compact`，exit 0。
· `>= 90%` → stderr 強制指引（含 %、used/window 實數、下一步）＋ 呼叫
  `tools/session_resume_planner.py` 寫出「可重啟點任務書」骨架 ＋ **exit 2**。
  PostToolUse 的 exit 2 會把 stderr 回饋給模型，這正是要的效果；它**不**阻斷已經
  完成的那次工具呼叫（與 PreToolUse 的 exit 2 語意不同，別混淆）。
· **同一門檻同一 session 只喊一次**（state 檔在系統暫存，檔名帶 session id）。
  代價明說：模型若無視 90% 那一喊，本檔不會再喊第二次。刻意接受——每次工具呼叫
  都 exit 2 的守衛會被整個關掉，而被關掉的守衛比沒有守衛更糟（它讓人以為有人在看）。
· **任何非預期例外 → exit 0（fail-open）**。`.claude/settings.json` 的 description
  記載過 P0：hook 誤觸會把所有工具硬鎖死。守衛自身絕不可成為故障源。

零外部相依（與兩支姊妹 hook 同一組理由，非偷懶）
------------------------------------------------
hook 由 `.claude/settings.json` 的 shim 以 `runpy.run_path(...)` 起，而 `run_path`
**不會**把腳本所在目錄加進 `sys.path`；`tools/` 也不在路徑上。⇒ 本檔只用 stdlib，
UTF-8 串流手術就地重做一次。反向依賴是允許的：`tools/session_resume_planner.py`
**import 本檔**取用下面這幾支純函式，讓「怎麼算水位」只有一個家（本 repo 對
「同一份知識住兩個家」有反覆的判例，其中一次就長在專門防它的那一節自己身上）。

回歸鎖：`tools/tests/test_context_budget_guard.py`（合成 jsonl 注入，逐條驗紅）。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# 自己的 stdout/stderr 強制 UTF-8。缺這段時：locale 表達不了 CJK（en-US Windows
# ＝cp1252）→ 整段指引變 `\uXXXX` 逃脫字面；locale 表達得了但非 UTF-8（zh-TW
# ＝cp950）→ 讀者端亂碼。兩種都讓「提醒有了、指引沒了」，而本檔存在的唯一理由
# 就是純文件約束無攔阻力，指引不可讀等於把它砍掉一半。
# 例外一律吞掉且刻意比 stdlib 慣例更寬：**模組層**崩潰發生在 main() 的 try 之外、
# 繞得過那道保險，而 fail-open 在這裡是 P0。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001 — 見上
        pass

#: 佔用當前 context 的三個 usage 欄。`output_tokens` 刻意不在內，理由見模組 docstring。
USAGE_FIELDS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")

#: 硬指定 context window 的環境變數（最高優先；唯一不含猜測的來源）。
WINDOW_ENV = "AUTOSDD_CONTEXT_WINDOW"

#: 保守下界。實際是 1M 時只會早喊，方向安全。
CONSERVATIVE_WINDOW = 200_000
#: 已知的下一檔變體。觀測到 used > CONSERVATIVE_WINDOW 只證明「大於 200K」，
#: 取這個值是在已知變體裡選，不是證出來的——訊息必須標成推斷。
WIDE_WINDOW = 1_000_000

WARN_RATIO = 0.75
HARD_RATIO = 0.90

TIER_WARN = "warn"
TIER_HARD = "hard"

SOURCE_PINNED = f"指定值（環境變數 {WINDOW_ENV}）"
SOURCE_INFERRED_WIDE = (
    f"推斷值（本 session 曾觀測到 used > {CONSERVATIVE_WINDOW:,} ⇒ window 必然大於它；"
    f"取 {WIDE_WINDOW:,} 是在已知變體裡選下一檔，**不是**證出來的值）"
)
SOURCE_INFERRED_FLOOR = (
    f"推斷值・保守下界（未觀測到超過 {CONSERVATIVE_WINDOW:,} 的用量。"
    f"若實際是 {WIDE_WINDOW:,} 只會提早喊，方向安全；要精確就設 {WINDOW_ENV}）"
)

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

    刻意只認 `int`（`bool` 也排除——它是 `int` 子類，混進來會讓 `True` 算成 1）：
    欄位缺一律當 0，但整筆一個欄位都沒有時回 `None`，讓「量到零」與「量不到」
    分得開。這兩者混同正是本 repo 反覆踩到的 fail-open 形狀。
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


def scan_usage(path: Path) -> tuple[int | None, int]:
    """逐行掃 jsonl，回 `(最後一筆 used, 歷來最大 used)`；掃不到時回 `(None, 0)`。

    刻意**逐行覆寫 last** 而不是整檔 `json.loads` 後排序：逐字稿是會長到數十 MB
    的 append-only 檔，而本檔每次工具呼叫都會跑一次。三段省法：
      ① 以 `"usage"` 子字串預篩，絕大多數行連 `json.loads` 都不進；
      ② 記憶體 O(1)（只留 last 與 max）；
      ③ 壞行直接跳過——逐字稿常有半截尾行（正在寫入時被讀到），一行壞掉不得
         讓整支守衛崩潰（同 `tools/probe/audit_session.py::iter_records` 的既有判斷）。
    歷來最大值是 window 下界推論的唯一輸入，所以必須整檔看過，不能只看尾巴。
    """
    last: int | None = None
    peak = 0
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
                value = used_of(message.get("usage"))
                if value is None:
                    continue
                last = value
                peak = max(peak, value)
    except OSError:
        return None, 0
    return last, peak


def resolve_window(peak_used: int, env_raw: str | None = None) -> tuple[int, str]:
    """`(window, 來源說明)`。純函式——紅綠由注入自證，不讀環境（由呼叫端傳入）。

    順序即優先序：指定 → 可證的下界推論 → 保守值。來源說明會原樣印進使用者看到的
    訊息，所以它**必須**分得出「指定」與「推斷」；把推斷寫成已知是本 repo 的既有
    缺陷形態，不是文風問題。
    """
    if env_raw is not None:
        try:
            pinned = int(str(env_raw).strip())
        except ValueError:
            pinned = 0
        if pinned > 0:
            return pinned, SOURCE_PINNED
    if peak_used > CONSERVATIVE_WINDOW:
        return WIDE_WINDOW, SOURCE_INFERRED_WIDE
    return CONSERVATIVE_WINDOW, SOURCE_INFERRED_FLOOR


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
    """逐字稿檔名（去副檔名）即 session id；非英數字元一律換成 `-`。

    清洗不是裝飾：這個字串會變成暫存檔名的一部分，未清洗的路徑分隔符會讓
    state 檔寫到別的目錄去（或在 Windows 上直接寫檔失敗）。
    """
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in transcript.stem)


def state_path(session_id: str, tmp_dir: str | None = None) -> Path:
    return Path(tmp_dir or tempfile.gettempdir()) / f"{STATE_PREFIX}{session_id}.json"


def announced_tiers(state: Path) -> set[str]:
    """已喊過的門檻集合。讀不出來一律回空集合（寧可多喊一次，也不要靜默失聲）。"""
    try:
        data = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    tiers = data.get("tiers") if isinstance(data, dict) else None
    return {str(t) for t in tiers} if isinstance(tiers, list) else set()


def remember_tier(state: Path, tier: str) -> None:
    """把門檻記進 state 檔。寫失敗不得升級為守衛失敗——最壞情況是下次再喊一次。"""
    tiers = sorted(announced_tiers(state) | {tier})
    try:
        state.write_text(
            json.dumps({"tiers": tiers}, ensure_ascii=False),
            encoding="utf-8",
            newline="\n",
        )
    except OSError:
        pass


def repo_root() -> Path:
    """monorepo 根。`CLAUDE_PROJECT_DIR` 由 Claude Code 注入，缺席時以本檔位置推。

    以檔案位置為主要依據（`.claude/hooks/<本檔>` ⇒ 上溯兩層）而不是 cwd：cwd 由
    註冊面的 shim 決定，那是別人的實作細節，被改掉時本檔不該跟著壞。
    """
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        candidate = Path(env)
        if candidate.is_dir():
            return candidate
    return Path(__file__).resolve().parents[2]


def write_resume_plan(transcript: Path) -> str:
    """呼叫 `tools/session_resume_planner.py` 產出任務書骨架；回傳路徑（失敗回空字串）。

    走 subprocess 而不是 import：本檔的零相依契約（見模組 docstring）不允許 import
    repo 內任何模組，而 `tools/` 根本不在 hook 行程的 `sys.path` 上。子行程的
    stdout/stderr 明確宣告 UTF-8（`encoding=`／`errors=`），避免 zh-TW cp950 下
    讀子行程輸出時炸 UnicodeDecodeError。任何失敗一律吞掉——任務書寫不出來時，
    使用者仍該拿到那段強制指引。
    """
    planner = repo_root() / "tools" / "session_resume_planner.py"
    if not planner.is_file():
        return ""
    out = Path(tempfile.gettempdir()) / f"{PLAN_PREFIX}{session_id_of(transcript)}.md"
    try:
        subprocess.run(
            [sys.executable, str(planner), "--transcript", str(transcript),
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
        )
    except Exception:  # noqa: BLE001 — 診斷輔助不得反過來變成守衛的故障源
        return ""
    return str(out) if out.is_file() else ""


def _headline(used: int, window: int, source: str) -> str:
    return (f"{used / window:.1%}"
            f"（{MEASURE_LABEL}：used {used:,} / window {window:,}〔{source}〕）")


def warn_message(used: int, window: int, source: str) -> str:
    return (
        f"⚠️  context 水位 {_headline(used, window, source)}——已越過 75%。\n"
        "   建議現在跑 `/compact`（根 CLAUDE.md〈Token 將耗盡時的無害暫停〉三段式水位："
        "~75% compact、~90% 停止開新戰場、撞上限才重啟）。此時仍可開新工作。\n"
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
        f"🔴 context 水位 {_headline(used, window, source)}——已越過 90% 硬線。\n"
        "   此後**只做收斂，不做展開**（根 CLAUDE.md〈Token 將耗盡時的「無害暫停 →"
        " reset 後重啟」SOP〉）：\n"
        "  1. 立刻 `/compact`。\n"
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


def read_payload() -> dict | None:
    """讀 stdin 的 hook payload；`None`＝退化（讀不出來）。

    走 **bytes 端**再以 UTF-8+replace 解碼：zh-TW Windows 的 pipe 預設 cp950，
    裸文字端 read 遇到含中文的 UTF-8 payload 會拋 UnicodeDecodeError。三支姊妹
    hook 都有這道防線，本檔照抄同一形態。
    """
    try:
        buffer = getattr(sys.stdin, "buffer", None)
        raw = (buffer.read().decode("utf-8", "replace") if buffer is not None
               else sys.stdin.read())
    except Exception:  # noqa: BLE001 — 讀不到就是退化，不是崩潰
        return None
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def main() -> int:
    try:
        payload = read_payload()
        if payload is None:
            return 0  # 退化 payload：本檔是觀測者不是阻斷器，靜默略過這一次
        raw_path = payload.get("transcript_path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            return 0
        transcript = Path(raw_path)
        if not transcript.is_file():
            return 0

        used, peak = scan_usage(transcript)
        if used is None:
            return 0  # 掃不到任何 usage：量不到 ≠ 量到零，不做任何宣稱
        window, source = resolve_window(peak, os.environ.get(WINDOW_ENV))
        tier = tier_of(used, window)
        if tier is None:
            return 0

        state = state_path(session_id_of(transcript))
        if tier in announced_tiers(state):
            return 0
        remember_tier(state, tier)

        if tier == TIER_WARN:
            sys.stderr.write(warn_message(used, window, source))
            return 0
        sys.stderr.write(hard_message(
            used, window, source, write_resume_plan(transcript),
            sdd_active=bool(os.environ.get("SDD_ACTIVE_VERSION")),
        ))
        return 2
    except Exception:  # noqa: BLE001 — fail-open 是刻意的，見模組 docstring 的 P0
        return 0


if __name__ == "__main__":
    sys.exit(main())
