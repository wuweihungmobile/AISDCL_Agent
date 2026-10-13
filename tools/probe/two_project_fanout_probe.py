#!/usr/bin/env python3
"""PRD §11.7 兩專案同時派工（驗收補件）：兩個行程搶同一本派發帳，成功總和不得超過 cap。"""
# WHY 這支探針量的是什麼
# -----------------------
# §11.7：「同帳號同時啟動兩個專案的 Daemon，兩者併發總和不超過單一 Daemon 情境的上限」。本機上
# 兩個專案的 hook 共用**同一本機器級派發帳**（`quota_gate.fanout_ledger_path()`），而 cap 的
# 執法點是 `quota_gate.quota_gate()` 裡三步：先記帳（`claim_dispatch`，`O_EXCL` 建目錄項）、
# 再數（`live_dispatches`）、`live <= cap` 才放行，否則撤銷自己那一筆。本探針用**兩個獨立
# 行程**（`spawn`，各自 import 一份模組；`Barrier` 對齊每一回合的起跑）把同一個判準打到競態
# 邊緣，cap 由參數注入（預設 2）：
#   · 安全面（硬判決）：每回合兩行程「成功」總和 ≤ cap；
#   · 活性面（資訊）：總和 < cap 的回合＝瞬時幽靈佔位造成的暫時過度擋（對方剛建、尚未撤銷的
#     那一筆被算進 live）；每行程重試 `--attempts` 次，數字只報不判。
#
# 🔴 誠實劃界：
#   · 本探針複製了 `quota_gate()` 那三步的**形狀**（不是整個 hook：整個 hook 會讀額度快取、
#     可能打端點，那是另一個量測）。複製必有漂移風險 ⇒ 開跑前先檢查生產函式的原始碼仍是
#     claim → count → `live <= cap` → release 同序；不同序即 FAIL，不去猜新形狀。
#   · 成功的派發不撤銷（模擬「同一視窗內都還活著」），派發帳住臨時目錄、跑完清掉。
#   · 對照組（探針自證有鑑別力）：同一支 harness 改跑舊的「先數再記」判準（count → 讓出
#     一個時間片 → claim，cap 取 cap+1 以留出兩行程同時通過的空間）⇒ 必須量得到超過 cap 的
#     回合；量不到＝harness 沒有抓競態的能力，上面的 PASS 就不具意義，整支判 FAIL。
#   · 驗的是**同機兩行程**；跨機器各有各的派發帳，本探針結構上看不到（PRD §11.7 的「同帳號」
#     跨機情境要靠帳號層級額度端點，那是 T5 的事）。
#
# 用法
# ----
#     python tools/probe/two_project_fanout_probe.py
#     python tools/probe/two_project_fanout_probe.py --cap 2 --attempts 50 --rounds 30
from __future__ import annotations

import argparse
import inspect
import multiprocessing
import shutil
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import quota_gate  # noqa: E402

import _stdio_utf8  # noqa: E402,F401  （side effect：強制 stdout/stderr 為 UTF-8）

#: 生產 `quota_gate()` 裡那四個步驟的出現順序（原始碼片段；順序即判準）。
_PRODUCTION_STEPS = ("entry = claim_dispatch(root, now)", "live = live_dispatches(root, now)",
                     "if live <= cap:", "release_dispatch(entry)")


def production_shape_ok() -> bool:
    """生產函式仍是「記帳 → 數 → ≤cap 放行 → 撤銷」同序（本探針複製的就是這個形狀）。"""
    src = inspect.getsource(quota_gate.quota_gate)
    spots = [src.find(step) for step in _PRODUCTION_STEPS]
    return all(i >= 0 for i in spots) and spots == sorted(spots)


def attempt(root: Path, cap: int) -> bool:
    """一次派發嘗試＝`quota_gate()` 的三步判準；`True`＝放行（留在帳上），`False`＝撤銷。"""
    now = datetime.now().astimezone()
    entry = quota_gate.claim_dispatch(root, now)
    if quota_gate.live_dispatches(root, now) <= cap:
        return True
    quota_gate.release_dispatch(entry)
    return False


def attempt_check_then_claim(root: Path, cap: int) -> bool:
    """對照組：舊的「先數再記」——數到還有空位就讓出時間片再記帳，兩行程會同時通過。"""
    now = datetime.now().astimezone()
    if quota_gate.live_dispatches(root, now) >= cap:
        return False
    time.sleep(0.002)
    return quota_gate.claim_dispatch(root, now) is not None


def worker(base: str, cap: int, attempts: int, rounds: int, barrier, out, broken: bool) -> None:
    """一個「專案」：每回合等 Barrier 對齊後，對該回合的派發帳連搶 `attempts` 次。"""
    step = attempt_check_then_claim if broken else attempt
    ok_per_round = []
    for r in range(rounds):
        root = Path(base) / f"round-{r}"
        barrier.wait()
        ok_per_round.append(sum(step(root, cap) for _ in range(attempts)))
    out.put(ok_per_round)


def race(cap: int, attempts: int, rounds: int, broken: bool = False) -> list[list[int]]:
    """起兩個行程（spawn）打同一串派發帳，回 `[行程A 逐回合成功數, 行程B 逐回合成功數]`。"""
    base = tempfile.mkdtemp(prefix="two_project_fanout_")
    try:
        ctx = multiprocessing.get_context("spawn")
        barrier, out = ctx.Barrier(2), ctx.Queue()
        args = (base, cap, attempts, rounds, barrier, out, broken)
        procs = [ctx.Process(target=worker, args=args) for _ in range(2)]
        for proc in procs:
            proc.start()
        counts = [out.get(timeout=120) for _ in procs]
        for proc in procs:
            proc.join(timeout=30)
    finally:
        shutil.rmtree(base, ignore_errors=True)
    return counts


def run(cap: int, attempts: int, rounds: int) -> int:
    shape = production_shape_ok()
    print(f"production 判準形狀（claim → count → ≤cap 放行 → release，同序）："
          f"{'PASS' if shape else 'FAIL'}")
    if not shape:
        print("  quota_gate.quota_gate() 的派發判準已與本探針複製的形狀不同——先改探針再下結論")
        return 1
    counts = race(cap, attempts, rounds)
    totals = [a + b for a, b in zip(*counts)]
    over, under = sum(t > cap for t in totals), sum(t < cap for t in totals)
    print(f"兩個行程（spawn、Barrier 對齊）：cap={cap}、每行程每回合 {attempts} 次、{rounds} 回合")
    for r in range(min(3, rounds)):
        print(f"  回合 {r + 1}：行程A 成功 {counts[0][r]}、行程B 成功 {counts[1][r]}"
              f" ⇒ 合計 {totals[r]}")
    print(f"各行程累計成功：A={sum(counts[0])} B={sum(counts[1])}；每回合合計 min={min(totals)} "
          f"max={max(totals)}；超過 cap 的回合 {over}；不足 cap 的回合 {under}"
          "（資訊：瞬時幽靈佔位）")
    safe = over == 0
    print(f"{'PASS' if safe else 'FAIL'} 兩行程成功總和 ≤ cap={cap}（{rounds} 回合）")
    ctl_cap = cap + 1
    ctl = [a + b for a, b in zip(*race(ctl_cap, 3, 10, broken=True))]
    caught = sum(t > ctl_cap for t in ctl)
    print(f"{'PASS' if caught else 'FAIL'} 對照組（先數再記）量得到超過 cap={ctl_cap} 的回合："
          f"{caught}/10（合計 max={max(ctl)}）")
    return 0 if safe and caught else 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--cap", type=int, default=2, help="注入的 cap（預設 2）")
    parser.add_argument("--attempts", type=int, default=50, help="每行程每回合的搶佔次數")
    parser.add_argument("--rounds", type=int, default=30, help="回合數（每回合一本新派發帳）")
    args = parser.parse_args(argv)
    if min(args.cap, args.attempts, args.rounds) < 1:
        parser.error("--cap／--attempts／--rounds 都必須 ≥ 1")
    return run(args.cap, args.attempts, args.rounds)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
