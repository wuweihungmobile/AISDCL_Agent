"""SelfImproving Console 稽核檔與 HMAC 驗證（TCS-SelfImproving-P2 R94）。

能力類別 `ro`：CLI 只讀稽核檔、絕不寫。檔＝`<si>/console_audit/<audit_ref>.json`，外層鍵恰
`schema_rev`、`kind`、`audit_ref`、`subject`、`body`（字串）、`key_id`、`mac`。
簽章對象＝`body` 字串的 UTF-8 位元組（不重新序列化）：`mac`＝`HMAC-SHA256(金鑰位元組, body 位元組)`
小寫 hex；金鑰環 `AUTOSDD_SI_AUDIT_KEY` 為逗號分隔的金鑰字串，依 `key_id`
（金鑰位元組 sha256 的前 8 碼）選用。
金鑰衛生：本檔任何例外訊息都不含金鑰位元組。
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import events as si_events

KEY_ENV = "AUTOSDD_SI_AUDIT_KEY"
AUDIT_DIR = "console_audit"
KINDS = ("decide", "obs-add", "obs-close")
_OUTER_KEYS = {"schema_rev", "kind", "audit_ref", "subject", "body", "key_id", "mac"}
_USER_RE = re.compile(r"[A-Za-z0-9_.-]{1,64}")
_TIME_RE = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d")
_KEY_ID_RE = re.compile(r"[0-9a-f]{8}")
_MAC_RE = re.compile(r"[0-9a-f]{64}")


class AuditError(Exception):
    """稽核檔驗證失敗；`code` 為 R94 的碼。"""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code} {detail}".strip())
        self.code, self.detail = code, detail


@dataclass
class Audit:
    path: Path
    raw: bytes
    outer: dict
    body: dict

    @property
    def sha(self) -> str:
        return "sha256:" + hashlib.sha256(self.raw).hexdigest()

    @property
    def key_id(self) -> str:
        return self.outer["key_id"]


def audit_path(si: Path, ref: str) -> Path:
    return si / AUDIT_DIR / f"{ref}.json"


def key_ring(env=None) -> list[bytes]:
    """金鑰環：逗號分隔、各自去前後空白、空項略過；未設或全為空項＝空環。"""
    raw = (os.environ if env is None else env).get(KEY_ENV, "")
    return [k.strip().encode("utf-8") for k in raw.split(",") if k.strip()]


def row_time(when: str) -> str:
    """`YYYY-MM-DDTHH:MM:SS±HH:MM` → OBS 列的 `YYYY-MM-DD HH:MM ±HH:MM`（保留 offset、丟秒）。"""
    return f"{when[:10]} {when[11:16]} {when[19:]}"


def key_id_of(key: bytes) -> str:
    return hashlib.sha256(key).hexdigest()[:8]


def _outer(raw: bytes) -> dict:
    try:
        outer = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise AuditError("AUDIT-SCHEMA", "稽核檔不是 UTF-8 無 BOM 的 JSON") from exc
    ok = isinstance(outer, dict) and set(outer) == _OUTER_KEYS
    ok = ok and outer["schema_rev"] == 1 and not isinstance(outer["schema_rev"], bool)
    strs = ("kind", "audit_ref", "body", "key_id", "mac")
    ok = ok and all(isinstance(outer[k], str) for k in strs)
    ok = ok and (outer["subject"] is None or isinstance(outer["subject"], str))
    ok = ok and si_events.valid_uuid(outer["audit_ref"]) and _KEY_ID_RE.fullmatch(outer["key_id"])
    ok = ok and _MAC_RE.fullmatch(outer["mac"])
    if not ok:
        raise AuditError("AUDIT-SCHEMA", "外層鍵集合、型別或 schema_rev 不合")
    return outer


def _subject_of(body: dict):
    kind = body.get("kind")
    if kind == "decide":
        return body.get("run") if body.get("dkind") == "resume" else body.get("prop")
    return body.get("obs_id") if kind == "obs-close" else None


def parse(path: Path) -> Audit:
    """R94 驗證順序中不需金鑰的部分（檔→外層→body→ref→kind→user→role→time→subject）。"""
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise AuditError("AUDIT-FILE-MISSING", str(path.name)) from exc
    except OSError as exc:
        why = f"讀不到 {path.name}（{type(exc).__name__}）"
        raise AuditError("AUDIT-FILE-MISSING", why) from exc
    outer = _outer(raw)
    try:
        body = json.loads(outer["body"])
    except ValueError:
        body = None
    if not isinstance(body, dict):
        raise AuditError("AUDIT-BODY-INVALID", "body 不是 JSON 物件文字")
    if not (path.stem == outer["audit_ref"] == body.get("audit_ref")):
        raise AuditError("AUDIT-REF-MISMATCH", "檔名、外層、body 的 audit_ref 不一致")
    if outer["kind"] != body.get("kind") or outer["kind"] not in KINDS:
        raise AuditError("AUDIT-KIND-MISMATCH", "外層與 body 的 kind 不等或不在三值內")
    user = body.get("user")
    if not (isinstance(user, str) and _USER_RE.fullmatch(user)):
        raise AuditError("AUDIT-USER-FORMAT", "user 不合 ^[A-Za-z0-9_.-]{1,64}$ 或缺")
    if body.get("role") != "ADMIN":
        raise AuditError("ROLE-NOT-ADMIN", "role 須恆為 ADMIN")
    when = body.get("time")
    if not (isinstance(when, str) and _TIME_RE.fullmatch(when) and _valid_time(when)):
        raise AuditError("AUDIT-TIME-FORMAT", "time 須為 YYYY-MM-DDTHH:MM:SS±HH:MM（不收 Z）")
    if outer["subject"] != _subject_of(body):
        raise AuditError("AUDIT-SUBJECT-MISMATCH", "外層 subject 不等於 body 的對象")
    return Audit(path, raw, outer, body)


def _valid_time(text: str) -> bool:
    try:
        datetime.fromisoformat(text)
    except ValueError:
        return False
    return True


def _c0(text) -> bool:
    return isinstance(text, str) and any(ord(ch) < 0x20 for ch in text)


def body_guard(kind: str, body: dict) -> list[tuple[str, str]]:
    """R136：Console 三動詞的寫入前本文判準（純函式；在取鎖與組列之前呼叫）。回（碼, 說明）清單：
    (a) `CTRL-CHAR`（自由文字欄含 C0 控制字元）、(b) `EVENT-KEY-UNKNOWN`／`EVENT-TYPE`
    （與 `events.validate` 同源）、(c) `REASON-EMPTY`、(d) `DISPOSITION-INVALID`（含換行）。"""
    out: list[tuple[str, str]] = []
    if kind == "decide":
        dkind = body.get("dkind")
        if _c0(body.get("reason")):
            out.append(("CTRL-CHAR", "decide 的 reason 含控制字元"))
        if dkind in si_events._WITH_REASON and body.get("reason") == "":
            out.append(("REASON-EMPTY", f"{dkind} 的 reason 不得為空字串"))
        out += si_events.dec_key_problems(dkind, body)
    elif kind == "obs-add":
        texts = [body.get(k) for k in ("context", "symptom", "evidence", "exposure")]
        texts += list((body.get("marks_extra") or {}).values())
        if any(_c0(t) for t in texts):
            out.append(("CTRL-CHAR", "obs-add 的自由文字欄含控制字元（含換行）"))
    elif kind == "obs-close" and "\n" in str(body.get("disposition", "")):
        out.append(("DISPOSITION-INVALID", "disposition 含換行"))
    return out


def check_mac(audit: Audit, ring: list[bytes]) -> None:
    """金鑰環與 HMAC：環空＝KEY-MISSING（入帳不是回查，不降為 NE）；key_id 不在環＝KEY-UNKNOWN。"""
    if not ring:
        raise AuditError("AUDIT-KEY-MISSING", f"{KEY_ENV} 未設或為空")
    key = next((k for k in ring if key_id_of(k) == audit.key_id), None)
    if key is None:
        raise AuditError("AUDIT-KEY-UNKNOWN", f"key_id {audit.key_id} 不在金鑰環內")
    want = hmac.new(key, audit.outer["body"].encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(want, audit.outer["mac"]):
        raise AuditError("AUDIT-MAC-MISMATCH", "HMAC 不符")


def verify(path: Path, ring: list[bytes] | None = None) -> Audit:
    audit = parse(path)
    check_mac(audit, key_ring() if ring is None else ring)
    return audit


__all__ = ["Audit", "AuditError", "audit_path", "key_ring", "key_id_of", "parse", "check_mac",
           "verify", "row_time", "body_guard", "KEY_ENV", "AUDIT_DIR", "KINDS"]
