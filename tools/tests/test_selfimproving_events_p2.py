# 受測面：tools/lib/selfimproving/sandbox.py（程式碼鎖，非散文）
"""SelfImproving P2 事件詞彙、欄位表、狀態機與 `check` 追加項的驗收測試（TCS-P2 EP 檔）。

方法名含 AT 底線形（錨定 `-k AT_240_1_1_` 只收一個），夾具全用 tmp 目錄內的合成 repo
（hermetic 環境，不碰真帳本、不上網）。合成編號於執行期組出。
"""

from __future__ import annotations

import hashlib
import json
import os
import unittest
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2
from _selfimproving_fixtures import SiTestCase, ev, pid, rid
from _selfimproving_p2_fixtures import P2TestCase

from lib.selfimproving import events as si_events
from lib.selfimproving import fold as si_fold

HEAD = "0" * 40


def setUpModule() -> None:
    fx.setup("si_p2e_")


def tearDownModule() -> None:
    fx.teardown()


def comp(event: dict, seq: int = 9) -> dict:
    """補欄後的單一事件 dict（seq 預設 9，使 `card_seq` 的預設 1 小於它）。"""
    return fx.compose([event], HEAD, [seq])[0]


def ok_events() -> dict[str, dict]:
    """§5.2 `EV-OK`：每個 P2 kind 的合規代表事件（欄位值取夾具預設，括號內為覆寫）。"""
    out: dict[str, dict] = {"card": fx.card_ev(1)}
    for dk in si_events_dkinds():
        tail = {"run": rid(1)} if dk == "resume" else {"prop": pid(1)}
        out[f"dec-t-{dk}"] = ev("dec", "掌舵者", dkind=dk, **tail)
        out[f"dec-c-{dk}"] = ev("dec", "main", dkind=dk, carrier="console", **tail)
    out["freeze"] = fx.freeze_ev(1)
    out["sbx-ok"] = fx.sandbox_ev(1)
    out["sbx-export"] = fx.sandbox_ev(1, applied=False, fail_code="SANDBOX-EXPORT-FAILED")
    out["sbx-timeout"] = fx.sandbox_ev(1, applied=False, fail_code="SANDBOX-APPLY-TIMEOUT")
    out["sbx-nofit"] = fx.sandbox_ev(1, applied=False)
    out["ver-pass"] = fx.verify_ev(1, "PASS")
    out["ver-fail"] = fx.verify_ev(1, "FAIL")
    out["ver-ne0"] = fx.verify_ev(1, "NE")
    out["ver-ne1"] = fx.verify_ev(1, "NE", probes_n=1, baseline_red=False, patched_green=None,
                                  mutated_red=None, carrier_proof=True, verify_sha256=fx.H(9),
                                  heldout_digest=fx.H(7), reasons=["BASELINE-NOT-RED"])
    out["promote"] = fx.promote_ev(1)
    out["rollback"] = fx.rollback_ev(1)
    out["obs-add"] = fx.obs_add_ev()
    out["obs-close"] = fx.obs_close_ev()
    return out


def si_events_dkinds():
    from lib.selfimproving.events import DKINDS

    return DKINDS


_TY, _MI, _UN = "EVENT-TYPE", "EVENT-KEY-MISSING", "EVENT-KEY-UNKNOWN"


def neg_cases() -> list[tuple[str, str, object, set[str]]]:
    """§5.2 `EV-NEG`：（標籤, 基底鍵, 變異, 預期碼集合）；變異為 (動作, 鍵[, 值])。"""
    drop = lambda k: ("drop", k)  # noqa: E731
    put = lambda k, v: ("put", k, v)  # noqa: E731
    t = "dec-t-"
    c = "dec-c-"
    return [
        ("card 缺 card_sha256", "card", drop("card_sha256"), {_MI}),
        ("card 多 note", "card", put("note", "x"), {_UN}),
        ("card rev 0", "card", put("rev", 0), {_TY}),
        ("card digest 形態", "card", put("digest", "sha256:XYZ"), {_TY}),
        ("dec 缺 quote", t + "approve", drop("quote"), {_MI}),
        ("dec 缺 card_seq", t + "approve", drop("card_seq"), {_MI}),
        ("dec card_seq 不小於 seq", t + "approve", put("card_seq", 9), {_TY}),
        ("dec decider 非掌舵者", t + "approve", put("decider", "main"), {_TY}),
        ("console 多 quote", c + "approve", put("quote", "核准 x"), {_UN}),
        ("console decider a;b", c + "approve", put("decider", "a;b"), {_TY}),
        ("dec prop 與 run 同時有", t + "approve", put("run", rid(1)), {_TY}),
        ("dec dkind approve-all", t + "approve", put("dkind", "approve-all"), {_TY}),
        ("dec flags x", t + "promote", put("flags", ["x"]), {_TY}),
        ("approve 帶 flags", t + "approve", put("flags", ["unverified_ack"]), {_UN}),
        ("approve 帶 reason_class", t + "approve", put("reason_class", "未說明"), {_UN}),
        ("reject 缺 reason", t + "reject", drop("reason"), {_MI}),
        ("reject 缺 reason_class", t + "reject", drop("reason_class"), {_MI}),
        ("promote 缺 digest", t + "promote", drop("digest"), {_MI}),
        ("rollback 帶 digest", t + "rollback", put("digest", fx.H(4)), {_UN}),
        ("dec decided_at 無 offset", t + "approve", put("decided_at", "2026-10-20T08:00:00"),
        {_TY}),
        ("freeze n 0", "freeze", put("n", 0), {_TY}),
        ("freeze frozen_by 含空白", "freeze", put("frozen_by", "a b"), {_TY}),
        ("sbx applied 真而 touched_ok null", "sbx-ok", put("touched_ok", None), {_TY}),
        ("sbx applied 假而 rollback_ok 真", "sbx-nofit", put("rollback_ok", True), {_TY}),
        ("sbx fail_code X", "sbx-nofit", put("fail_code", "X"), {_TY}),
        ("sbx export 失敗而 sha 非 null", "sbx-export", put("sandbox_sha256", fx.H(8)), {_TY}),
        ("sbx sha null 而 fail_code null", "sbx-nofit", put("sandbox_sha256", None), {_TY}),
        ("sbx timeout 而 applied 真", "sbx-timeout", put("applied", True), {_TY}),
        ("sbx base 39 位", "sbx-ok", put("base", "a" * 39), {_TY}),
        ("verify verdict OK", "ver-pass", put("verdict", "OK"), {_TY}),
        ("verify reasons 含未知碼", "ver-ne0", put("reasons", ["NOPE"]), {_TY}),
        ("verify PASS 而 reasons 非空", "ver-pass", put("reasons", ["NO-PROBES"]), {_TY}),
        ("verify NE 而 reasons 空", "ver-ne0", put("reasons", []), {_TY}),
        ("verify probes_n 0 而 sha 非 null", "ver-pass", put("probes_n", 0), {_TY}),
        ("verify probes_n 2 而 sha null", "ver-pass", put("verify_sha256", None), {_TY}),
        ("verify baseline_red 字串", "ver-pass", put("baseline_red", "yes"), {_TY}),
        ("verify heldout_digest 形態", "ver-pass", put("heldout_digest", "sha256:bad"), {_TY}),
        ("promote unverified_ack 字串", "promote", put("unverified_ack", "yes"), {_TY}),
        ("promote head_sha 7 位", "promote", put("head_sha", "abcdef0"), {_TY}),
        ("promote 缺 post_sha256", "promote", drop("post_sha256"), {_MI}),
        ("rollback 多 commit_sha", "rollback", put("commit_sha", "x"), {_UN}),
        ("obs.add carrier transcript", "obs-add", put("carrier", "transcript"), {_TY}),
        ("obs.add decider a;b", "obs-add", put("decider", "a;b"), {_TY}),
        ("obs.add obs 形態", "obs-add", put("obs", "OBS-1"), {_TY}),
        ("obs.close disposition 空", "obs-close", put("disposition", ""), {_TY}),
    ]


def mutate(base: dict, action: tuple) -> dict:
    obj = dict(base)
    if action[0] == "drop":
        obj.pop(action[1])
    else:
        obj[action[1]] = action[2]
    return obj


class TestEventTables(SiTestCase):
    """受測：`tools/lib/selfimproving/events.py`（R72 欄位表）。"""

    def test_AT_240_1_1_vocabulary_and_conforming_events(self):
        self.assertEqual(len(si_events.KINDS), 21)
        self.assertTrue({"obs.add", "obs.close"} <= set(si_events.KINDS))
        bad = {}
        for label, event in ok_events().items():
            problems = si_events.validate(comp(event))
            if problems:
                bad[label] = problems
        self.assertEqual(bad, {})
        legacy = [
            fx.dec_ev(1, "approve"),
            *fx._verify(1, "PASS"),
            ev("app.sandbox", "main", prop=pid(1)),
            ev("card", "main", prop=pid(1)),
        ]
        for event in legacy:
            self.assertEqual(si_events.validate(comp(event)), [], event)
        problems = si_events.validate(comp(ev("x.y")))
        self.assertEqual([c for c, _ in problems], ["EVENT-KIND"])
        self.assertIn("21 個詞彙", problems[0][1])

    def test_AT_240_1_E_1_field_table_negatives(self):
        base = {label: comp(event) for label, event in ok_events().items()}
        cases = neg_cases()
        used = {key.split("-")[0] for _, key, _, _ in cases}
        self.assertTrue({"card", "dec", "freeze", "sbx", "ver", "promote", "rollback", "obs"}
                        <= used)
        for label, key, action, want in cases:
            with self.subTest(label):
                self.assertEqual(si_events.validate(base[key]), [], f"{label} 的基底須合規")
                got = {code for code, _ in si_events.validate(mutate(base[key], action))}
                self.assertEqual(got, want, label)
        # 超長 disposition 由 check 的 events.structure（帶 row_max_bytes）判
        repo = fx2.p2_base()
        rmb = json.loads(fx.read(repo, fx.PARAMS))["row_max_bytes"]
        events = [*fx2.RUN_EVENTS, fx.obs_close_ev(disposition="決" * (rmb // 3 + 1))]
        fx.write_events(repo, events)
        res = self.check(repo)
        self.assertEqual(self.S(res, "events.structure"), "FAIL")
        self.assertEqual(fx2.codes(res, "events.structure"), {_TY})
        fx.write_events(repo, [*fx2.RUN_EVENTS, fx.obs_close_ev(disposition="決" * (rmb // 3))])
        self.assertEqual(self.S(self.check(repo), "events.structure"), "PASS")


class TestStateMachine(SiTestCase):
    """受測：`tools/lib/selfimproving/fold.py`（R74、R75）。"""

    def replay(self, events, **prm):
        repo = fx2.p2_base()
        fx.set_params(repo, **prm)
        fx.write_events(repo, events)
        return self.check(repo)

    def test_AT_240_2_1_legal_lifecycle(self):
        events = fx2.sc_p2_legal()
        res = self.replay(events)
        self.assertEqual(self.S(res, "events.structure"), "PASS")
        self.assertEqual(self.S(res, "events.transitions"), "PASS")
        self.assertEqual(self.F(res, "events.transitions"), set())
        f = si_fold.fold(si_events.sound(fx.compose(events, HEAD)), 2, 2)
        self.assertEqual(f.problems, [])
        p = f.props
        self.assertEqual(p[pid(124)].state, "promoted")
        self.assertEqual((p[pid(124)].rollback_ok, p[pid(124)].touched_ok), (True, True))
        self.assertEqual(p[pid(125)].state, "promoted")
        c = p[pid(126)]
        self.assertEqual((c.rev, c.state, c.verdict, c.flags, c.reasons), (2, "proposed", None, [],
            []))
        self.assertEqual((c.rollback_ok, c.touched_ok), (None, None))
        d = p[pid(127)]
        self.assertEqual((d.state, d.verdict, d.reasons), ("verified", "PASS", []))
        e = p[pid(128)]
        self.assertEqual(e.state, "rejected")
        want = [x for x in f.cooldowns if x["prop"] == pid(128)]
        self.assertEqual([x["reason_class"] for x in want], ["風險過高"])
        # rev 1 的退回快照：重放到 return 為止時 reasons 含 TOUCHED-SUPERSET
        upto = [e for e in fx.compose(events, HEAD) if not (e["kind"] == "prop"
                                                           and e.get("rev") == 2)]
        f1 = si_fold.fold(si_events.sound(upto), 2, 2)
        self.assertEqual(f1.props[pid(126)].state, "returned")
        self.assertIn("TOUCHED-SUPERSET", f1.props[pid(126)].reasons)

    def _trans(self, tail, *, prm=None):
        res = self.replay([*fx2.RUN_EVENTS, *tail], **(prm or {}))
        return res, self.S(res, "events.transitions"), self.F(res, "events.transitions")

    def test_AT_240_2_E_1_illegal_transitions(self):
        n = 130
        pre = [fx.prop_ev(n, 1, target=[f"docs/notes/n{n}.md"])]
        appr = [*pre, fx.dec_ev(n, "approve")]
        frozen = [*appr, fx.freeze_ev(n)]
        sbx = [*frozen, fx.sandbox_ev(n)]
        pass_chain = [*sbx, fx.verify_ev(n, "PASS")]
        illegal = {
            "a": ([*pre, fx.sandbox_ev(n)], "TRANSITION-ILLEGAL"),
            "b": ([*appr, fx.verify_ev(n, "PASS")], "TRANSITION-ILLEGAL"),
            "c": ([*frozen, fx.sandbox_ev(n, rollback_ok=False), fx.verify_ev(n, "PASS"),
                   fx.dec_ev(n, "promote")], "TRANSITION-ILLEGAL"),
            "d": ([*frozen, fx.sandbox_ev(n, touched_ok=False), fx.verify_ev(n, "PASS"),
                   fx.dec_ev(n, "promote")], "TRANSITION-ILLEGAL"),
            "e": ([*sbx, fx.verify_ev(n, "NE"), fx.dec_ev(n, "return", reason_class="證據不足")],
                  "TRANSITION-ILLEGAL"),
            "f": ([*pass_chain, fx.verify_ev(n, "PASS"), fx.verify_ev(n, "PASS")],
                  "VERIFY-RUNS-EXCEEDED"),
            "g": ([*pass_chain, fx.promote_ev(n)], "TRANSITION-ILLEGAL"),
            "h": ([*pass_chain, fx.dec_ev(n, "promote"), fx.promote_ev(n), fx.rollback_ev(n)],
                  "TRANSITION-ILLEGAL"),
            "i": ([ev("dec", "掌舵者", dkind="resume", run=rid(99), reason="x")],
                  "TRANSITION-ORPHAN"),
            "j": ([*pre, fx.dec_ev(n, "unblock")], "TRANSITION-ILLEGAL"),
            "k": ([*pre, fx.dec_ev(n, "return", reason_class="證據不足"), fx.sandbox_ev(n)],
                  "TRANSITION-ILLEGAL"),
            "l": ([*pass_chain, fx.dec_ev(n, "approve")], "TRANSITION-ILLEGAL"),
        }
        for key, (tail, code) in illegal.items():
            with self.subTest(key):
                res, status, found = self._trans(tail, prm={"verify_runs_max": 2})
                self.assertEqual(status, "FAIL", key)
                self.assertEqual({c for _, c in found}, {code}, (key, found))
        controls = {
            "e2": [*sbx, fx.verify_ev(n, "NE", reasons=["TOUCHED-SUPERSET"]),
                   fx.dec_ev(n, "return", reason_class="證據不足")],
            "f2": [*pass_chain, fx.verify_ev(n, "PASS")],
            "c2": [*pass_chain, fx.dec_ev(n, "promote")],
        }
        for key, tail in controls.items():
            with self.subTest(key):
                self.assertEqual(self._trans(tail, prm={"verify_runs_max": 2})[1], "PASS", key)

    def test_AT_240_2_E_2_ledger_invariants(self):
        n = 131
        pre = [fx.prop_ev(n, 1, target=[f"docs/notes/n{n}.md"])]
        appr = [*pre, fx.dec_ev(n, "approve")]
        base = [*appr, fx.freeze_ev(n), fx.sandbox_ev(n), fx.verify_ev(n, "PASS")]
        ne_chain = [*appr, fx.freeze_ev(n), fx.sandbox_ev(n), fx.verify_ev(n, "NE")]
        flagged = lambda ack: [  # noqa: E731
            *ne_chain, fx.dec_ev(n, "promote", flags=["unverified_ack"]),
            fx.promote_ev(n, unverified_ack=ack)]
        plain = lambda ack: [  # noqa: E731
            *base, fx.dec_ev(n, "promote"), fx.promote_ev(n, unverified_ack=ack)]
        rolled = lambda **kw: [  # noqa: E731
            *plain(False), fx.dec_ev(n, "rollback"), fx.rollback_ev(n, **kw)]
        cases = {
            "a": ([*appr, fx.freeze_ev(n, frozen_by="SA"), fx.sandbox_ev(n)],
                  "FROZEN-BY-PROPOSER", [*appr, fx.freeze_ev(n), fx.sandbox_ev(n)]),
            "b": ([*appr, fx.freeze_ev(n), fx.freeze_ev(n), fx.sandbox_ev(n)], "HELDOUT-DUP",
                  [*appr, fx.freeze_ev(n), fx.sandbox_ev(n)]),
            "c": ([*appr, fx.sandbox_ev(n), fx.freeze_ev(n)], "HELDOUT-AFTER-SANDBOX",
                  [*appr, fx.freeze_ev(n), fx.sandbox_ev(n)]),
            "c2": ([*appr, fx.sandbox_ev(n)], "HELDOUT-AFTER-SANDBOX",
                   [*appr, fx.freeze_ev(n), fx.sandbox_ev(n)]),
            "d": ([*appr, fx.freeze_ev(n), fx.sandbox_ev(n, base="1" * 40)],
                  "SANDBOX-BASE-MISMATCH", [*appr, fx.freeze_ev(n), fx.sandbox_ev(n)]),
            "e": (flagged(False), "PROMOTE-ACK-MISMATCH", flagged(True)),
            "e2": (plain(True), "PROMOTE-ACK-MISMATCH", plain(False)),
            "f": (rolled(pre_sha256=fx.H(12)), "ROLLBACK-MANIFEST-MISMATCH", rolled()),
            "f2": (rolled(post_sha256=fx.H(12)), "ROLLBACK-MANIFEST-MISMATCH", rolled()),
            "g": ([*pre, fx.dec_ev(n, "approve", digest=fx.H(99))], "DEC-TARGET-MISMATCH",
                  appr),
        }
        for key, (tail, code, good) in cases.items():
            with self.subTest(key):
                res, status, found = self._trans(tail)
                self.assertEqual(status, "FAIL", key)
                self.assertEqual({c for _, c in found}, {code}, (key, found))
                self.assertEqual(self._trans(good)[1], "PASS", f"{key} 的合規對照")
        # card_seq 指向不存在事件的 dec 不被 events.transitions 標紅（離線不驗連結，⚖ 24）
        dangling = [*pre, fx.dec_ev(n, "approve", card_seq=2)]
        self.assertEqual(self._trans(dangling)[1], "PASS")


class TestCooldown(P2TestCase):
    """受測：`tools/lib/selfimproving/cooldown.py`、`props.py`、`fold.py`（R82）。"""

    def codes_of_try(self, R, sources, **kw):
        rc, out, err = fx2.new_try(R, sources, **kw)
        return rc, out, fx.codes_of(out)

    def test_AT_213_2_1_cooldown_blocks_same_type(self):
        o = fx.obs_id
        R, a = fx2.cool_base()
        snap0 = fx.snap(R)
        rc, out, codes = self.codes_of_try(R, [o(12)])
        self.assertEqual(rc, 1, out)
        self.assertIn("COOLDOWN", codes)
        self.assertIn(a, out)
        self.draft_ok(R, out, "COOLDOWN")
        self.assertEqual(fx.snap(R), snap0)
        R2, _ = fx2.cool_base()
        self.assertEqual(self.codes_of_try(R2, [o(12)], cls="P")[0], 0)
        R3, _ = fx2.cool_base()
        self.assertEqual(self.codes_of_try(R3, [o(12)], target=fx2.OTHER)[0], 0)
        # (4)(5) 解除後再提：須附 reject_response
        R4, a4 = fx2.cool_base()
        fx.append_events(R4, [fx.ev("dec", "掌舵者", prop=a4, dkind="unblock")])
        rc, out, codes = self.codes_of_try(R4, [o(12)])
        self.assertEqual((rc, codes), (1, {"REJECT-RESPONSE-MISSING"}), out)
        self.assertEqual(self.codes_of_try(R4, [o(12)], response=True)[0], 0)
        # (6) (b-2) 新證據：同根因（已確認）、證據不相交、時間晚於否決
        row = fx2.obs_row(14, f"{fx2.OTHER}:7", days_ago=1)
        R6, a6 = fx2.cool_base(rows=[row])
        fx2.attr_root(R6, 14, 3)
        rc, out, codes = self.codes_of_try(R6, [o(14)], response=True)
        self.assertEqual(rc, 0, out)

    def test_AT_213_2_E_1_cooldown_release_negatives(self):
        o = fx.obs_id
        resp = {"response": True}
        # (a) 證據相交
        R, a = fx2.cool_base(rows=[fx2.obs_row(15, f"{fx2.DEMO}:12", days_ago=1)])
        fx2.attr_root(R, 15, 3)
        cases = {"a": (R, a, [o(15)])}
        # (b) 未確認的 attr
        R, a = fx2.cool_base(rows=[fx2.obs_row(16, f"{fx2.OTHER}:7", days_ago=1)])
        fx2.attr_root(R, 16, 3, confirm=False)
        cases["b"] = (R, a, [o(16)])
        # (c) 時間早於否決
        R, a = fx2.cool_base(rows=[fx2.obs_row(17, f"{fx2.OTHER}:7", days_ago=4)])
        fx2.attr_root(R, 17, 3)
        cases["c"] = (R, a, [o(17)])
        # (d) 新證據只是 DEF 列
        R, a = fx2.cool_base()
        fx.put(R, fx.DEFLOG, fx.read(R, fx.DEFLOG).rstrip("\n") + "\n" + fx.line(
            [fx.def_id(2), "2026-10-20", "夾具", "tools/lib/si_other.py:3", "P2", "-",
            "open"]) + "\n")
        fx.commit_all(R, "def")
        cases["d"] = (R, a, [o(12), fx.def_id(2)])
        for label, (R, a, sources) in cases.items():
            with self.subTest(label):
                rc, out, codes = self.codes_of_try(R, sources)
                self.assertEqual(rc, 1, out)
                self.assertIn("COOLDOWN", codes, label)
                fx.append_events(R, [fx.ev("dec", "掌舵者", prop=a, dkind="unblock")])
                self.assertEqual(self.codes_of_try(R, sources, **resp)[0], 0, f"{label} 解除後")
        # (e) 未說明：最嚴冷卻，只有 unblock 能結束
        R, a = fx2.cool_base(reject_class="未說明",
                             rows=[fx2.obs_row(18, f"{fx2.OTHER}:7", days_ago=1)])
        fx2.attr_root(R, 18, 3)
        rc, out, codes = self.codes_of_try(R, [o(18)], **resp)
        self.assertEqual(rc, 1, out)
        self.assertIn("COOLDOWN", codes)
        fx.append_events(R, [fx.ev("dec", "掌舵者", prop=a, dkind="unblock")])
        self.assertEqual(self.codes_of_try(R, [o(18)], **resp)[0], 0)
        # (f) 退回不啟動冷卻
        R, a = fx2.cool_base(kind="return")
        rc, out, codes = self.codes_of_try(R, [o(11)])
        self.assertEqual(rc, 1, out)
        self.assertIn("DUPLICATE-TYPE", codes)
        self.assertNotIn("COOLDOWN", codes)

    def _transitions(self, R):
        res = self.check(R)
        item = res["_item"]["events.transitions"]
        return res, item, {(f["subject"], f["code"], f["level"]) for f in item["findings"]}

    def test_AT_213_3_1_no_false_bypass_warning(self):
        o = fx.obs_id
        # L0：只有 reject
        R0, a0 = fx2.cool_base()
        res, item, found = self._transitions(R0)
        self.assertEqual(item["status"], "PASS")
        self.assertFalse({c for _, c, _ in found} & {"COOLDOWN-BYPASS-SUSPECT"})
        cool = {c["prop"]: c["reason_class"] for c in self.MJ(R0, "status")["cooldowns"]}
        self.assertEqual(cool, {a0: "證據不足"})
        # L1：unblock 之後同型 prop-new（附 reject_response）
        R1, a1 = fx2.cool_base()
        fx.append_events(R1, [fx.ev("dec", "掌舵者", prop=a1, dkind="unblock")])
        self.assertEqual(fx2.new_try(R1, [o(12)], response=True)[0], 0)
        res, item, found = self._transitions(R1)
        self.assertEqual(item["status"], "PASS")
        self.assertFalse({c for _, c, _ in found} & {"COOLDOWN-BYPASS-SUSPECT"})
        self.assertEqual(self.MJ(R1, "status")["cooldowns"], [])
        # L2：不同型（cls P）的第二個 PROP，第一個仍在冷卻中
        R2, a2 = fx2.cool_base()
        self.assertEqual(fx2.new_try(R2, [o(12)], cls="P")[0], 0)
        res, item, found = self._transitions(R2)
        self.assertEqual(item["status"], "PASS")
        self.assertFalse({c for _, c, _ in found} & {"COOLDOWN-BYPASS-SUSPECT"})
        # L3：(b-2) 新證據成立的同型 prop-new（未 unblock）——離線只能是 warn
        row = fx2.obs_row(14, f"{fx2.OTHER}:7", days_ago=1)
        R3, a3 = fx2.cool_base(rows=[row])
        fx2.attr_root(R3, 14, 3)
        self.assertEqual(fx2.new_try(R3, [o(14)], response=True)[0], 0)
        res, item, found = self._transitions(R3)
        new_pid = fx.EV(R3)[-1]["id"]
        self.assertEqual(item["status"], "PASS")
        self.assertEqual({(s, c, lv) for s, c, lv in found},
                         {(new_pid, "COOLDOWN-BYPASS-SUSPECT", "warn")})

    def test_AT_213_3_E_1_bypass_is_detected(self):
        R, a = fx2.cool_base()
        n = int(a.rsplit("-", 1)[1]) + 1

        def tail(**kw):
            base = {"cls": "D", "target": [fx2.DEMO], "sources": [fx.obs_id(11)]}
            base.update(kw)
            return [fx.prop_ev(n, 1, **base)]

        def check(R, events):
            fx.append_events(R, events)
            res = self.check(R)
            item = res["_item"]["events.transitions"]
            return item["status"], {(f["subject"], f["code"], f["level"])
                                    for f in item["findings"]}

        status, found = check(R, tail())
        self.assertEqual(status, "PASS")
        self.assertEqual(found, {(fx.pid(n), "COOLDOWN-BYPASS-SUSPECT", "warn")})
        R2, a2 = fx2.cool_base()
        unb = [fx.ev("dec", "掌舵者", prop=a2, dkind="unblock")]
        self.assertEqual(check(R2, unb + tail())[1], set())
        R3, _ = fx2.cool_base()
        self.assertEqual(check(R3, tail(target=[fx2.OTHER]))[1], set())
        R4, _ = fx2.cool_base()
        self.assertEqual(check(R4, tail(cls="P"))[1], set())


class TestCardIssue(P2TestCase):
    """受測：`tools/lib/selfimproving/decwrite.py` 的 `card --issue`（R81）。"""

    def test_AT_240_6_1_issue_records_a_card_event(self):
        R, p = fx2.template("proposed-only", lambda r: fx2.new_prop(r))
        out0 = self.M(R, "card", p)[1]
        n0 = len(fx.EV(R))
        for _ in range(2):
            rc, out, err = self.M(R, "card", p, "--issue", "--by", "main")
            self.assertEqual(rc, 0, out + err)
            self.assertEqual(out.encode("utf-8"), out0.encode("utf-8"))
            self.assertRegex(err, rf"^ok card seq=\d+ prop={p} digest8=[0-9a-f]{{8}}\n$")
        rc, out, err = self.M(R, "card", p, "--issue", "--json")
        self.assertEqual(rc, 0, out + err)
        obj = json.loads(out)
        cards = [e for e in fx.EV(R) if e["kind"] == "card"]
        self.assertEqual(len(fx.EV(R)) - n0, 3)
        pe = fx2.prop_event(R, p)
        for e in cards:
            self.assertEqual(list(e), ["seq", "t", "kind", "by", "prop", "rev", "digest",
                                       "card_sha256"])
            self.assertEqual((e["digest"], e["rev"]), (pe["digest"], pe["rev"]))
        want = "sha256:" + hashlib.sha256(out0.replace("\r\n", "\n").encode("utf-8")).hexdigest()
        self.assertEqual({e["card_sha256"] for e in cards}, {want})
        self.assertEqual(len({e["seq"] for e in cards}), 3)
        self.assertEqual(obj["issued"], {"seq": cards[-1]["seq"], "card_sha256": want})
        base = json.loads(self.M(R, "card", p, "--json")[1])
        self.assertEqual(list(obj)[:-1], list(base))
        self.assertEqual({k: v for k, v in obj.items() if k != "issued"}, base)

    def test_AT_240_6_E_1_state_preconditions(self):
        def prep(state):
            def build(R):
                p = fx2.new_prop(R, route="handoff:T1" if state == "handed-off" else "loop")
                if state in ("proposed", "handed-off"):
                    if state == "handed-off":
                        fx2.issue_card(R, p)
                        assert fx2.decide_say(R, p, f"轉交 {p}")[0] == 0
                    return p
                fx2.issue_card(R, p)
                if state == "returned":
                    assert fx2.decide_say(R, p, f"退回 {p} 補", reason_class="證據不足")[0] == 0
                elif state in ("approved", "sandboxed", "verified", "promoted"):
                    assert fx2.decide_say(R, p, f"核准 {p}")[0] == 0
                    if state != "approved":
                        pe = fx2.prop_event(R, p)
                        ev = [fx.ev("heldout.freeze", "FZ", prop=p),
                              fx.ev("app.sandbox", "main", prop=p, base=pe["base"])]
                        if state in ("verified", "promoted"):
                            ev.append(fx.ev("app.verify", "main", prop=p, verdict="PASS"))
                        if state == "promoted":
                            card = fx2.last_event(R, "card")
                            ev += [fx.ev("dec", "掌舵者", prop=p, dkind="promote",
                                         digest=pe["digest"], card_seq=card["seq"],
                                         quote=f"晉升 {p}"),
                                   fx.ev("app.promote", "main", prop=p)]
                        fx.append_events(R, ev)
                elif state in ("rejected-cool", "rejected-free"):
                    assert fx2.decide_say(R, p, f"否決 {p} 證據座標不足",
                                          reason_class="證據不足")[0] == 0
                    if state == "rejected-free":
                        assert fx2.decide_say(R, p, f"解除 {p}")[0] == 0
                return p
            return fx2.template(f"issue-{state}", build)

        bad = ["approved", "sandboxed", "returned", "handed-off", "rejected-free"]
        good = ["proposed", "verified", "promoted", "rejected-cool"]
        for state in bad:
            with self.subTest(state):
                R, p = prep(state)
                n0 = len(fx.EV(R))
                rc, out, err = self.M(R, "card", p, "--issue")
                self.rejected(rc, out, {"STATE-ILLEGAL"}, state)
                self.assertEqual(len(fx.EV(R)), n0)
                self.assertEqual(self.M(R, "card", p)[0], 0)
        for state in good:
            with self.subTest(state):
                R, p = prep(state)
                rc, out, err = self.M(R, "card", p, "--issue")
                self.assertEqual(rc, 0, out + err)
        R, p = prep("proposed")
        ghost = "PROP-SI-" + f"{int(p.rsplit('-', 1)[1]) + 900:03d}"
        self.usage_error(*self.M(R, "card", ghost, "--issue"))
        n0 = len(fx.EV(R))
        with mock.patch.dict(os.environ, {"AUTOSDD_UNATTENDED": "1"}):
            rc, out, err = self.M(R, "card", p, "--issue")
        self.rejected(rc, out, {"UNATTENDED-REFUSED"})
        self.assertEqual(len(fx.EV(R)), n0)


def approved_copy(route: str = "loop"):
    """已核准的 PROP 的獨立複本（樣板快取）；回 (repo, prop)。"""
    return fx2.template(f"approved-{route}", lambda r: fx2.drive_to(r, "approved", route=route))


class TestHeldoutFreeze(P2TestCase):
    """受測：`tools/lib/selfimproving/decwrite.py`、`heldout.py`、`manifest.py`（R83、R84）。"""

    def fresh(self, route="loop"):
        self.new_home()
        return approved_copy(route)

    def freeze(self, R, p, src, by="FZ", *extra):
        return self.M(R, "heldout-freeze", p, "--from", src, "--by", by, *extra)

    def heldout_dir(self, **kw):
        return fx2.make_heldout(fx.new_dir("ho"), **kw)

    def test_AT_220_1_1_freeze_copies_and_digests(self):
        R, p = self.fresh()
        src = self.heldout_dir(cases=5)
        porcelain = fx.git(R, "status", "--porcelain")
        rc, out, err = self.freeze(R, p, src, "FZ", "--json")
        self.assertEqual(rc, 0, out + err)
        obj = json.loads(out)
        ev = fx2.last_event(R, "heldout.freeze")
        self.assertEqual(list(ev), ["seq", "t", "kind", "by", "prop", "digest", "n", "frozen_by"])
        self.assertEqual((ev["by"], ev["frozen_by"], ev["n"], ev["prop"]), ("FZ", "FZ", 5, p))
        self.assertEqual(obj, {"ok": True, "kind": "heldout.freeze", "seq": ev["seq"], "id": None,
                               "prop": p, "n": 5, "digest8": ev["digest"].split(":")[1][:8]})
        dest = self.home / "heldout" / p
        self.assertEqual(fx2.snapshot_tree(dest), fx2.snapshot_tree(src))
        self.assertTrue((dest / "data" / "sample.txt").is_file())
        self.assertEqual(ev["digest"], fx2.manifest_raw(dest))
        self.assertEqual(fx.git(R, "status", "--porcelain"), porcelain)
        self.assertEqual(self.S(self.check(R), "events.transitions"), "PASS")
        # 案例數小於 min_heldout 仍可凍結
        R2, p2 = self.fresh()
        rc, out, err = self.freeze(R2, p2, self.heldout_dir(cases=4))
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(fx2.last_event(R2, "heldout.freeze")["n"], 4)
        R3, p3 = self.fresh()
        rc, out, err = self.freeze(R3, p3, self.heldout_dir())
        self.assertRegex(out, rf"^ok heldout.freeze seq=\d+ prop={p3} n=5 digest8=[0-9a-f]{{8}}\n$")

    def test_AT_220_1_E_1_freeze_rejections(self):
        def mutated(change):
            d = self.heldout_dir()
            m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
            change(d, m)
            (d / "manifest.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
            return d

        def probe0(key, value):
            def go(d, m):
                m["probes"][0][key] = value
            return go

        bad = {
            "缺": lambda d, m: (d / "manifest.json").unlink() or m.clear(),
            "多鍵": lambda d, m: m.update(extra=1),
            "schema_rev": lambda d, m: m.update(schema_rev=2),
            "argv0": lambda d, m: probe0("argv", ["python3", "x"])(d, m),
            "module": lambda d, m: probe0("module", "a-b")(d, m),
            "mutation 分隔": lambda d, m: m.update(mutation="sub/mutation.patch"),
            "mutation 不存在": lambda d, m: m.update(mutation="nope.patch"),
            "probes id 重複": lambda d, m: m["probes"].append(dict(m["probes"][0])),
        }
        for label, change in bad.items():
            with self.subTest(label):
                R, p = self.fresh()
                src = mutated(change)
                snap0 = fx.snap(R)
                rc, out, err = self.freeze(R, p, src)
                self.rejected(rc, out, {"HELDOUT-MANIFEST-INVALID"}, label)
                self.assertEqual(fx.snap(R), snap0)
                self.assertFalse((self.home / "heldout" / p).exists())
        R, p = self.fresh()
        rc, out, err = self.freeze(R, p, mutated(lambda d, m: m.update(cases=[])))
        self.rejected(rc, out, {"HELDOUT-EMPTY"})
        ghost = "OBS-SI-" + "9" * 3
        rc, out, err = self.freeze(R, p, mutated(
            lambda d, m: m.update(cases=[{"id": "c0", "ref": ghost}])))
        self.rejected(rc, out, {"HELDOUT-REF-UNRESOLVED"})
        rc, out, err = self.freeze(R, p, self.heldout_dir(), "SA")
        self.rejected(rc, out, {"FROZEN-BY-PROPOSER"})
        # --from 不存在：rc 3
        self.usage_error(*self.freeze(R, p, fx.new_dir("nonexistent")))
        # --from 在 <HOME>/heldout/ 之內
        inside = fx2.make_heldout(self.home / "heldout" / "elsewhere")
        rc, out, err = self.freeze(R, p, inside)
        self.rejected(rc, out, {"HELDOUT-FROM-INSIDE"})
        # 連結（以替身回報連結型條目；不得 skip）
        src = self.heldout_dir()
        (src / "link.txt").write_text("x", encoding="utf-8")
        from lib.selfimproving import heldout as si_heldout
        with mock.patch.object(si_heldout, "_is_link", lambda e: e.name == "link.txt"):
            rc, out, err = self.freeze(R, p, src)
        self.rejected(rc, out, {"HELDOUT-LINK"})
        self.assertFalse((self.home / "heldout" / p).exists())
        self.assertEqual([x.name for x in (self.home / "heldout").iterdir()], ["elsewhere"])
        # 首次成功、再凍結一次 → HELDOUT-EXISTS
        rc, out, err = self.freeze(R, p, self.heldout_dir())
        self.assertEqual(rc, 0, out + err)
        rc, out, err = self.freeze(R, p, self.heldout_dir())
        self.rejected(rc, out, {"HELDOUT-EXISTS"})
        # 已有 app.sandbox
        R2, p2 = self.fresh()
        pe = fx2.prop_event(R2, p2)
        fx.append_events(R2, [fx.ev("app.sandbox", "main", prop=p2, base=pe["base"])])
        rc, out, err = self.freeze(R2, p2, self.heldout_dir())
        self.rejected(rc, out, {"HELDOUT-AFTER-SANDBOX"})
        # handoff 路由與 rejected 態
        self.new_home()
        R3, p3 = fx2.template("carried-handoff", lambda r: fx2.drive_to(r, "carried",
                                                                       route="handoff:T1"))
        rc, out, err = self.freeze(R3, p3, self.heldout_dir())
        self.rejected(rc, out, {"ROUTE-HANDOFF"})
        self.new_home()
        R4, p4 = fx2.template("carried-rej", lambda r: _rejected(r))
        rc, out, err = self.freeze(R4, p4, self.heldout_dir())
        self.rejected(rc, out, {"PROP-STATE-ILLEGAL"})
        # 無人值守
        R5, p5 = self.fresh()
        before = (R5 / fx.EVL).read_bytes()
        with mock.patch.dict(os.environ, {"AUTOSDD_UNATTENDED": "1"}):
            rc, out, err = self.freeze(R5, p5, self.heldout_dir())
        self.rejected(rc, out, {"UNATTENDED-REFUSED"})
        self.assertEqual((R5 / fx.EVL).read_bytes(), before)


def _rejected(R):
    p = fx2.drive_to(R, "carried")
    assert fx2.decide_say(R, p, f"否決 {p} 證據座標不足", reason_class="證據不足")[0] == 0
    return p


def codes_set(res: dict, item: str) -> set[str]:
    return {c for _, c in {(f["subject"], f["code"]) for f in res["_item"][item]["findings"]}}


# AT-240-2-E-3 的 CLI 抽樣（§5.2 PARITY 的 16 格）：8 個 dkind 各一格接受、一格拒絕。
# （態, dkind, 未驗採納, 決定行, 理由類, 預期 rc）；態名與 `states` 格點同名，`{p}` 為 PROP 號。
CLI_SAMPLE = (
    ("proposed-loop", "approve", False, "核准 {p}", None, 0),
    ("proposed-handoff", "approve", False, "核准 {p}", None, 1),
    ("proposed-loop", "reject", False, "否決 {p} 證據座標不足", "證據不足", 0),
    ("approved", "reject", False, "不轉交 {p} 本迴圈不處理", "範圍外", 1),
    ("proposed-loop", "return", False, "退回 {p} 改用 M 類", "工件類別錯", 0),
    ("verified-ne-noprobes", "return", False, "退回 {p} 補探針", "範圍外", 1),
    ("proposed-handoff", "ack-handoff", False, "轉交 {p}", None, 0),
    ("proposed-loop", "ack-handoff", False, "轉交 {p}", None, 1),
    ("verified-pass", "decline-promote", False, "否決 {p} 風險太高", "風險過高", 0),
    ("approved", "decline-promote", False, "否決 {p} 風險太高", "風險過高", 1),
    ("rejected-cooling", "unblock", False, "解除 {p}", None, 0),
    ("rejected-unblocked", "unblock", False, "解除 {p}", None, 1),
    ("verified-pass", "promote", False, "晉升 {p}", None, 0),
    ("verified-pass", "promote", True, "晉升 {p} 未驗採納", None, 1),
    ("promoted", "rollback", False, "回滾 {p} 太慢", None, 0),
    ("verified-pass", "rollback", False, "回滾 {p} 太慢", None, 1),
)
_E3_SAY = {"approved": [("核准 {p}", None)],
           "rejected-cooling": [("否決 {p} 證據座標不足", "證據不足")],
           "rejected-unblocked": [("否決 {p} 證據座標不足", "證據不足"), ("解除 {p}", None)]}
_E3_HAND = {"verified-pass": ("verified", {}), "promoted": ("promoted", {}),
            "verified-ne-noprobes": ("verified", {"verdict": "NE"})}


def e3_state(state: str):
    """CLI 抽樣的態：建在真 repo 上（樣板複本，一態只建一次）；回 (repo, PROP 號)。"""
    def build(R):
        p = fx2.new_prop(R, route="handoff:T1" if state == "proposed-handoff" else "loop")
        fx2.issue_card(R, p)
        for quote, rcls in _E3_SAY.get(state, ()):
            rc, out, err, _, _ = fx2.decide_say(R, p, quote.format(p=p), reason_class=rcls)
            assert rc == 0, out + err
        if state in _E3_HAND:
            fx2.hand_to(R, p, _E3_HAND[state][0], **_E3_HAND[state][1])
        return p
    return fx2.template(f"e3-{state}", build)


def decs(R) -> list[dict]:
    return [e for e in fx.EV(R) if e["kind"] == "dec"]


class TestP2Checks(P2TestCase):
    # 受測面：tools/lib/selfimproving/sandbox.py（程式碼鎖，非散文）
    """AT-240-1-E-2、2-E-3、3-1、3-E-1、4-1、4-E-1、220-1-E-2、240-11、240-15。"""

    def test_AT_240_1_E_2_event_line_boundary(self):
        def ready():
            self.new_home()
            return fx2.template("carried", lambda r: fx2.drive_to(r, "carried"))

        def decide(R, p):
            return fx2.decide_say(R, p, f"否決 {p} 證據座標不足", reason_class="證據不足",
                                  issue=False)
        Rb, p = ready()
        before = len((Rb / fx.EVL).read_bytes().splitlines())
        self.assertEqual(decide(Rb, p)[0], 0)
        line = (Rb / fx.EVL).read_bytes().splitlines()[before]
        size = len(line)
        R, p = ready()
        fx.set_params(R, event_max_bytes=size)
        self.assertEqual(decide(R, p)[0], 0)
        seq = fx2.last_event(R, "dec")["seq"]
        res = self.check(R)
        self.assertNotIn((f"seq={seq}", "EVENT-BYTES-OVER"), self.F(res, "events.structure"))
        Rc, p = ready()
        fx.set_params(Rc, event_max_bytes=size - 1)
        ev0 = (Rc / fx.EVL).read_bytes()
        rc, out, _, _, _ = decide(Rc, p)
        self.rejected(rc, out, {"EVENT-BYTES-OVER"})
        self.assertEqual((Rc / fx.EVL).read_bytes(), ev0)
        fx.set_params(R, event_max_bytes=size - 1)
        res = self.check(R)
        self.assertEqual(self.S(res, "events.structure"), "FAIL")
        self.assertIn((f"seq={seq}", "EVENT-BYTES-OVER"), self.F(res, "events.structure"))

    def test_AT_240_2_E_3_decide_and_fold_agree(self):
        base = [fx.run_open_ev(1), fx.skip_ev(1)]
        n = 124
        states = {
            "proposed-loop": [fx.prop_ev(n, 1)],
            "proposed-handoff": [fx.prop_ev(n, 1, route="handoff:T1")],
            "approved": [fx.prop_ev(n, 1), fx.dec_ev(n, "approve")],
            "sandboxed": [fx.prop_ev(n, 1), fx.dec_ev(n, "approve"), fx.freeze_ev(n),
                          fx.sandbox_ev(n)],
            "verified-pass": fx2.verified_chain(n),
            "verified-ne-noprobes": fx2.verified_chain(n, "NE"),
            "verified-ne-touched": [fx.prop_ev(n, 1), fx.dec_ev(n, "approve"), fx.freeze_ev(n),
                                    fx.sandbox_ev(n, touched_ok=False),
                                    fx.verify_ev(n, "NE", reasons=["TOUCHED-SUPERSET"])],
            "verified-fail": fx2.verified_chain(n, "FAIL"),
            "verified-pass-rollback-false": fx2.verified_chain(n, rollback_ok=False),
            "verified-pass-touched-false": fx2.verified_chain(n, touched_ok=False),
            "rejected-cooling": [fx.prop_ev(n, 1), fx.dec_ev(n, "reject")],
            "rejected-unblocked": [fx.prop_ev(n, 1), fx.dec_ev(n, "reject"),
                                   fx.dec_ev(n, "unblock")],
            "promoted": fx2.promoted_chain(n),
        }
        forms = [("approve", []), ("reject", []), ("return", []), ("ack-handoff", []),
                 ("decline-promote", []), ("unblock", []), ("promote", []),
                 ("promote", ["unverified_ack"]), ("rollback", [])]
        from lib.selfimproving import decwrite
        allowed = {"PRECONDITION-STATE", "PRECONDITION-VERDICT", "ROUTE-HANDOFF", "NOT-IN-COOLDOWN",
                   "PROMOTE-FORM-MISMATCH", "PROMOTE-PREMISE-ROLLBACK", "PROMOTE-PREMISE-TOUCHED"}
        accepted = rejected = 0
        grid = {}
        for sname, chain in states.items():
            events = fx.compose([*base, *chain], HEAD)
            folded = si_fold.fold(si_events.sound(events))
            self.assertIn(pid(n), folded.props, sname)
            for dk, flags in forms:
                with self.subTest(f"{sname}/{dk}/{bool(flags)}"):
                    extra = {"flags": flags} if flags else {}
                    more = fx.compose([*base, *chain, fx.dec_ev(n, dk, **extra)], HEAD)
                    replay = si_fold.fold(si_events.sound(more))
                    illegal = any(c == "TRANSITION-ILLEGAL" for c, _, _ in replay.problems)
                    got = decwrite.preconditions(folded, pid(n), dk, flags)
                    grid[(sname, dk, bool(flags))] = got
                    self.assertEqual(illegal, bool(got), (sname, dk, got))
                    self.assertLessEqual(set(got), allowed, (sname, dk, got))
                    accepted += not got
                    rejected += bool(got)
        self.assertTrue(accepted >= 9 and rejected >= 9, (accepted, rejected))
        self.cli_sample(grid)

    def cli_sample(self, grid):
        """AT-240-2-E-3 (2)：抽樣 16 格以 CLI `decide`（PC-01 逐字稿）實呼叫；rc 與前提判定一致。"""
        from lib.selfimproving import decwrite
        cover: dict[str, set[bool]] = {}
        for state, dkind, ack, quote, rcls, want in CLI_SAMPLE:
            with self.subTest(f"{state}/{dkind}{'+ack' if ack else ''}/rc={want}"):
                R, p = e3_state(state)
                folded = si_fold.fold(si_events.sound(fx.EV(R)), 2)
                seam = decwrite.preconditions(folded, p, dkind, ["unverified_ack"] if ack else [])
                cover.setdefault(dkind, set()).add(bool(seam))
                self.assertEqual(seam, grid[(state, dkind, ack)])  # 真 repo 的態＝格點的態
                self.assertEqual(want, 1 if seam else 0, seam)
                fx2.cli(R, "card", p, "--issue")  # 卡面前提態內重發；他態拒收、沿用原卡
                before = decs(R)
                rc, out, err, _, _ = fx2.decide_say(R, p, quote.format(p=p), kind=dkind,
                                                    reason_class=rcls, issue=False)
                self.assertEqual(rc, want, out + err)
                if want:
                    self.rejected(rc, out, msg=out)
                    self.assertLessEqual(set(seam), fx.codes_of(out), out)
                    self.assertEqual(decs(R), before)  # rc 1：不記 DEC
                else:
                    self.assertEqual([(e["prop"], e["dkind"]) for e in decs(R)[len(before):]],
                                     [(p, dkind)])
        self.assertEqual(len(CLI_SAMPLE), 16)
        dkinds = ("approve", "reject", "return", "ack-handoff", "decline-promote", "unblock",
                  "promote", "rollback")
        self.assertEqual(cover, {dk: {True, False} for dk in dkinds})  # 每個 dkind 一接受一拒絕

    def test_AT_240_3_1_check_has_32_items(self):
        self.new_home()
        R0 = fx2.make_p2_repo(fx.new_dir("r0"))
        R1 = fx.new_dir("r1")
        import shutil
        shutil.copytree(R0, R1)
        rc, out, err = fx2.cli(R1, "run-open", "--trigger", "a", "--coord", "tools/a.py:1", "--by",
                               "main")
        self.assertEqual(rc, 0, out + err)
        fx.commit_all(R1, "events")
        cne = ["CARRIER-NOT-ESTABLISHED"]

        def items(R):
            return [(i["id"], i["status"], i["blocking"], sorted(f["code"] for f in i["findings"]))
                    for i in self.MJ(R, "check")["items"][:28]]

        from lib.selfimproving import check as si_check
        ids = list(si_check.ITEM_IDS[:28])
        ne0 = {14, 22, 23, 24, 25, 26, 27, 28}
        want0 = [(ids[k], "NE" if k + 1 in ne0 else "PASS", False,
                  cne if k + 1 in ne0 else []) for k in range(28)]
        want1 = [(ids[k], "NE" if k + 1 == 28 else "PASS", False,
                  cne if k + 1 == 28 else (["FAMILY-REF-DANGLING"] if k + 1 == 14 else []))
                 for k in range(28)]
        self.assertEqual(items(R0), want0)
        self.assertEqual(items(R1), want1)
        res0, res1 = self.check(R0), self.check(R1)
        self.assertEqual(self.M(R0, "check")[1].splitlines()[0], "si-check rows=10 items=33")
        self.assertEqual([i["id"] for i in res0["items"][28:32]],
                         ["events.dec_quote", "events.dec_console", "events.verdict",
                          "obs.console_audit"])
        for k in ("events.dec_quote", "events.dec_console", "events.verdict", "obs.console_audit"):
            self.assertEqual((self.S(res0, k), res0["_item"][k]["blocking"],
                              codes_set(res0, k)), ("NE", False, set(cne)))
            self.assertEqual(self.S(res1, k), "PASS")
        self.assertEqual((res0["overall"], res0["_rc"]), ("PASS", 0))
        self.assertEqual(self.MJ(R1, "check")["fingerprint_parts"]["check_rules_rev"], 4)

    def test_AT_240_3_E_1_new_items_fail_and_ne(self):
        def run_check(chain, rows=()):
            self.new_home()
            R = fx2.make_p2_repo(fx.new_dir("bk"), events=[fx.run_open_ev(1), fx.skip_ev(1),
                                                          *chain], extra_obs=rows)
            return self.check(R)

        def broken(label, chain, item, code, fixed, rows=()):
            """`chain` 使該項 FAIL 且帶 `code`；`fixed`（事件鏈，或回 check 結果的函式）＝同一情境
            改正後的合規對照，該項須為 PASS（只有那一個缺陷會讓它紅）。"""
            with self.subTest(label):
                res = run_check(chain, rows)
                self.assertEqual(self.S(res, item), "FAIL", self.F(res, item))
                self.assertIn(code, codes_set(res, item))
                ok = fixed() if callable(fixed) else run_check(fixed)
                self.assertEqual(self.S(ok, item), "PASS", self.F(ok, item))

        def console_ok(kind):  # 合規對照：同一情境走真實 CLI 入帳（列、事件、稽核檔同時成立）
            self.new_home()
            R = fx2.make_p2_repo(fx.new_dir("ok"))
            ref, target = fx2.new_uuid(), fx.obs_id(1)
            body = (fx2.body_obs_add(ref) if kind == "obs-add"
                    else fx2.body_obs_close(ref, target, "decided：夾具"))
            fx2.write_audit(self.home, kind=kind, ref=ref, body=body,
                            subject=None if kind == "obs-add" else target)
            with mock.patch.dict(os.environ, {"AUTOSDD_SI_AUDIT_KEY": fx2.AUDIT_KEY}):
                rc, out, err = self.M(R, kind, "--carrier", "console", "--audit-ref", ref)
                self.assertEqual(rc, 0, out + err)
                return self.check(R)
        head3 = [fx.prop_ev(124, 1), fx.dec_ev(124, "approve"), fx.freeze_ev(124)]
        pre = [*head3, fx.sandbox_ev(124)]
        ok_v = dict(probes_n=1, baseline_red=True, patched_green=True, mutated_red=True,
                    carrier_proof=True, verify_sha256=fx.H(9), heldout_digest=fx.H(7), reasons=[])
        broken("a", [*pre, fx.verify_ev(124, "PASS", **{**ok_v, "probes_n": 0,
                                                       "verify_sha256": None,
                                                       "baseline_red": None,
                                                       "patched_green": None,
                                                       "mutated_red": None,
                                                       "carrier_proof": None,
                                                       "heldout_digest": None})],
               "events.verdict", "VERDICT-MISMATCH", [*pre, fx.verify_ev(124, "NE")])
        # (b) 只剩 R98 (c)(ii)：⓪ 層兩碼同時成立而記錄只留第一碼——verdict 同為 NE、記錄碼
        # 無一不可導出（(i)(iii) 皆不觸發）。reasons 若給 []，違反 R72「空陣列 ⇔ PASS」，
        # 事件在 events.structure 即被排除而到不了 verdict 重算，故不能用空陣列隔離 (ii)。
        two = [*head3, fx.sandbox_ev(124, touched_ok=False, rollback_ok=False)]
        broken("b", [*two, fx.verify_ev(124, "NE", reasons=["TOUCHED-SUPERSET"])],
               "events.verdict", "VERDICT-MISMATCH",
               [*two, fx.verify_ev(124, "NE", reasons=["TOUCHED-SUPERSET",
                                                       "ROLLBACK-DRYRUN-FAILED"])])
        broken("c", [*pre, fx.verify_ev(124, "NE", **{**ok_v, "reasons": ["BASELINE-NOT-RED"]})],
               "events.verdict", "VERDICT-MISMATCH", [*pre, fx.verify_ev(124, "PASS", **ok_v)])
        nofit = [*head3, fx.sandbox_ev(124, applied=False)]
        broken("d", [*nofit, fx.verify_ev(124, "NE", **{
                   **ok_v, "probes_n": 2, "reasons": ["SANDBOX-NOT-APPLIED"]})],
               "events.verdict", "VERDICT-MISMATCH",
               [*nofit, fx.verify_ev(124, "NE", reasons=["SANDBOX-NOT-APPLIED"])])
        ref = fx2.new_uuid()
        row = [fx.obs_id(11), "2026-10-21 08:00 +08:00", "c", "s", "tools/a.py:1", "bug", "P3",
            "open",
               f"面=流程;來源=人;回報者=a;carrier=console;audit_ref={ref}"]
        broken("e", [], "obs.console_audit", "CONSOLE-EVENT-MISSING",
               lambda: console_ok("obs-add"), rows=[row])
        broken("f", [fx.obs_close_ev(obs=fx.obs_id(1), audit_ref=fx2.new_uuid())],
               "obs.console_audit", "CONSOLE-CLOSE-NOT-APPLIED", lambda: console_ok("obs-close"))
        sid = fx2.new_sid()
        helm = fx.skip_ev(2, reason="helmsman", sid=sid, line=1, note="x")
        decided = [fx.prop_ev(124, 1), fx.card_ev(124), fx.dec_ev(124, "approve")]

        def helmsman_check(records, *, with_dec=True):
            """(i)：帳本含 `dec` 與 helmsman 免掃；`records` 為 None＝逐字稿目錄不存在。"""
            self.new_home()
            R = fx2.make_p2_repo(fx.new_dir("hm"), events=[
                fx.run_open_ev(1), fx.skip_ev(1), *(decided if with_dec else []),
                fx.run_open_ev(2), helm])
            if records is not None:
                fx2.make_transcript(R, sid, records)
            return self.check(R)

        def no_p1_warn(res):
            for item in res["_item"].values():
                self.assertNotIn("QUOTE-VERIFIER-NOT-ESTABLISHED",
                    {f["code"] for f in item["findings"]})
        with self.subTest("g"):
            res = helmsman_check([fx2.rec_assistant_text("x", fx2.ts(0))])
            self.assertEqual(self.S(res, "events.research"), "FAIL")
            self.assertIn("HELMSMAN-REF-INVALID", codes_set(res, "events.research"))
            no_p1_warn(res)
            ok = helmsman_check([fx2.rec_user_human("掌舵者原話", fx2.ts(0))])  # 合規對照
            self.assertEqual(self.S(ok, "events.research"), "PASS", self.F(ok, "events.research"))
            no_p1_warn(ok)
        with self.subTest("h"):
            res = helmsman_check(None, with_dec=False)
            self.assertEqual((self.S(res, "events.research"), res["_item"]["events.research"][
                "blocking"]), ("NE", False))
            self.assertIn("TRANSCRIPT-UNAVAILABLE", codes_set(res, "events.research"))
            self.assertEqual(res["_rc"], 0)
        from lib.selfimproving.check import _NONBLOCKING as nb  # E-08：五碼皆 NE 不使 rc 為 2
        self.assertLessEqual({"CONSOLE-AUDIT-MISSING", "CONSOLE-KEY-MISSING", "ORIGIN-MISSING",
                              "TRANSCRIPT-UNAVAILABLE", "ATTACHMENT-TIME-UNKNOWN"}, nb)

    def test_AT_240_4_1_params_30_keys(self):
        self.new_home()
        R = fx2.p2_base()
        self.assertEqual(self.S(self.check(R), "params.keys"), "PASS")
        real = json.loads(fx.REAL_PARAMS.read_text(encoding="utf-8"))
        self.assertEqual((real["probe_timeout_seconds"], real["verify_runs_max"]), (600, 2))
        self.assertEqual(len(real), 32)
        p = fx2.drive_to(R, "sandboxed")
        fx.set_params(R, verify_runs_max=1)
        self.assertEqual(self.M(R, "verify", p)[0], 0)
        rc, out, _ = self.M(R, "verify", p)
        self.rejected(rc, out, {"VERIFY-RUNS-EXCEEDED"})

    def test_AT_240_4_E_1_new_keys_invalid(self):
        variants = [("probe_timeout_seconds", KeyError, "PARAM-MISSING"),
                    ("probe_timeout_seconds", 0, "PARAM-RANGE"),
                    ("probe_timeout_seconds", "600", "PARAM-TYPE"),
                    ("probe_timeout_seconds", True, "PARAM-TYPE"),
                    ("verify_runs_max", KeyError, "PARAM-MISSING"),
                    ("verify_runs_max", -1, "PARAM-RANGE")]
        self.new_home()
        R = fx2.p2_base()
        p = fx2.drive_to(R, "sandboxed")
        self.assertEqual(self.M(R, "verify", p)[0], 0)
        good = json.loads(fx.read(R, fx.PARAMS))
        for key, value, code in variants:
            with self.subTest(f"{key}={value}"):
                fx.put(R, fx.PARAMS, fx.dump_params(good))
                fx.set_params(R, **{key: value})
                res = self.check(R)
                self.assertEqual(self.S(res, "params.keys"), "FAIL")
                self.assertIn((key, code), self.F(res, "params.keys"))
                if key == "verify_runs_max":
                    self.assertEqual(self.S(res, "events.verdict"), "NE")
                    self.assertIn("SOURCE-UNAVAILABLE", codes_set(res, "events.verdict"))
                s0, e0 = fx.snap(R), (R / fx.EVL).read_bytes()
                for verb in (["verify", p],) + ((["sandbox", p],) if key == "probe_timeout_seconds"
                                                else ()):
                    rc, out, err = self.M(R, *verb)
                    self.usage_error(rc, out, err, str(verb))
                    self.assertIn(key, err)
                self.assertEqual((fx.snap(R), (R / fx.EVL).read_bytes()), (s0, e0))
        fx.put(R, fx.PARAMS, fx.dump_params(good))

    def test_AT_220_1_E_2_freeze_order(self):
        self.new_home()
        R = fx2.p2_base()
        p = fx2.drive_to(R, "approved")
        ev0 = (R / fx.EVL).read_bytes()
        rc, out, _ = self.M(R, "sandbox", p)
        self.rejected(rc, out, {"HELDOUT-NOT-FROZEN"})
        self.assertEqual((R / fx.EVL).read_bytes(), ev0)
        rc, out, err = fx2.cli(R, "heldout-freeze", p, "--from", fx2.make_heldout(fx.new_dir("ho")),
                               "--by", "FZ")
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(self.M(R, "sandbox", p)[0], 0)
        n = 124
        head = [fx.run_open_ev(1), fx.skip_ev(1), fx.prop_ev(n, 1), fx.dec_ev(n, "approve")]
        for code, chain in (
                ("HELDOUT-AFTER-SANDBOX", [fx.sandbox_ev(n), fx.freeze_ev(n)]),
                ("HELDOUT-DUP", [fx.freeze_ev(n), fx.freeze_ev(n)]),
                ("FROZEN-BY-PROPOSER", [fx.freeze_ev(n, by="SA", frozen_by="SA")])):
            with self.subTest(code):
                self.new_home()
                Rw = fx2.make_p2_repo(fx.new_dir("fz"), events=[*head, *chain])
                res = self.check(Rw)
                self.assertEqual(self.S(res, "events.transitions"), "FAIL")
                self.assertIn(code, codes_set(res, "events.transitions"))

    def _links(self, rows):
        self.new_home()
        return fx2.make_p2_repo(fx.new_dir("lk"), extra_obs=rows)

    def test_AT_240_11_1_families_resolve(self):
        self.new_home()
        R = fx2.p2_base()
        p = fx2.new_prop(R)
        ghost_p, ghost_r = "PROP-SI-" + "977", "RUN-SI-" + "978"
        rows = [[fx.obs_id(11), "2026-10-21 08:00 +08:00", "c", f"散文提及 {ghost_p} 與 {ghost_r}",
                 "tools/a.py:1", "bug", "P3", "open", "面=流程;來源=人;回報者=a"],
                [fx.obs_id(12), "2026-10-21 08:00 +08:00", "c", "已解析", "tools/a.py:1", "bug",
                "P3",
                 f"proposed@{p}", "面=流程;來源=人;回報者=a"],
                [fx.obs_id(13), "2026-10-21 08:00 +08:00", "c", "提及 DEC-SI-001", "tools/a.py:1",
                 "bug", "P3", "open", "面=流程;來源=人;回報者=a"]]
        text = fx.read(R, OBS_LEDGER_REL)
        lines = text.rstrip("\n").split("\n") + [fx.line(r) for r in rows]
        fx.put(R, OBS_LEDGER_REL, "\n".join(lines) + "\n")
        fx.put(R, "docs/01_requirements/spec_demo.md", f"規格提及 {ghost_p}\n")
        res = self.check(R)
        found = {s for s, c in self.F(res, "ref.carrier_families") if c == "FAMILY-REF-DANGLING"}
        self.assertEqual(found, {fx.obs_id(8)})
        self.assertNotIn("PROP-DIR-ORPHAN", codes_set(res, "ref.carrier_families"))
        self.assertEqual((self.S(res, "ref.carrier_families"), res["_rc"]), ("NE", 0))
        detail = next(f["detail"] for f in res["_item"]["ref.carrier_families"]["findings"]
                      if f["code"] == "CARRIER-NOT-ESTABLISHED")
        self.assertIn("families=DEC", detail)
        for fam in ("ATT", "PROP", "RUN"):
            self.assertNotIn(fam, detail.split("families=")[1].split()[0])
        fx.put(R, OBS_LEDGER_REL, fx.read(R, OBS_LEDGER_REL).replace("提及 DEC-SI-001", "提及別的"))
        self.assertEqual(self.S(self.check(R), "ref.carrier_families"), "PASS")

    def test_AT_240_11_E_1_families_dangling(self):
        ghost = "PROP-SI-" + "955"
        with self.subTest("a"):
            R, p = self.fresh_prop()
            row = [fx.obs_id(11), "2026-10-21 08:00 +08:00", "c", "s", "tools/a.py:1", "bug", "P3",
                   f"proposed@{ghost}", "面=流程;來源=人;回報者=a"]
            fx.put(R, OBS_LEDGER_REL, fx.read(R,
                OBS_LEDGER_REL).rstrip("\n") + "\n" + fx.line(row) + "\n")
            res = self.check(R)
            hits = [f for f in res["_item"]["ref.carrier_families"]["findings"]
                    if f["subject"] == fx.obs_id(11)]
            self.assertEqual([(h["code"], h["level"]) for h in hits], [("FAMILY-REF-DANGLING",
                "warn")])
            self.assertEqual(res["_rc"], 0)
        with self.subTest("b"):
            R, p = self.fresh_prop()
            fx.append_events(R, [fx.dec_ev(900, "approve"), fx.ev("attr.confirm", "QA",
                att=fx.aid(900)),
                                 fx.ev("research.skip", "main", run=fx.rid(900), reason="offline",
                                       note="x")])
            res = self.check(R)
            self.assertEqual(self.S(res, "ref.carrier_families"), "FAIL")
            self.assertEqual(len({s for s, c in self.F(res, "ref.carrier_families")
                                  if c == "FAMILY-REF-DANGLING" and s.startswith("seq=")}), 3)
            self.assertEqual(self.S(res, "events.transitions"), "FAIL")
        with self.subTest("c"):
            R, p = self.fresh_prop()
            (R / fx.PROPS_REL / ghost).mkdir()
            (R / fx.PROPS_REL / ghost / "r1.md").write_text("x", encoding="utf-8")
            res = self.check(R)
            self.assertEqual(self.S(res, "ref.carrier_families"), "FAIL")
            self.assertIn("PROP-DIR-ORPHAN", codes_set(res, "ref.carrier_families"))
        with self.subTest("real"):
            import subprocess
            import sys
            cp = subprocess.run([sys.executable, str(fx.TOOLS / "selfimproving.py"), "check",
                "--json"],
                                capture_output=True, text=True, encoding="utf-8", cwd=fx.ROOT,
                                env={**os.environ, "PYTHONUTF8": "1"})
            real = {i["id"]: i for i in json.loads(cp.stdout)["items"]}
            self.assertNotEqual(real["ref.carrier_families"]["status"], "FAIL")

    def fresh_prop(self):
        self.new_home()
        R = fx2.p2_base()
        return R, fx2.new_prop(R)

    def test_AT_240_15_1_deferred_and_closed_reopenable(self):
        coord = "docs/notes/demo.md:12"
        def row(n, disp):
            return [fx.obs_id(n), "2026-10-21 08:00 +08:00", "c", f"s{n}", coord, "bug",
                    "P3", disp, "面=流程;來源=人;回報者=a"]
        rows = [row(11, "deferred；再開症狀：甲"), row(12, "deferred；再開症狀：乙"),
                row(13, "deferred；再開症狀：丙"), row(14, "open"), row(15, "open"), row(16,
                "open")]
        R = self._links(rows)
        s0 = fx.snap(R)[0]
        n0 = len(fx.EV(R))
        atts = []
        for src, dst in ((14, 11), (15, 12), (16, 13), (14, 2)):
            rc, out, err = self.M(R, "attr", "--type", "link", "--by", "SA", "--from",
                                  fx.obs_id(src), "--reopens", fx.obs_id(dst))
            self.assertEqual(rc, 0, out + err)
            self.assertRegex(out, r"^ok attr seq=\d+ id=ATT-SI-\d{3,} type=link\n$")
            atts.append(fx2.last_event(R, "attr"))
        evs = fx.EV(R)[n0:]
        self.assertEqual(len(evs), 4)
        for e in evs:
            self.assertEqual(list(e), ["seq", "t", "kind", "by", "id", "type", "from", "reopens"])
        nums = [int(e["id"].rsplit("-", 1)[1]) for e in evs]
        self.assertEqual(nums, sorted(set(nums)))
        res = self.check(R)
        self.assertEqual((self.S(res, "events.structure"), self.S(res, "events.transitions")),
                         ("PASS", "PASS"))
        self.assertEqual(self.M(R, "attr-confirm", "--att", evs[0]["id"], "--by", "QA")[0], 0)
        self.assertEqual(self.MJ(R, "status")["reopen_candidates"]["unsettled"], 3)
        del s0

    def test_AT_240_15_E_1_reopens_rejections(self):
        coord = "docs/notes/demo.md:12"
        def row(n, disp):
            return [fx.obs_id(n), "2026-10-21 08:00 +08:00", "c", f"s{n}", coord, "bug",
                    "P3", disp, "面=流程;來源=人;回報者=a"]
        R = self._links([row(11, "open"), row(12, "deferred；再開症狀：甲"),
                         row(13, "fixed@" + "a" * 12)])
        fx.commit_all(R, "obs rows")
        fx.put(R, OBS_LEDGER_REL, fx.read(R, OBS_LEDGER_REL).rstrip("\n") + "\n"
               + fx.line(row(14, "open")) + "\n")
        s0 = fx.snap(R)
        cases = [(fx.obs_id(14), fx.obs_id(11), "REOPENS-NOT-CLOSED"),
                 (fx.obs_id(14), fx.obs_id(777), "REOPENS-NOT-FOUND"),
                 (fx.obs_id(14), fx.def_id(777), "REOPENS-NOT-FOUND"),
                 (fx.obs_id(778), fx.obs_id(12), "OBS-NOT-FOUND")]
        for src, dst, code in cases:
            with self.subTest(code + dst):
                rc, out, _ = self.M(R, "attr", "--type", "link", "--by", "SA", "--from", src,
                                    "--reopens", dst)
                self.rejected(rc, out, {code})
                self.draft_ok(R, out)
        self.assertEqual(fx.snap(R), s0)
        res = self.check(R)
        cand = [f["detail"] for f in res["_item"]["row.markers"]["findings"]
                if f["code"] == "REOPEN-CANDIDATE" and f["subject"] == fx.obs_id(14)]
        if cand:
            self.assertTrue(all(fx.obs_id(13) in d and fx.obs_id(12) not in d
                                and fx.obs_id(11) not in d for d in cand))

    def test_obs_si_261_export_names_the_unmeasurable_touched(self):
        """OBS-SI-261：patch 讀不到或解不開時，`export` 的 `touched` 為 null 且 `ne` 有該項。"""
        R = fx2.p2_base()
        p = fx2.new_prop(R)
        patch = R / fx.PROPS_REL / p / "r1.patch"
        field = f"proposals.{p}.touched"

        def seen():
            obj = self.MJ(R, "export", "--kind", "proposals")
            item = obj["items"][0]
            ne = [n for n in obj["ne"] if n["field"] == field]
            return item["touched"], item["touched_count"], ne
        self.assertEqual(seen(), ([fx2.DEMO], 1, []))
        patch.write_bytes(b"this is not a patch\n")
        self.assertEqual(seen(), (None, None, [{"field": field, "reason": "PATCH-INVALID"}]))
        patch.unlink()
        self.assertEqual(seen(), (None, None, [{"field": field, "reason": "PATCH-UNREADABLE"}]))


OBS_LEDGER_REL = "docs/06_quality/SelfImproving_Observation_Ledger.md"


if __name__ == "__main__":
    unittest.main()
