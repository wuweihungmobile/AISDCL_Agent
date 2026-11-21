"""完成閘（Stop；看狀態、不看措辭）與其周邊判準（DES §4、§5.3；REQ-WP-20／21／24／26、REQ-WP-15）。

第七類停＝宣告式完成：主控說「做完了」，OIR 卻還有沒人驅動的未結項（undriven）。本檔只判**狀態**：
回覆文字不參與判斷（MU-WP-07）。純函式為主，唯一的副作用是 `mark_pushed`／`cap_note` 寫的兩個
痕跡標記；**不開任何子行程**（DES §4.5）：driven 有效性只讀事件帳本與排程快取（`schedcache`），
狀態佐證由呼叫端（hook）以參數 `evidence` 傳入，與半路停工判準共用同一個布林值。

fail-open：OIR／params 讀不到或壞掉 ⇒ `load_state` 回 `None` 並向 stderr 出聲一行，呼叫端放行。

保溫閘讓路（DES §4.4）：兩支 Stop hook 是並行行程，標記檔可能還沒寫；所以讓路判準另含「現在就有
undriven」這一格（同樣只讀帳本）。跨套件只透過資料檔，本檔不 import sessionctl。
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from lib import endurance_env

from . import fold as oi_fold
from . import ledger as oi_ledger
from . import params as oi_params
from . import schedcache

UNATTENDED_ENV = "AUTOSDD_UNATTENDED"
#: 推回訊息列出的 undriven 上限（DES §4.1：前 5 個）。
LIST_LIMIT = 5
#: `.gate` 標記的新鮮度（秒）：同一回合的兩支 Stop hook 在數秒內跑完；逾時＝上一回合的殘留，不讓路。
MARKER_FRESH_SECONDS = 900
_HUMAN_STATES = ("listed", "escalated")


@dataclass
class State:
    undriven: list[dict] = field(default_factory=list)
    human: list[dict] = field(default_factory=list)
    human_cap: int = 7


def default_root() -> Path:
    """repo 根：`CLAUDE_PROJECT_DIR` 優先（沙盒 E2E 靠它指向沙盒樹），否則由本檔位置推出。"""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(env) if env else Path(__file__).resolve().parents[3]


def _warn(text: str) -> None:
    try:
        sys.stderr.write(f"openitems 完成閘：{text}\n")
    except Exception:  # noqa: BLE001 — 出聲失敗不得變成故障
        pass


def load_state(root: Path | None = None, now: datetime | None = None) -> State | None:
    """讀帳本＋參數＋排程快取→fold；讀不到／壞掉回 `None`（fail-open，stderr 出聲一行）。"""
    base = Path(root) if root is not None else default_root()
    try:
        params = oi_params.load(base)
        events, _bad = oi_ledger.read_events(oi_params.ledger_path(base))
        at = now or datetime.now().astimezone()
        folded = oi_fold.fold(events, params, at, schedcache.exists_fn(params, at))
    except Exception as exc:  # noqa: BLE001 — OIR 讀不到一律放行，不得把閘變成阻斷源
        _warn(f"OIR 讀取失敗，本次放行（{type(exc).__name__}：{str(exc).splitlines()[0][:100]}）")
        return None
    human = sorted((i for i in folded.items.values() if i["state"] in _HUMAN_STATES),
                   key=lambda i: (i["opened"], i["id"]))
    return State(folded.undriven(), human, params["human_cap"])


def stop_verdict(state: State | None, payload: dict, env=None, *, evidence: bool) -> str:
    """推回 reason；放行回 `""`。推回 ⇔ 非第二次 Stop ∧ 非無人窗口 ∧ undriven≥1 ∧ 有佐證。"""
    env = os.environ if env is None else env
    if state is None or not isinstance(payload, dict) or payload.get("stop_hook_active"):
        return ""
    if env.get(UNATTENDED_ENV) or not state.undriven or not evidence:
        return ""
    rows = sorted(state.undriven, key=lambda i: (i["opened"], i["id"]))
    lines = [f"- {i['id']}｜{i['title'][:60]}（{i['kind']}）" for i in rows[:LIST_LIMIT]]
    more = f"（另 {len(rows) - LIST_LIMIT} 項）" if len(rows) > LIST_LIMIT else ""
    return "\n".join([
        f"🔴 完成閘：還有 {len(rows)} 個未結項沒人驅動（說「做完了」不算，看 OIR 狀態）{more}：",
        *lines,
        "出口三選一：`python tools/openitems.py drive <id>`（auto／observe，掛排程驅動器）；"
        "`python tools/openitems.py convert <id> --kind human --why \"<WHY>\"`（轉人工清單）；"
        "或同回合 AskUserQuestion。（只推回這一次；第二次 Stop 放行。）"])


def _marker_dir(write: bool = True) -> Path:
    """讀端用唯讀的 `trace_dir_peek`（不 mkdir），寫端用 `trace_dir`；兩端看向同一個家。"""
    return (endurance_env.trace_dir() if write else endurance_env.trace_dir_peek()[0]) / "openitems"


def mark_pushed(sid: str) -> None:
    """完成閘推回當回合寫 `<sid>.gate`（供保溫閘讓路）。寫不進去不影響推回。"""
    try:
        folder = _marker_dir()
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{sid}.gate").write_text(oi_ledger.now_iso(), encoding="utf-8")
    except (OSError, ValueError):
        pass


def cap_note(state: State | None, sid: str) -> str:
    """人工清單 > `human_cap` 時每個 session 首次 Stop 附一行（只出聲、不阻斷；記 `.capnote`）。"""
    if state is None or not sid or len(state.human) <= state.human_cap:
        return ""
    try:
        flag = _marker_dir() / f"{sid}.capnote"
        if flag.exists():
            return ""
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.write_text(oi_ledger.now_iso(), encoding="utf-8")
    except OSError:
        return ""
    return (f"人工清單已滿 {len(state.human)} 項（上限 {state.human_cap}），"
            "請先嘗試轉機驗（openitems convert）。")


def keepwarm_yields(sid: str, state: State | None = None, now: datetime | None = None) -> bool:
    """保溫閘讓路：本 session 的 `.gate` 標記新鮮，或 OIR 現在有 undriven（兩支 Stop hook 並行，
    標記可能還沒寫）。讀不到一律 `False`（不讓路＝保溫照舊）。"""
    try:
        marker = _marker_dir(False) / f"{sid}.gate"
        at = (now or datetime.now().astimezone()).timestamp()
        age = at - marker.stat().st_mtime if sid and marker.is_file() else None
        if age is not None and -5 <= age <= MARKER_FRESH_SECONDS:  # 檔案系統時鐘可略早於行程時鐘
            return True
    except OSError:
        pass
    st = state if state is not None else load_state(now=now)
    return bool(st and st.undriven)


def human_lines(state: State | None) -> list[str]:
    """SessionStart「掌舵者目視清單」：`listed`＋`escalated` 依 open 時間前 `human_cap` 項。"""
    if state is None or not state.human:
        return []
    out = []
    for item in state.human[:state.human_cap]:
        esc = "已升級" if item["state"] == "escalated" else "人工"
        tag = "須掌舵者親打" if item["kind"] == "k1" else esc
        out.append(f"{item['id']}｜{item['title'][:50]}（{tag}）")
    if len(state.human) > state.human_cap:
        out.append(f"另 {len(state.human) - state.human_cap} 項")
    return out
