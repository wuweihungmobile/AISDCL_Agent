"""FC：研究面的 fake claude——可注入故障的 `claude -p <prompt> --output-format json` 替身。

與產品 `aisdlc-mock-claude` 的研究劇本模式共用同一份劇本格式（`scripts/mock_claude_script_*.json`；
TCS §5.2），並共用 `app.mock_claude` 的劇本讀取、路徑檢查與寫檔函式（同一份知識只有一個家）；FC 另外
支援故障注入（每個劇本步驟可加以下鍵，全部選填；「第幾次呼叫」＝同一 `(role, round)` 被呼叫的次數，
由 `FAKE_CLAUDE_STATE` 指向的 JSON 檔計數，沒設則恆為第 1 次）：

  attempts            清單；第 N 次呼叫用第 N 項（超過就用最後一項）覆寫 writes／delay／result／
                      usage_input_tokens／exit_code——例：前兩次寫出無效的審查 JSON、第三次才寫合法的
  delay               睡眠秒數（測試逾時：值大於步驟牆鐘）
  result              輸出的 `result` 文字（例：額度訊息 `Claude usage limit reached|<epoch>`）
  usage_input_tokens  回報的 input_tokens（引擎以 usage 與 contextWindow 推 context%：Token Guard）
  exit_code           行程結束碼

環境變數：`MOCK_CLAUDE_RESEARCH_SCRIPT`（劇本路徑；必設）、`MOCK_CLAUDE_TRACE`（每次呼叫 append 一行
JSON：role／round／attempt／環境鍵名／`FAKE_CLAUDE_WATCH` 指名的字串是否出現在任何環境值中）、
`FAKE_CLAUDE_STATE`（計數檔）、`FAKE_CLAUDE_WATCH`（JSON 字串清單；只回報命中與否，不記環境值）。

啟動器：`make_launcher(目錄)` 在該目錄建一個可當 `claude.command` 的單一可執行檔（POSIX 為 `sh`
殼、Windows 為 `.cmd` shim——與真 claude 的 npm shim 同一條引擎啟動路徑）。
"""
from __future__ import annotations

import json
import os
import stat
import sys
import time
from pathlib import Path
from typing import Any

from app.mock_claude import (
    ScriptError,
    apply_writes,
    find_step,
    load_research_script,
    prompt_role_round,
    result_payload,
)

SCRIPT_ENV = "MOCK_CLAUDE_RESEARCH_SCRIPT"
STATE_ENV = "FAKE_CLAUDE_STATE"
WATCH_ENV = "FAKE_CLAUDE_WATCH"
TRACE_ENV = "MOCK_CLAUDE_TRACE"
FAULT_KEYS = ("writes", "delay", "result", "usage_input_tokens", "exit_code")


def make_launcher(directory: Path) -> str:
    """在 `directory` 建 FC 的啟動器並回傳其絕對路徑（`claude.command` 是單一可執行檔、不做
    shlex 切分）。"""
    directory.mkdir(parents=True, exist_ok=True)
    python, script = sys.executable, Path(__file__).resolve()
    if sys.platform == "win32":
        launcher = directory / "fake-claude.cmd"
        launcher.write_text(f'@echo off\r\n"{python}" "{script}" %*\r\n', encoding="utf-8",
                            newline="")
    else:
        launcher = directory / "fake-claude"
        launcher.write_text(f'#!/bin/sh\nexec "{python}" "{script}" "$@"\n', encoding="utf-8",
                            newline="\n")
        launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return str(launcher)


def _prompt(argv: list[str]) -> str:
    if "-p" in argv and argv.index("-p") + 1 < len(argv):
        return argv[argv.index("-p") + 1]
    return ""


def _bump(key: str) -> int:
    """這個 `(role, round)` 第幾次被呼叫（含這一次）；沒有計數檔＝恆為 1。"""
    state_path = os.environ.get(STATE_ENV, "")
    if not state_path:
        return 1
    path = Path(state_path)
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    state[key] = int(state.get(key, 0)) + 1
    path.write_text(json.dumps(state), encoding="utf-8", newline="\n")
    return int(state[key])


def _effective(step: dict[str, Any], attempt: int) -> dict[str, Any]:
    merged = {key: step[key] for key in FAULT_KEYS if key in step}
    attempts = step.get("attempts") or []
    if attempts:
        merged |= attempts[min(attempt, len(attempts)) - 1]
    return merged


def _trace(role: str, round_no: int, attempt: int) -> None:
    trace = os.environ.get(TRACE_ENV, "")
    if not trace:
        return
    watch = json.loads(os.environ.get(WATCH_ENV, "[]") or "[]")
    values = [v for k, v in os.environ.items() if k != WATCH_ENV]     # 觀察清單本身不算洩漏
    entry = {"pid": os.getpid(), "role": role, "round": round_no, "attempt": attempt,
             "cwd": str(Path.cwd()), "env_keys": sorted(os.environ),
             "pythonpath": os.environ.get("PYTHONPATH"),
             "watch_hits": [w for w in watch if any(w in v for v in values)]}
    with open(trace, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run(argv: list[str]) -> int:
    if "--version" in argv:
        sys.stdout.write("0.0.0-fake (fake claude)\n")
        return 0
    prompt = _prompt(argv)
    try:
        doc, script_dir = load_research_script(os.environ.get(SCRIPT_ENV, ""))
        role, round_no = prompt_role_round(prompt)
        step = find_step(doc, role, round_no)
        attempt = _bump(f"{role}:{round_no}")
        fault = _effective(step, attempt)
        _trace(role, round_no, attempt)
        if fault.get("delay"):
            time.sleep(float(fault["delay"]))
        written = apply_writes(fault.get("writes", []), script_dir, Path.cwd())
    except ScriptError as exc:
        sys.stderr.write(f"fake claude：{exc}（argv={argv!r}）\n")
        return 2
    text = str(fault.get("result") or f"fake claude 完成（role={role} round={round_no} "
                                      f"attempt={attempt}）：寫出 {len(written)} 個檔案。")
    payload = result_payload(text)
    if fault.get("usage_input_tokens"):
        payload["usage"]["input_tokens"] = int(fault["usage_input_tokens"])
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    return int(fault.get("exit_code") or 0)


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
