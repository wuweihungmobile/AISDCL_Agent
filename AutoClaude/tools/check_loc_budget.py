#!/usr/bin/env python
"""LOC budget checker — tiered policy (ADR-SD07-001 v1.0, SD_07 W0).

分級政策（取代 SD_02/05/06 250 LOC 一刀切）：

  | tier           | budget | 對應目錄 / 識別                              |
  |----------------|--------|---------------------------------------------|
  | data           | 150    | autoclaude/models/, autoclaude/core/ports/  |
  | plugin_entry   | 250    | autoclaude/plugins/*_plugin.py, */plugin.py |
  | strategy       | 300    | autoclaude/core/services/mutation/, prompt_builder |
  | adapter        | 400    | autoclaude/infra/adapters/, infra/repositories/ |
  | service        | 500    | autoclaude/core/services/, steps_orchestrator/, playbook_runner.py |
  | contract       | 400    | autoclaude/core/hookspec.py, wiring.py, execution/types.py |
  | absolute_limit | 750    | 全域絕對紅線（任何層級不得超）              |

per-file overrides 由 .loc-budget.toml 提供（需 Architect / SD 雙簽核 +
PR description 書面理由，ADR §6.2）。

總量 cap：total LOC ≤ baseline × 1.20（防爆漲）。R56 訂正：此 cap 與 tier/absolute
違規**同級阻塞**（見下方 has_violation），非舊述的「sanity check」——宣稱與行為不一致
曾導致兩輪把它誤當軟性提示。baseline 重新校準須走 ADR-SD07-001 §6.3 正式程序
（先刪死碼／收斂重複實作，最後才調 baseline；Architect + SD 雙簽）。
R56 round 5 增訂：`total ≥ cap − TOTAL_WARN_MARGIN` 但尚未破線時印 **非阻塞** [WARN]
（rc 不變、不進 has_violation），把 §6.3 觸發條件 ② 的偵測從人眼改為機械。

使用：
  python tools/check_loc_budget.py            # 檢查（CI gate）
  python tools/check_loc_budget.py --update   # 更新 baseline；R56 註記：刻意不接線任何
                                              # 閘門，僅供 ADR §6.3 核准後人工執行
  python tools/check_loc_budget.py --json     # 輸出 JSON 報表
"""
from __future__ import annotations

import fnmatch
import json
import sys
import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BASELINE_FILE = PROJECT_ROOT / ".loc_baseline"
OVERRIDE_FILE = PROJECT_ROOT / ".loc-budget.toml"

# ADR-SD07-001 §4.2 分級表（順序敏感：上方 tier 優先匹配）
LOC_TIERS: dict[str, dict] = {
    "data": {
        "budget": 150,
        "patterns": [
            "autoclaude/models/",
            "autoclaude/core/ports/",
        ],
    },
    "plugin_entry": {
        "budget": 250,
        "patterns": [
            "autoclaude/plugins/*_plugin.py",
            "autoclaude/plugins/*/plugin.py",
        ],
    },
    "strategy": {
        "budget": 300,
        "patterns": [
            "autoclaude/core/services/mutation/",
            "autoclaude/decision/prompt_builder.py",
            # F-A1 / ADR-AGT-002 §2 + SRD_AGT_Phase3 §2.3：GoalDecomposer 設計屬
            # strategy tier ≤300，機械錨定使設計宣稱可被 CI 強制（流程改善 #8）
            "autoclaude/execution/goal_decomposer.py",
        ],
    },
    "adapter": {
        "budget": 400,
        "patterns": [
            "autoclaude/infra/adapters/",
            "autoclaude/infra/repositories/",
        ],
    },
    "contract": {
        "budget": 400,
        "patterns": [
            "autoclaude/core/hookspec.py",
            "autoclaude/core/wiring.py",
            "autoclaude/execution/types.py",
        ],
    },
    "service": {
        "budget": 500,
        "patterns": [
            "autoclaude/core/services/",
            "autoclaude/execution/steps_orchestrator/",
            "autoclaude/execution/playbook_runner.py",
        ],
    },
}
ABSOLUTE_LIMIT = 750
SCAN_ROOT = "autoclaude"
TOTAL_INCREASE_LIMIT = 1.20
# R56 round 5 修正：ADR-SD07-001 §6.3 觸發條件 ② 是「連續 2 輪 total ≥ cap − 10」，
# 但本工具此前只在 total > cap 才有訊號 —— 落在預警帶時輸出與正常態一字不差，
# 該 ADR 自己的「緣起」段記載 R53(=cap)／R55(=cap−1) 兩次都是靠審查員逐字讀輸出
# 才發現。在一個把「9 支 vs 15 支」人工計數都機械化的 repo 裡，新訂程序不該只靠人眼。
# 本常數即該條的機械化。
# R56 round 5 補鎖（四方複核指出本訊號自身零回歸保護、且與 ADR 兩站點硬編互稱同步）：
#   - 本常數 ↔ ADR §6.3 ② 的「cap − 10」由 tests/contract/test_loc_budget_tiered.py::
#     test_total_warn_margin_matches_adr_sd07_001_section_6_3 自 ADR 正文抽數字比對，
#     機械鎖定而非人工宣稱；改任一站點未同步即翻紅。
#   - 下方預警帶四態邊界（>= 下緣／total==cap／破線）與「WARN 非阻塞、rc 不得改變」
#     由同檔 test_warn_band_boundary_and_rc_invariant 釘住；JSON 兩欄由
#     test_warn_band_json_payload_matches_text_mode 釘住。
TOTAL_WARN_MARGIN = 10

# ADR-SD08-001 §3.1：CLAUDE.md 文件治理（≤ 400 行強制）
# SPECIAL_FILES 採 raw line count（wc -l 等價，含空行/註解，因 CLAUDE.md 為 Markdown）
SPECIAL_FILES: dict[str, int] = {
    "CLAUDE.md": 400,  # ADR-SD08-001 §2.1：CLAUDE.md ≤ 400 + Snapshot SSOT
    # SD_09 Pre-W0 audit P0-06：補長文件預算（Migration SOP / Sprint history）
    "docs/08_deployment/Production_Migration_SOP.md": 800,
    "docs/05_development/sprint_history.md": 2000,
}


@dataclass(frozen=True)
class FileReport:
    rel_path: str
    loc: int
    tier: str
    budget: int
    over_by: int
    override_reason: str | None


def count_loc(path: Path) -> int:
    """計算實際程式碼行數（排除空行與純註解行）。"""
    if not path.exists():
        return 0
    n = 0
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            n += 1
    return n


def count_raw_lines(path: Path) -> int:
    """計算原始行數（wc -l 等價，用於 Markdown 等非程式碼檔案）。"""
    if not path.exists():
        return 0
    with path.open(encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in f)


def check_special_files() -> list[FileReport]:
    """ADR-SD08-001 §3.1：檢查 SPECIAL_FILES 的 raw line count。"""
    violations: list[FileReport] = []
    for file_path, max_lines in SPECIAL_FILES.items():
        f = PROJECT_ROOT / file_path
        if not f.exists():
            continue
        actual = count_raw_lines(f)
        if actual > max_lines:
            violations.append(
                FileReport(
                    rel_path=file_path,
                    loc=actual,
                    tier="special",
                    budget=max_lines,
                    over_by=actual - max_lines,
                    override_reason="ADR-SD08-001 CLAUDE.md 文件治理",
                )
            )
    return violations


def collect_total_loc(root: Path) -> int:
    return sum(count_loc(p) for p in root.rglob("*.py"))


def _matches_pattern(rel_posix: str, pattern: str) -> bool:
    if pattern.endswith("/"):
        return rel_posix.startswith(pattern)
    return fnmatch.fnmatchcase(rel_posix, pattern)


def classify_file(rel_path: Path) -> tuple[str, int]:
    """依 LOC_TIERS 順序匹配，回傳 (tier_name, budget)。

    未匹配任何 tier → 預設使用 absolute_limit（750）以避免新檔案無 budget。
    """
    rel_posix = rel_path.as_posix()
    for tier_name, spec in LOC_TIERS.items():
        for pat in spec["patterns"]:
            if _matches_pattern(rel_posix, pat):
                return tier_name, spec["budget"]
    return "unclassified", ABSOLUTE_LIMIT


def load_overrides() -> dict[str, dict]:
    """讀 .loc-budget.toml [overrides]；不存在則回空 dict。"""
    if not OVERRIDE_FILE.exists():
        return {}
    with OVERRIDE_FILE.open("rb") as f:
        data = tomllib.load(f)
    return data.get("overrides", {})


def read_baseline() -> int | None:
    if not BASELINE_FILE.exists():
        return None
    try:
        return int(BASELINE_FILE.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None


def write_baseline(value: int) -> None:
    BASELINE_FILE.write_text(f"{value}\n", encoding="utf-8")


def iter_source_files() -> Iterable[Path]:
    for p in (PROJECT_ROOT / SCAN_ROOT).rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        yield p


def build_reports(overrides: dict[str, dict]) -> list[FileReport]:
    reports: list[FileReport] = []
    for p in iter_source_files():
        rel = p.relative_to(PROJECT_ROOT)
        loc = count_loc(p)
        tier_name, budget = classify_file(rel)
        override_reason = None
        rel_posix = rel.as_posix()
        if rel_posix in overrides:
            ov = overrides[rel_posix]
            tier_name = ov.get("tier", tier_name)
            override_reason = ov.get("reason", "(no reason given)")
            budget = LOC_TIERS.get(tier_name, {}).get("budget", ABSOLUTE_LIMIT)
        reports.append(
            FileReport(
                rel_path=rel_posix,
                loc=loc,
                tier=tier_name,
                budget=budget,
                over_by=max(0, loc - budget),
                override_reason=override_reason,
            )
        )
    return reports


def check(update_baseline: bool = False, as_json: bool = False) -> int:
    overrides = load_overrides()
    reports = build_reports(overrides)

    tier_violations: list[FileReport] = []
    absolute_violations: list[FileReport] = []
    for r in reports:
        if r.loc > ABSOLUTE_LIMIT:
            absolute_violations.append(r)
        if r.over_by > 0:
            tier_violations.append(r)

    # ADR-SD08-001 §3.1：CLAUDE.md ≤ 400 強制
    special_violations = check_special_files()

    total = sum(r.loc for r in reports)
    baseline = read_baseline()
    if update_baseline or baseline is None:
        write_baseline(total)
        baseline = total
        print(f"[baseline] 已寫入 .loc_baseline = {total}")
    cap = int(baseline * TOTAL_INCREASE_LIMIT)
    total_violation = total > cap
    # 預警帶：已進 ADR §6.3 ② 的「餘裕耗盡」區間但尚未破線。**非阻塞**（不進
    # has_violation、不影響 rc），僅提示；破線後改由下方 [TOTAL] 阻塞訊息接手，
    # 故此處刻意排除 total_violation 以免同一件事印兩段。
    total_warn_band = (not total_violation) and total >= cap - TOTAL_WARN_MARGIN

    if as_json:
        payload = {
            "total": total,
            "baseline": baseline,
            "cap": cap,
            "total_violation": total_violation,
            # ADR §6.3 的「必要證據」指定 --json 報表，故預警帶亦須在 JSON 可機讀，
            # 否則走正規程序的人反而看不到觸發條件 ②。
            "total_warn_band": total_warn_band,
            "total_warn_margin": TOTAL_WARN_MARGIN,
            "absolute_violations": [r.__dict__ for r in absolute_violations],
            "tier_violations": [r.__dict__ for r in tier_violations],
            "special_violations": [r.__dict__ for r in special_violations],
            "policy_version": "v2-tiered+sd08-special",
            "absolute_limit": ABSOLUTE_LIMIT,
            "special_files": SPECIAL_FILES,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        violations_count = (
            len(absolute_violations)
            + len(tier_violations)
            + len(special_violations)
            + (1 if total_violation else 0)
        )
        print(
            f"[check_loc_budget v2-tiered] total={total} baseline={baseline} "
            f"cap={cap} violations={violations_count} "
            f"(absolute={len(absolute_violations)} tier={len(tier_violations)} "
            f"special={len(special_violations)} "
            f"total={'1' if total_violation else '0'})"
        )
        if absolute_violations:
            print(f"\n[ABSOLUTE] absolute red line violations (limit {ABSOLUTE_LIMIT} LOC):")
            for r in absolute_violations:
                print(f"  [{r.tier}] {r.rel_path}: {r.loc} > {ABSOLUTE_LIMIT}")
        if tier_violations:
            print("\n[TIER] tiered budget violations:")
            for r in tier_violations:
                tag = f" (override: {r.override_reason})" if r.override_reason else ""
                print(
                    f"  [{r.tier}<={r.budget}] {r.rel_path}: {r.loc} > {r.budget} "
                    f"(+{r.over_by}){tag}"
                )
        if total_violation:
            print(
                f"\n[TOTAL] total LOC cap violation: {SCAN_ROOT}/: {total} > "
                f"baseline({baseline}) x {TOTAL_INCREASE_LIMIT} = {cap}"
            )
        if total_warn_band:
            print(
                f"\n[WARN] total LOC 已進預警帶（非阻塞，rc 不變）：{total} ≥ "
                f"cap({cap}) − {TOTAL_WARN_MARGIN}，餘裕僅剩 {cap - total} 行。"
                "\n       連續 2 輪落在本帶即滿足 ADR-SD07-001 §6.3 觸發條件 ②"
                "（baseline 重新校準程序）。"
                "\n       先減後調：①刪死碼／收斂重複實作 ②零／負增行手法 "
                "③確認為不可壓縮的真實功能後才調 baseline（Architect + SD 雙簽）。"
                "\n       見 docs/04_planning/ADR/ADR-SD07-001-loc-policy.md §6.3。"
            )
        if special_violations:
            print("\n[SPECIAL] ADR-SD08-001 SPECIAL_FILES line-count violations:")
            for r in special_violations:
                print(
                    f"  [{r.tier}<={r.budget}] {r.rel_path}: {r.loc} > {r.budget} "
                    f"(+{r.over_by}) — {r.override_reason}"
                )

    has_violation = (
        bool(absolute_violations)
        or bool(tier_violations)
        or bool(special_violations)
        or total_violation
    )
    return 1 if has_violation else 0


def main() -> int:
    # DEF-82-001/DEF-101-070 家族慣例：報表含中文/→ 等非 ASCII，Windows cp950 console
    # 直接 print 會 UnicodeEncodeError 中斷；stdout + stderr 皆強制 utf-8。
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, OSError):
            pass
    update = "--update" in sys.argv
    as_json = "--json" in sys.argv
    return check(update_baseline=update, as_json=as_json)


if __name__ == "__main__":
    sys.exit(main())
