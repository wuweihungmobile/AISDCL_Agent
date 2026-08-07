#!/usr/bin/env python3
"""跨語言腳本（`.sh`／`.ps1`）掃描面 SSOT（R60 Scan-E E-A-01）。

WHY：本 repo 對「active 的 `.sh`／`.ps1`」有兩套掃描面，過去各自硬編、且**形狀不同**：

  1. **CI 語法／編碼掃描面**——`root-infra-ci.yml` 第 2 道（pwsh `Parser::ParseFile`
     ＋ UTF-8 BOM 守門）與其三份本地鏡射（`tools/tests/test_ps51_compat.scan_trees()`／
     `tools/tests/test_ps1_bom._scan_prefixes()`／`tools/windows_smoke_local.ps1` 的
     `$ps1Trees`）：**遞迴**掃三棵固定樹 `tools/`、`AutoClaude/tools/`、
     `AISDLC_SDD/scripts/`，再加 LATEST 版樹（第 4 棵，路徑動態解析）。
  2. **parity enrollment 發現面**——`tools/check_script_parity.py`：**非遞迴** glob
     一份自己的四目錄名冊 `("tools", "tools/lib", "AutoClaude/tools",
     "AISDLC_SDD/scripts")`，另加 LATEST tools（那條 leg 本來就遞迴）。

形狀不一致的實測後果（R60 量測）：**今日兩邊掃到的檔案集合完全相同（各 35 支
`.sh`／`.ps1`，diff 為空）**——因為現存腳本剛好全躺在名冊逐一列出的目錄裡。但任何人
在既有樹下**新開一層子目錄**放腳本（例：`tools/ops/deploy.sh` ＋ `deploy.ps1`），
CI 的 `-Recurse` 會掃到它（語法／BOM 有守），parity enrollment 卻**看不到**它、不會
fail-loud 要求納管，於是 `check_script_parity` 自述的「新增成對腳本必為機械攔截」
靜默失效；而那份名冊自己**沒有任何完整性鎖**（R60 實查：生產碼、測試、缺陷帳本三面
grep，唯一相關斷言是「`tools/lib` 有沒有在名冊裡」的成員存在性，不是完整性），
所以「掃描面缺一個目錄」這件事沒有人會知道。CI 側早在 R13（CI-4）就為同一風險把
`AISDLC_SDD/scripts` 補上 `-Recurse` 做預防性收斂，parity 側從未跟上。

修法（R60）：掃描根收斂成本檔這一份名冊，且**列舉實作也只留這一份**
（`iter_tree_scripts()`）——parity 因此與 CI 同為遞迴形狀，`tools/lib` 不再需要
單獨列名（遞迴自動涵蓋），名冊由「4 目錄」降為「3 棵樹」。形狀一致性
（本檔名冊 == CI 第 2 道固定樹集合）與遞迴性另由
`tools/tests/test_script_scan_surface_ssot.py` 機械斷言。

消費者（改動本檔請同步檢視）：
  - `tools/check_script_parity.py`：`_PAIR_SCAN_DIRS`／`_discover_scripts()`
  - `tools/tests/test_ps51_compat.py`：`scan_trees()`
  - `tools/tests/test_ps1_bom.py`：`_scan_prefixes()`
  - `tools/tests/test_script_scan_surface_ssot.py`：本檔的守門（形狀一致性鎖）
  - `.github/workflows/root-infra-ci.yml` 第 2 道、`tools/windows_smoke_local.ps1`
    [1/9]：**非 Python**，改走本檔的 `--list` CLI（見下）

🔴 R79 ARCH（本檔最後一次結構變更）：上面最後兩個站點原本各自持有一份
`Get-ChildItem -Recurse -Filter *.ps1` 的**獨立列舉實作**（無法 import 本檔），
於是 repo 為了偵測「三份複本是否同步」養了 866 行對抗式正則錨機械
（`tools/tests/_ci_scan_anchors.py` 154 行 ＋ `tools/tests/test_ci_scan_anchors.py`
712 行），而該錨自己的 docstring 逐條列出三種**已實測抓不到**的逃逸形態
（`[System.IO.Directory]::GetFiles()`／`Get-Item`／`Resolve-Path`）——軍備競賽已
翻車兩次（R56→R57）。改法不是再加一條錨，而是**讓複本消失**：兩個非 Python 站點
改為呼叫本檔的 `--list` CLI 取得掃描面，於是「三份不同步」在結構上不可能發生，
866 行連同那三種逃逸一起退場。殘餘鎖只剩「兩個站點真的呼叫本檔、且沒有自持第二份
列舉」，落在 `tools/tests/test_script_scan_surface_ssot.py::TestNonPythonSitesCallTheSsot`。

**收錄什麼**：掃描面的**根、列舉方式、per-tree 檔數下限、LATEST 樹解析**。
per-tree 下限（`PS1_TREE_FLOORS`）自 R79 起收進本檔——它原本刻意留在各消費者
（理由：「各鎖自己的靈敏度參數」），但那個理由在「列舉實作由所有站點共用」之後
不再成立：下限一旦分散，`windows_smoke_local.ps1` 與 `test_ps51_compat` 兩份就得
再養一道同步鎖，正是本次要消滅的形態。仍**不**收錄 `test_ps1_bom._MIN_FILES`
（那是跨全部四棵樹的總數下限，語意不同、只有一個持有者，無複本問題）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 三棵固定掃描樹（一律**遞迴**列舉）。第 4 棵＝AISDLC_SDD LATEST 版樹，其路徑隨
# Copy-on-Evolve 升版而變，由 `AISDLC_SDD/scripts/sdd_version.py` SSOT 動態解析，
# 故刻意不列於此常數（列了就會每次升版失效）。
SCRIPT_SCAN_ROOTS: tuple[str, ...] = ("tools", "AutoClaude/tools", "AISDLC_SDD/scripts")

# LATEST 樹在各消費者裡的正規化 key（升版後登記／斷言不失效）。
LATEST_TREE_KEY = "LATEST"

# 掃描的副檔名（`.sh` POSIX 側、`.ps1` PowerShell 側）。
SCRIPT_SUFFIXES: tuple[str, ...] = (".sh", ".ps1")


def iter_tree_scripts(
    repo_root: Path, suffixes: tuple[str, ...] = SCRIPT_SUFFIXES
) -> list[str]:
    """三棵固定樹底下（**遞迴**）所有指定副檔名檔案的 repo 相對 posix 路徑（排序、去重）。

    這是掃描面的唯一列舉實作——遞迴性只寫在這裡一次，消費者不得自己 glob，
    否則「有人把某一處改回非遞迴」又會變成無訊號（本檔存在的理由）。
    不存在的樹靜默略過（`AISDLC_SDD/` 在極簡 checkout 下可能缺席），與原
    `_discover_scripts()` 的 `if not d.is_dir(): continue` 語意一致。
    """
    found: set[str] = set()
    for rel_root in SCRIPT_SCAN_ROOTS:
        found.update(iter_one_tree(repo_root, rel_root, suffixes))
    return sorted(found)


def iter_one_tree(
    repo_root: Path, rel_root: str, suffixes: tuple[str, ...] = SCRIPT_SUFFIXES
) -> list[str]:
    """單一棵樹底下（**遞迴**）的腳本清單（repo 相對 posix 路徑，排序去重）。

    `iter_tree_scripts()` 是本函式對 `SCRIPT_SCAN_ROOTS` 的聚合；per-tree 下限
    要逐棵樹判定（`--check-floors`），故列舉實作切在這一層而非再抄一份。
    """
    root = repo_root / rel_root
    if not root.is_dir():
        return []
    found: set[str] = set()
    for suffix in suffixes:
        for path in root.rglob(f"*{suffix}"):
            if path.is_file():
                found.add(path.relative_to(repo_root).as_posix())
    return sorted(found)


# ─────────────────────────────────────────────────────────────────────────────
# per-tree `.ps1` 檔數下限（掃描面靜默縮小＝樣式被改壞／目錄搬家時的唯一訊號）。
# 值＝實測支數，刻意刪減腳本時同步下修（R76：AutoClaude/tools 由 7 下修為 6，
# reschedule_g0_gatecheck.ps1 整支刪除、真孤兒）。鍵必須與
# `SCRIPT_SCAN_ROOTS` ＋ `LATEST_TREE_KEY` 完全對齊——缺鍵即 KeyError fail-loud，
# 不會靜默把新樹當 floor 0 放過（`test_script_scan_surface_ssot` 另有具名鎖）。
# ─────────────────────────────────────────────────────────────────────────────
PS1_TREE_FLOORS: dict[str, int] = {
    "tools": 8,
    "AutoClaude/tools": 6,
    "AISDLC_SDD/scripts": 2,
    LATEST_TREE_KEY: 4,
}


def latest_tree_rel(repo_root: Path) -> str:
    """LATEST 版樹的 repo 相對路徑（`AISDLC_SDD/AISDLC_SDD_v0.NN`）。

    一律委派 `AISDLC_SDD/scripts/sdd_version.py` SSOT（經 `tools/lib/sdd_latest.py`）
    ——DEF-101-133 禁止任何站點內嵌第二份版本 glob/regex。解析失敗即 raise
    （`AssertionError`），呼叫端不得靜默縮面。
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
    import sdd_latest  # noqa: PLC0415  （延後 import：模組層 import 不該動 sys.path）

    return f"AISDLC_SDD/{sdd_latest.resolve_latest_name(repo_root / 'AISDLC_SDD')}"


def ps1_scan_trees(repo_root: Path, with_latest: bool) -> list[tuple[str, str]]:
    """掃描樹清單 `[(樹 key, repo 相對前綴)]`；`with_latest` 時附上第 4 棵 LATEST 樹。"""
    trees = [(root, root) for root in SCRIPT_SCAN_ROOTS]
    if with_latest:
        trees.append((LATEST_TREE_KEY, latest_tree_rel(repo_root)))
    return trees


def _main(argv: list[str] | None = None) -> int:
    """`--list` CLI：給無法 import 本檔的非 Python 消費站點用（見模組 docstring）。

    stdout 只印路徑（每行一支），診斷訊息一律走 stderr——呼叫端直接把 stdout
    收成陣列即為掃描面，不需要再解析任何東西。
    """
    parser = argparse.ArgumentParser(
        description="腳本掃描面 SSOT 列舉器（非 Python 站點的唯一取用途徑）"
    )
    parser.add_argument("--list", action="store_true", required=True,
                        help="把掃描面逐行印到 stdout")
    parser.add_argument("--suffix", default=".ps1",
                        help="副檔名（預設 .ps1）")
    parser.add_argument("--with-latest", action="store_true",
                        help="含 AISDLC_SDD LATEST 版樹（凍結版一律排除）")
    parser.add_argument("--check-floors", action="store_true",
                        help="逐棵樹強制 PS1_TREE_FLOORS 下限，未達即 rc=1")
    parser.add_argument("--absolute", action="store_true",
                        help="印絕對路徑（執行站點用；預設印 repo 相對 posix 路徑）")
    parser.add_argument("--repo-root", default=None,
                        help="repo 根（預設＝本檔所在 tools/ 的上一層）")
    args = parser.parse_args(argv)

    repo_root = (
        Path(args.repo_root).resolve() if args.repo_root
        else Path(__file__).resolve().parents[1]
    )
    if args.check_floors and args.suffix != ".ps1":
        print("--check-floors 目前只對 --suffix .ps1 有下限表", file=sys.stderr)
        return 2
    # 🔴 R79 複審（ARCH blocking）：`--check-floors` 但不帶 `--with-latest` ⇒ 拒跑。
    # 判準的立論是「掃描面靜默縮小必須有訊號」，而 LATEST 版樹是 Copy-on-Evolve 每升
    # 一版就換路徑的那一棵——少寫一個旗標，它整棵（連同它的 per-tree 下限）就靜默
    # 退出掃描面，而 rc 仍是 0＝**縮面沒有任何訊號**，恰恰打掉那個立論。
    # 「要檢查下限、卻刻意不含 LATEST」在本 repo 沒有任何合法用途（三個消費站點
    # 全部同時帶兩個旗標，現查：Grep `--check-floors`），故這裡直接 fail-loud 而非警告。
    # 用 rc=2（用法錯誤）而非 rc=1（掃描面異常），讓兩種紅在呼叫端可分辨。
    if args.check_floors and not args.with_latest:
        print(
            "--check-floors 必須與 --with-latest 併用：少了它，AISDLC_SDD LATEST 版樹"
            "整棵連同其下限一起靜默退出掃描面，而 rc 仍為 0——那正是本旗標要防的事",
            file=sys.stderr,
        )
        return 2

    try:
        trees = ps1_scan_trees(repo_root, args.with_latest)
    except AssertionError as exc:  # LATEST 解析失敗＝fail-loud，不得靜默縮面
        print(f"掃描面 SSOT：{exc}", file=sys.stderr)
        return 1
    if args.with_latest:
        print(f"AISDLC_SDD LATEST 版：{trees[-1][1]}（其餘凍結版排除）", file=sys.stderr)

    rc = 0
    out: list[str] = []
    for key, prefix in trees:
        rels = iter_one_tree(repo_root, prefix, (args.suffix,))
        if args.check_floors:
            floor = PS1_TREE_FLOORS[key]
            print(f"  {prefix}：{len(rels)} 支（下限 {floor}）", file=sys.stderr)
            if len(rels) < floor:
                print(
                    f"::error::active {args.suffix} 掃描面異常縮小：{prefix} 僅 "
                    f"{len(rels)} 支（現況應 >= {floor}）——目錄搬家或樹清單疑似被改壞",
                    file=sys.stderr,
                )
                rc = 1
        out.extend(rels)

    for rel in out:
        print((repo_root / rel).as_posix() if args.absolute else rel)
    return rc


if __name__ == "__main__":
    # 🔴 R79 收斂包：本檔自 R79 起是**入口點**（`--list` CLI，兩個非 Python 站點
    # 與 pre-push root-infra leg 都直接跑它），而它印中文（`--check-floors` 的
    # `::error::` 訊息與 LATEST 版提示）⇒ 非 UTF-8 locale 下 stdout 會 UnicodeEncodeError、
    # stderr 降解成 \uXXXX（`tools/tests/test_subprocess_encoding_hygiene.py`
    # ::TestEntryPointStdioProtection 在守這件事，實測轉紅過）。
    # 刻意放在 `__main__` 內而非模組層：本檔同時被 4 支消費者 import 當函式庫，
    # 那些情境不該付 stdio 手術的副作用（同 test_adr_xplat001_c1c2_lock.py 的既有取捨）。
    import _stdio_utf8  # noqa: F401

    raise SystemExit(_main())
