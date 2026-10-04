"""DEF-200-246 反向存在鎖：`integration_queue` 在 `autoclaude/` 內維持零生產寫者。

WHY：PRD §6.2 R-6.2-2 ③（dry_run 判決）與 G5 是「依設計未實作」（closed-by-decision）；
結案前提＝欄位只有定義（checkpoint_manager）與讀者（boot_self_check），缺的是尚不存在的
多 agent worktree 整合生產者。前提靠人記得會腐壞：第一個生產寫者出現時本鎖轉紅，逼人先重審
PRD §6.2 與 DEF-200-246 再放行。劃界：只判字面寫入形態；`setattr(cp, 動態名, …)` 看不到。
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_PKG = Path(__file__).resolve().parents[2] / "autoclaude"
_ALLOWED = {"utils/checkpoint_manager.py", "execution/boot_self_check.py"}  # 定義／讀者
_WRITE = re.compile(
    r"integration_queue(?:\[[^\]]*\])?\s*(?:=(?!=)|[-+|]=)"  # 屬性／kwarg／索引賦值
    r"|[\"']integration_queue[\"']\s*(?:\]\s*=(?!=)|:)"  # 字串鍵賦值／dict 字面
    r"|integration_queue\s*\.\s*(?:append|extend|insert|put|update|setdefault|pop|clear)\("
    r"|(?:setattr|setdefault)\(.*integration_queue"
)


def _scan(pkg: Path) -> list[str]:
    hits = []
    for p in sorted(pkg.rglob("*.py")):
        rel = p.relative_to(pkg).as_posix()
        if rel in _ALLOWED:
            continue
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if _WRITE.search(line):
                hits.append(f"{rel}:{n}: {line.strip()}")
    return hits


def test_no_production_writer_of_integration_queue():
    files = {p.relative_to(_PKG).as_posix() for p in _PKG.rglob("*.py")}
    assert _ALLOWED <= files, "掃描母體不含定義／讀者檔 ⇒ 路徑或改名使本鎖失明"
    hits = _scan(_PKG)
    assert not hits, (
        "integration_queue 出現生產寫者 ⇒ DEF-200-246 的結案前提（零寫者）已腐壞：先重審 "
        f"PRD §6.2 R-6.2-2 ③／G5 與 DEF-200-246，再更新本鎖。命中：{hits}"
    )


@pytest.mark.parametrize("src,expect_hit", [
    ("cp.integration_queue.append(q)", True),
    ("Cp(integration_queue=[q])", True),
    ('d["integration_queue"] = q', True),
    ("for q in cp.integration_queue:", False),
    ('getattr(cp, "integration_queue", None)', False),
])
def test_the_tripwire_has_teeth(tmp_path, src, expect_hit):
    """紅綠自證：寫入形態必須被抓、純讀取形態不得誤報（否則本鎖是恆綠或恆紅）。"""
    (tmp_path / "mod.py").write_text(src + "\n", encoding="utf-8")
    assert bool(_scan(tmp_path)) is expect_hit
