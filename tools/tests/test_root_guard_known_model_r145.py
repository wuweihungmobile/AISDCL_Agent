#!/usr/bin/env python3
"""D21（DEF-200-275 第六輪，SD-09）：根層 `context_budget_guard.py` 補查表收斂階
——鏡射 SDD `context_window.py::_converge_pinned_window()`（D14），資料只有一個家
（`known_model_windows.json`，經 `sdd_latest.py` 解析 LATEST），根層不存第二份查表。
詳見 docs/06_quality/CrossPlatform_DEF200275_Context_Metering_Evidence.md〈第六輪〉。
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOK = _REPO_ROOT / ".claude" / "hooks" / "context_budget_guard.py"
_PLANNER = _REPO_ROOT / "tools" / "session_resume_planner.py"

sys.path.insert(0, str(_HOOK.parent))
import context_budget_guard as guard  # noqa: E402

_KNOWN = {"claude-fable-5-1": 1_000_000, "claude-haiku-4-5": 200_000}


class ConvergePinnedToKnownModelTests(unittest.TestCase):
    """D21：鏡射 SDD `context_window.py` 同名測試類——收斂方向、交叉否決、fail-open。"""

    def test_converges_to_smaller_table_value_for_haiku(self) -> None:
        window, source = guard.resolve_window(
            0, env_raw="967000", observed_model="claude-haiku-4-5", known_models=_KNOWN)
        self.assertEqual(window, 200_000)
        self.assertIn("已收斂", source)
        self.assertTrue(guard.may_block(source), "查表值不是保守下界，應可硬擋")

    def test_keeps_pinned_when_table_value_is_larger_for_fable(self) -> None:
        """D21：查表值≥指定值時不收斂，但來源說明須留下「有查過表」的證據。"""
        window, source = guard.resolve_window(
            0, env_raw="967000", observed_model="claude-fable-5-1", known_models=_KNOWN)
        self.assertEqual(window, 967_000)
        self.assertIn("查表", source)
        self.assertIn("claude-fable-5-1=1,000,000", source)
        self.assertIn("不收斂", source)
        self.assertNotIn("已收斂", source)

    def test_cc_env_raw_and_settings_window_converge_the_same_way(self) -> None:
        """②③④ 三階皆會收斂（根層沒有 SDD 那個「① 永不收斂」的 session 手動釘值概念）。"""
        for kwargs in (dict(cc_window_raw="967000"), dict(settings_window=967000)):
            with self.subTest(kwargs=kwargs):
                window, source = guard.resolve_window(
                    0, observed_model="claude-haiku-4-5", known_models=_KNOWN, **kwargs)
                self.assertEqual(window, 200_000)
                self.assertIn("已收斂", source)

    def test_observed_model_unknown_to_table_keeps_pinned_unchanged(self) -> None:
        """查得到表但 model 不在表裡＝「沒有東西可比」，與 SDD 同型：來源說明原樣不動。"""
        window, source = guard.resolve_window(
            0, env_raw="967000", observed_model="claude-mystery-9", known_models=_KNOWN)
        self.assertEqual((window, source), (967_000, guard.SOURCE_PINNED))

    def test_no_known_models_table_is_fail_open_and_silent(self) -> None:
        """表缺檔／解析失敗 fail-open：不收斂，來源說明不留「查過表」字樣。"""
        window, source = guard.resolve_window(
            0, env_raw="967000", observed_model="claude-fable-5-1", known_models=None)
        self.assertEqual((window, source), (967_000, guard.SOURCE_PINNED))
        self.assertNotIn("查表", source)

        window2, source2 = guard.resolve_window(
            0, env_raw="967000", observed_model="claude-fable-5-1", known_models={})
        self.assertEqual((window2, source2), (967_000, guard.SOURCE_PINNED))


class KnownModelWindowsPathFailOpenTests(unittest.TestCase):
    """D21：資料只有一個家——LATEST 版 `known_model_windows.json`，經 `sdd_latest.py`
    解析；四種失效（無 AISDLC_SDD／無版本目錄／解析失敗／檔不存在）皆 fail-open 回 `None`，
    不拋例外（hook 是 P0：任何未預期例外都必須 fail-open，見模組 docstring）。"""

    def test_no_aisdlc_sdd_directory_is_fail_open(self) -> None:
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as td:
            with contextlib.redirect_stderr(buf):
                path = guard.known_model_windows_path(root=Path(td))
        self.assertIsNone(path, "純 AutoClaude 部署（沒有 AISDLC_SDD 子專案）是常態，不是錯誤")
        # SA-F1：fail-open 六種失效路徑此前全靜默，方向不變但不可再靜默。
        self.assertTrue(buf.getvalue(), "fail-open 不該再靜默——必須印一行 stderr")
        self.assertIn("無 AISDLC_SDD 子專案", buf.getvalue())

    def test_aisdlc_sdd_present_but_no_version_directories_is_fail_open(self) -> None:
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sdd_root = root / "AISDLC_SDD"
            (sdd_root / "scripts").mkdir(parents=True)
            # SA-F1：需放進真的 sdd_version.py 才能重現「有子專案無版本目錄」
            # （空殼會變成另一種「LATEST 解析失敗」）。
            real_script = _REPO_ROOT / "AISDLC_SDD" / "scripts" / "sdd_version.py"
            (sdd_root / "scripts" / "sdd_version.py").write_text(
                real_script.read_text(encoding="utf-8"), encoding="utf-8")
            with contextlib.redirect_stderr(buf):
                path = guard.known_model_windows_path(root=root)
        self.assertIsNone(path)
        # SA-F1：與「無子專案」是不同失效種類，stderr 訊息須能分辨。
        self.assertTrue(buf.getvalue(), "fail-open 不該再靜默——必須印一行 stderr")
        self.assertIn("有子專案無版本目錄", buf.getvalue())

    def test_real_repo_resolves_to_a_readable_table(self) -> None:
        """正面控制組：本 repo 真的有 AISDLC_SDD/LATEST，路徑解析得到且讀得出真實資料。"""
        path = guard.known_model_windows_path()
        self.assertIsNotNone(path)
        self.assertTrue(path.is_file())
        table, note = guard.load_known_model_windows(path)
        self.assertEqual(table.get("claude-fable-5-1"), 1_000_000)
        self.assertEqual(table.get("claude-haiku-4-5"), 200_000)
        self.assertTrue(note, "D27：查表來源說明（refreshed_at／seeded_from）不得是空字串")

    def test_corrupt_json_is_fail_open_not_a_crash(self) -> None:
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.json"
            bad.write_text("{not json", encoding="utf-8")
            with contextlib.redirect_stderr(buf):
                result = guard.load_known_model_windows(bad)
        self.assertEqual(result, ({}, guard._NO_TABLE_NOTE))
        # SA-F1：JSON 損毀是 load_known_model_windows() 自己的 fail-open 之一。
        self.assertTrue(buf.getvalue(), "fail-open 不該再靜默——必須印一行 stderr")
        self.assertIn("JSON 損毀", buf.getvalue())

    def test_wrong_shape_json_is_fail_open(self) -> None:
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "shape.json"
            bad.write_text(json.dumps({"models": "not-a-dict"}), encoding="utf-8")
            with contextlib.redirect_stderr(buf):
                result = guard.load_known_model_windows(bad)
        self.assertEqual(result, ({}, guard._NO_TABLE_NOTE))
        self.assertTrue(buf.getvalue(), "fail-open 不該再靜默——必須印一行 stderr")
        self.assertIn("JSON 形狀不對", buf.getvalue())


class NormalizeModelIdTests(unittest.TestCase):
    """查表鍵正規化：去 `[1m]`／`-1m`、小寫、去日期尾碼——與 SDD 同名函式逐字同構
    （查表資料共用同一份檔，鍵的正規化規則不能各算各的）。"""

    def test_strips_wide_marker_and_lowercases(self) -> None:
        self.assertEqual(guard.normalize_model_id("Claude-Opus-5[1m]"), "claude-opus-5")
        self.assertEqual(guard.normalize_model_id("claude-opus-5-1m"), "claude-opus-5")

    def test_strips_date_suffix(self) -> None:
        self.assertEqual(guard.normalize_model_id("claude-sonnet-4-6-20260615"),
                         "claude-sonnet-4-6")

    def test_none_and_empty_are_empty_string(self) -> None:
        self.assertEqual(guard.normalize_model_id(None), "")
        self.assertEqual(guard.normalize_model_id(""), "")


class WindowEvidenceAlwaysQueriesTheRealTableTests(unittest.TestCase):
    """D27（DEF-200-275 第七輪，推翻 D21）：四方複審 ARCH-A4-01 判定「沒有 pin 時
    `window_evidence()` 不解析 LATEST」這個效能捷徑本身就是缺陷根因——沒有釘值的
    機器上（`AUTOSDD_CONTEXT_WINDOW` 只住個人 `~/.claude/settings.json`，不隨 clone
    走）分母因此少了 ⑥ 查表這一階，與 SDD `context_window.py` 對同一份逐字稿算出
    不同答案（差可達 5 倍）。本類別因此把「省一次查表」的舊行為測試**翻成**
    「無釘值仍會查到真實表」——效能代價改在 `sdd_latest.resolve_latest_root_fast()`
    的熱路徑解（見 `docs/06_quality/CrossPlatform_DEF200275_Context_Metering_
    Evidence.md`〈第七輪〉）。"""

    def test_no_pin_at_all_still_queries_the_real_table(self) -> None:
        # 隔離環境變數（DEF-200-281 同型教訓：夾具沒隔離會測到別的東西）。
        with unittest.mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(guard.WINDOW_ENV, None)
            os.environ.pop(guard.CC_WINDOW_ENV, None)
            evidence = guard.window_evidence(observed_model="claude-fable-5-1")
        # D27：本機真有 AISDLC_SDD/LATEST ⇒ 就算完全沒有任何 pin，也查得到、且真的
        # 是那份表的內容——這正是 ARCH-A4-01 判定 D21 缺失的那一階。
        self.assertEqual(evidence["known_models"].get("claude-fable-5-1"), 1_000_000)
        self.assertEqual(evidence["known_models"].get("claude-haiku-4-5"), 200_000)
        self.assertTrue(evidence["known_models_note"], "查表來源說明不得是空字串")

    def test_a_pin_present_triggers_a_real_table_lookup(self) -> None:
        import os
        old = os.environ.get(guard.WINDOW_ENV)
        os.environ[guard.WINDOW_ENV] = "967000"
        try:
            evidence = guard.window_evidence(observed_model="claude-fable-5-1")
        finally:
            if old is None:
                os.environ.pop(guard.WINDOW_ENV, None)
            else:
                os.environ[guard.WINDOW_ENV] = old
        # 本機真有 AISDLC_SDD/LATEST ⇒ 查得到、且真的是那份表的內容（不是空表）。
        self.assertEqual(evidence["known_models"].get("claude-fable-5-1"), 1_000_000)


class CheckReportPrintsConvergenceEvidenceTests(unittest.TestCase):
    """D21：`--check` 的 window 行須印出收斂證據；走真實 subprocess 驗證真的流到輸出。"""

    def _write_transcript(self, path: Path, used: int, model: str) -> None:
        usage = {"input_tokens": used, "cache_creation_input_tokens": 0,
                 "cache_read_input_tokens": 0}
        line = json.dumps({"type": "assistant",
                           "message": {"model": model, "usage": usage}})
        path.write_text(line + "\n", encoding="utf-8")

    def test_check_output_shows_the_table_lookup_even_when_not_converging(self) -> None:
        import os
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            transcript = Path(td) / "sess-r145.jsonl"
            self._write_transcript(transcript, 100_000, "claude-fable-5-1")
            env = dict(os.environ)
            env["AUTOSDD_CONTEXT_WINDOW"] = "967000"
            env["AUTOSDD_SENTINEL_OFF"] = "1"
            proc = subprocess.run(
                [sys.executable, str(_PLANNER), "--check", "--transcript", str(transcript)],
                capture_output=True, encoding="utf-8", errors="replace",
                timeout=60, check=False, env=env)
            self.assertEqual(proc.returncode, 0, proc.stderr[:2000])
            self.assertIn("查表", proc.stdout)
            self.assertIn("claude-fable-5-1=1,000,000", proc.stdout)
            self.assertIn("不收斂", proc.stdout)


if __name__ == "__main__":
    unittest.main()
