#!/usr/bin/env python3
"""PRD §11.8 24 小時端到端（模擬法，驗收補件）：模擬時鐘一分鐘一拍，真政策管線＋真接力狀態機。"""
# WHY 用模擬法、以及它證明什麼
# ----------------------------
# §11.8 要「24 小時連續、跨 ≥4 次 5 小時視窗重置」——真跑要 24 小時牆鐘。本檔把 1440 拍壓成秒級：
#   · 真程式（不重寫第二份判準）：`pacing_simulator.Pipeline`＝`quota_gate()` 的離線等價物
#     （`quota_policy.decide` → `quota_availability.evaluate` → `quota_stability.evaluate`）；
#     接力用 `relay_machine.apply_reset_at`／`resolve`／`made_progress`／`max_spawns`。
#   · 合成世界：`session`／`five_hour` 在每個 5h 視窗內從 0 線性升到 100%（`--burn-minutes`
#     分鐘燒滿）、翻頁點 5／10／15／20h 歸零；`seven_day` 緩升（`--u7-slope` pp／天）。
#   · 工作模型（模型層，不是真 agent）：任務佇列、固定時長；cap 為 `None` 或 >0 才推進；進
#     prepare 帶寫 checkpoint 旗標（＝被預告、進入收尾姿態）；halt 帶即停——有旗標才來得及做最終
#     存檔（乾淨），無旗標＝髒污。翻頁後 `RESET_SKEW_SECONDS`（planner SSOT）才醒，醒來由
#     `resolve()` 判能否續跑（RELAY_NEXT 才續；`made_progress` 看上一視窗有沒有進度）。
# 🔴 誠實劃界（讀數字前先讀）：
#   · **這是模擬時鐘，不是真的 24 小時牆鐘**；合成軸不是真機分布，證明的是「真政策＋真狀態機在
#     這組輸入下的行為」。真正的整合軸住引擎層 `AutoClaude/tests/integration/
#     test_day_long_resume_prd11_8.py`（真 AutoResumeService 多次撞線續跑）。
#   · 接力判定在本檔於「醒來當下」以現況 band 評估；真 planner 在續跑窗**收尾**（settle_window）
#     評估。輸入相同（上一窗 handback／進度／seq／band），時機不同——照實寫。
#   · 未模擬單次 spawn 3600s 牆鐘上限與每視窗 `max_spawns`（出廠 2）：真無人接力每視窗至多 2 個
#     spawn，有效工作佔比上限遠低於本模擬（本檔≈每視窗一個不超時的續跑）。
#   · free 帶 cap 恆為 `None`（直通，DEF-200-242；PRD §11.2 註記 C1）⇒「翻頁後第一拍 cap ≤
#     cap_notice」不是機械保證，本檔對該項只印不擋。
# `--target-ratio` 出廠值 0.80 的來源：出廠燃燒率（270 分燒滿）下，政策理論值＝每窗 95% 水位前全速
# 工作、扣醒來延遲，實測約 0.875；取其 90% 四捨五入到 0.05。換燃燒率要連帶重訂目標。
#
# PRD §11.8 句 ↔ 斷言：「24 小時連續、跨 ≥4 次重置」→ n；「0 次非預期任務截斷」→ 1；「0 次髒污
# 工作區」→ 2；「U7d 未觸及 WEEKLY_HALT」→ 3；「有效工作時間佔比達成設定目標」→ 4；接力鏈每次
# 翻頁後續得起來 → 5；翻頁後首拍 cap → 6（只印不擋）。控制組＝刻意注入缺陷，驗斷言會紅。
#
# 用法：python tools/probe/day_long_relay_sim.py --selftest   # 斷言＋控制組
#       python tools/probe/day_long_relay_sim.py --run         # 斷言＋逐視窗表
from __future__ import annotations

import argparse
import math
import sys
import tempfile
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import quota_policy  # noqa: E402
import relay_machine  # noqa: E402
from pacing_simulator import Pipeline  # noqa: E402

import _stdio_utf8  # noqa: E402,F401  （side effect：強制 stdout/stderr 為 UTF-8）
import session_resume_planner as planner  # noqa: E402

T0 = datetime(2026, 1, 1, tzinfo=UTC)         # 模擬起點（固定 ⇒ 可重跑）
MINUTES, WINDOW = 24 * 60, 300                # 24 小時、一個 5 小時視窗（分鐘）
TASK_MIN = 25                                 # 每個任務固定 25 分鐘
WAKE_LAG = math.ceil(planner.RESET_SKEW_SECONDS / 60)   # 翻頁後醒來延遲（SSOT，不寫死）
U7D_START = 40.0
PRD_WEEKLY_HALT = 90.0    # PRD 原文 WEEKLY_HALT_PERCENT（實作面週軸 halt 同為 95，註記 C8）


def axes_at(minute: int, burn: int, u7_slope: float) -> tuple:
    """第 `minute` 拍的三軸讀數：5h 軸線性升、視窗翻頁歸零；7d 軸緩升（resets_at 一律未來）。"""
    window, offset = divmod(minute, WINDOW)
    end = (T0 + timedelta(minutes=(window + 1) * WINDOW)).isoformat()
    pct = min(100.0, 100.0 * offset / burn)
    week = U7D_START + u7_slope * minute / MINUTES
    return (quota_policy.Axis("session", pct, end), quota_policy.Axis("five_hour", pct, end),
            quota_policy.Axis("seven_day", week, (T0 + timedelta(days=7)).isoformat()))


class Worker:
    """任務佇列工人（模型層）。`flag`＝被預告（prepare 帶）⇒ halt 時來得及最終存檔。"""

    def __init__(self, *, never_flag: bool = False) -> None:
        self.never_flag, self.idx, self.done, self.running = never_flag, 0, 0, True
        self.flag, self.flag_window, self.saved = False, -1, False
        self.work, self.completed, self.halts, self.cuts, self.restarts = 0, [], [], [], 0

    def step(self) -> None:
        self.done, self.work = self.done + 1, self.work + 1
        if self.done == TASK_MIN:
            self.completed.append(self.idx)
            self.idx, self.done = self.idx + 1, 0

    def warn(self, window: int) -> None:
        if self.running and self.flag_window != window and not self.never_flag:
            self.flag, self.flag_window = True, window

    def halt(self, minute: int, band: str, prepare_seen: bool) -> None:
        self.halts.append({"minute": minute, "band": band, "flag": self.flag,
                           "prepare_seen": prepare_seen, "task": self.idx})
        self.saved, self.running = self.flag, False

    def cut(self, minute: int, band: str) -> None:
        """halt 以外的中斷（控制組注入）：進度作廢、當前任務從頭來過。"""
        self.cuts.append({"minute": minute, "band": band})
        self.done = 0

    def resume(self) -> None:
        if not self.saved:                    # 髒污：沒有最終存檔 ⇒ 當前任務進度作廢
            self.restarts, self.done = self.restarts + 1, 0
        self.flag, self.running = False, True


def simulate(*, burn: int = 270, u7_slope: float = 15.0, mutate: str | None = None) -> dict:
    """跑 1440 拍，回原始痕跡（斷言只讀它，見 `judge`）。`mutate`＝控制組要注入的缺陷。"""
    policy = quota_policy.load_policy({})[0]
    if mutate == "skip-prepare":
        policy = replace(policy, prepare_pct=policy.halt_pct)       # 政策缺陷：跳過預告帶
    worker = Worker(never_flag=mutate == "no-checkpoint")
    flips, wakes, windows, seen = [], [], {}, set()
    with Pipeline(policy) as pipe, tempfile.TemporaryDirectory(prefix="day_long_sim_") as raw:
        handback = Path(raw) / "handback.md"
        handback.write_text("# 交接\n\n## 下一步指令\n- 繼續任務佇列\n", encoding="utf-8",
                            newline="\n")
        relay = {"handback_verdict": "written", "handback_path": str(handback),
                 "files_changed": 0, "relay_seq": 0, "relay_no_progress_streak": 0, "reset_at": ""}
        window_work = 0
        for minute in range(MINUTES):
            window, offset = divmod(minute, WINDOW)
            now = T0 + timedelta(minutes=minute)
            cap, band, _raw = pipe.step(now, axes_at(minute, burn, u7_slope))
            if offset == 0 and minute:                               # 視窗翻頁
                flips.append({"minute": minute, "first_cap": cap, "first_band": band})
                relay["files_changed"] = 0 if (mutate == "no-progress" and window == 2) \
                    else window_work
                relay_machine.apply_reset_at(relay, (T0 + timedelta(
                    minutes=(window + 1) * WINDOW)).isoformat())
                window_work, seen = 0, set()
            seen.add(band)
            windows.setdefault(window, {}).setdefault(band, minute)
            if offset == WAKE_LAG and window and not worker.running:  # 醒來：resolve 判能否續跑
                got = relay_machine.resolve(relay, band, max_spawns=relay_machine.max_spawns(),
                                            no_progress_limit=relay_machine.no_progress_limit())
                outcome = got.pop("next_state")
                relay.update(got)
                wakes.append({"minute": minute, "outcome": outcome, "made": relay_machine
                              .made_progress("written", int(relay["files_changed"]))})
                if outcome == relay_machine.STATE_RELAY_NEXT:
                    worker.resume()
            if band == quota_policy.BAND_PREPARE:                    # 進 prepare：預告 ⇒ 寫旗標
                worker.warn(window)
            if mutate == "kill" and minute == 130 and worker.running:
                worker.cut(minute, band)
            if worker.running and cap == 0:
                worker.halt(minute, band, quota_policy.BAND_PREPARE in seen)
            elif worker.running:
                worker.step()
                window_work += 1
    return {"worker": worker, "flips": flips, "wakes": wakes, "windows": windows,
            "u7_max": max(a.pct for m in range(MINUTES)
                          for a in axes_at(m, burn, u7_slope) if a.kind == "seven_day"),
            "halt_pct": policy.halt_pct, "cap_notice": policy.cap_notice}


def judge(sim: dict, target: float) -> list[tuple[str, str, bool, str]]:
    """痕跡 ⇒ `[(id, 標題, 通過?, 實測細節)]`；6 號只印不擋（通過欄恆 True）。"""
    worker, flips, wakes = sim["worker"], sim["flips"], sim["wakes"]
    free_notice = (quota_policy.BAND_FREE, quota_policy.BAND_NOTICE)
    trunc = len(worker.cuts) + sum(1 for h in worker.halts
                                   if h["band"] in free_notice or not h["prepare_seen"])
    dirty = sum(1 for h in worker.halts if not h["flag"])
    ratio = worker.work / MINUTES
    first_caps = [f["first_cap"] for f in flips]
    over = [c for c in first_caps if c is None or c > sim["cap_notice"]]
    return [
        ("n", "24 小時連續、跨 ≥4 次 5 小時視窗重置", MINUTES == 1440 and len(flips) >= 4,
         f"{MINUTES} 拍（模擬 {MINUTES // 60} 小時）、翻頁 {len(flips)} 次（拍 "
         f"{[f['minute'] for f in flips]}）"),
        ("1", "0 次非預期任務截斷（free／notice 被中斷、或 halt 前沒經過 prepare 帶）",
         trunc == 0, f"截斷 {trunc} 次（halt {len(worker.halts)} 次、halt 以外中斷 "
         f"{len(worker.cuts)} 次）"),
        ("2", "0 次髒污工作區（任何 halt 當下 checkpoint 旗標為真）", dirty == 0,
         f"髒污 {dirty} 次、續跑後進度作廢 {worker.restarts} 次"),
        ("3", "U7d 未觸及 WEEKLY_HALT（seven_day 最大值 < 實作 halt 門檻與 PRD 原文 90%）",
         sim["u7_max"] < min(sim["halt_pct"], PRD_WEEKLY_HALT),
         f"seven_day 最大 {sim['u7_max']:.1f}% < min({sim['halt_pct']}%, {PRD_WEEKLY_HALT}%)"),
        ("4", f"有效工作時間佔比達成設定目標（≥{target:.2f}）", ratio >= target,
         f"工作 {worker.work} 分／{MINUTES} 分＝{ratio:.3f}"
         f"（完成任務 {len(worker.completed)} 個）"),
        ("5", "接力鏈每次翻頁後續得起來（resolve＝RELAY_NEXT 且 made_progress）",
         len(wakes) >= 4 and all(w["outcome"] == relay_machine.STATE_RELAY_NEXT and w["made"]
                                 for w in wakes),
         f"醒來 {len(wakes)} 次：{sorted({w['outcome'] for w in wakes})}、皆有進度 "
         f"{all(w['made'] for w in wakes)}"),
        ("6", "（只印不擋）翻頁後首拍 cap ≤ cap_notice——free 直通 None 為設計（C1／DEF-200-242）",
         True, f"首拍 cap={first_caps}（不設限或 >{sim['cap_notice']} 者 {len(over)} 次）"),
    ]


# 控制組：刻意注入缺陷 ⇒ 對應斷言**必須**轉紅（紅綠自證；缺了它斷言可能只是裝飾）。
CONTROLS = {"skip-prepare": ({}, {"1", "2"}), "no-checkpoint": ({}, {"2"}),
            "kill": ({}, {"1"}), "no-progress": ({}, {"4", "5"}),
            "weekly": ({"u7_slope": 70.0}, {"3", "4", "5"})}


def print_table(sim: dict) -> None:
    print("視窗  各帶首次進入的拍（相對視窗起點） ｜ 翻頁後醒來判定（resolve）")
    wakes = {w["minute"] // WINDOW: w["outcome"] for w in sim["wakes"]}
    for window, bands in sorted(sim["windows"].items()):
        cells = "、".join(f"{b}@{m - window * WINDOW}" for b, m in
                         sorted(bands.items(), key=lambda kv: kv[1]))
        print(f"w{window}  {cells} ｜ {wakes.get(window, '（起跑窗／無醒來）')}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--selftest", action="store_true", help="斷言 ＋ 控制組（刻意注入缺陷）")
    parser.add_argument("--run", action="store_true", help="斷言 ＋ 逐視窗表")
    parser.add_argument("--target-ratio", type=float, default=0.80, help="有效工作佔比目標")
    parser.add_argument("--burn-minutes", type=int, default=270, help="5h 軸燒滿 100%% 的分鐘數")
    parser.add_argument("--u7-slope", type=float, default=15.0, help="seven_day 每天上升 pp")
    args = parser.parse_args(argv)
    if not (args.selftest or args.run):
        parser.print_usage(sys.stderr)
        return 2
    sim = simulate(burn=args.burn_minutes, u7_slope=args.u7_slope)
    if args.run:
        print_table(sim)
    print("（模擬時鐘 24 小時、一分鐘一拍，不是真牆鐘；真政策管線＋真接力狀態機＋模型層工人）")
    verdicts = judge(sim, args.target_ratio)
    for ident, title, ok, detail in verdicts:
        print(f"{'PASS' if ok else 'FAIL'} ({ident}) {title} — {detail}")
    failed = sum(not ok for _i, _t, ok, _d in verdicts)
    if args.selftest:
        for name, (kwargs, expect) in CONTROLS.items():
            sim_c = simulate(burn=args.burn_minutes, mutate=name, **{"u7_slope": 15.0, **kwargs})
            red = {i for i, _t, ok, _d in judge(sim_c, args.target_ratio) if not ok}
            failed += red != expect
            print(f"{'PASS' if red == expect else 'FAIL'} (控制組 {name}) 預期轉紅 "
                  f"{sorted(expect)}、實際轉紅 {sorted(red)}")
    print(f"合計：{'全數符合' if not failed else f'{failed} 項不符'}（斷言 {len(verdicts)} 項"
          f"{'＋控制組 ' + str(len(CONTROLS)) + ' 組' if args.selftest else ''}）")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
