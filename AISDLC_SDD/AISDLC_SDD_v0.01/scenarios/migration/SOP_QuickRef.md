# Migration 技術棧遷移 - 快速參考指南

**版本**: v0.01
**閱讀時間**: 5 分鐘
**適用情境**: 全技術棧遷移、資料庫平台遷移、系統現代化

---

## 🎯 一頁總覽

### 適用場景
✅ 前端/後端/DB 框架全面替換
✅ 資料庫平台遷移（如 Oracle→PostgreSQL）
✅ 系統現代化 + 新平台擴展（Android/macOS）
✅ 技術棧升級（如 Python 2→Java, jQuery→React）

### 不適用場景
❌ 同技術棧內代碼改善（請用 Refactoring）
❌ Bug 修復或小功能新增（請用 Brownfield）
❌ 全新系統無舊代碼（請用 Greenfield）

---

## 📋 9 階段快速流程

```
┌─────────────────────────────────────────────┐
│ 階段 1: 現況分析與需求提取 (1-2h) 🔴         │
│ └─ 舊系統掃描 → 業務邏輯提取 → 技術盤點     │
├─────────────────────────────────────────────┤
│ 階段 2: 遷移架構設計 (1-1.5h) 🔴             │
│ └─ 技術映射 → 策略選擇 → 並行運行設計       │
├─────────────────────────────────────────────┤
│ 階段 3: 資料庫遷移 (0.5-1h / 2-4w) 🔴       │
│ └─ Schema轉換 → SQL改寫 → SP遷移 → 資料搬移 │
├─────────────────────────────────────────────┤
│ 階段 4: 後端遷移 (30-40m / 4-6w) 🔴         │
│ └─ API契約 → Service重寫 → 功能替換         │
├─────────────────────────────────────────────┤
│ 階段 5: 前端遷移 (30-40m / 6-8w) 🟡         │
│ └─ 元件映射 → 逐模組重寫 → 功能對等驗證     │
├─────────────────────────────────────────────┤
│ 階段 6: 新平台開發 (20-30m / 4-6w) 🟡       │
│ └─ 行動端架構 → 掃碼/硬體 → 離線支援       │
├─────────────────────────────────────────────┤
│ 階段 7: 驗證與測試 (30-40m / 2-3w) ✅       │
│ └─ DB驗證 → 跨系統比對 → 行動端測試         │
├─────────────────────────────────────────────┤
│ 階段 8: 部署與切換 (20-30m / 1-2w) ✅       │
│ └─ L0+L1+L2(Contract)+L3(Canary+Rollback)  │
│    → 雙寫驗證 → 5%→25%→50%→100% → 退役     │
├─────────────────────────────────────────────┤
│ 階段 9: 知識沉澱 (20m / 2-3d) ✅            │
│ └─ 遷移手冊 → ADR → 經驗總結               │
└─────────────────────────────────────────────┘
```

---

## ⚡ 遷移策略快速決策

| 策略 | 適用情境 | 風險 | 推薦 |
|------|---------|------|------|
| **分層漸進遷移** | 全棧遷移 | 🟢 低 | ✅ 首選 |
| **Strangler Pattern** | 大型遺留系統 | 🟢 低 | ✅ 推薦 |
| **Big Bang** | 小型系統 | 🔴 高 | ⚠️ 不建議 |
| **並行重寫** | 團隊充足 | 🟡 中 | 可選 |

---

## 🔑 遷移黃金法則

1. **先資料，後程式** — DB 遷移是基礎
2. **先後端，後前端** — API 穩定前端才能接
3. **逐模組替換** — 不要一次全換
4. **新舊對比** — 每個模組都要比對結果
5. **可隨時回切** — 舊系統保持運行直到完全驗證

---

## 🛠️ 可用 Skills 快速參考

### 核心 Skills（所有遷移皆適用）
| Skill | 用途 | 觸發時機 |
|-------|------|---------|
| `/brownfield-analysis` | 舊系統代碼品質與架構分析 | 階段 1 |
| `/sa-analyst` | 需求重新分析、業務邏輯提取 | 階段 1 |
| `/ba-analyst` | 業務邏輯完整性驗證 | 階段 1（多業務域必觸發）|
| `/sd-architect` | 遷移架構設計、技術棧映射 | 階段 2 |
| `/pm-planning` | 遷移優先級與 ROI 決策 | 階段 2 |
| `/database-migration` | DB 遷移規劃（Schema/SQL/SP） | 階段 3 |
| `/integration-database` | 新 DB 整合方案（ORM/連線池） | 階段 3 |
| `/integration-api-client` | API 契約設計（新舊對照） | 階段 4 |
| `/dev-review` | 遷移代碼審查 | 階段 4-5 |
| `/mobile-development` | 行動端/桌面端開發 | 階段 6 |
| `/qa-testing` | 測試策略與驗收測試 | 階段 7 |
| `/testing-strategy` | 跨系統對比測試（行為等價驗證） | 階段 7 |
| `/devops-github-actions` | 4 層 CI/CD Pipeline 建立 | 階段 8 |
| `/release-management` | Canary 發布與回滾管理 | 階段 8 |
| `/security-audit` | 安全審計（新舊棧掃描） | 全程 |
| `/performance-optimization` | 效能基準建立（Stage 1）與對比（Stage 7） | 全程 |
| `/compliance-audit` | 合規審查（電商支付 PCI-DSS/個資 GDPR） | 全程（涉及支付/個資時） |
| `/code-review` | 遷移代碼品質審查 | 階段 3-5 |
| `/sprint-planning` | 大規模遷移 Phase 拆分與迭代規劃 | 階段 3-6 |

---

## ⚠️ 遷移關鍵注意事項

### 1. CSR→SSR Auth 策略遷移（Vue3→Next.js）
- Vue3 SPA 的 localStorage JWT → Next.js SSR 的 httpOnly Cookie
- 推薦使用 next-auth 統一管理 Server-side 認證
- Server Components 無法讀取 localStorage，需全面改為 Cookie

### 2. Python→Java 型別系統遷移
- Python 鬆散型別 → Spring Boot 強型別 DTO/Entity
- 必須為每個 API 端點明確定義 Java Request/Response DTO
- 建立「Python API → Java DTO 映射表」逐端點確認

### 3. Oracle CDC 工具選擇注意
- Debezium for Oracle 需要 Oracle LogMiner 授權（企業版功能）
- 開源替代：ora2pg（批次遷移）、pgloader（增量同步）
- 雲端方案：AWS DMS（支援 Oracle CDC，需評估費用）

### 4. 多業務域 DDD Bounded Context
- 4 業務域（電商/民宿/CMS/知識管理）必須先做 Context 劃分
- 遷移是重新設計架構邊界的最佳時機
- 共用模組（User/Auth/File/Notification）需明確 API 合約，禁止直接 DB 共享

---

## 📚 參考資源

- [Migration SOP 完整版](./SOP.md)
- [Migration 快速啟動指令集](../../prompts/scenario-prompts/migration-prompts.md)
- [Refactoring DeepDive Part 11 - 技術棧遷移深度指南](../refactoring/SOP_DeepDive.md)
- [migration-planning-flow Workflow](../../workflow/scenario-specific/migration-planning-flow.md)
- [AISDLC_INIT.md](../../AISDLC_INIT.md)

---

**文檔版本: v0.01
**最後更新**: 2026-03-26
