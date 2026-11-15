"""tools/lib/sessionctl/cachestate.py 與 roster.resume_gate：續棒看目標代理的快取冷熱。

AT-TW-01～08（冷熱判準）、AT-TW-09～18（續棒閘）。縫：`now` 注入、tmp 圍籬造逐字稿、
`AUTOSDD_TRACE_DIR` 指 tmp；不讀真實 `~/.claude`、不起排程、不起 claude。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

from lib.sessionctl import cachestate, roster  # noqa: E402

SID = "d4ed2654-9181-4df1-a6e6-2d712956e23b"
NOW = datetime(2026, 11, 14, 12, 0, 0, tzinfo=UTC)
LIMIT = 150_000


def _rec(ctx: int, minutes_ago: float, *, h1: int = 0, kind: str = "assistant",
         legacy: bool = False, seconds_ago: float | None = None) -> str:
    """一筆逐字稿記錄；`legacy`＝usage 無 `cache_creation` 欄；`kind=user` 模擬 tool_result。"""
    ago = timedelta(seconds=seconds_ago) if seconds_ago is not None else timedelta(
        minutes=minutes_ago)
    usage = {"input_tokens": 1, "cache_read_input_tokens": ctx - 1,
             "cache_creation_input_tokens": 0, "output_tokens": 7}
    if not legacy:
        usage["cache_creation"] = {"ephemeral_5m_input_tokens": 0,
                                   "ephemeral_1h_input_tokens": h1}
    body = {"id": "m1", "usage": usage} if kind == "assistant" else {"content": "tool_result"}
    return json.dumps({"type": kind, "timestamp": (NOW - ago).isoformat(), "message": body})


class _Fence(unittest.TestCase):
    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory(prefix="tw-cache-")
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name)
        self.slug = self.tmp / "slug"
        self.slug.mkdir()
        self.trace_dir = self.tmp / "traces"
        self.trace_dir.mkdir()
        patch = mock.patch.dict(os.environ, {"AUTOSDD_TRACE_DIR": str(self.trace_dir)})
        patch.start()
        self.addCleanup(patch.stop)

    def agent(self, aid: str, *lines: str) -> Path:
        folder = self.slug / SID / "subagents"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"agent-{aid}.jsonl"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def traces(self) -> list[dict]:
        target = self.trace_dir / "autosdd_session_switch.jsonl"
        if not target.exists():
            return []
        return [json.loads(x) for x in target.read_text(encoding="utf-8").splitlines()]

    def send(self, to: str = "a1", message: str = "續做", field: str = "to") -> dict:
        return {"hook_event_name": "PreToolUse", "tool_name": "SendMessage", "session_id": SID,
                "transcript_path": str(self.slug / f"{SID}.jsonl"),
                "tool_input": {field: to, "message": message}}


class CacheStateTest(_Fence):
    """tools/lib/sessionctl/cachestate.py::cache_state：冷熱判準（AT-TW-01～08）。"""

    def state(self, *lines: str) -> dict:
        return cachestate.cache_state(self.agent("a1", *lines), NOW)

    def test_at_tw_01_five_minute_agent_idle_ten_minutes_is_cold(self) -> None:
        """tools/lib/sessionctl/cachestate.py：5m 型閒置 10 分鐘 ⇒ tier 5m、cold。"""
        got = self.state(_rec(150_000, 10))
        self.assertEqual((got["tier"], got["cold"]), ("5m", True))

    def test_at_tw_02_five_minute_agent_idle_one_minute_is_warm(self) -> None:
        """tools/lib/sessionctl/cachestate.py：熱續棒不得被誤判成冷（否則逼人白重做）。"""
        self.assertIs(self.state(_rec(150_000, 1))["cold"], False)

    def test_at_tw_03_cold_line_has_a_thirty_second_margin(self) -> None:
        """tools/lib/sessionctl/cachestate.py：冷線＝300−30 秒；邊界前後各一格（299.995 秒間隔
        實證仍整份重寫，沒有邊際會放行它）。"""
        self.assertEqual(cachestate.CACHE_MARGIN_SECONDS, 30)  # 常數本身也釘死，不得調成 0
        self.assertIs(self.state(_rec(150_000, 0, seconds_ago=270))["cold"], True)
        self.assertIs(self.state(_rec(150_000, 0, seconds_ago=269))["cold"], False)

    def test_at_tw_04_one_hour_evidence_anywhere_in_the_tail_makes_it_one_hour(self) -> None:
        """tools/lib/sessionctl/cachestate.py：tier 看尾端**任一筆**——純讀回合寫入 0，只看最後一筆
        會把 1h 代理誤判成 5m。"""
        got = self.state(_rec(150_000, 30, h1=900), _rec(150_000, 10, h1=0))
        self.assertEqual((got["tier"], got["cold"]), ("1h", False))

    def test_at_tw_05_one_hour_agent_idle_sixty_one_minutes_is_cold(self) -> None:
        """tools/lib/sessionctl/cachestate.py：1h 型的冷線不得沿用 5 分。"""
        got = self.state(_rec(150_000, 61, h1=900))
        self.assertEqual((got["tier"], got["cold"]), ("1h", True))

    def test_at_tw_06_missing_cache_creation_field_falls_back_to_five_minutes(self) -> None:
        """tools/lib/sessionctl/cachestate.py：缺欄退保守的 5m（較早判冷＝較嚴）。"""
        self.assertEqual(self.state(_rec(150_000, 10, legacy=True))["tier"], "5m")

    def test_at_tw_07_tool_result_records_do_not_reset_the_cache_clock(self) -> None:
        """tools/lib/sessionctl/cachestate.py：
        idle 從最後一筆 assistant 起算，user／tool_result 不算。"""
        got = self.state(_rec(150_000, 8), _rec(0, 0.1, kind="user"))
        self.assertTrue(got["cold"])
        self.assertAlmostEqual(got["idle_s"], 480, delta=1)

    def test_at_tw_07_the_clock_runs_from_the_latest_of_many_usage_records(self) -> None:
        """AT-TW-07 tools/lib/sessionctl/cachestate.py：真實逐字稿尾端必有多筆 assistant usage，
        計時取最後一筆；取到最早一筆會把仍熱的代理判冷、誤擋熱續棒（比 AT-TW-10 更隱蔽）。"""
        warm = self.state(_rec(150_000, 20), _rec(150_000, 1))
        self.assertIs(warm["cold"], False)
        self.assertAlmostEqual(warm["idle_s"], 60, delta=1)
        cold = self.state(_rec(150_000, 1), _rec(150_000, 20))  # 檔內順序與時間先後無關
        self.assertIs(cold["cold"], False)
        late_cold = self.state(_rec(150_000, 20), _rec(150_000, 10))
        self.assertIs(late_cold["cold"], True)
        self.assertAlmostEqual(late_cold["idle_s"], 600, delta=1)

    def test_at_tw_08_unreadable_transcripts_fail_open(self) -> None:
        """tools/lib/sessionctl/cachestate.py：
        檔不存在／空／壞 JSON／無 assistant ⇒ 不冷、idle None。"""
        samples = {"缺檔": self.slug / "ghost.jsonl",
                   "空": self.agent("e"), "壞": self.agent("b", "{{壞 JSON"),
                   "無 assistant": self.agent("u", _rec(0, 20, kind="user"))}
        for label, path in samples.items():
            with self.subTest(label):
                got = cachestate.cache_state(path, NOW)
                self.assertEqual((got["cold"], got["idle_s"]), (False, None))

    def test_override_reason_needs_the_fullwidth_prefix_and_eight_chars(self) -> None:
        """tools/lib/sessionctl/cachestate.py::override_reason：
        全形冒號、去空白後 ≥ 8 字、取到行尾。"""
        ok = cachestate.override_reason("先做這個\n續棒理由： 上一棒只差一個檔未寫完 \n其他")
        self.assertEqual(ok, "上一棒只差一個檔未寫完")
        for bad in ("續棒理由：因為", "續棒理由:半形冒號也不行啊啊啊啊", "沒寫理由", None, 5):
            with self.subTest(bad=bad):
                self.assertIsNone(cachestate.override_reason(bad))


class ResumeGateTest(_Fence):
    """tools/lib/sessionctl/roster.py::resume_gate：SendMessage 成本閘看冷熱（AT-TW-09～18）。"""

    INTERACTIVE: dict = {}
    UNATTENDED = {"AUTOSDD_UNATTENDED": "1"}

    def gate(self, payload: dict, env: dict) -> tuple[int, str]:
        return roster.resume_gate(payload, env, NOW)

    def test_at_tw_09_interactive_cold_big_agent_is_blocked_with_the_next_step(self) -> None:
        """tools/lib/sessionctl/roster.py：
        互動、冷、150,000 ⇒ rc 2，訊息給確切下一步與逃生口寫法。"""
        self.agent("a1", _rec(LIMIT, 10))
        rc, text = self.gate(self.send(), self.INTERACTIVE)
        self.assertEqual(rc, 2)
        for needle in ("續棒成本閘", "改派新代理＋短任務書", "續棒理由：", "a1", "150,000",
                       "閒置 10 分鐘（快取壽命 5m）", "交卷檔／handback 路徑"):
            self.assertIn(needle, text)

    def test_at_tw_10_interactive_warm_agent_passes_silently(self) -> None:
        """tools/lib/sessionctl/roster.py：熱續棒只付讀價、比新代理便宜——放行且不出聲。"""
        self.agent("a1", _rec(LIMIT, 1))
        self.assertEqual(self.gate(self.send(), self.INTERACTIVE), (0, ""))

    def test_at_tw_11_cold_but_below_threshold_passes(self) -> None:
        """tools/lib/sessionctl/roster.py：
        冷但 149,999 ⇒ 放行（小上下文重寫成本低於新代理啟動成本）。"""
        self.agent("a1", _rec(LIMIT - 1, 10))
        self.assertEqual(self.gate(self.send(), self.INTERACTIVE), (0, ""))

    def test_at_tw_12_a_stated_reason_overrides_and_leaves_a_trace(self) -> None:
        """tools/lib/sessionctl/roster.py：
        合格 `續棒理由：` ⇒ 放行並落 resume_gate_override 痕跡。"""
        self.agent("a1", _rec(LIMIT, 10))
        send = self.send(message="續棒理由：上一棒只差一個檔未寫完")
        self.assertEqual(self.gate(send, self.INTERACTIVE), (0, ""))
        rows = [r for r in self.traces() if r["event"] == "resume_gate_override"]
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["target"], rows[0]["ctx"]), ("a1", LIMIT))
        self.assertIn("上一棒", rows[0]["reason"])

    def test_at_tw_13_a_too_short_reason_does_not_override(self) -> None:
        """tools/lib/sessionctl/roster.py：
        理由少於 8 字仍阻斷（理由必填，逃生口才不淪為整包 noqa）。"""
        self.agent("a1", _rec(LIMIT, 10))
        send = self.send(message="續棒理由：因為")
        self.assertEqual(self.gate(send, self.INTERACTIVE)[0], 2)

    def test_at_tw_13_the_reason_floor_is_exactly_eight_characters(self) -> None:
        """AT-TW-13 tools/lib/sessionctl/cachestate.py::override_reason：下界恰 8 字（strip 後
        計字）——7 字不接受、8 字接受；邊界不釘，必填門檻可被偷偷抬高或放低。"""
        eight, seven = "一二三四五六七八", "一二三四五六七"
        self.assertEqual(cachestate.OVERRIDE_MIN_CHARS, 8)
        self.assertEqual(cachestate.override_reason(f"續棒理由：  {eight}  "), eight)
        self.assertIsNone(cachestate.override_reason(f"續棒理由：  {seven}  "))
        self.agent("a1", _rec(LIMIT, 10))
        self.assertEqual(self.gate(self.send(message=f"續棒理由：{eight}"), self.INTERACTIVE),
                         (0, ""))
        self.assertEqual(self.gate(self.send(message=f"續棒理由：{seven}"),
                                   self.INTERACTIVE)[0], 2)

    def test_at_tw_14_unattended_ignores_the_override(self) -> None:
        """tools/lib/sessionctl/roster.py：無人窗口沒有人可問——合格理由也無效。"""
        self.agent("a1", _rec(LIMIT, 10))
        send = self.send(message="續棒理由：上一棒只差一個檔未寫完")
        self.assertEqual(self.gate(send, self.UNATTENDED)[0], 2)
        self.assertEqual([r for r in self.traces() if r["event"] == "resume_gate_override"], [])

    def test_at_tw_15_unattended_warm_agent_is_still_blocked(self) -> None:
        """tools/lib/sessionctl/roster.py：
        無人熱代理 450,000 照舊阻斷（不放寬既有 AT-SC-62／65）。"""
        self.agent("a1", _rec(450_000, 1))
        rc, text = self.gate(self.send(), self.UNATTENDED)
        self.assertEqual(rc, 2)
        self.assertIn("🔴 已阻斷（無人窗口）。", text)
        self.assertIn("改派新代理＋短任務書", text)

    def test_at_tw_16_recipient_is_the_fallback_target_field(self) -> None:
        """tools/lib/sessionctl/roster.py：目標欄 `to` 缺則 `recipient`（沙盒 V-S2）。"""
        self.agent("a1", _rec(LIMIT, 10))
        self.assertEqual(self.gate(self.send(field="recipient"), self.INTERACTIVE)[0], 2)

    def test_at_tw_17_a_block_leaves_a_trace_with_the_measured_fields(self) -> None:
        """tools/lib/sessionctl/roster.py：
        阻斷落 resume_gate_block（target／ctx／idle_s／tier）。"""
        self.agent("a1", _rec(LIMIT, 10))
        self.gate(self.send(), self.INTERACTIVE)
        rows = [r for r in self.traces() if r["event"] == "resume_gate_block"]
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["target"], rows[0]["ctx"], rows[0]["tier"]),
                         ("a1", LIMIT, "5m"))
        self.assertAlmostEqual(rows[0]["idle_s"], 600, delta=1)

    def test_at_tw_18_unresolvable_targets_fail_open_in_both_modes(self) -> None:
        """tools/lib/sessionctl/roster.py：
        目標不存在／壞逐字稿／to 非字串／路徑穿越 ⇒ 互動與無人皆放行。"""
        self.agent("a1", _rec(LIMIT * 3, 10))
        self.agent("bad", "{{壞 JSON")
        weird = self.send("x")
        weird["tool_input"]["to"] = 123
        cases = {"不存在": self.send("ghost"), "壞逐字稿": self.send("bad"), "to 非字串": weird,
                 "穿越": self.send("../../etc/passwd"), "萬用字元": self.send("*")}
        for env in (self.INTERACTIVE, self.UNATTENDED):
            for label, payload in cases.items():
                with self.subTest(label=label, env=sorted(env)):
                    self.assertEqual(self.gate(payload, env), (0, ""))
        self.assertEqual(self.gate({}, self.UNATTENDED), (0, ""))

    def test_the_override_is_traced_only_when_it_was_actually_needed(self) -> None:
        """tools/lib/sessionctl/roster.py：
        熱代理帶理由也不落 override（痕跡＝逃生口真實使用量）。"""
        self.agent("a1", _rec(LIMIT, 1))
        self.gate(self.send(message="續棒理由：其實不需要這句話啊"), self.INTERACTIVE)
        self.assertEqual(self.traces(), [])


if __name__ == "__main__":
    unittest.main()
