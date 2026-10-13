"""PRD §8 列 1「非預期 429（推論端）」：有 `Retry-After` 且夠短 ⇒ 有界退避重試，否則維持既有 halt。

立案（PRD §16.2「§8 列 1」那一列）：此前 limit 字樣一律 halt，沒有 `Retry-After` 遵循／full-jitter／
重試次數；再開症狀＝一次推論端非預期 429（帶 `Retry-After` 且短於一個 halt 週期）使引擎直接 halt、
而本可由退避化解。本檔守決策層（純函式＋plugin 的 `limit_retry_wait`）；kernel 的重跑機制與接線在
`tests/core/test_kernel_limit_retry_prd8_1.py`。

四層判準，各守一個失效方向：
  (a) 解析：`Retry-After: N`／`retry after N seconds`／帶單位／帶引號的 JSON 形態都認；認不準的
      一律回 None（⇒ halt）——解析錯成「很短」會讓引擎在伺服器要求久等時提早重打。
  (b) 純決策：第 1～max 次回等待秒數、第 max+1 次回 None；缺席／過長 ⇒ None；邊界值逐一釘住。
  (c) 退避形狀：遵循伺服器建議（不早於 Retry-After）＋ full-jitter（上限 min(cap, 10·2^n)）。
  (d) plugin：額度已撞硬線時不退避（那是真的用完，不是遙測落後）；無 Retry-After 時既有 halt
      逐位不變。
"""
from __future__ import annotations

import pytest

from autoclaude.core.ports.quota_meter import QuotaReading, retry_after_seconds
from autoclaude.plugins.token_guard.policy import TokenGuardPlugin
from autoclaude.plugins.token_guard.thresholds import limit_retry_wait_decision
from autoclaude.utils.config import TokenGuardConfig

_429 = "429 rate limit exceeded"


# ══════════════════════════════════════════════════════════════════════════════
# (a) 解析
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("text, expected", [
    ("API Error: 429 rate limit exceeded. Retry-After: 60", 60),
    ("429 rate limit exceeded\nretry-after: 7\n", 7),
    ("429 Too Many Requests retry-after=15", 15),
    ("rate limit hit; please retry after 30 seconds.", 30),
    ("429 rate limit exceeded, retry after 60s", 60),
    ("rate limit: Retry after 2 minutes", 120),
    ("rate limit: retry after 1.5 seconds", 2),            # 向上取整：寧晚勿早
    ("rate limit: retry after 1500ms", 2),
    ('{"type":"error","error":{"type":"rate_limit_error"},"retry-after": "45"}', 45),
    ("rate limit retry_after: 9", 9),
    ("rate limit: retry after 3 days", 259200),             # 認得單位才能讓上界判準擋掉它
    ("rate limit: Retry-After: 60 more details follow", 60),  # `60 more` 不是單位 m
])
def test_the_recognised_forms(text, expected):
    assert retry_after_seconds(text) == expected


@pytest.mark.parametrize("text", [
    None, 123, "", "429 rate limit exceeded", "Claude usage limit reached. Resets at 9am",
    "retry after", "Retry-After:", "Retry-After: soon", "retry after tomorrow",
    "Retry-After: Wed, 21 Oct 2026 07:28:00 GMT",   # HTTP-date 形態：不猜，走 halt
    "Retrying in 40 seconds… (attempt 3/10)",       # CLI 自己的倒數，不是給我們的指示
])
def test_unrecognised_forms_are_none_never_a_guess(text):
    assert retry_after_seconds(text) is None


def test_the_first_hint_wins():
    assert retry_after_seconds("retry-after: 5 ... retry-after: 500") == 5


# ══════════════════════════════════════════════════════════════════════════════
# (b)(c) 純決策與退避形狀
# ══════════════════════════════════════════════════════════════════════════════
def _decide(retry_after, used=0, max_retries=5, max_after=300, rand=lambda: 0.0):
    return limit_retry_wait_decision(retry_after=retry_after, retries_used=used,
                                     max_retries=max_retries, max_retry_after=max_after,
                                     rand=rand)


def test_retries_one_to_five_wait_and_the_sixth_is_the_halt_path():
    """核心判準：Retry-After 60 ⇒ 第 1～5 次回等待秒數、第 6 次回 None（⇒ 既有 halt）。"""
    waits = [_decide(60, used=n) for n in range(5)]
    assert all(isinstance(w, float) and w >= 60 for w in waits), waits
    assert _decide(60, used=5) is None
    assert _decide(60, used=99) is None


def test_an_absent_retry_after_never_retries():
    for used in range(8):
        assert _decide(None, used=used) is None


@pytest.mark.parametrize("retry_after, expected_none", [(299, False), (300, False), (301, True),
                                                        (3600, True)])
def test_the_retry_after_upper_bound_is_inclusive(retry_after, expected_none):
    assert (_decide(retry_after) is None) is expected_none


def test_the_retry_count_boundary_is_exact():
    assert _decide(10, used=4, max_retries=5) is not None
    assert _decide(10, used=5, max_retries=5) is None
    assert _decide(10, used=0, max_retries=1) is not None
    assert _decide(10, used=1, max_retries=1) is None


def test_zero_max_retries_turns_the_backoff_off():
    assert _decide(10, used=0, max_retries=0) is None


def test_the_wait_never_undercuts_the_servers_hint_and_jitter_is_bounded():
    """遵循伺服器建議：rand=0 時**恰等於** Retry-After（jitter 只往後加）；rand→1 時逼近上限。
    jitter 上限＝min(cap, 10·2^n)（PRD §8 列 1 的 full-jitter 公式），n 為已重試次數。"""
    for n in range(5):
        floor = _decide(60, used=n, rand=lambda: 0.0)
        ceil = _decide(60, used=n, rand=lambda: 0.999999)
        assert floor == 60.0
        assert ceil == pytest.approx(60 + min(300, 10 * 2 ** n), abs=1e-3)
        assert ceil < 60 + min(300, 10 * 2 ** n)


def test_the_jitter_window_doubles_per_retry_then_is_capped_by_the_retry_after_bound():
    spans = [_decide(60, used=n, rand=lambda: 0.5) - 60 for n in range(5)]
    assert spans == [5.0, 10.0, 20.0, 40.0, 80.0]
    capped = _decide(10, used=4, max_after=100, rand=lambda: 0.5) - 10
    assert capped == 50.0, "上限取 min(cap=max_retry_after, 10·2^n)：160 被 cap=100 壓成 100"


def test_two_agents_hitting_the_wall_together_do_not_retry_in_lockstep():
    """full-jitter 的存在理由：同時撞牆的多個 Agent 若等同樣久就會同步重打（雷群）。"""
    draws = iter([0.1, 0.9])
    a = _decide(60, used=2, rand=lambda: next(draws))
    b = _decide(60, used=2, rand=lambda: next(draws))
    assert a != b


# ══════════════════════════════════════════════════════════════════════════════
# 設定旋鈕
# ══════════════════════════════════════════════════════════════════════════════
def test_the_two_knobs_have_the_documented_factory_values():
    cfg = TokenGuardConfig()
    assert cfg.max_retry_after_seconds == 300
    assert cfg.max_limit_retries == 5


@pytest.mark.parametrize("field, bad", [("max_retry_after_seconds", 0),
                                        ("max_retry_after_seconds", 3601),
                                        ("max_limit_retries", -1), ("max_limit_retries", 21)])
def test_out_of_range_knob_values_are_rejected(field, bad):
    with pytest.raises(ValueError):
        TokenGuardConfig(**{field: bad})


@pytest.mark.parametrize("field, edge", [("max_retry_after_seconds", 1),
                                         ("max_retry_after_seconds", 3600),
                                         ("max_limit_retries", 0), ("max_limit_retries", 20)])
def test_the_range_edges_are_accepted(field, edge):
    assert getattr(TokenGuardConfig(**{field: edge}), field) == edge


# ══════════════════════════════════════════════════════════════════════════════
# (d) plugin：limit_retry_wait
# ══════════════════════════════════════════════════════════════════════════════
class _Meter:
    def __init__(self, pct=None, band=None):
        self._r = None if pct is None else QuotaReading(pct, "five_hour", None)
        self._band = band
        self.reads = 0

    def read(self):
        return self._r

    def read_worst_pct(self):
        self.reads += 1
        return self._r

    def read_pace(self):
        class _P:
            band = self._band or "unmeasured"
        return _P()


def _plugin(meter=None, **cfg):
    # 兩條門檻明寫：出廠值由 .env／env.shared 驅動（本機可被調成別的數字），測試不得隨之漂移。
    cfg.setdefault("quota_halt_pct", 95.0)
    cfg.setdefault("quota_throttle_pct", 70.0)
    return TokenGuardPlugin(TokenGuardConfig(**cfg), quota_meter=meter, rand=lambda: 0.0)


def test_a_short_retry_after_on_a_429_gets_a_wait_from_the_plugin():
    assert _plugin(_Meter(pct=10.0)).limit_retry_wait(f"{_429}, Retry-After: 60", 0) == 60.0


def test_without_a_retry_after_the_existing_halt_path_is_untouched_and_the_meter_unread():
    """既有行為逐位元不變的證明之一：沒有 Retry-After ⇒ None，且連額度快取都不讀（零附帶面）。"""
    meter = _Meter(pct=10.0)
    p = _plugin(meter)
    assert p.limit_retry_wait(_429, 0) is None
    assert p.limit_retry_wait("Claude usage limit reached. Your limit resets at 9am", 0) is None
    assert meter.reads == 0
    # 而既有的 halt 判決仍在：
    assert p.evaluate_quota({"failure_reason": _429}).request_halt is True


def test_an_ordinary_failure_with_the_word_retry_after_is_not_a_limit_hit():
    assert _plugin().limit_retry_wait("AssertionError: retry after 60 seconds is wrong", 0) is None


def test_a_retry_after_beyond_the_bound_is_not_retried():
    assert _plugin().limit_retry_wait(f"{_429} retry-after: 301", 0) is None


def test_the_bound_follows_the_knob():
    p = _plugin(max_retry_after_seconds=30)
    assert p.limit_retry_wait(f"{_429} retry-after: 30", 0) == 30.0
    assert p.limit_retry_wait(f"{_429} retry-after: 31", 0) is None


def test_the_retry_budget_follows_the_knob():
    p = _plugin(max_limit_retries=2)
    text = f"{_429} retry-after: 5"
    assert [p.limit_retry_wait(text, n) for n in range(3)] == [5.0, 5.0, None]


@pytest.mark.parametrize("meter", [_Meter(pct=95.0), _Meter(pct=99.0), _Meter(band="halt")],
                         ids=["at-halt-line", "above", "band-halt"])
def test_a_quota_that_is_really_exhausted_is_never_retried(meter):
    """429 是「遙測低估」的證據；但遙測自己已說用完時，退避重打只是在撞同一面牆。"""
    assert _plugin(meter).limit_retry_wait(f"{_429} retry-after: 5", 0) is None


def test_just_below_the_halt_line_is_still_retried():
    assert _plugin(_Meter(pct=94.9)).limit_retry_wait(f"{_429} retry-after: 5", 0) == 5.0


def test_an_unmeasured_quota_does_not_block_the_retry():
    """量不到 ≠ 用完：沒有快取時仍遵循伺服器的 Retry-After。"""
    assert _plugin(_Meter()).limit_retry_wait(f"{_429} retry-after: 5", 0) == 5.0
    assert _plugin(None).limit_retry_wait(f"{_429} retry-after: 5", 0) == 5.0


def test_a_disabled_guard_never_acts():
    assert _plugin(enabled=False).limit_retry_wait(f"{_429} retry-after: 5", 0) is None


def test_a_meter_that_only_implements_read_does_not_break_the_gate():
    """既有／外部注入的 port 可能只有 read()／read_worst_pct()：不得把整條路炸掉。"""
    class _Old:
        def read(self):
            return None

        def read_worst_pct(self):
            return None
    assert _plugin(_Old()).limit_retry_wait(f"{_429} retry-after: 5", 0) == 5.0


def test_the_default_jitter_source_is_random_and_stays_within_the_window():
    p = TokenGuardPlugin(TokenGuardConfig())
    waits = {p.limit_retry_wait(f"{_429} retry-after: 60", 2) for _ in range(20)}
    assert all(60 <= w < 60 + 40 for w in waits)
    assert len(waits) > 1, "預設 rand 恆回同值 ⇒ 沒有 jitter"


def test_evaluate_quota_is_unchanged_by_the_shared_quota_view_refactor():
    """`hard`／`soft` 的判準現在住共用的一處；四個觸發條件的判決與修前逐一相同。"""
    assert _plugin(_Meter(pct=96.0)).evaluate_quota({}).request_halt is True
    assert _plugin(_Meter(band="halt")).evaluate_quota({}).request_halt is True
    assert _plugin(_Meter(pct=71.0)).evaluate_quota({"in_correction_loop": True}).request_halt
    assert _plugin(_Meter(pct=71.0)).evaluate_quota({"in_correction_loop": False}) is None
    assert _plugin(_Meter(pct=10.0)).evaluate_quota({"failure_reason": _429}).request_halt
    assert _plugin(_Meter(pct=10.0)).evaluate_quota({}) is None
