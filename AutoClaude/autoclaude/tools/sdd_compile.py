"""sdd_compile — SDD 規格 → 標準 playbook YAML 編譯 CLI（plugin_entry tier ≤250）。

對應 AutoSDD_improving_01.md §3.3（W4，compile-then-run 兩段式第一段）：

    python -m autoclaude.tools.sdd_compile --spec-dir <docs path> --out <playbook.yaml>

第二段走既有入口 `python -m autoclaude <playbook.yaml>`，runner 路徑零修改：
  - 編譯產物為標準 playbook YAML（schema 與手寫 playbook 完全一致）
  - 執行時照常通過 pre_run_validator 與 CONDITIONAL 三層防禦（§1.3 截斷點 3）
  - 兩段之間留人工檢視點（SCG-4 PR Review 精神：生成物 = 待審工件）
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from ..core.ports.spec_source import (
    SpecFormatVersionError,
    SpecNotFrozenError,
    SpecTaintedError,
)
from ..infra.adapters.sdd_to_playbook_adapter import SddToPlaybookAdapter
from ..models.playbook import Playbook


def compile_spec(
    spec_dir: str,
    *,
    project: str = "sdd-project",
    global_goal: str | None = None,
    workflow_type: str = "aisdlc_sdd",
    fsm_state_path: str | None = None,
    test_path: str = "tests",
) -> Playbook:
    """SDD 規格目錄 → 已驗證的 Playbook 模型（供 CLI 與測試共用）。"""
    adapter = SddToPlaybookAdapter(
        fsm_state_path=fsm_state_path, test_path=test_path
    )
    spec = adapter.load_spec(spec_dir)
    tasks = adapter.compile_tasks(spec)
    if not tasks:
        raise ValueError(f"{spec_dir}: 規格中無任何 AC→AT 契約，無可編譯步驟")
    payload = {
        "version": "1.0",
        "project": project,
        "global_goal": global_goal
        or f"完成 {spec.scenario} 場景全部 {len(tasks)} 條 AT 契約"
           f"（規格 digest {spec.digest.split(':')[-1][:8]}）",
        "workflow_type": workflow_type,
        # 執行期 SddGovernancePlugin 以 workflow_path 為規格目錄錨點
        # （PRE_RUN 重載規格 → digest 防 drift + SCG 閘門映射）
        "workflow_path": spec_dir,
        "tasks": [t.model_dump(exclude_none=True) for t in tasks],
    }
    # 末端自驗：產物必須通過與 runner 載入端相同的 Playbook schema 驗證
    return Playbook.model_validate(payload)


def main(argv: list[str] | None = None) -> int:
    # DEF-101-789 家族：本 CLI 的錯誤訊息全是中文，Windows 非 UTF-8 終端下
    # stdout（預設 errors='strict'）直接 UnicodeEncodeError，stderr（預設
    # errors='backslashreplace'）則把訊息印成 \uXXXX 逃脫字面 —— 兩者都讓
    # 「規格未凍結」這類硬閘的理由讀不到。同 tools/mutation_analysis.py 慣例。
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass
    parser = argparse.ArgumentParser(
        prog="python -m autoclaude.tools.sdd_compile",
        description="編譯已凍結的 AISDLC-SDD 規格為標準 AutoClaude playbook YAML",
    )
    parser.add_argument("--spec-dir", required=True, help="SDD docs/ 規格目錄")
    parser.add_argument("--out", required=True, help="輸出 playbook YAML 路徑")
    parser.add_argument("--project", default="sdd-project")
    parser.add_argument("--global-goal", default=None)
    parser.add_argument(
        "--workflow-type", default="aisdlc_sdd", choices=("aisdlc", "aisdlc_sdd")
    )
    parser.add_argument("--fsm-state-path", default=None,
                        help="顯式 FSM 狀態檔（預設自 spec-dir 向上搜尋）")
    parser.add_argument("--test-path", default="tests",
                        help="evaluator 白名單模板的 pytest 目標路徑")
    args = parser.parse_args(argv)

    try:
        playbook = compile_spec(
            args.spec_dir,
            project=args.project,
            global_goal=args.global_goal,
            workflow_type=args.workflow_type,
            fsm_state_path=args.fsm_state_path,
            test_path=args.test_path,
        )
    except SpecNotFrozenError as exc:
        print(f"[sdd_compile] 規格未凍結（Spec-First 硬閘）：{exc}", file=sys.stderr)
        return 2
    except SpecTaintedError as exc:
        print(f"[sdd_compile] 規格遭汙染（SPEC_TAINTED）：{exc}", file=sys.stderr)
        return 3
    except SpecFormatVersionError as exc:
        # W-85-2：原 main() 未接此例外 → 版本漂移時噴未捕捉 traceback + exit 1（非乾淨退碼）。
        print(f"[sdd_compile] 規格格式版本不受支援（防漂移 fail-closed）：{exc}",
              file=sys.stderr)
        return 5
    except (FileNotFoundError, ValueError) as exc:
        print(f"[sdd_compile] {exc}", file=sys.stderr)
        return 4

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        yaml.safe_dump(
            playbook.model_dump(exclude_none=True),
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    print(f"[sdd_compile] 已輸出 {len(playbook.tasks)} 步驟 → {out}")
    print("[sdd_compile] 請人工 review 後以 `python -m autoclaude` 執行（兩段式）")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
