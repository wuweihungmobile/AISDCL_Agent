# Migration Contract Map（MCM）— 遷移契約地圖模板
# 使用說明：複製至 docs/02_architecture/migration/MIGRATION-CONTRACT-MAP-{system}.md 後填寫

**系統名稱**: {SystemName}
**遷移策略**: {Big Bang / Strangler Fig / Database-First / Event-Driven Migration}
**版本**: v1.0
**建立日期**: {date}
**SCG 狀態**: 待 SCG-3 凍結
**前置文件**: `ADR-MIGRATION-{NNN}.md`（遷移策略 ADR）

---

## 1. 遷移概覽

| 項目 | 說明 |
|------|------|
| 舊系統 | {LegacySystemName} — {技術棧} |
| 新系統 | {NewSystemName} — {技術棧} |
| 遷移階段 | {DB → 後端 → 前端 / 其他} |
| 並行期間 | {起始日} ~ {結束日} |
| 負責人 | {Owner} |

---

## 2. API Mapping Contract（API 映射契約）

> 定義每個舊系統 API 到新系統 API 的映射關係

| API-ID | 舊端點 | 新端點 | 映射類型 | 向後相容 | 廢棄期 |
|--------|--------|--------|---------|---------|------|
| MCM-API-001 | `GET /api/v1/{resource}` | `GET /api/v2/{resource}` | 1:1 直接映射 | ✅ | {date} |
| MCM-API-002 | `POST /api/v1/{resource}` | `POST /api/v2/{resource}` | 欄位重命名 | ⚠️ 轉換層 | {date} |
| MCM-API-NNN | {舊端點} | {新端點} | {映射類型} | {是/否} | {date} |

### 映射類型說明
- **1:1 直接映射**：路由/欄位完全相同
- **欄位重命名**：需轉換層
- **合併端點**：多個舊 API → 單個新 API
- **拆分端點**：單個舊 API → 多個新 API
- **廢棄（無替代）**：舊 API 不在新系統中存在

---

## 3. Data Migration Contract（資料遷移契約）

> 定義每個資料欄位的舊→新映射與轉換規則

### 3.1 資料表映射

| 舊資料表 | 新資料表 | 映射類型 | 說明 |
|---------|---------|---------|------|
| `legacy_{table}` | `{new_table}` | 1:1 | 直接映射 |
| `legacy_{table_a}` + `legacy_{table_b}` | `{merged_table}` | 合併 | Join 後遷移 |

### 3.2 欄位映射規則

| MCM-DATA-ID | 舊欄位 | 舊型別 | 新欄位 | 新型別 | 轉換規則 | 驗證規則 |
|-------------|--------|--------|--------|--------|---------|---------|
| MCM-DATA-001 | `legacy_col` | VARCHAR(100) | `new_col` | TEXT | 直接複製 | NOT NULL |
| MCM-DATA-002 | `status_code` | INT | `status` | ENUM | `{0→'inactive', 1→'active'}` | 必須在 ENUM 值中 |
| MCM-DATA-NNN | {舊欄位} | {型別} | {新欄位} | {型別} | {規則} | {驗證} |

### 3.3 資料轉換函數規格

```
TRANSFORM_{TableName}:
  input:  legacy_{table} row
  output: {new_table} row
  steps:
    1. {轉換步驟 1}
    2. {轉換步驟 2}
  error_handling: {出錯時：停止/跳過/記錄並繼續}
  rollback: {如何還原}
```

---

## 4. Routing Contract（流量路由規則）

> 並行期間，哪些流量路由到舊系統，哪些路由到新系統

### 4.1 路由策略

```
Client Request
    ↓
[API Gateway / Load Balancer]
    ↓
路由規則評估
    ├── 規則 1: {條件} → 舊系統 ({%}%)
    ├── 規則 2: {條件} → 新系統 ({%}%)
    └── 預設: → {舊/新}系統
```

### 4.2 路由規則表

| 規則 ID | 觸發條件 | 目標系統 | 生效時間 | 說明 |
|---------|---------|---------|---------|------|
| ROUTE-001 | Header: `X-System: legacy` | 舊系統 | 遷移全程 | 強制路由舊系統 |
| ROUTE-002 | User Group: `beta_testers` | 新系統 | Phase 2 起 | Beta 測試群組 |
| ROUTE-NNN | {條件} | {目標} | {時間} | {說明} |

### 4.3 Canary 流量分配計畫

| 遷移階段 | 新系統流量 % | 觸發條件 | 回滾條件 |
|---------|------------|---------|---------|
| Phase 1 | 5% | 環境就緒 | 錯誤率 > 1% |
| Phase 2 | 25% | P1 穩定 72h | 錯誤率 > 0.5% |
| Phase 3 | 50% | P2 穩定 48h | 任何 P0 事件 |
| Phase 4 | 100% | P3 穩定 24h | 回滾至 P3 |

---

## 5. Consistency Contract（資料一致性保證）

> 定義並行期間如何確保兩系統資料一致性

### 5.1 一致性模型

- **模型選擇**: {Strong / Eventual / Read-Your-Writes}
- **一致性時限**: 寫入後 {N} 秒內達到一致
- **衝突解決**: {Last-Write-Wins / Merge / 手動}

### 5.2 雙寫策略（Dual Write）

```
Write Request
    ├── Step 1: 寫入主系統（{舊/新}）
    ├── Step 2: 異步寫入從系統（{新/舊}）
    └── Step 3: 確認兩系統資料一致
    
一致性驗證頻率: 每 {N} 分鐘
一致性驗證工具: {工具名稱}
```

### 5.3 一致性驗證規格

| 驗證 ID | 驗證項目 | 頻率 | 容忍差異 | 告警閾值 |
|---------|---------|------|---------|---------|
| CONS-001 | 記錄總數一致 | 每 5 分鐘 | 0 | 任何差異 |
| CONS-002 | 關鍵欄位值一致 | 每 1 分鐘 | 0 | 任何差異 |
| CONS-NNN | {驗證項目} | {頻率} | {差異} | {閾值} |

---

## 6. Backward Compatibility Contract（向後相容性保證）

> 在廢棄期內，舊 API 必須繼續正常工作

| API-ID | 舊端點 | 廢棄期結束 | 相容策略 | 通知方式 |
|--------|--------|----------|---------|---------|
| MCM-API-001 | `GET /api/v1/{resource}` | {date} | 轉發至新系統 | Header: `Deprecation: {date}` |
| MCM-API-NNN | {端點} | {date} | {策略} | {方式} |

---

## 7. SCG-3 Contract Freeze 檢查清單

- [ ] 所有 API 映射均已記錄（MCM-API 編號完整）
- [ ] 所有資料欄位映射均已記錄（MCM-DATA 編號完整）
- [ ] 路由規則已定義並確認
- [ ] 一致性策略已選擇並規格化
- [ ] Backward Compatibility 廢棄期已確認
- [ ] 🔴 Human 確認：遷移契約地圖凍結

---

**文件狀態**: Draft / Review / Frozen
**最後更新**: {date}
**下游文件**: `CUTOVER-SPEC-{system}.md`, `ROLLBACK-SPEC-{system}.md`, `CONTRACT-TEST-SPEC-{system}.md`
