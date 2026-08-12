#!/usr/bin/env python3
"""護欄層「守誰」分桶普查——把「哪一桶在長」變成可重跑、可 diff 的量測值。

WHY 這支檔非有不可（立案：`DEF-200-103` 承接的訴求 2）
------------------------------------------------------
上一輪 Architect 交出了一組分桶比例（守散文 34.2%／守 SDD 23.0%／守自己 14.0%／
守生產碼 ≤12.5%），並據此下了本 repo 目前最重要的架構判讀：

    問題不是「太多」，是**單一總量棘輪讓最便宜的那一桶（守散文）永遠贏**。

而那組比例**沒有留下任何可重跑載具**——`tools/probe/` 底下當時只有去重普查
（`guard_layer_dedup_census.py`），分桶邏輯只以散文交付。這與本 repo 對 R77 分群
（`DEF-200-046`）下過的判決逐字同型：沒有留下可重跑的產物，「每輪重跑」就是一句話。
更要緊的是**下游動作卡住了**：「把總量棘輪按桶拆」在桶還沒有定義之前結構上做不到。

**本檔刻意住 `tools/probe/`，不住 `tools/tests/`**：後者是護欄層行數棘輪的量測面
（非遞迴 `tools/tests/*.py`），把普查工具放進去等於一邊量一邊把分子做大。同一組理由
逐字適用於姊妹檔 `guard_layer_dedup_census.py`。

兩個 scope 是兩個不同的量，**數字不可互用**
--------------------------------------------
· ``--scope guard-lines``（預設）＝**非遞迴** ``tools/tests/*.py``。這是行數棘輪
  （`_FROZEN_GUARD_LINES`）真正管的那個面，也是唯一一個「淨額 ≤ 0 到期義務」在判的面。
· ``--scope wide`` ＝上一輪 Architect 那個 113,084 的面，實查其組成為四塊：
  ``tools/tests``（遞迴）＋``tools/lib``＋``tools/*.py``（**maxdepth 1**）＋``.claude/hooks``。
  🔴 因此它**不含** ``tools/probe/``、``tools/git-hooks/``、``tools/act/``——那不是本檔的
  選擇，是那個數字的定義使然；本檔照原定義量，並另外把落在定義外的 `.py` 行數以
  ``excluded_from_wide`` 一併印出，讓「定義外還有多少」不再隱形。

四個估計量：first-match 是**點估計**，真值住在一組上下界之間
------------------------------------------------------------
一支鎖檔常常同時守好幾件事（守 `CLAUDE.md` 的某段散文、也守 `tools/lib/` 的某個常數），
所以「一檔一桶」本質上是有損的。上一輪用的是 first-match（依優先序取第一個命中的桶），
它的偏誤方向是**確定的**：優先序在前的桶被高報、在後的桶被低報。本檔把這件事攤開：

===============  ===========================================================
估計量           語意
===============  ===========================================================
``exclusive``    該檔**只**參照到這一棵樹 ⇒ 歸屬無爭議。各桶的**下界**。
``firstmatch``   上一輪的啟發式（優先序見 `BUCKET_PRIORITY`）。點估計。
``dominant``     依**參照出現次數**取最多的那一桶（平手時退回優先序）。點估計，
                 比 first-match 少一個「優先序決定結果」的人為輸入。
``any``          該檔只要參照到就計入 ⇒ 各桶的**上界**。**分母 > 100%**（``--multi``）。
===============  ===========================================================

``--multi`` 印的就是 ``any``；``any`` 與 ``exclusive`` 的差距即「啟發式的失真幅度」，
本檔以 ``distortion_pp``（百分點）逐桶印出，不寫死在任何散文裡。

判準：怎麼認定「這支檔在守哪一棵樹」
------------------------------------
以正規表示式在**原始文字**（不只字串字面）上抓路徑樣字 token，因為本層的 WHY 大量
住在 docstring 與 `#` 註解裡、且慣例是用反引號寫路徑（`` `docs/06_quality/…` ``）。
**已知覆蓋邊界（誠實劃界，不假裝完整）**：
  ① 分段組出來的路徑抓不到（``Path(...) / "tools" / "tests"`` 只有兩個裸 token）。
     ⇒ 對 `root_infra`／`guard_self` 兩桶是**低報**方向。
  ② 自我參照已扣除（一支檔提到自己的檔名不算「守自己」），否則 `guard_self` 桶會因為
     每支檔都寫得出自己的名字而變成恆真。
  ③ 提及次數不等於判準強度。本檔量的是「守備標的分佈」，不是「判準有多強」。
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

# 🔴 入口點印非 ASCII（本檔摘要全是中文）⇒ 先武裝 UTF-8 stdio。體例逐字對齊姊妹 probe
# （`guard_layer_dedup_census.py`／`shell_command_corpus.py`）：消費既有的 side-effect
# 模組，**不**在本檔再抄一份 reconfigure（`test_platform_utils_dedup.py` 的 shrink-only
# 棘輪守著複本數）。
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import _stdio_utf8  # noqa: E402,F401 — side effect：強制 stdout/stderr 為 UTF-8

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
from guard_bucket_policy import (  # noqa: E402
    BUCKET_PRIORITY,
    BUCKET_TREES,
    CACHE_PARTS,
    WIDE_SURFACE_SPEC,
    bucket_lines,
    classify_units,
    guard_surface_files,
)

_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _lines(path: pathlib.Path) -> int:
    """行數口徑逐字對齊 `guard_lines_in_worktree()`（`splitlines()`、壞位元組不致命）。

    刻意不用 `wc -l`：後者對「最後一行沒有換行」的檔少算一行，兩個口徑混用會讓本檔的
    總量與棘輪的總量差幾行而沒有人知道差在哪。
    """
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


def _wide_files() -> tuple[list[pathlib.Path], list[pathlib.Path]]:
    """回 (落在 wide 定義內的 `.py`, 定義外但仍是根層護欄層的 `.py`)。"""
    inside: set[pathlib.Path] = set()
    for rel, recursive in WIDE_SURFACE_SPEC:
        base = _ROOT / rel
        if not base.is_dir():
            continue
        it = base.rglob("*.py") if recursive else base.glob("*.py")
        inside.update(p for p in it if not CACHE_PARTS & set(p.parts))
    # 定義外：根層 `tools/` 樹與 `.claude/` 樹裡其餘的 `.py`。
    everything: set[pathlib.Path] = set()
    for rel in ("tools", ".claude"):
        everything.update(
            p for p in (_ROOT / rel).rglob("*.py") if not CACHE_PARTS & set(p.parts)
        )
    return sorted(inside), sorted(everything - inside)


def census(paths: list[pathlib.Path], grain: str = "chunk") -> dict:
    """四個估計量的桶計。量測本體住 `guard_bucket_policy.classify_units`（唯一實作）。"""
    units = classify_units(_ROOT, paths, grain)
    total = sum(u["lines"] for u in units)
    tallies = {est: bucket_lines(units, est)
               for est in ("exclusive", "firstmatch", "dominant", "any")}
    out: dict = {"surface_lines": total, "surface_files": len(paths), "buckets": {}}
    for bucket in list(BUCKET_PRIORITY) + ["selfcontained", "mixed"]:
        lo, hi = tallies["exclusive"][bucket], tallies["any"][bucket]
        out["buckets"][bucket] = {
            est: tallies[est][bucket]
            for est in ("exclusive", "firstmatch", "dominant", "any")
        } | {"distortion_pp": round((hi - lo) * 100.0 / total, 1) if total else 0.0}
    out["per_unit"] = units
    return out


def _pct(n: int, total: int) -> str:
    return f"{n * 100.0 / total:5.1f}%" if total else "  n/a"


def _print_summary(report: dict, scope: str, multi: bool) -> None:
    total = report["surface_lines"]
    print(f"# scope={scope}  grain={report['grain']}  檔數={report['surface_files']}  行數={total}")
    print("# 🔴 兩個 scope 的數字不可互用（guard-lines＝棘輪管的面；"
          "wide＝上一輪那個 113,084 的面）")
    est = "any" if multi else "firstmatch"
    head = (f"{'桶':<16}{'exclusive(下界)':>18}{'firstmatch':>14}"
            f"{'dominant':>12}{'any(上界)':>14}{'失真pp':>9}")
    print(head)
    print("-" * len(head))
    acc = 0
    for bucket, row in report["buckets"].items():
        acc += row[est]
        print(f"{bucket:<16}{row['exclusive']:>9}{_pct(row['exclusive'], total):>9}"
              f"{_pct(row['firstmatch'], total):>14}{_pct(row['dominant'], total):>12}"
              f"{_pct(row['any'], total):>14}{row['distortion_pp']:>8.1f}")
    print(f"\n# 以 {est} 加總 = {acc}（{_pct(acc, total)}）"
          + ("　← any 是上界，分母必然 >100%" if multi else ""))
    if "excluded_from_wide" in report:
        exc = report["excluded_from_wide"]
        print(f"# wide 定義外但仍屬根層護欄層：{exc['files']} 支 / {exc['lines']} 行"
              f"（{sorted(exc['dirs'])}）")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__ and __doc__.splitlines()[0])
    ap.add_argument("--scope", choices=("guard-lines", "wide"), default="guard-lines")
    ap.add_argument("--grain", choices=("chunk", "file"), default="chunk",
                    help="chunk＝頂層 class/def 逐塊分類（預設；檔級 exclusive 恆 0、無鑑別力）；"
                         "file＝與上一輪可比對的粒度")
    ap.add_argument("--multi", action="store_true",
                    help="摘要改印 any（一檔可計入多桶，分母 > 100%%）——啟發式失真幅度的對照組")
    ap.add_argument("--details", action="store_true", help="逐檔列出歸屬與參照計數")
    ap.add_argument("--json", action="store_true", help="輸出可 diff 的 JSON")
    ap.add_argument("--jsonl", metavar="PATH", help="逐檔寫成可 diff 的 .jsonl")
    args = ap.parse_args(argv)

    if args.scope == "guard-lines":
        paths = guard_surface_files(_ROOT)
        report = census(paths, args.grain)
    else:
        inside, outside = _wide_files()
        report = census(inside, args.grain)
        report["excluded_from_wide"] = {
            "files": len(outside),
            "lines": sum(_lines(p) for p in outside),
            "dirs": sorted({p.parent.relative_to(_ROOT).as_posix() for p in outside}),
        }
    report["scope"] = args.scope
    report["grain"] = args.grain
    report["bucket_trees"] = {b: list(t) for b, t in BUCKET_TREES.items()}

    if args.jsonl:
        with open(args.jsonl, "w", encoding="utf-8") as fh:
            for row in report["per_unit"]:
                fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        print(f"# 已寫出 {args.jsonl}（{len(report['per_unit'])} 列）")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    _print_summary(report, args.scope, args.multi)
    if args.details:
        print("\n# 逐檔（exclusive / firstmatch / dominant ｜ 參照計數）")
        for row in sorted(report["per_unit"], key=lambda r: -r["lines"]):
            print(f"{row['lines']:>6}  {row['file']}::{row['unit']:<40} "
                  f"{row['exclusive']}/{row['firstmatch']}/{row['dominant']}  {row['refs']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
