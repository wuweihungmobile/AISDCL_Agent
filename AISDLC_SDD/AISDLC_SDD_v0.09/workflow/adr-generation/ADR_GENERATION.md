# ADR Generation Workflow
# Architecture Decision Record 生成工作流程

**版本**: v1.0
**建立日期**: 2026-04-12
**工作流程類型**: 文件生成（Document Generation）
**分類**: SDD Phase 01 新增

---

## 🎯 工作流程目的

標準化所有架構決策的記錄流程，確保每個技術決策都有對應的 ADR 文件，使架構決策可追溯、可審查。

---

## 🔔 觸發條件

以下情況**必須**生成 ADR：

- [ ] 技術棧選擇（程式語言、框架、資料庫）
- [ ] 架構模式選擇（Monolith / Microservices / Event-Driven）
- [ ] 整合策略（API / Event / File / DB Share）
- [ ] 安全機制選擇（Auth / Encryption / Token）
- [ ] 部署策略（Container / Serverless / VM）
- [ ] 任何「重大且難以逆轉」的技術決策

---

## 🔄 工作流程步驟

```
[偵測到架構決策點]
         │
         ▼
1. Agent 觸發 generate_adr Skill
         │
         ▼
2. 從 ADR-TEMPLATE.md 讀取範本
         │
         ▼
3. 填寫 ADR 內容：
   ├── 決策標題與序號（ADR-NNN）
   ├── 情境描述（Context）
   ├── 決策內容（Decision）
   ├── 理由（Rationale）
   ├── 後果（Consequences）
   └── 替代方案評估（Alternatives）
         │
         ▼
4. 執行 spec_compliance_check
         │
         ├── 驗證失敗 ──→ 補充缺失內容
         │
         ▼
5. 🔴 Human Checkpoint（確認決策正確）
         │
         ├── 需修改 ──→ 回到步驟 3
         │
         ▼
6. 儲存至 docs/02_architecture/adr/ADR-{NNN}-{title}.md
         │
         ▼
7. 更新 ADR Index（technical-writer 執行 adr_index_maintenance）
         │
         ▼
8. 在相關 SRD/FRD 文件中加入 ADR 引用
```

---

## 📋 ADR 序號規則

- 格式：`ADR-{NNN}`（三位數，左補零）
- 範例：`ADR-001`, `ADR-002`, ..., `ADR-099`
- 序號由 technical-writer 維護的 ADR-INDEX.md 統一管理
- 新 ADR 序號 = 目前最大序號 + 1

---

## 📂 輸出位置

- **ADR 文件**：`docs/02_architecture/adr/ADR-{NNN}-{kebab-title}.md`
- **ADR 索引**：`docs/02_architecture/adr/ADR-INDEX.md`（由 technical-writer 維護）

---

## 🔗 ADR 狀態流轉

```
Proposed → Accepted → （可選）Deprecated / Superseded
```

- **Proposed**：已提出，待 Human 確認
- **Accepted**：已確認，成為正式決策
- **Deprecated**：已廢棄（技術已過時）
- **Superseded by ADR-XXX**：被新的 ADR 取代

---

## 📂 相關文件

- [ADR 範本](../../docs_template/sdd/adr/ADR-TEMPLATE.md)
- [SDD 核心原則](../../guides/system/sdd/SDD_Core_Principles.md)
- [Spec-First Gate Workflow](../sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md)
