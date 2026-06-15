"""tools — AISDLC-SDD 工具套件根（v0.02 / DEF-01-003 修正）。

顯式 package 宣告：`python -m tools.arch_fitness.arch_fitness` /
`python -m tools.fsm_runtime.*` 原依賴 py3.3+ implicit namespace package，
補本檔後改為顯式 regular package，行為更穩健（import 解析不受 sys.path
上同名 namespace 影響）。
"""
