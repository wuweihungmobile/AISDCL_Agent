"""SelfImproving 反事實回測的答案判準、評分、洩漏稽核、結果帳本對帳與 status 值（FR-SI-46；P6）。

能力類別 `ro`：純函式（評分一律以集合運算與 `fractions.Fraction` 精確算術，不用浮點、不用 LLM 當
評審）；唯一的 I/O 是只讀的逐字稿與帳本。洩漏稽核是**偵測型、事後、fail-closed**：逐字稿位置沿
`transcript.py` 的子代理逐字稿掃描器，佈局不符一律落入 `transcript-missing`（不入彙總），
不靜默放行。
"""

from __future__ import annotations

import json
import os
import re
from fractions import Fraction
from pathlib import Path

from . import btcases, transcript
from .ledger import Finding

ANSWER_KEYS = {"case", "suspects", "hypothesis", "direction"}
AGENT_ID_RE = re.compile(r"^[0-9a-f]{8,32}$")
ALLOWED_TOOLS = ("Read", "Grep", "Glob")
# WHY：harness 2.1.322 的子代理交卷一律經 `SubagentHandback` 工具；它不帶檔案路徑、不讀檔，
# 故不算洩漏。路徑判準（Read／Grep／Glob 必須在快照內）一字不放寬，其餘工具名仍判不允許。
HARNESS_HANDBACK_TOOL = "SubagentHandback"
_TEXT_MAX = 400


def _ctrl(text: str) -> bool:
    return any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in text)


def _literal_path_ok(rel) -> bool:
    """suspect 的字面判準（沿 `evspec.safe_path`、不碰檔案系統）：相對、無 `..`、無磁碟代號。"""
    return (isinstance(rel, str) and bool(rel) and rel[0] not in "/\\"
            and not re.match(r"^[A-Za-z]:", rel) and ".." not in re.split(r"[/\\]", rel)
            and not _ctrl(rel))


def answer_codes(obj, slot: str) -> list[tuple[str, str]]:
    """答案檔格式（AC-SI-46-3）：鍵恰四個、`case`＝槽位、suspects 1～`BT_TOP` 個相對路徑、
    `hypothesis`／`direction` 非空且 ≤400 字元無控制字元。"""
    bad = ("BT-ANSWER-FORMAT", "答案檔格式不符")
    if not isinstance(obj, dict) or set(obj) != ANSWER_KEYS or obj["case"] != slot:
        return [bad]
    sus = obj["suspects"]
    if not (isinstance(sus, list) and 1 <= len(sus) <= btcases.BT_TOP
            and all(_literal_path_ok(s) for s in sus)):
        return [bad]
    texts = (obj["hypothesis"], obj["direction"])
    if not all(isinstance(t, str) and t.strip() and len(t) <= _TEXT_MAX and not _ctrl(t)
               for t in texts):
        return [bad]
    return []


def norm_path(p: str) -> str:
    p = p.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p.casefold()


def score_case(changed_files: list[str], suspects: list[str]) -> dict:
    """單案評分：suspects 依出現序去重並正規化；`rank` 為第一個命中者的 1 起算名次（無命中＝0）。"""
    truth = {norm_path(f) for f in changed_files}
    seen: list[str] = []
    for s in suspects:
        n = norm_path(s)
        if n not in seen:
            seen.append(n)
    hits = [n for n in seen if n in truth]
    rank = next((i for i, n in enumerate(seen, 1) if n in truth), 0)
    return {"rank": rank, "hit1": int(0 < rank <= 1), "hit3": int(0 < rank <= 3),
            "hit5": int(0 < rank <= 5), "precision": Fraction(len(hits), len(seen)),
            "recall": Fraction(len(hits), len(truth))}


def _pm(value: Fraction) -> int:
    """千分比，精確算術後四捨五入（恰 .5 進位）。"""
    return (value * 1000 * 2 + 1) // 2


def aggregate(scored: list[dict]) -> dict:
    """彙總只算 `ok` 案；`n=0` 時分數欄為 0 並標 `n0`。"""
    n = len(scored)
    out = {"n": n, "hit1": sum(s["hit1"] for s in scored), "hit3": sum(s["hit3"] for s in scored),
           "hit5": sum(s["hit5"] for s in scored), "prec_pm": 0, "rec_pm": 0, "n0": n == 0}
    if n:
        out["prec_pm"] = _pm(sum((s["precision"] for s in scored), Fraction(0)) / n)
        out["rec_pm"] = _pm(sum((s["recall"] for s in scored), Fraction(0)) / n)
    return out


def inside(snap, target, *, pathmod=os.path, realpath=None) -> bool:
    """`target` 是否在 `snap` 之下（以路徑元件為界、不是字串前綴；`s1x` 不在 `s1` 之下）。
    `pathmod`（`ntpath`／`posixpath`）與 `realpath` 可注入，使同一平台能同時驗兩種語意
    （D-EQA-14）。"""
    real = realpath or pathmod.realpath

    def norm(p) -> str:
        return pathmod.normcase(pathmod.normpath(real(str(p))))
    root, got = norm(snap), norm(target)
    return got == root or got.startswith(root.rstrip(pathmod.sep) + pathmod.sep)


def find_transcript(repo: Path, agent_id: str) -> Path | None:
    """`projects/<slug>/**/subagents/agent-<id>.jsonl`；找不到或不唯一＝None（fail-closed）。"""
    base = transcript.transcript_dir(repo)
    if not base.is_dir():
        return None
    want = f"agent-{agent_id}.jsonl"
    found = [p for p in transcript._subagent_transcripts(base) if p.name == want]
    return found[0] if len(found) == 1 else None


def _blocks(rec: transcript.Record):
    msg = rec.obj.get("message") if rec.obj else None
    content = msg.get("content") if isinstance(msg, dict) else None
    return [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []


def _user_text(rec: transcript.Record) -> str:
    msg = rec.obj.get("message") if rec.obj else None
    content = msg.get("content") if isinstance(msg, dict) else None
    if isinstance(content, str):
        return content
    return "\n".join(b["text"] for b in _blocks(rec) if isinstance(b.get("text"), str))


def _glob_escape(pattern, snap, ins) -> bool:
    if not isinstance(pattern, str):
        return True
    if ".." in re.split(r"[/\\]", pattern):
        return True
    absolute = pattern[:1] in ("/", "\\") or bool(re.match(r"^[A-Za-z]:", pattern))
    return absolute and not ins(snap, re.split(r"[*?\[{]", pattern)[0] or pattern)


def _tool_verdict(call: dict, cwd, snap, ins) -> str | None:
    """單一 `tool_use` 的違規原因碼；合規回 None。"""
    name, inp = call.get("name"), call.get("input")
    inp = inp if isinstance(inp, dict) else {}
    if name == HARNESS_HANDBACK_TOOL:
        return None
    if name not in ALLOWED_TOOLS:
        return f"tool-not-allowed:{name}"
    if name == "Read":
        fp = inp.get("file_path")
        return None if isinstance(fp, str) and ins(snap, fp) else "outside-snapshot"
    path = inp.get("path")
    if path is None:
        if not (isinstance(cwd, str) and ins(snap, cwd)):
            return "path-missing"
    elif not (isinstance(path, str) and ins(snap, path)):
        return "outside-snapshot"
    if name == "Glob" and _glob_escape(inp.get("pattern"), snap, ins):
        return "pattern-escape"
    return None


def audit_case(repo: Path, agent_id: str, snap: str, nonce: str, *, pathmod=os.path,
               realpath=None) -> str | None:
    """洩漏稽核（AC-SI-46-5）：乾淨回 None，否則回第一個原因碼（判準順序即規格順序）。"""
    path = find_transcript(repo, agent_id)
    if path is None:
        return "transcript-missing"
    try:
        records = transcript.load(path)
    except transcript.TranscriptError:
        return "transcript-missing"
    if not records or any(r.obj is None for r in records):
        return "transcript-missing"
    assistants = [r for r in records if r.obj.get("type") == "assistant"]
    if not assistants:
        return "transcript-missing"
    if not any(r.obj.get("type") == "user" and nonce in _user_text(r) for r in records):
        return "binding-mismatch"

    def ins(a, b) -> bool:
        return inside(a, b, pathmod=pathmod, realpath=realpath)
    reads = 0
    for rec in assistants:
        for call in (b for b in _blocks(rec) if b.get("type") == "tool_use"):
            why = _tool_verdict(call, rec.obj.get("cwd"), snap, ins)
            if why:
                return why
            reads += 1
    if reads == 0:
        return "no-reads"
    last = records[-1]
    if not (last.obj.get("type") == "assistant"
            and any(b.get("type") == "text" for b in _blocks(last))):
        return "transcript-open"
    return None


def models_of(repo: Path, agent_id: str) -> str | None:
    """同名 `.meta.json` 的 `model` 值；缺＝None。"""
    path = find_transcript(repo, agent_id)
    try:
        meta = json.loads(path.with_suffix(".meta.json").read_bytes().decode("utf-8")) \
            if path else {}
    except (OSError, ValueError):
        return None
    model = meta.get("model") if isinstance(meta, dict) else None
    return model if isinstance(model, str) and model else None


def _row_lines(repo: Path) -> list[bytes]:
    p = repo / btcases.RESULTS_REL
    raw = p.read_bytes() if p.is_file() else b""
    lines = raw.split(b"\n")
    return lines[:-1] if lines and lines[-1] == b"" else lines


def ledger_findings(repo: Path, events: list[dict]) -> list[Finding]:
    """`events.prop_files` 的回測判準（AC-SI-46-6）：每筆 `backtest.result` 對得上結果帳本該行與
    雜湊、對得上案例檔雜湊；帳本每一行恰被一筆事件綁定。"""
    lines, bound, out = _row_lines(repo), set(), []
    for ev in (e for e in events if e.get("kind") == "backtest.result"):
        sub, n = f"seq={ev['seq']}", ev["ledger_line"]
        if not 1 <= n <= len(lines):
            out.append(Finding(sub, "BT-RESULT-MISSING", "fail", f"結果帳本沒有第 {n} 行"))
        else:
            bound.add(n)
            if btcases.sha_of(lines[n - 1]) != ev["row_sha256"]:
                out.append(Finding(sub, "BT-RESULT-SHA-MISMATCH", "fail",
                                   f"第 {n} 行雜湊與事件不符"))
        _, raw = btcases.load(btcases.cases_path(repo, ev["cases_version"]))
        if btcases.sha_of(raw) != ev["cases_sha256"]:
            out.append(Finding(sub, "BT-CASES-SHA-MISMATCH", "fail",
                               f"cases-v{ev['cases_version']}.json 缺或雜湊與事件不符"))
    return out + [Finding(f"results.jsonl L{i}", "BT-ROW-UNBOUND", "fail", "沒有事件綁定這一行")
                  for i in range(1, len(lines) + 1) if i not in bound]


def status_value(events: list[dict] | None) -> dict | None:
    """`si status` 的 `backtest` 鍵（AC-SI-46-8）：最近一次 `backtest.result`；走勢只含同
    `cases_sha256` 最近至多 5 次的 `hit5`（舊→新、含本次）；無事件＝None。"""
    bts = sorted((e for e in events or [] if e.get("kind") == "backtest.result"),
                 key=lambda e: e["seq"])
    if not bts:
        return None
    last = bts[-1]
    trend = [e["hit5"] for e in bts if e["cases_sha256"] == last["cases_sha256"]][-5:]
    keys = ("cases_version", "cases_sha256", "n", "hit1", "hit3", "hit5", "prec_pm", "rec_pm",
            "contaminated")
    return {**{k: last[k] for k in keys}, "hit5_trend": trend}


def status_line(value: dict | None) -> str:
    if value is None:
        return "backtest: null"
    return (f"backtest: cases_v{value['cases_version']} sha={value['cases_sha256'][7:19]} "
            f"n={value['n']} hit1/3/5={value['hit1']}/{value['hit3']}/{value['hit5']} "
            f"prec_pm={value['prec_pm']} rec_pm={value['rec_pm']} "
            f"contaminated={value['contaminated']} hit5_trend={value['hit5_trend']}")
