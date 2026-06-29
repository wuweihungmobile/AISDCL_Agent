## 🔴 Rule 9：自動化閉環防護規則（憲法摘要）

> **🔴 重要**：完整 Rule 9 細則已結構化於 `AISDLC_SDD_v0.01/governance/rules/R-*.yaml`，
> 由 `rule_loader.load_for_state()` 依當前 FSM 狀態 lazy-load；SessionStart hook
> （`.claude/hooks/session_start.py`）會自動注入當前狀態命中的規則。完整地圖見
> `AISDLC_SDD_v0.01/governance/RULES_INDEX.md`（23 條規則一覽）。
>
> 本節僅保留**永遠生效、違反即停機的絕對禁令**（憲法層）。各 Phase 子規則、ACT 對照、
> 相關文件與驗收憑證一律見對應 `R-*.yaml`。

以下規則確保 SDD Agentic 閉環具備有界停機能力，防止無限重試耗盡 Token。

### 絕對禁令（不可違反，違反即停機）

1. 繞過 `FSMRuntime` 直接讀寫 `FSM-STATE-*.yaml`（R-9.6）
2. 停用 / 刪除 `.claude/` 的 Phase D·E hooks（R-9.6）
3. IMPLEMENTATION 期間 Write/Edit `docs/01~03` 規格文件（R-9.6）
4. SCG/PR/RTM retry 超上限仍重試、不進 ESCALATION（R-9.1）
5. Token ≥ 95% 仍工作、不產 Context Snapshot（R-9.2）
6. 進入 ESCALATION / ESCALATION_FINAL 後自動恢復（必須等人工）（R-9.5、R-9.14）
7. 對 `category=structural` 的 ESCALATION 強行 auto-recovery（R-9.14）
8. 修改 `_HAPPY_PATH` 但不同步 `formal/SDD_FSM.tla`（R-9.18）
9. 把觀測狀態放入 Terminals 集合（R-9.18）
10. 讓 `proposed` / `external` 規則阻塞 SCG（R-9.11）
11. 自動退役 active 規則而不經 `set_maturity(reviewed_by=)`（R-9.20）
12. 自動套用 spec patch 改 FRD/AC 而不經 HUMAN_PENDING（R-9.22）

### 核心機制速查

| 機制 | 摘要 | 細則 |
|------|------|------|
| Retry Budget | SCG 3 / PR 5 / RTM 2 次 → ESCALATION | R-9.1 |
| Context Budget | 70 / 85 / 90 / 95% 四階；≥95% 停機 | R-9.2 |
| 邏輯一致性 | SCG-0/3 前跑 spec-logical-validator | R-9.3 |
| SPEC_FROZEN | 通過後強制 /stage-compaction | R-9.4 |
| Runtime Hooks | settings.json `deny` 強制層 | R-9.6 |
| Chaos 驗收 | 100 輪 bounded_ratio==1.0 | R-9.9 |
| Formal 驗證 | TLA+/TLC 雙源一致 + reachable | R-9.18 |
| 對抗 / 自癒 | 對抗判官 + spec patch（proposed） | R-9.21、R-9.22 |

> 其餘 Phase D~J 各層（精準停機、閉環品質鏈、學習層、Hub、多模態、預測性停機、
> 成本治理、執行接地、鷹架代謝、艦隊並行…）的完整定義見 `governance/rules/R-9.*.yaml`
> 與 `governance/RULES_INDEX.md`，由 runtime 依狀態注入。
