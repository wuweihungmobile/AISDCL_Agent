"""解析 AutoClaude 引擎 stdout 的步驟訊號（純函式／純狀態機，不碰行程與檔案）。

實證依據（2026-10-14 對 `python -m autoclaude` 真跑；
log 格式 `YYYY-MM-DD HH:MM:SS [LEVEL] logger: msg`）：
  · 引擎**沒有**「步驟完成」的即時日誌——`step_log` 只在結尾的 KernelResult 一次印出；
    `CheckpointPlugin` 對 POST_STEP 也是空處理，所以引擎不會在每步結束寫 checkpoint。
  · 能用的即時訊號只有三種（全是 INFO 以上，console handler 預設就印）：
      ① `autoclaude.perception: subprocess 模式啟動：[argv…, '-p', '<prompt>']`
         ＝一次 `claude -p` attempt 剛 spawn（Windows 有 wexpect 時改印 `wexpect 模式啟動：`）；
      ② `autoclaude.core.kernel: === STEP_TOKEN_PEAK | step=<id> pct=<n> ===`
         ＝該 attempt 的執行器剛回來（尚未評估；僅 context% > 0 時才印）；
      ③ `=== STATE: ESCALATION | step=<id> | <reason> ===` 與結尾的
         `Playbook 結束 | KernelResult(success=…, completed_steps=…, …)`。
  ⇒ 「步驟 k 完成」只能由「下一個步驟的啟動行出現」或「結尾行 success=True」推得；
    同一步驟的啟動行再次出現＝RETRYING。解析不到任何標記時，Bridge 退化成只發 log 事件。
"""
from __future__ import annotations

import ast
import re
from collections.abc import Sequence
from dataclasses import dataclass

_LOG_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) "
    r"\[(?P<level>DEBUG|INFO|WARNING|ERROR|CRITICAL)\] (?P<logger>[\w.]+): (?P<msg>.*)$")
_START_RE = re.compile(r"(?P<mode>subprocess|wexpect) 模式啟動：")
_TOKEN_PEAK_RE = re.compile(r"=== STEP_TOKEN_PEAK \| step=(?P<step>.+?) pct=(?P<pct>[0-9.]+) ===")
_STATE_RE = re.compile(r"=== STATE: (?P<name>[A-Z_]+) \| (?P<body>.*?) ===\s*$")
_END_RE = re.compile(r"Playbook 結束 \| KernelResult\((?P<body>.*)\)\s*$")
_ESCALATION_STEP_RE = re.compile(r"^step=(?P<step>.+?) \| (?P<reason>.*)$")
_BRACKET_STEP_RE = re.compile(r"^\[(?P<step>[^\]]+)\]")


@dataclass(frozen=True)
class EngineEnd:
    success: bool
    halted: bool
    escalated: bool
    completed_steps: int
    total_steps: int


@dataclass(frozen=True)
class ParsedLine:
    level: str
    kind: str                       # plain | attempt_start | token_peak | state | run_end
    text: str
    prompt: str | None = None       # attempt_start：argv 內 `-p` 之後的 prompt（解析不到為 None）
    step_id: str | None = None      # token_peak／state
    pct: float | None = None        # token_peak
    state: str | None = None        # state：ESCALATION／CORRECTION／TOKEN_HALT／LIMIT_RETRY…
    detail: str = ""                # state：標記內容（升級原因等）
    end: EngineEnd | None = None    # run_end


class LineParser:
    """逐行解析；帶一個 bit 的狀態：traceback 內沒有 `[LEVEL]` 前綴的行沿用 ERROR。"""

    def __init__(self) -> None:
        self._in_traceback = False

    def parse(self, line: str) -> ParsedLine:
        m = _LOG_RE.match(line)
        if not m:
            if line.startswith("Traceback (most recent call last)"):
                self._in_traceback = True
            return ParsedLine("ERROR" if self._in_traceback else "INFO", "plain", line)
        self._in_traceback = False
        level, msg = m.group("level"), m.group("msg")
        start = _START_RE.search(msg)
        if start:
            return ParsedLine(level, "attempt_start", line,
                              prompt=_prompt_from_start(start.group("mode"), msg[start.end():]))
        peak = _TOKEN_PEAK_RE.search(msg)
        if peak:
            return ParsedLine(level, "token_peak", line, step_id=peak.group("step"),
                              pct=float(peak.group("pct")))
        state = _STATE_RE.search(msg)
        if state:
            return _state_line(level, line, state.group("name"), state.group("body"))
        end = _END_RE.search(msg)
        if end:
            return ParsedLine(level, "run_end", line, end=_parse_end(end.group("body")))
        return ParsedLine(level, "plain", line)


def _prompt_from_start(mode: str, tail: str) -> str | None:
    """啟動行的 argv 是 Python list 的 repr：用 literal_eval 還原，比用 regex 抓引號可靠得多。"""
    if mode == "wexpect":
        pos = tail.find("args=")
        if pos < 0:
            return None
        tail = tail[pos + len("args="):]
    try:
        argv = ast.literal_eval(tail.strip())
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        return None             # Windows 的 .cmd shim 啟動行是單一字串、不是 list：交給順序推斷
    if isinstance(argv, list) and "-p" in argv:
        idx = argv.index("-p")
        if idx + 1 < len(argv) and isinstance(argv[idx + 1], str):
            return argv[idx + 1]
    return None


def _state_line(level: str, line: str, name: str, body: str) -> ParsedLine:
    step: str | None = None
    detail = body
    if name == "ESCALATION":
        m = _ESCALATION_STEP_RE.match(body)
        if m:
            step, detail = m.group("step"), m.group("reason")
    elif name in ("CORRECTION", "LIMIT_RETRY", "TOKEN_HALT"):
        m = re.match(r"^step=(?P<step>\S+)", body) or _BRACKET_STEP_RE.match(body)
        if m:
            step = m.group("step")
    return ParsedLine(level, "state", line, step_id=step, state=name, detail=detail)


def _parse_end(body: str) -> EngineEnd:
    def flag(name: str) -> bool:
        return re.search(rf"\b{name}=True\b", body) is not None

    def num(name: str) -> int:
        m = re.search(rf"\b{name}=(\d+)", body)
        return int(m.group(1)) if m else 0

    # halted／escalated 在 dataclass repr 裡緊接在 completed_step_ids 之後：取**最後**一組，
    # 避免步驟名稱或 reason 文字裡剛好出現 `halted=True` 字樣時被誤讀。
    tail = list(re.finditer(r"halted=(True|False), escalated=(True|False)", body))
    halted = tail[-1].group(1) == "True" if tail else flag("halted")
    escalated = tail[-1].group(2) == "True" if tail else flag("escalated")
    return EngineEnd(
        success=re.match(r"success=True\b", body) is not None,
        halted=halted, escalated=escalated,
        completed_steps=num("completed_steps"), total_steps=num("total_steps"))


# ── 步驟狀態機 ────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class StepDef:
    step_id: str
    name: str
    prompt: str
    goal_task_id: str | None = None


@dataclass(frozen=True)
class StartDecision:
    idx: int
    retry: bool                 # 同一步驟的再次啟動（RETRYING）
    completes: int | None       # 這次啟動隱含「哪個步驟剛完成」（None＝沒有）


class StepTracker:
    """依啟動行推斷步驟邊界。決策（classify_start）與提交（retry／complete／begin）分開，
    讓呼叫端能在「步驟 k 完成、步驟 k+1 尚未開始」這個瞬間插手（pause 邊界）。"""

    def __init__(self, steps: Sequence[StepDef], completed_ids: Sequence[str] = ()):
        self.steps = list(steps)
        self.completed: list[str] = list(completed_ids)
        self.current: int | None = None
        self.attempt = 0
        ids = [s.step_id for s in self.steps]
        self._last_done = max((ids.index(i) for i in self.completed if i in ids), default=-1)

    @property
    def next_idx(self) -> int:
        return self._last_done + 1

    def _match(self, prompt: str | None) -> int | None:
        if not prompt:
            return None
        hits = [i for i, s in enumerate(self.steps)
                if s.prompt.strip() and s.prompt.strip() in prompt]
        if not hits:
            return None
        for preferred in (self.current, self.next_idx):
            if preferred in hits:
                return preferred
        return max(hits, key=lambda i: (len(self.steps[i].prompt.strip()), -i))

    def classify_start(self, prompt: str | None) -> StartDecision | None:
        if not self.steps:
            return None
        idx = self._match(prompt)
        if self.current is not None and idx in (None, self.current):
            # 對不上任何步驟（Brain 改寫過 prompt）時，視為目前步驟的重試。
            return StartDecision(self.current, retry=True, completes=None)
        if idx is None:
            idx = min(self.next_idx, len(self.steps) - 1)
        return StartDecision(idx, retry=False, completes=self.current)

    def retry(self) -> int:
        self.attempt += 1
        return self.attempt

    def complete_current(self) -> tuple[int, int] | None:
        if self.current is None:
            return None
        done = (self.current, self.attempt)
        self.completed.append(self.steps[self.current].step_id)
        self._last_done = self.current
        self.current, self.attempt = None, 0
        return done

    def fail_current(self) -> tuple[int, int] | None:
        if self.current is None:
            return None
        failed = (self.current, self.attempt)
        self.current, self.attempt = None, 0
        return failed

    def begin(self, idx: int) -> None:
        self.current, self.attempt = idx, 1
