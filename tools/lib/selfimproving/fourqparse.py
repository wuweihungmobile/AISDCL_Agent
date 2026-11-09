"""SelfImproving 四問答案檔：解析、判準、閘門與重放（TCS-SelfImproving-P5；PRD AC-SI-41-2～41-4、
43-1、43-2、44-4）。

能力類別 `ro`：只讀、純標準庫；答案檔落地與事件追加住 `fourq.py`（rw）。`validate` 是入帳時的完整
判準（格式、查詢重放、座標、引用、Q4 禁字）；`check` 重放只做格式（`replay=False`）。碼皆
`FOURQ-*`；格式合格不證明內容真實（P 型，PRD FG-N 誠實劃界）。
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import events as si_events
from . import fold as si_fold
from . import params as si_params
from . import refs as si_refs
from . import sources as si_sources
from .evspec import applicable, fourq_all, fourq_events, gate_codes, run_num  # noqa: F401
from .ledger import Finding

QS = ("此頂尖專家會做那些我沒有想到的事？", "在哪裡找到最前沿的資料與研究結果？",
      "使用哪些方法與工具？", "如何證明資料與改善結果是有正面影響與收斂的？")
TITLES = tuple(f"## Q{i} {q}" for i, q in enumerate(QS, 1))
HEAD = "# 四問審視 "
FILE_BYTES_MAX = 24576  # 模組常數：無先例、未校準（PRD AC-SI-41-2）
QUERIES_MAX = 24
Q = "docs/06_quality/"
CORPUS = (Q + "SelfImproving_Observation_Ledger.md",
          Q + "SelfImproving_Observation_Ledger_archive*.md",
          Q + "AutoSDD_Defect_Log.md", Q + "AutoSDD_Defect_Log_archive_*.md",
          Q + "AutoSDD_External_Blocked_Log.md", Q + "AutoSDD_Structural_Debt_Log.md",
          "docs/01_requirements/SelfImproving_PRD.md",
          "docs/05_development/SelfImproving_Operations_SOP.md")
_REQUIRED = (CORPUS[0], CORPUS[6], CORPUS[7])
_ITEM_RE = re.compile(r"^- (Q1-X\d+|Q1-\d+|Q2-F\d+|Q2-G\d+|Q3-\d+|Q4-\d+)｜(.+)$")
_QUERY_RE = re.compile(r"^「(.+)」＝(.+)$")
_REF_RE = re.compile(r"(?<![A-Za-z0-9])(OBS|ATT|PROP|DEC|APP|RUN|MEA)-SI-\d+")
_COORD_RE = re.compile(r"^(?P<p>[^\s:]+):(?P<a>\d+)(?:[-–]\d+)?$")
_SID_RE = re.compile(r"^sid (?P<u>\S+) line (?P<n>\d+)$")
_EXT_RE = re.compile(r"^外部：(.+)（src=([a-z0-9-]+)）$")
_TICK_RE = re.compile(r"`[^`]*`")
_URL_RE = re.compile(r"^https://[^/@\s?#]+(?:[/?#]\S*)?$")
_FIELDS = {"Q1": ("領域", "做法", "機制", "座標"), "Q2G": ("URL", "分級", "為何前沿", "更新頻率"),
           "Q2F": ("來源", "座標", "發現"), "Q3": ("對象", "方法", "工具"),
           "Q4": ("擬提案", "指標類別", "症狀定義", "反證", "收斂")}
LEAK_RES = (re.compile(r"n\s*=\s*\d"), re.compile(r"\d\s*%"), re.compile("基線|門檻|閾值"),
            re.compile(r"params\.json|W_N|W_MIN|W_EVT|W_OPP"))
GOODHART = ("觀察筆數", "OBS 筆數", "提案筆數", "採納率", "駁回率", "四問項數", "發現數", "零發現",
            "自評", "信心")
_NEG = ("不以", "不得以", "並非以")
Prob = tuple[str, str]


@dataclass
class Item:
    num: str
    kind: str  # Q1、Q1X、Q2F、Q2G、Q3、Q4
    fields: list[tuple[str, str]]
    lineno: int
    queries: list[tuple[str, str]] = field(default_factory=list)

    def get(self, label: str) -> str:
        return next((v for k, v in self.fields if k == label), "")


def width(text: str) -> int:
    from .card import width as card_width  # 延遲：card 的反解析不依賴本檔，避免載入環

    return card_width(text)


def _kind(num: str) -> str:
    return "Q1X" if num.startswith("Q1-X") else num[:2] if num[:2] in ("Q1", "Q3", "Q4") else (
        "Q2G" if "-G" in num else "Q2F")


def _labels_ok(kind: str, labels: list[str], zero: bool) -> bool:
    if kind == "Q1":
        return labels[:4] == list(_FIELDS["Q1"]) and len(labels) > 4 and set(labels[4:]) == {"查詢"}
    if kind == "Q1X":
        return len(labels) >= 3 and labels[0] == "考慮" and labels[-1] == "座標" and set(
            labels[1:-1]) == {"查詢"}
    return labels == (["免掃"] if zero else list(_FIELDS[kind]))


def _split(rest: str) -> list[tuple[str, str]]:
    out = []
    for seg in rest.split("｜"):
        label, sep, val = seg.partition("：")
        out.append((label.strip(), val.strip() if sep else ""))
    return out


def parse(text: str, run: str | None = None) -> tuple[list[Item], list[Prob]]:
    """（項目清單, 格式問題）；只判結構（首行、標題、項目行、編號、標籤、非空值）。"""
    probs: list[Prob] = []
    lines = text.split("\n")
    head = lines[0][len(HEAD):] if lines and lines[0].startswith(HEAD) else None
    if head is None or not si_events.RUN_RE.match(head) or (run and head != run):
        probs.append(("FOURQ-FORMAT", "首行須為「# 四問審視 <RUN>」且 RUN 與 --run 相同"))
    if [ln for ln in lines if ln.startswith("## ")] != list(TITLES):
        probs.append(("FOURQ-FORMAT", "二級標題須恰為四問逐字且依序"))
    items, sect, seen = [], 0, {}
    for no, ln in enumerate(lines[1:], 2):
        if ln.startswith("## "):
            sect += ln in TITLES[sect:sect + 1]
            continue
        if not ln.strip():
            continue
        m = _ITEM_RE.match(ln)
        if m is None or not m.group(1).startswith(f"Q{sect}-"):
            probs.append(("FOURQ-FORMAT", f"L{no} 不是合規項目行或不在其問之下"))
            continue
        num, kind = m.group(1), _kind(m.group(1))
        fields = _split(m.group(2))
        zero = num == "Q2-F0"
        if not _labels_ok(kind, [k for k, _ in fields], zero) or not all(v for _, v in fields):
            probs.append(("FOURQ-FORMAT", f"L{no} {num} 的標籤或值不合"))
            continue
        it = Item(num, kind, fields, no)
        it.queries = [q.groups() for k, v in fields if k == "查詢" and (q := _QUERY_RE.match(v))]
        if len(it.queries) != sum(1 for k, _ in fields if k == "查詢"):
            probs.append(("FOURQ-FORMAT", f"L{no} {num} 的查詢須為「…」＝狀態"))
        seen.setdefault(kind, []).append(int(num.rsplit("-", 1)[1].lstrip("XFG")))
        items.append(it)
    for kind, nums in seen.items():
        base = 0 if kind == "Q2F" and 0 in nums and len(nums) == 1 else 1
        if nums != list(range(base, base + len(nums))):
            probs.append(("FOURQ-FORMAT", f"{kind} 編號須自 1 連號（Q2-F0 只准單獨出現）"))
    if sum(len(i.queries) for i in items) > QUERIES_MAX:
        probs.append(("FOURQ-FORMAT", f"查詢總數超過 {QUERIES_MAX}"))
    return items, probs


def counts(items: list[Item]) -> dict:
    n = lambda *k: sum(1 for i in items if i.kind in k and i.num != "Q2-F0")  # noqa: E731
    return {"q1": n("Q1"), "q2": n("Q2F", "Q2G"), "q3": n("Q3"), "q4": n("Q4"),
            "gaps": n("Q2G"), "q1x": n("Q1X")}


def _outside_ticks(text: str) -> str:
    return _TICK_RE.sub("", text)


def leak_codes(text: str, keys=()) -> list[str]:
    """Q4／proof 禁字（`FOURQ-Q4-LEAK` 與 `PROOF-LEAK` 共用）：回命中的片段（空＝乾淨）。"""
    out, body = [], _outside_ticks(text)
    out += [m.group(0) for rx in LEAK_RES if (m := rx.search(body))]
    out += [k for k in sorted(keys)
            if re.search(rf"(?<![A-Za-z0-9_]){re.escape(k)}(?![A-Za-z0-9_])", body)]
    for term in GOODHART:
        for m in re.finditer(re.escape(term), body):
            if not body[:m.start()].endswith(_NEG):
                out.append(term)
                break
    return out


def _read(p: Path) -> str:
    return p.read_bytes().decode("utf-8", "replace").replace("\r\n", "\n")


def corpus_files(repo: Path) -> list[str]:
    """固定清單 `CORPUS` 解出的相對路徑（`fourq --corpus` 印的就是它）。"""
    out: list[str] = []
    for pat in CORPUS:
        if "*" not in pat:
            out += [pat] if (repo / pat).is_file() else []
            continue
        d, _, g = pat.rpartition("/")
        out += sorted(p.relative_to(repo).as_posix() for p in (repo / d).glob(g)
                      if p.is_file()) if (repo / d).is_dir() else []
    return out


def load_corpus(repo: Path) -> dict[str, list[str]] | None:
    files = corpus_files(repo)
    if any(r not in files for r in _REQUIRED):
        return None
    return {f: _read(repo / f).split("\n") for f in files}


def _coord_ok(c: str, repo: Path, obs: dict, defs: set, srcs: set | None, q: str | None,
              corp: dict | None) -> tuple[bool | None, str]:
    """（是否可定位, 說明）；`q` 非 None 時另要求所指那一行含 `q`（零項 Q1 的舉證）。"""
    m = _COORD_RE.match(c)
    if c.startswith("src="):
        sid = c[4:].split(" ")[0]
        return (None, sid) if srcs is None or sid not in srcs else (q is None, "")
    if _SID_RE.match(c):
        return si_events.valid_uuid(_SID_RE.match(c)["u"]) and q is None, ""
    if c in obs or c in defs:
        return q is None or any(q in ln and c in ln for ls in (corp or {}).values()
                                for ln in ls), ""
    if m and (repo / m["p"]).is_file():
        ls = _read(repo / m["p"]).split("\n")
        n = int(m["a"])
        return 1 <= n <= len(ls) and (q is None or q in ls[n - 1]), ""
    return False, ""


def _coords(it: Item, repo, obs, defs, srcs, q=None, corp=None) -> list[Prob]:
    segs = [s.strip() for s in it.get("座標").split("、") if s.strip()]
    got = [_coord_ok(s, repo, obs, defs, srcs, q, corp) for s in segs]
    out = [("FOURQ-SRC-UNKNOWN", f"{it.num} 的 src={g[1]} 不在來源表") for g in got if g[0] is None]
    if not any(g[0] for g in got) and not out:
        out.append(("FOURQ-COORD-MISSING", f"{it.num} 沒有可定位的座標"))
    return out


def _queries(items: list[Item], corp: dict[str, list[str]] | None) -> tuple[list[Prob], list[int]]:
    out: list[Prob] = []
    hits: list[int] = []
    for it in items:
        if it.kind not in ("Q1", "Q1X"):
            continue
        qs = [q for q, _ in it.queries]
        if it.kind == "Q1" and (len(qs) < 2 or len(set(qs)) != len(qs)):
            out.append(("FOURQ-QUERY-DUP", f"{it.num} 須有至少 2 條互異查詢"))
        for q, status in it.queries:
            w = width(q)
            if w < 4:
                out.append(("FOURQ-QUERY-TOO-SHORT", f"{it.num}「{q}」寬度 {w} < 4"))
            if w > 16:
                out.append(("FOURQ-QUERY-TOO-LONG", f"{it.num}「{q}」寬度 {w} > 16"))
            if it.kind == "Q1" and q not in it.get("做法") + "\n" + it.get("機制"):
                out.append(("FOURQ-QUERY-UNBOUND", f"{it.num}「{q}」不是做法或機制的子字串"))
            n = sum(1 for ls in (corp or {}).values() for ln in ls if q in ln)
            hits.append(min(n, 99))
            ok_status = (status == "命中") if it.kind == "Q1X" else (
                status == "零命中" or status.startswith("命中不涵蓋："))
            if not ok_status:
                out.append(("FOURQ-FORMAT", f"{it.num}「{q}」的狀態不合：{status}"))
            elif (status == "零命中" and n > 0) or (status != "零命中" and n == 0):
                out.append(("FOURQ-Q1-EMPTY-UNJUSTIFIED" if it.kind == "Q1X"
                            else "FOURQ-QUERY-MISMATCH", f"{it.num}「{q}」宣稱與重算不符（{n}）"))
    return out, hits


def _kind_probs(items: list[Item], repo: Path, srcs: set | None) -> list[Prob]:
    out: list[Prob] = []
    for it in items:
        if it.kind == "Q1" and len(it.get("領域")) > 20:
            out.append(("FOURQ-FORMAT", f"{it.num} 領域超過 20 字"))
        if it.kind == "Q2G":
            if not _URL_RE.match(it.get("URL")) or it.get("分級") not in ("T1", "T2"):
                out.append(("FOURQ-FORMAT", f"{it.num} 的 URL 須 https 無 userinfo、分級 T1／T2"))
        if it.kind == "Q3":
            for tool in (t.strip() for t in it.get("工具").split("、")):
                m = _EXT_RE.match(tool)
                if m and srcs is not None and m.group(2) in srcs:
                    continue
                if not m and tool and ".." not in tool and (repo / tool).exists():
                    continue
                out.append(("FOURQ-TOOL-UNKNOWN", f"{it.num} 的工具 {tool} 不存在或缺 src"))
        if it.kind == "Q4":
            cat, sym = it.get("指標類別"), it.get("症狀定義")
            cat_ok = bool(re.match(r"^(M1|M4|M5)(?![A-Za-z0-9])", cat)) or (
                cat.startswith("症狀：") and len(cat) > 3)
            if not cat_ok or not (_TICK_RE.search(sym) or _COORD_RE.search(sym)
                                  or si_events.OBS_ID_RE.match(sym)
                                  or si_events.DEF_ID_RE.match(sym)):
                out.append(("FOURQ-FORMAT", f"{it.num} 的指標類別或症狀定義不合"))
            bad = leak_codes("；".join(it.get(k) for k in _FIELDS["Q4"][1:]),
                             si_params.PARAM_SPECS)
            if bad:
                out.append(("FOURQ-Q4-LEAK", f"{it.num} 含禁字：{'、'.join(dict.fromkeys(bad))}"))
    return out


def validate(raw: bytes, repo: Path | None = None, *, run: str | None = None,
             events: list[dict] | None = None, items_max: int = 3, row_max: int = 700,
             replay: bool = True) -> tuple[list[Prob], list[Item], list[int]]:
    """（問題碼清單, 項目, 各查詢命中行數）；`replay=False`＝只判格式（`check` 重放）。"""
    probs: list[Prob] = []
    if len(raw) > FILE_BYTES_MAX:
        probs.append(("FOURQ-FILE-BYTES", f"整檔 {len(raw)} bytes > {FILE_BYTES_MAX}"))
    try:
        text = raw.decode("utf-8").replace("\r\n", "\n")
    except UnicodeDecodeError:
        return probs + [("FOURQ-FORMAT", "答案檔不是 UTF-8")], [], []
    if any((ord(c) < 32 and c != "\n") or 127 <= ord(c) <= 159 for c in text):
        probs.append(("FOURQ-FORMAT", "含控制字元"))
    probs += [("FOURQ-LINE", f"L{n} 超過 {row_max} bytes")
              for n, ln in enumerate(text.split("\n"), 1) if len(ln.encode("utf-8")) > row_max]
    items, fmt = parse(text, run)
    probs += fmt
    for it in items:
        line = text.split("\n")[it.lineno - 1]
        if it.kind in ("Q1", "Q2G") and "|" in _outside_ticks(line):
            probs.append(("FOURQ-PIPE", f"{it.num} 含 ASCII 管線字元"))
    c = counts(items)
    probs += [("FOURQ-ITEMS-OVER", f"{k} 項數 {c[k]} > {items_max}")
              for k in ("q1", "q1x", "q2", "q3", "q4") if c[k] > items_max]
    if not replay or repo is None:
        return probs, items, []
    srcs = si_sources.ids_or_none((repo / si_sources.SOURCES_REL).read_bytes()
                                  if (repo / si_sources.SOURCES_REL).is_file() else None)
    corp = load_corpus(repo)
    obs, defs = si_refs.obs_rows(repo), si_refs.def_ids(repo)
    if corp is None and any(i.queries for i in items):
        probs.append(("FOURQ-CORPUS-UNAVAILABLE", "固定語料缺必備檔，無法重放查詢"))
    qp, hits = _queries(items, corp) if corp is not None else ([], [])
    probs += qp + _kind_probs(items, repo, srcs)
    for it in items:
        if it.kind in ("Q1", "Q2F") and it.num != "Q2-F0":
            probs += _coords(it, repo, obs, defs, srcs)
        if it.kind == "Q1X" and corp is not None:
            probs += [("FOURQ-Q1-EMPTY-UNJUSTIFIED", d) for q, _ in it.queries
                      for _, d in _coords(it, repo, obs, defs, srcs, q, corp)]
    if c["q1"] == 0 and c["q1x"] < 2:
        probs.append(("FOURQ-Q1-EMPTY-UNJUSTIFIED", "零項 Q1 須至少 2 筆 Q1-X"))
    probs += _ref_probs(text, obs, events or [])
    return probs, items, hits


def _ref_probs(text: str, obs: dict, events: list[dict]) -> list[Prob]:
    ids = {"ATT": {e.get("id") for e in events if e.get("kind") == "attr"},
           "PROP": {e.get("id") for e in events if e.get("kind") == "prop"},
           "RUN": {e.get("run") for e in events if e.get("kind") == "run.open"},
           "DEC": {e.get("id") for e in events if e.get("kind") == "dec"},
           "APP": {e.get("id") for e in events if str(e.get("kind")).startswith("app.")},
           "OBS": set(obs), "MEA": set()}
    toks = dict.fromkeys(m.group(0) for m in _REF_RE.finditer(text))
    return [("FOURQ-REF-DANGLING", f"{t} 不存在") for t in toks
            if t not in ids[t.split("-")[0]]]


def sha_lf(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def loop_snapshot(repo: Path, params: dict, events: list[dict] | None) -> dict:
    """迴圈層快照（唯讀、不寫 `mea.*`；D-EQA-26）：M1、M4、M5a、M5b 的狀態、值、n、理由。"""
    from . import mea, meastat  # 延遲：量測碼只在入帳時載入
    from .git import Git
    from .status import MEASURE_KEYS

    def ne(why: str) -> dict:
        return {k: {"status": "NOT-EVALUABLE", "reason": why} for k in ("m1", "m4", "m5a", "m5b")}
    if events is None:
        return ne("carrier-not-established")
    if not set(MEASURE_KEYS) <= si_params.valid_keys(params):
        return ne("params-invalid")
    git = Git(repo)
    ctx = mea.build_ctx(repo, git, params, events)
    s = meastat.metrics(repo, git, ctx, carrier=True)["success"]
    return {"m1": s["m1"], "m4": s["m4"], "m5a": s["m5"]["main"], "m5b": s["m5"]["all"]}


def loop_text(snap: dict) -> str:
    def one(name: str, it: dict) -> str:
        if it["status"] == "read":
            n = it.get("n")
            body = f"read({format(it['value'], '.4g')}" + (f",n={n})" if n is not None else ")")
        else:
            body = f"NE({str(it.get('reason', ''))[:24]})"
        return f"{name}={body}".encode("ascii", "replace").decode("ascii")[:60]
    names = {"m1": "M1", "m4": "M4", "m5a": "M5a", "m5b": "M5b"}
    return ";".join(one(n, snap[k]) for k, n in names.items())[:256]


def _review_file(repo: Path, ev: dict, sub: str) -> list[Finding]:
    f = repo / si_events.fourq_path(ev["run"])
    if ev.get("path") != si_events.fourq_path(ev["run"]) or not f.is_file():
        return [Finding(sub, "FOURQ-FILE-MISSING", "fail", "答案檔缺")]
    raw = f.read_bytes()
    if sha_lf(raw) != ev.get("sha256"):
        return [Finding(sub, "FOURQ-SHA-MISMATCH", "fail", "答案檔 LF 雜湊與事件不符")]
    probs, items, _ = validate(raw, replay=False, items_max=10**6, run=ev["run"])
    if probs:
        return [Finding(sub, "FOURQ-FORMAT", "fail", probs[0][1])]
    c = counts(items)
    if any(c[k] != ev.get(k) for k in ("q1", "q2", "q3", "q4", "gaps")):
        return [Finding(sub, "FOURQ-COUNT-MISMATCH", "fail", "事件計數與重新解析不符")]
    return []


def check_findings(repo: Path, events: list[dict], params: dict) -> list[Finding]:
    """`events.research` 項追加（AC-SI-43-2）；重放只做格式。已關閉而無 fourq 的適用運轉記
    FOURQ-NOT-RUN（warn 級：不改 `check` 的 rc）。"""
    f, fq, out = si_fold.fold(events), fourq_all(events), []
    firsts, props = {}, {}
    for e in events:
        if e.get("kind") == "prop" and isinstance(e.get("run"), str):
            firsts.setdefault(e["run"], e["seq"])
            props.setdefault(e["run"], set()).add(e.get("proposer"))
    for run in sorted(set(f.runs) | set(fq) | set(firsts)):
        if not applicable(run, params):
            continue
        lst = fq.get(run, [])
        if len(lst) > 1:
            out.append(Finding(run, "FOURQ-MULTIPLE", "fail",
                               f"fourq 事件多於一筆 {[x[1] for x in lst]}"))
        if not lst:
            r = f.runs.get(run)
            if run in firsts:
                out.append(Finding(run, "FOURQ-MISSING", "fail", "有 prop 而無 fourq 事件"))
            elif r is not None and r.closed_seq is not None:
                out.append(Finding(run, "FOURQ-NOT-RUN", "warn", "[warn] 已關閉而無 fourq 事件"))
            continue
        kind, seq, ev = lst[0]
        rs = [s for s, _, r, _ in f.research_events if r == run]
        if not (rs and rs[0] < seq and (run not in firsts or seq < firsts[run])):
            out.append(Finding(run, "FOURQ-ORDER", "fail",
                               f"fourq seq={seq} 不在研究事件與第一筆 prop 之間"))
        if kind == "fourq.review":
            if ev.get("by") in props.get(run, set()):
                out.append(Finding(run, "FOURQ-IS-PROPOSER", "fail", "審視者等於同運轉提案者"))
            out += _review_file(repo, ev, run)
    return out


_PROOF_RE = re.compile(r"^指標類別：(.+?)；症狀定義：(.+?)；反證：(.+?)；收斂：(.+)$", re.DOTALL)


def body_codes(fields: dict, run: str, params: dict) -> list[Prob]:
    """適用運轉的本文須有 `method`、`proof`（AC-SI-43-3）；`proof` 只准四個定性子欄且過禁字判準。"""
    if not applicable(run, params):
        return []
    miss = [k for k in ("method", "proof") if not str(fields.get(k, "")).strip()]
    proof = str(fields.get("proof", "")).strip()
    if proof and not _PROOF_RE.match(proof):
        miss.append("proof 的四個定性子欄")
    out = [("BODY-FIELD-MISSING", "適用運轉的欄位表缺或不合：" + "、".join(miss))] if miss else []
    bad = leak_codes(proof, si_params.PARAM_SPECS) if proof else []
    if bad:
        out.append(("PROOF-LEAK", "proof 含禁字：" + "、".join(dict.fromkeys(bad))))
    return out


def gaps_open(repo: Path) -> dict:
    """處置 open 且症狀以「來源缺口候選：」起頭的 OBS 列數；帳本讀不到＝NOT-EVALUABLE（不是 0）。"""
    if si_refs.obs_ledger_text(repo) is None:
        return {"status": "NOT-EVALUABLE", "reason": "obs-ledger-unavailable"}
    n = sum(1 for r in si_refs.obs_rows(repo).values()
            if r.cells[3].strip().startswith("來源缺口候選：")
            and r.cells[7].strip().lower().startswith("open"))
    return {"status": "read", "count": n}


def status_value(repo: Path, events: list[dict] | None, params: dict) -> dict:
    """`status.fourq`（AC-SI-44-4；與 `export` 同一函式）。"""
    gaps = gaps_open(repo)
    if events is None:
        return {"status": "NOT-EVALUABLE", "reason": "carrier-not-established", "last_run": None,
                "state": "none", "loop": None, "gaps_open": gaps, "missing_runs": None}
    f, fq = si_fold.fold(events), fourq_events(events)
    runs = sorted((n, r) for r in f.runs if (n := run_num(r)) is not None)
    last = runs[-1][1] if runs else None
    miss = [r for _, r in runs if applicable(r, params) and f.runs[r].closed_seq is not None
            and r not in fq]
    if last is None:
        state = "none"
    elif last in fq:
        state = "review" if fq[last][0] == "fourq.review" else "skip"
    else:
        state = ("exempt" if not applicable(last, params) else
                 "missing" if f.runs[last].closed_seq is not None else "none")
    loops = [e["loop"] for e in events if e.get("kind") == "fourq.review"]
    return {"status": "read", "last_run": last, "state": state, "gaps_open": gaps,
            "loop": loops[-1] if loops else None, "missing_runs": len(miss)}


def status_line(v: dict) -> str:
    g = v["gaps_open"]
    gt = str(g["count"]) if g["status"] == "read" else f"NOT-EVALUABLE（{g['reason']}）"
    if v["status"] != "read":
        return f"fourq: NOT-EVALUABLE（{v['reason']}）gaps_open={gt}"
    return (f"fourq: state={v['state']} last_run={v['last_run']} missing_runs={v['missing_runs']} "
            f"gaps_open={gt} loop={v['loop']}")
