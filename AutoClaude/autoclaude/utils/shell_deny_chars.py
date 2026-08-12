# Shell 注入防護黑名單字元集 SSOT（DEF-101-238 收斂；R55 四方複審）。
#
# sdd_to_playbook_adapter.py / goal_freeze_gate.py（及 AutoClaude/tools/
# three_tier_to_playbook.py）曾各自宣告獨立字面值黑名單集合，僅靠註解宣稱超集關係
# （如「⊇ SddToPlaybookAdapter._DENY」），無機械測試鎖定，逾 39 輪未收斂（R16
# DEF-101-238 起）。各呼叫端改為 `BASE_DENY_CHARS | {...呼叫端專屬追加字元}` 顯式
# 聯集，取代重複字面值；超集關係機械斷言見 tests/test_shell_deny_chars_parity.py。
#
# 刻意不收斂範圍：兩支 CONDITIONAL 白名單 regex。執行語意確實不同（shell=True 原生殼
# vs shell=False+shlex.split），故 R85 複查後**維持不收斂**，但做了兩件事：
#
# ① **改名讓兩者分得開**（R85／訴求 2）。兩邊原本都叫 `_SAFE_COND_PATTERN`，同名不同義
#    是最容易被誤讀成「同一份知識住兩個家」的形態——而一旦有人「順手收斂」，就會把兩種
#    執行語意混成一個。現在分別是：
#      · execution/mutation_applier/_conditional.py → `_SHELL_TRUE_COND_WHITELIST`
#      · core/services/mutation/_conditional_evaluator.py → `_SHELL_FALSE_COND_WHITELIST`
#
# ② 🔴 **記下一個原註解沒說、且方向是反的事實**：走 `shell=True`（嚴格更危險）的那一支
#    **比較寬鬆**——它放行 `!` 且**沒有**黑名單；走 `shell=False`+shlex.split（本來就安全
#    得多）的那一支反而額外壓一層 `_DENY_CHARS`。安全姿態與危險程度成反比，這不是「語意
#    不同」能解釋的，是一個尚未處置的傾斜。原註解只寫「`!` 的差異已確認非安全漏洞」，
#    那句話回答的是「會不會出事」，沒有回答「為什麼比較危險的那邊防得比較少」。
#    R85 未動它（改資安姿態需要專門的威脅模型複審，不在減法輪射程），僅登記。
#
# 🔴 第三份副本（R85 實測）：tests/test_gap039_049.py 內以字面值硬抄了一份 shell=True 的
#    regex，註解自稱「與生產碼一致」，但**沒有任何機械物在比對這件事**——生產端改了它不會
#    紅。真正的一致性鎖在 tests/execution/test_shell_portability_contract_r85.py（直接 import
#    生產常數）。
#
# 本模組本身只收斂已於註解中明文宣稱同源的 spec-fragment 消毒家族，不變更任何既有執行行為。
BASE_DENY_CHARS: frozenset[str] = frozenset("!`><~$&;")
