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

# DEF-82-001/DEF-101-069/154 家族慣例：報表含 ✅/❌ 等非 ASCII，Windows cp950 console
# 直接 print 會 UnicodeEncodeError 中斷（連 PASS 路徑也炸）；stdout + stderr 皆強制 utf-8。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, OSError):
        pass

dsn = os.environ.get("AUTOCLAUDE_DB_DSN") or os.environ.get("AUTOCLAUDE_PG_DSN")
if not dsn:
    print(
        "[ERROR] 請設定環境變數 AUTOCLAUDE_DB_DSN（含 ?sslmode=require）後再執行。\n"
        "  範例：AUTOCLAUDE_DB_DSN='postgresql+asyncpg://user:pass@host/db?sslmode=require' "
        "python tools/check_both_mode_metrics.py",
        file=sys.stderr,
    )
    sys.exit(1)

# 刻意延遲 import：先做 DSN 環境變數檢查並 fail-fast，避免缺少必要設定時仍載入
# 這兩個較重的模組。
from autoclaude.utils.config import StorageConfig  # noqa: E402, I001
from autoclaude.infra.repositories.factory import build_state_repository  # noqa: E402

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
