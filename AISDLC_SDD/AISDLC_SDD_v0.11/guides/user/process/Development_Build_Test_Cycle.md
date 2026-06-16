# 開發-編譯-測試循環機制 (Development-Build-Test Cycle)

> **版本**: v1.0
> **適用範圍**: 所有 AISDLC 開發情境
> **最後更新**: 2025-01-11

---

## 🔴 核心原則（CRITICAL）

**🛑 強制規則**: 每完成一支程式（或一個功能單元），**必須立即執行**以下循環，**不可累積開發**。

**🤖 Agent 支援**: 此規則已整合至 [dev-developer Agent](../../agent/core/06.dev-developer-zh.yaml) 的 `core_principles` 第一條和 `quality_standards` 前三條，開發時請自動載入該 Agent 確保遵守。

```
開發 1 支程式
    ↓
立即編譯 (Compile/Build)
    ↓
編譯失敗？ → 🔴 立即停止 → 依照錯誤訊息修復 → 重新編譯
    ↓
編譯成功 ✅
    ↓
執行單元測試 (Unit Test)
    ↓
測試失敗？ → 🔴 立即停止 → 依照規格文檔修復 → 重新測試
    ↓
測試通過 ✅
    ↓
繼續開發下一支程式
```

---

## 🎯 為什麼需要這個循環？

### ❌ 問題場景（不使用循環）

```
開發 10 支程式 → 一次編譯 → 發現 50 個錯誤 → 花 3 小時修復 → 仍有錯誤
```

**後果**:
- 錯誤累積，難以定位問題源頭
- 修復一個錯誤可能引發其他錯誤
- 浪費大量時間在錯誤排查

### ✅ 正確做法（使用循環）

```
開發第 1 支 → 編譯 → 3 個錯誤 → 5 分鐘修復 → 編譯成功 → 測試通過
開發第 2 支 → 編譯 → 1 個錯誤 → 2 分鐘修復 → 編譯成功 → 測試通過
...
開發第 10 支 → 編譯 → 0 個錯誤 → 測試通過
```

**優勢**:
- 問題即時發現，容易定位
- 修復成本低（錯誤少、範圍小）
- 保證每一步都是可編譯、可測試的狀態

---

## 📋 執行檢查清單（每次開發後必做）

### 階段 1: 編譯檢查

```
□ 完成程式碼撰寫（1 支程式 or 1 個功能單元）
□ 儲存所有檔案
□ 執行編譯命令（依專案類型）:
  - Java: `mvn compile` 或 `gradle build`
  - C/C++: `make` 或 `cmake --build`
  - Python: `python -m py_compile <file>.py`
  - TypeScript: `tsc`
  - Go: `go build`
  - Rust: `cargo build`
□ 檢查編譯輸出，是否有錯誤訊息
□ 如有錯誤：立即停止，修復後重新編譯
□ 如無錯誤：繼續下一階段
```

### 階段 2: 單元測試檢查

```
□ 執行單元測試命令（依專案類型）:
  - Java: `mvn test` 或 `gradle test`
  - Python: `pytest` 或 `python -m unittest`
  - JavaScript/TypeScript: `npm test` 或 `jest`
  - Go: `go test`
  - Rust: `cargo test`
□ 檢查測試結果，是否所有測試通過
□ 如有測試失敗：
  - 讀取測試失敗訊息
  - 對照規格文檔（PRD/FRD/SRD）確認預期行為
  - 修復程式碼使其符合規格
  - 重新執行測試
□ 如所有測試通過：繼續開發下一支程式
```

### 階段 3: 文檔更新（如適用）

```
□ 如新增函數/類別，更新 API 文檔
□ 如修改功能，更新相關說明
□ Commit 程式碼與測試（使用有意義的 commit message）
```

---

## 🛑 禁止行為

1. **❌ 禁止累積開發多支程式後才編譯**
   - 錯誤範例：開發 5 支程式 → 一次編譯
   - 正確做法：開發 1 支 → 編譯 → 開發下一支

2. **❌ 禁止編譯失敗後繼續開發**
   - 錯誤範例：編譯失敗 → 先開發其他功能 → 稍後再修
   - 正確做法：編譯失敗 → 立即修復 → 編譯成功 → 才繼續

3. **❌ 禁止跳過單元測試**
   - 錯誤範例：編譯成功 → 直接開發下一支
   - 正確做法：編譯成功 → 執行測試 → 測試通過 → 才繼續

4. **❌ 禁止測試失敗後「先跳過」**
   - 錯誤範例：測試失敗 → 註解掉測試 → 繼續開發
   - 正確做法：測試失敗 → 依規格修復 → 測試通過 → 才繼續

---

## 🔧 特殊情況處理

### 情況 1: 功能跨越多個檔案

**問題**: 一個功能需要修改 3 個檔案才能完成

**解決方案**:
1. 將功能分解為最小可編譯單元
2. 每修改一個檔案，立即編譯測試
3. 如無法分解，完成所有檔案後立即編譯測試

**範例**:
```
修改 File A（新增 interface）→ 編譯 → 成功
修改 File B（實作 interface）→ 編譯 → 成功
修改 File C（使用 interface）→ 編譯 → 成功 → 執行測試
```

### 情況 2: 重構大量程式碼

**問題**: 重構會暫時破壞編譯

**解決方案**:
1. 使用 Git 建立專用分支
2. 分階段重構，每階段確保可編譯
3. 使用漸進式重構（Incremental Refactoring）
4. 保持測試覆蓋率

**範例**:
```
階段 1: 重構 Module A → 編譯 → 測試 → Commit
階段 2: 重構 Module B → 編譯 → 測試 → Commit
階段 3: 重構 Module C → 編譯 → 測試 → Commit
```

### 情況 3: 測試需要外部依賴（資料庫、API）

**問題**: 單元測試需要資料庫連線

**解決方案**:
1. 使用 Mock/Stub 替代外部依賴
2. 使用內嵌測試資料庫（如 H2, SQLite）
3. 使用 Docker 容器快速啟動依賴服務

**範例**:
```python
# ❌ 錯誤：直接依賴真實資料庫
def test_save_user():
    db = connect_to_production_db()
    user = User("test")
    db.save(user)
    assert db.find("test") == user

# ✅ 正確：使用 Mock
def test_save_user():
    mock_db = Mock()
    user = User("test")
    mock_db.save(user)
    mock_db.save.assert_called_once_with(user)
```

---

## 📊 編譯測試循環 KPI

### 建議指標

| 指標 | 目標值 | 說明 |
|------|--------|------|
| **每次開發的程式碼行數** | < 100 行 | 超過 100 行應分解為多個單元 |
| **編譯失敗修復時間** | < 10 分鐘 | 超過 10 分鐘表示單元太大 |
| **單元測試覆蓋率** | > 80% | 確保大部分程式碼有測試保護 |
| **測試失敗修復時間** | < 15 分鐘 | 超過 15 分鐘應重新檢視設計 |
| **每日編譯失敗次數** | < 5 次 | 頻繁失敗表示開發節奏過快 |

### 監控方式

```bash
# 記錄每次編譯結果
echo "$(date) - Compile Result: SUCCESS/FAIL" >> build.log

# 記錄測試結果
echo "$(date) - Test Result: PASS/FAIL" >> test.log

# 統計每日失敗次數
grep "FAIL" build.log | grep "$(date +%Y-%m-%d)" | wc -l
```

---

## 🤝 團隊協作建議

### 1. 使用 CI/CD 強制檢查

**GitHub Actions 範例**:
```yaml
name: Build and Test on Push

on: [push]

jobs:
  build-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build
        run: mvn compile
      - name: Test
        run: mvn test
      - name: Fail if build or test fails
        if: failure()
        run: exit 1
```

### 2. Code Review 檢查點

```
□ 每個 Pull Request 必須編譯成功
□ 每個 Pull Request 必須所有測試通過
□ 禁止合併編譯失敗或測試失敗的程式碼
□ 禁止註解掉失敗的測試
```

### 3. 團隊規範

- **每日站會**: 報告昨日編譯/測試失敗次數
- **Code Freeze**: 發布前禁止提交未測試的程式碼
- **修復優先**: 編譯/測試失敗必須最高優先級修復

---

## 📝 實際操作範例

### 範例 1: Java Spring Boot 開發

```bash
# 步驟 1: 開發一支 REST API Controller
vim src/main/java/com/example/UserController.java

# 步驟 2: 立即編譯
mvn compile
# 輸出: BUILD SUCCESS

# 步驟 3: 執行單元測試
mvn test -Dtest=UserControllerTest
# 輸出: Tests run: 3, Failures: 0, Errors: 0

# 步驟 4: Commit
git add src/main/java/com/example/UserController.java
git commit -m "feat: add GET /users endpoint"

# 步驟 5: 繼續開發下一支
```

### 範例 2: Python Flask 開發

```bash
# 步驟 1: 開發一個 API 路由
vim app/routes.py

# 步驟 2: 檢查語法
python -m py_compile app/routes.py
# 無輸出表示成功

# 步驟 3: 執行單元測試
pytest tests/test_routes.py
# 輸出: 5 passed in 0.12s

# 步驟 4: Commit
git add app/routes.py tests/test_routes.py
git commit -m "feat: add /api/users route"

# 步驟 5: 繼續開發下一支
```

### 範例 3: TypeScript React 開發

```bash
# 步驟 1: 開發一個 React Component
vim src/components/UserList.tsx

# 步驟 2: TypeScript 編譯檢查
npx tsc --noEmit
# 無輸出表示成功

# 步驟 3: 執行測試
npm test -- UserList.test.tsx
# 輸出: PASS src/components/UserList.test.tsx

# 步驟 4: Commit
git add src/components/UserList.tsx
git commit -m "feat: add UserList component"

# 步驟 5: 繼續開發下一支
```

---

## 🔗 相關文檔

### Agent 配置檔

- **[dev-developer Agent](../../agent/core/06.dev-developer-zh.yaml)** - 🔴 開發時必須載入此 Agent
  - `core_principles` 第一條：開發-編譯-測試循環（CRITICAL）
  - `quality_standards` 前三條：編譯測試循環強制執行、編譯失敗零容忍、測試失敗零容忍
  - `dependencies`: 包含本文檔參考

- **[qa-tester Agent](../../agent/core/07.qa-tester-zh.yaml)** - 測試階段使用

### 流程指南

- [Code_Review_Guidelines.md](Code_Review_Guidelines.md) - Code Review 標準

### 如何使用 dev-developer Agent

**開發任務開始時**，請 Claude Code 執行以下載入：

```
請以 dev-developer Agent 角色進行開發，
遵循 AISDLC/framework/agent/core/06.dev-developer-zh.yaml 中的所有規範，
特別是：
1. core_principles 第一條：開發-編譯-測試循環（CRITICAL）
2. quality_standards 前三條：編譯測試循環強制執行、編譯失敗零容忍、測試失敗零容忍
```

**Agent 會自動確保**：
- ✅ 每支程式開發完成後，立即執行編譯 → 修復錯誤 → 單元測試 → 修復失敗
- ✅ 編譯失敗必須立即停止開發，優先修復至編譯成功
- ✅ 單元測試失敗必須立即依規格文檔修復，絕不跳過或註解測試

---

**文檔元數據**:
- **文檔版本**: v1.0
- **建立日期**: 2025-01-11
- **最後更新**: 2025-01-11
- **維護者**: AISDLC Framework Team
- **文檔狀態**: Final
