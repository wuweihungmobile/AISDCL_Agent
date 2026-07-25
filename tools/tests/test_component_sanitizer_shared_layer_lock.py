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

方法論：對每個版本目錄用 subprocess 起一個乾淨行程匯入該版本的
`tools.fsm_runtime.state_loader`（cwd/sys.path 皆限定該版本根目錄），實測呼叫
`_sanitize_component()` 對已知危險輸入的行為，而非只做文字 pattern 比對——
behavioral 驗證比純文字比對更難被規避：若日後有人把委派邏輯內嵌展開成看似
不同的寫法，文字比對可能誤判為異常，但只要行為仍等價，behavioral 驗證仍會
通過；反之若有人真的另外寫了一份新的弱化實作，文字比對可能因湊巧含有相似
字串而誤判通過，behavioral 驗證則不會被騙。

刻意用 subprocess 而非同行程 import（理由同
`tools/tests/test_sanitize_component_frozen_sdd_versions_lock.py`::
`_latest_sdd_version_name` 與 `test_state_component_sanitizer_parity.py` 的既有
選擇）：30 個版本的 `tools.fsm_runtime.state_loader` 是同一個完全限定模組
名稱，同行程內用 `sys.path` 插拔 + `sys.modules` 手動清快取雖然可行，但每次
都要正確清乾淨三層（`tools` / `tools.fsm_runtime` / `tools.fsm_runtime.
state_loader`），一次沒清乾淨就會讓後面的版本悄悄沿用前一個版本已快取的模組
物件、產生假陽性通過；subprocess 天生行程隔離，不需要人工維護清快取的
正確性，用執行時間換正確性。

方法論邊界（誠實記載，同既有鎖 docstring 先例）：本檔只驗證「委派目標是否為
預期的共用模組檔案 + 已知危險輸入是否被擋下」，非窮舉所有可能的繞過手法；若
未來需要更細緻的資料流分析，屬另一個層次的驗證，非本檔涵蓋範圍。

執行：python -m pytest tools/tests/test_component_sanitizer_shared_layer_lock.py -v
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SDD_ROOT = _REPO_ROOT / "AISDLC_SDD"
_SHARED_MODULE_PATH = _SDD_ROOT / "scripts" / "component_sanitizer.py"

_FROZEN_VERSION_DIR_RE = re.compile(r"^AISDLC_SDD_v\d+\.\d+$")

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
    """LATEST 版本名（sdd_version.py SSOT）。手法同
    tools/tests/test_windowsapps_guard_bash_parity.py::_latest_sdd_version_name
    ——subprocess 呼叫 CLI，避免 sys.path 汙染；解析失敗即 fail-loud。"""
    resolver = _SDD_ROOT / "scripts" / "sdd_version.py"
    proc = subprocess.run(
        [sys.executable, str(resolver), "--sdd-root", str(_SDD_ROOT)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    name = proc.stdout.strip()
    if proc.returncode != 0 or not name:
        raise AssertionError(
            f"LATEST 解析失敗（sdd_version.py rc={proc.returncode}；stderr="
            f"{proc.stderr.strip()!r}）——掃描邊界不得靜默縮小"
        )
    return name


def _all_version_dirs() -> list[Path]:
    """全部版本目錄（29 凍結 + LATEST），依版本名稱排序。"""
    latest_name = _latest_sdd_version_name()
    dirs = [
        p for p in _SDD_ROOT.iterdir()
        if p.is_dir() and (_FROZEN_VERSION_DIR_RE.match(p.name) or p.name == latest_name)
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


if __name__ == "__main__":
    unittest.main()
