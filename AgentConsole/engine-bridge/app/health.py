"""GET /health/deep：深度探針（契約 v1.2 §3.1.1；QA DEF-AC-003，P1）。

為什麼要有它：`/health` 只證明「Bridge 行程活著、引擎可匯入」。Docker 映像曾經沒有 `git`
（引擎內共 11 處 subprocess 呼叫 git，開機自檢 `boot_self_check` 是其中之一）——容器永遠 healthy、
任何批次卻一律 FAILED（`FileNotFoundError: 'git'`）。深度探針把「引擎真正依賴的外部條件」逐項實測，
供容器編排的 healthcheck 使用；console-api 的探測環仍打 `/health`（本端點會 spawn 子行程、寫檔，
不適合每 30 秒打）。

四項檢查，任一失敗＝整體 degraded（HTTP 503）：
  git         以 subprocess 執行 `git --version`，逾時 5 秒（行程環境與引擎相同，PATH 也相同）。
  autoclaude  `import autoclaude`。
  workspace   在 ENGINE_WORKSPACE 內建立並刪除一個暫存檔（可寫）。
  db          只有設了 BRIDGE_DB_DSN 才 ping；沒設時 `ok` 為 null（不算失敗）。

Windows 行為＝`git` 由 CreateProcess 依 PATH 解析（找不到同樣是 FileNotFoundError）；spawn 參數走
`procutil.popen_platform_kwargs()`（CREATE_NO_WINDOW 等，與引擎 spawn 同一個來源）。
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from . import procutil
from .settings import Settings

#: `git --version` 的逾時秒數（契約 §3.1.1：5 秒）。
GIT_TIMEOUT_SECONDS = 5

Check = dict[str, Any]


def check_git() -> Check:
    try:
        proc = subprocess.run(
            ["git", "--version"], stdin=subprocess.DEVNULL, capture_output=True,
            encoding="utf-8", errors="replace", timeout=GIT_TIMEOUT_SECONDS, check=False,
            **procutil.popen_platform_kwargs())
    except FileNotFoundError:
        return {"ok": False, "reason": "找不到 git 執行檔"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": f"git --version 逾時（{GIT_TIMEOUT_SECONDS} 秒）"}
    except OSError as exc:
        return {"ok": False, "reason": f"無法執行 git：{exc}"}
    version = (proc.stdout or "").strip()
    if proc.returncode != 0 or not version:
        detail = (proc.stderr or "").strip()[:200]
        reason = f"git --version 回傳 {proc.returncode}" + (f"：{detail}" if detail else "")
        return {"ok": False, "reason": reason}
    return {"ok": True, "version": version}


def check_autoclaude() -> Check:
    try:
        import autoclaude
    except ImportError as exc:
        return {"ok": False, "reason": f"無法匯入 autoclaude：{exc}"}
    return {"ok": True, "version": str(getattr(autoclaude, "__version__", "unknown"))}


def check_workspace(workspace: Path) -> Check:
    """建立並刪除一個暫存檔：只看「存在且可寫」不夠（唯讀掛載、磁碟滿、權限不對都會讓引擎寫不出檔）。"""
    try:
        fd, name = tempfile.mkstemp(prefix=".health-", suffix=".tmp", dir=workspace)
        os.close(fd)
        os.unlink(name)
    except OSError as exc:
        return {"ok": False, "reason": f"工作區不可寫：{exc}"}
    return {"ok": True}


def check_db(db: Any | None) -> Check:
    if db is None:                       # 純檔案模式：沒有 DB 可 ping，不算失敗
        return {"ok": None}
    try:
        alive = bool(db.ping())
    except Exception as exc:             # noqa: BLE001 — 探針自己不得拋例外（那會變成 500 而不是 503）
        return {"ok": False, "reason": f"DB ping 例外：{exc}"}
    return {"ok": True} if alive else {"ok": False, "reason": "DB 無法連線（SELECT 1 失敗）"}


def deep_health(cfg: Settings, db: Any | None) -> tuple[int, dict[str, Any]]:
    """回傳 (HTTP 狀態, 本文)。200＝`status=ok`；503＝`status=degraded` 並附頂層 `reason`。"""
    checks: dict[str, Check] = {
        "git": check_git(),
        "autoclaude": check_autoclaude(),
        "workspace": check_workspace(cfg.engine_workspace),
        "db": check_db(db),
    }
    failed = [f"{name}: {check['reason']}" for name, check in checks.items()
              if check["ok"] is False]
    if not failed:
        return 200, {"status": "ok", "checks": checks}
    return 503, {"status": "degraded", "reason": "；".join(failed), "checks": checks}
