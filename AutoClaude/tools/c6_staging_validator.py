#!/usr/bin/env python
"""tools/c6_staging_validator.py — C6 自動化 staging 驗證腳本

六個驗證階段：
  A：基本 CRUD 循環（save / load / clear）
  B：高頻壓力（N 輪 save/load，驗證累積零失敗）
  C：大 payload 邊界（50KB last_correction_prompt）
  D：多 playbook_id 模擬並發寫入
  E：PG 故障降級（壞 DSN，驗證 File 路徑仍可寫且 dual_write_failure 計數）
  G：DualMetrics 全零確認（C6 通過條件）

執行方式：
    AUTOCLAUDE_ALLOW_INSECURE_DB=1 python tools/c6_staging_validator.py          # 24h 正式驗證
    AUTOCLAUDE_ALLOW_INSECURE_DB=1 python tools/c6_staging_validator.py --quick  # ~5min 功能驗證
    AUTOCLAUDE_ALLOW_INSECURE_DB=1 python tools/c6_staging_validator.py --duration 1  # 1h 縮短版

結束後自動產出報告：
    tools/c6_report_YYYYMMDD_HHMMSS.json
"""
import argparse
import json
import logging
import os
import shutil
import signal
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

os.environ.setdefault("AUTOCLAUDE_ALLOW_INSECURE_DB", "1")

_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

#: 🔴 DSN 一律由 `--dsn` 或 `AUTOCLAUDE_DB_DSN` 提供，**檔內不留 baked-in 憑證**（R82）。
#: 原版把 `autoclaude_runtime` 的密碼寫死在這裡，且刻意拆成兩段字串——於是
#: `user:pass@host` 不在同一行，`tools/lib/secret_scan.py` 的 DSN 判準（單行 regex）
#: 對它結構上失明：commit 過得了，不等於憑證沒有入庫。
DEFAULT_DSN = os.environ.get("AUTOCLAUDE_DB_DSN")
_TEST_DIR = str(_REPO_ROOT / ".autoclaude_c6_staging")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("c6_validator")

# E402 逐行豁免（非整檔）：這三個 import 必須晚於上方兩個副作用——sys.path.insert 把
# repo 根接上 sys.path，AUTOCLAUDE_ALLOW_INSECURE_DB 須在 config 被 import 前就位。
from autoclaude.infra.repositories.factory import build_state_repository  # noqa: E402
from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint  # noqa: E402
from autoclaude.utils.config import StorageConfig  # noqa: E402

# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_cp(pid: str, step_idx: int = 0, large: bool = False) -> PlaybookCheckpoint:
    cp = PlaybookCheckpoint(
        playbook_path=pid, step_idx=step_idx, step_id=f"T{step_idx:02d}",
        total_steps=10, project="c6_test",
    )
    if large:
        cp.last_correction_prompt = "A" * 50_000
        cp.failure_history = [{"attempt": i, "err": "x" * 500} for i in range(20)]
    return cp


class PhaseResult:
    def __init__(self, name: str):
        self.name, self.passed, self.failed = name, 0, 0
        self.errors: list[str] = []
        self._t0 = time.time()
        self.elapsed = 0.0

    def ok(self):
        self.passed += 1

    def fail(self, msg: str):
        self.failed += 1
        self.errors.append(msg)
        logger.warning("    [FAIL] %s", msg)

    def done(self) -> "PhaseResult":
        self.elapsed = round(time.time() - self._t0, 2)
        return self

    @property
    def success(self) -> bool:
        return self.failed == 0

    def as_dict(self) -> dict:
        return {
            "phase": self.name, "passed": self.passed, "failed": self.failed,
            "elapsed_s": self.elapsed, "errors": self.errors,
        }


# ── Phase functions ───────────────────────────────────────────────────────────

def phase_A_basic_crud(repo) -> PhaseResult:
    """基本 CRUD 循環：save → load（驗資料）→ clear → load（驗為 None）"""
    r = PhaseResult("A_basic_crud")
    pid = f"c6a_{uuid.uuid4().hex[:8]}"
    try:
        repo.save_checkpoint(pid, _make_cp(pid, step_idx=3))
        loaded = repo.load_checkpoint(pid)
        if loaded is None:
            r.fail("save 後 load 回傳 None")
        elif loaded.step_idx != 3:
            r.fail(f"step_idx 不一致: want=3, got={loaded.step_idx}")
        else:
            r.ok()
        repo.clear_checkpoint(pid)
        if repo.load_checkpoint(pid) is not None:
            r.fail("clear 後 load 應為 None")
        else:
            r.ok()
    except Exception as e:
        r.fail(f"例外: {e}")
    return r.done()


def phase_B_high_freq(repo, cycles: int = 100) -> PhaseResult:
    """高頻壓力：N 輪 save/load，累積驗證 File+PG 一致"""
    r = PhaseResult(f"B_high_freq_{cycles}")
    pid = f"c6b_{uuid.uuid4().hex[:8]}"
    try:
        for i in range(cycles):
            idx = i % 10
            repo.save_checkpoint(pid, _make_cp(pid, step_idx=idx))
            loaded = repo.load_checkpoint(pid)
            if loaded is None or loaded.step_idx != idx:
                r.fail(f"cycle {i}: step_idx 不一致")
                break
            else:
                r.ok()
    except Exception as e:
        r.fail(f"例外: {e}")
    finally:
        try:
            repo.clear_checkpoint(pid)
        except Exception:
            pass
    return r.done()


def phase_C_large_payload(repo) -> PhaseResult:
    """大 payload 邊界：50KB last_correction_prompt 不截斷"""
    r = PhaseResult("C_large_payload")
    pid = f"c6c_{uuid.uuid4().hex[:8]}"
    try:
        repo.save_checkpoint(pid, _make_cp(pid, large=True))
        loaded = repo.load_checkpoint(pid)
        if loaded is None:
            r.fail("大 payload load 回傳 None")
        elif len(loaded.last_correction_prompt or "") < 10_000:
            r.fail(f"payload 截斷: len={len(loaded.last_correction_prompt or '')}")
        else:
            r.ok()
    except Exception as e:
        r.fail(f"例外: {e}")
    finally:
        try:
            repo.clear_checkpoint(pid)
        except Exception:
            pass
    return r.done()


def phase_D_multi_playbook(repo, count: int = 10) -> PhaseResult:
    """多 playbook_id 並發模擬：N 個 ID 全部 save 後逐一 load 驗一致"""
    r = PhaseResult(f"D_multi_{count}")
    pids = [f"c6d_{uuid.uuid4().hex[:8]}" for _ in range(count)]
    try:
        for i, pid in enumerate(pids):
            repo.save_checkpoint(pid, _make_cp(pid, step_idx=i))
        for i, pid in enumerate(pids):
            loaded = repo.load_checkpoint(pid)
            if loaded is None or loaded.step_idx != i:
                r.fail(f"{pid}: step_idx 不一致")
            else:
                r.ok()
    except Exception as e:
        r.fail(f"例外: {e}")
    finally:
        for pid in pids:
            try:
                repo.clear_checkpoint(pid)
            except Exception:
                pass
    return r.done()


def phase_E_pg_failure_degradation() -> PhaseResult:
    """PG 故障降級：壞 DSN 使 PG 不可達，File 仍應寫入成功且計數 dual_write_failure"""
    r = PhaseResult("E_pg_fail_degrade")
    degraded_dir = _TEST_DIR + "_e_degrade"
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy.pool import NullPool

        from autoclaude.infra.repositories.dual_state_repository import DualStateRepository
        from autoclaude.infra.repositories.file_state_repository import FileStateRepository
        from autoclaude.infra.repositories.pg_state_repository import PgStateRepository

        bad_engine = create_async_engine(
            "postgresql+asyncpg://bad:bad@127.0.0.1:19999/nodb",
            poolclass=NullPool,
        )
        dual = DualStateRepository(
            primary=FileStateRepository(degraded_dir),
            shadow=PgStateRepository(bad_engine),
            strict=False,             # PG 失敗不 raise
            read_resolution="yaml_wins",
        )
        pid = f"c6e_{uuid.uuid4().hex[:8]}"
        dual.save_checkpoint(pid, _make_cp(pid, step_idx=5))

        loaded = dual.load_checkpoint(pid)
        if loaded is None or loaded.step_idx != 5:
            r.fail("PG 故障時 File 路徑讀取失敗")
        else:
            r.ok()  # File 主路徑正常

        m = dual.metrics.as_dict()
        if m.get("dual_write_failure", 0) > 0:
            r.ok()  # PG 寫入失敗被正確計數（符合預期）
        else:
            r.fail("預期 dual_write_failure > 0（PG 故障未被記錄到計數器）")

    except Exception as e:
        r.fail(f"例外: {e}")
    finally:
        shutil.rmtree(degraded_dir, ignore_errors=True)
    return r.done()


def phase_G_metrics(repo) -> PhaseResult:
    """C6 通過條件：主 repo DualMetrics 三個失敗計數器全為零"""
    r = PhaseResult("G_metrics_zero")
    if not hasattr(repo, "metrics"):
        r.fail("repo 無 metrics 屬性（非 DualStateRepository）")
        return r.done()
    m = repo.metrics.as_dict()
    logger.info("    Metrics snapshot: %s", m)
    for k in ("dual_write_failure", "shadow_drift_detected", "shadow_load_failure"):
        v = m.get(k, -1)
        if v == 0:
            r.ok()
        else:
            r.fail(f"{k} = {v}（C6 要求為 0）")
    return r.done()


# ── Orchestrator ──────────────────────────────────────────────────────────────

class C6Validator:
    def __init__(self, dsn: str, duration_hours: float, quick: bool):
        self.dsn = dsn
        self.duration_hours = duration_hours
        self.quick = quick
        self.results: list[PhaseResult] = []
        self.repo = None
        self._interrupted = False
        signal.signal(signal.SIGINT, self._on_sigint)

    def _on_sigint(self, *_):
        logger.warning("收到中斷訊號，正在存檔報告...")
        self._interrupted = True

    def _build_repo(self):
        cfg = StorageConfig(
            mode="both", db_dsn=self.dsn,
            dual_write_strict=True,
            dual_read_resolution="fail_loud",
        )
        return build_state_repository(_TEST_DIR, cfg)

    def _run_phase(self, fn) -> PhaseResult:
        r = fn()
        self.results.append(r)
        icon = "✅" if r.success else "❌"
        logger.info("  %s Phase %-20s  passed=%d failed=%d (%.1fs)",
                    icon, r.name, r.passed, r.failed, r.elapsed)
        return r

    def _full_suite(self, label: str, b_cycles: int, d_count: int):
        logger.info("── 完整套件 [%s] ──────────────────────────", label)
        for fn in [
            lambda: phase_A_basic_crud(self.repo),
            lambda: phase_B_high_freq(self.repo, b_cycles),
            lambda: phase_C_large_payload(self.repo),
            lambda: phase_D_multi_playbook(self.repo, d_count),
            lambda: phase_E_pg_failure_degradation(),
            lambda: phase_G_metrics(self.repo),
        ]:
            self._run_phase(fn)
            if self._interrupted:
                return

    def _hourly_check(self, hour: int):
        logger.info("── Hour %d 輕量檢查 ────────────────────────", hour)
        for fn in [
            lambda: phase_A_basic_crud(self.repo),
            lambda: phase_B_high_freq(self.repo, 20),
            lambda: phase_G_metrics(self.repo),
        ]:
            self._run_phase(fn)
            if self._interrupted:
                return

    def run(self) -> bool:
        start_ts = datetime.now(UTC)
        logger.info("C6 Validator 啟動")
        logger.info("  DB  : %s", self.dsn.split("@")[-1])
        logger.info("  時長: %.1fh  |  quick=%s", self.duration_hours, self.quick)

        b_cycles = 30 if self.quick else 200
        d_count = 5 if self.quick else 20
        check_interval = 60 if self.quick else 3600  # seconds

        try:
            self.repo = self._build_repo()
            logger.info("  Repo: %s ✅", type(self.repo).__name__)
        except Exception as e:
            logger.error("Repo 初始化失敗: %s", e)
            self._save_report(start_ts, success=False)
            return False

        end_ts = time.time() + self.duration_hours * 3600

        # 開始：完整套件
        self._full_suite("初始", b_cycles, d_count)

        # 主循環：每小時輕量 / 每 6 小時完整
        hour = 1
        while time.time() < end_ts and not self._interrupted:
            remaining = end_ts - time.time()
            sleep_secs = min(check_interval, remaining)
            if sleep_secs > 5:
                logger.info("  下次檢查：%.0f 秒後（剩餘 %.2fh）", sleep_secs, remaining / 3600)
                time.sleep(sleep_secs)

            if time.time() >= end_ts or self._interrupted:
                break

            if hour % 6 == 0:
                self._full_suite(f"Hour {hour}", b_cycles, d_count)
            else:
                self._hourly_check(hour)
            hour += 1

        # 結束：完整套件
        if not self._interrupted:
            self._full_suite("最終", b_cycles, d_count)

        # C6 通過條件：所有 G 階段全部 pass
        g_results = [r for r in self.results if r.name.startswith("G_")]
        success = bool(g_results) and all(r.success for r in g_results)
        self._save_report(start_ts, success=success)

        # 清除測試用 checkpoint 目錄
        shutil.rmtree(_TEST_DIR, ignore_errors=True)

        return success

    def _save_report(self, start_ts: datetime, success: bool):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = Path(__file__).parent / f"c6_report_{ts}.json"

        total_p = sum(r.passed for r in self.results)
        total_f = sum(r.failed for r in self.results)
        all_errs = [e for r in self.results for e in r.errors]

        report = {
            "c6_gate": "PASS" if success else "FAIL",
            "start_time": start_ts.isoformat(),
            "end_time": datetime.now(UTC).isoformat(),
            "duration_hours": self.duration_hours,
            "total_passed": total_p,
            "total_failed": total_f,
            "phases": [r.as_dict() for r in self.results],
            "all_errors": all_errs,
        }
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        gate_str = "[PASS]" if success else "[FAIL]"
        logger.info("=" * 60)
        logger.info("  C6 Gate : %s", gate_str)
        logger.info("  總計    : %d passed / %d failed", total_p, total_f)
        if all_errs:
            logger.info("  錯誤摘要:")
            for e in all_errs[:10]:
                logger.info("    - %s", e)
            if len(all_errs) > 10:
                logger.info("    ... 還有 %d 筆，詳見報告", len(all_errs) - 10)
        logger.info("  報告    : %s", path)
        logger.info("=" * 60)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="C6 Staging Validator — 24h dual-write 自動驗證")
    ap.add_argument("--duration", type=float, default=24.0, help="執行時長（小時，預設 24）")
    ap.add_argument("--quick", action="store_true", help="快速模式（~5 分鐘，用於功能驗證）")
    ap.add_argument("--dsn", default=DEFAULT_DSN,
                    help="PostgreSQL DSN（未給時取自 $AUTOCLAUDE_DB_DSN；無預設值）")
    args = ap.parse_args()

    if not args.dsn:
        ap.error("未提供 DSN：請給 --dsn，或設定環境變數 AUTOCLAUDE_DB_DSN。"
                 "本腳本刻意不內建憑證預設值。")

    if args.quick:
        args.duration = 5 / 60  # 5 minutes

    success = C6Validator(args.dsn, args.duration, args.quick).run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
