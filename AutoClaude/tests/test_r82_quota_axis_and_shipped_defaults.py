"""R82 A4 包的機械物：出廠預設可跑性（ACB-01/02、ACC-01/02）＋額度水位軸（ACQ-01/02/04/05）。

每一組都附「合成注入」對照：把缺陷形態注回去，該組必須 FAIL。
不是只測「擋得住」，也測「不亂擋」——只有正向斷言的鎖沒有鑑別力（R75 教訓）。
"""
from __future__ import annotations

import ast
import configparser
import json
import os
import re
import shutil
import subprocess
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from autoclaude.core.ports.quota_meter import (
    QuotaReading,
    is_quota_limit_text,
    resume_wait_seconds,
)
from autoclaude.infra.adapters.file_quota_meter import SCHEMA, FileQuotaMeterAdapter
from autoclaude.plugins.token_guard.policy import TokenGuardPlugin
from autoclaude.utils.config import (
    AppConfig,
    ClaudeConfig,
    NotificationConfig,
    TokenGuardConfig,
    load_config,
)
from autoclaude.utils.notifier import DEFAULT_DURATION_SECONDS

REPO = Path(__file__).resolve().parents[1]
SHIPPED_CONFIG = REPO / "config.yaml"
EXAMPLE_CONFIG = REPO / "config.yaml.example"


def _shipped(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


# ─────────────────────────────────────────────────────────────
# ACB-01（P0）：extra_args 只能放 `claude --help` 真的認得的旗標
# ─────────────────────────────────────────────────────────────
def _unknown_flags(args: list[str], help_text: str) -> list[str]:
    """判準本體（測試自持，不吃生產碼預算）：args 中以 `--` 開頭卻不在 help 裡的旗標。"""
    bad = []
    for a in args:
        if not a.startswith("--"):
            continue
        name = a.split("=", 1)[0]
        if not re.search(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", help_text):
            bad.append(name)
    return bad


class TestClaudeCliFlagsAreReal:
    def test_the_judge_itself_catches_the_bug_we_are_fixing(self):
        """合成注入：`--yes` 這個實際缺陷形態必須被判準抓到；合法旗標必須放行。

        沒有這一條，下面兩個測試在「判準永遠回空清單」時也會綠。
        """
        help_text = "  --permission-mode <mode>  ...\n  -p, --print  ...\n"
        assert _unknown_flags(["--yes"], help_text) == ["--yes"]
        assert _unknown_flags(["--permission-mode", "bypassPermissions"], help_text) == []

    def test_code_default_extra_args_carries_no_flag(self):
        # `--yes` 不是 Claude Code 的旗標，實測 `claude --yes mcp list` → rc=1
        # `error: unknown option '--yes'` ⇒ 出廠設定下每個步驟都在第一秒失敗。
        assert ClaudeConfig().extra_args == []

    @pytest.mark.parametrize("cfg_path", [SHIPPED_CONFIG, EXAMPLE_CONFIG])
    def test_shipped_yaml_extra_args_carries_no_bogus_flag(self, cfg_path: Path):
        args = (_shipped(cfg_path).get("claude") or {}).get("extra_args") or []
        assert "--yes" not in args, f"{cfg_path.name} 仍帶非法旗標 --yes"

    def test_every_shipped_flag_exists_in_the_real_cli_help(self):
        """權威判準：拿 `claude --help` 當 fixture 逐旗標比對。

        🔴 刻意不用 `claude <flag> --version` 驗——實測 `--version` 會短路旗標檢查
        （`claude --definitelynotaflag --version` 也回 rc=0），那是假綠。
        """
        exe = shutil.which("claude")
        if exe is None:
            pytest.skip("本機無 claude CLI（PATH 找不到）；此判準需要真的 CLI help 當 fixture")
        proc = subprocess.run(  # noqa: S603
            [exe, "--help"], capture_output=True, text=True, timeout=120,
            encoding="utf-8", errors="replace",   # locale 預設在 cp950 上會炸／降解
        )
        assert proc.returncode == 0, f"claude --help rc={proc.returncode}"
        help_text = proc.stdout + proc.stderr
        candidates = list(ClaudeConfig().extra_args)
        for cfg_path in (SHIPPED_CONFIG, EXAMPLE_CONFIG):
            candidates += (_shipped(cfg_path).get("claude") or {}).get("extra_args") or []
        assert _unknown_flags(candidates, help_text) == []


# ─────────────────────────────────────────────────────────────
# ACC-02：出廠 config.yaml 不得用較小的 context_patterns 蓋掉程式碼預設
# ─────────────────────────────────────────────────────────────
class TestShippedConfigDoesNotShrinkContextPatterns:
    def test_shipped_yaml_patterns_are_a_superset_of_code_defaults(self):
        shipped = (_shipped(SHIPPED_CONFIG).get("token_guard") or {}).get("context_patterns")
        if shipped is None:
            return  # 刪掉整個鍵＝單一 SSOT，就是本輪採用的修法
        assert set(TokenGuardConfig().context_patterns) <= set(shipped)

    @pytest.mark.parametrize(
        "line", ["[STATS: usage 92%]", "Token usage: 190000 tokens / max 200000"],
    )
    def test_formats_that_were_silently_invisible_are_detected_under_shipped_config(self, line):
        """這兩行在修前的出廠 config 下回 None ⇒ Token Guard 兩道門永遠不觸發。

        合成注入：把 config.yaml 的 4 條 regex 版塞回去，本測試必 FAIL（下一個測試證明）。
        """
        from autoclaude.utils.token_tracker import build_patterns, extract_context_pct
        cfg = load_config(str(SHIPPED_CONFIG))
        pats = build_patterns(cfg.token_guard.context_patterns)
        assert extract_context_pct(line, pats) is not None

    def test_the_old_four_pattern_set_really_was_blind(self):
        """反向對照：舊的 4 條確實看不到那兩種格式（證明上一條有鑑別力，不是恆真）。"""
        from autoclaude.utils.token_tracker import build_patterns, extract_context_pct
        old_four = [
            r"(\d+(?:\.\d+)?)\s*%\s*(?:context|token)",
            r"(?:context|token)\w*[\s:]+(\d+(?:\.\d+)?)\s*%",
            r"(\d+)\s*/\s*(\d+)\s*tokens?",
            r"\[CONTEXT_USAGE:\s*(\d+(?:\.\d+)?)%\]",
        ]
        pats = build_patterns(old_four)
        assert extract_context_pct("[STATS: usage 92%]", pats) is None


# ─────────────────────────────────────────────────────────────
# ACC-01：預設不彈桌面通知 + env 雙向開關 + 停留秒數可設
# ─────────────────────────────────────────────────────────────
class TestDesktopNotificationIsOffByDefault:
    def test_code_default_is_off(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AUTOCLAUDE_DESKTOP_NOTIFY", None)
            assert NotificationConfig().enabled is False

    @pytest.mark.parametrize("cfg_path", [SHIPPED_CONFIG, EXAMPLE_CONFIG])
    def test_shipped_yaml_is_off(self, cfg_path: Path):
        assert (_shipped(cfg_path).get("notification") or {}).get("enabled") is False

    @pytest.mark.parametrize(
        "raw,expected",
        [("1", True), ("true", True), ("on", True), ("0", False), ("no", False)],
    )
    def test_env_switch_is_two_way(self, raw, expected):
        with patch.dict(os.environ, {"AUTOCLAUDE_DESKTOP_NOTIFY": raw}):
            assert NotificationConfig().enabled is expected

    def test_env_example_documents_the_switch(self):
        text = (REPO / ".env.example").read_text(encoding="utf-8")
        assert "AUTOCLAUDE_DESKTOP_NOTIFY" in text

    def test_popup_lifetime_is_short_enough_not_to_hold_the_process(self):
        # plyer 的 Windows 後端在**非 daemon** 執行緒裡 sleep(timeout) ⇒ 這個數字就是
        # 「跑完之後行程還要多活多久」。原硬編 10 秒。
        assert DEFAULT_DURATION_SECONDS <= 3
        assert NotificationConfig().duration_seconds <= 3

    def test_plugin_passes_the_configured_duration_through(self):
        from autoclaude.core.hookspec import HookContext, KernelPhase
        from autoclaude.plugins import NotificationPlugin
        cfg = AppConfig()
        cfg.notification.duration_seconds = 2
        plugin = NotificationPlugin(enabled=True, app_config=cfg)
        ctx = HookContext(
            phase=KernelPhase.POST_RUN,
            playbook=type("P", (), {"project": "x"})(),
            payload={"success": True},
        )
        with patch("autoclaude.plugins.notification_plugin.notify") as spy:
            plugin.on_event(ctx)
        assert spy.call_args.kwargs["duration"] == 2

    def test_win10toast_is_not_attempted_off_windows(self):
        """修前 notifier 對非 Windows 也呼叫 win10toast，只靠 import 失敗兜底。"""
        import autoclaude.utils.notifier as nf
        with patch.object(nf, "_try_plyer", return_value=False), \
             patch.object(nf, "is_macos", return_value=False), \
             patch.object(nf, "is_windows", return_value=False), \
             patch.object(nf, "_try_win10toast", return_value=True) as toast:
            nf.notify("t", "m")
        toast.assert_not_called()


# ─────────────────────────────────────────────────────────────
# ACQ-01：QuotaMeterPort 檔案契約（量不到一律 None，絕不回 0.0）
# ─────────────────────────────────────────────────────────────
def _write_quota(tmp_path: Path, payload: dict, age_seconds: float = 0.0) -> Path:
    p = tmp_path / "autosdd_quota.json"
    p.write_text(json.dumps(payload), encoding="utf-8", newline="\n")
    if age_seconds:
        stamp = time.time() - age_seconds
        os.utime(p, (stamp, stamp))
    return p


def _axis(kind: str, pct: float, resets_at: str | None) -> dict:
    return {"kind": kind, "pct": pct, "resets_at": resets_at, "group": None}


# R82：檔案契約由頂層純量升到 `axes[]`。斷言的**性質**一條都沒放寬，只有形狀跟著契約走。
_GOOD = {"schema": SCHEMA,
         "axes": [_axis("weekly_all", 54.0, "2026-08-14T21:59:59.503474+00:00")]}


class TestFileQuotaMeterAdapter:
    def test_reads_the_real_file_contract(self, tmp_path):
        r = FileQuotaMeterAdapter(str(_write_quota(tmp_path, _GOOD))).read()
        assert r == QuotaReading(54.0, "weekly_all", "2026-08-14T21:59:59.503474+00:00")

    @pytest.mark.parametrize(
        "payload",
        [
            {"axes": [_axis("session", 50.0, None)]},                    # 缺 schema
            {"schema": "autosdd.quota/999",
             "axes": [_axis("session", 50.0, None)]},                    # schema 不符
            {"schema": "autosdd.quota/1", "pct": 50.0, "kind": "session"},  # 舊形狀
            {"schema": SCHEMA, "axes": [_axis("session", True, None)]},  # bool 偽裝成數字
            {"schema": SCHEMA, "axes": [_axis("session", "50", None)]},  # 字串
            {"schema": SCHEMA, "axes": [{"kind": "session"}]},           # 沒有 pct
            {"schema": SCHEMA, "axes": []},                              # 一條軸都沒有
            {"schema": SCHEMA},                                          # 沒有 axes
        ],
    )
    def test_unreadable_payloads_are_none_never_zero(self, tmp_path, payload):
        r = FileQuotaMeterAdapter(str(_write_quota(tmp_path, payload))).read()
        # 🔴 這一條是本組的重點：回 0.0 代表「額度很充足」，會讓所有門檻靜默失效。
        assert r is None

    def test_the_shortest_horizon_axis_wins_not_the_highest_percentage(self, tmp_path):
        """🔴 M8：本 adapter 唯一的消費者問的是「要等多久」，所以選軸只能看期程。

        修前讀的是量測器用 `worst()`（pct 數值**最大**、與期程無關）投影上來的頂層桶
        ⇒ 這一份 payload 會選中 weekly_all(99%)，而 `resume_wait_seconds` 對它回 None
        （不在 _WAITABLE_KINDS）⇒ AutoResumeService 的額度軸**實質恆回 None**、永遠
        回落寫死延遲。也就是說那條線壞掉是完全靜默的：`None` 在本檔被釘成正確行為。
        """
        now = datetime.now(UTC)
        payload = {"schema": SCHEMA, "axes": [
            _axis("weekly_all", 99.0, (now + timedelta(days=5)).isoformat()),
            _axis("session", 96.0, (now + timedelta(minutes=6)).isoformat()),
            _axis("spend", 88.0, None)]}
        reading = FileQuotaMeterAdapter(str(_write_quota(tmp_path, payload))).read()
        assert reading is not None and reading.kind == "session"
        assert resume_wait_seconds(reading, now=now) == pytest.approx(360, abs=2)

    def test_an_axis_without_a_reset_never_outranks_one_that_has_one(self, tmp_path):
        """反向對照：`resets_at=None`＝「沒有 reset 可以等」，不得被當成最近的那一個。"""
        now = datetime.now(UTC)
        payload = {"schema": SCHEMA, "axes": [
            _axis("spend", 99.0, None),
            _axis("five_hour", 12.0, (now + timedelta(hours=3)).isoformat())]}
        reading = FileQuotaMeterAdapter(str(_write_quota(tmp_path, payload))).read()
        assert reading is not None and reading.kind == "five_hour"

    def test_missing_file_is_none(self, tmp_path):
        assert FileQuotaMeterAdapter(str(tmp_path / "nope.json")).read() is None

    def test_corrupt_json_is_none(self, tmp_path):
        p = tmp_path / "autosdd_quota.json"
        p.write_text("{not json", encoding="utf-8", newline="\n")
        assert FileQuotaMeterAdapter(str(p)).read() is None

    def test_stale_reading_is_refused(self, tmp_path):
        p = _write_quota(tmp_path, _GOOD, age_seconds=3600)
        assert FileQuotaMeterAdapter(str(p), ttl_seconds=1800).read() is None
        # 反向對照：TTL 放寬後同一個檔就讀得到 ⇒ 上一行是 TTL 擋的，不是別的原因。
        assert FileQuotaMeterAdapter(str(p), ttl_seconds=7200).read() is not None


    def test_the_two_selection_criteria_are_not_the_same_question(self, tmp_path):
        """🔴 R82／C3 的本體：兩個準則答案**不同**，而且只有一個越過門檻。

        修前只有一個 `read()`（選 horizon 最短那一軸），`evaluate_quota` 拿它的 `.pct`
        當純量比 95 ⇒ 這一份 payload 下引擎讀到 10%、**什麼都不做**，而額度其實已經
        燒到 96%。既有的 R82 測試對這個缺陷零鑑別力：它的 payload 兩軸都 ≥95，選錯軸
        也照樣 halt。
        """
        now = datetime.now(UTC)
        payload = {"schema": SCHEMA, "axes": [
            _axis("weekly_all", 96.0, (now + timedelta(hours=3)).isoformat()),
            _axis("session", 10.0, (now + timedelta(minutes=20)).isoformat())]}
        meter = FileQuotaMeterAdapter(str(_write_quota(tmp_path, payload)))
        assert meter.read().kind == "session"              # 「要等多久」→ 最先 reset
        assert meter.read_worst_pct().kind == "weekly_all"  # 「還剩多少」→ 最緊的那條
        # 只有後者越門檻 ⇒ 這一組 payload 真的分得開兩個準則（不是恆真的斷言）。
        assert meter.read().pct < TokenGuardConfig().quota_halt_pct
        assert meter.read_worst_pct().pct >= TokenGuardConfig().quota_halt_pct
        req = TokenGuardPlugin(quota_meter=meter).evaluate_quota({})
        assert req is not None and req.request_halt is True

    def test_the_two_schema_literals_must_move_together(self):
        """🔴 M8：量測器（唯一寫者）與本 adapter（讀者）的 schema 必須相等。

        只升一邊時 adapter 對每一份新快取回 `None`＝「量不到」，而 `None` 被上面那組
        測試釘成**正確行為** ⇒ 失效全綠、完全靜默。這一條是那個縫的唯一觀測者。
        判準刻意讀量測器的原始碼（不 import）：`autoclaude` 反向依賴 harness 是
        `.importlinter` 的 forbidden contract，見 TestNoHarnessImport。
        """
        meter_src = (REPO.parent / "tools" / "lib" / "quota_meter.py").read_text(
            encoding="utf-8")
        declared = re.search(r'^SCHEMA = "([^"]+)"', meter_src, re.MULTILINE)
        assert declared, "量測器的 SCHEMA 宣告找不到了 ⇒ 這條鎖已靜默歸零"
        assert declared.group(1) == SCHEMA


class TestQuotaThresholdsAreNotTheContextThresholds:
    def test_defaults_are_the_shared_ladder_values_and_independent(self):
        cfg = TokenGuardConfig()
        # 🔴 R82（C3）：throttle 由 80 下修到 70＝根層階梯的 converge（「開始收斂」）。
        # 只准往下（更早停掉可選支出）；halt 95 是安全線，不得放寬。
        assert (cfg.quota_throttle_pct, cfg.quota_halt_pct) == (70.0, 95.0)
        # 不共用物件／不共用值域：改 context 那一軸不得動到額度那一軸。
        cfg2 = TokenGuardConfig(compact_threshold_pct=10.0, halt_threshold_pct=20.0)
        assert (cfg2.quota_throttle_pct, cfg2.quota_halt_pct) == (70.0, 95.0)

    def test_quota_halt_must_exceed_quota_throttle(self):
        with pytest.raises(ValueError, match="quota_halt_pct"):
            TokenGuardConfig(quota_throttle_pct=90.0, quota_halt_pct=90.0)


# ─────────────────────────────────────────────────────────────
# R82 / C3：門檻只有一個家（根層 ENV_SPEC），AutoClaude 這一側是鏡射不是複本
# ─────────────────────────────────────────────────────────────
_ROOT_POLICY_SRC = (REPO.parent / "tools" / "lib" / "quota_policy.py").read_text(
    encoding="utf-8")


def _root_env_default(name: str) -> float:
    """從根層 `ENV_SPEC` 的原始碼取出某個鍵的出廠預設（**不 import**，見 ACQ-02）。"""
    m = re.search(rf'EnvVar\("{re.escape(name)}",\s*"[^"]*",\s*([\d.]+)', _ROOT_POLICY_SRC)
    assert m, f"根層 ENV_SPEC 找不到 {name} ⇒ 這條鏡射鎖已靜默歸零"
    return float(m.group(1))


class TestQuotaThresholdsComeFromTheSharedDeclaration:
    """🔴 兩側**不得各養一組數字**。AutoClaude 不能 import harness（ACQ-02 forbidden
    contract），所以「同一個家」只能靠：① 同一組環境變數名；② 預設值相等，而②由本類
    讀根層原始碼比對——同 `test_the_two_schema_literals_must_move_together` 的體例。
    只改一邊時的失效是靜默的：兩個引擎對同一份快取給出不同的 band，而兩邊都全綠。
    """

    def test_the_judge_can_actually_read_the_root_declaration(self):
        # 判準自證：讀不到就必須爆，而不是回一個看起來合理的數字。
        assert _root_env_default("AUTOSDD_QUOTA_HALT_PCT") == 95.0
        with pytest.raises(AssertionError):
            _root_env_default("AUTOSDD_QUOTA_NO_SUCH_KEY")

    def test_shipped_defaults_equal_the_root_ladder(self):
        cfg = TokenGuardConfig()
        assert cfg.quota_throttle_pct == _root_env_default("AUTOSDD_QUOTA_CONVERGE_PCT")
        assert cfg.quota_halt_pct == _root_env_default("AUTOSDD_QUOTA_HALT_PCT")

    @pytest.mark.parametrize("name,attr", [
        ("AUTOSDD_QUOTA_CONVERGE_PCT", "quota_throttle_pct"),
        ("AUTOSDD_QUOTA_HALT_PCT", "quota_halt_pct"),
    ])
    def test_a_real_environment_variable_takes_effect(self, name, attr):
        with patch.dict(os.environ, {name: "63" if attr.endswith("throttle_pct") else "88"}):
            assert getattr(TokenGuardConfig(), attr) == (
                63.0 if attr.endswith("throttle_pct") else 88.0)

    def test_the_env_file_takes_effect_and_autoclaude_wins_over_the_root(self, tmp_path,
                                                                        monkeypatch):
        """🔴 掌舵者要的是「改 autoclaude/.env 就生效」，不是「改 .env.example」。

        兩份 `.env` 的關係是**繼承 ＋ 覆寫**：根層當基底、AutoClaude 那份覆寫它。
        合成注入驗紅：把 `_ENV_FILES` 改回只讀 os.environ，本測試三個斷言全部 FAIL。
        """
        from autoclaude.utils import config as cfgmod
        ac, root = tmp_path / "ac" / ".env", tmp_path / ".env"
        ac.parent.mkdir()
        # 行內註解刻意留著：使用者 `copy .env.example .env` 之後手加註解是常態。
        root.write_text("AUTOSDD_QUOTA_CONVERGE_PCT=55   # 基底\n"
                        "AUTOSDD_QUOTA_HALT_PCT=91       # 基底\n",
                        encoding="utf-8", newline="\n")
        ac.write_text("AUTOSDD_QUOTA_HALT_PCT=93  # 引擎側覆寫\n",
                      encoding="utf-8", newline="\n")
        monkeypatch.setattr(cfgmod, "_ENV_FILES", (ac, root))
        with patch.dict(os.environ, {}, clear=False):
            for k in ("AUTOSDD_QUOTA_CONVERGE_PCT", "AUTOSDD_QUOTA_HALT_PCT"):
                os.environ.pop(k, None)
            cfg = TokenGuardConfig()
            assert cfg.quota_throttle_pct == 55.0   # 只有根層有 ⇒ 繼承
            assert cfg.quota_halt_pct == 93.0       # 兩份都有 ⇒ AutoClaude 那份贏
            # 真環境變數仍然贏過兩份檔案。
            os.environ["AUTOSDD_QUOTA_HALT_PCT"] = "97"
            assert TokenGuardConfig().quota_halt_pct == 97.0

    def test_a_garbage_value_falls_back_instead_of_becoming_a_fault(self):
        with patch.dict(os.environ, {"AUTOSDD_QUOTA_HALT_PCT": "not-a-number"}):
            assert TokenGuardConfig().quota_halt_pct == 95.0

    def test_every_autosdd_key_in_the_env_example_has_a_real_reader(self):
        """防幽靈鍵，方向是「鍵 → 讀者」（根層 `env_example_problems()` 的鏡像方向）。

        `.env.example` 自己就記載過 improving_92 清掉一批「宣告了但程式從未讀取」的鍵。
        🔴 射程刻意只到 `AUTOSDD_` 這一族：`POSTGRES_*` 那批的讀者是 docker-compose、
        不是 `autoclaude/**`，把它們一起判就是四筆必須逐一辯護的假紅，而被改怕的鎖
        最後一定被改寬。本輪新增的那兩個鍵正好落在這一族內，所以射程夠。
        """
        keys = re.findall(r"^(AUTOSDD_[A-Z0-9_]+)=",
                          (REPO / ".env.example").read_text(encoding="utf-8"), re.MULTILINE)
        assert keys, ".env.example 一個 AUTOSDD_ 鍵都沒有 ⇒ 這條鎖已靜默歸零"
        src = "\n".join(f.read_text(encoding="utf-8", errors="replace")
                        for f in (REPO / "autoclaude").rglob("*.py"))
        ghosts = [k for k in keys if k not in src]
        assert ghosts == [], f"AutoClaude/.env.example 宣告了沒有讀者的鍵：{ghosts}"


# ─────────────────────────────────────────────────────────────
# R82 / C3：同一份快取，harness 與引擎必須給出同一個判定
# ─────────────────────────────────────────────────────────────
def _root_quota_policy():
    """import 根層判讀層（**只在測試裡**；生產碼那個方向由 ACQ-02 forbidden contract 擋住）。"""
    import sys
    sys.path.insert(0, str(REPO.parent / "tools" / "lib"))
    import quota_policy
    return quota_policy


class TestBandParityWithTheHarness:
    """🔴 兩個引擎讀同一份快取時**不得**得到相反的答案（C3 的驗收本體）。

    只鎖 `halt` 這一格是刻意的，而且它是**恰好等價**（雙向都成立，可以證明）：
      根層 band==halt ⇔ 某軸 cap==0 ⇔ 某軸 pct ≥ halt_pct ⇔ max(pct) ≥ halt_pct
                     ⇔ 引擎 `read_worst_pct().pct >= quota_halt_pct` ⇔ 引擎 halt。
    🔴 比較對象是**逐軸的帶別**（`decision.per_axis`），不是 `decision.band`——後者是
    **argmin(cap)** 那一軸的帶別，一個聚合值，與引擎的 argmax(pct) 本來就不是同一個量。
    這不是理論顧慮，是本輪落地時當場量到的：`five_hour 82%@4h + weekly_all 55%@5d`
    ⇒ 兩軸 cap 都是 4，平手時 `_binding_key` 取期程較長者 ⇒ binding=weekly_all、
    `decision.band='notice'`，而同一份 payload 裡真的有一軸站在 82%（converge）。
    拿 `decision.band` 當判準會把「兩個正確的答案」判成分歧，那種鎖活不過一輪。
    """

    def _sides(self, tmp_path, axes):
        Q = _root_quota_policy()
        now = datetime.now(UTC)
        payload = {"schema": SCHEMA, "axes": [
            _axis(k, p, None if m is None else (now + timedelta(minutes=m)).isoformat())
            for k, p, m in axes]}
        meter = FileQuotaMeterAdapter(str(_write_quota(tmp_path, payload)))
        state = Q.QuotaState(
            axes=tuple(Q.Axis(kind=a["kind"], pct=a["pct"], resets_at=a["resets_at"])
                       for a in payload["axes"]),
            measured_at=now.isoformat(), source="test")
        return Q, Q.decide(state, now, Q.DEFAULT_POLICY), TokenGuardPlugin(quota_meter=meter)

    @pytest.mark.parametrize("axes", [
        [("weekly_all", 96.0, 180), ("session", 10.0, 20)],    # 分歧組①（C3 的實測 payload）
        [("session", 96.0, 20), ("weekly_all", 55.0, 7200)],   # 短期程軸撞線
        [("five_hour", 82.0, 240), ("weekly_all", 55.0, 7200)],  # 收斂帶，兩軸期程不同
        [("session", 10.0, 20), ("weekly_all", 20.0, 7200)],   # 全綠（反向對照：不得亂擋）
        [("spend", 99.0, None), ("five_hour", 12.0, 180)],     # 沒有 reset 可等的那條線最緊
    ])
    def test_halt_is_exactly_equivalent_on_both_sides(self, tmp_path, axes):
        Q, decision, plugin = self._sides(tmp_path, axes)
        engine_halts = plugin.evaluate_quota({}) is not None
        assert any(r.band == Q.BAND_HALT for r in decision.per_axis) is engine_halts, (
            f"harness per_axis={[r.band for r in decision.per_axis]} 但引擎 halt="
            f"{engine_halts} ⇒ 同一份快取兩個答案")
        # cap=0 是階梯裡最小的 ⇒ 任一軸 halt 必定是 binding ⇒ 聚合值也必須說 halt。
        assert (decision.band == Q.BAND_HALT) is engine_halts

    @pytest.mark.parametrize("axes", [
        [("weekly_all", 96.0, 180), ("session", 10.0, 20)],
        [("five_hour", 82.0, 240), ("weekly_all", 55.0, 7200)],
        [("session", 71.0, 20), ("weekly_all", 20.0, 7200)],
        [("session", 69.9, 20), ("weekly_all", 20.0, 7200)],   # 門檻正下方（不得亂擋）
        [("session", 10.0, 20), ("weekly_all", 20.0, 7200)],   # 全綠
    ])
    def test_the_converge_band_is_exactly_equivalent_per_axis(self, tmp_path, axes):
        """收斂帶：「有沒有任何一軸站在 converge 以上」兩側必須同答案。

        引擎 throttle ⇔ max(pct) ≥ 70 ⇔ ∃ 軸 pct ≥ 70 ⇔ ∃ 軸 band ∈ {converge,
        prepare, halt}。這是恆等式，不是啟發式；上下兩組 payload 同時含正例與反例。
        """
        Q, decision, plugin = self._sides(tmp_path, axes)
        tight = (Q.BAND_CONVERGE, Q.BAND_PREPARE, Q.BAND_HALT)
        harness = any(r.band in tight for r in decision.per_axis)
        engine = plugin.evaluate_quota({"in_correction_loop": True}) is not None
        assert harness is engine, (
            f"harness per_axis={[r.band for r in decision.per_axis]} 但引擎 throttle={engine}")

    def test_the_parity_judge_can_fail(self, tmp_path):
        """判準自證：把引擎的選軸換回**最先 reset**那一支，分歧組①必須讓上面那條紅。"""
        Q, decision, _plugin = self._sides(
            tmp_path, [("weekly_all", 96.0, 180), ("session", 10.0, 20)])
        meter = FileQuotaMeterAdapter(str(_write_quota(tmp_path, {"schema": SCHEMA, "axes": [
            _axis("weekly_all", 96.0, (datetime.now(UTC) + timedelta(hours=3)).isoformat()),
            _axis("session", 10.0, (datetime.now(UTC) + timedelta(minutes=20)).isoformat())]})))
        meter.read_worst_pct = meter.read      # ← 這就是修前的形態
        assert decision.band == Q.BAND_HALT
        assert TokenGuardPlugin(quota_meter=meter).evaluate_quota({}) is None


# ─────────────────────────────────────────────────────────────
# ACQ-04：撞線 ≠ 一般步驟失敗（不得進 CORRECTION 重試迴圈）
# ─────────────────────────────────────────────────────────────
class _StubMeter:
    """QuotaMeterPort 的兩個面。🔴 R82：**刻意讓兩個面回同一個 reading**。

    這支 stub 只服務「門檻判定」那一族測試，它們不關心選軸；選軸的分歧由
    `TestTheTwoSelectionCriteriaAreNotTheSameQuestion` 用**真 adapter ＋ 真快取**驗，
    那才是缺陷發生的地方。stub 兩面同值 ⇒ 這一族測試對選軸零鑑別力，這是刻意的
    （讓它們假裝有鑑別力才是危險的）。
    """

    def __init__(self, reading):
        self._r = reading

    def read(self):
        return self._r

    def read_worst_pct(self):
        return self._r


class TestQuotaHaltClassification:
    def _plugin(self, reading):
        return TokenGuardPlugin(quota_meter=_StubMeter(reading))

    def test_hard_watermark_halts(self):
        req = self._plugin(QuotaReading(96.0, "session", None)).evaluate_quota({})
        assert req is not None and req.request_halt is True

    def test_limit_text_halts_even_when_the_meter_says_plenty_left(self):
        # 這是 ACQ-04 的核心：撞線訊息修前會被當一般失敗、被 CORRECTION 重試，
        # 而每一次重試都是再打一次 claude ⇒ 反而加速燒額度。
        req = self._plugin(QuotaReading(3.0, "session", None)).evaluate_quota(
            {"failure_reason": "Claude usage limit reached. Your limit resets at 9am"},
        )
        assert req is not None and req.request_halt is True

    def test_throttle_band_only_stops_optional_spend(self):
        p = self._plugin(QuotaReading(85.0, "session", None))
        # 重試（CORRECTION 迴圈）＝可選支出 → 停
        assert p.evaluate_quota({"in_correction_loop": True}).request_halt is True
        # 正常步驟 → 不擋（反向對照組：只測擋得住不測不亂擋的鎖沒有鑑別力）
        assert p.evaluate_quota({"in_correction_loop": False}) is None

    def test_ordinary_failure_is_not_misread_as_a_quota_hit(self):
        p = self._plugin(QuotaReading(10.0, "session", None))
        assert p.evaluate_quota({"failure_reason": "AssertionError: expected 3 got 4"}) is None

    def test_no_meter_means_zero_behaviour_change(self):
        assert TokenGuardPlugin().evaluate_quota({"in_correction_loop": True}) is None

    def test_limit_text_matcher_has_both_directions(self):
        assert is_quota_limit_text("Claude usage limit reached") is True
        assert is_quota_limit_text("pytest failed: 3 errors") is False
        assert is_quota_limit_text(None) is False


# ─────────────────────────────────────────────────────────────
# ACQ-05 / ACA-01：等多久由觀測到的 resets_at 決定，不是寫死 30 分鐘
# ─────────────────────────────────────────────────────────────
class TestResumeWaitComesFromObservedResetTime:
    def test_waitable_kind_uses_the_observed_reset_instant(self):
        now = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
        r = QuotaReading(96.0, "five_hour", (now + timedelta(minutes=17)).isoformat())
        assert resume_wait_seconds(r, now=now) == pytest.approx(17 * 60)

    def test_naive_reset_string_is_read_as_utc_not_local(self):
        now = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
        r = QuotaReading(96.0, "session", "2026-08-09T12:30:00")
        assert resume_wait_seconds(r, now=now) == pytest.approx(30 * 60)

    @pytest.mark.parametrize("kind", ["weekly_all", "seven_day", "spend"])
    def test_kinds_without_a_reset_worth_waiting_for_return_none(self, kind):
        # R81 實測：weekly 那類的 resets_at 可距當下數天；spend 根本沒有 reset 可等
        # ⇒ 對它們排程等待是錯的動作（記憶：monthly spend limit 沒有 reset 可等）。
        now = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
        r = QuotaReading(99.0, kind, (now + timedelta(days=5)).isoformat())
        assert resume_wait_seconds(r, now=now) is None

    def test_unparseable_or_absent_reset_returns_none_never_a_guess(self):
        assert resume_wait_seconds(QuotaReading(99.0, "session", None)) is None
        assert resume_wait_seconds(QuotaReading(99.0, "session", "not-a-time")) is None
        assert resume_wait_seconds(None) is None

    def test_past_reset_clamps_to_zero_instead_of_going_negative(self):
        now = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
        r = QuotaReading(99.0, "session", (now - timedelta(hours=3)).isoformat())
        assert resume_wait_seconds(r, now=now) == 0.0


class TestAutoResumeServiceHonoursTheQuotaAxis:
    def _service(self, meter):
        from autoclaude.core.services.auto_resume import AutoResumeService
        cfg = AppConfig()
        cfg.token_guard.resume_delay_minutes = 30
        return AutoResumeService(kernel=object(), config=cfg, quota_meter=meter)

    def test_waitable_quota_reset_overrides_the_hardcoded_delay(self):
        soon = datetime.now(UTC) + timedelta(minutes=4)
        svc = self._service(_StubMeter(QuotaReading(96.0, "session", soon.isoformat())))
        # 寫死的 30 分鐘（1800s）不得再是答案。
        assert 0 < svc._halt_wait_seconds(None) <= 4 * 60 + 5

    def test_non_waitable_kind_falls_back_and_does_not_invent_a_time(self):
        far = datetime.now(UTC) + timedelta(days=5)
        svc = self._service(_StubMeter(QuotaReading(99.0, "weekly_all", far.isoformat())))
        # 絕不睡 5 天：回落到既有排程（sched=None ⇒ 0.0），並由 log 通知人。
        assert svc._halt_wait_seconds(None) == 0.0

    def test_without_a_meter_behaviour_is_unchanged(self):
        svc = self._service(None)
        assert svc._halt_wait_seconds(None) == 0.0

    def test_a_context_halt_at_low_quota_never_touches_the_quota_axis(self, caplog):
        """同一支 `_halt_wait_seconds` 也服務 **context** halt，而那與額度無關。

        水位低於 throttle 門檻時必須完全不碰額度軸；否則每一次 context halt 都會印一行
        「額度沒有等得到的 reset」＝與本次 halt 無關的假訊號。
        """
        soon = datetime.now(UTC) + timedelta(minutes=9)
        svc = self._service(_StubMeter(QuotaReading(12.0, "session", soon.isoformat())))
        with caplog.at_level("INFO"):
            assert svc._halt_wait_seconds(None) == 0.0
        assert "額度" not in caplog.text

    def test_the_halt_loop_really_consults_the_quota_axis(self, tmp_path):
        """🔴 接線鎖：上面三條都直接呼叫 `_halt_wait_seconds`，於是「函式對了但沒人叫它」
        這個形態（本 repo 反覆記載的「機制蓋好沒接電」）結構上看不到。

        合成注入驗紅：把 run() halt 分支改回 `seconds_until_resume(sched)`，本測試必 FAIL。
        """
        from autoclaude.core.kernel_state import KernelResult
        pb = tmp_path / "pb.yaml"
        pb.write_text(
            yaml.safe_dump({"version": "1.0", "project": "x",
                            "tasks": [{"step_id": "T01", "name": "n", "prompt": "hi"}]}),
            encoding="utf-8", newline="\n",
        )
        soon = datetime.now(UTC) + timedelta(minutes=6)

        class _Kernel:
            def run(self, playbook, start_idx=0):
                return KernelResult(success=False, completed_steps=0, total_steps=1,
                                    halted=True)

        cfg = AppConfig()
        cfg.token_guard.resume_delay_minutes = 30
        cfg.token_guard.max_auto_resumes = 1
        from autoclaude.core.services.auto_resume import AutoResumeService
        svc = AutoResumeService(
            kernel=_Kernel(), config=cfg,
            quota_meter=_StubMeter(QuotaReading(96.0, "session", soon.isoformat())),
        )
        with patch("autoclaude.core.services.auto_resume.time.sleep") as slept:
            svc.run(str(pb))
        assert slept.call_count == 1
        # 依觀測到的 resets_at ≈ 6 分鐘；修前這裡永遠是 0（seconds_until_resume(None)）。
        assert 5 * 60 < slept.call_args.args[0] <= 6 * 60 + 5


# ─────────────────────────────────────────────────────────────
# R82 / C6：額度軸「已設計、未接線」——把那個缺口變成量得到的事實
# ─────────────────────────────────────────────────────────────
class TestTheQuotaAxisHasNoEngineSideRefresher:
    """🔴 這一組**不是**在測「功能正確」，是在把一個缺口釘住，讓它不會被靜默改寫。

    缺口：全 repo 唯一的快取寫入者住在 harness（`tools/lib/quota_gate.py::
    refresh_quota_blocking`）。🔴 R83 訂正原先那句射程（原文：「而它唯一的到達路徑是
    Claude Code 的 PreToolUse ＋扇出型工具」——接電之後為假）：它現在**也**由 PostToolUse
    到達（matcher 覆蓋 `Read|Bash|Grep|Glob|…`）⇒ 有 Claude Code session 在跑時，每 180 秒
    就會有人刷新。缺口**縮小但沒有消失**：AutoClaude 獨立跑（無 session）時仍然沒有任何
    東西刷新它 ⇒ TTL 一過就永久 `None`＝量不到，而「量不到」在引擎側是**不擋**。
    完整理由（以及為什麼仍不補）見 `autoclaude/core/ports/quota_meter.py` 檔頭那段。
    """

    def test_no_module_under_autoclaude_writes_the_quota_cache(self):
        """引擎側零寫入者。哪天有人補了，這條會紅並要求回來改掉那段劃界散文。"""
        writers = []
        for f in (REPO / "autoclaude").rglob("*.py"):
            src = f.read_text(encoding="utf-8", errors="replace")
            if "autosdd_quota.json" in src and re.search(
                    r"\.(write_text|write_bytes|open)\s*\(", src):
                writers.append(f.relative_to(REPO).as_posix())
        assert writers == [], (
            f"AutoClaude 出現了額度快取的寫入者：{writers} ⇒ ports/quota_meter.py 檔頭那段"
            "「已設計、未接線」的劃界已經過期，請一併改掉（散文與事實不得漂開）")

    def test_the_only_writer_is_the_harness(self):
        """反向對照：寫入者確實存在，只是住在 harness ⇒ 上一條不是恆真。"""
        meter = (REPO.parent / "tools" / "lib" / "quota_meter.py").read_text(encoding="utf-8")
        assert "def write_cache(" in meter

    def test_an_unrefreshed_cache_degrades_to_no_action_not_to_a_low_reading(self, tmp_path):
        """🔴 量不到必須是 `None`（不擋、不宣稱），**絕不是** 0.0（＝「額度很充足」）。

        這是缺口的**安全方向**：它會漏擋，但不會拿一個假的低水位去騙下游。
        """
        stale = _write_quota(tmp_path, _GOOD, age_seconds=3600)
        meter = FileQuotaMeterAdapter(str(stale), ttl_seconds=1800)
        assert meter.read() is None and meter.read_worst_pct() is None
        assert TokenGuardPlugin(quota_meter=meter).evaluate_quota(
            {"in_correction_loop": True}) is None
        # 撞線文字那條線**不吃快取** ⇒ 缺口之下仍有一層（離線、零 token）。
        assert TokenGuardPlugin(quota_meter=meter).evaluate_quota(
            {"failure_reason": "Claude usage limit reached"}) is not None


# ─────────────────────────────────────────────────────────────
# ACQ-02：autoclaude 不得反向依賴 monorepo harness（tools / .claude）
# ─────────────────────────────────────────────────────────────
_FORBIDDEN_ROOTS = {"tools", "_claude"}


def _harness_imports(path: Path) -> list[str]:
    """判準本體：回傳該檔中指向 harness 的 import 模組名。"""
    hits = []
    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""] if node.level == 0 else []
        else:
            continue
        for n in names:
            head = n.split(".", 1)[0]
            if head in _FORBIDDEN_ROOTS or ".claude" in n:
                hits.append(n)
    return hits


class TestNoHarnessImport:
    def test_the_judge_catches_the_shortcut_we_refused_to_take(self, tmp_path):
        """合成注入：`import tools.lib.quota_meter` 就是那條被拒絕的捷徑，必須被抓到。"""
        p = tmp_path / "bad.py"
        p.write_text("import tools.lib.quota_meter\nimport json\n",
                     encoding="utf-8", newline="\n")
        assert _harness_imports(p) == ["tools.lib.quota_meter"]

    def test_no_module_under_autoclaude_imports_the_harness(self):
        offenders = {}
        for f in (REPO / "autoclaude").rglob("*.py"):
            hits = _harness_imports(f)
            if hits:
                offenders[f.relative_to(REPO).as_posix()] = hits
        assert offenders == {}

    def test_importlinter_can_actually_see_that_direction(self):
        """🔴 修前 root_packages 只有 `autoclaude` ⇒ `tools.*` 是套件外 external import、
        不進 grimp 的圖，八條 contract 全綠＝假機械物。這一條釘住那個修法本身。"""
        parser = configparser.ConfigParser(allow_no_value=True)
        parser.read(REPO / ".importlinter", encoding="utf-8")
        roots = (parser["importlinter"]["root_packages"] or "").split()
        assert "tools" in roots, "root_packages 缺 tools ⇒ 這個方向對 importlinter 不可見"
        forbidding = [
            s for s in parser.sections()
            if s.startswith("importlinter:contract:")
            and parser[s].get("type") == "forbidden"
            and "autoclaude" in (parser[s].get("source_modules") or "").split()
            and "tools" in (parser[s].get("forbidden_modules") or "").split()
        ]
        assert forbidding, "缺一條 autoclaude ↛ tools 的 forbidden contract"


# ─────────────────────────────────────────────────────────────
# ACB-02：example_playbook 必須自足，且不得污染引擎自己的 tests/
# ─────────────────────────────────────────────────────────────
class TestExamplePlaybookIsSelfContained:
    PLAYBOOK = REPO / "scripts" / "example_playbook.yaml"

    def _referenced_paths(self) -> list[str]:
        """只掃**送給 Claude Code 的內容**（prompt / evaluator_command），不掃 YAML 註解。

        刻意用 yaml.safe_load 而不是整檔 regex：檔頭的訂正註記本來就會逐字引述修前那些
        壞路徑（那是說明，不是指令），整檔掃會把說明本身判成違規＝假紅。
        """
        data = yaml.safe_load(self.PLAYBOOK.read_text(encoding="utf-8"))
        blob = "\n".join(
            str(t.get("prompt", "")) + "\n" + str(t.get("evaluator_command", ""))
            for t in data["tasks"]
        )
        return re.findall(r"`?([\w./-]+\.(?:md|py))`?", blob)

    def test_every_spec_file_the_first_step_reads_actually_exists(self):
        """修前 T01 要讀 docs/sdd_auth_spec.md，該檔全庫不存在 ⇒ 第一步沒有規格可讀。"""
        missing = [
            p for p in self._referenced_paths()
            if p.endswith(".md") and "api_auth" not in p and not (REPO / p).exists()
        ]
        assert missing == [], f"playbook 指定讀取但不存在的規格檔：{missing}"

    def test_no_artifact_path_lands_in_the_engines_own_test_tree(self):
        # `tests/test_auth.py` 這種相對路徑會與 AutoClaude 自己的 tests/ 混在一起。
        bad = [p for p in self._referenced_paths()
               if p.startswith("tests/") or p == "auth.py"]
        assert bad == [], f"產物路徑會污染引擎自己的目錄：{bad}"

    def test_evaluator_command_points_at_the_example_workspace(self):
        data = yaml.safe_load(self.PLAYBOOK.read_text(encoding="utf-8"))
        cmds = [t.get("evaluator_command") for t in data["tasks"] if t.get("evaluator_command")]
        assert cmds, "example_playbook 應保留至少一個 evaluator_command（雙重驗證）"
        for c in cmds:
            assert "scripts/example_workspace/" in c
