"""
ESCALATION 或強制中斷時儲存的完整診斷快照。
提供 to_markdown() 讓人類快速接手診斷。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class EscalationDump:
    """ESCALATION 或強制中斷時儲存的完整診斷快照。"""
    playbook_path: str
    step_id: str
    step_name: str
    total_attempts: int
    failure_chain: list[dict]       # [{attempt, failure_reason, error_signature, minimax_reasoning, exit_code, correction_prompt_sent, error_class}]
    final_eval_output: str
    is_stuck: bool
    is_diverging: bool
    suspect_test_file: bool
    is_oscillating: bool = False              # 振盪模式（ABAB 交替）診斷旗標
    is_worsening: bool = False                # Gap-008-A：失敗數遞增（Minimax 越改越壞）
    suspect_assertion_mismatch: bool = False  # Gap-008-C：疑似測試期望值寫錯（AssertionError 無法收斂）
    saved_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    human_hint: str = ""
    last_log_path: str = ""
    checkpoint_resume_hint: str = ""

    def generate_handover_checklist(self) -> list[str]:
        """
        Gap-010-D：根據 ESCALATION 原因，自動生成可執行的接手行動清單。
        每個項目含可直接在終端執行的 shell 命令。
        """
        actions: list[str] = []
        look_back = min(self.total_attempts, 5)

        actions += [
            "# === AutoClaude 接手行動清單 ===",
            "# 1. 確認 Claude Code 最近的修改",
            f"git log --oneline -{look_back}",
            f"git diff HEAD~{look_back} HEAD",
        ]

        if self.suspect_test_file:
            actions += [
                "",
                "# 2. 測試檔語法驗證（suspect_test_file=True）",
                "python -m py_compile tests/test_*.py",
                "pytest --collect-only  # 確認測試可被收集",
            ]

        if self.is_stuck:
            actions += [
                "",
                "# 3. 卡死診斷（is_stuck=True，相同錯誤反覆出現）",
                f"cat '{self.last_log_path}' | tail -50  # 查看最後執行 log",
                "# 手動執行 evaluator_command 確認根本原因",
            ]

        if self.suspect_assertion_mismatch:
            actions += [
                "",
                "# 4. 測試期望值驗證（suspect_assertion_mismatch=True）",
                r"grep -rn 'assert.*==' tests/ | head -20",
                "# 請人工確認：assert 的期望值是否符合業務邏輯",
            ]

        if self.is_worsening:
            actions += [
                "",
                "# 5. 失敗數遞增診斷（is_worsening=True，修改越多失敗越多）",
                "git stash  # 暫存當前修改，從乾淨狀態診斷",
                "# 或：git checkout HEAD -- . # 危險！還原所有未 commit 的修改",
            ]

        if self.is_oscillating:
            actions += [
                "",
                "# 6. 振盪模式診斷（is_oscillating=True，兩個錯誤交替出現）",
                "# 修改 A 導致錯誤 B，修改 B 導致錯誤 A",
                "# 需要找到根本的設計衝突，而非逐一修補",
            ]

        actions += [
            "",
            "# 7. 手動修正後，恢復執行",
            f"autoclaude {self.playbook_path}  # 從 checkpoint 繼續",
            "# 若步驟已手動完成，可直接繼續下一步",
        ]

        return actions

    def to_markdown(self) -> str:
        lines = [
            "# AutoClaude Escalation Dump",
            f"**步驟**: {self.step_id} — {self.step_name}",
            f"**時間**: {self.saved_at}",
            f"**重試次數**: {self.total_attempts}",
            f"**Playbook**: {self.playbook_path}",
            "",
            "## 失敗鏈",
        ]
        for rec in self.failure_chain:
            corr_prompt = rec.get("correction_prompt_sent", "")
            corr_preview = f"\n  修正指令（前 200 字）: {corr_prompt[:200]}" if corr_prompt else ""
            error_class = rec.get("error_class", "unknown")
            lines.append(
                f"- Attempt {rec['attempt']} (exit={rec.get('exit_code', '?')}, "
                f"error_class={error_class}): "
                f"`{rec['error_signature'][:100]}`"
                f"\n  Minimax 決策: {rec['minimax_reasoning']}"
                f"{corr_preview}"
            )
        yes = "✅ 是"
        no = "❌ 否"
        lines += [
            "",
            "## 最後評估輸出",
            "```",
            self.final_eval_output[:3000],
            "```",
            "",
            "## 自動診斷",
            f"- 錯誤卡死（特徵相同）: {yes if self.is_stuck else no}",
            f"- 錯誤發散（越改越壞，exit_code）: {yes if self.is_diverging else no}",
            f"- 失敗數惡化（越改越多）: {yes if self.is_worsening else no}",
            f"- 振盪錯誤（ABAB 交替）: {yes if self.is_oscillating else no}",
            f"- 疑似測試檔本身有語法/Import 錯誤: {yes if self.suspect_test_file else no}",
            f"- 疑似測試期望值寫錯（AssertionError 多次無法收斂）: {yes if self.suspect_assertion_mismatch else no}",
            "",
            "## 建議行動",
            self.human_hint or "請檢查上方失敗鏈，優先確認測試檔是否有獨立錯誤。",
        ]
        if self.last_log_path:
            lines += ["", "## 最後執行 Log", f"`{self.last_log_path}`"]
        if self.checkpoint_resume_hint:
            lines += ["", "## 繼續執行指令", "```", self.checkpoint_resume_hint, "```"]
        # Gap-010-D：自動生成可執行的接手行動清單
        lines += [
            "",
            "## 接手行動清單（可直接執行）",
            "```bash",
            *self.generate_handover_checklist(),
            "```",
        ]
        return "\n".join(lines)

    def save(self, dump_dir: str) -> Path:
        """將快照儲存為 Markdown 檔案，回傳實際路徑。"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"escalation_{self.step_id}_{ts}.md"
        path = Path(dump_dir) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(self.to_markdown(), encoding="utf-8")
        tmp.replace(path)
        return path
