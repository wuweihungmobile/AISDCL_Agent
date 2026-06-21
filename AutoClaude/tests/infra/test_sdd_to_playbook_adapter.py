"""W3（AutoSDD_improving_01 §3）：SddToPlaybookAdapter 單測 + 消毒攻防測試。

覆蓋：
  1. 凍結硬閘（frozen_stages / current_state / 無狀態檔 fail-closed）
  2. TEST-CONTRACT-SPEC 解析（AC→AT 表 + Gherkin 區塊 + 場景偵測）
  3. compile_tasks 轉譯規則（step_id / max_retries / maintain_context / prompt digest）
  4. 注入攻防（黑名單字元 → SpecTaintedError；evaluator 僅白名單模板）
"""
from __future__ import annotations

import re

import pytest
import yaml

from autoclaude.core.ports.spec_source import (
    ISpecSource,
    SpecNotFrozenError,
    SpecTaintedError,
)
from autoclaude.infra.adapters.sdd_to_playbook_adapter import SddToPlaybookAdapter

_SPEC_MD = """# Test Contract Specification — Demo

場景：brownfield 既有系統改進

## 1. AC → AT 映射表

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-001-1 | 登入成功 | AT-001-1-1 | 正常登入 | ✅ | Unit | □ |
| AC-001-1 | 登入成功 | AT-001-1-2 | 錯誤密碼 | ✅ | Integration | □ |
| AC-002-1 | 餘額警示 | AT-002-1-1 | 餘額不足提示 | ✅ | E2E | □ |

## 2. AT 格式

```gherkin
# AT-001-1-1
Scenario: 正常登入
  Given 使用者在登入頁面
  When 輸入正確帳密
  Then 回傳 201 Created
```

```gherkin
# AT-001-1-2
Scenario: 錯誤密碼
  Given 使用者在登入頁面
  When 輸入錯誤密碼
  Then 顯示錯誤訊息「餘額不足」
```

```gherkin
# AT-002-1-1
Scenario: 回應時間
  Given 系統在尖峰負載
  When 查詢餘額
  Then 回應時間 < 200ms
```
"""


def _write_fsm_state(root, current_state="IMPLEMENTATION", frozen_stages=None):
    fsm_dir = root / "build" / "reports" / "fsm"
    fsm_dir.mkdir(parents=True, exist_ok=True)
    doc = {"fsm_state": {"current_state": current_state,
                         "frozen_stages": frozen_stages or []}}
    (fsm_dir / "FSM-STATE-demo.yaml").write_text(
        yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")


def _write_spec(root, text=_SPEC_MD, name="TEST-CONTRACT-SPEC-Demo.md"):
    docs = root / "docs" / "03_testing" / "contracts"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / name).write_text(text, encoding="utf-8")
    return root / "docs"


class TestFrozenGate:
    def test_no_fsm_state_file_fail_closed(self, tmp_path):
        spec_dir = _write_spec(tmp_path)
        with pytest.raises(SpecNotFrozenError, match="FSM"):
            SddToPlaybookAdapter().load_spec(str(spec_dir))

    def test_not_frozen_state_rejected(self, tmp_path):
        spec_dir = _write_spec(tmp_path)
        _write_fsm_state(tmp_path, current_state="SPEC_DRAFTING")
        with pytest.raises(SpecNotFrozenError, match="SPEC_DRAFTING"):
            SddToPlaybookAdapter().load_spec(str(spec_dir))

    def test_frozen_stages_accepted_even_if_state_regressed(self, tmp_path):
        spec_dir = _write_spec(tmp_path)
        _write_fsm_state(tmp_path, current_state="SPEC_DRAFTING",
                         frozen_stages=[{"stage": "SCG-0", "frozen_at": "t"}])
        spec = SddToPlaybookAdapter().load_spec(str(spec_dir))
        assert spec.digest.startswith("sha256:")

    @pytest.mark.parametrize("state", ["SPEC_FROZEN", "TEST_CONTRACT_NEGOTIATED",
                                       "IMPLEMENTATION", "RTM_VERIFY"])
    def test_post_frozen_states_accepted(self, tmp_path, state):
        spec_dir = _write_spec(tmp_path)
        _write_fsm_state(tmp_path, current_state=state)
        assert SddToPlaybookAdapter().load_spec(str(spec_dir)).contracts

    def test_explicit_fsm_state_path(self, tmp_path):
        spec_dir = _write_spec(tmp_path)
        _write_fsm_state(tmp_path)
        explicit = tmp_path / "build" / "reports" / "fsm" / "FSM-STATE-demo.yaml"
        adapter = SddToPlaybookAdapter(fsm_state_path=str(explicit))
        assert adapter.load_spec(str(spec_dir)).scenario == "brownfield"

    def test_missing_spec_file_raises(self, tmp_path):
        (tmp_path / "docs").mkdir()
        with pytest.raises(FileNotFoundError):
            SddToPlaybookAdapter().load_spec(str(tmp_path / "docs"))


class TestParsing:
    @pytest.fixture()
    def spec(self, tmp_path):
        spec_dir = _write_spec(tmp_path)
        _write_fsm_state(tmp_path)
        return SddToPlaybookAdapter().load_spec(str(spec_dir))

    def test_three_contracts_parsed(self, spec):
        assert [c.at_id for c in spec.contracts] == [
            "AT-001-1-1", "AT-001-1-2", "AT-002-1-1"]

    def test_scenario_detected(self, spec):
        assert spec.scenario == "brownfield"

    def test_scg_gate_by_test_type(self, spec):
        gates = {c.at_id: c.scg_gate for c in spec.contracts}
        assert gates["AT-001-1-1"] == "SCG-4"   # Unit
        assert gates["AT-002-1-1"] == "SCG-5"   # E2E

    def test_evaluator_cmd_whitelist_template_only(self, spec):
        for c in spec.contracts:
            assert re.fullmatch(
                r'python -m pytest [\w./\\-]+ -k "[A-Za-z0-9_]+" -q',
                c.evaluator_cmd,
            ), c.evaluator_cmd

    def test_satisfies_ispec_source_protocol(self):
        adapter: ISpecSource = SddToPlaybookAdapter()
        assert hasattr(adapter, "load_spec") and hasattr(adapter, "compile_tasks")


class TestCompileTasks:
    @pytest.fixture()
    def tasks(self, tmp_path):
        spec_dir = _write_spec(tmp_path)
        _write_fsm_state(tmp_path)
        adapter = SddToPlaybookAdapter()
        spec = adapter.load_spec(str(spec_dir))
        return spec, adapter.compile_tasks(spec)

    def test_step_id_format_unique(self, tasks):
        _, ts = tasks
        ids = [t.step_id for t in ts]
        assert ids[0] == "sdd-brownfield-at-001-1-1"
        assert len(set(ids)) == len(ids)

    def test_max_retries_by_gate(self, tasks):
        _, ts = tasks
        by_id = {t.step_id: t for t in ts}
        assert by_id["sdd-brownfield-at-001-1-1"].max_retries == 5   # SCG-4
        assert by_id["sdd-brownfield-at-002-1-1"].max_retries == 2   # SCG-5

    def test_maintain_context_within_same_ac_only(self, tasks):
        _, ts = tasks
        assert ts[0].maintain_context is False   # 首步
        assert ts[1].maintain_context is True    # 同 AC-001-1
        assert ts[2].maintain_context is False   # 跨入 AC-002-1

    def test_prompt_contains_gherkin_and_digest(self, tasks):
        spec, ts = tasks
        digest8 = spec.digest.split(":")[-1][:8]
        assert "依下列契約實作並使測試通過" in ts[0].prompt
        assert digest8 in ts[0].prompt
        assert "Given 使用者在登入頁面" in ts[0].prompt


_MULTI_SPEC = """# Test Contract Specification — Multi

場景：greenfield 新建

## 1. AC → AT 映射表

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-029-1 | 建立成功 | AT-029-1-1 | 雙斷言 | ✅ | Integration | □ |

## 2. AT 格式

```gherkin
# AT-029-1-1
Scenario: 建立資源
  Given 前置條件就緒
  When 送出建立請求
  Then 顯示訊息「建立成功」
  And 回傳通知「已寄送」
```
"""


def _gtr(gherkin):
    """白盒呼叫純函式 _gherkin_to_regex（回傳 (regex, weak)）。"""
    return SddToPlaybookAdapter()._gherkin_to_regex(gherkin)


def _block(*then_and_lines):
    body = "\n".join(f"  {ln}" for ln in then_and_lines)
    return f"# AT-029-1-1\nScenario: s\n  Given g\n  When w\n{body}\n"


class TestMultiAssertionCombination:
    """W-29-1：多重 Then/And 斷言組合保真度（AC-29-1）+ 向後相容（AC-29-2）。"""

    # AC-29-1：複雜斷言組合（多引號字面值）
    def test_two_quoted_assertions_combined(self):
        regex, weak = _gtr(_block("Then 顯示訊息「建立成功」", "And 顯示「已寄出」"))
        assert weak is False
        # 順序無關 AND：兩斷言皆須出現
        assert re.search(regex, "log: 建立成功 然後 已寄出")
        assert re.search(regex, "已寄出 在前 建立成功 在後")  # 順序無關
        assert not re.search(regex, "只有 建立成功 沒有另一個")  # 缺一即不過
        assert regex.count("(?=") == 2

    def test_three_quoted_assertions_all_combined(self):
        regex, weak = _gtr(_block(
            "Then 顯示「甲」", "And 顯示「乙」", "And 顯示「丙」"))
        assert weak is False
        assert regex.count("(?=") == 3
        assert re.search(regex, "丙 乙 甲")          # 三者俱全（順序無關）
        assert not re.search(regex, "甲 乙 沒有第三個")  # 缺一即不過

    def test_quoted_wins_when_mixed_with_status(self):
        # 刻意保留設計決策「quoted wins over status code」：混合時只取引號、
        # 不與 status 組合（單引號 → 不觸發多引號組合路徑）。對齊
        # test_gherkin_to_regex.py::test_quoted_wins_over_status_code。
        regex, weak = _gtr(_block("Then 回傳 201 Created", "And 顯示訊息「建立成功」"))
        assert weak is False
        assert regex == re.escape("建立成功")
        assert "(?=" not in regex  # 未組合

    def test_quantitative_excluded_keeps_single_quoted(self):
        # 引號 + 量化 NFR：量化非引號、僅 1 引號 → 走單斷言路徑（非組合）
        regex, weak = _gtr(_block("Then 顯示訊息「建立成功」", "And 回應時間 < 200ms"))
        assert weak is False
        assert regex == re.escape("建立成功")
        assert "(?=" not in regex

    # AC-29-2：向後相容（零行為變化）
    def test_single_quoted_unchanged(self):
        regex, weak = _gtr(_block("Then 顯示錯誤訊息「餘額不足」"))
        assert weak is False
        assert regex == re.escape("餘額不足")
        assert "(?=" not in regex

    def test_single_status_unchanged(self):
        # 單一 status 維持既有 alternation 格式 (?i)(code|phrase)，非新片段格式
        regex, weak = _gtr(_block("Then 回傳 201 Created"))
        assert weak is False
        assert regex == "(?i)(201|created)"

    def test_end_to_end_multi_assertion_regex(self, tmp_path):
        spec_dir = _write_spec(tmp_path, text=_MULTI_SPEC,
                               name="TEST-CONTRACT-SPEC-Multi.md")
        _write_fsm_state(tmp_path)
        spec = SddToPlaybookAdapter().load_spec(str(spec_dir))
        c = next(c for c in spec.contracts if c.at_id == "AT-029-1-1")
        assert c.weak_regex is False
        assert c.expected_regex.count("(?=") == 2
        # evaluator 端 re.search 同時驗證兩引號斷言
        assert re.search(c.expected_regex, "輸出 建立成功 並 已寄送 通知")
        assert not re.search(c.expected_regex, "輸出 建立成功 但缺後半")


_NEG_SPEC = """# Test Contract Specification — Negative

場景：security 安全強化

## 1. AC → AT 映射表

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-031-1 | 不洩漏敏感資訊 | AT-031-1-1 | 回應不含密碼 | ✅ | Integration | □ |

## 2. AT 格式

```gherkin
# AT-031-1-1
Scenario: 隱私防護
  Given 使用者已登入
  When 查詢個人資料
  Then 顯示訊息「查詢成功」
  And 回應不應包含「password」
```
"""


class TestNegativeAssertionFidelity:
    """W-31-1：負向斷言保真度（AC-31-1）。修正「不應包含「X」」被譯為要求 X 出現的
    語意顛倒缺口；負向用 \\A 錨定 (?!.*X) 確保 re.search 下「不出現」語意正確。"""

    def test_single_negative_requires_absence(self):
        regex, weak = _gtr(_block("Then 回應不應包含「password」"))
        assert weak is False
        assert regex == r"(?s)\A(?!.*password)"
        # 不含 → 通過；含 → 不過（語意未顛倒）
        assert re.search(regex, "回應為 token=abc 一切正常")
        assert not re.search(regex, "回應洩漏 password=secret")

    def test_mixed_positive_and_negative(self):
        regex, weak = _gtr(_block(
            "Then 顯示訊息「查詢成功」", "And 回應不得包含「password」"))
        assert weak is False
        # 正向 lookahead + 負向 lookahead，皆 \A 錨定
        assert regex == r"(?s)\A(?=.*查詢成功)(?!.*password)"
        assert re.search(regex, "查詢成功 且 token=abc")          # 正存負缺 → 過
        assert not re.search(regex, "查詢成功 但 password=x 外洩")  # 含禁詞 → 不過
        assert not re.search(regex, "沒有成功字樣 也無禁詞")        # 缺正向 → 不過

    def test_multiple_negatives_all_absent(self):
        regex, weak = _gtr(_block(
            "Then 不應顯示「internal error」", "And 不得回傳「stacktrace」"))
        assert weak is False
        assert regex.count("(?!") == 2
        assert regex.startswith(r"(?s)\A")
        assert re.search(regex, "輸出乾淨無內部訊息")
        assert not re.search(regex, "internal error 出現了")
        assert not re.search(regex, "夾帶 stacktrace 細節")

    def test_english_negation_marker(self):
        regex, weak = _gtr(_block('Then the response should not contain "secret"'))
        assert weak is False
        assert regex == r"(?s)\A(?!.*secret)"
        assert not re.search(regex, "leaked secret value")
        assert re.search(regex, "all clean output")

    def test_negation_inside_quote_is_positive(self):
        # 否定字眼在引號「之內」屬訊息文字，非斷言否定 → 仍為正向（向後相容）
        regex, weak = _gtr(_block("Then 顯示警告「不可撤銷」"))
        assert weak is False
        assert regex == re.escape("不可撤銷")
        assert "(?!" not in regex and "\\A" not in regex

    def test_end_to_end_negative_regex(self, tmp_path):
        spec_dir = _write_spec(tmp_path, text=_NEG_SPEC,
                               name="TEST-CONTRACT-SPEC-Neg.md")
        _write_fsm_state(tmp_path)
        spec = SddToPlaybookAdapter().load_spec(str(spec_dir))
        c = next(c for c in spec.contracts if c.at_id == "AT-031-1-1")
        assert c.weak_regex is False
        # 正向「查詢成功」須出現、負向「password」須不出現
        assert "(?=.*查詢成功)" in c.expected_regex
        assert "(?!.*password)" in c.expected_regex
        assert re.search(c.expected_regex, "輸出 查詢成功 token=abc")
        assert not re.search(c.expected_regex, "輸出 查詢成功 但 password 外洩")

    def test_positive_only_unchanged_no_anchor(self):
        # 防退化哨兵：純正向 ≥2 引號維持 improving_29 格式（不含 \A、不含 (?!）
        regex, _ = _gtr(_block("Then 顯示「甲」", "And 顯示「乙」"))
        assert regex == "(?s)(?=.*甲)(?=.*乙)"
        assert "\\A" not in regex and "(?!" not in regex


_NEG_STATUS_SPEC = """# Test Contract Specification — Negative Status

場景：security 安全強化

## 1. AC → AT 映射表

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-032-1 | 不洩漏內部錯誤碼 | AT-032-1-1 | 未授權不得回傳 500 | ✅ | Integration | □ |

## 2. AT 格式

```gherkin
# AT-032-1-1
Scenario: 不洩漏內部錯誤
  Given 未授權請求
  When 存取受保護資源
  Then 系統不應回傳 500
```
"""


class TestNegativeStatusAssertionFidelity:
    """W-32-1：否定狀態碼斷言保真度（AC-32-1）。修正與 W-31-1 引號路徑對稱的
    mis-specify——「不應回傳 500」原被譯為 (?i)(500)＝要求 500 出現（語意顛倒）；
    本輪改為 \\A(?!.*500) 要求該狀態碼不出現。"""

    def test_single_negative_status_requires_absence(self):
        regex, weak = _gtr(_block("Then 系統不應回傳 500"))
        assert weak is False
        assert regex == r"(?s)\A(?!.*500)"
        # 不含 500 → 通過；含 500 → 不過（語意未顛倒）
        assert re.search(regex, "回應 200 OK 一切正常")
        assert not re.search(regex, "伺服器回傳 500 Internal Server Error")

    def test_negative_status_english_marker(self):
        regex, weak = _gtr(_block("Then the API must not return 403"))
        assert weak is False
        assert regex == r"(?s)\A(?!.*403)"
        assert not re.search(regex, "got 403 forbidden")
        assert re.search(regex, "got 200 ok")

    def test_positive_status_unchanged_sentinel(self):
        # 防退化哨兵：正向狀態碼維持 improving_01 既有 (?i)(code|phrase) 格式，
        # 絕不誤套負向 \A/(?! （保護「回傳 201 Created」等正向路徑 bit-for-bit 不變）。
        regex, weak = _gtr(_block("Then 回傳 201 Created"))
        assert weak is False
        assert regex == "(?i)(201|created)"
        assert "\\A" not in regex and "(?!" not in regex

    def test_negative_status_includes_trailing_phrase(self):
        # W-40-1（DEF-32-002）：尾隨描述片語一併納入負向 lookahead（修原刻意排除之漏放）。
        # 含字母片語 → 全域 (?i)（與正向 case 一致）；片語正規化同正向 strip().lower()+escape。
        regex, weak = _gtr(_block("Then 不得回傳 500 Internal Server Error"))
        assert weak is False
        assert regex == r"(?is)\A(?!.*500)(?!.*internal\ server\ error)"

    def test_negative_status_phrase_only_output_caught(self):
        # DEF-32-002 核心修復：系統輸出僅含片語不帶數字「500」時，修正前 (?s)\A(?!.*500)
        # 會漏放（誤判通過）；修正後因片語 lookahead 命中 → 正確擋下。
        regex, _ = _gtr(_block("Then 不得回傳 500 Internal Server Error"))
        assert not re.search(regex, "回應 Internal Server Error 給呼叫者")  # 修復前會漏放
        assert not re.search(regex, "伺服器回傳 500")                      # 數字仍擋
        assert re.search(regex, "回應 200 OK 一切正常")                    # 正常輸出放行

    def test_negative_status_phrase_case_insensitive(self):
        # case 一致性：片語在 (?i) 下大小寫無關，任意 case 的洩漏輸出皆攔下。
        regex, _ = _gtr(_block("Then 不得回傳 500 Internal Server Error"))
        assert not re.search(regex, "INTERNAL SERVER ERROR leaked")
        assert not re.search(regex, "internal server error")

    def test_quoted_wins_over_negative_status(self):
        # quoted-wins 設計保留：同時含引號字面值時走引號路徑，狀態碼（含其否定）不評估。
        regex, weak = _gtr(_block(
            "Then 系統不應回傳 500", "And 顯示訊息「查詢成功」"))
        assert weak is False
        assert regex == re.escape("查詢成功")
        assert "500" not in regex

    def test_end_to_end_negative_status_regex(self, tmp_path):
        spec_dir = _write_spec(tmp_path, text=_NEG_STATUS_SPEC,
                               name="TEST-CONTRACT-SPEC-NegStatus.md")
        _write_fsm_state(tmp_path)
        spec = SddToPlaybookAdapter().load_spec(str(spec_dir))
        c = next(c for c in spec.contracts if c.at_id == "AT-032-1-1")
        assert c.weak_regex is False
        assert c.expected_regex == r"(?s)\A(?!.*500)"
        assert re.search(c.expected_regex, "回應 200 給未授權者")
        assert not re.search(c.expected_regex, "回應 500 洩漏內部錯誤")


_MULTI_STATUS_SPEC = """# Test Contract Specification — Multi Status

場景：security 安全強化

## 1. AC → AT 映射表

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-041-1 | 不洩漏多種錯誤碼 | AT-041-1-1 | 未授權不得回傳 500 或 403 | ✅ | Integration | □ |

## 2. AT 格式

```gherkin
# AT-041-1-1
Scenario: 不洩漏多種內部錯誤
  Given 未授權請求
  When 存取受保護資源
  Then 系統不應回傳 500
  And 系統不應回傳 403
```
"""


class TestStatusAssertionAggregation:
    """W-41-1：狀態碼斷言跨行聚合保真度（DEF-41-001）。修正與引號路徑對稱的
    under-specify——原狀態碼路徑只取「首條」status 行即 return，致多條負向只擋首條、
    或正負混合時負向遭丟棄（漏放）。改為收集所有 Then/And 狀態碼斷言。"""

    def test_multiple_negative_status_all_aggregated(self):
        # 核心修復（缺口 A）：兩條負向狀態碼皆須納入 lookahead，非只擋首條。
        regex, weak = _gtr(_block("Then 系統不應回傳 500", "And 系統不應回傳 403"))
        assert weak is False
        assert regex == r"(?s)\A(?!.*500)(?!.*403)"
        assert not re.search(regex, "回應 403 forbidden")   # 修正前漏放（只擋 500）
        assert not re.search(regex, "伺服器回傳 500")        # 首條仍擋
        assert re.search(regex, "回應 200 OK 一切正常")      # 皆不含 → 放行

    def test_positive_and_negative_status_mixed(self):
        # 核心修復（缺口 B）：正向在前時，原 (?i)(200) 完全丟棄負向 500；改為
        # (?=.*(?:200)) 要求 200 出現 + (?!.*500) 要求 500 不出現。
        regex, weak = _gtr(_block("Then 回傳 200", "And 不應回傳 500"))
        assert weak is False
        assert regex == r"(?s)\A(?=.*(?:200))(?!.*500)"
        assert not re.search(regex, "回傳 200 然後洩漏 500")  # 修正前漏放（負向被丟）
        assert not re.search(regex, "回應 forbidden 缺成功碼")  # 缺正向 200 → 不過
        assert re.search(regex, "回傳 200 一切正常")           # 含 200 不含 500 → 放行

    def test_multiple_negative_status_with_phrases_case_insensitive(self):
        # 含片語的多負向：碼與片語各自 (?!)，任一含字母片語 → 全域 (?i)（與 W-40-1 一致）。
        regex, weak = _gtr(_block(
            "Then 不得回傳 500 Internal Server Error", "And 不應回傳 403 Forbidden"))
        assert weak is False
        assert regex == (
            r"(?is)\A(?!.*500)(?!.*internal\ server\ error)(?!.*403)(?!.*forbidden)")
        assert not re.search(regex, "回應 FORBIDDEN 給呼叫者")     # 片語 case 無關仍擋
        assert not re.search(regex, "internal server error leaked")
        assert re.search(regex, "回應 200 OK")                     # 皆不含 → 放行

    def test_single_negative_status_unchanged_sentinel(self):
        # 防退化哨兵：單條負向（無片語）逐位元維持 (?s)\A(?!.*500)，不因聚合路徑改格式。
        regex, weak = _gtr(_block("Then 系統不應回傳 500"))
        assert weak is False
        assert regex == r"(?s)\A(?!.*500)"

    def test_single_positive_status_unchanged_sentinel(self):
        # 防退化哨兵：單條正向維持 alternation (?i)(碼|片語)，絕不誤套 \A/(?=/(?!。
        regex, weak = _gtr(_block("Then 回傳 201 Created"))
        assert weak is False
        assert regex == "(?i)(201|created)"
        assert "\\A" not in regex and "(?!" not in regex and "(?=" not in regex

    def test_end_to_end_multi_negative_status_regex(self, tmp_path):
        spec_dir = _write_spec(tmp_path, text=_MULTI_STATUS_SPEC,
                               name="TEST-CONTRACT-SPEC-MultiStatus.md")
        _write_fsm_state(tmp_path)
        spec = SddToPlaybookAdapter().load_spec(str(spec_dir))
        c = next(c for c in spec.contracts if c.at_id == "AT-041-1-1")
        assert c.weak_regex is False
        assert c.expected_regex == r"(?s)\A(?!.*500)(?!.*403)"
        assert re.search(c.expected_regex, "回應 200 給未授權者")
        assert not re.search(c.expected_regex, "回應 403 洩漏狀態")  # 第二條負向真攔


class TestNegationIdiomFidelity:
    """W-33-1（DEF-31-001）：裸 not 排除「not only…（but）」「is not empty」慣用語——
    此處 not 非否定其後引號，須維持正向；同時保證真否定（not contain）與強標記
    （should not）不受影響。"""

    def test_not_only_idiom_keeps_positive(self):
        # 「not only X but …」：not 為連接詞片語，引號斷言仍為正向（非否定）
        regex, weak = _gtr(_block('Then the response is not only valid but returns "token"'))
        assert weak is False
        assert regex == re.escape("token")
        assert "(?!" not in regex and "\\A" not in regex
        assert re.search(regex, "got token=abc")

    def test_is_not_empty_idiom_keeps_positive(self):
        # 「is not empty」：not empty 為存在斷言，其後引號為正向
        regex, weak = _gtr(_block('Then the result list is not empty and contains "user_id"'))
        assert weak is False
        assert regex == re.escape("user_id")
        assert "(?!" not in regex and "\\A" not in regex

    def test_genuine_not_contain_still_negative(self):
        # 防退化：真否定「does not contain X」（not 後非 only/empty）仍正確判為負向
        regex, weak = _gtr(_block('Then the response does not contain "password"'))
        assert weak is False
        assert regex == r"(?s)\A(?!.*password)"
        assert not re.search(regex, "leaked password=secret")
        assert re.search(regex, "all clean output")

    def test_idiom_then_genuine_negation_left_scan(self):
        # .search 左掃：首個 not 命中慣用語被排除，第二個真否定 not 仍命中 → 引號負向
        regex, weak = _gtr(_block(
            'Then the list is not empty but does not contain "spam"'))
        assert weak is False
        assert regex == r"(?s)\A(?!.*spam)"
        assert not re.search(regex, "found spam in body")
        assert re.search(regex, "clean body")

    def test_strong_marker_negation_unaffected(self):
        # 防退化哨兵：強標記 should not 不受裸 not 收斂影響，仍正確分流負向
        regex, weak = _gtr(_block(
            'Then the page shows "welcome"', 'And it should not contain "error"'))
        assert weak is False
        assert regex == r"(?s)\A(?=.*welcome)(?!.*error)"


class TestInjectionDefense:
    """§1.3 消毒攻防：黑名單字元 / 非白名單片段一律 SpecTaintedError。"""

    @pytest.mark.parametrize("payload", [
        "tests; rm -rf /",
        "tests`whoami`",
        "tests$(id)",
        "tests>out",
        "tests<in",
        "tests!bang",
        "tests~home",
        "tests&bg",
        "tests with space",
    ])
    def test_tainted_test_path_rejected(self, payload):
        with pytest.raises(SpecTaintedError):
            SddToPlaybookAdapter(test_path=payload)

    def test_tainted_at_id_in_spec_rejected(self, tmp_path):
        evil = _SPEC_MD.replace("AT-002-1-1", "AT-002-1-1;rm")
        spec_dir = _write_spec(tmp_path, text=evil)
        _write_fsm_state(tmp_path)
        # 注入的分號不符 AT row regex → 該列被拒於解析之外（白名單 regex 第一層）
        spec = SddToPlaybookAdapter().load_spec(str(spec_dir))
        assert all(";" not in c.evaluator_cmd for c in spec.contracts)

    def test_evaluator_cmd_never_contains_deny_chars(self, tmp_path):
        spec_dir = _write_spec(tmp_path)
        _write_fsm_state(tmp_path)
        spec = SddToPlaybookAdapter().load_spec(str(spec_dir))
        deny = set("!`><~$&;")
        for c in spec.contracts:
            assert not (set(c.evaluator_cmd) & deny), c.evaluator_cmd
