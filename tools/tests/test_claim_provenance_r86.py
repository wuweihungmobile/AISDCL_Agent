#!/usr/bin/env python3
"""`.claude/hooks/check_claim_provenance.py` 的回歸鎖（`DEF-200-103`）。

守的是什麼（Rule 9）：被守的判準治的是 `misstep_attribution.py` 連兩輪量到的最大
非-OTHER 失誤桶 `CLAIM-FIRST`（宣稱先於查證）——該桶發生的平面是「宣稱本身」，永不
變成 repo 裡的檔案 ⇒ 靜態掃描器結構上看不見它，所以本鎖每一條壞掉時都是**靜默的**。

🔴 立案敘事已逐字搬至 `docs/06_quality/CrossPlatform_R86_Guard_Repin_Evidence.md`
§C（棘輪自訂淨額 ≤0 出口）；per-assertion WHY 未搬，仍在各 class／method docstring 內。
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import types
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOK = _REPO_ROOT / ".claude" / "hooks" / "check_claim_provenance.py"
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
import quota_policy  # noqa: E402  # DEF-200-477：簡報夾具走真的 `quota_line()`（writer==reader）
import session_brief  # noqa: E402


def _load():
    """以檔案路徑載入 hook（**不**經 import 機制：`sys.path` 上沒有 `.claude/hooks/`）。"""
    spec = importlib.util.spec_from_file_location("_claim_guard", _HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


G = _load()

#: 一段「本場真的跑過」的工具輸出。判準比對的是**值**，所以這裡只要含那些數字即可。
_OWN_OUTPUT = "3748 passed, 146 skipped\nrc=0\n377 passed\n44 skipped"  # baseline-ok:語料

#: `PACE_AXES` 裡不在 `quota_policy.KNOWN_KINDS` 的軸——**登記的例外，只准變小**。
_AXES_OUTSIDE_KNOWN_KINDS = frozenset({"nimbus_quill"})

#: 第三個判準的固定「現在」。用固定時刻而不是 `datetime.now()`：age 是判準的輸入，
#: 讓它隨牆上時鐘漂移＝把測試變成非決定性的（本 repo 對脆弱綠有判例）。
_NOW = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)


def _hook_env(extra: dict | None = None) -> dict:
    """建子行程環境：先濾掉本檔 hook 自己的逃生口再疊 `extra`（洩漏會噤聲判準，DEF-200-349）。"""
    hatches = {
        "AUTOSDD_UNATTENDED",
        "AUTOSDD_CLAIM_GUARD_OFF",
        "AUTOSDD_NAKED_GUARD_OFF",
        "AUTOSDD_CAUSAL_GUARD_OFF",
        "AUTOSDD_BLOCK_CLAIM_GUARD_OFF",
        "AUTOSDD_PACE_GUARD_OFF",
        "AUTOSDD_CARRIER_GUARD_OFF",
    }
    return {**{k: v for k, v in os.environ.items() if k not in hatches}, **(extra or {})}


def _hook_env_reads() -> set[str]:
    """AST 掃描 `_HOOK`：回傳所有 `os.environ.get("...")` 讀到的環境變數字面名。"""
    return {
        node.args[0].value
        for node in ast.walk(ast.parse(_HOOK.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute) and node.func.attr == "get"
        and isinstance(node.func.value, ast.Attribute)
        and node.func.value.attr == "environ"
        and node.args and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    }


# 🔴 **刻意不在本檔驗「hook 檔存在」與「Stop 兩個載具都在」**（本批以雙向注入實測後移除）。
# 實測紀錄搬至 CrossPlatform_R204_StopHook_Negation_FalsePositive_Fix_Evidence.md〈附錄 B〉§1。


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
        return subprocess.run([sys.executable, str(_HOOK)], input=payload,
                              capture_output=True, text=True, env=_hook_env(env_extra),
                              timeout=60, encoding="utf-8", errors="replace")

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
        read_names = _hook_env_reads()
        self.assertIn("AUTOSDD_CLAIM_GUARD_OFF", read_names,
                      "本守衛必須有自己的逃生口")
        for foreign in ("AUTOSDD_GIT_GUARD_OFF", "AUTOSDD_CONTEXT_GUARD_OFF",
                        "AUTOSDD_SENTINEL_OFF"):
            self.assertNotIn(foreign, read_names,
                             f"不得**讀** {foreign} 當本守衛的開關（共用會讓一次關閉波及別的守衛）")

    def test_a_leaked_claim_guard_off_does_not_silence_the_value_judgement(self) -> None:
        """巢狀鎖（DEF-200-349）：拿掉 `_hook_env()` 對 os.environ 的過濾，這支會紅。"""
        payload = json.dumps({"hook_event_name": "Stop", "transcript_path": str(_HOOK),
                              "last_assistant_message": "收工：99991 passed。"})  # baseline-ok:語料
        with mock.patch.dict(os.environ, {"AUTOSDD_CLAIM_GUARD_OFF": "1"}):
            done = self._run(payload)
        self.assertIn("99991", done.stderr, "呼叫端洩漏的 AUTOSDD_CLAIM_GUARD_OFF=1 噤聲了真違規")


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

    事故敘事搬至 CrossPlatform_R204_StopHook_Negation_FalsePositive_Fix_Evidence.md〈附錄 B〉§2。
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
                              capture_output=True, text=True, env=_hook_env(), timeout=60,
                              encoding="utf-8", errors="replace")
        self.assertEqual(done.returncode, 0, "本守衛永不阻斷")
        self.assertIn("monthly spend limit", done.stderr)
        self.assertIn("variate_contrast.py", done.stderr, "必須指出查證只要一行")

    def test_turning_off_the_causal_guard_leaves_the_other_one_armed(self) -> None:
        """關掉因果判準之後，值域判準必須**還在**——否則兩個逃生口只是名字不同。"""
        payload = json.dumps({
            "hook_event_name": "Stop",
            "last_assistant_message": _INCIDENT + " 全套 99991 passed。",  # baseline-ok: 合成語料
            "transcript_path": str(self.transcript)})
        env = _hook_env({"AUTOSDD_CAUSAL_GUARD_OFF": "1"})
        done = subprocess.run([sys.executable, str(_HOOK)], input=payload, env=env,
                              capture_output=True, text=True, timeout=60,
                              encoding="utf-8", errors="replace")
        self.assertEqual(done.returncode, 0)
        self.assertNotIn("錯誤訊息的字面", done.stderr, "逃生口沒有真的關掉本判準")
        self.assertIn("99991", done.stderr, "另一個判準被順手關掉了")


# ─────────────────────────────────────────────────────────────────────────────
# 第三個判準（本輪 M1~M8）：引述一個已經過期的額度讀數
# ─────────────────────────────────────────────────────────────────────────────

def _pace_line(axis: str = "session", pct: str = "16") -> str:
    """一行**看起來就是 pace 輸出**的讀數（判準要求同行帶 pace 欄位記號）。"""
    return f"kind={axis} {pct}% 剩 128 分鐘 band=free horizon=mid cap=8"


class TestTheEscapeHatchIsArithmeticNotPresence(unittest.TestCase):
    """🔴 **本組是本輪否決權複審 M2＋M4 的直接產物，斷言方向刻意與規格版相反。**

    規格版紅綠自證被否決的經過搬至 Guard_Line_History_2.md〈R194 淨減法搬遷〉§129。  round-label-ok

    所以這裡的契約是：**時間戳自己過期 ⇒ 仍命中，且訊息要帶出它的 age**；只有「真的剛量」
    才靜音。第二條（真的剛量 → 靜音）是逃生口該有的紅綠自證，缺它就無法證明抑制器有
    鑑別力而不是恆真。
    """

    def _hits(self, minutes_ago: float, *, axis: str = "session"):
        now = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)
        stamp = (now - timedelta(minutes=minutes_ago)).isoformat()
        claim = f"{_pace_line(axis)}｜來源=cache 量測於={stamp}"
        return G.stale_pace_hits(claim, [], now)

    def test_a_four_hour_old_self_quoted_stamp_still_gets_flagged(self) -> None:
        """事故形狀本身：貼上四小時前的量測時刻**不是**豁免。"""
        hits = self._hits(240)
        self.assertEqual([h["kind"] for h in hits], ["stale"],
                         "貼一個過期的『量測於』被當成豁免了——那正是立案的事故")
        self.assertGreater(hits[0]["age_s"], 4 * 3600 - 60,
                           "訊息必須帶出那個時刻自己的 age，否則讀者不知道它有多舊")

    def test_the_message_says_how_old_the_reading_actually_is(self) -> None:
        """M3：訊息不得只說「過期了」，要說**過期多久**（age 是可行動的唯一資訊）。"""
        messages = G._pace_messages(self._hits(240))
        self.assertTrue(messages, "四小時前的讀數必須產出訊息")
        self.assertIn("240 分鐘前", messages[0])

    def test_a_stamp_that_really_is_fresh_is_the_silent_case(self) -> None:
        """逃生口該有的紅綠自證：真的剛量過 ⇒ 回空清單。

        沒有這一條，上一條可以靠「抑制器恆假」通過——那不是逃生口，是把它拿掉。
        """
        self.assertEqual(self._hits(0.5), [],
                         "剛量到的讀數被判過期了 ⇒ 這個守衛會擋到讓人無法工作")

    def test_the_boundary_is_the_axis_own_measured_ttl(self) -> None:
        """門檻必須是**那個軸自己的** TTL，不是一個全域數字（M5）。

        `session` 的 TTL 約兩分鐘、`seven_day` 約 23 分鐘 ⇒ 同一個 age（10 分鐘）在快軸上
        必須命中、在慢軸上必須靜音。單一門檻的代價是量出來的：複審實測 35% 的發火只由慢軸
        貢獻，而慢軸的中位漂移比快軸低一個數量級。
        """
        self.assertEqual([h["kind"] for h in self._hits(10, axis="session")], ["stale"])
        self.assertEqual(self._hits(10, axis="seven_day"), [],
                         "慢軸被快軸的門檻誤判 ⇒ 這就是單一門檻製造的那 35% 假紅")


class TestTheMessageMustNotTeachThePresenceLoophole(unittest.TestCase):
    """M3：訊息本身就是行為的教材，寫錯一句就把讀者訓練成用繞過 7。"""

    def test_it_tells_you_to_rerun_not_merely_to_paste_a_timestamp(self) -> None:
        now = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)
        claim = f"{_pace_line()}｜量測於={(now - timedelta(hours=4)).isoformat()}"
        message = G._pace_messages(G.stale_pace_hits(claim, [], now))[0]
        self.assertIn("重跑", message, "沒有叫人重跑＝在教『把舊區塊貼上就好』")
        self.assertIn("--pace", message, "必須給出確切指令，否則不可行動")
        self.assertIn("算 age", message,
                      "必須明說抑制是算術的——不說就等於默許『貼上即抑制』的誤解")


class TestPerAxisThresholdsAreDerivedNotPicked(unittest.TestCase):
    """M5：TTL 必須是**導出式的輸出**，不是有人挑的秒數。"""

    def test_every_ttl_is_exactly_one_pp_of_that_axis_measured_drift(self) -> None:
        """判準：`TTL == round(3600 / 該軸實測中位漂移)`。

        這一條會在「有人直接改秒數」時轉紅——那是本組存在的唯一理由：一個挑出來的門檻
        沒有辦法被複審，而一個導出來的門檻只要重新量就能重新裁決。
        """
        for axis, ttl in G.PACE_TTL_S.items():
            with self.subTest(axis=axis):
                rate = G.PACE_DRIFT_MEDIAN_PP_PER_HOUR[axis]
                self.assertEqual(ttl, round(3600.0 / rate))

    def test_axes_measured_as_not_drifting_are_registered_not_judged(self) -> None:
        """中位漂移 0 的軸**不得**有 TTL（含「無上界」那種寫法）。

        複審給了兩條路：導出 per-axis TTL，或**照實登記已量測的假紅類別**。本檔走後者，
        而且刻意不採信「那個讀數在物理上不會過期」——同一份重跑實測 `weekly_scoped`
        p90=9.375、max=31.034 pp/hr ⇒ 它會動。判它是假紅，宣稱它不會過期是假話。
        """
        zero = [a for a, r in G.PACE_DRIFT_MEDIAN_PP_PER_HOUR.items() if r == 0]
        self.assertTrue(zero, "沒有零漂移軸的話這一條就沒有守到東西")
        for axis in zero:
            self.assertNotIn(axis, G.PACE_TTL_S)
            self.assertEqual(G.stale_pace_hits(_pace_line(axis, "61"), [], _NOW), [])

    def test_the_two_axis_tables_inside_the_hook_cannot_drift_apart(self) -> None:
        """觸發表與漂移表必須逐格對齊：多在一邊＝那個軸靜默失去 TTL 或靜默失去觸發。"""
        self.assertEqual(set(G.PACE_AXES), set(G.PACE_DRIFT_MEDIAN_PP_PER_HOUR))

    def test_axes_outside_the_quota_policy_ssot_are_named_not_silent(self) -> None:
        """軸名字面允許住兩個家的唯一條件＝有東西在對帳（本檔就是那個東西）。

        差集刻意**釘成具名集合而不是空集合**：`nimbus_quill` 是伺服器真的會吐、而 PRD 任何
        列舉都沒有的桶（`quota_policy.py` 的 `KNOWN_KINDS` 旁註逐字記載這件事，並指出它
        今天已經在參與 cap 聚合）⇒ hook 認得它是對的。把差集斷言成空集合會逼下一個人
        「為了讓紅變綠」把那個軸從 hook 拿掉，而那是**縮小守衛的射程**去迎合一個鎖。
        """
        sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
        import quota_policy  # noqa: PLC0415

        self.assertEqual(set(G.PACE_AXES) - set(quota_policy.KNOWN_KINDS),
                         _AXES_OUTSIDE_KNOWN_KINDS,
                         "hook 與 quota_policy 的軸名差集變了 ⇒ 兩個家漂移了，"
                         "請確認新軸是伺服器真的吐的，再把它加進本例外集合")


class TestTheTriggerCoversTheMeasuredBypasses(unittest.TestCase):
    """M6：規避形態必須是**量出來**才收或才不收，不是憑感覺挑。"""

    def test_a_full_width_percent_sign_does_not_silence_the_guard(self) -> None:
        """全角 `％` 一個按鍵就能永久靜音整支守衛 ⇒ 覆蓋成本一個字元，收。"""
        claim = "kind=session 16％ 剩 128 分鐘 band=free"
        self.assertEqual([h["kind"] for h in G.stale_pace_hits(claim, [], _NOW)],
                         ["unanchored"])

    def test_the_axis_to_value_window_is_wide_enough_for_real_prose(self) -> None:
        """距離窗實測 p90=38 ⇒ 窗寬 40。規格挑的 8 只覆蓋 68.7%（本輪重跑）。"""
        self.assertGreaterEqual(G.PACE_VALUE_WINDOW, 38)
        claim = "kind=session（5 小時窗，binding 那一軸）已用 16% band=free"
        self.assertTrue(G.stale_pace_hits(claim, [], _NOW),
                        f"距離 {claim.index('16') - claim.index('session')} 字元就漏抓了")

    def test_a_bare_number_is_a_registered_bypass_not_an_oversight(self) -> None:
        """「軸 ＋ 裸數字」刻意不判，而這一條就是那個裁決的落款。

        量出來的理由：裸數字的母體是帶 `%` 的 **2.66 倍**（696 vs 418 次），而它的距離
        p50=29（帶 `%` 的是 2）⇒ 那個數字**通常根本不是這個軸的值**。判它會讓觸發面暴增
        且多數是雜訊，而「一個永遠在響的警報等於沒有警報」本 repo 已有判例。
        """
        self.assertEqual(G.stale_pace_hits("kind=session 16 剩 128 分鐘", [], _NOW), [],
                         "裸數字若開始命中，請先重跑普查再改這一條")


class TestAPercentBindsToItsOwnAxisNotToOneAcrossAnotherAxis(unittest.TestCase):
    """軸名與百分比之間夾著**另一個軸名**時，那個百分比屬於後者（跨軸誤綁定）。
    敘事搬至 CrossPlatform_R204_StopHook_Negation_FalsePositive_Fix_Evidence.md〈附錄 B〉§3。"""

    _CROSSED = "binding 軸是（`seven_day`，剩 988 分鐘；`session` 是 13%）"
    _OUTPUT = "kind=session 13% 剩 128 分鐘 band=free\nkind=seven_day 95% 剩 988 分鐘 band=halt"

    def _hits(self, claim: str, age: timedelta | None):
        stamped = [] if age is None else [(_NOW - age, self._OUTPUT)]
        return [(h["axis"], h["value"], h["kind"]) for h in G.stale_pace_hits(claim, stamped, _NOW)]

    def test_a_faithful_quote_across_another_axis_name_is_not_flagged(self) -> None:
        self.assertEqual(self._hits(self._CROSSED, timedelta(seconds=10)), [],
                         "13% 是 session 的值、錨點也在——正確引述不得被唸成找不到錨點")

    def test_each_axis_followed_by_its_own_percent_binds_as_before(self) -> None:
        claim = "kind=session 13% 剩 128 分鐘；kind=seven_day 95% 剩 988 分鐘"
        self.assertEqual(self._hits(claim, None),
                         [("session", "13", "unanchored"), ("seven_day", "95", "unanchored")])
        self.assertEqual(self._hits(claim, timedelta(seconds=10)), [])

    def test_a_reading_that_really_has_no_anchor_is_still_flagged_with_its_own_axis(self) -> None:
        self.assertEqual(self._hits(self._CROSSED, None), [("session", "13", "unanchored")],
                         "錨不到的真讀數必須仍被點名，而且綁到它自己的軸")

    def test_a_stale_reading_across_another_axis_name_is_still_stale(self) -> None:
        self.assertEqual(self._hits(self._CROSSED, timedelta(hours=4)),
                         [("session", "13", "stale")],
                         "綁錯軸會讓四小時前的真讀數被降級成 unanchored（漏判）")


class TestTheUnanchoredBlindSpotIsCountedNotHidden(unittest.TestCase):
    """M7：「錨不到＝放行」製造反向誘因（照實引述舊數字被唸、憑空捏一個不會）。

    判準無法在散文平面上分辨「捏的」與「輸出被截斷」，所以這裡守的不是「抓到它」，
    是**它有數字**——盲區可數才可能在下一輪被裁決。
    """

    def test_an_unanchorable_reading_is_its_own_class_not_silently_dropped(self) -> None:
        hits = G.stale_pace_hits(_pace_line("session", "77"), [], _NOW)
        self.assertEqual([h["kind"] for h in hits], ["unanchored"])
        self.assertIsNone(hits[0]["age_s"], "錨不到就沒有 age，不得編一個出來")

    def test_the_blind_spot_count_reaches_the_reader_without_anyone_running_a_probe(
            self) -> None:
        """M8：痕跡通道必須有**自動讀者**，否則它不是機制。

        本輪複審現查：全庫 trace 的唯一讀者是一支要人記得跑的手動 probe ⇒ 那個數字只在
        有人想起來時才存在。這一條釘的就是「寫進去的同一次執行就讀回來、並出現在送給模型
        的那則訊息裡」。誠實劃界：它只讀自己寫的那一份、只出聲，**沒有任何閘門會因為這個
        數字轉紅**——那需要一個穩定的分母，本機母體不是。
        """
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("AUTOSDD_TRACE_DIR")
            os.environ["AUTOSDD_TRACE_DIR"] = tmp
            try:
                hits = G.stale_pace_hits(_pace_line("session", "77"), [], _NOW)
                first = G._pace_messages(hits)
                second = G._pace_messages(hits)
            finally:
                if old is None:
                    os.environ.pop("AUTOSDD_TRACE_DIR", None)
                else:
                    os.environ["AUTOSDD_TRACE_DIR"] = old
            written = Path(tmp) / G.FRESHNESS_TRACE
            self.assertTrue(written.is_file(), "盲區沒有落痕跡 ⇒ 它不可數")
            self.assertIn("unanchored", written.read_text(encoding="utf-8"),
                          "盲區必須是**自己一類**，混進總數等於沒登記")
            self.assertIn("錨不到 1 筆", first[0], "第一次就必須把累計數讀回來")
            self.assertIn("錨不到 2 筆", second[0],
                          "第二次沒有累加 ⇒ 那個『讀回』其實沒有在讀檔")

    def test_nothing_to_say_means_the_trace_file_does_not_grow(self) -> None:
        """「沒觸發＝檔不長大」是本 repo 對痕跡的既有語意，也是它可偵測的前提。"""
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("AUTOSDD_TRACE_DIR")
            os.environ["AUTOSDD_TRACE_DIR"] = tmp
            try:
                self.assertEqual(G._pace_messages([]), [])
            finally:
                if old is None:
                    os.environ.pop("AUTOSDD_TRACE_DIR", None)
                else:
                    os.environ["AUTOSDD_TRACE_DIR"] = old
            self.assertFalse((Path(tmp) / G.FRESHNESS_TRACE).exists())


class TestTheModelChannelIsClampedOnStopHookActive(unittest.TestCase):
    """M1：這個夾具**不是優化**——沒有它，守衛會在額度吃緊的那一刻自己燒額度。
    敘事搬至 CrossPlatform_R204_StopHook_Negation_FalsePositive_Fix_Evidence.md〈附錄 B〉§4。"""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.transcript = Path(self._dir.name) / "t.jsonl"
        self.transcript.write_text("", encoding="utf-8")

    def _run(self, *, active: bool):
        payload = json.dumps({
            "hook_event_name": "Stop", "stop_hook_active": active,
            "last_assistant_message": _pace_line("session", "77"),
            "transcript_path": str(self.transcript)})
        env = _hook_env({"AUTOSDD_TRACE_DIR": self._dir.name})
        return subprocess.run([sys.executable, str(_HOOK)], input=payload, env=env,
                              capture_output=True, text=True, timeout=60,
                              encoding="utf-8", errors="replace")

    def test_the_first_stop_really_reaches_the_model(self) -> None:
        done = self._run(active=False)
        self.assertEqual(done.returncode, 0)
        self.assertIn("hookSpecificOutput", done.stdout,
                      "沒有發射 ⇒ 訊息不在行為迴圈裡（stderr 進不了 context）")
        self.assertIn('"hookEventName": "Stop"', done.stdout,
                      "事件名與實際事件不符時 CC 會把整個 additionalContext 丟掉")

    def test_the_re_entrant_stop_says_nothing_to_the_model(self) -> None:
        """紅綠自證的另一半：夾具必須真的夾得住，否則上一條只是證明它會發射。"""
        done = self._run(active=True)
        self.assertEqual(done.returncode, 0)
        self.assertEqual(done.stdout.strip(), "",
                         "stop_hook_active 下仍發射 ⇒ 迴圈沒有煞車，這支守衛會自己燒額度")
        self.assertIn("錨不到", done.stderr, "夾住的是模型通道，不是整個判準")


class TestThePaceGuardHasItsOwnEscapeHatch(unittest.TestCase):
    """第三個逃生口同樣不共用——共用會讓一次關閉波及別的守衛。"""

    def test_turning_off_the_pace_guard_leaves_the_value_guard_armed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            transcript = Path(tmp) / "t.jsonl"
            transcript.write_text("", encoding="utf-8")
            payload = json.dumps({
                "hook_event_name": "Stop",
                "last_assistant_message":
                    _pace_line("session", "77") + " 收工：99991 passed。",  # baseline-ok: 合成語料
                "transcript_path": str(transcript)})
            env = _hook_env({"AUTOSDD_PACE_GUARD_OFF": "1", "AUTOSDD_TRACE_DIR": tmp})
            done = subprocess.run([sys.executable, str(_HOOK)], input=payload, env=env,
                                  capture_output=True, text=True, timeout=60,
                                  encoding="utf-8", errors="replace")
        self.assertEqual(done.returncode, 0)
        self.assertNotIn("錨不到", done.stderr, "逃生口沒有真的關掉本判準")
        self.assertIn("99991", done.stderr, "另一個判準被順手關掉了")


class TestTheSessionStartBriefIsAnAnchorForTheStaleReadingJudgement(unittest.TestCase):
    """DEF-200-477（受測：hook 的 `_session_start_anchors`／`_pace_anchors`／`main()` 接線）。

    WHY：新視窗第一回合的額度數字只在 SessionStart 簡報（hook attachment，非 tool_result）裡，
    第三判準的錨點此前只認 tool_result ⇒ 如實轉述也被唸「找不到任何錨點」並多跑一回合。反方向
    一起守，否則簡報當錨點就成了新的隨機靜音器：憑空數字、值不符、過期轉述、降級簡報、別的
    hook 事件都仍要出聲；第五判準對簡報的排除（DEF-200-430）不動。
    """

    _CLAIM = "session 27%（band=free）"

    @staticmethod
    def _brief(note: str = "") -> str:
        """真 `session_brief.quota_line()` 對 27% 新鮮讀數印的額度行（writer==reader）＋ `note`。"""
        axis = quota_policy.Axis("session", 27.0, (_NOW + timedelta(hours=2)).isoformat())
        state = quota_policy.QuotaState((axis,), _NOW.isoformat(), "cache", "ok")
        gate = types.SimpleNamespace(quota_policy=quota_policy, policy_env=dict,
                                     read_quota=lambda now, path=None: state)
        return "[SDD-CTX-GUARD] 額度：" + session_brief.quota_line(gate, _NOW) + note

    @staticmethod
    def _record(text: str, at: datetime = _NOW, event: str = "SessionStart") -> dict:
        return {"timestamp": at.isoformat(), "attachment": {
            "type": "hook_additional_context", "hookEvent": event, "content": [text]}}

    def _kinds(self, after: timedelta, records: list, claim: str = _CLAIM) -> list[str]:
        """與 `main()` 同一條：錨點池 → `stale_pace_hits`；`now`＝簡報落款＋`after`。"""
        pool = G._pace_anchors([], records)
        return [h["kind"] for h in G.stale_pace_hits(claim, pool, _NOW + after)]

    def test_a_faithful_relay_of_a_fresh_brief_is_silent(self) -> None:
        """T1：照實轉述剛送達的簡報——被處罰的正解，也就是立案形態。"""
        self.assertEqual(self._kinds(timedelta(seconds=60), [self._record(self._brief())]), [],
                         "如實轉述簡報數字仍被判找不到錨點 ⇒ DEF-200-477 復發")

    def test_the_same_relay_hours_later_is_stale_not_unanchored(self) -> None:
        """T2：簡報當錨點不等於永久免罰——落款過了 TTL 照樣出聲，且帶得出 age。"""
        pool = G._pace_anchors([], [self._record(self._brief())])
        hits = G.stale_pace_hits(self._CLAIM, pool, _NOW + timedelta(hours=4))
        self.assertEqual([(h["kind"], h["axis"]) for h in hits], [("stale", "session")])
        self.assertEqual(hits[0]["age_s"], 4 * 3600 + G._BRIEF_ANCHOR_LAG_S)

    def test_a_number_the_brief_never_said_stays_unanchored(self) -> None:
        """T3：憑空數字（沒有簡報）與值不符（簡報 27%、轉述 61%）都仍判錨不到。"""
        self.assertEqual(self._kinds(timedelta(seconds=60), []), ["unanchored"])
        self.assertEqual(self._kinds(timedelta(seconds=60), [self._record(self._brief())],
                                     "session 61%（band=free）"), ["unanchored"])

    def test_a_later_tool_result_beats_the_older_brief(self) -> None:
        """錨點取**最新**那筆：簡報之後重跑 `--pace` 量到同一個值，引述它不是過期讀數。"""
        later = _NOW + timedelta(hours=4)
        remeasured = [(later - timedelta(seconds=30), "kind=session 27% 剩 90 分鐘 band=free")]
        pool = G._pace_anchors(remeasured, [self._record(self._brief())])
        self.assertEqual(G.stale_pace_hits(self._CLAIM, pool, later), [],
                         "簡報（四小時前）蓋過了更新的量測 ⇒ 錨點池沒有依時刻排序")

    def test_only_an_undegraded_session_start_brief_anchors(self) -> None:
        """T4：自陳『退化政策值』的簡報不是量測值；別的事件的 hook 通知（含本 hook 自己上一則
        警報＝`Stop`）也不得當錨點，否則警報自己洗白下一次引述。"""
        cases = {f"降級附註 {note[:8]}": self._record(self._brief(note))
                 for note in (session_brief._STALE_CACHE_NOTE, session_brief._UNMEASURED_NOTE)}
        cases.update({f"hookEvent={event}": self._record(self._brief(), event=event)
                      for event in ("Stop", "PostToolUse", "PreToolUse")})
        for label, record in cases.items():
            with self.subTest(label):
                self.assertEqual(self._kinds(timedelta(seconds=60), [record]), ["unanchored"])

    def test_the_conservative_variant_is_one_constant(self) -> None:
        """偏差上界的保守解：錨點往前推一個快取 TTL ⇒ 組出 100 秒的簡報，讀數可能已 280 秒舊。"""
        records = [self._record(self._brief())]
        self.assertEqual(self._kinds(timedelta(seconds=100), records), [])
        with mock.patch.object(G, "_BRIEF_ANCHOR_LAG_S", 180):
            self.assertEqual(self._kinds(timedelta(seconds=100), records), ["stale"])

    def test_the_fifth_judgement_and_the_degraded_marker_are_untouched(self) -> None:
        """T5：簡報照舊進不了第五判準的佐證面（DEF-200-430）；hook 就地寫死的降級字面與簡報同源。"""
        self.assertEqual(G._block_evidence_text([self._record(self._brief())]), "")
        for note in (session_brief._STALE_CACHE_NOTE, session_brief._UNMEASURED_NOTE):
            self.assertIn(G._BRIEF_DEGRADED, note, "簡報改了降級附註字面 ⇒ 降級簡報會被當成錨點")

    def test_the_hook_process_reads_the_brief_from_the_real_transcript(self) -> None:
        """接線鎖：`main()` 真的把簡報餵進第三判準（上面只證明 `_pace_anchors` 本身是對的）。
        借鄰班的 `_run`：多一個 subprocess 站點就得重釘 `_CHILD_SITE_FLOOR`。"""
        now = datetime.now(UTC)
        with tempfile.TemporaryDirectory() as tmp:
            transcript = Path(tmp) / "t.jsonl"

            def say(*records: dict) -> str:
                transcript.write_text("".join(json.dumps(r) + "\n" for r in records),
                                      encoding="utf-8")
                done = TestTheUnbackedBlockClaimHookWiring._run(
                    self, self._CLAIM, transcript, {"AUTOSDD_TRACE_DIR": tmp})
                self.assertEqual(done.returncode, 0, "本守衛永不阻斷")
                return done.stderr

            fresh = say(self._record(self._brief(), now - timedelta(seconds=20)))
            self.assertNotRegex(fresh, "找不到任何錨點|已經過期",
                                "新鮮簡報沒被當錨點 ⇒ main() 沒接上")
            self.assertIn("已經過期", say(self._record(self._brief(), now - timedelta(hours=4))))
            self.assertIn("找不到任何錨點", say(), "對照組：沒有簡報＝修前的行為")


# ─────────────────────────────────────────────────────────────────────────────
# 第四個判準：不帶值的完工判決 ＋ 本場零佐證動作（`WakeChain_IronLaws_Verification.md`
# 規則 8 的破洞）
# ─────────────────────────────────────────────────────────────────────────────

#: 立案句：`docs/06_quality/WakeChain_IronLaws_Verification.md` 第四節規則 8 那一列**逐字
#: 記載**它在修復前是 `rc=0、stderr/stdout 完全空白`（本輪落地前重放實測確認）。
_NAKED = "完成：全部修復完畢，已驗證，全綠，零損失。"

#: 全母體實測的 **3 筆假紅**（單一判決詞）。逐字留樣：這三句是判準必須**保持靜默**的
#: 形態，`NAKED_MIN_TOKENS` 由 1 改成 2 的全部理由就是它們。
_SINGLE_WORD_FALSE_REDS = (
    "我來幫你完成從 Windows 切到 Mac 的切換程序。",
    "2. **任務書磁碟化** — 寫明已驗證什麼、未做什麼、下一步確切指令",
    "R104 交接書尚未讀取，先核實內容再決定下一步，"
    "不採信備忘錄裡的「已驗證」字樣。",
)

#: 全母體實測 **57 句**堆疊型宣稱裡的真實樣本（去識別後保留形態）。它們全部發生在
#: **有**工具輸出的場次 ⇒ 必須靜默。這一組守的是「常態不得被當成違規」。
_BACKED_WRAP_UPS = (
    "收尾完成，10 道閘門全綠。",
    "收尾包完成：全套 3435 tests 全綠（rc=0），18 筆紅歸零。",  # baseline-ok:語料
    "**規則6（喚醒鏈自動續跑）修復：完成，已驗證**",
)


class TestTheNakedVerdictWithNoEvidenceIsFlagged(unittest.TestCase):
    """規則 8 的破洞本體：**不帶值**的完工判決 ＋ 本場一次工具輸出都沒有。
    敘事搬至 CrossPlatform_R204_StopHook_Negation_FalsePositive_Fix_Evidence.md〈附錄 B〉§5。"""

    def test_the_incident_sentence_with_zero_tool_output_is_flagged(self) -> None:
        """缺陷復發即紅。沒有這一條，整支判準可以恆回 `[]` 而 rc 一模一樣。"""
        hits = G.naked_verdict_hits(_NAKED, "")
        self.assertTrue(hits, "赤裸宣稱（零 tool_result）沒被指出來")
        self.assertEqual(hits[0]["tokens"],
                         ["全綠", "完成", "完畢", "已驗證", "零損失"],
                         "訊息必須指名是哪幾個詞堆疊起來的")

    def test_the_same_sentence_is_silent_once_the_session_really_ran_something(
            self) -> None:
        """🔴 對照組＝**正常收工**（有貼真實輸出、句尾說了完成）。

        這一條是本組的生死線：把它判紅就是把本 repo 的常態當違規，而
        `audit_session.py` 自陳「不得接成閘門」的原因正是它那個判準會這樣做
        （實測：往回看 3 個 tool_result 的證據面 ⇒ 28.4% 判無佐證）。
        """
        self.assertEqual(G.naked_verdict_hits(_NAKED, _OWN_OUTPUT), [],
                         "本場真的跑過工具卻被判赤裸宣稱 ⇒ 這道守衛會被整個關掉")

    def test_real_backed_wrap_ups_from_the_corpus_stay_silent(self) -> None:
        """全母體 57 句堆疊型宣稱**全部**發生在有工具輸出的場次 ⇒ 全部必須靜默。

        那個 57 就是鑑別力的憑證：57 → 0 是**證據面**在抑制，不是詞表在挑。
        """
        for sentence in _BACKED_WRAP_UPS:
            with self.subTest(sentence=sentence):
                self.assertEqual(G.naked_verdict_hits(sentence, _OWN_OUTPUT), [],
                                 f"{sentence!r} 是有佐證的常態，命中它等於處罰正解")

    def test_a_single_verdict_word_is_a_registered_bypass_not_an_oversight(
            self) -> None:
        """`NAKED_MIN_TOKENS` 的紅綠自證：實測 3 筆單一詞假紅必須靜默。

        三筆的成因是結構性的（意圖動詞／引述任務書體例／談論那個詞本身），全部不是
        斷言。門檻改回 1 就是把它們收回來——而「一個永遠在響的警報等於沒有警報」
        本 repo 已有判例。
        """
        self.assertEqual(G.NAKED_MIN_TOKENS, 2)
        for sentence in _SINGLE_WORD_FALSE_REDS:
            with self.subTest(sentence=sentence):
                self.assertEqual(G.naked_verdict_hits(sentence, ""), [],
                                 f"{sentence!r} 只有一個判決詞，判它就是那 3 筆假紅")

    def test_a_quoted_verdict_word_is_being_discussed_not_asserted(self) -> None:
        """引號內的詞是**被談論的對象**：3 筆假紅有 1 筆正是這一型。

        紅綠自證的另一半在下一行——拿掉引號、湊足兩個詞就必須命中，否則這個抑制器
        等於把判準關掉。
        """
        self.assertEqual(
            G.naked_verdict_hits("任務書要求寫明「已驗證」與「全綠」兩個字樣。", ""),
            [], "引號內的詞被當成斷言了")
        self.assertTrue(G.naked_verdict_hits("已驗證，全綠。", ""),
                        "拿掉引號後仍不命中 ⇒ 抑制器恆真，判準被關掉了")

    def test_an_attributed_relay_is_the_desired_behaviour_here_too(self) -> None:
        """邊界：帶出處標記的轉述必須放行（與第一個判準同一個逃生口語意）。

        無人看管時抑制詞縮到只認方括號標記——句子裡塞一個「回報」就能靜音，而無人
        看管的回合可以自己寫出那兩個字（同 `# git-guard-ok:` 的已知弱點與處置）。
        """
        for sentence in (f"`[他包回報]` {_NAKED}", f"修復包 C 回報：{_NAKED}",
                         f"QA 宣稱{_NAKED}"):
            with self.subTest(sentence=sentence):
                self.assertEqual(G.naked_verdict_hits(sentence, ""), [],
                                 f"{sentence!r} 已標出處卻被判違規")
        self.assertTrue(
            G.naked_verdict_hits(f"修復包 C 回報：{_NAKED}", "", unattended=True),
            "無人看管時『回報』不得再構成抑制——否則模型可以自己寫出豁免")
        self.assertEqual(
            G.naked_verdict_hits(f"`[他包回報]` {_NAKED}", "", unattended=True), [],
            "方括號標記在無人看管時仍須抑制")

    def test_the_value_domain_criterion_is_unchanged_by_this_one(self) -> None:
        """迴歸：新判準不得動到第一個判準的**任何**方向（含正反兩面）。

        兩個判準的證據面不同（值 vs 有無輸出），共用同一份 `PROVENANCE_RE` 與
        `_SENTENCE_RE` ⇒ 動到抑制詞或斷句就會同時改壞兩邊，而只有一邊有人看。
        """
        self.assertTrue(G.unsourced_verdict_hits("修復包 2 完成，1703 passed。",  # baseline-ok:語料
                                                 _OWN_OUTPUT))
        self.assertEqual(
            G.unsourced_verdict_hits("回歸 3748 passed。", _OWN_OUTPUT), [])  # baseline-ok:語料
        self.assertEqual(G.unsourced_verdict_hits("回歸 3,748 passed。",  # baseline-ok:語料
                                                  _OWN_OUTPUT), [])
        self.assertEqual(G.normalize_digits("rc=0，44 skip"), "rc=0，44 skip")
        self.assertEqual(G.unsourced_verdict_hits(_NAKED, ""), [],
                         "不帶值的句子不得開始命中第一個判準——那是另一個判準的射程")


class TestTheNakedGuardIsItsOwnProcessLevelContract(unittest.TestCase):
    """程序層：真違規要出聲、rc 仍為 0、逃生口不與其他判準共用。"""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.transcript = Path(self._dir.name) / "t.jsonl"
        self.transcript.write_text("", encoding="utf-8")  # 零 tool_result

    def _run(self, claim: str, env_extra: dict | None = None):
        payload = json.dumps({"hook_event_name": "Stop",
                              "last_assistant_message": claim,
                              "transcript_path": str(self.transcript)})
        env = _hook_env({"AUTOSDD_TRACE_DIR": self._dir.name, **(env_extra or {})})
        return subprocess.run([sys.executable, str(_HOOK)], input=payload, env=env,
                              capture_output=True, text=True, timeout=60,
                              encoding="utf-8", errors="replace")

    def test_it_speaks_on_stderr_but_still_exits_zero(self) -> None:
        """修復前實測 `rc=0` **且 stderr 全空**（規則 8 那一列逐字記載的破洞）。"""
        done = self._run(_NAKED)
        self.assertEqual(done.returncode, 0, "本守衛永不阻斷")
        self.assertIn("赤裸宣稱", done.stderr, "破洞句仍然靜默 ⇒ 規則 8 沒修好")
        self.assertIn("零 tool_result", done.stderr, "必須說出為什麼算赤裸")
        self.assertIn("跑任何一個工具即抑制", done.stderr,
                      "訊息必須給出可滿足的出路，否則讀者只能把守衛關掉")

    def test_turning_off_the_naked_guard_leaves_the_value_guard_armed(self) -> None:
        """逃生口刻意不共用：共用會讓「別唸我這件事」順手關掉另一件。"""
        claim = _NAKED + " 收工：99991 passed。"  # baseline-ok: 合成語料
        done = self._run(claim, {"AUTOSDD_NAKED_GUARD_OFF": "1"})
        self.assertEqual(done.returncode, 0)
        self.assertNotIn("赤裸宣稱", done.stderr, "逃生口沒有真的關掉本判準")
        self.assertIn("99991", done.stderr, "另一個判準被順手關掉了")

    def test_the_claim_guard_hatch_does_not_silence_this_one(self) -> None:
        """反向：關掉第一個判準時本判準必須**還在**（否則兩個名字同一個開關）。"""
        done = self._run(_NAKED, {"AUTOSDD_CLAIM_GUARD_OFF": "1"})
        self.assertEqual(done.returncode, 0)
        self.assertIn("赤裸宣稱", done.stderr)

    def test_the_new_hatch_is_read_and_is_not_a_shared_name(self) -> None:
        """判準問的是本檔**讀**了哪個環境變數（AST 站點），不是文字面出現過。"""
        read_names = _hook_env_reads()
        self.assertIn("AUTOSDD_NAKED_GUARD_OFF", read_names,
                      "第四個判準必須有自己的逃生口")
        for foreign in ("AUTOSDD_CLAIM_GUARD_OFF", "AUTOSDD_CAUSAL_GUARD_OFF",
                        "AUTOSDD_PACE_GUARD_OFF"):
            self.assertIn(foreign, read_names,
                          f"{foreign} 消失了 ⇒ 那個判準被順手併進別人的開關")


#: D15：一句赤裸的「被擋」宣稱，本場零證據。
_BLOCKED_CLAIM = "剛開新視窗，工具就被擋了，什麼都不能寫。"


class TestTheUnbackedBlockClaimJudgement(unittest.TestCase):
    """第五個判準（D15；DEF-200-275 第五輪）：「被擋／水位」宣稱在本場沒有
    deny／[SDD-FSM]／[SDD-CTX]／used= 佐證時出聲。"""

    def test_a_bare_block_claim_with_no_evidence_is_flagged(self) -> None:
        hits = G.unbacked_block_claim_hits(_BLOCKED_CLAIM, "")
        self.assertTrue(hits, "赤裸的「被擋」宣稱沒有被抓到")
        self.assertEqual(hits[0]["phrase"], "被擋")

    def test_a_quoted_block_phrase_is_being_discussed_not_asserted(self) -> None:
        self.assertEqual(
            G.unbacked_block_claim_hits("守衛的判準名字就叫「被擋」偵測。", ""), [],
            "引號內的詞是被談論的對象，不是斷言")

    def test_a_real_deny_marker_in_this_sessions_evidence_silences_it(self) -> None:
        evidence = "[SDD-CTX][CRIT] deny：本次呼叫被拒絕。"
        self.assertEqual(G.unbacked_block_claim_hits(_BLOCKED_CLAIM, evidence), [],
                         "本場已有 deny／[SDD-CTX] 佐證，不該再被判成無佐證")

    def test_a_used_equals_reading_in_this_sessions_evidence_silences_it(self) -> None:
        evidence = "used=850000 window=1000000 來源=指定值"
        self.assertEqual(G.unbacked_block_claim_hits(_BLOCKED_CLAIM, evidence), [],
                         "本場已有 used= 佐證，不該再被判成無佐證")

    def test_a_check_invocation_in_this_sessions_evidence_silences_it(self) -> None:
        evidence = "已跑 python tools/session_resume_planner.py --check 核對過水位"
        self.assertEqual(G.unbacked_block_claim_hits(_BLOCKED_CLAIM, evidence), [],
                         "引用了查證指令本身也算已經去查過")

    def test_a_quota_guard_notice_in_this_sessions_evidence_silences_it(self) -> None:
        """假紅普查逼出來的（見本檔假紅普查方法段）：`context_budget_guard.py` 的
        `kind=`／`band=`／`cap=` 通知格式不含 `deny`／`used=`，原始詞表對它結構性失明。"""
        evidence = "kind=session 28% band=notice cap=4 reason=ok"
        self.assertEqual(G.unbacked_block_claim_hits(_BLOCKED_CLAIM, evidence), [])

    def test_a_permission_wall_message_in_this_sessions_evidence_silences_it(self) -> None:
        """假紅普查逼出來的：harness 自己的權限牆訊息（不是任何 repo hook 印的字，逐字
        固定，本機全母體實測 6 筆一致）。"""
        evidence = ("Claude requested permissions to write to /tmp/x.md, "
                   "but you haven't granted it yet.")
        self.assertEqual(G.unbacked_block_claim_hits(_BLOCKED_CLAIM, evidence), [])

    def test_a_clean_claim_with_no_block_phrase_is_silent(self) -> None:
        self.assertEqual(G.unbacked_block_claim_hits("已完成三個檔案的修改。", ""), [])

    def test_a_negated_block_phrase_is_not_a_claim(self) -> None:
        """DEF-200-501（探針 PC1「兩步都沒被擋」被唸成被擋）：否定句不是宣稱。
        正控制＝肯定句「工具被擋了」仍命中，否則否定處理等於把判準關掉。"""
        for sentence in ("能。兩步都沒被擋。", "這一步未被擋。", "工具沒有被擋。",
                         "The call was not blocked."):
            with self.subTest(sentence=sentence):
                self.assertEqual(G.unbacked_block_claim_hits(sentence, ""), [])
        hits = G.unbacked_block_claim_hits("沒有人回應，工具被擋了。", "")
        self.assertEqual([h["phrase"] for h in hits], ["被擋"], "否定處理把真宣稱滅掉了")

    def test_the_negation_semantics_are_params_json_s_not_a_second_vocabulary(self) -> None:
        """否定語意以量測端的 params.json 為準：字面住兩個家，唯一條件是有東西逐字對帳。"""
        prm = json.loads(_PARAMS_PATH.read_text(encoding="utf-8"))
        head = re.match(r"\(\?<!\[[^\]]+\]\)", prm["claim_re"]).group(0)
        self.assertEqual(G.BLOCK_NEGATION_LOOKBEHIND, head + r"(?<!not\s)")
        self.assertTrue(prm["claim_exc_re"].startswith(G.BLOCK_NEGATION_EXC_RE.pattern))


class TestTheUnbackedBlockClaimHookWiring(unittest.TestCase):
    """程序層：D15 判準真的接進 Stop 分支，證據面真的讀得到 attachment 型佐證，
    且逃生口不與其他判準共用。"""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)

    def _write_transcript(self, lines: list[str]) -> Path:
        p = Path(self._dir.name) / "t.jsonl"
        p.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        return p

    def _run(self, claim: str, transcript: Path, env_extra: dict | None = None):
        payload = json.dumps({"hook_event_name": "Stop", "last_assistant_message": claim,
                              "transcript_path": str(transcript)})
        return subprocess.run([sys.executable, str(_HOOK)], input=payload,
                              env=_hook_env(env_extra), capture_output=True, text=True,
                              timeout=60, encoding="utf-8", errors="replace")

    def test_a_bare_claim_with_an_empty_transcript_is_flagged_on_stderr(self) -> None:
        transcript = self._write_transcript([])
        done = self._run(_BLOCKED_CLAIM, transcript)
        self.assertEqual(done.returncode, 0, "本守衛永不阻斷")
        self.assertIn("被擋／水位", done.stderr)

    def test_a_real_deny_attachment_in_the_transcript_silences_it(self) -> None:
        """驗證 `_INTERESTING` 前篩真的把 `hook_blocking_error` 攔進來，不是只在
        單元測試層面繞過真實逐字稿。"""
        line = json.dumps({
            "type": "attachment",
            "attachment": {"type": "hook_blocking_error", "hookEvent": "PreToolUse",
                           "blockingError": {
                               "blockingError": "[SDD-CTX] deny：used=900000 window=1000000"}},
        })
        transcript = self._write_transcript([line])
        done = self._run(_BLOCKED_CLAIM, transcript)
        self.assertEqual(done.returncode, 0)
        self.assertNotIn("被擋／水位", done.stderr, "真實 deny attachment 沒有被讀到")

    def test_a_real_additional_context_attachment_silences_it(self) -> None:
        line = json.dumps({
            "type": "attachment",
            "attachment": {"type": "hook_additional_context", "hookEvent": "PostToolUse",
                           "content": ["[SDD-CTX][WARN] used=800000 window=1000000"]},
        })
        transcript = self._write_transcript([line])
        done = self._run(_BLOCKED_CLAIM, transcript)
        self.assertEqual(done.returncode, 0)
        self.assertNotIn("被擋／水位", done.stderr,
                         "真實 hook_additional_context attachment 沒有被讀到")

    def test_the_escape_hatch_silences_only_this_one(self) -> None:
        transcript = self._write_transcript([])
        claim = _BLOCKED_CLAIM + " 收工：99991 passed。"  # baseline-ok: 合成語料
        done = self._run(claim, transcript, {"AUTOSDD_BLOCK_CLAIM_GUARD_OFF": "1"})
        self.assertEqual(done.returncode, 0)
        self.assertNotIn("被擋／水位", done.stderr, "逃生口沒有真的關掉本判準")
        self.assertIn("99991", done.stderr, "另一個判準被順手關掉了")

    def test_the_new_hatch_is_read_and_is_not_shared(self) -> None:
        read_names = _hook_env_reads()
        self.assertIn("AUTOSDD_BLOCK_CLAIM_GUARD_OFF", read_names,
                      "第五個判準必須有自己的逃生口")
        for foreign in ("AUTOSDD_CLAIM_GUARD_OFF", "AUTOSDD_NAKED_GUARD_OFF",
                        "AUTOSDD_CAUSAL_GUARD_OFF", "AUTOSDD_PACE_GUARD_OFF"):
            self.assertIn(foreign, read_names,
                          f"{foreign} 消失了 ⇒ 那個判準被順手併進別人的開關")

    def test_the_pc1_negated_sentence_is_silent_end_to_end(self) -> None:
        """DEF-200-501：探針 PC1 的逐字回覆走真實子行程，stderr 也不得唸「被擋／水位」。"""
        done = self._run("能。兩步都沒被擋。", self._write_transcript([]))
        self.assertEqual(done.returncode, 0, "本守衛永不阻斷")
        self.assertNotIn("被擋／水位", done.stderr, "否定句被當成被擋宣稱")


class TestTheBlockClaimEvidenceWindowIsRecentTurnsOnly(unittest.TestCase):
    """D24（SD-06）：第五判準的佐證窗口從全場收斂為「倒數第二則 role=user 訊息之後」，
    避免早已無關的舊通知替本回合赤裸宣稱背書。詳見 docs/06_quality/
    CrossPlatform_DEF200275_Context_Metering_Evidence.md〈第六輪〉。"""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)

    def _write_transcript(self, lines: list[str]) -> Path:
        p = Path(self._dir.name) / "t.jsonl"
        p.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        return p

    def _run(self, claim: str, transcript: Path):
        payload = json.dumps({"hook_event_name": "Stop", "last_assistant_message": claim,
                              "transcript_path": str(transcript)})
        return subprocess.run([sys.executable, str(_HOOK)], input=payload,
                              env=_hook_env(), capture_output=True, text=True, timeout=60,
                              encoding="utf-8", errors="replace")

    @staticmethod
    def _user_line(when: str, text: str) -> str:
        """真人 role=user 訊息（非 tool_result 中繼）——D24 拿它當回合邊界。"""
        return json.dumps({"type": "user", "timestamp": when,
                           "message": {"role": "user", "content": text}})

    @staticmethod
    def _notice_line(when: str, content: str) -> str:
        """額度守衛 `hook_additional_context` 通知形狀（見 `BLOCK_EVIDENCE_RE`）。"""
        return json.dumps({
            "type": "attachment", "timestamp": when,
            "attachment": {"type": "hook_additional_context", "hookEvent": "PostToolUse",
                           "content": [content]},
        })

    def test_a_notice_from_two_rounds_ago_no_longer_silences_this_rounds_claim(self) -> None:
        lines = [
            self._user_line("2026-09-01T00:00:00Z", "第一輪：開始工作"),
            self._notice_line("2026-09-01T00:01:00Z",
                             "kind=session 28% band=notice cap=4 reason=ok"),
            self._user_line("2026-09-01T00:02:00Z", "第二輪：（倒數第二則，邊界）"),
            self._user_line("2026-09-01T00:03:00Z", "第三輪：這一輪被擋了嗎？"),
        ]
        transcript = self._write_transcript(lines)
        done = self._run("我剛剛被擋了，不能寫檔案。", transcript)
        self.assertEqual(done.returncode, 0, "本守衛永不阻斷")
        self.assertIn("被擋／水位", done.stderr,
                      "兩回合前的 kind=/band= 通知不應再讓這一回合的赤裸宣稱免罰")

    def test_a_notice_inside_the_previous_round_still_silences_it(self) -> None:
        """對照組：通知落在邊界之後（前一回合）時仍應放行，不能矯枉過正。"""
        lines = [
            self._user_line("2026-09-01T00:00:00Z", "第一輪：開始工作"),
            self._user_line("2026-09-01T00:02:00Z", "第二輪：（倒數第二則，邊界）"),
            self._notice_line("2026-09-01T00:02:30Z",
                             "kind=session 91% band=crit cap=4 reason=ok"),
            self._user_line("2026-09-01T00:03:00Z", "第三輪：這一輪被擋了嗎？"),
        ]
        transcript = self._write_transcript(lines)
        done = self._run("我剛剛被擋了，不能寫檔案。", transcript)
        self.assertEqual(done.returncode, 0)
        self.assertNotIn("被擋／水位", done.stderr,
                         "邊界之後（前一回合）的通知仍應維持既有『合法情境』放行")

    def test_fewer_than_two_user_turns_falls_back_to_whole_transcript(self) -> None:
        """少於兩則真人訊息時無邊界可切，退回全場（覆蓋既有假紅普查案例形狀）。"""
        lines = [
            self._user_line("2026-09-01T00:00:00Z", "只有一輪，沒有邊界可切"),
            self._notice_line("2026-09-01T00:01:00Z",
                             "kind=session 28% band=notice cap=4 reason=ok"),
        ]
        transcript = self._write_transcript(lines)
        done = self._run("我剛剛被擋了，不能寫檔案。", transcript)
        self.assertEqual(done.returncode, 0)
        self.assertNotIn("被擋／水位", done.stderr,
                         "只有一則真人訊息時沒有邊界，應退回全場既有行為")


#: 出處欄位的形態（值域是逐字稿觀察所得、非官方契約，見 `_is_genuine_user_turn`）。
#: `_NOTICE_OLD` 是 `turnOrigin` 問世（CC 2.1.277）之前的通知形態：只有 `origin.kind`（本機
#: 母體 2.1.248～2.1.276 共 370 筆），`promptSource` 早期為 `sdk`、2.1.270 起為 `system`。
_HUMAN = {"origin": {"kind": "human"}, "promptSource": "typed", "turnOrigin": "human"}
_NOTICE = {"origin": {"kind": "task-notification"}, "promptSource": "system",
           "turnOrigin": "task_notification"}
_NOTICE_OLD = {"origin": {"kind": "task-notification"}, "promptSource": "sdk"}
_PEER = {"origin": {"kind": "peer"}, "isMeta": True, "promptSource": "system",
         "turnOrigin": "peer"}


class TestTheTurnBoundaryIgnoresHarnessGeneratedUserRecords(unittest.TestCase):
    """DEF-200-423：回合邊界只認操作者輸入（數字與判準全文見 `_is_genuine_user_turn`）。
    敘事搬至 CrossPlatform_R204_StopHook_Negation_FalsePositive_Fix_Evidence.md〈附錄 B〉§6。"""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)

    def _write(self, lines: list[str]) -> Path:
        path = Path(self._dir.name) / "t.jsonl"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def _hits(self, lines: list[str]) -> list[dict]:
        """與 `main()` 同一條三步管線：讀逐字稿 → 切窗口 → 判『被擋』宣稱。"""
        stamped, records, turns = G._read_transcript(str(self._write(lines)))
        evidence = G._block_claim_evidence(stamped, records, turns)
        return G.unbacked_block_claim_hits(_BLOCKED_CLAIM, evidence)

    def _run(self, lines: list[str]):
        # 借鄰班的 `_run`：多一個 subprocess 站點就得重釘 `_CHILD_SITE_FLOOR`。
        return TestTheBlockClaimEvidenceWindowIsRecentTurnsOnly._run(
            self, _BLOCKED_CLAIM, self._write(lines))

    @staticmethod
    def _user(when: str, content, **fields) -> str:
        return json.dumps({"type": "user", "timestamp": when,
                           "message": {"role": "user", "content": content}, **fields})

    @staticmethod
    def _quota_block(when: str) -> str:
        """額度守衛擋下 Workflow 的 tool_result（帶 `kind=`／`band=`／`cap=`）。"""
        block = {"type": "tool_result", "tool_use_id": "t1",
                 "content": "kind=session 21% band=prepare cap=1 ⇒ Workflow 不可派"}
        return json.dumps({"type": "user", "timestamp": when,
                           "message": {"role": "user", "content": [block]}})

    @staticmethod
    def _context(event, text: str) -> str:
        att = {"type": "hook_additional_context", "content": [text]}
        if event is not None:
            att["hookEvent"] = event
        return json.dumps({"type": "attachment", "timestamp": "2026-09-28T16:01:00Z",
                           "attachment": att})

    def _storm(self) -> list[str]:
        """事故形狀：真人 A → 阻斷 → 通知×2（新舊形態各一）→ peer → slash 展開（只有
        isMeta）→ 真人 B。"""
        return [
            self._user("2026-09-28T16:00:00Z", "第一則：請開工", **_HUMAN),
            self._quota_block("2026-09-28T16:08:35Z"),
            self._user("2026-09-28T17:12:59Z", "<task-notification>\n<task-id>a1", **_NOTICE_OLD),
            self._user("2026-09-28T17:43:13Z", "<task-notification>\n<task-id>a2", **_NOTICE),
            self._user("2026-09-28T17:48:00Z", "Another Claude session sent a message:", **_PEER),
            self._user("2026-09-28T17:50:00Z", "<command-name>/x</command-name>", isMeta=True),
            self._user("2026-09-28T18:00:00Z", "第二則：收工了嗎？", **_HUMAN),
        ]

    def test_notifications_and_meta_records_are_not_turn_boundaries(self) -> None:
        """舊謂詞把 4 則 harness 記錄都算回合 ⇒ 邊界落在 slash 展開，16:08 的阻斷被擠出窗口。"""
        self.assertEqual(self._hits(self._storm()), [], "通知／peer／展開被當成回合邊界")

    def test_the_hook_process_is_silent_on_that_shape(self) -> None:
        """同一形狀走真的 hook 行程：`main()` 必須把整筆記錄交給謂詞。"""
        done = self._run(self._storm())
        self.assertEqual(done.returncode, 0, "本守衛永不阻斷")
        self.assertNotIn("被擋／水位", done.stderr)

    def test_operator_prompts_still_bound_the_window(self) -> None:
        """對照組：`human`（打字）與 `sdk`（`claude -p`）仍是邊界，否則『修好了』與『判準被
        關掉了』的輸出一模一樣。"""
        for name, fields in (("typed", _HUMAN), ("claude -p", {"turnOrigin": "sdk"})):
            with self.subTest(prompt=name):
                lines = [
                    self._user("2026-09-28T16:00:00Z", "第一則", **fields),
                    self._quota_block("2026-09-28T16:08:35Z"),
                    self._user("2026-09-28T16:30:00Z", "第二則（邊界）", **fields),
                    self._user("2026-09-28T18:00:00Z", "第三則", **fields),
                ]
                self.assertTrue(self._hits(lines), "邊界之前的阻斷不應再替本回合背書")

    def test_records_without_provenance_keep_the_content_shape_verdict(self) -> None:
        """欄位全缺（舊版逐字稿／既有合成語料）與修前逐字相同：純字串是真人、清一色
        tool_result 是中繼。"""
        relay = [{"type": "tool_result", "content": "x"}]
        for record in (None, {}, {"type": "user", "timestamp": "2026-09-28T16:00:00Z"}):
            with self.subTest(record=record):
                self.assertTrue(G._is_genuine_user_turn("隨手打的一句話", record))
                self.assertFalse(G._is_genuine_user_turn(relay, record))
                self.assertFalse(G._is_genuine_user_turn("  ", record))
        lines = [
            self._user("2026-09-28T16:00:00Z", "第一則"),
            self._quota_block("2026-09-28T16:08:35Z"),
            self._user("2026-09-28T16:30:00Z", "第二則（邊界）"),
            self._user("2026-09-28T18:00:00Z", "第三則"),
        ]
        self.assertTrue(self._hits(lines), "無出處欄位的純字串仍是回合邊界")

    def test_an_unknown_provenance_value_is_not_a_boundary(self) -> None:
        """未知的新值一律不算邊界：窗口變大＝多收證據（D24 既定 fail-open 方向）；反過來
        當邊界，下一版 Claude Code 多一種 harness 訊息就讓假紅無聲復發。"""
        lines = [
            self._user("2026-09-28T16:00:00Z", "第一則", **_HUMAN),
            self._quota_block("2026-09-28T16:08:35Z"),
            self._user("2026-09-28T17:00:00Z", "某種新的 harness 訊息",
                       origin={"kind": "something-new"}),
            self._user("2026-09-28T18:00:00Z", "第二則", **_HUMAN),
        ]
        self.assertEqual(self._hits(lines), [], "未知 origin.kind 被當成邊界")
        self.assertFalse(G._is_genuine_user_turn("x", {"turnOrigin": "something_new"}))

    def test_a_task_notification_body_is_not_a_boundary_without_provenance(self) -> None:
        """舊版逐字稿沒有任何出處欄位：內容前綴是唯一線索（備援排除），且只認句首。"""
        body = "<task-notification>\n<task-id>a1</task-id>\n</task-notification>"
        lines = [
            self._user("2026-09-28T16:00:00Z", "第一則"),
            self._quota_block("2026-09-28T16:08:35Z"),
            self._user("2026-09-28T17:00:00Z", body),
            self._user("2026-09-28T18:00:00Z", "第二則"),
        ]
        self.assertEqual(self._hits(lines), [], "無欄位的通知本文被當成邊界")
        self.assertFalse(G._is_genuine_user_turn([{"type": "text", "text": body}], {}))
        self.assertTrue(G._is_genuine_user_turn("我貼一段 " + body, {}), "只認句首前綴")

    def test_slash_echoes_and_compact_summaries_are_not_boundaries_either(self) -> None:
        """複審鏡 SF-1：本機 slash 指令至今仍無出處欄位，回聲對（`<command-name>`＋
        `<local-command-stdout>`）同一時刻落兩筆，當邊界會把窗口塌到只剩當前回合；compact
        續接摘要是 harness 代筆。三者都走前綴備援排除（fail-open：只會讓窗口變大）。"""
        for body in ("<command-name>/model</command-name>",
                     "<local-command-stdout>Set model to opus</local-command-stdout>",
                     "This session is being continued from a previous conversation…"):
            with self.subTest(body=body[:20]):
                lines = [
                    self._user("2026-09-28T16:00:00Z", "第一則"),
                    self._quota_block("2026-09-28T16:08:35Z"),
                    self._user("2026-09-28T17:00:00Z", body),
                    self._user("2026-09-28T17:00:00Z", body),
                    self._user("2026-09-28T18:00:00Z", "第二則"),
                ]
                self.assertEqual(self._hits(lines), [], "無欄位的 slash 回聲／續接摘要被當成邊界")

    def test_the_predicate_never_raises_on_odd_record_shapes(self) -> None:
        """複審鏡 SF-3：`main()` 吞下一切例外 ⇒ 謂詞一炸，五個判準整場靜默。怪形狀（非 dict
        的 record／origin／turnOrigin、`isMeta` 非布林）只准回布林，不准拋。"""
        odd = (["x"], "x", 0, {"origin": "task-notification"}, {"origin": ["human"]},
               {"turnOrigin": ["human"]}, {"isMeta": "true"}, {"origin": {"kind": None}},
               {"origin": {}, "turnOrigin": ""})
        for record in odd:
            with self.subTest(record=record):
                self.assertIsInstance(G._is_genuine_user_turn("一句話", record), bool)
                self.assertIsInstance(G._is_genuine_user_turn([{"type": "text"}], record), bool)
        self.assertTrue(G._is_genuine_user_turn("一句話", {"origin": {"kind": "sdk"}}),
                        "複審鏡 SF-5：`claude -p` 不論標在 origin.kind 或 turnOrigin 都算操作者")

    def test_a_stop_hooks_deny_message_is_still_evidence(self) -> None:
        """複審鏡 SF-3 對照組：Stop 事件跳過的只有本 hook 的 `hook_additional_context` 警報；
        `hook_blocking_error`（真的 deny 訊息本體）不分事件一律算佐證。"""
        deny = json.dumps({"type": "attachment", "timestamp": "2026-09-28T16:01:00Z",
                           "attachment": {"type": "hook_blocking_error", "hookEvent": "Stop",
                                          "blockingError": {"blockingError": "deny: used=1"}}})
        lines = [self._user("2026-09-28T16:00:00Z", "第一則", **_HUMAN), deny]
        self.assertEqual(self._hits(lines), [], "Stop 的 hook_blocking_error 被連坐跳過")

    def test_the_hooks_own_stop_alert_is_not_evidence_for_the_next_claim(self) -> None:
        """本 hook 的警報以 `hook_additional_context`（`hookEvent=Stop`）落盤，內文列舉
        deny／[SDD-CTX]／used=／--check＝`BLOCK_EVIDENCE_RE` 的詞表 ⇒ 收進證據面，同窗口
        第二次同型宣稱就被自己的警報洗白。"""
        alert = ("🔴 這一則有 1 句「被擋／水位」宣稱，但本場沒有任何 deny／[SDD-FSM]／"
                 "[SDD-CTX]／used= 佐證。請先跑 `python tools/session_resume_planner.py --check`")
        lines = [self._user("2026-09-28T16:00:00Z", "第一則", **_HUMAN),
                 self._context("Stop", alert)]
        self.assertTrue(self._hits(lines), "自己的警報替下一則同型宣稱背書")

    def test_notices_from_other_hook_events_still_count_as_evidence(self) -> None:
        """對照組：守衛的水位通知仍算佐證；SessionStart 除外（DEF-200-430）。"""
        for event in ("PostToolUse", "PreToolUse", None):
            with self.subTest(hookEvent=event):
                lines = [self._user("2026-09-28T16:00:00Z", "第一則", **_HUMAN),
                         self._context(event, "[SDD-CTX][WARN] used=800000 window=1000000")]
                self.assertEqual(self._hits(lines), [])

    def test_a_claim_with_no_block_on_record_still_speaks_and_names_both_gauges(self) -> None:
        """正控：兩則真人訊息、全場從未阻斷 ⇒ 仍要出聲（修的是邊界，不是把判準修死）；
        指路要含額度面——`--check` 只量 context，額度帶（band=／cap=）在 `--pace`。"""
        lines = [self._user("2026-09-28T16:00:00Z", "第一則", **_HUMAN),
                 self._user("2026-09-28T18:00:00Z", "第二則", **_HUMAN)]
        done = self._run(lines)
        self.assertEqual(done.returncode, 0)
        self.assertIn("被擋／水位", done.stderr, "判準被修死了：無佐證的宣稱不再出聲")
        self.assertIn("--check", done.stderr)
        self.assertIn("--pace", done.stderr, "指路缺額度面")


#: 真實 hook 阻斷訊息（DEF-200-428）：全文不含 `BLOCK_EVIDENCE_RE` 任一詞（本機 131 筆中 106 筆）。
_HOOK_BLOCK_TEXT = (
    "PreToolUse:PowerShell hook error: [${CLAUDE_PROJECT_DIR}/.claude/hooks/_hook_launcher.py "
    ".claude/hooks/block_destructive_git.py]: 🔴 這條指令的等待機制會靜默壞掉，已擋下（鐵律六）")

#: 原生權限拒絕的訊息（CC 2.1.223 的實錄：`is_error` 卻沒有 `toolDenialKind`）；同樣不含詞表字樣。
_NATIVE_DENIAL_TEXT = ("<tool_use_error>File is in a directory that is denied by your "
                       "permission settings.</tool_use_error>")


def _at(minute: int) -> str:
    """同一天的整分鐘落款（帶 offset：naive 時間戳不落盤）。"""
    return f"2026-09-29T12:{minute:02d}:00Z"


# ══════════════════════════════════════════════════════════════════════════
# ②′ 量測器（`tools/probe/audit_session.py`／`tools/probe/fivequestion_ledger.py`）的契約鎖
# ══════════════════════════════════════════════════════════════════════════
_PROBE_DIR = _REPO_ROOT / "tools" / "probe"
_PARAMS_PATH = (_REPO_ROOT / "docs" / "06_quality" / "FiveQuestion_Audit_Protocol"
                / "params.json")
_T0 = datetime(2026, 10, 3, 12, 0, tzinfo=UTC).astimezone()  # 本機時區的正午
_Q4_NOW = datetime(2026, 10, 4, tzinfo=UTC)
_HOOK_DENIAL = "PreToolUse:PowerShell hook error: [python hooks/lint_powershell_command.py]: 擋"
_DEFECT_LOG = "\n".join([
    "| 編號 | 日期 | 情境 | 描述 | 嚴重度 | 對策 | 狀態 |",
    "|---|---|---|---|---|---|---|",
    "| DEF-200-100 | 2026-10-01 | c | d | P2 | m | fixed |",
    "| DEF-200-101 | 2026-10-02 | c | d | P3 | m | open |",
    "| DEF-200-102 | 2026-10-02 | c | d | P1 | m | open |",
    "| DEF-200-103 | 2026-10-03 | c | d | P2 | m | fixed |",
    "| DEF-200-104 | 2026-10-04 | c | d | P2 | m | open |",
])
_GATE_DOC = {
    "platform": "win32", "generated_at": "2026-10-03T12:00:00+00:00", "repo_head": "a" * 40,
    "statusline": {"installed": True, "matches_current_checkout": True},
    "hook_carrier": {"exists": True},
    "verify_hint": {"default_push_location": True, "default_lastexitcode": True},
    "check": {"rc": 0},
}


def _load_probe(name: str):
    """以檔案路徑載入 `tools/probe/<name>.py`。"""
    spec = importlib.util.spec_from_file_location(f"_t_{name}", _PROBE_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _printed(fn, *args, **kwargs) -> tuple[object, str]:
    """跑 `fn` 並攔下它 print 的每一行；環境變數改動（five_question 會 setdefault）一併還原。"""
    with mock.patch.dict(os.environ), mock.patch("builtins.print") as fake:
        result = fn(*args, **kwargs)
    return result, "\n".join(" ".join(map(str, c.args)) for c in fake.call_args_list)


def _use(name: str, block: tuple | None = None, **inp: str) -> dict:
    return {"name": name, "block": block, "input": inp}


def _profile(sid: str, uses: list[dict], texts: tuple = ()) -> dict:
    return {"sid": sid, "entry": "cli", "start": _T0, "cwd": "repo", "uses": uses,
            "texts": list(texts), "brief": False, "usage": None, "usage_ts": None}


def _line(role: str, content: list, stamp: str, **extra: str) -> dict:
    return {"timestamp": stamp, "entrypoint": "cli", "cwd": "repo",
            "message": {"role": role, "content": content}, **extra}


def _call(tid: str, stamp: str, name: str = "PowerShell", **inp: str) -> dict:
    return _line("assistant", [{"type": "tool_use", "id": tid, "name": name, "input": inp}], stamp)


def _result(tid: str, stamp: str, text: str = "ok", denied: bool = False) -> dict:
    block = {"type": "tool_result", "tool_use_id": tid, "content": text, "is_error": denied}
    extra = {"toolDenialKind": "permission-rule"} if denied else {}
    return _line("user", [block], stamp, **extra)


def _write_jsonl(path: Path, records: list[dict]) -> Path:
    body = "".join(json.dumps(rec, ensure_ascii=False) + "\n" for rec in records)
    path.write_text(body, encoding="utf-8", newline="\n")
    return path


def _row(rnd: int, day: str, sha: str = "x", new: tuple = (), excluded: tuple = (),
         **extra: str) -> dict:
    return {"round": rnd, "date": day, "base_head": "h", "protocol_sha256": sha,
            "window_reset": False, "new_p_le2": list(new), "excluded_p_le2": list(excluded),
            "p1": 0, **extra}


class TestTheFiveQuestionMeasurerReadsItsCriteriaFromParams(unittest.TestCase):
    """`tools/probe/audit_session.py` 的②′ 判準常數住 `params.json`，碼裡不得再寫死。

    WHY：params.json 入協定 manifest（改它＝重置窗口），量測器碼不入——常數若寫死在碼裡，
    定義漂移不會觸發任何重置，窗口內幾輪的數字就悄悄不可比。每條斷言都是「改 params 值、
    量測輸出跟著變」的雙向對照，不是檢查某個字串存在。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = _load_probe("audit_session")
        cls.prm = json.loads(_PARAMS_PATH.read_text(encoding="utf-8"))

    def _five(self, profs: list[dict], **override: object) -> str:
        return _printed(self.audit.five_question, profs, None, {"cli"},
                        {**self.prm, **override})[1]

    def test_params_json_names_the_new_keys_and_drops_the_dead_one(self) -> None:
        keys = {"q1c_first_calls", "claim_max_uses", "claim_lookback", "feed_read_re",
                "q1b_min_n", "q3_quiescent_seconds", "parity_non_shell_tools"}
        self.assertTrue(keys <= set(self.prm), keys - set(self.prm))
        self.assertNotIn("q4_max_commits_behind", self.prm,
                         "全 repo 零消費者的死參數：留著只會讓人以為 Q4′ 有距離上限")

    def test_the_window_widths_and_gates_are_pinned_and_typed(self) -> None:
        """DEF-200-482：Q1′c 看前 10 個呼叫（seq 6～12 的早期阻斷在 5 看不到）、取最近 10 支
        （每輪 1～3 支真實 session，六輪窗口內才可達）；新鍵型別要對（寫成字串的 60 會讓
        `now - ts >= '60'` 炸）。前 N 個呼叫與 Q2′／Q1′b 的窗同寬（README 宣稱，這裡釘住）。"""
        prm = self.prm
        self.assertEqual(list(prm), sorted(prm), "params.json 的鍵必須維持字母序（diff 可讀）")
        self.assertEqual((prm["q1c_n"], prm["q1c_first_calls"]), (10, 10))
        self.assertEqual({prm["q1c_first_calls"], prm["q2_max_index"], prm["claim_max_uses"]}, {10})
        self.assertIsInstance(prm["q1b_min_n"], int)
        self.assertGreaterEqual(prm["q1b_min_n"], 1)
        self.assertIsInstance(prm["q3_quiescent_seconds"], (int, float))
        self.assertGreater(prm["q3_quiescent_seconds"], 0)
        tools = prm["parity_non_shell_tools"]
        self.assertTrue(tools and all(isinstance(t, str) for t in tools), tools)
        self.assertEqual(len(tools), len(set(tools)), "重複的工具名")

    def test_the_readme_names_exactly_the_keys_params_json_has(self) -> None:
        """writer==reader：params.json 是 writer，README 的鍵清單是 reader（人讀的契約）。新增鍵卻
        沒在 README 說明＝讀的人不知道有這把尺；README 點名不存在的鍵＝說明在騙人。"""
        readme = (_PARAMS_PATH.parent / "README.md").read_text(encoding="utf-8")
        block = readme.split("- `params.json`", 1)[1].split("\n## ", 1)[0]
        named = set(re.findall(r"`([a-z][a-z0-9_]*)`", block))
        self.assertEqual(named, set(self.prm), "README 的 params 鍵清單與 params.json 不相等")

    def test_the_non_shell_tool_list_comes_from_params_not_from_code(self) -> None:
        self.assertFalse(hasattr(self.audit, "NON_SHELL_TOOLS"), "判準常數又寫回量測器碼裡")
        stamp = "2026-10-03T01:00:00Z"
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_jsonl(Path(tmp) / "w.jsonl",
                                [_call("t1", stamp, name="Write", file_path="x")])
            shipped = self.audit.scan_transcript(path)["collapsed"]
            emptied = {**self.prm, "parity_non_shell_tools": []}
            with mock.patch.object(self.audit, "_params", return_value=emptied):
                without_the_list = self.audit.scan_transcript(path)["collapsed"]
        self.assertEqual((shipped, without_the_list), (False, True),
                         "只用 Write 的 session：清單在＝不是崩塌；清單空＝認不得的工具＝崩塌候選")

    def test_q1b_is_not_evaluable_below_its_minimum_population(self) -> None:
        """Q1′b 此前對 0／0 印 PASS（其餘判準都有 NOT-EVALUABLE）；最小母體住 params。"""
        def session(i: int) -> dict:
            return _profile(f"s{i}", [_use("Read", file_path="x")])

        one, five = ([session(i) for i in range(n)] for n in (1, 5))
        self.assertIn("Q1′b 宣稱≠阻斷  NOT-EVALUABLE(1/5)  0／0", self._five(one))
        self.assertIn("Q1′b 宣稱≠阻斷  PASS  0／0", self._five(five))
        self.assertIn("Q1′b 宣稱≠阻斷  PASS  0／0", self._five(one, q1b_min_n=1),
                      "最小母體沒有讀 params")

    def _feed_pair(self, directory: str, sid: str, usage: int, usage_ts: datetime,
                   feed_ts: datetime, feed_used: int) -> dict:
        """有 feed 檔的 session 輪廓：逐字稿尾端 (usage, usage_ts)、feed (feed_used, feed_ts)。"""
        doc = {"session_id": sid, "ts": feed_ts.isoformat(timespec="seconds"),
               "context_window": {"current_usage": {"input_tokens": feed_used}}}
        Path(directory, f"{sid}.json").write_text(json.dumps(doc), encoding="utf-8")
        return {**_profile(sid, [_use("Read", file_path="x")]),
                "usage": usage, "usage_ts": usage_ts}

    def test_the_q3_quiescent_gate_excludes_pairs_from_an_in_flight_window(self) -> None:
        """DEF-200-482：Q3′ 只納入靜止配對（在途視窗的差值是一則訊息的增量，100 token 的容忍對它無
        意義）；控制組＝閘門關掉（0 秒）時同一組輸入對在途窗 FAIL，證明是閘門讓它不假紅。另釘「不
        舊於」的解析度：feed 的 ts 只到秒、逐字稿到毫秒，同一秒的配對不得被當成過期而靜默消失。"""
        import statusline_context_feed as scf  # noqa: PLC0415 — `tools/` 由載入量測器時進 sys.path

        now = datetime.now().astimezone()
        same_second = (now - timedelta(seconds=300)).replace(microsecond=519000)
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {scf.FEED_DIR_ENV: tmp}):
            busy = self._feed_pair(tmp, "busy", 150_000, now - timedelta(seconds=6),
                                   now - timedelta(seconds=5), 150_000 + 18_767)  # feed 先一則
            quiet = self._feed_pair(tmp, "quiet", 90_000, now - timedelta(seconds=700),
                                    now - timedelta(seconds=600), 90_000)
            same = self._feed_pair(tmp, "same", 70_000, same_second,
                                   same_second.replace(microsecond=0), 70_000)
            behind = self._feed_pair(tmp, "behind", 50_000, now - timedelta(seconds=400),
                                     now - timedelta(seconds=405), 50_000)  # feed 比逐字稿舊
            pop = [behind, same, quiet, busy]  # `feed_diffs` 由新往舊取
            self.assertEqual(self.audit.feed_diffs(pop, 10, now, 60), ([0, 0], 1))
            self.assertEqual(self.audit.feed_diffs(pop, 10, now, 0), ([18_767, 0, 0], 0),
                             "控制組：閘門關掉時在途窗的差值必須現形")
            self.assertEqual(self.audit.feed_diffs(pop, 10, now, 10_000), ([], 3), "都不靜止")
            gated = self._five([quiet, busy], q3_min_pairs=1)
            opened = self._five([quiet, busy], q3_quiescent_seconds=0)
        self.assertIn("Q3′ feed 差  PASS  1 對；max|差|=0 [0]；NOT-QUIESCENT 1", gated)
        self.assertIn("Q3′ feed 差  FAIL  2 對；max|差|=18767 [18767, 0]；NOT-QUIESCENT 0", opened)

    def test_selftest_rc_is_zero_only_for_a_table_that_is_right_and_can_discriminate(self) -> None:
        """DEF-200-482：`--selftest` 此前有「舊判準」欄（＝同一支函式）與 `舊判準零錯 ⇒ rc=1`，兩欄
        恆相等 ⇒ rc=1 是結構必然、紅綠自證空轉。現在：答案表每列判對 ⇒ rc=0；任一列不符 ⇒ rc=1；
        表內 expect 為 True 與 False 的列缺任一類（恆回同一值的判準也能全對）⇒ rc=1。用判準替身
        注入，不起子行程。"""
        def risky(command: str) -> bool:
            return command.startswith("risky")

        def table(*rows: tuple[str, bool]) -> tuple:
            return tuple((cmd, want, "after=7/-1", "原因") for cmd, want in rows)

        def run(rows: tuple, judge) -> tuple[object, str]:
            return _printed(self.audit.run_selftest, rows, judge)

        good = table(("risky a", True), ("safe a", False))
        flipped = table(("risky a", False), ("safe a", False))
        all_true, all_false = table(("risky a", True), ("risky b", True)), table(("safe a", False))
        self.assertEqual(run(good, risky)[0], 0)
        rc, out = run(flipped, risky)
        self.assertEqual(rc, 1, "一列的答案與判準不符卻 rc=0")
        self.assertIn("❌", out)
        for rows, judge in ((all_true, lambda _c: True), (all_false, lambda _c: False)):
            rc, out = run(rows, judge)
            self.assertEqual(rc, 1, "只有單一類答案的表（鑑別力為零）卻 rc=0")
            self.assertIn("缺 expect=True 或 expect=False", out)
        real_rc, real_out = _printed(self.audit.main, ["--selftest"])
        rows = self.audit._rc_real._RC_SELFTEST
        self.assertEqual(real_rc, 0, real_out)
        self.assertIn(f"判錯 0 / {len(rows)}", real_out)
        self.assertNotIn("舊判準", real_out, "同一支函式的兩欄恆相等，不該再印")

    def test_claim_lookback_decides_whether_a_block_still_backs_the_claim(self) -> None:
        stamp = "2026-10-03T01:00:00Z"
        records = [_call("t1", stamp, command="cd x"), _result("t1", stamp, _HOOK_DENIAL, True)]
        for i in range(2, 6):
            records += [_call(f"t{i}", stamp, command="git status"), _result(f"t{i}", stamp)]
        records.append(_line("assistant", [{"type": "text", "text": "我被擋住了。"}], stamp))
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_jsonl(Path(tmp) / "s.jsonl", records)
            narrow, wide = (self.audit.session_profile(path, n) for n in (3, 5))
        self.assertFalse(narrow["texts"][0][1], "往回看 3：阻斷已滑出視窗，不該替宣稱背書")
        self.assertTrue(wide["texts"][0][1], "往回看 5：阻斷仍在視窗內，宣稱有依據")

    def test_claim_max_uses_decides_which_claims_are_counted(self) -> None:
        profs = [_profile("s1", [_use("Read", file_path="x")] * 3,
                          texts=[(7, False, "我被擋住了。")])]
        profs += [_profile(f"s{i}", [_use("Read", file_path="x")])  # 湊滿 Q1′b 的最小母體
                  for i in range(2, 6)]
        self.assertIn("Q1′b 宣稱≠阻斷  HUMAN-REVIEW  1／1", self._five(profs, claim_max_uses=10))
        self.assertIn("Q1′b 宣稱≠阻斷  PASS  0／0", self._five(profs, claim_max_uses=5))

    def test_first_call_window_comes_from_params_and_events_carry_a_date(self) -> None:
        blocked = _use("PowerShell", ("hook", "lint_powershell_command.py"), command="cd x")
        profs = [_profile("s1", [_use("Read", file_path="a"), _use("Read", file_path="b"),
                                 blocked])]
        wide, narrow = (self._five(profs, q1c_first_calls=n) for n in (5, 2))
        self.assertIn("1／1（≤", wide)  # 第 3 個呼叫被擋，落在前 5 之內
        self.assertIn("0／1（≤", narrow)  # 前 2 之外
        self.assertIn(f'"date": "{_T0.date().isoformat()}"', wide, "事件列要帶 session 起點日期")

    def test_q2_first_check_accepts_the_read_fallback(self) -> None:
        sep = chr(92)
        reads = ["home/.autosdd/context_feed/abc.json",
                 sep.join(["Users", "u", ".autosdd", "context_feed", "abc.json"]),
                 sep.join(["Users", "u", "autosdd_quota.json"])]

        def q2(first_use: dict) -> str:
            rest = [_use("Read", file_path="code.py")] * 9
            return self._five([_profile(f"s{i}", [first_use, *rest]) for i in range(5)])

        for path in reads:
            self.assertIn("Q2′ 首查序號  PASS", q2(_use("Read", file_path=path)), path)
        self.assertIn("Q2′ 首查序號  FAIL", q2(_use("Read", file_path="notes/context_feed.md")))


class TestTheFiveQuestionMeasurerCliContracts(unittest.TestCase):
    """`tools/probe/audit_session.py` 的 CLI 契約：切片旗標有效、`--parity` 在真實窗口不恆紅。

    WHY：`--five-question` 曾在讀 `--record-since` 之前就 return（旗標被靜默吞掉，help 卻要人
    分期比較一律用它）；`--parity` 曾把零 tool_use 的 session 算成崩塌（每驗一次載具就新增一支
    ⇒ rc 在真實窗口恆為 1）。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = _load_probe("audit_session")

    def _session(self, directory: str, name: str, day: str) -> None:
        stamp = f"{day}T12:00:00Z"
        path = _write_jsonl(Path(directory) / name,
                            [_call("t1", stamp, command="git status"), _result("t1", stamp)])
        mtime = datetime(2026, 10, 4, tzinfo=UTC).timestamp()
        os.utime(path, (mtime, mtime))

    def _population(self, tmp: str, *extra: str) -> str:
        rc, out = _printed(self.audit.main, ["--project-dir", tmp, "--five-question", *extra])
        self.assertEqual(rc, 0, out)
        return out.splitlines()[0]

    def test_five_question_slices_by_record_since_and_until(self) -> None:
        cut = "2026-10-02T00:00:00+00:00"
        with tempfile.TemporaryDirectory() as tmp:
            self._session(tmp, "old.jsonl", "2026-10-01")
            self._session(tmp, "new.jsonl", "2026-10-03")
            everything = self._population(tmp)
            after = self._population(tmp, "--record-since", cut)
            before = self._population(tmp, "--record-until", cut)
            # 兩者並給時 --record-since 優先：若 --since 勝出，old 會被切掉而變 1 支
            both = self._population(tmp, "--since", "2026-10-03T00:00:00+00:00",
                                    "--record-since", "2026-09-01T00:00:00+00:00")
        self.assertIn("母體 2 支", everything)
        self.assertIn("母體 1 支", after, "--record-since 被靜默忽略")
        self.assertIn("母體 1 支", before, "--record-until 被靜默忽略")
        self.assertIn("母體 2 支", both, "--record-since 沒有優先於 --since")

    def test_parity_does_not_count_a_zero_tool_session_as_collapse(self) -> None:
        stamp = "2026-10-03T12:00:00Z"
        argv = ["--project-dir", "", "--parity", "--json"]
        with tempfile.TemporaryDirectory() as tmp:
            argv[1] = tmp
            self._session(tmp, "busy.jsonl", "2026-10-03")
            _write_jsonl(Path(tmp) / "qa.jsonl",
                         [_line("assistant", [{"type": "text", "text": "只是問答"}], stamp)])
            write_only = [_call("t7", stamp, name="Write", file_path="x")]  # 只 Write 的活體探針
            _write_jsonl(Path(tmp) / "probe.jsonl", write_only)
            rc_ok, out_ok = _printed(self.audit.main, argv)
            # 有用工具卻一條 shell 指令都抽不到＝格式變了，仍必須 fail-loud
            _write_jsonl(Path(tmp) / "broken.jsonl", [_call("t9", stamp, name="PwSh", cmd="x")])
            rc_bad, out_bad = _printed(self.audit.main, argv)
        self.assertEqual(json.loads(out_ok)["summary"]["collapsed_sessions"], [])
        self.assertEqual(rc_ok, 0, "分歧 0 且只有零 tool_use／只 Write 的 session ⇒ rc 應為 0")
        self.assertEqual(json.loads(out_bad)["summary"]["collapsed_sessions"], ["broken.jsonl"])
        self.assertEqual(rc_bad, 1)


class TestTheProtocolStatusPrintsLedgerIntegrityAndQ4Evidence(unittest.TestCase):
    """`tools/probe/audit_session.py --protocol-status` 印完整性閘與 Q4′ 九格。

    實作住 `tools/probe/fivequestion_ledger.py`。

    WHY：severity.md 曾宣稱「完整性閘…機械紅」卻沒有任何實作，Q4′ 證據也只能人讀九格；現在
    兩者都由量測器印出（rc 恆 0、不接閘門）。🔴 量不到（缺鍵／缺檔／git 失敗）必須印成「量不到」
    而不是通過——空洞的綠比紅更危險。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.led = _load_probe("fivequestion_ledger")
        cls.prm = json.loads(_PARAMS_PATH.read_text(encoding="utf-8"))

    def test_the_gate_flags_a_p_le2_defect_nobody_registered(self) -> None:
        rows = [_row(1, "2026-10-01", new=("DEF-200-100",)),
                _row(2, "2026-10-03", new=("DEF-200-103",))]
        # 102＝窗口 (10-01, 10-03] 內的 P1 且無人登記；101 是 P3；100 屬前列；104 晚於本列
        self.assertEqual(self.led.completeness_gap(rows, _DEFECT_LOG), ["DEF-200-102"])
        rows[-1]["excluded_p_le2"] = ["DEF-200-102"]
        self.assertEqual(self.led.completeness_gap(rows, _DEFECT_LOG), [])
        self.assertIsNone(self.led.completeness_gap([], _DEFECT_LOG), "沒有輪帳本＝量不到")

    def test_same_day_rounds_only_owe_what_no_earlier_row_registered(self) -> None:
        log = _DEFECT_LOG + "\n| DEF-200-105 | 2026-10-03 | c | d | P2 | m | open |"
        first = _row(1, "2026-10-03", new=("DEF-200-103",))
        self.assertEqual(self.led.completeness_gap([first], log), ["DEF-200-105"], "首列只認同日")
        second = _row(2, "2026-10-03", new=("DEF-200-105",))
        self.assertEqual(self.led.completeness_gap([first, second], log), [])
        self.assertEqual(self.led.completeness_gap([first, _row(2, "2026-10-03")], log),
                         ["DEF-200-105"], "同日第二輪不能掉進空的開區間")

    def test_q4_cells_never_read_a_missing_value_as_pass(self) -> None:
        full = self.led.q4_cells(_GATE_DOC, _Q4_NOW, True, 14)
        self.assertEqual((len(full), set(full.values())), (9, {True}))
        hints, off = _GATE_DOC["verify_hint"], dict.fromkeys(_GATE_DOC["verify_hint"], False)
        breaks = {f"{sec}.{key}": {sec: {**_GATE_DOC[sec], key: False}}
                  for sec in ("statusline", "verify_hint") for key in _GATE_DOC[sec]}
        breaks.update({"platform": {"platform": "linux", "verify_hint": off},
                       "check.rc==0": {"check": {"rc": 1}},
                       "hook_carrier.exists": {"hook_carrier": {"exists": False}},
                       "generated_at<=14d": {"generated_at": "2026-09-01T00:00:00+00:00"}})
        for cell, patch in breaks.items():
            got = self.led.q4_cells({**_GATE_DOC, **patch}, _Q4_NOW, True, 14)
            self.assertEqual([k for k, v in got.items() if v is not True], [cell], cell)
        for ancestor in (False, None):
            got = self.led.q4_cells(_GATE_DOC, _Q4_NOW, ancestor, 14)
            self.assertEqual([k for k, v in got.items() if v is not True],
                             ["repo_head_is_ancestor_of_HEAD"])
        # verify_hint 兩格＝Windows 專屬提示字樣（Push-Location／LASTEXITCODE）是否出現在產出機簡報：
        # win32 須在、darwin 須不在（簡報平台中立）。兩平台期望值相反——若對 darwin 也要求 True，
        # Mac 產的 JSON 會恆 FAIL、「兩平台九格」結構上不可達（立案形態見 DEF-200-491）。
        mac = {**_GATE_DOC, "platform": "darwin", "verify_hint": off}
        self.assertEqual(set(self.led.q4_cells(mac, _Q4_NOW, True, 14).values()), {True})
        got = self.led.q4_cells({**mac, "verify_hint": hints}, _Q4_NOW, True, 14)
        self.assertEqual([k for k in got if got[k] is not True],
                         [f"verify_hint.{h}" for h in hints], "darwin 不該出現 Windows 提示字樣")
        bare = self.led.q4_cells({"platform": "win32", "check": {"rc": None}}, _Q4_NOW, None, 14)
        self.assertEqual([k for k, v in bare.items() if v is True], ["platform"])
        self.assertIsNone(bare["check.rc==0"], "缺值＝量不到（None），不是 False 也不是 True")

    def test_is_ancestor_maps_only_rc_0_and_1_and_never_guesses(self) -> None:
        sha = "a" * 40
        for rc, want in ((0, True), (1, False), (128, None)):
            fake = mock.Mock(returncode=rc)
            with mock.patch.object(self.led.subprocess, "run", return_value=fake):
                self.assertIs(self.led.is_ancestor(_REPO_ROOT, sha), want, rc)
        with mock.patch.object(self.led.subprocess, "run", side_effect=OSError):
            self.assertIsNone(self.led.is_ancestor(_REPO_ROOT, sha))
        self.assertIsNone(self.led.is_ancestor(_REPO_ROOT, "HEAD"), "非十六進位不送進 git")
        self.assertIsNone(self.led.is_ancestor(_REPO_ROOT, None))

    def test_protocol_status_prints_everything_and_always_returns_zero(self) -> None:
        def run(root: Path, ancestor) -> tuple[object, str]:
            return _printed(self.led.protocol_status, self.prm, root / "proto",
                            root / "ledger.jsonl", root, trace_dir=root / "traces",
                            now=_Q4_NOW, ancestor=ancestor)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "proto").mkdir()
            (root / "traces").mkdir()
            readme = root / "proto" / "README.md"
            readme.write_text("x\n", encoding="utf-8", newline="\n")
            gate = root / "traces" / "session_gate_acceptance_h1.json"
            gate.write_text(json.dumps(_GATE_DOC), encoding="utf-8")
            sha = self.led.manifest_sha(root / "proto")[0]
            rows = [_row(1, "2026-10-01", sha, ("DEF-200-100",)),
                    _row(2, "2026-10-03", sha, ("DEF-200-103",), q4_win="PASS")]
            (root / "ledger.jsonl").write_text(
                "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8", newline="\n")
            (root / "AutoSDD_Defect_Log.md").write_text(_DEFECT_LOG, encoding="utf-8")
            rc, out = run(root, lambda _sha: True)
            _, unknown = run(root, lambda _sha: None)
            gate.write_text(json.dumps({**_GATE_DOC, "generated_at": "2026-09-01T00:00:00+00:00"}),
                            encoding="utf-8")
            _, stale = run(root, lambda _sha: True)
            readme.write_text("changed\n", encoding="utf-8", newline="\n")
            _, changed = run(root, lambda _sha: True)
        self.assertEqual(rc, 0)
        self.assertIn(f"protocol_sha256={sha}", out)
        self.assertIn("NOT-EVALUABLE(2/6)", out)
        self.assertIn("完整性閘 ✗ 漏列：DEF-200-102", out)
        self.assertIn('"q4_win": "PASS"', out, "帳本選填欄要原樣印出")
        self.assertIn("session_gate_acceptance_h1.json（win32）  PASS", out)
        unknown_line = next(ln for ln in unknown.splitlines() if "acceptance_h1" in ln)
        self.assertNotIn("PASS", unknown_line)
        self.assertIn("量不到", unknown_line)
        self.assertIn("  FAIL  ", next(ln for ln in stale.splitlines() if "acceptance_h1" in ln))
        self.assertIn("PROTOCOL-CHANGED", changed)

    def test_the_ledger_verdict_thresholds_hold_at_their_boundaries(self) -> None:
        """WHY：門檻（Σnew_p_le2<=2、Σp1==0、末列空）寫死在碼不在 params（ARCH-196-03），PASS／
        FAIL 分支原本零斷言；邊界行為至少要有鎖，才不會被「順手放寬一格」悄悄改掉。
        每列＝(new 個數, excluded 個數, p1)；另釘 ARCH-196-04 的「raw vs 公式可見」加印。"""
        need = self.prm["rounds_required"]
        zeros = [(0, 0, 0)] * (need - 2)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "proto").mkdir()
            (root / "proto" / "README.md").write_text("x\n", encoding="utf-8", newline="\n")
            sha = self.led.manifest_sha(root / "proto")[0]

            def printed(spec: list[tuple[int, int, int]]) -> str:
                rows = [_row(i, f"2026-10-{i:02d}", sha, tuple(f"N{i}-{k}" for k in range(n)),
                             tuple(f"X{i}-{k}" for k in range(x)), p1=p1)
                        for i, (n, x, p1) in enumerate(spec, 1)]
                (root / "ledger.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows),
                                                   encoding="utf-8", newline="\n")
                return _printed(self.led.protocol_status, self.prm, root / "proto",
                                root / "ledger.jsonl", root, trace_dir=root / "traces",
                                now=_Q4_NOW, ancestor=lambda _sha: True)[1]

            for label, spec, want in (
                ("Σnew=2 末列空 p1=0", [(1, 0, 0), (1, 0, 0)] + zeros, "PASS"),
                ("Σnew=3", [(2, 0, 0), (1, 0, 0)] + zeros, "FAIL"),
                ("末列非空", [(0, 0, 0)] * (need - 1) + [(1, 0, 0)], "FAIL"),
                ("某列 p1=1", [(1, 0, 0), (1, 0, 1)] + zeros, "FAIL"),
                (f"{need - 1} 列", [(0, 0, 0)] * (need - 1), f"NOT-EVALUABLE({need - 1}/{need})"),
            ):
                line = next(ln for ln in printed(spec).splitlines() if "評估:" in ln)
                self.assertTrue(line.endswith(f"評估: {want}"), f"{label}：{line}")
            out = printed([(1, 1, 0), (1, 0, 0)] + zeros)
        self.assertIn("raw=3", out, "new 2＋excluded 1：排除不入評估式，但 raw 必須看得見")
        self.assertIn("公式可見=2", out)


class TestTheBlockClaimEvidenceReadsStructuredDenials(unittest.TestCase):
    """DEF-200-428／430（受測：`.claude/hooks/check_claim_provenance.py` 的 `_tool_denial_kind`／
    `_read_transcript`／`_block_evidence_text`）：428 證據改認落盤的 `toolDenialKind` 欄位（備援：
    `is_error` 且行首 `PreToolUse:<Tool> hook error`／原生 denied）；430 簡報不算佐證。"""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)

    def _write(self, lines: list[str]) -> Path:
        path = Path(self._dir.name) / "t.jsonl"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def _hits(self, lines: list[str]) -> list[dict]:
        """與 `main()` 同一條三步管線：讀逐字稿 → 切窗口 → 判『被擋』宣稱。"""
        stamped, records, turns = G._read_transcript(str(self._write(lines)))
        evidence = G._block_claim_evidence(stamped, records, turns)
        return G.unbacked_block_claim_hits(_BLOCKED_CLAIM, evidence)

    def _run(self, lines: list[str]):
        # 借鄰班的 `_run`：多一個 subprocess 站點就得重釘 `_CHILD_SITE_FLOOR`。
        return TestTheBlockClaimEvidenceWindowIsRecentTurnsOnly._run(
            self, _BLOCKED_CLAIM, self._write(lines))

    @staticmethod
    def _human(when: str) -> str:
        return json.dumps({"type": "user", "timestamp": when,
                           "message": {"role": "user", "content": "請開工"}, **_HUMAN})

    @staticmethod
    def _result(when: str, text, is_error=None, **top) -> str:
        """一筆 tool_result 記錄；`top` 是頂層欄位（真實阻斷帶 `toolDenialKind`）。"""
        block = {"type": "tool_result", "tool_use_id": "toolu_x", "content": text}
        if is_error is not None:
            block["is_error"] = is_error
        return json.dumps({"type": "user", "timestamp": when,
                           "message": {"role": "user", "content": [block]}, **top})

    @staticmethod
    def _context(when: str, event, text: str) -> str:
        return json.dumps({"type": "attachment", "timestamp": when, "attachment": {
            "type": "hook_additional_context", "hookEvent": event, "content": [text]}})

    def test_a_structured_denial_backs_the_claim_even_when_its_text_says_nothing(self) -> None:
        self.assertIsNone(G.BLOCK_EVIDENCE_RE.search(_HOOK_BLOCK_TEXT), "前提失效：文字已在詞表內")
        denied = [self._human(_at(0)), self._result(
            _at(1), _HOOK_BLOCK_TEXT, is_error=True, toolDenialKind="permission-rule")]
        self.assertEqual(self._hits(denied), [], "結構化阻斷沒被認成佐證")
        done = self._run(denied)
        self.assertEqual(done.returncode, 0, "本守衛永不阻斷")
        self.assertNotIn("被擋／水位", done.stderr)
        plain = [self._human(_at(0)), self._result(_at(1), _HOOK_BLOCK_TEXT)]
        self.assertTrue(self._hits(plain), "對照組：同一段文字不帶欄位就不該算佐證")

    def test_any_non_empty_kind_counts_and_empty_ones_do_not(self) -> None:
        """欄位值是觀察所得（本機全是 `permission-rule`），故認任一非空值、不點名；空值不算。"""
        for value, backed in (("permission-rule", True), ("some-new-kind", True),
                              ("", False), (None, False), (False, False), (0, False)):
            with self.subTest(toolDenialKind=value):
                lines = [self._human(_at(0)),
                         self._result(_at(1), "無關文字", toolDenialKind=value)]
                self.assertEqual(not self._hits(lines), backed)

    def test_a_bare_denial_record_is_read_even_without_a_tool_result_block(self) -> None:
        """前篩鎖：欄位是判準本體，單獨出現（沒有 `tool_result` 字面）也要進得來。"""
        bare = json.dumps({"type": "user", "timestamp": _at(1),
                           "toolDenialKind": "permission-rule"})
        self.assertEqual(self._hits([self._human(_at(0)), bare]), [])

    def test_a_denial_text_on_an_error_result_backs_it_without_the_field(self) -> None:
        self.assertIsNone(G.BLOCK_EVIDENCE_RE.search(_NATIVE_DENIAL_TEXT), "前提失效：字樣在詞表內")
        listed = [{"type": "text", "text": _HOOK_BLOCK_TEXT}]
        for name, content in (("hook error", _HOOK_BLOCK_TEXT), ("blocks", listed),
                              ("native", _NATIVE_DENIAL_TEXT)):
            with self.subTest(content=name):
                lines = [self._human(_at(0)), self._result(_at(1), content, is_error=True)]
                self.assertEqual(self._hits(lines), [])

    def test_the_same_words_in_ordinary_output_are_not_evidence(self) -> None:
        quoted = "Exit code 1\nAssertionError: 'PreToolUse:PowerShell hook error: [x]' not in out"
        for name, kwargs, text in (
                ("一般結果", {}, _HOOK_BLOCK_TEXT),
                ("一般結果裡的原生拒絕字面", {}, _NATIVE_DENIAL_TEXT),
                ("一般結果裡的欄位名字面", {}, "toolDenialKind: permission-rule ⇒ 一次被擋"),
                ("is_error 明確為假", {"is_error": False}, _HOOK_BLOCK_TEXT),
                ("is_error 但字面不在行首", {"is_error": True}, quoted),
                ("is_error 但與阻斷無關", {"is_error": True}, "Exit code 1\nNo such file")):
            with self.subTest(name):
                lines = [self._human(_at(0)), self._result(_at(1), text, **kwargs)]
                self.assertTrue(self._hits(lines), f"{name}被當成阻斷佐證")

    def test_a_denial_outside_the_recent_window_no_longer_backs_a_later_claim(self) -> None:
        def denial(minute: int) -> str:
            return self._result(_at(minute), _HOOK_BLOCK_TEXT, is_error=True,
                                toolDenialKind="permission-rule")
        stale = [self._human(_at(0)), denial(1), self._human(_at(2)), self._human(_at(4))]
        fresh = [self._human(_at(0)), self._human(_at(2)), denial(3), self._human(_at(4))]
        self.assertTrue(self._hits(stale), "兩回合前的阻斷替現在的宣稱背書了")
        self.assertEqual(self._hits(fresh), [], "邊界之後（前一回合）的阻斷該算數")

    def test_a_session_start_brief_is_not_evidence_but_a_guards_notice_is(self) -> None:
        brief = ("[SDD-CTX-GUARD] context：本 session 尚無量測（新視窗）；額度：cap=2 "
                 "band=unmeasured；現查 python tools/session_resume_planner.py --check／--pace")
        self.assertTrue(G.BLOCK_EVIDENCE_RE.search(brief), "前提失效：簡報字面不在詞表內")
        opening = [self._human(_at(0)), self._context(_at(1), "SessionStart", brief)]
        self.assertTrue(self._hits(opening), "SessionStart 簡報替宣稱背書了")
        done = self._run(opening)
        self.assertEqual(done.returncode, 0)
        self.assertIn("被擋／水位", done.stderr)
        for event in ("PreToolUse", "PostToolUse"):
            with self.subTest(hookEvent=event):
                lines = [self._human(_at(0)), self._context(_at(1), event, brief)]
                self.assertEqual(self._hits(lines), [])

    def test_the_alert_names_the_structured_field_and_the_defect(self) -> None:
        done = self._run([self._human(_at(0))])
        self.assertIn("被擋／水位", done.stderr)
        for needle in ("toolDenialKind", "DEF-200-428"):
            self.assertIn(needle, done.stderr)

    def test_the_live_record_shape_is_read_end_to_end(self) -> None:
        live = self._result(
            _at(1), _HOOK_BLOCK_TEXT, is_error=True, toolDenialKind="permission-rule",
            toolUseResult="Error: " + _HOOK_BLOCK_TEXT, sourceToolAssistantUUID="a1",
            version="2.1.284", userType="external", isSidechain=False)
        done = self._run([self._human(_at(0)), live, self._human(_at(2))])
        self.assertEqual(done.returncode, 0)
        self.assertNotIn("被擋／水位", done.stderr)

    def test_odd_record_shapes_never_raise(self) -> None:
        """`main()` 吞例外 ⇒ 這裡一拋五個判準整場靜默；怪形狀（含不可雜湊 `hookEvent`）不得拋。"""
        errors = [{"type": "tool_result", "is_error": True, "content": None},
                  {"type": "tool_result", "is_error": True, "content": [None, 5, {"text": None}]}]
        odd = ({}, {"type": "user"}, {"type": "assistant", "toolDenialKind": "x"},
               {"type": "user", "message": "x"}, {"type": "user", "message": {"content": "x"}},
               {"type": "user", "message": {"content": [None, "x", 3, {"type": "tool_result"}]}},
               {"type": "user", "message": {"content": errors}})
        for record in odd:
            with self.subTest(record=record):
                self.assertIsNone(G._tool_denial_kind(record))
        self.assertTrue(G._tool_denial_kind({"type": "user", "toolDenialKind": {"k": 1}}))
        att = {"attachment": {"type": "hook_additional_context", "hookEvent": ["SessionStart"],
                              "content": ["x"]}}
        text = G._block_evidence_text([att, {"tool_denial": "k"}, None, "x"])
        self.assertIn("x", text)
        self.assertIn(G._DENIAL_MARK, text)
        # 內部旗標必須是不可列印字元：可讀字面會在 Read 到本 hook 原始碼時被當成佐證（自洗白）。
        self.assertFalse(G._DENIAL_MARK.isprintable())


if __name__ == "__main__":
    unittest.main()
