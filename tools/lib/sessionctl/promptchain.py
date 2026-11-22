"""交接包第 13 欄「鏈上前幾棒」（DES Control_Handover §9.2；REQ-CTL-18；零 token、只讀檔）。

WHY：本 session 接手時得翻上兩棒的 scratchpad（`RESTART_POINT`／任務書）與前棒的 `.prompts.md`——
交接包只列本 sid 的 scratchpad 與全文提示。本檔沿 `.ack` 的接手者 sid 往回走：本 sid 為某包 P₁ 的
接手者（`.ack` 記 `sid=<本 sid>`）⇒ P₁ 的擁有者＝前一棒 Y₁；再找 Y₁ 為接手者的包……至多
`CHAIN_DEPTH` 棒（防環）。**同一 sid 有多個包時**：每步取「`.ack` 內 `sid=` 等於當前 sid 者中 `.ack`
時刻最早的包」（一個 sid 只會被接手一次，其餘多包是它自己當擁有者時產生的），另有 N 個指向者註記；
找不到即止（「鏈止於 <sid>」）。每棒列：棒 sid、封存時刻、`.prompts.md` 路徑（缺則寫「缺」）、最近
`LAST_PROMPTS` 則真人提示前 `PROMPT_EXCERPT_CHARS` 字（取自該棒 sidecar）、該棒 scratchpad ★檔。
「掌舵者是否已答」**不判**（做不到可靠；主控層「待掌舵者決定」仍手寫）。一律不含 `tool_result`。
全欄超過 `COL13_MAX_CHARS` 從最舊棒截斷並寫「已截斷 N 列」。
"""
from __future__ import annotations

import os
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

CHAIN_DEPTH = 5
PROMPT_EXCERPT_CHARS = 200
LAST_PROMPTS = 3
COL13_MAX_CHARS = 8000
STAR_FILES_MAX = 12
NO_CHAIN = "（無前鏈）"
_PROMPT_HEAD = re.compile(r"(?m)^## 提示 \d+（[^\n]*\n")


def _unknown(why: str) -> str:
    return f"量不到：{why}"


def _quote(text: str) -> str:
    return "\n".join(f"> {ln}" for ln in text.splitlines()) or ">"


def _ack_epoch(pkg: Path) -> float:
    """包的 `.ack` 時刻（epoch）：先讀內文 `acked <ISO>`，退回 mtime；都不行 ⇒ `inf`（排最後）。"""
    ack = pkg.with_suffix(".ack")
    try:
        found = re.match(r"acked\s+(\S+)", ack.read_text(encoding="utf-8"))
        if found:
            return datetime.fromisoformat(found.group(1)).timestamp()
    except (OSError, ValueError):
        pass
    try:
        return ack.stat().st_mtime
    except OSError:
        return float("inf")


def walk(sid: str, base: Path, env=None) -> tuple[list[dict], str]:
    """`(棒清單由近到遠, 止於原因)`。每棒 `{owner, package, ack_at, others}`；環／深度上限／找不到
    都在原因字串說清楚，不拋、不無窮迴圈。"""
    from . import handoff, seal  # noqa: PLC0415 — lazy：handoff／seal 鏈會 import handoff_build

    env = os.environ if env is None else env
    rows = [(r["path"], r["sid"], seal.acker_sid(r["path"]))
            for r in handoff.list_handoffs(base, None, env)]
    cur, seen, legs, note = str(sid), {str(sid)}, [], ""
    for _ in range(CHAIN_DEPTH):
        cands = sorted(((_ack_epoch(p), p, owner) for p, owner, acker in rows
                        if acker == cur and owner != cur), key=lambda c: (c[0], str(c[1])))
        if not cands:
            note = f"鏈止於 {cur}：無包記錄其接手"
            break
        at, pkg, owner = cands[0]
        legs.append({"owner": owner, "package": pkg, "ack_at": at, "others": len(cands) - 1})
        if owner in seen:
            note = f"鏈在 {owner} 成環，止於此"
            break
        seen.add(owner)
        cur = owner
    else:
        note = f"已達深度上限 {CHAIN_DEPTH} 棒"
    return legs, note


def prompt_paths(sid: str, base: Path, env=None) -> list[Path]:
    """鏈上各棒的 `.prompts.md` 路徑（由近到遠；只回存在者）。給 `seal.render_prompts` 帶路徑。"""
    from . import seal  # noqa: PLC0415

    try:
        legs, _ = walk(sid, base, env)
        return [p for leg in legs if (p := seal.sidecar_path(leg["package"])).is_file()]
    except Exception:  # noqa: BLE001 — 鏈走不動不得擋封存
        return []


def _recent_prompts(sidecar: Path) -> list[str] | None:
    """該棒 sidecar 最後幾則真人提示的前 `PROMPT_EXCERPT_CHARS` 字；讀不到 ⇒ `None`。"""
    try:
        text = sidecar.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    cap = PROMPT_EXCERPT_CHARS
    bodies = [b.strip() for b in _PROMPT_HEAD.split(text)[1:]]
    return [b if len(b) <= cap else f"{b[:cap]}…（已截斷，原文 {len(b)} 字）"
            for b in bodies[-LAST_PROMPTS:]]


def _sealed_at(pkg: Path) -> str:
    try:
        return pkg.with_suffix(".sealed").read_text(encoding="utf-8").strip() or "（戳空白）"
    except OSError:
        return "未封存"


PadFn = Callable[[str], tuple[list[Path] | None, str]]


def _leg_block(idx: int, leg: dict, pad_fn: PadFn | None) -> str:
    from . import seal  # noqa: PLC0415

    pkg, owner = leg["package"], leg["owner"]
    extra = f"；另有 {leg['others']} 個包同接手者" if leg["others"] else ""
    sidecar = seal.sidecar_path(pkg)
    lines = [f"- 前 {idx} 棒 sid {owner}（封存 {_sealed_at(pkg)}；交棒包 {pkg.name}{extra}）"]
    shown = sidecar if sidecar.is_file() else f"缺（{sidecar}）"
    lines.append(f"  - prompts 全文：{shown}")
    prompts = _recent_prompts(sidecar) if sidecar.is_file() else None
    if prompts is None:
        lines.append("  - 最近真人提示：" + _unknown("prompts sidecar 缺或讀不到"))
    else:
        lines.append(f"  - 最近 {LAST_PROMPTS} 則真人提示：")
        lines += ["    " + ln for t in prompts for ln in _quote(t).splitlines()] or ["    （無）"]
    files, why = pad_fn(owner) if pad_fn is not None else (None, "未提供 scratchpad 查找")
    if files is None:
        lines.append("  - scratchpad ★檔：" + _unknown(why))
    else:
        lines.append("  - scratchpad ★檔：" + ("" if files else "（無）"))
        lines += [f"    - {p}" for p in files[:STAR_FILES_MAX]]
    return "\n".join(lines)


def column13(sid: str, base: Path | None, pad_fn=None, env=None) -> str:
    """第 13 欄全文。`base`（交接包目錄）未知 ⇒ 「量不到」；無前鏈 ⇒ 「（無前鏈）」。不拋。"""
    if base is None:
        return _unknown("未給交接包目錄，無法沿 .ack 往回走")
    try:
        legs, note = walk(sid, Path(base), env)
        if not legs:
            return NO_CHAIN
        blocks = [_leg_block(i, leg, pad_fn) for i, leg in enumerate(legs, 1)]
        dropped = 0
        while len(blocks) > 1 and len("\n".join(blocks)) > COL13_MAX_CHARS:
            blocks, dropped = blocks[:-1], dropped + 1  # 由近到遠排列，最舊在尾
        text = "\n".join(blocks)
        if len(text) > COL13_MAX_CHARS:
            text = text[:COL13_MAX_CHARS] + "…（單棒過長，已硬切）"
        cut = f"（已截斷 {dropped} 列較舊的棒；prompts 路徑見各 sidecar）\n" if dropped else ""
        return f"{text}\n{cut}（{note}）"
    except Exception as exc:  # noqa: BLE001 — 契約：不拋
        return _unknown(f"第 13 欄產生失敗（{type(exc).__name__}: {exc}）")
