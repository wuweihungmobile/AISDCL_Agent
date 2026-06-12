"""
dummy_cli.py — 模擬目標 CLI 工具（Mock-First 測試用）

行為：
  1. 啟動後印出歡迎訊息，進入互動迴圈。
  2. 透過 input() 等待指令輸入（stdin）。
  3. 模擬 1-2 秒處理延遲。
  4. 機率性觸發「授權請求 (Y/n)」提示；只接受 'y' 或 'Y' 才繼續。
  5. 根據指令輸出對應的成功 Keyword（stdout）或錯誤訊息（stderr）。
  6. 收到 'exit' 或 'quit' 指令時正常退出。

注意：啟動時設定 stdout 為 line-buffered，確保每行立即 flush 給父程序。

執行方式（建議用 -u 強制無緩衝）：
  python -u dummy_cli.py
"""
from __future__ import annotations

import random
import sys
import time

# 啟動時設定 stdout line-buffered，避免父程序讀取時卡在緩衝區
sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
sys.stderr.reconfigure(line_buffering=True)  # type: ignore[attr-defined]

# 指令→成功 Keyword 對照表
COMMAND_MAP: dict[str, str] = {
    "step1": "[INIT_DONE]",
    "step2": "[TEST_CREATED]",
    "step3": "[TASK_COMPLETE]",
    "ping":  "[PONG]",
}

# 需要授權才能執行的指令
AUTH_REQUIRED_CMDS: set[str] = {"step2", "step3"}

# 隨機觸發授權的機率（0.0 = 從不，1.0 = 永遠）
AUTH_RANDOM_PROB: float = 0.6


def _request_auth() -> bool:
    """顯示授權提示，回傳使用者是否確認。"""
    print("This action requires authorization. Proceed? (Y/n)", flush=True)
    try:
        answer = input().strip()
    except EOFError:
        return False
    return answer.lower() == "y"


def _handle_command(cmd: str) -> None:
    """處理單一指令，輸出結果到 stdout 或 stderr。"""
    cmd = cmd.strip()
    if not cmd:
        return

    if cmd in ("exit", "quit"):
        print("[GOODBYE]", flush=True)
        sys.exit(0)

    # 模擬處理延遲
    delay = random.uniform(1.0, 2.0)
    time.sleep(delay)

    # 授權檢查：指定指令機率性觸發，其他指令也有小機率
    needs_auth = (
        cmd in AUTH_REQUIRED_CMDS
        or random.random() < AUTH_RANDOM_PROB
    )
    if needs_auth:
        if not _request_auth():
            print(f"ERROR: Authorization denied for command '{cmd}'", file=sys.stderr, flush=True)
            return

    # 執行指令
    if cmd in COMMAND_MAP:
        keyword = COMMAND_MAP[cmd]
        print(f"Executing '{cmd}'... done", flush=True)
        print(keyword, flush=True)
    else:
        print(
            f"ERROR: Unknown command '{cmd}'. "
            f"Valid commands: {', '.join(COMMAND_MAP)}",
            file=sys.stderr,
            flush=True,
        )


def main() -> None:
    print("DummyCLI v1.0 ready — waiting for commands...", flush=True)

    while True:
        try:
            cmd = input()
        except EOFError:
            # 父程序關閉了 stdin pipe
            print("[EOF_RECEIVED]", flush=True)
            break
        except KeyboardInterrupt:
            print("[INTERRUPTED]", flush=True)
            break

        _handle_command(cmd)


if __name__ == "__main__":
    main()
