"""mock_claude — 模擬 `claude -p <prompt> --output-format json` 的確定性替身（E2E／測試專用）。

為什麼 Bridge 自己帶一個，而不是用 AutoClaude/tests/fixtures/dummy_cli.py（2026-10-14 實測）：
  · AutoClaude 的 Kernel 路徑（`python -m autoclaude`）只呼叫
    `<claude.command> [旗標…] -p <prompt>`；`PlaybookTask.command` 欄位在該路徑上**零消費**。
    dummy_cli 卻是「讀 stdin 指令」的互動迴圈 ⇒ 每個步驟都會卡到 step_timeout。
  · `claude.command` 是**單一字串、不做 shlex 切分**：`python -u dummy_cli.py` 會被當成一個
    檔名而 FileNotFoundError（引擎 traceback、rc=1）⇒ 替身必須是一個**可執行檔**。
  ⇒ 本模組以 console script 形式安裝（`[project.scripts] aisdlc-mock-claude`）：
    POSIX 是 `.venv/bin/aisdlc-mock-claude`、Windows 是 `.venv\\Scripts\\aisdlc-mock-claude.exe`
    （pip／uv 產生的真 .exe 啟動器，不需要手寫 .sh／.cmd）。Docker 映像內它在 PATH 上，
    所以 `config_overrides.claude.command = "aisdlc-mock-claude"` 即可。

行為（全由環境變數控制；預設只有 0.2 秒的處理延遲，別無副作用）：
  MOCK_CLAUDE_DELAY        每次 `-p` 呼叫的處理秒數（預設 0.2）
  MOCK_CLAUDE_TRACE        若設定，每次 `-p` 呼叫 append 一行 JSON（pid／ts／prompt 頭尾／
                           keywords）到該檔，測試用它證明「哪些步驟真的被呼叫過」，
                           獨立於 Bridge 自己的帳
  MOCK_CLAUDE_FAIL_REGEX   prompt 命中此 regex 時輸出不含任何 `[KEYWORD]`（讓 evaluator 判失敗）
  MOCK_CLAUDE_IGNORE_TERM  設為 1 時忽略 SIGTERM（POSIX；用來驗證 SIGKILL 升級路徑）
輸出：單行 JSON，形狀對齊真 claude 的 `--output-format json`（含 usage／modelUsage，使引擎
能推出 context%）；`result` 內回放 prompt 中所有 `[KEYWORD]` 字樣，滿足 expected_output_regex。
`--version` 立即回覆（引擎開機自檢會探測它），不延遲、不記 trace。
"""
from __future__ import annotations

import json
import os
import re
import signal
import sys
import time
from datetime import UTC, datetime

_KEYWORD_RE = re.compile(r"\[[A-Z][A-Z0-9_]*\]")
MOCK_VERSION = "0.0.0-mock"


def _prompt_from_argv(argv: list[str]) -> str:
    # PtyExecutor 把 `-p`、prompt 放在 argv 最後：`-p` 之後的下一個引數就是 prompt。
    if "-p" in argv:
        idx = argv.index("-p")
        if idx + 1 < len(argv):
            return argv[idx + 1]
    return ""


def run(argv: list[str]) -> int:
    if "--version" in argv:
        sys.stdout.write(f"{MOCK_VERSION} (mock claude)\n")
        sys.stdout.flush()
        return 0
    if os.environ.get("MOCK_CLAUDE_IGNORE_TERM") == "1" and sys.platform != "win32":
        # Windows 行為＝終止即 TerminateProcess，本來就無法被忽略，故只在 POSIX 設。
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    prompt = _prompt_from_argv(argv)
    keywords = _KEYWORD_RE.findall(prompt)
    trace = os.environ.get("MOCK_CLAUDE_TRACE", "")
    if trace:
        with open(trace, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps({
                "pid": os.getpid(),
                "ts": datetime.now(UTC).isoformat(),
                "prompt_head": prompt[:80],
                "prompt_tail": prompt[-120:],   # 引擎只會在前面加前綴：尾端必須原樣到達
                "keywords": keywords,   # 引擎可能在 prompt 前加 global_goal 前綴：認關鍵字最穩
            }, ensure_ascii=False) + "\n")
    delay = float(os.environ.get("MOCK_CLAUDE_DELAY", "0.2") or 0)
    if delay > 0:
        time.sleep(delay)
    fail_regex = os.environ.get("MOCK_CLAUDE_FAIL_REGEX", "")
    if fail_regex and re.search(fail_regex, prompt):
        keywords = []
    payload = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "num_turns": 1,
        "result": "mock claude 完成。" + " ".join(dict.fromkeys(keywords)),
        "session_id": "mock-session",
        "total_cost_usd": 0.0,
        "usage": {
            "input_tokens": 1200,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "output_tokens": 40,
        },
        "modelUsage": {"mock-model": {"contextWindow": 200000}},
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    return 0


def main() -> None:
    """console script 入口（`aisdlc-mock-claude`）。"""
    raise SystemExit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
