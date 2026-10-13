"""根 ruff.toml 只排除凍結版、LATEST 必留在掃描面——DEF-101-018 解鎖條件的回歸鎖。

WHY（測意圖，Rule 9）：repo 根 `ruff check .` 要印 `All checks passed!`，前提是凍結版
（v0.01 到 LATEST 之前的每一版）的存量命中被移出掃描面——那些目錄不可原地改（掌舵者
裁決：只有 LATEST 可改）。排除清單偏離「恰好＝凍結版」有兩個方向，各自有害：

  1. 吃到 LATEST（樣式寫太寬，例如 `v0.3*`）：LATEST 成為沒人 lint 的法外之地，
     債在那裡無聲長回來。
  2. 漏掉凍結版（樣式寫太窄）：LATEST 前進（Copy-on-Evolve 開新版）後，上一版凍結了卻
     沒補進清單；它的存量命中讓根層 ruff 紅，而那個目錄又不能改。

另鎖一側：根檔必須「只做 extend-exclude」。一旦加上 `select` 之類的規則設定，
AISDLC_SDD 就從 ruff 出廠預設被換成另一套規則集——那是 `tools/ruff.toml` 檔頭所說
「另一個授權面的決定」，不該由排除清單的編修順手帶進來。

LATEST 與版本集合一律走 `scripts/sdd_version.py` 的 SSOT（tracked 過濾＋數值排序），
不在本檔另寫第二份解析。判準自身的紅綠自證（合成輸入，不靠 repo 現況）見檔尾兩支。
"""
from __future__ import annotations

import fnmatch
import os
import tomllib
from pathlib import Path

from scripts import sdd_version  # isort: skip（首方/三方分組隨 cwd 而異，跳過排序消除歧義）

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_SDD_ROOT = os.path.dirname(os.path.dirname(_TESTS_DIR))


def _monorepo_root() -> str:
    # scripts/tests/ → scripts/ → AISDLC_SDD/ → monorepo 根
    return os.path.dirname(_SDD_ROOT)


_ROOT_RUFF_TOML = os.path.join(_monorepo_root(), "ruff.toml")


def is_excluded(patterns: list[str], version_dir: str) -> bool:
    """與 ruff 同語意：這個版本目錄是否被 `extend-exclude` 整棵跳過。

    ruff 的樣式相對於設定檔所在目錄（此處＝monorepo 根）、`*` 可跨 `/`；目錄本身命中
    即整棵略過，其下檔案命中則該檔略過。對版本目錄本身與其下一個代表性檔案路徑各比
    一次。用 `fnmatchcase` 而非 `fnmatch.fnmatch`：後者在 Windows 會把大小寫與斜線
    正規化，與 ruff 的比對語意不同（鐵律三：路徑分隔符）。
    """
    rel = f"AISDLC_SDD/{version_dir}"
    return any(
        fnmatch.fnmatchcase(candidate, pattern)
        for pattern in patterns
        for candidate in (rel, f"{rel}/probe.py")
    )


def frozen_versions_still_scanned(
    patterns: list[str], versions: set[str], latest: str
) -> list[str]:
    """LATEST 以外、卻沒被排除的版本目錄（＝仍在 ruff 掃描面的凍結版）。"""
    return sorted(v for v in versions if v != latest and not is_excluded(patterns, v))


def _config() -> dict:
    assert os.path.isfile(_ROOT_RUFF_TOML), (
        "repo 根沒有 ruff.toml ⇒ 凍結版回到 ruff 掃描面，根層 `ruff check .` 會被"
        "結構上不可修的存量命中壓紅（DEF-101-018 的解鎖條件消失）"
    )
    return tomllib.loads(Path(_ROOT_RUFF_TOML).read_text(encoding="utf-8"))


def _patterns() -> list[str]:
    return _config()["extend-exclude"]


def _latest_and_versions() -> tuple[str, set[str]]:
    ignored: list[str] = []  # 未 tracked 合法名目錄的警告：此處用不到，收走免得洗版
    latest = sdd_version.latest_version_name(Path(_SDD_ROOT), warn=ignored.append)
    assert latest, f"{_SDD_ROOT} 找不到任何 LATEST 版本目錄"
    tracked = sdd_version.tracked_version_dirs(Path(_SDD_ROOT))
    versions = tracked if tracked is not None else sdd_version.disk_version_dirs(Path(_SDD_ROOT))
    return latest, versions


def test_root_config_does_nothing_but_extend_exclude():
    """根檔只准有 `extend-exclude` 一個鍵：不選規則、不改 line-length、不指定 target。"""
    keys = set(_config())
    assert keys == {"extend-exclude"}, (
        f"根 ruff.toml 的頂層鍵是 {sorted(keys)}，不只 extend-exclude ⇒ AISDLC_SDD 不再走 "
        "ruff 出廠預設（`tools/ruff.toml` 檔頭：納管 AISDLC_SDD 是另一個授權面的決定）"
    )


def test_latest_stays_in_the_scan_surface():
    latest, _ = _latest_and_versions()
    assert not is_excluded(_patterns(), latest), (
        f"根 ruff.toml 的 extend-exclude 吃到了 LATEST（{latest}）⇒ 唯一可演化的版本變成"
        f"沒人 lint 的法外之地；樣式 {_patterns()} 要收窄到只含凍結版"
    )


def test_frozen_baseline_is_excluded():
    """正控：凍結基線 v0.01 必在排除面（防比對器退化成恆假、讓上一支恆綠）。"""
    assert is_excluded(_patterns(), "AISDLC_SDD_v0.01"), (
        "凍結基線 AISDLC_SDD_v0.01 不在 extend-exclude 內 ⇒ 它的存量命中會壓紅根層 "
        "`ruff check .`，而該目錄不可原地改"
    )


def test_every_non_latest_version_is_excluded():
    """LATEST 前進後此鎖會紅，訊息逐字指出要補進清單的版本。"""
    latest, versions = _latest_and_versions()
    leaked = frozen_versions_still_scanned(_patterns(), versions, latest)
    assert not leaked, (
        f"LATEST 現為 {latest}，但凍結版 {leaked} 仍在 ruff 掃描面 ⇒ 請把它們補進根 "
        f"ruff.toml 的 extend-exclude（現有樣式：{_patterns()}）；凍結版不可原地改，"
        "存量命中只能靠排除消去"
    )


_FROZEN_PATTERNS = [
    "AISDLC_SDD/AISDLC_SDD_v0.0*",
    "AISDLC_SDD/AISDLC_SDD_v0.1*",
    "AISDLC_SDD/AISDLC_SDD_v0.2*",
]


def test_criterion_is_red_when_latest_advances_without_updating_the_list():
    """自證（合成輸入）：v0.30 → v0.31 後 v0.30 成了凍結版，樣式沒補就必須被抓到。"""
    versions = {"AISDLC_SDD_v0.01", "AISDLC_SDD_v0.29", "AISDLC_SDD_v0.30", "AISDLC_SDD_v0.31"}
    assert frozen_versions_still_scanned(
        _FROZEN_PATTERNS, versions, "AISDLC_SDD_v0.31"
    ) == ["AISDLC_SDD_v0.30"]
    # 補進清單後轉綠；LATEST 本身仍不得被排除
    patched = [*_FROZEN_PATTERNS, "AISDLC_SDD/AISDLC_SDD_v0.30"]
    assert frozen_versions_still_scanned(patched, versions, "AISDLC_SDD_v0.31") == []
    assert not is_excluded(patched, "AISDLC_SDD_v0.31")


def test_criterion_is_red_when_a_pattern_swallows_latest():
    """自證（合成輸入）：樣式寫太寬吃到 LATEST 必須被 `is_excluded` 看見。"""
    assert not is_excluded(_FROZEN_PATTERNS, "AISDLC_SDD_v0.30")
    assert is_excluded([*_FROZEN_PATTERNS, "AISDLC_SDD/AISDLC_SDD_v0.3*"], "AISDLC_SDD_v0.30")
