"""C6 both 模式監控腳本 — 執行確認 dual-write metrics 全為零。

用法：
    AUTOCLAUDE_DB_DSN="postgresql+asyncpg://user:pass@host/db?sslmode=require" \
        python tools/check_both_mode_metrics.py
通過條件（C6）：
    dual_write_failure   == 0
    shadow_drift_detected == 0
    shadow_load_failure  == 0

R-P6-01/02（2026-05-15）：改用 AUTOCLAUDE_DB_DSN env var，移除 hardcoded credentials。
"""
import os
import sys

dsn = os.environ.get("AUTOCLAUDE_DB_DSN") or os.environ.get("AUTOCLAUDE_PG_DSN")
if not dsn:
    print(
        "[ERROR] 請設定環境變數 AUTOCLAUDE_DB_DSN（含 ?sslmode=require）後再執行。\n"
        "  範例：AUTOCLAUDE_DB_DSN='postgresql+asyncpg://user:pass@host/db?sslmode=require' "
        "python tools/check_both_mode_metrics.py",
        file=sys.stderr,
    )
    sys.exit(1)

from autoclaude.utils.config import StorageConfig
from autoclaude.infra.repositories.factory import build_state_repository

cfg = StorageConfig(
    mode="both",
    db_dsn=dsn,
    dual_write_strict=True,
    dual_read_resolution="fail_loud",
)

repo = build_state_repository(".autoclaude_checkpoints", cfg)

if not hasattr(repo, "metrics"):
    print("[ERROR] Repository does not have metrics — not DualStateRepository?")
    sys.exit(1)

m = repo.metrics.as_dict()
print("=== C6 Dual-Write Metrics ===")
for k, v in m.items():
    status = "✅" if v == 0 else "❌"
    print(f"  {status} {k}: {v}")

failures = {k: v for k, v in m.items() if v != 0 and k != "dual_write_success"}
if failures:
    print(f"\n[FAIL] {len(failures)} metric(s) non-zero: {list(failures.keys())}")
    sys.exit(1)
else:
    print("\n[PASS] All C6 gate metrics are zero.")
