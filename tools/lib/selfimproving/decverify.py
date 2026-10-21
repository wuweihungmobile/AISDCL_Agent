"""SelfImproving DEC 引言驗證（TCS-SelfImproving-P2 R79）。

`decide` 寫入前、`check` 的 `events.dec_quote`、`promote` 對 `approve` 與 `promote` 兩筆 DEC 的回查
共用的唯一函式 `verify_dec`；依 `carrier` 分派（缺＝`transcript`）。只讀、判準 fail-closed。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from . import card as si_card
from . import decgrammar
from . import fold as si_fold
from . import paths as si_paths
from . import props as si_props
from . import transcript as si_transcript
from .git import Git

CORE_END = "--- 以下不計入核心區 ---"
_VERB_OF = {"approve": "核准", "reject": "否決", "decline-promote": "否決", "return": "退回",
            "promote": "晉升", "ack-handoff": "轉交", "rollback": "回滾", "unblock": "解除",
            "resume": "恢復"}


@dataclass
class Verdict:
    status: str  # "ok"｜"fail"｜"ne"
    code: str = ""
    detail: str = ""


@dataclass
class Ctx:
    repo: Path
    events: list  # 通過單事件判準、依帳本序的事件
    git: Git
    params: dict


OK = Verdict("ok")


def card_text_sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def rebuild_card(ctx: Ctx, card_seq: int, prop: str) -> si_card.CardResult:
    """以事件帳本在該 `card` 事件之前的前綴折疊，重建當時的卡面（與 `card.build` 同一函式）。"""
    prefix = [e for e in ctx.events if e["seq"] < card_seq]
    return si_card.build(ctx.repo, ctx.git, prefix, si_fold.fold(prefix), prop, ctx.params)


def core_of(text: str) -> str:
    """卡面核心區（分界線之前的各行，以 LF 連接）。"""
    return "\n".join(_core(text))


def _core(text: str) -> list[str]:
    lines = text.replace("\r\n", "\n").split("\n")
    return lines[:lines.index(CORE_END)] if CORE_END in lines else lines


def delivered(ctx: Ctx, event: dict, enclosing: str) -> Verdict:
    """R79 ③：`card_seq` 所指的 card 事件、其雜湊與卡面核心區在 assistant 文字的逐字出現。"""
    seq = event.get("card_seq")
    card = next((e for e in ctx.events if e["seq"] == seq and e["kind"] == "card"), None)
    if card is None or card.get("prop") != event.get("prop"):
        return Verdict("fail", "CARD-NOT-DELIVERED", "card_seq 不指向同 PROP 的 card 事件")
    want = event.get("digest")
    if want is None:
        want = card.get("digest")
    if card.get("digest") != want:
        return Verdict("fail", "CARD-NOT-DELIVERED", "dec 的 digest 不等於 card_seq 的 digest")
    try:
        rebuilt = rebuild_card(ctx, card["seq"], card["prop"])
    except si_card.CardError as exc:
        return Verdict("fail", "CARD-SHA-MISMATCH", f"無法重建卡面（{exc.code}）")
    if card_text_sha(rebuilt.text) != card.get("card_sha256"):
        return Verdict("fail", "CARD-SHA-MISMATCH", "card_sha256 與前綴折疊重建的卡面不符")
    core = _core(rebuilt.text)
    if "\n".join(core) in enclosing:
        return OK
    have = set(enclosing.split("\n"))
    miss = next((i for i, ln in enumerate(core, start=1) if ln not in have), None)
    why = f"第 {miss} 行不符" if miss else "行序不符"
    return Verdict("fail", "CARD-NOT-DELIVERED", f"卡面核心區未逐字出現在送達訊息：{why}")


def _quote_in(event: dict, human_text: str) -> Verdict:
    """R79 ②前半：`quote` 須逐字等於該記錄文字中的某一行（先於語法判）。"""
    quote = event.get("quote")
    lines = [ln.strip() for ln in human_text.replace("\r\n", "\n").split("\n")]
    if not isinstance(quote, str) or quote.strip() not in lines:
        return Verdict("fail", "QUOTE-MISMATCH", "quote 不是該記錄文字中的一行")
    return OK


def _check_parsed(event: dict, parsed: decgrammar.Parsed, human_text: str) -> Verdict:
    norm = human_text.replace("\r\n", "\n").strip().split("\n")
    if norm[parsed.line_no - 1].strip() != event["quote"].strip():
        return Verdict("fail", "QUOTE-MISMATCH", "quote 不是該記錄的決定行")
    dk = event.get("dkind")
    if parsed.verb != _VERB_OF.get(dk) or dk not in parsed.kind_candidates:
        return Verdict("fail", "KIND-MISMATCH", f"引言動詞 {parsed.verb} 與 dkind {dk} 不同列")
    if bool(parsed.flags) != ("unverified_ack" in (event.get("flags") or [])):
        return Verdict("fail", "KIND-MISMATCH", "晉升式與 flags 不一致")
    target = event.get("run") if dk == "resume" else event.get("prop")
    if parsed.id != target:
        return Verdict("fail", "ID-MISMATCH", f"引言的 ID {parsed.id} 不等於事件的 {target}")
    if parsed.trailing != (event.get("reason") or ""):
        return Verdict("fail", "QUOTE-MISMATCH", "reason 不等於引言的理由句")
    return OK


def _verify_transcript(event: dict, ctx: Ctx) -> Verdict:
    try:
        records = si_transcript.load(si_transcript.path_for(ctx.repo, str(event.get("sid"))))
        line = event.get("line")
        if not isinstance(line, int) or not 1 <= line <= len(records):
            raise si_transcript.TranscriptError("LINE-OUT-OF-RANGE", f"line={line}")
        human = si_transcript.human_of(records[line - 1])
        got = _quote_in(event, human.text)
        if got.status == "ok":
            got = _check_parsed(event, decgrammar.parse(human.text), human.text)
        if got.status != "ok" or event.get("dkind") == "resume":
            return got
        enclosing = si_transcript.find_enclosing(records, human)
    except si_transcript.TranscriptError as exc:
        return Verdict("ne" if exc.ne else "fail", exc.code, exc.detail)
    except decgrammar.GrammarError as exc:
        return Verdict("fail", exc.code, exc.detail)
    return delivered(ctx, event, enclosing)


def verify_human_ref(repo: Path, sid: str, line: int) -> Verdict:
    """R77 (f)：只驗記錄是兩種真人載體之一且文字非空（`research.skip` 的 `helmsman` 回查用）。"""
    try:
        records = si_transcript.load(si_transcript.path_for(repo, sid))
        if not 1 <= line <= len(records):
            raise si_transcript.TranscriptError("LINE-OUT-OF-RANGE", f"line={line}")
        si_transcript.human_of(records[line - 1])
    except si_transcript.TranscriptError as exc:
        return Verdict("ne" if exc.ne else "fail", exc.code, exc.detail)
    return OK


def recompute_digest(repo: Path, ev: dict) -> str | None:
    """自 `rN.patch`、`rN.md` 重算 PROP 的 digest（R86、R91 的 `DIGEST-MISMATCH`）；讀不到 None。"""
    d = repo / si_card.PROPOSALS_REL / ev["id"]
    try:
        patch = (d / f"r{ev['rev']}.patch").read_bytes()
        body = (d / f"r{ev['rev']}.md").read_bytes().decode("utf-8")
        blocks = si_paths.parse_patch(patch)
    except (OSError, UnicodeDecodeError, si_paths.PatchError):
        return None
    touched = sorted({x for b in blocks for x in b.paths})
    return si_props.compute_digest(
        pid=ev["id"], rev=ev["rev"], cls=ev["cls"], action=ev["action"], target=ev["target"],
        touched=touched, base=ev["base"], preimage=si_props.preimage_of(blocks, touched),
        patch_sha=si_props.sha256_of(patch), body_sha=si_props.body_sha256(body),
        fields=si_props.parse_body(body)[1])


_NE_GATE = ("TRANSCRIPT-UNAVAILABLE", "CONSOLE-AUDIT-MISSING", "CONSOLE-KEY-MISSING")


def dec_gate(ctx: Ctx, event: dict | None) -> tuple[str, str] | None:
    """`sandbox`／`promote` 對 `dec` 的回查閘（fail-closed）：通過回 None，否則回 (碼, 說明)。"""
    if event is None:
        return ("DEC-VERIFY-FAILED", "找不到對應的 dec 事件")
    v = verify_dec(event, ctx)
    if v.status == "ok":
        return None
    if v.status == "ne" and v.code in _NE_GATE:
        return (v.code, v.detail)
    return ("DEC-VERIFY-FAILED", f"{v.code} {v.detail}".strip())


def verify_dec(event: dict, ctx: Ctx) -> Verdict:
    """依 `carrier` 分派的引言驗證；回 `Verdict(status, code, detail)`。"""
    if event.get("carrier") == "console":
        from . import decheck  # 延遲：console 分支才需要稽核檔判準

        return decheck.verify_console(event, ctx)
    return _verify_transcript(event, ctx)
