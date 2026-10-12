"""清倉模式（DEF-200-528）：增補檔 BD-1~BD-9／BD-2′／載體與接線；合成輸入、零網路、零真實落款。"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "lib"))
import quota_burndown as B  # noqa: E402
import quota_criteria as QC  # noqa: E402
import quota_gate as QG  # noqa: E402
import quota_messages as QM  # noqa: E402
import quota_meter as M  # noqa: E402
import quota_pace as W  # noqa: E402
import quota_policy as Q  # noqa: E402
import sentinel_lifecycle as SL  # noqa: E402

_FENCES: list[dict] = []


def setUpModule() -> None:  # 單模組直跑也不得碰真實 TEMP／快取／痕跡目錄
    _FENCES.append(SL.fence_enter())


def tearDownModule() -> None:
    SL.fence_exit(_FENCES.pop())


NOW = datetime(2026, 10, 12, 10, 37, tzinfo=UTC)
P, INF, A, WEEK = Q.DEFAULT_POLICY, float("inf"), Q.Axis, (NOW + timedelta(0, 459780)).isoformat()


def at(m, us=0):
    return None if m is None else (NOW + timedelta(minutes=m, microseconds=us)).isoformat()


def burn(kind="weekly_all", resets=WEEK):
    return B.Burn("0123456789", NOW.isoformat(), kind, at(7663), 7663.0, resets)


def state(*axes):
    return Q.QuotaState(tuple(axes), NOW.isoformat(), "cache")


def real():  # 掌舵者 2026-10-12 的 `--pace` 真實讀數（合成；r=5.0 時 five_hour 被攤提抬成 prepare）
    return state(A("session", 8.0, at(233)), A("weekly_all", 75.0, WEEK),
                 A("weekly_scoped", 41.0, at(7663, 218), scope_model="Fable"),
                 A("five_hour", 8.0, at(233)), A("seven_day", 75.0, WEEK), A("spend", 0.0, None))


def dec(s, b=None, ratio=5.0, **kw):
    return Q.decide(s, NOW, P, ratio, "n=67", burndown=b, **kw)


def cells(d):
    return {r.axis.kind: (r.band, r.horizon, r.cap, r.recommended) for r in d.per_axis}


def pair(s, kind, b=None, **kw):  # (無授權的格, 有授權的格)：同一軸的 (band, horizon, cap, rec)
    return cells(dec(s, None, **kw))[kind], cells(dec(s, b or burn(), **kw))[kind]


class TestRelaxation(unittest.TestCase):
    """BD-1~BD-5／BD-8／BD-9／BD-2′：逐軸放寬的方向、窮舉與順序鎖（純函式，零 I/O）。"""

    def test_naming_the_long_window_relaxes_boundedly_and_leaves_the_floors_alone(self) -> None:
        base, d = dec(real()), dec(real(), burn())
        self.assertEqual((base.cap, base.binding.kind), (1, "five_hour"), "前提：今天被攤提壓住")
        c0, c = cells(base), cells(d)
        self.assertEqual((d.cap, d.recommended_fanout), (P.cap_converge, P.cap_prepare))
        self.assertIn(d.binding.kind, ("weekly_all", "seven_day"))
        for kind in ("session", "five_hour"):  # Q-cross：攤提暫停 ⇒ band 退回 free、cap 夾在上限
            self.assertEqual((c[kind][0], c[kind][2], c0[kind][2]), (Q.BAND_FREE, P.cap_notice, 1))
        for kind in ("weekly_all", "seven_day"):  # Q-same：視野地板 ⇒ cap 2→cap_converge
            want = (Q._cap_for(Q.BAND_CONVERGE, Q.AXIS_FAR, P), P.cap_converge, P.cap_prepare)
            self.assertEqual((c0[kind][2], c[kind][2], c[kind][3]), want)
        for kind in ("weekly_scoped", "spend"):  # 底線②③：逐格不動，model-scoped 的 note 照印
            self.assertEqual(c[kind], c0[kind])
        scoped = next(r for r in d.per_axis if r.axis.kind == "weekly_scoped")
        self.assertIn(Q.NOTE_MODEL_EXCLUDED, scoped.note)
        for needle in ("清倉模式生效中", "落款 0123456789", "發令", "作用至", "效期剩",
                       "must-finish 門檻", "cap 1→", "cap 2→", "kind=spend（fallback 不納入）",
                       "kind=weekly_scoped（model-scoped 不納入）"):  # 出聲：放寬值、效期、門檻
            self.assertIn(needle, d.burndown.text)
        self.assertEqual(d.burndown.mark, "｜🔥清倉 0123456789：放寬 4 軸／未放寬 2 軸")
        self.assertIn(d.burndown.mark, QM.pace_line(d, 0, P.max_fanout))  # 標題行只帶短標記
        self.assertIn(d.burndown.text, Q.describe(d))  # hook 阻斷訊息只有 describe：必須看得到全文
        self.assertNotIn("清倉", Q.describe(d, burndown=False))  # --pace 的全文另起一行
        self.assertEqual(QC.m7_problems(Q.describe(d)), [])
        self.assertNotIn("清倉", Q.describe(base) + QM.pace_line(base, 0, P.max_fanout))
        hz = QM.throttle_horizon_line(d, NOW)  # 清倉＝要「用完」：不再預告「隨 reset 逼近才放寬」
        self.assertEqual((B.NOTE_HORIZON in hz, "改做不吃額度" in hz), (True, False))
        self.assertTrue(QM.model_hint_line(d).endswith(B.NOTE_HINT + "\n"))

    def test_naming_the_short_window_gets_only_the_same_window_effect(self) -> None:
        s, short = real(), burn("five_hour", at(233))
        self.assertEqual(pair(s, "five_hour", short)[1][2], P.cap_prepare)
        self.assertEqual(*pair(s, "weekly_all", short))
        deltas = tuple(Q._delta_minutes(a.resets_at, NOW, s.measured_at) for a in s.axes)
        self.assertTrue(B._eligible(s.axes[3], deltas[3][0], P), "前提：五小時軸自己符合資格")
        self.assertFalse(any(short.masks(s, deltas, 5.0, "n", P, None)[1]), "供給軸不 qualifying")

    def test_neighbours_need_string_equality(self) -> None:
        for us, moved in ((0, True), (1, False)):  # 差 1 微秒＝不同窗
            s = state(A("weekly_all", 75.0, WEEK), A("nimbus_quill", 75.0, at(7663, us)))
            was, now = pair(s, "nimbus_quill", ratio=None)
            self.assertEqual(now != was, moved, us)

    def test_bd2_the_ladder_never_tightens_over_every_cell(self) -> None:
        for pct in (20.0, 55.0, 75.0, 90.0):
            for minutes in (500, 3000, 8000, None):
                a, b = pair(state(A("weekly_all", pct, at(minutes))), "weekly_all", ratio=None)
                self.assertGreaterEqual((b[2] is None, b[2] or 0), (a[2] is None, a[2] or 0),
                                        (pct, minutes))  # cap 分量（None＝不設限最寬）
                self.assertGreaterEqual(b[3], a[3], (pct, minutes))  # rec 分量獨立單調
                self.assertTrue(b[2] is None or b[2] < P.max_fanout, (pct, minutes))
        anchor = pair(state(A("weekly_all", 20.0, at(500))), "weekly_all", ratio=None)
        self.assertEqual(anchor[0], anchor[1], "錨點①（free×near）逐格不變")

    def test_bd3_halt_still_stops_and_bd8_must_finish_still_wins(self) -> None:
        s = state(A("weekly_all", 20.0, at(3000)), A("nimbus_quill", 96.0, at(8000)))
        d = dec(s, burn(), None)
        self.assertEqual((d.cap, d.recommended_fanout), (0, 0))
        self.assertIn("停止帶不隨時間放寬", QM.throttle_horizon_line(d, NOW))  # 不被清倉替代句蓋掉
        for minutes in (500, 3000, 8000, None):  # halt × 四個 horizon：被點名軸自己撞線
            self.assertEqual(*pair(state(A("weekly_all", 96.0, at(minutes))), "weekly_all",
                                   ratio=None))
        d = dec(state(A("weekly_all", 20.0, at(P.wrap_minutes - 2))), burn(), None)
        self.assertLessEqual(d.recommended_fanout, P.cap_prepare)
        self.assertIn(Q.NOTE_MUST_FINISH, d.reason)

    def test_bd4_fallback_kinds_are_never_relaxed_even_when_named(self) -> None:
        for kind in sorted(Q.FALLBACK_KINDS):
            for pct in (50.0, 94.0, 96.0):
                for named in (burn(), burn(kind)):
                    s = state(A("weekly_all", 75.0, WEEK), A(kind, pct, WEEK))
                    self.assertEqual(*pair(s, kind, named), (kind, pct, named.axis_kind))

    def test_every_floor_conjunct_is_load_bearing(self) -> None:
        for a, m in ((A("weekly_all", 96.0, WEEK), 3000.0), (A("spend", 50.0, WEEK), 3000.0),
                     (A("weekly_scoped", 50.0, WEEK), 3000.0), (A("weekly_all", 50.0, None), None),
                     (A("weekly_all", 50.0, at(-5)), -5.0)):  # halt／fallback／scoped／不明／偏移
            self.assertFalse(B._eligible(a, m, P), (a.kind, a.pct, m))
        self.assertTrue(B._eligible(A("weekly_all", 50.0, WEEK), 3000.0, P))
        s = state(A("five_hour_x", 8.0, at(-5)), A("weekly_all", 75.0, WEEK),
                  A("five_hour", 8.0, at(233)))  # decide 層：時鐘偏移的短窗軸不得被 Q-cross 放寬
        self.assertEqual(*pair(s, "five_hour_x"), "距 reset 為負的短窗軸被放寬了")
        self.assertNotEqual(*pair(s, "five_hour"), "對照：同一授權下正常的短窗軸確實被放寬")

    def test_bd9_authorised_but_inert_says_so_with_reasons(self) -> None:
        s = state(A("weekly_all", 20.0, at(500)), A("spend", 0.0, None))
        d, base = dec(s, burn(), None), dec(s, None, None)
        self.assertEqual(d.burndown.effect, "inert")
        for needle in ("清倉模式生效中", "本次未放寬任何軸：", "kind=spend（fallback 不納入）"):
            self.assertIn(needle, d.burndown.text)
        self.assertEqual((d.cap, d.recommended_fanout), (base.cap, base.recommended_fanout))
        self.assertEqual(dec(real(), burn()).burndown.effect, "relaxed")
        week = at(518)  # 2026-08-28 立案原型：週軸 56%、Fable 分軌軸 91% 是攤提供給軸、r=5.2
        proto = state(A("five_hour", 49.0, at(158)), A("weekly_all", 56.0, week),
                      A("weekly_scoped", 91.0, week, scope_model="Fable"))
        for model, why in (("fable", "攤提供給軸 kind=weekly_scoped 不 qualifying"),
                           ("sonnet", "攤提在此帶未收緊")):  # sonnet：分軌軸被遮掉、供給軸改回週軸
            d = Q.decide(proto, NOW, P, 5.2, "n=2", active_model=model, burndown=burn(resets=week))
            self.assertEqual(d.burndown.effect, "inert", model)  # 理由各自指名真正的原因
            self.assertNotIn(B.NOTE_HORIZON, QM.throttle_horizon_line(d, NOW), model)
            for needle in (f"kind=five_hour（{why}", "kind=weekly_all（視野已不在 far"):
                self.assertIn(needle, d.burndown.text, model)
        hook = dec(real(), burn(), None).burndown.text  # 真機形狀＋派工 hook（無換算比）
        self.assertIn("kind=five_hour（本軸無攤提上調可暫停", hook)
        self.assertNotIn("與被點名軸不同窗", hook)  # free 帶短窗軸不得被說成「不同窗」


class TestCarrierAndEffectiveness(unittest.TestCase):
    """BD-6／BD-7（生效判準全合取）、CLI 唯一寫入口與接電；痕跡／快取目錄隔離，不吃 `.env`。"""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory(prefix="bd-", ignore_cleanup_errors=True)
        self.tmp = Path(self.enterContext(tmp))
        self.path, self.cache = self.tmp / "d.json", self.tmp / M.CACHE_NAME
        env = {"AUTOSDD_TRACE_DIR": str(self.tmp), "AUTOSDD_QUOTA_CACHE_DIR": str(self.tmp)}
        self.enterContext(mock.patch.dict(os.environ, env))
        self.enterContext(mock.patch.object(QG, "policy_env", lambda root=None: {}))

    def put_cache(self, now, weekly_resets=None) -> None:
        rows = (("session", 233), ("weekly_all", 7663), ("weekly_scoped", 7663), ("five_hour", 233),
                ("seven_day", 7663), ("spend", 7663))
        axes = [{"kind": k, "pct": 75.0 if m > 300 else 8.0, "resets_at": (
            weekly_resets if k == "weekly_all" and weekly_resets is not None
            else (now + timedelta(minutes=m)).isoformat()),
            "scope_model": "Fable" if k == "weekly_scoped" else None} for k, m in rows]
        self.cache.write_text(json.dumps({"schema": M.SCHEMA, "measured_at": now.isoformat(),
                                          "account_key": "acct", "axes": axes}), encoding="utf-8")

    def put(self, **over) -> None:
        rec = dict(schema=B.SCHEMA, id="0123456789", directive_verbatim="清倉", issued_at=at(0),
                   axis_kind="weekly_all", until_resets_at=WEEK, core_signature=["k"],
                   readings_at_issue=[])
        self.path.write_text(json.dumps({**rec, **over}), encoding="utf-8")

    def active(self, s=None, env=None, sig=("k",)):
        return B.active(s or real(), NOW, env or {}, lambda st: sig, self.path)

    def test_valid_then_each_conjunct_breaks_it(self) -> None:
        self.put()
        self.assertEqual(self.active(), burn(), "六個欄位逐一等於期望（含 named_resets_at）")
        self.assertIsNone(self.active(env={B.OFF_ENV: "1"}), "kill-switch")
        self.assertIsNone(self.active(state(A("five_hour", 8.0, at(233)))), "被點名軸不在")
        self.assertIsNone(self.active(sig=("other",)), "方案指紋")
        for over in ({"axis_kind": "spend"}, {"axis_kind": "weekly_scoped"}, {"schema": "x"},
                     {"id": None}, {"core_signature": None}):
            self.put(**over)
            self.assertIsNone(self.active(), over)
        self.path.unlink()
        self.assertIsNone(self.active(), "落款檔缺席")

    def test_bd6_bd7_a_turned_over_or_unparseable_window_is_never_armed(self) -> None:
        for until in (at(-1), at(0), "", "2026-10-17T18:00:00", "garbage", None):
            self.put(until_resets_at=until)  # at(0)＝now==until 也已過期（嚴格小於）
            self.assertIsNone(self.active(), until)
            self.assertEqual(B._left(until, NOW) or INF, INF, "紅面：解不出就當永久有效")
        self.put(until_resets_at=at(-1))
        self.assertIsNotNone(B.read_directive(self.path), "紅面：只看落款檔存在會讓過期授權生效")
        d = dec(real(), self.active())
        self.assertEqual(d.cap, dec(real()).cap)
        self.assertNotIn("清倉", Q.describe(d) + QM.pace_line(d, 0, P.max_fanout))

    def issue(self, kind="weekly_all", text="清倉"):
        return B.issue(kind, text, NOW, self.cache, self.path)

    def hook_ids(self):  # 派工 hook 路徑的 decide() 帶了哪個落款
        with mock.patch.object(QG.quota_policy, "decide", wraps=Q.decide) as spy:
            QG.quota_gate({"tool_name": "Agent"}, blocking=("Agent",), latch_read=lambda p: set(),
                          latch_write=lambda p, k: None, plan_writer=lambda *a, **k: "",
                          waker=lambda *a, **k: {})
        return [c.kwargs["burndown"] and c.kwargs["burndown"].id for c in spy.call_args_list]

    def test_refusals_never_leave_a_file(self) -> None:
        self.assertEqual(self.issue()[0], 1)  # 快取缺席
        self.put_cache(NOW)
        for kind, why in (("nope", "沒有 kind=nope"), ("weekly_scoped", "QB4"), ("spend", "QB4")):
            rc, msg = self.issue(kind)  # 不存在的軸／分軌軸／付費保險軸（後二者要擋在 QB4）
            self.assertTrue(rc == 1 and why in msg, (kind, msg))
        self.assertEqual(self.issue(text=" ")[0], 1, "指令逐字為空")
        for bad in ("", "2026-10-17T18:00:00", "garbage"):  # BD-7 寫入端：三臂皆非零 rc 且不落檔
            self.put_cache(NOW, weekly_resets=bad)
            self.assertEqual(self.issue()[0], 1, bad)
        self.assertFalse(self.path.exists())

    def test_issue_status_revoke_roundtrip_and_argument_errors(self) -> None:
        self.put_cache(NOW)
        rc, msg = self.issue()
        rec = json.loads(self.path.read_text(encoding="utf-8"))
        sig = QG.core_signature(QG.read_quota(NOW, self.cache))
        self.assertEqual((rc, rec["until_resets_at"]), (0, at(7663)))
        self.assertEqual(rec["core_signature"], list(sig))
        self.assertTrue(all(rec[k] for k in B.FIELDS) and len(rec["readings_at_issue"]) == 6)
        self.assertIsNotNone(datetime.fromisoformat(rec["issued_at"]).utcoffset(), "須帶 offset")
        self.assertTrue("不具防偽性質" in msg and "逾 TTL" not in msg)  # 快取新鮮：不出警示
        self.assertEqual(B.status(NOW, {}, self.path)[0], 0)
        self.assertIn("✗ " + B.OFF_ENV, B.status(NOW, {B.OFF_ENV: "1"}, self.path)[1])
        self.assertEqual(B.revoke(self.path)[0], 0)
        rc, text = B.status(NOW, {}, self.path)
        self.assertEqual((rc, "✗ 落款檔存在" in text), (1, True))
        for argv in (["--bogus"], ["--issue", "weekly_all"], []):  # 未知引數仍要 rc=2 出聲
            with mock.patch("sys.stderr"), self.assertRaises(SystemExit) as cm:
                B.main(argv)
            self.assertEqual(cm.exception.code, 2)
        self.put_cache(NOW - timedelta(minutes=30))  # 快取逾 TTL 仍可落款（不改行為），但要出聲警示
        self.assertIn("快取已逾 TTL", self.issue()[1])

    def test_pace_and_the_dispatch_hook_both_carry_the_directive(self) -> None:
        now = datetime.now().astimezone()
        self.put_cache(now)
        B.issue("weekly_all", "清倉")  # 預設路徑＝AUTOSDD_TRACE_DIR 下的落款檔，與 hook 讀的同一份
        ident = B.read_directive()["id"]
        report = QG.pace_report(now=now)
        self.assertEqual(report.count("清倉模式生效中"), 1, "全文清倉段整份輸出只印一次")
        self.assertIn(f"🔥清倉 {ident}：", report.splitlines()[0])  # 標題行只帶短標記
        for name, key, want in ((QG.BURN_LEDGER_NAME, "bd", ident),
                                (B.EVENTS_NAME, "effect", "relaxed")):
            last = (self.tmp / name).read_text(encoding="utf-8").splitlines()[-1]
            self.assertEqual(json.loads(last)[key], want, name)
        self.assertLessEqual({"decided_cap", "decided_rec"}, json.loads(last).keys())  # 穩定化前
        self.assertEqual(self.hook_ids(), [ident], "派工 hook 的 decide() 沒帶落款")
        with mock.patch.object(QG, "policy_env", lambda root=None: {B.OFF_ENV: "1"}):
            self.assertNotIn("清倉", QG.pace_report(now=now))
            self.assertEqual(self.hook_ids(), [None], "kill-switch 在派工 hook 路徑也要生效")
        self.assertIsNone(json.loads(W.row_of(NOW.isoformat(), (("a", 1.0),)))["bd"])  # 無授權


if __name__ == "__main__":
    unittest.main()
