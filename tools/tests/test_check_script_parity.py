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
    def test_below_floor_is_red(self) -> None:
        """R9 回歸鎖：任一側抽取數量低於 _MIN_EXTRACT_COUNTS 釘選即紅燈——
        即使雙邊清單完全一致（同步改壞宣告 pattern 的典型形狀）。"""
        floor = m._MIN_EXTRACT_COUNTS["run_act"]
        short = [f"step {i}" for i in range(floor - 1)]
        with mock.patch("builtins.print"):
            self.assertFalse(m._check_extract_floor("run_act", short, short))

    def test_at_floor_passes(self) -> None:
        floor = m._MIN_EXTRACT_COUNTS["run_act"]
        items = [f"step {i}" for i in range(floor)]
        with mock.patch("builtins.print"):
            self.assertTrue(m._check_extract_floor("run_act", items, items))

    def test_red_message_points_to_pin_update(self) -> None:
        """紅燈訊息必須指路：刻意刪減 step 時要同步更新釘選值（訊息說清楚）。"""
        with mock.patch("builtins.print") as fake_print:
            m._check_extract_floor("bootstrap", ["a"], ["a"])
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("_MIN_EXTRACT_COUNTS", printed)
        self.assertIn("bootstrap", printed)


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
            mock.patch.object(m, "_TLC_TRACK_ENROLLED", set()),
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
             mock.patch.object(m, "_TLC_TRACK_ENROLLED", set()), \
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


class TestRunTlcTrackLock(unittest.TestCase):
    """R12 ARCH-R12-3：run_tlc FSM 軌錨點集合鎖紅/綠自證（fixture 注入變異）。

    WHY：DEF-101-100——run_tlc.ps1 曾缺整條 FLEET_FSM 軌而 .sh 有，零機械訊號。
    軌 token（*_FSM*.tla/.cfg）集合比對恰好攔此型漂移。
    """

    _SH_FULL = (
        "#!/usr/bin/env bash\n"
        "# 註解裡的 GHOST_FSM.tla 不得入抽取\n"
        "java -cp x tlc2.TLC -config SDD_FSM.cfg SDD_FSM.tla\n"
        "java -cp x tlc2.TLC -config FLEET_FSM.cfg FLEET_FSM.tla\n"
        "java -cp x tlc2.TLC -config FLEET_FSM_LIVENESS.cfg FLEET_FSM.tla\n"
    )

    def _make_pair(self, name: str, sh_body: str, ps1_body: str) -> Path:
        latest_tools = _TMP_DIR / name / "tools"
        formal = latest_tools / "fsm_runtime" / "formal"
        formal.mkdir(parents=True, exist_ok=True)
        (formal / "run_tlc.sh").write_text(sh_body, encoding="utf-8")
        (formal / "run_tlc.ps1").write_text(ps1_body, encoding="utf-8")
        return latest_tools

    def test_matching_tracks_green(self) -> None:
        ps1 = self._SH_FULL.replace("java -cp", "& java -cp")  # 形態不同、token 相同
        latest_tools = self._make_pair("tlc_green", self._SH_FULL, ps1)
        with mock.patch("builtins.print"):
            self.assertTrue(m._check_run_tlc_tracks(latest_tools))

    def test_missing_fleet_track_on_ps1_is_red(self) -> None:
        """變異自證：.ps1 刪整條 FLEET 軌（DEF-101-100 原型）→ 必紅。"""
        ps1_lines = [ln for ln in self._SH_FULL.splitlines() if "FLEET" not in ln]
        latest_tools = self._make_pair(
            "tlc_red", self._SH_FULL, "\n".join(ps1_lines) + "\n")
        with mock.patch("builtins.print") as fake_print:
            ok = m._check_run_tlc_tracks(latest_tools)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertFalse(ok)
        self.assertIn("FLEET_FSM", printed)

    def test_comment_only_tracks_not_extracted(self) -> None:
        """註解行的軌字樣不入抽取（GHOST_FSM.tla 只出現在 # 註解）。"""
        latest_tools = self._make_pair("tlc_comment", self._SH_FULL, self._SH_FULL)
        tracks = m._extract_tlc_tracks(
            latest_tools / "fsm_runtime" / "formal" / "run_tlc.sh")
        self.assertNotIn("GHOST_FSM.tla", tracks)
        # multiset 語意（SD-2）：FLEET_FSM.tla 兩處引用各自入列 → 6 個 token
        self.assertEqual(len(tracks), 6, f"軌 multiset 應恰為 6，實得 {tracks}")

    def test_floor_pins_five_tracks(self) -> None:
        """釘選：兩側同步刪到 4 軌（floor=5 以下）也必紅——防同步改寫假綠。"""
        four = "\n".join(
            ln for ln in self._SH_FULL.splitlines() if "LIVENESS" not in ln) + "\n"
        latest_tools = self._make_pair("tlc_floor", four, four)
        with mock.patch("builtins.print"):
            self.assertFalse(m._check_run_tlc_tracks(latest_tools))

    def test_renamed_track_same_count_is_red_via_compare(self) -> None:
        """兩側皆 ≥floor 但集合不同（單側改名）必紅——_compare 專屬路徑回歸鎖。

        WHY（R12 QA 二審 EXP4 轉正）：其餘紅案例的 token 數同時低於 floor，
        floor 與 _compare 雙訊號並發；_compare 被突變恆 True 時它們仍紅、
        改名型漂移卻會漏。本案例兩側各 6 token（等量）僅名字不同——只有
        _compare 能攔，補上 meta 級防護。"""
        renamed = self._SH_FULL.replace("SDD_FSM", "SDX_FSM")
        latest_tools = self._make_pair("tlc_rename", self._SH_FULL, renamed)
        with mock.patch("builtins.print") as fake_print:
            self.assertFalse(m._check_run_tlc_tracks(latest_tools))
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("SDX_FSM", printed, "diff 須點名改名後的 token")

    def test_missing_script_is_red(self) -> None:
        """run_tlc 檔案消失 → 紅（指路更新 _TLC_TRACK_ENROLLED）。"""
        empty = _TMP_DIR / "tlc_missing" / "tools"
        empty.mkdir(parents=True, exist_ok=True)
        with mock.patch("builtins.print"):
            self.assertFalse(m._check_run_tlc_tracks(empty))

    def test_real_tree_run_tlc_green(self) -> None:
        """真磁碟整合：LATEST run_tlc 兩側軌集合一致（DEF-101-100 已修狀態）。"""
        latest_tools = m._resolve_latest_tools()
        self.assertIsNotNone(latest_tools)
        with mock.patch("builtins.print"):
            self.assertTrue(m._check_run_tlc_tracks(latest_tools))


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


if __name__ == "__main__":
    unittest.main()
