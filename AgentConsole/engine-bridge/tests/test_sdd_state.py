"""`app/sdd_state.py` 對 `frozen_stages` 的兩種讀法（SDD `spec-refreeze`，OBS-SI-108／F-17）。

`spec-refreeze` 不經人工閘、不換狀態，只在 `frozen_stages` 追加一筆 `kind: refreeze`，
裡面只有被重記的那幾份規格的新摘要。Bridge 有兩個讀者，讀法刻意不同，兩邊都要鎖：
- `frozen_stage_count` 數**階段**（`:freeze` 預設階段名 `Stage-<n+1>` 的 n）：重記不是新階段；
- `frozen_digest_of` 查**摘要**：聯集、後者勝出，重記的新摘要必須蓋過凍結時的舊摘要，
  否則 409 回報會拿舊摘要誤導人。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.sdd_state import frozen_digest_of, frozen_stage_count

SPEC_REL = "docs/03_testing/contracts/TCS-A.md"
OTHER_REL = "docs/01_requirements/PRD-A.md"
OLD, NEW, OTHER = "sha256:" + "0" * 64, "sha256:" + "1" * 64, "sha256:" + "2" * 64


def _freeze(stage: str, digests: dict[str, str], **extra: Any) -> dict[str, Any]:
    return {"stage": stage, "frozen_at": "2026-10-19T00:00:00+00:00",
            "spec_docs": list(digests), "spec_doc_digests": digests, **extra}


def _refreeze(stage: str, digests: dict[str, str]) -> dict[str, Any]:
    return _freeze(stage, digests, kind="refreeze", supersedes="2026-10-19T00:00:00+00:00",
                   reason="規格修訂後重記")


@pytest.mark.parametrize(("stages", "expected"), [
    (None, 0), ("not-a-list", 0), ([], 0),                       # 沒有欄位／壞形狀／空：不炸
    ([{"stage": "Stage-1"}, {"stage": "custom"}], 2),            # 舊狀態檔沒有 kind ＝ 凍結
    ([_freeze("Stage-1", {SPEC_REL: OLD}, kind="freeze")], 1),   # 明寫 freeze 一樣算
    ([_freeze("Stage-1", {SPEC_REL: OLD}), _refreeze("Stage-1", {SPEC_REL: NEW})], 1),
    ([_freeze("Stage-1", {SPEC_REL: OLD}), _refreeze("Stage-1", {SPEC_REL: NEW}),
      _refreeze("Stage-1", {SPEC_REL: OLD}), _freeze("Stage-2", {SPEC_REL: NEW})], 2),
])
def test_only_freezes_are_counted_as_stages_never_refreezes(
        stages: object, expected: int) -> None:
    """數筆數會讓「Stage-1＋一次重記」之後的下一次凍結預設名變成 Stage-3（跳號）。"""
    assert frozen_stage_count({"frozen_stages": stages}) == expected


def test_a_refreeze_digest_wins_over_the_frozen_one_and_unnamed_documents_keep_theirs(
        tmp_path: Path) -> None:
    """重記只帶被點名的那幾份：被點名的取新摘要，沒被點名的仍是凍結時的摘要（聯集、後者勝出）。
    同一份狀態上階段數仍是 1——兩個讀者讀的是同一批條目，結論不同。"""
    state = {"frozen_stages": [
        _freeze("Stage-1", {SPEC_REL: OLD, OTHER_REL: OTHER}),
        _refreeze("Stage-1", {SPEC_REL: NEW}),
    ]}
    assert frozen_digest_of(state, tmp_path / SPEC_REL) == NEW
    assert frozen_digest_of(state, tmp_path / OTHER_REL) == OTHER
    assert frozen_digest_of(state, tmp_path / "docs" / "elsewhere.md") is None
    assert frozen_stage_count(state) == 1
