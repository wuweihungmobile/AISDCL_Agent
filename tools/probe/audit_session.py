#!/usr/bin/env python3
"""每輪收尾的 session 逐字稿稽核器 —— PowerShell 工具面第一個觀測者。

WHY：指令字串從不變成 repo 裡的檔案，所有靜態掃描器結構上看不見鐵律二（禁裸 cd）、鐵律四
（宣稱先於查證）等違規；但 Claude Code 把每次工具呼叫逐字寫進 session 逐字稿，本檔就是讀那份
jsonl 的事後量測器（立案實測與各判準的沿革全文見證據檔〈九〉）。

🔴 邊界：只能當量測器，不得接成閘門
------------------------------------
逐字稿是 **untracked、機器本地、隨時會被清掉**的資料。所以本檔：
  · **只能當每輪收尾的量測器**——跑一次、把四個數字與宣稱清單記進帳本；
  · **不得接成 push 閘門或 CI 閘門**。別台機器（或清過快取的同一台）上那個
    目錄根本不存在，接成硬閘在結構上恆紅，而恆紅的閘門會被整個關掉，比沒有
    鎖更糟（本 repo 的 ARCH-R59-NB4 判例逐字記載過這件事）。

它自己失效的偵測：**逐支逐字稿**檢查「有記錄、卻一支帶 command 的 shell 呼叫都
抽不到」⇒ fail-loud（rc=1）。掃描面崩塌（目錄搬家／欄位改名／正則失效）不得靜默
通過成「本輪零違規」——那個失效方向看起來正好像「變乾淨了」，比紅更危險。

設計約束（各條的實測與沿革見證據檔〈九〉）：
  · 崩塌判準必須**逐支**：合計面的歷史總量會蓋掉「今天起每一支都抽不到」的格式變更；純問答的
    session 是真實的假陽性——去看那一支、在交件寫明理由，不是把判準關掉。
  · 計數**逐工具**（`COMMAND_PATTERNS`）：不同工具的指令不共用分母；Bash 的形態集合刻意為空。
  · 四個計數是字串形態偵測、宣稱對帳是啟發式：數量級可信，確切值不可引用成常數；列出的每一筆
    都是待人工看一眼的線索，不是判決。
  · 量測窗會被量測本身汙染（同期 agent 都在同一目錄開新逐字稿）：報表開頭固定印窗清單；要排除
    用 `--exclude`／`--exclude-self`／`--exclude-sid`（逐字稿沒有欄位能分辨掌舵者與 agent）。
  · 分期一律用 `--record-since`／`--record-until`（逐筆時戳）；`--since` 切的是檔案 mtime，
    跨切點的長 session 整支落後段。報表印判準指紋，指紋不同的兩組數字不可並列。

用法
----
    python tools/probe/audit_session.py                 # 本專案全部 session
    python tools/probe/audit_session.py --json
    python tools/probe/audit_session.py --transcript <某支 .jsonl>
    python tools/probe/audit_session.py --since 2026-08-06   # 只掃本輪那幾支
    python tools/probe/audit_session.py --latest 5           # 只掃最近改動的 5 支
    python tools/probe/audit_session.py --latest 5 --exclude-self   # 把自己剔出分母
    python tools/probe/audit_session.py --parity             # 兩端對拍，有分歧即 rc=1
    python tools/probe/audit_session.py --since <ISO> --five-question  # 判準②′ 五問量測
    python tools/probe/audit_session.py --protocol-status    # 審計協定雜湊／輪帳本窗口

    --record-until 2026-08-03T16:26:15                             # 兩面皆無觀測者
    --record-since 2026-08-03T16:26:15 --record-until 2026-08-07T00:05:53
    --record-since 2026-08-07T00:05:53                             # PowerShell 面也有
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from collections import Counter, deque
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _stdio_utf8  # noqa: E402,F401  （side effect：強制 stdout/stderr 為 UTF-8）
from lib import platform_utils  # noqa: E402  # DEF-200-421：claude_home() SSOT
from lib import rc_after_pipe_real as _rc_real  # noqa: E402  # R80 S7-01 判準本體

_REPO_ROOT = Path(__file__).resolve().parents[2]

# 🔴 攔截端的**純函式**直接向 hook 借、不抄第二份。依賴方向只能是 `tools/probe → .claude/hooks`
# （hook 由 `runpy.run_path` 起，import 誰都會在 import 期爆掉、破壞它的 fail-open 契約），所以
# `SHARED_PATTERN_SOURCE` 只能留複本。本段住檔案最前面：形態表在定義時就要用得到它。
_HOOK_PATH = _REPO_ROOT / ".claude" / "hooks" / "lint_powershell_command.py"
_hook_spec = importlib.util.spec_from_file_location("_lint_ps_hook", _HOOK_PATH)
_lint_ps_hook = importlib.util.module_from_spec(_hook_spec)
_hook_spec.loader.exec_module(_lint_ps_hook)
mask_regions = _lint_ps_hook.mask_regions

#: 🔴 **事後量測（本檔）與事中攔截（`.claude/hooks/lint_powershell_command.py`）
#: 共用的判準字面**。兩邊各存一份逐字相同的複本，因為那支 hook 由 `runpy.run_path`
#: 起、`sys.path` 上沒有 `tools/`，import 期爆掉會破壞它的 fail-open 契約 ⇒ 它只能是
#: 被抄的一方。代價已經發生過（R77：hook 那份有 `Tee-Object`、本檔那份沒有，兩份零
#: 比對 ⇒ 同一條規則「攔得下、卻量不到」）。既然結構上只能留複本，就把複本的
#: **一致性**變成會轉紅的事件，見 `tools/tests/test_check_hooks_liveness.py` 的
#: `TestHookAndProbeShareOneCriterion`（字面相等 ＋ 行為一致，兩向）。
#:
#: 🔴 修改守則：本字典要與 hook 那份**逐字相同**（連換行位置都相同才好 diff）。
SHARED_PATTERN_SOURCE: dict[str, str] = {
    # 管線接進這些 cmdlet 之後再讀 rc，才算命中（不是看到任何 `|` 都算）。
    # 🔴 R78／SA-01：**內建別名與全名同列**。上一版只列全名，實測 12 組「別名 vs
    # 全名、其餘字元逐字相同」的配對 **12/12 不對稱**（`| select -First 5` 放行、
    # `| Select-Object -First 5` 擋下）——而 `select` 正是「提前結束管線」最常見的
    # 寫法，等於這道鎖擋掉的剛好是沒人會寫的那一半。每個別名自帶右邊界
    # `(?![\w-])` 以免吃到 `selection`／`sortable`；`%` 與 `?` 另用 `(?=\s|\{|$)`，
    # 避免誤傷 `$_ % 2` 那類真正的運算子用法。
    "pipe-cmdlets": (
        r"(?:Select-Object|Select-String|Out-\w+|Format-\w+|Sort-Object"
        r"|Measure-Object|ForEach-Object|Where-Object|Tee-Object"
        r"|head|tail|findstr)(?![\w-])"
        r"|(?:select|sls|sort|measure|foreach|where|ft|fl|oh|tee)(?![\w-])"
        r"|[%?](?=\s|\{|$)"
    ),
    # 裸 cd／Set-Location 的**動詞面**（不含錨點——兩邊各自接自己的邊界）。
    # 🔴 R78／SD-01：補上 `chdir`／`sl` 兩個內建別名；並**移除 `(?!-)`**——
    # `Set-Location -Path X` 與 `cd X` 是同一件事，上一版只因為下一個字元是 `-`
    # 就整條放行＝一步就繞過。
    # 🔴 R79：參數改成**可選**。上一版尾巴硬性要求 `\s+\S`（至少一個參數），於是
    # **不帶參數**的 `cd`／`sl`／`chdir`／`Set-Location` 整條放行——而那一種在
    # PowerShell 語意上是切到 $HOME，鐵律二要防的「cwd 跨呼叫持續、之後每個相對路徑
    # 都找錯地方」在它身上只會更嚴重（後續全部相對路徑一次全錯）。規則自己要求了
    # 一個它不需要的東西。尾巴改成「有參數，或這一句到此為止（`;`／換行／管線／
    # 鏈接／區塊結尾／字串結尾）」。
    "naked-cd": r"(cd|chdir|sl|Set-Location)(?![\w-])(?:\s+\S|\s*(?=[;\n|&)}]|$))",
    # 裸 bash 的**指令字面**（`bash` / `bash.exe`）。刻意只到動詞為止：「跑的是不是
    # .sh」由兩邊各自補上（hook 要在遮蔽過的結構面找指令位置、回原文找 `.sh`，探針
    # 則就地把兩者接成一條），見各自的組裝處。
    # 🔴 R78／SD-01：上一版只認 `bash` 字面，`bash.exe` 一步就繞過。
    "bare-bash-sh": r"bash(?:\.exe)?(?![\w.-])",
}

def _rc_after_pipe(command: str) -> bool:
    """規則①的量測端＝**攔截端那支函式本身**（不再自寫第二份判準）。

    自寫的扁平正則與攔截端在兩個相反方向同時失準（多行指令低報、把正解形態高報），借過來之後
    這個欄位的語意才真的等於「攔截器會擋的那件事」。沿革見證據檔〈九〉。
    """
    return bool(_lint_ps_hook._rc_after_pipe(
        mask_regions(command, keep_expandable=False),
        mask_regions(command, keep_expandable=True),
    ))


# 🔴 把「攔截端會擋什麼」與「真的會量到假 rc 幾次」拆成兩欄：判準本體、pwsh 實測表與紅綠自證語料
# 住 `tools/lib/rc_after_pipe_real.py`；下面兩支是薄殼，只把已載入的 hook 模組餵進去。


def _rc_after_pipe_real(command: str) -> bool:
    """上游原生 × 截斷型管線 × 之後讀 rc ＝ 真的會量到假 rc 的那一種。"""
    return _rc_real.rc_after_pipe_real(command, _lint_ps_hook)


def rc_selftest() -> list[str]:
    """`--selftest`：跑那張實測語料表，回傳失敗訊息清單（空＝全綠）。"""
    return _rc_real.selftest(_lint_ps_hook)


#: PowerShell 工具面的形態偵測器。鍵即報表欄名；值是 `str -> truthy/falsy` 的**可呼叫**（規則①借的
#: 是攔截端的函式、不是正則）。`inline-loop` 已拆成兩欄且舊欄名刻意不保留：新舊數字**不可比較**。
_POWERSHELL_PATTERNS: dict[str, object] = {
    # 🔴 **對拍錨，不是違規次數**：逐字等於攔截端會擋的那件事（攔截端刻意偏擋，全母體實測 91.4% 是
    # 誤報），**不得**被引用成「違規了幾次」；存在的理由是讓 `--parity` 證明兩端沒漂移。
    "rc-after-pipe": _rc_after_pipe,
    # 🔴 **唯一可引用為「量到幾次真風險」的那一欄**：上游原生指令 × 實測會提前結束的管線元素 ×
    # 之後才讀 rc，三者同時成立才算（逐形態實測依據見 `tools/lib/rc_after_pipe_real.py`）。
    "rc-after-pipe-real": _rc_after_pipe_real,
    # 現寫的控制流：沒有任何測試看過這段碼，寫錯了只會表現成「數字怪怪的」。
    "inline-loop-statement": re.compile(
        r"\b(foreach\s*\(|for\s*\(\s*\$)", re.IGNORECASE
    ).search,
    # 慣用管線投影（`| ForEach-Object { … }`／`| % { … }`）：PowerShell 的日常寫法、不是「現寫的沒驗
    # 過的碼」，且**沒有攔截端**（見 `_INTERCEPTED_KEYS`）⇒ 結構上不可能被壓到 0。
    "pipeline-foreach": re.compile(
        r"\|\s*(ForEach-Object(?![\w-])|%(?=\s|\{|$))", re.IGNORECASE
    ).search,
    # 鐵律二：PowerShell 工具的 cwd 跨呼叫持續，裸 cd 之後的相對路徑全部會找錯地方。邊界與 hook 同一
    # 組「下一個指令從這裡開始」的入口（`&&`／`||`／`|`／`{`／`(` 之後），否則同一段違規「攔得下、卻
    # 量不到」。
    "naked-cd": re.compile(
        r"(?:^|[;\n|&{}()])\s*" + SHARED_PATTERN_SOURCE["naked-cd"], re.IGNORECASE
    ).search,
    # 裸 bash：Get-Command bash 解析到 system32 的 WSL 佔位版。共用字面只到動詞為止＝只認
    # **指令位置**；「跑的是不是 .sh」交給 `_CORROBORATORS`（路徑常寫在引號裡，遮蔽面上看不到
    # `.sh`）。
    "bare-bash-sh": re.compile(
        r"(?:^|[;\n|&{}()])\s*" + SHARED_PATTERN_SOURCE["bare-bash-sh"],
        re.IGNORECASE,
    ).search,
}

#: 有**事中攔截端**的形態（＝`lint_powershell_command.py` 真的會擋的那三條）。
#: 其餘只有量測、沒有攔截 ⇒ 它們結構上不可能被壓到 0，報表必須就地標明；否則一個
#: 永遠非零的數字會被讀成「一直沒人處理的違規」，而其實根本沒有人在擋它。
_INTERCEPTED_KEYS = frozenset({"rc-after-pipe", "rc-after-pipe-real",
                               "naked-cd", "bare-bash-sh"})

#: `{工具名: {形態: 正則}}`。逐工具是刻意的（沿革見證據檔〈九〉）：這些形態只約束 PowerShell 工具，
#: 混進 Bash 會得到近 100% 假陽性。`Bash` 鍵刻意留空且**不得刪除**：它是 `SHELL_TOOLS` 與 Bash 分母
#: 的來源。
COMMAND_PATTERNS: dict[str, dict[str, re.Pattern[str]]] = {
    "PowerShell": _POWERSHELL_PATTERNS,
    "Bash": {},
}

#: 帶 `command` 欄、會落進本稽核射程的工具（由上表推導，不另立第二個家）。
SHELL_TOOLS = tuple(COMMAND_PATTERNS)

#: 阻斷的唯一判準＝harness 自己蓋的章：`tool_result.is_error` 為真，且該記錄帶 `toolDenialKind`。
#: 子字串比對會被引文騙（grep 證據檔把 hook 錯誤字樣印出來即被誤判成被擋）。
_HOOKERR_RE = re.compile(r"^\s*(?:Pre|Post)ToolUse:\S+ hook error: \[(.*?)\]: ")
_SDD_RE = re.compile(r"^\s*\[SDD-(?:FSM|CTX)\]")
_USAGE_KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def block_source(rec: dict, block: dict, text: str) -> tuple[str, str] | None:
    """tool_result 的阻斷來源 `(kind, 細節)`；`None`＝不是阻斷。kind＝hook／sdd-router／
    non-hook（auto-mode 分類器、人拒絕、無前綴的 permission-rule）；hook 細節＝方括號內末個 .py。"""
    if not (block.get("is_error") and rec.get("toolDenialKind")):
        return None
    if hit := _HOOKERR_RE.match(text):
        return "hook", (re.findall(r"[\w.-]+\.py\b", hit.group(1)) or ["?"])[-1]
    return (("sdd-router", "sdd_hook_router.py") if _SDD_RE.match(text)
            else ("non-hook", str(rec["toolDenialKind"])))

#: 助理訊息裡「我已經驗過了」形態的句子。
CLAIM_RE = re.compile(r"(全綠|已驗證|全部通過|rc\s*=\s*0|\bpassed\b|\bPASS\b)")

#: 佐證字樣：只留「真的是某次執行的輸出」才會有的形狀。裝飾字元（`✅`）與裸 `ok` 零鑑別力，曾讓判出
#: 率塌到 0/72 而被讀成「沒有失實宣稱」；`OK` 必須自成行首（unittest 終端那個 OK）。實測見證據檔
#: 〈九〉。
EVIDENCE_RE = re.compile(
    r"(rc\s*=\s*0|Exit code:\s*0|\b\d+\s+passed\b|All checks passed|(?m:^OK\b))",
    re.IGNORECASE,
)

#: 宣稱往回看幾個 tool_result。窗太大會讓「前面任何一次 rc=0」替之後的宣稱背書（近乎恆真），太小會把
#: 連講兩句的宣稱全誤判；3＝「一句宣稱通常指的是它前面一兩次執行」（全史敏感度掃描表見證據檔
#: 〈九〉）。🔴 它是**判準的一部分**、不是常數：報表連窗一起印，引用百分比必須連窗一起引。誠實劃界：
#: 仍是啟發式，列出的每一筆是**待人工看一眼的線索，不是判決**。
DEFAULT_WINDOW = 3

#: 與攔截器同義的**放行**面：量測器不跟著放行，同一段指令會「攔截器說沒事、量測器記一筆違規」。放行
#: 不等於消失：豁免另計在 `exempted_calls`。🔴 不進 `SHARED_PATTERN_SOURCE`（那張表是「違規長什麼
#: 樣」，放行是另一件事）；兩邊是否同步由行為一致鎖覆蓋。比對面只認**住在真註解裡**的標記（見
#: `_exempt`）。
EXEMPT_RE = re.compile(r"#\s*ps-lint-ok:\s*\S")


def _exempt(command: str) -> bool:
    """行內豁免是否成立——與攔截端同一個判準；只認真註解裡的標記，在字串裡**引述**它不算。"""
    return bool(EXEMPT_RE.search(
        mask_regions(command, keep_expandable=False, keep_comments=True)))
_FIND_GIT_BASH_RE = re.compile(r"Find-GitBash", re.IGNORECASE)

#: `key -> 抑制條件`：命中了、但屬於 repo 明文指定的正解，不計為違規。
_SUPPRESSORS: dict[str, re.Pattern[str]] = {"bare-bash-sh": _FIND_GIT_BASH_RE}

#: `key -> 佐證條件（比對**原文**）`：指令位置從遮蔽過的結構面讀、佐證從原文讀。
#: 為何要拆兩面：`bash "tools/x.sh"` 的路徑住在引號裡，遮蔽面上看不到 `.sh`；而
#: `$doc = "…bash tools/x.sh…"` 在原文上看得到 `bash` 卻不是指令。兩面各取所長。
_CORROBORATORS: dict[str, re.Pattern[str]] = {
    "bare-bash-sh": re.compile(r"\.sh(?![\w])", re.IGNORECASE)
}

def comparison_surfaces(command: str) -> dict[str, str]:
    """`形態 key -> 該餵哪一面給它的偵測器`：指令位置類的形態吃**結構面**（字串／註解裡的 cd、bash
    不是指令）；`rc-after-pipe` 系吃**原文**（它自己要同時看結構面與展開面來比位置）。"""
    structural = mask_regions(command, keep_expandable=False)
    return {
        "rc-after-pipe": command,
        # 同上：它自己要同時看結構面與展開面比位置，所以只能拿到原文。
        "rc-after-pipe-real": command,
        "inline-loop-statement": structural,
        "pipeline-foreach": structural,
        "naked-cd": structural,
        "bare-bash-sh": structural,
    }


def project_transcript_dir(repo_root: Path) -> Path:
    """`repo_root` 對應的 Claude Code 逐字稿目錄。slug＝把路徑裡每個非英數字元換成 `-`
    （觀察到的編碼、非官方契約，故 `--project-dir` 一律可覆寫、目錄不存在時 fail-loud）。
    DEF-200-421：家目錄一律經 `platform_utils.claude_home()`，尊重 `CLAUDE_CONFIG_DIR`。"""
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(repo_root))
    return platform_utils.claude_home() / "projects" / slug


def iter_records(path: Path):
    """逐行 yield 解析得出的 jsonl 記錄（壞行直接跳過，逐字稿常有半截尾行）。"""
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict):
                yield rec


def _blocks(rec: dict) -> tuple[str, list]:
    msg = rec.get("message")
    if not isinstance(msg, dict):
        return "", []
    content = msg.get("content")
    return str(msg.get("role") or ""), content if isinstance(content, list) else []


def _result_text(block: dict) -> str:
    """tool_result 區塊的文字內容（content 可能是 str，也可能是區塊清單）。"""
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(b.get("text") or "") for b in content if isinstance(b, dict)
        )
    return ""


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？!?\n])", text)
    return [p.strip() for p in parts if p.strip()]


def _user_prompt_text(rec: dict) -> str:
    """user 角色訊息的純文字（可能是 str，也可能是區塊清單）。空字串＝不是人打的話。"""
    msg = rec.get("message")
    if not isinstance(msg, dict) or msg.get("role") != "user":
        return ""
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(b.get("text") or "") for b in content
                         if isinstance(b, dict) and b.get("type") == "text")
    return ""


def detector_hits(command: str, detectors: dict) -> set[str]:
    """一條指令在 `detectors` 底下命中的形態集合（純函式，供對拍與注入自證）。"""
    surfaces = comparison_surfaces(command)
    hits: set[str] = set()
    for key, detect in detectors.items():
        suppressor = _SUPPRESSORS.get(key)
        corroborator = _CORROBORATORS.get(key)
        if (detect(surfaces.get(key, command))
                and (corroborator is None or corroborator.search(command))
                and not (suppressor and suppressor.search(command))):
            hits.add(key)
    return hits


#: 攔截端只透過 stderr 的 hint 對外表示它判了哪一條，所以由 hint 的特徵字反推規則。
#: 這三個字面同時是 `tools/tests/test_check_hooks_liveness.py` 的 `MUST_BLOCK` 在斷言的
#: 「擋了要指出出口」那個 needle ⇒ 改了 hint 會在那邊先紅，本表不會靜默過期。
_HOOK_RULE_BY_HINT: dict[str, str] = {
    "rc-after-pipe": "LASTEXITCODE",
    "naked-cd": "Push-Location",
    "bare-bash-sh": "Find-GitBash",
}


def hook_rules(command: str) -> set[str]:
    """攔截端對這條指令判了哪幾條規則（純函式，供對拍）。"""
    joined = "\n".join(_lint_ps_hook.lint_command(command))
    return {key for key, needle in _HOOK_RULE_BY_HINT.items() if needle in joined}


def parity_divergences(commands) -> list[dict]:
    """攔截端 × 量測端對**同一批真實指令**的判定分歧（`[]`＝沒有分歧）。語料是真的流量、不是手寫樣本
    （手寫短指令結構上看不到多行／管線後另起呼叫的分歧）。只比三條兩端都有的規則；行內豁免直接跳過。
    """
    out: list[dict] = []
    for command in commands:
        if _exempt(command):
            continue
        theirs = hook_rules(command)
        mine = detector_hits(command, _POWERSHELL_PATTERNS) & set(_HOOK_RULE_BY_HINT)
        if theirs != mine:
            out.append({"command": command[:400], "hook": sorted(theirs),
                        "probe": sorted(mine)})
    return out


def powershell_commands(paths: list[Path]) -> list[str]:
    """量測窗內出現過的 unique PowerShell 指令（出現序，供對拍用）。"""
    seen: dict[str, None] = {}
    for path in paths:
        for rec in iter_records(path):
            _role, blocks = _blocks(rec)
            for block in blocks:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                if block.get("name") != "PowerShell":
                    continue
                inp = block.get("input")
                cmd = inp.get("command") if isinstance(inp, dict) else None
                if isinstance(cmd, str) and cmd:
                    seen.setdefault(cmd, None)
    return list(seen)


def criterion_fingerprint() -> str:
    """借來那支攔截端 hook 的內容雜湊（前 12 碼）：判準本體是 live hook 函式、會換版，指紋不同的兩組
    數字不可並列比較。"""
    import hashlib
    try:
        return hashlib.sha256(_HOOK_PATH.read_bytes()).hexdigest()[:12]
    except OSError:
        return "unreadable"


def _record_time(rec: dict) -> datetime | None:
    """記錄自己的 `timestamp`（ISO，帶時區）。`None`＝這一筆沒有時戳。"""
    raw = rec.get("timestamp")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def scan_transcript(path: Path, window_size: int = DEFAULT_WINDOW,
                    record_since: datetime | None = None,
                    record_until: datetime | None = None) -> dict:
    """單支逐字稿的量測結果（純資料，報表與 rc 由呼叫端決定）。`record_since`／`record_until` 是
    **逐筆**時間切片（見檔頭〈設計約束〉）；有切片時沒有時戳的記錄一律排除（不猜）。"""
    counts = {tool: dict.fromkeys(pats, 0) for tool, pats in COMMAND_PATTERNS.items()}
    shell_by_tool = dict.fromkeys(COMMAND_PATTERNS, 0)
    exempted = 0
    tool_totals: dict[str, int] = {}
    records_total = 0
    window: deque[str] = deque(maxlen=max(1, window_size))
    unsupported: list[str] = []
    claims_total = 0
    # 🔴 Bash 嘗試要**逐筆攤開**、不能只留總數：分子若幾乎全是這道鎖自己的探針，攔阻率是自我實現的
    # （分辨線索是 `description`）。實測沿革見證據檔〈九〉。
    bash_attempts: list[dict] = []
    pending_bash: dict[str, dict] = {}
    session_id = ""
    first_prompt = ""

    sliced = record_since is not None or record_until is not None
    for rec in iter_records(path):
        if sliced:
            when = _record_time(rec)
            if when is None:
                continue
            if record_since is not None and when < record_since:
                continue
            if record_until is not None and when >= record_until:
                continue
        records_total += 1
        if not session_id:
            session_id = str(rec.get("sessionId") or "")
        if not first_prompt:
            first_prompt = " ".join(_user_prompt_text(rec).split())[:110]
        role, blocks = _blocks(rec)
        for block in blocks:
            if not isinstance(block, dict):
                continue
            kind = block.get("type")
            if kind == "tool_use":
                name = str(block.get("name") or "")
                tool_totals[name] = tool_totals.get(name, 0) + 1
                inp = block.get("input")
                cmd = inp.get("command") if isinstance(inp, dict) else None
                if name == "Bash":
                    entry = {
                        "command": " ".join(str(cmd or "").split())[:120],
                        # description 是分辨「這道鎖自己的探針」與「真的誤用」的
                        # 唯一線索（本輪 5/7 的 description 逐字寫著在驗這道鎖）。
                        "description": str((inp or {}).get("description") or "")[:80]
                        if isinstance(inp, dict) else "",
                        "blocked": None,
                    }
                    bash_attempts.append(entry)
                    if block.get("id"):
                        pending_bash[str(block["id"])] = entry
                if name not in COMMAND_PATTERNS or not isinstance(cmd, str) or not cmd:
                    continue
                shell_by_tool[name] += 1
                if _exempt(cmd):
                    exempted += 1  # 攔截器放行的，量測器也放行（但另計，見常數旁註解）
                    continue
                for key in detector_hits(cmd, COMMAND_PATTERNS[name]):
                    counts[name][key] += 1
            elif kind == "tool_result":
                text = _result_text(block)
                entry = pending_bash.pop(str(block.get("tool_use_id") or ""), None)
                if entry is not None:
                    entry["blocked"] = block_source(rec, block, text) is not None  # 引文不算
                window.append(text)
            elif kind == "text" and role == "assistant":
                corpus = "\n".join(window)
                for sentence in _sentences(str(block.get("text") or "")):
                    if not CLAIM_RE.search(sentence):
                        continue
                    claims_total += 1  # 🔴 分母也要記：只印分子時，「CLAIM_RE 自己
                    # 失效」與「真的零違規」長得一模一樣。
                    if not EVIDENCE_RE.search(corpus):
                        unsupported.append(sentence[:200])

    shell_calls = sum(shell_by_tool.values())
    #: 被叫過幾次「本來就帶 command 的工具」——與 `shell_calls`（真的抽到指令的次數）
    #: 相減即「叫了但抽不到」，那是格式變更唯一乾淨的訊號。
    shell_tool_calls = sum(v for k, v in tool_totals.items() if k in COMMAND_PATTERNS)
    return {
        "transcript": path.name,
        # 🔴 窗的可回查性：帳本記的每個數字都必須能指回「是哪幾支、什麼時候、誰在講話」——
        # `--latest N` 是 mtime 浮動窗，同期 agent 會讓同一條指令隔一小時給不同答案。
        "session_id": session_id,
        "first_prompt": first_prompt,
        # 逐字稿最後寫入時間。**時間切片的唯一依據**：Q4 那種「觀測者上線前 vs 上線後」
        # 的比較必須能重跑，把切片留在下游腳本裡就等於下一輪要重寫一次。
        "mtime": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        "records": records_total,
        "tool_use_total": sum(tool_totals.values()),
        "by_tool": tool_totals,
        "shell_calls": shell_calls,
        "shell_calls_by_tool": shell_by_tool,
        "exempted_calls": exempted,
        "bash_tool_attempts": tool_totals.get("Bash", 0),
        # 分子攤開（見 `bash_attempts` 旁的區塊註解）：只留總數時，「攔阻率 100%」
        # 與「那個 100% 幾乎全是這道鎖自己的探針」印出來一模一樣。
        "bash_attempt_details": bash_attempts,
        "patterns": counts,
        # 逐支崩塌訊號（見檔頭〈設計約束〉）：**有記錄**卻一支帶 command 的 shell 呼叫都抽不到。前提
        # 用 `records` 而不是 `tool_use_total`（連 tool_use 都認不出來正是最徹底的格式變更）。🔴 逐
        # 筆切片下前提改為「**shell 工具真的被叫過**、卻一條指令都抽不到」：子窗裡沒跑 shell 是正常
        # 狀態，沿用 `records>0` 會讓警報在分期用法下常響（常響的警報等於沒有）。誠實劃界：切片下連
        # 工具名都認不出來（`PowerShell` 被改名）時本判準看不到，由合計面的 `shell_calls == 0` 兜
        # 底。
        "collapsed": (shell_tool_calls > 0 if sliced else records_total > 0)
        and shell_calls == 0,
        "unsupported_claims": unsupported,
        # 分母（命中 CLAIM_RE 的句子總數）。只印分子時，「CLAIM_RE 失效」與「真的
        # 零違規」長得一模一樣，而後者是沒有人會去追的那一種。
        "claims_total": claims_total,
        # 判準的一部分：換一個窗就是另一個數字，所以它必須跟著數字一起走。
        "claim_window": window_size,
    }


def aggregate(results: list[dict]) -> dict:
    """跨 session 合計 —— 帳本要記的數字。**逐工具**，見檔頭 SD-04 那一段。"""
    totals = {tool: dict.fromkeys(pats, 0) for tool, pats in COMMAND_PATTERNS.items()}
    shell_by_tool = dict.fromkeys(COMMAND_PATTERNS, 0)
    bash_attempts = 0
    bash_details: list[dict] = []
    exempted = 0
    claims = 0
    claims_total = 0
    for res in results:
        bash_attempts += res["bash_tool_attempts"]
        bash_details += res.get("bash_attempt_details") or []
        exempted += res["exempted_calls"]
        claims += len(res["unsupported_claims"])
        claims_total += res["claims_total"]
        for tool, value in res["shell_calls_by_tool"].items():
            shell_by_tool[tool] = shell_by_tool.get(tool, 0) + value
        for tool, per_tool in res["patterns"].items():
            for key, value in per_tool.items():
                totals.setdefault(tool, {})[key] = totals.get(tool, {}).get(key, 0) + value
    return {
        "sessions": len(results),
        "shell_calls": sum(shell_by_tool.values()),
        "shell_calls_by_tool": shell_by_tool,
        "exempted_calls": exempted,
        "bash_tool_attempts": bash_attempts,
        "bash_attempt_details": bash_details,
        "patterns": totals,
        "collapsed_sessions": [r["transcript"] for r in results if r["collapsed"]],
        "unsupported_claim_count": claims,
        "claim_sentences_total": claims_total,
        "claim_window": results[0]["claim_window"] if results else DEFAULT_WINDOW,
        # 窗的定義本身也是資料：帳本引用任何一個數字時必須連它一起記，否則下一個人
        # 重跑會拿到別的數字然後去找一個不存在的原因。
        "window_manifest": [
            {"transcript": r["transcript"], "session_id": r["session_id"],
             "mtime": r["mtime"], "records": r["records"],
             "powershell_calls": r["shell_calls_by_tool"].get("PowerShell", 0),
             "first_prompt": r["first_prompt"]}
            for r in results
        ],
    }


def collapse_verdict(summary: dict) -> str | None:
    """`None`＝掃描面健在；回字串＝掃描面崩塌的理由（純函式，供注入自證）。三款由窄到寬：掃不到檔／
    **某幾支**抽不到 shell 呼叫／整批合計為零；第二款才是預設用法下真的打得到的（歷史總量蓋不掉
    它）。"""
    if summary["sessions"] == 0:
        return ("掃不到任何 session 逐字稿——目錄不存在／已被清空／`--since`、`--latest` "
                "把窗縮到空。本檔是量測器不是閘門，但『量到零』與『量不到』必須分得開")
    collapsed = summary.get("collapsed_sessions") or []
    if collapsed:
        return (f"有記錄、卻一支帶 command 的 shell 呼叫都抽不到：{collapsed} ⇒ 掃描面"
                "對這幾支崩塌（欄位改名／記錄格式變更／COMMAND_PATTERNS 的工具鍵過期）。"
                "這個失效方向看起來像『變乾淨了』，比紅更危險，故 fail-loud。"
                "若確認那幾支真的整場沒用過 shell（純問答／純讀檔），"
                "用 --transcript／--since／--latest 把量測窗縮到本輪那幾支再跑")
    if summary["shell_calls"] == 0:
        return ("帶 command 的 shell 呼叫數為 0 ⇒ 掃描面崩塌（逐字稿全為空檔？），"
                "不是『本輪零違規』")
    return None


def _print_pattern_block(patterns: dict, shell_by_tool: dict, indent: str) -> None:
    """逐工具印形態計數。**每一列都帶自己的分母**——混用分母正是 SD-04 那一筆。"""
    for tool, per_tool in patterns.items():
        denominator = shell_by_tool.get(tool, 0)
        if not per_tool:
            print(f"{indent}[{tool}] 帶 command 的呼叫 {denominator}"
                  f"（本工具無形態判準：鐵律一已禁用它，工具存在本身即違規）")
            continue
        print(f"{indent}[{tool}] 帶 command 的呼叫 {denominator}（＝以下各列的分母）")
        for key, value in per_tool.items():
            pct = 100.0 * value / denominator if denominator else 0.0
            note = "" if key in _INTERCEPTED_KEYS else "  ← 僅量測，無攔截端"
            print(f"{indent}  {key:22s} {value:5d}  "
                  f"({pct:.1f}% of {tool} calls){note}")


def _print_window_manifest(summary: dict) -> None:
    """🔴 報表**開頭**固定印出「這一次到底量了哪幾支」：量測這個動作本身會改變下一次的量測值（同期
    agent 在同一目錄開新逐字稿），窗不印出來，帳本的數字就沒有人能回查。逐字稿沒有欄位能分辨掌舵者與
    agent，故不自動分類——要排除就用 `--exclude`／`--exclude-self`／`--exclude-sid`（明示而非猜測）。
    """
    manifest = summary.get("window_manifest") or []
    print(f"### 量測窗（{len(manifest)} 支；引用任何數字時請連本段一起記）")
    # 🔴 判準指紋與逐筆切片同屬「這個數字是用哪一把尺、量哪一段」的定義，必須跟著數字走。
    slice_lo, slice_hi = (summary.get("record_slice") or [None, None])
    print(f"  判準指紋（借來的攔截端 hook 內容雜湊）: "
          f"{summary.get('criterion_fingerprint', '?')}"
          "  ← 指紋不同的兩組數字不可放在一起比")
    print(f"  逐筆時間切片: {slice_lo or '（無）'} ~ {slice_hi or '（無）'}"
          f"{'' if (slice_lo or slice_hi) else '  ← 未切片＝這是歷史總量，不是本輪'}")
    for row in manifest:
        print(f"  · {row['transcript']}  mtime={row['mtime']}  "
              f"記錄={row['records']}  PowerShell={row['powershell_calls']}")
        print(f"      開場白: {row['first_prompt'] or '（無 user 文字訊息）'}")


def _print_report(results: list[dict], summary: dict, max_claims: int) -> None:
    _print_window_manifest(summary)
    for res in results:
        by_tool = res["by_tool"]
        print(f"\n### {res['transcript']}{'  ⚠️ 崩塌訊號' if res['collapsed'] else ''}")
        print(f"  記錄 {res['records']}  tool_use 總數: {res['tool_use_total']}  |  "
              f"Bash={by_tool.get('Bash', 0)}  PowerShell={by_tool.get('PowerShell', 0)}")
        _print_pattern_block(res["patterns"], res["shell_calls_by_tool"], "    ")
        claims = res["unsupported_claims"]
        if claims:
            print(f"  無對應輸出的宣稱: {len(claims)} / {res['claims_total']} 句宣稱"
                  "（啟發式，需人工看一眼）")
            for sentence in claims[:max_claims]:
                print(f"    · {sentence}")
            if len(claims) > max_claims:
                print(f"    …另有 {len(claims) - max_claims} 句（--max-claims 可調）")

    print(f"\n### 合計（{summary['sessions']} 支逐字稿；帳本要記的數字）")
    print("  🔴 逐工具分開記——不同工具的指令不共用分母（見檔頭 SD-04）")
    _print_pattern_block(summary["patterns"], summary["shell_calls_by_tool"], "  ")
    details = summary.get("bash_attempt_details") or []
    blocked = sum(1 for d in details if d.get("blocked"))
    print(f"  Bash 工具嘗試數（鐵律一違規本身）  {summary['bash_tool_attempts']}"
          f"（其中被擋下 {blocked}）")
    if details:
        # 🔴 逐筆印出：攔阻率的分子若幾乎全是這道鎖自己的探針就是自我實現的；分辨線索是
        # description。
        print("  🔴 分子攤開——請自行判讀哪幾筆是「驗這道鎖還活著」的探針："
              "以自己的探針當分子時，攔阻率是自我實現的")
        for detail in details[:20]:
            mark = {True: "擋下", False: "未擋", None: "無結果"}[detail.get("blocked")]
            print(f"      [{mark}] {detail.get('description') or '（無描述）'}"
                  f"  ||  {detail.get('command', '')[:70]}")
        if len(details) > 20:
            print(f"      …另有 {len(details) - 20} 筆（--json 可取全部）")
    print(f"  行內豁免而未計形態的呼叫           {summary['exempted_calls']}")
    # 🔴 分子與分母**與窗**一起印：只印分子時，「CLAIM_RE 自己失效（分母崩了）」與
    # 「真的零違規」印出來一模一樣，而後者沒有人會去追；不印窗則換個窗就是另一個數字。
    print(f"  無對應輸出的宣稱                   "
          f"{summary['unsupported_claim_count']} / "
          f"{summary['claim_sentences_total']} 句命中 CLAIM_RE"
          f"（往回看 {summary['claim_window']} 個 tool_result）")
    if summary["collapsed_sessions"]:
        print(f"  ⚠️ 崩塌訊號的逐字稿                {summary['collapsed_sessions']}")


def select_paths(paths: list[Path], since: str | None = None, until: str | None = None,
                 latest: int | None = None,
                 exclude: list[str] | None = None) -> list[Path]:
    """把量測窗縮到「本輪那幾支」（沒有這個，崩塌判準就只能對著歷史總量說話）。

    `since`／`until` 吃 ISO，以檔案 mtime 篩（跨切點的長 session 整支落後段）；`latest`＝只留最近改
    動的 N 支；`exclude`＝檔名含任一子字串者剔除，且在 `latest` **之前**套用（否則被剔掉的仍會先把別
    人擠出窗外）。剔除必須是明示的：逐字稿沒有欄位能可靠地區分掌舵者與 agent。窗篩空時**不吞掉**——回
    空清單讓 `collapse_verdict` 說「量不到」。"""
    files = [p for p in paths if p.is_file()]
    for needle in exclude or []:
        if needle:
            files = [p for p in files if needle not in p.name]
    if since:
        low = datetime.fromisoformat(since).timestamp()
        files = [p for p in files if p.stat().st_mtime >= low]
    if until:
        high = datetime.fromisoformat(until).timestamp()
        files = [p for p in files if p.stat().st_mtime < high]
    files.sort(key=lambda p: p.stat().st_mtime)
    if latest is not None:
        files = files[-latest:] if latest > 0 else []
    return files


# ══════════════════════════════════════════════════════════════════════════
# 判準②′ 五問量測（只印不擋、rc 恆 0；操作型定義與校準見證據檔〈九〉）
# ══════════════════════════════════════════════════════════════════════════
_PROTOCOL_DIR = _REPO_ROOT / "docs" / "06_quality" / "FiveQuestion_Audit_Protocol"
_LEDGER = _PROTOCOL_DIR.parent / "FiveQuestion_Round_Ledger.jsonl"


def _params() -> dict:
    """閾值與量測句型（正則）都凍結在協定目錄、入雜湊：更動任何一個即重置窗口。"""
    return json.loads((_PROTOCOL_DIR / "params.json").read_text(encoding="utf-8"))


def _used(usage: dict) -> int:
    """與 `--check` 同式：input＋cache_creation＋cache_read（output 不計）。"""
    return sum(int(usage.get(k) or 0) for k in _USAGE_KEYS)


def session_profile(path: Path) -> dict:
    """單趟掃描主執行緒（非 isSidechain）：tool_use 序列與阻斷、助理文字、簡報、最後 usage。"""
    prof: dict = {"sid": path.stem, "entry": "", "start": None, "cwd": "", "uses": [],
                  "texts": [], "brief": False, "usage": None, "usage_ts": None}
    by_id: dict[str, dict] = {}
    recent: deque[bool] = deque(maxlen=DEFAULT_WINDOW)  # 最近幾個 tool_result 是否為阻斷
    for rec in iter_records(path):
        if rec.get("isSidechain"):
            continue
        prof["entry"] = prof["entry"] or str(rec.get("entrypoint") or "")
        prof["cwd"] = prof["cwd"] or str(rec.get("cwd") or "")
        prof["start"] = prof["start"] or _record_time(rec)
        att = rec.get("attachment") if isinstance(rec.get("attachment"), dict) else {}
        if not prof["uses"] and att.get("hookName") == "SessionStart:startup":
            prof["brief"] = prof["brief"] or "[SDD-CTX-GUARD]" in str(att)
        role, blocks = _blocks(rec)
        if role == "assistant" and isinstance(rec["message"].get("usage"), dict):
            prof["usage"], prof["usage_ts"] = _used(rec["message"]["usage"]), _record_time(rec)
        for block in (b for b in blocks if isinstance(b, dict)):
            kind, tid = block.get("type"), str(block.get("tool_use_id") or block.get("id"))
            if kind == "tool_use":
                inp = block.get("input")
                by_id[tid] = {"name": str(block.get("name") or ""), "block": None,
                              "input": inp if isinstance(inp, dict) else {}}
                prof["uses"].append(by_id[tid])
            elif kind == "tool_result":
                src = block_source(rec, block, _result_text(block))
                if src and tid in by_id:
                    by_id[tid]["block"] = src
                recent.append(src is not None)
            elif kind == "text" and role == "assistant":
                prof["texts"].append((len(prof["uses"]), any(recent), str(block.get("text") or "")))
    prof["start"] = prof["start"] or datetime.fromtimestamp(path.stat().st_mtime).astimezone()
    return prof


def _hook_module(name: str):
    """借 `.claude/hooks/<name>.py` 當重放 oracle；讀不進回 None（絕不當成放行）。"""
    try:
        spec = importlib.util.spec_from_file_location(name, _HOOK_PATH.with_name(name + ".py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:  # oracle 不可用＝no-oracle，由呼叫端升級成人工複核
        return None


def judge_block(use: dict, cwd: str, bdg, prm: dict) -> str:
    """Q1′a oracle：於 HEAD 重放該 hook 的判準（bdg＝block_destructive_git 模組或 None）。回
    correct／MISBLOCK／human／listed／no-oracle。與守衛同一份碼：抓得到接線漂移，抓不到判準誤判。"""
    (kind, hook), tool, inp = use["block"], use["name"], use["input"]
    cmd = str(inp.get("command") or "")
    if kind == "sdd-router":
        return "human"  # 只判得到規則一致；狀態是否陳舊＝人供
    if tool not in prm["converge_tools"]:
        return "listed"  # 扇出型被 context_budget_guard 擋＝派工預算，不入 Q1′a
    if hook == "context_budget_guard.py":
        return "MISBLOCK"  # 它只該擋扇出型；收斂型被它擋＝範圍錯
    if hook == "block_bash_on_windows.py":
        return "correct" if tool == "Bash" and re.match(r"[A-Za-z]:", cwd) else "MISBLOCK"
    if hook == "lint_powershell_command.py":
        hits = _lint_ps_hook.lint_command(cmd) if tool == "PowerShell" else []
    elif hook == "block_destructive_git.py" and bdg:
        hits = ([bdg.govwrite_hit(inp)] if tool not in ("Bash", "PowerShell") else
                bdg.destructive_git_hits(cmd, start_dir=None) + bdg.waitform_hits(
                    cmd, run_in_background=bool(inp.get("run_in_background")), tool=tool))
    else:
        return "no-oracle"
    return "correct" if any(hits) else "MISBLOCK"


def feed_diffs(pop: list[dict], limit: int) -> list[int]:
    """最近 limit 支（feed 在、且不舊於逐字稿最後一筆 usage）的 feed used 減逐字稿 used。"""
    from statusline_context_feed import context_feed_path  # 唯一的 feed 路徑實作，不另拼

    out: list[int] = []
    for p in reversed(pop):
        try:
            doc = json.loads(context_feed_path(p["sid"]).read_text(encoding="utf-8"))
            fresh = datetime.fromisoformat(doc["ts"]) >= p["usage_ts"]
            diff = _used(doc["context_window"]["current_usage"]) - p["usage"]
        except (OSError, ValueError, KeyError, TypeError):
            continue  # 無 feed／壞 feed／無 usage＝量不到，不入 N
        if fresh and doc.get("session_id") == p["sid"]:
            out.append(diff)
    return out[:limit]


def five_question(profs: list[dict], since: datetime | None, entries: set[str], prm: dict) -> None:
    """②′ 的 Q1′a／b／c、Q2′、Q3′ 在同一母體上的量測，直接印表（Q4′ 人供）。母體＝頂層逐字稿、
    entrypoint ∈ entries、≥1 個 tool_use、**起點** ≥ since（逐 session 起點，非檔案 mtime）。"""
    os.environ.setdefault("CLAUDE_PROJECT_DIR", str(_REPO_ROOT))  # govwrite 的 oracle 以它定專案根
    pop = sorted((p for p in profs if p["entry"] in entries and p["uses"]
                  and (since is None or p["start"] >= since)), key=lambda p: p["start"])
    bdg, planner = _hook_module("block_destructive_git"), re.compile(prm["planner_re"])
    cl, ex, qt = (re.compile(prm[k], re.I) for k in ("claim_re", "claim_exc_re", "quote_re"))
    blk = [(p, i, u) for p in pop for i, u in enumerate(p["uses"], 1) if u["block"]]
    ev = [{"sid": p["sid"][:8], "seq": i, "tool": u["name"], "kind": u["block"][0],
           "by": u["block"][1], "oracle": judge_block(u, p["cwd"], bdg, prm)}
          for p, i, u in blk if u["block"][0] != "non-hook"]
    mis, nor = ([e for e in ev if e["oracle"] == o] for o in ("MISBLOCK", "no-oracle"))
    claims = [(s, sup) for p in pop for n, sup, text in p["texts"] if n < 10
              for s in _sentences(qt.sub("", text)) if cl.search(s) and not ex.search(s)]
    bare = [s[:120] for s, sup in claims if not sup]
    win = pop[-prm["q1c_n"]:]
    # 前 5 個呼叫的分子只計 hook 來源（含 SDD router）的阻斷；auto-mode／人拒絕不計
    hk = [[bool(u["block"]) and u["block"][0] != "non-hook" for u in p["uses"][:5]] for p in win]
    hit5, first = sum(map(any, hk)), sum(h[0] for h in hk)
    idx = [(p["sid"][:8], next((i for i, u in enumerate(p["uses"], 1) if u["name"] in
            ("Bash", "PowerShell") and planner.search(str(u["input"].get("command")))), None),
            p["brief"]) for p in pop if len(p["uses"]) >= prm["q2_max_index"]]
    late = [r[:2] for r in idx if r[1] is None or r[1] > prm["q2_max_index"]]
    diffs = feed_diffs(pop, prm["q3_n"])

    def show(label: str, n: int, need: int, detail: str, bad: bool = False, human: bool = False):
        """FAIL 優先；其次需人工複核；樣本數不足就誠實說量不到，不寫 PASS。"""
        status = ("FAIL" if bad else "HUMAN-REVIEW" if human
                  else f"NOT-EVALUABLE({n}/{need})" if n < need else "PASS")
        print(f"  {label}  {status}  {detail}")

    other = Counter(u["block"][1] for _, _, u in blk if u["block"][0] == "non-hook")
    print(f"### ②′ 五問量測：母體 {len(pop)} 支（{sorted(entries)}・起點≥{since or '無'}）")
    show("Q1′a 誤擋", len(pop), 1, f"{len(mis)}／hook 阻斷 {len(ev)}；無 oracle {len(nor)}",
         bool(mis), bool(nor))
    show("Q1′b 宣稱≠阻斷", len(pop), 1, f"{len(bare)}／{len(claims)} {bare[:3]}", human=bool(bare))
    show("Q1′c 前5呼叫被擋", len(win), prm["q1c_n"], f"{hit5}／{len(win)}（≤{prm['q1c_gate']}）；"
         f"首呼叫被擋 {first}／{len(win)}",
         len(win) >= prm["q1c_n"] and hit5 / len(win) > prm["q1c_gate"])
    show("Q2′ 首查序號", len(idx), prm["q2_min_n"],
         f"逾期或從未 {len(late)}／{len(idx)} {late}；有簡報 {sum(r[2] for r in idx)}", bool(late))
    show("Q3′ feed 差", len(diffs), prm["q3_min_pairs"],
         f"{len(diffs)} 對；max|差|={max(map(abs, diffs), default=0)} {diffs}",
         any(abs(d) > prm["q3_tolerance_tokens"] for d in diffs))
    print("  Q4′ 各平台 --status  本檔不量（Mac 另跑 --status；Windows 人供）")
    print(f"  非 hook 阻斷（auto-mode／人拒絕，不入 Q1′）：{dict(other) or '無'}")
    print("  hook 阻斷逐筆（oracle＝HEAD 判準重放）：" + ("" if ev else "無"))
    for event in ev:
        print("   ·", json.dumps(event, ensure_ascii=False))


def protocol_status(prm: dict) -> int:
    """`--protocol-status`：協定 manifest 雜湊＋輪帳本窗口長度＋評估式。rc 恆 0（不得接閘門）。"""
    import hashlib
    man = sorted((p.relative_to(_PROTOCOL_DIR).as_posix(),
                  hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest())
                 for p in _PROTOCOL_DIR.rglob("*") if p.is_file() and p.name[0] != ".")
    sha = hashlib.sha256(json.dumps(man, ensure_ascii=False).encode("utf-8")).hexdigest()
    rows = [json.loads(ln) for ln in _LEDGER.read_text(encoding="utf-8").splitlines()
            if ln.strip()] if _LEDGER.is_file() else []
    need, run = prm["rounds_required"], 0
    for row in reversed(rows):  # 窗口＝尾端連續同 sha 的列，遇 window_reset 即止
        if row["protocol_sha256"] != rows[-1]["protocol_sha256"]:
            break
        run += 1
        if row.get("window_reset"):
            break
    ok = (run >= need and sum(len(r["new_p_le2"]) for r in rows[-need:]) <= 2
          and sum(r["p1"] for r in rows[-need:]) == 0 and not rows[-1]["new_p_le2"])
    verdict = ("PROTOCOL-CHANGED（需新列帶 window_reset:true＋理由）"
               if rows and rows[-1]["protocol_sha256"] != sha
               else f"NOT-EVALUABLE({run}/{need})" if run < need else "PASS" if ok else "FAIL")
    print(f"### ②′ 協定狀態\n  protocol_sha256={sha}（manifest {len(man)} 檔）")
    print(f"  輪帳本 {len(rows)} 列；window_len={run}；評估: {verdict}")
    return 0


def probe_selftest() -> list[str]:
    """②′ 量測自證：阻斷判準不被引文騙、不只認 Bash；宣稱句型放過疑問與否定。回失敗清單。"""
    deny, err = {"toolDenialKind": "permission-rule"}, {"is_error": True}
    hook = "PreToolUse:Write hook error: [${DIR}/_hook_launcher.py .claude/hooks/x_guard.py]: 擋"
    cases = [(({}, {"is_error": False}, hook.replace("Write", "Bash")), None),  # 引文含舊 needle
             ((deny, err, hook), ("hook", "x_guard.py")),  # Write 的 hook error（不只 Bash）
             (({}, err, hook), None)]  # 無 toolDenialKind＝一般工具錯誤
    bad = [f"block_source 判錯：{a[2][:30]}" for a, want in cases if block_source(*a) != want]
    cl, ex = (re.compile(_params()[k], re.I) for k in ("claim_re", "claim_exc_re"))
    for text, want in (("我被擋住了，無法使用工具。", 1), ("現在工具還被擋著嗎？", 0)):
        if bool(cl.search(text) and not ex.search(text)) != bool(want):
            bad.append(f"宣稱句型：{text!r} 應判 {want}")
    return bad


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project-dir", help="逐字稿目錄（覆寫 slug 推導）")
    parser.add_argument("--transcript", action="append", default=[],
                        help="直接指定一支 .jsonl（可重複）")
    parser.add_argument("--since", help="只掃 mtime >= 此 ISO 時刻的逐字稿"
                                        "（2026-08-07 或 2026-08-07T00:05:53）")
    parser.add_argument("--until", help="只掃 mtime < 此 ISO 時刻的逐字稿"
                                        "（與 --since 併用即『觀測者上線前／後』分期）")
    parser.add_argument("--record-since", dest="record_since",
                        help="**逐筆**時間切片下界（ISO）。分期比較一律用這個，"
                             "不要用 --since：後者切的是檔案 mtime，跨越分界點的長 "
                             "session 會整支落在後段（本輪實測誤差 3,284 vs 7）")
    parser.add_argument("--record-until", dest="record_until",
                        help="**逐筆**時間切片上界（ISO，不含）")
    parser.add_argument("--latest", type=int,
                        help="只掃最近改動的 N 支（每輪量測建議搭配它或 --since）")
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW,
                        help=f"宣稱往回看幾個 tool_result（預設 {DEFAULT_WINDOW}）")
    parser.add_argument("--exclude", action="append", default=[],
                        help="檔名含此子字串的逐字稿不納入量測窗（可重複）；"
                             "在 --latest 之前套用")
    parser.add_argument("--exclude-self", action="store_true",
                        help="剔除**正在跑這支腳本的那個 session**（讀環境變數 "
                             "CLAUDE_CODE_SESSION_ID）。量測者把自己算進分母時，"
                             "跑量測這個動作本身就會改變量測值")
    parser.add_argument("--exclude-sid", action="append", default=[], help="明示剔除某 session id")
    parser.add_argument("--five-question", action="store_true", help="印判準②′ 五問量測（rc 恆 0）")
    parser.add_argument("--entrypoint", default="cli,claude-vscode", help="②′ 母體 entrypoint")
    parser.add_argument("--protocol-status", action="store_true", help="印審計協定雜湊與輪帳本窗口")
    parser.add_argument("--max-claims", type=int, default=10)
    parser.add_argument("--selftest", action="store_true",
                        help="對已知正解／已知違規各數組跑 `rc-after-pipe-real`"
                             "（答案來自 pwsh 真機實測），並同時印出舊判準對同一批"
                             "語料的判定當作紅的那一半。有任何一組不符即 rc=1")
    parser.add_argument("--parity", action="store_true",
                        help="把量測窗裡每一條 unique PowerShell 指令同時餵給攔截端與"
                             "量測端，列出判定分歧（有分歧即 rc=1）")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    if args.protocol_status:
        return protocol_status(_params())
    if args.selftest:
        failures, probe_bad = rc_selftest(), probe_selftest()  # ②′ 自證另計，不灌進「新判準判錯」
        print("### `rc-after-pipe-real` 紅綠自證"
              f"（{len(_rc_real._RC_SELFTEST)} 組，答案＝pwsh 7.6.4 真機實測值）")
        print("  🔴 綠的那一半：修正後的判準對每一組都要判對。")
        print("  🔴 紅的那一半：同一批語料餵給**舊判準**（＝攔截端那支借來的函式），"
              "看它錯在哪——\n     判準沒有鑑別力時，兩欄會一模一樣。")
        old_wrong = 0
        for command, expected, measured, why in _rc_real._RC_SELFTEST:
            new_verdict = _rc_after_pipe_real(command)
            old_verdict = _rc_after_pipe(command)
            old_wrong += int(old_verdict is not expected)
            print(f"  {'✅' if new_verdict is expected else '❌'} "
                  f"實測{measured:9s} 應判={str(expected):5s} "
                  f"新={str(new_verdict):5s} 舊={str(old_verdict):5s}  {why}")
        print(f"\n  新判準判錯 {len(failures)} / {len(_rc_real._RC_SELFTEST)}；"
              f"舊判準判錯 {old_wrong} / {len(_rc_real._RC_SELFTEST)}")
        print(f"  ②′ 量測自證（阻斷判準＋宣稱句型）判錯 {len(probe_bad)} 組")
        if old_wrong == 0:
            print("  ⚠️ 舊判準一組都沒判錯 ⇒ 這批語料對「修了什麼」沒有鑑別力，"
                  "自證是空的；請補進真的會分開兩者的形態。", file=sys.stderr)
        for line in failures + probe_bad:
            print(f"  ❌ {line}", file=sys.stderr)
        # 舊判準零錯誤也算紅：那表示這份語料證明不了本輪修了任何東西。
        return 1 if (failures or probe_bad or old_wrong == 0) else 0

    exclude = list(args.exclude) + args.exclude_sid
    if args.exclude_self:
        own = os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip()
        if own:
            exclude.append(own)
            print(f"ℹ️ --exclude-self 剔除 {own}（subagent 內＝父窗 id）", file=sys.stderr)
        else:
            # fail-loud 而不是靜默略過：以為排除了、其實沒排除，正是本旗標要治的病。
            print("⚠️ --exclude-self：環境變數 CLAUDE_CODE_SESSION_ID 是空的 ⇒ "
                  "無法辨識自己這一支，本次未剔除任何東西", file=sys.stderr)

    if args.transcript:
        candidates = [Path(p) for p in args.transcript]
    else:
        base = Path(args.project_dir) if args.project_dir else \
            project_transcript_dir(_REPO_ROOT)
        candidates = sorted(base.glob("*.jsonl")) if base.is_dir() else []

    paths = select_paths(candidates, args.since, args.until, args.latest, exclude)

    def _iso(value: str | None) -> datetime | None:
        if not value:
            return None
        parsed = datetime.fromisoformat(value)
        # naive 視為本機時區，否則與逐字稿的帶時區時戳無法比較（TypeError）。
        return parsed if parsed.tzinfo else parsed.astimezone()

    if args.five_question:
        entries = {e.strip() for e in args.entrypoint.split(",") if e.strip()}
        five_question([session_profile(p) for p in paths], _iso(args.since), entries, _params())
        return 0
    rec_since, rec_until = _iso(args.record_since), _iso(args.record_until)
    results = [scan_transcript(p, args.window, rec_since, rec_until) for p in paths]
    summary = aggregate(results)
    summary["criterion_fingerprint"] = criterion_fingerprint()
    summary["record_slice"] = [args.record_since, args.record_until]
    verdict = collapse_verdict(summary)

    commands = powershell_commands(paths) if args.parity else []
    divergences = parity_divergences(commands) if args.parity else []
    if args.parity:
        summary["parity_commands"] = len(commands)
        summary["parity_divergences"] = len(divergences)

    if args.as_json:
        payload = {"sessions": results, "summary": summary,
                   "collapse_verdict": verdict}
        if args.parity:
            payload["parity"] = divergences
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_report(results, summary, args.max_claims)
        if args.parity:
            print(f"\n### 攔截端 × 量測端對拍（{len(commands)} 條 unique 指令）")
            print(f"  判定分歧 {len(divergences)} 筆")
            for row in divergences[:args.max_claims]:
                print(f"    · hook={row['hook']} probe={row['probe']}")
                print(f"      {row['command'][:200]}")
        if verdict:
            print(f"\n❌ {verdict}")

    return 1 if (verdict or divergences) else 0


if __name__ == "__main__":
    sys.exit(main())
