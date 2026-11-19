"""`wastecensus/sections_keep.py`／`keep_load.py` 的驗收測試（R216 WP-G；TCS-SessionSwitch-CostModel
AT-SS-50～52、E2E-SS-01／02 的快照形態）。

守的是「換 session 成本模型有沒有被量到」：每個指標的邊界（為什麼這樣算）、保溫成本必須入帳、
痕跡事件名與 sessionctl 兩邊相等、母體快照重放決定性、入口不污染工作樹。
縫＝造出來的小型母體與逐字稿（隔離 tmp 目錄），不讀真實 ~/.claude、~/.autosdd；時間一律 epoch 秒。
真實逐字稿的零 token 實跑（E2E-SS-01／02 本機形態）由 realverify 家族
`sessionctl_switchcensus` 負責。
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "tools"))
sys.path.insert(0, str(_REPO / "tools" / "lib"))

from lib.sessionctl import costmodel, keepwarm, longwait  # noqa: E402
from lib.wastecensus import reader  # noqa: E402
from lib.wastecensus import sections_keep as sk  # noqa: E402
from lib.wastecensus.annotate import units  # noqa: E402

_T0 = 1_800_000_000.0
_PROBE = _REPO / "tools" / "probe" / "waste_census.py"
_MIN = 60.0


def _turn(at_min, *, cc=0, cr=0, inp=1, out=5, cause="human", tools=(), cc1=None):
    """一個回合（reader 的 Turn 切片）。`cc1` 缺省＝cc 全為 1h 層（主控）。"""
    return {"ts_first": _T0 + at_min * _MIN, "ts_last": _T0 + at_min * _MIN + 5, "inp": inp,
            "cc": cc, "cr": cr, "out": out, "cc5": 0, "cc1": cc if cc1 is None else cc1,
            "cause": cause, "tools": list(tools)}


def _main(sid, turns, *, compactions=(), kw_calls=(), handoff_start=False):
    return {"sid": sid, "handoff_start": handoff_start, "turns": list(turns),
            "compactions": list(compactions), "kw_calls": list(kw_calls)}


def _pop(mains=(), subs=()):
    return {"main": list(mains), "sub": list(subs)}


class IdleRewriteBoundaryTest(unittest.TestCase):
    def _idle_session(self, gap_min, cause="human", cr_after=0):
        """前一回合上下文 30 萬；`gap_min` 分後回來，cache_read 低＝整份重寫。"""
        return _main("aaaaaaaa", [_turn(0, cr=300_000),
                                  _turn(gap_min, cc=300_000, cr=cr_after, cause=cause)])

    def test_55_minutes_is_the_idle_boundary(self) -> None:
        """WHY：1h TTL 前約 5 分鐘是閒置自動壓縮的觀測點；55 分以下回來快取仍熱，不算閒置重寫。"""
        # 間隔自上一回合「最後一筆記錄」起算（5 秒）：54.8 分起點 → 54.7 分；55.2 分 → 55.1 分
        self.assertEqual(sk.m_k1([self._idle_session(54.8)])["count"], 0)
        self.assertEqual(sk.m_k1([self._idle_session(55.2)])["count"], 1)

    def test_a_warm_cache_return_is_not_a_rewrite(self) -> None:
        """反向變體：回來時 cache_read 還在（沒有整份重寫）⇒ 不計入 M-K1。"""
        warm = _main("aaaaaaaa", [_turn(0, cr=300_000), _turn(90, cc=1_000, cr=299_000)])
        self.assertEqual(sk.m_k1([warm])["count"], 0)

    def test_only_keepable_causes_count_and_quota_resume_goes_to_the_f4_replay(self) -> None:
        """WHY：額度續跑／壓縮後／阻塞於工具的閒置不是保溫能救的；
        M-K1 只收人／通知／交卷／其他 user。"""
        for cause in ("quota_resume", "compaction", "tool_result"):
            self.assertEqual(sk.m_k1([self._idle_session(90, cause)])["count"], 0, cause)
        for cause in ("human", "task_notification", "peer_handback", "other_user"):
            self.assertEqual(sk.m_k1([self._idle_session(90, cause)])["count"], 1, cause)
        got = sk.m_k1([self._idle_session(90)])
        self.assertEqual((got["tokens"], got["units"]), (300_000, 300_000 * costmodel.W_CC1))


class IdleCompactionTest(unittest.TestCase):
    def test_only_auto_compaction_after_50_to_60_idle_minutes_counts(self) -> None:
        """AT-SS-50：閒置 56 分後 auto 壓縮＝1；閒置 3 分（流程內）、手動、量不到閒置、窗外都不計。
        WHY：M-K2 量的是「人離開一小時，harness 把上下文砍到剩 2%」，不是一般壓縮。"""
        comps = [{"trigger": "auto", "idle_min": 56.0, "pre": 400_000, "ts": 1},
                 {"trigger": "auto", "idle_min": 3.0, "pre": 880_000, "ts": 2},
                 {"trigger": "manual", "idle_min": 56.0, "pre": 1, "ts": 3},
                 {"trigger": "auto", "idle_min": None, "pre": 1, "ts": 4},
                 {"trigger": "auto", "idle_min": 49.9, "pre": 1, "ts": 5},
                 {"trigger": "auto", "idle_min": 60.0, "pre": 300_000, "ts": 6}]
        got = sk.m_k2([_main("a", [_turn(0), _turn(1)], compactions=comps)])
        # auto_total＝量得到閒置的 auto 壓縮
        self.assertEqual((got["count"], got["auto_total"]), (2, 4))
        self.assertEqual(got["pre_tokens"], [300_000, 400_000])


class KeepWarmCostIsBookedTest(unittest.TestCase):
    def _session(self, n_wakes):
        """`n_wakes` 條 keepwarm 叫醒鏈：每條＝叫醒回合＋重掛的 tool_result 回合；
        中間夾無關回合。"""
        turns, calls, minute = [_turn(0, cr=200_000, cause="human")], [], 1
        for _ in range(n_wakes):
            calls.append({"ts": _T0 + (minute - 1) * _MIN, "kind": "keepwarm", "bg": True,
                          "notif_ts": _T0 + minute * _MIN})
            turns += [_turn(minute, cr=200_000, cause="task_notification"),
                      _turn(minute + 0.1, cr=200_000, cause="tool_result"),
                      _turn(minute + 1, cr=200_000, cause="human")]  # 無關回合：不得入帳
            minute += 50
        return _main("kw", turns, kw_calls=calls), turns

    def test_three_wake_chains_book_exactly_their_six_turns(self) -> None:
        """AT-SS-51：三條叫醒鏈 ⇒ M-K5 單位＝六個回合的加權單位。WHY：保溫成本必須入帳，
        不得用「快取命中」掩蓋保溫花掉的錢；夾在鏈之間的一般回合不能被誤算進去（否則比值虛高）。"""
        main, turns = self._session(3)
        want = sum(units(t) for i, t in enumerate(turns) if (i - 1) % 3 in (0, 1) and i > 0)
        got = sk.m_k5([main], [], k1_units=want * 4)
        self.assertEqual(got["calls"], 3)
        self.assertAlmostEqual(got["units"], want)
        self.assertEqual(got["ratio_vs_k1"], 0.25)

    def test_a_background_call_without_a_wake_record_books_nothing(self) -> None:
        """反向變體：還在跑／被中止、沒有叫醒記錄的 keepwarm 不入帳（它的發出回合屬前一條鏈）。"""
        main, _ = self._session(1)
        main["kw_calls"][0]["notif_ts"] = None
        self.assertEqual(sk.m_k5([main], [])["units"], 0)

    def test_foreground_waitfor_books_the_issuing_turn_and_the_result_turn(self) -> None:
        """子代理 waitfor 是前景呼叫：發出指令的回合與讀結果的下一回合各付一次讀價。"""
        turns = [_turn(0, cr=100_000), _turn(1, cr=100_000, cause="tool_result"),
                 _turn(2, cr=100_000, cause="tool_result")]
        sub = {"sid": "s", "turns": turns,
               "kw_calls": [{"ts": turns[0]["ts_first"] + 1, "kind": "waitfor", "bg": False,
                             "notif_ts": None}]}
        self.assertAlmostEqual(sk.m_k5([], [sub])["units"], units(turns[0]) + units(turns[1]))


class SubagentBucketsTest(unittest.TestCase):
    def _sub(self, prev_tools, cause="tool_result", cc=50_000, cr=0):
        turns = [_turn(0, cr=60_000, tools=prev_tools), _turn(10, cc=cc, cr=cr, cause=cause)]
        return {"sid": "s", "turns": turns, "kw_calls": []}

    def test_handback_then_resume_is_m_k4_and_midrun_wait_is_m_k3(self) -> None:
        """WHY：同樣是冷快取重寫，成因不同、補法不同——交卷後被續棒走冷續棒閘（M-K4），
        執行中長等待走分段等待（M-K3）；兩桶不得互相混。"""
        self.assertEqual((sk.m_k4([self._sub(["SubagentHandback"])])["count"],
                          sk.m_k3([self._sub(["SubagentHandback"])])["count"]), (1, 0))
        self.assertEqual((sk.m_k4([self._sub(["PowerShell"])])["count"],
                          sk.m_k3([self._sub(["PowerShell"])])["count"]), (0, 1))
        self.assertEqual(sk.m_k4([self._sub(["PowerShell"], cause="other_user")])["count"], 1)

    def test_compaction_and_warm_returns_are_not_counted(self) -> None:
        self.assertEqual(sk.m_k3([self._sub(["PowerShell"], cause="compaction")])["count"], 0)
        self.assertEqual(sk.m_k3([self._sub(["PowerShell"], cc=1_000, cr=59_000)])["count"], 0)


class SwitchCostPaidTest(unittest.TestCase):
    def test_m_k6_pairs_each_spawn_with_the_new_sessions_first_15_turns(self) -> None:
        """WHY：換手的真實代價是新 session 開場 15 回合的加權單位（F 實付）；找不到逐字稿的 spawn
        只計次數、不拿 0 當 F。"""
        new = _main("bbbb", [_turn(i, cc=10_000, cr=50_000) for i in range(20)])
        traces = [{"event": sk.EV_SESSION_SPAWNED, "ok": True, "new_transcripts": ["bbbb.jsonl"]},
                  {"event": sk.EV_SESSION_SPAWNED, "ok": True, "new_transcripts": ["gone.jsonl"]},
                  {"event": sk.EV_SESSION_SPAWNED, "ok": False, "new_transcripts": ["bbbb.jsonl"]}]
        got = sk.m_k6([new], traces)
        self.assertEqual((got["spawns"], got["f_paid_n"]), (2, 1))
        self.assertAlmostEqual(got["f_paid"]["median"], sum(units(t) for t in new["turns"][:15]))


class ReplayFormulaTest(unittest.TestCase):
    def test_n_star_matches_the_design_table(self) -> None:
        """設計 §3.3 F1：c=40 萬 ⇒ 9、15 萬 ⇒ 8、3 萬 ⇒ 5。W_CC1 誤用 1.25 的突變必紅。"""
        self.assertEqual((sk.n_star(400_000), sk.n_star(150_000), sk.n_star(30_000)), (9, 8, 5))

    def test_p3_fresh_decision_flips_exactly_at_the_f4_threshold(self) -> None:
        """與 `costmodel.fresh_is_cheaper` 同一條邊界：W_CC1·c > F(1+q)，相等不換新。"""
        f = 480_000.0
        grid = ((480_000, 1.0, 0), (480_001, 1.0, 1), (240_000, 0.0, 0), (240_001, 0.0, 1))
        for ctx_, q, want in grid:
            qr = _main("q", [_turn(0, cr=ctx_, inp=0), _turn(120, cc=ctx_, cause="quota_resume")])
            fresh = sk.replay_p3([qr], f, qs=(q,))[0]["fresh"]
            self.assertEqual(fresh, want, (ctx_, q))
            self.assertEqual(costmodel.fresh_is_cheaper(ctx_, cold=True, env={
                costmodel.FRESH_COST_KEY: "480000", costmodel.VALUE_Q_KEY: str(q)}), bool(want))

    def test_p1_keepwarm_saves_when_the_gap_fits_inside_n_star_pings(self) -> None:
        """WHY：ski-rental 上限內回來，保溫總成本必低於整份重寫；回來得太晚（超過 n* 次）
        才付重寫——不得出現「保溫比放冷還貴卻硬保」。"""
        quick = _main("k", [_turn(0, cr=300_000), _turn(100, cc=300_000, cause="human")])
        got = sk.replay_p1([quick], 45.0)
        self.assertEqual((got["keepable"], got["rewrites"], got["still_expired"]), (1, 1, 0))
        self.assertLess(got["cost"], got["base"])
        late = _main("k", [_turn(0, cr=300_000), _turn(60 * 100, cc=300_000, cause="human")])
        self.assertEqual(sk.replay_p1([late], 45.0)["still_expired"], 1)

    def test_s2_segmented_wait_replaces_the_rewrite_with_polls(self) -> None:
        """S2：等待 9 分、每 4 分回來一次 ⇒ 2 段；成本＝2×(0.1c＋1500) 遠低於重寫 1.25c。"""
        turns = [_turn(0, cr=100_000, inp=0, tools=["PowerShell"]),
                 _turn(9, cc=100_000, cause="tool_result")]
        got = sk.replay_subs([{"sid": "s", "turns": turns, "kw_calls": []}])
        self.assertEqual((got["s2_events"], got["s2_polls"], got["s2_still_expired"]), (1, 2, 0))
        self.assertAlmostEqual(got["s2_cost"], 2 * (0.1 * 100_000 + 1500))
        self.assertAlmostEqual(got["s2_base"], 1.25 * 100_000)

    def test_p4b_only_uses_sessions_that_started_before_the_cut(self) -> None:
        """WHY：11-14 後的 session 已被舊 R1 截斷（倖存者偏差），不得進軟線掃描。"""
        import time
        cut = time.mktime(time.strptime(sk.P4B_CUT, "%Y-%m-%d"))
        def sess(start):
            turns = [_turn(0, cr=500_000), _turn(1, cr=500_000), _turn(2, cr=500_000)]
            for t in turns:
                t["ts_first"] += start - _T0
                t["ts_last"] += start - _T0
            return _main("p", turns)
        old, new = sess(cut - 86_400), sess(cut + 86_400)
        self.assertEqual(sk.replay_p4b([old, new], 480_000, 150_000, (450_000,))[0]["crossed"], 1)


class ParityWithSessionctlTest(unittest.TestCase):
    def test_trace_event_names_equal_sessionctl_constants(self) -> None:
        """AT-SS-52 / REQ-SS-21：wastecensus 不 import 守衛碼，事件名字面相等由本測試釘住。"""
        self.assertEqual(sk.EV_KEEPWARM_VERDICT, keepwarm.EV_VERDICT)
        self.assertEqual(sk.EV_KEEPWARM_STOP_BLOCK, keepwarm.EV_STOP_BLOCK)
        self.assertEqual(sk.EV_WATCH_QUOTA_LATCHED, keepwarm.EV_QUOTA_LATCHED)
        self.assertEqual(sk.EV_LONGWAIT_BLOCK, longwait.EV_BLOCK)

    def test_keepwarm_command_marks_and_weights_equal_sessionctl(self) -> None:
        self.assertIn((keepwarm.CMD_MARK, "keepwarm"), reader.KW_MARKS)
        self.assertEqual((reader.W_CR, reader.W_CC1, reader.W_CC5),
                         (costmodel.W_CR, costmodel.W_CC1, costmodel.W_CC5))


def _rec(kind, at_min, **extra):
    stamp = datetime(2027, 1, 15, 8, 0, 0, tzinfo=UTC) + timedelta(minutes=at_min)
    return {"type": kind, "timestamp": stamp.isoformat().replace("+00:00", "Z"), **extra}


def _assistant(ts, mid, command=None, *, bg=False, tid=None, cc=1, cr=100_000):
    content = [] if command is None else [{
        "type": "tool_use", "id": tid, "name": "PowerShell",
        "input": {"command": command, "run_in_background": bg}}]
    usage = {"input_tokens": 1, "cache_creation_input_tokens": cc,
             "cache_read_input_tokens": cr, "output_tokens": 5,
             "cache_creation": {"ephemeral_1h_input_tokens": cc}}
    return _rec("assistant", ts, message={"id": mid, "model": "claude-x", "content": content,
                                           "usage": usage})


class ReaderFindsKeepwarmCallsTest(unittest.TestCase):
    def test_kw_calls_carry_kind_background_flag_and_wake_time(self) -> None:
        """WHY：M-K5 要把保溫回合從一般回合分出來，靠的就是 reader 認得 keepwarm／waitfor
        指令並配對叫醒通知；其他 PowerShell 指令不得被當成保溫。"""
        kw = "python tools/sessionctl.py keepwarm --sid x"
        wf = "python tools/sessionctl.py waitfor --done f.done"
        recs = [_assistant(0, "m0", kw, bg=True, tid="t1"),
                _assistant(10, "m1", wf, tid="t2"),
                _assistant(20, "m2", "git status", tid="t3"),
                _rec("queue-operation", 30, operation="enqueue",
                     content="<task-notification><tool-use-id>t1</tool-use-id>"
                             "<status>completed</status></task-notification>")]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.jsonl"
            path.write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")
            calls = reader.read_thread(path, "s", "main")["kw_calls"]
        self.assertEqual([(c["kind"], c["bg"]) for c in calls],
                         [("keepwarm", True), ("waitfor", False)])
        self.assertIsNotNone(calls[0]["notif_ts"])
        self.assertIsNone(calls[1]["notif_ts"])


class SnapshotAndEntryPointTest(unittest.TestCase):
    def _transcripts(self, base: Path) -> None:
        for sid, gap in (("11111111-aaaa", 90), ("22222222-bbbb", 40)):
            recs = [_assistant(0, "a0", cr=300_000, cc=1),
                    _rec("user", 5, origin={"kind": "human"}, message={"content": "hi"}),
                    _assistant(gap, "a1", cc=300_000, cr=0)]
            (base / f"{sid}.jsonl").write_text("\n".join(json.dumps(r) for r in recs) + "\n",
                                               encoding="utf-8")

    def _probe(self, *args):
        argv = [sys.executable, str(_PROBE), *args]
        proc = subprocess.run(argv, capture_output=True,  # noqa: S603
                              encoding="utf-8", errors="replace", timeout=120)
        return proc.returncode, proc.stdout, proc.stderr

    def test_snapshot_replay_equals_direct_run_and_is_deterministic(self) -> None:
        """E2E-SS-01（CI 形態）：同一份快照重放兩次逐字相同，且與直接讀逐字稿的結果逐字相同。
        WHY：CI 沒有真實逐字稿；判準若只能在作者機器上重現就不是判準。快照不含對話內容。"""
        flags = ["--switch-metrics", "--replay-switch", "--calibrate-switch",
                 "--resume-cost-file", "NUL-nonexistent", "--trace-file", "NUL-nonexistent"]
        with tempfile.TemporaryDirectory() as tmp:
            base, snap = Path(tmp) / "proj", Path(tmp) / "pop.json"
            base.mkdir()
            self._transcripts(base)
            rc0, direct, err0 = self._probe("--base", str(base), "--since-days", "3650",
                                            "--dump-population", str(snap), *flags)
            self.assertEqual(rc0, 0, err0)
            direct = direct.replace(f"母體快照已寫：{snap}\n", "")
            rc1, one, _ = self._probe("--population", str(snap), *flags)
            rc2, two, _ = self._probe("--population", str(snap), *flags)
            self.assertEqual((rc1, rc2), (0, 0))
            self.assertEqual(one, two)
            self.assertEqual(one.replace("近 14.0 天", "近 3650.0 天"), direct)
            self.assertIn("M-K1 主控可保溫閒置後重寫：1 件／300,000 tok", one)
            body = json.loads(snap.read_text(encoding="utf-8"))
            # 沒有對話內容：每個 session 只有結構欄位，回合只有 usage／時間戳／起因／工具名
            self.assertEqual(sorted(body["main"][0]),
                             ["compactions", "handoff_start", "kw_calls", "sid", "turns"])
            self.assertEqual(sorted(body["main"][0]["turns"][0]),
                             sorted(("ts_first", "ts_last", "inp", "cc", "cr", "out", "cc5",
                                     "cc1", "cause", "tools")))

    def test_the_handoff_start_flag_replaces_the_prompt_text(self) -> None:
        """WHY：F（接手成本）要認「交棒開場的 session」，但快照不能帶提示原文。"""
        self.assertTrue(sk.is_handoff_start("按交接包繼續：讀 x"))
        self.assertTrue(sk.is_handoff_start("Resume via HANDOFF file"))
        self.assertFalse(sk.is_handoff_start("幫我改一個 bug"))
        self.assertFalse(sk.is_handoff_start(""))
        turns = [_turn(i, cc=10_000, cr=50_000) for i in range(20)]
        self.assertEqual(len(sk.f_rows([_main("a", turns, handoff_start=True)])), 1)
        self.assertEqual(sk.f_rows([_main("a", turns)]), [])

    def test_missing_transcript_dir_without_snapshot_fails_loud(self) -> None:
        rc, _out, err = self._probe("--base", str(Path(tempfile.gettempdir()) / "no-such-dir-r216"),
                                    "--switch-metrics")
        self.assertEqual(rc, 1)
        self.assertIn("逐字稿目錄不存在", err)

    def test_stale_snapshot_schema_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snap = Path(tmp) / "pop.json"
            stale = {"schema": "old/0", "main": [], "sub": []}
            snap.write_text(json.dumps(stale), encoding="utf-8")
            rc, _out, err = self._probe("--population", str(snap), "--switch-metrics")
        self.assertNotEqual(rc, 0)
        self.assertIn("schema", err)


class ResumeCostCalibrationTest(unittest.TestCase):
    def test_only_measured_cold_windows_validate_the_full_rewrite_assumption(self) -> None:
        """F4 的前提是「過期後續跑≈整份重寫」。relay_seq≥1 的接力窗快取仍熱（寫入占比低），
        不能拿來驗證，也不能被算進冷窗分母。"""
        def row(seq, cc, cr, measured=True):
            return {"measured": measured, "relay_seq": seq, "input_tokens": 2 if measured else None,
                    "cache_creation_input_tokens": cc, "cache_read_input_tokens": cr}
        rows = [row(0, 90, 10), row(1, 10, 90), row(0, None, None, measured=False)]
        got = sk.resume_cost_summary(rows)
        self.assertEqual((got["n"], got["cold_n"], got["write_share_ge_80pct_cold"]), (2, 1, 1))


if __name__ == "__main__":
    unittest.main()
