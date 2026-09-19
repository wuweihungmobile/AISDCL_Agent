#!/usr/bin/env python3
"""`tools/lib/session_brief.py` 的回歸鎖（R158／P6：SessionStart 真實數字簡報）。 round-label-ok

四象限（IMPL_P6.md 指名）：額度〈有快取／無快取〉× context〈有 usage／無 usage〉，
每象限至少一支＋整合測試（量不到就照實說，不得讓呼叫端出例外）。接線面另見
`test_context_budget_guard.py::HandbackSessionStartAnnounceTest`。
"""
from __future__ import annotations

import sys
import types
import unittest
from datetime import UTC, datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
import quota_policy  # noqa: E402
import session_brief as sb  # noqa: E402

_NOW = datetime(2026, 9, 20, 1, 0, 0, tzinfo=UTC)


def _fake_quota_gate(*, read_quota=None, policy_env=None):
    """組一個最小的 `quota_gate` 替身：只帶 `quota_line()` 用得到的三個屬性。"""
    return types.SimpleNamespace(
        quota_policy=quota_policy,
        read_quota=read_quota or (lambda now, path=None: (_ for _ in ()).throw(
            OSError("test double 未預期被呼叫"))),
        policy_env=policy_env or (lambda: {}),
    )


def _cache_hit_state() -> quota_policy.QuotaState:
    axis = quota_policy.Axis("session", 40.0, None, via="limits[].percent")
    return quota_policy.QuotaState((axis,), "2026-09-20T00:00:00+08:00", "cache", "ok")


class QuotaLineTest(unittest.TestCase):
    """象限：額度〈有快取〉／〈無快取〉。零網路——`quota_gate` 全由呼叫端注入。"""

    def test_with_cache_describes_the_decision(self) -> None:
        state = _cache_hit_state()
        gate = _fake_quota_gate(read_quota=lambda now, path=None: state)
        got = sb.quota_line(gate, _NOW)
        self.assertIn("kind=session", got, "有快取時應印出逐軸判讀，而不是回退訊息")
        self.assertNotIn("額度快取不可用", got)

    def test_without_cache_falls_back_to_a_human_sentence(self) -> None:
        def _boom(now, path=None):
            raise OSError("合成：無快取")

        gate = _fake_quota_gate(read_quota=_boom)
        got = sb.quota_line(gate, _NOW)
        self.assertIn("額度快取不可用", got)
        self.assertIn("--pace", got, "回退訊息要帶得出查證指令")

    def test_load_policy_failure_also_falls_back(self) -> None:
        """不只 `read_quota` 會壞；`load_policy`／`decide`／`describe` 任何一環出例外
        都必須收斂成同一句人話，不得讓 SessionStart 整條崩潰。"""
        gate = types.SimpleNamespace(
            quota_policy=types.SimpleNamespace(
                load_policy=lambda env: (_ for _ in ()).throw(ValueError("壞掉的 policy")),
                decide=quota_policy.decide, describe=quota_policy.describe),
            read_quota=lambda now, path=None: _cache_hit_state(),
            policy_env=lambda: {},
        )
        got = sb.quota_line(gate, _NOW)
        self.assertIn("額度快取不可用", got)

    def test_default_now_is_used_when_omitted(self) -> None:
        """`now=None` 時走 `datetime.now().astimezone()`，不得拋例外（純粹是不崩潰的鑑別）。"""
        gate = _fake_quota_gate(read_quota=lambda now, path=None: _cache_hit_state())
        got = sb.quota_line(gate)
        self.assertIn("kind=session", got)


class ContextLineTest(unittest.TestCase):
    """象限：context〈有 usage〉／〈無 usage〉。四個依賴函式全部由呼叫端注入。"""

    def test_missing_transcript_reports_no_measurement(self) -> None:
        got = sb.context_line(
            None, scan_transcript=None, resolve_window=None,
            window_evidence=None, read_context_feed=None)
        self.assertEqual(got, sb._NO_MEASURE)

    def test_nonexistent_transcript_path_reports_no_measurement(self) -> None:
        got = sb.context_line(
            Path("/nonexistent/does-not-exist.jsonl"),
            scan_transcript=None, resolve_window=None,
            window_evidence=None, read_context_feed=None)
        self.assertEqual(got, sb._NO_MEASURE)

    def test_scan_returning_no_usage_reports_no_measurement(self) -> None:
        tmp = self._touch()
        got = sb.context_line(
            tmp, scan_transcript=lambda p: (None, 0, None),
            resolve_window=lambda *a, **k: (200_000, "x"),
            window_evidence=lambda *a, **k: {}, read_context_feed=lambda *a: {})
        self.assertEqual(got, sb._NO_MEASURE, "量不到 usage 不該假裝量到了")

    def test_scan_with_usage_reports_used_and_window(self) -> None:
        tmp = self._touch()
        got = sb.context_line(
            tmp,
            scan_transcript=lambda p: (12_345, 12_345, "claude-test-double-3"),
            resolve_window=lambda *a, **k: (1_000_000, "指定值（測試）"),
            window_evidence=lambda *a, **k: {}, read_context_feed=lambda *a: {})
        self.assertIn("used=12,345", got)
        self.assertIn("window=1,000,000", got)
        self.assertIn("1.2%", got)
        self.assertIn("指定值（測試）", got, "分母來源說明沒有帶進句子")

    def test_a_broken_dependency_falls_back_to_no_measurement(self) -> None:
        """任何一環（掃描／解析 window／讀 feed）拋例外都要收斂，不得讓 SessionStart 死掉。"""
        tmp = self._touch()

        def _boom(_p):
            raise ValueError("合成：掃描壞掉")

        got = sb.context_line(
            tmp, scan_transcript=_boom, resolve_window=None,
            window_evidence=None, read_context_feed=None)
        self.assertEqual(got, sb._NO_MEASURE)

    def test_non_positive_window_reports_no_measurement(self) -> None:
        """`window<=0` 是 `tier_of()` 定義過的「不對零做除法」的同型地雷，本檔獨立防一次。"""
        tmp = self._touch()
        got = sb.context_line(
            tmp, scan_transcript=lambda p: (100, 100, "m"),
            resolve_window=lambda *a, **k: (0, "壞掉的分母"),
            window_evidence=lambda *a, **k: {}, read_context_feed=lambda *a: {})
        self.assertEqual(got, sb._NO_MEASURE)

    def _touch(self) -> Path:
        import shutil
        import tempfile
        path = Path(tempfile.mkdtemp(prefix="session-brief-")) / "t.jsonl"
        path.write_text("{}\n", encoding="utf-8")
        self.addCleanup(shutil.rmtree, path.parent, True)
        return path


class SessionstartBriefTest(unittest.TestCase):
    """整合：四象限全組合都要含兩條查證指令 ＋ rc=2 澄清句，且不崩潰、不消失。"""

    def _payload(self, transcript: Path | None) -> dict:
        return {"transcript_path": str(transcript) if transcript else None}

    def test_cache_hit_and_usage_present(self) -> None:
        tmp = self._touch()
        gate = _fake_quota_gate(read_quota=lambda now, path=None: _cache_hit_state())
        got = sb.sessionstart_brief(
            self._payload(tmp), gate,
            scan_transcript=lambda p: (999, 999, "claude-test-double-3"),
            resolve_window=lambda *a, **k: (200_000, "指定值（測試）"),
            window_evidence=lambda *a, **k: {}, read_context_feed=lambda *a: {}, now=_NOW)
        self.assertIn("[SDD-CTX-GUARD]", got)
        self.assertIn("used=999", got)
        self.assertIn("kind=session", got)
        self._assert_common(got)

    def test_cache_hit_and_usage_absent(self) -> None:
        gate = _fake_quota_gate(read_quota=lambda now, path=None: _cache_hit_state())
        got = sb.sessionstart_brief(
            self._payload(None), gate,
            scan_transcript=None, resolve_window=None,
            window_evidence=None, read_context_feed=None, now=_NOW)
        self.assertIn(sb._NO_MEASURE, got)
        self.assertIn("kind=session", got)
        self._assert_common(got)

    def test_cache_miss_and_usage_present(self) -> None:
        tmp = self._touch()

        def _boom(now, path=None):
            raise OSError("合成：無快取")

        gate = _fake_quota_gate(read_quota=_boom)
        got = sb.sessionstart_brief(
            self._payload(tmp), gate,
            scan_transcript=lambda p: (1, 1, "claude-test-double-3"),
            resolve_window=lambda *a, **k: (200_000, "指定值（測試）"),
            window_evidence=lambda *a, **k: {}, read_context_feed=lambda *a: {}, now=_NOW)
        self.assertIn("used=1", got)
        self.assertIn(sb._QUOTA_UNAVAILABLE, got)
        self._assert_common(got)

    def test_cache_miss_and_usage_absent(self) -> None:
        """四象限最壞的一格：兩邊都量不到。簡報仍要送出，兩句 fail-open 訊息都在。"""

        def _boom(now, path=None):
            raise OSError("合成：無快取")

        gate = _fake_quota_gate(read_quota=_boom)
        got = sb.sessionstart_brief(
            self._payload(None), gate,
            scan_transcript=None, resolve_window=None,
            window_evidence=None, read_context_feed=None, now=_NOW)
        self.assertIn(sb._NO_MEASURE, got)
        self.assertIn(sb._QUOTA_UNAVAILABLE, got)
        self._assert_common(got)

    def _assert_common(self, brief: str) -> None:
        self.assertIn("python tools/session_resume_planner.py --check", brief)
        self.assertIn("python tools/session_resume_planner.py --pace", brief)
        self.assertIn("rc=2", brief, "缺少『rc=2 紅字只代表扇出暫停』的誤讀澄清句")
        self.assertIn("Read／Write／Edit／Bash／git", brief)

    def _touch(self) -> Path:
        import shutil
        import tempfile
        path = Path(tempfile.mkdtemp(prefix="session-brief-")) / "t.jsonl"
        path.write_text("{}\n", encoding="utf-8")
        self.addCleanup(shutil.rmtree, path.parent, True)
        return path


if __name__ == "__main__":
    unittest.main()
