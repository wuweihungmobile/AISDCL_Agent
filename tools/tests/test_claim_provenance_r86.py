#!/usr/bin/env python3
"""`.claude/hooks/check_claim_provenance.py` 的回歸鎖（`DEF-200-103`）。

守的是什麼（Rule 9）：被守的判準治的是 `misstep_attribution.py` 連兩輪量到的最大
非-OTHER 失誤桶 `CLAIM-FIRST`（宣稱先於查證）——該桶發生的平面是「宣稱本身」，永不
變成 repo 裡的檔案 ⇒ 靜態掃描器結構上看不見它，所以本鎖每一條壞掉時都是**靜默的**。

🔴 **立案敘事（三組判準各自對應哪一個已實測發生過的失效方向、以及為何凍結成字面樣本
而不是測試時重讀逐字稿）已逐字搬至** `docs/06_quality/CrossPlatform_R86_Guard_Repin_Evidence.md`
**§C**；本輪動用棘輪自己指定的「把 WHY 與史料搬出護欄層」出口以兌現淨額 ≤ 0 的到期義務。
per-assertion 的 WHY **未搬動**，仍在各 class／method 的 docstring 內。
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOK = _REPO_ROOT / ".claude" / "hooks" / "check_claim_provenance.py"


def _load():
    """以檔案路徑載入 hook（**不**經 import 機制：`sys.path` 上沒有 `.claude/hooks/`）。"""
    spec = importlib.util.spec_from_file_location("_claim_guard", _HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


G = _load()

#: 一段「本場真的跑過」的工具輸出。判準比對的是**值**，所以這裡只要含那些數字即可。
_OWN_OUTPUT = "3748 passed, 146 skipped\nrc=0\n377 passed\n44 skipped"  # baseline-ok:語料


# 🔴 **刻意不在本檔驗「hook 檔存在」與「Stop 兩個載具都在」**（本批以雙向注入實測後移除）。
# 兩者都已有既有鎖在守，重寫一份就是同一份知識住兩個家、而只有一個家會被改：
#   · 拔掉 Stop 的 POSIX 載具 ⇒ `test_check_hooks_liveness.py` 的
#     `TestExecFormConversionScope::test_every_active_settings_file_passes_the_form_criteria`
#     與 `TestHookEntriesAreExecForm::test_real_settings_is_all_exec_form` 實測轉紅（rc=1）。
#   · 把 hook 檔移走 ⇒ 同檔 `TestHookRegistrationScopeIsShrinkOnly::
#     test_baseline_scripts_all_exist_on_disk` 實測轉紅（rc=1）。
# 那兩道鎖的分母是**現查磁碟的註冊集合**，本檔新增的條目自動落進它們的射程，
# 所以本檔只需守「判準本體」與「程序層契約」——註冊面不是本檔的職責。


class TestItCatchesTheRelayedNumber(unittest.TestCase):
    """鑑別力：真實面普查 13 筆命中裡有 12 筆是這一型（把別包交件的數字當自己的話講）。

    這些樣本是從本機逐字稿抽出後**去識別並改寫**過的形態樣本，不是原文。
    """

    RELAYED = (
        "修復包 2 完成，全套測試 1703 passed / 0 failed。",  # baseline-ok:語料
        "跨平台掃描完成（AutoClaude 3701 passed）。",  # baseline-ok:語料
        "修復專家 C 也完工：根層 unittests 244 OK、新守門真 repo 已綠。",
        "全 FSM runtime 套件 1714 passed 無回歸。",  # baseline-ok:語料
    )

    def test_a_number_with_no_source_in_my_own_output_is_flagged(self) -> None:
        for sentence in self.RELAYED:
            with self.subTest(sentence=sentence):
                hits = G.unsourced_verdict_hits(sentence, _OWN_OUTPUT)
                self.assertTrue(
                    hits, f"{sentence!r} 的數字在本場工具輸出裡沒有出處，卻沒被指出來")

    def test_the_same_number_is_silent_once_it_really_is_in_my_output(self) -> None:
        """對照組：同一個判決、數字真的來自本場輸出 ⇒ 必須不命中。

        沒有這一條，「判準永遠命中」與「判準有鑑別力」的 rc 一模一樣。
        """
        self.assertEqual(
            G.unsourced_verdict_hits("回歸 3748 passed。", _OWN_OUTPUT), [])  # baseline-ok:語料


class TestTheMeasuredFalsePositiveShapesStayGreen(unittest.TestCase):
    """假紅是這道鎖的生死線——凡在此的形態都**實測過**會被誤判。"""

    def test_a_thousands_separator_still_matches_the_plain_output(self) -> None:
        """`3,748 passed` 與輸出裡的 `3748` 必須對得上。  # baseline-ok:語料

        不做正規化時 `\\b(\\d+)` 只抓到 `748`，於是每一個上千的測試數都變成假紅——
        而本 repo 的宣稱幾乎都是上千的測試數 ⇒ 這一條沒守住，判準等於全噪音。
        """
        self.assertEqual(
            G.unsourced_verdict_hits("回歸 3,748 passed。", _OWN_OUTPUT), [])  # baseline-ok:語料

    def test_an_attributed_relay_is_the_desired_behaviour_not_a_violation(self) -> None:
        """標了出處的轉述必須放行——命中它等於處罰正解，而正解是本判準要換到的行為。"""
        for sentence in ("`[他包回報]` 全套 9999 passed。",  # baseline-ok:語料
                         "QA 回報 9999 passed，本包未重跑。",  # baseline-ok:語料
                         "C9 宣稱 10 道閘門全 rc=7。"):
            with self.subTest(sentence=sentence):
                self.assertEqual(G.unsourced_verdict_hits(sentence, _OWN_OUTPUT), [],
                                 f"{sentence!r} 已標出處卻被判違規")


class TestThousandsNormalisationDoesNotFuseNeighbours(unittest.TestCase):
    """正規化只准吃**數字之間的半角逗號**。

    第一版連全角「，」一起吃 ⇒ `rc=0，44 skip` 被併成 `rc=044`，判準自己生出一筆假紅。
    這一條守的是「修假紅的動作不要製造新假紅」。
    """

    def test_a_full_width_comma_is_not_a_thousands_separator(self) -> None:
        self.assertEqual(G.normalize_digits("rc=0，44 skip"), "rc=0，44 skip")
        self.assertEqual(
            G.unsourced_verdict_hits("rc=0，44 skip 全為 platform。", _OWN_OUTPUT), [])

    def test_a_half_width_comma_between_digits_is_one(self) -> None:
        self.assertEqual(G.normalize_digits("3,748"), "3748")

    def test_a_half_width_comma_not_between_digits_survives(self) -> None:
        """`a, 1` 這種列舉逗號不得被吃掉，否則會把不相鄰的數字黏成一個值。"""
        self.assertEqual(G.normalize_digits("gates, 3 passed"), "gates, 3 passed")


class TestUnattendedRunsGetTheNarrowMarkerSet(unittest.TestCase):
    """無人看管時，抑制詞縮到只認方括號標記。

    立案：句子裡塞一個「宣稱」就能讓判準閉嘴，而無人看管的回合可以自己寫出那兩個字
    （同 `# git-guard-ok:` 的已知弱點與其 `AUTOSDD_UNATTENDED` 處置）。方括號那兩個
    字面在 `docs/04_planning/` 有成文定義、亂標會在收輪對帳時被逐列核出來。
    """

    def test_a_soft_marker_stops_suppressing_when_unattended(self) -> None:
        sentence = "QA 宣稱 9999 passed。"  # baseline-ok:語料
        self.assertEqual(G.unsourced_verdict_hits(sentence, _OWN_OUTPUT), [])
        self.assertTrue(
            G.unsourced_verdict_hits(sentence, _OWN_OUTPUT, unattended=True),
            "無人看管時『宣稱』不得再構成抑制——否則模型可以自己寫出豁免")

    def test_the_bracket_marker_still_suppresses_when_unattended(self) -> None:
        self.assertEqual(
            G.unsourced_verdict_hits("`[他包回報]` 9999 passed。", _OWN_OUTPUT,  # baseline-ok:語料
                                     unattended=True), [])


class TestTheProcessNeverBlocksAndAlwaysFailsOpen(unittest.TestCase):
    """程序層契約：**一律 exit 0**。

    這是本檔最重要的一組。Stop hook 若回 exit 2 會把回合推回模型手上，而本判準治的是
    「話講得太滿」不是「工作沒做完」——推回去只會生出更多話；且阻斷迴圈的唯一煞車是
    `stop_hook_active`。再加上 `.claude/settings.json` description 記載過的 P0：
    hook 誤觸 deny 會把所有工具硬鎖死。
    """

    def _run(self, payload: str, env_extra: dict | None = None):
        env = {**os.environ, **(env_extra or {})}
        return subprocess.run([sys.executable, str(_HOOK)], input=payload,
                              capture_output=True, text=True, env=env, timeout=60,
                              encoding="utf-8", errors="replace")

    def test_every_degraded_payload_exits_zero_and_says_nothing(self) -> None:
        """壞 JSON／空輸入／缺欄位三種退化 payload 一律靜默放行。

        刻意**不**採 fail-closed：Stop 是每一則回覆都會經過的路徑，對讀不出內容的
        payload 出聲會變成「一個永遠在響的警報」。
        """
        for payload in ("", "not json", "{}", '{"last_assistant_message":"x"}'):
            with self.subTest(payload=payload):
                done = self._run(payload)
                self.assertEqual(done.returncode, 0, f"{payload!r} 未 fail-open")
                self.assertEqual(done.stderr.strip(), "",
                                 f"{payload!r} 不該出聲（退化 payload 無可判之事）")

    def test_a_real_violation_speaks_on_stderr_but_still_exits_zero(self) -> None:
        payload = json.dumps({
            "hook_event_name": "Stop",
            "last_assistant_message": "收工：99991 passed 全綠。",  # baseline-ok:語料
            "transcript_path": str(_HOOK),  # 任一存在且不含該數字的檔即可當證據面
        })
        done = self._run(payload)
        self.assertEqual(done.returncode, 0, "本守衛永不阻斷")
        self.assertIn("99991", done.stderr, "真違規必須指名是哪個數字")

    def test_the_escape_hatch_silences_it_completely(self) -> None:
        payload = json.dumps({
            "hook_event_name": "Stop",
            "last_assistant_message": "收工：99991 passed。",  # baseline-ok:語料
            "transcript_path": str(_HOOK),
        })
        done = self._run(payload, {"AUTOSDD_CLAIM_GUARD_OFF": "1"})
        self.assertEqual(done.returncode, 0)
        self.assertEqual(done.stderr.strip(), "")

    def test_the_escape_hatch_is_not_shared_with_the_other_guards(self) -> None:
        """逃生口刻意不共用：共用一個會讓「我只是想暫時別被唸」順手關掉別的保護。

        🔴 判準問的是「本檔**讀**了哪些環境變數」，所以取樣面必須是 **AST 的
        `os.environ.get(...)` 站點**，不是整份檔案的文字。拿整份文件當 haystack 去斷言
        某字樣不出現，會在檔案**合法地**提到那個字樣時假紅（本 repo 的
        `test_check_defect_log_crossref.py` 內
        `test_no_root_test_asserts_absence_against_a_whole_live_document`
        釘住這個反模式，且記載過它曾逼得帳本改寫自己的缺陷描述）——本檔的檔頭正是要
        逐字說明「為何不與那幾個變數共用」，文字面判準會把那段說明本身判成違規。
        """
        read_names = {
            node.args[0].value
            for node in ast.walk(ast.parse(_HOOK.read_text(encoding="utf-8")))
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute) and node.func.attr == "get"
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "environ"
            and node.args and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        }
        self.assertIn("AUTOSDD_CLAIM_GUARD_OFF", read_names,
                      "本守衛必須有自己的逃生口")
        for foreign in ("AUTOSDD_GIT_GUARD_OFF", "AUTOSDD_CONTEXT_GUARD_OFF",
                        "AUTOSDD_SENTINEL_OFF"):
            self.assertNotIn(foreign, read_names,
                             f"不得**讀** {foreign} 當本守衛的開關（共用會讓一次關閉波及別的守衛）")


class TestTruncationBiasesTowardsSilenceNotFalseRed(unittest.TestCase):
    """證據面取不到時必須**放行**，不得判違規。

    方向性很關鍵：命中的定義是「值在證據面裡找不到」⇒ 證據面愈小、命中愈多。所以
    截斷／讀不到一律偏向假紅，而假紅會讓這道鎖被整個關掉。
    """

    def test_an_oversized_transcript_makes_the_hook_stay_quiet(self) -> None:
        with self.assertRaises(ValueError):
            G._tool_output_digits(str(_HOOK), byte_cap=1)

    def test_that_raise_is_swallowed_into_a_silent_pass_at_process_level(self) -> None:
        """上一條的 raise 必須被 `main()` 吃掉成靜默放行，而不是變成 traceback。"""
        payload = json.dumps({
            "hook_event_name": "Stop",
            "last_assistant_message": "9999 passed。",  # baseline-ok:語料
            "transcript_path": "/nonexistent/does/not/exist.jsonl",
        })
        done = subprocess.run([sys.executable, str(_HOOK)], input=payload,
                              capture_output=True, text=True, timeout=60,
                              encoding="utf-8", errors="replace")
        self.assertEqual(done.returncode, 0)
        self.assertEqual(done.stderr.strip(), "")


#: R89 事故的字面樣本：機器吐出來的那句話，與主控把它當成機制結論的那一句。
_MACHINE_SAID = "API Error: You've hit your monthly spend limit · raise it at claude.ai"
_INCIDENT = ("R87 的真實形狀是：主池被 13 個並發衝爆，而衝爆後後備池沒了 ⇒ "
             "報 `monthly spend limit`。")


class TestTheR89ErrorLiteralMechanismJudgement(unittest.TestCase):
    """`DEF-200-123`：把**錯誤訊息的字面**當成機制結論。

    守的是什麼：那句假前提被寫進交棒書、多個 commit，還當成前提餵給 Architect ⇒ 整段
    分析建立在假前提上；而真相是那個量**連續 15 列都是 100.0＝常數**，不可能是變因。
    本判準治**形態**，內容那一半治在 `tools/probe/variate_contrast.py`。
    """

    def test_the_incident_sentence_is_flagged(self) -> None:
        """缺陷復發即紅——沒有這一條，整支判準可以恆回 `[]` 而 rc 一模一樣。"""
        hits = G.error_literal_mechanism_hits(_INCIDENT, _MACHINE_SAID)
        self.assertTrue(hits, "事故原句未被指出來")
        self.assertEqual(hits[0]["literal"], "monthly spend limit")

    def test_the_corrected_sentence_with_a_contrast_word_is_silent(self) -> None:
        """對照組＝掌舵者訂正後我自己寫下的**正解**，命中它就是處罰正解。
        普查實測：抑制詞在全母體只擋掉這一句 ⇒ 只擋正解、不減損鑑別力。"""
        self.assertEqual(G.error_literal_mechanism_hits(
            "`monthly spend limit` 全程都是滿的 ⇒ 它是常數，不可能是變因。",
            _MACHINE_SAID), [])

    def test_a_literal_the_machine_never_said_is_silent(self) -> None:
        """問的是「這串字是不是機器吐給你的」——沒在工具輸出裡出現就不是。
        少了這一條，判準會變成「不准在結論裡引述任何英文」，那是另一回事。"""
        self.assertEqual(G.error_literal_mechanism_hits(_INCIDENT, "rc=0 全綠"), [])

    def test_symbols_are_not_messages(self) -> None:
        """普查裡 10 筆假陽性有 8 筆是這一型 ⇒ 精確率 23%→100% 全靠這一條。
        寫「⇒ `ModuleNotFoundError`」的人是在指認他**推理出來的**失效模式，不是在轉述
        機器的散文。符號的記號＝詞內大寫／`.`／`_`／`:`／只有一個詞。"""
        for symbol in ("ModuleNotFoundError", "WinError 216", "DeadlineExceeded",
                       "subprocess.TimeoutExpired",
                       "TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound"):
            with self.subTest(symbol=symbol):
                self.assertEqual(
                    G.error_literal_mechanism_hits(f"打包沒宣告 ⇒ `{symbol}`。",
                                                   f"log: {symbol} raised"),
                    [], f"{symbol!r} 是符號不是訊息，不該命中")

    def test_an_ordinary_mechanism_sentence_stays_silent(self) -> None:
        """全母體 1,474 句機制結論句只命中 3 筆——沒有這一條就量不出那個分母有沒有意義。"""
        self.assertEqual(G.error_literal_mechanism_hits(
            "根因是 `_defer_bootout` 寫死的 sleep 3。", _MACHINE_SAID), [])


class TestTheCausalEscapeHatchIsItsOwn(unittest.TestCase):
    """兩個判準各自一個逃生口——共用會讓「別唸我這件事」順手關掉另一件。"""

    def setUp(self) -> None:
        """造一支**真的逐字稿**當證據面：證據只認 `tool_result` 區塊，隨便給支 `.py`
        會讓工具輸出是空的，於是「機器說過那句話」這個前提在測試裡不成立（實測）。"""
        self._dir = tempfile.TemporaryDirectory()
        self.transcript = Path(self._dir.name) / "t.jsonl"
        self.transcript.write_text(json.dumps({"message": {"role": "user", "content": [
            {"type": "tool_result", "content": _MACHINE_SAID}]}}) + "\n",
            encoding="utf-8")
        self.addCleanup(self._dir.cleanup)

    def _payload(self) -> str:
        return json.dumps({"hook_event_name": "Stop",
                           "last_assistant_message": _INCIDENT,
                           "transcript_path": str(self.transcript)})

    def test_it_speaks_on_stderr_but_still_exits_zero(self) -> None:
        done = subprocess.run([sys.executable, str(_HOOK)], input=self._payload(),
                              capture_output=True, text=True, timeout=60,
                              encoding="utf-8", errors="replace")
        self.assertEqual(done.returncode, 0, "本守衛永不阻斷")
        self.assertIn("monthly spend limit", done.stderr)
        self.assertIn("variate_contrast.py", done.stderr, "必須指出查證只要一行")

    def test_turning_off_the_causal_guard_leaves_the_other_one_armed(self) -> None:
        """關掉因果判準之後，值域判準必須**還在**——否則兩個逃生口只是名字不同。"""
        env = {**os.environ, "AUTOSDD_CAUSAL_GUARD_OFF": "1"}
        payload = json.dumps({
            "hook_event_name": "Stop",
            "last_assistant_message": _INCIDENT + " 全套 99991 passed。",  # baseline-ok: 合成語料
            "transcript_path": str(self.transcript)})
        done = subprocess.run([sys.executable, str(_HOOK)], input=payload, env=env,
                              capture_output=True, text=True, timeout=60,
                              encoding="utf-8", errors="replace")
        self.assertEqual(done.returncode, 0)
        self.assertNotIn("錯誤訊息的字面", done.stderr, "逃生口沒有真的關掉本判準")
        self.assertIn("99991", done.stderr, "另一個判準被順手關掉了")


if __name__ == "__main__":
    unittest.main()
