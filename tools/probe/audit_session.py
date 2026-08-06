#!/usr/bin/env python3
"""每輪收尾的 session 逐字稿稽核器 —— PowerShell 工具面第一個觀測者。

WHY（本輪掃描的立案量測）
--------------------------
「Windows 上常犯低級錯誤」的機械層根因不是紀律不夠：本輪逐字稿實測顯示，
**有觀測者的那條規則違規 1 次且被當場擋下，沒有觀測者的那些規則違規率 20~35%**。
而整個 PowerShell 工具面在本輪之前**零觀測者**——鐵律二（禁裸 cd）、鐵律四
（宣稱先於查證）、以及「在對的 shell 裡現寫一段沒驗過的碼」，這三類的違規面
全部在**指令字串的內容**裡，而那個字串從來不會變成 repo 裡的檔案，於是全庫
所有靜態掃描器結構上都看不見它們。

但它們並非不可觀測：Claude Code 把每一次工具呼叫逐字寫進 session 逐字稿
（PreToolUse payload 的 `transcript_path` 欄就是那份檔案的權威路徑，本輪以
一支拋棄式 dump hook 實測確認）。repo 內此前**零消費者** ⇒ 這把「徹底解法」
從「要改 Claude Code」降級成「寫一支讀 jsonl 的稽核腳本」。本檔就是那支。

🔴 邊界：只能當量測器，不得接成閘門
------------------------------------
逐字稿是 **untracked、機器本地、隨時會被清掉**的資料。所以本檔：
  · **只能當每輪收尾的量測器**——跑一次、把四個數字與宣稱清單記進帳本；
  · **不得接成 push 閘門或 CI 閘門**。別台機器（或清過快取的同一台）上那個
    目錄根本不存在，接成硬閘在結構上恆紅，而恆紅的閘門會被整個關掉，比沒有
    鎖更糟（本 repo 的 ARCH-R59-NB4 判例逐字記載過這件事）。

它自己失效的偵測：**帶 command 的 shell 呼叫數為 0 ⇒ fail-loud（rc=1）**。
掃描面崩塌（目錄搬家／欄位改名／正則失效）不得靜默通過成「本輪零違規」——
那個失效方向看起來正好像「變乾淨了」，比紅更危險。

判準的性質（誠實劃界）
----------------------
· 四個計數是**字串形態偵測**：量的是「出現過幾次這種寫法」，不是「有幾次真的
  造成了錯誤結果」。數量級可信，**確切值不可被引用成常數**。
· 宣稱對帳是**啟發式**：比對一句宣稱與它前面 N 個 tool_result 的內容有無可佐證
  字樣。它抓得到「完全沒有對應輸出的宣稱」，抓不到「有輸出但輸出被誤讀」。
  列出的每一筆都是**待人工看一眼的線索，不是判決**。

用法
----
    python tools/probe/audit_session.py                 # 本專案全部 session
    python tools/probe/audit_session.py --json
    python tools/probe/audit_session.py --transcript <某支 .jsonl>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _stdio_utf8  # noqa: E402,F401  （side effect：強制 stdout/stderr 為 UTF-8）

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: 帶 `command` 欄、會落進本稽核射程的工具。
SHELL_TOOLS = ("Bash", "PowerShell")

#: 指令字串的形態偵測式。鍵即報表欄名，勿改動（帳本會引用）。
COMMAND_PATTERNS: dict[str, re.Pattern[str]] = {
    # 讀 rc 時接了管線：pwsh 7.x 提前中斷管線時不更新 $LASTEXITCODE（保留前值），
    # PS 5.1 則寫入 -1 —— 兩個方向都讓 rc 不可信，且「真紅被讀成綠」是其中一種。
    "rc-after-pipe": re.compile(
        r"\|[^\n]*?(Select-Object|Select-String|Out-\w+|Format-\w+|Sort-Object"
        r"|Measure-Object|ForEach-Object|Where-Object|head|tail|findstr)"
        r"[^\n]*\n?[^\n]*LASTEXITCODE",
        re.IGNORECASE,
    ),
    # 現寫的迴圈／範圍展開：沒有任何測試看過這段碼，寫錯了只會表現成「數字怪怪的」。
    "inline-loop": re.compile(
        r"\b(foreach\s*\(|ForEach-Object|for\s*\(\s*\$)", re.IGNORECASE
    ),
    # 鐵律二：PowerShell 工具的 cwd 跨呼叫持續，裸 cd 之後的相對路徑全部會找錯地方。
    "naked-cd": re.compile(r"(?m)(?:^|;)\s*(cd|Set-Location)\b\s+(?!-)", re.IGNORECASE),
    # 裸 bash：Get-Command bash 解析到 system32 的 WSL 佔位版，且反斜線分隔符被吃掉。
    "bare-bash-sh": re.compile(r"(?m)(?<![\w/\\'\"-])bash\s+[^\n]*\.sh"),
}

#: 助理訊息裡「我已經驗過了」形態的句子。
CLAIM_RE = re.compile(r"(全綠|已驗證|全部通過|rc\s*=\s*0|\bpassed\b|\bPASS\b)")

#: 佐證字樣：前 N 個 tool_result 內出現任一即視為該宣稱有對應輸出。
EVIDENCE_RE = re.compile(
    r"(rc\s*=\s*0|\bOK\b|\bpassed\b|All checks passed|Exit code:\s*0|✅)",
    re.IGNORECASE,
)

#: 宣稱往回看幾個 tool_result。12 是「一個工作項通常跑幾支指令」的量級。
DEFAULT_WINDOW = 12


def project_transcript_dir(repo_root: Path) -> Path:
    """`repo_root` 對應的 Claude Code 逐字稿目錄。

    slug 規則＝把路徑裡每個非英數字元換成 `-`（本機實測：`d:\\CursorProject\\
    AISDCL_Agent` → `d--CursorProject-AISDCL-Agent`）。這是**觀察到的**編碼方式，
    不是官方契約，所以 `--project-dir` 一律可覆寫，而目錄不存在時 fail-loud。
    """
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(repo_root))
    return Path.home() / ".claude" / "projects" / slug


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


def scan_transcript(path: Path, window_size: int = DEFAULT_WINDOW) -> dict:
    """單支逐字稿的量測結果（純資料，報表與 rc 由呼叫端決定）。"""
    counts = dict.fromkeys(COMMAND_PATTERNS, 0)
    tool_totals: dict[str, int] = {}
    shell_calls = 0
    window: deque[str] = deque(maxlen=window_size)
    unsupported: list[str] = []

    for rec in iter_records(path):
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
                if name not in SHELL_TOOLS or not isinstance(cmd, str) or not cmd:
                    continue
                shell_calls += 1
                for key, rx in COMMAND_PATTERNS.items():
                    if rx.search(cmd):
                        counts[key] += 1
            elif kind == "tool_result":
                window.append(_result_text(block))
            elif kind == "text" and role == "assistant":
                corpus = "\n".join(window)
                for sentence in _sentences(str(block.get("text") or "")):
                    if CLAIM_RE.search(sentence) and not EVIDENCE_RE.search(corpus):
                        unsupported.append(sentence[:200])

    return {
        "transcript": path.name,
        "tool_use_total": sum(tool_totals.values()),
        "by_tool": tool_totals,
        "shell_calls": shell_calls,
        "bash_tool_attempts": tool_totals.get("Bash", 0),
        "patterns": counts,
        "unsupported_claims": unsupported,
    }


def aggregate(results: list[dict]) -> dict:
    """跨 session 合計 —— 帳本要記的就是這一層的四個數字。"""
    totals = dict.fromkeys(COMMAND_PATTERNS, 0)
    shell_calls = 0
    bash_attempts = 0
    claims = 0
    for res in results:
        shell_calls += res["shell_calls"]
        bash_attempts += res["bash_tool_attempts"]
        claims += len(res["unsupported_claims"])
        for key, value in res["patterns"].items():
            totals[key] = totals.get(key, 0) + value
    return {
        "sessions": len(results),
        "shell_calls": shell_calls,
        "bash_tool_attempts": bash_attempts,
        "patterns": totals,
        "unsupported_claim_count": claims,
    }


def collapse_verdict(summary: dict) -> str | None:
    """`None`＝掃描面健在；回字串＝掃描面崩塌的理由（純函式，供注入自證）。"""
    if summary["sessions"] == 0:
        return ("掃不到任何 session 逐字稿——目錄不存在或已被清空。"
                "本檔是量測器不是閘門，但『量到零』與『量不到』必須分得開")
    if summary["shell_calls"] == 0:
        return ("帶 command 的 shell 呼叫數為 0 ⇒ 掃描面崩塌（欄位改名／記錄格式變更／"
                "SHELL_TOOLS 過期），不是『本輪零違規』。這個失效方向看起來像變乾淨了，"
                "比紅更危險，故 fail-loud")
    return None


def _print_report(results: list[dict], summary: dict, max_claims: int) -> None:
    for res in results:
        by_tool = res["by_tool"]
        print(f"\n### {res['transcript']}")
        print(f"  tool_use 總數: {res['tool_use_total']}  |  "
              f"Bash={by_tool.get('Bash', 0)}  PowerShell={by_tool.get('PowerShell', 0)}")
        print(f"  帶 command 的 shell 呼叫: {res['shell_calls']}")
        for key, value in res["patterns"].items():
            if not value:
                continue
            pct = 100.0 * value / res["shell_calls"] if res["shell_calls"] else 0.0
            print(f"    {key:16s} {value:4d}  ({pct:.1f}% of shell calls)")
        claims = res["unsupported_claims"]
        if claims:
            print(f"  無對應輸出的宣稱: {len(claims)}（啟發式，需人工看一眼）")
            for sentence in claims[:max_claims]:
                print(f"    · {sentence}")
            if len(claims) > max_claims:
                print(f"    …另有 {len(claims) - max_claims} 句（--max-claims 可調）")

    print("\n### 合計（帳本要記的四個數字）")
    print(f"  shell 呼叫數          {summary['shell_calls']}")
    print(f"  rc-after-pipe 數      {summary['patterns']['rc-after-pipe']}")
    print(f"  inline 迴圈數         {summary['patterns']['inline-loop']}")
    print(f"  Bash 工具嘗試數       {summary['bash_tool_attempts']}")
    print(f"  （另）裸 cd           {summary['patterns']['naked-cd']}")
    print(f"  （另）裸 bash + .sh   {summary['patterns']['bare-bash-sh']}")
    print(f"  無對應輸出的宣稱      {summary['unsupported_claim_count']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project-dir", help="逐字稿目錄（覆寫 slug 推導）")
    parser.add_argument("--transcript", action="append", default=[],
                        help="直接指定一支 .jsonl（可重複）")
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW,
                        help=f"宣稱往回看幾個 tool_result（預設 {DEFAULT_WINDOW}）")
    parser.add_argument("--max-claims", type=int, default=10)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    if args.transcript:
        paths = [Path(p) for p in args.transcript]
    else:
        base = Path(args.project_dir) if args.project_dir else \
            project_transcript_dir(_REPO_ROOT)
        paths = sorted(base.glob("*.jsonl")) if base.is_dir() else []

    results = [scan_transcript(p, args.window) for p in paths if p.is_file()]
    summary = aggregate(results)
    verdict = collapse_verdict(summary)

    if args.as_json:
        print(json.dumps({"sessions": results, "summary": summary,
                          "collapse_verdict": verdict},
                         ensure_ascii=False, indent=2))
    else:
        _print_report(results, summary, args.max_claims)
        if verdict:
            print(f"\n❌ {verdict}")

    return 1 if verdict else 0


if __name__ == "__main__":
    sys.exit(main())
