#!/usr/bin/env python3
"""共用淨化層架構鎖（R45 架構最佳化，DEF-101-358 收斂驗證）。

背景：R45 把 `_sanitize_component()` 從「30 個版本目錄各自一份複本」改為「全部
委派 `AISDLC_SDD/scripts/component_sanitizer.py` 這一個共用 SSOT」，一次性解決
DEF-101-358（29 版凍結基線曾留著只擋路徑分隔符的弱化版，缺 LATEST 已有的
Windows 保留裝置名／控制字元／長度上限強化）。本檔鎖住這個架構決策的兩個
不變量，避免日後又不小心退化回「30 份各自維護」的舊架構：

  1. 共用模組本身持續存在，且行為持續擋下已知危險輸入類別。
  2. 每個版本（29 凍結 + LATEST）的 `state_loader.py` 持續透過共用模組取得
     `_sanitize_component`，而非任何一版又長出自己的獨立複本（不論弱化版或
     另一份強化版——只要不是委派同一份共用原始碼（同一支 `component_sanitizer.py`
     檔案；因刻意不寫入 `sys.modules` 以避免跨版本快取汙染，每版各自
     `exec_module()` 一次，故精確而言是 30 個各自獨立的函式物件執行同一份
     程式碼，非跨版本共用同一顆記憶體物件），代表 SSOT 已經分裂，
     DEF-101-358 修好的「改一處、全版本立即生效」保證就會失真）。

方法論：對每個版本目錄用 subprocess 起乾淨行程匯入該版 `state_loader`，實測
`_sanitize_component()` 對已知危險輸入的行為（行為驗證比文字比對更難規避；子行程天生行程隔離，不必
人工清 `sys.modules` 快取，用執行時間換正確性）。方法論推導與 subprocess 取捨全文搬至
Guard_Line_History_2.md〈R186 淨減法搬遷〉§9。  round-label-ok

方法論邊界（誠實記載，同既有鎖 docstring 先例）：本檔只驗證「委派目標是否為
預期的共用模組檔案 + 已知危險輸入是否被擋下」，非窮舉所有可能的繞過手法；若
未來需要更細緻的資料流分析，屬另一個層次的驗證，非本檔涵蓋範圍。

R66 追加（DEF-101-627）：本應為 `sdd_latest` 新增專屬 `tools/tests/test_sdd_latest.py`，但棘輪要求
擴充既有檔，故其回歸鎖併入本檔；`exclude_frozen_sdd_versions` 過濾語意併入姊妹檔
`test_sanitize_component_frozen_sdd_versions_lock.py`。沿革搬至
Guard_Line_History_2.md〈R186 淨減法搬遷〉§10。  round-label-ok

執行：python -m pytest tools/tests/test_component_sanitizer_shared_layer_lock.py -v
"""
from __future__ import annotations

import inspect
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SDD_ROOT = _REPO_ROOT / "AISDLC_SDD"
_SHARED_MODULE_PATH = _SDD_ROOT / "scripts" / "component_sanitizer.py"

sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
import sdd_latest  # noqa: E402

# 已知需達到的版本下限（29 凍結 + 1 LATEST = 30；R45 建檔時的實際數量）。若未來
# 新增版本，此下限只會被超過、不會被打破；若數字倒退，代表掃描邊界被靜默縮小。
_MIN_EXPECTED_TOTAL_VERSIONS = 30

_PROBE_SCRIPT = """
import json
import sys
sys.path.insert(0, {version_root!r})
from tools.fsm_runtime import state_loader

shared = getattr(state_loader, "_shared_component_sanitizer", None)
result = {{
    "reserved": state_loader._sanitize_component("CON"),
    "forbidden_char": state_loader._sanitize_component("proj<name"),
    "control_char": state_loader._sanitize_component("proj" + chr(1) + "name"),
    "long_len": len(state_loader._sanitize_component("a" * 200)),
    "shared_module_file": getattr(shared, "__file__", None),
}}
print(json.dumps(result))
"""


def _latest_sdd_version_name() -> str:
    """LATEST 版本名（sdd_version.py SSOT；解析失敗即 fail-loud）。委派
    tools/lib/sdd_latest.py 單一真相源（ADR-XPLAT-002 Phase 2-C，R66 收斂）。"""
    return sdd_latest.resolve_latest_name(_SDD_ROOT)


def _all_version_dirs() -> list[Path]:
    """全部版本目錄（29 凍結 + LATEST），依版本名稱排序。"""
    latest_name = _latest_sdd_version_name()
    dirs = [
        p for p in _SDD_ROOT.iterdir()
        if p.is_dir()
        and (sdd_latest.FROZEN_VERSION_DIR_RE.fullmatch(p.name) or p.name == latest_name)
    ]
    return sorted(dirs, key=lambda p: p.name)


def _probe_version(version_dir: Path) -> dict:
    script = _PROBE_SCRIPT.format(version_root=str(version_dir))
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"{version_dir.name}: state_loader 匯入/呼叫失敗（rc={proc.returncode}）\n"
            f"stdout={proc.stdout}\nstderr={proc.stderr}"
        )
    return json.loads(proc.stdout.strip().splitlines()[-1])


class TestSharedComponentSanitizerModuleExists(unittest.TestCase):
    def test_shared_module_file_exists(self) -> None:
        self.assertTrue(
            _SHARED_MODULE_PATH.is_file(),
            f"共用淨化模組遺失：{_SHARED_MODULE_PATH}——DEF-101-358 的共用層基礎已不存在",
        )


class TestScanBoundary(unittest.TestCase):
    def test_at_least_30_versions_scanned(self) -> None:
        dirs = _all_version_dirs()
        self.assertGreaterEqual(
            len(dirs), _MIN_EXPECTED_TOTAL_VERSIONS,
            f"掃描到的版本數只有 {len(dirs)}（預期至少 {_MIN_EXPECTED_TOTAL_VERSIONS}，"
            "含 LATEST）——掃描邊界是否被靜默縮小？",
        )


class TestEveryVersionDelegatesToSharedSanitizer(unittest.TestCase):
    """主鎖：每個版本（29 凍結 + LATEST）皆須透過共用模組取得強化版
    _sanitize_component，behavioral 驗證（見頂部 docstring 方法論）。"""

    def test_every_version_sanitize_component_blocks_known_hostile_inputs(self) -> None:
        offenders: list[str] = []
        for version_dir in _all_version_dirs():
            result = _probe_version(version_dir)
            if not result["reserved"].startswith("_"):
                offenders.append(
                    f"{version_dir.name}: 未擋下保留裝置名 CON：{result['reserved']!r}"
                )
            if "<" in result["forbidden_char"]:
                offenders.append(
                    f"{version_dir.name}: 未擋下 Windows 禁用字元 <：{result['forbidden_char']!r}"
                )
            if chr(1) in result["control_char"]:
                offenders.append(
                    f"{version_dir.name}: 未擋下控制字元：{result['control_char']!r}"
                )
            if result["long_len"] > 80:
                offenders.append(
                    f"{version_dir.name}: 未截斷超長字串，長度={result['long_len']}"
                )
        self.assertEqual(
            offenders, [],
            "以下版本的 _sanitize_component 未達 DEF-101-358 要求的強化防護水準："
            f"{offenders}",
        )

    def test_every_version_delegates_to_the_same_shared_module_file(self) -> None:
        expected = _SHARED_MODULE_PATH.resolve()
        offenders: list[str] = []
        for version_dir in _all_version_dirs():
            result = _probe_version(version_dir)
            shared_file = result["shared_module_file"]
            if not shared_file:
                offenders.append(
                    f"{version_dir.name}: state_loader 未透過 _shared_component_sanitizer "
                    "委派（疑似又長出獨立複本，SSOT 已分裂）"
                )
                continue
            if Path(shared_file).resolve() != expected:
                offenders.append(
                    f"{version_dir.name}: 委派目標不是預期的共用模組檔案——"
                    f"實際={shared_file}，預期={expected}"
                )
        self.assertEqual(
            offenders, [],
            f"以下版本未正確委派到唯一的共用淨化模組：{offenders}",
        )


class TestFrozenVersionDirRegexFullmatchLock(unittest.TestCase):
    """R66 追加（DEF-101-627）：`sdd_latest.FROZEN_VERSION_DIR_RE` 的 `.fullmatch()`
    正確性永久回歸鎖（DEF-101-624 修的正是這個邊界）。

    WHY：`$` 錨在非 MULTILINE 模式下對「字串結尾前恰有一個換行字元」的位置也
    視為滿足，而 `.match()` 不要求吃光整段輸入，兩者相乘會讓帶尾隨換行字元的
    偽造目錄名被誤判為合法版本目錄名；`.fullmatch()` 要求輸入從頭到尾整段對齊
    pattern，同一輸入下正確地不命中。本鎖鎖住這個行為差異本身，而非只鎖某一次
    手動驗證當下印出的文字。"""

    def test_fullmatch_rejects_trailing_newline(self) -> None:
        self.assertIsNone(
            sdd_latest.FROZEN_VERSION_DIR_RE.fullmatch("AISDLC_SDD_v0.30\n"),
            ".fullmatch() 對帶尾隨換行字元的偽造目錄名應回傳 None"
            "——DEF-101-624 修復的邊界情境倒退",
        )

    def test_match_would_have_wrongly_accepted_trailing_newline(self) -> None:
        """WHY 佐證（非驗證 production 行為）：重現 DEF-101-624 修復前若誤用
        `.match()` 會得到的錯誤命中，說明為何本模組的呼叫慣例硬性要求
        `.fullmatch()`——若本斷言本身失敗，代表 Python regex `$` 錨語意已變，
        需重新評估本模組的 fullmatch 慣例是否仍必要。"""
        self.assertIsNotNone(sdd_latest.FROZEN_VERSION_DIR_RE.match("AISDLC_SDD_v0.30\n"))

    def test_fullmatch_accepts_real_version_dir_names(self) -> None:
        self.assertIsNotNone(sdd_latest.FROZEN_VERSION_DIR_RE.fullmatch("AISDLC_SDD_v0.30"))
        self.assertIsNotNone(sdd_latest.FROZEN_VERSION_DIR_RE.fullmatch("AISDLC_SDD_v0.01"))

    def test_fullmatch_rejects_non_version_strings(self) -> None:
        for bad in (
            "AISDLC_SDD_v0.30/extra",
            "AISDLC_SDD_v0.30 ",
            " AISDLC_SDD_v0.30",
            "AISDLC_SDD_v0.30\r\n",
            "not_a_version_dir",
        ):
            with self.subTest(bad=bad):
                self.assertIsNone(sdd_latest.FROZEN_VERSION_DIR_RE.fullmatch(bad))


class TestOwnCallSiteStaysOnFullmatch(unittest.TestCase):
    """R66 追加（DEF-101-627）：本檔自己的 `_all_version_dirs()` call-site 鎖——
    只鎖 `FROZEN_VERSION_DIR_RE` 本身的行為（上一個測試類別）不足以擋住「呼叫端
    自己把 `.fullmatch(` 又改回 `.match(`」這種退步，regex 定義正確、呼叫端
    方法用錯一樣重現原缺陷。手法同 `test_dev_start.py::
    TestVenvSelfHealCallSitesUseSafeRmtree`（`inspect.getsource` +
    `assertIn`/`assertNotIn` 原始碼字面檢查）。"""

    def test_all_version_dirs_uses_fullmatch(self) -> None:
        src = inspect.getsource(_all_version_dirs)
        self.assertIn(
            "FROZEN_VERSION_DIR_RE.fullmatch(", src,
            "_all_version_dirs() 不再呼叫 .fullmatch( — DEF-101-624 修復被還原")
        self.assertNotIn(
            "FROZEN_VERSION_DIR_RE.match(", src,
            "_all_version_dirs() 又改回裸 .match( — 帶尾隨換行字元的偽造目錄名"
            "會被誤判為合法版本目錄（DEF-101-624 迴歸）")


class TestResolveLatestAgainstRealRepo(unittest.TestCase):
    """R66 追加（DEF-101-627）：`resolve_latest_name`/`resolve_latest_root` 正常
    路徑（對真實 AISDLC_SDD 根目錄，非 mock——這正是消費者實際使用的方式）。"""

    def test_resolve_latest_name_matches_expected_pattern_and_exists(self) -> None:
        name = sdd_latest.resolve_latest_name(_SDD_ROOT)
        self.assertRegex(name, r"^AISDLC_SDD_v\d+\.\d+$")
        self.assertTrue((_SDD_ROOT / name).is_dir())

    def test_resolve_latest_root_equals_sdd_root_join_name(self) -> None:
        name = sdd_latest.resolve_latest_name(_SDD_ROOT)
        root = sdd_latest.resolve_latest_root(_SDD_ROOT)
        self.assertEqual(root, _SDD_ROOT / name)
        self.assertTrue(root.is_dir())


class TestResolveLatestFailLoud(unittest.TestCase):
    """R66 追加（DEF-101-627）：`resolve_latest_name`/`resolve_latest_root` 的
    fail-loud 路徑——`sdd_root/scripts/sdd_version.py` 不存在時，subprocess
    執行一支不存在的腳本檔必然 rc!=0、stdout 為空，兩個入口皆須 raise
    AssertionError，不得靜默回傳空字串或 None（掃描邊界不得靜默縮小，見
    `tools/lib/sdd_latest.py` 模組 docstring）。"""

    def test_resolve_latest_name_raises_when_resolver_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_root = Path(td)  # 刻意不建立 scripts/sdd_version.py
            with self.assertRaises(AssertionError) as ctx:
                sdd_latest.resolve_latest_name(fake_root)
            self.assertIn("LATEST 解析失敗", str(ctx.exception))

    def test_resolve_latest_root_raises_when_resolver_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_root = Path(td)
            with self.assertRaises(AssertionError) as ctx:
                sdd_latest.resolve_latest_root(fake_root)
            self.assertIn("LATEST 解析失敗", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
