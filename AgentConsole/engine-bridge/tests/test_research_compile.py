"""stage run 編譯（TCS AT-960-7-1／7-2／7-3、AT-960-11-E-1；ADR-003 D1）。

被測物＝`app/research/compile/`（純函式）。每個 AT 對兩份框架樹各跑一次：夾具副本（永遠在）
與真的 SDD 樹（`SDD_ROOT` 有設就用它、否則 `load_settings` 找到的樹；不在＝`TOOL-ABSENCE`
跳過，SCG-4 須兩者皆在場、0 skipped 重跑）——副本與成品的差異是缺陷（TCS §5.2）。
"""
from __future__ import annotations

import os
import re
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from app.models import PlaybookIn
from app.research.compile import (
    NO_BACKGROUND_NOTICE,
    PROMPT_MAX_CHARS,
    CompiledStage,
    CompileError,
    StageRequest,
    allowed_tools,
    compile_role,
    compile_stage,
    defects_rel,
    evaluator_command,
    review_output_rel,
    scoring_tokens_in,
)
from app.research.compile.playbooks import canonical_sha256, claude_abs_path, quote_arg
from app.research.compile.prompts import review_protocol
from app.research.gates.schemas import DIMENSIONS, RUBRIC_REGISTRY
from app.security import DENY_CHARS
from app.settings import load_settings

FIXTURE_FRAMEWORK = Path(__file__).resolve().parent / "fixtures" / "research" / "framework"
SHA = "b" * 64
DENIED_TOOLS = ("Bash", "PowerShell", "Task", "Agent")
WEB_HOST = "blog.example.org"


def real_framework() -> Path:
    """真的 SDD 樹；缺它或缺新 agent＝TOOL-ABSENCE 跳過（SCG-4 須 0 skipped）。"""
    env = os.environ.get("SDD_ROOT")
    root = load_settings({"SDD_ROOT": env} if env else {}).sdd_root
    if root is None or not (root / "agent" / "specialized" / "spec-engineer-zh.yaml").is_file():
        pytest.skip("TOOL-ABSENCE: SDD_ROOT 不存在")
    return root


@pytest.fixture(params=["fixture", "real"])
def framework(request: pytest.FixtureRequest) -> Path:
    return FIXTURE_FRAMEWORK if request.param == "fixture" else real_framework()


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    path = tmp_path / "ws"
    path.mkdir()
    return path.resolve()


Compile = Callable[..., CompiledStage]


@pytest.fixture
def compile_with(framework: Path, workspace: Path) -> Compile:
    def build(stage: str, **overrides: Any) -> CompiledStage:
        extra: dict[str, Any] = {
            "research": {"issue_scope_sha256": "a" * 64},
            "draft": {},
            "review": {"round_no": 2, "prd_rel": "01_specs/PRD_draft.md", "prd_sha256": SHA,
                       "ac_total": 4},
            "revise": {"round_no": 1, "prd_rel": "01_specs/PRD_draft.md"},
        }[stage]
        values: dict[str, Any] = {
            "stage": stage, "slug": "demo", "workspace": workspace, "framework_root": framework,
            "step_timeout_seconds": 1200, **extra, **overrides}
        return compile_stage(StageRequest(**values))

    return build


def tools_of(compiled: CompiledStage) -> list[str]:
    extra = compiled.config_overrides["claude"]["extra_args"]
    value = extra[extra.index("--allowedTools") + 1]
    assert isinstance(value, str)
    return value.split(",")


# ── AT-960-7-1 ─────────────────────────────────────────────────────────────────────────
def test_AT_960_7_1_each_role_gets_its_minimal_allowed_tools(
        compile_with: Compile, workspace: Path) -> None:
    """寫入權限只以 `Edit(//<絕對路徑>/…)` 限定（V-R1 真機：`Write(<路徑>)` 與相對寫法在 headless
    `-p` 都被拒；裸 `Write` 能寫工作區以外）——TCS 原文的 `Write(<工作區>/…)` 因此改寫（勘誤）。"""
    scope = claude_abs_path(workspace)
    base = ["Read", "Glob", "Grep", f"Edit({scope}/**)"]
    assert tools_of(compile_with("research")) == base
    assert tools_of(compile_with("research", web_hosts=(WEB_HOST,))) == [
        *base, "WebSearch", f"WebFetch(domain:{WEB_HOST})"]
    assert tools_of(compile_with("draft", web_hosts=(WEB_HOST,))) == base
    assert tools_of(compile_with("revise", web_hosts=(WEB_HOST,))) == base
    review = tools_of(compile_with("review", web_hosts=(WEB_HOST,)))
    assert review == ["Read", "Glob", "Grep", f"Edit({scope}/02_governance/reviews/round-2/**)"]
    assert allowed_tools("review", workspace, 3)[-1].endswith("/reviews/round-3/**)")
    assert not any(t.startswith("Write") or t == "Edit" for t in review + base), "沒有裸工具"


def test_AT_960_7_1_the_path_rule_uses_the_measured_claude_syntax() -> None:
    """V-R1 真機量測的寫法：Windows `C:\\Users\\x\\ws` → `//c/Users/x/ws`、POSIX → `//home/…`。"""
    from app.research.compile import playbooks

    if os.name == "nt":
        assert claude_abs_path(Path("C:/Users/Alice/ws")) == "//c/Users/Alice/ws"
        assert claude_abs_path(Path("D:\\data\\ws")) == "//d/data/ws"
    else:
        assert claude_abs_path(Path("/home/alice/ws")) == "//home/alice/ws"
    assert claude_abs_path(Path(playbooks.__file__).resolve().parent).startswith("//")
    assert ":" not in claude_abs_path(Path(playbooks.__file__).resolve().parent)


def test_AT_960_7_1_no_role_ever_has_shell_or_agent_tools_and_only_research_has_web(
        compile_with: Compile) -> None:
    for stage in ("research", "draft", "review", "revise"):
        compiled = compile_with(stage, web_hosts=(WEB_HOST,))
        joined = ",".join(tools_of(compiled))
        assert not any(name in joined for name in DENIED_TOOLS), (stage, joined)
        has_web = "WebSearch" in joined or "WebFetch" in joined
        assert has_web is (stage == "research"), (stage, joined)
        extra = compiled.config_overrides["claude"]["extra_args"]
        assert extra[:2] == ["--permission-mode", "acceptEdits"]
        assert "bypassPermissions" not in extra and "--dangerously-skip-permissions" not in extra
        assert all(not task["maintain_context"] for task in compiled.playbook["tasks"])


# ── AT-960-7-2 ─────────────────────────────────────────────────────────────────────────
def test_AT_960_7_2_manifest_matches_the_prompt_files_and_yaml_bytes(
        compile_with: Compile, framework: Path) -> None:
    import hashlib

    for stage, roles in (("research", ["research"]), ("draft", ["draft"]),
                         ("revise", ["revise"]),
                         ("review", [f"review-{d.lower()}" for d in DIMENSIONS])):
        compiled = compile_with(stage)
        assert [entry["role"] for entry in compiled.prompt_manifest] == roles
        for entry in compiled.prompt_manifest:
            text = compiled.prompt_files[f".prompts/{entry['role']}.md"]
            assert hashlib.sha256(text.encode("utf-8")).hexdigest() == entry["persona_sha256"]
            yaml_bytes = (framework / entry["agent_yaml"]).read_bytes()
            assert hashlib.sha256(yaml_bytes).hexdigest() == entry["yaml_sha256"]
            assert {"role", "agent_yaml", "yaml_sha256", "persona_sha256"} <= set(entry)
    security = compile_with("review").prompt_manifest[-1]
    assert security["assist_agent_id"] == "compliance-officer"
    assert (framework / security["assist_agent_yaml"]).is_file()


def test_AT_960_7_2_step_prompt_is_a_fixed_reference_and_never_contains_persona_text(
        compile_with: Compile) -> None:
    for stage in ("research", "draft", "review", "revise"):
        compiled = compile_with(stage)
        prompts = [task["prompt"] for task in compiled.playbook["tasks"]]
        for step, prompt in zip(compiled.steps, prompts, strict=True):
            assert f".prompts/{step.role}.md" in prompt
            assert re.search(r"round=\d+", prompt) and f"stage={stage.upper()}" in prompt
            assert len(prompt) <= PROMPT_MAX_CHARS and "\n" not in prompt
        for persona in compiled.personas:
            text = persona.text
            for start in range(0, len(text) - 40, 7):          # 任一長於 40 字的片段都不得出現
                assert text[start:start + 41] not in " ".join(prompts), (persona.role, start)


# ── AT-960-7-3 ─────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("timeout", [1200, 600])
def test_AT_960_7_3_every_step_is_bounded_and_self_contained(
        compile_with: Compile, workspace: Path, timeout: int) -> None:
    for stage in ("research", "draft", "review", "revise"):
        compiled = compile_with(stage, step_timeout_seconds=timeout)
        assert compiled.env == {"CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS": str(timeout * 1000)}
        assert compiled.config_overrides["playbook"]["step_timeout_seconds"] == timeout
        assert compiled.config_overrides["token_guard"] == {"auto_resume": False}
        for task in compiled.playbook["tasks"]:
            assert task["maintain_context"] is False
            assert NO_BACKGROUND_NOTICE in task["prompt"]
            command = task["evaluator_command"]
            assert not (set(command) & (DENY_CHARS | {"\n", "\r", "\x00"})), command
            assert str(workspace.resolve()) in command and "~" not in command
        PlaybookIn.model_validate(compiled.playbook)           # 引擎與 Bridge 的模型都接受


def test_AT_960_7_3_steps_hand_over_only_through_workspace_files(compile_with: Compile) -> None:
    path_or_token = re.compile(r"^([0-9A-Za-z_./-]+|[0-9a-f]{64})$")
    for stage in ("research", "draft", "review", "revise"):
        for step in compile_with(stage).steps:
            assert all(path_or_token.match(v) for v in step.inputs.values()), step.inputs
            others = [other for other in review_outputs(compile_with("review"))
                      if other not in step.outputs]
            assert not set(step.inputs.values()) & set(others)  # 不讀別位審查者的產出


def review_outputs(compiled: CompiledStage) -> list[str]:
    return [out for step in compiled.steps for out in step.outputs]


def test_AT_960_7_3_reviewers_run_as_four_ordered_independent_steps(
        compile_with: Compile) -> None:
    compiled = compile_with("review")
    assert [step.role for step in compiled.steps] == [
        "review-architecture", "review-product", "review-qa", "review-security"]
    assert [step.outputs for step in compiled.steps] == [
        (review_output_rel(2, d),) for d in DIMENSIONS]
    assert compiled.steps[2].inputs["ac_total"] == "4"
    assert "ac_total" not in compiled.steps[0].inputs
    assert [t["step_id"] for t in compiled.playbook["tasks"]] == [s.step_id for s in compiled.steps]


# ── AT-960-11-E-1 ──────────────────────────────────────────────────────────────────────
def test_AT_960_11_E_1_draft_inputs_carry_no_review_material_or_scoring_constants(
        compile_with: Compile) -> None:
    draft = compile_with("draft")
    assert dict(draft.steps[0].inputs) == {
        "issue_scope": "00_research/issue_scope.json",
        "evidence_matrix": "00_research/evidence_matrix.md",
        "evidence_items": "00_research/evidence_items.json"}
    blob = " ".join(draft.steps[0].inputs.values()) + draft.steps[0].prompt
    assert "reviews/" not in blob and "review_card" not in blob and "02_governance" not in blob
    for role in ("draft", "revise"):
        text = compile_with("draft" if role == "draft" else "revise").prompt_files[
            f".prompts/{role}.md"]
        assert scoring_tokens_in(text) == []
        assert "審查協定" not in text and "評分錨點" not in text     # 審查者的協定只屬於審查角色
        for token in ("0.30", "0.25", "0.20"):
            assert token not in text
    revise = compile_with("revise")
    assert set(revise.steps[0].inputs) == {"prd", "defects"}
    assert revise.steps[0].inputs["defects"] == defects_rel(1)
    assert not re.search(r"score|weighted|權重|門檻", " ".join(revise.steps[0].inputs.values()))


def test_AT_960_11_E_1_reviewer_personas_never_carry_weights_or_thresholds(
        compile_with: Compile) -> None:
    compiled = compile_with("review")
    for persona in compiled.personas:                      # 框架 YAML 的人設只准沒有審查常數
        assert scoring_tokens_in(persona.text) == [], persona.role
    for dimension in DIMENSIONS:                           # Bridge 自寫的審查協定連字眼都不帶
        entry = RUBRIC_REGISTRY[dimension]
        protocol = review_protocol(dimension, agent_id=entry["agent_id"],
                                   defect_prefix=entry["defect_prefix"], items=entry["items"])
        for word in ("權重", "門檻", "地板", "通過條件", "weighted", "threshold"):
            assert word not in protocol, (dimension, word)
        assert protocol in compiled.prompt_files[f".prompts/review-{dimension.lower()}.md"]
    for prompt in (task["prompt"] for task in compiled.playbook["tasks"]):
        for word in ("權重", "門檻", "地板", "通過條件", "FSM", "weighted"):
            assert word not in prompt


# ── 編譯層本身的規則（TCS 之外的鎖）─────────────────────────────────────────────────────
def test_compile_is_deterministic_and_hashes_are_sha256_hex(compile_with: Compile) -> None:
    first, second = compile_with("review"), compile_with("review")
    assert first.playbook_sha256 == second.playbook_sha256 == canonical_sha256(first.playbook)
    assert first.config_sha256 == second.config_sha256
    assert re.fullmatch(r"[0-9a-f]{64}", first.playbook_sha256)
    assert first.playbook_sha256 != compile_with("review", round_no=3).playbook_sha256


def test_evaluator_command_uses_isolated_utf8_python_and_gate_cli(compile_with: Compile) -> None:
    for stage in ("research", "draft", "review", "revise"):
        for task in compile_with(stage).playbook["tasks"]:
            command = task["evaluator_command"]
            assert " -I -X utf8 -m app.research.gate_cli " in command
            assert "shell" not in command and "bash" not in command.lower()
    research = compile_with("research", supplement=True, accept_template_sentinel=True)
    text = research.playbook["tasks"][0]["evaluator_command"]
    assert "--previous .inputs/evidence_items.prev.json" in text
    assert "--accept-template-sentinel" in text and "--fetch-index" in text


def test_missing_or_broken_framework_files_fail_loud(tmp_path: Path, workspace: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(CompileError) as missing:
        compile_role(empty, "research")
    assert missing.value.reason == "agent_yaml_missing"
    broken = tmp_path / "broken"
    shutil.copytree(FIXTURE_FRAMEWORK, broken)
    (broken / "agent/specialized/research-analyst-zh.yaml").write_text(
        "persona: [unclosed", encoding="utf-8", newline="\n")
    with pytest.raises(CompileError) as bad:
        compile_role(broken, "research")
    assert bad.value.reason == "agent_yaml_invalid"
    with pytest.raises(CompileError) as unknown:
        compile_role(FIXTURE_FRAMEWORK, "review-everything")
    assert unknown.value.reason == "unknown_role"


def test_a_scoring_constant_in_the_author_yaml_is_a_framework_defect_not_silently_scrubbed(
        tmp_path: Path) -> None:
    framework = tmp_path / "fw"
    shutil.copytree(FIXTURE_FRAMEWORK, framework)
    path = framework / "agent/specialized/spec-engineer-zh.yaml"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("不編造 - ", "不編造 - 門檻 85 分 - ", 1), encoding="utf-8",
                    newline="\n")
    for role in ("draft", "revise"):
        with pytest.raises(CompileError) as leaked:
            compile_role(framework, role)
        assert leaked.value.reason == "persona_scoring_leak" and "85" in str(leaked.value)
    assert scoring_tokens_in("上限 600 字元、v0.20.0、0.60") == []
    assert scoring_tokens_in("0.30 與 85 與 60") == ["0.30", "60", "85"]


def test_the_draft_persona_embeds_the_prd_skeleton_without_the_guide(
        compile_with: Compile) -> None:
    text = compile_with("draft").prompt_files[".prompts/draft.md"]
    assert "<!-- r2p:template-guide" not in text and text.count("<!-- r2p:section=") == 6
    assert "{{" in text                                   # 骨架的佔位仍在（由起草者填寫）
    assert "r2p:section" not in compile_with("revise").prompt_files[".prompts/revise.md"]


def test_unsafe_paths_and_oversized_tools_are_refused_before_any_run(
        tmp_path: Path, framework: Path) -> None:
    with pytest.raises(CompileError) as tilde:
        evaluator_command("python", ["draft", "--workspace", "C:/Users/RUNNER~1/ws"])
    assert tilde.value.reason == "evaluator_forbidden_char"
    hosts = tuple(f"host-{i:04d}.example.org" for i in range(300))
    with pytest.raises(CompileError) as too_long:
        compile_stage(StageRequest(
            stage="research", slug="demo", workspace=tmp_path, framework_root=framework,
            step_timeout_seconds=600, issue_scope_sha256="a" * 64, web_hosts=hosts))
    assert too_long.value.reason == "allowed_tools_too_long"
    for bad in ({"stage": "bogus"}, {"step_timeout_seconds": 0}):
        values = {"stage": "draft", "slug": "demo", "workspace": tmp_path,
                  "framework_root": framework, "step_timeout_seconds": 600, **bad}
        with pytest.raises(CompileError):
            compile_stage(StageRequest(**values))
    assert quote_arg("plain/path.json") == "plain/path.json"
    assert quote_arg("a b").startswith(('"', "'")) and " " in quote_arg("a b")
