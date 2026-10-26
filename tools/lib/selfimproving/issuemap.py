"""SelfImproving 議題中心的顯示層對照表（TCS-IssueCenter R-IC-01～R-IC-08；PRD §4）。

純函式、純標準庫：七狀態、八結果、四來源、四嚴重度、事件動作、決定動詞、通道、`problems` 碼、
`ne` 理由與「下一步」句型的唯一住所，其他檔不得持有第二份（`issues*.py` 只呼叫本檔）。機器值查無
對應回 `None`，由呼叫端 fail-loud 顯示「未歸類」；本檔不替表外值猜歸類。`closure_problems` 把本表
的鍵集合與上游（`events`、`rows`、`defs`）雙向比對：上游新增值而本表沒登記就回非空（測試紅）。
"""

from __future__ import annotations

import re

from . import defs, events, rows

_STATUS_ROWS = (  # (名稱, 專屬分頁, 可排優先順序, 意思)；順序固定
    ("候選", None, False, "剛記下來，還沒成立，不會成為待辦"),
    ("待您決定", "待您決定", True,
     "等掌舵者按一下：決定提案（含復發後是否回滾），或裁決一個決定類觀察；"
     "若決定不回滾，目前沒有動詞可消去，會留在此狀態"),
    ("待解", "待處理", True, "已成立的缺陷或觀察，還沒人在處理"),
    ("進行中", "待處理", True, "有人在做：修復、沙盒、驗證、修訂、回滾"),
    ("觀察中", "待處理", False, "已採納，量測窗內看會不會復發"),
    ("延後", None, False,
     "刻意先放著，寫明「什麼情況再回來」；下一步欄是帳本原文節錄，可能含英文片段"),
    ("已完成", "已完成", False, "結案；「結果」欄寫明怎麼結的"),
)
_RESULT_ROWS = (
    ("已修復", "問題已改好"), ("已採納", "提案已晉升並走完量測窗、窗內未復發"),
    ("已否決", "決定不做（提案被否決、缺陷不修）"), ("已退役", "觀察列不再相關（附依據座標）"),
    ("已裁決", "由掌舵者或主控裁決結案、不改程式"),
    ("已轉交", "已轉到別處追蹤：觀察轉成缺陷或提案、提案轉交其他通道；「下一步」寫明去向"),
    ("已合併", "併入另一筆觀察"), ("已回滾", "提案採納後被回滾"),
)
_SOURCE_ROWS = (  # 順位序：先中者定案
    ("使用者提案", "您自己提的（含經 Console 簽章入帳的）"),
    ("系統缺陷", "測試、CI、體檢或主控發現的缺陷"),
    ("研究提案", "研究掃描外部來源產生；外部內容須另有內部佐證才能成提案"),
    ("系統改善", "流程、工具、文件的改善"),
)
_SEVERITY_ROWS = (
    ("緊急", "各帳本的最高級（缺陷帳本的 P0 與 P1、觀察帳本的 P1），原值在詳情的原列區"),
    ("高", "次高級（P2）"), ("中", "中級（P3）"), ("低", "最低級（P4）"),
)
_PROBLEM_ROWS = (
    ("ROW-ARITY", "帳本列欄數不符（觀察列另含 ID 格式不合），該列不成議題；"
                  "編號或行號過大而無法編入游標者同樣不成議題"),
    ("ID-DUP", "同編號多列、只收第一列"), ("UNMAPPED", "帳本值不在對照表"),
    ("EVENT-PARSE", "事件帳本有讀不懂的行"), ("EVENT-UNSOUND", "事件帳本有不合格事件、已略過"),
)
_NE_ROWS = (
    ("OBS-LEDGER-UNAVAILABLE", "觀察帳本讀不到"), ("DEFECT-LEDGER-UNAVAILABLE", "缺陷帳本讀不到"),
    ("SIBLING-LEDGER-UNAVAILABLE", "姊妹軌檔讀不到"),
    ("EVENT-LEDGER-UNAVAILABLE", "事件帳本讀不到"),
    ("SEVERITY-UNAVAILABLE", "嚴重度量不到"), ("TIME-UNPARSEABLE", "時間欄解不出"),
    ("CARD-UNAVAILABLE", "提案卡面建不出"), ("MEASURE-UNAVAILABLE", "量測窗進度量不到"),
    ("git-unavailable", "git 取不到版本"),
)
EVENT_LABELS = {
    "run.open": "開運轉", "run.close": "關運轉", "research.scan": "研究掃描",
    "research.skip": "免掃", "attr": "歸因", "attr.confirm": "確認歸因", "attr.reject": "駁回歸因",
    "prop": "提案",
    "card": "出卡", "dec": "決定", "heldout.freeze": "凍結評估集", "app.sandbox": "沙盒套用",
    "app.verify": "驗證", "app.promote": "晉升", "app.rollback": "回滾", "mea.open": "開量測窗",
    "mea.close": "關量測窗", "mea.amend": "更正量測", "mea.report": "量測報告",
    "obs.add": "新增觀察", "obs.close": "關閉觀察",
}
DKIND_LABELS = {
    "approve": "核准", "reject": "否決", "return": "退回", "promote": "晉升", "rollback": "回滾",
    "decline-promote": "不晉升", "unblock": "解除冷卻", "resume": "恢復運轉",
    "ack-handoff": "確認轉交",
}
ROUTE_LABELS = {"DEF": "缺陷帳本", "R": "跨平台輪", "T1": "掌舵者指令", "PRD": "規格修訂"}
LEDGER_LABELS = {"obs": "觀察帳本", "def": "缺陷帳本", "event": "事件帳本"}
UPDATED_AT_NOTE = "已完成議題的日期是帳本上的「最後已知動靜」，不是結案日（帳本沒有記結案時間）"
NEXT_STEPS = {  # PRD §5.2 十九情境各一句；`{…}` 為代入值
    "N01": "等歸因確認（歸因者提出、審查者確認），或由掌舵者簽核成立",
    "N02": "等掌舵者決定：核准、否決或退回",
    "N03": "等掌舵者決定：轉交、不轉交或退回（通道：{channel}）",
    "N04": "驗證已有結果，等掌舵者決定（可選的決定依驗證結果而定，見「決定」對話框）",
    "N05": "量測窗內復發，等您決定是否回滾（目前只有「回滾」動詞）",
    "N06": "等掌舵者決定：在此關閉並寫下裁決", "N07": "尚未分流，等待修復",
    "N08": "已成立，尚無人接手", "N09": "已分流待修", "N10": "已核准，等沙盒套用",
    "N11": "已退回，等提案者修訂（第 {rev} 版）", "N12": "沙盒已套用，等驗證",
    "N13": "已決定回滾，等執行回滾", "N14": "已晉升，等量測窗開啟",
    "N15": "量測窗 {n_opp}／{w_opp}", "N15u": "量測窗進度量不到",
    "N16": "等再開症狀出現：{excerpt}", "N17": "等解鎖條件：{unlock}（最近複查 {review}）",
    "N18": "已結案（{result}）", "N18t": "已結案（{result}），見 {target}",
    "N18h": "已結案（{result}），通道：{channel}", "N18r": "已結案（{result}）{cool}",
    "N19": "帳本值不在對照表內，請查原列",
}
COOL_TEXT = {"cooling": "；同型冷卻中", "cooled": "；冷卻已解除"}
EMPTY_EXCERPT = "（帳本未寫明）"
ORPHAN_TITLE = "（主帳本列已歸檔）"
CARD_TITLE = "（提案 {id}：卡面量不到）"
PROP_RAW_LABELS = ("提案卡", "狀態", "路由", "類別", "動作", "修訂", "摘要碼", "來源項目")
DEC_PREFIX = "決定："
STATUSES = tuple(r[0] for r in _STATUS_ROWS)
RESULTS = tuple(r[0] for r in _RESULT_ROWS)
SOURCES = tuple(r[0] for r in _SOURCE_ROWS)
SEVERITIES = tuple(r[0] for r in _SEVERITY_ROWS)
DEF_SEVERITIES = ("P0", "P1", "P2", "P3", "P4")
PROBLEM_CODES = tuple(r[0] for r in _PROBLEM_ROWS)
NE_REASONS = tuple(r[0] for r in _NE_ROWS)
TABS = ("待處理", "待您決定", "已完成")  # 摘要三格；「待處理」同時是篩選別名
TAB_MEMBERS = {t: tuple(r[0] for r in _STATUS_ROWS if r[1] == t) for t in TABS}
PENDING = TAB_MEMBERS[TABS[0]]
PENDING_VIEW = (*PENDING, "待您決定", TABS[0])  # 文字表頁內顯示序第一條（無順位）適用的篩選值
DECIDE_STATUS = "待您決定"
_RANKABLE = frozenset(r[0] for r in _STATUS_ROWS if r[2])
UNMAPPED = "未歸類"
MARK = f"{UNMAPPED}："
# 機器值 → (狀態, 結果, 下一步情境碼)；帶條件的鍵（未結觀察與提案的五個態）由函式判
_OBS = {
    "deferred": ("延後", None, "N16"), "decided": ("已完成", "已裁決", "N18"),
    "retired": ("已完成", "已退役", "N18"), "fixed@": ("已完成", "已修復", "N18"),
    "merged@": ("已完成", "已合併", "N18"), "DEF-": ("已完成", "已轉交", "N18t"),
    "proposed@": ("已完成", "已轉交", "N18t"),
}
_OBS_KEYS = frozenset(_OBS) | {"open"}
_DEF = {
    "open": ("待解", None, "N07"), "routed": ("進行中", None, "N09"),
    "fixed": ("已完成", "已修復", "N18"), "wontfix": ("已完成", "已否決", "N18"),
    "closed-by-decision": ("已完成", "已裁決", "N18"),
}
_PROP = {
    "verified": ("待您決定", None, "N04"), "approved": ("進行中", None, "N10"),
    "returned": ("進行中", None, "N11"), "sandboxed": ("進行中", None, "N12"),
    "rejected": ("已完成", "已否決", "N18r"), "handed-off": ("已完成", "已轉交", "N18h"),
}
_PROP_KEYS = frozenset(_PROP) | {"proposed", "promoted", "measuring", "closed"}
_CATEGORIES = frozenset({"process", "bug", "tooling", "doc", "decision"})
_SEV = {"P0": 0, "P1": 0, "P2": 1, "P3": 2, "P4": 3}  # → SEVERITIES 的索引
_OBS_SEV = ("P1", "P2", "P3", "P4")
_DEF_SEV_RE = re.compile(r"^[\s*_]*(P[0-4])(?!\d)")
_PREFIX_KEYS = ("fixed@", "merged@", "proposed@", "DEF-")


def unmapped(raw: str, limit: int = 80) -> str:
    """「未歸類：<原值>」；原值超過 `limit` 個 code point 取前 `limit` 個加「…」（不計入）。"""
    return MARK + (raw if len(raw) <= limit else raw[:limit] + "…")


def is_unmapped(text: str | None) -> bool:
    return isinstance(text, str) and text.startswith(MARK)


def obs_key(token: str | None) -> str | None:
    """`rows.disp_token` 的值 → 對照表鍵（`fixed@<sha>` 等以前綴為鍵）；表外回 None。"""
    key = next((p for p in _PREFIX_KEYS if token and token.startswith(p)), token)
    return key if key in _OBS_KEYS else None


def _prop(state, window, decided, pending, consumed, route):
    if state in ("promoted", "measuring"):
        if pending >= 1:
            return ("進行中", None, "N13")
        return ("觀察中", None, "N14" if state == "promoted" else "N15")
    if state == "proposed":
        return ("待您決定", None, "N03" if str(route).startswith("handoff:") else "N02")
    if state != "closed":
        return _PROP.get(state)
    if window == "rolled-back" or consumed >= 1:  # 判序依 R-IC-19：已回滾先於量不到
        return ("已完成", "已回滾", "N18")
    if window not in ("clean", "recurred"):
        return ("已完成", unmapped(state), "N19")
    if pending >= 1:
        return ("進行中", None, "N13")
    if decided == 0 and window == "recurred":
        return ("待您決定", None, "N05")
    return ("已完成", "已採納", "N18")


def classify(kind: str, key: str | None, **cond):
    """(狀態, 結果, 下一步情境碼) 或 None（表外）。`cond` 關鍵字：觀察 `decision`、`established`；
    缺陷 `sibling`；提案 `route`、`window`（首窗生效結果）、`decided`、`pending`、`consumed`。"""
    if kind == "obs":
        key = obs_key(key)
        if key != "open":
            return _OBS.get(key)
        if cond.get("decision"):
            return ("待您決定", None, "N06")
        return ("待解", None, "N08") if cond.get("established") else ("候選", None, "N01")
    if kind == "def":
        return ("延後", None, "N17") if cond.get("sibling") else _DEF.get(key)
    if kind == "prop":
        return _prop(key, cond.get("window"), cond.get("decided", 0), cond.get("pending", 0),
                     cond.get("consumed", 0), cond.get("route", "loop"))
    return None


def status_of(kind: str, key: str | None, **cond):
    """(狀態, 結果) 或 None（表外）；`kind`＝obs／def／prop，條件同 `classify`。"""
    hit = classify(kind, key, **cond)
    return None if hit is None else hit[:2]


def severity_of(group: str, raw: str):
    """(名稱, rank) 或 None（表外）。觀察組＝P1～P4 全等；缺陷組＝欄首（略過空白、`*`、`_`）
    的 P0～P4，其後不得再接數字（P10 是表外值），後綴說明不看。"""
    if group == "def":
        m = _DEF_SEV_RE.match(raw or "")
        key = m.group(1) if m else None
    else:
        key = raw if raw in _OBS_SEV else None
    return None if key is None else (SEVERITIES[_SEV[key]], _SEV[key] + 1)


def mark_of(marks: dict, name: str) -> str:
    """`rows.row_marks` 結果中某鍵的值（沒有該鍵回空字串）。"""
    return marks.get(name, ("", False))[0]


def user_marked(marks: dict) -> bool:
    """標記含 `來源=人` 或 `carrier=console`：掌舵者親自入帳（路徑 B；來源順位第一）。"""
    return mark_of(marks, "來源") == "人" or mark_of(marks, "carrier") == "console"


def source_of(marks: dict, category: str, *, is_def: bool = False) -> str | None:
    """四來源之一（R-IC-16 的觀察列順位）；分類表外且無標記可判時回 None。"""
    if is_def:
        return SOURCES[1]
    if user_marked(marks):
        return SOURCES[0]
    if category == "bug":
        return SOURCES[1]
    if mark_of(marks, "回報者") == "研究者":
        return SOURCES[2]
    return SOURCES[3] if category in _CATEGORIES else None


def rankable(status: str) -> bool:
    return status in _RANKABLE


def action_of(kind: str, status: str) -> str | None:
    """畫面依它決定按鈕：待您決定的提案＝decide-proposal、觀察＝close-observation，其餘 None。"""
    if status != DECIDE_STATUS:
        return None
    return {"prop": "decide-proposal", "obs": "close-observation"}.get(kind)


def event_label(kind: str) -> str | None:
    return EVENT_LABELS.get(kind)


def dkind_label(dkind: str) -> str | None:
    return DKIND_LABELS.get(dkind)


def route_label(route: str) -> str | None:
    """通道（`handoff:` 後綴；帶前綴的完整路由也收）的中文；`loop` 與表外回 None。"""
    return ROUTE_LABELS.get(route.removeprefix("handoff:"))


def labels() -> dict:
    """legend 的全部中文（每次回新物件）；`issues` 的 legend 唯一來源。"""
    return {
        "statuses": [{"name": n, "meaning": m, "tab": t, "rankable": r}
                     for n, t, r, m in _STATUS_ROWS],
        "results": [{"name": n, "meaning": m} for n, m in _RESULT_ROWS],
        "sources": [{"name": n, "meaning": m} for n, m in _SOURCE_ROWS],
        "severities": [{"name": n, "rank": i, "meaning": m}
                       for i, (n, m) in enumerate(_SEVERITY_ROWS, start=1)],
        "problem_codes": [{"code": c, "meaning": m} for c, m in _PROBLEM_ROWS],
        "ne_reasons": [{"reason": r, "meaning": m} for r, m in _NE_ROWS],
        "unmapped_label": UNMAPPED,
        "updated_at_note": UPDATED_AT_NOTE,
    }


def _first_group_branches(pattern: str) -> list[str]:
    """正規式第一個括號群組內、最外層以 `|` 分開的分支原文（不改上游，只解析 pattern 字串）。"""
    out, buf, depth, i = [], "", 1, pattern.index("(") + 1
    while i < len(pattern):
        ch = pattern[i]
        if ch == "\\":
            buf, i = buf + pattern[i:i + 2], i + 2
            continue
        depth += (ch == "(") - (ch == ")")
        if depth == 0:
            break
        if ch == "|" and depth == 1:
            out, buf = [*out, buf], ""
        else:
            buf += ch
        i += 1
    return [*out, buf]


def real_upstream() -> dict[str, set[str]]:
    """上游單一真相的現況快照（`closure_problems` 預設比對對象；測試以它派生合成變體）。"""
    return {
        "prop_states": set(events.PROP_STATES), "kinds": set(events.KINDS),
        "dkinds": set(events.DKINDS), "categories": set(rows.CATEGORIES),
        "routes": {r.split(":", 1)[1] for r in events.ROUTES if r.startswith("handoff:")},
        "severities": set(rows.SEVERITIES), "def_labels": set(defs._STATUS_KEYWORDS),
        "disp_tokens": {re.sub(r"\\S\+\??$", "", b)
                        for b in _first_group_branches(rows.DISP_TOKEN_RE.pattern)},
    }


def real_table() -> dict[str, set[str]]:
    """本表各維度的鍵集合（與 `real_upstream` 同形）。"""
    return {
        "prop_states": set(_PROP_KEYS), "kinds": set(EVENT_LABELS), "dkinds": set(DKIND_LABELS),
        "categories": set(_CATEGORIES), "routes": set(ROUTE_LABELS), "severities": set(_OBS_SEV),
        "def_labels": set(_DEF), "disp_tokens": set(_OBS_KEYS),
    }


def closure_problems(upstream: dict | None = None, table: dict | None = None) -> list[str]:
    """雙向封閉鎖：每個維度的上游鍵集合與本表鍵集合須相等（空串列＝封閉）；`upstream`、`table`
    預設取真值，測試注入合成值自證紅綠。"""
    up = real_upstream() if upstream is None else upstream
    tb = real_table() if table is None else table
    out = []
    for dim in sorted(set(up) | set(tb)):
        have, want = set(tb.get(dim, ())), set(up.get(dim, ()))
        out += [f"{dim}：表缺「{v}」（上游有而表無）" for v in sorted(want - have)]
        out += [f"{dim}：表多「{v}」（上游無此值）" for v in sorted(have - want)]
    return out
