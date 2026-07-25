"""Phase I M3 / ACT-067 — Production Behavioral → FPL Draft（生產真實行為反哺規格）.

落實 SDD_improving_Automation_09.md §4.3：打通「生產真實行為 → 可查詢 drill-down →
FPL → SLV/新 AC」單一閉環。同一 behavioral divergence 窗口內 ≥3 次 → 自動生成
FPL-NNN 草案（source=PROD-auto-generated，trust_level=proposed，advisory-only per
Rule 9.11.3）→ 餵入既有 slv_generator.propose_slv_from_fpl → SLV/AC 草案 → 人工 review 升 verified。

全程 advisory + 人工 gate，不破壞既有 NFR pull（production_monitor）與沙箱 query 契約。
守 OPEN-10.6：file-based、無 HTTP endpoint。
"""
from __future__ import annotations

import datetime as _dt
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# R44: reuse package SSOT sanitizer (state_loader._sanitize_component) for
# path-traversal defence when building filenames from externally-influenced ids.
from .state_loader import _sanitize_component

# 同 divergence 窗口內 ≥ N 次 → 生成 FPL 草案
DRIFT_WINDOW_THRESHOLD = 3

FAILURE_PATTERNS_DIR = Path(__file__).resolve().parents[2] / "knowledge" / "failure-patterns"


@dataclass
class BehavioralDriftEvent:
    ac_id: str
    divergence_kind: str
    score: float
    ts: str = ""


def count_by_window(events: List[BehavioralDriftEvent]) -> dict:
    """以 (ac_id, divergence_kind) 為 key 計數（窗口內聚合）。"""
    counts = defaultdict(int)
    for e in events:
        counts[(e.ac_id, e.divergence_kind)] += 1
    return dict(counts)


def should_generate_fpl(events: List[BehavioralDriftEvent], *, threshold: int = DRIFT_WINDOW_THRESHOLD) -> List[tuple]:
    """回傳達閾值的 (ac_id, divergence_kind) 清單。"""
    return [k for k, n in count_by_window(events).items() if n >= threshold]


def generate_fpl_draft(
    ac_id: str,
    divergence_kind: str,
    *,
    occurrences: int,
    fpl_id: Optional[str] = None,
    out_dir: Optional[Path] = None,
    today: Optional[str] = None,
) -> str:
    """生成 FPL-NNN 草案 markdown（source=PROD-auto-generated，trust_level=proposed）。

    回傳寫入路徑。advisory-only — 人工 review 後才餵 slv_generator 升 verified。
    """
    target = out_dir or FAILURE_PATTERNS_DIR
    target.mkdir(parents=True, exist_ok=True)
    date = today or _dt.date.today().isoformat()
    # R44: both branches (explicit fpl_id override and the fallback) are
    # externally-influenceable — sanitize either way before path assembly.
    fid = _sanitize_component(fpl_id) if fpl_id else (
        f"FPL-PROD-{_sanitize_component(ac_id)}-{_sanitize_component(divergence_kind)}"
    )
    path = target / f"{fid}.md"
    content = f"""# {fid} — 生產 behavioral 偏差（自動衍生草案）

- **source**: PROD-auto-generated {date}
- **source_fpl**: null（生產遙測衍生，per Rule 9.11.5 審計鏈顯式宣告）
- **trust_level**: proposed（advisory-only，per Rule 9.11.3 — 人工 review 升 verified 才 enforce）
- **ac_id**: {ac_id}
- **divergence_kind**: {divergence_kind}
- **occurrences**: {occurrences}（窗口內 ≥ {DRIFT_WINDOW_THRESHOLD} 觸發自動草擬）

## 偵測到的功能性偏差

生產遙測顯示 `{ac_id}` 的 **{divergence_kind}** 偏差重複出現 {occurrences} 次。
此為「生產真實行為 → 可查詢 → FPL → SLV/新 AC」閉環的第一步草案。

## 建議 Next Action

1. 人工 review 本草案是否屬實質規格缺口（vs 監控誤報）。
2. 若屬實 → 餵入 `slv_generator.propose_slv_from_fpl({fid})` 產 SLV/AC 草案。
3. sa-analyst 決定是否採納並更新 FRD 的對應 AC（人工 signoff，Rule 8 / 9.11.3）。

> 本草案由 production_to_fpl.py（ACT-067）自動產出；**禁自動 enforce**，全程 advisory。
"""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)
    return str(path)


def process_drift_events(
    events: List[BehavioralDriftEvent],
    *,
    threshold: int = DRIFT_WINDOW_THRESHOLD,
    out_dir: Optional[Path] = None,
    today: Optional[str] = None,
) -> List[str]:
    """掃 drift 事件，對達閾值的 (ac, kind) 生成 FPL 草案。回傳寫入路徑清單。"""
    counts = count_by_window(events)
    written: List[str] = []
    for (ac_id, kind), n in counts.items():
        if n >= threshold:
            written.append(generate_fpl_draft(
                ac_id, kind, occurrences=n, out_dir=out_dir, today=today
            ))
    return written
