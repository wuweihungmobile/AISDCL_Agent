"""SelfImproving OBS 寫入：`obs-add`、`obs-close`（TCS-SelfImproving-P2 R96 (c)、R97）。

能力類別 `rw`：只動工作樹的 OBS 帳本（不 commit）與事件帳本（經 `wv.append` 的寫入鎖）。寫入順序＝
鎖內重讀 OBS 帳本、配號、改檔（先列後事件）、追加事件；任一步失敗回退（`State.cleanups`）：事件追加
失敗時僅在帳本長度仍等於改寫後長度才還原，否則不動並於 stderr 印 `OBS-ORPHAN`（由 `check` 的
`obs.console_audit` 標紅承接）。改檔＝同目錄 tmp 檔寫完、flush、fsync 後 `os.replace`，
單次嘗試不重試；任何 `OSError` 就地轉 `LEDGER-WRITE-FAILED` 拒收（R97）。
OBS 寫入動詞只有 `obs-add` 與 `obs-close`：沒有刪除、改號、編輯（AC-SI-35-3）。
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

from . import check as si_check
from . import consoleaudit, evwrite, obsrows
from . import events as si_events
from . import refs as si_refs
from . import rows as si_rows
from . import writeverbs as wv
from .decwrite import ok_out, refuse_unattended
from .ledger import parse_ledger, split_lines

PAUSE_HOOK = None  # 測試鉤子：預檢之後、鎖內重讀之前
_KEYS = ("event_max_bytes", "row_max_bytes")
_DISP_CODES = {"DISP-ENUM": "DISPOSITION-INVALID", "DISP-DEFER-LATER": "DISPOSITION-INVALID",
               "DISP-TEXT-MISSING": "DISPOSITION-TEXT-MISSING"}


def _atomic_write(path: Path, data: bytes) -> None:
    """tmp 寫完→flush→fsync→`os.replace`（單次嘗試不重試）；任何 `OSError`（含 tmp 清理）就地轉
    `LEDGER-WRITE-FAILED` 拒收（R97：rc 1、零殘留），原生例外不外洩。"""
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        try:
            with tmp.open("wb") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)
    except OSError as exc:
        raise evwrite.Reject([("LEDGER-WRITE-FAILED", type(exc).__name__)]) from exc


def _prepare(repo: Path, verb: str, ref: str, kind: str, as_json: bool):
    """共同前置：回 (稽核檔, 事件, params)；不符回拒收 `Out`。"""
    refused = refuse_unattended(repo, verb, as_json)
    if refused:
        return refused
    params = wv.params_for(repo, *_KEYS)
    si = si_events.si_dir()
    try:
        evwrite.ensure_home(si)
    except evwrite.HomeUnwritable as exc:
        raise wv.UsageError(f"HOME-UNWRITABLE {exc}") from exc
    try:
        audit = consoleaudit.verify(consoleaudit.audit_path(si, ref))
    except consoleaudit.AuditError as exc:
        return wv.reject(repo, verb, [(exc.code, exc.detail)], as_json)
    events = si_events.load_sound_events(repo / si_events.LEDGER_REL) or []
    if audit.body["kind"] != kind:
        return wv.reject(repo, verb, [("AUDIT-KIND-MISMATCH", f"稽核檔 kind 為 "
                                       f"{audit.body['kind']}，{verb} 只收 {kind}")], as_json)
    if obsrows.ref_used(repo, events, ref):
        return wv.reject(repo, verb, [("AUDIT-REF-REUSED", f"audit_ref {ref} 已入帳過")], as_json)
    return audit, events, params


def _insert_row(text: str, row: str) -> str:
    """把列插在最後一個資料列之後（說明散文之前）；沿用該行的行尾（LF 或 CRLF）。"""
    last = max(r.lineno for r in parse_ledger(text).rows)
    pieces = text.split("\n")
    crlf = pieces[last - 1].endswith("\r")
    pieces.insert(last, row + ("\r" if crlf else ""))
    return "\n".join(pieces)


def _orphan_guard(path: Path, raw: bytes, new: bytes):
    """事件追加失敗時的回退：帳本長度仍等於改寫後長度才截回追加前位元組，否則印 `OBS-ORPHAN`。"""
    def restore() -> None:
        try:
            same_len = len(path.read_bytes()) == len(new)
        except OSError:
            same_len = False
        if same_len:
            try:
                _atomic_write(path, raw)
            except evwrite.Reject:
                pass  # 還原是盡力而為（cleanup 語意）：失敗不得遮蔽使事件追加失敗的原例外
        else:
            sys.stderr.write("OBS-ORPHAN OBS 帳本已被他處改動，未截回；孤列由 check 的 "
                             "obs.console_audit 標紅\n")
    return restore


def _event(audit: consoleaudit.Audit, kind: str, by: str, obs: str, ref: str) -> dict:
    return {"kind": kind, "by": by, "obs": obs, "audit_ref": ref, "audit_sha256": audit.sha,
            "key_id": audit.key_id, "decider": audit.body["user"], "carrier": "console"}


def _ledger_path(repo: Path) -> Path:
    return repo / si_check.LEDGER_REL


def add_console_row(repo: Path, audit_ref: str, by: str, as_json: bool = False) -> tuple[int, str]:
    out = _add(repo, audit_ref, by, as_json)
    return out.rc, out.text


def _add(repo: Path, ref: str, by: str, as_json: bool) -> wv.Out:
    got = _prepare(repo, "obs-add", ref, "obs-add", as_json)
    if isinstance(got, wv.Out):
        return got
    audit, events, params = got
    body, path = audit.body, _ledger_path(repo)
    codes = obsrows.body_problems(body, set(si_refs.obs_rows(repo)))
    text = si_refs.obs_ledger_text(repo)
    if text is None:
        raise wv.UsageError(f"OBS 帳本不存在：{path}")
    if not codes:
        row = obsrows.compose(body, obsrows.next_ident(repo, text), ref,
                              consoleaudit.row_time(body["time"]))
        codes = obsrows.self_check(row, params["row_max_bytes"], parse_ledger(text).tz)
    if codes:
        return wv.reject(repo, "obs-add", codes, as_json)
    if PAUSE_HOOK is not None:
        PAUSE_HOOK()

    def build(state):
        if obsrows.ref_used(repo, state.events, ref):
            raise evwrite.Reject([("AUDIT-REF-REUSED", "寫入鎖內重驗：audit_ref 已入帳")])
        raw = path.read_bytes()
        cur = raw.decode("utf-8")
        ident = obsrows.next_ident(repo, cur)
        row2 = obsrows.compose(body, ident, ref, consoleaudit.row_time(body["time"]))
        bad = obsrows.self_check(row2, params["row_max_bytes"], parse_ledger(cur).tz)
        if bad:
            raise evwrite.Reject(bad)
        new = _insert_row(cur, row2).encode("utf-8")
        _atomic_write(path, new)
        state.cleanups.append(_orphan_guard(path, raw, new))
        return _event(audit, "obs.add", by, ident, ref)

    return wv.append(repo, "obs-add", build, params, as_json, lambda e: ok_out(
        "obs.add", e["seq"], e["obs"], [("audit_ref", ref)], as_json).text)


def _replace_disposition(line: str, disp: str) -> str:
    """只改該列第 8 欄（處置）：保留該欄原有的前後空白與行內其餘位元組逐字不變。"""
    cr = "\r" if line.endswith("\r") else ""
    body = line[:-1] if cr else line
    pipes = [i for i, ch in enumerate(body) if ch == "|" and (i == 0 or body[i - 1] != "\\")]
    seg = body[pipes[7] + 1:pipes[8]]
    lead, tail = seg[:len(seg) - len(seg.lstrip())], seg[len(seg.rstrip()):]
    return body[:pipes[7] + 1] + lead + disp + tail + body[pipes[8]:] + cr


def _close_codes(body: dict, params: dict, line: str, tz: str | None) -> list:
    disp = body.get("disposition")
    if not isinstance(disp, str) or not isinstance(body.get("obs_id"), str):
        return [("AUDIT-BODY-INVALID", "obs-close 的 body 須有字串 obs_id 與 disposition")]
    if "|" in disp:
        return [("PIPE-IN-FIELD", "disposition 含 |（會破壞九欄表）")]
    if guard := consoleaudit.body_guard("obs-close", body):  # R136 (d)：先於組列後自驗
        return guard
    if si_rows.disp_token(disp) == "open":
        return [("DISPOSITION-INVALID", "open 不是終值")]
    new = _replace_disposition(line, disp)
    bad = obsrows.self_check(new.rstrip("\r"), params["row_max_bytes"], tz)
    return [(_DISP_CODES.get(c, c), d) for c, d in bad]


def close_console_row(repo: Path, audit_ref: str, by: str,
                      as_json: bool = False) -> tuple[int, str]:
    out = _close(repo, audit_ref, by, as_json)
    return out.rc, out.text


def _close(repo: Path, ref: str, by: str, as_json: bool) -> wv.Out:
    got = _prepare(repo, "obs-close", ref, "obs-close", as_json)
    if isinstance(got, wv.Out):
        return got
    audit, events, params = got
    body, path = audit.body, _ledger_path(repo)
    raw0 = path.read_bytes() if path.is_file() else None
    if raw0 is None:
        raise wv.UsageError(f"OBS 帳本不存在：{path}")
    lines = split_lines(raw0.decode("utf-8"))
    row = next((r for r in parse_ledger(raw0.decode("utf-8")).rows
                if r.nine and r.kind == 1 and r.ident == body.get("obs_id")), None)
    codes: list = []
    if row is None:
        known = body.get("obs_id") in si_refs.obs_rows(repo)
        codes = [("OBS-ARCHIVED", "該列只在封存檔") if known else
                 ("OBS-NOT-FOUND", f"{body.get('obs_id')} 不在 OBS 主帳本")]
    elif row.cells[7] != "open":
        codes = [("NOT-OPEN", f"{row.ident} 的處置不是恰為 open")]
    else:
        codes = _close_codes(body, params, row.raw, parse_ledger(raw0.decode("utf-8")).tz)
    if codes:
        return wv.reject(repo, "obs-close", codes, as_json)
    if PAUSE_HOOK is not None:
        PAUSE_HOOK()
    del lines

    def build(state):
        raw = path.read_bytes()
        if hashlib.sha256(raw).digest() != hashlib.sha256(raw0).digest():
            raise evwrite.Reject([("LEDGER-CHANGED", "預檢之後 OBS 帳本已被改動")])
        text = raw.decode("utf-8")
        pieces = text.split("\n")
        pieces[row.lineno - 1] = _replace_disposition(pieces[row.lineno - 1], body["disposition"])
        new = "\n".join(pieces).encode("utf-8")
        _atomic_write(path, new)
        state.cleanups.append(_orphan_guard(path, raw, new))
        ev = _event(audit, "obs.close", by, row.ident, ref)
        return {**ev, "disposition": body["disposition"]}

    return wv.append(repo, "obs-close", build, params, as_json, lambda e: ok_out(
        "obs.close", e["seq"], e["obs"], [("audit_ref", ref)], as_json).text)


__all__ = ["PAUSE_HOOK", "add_console_row", "close_console_row"]
