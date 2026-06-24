"""DEF-02-002（v0.04 修正）— tlc_runner 計數解析單元測試（純字串，不需 Java/TLC 實跑）。

驗證意圖（WHY）：
  舊版 `_grp` 用 `re.search` 取**首個**匹配，會抓到 TLC 執行中途的 progress 行而非
  最終 summary，致 raw 計數不可靠且出現 `distinct(855) > generated(706)`（違反 TLC
  「窮舉先生成後去重 ⟹ generated >= distinct」恆等不變量）。v0.04 改取 last-match +
  fail-closed 斷言。本測試鎖定：
    (1) 取最終 summary（非首個 progress 行）；
    (2) 正常 summary（generated >= distinct）不誤報；
    (3) 畸形（generated < distinct）必 raise（不變量守護）；
    (4) 無匹配回 0、不 raise（META/FLEET 等小模型邊界容忍）。
"""
from __future__ import annotations

import pytest

from tools.fsm_runtime.tlc_runner import parse_tlc_summary


def test_takes_final_summary_not_first_progress_line():
    """WHY：DEF-02-002 根因＝抓到中途 progress 行。last-match 必須取最終 summary。"""
    out = (
        "Progress(10): 706 states generated, 400 distinct states found\n"
        "Progress(14): 850 states generated, 700 distinct states found\n"
        "Model checking completed. No error has been found.\n"
        "900 states generated, 855 distinct states found, 0 states left on queue.\n"
        "The depth of the complete state graph search is 15.\n"
    )
    res = parse_tlc_summary(out)
    assert res["generated"] == 900   # 非首個 progress 的 706
    assert res["distinct"] == 855
    assert res["depth"] == 15


def test_normal_summary_does_not_raise():
    """WHY：正常 generated >= distinct 不得誤報。"""
    out = "855 states generated, 706 distinct states found, 0 states left on queue.\n"
    res = parse_tlc_summary(out)
    assert res["generated"] == 855
    assert res["distinct"] == 706


def test_malformed_generated_lt_distinct_raises():
    """WHY：generated < distinct 違反 TLC 恆等不變量 → fail-closed raise（攻防：守護不變量）。"""
    out = "706 states generated, 855 distinct states found, 0 states left on queue.\n"
    with pytest.raises(RuntimeError, match="DEF-02-002"):
        parse_tlc_summary(out)


def test_no_match_returns_zero_without_raise():
    """WHY：無計數輸出（環境錯誤/空輸出）回 0 且不 raise，避免邊界誤殺。"""
    res = parse_tlc_summary("java not found\n")
    assert res == {"distinct": 0, "generated": 0, "depth": 0}
