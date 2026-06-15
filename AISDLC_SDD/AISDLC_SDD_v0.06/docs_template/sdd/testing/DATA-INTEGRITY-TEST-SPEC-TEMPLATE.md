# Data Integrity Test Spec — 資料完整性測試規格模板
# 使用說明：複製至 docs/03_testing/DATA-INTEGRITY-TEST-SPEC-{system}.md 後填寫

**系統名稱**: {SystemName}
**版本**: v1.0
**建立日期**: {date}
**前置文件**: `MIGRATION-CONTRACT-MAP-{system}.md`（MCM Data Migration Contract 章節）

---

## 1. 資料完整性驗證維度

| 維度 | 說明 | 驗證方法 |
|------|------|---------|
| **完整性（Completeness）** | 所有記錄均已遷移 | COUNT 比對 |
| **準確性（Accuracy）** | 欄位值正確轉換 | 抽樣欄位比對 |
| **一致性（Consistency）** | 外鍵關係完整 | 參照完整性檢查 |
| **時效性（Timeliness）** | 遷移後新資料同步 | 雙寫驗證 |
| **唯一性（Uniqueness）** | 主鍵無重複 | DISTINCT COUNT |

---

## 2. 完整性測試（Completeness Tests）

### TCS-DI-COMP-001：記錄總數比對

```sql
-- 舊系統
SELECT COUNT(*) AS legacy_count FROM legacy_{table};

-- 新系統  
SELECT COUNT(*) AS new_count FROM {new_table};

-- 驗證：legacy_count = new_count
-- 容忍差異：0（若有軟刪除則扣除）
```

### TCS-DI-COMP-002：主鍵範圍覆蓋

```sql
-- 驗證舊系統所有 ID 均存在於新系統
SELECT COUNT(*) FROM legacy_{table} l
WHERE NOT EXISTS (
  SELECT 1 FROM {new_table} n 
  WHERE n.legacy_id = l.id
);
-- 預期結果：0
```

---

## 3. 準確性測試（Accuracy Tests）

### TCS-DI-ACC-001：關鍵欄位抽樣比對

| 抽樣欄位 | 轉換規則（MCM 引用） | 抽樣比例 | 通過標準 |
|---------|-----------------|---------|---------|
| `{field_1}` | MCM-DATA-001 | 10% | 100% 一致 |
| `{field_2}` | MCM-DATA-002 | 5% | 100% 一致 |
| `{field_N}` | MCM-DATA-NNN | {%} | 100% 一致 |

```sql
-- 抽樣比對範例
SELECT 
  l.id,
  l.{legacy_field},
  n.{new_field},
  CASE 
    WHEN {轉換規則(l.legacy_field)} = n.{new_field} THEN 'PASS'
    ELSE 'FAIL'
  END AS validation_result
FROM legacy_{table} l
JOIN {new_table} n ON n.legacy_id = l.id
TABLESAMPLE SYSTEM(10);
-- 預期：所有結果為 PASS
```

### TCS-DI-ACC-002：ENUM/狀態值轉換驗證

```sql
-- 驗證所有狀態碼已正確轉換
SELECT DISTINCT new_status 
FROM {new_table}
WHERE new_status NOT IN ({valid_enum_values});
-- 預期：0 筆（無非法值）
```

---

## 4. 一致性測試（Consistency Tests）

### TCS-DI-CONS-001：外鍵完整性

```sql
-- 驗證外鍵引用完整（新系統）
SELECT COUNT(*) FROM {child_table} c
WHERE NOT EXISTS (
  SELECT 1 FROM {parent_table} p 
  WHERE p.id = c.parent_id
);
-- 預期：0（無孤立記錄）
```

### TCS-DI-CONS-002：業務規則一致性

| 業務規則 | 驗證 SQL / 邏輯 | 預期結果 |
|---------|----------------|---------|
| {業務規則 1} | {SQL} | 0 筆違反 |
| {業務規則 N} | {SQL} | 0 筆違反 |

---

## 5. 唯一性測試（Uniqueness Tests）

### TCS-DI-UNIQ-001：主鍵唯一性

```sql
SELECT id, COUNT(*) FROM {new_table}
GROUP BY id HAVING COUNT(*) > 1;
-- 預期：0 筆重複
```

---

## 6. 時效性測試（Timeliness Tests — 雙寫期間）

### TCS-DI-TIME-001：雙寫延遲驗證

```
given: 在舊系統寫入一筆記錄
when: 等待 {N} 秒
then: 新系統中可查詢到相同記錄
SLA: 最大延遲 {N} 秒
```

---

## 7. 測試執行順序

```
1. 資料遷移完成後立即執行：
   TCS-DI-COMP-001 → TCS-DI-COMP-002（完整性）
   TCS-DI-UNIQ-001（唯一性）
   TCS-DI-CONS-001（一致性）

2. 批量抽樣執行（可並行）：
   TCS-DI-ACC-001（準確性抽樣）
   TCS-DI-ACC-002（ENUM 驗證）

3. 持續監控（雙寫期間）：
   TCS-DI-TIME-001（時效性）
```

---

## 8. 通過標準（Definition of Pass）

| 項目 | 標準 |
|------|------|
| 記錄完整性 | 差異 = 0 筆 |
| 欄位準確性 | 抽樣 100% 通過 |
| 外鍵一致性 | 孤立記錄 = 0 筆 |
| 主鍵唯一性 | 重複 = 0 筆 |
| 雙寫延遲 | P95 < {N}s |

**最後更新**: {date}
