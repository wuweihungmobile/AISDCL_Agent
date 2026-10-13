#!/usr/bin/env python3
"""PRD §11.2 離線配速模擬器（驗收補件）：合成 U5h／U7d／T_rem 序列 ⇒ 真管線，不燒真實額度。"""
# WHY 這支存在、以及它**不是**什麼
# ---------------------------------
# §11.2 要求「離線模擬器餵合成序列、跑完性質測試」。`decide()`＋單調／穩定性質測試已在
# `tools/tests/test_quota_policy.py`，缺的是一支**可重跑、逐項印 PASS／FAIL、數字可貼進
# 驗收紀錄**的獨立載具。本檔的管線＝`quota_gate.quota_gate()` 的離線等價物，三段逐字
# 同序、都是生產函式（不另寫第二份判準）：
#   `quota_policy.decide()` → `quota_availability.evaluate()` → `quota_stability.evaluate()`
# 遲滯狀態檔住臨時目錄（`AUTOSDD_TRACE_DIR` 指過去，跑完清掉）；時鐘是注入的模擬時刻。
#
# 🔴 誠實劃界（讀數字前先讀）：
#   · (a)(b)(c)(d) 是**合成情境**的性質斷言：證明機制在該輸入上的行為，不證明真機的分布。
#   · (e) H1 才是真機母體：從 `quota_burn.jsonl`（量到）＋ `autosdd_quota_degraded.jsonl`
#     （量不到）按時間重建。兩者都是**點事件**，不是連續區間；痕跡住系統暫存，重開機即
#     蒸發——取不到就印「H1 母體不可得」，**不得**拿合成序列頂替（PRD §4.2.4〈H1〉）。
#     (e) 末尾另附一個合成對照組，只驗**比較器自己**有鑑別力，不算 H1 證據。
#   · 「量不到」只取 `no-account-key`／`policy-invalid` 以外的來源（那兩種是量測成功的
#     旁註，不是可得性事件）。
#
# 用法
# ----
#     python tools/probe/pacing_simulator.py --selftest
#     python tools/probe/pacing_simulator.py --selftest \
#         --burn-ledger <jsonl> --degraded-trace <jsonl>
from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import tempfile
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import endurance_env  # noqa: E402
import quota_availability  # noqa: E402
import quota_gate  # noqa: E402
import quota_messages  # noqa: E402
import quota_policy  # noqa: E402
import quota_stability  # noqa: E402

import _stdio_utf8  # noqa: E402,F401  （side effect：強制 stdout/stderr 為 UTF-8）

#: 模擬時鐘起點（固定，結果可重跑）與一個控制週期。週期取 360s：≥ `min_dwell`（300）與
#: 可得性 dwell（360）——更密的週期只會讓放寬更慢，收緊方向本來就不受週期影響。
T0 = datetime(2026, 1, 1, tzinfo=UTC)
CYCLE = timedelta(seconds=360)
#: 不算「量不到」的降級旁註來源（量測本身成功）。
NOT_AN_OUTAGE = frozenset({"no-account-key", "policy-invalid"})


def axes(now: datetime, u5h: float, u7d: float = 10.0, t_rem_min: float = 90.0) -> tuple:
    """兩軸合成讀數：`five_hour` 還剩 `t_rem_min` 分鐘 reset；`seven_day` 五天後。"""
    return (quota_policy.Axis("five_hour", u5h, (now + timedelta(minutes=t_rem_min)).isoformat()),
            quota_policy.Axis("seven_day", u7d, (now + timedelta(days=5)).isoformat()))


class Pipeline:
    """`quota_gate()` 的離線等價物；`hysteresis=False` ⇒ 只看 `decide()`（無狀態的對照組）。"""

    def __init__(self, policy: quota_policy.Policy, *, hysteresis: bool = True) -> None:
        self.policy, self.hysteresis, self._saved = policy, hysteresis, None
        self._tmp = tempfile.TemporaryDirectory(prefix="pacing_sim_")

    def __enter__(self) -> Pipeline:
        self._saved = os.environ.get(endurance_env.TRACE_DIR_ENV)
        os.environ[endurance_env.TRACE_DIR_ENV] = self._tmp.name
        return self

    def __exit__(self, *_exc: object) -> None:
        os.environ.pop(endurance_env.TRACE_DIR_ENV, None)
        if self._saved is not None:
            os.environ[endurance_env.TRACE_DIR_ENV] = self._saved
        self._tmp.cleanup()

    def step(self, now: datetime, rows: tuple, ratio: float | None = None) -> tuple:
        """一個控制週期 ⇒ `(穩定後 cap, 帶別, decide() 原始 cap)`；`rows` 為空＝遙測中斷。"""
        state = (quota_policy.QuotaState(rows, now.isoformat(timespec="seconds"), "sim")
                 if rows else quota_policy.QuotaState((), "", "sim", "sim-outage"))
        decision = quota_policy.decide(state, now, self.policy, ratio)
        if not self.hysteresis:
            return decision.cap, decision.band, decision.cap
        avail = quota_availability.evaluate(
            now, state.usable(), exit_streak=self.policy.availability_exit_streak,
            min_dwell_seconds=self.policy.availability_min_dwell_seconds)
        cap = quota_stability.evaluate(
            decision.cap, decision.band, now, min_dwell_seconds=self.policy.min_dwell_seconds,
            unmeasured=avail.availability == quota_availability.AVAILABILITY_UNMEASURED,
            reset_at=quota_messages.halt_resets_at(decision))
        return cap, decision.band, decision.cap


def changes(caps: list) -> int:
    return sum(1 for a, b in zip(caps, caps[1:]) if a != b)


def rungs(policy: quota_policy.Policy) -> list:
    """band 階梯：生產的 `(帶, horizon)` 組合所能產生的**有限** cap 值（升冪）。"""
    bands = (quota_policy.BAND_NOTICE, quota_policy.BAND_CONVERGE, quota_policy.BAND_PREPARE)
    horizons = (quota_policy.AXIS_NEAR, quota_policy.AXIS_MID, quota_policy.AXIS_FAR)
    return sorted({0} | {quota_policy._cap_for(b, h, policy) for b in bands for h in horizons})


# ── (a) 收斂性 ──────────────────────────────────────────────────────────────
def check_convergence(policy) -> tuple[bool, str]:
    """固定燃燒率（0.01pp／週期，留在 notice 帶）下，從 halt 的 cap=0 出發 ≤10 個週期收斂。"""
    with Pipeline(policy) as pipe:
        t, seq = T0, []
        for _ in range(2):
            seq.append(pipe.step(t, axes(t, 97.0))[0])
            t += CYCLE
        start = len(seq)
        for i in range(30):
            seq.append(pipe.step(t, axes(t, 60.0 + 0.01 * i))[0])
            t += CYCLE
    run = seq[start - 1:]
    last = max((i for i in range(1, len(run)) if run[i] != run[i - 1]), default=0)
    ok = last <= 10 and run[-1] == policy.cap_notice and run[10:] == [run[10]] * len(run[10:])
    return ok, f"起點 cap={run[0]}，最後一次變動在第 {last} 個週期（≤10），終值 {run[-1]}"


# ── (b) 放寬只走 band 階梯、不跳級 ──────────────────────────────────────────
def check_relax_ladder(policy) -> tuple[bool, str]:
    ladder, pcts = rungs(policy), [10 + 8 * i for i in range(11)] + [97, 97]
    pcts += [66] * 12 + [75] * 3 + [66] * 12 + [10]
    with Pipeline(policy) as pipe:
        t, caps = T0, []
        for pct in pcts:
            caps.append(pipe.step(t, axes(t, float(pct)))[0])
            t += CYCLE
    relax = [(a, b) for a, b in zip(caps, caps[1:]) if a is not None and b is not None and b > a]
    bad = [(a, b) for a, b in relax if b > min((r for r in ladder if r > a), default=a)]
    bypass = sum(1 for a, b in zip(caps, caps[1:]) if a is not None and b is None)
    ok = bool(relax) and not bad
    return ok, (f"放寬 {len(relax)} 次、跳級 {len(bad)} 次；階梯 {ladder}；"
                f"free 帶直通 {bypass} 次（設計例外，DEF-200-242）")


# ── (c) 75% 時 cap 由 band 常數保證 ─────────────────────────────────────────
def check_band_constant(policy) -> tuple[bool, str]:
    """U5h=75（converge 帶）：任何 T_rem／U7d／換算比下 cap ≤ cap_converge（配速只准收緊）；窗末
    （T_rem ≤ 60 分，75% 未超前線性預算）且週軸不綁定時**恰為** cap_converge；改常數 cap 跟著變。"""
    n, over, inexact = 0, [], []
    for t_rem in (5.0, 20.0, 60.0, 120.0, 240.0):
        for u7d in (0.0, 30.0, 75.0, 90.0, 97.0):
            for ratio in (None, 0.2, 1.0, 10.0):
                state = quota_policy.QuotaState(axes(T0, 75.0, u7d, t_rem), T0.isoformat(), "sim")
                cap = quota_policy.decide(state, T0, policy, ratio).cap
                n += 1
                if cap is None or cap > policy.cap_converge:
                    over.append((t_rem, u7d, ratio, cap))
                if t_rem <= 60.0 and u7d <= 30.0 and cap != policy.cap_converge:
                    inexact.append((t_rem, u7d, ratio, cap))
    follows = []
    for const in (3, 6):
        state = quota_policy.QuotaState(axes(T0, 75.0, 0.0, 20.0), T0.isoformat(), "sim")
        tuned = replace(policy, cap_converge=const)
        follows.append(quota_policy.decide(state, T0, tuned).cap == const)
    ok = not over and not inexact and all(follows)
    return ok, (f"{n} 組輸入：超過 cap_converge={policy.cap_converge} 者 {len(over)}、"
                f"窗末卻不等於它者 {len(inexact)}；改常數為 3／6 後 cap 連動 {follows}")


# ── (d) 遙測中斷 11 分鐘 ⇒ cap 退到 cap_prepare 以下 ────────────────────────
def check_outage(policy) -> tuple[bool, str]:
    with Pipeline(policy) as pipe:
        t = T0
        for _ in range(6):
            steady = pipe.step(t, axes(t, 60.0))[0]
            t += CYCLE
        seen = []
        for k in range(3):
            seen.append(pipe.step(t + timedelta(seconds=330 * k), ())[:2])
    caps = [cap for cap, _band in seen]
    ok = (all(cap is not None and 1 <= cap <= policy.cap_prepare for cap in caps)
          and all(band == quota_policy.BAND_UNMEASURED for _cap, band in seen)
          and caps == sorted(caps, reverse=True))
    return ok, (f"中斷前 cap={steady}，中斷 0／5.5／11 分鐘的 cap={caps}"
                f"（上限 cap_prepare={policy.cap_prepare}）")


# ── (e) H1：真機母體重建 ────────────────────────────────────────────────────
def _jsonl(path: Path) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows = []
    for line in lines:
        with contextlib.suppress(ValueError):
            if isinstance(row := json.loads(line), dict):
                rows.append(row)
    return rows


def population(burn: Path, degraded: Path) -> list:
    """時間序 `[(時刻, 'M'|'U', 列)]`，截到兩份痕跡**共同涵蓋**的區間（免得一端空白被讀成穩定）。"""
    events = []
    for row in _jsonl(burn):
        with contextlib.suppress(KeyError, TypeError, ValueError):
            events.append((datetime.fromisoformat(row["ts"]), "M", row))
    for row in _jsonl(degraded):
        with contextlib.suppress(KeyError, TypeError, ValueError):
            if row.get("source") not in NOT_AN_OUTAGE:
                events.append((datetime.fromisoformat(row["at"]), "U", row))
    spans = [[e[0] for e in events if e[1] == kind] for kind in "MU"]
    if not all(spans):
        return []
    lo, hi = max(min(s) for s in spans), min(max(s) for s in spans)
    return sorted((e for e in events if lo <= e[0] <= hi), key=lambda e: e[0])


def replay(policy, events: list) -> dict:
    """同一串事件跑兩次：關遲滯（只看 `decide()`）與開遲滯；回逐筆 cap 與未滿 dwell 的放寬數。"""
    out = {}
    for name, on in (("off", False), ("on", True)):
        caps, last, under = [], None, 0
        with Pipeline(policy, hysteresis=on) as pipe:
            for ts, kind, row in events:
                resets = row.get("resets_at") or {}
                rows = () if kind == "U" else tuple(
                    quota_policy.Axis(k, float(v), resets.get(k)) for k, v in row["pct"].items())
                cap = pipe.step(ts, rows)[0]
                if caps and cap != caps[-1]:
                    relax = cap is not None and caps[-1] is not None and cap > caps[-1]
                    under += relax and last is not None and (
                        ts - last).total_seconds() < policy.min_dwell_seconds
                    last = ts
                caps.append(cap)
        out[name], out[name + "_under_dwell"] = caps, under
    return out


def check_h1(policy, burn: Path, degraded: Path) -> tuple[bool | None, str]:
    events = population(burn, degraded)
    if len(events) < 2:
        return None, "H1 母體不可得（痕跡住系統暫存）"
    seq = "".join(e[1] for e in events)
    res = replay(policy, events)
    off, on = changes(res["off"]), changes(res["on"])
    ok = on < off and res["on_under_dwell"] == 0
    first, last = (events[i][0].isoformat(timespec="seconds") for i in (0, -1))
    return ok, (f"{first}～{last} {len(seq)} 個符號、{changes(list(seq))} 次翻動；"
                f"cap 變動 關遲滯={off} 開遲滯={on}；"
                f"dwell 未滿就放寬={res['on_under_dwell']}")


def check_h1_control(policy) -> tuple[bool, str]:
    """比較器自身的鑑別力（合成，**不是** H1 證據）：每 6 分鐘 M／U 交替 ⇒ 開遲滯必須嚴格較少。"""
    events = []
    for i in range(20):
        ts = T0 + timedelta(minutes=6 * i)
        row = {"pct": {"five_hour": 60.0, "seven_day": 10.0}}
        events.append((ts, "U" if i % 2 else "M", row))
    res = replay(policy, events)
    off, on = changes(res["off"]), changes(res["on"])
    return on < off, f"合成 M／U 交替：cap 變動 關遲滯={off} 開遲滯={on}"


def run(burn: Path, degraded: Path) -> int:
    policy = quota_policy.load_policy({})[0]
    checks = (
        ("a", "收斂性：固定燃燒率 10 個週期內 cap 不再變動", lambda: check_convergence(policy)),
        ("b", "放寬只走 band 階梯、不跳級", lambda: check_relax_ladder(policy)),
        ("c", "U5h=75% 時 cap 由 band 常數保證", lambda: check_band_constant(policy)),
        ("d", "遙測中斷 11 分鐘 ⇒ cap ≤ cap_prepare", lambda: check_outage(policy)),
        ("e", "H1 真機母體：開遲滯的 cap 變動嚴格少於關遲滯",
         lambda: check_h1(policy, burn, degraded)),
        ("e0", "H1 比較器對照組（合成，非證據）", lambda: check_h1_control(policy)),
    )
    verdicts = []
    for ident, title, fn in checks:
        ok, detail = fn()
        verdicts.append(ok)
        print(f"{'N/A ' if ok is None else 'PASS' if ok else 'FAIL'} ({ident}) {title} — {detail}")
    failed = sum(v is False for v in verdicts)
    print(f"合計：PASS {sum(v is True for v in verdicts)}／FAIL {failed}／N/A "
          f"{sum(v is None for v in verdicts)}（共 {len(verdicts)} 項）")
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--selftest", action="store_true", help="跑全部性質斷言並逐項印 PASS／FAIL")
    parser.add_argument("--burn-ledger", type=Path, default=None,
                        help="H1：落款檔（預設＝生產路徑）")
    parser.add_argument("--degraded-trace", type=Path, default=None,
                        help="H1：量不到的降級痕跡（預設＝生產路徑，住系統暫存）")
    args = parser.parse_args(argv)
    if not args.selftest:
        parser.print_usage(sys.stderr)
        return 2
    return run(args.burn_ledger or quota_gate.burn_ledger_path(),
               args.degraded_trace or quota_gate.quota_trace_path())


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
