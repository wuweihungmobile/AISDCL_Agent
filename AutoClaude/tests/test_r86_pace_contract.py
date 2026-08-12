"""R86：配速契約（`autosdd_pace.json`）＋引擎側動態決策的機械物。

掌舵者的立案句逐字：「請將演算法落實在**程式機制**，不是光光靠模型判斷」。
⇒ 本檔守的不是「功能會動」，是四條**性質**：
  ① 契約讀寫往返：根層寫什麼，引擎就決定什麼（引擎不重算）。
  ② 陳舊即保守：`measured_at` 過期 ⇒ 走保守側，**不是**沿用、**不是**不設限。
  ③ 缺檔即保守：契約不存在 ⇒ 同上，且**必須出聲**（fail-open 的表徵與修好完全相同）。
  ④ 不得更寬鬆：新機制在任何情境下都不比修前的靜態門檻寬鬆。

每一組都附「合成注入」對照：把缺陷形態注回去，該組必須 FAIL——只有正向斷言的鎖沒有
鑑別力（R75 教訓）。
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from autoclaude.core.orchestration.coordinator import (
    MaxActiveRunsExceeded,
    OrchestrationCoordinator,
)
from autoclaude.core.ports.quota_meter import (
    BAND_HALT,
    BAND_PREPARE,
    BAND_UNMEASURED,
    DEGRADED_CAP,
    PACE_SCHEMA,
    PaceDecision,
    effective_fanout,
)
from autoclaude.infra.adapters.file_quota_meter import (
    DEFAULT_TTL_SECONDS,
    PACE_TTL_SECONDS,
    FileQuotaMeterAdapter,
)
from autoclaude.plugins.token_guard.policy import TokenGuardPlugin
from autoclaude.utils.config import TokenGuardConfig

REPO = Path(__file__).resolve().parents[1]
_ROOT_POLICY = REPO.parent / "tools" / "lib" / "quota_policy.py"


# ─────────────────────────────────────────────────────────────
# fixtures：契約檔的合成器（**永遠不打伺服器**；多組情境一律合成）
# ─────────────────────────────────────────────────────────────
def _pace_payload(cap: int = 8, band: str = "notice", *, age_seconds: float = 0.0,
                  schema: str = PACE_SCHEMA, source: str = "cache", **extra) -> dict:
    measured = datetime.now(UTC) - timedelta(seconds=age_seconds)
    return {"schema": schema, "cap": cap, "band": band, "source": source,
            "measured_at": measured.isoformat(),
            "headroom_pct": 25.0, "headroom_pct_per_hour": 12.5,
            "binding_kind": "session", **extra}


def _write_pace(tmp_path: Path, payload: dict | None) -> FileQuotaMeterAdapter:
    """回傳一個 adapter，其配速契約落在 tmp_path（`payload is None` ＝刻意不寫檔）。"""
    quota_path = tmp_path / "autosdd_quota.json"
    if payload is not None:
        (tmp_path / "autosdd_pace.json").write_text(
            json.dumps(payload), encoding="utf-8", newline="\n")
    return FileQuotaMeterAdapter(str(quota_path))


# ─────────────────────────────────────────────────────────────
# ① 契約讀寫往返：根層寫什麼，引擎就決定什麼
# ─────────────────────────────────────────────────────────────
class TestContractRoundTrip:
    def test_the_engine_reads_back_exactly_what_the_harness_wrote(self, tmp_path):
        meter = _write_pace(tmp_path, _pace_payload(cap=3, band=BAND_PREPARE,
                                                    source="endpoint"))
        assert meter.read_pace() == PaceDecision(3, BAND_PREPARE, "endpoint")

    def test_the_engine_does_not_recompute_the_cap_from_the_percentage(self, tmp_path):
        """🔴 這一條是「演算法只有一個家」的判準本體。

        契約刻意寫一個**與任何水位階梯都不相符**的組合（band=free 卻 cap=1）。若引擎自己
        照 pct 重算階梯，free 帶會給出 8/16 這種數字；照契約走才會拿到 1。
        """
        meter = _write_pace(tmp_path, _pace_payload(cap=1, band="free"))
        assert meter.read_pace().cap == 1

    @pytest.mark.parametrize("static,cap,expected", [
        (5, 8, 5),     # 契約比靜態鬆 ⇒ 靜態說了算（不得被放寬）
        (5, 2, 2),     # 契約比靜態緊 ⇒ 契約說了算（收緊）
        (5, 0, 1),     # halt 帶 ⇒ 夾到 1（停不停是 halt 那一軸的事，不是併發度這一軸）
        (1, 16, 1),
    ])
    def test_the_coordinator_applies_the_contract_at_its_fanout_guard(
            self, tmp_path, static, cap, expected):
        meter = _write_pace(tmp_path, _pace_payload(cap=cap))
        coord = OrchestrationCoordinator(
            bus=object(), brain=object(), executor=object(),
            max_active_runs_per_goal=static, pace_meter=meter)
        assert coord.effective_max_active_runs == expected
        # 靜態那個 property 的語意不得被改掉（4 支既有測試讀它）。
        assert coord.max_active_runs_per_goal == static

    def test_the_guard_really_raises_at_the_contract_limit_not_the_static_one(self, tmp_path):
        """端到端：契約 cap=2、靜態 5 ⇒ 第 2 個並發單位就必須被擋下（修前要到第 5 個）。"""
        meter = _write_pace(tmp_path, _pace_payload(cap=2))
        coord = OrchestrationCoordinator(
            bus=object(), brain=object(), executor=object(),
            max_active_runs_per_goal=5, pace_meter=meter)
        with pytest.raises(MaxActiveRunsExceeded, match="MAX_ACTIVE_RUNS_PER_GOAL=2"):
            coord.run_step(playbook=None, task=None, step_idx=0, active_runs_for_goal=2)


# ─────────────────────────────────────────────────────────────
# ②③ 陳舊／缺檔／壞檔 ⇒ 一律保守，且必須出聲
# ─────────────────────────────────────────────────────────────
class TestUnmeasurableAlwaysDegradesConservatively:
    @pytest.mark.parametrize("payload,why", [
        (None, "缺檔"),
        (_pace_payload(age_seconds=PACE_TTL_SECONDS + 1), "measured_at 過期"),
        (_pace_payload(schema="autosdd.pace/0"), "schema 不符"),
        (_pace_payload(cap=-1), "cap 負數"),
        (_pace_payload(cap=True), "cap 是 bool（isinstance 會把它收成 1）"),
        ({"schema": PACE_SCHEMA, "cap": 8, "band": "free"}, "沒有 measured_at"),
        ({"schema": PACE_SCHEMA, "cap": 8, "measured_at": "x"}, "measured_at 解不出來"),
        ({"nonsense": 1}, "整份形狀不符"),
    ])
    def test_every_unmeasurable_shape_lands_on_the_conservative_floor(
            self, tmp_path, payload, why):
        got = _write_pace(tmp_path, payload).read_pace()
        assert got == PaceDecision(DEGRADED_CAP, BAND_UNMEASURED, "degraded"), why
        # 🔴 絕不是「不設限」：cap 是一個有限、且小於 shipped free 帶（8）的數字。
        assert 1 <= got.cap < 8

    def test_a_corrupt_contract_file_does_not_crash_the_engine(self, tmp_path):
        (tmp_path / "autosdd_pace.json").write_text("{not json", encoding="utf-8")
        meter = FileQuotaMeterAdapter(str(tmp_path / "autosdd_quota.json"))
        assert meter.read_pace().band == BAND_UNMEASURED

    def test_a_future_measured_at_is_refused_instead_of_being_eternally_fresh(self, tmp_path):
        """時鐘偏移**絕不允許把預算調高**（同根層對負 minutes 的處置）。

        寫一個「未來一小時」的 measured_at：不夾的話它永遠算「剛量到」。
        """
        got = _write_pace(tmp_path, _pace_payload(age_seconds=-3600)).read_pace()
        assert got.band == BAND_UNMEASURED

    def test_the_failure_is_said_out_loud_not_silently_reused(self, tmp_path, caplog):
        """🔴「失效必須可偵測」：本 repo 判過 fail-open 的表徵與修好完全相同。"""
        with caplog.at_level(logging.WARNING):
            _write_pace(tmp_path, None).read_pace()
        assert [r for r in caplog.records if "[pace]" in r.message], (
            "契約量不到卻一聲不吭 ⇒ 失效變成靜默的")

    def test_the_judge_can_fail_the_permissive_implementation(self, tmp_path):
        """合成注入：把「量不到 ⇒ 不設限」那個缺陷形態注回去，上面的判準必須抓到。"""
        class _FailOpen(FileQuotaMeterAdapter):
            def read_pace(self):        # 缺陷形態：量不到就當成「額度很充足」
                return PaceDecision(999, "free", "degraded")

        bad = _FailOpen(str(tmp_path / "autosdd_quota.json")).read_pace()
        assert not (bad == PaceDecision(DEGRADED_CAP, BAND_UNMEASURED, "degraded"))
        assert not (1 <= bad.cap < 8)


class TestPaceTtlIsBoundedByItsInput:
    def test_a_derived_decision_may_not_outlive_the_measurement_it_derives_from(self):
        """🔴 結構性不變式，不是「挑一個看起來合理的分鐘數」。

        配速契約是 `autosdd_quota.json` 的**衍生物**。若它的 TTL ≥ 原始量測的 TTL，就會
        出現「所依據的快取都已作廢、決策卻還算有效」——而那個組合的外觀與「剛量到」相同。
        """
        assert 0.0 < PACE_TTL_SECONDS < DEFAULT_TTL_SECONDS

    def test_freshness_comes_from_the_payload_not_the_file_mtime(self, tmp_path):
        """🔴 與 `autosdd_quota.json` 刻意不同的判準（不是漏抄）。

        那份快取由量測者自己整檔重寫 ⇒ mtime ≡ 量測時刻。本契約是衍生物：根層可以拿一份
        很舊的快取**現在**算出決策並立刻寫檔 ⇒ mtime 全新、底層量測很舊。這裡構造的正是
        那個組合（檔案剛寫、measured_at 很舊），mtime 判準會放行，payload 判準必須拒絕。
        """
        path = tmp_path / "autosdd_pace.json"
        path.write_text(json.dumps(_pace_payload(age_seconds=PACE_TTL_SECONDS + 60)),
                        encoding="utf-8")
        assert datetime.now(UTC).timestamp() - path.stat().st_mtime < PACE_TTL_SECONDS
        assert FileQuotaMeterAdapter(str(tmp_path / "autosdd_quota.json")
                                     ).read_pace().band == BAND_UNMEASURED


# ─────────────────────────────────────────────────────────────
# ④ 不得更寬鬆（結構性，不是紀律）
# ─────────────────────────────────────────────────────────────
class TestTheNewMechanismIsNeverMorePermissive:
    @pytest.mark.parametrize("static", [1, 2, 5, 8, 16, 64])
    @pytest.mark.parametrize("cap", [0, 1, 2, 4, 8, 16, 999])
    def test_窮舉_no_combination_is_looser_than_the_old_static_threshold(self, static, cap):
        old = static                                    # 修前：只讀靜態上限
        new = effective_fanout(static, PaceDecision(cap, "notice", "cache"))
        assert new <= max(1, old)

    def test_no_port_injected_means_bit_for_bit_the_old_behaviour(self):
        """功能沒開 ⇒ 零行為變化（同本 repo 既有慣例 `quota_meter=None`）。"""
        assert effective_fanout(5, None) == 5
        coord = OrchestrationCoordinator(bus=object(), brain=object(), executor=object(),
                                         max_active_runs_per_goal=5)
        assert coord.effective_max_active_runs == 5

    def test_a_degraded_contract_is_stricter_than_the_old_behaviour_not_looser(self, tmp_path):
        meter = _write_pace(tmp_path, None)
        coord = OrchestrationCoordinator(bus=object(), brain=object(), executor=object(),
                                         max_active_runs_per_goal=5, pace_meter=meter)
        assert coord.effective_max_active_runs == DEGRADED_CAP < 5

    def test_the_floor_is_one_so_a_halt_band_cannot_deadlock_the_engine(self):
        """cap=0 在**併發度**這一軸不得變成死鎖——停不停是 halt 那一軸的決定。"""
        assert effective_fanout(5, PaceDecision(0, BAND_HALT, "cache")) == 1


# ─────────────────────────────────────────────────────────────
# 引擎側「live」消費點：TokenGuardPlugin（production 真的有註冊的那一個）
# ─────────────────────────────────────────────────────────────
class _BandOnlyMeter:
    """只回 band 的假 port（`read_worst_pct` 刻意回 None＝水位那一軸量不到）。"""

    def __init__(self, band: str):
        self._band = band

    def read(self):
        return None

    def read_worst_pct(self):
        return None

    def read_pace(self):
        return PaceDecision(4, self._band, "cache")


class TestTheBandFromTheContractDrivesTheLiveGuard:
    def _plugin(self, band):
        return TokenGuardPlugin(token_guard_cfg=TokenGuardConfig(),
                                quota_meter=_BandOnlyMeter(band))

    def test_halt_band_halts_even_when_the_percentage_axis_is_unmeasurable(self):
        """🔴 修前：pct 量不到 ⇒ 兩道門都不成立 ⇒ 無動作。現在根層的結論接得上。"""
        req = self._plugin(BAND_HALT).evaluate_quota({})
        assert req is not None and req.request_halt and "band=halt" in req.reason

    def test_prepare_band_only_stops_optional_spend(self):
        """收斂帶的語意：只停掉「可選支出」（CORRECTION 重試），正常步驟仍放行。"""
        plugin = self._plugin(BAND_PREPARE)
        assert plugin.evaluate_quota({"in_correction_loop": True}) is not None
        assert plugin.evaluate_quota({}) is None

    @pytest.mark.parametrize("band", [BAND_UNMEASURED, "free", "notice", "converge"])
    def test_bands_the_engine_has_no_action_for_change_nothing(self, band):
        """🔴 **不對一個沒量到的值 halt**（同根層「量不到永不 halt」）。

        `converge`／`notice` 刻意也不接：那兩帶的動作是「少派 agent」，而那是 cap 那一軸
        （coordinator）的事；在這裡接上去就是同一件事有兩個家。
        """
        plugin = self._plugin(band)
        assert plugin.evaluate_quota({}) is None
        assert plugin.evaluate_quota({"in_correction_loop": True}) is None

    def test_a_meter_without_read_pace_does_not_explode(self):
        """既有／外部注入的 port 只實作 read()/read_worst_pct() ⇒ 不得炸掉整條額度軸。"""
        class _Old:
            def read(self):
                return None

            def read_worst_pct(self):
                return None

        assert TokenGuardPlugin(token_guard_cfg=TokenGuardConfig(),
                                quota_meter=_Old()).evaluate_quota({}) is None

    def test_limit_text_still_wins_without_any_contract(self):
        """撞線文字那條線**不吃契約** ⇒ 契約缺席之下仍有一層（離線、零 token）。"""
        plugin = self._plugin(BAND_UNMEASURED)
        assert plugin.evaluate_quota(
            {"failure_reason": "Claude usage limit reached"}) is not None


# ─────────────────────────────────────────────────────────────
# 兩側常數的鏡射：引擎不得自養一組數字（同既有 ACQ-02 體例，讀原始碼不 import）
# ─────────────────────────────────────────────────────────────
class TestDegradedCapMirrorsTheRootDeclaration:
    def test_the_shipped_degraded_cap_equals_the_root_env_spec_default(self):
        src = _ROOT_POLICY.read_text(encoding="utf-8")
        m = re.search(r'EnvVar\("AUTOSDD_QUOTA_DEGRADED_CAP",\s*"[^"]*",\s*(\d+)', src)
        assert m, "根層 ENV_SPEC 找不到 AUTOSDD_QUOTA_DEGRADED_CAP ⇒ 這條鏡射鎖已靜默歸零"
        assert DEGRADED_CAP == int(m.group(1)) == TokenGuardConfig().quota_degraded_cap

    def test_the_env_key_really_takes_effect(self):
        with patch.dict(os.environ, {"AUTOSDD_QUOTA_DEGRADED_CAP": "2"}):
            assert TokenGuardConfig().quota_degraded_cap == 2

    def test_the_band_literals_match_the_root_ones(self):
        src = _ROOT_POLICY.read_text(encoding="utf-8")
        for literal in (BAND_HALT, BAND_PREPARE):
            assert f'"{literal}"' in src, (
                f"帶別字面 {literal!r} 在根層找不到 ⇒ 兩側對同一份契約的解讀已漂開")

    def test_the_wiring_passes_the_configured_floor_into_the_adapter(self):
        from autoclaude.core.wiring import build_quota_meter
        assert build_quota_meter(2).read_pace().cap == 2   # 契約不存在 ⇒ 落在地板上
        assert build_quota_meter().read_pace().cap == DEGRADED_CAP


# ─────────────────────────────────────────────────────────────
# 兩份 `.env` 的分歧偵測（R86 掌舵者點名；缺陷①「分歧靜默」）
# ─────────────────────────────────────────────────────────────
class TestTwoEnvFilesDivergeLoudlyNotSilently:
    def _files(self, tmp_path, ac_text: str, root_text: str, monkeypatch):
        from autoclaude.utils import config as cfgmod
        ac, root = tmp_path / "ac" / ".env", tmp_path / ".env"
        ac.parent.mkdir(exist_ok=True)
        ac.write_text(ac_text, encoding="utf-8", newline="\n")
        root.write_text(root_text, encoding="utf-8", newline="\n")
        monkeypatch.setattr(cfgmod, "_ENV_FILES", (ac, root))
        for k in ("AUTOSDD_QUOTA_HALT_PCT", "AUTOSDD_QUOTA_CONVERGE_PCT"):
            monkeypatch.delenv(k, raising=False)
        return cfgmod

    def test_a_silent_divergence_is_reported_once_with_both_values(
            self, tmp_path, monkeypatch, caplog):
        cfgmod = self._files(tmp_path, "AUTOSDD_QUOTA_HALT_PCT=93\n",
                             "AUTOSDD_QUOTA_HALT_PCT=91\n", monkeypatch)
        with caplog.at_level(logging.WARNING):
            assert cfgmod.TokenGuardConfig().quota_halt_pct == 93.0   # 引擎側覆寫仍然贏
        msgs = [r.getMessage() for r in caplog.records if "[env 分歧]" in r.getMessage()]
        assert len(msgs) == 1 and "AUTOSDD_QUOTA_HALT_PCT" in msgs[0]
        assert "'93'" in msgs[0] and "'91'" in msgs[0], "沒說出兩邊各是什麼值＝沒用的告警"

    def test_an_explicit_override_marker_suppresses_the_noise(
            self, tmp_path, monkeypatch, caplog):
        """治法不是禁止分歧（那會殺掉合法覆寫），是**讓分歧必須是明示的**。"""
        cfgmod = self._files(
            tmp_path, "AUTOSDD_QUOTA_HALT_PCT=93  # override-ok: 無人看管跑批要更保守\n",
            "AUTOSDD_QUOTA_HALT_PCT=91\n", monkeypatch)
        with caplog.at_level(logging.WARNING):
            assert cfgmod.TokenGuardConfig().quota_halt_pct == 93.0
        assert [r for r in caplog.records if "[env 分歧]" in r.getMessage()] == []

    def test_identical_values_are_not_reported(self, tmp_path, monkeypatch, caplog):
        """沒有鑑別力的鎖比沒有鎖更糟：值相同時**不得**噪音。"""
        cfgmod = self._files(tmp_path, "AUTOSDD_QUOTA_HALT_PCT=91\n",
                             "AUTOSDD_QUOTA_HALT_PCT=91  # 基底\n", monkeypatch)
        with caplog.at_level(logging.WARNING):
            cfgmod.TokenGuardConfig()
        assert [r for r in caplog.records if "[env 分歧]" in r.getMessage()] == []

    def test_secret_values_can_never_reach_the_warning_path(
            self, tmp_path, monkeypatch, caplog):
        """🔴 機密不外洩——而且是**結構性**保證，不是靠「像機密的鍵名」關鍵詞表遮罩。

        `_quota_env` 的呼叫點是寫死的白名單（實查全 `autoclaude/**` 只有 3 個，全部
        `AUTOSDD_QUOTA_*`）⇒ 機密鍵的值結構上到不了這條會 log 的路徑。
        這裡在兩份 `.env` 放三種**值不同**的假機密：只要有任何一個值出現在 log 裡就 FAIL。
        （為什麼不能複用根層 `tools/lib/secret_scan.py` 的機密鍵判準：`.importlinter` 的
        no-harness-import contract 明文禁止 `autoclaude` import `tools.*`；抄一份就是
        「同一份知識住兩個家」＝本 repo 的頭號病。⇒ 只能讓機密結構上到不了。）
        """
        fakes = {"MINIMAX_API_KEY": ("sk-AAAAdeadbeefLEAK1", "sk-BBBBdeadbeefLEAK2"),
                 "POSTGRES_PASSWORD": ("p4ssw0rdLEAK3", "p4ssw0rdLEAK4"),
                 "AUTOCLAUDE_DB_DSN": ("postgresql://u:LEAK5@db.example.com/x",
                                       "postgresql://u:LEAK6@db2.example.com/x")}
        ac_lines = [f"{k}={v[0]}" for k, v in fakes.items()] + ["AUTOSDD_QUOTA_HALT_PCT=93"]
        root_lines = [f"{k}={v[1]}" for k, v in fakes.items()] + ["AUTOSDD_QUOTA_HALT_PCT=91"]
        cfgmod = self._files(tmp_path, "\n".join(ac_lines) + "\n",
                             "\n".join(root_lines) + "\n", monkeypatch)
        with caplog.at_level(logging.WARNING):
            cfgmod.TokenGuardConfig()
        blob = "\n".join(r.getMessage() for r in caplog.records)
        # 配額鍵的分歧照樣要被講出來（否則本測試會在「什麼都不印」的實作下假綠）。
        assert "AUTOSDD_QUOTA_HALT_PCT" in blob
        leaked = [v for pair in fakes.values() for v in pair if v in blob]
        assert leaked == [], f"機密值外洩到 log：{leaked}"
        assert [k for k in fakes if k in blob] == [], "連機密鍵名都不該出現在這條路徑上"

    def test_the_two_layer_inheritance_contract_is_intact(self, tmp_path, monkeypatch):
        """🔴 掌舵者裁決：**不合併成一份**。這一條把「三層繼承」釘住，防後人順手拆掉。"""
        cfgmod = self._files(tmp_path, "AUTOSDD_QUOTA_HALT_PCT=93\n",
                             "AUTOSDD_QUOTA_CONVERGE_PCT=55\nAUTOSDD_QUOTA_HALT_PCT=91\n",
                             monkeypatch)
        cfg = cfgmod.TokenGuardConfig()
        assert cfg.quota_throttle_pct == 55.0    # 只有根層有 ⇒ 繼承
        assert cfg.quota_halt_pct == 93.0        # 兩份都有 ⇒ AutoClaude 那份贏
        with patch.dict(os.environ, {"AUTOSDD_QUOTA_HALT_PCT": "97"}):
            assert cfgmod.TokenGuardConfig().quota_halt_pct == 97.0   # 真 env 贏過兩份檔

    def test_the_example_file_says_out_loud_that_it_is_an_override_layer(self):
        """檔名沒改（跨檔參照 19 處，改名不在本輪射程）⇒ 角色必須在文字上明示。"""
        head = (REPO / ".env.example").read_text(encoding="utf-8").splitlines()[0]
        assert "覆寫層" in head, "第一行沒說出它是覆寫層 ⇒ 讀者會以為它是獨立用途的 env"

    def test_the_example_file_does_not_hardcode_the_drifting_overlap_list(self):
        """會漂移的量測值一律不寫死，只寫哪一支載具會印出它。"""
        text = (REPO / ".env.example").read_text(encoding="utf-8")
        assert "comm -12" in text
