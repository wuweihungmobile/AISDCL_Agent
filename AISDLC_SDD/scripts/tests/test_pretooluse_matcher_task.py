"""PreToolUse matcher 必含 Task — DEF-CLDREV-017 回歸鎖.

為何重要（Rule 9）：`context_ledger_pre.py` 的 ACT-020 子代理派發契約注入
（`_build_subagent_notice`，Rule 9.8.4）**只在 `tool_name == "Task"` 時觸發**；若 PreToolUse
matcher 不含 `Task`，Claude Code 永不會在 Task（子代理）派發時執行此 hook，注入分支即 dead
code。此縫自 v0.01 休眠至 v0.18（跨 19 版 matcher 一致缺 Task），DEF-CLDREV-017 經掌舵者裁定
啟用：在「根 router settings」與「最新演化版 settings」兩處 PreToolUse matcher 補 `Task`。

本鎖機械守護該啟用不被回退——移除任一處的 `Task` 即此 case 轉紅（取代「人工記得雙改」）。
與 `test_router_hook_coverage_lint.py`（守 hook **event 可達性**）互補：此處守 PreToolUse
matcher **內容**。
"""
from __future__ import annotations

import json
import os

from scripts import router_hook_coverage_lint as lint


def _sdd_root() -> str:
    """test 檔在 AISDLC_SDD/scripts/tests/ → 三層 dirname = AISDLC_SDD/（同 router lint 慣例）。"""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _monorepo_root() -> str:
    """根 router settings.json 位於 AISDLC_SDD/ 的上一層（monorepo 整合層根）。"""
    return os.path.dirname(_sdd_root())


def _pretooluse_matchers(settings_path: str) -> list[str]:
    with open(settings_path, encoding="utf-8") as f:
        doc = json.load(f)
    return [
        blk["matcher"]
        for blk in doc.get("hooks", {}).get("PreToolUse", [])
        if blk.get("matcher") is not None
    ]


def test_root_router_pretooluse_matcher_includes_task():
    settings = os.path.join(_monorepo_root(), ".claude", "settings.json")
    matchers = _pretooluse_matchers(settings)
    assert matchers, f"根 settings.json 無 PreToolUse matcher：{settings}"
    for m in matchers:
        assert "Task" in m.split("|"), (
            f"根 router PreToolUse matcher 缺 Task：{m!r} — ACT-020 子代理注入將不觸發（DEF-CLDREV-017）"
        )


def test_latest_version_pretooluse_matcher_includes_task():
    res = lint.analyze(_sdd_root())
    latest = res.get("latest")
    assert latest, "找不到最新演化版（router lint analyze 回 latest=None）"
    settings = os.path.join(_sdd_root(), latest, ".claude", "settings.json")
    matchers = _pretooluse_matchers(settings)
    assert matchers, f"{latest} settings.json 無 PreToolUse matcher"
    for m in matchers:
        assert "Task" in m.split("|"), (
            f"{latest} PreToolUse matcher 缺 Task：{m!r}（DEF-CLDREV-017）"
        )
