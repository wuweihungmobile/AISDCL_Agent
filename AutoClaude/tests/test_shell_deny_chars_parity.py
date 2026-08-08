"""Shell 注入防護黑名單字元集 SSOT parity 測試（DEF-101-238 收斂；R55 四方複審）。

sdd_to_playbook_adapter._DENY / goal_freeze_gate._DENY /
tools/three_tier_to_playbook._DENY 三個呼叫端皆改為
``BASE_DENY_CHARS | {...呼叫端專屬追加字元}`` 顯式聯集（見
autoclaude/utils/shell_deny_chars.py）。本測試機械鎖定：

  1. 三個呼叫端的 ``_DENY`` 恆為 ``BASE_DENY_CHARS`` 的超集（不會有人漏改造成
     悄悄縮小為子集）；
  2. 三個呼叫端目前的實際字元集與收斂前的歷史字面值完全一致（零行為變更迴歸鎖）；
  3. **（R56 補）三個呼叫端的原始碼必須真的引用 SSOT**，不得把字面值抄回去。

R56 修正（QA 發現，兩項）：
  (a) 原 ``test_sdd_adapter_deny_equals_base`` 的
      ``set(_SDD_ADAPTER_DENY) == set(BASE_DENY_CHARS)`` 是**恆真斷言** ——
      sdd_to_playbook_adapter.py 是 ``import BASE_DENY_CHARS as _DENY``，兩者
      本來就是同一個物件，``x == x`` 不可能失敗，卻讓讀者以為守到了「無額外
      追加」。改以 ``is`` 明示真正想鎖的關係（別名匯入本身），比 ``==`` 誠實
      且更嚴格。
  (b) 原三支測試全部只比較 ``set(...)`` 的**值**，不鎖 SSOT 的**用法**：若有人
      把 ``_DENY = BASE_DENY_CHARS | {"|"}`` 改回字面值 ``set("!`><~$&;|")``，
      三支測試仍全綠 —— 而「各站點各自宣告獨立字面值黑名單」正是逾 39 輪未收斂
      的 DEF-101-238 病灶本體，收斂完成後卻沒有任何鎖阻止它復發。新增
      ``test_all_sites_derive_deny_from_ssot_in_source``（比照 root
      tools/tests/test_windowsapps_guard_bash_parity.py 的原始碼掃描慣例）補上
      這道「用法鎖」，並補一支 goal_freeze_gate 的行為層測試，確保黑名單真的
      接在裁決路徑上（原本除本檔外無任何測試覆蓋該 adapter 的注入字元分支）。
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from autoclaude.infra.adapters.goal_freeze_gate import _DENY as _GOAL_FREEZE_DENY
from autoclaude.infra.adapters.goal_freeze_gate import BoundedGoalFreezeGate
from autoclaude.infra.adapters.sdd_to_playbook_adapter import _DENY as _SDD_ADAPTER_DENY
from autoclaude.utils.shell_deny_chars import BASE_DENY_CHARS
from tools.three_tier_to_playbook import _DENY as _THREE_TIER_DENY

_PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 每個呼叫端「_DENY 必須由 SSOT 推導」的原始碼形狀。任一站點改回裸字面值即失配。
_SSOT_DERIVATION_SITES = (
    (
        "autoclaude/infra/adapters/sdd_to_playbook_adapter.py",
        r"^from \.\.\.utils\.shell_deny_chars import BASE_DENY_CHARS as _DENY$",
    ),
    (
        "autoclaude/infra/adapters/goal_freeze_gate.py",
        r"^_DENY = BASE_DENY_CHARS \| \{",
    ),
    (
        "tools/three_tier_to_playbook.py",
        r"^_DENY = BASE_DENY_CHARS \| \{",
    ),
)


def test_sdd_adapter_deny_equals_base():
    """sdd_to_playbook_adapter._DENY 就是 BASE_DENY_CHARS 本體（別名匯入，無額外追加）。"""
    assert _SDD_ADAPTER_DENY is BASE_DENY_CHARS
    assert set(BASE_DENY_CHARS) == set("!`><~$&;")


def test_goal_freeze_gate_deny_is_superset_of_base():
    """goal_freeze_gate._DENY ⊇ BASE_DENY_CHARS，且與收斂前歷史字面值一致。"""
    assert set(_GOAL_FREEZE_DENY) >= set(BASE_DENY_CHARS)
    assert set(_GOAL_FREEZE_DENY) == set("!`><~$&;|")


def test_three_tier_to_playbook_deny_is_superset_of_base():
    """three_tier_to_playbook._DENY ⊇ BASE_DENY_CHARS，且與收斂前歷史字面值一致。"""
    assert set(_THREE_TIER_DENY) >= set(BASE_DENY_CHARS)
    assert set(_THREE_TIER_DENY) == set("!`><~$&;\n\r")


@pytest.mark.parametrize(("rel_path", "pattern"), _SSOT_DERIVATION_SITES)
def test_all_sites_derive_deny_from_ssot_in_source(rel_path, pattern):
    """R56 用法鎖：三個呼叫端的 `_DENY` 必須由 `BASE_DENY_CHARS` 推導，不得抄字面值。

    只鎖「值」不鎖「用法」會讓 DEF-101-238 的病灶（各站點各自宣告字面值黑名單）
    悄悄復發而測試全綠 —— 抄回去的字面值當下與 SSOT 等值，值比對抓不到，之後
    SSOT 增修一個字元才會分岔，而那時已無測試會紅。本測試直接對原始碼斷言推導
    關係，讓「複製字面值」這個動作本身即刻失敗。
    """
    src = (_PROJECT_ROOT / rel_path).read_text(encoding="utf-8")
    assert re.search(pattern, src, flags=re.MULTILINE), (
        f"{rel_path} 的 _DENY 未由 SSOT autoclaude/utils/shell_deny_chars.py"
        f" 推導（預期原始碼含 {pattern!r}）——DEF-101-238 字面值複製復發"
    )


@pytest.mark.parametrize("bad_char", sorted(BASE_DENY_CHARS | {"|"}))
def test_goal_freeze_gate_rejects_each_deny_char(bad_char):
    """行為層鎖：黑名單真的接在 BoundedGoalFreezeGate 裁決路徑上（非僅宣告）。

    R56 QA 發現：收斂前後都只有字元集比對，若哪天 `_DENY` 的消費點（evaluate()
    內的 tainted 掃描）被拿掉或條件寫反，字元集測試仍會全綠。本測試逐一餵入每個
    黑名單字元，斷言一律 fail-closed 拒絕自動 signoff。

    🔴 DEF-101-470：本測試原本只餵**一筆** prompt，於是把 `goal_freeze_gate.py` 的
    `for i, prompt in enumerate(prompts)` 改成 `enumerate(prompts[:1])` 仍全綠——
    而 gate 的意義正是對「多步驟拆解」**逐步**掃描，只掃第 0 筆等於步驟 1~11 的
    注入字元一律自動放行。改成髒字元放在**第二筆**，並斷言 reason 逐字指名
    `步驟 1`（`enumerate` 為 0-based ⇒ 第二筆＝索引 1），讓上述退化當場轉紅。
    """
    gate = BoundedGoalFreezeGate()
    verdict = gate.evaluate(
        goal_hash="h1",
        step_count=2,
        prompts=("clean step", f"build the thing {bad_char} now"),
    )
    assert verdict.auto_approved is False, f"含注入嫌疑字元 {bad_char!r} 不應自動放行"
    assert "注入嫌疑字元" in verdict.reason
    assert "步驟 1" in verdict.reason, (
        f"gate 必須指名是**第二筆** prompt 觸發（reason={verdict.reason!r}）——"
        "只掃第 0 筆的退化就是 DEF-101-470 的形狀"
    )


def test_goal_freeze_gate_approves_clean_prompt():
    """對照組：無黑名單字元 + 有界步驟數 + 有 goal_hash → 自動 signoff（防過度攔截）。"""
    gate = BoundedGoalFreezeGate()
    verdict = gate.evaluate(goal_hash="h1", step_count=2, prompts=("step one", "step two"))
    assert verdict.auto_approved is True
