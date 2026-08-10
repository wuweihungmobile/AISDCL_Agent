#!/usr/bin/env python3
"""R83／包 W2-B：「示範指令只在單一平台成立」機械守門 ＋ PG skip 解法的可發現性錨。

═══════════════════════════════════════════════════════════════════════════
WHY（本檔為何存在——三筆當回合實測的缺陷，全部長在「指引」上）
═══════════════════════════════════════════════════════════════════════════

1. **DSN 守衛的修法只印 PowerShell 形態**（本輪主缺陷）。
   `AutoClaude/tests/conftest.py::pg_dsn_problems` 修前逐字印
   `$env:AUTOCLAUDE_TEST_PG_DSN = '…'`。`$env:` 是 PowerShell 專屬語法，bash/zsh 照抄
   會把它展開成空字串、再把 `=` 當成指令名 ⇒ 得到一個與 DSN 毫無關係的錯誤。難看之處
   在於**它長在一支專門用來「把人導向正解」的訊息上**：那則訊息存在的全部理由就是省下
   使用者從 SQLAlchemy 錯誤反推回「我少打了四個字」那段路，而它自己在 mac 上又製造了
   一段同型的反推。同檔另有 2 處、姊妹檔 `tests/perf/test_pgvector_recall_perf.py` 2 處、
   `AutoClaude/tools/setup_pg_runtime_role.py` 1 處，全部同形態（本輪一併修）。

2. **`timeout <n>` 在 macOS 不存在**（GNU coreutils；BSD 沒有）。當回合實測：
   `which timeout` → `timeout not found`、rc=1。repo 已有
   `tools/tests/test_bash32_compat.py` 守 `.sh` 與 workflow inline `run:` 這兩個面，
   但**文件與錯誤訊息裡的示範指令一個字都沒人看**。

3. 兩者的共同形態＝**單平台指引不外推**，而它發生的那個平面（活文件的散文與
   Python 的訊息字串）此前零判準。

═══════════════════════════════════════════════════════════════════════════
判準（誠實劃界：掃什麼、怎麼判、故意不判什麼）
═══════════════════════════════════════════════════════════════════════════

**掃描面（兩個，都明確列舉，不是「全 repo」）**

  A. **活文件 `.md`**＝`tools/tests/test_doc_env_prefix_platform_parity_r60.py::_LIVE_DOCS`
     **直接 import 該常數**，不另抄一份名冊——那一支守的是同一族缺陷的**反方向**
     （bash 前綴必附 PowerShell 對照），兩支共用同一個名冊才不會出現「一邊擴了、
     另一邊沒擴」的漂移。名冊模組不可載入時 fail-loud（縮面必須出聲）。

  B. **Python 的使用者可見指引字串**＝tracked `*.py`，限
     `AutoClaude/` 與根層 `tools/` 兩棵，**且**該字串字面值帶指引措辭
     （`修法`／`配方`／`跑法`／`用法`／`設定方式`／`請改`／`請用`／`改用`／`本機執行`）。
     - 刻意**排除 `tools/tests/`**：本 repo 的平台形態**偵測器**都住在這裡
       （本檔、`test_platform_neutral_paths.py`、`test_ps51_compat.py`、`test_dev_start.py`…），
       它們的 pattern 表與合成 fixture **必然**含單平台形態，判它們就是製造假紅。
       當回合實測：不排除時 `tools/tests/` 命中 1 筆（`test_bash_probe_spec_contract.py`
       的 `export PATH=` — 那是在描述 bash 啟動器的自我注入行為，不是給人照抄的指令）。
     - 刻意**排除 `AISDLC_SDD/`**：Copy-on-Evolve 凍結面（v0.01~v0.29 禁改）。當回合實測
       那棵樹有 90 支檔／約 300 筆 `timeout <n>`（FSM 測試資料），全判紅＝把凍結政策打破。
     - 指引措辭是**必要條件不是充分條件**：純英文寫的新訊息不會被抓到（見末段「抓不到什麼」）。

**三個形態族（都是「在另一個平台會壞掉」，不是風格偏好）**

  · `_WINDOWS_ONLY`：`$env:NAME = …`（**設值**形態）。刻意不判 `$env:NAME` 的**讀取**
    ——讀取常出現在「檢查 Windows 專屬載具」這種正當的單平台脈絡裡
    （如 `tools/lib/hook_wiring.py` 的 `Test-Path (Join-Path $env:CLAUDE_PROJECT_DIR …)`），
    判它會製造要逐筆辯護的假紅。本包的缺陷全部是**設值**形態。
  · `_POSIX_ONLY`：`export NAME=`、`open -a <App>`（後者 macOS 專屬）。
  · `_GNU_ONLY`：`timeout <n>`／`readlink -f`／`sed -i`／`grep -P`／`date -d`／`stat -c`／
    `xargs -r`——這一族**兩個平台都不成立**（macOS 是 BSD userland、PowerShell 更不用說）
    ⇒ **沒有配對可言，一律違規**。刻意要求帶運算元（`date -d <值>`），因為
    裸提一個旗標名（`` `date -d` ``）是**引述**不是示範指令——根 CLAUDE.md 的欠債表就是
    這樣寫的，判它會讓這道鎖一出生就對一份我改不動的檔轉紅。

**判定單位與規則**

  · `.md` 圍欄（fence）：**info string 就是平台宣告**。
      - PowerShell 家族標籤（powershell/pwsh/ps1/ps/posh）→ 允許 `_WINDOWS_ONLY`；
        出現 `_POSIX_ONLY` 即違規。
      - POSIX 家族標籤（bash/sh/zsh/shell/console）→ 反之。
      - **未標註語言**的圍欄 → 視同散文，走下面的「兩個平台標籤」規則。
      - 非 shell 語言（python/yaml/json/text…）→ 略過（不是 shell 指令指引）。
  · `.md` 散文：判定單位＝**段落**（連續非空行；blockquote 的 `>` 空行視為分隔）。
    表格因為沒有空行，整張表算一個段落——刻意接受這個寬鬆度：逐列判會把
    「症狀欄引述壞形態、解法欄給正確形態」這種正確寫法判紅。
  · Python：判定單位＝**該字串字面值本身**（f-string 以 `ast.JoinedStr` 還原後併看）。
  · 規則：單位內出現 `_WINDOWS_ONLY` 或 `_POSIX_ONLY` 時，該單位必須**同時**提到
    一個 Windows 平台標籤與一個 POSIX 平台標籤（`PowerShell`/`pwsh`/`Windows`
    ↔ `bash`/`zsh`/`macOS`/`Linux`/`POSIX`）。
    **為何判「標籤」而不是「有沒有對面那一條指令」**：兩平台的對應寫法往往不是同一個
    指令族（`open -a Docker` ↔ 「用 GUI 開 Docker Desktop」根本不是指令），硬要求
    token 級對照會逼人寫出假的對照。要求「說清楚這段是給誰用的、另一邊怎麼辦」
    才是真正要的東西。

**存量與門檻**：當回合實測，A 面（`_LIVE_DOCS` 10 份）與 B 面在本包修完後**存量皆為 0**
⇒ 採**零容忍**，不設棘輪。本 repo 已有判例：一次判 148 筆假紅的鎖活不過一輪，所以
上面每一條收窄（只判設值形態／要求運算元／段落級／排除兩棵樹）都是先實測再決定的。

**豁免出口**：違規行**行尾**加 `# xplatcmd-ok: <WHY>`（`.md` 建議用
`<!-- xplatcmd-ok: WHY -->`）。WHY 必填，留空不具豁免力（同 `bash4-ok:`／`encoding-ok:`／
`envprefix-ok:` 既有慣例）。Python 側接受標記出現在字串**所在行區間或其前一行的註解**上。
正當用途：確實只在單一平台成立、且該脈絡本身就是平台專屬的東西（例：教人怎麼查
Windows hook 載具在不在、schtasks 的 Action 字串）。**stale 自檢**：帶標記卻壓不住任何
違規的行一律 fail-loud 指名要求移除——豁免清單腐化與沒有豁免同樣危險。

**結構上抓不到什麼（不要把本檔讀成完整性保證）**
  · 只認上面列的形態族。`Get-ChildItem`/`Select-String`/`sudo`/`brew`/`launchctl` 等
    其他單平台工具**不在族內**（未實測存量，貿然加會製造假紅；要加請先量再加）。
  · Python 側靠「指引措辭」認人 ⇒ **純英文**或用別種措辭寫的新訊息看不到。
  · `.md` 只掃 `_LIVE_DOCS` 名冊；帳本／improving 系列／`AISDLC_SDD/**` 各版模板不在內。
  · 判「有沒有提到兩個平台」抓得到「完全沒交代另一邊」，抓不到「交代了但寫錯」。
  · **執行期**才成立的指令（playbook 內容、使用者輸入）完全不在靜態掃描面上。

執行：python3 -m unittest tools.tests.test_skip_discoverability_r83 -v
"""
from __future__ import annotations

import ast
import importlib.util
import re
import subprocess
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[1]

_OK_MARKER = "xplatcmd-ok:"

# ── 形態族 ────────────────────────────────────────────────────────────────
_WINDOWS_ONLY: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\$env:[A-Za-z_][A-Za-z0-9_]*\s*=(?!=)"),
     "$env:X = …（設定環境變數；PowerShell 專屬，bash/zsh 照抄無效）"),
]
_POSIX_ONLY: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?<![\w-])export\s+[A-Za-z_][A-Za-z0-9_]*="),
     "export X=…（POSIX shell 專屬；PowerShell 沒有這個指令語意）"),
    (re.compile(r"(?<![\w-])open\s+-a\s+\S"),
     "open -a <App>（macOS 專屬）"),
]
#: 兩個平台都不成立 ⇒ 無配對可言，一律違規。全部要求帶運算元（裸提旗標名是引述、不是示範）。
_GNU_ONLY: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?<![\w-])timeout\s+\d"),
     "timeout <n>（GNU coreutils；macOS BSD userland 沒有這支，實測 command not found）"),
    (re.compile(r"(?<![\w-])readlink\s+-f\s+\S"), "readlink -f（BSD readlink 不支援）"),
    # `sed -i ''` 刻意**不算**本族：那是 BSD **要求**的寫法（-i 必須帶字尾引數），
    # 不是「GNU-only」。實測若不排除，`tools/run_shellcheck.py` 檔頭那句「shellcheck
    # 看不到 `sed -i ''`／`readlink -f` 這類執行期差異」會被判紅——那是在**列舉**分歧
    # 形態、不是示範指令。（BSD-only 那一族不在本檔射程，見檔頭「抓不到什麼」）
    (re.compile(r"(?<![\w-])sed\s+-i\s+(?!(?:''|\"\"))\S"), "sed -i <script>（GNU-only；BSD 的 -i 必須帶字尾引數）"),
    (re.compile(r"(?<![\w-])grep\s+-[A-Za-z]*P\s+\S"), "grep -P（BSD grep 無 PCRE）"),
    (re.compile(r"(?<![\w-])date\s+-d\s+\S"), "date -d（BSD date 語意不同）"),
    (re.compile(r"(?<![\w-])stat\s+-c\s+\S"), "stat -c（BSD stat 用 -f）"),
    (re.compile(r"(?<![\w-])xargs\s+-r\b"), "xargs -r（BSD xargs 無此旗標）"),
]

_WIN_LABEL = re.compile(r"powershell|pwsh|windows", re.IGNORECASE)
_POSIX_LABEL = re.compile(r"\bbash\b|\bzsh\b|macos|linux|posix|mac/linux", re.IGNORECASE)

_PS_FENCE_TAGS = {"powershell", "pwsh", "ps1", "ps", "posh"}
_SH_FENCE_TAGS = {"bash", "sh", "zsh", "shell", "console"}

_FENCE_RE = re.compile(r"^[>\s]*(?:```|~~~)(?P<lang>[A-Za-z0-9_+-]*)\s*$")
_BLANK_RE = re.compile(r"^[>\s]*$")
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")

#: Python 側「這是說給使用者聽的指引」的認人條件（必要條件，非充分）。
_GUIDANCE_WORDS = re.compile(
    # `請設定` 是本輪**實測補上**的：`AutoClaude/alembic/env.py` 缺 DSN 時的 fail-loud
    # 訊息逐字寫「請設定環境變數 …／export …」，是使用者撞牆時唯一的指路，卻不含上面
    # 任何一個詞 ⇒ 整支從掃描面漏掉。加詞的判準是「有沒有實際漏掉一個真站點」，不是憑想像加。
    #
    # 🔴 `使用` 是**獨立驗證階段**依同一條判準補上的（R83／W2-B 複驗）：本檔落地當回合，
    # 把過濾器整個拿掉重掃全掃描面，全庫只多出 **4** 筆命中，逐筆看過之後——
    #   · 2 筆是**真站點**，且與本包已修的那一族逐字同形（`AutoClaude/scripts/
    #     migrate_file_to_pg.py` 的「使用：」與 `AutoClaude/tools/probe_minimax_embedding.py`
    #     的「使用方式：」，兩者都只給 `export …`，Windows 讀者無路可走）；
    #   · 2 筆是假紅（`test_embedder_contract.py` 在**描述**「開發者 shell export … 時本測試
    #     偽 fail」這個情境、`test_run_local_nightly_static.py` 拿 `$env:…` 字面去 index
    #     ps1 內容），兩者都**不含**「使用」二字。
    # ⇒ 加 `使用` 這一個詞恰好收下那 2 筆真站點、一筆假紅都不帶進來（實測差集驗證過）。
    # 這正是本檔自己寫的判準：**加詞要靠「實際漏掉一個真站點」，不是靠想像**；而只做合成
    # 自證不會發現它——過濾器是**必要條件**，漏掉的東西結構上不會出現在任何一次綠燈裡。
    r"修法|配方|跑法|用法|設定方式|請設定|請改|請用|改用|本機執行|一行可貼|使用"
)

#: Python 掃描面：兩棵樹，各自扣掉一個明說理由的子樹。
_PY_ROOTS = ("AutoClaude/", "tools/")
_PY_EXCLUDE_PREFIXES = (
    # 偵測器自己的形態表與合成 fixture 住在這裡；判它們就是製造假紅（見檔頭）
    "tools/tests/",
)


# ═══════════════════════════════════════════════════════════════════════════
# 純判定函式（無 I/O，供合成注入自證直接呼叫）
# ═══════════════════════════════════════════════════════════════════════════
def _hits(text: str, family: list[tuple[re.Pattern[str], str]]) -> list[str]:
    return [desc for pat, desc in family if pat.search(text)]


def _mentions_both_platforms(unit: str) -> bool:
    return bool(_WIN_LABEL.search(unit)) and bool(_POSIX_LABEL.search(unit))


def unit_problems(segment: str, unit: str, *, declared: str | None = None) -> list[str]:
    """判一個「示範指令片段」在其判定單位下有沒有問題。

    `segment`＝要判的那一小段（fence 的一行／inline code span／字串字面值）；
    `unit`＝配對範圍（fence 全文／段落／同一個字串字面值）；
    `declared`＝平台宣告，`"win"`／`"posix"`／`None`（未宣告 ⇒ 走「兩個平台標籤」規則）。
    """
    problems: list[str] = []
    for desc in _hits(segment, _GNU_ONLY):
        problems.append(f"{desc} ⇒ 兩個平台都不成立，沒有配對可言")
    win = _hits(segment, _WINDOWS_ONLY)
    posix = _hits(segment, _POSIX_ONLY)
    if declared == "win":
        problems += [f"{d} ⇒ 寫在已宣告 PowerShell 的區塊裡" for d in posix]
    elif declared == "posix":
        problems += [f"{d} ⇒ 寫在已宣告 POSIX shell 的區塊裡" for d in win]
    else:
        if (win or posix) and not _mentions_both_platforms(unit):
            for d in win + posix:
                problems.append(
                    f"{d} ⇒ 未宣告平台、且判定單位內沒有同時提到 Windows 與 POSIX 兩側"
                    "（照抄的人有一半在另一個平台上）"
                )
    return problems


def _marked(line: str) -> bool:
    """行內是否帶**有 WHY** 的豁免標記。"""
    idx = line.find(_OK_MARKER)
    if idx < 0:
        return False
    return bool(line[idx + len(_OK_MARKER):].strip(" \t-#>*`<!->\n"))


# ═══════════════════════════════════════════════════════════════════════════
# Markdown 掃描
# ═══════════════════════════════════════════════════════════════════════════
def scan_markdown(text: str) -> tuple[list[tuple[int, str]], set[int]]:
    """回傳 (違規清單[(行號, 說明)], 有效壓下違規的標記行號集合)。行號 1-based。"""
    lines = text.splitlines()
    # ① 標出每一行的所屬區塊
    kinds: list[str | None] = []          # None=prose；否則是 fence 語言（"" 代表未標註）
    fence_id: list[int] = []
    cur, fid, counter = None, -1, 0
    for raw in lines:
        m = _FENCE_RE.match(raw)
        if m:
            if cur is None:
                counter += 1
                cur, fid = m.group("lang").lower(), counter
            else:
                cur, fid = None, -1
            kinds.append("__FENCE_MARK__")
            fence_id.append(-1)
            continue
        kinds.append(cur)
        fence_id.append(fid)
    # ② fence 全文（配對單位）
    fence_text: dict[int, str] = {}
    for idx, raw in enumerate(lines):
        if fence_id[idx] > 0:
            fence_text[fence_id[idx]] = fence_text.get(fence_id[idx], "") + raw + "\n"
    # ③ 段落切分（僅 prose）
    para_of = [-1] * len(lines)
    pid, prev_blank = 0, True
    for idx, raw in enumerate(lines):
        if kinds[idx] is not None:
            prev_blank = True
            continue
        if _BLANK_RE.match(raw):
            prev_blank = True
            continue
        if prev_blank:
            pid += 1
            prev_blank = False
        para_of[idx] = pid
    para_text: dict[int, str] = {}
    for idx, raw in enumerate(lines):
        if para_of[idx] > 0:
            para_text[para_of[idx]] = para_text.get(para_of[idx], "") + raw + "\n"

    violations: list[tuple[int, str]] = []
    live_markers: set[int] = set()
    for idx, raw in enumerate(lines):
        kind = kinds[idx]
        if kind == "__FENCE_MARK__":
            continue
        if kind is None:
            segments = _INLINE_CODE_RE.findall(raw)
            unit = para_text.get(para_of[idx], raw)
            declared = None
        else:
            if kind and kind not in _PS_FENCE_TAGS and kind not in _SH_FENCE_TAGS:
                continue          # 非 shell 語言的圍欄不納管
            segments = [raw]
            unit = fence_text.get(fence_id[idx], raw)
            declared = ("win" if kind in _PS_FENCE_TAGS
                        else "posix" if kind in _SH_FENCE_TAGS else None)
        found: list[str] = []
        for seg in segments:
            found += unit_problems(seg, unit, declared=declared)
        if not found:
            continue
        if _marked(raw):
            live_markers.add(idx + 1)
            continue
        for desc in found:
            violations.append((idx + 1, desc))
    return violations, live_markers


# ═══════════════════════════════════════════════════════════════════════════
# Python 掃描
# ═══════════════════════════════════════════════════════════════════════════
#: `str.format()` 樣板的佔位符。**非補不可**：本輪的真實修法就是把配方抽成 `.format()`
#: 樣板（`AutoClaude/tests/conftest.py::_ENV_RECIPE_TEMPLATE`），若不正規化，
#: `$env:{var} = …` 的 `{` 會讓 `$env:` 後面接不到識別字 ⇒ **整族樣板從判準中間漏掉**，
#: 而那正是修法本身會採用的寫法（實測：紅綠自證的注入樣本因此第一次沒轉紅）。
_FORMAT_PLACEHOLDER = re.compile(
    r"\{[A-Za-z_][A-Za-z0-9_]*(?:![rsa])?(?::[^{}]*)?\}|\{\}"
)


def _literal_text(node: ast.AST) -> str | None:
    """把 `Constant`／`JoinedStr` 還原成可掃描的文字（插值與 `.format()` 佔位符正規化）。"""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return _FORMAT_PLACEHOLDER.sub("EXPR", node.value)
    if isinstance(node, ast.JoinedStr):
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                parts.append(v.value)
            else:
                # 佔位符刻意用**識別字形態**（不是 `<expr>`）：真實缺陷長成
                # `f"$env:{var} = '{value}'"`，插值處正好是變數名的位置——用尖括號當
                # 佔位符會讓 `$env:` 後面接不到識別字，整族 f-string 訊息從判準中間漏掉。
                parts.append("EXPR")
        return _FORMAT_PLACEHOLDER.sub("EXPR", "".join(parts))
    return None


def scan_python(source: str) -> tuple[list[tuple[int, str]], set[int]]:
    """回傳 (違規清單[(行號, 說明)], 有效壓下違規的標記行號集合)。"""
    tree = ast.parse(source)
    lines = source.splitlines()
    violations: list[tuple[int, str]] = []
    live_markers: set[int] = set()
    for node in ast.walk(tree):
        text = _literal_text(node)
        if text is None or not _GUIDANCE_WORDS.search(text):
            continue
        found = unit_problems(text, text, declared=None)
        if not found:
            continue
        start = getattr(node, "lineno", 1)
        end = getattr(node, "end_lineno", start) or start
        # 標記可寫在字串所在行區間內，或緊接其上的註解行
        window = range(max(1, start - 1), min(len(lines), end) + 1)
        marker_line = next((n for n in window if _marked(lines[n - 1])), None)
        if marker_line is not None:
            live_markers.add(marker_line)
            continue
        for desc in found:
            violations.append((start, desc))
    return violations, live_markers


# ═══════════════════════════════════════════════════════════════════════════
# 掃描面解析
# ═══════════════════════════════════════════════════════════════════════════
def _live_docs() -> list[str]:
    """直接取用姊妹鎖的名冊常數（SSOT），載不到即 fail-loud。"""
    sibling = _TESTS_DIR / "test_doc_env_prefix_platform_parity_r60.py"
    if not sibling.is_file():
        raise AssertionError(
            f"名冊 SSOT 不見了：{sibling}——本檔的 `.md` 掃描面來自它的 `_LIVE_DOCS`；"
            "缺席時**不得**退回一份自抄的清單（那正是「同一份知識住兩個家」）"
        )
    spec = importlib.util.spec_from_file_location("_xplat_live_docs_ssot", sibling)
    assert spec is not None and spec.loader is not None, sibling
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    docs = list(getattr(module, "_LIVE_DOCS"))
    assert docs, "`_LIVE_DOCS` 是空的 ⇒ 掃描面靜默縮成 0"
    return docs


def _tracked_python_files() -> list[str]:
    # `-c core.quotepath=false` ＋ `-z`：非 ASCII 路徑不得被 C-quote（本 repo 630 條非 ASCII
    # tracked 路徑，見鐵律三「git 路徑列舉」那一列）。`encoding=`／`errors=` 必填——`text=True`
    # 單獨用會走本機 locale 編碼，Windows 的 cp950 讀不到這批路徑（`tools/tests/
    # test_subprocess_encoding_hygiene.py` 守這一條，本檔落地當回合就被它抓到過一次）。
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files", "-z", "*.py"],
        cwd=_REPO_ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=True,
    ).stdout
    rels = [f for f in out.split("\0") if f]
    keep = [
        r for r in rels
        if r.startswith(_PY_ROOTS) and not r.startswith(_PY_EXCLUDE_PREFIXES)
    ]
    return keep


# ═══════════════════════════════════════════════════════════════════════════
# ① 活文件（.md）
# ═══════════════════════════════════════════════════════════════════════════
class TestLiveDocsCommandsWorkOnBothPlatforms(unittest.TestCase):
    """活文件裡的示範指令不得只在單一平台成立。

    Rule 9（測試驗證意圖）：本類守的不是「文字長什麼樣」，而是
    **「照抄這份文件的人有一半在另一個平台上」這件事會不會再度靜默發生」**。
    """

    def test_live_docs_have_no_single_platform_demo_commands(self) -> None:
        problems: list[str] = []
        for rel in _live_docs():
            path = _REPO_ROOT / rel
            self.assertTrue(path.is_file(), f"名冊成員缺席：{rel}（改名/搬移須同步名冊）")
            violations, _ = scan_markdown(path.read_text(encoding="utf-8"))
            problems += [f"{rel}:{line} {desc}" for line, desc in violations]
        self.assertEqual(
            [], problems,
            "活文件的示範指令只在單一平台成立：\n  " + "\n  ".join(problems)
            + f"\n修法：補上另一個平台的寫法並在同一段落／圍欄裡標明平台；"
            f"確實只可能單平台時於該行行尾加 `{_OK_MARKER} <WHY>`（WHY 必填）",
        )

    def test_exemption_markers_are_not_stale(self) -> None:
        """帶標記卻壓不住任何違規 → fail-loud（豁免清單腐化與沒有豁免同樣危險）。"""
        stale: list[str] = []
        for rel in _live_docs():
            text = (_REPO_ROOT / rel).read_text(encoding="utf-8")
            _, live = scan_markdown(text)
            for n, raw in enumerate(text.splitlines(), 1):
                if _OK_MARKER in raw and n not in live:
                    stale.append(f"{rel}:{n}")
        self.assertEqual([], stale, f"陳舊的 `{_OK_MARKER}` 標記（請移除）：{stale}")


# ═══════════════════════════════════════════════════════════════════════════
# ② 使用者可見的 Python 指引字串
# ═══════════════════════════════════════════════════════════════════════════
class TestUserFacingMessagesWorkOnBothPlatforms(unittest.TestCase):
    """會印給使用者看的指引字串同樣不得只在單一平台成立。

    立案的實測依據：`AutoClaude/tests/conftest.py` 的 DSN 修法訊息——一支
    **專門用來把人導向正解**的訊息，自己只印 PowerShell 形態（R83 修）。
    """

    def test_guidance_strings_cover_both_platforms(self) -> None:
        problems: list[str] = []
        for rel in _tracked_python_files():
            path = _REPO_ROOT / rel
            try:
                source = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            try:
                violations, _ = scan_python(source)
            except SyntaxError:
                continue
            problems += [f"{rel}:{line} {desc}" for line, desc in violations]
        self.assertEqual(
            [], problems,
            "使用者可見的指引字串只在單一平台成立：\n  " + "\n  ".join(problems)
            + f"\n修法：同一則訊息把兩個平台的寫法都印出來並標明平台"
            f"（參考 `AutoClaude/tests/conftest.py::two_platform_env_recipe`）；"
            f"確實只可能單平台時於字串所在行區間或其上一行加 `# {_OK_MARKER} <WHY>`",
        )

    def test_python_exemption_markers_are_not_stale(self) -> None:
        stale: list[str] = []
        for rel in _tracked_python_files():
            path = _REPO_ROOT / rel
            try:
                source = path.read_text(encoding="utf-8")
                _, live = scan_python(source)
            except (OSError, UnicodeDecodeError, SyntaxError):
                continue
            for n, raw in enumerate(source.splitlines(), 1):
                if _OK_MARKER in raw and n not in live:
                    stale.append(f"{rel}:{n}")
        self.assertEqual([], stale, f"陳舊的 `{_OK_MARKER}` 標記（請移除）：{stale}")

    def test_scan_surface_is_not_silently_empty(self) -> None:
        """掃描面塌成 0 ＝靜默縮面；下限刻意設在遠低於實測值處（實測 >1000 支）。"""
        files = _tracked_python_files()
        self.assertGreater(
            len(files), 200,
            f"Python 掃描面只剩 {len(files)} 支 ⇒ `git ls-files` 或前綴過濾壞了，這道鎖已恆綠",
        )


# ═══════════════════════════════════════════════════════════════════════════
# ③ 合成注入紅綠自證（判準真的有鑑別力，不是恆綠）
# ═══════════════════════════════════════════════════════════════════════════
class TestDetectorRedGreenSelfProof(unittest.TestCase):
    def test_powershell_only_recipe_in_untagged_context_is_caught(self) -> None:
        bad = "修法：$env:AUTOCLAUDE_TEST_PG_DSN = 'postgresql+asyncpg://x'"
        self.assertTrue(unit_problems(bad, bad), "PowerShell 單邊配方沒被抓到 ⇒ 本鎖無鑑別力")

    def test_the_same_recipe_with_both_platforms_is_green(self) -> None:
        good = (
            "修法（兩平台）：\n"
            "  PowerShell：  $env:AUTOCLAUDE_TEST_PG_DSN = 'postgresql+asyncpg://x'\n"
            "  bash / zsh：  export AUTOCLAUDE_TEST_PG_DSN='postgresql+asyncpg://x'"
        )
        self.assertEqual([], unit_problems(good, good))

    def test_posix_only_recipe_is_caught_too(self) -> None:
        """反方向同樣要抓——只補一邊等於把缺陷換個方向留著。"""
        bad = "用法：export SD07_REAL_PG_E2E_ENABLED=true"
        self.assertTrue(unit_problems(bad, bad))

    def test_gnu_only_command_is_always_red_even_when_both_platforms_named(self) -> None:
        """`timeout <n>` 在 macOS 與 PowerShell 都不成立 ⇒ 提到兩個平台也救不了它。"""
        text = "用法（Windows PowerShell 與 macOS bash 皆同）：timeout 900 python -m pytest"
        problems = unit_problems(text, text)
        self.assertTrue(any("timeout" in p for p in problems), problems)

    def test_bare_flag_mention_is_not_a_demo_command(self) -> None:
        """裸提旗標名是**引述**不是示範——判它會對一堆欠債登記表誤殺（見檔頭）。"""
        self.assertEqual([], unit_problems("今天還有 3 筆 date -d", "date -d 用法"))

    def test_declared_fence_language_is_the_platform_declaration(self) -> None:
        line_ps = "$env:PYTHONUTF8 = '1'; lint-imports"
        self.assertEqual([], unit_problems(line_ps, line_ps, declared="win"))
        self.assertTrue(unit_problems(line_ps, line_ps, declared="posix"),
                        "bash 圍欄裡的 PowerShell 語法必須紅")
        line_sh = "export PYTHONUTF8=1"
        self.assertEqual([], unit_problems(line_sh, line_sh, declared="posix"))
        self.assertTrue(unit_problems(line_sh, line_sh, declared="win"))

    def test_markdown_scanner_catches_injected_violation_and_marker_suppresses(self) -> None:
        doc = (
            "# t\n\n"
            "設定方式：`$env:FOO = '1'`\n\n"
            "```bash\nopen -a Docker\n```\n"
        )
        violations, _ = scan_markdown(doc)
        self.assertTrue(violations, "散文裡的 PowerShell 單邊指令沒被抓到")
        self.assertTrue(all(v[0] == 3 for v in violations), violations)

        marked = doc.replace(
            "設定方式：`$env:FOO = '1'`",
            "設定方式：`$env:FOO = '1'` <!-- xplatcmd-ok: 合成樣本 -->",
        )
        violations2, live = scan_markdown(marked)
        self.assertEqual([], violations2)
        self.assertIn(3, live)

    def test_markdown_marker_without_why_has_no_power(self) -> None:
        doc = "# t\n\n設定方式：`$env:FOO = '1'` <!-- xplatcmd-ok: -->\n"
        violations, live = scan_markdown(doc)
        self.assertTrue(violations, "空 WHY 的標記不得具豁免力")
        self.assertEqual(set(), live)

    def test_markdown_paragraph_is_the_pairing_unit(self) -> None:
        """對照寫在**同一段落**的另一行也算數（表格與多行段落的實況）。"""
        doc = (
            "# t\n\n"
            "Windows 上要寫 `$env:FOO = '1'`；\n"
            "在 macOS 的 bash / zsh 上則是 `export FOO=1`。\n"
        )
        violations, _ = scan_markdown(doc)
        self.assertEqual([], violations, violations)

        split = doc.replace("；\n", "；\n\n")   # 拆成兩段 ⇒ 第一段只剩單邊
        violations2, _ = scan_markdown(split)
        self.assertTrue(violations2, "段落一拆開就該紅（否則配對單位形同虛設）")

    def test_python_scanner_catches_injected_violation_and_marker_suppresses(self) -> None:
        src = 'REASON = "配方：$env:PG_REAL_ENABLED = \'1\'"\n'
        violations, _ = scan_python(src)
        self.assertTrue(violations, "Python 訊息字串裡的單邊配方沒被抓到")

        marked = "# xplatcmd-ok: 合成樣本\n" + src
        violations2, live = scan_python(marked)
        self.assertEqual([], violations2)
        self.assertEqual({1}, live)

    def test_python_scanner_reassembles_fstrings(self) -> None:
        """f-string 的字面段分屬多個 AST 節點，不還原就會讓判準從中間漏掉。"""
        src = 'X = f"修法：$env:{name} = \'{value}\'"\n'
        violations, _ = scan_python(src)
        self.assertTrue(violations, "f-string 沒被還原 ⇒ 整族 f-string 訊息在掃描面外")

    def test_python_scanner_normalises_format_templates(self) -> None:
        """`.format()` 樣板的 `{var}` 不正規化，整族樣板就從判準中間漏掉。

        這一支不是假想：本輪的修法本身就是把配方抽成 `.format()` 樣板，第一版偵測器
        對它零命中（合成注入沒轉紅才發現）。修好之後注入舊形態立刻紅。
        """
        bad = 'T = "     修法：$env:{var} = \'{value}\'"\n'
        self.assertTrue(scan_python(bad)[0], "`.format()` 樣板沒被正規化 ⇒ 判準有結構性盲區")
        good = (
            'T = ("     PowerShell：  $env:{var} = \'{value}\'\\n"\n'
            '     "     bash / zsh：  export {var}=\'{value}\'")\n'
        )
        self.assertEqual([], scan_python(good)[0])

    def test_usage_wording_is_in_the_vocabulary_and_costs_no_false_red(self) -> None:
        """`使用`／`使用方式` 這種措辭必須認得——漏掉它會讓整族「使用：」docstring 隱形。

        Rule 9：本支守的不是關鍵詞表長什麼樣，而是**「過濾器是必要條件，被它擋掉的東西
        結構上永遠不會出現在任何一次綠燈裡」**這個失效模式。R83 複驗實測：把過濾器拿掉
        重掃全掃描面只多 4 筆，其中 2 筆是與本包同族的真站點（`migrate_file_to_pg.py`、
        `probe_minimax_embedding.py`），2 筆是假紅且都不含「使用」二字 ⇒ 加這一個詞是
        零假紅的淨收斂。下面兩組樣本就是那四筆的最小形態。
        """
        real = 'D = """一次性工具。\n\n使用：\n  export AUTOCLAUDE_DB_DSN="postgresql://x"\n"""\n'
        self.assertTrue(scan_python(real)[0], "「使用：」形態的單邊指引沒被抓到")

        # 假紅的兩種形態：①在**描述**別人的 shell 行為；②拿字面去 index 檔案內容。
        narrating = 'D = """hermetic：開發者 shell export TEI_DIM=512 時本測試偽 fail。"""\n'
        self.assertEqual([], scan_python(narrating)[0], "描述情境被誤判成示範指令")
        indexing = 'i = ps1.index("$env:AUTOCLAUDE_DB_DSN = $asyncDsn")\n'
        self.assertEqual([], scan_python(indexing)[0], "字面索引被誤判成示範指令")

    def test_python_scanner_ignores_strings_without_guidance_wording(self) -> None:
        """沒有指引措辭的字串（合成 fixture、pattern 表）不判——這是刻意的收窄。"""
        # 值刻意不用 Windows 磁碟機字面值（`tools/tests/test_platform_neutral_paths.py::
        # TestPlatformNeutralPaths::test_no_windows_drive_fake_paths` 會判紅）——本樣本
        # 要證的是「沒有指引措辭就不判」，路徑長什麼樣與它無關。
        src = 'PS_FIXTURE = "$env:PATH = \'somewhere\'"\n'
        self.assertEqual([], scan_python(src)[0])


# ═══════════════════════════════════════════════════════════════════════════
# ④ PG skip 解法的可發現性錨（本包的另一半：#1 不是技術缺陷，是找不到）
# ═══════════════════════════════════════════════════════════════════════════
class TestPgSkipRemedyStaysDiscoverable(unittest.TestCase):
    """「大量 skipped 的最大宗解法＝一行 docker 指令」必須留在使用者找得到的地方。

    Rule 9：本類守的是**可發現性**這個意圖，不是某段文字的排版。R83 實測
    （macOS，同一棵工作樹、同一支直譯器）：
      · `AUTOCLAUDE_NO_PG_AUTODETECT=1 pytest tests/ -q` → 172 skipped
      · 容器 healthy、零程式改動零環境變數 → 76 skipped
    ⇒ 96 支 skip 的全部成因就是「容器沒起來」，而這件事在 R83 之前於
    `ONBOARDING.md`／`useMacWin.md` 兩份 onboarding 文件裡**一個字都找不到**
    （只寫在 `AutoClaude/docker-compose.ci.yml` 檔頭——那是已經知道要找它的人才會開的檔）。
    這兩份文件是掌舵者實際會讀的入口，拿掉這段＝缺陷復發。
    """

    _COMPOSE_CMD = "docker compose -f docker-compose.ci.yml up -d"

    def test_both_onboarding_docs_carry_the_one_line_remedy(self) -> None:
        for rel in ("ONBOARDING.md", "useMacWin.md"):
            text = (_REPO_ROOT / rel).read_text(encoding="utf-8")
            self.assertIn(
                self._COMPOSE_CMD, text,
                f"{rel} 不再含 PG skip 的一行解法 `{self._COMPOSE_CMD}` ⇒ 可發現性缺陷復發",
            )
            self.assertIn(
                "docker info", text,
                f"{rel} 沒交代「先確認 daemon 真的活著」——那是這一行指令唯一的前置條件",
            )

    def test_the_compose_file_the_docs_point_at_actually_exists(self) -> None:
        """指路句指向不存在的東西比不指路更糟（本 repo 已有判例：死指標 §9.1）。"""
        self.assertTrue(
            (_REPO_ROOT / "AutoClaude" / "docker-compose.ci.yml").is_file(),
            "文件教人跑的 compose 檔不在磁碟上",
        )

    def test_the_kill_switch_named_in_the_docs_is_the_real_one(self) -> None:
        """現查指令用的旗標必須真的是 autodetect 讀的那一個，否則量出來的差額是假的。"""
        gate = (_REPO_ROOT / "AutoClaude" / "tools" / "local_ci_gate.py").read_text(
            encoding="utf-8")
        self.assertIn("AUTOCLAUDE_NO_PG_AUTODETECT", gate)
        for rel in ("ONBOARDING.md",):
            self.assertIn(
                "AUTOCLAUDE_NO_PG_AUTODETECT",
                (_REPO_ROOT / rel).read_text(encoding="utf-8"),
                f"{rel} 沒給出可重跑的現查方法 ⇒ 那個數字就只能靠人記得",
            )

    def test_docs_do_not_freeze_the_measured_delta_as_a_constant(self) -> None:
        """數字是量測值不是常數——本 repo 明文禁止把會漂的量寫進散文。

        判準只看 §7.1／D 段自己那幾行（以 compose 指令所在行為錨、前後 40 行），
        不去管文件其他地方的歷史快照註記（那些是刻意保留的時代史料）。
        """
        pattern = re.compile(r"消掉\s*\d+\s*支|少了\s*\d+\s*支\s*skip|skip.{0,4}由\s*\d+\s*降到\s*\d+")
        for rel in ("ONBOARDING.md", "useMacWin.md"):
            lines = (_REPO_ROOT / rel).read_text(encoding="utf-8").splitlines()
            anchors = [i for i, raw in enumerate(lines) if self._COMPOSE_CMD in raw]
            self.assertTrue(anchors, rel)
            for a in anchors:
                window = "\n".join(lines[max(0, a - 40):a + 40])
                self.assertIsNone(
                    pattern.search(window),
                    f"{rel} 把「消掉幾支」寫成了常數——那是量測值，只能給現查指令",
                )


if __name__ == "__main__":
    unittest.main()
