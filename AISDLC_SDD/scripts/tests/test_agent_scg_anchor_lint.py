"""Agent 閘門錨點 ↔ SCG SSOT 一致性 lint 意圖鎖（AGT-03／AGT-04／AGT-05，R84）.

每個 case 編碼「為何此行為重要」（Rule 9）：本 lint 的價值＝讓「agent prompt 把某個
主題錨在錯的閘門上」這件事被機械擋下。立案事實是可量的——LATEST agent 樹曾有 16 個站點
把 RTM 的 AT 欄位錨在 ``SCG-4（測試計畫後）``，而 SCG SSOT 逐字寫著 SCG-4＝PR Review Gate、
SCG-5＝RTM Completeness Gate；同一個錯字串抄了 14 支檔，而 ci-gate 當時已跑的 3 支 agent
lint 全綠 ⇒ 結構上看不見它。

故覆蓋：
  (1) 正確錨點（RG-TEST 承載測試主題、SCG-5 承載 RTM）→ 0；
  (2) 重現 AGT-03 原缺陷：``SCG-4（測試計畫後）`` → 非零；
  (3) 反向錯錨：SCG-5 宣稱自己是 PR Review → 非零（判準不是只認一個方向）；
  (4) **判準自證**：標記表若與 SSOT 不符（SSOT 被改動而表沒跟上）→ 非零 fail-loud，
      不得靜默放行——否則這張表就是同一份知識的第三個家；
  (5) SSOT 閘門表解析不到 7 列 → 非零（判準的輸入不可信時寧可紅）；
  (6) 註解行豁免：訂正協議要求把被訂正的原文逐字保留，那些原文必然含舊錯錨 → 0；
  (7) 單一真相源引用指向不存在的檔 → 非零（引用一個不存在的家＝假話，且無其他東西會紅）；
  (8) agent.version 寫死版號 → 非零（AGT-05：27 支曾一起停在 v0.18，無人在守）；
      指向 SSOT → 0；
  (9) 突變實證：先綠，改壞即紅（同一個 repo 內前後對照，證明不是恆綠）。
任一退化都會讓「錯錨抄 N 份」與「version 全體過期」死灰復燃。
"""
from __future__ import annotations

import os

from scripts import agent_scg_anchor_lint as lint

_VER = "AISDLC_SDD_v0.30"

# SSOT 閘門表：與框架內 SDD_SPEC_FIRST_GATE.md 同形（本測試自帶，不依賴磁碟真檔）。
_SSOT_ROWS = [
    "| 🔷 SCG-0 | Requirement Spec Gate | 需求凍結前（PRD + FRD 完成） | sa-analyst |",
    "| 🔷 SCG-1 | Design Spec Gate | 設計凍結前（SRD + API Spec 完成） | sd-architect |",
    "| 🔷 SCG-2 | Architecture Spec Gate | 架構凍結前（C4 圖 + ADR 完成） | sd-architect |",
    "| 🔷 SCG-3 | API Contract Gate（Contract Freeze） | 開發啟動前 | sd-architect |",
    "| 🔷 SCG-4 | PR Review Gate | 實作 PR 審查（實作與規格一致性） | dev-senior |",
    "| 🔷 SCG-5 | RTM Completeness Gate | 交付前（RTM 100% 覆蓋） | qa-lead |",
    "| 🔷 SCG-6 | Release Gate | 發布前（所有閘門通過確認） | all |",
]

_VERSION_OK = '  version: "see FRAMEWORK_STATUS.md（框架 LATEST）"'


def _mk_repo(tmp_path, ssot_rows=None, rg_table=True) -> str:
    repo = str(tmp_path)
    ver = os.path.join(repo, _VER)
    gate_dir = os.path.join(ver, "workflow", "sdd-spec-first-gate")
    os.makedirs(gate_dir, exist_ok=True)
    rows = _SSOT_ROWS if ssot_rows is None else ssot_rows
    with open(os.path.join(gate_dir, "SDD_SPEC_FIRST_GATE.md"), "w", encoding="utf-8") as f:
        f.write("# gate\n\n| 閘門 | 名稱 | 觸發條件 | 主責 Agent |\n|--|--|--|--|\n"
                + "\n".join(rows) + "\n")
    if rg_table:
        guide_dir = os.path.join(ver, "guides", "system", "sdd")
        os.makedirs(guide_dir, exist_ok=True)
        with open(os.path.join(guide_dir, "SDD_GUIDE.md"), "w", encoding="utf-8") as f:
            f.write("| 代碼 | 補充閘門 | 觸發時機 |\n|--|--|--|\n"
                    "| RG-TEST | Test Strategy Gate | SCG-3 後，測試開始前 |\n")
    os.makedirs(os.path.join(ver, "agent", "core"), exist_ok=True)
    return repo


def _write_agent(repo: str, body: str, fname: str = "07.qa-tester-zh.yaml") -> str:
    fp = os.path.join(repo, _VER, "agent", "core", fname)
    with open(fp, "w", encoding="utf-8") as f:
        f.write("agent:\n  id: \"qa-tester\"\n" + _VERSION_OK + "\n" + body)
    return fp


# ── (1) 正確錨點 → 0 ────────────────────────────────────────────────────────

def test_correct_anchors_pass(tmp_path):
    repo = _mk_repo(tmp_path)
    _write_agent(repo, '  trigger: "RG-TEST（測試策略閘門後）填入；SCG-5（RTM Completeness Gate）前 100%"\n')
    assert lint.main([repo]) == 0


# ── (2) 重現 AGT-03 原缺陷 → 非零 ───────────────────────────────────────────

def test_agt03_original_defect_is_caught(tmp_path):
    """SCG-4 是 PR Review Gate；把測試計畫掛上去會讓 SCG-5 的把關者拿不到覆蓋依據。"""
    repo = _mk_repo(tmp_path)
    _write_agent(repo, '  trigger: "SCG-0（FRD 後）、SCG-1（SRD 後）、SCG-4（測試計畫後）、需求變更後"\n')
    assert lint.main([repo]) == 1


# ── (3) 反向錯錨 → 非零（判準不是只認一個方向）──────────────────────────────

def test_reverse_misanchor_is_caught(tmp_path):
    repo = _mk_repo(tmp_path)
    _write_agent(repo, '  spec_gate: "SCG-5 PR Review 一致性審查"\n')
    assert lint.main([repo]) == 1


# ── (4) 判準自證：SSOT 變動而標記表沒跟上 → fail-loud ───────────────────────

def test_topic_map_must_be_ssot_derived(tmp_path):
    """把 SSOT 的 SCG-4/SCG-5 名稱互換：表若不自證，這種情況會靜默放行錯錨。"""
    swapped = list(_SSOT_ROWS)
    swapped[4] = "| 🔷 SCG-4 | RTM Completeness Gate | 交付前 | qa-lead |"
    swapped[5] = "| 🔷 SCG-5 | PR Review Gate | 實作 PR 審查 | dev-senior |"
    repo = _mk_repo(tmp_path, ssot_rows=swapped)
    _write_agent(repo, '  note: "無錨點"\n')
    assert lint.main([repo]) == 1


def test_rg_owned_marker_must_be_absent_from_scg_table(tmp_path):
    """若哪天 SCG 表真的收了「測試計畫」，本 lint 必須紅（表與 SSOT 對不上）而非繼續判紅 agent。"""
    hijacked = list(_SSOT_ROWS)
    hijacked[4] = "| 🔷 SCG-4 | Test Plan Gate | 測試計畫完成後 | qa-lead |"
    repo = _mk_repo(tmp_path, ssot_rows=hijacked)
    _write_agent(repo, '  note: "無錨點"\n')
    assert lint.main([repo]) == 1


# ── (5) SSOT 解析不到 7 列 → 非零 ───────────────────────────────────────────

def test_unparseable_ssot_fails_loud(tmp_path):
    repo = _mk_repo(tmp_path, ssot_rows=_SSOT_ROWS[:3])
    _write_agent(repo, '  note: "無錨點"\n')
    assert lint.main([repo]) == 1


# ── (6) 註解行豁免（訂正協議要求保留原文）→ 0 ───────────────────────────────

def test_comment_lines_are_exempt(tmp_path):
    repo = _mk_repo(tmp_path)
    _write_agent(repo, '  # 原文逐字保留：SCG-4（測試計畫後）填入\n  trigger: "RG-TEST 後填入"\n')
    assert lint.main([repo]) == 0


# ── (7) 單一真相源引用不存在 → 非零 ─────────────────────────────────────────

def test_dangling_single_home_reference_is_caught(tmp_path):
    repo = _mk_repo(tmp_path)
    _write_agent(repo, '  evidence_discipline:\n    inherits_from: "agent/NOPE.md"\n')
    assert lint.main([repo]) == 1


def test_existing_single_home_reference_passes(tmp_path):
    repo = _mk_repo(tmp_path)
    home = os.path.join(repo, _VER, "agent", "EVIDENCE_DISCIPLINE.md")
    with open(home, "w", encoding="utf-8") as f:
        f.write("# home\n")
    _write_agent(repo, '  evidence_discipline:\n    inherits_from: "agent/EVIDENCE_DISCIPLINE.md"\n')
    assert lint.main([repo]) == 0


# ── (8) version 欄 ─────────────────────────────────────────────────────────

def test_hardcoded_version_is_caught(tmp_path):
    """AGT-05：27 支 agent 在框架走到 v0.30 時全部還寫 v0.18，且無 lint 在守。"""
    repo = _mk_repo(tmp_path)
    fp = os.path.join(repo, _VER, "agent", "core", "07.qa-tester-zh.yaml")
    with open(fp, "w", encoding="utf-8") as f:
        f.write('agent:\n  id: "qa-tester"\n  version: "v0.18"\n  note: "x"\n')
    assert lint.main([repo]) == 1


# ── (9) 突變實證：同一 repo 前後對照，證明不是恆綠 ──────────────────────────

def test_mutation_flips_green_to_red(tmp_path):
    repo = _mk_repo(tmp_path)
    fp = _write_agent(repo, '  trigger: "RG-TEST（測試策略閘門後）填入"\n')
    assert lint.main([repo]) == 0
    with open(fp, encoding="utf-8") as f:
        s = f.read()
    with open(fp, "w", encoding="utf-8") as f:
        f.write(s.replace("RG-TEST（測試策略閘門後）", "SCG-4（測試計畫後）"))
    assert lint.main([repo]) == 1
