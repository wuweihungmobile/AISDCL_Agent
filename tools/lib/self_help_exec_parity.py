"""腳本自述用法 ↔ git 索引 exec bit 的對等判準（R80 包 F／S8-01）。

為何住在 `tools/lib/` 而不是 `tools/check_script_parity.py` 裡（R80 收尾包移出）：
那支消費端受 `AutoClaude/tools/check_loc_budget.py` 的 SPECIAL_FILES **raw-line 棘輪**
管，而該棘輪以「納管當下實際行數」設定＝**零餘裕**（實測 HEAD 1618 ＝ 門檻 1618）⇒
在它裡面新增任何一道判準都必然破線，而破線的合法出口只有「刪等量以上的行／抽共用
模組」（先例 `tools/lib/ci_liveness.py`、`tools/lib/defect_ledger_index.py`）。
判準本體與它的 WHY 一起搬過來，消費端只留一行呼叫——**不得**為了讓它留在原地而調高門檻。

🔴 缺陷本體（實測，非假設）：`AISDLC_SDD/<LATEST>/tools/init_project.sh` 的 `-h`
逐字印出 `  ./init_project.sh [選項]`，而該檔的 git 索引模式是 **100644**。隔離容器
內 fresh clone 照著跑的實測結果是 `rc=126`、stderr 逐字 `Permission denied`。
它是整個框架的**安裝入口** ⇒ mac/Linux 使用者第一步就撞牆。

為什麼三個平面同時看不見它：
  · Windows：NTFS 沒有 exec bit，且本 repo 一律以 `bash x.sh` 形態呼叫；
  · CI：全庫 workflow 對 `./….sh` 直呼形態命中 0（都走 `bash x.sh`）；
  · 既有鎖：`tools/tests/test_platform_neutral_paths.py::TestExecBitIsGovernedViaTheGitIndex`
    只掃 **`.md` 文件**裡的 `./x.sh`——腳本**自己的 --help 輸出**不是 .md，
    結構上不在它的射程內。本模組補的就是這一面（同一條判準、換一個掃描面）。

判準：凡一支 shell 腳本的內文出現「以 `./` 直呼**它自己**」的形態，它的 git 索引
模式就必須是 100755。刻意只判「自己呼叫自己」——腳本裡指向**別支**腳本的 `./x.sh`
多半是在講使用者自己專案的檔案（同 `resolve_doc_script()` 的假紅取捨）。
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from pathlib import Path

_SELF_HELP_DOT_SLASH_RE = re.compile(r"(?<![\w./-])\./([A-Za-z0-9_./-]+\.sh)\b")
_INDEX_MODE_EXEC = "100755"
#: 凍結版（Copy-on-Evolve 禁改）的同型存量**站點數**（不是檔數，體例同 `.md` 側的
#: `_BARE_SH_DOC_DEBT_FROZEN`）：29 支 `init_project.sh`（v0.01~v0.29）× 各 4 行
#: （該檔 :42/:67/:70/:73）＝116。R80 只把 LATEST 那一支改成 100755（`git
#: update-index --chmod=+x`，不動內容故不碰任何 hash 釘選）。
#: 🔴 這是**可見的欠債，不是豁免**，判準為雙向精確比對：多一筆＝有人把同型缺陷複製
#: 進凍結版；少一筆＝有人動了禁改的凍結版（那本身就是必須被看見的事件）。
_SELF_HELP_DEBT_FROZEN = 116


def index_modes(repo_root: Path) -> dict[str, str]:
    """`git ls-files -s` → {repo 相對路徑: 模式}。空 dict ＝取數管道壞掉。"""
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "-s"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
    )
    if proc.returncode != 0:
        return {}
    modes: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        head, sep, path = line.partition("\t")
        if sep and head.split():
            modes[path.strip()] = head.split()[0]
    return modes


def self_help_offenders(
    texts: dict[str, str], modes: dict[str, str]
) -> list[tuple[str, int]]:
    """(路徑, 行號) —— 腳本教人 `./自己`、而自己的索引模式不是 100755 的站點。

    純函式（供測試注入合成輸入），不碰磁碟。
    """
    out: list[tuple[str, int]] = []
    for rel, text in texts.items():
        basename = rel.rsplit("/", 1)[-1]
        if modes.get(rel) == _INDEX_MODE_EXEC:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for match in _SELF_HELP_DOT_SLASH_RE.finditer(line):
                if match.group(1).rsplit("/", 1)[-1] == basename:
                    out.append((rel, lineno))
    return out


def check(
    repo_root: Path,
    resolve_latest: Callable[[Path], Path | None],
    fail: Callable[[str], None],
) -> bool:
    """對真實 repo 跑一次；紅燈走呼叫端的 `fail`（紅燈輸出唯一出口），綠燈自己 print。"""
    modes = index_modes(repo_root)
    if not modes:
        fail("❌ 自述用法 ↔ exec bit 鎖：`git ls-files -s` 回空——取數管道壞掉，"
             "本檢查的結論無效（不得當成通過）")
        return False
    latest = resolve_latest(repo_root / "AISDLC_SDD")
    if latest is None:
        fail("❌ 自述用法 ↔ exec bit 鎖：LATEST 解析失敗，無法區分凍結版與活版")
        return False
    live_prefix = f"AISDLC_SDD/{latest.name}/"
    texts: dict[str, str] = {}
    for rel in modes:
        if not rel.endswith(".sh"):
            continue
        path = repo_root / rel
        if path.is_file():
            texts[rel] = path.read_text(encoding="utf-8", errors="replace")
    offenders = self_help_offenders(texts, modes)

    def _frozen(rel: str) -> bool:
        return rel.startswith("AISDLC_SDD/AISDLC_SDD_v0.") and not rel.startswith(
            live_prefix)

    live = [o for o in offenders if not _frozen(o[0])]
    frozen = [o for o in offenders if _frozen(o[0])]
    ok = True
    if live:
        fail("❌ 自述用法 ↔ exec bit 鎖：腳本自己的說明教人跑 `./x.sh`，但它的 git "
             "索引模式不是 100755 ⇒ mac/Linux 一 clone 照著做就 rc=126 "
             "`Permission denied`（Windows 因 NTFS 無 exec bit 結構上看不到）。"
             "修法二擇一：`git update-index --chmod=+x <檔>`，或把說明改寫成 "
             "`bash x.sh`：\n" + "\n".join(f"  {rel}:{n}" for rel, n in live))
        ok = False
    if len(frozen) != _SELF_HELP_DEBT_FROZEN:
        fail(f"❌ 自述用法 ↔ exec bit 鎖：凍結版同型存量由 {_SELF_HELP_DEBT_FROZEN} "
             f"變成 {len(frozen)}。多一筆＝新增同型缺陷；少一筆＝有人動了 "
             "Copy-on-Evolve 禁改的凍結版。兩向都請回來改這個數字並說明理由")
        ok = False
    if ok:
        print(f"✅ 自述用法 ↔ exec bit 鎖：活版 0 筆違規（凍結版可見欠債 {len(frozen)} 筆）")
    return ok
