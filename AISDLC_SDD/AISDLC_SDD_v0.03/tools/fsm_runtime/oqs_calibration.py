"""Phase I M1 / ACT-062 — OQS Calibration Feedback Chain（誰評估評估器）.

落實 SDD_improving_Automation_09.md §3.4 / PI-2：Phase H 防了 Generator 過擬合
（oracle 對 dev 不可見），卻完全沒防 **Evaluator（OQS）自己漂移**。OQS 的
_WEIGHTS / BLOCK_THRESHOLD 是硬編碼常數、score() 無 record_calibration 入口
（對比 path_cost 有完整校準鏈）。dev 只要學會「堆無意義但會過的測試」就能衝高
test_pass_rate（權重最大 0.40）→ GAN mode collapse 的工程復現。

本模組補上 OQS 的對稱校準鏈：
  - record_calibration(verdict, downstream_violated)：把每次 OQS verdict 與下游
    真實結果（PR_REVIEW 是否回退 / 生產是否在同 AC 違反）配對，rolling-N 計命中率。
  - check_drift()：連續 N 次「OQS pass 但下游違反」→ 寫 OQS-DRIFT-{date}.yaml，
    要求進 EVALUATOR_AUDIT、人工調 _WEIGHTS/BLOCK_THRESHOLD 並 bump SCORER_VERSION。
  - FLAKY verdict 不進校準樣本（隨機訊號既不蓋章也不污染校準 — PI-3 協同）。

評分基準永不自動改（仿 rule_loader.set_maturity 人工 gate）：本模組只「偵測 +
建議」，絕不自動改 output_quality_scorer 的權重/門檻。

純 stdlib + yaml、確定性、file_lock 互斥（沿用 ACT-024）。
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .file_lock import file_lock
from .output_quality_scorer import SCORER_VERSION

ROLLING_WINDOW = 10              # rolling-N 命中率視窗
DRIFT_CONSECUTIVE_THRESHOLD = 3  # 連續 N 次「pass 但下游違反」→ drift


def _root() -> Path:
    from .state_loader import REPO_ROOT
    return REPO_ROOT


def _rolling_path() -> Path:
    return _root() / "build" / "state" / "oqs-calibration-rolling.yaml"


def _drift_report_dir() -> Path:
    return _root() / "build" / "reports" / "eval"


@dataclass
class DriftResult:
    drifted: bool
    consecutive_pass_but_violated: int
    hit_rate: float
    samples: int
    report_path: Optional[str] = None


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        import yaml  # type: ignore
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}


def record_calibration(
    *,
    verdict: str,
    downstream_violated: bool,
    ac_id: str = "",
    rolling_path: Optional[Path] = None,
) -> DriftResult:
    """記錄一次 OQS verdict ↔ 下游真實結果配對，回傳 drift 判定。

    verdict ∈ {"pass","runtime_fail","spec_defect","inconclusive","FLAKY"}.
    FLAKY 一律跳過（不入樣本）。downstream_violated=True 代表 OQS 放行但
    下游（PR_REVIEW 回退 / 生產違反）證明判錯。
    """
    if verdict.upper() == "FLAKY":
        # 隨機訊號不進校準樣本（PI-3 協同）
        return DriftResult(drifted=False, consecutive_pass_but_violated=0,
                           hit_rate=1.0, samples=0)

    path = rolling_path or _rolling_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import yaml  # type: ignore
    except Exception:  # noqa: BLE001
        return DriftResult(drifted=False, consecutive_pass_but_violated=0, hit_rate=1.0, samples=0)

    with file_lock(path.with_suffix(".lock")):
        doc = _load(path)
        rows: List[dict] = list(doc.get("samples", []))
        rows.append({
            "verdict": verdict,
            "downstream_violated": bool(downstream_violated),
            "ac_id": ac_id,
            "scorer_version": SCORER_VERSION,
            "ts": _now(),
        })
        if len(rows) > ROLLING_WINDOW * 4:
            rows = rows[-ROLLING_WINDOW * 4:]
        doc["samples"] = rows
        doc["updated_at"] = _now()
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
        tmp.replace(path)

    return _assess(rows)


def _assess(rows: List[dict]) -> DriftResult:
    window = rows[-ROLLING_WINDOW:]
    n = len(window)
    # hit = OQS verdict 與下游一致：pass→未違反 / 非 pass→（不評）。
    # 命中率以「pass 且未違反」+「非 pass」為命中。
    hits = 0
    for r in window:
        passed = str(r.get("verdict")) == "pass"
        violated = bool(r.get("downstream_violated"))
        if passed and not violated:
            hits += 1
        elif not passed:
            hits += 1
    hit_rate = round(hits / n, 4) if n else 1.0

    # 連續「pass 但 violated」計數（從尾端往前）
    consec = 0
    for r in reversed(rows):
        if str(r.get("verdict")) == "pass" and bool(r.get("downstream_violated")):
            consec += 1
        else:
            break
    drifted = consec >= DRIFT_CONSECUTIVE_THRESHOLD
    return DriftResult(drifted=drifted, consecutive_pass_but_violated=consec,
                       hit_rate=hit_rate, samples=n)


def write_oqs_drift_report(
    result: DriftResult,
    *,
    today: Optional[str] = None,
    out_dir: Optional[Path] = None,
) -> Optional[str]:
    """連續漂移時寫 OQS-DRIFT-{date}.yaml（要求人工 recalibrate + bump SCORER_VERSION）。"""
    try:
        import yaml  # type: ignore
    except Exception:  # noqa: BLE001
        return None
    target = out_dir or _drift_report_dir()
    target.mkdir(parents=True, exist_ok=True)
    date = today or _dt.date.today().isoformat()
    path = target / f"OQS-DRIFT-{date}.yaml"
    doc = {
        "detected_at": _now(),
        "scorer_version": SCORER_VERSION,
        "consecutive_pass_but_violated": result.consecutive_pass_but_violated,
        "rolling_hit_rate": result.hit_rate,
        "verdict": "OQS_DRIFT",
        "required_action": (
            "進 EVALUATOR_AUDIT；人工調整 output_quality_scorer._WEIGHTS / "
            "BLOCK_THRESHOLD 並 bump SCORER_VERSION（評分基準永不自動改 — 仿 "
            "rule_loader.set_maturity 人工 gate）。"
        ),
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    tmp.replace(path)
    return str(path)
