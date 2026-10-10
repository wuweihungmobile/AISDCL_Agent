# Test Contract Specification — WordCount 詞頻統計

**文件類型**: Test Contract Specification (TCS)
**SDD Gate**: SCG-4 Test Strategy Gate
**存放位置**: `docs/03_testing/contracts/TEST-CONTRACT-SPEC-WordCount.md`
**spec-format-version**: 1.0
**場景**: greenfield 全新純函式模組（無既有程式碼、無外部依賴，僅用 Python 標準庫）

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **Feature ID** | F-001 |
| **Feature 名稱** | WordCount 詞頻統計 |
| **User Story** | US-001 作為文字分析工具的使用者，我要知道一段英文文字中每個單字出現幾次 |
| **建立日期** | 2026-10-10 |
| **QA 負責人** | SA/SD agent |
| **SCG Gate** | SCG-4 通過 |

介面契約：模組 `wordcount`、函式 `wordcount(text: str) -> dict[str, int]`。

---

## 1. AC → AT 映射表

> **SDD 原則**: 每個 AC 必須對應至少一個可自動化的 AT。

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-001-1 | 以空白分隔、不分大小寫統計每個單字的出現次數 | AT-001-1-1 | 重複單字被累計且不分大小寫 | ✅ | Unit | □ |
| AC-001-1 | 以空白分隔、不分大小寫統計每個單字的出現次數 | AT-001-1-2 | 前後標點不併入單字（負向） | ✅ | Unit | □ |
| AC-002-1 | 非字串輸入必須明確拒絕 | AT-002-1-1 | 傳入 None 時拋出 TypeError | ✅ | Unit | □ |

**覆蓋率統計**:
- 總 AC 數: 2
- 已映射 AT 數: 3
- 映射覆蓋率: 100% （目標: 100%）

---

## 2. 可自動化 AT 格式規範

```gherkin
# AT-001-1-1
# 對應 AC: AC-001-1 以空白分隔、不分大小寫統計每個單字的出現次數
# 測試類型: Unit
# 自動化工具: pytest

Feature: WordCount 詞頻統計

Scenario: 重複單字被累計且不分大小寫
  Given 輸入文字 "The cat and the hat"
  When 呼叫 wordcount(text)
  Then 回傳字典中「the」的次數為 2
  And 「cat」的次數為 1
```

```gherkin
# AT-001-1-2
# 對應 AC: AC-001-1 以空白分隔、不分大小寫統計每個單字的出現次數（負向）
# 測試類型: Unit
# 自動化工具: pytest

Feature: WordCount 詞頻統計 - 標點處理

Scenario: 前後標點不併入單字
  Given 輸入文字 "Hello, World! hello."
  When 呼叫 wordcount(text)
  Then 回傳字典恰有 2 個鍵，其中「hello」的次數為 2
  And 鍵中不應出現帶標點的單字，例如「hello,」
```

```gherkin
# AT-002-1-1
# 對應 AC: AC-002-1 非字串輸入必須明確拒絕
# 測試類型: Unit
# 自動化工具: pytest

Feature: WordCount 詞頻統計 - 輸入驗證

Scenario: 傳入 None 時被拒絕
  Given 輸入為 None
  When 呼叫 wordcount(None)
  Then 拋出 TypeError
  And 錯誤訊息說明輸入必須是字串
```

---

## 3. AT 完整清單

### 3.1 Unit Tests

| AT ID | 對應 AC | 描述 | 測試方法 | 預期結果 |
|-------|---------|------|---------|---------|
| AT-001-1-1 | AC-001-1 | 重複單字累計、大小寫合併 | 呼叫 wordcount 後比對字典 | the=2、cat=1、and=1、hat=1 |
| AT-001-1-2 | AC-001-1 | 標點不併入單字 | 呼叫 wordcount 後比對字典 | 恰 2 個鍵：hello=2、world=1 |
| AT-002-1-1 | AC-002-1 | None 輸入被拒絕 | pytest.raises(TypeError) | 拋出 TypeError，訊息提及 str |

---

## 4. 邊界與錯誤測試規格

| 場景類型 | AT ID | 描述 | 輸入 | 預期結果 |
|---------|-------|------|------|---------|
| 空值處理 | AT-002-1-1 | None 輸入 | None | TypeError 與明確錯誤訊息 |

---

## 5. 測試資料規格

| 資料項目 | 類型 | 說明 | 來源 |
|---------|------|------|------|
| 英文短句 | 靜態 Fixture | AT 內直接以字面值給定，無外部檔案 | 測試程式內嵌 |

---

## 6. RTM 連結確認

| 追溯項目 | 覆蓋狀態 |
|---------|---------|
| F-001 → US-001 | ☑ 已映射 |
| US-001 → AC-001-1／AC-002-1 | ☑ 已映射 |
| AC-001-1／AC-002-1 → AT-001-1-1／AT-001-1-2／AT-002-1-1 | ☑ 已映射（本文件） |

## 📋 SCG-4 通過標準

| 驗證項目 | 判斷標準 | 狀態 |
|---------|---------|------|
| AC → AT 100% 映射 | 無未映射 AC | ☑ |
| AT 格式可自動化 | 使用 Given-When-Then 格式 | ☑ |
| 負向測試覆蓋 | 每個 AC 有至少一個負向 AT | ☑（AC-001-1：AT-001-1-2；AC-002-1：AT-002-1-1） |
| 測試資料規格完整 | 資料來源明確定義 | ☑ |

**確認人**: SA/SD agent  **確認日期**: 2026-10-10  **狀態**: ☑ 通過
