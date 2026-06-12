"""W1a DoD：阻擋未來測試再次直接存取 runner._checkpoint_mgr / runner._knowledge_base（SD_03 §3.3）。

目的：確保測試解耦成果長期有效。任何新增直接存取 runner._checkpoint_mgr 或
runner._knowledge_base 的測試程式碼，此阻擋測試將會 fail，提示開發者改用
constructor injection（checkpoint_mgr= / knowledge_base=）。
"""
from __future__ import annotations

import re
from pathlib import Path

TESTS_DIR = Path(__file__).parent.parent

FORBIDDEN_PATTERNS = [
    re.compile(r"\brunner\._checkpoint_mgr\b"),
    re.compile(r"\brunner\._knowledge_base\b"),
]

EXCLUDE_FILES = {
    Path(__file__).name,  # 本檔案本身
}

EXCLUDE_COMMENT_PATTERN = re.compile(r"#.*$", re.MULTILINE)


def _scan_test_files():
    """掃描 tests/ 下所有 .py 檔，回傳 (file, line_no, pattern) 違規清單。"""
    violations = []
    for py_file in TESTS_DIR.rglob("*.py"):
        if py_file.name in EXCLUDE_FILES:
            continue
        if "__pycache__" in str(py_file):
            continue
        content = py_file.read_text(encoding="utf-8")
        # 移除行內注釋（避免注釋行被誤判）
        stripped = EXCLUDE_COMMENT_PATTERN.sub("", content)
        for pattern in FORBIDDEN_PATTERNS:
            for match in pattern.finditer(stripped):
                line_no = content[: match.start()].count("\n") + 1
                violations.append((py_file.relative_to(TESTS_DIR), line_no, pattern.pattern))
    return violations


def test_no_direct_internal_alias_access():
    """任何測試程式碼不得直接存取 runner._checkpoint_mgr / runner._knowledge_base。

    請改用 constructor injection：
      cp_mgr = CheckpointManager(...)
      runner = PlaybookRunner(..., checkpoint_mgr=cp_mgr)
      # 然後直接使用 cp_mgr 而非 runner._checkpoint_mgr
    """
    violations = _scan_test_files()
    if violations:
        details = "\n".join(
            f"  {f}:{ln} — 違反 pattern: {pat}"
            for f, ln, pat in violations
        )
        raise AssertionError(
            f"W1a DoD 違反：測試程式碼直接存取 internal alias（{len(violations)} 處）：\n{details}\n\n"
            "修復方式：改用 constructor injection（checkpoint_mgr= / knowledge_base= 參數）。"
        )
