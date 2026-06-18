"""AutoSDD improving_35 W-35-1 — mutation baseline 多模組並存鎖定契約測試。

對應 [SD09_Execution_Guide.md W1 T1-B8](../../docs/05_development/SD09_Execution_Guide.md)
（GoalSynthesis mutation pilot 上 nightly 後，與既鎖 TokenGuard 並存的回歸保護）
與 [ADR-SD08-002 §2.4 + ADR-SD09-009 §5.5](../../docs/04_planning/ADR/ADR-SD08-002-mutation-baseline.md)。

定位（與既有測試不重疊）：
  - tests/contract/test_mutation_baseline_lock.py / tests/tools/test_mutation_baseline_lock.py
    多在 should_lock 純函數層或「單模組 run()」；本檔聚焦「**兩模組並存於同一份
    .mutation_history.jsonl／.mutation_baseline.toml、經 run() 端到端 + load_module_history
    篩選**」的整合層契約——這正是 W1 GoalSynthesis pilot 上 nightly 後與既鎖 TokenGuard
    並存的回歸缺口。
  - should_lock(history, module) 用 history[-7:] 取 tail，**不自行 filter module**（見
    mutation_baseline_lock.py:326）；模組隔離真正機制是 load_module_history(path, module)
    先篩選。故本檔以 load_module_history / run() 為對象驗證隔離。

≥ 4 case（T1-B8 對應）：
  1. 兩模組各自連續達標 → 經 run() 各自獨立鎖定，baseline 兩行並存（不互踩）。
  2. 共用 history 檔交錯兩模組紀錄 → load_module_history 篩選隔離 + 各自 should_lock。
  3. 一模組單日抖動跌破門檻 → 不鎖；另一模組達標仍鎖（隔離不被拖累）。
  4. 同一 kill_rate 落在兩模組 effective threshold 之間 → per-module 目標差異正確套用。

註：
  - 全程以 run(..., source_path=<tmp mock dir>) 注入 mock 模組目錄，**不依賴真實
    _MODULE_PATHS 佈局**——既保測試穩健（Rule 9），亦迴避本輪發現的 DEF-35-001
    （autoclaude/plugins/goal_synthesis 為單檔非目錄，_MODULE_PATHS 當目錄 → compute_source_sha256
    回 'unknown'；該配置缺陷 routed W1 執行期修，本檔不把 bug 釘成期望行為）。
  - T1-B8 字面第 4 項「模組間 LRU 順序」屬 ci.yml 三 cron active-module 輪替（排程層、W1
    執行期），baseline_lock 純函數層無 LRU 機制；本檔以「per-module 目標差異隔離」覆蓋等價的
    模組區分語意，LRU 輪替留 W1 執行期（誠實標示，不偽造覆蓋）。
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from tools.mutation_baseline_lock import (
    EXTRA_TOLERANCE,
    TARGETS,
    TOLERANCE,
    load_module_history,
    read_baseline,
    run,
    should_lock,
)


def _effective(module: str) -> float:
    """模組 effective threshold = target - TOLERANCE - EXTRA_TOLERANCE（ADR-SD09-009 §5.5）。"""
    return TARGETS[module] - TOLERANCE - EXTRA_TOLERANCE


def _write_mutmut_log(
    path: Path, killed: int, survived: int, timeout: int = 0, suspicious: int = 0
) -> None:
    """模擬 mutmut emoji results（無 marker → parse_mutmut_log fallback 取最後一筆；
    與既有 contract test helper 同格式）。"""
    path.write_text(
        f"""Legend for output:
🎉 Killed mutants. The goal is for everything to end up in this bucket.
🙁 Survived. This means your tests need to be expanded.

🎉 Killed ({killed})
🙁 Survived ({survived})
⏰ Timeout ({timeout})
🤔 Suspicious ({suspicious})
🔇 Skipped (0)
""",
        encoding="utf-8",
    )


def _preload(history_path: Path, module: str, rates: list[float], sha_prefix: str) -> None:
    """以 append 模式預灌某模組歷史；日期由今日 UTC 倒推 len(rates) 天（避免 M-05 同日去重），
    每筆附 unique source_sha256（滿足紀律 #12）。多模組交錯呼叫不互相覆寫。"""
    today = _dt.datetime.now(tz=_dt.timezone.utc).date()
    n = len(rates)
    with history_path.open("a", encoding="utf-8") as f:
        for i, rate in enumerate(rates):
            day = today - _dt.timedelta(days=n - i)
            rec = {
                "timestamp": f"{day.isoformat()}T02:00:00+00:00",
                "module": module,
                "kill_rate": rate,
                "counts": {"killed": int(rate * 100), "survived": int((1 - rate) * 100)},
                "source_sha256": f"{sha_prefix}{i:09d}",
            }
            f.write(json.dumps(rec) + "\n")


def _make_module_dir(base: Path, name: str, content: str) -> Path:
    """建 mock 模組目錄含一支 .py，使 compute_source_sha256 回真實 16-char sha（非 unknown）。"""
    d = base / name
    d.mkdir()
    (d / f"{name}.py").write_text(content, encoding="utf-8")
    return d


# ====================== T1-B8 必備 4 case ======================


def test_two_modules_lock_independently_via_run(tmp_path: Path) -> None:
    """case 1：goal_synthesis 與 token_guard 各自連續 7 次達標 → 經 run() 端到端各自鎖定，
    共用 baseline 檔兩行並存且互不干擾。

    為何重要：W1 GoalSynthesis 上 nightly 時 TokenGuard 可能已鎖定；兩模組共用
    .mutation_baseline.toml，若 write_baseline 非 per-module upsert 會互相覆蓋 → 既鎖
    TokenGuard baseline 遺失。本 case 鎖定「並存不互踩」這一回歸風險。
    """
    history = tmp_path / ".mutation_history.jsonl"
    baseline = tmp_path / ".mutation_baseline.toml"
    gs_dir = _make_module_dir(tmp_path, "gs_src", "g = 1\n")
    tg_dir = _make_module_dir(tmp_path, "tg_src", "t = 2\n")

    # 預灌各 6 筆達標（GS ≥ 0.63 用 0.66；TG ≥ 0.68 用 0.72），交錯於同一 history
    _preload(history, "goal_synthesis", [0.66] * 6, "gspre")
    _preload(history, "token_guard", [0.72] * 6, "tgpre")

    gs_log = tmp_path / "gs.log"
    _write_mutmut_log(gs_log, killed=66, survived=34)  # 0.66
    tg_log = tmp_path / "tg.log"
    _write_mutmut_log(tg_log, killed=72, survived=28)  # 0.72

    r_gs = run("goal_synthesis", gs_log, history, baseline, source_path=gs_dir)
    r_tg = run("token_guard", tg_log, history, baseline, source_path=tg_dir)

    assert r_gs["status"] == "locked"
    assert r_tg["status"] == "locked"
    locked = read_baseline(baseline)
    assert "goal_synthesis" in locked and "token_guard" in locked
    assert locked["goal_synthesis"] >= _effective("goal_synthesis")
    assert locked["token_guard"] >= _effective("token_guard")


def test_shared_history_file_module_isolation(tmp_path: Path) -> None:
    """case 2：同一 history 檔交錯兩模組各 7 筆達標 → load_module_history 篩選隔離，
    且各自 should_lock 為 True（tail 不被他模組紀錄污染）。

    為何重要：should_lock 用 history[-7:] 不自行 filter module；若上游漏呼叫
    load_module_history 直接傳交錯 list，tail7 會混入他模組 → 假鎖/假拒。本 case 鎖定
    「共用檔 → 篩選 → 鎖定」的正確管線。
    """
    history = tmp_path / ".mutation_history.jsonl"
    _preload(history, "goal_synthesis", [0.66] * 7, "gs")
    _preload(history, "token_guard", [0.72] * 7, "tg")

    gs_hist = load_module_history(history, "goal_synthesis")
    tg_hist = load_module_history(history, "token_guard")

    assert len(gs_hist) == 7 and all(r["module"] == "goal_synthesis" for r in gs_hist)
    assert len(tg_hist) == 7 and all(r["module"] == "token_guard" for r in tg_hist)
    assert should_lock(gs_hist, "goal_synthesis")[0] is True
    assert should_lock(tg_hist, "token_guard")[0] is True


def test_one_module_dip_does_not_block_other(tmp_path: Path) -> None:
    """case 3：token_guard 含單日抖動跌破門檻 → 不鎖；goal_synthesis 全達標 → 仍鎖。

    為何重要：兩模組 nightly 共用 history，一模組的抖動不得波及另一模組的鎖定判定
    （隔離性）；證明 per-module tail 與門檻判定彼此獨立。
    """
    history = tmp_path / ".mutation_history.jsonl"
    _preload(history, "goal_synthesis", [0.66] * 7, "gs")
    _preload(history, "token_guard", [0.72] * 6 + [0.50], "tg")  # 第 7 筆抖動跌破

    gs_hist = load_module_history(history, "goal_synthesis")
    tg_hist = load_module_history(history, "token_guard")

    assert should_lock(gs_hist, "goal_synthesis")[0] is True
    assert should_lock(tg_hist, "token_guard")[0] is False


def test_per_module_threshold_applied_distinctly() -> None:
    """case 4：同一 kill_rate 0.65 落在 goal_synthesis(eff 0.63) 與 token_guard(eff 0.68)
    之間 → GS 鎖定、TG 拒鎖。驗證 per-module TARGETS 正確套用（取代不存在的 LRU 順序語意）。

    為何重要：多模組共用同一 should_lock，門檻必須依 module 取 TARGETS[module]，不可用單一
    全域門檻；否則 GoalSynthesis(70%) 會被誤用 TokenGuard(75%) 門檻致永遠無法鎖定。
    """
    assert abs(_effective("goal_synthesis") - 0.63) < 1e-9
    assert abs(_effective("token_guard") - 0.68) < 1e-9

    gs_hist = [
        {"module": "goal_synthesis", "kill_rate": 0.65, "source_sha256": f"gs{i:013d}"}
        for i in range(7)
    ]
    tg_hist = [
        {"module": "token_guard", "kill_rate": 0.65, "source_sha256": f"tg{i:013d}"}
        for i in range(7)
    ]

    assert should_lock(gs_hist, "goal_synthesis")[0] is True, "0.65 ≥ GS eff 0.63 → 應鎖"
    assert should_lock(tg_hist, "token_guard")[0] is False, "0.65 < TG eff 0.68 → 應拒鎖"
