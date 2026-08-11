#!/usr/bin/env python
"""指令字串語料抽取器 — 讓「判準的假紅普查」變成**可重跑**的東西（R84／`DEF-200-046`）。

用法
----
    python tools/probe/shell_command_corpus.py --summary
    python tools/probe/shell_command_corpus.py --corpus transcripts --predicate waitform \\
        --hits-only --out /tmp/waitform_census.jsonl --show 40
"""
#
# WHY 這支腳本存在（立案事實，不是整潔）
# --------------------------------------
# 根 CLAUDE.md 鐵律五自陳：「落地當回合對全庫 tracked 檔抽出的 **10,106 筆 git 指令片段**
# （去重 1,031 種）實跑該判準：命中 30 種唯一字面／254 次，逐筆人工判讀**全部是真陽性**，
# 假陽性 0 筆」。R84 獨立驗證輪去找那份產物——**repo 裡一支都沒有**：
# `grep -rn "10,106\\|10106"` 只命中 CLAUDE.md 那句宣稱本身，`tools/probe/` 當時的 5 支
# （audit_session／console_spawn_watch／misstep_attribution／reset_window_distribution／
# xplat_injection_matrix）無一產生 git 指令片段語料。
# ⇒ 交棒書要求後人「用同樣的方法」為新判準做假紅普查，那件事**結構上做不到**：沒有共同
# 母體、沒有去重規則、沒有逐筆歸屬理由，兩輪的數字不可比，而「假陽性 0」正是那些判準
# 唯一的驗收條件。
#
# CLAUDE.md 自己已經對**同一個形態**下過判決（R77 的失誤分群「沒有留下任何可重跑的產物，
# 所以『每輪重跑』這條要求結構上做不到」），並以 `tools/probe/misstep_attribution.py` 修好。
# 本檔是鐵律五／鐵律六那一側的同一個修法。
#
# 🔴 **兩個母體不能互相替代**（R84 實測，這是本檔最重要的一句）
# ------------------------------------------------------------
# · `tracked`（git 追蹤的文字檔）抓得到「寫進 repo 的指令」：腳本、workflow、文件示範。
#   **對鐵律六是錯的量測面**——那兩種形態是模型當回合現寫、送進 Bash 工具的字串，永遠
#   不會變成 repo 裡的檔案。本輪實測：tracked 面上 `waitform` 的命中**全部落在描述它們
#   的 `.md` 散文**（根 CLAUDE.md、`AutoSDD_Defect_Log.md`）與本判準自己的 docstring，
#   而 hook 結構上讀不到 `.md` ⇒ 照 tracked 面判會得到「全是假紅」的錯誤結論，
#   並因此否決一個好判準。
# · `transcripts`（逐字稿裡真的送出過的 `tool_input.command`）抓得到模型實際下過的每
#   一條指令。**這一面才是 PreToolUse hook 的真實輸入面**——hook 讀的就是這個欄位。
#
# ⇒ 判準若是 hook（PreToolUse 讀指令字串），假紅普查一律以 `transcripts` 為母體；
# `tracked` 面只用來回答另一個問題：「repo 內寫死的腳本會不會被這道 hook 擋到」。
# 兩者都留著，但**必須各自標明**，不得混成一個數字——那正是 10,106 那個數字今天無從複驗的
# 原因之一（它沒說是哪一面）。
#
# 🔴 母體大小是**量測值不是常數**
# ------------------------------
# 本檔刻意不把任何數字寫進 docstring 或任何文件當常數：`transcripts` 會隨每一次工具呼叫
# 長大，`tracked` 會隨 commit 變。要數字就現跑（`--summary`）。CLAUDE.md 那句宣稱裡的
# 10,106／1,031／30／254 應當被讀成「R83 那一刻的量測值」。
#
# 去重規則（明文，因為它決定了「唯一數」這個量）
# ----------------------------------------------
# · 鍵＝**指令字串逐字**（不 strip、不正規化空白、不折行接續）。理由：判準吃的就是逐字
#   原文，任何正規化都會讓語料與判準的輸入面不一致——而不一致的方向是「語料比真實輸入乾淨」，
#   也就是**低報假紅**。
# · 同一字串多次出現＝`occurrences` 累加，`first_source` 記第一次見到的座標（可回溯）。
# · 排序＝`(corpus, command)`，讓輸出檔可以 `diff`（兩輪之間的差異就是真的差異）。
#
# 輸出（JSONL，一列一個唯一指令）
# -------------------------------
#     {"corpus":…, "sha12":…, "occurrences":…, "first_source":…, "reason":…,
#      "command":…, "hits":{"git":[…],"waitform":[…]}}
# `reason` 是**逐筆歸屬理由**（這條字串為什麼在語料裡、從哪個欄位抽出來的），不是分類標籤。
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
sys.path.insert(0, str(_REPO_ROOT / "tools"))

# 🔴 入口點印非 ASCII（本檔的摘要與逐筆理由全是中文）⇒ 必須先武裝 UTF-8 stdio，否則
# locale 表達不了 CJK 時整段輸出變 `\uXXXX` 逃脫字面／表達得了但非 UTF-8 時是亂碼。
# 體例逐字對齊姊妹 probe（`misstep_attribution.py`／`reset_window_distribution.py`）：
# 消費既有的 `tools/_stdio_utf8` side-effect 模組，**不**在本檔再抄一份 reconfigure
# （`tools/tests/test_platform_utils_dedup.py` 的 shrink-only 棘輪守著複本數）。
# 本行是被 `tools/tests/test_subprocess_encoding_hygiene.py` 抓出來後補的，不是預先想到的。
#: 被普查的判準**一律 import 生產程式碼**，不在本檔重抄一份。抄一份的話語料會對著一個
#: 副本跑，而副本與 hook 漂移的那一天，普查結果會變成「對已經不存在的判準做的量測」。
import block_destructive_git as G  # noqa: E402

# 🔴 這兩支的**順序由 ruff isort 決定，不是由「先武裝再輸出」決定**——姊妹 probe 把
# `_stdio_utf8` 排在前面，本檔排在後面，兩者都對：上面那支 import 到底不印任何東西
# （純定義），而 `_stdio_utf8` 的 side effect 在 `main()` 印第一個字之前就已生效。
# 寫在這裡是因為讀到這裡的人會想把它搬回去，然後被 I001 擋下。
import _stdio_utf8  # noqa: E402,F401 — side effect：強制 stdout/stderr 為 UTF-8

#: `tracked` 面：只看文字檔，且**排除凍結面**（`AISDLC_SDD/AISDLC_SDD_v0.01`~`v0.29` 依
#: Copy-on-Evolve 不動 ⇒ 它們的內容不是「今天的 repo 會下的指令」，計進去只會把母體
#: 灌水成版本數的倍數）。
_TEXT_SUFFIXES = frozenset({
    ".py", ".sh", ".bash", ".ps1", ".psm1", ".yml", ".yaml", ".md", ".txt",
    ".json", ".toml", ".cfg", ".ini", ".mk", "",
})
_FROZEN_RE = re.compile(r"^AISDLC_SDD/AISDLC_SDD_v0\.(?:0[1-9]|1\d|2\d)/")

#: `tracked` 面的抽取規則：**整行**，只要該行出現任一「候選錨 token」。
#:
#: 🔴 為什麼是整行、而且錨是**判準集合的聯集**（本輪修正過一次，理由是實測的）：
#: 第一版的錨只有 git 執行檔 token、且把片段切到下一個語句分隔符為止——那讓 `waitform`
#: 在 tracked 面上恆為 **0 命中**，因為 `nohup … &` 那種行根本沒有 git token、進不了語料。
#: **零命中與「這一面很乾淨」在輸出上完全同形**，而那正是本 repo 反覆判紅的假綠。
#: ⇒ 錨改成聯集（新增判準要在這裡加一個 token，加不加得到是看得見的），片段改成整行
#: （不切 `;`／`&&`／`#`）。整行的代價誠實寫在這裡：`.md` 散文的一整行會進語料而它不是
#: 一條可執行指令——但那恰好是本檔要曝光的事實（見上方兩個母體的對照表），不是雜訊。
_ANCHOR_RE = re.compile(
    r"(?<![\w./\\-])(?:"
    r"(?:[^\s'\"]*[\\/])?git(?:\.exe)?"      # 鐵律五
    r"|nohup|disown|setsid|pgrep"            # 鐵律六 判準①③／②
    r")(?![\w.-])")

#: `transcripts` 面：這台機器上 Claude Code 的逐字稿。`*` 是**專案 slug**——刻意掃全部
#: 專案而不只當前那一個：hook 是使用者層級行為，換一個 checkout 不會換掉模型的習慣。
_TRANSCRIPT_GLOB = "*/*.jsonl"
#: 只取真的會送進 shell 的工具（＝被守的那支 hook 的 `OWN_TOOLS`，現查不寫死）。
_SHELL_TOOLS = frozenset(G.OWN_TOOLS)


def _sha12(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:12]


def tracked_fragments(repo_root: Path) -> list[tuple[str, str, str]]:
    """`tracked` 面：`(command, source, reason)`。

    走 `git ls-files -z` ＋ `core.quotepath=false`（鐵律三「git 路徑列舉」那一列的規矩：
    非 ASCII 路徑不帶這兩個旗標會被 C-quote 掉、檔案靜默掉出掃描面）。
    """
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files", "-z"],
        cwd=str(repo_root), capture_output=True, text=True, encoding="utf-8",
        errors="replace", check=False)
    rows: list[tuple[str, str, str]] = []
    for rel in out.stdout.split("\0"):
        if not rel or _FROZEN_RE.match(rel):
            continue
        path = repo_root / rel
        if path.suffix.lower() not in _TEXT_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            frag = line.strip()
            if frag and _ANCHOR_RE.search(line):
                rows.append((frag, f"{rel}:{lineno}",
                             "tracked 檔內整行（該行含判準集合聯集裡的錨 token："
                             "git 執行檔／nohup／disown/setsid／pgrep）"))
    return rows


def transcript_commands(root: Path | None = None) -> list[tuple[str, str, str]]:
    """`transcripts` 面：`(command, source, reason)`。

    逐字稿是 JSONL，每列一個事件；`assistant` 訊息的 `content` 陣列裡 `type=="tool_use"`
    且 `name` 落在 `_SHELL_TOOLS` 的那些，取 `input.command`。這**就是** PreToolUse
    payload 的 `tool_input.command`（本輪以臨時 probe 實測對照過同一個欄位）。
    壞列一律跳過並不出聲：逐字稿會被 harness 邊寫邊讀，尾列半截是常態，不是異常。
    """
    base = root or (Path(os.path.expanduser("~")) / ".claude" / "projects")
    rows: list[tuple[str, str, str]] = []
    for jsonl in sorted(base.glob(_TRANSCRIPT_GLOB)):
        try:
            text = jsonl.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if '"tool_use"' not in line:
                continue
            try:
                event = json.loads(line)
            except Exception:  # noqa: BLE001 — 尾列半截是常態
                continue
            message = event.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                if block.get("name") not in _SHELL_TOOLS:
                    continue
                command = (block.get("input") or {}).get("command")
                if isinstance(command, str) and command.strip():
                    rows.append((
                        command, f"{jsonl.parent.name}/{jsonl.name}:{lineno}",
                        f"逐字稿 assistant tool_use name={block.get('name')} 的 "
                        f"input.command＝PreToolUse payload 的 tool_input.command 同一欄位"))
    return rows


def _predicate_hits(command: str, which: str) -> dict[str, list[str]]:
    """對一條指令跑被普查的判準。**start_dir 固定為專案根**＝production 的 fail-closed 起點。"""
    hits: dict[str, list[str]] = {}
    if which in ("git", "all"):
        hits["git"] = G.destructive_git_hits(command, start_dir=str(_REPO_ROOT))
    if which in ("waitform", "all"):
        # 🔴 `run_in_background` 語料裡取不到（逐字稿的 tool_use input 有這個 key，但
        # tracked 面沒有）⇒ 普查一律以 False 跑，量的是「判準①②」那兩條。判準③ 只在
        # 旗標為真時才可能命中，把它一起打開會讓假紅數字虛高而不可比。
        hits["waitform"] = G.waitform_hits(command, run_in_background=False)
    return hits


def build(corpora: list[str], which: str) -> list[dict]:
    records: dict[tuple[str, str], dict] = {}
    for corpus in corpora:
        rows = (tracked_fragments(_REPO_ROOT) if corpus == "tracked"
                else transcript_commands())
        for command, source, reason in rows:
            key = (corpus, command)
            if key in records:
                records[key]["occurrences"] += 1
                continue
            records[key] = {
                "corpus": corpus, "sha12": _sha12(command), "occurrences": 1,
                "first_source": source, "reason": reason, "command": command,
                "hits": _predicate_hits(command, which),
            }
    return [records[k] for k in sorted(records)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__ and __doc__.splitlines()[0])
    ap.add_argument("--corpus", choices=["tracked", "transcripts", "both"], default="both")
    ap.add_argument("--predicate", choices=["git", "waitform", "all", "none"], default="all")
    ap.add_argument("--out", help="輸出 JSONL 路徑（省略＝不寫檔，只印摘要）")
    ap.add_argument("--hits-only", action="store_true", help="只輸出有命中的列")
    ap.add_argument("--show", type=int, default=0, help="印出前 N 筆命中的逐字內容供人工判讀")
    ap.add_argument("--summary", action="store_true", help="只印摘要（等同不給 --out）")
    args = ap.parse_args(argv)

    corpora = ["tracked", "transcripts"] if args.corpus == "both" else [args.corpus]
    records = build(corpora, args.predicate)
    hit_rows = [r for r in records if any(r["hits"].values())]

    for corpus in corpora:
        mine = [r for r in records if r["corpus"] == corpus]
        total = sum(r["occurrences"] for r in mine)
        print(f"[{corpus}] 母體 {total} 筆／去重後 {len(mine)} 種唯一字面")
        for name in ("git", "waitform"):
            sel = [r for r in mine if r["hits"].get(name)]
            if args.predicate in (name, "all"):
                print(f"    判準 {name}: 命中 {len(sel)} 種唯一／"
                      f"{sum(r['occurrences'] for r in sel)} 次")

    if args.show:
        for rec in hit_rows[: args.show]:
            names = ",".join(k for k, v in rec["hits"].items() if v)
            print(f"\n--- [{rec['corpus']}][{names}] {rec['first_source']}\n"
                  f"{rec['command'][:400]}")

    if args.out and not args.summary:
        payload = hit_rows if args.hits_only else records
        Path(args.out).write_text(
            "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
                    for r in payload), encoding="utf-8")
        print(f"\n寫出 {len(payload)} 列 → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
