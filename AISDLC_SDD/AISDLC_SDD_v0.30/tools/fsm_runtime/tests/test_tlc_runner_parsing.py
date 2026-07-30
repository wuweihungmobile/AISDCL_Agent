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


# ---------------------------------------------------------------------------
# R65 ADR-XPLAT-002 §5 Phase 2-A／§8 item 4 — --tla-version／--install-only
# argparse 回歸鎖
# ---------------------------------------------------------------------------
#
# WHY：main() 新增的 `--tla-version`（覆寫 download_jar 版本，`args.tla_version or
# DEFAULT_TLA_VERSION` 决定實際流入值）與既有 `--install-only`（僅下載 jar 後退出、
# 不跑 TLC）目前只靠本輪人工實測佐證，argparse 行為若被改壞（例如
# `args.tla_version or DEFAULT_TLA_VERSION` 誤植成恆回傳 DEFAULT_TLA_VERSION、或
# `--install-only` 遺失 `action="store_true"`）不會有任何測試轉紅。以下三個測試
# monkeypatch find_java／jar_path／download_jar，隔絕真實 java/網路依賴，只鎖
# argparse → main() 內部流向的行為。


def _capturing_download_jar(calls: list[str], tmp_path):
    """回傳一個記錄呼叫版本、不真的下載的 download_jar 替身。"""
    def _fake(version):
        calls.append(version)
        return tmp_path / "tla2tools.jar"
    return _fake


def test_default_tla_version_flows_to_download_jar(monkeypatch, tmp_path):
    """不帶 --tla-version 時，流入 download_jar() 的版本字串＝DEFAULT_TLA_VERSION。"""
    from tools.fsm_runtime import tlc_runner as T

    calls: list[str] = []
    monkeypatch.setattr(T, "find_java", lambda: "java")
    monkeypatch.setattr(T, "jar_path", lambda: tmp_path / "tla2tools.jar")
    monkeypatch.setattr(T, "download_jar", _capturing_download_jar(calls, tmp_path))

    rc = T.main(["tlc_runner", "--install-only"])

    assert rc == 0
    assert calls == [T.DEFAULT_TLA_VERSION]


def test_explicit_tla_version_overrides_default(monkeypatch, tmp_path):
    """帶 --tla-version v1.8.1 時，流入 download_jar() 的版本字串是該值，非預設值。"""
    from tools.fsm_runtime import tlc_runner as T

    calls: list[str] = []
    monkeypatch.setattr(T, "find_java", lambda: "java")
    monkeypatch.setattr(T, "jar_path", lambda: tmp_path / "tla2tools.jar")
    monkeypatch.setattr(T, "download_jar", _capturing_download_jar(calls, tmp_path))

    rc = T.main(["tlc_runner", "--install-only", "--tla-version", "v1.8.1"])

    assert rc == 0
    assert calls == ["v1.8.1"]
    assert calls != [T.DEFAULT_TLA_VERSION]


def test_install_only_flag_defaults_false_and_parses_true(monkeypatch, tmp_path):
    """--install-only 的 argparse 解析：預設 False（jar 缺失時報錯退出、不下載）、
    帶了即 True（觸發下載並提前返回，不執行 run_tlc）。"""
    from tools.fsm_runtime import tlc_runner as T

    calls: list[str] = []
    monkeypatch.setattr(T, "find_java", lambda: "java")
    monkeypatch.setattr(T, "jar_path", lambda: tmp_path / "tla2tools.jar")
    monkeypatch.setattr(T, "download_jar", _capturing_download_jar(calls, tmp_path))

    # 不帶 --install-only、也不帶 --download：預設須為 False，jar 缺失時直接報錯
    # 退出（rc=2），不呼叫 download_jar——若 store_true 被改壞成恆為 True，這裡
    # 會誤觸發下載、rc 誤變 0。
    rc_default = T.main(["tlc_runner"])
    assert rc_default == 2
    assert calls == []

    # 帶 --install-only：True，觸發下載並提前返回 0（不執行 run_tlc）。
    rc_flag = T.main(["tlc_runner", "--install-only"])
    assert rc_flag == 0
    assert calls == [T.DEFAULT_TLA_VERSION]
