#!/usr/bin/env python3
"""tools/check_script_parity.py 的單元測試（R9 跨平台複審落地）。

守兩個「靜默退出守護範圍」的回歸鎖：
  1. gate 呼叫抽取須同時接受單/雙引號——舊版只認單引號，兩側同步改雙引號時
     該 gate 會靜默消失於比對清單且雙邊一致、無任何 diff 訊號。
  2. 抽取數量下限釘選（_MIN_EXTRACT_COUNTS）——宣告 pattern 被同步改寫時，
     數量低於釘選值必須紅燈，不得假綠。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import atexit
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_script_parity as m  # noqa: E402

# 系統暫存目錄放測試用 fixture 檔（非 repo 內），process 結束自動清除。
_TMP_DIR = Path(tempfile.mkdtemp(prefix="script_parity_test_"))
atexit.register(lambda: shutil.rmtree(_TMP_DIR, ignore_errors=True))
_tmp_counter = [0]


def _write_tmp(text: str, suffix: str = ".sh") -> Path:
    _tmp_counter[0] += 1
    p = _TMP_DIR / f"fixture_{_tmp_counter[0]}{suffix}"
    p.write_text(text, encoding="utf-8")
    return p


# （歷史：TestExtractGateCallsQuoteStyles 隨 local_ci_gate R12 薄殼化收斂移除——
#   gate-call 抽取已自 check_script_parity 退場，該對改由 thinness hash 釘選守門。）


class TestExtractFloor(unittest.TestCase):
    """R16 起改用合成 label（mock.patch.dict 注入），不再耦合 bootstrap/run_act 這類
    實際登記——三對已於 R16 薄殼化收斂退出 _MIN_EXTRACT_COUNTS（見 check_script_parity
    檔頭），若測試繼續硬編實際 key，下次任何一對再退場又會無關地弄壞這裡。"""

    def test_below_floor_is_red(self) -> None:
        """R9 回歸鎖：任一側抽取數量低於 _MIN_EXTRACT_COUNTS 釘選即紅燈——
        即使雙邊清單完全一致（同步改壞宣告 pattern 的典型形狀）。"""
        with mock.patch.dict(m._MIN_EXTRACT_COUNTS, {"_synthetic": 6}):
            short = [f"step {i}" for i in range(5)]
            with mock.patch("builtins.print"):
                self.assertFalse(m._check_extract_floor("_synthetic", short, short))

    def test_at_floor_passes(self) -> None:
        with mock.patch.dict(m._MIN_EXTRACT_COUNTS, {"_synthetic": 6}):
            items = [f"step {i}" for i in range(6)]
            with mock.patch("builtins.print"):
                self.assertTrue(m._check_extract_floor("_synthetic", items, items))

    def test_red_message_points_to_pin_update(self) -> None:
        """紅燈訊息必須指路：刻意刪減 step 時要同步更新釘選值（訊息說清楚）。"""
        with mock.patch.dict(m._MIN_EXTRACT_COUNTS, {"_synthetic": 2}):
            with mock.patch("builtins.print") as fake_print:
                m._check_extract_floor("_synthetic", ["a"], ["a"])
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("_MIN_EXTRACT_COUNTS", printed)
        self.assertIn("_synthetic", printed)


class TestPairEnrollment(unittest.TestCase):
    """R10 拍板案(a)（DEF-101-134）：成對腳本註冊完整性發現鎖。

    WHY：marker_pairs / thinness 對象皆硬編碼——過去新增一對 .sh/.ps1 而不掛
    任何守門是零訊號的結構性缺口（Architect『新增腳本可繞過 parity 守門』）。
    此鎖使未納管對子紅燈、註冊清單 stale 亦紅燈。
    """

    def test_real_tree_enrollment_passes(self) -> None:
        self.assertTrue(m._check_pair_enrollment())

    def test_unknown_pair_detected(self) -> None:
        fake_root = _TMP_DIR / "enroll_unknown"
        (fake_root / "tools").mkdir(parents=True, exist_ok=True)
        (fake_root / "tools" / "rogue_pair.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (fake_root / "tools" / "rogue_pair.ps1").write_text("# x\n", encoding="utf-8")
        with mock.patch.object(m, "_REPO_ROOT", fake_root), \
             mock.patch("builtins.print") as fake_print:
            ok = m._check_pair_enrollment()
        self.assertFalse(ok)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("rogue_pair", printed)
        self.assertIn("未註冊的成對腳本", printed)

    def test_stale_registration_detected(self) -> None:
        fake_root = _TMP_DIR / "enroll_stale"
        (fake_root / "tools").mkdir(parents=True, exist_ok=True)  # 空目錄，無任何對子
        with mock.patch.object(m, "_REPO_ROOT", fake_root), \
             mock.patch("builtins.print") as fake_print:
            ok = m._check_pair_enrollment()
        self.assertFalse(ok)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("stale", printed)


class TestSingleSidedEnrollment(unittest.TestCase):
    """R11 架構改善 C2：單邊（孤兒）腳本納管發現鎖。

    WHY：R11 前 _discover_pairs 只認同名成對——新增一支只有 .sh 或只有 .ps1 的
    腳本零機械訊號（跨平台對等從未被追問）。此鎖使未登記單邊紅燈、豁免清單
    stale（檔案消失或對邊已出現）亦紅燈。
    """

    @staticmethod
    def _patched(fake_root: Path, single_exempt: dict[str, str]):
        """把全部註冊清單 mock 成空、只保留受測的單邊豁免——隔離真 repo 清單。

        R12 起 _check_pair_enrollment 內建 LATEST 解析（fail-loud），fixture 假
        root 無 sdd_version.py 會誤紅——mock _resolve_latest_tools 指向 fixture
        內的空 LATEST tools 目錄（掃描邊界存在但無腳本，中立於受測情境）。"""
        latest_tools = fake_root / "_latest_tools"
        latest_tools.mkdir(parents=True, exist_ok=True)
        return (
            mock.patch.object(m, "_REPO_ROOT", fake_root),
            mock.patch.object(m, "_MARKER_PAIRS", []),
            mock.patch.object(m, "_THINNESS_ENROLLED", set()),
            mock.patch.object(m, "_EXEMPT_PAIRS", {}),
            mock.patch.object(m, "_SINGLE_SIDED_EXEMPT", single_exempt),
            mock.patch.object(m, "_LATEST_THINNESS_ENROLLED", set()),
            mock.patch.object(m, "_resolve_latest_tools", lambda: latest_tools),
        )

    def _run_enrollment(self, fake_root: Path, single_exempt: dict[str, str]):
        patches = self._patched(fake_root, single_exempt)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], \
             patches[6], \
             mock.patch("builtins.print") as fake_print:
            ok = m._check_pair_enrollment()
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        return ok, printed

    def test_unregistered_single_sided_script_fails(self) -> None:
        """反例：磁碟上有未登記的單邊腳本 → 必紅並點名。"""
        fake_root = _TMP_DIR / "single_unknown"
        (fake_root / "tools").mkdir(parents=True, exist_ok=True)
        (fake_root / "tools" / "rogue_single.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        ok, printed = self._run_enrollment(fake_root, {})
        self.assertFalse(ok)
        self.assertIn("rogue_single.sh", printed)
        self.assertIn("未納管的單邊腳本", printed)

    def test_exempted_single_sided_script_passes(self) -> None:
        """正例：已附決策依據登記的單邊腳本 → 綠。"""
        fake_root = _TMP_DIR / "single_exempt"
        (fake_root / "tools").mkdir(parents=True, exist_ok=True)
        (fake_root / "tools" / "lonely.ps1").write_text("# x\n", encoding="utf-8")
        ok, printed = self._run_enrollment(
            fake_root, {"tools/lonely.ps1": "測試豁免依據"}
        )
        self.assertTrue(ok, f"已豁免單邊不應紅燈，輸出：{printed}")

    def test_stale_single_sided_exemption_file_gone_fails(self) -> None:
        """stale 之一：豁免清單條目的檔案已消失 → 紅（防清單腐化）。"""
        fake_root = _TMP_DIR / "single_stale_gone"
        (fake_root / "tools").mkdir(parents=True, exist_ok=True)
        ok, printed = self._run_enrollment(
            fake_root, {"tools/ghost.sh": "測試豁免依據"}
        )
        self.assertFalse(ok)
        self.assertIn("ghost.sh", printed)
        self.assertIn("stale", printed)

    def test_stale_single_sided_exemption_pair_appeared_fails(self) -> None:
        """stale 之二：對邊腳本已出現（不再是單邊）→ 紅並指路重新納管——
        run_local_nightly.sh 已於 R11（DEF-101-163）落地並依本語意轉登記為
        _EXEMPT_PAIRS 成對豁免（本案例正是當時實際出訊號的機制）。"""
        fake_root = _TMP_DIR / "single_stale_paired"
        (fake_root / "tools").mkdir(parents=True, exist_ok=True)
        (fake_root / "tools" / "lonely.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (fake_root / "tools" / "lonely.ps1").write_text("# x\n", encoding="utf-8")
        ok, printed = self._run_enrollment(
            fake_root, {"tools/lonely.ps1": "測試豁免依據"}
        )
        self.assertFalse(ok)
        self.assertIn("對邊腳本已出現", printed)
        self.assertIn("未註冊的成對腳本", printed)  # 新對子 unknown 的第二訊號


class TestR13LibAndInstallerEnrollment(unittest.TestCase):
    """R13 ARCH-R13-4／CI-3：tools/lib 納入掃描邊界＋mac nightly 安裝器單邊納管。

    WHY：tools/lib/ 三支（install 共用層「異名對等品」×2＋PowerShell 專屬 helper）
    過去完全在 _PAIR_SCAN_DIRS 邊界外——增刪/改名零機械訊號；install_mac_nightly.sh
    （R13 ARCH-R13-3 launchd 安裝器）為新增單邊 .sh，皆須附決策依據納管。
    計數註記（R13 擴充依據）：「13 對＋11 支單邊」是 R12 時期工具的動態實跑輸出、
    並無任何測試釘選值鎖定該計數（enrollment 守護靠 unknown/stale 名單而非總數），
    R13 擴面後實跑輸出為 13 對＋15 支單邊，無需同步任何釘選。
    """

    _R13_SINGLES = (
        "tools/lib/git_hooks_install_common.sh",
        "tools/lib/GitHooksInstallCommon.ps1",
        "tools/lib/Find-GitBash.ps1",
        "tools/install_mac_nightly.sh",
    )

    def test_tools_lib_covered_by_scan_surface(self) -> None:
        """掃描邊界必**涵蓋** tools/lib（回退即紅——邊界縮面零訊號的防護本體）。

        R60 Scan-E E-A-01 訂正：掃描根自此收斂為 SSOT `SCRIPT_SCAN_ROOTS` 三棵樹且
        **遞迴**，`tools/lib` 由 `tools` 樹自動涵蓋、不再單獨列名，故原斷言
        `assertIn("tools/lib", _PAIR_SCAN_DIRS)` 對新形狀已無意義（它會在「掃描面
        其實變大了」的情況下翻紅，激勵方向相反）。改鎖語意本體兩層：① `tools/lib`
        必須落在某個掃描根底下；② 真磁碟上該目錄的腳本必須**真的被列舉到**——
        後者才是「非遞迴回退」會踩到的斷言（遞迴性本體另由
        `tools/tests/test_script_scan_surface_ssot.py` 以合成假樹守，不依賴 repo 現況）。
        """
        covered = [
            root for root in m._PAIR_SCAN_DIRS
            if root == "tools/lib" or "tools/lib".startswith(f"{root}/")
        ]
        self.assertTrue(
            covered,
            f"tools/lib 不在任何掃描根底下（名冊={m._PAIR_SCAN_DIRS}）——邊界縮面",
        )
        listed = [
            rel for rel in m.iter_tree_scripts(m._REPO_ROOT)
            if rel.startswith("tools/lib/")
        ]
        self.assertTrue(
            listed,
            "tools/lib 底下一支腳本都沒被列舉到——掃描面疑似退回非遞迴（R60 E-A-01 迴歸）",
        )

    def test_r13_singles_exempted_with_rationale(self) -> None:
        """四支 R13 納管腳本必在單邊豁免表且附非空決策依據。

        R63（ADR-XPLAT-002 Phase 1-C (b)）：值由純字串升級為 `(tier, reason)`
        二元組，取 `[1]`（reason）驗證非空——語意與 R13 原始斷言不變。"""
        for rel in self._R13_SINGLES:
            self.assertIn(rel, m._SINGLE_SIDED_EXEMPT,
                          f"{rel} 未登記 _SINGLE_SIDED_EXEMPT——R13 納管回退")
            self.assertTrue(m._SINGLE_SIDED_EXEMPT[rel][1].strip(),
                            f"{rel} 的豁免依據為空——豁免必須附 WHY")

    def test_real_tree_r13_singles_discovered(self) -> None:
        """真磁碟整合：四支確實被掃描「發現」為單邊（不只是表上有名字）——
        豁免表條目若失去磁碟對應物，另有 stale 反向檢查兜底；此處鎖正向：
        掃描器真的看得到它們（tools/lib 目錄真的入掃）。"""
        latest_tools = m._resolve_latest_tools()
        self.assertIsNotNone(latest_tools, "真 repo 內 LATEST 解析不得失敗（fail-loud）")
        _pairs, singles = m._discover_scripts(latest_tools)
        for rel in self._R13_SINGLES:
            self.assertIn(rel, singles, f"{rel} 未被掃描發現——掃描邊界疑似回退")


class TestLatestToolsEnrollment(unittest.TestCase):
    """R12 ARCH-R12-3：LATEST 版 tools 遞迴掃描納管完整性。

    WHY：v0.30 tools 下 4 對同名 .sh/.ps1 完全在 _PAIR_SCAN_DIRS 邊界外（其中
    run_tlc 有 DEF-101-100 實證漂移前科），新增/移除 LATEST 對子過去零機械訊號。
    """

    def test_latest_rogue_pair_in_subdir_detected(self) -> None:
        """遞迴掃描：LATEST tools 子目錄深處的未登記對子必紅（非遞迴會漏）。"""
        fake_root = _TMP_DIR / "latest_rogue"
        latest_tools = fake_root / "_latest_tools"
        deep = latest_tools / "sub" / "deep"
        deep.mkdir(parents=True, exist_ok=True)
        (deep / "rogue.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (deep / "rogue.ps1").write_text("# x\n", encoding="utf-8")
        with mock.patch.object(m, "_REPO_ROOT", fake_root), \
             mock.patch.object(m, "_MARKER_PAIRS", []), \
             mock.patch.object(m, "_THINNESS_ENROLLED", set()), \
             mock.patch.object(m, "_EXEMPT_PAIRS", {}), \
             mock.patch.object(m, "_SINGLE_SIDED_EXEMPT", {}), \
             mock.patch.object(m, "_LATEST_THINNESS_ENROLLED", set()), \
             mock.patch("builtins.print") as fake_print:
            ok = m._check_pair_enrollment(latest_tools)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertFalse(ok)
        self.assertIn("LATEST/tools/sub/deep/rogue", printed)

    def test_latest_resolution_failure_is_fail_loud_red(self) -> None:
        """LATEST 解析失敗（SSOT 缺席/執行失敗）→ 紅燈，不得靜默縮小掃描邊界。"""
        fake_root = _TMP_DIR / "latest_fail"
        (fake_root / "tools").mkdir(parents=True, exist_ok=True)
        with mock.patch.object(m, "_REPO_ROOT", fake_root), \
             mock.patch.object(m, "_resolve_latest_tools", lambda: None), \
             mock.patch("builtins.print") as fake_print:
            ok = m._check_pair_enrollment()
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertFalse(ok)
        self.assertIn("LATEST 解析失敗", printed)

    def test_real_tree_latest_pairs_all_enrolled(self) -> None:
        """真磁碟整合：LATEST 四對＋verify_traceability.sh 單邊皆已納管（綠）。"""
        latest_tools = m._resolve_latest_tools()
        self.assertIsNotNone(latest_tools, "真 repo 內 LATEST 解析不得失敗（fail-loud）")
        pairs, singles = m._discover_scripts(latest_tools)
        latest_pairs = [p for p in pairs if p.startswith(m._LATEST_PREFIX)]
        self.assertIn("LATEST/tools/fsm_runtime/formal/run_tlc", latest_pairs)
        known = m._enrolled_pairs()
        self.assertEqual([p for p in latest_pairs if p not in known], [],
                         "LATEST 成對腳本必須全數納管")
        latest_singles = [s for s in singles if s.startswith(m._LATEST_PREFIX)]
        for s in latest_singles:
            self.assertIn(s, m._SINGLE_SIDED_EXEMPT,
                          f"LATEST 單邊腳本 {s} 未附決策依據登記")


class TestRunTlcInvocationParityLock(unittest.TestCase):
    """R65（ADR-XPLAT-002 §5 Phase 2-A）：取代退場的 run_tlc FSM 軌錨點集合鎖
    （原 `_check_run_tlc_tracks`）。run_tlc.{sh,ps1} 薄殼化後兩側已不再內嵌
    `.tla`/`.cfg` 檔名字面（舊鎖的抽取對象消失），但「兩側委派引數仍可能分歧」
    （DEF-101-100 攔的正是這型漂移：.ps1 曾缺整條 FLEET_FSM 軌而 .sh 有）這個
    風險本身沒有消失——依 ADR §4.2 rule 3 dominance test，此斷言沒有現成接手者，
    改抽兩側委派 `tools.fsm_runtime.tlc_runner` 時傳的 `--module`/`--cfg` 引數
    token 做同型 multiset 比對，延續同一個保護意圖，只是換一個新形態下仍存在
    的錨點（fixture 注入變異，同 R12 原測試手法）。
    """

    _SH_FULL = (
        "#!/usr/bin/env bash\n"
        "# 註解裡的 --module GHOST_FSM 不得入抽取\n"
        "python -m tools.fsm_runtime.tlc_runner --module SDD_FSM --depth 50\n"
        "python -m tools.fsm_runtime.tlc_runner --module FLEET_FSM\n"
        "python -m tools.fsm_runtime.tlc_runner --module FLEET_FSM --cfg FLEET_FSM_LIVENESS.cfg\n"
    )

    def _make_pair(self, name: str, sh_body: str, ps1_body: str) -> Path:
        latest_tools = _TMP_DIR / name / "tools"
        formal = latest_tools / "fsm_runtime" / "formal"
        formal.mkdir(parents=True, exist_ok=True)
        (formal / "run_tlc.sh").write_text(sh_body, encoding="utf-8")
        (formal / "run_tlc.ps1").write_text(ps1_body, encoding="utf-8")
        return latest_tools

    def test_matching_invocations_green(self) -> None:
        ps1 = self._SH_FULL.replace(
            "python -m tools.fsm_runtime.tlc_runner",
            "& python -m tools.fsm_runtime.tlc_runner",
        )  # 形態不同、token 相同
        latest_tools = self._make_pair("inv_green", self._SH_FULL, ps1)
        with mock.patch("builtins.print"):
            self.assertTrue(m._check_run_tlc_invocation_parity(latest_tools))

    def test_missing_fleet_invocation_on_ps1_is_red(self) -> None:
        """變異自證：.ps1 刪整條 FLEET 委派（DEF-101-100 原型換新錨點）→ 必紅。"""
        ps1_lines = [ln for ln in self._SH_FULL.splitlines() if "FLEET" not in ln]
        latest_tools = self._make_pair(
            "inv_red", self._SH_FULL, "\n".join(ps1_lines) + "\n")
        with mock.patch("builtins.print") as fake_print:
            ok = m._check_run_tlc_invocation_parity(latest_tools)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertFalse(ok)
        self.assertIn("FLEET_FSM", printed)

    def test_comment_only_invocations_not_extracted(self) -> None:
        """註解行的引數字樣不入抽取（--module GHOST_FSM 只出現在 # 註解）。"""
        latest_tools = self._make_pair("inv_comment", self._SH_FULL, self._SH_FULL)
        args = m._extract_tlc_runner_invocations(
            latest_tools / "fsm_runtime" / "formal" / "run_tlc.sh")
        self.assertNotIn("--module GHOST_FSM", args)
        # multiset 語意：--module FLEET_FSM 兩處引用各自入列 → 4 個 token
        self.assertEqual(len(args), 4, f"引數 multiset 應恰為 4，實得 {args}")

    def test_floor_pins_four_invocations(self) -> None:
        """釘選：兩側同步刪到 3 個引數（floor=4 以下）也必紅——防同步改寫假綠。"""
        three = "\n".join(
            ln for ln in self._SH_FULL.splitlines() if "LIVENESS" not in ln) + "\n"
        latest_tools = self._make_pair("inv_floor", three, three)
        with mock.patch("builtins.print"):
            self.assertFalse(m._check_run_tlc_invocation_parity(latest_tools))

    def test_renamed_invocation_same_count_is_red_via_compare(self) -> None:
        """兩側皆 ≥floor 但集合不同（單側改名）必紅——_compare 專屬路徑回歸鎖。

        WHY（同 R12 原測試手法）：其餘紅案例的 token 數同時低於 floor，floor 與
        _compare 雙訊號並發；_compare 被突變恆 True 時它們仍紅、改名型漂移卻會漏。
        本案例兩側各 4 token（等量）僅名字不同——只有 _compare 能攔。"""
        renamed = self._SH_FULL.replace("SDD_FSM", "SDX_FSM")
        latest_tools = self._make_pair("inv_rename", self._SH_FULL, renamed)
        with mock.patch("builtins.print") as fake_print:
            self.assertFalse(m._check_run_tlc_invocation_parity(latest_tools))
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("SDX_FSM", printed, "diff 須點名改名後的 token")

    def test_missing_script_is_red(self) -> None:
        """run_tlc 檔案消失 → 紅（指路更新 _LATEST_THINNESS_ENROLLED）。"""
        empty = _TMP_DIR / "inv_missing" / "tools"
        empty.mkdir(parents=True, exist_ok=True)
        with mock.patch("builtins.print"):
            self.assertFalse(m._check_run_tlc_invocation_parity(empty))

    def test_real_tree_run_tlc_green(self) -> None:
        """真磁碟整合：LATEST run_tlc 兩側委派引數集合一致（R65 薄殼化後狀態）。"""
        latest_tools = m._resolve_latest_tools()
        self.assertIsNotNone(latest_tools)
        with mock.patch("builtins.print"):
            self.assertTrue(m._check_run_tlc_invocation_parity(latest_tools))


class TestLatestThinnessPin(unittest.TestCase):
    """R65（ADR-XPLAT-002 §5 Phase 2-A）：LATEST 版薄殼 hash 釘選
    （`_check_latest_thinness`）紅/綠自證——接手退場的 `_TLC_TRACK_ENROLLED` 的
    「run_tlc.{sh,ps1} 兩側檔案存在、內容未偏離已核准樣子」這條斷言，且比舊鎖更
    嚴格（舊鎖只比對抽取到的軌 token 集合，本鎖鎖住整份正規化內容——任何實質
    修改，不論是否影響 --module/--cfg 引數，都會先在這裡紅燈）。
    """

    def _make_shell_tree(self, name: str, sh_body: str, ps1_body: str) -> Path:
        latest_tools = _TMP_DIR / name / "tools"
        formal = latest_tools / "fsm_runtime" / "formal"
        formal.mkdir(parents=True, exist_ok=True)
        (formal / "run_tlc.sh").write_text(sh_body, encoding="utf-8")
        (formal / "run_tlc.ps1").write_text(ps1_body, encoding="utf-8")
        return latest_tools

    def test_real_tree_pins_green(self) -> None:
        latest_tools = m._resolve_latest_tools()
        self.assertIsNotNone(latest_tools)
        with mock.patch("builtins.print"):
            self.assertTrue(m._check_latest_thinness(latest_tools))

    def test_tampered_content_is_red(self) -> None:
        """正規化內容偏離釘選 → 紅（hash 釘選是權威判定，不是抽取式比對）。"""
        latest_tools = self._make_shell_tree(
            "thin_tamper", "#!/usr/bin/env bash\necho tampered\n", "echo tampered\n")
        fake_pins = {
            "LATEST/tools/fsm_runtime/formal/run_tlc.sh": "0" * 64,
            "LATEST/tools/fsm_runtime/formal/run_tlc.ps1": "0" * 64,
        }
        with mock.patch.object(m, "_LATEST_PINNED_SHA256", fake_pins), \
             mock.patch("builtins.print") as fake_print:
            ok = m._check_latest_thinness(latest_tools)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertFalse(ok)
        self.assertIn("hash 與釘選不符", printed)

    def test_missing_file_is_red(self) -> None:
        empty = _TMP_DIR / "thin_missing" / "tools"
        empty.mkdir(parents=True, exist_ok=True)
        fake_pins = {"LATEST/tools/fsm_runtime/formal/run_tlc.sh": "0" * 64}
        with mock.patch.object(m, "_LATEST_PINNED_SHA256", fake_pins), \
             mock.patch("builtins.print") as fake_print:
            ok = m._check_latest_thinness(empty)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertFalse(ok)
        self.assertIn("檔案不存在", printed)

    def test_latest_resolution_failure_is_red(self) -> None:
        fake_pins = {"LATEST/tools/fsm_runtime/formal/run_tlc.sh": "0" * 64}
        with mock.patch.object(m, "_LATEST_PINNED_SHA256", fake_pins), \
             mock.patch("builtins.print") as fake_print:
            ok = m._check_latest_thinness(None)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertFalse(ok)
        self.assertIn("LATEST 解析失敗", printed)

    def test_line_count_over_max_lines_is_red(self) -> None:
        import check_wrapper_thinness as _thinness

        body = "#!/usr/bin/env bash\n" + "echo x\n" * (_thinness.MAX_LINES + 5)
        latest_tools = self._make_shell_tree("thin_toolong", body, "echo x\n")
        fake_pins = {
            "LATEST/tools/fsm_runtime/formal/run_tlc.sh": _thinness.normalized_sha256(
                latest_tools / "fsm_runtime" / "formal" / "run_tlc.sh"),
        }
        with mock.patch.object(m, "_LATEST_PINNED_SHA256", fake_pins), \
             mock.patch("builtins.print") as fake_print:
            ok = m._check_latest_thinness(latest_tools)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertFalse(ok)
        self.assertIn("超過薄殼上限", printed)


class TestThinnessCrossLock(unittest.TestCase):
    """parity↔thinness 鍵集合交叉鎖（R12 QA 一審 QA-1）。

    WHY：兩份獨立字面清單（_THINNESS_ENROLLED vs _PINNED_SHA256）同 commit 雙邊
    各刪一行即雙工具全綠——交叉鎖使任一邊單獨腐化必紅。"""

    def test_current_tables_consistent_green(self) -> None:
        with mock.patch("builtins.print"):
            self.assertTrue(m._check_thinness_cross_lock())

    def test_missing_pin_key_is_red(self) -> None:
        import check_wrapper_thinness as t
        pins = {k: v for k, v in t._PINNED_SHA256.items()
                if k != "AutoClaude/tools/local_ci_gate.ps1"}
        with mock.patch.object(t, "_PINNED_SHA256", pins), \
             mock.patch("builtins.print") as fake_print:
            self.assertFalse(m._check_thinness_cross_lock())
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("local_ci_gate.ps1", printed)

    def test_extra_pin_without_enrollment_is_red(self) -> None:
        import check_wrapper_thinness as t
        pins = dict(t._PINNED_SHA256)
        pins["tools/rogue_wrapper.sh"] = "0" * 64
        with mock.patch.object(t, "_PINNED_SHA256", pins), \
             mock.patch("builtins.print") as fake_print:
            self.assertFalse(m._check_thinness_cross_lock())
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("rogue_wrapper.sh", printed)


class TestLatestThinnessCrossLock(unittest.TestCase):
    """LATEST 版 parity↔thinness 鍵集合交叉鎖（R66 DEF-101-622，同 R12 QA-1 教訓
    套用於 R65 新表 _LATEST_THINNESS_ENROLLED／_LATEST_PINNED_SHA256）。

    WHY：兩份獨立字面清單同一 commit 各自腐化（清空 pin 表但不動 enrollment 集合）
    若無交叉鎖，`_check_latest_thinness()` 的迴圈只走 `_LATEST_PINNED_SHA256`，
    清空後迴圈次數為零、恆回傳 True，且會印出自相矛盾的「0 支 hash 釘選皆正常」
    訊息——本鎖必須攔下這個情境。"""

    def test_current_tables_consistent_green(self) -> None:
        with mock.patch("builtins.print"):
            self.assertTrue(m._check_latest_thinness_cross_lock())

    def test_bug_injection_cleared_pins_still_enrolled_is_red(self) -> None:
        """紅：清空 _LATEST_PINNED_SHA256、不動 _LATEST_THINNESS_ENROLLED——這正是
        缺陷描述裡實測過的自相矛盾情境（_check_latest_thinness 本身會誤判綠燈，
        本鎖須攔下）。"""
        with mock.patch.object(m, "_LATEST_PINNED_SHA256", {}), \
             mock.patch("builtins.print") as fake_print:
            self.assertFalse(m._check_latest_thinness_cross_lock())
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("run_tlc.sh", printed)
        self.assertIn("run_tlc.ps1", printed)

    def test_missing_pin_key_is_red(self) -> None:
        pins = {
            k: v for k, v in m._LATEST_PINNED_SHA256.items()
            if k != "LATEST/tools/fsm_runtime/formal/run_tlc.ps1"
        }
        with mock.patch.object(m, "_LATEST_PINNED_SHA256", pins), \
             mock.patch("builtins.print") as fake_print:
            self.assertFalse(m._check_latest_thinness_cross_lock())
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("run_tlc.ps1", printed)

    def test_extra_pin_without_enrollment_is_red(self) -> None:
        pins = dict(m._LATEST_PINNED_SHA256)
        pins["LATEST/tools/rogue_wrapper.sh"] = "0" * 64
        with mock.patch.object(m, "_LATEST_PINNED_SHA256", pins), \
             mock.patch("builtins.print") as fake_print:
            self.assertFalse(m._check_latest_thinness_cross_lock())
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("rogue_wrapper.sh", printed)


class TestGitLongpathsFlagParity(unittest.TestCase):
    """R50 四方複審發現：macos_smoke_local.sh／windows_smoke_local.ps1 各自獨立
    內嵌 `-c core.longpaths=true` git flag；_SINGLE_SIDED_EXEMPT 過去只登記兩檔
    互為異名對等品的存在性，未比對旗標內容——若任一側遺漏或改動，parity 工具
    先前不會有任何機械訊號。本測試證明新增的 `_check_git_longpaths_flag_parity()`
    確實能攔下這個此前的零訊號窗（red→green 對照）。"""

    def _make_repo(self, macos_body: str, windows_body: str) -> Path:
        root = _TMP_DIR / f"longpaths_repo_{_tmp_counter[0]}"
        _tmp_counter[0] += 1
        (root / "tools").mkdir(parents=True, exist_ok=True)
        (root / "tools" / "macos_smoke_local.sh").write_text(macos_body, encoding="utf-8")
        (root / "tools" / "windows_smoke_local.ps1").write_text(windows_body, encoding="utf-8")
        return root

    def test_current_repo_files_have_flag_on_both_sides_green(self) -> None:
        """現況（真實 repo 檔案）：兩側皆含旗標，應綠燈——先確認未誤傷現況。"""
        with mock.patch("builtins.print"):
            self.assertTrue(m._check_git_longpaths_flag_parity())

    def test_both_sides_present_is_green(self) -> None:
        root = self._make_repo(
            'git clone --quiet -c core.longpaths=true "$X" "$Y"\n',
            "git clone --quiet -c core.longpaths=true $X $Y\n",
        )
        with mock.patch.object(m, "_REPO_ROOT", root), mock.patch("builtins.print"):
            self.assertTrue(m._check_git_longpaths_flag_parity())

    def test_macos_side_missing_flag_is_red(self) -> None:
        """回歸重現：mac 側意外遺漏旗標（如維護時複製貼上漏帶），先前 parity
        工具對此零訊號——本測試證明新鎖能攔下。"""
        root = self._make_repo(
            'git clone --quiet "$X" "$Y"\n',
            "git clone --quiet -c core.longpaths=true $X $Y\n",
        )
        with mock.patch.object(m, "_REPO_ROOT", root), \
             mock.patch("builtins.print") as fake_print:
            self.assertFalse(m._check_git_longpaths_flag_parity())
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("macos_smoke_local.sh", printed)

    def test_windows_side_missing_flag_is_red(self) -> None:
        root = self._make_repo(
            'git clone --quiet -c core.longpaths=true "$X" "$Y"\n',
            "git clone --quiet $X $Y\n",
        )
        with mock.patch.object(m, "_REPO_ROOT", root), \
             mock.patch("builtins.print") as fake_print:
            self.assertFalse(m._check_git_longpaths_flag_parity())
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("windows_smoke_local.ps1", printed)


class TestR61Phase1BMigration(unittest.TestCase):
    """ADR-XPLAT-002 Phase 1-B（R61）：`install_git_hooks`／`install-hooks` 兩對由
    `_EXEMPT_PAIRS`（零守門決策豁免）遷移至 `_THINNESS_ENROLLED`（hash 釘選），
    UEP 應由 8 降為 6。本測試鎖住遷移後的狀態，防止有人日後誤加回 `_EXEMPT_PAIRS`
    （殭屍豁免自檢只擋「同時掛兩邊」，不擋「加回其中一邊」）。"""

    def test_migrated_pairs_not_in_exempt_pairs(self) -> None:
        self.assertNotIn("AutoClaude/tools/install_git_hooks", m._EXEMPT_PAIRS)
        self.assertNotIn("AISDLC_SDD/scripts/install-hooks", m._EXEMPT_PAIRS)

    def test_migrated_pairs_in_thinness_enrolled(self) -> None:
        self.assertIn("AutoClaude/tools/install_git_hooks", m._THINNESS_ENROLLED)
        self.assertIn("AISDLC_SDD/scripts/install-hooks", m._THINNESS_ENROLLED)

    def test_uep_is_five_after_r65_migration(self) -> None:
        """UEP＝`_EXEMPT_PAIRS`（ADR-XPLAT-002 §4.1，R65 更新）。

        歷史：R60 基線 8 → R61 Phase 1-B 遷移兩對至 `_THINNESS_ENROLLED` 後為 6
        （公式當時是 `_EXEMPT_PAIRS` + `_TLC_TRACK_ENROLLED`）→ R65 Phase 2-A 把
        run_tlc 那唯一一筆 `_TLC_TRACK_ENROLLED` 條目也升級為 hash 釘選
        （`_LATEST_THINNESS_ENROLLED`，不計入 UEP）後，`_TLC_TRACK_ENROLLED` 本身
        退場、公式不再有該項，UEP 應為 5。本測試名稱雖冠 R61，但斷言的是「當前
        UEP 公式與數值」的活體回歸鎖（非凍結歷史快照），故隨本輪同步更新，防止
        被靜默改回。"""
        uep = len(m._EXEMPT_PAIRS)
        self.assertEqual(uep, 5)


class TestPrintCollapseFlag(unittest.TestCase):
    """R61 Phase 1-C 最小可行切片：`--print-collapse` 把 UEP／AC 從「手跑 scratchpad
    腳本才查得到」升級為本工具的第一等公民輸出（ADR-XPLAT-002 §8 未解決項 #4 的
    一部分；完整的 tier 分類重構列 R62，見 ADR 本輪裁決段）。"""

    def test_print_collapse_returns_zero_and_reports_uep_ac(self) -> None:
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = m.main(["--print-collapse"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        expected_uep = len(m._EXEMPT_PAIRS)
        self.assertIn(f"UEP={expected_uep}", out)
        self.assertIn("AC=", out)

    def test_ac_matches_sum_of_seven_registries(self) -> None:
        """AC 定義（§4.2）＝描述性常數登記表長度總和；本測試獨立重算，防止
        `_print_collapse()` 內部算式與 ADR 定義漂移卻無人發現（既有各表各自已有
        其他鎖守著不被誤刪）。R65：原「六張表」的 `_TLC_TRACK_ENROLLED` 已退場，
        改由 `_LATEST_PINNED_SHA256`／`_LATEST_THINNESS_ENROLLED` 兩張新表接手其
        「描述性常數登記」角色，故現為七張表。"""
        import io
        from contextlib import redirect_stdout

        import check_wrapper_thinness as _thinness

        expected_ac = (
            len(_thinness._PINNED_SHA256)
            + len(m._THINNESS_ENROLLED)
            + len(m._EXEMPT_PAIRS)
            + len(m._SINGLE_SIDED_EXEMPT)
            + len(m._LATEST_PINNED_SHA256)
            + len(m._LATEST_THINNESS_ENROLLED)
            + len(m._MIN_EXTRACT_COUNTS)
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            m.main(["--print-collapse"])
        self.assertIn(f"AC={expected_ac}", buf.getvalue())

    def test_no_arg_invocation_unaffected(self) -> None:
        """`--print-collapse` 是新增分支，不得影響既有無參數呼叫路徑（main() 現在
        接受可選 argv，預設仍讀 sys.argv——呼叫端零改動）。"""
        with mock.patch.object(sys, "argv", ["check_script_parity.py"]), \
             mock.patch("builtins.print"):
            rc = m.main()
        self.assertEqual(rc, 0)


class TestR63TierClassification(unittest.TestCase):
    """R63（ADR-XPLAT-002 §5 Phase 1-C (b)(d)）：`_EXEMPT_PAIRS`／`_SINGLE_SIDED_EXEMPT`
    值由純理由字串升級為 `(tier, reason)` 二元組 + tier3/4 硬理由關鍵詞斷言。

    Scan-H 紀律 #1（每一支新增／修改的鎖必附 bug-injection 紅綠實測）：本類別逐一
    構造每種違規形態並證明轉紅，另證明真 repo 現況本身是綠的。"""

    def test_real_tables_pass_tier_classification(self) -> None:
        with mock.patch("builtins.print"):
            self.assertTrue(m._check_tier_classification())

    def test_legacy_string_value_is_red(self) -> None:
        """R62 及之前的純字串值形態現在必須被判為不合法——證明型別升級是強制的，
        不是靜默相容（若靜默相容，日後有人漏轉型別也不會被抓到）。"""
        with mock.patch.object(m, "_EXEMPT_PAIRS", {"x/y": "純字串舊格式"}), \
             mock.patch.object(m, "_SINGLE_SIDED_EXEMPT", {}), \
             mock.patch("builtins.print") as fake_print:
            ok = m._check_tier_classification()
        self.assertFalse(ok)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("二元組", printed)

    def test_invalid_tier_value_is_red(self) -> None:
        with mock.patch.object(
            m, "_EXEMPT_PAIRS", {"x/y": ("not_a_real_tier", "某理由")}
        ), mock.patch.object(m, "_SINGLE_SIDED_EXEMPT", {}), \
             mock.patch("builtins.print") as fake_print:
            ok = m._check_tier_classification()
        self.assertFalse(ok)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("not_a_real_tier", printed)

    def test_empty_reason_is_red(self) -> None:
        with mock.patch.object(m, "_EXEMPT_PAIRS", {"x/y": (m._UNPINNED, "   ")}), \
             mock.patch.object(m, "_SINGLE_SIDED_EXEMPT", {}), \
             mock.patch("builtins.print") as fake_print:
            ok = m._check_tier_classification()
        self.assertFalse(ok)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("reason 為空", printed)

    def test_tier3_without_hard_keyword_is_red(self) -> None:
        with mock.patch.object(
            m, "_EXEMPT_PAIRS", {"x/y": (m._TIER3_OS_PRIMITIVE, "泛泛豁免、無硬理由")}
        ), mock.patch.object(m, "_SINGLE_SIDED_EXEMPT", {}), \
             mock.patch("builtins.print") as fake_print:
            ok = m._check_tier_classification()
        self.assertFalse(ok)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("硬理由關鍵詞", printed)

    def test_tier4_without_hard_keyword_is_red(self) -> None:
        with mock.patch.object(
            m, "_SINGLE_SIDED_EXEMPT", {"x/y.ps1": (m._TIER4_FORBIDDEN, "泛泛理由")}
        ), mock.patch.object(m, "_EXEMPT_PAIRS", {}), \
             mock.patch("builtins.print") as fake_print:
            ok = m._check_tier_classification()
        self.assertFalse(ok)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("硬理由關鍵詞", printed)

    def test_tier4_with_hard_keyword_is_green(self) -> None:
        with mock.patch.object(
            m, "_EXEMPT_PAIRS", {"x/y": (m._TIER4_FORBIDDEN, "本身即為驗證載具")}
        ), mock.patch.object(m, "_SINGLE_SIDED_EXEMPT", {}), \
             mock.patch("builtins.print"):
            ok = m._check_tier_classification()
        self.assertTrue(ok)

    def test_unpinned_tier_does_not_require_hard_keyword(self) -> None:
        """unpinned／tier1_*／tier2_spec 不受硬理由關鍵詞斷言約束——只有 tier3/4
        （§3.3／§3.4 明文封頂類別）需要，見 (d) 的範圍（ADR §6 邊界 4）。

        R67-E24：unpinned 另受**退場錨點**約束（`TestR67UnpinnedExitObligation`），
        故本 fixture 補上錨點——本測試斷言的是「硬理由關鍵詞不適用於 unpinned」，
        不是「unpinned 完全無門檻」，語意不變。"""
        with mock.patch.object(
            m, "_EXEMPT_PAIRS",
            {"x/y": (m._UNPINNED, "泛泛理由，不含任何硬關鍵詞；退場：未指派")}
        ), mock.patch.object(m, "_SINGLE_SIDED_EXEMPT", {}), \
             mock.patch("builtins.print"):
            ok = m._check_tier_classification()
        self.assertTrue(ok)


class TestR63EquivalenceGroupsFreshness(unittest.TestCase):
    """R63（ADR-XPLAT-002 §5 Phase 1-C (a)）：4 組異名對等品字典化 + stale 自檢。

    Scan-H 紀律 #1：逐一構造三種 stale 情境（檔案消失／不再登記單邊豁免／stem 其實
    相同）並證明轉紅，另證明真 repo 現況本身是綠的。"""

    def test_real_groups_pass(self) -> None:
        with mock.patch("builtins.print"):
            self.assertTrue(m._check_equivalence_groups_fresh())

    def test_missing_file_on_disk_is_red(self) -> None:
        empty_root = _TMP_DIR / "equiv_missing_root"
        empty_root.mkdir(parents=True, exist_ok=True)
        with mock.patch("builtins.print") as fake_print:
            ok = m._check_equivalence_groups_fresh(repo_root=empty_root)
        self.assertFalse(ok)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("已不存在於磁碟", printed)

    def test_unregistered_member_is_red(self) -> None:
        fake_root = _TMP_DIR / "equiv_unregistered"
        (fake_root / "tools").mkdir(parents=True, exist_ok=True)
        (fake_root / "tools" / "a.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (fake_root / "tools" / "b.ps1").write_text("# x\n", encoding="utf-8")
        groups = {"synthetic": ("tools/a.sh", "tools/b.ps1")}
        with mock.patch.object(m, "_EQUIVALENCE_GROUPS", groups), \
             mock.patch.object(
                 m, "_SINGLE_SIDED_EXEMPT", {"tools/a.sh": (m._UNPINNED, "x")}
             ), mock.patch("builtins.print") as fake_print:
            ok = m._check_equivalence_groups_fresh(repo_root=fake_root)
        self.assertFalse(ok)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("tools/b.ps1", printed)
        self.assertIn("不在 _SINGLE_SIDED_EXEMPT", printed)

    def test_same_stem_is_red(self) -> None:
        fake_root = _TMP_DIR / "equiv_same_stem"
        (fake_root / "tools").mkdir(parents=True, exist_ok=True)
        (fake_root / "tools" / "same.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (fake_root / "tools" / "same.ps1").write_text("# x\n", encoding="utf-8")
        groups = {"synthetic": ("tools/same.sh", "tools/same.ps1")}
        exempt = {
            "tools/same.sh": (m._UNPINNED, "x"),
            "tools/same.ps1": (m._UNPINNED, "y"),
        }
        with mock.patch.object(m, "_EQUIVALENCE_GROUPS", groups), \
             mock.patch.object(m, "_SINGLE_SIDED_EXEMPT", exempt), \
             mock.patch("builtins.print") as fake_print:
            ok = m._check_equivalence_groups_fresh(repo_root=fake_root)
        self.assertFalse(ok)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("stem 相同", printed)


class TestR64TierShrinkOnlyRatchet(unittest.TestCase):
    """R64（ADR-XPLAT-002 §8 item 12）：`_EXEMPT_PAIRS`／`_SINGLE_SIDED_EXEMPT` 的
    tier 值只准往「更嚴格或不變」的方向改，對 HEAD 版本機械比對，形狀比照
    `tools/tests/test_adr_xplat001_c1c2_lock.py::TestShrinkOnlyRatchet`（ADR 指定的
    照抄對象）：(a) 正控（自比自為零違規）、(b) 合成注入兩個降級方向、(c) 對照組
    （升級/不變/整筆移出登記表皆合法）、(d) 字典改名不得靜默放行、(e) 真棘輪
    （對 HEAD 現查）。

    本類刻意加進本檔而非新開檔案：`TestGuardFileCountShrinkOnlyRatchet`
    （`test_adr_xplat001_c1c2_lock.py`）已把 `tools/tests/*.py` 的檔數棘輪化
    （DEF-101-561③，R61 起禁止新增鎖檔、只准合併）——新開一支 `test_*.py` 會讓
    那道鎖翻紅，故比照該裁決的既有慣例（`TestGuardFileCountShrinkOnlyRatchet`
    自己也是主題不同卻擴進既有檔的先例），把本鎖擴進本檔（`check_script_parity`
    既有測試檔）。
    """

    @staticmethod
    def _synth_source(tier_const_name: str, key: str = "x/y",
                       extra_single_sided: str = "") -> str:
        """組一份「合成上一版」原始碼：六個 tier 常數字面賦值 + 一筆 _EXEMPT_PAIRS
        登記（tier 用常數參照寫成，同本檔真實寫法），供降級/合法情境注入。"""
        return (
            '_TIER1_CONTRACT = "tier1_contract"\n'
            '_TIER1_ADAPTER = "tier1_adapter"\n'
            '_TIER2_SPEC = "tier2_spec"\n'
            '_TIER3_OS_PRIMITIVE = "tier3_os_primitive"\n'
            '_TIER4_FORBIDDEN = "tier4_forbidden"\n'
            '_UNPINNED = "unpinned"\n'
            '_EXEMPT_PAIRS: dict = {\n'
            f'    "{key}": ({tier_const_name}, "reason"),\n'
            '}\n'
            f'_SINGLE_SIDED_EXEMPT: dict = {{{extra_single_sided}}}\n'
        )

    def test_extraction_is_not_vacuous_on_the_current_source(self) -> None:
        """正控：抽取器對本檔現行原始碼必須抽得到兩張表的全部登記，且自比自為零違規。

        作用同 `TestShrinkOnlyRatchet.test_extraction_is_not_vacuous_on_the_current_source`：
        防「AST 抽取器被改壞（如漏認 AnnAssign 形態）⇒ 抽不到 ⇒ 棘輪永遠沉默」——
        R64 落地時本檔真的先踩到這個坑（`_EXEMPT_PAIRS: dict[...] = {...}` 是
        `ast.AnnAssign`，一開始的抽取器只認 `ast.Assign` 而靜默回 None）。
        """
        current_source = Path(m.__file__).read_text(encoding="utf-8")
        exempt = m._extract_tier_map_from_source(current_source, "_EXEMPT_PAIRS")
        single = m._extract_tier_map_from_source(current_source, "_SINGLE_SIDED_EXEMPT")
        self.assertIsNotNone(exempt, "抽取器對現行 _EXEMPT_PAIRS 回傳 None——抽取失效")
        self.assertIsNotNone(single, "抽取器對現行 _SINGLE_SIDED_EXEMPT 回傳 None——抽取失效")
        self.assertEqual(len(exempt), len(m._EXEMPT_PAIRS))
        self.assertEqual(len(single), len(m._SINGLE_SIDED_EXEMPT))
        self.assertEqual(m.tier_ratchet_problems(current_source), [])

    def test_downgrading_tier3_or_tier4_is_detected(self) -> None:
        """注入：上一版 tier3/4，現版降為其他 tier（含 unpinned）⇒ 必須被指名。"""
        for prev_tier, cur_tier in (
            ("_TIER3_OS_PRIMITIVE", m._UNPINNED),
            ("_TIER4_FORBIDDEN", m._TIER1_ADAPTER),
        ):
            with self.subTest(prev_tier=prev_tier, cur_tier=cur_tier):
                previous = self._synth_source(prev_tier)
                problems = m.tier_ratchet_problems(
                    previous,
                    current_exempt_pairs={"x/y": (cur_tier, "reason")},
                    current_single_sided={},
                )
                self.assertEqual(len(problems), 1, f"預期恰一處違規，實得：{problems}")
                self.assertIn("x/y", problems[0])
                self.assertIn("明文封頂類別", problems[0])

    def test_downgrading_tier1_or_tier2_to_unpinned_is_detected(self) -> None:
        """注入：上一版 tier1/tier2，現版打回 unpinned ⇒ 必須被指名。"""
        for prev_tier in ("_TIER1_CONTRACT", "_TIER1_ADAPTER", "_TIER2_SPEC"):
            with self.subTest(prev_tier=prev_tier):
                previous = self._synth_source(prev_tier)
                problems = m.tier_ratchet_problems(
                    previous,
                    current_exempt_pairs={"x/y": (m._UNPINNED, "reason")},
                    current_single_sided={},
                )
                self.assertEqual(len(problems), 1, f"預期恰一處違規，實得：{problems}")
                self.assertIn("x/y", problems[0])

    def test_upgrading_or_keeping_tier_is_accepted(self) -> None:
        """對照組：unpinned → tier3（升級）與 tier3 → tier3（不變）皆零違規。"""
        previous_unpinned = self._synth_source("_UNPINNED")
        problems = m.tier_ratchet_problems(
            previous_unpinned,
            current_exempt_pairs={"x/y": (m._TIER3_OS_PRIMITIVE, "reason")},
            current_single_sided={},
        )
        self.assertEqual(problems, [])

        previous_tier3 = self._synth_source("_TIER3_OS_PRIMITIVE")
        problems = m.tier_ratchet_problems(
            previous_tier3,
            current_exempt_pairs={"x/y": (m._TIER3_OS_PRIMITIVE, "reason")},
            current_single_sided={},
        )
        self.assertEqual(problems, [])

    def test_lateral_move_between_tier1_and_tier2_is_accepted(self) -> None:
        """對照組：tier1_contract／tier1_adapter／tier2_spec 彼此互換（同屬
        `_TIER1_2` 集合、非退回 unpinned）不算降級，應零違規——棘輪只鎖「退回
        unpinned」這個方向，同屬已歸類等級之間的橫向改分類合法，不應被誤判。"""
        lateral_pairs = (
            ("_TIER1_CONTRACT", m._TIER2_SPEC),
            ("_TIER2_SPEC", m._TIER1_CONTRACT),
            ("_TIER1_ADAPTER", m._TIER2_SPEC),
        )
        for prev_tier, cur_tier in lateral_pairs:
            with self.subTest(prev_tier=prev_tier, cur_tier=cur_tier):
                previous = self._synth_source(prev_tier)
                problems = m.tier_ratchet_problems(
                    previous,
                    current_exempt_pairs={"x/y": (cur_tier, "reason")},
                    current_single_sided={},
                )
                self.assertEqual(problems, [], f"預期零違規，實得：{problems}")

    def test_upgrading_unpinned_to_tier1_or_tier2_is_accepted(self) -> None:
        """對照組：上一版 unpinned，現版升級為 tier1_contract／tier2_spec（首次
        歸類）⇒ 零違規——現有測試只驗過 unpinned→tier3，這裡補齊往 tier1/2
        方向升級的組合，避免棘輪誤攔正常的初次歸類。"""
        for cur_tier in (m._TIER1_CONTRACT, m._TIER2_SPEC):
            with self.subTest(cur_tier=cur_tier):
                previous = self._synth_source("_UNPINNED")
                problems = m.tier_ratchet_problems(
                    previous,
                    current_exempt_pairs={"x/y": (cur_tier, "reason")},
                    current_single_sided={},
                )
                self.assertEqual(problems, [], f"預期零違規，實得：{problems}")

    def test_removing_the_key_entirely_is_accepted_as_convergence(self) -> None:
        """對照組：上一版 tier3/4，現版兩張表都不再登記該 key（整筆收斂移除）⇒ 零違規。

        這是 ADR §8 item 12 明文的合法出口：「除非該筆同時被移出登記表，代表已徹底
        收斂」——硬擋這種情況會懲罰真正把缺口收斂掉的人，方向與棘輪的目的相反。
        """
        previous = self._synth_source("_TIER4_FORBIDDEN")
        problems = m.tier_ratchet_problems(
            previous, current_exempt_pairs={}, current_single_sided={},
        )
        self.assertEqual(problems, [])

    def test_renaming_the_registry_dict_is_reported_not_silently_skipped(self) -> None:
        """改名／改寫 `_EXEMPT_PAIRS` 這個字典本身（而非其中某筆 key）不得讓棘輪
        靜默失效——抽不到字典就是紅，訊息須點名『改名／改寫』。"""
        previous = (
            '_TIER3_OS_PRIMITIVE = "tier3_os_primitive"\n'
            '_EXEMPT_PAIRS_RENAMED: dict = {\n'
            '    "x/y": (_TIER3_OS_PRIMITIVE, "reason"),\n'
            '}\n'
            '_SINGLE_SIDED_EXEMPT: dict = {}\n'
        )
        problems = m.tier_ratchet_problems(
            previous,
            current_exempt_pairs={"x/y": (m._UNPINNED, "reason")},
            current_single_sided={},
        )
        self.assertEqual(len(problems), 1, f"預期恰一處違規，實得：{problems}")
        self.assertIn("_EXEMPT_PAIRS", problems[0])
        self.assertIn("改名／改寫", problems[0])

    def test_production_check_wired_into_main(self) -> None:
        """`_check_tier_ratchet()` 已隨 `main()` 執行（無參數呼叫路徑），非孤兒函式。"""
        with mock.patch.object(sys, "argv", ["check_script_parity.py"]), \
             mock.patch("builtins.print"):
            rc = m.main()
        self.assertEqual(rc, 0, "真 repo 現況應為零降級，main() 應 rc=0")


class TestR67BaselineRatchet(unittest.TestCase):
    """R67-H14 回歸鎖：棘輪的比對基準必須是**凍結常數**，不得是 git 導出的量。

    WHY（Rule 9：測意圖不只測行為）——R64 的棘輪拿 `git show HEAD:<本檔>` 當基準，
    形式上完全正確，實質上在**每一個真正消費它 rc 的閘門**裡都是恆真的：pre-push 與
    三支 CI workflow 都跑在 commit 之後（CI 更是乾淨 checkout），HEAD 逐字等於工作樹
    ⇒ 基準與被檢查值在被比較前就已相等，比較退化。實測（R67 掃描，沙箱）：把
    `run_local_nightly` 由 tier4 降為 unpinned 並 commit ⇒ `check_script_parity.py`
    rc=0、真 pre-push hook 端到端 rc=0、`tools/tests` 與控制組逐字相同。

    根因不是「判準寫得不夠嚴」，而是「基準會自己對齊」。故本類鎖的是**那個結構性質**
    本身（下面第一支測試：禁用 subprocess 仍須完整運作），而不只是鎖某幾筆 tier 值——
    只鎖值的話，任何人把基準改回 git 導出量都不會有訊號。
    """

    def test_ratchet_is_independent_of_git_state(self) -> None:
        """🔴 核心結構鎖：棘輪全程不得呼叫外部行程（git）。

        舊實作在此鎖下必紅（它呼叫 `git show HEAD:…`）。這一條同時封死兩件事：
        (1) 基準自我對齊的恆真陷阱；(2)「git 取不到基準 ⇒ 綠燈空轉」的 fail-open。
        """
        def _boom(*_a, **_kw):  # pragma: no cover - 只為證明沒被呼叫
            raise AssertionError(
                "棘輪呼叫了外部行程——基準又變回 git 導出量了（R67-H14 回歸）"
            )

        with mock.patch("subprocess.run", _boom), \
             mock.patch("subprocess.check_output", _boom), \
             mock.patch("subprocess.Popen", _boom):
            self.assertEqual(m.baseline_ratchet_problems(), [])
            with mock.patch("builtins.print"):
                self.assertTrue(m._check_tier_ratchet())

    def test_real_tables_match_frozen_baseline(self) -> None:
        """正控：真 repo 現況對凍結基準零違規（否則本輪就該同步基準或修 tier）。"""
        self.assertEqual(m.baseline_ratchet_problems(), [])

    def test_downgrade_versus_baseline_is_red_without_any_commit(self) -> None:
        """缺陷注入（本鎖存在的理由）：只改活體 tier、基準不動 ⇒ 必紅。

        這正是舊實作 commit 之後會放行的情境——現在與 git 狀態無關，恆紅。
        """
        tampered = dict(m._EXEMPT_PAIRS)
        tampered["AutoClaude/tools/run_local_nightly"] = (
            m._UNPINNED, "注入：把明文封頂的 tier4 悄悄鬆綁；退場：未指派"
        )
        problems = m.baseline_ratchet_problems(current_exempt_pairs=tampered)
        self.assertTrue(
            any("run_local_nightly" in p and "明文封頂類別" in p for p in problems),
            f"tier4→unpinned 降級未被偵測，實得：{problems}",
        )

    def test_live_entry_missing_from_baseline_is_red(self) -> None:
        """涵蓋規則：活體登記表有、基準沒有 ⇒ 紅。

        雙重用途：(a) 新增豁免必須顯式進基準（在 diff 上現形）；(b) 擋「刪掉基準那一
        筆來迴避棘輪」——key 還活著而基準沒有它就是紅，刪不掉。
        """
        tampered = dict(m._SINGLE_SIDED_EXEMPT)
        tampered["tools/ghost_new_exemption.sh"] = (m._UNPINNED, "注入；退場：未指派")
        problems = m.baseline_ratchet_problems(current_single_sided=tampered)
        self.assertTrue(
            any("ghost_new_exemption" in p and "_TIER_BASELINE" in p for p in problems),
            f"未涵蓋於基準的新登記未被偵測，實得：{problems}",
        )

    def test_deleting_a_baseline_entry_does_not_dodge_the_ratchet(self) -> None:
        """迴避路徑封堵：把某筆自基準刪掉（想讓降級無從比對）⇒ 仍紅（走涵蓋規則）。"""
        shrunk = {
            k: v for k, v in m._TIER_BASELINE.items()
            if k != "AutoClaude/tools/run_local_nightly"
        }
        tampered = dict(m._EXEMPT_PAIRS)
        tampered["AutoClaude/tools/run_local_nightly"] = (
            m._UNPINNED, "注入；退場：未指派"
        )
        problems = m.baseline_ratchet_problems(
            current_exempt_pairs=tampered, baseline=shrunk,
        )
        self.assertTrue(
            any("run_local_nightly" in p for p in problems),
            f"刪基準條目後降級被放行＝迴避成功，實得：{problems}",
        )

    def test_converged_entry_removed_from_live_tables_stays_green(self) -> None:
        """對照組：整筆自活體表移除（＝真的收斂掉）⇒ 零違規，基準保留該筆不誤紅。

        棘輪的目的是擋退步，不是懲罰把缺口收掉的人（ADR §8 item 12 明文出口）。
        """
        shrunk_pairs = {
            k: v for k, v in m._EXEMPT_PAIRS.items()
            if k != "AutoClaude/tools/run_local_nightly"
        }
        self.assertEqual(
            m.baseline_ratchet_problems(current_exempt_pairs=shrunk_pairs), []
        )

    def test_baseline_covers_every_live_entry_and_agrees_on_tier(self) -> None:
        """基準新鮮度：真 repo 兩張活體表的每一筆都在基準內，且 tier 逐字一致。

        （降級規則只鎖兩個方向，橫向/升級改動不會紅——若同時忘了同步基準，基準就會
        慢慢變成一份沒人維護的化石。本鎖要求基準與活體逐字對齊，強制同步。）
        """
        live = m._live_tier_map(None, None)
        missing = sorted(k for k in live if k not in m._TIER_BASELINE)
        self.assertEqual(missing, [], f"活體登記項未進基準：{missing}")
        mismatched = sorted(
            f"{k}: 活體={live[k]} / 基準={m._TIER_BASELINE[k]}"
            for k in live if m._TIER_BASELINE[k] != live[k]
        )
        self.assertEqual(
            mismatched, [],
            "活體 tier 與凍結基準不一致——升級/橫向改動請同步 _TIER_BASELINE；"
            f"降級請走 ADR 具名理由：{mismatched}",
        )

    def test_unpinned_ceiling_is_not_derived_from_the_baseline(self) -> None:
        """R67-E24：天花板必須是獨立常數，不得由基準自動導出。

        若寫成 `sum(1 for t in _TIER_BASELINE.values() if t == _UNPINNED)`，新增一筆
        unpinned（連同基準）會讓天花板自己長高＝又一個自我對齊的恆真陷阱。本鎖以
        「基準多一筆 unpinned 時天花板不變」直接證明它沒有這種耦合。
        """
        inflated = dict(m._TIER_BASELINE)
        inflated["tools/ghost_unpinned.sh"] = m._UNPINNED
        tampered_live = dict(m._SINGLE_SIDED_EXEMPT)
        tampered_live["tools/ghost_unpinned.sh"] = (m._UNPINNED, "注入；退場：未指派")
        problems = m.baseline_ratchet_problems(
            current_single_sided=tampered_live, baseline=inflated,
        )
        self.assertTrue(
            any("超過天花板" in p for p in problems),
            f"unpinned 天花板隨基準一起長高＝棘輪無張力，實得：{problems}",
        )

    def test_unpinned_shrink_is_green(self) -> None:
        """對照組：收斂掉一筆 unpinned（總量下降）⇒ 天花板規則不誤紅。"""
        shrunk = {
            k: v for k, v in m._SINGLE_SIDED_EXEMPT.items()
            if k != "AISDLC_SDD/scripts/act-ci.sh"
        }
        problems = m.baseline_ratchet_problems(current_single_sided=shrunk)
        self.assertEqual([p for p in problems if "天花板" in p], [])

    # ── R67 round 2（ARCH-R67-03）：tier3/4 課責地板 ───────────────────────────
    # WHY 這一組必須存在：上面的降級規則 (A)(B) 是**逐 key** 比對基準，而
    # `test_baseline_covers_every_live_entry_and_agrees_on_tier` 又要求活體與基準逐字
    # 相等 ⇒「兩處一起改」是合法異動的常規工作流，降級因此可以偽裝成常規成對編輯。
    # Architect 沙箱實測（INJ-1c）：把 `LATEST/tools/init_project` 在活體與基準兩處同步
    # 由 tier3_os_primitive 改為 tier1_contract ⇒ `check_script_parity.py` rc=0、本檔
    # 全綠——明文封頂（ADR §3.3「禁止未來輪重辯」）的項目被降級且零訊號，還順帶卸掉
    # `_HARD_REASON_KEYWORDS` 對 tier3/4 的硬理由義務（reason 散文原封不動仍寫著
    # launchd/schtasks 字樣）。地板走總量維度，對成對編輯免疫。

    def test_paired_edit_downgrade_of_a_capped_entry_is_caught_by_the_floor(self) -> None:
        """🔴 缺陷注入（本地板存在的理由）：INJ-1c 逐字重現 ⇒ 必紅。

        同時改活體與基準（＝逐 key 規則完全看不見的那條路），地板仍須轉紅。
        """
        key = "LATEST/tools/init_project"
        self.assertEqual(
            m._TIER_BASELINE[key], m._TIER3_OS_PRIMITIVE,
            "注入前提已變（該筆不再是 tier3）——請改挑另一筆明文封頂項重寫本注入",
        )
        tampered_live = dict(m._EXEMPT_PAIRS)
        tampered_live[key] = (m._TIER1_CONTRACT, m._EXEMPT_PAIRS[key][1])
        tampered_baseline = dict(m._TIER_BASELINE)
        tampered_baseline[key] = m._TIER1_CONTRACT
        problems = m.baseline_ratchet_problems(
            current_exempt_pairs=tampered_live, baseline=tampered_baseline,
        )
        self.assertTrue(
            any("課責數" in p and "地板" in p for p in problems),
            f"成對編輯降級明文封頂項未被地板攔下＝棘輪對常規工作流無張力，實得：{problems}",
        )

    def test_tier34_floor_is_not_derived_from_the_baseline(self) -> None:
        """R67 round 2：地板必須是**簽入的字面常數**，不得由基準／活體表算出來。

        比照 `test_unpinned_ceiling_is_not_derived_from_the_baseline` 的意圖：若寫成
        `sum(1 for t in _TIER_BASELINE.values() if t in _TIER3_4)`，上面那支注入就會
        自我對齊（基準降一筆、地板跟著降一筆）⇒ 又一個 R67-H14 形狀的恆真陷阱。
        以 AST 直接斷言賦值右側是 int 字面，而不是任何運算式。
        """
        import ast

        tree = ast.parse(Path(m.__file__).read_text(encoding="utf-8"))
        assigned = [
            node.value for node in tree.body
            if isinstance(node, ast.Assign) and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "_TIER34_FLOOR"
        ]
        self.assertEqual(len(assigned), 1, "_TIER34_FLOOR 必須恰有一處模組層賦值")
        self.assertIsInstance(
            assigned[0], ast.Constant,
            "_TIER34_FLOOR 被寫成運算式——若它由 _TIER_BASELINE／活體表導出，"
            "成對編輯會讓地板自己跟著降＝棘輪無張力（R67-H14 恆真陷阱形狀）",
        )
        self.assertIsInstance(assigned[0].value, int)

    def test_converged_removal_of_a_capped_entry_does_not_trip_the_floor(self) -> None:
        """對照組（雙向）：整筆移出活體表＝ADR §8 item 12 明文出口 ⇒ 地板不誤紅。

        測意圖：地板要擋的是「留在表內但被改成別的 tier」，不是懲罰真的把缺口收掉的人。
        課責數把「基準記為 tier3/4 而已移出活體表」的 key 一併計入，兩種情形才分得開；
        若這裡誤紅，下一個人收斂完會被逼著下修地板，等於獎勵「留著不收」。
        """
        shrunk_pairs = {
            k: v for k, v in m._EXEMPT_PAIRS.items()
            if k != "AutoClaude/tools/run_local_nightly"
        }
        problems = m.baseline_ratchet_problems(current_exempt_pairs=shrunk_pairs)
        self.assertEqual([p for p in problems if "課責數" in p], [])

    def test_deleting_the_baselines_memory_of_a_capped_entry_is_red(self) -> None:
        """迴避路徑封堵：連基準那一筆 tier3/4 記憶也刪掉 ⇒ 課責數下降 ⇒ 紅。

        這是唯一能讓課責數合法下降的動作，而基準的維護規則寫著「已收斂的 key 刻意保留
        （永久記憶）」——所以它本來就不該發生，發生就要在 diff 上現形。
        """
        key = "AutoClaude/tools/run_local_nightly"
        shrunk_pairs = {k: v for k, v in m._EXEMPT_PAIRS.items() if k != key}
        forgetful = {k: v for k, v in m._TIER_BASELINE.items() if k != key}
        problems = m.baseline_ratchet_problems(
            current_exempt_pairs=shrunk_pairs, baseline=forgetful,
        )
        self.assertTrue(
            any("課責數" in p for p in problems),
            f"刪掉基準的 tier3/4 記憶後地板放行＝永久記憶可被抹除，實得：{problems}",
        )


class TestR67UnpinnedExitObligation(unittest.TestCase):
    """R67-E24 回歸鎖：`unpinned` 的 reason 必須帶退場錨點。

    WHY：`unpinned`＝「不符 Tier-1~4 任一定義」，佔比 8/23＝34.8%。R67 前它唯一的門檻
    是「reason 非空」——實測 `reason="x"` 照樣綠——於是它成為 Tier 模型之外一個不需要
    任何理由品質、也沒有退場義務的永久豁免桶。本鎖要求每筆明說誰來接
    （`退場：未指派` 或 `退場：R<輪號>…`），把「沒人接」由散文語感升級為可 grep 的欄位。

    邊界（誠實）：不驗證輪號是否仍在未來——那要耦合帳本當前輪號，`CrossPlatform_Scan_
    Dimensions.md` §191 已明文警告會造成永紅。數量面的退步由 `_UNPINNED_CEILING` 擋。
    """

    def test_real_tables_all_unpinned_carry_exit_anchor(self) -> None:
        missing = sorted(
            key for table in (m._EXEMPT_PAIRS, m._SINGLE_SIDED_EXEMPT)
            for key, (tier, reason) in table.items()
            if tier == m._UNPINNED and not m._UNPINNED_EXIT_RE.search(reason)
        )
        self.assertEqual(missing, [], f"unpinned 缺退場錨點：{missing}")

    def test_placeholder_reason_is_red(self) -> None:
        """缺陷注入：R67 前 `reason="x"` 實測為綠（門檻只有『非空』）；現在必紅。"""
        with mock.patch.object(m, "_EXEMPT_PAIRS", {"x/y": (m._UNPINNED, "x")}), \
             mock.patch.object(m, "_SINGLE_SIDED_EXEMPT", {}), \
             mock.patch("builtins.print") as fake_print:
            ok = m._check_tier_classification()
        self.assertFalse(ok)
        printed = " ".join(
            str(a) for call in fake_print.call_args_list for a in call.args
        )
        self.assertIn("退場錨點", printed)

    def test_reason_with_exit_anchor_is_green(self) -> None:
        """對照組（雙向）：帶錨點即通過——證明紅燈來自缺錨點，不是 fixture 本身壞掉。"""
        for anchor in ("退場：未指派", "退場：R99（某具名解鎖條件）"):
            with self.subTest(anchor=anchor):
                with mock.patch.object(
                    m, "_EXEMPT_PAIRS", {"x/y": (m._UNPINNED, f"某理由；{anchor}")}
                ), mock.patch.object(m, "_SINGLE_SIDED_EXEMPT", {}), \
                     mock.patch("builtins.print"):
                    self.assertTrue(m._check_tier_classification())

    # ── R67 round 2（SD-R67-03／ARCH-R67-01 交叉發現）：開放下界形態 ──────────
    # R67 round 1 的正則寫 `R\d+`，對 `退場：R68+` 是**放行**的（search 匹到 `R68` 前綴
    # 即成立）。而同輪 DOCRULE 包才剛依 ADR-XPLAT-002 §8 表頭規則 1 把 `R<N>+` 定為病灶
    # 並禁用（開放下界永不到期；item 7／8 六輪零異動即實例），本包同輪卻在
    # `_EXEMPT_PAIRS['AISDLC_SDD/scripts/ci-gate']` 寫下 `退場：R68+` —— 新機制一出生就
    # 把當輪判定為不可接受的寫法制度化。下面兩支把「規則只存在於散文裡」變成機械擋。

    def test_open_ended_round_form_is_rejected(self) -> None:
        """🔴 缺陷注入：`退場：R68+`（含全形加號）必紅——這是 §8 表頭規則 1 的病灶形態。"""
        for anchor in ("退場：R68+（三條解除判準）", "退場：R68＋（三條解除判準）"):
            with self.subTest(anchor=anchor):
                with mock.patch.object(
                    m, "_EXEMPT_PAIRS", {"x/y": (m._UNPINNED, f"某理由；{anchor}")}
                ), mock.patch.object(m, "_SINGLE_SIDED_EXEMPT", {}), \
                     mock.patch("builtins.print") as fake_print:
                    ok = m._check_tier_classification()
                self.assertFalse(
                    ok,
                    f"{anchor!r} 被放行——`R<N>+` 是開放下界，永遠有一個「之後」可以指，"
                    "與『未指派』等價卻讀起來像有承接對象（ADR §8 表頭規則 1）",
                )
                printed = " ".join(
                    str(a) for call in fake_print.call_args_list for a in call.args
                )
                self.assertIn("退場錨點", printed)

    def test_real_tables_carry_no_open_ended_exit_anchor(self) -> None:
        """真表現況：兩張活體登記表不得留下任何 `退場：R<N>+` 形態。

        與上一支互補：上一支證明判準會紅，這一支證明**現況已經沒有**這種寫法
        （R67 round 1 落地時 `ci-gate` 那筆就是 `退場：R68+`，靠人眼交叉比對才發現）。
        """
        import re

        open_ended = re.compile(r"退場：R\d+[+＋]")
        offenders = sorted(
            key for table in (m._EXEMPT_PAIRS, m._SINGLE_SIDED_EXEMPT)
            for key, (_tier, reason) in table.items()
            if open_ended.search(reason)
        )
        self.assertEqual(
            offenders, [],
            "reason 內出現開放下界承接（`退場：R<N>+`）——只准具名輪次或未指派："
            f"{offenders}",
        )

    def test_non_unpinned_tiers_are_not_required_to_carry_the_anchor(self) -> None:
        """邊界：退場義務只加在 unpinned；tier3/4 是明文封頂類別，本來就不該退場。"""
        with mock.patch.object(
            m, "_EXEMPT_PAIRS", {"x/y": (m._TIER4_FORBIDDEN, "本身即為驗證載具")}
        ), mock.patch.object(m, "_SINGLE_SIDED_EXEMPT", {}), \
             mock.patch("builtins.print"):
            self.assertTrue(m._check_tier_classification())


class TestR67AcCoverage(unittest.TestCase):
    """R67-H34 回歸鎖：AC 的涵蓋面不得再被「新增一張登記表」整張逃逸。

    WHY：AC（§4.2 反位移判準）是「描述性常數登記項的誠實全集」，用途是擋「換個地方
    複雜」。R67 前這個全集只存在於 `_print_collapse()` 一條寫死的七項加總算式裡，而
    號稱「獨立重算」的 `test_ac_matches_sum_of_seven_registries` 逐字複製同一條算式
    ⇒ 對「多了一張沒被算進去的表」天生零訊號（實測：注入第 8 張表 3 筆，AC 不動、
    全套 tools/tests 零紅）。

    本鎖改用**真正不同的實作路徑**：以 `ast` 掃描兩支工具原始碼的模組層登記表，
    比對「掃到的全集 == AC 納入 ∪ 具名排除」。新增任何一張表若兩邊都沒登記即紅。
    """

    _MIN_DISCOVERED = 9  # 2026-08-01 實測 13 張；下限防「掃描器被改壞 ⇒ 掃到 0 ⇒ 恆綠」

    @staticmethod
    def _discover(path: Path) -> set[str]:
        """AST 掃出模組層「值為非空 dict/set 字面」的私有登記表名稱。"""
        import ast

        tree = ast.parse(path.read_text(encoding="utf-8"))
        found: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                    and isinstance(node.targets[0], ast.Name):
                name, value = node.targets[0].id, node.value
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                    and node.value is not None:
                name, value = node.target.id, node.value
            else:
                continue
            if not name.startswith("_"):
                continue
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) \
                    and value.func.id == "frozenset" and value.args:
                value = value.args[0]
            if isinstance(value, ast.Dict) and value.keys:
                found.add(name)
            elif isinstance(value, ast.Set) and value.elts:
                found.add(name)
        return found

    def _discovered_pairs(self) -> set[tuple[str, str]]:
        import check_wrapper_thinness as _thinness

        pairs = {("parity", n) for n in self._discover(Path(m.__file__))}
        pairs |= {("thinness", n) for n in self._discover(Path(_thinness.__file__))}
        return pairs

    def test_scanner_is_not_vacuous(self) -> None:
        """正控：掃描器對現行原始碼必須掃得到足量登記表——掃到 0 就會恆綠。"""
        pairs = self._discovered_pairs()
        self.assertGreaterEqual(
            len(pairs), self._MIN_DISCOVERED,
            f"AST 掃描僅得 {len(pairs)} 張登記表 < 下限 {self._MIN_DISCOVERED}"
            f"——掃描器疑似被改壞（靜默縮面）；刻意精簡請同步下修下限",
        )
        self.assertIn(("parity", "_EXEMPT_PAIRS"), pairs)
        self.assertIn(("thinness", "_PINNED_SHA256"), pairs)

    def test_every_registry_is_either_counted_or_named_excluded(self) -> None:
        """🔴 核心：掃到的每一張表，非納入 AC 即具名排除；漏一張即紅。"""
        declared = set(m._AC_REGISTRY_NAMES) | set(m._AC_EXCLUDED_REGISTRIES)
        undeclared = sorted(self._discovered_pairs() - declared)
        self.assertEqual(
            undeclared, [],
            "下列模組層登記表既未計入 AC、也未具名排除——§4.2 的『誠實全集』出現缺口："
            f"{undeclared}；請納入 _AC_REGISTRY_NAMES 或加進 _AC_EXCLUDED_REGISTRIES "
            "並寫下理由",
        )

    def test_declared_names_all_exist(self) -> None:
        """反向 stale：宣告（納入/排除）的名字若已不存在於原始碼 ⇒ 紅，防清單腐化。"""
        discovered = self._discovered_pairs()
        stale = sorted(
            (set(m._AC_REGISTRY_NAMES) | set(m._AC_EXCLUDED_REGISTRIES)) - discovered
        )
        self.assertEqual(stale, [], f"AC 宣告清單指向已不存在的登記表：{stale}")

    def test_ghost_registry_is_detected(self) -> None:
        """缺陷注入：模擬「新增第 8 張登記表卻沒登記」——R67 前此情境全綠。"""
        real = self._discovered_pairs()
        with mock.patch.object(
            TestR67AcCoverage, "_discovered_pairs",
            lambda _self: real | {("parity", "_GHOST_REGISTRY")},
        ):
            with self.assertRaises(AssertionError) as ctx:
                self.test_every_registry_is_either_counted_or_named_excluded()
        self.assertIn("_GHOST_REGISTRY", str(ctx.exception))

    def test_ac_value_is_pinned(self) -> None:
        """AC 活體值釘選（比照 UEP 的 `test_uep_is_five_after_r65_migration`）。

        §4.2 判定規則 2：AC 每一筆上升必須在同一 commit 內具名對應一筆 UEP 下降。
        R67 前 AC 完全無值鎖（實測 AC 48→49 全綠）；現在上升即紅、下降亦紅（提醒
        同步下修以維持張力）。R67 現值 48 = 14+7+5+18+2+1+1。
        """
        ac = sum(len(reg) for reg in m.ac_registries().values())
        self.assertEqual(
            ac, 48,
            f"AC 由 48 變為 {ac} —— 上升請依 ADR-XPLAT-002 §4.2 規則 2 具名對應一筆 "
            f"UEP 下降後同步本釘選值；下降請一併下修本值",
        )

    def test_ac_registries_is_the_only_source_for_print_collapse(self) -> None:
        """`--print-collapse` 的 AC 必須來自 `ac_registries()`（不得另有第二條算式）。"""
        import io
        from contextlib import redirect_stdout

        expected = sum(len(reg) for reg in m.ac_registries().values())
        buf = io.StringIO()
        with redirect_stdout(buf):
            m.main(["--print-collapse"])
        self.assertIn(f"AC={expected}", buf.getvalue())


class TestR67LatestPinnedShebangCoverage(unittest.TestCase):
    """R67-H35 回歸鎖（LATEST 側）：`_LATEST_PINNED_SHA256` 的 `.sh` 也須把 shebang
    納入 hash 輸入。

    WHY：`_check_latest_thinness()` 重用 `check_wrapper_thinness` 的同一組純函式，
    LATEST run_tlc.sh 同樣是 `#!/usr/bin/env bash`。`tools/tests/
    test_check_wrapper_thinness.py` 那支全面性測試只走 `_PINNED_SHA256`，LATEST 這
    一支不在它的迴圈裡——不補這條就會出現「主表修好、LATEST 仍在覆蓋面外」。
    """

    def test_latest_pinned_sh_shebang_enters_hash(self) -> None:
        import check_wrapper_thinness as _thinness

        latest_tools = m._resolve_latest_tools()
        self.assertIsNotNone(latest_tools, "真 repo 內 LATEST 解析不得失敗")
        checked = 0
        for rel in m._LATEST_PINNED_SHA256:
            path = latest_tools / rel[len(m._LATEST_PREFIX):]
            if path.suffix != ".sh":
                continue
            self.assertTrue(path.is_file(), f"{rel} 不存在於磁碟")
            first = _thinness._read_source(path).splitlines()[0]
            self.assertTrue(first.startswith("#!"), f"{rel} 首行非 shebang：{first!r}")
            self.assertEqual(
                _thinness.normalized_content(path).splitlines()[0], first,
                f"{rel} 的 shebang 未進入 hash 輸入（R67-H35 回歸）",
            )
            checked += 1
        self.assertGreaterEqual(checked, 1, "LATEST 釘選面內無 .sh，本鎖已空轉")


if __name__ == "__main__":
    unittest.main()
