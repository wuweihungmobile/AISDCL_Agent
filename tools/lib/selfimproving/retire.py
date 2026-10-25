"""SelfImproving 退役欄位與退役目標判準（TCS-P3 R127）。

能力類別 `ro`、純函式：由 `props` 的階段一（本文欄位，與 `BODY-FIELD-*` 一併收集）與
階段二（政策與狀態）呼叫。任何 `action` 的 `prop-new`／`prop-revise` 本文欄位表都須有
`retire_when`、`reopen_symptom` 兩鍵且值非空、一句、不含輪號／日期／待排程；
`action=retire` 的目標須為已採納工件（在役）。本模組不判 patch 能否套用（由 `verify` 判）、
不呼叫任何 SDD 碼。
"""

from __future__ import annotations

import re

KEYS = ("retire_when", "reopen_symptom")
_ROUND_RE = re.compile(r"(?<![A-Za-z0-9])R\d+|improving_\d+")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_OUT_OF_SERVICE = ("retire", "delete")
Code = tuple[str, str]


def form_problems(text: str) -> list[Code]:
    """R127 (b)：非空值的形態成因（空值回空清單，由 `RETIRE-FIELD-MISSING` 判、不雙報）。"""
    value = text.strip()
    if not value:
        return []
    causes = [name for name, bad in (
        ("換行", "\n" in value or "\r" in value), ("輪號", bool(_ROUND_RE.search(value))),
        ("日期", bool(_DATE_RE.search(value))), ("待排程", "待排程" in value)) if bad]
    return [("RETIRE-FIELD-FORM", cause) for cause in causes]


def field_codes(fields: dict, cls: str) -> list[Code]:
    """R127 (a)(b)：欄位表的缺欄與形態碼；M 類的 `retire_when` 缺或空由 `M-FIELD-MISSING` 判。"""
    out: list[Code] = []
    missing = [k for k in KEYS if not fields.get(k, "").strip()
               and not (cls == "M" and k == "retire_when")]
    if missing:
        out.append(("RETIRE-FIELD-MISSING", "欄位表缺或空：" + "、".join(missing)))
    for key in KEYS:
        out += [(code, f"{key}：{cause}") for code, cause in form_problems(fields.get(key, ""))]
    return out


def _norm(path: str) -> str:
    return path.replace("\\", "/").casefold()


def in_service(folded, events: list, path: str) -> bool:
    """R127 (c)：存在 promoted 且未被 `app.rollback` 的 PROP 其 target 含 `path`，且其中最近晉升者
    （`app.promote` 的 seq 最大）的 `action` 不是 `retire`／`delete`。"""
    rolled = {e.get("prop") for e in events if e.get("kind") == "app.rollback"}
    owners = [p for p in folded.props.values() if p.promote_seq is not None
              and p.id not in rolled and path in {_norm(t) for t in p.target}]
    return bool(owners) and max(owners, key=lambda p: p.promote_seq).action not in _OUT_OF_SERVICE


def target_codes(c) -> list[Code]:
    """R127 (c)：`action=retire` 的目標須皆在役，否則 `RETIRE-TARGET-NOT-ADOPTED`。"""
    if c.action != "retire":
        return []
    bad = sorted({t for t in c.targets if not in_service(c.folded, c.events, _norm(t))})
    return [("RETIRE-TARGET-NOT-ADOPTED", "未採納的退役目標：" + "、".join(bad))] if bad else []
