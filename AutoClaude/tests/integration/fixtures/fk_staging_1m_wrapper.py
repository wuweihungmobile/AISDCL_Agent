"""tests/integration/fixtures/fk_staging_1m_wrapper.py — F-05（SD_Improving_09 W0）。

ADR-SD09-001 §2.3 紅線 ❌21 三項齊備之一：
  將既有 `tools/sd06_w3_staging_dryrun.sh` 包裝成 Python 介面，供 W4/W5 整合測試
  以及 DBA / Tech Lead pre-flight check 統一呼叫。

設計原則：
  - 純 thin wrapper：不重寫 SOP 邏輯，僅組裝環境變數 + subprocess 呼叫
  - 無 PG 環境時 graceful return `{"status": "skipped", "reason": ...}`（不 raise）
  - 預設 dry_run=True；實際 staging 演練須 caller 明確傳 dry_run=False
  - LOC ≤ 150（data tier）

對應：
  - tools/sd06_w3_staging_dryrun.sh §0~§10
  - docs/05_development/SD06_FK_DryRun_Report.md §1~§5
  - tests/contract/test_fk_staging_wrapper.py（≥ 2 case：no_pg + DSN 解析）
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _ROOT / "tools" / "sd06_w3_staging_dryrun.sh"

# R69 後續（DEF-101-753）：bash 解析改走 monorepo 根層既有單一真相源
# `tools/integration_gate_core.py::find_git_bash()`（port 自 tools/lib/Find-GitBash.ps1），
# 不在本檔另寫第二份探測。原本 `shutil.which("bash")` + argv[0] 寫死字面值 `"bash"`
# 有兩層問題：① Windows 上 `subprocess` 以 CreateProcess 解析裸名，其搜尋順序把
# `C:\Windows\System32` 排在 PATH **之前** ⇒ 就算 PATH 上有 Git Bash 也一定命中 WSL
# 啟動器；② `shutil.which` 無 System32 段排除，於是 `_has_pg_environment()` 會把「只有
# WSL 佔位版」誤判為環境齊備，本 wrapper 遂回報 `failed`（而非誠實的 `skipped`）。
sys.path.insert(0, str(_ROOT.parent / "tools"))
import integration_gate_core as _gate  # noqa: E402


def _resolve_dsn(explicit: str | None) -> str | None:
    """DSN 解析優先序：explicit > AUTOCLAUDE_DB_DSN > AUTOCLAUDE_PG_DSN（deprecated）。"""
    if explicit:
        return explicit
    return os.environ.get("AUTOCLAUDE_DB_DSN") or os.environ.get("AUTOCLAUDE_PG_DSN")


def _has_pg_environment(dsn: str | None) -> tuple[bool, str]:
    """判定本機是否具備 PG 演練環境。

    Returns: (ok, reason) — ok=False 時 reason 描述缺哪一項
    """
    if not dsn:
        return False, "no_pg_env: DSN 未設定（檢查 AUTOCLAUDE_DB_DSN）"
    if not _SCRIPT.exists():
        return False, f"no_pg_env: 缺 wrapper 腳本 {_SCRIPT}"
    if _gate.find_git_bash() is None:
        return False, "no_pg_env: 找不到可用的 bash（Windows 需 Git for Windows）"
    if shutil.which("psql") is None:
        return False, "no_pg_env: psql 不存在於 PATH"
    return True, "ok"


def fk_staging_1m_dryrun(
    pg_dsn: str | None = None,
    *,
    rows: int = 1_000_000,
    dry_run: bool = True,
) -> dict[str, Any]:
    """1M 列 FK staging dry-run wrapper（F-05 / ADR-SD09-001 §2.3）。

    Args:
        pg_dsn: PG DSN；未指定時依序讀 AUTOCLAUDE_DB_DSN / AUTOCLAUDE_PG_DSN
        rows: seed 列數（預設 100 萬；測試可降為 10000）
        dry_run: True 僅 echo 將執行的步驟；False 真正下 alembic upgrade

    Returns:
        dict 含以下欄位：
          - status: "ok" / "skipped" / "failed"
          - reason: status != "ok" 時的解釋字串
          - rows: 實際傳入的 rows
          - dry_run: True / False
          - dsn_masked: 遮罩過密碼的 DSN（status == "ok" 時）
          - returncode: subprocess 退出碼（status == "ok" / "failed" 時）
          - stdout_tail: stdout 末 30 行（debug 用，dry_run 時為步驟摘要）

    Safety：
      - 無 PG 環境（DSN 缺 / psql 缺 / bash 缺 / 腳本缺）→ skipped 不 raise
      - dry_run=True 為預設，避免測試環境誤觸 staging
    """
    dsn = _resolve_dsn(pg_dsn)
    ok, reason = _has_pg_environment(dsn)
    if not ok:
        return {"status": "skipped", "reason": reason, "rows": rows, "dry_run": dry_run}

    env = dict(os.environ)
    env["AUTOCLAUDE_DB_DSN"] = dsn  # type: ignore[assignment]
    env["SEED_ROWS"] = str(rows)
    env["PYTHONUTF8"] = "1"

    cmd = [str(_gate.find_git_bash()), str(_SCRIPT)]
    if not dry_run:
        cmd.append("--execute")

    try:
        result = subprocess.run(
            cmd,
            cwd=str(_ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3600,
        )
    except subprocess.TimeoutExpired:
        return {"status": "failed", "reason": "timeout", "rows": rows, "dry_run": dry_run}
    except OSError as exc:
        return {"status": "failed", "reason": f"os_error: {exc}", "rows": rows, "dry_run": dry_run}

    tail_lines = (result.stdout or "").splitlines()[-30:]
    masked = (dsn or "").replace(
        (dsn or "").split("@")[0].split("//")[-1] if dsn and "@" in dsn else "",
        "***",
    )
    return {
        "status": "ok" if result.returncode == 0 else "failed",
        "reason": "ok" if result.returncode == 0 else f"exit_{result.returncode}",
        "rows": rows,
        "dry_run": dry_run,
        "dsn_masked": masked,
        "returncode": result.returncode,
        "stdout_tail": "\n".join(tail_lines),
    }


__all__ = ["fk_staging_1m_dryrun"]
