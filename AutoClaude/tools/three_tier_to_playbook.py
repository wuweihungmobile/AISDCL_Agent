"""AutoSDD_improving_94 W-94-2 — three_tier → 可執行 Playbook 薄 compiler。

對應規格：docs/04_planning/AutoSDD_improving_94.md §3.2 W-94-2 / §3.3 攤平規則 / RTM-94-3~5。

職責（Rule 5：code 做確定性轉換、非 AI）：
  把 three_tier_schema 的「專案→目標→任務」規劃結構（Project→GoalTask→ExecutionItem）
  **確定性攤平**為 AutoClaude runner 可執行的扁平 Playbook（project + tasks[]）。
  判斷部分（PRD→三層結構與每步 prompt）由 AISDLC_SDD 的 sdd-prd-to-playbook agent 負責，
  本工具不含任何 AI/啟發式。

支援來源 YAML（皆 three_tier 格式，非扁平 Playbook）：
  A) ThreeTierFixture（含 `projects:` 陣列）；單 project 直接攤平，多 project 需 --project-id
  B) 單一 Project（含 `project_id:`）

攤平規則（§3.3）：
  Project.name              → Playbook.project
  Project.description       → Playbook.global_goal
  DFS(goal_tasks, preorder, 含 sub_tasks 至 depth≤3〔由 three_tier model 既有強制〕)：
    每 ExecutionItem → 1 PlaybookTask（step_id=exec_id, prompt=prompt or action,
      expected_output_regex=同名欄, evaluator_command=白名單消毒, goal_task_id=所屬 GoalTask）

安全（架構紅線：「從文件生成指令」須套 CONDITIONAL 等強度消毒，fail-closed）：
  evaluator_command 採「黑名單字元集 ⊇ CONDITIONAL + 白名單首 token + 安全字集」三層，
  任一不過 → raise CompileError（拒絕，不靜默放行）。對齊
  infra/adapters/sdd_to_playbook_adapter.py 的 _DENY / 白名單模板強度。

CLI 範例：
  python tools/three_tier_to_playbook.py --source prd_project.yaml --out playbook.yaml
  python tools/three_tier_to_playbook.py --source fixture.yaml --project-id PRJ-001 --out pb.yaml
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable, Optional

import click
import yaml

# autoclaude package import — 確保可從 repo root 執行（對齊 migrate_yaml_to_db.py）
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from autoclaude.models.playbook import Playbook, PlaybookTask  # noqa: E402
from autoclaude.models.three_tier_schema import (  # noqa: E402
    ExecutionItem,
    GoalTask,
    Project,
    ThreeTierFixture,
)

# evaluator 消毒：黑名單字元集 ⊇ CONDITIONAL（對齊 sdd_to_playbook_adapter._DENY）+ 換行
_DENY = set("!`><~$&;\n\r")
# 白名單：evaluator 首 token 僅允許 pytest / python（SDD evaluator 既有形態），自由字串拒絕
_EVAL_ALLOWED_HEAD = ("pytest", "python")
# 安全字集（第二層）：word / 半形空白 / . / / / \\ / - / = / : / 引號（容 pytest -k "expr"）
# 🔴 只允許「半形空格」（非 \s）——\s 含 tab/換頁，會讓 `python\t-c\t...` 繞過首 token 白名單
# 後仍能塞任意旗標（improving_94 Architect P2 加固）。
_EVAL_SAFE = re.compile(r"""^[\w ./\\=:"'\-]+$""")


class CompileError(ValueError):
    """攤平 / 消毒失敗（fail-closed）。"""


def sanitize_evaluator(cmd: Optional[str]) -> Optional[str]:
    """evaluator_command 三層消毒；None/空 → None；不合法 → raise CompileError。"""
    if cmd is None:
        return None
    c = cmd.strip()
    if not c:
        return None
    deny_hit = sorted({ch for ch in c if ch in _DENY})
    if deny_hit:
        raise CompileError(
            f"evaluator_command 含黑名單字元 {deny_hit}（CONDITIONAL 消毒，拒絕注入）: {cmd!r}"
        )
    if not _EVAL_SAFE.match(c):
        raise CompileError(f"evaluator_command 含非白名單字集字元: {cmd!r}")
    tokens = c.split()
    head = tokens[0]
    if head not in _EVAL_ALLOWED_HEAD:
        raise CompileError(
            f"evaluator_command 首 token {head!r} 不在白名單 {_EVAL_ALLOWED_HEAD}；自由字串拒絕"
        )
    # 🔴 python 開頭時禁 `-c`（任意碼執行）——只放行 `python -m ...` 形態
    # （improving_94 Architect P2 加固：堵 `python -c "import os; ..."` 任意碼路徑）
    if head == "python" and "-c" in tokens:
        raise CompileError(
            f"evaluator_command 禁用 `python -c`（任意碼執行）；請改 `python -m ...`: {cmd!r}"
        )
    return c


def _walk(tasks: Iterable[GoalTask]) -> Iterable[GoalTask]:
    """DFS preorder 走訪 goal_tasks（含 sub_tasks）。"""
    for t in tasks:
        yield t
        yield from _walk(t.sub_tasks)


def _name_for(gt: GoalTask, ei: ExecutionItem, *, max_len: int = 80) -> str:
    base = f"{gt.title} / {ei.action}"
    return base if len(base) <= max_len else base[: max_len - 1] + "…"


def flatten_project(project: Project, *, workflow_type: str = "aisdlc_sdd") -> Playbook:
    """純函式：Project（專案→目標→任務）→ 可執行 Playbook（扁平 tasks[]）。"""
    tasks: list[PlaybookTask] = []
    for gt in _walk(project.goal_tasks):
        for ei in gt.execution_items:
            tasks.append(
                PlaybookTask(
                    step_id=ei.exec_id,
                    name=_name_for(gt, ei),
                    prompt=ei.prompt or ei.action,  # 無 prompt 退回 action 描述
                    expected_output_regex=ei.expected_output_regex,
                    evaluator_command=sanitize_evaluator(ei.evaluator_command),
                    goal_task_id=gt.goal_task_id,  # ← 三層分組落地處
                )
            )
    if not tasks:
        raise CompileError(
            f"project {project.project_id} 無任何 execution_item，攤不出可執行 playbook"
        )
    return Playbook(
        project=project.name,
        global_goal=project.description or None,
        workflow_type=workflow_type,
        tasks=tasks,
    )


def load_projects(yaml_text: str) -> list[Project]:
    """YAML 字串 → list[Project]（ThreeTierFixture 或單一 Project）。"""
    data = yaml.safe_load(yaml_text) or {}
    if not isinstance(data, dict):
        raise CompileError("YAML 頂層不是 mapping")
    if isinstance(data.get("projects"), list):
        return ThreeTierFixture(**data).projects
    if data.get("project_id"):
        return [Project(**data)]
    raise CompileError("YAML 無 projects 也無 project_id（非 three_tier 格式）")


def select_project(projects: list[Project], project_id: Optional[str]) -> Project:
    if project_id:
        for p in projects:
            if p.project_id == project_id:
                return p
        raise CompileError(f"找不到 project_id={project_id!r}")
    if len(projects) == 1:
        return projects[0]
    ids = [p.project_id for p in projects]
    raise CompileError(f"來源含多個 project（{ids}），請以 --project-id 指定")


def compile_to_playbook(
    yaml_text: str,
    *,
    project_id: Optional[str] = None,
    workflow_type: str = "aisdlc_sdd",
) -> Playbook:
    """頂層入口：three_tier YAML → 可執行 Playbook。"""
    projects = load_projects(yaml_text)
    project = select_project(projects, project_id)
    return flatten_project(project, workflow_type=workflow_type)


def playbook_to_yaml(pb: Playbook) -> str:
    """Playbook → 精簡 YAML（去 None / 去預設值，保留可讀順序）。"""
    return yaml.safe_dump(
        pb.model_dump(exclude_none=True, exclude_defaults=True),
        allow_unicode=True,
        sort_keys=False,
        width=100,
    )


@click.command(name="three-tier-to-playbook")
@click.option("--source", required=True, type=click.Path(path_type=Path),
              help="three_tier YAML（Project / ThreeTierFixture）")
@click.option("--out", type=click.Path(path_type=Path), default=None,
              help="輸出 playbook.yaml 路徑（省略則印 stdout）")
@click.option("--project-id", default=None, help="多 project 來源時選定哪個")
@click.option("--workflow-type", default="aisdlc_sdd",
              help="auto | aisdlc | aisdlc_sdd（預設 aisdlc_sdd）")
def cli(source: Path, out: Optional[Path], project_id: Optional[str], workflow_type: str) -> None:
    """SD_improving_94 W-94-2：three_tier → 可執行 Playbook 攤平工具。"""
    yaml_text = Path(source).read_text(encoding="utf-8")
    try:
        pb = compile_to_playbook(yaml_text, project_id=project_id, workflow_type=workflow_type)
    except Exception as exc:  # noqa: BLE001 — CLI 入口收斂為 exit code
        click.echo(f"ERROR: {type(exc).__name__}: {exc}", err=True)
        sys.exit(2)
    text = playbook_to_yaml(pb)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        click.echo(f"OK: 攤平 {len(pb.tasks)} 個 task（project={pb.project}）→ {out}")
    else:
        click.echo(text)


if __name__ == "__main__":
    cli()
