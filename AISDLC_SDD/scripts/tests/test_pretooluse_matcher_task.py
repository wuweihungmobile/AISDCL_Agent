"""PreToolUse matcher 必含 Task — DEF-CLDREV-017 回歸鎖.

為何重要（Rule 9）：`context_ledger_pre.py` 的 ACT-020 子代理派發契約注入
（`_build_subagent_notice`，Rule 9.8.4）**只在 `tool_name == "Task"` 時觸發**；若承載它的
PreToolUse 條目 matcher 不含 `Task`，Claude Code 永不會在 Task（子代理）派發時執行該 hook，
注入分支即 dead code。此縫自 v0.01 休眠至 v0.18（跨 19 版 matcher 一致缺 Task），
DEF-CLDREV-017 經掌舵者裁定啟用：在「根 router settings」與「最新演化版 settings」兩處補 `Task`。

本鎖機械守護該啟用不被回退——把 `Task` 從承載條目移除即此 case 轉紅（取代「人工記得雙改」）。
與 `test_router_hook_coverage_lint.py`（守 hook **event 可達性**）互補：此處守 PreToolUse
matcher **內容**。

🔴 本輪訂正：判準由「所有 matcher」收斂為「承載 ACT-020 注入的那些 matcher」
------------------------------------------------------------------------
上面那段 WHY 要保證的東西只有一個：**子代理注入走的那支 hook 會在 Task 派發時被觸發**。
而原判準寫成對根 settings.json 內**每一個** PreToolUse 條目的全稱約定，射程遠大於它的理由。

代價不是理論上的。根 settings.json 除了 router 條目之外還住著獨立的守衛型 hook，那類 hook
對「解析不出工具名的退化 payload」是 fail-closed（exit 2 阻斷）——這對它們自己是對的設計。
兩者相乘的結果：守衛為了滿足全稱約定而把 `Task` 收進自己的 matcher，於是一份退化 payload
會讓一支**與 Task 無關的守衛**硬擋掉子代理派工，訊息還指向不相干的原因。本輪七輸入實測
逐字重現該狀態（`block_bash_on_windows.py` 對缺 `tool_name` 的 payload 回 rc=2）。

這是「兩道鎖的合法動作互為對方違規」的形態：A 鎖要求把 `Task` 加進 matcher，B 鎖要求
退化 payload 必須 fail-closed，交界處產生一個誰都沒同意的行為。處置是**讓兩道鎖各自
表達它真正要的東西**，而不是放棄其中一邊：
  · 本鎖收斂到「承載 ACT-020 注入的條目」（＝它的 WHY 本來就只要求這個）；
  · 對稱的另一半在 `tools/tests/test_check_hooks_liveness.py`：**任何對退化 payload
    回 rc=2 的守衛，其 matcher 不得含有自己射程之外的工具**。
兩條合起來仍然把原來的保證守滿，而且不再互咬。

非空轉：找不到任何承載條目本身即紅（見 `_MISSING_CARRIER`）——把 router 條目整個刪掉
不能變成「沒有條目要檢查所以通過」。
"""
from __future__ import annotations

import json
import os

from scripts import router_hook_coverage_lint as lint

#: 承載 ACT-020 子代理注入的 hook（根層走 router 轉發，各演化版走實體 hook）。
ACT020_CARRIER_MARKERS = ("context_ledger_pre", "sdd_hook_router")

_MISSING_CARRIER = (
    "PreToolUse 內找不到任何承載 ACT-020 子代理注入的條目"
    f"（command 需指名 {' 或 '.join(ACT020_CARRIER_MARKERS)}）"
    " — 注入分支變成 dead code，且本鎖會退化成恆綠（DEF-CLDREV-017）"
)


def _sdd_root() -> str:
    """test 檔在 AISDLC_SDD/scripts/tests/ → 三層 dirname = AISDLC_SDD/（同 router lint 慣例）。"""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _monorepo_root() -> str:
    """根 router settings.json 位於 AISDLC_SDD/ 的上一層（monorepo 整合層根）。"""
    return os.path.dirname(_sdd_root())


def _load(settings_path: str) -> dict:
    with open(settings_path, encoding="utf-8") as f:
        return json.load(f)


def is_act020_carrier(entry: dict) -> bool:
    """該 PreToolUse 條目是否承載 ACT-020 注入（依 hook command 內的腳本名判定）。"""
    for hook in entry.get("hooks") or []:
        command = str(hook.get("command", ""))
        if any(marker in command for marker in ACT020_CARRIER_MARKERS):
            return True
    return False


def act020_task_matcher_verdict(doc: dict) -> str | None:
    """`None`＝承載條目的 matcher 都含 Task；回字串＝失效理由（純函式，供注入自證）。"""
    entries = [
        blk for blk in doc.get("hooks", {}).get("PreToolUse", []) or []
        if isinstance(blk, dict)
    ]
    carriers = [blk for blk in entries if is_act020_carrier(blk)]
    if not carriers:
        return _MISSING_CARRIER
    for blk in carriers:
        matcher = blk.get("matcher")
        if matcher is None or "Task" not in str(matcher).split("|"):
            return (
                f"承載 ACT-020 注入的 PreToolUse matcher 缺 Task：{matcher!r}"
                " — 子代理派發時該 hook 不會被觸發（DEF-CLDREV-017）"
            )
    return None


def test_root_router_pretooluse_matcher_includes_task():
    settings = os.path.join(_monorepo_root(), ".claude", "settings.json")
    doc = _load(settings)
    assert doc.get("hooks", {}).get("PreToolUse"), f"根 settings.json 無 PreToolUse 條目：{settings}"
    verdict = act020_task_matcher_verdict(doc)
    assert verdict is None, f"{settings}：{verdict}"


def test_latest_version_pretooluse_matcher_includes_task():
    res = lint.analyze(_sdd_root())
    latest = res.get("latest")
    assert latest, "找不到最新演化版（router lint analyze 回 latest=None）"
    settings = os.path.join(_sdd_root(), latest, ".claude", "settings.json")
    doc = _load(settings)
    assert doc.get("hooks", {}).get("PreToolUse"), f"{latest} settings.json 無 PreToolUse 條目"
    verdict = act020_task_matcher_verdict(doc)
    assert verdict is None, f"{latest}：{verdict}"


def test_criterion_is_red_when_the_carrier_loses_task():
    """注入自證①：把 Task 從承載條目拿掉必須轉紅（收斂射程 ≠ 放棄保證）。"""
    doc = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Write|Edit|Read|Bash|NotebookEdit",
                    "hooks": [{"command": "... .claude/hooks/context_ledger_pre.py"}],
                }
            ]
        }
    }
    verdict = act020_task_matcher_verdict(doc)
    assert verdict is not None and "缺 Task" in verdict, verdict


def test_criterion_is_green_for_a_narrow_non_carrier_guard():
    """注入自證②：非承載條目（獨立守衛）用窄 matcher 必須放行。

    這正是收斂射程要換到的東西——守衛得以把 matcher 收到自己那一個工具，
    fail-closed 分支的爆炸半徑才回到它的職責範圍內。
    """
    doc = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Write|Edit|Read|Bash|NotebookEdit|Task",
                    "hooks": [{"command": "... .claude/hooks/sdd_hook_router.py context_ledger_pre"}],
                },
                {
                    "matcher": "Bash",
                    "hooks": [{"command": "... .claude/hooks/block_bash_on_windows.py"}],
                },
            ]
        }
    }
    assert act020_task_matcher_verdict(doc) is None


def test_criterion_is_red_when_no_carrier_exists_at_all():
    """注入自證③：反空轉——承載條目被整個刪掉不得變成「沒東西要檢查所以通過」。"""
    doc = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"command": "x.py"}]}]}}
    verdict = act020_task_matcher_verdict(doc)
    assert verdict is not None and "dead code" in verdict, verdict
