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
from datetime import UTC, datetime, timedelta
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

#: `PACE_AXES` 裡不在 `quota_policy.KNOWN_KINDS` 的軸——**登記的例外，只准變小**。
_AXES_OUTSIDE_KNOWN_KINDS = frozenset({"nimbus_quill"})

#: 第三個判準的固定「現在」。用固定時刻而不是 `datetime.now()`：age 是判準的輸入，
#: 讓它隨牆上時鐘漂移＝把測試變成非決定性的（本 repo 對脆弱綠有判例）。
_NOW = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)


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


# ─────────────────────────────────────────────────────────────────────────────
# 第三個判準（本輪 M1~M8）：引述一個已經過期的額度讀數
# ─────────────────────────────────────────────────────────────────────────────

def _pace_line(axis: str = "session", pct: str = "16") -> str:
    """一行**看起來就是 pace 輸出**的讀數（判準要求同行帶 pace 欄位記號）。"""
    return f"kind={axis} {pct}% 剩 128 分鐘 band=free horizon=mid cap=8"


class TestTheEscapeHatchIsArithmeticNotPresence(unittest.TestCase):
    """🔴 **本組是本輪否決權複審 M2＋M4 的直接產物，斷言方向刻意與規格版相反。**

    規格版寫的紅綠自證是「插入 4 小時前的『量測於』⇒ 回空清單」——那**把事故寫成契約**：
    立案的事故形狀就是「把四小時前的 pace 區塊整塊貼上」，而那份規格會讓那個動作**變成
    合法的靜音手法**。複審量到的代價：在整個母體上，「在場即抑制」型抑制器**一次都沒有
    做對過** ⇒ 它不是逃生口，是隨機靜音器。

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

    複審實測：不夾 ⇒ 一個 prompt 9 次 Stop、9 則零內容 assistant 訊息；夾了 ⇒ 2 次 Stop、
    1 次發射、恰好 1 個額外回合。而 stderr 那條**送不到模型**（`DEF-200-135`：exit 0 的
    stderr 不進 context，實測 1h49m／45 turns 零訊號）⇒ 唯一有效通道就是會迴圈的那一條。
    """

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
        env = {**os.environ, "AUTOSDD_TRACE_DIR": self._dir.name}
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
            env = {**os.environ, "AUTOSDD_PACE_GUARD_OFF": "1",
                   "AUTOSDD_TRACE_DIR": tmp}
            done = subprocess.run([sys.executable, str(_HOOK)], input=payload, env=env,
                                  capture_output=True, text=True, timeout=60,
                                  encoding="utf-8", errors="replace")
        self.assertEqual(done.returncode, 0)
        self.assertNotIn("錨不到", done.stderr, "逃生口沒有真的關掉本判準")
        self.assertIn("99991", done.stderr, "另一個判準被順手關掉了")


if __name__ == "__main__":
    unittest.main()
