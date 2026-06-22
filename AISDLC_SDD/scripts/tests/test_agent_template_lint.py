"""agent_template_lint 意圖鎖（DEF-AGTREV-002 + DEF-AGTREV-005 盲區封閉）.

每個 case 編碼「為何此行為重要」（Rule 9）：本 lint 的價值＝讓「agent 定義檔引用一個
不存在 / 非根相對 / 裸檔名（非 docs_template/ 前綴）的 template」這件事被機械擋下。

緣由（v0.18 重審）：原 lint 的 TOK regex 只認帶 `docs_template/` 前綴的 token，使核心
agent 內 12 條短名 broken template_path（如 `user-story-template.md`）+ 19 條誤指
`docs/` 輸出區的 template + 3 條 dependencies.templates 短名長期假綠潛伏。DEF-AGTREV-005
封閉盲區後，本測試鎖死三類偵測：
  (1) docs_template/ 路徑存在 → 0；
  (2) docs_template/ 路徑不存在 → 非零（BROKEN）；
  (3) ../docs_template/（非根相對）→ 非零（NON-ROOT-RELATIVE）；
  (4) 裸檔名 template_path（非 docs_template/ 前綴）→ 非零（BARE-NAME，盲區封閉）；
  (5) dependencies.templates 裸檔名 → 非零（清單項盲區封閉）；
  (6) dependencies.templates 指向存在的 docs_template/ → 0；
  (7) 突變實證：clean → 把路徑改裸名即轉紅（抓退化）。
任一退化都會讓「broken template 假綠」死灰復燃。
"""
from __future__ import annotations

import os

from scripts import agent_template_lint as atl

_VER = "AISDLC_SDD_v0.18"


def _write_template(repo: str, rel: str) -> None:
    """在 <ver>/docs_template/ 下建一個存在的模板檔（pool 來源）。"""
    p = os.path.join(repo, _VER, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write("# template\n")


def _write_agent(repo: str, fname: str, body: str) -> None:
    """以原始 YAML 文字寫 agent（含引號，對齊真實 agent 格式使 BARE regex 生效）。"""
    base = os.path.join(repo, _VER, "agent", "core")
    os.makedirs(base, exist_ok=True)
    with open(os.path.join(base, fname), "w", encoding="utf-8") as f:
        f.write(body)


def _agent_with_template_path(value: str) -> str:
    return (
        "agent:\n"
        "  id: \"sa-analyst\"\n"
        "document_responsibilities:\n"
        "  primary_documents:\n"
        "    - document_type: \"FRD\"\n"
        f"      template_path: \"{value}\"\n"
    )


# ── (1) docs_template/ 路徑存在 → 0 ──────────────────────────────────────────

def test_existing_docs_template_passes(tmp_path):
    repo = str(tmp_path)
    _write_template(repo, "docs_template/core/frd/FRD_Universal_Template.md")
    _write_agent(repo, "04.sa-analyst-zh.yaml",
                 _agent_with_template_path("docs_template/core/frd/FRD_Universal_Template.md"))
    assert atl.main([repo]) == 0


# ── (2) docs_template/ 路徑不存在 → 非零 ──────────────────────────────────────

def test_missing_docs_template_fails(tmp_path):
    repo = str(tmp_path)
    _write_template(repo, "docs_template/core/frd/FRD_Universal_Template.md")  # 別的存在檔，確保 pool 非空
    _write_agent(repo, "04.sa-analyst-zh.yaml",
                 _agent_with_template_path("docs_template/core/frd/DOES_NOT_EXIST.md"))
    assert atl.main([repo]) == 1


# ── (3) ../docs_template/（非根相對）→ 非零 ───────────────────────────────────

def test_non_root_relative_fails(tmp_path):
    repo = str(tmp_path)
    _write_template(repo, "docs_template/core/frd/FRD_Universal_Template.md")
    _write_agent(repo, "04.sa-analyst-zh.yaml",
                 _agent_with_template_path("../docs_template/core/frd/FRD_Universal_Template.md"))
    assert atl.main([repo]) == 1


# ── (4) 裸檔名 template_path（盲區封閉）→ 非零 ────────────────────────────────

def test_bare_name_template_path_fails(tmp_path):
    """DEF-AGTREV-005：裸檔名（非 docs_template/ 前綴）原 TOK 看不到 → 必須被 BARE 抓出。"""
    repo = str(tmp_path)
    _write_template(repo, "docs_template/core/frd/FRD_Universal_Template.md")
    _write_agent(repo, "04.sa-analyst-zh.yaml",
                 _agent_with_template_path("user-story-template.md"))
    assert atl.main([repo]) == 1


# ── (5) dependencies.templates 裸檔名（清單項盲區）→ 非零 ─────────────────────

def test_dependencies_templates_bare_name_fails(tmp_path):
    repo = str(tmp_path)
    _write_template(repo, "docs_template/core/frd/FRD_Universal_Template.md")
    body = (
        "agent:\n  id: \"ba-business-analyst\"\n"
        "dependencies:\n"
        "  templates:\n"
        "    - stakeholder-validation-template.md\n"
    )
    _write_agent(repo, "02.ba-business-analyst-zh.yaml", body)
    assert atl.main([repo]) == 1


# ── (6) dependencies.templates 指向存在的 docs_template/ → 0 ──────────────────

def test_dependencies_templates_valid_passes(tmp_path):
    repo = str(tmp_path)
    _write_template(repo, "docs_template/support/Requirement_Extraction_Report_Template.md")
    body = (
        "agent:\n  id: \"ba-business-analyst\"\n"
        "dependencies:\n"
        "  templates:\n"
        "    - docs_template/support/Requirement_Extraction_Report_Template.md\n"
    )
    _write_agent(repo, "02.ba-business-analyst-zh.yaml", body)
    assert atl.main([repo]) == 0


# ── (4b) DEF-AGTREV-008：非 .md 副檔名（.yaml）誤指 docs/ 也須抓 ────────────────

def test_non_md_yaml_template_in_docs_fails(tmp_path):
    """sdd_skills 的 API CONTRACT template 為 .yaml；原 `\\.md` 規格漏抓誤指 docs/ 者。
    擴 _TMPL_EXT 後，指向非 docs_template/ 的 .yaml 必須非零。"""
    repo = str(tmp_path)
    _write_template(repo, "docs_template/sdd/api/CONTRACT-TEMPLATE.yaml")
    _write_agent(repo, "05.sd-architect-zh.yaml",
                 "agent:\n  id: \"sd-architect\"\n"
                 "sdd_skills:\n"
                 "  contract_first:\n"
                 "    template: \"docs/02_architecture/api/CONTRACT-TEMPLATE.yaml\"\n")
    assert atl.main([repo]) == 1


def test_valid_yaml_docs_template_passes(tmp_path):
    """指向存在的 docs_template/ .yaml → 0（確認擴副檔名後不誤殺合法 .yaml）。"""
    repo = str(tmp_path)
    _write_template(repo, "docs_template/sdd/api/CONTRACT-TEMPLATE.yaml")
    _write_agent(repo, "05.sd-architect-zh.yaml",
                 "agent:\n  id: \"sd-architect\"\n"
                 "sdd_skills:\n"
                 "  contract_first:\n"
                 "    template: \"docs_template/sdd/api/CONTRACT-TEMPLATE.yaml\"\n")
    assert atl.main([repo]) == 0


# ── (7) 突變實證：clean → 改裸名即轉紅 ────────────────────────────────────────

def test_clean_then_bare_name_detects_regression(tmp_path):
    repo = str(tmp_path)
    _write_template(repo, "docs_template/core/frd/FRD_Universal_Template.md")
    _write_agent(repo, "04.sa-analyst-zh.yaml",
                 _agent_with_template_path("docs_template/core/frd/FRD_Universal_Template.md"))
    assert atl.main([repo]) == 0
    # 突變：根相對改裸名 → 盲區若復活則仍 0；封閉後必須轉 1
    _write_agent(repo, "04.sa-analyst-zh.yaml",
                 _agent_with_template_path("frd-template.md"))
    assert atl.main([repo]) == 1
