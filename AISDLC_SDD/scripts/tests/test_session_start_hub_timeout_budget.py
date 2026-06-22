"""SessionStart 嵌套 timeout 不變量 — DEF-CLDREV-026 回歸鎖.

為何重要（架構）：根 router 對 SessionStart child 設硬上限
`_CHILD_TIMEOUT["SessionStart"]`（現 25s，刻意 < 外層 settings.json 的 30s，留餘裕讓 router
被外層砍掉前印 fail-safe 放行 JSON）。但 `session_start.py` 的 Hub auto-pull 會 shell out
`git clone/fetch`，其 timeout 取 LATEST `knowledge/hub-registry.yaml` 的
`sync_policy.pull.timeout_seconds`。該值原為 30 > 25 → 啟用 Hub 後若 pull 慢，router 會先在
25s 砍掉整支 session_start，FSM bootstrap 注入（decision-trace / 當前狀態規則 / ESCALATION
warnings）全部蒸發，session 在無 SDD 治理 context 下啟動（Architect 鏡 [A6-01]）。

本鎖機械守護嵌套不變量：外層 settings 30 ⊃ router child 25 ⊃ hub pull 20，hub pull 必
+ 5s headroom ≤ router SessionStart 上限（餘裕給 session_start 其餘 bootstrap + router
fail-safe）。任一處漂移使 hub pull 逼近/超過 router 上限即此 case 轉紅。
"""
from __future__ import annotations

import ast
import os
import re

import yaml

from scripts import router_hook_coverage_lint as lint

# session_start 除 hub pull 外尚有本地 bootstrap（reconcile_ci_events / timeout_checker /
# scan_inbox），加上 router 自身 fail-safe 餘裕；hub pull 必須比 router 上限至少小此秒數。
_HEADROOM_SEC = 5.0


def _sdd_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _monorepo_root() -> str:
    return os.path.dirname(_sdd_root())


def _router_session_start_cap() -> float:
    """從根 router 原始碼解析 _CHILD_TIMEOUT['SessionStart']（ast 解析、不 import 以免副作用）。"""
    path = os.path.join(_monorepo_root(), ".claude", "hooks", "sdd_hook_router.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"_CHILD_TIMEOUT\s*=\s*(\{[^}]*\})", src)
    assert m, f"找不到 _CHILD_TIMEOUT 字面量：{path}"
    table = ast.literal_eval(m.group(1))
    assert "SessionStart" in table, f"_CHILD_TIMEOUT 缺 SessionStart：{table!r}"
    return float(table["SessionStart"])


def _latest_hub_pull_timeout() -> float:
    res = lint.analyze(_sdd_root())
    latest = res.get("latest")
    assert latest, "找不到最新演化版（router lint analyze 回 latest=None）"
    path = os.path.join(_sdd_root(), latest, "knowledge", "hub-registry.yaml")
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    pull = (doc.get("sync_policy") or {}).get("pull") or {}
    return float(pull.get("timeout_seconds", 30))


def test_hub_pull_timeout_fits_within_router_session_start_cap():
    cap = _router_session_start_cap()
    hub = _latest_hub_pull_timeout()
    assert hub + _HEADROOM_SEC <= cap, (
        f"嵌套 timeout 不變量破壞：hub pull timeout={hub}s + headroom {_HEADROOM_SEC}s "
        f"> router SessionStart 上限 {cap}s（DEF-CLDREV-026）。啟用 Hub 後慢 pull 會致 router "
        f"先砍 session_start、FSM 注入蒸發。請降低 hub-registry.yaml pull.timeout_seconds。"
    )
