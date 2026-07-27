"""跨全部 AISDLC_SDD 版本（LATEST + 全部凍結基線）的唯讀 AST 呼叫點掃描
——R46 新增（DEF-101-378 掃描範圍擴大）。

WHY（架構層系統性缺陷偵測，非逐行找 bug）：
`AISDLC_SDD_v0.30/tools/fsm_runtime/tests/test_sanitize_component_call_site_lock.py`
（LATEST 版）只守 LATEST 一個版本目錄——這支測試檔本身根本不存在於任何一個凍結
版本（v0.01~v0.29）裡，29 個凍結版本從建立以來從未被這支 AST 掃描器檢查過。這正
是 `path_cost.py::_write_milestone()` 這類「LATEST 早已修好、但 29 份凍結副本從未
回補」漏洞（DEF-101-379）能完全躲過機械偵測、直到人工全新掃描才發現的結構性根因
——與 R43/R44 揭露的「新規則預設排除凍結版本」同一類系統性缺口同構。

本檔用共用掃描邏輯（`component_sanitizer_callsite_scan.py`，R46 從 LATEST 版測試
抽出，見該模組 docstring 完整方法論；含 DEF-101-378 修復的 BoolOp／IfExp 遞迴拆解
與有界別名追蹤兩項）對全部版本目錄做**唯讀**掃描。

Copy-on-Evolve 邊界：鐵律禁止的是「原地修改凍結版本的檔案內容」，不禁止「從外部
讀取/掃描」——本檔只讀不寫，不牴觸該鐵律（先例：`tools/tests/
test_windowsapps_guard_cross_consistency.py` 本就對全 repo 含凍結版本路徑做唯讀
掃描；R44 亦已示範唯讀掃描揪出凍結版本真實缺陷後，經使用者核准可對凍結內容做
例外回補）。

執行：cd AISDLC_SDD && python -m pytest scripts/tests/test_sanitize_component_callsite_frozen_versions.py -v
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = os.path.dirname(__file__)
SDD_ROOT = Path(os.path.abspath(os.path.join(HERE, "..", "..")))  # AISDLC_SDD/
sys.path.insert(0, os.path.join(str(SDD_ROOT), "scripts"))

from component_sanitizer_callsite_scan import find_offenders, iter_module_files  # noqa: E402
from sdd_version import VERSION_DIR_RE, disk_version_dirs, tracked_version_dirs  # noqa: E402


def _all_version_dirs() -> list[str]:
    """全部版本目錄名，tracked ∪ 磁碟（git 不可用時 fallback 純磁碟掃描）——唯讀
    掃描不需要 `sdd_version.py::latest_version_name()` 的排他式單一 LATEST 判斷，
    寧可多掃（含理論上未 tracked 的合法命名目錄）也不可少掃。"""
    tracked = tracked_version_dirs(SDD_ROOT)
    disk = disk_version_dirs(SDD_ROOT)
    names = disk if tracked is None else (tracked | disk)
    return sorted(
        names,
        key=lambda n: tuple(int(x) for x in VERSION_DIR_RE.fullmatch(n).groups()),
    )


def test_at_least_one_version_directory_found() -> None:
    """防呆：掃描邊界不得靜默縮小成 0（例如 SDD_ROOT 路徑算錯）。"""
    versions = _all_version_dirs()
    assert versions, f"找不到任何 AISDLC_SDD_v*.* 版本目錄於 {SDD_ROOT}"


# R57 修正（B2 掃描面缺口）：本鎖原本每個版本只掃 `tools/fsm_runtime/`，
# 同版本內另外兩處也會寫檔的生產程式碼目錄從未被這支前瞻鎖看過——
# `.claude/hooks/`（session_start／context_ledger_pre/post／post_commit_drift／
# closure_evidence_verify，30 版共 139 個 .py，且 hook 本就會落地 ledger/證據檔）
# 與 `tools/arch_fitness/`（30 版共 30 個 .py）。實測擴面後 30 版全數 0 offender，
# 故本次擴面不改變現況判定，價值全在「前瞻」：未來若有人在 hook 或 arch_fitness
# 裡用 rule_id／ac_id 等風險識別字組檔名而忘記淨化，本鎖現在會抓到，先前不會。
_SCAN_SUBDIRS = ("tools/fsm_runtime", ".claude/hooks", "tools/arch_fitness")
# 掃描面下限：30 版 × 3 目錄（新增版本只會使其變大，縮小＝掃描邊界被靜默切掉）
_MIN_SCANNED_DIRS = 90


def test_all_versions_have_no_unsanitized_callsite_offenders() -> None:
    versions = _all_version_dirs()
    all_offenders: list[str] = []
    scanned_versions: list[str] = []
    scanned_dirs: list[str] = []

    for version in versions:
        fsm_dir = SDD_ROOT / version / "tools" / "fsm_runtime"
        if not fsm_dir.is_dir():
            continue  # 防呆跳過（理論上每個版本皆有 fsm_runtime，同構目錄結構）
        scanned_versions.append(version)
        for subdir in _SCAN_SUBDIRS:
            scan_dir = SDD_ROOT / version / Path(subdir)
            if not scan_dir.is_dir():
                continue  # 防呆跳過（同構目錄結構下三者皆應存在）
            scanned_dirs.append(f"{version}/{subdir}")
            files = iter_module_files(scan_dir)
            offenders = find_offenders(files)
            all_offenders.extend(f"[{version}/{subdir}] {o}" for o in offenders)

    assert len(scanned_versions) >= 30, (
        f"實際掃到的版本數異常偏少（{len(scanned_versions)}／{versions}），"
        "掃描邊界可能被靜默縮小，須先查明原因再放行"
    )
    assert len(scanned_dirs) >= _MIN_SCANNED_DIRS, (
        f"實際掃到的目錄數異常偏少（{len(scanned_dirs)} < {_MIN_SCANNED_DIRS}），"
        f"掃描面可能被靜默縮小（應為版本數 × {len(_SCAN_SUBDIRS)} 個子目錄）"
    )
    assert all_offenders == [], (
        "跨版本唯讀掃描發現未淨化的組檔名呼叫點（DEF-101-378 掃描範圍擴大後的"
        f"首次 repo-wide 前瞻鎖，疑似 DEF-101-379 同類缺口）：{all_offenders}"
        "——凍結版本的修復須先取得人工核准打破 Copy-on-Evolve（比照 R44/R45/R46"
        "判例），LATEST 則直接修復並確認 test_sanitize_component_call_site_"
        "lock.py 仍綠。"
    )
