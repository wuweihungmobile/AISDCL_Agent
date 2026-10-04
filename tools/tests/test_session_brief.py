#!/usr/bin/env python3
"""`tools/lib/session_brief.py` 的回歸鎖（R158／P6：四象限——額度〈有／無快取〉× round-label-ok
context〈有／無 usage〉，量不到就照實說；ctx5 輪另補 G1（statusLine 安裝狀態三格＋
feed reason 兩格）與 G2（stale-cache 追加文案兩格）。接線面另見
`test_context_budget_guard.py::HandbackSessionStartAnnounceTest`。
另收 `tools/session_gate_acceptance.py`（單一指令驗收）的回歸鎖：它只重用簡報的函式，
且 `tools/tests` 檔數壓線，故併在本檔而不另開新檔。"""
from __future__ import annotations

import contextlib
import fnmatch
import io
import json
import os
import re
import shutil
import sys
import tempfile
import types
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
import quota_gate  # noqa: E402
import quota_messages as qm  # noqa: E402
import quota_policy  # noqa: E402
import session_brief as sb  # noqa: E402
import unattended_authz  # noqa: E402

_NOW = datetime(2026, 9, 20, 1, 0, 0, tzinfo=UTC)
#: 簡報給的安裝指令形狀：POSIX `"<直譯器>" "<腳本>"`、Windows `& '<直譯器>' '<腳本>'`
#: （兩 token 都是引號包住的絕對路徑；PowerShell 用單引號＝字面，內嵌單引號寫成兩個）。
_PASTEABLE = re.compile(
    r"^(?:& '((?:[^']|'')+)' '((?:[^']|'')+)'|\"([^\"]+)\" \"([^\"]+)\")$")
_FSM_YAML = "fsm_state:\n  current_state: SPEC_DRAFTING\n  current_sprint: 1\n"


def _fsm_tree(case: unittest.TestCase, body: str, project: str = "AISDLC_SDD"):
    """假 repo 根：版本 0.99 的 `build/reports/fsm/FSM-STATE-<project>.yaml`。"""
    root = Path(tempfile.mkdtemp(prefix="sdd-fsm-"))
    case.addCleanup(shutil.rmtree, root, True)
    fsm = root / "AISDLC_SDD" / "AISDLC_SDD_v0.99" / "build" / "reports" / "fsm"
    fsm.mkdir(parents=True)
    (fsm / f"FSM-STATE-{project}.yaml").write_text(body, encoding="utf-8")
    return root, fsm / f"FSM-STATE-{project}.yaml"


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


def _scoped_state() -> quota_policy.QuotaState:
    """DEF-200-432：與真機 `--pace` 同形的新鮮讀數（Fable 分軌軸 `weekly_scoped` 已進收緊帶）。"""
    def iso(minutes: int) -> str:
        return (_NOW + timedelta(minutes=minutes)).isoformat()
    axes = (quota_policy.Axis("five_hour", 12.0, iso(200)),
            quota_policy.Axis("seven_day", 50.0, iso(4864)),
            quota_policy.Axis("weekly_scoped", 86.0, iso(4864), scope_model="Fable"))
    return quota_policy.QuotaState(axes, _NOW.isoformat(), "cache", "ok")


_VERDICT = re.compile(r"⇒ cap=(\S+) recommended=(\S+) band=(\S+) binding=(\S+)")


def _verdict(text: str) -> tuple[str, ...]:
    """額度行的判定四欄 `(cap, recommended, band, binding)`；找不到回 `()`（斷言端會紅）。"""
    m = _VERDICT.search(text)
    return m.groups() if m else ()


def _decided(active_model: str | None) -> tuple[str, ...]:
    """期望值：對同一份讀數跑真的 `decide()`，取同一組四欄——不在測試裡重寫判準。"""
    policy, _problems = quota_policy.load_policy({})
    d = quota_policy.decide(_scoped_state(), _NOW, policy, active_model=active_model)
    return (str(d.cap), str(d.recommended_fanout), d.band, d.binding.kind if d.binding else "-")


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


class UnmeasuredLineCaveatTest(unittest.TestCase):
    """每一種「量不到」的 reason，額度行都要附退化政策值附註（此前只有 `stale-cache` 附）。

    狀態一律由真的 `quota_gate.read_quota()` 對合成快取檔產出（不手寫 reason 字串），判準是
    `band == unmeasured`，不是列舉 reason——新增第六種量不到的原因也不得變成裸 `cap=2`。
    史料見本輪證據檔〈九〉。
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="brief-unmeasured-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        patcher = mock.patch.dict(os.environ, {"AUTOSDD_QUOTA_CACHE_DIR": str(self.tmp)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.cache = self.tmp / "cache.json"

    def _line(self, body: object | None) -> str:
        if body is not None:
            self.cache.write_text(json.dumps(body), encoding="utf-8")
        gate = _fake_quota_gate(read_quota=lambda now, path=None: quota_gate.read_quota(
            now, self.cache))
        return sb.quota_line(gate, _NOW)

    def _fresh(self, **overrides: object) -> dict:
        resets = (_NOW + timedelta(hours=2)).isoformat()
        axis = {"kind": "session", "pct": 40.0, "resets_at": resets}
        body = {"schema": quota_gate.quota_schema(), "source": "endpoint",
                "measured_at": (_NOW - timedelta(seconds=10)).isoformat(), "axes": [axis]}
        return {**body, **overrides}

    def test_every_unmeasured_reason_carries_the_caveat(self) -> None:
        stale = self._fresh(measured_at=(_NOW - timedelta(hours=6)).isoformat())
        dead = self._fresh(axes=[{"kind": "session", "pct": 40.0,
                                  "resets_at": (_NOW - timedelta(seconds=30)).isoformat()}])
        cases = (("no-cache", None), ("bad-cache", []), ("schema-mismatch", {"schema": "bogus"}),
                 ("stale-cache", stale), ("expired-window", dead))
        for reason, body in cases:
            with self.subTest(reason):
                got = self._line(body)
                self.assertIn(f"reason={reason}", got, "夾具沒有產出預期的 reason")
                self.assertIn("band=unmeasured", got)
                for fragment in ("退化政策值，不是量測值", "PreToolUse 會自動補量一次、零 token",
                                 "python tools/session_resume_planner.py --pace"):
                    self.assertIn(fragment, got)

    def test_only_a_stale_cache_is_called_stale(self) -> None:
        """附註不得對非陳舊的原因說「陳舊快取」——量不到的原因要求 operator 做的事各不相同。"""
        self.assertNotIn("陳舊快取", self._line(None))
        stale = self._fresh(measured_at=(_NOW - timedelta(hours=6)).isoformat())
        self.assertIn("陳舊快取的退化政策值", self._line(stale))

    def test_the_criterion_is_the_band_not_a_list_of_reason_strings(self) -> None:
        """一個從未見過的 reason 字面照樣附註（改成逐字列舉 reason 必紅）。"""
        invented = quota_policy.QuotaState((), "", "future-source", "future-reason-xyz")
        gate = _fake_quota_gate(read_quota=lambda now, path=None: invented)
        got = sb.quota_line(gate, _NOW)
        self.assertIn("reason=future-reason-xyz", got)
        self.assertIn("退化政策值，不是量測值", got)

    def test_a_usable_cache_gets_no_caveat(self) -> None:
        got = self._line(self._fresh())
        self.assertIn("kind=session", got)
        self.assertNotIn("退化政策值", got, "量得到的讀數不得被貼上退化警語")


class Rc2ClarifyTest(unittest.TestCase):
    """DEF-200-412：rc=2 澄清句平台感知——Windows 版換 PowerShell、點破
    『被擋≠不能寫檔』這個誤讀。

    WHY：POSIX 版原句「…Read／Write／Edit／Bash／git…不受影響」在 Windows 上對
    模型是假話——`block_bash_on_windows.py`（鐵律一）對 Bash 工具整支 exit 2。
    新視窗的模型會先被這句安撫「Bash 沒事」，下一步撞牆後又把「Bash 被擋」誤讀成
    「寫檔被擋」（掌舵者 Q1 原話：「才開新視窗，就說他被擋不能寫檔案用工具了」）。
    """

    def test_windows_variant_teaches_powershell_not_bash(self) -> None:
        got = sb.rc2_clarify(windows=True)
        self.assertIn("PowerShell", got)
        self.assertIn("lint 擋下", got)
        self.assertIn("見本簡報開頭", got, "Bash 停用與照常可用的工具已前移到簡報第一句")
        self.assertNotIn("／Bash／", got, "Windows 版不該再教 Bash 這個已被停用的載具")
        self.assertNotIn("不能寫檔", got, "句中引述症狀字面＝預示症狀（DEF-200-476）")

    def test_posix_variant_is_the_pause_half_plus_the_single_clause(self) -> None:
        got = sb.rc2_clarify(windows=False)
        self.assertTrue(got.startswith(sb._RC2_PAUSE), got)
        self.assertIn(qm.convergent_tools_clause(False) + "。", got)
        self.assertNotIn("PowerShell", got, "POSIX 版不該提 Windows 的載具")

    def test_the_pause_half_names_the_guard_not_every_hook(self) -> None:
        """Windows 的 Bash 阻斷與 lint 阻斷同為 rc=2：泛稱「hook 的 rc=2 只代表扇出暫停」會與
        同段的 Windows 尾句牴觸（SD-195-01）。"""
        for windows in (False, True):
            got = sb.rc2_clarify(windows=windows)
            self.assertTrue(got.startswith("額度／水位守衛（context_budget_guard）的 rc=2"), got)
            self.assertNotIn("hook 的 rc=2", got)

    def test_the_windows_halt_note_lists_what_works_without_quoting_the_symptom(self) -> None:
        """清單只住 `convergent_tools_clause()` 一份（單一導出）；Windows 註記只回指它，
        不抄第二份。"""
        for event in ("PostToolUse", "PreToolUse"):
            got = qm.halt_convergent_clarification(windows=True, event=event, tool="Agent")
            self.assertIn(qm.convergent_tools_clause(True), got)
            self.assertIn("其餘工具照常可用", got)
            self.assertEqual(got.count("Read／Write／Edit"), 1, "工具清單在同一則訊息出現兩次")
            self.assertNotIn("不能寫檔", got, "句中引述症狀字面＝預示症狀（DEF-200-476）")


class VerifyHintTest(unittest.TestCase):
    """SA-01：簡報教兩條現查指令時一併教安全形態。新視窗 2/2 的首個工具呼叫寫
    `--pace 2>&1 | head -40; echo "rc=$?"` 被鐵律六守衛（正確）擋下——缺的是行動點。"""

    def test_each_platform_keeps_the_commands_and_teaches_the_safe_form(self) -> None:
        for windows, must in ((False, ("導檔", "| head")), (True, ("`cd`", "Push-Location"))):
            hint = sb.verify_hint(windows=windows)
            for needle in ("--check", "--pace", "直接跑") + must:
                self.assertIn(needle, hint, (windows, needle))

    def test_no_variant_recommends_the_masked_pipe_form(self) -> None:
        """反例鎖：被點名的壞形態只准出現在『別／不要』的語境，不得寫成可照抄的完整指令。"""
        for windows in (False, True):
            hint = sb.verify_hint(windows=windows)
            self.assertTrue("別" in hint or "不要" in hint, hint)
            self.assertNotRegex(hint, r"\|\s*(head|tail)\b[^`]*;\s*echo")

    def test_the_brief_carries_the_platform_variant(self) -> None:
        self.assertNotEqual(sb.verify_hint(windows=True), sb.verify_hint(windows=False))
        for windows in (False, True):
            with mock.patch.object(sb.platform_utils, "is_windows", return_value=windows):
                got = sb.sessionstart_brief(
                    {}, _cache_miss_gate(), None, None, None, None, now=_NOW,
                    check_statusline=lambda: {"installed": True})
            self.assertIn(sb._VERIFY_HINT_WINDOWS if windows else sb._VERIFY_HINT, got)
            self.assertNotIn(sb._VERIFY_HINT if windows else sb._VERIFY_HINT_WINDOWS, got)


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
    """G1 四格：已安裝／未安裝／查不到／已安裝但與本 checkout 不符（DEF-200-414）。
    零 I/O——`check_status` 全由測試注入替身，不觸及真正的
    `install_statusline.status()`。"""

    def test_installed_reports_installed(self) -> None:
        got = sb.statusline_line(lambda: {"installed": True})
        self.assertEqual(got, "statusLine：已安裝")

    def test_installed_but_mismatched_reports_mismatch(self) -> None:
        """DEF-200-414：`matches_current_checkout` 為假時不得誤報成「已安裝」。"""
        got = sb.statusline_line(
            lambda: {"installed": True, "matches_current_checkout": False}
        )
        self.assertIn("已安裝但與本 checkout 不符", got)
        self.assertIn("install_statusline.py", got)
        self.assertNotEqual(got, "statusLine：已安裝")

    def test_missing_matches_key_defaults_to_installed(self) -> None:
        """缺 `matches_current_checkout` 鍵時預設視為相符（既有三格測試語意不變）。"""
        got = sb.statusline_line(lambda: {"installed": True})
        self.assertEqual(got, "statusLine：已安裝")

    def test_not_installed_reports_install_hint(self) -> None:
        got = sb.statusline_line(lambda: {"installed": False})
        self.assertIn("statusLine：未安裝", got)
        self.assertIn("install_statusline.py", got,
                      "未安裝時沒帶出安裝指令")

    def test_install_hint_is_a_pasteable_absolute_command(self) -> None:
        """簡報給的安裝指令要與 cwd、PATH 上的 python 無關（DEF-200-411 的兩個失敗面）：
        兩個 token 都是存在的絕對路徑。舊提示是裸 `python tools/…`（相對路徑），換個
        cwd、或 PATH 上排前面的是 pyenv python 就裝不起來——掌舵者 Q4 連問四輪「Windows
        為何沒有 ctx 行」的最後一個洞。"""
        cmd = sb._install_command()
        match = _PASTEABLE.match(cmd)
        self.assertIsNotNone(match, f"不是可貼的『直譯器／腳本』兩 token 形狀：{cmd}")
        py, script = (g.replace("''", "'") for g in match.groups() if g is not None)
        for token in (py, script):
            self.assertTrue(Path(token).is_absolute() and Path(token).is_file(), token)
        self.assertEqual(Path(script), _REPO_ROOT / "tools" / "install_statusline.py")
        for installed in ({"installed": False},
                          {"installed": True, "matches_current_checkout": False}):
            self.assertIn(cmd, sb.statusline_line(lambda: installed),
                          "未安裝／不相符兩種文案都要帶同一條可貼指令")

    def test_install_command_picks_the_checkout_venv_and_the_platform_lead(self) -> None:
        """直譯器優先取本 checkout 的 `.venv`（缺才退回 `sys.executable`，與
        `settings_snippet()` 同序）；Windows 前綴 `& `（PowerShell 呼叫運算子：
        帶引號的首 token 不加它只會被當字串印出、不會執行），POSIX 不加。`root`／
        `windows` 是注入縫：Windows 形狀在 Mac 上也要被鎖住。"""
        root = Path(tempfile.mkdtemp(prefix="brief-root-"))
        self.addCleanup(shutil.rmtree, root, True)
        script = root / "tools" / "install_statusline.py"
        for windows, lead, q in ((False, "", '"'), (True, "& ", "'")):
            with self.subTest(windows=windows):
                self.assertEqual(sb._install_command(root, windows),
                                 f"{lead}{q}{sys.executable}{q} {q}{script}{q}",
                                 "無 .venv 時該退回 sys.executable")
                venv_py = sb.platform_utils.venv_python_path(root / ".venv", windows)
                venv_py.parent.mkdir(parents=True, exist_ok=True)
                venv_py.write_text("", encoding="utf-8")
                self.assertEqual(sb._install_command(root, windows),
                                 f"{lead}{q}{venv_py}{q} {q}{script}{q}")
                venv_py.unlink()

    def test_a_windows_command_survives_powershell_special_characters(self) -> None:
        """Windows 形態用 PowerShell 單引號字串：`$`、反引號在雙引號內會被內插／跳脫（路
        徑被靜默改寫成別的東西），單引號內全是字面，內嵌單引號寫成兩個。以 PowerShell 的
        字面規則把指令解回 token，必須逐字還原原路徑——含空白、`$`、反引號、單引號的路徑
        各一。"""
        for name in ("plain", "with space", "a$b", "a`b", "O'Brien", "$env_path `x' y"):
            with self.subTest(name=name):
                root = Path(tempfile.gettempdir()) / name
                cmd = sb._install_command(root, True)
                match = re.fullmatch(r"& '((?:[^']|'')*)' '((?:[^']|'')*)'", cmd)
                self.assertIsNotNone(match, f"不是 `& '直譯器' '腳本'`：{cmd}")
                self.assertEqual(
                    [t.replace("''", "'") for t in match.groups()],
                    [sys.executable, str(root / "tools" / "install_statusline.py")])

    def test_the_fail_open_sentence_does_not_contradict_itself(self) -> None:
        """`_install_command()` 退回舊提示時，外層文案已說「貼上即安裝；先預覽就在尾端加
        --dry-run」，所以退回的指令本身不得再帶 `--dry-run` 或「預覽後去掉旗標」——否則同
        一句話一邊叫人貼上就裝、一邊說那是預覽。"""
        with mock.patch.object(sb.platform_utils, "venv_python_path",
                               side_effect=RuntimeError("合成：組不出")):
            line = sb.statusline_line(lambda: {"installed": False})
        self.assertIn("貼上即安裝", line)
        self.assertEqual(line.count("--dry-run"), 1, line)
        self.assertNotIn("去掉旗標", line)

    def test_install_command_fails_open_to_the_old_hint(self) -> None:
        """組不出絕對路徑時退回舊提示、簡報照出——安裝提示壞掉不得讓 SessionStart 崩潰。"""
        with mock.patch.object(sb.platform_utils, "venv_python_path",
                               side_effect=RuntimeError("合成：組不出")):
            self.assertEqual(sb._install_command(), sb._STATUSLINE_INSTALL_HINT)
            self.assertIn("statusLine：未安裝",
                          sb.statusline_line(lambda: {"installed": False}))

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


class StatuslineSystemMessageTest(unittest.TestCase):
    """SA-02／Q4：簡報只進模型 context、人看不到——statusLine 沒裝好時另給人一句
    （`systemMessage`）；裝好、查不到、compact（session 中途重注）一律 `None`，不每場吵。"""

    def test_missing_or_mismatched_speaks_with_the_pasteable_command(self) -> None:
        for report in ({"installed": False},
                       {"installed": True, "matches_current_checkout": False}):
            msg = sb.statusline_system_message({"source": "startup"}, lambda: report)
            self.assertIn(sb._install_command(), msg or "")
            self.assertIn("install_statusline.py", msg or "")

    def test_installed_unreadable_and_compact_stay_silent(self) -> None:
        def boom() -> dict:
            raise OSError("合成：查不到")
        for payload, check in (({}, lambda: {"installed": True}), ({}, boom),
                               ({"source": "compact"}, lambda: {"installed": False})):
            self.assertIsNone(sb.statusline_system_message(payload, check))

    def test_windows_gets_the_powershell_form(self) -> None:
        with mock.patch.object(sb.platform_utils, "is_windows", return_value=True):
            msg = sb.statusline_system_message({}, lambda: {"installed": False})
        self.assertIn(sb._install_command(windows=True), msg or "")


class SddFsmLineTest(unittest.TestCase):
    """`--check` 末行（給模型在 Q1「說被擋」時一條可外驗的證據）：只印 SDD router 的原始
    `current_state`，不判是否阻斷——阻斷態清單的唯一真相源在 SDD 側（`fsm_runtime`），
    這裡抄一份就是第二個家。純文字 regex 讀，不 import SDD 的 fsm_runtime、不需 yaml。"""

    def test_unset_reports_dormant(self) -> None:
        """`SDD_ACTIVE_VERSION` 缺席／空白＝router 休眠；簡報要說「休眠」，
        不能留白讓人猜。"""
        dormant = "SDD FSM：休眠（SDD_ACTIVE_VERSION 未設）"
        for env in ({}, {"SDD_ACTIVE_VERSION": ""}, {"SDD_ACTIVE_VERSION": "  "}):
            with self.subTest(env=env):
                self.assertEqual(sb.sdd_fsm_line(env), dormant)

    def test_set_prints_the_raw_state_the_path_and_the_mtime(self) -> None:
        """有設 ⇒ 印狀態檔裡的 `current_state` 原值＋路徑＋真實 mtime（帶 offset 的
        ISO）：20 天沒被任何 hook 寫過的殘留態，要靠 mtime 才看得出來。
        範本形態（帶引號＋行尾註解）也要讀得動。"""
        template = 'fsm_state:\n  current_state: "INIT"          # 當前 FSM 狀態\n'
        for body, state in ((_FSM_YAML, "SPEC_DRAFTING"), (template, "INIT")):
            with self.subTest(state=state):
                root, path = _fsm_tree(self, body)
                stamp = datetime(2026, 9, 11, 0, 44, 57, tzinfo=UTC).timestamp()
                os.utime(path, (stamp, stamp))
                got = sb.sdd_fsm_line({"SDD_ACTIVE_VERSION": "0.99"}, root)
                self.assertIn(f"current_state={state}（", got)
                self.assertIn(str(path), got)
                shown = re.search(r"mtime ([^）]+)）", got).group(1)
                self.assertEqual(datetime.fromisoformat(shown).timestamp(), stamp)

    def test_a_leading_v_is_accepted_like_the_router(self) -> None:
        """router 的 `_normalize_version` 去前導 v（`v0.99` ＝ `0.99`）；簡報若不認，
        同一份設定下 router 在跑、簡報卻說「無狀態檔」。"""
        root, _ = _fsm_tree(self, _FSM_YAML)
        self.assertEqual(sb.sdd_fsm_line({"SDD_ACTIVE_VERSION": "v0.99"}, root),
                         sb.sdd_fsm_line({"SDD_ACTIVE_VERSION": "0.99"}, root))

    def test_set_without_a_state_file_says_so(self) -> None:
        """版本有設但狀態檔不存在 ⇒ 明說「無狀態檔」並印預期路徑，不得假裝成某個狀態。"""
        root = Path(tempfile.mkdtemp(prefix="sdd-fsm-"))
        self.addCleanup(shutil.rmtree, root, True)
        got = sb.sdd_fsm_line({"SDD_ACTIVE_VERSION": "0.99"}, root)
        self.assertIn("無狀態檔", got)
        self.assertIn("FSM-STATE-AISDLC_SDD.yaml", got)
        self.assertNotIn("current_state=", got)

    def test_a_malformed_version_never_becomes_a_path(self) -> None:
        """router 對 `0.19/../../x` 這類值放行不路由（DEF-CLDREV-028 路徑注入）；
        簡報這一側不得把它拼進路徑讀檔——格式不符一律只報「格式非法」。"""
        root, _ = _fsm_tree(self, _FSM_YAML)
        for bad in ("0.99/../..", "..", "0.99\\..", "abc", "1"):
            with self.subTest(bad=bad):
                got = sb.sdd_fsm_line({"SDD_ACTIVE_VERSION": bad}, root)
                self.assertIn("格式非法", got)
                self.assertNotIn("current_state=", got)

    def test_sdd_project_override_selects_its_own_state_file(self) -> None:
        """狀態檔鍵＝`SDD_PROJECT`（有設）否則版本目錄的上一層資料夾名（同
        `state_loader.project_from_env`）；鍵不同就會讀到別人的檔——目錄裡另有一堆
        `FSM-STATE-test-*.yaml` 殘檔。"""
        body = "fsm_state:\n  current_state: ESCALATION\n"
        root, _ = _fsm_tree(self, body, project="custom")
        env = {"SDD_ACTIVE_VERSION": "0.99", "SDD_PROJECT": "custom"}
        self.assertIn("current_state=ESCALATION（", sb.sdd_fsm_line(env, root))

    def test_it_reports_the_state_without_judging_it(self) -> None:
        """阻斷態也只印原值、不下「阻斷／不阻斷」判決：判決要靠 SDD 側那份清單，
        這裡不維護第二份。"""
        root, _ = _fsm_tree(self, "fsm_state:\n  current_state: ESCALATION\n")
        got = sb.sdd_fsm_line({"SDD_ACTIVE_VERSION": "0.99"}, root)
        self.assertIn("current_state=ESCALATION（", got)
        self.assertNotIn("阻斷", got)

    def test_an_unreadable_state_is_reported_as_such(self) -> None:
        """狀態檔在但讀不出 `current_state` ⇒ 照實說讀不出，
        不退回任何預設狀態（假狀態比沒有更糟）。"""
        root, _ = _fsm_tree(self, "garbage: true\n")
        got = sb.sdd_fsm_line({"SDD_ACTIVE_VERSION": "0.99"}, root)
        self.assertIn("讀不出 current_state", got)
        self.assertNotIn("current_state=", got)


class SessionstartBriefTest(unittest.TestCase):
    """整合：四象限全組合都要含兩條查證指令 ＋ rc=2 澄清句，且不崩潰、不消失。

    DEF-200-412：`rc2_clarify()` 內部現查 `platform_utils.is_windows()`——本類別
    大多數既有測試只關心「兩句都在」這件事，與平台無關，故 `setUp()` 固定釘死
    POSIX（`False`），讓斷言在任何 CI runner（Windows／macOS／Linux）上都得到同一個
    字面，不隨「這台機器剛好是什麼平台」漂移。Windows 分支另有專屬測試
    （`test_windows_platform_swaps_to_powershell_guidance`）明確 patch 成 `True`。
    """

    def setUp(self) -> None:
        patcher = mock.patch.object(sb.platform_utils, "is_windows", return_value=False)
        patcher.start()
        self.addCleanup(patcher.stop)

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
        self.assertIn("install_statusline.py", got)

    def test_windows_platform_swaps_to_powershell_guidance(self) -> None:
        """DEF-200-412 接線面：`platform_utils.is_windows()` 為 True 時，最終簡報也
        真的換成 PowerShell 版澄清句——不是只有 `rc2_clarify()` 單元本身知道，
        `sessionstart_brief()` 有把它接進去。"""
        with mock.patch.object(sb.platform_utils, "is_windows", return_value=True):
            got = sb.sessionstart_brief(
                self._payload(None), _cache_miss_gate(),
                scan_transcript=None, resolve_window=None,
                window_evidence=None, read_context_feed=None, now=_NOW,
                check_statusline=self._FAKE_INSTALLED)
        self.assertIn("PowerShell／git", got)
        self.assertIn("鐵律一 hook 停用", got)

    def test_the_windows_brief_leads_with_the_disabled_bash_and_the_working_tools(self) -> None:
        """新視窗的模型要在**第一句**就拿到「哪個工具停用、哪些照常可用」（原句住簡報尾端易被
        略過；SD-195-03）；POSIX 簡報不加這句；兩個平台都不引述症狀字面。"""
        brief = {}
        for windows in (True, False):
            with mock.patch.object(sb.platform_utils, "is_windows", return_value=windows):
                brief[windows] = self._cache_miss_brief()
        lead = ("[SDD-CTX-GUARD]（Windows：Bash 工具由鐵律一 hook 停用，跑指令用 PowerShell "
                "工具；" + qm.convergent_tools_clause(True) + "。） 本 session 啟動時真實水位——")
        self.assertTrue(brief[True].startswith(lead), brief[True][:300])
        self.assertTrue(brief[False].startswith("[SDD-CTX-GUARD] 本 session 啟動時真實水位——"))
        self.assertNotIn("（Windows：", brief[False])
        for windows, got in brief.items():
            for symptom in ("不能寫檔", "也不要宣稱被擋"):
                self.assertNotIn(symptom, got, (windows, symptom))

    def _cache_miss_brief(self) -> str:
        return sb.sessionstart_brief(
            self._payload(None), _cache_miss_gate(),
            scan_transcript=None, resolve_window=None,
            window_evidence=None, read_context_feed=None, now=_NOW,
            check_statusline=self._FAKE_INSTALLED)

    def test_an_unattended_turn_is_told_which_writes_the_guard_blocks(self) -> None:
        """無人值守時治理檔的 Write／Edit 會被唯讀守衛擋下（exit 2）：簡報若只說 Write／Edit
        照常可用，就與守衛自己的訊息互相矛盾。互動 session 一律不加這句。"""
        sentence = "治理檔（PRD 保護面）的 Write／Edit 會被唯讀守衛擋下"
        with mock.patch.dict(os.environ, {unattended_authz.UNATTENDED_ENV: "1"}):
            self.assertIn(sentence, self._cache_miss_brief())
        with mock.patch.dict(os.environ):
            os.environ.pop(unattended_authz.UNATTENDED_ENV, None)
            self.assertNotIn(sentence, self._cache_miss_brief())

    def _assert_common(self, brief: str) -> None:
        self.assertIn("python tools/session_resume_planner.py --check", brief)
        self.assertIn("python tools/session_resume_planner.py --pace", brief)
        self.assertIn("rc=2", brief, "缺少『rc=2 紅字只代表扇出暫停』的誤讀澄清句")
        self.assertIn("Read／Write／Edit／Bash／git", brief)
        self.assertIn("statusLine：已安裝", brief, "G1 的 statusLine 那一句沒有進最終簡報")


class QuotaLineActiveModelTest(unittest.TestCase):
    """DEF-200-432（受測：`session_brief.quota_line`）：額度行的 `decide()` 此前沒帶
    `active_model` ⇒ 簡報 `cap=8 band=notice`、`--pace` 卻是 `cap=1 band=prepare`（Fable）。
    鎖：傳得進去／會改判定／不傳＝逐字不變；期望值取自真的 `decide()`，且帶／不帶兩值須不同。"""

    def _gate(self):
        return _fake_quota_gate(read_quota=lambda now, path=None: _scoped_state())

    def test_active_model_reaches_decide(self) -> None:
        seen: list[object] = []
        real = quota_policy.decide

        def _spy(*args, **kwargs):
            seen.append(kwargs.get("active_model", "<未傳>"))
            return real(*args, **kwargs)

        gate = types.SimpleNamespace(
            quota_policy=types.SimpleNamespace(
                load_policy=quota_policy.load_policy, decide=_spy,
                describe=quota_policy.describe),
            read_quota=lambda now, path=None: _scoped_state(), policy_env=lambda: {})
        sb.quota_line(gate, _NOW, "fable")
        sb.quota_line(gate, _NOW)
        self.assertEqual(seen, ["fable", None], "active_model 沒傳進 decide()（或缺席時不是 None）")

    def test_the_fable_line_speaks_the_verdict_decide_gives_and_differs_from_blind(self) -> None:
        blind = _verdict(sb.quota_line(self._gate(), _NOW))
        fable = _verdict(sb.quota_line(self._gate(), _NOW, "fable"))
        self.assertEqual(fable, _decided("fable"), "簡報的判定與真的 decide(fable) 不同")
        self.assertEqual(blind, _decided(None))
        self.assertNotEqual(fable, blind, "夾具對模型沒有鑑別力：帶不帶 fable 判定相同")
        self.assertEqual(fable[3], "weekly_scoped", "Fable 軸沒成為 binding ⇒ 沒進 cap 聚合")

    def test_another_model_keeps_the_scoped_axis_out(self) -> None:
        self.assertEqual(_verdict(sb.quota_line(self._gate(), _NOW, "sonnet")),
                         _verdict(sb.quota_line(self._gate(), _NOW)))

    def test_the_line_says_which_model_it_was_computed_for(self) -> None:
        with_model = sb.quota_line(self._gate(), _NOW, "fable")
        self.assertIn("active_model=fable", with_model)
        self.assertIn("model=Fable", with_model, "軸自己的 scope_model 字面（與 --pace 同）不見了")
        self.assertNotIn("active_model=", sb.quota_line(self._gate(), _NOW))

    def test_no_model_is_byte_identical_to_the_legacy_call(self) -> None:
        legacy = sb.quota_line(self._gate(), _NOW)
        self.assertEqual(sb.quota_line(self._gate(), _NOW, None), legacy)

    def test_an_unmeasured_line_carries_no_model_marker(self) -> None:
        """快取量不到（`axes == ()`）時模型沒有作用，不附標記（免得退化政策值旁多一句假精確）。"""
        stale = quota_policy.QuotaState((), "", "stale-cache", "stale-cache（測試）")
        got = sb.quota_line(_fake_quota_gate(read_quota=lambda now, path=None: stale),
                            _NOW, "fable")
        self.assertIn("stale-cache", got)
        self.assertNotIn("active_model=", got)


class SessionstartBriefActiveModelTest(unittest.TestCase):
    """DEF-200-432（受測：`sessionstart_brief(guard=…)` → `_active_model` →
    `harness_feed.start_model_of`）：新視窗逐字稿檔常還沒建，順序＝payload `model` → 逐字稿 →
    同 sid feed `model.id`（headless `-p` 的 payload 不帶 `model`）。`guard` 用真的模組。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="brief-model-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        hooks_dir = str(_REPO_ROOT / ".claude" / "hooks")
        if hooks_dir not in sys.path:
            sys.path.insert(0, hooks_dir)
        import context_budget_guard  # noqa: PLC0415 — 延遲：只有本類需要真守衛
        self.guard = context_budget_guard
        env = mock.patch.dict(
            os.environ, {context_budget_guard.CONTEXT_FEED_DIR_ENV: str(self.tmp)}, clear=False)
        env.start()
        self.addCleanup(env.stop)
        self.gate = _fake_quota_gate(read_quota=lambda now, path=None: _scoped_state())
        self.transcript = self.tmp / "sess-brief.jsonl"  # 刻意不建檔：新視窗那一刻它還不存在

    def _write_feed(self, model_id: str, *, sid: str = "sess-brief") -> None:
        (self.tmp / f"{sid}.json").write_text(json.dumps({
            "session_id": sid, "model": {"id": model_id},
            "context_window": {"context_window_size": 1_000_000, "current_usage": None},
        }), encoding="utf-8")

    def _brief(self, payload: dict, **extra: object) -> str:
        return sb.sessionstart_brief(
            payload, self.gate, scan_transcript=lambda p: (None, 0, None),
            resolve_window=lambda *a, **k: (1_000_000, "測試"), window_evidence=lambda *a, **k: {},
            read_context_feed=lambda *a: {}, now=_NOW,
            check_statusline=lambda: {"installed": True}, **extra)

    def _payload(self, **extra: object) -> dict:
        return {"transcript_path": str(self.transcript), **extra}

    def test_the_payload_model_makes_the_brief_speak_the_pace_verdict(self) -> None:
        got = self._brief(self._payload(model="claude-fable-5-1"), guard=self.guard)
        self.assertEqual(_verdict(got), _decided("fable"))
        self.assertNotEqual(_verdict(got), _decided(None), "夾具對模型沒有鑑別力")
        self.assertIn("active_model=fable", got)

    def test_without_a_payload_model_a_fresh_feed_supplies_it(self) -> None:
        self._write_feed("claude-fable-5-1")
        got = self._brief(self._payload(), guard=self.guard)
        self.assertEqual(_verdict(got), _decided("fable"))

    def test_the_payload_beats_the_feed(self) -> None:
        self._write_feed("claude-fable-5-1")
        got = self._brief(self._payload(model="claude-sonnet-5-5"), guard=self.guard)
        self.assertEqual(_verdict(got), _decided(None), "feed 說 fable 卻壓過了 payload 的 sonnet")
        self.assertIn("active_model=sonnet", got)

    def test_a_feed_that_says_sonnet_keeps_the_fable_axis_out(self) -> None:
        self._write_feed("claude-sonnet-5-5")
        got = self._brief(self._payload(), guard=self.guard)
        self.assertEqual(_verdict(got), _decided(None))
        self.assertIn("active_model=sonnet", got)

    def test_nothing_known_is_byte_identical_to_the_legacy_call(self) -> None:
        legacy = self._brief(self._payload())
        self.assertEqual(self._brief(self._payload(), guard=self.guard), legacy)
        self.assertNotIn("active_model", legacy)

    def test_a_foreign_feed_is_not_believed(self) -> None:
        self._write_feed("claude-fable-5-1", sid="sess-brief")
        (self.tmp / "sess-brief.json").write_text(json.dumps({
            "session_id": "someone-else", "model": {"id": "claude-fable-5-1"},
            "context_window": {"context_window_size": 1_000_000}}), encoding="utf-8")
        got = self._brief(self._payload(), guard=self.guard)
        self.assertEqual(_verdict(got), _decided(None))
        self.assertNotIn("active_model=", got)

    def test_without_a_guard_the_payload_model_cannot_be_resolved(self) -> None:
        """既有的六位置引數呼叫（沒傳 `guard`）逐字相容：即使 payload 帶了模型也照舊。"""
        got = self._brief(self._payload(model="claude-fable-5-1"))
        self.assertEqual(_verdict(got), _decided(None))
        self.assertNotIn("active_model", got)

    def test_a_broken_guard_fails_open_to_the_legacy_line(self) -> None:
        def _boom(_model: object) -> str:
            raise RuntimeError("合成：guard 壞了")
        broken = types.SimpleNamespace(model_family=_boom)
        got = self._brief(self._payload(model="claude-fable-5-1"), guard=broken)
        self.assertEqual(_verdict(got), _decided(None), "guard 壞掉不該讓簡報崩潰或改判")


def _halt_decision() -> quota_policy.Decision:
    """停止水位的真 `decide()` 結果（五小時軸 99%）：組 halt 訊息用，不手捏 Decision。"""
    state = quota_policy.QuotaState(
        (quota_policy.Axis("five_hour", 99.0, (_NOW + timedelta(minutes=30)).isoformat()),),
        _NOW.isoformat(), "cache", "ok")
    policy, _problems = quota_policy.load_policy({})
    return quota_policy.decide(state, _NOW, policy)


class ConvergentToolsClauseSingleHomeTest(unittest.TestCase):
    """「收斂型工具清單」那句只有一個導出：`quota_messages.convergent_tools_clause()`。

    立案：同一份清單住在簡報（POSIX／Windows 各一）與 halt 訊息（POSIX／Windows 各一）四個家，
    其中兩處靠對成句做字串手術（切全形分號、切「，只有扇出型」）衍生——改任一份字面（尤其插入
    全形分號）就悄悄壞。現在只有函式本體一處持有字面，其餘一律呼叫它。"""

    _LIBS = ("quota_messages.py", "session_brief.py")
    _PHRASE = "不受影響"

    @staticmethod
    def _source(name: str) -> str:
        return (_REPO_ROOT / "tools" / "lib" / name).read_text(encoding="utf-8")

    @staticmethod
    def _outside_the_def(text: str) -> str:
        """去掉 `convergent_tools_clause` 的整個本體（到下一行頂格的非空白為止）。"""
        return re.sub(r"^def convergent_tools_clause\(.*?(?=^\S)", "", text, flags=re.S | re.M)

    @staticmethod
    def _tools_of(text: str) -> set[str]:
        found = re.search(r"收斂型工具（([^，）]+)", text)
        return set(found.group(1).split("／")) if found else set()

    def test_the_phrase_survives_only_inside_the_function_body(self) -> None:
        inside = 0
        for name in self._LIBS:
            text = self._source(name)
            rest = self._outside_the_def(text)
            self.assertNotIn(self._PHRASE, rest, f"{name}：函式本體之外又抄了一份")
            inside += text.count(self._PHRASE) - rest.count(self._PHRASE)
        self.assertEqual(inside, 1, "字面該恰好只住在函式本體一處")

    def test_the_grep_lock_can_fail(self) -> None:
        """判準自證：把字面塞回本體之外，鎖就必須看得到。"""
        text = self._source("quota_messages.py") + "\n# 又抄了一份：不受影響\n"
        self.assertIn(self._PHRASE, self._outside_the_def(text))

    def test_no_string_surgery_is_left_on_the_composed_sentence(self) -> None:
        text = self._source("quota_messages.py")
        for surgery in ('.split("；"', ".partition("):
            self.assertNotIn(surgery, text)

    def test_the_clause_is_safe_to_compose(self) -> None:
        for windows in (False, True):
            clause = qm.convergent_tools_clause(windows)
            self.assertNotIn("；", clause)
            self.assertNotIn("，只有", clause)
            self.assertTrue(clause.endswith(self._PHRASE), clause)

    def test_every_consumer_names_the_same_tools_per_platform(self) -> None:
        decision = _halt_decision()
        act = {"plan": "P", "kind": "five_hour", "branch": qm.QUOTA_BRANCH_ARM,
               "armed": True, "sentinel_off": False, "posix": False}
        for windows in (False, True):
            want = self._tools_of(qm.convergent_tools_clause(windows))
            self.assertIn("git", want)
            with mock.patch.object(sb.platform_utils, "is_windows", return_value=windows):
                consumers = {
                    "簡報": sb.rc2_clarify(),
                    "halt": qm.halt_convergent_clarification(),
                    "halt 阻斷": qm.halt_convergent_clarification(event="PreToolUse", tool="Agent"),
                    "量不到": qm.degraded_convergent_clarification(),
                    "halt 抬頭": qm.quota_halt_message(decision, act, "PostToolUse", "Read"),
                }
            for label, text in consumers.items():
                with self.subTest(windows=windows, consumer=label):
                    self.assertEqual(self._tools_of(text), want)
        self.assertEqual(self._tools_of(qm.convergent_tools_clause(False)) - {"Bash"},
                         self._tools_of(qm.convergent_tools_clause(True)) - {"PowerShell"},
                         "兩個平台只該差殼（Bash／PowerShell）")

    def test_a_bad_shell_call_is_said_to_stop_only_that_call(self) -> None:
        for windows, shell in ((False, "Bash"), (True, "PowerShell")):
            clause = qm.convergent_tools_clause(windows)
            self.assertIn(f"寫壞的 {shell} 只擋那一次呼叫", clause)
            for text in (sb.rc2_clarify(windows), qm.halt_convergent_clarification(windows),
                         qm.degraded_convergent_clarification(windows)):
                with self.subTest(shell=shell):
                    self.assertIn(clause, text)

    def test_the_posix_brief_says_the_bad_call_does_not_run_and_bash_still_works(self) -> None:
        got = sb.rc2_clarify(windows=False)
        for needle in ("寫壞的那一次 Bash 呼叫會被攔下、不執行", "Bash 本身仍可用", "照改重跑即可"):
            self.assertIn(needle, got)
        self.assertNotIn("另由指令形態守衛擋下", got)

    def test_the_composed_halt_sentences_keep_their_first_clause_contract(self) -> None:
        """首句隨事件換、其餘同源：PreToolUse 沒執行，不得說「已正常執行完成」。"""
        legacy = qm.halt_convergent_clarification(windows=False)
        blocked = qm.halt_convergent_clarification(windows=False, event="PreToolUse", tool="Agent")
        self.assertEqual(legacy, qm.HALT_CONVERGENT_CLARIFICATION)
        self.assertTrue(legacy.startswith("你剛才那次工具呼叫已正常執行完成；"))
        self.assertTrue(blocked.startswith("這次 Agent 呼叫已被擋下、沒有執行；"))
        self.assertEqual(blocked.split("；", 1)[1], legacy.split("；", 1)[1])


class ReadFallbackHintTest(unittest.TestCase):
    """真實數據的載具原先只有 Bash（planner `--check`／`--pace`）：auto mode 分類器暫時不可用
    時 Bash 與寫檔一起被拒，模型同時「被擋」又「查不了真實數據」。Read 工具唯讀、不經那個
    分類器，所以簡報多給一條唯讀退路：feed 檔（context）與額度快取檔，路徑取自既有 SSOT。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="brief-read-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        env = mock.patch.dict(os.environ, {"AUTOSDD_CONTEXT_FEED_DIR": str(self.tmp / "feed"),
                                           "AUTOSDD_QUOTA_CACHE_DIR": str(self.tmp / "quota")})
        env.start()
        self.addCleanup(env.stop)
        self.gate = _fake_quota_gate(read_quota=lambda now, path=None: _cache_hit_state())
        self.gate.quota_cache_path = quota_gate.quota_cache_path  # 真的 SSOT：meter 的 cache_path

    def _brief(self, payload: dict, *, windows: bool = False, gate: object = None) -> str:
        with mock.patch.object(sb.platform_utils, "is_windows", return_value=windows):
            return sb.sessionstart_brief(
                payload, gate or self.gate, scan_transcript=None, resolve_window=None,
                window_evidence=None, read_context_feed=None, now=_NOW,
                check_statusline=lambda: {"installed": True})

    def test_both_platforms_teach_the_read_tool_fallback(self) -> None:
        for windows in (False, True):
            hint = sb.verify_hint(windows=windows)
            for needle in ("**Read**", "分類器", "唯讀", "used_percentage", "current_usage",
                           "context_window_size", "axes[]", "severity", "不要憑簡報猜",
                           "沒看到阻斷訊息就不要說被擋", "只針對那一個路徑", "受保護路徑"):
                self.assertIn(needle, hint, (windows, needle))
            self.assertNotIn("寫檔被拒", hint, (windows, "條件句不預寫劇本（DEF-200-476）"))

    def test_both_platforms_say_a_permission_prompt_is_not_a_hook_block(self) -> None:
        """退路的兩個 Read 目標在 cwd 外、planner 現查也常要核准：模型把這種權限詢問讀成「被擋」就會
        放棄現查並宣稱被擋。解釋句只掛在唯讀退路之後（整則訊息一次；開頭條件子句也提到「權限詢問」
        不算解釋句），不進其他段落。"""
        for windows in (False, True):
            with self.subTest(windows=windows):
                hint = sb.verify_hint(windows=windows)
                after_fallback = hint.split("沒看到阻斷訊息就不要說被擋", 1)[1]
                self.assertEqual(after_fallback.count("權限詢問"), 1, hint)
                for needle in ("權限詢問", "harness", "不是 hook 阻斷", "有人在就核准", "headless"):
                    self.assertIn(needle, after_fallback, (windows, needle))
                self.assertNotIn("權限詢問", sb.rc2_clarify(windows=windows))

    def test_the_brief_names_the_resolved_feed_and_quota_files_on_both_platforms(self) -> None:
        feed, quota = self.tmp / "feed" / "sess-abc.json", self.tmp / "quota" / "autosdd_quota.json"
        for windows in (False, True):
            got = self._brief({"session_id": "sess-abc"}, windows=windows)
            with self.subTest(windows=windows):
                self.assertIn(f"`{feed}`", got)
                self.assertIn(f"`{quota}`", got)
                self.assertIn("**Read**", got)

    def test_the_paths_come_from_the_ssot_not_from_a_second_spelling(self) -> None:
        """路徑與寫入端 `statusline_context_feed.context_feed_path()`、meter 的 `cache_path()`
        逐字相同——不設環境覆寫時也一樣（預設目錄含 `context_feed`／`autosdd_quota.json`）。"""
        sys.path.insert(0, str(_REPO_ROOT / "tools"))
        import statusline_context_feed  # noqa: PLC0415 — 延遲：只有本格要對帳寫入端
        with mock.patch.dict(os.environ):
            os.environ.pop("AUTOSDD_CONTEXT_FEED_DIR")
            os.environ.pop("AUTOSDD_QUOTA_CACHE_DIR")
            got = self._brief({"session_id": "sess-abc"})
            feed = statusline_context_feed.context_feed_path("sess-abc")
            self.assertIn(str(feed), got)
            self.assertIn("context_feed", str(feed))
            self.assertIn(str(quota_gate.quota_cache_path()), got)
            self.assertTrue(str(quota_gate.quota_cache_path()).endswith("autosdd_quota.json"))

    def test_the_session_id_comes_from_the_payload_then_the_transcript_name(self) -> None:
        transcript = self.tmp / "from-transcript.jsonl"
        by_payload = self._brief({"session_id": "from-payload", "transcript_path": str(transcript)})
        self.assertIn("from-payload.json", by_payload)
        self.assertNotIn("from-transcript.json", by_payload)
        self.assertIn("from-transcript.json", self._brief({"transcript_path": str(transcript)}))

    def test_without_a_session_id_the_template_and_the_newest_mtime_rule_are_given(self) -> None:
        got = self._brief({})
        self.assertIn(str(self.tmp / "feed" / "<session_id>.json"), got)
        self.assertIn("最新 mtime", got)

    def test_an_unreachable_ssot_degrades_to_a_pathless_sentence_not_a_crash(self) -> None:
        bare = _fake_quota_gate(read_quota=lambda now, path=None: _cache_hit_state())
        with mock.patch.dict(sys.modules, {"statusline_context_feed": None}):
            got = self._brief({"session_id": "sess-abc"}, gate=bare)
        self.assertIn("**Read**", got)
        self.assertNotIn("sess-abc.json", got)
        self.assertNotIn("autosdd_quota.json", got)


def _load_sga():
    """延遲載入驗收工具：`tools/` 只在需要它的格才進 `sys.path`（同下方對帳寫入端的作法）；
    工具檔缺席時只讓本類別的測試紅，不拖垮整個模組的匯入。"""
    tools = str(_REPO_ROOT / "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import session_gate_acceptance  # noqa: PLC0415 — 延遲，理由見 docstring
    return session_gate_acceptance


_REPORT_KEYS = frozenset({
    "schema", "generated_at", "platform", "os_label", "host", "python_version", "cc_version",
    "repo_head", "statusline", "hook_carrier", "verify_hint", "fsm_current_state",
    "fsm_line", "check", "trace_dir"})


class SessionGateAcceptanceTest(unittest.TestCase):
    """單一指令驗收（`tools/session_gate_acceptance.py`）把「這個平台的守門真的裝好了」收成
    一份貼回即可判讀的 JSON。測意圖：證據只准**量到什麼寫什麼**——量不到寫 null／error、
    不崩潰、不弄髒真實家目錄；Windows 格（簡報給 `Push-Location`／`LASTEXITCODE` 兩個安全
    形態 token）是 Mac 側唯一能預先釘住的那一半，平台一翻轉兩格必須跟著翻。"""

    def setUp(self) -> None:
        import endurance_env  # noqa: PLC0415 — 延遲；且須在改 HOME 之前解出「真實」居所
        self.sga = _load_sga()
        self.real = Path.home().joinpath(*endurance_env.TRACE_HOME_PARTS)
        self.real_before = self._real_stamps()
        self.home = Path(tempfile.mkdtemp(prefix="gate-accept-"))
        self.addCleanup(shutil.rmtree, self.home, True)
        self.traces = self.home / "traces"
        self.assertNotEqual(self.real, self.traces)
        env = mock.patch.dict(os.environ, {
            "HOME": str(self.home), "USERPROFILE": str(self.home),
            "AUTOSDD_TRACE_DIR": str(self.traces),
            "AUTOSDD_CONTEXT_FEED_DIR": str(self.home / "feed"),
            "AUTOSDD_QUOTA_CACHE_DIR": str(self.home / "quota")})
        env.start()
        self.addCleanup(env.stop)
        for key in ("CLAUDE_CONFIG_DIR", "CLAUDE_CODE_SESSION_ID"):
            os.environ.pop(key, None)

    def _real_stamps(self) -> dict[str, int]:
        return {p.name: p.stat().st_mtime_ns
                for p in self.real.glob("session_gate_acceptance_*.json")}

    def _run(self, argv: list[str] | None = None) -> tuple[int, dict]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = self.sga.cli([] if argv is None else argv)
        return rc, (json.loads(out.getvalue()) if out.getvalue().strip() else {})

    def test_the_report_has_exactly_the_documented_keys(self) -> None:
        rc, report = self._run()
        self.assertEqual(rc, 0)
        self.assertEqual(set(report), _REPORT_KEYS)
        self.assertEqual(set(report["statusline"]), {
            "installed", "matches_current_checkout", "python_basis", "settings_file_exists"})
        self.assertEqual(set(report["hook_carrier"]), {"path", "exists", "is_symlink"})
        self.assertEqual(set(report["verify_hint"]), {
            "default_push_location", "default_lastexitcode", "windows_variant_both"})
        self.assertEqual(set(report["check"]), {"rc", "diff_line", "lines", "banner", "stderr"})
        self.assertEqual(report["platform"], sys.platform)
        stamp = datetime.fromisoformat(report["generated_at"])
        self.assertIsNotNone(stamp.utcoffset(), "不帶 offset 的時間戳無法跨機器比對新舊")

    def test_the_windows_cells_flip_with_the_platform_and_the_variant_has_both_tokens(self) -> None:
        cells = {}
        for windows in (True, False):
            with mock.patch.object(sb.platform_utils, "is_windows", return_value=windows):
                cells[windows] = self.sga.hint_cells()
        self.assertEqual(cells[True], {"default_push_location": True,
                                       "default_lastexitcode": True, "windows_variant_both": True})
        self.assertEqual(cells[False], {"default_push_location": False,
                                        "default_lastexitcode": False, "windows_variant_both": True})
        for token in ("Push-Location", "LASTEXITCODE"):
            self.assertIn(token, sb.verify_hint(windows=True))

    def test_an_unknown_flag_is_rejected_loudly_and_writes_nothing(self) -> None:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = self.sga.cli(["--bogus"])
        self.assertEqual(rc, 2)
        self.assertEqual(out.getvalue(), "", "拒收時不得印出任何一份看起來像證據的 JSON")
        self.assertIn("--bogus", err.getvalue())
        self.assertEqual(list(self.traces.glob("*")), [])

    def test_the_only_write_is_one_json_under_the_injected_trace_dir(self) -> None:
        rc, report = self._run()
        self.assertEqual(rc, 0)
        written = list(self.traces.iterdir())
        self.assertEqual(len(written), 1, [p.name for p in written])
        self.assertTrue(written[0].name.startswith("session_gate_acceptance_"))
        self.assertEqual(json.loads(written[0].read_text(encoding="utf-8")), report)
        self.assertEqual(report["trace_dir"], str(self.traces))
        self.assertEqual(self._real_stamps(), self.real_before, "真實 trace 居所被動了")

    def test_nothing_to_measure_is_a_null_cell_not_a_crash_and_never_a_pass(self) -> None:
        rc, report = self._run()
        self.assertEqual(rc, 0)
        self.assertIsNone(report["cc_version"])
        self.assertIs(report["statusline"]["installed"], False)
        self.assertIs(report["statusline"]["settings_file_exists"], False)
        self.assertIsNone(report["check"]["diff_line"])
        self.assertIsInstance(report["check"]["rc"], int)
        self.assertNotEqual(report["check"]["rc"], 0, "沒有逐字稿卻回 0＝把量不到寫成通過")

    def test_a_raising_collector_becomes_an_error_cell_and_the_rest_survives(self) -> None:
        import install_statusline  # noqa: PLC0415 — `tools/` 已由 `_load_sga()` 放進 sys.path
        import session_resume_planner as planner  # noqa: PLC0415
        for exc in (RuntimeError("boom"), SystemExit(2)):
            with self.subTest(exc=type(exc).__name__):
                with mock.patch.object(planner, "main", side_effect=exc), \
                        mock.patch.object(install_statusline, "status", side_effect=OSError("x")):
                    rc, report = self._run()
                self.assertEqual(rc, 0)
                self.assertEqual(report["check"], {"rc": None, "error": type(exc).__name__})
                self.assertEqual(report["statusline"], {"error": "OSError"})
                self.assertEqual(set(report), _REPORT_KEYS)

    def test_the_in_process_planner_call_leaves_the_environment_as_it_found_it(self) -> None:
        def leak(env, root=None):  # 與 planner 的 `apply_env_defaults` 同形：把預設填進環境
            env["GATE_ACCEPT_ENV_LEAK_PROBE"] = "1"
            return []
        before = dict(os.environ)
        with mock.patch.object(quota_gate, "apply_env_defaults", side_effect=leak):
            self._run()
        self.assertEqual(dict(os.environ), before, "planner 填的環境變數洩漏到呼叫端")

    def test_repo_head_reads_loose_packed_and_detached_refs(self) -> None:
        sha, other = "a" * 40, "b" * 40
        repo = self.home / "repo"
        git = repo / ".git"
        (git / "refs" / "heads").mkdir(parents=True)
        (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
        loose = git / "refs" / "heads" / "main"
        loose.write_text(sha + "\n", encoding="utf-8")
        self.assertEqual(self.sga.repo_head(repo), sha, "鬆散 ref")
        loose.unlink()
        (git / "packed-refs").write_text(
            f"# pack-refs with: peeled\n{other} refs/heads/dev\n{sha} refs/heads/main\n",
            encoding="utf-8")
        self.assertEqual(self.sga.repo_head(repo), sha, "只住在 packed-refs")
        (git / "HEAD").write_text(other + "\n", encoding="utf-8")
        self.assertEqual(self.sga.repo_head(repo), other, "detached HEAD 直接是 sha")
        (git / "HEAD").write_text("ref: refs/heads/gone\n", encoding="utf-8")
        self.assertIsNone(self.sga.repo_head(repo), "兩處都找不到＝量不到，不是猜一個")

    def test_hook_carrier_reports_existence_of_the_literal_path(self) -> None:
        repo = self.home / "repo-carrier"
        literal = (".venv", "Scripts", "pythonw.exe")  # platform-ok: hook 載具字面（兩平台同名）
        self.assertEqual(self.sga.hook_carrier(repo),
                         {"path": "/".join(literal), "exists": False, "is_symlink": False})
        carrier = repo.joinpath(*literal)
        carrier.parent.mkdir(parents=True)
        carrier.write_bytes(b"")
        self.assertEqual(self.sga.hook_carrier(repo)["exists"], True)
        self.assertEqual(self.sga.hook_carrier(repo)["is_symlink"], False)

    def test_cc_version_is_the_last_versioned_record_of_the_newest_transcript(self) -> None:
        from probe.audit_session import project_transcript_dir  # noqa: PLC0415
        base = project_transcript_dir(_REPO_ROOT)
        self.assertTrue(str(base).startswith(str(self.home)), "逐字稿目錄沒有跟著隔離的家走")
        base.mkdir(parents=True)
        self.assertIsNone(self.sga.cc_version(_REPO_ROOT), "目錄在、逐字稿不在")
        old, new = base / "old.jsonl", base / "new.jsonl"
        old.write_text(json.dumps({"version": "1.0.0"}) + "\n", encoding="utf-8")
        new.write_text("\n".join([
            json.dumps({"type": "user", "version": "2.1.287"}),
            json.dumps({"type": "assistant", "version": "2.1.288"}),
            json.dumps({"type": "file-history-snapshot"}),
            '{"half-written']) + "\n", encoding="utf-8")
        os.utime(old, (1_000_000_000, 1_000_000_000))
        self.assertEqual(self.sga.cc_version(_REPO_ROOT), "2.1.288")


class RepoSettingsReadOnlyAllowTest(unittest.TestCase):
    """DEF-200-476：repo settings 的 permissions.allow 只准是簡報教的兩條 planner 現查＋兩個唯讀退路
    Read 目標。涵蓋判定摹仿 harness（去 Tool(…) 外殼、含 * 者萬用比對），不重寫它的比對器。"""
    _SETTINGS = _REPO_ROOT / ".claude" / "settings.json"
    #: venv 相對形（`.venv\Scripts\python.exe tools/…`）在 headless dontAsk 探針實測
    #: PS-DENIED＝死規則，已移除；SOP 第 0 步改教與簡報相同的裸 python 字面。
    _HEADS = {"PowerShell": ("python tools/", "python *"),
              "Bash": ("python tools/", "python *")}
    _ALLOW = frozenset(f"{t}({h}session_resume_planner.py --{f}*)" for t, hs in _HEADS.items()
                       for h in hs for f in ("check", "pace")) | {
        "Read(~/.autosdd/context_feed/*.json)", "Read(~/autosdd_quota.json)"}
    _NARROW = re.compile(
        r"^Read\(~/(\.autosdd/context_feed/\*\.json|autosdd_quota\.json)\)$|"
        r"^(Bash|PowerShell)\((python|\.venv\S*python(\.exe)?) \S*session_resume_planner\.py "
        r"--(check|pace)\*\)$")

    def _allow(self) -> list[str]:
        return json.loads(self._SETTINGS.read_text(encoding="utf-8"))["permissions"]["allow"]

    def _covered(self, tool: str, text: str) -> bool:
        rules = [(r.partition("(")[0], r.partition("(")[2][:-1]) for r in self._allow()]
        return any(t == tool and (fnmatch.fnmatchcase(text, p) if "*" in p else text == p)
                   for t, p in rules)

    def test_allow_equals_the_constant_table_without_duplicates(self) -> None:
        self.assertEqual(sorted(self._allow()), sorted(self._ALLOW), "集合不等或有重複規則")

    def test_each_brief_command_is_covered_on_both_carriers(self) -> None:
        for cmd in re.findall(r"`([^`]+)`", sb._CHECK_PACE):
            for tool in ("Bash", "PowerShell"):
                self.assertTrue(self._covered(tool, cmd), (tool, cmd))

    def test_read_rules_cover_the_briefs_read_targets_under_any_home(self) -> None:
        home = tempfile.mkdtemp(prefix="allow-home-")
        self.addCleanup(shutil.rmtree, home, True)
        env = dict.fromkeys(("HOME", "USERPROFILE"), home) | {
            "AUTOSDD_CONTEXT_FEED_DIR": "", "AUTOSDD_QUOTA_CACHE_DIR": ""}
        with mock.patch.dict(os.environ, env):
            for shown in sb._read_targets(quota_gate, "x"):
                rel = "~/" + Path(shown.strip("`")).relative_to(Path.home()).as_posix()
                self.assertTrue(self._covered("Read", rel), rel)

    def test_no_rule_widens_beyond_the_two_read_only_families(self) -> None:
        for rule in self._allow():
            self.assertRegex(rule, self._NARROW)
            self.assertNotRegex(
                rule, r"^(Write|Edit|NotebookEdit)\(|git (commit|push)|Remove-|\*\*")


if __name__ == "__main__":
    unittest.main()
