"""`rule_loader._write_rule()` 行尾契約鎖（R60 Scan-F 反駁者自找 #2）。

WHY：`governance/rules/R-*.yaml` 是 tracked 檔，`.gitattributes` 明文宣告
`*.yaml  text eol=lf`。`_write_rule()` 原本用 `Path.write_text(...)` 而不帶
`newline=""`，text 模式預設 `newline=None` 會在 Windows 上把每個 `"\n"` 寫成
`"\r\n"`。fire 遙測 production 出貨為 ON、`record_state_fires()` 在**每次
transition** 都走這條路徑寫回，故 Windows 上跑一次 FSM 就會把整批規則檔改成
CRLF：R60 實測一次探針讓 15 支 `R-*.yaml` 變「已修改」（git 對每檔印
`CRLF will be replaced by LF`），掩蓋真正的變更、並觸發 smoke 的「未 commit
變更」告警；macOS/Linux 上同一段程式只產生 fire_count 的數字 diff。

鑑別力：斷言寫出的**位元組**裡零 `\r`。此鎖在 Windows 上對移除 `newline=""`
立即翻紅（實測），在 POSIX 上恆綠（該平台本來就不做換行轉譯）——這是平台語意
使然，不是鎖失效；`test_write_rule_source_declares_newline_contract` 補上一道
在任何平台都有鑑別力的原始碼契約斷言。
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime import rule_loader  # noqa: E402


def _seed_rule(rules_dir: Path, rule_id: str = "R-9.99-eol-probe") -> Path:
    rules_dir.mkdir(parents=True, exist_ok=True)
    path = rules_dir / f"{rule_id}.yaml"
    path.write_bytes(
        yaml.safe_dump(
            {
                "id": rule_id,
                "title": "行尾契約探針",
                "trigger_states": ["*"],
                "severity": "low",
                "maturity": "active",
                "spec": "R60 regression fixture",
                "test_ref": __file__,
                "scaffold_roi": {
                    "fire_count": 0, "catch_count": 0, "false_positive_count": 0,
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ).encode("utf-8")
    )
    return path


def test_record_fire_writes_lf_only(tmp_path):
    rules_dir = tmp_path / "rules"
    path = _seed_rule(rules_dir)
    assert path.read_bytes().count(b"\r") == 0, "載具失效：fixture 本身就已是 CRLF"

    updated = rule_loader.record_fire("R-9.99-eol-probe", caught=False, rules_dir=rules_dir)
    assert updated is not None, "載具失效：record_fire 沒找到探針規則，等於什麼都沒寫"
    assert updated.scaffold_roi["fire_count"] == 1

    raw = path.read_bytes()
    cr_count = raw.count(b"\r")
    assert cr_count == 0, (
        "_write_rule() 把 eol=lf 的 tracked 規則檔寫成 CRLF"
        f"（CR x {cr_count}）——Windows 上每次 rule fire 都會污染工作樹"
    )
    assert b"fire_count: 1" in raw


def test_record_state_fires_writes_lf_only(tmp_path):
    """production 真正的高頻入口（每次 transition 進入狀態即批次記帳）。"""
    rules_dir = tmp_path / "rules"
    path = _seed_rule(rules_dir, "R-9.98-eol-batch")
    fired = rule_loader.record_state_fires("EXECUTION", rules_dir=rules_dir)
    assert fired == ["R-9.98-eol-batch"], f"載具失效：本次沒有任何規則被記帳（{fired}）"
    assert path.read_bytes().count(b"\r") == 0


def test_write_rule_source_declares_newline_contract():
    """平台中立契約鎖：POSIX 上位元組斷言恆綠、對回歸零鑑別力，故另鎖原始碼意圖。"""
    src = inspect.getsource(rule_loader._write_rule)
    assert 'newline=""' in src, (
        "_write_rule() 的寫檔已不帶 newline=\"\" — Windows 上會把 "
        "governance/rules/*.yaml（.gitattributes 宣告 eol=lf）整檔轉成 CRLF"
    )
