# Shell 注入防護黑名單字元集 SSOT（DEF-101-238 收斂；R55 四方複審）。
#
# sdd_to_playbook_adapter.py / goal_freeze_gate.py（及 AutoClaude/tools/
# three_tier_to_playbook.py）曾各自宣告獨立字面值黑名單集合，僅靠註解宣稱超集關係
# （如「⊇ SddToPlaybookAdapter._DENY」），無機械測試鎖定，逾 39 輪未收斂（R16
# DEF-101-238 起）。各呼叫端改為 `BASE_DENY_CHARS | {...呼叫端專屬追加字元}` 顯式
# 聯集，取代重複字面值；超集關係機械斷言見 tests/test_shell_deny_chars_parity.py。
#
# 刻意不收斂範圍：execution/mutation_applier/_conditional.py 與
# core/services/mutation/_conditional_evaluator.py 的白名單 regex 與黑名單
# _DENY_CHARS（執行語意不同：shell=True 原生殼 vs shell=False+shlex.split；`!`
# 是否放行的差異已由 DEF-101-238 SD 一審確認非安全漏洞）——本模組只收斂已於註解
# 中明文宣稱同源的 spec-fragment 消毒家族，不變更任何既有執行行為。
BASE_DENY_CHARS: frozenset[str] = frozenset("!`><~$&;")
