"""`tools/lib/quota_rush.py` 與 `tools/sessionctl.py rush` 的機械物
（TCS-TokenWaste-20261114 §10.4.5，AT-QP-41～55；AT-QP-69 的原語鎖也在此釘一份）。

縫：`now`（aware）注入、`AUTOSDD_TRACE_DIR` 指 tmp（戳記與痕跡落此，不寫真實 `~/.autosdd`）、
`env` mapping 注入。每條 AT 的 docstring 寫「為何會紅」。

執行：python -m unittest discover -s tools/tests -p test_quota_rush.py
"""
from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "tools" / "lib"))
import endurance_env as EE  # noqa: E402
import quota_burndown as B  # noqa: E402
import quota_gate as QG  # noqa: E402
import quota_pace_floor as PF  # noqa: E402
import quota_policy as Q  # noqa: E402
import quota_rush as R  # noqa: E402
import sentinel_lifecycle as SL  # noqa: E402

NOW = datetime(2026, 11, 15, 10, 0, 0, tzinfo=UTC)
WHY = "測試用趕工理由八字以上"
_FENCES: list[dict] = []


def setUpModule() -> None:  # 單模組直跑也不得碰真實 TEMP／快取目錄（同 test_quota_policy）
    _FENCES.append(SL.fence_enter())


def tearDownModule() -> None:
    SL.fence_exit(_FENCES.pop())


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="quota_rush_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.traces = self.tmp / "traces"
        patcher = mock.patch.dict(os.environ, {EE.TRACE_DIR_ENV: str(self.traces)})
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop(R.UNATTENDED_ENV, None)
        os.environ.pop(R.RUSH_KEY, None)
        self.stamp = R.stamp_path()
        self.events = self.traces / R.EVENTS_NAME

    def rows(self) -> list[dict]:
        if not self.events.is_file():
            return []
        return [json.loads(x) for x in self.events.read_text(encoding="utf-8").splitlines()]

    def good_stamp(self, **over) -> dict:
        data = {"schema": R.SCHEMA, "issued_at": NOW.isoformat(),
                "until": (NOW + timedelta(hours=1)).isoformat(),
                "until_epoch": (NOW + timedelta(hours=1)).timestamp(),
                "hours": 1.0, "why": WHY, "sid": "s"}
        data.update(over)
        return data

    def put(self, data) -> None:
        text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
        self.stamp.write_text(text, encoding="utf-8")


class IssueTest(_Base):
    def test_at_qp_41_issue_writes_a_complete_stamp_and_one_event(self):
        """戳記格式是讀取端 fail-closed 的對手；欄位缺漏讀取端會全當無效。"""
        rc, text = R.issue(1, WHY, sid="sid-1", now=NOW, env={})
        self.assertEqual(rc, 0, text)
        data = json.loads(self.stamp.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], R.SCHEMA)
        self.assertEqual(data["issued_at"], NOW.isoformat())
        self.assertEqual(data["until"], (NOW + timedelta(hours=1)).isoformat())
        self.assertEqual(data["until_epoch"], (NOW + timedelta(hours=1)).timestamp())
        self.assertEqual((data["hours"], data["why"], data["sid"]), (1.0, WHY, "sid-1"))
        self.assertEqual([r["event"] for r in self.rows()], ["pace_rush_on"])
        self.assertIsNotNone(R.read_stamp())

    def test_at_qp_42_hours_bounds_are_strict(self):
        """上限 5 小時是 §2.15 的安全邊界；`<=` 寫成 `<` 或上限放寬一格即紅。"""
        for hours in (0, -1, 5.01, float("nan"), "abc", float("inf")):
            with self.subTest(hours=hours):
                self.stamp.unlink(missing_ok=True)
                self.assertEqual(R.issue(hours, WHY, now=NOW, env={})[0], 2)
                self.assertFalse(self.stamp.exists())
        for hours in (5.0, 0.01, "2"):
            with self.subTest(hours=hours):
                self.assertEqual(R.issue(hours, WHY, now=NOW, env={})[0], 0)

    def test_at_qp_43_why_counts_characters_after_stripping_any_whitespace(self):
        """理由必填是戳記不淪為隨手關閉的唯一約束；全形空白不得灌水字數。"""
        cases = (("1234567", 2), ("12345678", 0), ("  1234567  ", 2),
                 ("　 12345678 　", 0), ("　" * 12, 2), ("", 2))
        for why, want in cases:
            with self.subTest(why=why):
                self.assertEqual(R.issue(1, why, now=NOW, env={})[0], want)

    def test_at_qp_44_unattended_window_cannot_declare_a_rush(self):
        """無人窗口無人可宣告趕工；放行＝夜間自動窗口可自我解除煞車。"""
        rc, text = R.issue(1, WHY, now=NOW, env={R.UNATTENDED_ENV: "1"})
        self.assertEqual(rc, 2)
        self.assertIn("無人", text)
        self.assertFalse(self.stamp.exists())

    def test_at_qp_49_reissue_replaces_the_old_stamp(self):
        """延長趕工＝重發；讀取端只認單一戳記。"""
        R.issue(1, WHY, now=NOW, env={})
        R.issue(2, WHY, now=NOW, env={})
        self.assertEqual(R.read_stamp()["hours"], 2.0)
        self.assertEqual([r["event"] for r in self.rows()], ["pace_rush_on", "pace_rush_on"])


class ReadActiveOverlayTest(_Base):
    def test_at_qp_45_every_structural_defect_reads_as_no_stamp(self):
        """每一種結構異常都必須 fail-closed（當無戳記＝床套用＝較緊）；任一種誤判有效＝放寬。"""
        self.put(self.good_stamp())
        live = R.active(NOW, env={})
        self.assertIsNotNone(live)
        self.assertEqual(int(live["left_minutes"]), 60)
        u = NOW + timedelta(hours=1)
        bad = {
            "until=now": self.good_stamp(until=NOW.isoformat(), until_epoch=NOW.timestamp()),
            "until=now-1s": self.good_stamp(until=(NOW - timedelta(seconds=1)).isoformat(),
                                            until_epoch=NOW.timestamp() - 1),
            "壞 JSON": "{not json",
            "缺欄": {k: v for k, v in self.good_stamp().items() if k != "why"},
            "schema 不符": self.good_stamp(schema="other/1"),
            "until naive": self.good_stamp(until=u.replace(tzinfo=None).isoformat()),
            "issued naive": self.good_stamp(issued_at=NOW.replace(tzinfo=None).isoformat()),
            "超過 5 小時": self.good_stamp(issued_at=(NOW - timedelta(hours=6)).isoformat()),
            "epoch 不一致": self.good_stamp(until_epoch=u.timestamp() + 120),
            "型別錯": self.good_stamp(hours="1"),
        }
        for name, data in bad.items():
            with self.subTest(defect=name):
                self.put(data)
                self.assertIsNone(R.active(NOW, env={}))
        self.put(self.good_stamp())
        self.assertIsNone(R.active(NOW, env={R.UNATTENDED_ENV: "1"}), "無人窗口一律忽略")

    def test_at_qp_46_overlay_adds_only_when_valid_and_never_overrides_or_raises(self):
        """`policy_env` 是所有 hook 的熱路徑，疊入失敗不得變故障源；
        覆蓋明示環境值＝吞掉操作者意圖。"""
        self.put(self.good_stamp())
        env = {"A": "1"}
        out = R.overlay(env, NOW)
        self.assertEqual(out[R.RUSH_KEY], str(self.good_stamp()["until_epoch"]))
        self.assertNotIn(R.RUSH_KEY, env, "原 mapping 不得被改")
        for blank in ("", "  ", "0", "-5"):
            with self.subTest(blank=blank):
                self.assertIn(R.RUSH_KEY, R.overlay({R.RUSH_KEY: blank}, NOW))
        explicit = {R.RUSH_KEY: "123456"}
        self.assertEqual(R.overlay(explicit, NOW), explicit, "已有正值不覆蓋")
        self.assertEqual(R.overlay({R.RUSH_KEY: "abc"}, NOW), {R.RUSH_KEY: "abc"})
        self.assertEqual(R.overlay(env, NOW + timedelta(hours=2)), env, "過期")
        self.assertEqual(R.overlay({R.UNATTENDED_ENV: "1"}, NOW), {R.UNATTENDED_ENV: "1"})
        self.stamp.unlink()
        self.assertEqual(R.overlay(env, NOW), env, "無戳記")
        self.stamp.mkdir()  # 不可讀（是目錄）：不拋
        self.assertEqual(R.overlay(env, NOW), env)

    def test_at_qp_47_stamp_reaches_policy_through_the_single_exit_and_revoke_restores(self):
        """端到端：戳記經 `policy_env()` 唯一出口抵達 `Policy`；少接一段就是「戳記寫了沒生效」。"""
        now = datetime.now().astimezone()
        rows = (Q.Axis("five_hour", 38.0, (now + timedelta(minutes=247)).isoformat()),
                Q.Axis("weekly_all", 30.0, (now + timedelta(minutes=8000)).isoformat()))
        state = Q.QuotaState(rows, now.isoformat(), "test")
        root = self.tmp / "root"
        root.mkdir()

        def band() -> tuple:
            policy, problems = Q.load_policy(QG.policy_env(root))
            self.assertEqual(problems, [])
            five = Q.decide(state, now, policy).per_axis[0]
            return policy.pace_rush_until, five.band

        self.assertEqual(band(), (None, "converge"), "控制組：無戳記，床套用")
        self.assertEqual(R.issue(1, WHY, now=now, env={})[0], 0)
        until, rushed_band = band()
        self.assertEqual(until, R.read_stamp()["until_epoch"])
        self.assertEqual(rushed_band, "free", "戳記生效：床暫停")
        self.assertEqual(R.revoke(now)[0], 0)
        self.assertEqual(band(), (None, "converge"), "撤銷後床恢復")


class ReviewP3HardeningTest(_Base):
    """安全審查 P3-1～P3-4：讀取端對「規格說無效」的輸入也一律視為無趕工。"""

    def test_p3_1_unattended_window_ignores_the_env_carrier_too(self):
        """規格「趕工戳記在無人窗口無效」不分載體：手設 `RUSH_KEY` 若在無人窗口仍生效，夜間窗口
        的環境（`.env`／排程）就能自我解除煞車；`overlay` 不移除該鍵即紅。"""
        until = str(NOW.timestamp() + 3600)
        env = {R.UNATTENDED_ENV: "1", R.RUSH_KEY: until}
        self.assertNotIn(R.RUSH_KEY, R.overlay(env, NOW))
        policy, _problems = Q.load_policy(R.overlay(env, NOW))
        self.assertIsNone(policy.pace_rush_until)
        self.assertEqual(env[R.RUSH_KEY], until, "原 mapping 不得被改")
        self.assertIn(R.RUSH_KEY, R.overlay({R.RUSH_KEY: until}, NOW), "有人窗口的明示值照舊")

    def test_p3_2_reader_requires_the_same_why_floor_as_the_writer(self):
        """寫入端拒絕短 WHY，讀取端卻收手寫戳記＝可稽核性只剩一半；讀取端少了下限即紅。"""
        for why in ("x", "1234567", "　" * 12, "  1234567  "):
            with self.subTest(why=why):
                self.put(self.good_stamp(why=why))
                self.assertIsNone(R.read_stamp())
                self.assertIsNone(R.active(NOW, env={}))
        self.put(self.good_stamp(why="12345678"))
        self.assertIsNotNone(R.active(NOW, env={}))

    def test_p3_3_reader_looks_only_where_the_writer_would_write(self):
        """健康的主居所不併讀系統暫存（暫存人人可寫）；寫入端退回暫存時兩端才一起落在暫存。
        讀取端寫死「兩處都找」＝第一個斷言紅；只看主居所＝第二個斷言紅。"""
        temp_stamp = Path(tempfile.gettempdir()) / R.STAMP_NAME
        self.addCleanup(temp_stamp.unlink, missing_ok=True)
        temp_stamp.write_text(json.dumps(self.good_stamp()), encoding="utf-8")
        self.assertEqual(EE.trace_dir_peek(), (self.traces, False))
        self.assertIsNone(R.read_stamp(), "主居所健康＝暫存裡的戳記不採信")
        blocker = self.tmp / "afile"
        blocker.write_text("x", encoding="utf-8")
        with mock.patch.dict(os.environ, {EE.TRACE_DIR_ENV: str(blocker / "sub")}):
            self.assertEqual(EE.trace_dir_peek()[1], True)
            self.assertEqual(EE.trace_dir_status()[1], True, "寫入端同樣退化（兩端同一判準）")
            self.assertIsNotNone(R.read_stamp(), "主居所不可用＝讀寫兩端都落在暫存")
            temp_stamp.unlink()
            self.assertEqual(R.issue(1, WHY, now=NOW, env={})[0], 0)
            self.assertTrue(temp_stamp.is_file(), "前提：寫入端確實退回暫存")
            self.assertIsNotNone(R.read_stamp())

    def test_p3_4_decision_pace_carries_the_burndown_hold(self):
        """清倉授權 hold 某軸時實際餵入水位未被床抬；`Decision.pace` 若仍報 `lifted`，
        gate 會落一列沒真的抬水位的 `pace_floor`（M-P4 撤回判定的分子灌水）。"""
        week = (NOW + timedelta(minutes=7663)).isoformat()
        five = (NOW + timedelta(minutes=233)).isoformat()
        state = Q.QuotaState((Q.Axis("session", 60.0, five), Q.Axis("weekly_all", 75.0, week),
                              Q.Axis("five_hour", 60.0, five), Q.Axis("seven_day", 75.0, week)),
                             NOW.isoformat(), "cache")
        burn = B.Burn("0123456789", NOW.isoformat(), "weekly_all",
                      (NOW + timedelta(minutes=7663)).isoformat(), 7663.0, week)
        plain = Q.decide(state, NOW, Q.DEFAULT_POLICY, 5.0, "n=67")
        held = Q.decide(state, NOW, Q.DEFAULT_POLICY, 5.0, "n=67", burndown=burn)
        self.assertIn("lifted", {f.state for f in plain.pace}, "前提：無授權時床真的抬")
        self.assertNotIn("lifted", {f.state for f in held.pace})
        self.assertIn("exempt-hold", {f.state for f in held.pace})
        self.assertFalse(R.log_floor(held, NOW), "hold 軸沒被床抬 ⇒ 不落 pace_floor 列")


class ReadSideCreatesNothingTest(_Base):
    def test_read_paths_never_create_the_trace_directory(self):
        """`policy_env()` 在 `--check`／`--pace` 這類唯讀查詢的熱路徑上：讀取端若走會 mkdir 的
        `trace_dir()`，沒人寫過戳記的機器 HOME 底下會憑空長出 `.autosdd/traces`
        （`PlannerCliTest.test_check_prints_usage_and_writes_nothing` 抓到的事故形態）。"""
        ghost = self.tmp / "never_created"
        with mock.patch.dict(os.environ, {EE.TRACE_DIR_ENV: str(ghost)}):
            self.assertIsNone(R.read_stamp())
            self.assertIsNone(R.active(NOW, env={}))
            self.assertEqual(R.overlay({"A": "1"}, NOW), {"A": "1"})
            self.assertEqual(R.revoke(NOW), (0, "無趕工戳記"))
            self.assertIn("無趕工戳記", R.status_text(NOW, env={}))
            self.assertFalse(ghost.exists())


class RevokeStatusCliTest(_Base):
    def test_at_qp_48_revoke_logs_only_a_real_revocation(self):
        """M-P7 的 off 事件只能是真撤銷；無檔也寫事件會稀釋指標。"""
        self.assertEqual(R.revoke(NOW), (0, "無趕工戳記"))
        self.assertEqual(self.rows(), [])
        R.issue(1, WHY, now=NOW, env={})
        self.assertEqual(R.revoke(NOW)[0], 0)
        self.assertFalse(self.stamp.exists())
        self.assertEqual([r["event"] for r in self.rows()], ["pace_rush_on", "pace_rush_off"])
        self.assertEqual(self.rows()[-1]["reason"], "revoked")

    def _cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = R.cli(list(argv))
        return rc, out.getvalue(), err.getvalue()

    def test_at_qp_50_cli_contract_separates_usage_errors_from_refusals(self):
        """rc 契約是呼叫端（主控）判斷成敗的依據；用法錯誤（3）與拒絕（2）要分得開。"""
        rc, out, _ = self._cli("--status")
        self.assertEqual(rc, 0)
        self.assertIn("無趕工戳記", out)
        rc, out, _ = self._cli("--hours", "1", "--why", WHY, "--sid", "sid-x")
        self.assertEqual(rc, 0, out)
        rc, out, _ = self._cli("--status")
        self.assertEqual(rc, 0)
        for part in ("到期", "分鐘", WHY):
            self.assertIn(part, out)
        self.assertEqual(self._cli("--off")[0], 0)
        for argv in ((), ("--hours", "1"), ("--off", "--hours", "1", "--why", WHY),
                     ("--bogus",), ("--why", WHY), ("--status", "--off"),
                     ("--hours",)):
            with self.subTest(argv=argv):
                self.assertEqual(self._cli(*argv)[0], 3)
        self.assertEqual(self._cli("--hours", "abc", "--why", WHY)[0], 2)
        self.assertEqual(self._cli("--hours", "9", "--why", WHY)[0], 2)

    def test_at_qp_51_sessionctl_shell_dispatches_rush(self):
        """薄殼分派真的接上；漏接＝文件宣稱有、命令列沒有。"""
        env = {k: v for k, v in os.environ.items() if k != R.UNATTENDED_ENV}
        env["PYTHONUTF8"] = "1"
        script = str(_REPO / "tools" / "sessionctl.py")

        def run(*args):
            return subprocess.run([sys.executable, script, *args], env=env, text=True,
                                  encoding="utf-8", capture_output=True, timeout=60, check=False)

        done = run("rush", "--hours", "1", "--why", WHY)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("到期", done.stdout)
        self.assertTrue(self.stamp.is_file())
        bogus = run("nonsense")
        self.assertEqual(bogus.returncode, 3)
        self.assertIn("rush", bogus.stderr)


class FloorLogTest(_Base):
    @staticmethod
    def _decision(*states, cap=2, band="converge"):
        floors = tuple(PF.PaceFloor("five_hour", 38.0, 247.0, 300.0, 37.7, 0.3,
                                    70.0 if s == "lifted" else None, s) for s in states)
        return SimpleNamespace(pace=floors, cap=cap, band=band)

    def test_at_qp_52_only_a_lifted_floor_is_logged(self):
        """M-P4 撤回條件的分子；不在 lifted 時寫＝分子灌水。"""
        for states, want in ((("lifted",), 1), (("within",), 0), (("exempt-rush",), 0),
                             (("exempt-weekly-reset", "unknown"), 0), (("lifted", "lifted"), 1)):
            with self.subTest(states=states):
                self.events.unlink(missing_ok=True)
                self.assertEqual(R.log_floor(self._decision(*states), NOW), bool(want))
                self.assertEqual(len(self.rows()), want)
        row = self.rows()[-1]
        for key in ("at", "kind", "pct", "minutes", "allowed_pp", "level", "cap", "band"):
            self.assertIn(key, row)
        self.assertEqual(row["event"], "pace_floor")
        directory = self.tmp / "adir"
        directory.mkdir()
        self.assertFalse(R.log_floor(self._decision("lifted"), NOW, path=directory))
        self.assertFalse(R.log_floor(SimpleNamespace(), NOW), "畸形 decision 不拋")

    def test_at_qp_54_event_file_is_single_line_json_inside_the_fence(self):
        """測試不得污染開發機真實痕跡（本 repo 的圍籬慣例）；一列一行、不轉義中文、LF 結尾。"""
        R.issue(1, WHY, now=NOW, env={})
        R.log_floor(self._decision("lifted"), NOW)
        raw = self.events.read_bytes()
        self.assertTrue(raw.endswith(b"\n"))
        self.assertNotIn(b"\r", raw)
        self.assertIn(WHY.encode("utf-8"), raw, "ensure_ascii=False")
        for line in raw.decode("utf-8").splitlines():
            json.loads(line)
        self.assertEqual(self.events.parent, self.traces)


class GateWiringTest(_Base):
    """AT-QP-53：落款點只在派發邊緣（PostToolUse 對每個工具都判，若也落款會寫出數千列）。"""

    def setUp(self) -> None:
        super().setUp()
        for name, value in {"quota_cache_path": lambda: self.tmp / "c.json",
                            "fanout_ledger_path": lambda: self.tmp / "l.d",
                            "quota_latch_path": lambda: self.tmp / "latch.json",
                            "quota_trace_path": lambda: self.tmp / "trace.jsonl",
                            "degraded_stamp_path": lambda source: self.tmp / f"stamp-{source}"
                            }.items():
            patcher = mock.patch.object(QG, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(QG.quota_env_layers, "merged_file_env", lambda _b: {})
        patcher.start()
        self.addCleanup(patcher.stop)

    def _cache(self, five_hour_pct: float) -> None:
        now = datetime.now().astimezone()
        reset = (now + timedelta(minutes=247)).isoformat()
        self.cache = {"schema": QG.quota_schema(),
                      "measured_at": (now - timedelta(seconds=10)).isoformat(),
                      "axes": [{"kind": "five_hour", "pct": five_hour_pct, "resets_at": reset},
                               {"kind": "session", "pct": five_hour_pct, "resets_at": reset},
                               {"kind": "weekly_all", "pct": 30.0,
                                "resets_at": (now + timedelta(minutes=8000)).isoformat()}]}
        (self.tmp / "c.json").write_text(json.dumps(self.cache), encoding="utf-8")

    def _gate(self, event: str, tool: str) -> int:
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            rc = QG.quota_gate({"hook_event_name": event, "tool_name": tool,
                                "transcript_path": ""}, blocking=("Agent",),
                               latch_read=lambda _p: set(), latch_write=lambda _p, _k: None,
                               plan_writer=lambda *_a, **_k: "", waker=lambda *_a, **_k: {},
                               event=event)
            QG.flush_to_model()
        return rc

    def test_at_qp_53_only_the_dispatch_edge_logs_a_floor_row(self):
        self._cache(38.0)
        self._gate("PostToolUse", "Read")
        self.assertEqual(self.rows(), [], "PostToolUse 不落款")
        self._gate("PreToolUse", "Agent")
        self.assertEqual([r["event"] for r in self.rows()], ["pace_floor"])
        self._cache(10.0)  # 允許線內：床未抬
        self.events.unlink()
        self._gate("PreToolUse", "Agent")
        self.assertEqual(self.rows(), [])


class StaticLocksTest(unittest.TestCase):
    def test_at_qp_55_load_policy_sites_are_pinned(self):
        """戳記只經 `policy_env()` 進場；新站點若自建 env 就看不到戳記（同一件事兩個數）。
        只准縮不准長：新增站點即紅，必須先在這裡登記並說明為何不走 `policy_env()`。"""
        pinned = {  # path -> (policy_env 站點數, 直接餵 env 的站點數)；直接站點的 WHY 見行尾
            "tools/lib/quota_gate.py": (3, 1),       # 1050：gate 已先取 env 變數＝policy_env()
            "tools/lib/quota_escalation.py": (1, 0),
            "tools/lib/quota_boot_check.py": (1, 0),
            "tools/lib/relay_machine.py": (1, 0),
            "tools/lib/resume_route.py": (1, 0),
            "tools/lib/session_brief.py": (2, 0),
            "tools/lib/sessionctl/park.py": (1, 0),
            "tools/lib/sessionctl/park_reset.py": (1, 0),  # R218 Q3：park 取 reset 的政策站點（自 park_cli 搬出）
            "tools/lib/sessionctl/qw_plan.py": (0, 1),  # R218 Q1：只讀 prepare_pct（戳記只墊高水位、不動門檻值）
            "tools/lib/wastecensus/resume.py": (1, 0),
            "tools/lib/wastecensus/pace_replay.py": (1, 0),  # R217 A7：回放經 policy_env
            "tools/lib/quota_burndown.py": (0, 1),   # env 由 gate 傳入（policy_env 的產物）
            "tools/lib/quota_env_layers.py": (0, 1),  # doctor：檢查檔層，刻意不疊戳記
            "tools/probe/day_long_relay_sim.py": (0, 1),   # 模擬器：固定預設政策
            "tools/probe/pacing_simulator.py": (0, 1),
            "tools/probe/zero_token_patrol_sim.py": (0, 1),
        }
        found: dict[str, list[int]] = {}
        roots = [_REPO / "tools", _REPO / ".claude" / "hooks"]
        for root in roots:
            for path in sorted(root.rglob("*.py")):
                rel = path.relative_to(_REPO).as_posix()
                if rel.startswith("tools/tests/"):
                    continue
                try:
                    tree = ast.parse(path.read_text(encoding="utf-8"))
                except (SyntaxError, UnicodeDecodeError):
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        name = getattr(node.func, "attr", getattr(node.func, "id", ""))
                        if name == "load_policy":
                            via = "policy_env" in ast.unparse(node.args[0]) if node.args else False
                            found.setdefault(rel, [0, 0])[0 if via else 1] += 1
        got = {k: tuple(v) for k, v in found.items()}
        self.assertEqual(got, pinned)

    def test_at_qp_69_stamp_module_uses_no_dir_entry_mutating_primitive(self):
        """Windows 檔案鎖原語鎖：`os.replace`／`rename` 覆寫被開著的目的檔 → WinError 5。"""
        tree = ast.parse((_REPO / "tools" / "lib" / "quota_rush.py").read_text(encoding="utf-8"))
        pairs = {(getattr(n.value, "id", ""), n.attr) for n in ast.walk(tree)
                 if isinstance(n, ast.Attribute)}
        attrs = {attr for _owner, attr in pairs}
        self.assertEqual({("os", "replace"), ("os", "rename"), ("shutil", "move")} & pairs, set())
        self.assertNotIn("rename", attrs)

    def test_at_qp_67_only_the_rush_module_writes_stamp_or_trace(self):
        """寫戳記與痕跡的呼叫只准出現在 `quota_rush.py`（判準檔 `quota_pace_floor` 純函式）。"""
        src = (_REPO / "tools" / "lib" / "quota_pace_floor.py").read_text(encoding="utf-8")
        fs = [n.func for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Call)]
        self.assertFalse({ast.unparse(f).split(".")[-1] for f in fs} & {"write_text", "open"})
        rush = (_REPO / "tools" / "lib" / "quota_rush.py").read_text(encoding="utf-8")
        self.assertIn("write_text", rush)


if __name__ == "__main__":
    unittest.main()
