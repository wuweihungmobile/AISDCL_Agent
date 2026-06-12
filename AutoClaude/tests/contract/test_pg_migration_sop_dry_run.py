"""Production_Migration_SOP.md dry-run contract test（SD_08 W5 T5-H7 / ADR-SD08-005）。

≥ 2 case：
  1. §1 前置確認 checklist — (a)/(b)/(c) 在 W5 末必須全綠
  2. §2 灰度啟動 dual_write_strict — 文件必須明文 "fail_loud" + drift_log SLA
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOP_PATH = PROJECT_ROOT / "docs" / "08_deployment" / "Production_Migration_SOP.md"


@pytest.fixture(scope="module")
def sop_content() -> str:
    assert SOP_PATH.exists(), f"Production_Migration_SOP.md 缺失：{SOP_PATH}"
    return SOP_PATH.read_text(encoding="utf-8")


# ──────────────────────────────────────────────────────────────
# Case 1：§1 前置確認 (a)/(b)/(c) checklist 在 W5 末必須打勾
# ──────────────────────────────────────────────────────────────
def test_sop_section1_prerequisite_checklist_w5_done(sop_content):
    """§1 前置確認 (a) AI-Agent 演練 / (b) WAL lag adapter / (c) ADR-SD08-005 在 W5 末必須打勾。"""
    # 抓 §1 區段
    m = re.search(
        r"## §1\..*?(?=## §2\.)",
        sop_content,
        re.DOTALL,
    )
    assert m, "SOP 缺 §1 section"
    section1 = m.group(0)

    # (a)/(b)/(c) 三項在 W5 末必須打勾 ✅；(d)/(e) 為 SD_09 前置可為空 []
    # 用 (a) / (b) / (c) 標記檢查
    assert "[✅] (a)" in section1, "§1 (a) AI-Agent 演練 未打勾"
    assert "[✅] (b)" in section1, "§1 (b) WAL lag adapter 未打勾"
    assert "[✅] (c)" in section1, "§1 (c) ADR-SD08-005 PM 核准 未打勾"


# ──────────────────────────────────────────────────────────────
# Case 2：§2 灰度啟動 dual_write_strict + drift_log SLA 必須明文
# ──────────────────────────────────────────────────────────────
def test_sop_section2_dual_write_strict_fail_loud(sop_content):
    """§2 灰度啟動必須含 dual_write_strict=fail_loud + drift_log SLA。"""
    m = re.search(
        r"## §2\..*?(?=## §3\.)",
        sop_content,
        re.DOTALL,
    )
    assert m, "SOP 缺 §2 section"
    section2 = m.group(0)

    # dual_write_strict 模式必須明文 fail_loud
    assert "dual_write_strict" in section2, "§2 未提及 dual_write_strict"
    assert "fail_loud" in section2, "§2 未指定 dual_write_strict=fail_loud"

    # drift_log SLA 必須明文 = 0 / 7 天
    assert "drift_log" in section2, "§2 未提及 drift_log SLA"
    assert re.search(r"=\s*0", section2), "§2 drift_log 必須明文 = 0 事件"

    # WAL lag 三閾值對齊（與 pg_health.py 一致）
    assert "2s" in section2 or "2.0" in section2, "§2 WAL lag warn 閾值未明文"
    assert "10s" in section2 or "10.0" in section2, "§2 WAL lag critical 閾值未明文"
