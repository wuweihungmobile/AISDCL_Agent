# Test Contract Specification — Template
# 測試契約規格文件模板（AC → AT 完整映射）
# Phase 05 — Testing 情境 SDD 強化

**文件類型**: Test Contract Specification (TCS)
**SDD Gate**: SCG-4 PR Review Gate（RG-TEST 為補充閘）  <!-- 🔴 115／S-08 訂正：原文「SCG-4 Test Strategy Gate」；SCG-4＝PR Review Gate（SSOT：workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md），Test Strategy Gate＝補充閘 RG-TEST（guides/system/sdd/SDD_GUIDE.md） -->
**使用時機**: FRD/SRD 完成後，每個 Feature 必須產出此文件
**存放位置**: `docs/03_testing/contracts/TCS-{Feature}-{date}.md`
**spec-format-version**: 1.0  <!-- improving_85：AutoClaude SddToPlaybookAdapter 防漂移閘讀取（_SUPPORTED_SPEC_FORMAT_VERSIONS）；本表/Gherkin 格式跨版不相容演進時 bump 並同步 adapter 支援集 -->
**scenario**: greenfield  <!-- 10 場景之一（greenfield／brownfield／refactoring／documentation／devops／integration／migration／performance／security／testing）；AutoClaude adapter 優先讀本欄決定 step_id 的場景段，缺省才依全文推斷（並出聲 sdd.scenario_inferred） -->

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **Feature ID** | F-{NNN} |
| **Feature 名稱** | {FeatureName} |
| **User Story** | US-{NNN} |
| **建立日期** | {YYYY-MM-DD} |
| **QA 負責人** | {Name} |
| **SCG Gate** | SCG-4 □ 待審 / □ 通過 |

---

## 增量變更專用：FRD-lite 與〈增量追溯表〉（選填；一般 Feature 刪除本節）

> 僅在「變更限於已凍結系統的單一 Feature」並適用 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`〈增量（delta）條款〉時填寫。
> **未列入追溯表視為未滿足**；引用不得指向未凍結文件（必須列在 FSM 狀態檔 `frozen_stages[*].spec_docs`）。

**FRD-lite**（US／AC 併入本檔頭；每個 AC 仍須 Given-When-Then，並在 §1 有對應 AT）：

| US ID | User Story | AC ID | AC（Given／When／Then） |
|-------|------------|-------|-----------------------|
| US-{NNN} | {As a … I want … so that …} | AC-{NNN}-1 | {Given … When … Then …} |

> 編譯相容提醒：FRD-lite 表的**第一欄用 US ID**；不要把 AC ID 放第一欄——`sdd_compile` 會把「第一欄形如 `AC-…`」的表格列當成
> AC→AT 映射列掃描（取第三欄的 AT 字樣）。

**〈增量追溯表〉**（SCG-0～3 每個清單項一列；清單見 `SDD_SPEC_FIRST_GATE.md`〈閘門通過標準〉）：

| 清單項（閘門／項目） | 追溯 ID | 已凍結上位文件（路徑） | 凍結摘要 |
|---------------------|---------|----------------------|---------|
| {SCG-0／FRD 覆蓋 PRD 功能項} | {F-NNN、US-NNN} | {docs/01_requirements/FRD-System.md} | {sha256:64 位小寫 hex} |
| {SCG-2／重大架構決策有對應 ADR} | {ADR-NNN} | {docs/02_architecture/adr/ADR-NNN-title.md} | {sha256:64 位小寫 hex} |

> 凍結摘要＝該文件在 `frozen_stages[*].spec_doc_digests` 的值（`fsm_runtime show` 可查）。沒有新決策／沒有對外契約變更時，ADR／OpenAPI
> 清單項仍要列——追溯到**既有**已凍結文件；僅有新架構決策才另立 ADR、僅有對外 API／事件契約變更才另附 OpenAPI delta。

---

## 1. AC → AT 映射表

> **SDD 原則**: 每個 AC 必須對應至少一個可自動化的 AT。
>
> **AT ID 文法**（AutoClaude 編譯與逆向 RTM 共用）：`AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`，整串全比對、區分大小寫；
> **前兩段數字＝所屬 AC**（`AT-001-12-3-a` 屬 `AC-001-12`），第三段起的英數尾綴不影響歸屬。本表每列的 AC ID 必須等於 AT 前兩段推得者
> （`AC-001-12` 對 `AT-001-12-…`），不一致的列會被視為「出現卻未編成」。

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-{NNN}-1 | {AC description} | AT-{NNN}-1-1 | Given...When...Then... | ✅ | Unit | □ |
| AC-{NNN}-1 | {AC description} | AT-{NNN}-1-2 | Given...When...Then... | ✅ | Integration | □ |
| AC-{NNN}-2 | {AC description} | AT-{NNN}-2-1 | Given...When...Then... | ✅ | E2E | □ |
| AC-{NNN}-2 | {AC description} | AT-{NNN}-2-2 | {negative case} | ✅ | Unit | □ |

**覆蓋率統計**:
- 總 AC 數: {N}
- 已映射 AT 數: {N}
- 映射覆蓋率: {N}% （目標: 100%）

---

## 2. 可自動化 AT 格式規範

> **SDD 原則**: AT 必須以可直接轉換為自動化測試的格式撰寫。
>
> 🔴 **實例化時刪除或改成真實 ID**：§2.2、§2.3 的示例區塊（標頭 `AT-001-1-1`、`AT-001-1-2`）只是格式示範。把本模板複製到 `docs/` 填寫時，
> 示例區塊必須刪除，或改成真實 AC 的 AT 並在 §1 補上對應列——否則 `sdd_compile` 會因「標頭出現卻無對應 §1 列」得到 `unmapped_at_ids`（CLI rc 6）。

### 2.1 AT 格式標準（Given-When-Then）

```gherkin
# AT-{NNN}-{Y}-{Z}
# 對應 AC: AC-{NNN}-{Y}
# 測試類型: Unit / Integration / E2E / Contract
# 自動化工具: {tool}

Feature: {FeatureName}

Scenario: {ScenarioDescription}
  Given {precondition}
  And {additional precondition if needed}
  When {action}
  Then {expected outcome}
  And {additional assertion if needed}
```

### 2.2 AT 範例（正向路徑）

```gherkin
# AT-001-1-1
# 對應 AC: AC-001-1 使用者可成功登入
# 測試類型: E2E
# 自動化工具: Playwright

Feature: User Authentication

Scenario: 有效帳號密碼登入成功
  Given 使用者在登入頁面
  And 使用者帳號 "user@example.com" 已存在
  When 使用者輸入正確帳號和密碼
  And 點擊登入按鈕
  Then 使用者被重導至儀表板
  And 顯示歡迎訊息
  And JWT token 已存入 localStorage
```

### 2.3 AT 範例（負向路徑）

```gherkin
# AT-001-1-2
# 對應 AC: AC-001-1 使用者可成功登入（錯誤處理）
# 測試類型: Integration
# 自動化工具: Jest + Supertest

Feature: User Authentication - Error Handling

Scenario: 無效帳號密碼登入失敗
  Given 使用者嘗試登入
  When 使用者輸入錯誤密碼 "wrong_password"
  Then 系統回傳 HTTP 401
  And 回傳錯誤訊息 "Invalid credentials"
  And 不產生任何 JWT token
  And 連續失敗 5 次後帳號被鎖定
```

---

## 3. AT 完整清單

### 3.1 Unit Tests

| AT ID | 對應 AC | 描述 | 測試方法 | 預期結果 |
|-------|---------|------|---------|---------|
| AT-{NNN}-{Y}-{Z} | AC-{NNN}-{Y} | {description} | {method name} | {expected} |

### 3.2 Integration Tests

| AT ID | 對應 AC | 描述 | API/Service | 預期結果 |
|-------|---------|------|-------------|---------|
| AT-{NNN}-{Y}-{Z} | AC-{NNN}-{Y} | {description} | {endpoint} | HTTP {status} |

### 3.3 Contract Tests

| AT ID | 對應 AC | Consumer | Provider | Interaction | 驗證項目 |
|-------|---------|---------|---------|------------|---------|
| AT-{NNN}-{Y}-{Z} | AC-{NNN}-{Y} | {consumer} | {provider} | {interaction} | Schema + Status |

### 3.4 E2E Tests

| AT ID | 對應 AC | 使用者旅程 | 起點 | 終點 | 關鍵斷言 |
|-------|---------|----------|------|------|---------|
| AT-{NNN}-{Y}-{Z} | AC-{NNN}-{Y} | {journey} | {start} | {end} | {assertion} |

---

## 4. 邊界與錯誤測試規格

> **本節的 `AT-{NNN}-E-n` 是文件內編號**：第二段不是數字，**不符合**編譯用 AT 文法 `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`（前兩段須為所屬 AC），
> 所以**不會被 AutoClaude 編譯成 step**。要讓邊界／錯誤 AT 由 AutoClaude 執行者，改命名為 `AT-{NNN}-{Y}-E-{n}`
> （掛在其所屬 AC `AC-{NNN}-{Y}` 之下，符合文法；前兩段 `{NNN}-{Y}` 即所屬 AC）並**列入 §1 映射表**。
> 本表第一欄是場景類型、不是 AC ID，不屬編譯的宣告位置——照本節填寫本身不會讓編譯失敗。

| 場景類型 | AT ID | 描述 | 輸入 | 預期結果 |
|---------|-------|------|------|---------|
| 邊界值（最小） | AT-{NNN}-E-1 | {desc} | {min value} | {expected} |
| 邊界值（最大） | AT-{NNN}-E-2 | {desc} | {max value} | {expected} |
| 空值處理 | AT-{NNN}-E-3 | {desc} | null / empty | 明確錯誤訊息 |
| 非法輸入 | AT-{NNN}-E-4 | {desc} | {invalid input} | HTTP 400 + 錯誤描述 |
| 並發衝突 | AT-{NNN}-E-5 | {desc} | concurrent requests | 冪等或適當衝突回應 |

---

## 5. 測試資料規格

| 資料項目 | 類型 | 說明 | 來源 |
|---------|------|------|------|
| {test_data_1} | 靜態 Fixture | {description} | `tests/fixtures/{file}.json` |
| {test_data_2} | 動態生成 | {description} | Factory / Faker |
| {test_data_3} | 敏感資料（Masked） | {description} | 匿名化生產資料 |

---

## 6. RTM 連結確認

| 追溯項目 | 覆蓋狀態 |
|---------|---------|
| EPIC-{NNN} → F-{NNN} | □ 已映射 |
| F-{NNN} → US-{NNN} | □ 已映射 |
| US-{NNN} → AC-{NNN} | □ 已映射 |
| AC-{NNN} → AT-{NNN} | □ 已映射（本文件） |
| AT-{NNN} → CI Pipeline | □ 已整合 |

---

## 📋 SCG-4 通過標準

| 驗證項目 | 判斷標準 | 狀態 |
|---------|---------|------|
| AC → AT 100% 映射 | 無未映射 AC | □ |
| AT 格式可自動化 | 使用 Given-When-Then 格式 | □ |
| 負向測試覆蓋 | 每個 AC 有至少一個負向 AT | □ |
| 邊界值測試 | 關鍵欄位有邊界值測試 | □ |
| 測試資料規格完整 | 資料來源明確定義 | □ |

**確認人**: ____________  **確認日期**: ____________  **狀態**: □ 通過 / □ 待修訂
