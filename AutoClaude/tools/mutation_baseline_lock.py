"""SD_Improving_08 W3 T3-D3 — mutation baseline 連續 7 次達標鎖定。

對應 [ADR-SD08-002 §2.4](../docs/04_planning/ADR/ADR-SD08-002-mutation-baseline.md)。

職責：
    1. 解析 mutmut results log 取出 kill_rate
    2. 追加至 .mutation_history.jsonl（最近 N 筆）
    3. 若連續 7 次達 (target - 0.05) → 寫入 .mutation_baseline.toml（取 min 最保守值）
    4. 否則僅累積觀察期紀錄（continue-on-error 維持非阻塞）

分模組目標（ADR-SD08-002 §2.1 + ADR-SD09-009 §5.5 ±2pp tolerance）：
    token_guard:     75%（effective threshold 68% = 75% - 5% TOLERANCE - 2% EXTRA）
    goal_synthesis:  70%（effective threshold 63%）
    coordinator:     65%（effective threshold 58%）

kill_rate 公式（ADR-SD09-009 v1.0 ACCEPTED 2026-05-25 選項 A）：
    (killed + 0.5 × suspicious) / (killed + survived + timeout + suspicious)
    — suspicious 計 0.5 killed 半 kill，緩衝 mutmut timing-sensitive bounce flake。

退出碼：
    0  累積中（observing）/ 已鎖定（locked）
    1  log 不存在或解析失敗
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent

TARGETS: dict[str, float] = {
    "token_guard": 0.75,
    "goal_synthesis": 0.70,
    "coordinator": 0.65,
}
TOLERANCE = 0.05  # 目標 -5% 容忍
# ADR-SD09-009 v1.0 ACCEPTED 2026-05-25 §5.5：±2pp tolerance 緩衝 suspicious bounce flake。
# effective threshold = target - TOLERANCE - EXTRA_TOLERANCE（token_guard: 0.75 - 0.05 - 0.02 = 0.68）
EXTRA_TOLERANCE = 0.02
CONSECUTIVE_RUNS = 7
# SD_09 W3 Round 21 audit Architect P1 #2 修復（紀律 #12 強化）：
#   Round 4 修復原採 ceil(N/2)=4 作為「部分缺 sha 寬鬆鎖定」門檻；Architect 指出
#   理論上 3 missing + 4 unique sha 即可鎖定，比預期 7 unique 弱 43%。
#   收緊為 N - MAX_BACKWARD_COMPAT_MISSING = 7 - 2 = 5；只允許 R2 P0-5 修復前
#   兩筆 legacy record（2026-05-20 / 2026-05-21）缺欄位，之後必須全部 unique sha。
MAX_BACKWARD_COMPAT_MISSING = 2

# SD_09 W3 Round 2 audit P0-5：source_sha256 對應 plugin 目錄
_MODULE_PATHS: dict[str, Path] = {
    "token_guard": _REPO_ROOT / "autoclaude" / "plugins" / "token_guard",
    "goal_synthesis": _REPO_ROOT / "autoclaude" / "plugins" / "goal_synthesis",
    "coordinator": _REPO_ROOT / "autoclaude" / "core" / "orchestration",
}

_LINE_PATTERNS = {
    "killed": re.compile(r"Killed\b[^\(]*\((\d+)\)", re.IGNORECASE),
    "survived": re.compile(r"Survived\b[^\(]*\((\d+)\)", re.IGNORECASE),
    "timeout": re.compile(r"Timeout\b[^\(]*\((\d+)\)", re.IGNORECASE),
    "suspicious": re.compile(r"Suspicious\b[^\(]*\((\d+)\)", re.IGNORECASE),
    "skipped": re.compile(r"Skipped\b[^\(]*\((\d+)\)", re.IGNORECASE),
}

# SD_09 W2 audit P0-AUDIT-04 修復：marker-based parse
# 由 tools/run_mutmut_in_docker.sh 寫入 `--- mutmut full counts (from cache; ...) ---`
# 與 `--- mutmut full counts (end) ---` 之間是「單一真相」5 行 counts。
# 取「最後一筆」依賴隱性順序，mutmut 輸出順序變更會讀錯誤的 N（紀律 #5）。
# begin marker 須排除 `(end)` 字樣，否則同一 regex 會誤匹配 end 行
_COUNTS_BEGIN_MARKER = re.compile(
    r"^---\s*mutmut full counts(?!\s*\(end\))[^\n]*---\s*$", re.IGNORECASE
)
_COUNTS_END_MARKER = re.compile(r"^---\s*mutmut full counts\s*\(end\)\s*---\s*$", re.IGNORECASE)


def _parse_marker_section(text: str) -> dict[str, int] | None:
    """於 begin/end marker 間擷取 5 行 counts；找不到 marker 則 None。"""
    lines = text.splitlines()
    begin_idx = -1
    end_idx = -1
    for i, line in enumerate(lines):
        if _COUNTS_BEGIN_MARKER.match(line):
            begin_idx = i
        elif begin_idx >= 0 and _COUNTS_END_MARKER.match(line):
            end_idx = i
            break
    if begin_idx < 0 or end_idx < 0:
        return None
    section = lines[begin_idx + 1 : end_idx]
    counts: dict[str, int] = {k: 0 for k in _LINE_PATTERNS}
    for line in section:
        for kind, pat in _LINE_PATTERNS.items():
            m = pat.search(line)
            if m:
                counts[kind] = int(m.group(1))
                break
    return counts


def parse_mutmut_log(log_path: Path) -> dict[str, int]:
    """解析 mutmut results log。

    SD_09 W2 audit P0-AUDIT-04 修復：
      - 優先 marker-based parse（`--- mutmut full counts ... ---` 區段為單一真相）
      - marker 缺失時 fallback 至「取最後一筆」（向下相容舊 log）

    Raises:
        FileNotFoundError: log 檔不存在
        ValueError: log 解析完全無計數（防 SD_09 Pre-W0 audit P0-01：
                    空 log / 環境 crash / mutmut 未跑成功 → 不污染 history 為 0%）
    """
    if not log_path.exists():
        raise FileNotFoundError(f"mutmut log not found: {log_path}")
    text = log_path.read_text(encoding="utf-8", errors="replace")

    counts = _parse_marker_section(text)
    if counts is not None and sum(counts.values()) > 0:
        return counts

    # Fallback：取最後一筆（舊 log 相容）
    counts = {k: 0 for k in _LINE_PATTERNS}
    for line in text.splitlines():
        for kind, pat in _LINE_PATTERNS.items():
            m = pat.search(line)
            if m:
                counts[kind] = int(m.group(1))
    if sum(counts.values()) == 0:
        raise ValueError(
            "empty mutmut log; refusing to write 0% to history "
            f"(log={log_path})"
        )
    return counts


def calc_kill_rate(counts: dict[str, int]) -> float:
    """kill rate = (killed + 0.5 × suspicious) / (killed + survived + timeout + suspicious)。

    ADR-SD09-009 v1.0 ACCEPTED 2026-05-25 — 選項 A：suspicious 計 0.5 killed 半 kill。

    mutmut 2.4.x 對 timing-sensitive 點位的 suspicious 標籤為半確定性
    （mutmut README: "probably killed but timing-sensitive"）。0.5 weight 為中位
    無偏估計，避免 bounce flake（同 mutant 跨 run 在 killed↔suspicious 間飄動）
    觸發鎖定重計。當 suspicious=0 時退化為原公式（向下相容）。
    """
    killed = counts.get("killed", 0)
    survived = counts.get("survived", 0)
    timeout = counts.get("timeout", 0)
    suspicious = counts.get("suspicious", 0)
    denom = killed + survived + timeout + suspicious
    if denom <= 0:
        return 0.0
    return (killed + 0.5 * suspicious) / denom


def _utc_date_of_record(record: dict[str, Any]) -> str | None:
    """擷取 record timestamp 的 UTC date；無則 None。"""
    # SD_09 W2 audit P2-AUDIT-28：模組頂已 import datetime as _dt，移除重複 import
    ts = record.get("timestamp")
    if not ts:
        return None
    try:
        dt = _dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt.astimezone(_dt.timezone.utc).date().isoformat()
    except (TypeError, ValueError):
        return None


def append_history(history_path: Path, record: dict[str, Any]) -> None:
    """附加一筆紀錄；同 module + 同 UTC date 已存在則覆寫該筆（M-05 修復對齊）。

    SD_09 W0 zero-trust audit M-05 修復：避免同日 mutmut 多 runs 偽造觀察期 #1 連續 7 次。
    """
    history_path.parent.mkdir(parents=True, exist_ok=True)
    module = record.get("module")
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
                # 同 module + 同 UTC date → 跳過舊紀錄
                if (
                    module
                    and parsed.get("module") == module
                    and new_date
                    and _utc_date_of_record(parsed) == new_date
                ):
                    continue
                existing.append(parsed)

    existing.append(record)
    with history_path.open("w", encoding="utf-8") as f:
        for rec in existing:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def load_module_history(history_path: Path, module: str) -> list[dict[str, Any]]:
    if not history_path.exists():
        return []
    records: list[dict[str, Any]] = []
    with history_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("module") == module:
                records.append(rec)
    return records


def compute_source_sha256(module_path: Path) -> str:
    """SD_09 W3 Round 2 audit P0-5：計算 plugin 目錄所有 .py SHA-256（截 16 chars）。

    用途：mutation history 區分「同 source 跑 7 次」vs「7 次不同 commit」，避免假鎖定。
    若 module_path 不存在或無 .py 檔 → 回 'unknown'（向下相容測試環境）。
    """
    if not module_path.exists():
        return "unknown"
    hasher = hashlib.sha256()
    # SD_09 W3 Round 21 audit QA P1-R21-3 修復：顯式 posix path key
    # 避免跨平台（Win NTFS vs Linux ext4 / OS locale）排序差異導致 sha 不一致
    py_files = sorted(module_path.rglob("*.py"), key=lambda p: p.as_posix())
    if not py_files:
        return "unknown"
    for py_file in py_files:
        try:
            hasher.update(py_file.read_bytes())
        except (OSError, PermissionError):
            continue
    return hasher.hexdigest()[:16]


def compute_consistency_warning(
    history: list[dict[str, Any]],
    module: str,
    threshold: float = 0.03,
) -> tuple[bool, str]:
    """SD_09 W3 Round 31 audit P1-R31-2：multi-run kill_rate variance consistency check（紀律 #12 強化）。

    篩選 module 對應 record → 按 source_sha256 分組 → 對任一 sha 出現 ≥ 2 次的群組計算 kill_rate stddev。
    若任一 sha stddev > threshold（預設 3pp = 0.03）→ return (True, warning_message)；否則 (False, "")。

    目的：偵測 mutmut suspicious 非確定性導致同 sha 多 run kill_rate 大幅震盪（如 R30 85.57% vs
    同 sha 復跑 R31 74.83% 差 10.74pp）。避免單次 outlier 被誤判為 baseline 真實水位。

    本 function 為 **附加告警通道**：不改 should_lock return value 邏輯，僅供 main() 印 stderr WARN。
    對應 [Nightly_Forensic_Discipline.md §紀律 #12](../docs/06_quality/Nightly_Forensic_Discipline.md)。
    """
    # 篩選 module 對應 record（含 sha 且 kill_rate 存在）
    module_records = [
        r for r in history
        if r.get("module") == module
        and r.get("source_sha256")
        and isinstance(r.get("kill_rate"), (int, float))
    ]
    if not module_records:
        return False, ""

    # 按 source_sha256 分組
    by_sha: dict[str, list[float]] = {}
    for r in module_records:
        sha = str(r["source_sha256"])
        by_sha.setdefault(sha, []).append(float(r["kill_rate"]))

    # 對任一 sha ≥ 2 次的群組計算 kill_rate stddev
    for sha, rates in by_sha.items():
        if len(rates) < 2:
            continue
        mean = sum(rates) / len(rates)
        variance = sum((x - mean) ** 2 for x in rates) / len(rates)
        stddev = variance ** 0.5
        if stddev > threshold:
            return True, (
                f"WARN: same-sha multi-run variance detected — sha={sha[:16]} runs={len(rates)} "
                f"stddev={stddev * 100:.2f}pp > threshold {threshold * 100:.0f}pp "
                f"(mutmut suspicious non-determinism risk)"
            )
    return False, ""


def should_lock(history: list[dict[str, Any]], module: str) -> tuple[bool, float | None]:
    """連續 N 次達 (target - tolerance) 才鎖定，取 min 為最保守 baseline 值。

    SD_09 W3 Round 2 audit P0-5 修復：tail 7 筆必須含 ≥ 7 個 unique source_sha256
    （避免「同 source 跑 7 次騙過」）。

    SD_09 W3 Round 4 audit P0-AUDIT-R3-2 修復（紀律 #12 強化）：
        原本「tail 含任一缺 sha → 完全跳過 unique 檢查」設計過寬。
        若舊紀錄缺 sha + 新紀錄全部同 sha → 假鎖定。
        修正：tail 含缺 sha 紀錄時，仍要求 **non-None 部分 unique 數 = non-None 筆數**，
        且 non-None 部分至少要 ≥ ceil(N/2)（避免「7 筆中 6 筆缺欄位 + 1 筆 sha」假鎖定）。

    SD_09 W3 Round 8 audit P2-NEW-1 修復（紀律 #1 / #3 取證可見性）：
        拒鎖時印 stderr `[should_lock] reject reason=...` 標籤，讓上游能分辨拒鎖原因
        （未滿筆數 / kill_rate 跌破門檻 / sha 不足）；避免使用者誤判進度。
    """
    target = TARGETS.get(module)
    if target is None:
        sys.stderr.write(f"[should_lock] reject module={module} reason=unknown_module\n")
        return False, None
    # ADR-SD09-009 §5.5：±2pp tolerance 緩衝 suspicious bounce flake
    # token_guard: 0.75 - 0.05 - 0.02 = 0.68 effective threshold
    threshold = target - TOLERANCE - EXTRA_TOLERANCE
    if len(history) < CONSECUTIVE_RUNS:
        sys.stderr.write(
            f"[should_lock] reject module={module} reason=insufficient_runs "
            f"count={len(history)}/{CONSECUTIVE_RUNS}\n"
        )
        return False, None
    tail = history[-CONSECUTIVE_RUNS:]
    scores = [r.get("kill_rate", 0.0) for r in tail]
    if not all(s >= threshold for s in scores):
        below = [(i, s) for i, s in enumerate(scores) if s < threshold]
        sys.stderr.write(
            f"[should_lock] reject module={module} reason=kill_rate_below_threshold "
            f"threshold={threshold:.4f} below_count={len(below)}/{CONSECUTIVE_RUNS} "
            f"min_score={min(scores):.4f}\n"
        )
        return False, None

    # P0-5 + Round 4 P0-AUDIT-R3-2：sha unique 檢查
    shas = [r.get("source_sha256") for r in tail]
    non_none_shas = [sha for sha in shas if sha]
    if len(non_none_shas) == CONSECUTIVE_RUNS:
        # 全部有 sha：強制 N unique
        if len(set(non_none_shas)) < CONSECUTIVE_RUNS:
            sys.stderr.write(
                f"[should_lock] reject module={module} reason=sha_not_unique_full "
                f"unique={len(set(non_none_shas))}/{CONSECUTIVE_RUNS}\n"
            )
            return False, None
    else:
        # 含舊紀錄缺欄位：(1) non-None 部分必須全 unique；(2) 至少要 ≥ N - MAX_BACKWARD_COMPAT_MISSING 筆
        # SD_09 W3 Round 21 Architect P1 #2 強化：原 ceil(N/2)=4 過寬，收緊為 7-2=5。
        # 只允許 R2 P0-5 修復前 2 筆 legacy（5/20-5/21）缺欄位；其餘必須全 unique sha。
        min_non_none = CONSECUTIVE_RUNS - MAX_BACKWARD_COMPAT_MISSING  # 7 - 2 = 5
        if len(non_none_shas) < min_non_none:
            sys.stderr.write(
                f"[should_lock] reject module={module} reason=sha_partial_below_min "
                f"non_none={len(non_none_shas)}/{min_non_none} "
                f"(N - MAX_BACKWARD_COMPAT_MISSING)\n"
            )
            return False, None
        if len(set(non_none_shas)) < len(non_none_shas):
            sys.stderr.write(
                f"[should_lock] reject module={module} reason=sha_partial_duplicate "
                f"unique={len(set(non_none_shas))}/{len(non_none_shas)}\n"
            )
            return False, None
    return True, min(scores)


def read_baseline(baseline_path: Path) -> dict[str, float]:
    if not baseline_path.exists():
        return {}
    text = baseline_path.read_text(encoding="utf-8")
    result: dict[str, float] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("["):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        try:
            result[key] = float(val)
        except ValueError:
            continue
    return result


def write_baseline(baseline_path: Path, module: str, score: float) -> None:
    """以最小侵入式 upsert 寫入 .mutation_baseline.toml。"""
    existing = read_baseline(baseline_path)
    existing[module] = score
    lines = [
        "# SD_Improving_08 W3 T3-D5 — mutation kill rate baseline（連續 7 次達標鎖定值）",
        "# 自動寫入：tools/mutation_baseline_lock.py（ADR-SD08-002 §2.4）",
        "# 鎖定後升級條件視 SD_09 評估；continue-on-error 維持非阻塞。",
        "",
        "[scores]",
    ]
    for key in sorted(existing):
        lines.append(f'{key} = {existing[key]:.4f}')
    baseline_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(
    module: str,
    log_path: Path,
    history_path: Path,
    baseline_path: Path,
    *,
    source_path: Path | None = None,
) -> dict[str, Any]:
    counts = parse_mutmut_log(log_path)
    kill_rate = calc_kill_rate(counts)
    # P0-5：嵌入 source_sha256（同 source 跑 7 次無法 lock）
    src_path = source_path or _MODULE_PATHS.get(module)
    source_sha = compute_source_sha256(src_path) if src_path else "unknown"
    record = {
        "timestamp": _dt.datetime.now(tz=_dt.timezone.utc).isoformat(),
        "module": module,
        "kill_rate": kill_rate,
        "counts": counts,
        "source_sha256": source_sha,
    }
    append_history(history_path, record)
    history = load_module_history(history_path, module)
    locked, baseline_value = should_lock(history, module)
    if locked and baseline_value is not None:
        existing = read_baseline(baseline_path).get(module)
        if existing is None or baseline_value > existing:
            write_baseline(baseline_path, module, baseline_value)
        return {
            "status": "locked",
            "module": module,
            "kill_rate": kill_rate,
            "baseline": baseline_value,
            "source_sha256": source_sha,
        }
    return {
        "status": "observing",
        "module": module,
        "kill_rate": kill_rate,
        "runs_collected": len(history),
        "runs_needed": max(0, CONSECUTIVE_RUNS - len(history)),
        "source_sha256": source_sha,
    }


def _check_log_mtime(log_path: Path, max_age_seconds: int) -> tuple[bool, float]:
    """SD_09 W3 Round 2 audit P1-2：驗證 log mtime 在 max_age_seconds 內。

    Returns:
        (是否新鮮, 實際年齡秒)
    """
    if not log_path.exists():
        return False, float("inf")
    mtime = log_path.stat().st_mtime
    age = time.time() - mtime
    return age <= max_age_seconds, age


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mutation baseline lock (SD_08 W3 T3-D3)")
    parser.add_argument("module", choices=sorted(TARGETS.keys()))
    parser.add_argument("--log", type=Path, required=True, help="mutmut results log 路徑")
    parser.add_argument("--history", type=Path, default=_REPO_ROOT / ".mutation_history.jsonl")
    parser.add_argument("--baseline", type=Path, default=_REPO_ROOT / ".mutation_baseline.toml")
    parser.add_argument("--json", action="store_true", help="輸出 JSON")
    parser.add_argument(
        "--require-log-mtime-within-seconds",
        type=int,
        default=0,
        help="若 > 0，驗證 log mtime 在 N 秒內（避免讀到 stale log）；超時 stage fail（P1-2）",
    )
    args = parser.parse_args(argv)

    # P1-2：log mtime 守門（紀律 #7 cache fresh）
    if args.require_log_mtime_within_seconds > 0:
        fresh, age = _check_log_mtime(args.log, args.require_log_mtime_within_seconds)
        if not fresh:
            print(
                f"::error::mutation log mtime stale: age={age:.1f}s > "
                f"{args.require_log_mtime_within_seconds}s (log={args.log})",
                file=sys.stderr,
            )
            return 1

    try:
        result = run(args.module, args.log, args.history, args.baseline)
    except FileNotFoundError as e:
        print(f"::error::{e}", file=sys.stderr)
        return 1
    except ValueError as e:
        # SD_09 Pre-W0 audit P0-01：空 log 守門 — 不污染 history，但保持 nightly 非阻塞
        print(f"::warning::{e}", file=sys.stderr)
        return 0

    # SD_09 W3 Round 31 audit P1-R31-2：附加 multi-run consistency check（紀律 #12 強化）
    # 寫入 history 後再讀整段歷史檢查 same-sha 變異；僅 stderr WARN，不改 lock 行為
    try:
        full_history = load_module_history(args.history, args.module)
        triggered, warn_msg = compute_consistency_warning(full_history, args.module)
        if triggered:
            print(f"::warning::{warn_msg}", file=sys.stderr)
    except Exception:  # noqa: BLE001 — 告警通道不可阻斷主流程
        pass

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["status"] == "locked":
            print(f"::notice::{args.module} baseline locked at {result['baseline']:.2%}")
        else:
            need = result["runs_needed"]
            print(
                f"::notice::{args.module} observing — kill_rate={result['kill_rate']:.2%} "
                f"runs={result['runs_collected']}/{CONSECUTIVE_RUNS} (need {need} more)"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
