# enforces (governance rules): R-9.16
"""test_ambiguity_scorer.py — Phase G M3 / ACT-037 verification.

Acceptance:
  - 50 fixture (25 ambiguous + 25 clear) classification accuracy >= 80%
  - 6 dimension unit tests (each dim >= 3 cases)
  - cache hit / invalidation
  - SCG-0 blocking decision (Rule 9.16.2)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.fsm_runtime.ambiguity_scorer import (
    SCORER_VERSION,
    invalidate_cache,
    is_blocking,
    score_ac,
    score_frd,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "ambiguity_corpus"
THRESHOLD = 0.4


def _load(name: str) -> list[dict]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))["samples"]


# ─────────────────────────────────────────────────────────────
# Acceptance: corpus classification accuracy >= 80%
# ─────────────────────────────────────────────────────────────


def test_ambiguous_corpus_classified_as_blocking():
    samples = _load("ambiguous.json")
    correct = sum(1 for s in samples if score_ac(s["text"]).score >= THRESHOLD)
    accuracy = correct / len(samples)
    assert accuracy >= 0.80, (
        f"ambiguous accuracy {accuracy:.2%} < 80% (correct={correct}/{len(samples)})"
    )


def test_clear_corpus_classified_as_passing():
    samples = _load("clear.json")
    correct = sum(1 for s in samples if score_ac(s["text"]).score < THRESHOLD)
    accuracy = correct / len(samples)
    assert accuracy >= 0.80, (
        f"clear accuracy {accuracy:.2%} < 80% (correct={correct}/{len(samples)})"
    )


def test_combined_corpus_accuracy_at_least_80pct():
    ambig = _load("ambiguous.json")
    clear = _load("clear.json")
    correct = sum(1 for s in ambig if score_ac(s["text"]).score >= THRESHOLD) + \
              sum(1 for s in clear if score_ac(s["text"]).score < THRESHOLD)
    total = len(ambig) + len(clear)
    accuracy = correct / total
    assert accuracy >= 0.80, f"combined {accuracy:.2%} (correct={correct}/{total})"


# ─────────────────────────────────────────────────────────────
# Per-dimension unit tests (>= 3 cases each)
# ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("text", [
    "系統應快速回應",
    "fast and reasonable response",
    "處理應適當且足夠",
])
def test_d1_quantifier_triggers(text):
    s = score_ac(text)
    assert s.dimensions.d1_quantifier > 0


@pytest.mark.parametrize("text", [
    "資料應被處理。",
    "系統可被使用者設定。",
    "The order is processed.",
])
def test_d2_passive_triggers(text):
    s = score_ac(text)
    assert s.dimensions.d2_passive > 0


@pytest.mark.parametrize("text", [
    "效能必須維持高水準",
    "Latency should stay low",
    "系統可用性需持續穩定",
])
def test_d3_nfr_no_number_triggers(text):
    s = score_ac(text)
    assert s.dimensions.d3_no_number > 0


@pytest.mark.parametrize("text", [
    "系統處理使用者請求",
    "API returns success",
    "資料寫入資料庫",
])
def test_d4_no_negative_triggers(text):
    s = score_ac(text)
    assert s.dimensions.d4_no_negative > 0


@pytest.mark.parametrize("text", [
    "endpoint /orders 回傳訂單清單",
    "畫面顯示使用者頭像",
    "form submit 觸發 API",
])
def test_d5_no_anchor_triggers(text):
    s = score_ac(text)
    assert s.dimensions.d5_no_anchor > 0


@pytest.mark.parametrize("text", [
    "處理方式如同既有流程",
    "回傳格式與相關 API 一致",
    "behaves similar to existing system",
])
def test_d6_ambiguous_reference_triggers(text):
    s = score_ac(text)
    assert s.dimensions.d6_ambiguous_ref > 0


# ─────────────────────────────────────────────────────────────
# Negative cases — clear AC should NOT trigger relevant dim
# ─────────────────────────────────────────────────────────────


def test_clear_ac_with_numbers_avoids_d3():
    s = score_ac("API 回應時間需 < 200 ms")
    assert s.dimensions.d3_no_number == 0


def test_clear_ac_with_anchor_avoids_d5():
    s = score_ac("畫面顯示使用者列表 <!-- anchor:ui:user-list -->")
    assert s.dimensions.d5_no_anchor == 0


def test_clear_ac_with_negative_avoids_d4():
    s = score_ac("若使用者未登入，導向 /login")
    assert s.dimensions.d4_no_negative == 0


# ─────────────────────────────────────────────────────────────
# Score boundary
# ─────────────────────────────────────────────────────────────


def test_score_capped_at_one():
    text = "系統應快速適當地處理大量資料，被批次執行類似相應的操作"
    s = score_ac(text)
    assert s.score <= 1.0


def test_empty_text_returns_zero():
    s = score_ac("")
    assert s.score == 0.0
    assert s.dimensions.total() == 0.0


# ─────────────────────────────────────────────────────────────
# SCG-0 blocking decision (Rule 9.16.2)
# ─────────────────────────────────────────────────────────────


def test_is_blocking_true_when_any_score_above_threshold():
    scores = {
        "AC-001": score_ac("效能應快速且適度，類似既有產品"),  # 2+ signals -> ambiguous
        "AC-002": score_ac("若 X 超過 100，回傳 400"),  # clear
    }
    block, ids = is_blocking(scores, threshold=THRESHOLD)
    assert block is True
    assert "AC-001" in ids


def test_is_blocking_false_when_all_below_threshold():
    scores = {
        "AC-001": score_ac("若密碼長度 < 8 字元，回傳 400"),
        "AC-002": score_ac("API 回應時間 < 200 ms，否則告警"),
    }
    block, ids = is_blocking(scores, threshold=THRESHOLD)
    assert block is False
    assert ids == []


# ─────────────────────────────────────────────────────────────
# FRD batch + cache (Rule 9.16.4)
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def temp_frd(tmp_path):
    text = """# FRD Sample

### F-001 Login

#### AC-001-1 Happy Login
若使用者輸入正確帳密，登入成功並導向 /home <!-- anchor:ui:home -->

#### AC-001-2 Failed Login
若連續錯誤 3 次，鎖定帳號 15 分鐘
"""
    p = tmp_path / "FRD-Sample.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_score_frd_extracts_ac_blocks(temp_frd, tmp_path):
    invalidate_cache(repo_root=tmp_path)
    results = score_frd(temp_frd, repo_root=tmp_path)
    assert "AC-001-1" in results
    assert "AC-001-2" in results


def test_score_frd_cache_hit(temp_frd, tmp_path):
    invalidate_cache(repo_root=tmp_path)
    r1 = score_frd(temp_frd, repo_root=tmp_path)
    cache_dir = tmp_path / "build" / "cache" / "ambiguity" / SCORER_VERSION
    assert any(cache_dir.glob("*.json")), "cache file should exist after first run"
    r2 = score_frd(temp_frd, repo_root=tmp_path)
    assert {k: v.score for k, v in r1.items()} == {k: v.score for k, v in r2.items()}


def test_invalidate_cache_removes_files(temp_frd, tmp_path):
    score_frd(temp_frd, repo_root=tmp_path)
    cache_dir = tmp_path / "build" / "cache" / "ambiguity" / SCORER_VERSION
    assert any(cache_dir.glob("*.json"))
    deleted = invalidate_cache(repo_root=tmp_path)
    assert deleted >= 1
    assert not any(cache_dir.glob("*.json"))
