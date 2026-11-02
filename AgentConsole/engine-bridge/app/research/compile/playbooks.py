"""stage run 編譯：playbook、`config_overrides`、請求 env 與 evaluator 指令（ADR-003 D1；W-R8）。

一個 stage run＝一份短 playbook（RESEARCH／DRAFT／REVISE 各一步；REVIEW 為四個審查者各一步，依序、
不並行）。每步 `maintain_context:false`（不得用 `--continue` 接上同 cwd 最近的對話）；步驟間只經
工作區檔案交接；步驟 prompt 只寫「先 Read `.prompts/<角色>.md`」；每步的 `evaluator_command` 是
`<python> -I -m app.research.gate_cli …`（確定性驗證，rc 0 才算過；失敗訊息帶進引擎的下一次重試）。

純函式、零寫檔、零子行程（不 import subprocess）：回傳 `CompiledStage`，由 orchestrator 寫
`.prompts/`、建 `RunCreateIn`。工具白名單是 run 級（`claude.extra_args` 的 `--allowedTools`；
ADR-003 D1 的替代案(b) 即因此被否決），所以 stage 才是授權的最小單位：
  RESEARCH            Read、Glob、Grep、`Edit(<工作區>/**)`；Web 層啟用時另加 WebSearch 與每個有效
                      Web 網域的 `WebFetch(domain:<host>)`
  DRAFT／REVISE       Read、Glob、Grep、`Edit(<工作區>/**)`
  REVIEW              Read、Glob、Grep、`Edit(<工作區>/02_governance/reviews/round-<k>/**)`
任何角色皆無 Bash、PowerShell、Task、Agent；起草、修訂、審查從不含 Web 工具。

寫入權限的語法（**V-R1 真機實測**，claude 2.1.316、Windows、headless `-p`、haiku）：路徑限定的規則
只有 `Edit(//<絕對路徑>/…)` 有效——Windows 為 `//c/Users/…`（磁碟機代號小寫、無冒號），`Edit`
規則同時涵蓋 Write 工具；`Write(<路徑>)`（絕對 `C:/…`、`//c/…`、相對、`/` 起頭四種寫法）與
`Edit(<相對路徑>)`、`Edit(/…)` 一律被拒（審查者連自己的輸出檔都寫不出來）；裸 `Write` 則能寫
**工作區以外**的任何位置——所以全部階段一律以 `Edit(//…)` 限定在工作區之內。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ...security import forbidden_chars
from ..gates.schemas import DIMENSIONS
from . import personas
from .personas import RolePersona, review_role
from .prompts import PROMPTS_DIR, CompileError, step_prompt

STAGES: tuple[str, ...] = ("research", "draft", "review", "revise")
EVIDENCE_REL = "00_research/evidence_items.json"
MATRIX_REL = "00_research/evidence_matrix.md"
ISSUE_SCOPE_REL = "00_research/issue_scope.json"
EVIDENCE_INDEX_REL = "00_research/.evidence_index.json"
PREFETCH_INDEX_REL = "00_research/prefetch_index.json"
PREVIOUS_EVIDENCE_REL = ".inputs/evidence_items.prev.json"
PRD_DRAFT_REL = "01_specs/PRD_draft.md"
ADR_DRAFT_REL = "01_specs/adr_draft.md"
WEB_TOOLS = ("WebSearch",)
READ_TOOLS = ("Read", "Glob", "Grep")
#: 命令列（旗標值）的總長預算：Windows `.cmd` shim 的整行上限 7800 字元（AutoClaude
#: `_CMD_LINE_MAX_CHARS`），其中 prompt 另佔（≤ 1000 字元），這裡替工具白名單與其他旗標留的上界。
ARGV_BUDGET_CHARS = 5000
EVALUATOR_TIMEOUT_SECONDS = 60
_SHELL_UNSAFE_WINDOWS = frozenset('%"')


def defects_rel(round_no: int) -> str:
    """修訂輸入的缺陷清單（Bridge 寫；不放在 `02_governance/`，起草者不讀那裡）。"""
    return f".inputs/defects-round-{round_no}.json"


def review_output_rel(round_no: int, dimension: str) -> str:
    return f"02_governance/reviews/round-{round_no}/{dimension.lower()}.json"


def long_path(path: Path) -> str:
    """寫進命令列的路徑：Windows＝`resolve()` 後的長名（8.3 短名含 `~`，屬禁止字元）；
    POSIX＝絕對路徑、不跟隨符號連結（venv 的 `bin/python` 是連結，跟隨會跳出 venv 而失去
    site-packages）。"""
    if sys.platform == "win32":
        return str(path.resolve())
    return os.path.abspath(path)


def quote_arg(value: str) -> str:
    """一個命令列引數的引號形態（evaluator 的 `Popen(shell=True)`：Windows 走 cmd.exe、
    POSIX 走 sh）。"""
    if value and all(ch.isalnum() or ch in "._-/:\\=" for ch in value) and " " not in value:
        return value
    if sys.platform == "win32":
        if any(ch in _SHELL_UNSAFE_WINDOWS for ch in value):
            raise CompileError("evaluator_path_unsafe",
                               f"路徑含 cmd.exe 的特殊字元：{value!r}")
        return f'"{value}"'
    return "'" + value.replace("'", "'\\''") + "'"


def evaluator_command(python: str, args: Sequence[str]) -> str:
    """`<python> -I -X utf8 -m app.research.gate_cli <args…>`。`-I`（隔離模式）不把工作目錄放進
    `sys.path`：引擎在工作區執行 evaluator，沒有它，agent 在工作區放一個 `app/` 套件就能偽造
    evaluator
    的結果。`-I` 同時忽略 `PYTHON*` 環境變數，所以輸出編碼改以 `-X utf8` 明設（Windows 的 stderr
    預設
    是 ANSI 碼頁，違規說明會變亂碼並被帶進下一次重試）。
    整條指令不得含 `DENY_CHARS`（含 `~`）、換行；違反＝`CompileError`（路徑問題只有人能改）。"""
    command = " ".join([quote_arg(python), "-I", "-X", "utf8", "-m", "app.research.gate_cli",
                        *[quote_arg(arg) for arg in args]])
    if bad := forbidden_chars(command):
        raise CompileError("evaluator_forbidden_char", f"evaluator 指令含禁止字元 {bad}")
    return command


def claude_abs_path(path: Path) -> str:
    """Claude Code 權限規則的絕對路徑寫法 `//<路徑>`（V-R1 真機；見模組說明）：Windows 的
    `C:\\Users\\x\\ws` → `//c/Users/x/ws`，POSIX 的 `/home/x/ws` → `//home/x/ws`。"""
    posix = Path(long_path(path)).as_posix()
    drive = re.match(r"^([A-Za-z]):/(.*)$", posix)
    if drive:
        return f"//{drive.group(1).lower()}/{drive.group(2)}"
    return "/" + posix


def allowed_tools(stage: str, workspace: Path, round_no: int,
                  web_hosts: Sequence[str] = ()) -> list[str]:
    """run 級工具白名單（見模組說明）；`web_hosts` 只對 RESEARCH 有意義（有效 Web 清單）。"""
    scope = claude_abs_path(workspace)
    if stage == "research":
        tools = [*READ_TOOLS, f"Edit({scope}/**)"]
        if web_hosts:
            tools += [*WEB_TOOLS, *[f"WebFetch(domain:{host})" for host in web_hosts]]
        return tools
    if stage in ("draft", "revise"):
        return [*READ_TOOLS, f"Edit({scope}/**)"]
    if stage == "review":
        return [*READ_TOOLS, f"Edit({scope}/02_governance/reviews/round-{round_no}/**)"]
    raise CompileError("unknown_stage", f"未知的 stage：{stage}")


@dataclass(frozen=True)
class StageRequest:
    """編譯一個 stage run 所需的全部輸入（orchestrator 在建 run 前蒐齊）。"""

    stage: str
    slug: str
    workspace: Path
    framework_root: Path
    step_timeout_seconds: int
    claude_command: str = "claude"
    web_hosts: tuple[str, ...] = ()
    python_executable: str | None = None
    #: REVIEW＝本次要產生的輪號；REVISE＝剛結束的那輪；其餘 0。
    round_no: int = 0
    scope_rev: int = 1
    issue_scope_sha256: str | None = None
    budget_note: str = ""
    supplement: bool = False
    accept_template_sentinel: bool = False
    prd_rel: str | None = None
    prd_sha256: str | None = None
    ac_total: int | None = None
    max_retries: int = 1


@dataclass(frozen=True)
class StepSpec:
    """一個編譯好的步驟（`inputs` 只供稽核與測試，引擎看到的只有 playbook 的 task）。"""

    step_id: str
    role: str
    name: str
    prompt: str
    inputs: Mapping[str, str]
    outputs: tuple[str, ...]
    evaluator_command: str
    max_retries: int

    def task(self) -> dict[str, Any]:
        return {"step_id": self.step_id, "name": self.name, "prompt": self.prompt,
                "evaluator_command": self.evaluator_command,
                "evaluator_timeout_seconds": EVALUATOR_TIMEOUT_SECONDS,
                "max_retries": self.max_retries, "maintain_context": False}


@dataclass(frozen=True)
class CompiledStage:
    stage: str
    round_no: int
    steps: tuple[StepSpec, ...]
    personas: tuple[RolePersona, ...]
    prompt_files: Mapping[str, str]
    playbook: dict[str, Any]
    config_overrides: dict[str, Any]
    env: dict[str, str]
    tools: tuple[str, ...]
    prompt_manifest: tuple[dict[str, str], ...]
    playbook_sha256: str
    config_sha256: str
    extra: dict[str, Any] = field(default_factory=dict)


def canonical_sha256(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _gate_args(req: StageRequest, check: str, *extra: str) -> list[str]:
    return [check, "--workspace", long_path(req.workspace), *extra]


def _research_steps(req: StageRequest, python: str) -> list[StepSpec]:
    if not req.issue_scope_sha256:
        raise CompileError("missing_input", "RESEARCH 需要 issue_scope_sha256")
    gate = ["--issue-scope-sha256", req.issue_scope_sha256, "--fetch-index", PREFETCH_INDEX_REL]
    inputs = {"issue_scope": ISSUE_SCOPE_REL, "issue_scope_sha256": req.issue_scope_sha256,
              "prefetch_index": PREFETCH_INDEX_REL, "raw_dir": "00_research/raw/"}
    if req.supplement:
        gate += ["--previous", PREVIOUS_EVIDENCE_REL]
        inputs["previous"] = PREVIOUS_EVIDENCE_REL
    if req.accept_template_sentinel:
        gate.append("--accept-template-sentinel")
    outputs = (EVIDENCE_REL,)
    return [StepSpec(
        step_id="step-01-research", role="research", name="RESEARCH：三層檢索與證據抽取",
        prompt=step_prompt("research", stage="research", round_no=0, inputs=inputs,
                           outputs=outputs, note=req.budget_note),
        inputs=inputs, outputs=outputs,
        evaluator_command=evaluator_command(python, _gate_args(req, "evidence", *gate)),
        max_retries=req.max_retries)]


def _draft_steps(req: StageRequest, python: str) -> list[StepSpec]:
    inputs = {"issue_scope": ISSUE_SCOPE_REL, "evidence_matrix": MATRIX_REL,
              "evidence_items": EVIDENCE_REL}
    outputs = (PRD_DRAFT_REL, ADR_DRAFT_REL)
    return [StepSpec(
        step_id="step-01-draft", role="draft", name="DRAFT：起草 SE-PRD 與 adr_draft",
        prompt=step_prompt("draft", stage="draft", round_no=0, inputs=inputs, outputs=outputs),
        inputs=inputs, outputs=outputs,
        evaluator_command=evaluator_command(python, _gate_args(
            req, "draft", "--evidence-index", EVIDENCE_INDEX_REL)),
        max_retries=req.max_retries)]


def _revise_steps(req: StageRequest, python: str) -> list[StepSpec]:
    if req.round_no < 1:
        raise CompileError("missing_input", "REVISE 需要剛結束的輪號（≥ 1）")
    inputs = {"prd": req.prd_rel or PRD_DRAFT_REL, "defects": defects_rel(req.round_no)}
    outputs = (PRD_DRAFT_REL, ADR_DRAFT_REL)
    return [StepSpec(
        step_id="step-01-revise", role="revise", name=f"REVISE-{req.round_no}：依缺陷清單修訂",
        prompt=step_prompt("revise", stage="revise", round_no=req.round_no, inputs=inputs,
                           outputs=outputs),
        inputs=inputs, outputs=outputs,
        evaluator_command=evaluator_command(python, _gate_args(
            req, "revise", "--evidence-index", EVIDENCE_INDEX_REL)),
        max_retries=req.max_retries)]


def _review_steps(req: StageRequest, python: str) -> list[StepSpec]:
    if req.round_no < 1 or not req.prd_rel or not req.prd_sha256:
        raise CompileError("missing_input", "REVIEW 需要輪號（≥ 1）、PRD 路徑與 prd_sha256")
    steps: list[StepSpec] = []
    for index, dimension in enumerate(DIMENSIONS, start=1):
        role = review_role(dimension)
        inputs = {"prd": req.prd_rel, "prd_sha256": req.prd_sha256,
                  "evidence_matrix": MATRIX_REL, "issue_scope": ISSUE_SCOPE_REL}
        if dimension == "QA" and req.ac_total is not None:
            inputs["ac_total"] = str(req.ac_total)
        outputs = (review_output_rel(req.round_no, dimension),)
        gate = ["--dimension", dimension, "--round", str(req.round_no),
                "--prd-sha256", req.prd_sha256, "--prd-path", req.prd_rel,
                "--evidence-index", EVIDENCE_INDEX_REL]
        steps.append(StepSpec(
            step_id=f"step-{index:02d}-{role}", role=role,
            name=f"REVIEW-{req.round_no}：{dimension} 維度審查",
            prompt=step_prompt(role, stage="review", round_no=req.round_no, inputs=inputs,
                               outputs=outputs),
            inputs=inputs, outputs=outputs,
            evaluator_command=evaluator_command(python, _gate_args(
                req, "review-dimension", *gate)),
            max_retries=req.max_retries))
    return steps


_BUILDERS = {"research": _research_steps, "draft": _draft_steps, "revise": _revise_steps,
             "review": _review_steps}


def compile_stage(req: StageRequest) -> CompiledStage:
    """編譯一個 stage run：persona 檔、步驟、playbook、`config_overrides` 與請求 env。

    失敗一律 `CompileError`（框架檔缺失、路徑含禁止字元、參數缺漏）；不寫任何東西。"""
    if req.stage not in _BUILDERS:
        raise CompileError("unknown_stage", f"未知的 stage：{req.stage}")
    if req.step_timeout_seconds < 1:
        raise CompileError("invalid_timeout", "步驟牆鐘須為正整數秒")
    python = long_path(Path(req.python_executable or sys.executable))
    steps = _BUILDERS[req.stage](req, python)
    roles = tuple(dict.fromkeys(step.role for step in steps))
    compiled = personas.compile_roles(req.framework_root, roles)
    prompt_files = {compiled[role].prompt_rel: compiled[role].text for role in roles}
    tools = allowed_tools(req.stage, req.workspace, req.round_no, req.web_hosts)
    extra_args = ["--permission-mode", "acceptEdits", "--allowedTools", ",".join(tools)]
    if sum(len(arg) + 1 for arg in extra_args) > ARGV_BUDGET_CHARS:
        raise CompileError("allowed_tools_too_long",
                           f"工具白名單超過命令列預算 {ARGV_BUDGET_CHARS} 字元（Web 網域過多）")
    # 刻意不帶 `global_goal`：引擎會把它加成步驟 prompt 的多行前綴（「總目標」區塊），而 Windows
    # 的 `.cmd` shim 經 `cmd /s /c` 會在第一個換行就截斷命令列（真機實測；V-R3）——步驟 prompt
    # 必須維持單行。
    playbook = {
        "version": "1.0", "project": f"research-{req.slug}", "workflow_type": "auto",
        "global_invariants": {"max_retries_per_step": req.max_retries, "auto_compact_interval": 0},
        "tasks": [step.task() for step in steps]}
    config = {"claude": {"command": req.claude_command, "extra_args": extra_args},
              "playbook": {"step_timeout_seconds": req.step_timeout_seconds},
              "token_guard": {"auto_resume": False}}
    env = {"CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS": str(req.step_timeout_seconds * 1000)}
    return CompiledStage(
        stage=req.stage, round_no=req.round_no, steps=tuple(steps),
        personas=tuple(compiled[role] for role in roles), prompt_files=prompt_files,
        playbook=playbook, config_overrides=config, env=env, tools=tuple(tools),
        prompt_manifest=tuple(compiled[role].manifest_entry() for role in roles),
        playbook_sha256=canonical_sha256(playbook), config_sha256=canonical_sha256(config))


__all__ = ["PROMPTS_DIR", "CompiledStage", "StageRequest", "StepSpec", "allowed_tools",
           "claude_abs_path", "compile_stage", "defects_rel", "evaluator_command", "long_path",
           "quote_arg", "review_output_rel"]
