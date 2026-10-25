"""SelfImproving 事件帳本：讀取、封閉詞彙與欄位表判準、家目錄解析（TCS-SelfImproving-P1 R30、R31）。

只讀、純標準庫：本檔不開檔寫入、不碰 git；寫入走 `evwrite.py`（rw 類）。輸入是位元組或已解析的
事件 dict，輸出是形態問題（碼＋說明）；列級判級與重放由 `evcheck.py`、折疊由 `fold.py`。
"""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

OBS_ID_RE = re.compile(r"^OBS-SI-\d{3,}$")
DEF_ID_RE = re.compile(r"^DEF-\d+-\d+$")
RUN_RE = re.compile(r"^RUN-SI-\d{3,}$")
PROP_RE = re.compile(r"^PROP-SI-\d{3,}$")
ATT_RE = re.compile(r"^ATT-SI-\d{3,}$")
DEC_RE = re.compile(r"^DEC-SI-\d{3,}$")
APP_RE = re.compile(r"^APP-SI-\d{3,}$")
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
KEY_ID_RE = re.compile(r"^[0-9a-f]{8}$")
ACCOUNT_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_T_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")

LEDGER_REL = "docs/06_quality/SelfImproving_Event_Ledger.jsonl"
PROPOSALS_REL = "docs/06_quality/SelfImproving_Proposals"
KINDS = (
    "run.open", "run.close", "research.scan", "research.skip", "attr", "attr.confirm",
    "attr.reject", "prop", "card", "dec", "heldout.freeze", "app.sandbox", "app.verify",
    "app.promote", "app.rollback", "mea.open", "mea.close", "mea.amend", "mea.report",
    "obs.add", "obs.close",
)
PROP_STATES = ("proposed", "approved", "rejected", "returned", "handed-off", "sandboxed",
               "verified", "promoted", "measuring", "closed")
ROOT_CAUSE_RE = re.compile(r"^[a-z][a-z0-9-]*/[a-z][a-z0-9-]*$")
SRC_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
ITEM_KINDS = ("DEF", "OBS", "RULE", "PLAYBOOK_STEP", "DOC", "MEMORY_ENTRY", "NONE")
CLS_VALUES = ("M", "P", "R", "D", "evaluator-change", "loop-self")
ACTIONS = ("add", "modify", "delete", "retire")
ROUTES = ("loop", "handoff:DEF", "handoff:R", "handoff:T1", "handoff:PRD")
_COMMON = ("seq", "t", "kind", "by")


@dataclass
class Line:
    no: int
    nbytes: int
    obj: dict | None


def si_dir(env: dict | None = None) -> Path:
    """家目錄機器狀態：`AUTOSDD_SI_DIR` 非空則取之，否則 `~/.autosdd/selfimproving`。"""
    val = (env if env is not None else os.environ).get("AUTOSDD_SI_DIR", "")
    return Path(val) if val.strip() else Path.home() / ".autosdd" / "selfimproving"


def read_lines(raw: bytes) -> list[Line]:
    """逐行解析：容忍開頭 BOM 與行尾單一 CR；空白行、非 UTF-8、非 JSON 物件的行 obj 為 None。"""
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    parts = raw.split(b"\n")
    if parts and parts[-1] == b"":
        parts.pop()
    out = []
    for i, seg in enumerate(parts, start=1):
        seg = seg[:-1] if seg.endswith(b"\r") else seg
        obj = None
        try:
            val = json.loads(seg.decode("utf-8")) if seg.strip() else None
            obj = val if isinstance(val, dict) else None
        except (ValueError, UnicodeDecodeError):
            obj = None
        out.append(Line(i, len(seg), obj))
    return out


def load_events(path: Path) -> list[dict] | None:
    """事件帳本的已解析事件（略過無法解析的行）；檔不存在回 None。"""
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    return [ln.obj for ln in read_lines(raw) if ln.obj is not None]


def sound(events: list[dict]) -> list[dict]:
    """通過 `validate` 的事件（折疊與各消費者共用）；未通過者只由 `events.structure` 報 EVENT-*，
    不進折疊、不進任何查表，所以型別怪異的手寫事件不會讓下游崩潰（R37）。"""
    return [e for e in events if isinstance(e, dict) and not validate(e)]


def load_sound_events(path: Path) -> list[dict] | None:
    """`load_events` 再過 `sound`；檔不存在回 None。"""
    loaded = load_events(path)
    return None if loaded is None else sound(loaded)


def _hashable(v):
    """查表鍵一律先過這關：型別怪異（list／dict）的值當成查不到，不讓 `dict.get` 拋 TypeError。"""
    return v if isinstance(v, str) else None


def _int(v, lo: int = 0) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= lo


def _s(v) -> bool:
    return isinstance(v, str) and bool(v)


def _re(rx):
    return lambda v: isinstance(v, str) and bool(rx.match(v))


def _list_of(pred, lo: int = 1):
    return lambda v: isinstance(v, list) and len(v) >= lo and all(pred(x) for x in v)


def valid_by(v) -> bool:
    return isinstance(v, str) and 0 < len(v) <= 32 and not any(c.isspace() for c in v)


def valid_t(v) -> bool:
    if not (isinstance(v, str) and _T_RE.match(v)):
        return False
    try:
        return datetime.fromisoformat(v).utcoffset() is not None
    except ValueError:
        return False


def valid_uuid(v) -> bool:
    try:
        return isinstance(v, str) and str(uuid.UUID(v)) == v.lower()
    except ValueError:
        return False


def _line1(v) -> bool:
    return isinstance(v, str) and bool(v) and "\n" not in v and "\r" not in v


def _bool_or_null(v) -> bool:
    return v is None or isinstance(v, bool)


def _sha_or_null(v) -> bool:
    return v is None or (isinstance(v, str) and bool(SHA256_RE.match(v)))


def _note(v) -> bool:
    return isinstance(v, str) and 1 <= len(v) <= 120 and "\n" not in v and "\r" not in v


def _item(v) -> bool:
    return (isinstance(v, list) and len(v) == 2 and v[0] in ITEM_KINDS and isinstance(v[1], str))


def _outcomes(v) -> bool:
    return (isinstance(v, dict) and all(PROP_RE.match(k) and x in PROP_STATES
                                        for k, x in v.items()))


def _scan_src(v) -> bool:
    keys = {"id", "sha256", "bytes", "changed", "http_status"}
    return (isinstance(v, dict) and set(v) == keys and _re(SRC_ID_RE)(v["id"])
            and _re(SHA256_RE)(v["sha256"]) and _int(v["bytes"]) and isinstance(v["changed"], bool)
            and _int(v["http_status"], 200) and v["http_status"] <= 299)


def _preimage(v) -> bool:
    return isinstance(v, dict) and all(isinstance(k, str) and _re(SHA256_RE)(x)
                                       for k, x in v.items())


_SHA = _re(SHA256_RE)
# kind → {鍵: 型別判準}；required 另列（其餘為條件鍵，由 conditional() 處理）
_SPEC: dict[str, dict] = {
    "run.open": {"run": _re(RUN_RE), "trigger": lambda v: v in tuple("abcde"),
                 "coords": _list_of(_s), "head_sha": _re(SHA40_RE)},
    "run.close": {"run": _re(RUN_RE), "outcomes": _outcomes, "no_event": lambda v: v is True},
    "research.scan": {"run": _re(RUN_RE), "sources": _list_of(_scan_src), "sources_sha256": _SHA,
                      "fetched_at": valid_t},
    "research.skip": {"run": _re(RUN_RE), "reason": lambda v: v in ("quota-band", "offline",
                                                                    "helmsman"),
                      "note": _note, "band": lambda v: _s(v) and v.lower() != "free",
                      "sid": valid_uuid, "line": lambda v: _int(v, 1)},
    "attr": {"id": _re(ATT_RE), "type": lambda v: v in ("root", "link"),
             "obs": _list_of(_re(OBS_ID_RE)), "items": _list_of(_item),
             "root_cause": _re(ROOT_CAUSE_RE), "from": _re(OBS_ID_RE),
             "reopens": lambda v: isinstance(v, str) and bool(OBS_ID_RE.match(v)
                                                              or DEF_ID_RE.match(v))},
    "attr.confirm": {"att": _re(ATT_RE)},
    "attr.reject": {"att": _re(ATT_RE), "note": _note},
    "prop": {"id": _re(PROP_RE), "rev": lambda v: _int(v, 1), "run": _re(RUN_RE),
             "base": _re(SHA40_RE), "cls": lambda v: v in CLS_VALUES,
             "action": lambda v: v in ACTIONS, "route": lambda v: v in ROUTES,
             "target": _list_of(_s), "touched_count": lambda v: _int(v, 0),
             "touched_sha256": _SHA, "patch_sha256": _SHA, "body_sha256": _SHA, "digest": _SHA,
             "sources": _list_of(lambda x: isinstance(x, str) and bool(
                 OBS_ID_RE.match(x) or DEF_ID_RE.match(x))),
             "proposer": valid_by, "reviewer": lambda v: v is None or valid_by(v),
             "preimage": _preimage},
}


def _str(v) -> bool:
    return isinstance(v, str)


# mea.*（P3 才有完整欄位表）被折疊／查表讀取的鍵：有帶就須型別合法（缺鍵由 TRANSITION-ORPHAN 判），
# 使 `sound()` 之後的消費者不必再防禦型別（R37；`from`、`cause` 等不被讀取者不判）。
_PROP_ONLY = {"prop": _str}
_CONSUMED: dict[str, dict] = {
    "mea.open": _PROP_ONLY, "mea.report": _PROP_ONLY,
    "mea.close": {"prop": _str, "result": _str},
    "mea.amend": {"prop": _str, "window": lambda v: _int(v, 1), "to": _str},
}
_ALWAYS_OPTIONAL = {"run.close": {"outcomes", "no_event"},
                    "research.skip": {"band", "sid", "line"},
                    "attr": {"obs", "items", "root_cause", "from", "reopens"},
                    "prop": {"preimage"}}
_ATTR_KEYS = {"root": {"obs", "items", "root_cause"}, "link": {"from", "reopens"}}
_SKIP_KEYS = {"quota-band": {"band"}, "helmsman": {"sid", "line"}, "offline": set()}


DKINDS = ("approve", "reject", "return", "promote", "decline-promote", "rollback", "unblock",
          "resume", "ack-handoff")
REASON_CLASSES = ("證據不足", "風險過高", "工件類別錯", "已被涵蓋", "範圍外", "卡面不清", "未說明")
VERIFY_REASONS = (
    "SANDBOX-NOT-APPLIED", "SANDBOX-EXPORT-FAILED", "SANDBOX-APPLY-TIMEOUT", "TOUCHED-SUPERSET",
    "ROLLBACK-DRYRUN-FAILED", "NO-PROBES", "CARRIER-PROOF-FAILED", "HELDOUT-DIGEST-MISMATCH",
    "HELDOUT-TOO-SMALL", "HELDOUT-EXPOSED", "EXPOSURE-UNKNOWN", "PROBE-TIMEOUT",
    "BASELINE-NOT-RED", "PATCHED-NOT-GREEN", "MUTATION-NOT-RED", "MUTATION-ABSENT",
)
TRANSCRIPT_QUOTE_ONLY = ("quote", "sid", "line")  # `console` 載體不得有
_CONSOLE_ONLY = ("audit_ref", "audit_sha256", "key_id")  # `transcript` 載體不得有
_WITH_DIGEST = ("approve", "reject", "return", "promote", "decline-promote", "ack-handoff")
_WITH_REASON = ("reject", "decline-promote", "return", "rollback", "resume")
_WITH_CLASS = ("reject", "decline-promote", "return")
_Issues = list[tuple[str, str]]


# P2 九種 kind：鍵 → 型別判準（必備與否由 `required`／`conditional` 定）
_SPEC2: dict[str, dict] = {
    "card": {"prop": _re(PROP_RE), "rev": lambda v: _int(v, 1), "digest": _SHA,
             "card_sha256": _SHA},
    "dec": {"id": _re(DEC_RE), "dkind": lambda v: v in DKINDS, "decider": _s,
            "decided_at": valid_t, "prop": _re(PROP_RE), "run": _re(RUN_RE), "digest": _SHA,
            "reason": _line1, "reason_class": lambda v: v in REASON_CLASSES,
            "flags": _list_of(lambda x: x == "unverified_ack", 0),
            "carrier": lambda v: v in ("transcript", "console"), "quote": _line1,
            "sid": valid_uuid, "line": lambda v: _int(v, 1), "card_seq": lambda v: _int(v, 1),
            "audit_ref": valid_uuid, "audit_sha256": _SHA, "key_id": _re(KEY_ID_RE)},
    "heldout.freeze": {"prop": _re(PROP_RE), "digest": _SHA, "n": lambda v: _int(v, 1),
                       "frozen_by": valid_by},
    "app.sandbox": {"id": _re(APP_RE), "prop": _re(PROP_RE), "rev": lambda v: _int(v, 1),
                    "base": _re(SHA40_RE), "sandbox_sha256": _sha_or_null,
                    "applied": lambda v: isinstance(v, bool), "touched_ok": _bool_or_null,
                    "rollback_ok": _bool_or_null,
                    "fail_code": lambda v: v in (None, "SANDBOX-EXPORT-FAILED",
                                                 "SANDBOX-APPLY-TIMEOUT")},
    "app.verify": {"id": _re(APP_RE), "prop": _re(PROP_RE), "rev": lambda v: _int(v, 1),
                   "verdict": lambda v: v in ("PASS", "FAIL", "NE"),
                   "baseline_red": _bool_or_null, "patched_green": _bool_or_null,
                   "mutated_red": _bool_or_null, "carrier_proof": _bool_or_null,
                   "probes_n": lambda v: _int(v, 0), "verify_sha256": _sha_or_null,
                   "heldout_digest": _sha_or_null,
                   "reasons": _list_of(lambda x: x in VERIFY_REASONS, 0)},
    "app.promote": {"id": _re(APP_RE), "prop": _re(PROP_RE), "rev": lambda v: _int(v, 1),
                    "head_sha": _re(SHA40_RE), "pre_sha256": _SHA, "post_sha256": _SHA,
                    "unverified_ack": lambda v: isinstance(v, bool)},
    "app.rollback": {"id": _re(APP_RE), "prop": _re(PROP_RE), "rev": lambda v: _int(v, 1),
                     "pre_sha256": _SHA, "post_sha256": _SHA},
    "obs.add": {"obs": _re(OBS_ID_RE), "audit_ref": valid_uuid, "audit_sha256": _SHA,
                "key_id": _re(KEY_ID_RE), "decider": _re(ACCOUNT_RE),
                "carrier": lambda v: v == "console"},
    "obs.close": {"obs": _re(OBS_ID_RE), "audit_ref": valid_uuid, "audit_sha256": _SHA,
                  "key_id": _re(KEY_ID_RE), "decider": _re(ACCOUNT_RE),
                  "carrier": lambda v: v == "console", "disposition": _line1},
}
_DEC_OPTIONAL = {"prop", "run", "digest", "reason", "reason_class", "flags", "carrier", "quote",
                 "sid", "line", "card_seq", "audit_ref", "audit_sha256", "key_id"}


def _dec_carrier(obj: dict) -> str:
    return obj["carrier"] if obj.get("carrier") in ("transcript", "console") else "transcript"


def _required2(kind: str, obj: dict) -> set[str]:
    """P2 kind 的必備鍵（條件必備依 `dkind` 與 `carrier`；值不合法時不推導其條件鍵）。"""
    req = set(_SPEC2[kind])
    if kind != "dec":
        return req
    req -= _DEC_OPTIONAL
    dk = obj.get("dkind")
    if dk not in DKINDS:
        return req
    req.add("run" if dk == "resume" else "prop")
    req |= {"digest"} if dk in _WITH_DIGEST else set()
    req |= {"reason"} if dk in _WITH_REASON else set()
    req |= {"reason_class"} if dk in _WITH_CLASS else set()
    if _dec_carrier(obj) == "transcript":
        req |= {"quote", "sid", "line"} | (set() if dk == "resume" else {"card_seq"})
    else:
        req |= set(_CONSOLE_ONLY)
    return req


def _forbidden2(kind: str, obj: dict) -> set[str]:
    """條件上「不得有」的鍵（出現＝EVENT-KEY-UNKNOWN）。"""
    if kind != "dec":
        return set()
    dk = obj.get("dkind")
    if dk not in DKINDS:
        return set()
    out = set()
    out |= {"digest"} if dk not in _WITH_DIGEST else set()
    out |= {"reason"} if dk not in _WITH_REASON else set()
    out |= {"reason_class"} if dk not in _WITH_CLASS else set()
    out |= {"flags"} if dk != "promote" else set()
    out |= {"prop"} if dk == "resume" and "run" in obj else set()
    out |= {"card_seq"} if dk == "resume" else set()
    out |= set(TRANSCRIPT_QUOTE_ONLY) | {"card_seq"} if _dec_carrier(obj) == "console" else set()
    out |= set(_CONSOLE_ONLY) if _dec_carrier(obj) == "transcript" else set()
    return out


def dec_key_problems(dkind: str, body: dict) -> _Issues:
    """R136 (b)：Console `decide` 的 body 之於該 `dkind` 的不收鍵（`reason`、非空 `flags`）
    與 `flags` 元素型別；與 `validate` 對 `dec` 同源（同一組 `_forbidden2`、`_SPEC2`）。"""
    forb = _forbidden2("dec", {"dkind": dkind, "carrier": "console"})
    out = [("EVENT-KEY-UNKNOWN", f"dec 的 {k} 對 {dkind} 不收") for k in ("reason", "flags")
           if k in body and k in forb and body[k] != []]
    if "flags" in body and not out and not _SPEC2["dec"]["flags"](body["flags"]):
        out.append(("EVENT-TYPE", "dec.flags 型別或值域不合"))
    return out


def _conditional2(kind: str, obj: dict) -> _Issues:
    """P2 kind 的條件規則與互斥（碼皆 EVENT-TYPE）。"""
    fn = {"dec": _dec_rules, "app.sandbox": _sandbox_rules, "app.verify": _verify_rules}.get(kind)
    return fn(obj) if fn else []


def _dec_rules(obj: dict) -> _Issues:
    out: _Issues = []
    if "prop" in obj and "run" in obj:
        out.append(("EVENT-TYPE", "dec 的 prop 與 run 須恰一"))
    if _dec_carrier(obj) == "transcript":
        if "decider" in obj and obj["decider"] != "掌舵者":
            out.append(("EVENT-TYPE", "transcript 載體的 decider 恆為「掌舵者」"))
        cs = obj.get("card_seq")
        if _int(cs, 1) and _int(obj.get("seq"), 1) and cs >= obj["seq"]:
            out.append(("EVENT-TYPE", "card_seq 須小於本筆 seq"))
    elif "decider" in obj and not ACCOUNT_RE.match(str(obj["decider"])):
        out.append(("EVENT-TYPE", "console 載體的 decider 須合 ^[A-Za-z0-9_.-]{1,64}$"))
    return out


def _sandbox_rules(obj: dict) -> _Issues:
    out: _Issues = []
    applied, fc, sha = obj.get("applied"), obj.get("fail_code"), obj.get("sandbox_sha256")
    ok, rb = obj.get("touched_ok"), obj.get("rollback_ok")
    if applied is True:
        if not (isinstance(ok, bool) and isinstance(rb, bool)) or fc is not None or sha is None:
            out.append(("EVENT-TYPE", "applied 為真須 touched_ok／rollback_ok 皆布林、"
                        "fail_code 為 null、sandbox_sha256 非 null"))
    elif applied is False and (ok is not None or rb is not None):
        out.append(("EVENT-TYPE", "applied 為假時 touched_ok 與 rollback_ok 皆須為 null"))
    if (fc == "SANDBOX-EXPORT-FAILED") != (sha is None) and "sandbox_sha256" in obj:
        out.append(("EVENT-TYPE", "fail_code 為 SANDBOX-EXPORT-FAILED ⇔ sandbox_sha256 為 null"))
    if fc == "SANDBOX-APPLY-TIMEOUT" and (applied is not False or sha is None):
        out.append(("EVENT-TYPE", "SANDBOX-APPLY-TIMEOUT 須 applied 為假且 sandbox_sha256 非 null"))
    return out


def _verify_rules(obj: dict) -> _Issues:
    out: _Issues = []
    rs, verdict = obj.get("reasons"), obj.get("verdict")
    known = verdict in ("PASS", "FAIL", "NE")
    if isinstance(rs, list) and known and (not rs) != (verdict == "PASS"):
        out.append(("EVENT-TYPE", "reasons 為空陣列 ⇔ verdict 為 PASS"))
    n, vs = obj.get("probes_n"), obj.get("verify_sha256")
    if _int(n, 0) and "verify_sha256" in obj and (n == 0) != (vs is None):
        out.append(("EVENT-TYPE", "probes_n 為 0 ⇔ verify_sha256 為 null"))
    return out



def _required(kind: str, obj: dict) -> set[str]:
    req = set(_SPEC[kind]) - _ALWAYS_OPTIONAL.get(kind, set())
    if kind == "attr":
        req |= _ATTR_KEYS.get(_hashable(obj.get("type")), set())
    return req


def validate(obj: dict) -> list[tuple[str, str]]:
    """事件 dict 的形態問題（碼, 說明）：共通鍵、詞彙、值域與 P1 欄位表的必備／表外／型別。"""
    out: list[tuple[str, str]] = []
    for key in _COMMON:
        if key not in obj:
            out.append(("EVENT-KEY-MISSING", f"共通鍵 {key} 缺"))
    if out:
        return out
    if not _int(obj["seq"], 1):
        out.append(("EVENT-TYPE", "seq 須為整數 ≥1（非布林）"))
    if not valid_t(obj["t"]):
        out.append(("EVENT-TYPE", "t 須帶 offset 且合 ISO 形態"))
    if obj["kind"] not in KINDS:
        return out + [("EVENT-KIND", f"kind {obj['kind']!r} 不在 21 個詞彙內")]
    if not valid_by(obj["by"]):
        out.append(("EVENT-TYPE", "by 須為非空、無空白、≤32 字元的標籤"))
    kind = obj["kind"]
    p2 = kind in _SPEC2
    if kind not in _SPEC and not p2:
        consumed = _CONSUMED.get(kind, {})
        return out + [("EVENT-TYPE", f"{kind}.{key} 型別或值域不合")
                      for key, ok in consumed.items() if key in obj and not ok(obj[key])]
    spec, body = (_SPEC2 if p2 else _SPEC)[kind], {k: v for k, v in obj.items()
                                                       if k not in _COMMON}
    need = _required2(kind, obj) if p2 else _required(kind, obj)
    forb = _forbidden2(kind, obj) if p2 else set()
    for key in sorted(need - set(body)):
        out.append(("EVENT-KEY-MISSING", f"{kind} 缺必備鍵 {key}"))
    for key in sorted((set(body) - set(spec)) | (set(body) & forb)):
        out.append(("EVENT-KEY-UNKNOWN", f"{kind} 出現表外或不得有的鍵 {key}"))
    allowed = set(spec) - forb
    if kind == "attr" and _hashable(obj.get("type")) in _ATTR_KEYS:
        allowed -= {"obs", "items", "root_cause", "from", "reopens"} - _ATTR_KEYS[obj["type"]]
    for key in sorted(set(body) & allowed):
        if not spec[key](body[key]):
            out.append(("EVENT-TYPE", f"{kind}.{key} 型別或值域不合"))
    if kind == "attr":
        out += [("EVENT-KEY-UNKNOWN", f"attr（{obj.get('type')}）不得有鍵 {k}")
                for k in sorted((set(body) & set(spec)) - allowed)]
    out += _conditional2(kind, obj) if p2 else _conditional(kind, obj, body)
    return out


def _conditional(kind: str, obj: dict, body: dict) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if kind == "run.close" and (("outcomes" in body) == ("no_event" in body)):
        out.append(("EVENT-TYPE", "run.close 的 outcomes／no_event 須恰有一個"))
    if kind == "research.scan" and obj.get("by") != "researcher":
        out.append(("EVENT-TYPE", "research.scan 的 by 恆為 researcher"))
    if kind == "research.skip":
        if obj.get("by") != "main":
            out.append(("EVENT-TYPE", "research.skip 的 by 恆為 main"))
        want = _SKIP_KEYS.get(_hashable(obj.get("reason")))
        if want is not None and {"band", "sid", "line"} & set(body) != want:
            out.append(("EVENT-TYPE", "research.skip 的 reason 與附帶鍵（band／sid／line）不符"))
    if kind == "prop" and "cls" in obj and (("preimage" in body) != (obj["cls"] == "M")):
        out.append(("EVENT-TYPE", "prop 的 preimage 只准 M 類且 M 類必備"))
    return out
