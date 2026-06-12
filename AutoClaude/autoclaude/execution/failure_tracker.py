"""
跨 attempt 追蹤錯誤模式，偵測收斂或發散。
用於 PlaybookRunner CORRECTION 迴圈，防止無效重試並提前識別根因。
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional

# Gap-008-A：失敗數提取 Pattern（與 ConvergenceMonitor 使用相同規則，但各自持有副本避免循環 import）
_FAIL_COUNT_PATTERNS = [
    re.compile(r'(\d+) failed', re.I),
    re.compile(r'failures[=:]\s*(\d+)', re.I),
    re.compile(r'(\d+) tests? failed', re.I),
    re.compile(r'FAIL\s*:\s*(\d+)', re.I),
    re.compile(r'Tests run: \d+, Failures: (\d+)', re.I),
]

# 已知框架/標準庫內部路徑前綴 — 這些不算「實作檔錯誤」
_FRAMEWORK_PATH_RE = re.compile(
    r'(?:_pytest[/\\]|pluggy[/\\]|site-packages[/\\]|lib[/\\]python|importlib)',
    re.IGNORECASE,
)

# Gap-010: 支援 test_*.py 和 *_test.py 兩種測試檔命名格式
_TEST_FILE_RE = re.compile(r'(?:test_\w+|\w+_test)\.py', re.IGNORECASE)

# Gap-007-E：多模式實作檔錯誤偵測（原單模式要求 :行號，無行號格式會繞過）
_IMPL_ERROR_PATTERNS = [
    re.compile(r'\b(?!test_)[a-zA-Z]\w*\.py:\d+'),          # 帶行號（精確）
    re.compile(r'\((?!test_)[a-zA-Z]\w*\.py\)'),             # 括號內的實作檔引用（ImportError 格式）
    re.compile(r"from '(?!test)[^']*\.py'"),                  # from 'module.py' 格式
]


def _has_impl_error(line: str) -> bool:
    """任意一種實作檔錯誤模式匹配，且不屬於框架內部路徑，也不是測試檔。"""
    return (
        any(p.search(line) for p in _IMPL_ERROR_PATTERNS)
        and not _FRAMEWORK_PATH_RE.search(line)
        and not _TEST_FILE_RE.search(line)  # Gap-010: 排除 *_test.py 格式的測試檔
    )


# Gap-007-D：策略組合輪換（確定性策略清單，Minimax 無法忽略）
STRATEGY_TYPES = [
    "PINPOINT",   # 修正最具體的錯誤位置（預設）
    "REWRITE",    # 重寫失敗函式
    "ADD_TYPES",  # 增加型別標注澄清合約
    "SPLIT",      # 拆分複雜函式
    "SIMPLIFY",   # 簡化實作，移除邊界條件
]


@dataclass
class AttemptRecord:
    attempt: int
    failure_reason: str
    eval_output: str
    exit_code: int
    error_signature: str        # 正規化後的錯誤特徵碼（去掉行號等揮發性資訊）
    minimax_reasoning: str
    correction_prompt_sent: str = ""  # Minimax 生成的完整修正指令（可審計性）
    error_class: str = "unknown"      # ErrorClassifier 語義分類（syntax/import/assertion/...）
    mutation_applied: bool = False    # Gap-032：此次 correction 是否已觸發突變（防止 mutation_pressure 過計數）


class FailureTracker:
    """跨 attempt 追蹤錯誤模式，偵測收斂或發散。"""

    def __init__(self, step_id: str):
        self.step_id = step_id
        self.history: list[AttemptRecord] = []
        self._tried_strategies: set[str] = {"PINPOINT"}  # Gap-007-D：第一次預設 PINPOINT

    # ──────────────────────────────────────────────
    # Gap-007-A：序列化 / 反序列化（含 eval_output 供 suspect_test_file_error 恢復）
    # ──────────────────────────────────────────────

    def to_checkpoint_records(self) -> list[dict]:
        """序列化供 checkpoint 使用（含截斷的 eval_output 以支援恢復後的收斂偵測）。"""
        return [
            {
                "attempt": r.attempt,
                "failure_reason": r.failure_reason,
                "eval_output": r.eval_output[:500],  # 截斷節省儲存空間
                "exit_code": r.exit_code,
                "error_signature": r.error_signature,
                "minimax_reasoning": r.minimax_reasoning,
                "correction_prompt_sent": r.correction_prompt_sent,
                "error_class": r.error_class,
            }
            for r in self.history
        ]

    @classmethod
    def from_records(cls, step_id: str, records: list[dict]) -> "FailureTracker":
        """從 checkpoint 記錄重建 FailureTracker（恢復後的收斂偵測繼承歷史）。"""
        tracker = cls(step_id)
        for rec in records:
            tracker.history.append(AttemptRecord(
                attempt=rec.get("attempt", 0),
                failure_reason=rec.get("failure_reason", ""),
                eval_output=rec.get("eval_output", ""),
                exit_code=rec.get("exit_code", 0),
                error_signature=rec.get("error_signature", ""),
                minimax_reasoning=rec.get("minimax_reasoning", ""),
                correction_prompt_sent=rec.get("correction_prompt_sent", ""),
                error_class=rec.get("error_class", "unknown"),
            ))
        return tracker

    # ──────────────────────────────────────────────
    # Gap-007-D：策略組合輪換
    # ──────────────────────────────────────────────

    def next_strategy(
        self,
        kb: "Optional[object]" = None,  # Optional[FailureKnowledgeBase]
        current_error_class: str = "unknown",
    ) -> str:
        """
        回傳下一個未嘗試的策略名稱，並記錄。
        Gap-010-F：若提供 FailureKnowledgeBase，優先按歷史成功率排序選擇。
        所有策略嘗試完後循環重置回 PINPOINT。
        """
        priority_order = STRATEGY_TYPES
        if kb is not None and hasattr(kb, "get_strategy_priority"):
            priority_order = kb.get_strategy_priority(current_error_class)

        for s in priority_order:
            if s not in self._tried_strategies:
                self._tried_strategies.add(s)
                return s
        # 所有策略都嘗試過，循環重置
        self._tried_strategies = {"PINPOINT"}
        return "PINPOINT"

    # ──────────────────────────────────────────────
    # 核心追蹤方法
    # ──────────────────────────────────────────────

    def record(
        self,
        attempt: int,
        failure_reason: str,
        eval_output: str,
        exit_code: int,
        minimax_reasoning: str = "",
        error_class: str = "unknown",
    ) -> None:
        sig = self._normalize_error(eval_output)
        self.history.append(AttemptRecord(
            attempt=attempt,
            failure_reason=failure_reason,
            eval_output=eval_output,
            exit_code=exit_code,
            error_signature=sig,
            minimax_reasoning=minimax_reasoning,
            error_class=error_class,
        ))

    def is_oscillating(self, window: int = 4) -> bool:
        """
        偵測錯誤特徵碼在兩個值之間嚴格交替（ABAB 振盪模式）。
        需至少 window 筆記錄；只有恰好 2 種獨特特徵碼且相鄰記錄不相同才算振盪。
        """
        if len(self.history) < window:
            return False
        recent_sigs = [r.error_signature for r in self.history[-window:]]
        if len(set(recent_sigs)) != 2:
            return False
        return all(recent_sigs[i] != recent_sigs[i + 1] for i in range(len(recent_sigs) - 1))

    def is_cycling(self, window: int = 6, min_unique: int = 2) -> bool:
        """
        偵測多路週期振盪（ABCABC 等 3 路以上循環，補充 is_oscillating 的 2 路 ABAB 盲點）。

        條件：
        1. 至少 window 筆記錄
        2. 有 >= min_unique 種不同特徵碼（排除純卡死）
        3. 沒有任何一個特徵碼佔比超過 window//2（排除局部卡死）
        """
        if len(self.history) < window:
            return False
        recent_sigs = [r.error_signature for r in self.history[-window:]]
        unique_sigs = set(recent_sigs)
        if len(unique_sigs) < min_unique:
            return False
        max_count = max(recent_sigs.count(s) for s in unique_sigs)
        return max_count <= window // 2

    def update_last_correction_prompt(self, correction_prompt: str) -> None:
        """記錄最後一次 Minimax 生成的完整修正指令（供 EscalationDump 可審計性）。"""
        if self.history:
            self.history[-1].correction_prompt_sent = correction_prompt

    def is_stuck(self, consecutive_threshold: int = 2) -> bool:
        """最近 N 次錯誤特徵碼完全相同 → 確定卡死。"""
        if len(self.history) < consecutive_threshold:
            return False
        recent_sigs = [r.error_signature for r in self.history[-consecutive_threshold:]]
        return len(set(recent_sigs)) == 1

    def is_diverging(self) -> bool:
        """exit_code 嚴格遞增（且都非 0）→ Minimax 在惡化問題。"""
        if len(self.history) < 2:
            return False
        exit_codes = [r.exit_code for r in self.history]
        return all(exit_codes[i] < exit_codes[i + 1] for i in range(len(exit_codes) - 1))

    def is_worsening(self, window: int = 3, threshold_ratio: float = 1.5) -> bool:
        """
        Gap-008-A：失敗數嚴格遞增且最後一次比第一次多 threshold_ratio 倍 → Minimax 策略使情況惡化。

        解決 is_diverging() 的根本缺陷：pytest 不管失敗幾個都返回 exit_code=1，
        因此改用「失敗測試數量趨勢」來偵測 Minimax 幻覺修復。

        條件：
        1. 至少 window 筆記錄且每筆都能提取到失敗數
        2. 失敗數為嚴格遞增序列
        3. 最後一筆 >= 第一筆 * threshold_ratio（避免 1→2 雜訊觸發）
        """
        if len(self.history) < window:
            return False
        recent = self.history[-window:]
        counts = []
        for r in recent:
            c = self._extract_fail_count_from_output(r.eval_output)
            if c is None:
                return False
            counts.append(c)
        if any(c == 0 for c in counts):
            return False
        is_strictly_increasing = all(counts[i] < counts[i + 1] for i in range(len(counts) - 1))
        is_significant_increase = counts[-1] >= counts[0] * threshold_ratio
        return is_strictly_increasing and is_significant_increase

    def suspect_assertion_baseline_mismatch(self, min_attempts: int = 3) -> bool:
        """
        Gap-008-C：偵測「測試期望值可能寫錯」的語意模式（AssertionError 基線不匹配）。

        條件（同時滿足）：
        1. 至少 min_attempts 次嘗試
        2. 全部 attempt 都是 assertion error class
        3. 失敗數沒有減少（Minimax 改了但沒讓更多測試通過）
        4. 錯誤特徵碼有 >= 2 種變化（Minimax 嘗試了多種修法都沒用）

        語意：不管怎麼改實作，同一批測試始終 AssertionError → 可能是期望值問題。
        這是「懷疑」而非「確認」，ESCALATION 時必須在 human_hint 中明確說明。
        """
        if len(self.history) < min_attempts:
            return False
        if not all(r.error_class == "assertion" for r in self.history):
            return False
        fail_counts = [self._extract_fail_count_from_output(r.eval_output) for r in self.history]
        valid_counts = [c for c in fail_counts if c is not None]
        if len(valid_counts) >= 2 and valid_counts[-1] < valid_counts[0]:
            return False  # 失敗數有在減少，暫不懷疑
        unique_sigs = set(r.error_signature for r in self.history)
        return len(unique_sigs) >= 2

    @staticmethod
    def _extract_fail_count_from_output(eval_output: str) -> Optional[int]:
        """Gap-008-A：從 eval_output 提取失敗測試數。"""
        for pattern in _FAIL_COUNT_PATTERNS:
            m = pattern.search(eval_output)
            if m:
                return int(m.group(1))
        return None

    def suspect_test_file_error(self) -> bool:
        """
        所有 attempt 的錯誤都指向 test_ 開頭的檔案（SyntaxError/ImportError/NameError），
        且沒有指向真正實作檔的錯誤 → 懷疑測試檔本身有問題，修改實作沒有用。
        需至少 2 次 attempt 才確認。

        雙模式偵測（Gap-006-C 修復）：
        - 模式 1：同行匹配（FAILED tests/test_foo.py - SyntaxError）
        - 模式 2：跨行匹配（ERROR collecting tests/test_foo.py\\n  SyntaxError）

        Gap-007-E 修復：使用 _has_impl_error()（多模式，含無行號格式）
        """
        if len(self.history) < 2:
            return False
        same_line_pattern = re.compile(
            r'(?:test_\w+|\w+_test)\.py.*(?:SyntaxError|ImportError|NameError|ModuleNotFoundError)',
            re.IGNORECASE,
        )
        test_file_pattern = re.compile(r'(?:test_\w+|\w+_test)\.py', re.IGNORECASE)
        error_type_pattern = re.compile(
            r'(?:SyntaxError|ImportError|NameError|ModuleNotFoundError)', re.IGNORECASE,
        )
        for rec in self.history:
            output = rec.eval_output
            has_test_file_error = bool(
                same_line_pattern.search(output) or
                (test_file_pattern.search(output) and error_type_pattern.search(output))
            )
            if not has_test_file_error:
                return False
            # Gap-007-E：逐行掃描，使用多模式 impl_error 偵測（含括號/from 格式）
            for line in output.splitlines():
                if _has_impl_error(line):
                    return False  # 確認是真正的實作檔錯誤
        return True

    def build_history_summary(self, max_unique_records: int = 5) -> str:
        """
        Gap-008-B：給 Minimax 的跨 attempt 歷史摘要（去重 + 限制長度）。

        相同 error_signature 只保留最新一筆 + 累計出現次數，
        壓縮率約 87.5%（10 次相同錯誤 → 1 行），同時保留頻率資訊。
        """
        if not self.history:
            return ""
        sig_count: dict[str, int] = {}
        sig_latest: dict[str, AttemptRecord] = {}
        for rec in self.history:
            sig = rec.error_signature
            sig_count[sig] = sig_count.get(sig, 0) + 1
            sig_latest[sig] = rec
        sorted_sigs = sorted(sig_count.keys(), key=lambda s: sig_count[s], reverse=True)
        top_sigs = sorted_sigs[:max_unique_records]
        lines = [
            f"### 歷次失敗摘要（去重後 {len(top_sigs)}/{len(sig_count)} 種錯誤，"
            f"總嘗試 {len(self.history)} 次）",
        ]
        for sig in top_sigs:
            rec = sig_latest[sig]
            count = sig_count[sig]
            repeat_tag = f"（已出現 {count} 次）" if count > 1 else ""
            corr_preview = ""
            if rec.correction_prompt_sent:
                corr_preview = (
                    f"\n  └─ Minimax 最後修正方向（前 120 字）: "
                    f"{rec.correction_prompt_sent[:120]}"
                )
            lines.append(
                f"- Attempt {rec.attempt}{repeat_tag}: exit={rec.exit_code} "
                f"class={rec.error_class} "
                f"sig={rec.error_signature[:80]}"
                f"{corr_preview}"
            )
        if len(sig_count) > max_unique_records:
            lines.append(f"  ... (另有 {len(sig_count) - max_unique_records} 種錯誤已省略)")
        return "\n".join(lines)

    def to_failure_chain(self) -> list[dict]:
        """轉為可序列化的失敗鏈清單（供 EscalationDump 使用）。"""
        return [
            {
                "attempt": r.attempt,
                "failure_reason": r.failure_reason,
                "error_signature": r.error_signature,
                "minimax_reasoning": r.minimax_reasoning,
                "exit_code": r.exit_code,
                "correction_prompt_sent": r.correction_prompt_sent,
                "error_class": r.error_class,
            }
            for r in self.history
        ]

    @staticmethod
    def _normalize_error(eval_output: str) -> str:
        """移除行號、記憶體地址等揮發性資訊，取得穩定的錯誤特徵碼。"""
        normalized = re.sub(r'line \d+', 'line N', eval_output)
        normalized = re.sub(r'0x[0-9a-fA-F]+', '0xADDR', normalized)
        normalized = re.sub(r'[A-Za-z]:[/\\].*?([/\\]\w+\.py)', r'\1', normalized)  # Windows 路徑
        normalized = re.sub(r'/.*/(\w+\.py)', r'\1', normalized)                    # Unix 路徑
        return normalized[:200].strip()
