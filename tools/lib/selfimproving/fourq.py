"""SelfImproving `fourq` 動詞：四問答案檔入帳、免審、語料清單（TCS-SelfImproving-P5；PRD
AC-SI-42-1～42-4）。

能力類別 `rw`：判準全在 `fourqparse.py`（ro）；寫入只經 `evwrite`（事件）與 `propfiles.write_new`
（答案檔 `_fourq/<RUN>.md`，`O_EXCL`）。一次入帳恰追加一筆 `fourq.review`；追加失敗時已落地檔移除
（零殘留）。額度帶經 `sched.quota_check`（`QUOTA_READ` 為注入縫）：`free` 用 `fourq_items_max`，其餘
（含量不到）用 `fourq_degrade_items_max`。本檔不連網、不起子行程。
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from . import events as si_events
from . import evwrite, fourqparse, propfiles, sched, unattended
from . import fold as si_fold
from . import writeverbs as wv
from .fourqparse import (  # noqa: F401  # 再匯出：測試與呼叫端以 fourq.<名> 取用
    check_findings,
    fourq_events,
    gate_codes,
    loop_snapshot,
    status_value,
)

QUOTA_READ = None  # 測試注入縫：`read(now)` 回帶 `.band` 的物件（缺省＝真讀額度）
_KEYS = ("event_max_bytes", "row_max_bytes", "fourq_items_max", "fourq_degrade_items_max")
Out = wv.Out
UsageError = wv.UsageError


def _free_band() -> bool:
    v = sched.quota_check(datetime.now().astimezone(), read=QUOTA_READ)
    return not v["skip"] and not v["degrade"]


def _state_codes(events: list[dict], run: str) -> list[tuple[str, str]]:
    f = si_fold.fold(events)
    r = f.runs.get(run)
    if r is None or r.closed_seq is not None:
        return [("RUN-NOT-OPEN", f"{run} 不是已開未關的運轉")]
    out = []
    if not any(x == run for _, _, x, _ in f.research_events):
        out.append(("FOURQ-BEFORE-RESEARCH", f"{run} 尚無研究事件"))
    if run in fourq_events(events):
        out.append(("FOURQ-ALREADY", f"{run} 已有 fourq 事件"))
    return out


def corpus(repo: Path, as_json: bool) -> Out:
    """`fourq --corpus`：唯讀印固定語料清單（審視者任務書與 CLI 重放同一份）。"""
    files = fourqparse.corpus_files(repo)
    if as_json:
        return Out(0, json.dumps({"ok": True, "files": files}, ensure_ascii=False) + "\n")
    return Out(0, "".join(f"{f}\n" for f in files))


def _read_answers(path: str | None) -> bytes:
    try:
        raw = Path(path or "").read_bytes()
        raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise UsageError(f"--answers-file 讀不到或不是 UTF-8（{type(exc).__name__}）") from exc
    return raw


def _render(e: dict, as_json: bool) -> str:
    extra = [("run", e["run"]), ("sha256", e["sha256"]), ("q1", e["q1"]), ("q2", e["q2"]),
             ("q3", e["q3"]), ("q4", e["q4"]), ("gaps", e["gaps"])]
    if as_json:
        return wv.ok_text("fourq.review", e["seq"], None, [*extra, ("loop", e["loop"])], True)
    return wv.ok_text("fourq.review", e["seq"], None, extra, False) + "".join(
        f"  loop {part}\n" for part in e["loop"].split(";"))


def review(repo: Path, ns, as_json: bool) -> Out:
    """`fourq --run <RUN> --answers-file <路徑> --by <標籤> [--dry-run]`。"""
    if not si_events.RUN_RE.match(ns.run or ""):
        raise UsageError("--run 須為 RUN-SI-NNN")
    if not si_events.valid_by(ns.by or ""):
        raise UsageError("--by 須為非空、無空白、≤32 字元的標籤")
    raw = _read_answers(ns.answers_file)
    params = wv.params_for(repo, *_KEYS)
    cap = params["fourq_items_max" if _free_band() else "fourq_degrade_items_max"]
    pre = [("FOURQ-BY-RESERVED", f"--by 不得為 {ns.by}")] if ns.by in ("main", "researcher") else []

    def evaluate(events: list[dict]):
        probs, items, hits = fourqparse.validate(
            raw, repo, run=ns.run, events=events, items_max=cap, row_max=params["row_max_bytes"])
        return pre + _state_codes(events, ns.run) + probs, items, hits

    if ns.dry_run:
        codes, _, _ = evaluate(si_events.load_sound_events(repo / si_events.LEDGER_REL) or [])
        return wv.reject(repo, "fourq", codes, as_json) if codes else Out(0, "dry-run ok\n")
    data = raw.decode("utf-8").replace("\r\n", "\n").encode("utf-8")

    def build(state):
        codes, items, hits = evaluate(state.events)
        if codes:
            raise evwrite.Reject(codes)
        rel = si_events.fourq_path(ns.run)
        try:
            created = propfiles.write_new(repo, rel, data)
        except FileExistsError as exc:
            raise evwrite.Reject([("FOURQ-FILE-EXISTS", f"{rel} 已存在，不得覆寫")]) from exc
        state.cleanups.append(lambda: propfiles.remove(created))
        c = fourqparse.counts(items)
        snap = fourqparse.loop_text(loop_snapshot(repo, params, state.events))
        return {"kind": "fourq.review", "by": ns.by, "run": ns.run, "path": rel,
                "sha256": fourqparse.sha_lf(raw), "q1": c["q1"], "q2": c["q2"], "q3": c["q3"],
                "q4": c["q4"], "gaps": c["gaps"], "qhits": ",".join(map(str, hits)),
                "loop": snap}
    return wv.append(repo, "fourq", build, params, as_json, lambda e: _render(e, as_json))


def skip(repo: Path, ns, as_json: bool) -> Out:
    """`fourq --skip --run <RUN> --reason {quota-band|helmsman} --note … [--band｜--sid --line]`"""
    if not si_events.RUN_RE.match(ns.run or ""):
        raise UsageError("--run 須為 RUN-SI-NNN")
    note = ns.note or ""
    if not (1 <= len(note) <= 120 and "\n" not in note and "\r" not in note):
        raise UsageError("--note 須為 1～120 字元、無換行的一行")
    extra = {"quota-band": {"band"}, "helmsman": {"sid", "line"}}.get(ns.reason)
    given = {k for k in ("band", "sid", "line") if getattr(ns, k) is not None}
    if extra is None or given != extra:
        raise UsageError("--reason 須為 quota-band（附 --band）或 helmsman（附 --sid 與 --line）")
    if ns.band is not None and ns.band.strip().lower() in ("", "free"):
        raise UsageError("--band 不得為 free")
    if ns.sid is not None and not si_events.valid_uuid(ns.sid):
        raise UsageError("--sid 須為 UUID")
    if ns.line is not None and ns.line < 1:
        raise UsageError("--line 須為整數 ≥1")
    params = wv.params_for(repo, "event_max_bytes")
    if unattended.is_set(os.environ):
        return wv.reject(repo, "fourq", [("FOURQ-SKIP-REFUSED", "無人值守下四問不得免審")], as_json)
    free = ns.reason == "quota-band" and _free_band()

    def build(state):
        codes = _state_codes(state.events, ns.run)
        if free:
            codes.append(("FOURQ-SKIP-BAND-FREE", "額度帶為 free，互動運轉也須做四問"))
        if codes:
            raise evwrite.Reject(codes)
        ev = {"kind": "fourq.skip", "by": "main", "run": ns.run, "reason": ns.reason, "note": note}
        ev.update({k: getattr(ns, k) for k in extra})
        return ev
    return wv.append(repo, "fourq", build, params, as_json, lambda e: wv.ok_text(
        "fourq.skip", e["seq"], None, [("run", ns.run), ("reason", ns.reason)], as_json))
