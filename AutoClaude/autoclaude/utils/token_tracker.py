"""
Token / Context 使用率追蹤器。

兩個職責：
  1. extract_context_pct()  — 從 Claude Code 的單行輸出中萃取 context 百分比
  2. TokenUsageLogger       — 以 JSONL 格式持續記錄每個步驟的 token 狀態
"""
from __future__ import annotations
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("autoclaude.utils.token_tracker")

# 預建置的 pattern 清單（可被 TokenGuardConfig.context_patterns 覆蓋）
# T7（SD_04 §3 / M-4）：與 TokenGuardConfig.context_patterns 預設值同步
_DEFAULT_PATTERNS: list[re.Pattern] = [
    # "95% context used"  /  "token 92% full"
    re.compile(r"(\d+(?:\.\d+)?)\s*%\s*(?:context|token)", re.IGNORECASE),
    # "context usage: 95%"  /  "tokens: 92%"
    re.compile(r"(?:context|token)\w*[\s:]+(\d+(?:\.\d+)?)\s*%", re.IGNORECASE),
    # "190000 / 200000 tokens" → compute percentage
    re.compile(r"(\d+)\s*/\s*(\d+)\s*tokens?", re.IGNORECASE),
    # AutoClaude 專屬標記，可要求 Claude Code System Prompt 輸出：[CONTEXT_USAGE: 92%]
    re.compile(r"\[CONTEXT_USAGE:\s*(\d+(?:\.\d+)?)%\]", re.IGNORECASE),
    # 新增：Claude Code "Context window: N / M tokens"
    re.compile(r"Context window:\s*(\d+)\s*/\s*(\d+)\s*tokens", re.IGNORECASE),
    # 新增：[STATS: usage N%] 簡短標記
    re.compile(r"\[STATS:\s*usage\s*(\d+(?:\.\d+)?)\s*%\]", re.IGNORECASE),
    # 新增：Token usage: N tokens / max M
    re.compile(r"Token usage:\s*(\d+)\s*tokens\s*/\s*max\s*(\d+)", re.IGNORECASE),
]


def build_patterns(pattern_strings: list[str]) -> list[re.Pattern]:
    """將設定檔中的字串 patterns 編譯為 re.Pattern 列表。"""
    compiled: list[re.Pattern] = []
    for ps in pattern_strings:
        try:
            compiled.append(re.compile(ps, re.IGNORECASE))
        except re.error as exc:
            logger.warning("無效的 context pattern %r: %s", ps, exc)
    return compiled


def extract_context_pct(
    line: str,
    patterns: list[re.Pattern] | None = None,
) -> Optional[float]:
    """
    從一行輸出中萃取 context 使用百分比（範圍 0-100）。
    找不到返回 None；若同一行有多個 match，取最高值。
    """
    active = patterns if patterns is not None else _DEFAULT_PATTERNS
    best: Optional[float] = None
    for pat in active:
        for m in pat.finditer(line):
            try:
                groups = m.groups()
                if not groups:                          # 無 capture group，跳過
                    continue
                # Dev-Minor-7：拒絕負號前綴（例如 "-50%"），避免將負數百分比誤判為合法值
                start = m.start(1) if m.groups() else m.start()
                if start > 0 and line[start - 1] == "-":
                    continue
                if len(groups) == 2:                    # N / M tokens 格式
                    used, total = float(groups[0]), float(groups[1])
                    pct = (used / total * 100.0) if total > 0 else None
                else:
                    pct = float(groups[0])
                if pct is not None and 0.0 <= pct <= 100.0 and (best is None or pct > best):
                    best = pct
            except (ValueError, ZeroDivisionError):
                continue
    return best


# ──────────────────────────────────────────────
# Token 使用日誌（JSONL）
# ──────────────────────────────────────────────

class TokenUsageLogger:
    """
    以追加方式寫入 logs/token_usage.jsonl。
    每一行為一筆 JSON 記錄，包含時間戳、步驟、token%、動作、結果。
    """

    def __init__(self, log_dir: str):
        self._log_path = Path(log_dir) / "token_usage.jsonl"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def log_path(self) -> Path:
        return self._log_path

    def record(
        self,
        playbook_project: str,
        step_id: str,
        token_pct: float,
        action: str,       # "continue" | "compact" | "halt_checkpoint"
        step_result: str,  # "success" | "failed" | "in_progress"
    ) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "playbook": playbook_project,
            "step_id": step_id,
            "token_pct": round(token_pct, 1),
            "action": action,
            "step_result": step_result,
        }
        try:
            with self._log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.warning("Token log 寫入失敗: %s", exc)
        logger.debug("Token record: %s", entry)

    def read_all(self) -> list[dict]:
        """讀取所有記錄，回傳 list[dict]（供測試與報表使用）。"""
        if not self._log_path.exists():
            return []
        entries = []
        with self._log_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return entries
