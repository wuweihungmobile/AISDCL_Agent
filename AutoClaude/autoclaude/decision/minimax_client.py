"""
Minimax API 客戶端。
- 僅使用 httpx（同步），避免引入 asyncio 複雜性。
- API 異常時拋出 MinimaxError，由上層降級處理。
- 提供 Playbook 步驟失敗修正決策：decide_correction()
- 內建指數退避重試（最多 3 次），容忍瞬時 API 故障。
- Gap-008-D：Hallucination Guard，驗證 correction_prompt 品質。
"""
from __future__ import annotations
import json
import logging
import re
import time
from typing import Optional

import httpx

from ..models.decision import CorrectionDecision, GoalAchievementDecision, EvolutionDecision
from .prompt_builder import (
    build_correction_system_prompt,
    build_correction_message,
    GOAL_VALIDATION_SYSTEM_PROMPT,
    EVOLUTION_SYSTEM_PROMPT,
    build_goal_validation_message,
    build_evolution_message,
)

logger = logging.getLogger("autoclaude.decision")

_MAX_API_RETRIES = 3

# Gap-008-D：Hallucination Guard 常數
_CORRECTION_MIN_CHARS = 50
_CORRECTION_SIMILARITY_THRESHOLD = 0.90
_SPECIFIC_REFERENCE_RE = re.compile(
    r'(?:line \d+|\.py|def \w+|assert\s|SyntaxError|ImportError|TypeError|'
    r'assert\s+\w+\s*==|return\s+\w+)',
    re.IGNORECASE,
)


def _rough_similarity(a: str, b: str) -> float:
    """快速估算兩段文字相似度（基於 Jaccard 詞彙集合）。"""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    union = len(words_a | words_b)
    return len(words_a & words_b) / union if union > 0 else 0.0


def _validate_correction_quality(
    correction_prompt: str,
    previous_prompts: list[str],
) -> tuple[bool, str]:
    """
    Gap-008-D：驗證 Minimax 生成的 correction_prompt 品質。
    返回 (is_valid, reason)。

    品質標準：
    1. 長度合理（>= 50 字元）
    2. 與上次不高度重複（Jaccard 相似度 < 90%）
    3. 包含具體錯誤引用（檔案名、行號、函式名、錯誤類型其中一個）
    """
    if len(correction_prompt) < _CORRECTION_MIN_CHARS:
        return False, f"correction_prompt 過短（{len(correction_prompt)} 字元），可能是幻覺"
    if previous_prompts:
        sim = _rough_similarity(correction_prompt, previous_prompts[-1])
        if sim >= _CORRECTION_SIMILARITY_THRESHOLD:
            return False, f"correction_prompt 與上次高度相似（{sim:.0%}），可能是幻覺重複"
    if not _SPECIFIC_REFERENCE_RE.search(correction_prompt):
        return False, "correction_prompt 缺乏具體錯誤引用，可能是通用幻覺建議"
    return True, "ok"
_BASE_RETRY_DELAY_S = 2.0
_CORRECTION_PROMPT_MAX_CHARS = 1200  # Gap-006-E：從 600 提升至 1200


def _truncate_correction_prompt(prompt: str) -> str:
    """在換行邊界智慧截斷，優於硬切（Gap-006-E）。"""
    if len(prompt) <= _CORRECTION_PROMPT_MAX_CHARS:
        return prompt
    truncated = prompt[:_CORRECTION_PROMPT_MAX_CHARS]
    last_newline = truncated.rfind('\n')
    if last_newline > _CORRECTION_PROMPT_MAX_CHARS * 0.7:
        truncated = truncated[:last_newline]
    return truncated + "\n（指令已在項目邊界截斷，請優先完成上方列出的修正）"


class MinimaxError(Exception):
    pass


class MinimaxClient:
    def __init__(self, api_key: str, base_url: str, model: str, timeout: int = 30):
        if not api_key:
            raise MinimaxError(
                "Minimax API key 未設定，請在 config.yaml 或環境變數 MINIMAX_API_KEY 中設定"
            )
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._timeout = timeout

    # ──────────────────────────────────────────────
    # Playbook 步驟失敗修正
    # ──────────────────────────────────────────────
    def decide_correction(
        self,
        step_id: str,
        task_name: str,
        task_prompt: str,
        expected_regex: Optional[str],
        failure_reason: str,
        eval_output: str,
        retry_count: int,
        history_summary: str = "",
        convergence_trend: str = "",
        convergence_reasoning: str = "",
        strategy_hint: str = "",
        error_class: str = "unknown",
        last_correction_prompt: str = "",  # Gap-008-D：前次修正 prompt，供 Hallucination Guard 去重比對
        task_goal_summary: Optional[str] = None,  # Gap-010-B：任務目標摘要（高重試時取代完整 prompt）
        global_goal: Optional[str] = None,         # Gap-011-A：自治系統總目標
        allow_step_mutation: bool = False,          # Gap-011-B：是否允許 Minimax 提議步驟變異
        mutation_history: Optional[list[str]] = None,  # Gap-013-D：本步驟已執行的突變歷史
        mutation_pressure: int = 0,                 # Gap-032：突變壓力等級 0-3
    ) -> CorrectionDecision:
        mutation_history = mutation_history or []
        system_prompt = build_correction_system_prompt(allow_step_mutation)  # Gap-011-B
        user_msg = build_correction_message(
            step_id=step_id,
            task_name=task_name,
            task_prompt=task_prompt,
            expected_regex=expected_regex,
            failure_reason=failure_reason,
            eval_output=eval_output,
            retry_count=retry_count,
            history_summary=history_summary,
            convergence_trend=convergence_trend,
            convergence_reasoning=convergence_reasoning,
            strategy_hint=strategy_hint,
            error_class=error_class,
            task_goal_summary=task_goal_summary,  # Gap-010-B
            global_goal=global_goal,               # Gap-011-A
            mutation_history=mutation_history,     # Gap-013-D
            mutation_pressure=mutation_pressure,   # Gap-032
        )
        raw = self._call_with_retry(system_prompt, user_msg)
        try:
            decision = CorrectionDecision.model_validate(raw)
        except Exception as exc:
            raise MinimaxError(f"CorrectionDecision 解析失敗: {exc}") from exc
        # Gap-006-E：智慧截斷 correction_prompt（上限 1200 字，在換行邊界截斷）
        if len(decision.correction_prompt) > _CORRECTION_PROMPT_MAX_CHARS:
            logger.warning(
                "Minimax correction_prompt 超過 %d 字 (%d 字)，智慧截斷",
                _CORRECTION_PROMPT_MAX_CHARS, len(decision.correction_prompt),
            )
            decision = CorrectionDecision(
                correction_prompt=_truncate_correction_prompt(decision.correction_prompt),
                reasoning=decision.reasoning,
                task_goal_summary=decision.task_goal_summary,
                step_mutation=decision.step_mutation,  # Gap-011-B：截斷時保留 step_mutation
            )
        # Gap-008-D：Hallucination Guard — 驗證品質，不通過時記錄警告（不阻斷，由 ConvergenceMonitor 處理）
        previous_prompts = [last_correction_prompt] if last_correction_prompt else []
        is_valid, quality_reason = _validate_correction_quality(
            decision.correction_prompt, previous_prompts
        )
        if not is_valid:
            logger.warning("=== Gap-008-D | Minimax 品質驗證警告: %s ===", quality_reason)
        return decision

    # ──────────────────────────────────────────────
    # 帶指數退避重試的 HTTP 呼叫
    # ──────────────────────────────────────────────
    def _call_with_retry(self, system_prompt: str, user_message: str) -> dict:
        """最多重試 _MAX_API_RETRIES 次，每次失敗後指數退避等待。"""
        last_exc: Exception = MinimaxError("未知錯誤")
        for attempt_n in range(_MAX_API_RETRIES):
            try:
                return self._call(system_prompt, user_message)
            except MinimaxError as exc:
                last_exc = exc
                if attempt_n < _MAX_API_RETRIES - 1:
                    wait = _BASE_RETRY_DELAY_S * (2 ** attempt_n)
                    logger.warning(
                        "Minimax API 暫時失敗（attempt %d/%d），%.0fs 後重試: %s",
                        attempt_n + 1, _MAX_API_RETRIES, wait, exc,
                    )
                    time.sleep(wait)
        raise last_exc

    # ──────────────────────────────────────────────
    # 內部 HTTP 呼叫（單次）
    # ──────────────────────────────────────────────
    def _call(self, system_prompt: str, user_message: str) -> dict:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            resp = httpx.post(
                self._base_url,
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )
            resp.raise_for_status()
        except httpx.TimeoutException as exc:
            raise MinimaxError(f"Minimax API 逾時 ({self._timeout}s)") from exc
        except httpx.HTTPStatusError as exc:
            raise MinimaxError(
                f"Minimax API 錯誤 HTTP {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except httpx.RequestError as exc:
            raise MinimaxError(f"Minimax API 連線失敗: {exc}") from exc

        return self._parse_response(resp.json())

    # ──────────────────────────────────────────────
    # Gap-014-A：全局目標達成驗證
    # ──────────────────────────────────────────────
    def validate_goal_achievement(
        self,
        global_goal: str,
        step_summary: str,
        playbook_project: str,
        code_state_snapshot: str = "",  # Gap-023-B：程式碼檔案狀態快照
    ) -> GoalAchievementDecision:
        """
        Gap-014-A / Gap-023-B：諮詢 Minimax 判斷 global_goal 是否真正達成（含程式碼快照）。
        回傳 GoalAchievementDecision（is_achieved=True 表示達成）。
        """
        user_msg = build_goal_validation_message(
            global_goal=global_goal,
            step_summary=step_summary,
            playbook_project=playbook_project,
            code_state_snapshot=code_state_snapshot,
        )
        raw = self._call_with_retry(GOAL_VALIDATION_SYSTEM_PROMPT, user_msg)
        try:
            return GoalAchievementDecision.model_validate(raw)
        except Exception as exc:
            raise MinimaxError(f"GoalAchievementDecision 解析失敗: {exc}") from exc

    # ──────────────────────────────────────────────
    # Gap-016-B：AI 驅動 Playbook 演化提議
    # ──────────────────────────────────────────────
    def propose_evolution(
        self,
        step_id: str,
        step_name: str,
        step_prompt: str,
        failure_summary: str,
        escalation_reasoning: str,
        global_goal: Optional[str] = None,  # Gap-022-B：總目標約束，防演化步驟語意漂移
    ) -> EvolutionDecision:
        """
        Gap-016-B / Gap-022-B：諮詢 Minimax 提議 Playbook 演化策略（含 global_goal 約束）。
        回傳 EvolutionDecision，由 MinimaxEvolver 轉換為 PlaybookEvolutionProposal。
        """
        user_msg = build_evolution_message(
            step_id=step_id,
            step_name=step_name,
            step_prompt=step_prompt,
            failure_summary=failure_summary,
            escalation_reasoning=escalation_reasoning,
            global_goal=global_goal,
        )
        raw = self._call_with_retry(EVOLUTION_SYSTEM_PROMPT, user_msg)
        try:
            return EvolutionDecision.model_validate(raw)
        except Exception as exc:
            raise MinimaxError(f"EvolutionDecision 解析失敗: {exc}") from exc

    def _parse_response(self, data: dict) -> dict:
        try:
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            logger.error("Minimax 回應解析失敗: %s\n原始資料: %s", exc, data)
            raise MinimaxError(f"決策 JSON 解析失敗: {exc}") from exc
