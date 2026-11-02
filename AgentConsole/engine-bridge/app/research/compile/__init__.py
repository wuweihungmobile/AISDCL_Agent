"""stage run 的編譯層（ADR-003 D1）：框架 agent YAML → `.prompts/`、playbook、
`config_overrides`、env。

  · `personas`  agent YAML → persona 檔（`.prompts/<角色>.md`）與 manifest（YAML／persona 雜湊）
  · `prompts`   步驟 prompt（固定參照句＋禁令句）、審查協定文字、`CompileError`
  · `playbooks` 步驟、`--allowedTools`、請求 env、evaluator 指令、playbook／config 雜湊

整個套件是純函式（不寫檔、不起子行程、不連網）；寫 `.prompts/`、建 run 都由 orchestrator 做。
"""
from __future__ import annotations

from .personas import (
    AUTHOR_ROLES,
    REVIEW_ROLES,
    ROLE_SPECS,
    RolePersona,
    compile_role,
    compile_roles,
    review_role,
    scoring_tokens_in,
)
from .playbooks import (
    CompiledStage,
    StageRequest,
    StepSpec,
    allowed_tools,
    compile_stage,
    defects_rel,
    evaluator_command,
    review_output_rel,
)
from .prompts import NO_BACKGROUND_NOTICE, PROMPT_MAX_CHARS, CompileError, step_prompt

__all__ = [
    "AUTHOR_ROLES", "NO_BACKGROUND_NOTICE", "PROMPT_MAX_CHARS", "REVIEW_ROLES", "ROLE_SPECS",
    "CompileError", "CompiledStage", "RolePersona", "StageRequest", "StepSpec", "allowed_tools",
    "compile_role", "compile_roles", "compile_stage", "defects_rel", "evaluator_command",
    "review_output_rel", "review_role", "scoring_tokens_in", "step_prompt"]
