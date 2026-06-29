"""Phase H M4 / ACT-053 — Runtime Observability Query（本地唯讀查詢層）.

落實 SDD_improving_Automation_08.md §4.3 / §G5：保留 OPEN-10.6「禁 HTTP endpoint」
資安決策，但恢復 AI「主動查詢根因」的能力——關鍵是「查詢」≠「開 server」。

Evaluator 在 EXECUTION_EVALUATION 中可呼叫 logql_lite() 直接對沙箱日誌推理
「為何失敗」，而非被動收 file-based pull 的預嚼摘要。

資料源（唯讀 ndjson，由 sandbox_runner 落地）：
  data/observability/logs.ndjson    {ts, level, msg, ...}
  data/observability/metrics.ndjson {ts, name, value, labels:{}}
無網路、無 endpoint、無第三方依賴（純 stdlib）。
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OBS_DIR = _ROOT / "data" / "observability"


def _read_ndjson(path: Path) -> List[dict]:
    if not path.exists():
        return []
    out: List[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


# --- LogQL-lite：{label="v", ...} |= "substr" / |~ "regex" -----------------

_SELECTOR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')


@dataclass
class LogQuery:
    selectors: Dict[str, str]
    contains: List[str]
    regexes: List[str]


def parse_logql(query: str) -> LogQuery:
    """Parse a tiny LogQL subset: `{level="error"} |= "deadlock" |~ "tx-\\d+"`."""
    selectors: Dict[str, str] = {}
    sel_match = re.search(r"\{([^}]*)\}", query)
    if sel_match:
        for k, v in _SELECTOR_RE.findall(sel_match.group(1)):
            selectors[k] = v
    contains = re.findall(r'\|=\s*"([^"]*)"', query)
    regexes = re.findall(r'\|~\s*"([^"]*)"', query)
    return LogQuery(selectors=selectors, contains=contains, regexes=regexes)


def logql_lite(query: str, *, obs_dir: Optional[Path] = None) -> List[dict]:
    """Query logs.ndjson with a LogQL subset; returns matching log entries."""
    q = parse_logql(query)
    entries = _read_ndjson(Path(obs_dir or DEFAULT_OBS_DIR) / "logs.ndjson")
    out: List[dict] = []
    # H-2 修：使用者/AI 提供的正則可能非法（手誤）；不可讓底層 re.error 中斷
    # 上層失敗推理流程 — 轉成乾淨 ValueError 附原查詢。
    try:
        compiled = [re.compile(r) for r in q.regexes]
    except re.error as exc:
        raise ValueError(f"logql_lite: invalid regex in query {query!r}: {exc}") from exc
    for e in entries:
        if any(str(e.get(k, "")) != v for k, v in q.selectors.items()):
            continue
        blob = e.get("msg", "") if isinstance(e.get("msg"), str) else json.dumps(e)
        if any(c not in blob for c in q.contains):
            continue
        if any(not rx.search(blob) for rx in compiled):
            continue
        out.append(e)
    return out


# --- PromQL-lite：metric{label="v"} 聚合 ------------------------------------

_AGGS = {
    "count": len,
    "sum": lambda xs: round(sum(xs), 6),
    "avg": lambda xs: round(sum(xs) / len(xs), 6) if xs else 0.0,
    "max": lambda xs: max(xs) if xs else 0.0,
    "min": lambda xs: min(xs) if xs else 0.0,
}


def promql_lite(metric: str, *, agg: str = "avg", labels: Optional[Dict[str, str]] = None,
                obs_dir: Optional[Path] = None) -> float:
    """Aggregate metrics.ndjson values for a metric name with optional label filter."""
    agg = agg.strip().lower()
    if agg not in _AGGS:
        raise ValueError(f"unknown agg={agg!r}; expected one of {sorted(_AGGS)}")
    rows = _read_ndjson(Path(obs_dir or DEFAULT_OBS_DIR) / "metrics.ndjson")
    labels = labels or {}
    vals: List[float] = []
    for r in rows:
        if r.get("name") != metric:
            continue
        rl = r.get("labels", {}) or {}
        if any(str(rl.get(k)) != v for k, v in labels.items()):
            continue
        try:
            v = float(r.get("value"))
        except (TypeError, ValueError):
            continue
        # H-3 修：過濾 NaN/inf — 否則無聲污染聚合（avg→nan），下游 PBS 比較全 False 誤判。
        if not math.isfinite(v):
            continue
        vals.append(v)
    fn = _AGGS[agg]
    return float(fn(vals)) if agg != "count" else float(fn(vals))
