"""RFC 生命週期 lint 意圖鎖（DEF-23-005）.

每個 case 編碼「為何此行為重要」（Rule 9）：lint 的價值＝在 RFC 收官後機械攔截
「已決 RFC 滯留 active/」，且**不得誤報** genuinely-proposed RFC（否則開發者會關掉 lint）。
故正例（已決→fire）與負例（待決→pass）對稱覆蓋，並鎖死「只掃最新版」「語意版本」邊界。
"""
from __future__ import annotations

import os

import pytest

from scripts import rfc_lifecycle_lint as lint


def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _mk_repo(tmp_path, versions: list[str]) -> str:
    """建假 repo：每版含 build/planning/active 目錄；回傳 repo_root。"""
    repo = str(tmp_path)
    for v in versions:
        os.makedirs(os.path.join(repo, v, "build", "planning", "active"), exist_ok=True)
    return repo


# ── 已決偵測（正例，須 fire）────────────────────────────────────────────────

def test_landed_version_existing_fires(tmp_path):
    """RFC 宣告落地版本＝已存在的凍結版 → 已決、已凍結，滯留 active/ 即違規。

    為何重要：這正是 DEF-23-005 本體（v0.12/v0.13 active/ 滯留 _26/_27）的機械再現。
    """
    repo = _mk_repo(tmp_path, ["AISDLC_SDD_v0.13", "AISDLC_SDD_v0.14"])
    _write(os.path.join(repo, "AISDLC_SDD_v0.14", "build", "planning", "active", "RFC_28.md"),
           "# RFC 28\n**落地版本**：AISDLC_SDD_v0.14（Copy-on-Evolve）\n")
    v = lint.lint(repo)
    assert len(v) == 1 and v[0][0] == "RFC_28.md"
    assert "AISDLC_SDD_v0.14" in v[0][1]


def test_closed_status_fires(tmp_path):
    """顯式結案狀態行 → 已決，滯留 active/ 即違規（不依賴落地版本欄）。"""
    repo = _mk_repo(tmp_path, ["AISDLC_SDD_v0.14"])
    _write(os.path.join(repo, "AISDLC_SDD_v0.14", "build", "planning", "active", "RFC_X.md"),
           "# RFC X\n**狀態**：已決\n決策：採納。\n")
    v = lint.lint(repo)
    assert len(v) == 1 and "結案狀態" in v[0][1]


# ── 待決（負例，不得 fire — 防誤報）──────────────────────────────────────────

def test_proposed_rfc_passes(tmp_path):
    """genuinely-proposed RFC（有前置基線、無落地版本、無結案狀態）→ 不得誤報。"""
    repo = _mk_repo(tmp_path, ["AISDLC_SDD_v0.14"])
    _write(os.path.join(repo, "AISDLC_SDD_v0.14", "build", "planning", "active", "RFC_P.md"),
           "# RFC P\n**前置基線**：v0.14 凍結\n**決策**：（待人工 review）\n")
    assert lint.lint(repo) == []


def test_landed_version_nonexisting_passes(tmp_path):
    """落地版本（精確欄）指向尚未存在的版（v0.99）→ 仍是『目標』非『已落地』，不得誤報。

    為何重要：proposal 常先寫目標落地版本；只有該版『已凍結存在於磁碟』才算已決（鎖存在性閘）。
    """
    repo = _mk_repo(tmp_path, ["AISDLC_SDD_v0.14"])
    _write(os.path.join(repo, "AISDLC_SDD_v0.14", "build", "planning", "active", "RFC_T.md"),
           "# RFC T\n**落地版本**：AISDLC_SDD_v0.99（規劃中，尚未凍結）\n")
    assert lint.lint(repo) == []


def test_inline_marker_mentions_not_fired(tmp_path):
    """meta 文件為『說明偵測規則』而引用 token（inline-code / 句中）→ 不得誤報。

    為何重要：本 lint 的 RFC 文件本身含 `狀態：已決` / `落地版本：vX` 字面當範例；dogfooding
    當場揭露此誤報源 → 偵測須錨定行首 header 欄位式，inline 提及不算已決標記。
    """
    repo = _mk_repo(tmp_path, ["AISDLC_SDD_v0.14"])
    _write(os.path.join(repo, "AISDLC_SDD_v0.14", "build", "planning", "active", "meta.md"),
           "# 說明 RFC\n"
           "本 lint 偵測：宣告 `落地版本：AISDLC_SDD_v0.14` 且該版存在者算已決；\n"
           "或顯式結案狀態行 `狀態：已決/結案`。genuinely-proposed RFC 兩者皆無。\n"
           "**落地形態**：shared infra（不指向任何 vX）\n")
    assert lint.lint(repo) == []


# ── 邊界 ────────────────────────────────────────────────────────────────────

def test_gitkeep_and_nonmd_ignored(tmp_path):
    """.gitkeep / 非 .md 檔不掃（空 active/ 只有 .gitkeep 是常態）。"""
    repo = _mk_repo(tmp_path, ["AISDLC_SDD_v0.14"])
    active = os.path.join(repo, "AISDLC_SDD_v0.14", "build", "planning", "active")
    _write(os.path.join(active, ".gitkeep"), "")
    _write(os.path.join(active, "note.txt"), "落地版本：AISDLC_SDD_v0.14")
    assert lint.lint(repo) == []


def test_empty_active_passes(tmp_path):
    """v0.14 active/ 空（現況）→ pass（lint 價值在防未來復發）。"""
    repo = _mk_repo(tmp_path, ["AISDLC_SDD_v0.14"])
    assert lint.lint(repo) == []


def test_scans_only_latest_version(tmp_path):
    """只掃最新版：舊版 active/ 滯留已決 RFC（Copy-on-Evolve 歷史快照）不得 fire。

    為何重要：v0.12/v0.13 至今凍結著 _26/_27；掃舊版會對歷史誤報、且違反『不動凍結本體』。
    """
    repo = _mk_repo(tmp_path, ["AISDLC_SDD_v0.13", "AISDLC_SDD_v0.14"])
    # 舊版滯留已決 RFC（模擬真實 v0.13）
    _write(os.path.join(repo, "AISDLC_SDD_v0.13", "build", "planning", "active", "old.md"),
           "**落地版本**：AISDLC_SDD_v0.13\n")
    # 最新版 active/ 乾淨
    assert lint.lint(repo) == []


def test_latest_version_semantic(tmp_path):
    """語意版本：v0.10 > v0.9（非字典序），對齊 scripts/sdd_version.py SSOT 的數值排序語意。"""
    assert lint.latest_version({"AISDLC_SDD_v0.9", "AISDLC_SDD_v0.10"}) == "AISDLC_SDD_v0.10"
    assert lint.latest_version(set()) is None


# ── DEF-43-003：major version bump（v1.x）兩端盲區封閉 ─────────────────────────

def test_latest_version_major_bump(tmp_path):
    """v1.00 > v0.18：major bump 後新版必勝（原硬寫死 major=0 會把 v1.00 當 (0,0) 排輸）。

    為何重要：一旦 Copy-on-Evolve 升 v1.00，若 latest_version 仍硬寫死 major=0，LATEST 會
    退回 v0.x → 父層 skills 鏡像停在舊版、ci-gate 雙軌不測新版（DEF-43-003 靜默退化）。
    """
    assert lint.latest_version({"AISDLC_SDD_v0.18", "AISDLC_SDD_v1.00"}) == "AISDLC_SDD_v1.00"
    assert lint.latest_version({"AISDLC_SDD_v1.2", "AISDLC_SDD_v1.10"}) == "AISDLC_SDD_v1.10"


def test_discover_finds_v1_dirs(tmp_path):
    """discover_frozen_versions 須認得 v1.x 目錄（原 VERSION_RE `v0\\.` 會整個漏掉）。"""
    repo = _mk_repo(tmp_path, ["AISDLC_SDD_v0.18", "AISDLC_SDD_v1.00"])
    found = lint.discover_frozen_versions(repo)
    assert "AISDLC_SDD_v1.00" in found and "AISDLC_SDD_v0.18" in found


def test_main_exit_codes(tmp_path, capsys):
    """CLI：乾淨 exit 0、有違規 exit 1（ci-gate 硬閘語意）。"""
    clean = _mk_repo(tmp_path, ["AISDLC_SDD_v0.14"])
    assert lint.main([clean]) == 0
    dirty = _mk_repo(tmp_path / "d", ["AISDLC_SDD_v0.14"])
    _write(os.path.join(dirty, "AISDLC_SDD_v0.14", "build", "planning", "active", "r.md"),
           "**落地版本**：AISDLC_SDD_v0.14\n")
    assert lint.main([dirty]) == 1
    out = capsys.readouterr().out
    assert "DEF-23-005" in out


def test_real_repo_v014_active_clean():
    """真實 repo 鎖：v0.14（最新）active/ 現況乾淨（improving_23 已清）→ lint pass。"""
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assert lint.lint(repo_root) == []


# ── W-33-2（DEF-30-001）：狀態欄標準化 + 缺欄 advisory warn ────────────────────

def test_closed_status_decided_token_fires(tmp_path):
    """標準英文 token『狀態：decided』→ 識別為已決（DEF-30-001 標準化）。

    為何重要：DEF-30-001 標準化狀態詞彙為 proposed/decided；新標準 decided token 須與
    既有『已決』同等被 decided 偵測攔下，否則用標準寫法的已決 RFC 滯留 active/ 漏網。
    """
    repo = _mk_repo(tmp_path, ["AISDLC_SDD_v0.14"])
    _write(os.path.join(repo, "AISDLC_SDD_v0.14", "build", "planning", "active", "RFC_D.md"),
           "# RFC D\n**狀態**：decided\n決策：採納。\n")
    v = lint.lint(repo)
    assert len(v) == 1 and "結案狀態" in v[0][1]


def test_active_rfc_missing_status_warns_not_fails(tmp_path):
    """active/ RFC 缺標準『**狀態**：』欄 → advisory（缺欄清單），但非硬違規（不阻擋）。

    為何重要：DEF-30-001 的『缺 狀態 欄即 warn』強制慣例——缺欄是慣例提醒（exit 0），
    與『已決滯留 active/』（exit 1）嚴格分級，避免合法 proposed RFC 因缺欄被當硬違規擋下。
    """
    repo = _mk_repo(tmp_path, ["AISDLC_SDD_v0.14"])
    _write(os.path.join(repo, "AISDLC_SDD_v0.14", "build", "planning", "active", "RFC_N.md"),
           "# RFC N\n**前置基線**：v0.14 凍結\n（無狀態欄）\n")
    assert lint.missing_status(repo) == ["RFC_N.md"]   # advisory 命中
    assert lint.lint(repo) == []                       # 非硬違規


def test_proposed_status_clean_no_warn_no_fire(tmp_path):
    """標準『狀態：proposed』→ 既非已決（不 fire）亦非缺欄（不 warn）→ 全乾淨。"""
    repo = _mk_repo(tmp_path, ["AISDLC_SDD_v0.14"])
    _write(os.path.join(repo, "AISDLC_SDD_v0.14", "build", "planning", "active", "RFC_P2.md"),
           "# RFC P2\n**狀態**：proposed\n**前置基線**：v0.14\n")
    assert lint.lint(repo) == []
    assert lint.missing_status(repo) == []


def test_main_missing_status_warns_but_exits_zero(tmp_path, capsys):
    """CLI：僅缺欄（無已決滯留）→ 印 ::warning:: 但 exit 0（advisory 不阻擋硬閘）。"""
    repo = _mk_repo(tmp_path, ["AISDLC_SDD_v0.14"])
    _write(os.path.join(repo, "AISDLC_SDD_v0.14", "build", "planning", "active", "RFC_W.md"),
           "# RFC W\n（無狀態欄）\n")
    assert lint.main([repo]) == 0
    out = capsys.readouterr().out
    assert "::warning::" in out and "DEF-30-001" in out and "RFC_W.md" in out
