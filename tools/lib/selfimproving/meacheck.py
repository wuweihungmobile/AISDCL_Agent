"""SelfImproving `check` 第 33 項 `events.mea`：四種 `mea.*` 事件的欄位表判準（TCS-P3 R113、R115）。

能力類別 `ro`：只讀事件（不讀 OBS／DEF 帳本、不呼叫 git）。表外鍵 `MEA-KEY-UNKNOWN`、缺必備鍵
`MEA-KEY-MISSING`、型別或值域不合 `MEA-TYPE`、列舉外 `MEA-ENUM`；指向與轉移合法性（amend、第二個
`mea.open`）由 `fold` 的 `TRANSITION-ILLEGAL` 於 `events.transitions` 呈現，本項不重報。
"""

from __future__ import annotations

from . import events as si_events
from .ledger import Finding

RESULTS = ("clean", "recurred", "rolled-back", "pending")


def _int(lo: int):
    return lambda v: si_events._int(v, lo)


def _num01(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 1


def _opt(pred):
    return lambda v: v is None or pred(v)


def _missing(v) -> bool:
    return (isinstance(v, list) and len(v) <= 20 and v == sorted(set(v))
            and all(isinstance(x, str) and len(x) <= 60 for x in v))


def _ids(v) -> bool:
    return isinstance(v, list) and all(
        isinstance(x, str) and (si_events.OBS_ID_RE.match(x) or si_events.DEF_ID_RE.match(x))
        for x in v)


_FATAL = ("MEA-KEY-MISSING", "MEA-TYPE", "MEA-ENUM")  # 會使消費端崩潰或誤判的欄位問題
_PROP = lambda v: isinstance(v, str) and bool(si_events.PROP_RE.match(v))  # noqa: E731
_T = si_events.valid_t
_ENUM = {"result": RESULTS, "from": RESULTS, "to": RESULTS, "report": ("baseline", "check")}
_SPEC = {
    "mea.open": {"prop": _PROP, "w_opp": _int(1), "promote_seq": _int(1)},
    "mea.close": {"prop": _PROP, "result": None, "n_opp": _int(0), "at": _T},
    "mea.amend": {"prop": _PROP, "window": _int(1), "from": None, "to": None, "cause": _int(1)},
    "baseline": {"prop": _PROP, "report": None, "promote_seq": _int(1), "opp": _ids,
                 "events": _int(0), "pending": _int(0), "w_opp": _int(1), "w_evt": _int(1),
                 "w_min": _int(1), "anchor": _opt(_T)},
    "check": {"report": None, "fingerprint": lambda v: isinstance(v, str) and bool(
        si_events.SHA256_RE.match(v)), "metrics_rev": _int(0), "windows": _int(0),
        "m1_n": _int(0), "m1": _opt(_num01), "m4": _opt(_int(0)), "m5_main": _opt(_num01),
        "m5_all": _opt(_num01), "m5_n": _int(0), "falsified": si_events._bool_or_null,
        "missing": _missing},
}


def _schema(e: dict) -> str | None:
    if e["kind"] != "mea.report":
        return e["kind"]
    return e.get("report") if e.get("report") in ("baseline", "check") else None


def _field_codes(e: dict, spec: dict) -> list[tuple[str, str]]:
    out = []
    body = {k: v for k, v in e.items() if k not in si_events._COMMON}
    out += [("MEA-KEY-MISSING", f"缺必備鍵 {k}") for k in spec if k not in body]
    out += [("MEA-KEY-UNKNOWN", f"表外鍵 {k}") for k in body if k not in spec]
    for key, pred in spec.items():
        if key not in body:
            continue
        if key in _ENUM:
            if body[key] not in _ENUM[key] or not isinstance(body[key], str):
                out.append(("MEA-ENUM", f"{key} 不在列舉內"))
        elif not pred(body[key]):
            out.append(("MEA-TYPE", f"{key} 型別或值域不合"))
    ids, w = body.get("opp"), body.get("w_opp")
    if _ids(ids) and si_events._int(w, 1) and len(ids) > w:
        out.append(("MEA-TYPE", "opp 筆數超過 w_opp"))
    return out


def field_problems(events: list[dict]) -> list[tuple]:
    """欄位表不合（缺必備鍵、型別或值域、列舉外）的 `mea.*` 事件 → [(PROP 號或 None, 碼)]。

    消費端（窗規則、指標、匯出）一律視這些事件為「不可評估」（`mea-events-invalid`），不以
    traceback 結束；`check` 照報（`findings`）。PROP 號無法辨識者以 None 代表。"""
    out = []
    for e in events:
        if not e["kind"].startswith("mea."):
            continue
        schema = _schema(e)
        if schema is None:
            codes = ["MEA-KEY-MISSING" if "report" not in e else "MEA-ENUM"]
        elif schema in _SPEC:
            codes = [c for c, _ in _field_codes(e, _SPEC[schema])]
        else:
            continue
        prop = e.get("prop") if _PROP(e.get("prop")) else None
        out += [(prop, c) for c in codes if c in _FATAL]
    return out


def bad_props(events: list[dict]) -> set:
    """`field_problems` 涉及的 PROP 號集合（含 None＝有無法歸屬的壞事件）。"""
    return {p for p, _ in field_problems(events)}


def reject_codes(problems: list[tuple]) -> list[tuple[str, str]]:
    """`measure` 的拒收碼（沿用 `check` 的碼，不新造）。"""
    return [(c, f"{c}：mea.* 事件欄位不合，不在不可評估的帳本上追加")
            for c in sorted({c for _, c in problems})]


def findings(events: list[dict]) -> list[Finding]:
    """`events.mea` 的 FAIL findings（事件須已通過單事件判準；事件帳本不在場由呼叫端判）。"""
    promote = {e["prop"]: e["seq"] for e in events
               if e["kind"] == "app.promote" and isinstance(e.get("prop"), str)}
    opens: dict = {}
    for e in events:
        if e["kind"] == "mea.open" and isinstance(e.get("prop"), str):
            opens.setdefault(e["prop"], e)
    out: list[Finding] = []
    seen_base: set = set()
    for e in events:
        schema = _schema(e) if e["kind"].startswith("mea.") else None
        sub = f"seq={e['seq']}"
        if not e["kind"].startswith("mea."):
            continue
        if schema is None:
            out.append(Finding(sub, "MEA-KEY-MISSING" if "report" not in e else "MEA-ENUM", "fail",
                               "report 缺或不在列舉內"))
            continue
        codes = _field_codes(e, _SPEC[schema])
        prop = e.get("prop")
        if schema != "check" and _PROP(prop):
            sp = promote.get(prop)
            if sp is None or sp >= e["seq"]:
                codes.append(("MEA-NOT-PROMOTED", f"{prop} 在本筆之前沒有 app.promote"))
            else:
                codes += _relations(e, schema, sp, opens.get(prop), seen_base)
        out += [Finding(sub, c, "fail", d) for c, d in codes]
    return out


def _relations(e: dict, schema: str, sp: int, opened: dict | None,
               seen_base: set) -> list[tuple[str, str]]:
    out = []
    if schema in ("mea.open", "baseline") and si_events._int(e.get("promote_seq"), 1) \
            and e["promote_seq"] != sp:
        out.append(("MEA-PROMOTE-SEQ", f"promote_seq 不等於 app.promote 的 seq {sp}"))
    if schema == "baseline":
        if e["prop"] in seen_base:
            out.append(("MEA-BASELINE-DUP", "同一 PROP 第二筆基線報告"))
        elif opened is not None and e["seq"] > opened["seq"]:
            out.append(("MEA-BASELINE-ORDER", "基線報告晚於 mea.open"))
        seen_base.add(e["prop"])
    w = opened.get("w_opp") if opened else None
    if schema == "mea.close" and si_events._int(w, 1) and si_events._int(e.get("n_opp"), 0):
        if e["n_opp"] > w or (e.get("result") == "clean" and e["n_opp"] != w):
            out.append(("MEA-CLOSE-N", f"n_opp={e['n_opp']} 與 w_opp={w} 不合"))
    return out
