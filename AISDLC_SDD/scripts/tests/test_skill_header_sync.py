"""Skill 版本戳記 SSOT 守新鮮意圖鎖（DEF-CLDREV-007）。

每個 case 編碼「為何此行為重要」（Rule 9）：此 lint 的價值＝把「每輪 Copy-on-Evolve
人工漏改 skill 版本戳」這項系統性摩擦，從流程轉為機械強制——故必須

  (1) 偵測到 stale 戳記（footer / README 套件版）並能 --write 修正（正例 → fire）；
  (2) 修正時**保留後綴語意**（如「（SDD 專屬 Skill）」），不可整段吃掉；
  (3) **絕不誤改** provenance（規則出生版本）、歷史事實、模板佔位版本（負例 → 不得 fire），
      否則會破壞 SLV 規則出處或文件史實，開發者就會關掉它；
  (4) 只校 LATEST，凍結基線（戳記本就對齊自身目錄）pass，不被重寫。
"""
from __future__ import annotations

import os

from scripts import skill_header_sync as sync


def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _mk_skill(repo: str, version: str, name: str, footer: str) -> str:
    p = os.path.join(repo, version, ".claude", "skills", name, "SKILL.md")
    _write(p, f"---\nname: {name}\n---\n# {name}\n\n{footer}\n")
    return p


# ── 偵測 + 修正（正例，須 fire）────────────────────────────────────────────────

def test_stale_footer_detected_and_fixed(tmp_path):
    """LATEST 內 footer 寫死舊版 → check fire；write 後 check pass。

    為何重要：這正是 DEF-CLDREV-007 本體（v0.19 內 42 footer 仍寫 v0.01）的機械再現。
    """
    repo = str(tmp_path)
    _mk_skill(repo, "AISDLC_SDD_v0.19", "qa-testing", "**基於**: AISDLC-SDD v0.01")
    assert sync.check(repo) == 1
    assert sync.write(repo) == 0
    assert sync.check(repo) == 0
    p = os.path.join(repo, "AISDLC_SDD_v0.19", ".claude", "skills", "qa-testing", "SKILL.md")
    assert "**基於**: AISDLC-SDD v0.19" in open(p, encoding="utf-8").read()


def test_suffix_preserved_on_rewrite(tmp_path):
    """重寫只換 version token，後綴「（SDD 專屬 Skill）」原樣保留。

    為何重要：後綴承載語意（Phase/出處），整段吃掉＝資訊遺失。
    """
    repo = str(tmp_path)
    _mk_skill(repo, "AISDLC_SDD_v0.19", "adr-generate",
              "**基於**: AISDLC-SDD v0.01（SDD 專屬 Skill）")
    sync.write(repo)
    txt = open(os.path.join(repo, "AISDLC_SDD_v0.19", ".claude", "skills",
                            "adr-generate", "SKILL.md"), encoding="utf-8").read()
    assert "**基於**: AISDLC-SDD v0.19（SDD 專屬 Skill）" in txt


def test_readme_collection_version_synced(tmp_path):
    """README `**版本**: v0.02-SDD` 套件版戳也納管，同步至 LATEST 並保 -SDD 後綴。"""
    repo = str(tmp_path)
    p = os.path.join(repo, "AISDLC_SDD_v0.19", ".claude", "skills", "README.md")
    _write(p, "# Skills\n\n**版本**: v0.02-SDD\n")
    assert sync.check(repo) == 1
    sync.write(repo)
    assert "**版本**: v0.19-SDD" in open(p, encoding="utf-8").read()


# ── 不得誤改（負例，防傷及無辜）──────────────────────────────────────────────

def test_provenance_not_touched():
    """SLV 規則 provenance `source: builtin (AISDLC-SDD v0.01 ...)` 是出生版本，須保留。"""
    line = 'source: "builtin (AISDLC-SDD v0.01 Phase A)"'
    assert sync._stale_lines(line, "v0.19") == []


def test_historical_fact_not_touched():
    """歷史事實『6個，AISDLC-SDD v0.01 新增』非版本戳，須保留。"""
    line = "│── # ★ SDD 專屬家族 (6個，AISDLC-SDD v0.01 新增)"
    assert sync._stale_lines(line, "v0.19") == []


def test_template_placeholder_version_not_touched():
    """模板佔位版本 `**版本**: {N}.{N}` / `1.0` 是輸出文件版本，非框架版本，須保留。"""
    assert sync._stale_lines("**版本**: {N}.{N}", "v0.19") == []
    assert sync._stale_lines("**版本**: 1.0", "v0.19") == []


# ── 只校 LATEST（邊界）────────────────────────────────────────────────────────

def test_frozen_baseline_aligned_passes(tmp_path):
    """凍結基線 footer 對齊自身目錄（v0.01→v0.01），但 lint 只校 LATEST → 整體 pass。

    為何重要：杜絕 lint 去重寫凍結本體（違反 Copy-on-Evolve），且舊版對齊自身即合法。
    """
    repo = str(tmp_path)
    _mk_skill(repo, "AISDLC_SDD_v0.01", "qa-testing", "**基於**: AISDLC-SDD v0.01")
    _mk_skill(repo, "AISDLC_SDD_v0.19", "qa-testing", "**基於**: AISDLC-SDD v0.19")
    assert sync.check(repo) == 0
    # write 不得改動凍結基線那行
    sync.write(repo)
    frozen = open(os.path.join(repo, "AISDLC_SDD_v0.01", ".claude", "skills",
                              "qa-testing", "SKILL.md"), encoding="utf-8").read()
    assert "**基於**: AISDLC-SDD v0.01" in frozen


def test_version_token_extraction():
    """目錄名 → 戳記 token。"""
    assert sync._version_token("AISDLC_SDD_v0.19") == "v0.19"
    assert sync._version_token("AISDLC_SDD_v1.00") == "v1.00"
    assert sync._version_token("garbage") is None
