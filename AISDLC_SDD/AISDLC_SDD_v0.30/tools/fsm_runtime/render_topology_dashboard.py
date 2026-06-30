"""render_topology_dashboard.py — W-66-1 舵手可審批儀表板 CLI（read-only observer）.

GAP-Y2 closure（improving_66, B 軌, Rule 9.37）：meta⁸ 互遞迴呼叫圖可審批儀表板
`steersman_renderer.render_recursion_topology_dashboard`（Phase Y / ACT-160/161）在 v0.25 以前
**只在測試裡被呼叫**、runtime 零 wire、無 CLI 入口——舵手實際做 K=1 signoff proposed 互遞迴算子時，
打開 `value-dimension-ledger.yaml` 看到的仍是原始 `recursion_inventions`（帶 rank 的鄰接 dict），
盲簽問題只在測試裡解決、活迴圈裡沒有。

本 CLI 是「讀 ledger 的 proposed 算子 → 過 `guard_visualization_bounded` → 印
`render_recursion_topology_dashboard`」的**薄殼觀察者**，斷此盲簽鏈：

  · **read-only 純觀察者（Rule 9.37.4）**：只**讀** `value-dimension-ledger.yaml` 既有
    `recursion_inventions`（genesis 既已持久化），**永不寫 FSM-STATE / 不影響 churn / 不影響 meta-loop**。
  · **對抗分離乾淨（Rule 9.37.4）**：只 import 渲染器（`recursion_topology_view` /
    `steersman_renderer`）與 guard（`meta_halt_monitor`），**零 import 任何 generator**
    （`operator_*_genesis` / `dimension_semantics_synthesizer` / `vocabulary_genesis` /
    `embodied_grounding_oracle`）。op_dict 直接取自 ledger 已序列化之 `operator`（不需 import
    `RecursiveOperator` 重建），故連 generator 模組都不載入。
  · **呈現前必過 guard（Rule 9.37 VisualizationBounded）**：render budget + PY-2 拓樸防偽 +
    接地 fail-closed；**不提供任何繞過 guard 的 raw 渲染開關**（DoD #2）。guard 違反 →
    非零 exit + 不印儀表板（fail-loud，絕不 false-green）。

用法（以 `AISDLC_SDD_v0.26/` 版本目錄為 cwd 執行，`tools.fsm_runtime` 為 namespace package）：
  python -m tools.fsm_runtime.render_topology_dashboard [--ledger PATH] [--rule-id RCR-xxx]
      [--page N] [--fold] [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, List, Mapping, Optional, Sequence, Tuple

import yaml

from . import recursion_topology_view as _v
from . import steersman_renderer as _sr
from .meta_halt import meta_halt_monitor as _mm
from .state_loader import REPO_ROOT

# 預設 ledger 路徑（與 operator_recursion_genesis.DIM_LEDGER_PATH 同源，但**不 import** generator）。
DEFAULT_LEDGER_PATH = REPO_ROOT / "build" / "state" / "value-dimension-ledger.yaml"


class DashboardCLIError(RuntimeError):
    """fail-loud：ledger 缺檔 / 缺段 / rule-id 不存在 → 明確訊息 + 非零 exit（絕不靜默空輸出）。"""


def _load_proposals(ledger_path: Path) -> List[Tuple[str, Mapping[str, Any]]]:
    """讀 ledger 的 `recursion_inventions[].selected[]`，回 `[(rule_id, op_dict), ...]`（read-only）.

    op_dict ＝ `proposal['operator']`（即 `RecursiveOperator.to_dict()`，含 ranks/edges/fuel…）；
    rule_id 由 fingerprint 還原（`RCR-<fingerprint 去冒號>`，對齊 genesis `record_round_proposal`）。
    """
    if not ledger_path.exists():
        raise DashboardCLIError(
            f"ledger 不存在：{ledger_path}（genesis 尚未落任何 recursion_inventions 提案？）")
    data = yaml.safe_load(ledger_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise DashboardCLIError(f"ledger 格式非法（頂層非 mapping）：{ledger_path}")
    inventions = data.get("recursion_inventions")
    if not isinstance(inventions, list) or not inventions:
        raise DashboardCLIError(
            f"ledger 無 `recursion_inventions` 段或為空：{ledger_path}（無 proposed 互遞迴算子可審批）")
    out: List[Tuple[str, Mapping[str, Any]]] = []
    for rnd in inventions:
        if not isinstance(rnd, dict):
            continue
        for prop in rnd.get("selected") or []:
            if not isinstance(prop, dict):
                continue
            op = prop.get("operator")
            if not isinstance(op, dict):
                continue
            fp = str(prop.get("fingerprint") or op.get("fingerprint") or "")
            rid = ("RCR-" + fp.replace(":", "-")) if fp else "RCR-(未知指紋)"
            out.append((rid, op))
    if not out:
        raise DashboardCLIError(
            f"`recursion_inventions` 內無可解析的 proposed 算子（selected[].operator 缺漏）：{ledger_path}")
    return out


def render_one(op_dict: Mapping[str, Any], *, page: int, fold: bool, as_json: bool) -> str:
    """單一算子 → extract_topology → **必過 guard** → 渲染.

    guard 違反（render budget 逃逸 / 拓樸防偽 / 接地 false-green）→ 向上拋 `VisualizationViolation`，
    由 `main` 轉為非零 exit（fail-loud）。**無繞過 guard 的開關**。
    """
    view = _v.extract_topology(op_dict, budget=_v.render_budget(), page_cursor=page)
    if fold:
        view = _v.fold_topology(view)
    # 呈現前必過 guard（render budget + PY-2 拓樸防偽 + 接地 fail-closed）；不提供繞過開關。
    _mm.guard_visualization_bounded(view, op_dict)   # 違反 → raise VisualizationViolation
    if as_json:
        return json.dumps(_v.render_json(view), ensure_ascii=False, indent=2)
    return _sr.render_recursion_topology_dashboard(view)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="render_topology_dashboard",
        description="舵手可審批儀表板 CLI（read-only observer）：把 ledger 的 proposed 互遞迴算子"
                    "投影成有界、防偽的人類 K=1 signoff 儀表板（Rule 9.37）。")
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER_PATH,
                        help=f"value-dimension-ledger.yaml 路徑（預設 {DEFAULT_LEDGER_PATH}）")
    parser.add_argument("--rule-id", default=None,
                        help="只渲染指定 RCR-xxx 算子（預設：全部 proposed 算子）")
    parser.add_argument("--page", type=int, default=0, help="分頁游標（大圖有界截斷，預設 0）")
    parser.add_argument("--fold", action="store_true", help="開啟鏈塌縮降維（PY-3 fold_topology）")
    parser.add_argument("--json", dest="as_json", action="store_true",
                        help="輸出機讀 JSON（render_json）而非 Markdown")
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        proposals = _load_proposals(args.ledger)
    except DashboardCLIError as exc:
        print(f"[render_topology_dashboard] FAIL（fail-loud）：{exc}", file=sys.stderr)
        return 2

    if args.rule_id:
        proposals = [(rid, op) for (rid, op) in proposals if rid == args.rule_id]
        if not proposals:
            print(f"[render_topology_dashboard] FAIL（fail-loud）：rule-id {args.rule_id} "
                  f"在 ledger 中無對應 proposed 算子。", file=sys.stderr)
            return 2

    blocks: List[str] = []
    for rid, op in proposals:
        try:
            body = render_one(op, page=args.page, fold=args.fold, as_json=args.as_json)
        except _mm.VisualizationViolation as exc:
            # 拓樸防偽 / render budget / 接地 false-green 任一 → fail-closed：非零 exit + 絕不印儀表板。
            print(f"[render_topology_dashboard] BLOCKED（Rule 9.37 VisualizationBounded fail-closed）"
                  f" {rid}：{exc}", file=sys.stderr)
            return 3
        blocks.append(f"<!-- {rid} -->\n{body}")

    print("\n\n---\n\n".join(blocks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
