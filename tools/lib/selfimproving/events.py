"""SelfImproving 事件帳本：讀取、封閉詞彙與欄位表判準、家目錄解析（TCS-SelfImproving-P1 R30、R31）。

只讀、純標準庫：本檔不開檔寫入、不碰 git；寫入走 `evwrite.py`（rw 類）。輸入是位元組或已解析的
事件 dict，輸出是形態問題（碼＋說明）；列級判級與重放由 `evcheck.py`、折疊由 `fold.py`。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from .evspec import (  # noqa: F401  # 再匯出：既有呼叫端以 si_events.<名> 取用
    _ALWAYS_OPTIONAL,
    _ATTR_KEYS,
    _COMMON,
    _CONSOLE_KEYS,
    _CONSOLE_ONLY,
    _CONSUMED,
    _DEC_OPTIONAL,
    _PROP_ONLY,
    _SHA,
    _SKIP_KEYS,
    _SPEC,
    _SPEC2,
    _T_RE,
    _WITH_CLASS,
    _WITH_DIGEST,
    _WITH_REASON,
    ACCOUNT_RE,
    ACTIONS,
    APP_RE,
    ATT_RE,
    CLS_VALUES,
    DEC_RE,
    DEF_ID_RE,
    DKINDS,
    ITEM_KINDS,
    KEY_ID_RE,
    KINDS,
    LEDGER_REL,
    OBS_ID_RE,
    PROP_RE,
    PROP_STATES,
    PROPOSALS_REL,
    REASON_CLASSES,
    ROOT_CAUSE_RE,
    ROUTES,
    RUN_RE,
    SHA40_RE,
    SHA256_RE,
    SKIP_REASONS,
    SRC_ID_RE,
    TRANSCRIPT_QUOTE_ONLY,
    VERIFY_REASONS,
    _bool_or_null,
    _conditional2,
    _dec_carrier,
    _dec_rules,
    _forbidden2,
    _hashable,
    _int,
    _Issues,
    _item,
    _line1,
    _list_of,
    _note,
    _outcomes,
    _preimage,
    _re,
    _required2,
    _s,
    _sandbox_rules,
    _scan_src,
    _sha_or_null,
    _str,
    _verify_rules,
    dec_key_problems,
    fourq_path,
    fourq_rules,
    valid_by,
    valid_t,
    valid_uuid,
)


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
        return out + [("EVENT-KIND", f"kind {obj['kind']!r} 不在 {len(KINDS)} 個詞彙內")]
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


def _p4_rules(kind: str, obj: dict, body: dict) -> list[tuple[str, str]]:
    """P4 條件規則（R139）：載體對應的必備／不得有鍵；`due_at` 配 trigger；成對鍵。"""
    out: list[tuple[str, str]] = []
    miss, unk = "EVENT-KEY-MISSING", "EVENT-KEY-UNKNOWN"
    if kind == "sched.set":
        car = _hashable(obj.get("carrier"))
        want = {"console": _CONSOLE_KEYS, "transcript": {"sid", "line"}, "host": set()}.get(car)
        if want is not None:
            have = set(body) & (_CONSOLE_KEYS | {"sid", "line"})
            out += [(miss, f"sched.set（{car}）缺 {k}") for k in sorted(want - have)]
            out += [(unk, f"sched.set（{car}）不得有 {k}") for k in sorted(have - want)]
            if car == "host" and obj.get("enabled") is not False:
                out.append(("EVENT-TYPE", "sched.set 的 host 載體只限 enabled=false"))
    elif kind == "sched.skip" and {"carrier", "audit_ref"} & set(body):
        out += [(miss, f"sched.skip 的 {k} 與 carrier 須成對") for k in ("carrier", "audit_ref")
                if k not in body]
    elif kind == "run.open":
        trig, has = obj.get("trigger"), set(body)
        if trig == "f" and "due_at" not in has:
            out.append((miss, "run.open（trigger f）缺 due_at"))
        if trig in tuple("abcde") and "due_at" in has:
            out.append((unk, "run.open 的 due_at 只限 trigger f"))
        if "carrier" in has and trig != "a":
            out.append(("EVENT-TYPE", "run.open 的 carrier 只限 trigger a"))
        extra = _CONSOLE_KEYS & has
        if "carrier" in has:
            out += [(miss, f"run.open（console）缺 {k}") for k in sorted(_CONSOLE_KEYS - has)]
        else:
            out += [(unk, f"run.open 無 carrier 時不得有 {k}") for k in sorted(extra)]
    return out


def _conditional(kind: str, obj: dict, body: dict) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = _p4_rules(kind, obj, body)
    if kind.startswith("fourq."):
        out += fourq_rules(kind, obj, body)
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
