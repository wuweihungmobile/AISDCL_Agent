#!/usr/bin/env python3
"""`.claude/settings.json` 的 hook 佈線解析 — **唯一真相源**（R80）。"""
#
# 🔴 以下 WHY 為何用 `#`：**只是 R81 留下的體例，不再是預算理由**（ADR-XPLAT-013 否決權
# 複審 M3 訂正）。原文寫的是「`count_loc()` 把 docstring 計入、`#` 排除，搬回 docstring
# 會直接讓 LOC 閘門再紅一次」，並引 TIER-WARN 訊息當依據。那兩件事**現在都不成立**：
#   · ADR-XPLAT-013 起 `count_loc()` 只算**斷言行**，docstring 與整行 `#` 同為敘事、
#     同為零計價 ⇒ 換載體省不到一行。當回合實測：把下方 52 行 essay 逐字搬進 docstring，
#     `count_loc` 367 → 367（+0）。原文宣稱的「會再紅一次」是**假的**。
#   · 它引的那句 TIER-WARN 指路（「說明文字請寫成 `#` 而非 docstring」）已由
#     ADR-XPLAT-013 從 `check_loc_budget.py` **刪除** ⇒ 該引用已懸空。
# ⇒ 加 WHY 用 `#` 或 docstring 皆可，挑可讀性高的那個；不要再為了預算而搬敘事——
#   新計價下要省預算只有一條路：**少寫斷言**（拆職責／抽共用模組）。
#
# WHY 這支檔非有不可（立案量測，不是預防性設計）
# ================================================
# Claude Code 的 hook 條目有兩種形態，而**腳本路徑住在不同的欄位**：
#
#   · **shell form**（舊）：`{"command": "python -c \"…runpy…\" .claude/hooks/x.py"}`
#     → 腳本名在 `command` 字串裡。Windows 上這種形態經 Git Bash 的 `bash.exe -c` 起，
#       而 `bash.exe` 是 console 子系統程式 ⇒ **每觸發一次就閃一個 console 視窗**。
#   · **exec form**（新）：`{"command": "<執行檔>", "args": ["…/_hook_launcher.py",
#     ".claude/hooks/x.py", …]}` → 不經 shell、零視窗，但腳本名**結構性地搬到 `args`**。
#
# R80 實測：轉成 exec form 之後，repo 內「只讀 `command` 字串去找 hook 腳本名」的解析器
# **全部當場失明**——掃出來的腳本集合由 6 支變成 0~1 支。而那批解析器正是用來守
# 「文件宣稱 ↔ 實際註冊」「hook 註冊面只准縮」「根 CLAUDE.md 必須提到每一支已註冊
# hook」「已註冊腳本必須有 UTF-8 stdio 保護」的判準。
#
# 🔴 **本段刻意不寫死「有幾個」**（R80 二審 `NEW-ARCH-R80B-07`＝`QA2-N1`）：那個數字原本
# 寫在**三個家**（本段一處、下方 WHY 一處、`tools/tests/test_context_budget_guard.py` 的
# 委派註解一處）而只有**兩個值**（七／八），且下方清單第 7 項在落地當輪就已過期。
# 消費端會增減，是量測值不是常數 ⇒ 現查：
# `Grep pattern:"import hook_wiring" path:<repo 根>`（或 `hook_entry_argv|settings_targets|
# entries_launching` 這幾個入口名）。
#
# 🔴 **失明的後果比彈窗嚴重、而且方向是「看起來變乾淨」**：分母掃出 0 支 ⇒ 沒有東西
# 可違反 ⇒ 那幾道鎖安靜地變成恆綠，rc 與「正確地全部通過」一模一樣。這正是本 repo
# 反覆判過的兩個形態（「檔案在、但守的是別的東西」／「早退遮蔽訊號」）。
#
# 所以本檔的存在理由不是「抽共用層比較漂亮」，是：**同一份『這個 hook 條目到底會跑
# 哪支腳本』的知識，先前散住在好幾個家裡，改一種形態就要同時改每一處，而漏掉任何一處
# 都不會有任何東西轉紅。** 只依賴 stdlib（hook／護欄層執行環境不保證有第三方套件，
# 同 `tools/lib/platform_utils.py` 檔頭的約定）。
#
# 消費者（改動本檔的判準前先確認每一處仍成立；**清單是導覽，權威是上面那條現查指令**）
# --------------------------------------------------------------------------------
#   · `tools/tests/test_subprocess_encoding_hygiene.py::hook_command_scripts`
#   · `tools/tests/test_check_hooks_liveness.py::matchers_for_script`
#   · `tools/tests/test_doc_loc_baseline_freshness_r60.py::registered_hook_basenames`（經上一項）
#   · `tools/tests/test_context_budget_guard.py`（R80 二審訂正：此處 R80 落地當輪就已改為
#     委派本檔的 `hook_entry_argv`，而清單卻寫著「仍是 command-only」——**落地當輪即過期**）
#   · `tools/check_hooks_liveness.py`（延後 import，呼叫 `carrier_liveness_problems`；
#     R80 二審補列，先前整支漏在清單外）
#   · `AISDLC_SDD/scripts/router_hook_coverage_lint.py::router_wired_events`
#   · `AISDLC_SDD/scripts/tests/test_pretooluse_matcher_task.py::is_act020_carrier`
#   · `AISDLC_SDD/scripts/tests/test_hook_wiring_cwd_safety.py`（用 `hook_entry_argv`）
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

#: 統一啟動器的 repo 相對路徑（exec form 的 `command` 塞不進 `-c` 程式碼，
#: 所以那份 shim 必須有一個實體檔案的家）。
LAUNCHER_REL = ".claude/hooks/_hook_launcher.py"

#: Claude Code 注入的專案根佔位符。實測在 `command` **與** `args` 元素裡都會被展開。
PROJECT_DIR_PLACEHOLDER = "${CLAUDE_PROJECT_DIR}"

#: POSIX 側載具＝直接 exec 帶 shebang 的啟動器（git index 100755）。
POSIX_CARRIER = f"{PROJECT_DIR_PLACEHOLDER}/{LAUNCHER_REL}"

#: Windows 側載具，**只准二選一、且全檔不得混用**。
#: venv 版不看 PATH（與 session 怎麼被啟動無關）；PATH 版在 schtasks 起的 session 上
#: 實測解析不到（那種 session 的 `python` 是 pyenv shim，沒有 `pythonw.exe`）⇒ 會
#: 靜默失去全部 hook。混用兩種＝一部分 hook 在某些機器消失，且「加第二個當備援」會
#: 導致 hook 跑兩次（deny 型守衛第二次被略過＝安全洞）。
WIN_CARRIER_REL = ".venv/Scripts/pythonw.exe"
WIN_CARRIER_VENV = f"{PROJECT_DIR_PLACEHOLDER}/{WIN_CARRIER_REL}"
WIN_CARRIER_PATH = "pythonw.exe"
WIN_CARRIERS = (WIN_CARRIER_VENV, WIN_CARRIER_PATH)

#: hook command／args 裡的腳本路徑（正／反斜線皆收）。刻意不去解析 `-c` 那段 Python
#: 程式碼：shim 本體不含任何 `.py` 字面，路徑一律以引數形式出現。
_PY_TOKEN_RE = re.compile(r"[\w./\\${}-]*\.py")

#: 機器專屬絕對路徑：磁碟機代號、UNC、POSIX 家目錄、WSL 掛載（DEF-101-778 判例）。
_ABS_RE = re.compile(r"(?i)(^[a-z]:[\\/])|(^\\\\)|(^/users/)|(^/home/)|(^/mnt/[a-z]/)")

#: 一段或多段前導 `../`。**子專案 session 的 `CLAUDE_PROJECT_DIR` 是子專案目錄**，
#: 而啟動器只有一個家（monorepo 根層）⇒ 子專案的條目寫成
#: `${CLAUDE_PROJECT_DIR}/../.claude/hooks/_hook_launcher.py`（R81 轉換 AutoClaude 那份
#: 時採用；刻意不複製第二份啟動器——同一份知識住兩個家是本 repo 的頭號病）。
_PARENT_PREFIX_RE = re.compile(r"^(?:\.\./)+")


# 實測依據：`args: []` 會讓 CC 切到 exec form，於是整串 `python "…" x 0` 被當成
# **一個執行檔路徑**去 spawn（`uv_spawn ENOENT`）——所以「有 args」是判準，
# 「args 非空」不是。
def is_exec_form(hook: dict) -> bool:
    """條目是否為 exec form。判準＝**有沒有 `args` 欄位**（`args: []` 也算）。"""
    return isinstance(hook, dict) and "args" in hook


# `type` 缺席時視同 "command"（CC 的預設，也是既有合成 fixture 的寫法）；只有**明確標成
# 別種 type** 才排除——把「沒寫」當成「不是」會讓解析面靜默縮小。
#
# 🔴 為何非收斂成一支函式不可（R80 ARCH-02／SD-02，實測注入確認）：本檔一度同時存在
# **三種**慣例——`hook_entry_argv` 用 `get("type", "command")`（旁註逐字禁止「把沒寫當成
# 不是」）、`hook_form_problems` 用 `get("type") != "command": continue` 整條跳過、
# `declared_win_carriers` 根本不看 `type`。後果不是風格不一致，是**形態鎖多了一個免費
# 逃逸口**：把條目退回 shell form 時只要順手**省掉 `type`**，A~F 六條判準（含它自稱的
# 核心 E）一條都不會說話，而 `settings_targets()` 仍看得見那個條目 ⇒ CC 眼中它是活的
# hook、鎖眼中它不存在。這正是本 repo 反覆判過的「早退遮蔽訊號，而方向是看起來變乾淨」。
def is_command_hook(hook: dict) -> bool:
    """條目是不是 `type=="command"` — **全檔唯一**的 type 慣例。"""
    return isinstance(hook, dict) and hook.get("type", "command") == "command"


def hook_entry_argv(hook: dict) -> list[str]:
    """條目實際會被執行的 argv（`${CLAUDE_PROJECT_DIR}` **未展開**）。

    shell form 回 `[command]`（那一整串本來就是交給 shell 的），exec form 回
    `[command, *args]`。呼叫端要真的跑它時請先過 `expand_tokens()`。
    """
    if not is_command_hook(hook):
        return []
    command = str(hook.get("command", ""))
    if not is_exec_form(hook):
        return [command]
    args = hook.get("args")
    return [command] + [str(a) for a in (args if isinstance(args, list) else [])]


def expand_tokens(tokens: list[str], project_dir: str) -> list[str]:
    """把 `${CLAUDE_PROJECT_DIR}` 展開成 `project_dir`，並轉成本平台的路徑分隔符。"""
    out: list[str] = []
    for tok in tokens:
        expanded = tok.replace(PROJECT_DIR_PLACEHOLDER, project_dir.replace("\\", "/"))
        out.append(os.path.normpath(expanded) if "/" in expanded else expanded)
    return out


# 實測依據（R80，Windows）：`.py` 直接 spawn 回 `EFTYPE`、缺檔回 `ENOENT`，
# 兩者 CC 都只記一行 ERROR 就放行（**fail-open**）。所以「跑不起來」不是缺陷，
# 是跨平台配對設計刻意的那一半——但驗證載具必須知道自己在哪一半，否則會把
# 「另一個平台的那條」當成真紅。
def carrier_available(hook: dict, project_dir: str, *, exists=os.path.exists) -> bool:
    """這個條目的載具在**當前平台**跑不跑得起來（配對中恰好一條成立、另一條 fail-open）。"""
    argv = hook_entry_argv(hook)
    if not argv:
        return False
    if not is_exec_form(hook):
        return True  # shell form 一律交給 shell，可跑與否由 shell 決定
    exe = expand_tokens([argv[0]], project_dir)[0]
    if "/" not in exe and os.sep not in exe:
        return True  # 靠 PATH 解析，靜態判不了 ⇒ 不擅自判死
    if not exists(exe):
        return False
    if exe.lower().endswith(".py"):
        return os.name != "nt"  # Windows 上 .py 不能直接 spawn（實測 EFTYPE）
    return True


# 🔴 前導 `../` 一併剝掉（R81）：不剝的話，子專案條目裡的
# `${CLAUDE_PROJECT_DIR}/../.claude/hooks/_hook_launcher.py` 與 `LAUNCHER_REL`
# 比不相等 ⇒ `hook_entry_targets()` 會把**載具**當成一支「已註冊的 hook 腳本」算進去，
# 而「載具不是守衛」正是那個函式特意要區分的事（見其旁註）。
def _normalise(token: str) -> str:
    """把一個路徑 token 正規化成專案相對的 posix 路徑（無佔位符、無前導斜線／`../`）。"""
    rel = token.replace("\\", "/")
    rel = rel.replace(PROJECT_DIR_PLACEHOLDER, "")
    return _PARENT_PREFIX_RE.sub("", rel.lstrip("/"))


# 為何不是 `== POSIX_CARRIER` 的字面比對：子專案（AutoClaude）與 SDD 各版的
# `CLAUDE_PROJECT_DIR` 指向自己那個目錄，而啟動器只有一個家 ⇒ 那些條目以一段或多段
# `../` 回到 monorepo 根層取用**同一支檔**。字面比對會把它們判成「沒有宣告 POSIX 載具」，
# 於是 `posix_carrier_problems()` 對整個子專案靜默失明——而那一側的失效同樣是 fail-open。
def is_posix_carrier(command: str) -> bool:
    """`command` 是不是 POSIX 載具（＝啟動器本身），`../` 前綴視為同一個載具。"""
    return _normalise(str(command)) == LAUNCHER_REL


# 🔴 R84（訴求 7／A2b）：Windows 載具也必須走**正規化**比對，理由與上面那段逐字同構，
# 而代價已經量到了——`hook_form_problems()` 對 `AutoClaude/.claude/settings.json`
# 回 **12 筆假紅**（6 筆「args[0] 必須是啟動器」＋ 6 筆「command 只准是…」），因為那份
# 檔的載具帶 `../`。`is_posix_carrier()` 在 R81 已經修好這件事，B／E 兩條卻仍在做字面
# 比對 ⇒ **同一個缺口只補了一半**。假紅的下場不是「比較嚴格」：這份檔的形態判準因此
# 永遠回非空，任何人想把 A~F 的掃描面擴到子專案／SDD LATEST 都會先撞到一堵假牆，
# 於是那個擴面一直沒有發生（本輪 SDD LATEST 30 份全是 shell form 就是它的下游後果）。
# 回 kind（而不是 bool）是因為判準 F 要的是「有沒有混用兩**種**載具」——正規化之後
# `../.venv/…` 與 `../../.venv/…` 是同一種，混用判準必須看種類而不是字面。
def win_carrier_kind(command: str) -> str | None:
    """Windows 載具的種類：`"venv"`／`"path"`；不是 Windows 載具回 `None`。"""
    cmd = str(command)
    if cmd == WIN_CARRIER_PATH:
        return "path"
    return "venv" if _normalise(cmd) == WIN_CARRIER_REL else None


# 兩種形態都認得——這就是本檔存在的全部理由。預設**不含啟動器本身**：啟動器是
# 載具不是守衛，它只是在同一個行程裡 `runpy` 目標腳本；把它算成「已註冊 hook 腳本」
# 會讓下游那些「每支已註冊腳本都要有 X」的判準把載具也算進去（例如 stdio 強制那道
# per-tree shrink-only 棘輪會被迫 +1，而那是**調高棘輪**，本 repo 明文禁止）。
# 需要看載具本身時傳 `include_launcher=True`。
def hook_entry_targets(hook: dict, *, include_launcher: bool = False) -> list[str]:
    """這個 hook 條目**實際會跑到**的腳本（repo 相對 posix 路徑，保序去重）。"""
    out: list[str] = []
    for token in _PY_TOKEN_RE.findall(" ".join(hook_entry_argv(hook))):
        rel = _normalise(token)
        if not rel:
            continue
        if rel == LAUNCHER_REL and not include_launcher:
            continue
        if rel not in out:
            out.append(rel)
    return out


def settings_targets(settings: dict, *, include_launcher: bool = False) -> list[tuple[str, str]]:
    """`settings` 內每個 hook 條目會跑到的腳本 → `[(事件名, repo 相對 posix 路徑)]`。"""
    out: list[tuple[str, str]] = []
    for event, entries in (settings.get("hooks") or {}).items():
        for entry in entries or []:
            for hook in entry.get("hooks") or []:
                for rel in hook_entry_targets(hook, include_launcher=include_launcher):
                    out.append((str(event), rel))
    return out


def entries_launching(settings: dict, needle: str, event: str = "PreToolUse") -> list[dict]:
    """`settings[event]` 內，**實際會跑到** `needle`（腳本名或路徑片段）的那些 block。"""
    found: list[dict] = []
    for entry in (settings.get("hooks") or {}).get(event, []) or []:
        for hook in entry.get("hooks") or []:
            if any(needle in rel for rel in hook_entry_targets(hook, include_launcher=True)):
                found.append(entry)
                break
    return found


# ─────────────────────────────────────────────────────────────────────────────
# 形態判準 A~F（回歸鎖用；純函式，回非空即紅）
# ─────────────────────────────────────────────────────────────────────────────

# 六條規則（任一違反即回一筆問題；空 list＝綠）：
#   A 每個 `type=="command"` 條目必須有 `args`（沒有＝shell form＝Windows 上閃窗）
#   B `command` 只准是兩種載具之一（防有人塞回 `python`／`sh -c`／`cmd /c`）；比對走
#     `win_carrier_kind()`／`is_posix_carrier()` 的**正規化**版，不是字面（R84／A2b）
#   C `command` 不得含空白（V4 陷阱：`args` 存在時整串會被當成一個執行檔路徑，
#     實測 `uv_spawn ENOENT`，而它「看起來像對的」）
#   D `command` 與所有 `args` 元素不得出現機器專屬絕對路徑（DEF-101-778）
#   E 每個目標在同一 block 內必須恰好一個 Windows 條目 ＋ 恰好一個 POSIX 條目
#     ⚠️ **這條是本鎖的核心**：exec form 的 spawn 失敗是 **fail-open**，少一邊
#     不會有任何東西轉紅，只會在那個平台靜默失去這個 hook
#   F 全檔不得混用兩**種** Windows 載具（venv／PATH，見 `WIN_CARRIERS` 旁註記）
def hook_form_problems(settings: dict) -> list[str]:
    """形態判準 A~F（詳見上方註記）。"""
    problems: list[str] = []
    carriers_used: set[str] = set()
    for event, blocks in (settings.get("hooks") or {}).items():
        for index, block in enumerate(blocks or []):
            where = f"{event}[{index}] matcher={block.get('matcher', '-')!r}"
            pairs: dict[tuple[str, ...], dict[str, int]] = {}
            for hook in block.get("hooks") or []:
                if not is_command_hook(hook):
                    continue
                command = str(hook.get("command", ""))
                if not is_exec_form(hook):
                    problems.append(
                        f"{where}: 條目退回 shell form（無 args 欄位）⇒ Windows 上會經 "
                        f"bash.exe 而閃 console 視窗：{command[:60]!r}")
                    continue
                args = hook.get("args")
                if not isinstance(args, list) or not args:
                    problems.append(f"{where}: args 必須是非空陣列，實得 {args!r}")
                    continue
                args = [str(a) for a in args]
                if re.search(r"\s", command):
                    problems.append(
                        f"{where}: command 含空白 ⇒ exec form 會把整串當成一個執行檔"
                        f"路徑（實測 uv_spawn ENOENT）：{command[:60]!r}")
                    continue
                hits = [v for v in [command, *args] if _ABS_RE.search(v)]
                if hits:
                    problems.append(
                        f"{where}: 出現機器專屬絕對路徑"
                        f"（只准 {PROJECT_DIR_PLACEHOLDER} 佔位）：{hits}")
                kind = win_carrier_kind(command)
                if kind:
                    carriers_used.add(kind)
                    if not is_posix_carrier(args[0]):
                        problems.append(
                            f"{where}: Windows 載具的 args[0] 必須是啟動器 "
                            f"{POSIX_CARRIER!r}，實得 {args[0]!r}")
                        continue
                    tail = tuple(args[1:])
                    pairs.setdefault(tail, {})
                    pairs[tail]["win"] = pairs[tail].get("win", 0) + 1
                elif is_posix_carrier(command):
                    tail = tuple(args)
                    pairs.setdefault(tail, {})
                    pairs[tail]["posix"] = pairs[tail].get("posix", 0) + 1
                else:
                    problems.append(
                        f"{where}: command 只准是 {WIN_CARRIERS}（Windows 載具）或 "
                        f"{POSIX_CARRIER!r}（POSIX 載具），實得 {command!r}")
            for tail, seen in pairs.items():
                if seen.get("win", 0) != 1 or seen.get("posix", 0) != 1:
                    problems.append(
                        f"{where}: 目標 {list(tail)} 的載具未成對（win={seen.get('win', 0)} "
                        f"posix={seen.get('posix', 0)}，各需恰好 1）⇒ 缺的那一邊在該平台"
                        "會靜默失去這個 hook，而 spawn 失敗是 fail-open、不會有任何"
                        "東西轉紅")
    if len(carriers_used) > 1:
        problems.append(
            f"同一份 settings.json 混用了兩種 Windows 載具 {sorted(carriers_used)}："
            "兩者前置條件不同（venv 存在 vs PATH 找得到），混用等於讓一部分 hook 在"
            "某些 session 靜默消失；而『加第二個當備援』會讓 hook 跑兩次")
    return problems


# ─────────────────────────────────────────────────────────────────────────────
# 載具存在性判準（方案書 §4.3 自陳「連 .venv 都沒有仍無機械物看守」那個缺口）
# ─────────────────────────────────────────────────────────────────────────────

def declared_win_carriers(settings: dict) -> set[str]:
    """`settings` 內宣告過的 Windows 載具字串集合。"""
    out: set[str] = set()
    for _event, blocks in (settings.get("hooks") or {}).items():
        for block in blocks or []:
            for hook in block.get("hooks") or []:
                command = str(hook.get("command", ""))
                if is_command_hook(hook) and is_exec_form(hook) and win_carrier_kind(command):
                    out.add(command)
    return out


def declared_posix_carriers(settings: dict) -> set[str]:
    """`settings` 內宣告過的 POSIX 載具字串集合（判準與 Windows 側對稱）。"""
    return {
        str(hook.get("command", ""))
        for _event, blocks in (settings.get("hooks") or {}).items()
        for block in blocks or []
        for hook in block.get("hooks") or []
        if is_command_hook(hook) and is_exec_form(hook)
        and is_posix_carrier(hook.get("command", ""))
    }


# 🔴 為什麼這道非有不可（方案書 §4.3 自己劃出的缺口）：載具解析不到時 CC 只記一行
# ERROR、工具照跑（**fail-open**）⇒ 六支守衛會**全部靜默失效，而螢幕上的表徵就是
# 「終於不閃窗了」**——與修好了一模一樣。把缺口寫下來卻不給判準，等於把它登記成
# 「已知且已接受」。
#
# 🔴 為什麼判準綁「宣告」而不是硬編一個路徑：這樣「有人把載具改成別的東西」也會
# 被同一條守到（改了宣告就要有對應的實況），而不是只守住今天這一種寫法。
#
# 非 Windows 不看 `.venv/Scripts/pythonw.exe`：它在 mac/Linux 本來就不存在，那條在
# 該平台是**設計上的 fail-open**、不是缺陷（`DEF-101-766`：單平台判準不可無條件外推）。
# `PATH` 載具同樣不在射程內——它的實況取決於 session 的 PATH，不是磁碟上的檔案，
# 靜態判準看不到，硬判會變成誤報。
#
# 🔴 R80 SA-05：非 Windows **不再一律回空**，改判該平台自己的那條載具（見
# `posix_carrier_problems`）。原本的「回空」把「這個平台沒有 Windows 載具」誤當成
# 「這個平台沒有載具問題」——而 POSIX 那條同樣是單點失效面，失效同樣靜默。
#
# 🔴 誠實劃界（R84）：`project_dir` 是**單一** session 的專案根，而帶 `../` 的載具字串
# 要用它自己那份 settings 所屬的專案根去展開才對得上 ⇒ 本函式不可拿 monorepo 根去跑
# 子專案／SDD LATEST 那兩份（會 normpath 到 repo 之外而假紅）。呼叫端現況只餵根層那份。
def carrier_liveness_problems(
    settings: dict,
    project_dir: str,
    *,
    exists=os.path.exists,
    on_windows: bool = os.name == "nt",
    is_exec=None,
    probe=None,
) -> list[str]:
    """**宣告 ↔ 實況**雙向綁定：settings 宣告了 venv 載具 ⇒ 那個路徑必須真的存在。"""
    if not on_windows:
        return posix_carrier_problems(
            settings, project_dir, exists=exists, is_exec=is_exec, probe=probe)
    problems: list[str] = []
    for carrier in sorted(declared_win_carriers(settings)):
        if win_carrier_kind(carrier) != "venv":
            continue  # PATH 版的實況取決於 session 的 PATH，靜態判不了（見上方 docstring）
        path = expand_tokens([carrier], project_dir)[0]
        if not exists(path):
            problems.append(
                f"`.claude/settings.json` 宣告 Windows hook 載具 {carrier}，但實況不存在："
                f"{path}\n"
                "    ⇒ 這台機器上**全部 hook 都不會跑**（載具 spawn 失敗是 fail-open，"
                "只記一行 ERROR、工具照跑），\n"
                "      而螢幕上的表徵與『修好了』完全相同：不閃窗、沒有錯誤。\n"
                "    修法：在 repo 根跑 bootstrap 重建 .venv"
                "（tools/bootstrap.ps1 ／ tools/bootstrap.sh），\n"
                "      或現查一行：Test-Path (Join-Path $env:CLAUDE_PROJECT_DIR "
                "'.venv\\Scripts\\pythonw.exe')")
    return problems


#: POSIX 載具能承載的**最低**直譯器版本。SSOT＝`tools/bootstrap_core.py`（它挑直譯器
#: 與建 venv 的門檻逐字是 `>= (3, 11)`）。此處刻意重寫一份而不 import 那支檔：本檔的
#: 檔頭約定「只依賴 stdlib」，而兩端不一致會由 `tools/tests/test_check_hooks_liveness.py`
#: 的對照斷言當場轉紅——同一份知識**允許**住兩個家的唯一條件就是有東西在對帳。
POSIX_MIN_PY = (3, 11)


def _probe_shebang(path: str) -> tuple[str | None, tuple[int, int] | None]:
    """讀 `path` 的 shebang → `(解析到的直譯器, 版本)`；任一步做不到該格回 `None`。"""
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            first = handle.readline()
    except OSError:
        return (None, None)
    parts = first[2:].split() if first.startswith("#!") else []
    if not parts:
        return (None, None)
    name = parts[1] if os.path.basename(parts[0]) == "env" and len(parts) > 1 else parts[0]
    interp = shutil.which(name)
    if not interp:
        return (None, None)
    try:
        done = subprocess.run(
            [interp, "-c", "import sys; print('%d %d' % sys.version_info[:2])"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=20, check=False)
        major, minor = (int(tok) for tok in done.stdout.split())
    except Exception:
        return (interp, None)
    return (interp, (major, minor))


# 🔴 為何 POSIX 這半非有不可（缺口的形狀與 Windows 側**不對稱**，不是順手補對稱）：
# Windows 條目把載具釘死在 `.venv/Scripts/pythonw.exe`——一個確定的檔案，在不在看得出來。
# POSIX 條目的 `command` 是那支帶 shebang 的啟動器本身，於是真正被執行的直譯器是
# **`PATH` 上任意一個 `python3`**：macOS 內建那支常年是 3.9，而本 repo 的 bootstrap 門檻
# 是 3.11。三種失效——檔不在／沒有執行位元／shebang 解析到的直譯器太舊——**表徵完全相同**：
# CC 只記一行 ERROR 就放行（fail-open），六支守衛一起消失，而螢幕上看起來就是
# 「終於不閃窗了」。
#
# 誠實劃界：`PATH` 是 session 屬性，本判準量的是**跑這個檢查的那個 shell 的 PATH**，
# 不是 Claude Code 自己那個行程的（拿不到）。所以它抓得到「這台機器根本沒有夠新的
# python3」，抓不到「CC 的 PATH 與我的不同」。必要條件，不是充分條件。
def posix_carrier_problems(
    settings: dict,
    project_dir: str,
    *,
    exists=os.path.exists,
    is_exec=None,
    probe=None,
) -> list[str]:
    """POSIX 側載具的**宣告 ↔ 實況**綁定（R80 SA-05；WHY 見上方註記）。"""
    if is_exec is None:
        def is_exec(path: str) -> bool:
            return os.access(path, os.X_OK)
    probe = probe or _probe_shebang
    problems: list[str] = []
    for carrier in sorted(declared_posix_carriers(settings)):
        path = expand_tokens([carrier], project_dir)[0]
        if not exists(path):
            problems.append(
                f"`.claude/settings.json` 宣告 POSIX hook 載具 {carrier}，但實況不存在："
                f"{path} ⇒ 這台機器上**全部 hook 都不會跑**（spawn 失敗是 fail-open）")
            continue
        if not is_exec(path):
            problems.append(
                f"POSIX hook 載具 {path} 沒有執行位元 ⇒ spawn 回 EACCES、CC 只記一行 "
                "ERROR 就放行，六支守衛一起靜默消失。修法：git index 應為 100755"
                "（`git update-index --chmod=+x`），並確認 checkout 沒有把它洗掉")
            continue
        interp, version = probe(path)
        if interp is None:
            problems.append(
                f"POSIX hook 載具 {path} 的 shebang 解析不到任何直譯器 ⇒ 直接 exec 它會"
                "失敗，而失敗是 fail-open（六支守衛靜默消失）")
            continue
        if version is not None and version < POSIX_MIN_PY:
            want = ".".join(str(n) for n in POSIX_MIN_PY)
            got = ".".join(str(n) for n in version)
            problems.append(
                f"POSIX hook 載具的 shebang 解析到 {interp}（Python {got}），低於本 repo "
                f"的下限 {want}（SSOT：tools/bootstrap_core.py）。這在 macOS 上是**預設**"
                "狀態（系統 python3 常年 3.9），所以這行話在 mac 上 day 1 就會響——"
                "正因如此它必須說真話，否則只是在訓練你忽略它。\n"
                "    實測後果（R82 MAC-03；`tools/tests/test_mac_readiness_r82.py` 現查）："
                "現行 hook 集**載入得起來**，但 `.claude/hooks/context_budget_guard.py` 依賴的 "
                "`tools/lib/quota_meter.py` 帶 3.11+ 構造，會走該檔的 try/except 退化成 "
                "`None` ⇒ **額度軸整條靜默消失**（hook 仍回 rc=0，螢幕表徵與健康完全相同）。\n"
                "    真正的風險面：hook 鏈上**沒有 try/except 保護**的那幾格（例如同檔的 "
                "`from quota_limits import …`，該處刻意不給 fallback）一旦被加進任何 3.11 "
                "專屬 import，六支守衛會一起靜默消失——而 spawn／import 失敗是 fail-open"
                "（CC 只記一行 ERROR、工具照跑）。\n"
                f"    修法：讓 PATH 上的 python3 指向 >= {want}，或把 POSIX 條目的 "
                "command 釘到 venv 內的直譯器（後者要一併處理「全新 clone 還沒有 venv」）")
    return problems


# ─────────────────────────────────────────────────────────────────────────────
# 執行期證據（本輪）：載具**真的**解析到了嗎
# ─────────────────────────────────────────────────────────────────────────────

# 🔴 為何靜態那三道全都看不到「載具解析不到」（M9 立案，本輪現查得出的空格）
# ---------------------------------------------------------------------------
# 現查（母體＝本機 `~/.claude/projects/<slug>/` 全部 1,061 支逐字稿）：
# `hook_non_blocking_error` 共 **217** 筆，其 stderr **全部** 是同一句
# `ENOENT: no such file or directory, posix_spawn '<repo>/.venv/Scripts/pythonw.exe'`
# ——分佈 PreToolUse 86／PostToolUse 72／SessionStart 40／**Stop 19**，跨
# 2026-08-12 ~ 2026-08-21（九天）、Stop 那 19 筆分屬 16 個不同 session。
#
# ⇒ 第一個結論與直覺相反：**這不是 Stop 專屬的缺陷**。四個事件全中，因為每個 block 依
# 形態判準 E 都必須成對（Windows 一條 ＋ POSIX 一條），而 mac 上 Windows 那條每次必然
# ENOENT。「Stop 只有 19 筆」不是它比較少壞，是 attachment 落盤本身有偏差（見下）。
#
# 三道靜態機械物為何一條都沒說話，逐一對號：
#   · `hook_form_problems()`（A~F）：**成對是它要求的**，兩條都在 ⇒ 判綠是正確的。
#   · `carrier_liveness_problems()`：非 Windows 第一行就 `return posix_carrier_problems(...)`
#     ⇒ 結構上**看不到** Windows 那條。這是刻意的（外平台載具不存在是設計，不是缺陷），
#     但代價是「宣告↔實況」這條綁定在每個平台**只綁一半**。
#   · `tools/check_hooks_liveness.py`：檔頭自陳射程＝git hooks 生效性 ＋ 載具**存在性**，
#     兩者都是靜態讀檔。
# ⇒ 缺的那一格不是「再加一條靜態判準」，是**沒有任何東西讀執行期證據**。而執行期證據
# 一直都在（逐字稿裡的 hook attachment），只是零讀者——與本輪 M8 判過的「痕跡沒有自動
# 讀者 ⇒ 它不是機制」同型。
#
# 🔴 第二個結論（判準能做到什麼、做不到什麼，是量出來的）：`hook_success` **只有在
# hook 真的印了東西時才落盤**——全母體 11,438 筆 success 逐筆檢查，stdout 或 stderr
# 至少一個非空的有 11,438 筆、兩者皆空 **0 筆**；而根層六支守衛安靜時一筆都不留（全母體
# 只有 14 筆屬於根層 hook，其餘 11,424 筆全是會固定印字的 SDD 三支）。
# ⇒ 「某個目標零 success」**不能**當成「它沒跑起來」，那會對每一支安靜的守衛假紅。
# 可判的只有**失敗**那一半，所以本判準只問一件事：**這次失敗的是不是本平台自己那條載具**。
HOOK_RESULT_TYPES = ("hook_success", "hook_non_blocking_error")


def hook_result_attachments(records) -> list[dict]:
    """逐字稿記錄串 → 其中的 hook 執行結果 attachment（保序；非該型一律略過）。"""
    return [rec["attachment"] for rec in records
            if isinstance(rec, dict) and isinstance(rec.get("attachment"), dict)
            and rec["attachment"].get("type") in HOOK_RESULT_TYPES]


# 三種分類，各自的**方向**都是設計上決定的：
#   · `native`：本平台自己那條載具失敗 ⇒ **真的壞了**（那個 hook 這一次沒跑，而 CC 只記
#     一行 ERROR 就放行）。這是本判準會轉紅的一類。
#   · `by_design`：另一個平台那條失敗 ⇒ 跨平台配對刻意的 fail-open，**不是缺陷**。它必須
#     被**數出來**而不是被忽略：一個每次都響的噪音底線會讓真訊號無法被辨認（本 repo 對
#     「一個永遠在響的警報等於沒有警報」已有判例），而九天沒人發現正是這個機制。
#   · `alien`：失敗的 command 兩種載具都不是（有人塞回 `python -c`／改了載具／多了第三種）
#     ⇒ 也算真的壞了，因為形態判準只看 settings.json，看不到「實際被執行的是別的東西」。
# 上限 8 筆是訊息長度的防呆：同一場同一條載具會重複失敗上百次，逐筆列出等於把訊息變成
# 沒有人會讀的一片牆（計數欄仍然是全量，不受這個上限影響）。
def runtime_carrier_verdict(attachments, *, on_windows: bool = os.name == "nt"
                            ) -> tuple[list[str], dict[str, int]]:
    """執行期證據 → `(真的壞了的問題清單, 分類計數)`；問題清單非空即紅。"""
    counts = dict.fromkeys(("native_fail", "by_design_fail", "alien_fail", "success"), 0)
    problems: list[str] = []
    for att in attachments:
        command = str(att.get("command") or "")
        head = (command.split() or [""])[0]
        if att.get("type") == "hook_success":
            counts["success"] += 1
            continue
        win, posix = bool(win_carrier_kind(head)), is_posix_carrier(head)
        where = f"[{att.get('hookEvent') or att.get('hookName') or '?'}]"
        if win if on_windows else posix:
            counts["native_fail"] += 1
            problems.append(
                f"{where} 本平台自己那條 hook 載具失敗 ⇒ "
                f"{(hook_entry_targets({'command': command}) or ['?'])[0]} 這一次**沒有跑**"
                f"（CC 只記一行 ERROR 就放行，fail-open）：{str(att.get('stderr') or '')[:200]}")
        elif win or posix:
            counts["by_design_fail"] += 1
        else:
            counts["alien_fail"] += 1
            problems.append(
                f"{where} 失敗的 command 不是本 repo 認得的兩種載具之一（形態判準只看 "
                f"settings.json，看不到實際被執行的是別的東西）：{head!r}")
    return problems[:8], counts


# ─────────────────────────────────────────────────────────────────────────────
# exec form 轉換的**射程**（R80 QA-03）：哪一份轉了、哪一份還沒
# ─────────────────────────────────────────────────────────────────────────────

#: 凍結版 settings 的路徑前綴（Copy-on-Evolve：各版目錄是歷史快照，不隨演化改寫）。
FROZEN_SETTINGS_PREFIX = "AISDLC_SDD/AISDLC_SDD_v"

#: LATEST SDD 版那一份 settings 在普查表裡的**版本中性**鍵。
#: 刻意不用真實路徑當鍵：那會把「現在 LATEST 是哪一版」寫成常數，而 Copy-on-Evolve
#: 每開一版就會讓它過期（同 `FRAMEWORK_STATUS.md` 為版號唯一真相源的既有政策）。
LATEST_SETTINGS_KEY = "AISDLC_SDD/<LATEST>/.claude/settings.json"

#: 凍結歷史面（各版目錄裡**非 LATEST** 的那些）仍是 shell form 的 settings **份數**。
#: 判準是相等、方向是只准變小，理由與 `SHELL_FORM_CENSUS` 逐字同構。
#:
#: 🔴 為何不是 0（誠實劃界，不是放寬）：那 29 份是 Copy-on-Evolve 的歷史快照，依政策
#: 不改寫（本 repo 明文：凍結面一律不動）。把它們登記成**已知豁免且只准變小**，是為了
#: 讓「LATEST 那一份退回 shell form」與「凍結面被人動了」兩件事各有一條會轉紅的判準；
#: 寫成散文（R80／R81 的做法）的代價已經實測到：`FROZEN_SETTINGS_PREFIX` 把 30 份全部
#: 結構性排除在 `SHELL_FORM_CENSUS` 之外 ⇒ 那兩格「皆為 0」是**假的安心**，而只要掌舵者
#: 曾以 SDD 版目錄為 cwd 開 session（框架 skills 正掛那裡），R80／R81 的修法一次都沒生效。
#:
#: 新開一版時這個數字**不會上升**：新版由已是 exec form 的 LATEST 複製而來，LATEST 前移
#: 之後舊 LATEST 掉進凍結面時本身就是 exec form。上升＝有人真的改了凍結面。
FROZEN_SHELL_FORM_MAX = 29

#: `latest_sdd_settings()` 的 per-repo 快取（LATEST 解析走 subprocess SSOT，一次約 0.3s，
#: 而本模組的判準會對同一個 repo root 反覆問它）。
_LATEST_SETTINGS_CACHE: dict[str, str | None] = {}


# LATEST 解析**不自己實作**：SSOT 是 `AISDLC_SDD/scripts/sdd_version.py`，而 repo 內
# 已有唯一的 Python 轉接層 `tools/lib/sdd_latest.py`（R66 收斂掉 10 份逐字複本）。
# 這裡刻意延後 import 並吞掉例外：本模組是 hook／護欄層的取數管道，LATEST 解析失敗
# （非 git、tarball、SDD 樹不存在）不該讓整條判準爆掉——回 `None` 時 LATEST 那一份
# 只是回到「不在射程內」，而它不在射程時普查表的缺鍵會由 `shell_form_census_problems()`
# 的「在普查表內卻掃不到 ⇒ 射程疑似縮小」那一款出聲，不會靜默。
def latest_sdd_settings(repo_root) -> str | None:
    """LATEST SDD 版的 `.claude/settings.json`（repo 相對 posix）；解析不到回 `None`。"""
    root = Path(repo_root)
    key = str(root)
    if key not in _LATEST_SETTINGS_CACHE:
        rel = None
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from sdd_latest import resolve_latest_name  # noqa: PLC0415

            rel = (f"AISDLC_SDD/{resolve_latest_name(root / 'AISDLC_SDD')}"
                   "/.claude/settings.json")
        except Exception:
            rel = None
        _LATEST_SETTINGS_CACHE[key] = rel if rel and (root / rel).is_file() else None
    return _LATEST_SETTINGS_CACHE[key]

#: **活躍**（真的會被 Claude Code 載入）的 settings 檔 → 該檔目前殘留的 shell form 條目數。
#:
#: 🔴 本表的存在理由（史實，不是現況）：R80 的 exec form 只轉了**根層那一份**，
#: AutoClaude 子專案那 6 條當時仍是 shell form ⇒ 在 AutoClaude 子專案 session 下閃窗
#: 一次都沒少，而根 `CLAUDE.md` 一度把它寫成通則。把「哪一份轉了」寫成散文的代價是
#: 「某一份退回 shell form」永遠不會轉紅，所以它被登記成**量測值**。
#: R81 把 AutoClaude 那 6 條轉完（12 條 exec form 條目），故本表**兩格皆為 0**——
#: 表歸零不代表可以拆掉：它現在守的是「不准有人再退回去」。
#:
#: 判準是**相等**（形狀同 `tools/lib/skip_tag_policy._SITE_CLASS_CENSUS`）：
#: 多了＝有人退回 shell form（那一份的閃窗回來了）；少了＝有人轉好了卻沒回來改這張表，
#: 而餘裕就是日後無聲加回去的破口。掃描面是**現查磁碟**，不是寫死清單——新開一份活躍
#: settings 卻不入表也會紅。
#: 🔴 R84 補第三格：`AISDLC_SDD/<LATEST>/.claude/settings.json`。它先前被
#: `FROZEN_SETTINGS_PREFIX` **結構性排除**在掃描面之外 ⇒ 「兩格皆為 0」是假的安心
#: （見 `FROZEN_SHELL_FORM_MAX` 旁那段立案事實）。鍵用版本中性佔位，見 `LATEST_SETTINGS_KEY`。
SHELL_FORM_CENSUS: dict[str, int] = {
    ".claude/settings.json": 0,
    "AutoClaude/.claude/settings.json": 0,
    LATEST_SETTINGS_KEY: 0,
}


def shell_form_entries(settings: dict) -> list[str]:
    """`settings` 內仍是 shell form 的 hook 條目（回 command 前 60 字，供訊息用）。"""
    return [
        str(hook.get("command", ""))[:60]
        for _event, blocks in (settings.get("hooks") or {}).items()
        for block in blocks or []
        for hook in block.get("hooks") or []
        if is_command_hook(hook) and not is_exec_form(hook)
    ]


# 🔴 R84：排除規則由「整個 `AISDLC_SDD/AISDLC_SDD_v*` 家族」收窄成「**非 LATEST** 的那些」。
# 舊版把 LATEST 也排掉，而 LATEST 是**真的會被 Claude Code 載入**的活躍檔（框架 skills
# 掛在那個目錄，以它為 cwd 開 session 是常態）⇒ 它退回／停留在 shell form 時沒有任何
# 東西轉紅。凍結歷史面另有 `frozen_shell_form_problems()` 這條 shrink-only 判準看著，
# 所以這裡的收窄不會讓凍結面變成無人看管。
def discover_active_settings(repo_root) -> list[str]:
    """repo 內**活躍**的 `.claude/settings.json`（repo 相對 posix；含 SDD LATEST 那一份）。"""
    root = Path(repo_root)
    latest = latest_sdd_settings(root)
    found: list[str] = []
    for pattern in (".claude/settings.json", "*/.claude/settings.json",
                    "*/*/.claude/settings.json"):
        for path in root.glob(pattern):
            rel = path.relative_to(root).as_posix()
            if rel in found or (rel.startswith(FROZEN_SETTINGS_PREFIX) and rel != latest):
                continue
            found.append(rel)
    return sorted(found)


def census_key(rel: str, repo_root) -> str:
    """實際路徑 → 普查鍵（LATEST 那一份換成版本中性鍵，其餘原樣）。"""
    return LATEST_SETTINGS_KEY if rel == latest_sdd_settings(repo_root) else rel


def census_counts(repo_root) -> dict[str, int]:
    """現查磁碟 → `{普查鍵: 該份殘留的 shell form 條目數}`（取數管道只有一個家）。"""
    return {
        census_key(rel, repo_root):
            len(shell_form_entries(json.loads(
                (Path(repo_root) / rel).read_text(encoding="utf-8"))))
        for rel in discover_active_settings(repo_root)
    }


def frozen_shell_form_settings(repo_root) -> list[str]:
    """凍結面（各版目錄裡**非 LATEST** 的那些）仍殘留 shell form 條目的 settings 清單。"""
    root = Path(repo_root)
    latest = latest_sdd_settings(root)
    out: list[str] = []
    for path in sorted(root.glob(f"{FROZEN_SETTINGS_PREFIX}*/.claude/settings.json")):
        rel = path.relative_to(root).as_posix()
        if rel != latest and shell_form_entries(
                json.loads(path.read_text(encoding="utf-8"))):
            out.append(rel)
    return out


def frozen_shell_form_problems(found: list[str], cap: int | None = None) -> list[str]:
    """凍結面 shell form 份數的相等判準（純函式；空＝通過）。"""
    want = FROZEN_SHELL_FORM_MAX if cap is None else cap
    if len(found) == want:
        return []
    verb = ("上升——新版一律由已是 exec form 的 LATEST 複製 ⇒ 這個數字不該變大，"
            "上升代表有人真的改了凍結面（Copy-on-Evolve 明文禁止），或 LATEST 解析壞掉"
            "把活躍那份算了進來"
            if len(found) > want else
            "下降——請同一次變更把 hook_wiring.FROZEN_SHELL_FORM_MAX 下修到實測值，"
            "餘裕＝日後無聲加回去的破口")
    return [f"凍結面（非 LATEST 各版）仍是 shell form 的 settings 實測 {len(found)} 份、"
            f"基準 {want}——{verb}。清單：{found}"]


def shell_form_census_problems(counts: dict[str, int],
                               baseline: dict[str, int] | None = None) -> list[str]:
    """shell form 普查的相等判準（純函式；空＝通過）。"""
    want = SHELL_FORM_CENSUS if baseline is None else baseline
    problems: list[str] = []
    for rel in sorted(set(counts) | set(want)):
        if rel not in want:
            problems.append(
                f"{rel}：活躍 settings 檔出現在掃描面卻不在 SHELL_FORM_CENSUS——"
                f"新的 settings 檔必須顯式入表（實測 {counts[rel]} 條 shell form），"
                "否則「這一份轉了沒有」對所有機械物隱形")
        elif rel not in counts:
            problems.append(f"{rel}：在普查表內卻掃不到——射程疑似縮小（基準 {want[rel]}）")
        elif counts[rel] != want[rel]:
            verb = ("退回 shell form（該份的 hook 閃窗回來了）"
                    if counts[rel] > want[rel]
                    else "已轉掉一部分卻沒同步下修基準（餘裕＝日後無聲加回去的破口）")
            problems.append(
                f"{rel}：shell form 條目實測 {counts[rel]}、基準 {want[rel]}——{verb}。"
                "請同一次變更改 tools/lib/hook_wiring.SHELL_FORM_CENSUS")
    return problems
