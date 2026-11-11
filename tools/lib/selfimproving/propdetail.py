"""SelfImproving 提案詳情：`export --kind proposals --id` 的 `detail`（TCS-SelfImproving-P7 §2.1；
AC-SI-47-1～47-7）。

能力類別 `ro`：只讀 repo 內檔（patch、本文、OBS 帳本）與已載入的事件；**不讀家目錄任何檔**（評估集
內容零洩漏，AC-SI-47-4：本檔不呼叫 `si_dir`、不建構家目錄路徑，評估集只經帳本事件取 n／digest）。
白話一律經 `nextstep`，本檔不內嵌。`ne` 為匯出的量不到清單（本檔只追加）。
"""

from __future__ import annotations

from pathlib import Path

from . import issuemap, nextstep
from . import params as si_params
from . import refs as si_refs
from . import verdict as si_verdict
from .events import PROPOSALS_REL

DETAIL_TEXT_MAX = 262144  # 位元組；模組常數，不進 params.json
TIMELINE_MAX = 500


def _ne(ne: list, pid: str, part: str, code: str) -> None:
    ne.append({"field": f"proposals.{pid}.detail.{part}", "reason": code,
               "text": nextstep.reason(code).text})


def _clip(raw: bytes) -> tuple[str, bool]:
    """依位元組上限截斷並解碼；上限落在字元中間時退到前一個完整字元（不切壞 UTF-8）。"""
    cut = raw[:DETAIL_TEXT_MAX]
    try:
        text = cut.decode("utf-8")
    except UnicodeDecodeError as exc:
        if len(raw) > DETAIL_TEXT_MAX and exc.start >= len(cut) - 3:
            text = cut[:exc.start].decode("utf-8", "replace")
        else:
            text = cut.decode("utf-8", "replace")
    return text, len(raw) > DETAIL_TEXT_MAX


def _file_part(repo: Path, pid: str, rev: int, ext: str, ne: list, code: str) -> dict | None:
    rel = f"{PROPOSALS_REL}/{pid}/r{rev}.{ext}"
    try:
        raw = (repo / rel).read_bytes()
    except OSError:
        _ne(ne, pid, ext if ext == "patch" else "body", code)
        return None
    text, truncated = _clip(raw)
    return {"rel": rel, "bytes": len(raw), "text": text, "truncated": truncated}


def _source_obs(repo: Path, p, ne: list) -> list[dict]:
    try:
        rows = si_refs.obs_rows(repo) if si_refs.obs_ledger_text(repo) is not None else None
    except OSError:
        rows = None
    if rows is None:
        _ne(ne, p.id, "sourceObs", "OBS-LEDGER-UNREADABLE")
        rows = {}
    out = []
    for ident in p.sources:
        row = rows.get(ident)
        if row is None:
            out.append({"id": ident, "missing": True})
        else:
            cells = row.cells
            out.append({"id": ident, "context": cells[2], "symptom": cells[3],
                        "severity": cells[6], "disposition": cells[7]})
    return out


def _min_of(params: dict, p, ne: list):
    ok = nextstep.MIN_KEY in si_params.valid_keys(params)
    if not ok:
        _ne(ne, p.id, nextstep.MIN_KEY.removeprefix("min_"), "HELDOUT-MIN-UNKNOWN")
    return params[nextstep.MIN_KEY] if ok else None


def _frozen_part(events: list[dict], p, minimum) -> dict:
    ev = next((e for e in events if e["seq"] == p.freeze_seq), None) if p.freeze_seq else None
    if ev is None:
        return {"frozen": False, "seq": None, "n": None, "min": minimum, "belowMin": None,
                "frozenBy": None, "digest8": None, "neNote": None}
    n = ev["n"]
    below = n < minimum if minimum is not None else None
    return {"frozen": True, "seq": ev["seq"], "n": n, "min": minimum, "belowMin": below,
            "frozenBy": ev["frozen_by"], "digest8": ev["digest"].split(":", 1)[-1][:8],
            "neNote": nextstep.below_min_note(n, minimum) if below else None}


def _latest(events: list[dict], kind: str, p) -> dict | None:
    return next((e for e in reversed(events) if e["kind"] == kind and e.get("prop") == p.id
                 and e.get("rev") == p.rev), None)


def _sandbox_part(ev: dict | None) -> dict | None:
    if ev is None:
        return None
    code = ev.get("fail_code") or (None if ev["applied"] else "SANDBOX-NOT-APPLIED")
    return {"seq": ev["seq"], "id": ev["id"], "applied": ev["applied"],
            "touchedOk": ev.get("touched_ok"), "rollbackOk": ev.get("rollback_ok"),
            "failCode": code, "failText": nextstep.reason(code).text if code else None}


def _verify_part(ev: dict | None, sandbox: dict | None, freeze: dict | None,
                 minimum) -> dict | None:
    if ev is None:
        return None
    reasons = si_verdict.verdict_of(sandbox, ev, freeze, minimum)[1]  # 重算，不抄事件記錄
    return {"seq": ev["seq"], "id": ev["id"], "verdict": ev["verdict"],
            "baselineRed": ev.get("baseline_red"), "patchedGreen": ev.get("patched_green"),
            "mutatedRed": ev.get("mutated_red"), "probesN": ev["probes_n"],
            "carrierProof": ev.get("carrier_proof"),
            "reasons": [{"code": c, "text": nextstep.reason(c).text} for c in reasons]}


def _timeline(events: list[dict], p, ne: list) -> list[dict]:
    mine = sorted((e for e in events if e.get("prop") == p.id or e.get("id") == p.id),
                  key=lambda e: e["seq"])
    if len(mine) > TIMELINE_MAX:
        mine = mine[-TIMELINE_MAX:]
        _ne(ne, p.id, "timeline", "TIMELINE-TRUNCATED")
    out = []
    for e in mine:
        kind = e["kind"]
        verb = issuemap.dkind_label(e.get("dkind")) or str(e.get("dkind"))
        action = (issuemap.DEC_PREFIX + verb if kind == "dec"
                  else issuemap.event_label(kind) or kind)
        out.append({"seq": e["seq"], "t": e["t"], "by": e["by"], "kind": kind, "action": action})
    return out


def build(repo: Path, events: list[dict], f, p, params: dict, ne: list) -> dict:
    """`detail` 八欄（鍵序固定）；`events` 為已過 `sound` 的事件列、`f` 為其折疊。"""
    minimum = _min_of(params, p, ne)
    freeze = next((e for e in events if e["seq"] == p.freeze_seq), None) if p.freeze_seq else None
    sandbox = _latest(events, "app.sandbox", p)
    return dict(
        patch=_file_part(repo, p.id, p.rev, "patch", ne, "PATCH-UNREADABLE"),
        body=_file_part(repo, p.id, p.rev, "md", ne, "BODY-UNREADABLE"),
        sourceObs=_source_obs(repo, p, ne),
        heldout=_frozen_part(events, p, minimum),
        sandbox=_sandbox_part(sandbox),
        verify=_verify_part(_latest(events, "app.verify", p), sandbox, freeze, minimum),
        next=nextstep.of(f, p, {nextstep.MIN_KEY: minimum}, events),
        timeline=_timeline(events, p, ne))
