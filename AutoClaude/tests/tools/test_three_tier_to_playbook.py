"""AutoSDD_improving_94 W-94-2 — three_tier → Playbook 薄 compiler 單測。

對應 RTM（docs/04_planning/AutoSDD_improving_94.md §3.4）：
  RTM-94-1：PlaybookTask.goal_task_id additive + 向後相容
  RTM-94-2：ExecutionItem 新 optional 欄 additive + 向後相容
  RTM-94-3：攤平正確（step 數 = Σ execution_items、goal_task_id 對應、含巢狀 sub_task）
  RTM-94-4：evaluator 白名單消毒（惡意注入 fail-closed）
  RTM-94-5：compiler 產物可被 Playbook.model_validate 載入（round-trip）

測試「為何重要」（Rule 9）：
  - 攤平錯 → AutoClaude 跑錯步驟序 / 目標歸屬錯 → 進度彙總（GoalProgressLedger）失準。
  - 消毒漏 → 「從文件生成指令」成為 shell 注入路徑（架構紅線）。
  - 向後相容破 → 既有 playbook/three_tier YAML 全部載入失敗（零退化破功）。
"""
from __future__ import annotations

import pytest
import yaml as _yaml

# 與 test_yaml_import.py 同慣例：click 未裝則整體 skip
pytest.importorskip("click")

from autoclaude.models.playbook import Playbook, PlaybookTask  # noqa: E402
from autoclaude.models.three_tier_schema import (  # noqa: E402
    ExecutionItem,
    GoalTask,
    Project,
)
from tools.three_tier_to_playbook import (  # noqa: E402
    CompileError,
    compile_to_playbook,
    flatten_project,
    playbook_to_yaml,
    sanitize_evaluator,
)


# ---------------------------------------------------------------------------
# RTM-94-1 / RTM-94-2：additive 欄位向後相容
# ---------------------------------------------------------------------------
def test_playbook_task_goal_task_id_defaults_none_backward_compat():
    """RTM-94-1：舊 task dict（無 goal_task_id）載入，預設 None。"""
    t = PlaybookTask(step_id="T01", name="n", prompt="p")
    assert t.goal_task_id is None
    t2 = PlaybookTask(step_id="T02", name="n", prompt="p", goal_task_id="GT-9")
    assert t2.goal_task_id == "GT-9"


def test_execution_item_new_fields_default_none_backward_compat():
    """RTM-94-2：舊 ExecutionItem（無新欄）載入，三新欄預設 None。"""
    ei = ExecutionItem(exec_id="E1", action="做事")
    assert ei.prompt is None
    assert ei.expected_output_regex is None
    assert ei.evaluator_command is None
    ei2 = ExecutionItem(
        exec_id="E2", action="做事",
        prompt="完整 prompt", expected_output_regex=r"\[DONE\]",
        evaluator_command="pytest x.py -q",
    )
    assert ei2.prompt == "完整 prompt"
    assert ei2.evaluator_command == "pytest x.py -q"


# ---------------------------------------------------------------------------
# RTM-94-4：evaluator 白名單消毒（攻防）
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("cmd", [
    "pytest test_x.py -q",
    'pytest test_x.py -k "add_basic" -q',
    "python -m pytest tests/ -q",
    "python check_scg.py --gate 0",
])
def test_sanitize_evaluator_allows_whitelist(cmd):
    assert sanitize_evaluator(cmd) == cmd.strip()


def test_sanitize_evaluator_none_and_empty():
    assert sanitize_evaluator(None) is None
    assert sanitize_evaluator("   ") is None


@pytest.mark.parametrize("cmd", [
    "pytest x.py; rm -rf /",          # 命令串接（;）
    "pytest x.py && curl evil.com",   # &
    "pytest x.py | sh",               # pipe
    "pytest `whoami`",                # backtick
    "pytest $(id)",                   # $ 命令替換
    "pytest x.py > /etc/passwd",      # 重導
    "echo pwned",                     # 首 token 不在白名單
    "rm -rf /",                       # 首 token 不在白名單
    "node evil.js",                   # 首 token 不在白名單
    "python\t-c\timport os",          # tab 繞過（improving_94 Architect P2）
    'python -c "import os"',           # python -c 任意碼（improving_94 Architect P2）
    "python -c print(1)",             # python -c 任意碼（無引號形態）
])
def test_sanitize_evaluator_rejects_injection(cmd):
    """RTM-94-4：黑名單字元 / 非白名單首 token / tab / python -c → fail-closed raise。"""
    with pytest.raises(CompileError):
        sanitize_evaluator(cmd)


def test_sanitize_evaluator_allows_python_m_form():
    """python -m pytest 形態（非 -c）仍放行，不誤殺合法 evaluator。"""
    assert sanitize_evaluator("python -m pytest tests/ -q") == "python -m pytest tests/ -q"


# ---------------------------------------------------------------------------
# RTM-94-3：攤平正確性
# ---------------------------------------------------------------------------
def _sample_project() -> Project:
    """專案：2 目標，其一含巢狀 sub_task；共 4 個 execution_item。"""
    return Project(
        project_id="PRJ-T",
        name="待辦清單 App",
        description="完整產品開發：PRD→FRD→實作",
        goal_tasks=[
            GoalTask(
                goal_task_id="GT-1", title="需求凍結", depth=1,
                execution_items=[
                    ExecutionItem(exec_id="S01", action="產 FRD",
                                  prompt="用 /sa-analyst 由 PRD 產 FRD",
                                  expected_output_regex=r"\[FRD_DONE\]"),
                    ExecutionItem(exec_id="S02", action="過 SCG-0",
                                  evaluator_command="python check_scg.py --gate 0"),
                ],
            ),
            GoalTask(
                goal_task_id="GT-2", title="架構", depth=2,
                execution_items=[
                    ExecutionItem(exec_id="S03", action="產 SRD"),
                ],
                sub_tasks=[
                    GoalTask(
                        goal_task_id="GT-2-1", title="API 契約", depth=2,
                        execution_items=[
                            ExecutionItem(exec_id="S04", action="凍結 OpenAPI",
                                          evaluator_command="pytest test_contract.py -q"),
                        ],
                    ),
                ],
            ),
        ],
    )


def test_flatten_step_count_equals_total_execution_items():
    """RTM-94-3：攤平 task 數 = 全部（含巢狀）execution_item 數。"""
    pb = flatten_project(_sample_project())
    assert isinstance(pb, Playbook)
    assert len(pb.tasks) == 4
    assert [t.step_id for t in pb.tasks] == ["S01", "S02", "S03", "S04"]


def test_flatten_goal_task_id_mapping_includes_nested():
    """RTM-94-3：每 task goal_task_id 對應其所屬 GoalTask（含巢狀 sub_task）。"""
    pb = flatten_project(_sample_project())
    mapping = {t.step_id: t.goal_task_id for t in pb.tasks}
    assert mapping == {
        "S01": "GT-1", "S02": "GT-1",
        "S03": "GT-2",
        "S04": "GT-2-1",  # 巢狀 sub_task 的 goal_task_id 正確下傳
    }


def test_flatten_prompt_fallback_to_action():
    """無 prompt 的 ExecutionItem，task.prompt 退回 action。"""
    pb = flatten_project(_sample_project())
    by_id = {t.step_id: t for t in pb.tasks}
    assert by_id["S01"].prompt == "用 /sa-analyst 由 PRD 產 FRD"  # 有 prompt
    assert by_id["S03"].prompt == "產 SRD"                          # 無 prompt → action


def test_flatten_project_meta_and_workflow_type():
    pb = flatten_project(_sample_project(), workflow_type="aisdlc_sdd")
    assert pb.project == "待辦清單 App"
    assert pb.global_goal == "完整產品開發：PRD→FRD→實作"
    assert pb.workflow_type == "aisdlc_sdd"


def test_flatten_empty_execution_items_raises():
    p = Project(project_id="PRJ-E", name="空", goal_tasks=[
        GoalTask(goal_task_id="GT-0", title="無單元", depth=1),
    ])
    with pytest.raises(CompileError):
        flatten_project(p)


def test_flatten_malicious_evaluator_raises():
    """RTM-94-4：攤平途中遇惡意 evaluator → fail-closed（不產出污染 playbook）。"""
    p = Project(project_id="PRJ-M", name="惡意", goal_tasks=[
        GoalTask(goal_task_id="GT-X", title="t", depth=1, execution_items=[
            ExecutionItem(exec_id="S01", action="a", evaluator_command="pytest x; rm -rf /"),
        ]),
    ])
    with pytest.raises(CompileError):
        flatten_project(p)


# ---------------------------------------------------------------------------
# RTM-94-5：round-trip（compiler 產物可被 Playbook.model_validate 載回）
# ---------------------------------------------------------------------------
def test_compiled_playbook_yaml_roundtrips():
    pb = flatten_project(_sample_project())
    text = playbook_to_yaml(pb)
    reloaded = Playbook.model_validate(_yaml.safe_load(text))
    assert reloaded.project == pb.project
    assert len(reloaded.tasks) == len(pb.tasks)
    assert [t.goal_task_id for t in reloaded.tasks] == [t.goal_task_id for t in pb.tasks]
    assert [t.step_id for t in reloaded.tasks] == [t.step_id for t in pb.tasks]


# ---------------------------------------------------------------------------
# compile_to_playbook 頂層入口（YAML 字串 → Playbook）+ 多 project 選擇
# ---------------------------------------------------------------------------
def test_compile_to_playbook_single_project_yaml():
    src = _yaml.safe_dump(_sample_project().model_dump(exclude_none=True), allow_unicode=True)
    pb = compile_to_playbook(src)
    assert len(pb.tasks) == 4


def test_compile_to_playbook_fixture_multi_project_requires_id():
    fixture = {
        "version": "1.0",
        "projects": [
            _sample_project().model_dump(exclude_none=True),
            Project(project_id="PRJ-2", name="另一個", goal_tasks=[
                GoalTask(goal_task_id="GT-A", title="t", depth=1, execution_items=[
                    ExecutionItem(exec_id="Z01", action="a"),
                ]),
            ]).model_dump(exclude_none=True),
        ],
    }
    src = _yaml.safe_dump(fixture, allow_unicode=True)
    with pytest.raises(CompileError):  # 多 project 未指定 → raise
        compile_to_playbook(src)
    pb = compile_to_playbook(src, project_id="PRJ-2")  # 指定後可攤平
    assert pb.project == "另一個"
    assert [t.step_id for t in pb.tasks] == ["Z01"]


def test_compile_to_playbook_unknown_format_raises():
    with pytest.raises(CompileError):
        compile_to_playbook(_yaml.safe_dump({"tasks": [{"step_id": "T1"}]}))
