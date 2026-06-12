---
name: brownfield
description: 分析既有系統的代碼品質、架構問題和改進機會
user-invocable: true
disable-model-invocation: false
argument-hint: "[focus: 分析重點 (full/code-quality/architecture/tech-debt/performance)]"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# Brownfield System Analysis Skill

基於 AISDLC Brownfield 情境的既有系統分析技能。

---

## 觸發方式

```bash
/brownfield                    # 完整分析
/brownfield code-quality       # 專注代碼品質
/brownfield architecture       # 專注架構分析
/brownfield tech-debt          # 專注技術債務
/brownfield performance        # 專注效能問題
```

---

## 執行流程

### 階段 1: 專案結構探索 (15分鐘)

**任務清單**:
1. 掃描專案目錄結構
2. 識別技術棧和框架
3. 分析套件依賴
4. 識別入口點和核心模組

**自動探索命令**:
```bash
# 目錄結構
find . -type d -name node_modules -prune -o -type f -print | head -100

# 依賴分析
cat package.json | jq '.dependencies, .devDependencies'

# 程式碼統計
npx cloc . --exclude-dir=node_modules,dist,build
```

**產出物**: 專案概覽報告

```markdown
## 專案概覽

### 技術棧
- 語言: TypeScript 5.x
- 框架: Next.js 14
- 資料庫: PostgreSQL + Prisma
- 測試: Jest + Testing Library

### 目錄結構
- `src/app/` - 頁面路由 (App Router)
- `src/components/` - React 元件
- `src/lib/` - 工具函數
- `src/services/` - 業務邏輯

### 關鍵數據
- 總行數: ~15,000 行
- 檔案數: 120 個
- 依賴數: 45 個
```

---

### 階段 2: 代碼品質分析 (20分鐘)

**分析項目**:

#### 2.1 複雜度分析
```bash
# 使用 ESLint 複雜度規則
npx eslint . --rule 'complexity: ["warn", 10]' --format json

# 或使用 SonarQube
npx sonar-scanner
```

**複雜度指標**:
| 指標 | 良好 | 警告 | 危險 |
|------|------|------|------|
| 圈複雜度 | < 10 | 10-20 | > 20 |
| 認知複雜度 | < 15 | 15-25 | > 25 |
| 函數行數 | < 30 | 30-50 | > 50 |
| 檔案行數 | < 300 | 300-500 | > 500 |

#### 2.2 重複代碼檢測
```bash
# 使用 jscpd
npx jscpd ./src --min-lines 5 --reporters html,json
```

#### 2.3 依賴健康度
```bash
# 檢查過時依賴
npm outdated

# 檢查安全漏洞
npm audit

# 檢查未使用依賴
npx depcheck
```

**產出物**: 代碼品質報告

```markdown
## 代碼品質報告

### 複雜度問題 (需立即處理)
| 檔案 | 函數 | 複雜度 | 建議 |
|------|------|--------|------|
| `src/services/order.ts` | processOrder | 25 | 拆分為多個函數 |
| `src/utils/validator.ts` | validateAll | 18 | 使用策略模式 |

### 重複代碼 (建議重構)
- `src/pages/user/*.tsx` 有 3 處相似代碼 (約 45 行)
- `src/api/*.ts` 錯誤處理邏輯重複 (約 20 行)

### 依賴問題
- 🔴 5 個高風險安全漏洞
- 🟡 12 個過時依賴
- ⚪ 3 個未使用依賴
```

---

### 階段 3: 架構分析 (20分鐘)

**分析項目**:

#### 3.1 模組依賴關係
```bash
# 生成依賴圖
npx madge --image dependency-graph.svg ./src
```

#### 3.2 分層架構檢查

**理想分層**:
```
┌─────────────────────────────┐
│     Presentation Layer      │  ← pages, components
├─────────────────────────────┤
│     Application Layer       │  ← services, use-cases
├─────────────────────────────┤
│       Domain Layer          │  ← entities, value-objects
├─────────────────────────────┤
│    Infrastructure Layer     │  ← repositories, external APIs
└─────────────────────────────┘
```

**檢查規則**:
- ❌ 上層不應直接依賴下層實作
- ❌ 跨層呼叫應經過介面
- ❌ 循環依賴必須消除

#### 3.3 架構問題識別

**常見問題**:
| 問題類型 | 症狀 | 影響 | 優先級 |
|---------|------|------|--------|
| 循環依賴 | A → B → C → A | 難以維護 | 🔴 高 |
| 過度耦合 | 單一模組被 >10 處引用 | 變更風險高 | 🟡 中 |
| 分層混亂 | UI 直接呼叫 DB | 可測試性差 | 🔴 高 |
| 缺少抽象 | 直接依賴第三方 SDK | 替換困難 | 🟡 中 |

---

### 階段 4: 技術債務評估 (15分鐘)

**技術債務分類**:

```markdown
## 技術債務清單

### 🔴 緊急 (影響穩定性)
1. **無錯誤邊界**
   - 位置: 全站
   - 影響: 任何錯誤導致白屏
   - 建議: 新增 ErrorBoundary 元件

2. **硬編碼配置**
   - 位置: `src/config.ts`
   - 影響: 環境切換困難
   - 建議: 移至環境變數

### 🟡 重要 (影響開發效率)
1. **缺少 TypeScript 嚴格模式**
   - 影響: 類型安全不完整
   - 建議: 啟用 strict: true

2. **測試覆蓋率低**
   - 當前: 23%
   - 目標: > 70%
   - 建議: 優先補充核心邏輯測試

### ⚪ 一般 (可延後處理)
1. **舊版套件**
   - React 17 → 18
   - 建議: 規劃升級
```

---

### 階段 5: 改進建議 🔴

🔴 **確認點**: 根據分析結果，向使用者確認改進優先級

**改進路線圖**:

```markdown
## 建議改進路線圖

### Phase 1: 穩定性 (1-2週)
- [ ] 新增全域錯誤處理
- [ ] 修復高風險安全漏洞
- [ ] 配置管理重構

### Phase 2: 可維護性 (2-4週)
- [ ] 消除循環依賴
- [ ] 重構高複雜度函數
- [ ] 補充單元測試

### Phase 3: 效能優化 (可選)
- [ ] 代碼分割優化
- [ ] 資料庫查詢優化
- [ ] 快取策略實作

### 預估效益
- 開發效率提升: 約 30%
- Bug 率降低: 約 40%
- 維護成本降低: 約 25%
```

---

## 產出物清單

| 產出物 | 說明 |
|--------|------|
| `Brownfield_Analysis_Report.md` | 完整分析報告 |
| `Code_Quality_Report.md` | 代碼品質詳細報告 |
| `Tech_Debt_Registry.md` | 技術債務清單 |
| `Improvement_Roadmap.md` | 改進路線圖 |

---

## 後續 Skill

分析完成後，可根據結果使用：

- `/refactor` - 執行代碼重構
- `/performance` - 效能優化
- `/testing` - 補充測試
- `/security` - 安全強化

---


## 相關檔案

- SOP 參考: `scenarios/brownfield/SOP_QuickRef.md`

**基於**: AISDLC v0.09 Brownfield 情境
**維護者**: AISDLC Framework Team
