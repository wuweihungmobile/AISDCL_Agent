"""park 等待期間額度提前恢復的純判準葉（Control_Handover DES §8；REQ-CTL-31～38；W6）。

WHY（2026-11-22 真事件）：`65389f03` 週額度 100% ⇒ `park --at` 到 11/24 19:03；掌舵者換帳號後讀數
已回 0%，但等待期間沒有任何元件重讀額度，只能靠人手開窗（提前量下界 52.2 小時）。本檔只有判準與
文字組裝：**不 import `park_cli`／`parkearly`**（import 方向 planner → parkearly → {parkprobe,
park_cli}、park_cli → parkprobe，無環）；唯一的額度讀取是 `park._pace_state`（經 `quota_meter`
的唯讀 GET、TTL≥180 秒），不新增第二個端點知識（PRD §15.5 紅線 1 豁免四條件）。
基準欄名常數住本檔、**不進 `qw_schema`**（單包兩端；DES D-CT-9）。
"""
from __future__ import annotations

import json
from datetime import datetime

import endurance_env

from . import park

MK_PARKED_PCT = "parked_pct"
MK_PARKED_ACCOUNT = "parked_account"
EARLY_MIN_WAIT_MIN = 60  # 剩餘等待低於此值不探（照原排程就好）
EARLY_DROP_PP = 5.0  # 讀數須比登記當下低至少這麼多
UNMEASURED_STREAK = 3  # 連續這麼多次量不到 ⇒ SessionStart 出聲
EV_PROBE, EV_RECOVERED = "park_early_probe", "park_early_recovered"
REASON_UNMEASURED, REASON_NO_BASELINE = "unmeasured", "no_baseline"
REASON_HOLD, REASON_RECOVERED = "hold", "recovered"


def reading(state) -> float | None:
    """短窗∪週軸的最大讀數；FALLBACK／模型分軌軸與非有限值不算；沒有可用軸 ⇒ None。"""
    import quota_policy  # noqa: PLC0415 — lazy

    banned = quota_policy.FALLBACK_KINDS | quota_policy.MODEL_SCOPED_KINDS
    pcts = [a.pct for a in state.axes if a.kind not in banned and park._real_pct(a.pct)]  # noqa: SLF001
    return float(max(pcts)) if pcts else None


def baseline(S: dict, now: datetime) -> dict:
    """`park` 登記當下併進標記的兩個基準欄；量不到讀數 ⇒ `{}`（登記照常、之後出聲 no_baseline）。
    `parked_account` 量不到寫 `None`（舊標記無此欄與此同義：不判換帳號）。縫：`S["quota"]`。"""
    try:
        state = (S.get("quota") or park._pace_state)(now)  # noqa: SLF001
        cur = reading(state)
    except Exception:  # noqa: BLE001 — 基準只是輔助，量不到不得讓 park 登記失敗
        return {}
    return {} if cur is None else {MK_PARKED_PCT: cur, MK_PARKED_ACCOUNT: state.account_key}


def has_baseline(marker) -> bool:
    return park._real_pct((marker or {}).get(MK_PARKED_PCT))  # noqa: SLF001


def account_changed(marker, now_key) -> bool:
    """標記基準帳號與當下帳號皆非空且不相等；任一側 `None`／空（量不到、舊標記）⇒ False。"""
    then = (marker or {}).get(MK_PARKED_ACCOUNT)
    return bool(then) and bool(now_key) and then != now_key


def evaluate(marker: dict, state, policy, now: datetime) -> dict:
    """純判準：回 `{reason, recovered, cur, baseline, account_changed}`。讀不到 ⇒ `unmeasured`；
    無基準 ⇒ `no_baseline`（不判）；否則 `recovered ⇔ cur ≤ parked_pct − 5pp ∧ cur < 準備門檻`。
    `now` 保留給簽名一致（讀數年齡由 `park._pace_state` 的 TTL 負責，陳舊先補量、補不到＝空軸）。"""
    base = marker.get(MK_PARKED_PCT)
    out = {"reason": REASON_NO_BASELINE, "recovered": False, "cur": None,
           "baseline": base if has_baseline(marker) else None, "account_changed": False}
    if not has_baseline(marker):
        return out
    cur = reading(state) if state.axes else None
    if cur is None:
        return dict(out, reason=REASON_UNMEASURED)
    hit = cur <= base - EARLY_DROP_PP and cur < policy.prepare_pct
    return dict(out, cur=cur, recovered=hit, reason=REASON_RECOVERED if hit else REASON_HOLD,
                account_changed=account_changed(marker, state.account_key))


def probe_rows(sid: str) -> list[dict]:
    """本 sid 的 `park_early_probe` 痕跡列（舊→新；讀不到 ⇒ 空）。"""
    try:
        lines = (endurance_env.trace_dir_peek()[0] / park._SPAWNED_LOG).read_text(  # noqa: SLF001
            encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    rows = []
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict) and rec.get("event") == EV_PROBE and rec.get("sid") == sid:
            rows.append(rec)
    return rows


def status_row(marker: dict, S: dict | None = None) -> str:
    """`park --status` 的 `early_probe:` 一列。`next_probe` 取縫 `S["next_probe"]`（排程器自報）；
    沒有就標 `?`（本 repo 的排程後端只能列名稱、不回下次執行時刻——照實說，不猜）。"""
    S = S or {}
    sid = marker.get("sid", "")
    if not has_baseline(marker):
        return f"early_probe: absent({REASON_NO_BASELINE})"
    last = (probe_rows(sid) or [{}])[-1]
    nxt = S["next_probe"](sid) if callable(S.get("next_probe")) else "?"
    return (f"early_probe: next_probe={nxt} last={last.get('at', 'never')} "
            f"reading={last.get('reading', '?')} baseline={marker[MK_PARKED_PCT]}")


def with_token(lines: list[str], marker: dict, sentinel: tuple[str, str]) -> list[str]:
    """`park` 登記末行追加一個 token：`early_probe=armed`（哨兵在且有基準）｜`absent(原因)`。
    只追加、不改既有 token（QW §7.1 末行字面相容）。"""
    state, why = sentinel
    token = ("armed" if state == "armed" and has_baseline(marker)
             else f"absent({why if state != 'armed' else REASON_NO_BASELINE})")
    return [*lines[:-1], f"{lines[-1]} early_probe={token}"]


def early_view(marker: dict | None, opts) -> dict | None:
    """`park --fire` 的 early 模式（`opts.early`）：把重排次數記成已用盡，讓 QW §7.3 的分支 A
    （主載具活著且未到 ⇒ 重排）落到 `yield_exhausted`、其餘分支照舊（DES I-10）。非 early ⇒ 原樣。
    只是記憶體副本；`parkearly.fire_early` 事後還原磁碟上標記的次數欄。"""
    from . import park_yield  # noqa: PLC0415

    if marker is None or not getattr(opts, "early", False):
        return marker
    return dict(marker, **{park_yield.RESCHEDULES_KEY: park_yield.MAX_RESCHEDULES})


def brief_line(env=None) -> str:
    """SessionStart 一行：有 armed park 的標記、而其探針連續 `UNMEASURED_STREAK` 次量不到 ⇒ 出聲。
    唯讀、任何例外 ⇒ `""`（簡報失敗不得反過來擋 SessionStart）。"""
    try:
        folder = endurance_env.trace_dir_peek()[0] / park.PARK_DIR
        now = datetime.now().astimezone()
        for path in sorted(folder.glob("*.json")):
            marker = park.read_marker(path.stem)
            if not park.yields(marker, now):
                continue
            tail = probe_rows(path.stem)[-UNMEASURED_STREAK:]
            if len(tail) == UNMEASURED_STREAK and all(
                    r.get("reason") == REASON_UNMEASURED for r in tail):
                return (f" sessionctl：session {path.stem[:8]} 的 park 提前恢復探針連續 "
                        f"{UNMEASURED_STREAK} 次量不到額度——到點前不會因額度恢復而提前接手；"
                        f"看狀態：python tools/sessionctl.py park --status "
                        f"--session-id {path.stem}")
    except Exception:  # noqa: BLE001
        return ""
    return ""
