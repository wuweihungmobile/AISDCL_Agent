"""AutoSDD_improving_95 W-95-2 — bridge e2e harness 確定性部分單測（RTM-95-2/3/5）。

只測確定性純函式（compile_plan / parse_e2e_log / build_evidence）；真跑 subprocess
（run_autoclaude，花真 Claude token）不在單測覆蓋——對齊規格 §3.2「LLM 真跑不寫死測試」。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TOOLS = _REPO_ROOT / "tools"
for _p in (str(_REPO_ROOT), str(_TOOLS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import run_bridge_e2e as rbe  # noqa: E402
from three_tier_to_playbook import CompileError  # noqa: E402

_STRUTILS_PLAN = _REPO_ROOT / "scripts" / "bridge_e2e" / "strutils_prd_plan.yaml"


# --- RTM-95-1/2：Archy 真跑產物經 compiler 攤平 ---

def test_compile_strutils_plan_flattens_5_tasks_with_goal_grouping():
    """RTM-95-2：strutils plan → 5 task，goal_task_id 正確分組（GT-SPEC×1 + GT-IMPL×4）。"""
    pb, yaml_text = rbe.compile_plan(_STRUTILS_PLAN)
    assert len(pb.tasks) == 5
    assert pb.project == "strutils 字串工具庫"
    assert pb.workflow_type == "aisdlc_sdd"
    by_goal = {}
    for t in pb.tasks:
        by_goal.setdefault(t.goal_task_id, []).append(t.step_id)
    assert by_goal["GT-SPEC"] == ["E-SPEC-1"]
    assert by_goal["GT-IMPL"] == ["E-IMPL-1", "E-IMPL-2", "E-IMPL-3", "E-IMPL-4"]
    # improving_96 DEF-95-002 修復：全 5 步皆 backend-robust 客觀 evaluator、無 keyword regex。
    # 兩類：①可跑測試的「實作至綠」步（E-IMPL-2/4）→ pytest；②產/改檔步（E-SPEC-1 寫 SPEC.md、
    # E-IMPL-1/3 寫改 test_strutils.py）→ artifact-existence（autoclaude-artifact-check
    # console script；R52 修正原 `python -m autoclaude.artifact_check` 裸 python 跨平台缺陷）。
    evals = {t.step_id: t.evaluator_command for t in pb.tasks if t.evaluator_command}
    assert set(evals) == {"E-SPEC-1", "E-IMPL-1", "E-IMPL-2", "E-IMPL-3", "E-IMPL-4"}
    assert evals["E-IMPL-2"].startswith("pytest ")
    assert evals["E-IMPL-4"].startswith("pytest ")
    for sid in ("E-SPEC-1", "E-IMPL-1", "E-IMPL-3"):
        assert evals[sid].startswith("autoclaude-artifact-check ")
    # backend-robust 核心斷言：無任一步以 keyword 回顯（expected_output_regex）把關
    assert all(t.expected_output_regex is None for t in pb.tasks)
    assert "tasks:" in yaml_text  # 可序列化


def test_compile_strutils_plan_loadable_back_as_playbook():
    """RTM-95-1：攤平產物可被 Playbook.model_validate 重新載入（合法 playbook）。"""
    import yaml as _yaml

    from autoclaude.models.playbook import Playbook
    _pb, yaml_text = rbe.compile_plan(_STRUTILS_PLAN)
    reloaded = Playbook.model_validate(_yaml.safe_load(yaml_text))
    assert len(reloaded.tasks) == 5
    assert reloaded.tasks[0].step_id == "E-SPEC-1"


# --- RTM-95-5：安全——惡意 evaluator 經 compile 鏈 fail-closed ---

def test_bridge_e2e_evaluator_sanitize_chain_rejects_injection(tmp_path):
    """RTM-95-5：Archy 產物若帶惡意 evaluator_command，compile_plan 一律 fail-closed 拒絕。"""
    evil = tmp_path / "evil_plan.yaml"
    evil.write_text(
        'project_id: "PRJ-EVIL"\n'
        'name: "evil"\n'
        "goal_tasks:\n"
        '  - goal_task_id: "G1"\n'
        '    title: "g"\n'
        "    depth: 1\n"
        "    execution_items:\n"
        '      - exec_id: "E1"\n'
        '        action: "a"\n'
        '        evaluator_command: "pytest x && rm -rf /"\n',  # shell 串接元字元
        encoding="utf-8",
    )
    with pytest.raises(CompileError):
        rbe.compile_plan(evil)


def test_artifact_check_evaluator_passes_sanitizer():
    """RTM-96-2：artifact-existence evaluator 形態通過白名單消毒（improving_96 DEF-95-002）。

    回歸鎖：doc/spec 步用的 `autoclaude-artifact-check <path> --min-bytes N`（R52 修正後
    的推薦形態，console script、免猜 python/python3）必須永遠通過 sanitize_evaluator
    （首 token autoclaude-artifact-check、無 shell 元字元）。
    """
    from three_tier_to_playbook import sanitize_evaluator  # noqa: E402

    cmd = "autoclaude-artifact-check SPEC.md --min-bytes 200"
    assert sanitize_evaluator(cmd) == cmd


def test_artifact_check_evaluator_legacy_python_form_still_passes_sanitizer():
    """向下相容回歸鎖：R52 修正前既有 playbook 可能已落盤 `python -m
    autoclaude.artifact_check <path> --min-bytes N` 形態（首 token python、-m 形態非
    -c、無 shell 元字元），sanitize_evaluator 不得因新增 autoclaude-artifact-check
    白名單而破壞既有向下相容。
    """
    from three_tier_to_playbook import sanitize_evaluator  # noqa: E402

    cmd = "python -m autoclaude.artifact_check SPEC.md --min-bytes 200"
    assert sanitize_evaluator(cmd) == cmd


# --- RTM-95-3：log 解析 + 證據 schema（餵 canned log，不打真 LLM）---

# 🔴 canned log 刻意保留 `[INFO]` 等級標籤前綴 + completed_step_ids（鏡像 W-95-3 真跑實況）：
#   回歸鎖 log-level 標籤被誤當 step_id 的解析 bug（gap 跨 `[` 吃掉 `[E-SPEC-1] ✓`）。
_CANNED_LOG = (
    "2026-06-29 10:00:00 [INFO] autoclaude: Playbook 模式啟動\n"
    "2026-06-29 10:01:00 [INFO] === STEP_TOKEN_PEAK | step=E-SPEC-1 pct=3.1200 ===\n"
    "2026-06-29 10:02:00 [INFO] === STEP_TOKEN_PEAK | step=E-IMPL-2 pct=8.4500 ===\n"
    "2026-06-29 10:05:00 [INFO] autoclaude: Playbook 結束 | KernelResult(success=True, "
    "completed_steps=5, total_steps=5, reason='success', step_log=["
    "'[E-SPEC-1] 需求/設計凍結（SCG-0~1）：slugify/tru… ✓ (attempt 1)', "
    "'[E-IMPL-1] 測試骨架 ✓ (attempt 1)', "
    "'[E-IMPL-2] 實作 slugify ✓ (attempt 2)', '[E-IMPL-3] 加測試 ✓ (attempt 1)', "
    "'[E-IMPL-4] 實作 truncate ✓ (attempt 1)'], "
    "completed_step_ids=['E-SPEC-1', 'E-IMPL-1', 'E-IMPL-2', 'E-IMPL-3', 'E-IMPL-4'], "
    "escalated=False, peak_token_pct=8.4500)\n"
)


def test_parse_e2e_log_extracts_steps_tokens_and_kernel_result():
    """RTM-95-3：解析出每步 ✓ attempt、權威 completed_ids、per-step token%、整輪 KernelResult。"""
    parsed = rbe.parse_e2e_log(_CANNED_LOG)
    # 🔴 回歸鎖：`[INFO]` 標籤不得被當 step_id；E-SPEC-1 的 ✓ 不得被前綴標籤跨越吃掉。
    assert parsed["ok_steps"] == {
        "E-SPEC-1": 1, "E-IMPL-1": 1, "E-IMPL-2": 2, "E-IMPL-3": 1, "E-IMPL-4": 1,
    }
    assert "INFO" not in parsed["ok_steps"]
    assert parsed["completed_ids"] == ["E-SPEC-1", "E-IMPL-1", "E-IMPL-2", "E-IMPL-3", "E-IMPL-4"]
    assert parsed["step_token_pct"] == {"E-SPEC-1": 3.12, "E-IMPL-2": 8.45}
    kr = parsed["kernel_result"]
    assert kr["success"] is True
    assert kr["completed_steps"] == 5 and kr["total_steps"] == 5
    assert kr["escalated"] is False
    assert kr["peak_token_pct"] == 8.45


def test_parse_e2e_log_empty_when_no_markers():
    """無任何標記（dry-run/啟動即敗）→ 全空、kernel_result=None。"""
    parsed = rbe.parse_e2e_log("nothing useful here\n")
    assert parsed["ok_steps"] == {}
    assert parsed["completed_ids"] == []
    assert parsed["step_token_pct"] == {}
    assert parsed["kernel_result"] is None


def test_build_evidence_joins_goal_task_and_aggregates():
    """RTM-95-3：證據 join goal_task_id + aggregate pass_rate/分組正確 + schema 完整可讀回。"""
    pb, _ = rbe.compile_plan(_STRUTILS_PLAN)
    parsed = rbe.parse_e2e_log(_CANNED_LOG)
    ev = rbe.build_evidence(pb, parsed, source="plan.yaml", config="cfg.yaml")
    assert ev["schema"] == "autosdd_bridge_e2e_evidence/v1"
    assert ev["aggregate"]["total_steps"] == 5
    assert ev["aggregate"]["success_steps"] == 5
    assert ev["aggregate"]["pass_rate"] == 1.0
    assert ev["aggregate"]["evaluator_steps"] == 5  # 全 5 步 backend-robust 客觀 evaluator
    assert ev["aggregate"]["escalated"] is False
    assert ev["aggregate"]["kernel_success"] is True
    # goal_task 分組
    assert ev["by_goal_task"]["GT-SPEC"] == {"steps": 1, "success": 1}
    assert ev["by_goal_task"]["GT-IMPL"] == {"steps": 4, "success": 4}
    # per-step join：E-IMPL-2 帶 evaluator + attempt 2（非 first_pass）+ token%
    s2 = next(s for s in ev["per_step"] if s["step_id"] == "E-IMPL-2")
    assert s2["goal_task_id"] == "GT-IMPL"
    assert s2["success"] is True and s2["first_pass"] is False
    assert s2["has_evaluator"] is True and s2["token_pct"] == 8.45
    # 整份可序列化讀回（schema 完整）
    assert json.loads(json.dumps(ev, ensure_ascii=False))["project"] == pb.project


def test_build_evidence_marks_failed_step_when_not_in_ok():
    """部分失敗：未出現 ✓ 的步 success=False、pass_rate 反映真值。"""
    pb, _ = rbe.compile_plan(_STRUTILS_PLAN)
    # 只前 3 步成功（E-IMPL-4 escalated 未完成）
    partial = (
        "[E-SPEC-1] 規格 ✓ (attempt 1)\n[E-IMPL-1] 測試 ✓ (attempt 1)\n"
        "[E-IMPL-2] 實作 ✓ (attempt 1)\n"
        "KernelResult(success=False, completed_steps=3, total_steps=5, "
        "reason='escalated', escalated=True, peak_token_pct=0.0)\n"
    )
    parsed = rbe.parse_e2e_log(partial)
    ev = rbe.build_evidence(pb, parsed, source="p", config="c")
    assert ev["aggregate"]["success_steps"] == 3
    assert ev["aggregate"]["pass_rate"] == 0.6
    assert ev["aggregate"]["escalated"] is True
    s4 = next(s for s in ev["per_step"] if s["step_id"] == "E-IMPL-4")
    assert s4["success"] is False and s4["token_pct"] is None
