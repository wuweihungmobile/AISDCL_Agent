"""
ESCALATION 或強制中斷時儲存的完整診斷快照。
提供 to_markdown() 讓人類快速接手診斷。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# DEF-101（Mac/Windows 相容性）：step_id 為 PlaybookTask 上完全自由格式、無驗證
# 的欄位（playbook 作者手寫 YAML 可能寫成 "Step 1: Setup" 這種含冒號的自然字串），
# 若未淨化直接組進檔名，在 Windows 上會因禁用字元 / 保留裝置名導致 open() 拋出
# 未捕捉的 OSError。本檔刻意重用 utils/logger.py 既有的 `_sanitize_log_filename()`
# （RawStreamLogger 已用它解決同類問題），而非另寫一份相似邏輯——避免重蹈
# DEF-101-219／DEF-101-295 同一淨化規則被多處獨立實作、其一漏改即復發的根因。
from ..utils.logger import _sanitize_log_filename, write_text_with_fallback


@dataclass
class EscalationDump:
    """ESCALATION 或強制中斷時儲存的完整診斷快照。"""
    playbook_path: str
    step_id: str
    step_name: str
    total_attempts: int
    failure_chain: list[dict]  # dict keys 見 to_markdown() 消費處
    final_eval_output: str
    is_stuck: bool
    is_diverging: bool
    suspect_test_file: bool
    is_oscillating: bool = False              # 振盪模式（ABAB 交替）診斷旗標
    is_worsening: bool = False                # Gap-008-A：失敗數遞增（越改越壞）
    suspect_assertion_mismatch: bool = False  # Gap-008-C：測試期望值疑似寫錯
    saved_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    human_hint: str = ""
    last_log_path: str = ""
    checkpoint_resume_hint: str = ""
    # AutoSDD_improving_14 A 軌（W-14-2）：meta⁸ 互遞迴拓樸審批儀表板（已過 SDD 端 PY-2
    # 拓樸防偽 + AutoClaude 端 fail-closed 稽核的 Markdown）。空字串＝非 SDD recursion
    # signoff / 無儀表板（預設，零退化）；有值時 to_markdown() 嵌入供舵手於指揮官端審批。
    topology_dashboard: str = ""

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
            f"- 疑似測試期望值寫錯: {yes if self.suspect_assertion_mismatch else no}",
            "",
            "## 建議行動",
            self.human_hint or "請檢查上方失敗鏈，優先確認測試檔是否有獨立錯誤。",
        ]
        if self.topology_dashboard:
            lines += ["", "## 🧭 meta⁸ 互遞迴拓樸審批儀表板（指揮官端可審批）",
                      "> SDD 渲染、已過拓樸防偽 + fail-closed 稽核；🔴=耗 fuel、⛔=強制打斷。",
                      "", self.topology_dashboard]
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
        filename = _sanitize_log_filename(f"escalation_{self.step_id}_{ts}.md")
        path = Path(dump_dir) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        # `_sanitize_log_filename()` 只淨化禁用字元，不截斷長度——超長 step_id（無
        # 驗證的自由格式欄位）仍可能讓檔名超出檔案系統上限；共用 helper 失敗時會
        # fallback 寫入系統暫存目錄，避免 ESCALATION 診斷快照（失敗復盤關鍵材料）
        # 因此完全遺失。
        return write_text_with_fallback(
            path, self.to_markdown(), fallback_prefix="escalation_fallback"
        )
