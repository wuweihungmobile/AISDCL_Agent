"""`.claude/hooks/check_pending_handoff.py` 的回歸鎖（根 CLAUDE.md〈收尾常態規則〉的機械物）。

四組：① 純函式 `pending_handoff_hits` 紅綠（含立案那一則與普查抓到的假紅形態）；
② `asked_this_turn` 的回合邊界；③ 子行程真跑：阻斷形態、`stop_hook_active` 煞車、
無人值守與逃生口、逐字稿缺席 fail-open；④ 登記面與回合邊界詞彙和姊妹檔對帳。
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOK = _REPO_ROOT / ".claude" / "hooks" / "check_pending_handoff.py"
_SIBLING = _REPO_ROOT / ".claude" / "hooks" / "check_claim_provenance.py"
_SETTINGS = _REPO_ROOT / ".claude" / "settings.json"

#: 立案那一則（sid 655d9777 line 8657）的收尾句；句內另有「沒有」，整句否定判會把它靜音。
_INCIDENT = ("CI 補報：四支 workflow 全部綠。handback 已更新為最終狀態；本輪沒有未結工作，"
             "只剩前一則提到的兩件人工決定（三份多餘稽核檔是否刪除、V2 對話框停用的真機目視）。")


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _user(text: str, kind: str = "human") -> str:
    return json.dumps({"type": "user", "origin": {"kind": kind},
                       "message": {"role": "user", "content": text}}, ensure_ascii=False)


def _tool_result() -> str:
    return json.dumps({"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]}}, ensure_ascii=False)


def _assistant(text: str = "", ask: bool = False, sidechain: bool = False) -> str:
    blocks: list = []
    if text:
        blocks.append({"type": "text", "text": text})
    if ask:
        blocks.append({"type": "tool_use", "name": "AskUserQuestion", "id": "t1", "input": {}})
    return json.dumps({"type": "assistant", "isSidechain": sidechain,
                       "message": {"role": "assistant", "content": blocks}}, ensure_ascii=False)


def _transcript(tmp: Path, lines: list[str]) -> Path:
    path = tmp / "sid.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


class TestPendingHandoffJudgement(unittest.TestCase):
    """`.claude/hooks/check_pending_handoff.py::pending_handoff_hits` 純函式紅綠自證。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.hook = _load(_HOOK)

    def test_the_incident_sentence_is_red_despite_the_negation_elsewhere(self) -> None:
        hits = self.hook.pending_handoff_hits(_INCIDENT)
        self.assertEqual([h["word"] for h in hits], ["人工決定"], hits)

    def test_each_handoff_form_is_red(self) -> None:
        for claim in ("## 請掌舵者處理的兩件小事", "**待您處理或另排**", "## 需要您拍板（三項）",
                      "髒檔照慣例留給您。", "V2 真機目視待掌舵者。", "等您有空再做。"):
            with self.subTest(claim=claim):
                self.assertTrue(self.hook.pending_handoff_hits(claim), claim)

    def test_negation_next_to_the_word_is_green(self) -> None:
        self.assertEqual(self.hook.pending_handoff_hits("目前沒有任何事卡在等您。"), [])
        self.assertEqual(self.hook.pending_handoff_hits("不需要您做任何事。"), [])

    def test_permission_k1_interactive_and_quoted_forms_are_green(self) -> None:
        for claim in ("需要您核准寫入該檔案的權限。",
                      "現在只等您兩句話：",
                      "請您打「晉升」，一則一個。",
                      "這個決定須掌舵者親打。",
                      "屆時用互動選項請您決定。",
                      "不採信備忘錄裡的「待您處理」字樣。"):
            with self.subTest(claim=claim):
                self.assertEqual(self.hook.pending_handoff_hits(claim), [], claim)

    def test_block_message_names_both_exits_and_the_switch(self) -> None:
        msg = self.hook.block_message([{"word": "待您", "sentence": "x"}])
        for token in ("AskUserQuestion", "須掌舵者親打", "AUTOSDD_HANDOFF_GUARD_OFF", "待您"):
            self.assertIn(token, msg)


class TestSecondPersonVocabulary(unittest.TestCase):
    """`.claude/hooks/check_pending_handoff.py::pending_handoff_hits`：
    「你」系列交棒詞（AT-PK-74～75）。
    WHY：2026-11-15 事故收尾寫「是否輪替仍由你決定」——詞表只認「您」，同義的「你」整句漏網。
    🔴 AT-PK-74 在 staged hook 套用前紅屬預期（`.claude/` 由主控套用）。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.hook = _load(_HOOK)

    def test_at_pk_74_second_person_handoffs_are_red(self) -> None:
        for claim in ("`BRIDGE_SI_WRITE_TOKEN` 是否輪替仍由你決定。", "待你處理", "留給你",
                      "交給你", "需要你", "你來決定"):
            with self.subTest(claim=claim):
                self.assertTrue(self.hook.pending_handoff_hits(claim), claim)

    def test_everyday_second_person_narration_stays_green(self) -> None:
        """「請你」「等你」不收：真實面普查 214 回合裡它們造成 3 回合假紅（事後敘述，不是交棒）。
        額度停工等人這一類由 park 的結構判準守，不靠詞表。"""
        for claim in ("結果我反而請你回到這個舊視窗", "結果就是等你回來，快取早已過期"):
            with self.subTest(claim=claim):
                self.assertEqual(self.hook.pending_handoff_hits(claim), [], claim)

    def test_at_pk_75_negated_quoted_and_k1_second_person_forms_are_green(self) -> None:
        for claim in ("你不需要做任何事", "你可以隨時回來看", "沒有任何事卡在等你", "不用等你",
                      "「由你決定」字樣是舊稿的寫法", "這個決定須掌舵者親打，由你決定也行"):
            with self.subTest(claim=claim):
                self.assertEqual(self.hook.pending_handoff_hits(claim), [], claim)


class TestAskedThisTurn(unittest.TestCase):
    """`.claude/hooks/check_pending_handoff.py::asked_this_turn` 的回合邊界。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.hook = _load(_HOOK)

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="w-handoff-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_a_question_in_this_turn_counts(self) -> None:
        path = _transcript(self.tmp, [_user("做"), _assistant(ask=True), _tool_result(),
                                      _assistant("待您決定。")])
        self.assertTrue(self.hook.asked_this_turn(str(path)))

    def test_a_question_in_an_earlier_turn_does_not_count(self) -> None:
        path = _transcript(self.tmp, [_user("做"), _assistant(ask=True), _tool_result(),
                                      _assistant("好。"), _user("再做"), _assistant("待您決定。")])
        self.assertFalse(self.hook.asked_this_turn(str(path)))

    def test_harness_turns_are_not_boundaries_but_sdk_turns_are(self) -> None:
        notice = json.dumps({"type": "user", "origin": {"kind": "task-notification"},
                             "message": {"role": "user", "content": "<task-notification>x"}})
        path = _transcript(self.tmp, [_user("做"), _assistant(ask=True), notice,
                                      _assistant("待您。")])
        self.assertTrue(self.hook.asked_this_turn(str(path)))
        path = _transcript(self.tmp, [_user("做"), _assistant(ask=True), _user("再", "sdk"),
                                      _assistant("待您。")])
        self.assertFalse(self.hook.asked_this_turn(str(path)))

    def test_a_sidechain_question_does_not_count(self) -> None:
        path = _transcript(self.tmp, [_user("做"), _assistant(ask=True, sidechain=True),
                                      _assistant("待您。")])
        self.assertFalse(self.hook.asked_this_turn(str(path)))

    def test_unreadable_or_oversized_transcripts_raise_instead_of_answering(self) -> None:
        with self.assertRaises(OSError):
            self.hook.asked_this_turn(str(self.tmp / "missing.jsonl"))
        path = _transcript(self.tmp, [_user("做"), _assistant("待您。")])
        with self.assertRaises(ValueError):
            self.hook.asked_this_turn(str(path), byte_cap=1)


class TestStopHookWiring(unittest.TestCase):
    """`.claude/hooks/check_pending_handoff.py` 子行程真跑：阻斷、煞車、逃生口、fail-open、登記。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="w-handoff-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.transcript = _transcript(self.tmp, [_user("做"), _assistant(_INCIDENT)])

    def _run(self, claim: str = _INCIDENT, active: bool = False, env: dict | None = None,
             transcript: str | None = None):
        payload = json.dumps({"hook_event_name": "Stop", "stop_hook_active": active,
                              "session_id": "sid-handoff", "last_assistant_message": claim,
                              "transcript_path": transcript or str(self.transcript)})
        child = {k: v for k, v in os.environ.items()
                 if k not in ("AUTOSDD_UNATTENDED", "AUTOSDD_HANDOFF_GUARD_OFF")}
        child.update({"CLAUDE_PROJECT_DIR": str(_REPO_ROOT), "PYTHONUTF8": "1",
                      "AUTOSDD_TRACE_DIR": str(self.tmp / "tr"), **(env or {})})
        return subprocess.run([sys.executable, str(_HOOK)], input=payload, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=60, env=child)

    def test_a_prose_handoff_without_a_question_is_pushed_back_once(self) -> None:
        done = self._run()
        self.assertEqual(done.returncode, 0, done.stderr)
        doc = json.loads(done.stdout)
        self.assertEqual(doc["decision"], "block")
        self.assertIn("AskUserQuestion", doc["reason"])
        self.assertIn("systemMessage", doc)
        trace = self.tmp / "tr" / "handoff_block.jsonl"
        self.assertTrue(trace.exists(), "阻斷必須留痕跡（沒觸發＝檔不長大）")

    def test_the_second_stop_and_a_question_in_the_turn_are_silent(self) -> None:
        self.assertEqual(self._run(active=True).stdout, "")
        asked = _transcript(self.tmp, [_user("做"), _assistant(ask=True), _assistant(_INCIDENT)])
        self.assertEqual(self._run(transcript=str(asked)).stdout, "")

    def test_the_switch_and_unattended_are_silent(self) -> None:
        self.assertEqual(self._run(env={"AUTOSDD_HANDOFF_GUARD_OFF": "1"}).stdout, "")
        self.assertEqual(self._run(env={"AUTOSDD_UNATTENDED": "1"}).stdout, "")

    def test_a_missing_transcript_fails_open(self) -> None:
        done = self._run(transcript=str(self.tmp / "missing.jsonl"))
        self.assertEqual((done.returncode, done.stdout), (0, ""))

    def test_a_clean_closing_message_is_silent(self) -> None:
        done = self._run(claim="任務完成，CI 全綠；目前沒有任何事卡在等您。")
        self.assertEqual((done.returncode, done.stdout), (0, ""))

    def test_registered_under_stop_in_exec_form(self) -> None:
        settings = json.loads(_SETTINGS.read_text(encoding="utf-8-sig"))
        found = [h for group in settings["hooks"]["Stop"] for h in group["hooks"]
                 if ".claude/hooks/check_pending_handoff.py" in h.get("args", [])]
        self.assertEqual(len(found), 1, "必須恰登記一次於 Stop")
        self.assertTrue(found[0]["args"][0].endswith("_hook_launcher.py"))
        self.assertTrue(found[0]["command"].endswith("pythonw.exe"))

    def test_turn_boundary_vocabulary_matches_the_sibling_hook(self) -> None:
        hook, sibling = _load(_HOOK), _load(_SIBLING)
        self.assertEqual(hook._OPERATOR_TURN_ORIGINS, sibling._OPERATOR_TURN_ORIGINS)
        self.assertEqual(hook._HARNESS_BODY_PREFIXES, sibling._HARNESS_BODY_PREFIXES)


def _assistant_tool(name: str, text: str = "") -> str:
    blocks: list = [{"type": "tool_use", "name": name, "id": "t9", "input": {}}]
    if text:
        blocks.insert(0, {"type": "text", "text": text})
    return json.dumps({"type": "assistant", "isSidechain": False,
                       "message": {"role": "assistant", "content": blocks}}, ensure_ascii=False)


#: 2026-11-17 真機事故原話（sid 16496139）：說「接著派下一棒」就結束回合，沒有任何背景工作。
_MIDWORK = "親驗通過，已記進計畫檔，現查額度後派下一棒。"


class TestMidworkWording(unittest.TestCase):
    """`.claude/hooks/check_pending_handoff.py::midwork_hits`：「我接下來還要做事」措辭那一半。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.hook = _load(_HOOK)

    def test_the_incident_sentence_and_progressive_forms_are_red(self) -> None:
        for claim in (_MIDWORK, "接著跑全套測試。", "接下來派 QA 審查。", "下一步推送並等 CI。",
                      "稍後提交。", "我立刻續做。", "目前正在進行第二棒。",
                      "這不是收尾，還有一棒。",
                      "接著重跑根層全套，再做護欄重釘。", "我接著 push、對帳。",
                      "等交卷再接著親驗。"):
            with self.subTest(claim=claim):
                self.assertTrue(self.hook.midwork_hits(claim), claim)

    def test_summaries_headings_quotes_negation_and_other_owners_are_green(self) -> None:
        for claim in ("任務完成，CI 全綠，commit 已推送。", "## 下一步確切指令",
        "下一步請掌舵者決定。",
                      "不會接著做任何事。", "沒有下一步要派。",
                      "不採信備忘錄裡的「接著派下一棒」字樣。",
                      "下一步由新 session 接手。", "接下來要做哪件事？", "立即可派的修復棒已備妥。",
                      "你打完後我會接著跑 decide，請你再親打一次。",
                      "額度重置後說一聲「繼續」，我接著做。",
                      "守衛：若主控說接下來還要做事，就機械推回一次。"):
            with self.subTest(claim=claim):
                self.assertEqual(self.hook.midwork_hits(claim), [], claim)

    def test_legitimate_handoff_markers_silence_the_whole_reply(self) -> None:
        for claim in (_MIDWORK + "\n已執行 handoff --spawn。", _MIDWORK + " PARK_VERDICT=armed",
                      _MIDWORK + " python tools/sessionctl.py park 已掛。",
                      _MIDWORK + " 交接包已封存。"):
            with self.subTest(claim=claim):
                self.assertEqual(self.hook.midwork_hits(claim), [], claim)


class TestMidworkStopWiring(unittest.TestCase):
    """`.claude/hooks/check_pending_handoff.py` 半路停工判準的子行程真跑（狀態為主、措辭為輔）。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="w-midwork-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.dirty = self.tmp / "dirty"
        self.clean = self.tmp / "clean"
        for repo, files in ((self.dirty, True), (self.clean, False)):
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True,
                           timeout=60)
            if files:
                (repo / "a.txt").write_text("x", encoding="utf-8")
        self.plain = self.tmp / "plain"  # 非 git 目錄：量不到
        self.plain.mkdir()
        self.work = _transcript(self.tmp, [_user("做"), _assistant_tool("Edit"),
        _assistant(_MIDWORK)])
        self.readonly = self.tmp / "readonly.jsonl"
        self.readonly.write_text("\n".join([_user("做"), _assistant_tool("Read"),
                                            _assistant(_MIDWORK)]) + "\n", encoding="utf-8")

    def _run(self, claim: str = _MIDWORK, *, cwd: Path | None = None,
    transcript: Path | None = None,
             tasks="absent", active: bool = False, env: dict | None = None):
        doc = {"hook_event_name": "Stop", "stop_hook_active": active, "session_id": "sid-mw",
               "last_assistant_message": claim, "cwd": str(cwd or self.dirty),
               "transcript_path": str(transcript or self.work)}
        if tasks != "absent":
            doc["background_tasks"] = tasks
        child = {k: v for k, v in os.environ.items()
                 if k not in ("AUTOSDD_UNATTENDED", "AUTOSDD_HANDOFF_GUARD_OFF")}
        child.update({"CLAUDE_PROJECT_DIR": str(_REPO_ROOT), "PYTHONUTF8": "1",
                      "AUTOSDD_TRACE_DIR": str(self.tmp / "tr"), **(env or {})})
        return subprocess.run([sys.executable, str(_HOOK)], input=json.dumps(doc),
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=60, env=child)

    def test_incident_with_no_background_work_and_a_dirty_tree_is_pushed_back(self) -> None:
        done = self._run(tasks=[])
        self.assertEqual(done.returncode, 0, done.stderr)
        doc = json.loads(done.stdout)
        self.assertEqual(doc["decision"], "block")
        for token in ("沒有任何背景工作", "handoff --finalize", "park", "AskUserQuestion"):
            self.assertIn(token, doc["reason"])
        trace = (self.tmp / "tr" / "handoff_block.jsonl").read_text(encoding="utf-8")
        self.assertIn("midwork_stop_block", trace)

    def test_a_running_background_task_or_a_finished_one_decides_correctly(self) -> None:
        running = [{"id": "a1", "type": "subagent", "status": "running"}]
        self.assertEqual(self._run(tasks=running).stdout, "")
        self.assertEqual(self._run(tasks={"id": "s1", "type": "shell", "status": "running"}).stdout,
        "")
        finished = [{"id": "a1", "type": "subagent", "status": "completed"}]
        self.assertEqual(json.loads(self._run(tasks=finished).stdout)["decision"], "block")

    def test_a_missing_background_tasks_field_is_fail_open(self) -> None:
        self.assertEqual(self._run().stdout, "")

    def test_every_other_guard_condition_is_silent(self) -> None:
        self.assertEqual(self._run(tasks=[], active=True).stdout, "")
        self.assertEqual(self._run(tasks=[], env={"AUTOSDD_UNATTENDED": "1"}).stdout, "")
        self.assertEqual(self._run(tasks=[], env={"AUTOSDD_HANDOFF_GUARD_OFF": "1"}).stdout, "")
        asked = self.tmp / "asked.jsonl"
        asked.write_text("\n".join([_user("做"), _assistant_tool("Edit"), _assistant(ask=True),
                                    _assistant(_MIDWORK)]) + "\n", encoding="utf-8")
        self.assertEqual(self._run(tasks=[], transcript=asked).stdout, "")
        self.assertEqual(self._run(_MIDWORK + " 已執行 handoff --spawn。", tasks=[]).stdout, "")

    def test_a_plain_summary_is_silent_even_with_a_dirty_tree(self) -> None:
        self.assertEqual(self._run("任務完成，全部驗證通過，commit 已推送。", tasks=[]).stdout, "")

    def test_state_evidence_clean_tree_with_readonly_tools_is_silent(self) -> None:
        self.assertEqual(self._run(tasks=[], cwd=self.clean, transcript=self.readonly).stdout, "")

    def test_state_evidence_either_a_dirty_tree_or_a_work_tool_suffices(self) -> None:
        # 乾淨樹但本回合做過 Edit ⇒ 推回；髒樹但本回合只讀 ⇒ 推回；兩者都量不到 ⇒ 不判
        self.assertEqual(json.loads(self._run(tasks=[], cwd=self.clean).stdout)["decision"],
        "block")
        self.assertEqual(json.loads(self._run(tasks=[],
        transcript=self.readonly).stdout)["decision"],
                         "block")
        self.assertEqual(self._run(tasks=[], cwd=self.plain, transcript=self.readonly).stdout, "")

    def test_both_criteria_at_once_produce_one_merged_reason(self) -> None:
        both = "只剩兩件人工決定。" + _MIDWORK
        doc = json.loads(self._run(both, tasks=[]).stdout)
        self.assertEqual(doc["decision"], "block")
        self.assertIn("人工決定", doc["reason"])
        self.assertIn("沒有任何背景工作", doc["reason"])

    def test_an_unreadable_transcript_fails_open(self) -> None:
        done = self._run(tasks=[], transcript=self.tmp / "missing.jsonl")
        self.assertEqual((done.returncode, done.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
