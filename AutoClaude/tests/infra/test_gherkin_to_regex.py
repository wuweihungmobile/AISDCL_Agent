"""W3（AutoSDD_improving_01 §3.1）：Gherkin Then → expected_output_regex 轉譯實例
+ weak_regex audit 路徑（禁 silent fallback）。
"""
from __future__ import annotations

import re

from autoclaude.core.ports.observability import NullObservability
from autoclaude.infra.adapters.sdd_to_playbook_adapter import SddToPlaybookAdapter


def _to_regex(gherkin: str, obs=None):
    adapter = SddToPlaybookAdapter(observability=obs)
    return adapter._gherkin_to_regex(gherkin)


class TestTranslationExamples:
    """§3.1 轉譯實例表逐列驗證。"""

    def test_status_code_with_literal(self):
        regex, weak = _to_regex("Then 回傳 201 Created")
        assert weak is False
        assert re.search(regex, "HTTP 201") and re.search(regex, "CREATED")

    def test_quoted_literal_escaped(self):
        regex, weak = _to_regex("Then 顯示錯誤訊息「餘額不足」")
        assert (regex, weak) == ("餘額不足", False)
        assert re.search(regex, "錯誤：餘額不足！")

    def test_quantitative_nfr_falls_back_weak(self):
        regex, weak = _to_regex("Then 回應時間 < 200ms")
        assert weak is True
        assert regex == r"\bPASS(ED)?\b"
        assert re.search(regex, "12 PASSED in 3s")
        assert not re.search(regex, "COMPASS heading")  # \b 邊界保護

    def test_quoted_wins_over_status_code(self):
        regex, weak = _to_regex('Then 系統回傳 HTTP 401\nAnd 回傳錯誤訊息 "Invalid credentials"')
        assert weak is False
        assert regex == re.escape("Invalid credentials")

    def test_status_only_no_literal(self):
        regex, weak = _to_regex("Then 系統回傳 HTTP 401")
        assert weak is False
        assert re.search(regex, "got 401")

    def test_no_then_at_all_falls_back_weak(self):
        regex, weak = _to_regex("一般描述文字，無 Gherkin 結構")
        assert weak is True

    def test_and_before_then_not_treated_as_assertion(self):
        # And 在 Given 之後、Then 之前 → 非斷言
        gherkin = "Given 前置\nAnd 帳號 \"user@example.com\" 已存在\nWhen 動作\nThen 回傳 201"
        regex, weak = _to_regex(gherkin)
        assert weak is False
        assert re.search(regex, "201")  # 取 Then 的 201，而非 Given 段引號字面值

    def test_regex_is_valid_pattern(self):
        for g in ["Then 回傳 201 Created", "Then 顯示「a.b*c」", "Then x < 1ms"]:
            regex, _ = _to_regex(g)
            re.compile(regex)  # 不拋例外即通過


class _SpyObs(NullObservability):
    def __init__(self):
        self.events: list[tuple[str, dict]] = []

    def record_event(self, name, attributes=None):
        self.events.append((name, dict(attributes or {})))


class TestWeakRegexAudit:
    """weak_regex 必經 IObservabilityPort 留痕（sdd.weak_regex 事件）。"""

    _SPEC = """| AC ID | d | AT ID | d | a | 測試類型 | s |
|---|---|---|---|---|---|---|
| AC-001-1 | x | AT-001-1-1 | x | ✅ | Unit | □ |

```gherkin
# AT-001-1-1
Then 回應時間 < 200ms
```
"""

    def test_weak_regex_emits_audit_event(self):
        spy = _SpyObs()
        adapter = SddToPlaybookAdapter(observability=spy)
        contracts = adapter._parse_contracts(self._SPEC)
        assert contracts[0].weak_regex is True
        assert spy.events == [
            ("sdd.weak_regex",
             {"at_id": "AT-001-1-1", "gherkin": contracts[0].gherkin})]

    def test_strong_regex_no_audit_event(self):
        spy = _SpyObs()
        adapter = SddToPlaybookAdapter(observability=spy)
        adapter._parse_contracts(self._SPEC.replace("回應時間 < 200ms", "回傳 201"))
        assert spy.events == []
