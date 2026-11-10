"""SelfImproving P6 事件欄位表（`research.registry`、`backtest.result`、`research.scan` 新欄位）。

能力類別 `ro`：純資料與純判準函式；`evspec.py` 只 import 並併表（零行為變更）。欄位與最壞行長的
唯一規格＝PRD §9.2（TCS-SelfImproving-P6 AT-645-7-*、AT-630-8-4）。另含 `PROOF-BACKTEST` 的純函式
`proof_backtest_codes`：提案的 `proof` 不得拿回測分數當成效（反 Goodhart，AC-SI-46-8）。
"""

from __future__ import annotations

import re

from .evspec import (
    _SHA,
    ACCOUNT_RE,
    KEY_ID_RE,
    _int,
    _Issues,
    _re,
    valid_t,
    valid_uuid,
)

_BATCH_RE = re.compile(r"^BT-\d{3,6}$")
_SEED_MAX = 2**31 - 1
ARTICLES_MAX = 99
_PM = lambda v: _int(v, 0) and v <= 1000  # noqa: E731  # 千分比
_N10 = lambda v: _int(v, 0) and v <= 10  # noqa: E731


def _k(v) -> bool:
    return _int(v, 1) and v <= 10


SPEC: dict[str, dict] = {
    "research.registry": {
        "audit_ref": valid_uuid, "audit_sha256": _SHA, "key_id": _re(KEY_ID_RE),
        "decider": _re(ACCOUNT_RE), "carrier": lambda v: v == "console", "audit_time": valid_t,
        "registry_sha256": _SHA, "hosts_n": _int, "watch_n": _int, "watch_on": _int,
        "changed": lambda v: isinstance(v, bool),
    },
    "backtest.result": {
        "batch": _re(_BATCH_RE), "cases_version": lambda v: _int(v, 1), "cases_sha256": _SHA,
        "seed": lambda v: _int(v, 0) and v <= _SEED_MAX, "k": _k, "n": _N10,
        "unanswered": _N10, "contaminated": _N10, "hit1": _N10, "hit3": _N10, "hit5": _N10,
        "prec_pm": _PM, "rec_pm": _PM, "ledger_line": lambda v: _int(v, 1), "row_sha256": _SHA,
    },
}
# `research.scan` 的新增鍵（舊鍵 `run`／`sources`／`fetched_at` 與舊格式 `sources_sha256` 不動）
SCAN_EXTRA: dict = {
    "registry_seq": lambda v: _int(v, 1), "registry_sha256": _SHA,
    "articles_n": lambda v: _int(v, 0) and v <= ARTICLES_MAX, "articles_sha256": _SHA,
}
# 全部選填（是否必備由 `scan_rules` 的條件規則定）
SCAN_OPTIONAL = {"sources_sha256", "registry_seq", "registry_sha256", "articles_n",
                 "articles_sha256"}
_MISS, _TYPE = "EVENT-KEY-MISSING", "EVENT-TYPE"


def scan_rules(obj: dict, body: dict) -> _Issues:
    """`research.scan`：舊格式（`sources_sha256`）與新格式（`registry_seq`＋`registry_sha256`）
    二擇一且恰一；`articles_n`／`articles_sha256` 成對且只准與新格式同現。"""
    out: _Issues = []
    old = "sources_sha256" in body
    reg = {"registry_seq", "registry_sha256"} & set(body)
    if old and reg:
        out.append((_TYPE, "research.scan 的 sources_sha256 與 registry_* 須恰有一種"))
    elif not old and not reg:
        out.append((_MISS, "research.scan 缺 sources_sha256 或 registry_seq／registry_sha256"))
    elif reg and len(reg) < 2:
        out.append((_MISS, "research.scan 的 registry_seq 與 registry_sha256 須成對"))
    arts = {"articles_n", "articles_sha256"} & set(body)
    if arts and len(arts) < 2:
        out.append((_MISS, "research.scan 的 articles_n 與 articles_sha256 須成對"))
    if arts and old:
        out.append((_TYPE, "research.scan 的 articles_* 只准與新格式同現"))
    return out


def registry_rules(obj: dict) -> _Issues:
    out: _Issues = []
    n, on = obj.get("watch_n"), obj.get("watch_on")
    if _int(n) and _int(on) and on > n:
        out.append((_TYPE, "research.registry 的 watch_on 不得大於 watch_n"))
    return out


def backtest_rules(obj: dict) -> _Issues:
    out: _Issues = []
    h1, h3, h5, n = (obj.get(k) for k in ("hit1", "hit3", "hit5", "n"))
    if all(_int(v) for v in (h1, h3, h5, n)) and not h1 <= h3 <= h5 <= n:
        out.append((_TYPE, "backtest.result 須 hit1 ≤ hit3 ≤ hit5 ≤ n"))
    return out


def rules(kind: str, obj: dict, body: dict) -> _Issues:
    """P6 三種事件的條件規則（`events._conditional` 呼叫；碼皆 EVENT-TYPE／EVENT-KEY-MISSING）。"""
    if kind == "research.scan":
        return scan_rules(obj, body)
    if kind == "research.registry":
        return registry_rules(obj)
    return backtest_rules(obj) if kind == "backtest.result" else []


_PROOF_RE = re.compile(r"回測|backtest", re.IGNORECASE)


def proof_backtest_codes(text: str) -> list[str]:
    """`proof` 含「回測」或 `backtest`（大小寫不拘）＝回 `["PROOF-BACKTEST"]`，否則空串列。"""
    return ["PROOF-BACKTEST"] if isinstance(text, str) and _PROOF_RE.search(text) else []
