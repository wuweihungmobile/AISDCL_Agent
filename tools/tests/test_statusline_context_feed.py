#!/usr/bin/env python3
"""`tools/statusline_context_feed.py` 的回歸鎖（DEF-200-275 第七輪 D32-5）。

WHY：status line 的 command 走 shell 子行程，本檔存在的唯一理由是「絕不能讓 status
line 因為它而空白或報錯」——所以每條控制組都配一個破壞性輸入的注入組（壞 JSON／
`current_usage` 為 `null`／`session_id` 缺席），確認 fail-open 是真的 fail-open，
而不是「多數情況下不會炸」。
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MOD_PATH = _REPO_ROOT / "tools" / "statusline_context_feed.py"

sys.path.insert(0, str(_MOD_PATH.parent))
import statusline_context_feed as feed  # noqa: E402

#: 官方 status line schema 範例（Claude Code 文件站的 statusline 頁）節錄，供多支測試共用。
_SAMPLE = {
    "session_id": "abc-123",
    "model": {"id": "claude-fable-5-1", "display_name": "Fable"},
    "context_window": {
        "context_window_size": 1_000_000,
        "total_input_tokens": 393_900,
        "total_output_tokens": 1_200,
        "used_percentage": 39.4,
        "remaining_percentage": 60.6,
        "current_usage": {
            "input_tokens": 300_000, "output_tokens": 1_200,
            "cache_creation_input_tokens": 50_000, "cache_read_input_tokens": 43_900,
        },
    },
    "exceeds_200k_tokens": True,
    "version": "2.1.13",
}


def _run(
    stdin_text: str, argv: list[str] | None = None, env: dict | None = None,
) -> tuple[int, str]:
    """跑 `main()` 的子行程等級隔離（stdout 真的走 `print`，用 subprocess 才驗得到）。"""
    import subprocess
    proc = subprocess.run(
        [sys.executable, str(_MOD_PATH), *(argv or [])],
        input=stdin_text, capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, **(env or {})}, timeout=15, check=False,
    )
    return proc.returncode, proc.stdout


class ContextFeedPathTest(unittest.TestCase):
    def test_env_override_wins(self) -> None:
        base = str(Path("/tmp") / "xyz")
        with mock.patch.dict(os.environ, {feed.FEED_DIR_ENV: base}, clear=False):
            self.assertEqual(feed.context_feed_path("s1"), Path(base) / "s1.json")

    def test_default_is_home_autosdd(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(feed.FEED_DIR_ENV, None)
            got = feed.context_feed_path("s1")
        want = Path(os.path.expanduser("~")) / ".autosdd" / "context_feed" / "s1.json"
        self.assertEqual(got, want)


class BuildFeedDocTest(unittest.TestCase):
    def test_extracts_declared_subset(self) -> None:
        doc = feed.build_feed_doc(_SAMPLE)
        self.assertEqual(doc["schema"], 1)
        self.assertEqual(doc["session_id"], "abc-123")
        self.assertEqual(doc["model"], {"id": "claude-fable-5-1", "display_name": "Fable"})
        self.assertEqual(doc["context_window"], _SAMPLE["context_window"])
        self.assertTrue(doc["exceeds_200k_tokens"])
        self.assertEqual(doc["version"], "2.1.13")
        self.assertIn("+", doc["ts"][-6:], "ts 必須帶 offset，不可是 naive 本地時間戳")

    def test_missing_session_id_raises(self) -> None:
        """注入：`session_id` 缺席時本函式必須 raise，讓呼叫端的 fail-open 分支接住——
        若靜默用某個佔位字串頂替，feed 檔就會寫到錯的 session。"""
        with self.assertRaises(ValueError):
            feed.build_feed_doc({"model": {"id": "x"}})
        with self.assertRaises(ValueError):
            feed.build_feed_doc({"session_id": "   "})


class UiLineTest(unittest.TestCase):
    def test_normal_line_matches_official_example_shape(self) -> None:
        self.assertEqual(feed.ui_line(_SAMPLE), "ctx 39.4% 393.9k/1.0m | Fable")

    def test_null_current_usage_prints_na(self) -> None:
        """session 首次 API 呼叫前／`/compact` 後：官方契約是 `used_percentage=null`。"""
        payload = {**_SAMPLE, "context_window": {"used_percentage": None}}
        self.assertEqual(feed.ui_line(payload), "ctx n/a | Fable")

    def test_missing_model_falls_back_to_question_mark(self) -> None:
        self.assertEqual(feed.ui_line({"context_window": {"used_percentage": None}}),
                         "ctx n/a | ?")

    def test_high_water_mark_gets_bang_prefix(self) -> None:
        hot = {**_SAMPLE, "context_window": {**_SAMPLE["context_window"], "used_percentage": 94.0}}
        self.assertTrue(feed.ui_line(hot).startswith("!ctx 94.0%"))

    def test_below_threshold_has_no_bang(self) -> None:
        self.assertFalse(feed.ui_line(_SAMPLE).startswith("!"))

    def test_non_ascii_display_name_is_sanitized(self) -> None:
        payload = {**_SAMPLE, "model": {"id": "x", "display_name": "模型中文"}}
        line = feed.ui_line(payload)
        line.encode("ascii")  # 不 raise 即通過——本行本身就是斷言

    def test_numerator_uses_current_usage_not_total_input_tokens(self) -> None:
        """D32b-4：分子必須是 `current_usage` 三欄和，不是 `total_input_tokens`——
        `_SAMPLE` 裡兩者巧合同值（393,900）看不出錯用哪一個，這裡刻意灌兩個不同的
        數字：`total_input_tokens` 改成 700,000，`current_usage` 維持 393,900，
        錯用 `total_input_tokens` 會讓本測試印出 700.0k 而轉紅。"""
        payload = {**_SAMPLE, "context_window": {
            **_SAMPLE["context_window"], "total_input_tokens": 700_000}}
        self.assertEqual(feed.ui_line(payload), "ctx 39.4% 393.9k/1.0m | Fable")

    def test_missing_current_usage_numerator_is_question_mark(self) -> None:
        """`current_usage` 為 `null`（但 `used_percentage` 仍在）時分子印 `?`，不得
        回退去讀 `total_input_tokens`——那正是 D32b-4 要改掉的耦合。"""
        payload = {**_SAMPLE, "context_window": {
            **_SAMPLE["context_window"], "current_usage": None}}
        self.assertEqual(feed.ui_line(payload), "ctx 39.4% ?/1.0m | Fable")


class AtomicWriteAndMainTest(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.feed_dir = Path(self._tmp.name)

    def test_main_writes_feed_and_prints_ui_line(self) -> None:
        rc, out = _run(json.dumps(_SAMPLE), env={feed.FEED_DIR_ENV: str(self.feed_dir)})
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "ctx 39.4% 393.9k/1.0m | Fable")
        written = json.loads((self.feed_dir / "abc-123.json").read_text(encoding="utf-8"))
        self.assertEqual(written["session_id"], "abc-123")
        self.assertEqual(written["context_window"]["context_window_size"], 1_000_000)

    def test_garbage_stdin_never_crashes_and_writes_nothing(self) -> None:
        rc, out = _run("not json at all {{{", env={feed.FEED_DIR_ENV: str(self.feed_dir)})
        self.assertEqual(rc, 0, "status line 永不可因本檔而回非零")
        self.assertEqual(out.strip(), "ctx ? (feed error)")
        self.assertEqual(list(self.feed_dir.iterdir()), [])

    def test_empty_stdin_never_crashes(self) -> None:
        rc, out = _run("", env={feed.FEED_DIR_ENV: str(self.feed_dir)})
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "ctx ? (feed error)")

    def test_write_is_atomic_no_tmp_file_left_behind(self) -> None:
        path = self.feed_dir / "sid.json"
        feed._atomic_write_json(path, {"a": 1})
        self.assertTrue(path.is_file())
        leftovers = [p for p in self.feed_dir.iterdir() if p != path]
        self.assertEqual(leftovers, [], f"原子寫留下暫存檔：{leftovers}")

    def test_write_survives_transient_permission_error(self) -> None:
        """注入：Windows 教訓——目標檔被開著讀時 `os.replace` 短暫 `PermissionError`，
        重試幾次就該過。第一次呼叫失敗、第二次成功。"""
        path = self.feed_dir / "sid.json"
        real_replace = os.replace
        calls = {"n": 0}

        def flaky(src, dst):
            calls["n"] += 1
            if calls["n"] == 1:
                raise PermissionError("transient")
            return real_replace(src, dst)

        with mock.patch("os.replace", flaky):
            feed._atomic_write_json(path, {"a": 1})
        self.assertTrue(path.is_file())
        self.assertGreaterEqual(calls["n"], 2)


class SettingsSnippetTest(unittest.TestCase):
    def test_cli_prints_valid_json_with_existing_paths(self) -> None:
        rc, out = _run("", argv=["--print-settings-snippet"])
        self.assertEqual(rc, 0)
        doc = json.loads(out)  # 必須是合法 JSON——`json.loads` 不會就地 raise 才算過
        line = doc["statusLine"]
        self.assertEqual(line["type"], "command")
        self.assertEqual(line["padding"], 0)
        parts = line["command"].split(" ", 1)
        self.assertTrue(Path(parts[0]).is_file(), f"python 路徑不存在：{parts[0]}")
        self.assertTrue(Path(parts[1]).is_file(), f"腳本路徑不存在：{parts[1]}")
        self.assertNotIn("\\", line["command"], "要求 POSIX 正斜線")

    def test_settings_snippet_is_a_pure_function_of_this_checkout(self) -> None:
        doc = feed.settings_snippet()
        self.assertIn(str(_MOD_PATH.resolve().as_posix()), doc["statusLine"]["command"])


if __name__ == "__main__":
    unittest.main()
