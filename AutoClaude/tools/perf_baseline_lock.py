"""SD_09 W2-#1 — perf baseline 連續 7 次 samples ≥ 20 達標鎖定工具。

對應 [ADR-SD08-003 v1.1 §2.6](../docs/04_planning/ADR/ADR-SD08-003-perf-regression-policy.md)：
    - samples ≥ 20 才可寫入 .perf_baseline.toml
    - main branch nightly 連續 7 次達標即可 overwrite baseline
    - 重大重構後手動 unlock + recapture（--reset 旗標）

職責：
    1. 讀 perf_results.json（pytest 跑 perf tests 產出，conftest 寫入）
    2. 同日去重 append 至 .perf_history.jsonl（仿 mutation_baseline_lock M-05）
    3. 若連續 CONSECUTIVE_RUNS 次達標（相對舊 baseline 增量 < BLOCK 15%）
       → 寫 .perf_baseline.toml（每場景取 7 次中最保守 p95，即 max）
    4. 否則僅累積觀察期紀錄

退出碼：
    0  累積中（observing）/ 已鎖定（locked）/ 無 baseline 首次播種
    1  perf_results.json 不存在或 samples < MIN_SAMPLES

對應 SD_09 W2 zero-trust audit「範圍外」#1：perf samples=20 重採 baseline。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent

# 與 autoclaude/utils/perf_baseline.py::MIN_RUNS 同步（ADR-SD08-003 v1.1）
MIN_SAMPLES = 20
CONSECUTIVE_RUNS = 7  # ADR-SD08-003 §2.6 lock policy
BLOCK_THRESHOLD = 0.15  # 與 tools/perf_regression_check.py BLOCK_THRESHOLD 同

# SD_09 W3 Round 52 — sub-ms jitter 絕對下限（與 tools/perf_regression_check.py 同步，≤ 1 處）。
# 解 token_halt_roundtrip baseline 卡 samples=7 deadlock：相對門檻對亞毫秒場景過嚴，
# baseline×15% 之絕對窗（0.489×0.15≈0.07ms）< 自然 jitter（~0.3ms）→ should_lock 永遠 False
# → baseline 永遠 samples=7 undersampled → 每輪偽 WARN。容忍判定改「相對超標 AND 絕對差 ≥ floor」
# 才算 regression；真實 regression（abs >> floor）仍拒鎖，baseline 得以 re-lock 至 samples=20。
SUBMS_JITTER_FLOOR_MS = 0.5


def load_results(path: Path) -> dict[str, dict]:
    """讀 perf_results.json；格式：{scenario: {p50_ms, p95_ms, p99_ms, samples, ...}}。"""
    if not path.exists():
        raise FileNotFoundError(f"perf_results.json not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"unexpected perf_results.json shape: {type(raw).__name__}")
    return raw


def load_baseline(path: Path) -> dict[str, dict]:
    """讀 .perf_baseline.toml（純文字 parse，避免拖 tomllib 在舊 Python）。"""
    if not path.exists():
        return {}
    import tomllib
    with path.open("rb") as f:
        return tomllib.load(f)


def _utc_date_of_record(record: dict[str, Any]) -> str | None:
    """擷取 record timestamp 的 UTC date；無則 None。"""
    ts = record.get("timestamp")
    if not ts:
        return None
    try:
        dt = _dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt.astimezone(_dt.timezone.utc).date().isoformat()
    except (TypeError, ValueError):
        return None


def append_history(history_path: Path, record: dict[str, Any]) -> None:
    """附加一筆 perf history（同 UTC date 已存在則覆寫該筆；對齊 mutation_baseline_lock M-05）。"""
    history_path.parent.mkdir(parents=True, exist_ok=True)
    new_date = _utc_date_of_record(record)

    existing: list[dict[str, Any]] = []
    if history_path.exists():
        with history_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if new_date and _utc_date_of_record(parsed) == new_date:
                    continue
                existing.append(parsed)

    existing.append(record)
    with history_path.open("w", encoding="utf-8") as f:
        for rec in existing:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def load_history(history_path: Path) -> list[dict[str, Any]]:
    if not history_path.exists():
        return []
    records: list[dict[str, Any]] = []
    with history_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _within_regression_tolerance(
    history_tail: list[dict[str, Any]], scenario: str, baseline_p95: float
) -> bool:
    """檢查 tail 7 筆某場景 p95 是否全部 < baseline × (1 + BLOCK_THRESHOLD)。"""
    threshold = baseline_p95 * (1 + BLOCK_THRESHOLD)
    for rec in history_tail:
        scen = rec.get("scenarios", {}).get(scenario)
        if not scen:
            return False
        p95 = scen.get("p95_ms")
        if p95 is None:
            return False
        # SD_09 W3 Round 52：相對超標僅在「絕對差亦 ≥ floor」時才算 regression。
        # 亞毫秒 jitter（abs < 0.5ms）即使相對 +59% 仍視為容忍範圍，使 baseline 得以 re-lock。
        if p95 >= threshold and abs(p95 - baseline_p95) >= SUBMS_JITTER_FLOOR_MS:
            return False
    return True


def should_lock(
    history: list[dict[str, Any]], scenario: str, baseline_p95: float | None
) -> tuple[bool, float | None]:
    """連續 N 次 samples ≥ MIN_SAMPLES 且（無舊 baseline 或增量 < 15%）→ 鎖定。

    回傳：(locked, new_p95)
        new_p95: 取 N 筆 max p95（最保守值）
    """
    if len(history) < CONSECUTIVE_RUNS:
        return False, None
    tail = history[-CONSECUTIVE_RUNS:]
    p95s: list[float] = []
    for rec in tail:
        scen = rec.get("scenarios", {}).get(scenario)
        if not scen:
            return False, None
        if scen.get("samples", 0) < MIN_SAMPLES:
            return False, None
        p95 = scen.get("p95_ms")
        if p95 is None:
            return False, None
        p95s.append(float(p95))
    # 若有舊 baseline，須全 tail 在容忍範圍內
    if baseline_p95 is not None and baseline_p95 > 0:
        if not _within_regression_tolerance(tail, scenario, baseline_p95):
            return False, None
    return True, max(p95s)


def write_baseline(
    baseline_path: Path,
    locked_updates: dict[str, dict[str, Any]],
    *,
    git_sha: str = "unknown",
) -> None:
    """寫 .perf_baseline.toml（合併既有未變更場景 + 新鎖定場景）。

    locked_updates: {scenario: {p50_ms, p95_ms, p99_ms, samples, captured_at}}
    """
    existing = load_baseline(baseline_path)
    existing.update(locked_updates)

    lines = [
        "# Auto-generated by tools/perf_baseline_lock.py",
        f"# Lock policy: SD_09 W2 升 samples ≥ {MIN_SAMPLES} + 連續 {CONSECUTIVE_RUNS} 次"
        " 達標寫入（ADR-SD08-003 v1.1 §2.6）",
        "",
    ]
    for scen in sorted(existing.keys()):
        sec = existing[scen]
        lines.append(f"[{scen}]")
        lines.append(f"p50_ms = {sec.get('p50_ms', 0.0)}")
        lines.append(f"p95_ms = {sec.get('p95_ms', 0.0)}")
        lines.append(f"p99_ms = {sec.get('p99_ms', 0.0)}")
        lines.append(f"samples = {sec.get('samples', 0)}")
        lines.append(f'git_sha = "{sec.get("git_sha", git_sha)}"')
        lines.append(f'captured_at = "{sec.get("captured_at", "")}"')
        lines.append("")
    baseline_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def reset_baseline(baseline_path: Path) -> Path:
    """SD_09 W2-#1 invalidate 舊 samples=7 baseline；備份至 .perf_baseline_legacy.toml。

    回傳備份檔路徑。已有備份則覆寫（避免累積垃圾）。
    """
    if not baseline_path.exists():
        return baseline_path  # noop
    backup = baseline_path.with_suffix(".legacy.toml")
    backup.write_text(baseline_path.read_text(encoding="utf-8"), encoding="utf-8")
    baseline_path.unlink()
    return backup


def run(
    results_path: Path,
    history_path: Path,
    baseline_path: Path,
    *,
    git_sha: str = "unknown",
) -> dict[str, Any]:
    """執行一次 lock 嘗試。

    對 perf_results.json 內所有 scenarios 累積至 history；判定 lock。
    """
    results = load_results(results_path)
    # 過濾 samples < MIN_SAMPLES 的場景（不寫入 history 避免污染）
    valid_scenarios: dict[str, dict] = {}
    rejected: list[str] = []
    for scen, sec in results.items():
        if not isinstance(sec, dict):
            continue
        samples = int(sec.get("samples", 0) or 0)
        if samples < MIN_SAMPLES:
            rejected.append(f"{scen}(samples={samples})")
            continue
        valid_scenarios[scen] = sec

    if not valid_scenarios:
        raise ValueError(
            f"no scenarios with samples >= {MIN_SAMPLES}; rejected={rejected}"
        )

    record = {
        "timestamp": _dt.datetime.now(tz=_dt.timezone.utc).isoformat(),
        "git_sha": git_sha,
        "scenarios": valid_scenarios,
    }
    append_history(history_path, record)

    history = load_history(history_path)
    baseline = load_baseline(baseline_path)

    locked_updates: dict[str, dict[str, Any]] = {}
    observing: dict[str, dict[str, Any]] = {}
    for scen in valid_scenarios.keys():
        old_baseline_p95 = None
        if scen in baseline:
            try:
                old_baseline_p95 = float(baseline[scen].get("p95_ms", 0)) or None
            except (TypeError, ValueError):
                old_baseline_p95 = None
        locked, new_p95 = should_lock(history, scen, old_baseline_p95)
        if locked and new_p95 is not None:
            # 取最後一筆 stats（最保守 p95 取自 tail max）
            tail_last = history[-1]["scenarios"][scen]
            locked_updates[scen] = {
                "p50_ms": tail_last.get("p50_ms", 0.0),
                "p95_ms": round(new_p95, 3),
                "p99_ms": tail_last.get("p99_ms", new_p95),
                "samples": MIN_SAMPLES,
                "git_sha": git_sha,
                "captured_at": record["timestamp"],
            }
        else:
            # 統計連續達標次數
            count = 0
            for rec in reversed(history):
                scen_data = rec.get("scenarios", {}).get(scen)
                if not scen_data or scen_data.get("samples", 0) < MIN_SAMPLES:
                    break
                if old_baseline_p95 is not None and old_baseline_p95 > 0:
                    p95 = scen_data.get("p95_ms", float("inf"))
                    # SD_09 W3 Round 52：與 _within_regression_tolerance 對齊 — sub-ms jitter
                    # （abs < floor）不中斷連續計數，避免亞毫秒場景永遠 observing。
                    if (
                        p95 >= old_baseline_p95 * (1 + BLOCK_THRESHOLD)
                        and abs(p95 - old_baseline_p95) >= SUBMS_JITTER_FLOOR_MS
                    ):
                        break
                count += 1
            observing[scen] = {
                "runs_collected": count,
                "runs_needed": max(0, CONSECUTIVE_RUNS - count),
                "current_p95_ms": valid_scenarios[scen].get("p95_ms"),
                "baseline_p95_ms": old_baseline_p95,
            }

    if locked_updates:
        write_baseline(baseline_path, locked_updates, git_sha=git_sha)

    return {
        "status": "locked" if locked_updates else "observing",
        "locked": list(locked_updates.keys()),
        "observing": observing,
        "rejected_samples_too_low": rejected,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Perf baseline lock (SD_09 W2-#1)")
    parser.add_argument(
        "--results",
        type=Path,
        default=_REPO_ROOT / "perf_results.json",
        help="perf_results.json 路徑（預設 repo root）",
    )
    parser.add_argument(
        "--history",
        type=Path,
        default=_REPO_ROOT / ".perf_history.jsonl",
        help="累積 history（預設 .perf_history.jsonl）",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=_REPO_ROOT / ".perf_baseline.toml",
        help="baseline TOML（預設 .perf_baseline.toml）",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="invalidate 舊 baseline 並備份至 .perf_baseline.legacy.toml（SD_09 W2-#1）",
    )
    parser.add_argument("--git-sha", default="unknown", help="標註用 git SHA")
    parser.add_argument("--json", action="store_true", help="輸出 JSON")
    args = parser.parse_args(argv)

    if args.reset:
        backup = reset_baseline(args.baseline)
        print(f"::notice::baseline reset; backup -> {backup}")
        return 0

    try:
        result = run(
            args.results, args.history, args.baseline, git_sha=args.git_sha
        )
    except FileNotFoundError as e:
        print(f"::error::{e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"::warning::{e}", file=sys.stderr)
        return 0

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["locked"]:
            print(f"::notice::perf baseline locked: {', '.join(result['locked'])}")
        for scen, obs in result["observing"].items():
            need = obs["runs_needed"]
            print(
                f"::notice::{scen} observing — current_p95={obs['current_p95_ms']}ms "
                f"runs={obs['runs_collected']}/{CONSECUTIVE_RUNS} (need {need} more)"
            )
        if result["rejected_samples_too_low"]:
            print(
                f"::warning::rejected (samples<{MIN_SAMPLES}): "
                f"{', '.join(result['rejected_samples_too_low'])}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
