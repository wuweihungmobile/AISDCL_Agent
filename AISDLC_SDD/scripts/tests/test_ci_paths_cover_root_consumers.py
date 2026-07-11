"""aisdlc-sdd-ci paths 覆蓋根層消費檔 meta contract — DEF-101-042 治本鎖（第五輪複審）.

WHY（Rule 9 / Rule 12 fail-loud）：scripts/tests 的 contract test 消費 monorepo
根層檔案時，其唯一 CI 載體 aisdlc-sdd-ci 的 paths 過濾必須包含該根層檔，否則
「只改根層消費檔」的變更下回歸鎖恰好不跑（假綠盲區）。此同構缺陷已三度出現
（DEF-101-037 → DEF-101-042 → 複審抓 sdd_hook_router.py 殘漏），人工盤點 paths
已被實證不可靠——本鎖把「paths 與消費點同步」升級為機械斷言，永久終結打地鼠：
未來任何測試新增根層消費點而漏補 paths，本測試即紅。

做法：正則掃描本目錄所有 test_*.py 源碼的兩種根層消費慣用法——
  ``os.path.join(_monorepo_root(), "a", "b")`` 與 ``_monorepo_root() / "a" / "b"``
——重組 repo 相對路徑；凡指向磁碟上存在且不在 AISDLC_SDD/ 下（該前綴由
"AISDLC_SDD/**" 天然覆蓋）的檔案，斷言被 workflow push＋pull_request paths
覆蓋（fnmatch glob 語意）。另附兩道防呆：push/PR 清單對稱鎖（防單側漏補）、
已知 5 條消費檔必被掃出（防正則退化令本鎖形同虛設）。
"""
from __future__ import annotations

import fnmatch
import os
import re

import yaml

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))


def _monorepo_root() -> str:
    # scripts/tests/ → scripts/ → AISDLC_SDD/ → monorepo 根
    return os.path.dirname(os.path.dirname(os.path.dirname(_TESTS_DIR)))


def _workflow_paths() -> tuple[list[str], list[str]]:
    wf = os.path.join(_monorepo_root(), ".github", "workflows", "aisdlc-sdd-ci.yml")
    with open(wf, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    on = data.get("on") or data.get(True)  # YAML 1.1 把裸 key `on` 解析為布林 True
    return on["push"]["paths"], on["pull_request"]["paths"]


_JOIN_RE = re.compile(r"os\.path\.join\(\s*_monorepo_root\(\)\s*,([^)]*)\)")
_SLASH_RE = re.compile(r'_monorepo_root\(\)((?:\s*/\s*"[^"]+")+)')
_STR_RE = re.compile(r'"([^"]+)"')


def _consumed_root_paths() -> set[str]:
    found: set[str] = set()
    for name in sorted(os.listdir(_TESTS_DIR)):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        with open(os.path.join(_TESTS_DIR, name), encoding="utf-8") as f:
            src = f.read()
        for m in _JOIN_RE.finditer(src):
            segs = _STR_RE.findall(m.group(1))
            if segs:
                found.add("/".join(segs))
        for m in _SLASH_RE.finditer(src):
            segs = _STR_RE.findall(m.group(1))
            if segs:
                found.add("/".join(segs))
    # 只留「磁碟上存在的檔案」——join 到目錄／動態片段者非本鎖標的
    return {p for p in found if os.path.isfile(os.path.join(_monorepo_root(), p))}


def test_push_and_pr_paths_symmetric():
    push, pr = _workflow_paths()
    assert push == pr, f"push 與 pull_request paths 不對稱（單側漏補）：{push} vs {pr}"


def test_known_consumers_detected():
    """正則退化防呆：已知 5 條根層消費檔必被掃出，否則本鎖形同虛設。"""
    consumed = _consumed_root_paths()
    expected = {
        "tools/check_ntfs_paths.py",
        "tools/git-hooks/pre-commit",
        ".claude/settings.json",
        "AutoClaude/.claude/settings.json",
        ".claude/hooks/sdd_hook_router.py",
    }
    missing = expected - consumed
    assert not missing, f"掃描器漏抓已知消費檔（正則退化）：{missing}"


def test_all_root_consumers_covered_by_ci_paths():
    push, _ = _workflow_paths()
    uncovered = [
        p
        for p in sorted(_consumed_root_paths())
        if not p.startswith("AISDLC_SDD/")
        and not any(fnmatch.fnmatch(p, pat) for pat in push)
    ]
    assert not uncovered, (
        f"根層消費檔未列入 aisdlc-sdd-ci paths"
        f"（只改該檔時其回歸鎖不會跑，DEF-101-042 同構）：{uncovered}"
    )
