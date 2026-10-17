"""sdd_compile — SDD 規格 → 標準 playbook YAML 編譯 CLI（plugin_entry tier ≤250）。

對應 AutoSDD_improving_01.md §3.3（W4，compile-then-run 兩段式第一段）：

    python -m autoclaude.tools.sdd_compile --spec-dir <docs path> --out <playbook.yaml>

第二段走既有入口 `python -m autoclaude <playbook.yaml>`，runner 路徑零修改：
  - 編譯產物為標準 playbook YAML（schema 與手寫 playbook 完全一致）
  - 執行時照常通過 pre_run_validator 與 CONDITIONAL 三層防禦（§1.3 截斷點 3）
  - 兩段之間留人工檢視點（SCG-4 PR Review 精神：生成物 = 待審工件）

退出碼（improving_115／ADR-XPLAT-016 §8.2-8.3）：0 成功；2 規格未凍結或凍結後內容已變更；
3 規格遭汙染；4 缺檔／參數不合法／規格有歧義；5 規格格式版本不受支援；
6 規格中有 AT 字樣出現卻未編成步驟（fail-closed，不寫輸出檔、無覆寫旗標）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from ..core.ports.spec_source import (
    AT_ID_PATTERN,
    SpecDigestMismatchError,
    SpecFormatVersionError,
    SpecNotFrozenError,
    SpecTaintedError,
)
from ..infra.adapters.sdd_to_playbook_adapter import SddToPlaybookAdapter
from ..models.playbook import Playbook


class SpecAtUnmappedError(ValueError):
    """規格宣告位置出現了 AT 字樣，卻沒編成任何 step（CLI rc 6；ADR-XPLAT-016 §8.2）。

    先前這類 AT（如模板 §4 的 `AT-{NNN}-E-n`、舊編號、AC 與 AT 前兩段不一致的列）被靜默丟棄，
    Console 顯示的 step 數少於規格卻沒有任何人被告知。修法只有三條：補進 §1 AC→AT 映射表、
    改成合文法的 ID、或刪掉——所以沒有覆寫旗標。
    """

    def __init__(self, at_ids: tuple[str, ...], spec_path: str) -> None:
        self.at_ids = tuple(at_ids)
        super().__init__(
            f"{spec_path}: 規格中有 {len(self.at_ids)} 個 AT 字樣出現卻未編成步驟："
            f"{', '.join(self.at_ids)}（合文法：{AT_ID_PATTERN}，前兩段＝所屬 AC，"
            "且該列的 AC id 須與之一致）"
        )


def compile_spec(
    spec_dir: str,
    *,
    project: str = "sdd-project",
    global_goal: str | None = None,
    workflow_type: str = "aisdlc_sdd",
    fsm_state_path: str | None = None,
    test_path: str = "tests",
    spec_file: str | None = None,
    fsm_project: str | None = None,
) -> Playbook:
    """SDD 規格目錄（或規格檔）→ 已驗證的 Playbook 模型（供 CLI 與測試共用）。

    spec_file：同一目錄有多份 TCS 時具名指定（相對 spec_dir 或絕對）；此時 playbook 的
    workflow_path 是**檔案**路徑（引擎 PRE_RUN 的 load_spec 把檔案路徑視為 spec_file）。
    fsm_project：FSM 專案鍵；None＝讀環境 SDD_PROJECT（與引擎執行期同一條）。
    """
    adapter = SddToPlaybookAdapter(
        fsm_state_path=fsm_state_path, test_path=test_path, fsm_project=fsm_project
    )
    spec = adapter.load_spec(spec_dir, spec_file)
    if spec.unmapped_at_ids:  # fail-closed：出現卻未編成的 AT 不得被靜默丟棄
        raise SpecAtUnmappedError(spec.unmapped_at_ids, spec.spec_path)
    tasks = adapter.compile_tasks(spec)
    if not tasks:
        raise ValueError(f"{spec_dir}: 規格中無任何 AC→AT 契約，無可編譯步驟")
    by_file = spec_file is not None or Path(spec_dir).is_file()
    payload = {
        "version": "1.0",
        "project": project,
        "global_goal": global_goal
        or f"完成 {spec.scenario} 場景全部 {len(tasks)} 條 AT 契約"
           f"（規格 digest {spec.digest.split(':')[-1][:8]}）",
        "workflow_type": workflow_type,
        # 執行期 SddGovernancePlugin 以 workflow_path 為規格錨點（PRE_RUN 重載規格 →
        # digest 防 drift + SCG 閘門映射）：指定了規格檔就錨定到檔案，否則維持目錄（現行）
        "workflow_path": spec.spec_path if by_file else spec_dir,
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
    parser.add_argument("--spec-dir", required=True, help="SDD docs/ 規格目錄（亦可直接給規格檔）")
    parser.add_argument("--spec-file", default=None,
                        help="同一目錄有多份 TCS 時具名指定一份（相對 spec-dir 或絕對，須在其下、"
                             ".md）；指定後 playbook 的 workflow_path 是該檔案路徑")
    parser.add_argument("--fsm-project", default=None,
                        help="FSM 專案鍵（選 FSM-STATE-<鍵>.yaml）；省略＝讀環境 SDD_PROJECT"
                             "（與引擎執行期同一條）；空字串＝明確不指定。"
                             "同目錄多個狀態檔又無鍵即 rc=2")
    parser.add_argument("--out", required=True, help="輸出 playbook YAML 路徑")
    parser.add_argument("--project", default="sdd-project")
    parser.add_argument("--global-goal", default=None)
    parser.add_argument(
        "--workflow-type", default="aisdlc_sdd", choices=("aisdlc", "aisdlc_sdd")
    )
    parser.add_argument("--fsm-state-path", default=None,
                        help="顯式 FSM 狀態檔（預設自 spec-dir 向上搜尋）；執行期仍自 spec-dir "
                             "向上搜尋，狀態檔不在祖先鏈上時 rc=2")
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
            spec_file=args.spec_file,
            fsm_project=args.fsm_project,
        )
    except SpecDigestMismatchError as exc:  # 必須先於 SpecNotFrozenError（其子類）
        print(f"[sdd_compile] 凍結後規格內容已變更（摘要不符，Spec-First 硬閘）：{exc}",
              file=sys.stderr)
        return 2
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
    except SpecAtUnmappedError as exc:  # 必須先於一般 ValueError（其父類）
        print(f"[sdd_compile] fail-closed，不寫輸出檔：{exc}", file=sys.stderr)
        return 6
    except (FileNotFoundError, ValueError) as exc:
        print(f"[sdd_compile] {exc}", file=sys.stderr)
        return 4

    if args.fsm_state_path:
        # D-SBR-04：--fsm-state-path 只作用於編譯期。執行期 PRE_RUN 以 workflow_path 向上搜尋
        # 狀態檔（playbook 沒有欄位帶它），所以狀態檔在祖先鏈之外時編譯會綠、執行卻在 PRE_RUN
        # 被 SPEC_NOT_FROZEN 否決。以執行期等價呼叫（不帶 fsm_state_path；workflow_path 與
        # playbook 所帶一致：指定了規格檔就是檔案路徑）預檢，提前到編譯期失敗。
        try:
            SddToPlaybookAdapter().load_spec(playbook.workflow_path)
        except SpecNotFrozenError as exc:
            print("[sdd_compile] 執行期 PRE_RUN 找不到凍結的 FSM 狀態檔，會以 SPEC_NOT_FROZEN "
                  "否決此 playbook（--fsm-state-path 不隨 playbook 帶到執行期；請把狀態檔放在 "
                  f"spec-dir 祖先鏈的 build/reports/fsm/）：{exc}", file=sys.stderr)
            return 2

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        yaml.safe_dump(
            playbook.model_dump(exclude_none=True),
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
        newline="\n",
    )
    print(f"[sdd_compile] 已輸出 {len(playbook.tasks)} 步驟 → {out}")
    print("[sdd_compile] 請人工 review 後以 `python -m autoclaude` 執行（兩段式）")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
