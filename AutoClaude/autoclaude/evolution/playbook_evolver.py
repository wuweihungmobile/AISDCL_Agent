"""
PlaybookEvolver — Level 5 Playbook 自演化引擎（Gap-010-E）。

當 ESCALATION 的根因是「步驟設計本身有問題」時，
自動提議 Playbook 結構演化（注入前置步驟、拆分步驟等），
並將演化後的 Playbook 寫入 evolved_{原檔名}.yaml。

演化觸發條件（任一成立）：
1. suspect_test_file=True 且 PreRunValidator 未在啟動時攔截
2. suspect_assertion_mismatch=True 且 total_attempts >= 4
3. is_stuck=True 且失敗鏈 >= 3 筆（Minimax 策略全部無效）

演化類型：
- INJECT_STEP: 在當前步驟前注入一個新的前置步驟
- SPLIT_STEP: 將當前步驟拆為 2 個更小的步驟
- REVISE_EVALUATOR: 建議修改 evaluator_command
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from ..models.playbook import Playbook, PlaybookTask, EvolutionMetadata
from ..models.escalation import EscalationDump

logger = logging.getLogger("autoclaude.evolution.evolver")


@dataclass
class PlaybookEvolutionProposal:
    """Playbook 演化提議。"""
    evolution_type: str           # "INJECT_STEP" | "SPLIT_STEP" | "REVISE_EVALUATOR"
    inject_before_idx: int        # 插入位置（步驟索引）
    reasoning: str                # 演化原因說明
    new_step: Optional[PlaybookTask] = None        # INJECT_STEP 使用
    split_steps: Optional[list[PlaybookTask]] = None  # SPLIT_STEP 使用
    revised_evaluator: Optional[str] = None       # REVISE_EVALUATOR 使用


class PlaybookEvolver:
    """
    Level 5 核心組件：根據 ESCALATION 分析，提議並應用 Playbook 結構演化。
    不依賴 Minimax，基於規則推論演化方案（低誤操作風險）。
    """

    def propose_evolution(
        self,
        playbook: Playbook,
        failed_step_idx: int,
        escalation_dump: EscalationDump,
        escalation_history: Optional[list[EscalationDump]] = None,
    ) -> Optional[PlaybookEvolutionProposal]:
        """
        分析失敗模式，提議 Playbook 演化方案。
        回傳 None 表示無法自動演化（需人工介入）。
        """
        dump = escalation_dump

        # Gap-013-G：注入步驟的 max_retries 從 global_invariants 推算（2~3，不超過全域設定）
        _global_max = playbook.global_invariants.max_retries_per_step
        _inject_max_retries = max(2, min(_global_max, 3))

        # Gap-033：跨步驟 escalation 模式分析（若有 2+ 個歷史 ESCALATION 且同類型錯誤）
        if escalation_history and len(escalation_history) >= 2:
            _error_classes = [
                d.failure_chain[-1].get("error_class", "unknown")
                for d in escalation_history
                if d.failure_chain
            ]
            if _error_classes:
                _common_class = max(set(_error_classes), key=_error_classes.count)
                _class_count = _error_classes.count(_common_class)
                if _class_count >= 2 and _common_class in ("import", "environment"):
                    logger.warning(
                        "Gap-033 | 跨步驟模式：%d 個步驟均因 %s 失敗，建議全域環境前置步驟",
                        _class_count, _common_class,
                    )
                    return PlaybookEvolutionProposal(
                        evolution_type="INJECT_STEP",
                        inject_before_idx=0,  # 插入到最前面
                        reasoning=(
                            f"{_class_count} 個步驟均因 {_common_class} 失敗，"
                            f"注入全域環境設置步驟（Gap-033 跨步驟模式分析）"
                        ),
                        new_step=PlaybookTask(
                            step_id="ENV_INIT_GLOBAL",
                            name="全域環境初始化（跨步驟模式修復）",
                            prompt=(
                                "多個步驟均因環境依賴問題失敗。\n"
                                "請執行：\n"
                                "1. 確認 requirements.txt 存在且完整\n"
                                "2. 執行 pip install -r requirements.txt\n"
                                "3. 確認 python -c 'import fastapi, sqlalchemy' 無錯誤\n"
                                "4. 輸出「環境初始化完成」"
                            ),
                            expected_output_regex="環境初始化完成",
                            evaluator_command="python -c 'import fastapi' && echo 'OK'",
                            max_retries=_inject_max_retries,
                        ),
                    )

        # Case 1: 測試檔本身設計有問題 → 注入「修復測試檔」前置步驟
        if dump.suspect_test_file:
            pre_step_id = f"{dump.step_id}_PRE"
            return PlaybookEvolutionProposal(
                evolution_type="INJECT_STEP",
                inject_before_idx=failed_step_idx,
                reasoning=(
                    f"測試檔本身有語法/Import 錯誤，在步驟 {dump.step_id} 前注入前置修復步驟"
                ),
                new_step=PlaybookTask(
                    step_id=pre_step_id,
                    name=f"修復 {dump.step_id} 的測試檔問題",
                    prompt=(
                        f"步驟 {dump.step_id} 的測試執行時發現測試檔本身有錯誤。\n"
                        f"請先診斷並修復測試檔：\n"
                        f"{dump.human_hint}\n\n"
                        f"修復完成後，確認測試可以被 pytest 收集（執行 pytest --collect-only）。"
                    ),
                    expected_output_regex=r"selected",
                    evaluator_command="pytest --collect-only",
                    max_retries=_inject_max_retries,  # Gap-013-G
                ),
            )

        # Case 2: AssertionError 基線不匹配 → 注入「確認測試期望值」步驟
        if dump.suspect_assertion_mismatch and dump.total_attempts >= 4:
            pre_step_id = f"{dump.step_id}_ASSERT_FIX"
            return PlaybookEvolutionProposal(
                evolution_type="INJECT_STEP",
                inject_before_idx=failed_step_idx,
                reasoning=(
                    f"步驟 {dump.step_id} 的 AssertionError 在 {dump.total_attempts} 次後仍無法收斂，"
                    f"疑似測試期望值本身寫錯，注入前置確認步驟"
                ),
                new_step=PlaybookTask(
                    step_id=pre_step_id,
                    name=f"確認 {dump.step_id} 的測試期望值",
                    prompt=(
                        f"步驟 {dump.step_id} 的測試始終 AssertionError，"
                        f"可能是測試中的 assert 期望值本身有誤。\n\n"
                        f"請執行以下操作：\n"
                        f"1. 閱讀測試檔中的所有 assert 語句\n"
                        f"2. 確認每個期望值是否符合業務邏輯\n"
                        f"3. 若期望值有誤，修正測試檔中的 assert\n"
                        f"4. 執行 pytest --collect-only 確認測試可被收集\n\n"
                        f"最後輸出：已確認（或已修正）哪些 assert 期望值。"
                    ),
                    evaluator_command="pytest --collect-only",
                    max_retries=_inject_max_retries,  # Gap-013-G
                ),
            )

        # Case 3: 步驟卡死且失敗鏈 >= 3 → 建議拆分步驟
        if dump.is_stuck and len(dump.failure_chain) >= 3:
            failed_task = playbook.tasks[failed_step_idx]
            sub1_id = f"{dump.step_id}_A"
            sub2_id = f"{dump.step_id}_B"
            mid = len(failed_task.prompt) // 2
            # Gap-043：修復 rfind or mid 語意 Bug（rfind 回傳 0 時 `0 or mid` 取中點而非換行點）
            _nl_pos = failed_task.prompt.rfind('\n', 0, mid)
            split_pos = _nl_pos if _nl_pos != -1 else mid
            if split_pos < 50:  # 保護：Part A 至少 50 字符
                split_pos = mid
            prompt_a = failed_task.prompt[:split_pos].strip()
            prompt_b = failed_task.prompt[split_pos:].strip()
            # Gap-018-A：為 Part B 加入 context bridge 前置，防止語意割裂
            context_bridge = (
                f"[前置步驟 {sub1_id} 已完成的工作]\n"
                f"前一個子步驟（{sub1_id}）已完成 {failed_task.name} 的第一部分指令。\n"
                f"請確認 {sub1_id} 的輸出結果，然後繼續完成以下剩餘任務（不要重複第一部分的工作）：\n\n"
            )
            # Gap-026-A：為 Part A 推導輕量 evaluator（防假陽性通過）
            part_a_evaluator = self._derive_part_a_evaluator(failed_task.evaluator_command)
            return PlaybookEvolutionProposal(
                evolution_type="SPLIT_STEP",
                inject_before_idx=failed_step_idx,
                reasoning=(
                    f"步驟 {dump.step_id} 卡死且 {len(dump.failure_chain)} 種策略無效，"
                    f"將複雜步驟拆為兩個子步驟"
                ),
                split_steps=[
                    PlaybookTask(
                        step_id=sub1_id,
                        name=f"{failed_task.name}（第一部分）",
                        prompt=prompt_a or failed_task.prompt,
                        max_retries=failed_task.max_retries,
                        evaluator_command=part_a_evaluator,  # Gap-026-A
                    ),
                    PlaybookTask(
                        step_id=sub2_id,
                        name=f"{failed_task.name}（第二部分）",
                        prompt=context_bridge + (prompt_b or failed_task.prompt),
                        expected_output_regex=failed_task.expected_output_regex,
                        evaluator_command=failed_task.evaluator_command,
                        evaluator_timeout_seconds=failed_task.evaluator_timeout_seconds,
                        max_retries=failed_task.max_retries,
                    ),
                ],
            )

        logger.info("PlaybookEvolver: 無法自動演化步驟 %s，需人工介入", dump.step_id)
        return None

    @staticmethod
    def _derive_part_a_evaluator(full_evaluator: Optional[str]) -> Optional[str]:
        """
        Gap-026-A：從完整 evaluator_command 推導 Part A 輕量評估指令。
        策略：
        - pytest 指令 → 改為 --collect-only（僅確認測試可被收集）
        - 其他指令 → 加 || true 確保不因部分缺失而誤報失敗
        - 無 evaluator → 回傳 None
        """
        if not full_evaluator:
            return None
        cmd = full_evaluator.strip()
        if re.search(r'\bpytest\b', cmd):
            base = re.sub(r'\s+-[kxvsq]\S*', '', cmd)
            base = re.sub(r'\s+--tb=\S+', '', base)
            return base.split()[0] + " --collect-only"
        return f"{{ {cmd}; }} || true"

    def apply_evolution(
        self,
        playbook: Playbook,
        proposal: PlaybookEvolutionProposal,
        playbook_path: str,
        mutation_log: Optional[list[str]] = None,  # Gap-024-B：傳入 mutation_log 供序列化
    ) -> str:
        """
        將演化提議應用到 Playbook，寫入 evolved_{原檔名}.yaml。
        回傳新的 Playbook 路徑。
        """
        tasks = list(playbook.tasks)
        idx = proposal.inject_before_idx

        if proposal.evolution_type == "INJECT_STEP" and proposal.new_step:
            tasks.insert(idx, proposal.new_step)
            logger.info(
                "PlaybookEvolver: INJECT_STEP %s 於步驟 %d 前",
                proposal.new_step.step_id, idx,
            )
        elif proposal.evolution_type == "SPLIT_STEP" and proposal.split_steps:
            tasks[idx:idx + 1] = proposal.split_steps
            logger.info(
                "PlaybookEvolver: SPLIT_STEP 步驟 %d 拆為 %d 個子步驟",
                idx, len(proposal.split_steps),
            )
        elif proposal.evolution_type == "REVISE_EVALUATOR" and proposal.revised_evaluator:
            # Gap-013-B：補全 REVISE_EVALUATOR 處理分支（原本靜默落入 else，演化失效）
            # inject_before_idx 重用為「目標步驟索引」
            if 0 <= idx < len(tasks):
                tasks[idx].evaluator_command = proposal.revised_evaluator
                logger.info(
                    "PlaybookEvolver: REVISE_EVALUATOR 步驟 %d evaluator 更新為: %s",
                    idx, proposal.revised_evaluator[:80],
                )
            else:
                logger.warning(
                    "PlaybookEvolver: REVISE_EVALUATOR idx=%d 超出範圍（共 %d 步），略過",
                    idx, len(tasks),
                )
                return playbook_path
        else:
            logger.warning("PlaybookEvolver: 未知演化類型 %s，略過", proposal.evolution_type)
            return playbook_path

        # Gap-024-B：建立 evolution_metadata 供重載後恢復 mutation_log
        _prev_gen = playbook.evolution_metadata.generation if playbook.evolution_metadata else 0
        _prev_log = list(playbook.evolution_metadata.mutation_log) if playbook.evolution_metadata else []
        _new_log = _prev_log + (mutation_log or [])
        _escalated_ids = list(playbook.evolution_metadata.escalated_step_ids) if playbook.evolution_metadata else []

        evolved_playbook = Playbook(
            version=playbook.version,
            project=f"{playbook.project} [EVOLVED]",
            global_goal=playbook.global_goal,   # Gap-011-A: 保留總目標至演化版 Playbook
            workflow_type=playbook.workflow_type,
            workflow_path=playbook.workflow_path,
            global_invariants=playbook.global_invariants,
            context_negotiation=playbook.context_negotiation,
            evolution_metadata=EvolutionMetadata(  # Gap-024-B
                generation=_prev_gen + 1,
                mutation_log=_new_log,
                escalated_step_ids=_escalated_ids,
            ),
            tasks=tasks,
        )

        evolved_path = Path(playbook_path).parent / f"evolved_{Path(playbook_path).name}"
        try:
            with evolved_path.open("w", encoding="utf-8") as f:
                yaml.dump(
                    evolved_playbook.model_dump(exclude_none=True),
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                )
            logger.info("Level 5: 演化版 Playbook 已寫入 %s", evolved_path)
        except Exception as exc:
            logger.error("PlaybookEvolver: 寫入演化 Playbook 失敗: %s", exc)
            return playbook_path

        return str(evolved_path)
