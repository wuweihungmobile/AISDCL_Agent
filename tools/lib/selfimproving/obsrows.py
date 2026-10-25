"""SelfImproving OBS 列的本文規則、組列與預檢（TCS-SelfImproving-P2 R96 (a)(b)(d)）。

能力類別 `ro`：只讀；`obs-add --dry-run` 只走本檔（行程不載入 `obswrite`、`runner`、`fetch`、
`research`）。組列＝九欄、標記鍵序固定，使位元組可重現；組列後以 `rows.evaluate_rows` 對僅含該列的
合成帳本自驗（零 `fail` finding 才收）。
"""

from __future__ import annotations

import re
from pathlib import Path

from . import consoleaudit
from . import events as si_events
from . import refs as si_refs
from . import rows as si_rows
from .ledger import COLUMNS, ID_RE, max_valid_id, parse_ledger

_REQUIRED_STR = ("context", "symptom", "evidence", "category", "severity", "face")
_NONEMPTY = ("context", "symptom", "evidence")
_EXTRA_OK = ("rel", "reopens", "根因")
_PLACEHOLDER_REF = "00000000-0000-4000-8000-000000000000"
Code = tuple[str, str]


def _invalid(why: str) -> list[Code]:
    return [("AUDIT-BODY-INVALID", why)]


def body_problems(body: dict, known_ids: set[str]) -> list[Code]:
    """R96 (a) 的本文欄位規則（不含組列後自驗）；型別不合＝`AUDIT-BODY-INVALID`。"""
    bad = [k for k in _REQUIRED_STR if not isinstance(body.get(k), str)]
    if bad:
        return _invalid("缺或非字串：" + "、".join(bad))
    extra = body.get("marks_extra")
    if (not isinstance(body.get("external_derived"), bool)
            or ("exposure" in body and not isinstance(body["exposure"], str))
            or (extra is not None and not (isinstance(extra, dict) and all(
                isinstance(v, str) for v in extra.values())))
            or ("corrects" in body and not isinstance(body["corrects"], str))):
        return _invalid("external_derived／exposure／marks_extra／corrects 型別不合")
    texts = [body[k] for k in _REQUIRED_STR] + [body.get("exposure", ""), body.get("corrects", "")]
    texts += list((extra or {}).values())
    out: list[Code] = []
    if any("|" in t for t in texts):
        out.append(("PIPE-IN-FIELD", "字串欄含 |（會破壞九欄表）"))
    if any(not body[k].strip() for k in _NONEMPTY):
        out.append(("FIELD-EMPTY", "context、symptom、evidence 不得為空或只含空白"))
    if body["category"] not in si_rows.CATEGORIES:
        out.append(("ENUM-CATEGORY", "category 不在枚舉"))
    if body["severity"] not in si_rows.SEVERITIES:
        out.append(("ENUM-SEVERITY", "severity 不在 P1～P4"))
    if body["face"] not in si_rows.FACES:
        out.append(("FACE-INVALID", "face 不在 守衛／產品／文件／流程"))
    elif body["face"] == "守衛" and "exposure" not in body:
        out.append(("EXPOSURE-REQUIRED", "face 為 守衛 須有 exposure"))
    elif body["face"] != "守衛" and "exposure" in body:
        out.append(("EXPOSURE-UNEXPECTED", "face 非 守衛 不得有 exposure"))
    keys = list(extra or {})
    if any(k not in _EXTRA_OK for k in keys):
        out.append(("MARKS-EXTRA-KEY", "marks_extra 只准 rel、reopens、根因（src 一律拒）"))
    if body.get("corrects") is not None:
        if "rel" in (extra or {}):
            out.append(("REL-CONFLICT", "有 corrects 時 marks_extra 不得再含 rel"))
        if not ID_RE.match(body["corrects"]) or body["corrects"] not in known_ids:
            out.append(("CORRECTS-NOT-FOUND", "被更正的 OBS ID 不在 OBS 帳本（含封存檔）"))
    return out + consoleaudit.body_guard("obs-add", body)  # R136 (a)


def compose(body: dict, ident: str, ref: str, when_cell: str) -> str:
    """R96 (b)：九欄列；標記鍵序 面、暴露、外部衍生、rel=corrects、marks_extra、來源、回報者、
    carrier、audit_ref（以 `;` 連接）。"""
    marks = [f"面={body['face']}"]
    marks += [f"暴露={body['exposure']}"] if "exposure" in body else []
    marks += ["外部衍生=是"] if body["external_derived"] else []
    marks += [f"rel=corrects:{body['corrects']}"] if body.get("corrects") else []
    extra = body.get("marks_extra") or {}
    marks += [f"{k}={extra[k]}" for k in _EXTRA_OK if k in extra]
    marks += ["來源=人", f"回報者={body['user']}", "carrier=console", f"audit_ref={ref}"]
    cells = [ident, when_cell, body["context"].strip(), body["symptom"].strip(),
             body["evidence"].strip(), body["category"], body["severity"], "open", ";".join(marks)]
    return "| " + " | ".join(cells) + " |"


def self_check(row: str, row_max_bytes: int | None, tz: str | None = None) -> list[Code]:
    """組列後自驗：`evaluate_rows` 對僅含該列的合成帳本，回全部 `fail` finding 的（碼, 說明）。"""
    head = f"<!-- si-ledger: tz={tz} -->\n" if tz else ""
    text = (head + "| " + " | ".join(COLUMNS) + " |\n" + "|" + "---|" * len(COLUMNS) + "\n"
            + row + "\n")
    res = si_rows.evaluate_rows(parse_ledger(text), row_max_bytes, None)
    return [(f.code, f.detail) for fs in res.values() for f in fs if f.level == "fail"]


def next_ident(repo: Path, text: str | None = None) -> str:
    """下一個 OBS ID：主帳本（`text` 給定則用之，鎖內重讀）與封存檔的最大合法號加 1，至少三位。"""
    main = max_valid_id(parse_ledger(text)) if text is not None else 0
    top = max([main] + [int(i.rsplit("-", 1)[1]) for i in si_refs.obs_rows(repo)])
    return f"OBS-SI-{top + 1:03d}"


def ref_used(repo: Path, events: list[dict], ref: str) -> bool:
    """R95：同一 `audit_ref` 已有任一 `dec`、`obs.add`、`obs.close` 事件，或 OBS 列標記 `audit_ref`
    相同——跨 kind 計。"""
    if any(e.get("audit_ref") == ref for e in events
           if e["kind"] in ("dec", "obs.add", "obs.close")):
        return True
    return any(si_rows.row_marks(r).get("audit_ref", ("", 0))[0] == ref
               for r in si_refs.obs_rows(repo).values())


def preview(repo: Path, body, row_max_bytes: int | None) -> dict:
    """`obs-add --dry-run`：預覽列與自驗結果（與 Bridge `POST /si/observations:validate` 同形）。"""
    findings: list[Code] = []
    row = ""
    if not isinstance(body, dict):
        findings = _invalid("body 不是 JSON 物件")
    else:
        findings = body_problems({**body, "user": body.get("user", "dry-run")},
                                 set(si_refs.obs_rows(repo)))
        if not findings:
            ref = body.get("audit_ref")
            ref = ref if isinstance(ref, str) and si_events.valid_uuid(ref) else _PLACEHOLDER_REF
            when = body.get("time")
            cell = consoleaudit.row_time(when) if isinstance(when, str) and re.fullmatch(
                r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d", when) else si_rows.now_cell()
            row = compose({**body, "user": str(body.get("user", "dry-run"))},
                          next_ident(repo, si_refs.obs_ledger_text(repo)), ref, cell)
            findings = self_check(row, row_max_bytes)
    return {"ok": not findings, "row": row, "row_bytes": len(row.encode("utf-8")),
            "row_max_bytes": row_max_bytes,
            "findings": [{"code": c, "detail": d} for c, d in findings]}


__all__ = ["body_problems", "compose", "self_check", "next_ident", "ref_used", "preview"]
