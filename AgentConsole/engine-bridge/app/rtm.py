"""`GET /autoclaude/runs/{id}/rtm`：讀引擎逆向回寫的 RTM 覆蓋報告（唯讀；ADR-XPLAT-016 §8.5；契約
v1.5 §3.1.4 (f)）。

來源：該 run 工作區 `engine/checkpoints/rtm/` 下的 `RTM-COVERAGE-<project>.yaml`（引擎的
`RtmWritebackPlugin`只在 run **正常走完**時寫入；`.jsonl` 歷史檔不讀）。多份取修改時間最新者。
`advisory` 恆為 `true`——這是**諮詢視圖**，不覆寫人工 RTM；真正的閘是 SCG-4 的獨立審查。Bridge 不需
要權杖（唯讀）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .errors import ApiError, not_found

REPORT_GLOB = "RTM-COVERAGE-*.yaml"


def latest_report(directory: Path) -> Path | None:
    """最新（修改時間，同刻取檔名較大者）的 `RTM-COVERAGE-*.yaml`；沒有＝None。"""
    if not directory.is_dir():
        return None
    candidates = [p for p in directory.glob(REPORT_GLOB) if p.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: (p.stat().st_mtime_ns, p.name))


def _unreadable(detail: str) -> ApiError:
    return ApiError(422, "rtm_unreadable", detail=detail[:200])


def _number(summary: dict[str, Any], key: str) -> int | float:
    value = summary.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _unreadable(f"summary.{key} 缺漏或不是數字")
    return value


def _id_list(doc: dict[str, Any], key: str) -> list[str]:
    value = doc.get(key)
    return [str(v) for v in value] if isinstance(value, list) else []


def load_report(path: Path) -> dict[str, Any]:
    """報告檔 → 契約形狀。壞檔（讀不動、不是 YAML、不是映射、缺 `summary` 或核心數字）＝422
    `rtm_unreadable`。
    `unmapped_at_ids`／`summary.unmapped_at` 是 §8.5 新增欄：舊報告沒有它們，缺欄視為 `[]`／0。"""
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError, yaml.YAMLError) as exc:
        raise _unreadable(f"{type(exc).__name__}: {exc}") from exc
    if not isinstance(doc, dict):
        raise _unreadable("報告不是 YAML 映射")
    summary = doc.get("summary")
    if not isinstance(summary, dict):
        raise _unreadable("缺少 summary")
    unmapped_ids = _id_list(doc, "unmapped_at_ids")
    unmapped = summary.get("unmapped_at")
    return {
        "scenario": doc.get("scenario"),
        "spec_digest": doc.get("spec_digest"),
        "at": {"passed": _number(summary, "passed_at"), "total": _number(summary, "total_at"),
               "pct": _number(summary, "at_coverage_pct"),
               "unmapped": unmapped if isinstance(unmapped, int) and not isinstance(unmapped, bool)
               else len(unmapped_ids)},
        "ac": {"covered": _number(summary, "covered_ac"), "total": _number(summary, "total_ac"),
               "pct": _number(summary, "ac_coverage_pct")},
        "failed_at_ids": _id_list(doc, "failed_at_ids"),
        "weak_regex_at_ids": _id_list(doc, "weak_regex_at_ids"),
        "unmapped_at_ids": unmapped_ids,
        "fully_covered": bool(summary.get("fully_covered")),
        "advisory": True,
    }


def read_run_rtm(checkpoint_dir: Path, run_id: str) -> dict[str, Any]:
    """沒有報告檔（沒啟用 SDD 治理、run 尚未結束、run 不是正常走完）＝404 `rtm_not_found`。"""
    path = latest_report(checkpoint_dir / "rtm")
    if path is None:
        raise not_found("rtm_not_found", run_id=run_id)
    return load_report(path)
