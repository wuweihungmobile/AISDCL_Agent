#!/usr/bin/env python3
"""R85／P4 掃描包的**假紅普查載具**——把「這條草案判準今天會命中幾筆、其中幾筆是真陽性」
變成可重跑的量測，而不是提案裡的一句話。

🔴 **為什麼需要這一支**（R84 `DEF-200-046` 的同型教訓）：R83 為毀滅性 git 判準做過一次
假紅普查，結論「假陽性 0 筆」寫進了根 `CLAUDE.md`，但**那次普查沒有在 repo 內留下任何產物**
⇒ 交棒書要後人「用同樣的方法」為新判準做普查，結構上做不到。本檔就是那個產物：
本輪每一條草案判準的命中數、逐筆座標，下一輪重跑一次即可 diff。

🔴 **誠實劃界**：
  · 本檔**只量、不判**——它不接任何閘門的 rc，永遠 exit 0（除非自己壞掉）。
    草案判準要不要上線、上線後住哪一支鎖檔，是 P2 持有面的事，不是本檔的事。
  · 「活躍面」＝tracked `.py`，扣掉 `AISDLC_SDD/AISDLC_SDD_v*/`（Copy-on-Evolve 凍結面，
    R80 實測全庫行尾漂移約 95% 落在那裡）與 `.venv`／`__pycache__`。
    這個定義**與 `test_platform_neutral_paths.py` 的 `eol_drift_rows()` 不共用實作**，
    因為本檔是探針不是鎖；兩者若要合併是 P2 的事。
  · 命中數是**草案**判準的命中數，不是「缺陷數」。逐筆真／假陽性判讀在 findings 文件裡，
    本檔只負責把座標印出來讓那份判讀可以被複驗。

用法：
    python tools/probe/xplat_hazard_census.py                 # 全部草案，摘要
    python tools/probe/xplat_hazard_census.py --rule exe-argv # 只跑一條，印逐筆
    python tools/probe/xplat_hazard_census.py --jsonl out.jsonl
"""
from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _stdio_utf8  # noqa: E402,F401  （side effect：強制 stdout/stderr 為 UTF-8）

_REPO = Path(__file__).resolve().parents[2]

#: Copy-on-Evolve 凍結面前綴（LATEST 也含在內：本檔是探針，寧可低估活躍面也不要
#: 把凍結面的存量算進草案判準的假紅率而否決一個好判準）。
_FROZEN_PREFIXES = ("AISDLC_SDD/AISDLC_SDD_v",)
_SKIP_PARTS = {".venv", "__pycache__", "node_modules"}

# ── 詞彙表 ────────────────────────────────────────────────────────────────────
# 🔴 這兩張表是**判準本身**。改它就是重新定義量測 ⇒ 改動要當成一次變更來做
#    （同 `misstep_attribution._BUCKETS` 檔內的同一條規矩）。

#: 只有 Windows 才有的外部執行檔（argv[0] 字面）。取捨：只收「POSIX 上必定 FileNotFoundError」
#: 的那些；`git`／`python` 這種兩邊都有的一律不收。
_WIN_ONLY_EXE = {
    "schtasks", "schtasks.exe", "powershell", "powershell.exe", "pwsh.exe",
    "cmd", "cmd.exe", "reg", "reg.exe", "wmic", "wmic.exe", "tasklist",
    "tasklist.exe", "taskkill", "taskkill.exe", "sc.exe", "net.exe",
    "cscript", "cscript.exe", "wscript", "wscript.exe", "pythonw.exe",
    "where.exe", "icacls", "icacls.exe", "attrib", "attrib.exe",
}
#: 只有 POSIX 才有的外部執行檔（argv[0] 字面）。同樣只收「Windows 上必定找不到」的。
_POSIX_ONLY_EXE = {
    "launchctl", "pmset", "sw_vers", "pgrep", "pkill", "chmod", "chown",
    "ln", "uname", "id", "sudo", "which", "killall", "diskutil", "defaults",
    "osascript", "sysctl", "dscl", "codesign", "xattr", "installer",
}
#: Windows 專屬 codepage（POSIX 的 Python 也認得這些 codec 名，所以**不會拋例外**
#: ⇒ 失效表徵是「讀出亂碼」而不是崩潰，比崩潰更難看見）。
_WIN_ONLY_CODEC = {"cp950", "cp1252", "cp936", "cp932", "mbcs", "big5", "gbk", "cp437"}
#: 只在 POSIX 有語意的檔案模式位元（Windows 的 `os.chmod` 只認 read-only 旗標，
#: 其餘 bit 全部靜默丟棄 ⇒ 「設了執行位元」在 Windows 上是 no-op 而 rc=0）。
_EXEC_BITS = 0o111


def _tracked_py() -> list[str]:
    """tracked `.py` 的活躍面。

    `-z` ＋ `core.quotepath=false`（同 `tools/lib/git_paths.py` 的取數紀律：
    非 ASCII 路徑會被 C-quote 掉出掃描面，而那個失效是靜默的）。
    """
    proc = subprocess.run(
        ["git", "-c", "core.quotepath=false", "-C", str(_REPO),
         "ls-files", "-z", "--", "*.py"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
    )
    out: list[str] = []
    for rel in proc.stdout.split("\0"):
        if not rel.endswith(".py"):
            continue
        if rel.startswith(_FROZEN_PREFIXES):
            continue
        if _SKIP_PARTS & set(Path(rel).parts):
            continue
        out.append(rel)
    return out


def _argv0_literals(node: ast.Call) -> list[str]:
    """一個 `subprocess.*` 呼叫的 argv[0] 字面值（拿不到就回空——本檔只判**寫得出來**的）。"""
    if not node.args:
        return []
    first = node.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return [first.value]
    if isinstance(first, (ast.List, ast.Tuple)) and first.elts:
        head = first.elts[0]
        if isinstance(head, ast.Constant) and isinstance(head.value, str):
            return [head.value]
    return []


def _is_subprocess_call(node: ast.Call) -> bool:
    fn = node.func
    if isinstance(fn, ast.Attribute) and fn.attr in {
            "run", "Popen", "call", "check_call", "check_output"}:
        return True
    if isinstance(fn, ast.Name) and fn.id in {"run", "Popen", "check_output"}:
        return True
    return False


def _kw(node: ast.Call, name: str) -> ast.expr | None:
    for kw in node.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _exe_argv(tree: ast.AST, rel: str, src_lines: list[str]) -> list[dict]:
    """草案 R85-A：**單平台專屬外部執行檔的 argv[0] 字面**（M5 的 b8／b11 與其 mac→Win 鏡像）。

    為什麼今天沒人守：`scan_foreign_platform_api` 的詞彙表是 **Python 屬性**
    （`os.*`／`signal.*`／`ctypes.*`／`subprocess.CREATE_*`），對「送給 OS 的外部程式名」
    整族失明——那一族根本不是 Python 符號，AST 看到的只是一個字串常數。
    """
    hits: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_subprocess_call(node):
            continue
        for exe in _argv0_literals(node):
            base = Path(exe.replace("\\", "/")).name.lower()
            side = ("win-only" if base in _WIN_ONLY_EXE
                    else "posix-only" if base in _POSIX_ONLY_EXE else None)
            if side is None:
                continue
            hits.append({"rule": "exe-argv", "rel": rel, "line": node.lineno,
                         "side": side, "token": base,
                         "src": src_lines[node.lineno - 1].strip()[:130]})
    return hits


def _win_codec(tree: ast.AST, rel: str, src_lines: list[str]) -> list[dict]:
    """草案 R85-B：**顯式指名 Windows 專屬 codepage**（M5 的 b5）。

    為什麼今天沒人守：`scan_missing_encoding` 判的是「有沒有寫 `encoding=`」——
    寫了 `encoding='cp950'` 完全滿足它。兩者是相反的失效方向，同一道判準接不住。
    """
    hits: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        val = _kw(node, "encoding")
        if isinstance(val, ast.Constant) and isinstance(val.value, str):
            if val.value.lower().replace("-", "") in _WIN_ONLY_CODEC:
                hits.append({"rule": "win-codec", "rel": rel, "line": node.lineno,
                             "side": "win-only", "token": val.value,
                             "src": src_lines[node.lineno - 1].strip()[:130]})
    return hits


def _chmod_exec(tree: ast.AST, rel: str, src_lines: list[str]) -> list[dict]:
    """草案 R85-C：**`os.chmod` 設執行位元**（M5 的 a5）。

    為什麼今天沒人守：`_FOREIGN_ATTR_TABLE['os']` 收的是「POSIX 上有、Windows 上**沒有**」
    的屬性（`fork`／`killpg`／`getuid`…）＝import/attr 期就會 AttributeError 那一族。
    `os.chmod` **兩個平台都有**，所以它在那張表的判準下是合法的——而它的危害不是崩潰，
    是**靜默 no-op**：Windows 只認 read-only 旗標，`0o755` 的執行位元整批丟掉、rc=0。
    """
    hits: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if not (isinstance(fn, ast.Attribute) and fn.attr == "chmod"):
            continue
        for arg in node.args[1:]:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, int) \
                    and arg.value & _EXEC_BITS:
                hits.append({"rule": "chmod-exec", "rel": rel, "line": node.lineno,
                             "side": "posix-only", "token": oct(arg.value),
                             "src": src_lines[node.lineno - 1].strip()[:130]})
    return hits


def _shell_true(tree: ast.AST, rel: str, src_lines: list[str]) -> list[dict]:
    """草案 R85-D：**`shell=True` 站點**，並分流「指令是字面 vs 來自變數」。

    鐵律三大表那一格自陳「存量掃描結構上量不到真實危害面，真正被送進殼的指令來自
    playbook＝使用者輸入」。本規則不試圖判斷指令內容——它量的是**分母**：
    有幾個站點會把一個「非字面」的字串交給原生殼。那些才是需要**執行期契約**的入口，
    而它們是可以靜態列舉的（見 findings 的 R85-D 草案）。
    """
    hits: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_subprocess_call(node):
            continue
        val = _kw(node, "shell")
        if not (isinstance(val, ast.Constant) and val.value is True):
            continue
        first = node.args[0] if node.args else None
        kind = ("literal" if isinstance(first, ast.Constant)
                else "absent" if first is None else "non-literal")
        hits.append({"rule": "shell-true", "rel": rel, "line": node.lineno,
                     "side": kind, "token": kind,
                     "src": src_lines[node.lineno - 1].strip()[:130]})
    return hits


_RULES = {
    "exe-argv": _exe_argv,
    "win-codec": _win_codec,
    "chmod-exec": _chmod_exec,
    "shell-true": _shell_true,
}


def census(rules: list[str]) -> tuple[list[dict], int, int]:
    hits: list[dict] = []
    scanned = 0
    unparsed = 0
    for rel in _tracked_py():
        path = _REPO / rel
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text)
        except (OSError, SyntaxError, ValueError):
            unparsed += 1
            continue
        scanned += 1
        lines = text.splitlines() or [""]
        for name in rules:
            hits.extend(_RULES[name](tree, rel, lines))
    return hits, scanned, unparsed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="R85 跨平台草案判準的假紅普查載具")
    ap.add_argument("--rule", default="", help="逗號分隔；預設全部")
    ap.add_argument("--jsonl", default="", help="逐筆寫成 .jsonl 供下一輪 diff")
    ap.add_argument("--detail", action="store_true", help="印出逐筆座標")
    a = ap.parse_args(argv)

    rules = [r.strip() for r in a.rule.split(",") if r.strip()] or list(_RULES)
    unknown = sorted(set(rules) - set(_RULES))
    if unknown:
        print(f"❌ 無此規則：{unknown}；可用＝{list(_RULES)}", file=sys.stderr)
        return 2

    hits, scanned, unparsed = census(rules)
    print(f"活躍面 tracked .py＝{scanned} 支（解析失敗 {unparsed} 支，"
          f"凍結面 {_FROZEN_PREFIXES} 已排除）")
    for name in rules:
        rows = [h for h in hits if h["rule"] == name]
        by_side: dict[str, int] = {}
        for h in rows:
            by_side[h["side"]] = by_side.get(h["side"], 0) + 1
        print(f"  · {name:<12} 命中 {len(rows):>4} 筆   分流={by_side}")
    if a.detail:
        print()
        for h in sorted(hits, key=lambda x: (x["rule"], x["rel"], x["line"])):
            print(f'{h["rule"]:<11} {h["rel"]}:{h["line"]} [{h["side"]}/{h["token"]}] {h["src"]}')
    if a.jsonl:
        with open(a.jsonl, "w", encoding="utf-8") as fh:
            for h in hits:
                fh.write(json.dumps(h, ensure_ascii=False) + "\n")
        print(f"\n逐筆已寫入 {a.jsonl}（可 diff）")
    print("\n🔴 命中數 ≠ 缺陷數。逐筆真／假陽性判讀見 "
          "docs/06_quality/CrossPlatform_R85_Scan_Findings.md，本檔只負責讓它可複驗。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
