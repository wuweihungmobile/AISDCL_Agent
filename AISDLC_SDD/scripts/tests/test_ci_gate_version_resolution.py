"""DEF-03-001 雙軌版本閘門 — 版本解析邏輯回歸鎖。

WHY（測意圖非僅行為，Rule 9）：
原缺陷 DEF-03-001（P2）= `ci-gate.sh` 寫死 `FW_DIR=AISDLC_SDD_v0.01`，致官方閘門
永遠只測凍結基線、實際承載演化的最新版（v0.02+）從不進 CI/pre-push。本測試以
`SDD_GATE_DRY_RUN=1` 的版本清單輸出鎖定修復後的解析語意：

  1. 雙軌必同時含「凍結基線 v0.01」（回歸防護）與「最新演化版」（演化軌）——
     缺任一即代表治理缺口復發。
  2. 最新演化版必等於磁碟上語意版本最高者（auto-detect），而非任何寫死值——
     直接防止「又退回寫死某版」這個原缺陷再現。
  3. `SDD_FW_VERSION` 覆寫須能收斂為單一版本（debug/二分逃生口）。

純解析驗證（dry-run 不實跑 pytest/arch_fitness），快速且不依賴 Java/TLC。
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from scripts import bash_probe  # isort: skip（首方/三方分組隨 cwd 而異，跳過排序消除歧義）

# scripts/tests/ → scripts/ → AISDLC_SDD（REPO_ROOT，即 ci-gate.sh 的 REPO_ROOT）
REPO_ROOT = Path(__file__).resolve().parents[2]
CI_GATE = REPO_ROOT / "scripts" / "ci-gate.sh"

# WSL 佔位 bash（System32）吃不下 Windows 路徑引數 → 紅燈而非 skip（第五輪 DEF-101 P3）
_BASH = bash_probe.usable_bash()

pytestmark = pytest.mark.skipif(
    _BASH is None, reason="ci-gate.sh 為 bash 腳本，需可用 bash（非 WSL 佔位）"
)


def _dry_run(overrides: dict[str, str] | None = None) -> list[str]:
    """跑 ci-gate.sh dry-run，回傳解析出的版本清單。

    以 `bash -c '<VARS> bash scripts/ci-gate.sh'` 在外層 shell 自身環境內設變數，
    再呼叫內層腳本——繞過 Windows→WSL bash 不繼承宿主環境變數的屏障（CI 原生 bash
    亦適用）；相對路徑 scripts/ci-gate.sh 由 cwd 解析（WSL 自動轉譯 /mnt 路徑）。
    """
    assignments = {"SDD_GATE_DRY_RUN": "1", **(overrides or {})}
    prefix = " ".join(f"{k}={v}" for k, v in assignments.items())
    proc = subprocess.run(
        [_BASH, "-c", f"{prefix} bash scripts/ci-gate.sh"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert proc.returncode == 0, f"dry-run 非零退出：{proc.returncode}\n{proc.stderr}"
    m = re.search(r"^SDD_GATE_VERSIONS=(.*)$", proc.stdout, re.MULTILINE)
    assert m, f"未找到 SDD_GATE_VERSIONS 行：\n{proc.stdout}"
    return m.group(1).split()


def _disk_versions() -> list[str]:
    """磁碟上的版本目錄，依語意版本由低到高排序。

    DEF-19-002：glob 由 `v0.0*` 放寬為 `v0.*`，與修復後的 ci-gate.sh 雙 glob 同涵蓋面
    （含 v0.10+）。否則 helper 漏 v0.10 → 誤算「磁碟最高版=v0.09」，與腳本實測 v0.10 不符。
    """
    dirs = [p.name for p in REPO_ROOT.glob("AISDLC_SDD_v0.*") if p.is_dir()]
    # 以版本數值排序（對齊 scripts/sdd_version.py SSOT 的排序語意）
    return sorted(dirs, key=lambda n: [int(x) for x in re.findall(r"\d+", n)])


def test_ci_gate_exists():
    assert CI_GATE.is_file(), f"ci-gate.sh 不存在：{CI_GATE}"


def test_dual_track_includes_frozen_baseline_and_latest():
    """雙軌必同時含凍結基線 v0.01 與最新演化版（治理缺口不復發）。"""
    versions = _dry_run()
    assert "AISDLC_SDD_v0.01" in versions, "凍結基線 v0.01 必恆測（回歸防護）"
    latest = _disk_versions()[-1]
    assert latest in versions, f"最新演化版 {latest} 必納入官方閘門（DEF-03-001 修復點）"


def test_latest_is_highest_semver_not_hardcoded():
    """演化軌取磁碟語意版本最高者，而非任何寫死值（直防原缺陷再現）。"""
    versions = _dry_run()
    latest = _disk_versions()[-1]
    if latest != "AISDLC_SDD_v0.01":
        # 雙軌：[凍結基線, 最新演化版]，且最新版 = 磁碟最高版
        assert versions[-1] == latest, (
            f"演化軌應為磁碟最高版 {latest}，實得 {versions[-1]}——"
            f"疑似又退回寫死版本（DEF-03-001 復發）"
        )


def test_single_version_override_collapses_to_one():
    """SDD_FW_VERSION 覆寫須收斂為單一指定版本（debug 逃生口）。"""
    versions = _dry_run({"SDD_FW_VERSION": "AISDLC_SDD_v0.04"})
    assert versions == ["AISDLC_SDD_v0.04"], f"覆寫應僅測單版，實得 {versions}"
