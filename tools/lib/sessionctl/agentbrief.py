"""交接包第 12 欄「在飛／被切代理」與被切判準 `cut_kind`（DES Control_Handover §6.4／§9.1；
REQ-CTL-17、19；零 token、只讀檔）。

WHY：換 session 之後，在飛子代理的任務書、半成品落點、重派指令原本完全不在交接包內（新 session
只能翻上兩棒 scratchpad）。本檔從**代理自己的逐字稿**取：首筆 user 記錄＝原任務書（前
`TASK_EXCERPT_CHARS` 字＋其中出現的 scratchpad／handback 路徑）、Write／Edit 的 `file_path`（輸出
落點）、最後 `LAST_TEXTS` 則 assistant 純文字摘錄；**一律不含 `tool_result` 內容**（隱私面與
`.prompts.md` 同級）。被切判準（`cut_kind`）單一家在此，控制態讀取器（`controlfacts`）與第 12
欄共用：`usage_limit`（末筆記錄 `apiError` 含 `usage_limit_reached`，或末筆 `<synthetic>` assistant
文字含 `hit your`／`usage limit`）＞ `stopped`（主逐字稿的 `<status>killed</status>` 通知）＞
`residue`（名冊既有狀態）。**不自動重派**（裁10）：只給「新代理＋短任務書」的指標。

全欄大小上限常數（`COL12_MAX_CHARS` 等）住本檔；超出從最舊列截斷並於欄末寫「已截斷 N 列」。
"""
from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Callable, Iterable
from pathlib import Path

from . import rosterscan

BRIEF_CHARS = 300          # 每則 assistant 摘錄上限（DES §9.2）
LAST_TEXTS = 3             # 每支代理至多幾則 assistant 摘錄
TASK_EXCERPT_CHARS = 600   # 任務書指標＝首筆 user 記錄前幾字
OUTPUT_FILES_MAX = 8       # Write／Edit 的 file_path 去重後至多幾個
BRIEF_PATHS_MAX = 4        # 任務書內寫明的 scratchpad／handback 路徑至多幾個
COL12_MAX_CHARS = 12000    # 第 12 欄全欄上限
#: 「剛 TaskStop」的時間窗：被 TaskStop 的代理逐字稿 mtime 在此秒數內才列入（更舊者是歷史，不是
#: 接續資訊；DES §9.1 稱「剛」，未給數字，此處補一個量測面的常數並於交卷揭露）。
STOPPED_RECENT_SECONDS = 24 * 3600
_TAIL_BYTES = 262144
#: 找「最後 3 則 assistant 文字」多讀一些尾端：工具結果大時 256 KB 內可能一則文字都沒有。
_TEXT_TAIL_BYTES = 2 * 1024 * 1024
_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/]|/)[^\s`'\"<>|*?，。；、）)\]]+")
_PATH_KEYS = ("scratchpad", "handback")
_REDISPATCH = "重派：新代理＋短任務書（原任務書見指標），不 SendMessage 續舊代理"
_DRAIN = "排空後換（pending_switch）"
_ACTIONS = {"running": _DRAIN, "quiet": f"{_DRAIN}；若已無產出改「{_REDISPATCH}」",
            "cut": _REDISPATCH, "stopped": _REDISPATCH, "residue": _REDISPATCH}


def _unknown(why: str) -> str:
    return f"量不到：{why}"


def _quote(text: str) -> str:
    """引文逐行加 `> `（與 `handoff_build._quote` 同契約；本檔不 import 它以免循環）。"""
    return "\n".join(f"> {ln}" for ln in text.splitlines()) or ">"


def _excerpt(text: str, limit: int) -> str:
    return text if len(text) <= limit else f"{text[:limit]}…（已截斷，原文 {len(text)} 字）"


def _tail_records(path: Path, nbytes: int = _TAIL_BYTES) -> list[dict]:
    """尾端 `nbytes` 內的 JSON 記錄（壞行跳過；被截斷的第一行丟掉）；讀不到 ⇒ 空 list。"""
    try:
        with path.open("rb") as handle:
            size = handle.seek(0, os.SEEK_END)
            handle.seek(max(0, size - nbytes))
            chunk = handle.read()
    except OSError:
        return []
    lines = chunk.decode("utf-8", errors="replace").splitlines()
    if size > nbytes:
        lines = lines[1:]
    out = []
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def _blocks(rec: dict) -> list:
    msg = rec.get("message")
    content = msg.get("content") if isinstance(msg, dict) else None
    return content if isinstance(content, list) else []


def _text(rec: dict) -> str:
    """一筆記錄的純 text（字串內容或 text 區塊串接）；`tool_result`／`tool_use` 一律不取。"""
    msg = rec.get("message")
    content = msg.get("content") if isinstance(msg, dict) else None
    if isinstance(content, str):
        return content
    return "\n".join(str(b.get("text") or "") for b in _blocks(rec)
                     if isinstance(b, dict) and b.get("type") == "text")


def _is_synthetic(rec: dict) -> bool:
    msg = rec.get("message")
    return isinstance(msg, dict) and msg.get("model") == "<synthetic>"


# ───────────────────────────────────────────────────────── 被切判準（單一家）
def _is_usage_limit(rec: dict) -> bool:
    if "usage_limit_reached" in str(rec.get("apiError") or ""):
        return True
    if rec.get("type") != "assistant" or not _is_synthetic(rec):
        return False
    low = _text(rec).lower()
    return "hit your" in low or "usage limit" in low


def cut_kind(agent_path: Path | None, *, killed: Iterable[str] = (), agent_id: str = "",
             state: str = "") -> str | None:
    """被切種類：`usage_limit`／`stopped`／`residue`／`None`（沒被切）。只讀代理逐字稿尾端
    （statusLine 路徑會呼叫，不得讀全檔）；讀不到 ⇒ 不判 usage_limit（偏保守，不猜）。"""
    recs = _tail_records(Path(agent_path)) if agent_path else []
    if recs and _is_usage_limit(recs[-1]):
        return "usage_limit"
    if agent_id and agent_id in set(killed):
        return "stopped"
    return "residue" if state == "residue" else None


# ───────────────────────────────────────────────────────── 單支代理的讀取
def _first_user_text(path: Path) -> str | None:
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if isinstance(rec, dict) and rec.get("type") == "user":
                    text = _text(rec).strip()
                    if text:
                        return text
    except OSError:
        return None
    return None


def _output_files(path: Path) -> list[str]:
    """代理 Write／Edit 的 `file_path`（全檔掃，行內先子字串過濾）；去重、留最近幾個。"""
    seen: dict[str, None] = {}
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if '"file_path"' not in line or '"tool_use"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                for block in _blocks(rec) if isinstance(rec, dict) else ():
                    if isinstance(block, dict) and block.get("type") == "tool_use" and \
                            block.get("name") in ("Write", "Edit", "NotebookEdit"):
                        target = (block.get("input") or {}).get("file_path")
                        if isinstance(target, str) and target:
                            seen.pop(target, None)
                            seen[target] = None
    except OSError:
        return []
    return list(seen)[-OUTPUT_FILES_MAX:]


def _brief_paths(task: str) -> list[str]:
    found: dict[str, None] = {}
    for hit in _PATH_RE.findall(task):
        hit = hit.rstrip(".,:;")
        if any(k in hit.lower() for k in _PATH_KEYS):
            found.setdefault(hit)
    return list(found)[:BRIEF_PATHS_MAX]


def _last_texts(recs: list[dict]) -> list[str]:
    texts = [t for r in recs if r.get("type") == "assistant" and not _is_synthetic(r)
             and (t := _text(r).strip())]
    return [_excerpt(t, BRIEF_CHARS) for t in texts[-LAST_TEXTS:]]


def agent_file(sid: str, agent_id: str, transcript: Path | None,
               projects: Path | None = None) -> Path | None:
    """該代理的 `agent-<id>.jsonl`：先依主逐字稿推導（`<slug>/<sid>/subagents/`），缺才查名冊。"""
    if transcript is not None:
        cand = Path(transcript).parent / sid / "subagents" / f"agent-{agent_id}.jsonl"
        if cand.is_file():
            return cand
    try:
        from . import roster  # noqa: PLC0415 — lazy：roster 鏈較重
        return roster._agent_path(sid, agent_id, projects)
    except Exception:  # noqa: BLE001 — 找不到＝量不到，不拋
        return None


def _row(agent: dict, sid: str, transcript: Path | None, killed: set[str],
         projects: Path | None, full: bool) -> dict:
    """一支代理的列資料。`full=False`（控制態用）只讀尾端判種類，不掃全檔。"""
    aid = str(agent.get("id") or "")
    path = agent_file(str(agent.get("owner_sid") or sid), aid, transcript, projects)
    state = str(agent.get("state") or "quiet")
    kind = cut_kind(path, killed=killed, agent_id=aid, state=state)
    row = {"id": aid, "description": str(agent.get("description") or ""),
           "model": str(agent.get("model") or ""), "state": state, "kind": kind,
           "ctx": agent.get("ctx_tokens"), "last_at": agent.get("last_at") or "",
           "path": path, "error": "" if path is not None else _unknown("找不到代理逐字稿")}
    if full and path is not None:
        task = _first_user_text(path)
        recs = _tail_records(path, _TEXT_TAIL_BYTES)
        row.update(task=task, brief_paths=_brief_paths(task or ""), outputs=_output_files(path),
                   texts=_last_texts(recs))
        if task is None and not recs:
            row["error"] = _unknown("代理逐字稿空或讀不到")
    return row


def _stopped_agents(sid: str, transcript: Path | None, seen: set[str], killed: set[str],
                    now: float) -> list[dict]:
    """主逐字稿記著被 TaskStop、近 `STOPPED_RECENT_SECONDS` 內有動、且名冊不再列的代理。"""
    if transcript is None or not killed:
        return []
    folder = Path(transcript).parent / sid / "subagents"
    out = []
    try:
        files = sorted(folder.glob("agent-*.jsonl"))
    except OSError:
        return []
    from . import roster  # noqa: PLC0415 — lazy
    for path in files:
        aid = path.stem.removeprefix("agent-")
        try:
            fresh = now - path.stat().st_mtime <= STOPPED_RECENT_SECONDS
        except OSError:
            continue
        meta = roster._meta(path)
        if aid in killed and aid not in seen and fresh and meta.get("finished") is not True:
            info = roster._scan(path, False)
            out.append({"id": aid, "owner_sid": sid, "state": "stopped",
                        "description": meta.get("description"),
                        "model": meta.get("model") or meta.get("pickedEffortModel"),
                        "ctx_tokens": info["ctx_tokens"], "last_at": roster._iso(info["last_at"])})
    return out


def collect(agents: list[dict], sid: str, transcript: Path | None, *, full: bool = True,
            projects: Path | None = None, now: float | None = None) -> list[dict]:
    """名冊代理（running／quiet／residue）＋近期被 TaskStop 者 ⇒ 列資料，由舊到新。
    `kind`＝被切種類；`status`＝顯示用（`cut`／`stopped`／`residue`，否則 running／quiet）。"""
    at = time.time() if now is None else now
    killed = rosterscan.killed_ids(Path(transcript), sid) if transcript is not None else set()
    seen = {str(a.get("id")) for a in agents}
    rows = [_row(a, sid, transcript, killed, projects, full)
            for a in [*agents, *_stopped_agents(sid, transcript, seen, killed, at)]]
    for row in rows:
        row["status"] = {"usage_limit": "cut", "stopped": "stopped",
                         "residue": "residue"}.get(row["kind"] or "", row["state"])
    return sorted(rows, key=lambda r: r["last_at"])


# ───────────────────────────────────────────────────────── 第 12 欄
def _block(row: dict) -> str:
    cut = f"（{row['kind']}）" if row["status"] == "cut" else ""
    ctx = f"ctx {row['ctx']:,}" if isinstance(row.get("ctx"), int) else "ctx 量不到"
    head = (f"- {row['id']}｜{row['description'] or '（無描述）'}｜{row['model'] or '模型未知'}｜"
            f"{row['status']}{cut}｜{ctx}｜最後 {row['last_at'] or '量不到'}")
    if row.get("error"):
        return f"{head}\n  - {row['error']}\n  - 建議處置：{_ACTIONS[row['status']]}"
    pointer = _quote(_excerpt(row["task"], TASK_EXCERPT_CHARS)) if row.get("task") else \
        _unknown("代理逐字稿無任務書記錄")
    outs = [*row.get("outputs", []), *(f"{p}（任務書提及）" for p in row.get("brief_paths", []))]
    texts = "\n".join(_quote(t) for t in row.get("texts", [])) or _unknown("無 assistant 文字")
    ind = lambda s: "\n".join(f"    {ln}" for ln in s.splitlines())  # noqa: E731
    return (f"{head}\n  - 任務書指標：\n{ind(pointer)}\n  - 代理逐字稿：{row['path']}\n"
            f"  - 輸出落點：{'；'.join(outs) or _unknown('代理沒有 Write／Edit 記錄')}\n"
            f"  - 最後 {LAST_TEXTS} 則 assistant：\n{ind(texts)}\n"
            f"  - 建議處置：{_ACTIONS[row['status']]}")


def _fit(blocks: list[str], cap: int, noun: str) -> str:
    """由舊到新的區塊串；超過 `cap` 字從最舊截斷並寫「已截斷 N 列」（單塊仍超限則硬切）。"""
    dropped = 0
    while len(blocks) > 1 and len("\n".join(blocks)) > cap:
        blocks, dropped = blocks[1:], dropped + 1
    text = "\n".join(blocks)
    if len(text) > cap:
        text = text[:cap] + "…（單列過長，已硬切）"
    return text + (f"\n（已截斷 {dropped} 列{noun}）" if dropped else "")


def render_rows(rows: list[dict]) -> str:
    return _fit([_block(r) for r in rows], COL12_MAX_CHARS, "；全清單見 `sessionctl status`")


_CUT_SECTIONS = (("cut", "被額度切斷"), ("stopped", "主控已停止（TaskStop）"),
                 ("residue", "殘局（擁有者已不在、非燒額度中）"))
_TOKEN_SPLIT = re.compile(r"[\s｜|，。；：、（）()\[\]【】「」]+")


def main_layer(pkg_text: str | None) -> str:
    """交接包的**主控層**（`## 主控層` 之後；不含機械層）。判「已記入」只看這裡：機械層第 12 欄本來就列所有
    代理，把它算進去＝恆為「已記入」，判準失去鑑別力（TCS MU-CTL-62）。"""  # noqa: E501
    text = pkg_text or ""
    at = text.find("## 主控層")
    return text[at:] if at >= 0 else ""


def recorded_in_main(row: dict, pkg_text: str | None) -> bool:
    """主控層是否提到該代理：id 前 8 碼，或描述的首個詞元（以空白／`｜`／全形標點切；長度≥3 且含英數）。"""  # noqa: E501
    main = main_layer(pkg_text)
    if not main:
        return False
    if str(row.get("id") or "")[:8] and str(row["id"])[:8] in main:
        return True
    tokens = [t for t in _TOKEN_SPLIT.split(str(row.get("description") or "")) if t]
    first = tokens[0] if tokens else ""
    return len(first) >= 3 and any(c.isascii() and c.isalnum() for c in first) and first in main


def _stopped_block(row: dict, pkg_text: str | None, pkg_path: str | None) -> str:
    """`stopped` 一列：處置行換成「已記入交接包」或「交接包未記處置」；其餘行與第 12 欄同源逐字。"""
    head = _block(row).rsplit("\n", 1)[0]
    done = (f"主控已停止並已記入交接包 {pkg_path}（處置見主控層〈未完成〉）"
            if recorded_in_main(row, pkg_text) and pkg_path
            else "主控已停止、交接包未記處置 ⇒ 下一棒依第 12 欄重派")
    return f"{head}\n  - 處置：{done}"


def render_cut(rows: list[dict], *, pkg_text: str | None = None, pkg_path: str | None = None) -> str:  # noqa: E501
    """被切／被 TaskStop／殘局代理清單（DES §6.4 三處出聲共用的同一份文字；**不自動重派、不再寫「由主控
    決定」**）。三種狀態各自一段標題；`stopped` 的處置看本 sid 最新已封存包的主控層是否提到它
    （`pkg_text`／`pkg_path` 缺省＝找不到包 ⇒「未記處置」句）。第 12 欄 `render_rows` 逐字不變。"""  # noqa: E501
    cut = [r for r in rows if r.get("status") in ("cut", "stopped", "residue")]
    if not cut:
        return ""
    parts = []
    for status, title in _CUT_SECTIONS:
        mine = [r for r in cut if r["status"] == status]
        if not mine:
            continue
        blocks = [_stopped_block(r, pkg_text, pkg_path) if status == "stopped" else _block(r) for r in mine]  # noqa: E501
        parts.append(f"{title}（{len(mine)} 支；不自動重派）：\n"
                     + _fit(blocks, COL12_MAX_CHARS, "；全清單見 `sessionctl status`"))
    return "\n".join(parts)

def cut_list(agents: list[dict], sid: str, transcript: Path | None,
             projects: Path | None = None) -> list[dict]:
    """控制態用（`controlfacts`）：`[{"id","kind"}]`，kind＝`usage_limit`／`stopped`／`residue`。
    只讀尾端，不掃全檔、不讀任務書。"""
    return [{"id": r["id"], "kind": r["kind"]}
            for r in collect(agents, sid, transcript, full=False, projects=projects) if r["kind"]]


def oi_line(oi_fn: Callable[[], str] | None = None) -> str:
    """未結 OI id 一行：重用 SessionStart 簡報的 OIR 摘要函式；量不到寫量不到（不取主控自述）。"""
    try:
        if oi_fn is None:
            import session_brief_oi  # noqa: PLC0415 — lazy：只有真要讀 OIR 帳本時才載入
            oi_fn = session_brief_oi.openitems_line
        text = " ".join(str(oi_fn()).split())
    except Exception as exc:  # noqa: BLE001 — 取不到寫「量不到」，不拋
        return _unknown(f"OIR 目視清單讀不到（{type(exc).__name__}）")
    return text or _unknown("OIR 目視清單無資料（或帳本讀不到）")


def column12(agents: list[dict] | None, sid: str, transcript: Path | None, *, why: str = "",
             oi_fn: Callable[[], str] | None = None, projects: Path | None = None,
             now: float | None = None) -> str:
    """交接包第 12 欄全文。`agents=None`（名冊讀不動）⇒ 整欄「量不到：<why>」；單支代理讀不到只影響
    該列。末尾附「未結 OI」一行（REQ-CTL-18）。不拋。"""
    try:
        if agents is None:
            body = _unknown(why or "名冊不可用")
        else:
            rows = collect(agents, sid, transcript, projects=projects, now=now)
            body = render_rows(rows) if rows else "（無在飛／被切代理；名冊量到的零）"
    except Exception as exc:  # noqa: BLE001 — 契約：不拋
        body = _unknown(f"第 12 欄產生失敗（{type(exc).__name__}: {exc}）")
    return f"{body}\n\n未結 OI：{oi_line(oi_fn)}"


def main_model(transcript: Path | None) -> str | None:
    """主控模型＝逐字稿最後一筆非 synthetic assistant 記錄的 model；讀不到 ⇒ `None`。"""
    for rec in reversed(_tail_records(Path(transcript))) if transcript else ():
        msg = rec.get("message")
        model = msg.get("model") if isinstance(msg, dict) else None
        if rec.get("type") == "assistant" and isinstance(model, str) and model != "<synthetic>":
            return model
    return None
