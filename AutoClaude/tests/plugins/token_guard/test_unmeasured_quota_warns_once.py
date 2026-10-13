"""ARCH-02(a)：引擎獨立執行時量不到額度，不得「安靜地不存在」——第一次評估一次性出聲。

驗證意圖（Rule 9）：引擎側沒有額度刷新者（R82 決策：TestTheQuotaAxisHasNoEngineSideRefresher），
獨立跑且快取過期時 `read_worst_pct()` 回 None ⇒ 額度軸整條失效，而失效與「額度充足」在日誌上
外觀相同。
本檔守的是「失效可偵測」：量不到＋有裝 meter ⇒ 恰好一句 WARNING（講後果與補救）；量得到、沒裝
meter（這一軸本就不存在）、第二次起 ⇒ 靜默；而發聲不得改變任何判決。
"""
from __future__ import annotations

import logging

from autoclaude.core.ports.quota_meter import QuotaReading
from autoclaude.plugins.token_guard.policy import TokenGuardPlugin
from autoclaude.utils.config import TokenGuardConfig

_LOGGER = "autoclaude.plugins.token_guard"


class _Meter:
    def __init__(self, reading: QuotaReading | None):
        self._r = reading

    def read(self):
        return self._r

    def read_worst_pct(self):
        return self._r


def _said(caplog) -> list[str]:
    msgs = [r.getMessage() for r in caplog.records
            if r.name == _LOGGER and r.levelno == logging.WARNING]
    return [m for m in msgs if "額度遙測缺席" in m]


def _plugin(reading) -> TokenGuardPlugin:
    return TokenGuardPlugin(token_guard_cfg=TokenGuardConfig(), quota_meter=_Meter(reading))


class TestAnUnmeasurableQuotaSpeaksExactlyOnce:
    def test_the_first_evaluation_speaks_and_later_ones_stay_quiet(self, caplog):
        plugin = _plugin(None)
        with caplog.at_level(logging.WARNING, logger=_LOGGER):
            for _ in range(3):
                assert plugin.evaluate_quota({}) is None
        assert len(_said(caplog)) == 1, "量不到卻沒出聲（安靜失效），或每次評估都洗版"

    def test_the_sentence_names_the_consequence_and_the_remedy(self, caplog):
        with caplog.at_level(logging.WARNING, logger=_LOGGER):
            _plugin(None).evaluate_quota({})
        msg = _said(caplog)[0]
        for needle in ("resume_delay_minutes", "max_auto_resumes", "--pace"):
            assert needle in msg, f"訊息沒說到 {needle}（使用者不知道後果或怎麼補量）"

    def test_the_limit_retry_path_shares_the_same_single_shot(self, caplog):
        """`limit_retry_wait` 與 `evaluate_quota` 共用 `_quota_view`：兩條路加起來也只講一次。"""
        plugin = _plugin(None)
        with caplog.at_level(logging.WARNING, logger=_LOGGER):
            plugin.limit_retry_wait("API Error: 429 rate limit exceeded. Retry-After: 60", 0)
            assert len(_said(caplog)) == 1, "退避那條路也讀額度視圖，量不到時它也該講"
            plugin.evaluate_quota({})
        assert len(_said(caplog)) == 1


class TestSilenceWhereNothingIsMissing:
    def test_a_measured_quota_never_warns(self, caplog):
        with caplog.at_level(logging.WARNING, logger=_LOGGER):
            _plugin(QuotaReading(10.0, "session", None)).evaluate_quota({})
        assert _said(caplog) == []

    def test_without_any_meter_the_axis_does_not_exist_and_stays_silent(self, caplog):
        """沒裝 meter＝這一軸本來就不存在（單元測試／內嵌用法），不是「失效」。"""
        with caplog.at_level(logging.WARNING, logger=_LOGGER):
            assert TokenGuardPlugin().evaluate_quota({}) is None
        assert _said(caplog) == []


class TestSpeakingChangesNoDecision:
    def test_the_limit_text_halt_still_fires_when_the_quota_is_unmeasured(self):
        """量不到時仍有撞線訊息那一層（離線、零 token）；出聲不得吞掉或改變它。"""
        req = _plugin(None).evaluate_quota({"failure_reason": "Claude usage limit reached"})
        assert req is not None and req.request_halt is True
