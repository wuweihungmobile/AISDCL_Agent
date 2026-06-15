"""Phase L M-L1 / ACT-089~090 — Self-Improving Meta-Loop Halting（自我改進元迴圈停機）.

對應藍圖：build/planning/active/SDD_improving_Automation_12.md §1.2 / PL-1（L10 奠基石）。

框架有三條會跨 session 修改「常駐治理規則集」的相反迴圈：
  - 學習層（Phase E M4 / slv_generator）：ESCALATION→FPL→SLV proposed→verified（單調加規則）
  - 鷹架 GC（Phase H M5 / scaffold_gc + rule_loader.set_maturity）：退役 0-fire 規則（移除規則）
  - FSE 自我演化（arch_fitness）：新增 fitness function

單軌 `SDD_FSM.tla` 與艦隊 `FLEET_FSM.tla` 皆已形式化證明必達 terminal，但上述「加↔退」
元迴圈的**聯合收斂性從未形式化**——理論上可 add↔retire 抖動（學 SLV→0-fire 退役→
同型歧義再 escalate→重學語意同型 SLV'→…），即「框架自我改進」本身不停機。

本子套件補上這個閉環：
  - `meta_ledger`：跨 session churn 帳本（add/retire 事件 + 指紋 + capability_level）
  - `meta_halt_monitor`：ChurnBounded / GraduationRatchet 兩道有界停機守門
  - `formal/META_FSM.tla`：獨立命名空間形式化（不污染單軌，比照 FLEET_FSM）
"""
from __future__ import annotations

__all__ = ["meta_ledger", "meta_halt_monitor"]
