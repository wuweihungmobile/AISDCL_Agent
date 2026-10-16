"""GET /health/deep：深度探針（契約 v1.2 §3.1.1；QA DEF-AC-003，P1）。

為什麼要有它：`/health` 只證明「Bridge 行程活著、引擎可匯入」。Docker 映像曾經沒有 `git`
（引擎內共 11 處 subprocess 呼叫 git，開機自檢 `boot_self_check` 是其中之一）——容器永遠 healthy、
任何批次卻一律 FAILED（`FileNotFoundError: 'git'`）。深度探針把「引擎真正依賴的外部條件」逐項實測，
供容器編排的 healthcheck 使用；契約 v1.4（D-17）起 console-api 的探測環預設也打它
（`autoclaude.healthCheckPath`；成本是每 30 秒 spawn 一次 git、建刪一個暫存檔，
對單一 Bridge 可忽略）。

五項檢查。前四項任一失敗（`ok` 為 false）＝整體 degraded（HTTP 503）：
  git         以 subprocess 執行 `git --version`，逾時 5 秒（行程環境與引擎相同，PATH 也相同）。
  autoclaude  `import autoclaude`。
  workspace   在 ENGINE_WORKSPACE 內建立並刪除一個暫存檔（可寫）。
  db          只有設了 BRIDGE_DB_DSN 才 ping；沒設時 `ok` 為 null（不算失敗）。
第五項只當**資訊**，永遠不影響整體判定與 HTTP 狀態：
  sdd         （D-17）AISDLC_SDD 樹：沒有 SDD 目錄可用（Settings.sdd_root 為 None）＝`ok` 為
              null；設了但不是目錄、或看不出是 SDD 樹＝false；有＝true。判準見 `check_sdd`。
              為什麼不算進 503：SDD 是選用引擎，它壞了要顯示在 Console 的 SDD 卡，而不是讓
              Agent 可用率下降或誤報 AGENT_UNRESPONSIVE（console-api 的探測環與 compose 的
              healthcheck 都打這一支，503 會被當成 Bridge 不可用）。所以 `sdd.ok` 為 false 時
              整體照常 200，頂層 `reason` 也只列前四項的失敗。（契約 v1.4 §3.1.1，主控裁定）

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


#: 每個 AISDLC_SDD 版本目錄都有、而且入庫（git ls-files 可查）的入口文件。
_SDD_MARKER = "AISDLC_SDD_INIT.md"

#: 只當資訊的檢查：照常出現在 `checks` 裡，但失敗不翻轉整體判定、也不進頂層 `reason`。
_INFORMATIONAL_CHECKS = frozenset({"sdd"})


def check_sdd(sdd_root: Path | None) -> Check:
    """AISDLC_SDD 樹是否可用（D-17）。回 `{"ok", "latest", "reason"?}`：

      · `sdd_root` 為 None（沒設 SDD_ROOT、預設位置也找不到）＝`ok: null`、`latest: null`——
        Bridge 照樣能跑 AutoClaude 的批次（/sdd/version、/sdd/fsm 會回 503）。
      · 不是目錄＝false。
      · 是目錄，且（有 `build/reports/fsm` 或有版本入口文件 `AISDLC_SDD_INIT.md`）＝true，
        `latest` 為目錄名。兩者都沒有＝false（空的或掛錯的目錄，例如 compose 的唯讀掛載沒掛到
        東西）。

    這一項**只當資訊**：不論回什麼，`deep_health` 的整體判定都不看它（見模組說明）。

    為什麼入口文件也算數（主控任務書原寫「沒有 `build/reports/fsm` 就 false」）：LATEST 的
    `build/reports/` 被 git 忽略（AISDLC_SDD/.gitignore：`AISDLC_SDD_v0.30/build/reports/`），
    入庫檔數為 0，所以**全新 clone 沒有這個目錄**。FSM 狀態檔是跑過 SDD runtime 才會產生的
    執行期產物，不是「SDD 樹有沒有掛上」的證據；入口文件才是。照字面判，Console 的 SDD 卡會
    對一份完好的全新 clone 顯示失敗。"""
    if sdd_root is None:
        return {"ok": None, "latest": None,
                "reason": "未設定 SDD_ROOT，也找不到預設位置的 AISDLC_SDD 目錄"}
    if not sdd_root.is_dir():
        return {"ok": False, "latest": None, "reason": f"SDD_ROOT 不是目錄：{sdd_root.name}"}
    has_fsm_dir = (sdd_root / "build" / "reports" / "fsm").is_dir()
    if has_fsm_dir or (sdd_root / _SDD_MARKER).is_file():
        return {"ok": True, "latest": sdd_root.name}
    # 頂層 reason 以全形分號「；」連接各項：這裡的文字不可含它。
    return {"ok": False, "latest": sdd_root.name,
            "reason": f"{sdd_root.name} 看起來不是 AISDLC_SDD 樹（沒有 {_SDD_MARKER}，也沒有 "
                      "build/reports/fsm），唯讀掛載是不是沒掛到東西？"}


def deep_health(cfg: Settings, db: Any | None) -> tuple[int, dict[str, Any]]:
    """回傳 (HTTP 狀態, 本文)。200＝`status=ok`；503＝`status=degraded` 並附頂層 `reason`。

    判定只看 git／autoclaude／workspace／db 四項；`sdd`（`_INFORMATIONAL_CHECKS`）照樣回報在
    `checks` 裡，但 `ok` 為 false 時整體仍是 200，頂層 `reason` 也不列它。"""
    checks: dict[str, Check] = {
        "git": check_git(),
        "autoclaude": check_autoclaude(),
        "workspace": check_workspace(cfg.engine_workspace),
        "db": check_db(db),
        "sdd": check_sdd(cfg.sdd_root),
    }
    failed = [f"{name}: {check['reason']}" for name, check in checks.items()
              if name not in _INFORMATIONAL_CHECKS and check["ok"] is False]
    if not failed:
        return 200, {"status": "ok", "checks": checks}
    return 503, {"status": "degraded", "reason": "；".join(failed), "checks": checks}
