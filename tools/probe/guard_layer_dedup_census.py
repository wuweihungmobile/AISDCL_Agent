#!/usr/bin/env python3
"""護欄層「可減法面」普查（R85／F1 落地）——把「還有多少行是重複的」變成可重跑的量測值。

WHY 這支檔非有不可
------------------
R85 的四方複審裁決是「護欄層單輪淨額必須 ≤ 0」，而 Architect 給的方向是「從**守散文**
與**守自己**兩桶找重複判準」。那個方向當輪只以散文交付 ⇒ 下一輪要「用同樣的方法」重跑
時結構上做不到——這與本 repo 對 R77 分群、R83 假紅普查下過的判決逐字同型
（`DEF-200-046`：沒有留下可重跑的產物，「每輪重跑」就是一句話）。

**本檔刻意住 `tools/probe/`，不住 `tools/tests/`**：後者是護欄層行數棘輪的量測面
（`_GUARD_LINE_PATTERN` 非遞迴 `*.py`），把普查工具放進去等於一邊量一邊把分子做大。

三個桶各自的判準（都刻意保守，寧可少報）
----------------------------------------
① `verbatim`   ——**逐字相同**的函式本體（去 docstring 後 AST 完全相等）。
② `scaffold`   ——同一個 class 內「同鷹架、只有常數不同」的測試方法（把 Constant 全部
                 抹成同一個佔位後 AST 相等）。這正是 R85-P2 已被 SD 判為**正當**的
                 收斂形態（逐字零損失、注入樣本一個不少）。
③ 代價面 ——②要付的樣本數鎖成本與測試方法數變化，見下。

🔴 本檔最重要的輸出不是「可省幾行」，是**這條路在算術上到不到得了目標**（R85／F1 立案）。
兩件事要分開講，因為 R85 當輪把它們混在一起講過一次：

  · **合併本身不會弱化判準——條件是同一輪補上「樣本數鎖」**。把 N 支同鷹架測試併成 1 支
    表驅動測試，`countTestCases()` 少 N-1、`MIN_TESTS` 得跟著下修，而下修就是把「靜默蒸發
    仍全綠」的窗口開大（SD 對 P2 那次 3279→3268 的裁決逐字如此）。但那個代價**只在沒補
    樣本數鎖時才成立**：補了之後，刪一列表列**當場**轉紅，比「刪一支方法只能靠 MIN_TESTS
    這個粗聚合察覺」更強。P2 的問題不是合併，是合併時漏補（R85／F1 已補齊該兩族）。
  · **真正的阻礙是算術**：樣本數鎖每族約 4 行 ⇒ 全部合併的淨額 ≈
    `scaffold_lines_net_estimate` − 4 × `scaffold_groups`，實測**遠不足以**吃掉 R85 那一輪
    的淨額。⇒ 若某一輪需要的減法量級大於本檔印出的數字，那一輪就**不可能**靠去重達標，
    必須動用棘輪自己指定的另一條出口（把 WHY 與史料搬出護欄層），而那條出口會動到
    `_GUARD_LINES_REPIN_LOG` 的既有列 ⇒ 依 append-only 指紋，只有收尾單人窗口做得了。

用法
----
    python tools/probe/guard_layer_dedup_census.py            # 印摘要
    python tools/probe/guard_layer_dedup_census.py --details  # 逐候選列出
    python tools/probe/guard_layer_dedup_census.py --json     # 可 diff 的輸出
"""
from __future__ import annotations

import argparse
import ast
import collections
import json
import pathlib
import sys

# 🔴 入口點印非 ASCII（本檔的摘要全是中文）⇒ 必須先武裝 UTF-8 stdio，否則 locale 表達
# 不了 CJK 時整段輸出變 `\uXXXX` 逃脫字面／表達得了但非 UTF-8 時是亂碼。體例逐字對齊
# 姊妹 probe（`shell_command_corpus.py`／`misstep_attribution.py`）：消費既有的
# `tools/_stdio_utf8` side-effect 模組，**不**在本檔再抄一份 reconfigure
# （`tools/tests/test_platform_utils_dedup.py` 的 shrink-only 棘輪守著複本數）。
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import _stdio_utf8  # noqa: E402,F401 — side effect：強制 stdout/stderr 為 UTF-8

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_TESTS = _ROOT / "tools" / "tests"

#: 併一組 N 支同鷹架測試時，表驅動版仍要留下的行（1 支方法 ＋ 每案 1 列表列）的估計。
#: 刻意寫成常數而不是猜：估得太樂觀會讓「可省行數」變成一個沒有人驗得了的數字。
_ROW_COST_LINES = 2


class _BlankConstants(ast.NodeTransformer):
    """把所有字面常數抹成同一個佔位——「只有注入字串不同」因此變成 AST 相等。"""

    def visit_Constant(self, node: ast.Constant) -> ast.Constant:  # noqa: N802
        return ast.copy_location(ast.Constant(value="<K>"), node)


def _significant_body(node: ast.AST) -> list[ast.stmt]:
    """函式本體去掉 docstring（docstring 是說明不是判準，比對它會低報重複）。"""
    return [s for s in node.body                                   # type: ignore[attr-defined]
            if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)
                    and isinstance(s.value.value, str))]


def _span(body: list[ast.stmt]) -> int:
    return body[-1].end_lineno - body[0].lineno + 1 if body else 0


def census(tests_dir: pathlib.Path | None = None) -> dict:
    """回 `{verbatim: [...], scaffold: [...], totals: {...}}`。純函式，不寫磁碟。"""
    tests_dir = tests_dir or _TESTS
    verbatim: dict[str, list] = collections.defaultdict(list)
    scaffold: dict[tuple, list] = collections.defaultdict(list)
    files = sorted(tests_dir.glob("*.py"))
    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body = _significant_body(node)
                if _span(body) >= 6:
                    key = ast.dump(ast.Module(body=body, type_ignores=[]))
                    verbatim[key].append([path.name, node.name, node.lineno, _span(body)])
            if not isinstance(node, ast.ClassDef):
                continue
            for meth in node.body:
                if not isinstance(meth, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                body = _significant_body(meth)
                if _span(body) < 4:
                    continue
                shape = _BlankConstants().visit(
                    ast.parse(ast.unparse(ast.Module(body=body, type_ignores=[]))))
                scaffold[(path.name, node.name, ast.dump(shape))].append(
                    [meth.name, meth.lineno, meth.end_lineno - meth.lineno + 1])

    vgroups = [v for v in verbatim.values() if len(v) > 1]
    sgroups = [{"file": k[0], "cls": k[1], "methods": v}
               for k, v in scaffold.items() if len(v) > 1]
    v_lines = sum(g[0][3] * (len(g) - 1) for g in vgroups)
    s_raw = sum(sum(m[2] for m in g["methods"][1:]) for g in sgroups)
    s_net = sum(max(0, sum(m[2] for m in g["methods"][1:])
                    - _ROW_COST_LINES * len(g["methods"])) for g in sgroups)
    s_methods = sum(len(g["methods"]) - 1 for g in sgroups)
    return {
        "files_scanned": len(files),
        "guard_lines": sum(len(p.read_text(encoding="utf-8").splitlines()) for p in files),
        "verbatim": vgroups,
        "scaffold": sgroups,
        "totals": {
            "verbatim_groups": len(vgroups), "verbatim_lines_upper_bound": v_lines,
            "scaffold_groups": len(sgroups), "scaffold_lines_raw": s_raw,
            "scaffold_lines_net_estimate": s_net,
            "test_methods_lost_if_all_merged": s_methods,
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--details", action="store_true", help="逐候選列出（人工判讀用）")
    ap.add_argument("--json", action="store_true", help="輸出可 diff 的 JSON")
    args = ap.parse_args(argv)
    data = census()
    if args.json:
        json.dump(data, sys.stdout, ensure_ascii=False, indent=1, sort_keys=True)
        print()
        return 0
    t = data["totals"]
    print(f"[guard-layer dedup census] {data['files_scanned']} 支檔／"
          f"{data['guard_lines']} 行（＝棘輪量的那個面）")
    print(f"  ① verbatim  ：{t['verbatim_groups']} 組，上界 {t['verbatim_lines_upper_bound']} 行"
          "（**上界**：本判準比對的是 AST，不同 self._run() 會被算成同一個本體——"
          "R85 實測 bootstrap.ps1 與 dev_start.ps1 那一組即為此類假陽性，逐組必須人工判讀）")
    print(f"  ② scaffold  ：{t['scaffold_groups']} 組，原始 {t['scaffold_lines_raw']} 行／"
          f"扣掉表列成本後淨估 {t['scaffold_lines_net_estimate']} 行")
    net = t["scaffold_lines_net_estimate"] - 4 * t["scaffold_groups"]
    print(f"  ③ 代價      ：全部合併會少掉 {t['test_methods_lost_if_all_merged']} 支測試方法 ⇒ "
          "`run_root_unittests.MIN_TESTS` 必須同額下修；**補上樣本數鎖後這個代價才會消失**"
          f"（每族約 4 行）⇒ ②真正可用的淨額 ≈ {net} 行。若某輪需要的減法大於這個數，"
          "去重這條路在算術上就到不了（見本檔 docstring 末段）")
    if args.details:
        for g in sorted(data["scaffold"],
                        key=lambda g: -sum(m[2] for m in g["methods"][1:])):
            saving = sum(m[2] for m in g["methods"][1:])
            print(f"\n  ~{saving:4d} 行  {g['file']}::{g['cls']}（{len(g['methods'])} 支同鷹架）")
            for name, lineno, span in g["methods"]:
                print(f"        L{lineno:<6d} {span:3d} 行  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
