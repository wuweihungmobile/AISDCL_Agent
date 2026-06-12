#!/usr/bin/env python
"""Perf regression checker — annotation + PR comment 雙通道告警（ADR-SD08-003 §2.5）。

判定規則（ADR-SD08-003 §2.4）：
  - p95 增量 < 10%   : 🟢 通過（無動作）
  - 10% ≤ 增量 < 15% : 🟡 警告（`::warning::` annotation；非阻塞）
  - p95 增量 ≥ 15%   : 🔴 阻塞（`::error::` annotation + PR comment + exit=1）

輸入：
  perf_results.json   — pytest-benchmark / measure() 輸出（場景 → p95_ms）
  .perf_baseline.toml — 鎖定 baseline（場景 → p95_ms）

輸出：
  stdout              — 人類可讀表格
  GitHub annotation   — ::warning:: / ::error::（CI 解析）
  PR comment markdown — 寫 perf_regression_comment.md（gh pr comment -F 使用）

退出碼（SD_09 W3 Round 2 audit P0-6 三態修復）：
  0 = 全綠
  1 = 至少一個 🔴 阻塞 或 baseline 不存在
  2 = 至少一個 🟡 警告（含 BLOCK→WARN 退化）— 讓上游 ps1 summary 顯示 perf=2 區分真綠
"""
from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent

WARN_THRESHOLD = 0.10  # 10% — 觸發 ::warning::
BLOCK_THRESHOLD = 0.15  # 15% — 觸發 ::error:: + block

# SD_09 W3 Round 52 — sub-ms jitter 絕對下限（解 token_halt_roundtrip baseline samples=7 deadlock）。
# 亞毫秒場景（如 token_halt_roundtrip ~0.5ms）相對門檻 15% 僅 ~0.07ms 絕對窗，遠小於自然
# 量測 jitter（~0.3ms）→ current 一跳高即觸 WARN 且 baseline 永遠卡 samples=7 無法 re-lock。
# 修法：|current - baseline| < 此值視為量測噪音（green）；真實 regression（abs >> floor，
# 如 0.5→5ms）仍照常攔截。取代 R31 P2-R31-2 純標籤路線（已證會造成 perf_baseline_lock deadlock）。
# 與 tools/perf_baseline_lock.py:SUBMS_JITTER_FLOOR_MS 同步（≤ 1 處）。
SUBMS_JITTER_FLOOR_MS = 0.5

# SD_09 W0 二次 audit P1-F：baseline sample size 不足提示閾值
# SD_09 W2 audit P2-AUDIT-30：SSOT 對齊 ADR-SD08-003 v1.1 §2.6
# **不從 autoclaude.utils.perf_baseline import**：該 package __init__ 會鏈式 import
# logger/notifier，在 subprocess 內污染 stdout 編碼（contract test 用 cp950 解碼會 crash）。
# 同步責任：autoclaude/utils/perf_baseline.py:MIN_RUNS 變更時需手動同步此值（≤ 1 處）。
MIN_BASELINE_SAMPLES = 20  # ADR-SD08-003 v1.1; sync with autoclaude.utils.perf_baseline.MIN_RUNS


def load_baseline(path: Path) -> dict[str, dict]:
    """讀 .perf_baseline.toml；不存在則回空 dict。"""
    if not path.exists():
        return {}
    with path.open("rb") as f:
        return tomllib.load(f)


def load_results(path: Path) -> dict[str, float]:
    """讀 perf_results.json；格式：{scenario: p95_ms}。

    亦支援 pytest-benchmark 風格 {"benchmarks": [{"name": ..., "stats": {"mean":...}}]}
    """
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "benchmarks" in raw:
        out: dict[str, float] = {}
        for b in raw.get("benchmarks", []):
            name = b.get("name", "")
            stats = b.get("stats", {})
            # benchmark mean 秒 → ms
            p95 = stats.get("mean", 0) * 1000.0
            out[name] = float(p95)
        return out
    if isinstance(raw, dict):
        # 支援兩種格式：
        # 格式 A: {scenario: p95_ms}  — 數字值
        # 格式 B: {scenario: {p95_ms: ..., p50_ms: ...}}  — write_perf_results() 輸出的巢狀 dict
        result: dict[str, float] = {}
        for k, v in raw.items():
            if isinstance(v, (int, float)):
                result[k] = float(v)
            elif isinstance(v, dict) and "p95_ms" in v:
                result[k] = float(v["p95_ms"])
        return result
    return {}


def classify(delta_pct: float) -> str:
    """0~1 增量百分比（0.15 = +15%）→ 等級 green / warn / block。"""
    if delta_pct < WARN_THRESHOLD:
        return "green"
    if delta_pct < BLOCK_THRESHOLD:
        return "warn"
    return "block"


def emit_annotation(level: str, scenario: str, baseline: float, current: float, pct: float) -> None:
    """寫 GitHub Actions annotation（stdout，CI runner 解析）。

    SD_09 W3 Round 31 audit P2-R31-2：WARN 訊息若亞毫秒 jitter（|baseline - current| < 1.0 ms）
    末段附 `(sub-ms jitter range)` 標籤，標示為採樣噪音而非真實 regression。
    不改判定邏輯 / 不改門檻，僅標籤輔助人類判讀（如 R30 token_halt_roundtrip 0.5→1.0ms +104.5%）。
    """
    sign = "::warning::" if level == "warn" else "::error::"
    title = "Perf Regression" if level == "block" else "Perf Warning"
    suffix = ""
    if level == "warn" and abs(baseline - current) < 1.0:
        suffix = " (sub-ms jitter range)"
    print(
        f"{sign} title={title}::"
        f"scenario={scenario} baseline_p95={baseline:.1f}ms "
        f"current_p95={current:.1f}ms delta=+{pct * 100:.1f}%{suffix}"
    )


def build_pr_comment(rows: list[dict]) -> str:
    """產出 PR comment markdown（ADR-SD08-003 §2.5 範本）。"""
    lines = ["## ⚠️ Perf Regression Alert (ADR-SD08-003)", ""]
    lines.append("| 場景 | Baseline p95 | Current p95 | 增量 | 狀態 |")
    lines.append("|------|--------------|-------------|------|------|")
    for r in rows:
        emoji = {"green": "🟢 通過", "warn": "🟡 警告", "block": "🔴 阻塞"}[r["level"]]
        lines.append(
            f"| {r['scenario']} | {r['baseline_ms']:.1f} ms | "
            f"{r['current_ms']:.1f} ms | +{r['delta_pct'] * 100:.1f}% | {emoji} |"
        )
    lines.append("")
    lines.append("**Policy**: ADR-SD08-003 §2.4 — p95 增量 ≥ 15% 阻塞 merge；10–15% 警告。")
    lines.append("")
    lines.append(
        "**Note (SD_09 W0 二次 audit P1-F)**: baseline samples 若 < "
        f"{MIN_BASELINE_SAMPLES} 統計噪音偏高；建議拉高 baseline 取樣數降低偽陽率。"
    )
    return "\n".join(lines) + "\n"


def check(
    results_path: Path,
    baseline_path: Path,
    *,
    comment_out: Optional[Path] = None,
) -> int:
    baseline_data = load_baseline(baseline_path)
    results = load_results(results_path)

    if not baseline_data:
        print(f"::error::baseline 不存在或為空：{baseline_path}", flush=True)
        print(
            "Hint: 首次跑請執行 `python tools/perf_baseline_lock.py --init` 或手動寫入 .perf_baseline.toml"
        )
        return 1

    if not results:
        print(f"::error::perf_results 為空：{results_path}", flush=True)
        return 1

    rows: list[dict] = []
    block_count = 0
    warn_count = 0
    for scenario, current_p95 in sorted(results.items()):
        section = baseline_data.get(scenario)
        if not section:
            print(f"::warning::scenario={scenario} 無 baseline section，跳過")
            continue
        baseline_p95 = float(section.get("p95_ms", 0))
        if baseline_p95 <= 0:
            print(f"::warning::scenario={scenario} baseline.p95_ms 異常 ({baseline_p95})")
            continue
        # SD_09 W0 二次 audit P1-F + W0 audit-#NEW：baseline samples < MIN 視為「統計噪音風險高」
        # 提示但不阻塞；長期應於 ADR-SD08-003 鎖入 samples ≥ 20 才能寫 baseline。
        baseline_samples = int(section.get("samples", 0) or 0)
        undersampled = baseline_samples < MIN_BASELINE_SAMPLES
        if undersampled:
            print(
                f"::warning::scenario={scenario} baseline samples={baseline_samples} "
                f"<{MIN_BASELINE_SAMPLES} (statistical noise high; not blocking)"
            )
        delta_pct = (current_p95 - baseline_p95) / baseline_p95
        abs_delta = abs(current_p95 - baseline_p95)
        # SD_09 W3 Round 52 修復（sub-ms jitter deadlock）：絕對差 < SUBMS_JITTER_FLOOR_MS
        # 視為量測噪音（green），不論相對 % 多大。亞毫秒場景（token_halt_roundtrip ~0.5ms）
        # 的 +59% 實為 0.3ms 絕對 jitter，非真實 regression。真實 regression（abs >> floor）仍攔截。
        if abs_delta < SUBMS_JITTER_FLOOR_MS:
            level = "green"
            print(
                f"::notice::scenario={scenario} sub-ms jitter abs_delta={abs_delta:.3f}ms "
                f"<{SUBMS_JITTER_FLOOR_MS}ms → PASS (delta=+{delta_pct * 100:.1f}% on sub-ms "
                "baseline; supersedes R31 P2-R31-2 label-only)"
            )
        else:
            level = classify(delta_pct)
            # SD_09 W0 P0-AUDIT-perf-followup 修復：語意一致性 —
            #   warning 已印「not blocking」但原邏輯仍 BLOCK → 退化為 WARN 對齊宣告意圖。
            #   long-term：等 baseline_lock 累積 7 次 samples=20 後自動切回嚴格 BLOCK。
            if undersampled and level == "block":
                print(
                    f"::notice::scenario={scenario} BLOCK→WARN downgrade due to undersampled baseline "
                    f"(samples={baseline_samples} <{MIN_BASELINE_SAMPLES})"
                )
                level = "warn"
        rows.append(
            {
                "scenario": scenario,
                "baseline_ms": baseline_p95,
                "current_ms": current_p95,
                "delta_pct": delta_pct,
                "level": level,
            }
        )
        if level == "warn":
            warn_count += 1
            emit_annotation("warn", scenario, baseline_p95, current_p95, delta_pct)
        elif level == "block":
            block_count += 1
            emit_annotation("block", scenario, baseline_p95, current_p95, delta_pct)

    # 人類可讀輸出
    print("\n[perf_regression_check] 比對結果：")
    for r in rows:
        emoji = {"green": "PASS", "warn": "WARN", "block": "BLOCK"}[r["level"]]
        print(
            f"  [{emoji}] {r['scenario']}: "
            f"{r['baseline_ms']:.1f}ms → {r['current_ms']:.1f}ms (+{r['delta_pct'] * 100:.1f}%)"
        )

    # 寫 PR comment（若有阻塞或警告）
    if comment_out and (block_count + warn_count) > 0:
        comment_out.write_text(build_pr_comment(rows), encoding="utf-8")
        print(f"\nPR comment markdown 已寫入：{comment_out}")

    print(f"\nTotal: green={len(rows) - warn_count - block_count} warn={warn_count} block={block_count}")
    # SD_09 W3 Round 2 audit P0-6 修復（三態）：
    #   0=全綠 / 2=有 WARN（含 undersampled BLOCK→WARN 退化）/ 1=有 BLOCK
    # 讓 ps1 summary 區分「綠」與「觀察期等待」— 不再用單 rc 0 蓋過真實 WARN 信號
    if block_count > 0:
        return 1
    if warn_count > 0:
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Perf regression checker (ADR-SD08-003)")
    parser.add_argument("results", type=Path, help="perf_results.json")
    parser.add_argument(
        "baseline",
        type=Path,
        nargs="?",
        default=PROJECT_ROOT / ".perf_baseline.toml",
        help="baseline TOML (default: .perf_baseline.toml)",
    )
    parser.add_argument(
        "--comment-out",
        type=Path,
        default=PROJECT_ROOT / "perf_regression_comment.md",
        help="PR comment markdown 輸出路徑",
    )
    args = parser.parse_args()
    return check(args.results, args.baseline, comment_out=args.comment_out)


if __name__ == "__main__":
    sys.exit(main())
