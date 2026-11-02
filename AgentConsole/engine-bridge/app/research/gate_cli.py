"""gate evaluator 的命令列入口（AutoClaude 步驟的 `evaluator_command`；ADR-003 D1）。

每個研究 stage 步驟結束後由引擎以 `<python> -m app.research.gate_cli <check> …` 驗收 agent 的產出：
  rc 0＝合格；rc 1＝有違規（每行一條 `[規則] 路徑: 說明` 印到 stderr，引擎把它帶進下一次重試）；
  rc 2＝用法錯誤。

檢查（`<check>`）與必要引數（`--workspace` 是研究工作區的絕對路徑）：
  evidence          `00_research/evidence_items.json` 的 16 條規則；
                    `--issue-scope-sha256`（任務書給的現行議題檔雜湊）、
                    選 `--fetch-index`／`--previous`（相對工作區）、`--accept-template-sentinel`
  draft             `01_specs/PRD_draft.md` 的草擬預檢 P0-1～P0-9；選 `--evidence-index`
  revise            同 draft（修訂輪的產出也走同一份預檢）
  review-dimension  `02_governance/reviews/round-<k>/<維度小寫>.json`；
                    `--dimension`、`--round`、`--prd-sha256`（任務書給的值）、
                    `--prd-path`（相對工作區）、選 `--evidence-index`

evaluator 子行程沒有資料庫、也不該有：所有外部輸入都是工作區內的檔案（任務書與 Bridge 渲染的索引）。
本模組只讀檔、不寫檔、不碰網路；入庫前 Bridge 會在行程內以同一批純函式再驗一次。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .gates.evidence import EvidenceContext, validate_evidence_items
from .gates.prd_schema import count_acs, precheck_draft
from .gates.review_card import validate_review_dimension
from .gates.schemas import DIMENSIONS, Violation, violation_lines

RC_OK, RC_INVALID, RC_USAGE = 0, 1, 2
EVIDENCE_REL = "00_research/evidence_items.json"
ISSUE_SCOPE_REL = "00_research/issue_scope.json"
PRD_DRAFT_REL = "01_specs/PRD_draft.md"


def _load_json(path: Path) -> tuple[Any, list[Violation]]:
    """嚴格讀 JSON：UTF-8、無 BOM；檔案不存在或不是 JSON 回違規（不丟例外）。"""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return None, [Violation("R1", path.name, f"檔案讀不到：{type(exc).__name__}")]
    if raw.startswith(b"\xef\xbb\xbf"):
        return None, [Violation("R1", path.name, "檔案不得含 BOM（須為 UTF-8、無 BOM）")]
    try:
        return json.loads(raw.decode("utf-8")), []
    except (UnicodeDecodeError, ValueError) as exc:
        return None, [Violation("R1", path.name, f"不是合法的 UTF-8 JSON：{exc}")]


def _optional_json(workspace: Path, rel: str | None) -> Any:
    if not rel:
        return None
    data, problems = _load_json(workspace / rel)
    return None if problems else data


def _evidence_rows(workspace: Path, rel: str | None) -> dict[str, dict[str, Any]] | None:
    data = _optional_json(workspace, rel)
    rows = data.get("rows") if isinstance(data, dict) else None
    return rows if isinstance(rows, dict) else None


def _check_evidence(workspace: Path, args: argparse.Namespace) -> list[Violation]:
    doc, problems = _load_json(workspace / EVIDENCE_REL)
    if problems:
        return problems
    fetch = _optional_json(workspace, args.fetch_index)
    fetches = fetch.get("fetches") if isinstance(fetch, dict) else None
    ctx = EvidenceContext(
        issue_scope=_optional_json(workspace, ISSUE_SCOPE_REL),
        issue_scope_sha256=args.issue_scope_sha256,
        accept_template_sentinel=args.accept_template_sentinel,
        fetch_index=fetches if isinstance(fetches, dict) else {},
        previous=_optional_json(workspace, args.previous))
    return validate_evidence_items(doc, ctx)


def _read_text(path: Path) -> tuple[str | None, list[Violation]]:
    try:
        return path.read_text(encoding="utf-8"), []
    except (OSError, UnicodeDecodeError) as exc:
        return None, [Violation("P0-1", path.name, f"檔案讀不到或不是 UTF-8：{type(exc).__name__}")]


def _check_draft(workspace: Path, args: argparse.Namespace) -> list[Violation]:
    text, problems = _read_text(workspace / PRD_DRAFT_REL)
    if text is None:
        return problems
    return precheck_draft(text, evidence_rows=_evidence_rows(workspace, args.evidence_index))


def _check_dimension(workspace: Path, args: argparse.Namespace) -> list[Violation]:
    path = workspace / "02_governance" / "reviews" / f"round-{args.round}" / (
        f"{args.dimension.lower()}.json")
    doc, problems = _load_json(path)
    if problems:
        return [Violation("V1", v.path, v.message) for v in problems]
    prd, prd_problems = _read_text(workspace / args.prd_path)
    rows = _evidence_rows(workspace, args.evidence_index)
    return validate_review_dimension(
        doc, dimension=args.dimension, round_no=args.round, prd_sha256=args.prd_sha256,
        ac_total=None if prd is None else count_acs(prd),
        evidence_numbers=None if rows is None else rows.keys()) + prd_problems


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app.research.gate_cli", description=__doc__)
    sub = parser.add_subparsers(dest="check", required=True)
    for name in ("evidence", "draft", "revise", "review-dimension"):
        item = sub.add_parser(name)
        item.add_argument("--workspace", required=True)
        item.add_argument("--evidence-index")
    sub.choices["evidence"].add_argument("--issue-scope-sha256", required=True)
    sub.choices["evidence"].add_argument("--fetch-index")
    sub.choices["evidence"].add_argument("--previous")
    sub.choices["evidence"].add_argument("--accept-template-sentinel", action="store_true")
    review = sub.choices["review-dimension"]
    review.add_argument("--dimension", required=True, choices=DIMENSIONS)
    review.add_argument("--round", required=True, type=int)
    review.add_argument("--prd-sha256", required=True)
    review.add_argument("--prd-path", required=True)
    return parser


def run(argv: Sequence[str]) -> tuple[int, list[str]]:
    """回 `(rc, 要印到 stderr 的行)`；不印、不結束行程（方便測試）。"""
    try:
        args = build_parser().parse_args(list(argv))
    except SystemExit as exc:                       # argparse 用法錯誤＝rc 2
        return (RC_USAGE if exc.code else RC_OK), []
    workspace = Path(args.workspace)
    if not workspace.is_dir():
        return RC_USAGE, [f"--workspace 不是目錄：{args.workspace}"]
    handlers = {"evidence": _check_evidence, "draft": _check_draft, "revise": _check_draft,
                "review-dimension": _check_dimension}
    problems = handlers[args.check](workspace, args)
    return (RC_INVALID if problems else RC_OK), violation_lines(problems)


def main(argv: Sequence[str] | None = None) -> int:
    rc, lines = run(sys.argv[1:] if argv is None else argv)
    for line in lines:
        print(line, file=sys.stderr)
    if rc == RC_OK:
        print("OK")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
