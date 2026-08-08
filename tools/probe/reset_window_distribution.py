#!/usr/bin/env python3
"""量測「撞線 → 額度恢復」等待窗的實際分布（ADR-XPLAT-004 §2.7 的可重跑產物）。"""
# WHY 這支必須存在，而不是把數字寫進 ADR 就算了
# ------------------------------------------------
# R79 對 R77 的訂正逐字記載過一次同型失誤：R77 宣稱「每輪重跑一次分群」，卻**沒有留下
# 任何可重跑的產物**，於是那條要求在 R77~R78 之間結構上做不到，而 ADR 裡的百分比被
# 當成常數引用了五輪。本檔是 `misstep_attribution.py` 的同型物：來源清單、判準、每一
# 筆的歸屬理由都在檔內，輸出是可 diff 的 `.jsonl`。
#
# 🔴 本檔產出的每一個數字都是**量測值，不是常數**。ADR §2.7 明文寫了「不得被引用為常數」；
# 要對照就重跑，別抄。
#
# 判準一律**沿用** `.claude/hooks/context_budget_guard.py` 的既有實作
# （`SYNTHETIC_MODEL` 指紋／`classify_limit`／`parse_reset_at`），不在這裡另寫一份：
# 「同一份知識住兩個家」是本 repo 反覆判過的形態，而撞線偵測的權威實作住在那支 hook
# （它結構上不能 import 別人，只能是被 import 的那一方）。
#
# 為什麼要 episode 級的數字，而不是只報事件筆數：一次撞線會在 16 秒內讓**每個 subagent**
# 各留一筆合成記錄（實測最大一群 46 筆）。直接對事件取中位數會被扇出規模主導 ⇒ 那是
# 「當時開了幾個 subagent」的分布，不是「等待窗」的分布。以 reset 時刻分群才是 episode。
#
# 用法
# ----
#     python tools/probe/reset_window_distribution.py
#     python tools/probe/reset_window_distribution.py --base <逐字稿根> --out <jsonl>
from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))

# 🔴 本檔整份輸出都是中文 ⇒ 非 UTF-8 locale 下 stdout 會直接 UnicodeEncodeError、
# stderr 會降解成 `\uXXXX`（R74 的 P0 同源，且本機 UTF-8 環境**結構上重現不了**，
# 不得以「我這裡中文是好的」當通過依據）。同 `probe/audit_session.py` 的既有作法。
import context_budget_guard as guard  # noqa: E402

import _stdio_utf8  # noqa: E402,F401  （side effect：強制 stdout/stderr 為 UTF-8）


def limit_events(path: Path):
    """該逐字稿裡**每一筆** harness 合成的額度／錯誤事件 `(timestamp, text)`。

    `guard.latest_limit_event()` 只回最後一筆（它的呼叫端只需要那一筆），這裡需要全部，
    故就地沿用它的**指紋定義**（`type=assistant` ＋ `model == SYNTHETIC_MODEL`）掃全檔。
    """
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if guard.SYNTHETIC_MODEL not in line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                msg = rec.get("message") or {}
                if rec.get("type") != "assistant" or msg.get("model") != guard.SYNTHETIC_MODEL:
                    continue
                body = msg.get("content")
                text = body if isinstance(body, str) else " ".join(
                    str(b.get("text", "")) for b in body or [] if isinstance(b, dict))
                yield str(rec.get("timestamp") or ""), text
    except OSError:
        return


def local_time(stamp: str) -> datetime | None:
    """逐字稿的 ISO-8601（UTC）→ 本機時區；壞值回 `None`。"""
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone()
    except (TypeError, ValueError):
        return None


def scan(base: Path) -> tuple[list[dict], Counter, Counter]:
    """回 `(session-limit 逐筆, 事件分類計數, reset 字面計數)`。"""
    rows: list[dict] = []
    kinds: Counter = Counter()
    literals: Counter = Counter()
    for path in sorted(base.rglob("*.jsonl")):
        for stamp, text in limit_events(path):
            kind = guard.classify_limit(text)
            kinds[kind] += 1
            if kind != guard.LIMIT_SESSION:
                continue
            anchor = local_time(stamp)
            match = guard._RESET_RE.search(text)
            if match:
                literals[match.group(0).lower()] += 1
            reset = guard.parse_reset_at(text, anchor) if anchor else None
            rows.append({
                "file": path.name,
                "hit": anchor.isoformat(timespec="seconds") if anchor else None,
                "reset": reset.isoformat(timespec="seconds") if reset else None,
                "minutes": (round((reset - anchor).total_seconds() / 60.0, 1)
                            if reset and anchor else None),
                "text": text[:160],
            })
    return rows, kinds, literals


def episodes(rows: list[dict], *, earliest: bool = True) -> dict[str, float]:
    """以 reset 時刻分群 ⇒ `{reset: 該 episode 的 hit→reset 分鐘數}`。

    🔴 取 **max** 而不是 min，而這個方向很容易寫反（R80 落地時我第一版就寫反了）：
    `minutes = reset - hit`，所以**最早**撞的那一筆的值**最大**；一個 episode 裡的其餘
    記錄是扇出的 subagent 陸續撞到同一道牆，它們離 reset 更近 ⇒ 值更小。
    「這次停機多久」問的是從第一個人撞到牆算起 ⇒ 取 max。

    `earliest=False` 改取 min＝「單一觀測者看到的最短窗」。兩個量回答不同問題，都有用：
    max 決定「要撐多久」，min 決定「一個剛醒來的哨兵最壞可能只剩多少時間可反應」。
    """
    groups: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if row["reset"] and row["minutes"] is not None:
            groups[row["reset"]].append(row["minutes"])
    pick = max if earliest else min
    return {reset: pick(vals) for reset, vals in sorted(groups.items())}


def report(base: Path, out: Path) -> int:
    files = sorted(base.rglob("*.jsonl"))
    rows, kinds, literals = scan(base)
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                   encoding="utf-8", newline="\n")
    eps = sorted(episodes(rows).values())
    shortest = sorted(episodes(rows, earliest=False).values())
    print(f"逐字稿母體          {len(files)} 支（{base}）")
    print(f"事件分類            {dict(kinds)}")
    print(f"session-limit 事件  {len(rows)} 筆；解得出 reset 的 "
          f"{sum(1 for r in rows if r['minutes'] is not None)} 筆")
    print(f"reset 相異字面      {len(literals)} 個 {dict(literals)}")
    if not eps:
        print("🔴 一個 episode 都沒有 ⇒ 這台機器沒有撞線史，本次量測沒有結論可下。")
        return 1
    print(f"相異撞線 episode    {len(eps)} 個")
    print(f"episode hit→reset   min={eps[0]} / median={statistics.median(eps)} / "
          f"max={eps[-1]} 分鐘")
    print(f"  ≤16 分／≤50 分     {sum(1 for m in eps if m <= 16)}／"
          f"{sum(1 for m in eps if m <= 50)}（分母 {len(eps)}）")
    print(f"  >300 分（>5 小時） {sum(1 for m in eps if m > 300)}"
          "　←（這一格是 0 就代表「要度過五小時」那個前提不成立）")
    print(f"  全部（分鐘）       {eps}")
    print(f"單一觀測者最短窗    min={shortest[0]} / median={statistics.median(shortest)} "
          f"/ max={shortest[-1]} 分鐘　←（決定「剛醒來的哨兵最壞剩多少時間」）")
    print(f"  全部（分鐘）       {shortest}")
    print(f"逐筆明細            {out}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="reset_window_distribution.py", allow_abbrev=False,
        description="撞線→reset 等待窗的實測分布（ADR-XPLAT-004 §2.7）")
    parser.add_argument("--base", default=str(Path.home() / ".claude" / "projects"),
                        help="逐字稿根目錄（預設 ~/.claude/projects）")
    parser.add_argument("--out", default=None, help="逐筆 jsonl 落點")
    args = parser.parse_args(argv)
    base = Path(args.base)
    if not base.is_dir():
        print(f"❌ 逐字稿根目錄不存在：{base}", file=sys.stderr)
        return 1
    # 🔴 預設落在系統暫存而**不是** repo 內。兩個理由，第二個是本輪實測踩到的：
    # ① repo 內不得有可寫暫存產物（`tools/tests/test_platform_neutral_paths.py` 有專屬判準）；
    # ② 它會以**未追蹤檔**出現在 `git status`，而本 repo 有好幾道鎖的掃描面正是
    #    `git status`／`git ls-files` ⇒ 一個純量測產物會讓別人的閘門漂移（R79 就是為此
    #    把一支 venv 建在 repo 之外）。要留檔請顯式給 `--out`。
    out = Path(args.out) if args.out else (
        Path(tempfile.gettempdir()) / "autosdd_reset_window_distribution.jsonl")
    return report(base, out)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
