# SDD Spec-First Gate Workflow
# 規格優先閘門工作流程

**版本**: v1.1
**建立日期**: 2026-04-12
**最後更新**: 2026-04-18
**工作流程類型**: 品質閘門（Quality Gate）
**分類**: SDD Phase 01 新增；Phase A 強化（FSM 整合）

---

## 🎯 工作流程目的

強制執行 SDD（Spec-First）原則：規格必須先於所有實作行為完成並通過驗證。

---

## 🔗 FSM 整合

本工作流程已整合至 [SDD_FSM_ENGINE.md](../sdd-fsm-engine/SDD_FSM_ENGINE.md)。

| FSM 狀態 | 對應 SCG 動作 | Retry Limit |
|---------|-------------|------------|
| SCG_VALIDATION | SCG-0, SCG-1, SCG-2, SCG-3 驗證 | 最多 **3 次** → ESCALATION |
| PR_REVIEW | SCG-4 實作審查 | 最多 **5 次**；相同模式 3 次 → SPEC_AUDIT |
| RTM_VERIFY | SCG-5 RTM 完整性驗證 | 最多 **2 次** → ESCALATION |
| RELEASE_READY | SCG-6 發布確認 | — |
| SPEC_FROZEN | SCG 通過後 → 觸發 stage-compaction | — |
| ESCALATION | retry 耗盡後 → 強制人工介入 | 不可自動退出 |

**退場機制**：見 [SDD_ESCALATION_PROTOCOL.md](../sdd-escalation/SDD_ESCALATION_PROTOCOL.md)

---

## 🔷 SCG 閘門類型與觸發條件

> ⚠️ **SCG 編號以 AISDLC_SDD_INIT.md 與 CLAUDE.md 為唯一真理來源（SSoT）。**

| 閘門 | 名稱 | 觸發條件 | 主責 Agent |
|-----|------|---------|-----------|
| 🔷 SCG-0 | Requirement Spec Gate | 需求凍結前（PRD + FRD 完成） | sa-analyst |
| 🔷 SCG-1 | Design Spec Gate | 設計凍結前（SRD + API Spec 完成） | sd-architect |
| 🔷 SCG-2 | Architecture Spec Gate | 架構凍結前（C4 圖 + ADR 完成） | sd-architect |
| 🔷 SCG-3 | API Contract Gate（Contract Freeze） | 開發啟動前（OpenAPI 3.1 凍結） | sd-architect / integration-specialist |
| 🔷 SCG-4 | PR Review Gate | 實作 PR 審查（實作與規格一致性） | dev-senior / tech-lead |
| 🔷 SCG-5 | RTM Completeness Gate | 交付前（RTM 100% 覆蓋） | qa-lead |
| 🔷 SCG-6 | Release Gate | 發布前（所有閘門通過確認） | all |

---

## 🔄 工作流程步驟（含 FSM 整合）

```
[任何 Stage 文件產出前]
         │
         ▼
0. 【FSM 狀態確認】
   記錄當前 retry_count（本 SCG 閘門的重試次數）
   若 retry_count ≥ max_retry → 直接進入 ESCALATION（不執行後續步驟）
         │
         ▼
1. Agent 識別文件類型 → 選擇對應 SCG 閘門
         │
         ▼
2a.【SLV 前置驗證 — 僅 SCG-0 / SCG-3】
   執行 /spec-logical-validator
   ├── SLV CRITICAL FAIL → retry_count++ → 🔴 STOP（修正邏輯問題）
   └── SLV PASS → 繼續步驟 2a-bis
         │
         ▼
2a-bis.【Ambiguity Gate — 僅 SCG-0，Phase G M3 / Rule 9.16】
   呼叫 tools.fsm_runtime.ambiguity_scorer.score_frd(FRD_path)
   ├── max(score) ≥ 0.4 且無對應 AMBIGUITY-WAIVER → SCG-0 FAIL → retry_count++ → 🔴 STOP
   ├── 報告寫入 build/reports/scg/AMBIGUITY-{date}.yaml
   └── 全部 < 0.4 或已 waive → 繼續步驟 2a-ter
         │
         ▼
2a-ter.【Spec Debate — 僅 SCG-0，Phase K M-K2 / ACT-084 / Rule 9.23.3~4，advisory】
   對落在 near-threshold band（預設 0.25 ≤ score < 0.4）的 AC：
   呼叫 tools.fsm_runtime.spec_debate.debate(ac_text)（兩隔離詮釋提對立讀法，量化分歧）
   ├── verdict=divergence → FSMRuntime.enter_spec_debate(ac_id) → exit_spec_debate("divergence")
   │      → HUMAN_PENDING（附兩詮釋 + 分歧證據，人工一句話定案；advisory 不自動改 AC）
   └── verdict=consensus → （如已進入）exit_spec_debate("consensus") → 繼續步驟 2b
         │
         ▼
2b. 執行 spec_compliance_check（格式/完整性驗證）
   ├── completeness 檢查
   ├── format 檢查
   ├── cross_reference 檢查
   └── sdd_specific 檢查
         │
         ├── 檢查失敗 → retry_count++ → 🔴 STOP：修正後重新執行
         │              若 retry_count ≥ 3 → ESCALATION
         │
         ▼
3. 🔷 Spec Compliance Gate PASSED（retry_count 不重置，待 SPEC_FROZEN 後重置）
         │
         ▼
4. 🔴 Human Checkpoint（人類審查）
         │
         ├── 需修改 ──→ 回到步驟 1（retry_count++）
         │
         ▼
5. 🎯 SPEC_FROZEN milestone
   → 執行 /stage-compaction（強制上下文壓縮）
   → retry_count 重置為 0（進入新 Stage）
   → 進入下一 Stage 的 SPEC_DRAFTING
```

---

## ✅ 閘門通過標準

### SCG-0（Requirement Spec Gate）
- [ ] PRD 已完成（業務目標、範疇、假設）
- [ ] FRD 所有欄位完整（F/US/AC 格式規範）
- [ ] 每個 User Story 有可測試 AC（Given/When/Then）
- [ ] 追溯鏈：EPIC → F → US → AC 完整
- [ ] 使用標準 ID 格式（EPIC/F/US/AC）
- [ ] SLV 前置驗證通過（SLV-001~003）
- [ ] **Ambiguity Gate 通過**：所有 AC ambiguity score < 0.4，或例外項已建立 AMBIGUITY-WAIVER（Phase G M3 / Rule 9.16）

### SCG-1（Design Spec Gate）
- [ ] SRD 完整定義系統設計
- [ ] API Spec 草稿已完成（端點清單）
- [ ] NFR 規格化（效能/安全/可用性目標量化）
- [ ] 技術選型有合理依據

### SCG-2（Architecture Spec Gate）
- [ ] SRD 完整定義系統架構
- [ ] C4 Context + Container 圖已產出
- [ ] 所有重大架構決策有對應 ADR
- [ ] Trust Boundary Map 已定義（安全場景必備）

### SCG-3（API Contract Gate — Contract Freeze）
- [ ] 使用 OpenAPI 3.1 格式
- [ ] 所有端點已定義 Request/Response Schema
- [ ] 安全機制已定義（securitySchemes）
- [ ] 追溯至 US/AC（x-aisdlc.related_us 欄位）
- [ ] SLV 前置驗證通過（SLV-004~006）

### SCG-4（PR Review Gate）
- [ ] 實作符合 SCG-3 凍結的 API Contract
- [ ] 單元測試覆蓋率 ≥ 80%
- [ ] 無 OWASP Top 10 安全漏洞
- [ ] Code Review 通過（由 dev-senior 或 tech-lead 確認）
- [ ] 無 TODO/FIXME 殘留

### SCG-5（RTM Completeness Gate）
- [ ] RTM 中所有 AC 均有對應 AT
- [ ] AT 覆蓋率 ≥ 80%（EPIC → F → US → AC → AT）
- [ ] 所有 AT 測試結果記錄完整（Pass/Fail）
- [ ] 未通過項目有對應 Bug Report 並已修復

### SCG-6（Release Gate）
- [ ] SCG-0 ~ SCG-5 全部通過確認
- [ ] 生產環境部署計畫已完成
- [ ] Rollback 計畫已定義
- [ ] 監控告警已配置（SLO 告警閾值）

---

## 📂 相關文件

- [SDD 核心原則](../../guides/system/sdd/SDD_Core_Principles.md)
- [ADR 範本](../../docs_template/sdd/adr/ADR-TEMPLATE.md)
- [RTM 範本](../../docs_template/sdd/testing/RTM-TEMPLATE.md)
- [API Contract 範本](../../docs_template/sdd/api/CONTRACT-TEMPLATE.yaml)
- [SDD_FSM_ENGINE.md](../sdd-fsm-engine/SDD_FSM_ENGINE.md) — FSM 狀態機（retry_limit 定義）
- [SDD_ESCALATION_PROTOCOL.md](../sdd-escalation/SDD_ESCALATION_PROTOCOL.md) — 退場機制
- [spec-logical-validator SKILL](../../.claude/skills/spec-logical-validator/SKILL.md) — SLV 邏輯驗證
- [stage-compaction SKILL](../../.claude/skills/stage-compaction/SKILL.md) — SPEC_FROZEN 後壓縮
