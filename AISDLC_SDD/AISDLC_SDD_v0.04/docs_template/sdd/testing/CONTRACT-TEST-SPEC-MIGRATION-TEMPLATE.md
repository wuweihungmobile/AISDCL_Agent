# Contract Test Spec — Migration 契約測試規格模板
# 使用說明：複製至 docs/03_testing/contracts/CONTRACT-TEST-SPEC-{system}.md 後填寫

**系統名稱**: {SystemName}
**測試基準文件**: `MIGRATION-CONTRACT-MAP-{system}.md`
**版本**: v1.0
**建立日期**: {date}
**SCG 狀態**: 待 SCG-4 凍結

---

## 1. 測試範圍與目標

| 目標 | 說明 |
|------|------|
| **API Contract 驗證** | 每個 MCM-API 映射必須通過契約測試 |
| **資料完整性驗證** | 每個 MCM-DATA 轉換必須通過驗證 |
| **路由規則驗證** | 並行期間流量路由規則正確執行 |
| **一致性驗證** | 雙系統資料一致性符合 Consistency Contract |

---

## 2. API Contract Tests（基於 MCM API Mapping）

> 每個 MCM-API-NNN 對應一組或多組 Contract Test Cases

### TCS-MCMAPI-001：MCM-API-001 映射驗證

| 欄位 | 值 |
|------|-----|
| **對應 MCM** | MCM-API-001 |
| **測試目的** | 驗證 `GET /api/v1/{resource}` 與 `GET /api/v2/{resource}` 回應等價 |
| **測試類型** | Consumer Contract Test |

#### 測試案例

```yaml
test_case: TCS-MCMAPI-001-01
name: "舊API回應格式與新API等價"
given:
  - 相同的請求參數：{params}
when:
  - 同時呼叫舊端點 GET /api/v1/{resource}?{params}
  - 同時呼叫新端點 GET /api/v2/{resource}?{params}
then:
  - 回應 HTTP Status Code 相同
  - 回應資料欄位語義等價（允許欄位名稱重命名）
  - 回應時間差異 < {N}ms
pass_criteria: 兩系統回應 100% 等價
```

```yaml
test_case: TCS-MCMAPI-001-02
name: "向後相容性：舊API在廢棄期內仍可用"
given:
  - 廢棄期尚未結束
when:
  - 呼叫舊端點 GET /api/v1/{resource}
then:
  - HTTP Status: 200（非 404/410）
  - Response Header 包含 Deprecation: {date}
  - 回應資料正確
```

### TCS-MCMAPI-NNN：{API 端點} 映射驗證

```yaml
# 複製上方格式，為每個 MCM-API 建立對應測試
```

---

## 3. Data Integrity Test Spec（資料完整性測試）

### TCS-MCMDATA-001：資料遷移完整性驗證

```yaml
test_case: TCS-MCMDATA-001-01
name: "遷移後記錄總數一致"
given:
  - 資料遷移已完成
when:
  - 查詢舊 DB：SELECT COUNT(*) FROM legacy_{table}
  - 查詢新 DB：SELECT COUNT(*) FROM {new_table}
then:
  - 兩者數量相同（容忍差異：0）
pass_criteria: 100% 記錄遷移完整

test_case: TCS-MCMDATA-001-02
name: "關鍵欄位轉換正確性（抽樣驗證）"
given:
  - 隨機抽樣 {N}% 記錄
when:
  - 比對 legacy_{table}.{col} 與 {new_table}.{new_col}
  - 套用轉換規則 MCM-DATA-{NNN}
then:
  - 每筆抽樣記錄轉換結果正確
  - 無 NULL 值在 NOT NULL 欄位
pass_criteria: 抽樣 100% 通過
```

### TCS-MCMDATA-002：轉換邊界條件測試

```yaml
test_case: TCS-MCMDATA-002-01
name: "NULL 值處理"
given:
  - 舊 DB 存在 NULL 值的記錄
when:
  - 執行資料遷移轉換
then:
  - NULL 值按照 MCM-DATA 規格正確處理（設預設值 / 保留 NULL / 報錯）

test_case: TCS-MCMDATA-002-02
name: "特殊字元與編碼處理"
given:
  - 含特殊字元或非 UTF-8 編碼的舊資料
when:
  - 執行資料遷移轉換
then:
  - 字元正確轉換，無亂碼
```

---

## 4. Consumer-Driven Contract Tests（CDC Tests）

> 從消費者視角定義 API 行為期望

### Provider Verification Tests

```yaml
provider: "{NewSystem}"
consumer: "{LegacySystem / Client}"
interactions:
  - description: "獲取 {resource} 列表"
    request:
      method: GET
      path: /api/v2/{resource}
      headers:
        Accept: application/json
    response:
      status: 200
      headers:
        Content-Type: application/json
      body:
        type: object
        properties:
          data:
            type: array
          total:
            type: integer
          # 確保舊消費者期望的欄位均存在
```

---

## 5. Routing Contract Tests

```yaml
test_case: TCS-ROUTING-001
name: "Canary 流量分配驗證"
given:
  - Canary 階段 Phase 2（25% 新系統）
when:
  - 發送 1000 個請求
then:
  - 約 250 個（±5%）路由至新系統
  - 約 750 個（±5%）路由至舊系統

test_case: TCS-ROUTING-002
name: "強制路由規則"
given:
  - 請求攜帶 Header: X-System: legacy
when:
  - 發送請求
then:
  - 100% 路由至舊系統
```

---

## 6. Rollback Contract Tests

```yaml
test_case: TCS-ROLLBACK-001
name: "回滾後系統恢復驗證"
given:
  - 已觸發回滾（錯誤率 > 閾值）
when:
  - 等待回滾完成（預期時間 < {N} 分鐘）
then:
  - 所有流量恢復至舊系統
  - 錯誤率恢復至基準線
  - 資料一致性未受損
```

---

## 7. 測試執行策略

| 測試階段 | 執行時機 | 工具 | 通過標準 |
|---------|---------|------|---------|
| CI/CD L2 | 每次 PR | Pact / Postman Newman | 所有契約測試通過 |
| 遷移前 | 每層切換前 | 自動化測試套件 | 100% 通過 |
| 遷移後 | 每層切換後 | 自動化測試套件 | 100% 通過 |
| 生產監控 | 持續 | 合成監控 | P95 < {N}ms, 錯誤率 < {%} |

---

## 8. SCG-4 凍結確認

- [ ] 每個 MCM-API 映射均有對應 Contract Test
- [ ] 資料完整性測試覆蓋所有 MCM-DATA 轉換
- [ ] Consumer-Driven Contract Tests 已定義
- [ ] 路由規則測試已定義
- [ ] 回滾測試已定義
- [ ] 🔴 Human 確認：測試規格凍結

**最後更新**: {date}
