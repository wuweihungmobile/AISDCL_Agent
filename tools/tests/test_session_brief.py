#!/usr/bin/env python3
"""`tools/lib/session_brief.py` 的回歸鎖（R158／P6：四象限——額度〈有／無快取〉× round-label-ok
context〈有／無 usage〉，量不到就照實說；ctx5 輪另補 G1（statusLine 安裝狀態三格＋
feed reason 兩格）與 G2（stale-cache 追加文案兩格）。接線面另見
`test_context_budget_guard.py::HandbackSessionStartAnnounceTest`。"""
from __future__ import annotations

import contextlib
import io
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


def _touch(case: unittest.TestCase) -> Path:
    """建一份最小逐字稿檔（兩測試類別共用，DEF-200-344 收斂複本）。"""
    import shutil
    import tempfile
    path = Path(tempfile.mkdtemp(prefix="session-brief-")) / "t.jsonl"
    path.write_text("{}\n", encoding="utf-8")
    case.addCleanup(shutil.rmtree, path.parent, True)
    return path


def _cache_miss_gate():
    """`quota_gate` 替身：`read_quota` 恆丟 `OSError`（模擬無快取，3 個測試共用）。"""
    return _fake_quota_gate(read_quota=lambda now, path=None: (_ for _ in ()).throw(
        OSError("合成：無快取")))


class QuotaLineTest(unittest.TestCase):
    """象限：額度〈有快取〉／〈無快取〉。零網路——`quota_gate` 全由呼叫端注入。"""

    def test_with_cache_describes_the_decision(self) -> None:
        state = _cache_hit_state()
        gate = _fake_quota_gate(read_quota=lambda now, path=None: state)
        got = sb.quota_line(gate, _NOW)
        self.assertIn("kind=session", got, "有快取時應印出逐軸判讀，而不是回退訊息")
        self.assertNotIn("額度快取不可用", got)

    def test_without_cache_falls_back_to_a_human_sentence(self) -> None:
        got = sb.quota_line(_cache_miss_gate(), _NOW)
        self.assertIn("額度快取不可用", got)
        self.assertIn("--pace", got, "回退訊息要帶得出查證指令")

    def test_load_policy_failure_also_falls_back(self) -> None:
        """不只 `read_quota` 會壞；`load_policy` 出例外也要收斂成同一句人話。"""
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

    def test_stale_cache_appends_the_fixed_caveat(self) -> None:
        """G2：`describe()` 文字含 `stale-cache` 時（快取過期、`decide()` 退化到
        `degraded_cap`）追加固定文案——講清楚這是退化政策值、PreToolUse 會自動補量，
        不是硬限制（ctx5 輪 FACTS：陳舊 30280s > TTL 180s 那個實例）。"""
        stale = quota_policy.QuotaState(
            (), "", "stale-cache", "stale-cache（測試：30280s > TTL 180s）")
        gate = _fake_quota_gate(read_quota=lambda now, path=None: stale)
        got = sb.quota_line(gate, _NOW)
        self.assertIn("stale-cache", got, "stale-cache 判準本身沒觸發")
        self.assertIn("陳舊快取的退化政策值，不是量測值", got)
        self.assertIn("PreToolUse 會自動補量一次、零 token", got)
        self.assertIn("python tools/session_resume_planner.py --pace", got)

    def test_non_stale_cache_does_not_append_the_caveat(self) -> None:
        """反向格：正常（非陳舊）快取不該被附加這句退化政策值警語——只在 `stale-cache`
        真的出現時才追加，不是每次都貼。"""
        gate = _fake_quota_gate(read_quota=lambda now, path=None: _cache_hit_state())
        got = sb.quota_line(gate, _NOW)
        self.assertNotIn("陳舊快取的退化政策值", got, "非陳舊快取卻被貼了 stale-cache 警語")


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
        tmp = _touch(self)
        got = sb.context_line(
            tmp, scan_transcript=lambda p: (None, 0, None),
            resolve_window=lambda *a, **k: (200_000, "x"),
            window_evidence=lambda *a, **k: {}, read_context_feed=lambda *a: {})
        self.assertEqual(got, sb._NO_MEASURE, "量不到 usage 不該假裝量到了")

    def test_scan_with_usage_reports_used_and_window(self) -> None:
        tmp = _touch(self)
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
        tmp = _touch(self)

        def _boom(_p):
            raise ValueError("合成：掃描壞掉")

        got = sb.context_line(
            tmp, scan_transcript=_boom, resolve_window=None,
            window_evidence=None, read_context_feed=None)
        self.assertEqual(got, sb._NO_MEASURE)

    def test_non_positive_window_reports_no_measurement(self) -> None:
        """`window<=0` 是 `tier_of()` 定義過的「不對零做除法」的同型地雷，本檔獨立防一次。"""
        tmp = _touch(self)
        got = sb.context_line(
            tmp, scan_transcript=lambda p: (100, 100, "m"),
            resolve_window=lambda *a, **k: (0, "壞掉的分母"),
            window_evidence=lambda *a, **k: {}, read_context_feed=lambda *a: {})
        self.assertEqual(got, sb._NO_MEASURE)

    def test_feed_reason_is_surfaced_not_silently_dropped(self) -> None:
        """G1：`feed["reason"]` 非空時（例如 statusLine 未設定或本 session 尚無
        assistant 訊息）附一句既有措辭，不再靜默丟棄——比照
        `harness_feed.check_lines()` 的用字，不是本檔自創的第二種措辭。"""
        tmp = _touch(self)
        reason = "無 feed（statusLine 未設定或本 session 尚無 assistant 訊息）"
        got = sb.context_line(
            tmp,
            scan_transcript=lambda p: (100, 100, "claude-test-double-3"),
            resolve_window=lambda *a, **k: (200_000, "指定值（測試）"),
            window_evidence=lambda *a, **k: {},
            read_context_feed=lambda *a: {"reason": reason})
        self.assertIn("used=100", got, "附加 reason 句子時把原本的 used/window 弄丟了")
        self.assertIn(f"harness feed 未採用：{reason}", got,
                      'feed["reason"] 非空卻被靜默丟棄')

    def test_feed_reason_none_appends_nothing(self) -> None:
        """反向格：`reason` 是 `None`（例如 feed 被成功採用）不該附加任何贅句。"""
        tmp = _touch(self)
        got = sb.context_line(
            tmp,
            scan_transcript=lambda p: (100, 100, "claude-test-double-3"),
            resolve_window=lambda *a, **k: (200_000, "指定值（測試）"),
            window_evidence=lambda *a, **k: {},
            read_context_feed=lambda *a: {"reason": None, "used": 100})
        self.assertNotIn("harness feed 未採用", got, "reason 為 None 卻仍附加了贅句")


class StatuslineLineTest(unittest.TestCase):
    """G1 三格：已安裝／未安裝／查不到（注入會拋例外的 callable）。零 I/O——
    `check_status` 全由測試注入替身，不觸及真正的 `install_statusline.status()`。"""

    def test_installed_reports_installed(self) -> None:
        got = sb.statusline_line(lambda: {"installed": True})
        self.assertEqual(got, "statusLine：已安裝")

    def test_not_installed_reports_install_hint(self) -> None:
        got = sb.statusline_line(lambda: {"installed": False})
        self.assertIn("statusLine：未安裝", got)
        self.assertIn("python tools/install_statusline.py --dry-run", got,
                      "未安裝時沒帶出安裝指令")

    def test_check_status_exception_fails_open_to_unknown(self) -> None:
        """任何例外（包含注入的替身直接拋出）都要收斂成「查不到」，不得讓
        SessionStart 崩掉；原因要帶進訊息（不是只印一句籠統的失敗）。"""
        def _boom() -> dict:
            raise OSError("合成：查不到")

        got = sb.statusline_line(_boom)
        self.assertIn("statusLine：查不到", got)
        self.assertIn("合成：查不到", got, "例外原因沒有帶進訊息")

    def test_default_check_status_is_the_real_installer(self) -> None:
        """接線面鑑別：不注入時的預設值就是 `_default_check_statusline`（產線走真的
        `install_statusline.status()`），本測試只驗接線、不呼叫它、不碰檔案系統。"""
        import inspect
        default = inspect.signature(sb.statusline_line).parameters["check_status"].default
        self.assertIs(default, sb._default_check_statusline)


class SessionstartBriefTest(unittest.TestCase):
    """整合：四象限全組合都要含兩條查證指令 ＋ rc=2 澄清句，且不崩潰、不消失。"""

    def _payload(self, transcript: Path | None) -> dict:
        return {"transcript_path": str(transcript) if transcript else None}

    #: 這幾支既有整合測試不關心 statusLine 判準本身（`StatuslineLineTest` 已單獨鎖
    #: 三格），一律注入固定替身、避免真的碰 `~/.claude/settings.json`（零 I/O）。
    _FAKE_INSTALLED = staticmethod(lambda: {"installed": True})

    def test_cache_hit_and_usage_present(self) -> None:
        tmp = _touch(self)
        gate = _fake_quota_gate(read_quota=lambda now, path=None: _cache_hit_state())
        got = sb.sessionstart_brief(
            self._payload(tmp), gate,
            scan_transcript=lambda p: (999, 999, "claude-test-double-3"),
            resolve_window=lambda *a, **k: (200_000, "指定值（測試）"),
            window_evidence=lambda *a, **k: {}, read_context_feed=lambda *a: {}, now=_NOW,
            check_statusline=self._FAKE_INSTALLED)
        self.assertIn("[SDD-CTX-GUARD]", got)
        self.assertIn("used=999", got)
        self.assertIn("kind=session", got)
        self._assert_common(got)

    def test_cache_hit_and_usage_absent(self) -> None:
        gate = _fake_quota_gate(read_quota=lambda now, path=None: _cache_hit_state())
        got = sb.sessionstart_brief(
            self._payload(None), gate,
            scan_transcript=None, resolve_window=None,
            window_evidence=None, read_context_feed=None, now=_NOW,
            check_statusline=self._FAKE_INSTALLED)
        self.assertIn(sb._NO_MEASURE, got)
        self.assertIn("kind=session", got)
        self._assert_common(got)

    def test_cache_miss_and_usage_present(self) -> None:
        got = sb.sessionstart_brief(
            self._payload(_touch(self)), _cache_miss_gate(),
            scan_transcript=lambda p: (1, 1, "claude-test-double-3"),
            resolve_window=lambda *a, **k: (200_000, "指定值（測試）"),
            window_evidence=lambda *a, **k: {}, read_context_feed=lambda *a: {}, now=_NOW,
            check_statusline=self._FAKE_INSTALLED)
        self.assertIn("used=1", got)
        self.assertIn(sb._QUOTA_UNAVAILABLE, got)
        self._assert_common(got)

    def test_cache_miss_and_usage_absent(self) -> None:
        """四象限最壞的一格：兩邊都量不到。簡報仍要送出，兩句 fail-open 訊息都在。"""
        got = sb.sessionstart_brief(
            self._payload(None), _cache_miss_gate(),
            scan_transcript=None, resolve_window=None,
            window_evidence=None, read_context_feed=None, now=_NOW,
            check_statusline=self._FAKE_INSTALLED)
        self.assertIn(sb._NO_MEASURE, got)
        self.assertIn(sb._QUOTA_UNAVAILABLE, got)
        self._assert_common(got)

    def test_a_dependencys_stderr_noise_does_not_leak_to_the_caller(self) -> None:
        """DEF-200-344：注入函式的 fail-open 噪音（如 windows-compat-ci #251 撞到的
        `known_model_windows` 查表警語）不得外洩到呼叫端 stderr。"""
        def _noisy_resolve_window(*_a, **_k):
            sys.stderr.write("known_model_windows fail-open: synthetic noise\n")
            return (200_000, "指定值（測試）")
        outer = io.StringIO()
        with contextlib.redirect_stderr(outer):
            got = sb.sessionstart_brief(
                self._payload(_touch(self)), _fake_quota_gate(
                    read_quota=lambda now, path=None: _cache_hit_state()),
                scan_transcript=lambda p: (1, 1, "claude-test-double-3"),
                resolve_window=_noisy_resolve_window,
                window_evidence=lambda *a, **k: {}, read_context_feed=lambda *a: {}, now=_NOW,
                check_statusline=self._FAKE_INSTALLED)
        self.assertEqual(outer.getvalue(), "", "注入函式的 stderr 噪音外洩到呼叫端")
        self.assertIn("--check", got)

    def test_check_statusline_wiring_reaches_the_final_brief(self) -> None:
        """G1 接線面：`check_statusline` 真的被組進最終簡報字串（未安裝格），不是
        傳進去卻被忽略。"""
        got = sb.sessionstart_brief(
            self._payload(None), _cache_miss_gate(),
            scan_transcript=None, resolve_window=None,
            window_evidence=None, read_context_feed=None, now=_NOW,
            check_statusline=lambda: {"installed": False})
        self.assertIn("statusLine：未安裝", got)
        self.assertIn("python tools/install_statusline.py --dry-run", got)

    def _assert_common(self, brief: str) -> None:
        self.assertIn("python tools/session_resume_planner.py --check", brief)
        self.assertIn("python tools/session_resume_planner.py --pace", brief)
        self.assertIn("rc=2", brief, "缺少『rc=2 紅字只代表扇出暫停』的誤讀澄清句")
        self.assertIn("Read／Write／Edit／Bash／git", brief)
        self.assertIn("statusLine：已安裝", brief, "G1 的 statusLine 那一句沒有進最終簡報")


if __name__ == "__main__":
    unittest.main()
