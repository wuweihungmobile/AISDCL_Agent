#!/usr/bin/env python3
"""ADR-XPLAT-012 條文一／二 Phase 1 觀察模式落地：`guard_line_taxonomy` 回歸鎖。

🔴 unittest.TestCase 風格（非 pytest 函式風格）：本 repo 根層四道閘門
（`tools/run_root_unittests.py` ＋ pre-push root-infra leg ＋ `root-infra-ci.yml` ＋
兩份 compat-ci）走 `unittest discover`，pytest 函式風格的測試檔會被整檔零收集
（R60 Scan-C 的 C-01；同型判例見 `test_adr_xplat001_c1c2_lock.py` 檔頭）。

涵蓋範圍：
  1. 三桶互斥、聯集＝全檔（對三支真實護欄檔＋本檔自己跑，不用合成語料）。
  2. 條文二 §3「第三道自證鎖」：真實含 shebang 的護欄檔，shebang 行必須歸斷言；
     PEP 263 編碼宣告半段因 repo 現查零支真實案例，改以最小合成語料驗證。
  3. 條文二 §4(b) 變異測試：把已知敘事行改寫成斷言，敘事行數必須下降——證明
     判準有鑑別力，不是套套邏輯。
  4. docstring 區塊內部空白行歸空白桶（訂正 3）。
  5. BOM 檔與語法錯誤檔的處置：跳過並標記，不中止（條文一 §4）。

執行：python tools/tests/test_guard_line_taxonomy_r99.py
      python -m unittest tools.tests.test_guard_line_taxonomy_r99 -v
      python -m pytest tools/tests/test_guard_line_taxonomy_r99.py -q
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO / "tools" / "lib"))

import guard_line_taxonomy as glt  # noqa: E402

#: ADR-XPLAT-012「決策與脈絡」實測證據段引用的三支頂格檔：各自含大量 `#` 註解與
#: docstring 敘事，是本分類器設計的直接動機來源（見該 ADR §1 的逐檔數字）。
_REAL_GUARD_FILES: tuple[str, ...] = (
    "tools/lib/quota_gate.py",
    ".claude/hooks/block_destructive_git.py",
    "tools/session_resume_planner.py",
)


def _read(rel: str) -> str:
    return (_REPO / rel).read_text(encoding="utf-8-sig")


class TestThreeBucketsPartitionRealGuardFiles(unittest.TestCase):
    """三桶互斥、聯集＝全檔非空白行＋空白行（對真實護欄檔跑）。"""

    def test_partition_holds_on_named_guard_files(self) -> None:
        targets = (*_REAL_GUARD_FILES, str(_HERE.relative_to(_REPO)))
        for rel in targets:
            with self.subTest(file=rel):
                source = _read(rel)
                total = len(source.splitlines())
                narrative, assertion, blank = glt.classify_lines(source)
                self.assertEqual(narrative & assertion, set(), "敘事／斷言重疊")
                self.assertEqual(narrative & blank, set(), "敘事／空白重疊")
                self.assertEqual(assertion & blank, set(), "斷言／空白重疊")
                self.assertEqual(
                    narrative | assertion | blank, set(range(1, total + 1)),
                    "三桶聯集未覆蓋全檔")


class TestForcedAssertionSelfCheck(unittest.TestCase):
    """條文二 §3「第三道自證鎖」：shebang／PEP 263 編碼宣告必須被強制歸斷言。

    shebang 半段用真實護欄檔（`.claude/hooks/block_destructive_git.py` 第一行就是
    `#!/usr/bin/env python`）；PEP 263 半段因 repo 現查（grep）零支 `.py` 帶真實
    編碼宣告，改以最小合成語料驗證，兩段各自獨立斷言、互不依賴同一份語料。
    """

    def test_real_shebang_file_forces_line_one_to_assertion(self) -> None:
        rel = ".claude/hooks/block_destructive_git.py"
        source = _read(rel)
        self.assertTrue(
            source.splitlines()[0].startswith("#!"),
            f"前提失效：{rel} 第一行已不是 shebang，換一支真實護欄檔")
        _narrative, assertion, _blank = glt.classify_lines(source)
        self.assertIn(1, assertion)

    def test_pep263_encoding_declaration_forces_assertion(self) -> None:
        source = "#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n\"\"\"doc.\"\"\"\nx = 1\n"
        _narrative, assertion, _blank = glt.classify_lines(source)
        self.assertTrue({1, 2}.issubset(assertion), "shebang 與編碼宣告行皆須歸斷言")


class TestMutationDiscriminatesNarrativeFromAssertion(unittest.TestCase):
    """條文二 §4(b) 變異測試：敘事改寫成斷言後，敘事行數必須下降。"""

    def test_rewriting_a_comment_line_into_code_drops_narrative_count(self) -> None:
        before = "x = 1\n# this line explains why x is chosen\ny = 2\n"
        after = "x = 1\nz = compute_replacement_for_the_explanatory_line()\ny = 2\n"
        narrative_before, _a1, _b1 = glt.classify_lines(before)
        narrative_after, _a2, _b2 = glt.classify_lines(after)
        self.assertEqual(
            len(narrative_before) - 1, len(narrative_after),
            "把唯一一行敘事改寫成程式碼後，敘事行數必須恰好少 1——"
            "若判準對這個變異無感，代表它只是在套套邏輯地回聲輸入")


class TestDocstringInternalBlankLineIsBlankNotNarrative(unittest.TestCase):
    """訂正 3：docstring 區塊內部的空白行歸空白桶，不歸敘事桶。"""

    def test_blank_line_inside_module_docstring(self) -> None:
        source = '"""Title.\n\nBody after a blank line.\n"""\nx = 1\n'
        narrative, _assertion, blank = glt.classify_lines(source)
        self.assertIn(2, blank)
        self.assertNotIn(2, narrative)
        self.assertIn(1, narrative)
        self.assertIn(3, narrative)


class TestUnparseableFilesAreSkippedAndMarkedNotAborted(unittest.TestCase):
    """條文一 §4：BOM 檔與語法錯誤檔的處置——跳過並標記，不中止。"""

    def test_bom_prefixed_valid_source_is_not_unparseable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bom_ok.py"
            p.write_bytes(b"\xef\xbb\xbf" + b"x = 1\n")
            result = glt.classify_file(p)
        self.assertFalse(
            result.unparseable, "utf-8-sig 應剝除 BOM，讓合法原始碼正常解析")
        self.assertEqual(result.assertion, 1)

    def test_syntax_error_file_is_marked_unparseable_not_raised(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "broken.py"
            p.write_text("def f(:\n    pass\n", encoding="utf-8")
            result = glt.classify_file(p)
        self.assertTrue(result.unparseable)
        self.assertEqual(
            (result.narrative, result.assertion, result.blank), (0, 0, 0))

    def test_a_batch_with_one_bad_file_does_not_abort_the_others(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            good = Path(td) / "good.py"
            good.write_text("x = 1\n", encoding="utf-8")
            bad = Path(td) / "bad.py"
            bad.write_text("def(:\n", encoding="utf-8")
            results = [glt.classify_file(p) for p in (good, bad)]
        self.assertFalse(results[0].unparseable)
        self.assertTrue(results[1].unparseable)


if __name__ == "__main__":
    unittest.main()
