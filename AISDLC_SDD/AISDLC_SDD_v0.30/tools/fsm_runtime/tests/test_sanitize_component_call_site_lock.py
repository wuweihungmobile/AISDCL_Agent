"""fsm_runtime 模組內「已知外部風險 ID」全站淨化涵蓋率鎖 — R41 Architect 架構最佳化，
R46 抽為共用層（DEF-101-378，見 `AISDLC_SDD/scripts/component_sanitizer_callsite_scan.py`）。

背景（架構層系統性缺陷偵測，非逐行找 bug）：R37 為 WindowsApps guard 建了
repo-wide 前瞻防增生鎖，把「同一缺陷類別在不同呼叫點反覆復發、只能逐一補洞」的
架構缺口物理消滅。但 `_sanitize_component()`（本模組淨化外部風險字串當檔名片段
的 SSOT，定義於 state_loader.py）的呼叫點漏接，是同構的另一個反覆復發缺陷類別
（DEF-101-219 → DEF-101-295 → DEF-101-324/335 → DEF-101-327 → DEF-101-328 →
DEF-101-334），過去多輪皆是「Scan 掃到才補」的點狀修復。本檔補上對稱鎖，讓
「新呼叫點忘記淨化」這個根因無法再逃過機械守門。

R46（DEF-101-378）：本檔原本自行內嵌全部掃描邏輯，只掃 LATEST 一個版本目錄
——29 個凍結版本從建立以來從未被這支測試檢查過（該測試檔本身也不存在於
v0.01~v0.29 任何一版），是 `path_cost.py::_write_milestone()` 這類漏洞
（DEF-101-379：LATEST 早已修好但 29 份凍結副本從未回補）能完全躲過機械偵測的
結構性根因。比照 R45 `component_sanitizer.py`（淨化函式本身）同一手法，抽出
共用掃描邏輯至 `AISDLC_SDD/scripts/component_sanitizer_callsite_scan.py`（含
BoolOp／IfExp 遞迴拆解 + 有界別名追蹤兩項新增修復），本檔改為 import 該共用層，
**繼續守 LATEST 未來新增呼叫點**這個既有職責不變（Rule 3 手術式變更：不搬動
正在運作中的既有測試職責）；`AISDLC_SDD/scripts/tests/
test_sanitize_component_callsite_frozen_versions.py`（新檔）另外用同一份共用
邏輯把唯讀掃描範圍擴大至全部 30 個版本（LATEST + 29 個凍結版本）。

共用層本身的方法論細節（風險名單凍結快照理由、BoolOp/別名追蹤範圍與深度、
`_KNOWN_EXEMPTIONS`/`_ADDITIONAL_RISKY_NAMES` 人工把關模式、已知盲點方法論邊界
如巢狀 f-string／pathlib `/`／`str.join()`／具名模板常數等）一律見
`component_sanitizer_callsite_scan.py` 模組 docstring，本檔不重複。

執行：python -m pytest tools/fsm_runtime/tests/test_sanitize_component_call_site_lock.py -v
"""
from __future__ import annotations

import importlib.util as _importlib_util
import unittest
from pathlib import Path

_FSM_RUNTIME_DIR = Path(__file__).resolve().parent.parent
# 本檔 → tests → fsm_runtime → tools → AISDLC_SDD_v0.30 → AISDLC_SDD（同 state_loader.py
# 委派 component_sanitizer.py 的路徑深度慣例，唯獨本檔多一層 tests/）
_SHARED_SCAN_PATH = (
    Path(__file__).resolve().parents[4] / "scripts" / "component_sanitizer_callsite_scan.py"
)


def _load_shared_scan_module():
    spec = _importlib_util.spec_from_file_location(
        "_aisdlc_sdd_shared_component_sanitizer_callsite_scan", _SHARED_SCAN_PATH
    )
    assert spec is not None and spec.loader is not None, (
        f"共用掃描模組載入失敗：{_SHARED_SCAN_PATH}"
    )
    module = _importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_scan = _load_shared_scan_module()


class TestSanitizeComponentCallSiteCoverage(unittest.TestCase):
    """repo-wide 前瞻防增生鎖——任何新增（或既有漏網）的組檔名呼叫點，只要用了
    模組內已知需淨化的識別字名稱卻未經 `_sanitize_component()`，就逃不過本測試
    （手法對稱套用 `TestNoOrphanWindowsAppsImplementation` 的「repo-wide 掃描 +
    凍結/例外清單」模式到 `_sanitize_component()` 這個不同的 SSOT）。本檔只掃
    LATEST（`_FSM_RUNTIME_DIR`）；跨全部 30 版的唯讀掃描見
    `AISDLC_SDD/scripts/tests/test_sanitize_component_callsite_frozen_versions.py`。"""

    def test_all_filename_fstrings_sanitize_known_risky_identifiers(self) -> None:
        files = _scan.iter_module_files(_FSM_RUNTIME_DIR)
        risky_names = _scan.risky_identifier_names()
        self.assertTrue(risky_names, "風險名單為空——凍結清單可能被誤清空，檢查 _FROZEN_RISKY_NAMES")

        offenders = _scan.find_offenders(files)
        self.assertEqual(
            offenders, [],
            "發現組檔名時漏接 _sanitize_component() 的已知風險識別字，疑似 "
            f"DEF-101-219/295/324/327/328 類別復發：{offenders}——新呼叫點請 "
            "import state_loader._sanitize_component 後包裝，或若確認已有等效"
            "防護，於 component_sanitizer_callsite_scan.py 的 _KNOWN_EXEMPTIONS "
            "登記並附決策理由。",
        )

    def test_live_bootstrap_is_subset_of_frozen_list(self) -> None:
        """凍結清單新鮮度檢查（R41 QA 一審發現後新增，非阻擋機制本體）：若目前
        程式碼冒出全新識別字名稱呼叫 `_sanitize_component()`（凍結清單裡沒有），
        提醒人工核實後手動登記進 `_FROZEN_RISKY_NAMES`——防止凍結清單本身腐化、
        跟不上新呼叫點引入的新風險名稱。"""
        files = _scan.iter_module_files(_FSM_RUNTIME_DIR)
        trees = _scan.parse_all(files)
        live_names = _scan.live_bootstrapped_names(trees)
        unknown = live_names - _scan._FROZEN_RISKY_NAMES - _scan._ADDITIONAL_RISKY_NAMES
        self.assertEqual(
            unknown, set(),
            "發現新識別字呼叫 _sanitize_component() 但未登記進 _FROZEN_RISKY_NAMES："
            f"{unknown}——人工核實此為外部風險字串後，加入 component_sanitizer_"
            "callsite_scan.py 的 _FROZEN_RISKY_NAMES。",
        )

    def test_known_exemptions_still_referenced(self) -> None:
        """例外清單防腐化：登記例外的檔案須仍存在，避免『檔案已刪除/改名但例外
        仍宣稱豁免』的假綠洞（同 WindowsApps 鎖同一防腐化手法）。"""
        for (filename, _identifier), _reason in _scan._KNOWN_EXEMPTIONS.items():
            self.assertTrue(
                (_FSM_RUNTIME_DIR / filename).is_file(),
                f"已登記例外的檔案遺失：{filename}",
            )

    def test_additional_risky_names_still_have_wrapper(self) -> None:
        """`_ADDITIONAL_RISKY_NAMES` 防腐化：登記的補充名稱須仍能在模組內某個
        呼叫 `_sanitize_component()` 的委派 wrapper 函式中找到同名形參，避免
        wrapper 被刪除/改名後補充清單仍宣稱涵蓋的假綠洞。"""
        import ast

        files = _scan.iter_module_files(_FSM_RUNTIME_DIR)
        trees = _scan.parse_all(files)
        wrapper_param_names: set[str] = set()
        for tree in trees.values():
            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef):
                    continue
                calls_sanitize = any(
                    isinstance(inner, ast.Call)
                    and isinstance(inner.func, ast.Name)
                    and inner.func.id == "_sanitize_component"
                    for inner in ast.walk(node)
                )
                if calls_sanitize:
                    wrapper_param_names.update(a.arg for a in node.args.args)

        for name in _scan._ADDITIONAL_RISKY_NAMES:
            self.assertIn(
                name, wrapper_param_names,
                f"`_ADDITIONAL_RISKY_NAMES` 登記的 `{name}` 已找不到對應的委派 "
                "wrapper 函式形參，登記可能已腐化，須重新核實或移除",
            )


if __name__ == "__main__":
    unittest.main()
