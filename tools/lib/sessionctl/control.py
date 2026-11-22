"""控制態判準的單一真相源（葉模組；DES `Control_Handover_Design.md` §3、§4；REQ-CTL-01～07）。

WHY：A4（P1）——封存閘（`seal.stop_verdict`）把「封存後主控又做了工作」判成封存失效，
冷叫醒閘（`converge._finalized_wake`）卻把「已封存、未交棒、主控仍在工作」當成已交棒、
要求 TaskStop 在飛代理與監督 watch：兩個閘對同一事實給矛盾答案，
照做＝在飛代理失去監督（14 天 12 筆 `finalized_wake_block`）。
結構解：「封存目前是否有效」只由本檔 `sealed_effective` 回答，所有消費端讀同一個四值，
不在各閘各補一次例外（DES §4.3 否決「若有派工就放行」那種壓制）。

匯入方向（DES §3.1）：只依標準庫、`transcript_activity`、`roster`（`WATCH_CMD_RE`／`KEEPWARM_CMD_RE`
單一家；`roster` 不 import 本檔或 `seal`，無循環）。`seal` 與 `converge` 單向依賴本檔。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import transcript_activity

from . import roster

# ───────────────────────────────────────────────────────── 監督呼叫文法（D-CT-2）
#: 這些工具本身屬監督／封存流程，不算「工作」。
SUPERVISION_TOOLS = frozenset({"TaskStop", "TaskOutput", "BashOutput", "AskUserQuestion"})
SHELL_TOOLS = frozenset({"PowerShell", "Bash"})
#: `sessionctl.py <動詞>` 的動詞全集；watch／keepwarm 的樣式取 `roster`（不另寫第二份）。
SESSIONCTL_VERBS = ("handoff", "park", "status", "keepwarm", "watch", "runlong", "waitfor",
                    "quotawall", "switch-plan")
_OTHER_VERB_RE = re.compile(
    r"sessionctl\.py[\"']?\s+(?:" + "|".join(v for v in SESSIONCTL_VERBS
                                              if v not in ("watch", "keepwarm")) + r")\b")
# 指令頭必須是 python 直譯器（含 `& 'C:\..\python.exe'`、`uv run python`）：避免
# `git commit -m "… sessionctl.py watch …"` 這種字面夾帶被當成監督。
_PY_HEAD_RE = re.compile(
    r"^[&\s]*(?:uv\s+run\s+)?[\"']?[^\s\"'|]*(?:python|pythonw|py)(?:\.exe)?[\"']?\s", re.I)
_SPLIT_RE = re.compile(r"\|\||&&|;|\r?\n")
_READ_HEADS = frozenset({"get-content", "gc", "cat", "type", "tail", "select-string", "sls"})
_PIPE_TAILS = frozenset({"select-object", "select", "select-string", "sls", "measure-object",
                         "out-string", "tail", "head"})
# 監督輸出檔＝上列指令的重導目標（任意名稱）；跨呼叫查不到重導目標時，退而認路徑字面帶監督動詞。
_OUTFILE_RE = re.compile(r"keepwarm|watch|waitfor|runlong|supervis|sessionctl", re.I)


def _is_sessionctl_segment(seg: str) -> bool:
    if _PY_HEAD_RE.search(seg) is None:
        return False
    return (roster.WATCH_CMD_RE.search(seg) is not None
            or roster.KEEPWARM_CMD_RE.search(seg) is not None
            or _OTHER_VERB_RE.search(seg) is not None)


def _is_output_read_segment(seg: str) -> bool:
    stages = [s.strip() for s in seg.split("|")]
    head = stages[0].split(None, 1)
    if not head or head[0].lower() not in _READ_HEADS or len(head) < 2:
        return False
    if _OUTFILE_RE.search(head[1]) is None:
        return False
    return all(s.split(None, 1)[0].lower() in _PIPE_TAILS for s in stages[1:] if s)


def is_supervision_call(block: object) -> bool:
    """`tool_use` 區塊是不是監督／封存流程呼叫（DES §3.3）。判不出一律回 `False`（算工作）：
    封存失效是保守側，寧可失效後再封存一次，也不讓真工作被當成沒發生。"""
    if not isinstance(block, dict):
        return False
    name = block.get("name")
    if name in SUPERVISION_TOOLS:
        return True
    if name not in SHELL_TOOLS:
        return False
    data = block.get("input")
    command = data.get("command") if isinstance(data, dict) else None
    if not isinstance(command, str) or not command.strip():
        return False
    segments = [s.strip() for s in _SPLIT_RE.split(command) if s.strip()]
    return bool(segments) and all(
        _is_sessionctl_segment(s) or _is_output_read_segment(s) for s in segments)


def is_supervision_shell(task: dict) -> bool:
    """background_tasks 一項是不是依設計掛著的監督／保溫 shell（單一家＝`roster`，此處包一層）。"""
    return roster.is_supervision_shell(task)


def wakeable_tasks(tasks: list[dict]) -> list[dict]:
    """封存有效時冷叫醒閘要列的任務：**非代理、非監督** 的背景任務（`ci_wait` 等；結束會把
    已封存的 session 叫醒）。代理交監督閘看管、watch／keepwarm 依設計掛著，皆不列（DES §4.2）。"""
    return [t for t in tasks
            if t.get("type") != "subagent" and not is_supervision_shell(t)]


# ───────────────────────────────────────────────────────── 封存四值（D-CT-1）
SEAL_NONE, SEAL_UNREADABLE, SEAL_EFFECTIVE, SEAL_INVALIDATED = (
    "none", "unreadable", "effective", "invalidated")


def _readable(transcript: object) -> bool:
    """逐字稿存在且可開啟讀首位元組（`worked_since` 對讀不到回 False，不能分辨「沒工作」與
    「讀不到」，故由本函式先驗，不改 `worked_since`）。"""
    try:
        path = Path(transcript)  # type: ignore[arg-type]
        if not path.is_file():
            return False
        with path.open("rb") as handle:
            handle.read(1)
        return True
    except (OSError, TypeError, ValueError):
        return False


def sealed_effective(stamp: str | None, transcript: object) -> str:
    """封存目前是否有效，四值（DES §3.2；`stamp` 是 `.sealed` 內文，本函式不讀檔）：
    戳不存在 ⇒ `none`（從未封存，與逐字稿無關）；戳壞或逐字稿讀不到 ⇒ `unreadable`；
    戳之後主控沒有「非唯讀、非監督」的 tool_use ⇒ `effective`；有 ⇒ `invalidated`。"""
    if stamp is None:
        return SEAL_NONE
    try:
        datetime.fromisoformat(str(stamp).strip().replace("Z", "+00:00"))
    except ValueError:
        return SEAL_UNREADABLE
    if not _readable(transcript):
        return SEAL_UNREADABLE
    worked = transcript_activity.worked_since(
        Path(transcript), str(stamp).strip(), ignore=is_supervision_call)  # type: ignore[arg-type]
    return SEAL_INVALIDATED if worked else SEAL_EFFECTIVE


# ───────────────────────────────────────────────────────── ControlState（DES §3.4）
_SEALED_DISPLAY = {SEAL_NONE: "none", SEAL_UNREADABLE: "unknown",
                   SEAL_EFFECTIVE: "effective", SEAL_INVALIDATED: "ineffective"}
_SUPERVISION = ("valid", "stuck", "none")
_SOURCES = ("payload", "heartbeat", "lock")
_CARRIERS = ("keepwarm", "watch", "park")
_CUT_KINDS = ("usage_limit", "stopped", "residue")


@dataclass(frozen=True)
class Facts:
    """事實讀取器（W3 `controlfacts`）向各模組取得的原始事實；憑證不取自主控自述。"""

    sid: str
    agents_running: int = 0
    agents_quiet: int = 0
    agents_cut: tuple = ()
    supervision: str = "none"
    supervision_source: str | None = None
    next_wake: str | None = None
    next_wake_carrier: str | None = None
    sealed: str = SEAL_NONE  # `sealed_effective` 的原值
    handed_over: str | None = None
    pending_switch: dict | None = None
    wall: bool = False
    park: dict | None = None
    unacked_pkg: str | None = None


@dataclass(frozen=True)
class ControlState:
    sid: str
    agents_running: int
    agents_quiet: int
    agents_cut: list = field(default_factory=list)
    supervision: str = "none"
    supervision_source: str | None = None
    next_wake: str | None = None
    next_wake_carrier: str | None = None
    sealed: str = "none"
    handed_over: str | None = None
    pending_switch: dict | None = None
    wall: bool = False
    park: dict | None = None
    unacked_pkg: str | None = None


def _count(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0


def classify(facts: Facts) -> ControlState:
    """事實→控制態的純合成：無 I/O、未知值收斂到保守值（`sealed` 未知 ⇒ `unknown`、監督未知 ⇒
    `none`、載具未知 ⇒ `None`），不猜。"""
    supervision = facts.supervision if facts.supervision in _SUPERVISION else "none"
    source = facts.supervision_source if supervision != "none" and \
        facts.supervision_source in _SOURCES else None
    carrier = facts.next_wake_carrier if facts.next_wake and \
        facts.next_wake_carrier in _CARRIERS else None
    cut = [{"id": str(c.get("id")), "kind": c["kind"]} for c in facts.agents_cut
           if isinstance(c, dict) and c.get("kind") in _CUT_KINDS]
    pending = facts.pending_switch if isinstance(facts.pending_switch, dict) and \
        facts.pending_switch.get("reason") and facts.pending_switch.get("since") else None
    return ControlState(
        sid=facts.sid, agents_running=_count(facts.agents_running),
        agents_quiet=_count(facts.agents_quiet), agents_cut=cut, supervision=supervision,
        supervision_source=source, next_wake=facts.next_wake or None, next_wake_carrier=carrier,
        sealed=_SEALED_DISPLAY.get(facts.sealed, "unknown"),
        handed_over=str(facts.handed_over) if facts.handed_over else None,
        pending_switch=pending, wall=bool(facts.wall), park=facts.park or None,
        unacked_pkg=str(facts.unacked_pkg) if facts.unacked_pkg else None)
