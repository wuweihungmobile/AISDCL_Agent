"""Phase J / ACT-075 — Capability Benchmark Harness（模型能力基準）.

補 L6 缺口 PJ-2：scaffold_gc 只看 catch/fire ROI，從不量測「底層模型變強了 →
鷹架 X 已多餘」。本模組提供一組凍結的小型確定性任務（對應每個鷹架想防的失敗
類），跑當前模型、量測通過率，落地能力帳本 build/state/capability-ledger.yaml，
供 rule_loader.propose_graduation_capability 做能力驅動退役（仍須人工 gate）。

純離線、可重現、零外網（沿用 G/H/I 慣例）。每個 benchmark 是 (capability_id,
prompt, grader) — grader 為確定性檢查函式；caller 提供 model_outputs（real session
產出或 fixture），harness 只負責 grade + 記帳，本身不呼叫 LLM。
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

import yaml

from .file_lock import file_lock
from .state_loader import REPO_ROOT

LEDGER_PATH = REPO_ROOT / "build" / "state" / "capability-ledger.yaml"
ROLLING_WINDOW = 10          # 每 capability 保留最近 N 次量測
GRADUATION_MIN_RUNS = 3      # 連續 N 次滿分才足以做能力驅動退役判據
GRADUATION_PASS_SCORE = 1.0  # 滿分門檻


@dataclass
class Benchmark:
    capability_id: str        # 對應一個鷹架想防的失敗類（如 "temporal_consistency"）
    prompt: str               # 凍結任務描述
    grader: Callable[[str], bool]  # 確定性檢查：model_output → pass/fail
    scaffold_rule_id: str = ""     # 對應的 governance rule（可空）


@dataclass
class BenchmarkResult:
    capability_id: str
    score: float              # 0..1 通過率
    passed: int
    total: int
    scaffold_rule_id: str = ""


@dataclass
class BenchmarkRun:
    results: List[BenchmarkResult] = field(default_factory=list)
    model_id: str = "unknown"
    ts: str = ""


def grade(benchmark: Benchmark, model_outputs: List[str]) -> BenchmarkResult:
    """以 grader 逐一評分 model_outputs，回傳通過率。空輸入 → score 0（保守）。"""
    total = len(model_outputs)
    if total == 0:
        return BenchmarkResult(benchmark.capability_id, 0.0, 0, 0, benchmark.scaffold_rule_id)
    passed = 0
    for out in model_outputs:
        try:
            if benchmark.grader(out):
                passed += 1
        except Exception:  # noqa: BLE001 — grader 失敗視為 fail（保守）
            pass
    return BenchmarkResult(
        capability_id=benchmark.capability_id,
        score=round(passed / total, 4),
        passed=passed,
        total=total,
        scaffold_rule_id=benchmark.scaffold_rule_id,
    )


def run_suite(
    suite: List[Benchmark],
    outputs_by_capability: Dict[str, List[str]],
    *,
    model_id: str = "unknown",
    today: Optional[str] = None,
) -> BenchmarkRun:
    """跑整組 benchmark（caller 提供每個 capability 的 model_outputs）。"""
    ts = (today or _dt.date.today().isoformat())
    run = BenchmarkRun(model_id=model_id, ts=ts)
    for b in suite:
        outs = outputs_by_capability.get(b.capability_id, [])
        run.results.append(grade(b, outs))
    return run


def _read_ledger(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": 1, "capabilities": {}}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {"schema_version": 1, "capabilities": {}}
    if not isinstance(data, dict):
        return {"schema_version": 1, "capabilities": {}}
    data.setdefault("capabilities", {})
    return data


def record_run(run: BenchmarkRun, *, path: Optional[Path] = None) -> Path:
    """把一次 BenchmarkRun 寫入能力帳本（rolling-N，file_lock 互斥，atomic）。"""
    p = path or LEDGER_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    lock = p.with_suffix(p.suffix + ".lock")
    with file_lock(lock):
        data = _read_ledger(p)
        caps = data.setdefault("capabilities", {})
        for r in run.results:
            entry = caps.setdefault(r.capability_id, {"history": []})
            entry["scaffold_rule_id"] = r.scaffold_rule_id
            entry["history"].append({
                "ts": run.ts, "model_id": run.model_id,
                "score": r.score, "passed": r.passed, "total": r.total,
            })
            entry["history"] = entry["history"][-ROLLING_WINDOW:]
            entry["latest_score"] = r.score
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        tmp.replace(p)
    return p


def capability_surpassed(capability_id: str, *, path: Optional[Path] = None,
                         min_runs: int = GRADUATION_MIN_RUNS) -> bool:
    """能力是否「連續 min_runs 次滿分」（能力驅動退役的前提訊號）。

    僅回傳訊號 — 不退役任何規則（退役必經 rule_loader.set_maturity 人工 gate，
    Rule 9.22.3）。
    """
    p = path or LEDGER_PATH
    data = _read_ledger(p)
    entry = data.get("capabilities", {}).get(capability_id)
    if not entry:
        return False
    hist = entry.get("history", [])
    if len(hist) < min_runs:
        return False
    recent = hist[-min_runs:]
    return all(float(h.get("score", 0.0)) >= GRADUATION_PASS_SCORE for h in recent)


__all__ = [
    "LEDGER_PATH", "Benchmark", "BenchmarkResult", "BenchmarkRun",
    "grade", "run_suite", "record_run", "capability_surpassed",
]
