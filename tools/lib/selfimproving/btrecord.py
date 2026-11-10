"""SelfImproving 反事實回測的答案落檔與結果入帳：`backtest answer`、`backtest score`
（FR-SI-46；P6）。

能力類別 `rw`：`answer` 把子代理答案原樣複製進批次目錄並記綁定（子代理 id）；`score` 先做確定性
評分與洩漏稽核（唯讀），再在**事件帳本寫入鎖內**「先追加結果帳本一行、後追加 `backtest.result`
事件、事件失敗截回追加前長度」（沿 `regwrite.py` 的 `State.cleanups` 形態）。結果帳本只追加
（`O_APPEND`＋`fsync`）。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from . import btcases, btscore, evwrite
from . import events as si_events
from . import writeverbs as wv
from .btcases import BtError
from .git import Git

PAUSE_HOOK = None  # 測試鉤子：洩漏稽核完成之後、取事件帳本寫入鎖之前（不沿用 evwrite.PAUSE_HOOK）
_EVENT_KEYS = ("batch", "cases_version", "cases_sha256", "seed", "k", "n", "unanswered",
               "contaminated", "hit1", "hit3", "hit5", "prec_pm", "rec_pm")


def _write_new(path: Path, raw: bytes) -> None:
    with open(path, "xb") as fh:
        fh.write(raw)
        fh.flush()
        os.fsync(fh.fileno())


def _json_file(path: Path) -> dict:
    try:
        obj = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise BtError([("BT-BATCH-UNKNOWN", f"批次檔讀不到：{path.name}")]) from exc
    return obj if isinstance(obj, dict) else {}


def answer(repo: Path, batch: str, slot: str, file: str, agent_id: str, root: str | None,
           as_json: bool) -> wv.Out:
    """`answer`：驗格式後原樣複製為 `answers/<槽位>.json`，並在 `binding.json` 記 `agent_id`。"""
    base = Path(root) if root else None
    meta, bdir = btcases.load_batch(base, batch), btcases.batch_dir(base, batch)
    if not btcases.SLOT_RE.match(slot) or slot not in {c.get("slot") for c in meta["cases"]}:
        raise BtError([("BT-ANSWER-CASE-UNKNOWN", f"批次 {batch} 沒有案 {slot}")])
    dest = bdir / "answers" / f"{slot}.json"
    exists = BtError([("BT-ANSWER-EXISTS", f"{slot} 已有答案，不覆寫")])
    if dest.exists():
        raise exists
    if not btscore.AGENT_ID_RE.match(agent_id):
        raise BtError([("BT-ANSWER-FORMAT", "--agent-id 須為 8～32 位小寫十六進位")])
    try:
        raw = Path(file).read_bytes()
        obj = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise BtError([("BT-ANSWER-FORMAT", f"答案檔讀不到或不是 JSON（{type(exc).__name__}）")]
                      ) from exc
    codes = btscore.answer_codes(obj, slot)
    if codes:
        raise BtError(codes)
    try:
        _write_new(dest, raw)
    except FileExistsError:
        raise exists from None
    try:
        bind = _json_file(bdir / "binding.json")
        bind.setdefault("answers", {})[slot] = {"agent_id": agent_id,
                                                "answered_at": btcases.now_iso()}
        (bdir / "binding.json").write_bytes(btcases.dumps(bind).encode("utf-8"))
    except (OSError, BtError) as exc:
        dest.unlink(missing_ok=True)
        raise wv.UsageError(f"binding.json 更新失敗（{type(exc).__name__}）") from exc
    text = f"ok backtest answer batch={batch} case={slot} agent_id={agent_id}\n"
    return wv.Out(0, json.dumps({"ok": True, "verb": "backtest", "sub": "answer", "batch": batch,
                                 "case": slot, "agent_id": agent_id}, ensure_ascii=False) + "\n"
                  if as_json else text)


def _evaluate(repo: Path, meta: dict, bdir: Path) -> tuple[list[dict], list[dict], set[str]]:
    """逐案評分與洩漏稽核：回（per_case, 通過者的評分, 子代理模型集合）。"""
    bind = _json_file(bdir / "binding.json").get("answers", {})
    per_case, scored, models = [], [], set()
    for c in meta["cases"]:
        slot, ident = c["slot"], c["id"]
        ans = bdir / "answers" / f"{slot}.json"
        try:
            obj = json.loads(ans.read_bytes().decode("utf-8"))
        except (OSError, ValueError):
            obj = None
        if obj is None or btscore.answer_codes(obj, slot):
            per_case.append({"case": ident, "status": "unanswered"})
            continue
        agent = (bind.get(slot) or {}).get("agent_id")
        why = btscore.audit_case(repo, agent, c["snap"], c["nonce"]) if agent else \
            "transcript-missing"
        model = btscore.models_of(repo, agent) if agent else None
        models |= {model} if model else set()
        if why:
            per_case.append({"case": ident, "status": "contaminated", "reason": why})
            continue
        sc = btscore.score_case(c["changed_files"], obj["suspects"])
        scored.append(sc)
        per_case.append({"case": ident, "status": "ok", "rank": sc["rank"]})
    return per_case, scored, models


def _row(repo: Path, meta: dict, agg: dict, per_case: list[dict], models: set[str]) -> dict:
    count = lambda s: sum(1 for p in per_case if p["status"] == s)  # noqa: E731
    return {"batch": meta["batch"], "scored_at": btcases.now_iso(),
            "cases_version": meta["cases_version"], "cases_sha256": meta["cases_sha256"],
            "seed": meta["seed"], "k": meta["k"], "head_sha": Git(repo).head(), "n": agg["n"],
            "unanswered": count("unanswered"), "contaminated": count("contaminated"),
            "hit1": agg["hit1"], "hit3": agg["hit3"], "hit5": agg["hit5"],
            "prec_pm": agg["prec_pm"], "rec_pm": agg["rec_pm"], "models": sorted(models),
            "per_case": per_case}


def _truncate_back(path: Path, size: int, existed: bool):
    def undo() -> None:
        if not existed:
            path.unlink(missing_ok=True)
            return
        with open(path, "r+b") as fh:
            fh.truncate(size)
    return undo


def _append_row(path: Path, line: bytes, state: evwrite.State) -> int:
    """鎖內：追加結果帳本一行（`O_APPEND`＋`fsync`），登記截回；回該行的 1 起算行號。"""
    existed = path.is_file()
    old = path.read_bytes() if existed else b""
    if old and not old.endswith(b"\n"):
        raise evwrite.Reject([("BT-LEDGER-TORN", "結果帳本末位元組不是 LF（撕裂的寫入）")])
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0),
                 0o644)
    state.cleanups.append(_truncate_back(path, len(old), existed))
    try:
        view = memoryview(line + b"\n")
        while view:
            view = view[os.write(fd, view):]
        os.fsync(fd)
    finally:
        os.close(fd)
    return old.count(b"\n") + 1


def _render(row: dict, as_json: bool):
    def render(ev: dict) -> str:
        if as_json:
            return json.dumps({"ok": True, "kind": "backtest.result", "seq": ev["seq"], "id": None,
                               **{k: ev[k] for k in (*_EVENT_KEYS, "ledger_line")},
                               "per_case": row["per_case"]}, ensure_ascii=False) + "\n"
        head = (f"ok backtest.result seq={ev['seq']} batch={ev['batch']} n={ev['n']} "
                f"unanswered={ev['unanswered']} contaminated={ev['contaminated']} "
                f"hit1/3/5={ev['hit1']}/{ev['hit3']}/{ev['hit5']} prec_pm={ev['prec_pm']} "
                f"rec_pm={ev['rec_pm']} ledger_line={ev['ledger_line']}"
                + (" n=0（不得宣稱達標）" if ev["n"] == 0 else ""))
        rows = [f"  {p['case']} {p['status']}" + (f" rank={p['rank']}" if "rank" in p else "")
                + (f" {p['reason']}" if "reason" in p else "") for p in row["per_case"]]
        return "\n".join([head, *rows]) + "\n"
    return render


def score(repo: Path, batch: str, root: str | None, as_json: bool) -> wv.Out:
    """`score`：確定性評分＋洩漏稽核＋入帳（結果帳本一行＋事件）；同批只准一次。"""
    base = Path(root) if root else None
    meta, bdir = btcases.load_batch(base, batch), btcases.batch_dir(base, batch)
    params = wv.params_for(repo, "event_max_bytes")
    scored_before = BtError([("BT-BATCH-SCORED", f"{batch} 已入帳過")])
    prior = si_events.load_sound_events(repo / si_events.LEDGER_REL) or []
    if any(e.get("kind") == "backtest.result" and e.get("batch") == batch for e in prior):
        raise scored_before
    _, raw = btcases.load(btcases.cases_path(repo, meta["cases_version"]))
    if btcases.sha_of(raw) != meta["cases_sha256"]:
        raise BtError([("BT-CASES-SHA-MISMATCH", "案例檔缺或雜湊與批次記錄不符")])
    per_case, scored, models = _evaluate(repo, meta, bdir)
    row = _row(repo, meta, btscore.aggregate(scored), per_case, models)
    line = json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if PAUSE_HOOK is not None:
        PAUSE_HOOK()

    def build(state):
        if any(e.get("kind") == "backtest.result" and e.get("batch") == batch
               for e in state.events):
            raise evwrite.Reject(scored_before.codes)
        lno = _append_row(repo / btcases.RESULTS_REL, line, state)
        return {"kind": "backtest.result", "by": "main", **{k: row[k] for k in _EVENT_KEYS},
                "ledger_line": lno, "row_sha256": btcases.sha_of(line)}
    return wv.append(repo, "backtest", build, params, as_json, _render(row, as_json))
