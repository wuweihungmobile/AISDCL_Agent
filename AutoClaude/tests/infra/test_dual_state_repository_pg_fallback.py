"""T10 邊界 2 — DualStateRepository PG fallback 測試（SD_Improving_04 W2 T10）。

驗證情境（**不連真 PG**；用 MagicMock 模擬 shadow PG 連線失敗）：
  1. save_checkpoint：shadow 失敗 + strict=False → warning only、metrics +1
  2. save_checkpoint：shadow 失敗 + strict=True → raise
  3. load_checkpoint：yaml_wins + primary 有資料 → 直接回 primary（不觸發 shadow load）
  4. load_checkpoint：db_wins + shadow 失敗 → fallback 至 primary
  5. load_checkpoint：yaml_wins + primary 空 + shadow 有資料 → 回 shadow（災難回復）
  6. clear_checkpoint：shadow 失敗 + strict=False → warning only
  7. schedule_resume：shadow 失敗 → warning only、回 primary 的 resume_at
  8. fail_loud + drift → RuntimeError + shadow_drift_detected += 1
  9. metrics.as_dict() 結構驗證
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# 測試需 sqlalchemy；CI 基礎 test job 僅裝 .[dev]（驗證「零 PG 依賴」不變量），
# 無 postgres extra → 未安裝時整體 skip（對齊 test_pg_memory_store_security.py 慣例）
pytest.importorskip("sqlalchemy")
from sqlalchemy.exc import OperationalError  # noqa: E402

from autoclaude.infra.repositories.dual_state_repository import (  # noqa: E402
    DualMetrics,
    DualStateRepository,
)
from autoclaude.infra.repositories.file_state_repository import FileStateRepository
from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint


# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────
def _make_checkpoint(step_idx: int = 0, step_id: str = "T01") -> PlaybookCheckpoint:
    return PlaybookCheckpoint(
        playbook_path="test.yaml",
        step_idx=step_idx,
        step_id=step_id,
        total_steps=3,
    )


def _make_operational_error() -> OperationalError:
    """模擬 asyncpg / SQLAlchemy 在 PG 不可用時拋出的例外。"""
    return OperationalError("SELECT 1", {}, Exception("connection refused"))


def _make_dual_with_mock_shadow(
    tmp_path,
    *,
    strict: bool = False,
    read_resolution: str = "yaml_wins",
):
    """primary 用真實 FileStateRepository；shadow 用 MagicMock。"""
    primary = FileStateRepository(checkpoint_dir=str(tmp_path / "primary"))
    shadow = MagicMock()
    dual = DualStateRepository(
        primary, shadow,
        strict=strict,
        read_resolution=read_resolution,
    )
    return dual, primary, shadow


# ──────────────────────────────────────────────────────────
# 1. save_checkpoint × strict=False
# ──────────────────────────────────────────────────────────
def test_save_shadow_fail_strict_false_returns_silent_warning(tmp_path):
    """shadow 寫入失敗（OperationalError）+ strict=False → 不 raise、metrics 計數。"""
    dual, primary, shadow = _make_dual_with_mock_shadow(tmp_path, strict=False)
    shadow.save_checkpoint.side_effect = _make_operational_error()
    cp = _make_checkpoint(step_idx=1, step_id="T02")

    # 不應 raise
    dual.save_checkpoint("proj_silent", cp)

    # 主後端寫入成功
    assert primary.load_checkpoint("proj_silent") is not None
    # 計數正確
    assert dual.metrics.dual_write_failure == 1
    assert dual.metrics.dual_write_success == 0
    # shadow 確實被呼叫
    shadow.save_checkpoint.assert_called_once()


# ──────────────────────────────────────────────────────────
# 2. save_checkpoint × strict=True
# ──────────────────────────────────────────────────────────
def test_save_shadow_fail_strict_true_raises(tmp_path):
    """shadow 寫入失敗 + strict=True → raise OperationalError。"""
    dual, primary, shadow = _make_dual_with_mock_shadow(tmp_path, strict=True)
    shadow.save_checkpoint.side_effect = _make_operational_error()

    with pytest.raises(OperationalError):
        dual.save_checkpoint("proj_strict", _make_checkpoint())

    # 主後端應已寫入（save 先寫主後端再寫 shadow）
    assert primary.load_checkpoint("proj_strict") is not None
    assert dual.metrics.dual_write_failure == 1


# ──────────────────────────────────────────────────────────
# 3. load_checkpoint yaml_wins × primary 有資料
# ──────────────────────────────────────────────────────────
def test_load_yaml_wins_falls_back_to_primary_when_shadow_unavailable(tmp_path):
    """yaml_wins：primary 已有資料時短路不呼叫 shadow（也不應計入 shadow_load_failure）。"""
    dual, primary, shadow = _make_dual_with_mock_shadow(
        tmp_path, read_resolution="yaml_wins",
    )
    # primary 先寫入資料
    primary.save_checkpoint("proj_yw", _make_checkpoint(step_idx=2, step_id="T03"))
    # shadow 即使會失敗也不該被觸發
    shadow.load_checkpoint.side_effect = _make_operational_error()

    loaded = dual.load_checkpoint("proj_yw")
    assert loaded is not None
    assert loaded.step_idx == 2
    # yaml_wins 短路語意：primary 命中時 shadow 不被呼叫
    shadow.load_checkpoint.assert_not_called()
    # 既然沒呼叫到，計數應維持 0
    assert dual.metrics.shadow_load_failure == 0


# ──────────────────────────────────────────────────────────
# 4. load_checkpoint db_wins × shadow load 失敗
# ──────────────────────────────────────────────────────────
def test_load_db_wins_falls_back_to_primary_when_shadow_load_fails(tmp_path):
    """db_wins：shadow load 失敗 → 退回 primary、metrics.shadow_load_failure += 1。"""
    dual, primary, shadow = _make_dual_with_mock_shadow(
        tmp_path, read_resolution="db_wins",
    )
    primary.save_checkpoint("proj_dw", _make_checkpoint(step_idx=4, step_id="T05"))
    shadow.load_checkpoint.side_effect = _make_operational_error()

    loaded = dual.load_checkpoint("proj_dw")
    assert loaded is not None
    assert loaded.step_idx == 4   # primary 的值
    # shadow 失敗應計入
    assert dual.metrics.shadow_load_failure == 1


# ──────────────────────────────────────────────────────────
# 5. load_checkpoint yaml_wins × primary 空、shadow 有資料（災難回復）
# ──────────────────────────────────────────────────────────
def test_load_yaml_wins_returns_shadow_when_primary_empty(tmp_path):
    """yaml_wins：primary 不存在 + shadow 可讀 → 回 shadow（disaster recovery）。"""
    dual, primary, shadow = _make_dual_with_mock_shadow(
        tmp_path, read_resolution="yaml_wins",
    )
    # primary 完全空白
    assert primary.load_checkpoint("proj_dr") is None
    # shadow 模擬 PG 中有災難回復資料
    shadow_cp = _make_checkpoint(step_idx=7, step_id="T08")
    shadow.load_checkpoint.return_value = shadow_cp

    loaded = dual.load_checkpoint("proj_dr")
    assert loaded is not None
    assert loaded.step_idx == 7
    assert loaded.step_id == "T08"
    shadow.load_checkpoint.assert_called_once_with("proj_dr")


# ──────────────────────────────────────────────────────────
# 6. clear_checkpoint × shadow 失敗 + strict=False
# ──────────────────────────────────────────────────────────
def test_clear_shadow_fail_strict_false_warns_only(tmp_path):
    """clear：shadow 失敗（strict=False）→ warning only、不 raise。"""
    dual, primary, shadow = _make_dual_with_mock_shadow(tmp_path, strict=False)
    shadow.clear_checkpoint.side_effect = _make_operational_error()

    # 先在 primary 寫入資料以便驗證 primary clear 動作
    primary.save_checkpoint("proj_clr", _make_checkpoint())
    assert primary.load_checkpoint("proj_clr") is not None

    # clear 不應 raise
    dual.clear_checkpoint("proj_clr")

    # primary 應已清除
    assert primary.load_checkpoint("proj_clr") is None
    shadow.clear_checkpoint.assert_called_once_with("proj_clr")


def test_clear_shadow_fail_strict_true_raises(tmp_path):
    """clear：shadow 失敗 + strict=True → raise（補強同對稱情境）。"""
    dual, primary, shadow = _make_dual_with_mock_shadow(tmp_path, strict=True)
    shadow.clear_checkpoint.side_effect = _make_operational_error()
    primary.save_checkpoint("proj_clr_strict", _make_checkpoint())

    with pytest.raises(OperationalError):
        dual.clear_checkpoint("proj_clr_strict")
    # primary 仍應被清除（先 clear primary）
    assert primary.load_checkpoint("proj_clr_strict") is None


# ──────────────────────────────────────────────────────────
# 7. schedule_resume × shadow 失敗
# ──────────────────────────────────────────────────────────
def test_schedule_resume_shadow_fail_warns_only(tmp_path):
    """schedule_resume：shadow 失敗 → warning only、回 primary 的 resume_at。"""
    dual, primary, shadow = _make_dual_with_mock_shadow(tmp_path)
    shadow.schedule_resume.side_effect = _make_operational_error()

    # primary 必須先有 checkpoint 才能 schedule_resume
    primary.save_checkpoint("proj_sr", _make_checkpoint())

    # 不應 raise
    resume_at = dual.schedule_resume("proj_sr", delay_minutes=10)
    assert resume_at is not None
    # 回傳值應為 primary 的權威時間
    shadow.schedule_resume.assert_called_once_with("proj_sr", 10)


# ──────────────────────────────────────────────────────────
# 8. fail_loud × drift
# ──────────────────────────────────────────────────────────
def test_fail_loud_drift_detected_raises_runtime_error(tmp_path):
    """fail_loud：primary.step_idx ≠ shadow.step_idx → raise + drift 計數 +1。"""
    dual, primary, shadow = _make_dual_with_mock_shadow(
        tmp_path, read_resolution="fail_loud",
    )
    primary.save_checkpoint("proj_fl", _make_checkpoint(step_idx=2, step_id="T03"))
    # shadow 回傳不同 step_idx
    shadow.load_checkpoint.return_value = _make_checkpoint(step_idx=5, step_id="T06")

    with pytest.raises(RuntimeError, match="drift detected"):
        dual.load_checkpoint("proj_fl")

    assert dual.metrics.shadow_drift_detected == 1


# ──────────────────────────────────────────────────────────
# 9. metrics.as_dict() 結構驗證
# ──────────────────────────────────────────────────────────
def test_metrics_dict_structure(tmp_path):
    """DualMetrics.as_dict() 應包含 5 個固定 key（metrics hook 介面契約）。

    SD_06 W5-T5-10：新增 reconcile_queued（PG-first 模式下 File 失敗計數）。
    """
    metrics = DualMetrics()
    d = metrics.as_dict()
    assert set(d.keys()) == {
        "dual_write_success",
        "dual_write_failure",
        "shadow_drift_detected",
        "shadow_load_failure",
        "reconcile_queued",
    }
    # 全部初始為 0
    assert all(v == 0 for v in d.values())

    # 確認 DualStateRepository.metrics 為同類型物件
    dual, _, _ = _make_dual_with_mock_shadow(tmp_path)
    assert isinstance(dual.metrics, DualMetrics)
    assert dual.metrics.as_dict() == d
