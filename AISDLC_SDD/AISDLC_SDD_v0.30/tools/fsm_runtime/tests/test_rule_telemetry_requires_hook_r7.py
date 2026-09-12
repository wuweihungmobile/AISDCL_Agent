# enforces (governance rules): R-9.20
"""D28（DEF-200-275 第七輪 SA-R7-01）— telemetry writeback「要求 hook 身分」加法式守衛測試。

背景：四方複審 SA-R7-01（P2，重現／讀碼／裁決三鏡皆確認真實）指出 v0.24 把
`_rule_fire_telemetry_enabled`／`_rule_catch_telemetry_enabled` 的 unset→ON 常態化後，
pytest 外任何 FSM 驅動（探針／審查 agent／手動重現）只要漏加
`SDD_ENABLE_RULE_FIRE_TELEMETRY=0 SDD_ENABLE_RULE_CATCH_TELEMETRY=0` opt-out 前綴，就會對
tracked 的 `governance/rules/*.yaml` 寫回 fire_count／catch_count——第五輪、第七輪各真實
發生一次污染。裁決 D28：不翻 v0.24 預設（43 處測試與文件釘住；框架獨立於 Claude Code
session 外使用時仍需 ON），改加一道**只在 session 明確要求時才生效**的加法式守衛：
`SDD_TELEMETRY_WRITEBACK_REQUIRES_HOOK`（session 級開關，只由 settings.json 釘）
＋ `SDD_FSM_HOOK_ENTRY`（hook 身分標記，只由三支真 hook 在 main() 入口設）。

本檔驗四象限（兩 env 皆未設→ON／REQUIRES=1 無 ENTRY→OFF／REQUIRES=1＋ENTRY=1→ON／
顯式 0 或 1 永遠優先於 REQUIRES）× fire 與 catch 兩側，外加一支端到端（真實 transition
寫 governance/rules 複本）與一支 stderr 只喊一次的噪音守則。每案皆編碼「為何此行為重要」
（Rule 9）：v0.24 契約零弱化、新洞真的被堵住、hook 身分真的豁免、顯式意圖不可被推翻。
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime import fsm_runtime as fr  # noqa: E402
from tools.fsm_runtime import rule_loader  # noqa: E402
from tools.fsm_runtime.fsm_runtime import FSMRuntime  # noqa: E402
from tools.fsm_runtime.state_loader import load_state, save_state  # noqa: E402

_REQ_ENV = "SDD_TELEMETRY_WRITEBACK_REQUIRES_HOOK"
_ENTRY_ENV = "SDD_FSM_HOOK_ENTRY"
_FIRE_ENV = "SDD_ENABLE_RULE_FIRE_TELEMETRY"
_CATCH_ENV = "SDD_ENABLE_RULE_CATCH_TELEMETRY"


@pytest.fixture(autouse=True)
def _clean_hook_identity_env(monkeypatch):
    """每案前先清空四個相關 env（conftest 的 session fixture 已預設清空/歸零，這裡再顯式一次
    是防禦性重複，不依賴 fixture 執行順序），並重置模組級「只喊一次」旗標——否則前一支測試
    若已觸發過 stderr 警告，後續案的「只喊一次」斷言會失真（跨測試污染）。"""
    for k in (_REQ_ENV, _ENTRY_ENV, _FIRE_ENV, _CATCH_ENV):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(fr, "_telemetry_writeback_skip_warned", False)


# ---------- 四象限（單元層級，直接呼叫兩個 enabled 函式）----------

@pytest.mark.parametrize(
    "enabled_fn, env_name",
    [
        (fr._rule_fire_telemetry_enabled, _FIRE_ENV),
        (fr._rule_catch_telemetry_enabled, _CATCH_ENV),
    ],
    ids=["fire", "catch"],
)
class TestFourQuadrants:
    def test_q1_both_unset_defaults_on(self, monkeypatch, enabled_fn, env_name):
        """WHY：兩個新 env 皆未設＝session 外裸 CLI 或未升級的呼叫端——v0.24「unset→ON」
        契約必須逐字延續，否則本輪新守衛會讓所有既有部署靜默退化成不記帳（比 SA-R7-01
        本身更嚴重的退步）。"""
        assert enabled_fn() is True

    def test_q2_requires_hook_without_entry_is_off(self, monkeypatch, enabled_fn, env_name):
        """WHY：這正是本輪要堵的洞本身——session 內漏加 opt-out 前綴的 ad-hoc 探針，必須被
        REQUIRES_HOOK=1 攔下，即使它跑的是貨真價實的 transition()。"""
        monkeypatch.setenv(_REQ_ENV, "1")
        assert enabled_fn() is False

    def test_q3_requires_hook_with_entry_is_on(self, monkeypatch, enabled_fn, env_name):
        """WHY：三支真 hook（context_ledger_pre/post、session_start）會在 main() 入口設
        SDD_FSM_HOOK_ENTRY=1；REQUIRES_HOOK=1 開著時，它們的遙測寫回必須完全不受影響，
        否則本輪守衛會連自己要放行的對象都一起誤殺。"""
        monkeypatch.setenv(_REQ_ENV, "1")
        monkeypatch.setenv(_ENTRY_ENV, "1")
        assert enabled_fn() is True

    def test_q4a_explicit_on_overrides_requires_hook_block(self, monkeypatch, enabled_fn, env_name):
        """WHY：v0.24 顯式 0/1 契約是既有 43 處測試/文件的地基，D28 新守衛必須是加法式——
        即使 REQUIRES_HOOK=1 且本行程不是 hook（照理會被擋），顯式設為 1 仍必須贏，
        證明本輪改動沒有動到 v0.24 的「顯式值優先」語意。"""
        monkeypatch.setenv(_REQ_ENV, "1")  # 沒設 ENTRY → 若走 REQUIRES_HOOK 路徑會是 False
        monkeypatch.setenv(env_name, "1")
        assert enabled_fn() is True

    def test_q4b_explicit_off_overrides_hook_identity(self, monkeypatch, enabled_fn, env_name):
        """WHY：反向同理——即使是貨真價實的 hook 行程（ENTRY=1，照理會被放行），呼叫端顯式
        opt-out（=0）仍必須贏，證明顯式值的優先權是雙向的，不是只贏「擋」不贏「放」。"""
        monkeypatch.setenv(_REQ_ENV, "1")
        monkeypatch.setenv(_ENTRY_ENV, "1")  # hook 身分俱全 → 若走 hook 路徑會是 True
        monkeypatch.setenv(env_name, "0")
        assert enabled_fn() is False


# ---------- stderr 只喊一次（模組級旗標，避免同 session 內洗版）----------

def test_skip_warning_fires_only_once_per_process(monkeypatch, capsys):
    """WHY：同一行程內每次 transition 都可能觸發本判定（fire 側每次轉態、catch 側每次
    escalation）；若每次都印 stderr 會洗版噪音掩蓋其他警訊。模組級旗標須保證整個行程
    （即使橫跨 fire／catch 兩側）只出聲一次。"""
    monkeypatch.setenv(_REQ_ENV, "1")
    assert fr._rule_fire_telemetry_enabled() is False
    assert fr._rule_catch_telemetry_enabled() is False
    captured = capsys.readouterr()
    assert captured.err.count("[SDD-FSM] rule telemetry write-back skipped") == 1, (
        f"應只喊一次，實際 stderr:\n{captured.err!r}"
    )
    assert "SDD_TELEMETRY_WRITEBACK_REQUIRES_HOOK=1" in captured.err
    assert "SDD_FSM_HOOK_ENTRY=1" in captured.err


# ---------- 端到端：真實 governance/rules 複本 + 真實 transition ----------

@pytest.fixture
def _rules_copy(tmp_path, monkeypatch):
    """把真實 governance/rules 整份複製到 tmp_path，monkeypatch rule_loader.RULES_DIR 指向
    複本——絕不觸碰活體 governance/rules（凍結面），但用真規則集驗證「守衛擋下寫回」與
    「守衛放行時真的寫」兩種行為，比合成假規則更貼近 SA-R7-01 實際踩的坑（活體規則被寫穿）。
    """
    rdir = tmp_path / "rules"
    shutil.copytree(rule_loader.RULES_DIR, rdir)
    monkeypatch.setattr(rule_loader, "RULES_DIR", rdir)
    return rdir


def _snapshot(rules_dir: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in sorted(rules_dir.glob("R-*.yaml"))}


def _rt_in_init(tmp_path, name="r7hook"):
    p = tmp_path / f"FSM-STATE-{name}.yaml"
    st = load_state(name, path=p, create_if_missing=True)
    st.root["current_state"] = "INIT"
    save_state(st)
    return FSMRuntime(st)


def test_e2e_requires_hook_without_entry_leaves_yaml_byte_identical(
    tmp_path, monkeypatch, _rules_copy
):
    """WHY：這是 SA-R7-01 要堵的實際傷害——REQUIRES_HOOK=1 開著、沒有 hook 身分時，一次
    真實 transition() 絕不能改動任何一個位元組的規則 YAML（不只是 fire_count 數值不變，
    是整份複本逐位元組不變，杜絕「順手重排格式」的隱性污染，見 rule_loader._write_rule
    的 yaml.safe_dump 重排格式）。"""
    monkeypatch.setenv(_REQ_ENV, "1")
    before = _snapshot(_rules_copy)
    rt = _rt_in_init(tmp_path)
    rt.transition("SCENARIO_DETECT", reason="D28 e2e q2")
    after = _snapshot(_rules_copy)
    assert after == before, "REQUIRES_HOOK=1 無 ENTRY：governance/rules 複本必須逐位元組不變"


def test_e2e_requires_hook_with_entry_records_fire(tmp_path, monkeypatch, _rules_copy):
    """WHY：守衛不能「一律擋」——真正的 hook 身分（ENTRY=1）在 REQUIRES_HOOK=1 下仍必須
    正常寫回，否則三支真 hook 的既有遙測功能會被本輪改動誤殺（v0.24 活體化倒退）。"""
    monkeypatch.setenv(_REQ_ENV, "1")
    monkeypatch.setenv(_ENTRY_ENV, "1")
    # 挑一條 trigger_states 含 "*" 或命中 SCENARIO_DETECT 的規則來驗 fire_count 真的 +1。
    hit_rule_path = next(
        p for p in sorted(_rules_copy.glob("R-*.yaml"))
        if "*" in (yaml.safe_load(p.read_text(encoding="utf-8")).get("trigger_states") or [])
    )
    before_count = yaml.safe_load(hit_rule_path.read_text(encoding="utf-8"))["scaffold_roi"]["fire_count"]
    rt = _rt_in_init(tmp_path)
    rt.transition("SCENARIO_DETECT", reason="D28 e2e q3")
    after_count = yaml.safe_load(hit_rule_path.read_text(encoding="utf-8"))["scaffold_roi"]["fire_count"]
    assert after_count == before_count + 1, "ENTRY=1（真 hook 身分）：命中規則 fire_count 必須 +1"
