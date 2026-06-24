"""Phase K M-K1 / ACT-081 — Intent Decomposer 測試套件.

涵蓋：分解（bullet/numbered/mixed）、有界（觸頂/clamp/env）、acyclic 守門（環/自環）、
underspecified 路徑（過模糊/成環/觸頂）、value_planner 介面、落盤。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime import intent_decomposer as ID
from tools.fsm_runtime import value_planner as VP


# ---------- 可分解（decomposed）----------

def test_decompose_bullet_list():
    dag = ID.decompose("- 下單流程\n- 折扣規則\n- 庫存扣減")
    assert dag.status == "decomposed"
    assert len(dag.nodes) == 3
    assert dag.node_ids() == ["N1", "N2", "N3"]


def test_decompose_numbered_list():
    dag = ID.decompose("1. 註冊\n2) 登入\n3. 重設密碼")
    assert dag.status == "decomposed"
    assert len(dag.nodes) == 3


def test_decompose_mixed_and_ignores_prose():
    text = "目標：做一個下單系統\n- 下單\n說明文字\n- 付款\n"
    dag = ID.decompose(text)
    assert dag.status == "decomposed"
    assert [n.title for n in dag.nodes] == ["下單", "付款"]


def test_decompose_node_count_matches_items():
    dag = ID.decompose("\n".join(f"- 需求{i}" for i in range(1, 11)))
    assert dag.status == "decomposed"
    assert len(dag.nodes) == 10


# ---------- 依賴（acyclic）----------

def test_explicit_deps_acyclic():
    dag = ID.decompose("- 基礎\n- 進階 [dep:1]\n- 整合 [dep:1,2]")
    assert dag.status == "decomposed"
    assert dag.nodes[1].depends_on == ["N1"]
    assert dag.nodes[2].depends_on == ["N1", "N2"]
    order = dag.topological_order()
    assert order.index("N1") < order.index("N2") < order.index("N3")


def test_dep_marker_stripped_from_title():
    dag = ID.decompose("- 基礎\n- 進階 [dep:1]")
    assert dag.nodes[1].title == "進階"


def test_out_of_range_dep_ignored():
    dag = ID.decompose("- 唯一 [dep:5]")
    assert dag.status == "decomposed"
    assert dag.nodes[0].depends_on == []


def test_is_acyclic_true():
    dag = ID.decompose("- a\n- b [dep:1]")
    assert dag.is_acyclic() is True


# ---------- 成環 → underspecified ----------

def test_cyclic_deps_underspecified():
    dag = ID.decompose("- a [dep:2]\n- b [dep:1]")
    assert dag.status == "underspecified"
    assert "cycle" in dag.reason.lower()


def test_self_dependency_is_cycle():
    dag = ID.decompose("- a [dep:1]")
    assert dag.status == "underspecified"
    assert "cycle" in dag.reason.lower()


def test_topological_order_raises_on_cycle():
    dag = ID.decompose("- a [dep:2]\n- b [dep:1]")
    with pytest.raises(ValueError):
        dag.topological_order()


# ---------- 過模糊 → underspecified ----------

def test_empty_text_underspecified():
    dag = ID.decompose("")
    assert dag.status == "underspecified"
    assert "vague" in dag.reason.lower()


def test_prose_only_underspecified():
    dag = ID.decompose("我想要一個很棒的系統，可以處理很多事情。")
    assert dag.status == "underspecified"


# ---------- 有界（觸頂 / clamp / env）----------

def test_exceeds_bound_underspecified():
    text = "\n".join(f"- 需求{i}" for i in range(1, 7))  # 6 items
    dag = ID.decompose(text, max_nodes=4)
    assert dag.status == "underspecified"
    assert "exceeds" in dag.reason.lower()


def test_clamp_below_min():
    assert ID.clamp_max_nodes(2) == ID.MIN_MAX_NODES


def test_clamp_above_max():
    assert ID.clamp_max_nodes(999) == ID.MAX_MAX_NODES


def test_max_nodes_clamped_in_decompose():
    dag = ID.decompose("- a\n- b\n- c", max_nodes=999)
    assert dag.max_nodes == ID.MAX_MAX_NODES


def test_env_override_max_nodes(monkeypatch):
    monkeypatch.setenv("SDD_INTENT_MAX_NODES", "4")
    text = "\n".join(f"- r{i}" for i in range(1, 6))  # 5 > 4
    dag = ID.decompose(text)  # max_nodes=None → env
    assert dag.max_nodes == 4
    assert dag.status == "underspecified"


# ---------- value_planner 介面（不自裁決）----------

def test_to_candidates_feeds_value_planner():
    dag = ID.decompose("- 高價值\n- 低價值")
    cands = dag.to_candidates()
    assert all(isinstance(c, VP.BacklogCandidate) for c in cands)
    ranked = VP.rank_candidates(cands)
    assert len(ranked) == 2


def test_candidates_are_cold_start():
    dag = ID.decompose("- x")
    assert dag.to_candidates()[0].cold_start is True


# ---------- 落盤 ----------

def test_write_spec_dag_creates_parseable_yaml(tmp_path):
    dag = ID.decompose("- a\n- b [dep:1]", intent_ref="intent.md")
    path = ID.write_spec_dag(dag, out_dir=tmp_path, today="2026-06-02")
    assert path.exists()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["status"] == "decomposed"
    assert data["intent_ref"] == "intent.md"
    assert len(data["nodes"]) == 2
    assert data["nodes"][1]["depends_on"] == ["N1"]


def test_write_underspecified_dag(tmp_path):
    dag = ID.decompose("", intent_ref="vague.md")
    path = ID.write_spec_dag(dag, out_dir=tmp_path, today="2026-06-02")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["status"] == "underspecified"
    assert data["nodes"] == []


# ---------- 20-fixture 聚合驗收（覆蓋率 ≥ 80% / 誤分解率 < 15%，ACT-081）----------
# 12 可分解意圖（應 decomposed）
DECOMPOSABLE = [
    "- 下單流程\n- 折扣規則\n- 庫存扣減",
    "1. 註冊\n2. 登入\n3. 重設密碼",
    "- 商品搜尋\n- 加入購物車\n- 結帳付款",
    "- 建立帳號\n- 驗證 Email [dep:1]\n- 啟用帳號 [dep:2]",
    "- 上傳檔案\n- 病毒掃描 [dep:1]\n- 儲存到雲端 [dep:2]",
    "- 訂單建立\n- 發送通知\n- 更新報表",
    "* 會員等級\n* 點數累積\n* 點數兌換 [dep:2]",
    "- 留言\n- 按讚\n- 分享",
    "1) 匯入資料\n2) 清洗資料 [dep:1]\n3) 產生報表 [dep:2]",
    "- 預約\n- 付訂金 [dep:1]\n- 確認預約 [dep:2]",
    "- 建立專案\n- 邀請成員 [dep:1]\n- 指派任務 [dep:2]",
    "- 設定鬧鐘\n- 響鈴\n- 貪睡",
]
# 8 模糊/成環意圖（應 underspecified）
UNDERSPECIFIED = [
    "",                                          # 空
    "我想要一個很棒的系統，可以處理很多事情。",     # 純散文
    "請幫我做一個完整的解決方案",                  # 純散文
    "希望能更好更快更強",                          # 純散文
    "- 折扣 [dep:2]\n- 庫存 [dep:1]",            # 2-環
    "- a [dep:1]",                               # 自環
    "- x [dep:2]\n- y [dep:3]\n- z [dep:1]",     # 3-環
    "目標是提升使用者體驗並增加營收",              # 純散文
]


def test_coverage_at_least_80pct():
    """可分解意圖被正確判為 decomposed 的覆蓋率 ≥ 80%。"""
    hits = sum(1 for t in DECOMPOSABLE if ID.decompose(t).status == "decomposed")
    assert hits / len(DECOMPOSABLE) >= 0.80


def test_misdecompose_rate_below_15pct():
    """全 20 fixture 分類錯誤率 < 15%（可分解誤判 underspecified、或模糊/成環誤判 decomposed）。"""
    wrong = 0
    for t in DECOMPOSABLE:
        if ID.decompose(t).status != "decomposed":
            wrong += 1
    for t in UNDERSPECIFIED:
        if ID.decompose(t).status != "underspecified":
            wrong += 1
    total = len(DECOMPOSABLE) + len(UNDERSPECIFIED)
    assert total >= 20
    assert wrong / total < 0.15


# ---------- intent-patterns 骨架載入（ACT-081，lazy / 不報錯）----------

def test_load_skeletons_missing_dir_returns_empty(tmp_path):
    assert ID.load_intent_skeletons(tmp_path / "nonexistent") == []


def test_load_skeletons_ignores_corrupt(tmp_path):
    (tmp_path / "INT-001.yaml").write_text("id: INT-001\nsignature: a | b\n", encoding="utf-8")
    (tmp_path / "INT-002.yaml").write_text(": : not yaml : :", encoding="utf-8")
    sk = ID.load_intent_skeletons(tmp_path)
    assert len(sk) == 1
    assert sk[0]["id"] == "INT-001"


def test_decompose_marks_skeleton_ref_on_hit():
    dag = ID.decompose("- 下單\n- 付款")
    skeletons = [{"id": "INT-005", "signature": dag.signature()}]
    hit = ID.decompose("- 下單\n- 付款", skeletons=skeletons)
    assert hit.skeleton_ref == "INT-005"


def test_decompose_no_skeleton_ref_without_hint():
    assert ID.decompose("- 下單\n- 付款").skeleton_ref == ""


# ---------- 結晶（≥3 次同型 → proposed INT-*.yaml，禁 verified）----------

def test_crystallize_below_threshold_no_write(tmp_path):
    dags = [ID.decompose("- 下單\n- 付款", intent_ref=f"i{i}") for i in range(2)]
    written = ID.crystallize_patterns(dags, out_dir=tmp_path)
    assert written == []


def test_crystallize_same_pattern_thrice_yields_proposed(tmp_path):
    dags = [ID.decompose("- 下單\n- 付款", intent_ref=f"intent-{i}.md") for i in range(3)]
    written = ID.crystallize_patterns(dags, out_dir=tmp_path)
    assert len(written) == 1
    doc = yaml.safe_load(written[0].read_text(encoding="utf-8"))
    assert doc["maturity"] == "proposed"      # 禁自動 verified
    assert doc["occurrences"] == 3
    assert doc["id"] == "INT-001"
    assert "signature" in doc


def test_crystallize_increments_and_no_overwrite(tmp_path):
    # 兩種不同型各 3 次 → 兩個 INT 草案，遞增不覆寫
    dags = [ID.decompose("- 下單\n- 付款", intent_ref=f"a{i}") for i in range(3)]
    dags += [ID.decompose("- 註冊\n- 登入\n- 登出", intent_ref=f"b{i}") for i in range(3)]
    written = ID.crystallize_patterns(dags, out_dir=tmp_path)
    assert len(written) == 2
    names = sorted(p.name for p in written)
    assert names == ["INT-001.yaml", "INT-002.yaml"]


def test_crystallize_skips_underspecified(tmp_path):
    dags = [ID.decompose("", intent_ref=f"vague{i}") for i in range(5)]
    assert ID.crystallize_patterns(dags, out_dir=tmp_path) == []
