"""Shell 注入防護黑名單字元集 SSOT parity 測試（DEF-101-238 收斂；R55 四方複審）。

sdd_to_playbook_adapter._DENY / goal_freeze_gate._DENY /
tools/three_tier_to_playbook._DENY 三個呼叫端皆改為
``BASE_DENY_CHARS | {...呼叫端專屬追加字元}`` 顯式聯集（見
autoclaude/utils/shell_deny_chars.py）。本測試機械鎖定：

  1. 三個呼叫端的 ``_DENY`` 恆為 ``BASE_DENY_CHARS`` 的超集（不會有人漏改造成
     悄悄縮小為子集）；
  2. 三個呼叫端目前的實際字元集與收斂前的歷史字面值完全一致（零行為變更迴歸鎖）。
"""
from __future__ import annotations

from autoclaude.infra.adapters.goal_freeze_gate import _DENY as _GOAL_FREEZE_DENY
from autoclaude.infra.adapters.sdd_to_playbook_adapter import _DENY as _SDD_ADAPTER_DENY
from autoclaude.utils.shell_deny_chars import BASE_DENY_CHARS
from tools.three_tier_to_playbook import _DENY as _THREE_TIER_DENY


def test_sdd_adapter_deny_equals_base():
    """sdd_to_playbook_adapter._DENY 是最初的 8 字元基準本身（無額外追加）。"""
    assert set(_SDD_ADAPTER_DENY) == set(BASE_DENY_CHARS) == set("!`><~$&;")


def test_goal_freeze_gate_deny_is_superset_of_base():
    """goal_freeze_gate._DENY ⊇ BASE_DENY_CHARS，且與收斂前歷史字面值一致。"""
    assert set(_GOAL_FREEZE_DENY) >= set(BASE_DENY_CHARS)
    assert set(_GOAL_FREEZE_DENY) == set("!`><~$&;|")


def test_three_tier_to_playbook_deny_is_superset_of_base():
    """three_tier_to_playbook._DENY ⊇ BASE_DENY_CHARS，且與收斂前歷史字面值一致。"""
    assert set(_THREE_TIER_DENY) >= set(BASE_DENY_CHARS)
    assert set(_THREE_TIER_DENY) == set("!`><~$&;\n\r")
