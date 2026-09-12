#!/usr/bin/env python
"""Claude Code status line 進料器（DEF-200-275 第七輪 D32-1，官方介面 code.claude.com/
docs/en/statusline）。

WHY
---
兩層 context 守衛（根層 `.claude/hooks/context_budget_guard.py`／SDD
`context_window.py`）分子讀逐字稿 usage（真實），但分母鏈裡沒有一階接得到 harness
自己回報的真實容量——status line 是 Claude Code 唯一把「容量＋用量」一起交給第三方
的官方管道：settings 的 `statusLine` 每則 assistant 訊息、`/compact` 後、
`refreshInterval` 到期時以 stdin 餵一份 JSON（頂層鍵含 `session_id`／`model`／
`context_window.{context_window_size,total_input_tokens,total_output_tokens,
used_percentage,remaining_percentage,current_usage{...}}`／`exceeds_200k_tokens`）。

本檔只做兩件事：① 把這份 JSON 原子寫進 feed 檔（`context_feed_path()`，兩層守衛各自
複製一份同名函式去讀，見 D32-2／D32-3）；② 印一行 ASCII 給 status line UI 顯示。
**絕不**讓 status line 因為本檔而空白或報錯——任何例外一律吞掉、印
`ctx ? (feed error)`、exit 0（同根層守衛既有的 fail-open 紀律）。

stdlib-only：status line 的 command 走 shell 子行程，不保證這台機器的 venv 在
PATH 上，第三方套件一律不可靠。
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import _stdio_utf8  # noqa: E402,F401 — 根層 tools/ 慣例：stdout/stderr 強制 UTF-8
from _cli_flags import reject_unknown_argv  # noqa: E402 — 同目錄 SSOT，未知引數秒回拒收

#: D32-2 SSOT：feed 檔目錄。未設＝`~/.autosdd/context_feed`；檔名＝`<session_id>.json`。
#: 根層 `context_budget_guard.py`／SDD `context_window.py` 各自持有一份逐字同構的
#: `context_feed_path()`（不跨專案 import，見根 CLAUDE.md〈雙專案 monorepo〉）——本檔
#: 是三份裡的寫入端，parity 由 `tools/tests/test_context_window_parity.py` 釘住。
FEED_DIR_ENV = "AUTOSDD_CONTEXT_FEED_DIR"

#: 84%＝根層守衛 `WARN_RATIO`（同一條門檻，逐字同步；status line 不 import hook，
#: 只能複製常數——兩邊皆為 0.84 由回歸鎖釘同值）。
WARN_RATIO_PCT = 84.0


def context_feed_path(session_id: str) -> Path:
    """Feed 檔路徑（D32-2）。與兩層守衛的同名函式逐字同構——一字之差都要在 parity 現形。"""
    base = os.environ.get(FEED_DIR_ENV)
    root = Path(base) if base else Path(os.path.expanduser("~")) / ".autosdd" / "context_feed"
    return root / f"{session_id}.json"


def _atomic_write_json(path: Path, data: dict) -> None:
    """tmp＋`os.replace` 原子寫（Windows 教訓：目標檔被開著讀時 `os.replace` 短暫
    `PermissionError`，重試幾次即過；同根 CLAUDE.md〈鐵律三〉Windows 檔案鎖那格）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp{os.getpid()}")
    tmp.write_text(json.dumps(data, ensure_ascii=True), encoding="utf-8")
    last_exc: Exception | None = None
    for _ in range(5):
        try:
            os.replace(tmp, path)
            return
        except PermissionError as exc:  # pragma: no cover — Windows 專屬競態
            last_exc = exc
            time.sleep(0.05)
    tmp.unlink(missing_ok=True)
    if last_exc is not None:
        raise last_exc


def build_feed_doc(payload: dict) -> dict:
    """從官方 status line payload 抽出要落盤的子集（純函式，供測試直接餵字典）。"""
    sid = payload.get("session_id")
    if not isinstance(sid, str) or not sid.strip():
        raise ValueError("payload 缺 session_id")
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    cw = payload.get("context_window") if isinstance(payload.get("context_window"), dict) else {}
    return {
        "schema": 1,
        "session_id": sid.strip(),
        "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model": {"id": model.get("id"), "display_name": model.get("display_name")},
        "context_window": cw,
        "exceeds_200k_tokens": payload.get("exceeds_200k_tokens"),
        "version": payload.get("version"),
    }


def _fmt_tokens(value: object) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return "?"
    n = float(value)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}m"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return f"{int(n)}"


def _ascii(text: object) -> str:
    return str(text if text is not None else "?").encode("ascii", "replace").decode("ascii")


def _current_usage_sum(cw: dict) -> int | None:
    """`current_usage` 三欄和——同兩層守衛 `used_of()` 判定用的那個量（D32b-4）。
    `total_input_tokens` 不是同一個量，`ui_line()` 分子改用這個，讓 UI 數字與
    守衛的判定同源。"""
    usage = cw.get("current_usage") if isinstance(cw, dict) else None
    if not isinstance(usage, dict):
        return None
    total = 0
    seen = False
    for field in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
        value = usage.get(field)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            total += value
            seen = True
    return int(total) if seen else None


def ui_line(payload: dict) -> str:
    """`--print-settings-snippet` 之外的主路徑：一行 ASCII 給 status line 顯示。"""
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    label = _ascii(model.get("display_name") or model.get("id") or "?")
    cw = payload.get("context_window") if isinstance(payload.get("context_window"), dict) else {}
    used_pct = cw.get("used_percentage")
    if not isinstance(used_pct, (int, float)) or isinstance(used_pct, bool):
        # session 首次 API 呼叫前／`/compact` 後到下一次呼叫前，官方契約是 null。
        return f"ctx n/a | {label}"
    used = _current_usage_sum(cw)
    size = cw.get("context_window_size")
    prefix = "!" if used_pct >= WARN_RATIO_PCT else ""
    return f"{prefix}ctx {used_pct:.1f}% {_fmt_tokens(used)}/{_fmt_tokens(size)} | {label}"


def settings_snippet() -> dict:
    """可貼進 `~/.claude/settings.json` 的 `statusLine` 區塊（D32-1）。command 用**本
    checkout** 的絕對 python 與腳本路徑、POSIX 正斜線；Windows 走 Git Bash 需自行調整
    （command 走 shell，且無 exec form，跨平台差異本檔管不到，只能留言註明）。"""
    script = Path(__file__).resolve()
    python = Path(sys.executable).resolve()
    command = f"{python.as_posix()} {script.as_posix()}"
    return {
        "statusLine": {"type": "command", "command": command, "padding": 0},
        "_comment_windows": (
            "Windows 上 command 走 shell（無 exec form）：改走 Git Bash 呼叫本腳本，"
            "command 改成 Git Bash 執行檔絕對路徑（現查安裝位置，勿寫死）"
            " -lc '<python> <本腳本，正斜線>'"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    # 未知引數秒回拒收（根層守門工具契約，SSOT＝tools/_cli_flags.py；status line 本身零引數呼叫）
    rc = reject_unknown_argv("statusline_context_feed.py", args,
                             known=("--print-settings-snippet",))
    if rc is not None:
        return rc
    if "--print-settings-snippet" in args:
        print(json.dumps(settings_snippet(), ensure_ascii=True, indent=2))
        return 0
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", "replace")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("payload 不是物件")
        doc = build_feed_doc(payload)
        _atomic_write_json(context_feed_path(doc["session_id"]), doc)
        print(ui_line(payload))
    except Exception:  # noqa: BLE001 — status line 永不可因本檔而空白／報錯
        print("ctx ? (feed error)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
