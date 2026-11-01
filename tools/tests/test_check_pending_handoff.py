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


if __name__ == "__main__":
    unittest.main()
