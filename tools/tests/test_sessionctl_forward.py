#!/usr/bin/env python3
"""UserPromptSubmit 轉送與「已交棒告知」的驗收測試（R3 WP-5；ARCH §2.2／§2.3、AT-F1～F8、M-F3）。

守的判準（每條 docstring 寫 WHY）：
- 路徑一（冷舊窗轉送）九條件缺一不擋；擋之前原文必須逐字落檔；spawn 失敗一律放行（寧可多付快取，
  不吞輸入）；`<task-notification>` 永不擋（F1-8：擋掉會吞子代理交卷結果）。
- 路徑二（已交棒告知）：新視窗活著就擋並說明、不 spawn、不看快取冷熱；新視窗不在就放行。
縫：假 spawn／alive／cache／crons／preflight（A-3 參數注入）、tmp 目錄；絕不真的開視窗、不碰真實
`~/.autosdd`。hook 層（子行程）以 `SESSIONCTL_APPLIED_ROOT` 指向套用後佈局的鏡像根驗成品；
hook 尚無新分支（套用前）時該幾條 skip。
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from datetime import UTC, datetime
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "tools"))
sys.path.insert(0, str(_REPO / "tools" / "lib"))

from lib.sessionctl import forward, switch  # noqa: E402
from lib.wastecensus import supervision as sv  # noqa: E402

SID = "cccccccc-1111-2222-3333-444444444444"
NOW = datetime(2026, 11, 17, 3, 0, 0, tzinfo=UTC)
PID = 4242
SPAWN_AT = "2026-11-17T09:05:00+08:00"  # 夾具的新視窗開窗時刻（帶 offset；顯示端換成本地時區）
GUARD_ROOT = Path(os.environ.get("SESSIONCTL_APPLIED_ROOT") or _REPO)
HOOK = GUARD_ROOT / ".claude" / "hooks" / "sessionctl_guard.py"
_SCRUB = ("AUTOSDD_UNATTENDED", "AUTOSDD_SESSIONCTL_GUARD_OFF", "AUTOSDD_SESSION_SWITCH_MODE")


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="fwd-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        env = {k: v for k, v in os.environ.items() if k not in _SCRUB}
        env.update({"AUTOSDD_TRACE_DIR": str(self.tmp / "traces"),
                    "AUTOSDD_HANDOFF_DIR": str(self.tmp / "handoff"),
                    "AUTOSDD_QUOTA_CACHE_DIR": str(self.tmp / "quota")})
        patcher = unittest.mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        (self.tmp / "traces").mkdir()
        (self.tmp / "handoff").mkdir()
        self.pkg = self.tmp / "handoff" / f"{SID}_20261117T020000Z.md"
        self.pkg.write_text(f"# 交接包 <!-- sessionctl-handoff sid={SID} at=x -->\n\n## 主控層\n",
                            encoding="utf-8")
        self.pkg.with_suffix(".sealed").write_text(NOW.isoformat() + "\n", encoding="utf-8")
        self.transcript = self.tmp / "t.jsonl"
        self.set_ctx(600_000)  # R216 F4：快取冷時只有上下文夠大（> 480,000）才轉送；夾具預設走轉送
        self.spawned: list[dict] = []
        self.refreshed: list[Path] = []
        self.spawn_rc = 0

    def set_ctx(self, ctx: int | None) -> None:
        """逐字稿最後一筆 assistant usage 合計 `ctx`；`None`＝沒有任何 usage（上下文量不到）。"""
        if ctx is None:
            self.transcript.write_text("{}\n", encoding="utf-8")
            return
        usage = {"input_tokens": 1, "cache_read_input_tokens": ctx - 1,
                 "cache_creation_input_tokens": 0, "output_tokens": 7}
        row = {"type": "assistant", "timestamp": NOW.isoformat(),
               "message": {"id": "m", "usage": usage}}
        self.transcript.write_text(json.dumps(row) + "\n", encoding="utf-8")

    # ── 假縫
    def fake_spawn(self, path, **kw) -> int:
        self.spawned.append({"path": Path(path), **kw})
        switch.trace("session_switch_spawned", pid=PID, handoff=str(path), at=NOW.isoformat(),
                     ok=self.spawn_rc == 0)
        return self.spawn_rc

    def verdict(self, prompt: str, **over) -> dict:
        args = {"spawn": self.fake_spawn, "alive": lambda pid: False,
                "cache": lambda p, n: {"cold": True, "idle_s": 4000.0},
                "crons": lambda sid: False, "preflight": lambda p: [],
                "refresh": lambda p, **kw: self.refreshed.append(Path(p)),
                "platform_name": "win32", "now": NOW}
        args.update(over)
        payload = {"session_id": SID, "transcript_path": str(self.transcript),
                   "prompt_id": "abcdef0123", "prompt": prompt,
                   "hook_event_name": "UserPromptSubmit"}
        return forward.prompt_verdict(payload, os.environ, **args)

    def events(self, name: str) -> list[dict]:
        path = self.tmp / "traces" / "autosdd_session_switch.jsonl"
        if not path.is_file():
            return []
        rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]
        return [r for r in rows if r.get("event") == name]

    def hand_over(self) -> None:
        """造「已交棒」：包已 ack，且痕跡有 spawn 記錄（pid=PID）。"""
        self.pkg.with_suffix(".ack").write_text("ok\n", encoding="utf-8")
        switch.trace("session_switch_spawned", pid=PID, handoff=str(self.pkg),
                     at=SPAWN_AT, ok=True)


class PathOneForwardTest(_Base):
    def test_all_nine_conditions_hold_then_block_with_original_saved_and_spawned(self) -> None:
        """WHY：九條全成立才擋；擋的同時必須已開新 session（帶原文檔、等 20 秒）、先補 sidecar。"""
        out = self.verdict("下一步：把 Weekly 用完")
        self.assertEqual(out["kind"], "block")
        self.assertIn("已轉到新 session", out["text"])
        self.assertIn("留：", out["text"])
        self.assertEqual(len(self.spawned), 1)
        call = self.spawned[0]
        self.assertEqual(call["wait_seconds"], 20)
        self.assertTrue(call["extra_prompt_file"].is_file())
        self.assertEqual(self.refreshed, [self.pkg])  # A-2：spawn 前補寫 sidecar
        self.assertEqual(len(self.events(forward.EV_SPAWNED)), 1)

    def test_each_failing_condition_passes_and_records_its_number(self) -> None:
        """AT-F1 WHY：任一條不成立就放行；量測端靠 forward_pass 的 cond 欄知道卡在哪一條。"""
        cases = {
            2: lambda: self.verdict("/compact"),
            3: lambda: self.verdict("留：先回答我"),
            5: lambda: self.verdict("x", cache=lambda p, n: {"cold": False, "idle_s": 5.0}),
            6: lambda: self.verdict("x", crons=lambda sid: True),
            7: lambda: self.verdict("x", platform_name="linux"),
            8: lambda: self.verdict("x", preflight=lambda p: ["髒"]),
        }
        for cond, run in cases.items():
            with self.subTest(cond=cond):
                before = len(self.events(forward.EV_PASS))
                out = run()
                self.assertNotEqual(out["kind"], "block")
                self.assertEqual(self.spawned, [])
                self.assertEqual(self.events(forward.EV_PASS)[before]["cond"], cond)
        # 條件 4：沒有封存戳
        self.pkg.with_suffix(".sealed").unlink()
        self.assertEqual(self.verdict("x")["kind"], "pass")
        self.assertEqual(self.events(forward.EV_PASS)[-1]["cond"], 4)
        # 條件 1：無人窗口
        with unittest.mock.patch.dict(os.environ, {"AUTOSDD_UNATTENDED": "1"}):
            self.assertEqual(self.verdict("x")["kind"], "pass")
        self.assertEqual(self.spawned, [])

    def test_task_notification_is_never_forwarded(self) -> None:
        """AT-F2／F1-8 回歸鎖 WHY：擋掉 <task-notification> 會把子代理交卷結果吞掉、主控永遠收不到。
        """
        for text in ("<task-notification>\n<task-id>x</task-id></task-notification>",
                     "  <system-reminder>x</system-reminder>", "<command-name>/x</command-name>"):
            with self.subTest(text=text[:20]):
                self.assertNotEqual(self.verdict(text)["kind"], "block")
        self.assertEqual(self.spawned, [])

    def test_pasted_content_is_forwardable_unknown_angle_wrapper_is_not(self) -> None:
        """A-6 WHY：掌舵者貼上的長指令以 <pasted_content 開頭，必須能轉；未知 `<`
        包裝判不出來就不轉。"""
        self.assertEqual(self.verdict("<pasted_content id=1>\n做這件事</pasted_content>")["kind"],
        "block")
        self.assertEqual(self.verdict("<weird>x</weird>")["kind"], "pass")

    def test_original_prompt_is_saved_verbatim_with_matching_sha256(self) -> None:
        """AT-F3 WHY：轉送的核心承諾是原文零損失——換行、CRLF、emoji、標題行、10 萬字都要逐字還原。
        """
        prompt = ("第一行\r\n## 已驗證\n  縮排與 emoji 😀🔥\n" + "長" * 100_000 + "\n結尾無換行")
        out = self.verdict(prompt)
        self.assertEqual(out["kind"], "block")
        raw = self.spawned[0]["extra_prompt_file"].read_bytes().decode("utf-8")
        head, body = raw.split(forward.BODY_MARK, 1)
        self.assertEqual(body, prompt)
        self.assertIn(hashlib.sha256(prompt.encode("utf-8")).hexdigest(), head)
        self.assertIn(f"字數：{len(prompt)}", head)

    def test_spawn_failure_passes_and_keeps_the_saved_original(self) -> None:
        """AT-F4 WHY：開新視窗失敗時不能把人的輸入吞掉；放行並留下原文檔與失敗痕跡。"""
        self.spawn_rc = 1
        out = self.verdict("重要指令")
        self.assertEqual(out["kind"], "pass")
        saved = self.pkg.with_name(f"{self.pkg.stem}.forward-abcdef01.md")
        self.assertTrue(saved.is_file())
        self.assertEqual(len(self.events(forward.EV_FAILED)), 1)
        self.assertEqual(self.events(forward.EV_SPAWNED), [])

    def test_alive_process_without_transcript_still_counts_as_forwarded(self) -> None:
        """ARCH §2.3 逾時段 WHY：spawn 回非零但新行程活著只是逐字稿慢了；
        放行會讓同一句被兩邊都處理。"""
        self.spawn_rc = 1
        out = self.verdict("指令", alive=lambda pid: pid == PID)
        self.assertEqual(out["kind"], "block")
        self.assertIn("1 分鐘", out["text"])

    def test_write_failure_of_the_original_never_blocks(self) -> None:
        """WHY：原文存不下來就不准擋（擋了就沒有任何地方留著這句話）。"""
        (self.pkg.with_name(f"{self.pkg.stem}.forward-abcdef01.md")).mkdir()
        self.assertEqual(self.verdict("指令")["kind"], "pass")
        self.assertEqual(self.spawned, [])

    def test_notify_and_non_windows_pass_with_a_spawn_hint(self) -> None:
        """AT-F5 WHY：不能自動開時要告訴掌舵者怎麼手動換，而不是靜默放行。"""
        with unittest.mock.patch.dict(os.environ, {"AUTOSDD_SESSION_SWITCH_MODE": "notify"}):
            notify = self.verdict("x")
        other = self.verdict("x", platform_name="linux")
        for out in (notify, other):
            self.assertEqual(out["kind"], "context")
            self.assertIn("handoff --spawn", out["text"])
        self.assertEqual(self.spawned, [])

    def test_def609_not_forwarding_is_shown_on_screen_with_the_reason(self) -> None:
        """DEF-200-609 WHY：真機 09:46 條件 8 放行時原因只進模型 context，掌舵者畫面一片空白、
        無從得知轉送為何沒發生。7／8 放行必須帶 `systemMessage`（畫面可見）且寫出原因。"""
        payload = {"session_id": SID, "transcript_path": str(self.transcript),
                   "prompt_id": "abcdef0123", "prompt": "測試 V-F1 轉送",
                   "hook_event_name": "UserPromptSubmit"}
        base = {"spawn": self.fake_spawn, "alive": lambda pid: False,
                "cache": lambda p, n: {"cold": True, "idle_s": 4000.0},
                "crons": lambda sid: False, "refresh": lambda p, **kw: None, "now": NOW}
        cases = {8: ({"preflight": lambda p: ["工作樹有 3 行未提交變更"], "platform_name": "win32"},
                     "工作樹有 3 行未提交變更"),
                 7: ({"preflight": lambda p: [], "platform_name": "linux"}, "linux")}
        for cond, (over, reason) in cases.items():
            with self.subTest(cond=cond):
                out = forward.hook_output(payload, os.environ, **base, **over)
                self.assertIn(reason, out["systemMessage"])
                self.assertIn("沒有自動轉到新 session", out["systemMessage"])
                self.assertIn("handoff --spawn",
                              out["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(self.spawned, [])
        # 其他放行（熱快取）維持靜默：不讓每句話都冒一行
        self.assertIsNone(forward.hook_output(
            payload, os.environ, **{**base, "cache": lambda p, n: {"cold": False}},
            preflight=lambda p: [], platform_name="win32"))

    def test_ss_48_cold_but_small_context_stays_because_resuming_is_cheaper(self) -> None:
        """R216／AT-SS-48／D9／MU-22 WHY：快取冷了，續跑重寫 2.0×c 與換新 F(1+q)＝960,000 比——c 小時
        續跑便宜，轉走反而多付（掌舵者原話：專注在不要讓 Cache 過期，不是換 session）。40 萬 ⇒ 放行
        ＋畫面一行原因（cond 10）、不 spawn；60 萬（夾具預設）⇒ 轉送；不等式反向的突變兩邊必紅。"""
        self.set_ctx(400_000)
        out = forward.hook_output(
            {"session_id": SID, "transcript_path": str(self.transcript), "prompt_id": "abcdef0123",
             "prompt": "指令", "hook_event_name": "UserPromptSubmit"}, os.environ,
            spawn=self.fake_spawn, alive=lambda pid: False,
            cache=lambda p, n: {"cold": True, "idle_s": 4000.0}, crons=lambda sid: False,
            preflight=lambda p: [], refresh=lambda p, **kw: None, platform_name="win32", now=NOW)
        self.assertIn("比換新", out["systemMessage"])
        self.assertIn("便宜", out["systemMessage"])
        self.assertEqual(self.spawned, [])
        self.assertEqual(self.events(forward.EV_PASS)[-1]["cond"], 10)
        self.set_ctx(600_000)
        self.assertEqual(self.verdict("指令")["kind"], "block")

    def test_ss_48_f4_boundary_and_unmeasurable_context(self) -> None:
        """AT-SS-48 邊界：480,000 相等不換（放行）、480,001 轉送；上下文量不到 ⇒ 放行（FRESH 會
        丟上下文，量不到不單方面造成資訊損失）。"""
        self.set_ctx(480_000)
        self.assertNotEqual(self.verdict("x")["kind"], "block")
        self.assertEqual(self.events(forward.EV_PASS)[-1]["cond"], 10)
        self.set_ctx(480_001)
        self.assertEqual(self.verdict("x")["kind"], "block")
        self.set_ctx(None)
        self.assertNotEqual(self.verdict("x")["kind"], "block")
        self.assertEqual(self.events(forward.EV_PASS)[-1]["cond"], 10)

    def test_hot_cache_stays_in_place(self) -> None:
        """AT-F6 WHY：快取熱時留下更便宜（ARCH §2.4 例二：<22 次呼叫），不轉。"""
        out = self.verdict("短追問", cache=lambda p, n: {"cold": False, "idle_s": 30.0})
        self.assertEqual(out["kind"], "pass")
        self.assertEqual(self.spawned, [])

    def test_cron_record_nonempty_or_unreadable_never_forwards(self) -> None:
        """AT-F7 WHY：本 session 還有排程要自己醒來跑，被轉走會斷掉；讀不到記錄時偏放行。"""
        for state in (True, None):
            with self.subTest(state=state):
                self.assertNotEqual(self.verdict("x", crons=lambda sid, s=state: s)["kind"],
                "block")
        self.assertEqual(self.spawned, [])

    def test_any_exception_fails_open(self) -> None:
        """WHY：守衛自己壞掉不得演變成擋住人。"""
        def boom(*a, **k):
            raise RuntimeError("x")
        self.assertEqual(self.verdict("x", spawn=boom, cache=boom)["kind"], "pass")
        self.assertEqual(forward.prompt_verdict({"prompt": 5}, os.environ)["kind"], "pass")
        self.assertIsNone(forward.hook_output("not-a-dict", os.environ))

    def test_trace_event_names_match_the_census_constants(self) -> None:
        """A-8 WHY：sessionctl 不能 import wastecensus，兩邊事件名靠本測試保持相等，
        否則量測端數不到。"""
        self.assertEqual(forward.EV_SPAWNED, sv.EV_FORWARD_SPAWNED)
        self.assertEqual(forward.EV_FAILED, sv.EV_FORWARD_FAILED)
        self.assertEqual(forward.EV_PASS, sv.EV_FORWARD_PASS)
        self.assertEqual(forward.ESCAPE_PREFIXES, ("留：", "留:"))


class PathTwoHandedOverTest(_Base):
    def setUp(self) -> None:
        super().setUp()
        self.hand_over()

    def test_new_window_alive_blocks_with_notice_and_never_spawns(self) -> None:
        """M-F3 WHY：已交棒的舊窗不該再收指令（實證 7 分鐘內被打 4 句）；說明零 token、
        原文存檔不遺失。
        開窗時刻以看的人所在時區顯示：期望值由測試獨立換算，不寫死字面（REV F1：寫死 09:05 在
        UTC 的 CI 必紅）。"""
        out = self.verdict("把Weekly用完", alive=lambda pid: pid == PID)
        self.assertEqual(out["kind"], "block")
        local_hhmm = datetime.fromisoformat(SPAWN_AT).astimezone().strftime("%H:%M")
        for word in ("已交棒", "可以關", "留：", local_hhmm, str(PID)):
            self.assertIn(word, out["text"])
        self.assertEqual(self.spawned, [])
        saved = self.pkg.with_name(f"{self.pkg.stem}.forward-abcdef01.md")
        self.assertIn("把Weekly用完", saved.read_text(encoding="utf-8"))
        self.assertEqual(self.events(forward.EV_HANDED_OVER)[-1]["outcome"], "block")

    def test_hot_cache_blocks_too(self) -> None:
        """WHY：兩個視窗同時動同一棵工作樹才是問題，與快取冷熱無關。"""
        out = self.verdict("x", alive=lambda pid: pid == PID,
                           cache=lambda p, n: {"cold": False, "idle_s": 1.0})
        self.assertEqual(out["kind"], "block")

    def test_new_window_gone_passes_with_a_status_line(self) -> None:
        """WHY：新視窗已關就不能把人擋在兩邊都沒人處理的地方。"""
        out = self.verdict("x", alive=lambda pid: False)
        self.assertEqual(out["kind"], "context")
        self.assertIn("已交棒", out["text"])

    def test_escape_prefix_task_notification_and_notify_mode_pass(self) -> None:
        """WHY：留：前綴是掌舵者的明確意圖；機器注入不擋；notify 只提醒。"""
        alive = {"alive": lambda pid: pid == PID}
        self.assertEqual(self.verdict("留：回答我", **alive)["kind"], "pass")
        self.assertEqual(self.verdict("<task-notification>x</task-notification>", **alive)["kind"],
        "pass")
        with unittest.mock.patch.dict(os.environ, {"AUTOSDD_SESSION_SWITCH_MODE": "notify"}):
            self.assertEqual(self.verdict("x", **alive)["kind"], "context")
        self.assertEqual(self.spawned, [])


def _hook(payload: dict | str, root: Path | None = None) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in _SCRUB}
    env["PYTHONUTF8"] = "1"
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run([sys.executable, str(HOOK)], input=raw, capture_output=True,
                          encoding="utf-8", errors="replace", timeout=60, check=False,
                          cwd=str(_REPO), env=env)


class HookLayerTest(_Base):
    def setUp(self) -> None:
        super().setUp()
        if not HOOK.is_file() or "UserPromptSubmit" not in HOOK.read_text(encoding="utf-8"):
            self.skipTest("hook 尚未套用 UserPromptSubmit 分支（套用前；SESSIONCTL_APPLIED_ROOT "
            "可指鏡像根）")

    def _payload(self, prompt: str) -> dict:
        return {"hook_event_name": "UserPromptSubmit", "session_id": SID, "prompt": prompt,
                "transcript_path": str(self.transcript), "prompt_id": "abcdef0123"}

    def test_malformed_input_exits_zero_and_silent(self) -> None:
        """AT-F8 WHY：hook 崩潰不得變成阻斷；壞 JSON、缺欄位、型別錯一律 rc 0 無輸出。"""
        for raw in ("not json", "{}", json.dumps({"hook_event_name": "UserPromptSubmit",
                                                  "prompt": 7})):
            with self.subTest(raw=raw[:12]):
                proc = _hook(raw)
                self.assertEqual((proc.returncode, proc.stdout.strip()), (0, ""), proc.stderr)

    def test_task_notification_through_the_real_hook_is_silent(self) -> None:
        """AT-F2 hook 層 WHY：跳板零判準，仍要證明機器注入不會被誤擋。"""
        self.hand_over()
        proc = _hook(self._payload("<task-notification>x</task-notification>"))
        self.assertEqual((proc.returncode, proc.stdout.strip()), (0, ""), proc.stderr)

    def test_handed_over_window_gets_block_json_without_spawning(self) -> None:
        """路徑二 hook 層 WHY：用本行程 pid 當「新視窗」（活著），證明輸出形態是 harness 認的 block
        JSON。"""
        switch.trace("session_switch_spawned", pid=os.getpid(), handoff=str(self.pkg),
                     at=NOW.isoformat(), ok=True)
        self.pkg.with_suffix(".ack").write_text("ok\n", encoding="utf-8")
        proc = _hook(self._payload("所以這個視窗可以關了對嗎?"))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        doc = json.loads(proc.stdout)
        if sys.platform == "win32":
            self.assertEqual(doc["decision"], "block")
            self.assertIn("已交棒", doc["reason"])
        else:  # 非 Windows 判不出新視窗活著 ⇒ 只附一行說明
            self.assertEqual(doc["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")


class RegistrationTest(unittest.TestCase):
    def test_user_prompt_submit_registered_exec_form_with_timeout_50(self) -> None:
        """WHY：註冊面 fail-open——漏註冊整個轉送靜默失效；timeout 須大於 spawn 等待 20 秒。"""
        settings_path = GUARD_ROOT / ".claude" / "settings.json"
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        entries = (settings.get("hooks") or {}).get("UserPromptSubmit")
        if not entries:
            self.skipTest("settings 尚未註冊 UserPromptSubmit（套用前）")
        mine = [h for e in entries for h in e["hooks"]
                if "sessionctl_guard.py" in (h.get("args") or [""])[-1]]
        self.assertEqual(len(mine), 1)
        self.assertTrue(mine[0]["args"][0].endswith("_hook_launcher.py"))
        self.assertEqual(mine[0]["timeout"], 50)


if __name__ == "__main__":
    unittest.main()
