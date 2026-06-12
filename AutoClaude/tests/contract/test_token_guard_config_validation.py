"""SD_06 W5-T5-15：TokenGuardConfig Pydantic v2 invariants test。

對應規格：
  - SD_Improving_06.md §6.5 AC6-2（Pydantic v2 nested model + invariants）
  - SD06_Execution_Guide.md W5 T5-15：≥ 8 case
  - autoclaude/utils/config.py（TokenGuardConfig.model_validator）

驗證 invariants：
  1. compact_threshold_pct ∈ [0, 100]
  2. halt_threshold_pct ∈ [0, 100]
  3. halt > compact（既有 M-3/X-3）
  4. resume_delay_minutes ≥ 0
  5. max_auto_resumes ≥ 1
  6. context_patterns 必須為合法 regex
  7. 邊界值：halt == compact + epsilon
  8. JSON Schema 產生（OpenAPI 3.1 相容）
"""
from __future__ import annotations

import re

import pytest
from pydantic import ValidationError

from autoclaude.utils.config import TokenGuardConfig


# ──────────────────────────────────────────────
# Case 1：合法預設值
# ──────────────────────────────────────────────
def test_default_values_valid():
    cfg = TokenGuardConfig()
    assert cfg.enabled is True
    assert cfg.compact_threshold_pct == 80.0
    assert cfg.halt_threshold_pct == 90.0
    assert cfg.halt_threshold_pct > cfg.compact_threshold_pct


# ──────────────────────────────────────────────
# Case 2：compact_threshold_pct 邊界值
# ──────────────────────────────────────────────
@pytest.mark.parametrize("pct", [-1.0, 100.1, 150.0])
def test_compact_threshold_out_of_range_rejected(pct):
    with pytest.raises(ValidationError):
        TokenGuardConfig(compact_threshold_pct=pct, halt_threshold_pct=99.0)


# ──────────────────────────────────────────────
# Case 3：halt_threshold_pct 邊界值
# ──────────────────────────────────────────────
@pytest.mark.parametrize("pct", [-1.0, 100.1])
def test_halt_threshold_out_of_range_rejected(pct):
    with pytest.raises(ValidationError):
        TokenGuardConfig(compact_threshold_pct=50.0, halt_threshold_pct=pct)


# ──────────────────────────────────────────────
# Case 4：halt > compact invariant
# ──────────────────────────────────────────────
def test_halt_must_exceed_compact():
    with pytest.raises(ValidationError, match="halt_threshold_pct"):
        TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=80.0)


def test_halt_below_compact_rejected():
    with pytest.raises(ValidationError, match="halt_threshold_pct"):
        TokenGuardConfig(compact_threshold_pct=90.0, halt_threshold_pct=85.0)


def test_halt_just_above_compact_accepted():
    cfg = TokenGuardConfig(compact_threshold_pct=70.0, halt_threshold_pct=70.5)
    assert cfg.halt_threshold_pct == 70.5


# ──────────────────────────────────────────────
# Case 5：resume_delay_minutes 非負
# ──────────────────────────────────────────────
def test_resume_delay_negative_rejected():
    with pytest.raises(ValidationError):
        TokenGuardConfig(resume_delay_minutes=-1)


def test_resume_delay_zero_accepted():
    cfg = TokenGuardConfig(resume_delay_minutes=0)
    assert cfg.resume_delay_minutes == 0


def test_resume_delay_too_large_rejected():
    """resume_delay_minutes 超過一天（1440 分）視為設定錯誤。"""
    with pytest.raises(ValidationError):
        TokenGuardConfig(resume_delay_minutes=1441)


# ──────────────────────────────────────────────
# Case 6：max_auto_resumes ≥ 1
# ──────────────────────────────────────────────
def test_max_auto_resumes_zero_rejected():
    with pytest.raises(ValidationError):
        TokenGuardConfig(max_auto_resumes=0)


def test_max_auto_resumes_one_accepted():
    cfg = TokenGuardConfig(max_auto_resumes=1)
    assert cfg.max_auto_resumes == 1


# ──────────────────────────────────────────────
# Case 7：context_patterns 合法性
# ──────────────────────────────────────────────
def test_context_patterns_invalid_regex_rejected():
    with pytest.raises(ValidationError, match="(?i)regex"):
        TokenGuardConfig(context_patterns=["[unclosed"])


def test_context_patterns_valid_regex_accepted():
    cfg = TokenGuardConfig(context_patterns=[r"(\d+)%"])
    # 確認 regex 可編譯
    re.compile(cfg.context_patterns[0])


# ──────────────────────────────────────────────
# Case 8：JSON Schema 產生
# ──────────────────────────────────────────────
def test_json_schema_generation():
    schema = TokenGuardConfig.model_json_schema()
    assert "properties" in schema
    assert "compact_threshold_pct" in schema["properties"]
    assert "halt_threshold_pct" in schema["properties"]
    # Pydantic v2 範圍限制應反映在 schema 內
    halt_prop = schema["properties"]["halt_threshold_pct"]
    assert halt_prop.get("minimum") == 0.0
    assert halt_prop.get("maximum") == 100.0
