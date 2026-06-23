"""Phase K M-K2 / ACT-083 — Spec Debate Engine 測試套件.

24 fixture（12 雙詮釋互斥 AC + 12 真清晰 AC）：偵出率 ≥ 80%、誤報率 < 15%；
有界（clamp/env）、強度凍結（profile version）、隔離詮釋分離。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime import spec_debate as SD


# 12 含雙讀標記的歧義 AC（verdict 應為 divergence）
AMBIGUOUS = [
    "折扣可疊加套用於同一筆訂單",
    "登入失敗時寄送通知和/或鎖定帳號",
    "報表欄位包含姓名、電話等等",
    "系統酌情清除過期快取",
    "視情況啟用雙因素驗證",
    "必要時重試付款請求",
    "盡可能壓縮上傳的圖片",
    "若有需要提供電子發票",
    "Send email and/or SMS on alert",
    "The discount field is optionally applied",
    "Cache is purged as appropriate",
    "Retry the failed request as needed",
]

# 12 無標記的清晰 AC（verdict 應為 consensus）
CLEAR = [
    "使用者連續輸入錯誤密碼 3 次後，帳號鎖定 15 分鐘",
    "訂單金額超過 1000 元時免運費",
    "API 回應時間 P95 必須低於 200 毫秒",
    "每位使用者最多綁定 5 張信用卡",
    "密碼長度至少 8 個字元",
    "上傳檔案大小上限為 10 MB",
    "工作階段閒置 30 分鐘後自動登出",
    "每日報表於 UTC 02:00 產生",
    "The cart holds at most 50 items",
    "User session expires after 24 hours",
    "Refund must complete within 7 days",
    "Each account has exactly one primary email",
]


# ---------- 逐筆驗證 ----------

@pytest.mark.parametrize("ac", AMBIGUOUS)
def test_ambiguous_yields_divergence(ac):
    res = SD.debate(ac)
    assert res.verdict == "divergence"
    assert res.divergence >= SD.DIVERGENCE_THRESHOLD


@pytest.mark.parametrize("ac", CLEAR)
def test_clear_yields_consensus(ac):
    res = SD.debate(ac)
    assert res.verdict == "consensus"
    assert res.divergence == 0.0


# ---------- 聚合驗收（偵出率 / 誤報率）----------

def test_detection_rate_at_least_80pct():
    hits = sum(1 for ac in AMBIGUOUS if SD.debate(ac).verdict == "divergence")
    assert hits / len(AMBIGUOUS) >= 0.80


def test_false_positive_rate_below_15pct():
    fp = sum(1 for ac in CLEAR if SD.debate(ac).verdict == "divergence")
    assert fp / len(CLEAR) < 0.15


# ---------- 隔離詮釋分離 ----------

def test_isolated_interpreters_differ_for_ambiguous():
    res = SD.debate("折扣可疊加")
    assert res.interp_pro != res.interp_con


def test_isolated_interpreters_same_for_clear():
    res = SD.debate("密碼長度至少 8 個字元")
    assert res.interp_pro == res.interp_con == "密碼長度至少 8 個字元"


def test_markers_populated_for_ambiguous():
    assert "可疊加" in SD.debate("折扣可疊加").markers


def test_markers_empty_for_clear():
    assert SD.debate("API 回應時間低於 200 毫秒").markers == []


def test_multiple_markers_raise_divergence():
    single = SD.debate("系統酌情清除快取").divergence
    multi = SD.debate("系統酌情清除快取，必要時重試").divergence
    assert multi > single


# ---------- 有界 / 凍結 ----------

def test_clamp_rounds_below_min():
    assert SD.clamp_rounds(0) == SD.MIN_ROUNDS


def test_clamp_rounds_above_max():
    assert SD.clamp_rounds(99) == SD.MAX_ROUNDS


def test_default_rounds_when_none(monkeypatch):
    monkeypatch.delenv("SDD_SPEC_DEBATE_ROUNDS", raising=False)
    assert SD.clamp_rounds(None) == SD.DEFAULT_ROUNDS


def test_env_override_rounds(monkeypatch):
    monkeypatch.setenv("SDD_SPEC_DEBATE_ROUNDS", "7")
    assert SD.debate("折扣可疊加").rounds == 7


def test_profile_version_frozen_default():
    assert SD.debate("折扣可疊加").profile_version == SD.SPEC_DEBATE_PROFILE_VERSION


def test_ac_id_passthrough():
    assert SD.debate("折扣可疊加", ac_id="AC-014").ac_id == "AC-014"


# ---------- 歧義對落盤（DIS-*.yaml，advisory / proposed / acyclic 不覆寫）----------

def test_persist_disambiguation_writes_proposed_yaml(tmp_path):
    res = SD.debate("折扣可疊加", ac_id="AC-014")
    path = SD.persist_disambiguation(
        res.ac_id, res.interp_pro, res.interp_con, res.divergence,
        markers=res.markers, out_dir=tmp_path,
    )
    assert path.exists()
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert doc["maturity"] == "proposed"          # 禁自動 verified
    assert doc["ac_id"] == "AC-014"
    assert doc["verdict"] is None                 # 待人工裁決（Rule 9.23.4）
    assert doc["interp_a"] != doc["interp_b"]     # 兩隔離詮釋互斥
    assert doc["id"] == "DIS-001"


def test_persist_disambiguation_acyclic_no_overwrite(tmp_path):
    res = SD.debate("折扣可疊加", ac_id="AC-014")
    p1 = SD.persist_disambiguation(res.ac_id, res.interp_pro, res.interp_con,
                                   res.divergence, out_dir=tmp_path)
    p2 = SD.persist_disambiguation(res.ac_id, res.interp_pro, res.interp_con,
                                   res.divergence, out_dir=tmp_path)
    assert p1 != p2                               # 不覆寫，遞增取新號
    assert p1.name == "DIS-001.yaml" and p2.name == "DIS-002.yaml"
    assert len(list(tmp_path.glob("DIS-*.yaml"))) == 2


def test_persist_from_result_adapter(tmp_path):
    res = SD.debate("登入失敗時寄送通知和/或鎖定帳號", ac_id="AC-020")
    path = SD.persist_from_result(res, out_dir=tmp_path)
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert doc["ac_id"] == "AC-020"
    assert doc["maturity"] == "proposed"
    assert doc["markers"]                          # 含命中標記
