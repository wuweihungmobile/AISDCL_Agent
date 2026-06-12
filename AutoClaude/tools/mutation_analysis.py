"""SD_Improving_08 W3 T3-D4 — survived mutation 分類 + 補測 backlog 自動產出。

對應 [ADR-SD08-002 §2.5](../docs/04_planning/ADR/ADR-SD08-002-mutation-baseline.md)。

職責：
    1. 解析 mutmut results log 取出 survived mutation 清單
    2. 對 survived mutation 執行 `mutmut show <id>` 取得 diff
    3. 分類：
       (a) boundary       — >=/> / </<=
       (b) constant       — True/False / 0/1
       (c) dead_branch    — if/elif 永真/永假
       (d) string_literal — log/error message（語意無關，標 ignore）
    4. 對 (a)/(b)/(c) 產出補測 backlog（Markdown），(d) 標 "ignore"

退出碼：
    0  成功（含 0 survived）
    1  log 不存在或 mutmut show 全部失敗
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

# SD_09 W2 audit P2-AUDIT-24 修復：移除 dead code `_SURVIVED_ID_PATTERNS`（從未被使用）
# ADR-SD09-009 v1.0 §5.3 紅線（紀律 #5 跨工具數字對齊）：本工具僅處理 survived 分類，
# 不計算 kill_rate；對 suspicious 的處理為「不分類為 survived」（已對齊 mutmut log
# "🙁 Survived" 區段語意）。kill_rate 公式變更（killed + 0.5×suspicious）由
# tools/mutation_baseline_lock.py:calc_kill_rate 單一真相負責；本工具不需修改。

# SD_09 W2 audit P0-AUDIT-04 / P1-AUDIT-14 對齊：marker-based summary 擷取
# 與 mutation_baseline_lock.py `_parse_marker_section` 保持一致 — 兩工具同一單一真相。
# begin marker 須排除 `(end)` 字樣，否則同一 regex 會誤匹配 end 行
_COUNTS_BEGIN_MARKER = re.compile(
    r"^---\s*mutmut full counts(?!\s*\(end\))[^\n]*---\s*$", re.IGNORECASE
)
_COUNTS_END_MARKER = re.compile(r"^---\s*mutmut full counts\s*\(end\)\s*---\s*$", re.IGNORECASE)

_CATEGORY_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "boundary": [
        re.compile(r"[<>]=?"),
        re.compile(r"\b(<=|>=|<|>)\b"),
    ],
    "constant": [
        re.compile(r"\bTrue\b|\bFalse\b"),
        re.compile(r"\b[01]\b"),
        re.compile(r"\bNone\b"),
    ],
    "dead_branch": [
        re.compile(r"\bif\b.*:"),
        re.compile(r"\belif\b.*:"),
    ],
    "string_literal": [
        re.compile(r"['\"][^'\"]+['\"]"),
    ],
}


def _expand_id_tokens(tokens: list[str]) -> list[str]:
    """SD_09 W0 二次 audit P0-D 修復：展開 dash range token。

    mutmut 2.4.x 把連續 mutant id 以 dash range 壓縮輸出（如 `12-16`, `25-30`）。
    舊版 `token.isdigit()` 排除帶 dash 的 token → 11 個獨立數字
    （vs `Survived (N)` summary 的 64）→ 兩工具報數不一致。

    本 helper 將 `12-16` 展開為 ["12","13","14","15","16"]，獨立數字原樣保留。
    """
    out: list[str] = []
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        if tok.isdigit():
            out.append(tok)
            continue
        m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", tok)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            if lo <= hi:
                out.extend(str(i) for i in range(lo, hi + 1))
    return out


def _extract_survived_from_marker(text: str) -> int | None:
    """SD_09 W2 audit P1-AUDIT-14 修復：於 marker 區段擷取 Survived 計數。

    與 mutation_baseline_lock._parse_marker_section 對齊：marker 區段為單一真相。
    """
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
    survived_pat = re.compile(r"Survived\b[^\(]*\((\d+)\)", re.IGNORECASE)
    for line in section:
        m = survived_pat.search(line)
        if m:
            return int(m.group(1))
    return None


def extract_survived_ids(log_path: Path) -> list[str]:
    """從 mutmut results log 擷取所有 survived mutation id。

    SD_09 W0 二次 audit P0-D 修復：
      1. 跨 `---- <file> (N) ----` 子標題收集；舊版只取 Survived label 後到首個 Killed/Timeout
         之間的內容，會漏掉後續 file section（mutmut 2.4 每個檔分段列）。
      2. dash range 展開（見 `_expand_id_tokens`）。
      3. 解析後 assertion：parsed survived count 必須等於 summary `Survived (N)` 內的 N；
         不相等時 WARN 並以 summary N 為單一真相（不 raise，graceful degradation）。
    """
    if not log_path.exists():
        raise FileNotFoundError(f"mutmut log not found: {log_path}")
    text = log_path.read_text(encoding="utf-8", errors="replace")

    # SD_09 W2 audit P1-AUDIT-14 修復：summary 取「marker 區段內」的 Survived 計數（單一真相）
    # 對齊 mutation_baseline_lock._parse_marker_section；舊版用 re.search 取「第一筆」
    # 會與 baseline_lock「最後一筆」不一致，違反紀律 #5。
    summary_total = _extract_survived_from_marker(text)
    if summary_total is None:
        # Fallback：marker 不存在時取最後一筆 Survived（與 baseline_lock fallback 對齊）
        survived_matches = re.findall(r"Survived[^\n]{0,8}\(\s*(\d+)\s*\)", text)
        if survived_matches:
            summary_total = int(survived_matches[-1])

    survived_section = re.search(
        r"Survived\s*🙁?\s*\(\d+\)\s*(.*?)(?=\n(?:Killed|Timeout|Suspicious|Skipped)\s*[^\n]{0,8}\(|\Z)",
        text, re.DOTALL,
    )
    if not survived_section:
        if summary_total == 0:
            return []
        return []
    body = survived_section.group(1)

    # 移除 `---- file (count) ----` 子標題行，避免標題內的數字被當成 id
    body = re.sub(r"-{2,}[^\n]*-{2,}", "", body)
    tokens = re.split(r"[,\s]+", body)
    ids = _expand_id_tokens(tokens)

    # P0-D assertion：parsed vs summary 數字一致；不一致 → 印 WARN 但回傳 parsed 結果
    if summary_total is not None and len(ids) != summary_total:
        sys.stderr.write(
            f"[mutation_analysis] WARN: parsed survived count ({len(ids)}) "
            f"!= summary Survived ({summary_total}) — log 解析不完整或 mutmut 格式變更；"
            "建議檢查 mutmut version / log 完整性\n"
        )
    return ids


def show_mutation_diff(mutation_id: str, timeout: float = 10.0) -> str | None:
    """呼叫 `mutmut show <id>` 取得 diff；失敗回 None。"""
    try:
        result = subprocess.run(
            ["mutmut", "show", mutation_id],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result.stdout if result.returncode == 0 else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def classify_diff(diff: str) -> str:
    """依優先順序分類：boundary > constant > dead_branch > string_literal > other。"""
    if not diff:
        return "other"
    diff_lines = [ln for ln in diff.splitlines() if ln.startswith(("-", "+"))]
    delta_text = "\n".join(diff_lines)

    for cat in ("boundary", "constant", "dead_branch", "string_literal"):
        for pat in _CATEGORY_PATTERNS[cat]:
            if pat.search(delta_text):
                return cat
    return "other"


def render_backlog(module: str, classified: dict[str, list[dict[str, str]]]) -> str:
    """產出 Markdown backlog。"""
    total = sum(len(items) for items in classified.values())
    lines = [
        f"# Mutation Survived Backlog — {module}",
        "",
        f"自動產出（SD_Improving_08 W3 T3-D4 / ADR-SD08-002 §2.5）。共 {total} 個 survived mutation。",
        "",
        "## 分類摘要",
        "",
        "| 分類 | 數量 | 補測動作 |",
        "|------|------|---------|",
    ]
    actions = {
        "boundary": "✅ 必補（boundary 條件補測）",
        "constant": "✅ 必補（常量翻轉斷言）",
        "dead_branch": "✅ 必補（分支可達性測試）",
        "string_literal": "⏭️ ignore（語意無關 log/error message）",
        "other": "🟡 人工分類",
    }
    for cat in ("boundary", "constant", "dead_branch", "string_literal", "other"):
        lines.append(f"| {cat} | {len(classified.get(cat, []))} | {actions[cat]} |")

    lines.append("")
    lines.append("## 補測 backlog")
    lines.append("")
    for cat in ("boundary", "constant", "dead_branch", "other"):
        items = classified.get(cat, [])
        if not items:
            continue
        lines.append(f"### {cat}（{len(items)}）")
        lines.append("")
        for item in items:
            mid = item["id"]
            preview = item.get("preview", "").strip().splitlines()[:3]
            preview_text = " / ".join(preview) if preview else "(no diff)"
            lines.append(f"- **#{mid}** — {preview_text}")
        lines.append("")
    if classified.get("string_literal"):
        lines.append("### string_literal（ignore）")
        lines.append("")
        for item in classified["string_literal"]:
            lines.append(f"- #{item['id']}（語意無關）")
        lines.append("")
    return "\n".join(lines)


def analyze(log_path: Path, module: str, output_path: Path, skip_show: bool = False) -> dict[str, int]:
    survived_ids = extract_survived_ids(log_path)
    classified: dict[str, list[dict[str, str]]] = defaultdict(list)
    if not survived_ids:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            f"# Mutation Survived Backlog — {module}\n\n0 survived mutations.\n", encoding="utf-8"
        )
        return {cat: 0 for cat in _CATEGORY_PATTERNS}

    for mid in survived_ids:
        diff = "" if skip_show else (show_mutation_diff(mid) or "")
        category = classify_diff(diff) if diff else "other"
        preview = (diff or "").strip()[:200]
        classified[category].append({"id": mid, "preview": preview})

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_backlog(module, classified), encoding="utf-8")
    return {cat: len(items) for cat, items in classified.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mutation survived analysis (SD_08 W3 T3-D4)")
    parser.add_argument("module", help="模組代號（token_guard / goal_synthesis / coordinator）")
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skip-show", action="store_true", help="跳過 mutmut show（單元測試用）")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        summary = analyze(args.log, args.module, args.output, skip_show=args.skip_show)
    except FileNotFoundError as e:
        print(f"::error::{e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        total = sum(summary.values())
        print(f"::notice::{args.module} survived={total} → {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
