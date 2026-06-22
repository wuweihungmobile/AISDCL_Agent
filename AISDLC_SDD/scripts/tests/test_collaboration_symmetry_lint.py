"""核心 agent collaboration_rules 對稱性 lint 意圖鎖（DEF-AGTREV-004）.

每個 case 編碼「為何此行為重要」（Rule 9）：本 lint 的價值＝讓「collaboration 有向圖
被人工宣告成單向斷鏈（downstream X→Y 漏對側 upstream←X、peer 單向）」這件事被機械擋下
——DEF-AGTREV-003 只手修一處，同類斷鏈仍潛伏。故覆蓋：
  (1) 對稱圖 → 0；
  (2) downstream 單向（漏對側 upstream）→ 非零；
  (3) peer 單向 → 非零；
  (4) 外部角色（Stakeholders/Business）為 downstream 來源不要求對側 → 仍 0（不誤報）；
  (5) template 示例檔（01.agent-template）即使單向也排除 → 仍 0；
  (6) peer 自環（self~self）不要求對側 → 仍 0。
任一退化都會讓「單向斷鏈」死灰復燃。

另含 DEF-AGTREV-006 presence 檢查（find_missing_collaboration_rules）：persona-schema
agent（具 persona 區塊）必須有 collaboration_rules；runtime agent（無 persona）豁免。
"""
from __future__ import annotations

import os

import yaml

from scripts import collaboration_symmetry_lint as csl


def _write_agent(repo: str, ver: str, fname: str, agent_id: str, rules: dict) -> None:
    """寫一個最小核心 agent yaml（agent.id + collaboration_rules）。"""
    base = os.path.join(repo, ver, "agent", "core")
    os.makedirs(base, exist_ok=True)
    doc = {"agent": {"id": agent_id}, "collaboration_rules": rules}
    with open(os.path.join(base, fname), "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True)


def _down(*types: str) -> list[dict]:
    return [{"agent_type": t} for t in types]


# 一組「對稱」的最小三 agent 圖：SA→SD（down），SD←SA（up），SA~SD peer 雙向。
def _make_symmetric(repo: str, ver: str = "AISDLC_SDD_v0.18") -> None:
    _write_agent(repo, ver, "04.sa-analyst-zh.yaml", "sa-analyst", {
        "downstream_collaboration": _down("SD"),
        "peer_collaboration": _down("SD"),
    })
    _write_agent(repo, ver, "05.sd-architect-zh.yaml", "sd-architect", {
        "upstream_collaboration": _down("SA"),
        "peer_collaboration": _down("SA"),
    })


# ── (1) 對稱圖 → 0 ───────────────────────────────────────────────────────────

def test_symmetric_graph_passes(tmp_path):
    repo = str(tmp_path)
    _make_symmetric(repo)
    assert csl.main([repo]) == 0


# ── (2) downstream 單向（漏對側 upstream）→ 非零 ──────────────────────────────

def test_downstream_without_upstream_fails(tmp_path):
    """SA downstream→SD 但 SD upstream 未列 SA → 斷鏈，必須非零。"""
    repo = str(tmp_path)
    ver = "AISDLC_SDD_v0.18"
    _write_agent(repo, ver, "04.sa-analyst-zh.yaml", "sa-analyst", {
        "downstream_collaboration": _down("SD"),
    })
    _write_agent(repo, ver, "05.sd-architect-zh.yaml", "sd-architect", {
        "upstream_collaboration": [],  # 漏 SA
    })
    assert csl.main([repo]) == 1


# ── (3) peer 單向 → 非零 ──────────────────────────────────────────────────────

def test_peer_one_way_fails(tmp_path):
    """SA peer~SD 但 SD peer 未列 SA → peer 應雙向，必須非零。"""
    repo = str(tmp_path)
    ver = "AISDLC_SDD_v0.18"
    _write_agent(repo, ver, "04.sa-analyst-zh.yaml", "sa-analyst", {
        "peer_collaboration": _down("SD"),
    })
    _write_agent(repo, ver, "05.sd-architect-zh.yaml", "sd-architect", {
        "peer_collaboration": [],  # 漏 SA
    })
    assert csl.main([repo]) == 1


# ── (4) 外部角色 downstream 來源不要求對側 → 0（不誤報）────────────────────────

def test_external_role_upstream_not_required(tmp_path):
    """PM/PO upstream 列 Stakeholders/Business（外部，無對應 agent 檔）→ 不要求對側，仍 0。"""
    repo = str(tmp_path)
    ver = "AISDLC_SDD_v0.18"
    _write_agent(repo, ver, "03.pm-po-agent-zh.yaml", "pm-po", {
        "upstream_collaboration": _down("Stakeholders/Business"),
    })
    assert csl.main([repo]) == 0


# ── (5) template 示例檔排除 → 0 ───────────────────────────────────────────────

def test_template_file_excluded(tmp_path):
    """01.agent-template 即使宣告單向 downstream 也排除（非真實 agent），仍 0。"""
    repo = str(tmp_path)
    ver = "AISDLC_SDD_v0.18"
    _write_agent(repo, ver, "01.agent-template-zh.yaml", "agent-template", {
        "downstream_collaboration": _down("SD"),  # 單向但屬 template，須排除
    })
    # 另放一個自洽 agent 確保圖非空
    _write_agent(repo, ver, "05.sd-architect-zh.yaml", "sd-architect", {})
    assert csl.main([repo]) == 0


# ── (6) peer 自環不要求對側 → 0 ──────────────────────────────────────────────

def test_peer_self_loop_allowed(tmp_path):
    """Dev peer~Dev（自環，知識分享）不要求對側，仍 0。"""
    repo = str(tmp_path)
    ver = "AISDLC_SDD_v0.18"
    _write_agent(repo, ver, "06.dev-developer-zh.yaml", "dev-developer", {
        "peer_collaboration": _down("Dev"),
    })
    assert csl.main([repo]) == 0


# ── (7) 突變實證：對稱圖刪掉對側 upstream 即轉紅（抓退化）─────────────────────

def test_symmetric_then_break_detects_regression(tmp_path):
    """先對稱（0），再把 SD upstream 改空（拿掉對側）→ 立刻非零。確保 lint 真能抓斷鏈。"""
    repo = str(tmp_path)
    ver = "AISDLC_SDD_v0.18"
    _make_symmetric(repo)
    assert csl.main([repo]) == 0
    # 突變：SD upstream 拿掉 SA（保留 peer），downstream SA→SD 變單向
    _write_agent(repo, ver, "05.sd-architect-zh.yaml", "sd-architect", {
        "upstream_collaboration": [],
        "peer_collaboration": _down("SA"),
    })
    assert csl.main([repo]) == 1


# ── (8) DEF-AGTREV-006：persona-schema 缺 collaboration_rules → 非零 ───────────

def _write_specialized(repo: str, fname: str, doc: dict, ver: str = "AISDLC_SDD_v0.18") -> None:
    base = os.path.join(repo, ver, "agent", "specialized")
    os.makedirs(base, exist_ok=True)
    with open(os.path.join(base, fname), "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True)


def test_persona_agent_missing_collaboration_rules_fails(tmp_path):
    """具 persona 區塊的 specialized agent 缺 collaboration_rules → presence 檢查必須非零。"""
    repo = str(tmp_path)
    _make_symmetric(repo)  # 先放一組對稱核心圖（symmetry 部分通過）
    _write_specialized(repo, "qa-web-tester-zh.yaml", {
        "agent": {"id": "qa-web-tester"},
        "persona": {"role": "Web QA"},  # 有 persona 但無 collaboration_rules
    })
    assert csl.main([repo]) == 1


def test_persona_agent_with_collaboration_rules_passes(tmp_path):
    """具 persona 且有非空 collaboration_rules → 通過。"""
    repo = str(tmp_path)
    _make_symmetric(repo)
    _write_specialized(repo, "qa-web-tester-zh.yaml", {
        "agent": {"id": "qa-web-tester"},
        "persona": {"role": "Web QA"},
        "collaboration_rules": {"upstream_collaboration": [{"agent_type": "QA-Lead"}]},
    })
    assert csl.main([repo]) == 0


def test_runtime_agent_without_persona_exempt(tmp_path):
    """runtime agent（無 persona）即使無 collaboration_rules 也豁免 → 仍 0。"""
    repo = str(tmp_path)
    _make_symmetric(repo)
    _write_specialized(repo, "sdd-orchestrator-zh.yaml", {
        "agent": {"id": "sdd-orchestrator"},
        "responsibilities": ["orchestrate"],  # runtime-schema，無 persona
    })
    assert csl.main([repo]) == 0


# ── (9) DEF-AGTREV-014：upstream 反向斷鏈（對方完全不承認）→ 非零 ──────────────

def test_upstream_without_any_reciprocal_fails(tmp_path):
    """BA upstream←PM/PO 但 PM/PO 既未 downstream→BA 亦未 peer~BA → 真實斷鏈，必須非零。

    （前 lint 只查 down→up 與 peer~peer，漏此 upstream 反向；DEF-AGTREV-014 補盲區。）
    """
    repo = str(tmp_path)
    ver = "AISDLC_SDD_v0.18"
    _write_agent(repo, ver, "02.ba-business-analyst-zh.yaml", "ba-business-analyst", {
        "upstream_collaboration": _down("PM/PO"),  # BA 視 PM/PO 為上游
    })
    _write_agent(repo, ver, "03.pm-po-agent-zh.yaml", "pm-po", {
        "downstream_collaboration": _down("SA"),  # 完全不提 BA
        "peer_collaboration": _down("SD"),
    })
    assert csl.main([repo]) == 1


def test_upstream_satisfied_by_peer_perspective_passes(tmp_path):
    """SD upstream←PM/PO 但 PM/PO 以 peer~SD 承認（視角不對稱非斷鏈）→ 接受，仍 0。

    刻意設計：upstream vs peer 的協作視角差不誤判，避免強制統一階層引發連鎖改寫。
    """
    repo = str(tmp_path)
    ver = "AISDLC_SDD_v0.18"
    _write_agent(repo, ver, "05.sd-architect-zh.yaml", "sd-architect", {
        "upstream_collaboration": _down("PM/PO"),  # SD 視 PM/PO 為上游
        "peer_collaboration": _down("PM/PO"),       # 同時 peer（與 PM/PO 對稱）
    })
    _write_agent(repo, ver, "03.pm-po-agent-zh.yaml", "pm-po", {
        "peer_collaboration": _down("SD"),  # PM/PO 以 peer 承認 SD（非 downstream）
    })
    assert csl.main([repo]) == 0
