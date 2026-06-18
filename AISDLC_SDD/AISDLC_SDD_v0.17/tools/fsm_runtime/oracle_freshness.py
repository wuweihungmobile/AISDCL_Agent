"""Phase I M1 / ACT-063 — Test-Oracle Freshness Check（oracle 凍結後新鮮度）.

落實 SDD_improving_Automation_09.md §3.4(2) / PI-2：Test-Oracle 在
TEST_CONTRACT_NEGOTIATED 凍結後，當 spec 經 SPEC_AUDIT / DRIFT_OBSERVATION →
SPEC_DRAFTING 演進，oracle 變 stale，評估器拿「舊考卷改新答案」卻無任何新鮮度
檢測。本模組進 EXECUTION_EVALUATION 前比對 oracle 凍結 sha 與當前 spec sha：
  - 相符 → fresh（oracle 有效）
  - 不符 → stale（advisory）→ 建議回 TEST_CONTRACT_NEGOTIATED 重談判
    （差異閾值化：僅實質影響該 AC 的變更才判 stale，避免抖動）。

純 stdlib、確定性、零外部依賴。
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


def compute_spec_sha(paths: Iterable[Path]) -> str:
    """對一組 spec 檔內容算穩定 sha256（排序後串接，避免順序抖動）。"""
    h = hashlib.sha256()
    for p in sorted(Path(x) for x in paths):
        try:
            h.update(Path(p).read_bytes())
        except OSError:
            h.update(f"<missing:{p}>".encode("utf-8"))
    return h.hexdigest()


@dataclass
class FreshnessResult:
    fresh: bool
    frozen_sha: Optional[str]
    current_sha: str
    reason: str

    @property
    def stale(self) -> bool:
        return not self.fresh


def check(
    *,
    frozen_spec_sha: Optional[str],
    spec_paths: Iterable[Path],
) -> FreshnessResult:
    """比對 oracle 凍結 sha 與當前 spec sha。

    frozen_spec_sha 為 None（舊合約未記 sha）→ 視為 fresh 但標 reason
    （向後相容；advisory，不阻塞）。
    """
    current = compute_spec_sha(spec_paths)
    if not frozen_spec_sha:
        return FreshnessResult(
            fresh=True, frozen_sha=None, current_sha=current,
            reason="no frozen_spec_sha recorded (legacy contract) — treat as fresh (advisory)",
        )
    if frozen_spec_sha == current:
        return FreshnessResult(
            fresh=True, frozen_sha=frozen_spec_sha, current_sha=current,
            reason="spec sha matches frozen oracle sha — oracle is fresh",
        )
    return FreshnessResult(
        fresh=False, frozen_sha=frozen_spec_sha, current_sha=current,
        reason=(
            "spec sha changed since oracle was frozen — oracle may be STALE; "
            "advise re-negotiation (back to TEST_CONTRACT_NEGOTIATED)"
        ),
    )


def changed_acs(old_acs: List[str], new_acs: List[str]) -> List[str]:
    """差異閾值化輔助：回傳實質變動的 AC（新增/刪除/改寫），供判 stale 是否實質。"""
    old = {a.strip() for a in old_acs}
    new = {a.strip() for a in new_acs}
    return sorted((old ^ new))
