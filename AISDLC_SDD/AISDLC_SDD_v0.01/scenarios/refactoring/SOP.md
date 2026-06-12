# Refactoring 程式碼重構與品質改善 SOP

**版本**: v0.01 | **最後更新**: 2026-03-26

> 📘 **文檔導航**: [快速參考 QuickRef](./SOP_QuickRef.md) | [深度技術指南 DeepDive](./SOP_DeepDive.md) | [情境轉換指引](../SCENARIO_TRANSITION_GUIDE.md)

> 📝 **關於範例連結說明**:
> 本 SOP 中部分連結（如文檔路徑、配置檔案等）為示例性質，
> 展示一般專案的文檔結構。實際使用時，請根據您的專案結構調整路徑。

## 🎯 情境概述

**適用場景**：程式碼品質改善、技術債清理、架構優化、可維護性提升、🆕 **技術棧替換**（部分或全棧）

> **⚠️ Refactoring vs Migration SOP 適用指引**：
> - **部分技術棧替換**（僅換前端、僅換後端、或僅換 DB）→ 使用本 Refactoring SOP 即可
> - **全技術棧遷移**（前端+後端+DB 同時替換）→ 有兩種選擇：
>   - ✅ **輕量版**：使用本 Refactoring SOP（步驟 2.5 + 策略 F 分層漸進遷移），適合小團隊、CI/CD 安全要求為 Standard 等級（L0+L1+SAST）
>   - ✅ **完整版**：使用 [Migration SOP](../migration/SOP.md)，適合需要 Advanced 安全等級（L0+L1+SAST+Container Scan+L2 Contract Test+L3 Canary Deploy）的生產系統
> - **判斷依據**：若系統為高流量生產環境、需要 Canary 部署與自動回滾，建議使用 Migration SOP

**預計時間**:
- 📋 **AISDLC 規劃階段**: 3-4 小時
  - **規劃時間** (AI 分析 + 人工確認): 3-4 小時
  - **執行時間** (依重構規模):
    - 小規模重構 (單一模組/檔案): 1-2 週
    - 中規模重構 (多模組/子系統): 2-4 週
    - 大規模重構 (架構級/全系統): 4-8 週
- 🔨 **實際執行階段**: 1-8 週 (依重構規模而定)

> 💡 **時間估算說明**:
> - **規劃時間**指使用 AISDLC 流程進行代碼品質分析、重構策略設計、測試計畫制定的時間
> - **執行時間**指實際重構實施的時間，會因代碼複雜度、技術債程度、測試覆蓋率而有很大差異
> - 小規模重構通常指單一模組內的代碼改善或小範圍設計模式應用
> - 中規模重構指跨模組的架構調整或設計模式重構
> - 大規模重構指架構層級的重構或全系統技術債清理

**涉及角色**：SD, Code-Analyzer, Dev-Senior, QA, Technical-Writer；🆕 X-Large/技術棧遷移時額外：SA, BA, PM/PO, DevOps, Performance-Engineer, Mobile-Architect（行動平台時）

**最終產出**：代碼品質分析報告 + 重構計畫 + 重構實作指引 + 驗證測試計畫 + 前後對比報告

---

## 🤝 協作模式 (Phase 2: v0.01)

### 主要協作模式

#### 1. Lead-Support (主導-支援)
- **主導 Agent**: SD-Architect
- **支援 Agents**: Code-Analyzer, Dev-Senior, QA
- **使用階段**: 重構策略設計、架構改進決策
- **模式說明**: SD 主導重構策略，Code-Analyzer 提供分析支援，Dev-Senior 提供實作建議

#### 2. Iterative-Refinement (迭代精煉)
- **循環流程**: 分析 → 重構設計 → 小範圍實作 → 測試驗證 → 評估效果 → 繼續/調整
- **使用階段**: 重構實作過程
- **模式說明**: 採用漸進式重構，每次小範圍改進並驗證

### 次要協作模式

#### 3. Peer-Review (同儕審查)
- **使用階段**: Code-Analyzer ↔ Dev-Senior 重構方案審查
- **模式說明**: 靜態分析與實作經驗相互驗證

---

## 📋 前置準備檢查清單

### 必要材料
- [ ] 目標代碼庫存取權限
- [ ] 重構動機和目標描述
- [ ] 現有測試套件 (如有)
- [ ] 重構時間預算
- [ ] 團隊技能盤點

### 選擇性材料
- [ ] 代碼品質報告 (SonarQube/CodeClimate 等)
- [ ] 效能分析報告 (如涉及效能優化)
- [ ] 技術債清單
- [ ] 過往維護痛點記錄
- [ ] 架構文檔 (如有)

### 重構前置條件檢查
- [ ] 有足夠的測試覆蓋（建議 ≥60%）或願意補充測試
- [ ] 團隊對重構目標有共識
- [ ] 有足夠的時間和資源
- [ ] 業務需求暫時穩定（避免邊重構邊加需求）

---

## 🔧 材料缺失應對方案

> 💡 **現實情況**: 重構專案常因歷史代碼缺乏文檔和測試而困難重重。以下提供實用的替代方案。

| 缺失材料 | 影響程度 | 應對方案 | 預計額外時間 |
|---------|---------|---------|-------------|
| **代碼品質報告** | 🔴 高 | • **方案 1**: 使用免費工具快速掃描 (SonarLint、ESLint、Pylint)<br>• **方案 2**: 使用 Code-Analyzer Agent 自動分析代碼異味<br>• **方案 3**: 手動代碼審查,記錄主要問題區域<br>• **方案 4**: 先聚焦已知痛點區域,後續擴展分析範圍 | +1-3 小時 |
| **測試覆蓋率** | 🔴 高 | • **方案 1**: 使用測試工具生成覆蓋率報告 (Jest、pytest-cov、JaCoCo)<br>• **方案 2**: 先補充關鍵路徑測試 (Golden Master Testing)<br>• **方案 3**: 使用 Characterization Tests 記錄現有行為<br>• **方案 4**: 採用保守重構策略,小步快跑降低風險 | +2-4 小時 |
| **重構目標** | 🔴 高 | • **方案 1**: 與團隊進行重構目標工作坊<br>• **方案 2**: 分析代碼品質報告,識別 Top 10 問題<br>• **方案 3**: 收集開發者痛點,優先解決影響最大的問題<br>• **方案 4**: 使用 SMART 方法定義可衡量的目標 | +1-2 小時 |
| **風險評估** | 🟡 中 | • **方案 1**: 使用風險評分矩陣 (影響範圍 × 技術複雜度)<br>• **方案 2**: 分析代碼變更頻率和複雜度熱點<br>• **方案 3**: 團隊討論識別高風險區域<br>• **方案 4**: 先重構低風險區域驗證流程 | +0.5-1 小時 |
| **重構時間預算** | 🟡 中 | • **方案 1**: 使用歷史數據估算 (過往重構經驗)<br>• **方案 2**: 參考業界標準時間分配 (10-20% Sprint 時間)<br>• **方案 3**: 先試點重構小範圍,推算整體時間<br>• **方案 4**: 採用漸進式重構,分散到日常開發中 | +0.5-1 小時 |
| **效能分析報告** | 🟢 低 | • **方案 1**: 使用免費 Profiler 工具 (Chrome DevTools、py-spy)<br>• **方案 2**: 建立簡易 Benchmark 測試<br>• **方案 3**: 暫時跳過效能優化,聚焦代碼品質<br>• **方案 4**: 使用日誌分析找出慢查詢 | +0.5-1 小時 |
| **架構文檔** | 🟢 低 | • **方案 1**: 使用工具生成依賴關係圖 (Madge、dependency-cruiser)<br>• **方案 2**: Code-Analyzer 自動生成架構概覽<br>• **方案 3**: 手動繪製關鍵模組架構圖<br>• **方案 4**: 暫時跳過,聚焦代碼級重構 | +1-2 小時 |

### 無測試保護時的應對流程

若代碼完全沒有測試,建議採用「**測試優先重構策略**」:

#### Phase 0: 建立安全網 (額外 1-2 週)

1. **Characterization Tests (特徵測試)** - 2-3 天
   - 記錄現有系統的實際行為
   - 使用 Approval Tests 快照當前輸出
   - 涵蓋關鍵業務流程

   ```javascript
   // 範例: Characterization Test
   test('記錄現有計算邏輯行為', () => {
     const inputs = [
       { price: 100, discount: 0.1 },
       { price: 200, discount: 0.2 },
       { price: 50, discount: 0 }
     ];

     const outputs = inputs.map(input => calculateTotal(input));

     // 第一次執行會生成快照,後續執行會比對
     expect(outputs).toMatchSnapshot();
   });
   ```

2. **Golden Master Testing** - 1-2 天
   - 對複雜系統建立「黃金標準」輸出
   - 重構後對比輸出,確保行為一致

3. **補充單元測試** - 3-5 天
   - 優先覆蓋關鍵業務邏輯 (目標 60%+)
   - 使用測試覆蓋率工具找出缺口

4. **整合測試** - 2-3 天
   - 測試模組間互動
   - 確保接口穩定

### 重構範圍過大時的應對策略

若重構範圍超出預期,建議採用「**漸進式重構 (Incremental Refactoring)**」:

#### 策略 1: 絞殺者模式 (Strangler Pattern)

```
舊代碼 (Legacy)
    ↓
建立新實作 (New Implementation)
    ↓
逐步遷移功能
    ↓
最終淘汰舊代碼
```

**優點**: 風險低,可隨時停止
**適用**: 大型模組重構

#### 策略 2: 分支抽象 (Branch by Abstraction)

```
1. 抽取介面
2. 建立新實作
3. 切換到新實作
4. 移除舊實作
```

**優點**: 持續交付,不阻塞開發
**適用**: 核心模組改造

#### 策略 3: 平行運行 (Parallel Run)

```
新舊實作並行 → 對比結果 → 驗證一致性 → 切換
```

**優點**: 高度安全
**適用**: 關鍵業務邏輯

### 團隊共識缺失時的應對方案

若團隊對重構目標無共識:

1. **召開重構啟動會議** (2 小時)
   - 展示代碼品質問題和影響
   - 討論重構目標和優先級
   - 達成 SMART 目標共識

2. **試點重構 (Pilot Refactoring)** (1-2 天)
   - 選擇小範圍模組進行試點
   - 展示重構前後對比
   - 收集團隊回饋,調整策略

3. **建立重構文化**
   - 每個 Sprint 分配 10-20% 時間用於重構
   - 遵循 Boy Scout Rule (隨手改善原則)
   - 重構納入 Code Review 標準

---

## 🛠️ 免費工具替代方案

> 💡 **成本考量**: 商業代碼品質工具價格高昂（SonarQube Enterprise $150k+/年），以下提供功能相近的免費/開源替代方案。

### 代碼品質分析工具

| 工具類別 | 商業方案 | 免費/開源替代 | 功能對比 | 適用場景 |
|---------|---------|-------------|---------|---------|
| **靜態代碼分析 (SAST)** | SonarQube Enterprise<br>Checkmarx | **SonarQube Community**<br>**ESLint + Plugins**<br>**Pylint/Flake8** | 90% 功能相同<br>缺少: 分支分析、企業級報告 | 中小型團隊<br>單一語言專案 |
| **代碼複雜度分析** | CodeClimate | **Radon** (Python)<br>**complexity-report** (JS)<br>**lizard** (多語言) | 精準度相同<br>缺少: 雲端儀表板 | 本地分析<br>CI/CD 整合 |
| **依賴關係分析** | Structure101 | **Madge** (JS/TS)<br>**dependency-cruiser**<br>**pydeps** (Python) | 功能齊全<br>缺少: 視覺化編輯 | 循環依賴檢測<br>架構違規檢查 |
| **重複代碼檢測** | - | **jscpd** (多語言)<br>**PMD CPD** (Java)<br>**duplo** (C/C++) | 開源方案完全免費 | 重複代碼清理 |
| **測試覆蓋率** | - | **Jest** (JS - 內建)<br>**pytest-cov** (Python)<br>**JaCoCo** (Java) | 測試框架內建,免費 | 所有測試場景 |
| **代碼格式化** | - | **Prettier** (JS/TS)<br>**Black** (Python)<br>**clang-format** (C/C++) | 業界標準,免費 | 代碼風格統一 |

### 工具安裝與使用指南

#### 1. SonarQube Community Edition（代碼品質綜合分析）

**安裝（Docker 方式）**:
```bash
# 啟動 SonarQube
docker run -d --name sonarqube \
  -p 9000:9000 \
  sonarqube:community

# 訪問 http://localhost:9000 (預設帳密: admin/admin)
```

**掃描專案**:
```bash
# 安裝 SonarScanner
npm install -g sonarqube-scanner

# 建立 sonar-project.properties
cat > sonar-project.properties <<EOF
sonar.projectKey=my-project
sonar.sources=src
sonar.host.url=http://localhost:9000
sonar.login=<your-token>
EOF

# 執行掃描
sonar-scanner
```

**CI/CD 整合**:
```yaml
# .github/workflows/sonarqube.yml
name: SonarQube Analysis
on: [push, pull_request]
jobs:
  sonarqube:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: SonarQube Scan
        uses: sonarsource/sonarqube-scan-action@master
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
          SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}
```

#### 2. ESLint + Security/Complexity Plugins（JavaScript/TypeScript）

**安裝**:
```bash
npm install --save-dev \
  eslint \
  eslint-plugin-security \
  eslint-plugin-sonarjs \
  eslint-plugin-complexity
```

**配置 (.eslintrc.json)**:
```json
{
  "extends": [
    "eslint:recommended",
    "plugin:security/recommended",
    "plugin:sonarjs/recommended"
  ],
  "plugins": ["security", "sonarjs"],
  "rules": {
    "complexity": ["error", { "max": 10 }],
    "max-depth": ["error", 4],
    "max-lines-per-function": ["error", { "max": 50 }],
    "sonarjs/cognitive-complexity": ["error", 15]
  }
}
```

**執行**:
```bash
# 掃描代碼
eslint src/

# 自動修復
eslint src/ --fix

# 輸出 JSON 報告
eslint src/ -f json -o eslint-report.json
```

#### 3. Madge（依賴關係與循環依賴檢測）

**安裝**:
```bash
npm install -g madge
```

**使用**:
```bash
# 檢測循環依賴
madge --circular src/

# 生成依賴關係圖（需安裝 Graphviz）
madge --image deps-graph.svg src/

# JSON 輸出
madge --json src/ > dependencies.json

# 檢查違反架構規則
madge --exclude '^(node_modules|test)' --circular src/
```

#### 4. Radon（Python 複雜度分析）

**安裝**:
```bash
pip install radon
```

**使用**:
```bash
# 循環複雜度分析
radon cc src/ -a -s

# 認知複雜度
radon cc src/ --total-average

# 可維護性指數
radon mi src/ -s

# 原始指標（LOC, SLOC, Comments）
radon raw src/ -s

# 輸出 JSON
radon cc src/ -j > complexity-report.json
```

#### 5. jscpd（重複代碼檢測）

**安裝**:
```bash
npm install -g jscpd
```

**使用**:
```bash
# 檢測重複代碼
jscpd src/

# 設定最小重複行數
jscpd src/ --min-lines 5

# 輸出 HTML 報告
jscpd src/ -r html -o ./reports

# 配置檔案 (.jscpd.json)
{
  "threshold": 3,
  "reporters": ["html", "console"],
  "ignore": ["**/__tests__/**", "**/node_modules/**"],
  "format": ["javascript", "typescript"]
}
```

#### 6. Lizard（多語言複雜度分析）

**安裝**:
```bash
pip install lizard
```

**使用**:
```bash
# 分析多種語言
lizard src/

# 設定複雜度閾值
lizard -C 15 src/

# 輸出 HTML 報告
lizard -o lizard-report.html src/

# 支援語言: C/C++, Java, C#, JavaScript, Python, Ruby, PHP, Swift, Objective-C
```

### 完整 CI/CD 整合範例

```yaml
# .github/workflows/code-quality.yml
name: Code Quality Check

on: [push, pull_request]

jobs:
  quality-check:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      # ESLint 靜態分析
      - name: ESLint Check
        run: |
          npm ci
          npm run lint -- --format json --output-file eslint-report.json

      # 循環依賴檢測
      - name: Circular Dependency Check
        run: |
          npx madge --circular src/
          if [ $? -ne 0 ]; then
            echo "❌ 發現循環依賴！"
            exit 1
          fi

      # 重複代碼檢測
      - name: Duplicate Code Check
        run: |
          npx jscpd src/ --threshold 3

      # 測試覆蓋率
      - name: Test Coverage
        run: |
          npm test -- --coverage --coverageReporters=json-summary
          COVERAGE=$(jq '.total.lines.pct' coverage/coverage-summary.json)
          if (( $(echo "$COVERAGE < 80" | bc -l) )); then
            echo "❌ 測試覆蓋率 $COVERAGE% < 80%"
            exit 1
          fi

      # 上傳報告
      - name: Upload Reports
        uses: actions/upload-artifact@v3
        with:
          name: code-quality-reports
          path: |
            eslint-report.json
            coverage/
```

### 工具選擇建議

| 專案規模 | 推薦工具組合 | 年度成本 |
|---------|------------|---------|
| **小型** (<10 人) | ESLint + Madge + Jest | $0 |
| **中型** (10-50 人) | SonarQube Community + Madge + jscpd | $0 (自架) |
| **大型** (50+ 人) | SonarQube Enterprise 或<br>開源組合 + 自建儀表板 | $0 或 $150k+ |

### 商業方案 vs 開源方案對比

| 考量因素 | 商業方案 | 開源方案 |
|---------|---------|---------|
| **成本** | $50k-200k/年 | $0 (僅人力成本) |
| **整合度** | 開箱即用 | 需自行整合 |
| **支援** | 專業技術支援 | 社群支援 |
| **功能** | 全面 | 核心功能齊全 |
| **客製化** | 有限 | 高度可客製 |
| **學習曲線** | 低 | 中等 |
| **適用團隊** | 大型企業 | 中小型團隊 |

---

## 🎯 Claude Code Skills 整合指引 (v0.01+)

> **🔴 重要**：在重構流程中，可透過 Claude Code Skills 快速觸發特定能力。以下列出各階段建議使用的 Skills。

### 各階段建議 Skills

| 階段 | 建議 Skill | 觸發時機 |
|------|-----------|---------|
| 階段 1 啟動 | `/sd-architect` | 啟動 SD 角色進行架構評估 |
| 階段 2 品質分析 | `/refactoring-code-quality` | 執行代碼品質分析 |
| 階段 2 品質分析 | `/sa-analyst` | 🔧 需求重新分析與業務邏輯提取（技術棧遷移時，需在品質分析階段同步進行） |
| 階段 2 品質分析 | `/performance-optimization` | 🔧 效能基準線建立（技術棧遷移時，需先記錄舊系統效能作為對比基準） |
| 階段 2 品質分析 | `/brownfield-analysis` | 舊系統現況分析（技術棧遷移時） |
| 階段 3 目標設定 | `/pm-planning` | 目標優先級與 ROI 決策（X-Large 規模時） |
| 階段 4 策略制定 | `/database-migration` | 🔧 資料庫遷移規劃：Schema 轉換、SQL 語法改寫（涉及 DB 遷移時） |
| 階段 5 實作指引 | `/dev-review` | 代碼審查與實作指導 |
| 階段 5 實作指引 | `/sprint-planning` | 迭代規劃（中大型重構時） |
| 階段 5 實作指引 | `/integration-database` | 🔧 新 DB 整合設定：ORM/連線池/交易管理（涉及 DB 遷移時，與 `/database-migration` 互補） |
| 階段 5 實作指引 | `/mobile-development` | 新增行動平台（Android/macOS）支援時 |
| 階段 6 驗證 | `/qa-testing` | 回歸測試策略制定 |
| 階段 6 驗證 | `/performance-optimization` | 效能基準對比（與階段 2 基準線比較） |
| 階段 6 驗證 | `/security-audit` | 安全審計（涉及認證/授權重構時） |
| 階段 7 對比展示 | `/performance-optimization` | 效能前後對比分析（與階段 2 基準線比較） |
| 階段 7 對比展示 | `/code-review` | 重構成果審查、品質指標對比 |
| 階段 8 部署 | `/devops-github-actions` | CI/CD Pipeline 重建 |
| 階段 8 部署 | `/release-management` | 版本發布管理 |

> **🔧 標記說明**：標有 🔧 的 Skill 為本次模擬測試後新增或調整的項目。

### 技術棧遷移額外 Skills

| Skill | 觸發時機 | 用途說明 |
|-------|---------|---------|
| `/brownfield-analysis` | 階段 2 - 舊系統現況分析 | 分析現有代碼品質、架構問題 |
| `/database-migration` | 階段 4 - DB 遷移規劃 | Schema/SQL/SP 轉換規劃 |
| `/integration-database` | 階段 5 - 新 DB 整合設定 | ORM、連線池、交易管理設定 |
| `/integration-api-client` | 階段 5 - API 客戶端設計 | 新舊系統對接 API 設計 |
| `/code-review` | 階段 5-6 - 遷移代碼審查 | 確保遷移代碼品質 |
| `/testing-strategy` | 階段 6 - 跨系統對比測試 | 新舊系統行為等價驗證 |
| `/mobile-development` | 階段 5 - 新增行動/桌面平台 | Android/macOS 開發規劃 |
| `/integration-redis` | 階段 5 - 快取/Session 共享 | 跨系統快取策略 |
| `/security-audit` | 全程 - 遷移安全審計 | 確保遷移過程不引入安全漏洞 |
| `/performance-optimization` | 階段 2+6+7 - 效能基準對比 | 舊系統基準線建立 → 新系統效能驗證 |
| `/compliance-audit` | 全程 - 合規審查（電商/支付/個資場景） | 涉及支付、個資處理時觸發，確保 GDPR/PCI-DSS 合規 |

---

## 🔄 開發-編譯-測試循環 (AISDLC 強制規則)

> **🔴 CRITICAL**：依據 AISDLC CLAUDE.md 強制規則，重構實作階段必須嚴格遵守以下循環。

```
重構 1 個方法/類別/模組
    ↓
立即編譯 (Compile/Build)
    ↓
編譯失敗？ → 🔴 立即停止 → 修復 → 重新編譯
    ↓
編譯成功 ✅
    ↓
執行單元測試 (Unit Test)
    ↓
測試失敗？ → 🔴 立即停止 → 修復 → 重新測試
    ↓
測試通過 ✅ → Commit
    ↓
繼續重構下一個方法/類別/模組
```

**禁止行為**：
- ❌ 重構多個模組後才編譯
- ❌ 編譯失敗繼續重構其他模組
- ❌ 跳過單元測試直接重構下一個

---

## 📋 Workflow 觸發時機對照表

> 以下說明 Refactoring 情境中各 Workflow 的觸發時機，對應 AISDLC_INIT.md 中 `auto_load_config.refactoring.workflows` 的配置。

| Workflow | 觸發時機 | 說明 |
|----------|---------|------|
| `refactoring-planning-flow` | 階段 1-7 全程 | 🔴 **主流程 Workflow**，貫穿重構的品質分析→目標設定→策略制定→實作→驗證→對比 |
| `requirements-extraction` | 階段 2（部分技術棧替換時） | 從舊系統代碼中系統性提取業務需求和規則 |
| `change-management` | 階段 3-5 | 重構引起的變更管理，追蹤 API 變更、Schema 變更對上下游的影響 |
| `user-story-design` | 階段 3 | 將重構目標轉化為可追蹤的 User Story（X-Large 規模時） |
| `api-specification` | 階段 4-5 | API 重新設計時觸發，確保新舊 API 對照完整 |
| `consistency-check` | 階段 6-7 | 驗證重構後文檔一致性（PRD/FRD/SRD/API 交叉驗證） |
| `interaction-analysis` | 階段 4 | 新架構的前後端互動分析（部分技術棧替換時必要） |
| `validation-documentation` | 階段 6 | 重構後的需求驗證，確保業務邏輯無遺漏 |
| `sprint-execution` | 階段 5（實作階段） | 重構實作的迭代執行，遵循開發-編譯-測試循環 |

> **⚠️ 全技術棧遷移 Workflow 說明**：上述 Workflow 配置同樣適用於全技術棧遷移（X-Large 規模）。若選擇使用 [Migration SOP](../migration/SOP.md)（Advanced CI/CD 安全等級），請參考其 Workflow 對應表，兩者 Workflow 覆蓋範圍一致。

---

## 🔒 CI/CD 安全基線與增強掃描（強制前置）

> **⚠️ CRITICAL**: 開始重構前，必須確認 CI/CD Pipeline 已配置以下安全層級。
> **Refactoring 情境安全等級: Standard** (L0 + L1 + SAST)

### Layer 0: Security Baseline（強制）

所有 PR 必須通過以下檢查：

| 檢查項 | 工具 | 阻塞等級 |
|--------|------|---------|
| Secret Detection | TruffleHog / gitleaks | 🔴 永遠阻塞 |
| Dependency Scan (SCA) | Trivy / npm audit | 🔴 Critical/High 阻塞 |
| License Compliance | license-checker | ⚠️ GPL-3.0/AGPL 阻塞 |

📖 **配置範本**: [Layer0_Security_Baseline_Template.md](../../docs_template/scenario_specific/devops/Layer0_Security_Baseline_Template.md)

### Layer 1: Build & Verify（強制）

| 關卡 | 目的 | 阻塞等級 |
|------|------|---------|
| Lint + Format | 程式碼風格一致性 | 🔴 失敗阻塞 |
| Compile / Build | 編譯成功 | 🔴 失敗阻塞 |
| Unit Test + Coverage | 覆蓋率 ≥ 80% | 🔴 失敗阻塞 |

📖 **配置範本**: [Layer1_Build_Verify_Template.md](../../docs_template/scenario_specific/devops/Layer1_Build_Verify_Template.md)

### 增強安全掃描: SAST（Standard 等級）

重構可能引入安全漏洞，SAST 靜態分析確保重構後代碼安全性不降級。

| 掃描類型 | 工具 | 阻塞策略 |
|---------|------|---------|
| **SAST** | Semgrep / CodeQL | 🔴 Critical/High 阻塞 |

📖 **配置範本**: [Security_Scan_Integration_Template.md](../../docs_template/scenario_specific/devops/Security_Scan_Integration_Template.md)

- [ ] Layer 0 Security Baseline 已配置
- [ ] Layer 1 Build & Verify 已配置
- [ ] SAST 掃描已配置（Semgrep 或 CodeQL）

### ⚡ Performance Benchmark Gate（⚠️ 選配）

> 重構不應引入效能退化，可選配 Micro-Benchmark 驗證重構後效能不降級。

| 層級 | 觸發時機 | 阻塞策略 | 說明 |
|------|---------|---------|------|
| **Micro-Benchmark** | 每次 PR | 🔴 退化 > 10% 阻塞 | 確保重構不引入效能退化 |

📖 **配置範本**: [Performance_Benchmark_Gate_Template.md](../../docs_template/scenario_specific/devops/Performance_Benchmark_Gate_Template.md)
🔧 **建置流程**: [devops-setup-flow 步驟 0.8](../../workflow/scenario-specific/devops-setup-flow.md)

### 🔔 Event-Driven Agent Notification（🔴 強制）

> PR 事件通知為強制。情境專屬觸發：mutation-test 結果 + diff-coverage 報告 + 重構影響分析報告。

📖 **配置範本**: [Event_Driven_Agent_Notification_Template.md](../../docs_template/scenario_specific/devops/Event_Driven_Agent_Notification_Template.md)
🔧 **建置流程**: [devops-setup-flow 步驟 0.10](../../workflow/scenario-specific/devops-setup-flow.md)

---

## 🚀 完整執行流程

### 階段 1：啟動和情境確認 (20 分鐘)

#### 步驟 1.1：載入 AISDLC 框架
```
執行指令：
「請載入 AISDLC_SDD_INIT.md (v0.01)，我要進行代碼重構」

或具體說明：
「請載入 AISDLC_INIT.md，我要重構 Web 應用的認證模組」
「請載入 AISDLC_INIT.md，我要改善 iOS App 的資料層架構」
「請載入 AISDLC_INIT.md，我要清理專案中的技術債」
「請載入 AISDLC_INIT.md，我要將系統從 Vue+Python+Oracle 遷移到 React+Spring Boot+PostgreSQL」
```

#### 步驟 1.2：回答情境識別問題
系統會詢問：
- 重構範圍 (單一模組/多個模組/全專案/全技術棧)
- 重構類型：
  - **代碼品質** - 消除 Code Smell、降低複雜度
  - **架構優化** - 模組解耦、設計模式引入
  - **效能優化** - 效能瓶頸消除、資源使用優化
  - **可測試性** - 依賴注入改造、測試覆蓋補強
  - **🆕 技術棧遷移** - 前端/後端/DB 框架替換（如 Vue→React, Python→Java, Oracle→PostgreSQL）
- 代碼現況 (品質等級、測試覆蓋率)
- 重構目標 (提升可維護性/消除 code smell/架構改進/技術棧現代化)
- 風險承受度 (保守/平衡/激進)
- 🆕 **是否涉及資料庫遷移？** (是/否，若是請指明來源與目標 DB)
- 🆕 **是否涉及新平台擴展？** (無/Web/Android/iOS/macOS Desktop/跨平台行動端/多平台組合)
- 🆕 **是否為生產系統？** (是/否 — 影響並行運行策略)
- 🆕 **是否涉及硬體整合？** (無/掃碼槍/條碼掃描(手機相機)/NFC/藍牙印表機/其他)
- 🆕 **是否涉及支付/個資/合規需求？** (無/支付處理(PCI-DSS)/個人資料(GDPR)/醫療資料(HIPAA)/其他)

> **⚠️ 重構類型判斷指引**：
> - 若「重構類型 = 技術棧遷移」且「範圍 = 全技術棧」，則自動升級為 **X-Large 規模**
> - X-Large 規模將額外載入 SA、BA、PM/PO、DevOps Agent
> - 若涉及資料庫遷移，將額外觸發「資料庫遷移專項流程」（Skill: `/database-migration`）
> - 若涉及新平台擴展，將載入對應的 Mobile/Desktop Architect Agent
> - 若涉及硬體整合（掃碼/NFC 等），將載入 Integration-Specialist Agent
> - 若涉及支付/個資/合規需求，將額外觸發 `/compliance-audit` 和載入 Compliance-Officer Agent
>
> **⚠️ 平台類型區分**：
> - **Android/iOS** = 行動端 → 載入 `sd-mobile-architect`，觸發 `/mobile-development`
> - **macOS Desktop** = 桌面端 → 載入 `sd-architect`（主導）+ `sd-mobile-architect`（Apple 生態經驗）
> - **跨平台行動端** = React Native/Flutter → 載入 `sd-mobile-architect`
> - **多平台組合**（如 Android + macOS）= 需同時載入行動端與桌面端 Architect

#### 步驟 1.3：確認載入結果
期待回應（以技術棧遷移為例）：
```
✅ 識別情境：Refactoring (技術棧遷移)
✅ 識別重構類型：技術棧遷移 (X-Large)
✅ 載入 Primary Agents：SD-Architect, Code-Analyzer
✅ 記錄 Supporting Agents：SA, BA, PM/PO, Dev-Senior, QA, Dev, DevOps
✅ 記錄 Optional Agents：Mobile-Architect, Integration-Specialist, Security-Engineer (按需載入)
✅ 載入 Workflows：requirements-extraction, change-management, user-story-design,
   api-specification, consistency-check, interaction-analysis, validation-documentation, sprint-execution
✅ 偵測到資料庫遷移需求：Oracle → PostgreSQL
✅ 偵測到新平台需求：Android, macOS
✅ 推薦策略：Strangler Pattern (生產系統漸進遷移)
準備開始代碼品質分析...
```

#### 步驟 1.4：啟動確認點 (5 分鐘)

> 🔴 **人機協作點：情境與範圍確認**
>
> **AI 提供**：
> - 情境識別結果（重構類型、規模評估）
> - Agent 載入清單（Primary/Supporting/Optional）
> - 建議 Workflow 和策略方向
>
> **需人工確認**：
> - 情境識別是否正確？
> - 重構範圍是否合理？
> - Agent 配置是否需要調整？
> - 是否需要搭配其他情境（Migration/Brownfield）？

---

### 階段 2：代碼品質深度分析 (1-1.5 小時)

#### 步驟 2.1：提供代碼資訊
```
執行指令：
「開始代碼品質分析，目標是：
- 代碼庫路徑：[路徑]
- 重構範圍：[具體模組/功能]
- 主要問題：[已知的痛點]
- 重構目標：[期望達成的目標]」
```

#### 步驟 2.2：自動代碼掃描與分析 (Code-Analyzer Agent)

**代碼異味檢測 (Code Smells)**：
- **重複代碼** (Duplicated Code)
- **過長方法** (Long Method) - 超過 50 行
- **過大類別** (Large Class) - 職責過多
- **過長參數列** (Long Parameter List) - 超過 3-4 個
- **發散式變化** (Divergent Change) - 一個類因多種原因修改
- **霰彈式修改** (Shotgun Surgery) - 一個變更影響多處
- **特性依戀** (Feature Envy) - 方法過度依賴其他類
- **資料泥團** (Data Clumps) - 相同資料總是一起出現
- **基本型別偏執** (Primitive Obsession) - 過度使用基本型別
- **條件複雜度** (Complex Conditional) - 深層嵌套 if/switch

**架構問題檢測**：
- 循環依賴 (Circular Dependencies)
- 緊耦合 (Tight Coupling)
- 違反單一職責原則 (SRP)
- 違反開放封閉原則 (OCP)
- 違反依賴倒置原則 (DIP)
- 上帝物件 (God Object)
- 不當親密 (Inappropriate Intimacy)

**可測試性分析**：
- 難以測試的代碼區域
- 缺少依賴注入
- 硬編碼依賴
- 靜態方法過度使用
- 全域狀態依賴

**技術債量化**：
- 代碼複雜度 (Cyclomatic Complexity)
- 認知複雜度 (Cognitive Complexity)
- 維護指數 (Maintainability Index)
- 技術債時間估算 (SQALE Rating)

**工具選擇建議** (商業版 vs 免費/開源替代方案):

| 分析類型 | 商業工具 | 免費/開源替代方案 | 建議 |
|---------|---------|-----------------|------|
| **代碼品質綜合分析** | SonarQube Enterprise | SonarQube Community Edition<br>SonarLint (IDE 外掛免費) | 小團隊用 Community 版即可 |
| **靜態代碼分析** | Checkmarx, Fortify | ESLint + Plugins (JS/TS)<br>Pylint/Flake8 (Python)<br>PMD/Checkstyle (Java) | 免費工具足以應對大多數情況 |
| **複雜度分析** | CodeClimate | Radon (Python)<br>complexity-report (JS)<br>lizard (多語言) | 開源工具精準度高 |
| **測試覆蓋率** | - | Jest/Vitest (JS/TS 內建)<br>pytest-cov (Python)<br>JaCoCo (Java) | 測試框架通常內建覆蓋率 |
| **依賴分析** | - | Madge (JS)<br>dependency-cruiser (JS)<br>pydeps (Python) | 免費工具即可 |

**⚠️ 無工具團隊的應對策略**:
1. 使用 IDE 內建的代碼檢查功能 (VS Code / IntelliJ 都有基礎檢查)
2. 手動代碼審查 (Code Review) + 檢查清單
3. 使用 Git hooks 整合免費工具 (pre-commit hooks)
4. 逐步引入工具，從最容易的開始 (如 ESLint)

#### 步驟 2.3：效能與資源分析 (如適用)

**效能熱點**：
- CPU 密集區域
- 記憶體洩漏風險
- N+1 查詢問題
- 不必要的資源載入
- 阻塞式 I/O

**資源使用**：
- 記憶體使用模式
- 資料庫連線管理
- 檔案處理效率
- 快取使用狀況

#### 步驟 2.4：品質分析確認點 (20 分鐘)

> 🔴 **人機協作點：品質分析確認**
>
> **AI 提供**：
> - 品質儀表板（整體評分 A-F、Code Smell 統計、技術債總量、測試覆蓋率）
> - 問題優先級清單（Critical/High/Medium/Low 分類）
> - 熱點模組識別（Top 10 檔案/模組、變更頻率 vs 品質交叉分析）
> - 視覺化呈現（依賴關係圖、複雜度熱力圖、技術債分佈圖）
>
> **需人工確認**：
> - ✅ 品質評估是否準確
> - ✅ 問題優先級是否合理
> - ✅ 是否有遺漏的關鍵問題
> - ✅ 補充任何背景資訊（為何某些代碼如此設計）
>
> **產出文件**：
> - 代碼品質分析報告 (Code Quality Analysis Report)
> - Code Smell 清單 (Code Smell Inventory)
> - 技術債評估報告 (Technical Debt Assessment)
> - 重構熱點地圖 (Refactoring Hotspot Map)

#### 步驟 2.5：🆕 技術棧遷移專項分析 (僅「技術棧遷移」類型適用)

> **⚠️ 觸發條件**：當步驟 1.2 識別重構類型為「技術棧遷移」時，必須執行此步驟。

**2.5.1 技術棧相容性分析** (SA + SD + Code-Analyzer)

| 分析維度 | 分析內容 | 產出 |
|---------|---------|------|
| **前端框架映射** | 舊框架元件 → 新框架對應方案<br>例: Vue SFC → React JSX, Pinia → Zustand/Redux, Vue Router → Next.js App Router<br>**⚠️ CSR→SSR 遷移注意**：Vue3+Vite 為 CSR（客戶端渲染），若遷移至 Next.js 需評估 SSR 策略差異：<br>• **Auth 策略**：CSR 的 localStorage JWT → SSR 的 httpOnly Cookie（Server Components 無法存取 localStorage）<br>• **資料取得模式**：Client-side fetch → Server-side RSC fetch / React Query<br>• **Session 管理**：前端 SPA token 管理 → next-auth / 自建 server-side session<br>• **SEO 影響**：SSR 可提升 SEO，但需注意 hydration 問題 | 前端遷移映射表 |
| **後端框架映射** | 舊 API → 新框架對應實作<br>例: Flask route → Spring @RestController, Python decorator → Spring AOP<br>**⚠️ 動態→靜態型別遷移**：Python 鬆散型別 → Spring Boot 強型別 DTO/Entity，需逐一明確定義所有 Request/Response 物件型別 | 後端遷移映射表 |
| **第三方依賴映射** | 舊生態套件 → 新生態替代方案<br>例: Vuetify → MUI, Axios → Spring RestTemplate/WebClient | 依賴替代方案表 |
| **業務邏輯提取** | 從舊代碼中系統性提取業務規則<br>每個模組逐一列出所有業務計算邏輯、驗證規則、狀態機 | 業務邏輯清單 |

**2.5.2 資料庫遷移分析** (SD + Dev-Senior) — 僅涉及 DB 遷移時

| 分析維度 | 分析內容 | 產出 |
|---------|---------|------|
| **Schema 轉換** | 資料型別映射（如 Oracle NUMBER → PostgreSQL NUMERIC）<br>約束轉換、索引轉換、分區策略轉換 | Schema 轉換映射表 |
| **SQL 語法差異** | Oracle 特有語法 → PostgreSQL 等價語法<br>例: DECODE→CASE, NVL→COALESCE, ROWNUM→LIMIT, CONNECT BY→WITH RECURSIVE, SYSDATE→NOW() | SQL 轉換對照表 |
| **Stored Procedure 轉換** | PL/SQL → 應用層 Java Service 或 PL/pgSQL<br>遊標→Stream/Iterator, 例外處理→try-catch, 套件→Service Class | SP 轉換計畫 |
| **資料遷移策略** | ETL 流程設計、增量同步方案<br>遷移工具選擇: ora2pg, pgloader, AWS DMS, 自建 ETL | 資料遷移計畫 |
| **功能替換映射** | Oracle 特有功能 → 替代方案<br>DBMS_JOB→@Scheduled/Quartz, UTL_FILE→Java NIO, DBMS_OUTPUT→SLF4J, Oracle Sequence→PostgreSQL SERIAL | 功能替換映射表 |

> **🔴 資料庫遷移 Skill 與 Workflow 觸發指引**：
>
> 當步驟 2.5.2 確認涉及資料庫遷移時，**必須**按以下順序觸發對應 Skill：
>
> | 執行順序 | Skill | 用途 | 階段 |
> |---------|-------|------|------|
> | 1 | `/database-migration Oracle PostgreSQL` | 資料庫遷移規劃：Schema 轉換、SQL 語法改寫、SP 遷移、資料搬移驗證 | 階段 2-3 |
> | 2 | `/integration-database` | 新 DB 整合設定：Spring Data JPA / Prisma ORM 配置、連線池、交易管理 | 階段 4-5 |
>
> **兩個 Skill 的區別**：
> - `/database-migration`：專注於「舊 DB → 新 DB」的遷移過程（Schema、資料、SP）
> - `/integration-database`：專注於「新系統如何使用新 DB」的整合設定（ORM、連線、交易）

**2.5.3 平台擴展分析** (SD-Mobile-Architect / SD-Architect) — 僅涉及新平台時

| 分析維度 | 分析內容 | 產出 |
|---------|---------|------|
| **行動端架構** | 共用 API 設計、離線支援策略、推播通知 | 行動端架構設計 |
| **硬體整合** | 掃碼功能(Camera API/Barcode SDK)、藍牙連線、NFC | 硬體整合方案 |
| **跨平台策略** | 原生 vs 跨平台(React Native/Flutter/KMP)決策 | 平台選型報告 |
| **🆕 macOS Desktop 特性** | 視窗管理(多視窗/分割視圖)、選單列整合、Dock 互動、<br>鍵盤快捷鍵、Touch Bar(如適用)、檔案系統存取、<br>Catalyst vs 原生 SwiftUI vs Electron 決策 | macOS 適配方案 |

> **⚠️ macOS 平台注意事項**：
> - macOS 雖為 Apple 生態，但屬於 **桌面平台**，與行動端 (iOS/Android) 的 UX 模式不同
> - macOS 應用需考慮：多視窗管理、拖放操作、右鍵選單、鍵盤導航、大螢幕佈局
> - 若同時涉及 Android + macOS，建議分別由 SD-Mobile-Architect（行動端）和 SD-Architect（桌面端）負責
> - 掃碼功能在 macOS 上可透過外接掃碼槍（USB/藍牙 HID）或 Continuity Camera（iPhone 充當掃描器）實現

**2.5.4 多業務域融合系統 DDD Bounded Context 分析** — 僅涉及多個業務域整合時

> **⚠️ 觸發條件**：系統融合 2 個以上不同業務領域時（如電商+民宿+CMS+知識管理），必須執行此步驟。
> 否則技術棧遷移後仍會保留原本業務邊界混亂的問題。

| 分析步驟 | 分析內容 | 產出 |
|---------|---------|------|
| **業務域識別** | 識別系統中各個 Bounded Context（如：OrderContext, PropertyContext, ContentContext, KnowledgeContext）<br>每個 Context 有獨立的業務語言（Ubiquitous Language）和邊界 | Bounded Context 地圖 |
| **Context 邊界劃定** | 確認每個 Context 的資料歸屬（哪些 Entity 屬於哪個 Context）<br>識別跨 Context 共享的資料（如：User 在所有 Context 共用）<br>設計 Context Mapping（Shared Kernel / Anti-Corruption Layer / Published Language） | Context Mapping 圖 |
| **共用模組識別** | 找出跨域共用的模組：認證(Auth)、用戶(User)、通知(Notification)、檔案(File)<br>設計共用模組的 API 合約（避免直接 DB 共享） | 共用模組清單與 API 合約 |
| **遷移優先順序** | 按業務重要性和依賴關係排序各 Context 的遷移順序<br>建議：先遷移依賴少的邊緣 Context，最後遷移核心 Context | 分層遷移計畫 |

> **💡 常見多業務域組合的 Context 建議**：
> - **電商**：OrderContext, ProductContext, PaymentContext, CartContext
> - **民宿管理**：PropertyContext, BookingContext, PricingContext, HousekeepingContext
> - **內容發布**：ContentContext, PublishContext, MediaContext
> - **知識管理**：KnowledgeContext, CategoryContext, SearchContext
> - **跨域共用**：UserContext（認證/授權）, NotificationContext, FileContext

> 🔴 **人機協作點：技術棧遷移分析確認**
>
> **需人工確認**：
> - ✅ 前端/後端/DB 映射表是否完整準確
> - ✅ 業務邏輯提取是否有遺漏
> - ✅ 資料庫遷移策略是否可行
> - ✅ 功能替換方案是否合適
> - ✅ **（多業務域時）** Bounded Context 劃分是否符合實際業務邊界
> - ✅ **（多業務域時）** 共用模組識別是否完整，API 合約是否合理
>
> **產出文件**：
> - 技術棧遷移映射報告 (Tech Stack Migration Mapping)
> - 資料庫遷移計畫 (Database Migration Plan)
> - 業務邏輯清單 (Business Logic Inventory)
> - **（多業務域時）** Bounded Context 地圖與 Context Mapping 圖

---

**📊 重構進度追蹤儀表板 (Refactoring Progress Dashboard)**：

> 持續追蹤重構進度，確保目標可視化

```markdown
## 重構進度儀表板模板

### 📈 整體進度
| 指標 | 起始值 | 當前值 | 目標值 | 進度 |
|------|--------|--------|--------|------|
| 循環複雜度 (Avg) | 25 | 18 | 10 | ████████░░ 70% |
| 測試覆蓋率 | 35% | 55% | 80% | █████░░░░░ 44% |
| Code Smells 數量 | 150 | 80 | 30 | █████░░░░░ 58% |
| 技術債 (天) | 45 | 28 | 10 | █████░░░░░ 49% |

### 📋 任務進度
| 狀態 | 數量 | 百分比 |
|------|------|--------|
| ✅ 已完成 | 12 | 40% |
| 🔄 進行中 | 5 | 17% |
| ⏳ 待處理 | 13 | 43% |
| **總計** | **30** | 100% |

### 🎯 里程碑追蹤
- [x] M1: 核心模組重構 (Week 1-2)
- [x] M2: API 層重構 (Week 3)
- [ ] M3: 資料存取層重構 (Week 4-5) ← 當前
- [ ] M4: 整合測試補齊 (Week 6)

### 📊 每週變化趨勢
Week 1: ████████░░ 15%
Week 2: █████████░ 35%
Week 3: ██████████ 55%
Week 4: ███████████ 70% (當前)
```

**進度追蹤工具建議**：
| 工具 | 免費方案 | 特點 |
|------|---------|------|
| **GitHub Projects** | ✅ 完全免費 | 與 Issue/PR 整合 |
| **Linear** | ✅ 免費 (小團隊) | UI 現代、速度快 |
| **Notion** | ✅ 免費 (個人) | 靈活自訂 |
| **SonarQube** | ✅ Community | 自動追蹤品質指標 |

---

### 階段 3：重構目標設定與範圍界定 (30-40 分鐘)

#### 步驟 3.1：觸發目標設定流程
```
執行指令：
「基於品質分析結果，請協助設定重構目標和範圍」
```

#### 步驟 3.2：目標設定協作 (SD + Dev-Senior)

**SMART 目標範例**：
- ✅ 「將 UserService 類別的循環複雜度從 45 降低到 15 以下」
- ✅ 「提升核心業務邏輯測試覆蓋率從 45% 到 80%」
- ✅ 「消除 authentication 模組的 3 個循環依賴」
- ✅ 「將 API 響應時間 P95 從 800ms 降低到 300ms」
- ❌ 「讓代碼更好」（過於模糊）

**目標分類**：

**品質目標 (Quality Goals)**：
- 降低複雜度
- 消除重複代碼
- 改善命名和可讀性
- 增強錯誤處理

**架構目標 (Architecture Goals)**：
- 模組解耦
- 改善分層架構
- 引入設計模式
- 依賴注入改造

**可測試性目標 (Testability Goals)**：
- 提升測試覆蓋率
- 改善測試性
- 加速測試執行
- 減少測試脆弱性

**效能目標 (Performance Goals)**：
- 降低響應時間
- 減少記憶體使用
- 優化資料庫查詢
- 改善並發處理

#### 步驟 3.3：範圍界定與階段劃分

**範圍界定原則**：
- 避免「Big Bang」重構，分階段進行
- 每個階段獨立可部署
- 高價值優先（影響大、風險可控）
- 由外而內（先 API/Interface，後實作）

**階段劃分範例**：
```
Phase 1 (1-2 週)：測試補強
- 補充關鍵路徑測試
- 建立測試保護網
- 重構前置條件達成

Phase 2 (1-2 週)：模組解耦
- 消除循環依賴
- 抽取介面
- 引入依賴注入

Phase 3 (1 週)：代碼清理
- 消除重複代碼
- 簡化複雜方法
- 改善命名

Phase 4 (1 週)：架構優化
- 引入設計模式
- 優化資料層
- 改善錯誤處理
```

> **⚠️ 重構規模評估方法 (Refactoring Scale Assessment)**
>
> 根據影響範圍和複雜度,將重構分為四個規模等級:
>
> | 規模 | 影響範圍 | 複雜度 | 建議時程 | 建議分 Phase |
> |------|---------|--------|---------|-------------|
> | **Small** | 單一模組/類別 | 低 (無外部依賴變動) | 2-5 天 | 單一 Phase |
> | **Medium** | 2-5 個模組 | 中 (部分 API 變動) | 1-3 週 | 2-3 個 Phases |
> | **Large** | 整個子系統 | 高 (跨層級重構) | 1-2 月 | 4-6 個 Phases |
> | **X-Large** | 多個子系統/架構級 | 極高 (全系統影響) | 2-6 月 | ≥6 個 Phases |
>
> **Phase 拆分原則**:
> - Small: 無需拆分,一次性完成
> - Medium: 按模組拆分 (模組 A → 模組 B → 整合)
> - Large: 按層級拆分 (測試補強 → API 層 → 業務邏輯層 → 資料層)
> - X-Large: 按子系統 + 層級拆分 (子系統 A 各層 → 子系統 B 各層 → 整合)
>
> **範例 - Medium 規模重構**:
> ```
> 目標: 重構訂單處理模組 (涉及 Order、Payment、Inventory 三個模組)
>
> Phase 1 (1 週): 測試補強
> - 補充 Order 模組測試 (目標: 80% 覆蓋率)
> - 補充 Payment、Inventory 整合測試
>
> Phase 2 (1 週): Order 模組重構
> - 抽取 OrderService 介面
> - 消除 Order 內部循環依賴
> - 部署並監控 1-2 天
>
> Phase 3 (1 週): Payment、Inventory 重構與整合
> - 對齊三個模組的介面設計
> - 引入事件驅動通訊 (解耦)
> - 全面測試與部署
> ```
>
> **範例 - Large 規模重構**:
> ```
> 目標: 電商平台從單體架構重構為微服務
>
> Phase 1 (2 週): 測試與監控基礎
> Phase 2 (3 週): API Gateway 與服務拆分準備
> Phase 3 (4 週): 用戶服務拆分
> Phase 4 (4 週): 商品服務拆分
> Phase 5 (4 週): 訂單服務拆分
> Phase 6 (2 週): 整合測試與效能優化
> ```

```

#### 步驟 3.4：目標與範圍確認點 (15 分鐘)

> 🔴 **人機協作點：目標與範圍確認**
>
> **AI 提供**：
> - 重構目標清單（SMART 格式的具體目標）
> - 階段規劃（分階段執行計畫和時間線）
> - 成功標準（可量化的驗收指標）
> - 風險評估（各階段的風險和緩解措施，含風險評分矩陣）
> - 投資回報分析（預估的重構成本 vs 長期效益）
>
> **需人工確認**：
> - ✅ 目標是否符合團隊期待
> - ✅ 階段劃分是否合理
> - ✅ 時間預算是否可行
> - ✅ 優先級排序是否正確
>
> **產出文件**：
> - 重構目標文件 (Refactoring Goals)
> - 階段規劃 (Phase Plan)
> - 成功標準 (Success Criteria)
> - ROI 分析 (Return on Investment Analysis)

**重構風險評分矩陣 (Risk Scoring Matrix)**:

```
風險分數 = 影響範圍 (1-5) × 技術複雜度 (1-5)
```

| 分數範圍 | 風險等級 | 建議策略 |
|---------|---------|---------|
| 20-25 | 🔴 Critical | 分多階段 (≥4 階段)、**關鍵路徑 80%** 測試覆蓋、強制 Peer Review、準備回滾方案 |
| 15-19 | 🟡 High | 分 2-3 階段、≥80% 測試覆蓋、Code Review 必須、監控關鍵指標 |
| 8-14 | 🟢 Medium | 標準流程、≥60% 測試覆蓋、Code Review 建議 |
| 1-7 | ⚪ Low | 快速重構、基礎測試即可 |

**影響範圍評分** (Scope Impact: 1-5):
- 1 = 單一函式/方法
- 2 = 單一類別/模組
- 3 = 單一套件/命名空間
- 4 = 多個相關模組
- 5 = 跨系統影響 (API 變更、資料庫 Schema)

**技術複雜度評分** (Technical Complexity: 1-5):
- 1 = 簡單重命名、格式化
- 2 = Extract Method、Inline Variable
- 3 = 類別重組、模組拆分
- 4 = 設計模式引入、依賴注入改造
- 5 = 架構重構、多執行緒改造

---

### 階段 4：重構策略制定 (1-1.5 小時)

#### 步驟 4.1：觸發策略制定
```
執行指令：
「請針對確認的目標，制定詳細的重構策略」
```

#### 步驟 4.2：策略模式選擇 (SD + Dev-Senior)

**策略 A：絞殺者模式 (Strangler Pattern)**
- **適用**：大型 Legacy 系統逐步替換
- **方法**：建立新系統，逐步遷移功能，最終淘汰舊系統
- **優點**：風險低、可隨時停止
- **缺點**：耗時長、過渡期維護兩套系統

**策略 B：分支抽象 (Branch by Abstraction)**
- **適用**：核心模組的架構改造
- **方法**：抽取介面 → 建立新實作 → 切換 → 移除舊實作
- **優點**：持續交付、風險可控
- **缺點**：需要良好的介面設計

**策略 C：平行運行 (Parallel Run)**
- **適用**：關鍵業務邏輯重構
- **方法**：新舊實作並行，對比結果，驗證正確性
- **優點**：高度安全、易於驗證
- **缺點**：效能開銷、維護複雜

**策略 D：特性切換 (Feature Toggle)**
- **適用**：需要動態開關的重構
- **方法**：使用 Feature Flag 控制新舊實作切換
- **優點**：可即時回滾、A/B Testing
- **缺點**：程式碼複雜度增加

**策略 E：漸進式重構 (Incremental Refactoring)**
- **適用**：日常持續改進
- **方法**：每次改動時順手重構周邊代碼
- **優點**：無額外時間成本、持續改善
- **缺點**：進度緩慢、需要紀律

**策略 F：🆕 技術棧遷移專用 — 分層漸進遷移 (Layered Progressive Migration)**
- **適用**：全技術棧替換（前端+後端+DB 同時遷移）
- **方法**：
  1. DB 層先行：Schema 轉換 + 資料遷移 + 雙寫驗證
  2. 後端層次之：新 API 實作 + 舊 API 對比 + API Gateway 路由
  3. 前端層最後：逐模組重寫 + 功能對等驗證
  4. 新平台：後端 API 穩定後啟動行動端開發
- **優點**：風險逐層隔離、每層獨立驗證
- **缺點**：週期長、需要嚴格的介面契約管理
- **並行運行策略**：
  - API Gateway (如 Kong/Nginx) 路由新舊後端
  - DB 雙寫 (Dual-Write) 或 CDC (Change Data Capture) 同步
  - Feature Flag 控制前端新舊版本切換

#### 步驟 4.2.1：🆕 技術棧遷移執行子流程（僅「技術棧遷移」類型適用）

> **⚠️ 觸發條件**：當步驟 1.2 識別重構類型為「技術棧遷移」時，必須制定以下分層執行計畫。

**分層漸進遷移執行順序**：

```
Phase A: 基礎設施準備 (1-2 週)
├─ 新 CI/CD Pipeline 建立 → /devops-github-actions
├─ 開發/測試/預生產環境建置
├─ API Gateway 設定（新舊系統路由）
└─ 監控告警設定

Phase B: 資料庫層遷移 (2-4 週)
├─ Schema 轉換與驗證 → /database-migration
├─ Stored Procedure → 應用層 Service 遷移
├─ 資料遷移 (ETL) + 資料驗證
├─ 雙寫機制建立（並行期間）
└─ 🔴 資料一致性驗證確認點

Phase C: 後端層遷移 (3-6 週)
├─ Spring Boot 專案骨架建立 → /integration-database
├─ 模組逐一遷移（按業務優先級）
│   ├─ 每個模組：Python API → Spring Boot Controller/Service
│   ├─ API 對比測試（新舊 API 同輸入→同輸出）
│   └─ 遵循 開發-編譯-測試循環
├─ API Gateway 逐步切換路由
└─ 🔴 新舊 API 功能等價驗證確認點

Phase D: 前端層遷移 (3-5 週)
├─ Next.js 專案骨架建立
├─ 元件遷移對照：
│   ├─ Vue SFC (.vue) → React Component (.tsx)
│   ├─ Pinia → Zustand/Redux Toolkit
│   ├─ Vue Router → Next.js App Router
│   ├─ Vuetify/Element Plus → MUI/Ant Design
│   └─ Composables (useXxx) → Custom Hooks (useXxx)
├─ 逐頁面/模組遷移，Feature Flag 控制切換
└─ 🔴 UI 功能等價驗證確認點

Phase E: 新平台開發 (並行於 Phase C-D)
├─ Android 應用 → /mobile-development Android
├─ macOS Desktop 應用 → /mobile-development macOS
├─ 共用 API 設計、掃碼整合
└─ 🔴 多平台功能驗證確認點

Phase F: 切換與收尾 (1-2 週)
├─ 全面切換至新系統
├─ 舊系統降級為唯讀備份
├─ 效能對比驗證 → /performance-optimization
└─ 文檔更新與知識沉澱
```

**並行運行期間的關鍵機制**：

| 機制 | 工具/方案 | 目的 |
|------|---------|------|
| API 路由 | Kong / Nginx / Spring Cloud Gateway | 控制請求流向新/舊後端 |
| DB 雙寫 | CDC (Debezium) / 應用層雙寫 | 確保資料同步到新舊 DB |
| Feature Flag | LaunchDarkly / Unleash / 自建 | 控制前端新舊版本顯示 |
| 對比驗證 | Diffy / Pact / 自建比對腳本 | 驗證新舊系統行為一致 |

#### 步驟 4.3：重構技術與模式

**常用重構技術**：

**提取 (Extract)**：
- Extract Method - 提取方法
- Extract Class - 提取類別
- Extract Interface - 提取介面
- Extract Variable - 提取變數

**內聯 (Inline)**：
- Inline Method - 內聯方法（消除不必要的間接層）
- Inline Variable - 內聯變數

**移動 (Move)**：
- Move Method - 移動方法
- Move Field - 移動欄位
- Move Class - 移動類別

**重新組織 (Reorganize)**：
- Rename - 重新命名
- Change Method Signature - 改變方法簽名
- Pull Up / Push Down - 上拉/下推（繼承層次調整）

**簡化 (Simplify)**：
- Replace Conditional with Polymorphism - 以多型替換條件
- Decompose Conditional - 分解條件
- Replace Magic Number with Constant - 以常數替換魔術數字
- Replace Type Code with State/Strategy - 以狀態/策略模式替換型別碼

**依賴處理 (Dependency)**：
- Introduce Parameter Object - 引入參數物件
- Preserve Whole Object - 保持物件完整
- Replace Parameter with Method - 以方法替換參數
- Introduce Dependency Injection - 引入依賴注入

#### 步驟 4.4：測試策略

**測試金字塔維持**：
```
       /\       E2E Tests (10%)
      /  \
     /----\     Integration Tests (30%)
    /------\
   /--------\   Unit Tests (60%)
```

**重構中的測試策略**：
1. **重構前**：補充測試保護網（Golden Master Testing）
2. **重構中**：保持綠燈（測試持續通過）
3. **重構後**：重構測試（改善測試代碼）

**特殊測試技術**：
- **Characterization Tests**：為 Legacy 代碼建立特徵測試
- **Approval Tests**：快照測試，適合複雜輸出
- **Mutation Testing**：驗證測試品質
- **Contract Testing**：確保介面相容性

#### 步驟 4.5：重構策略確認點 (20 分鐘)

> 🔴 **人機協作點：重構策略確認**
>
> **AI 提供**：
> - 推薦策略（針對各階段的重構策略選擇和理由）
> - 重構技術清單（具體要使用的重構技術）
> - 測試策略（測試補強計畫和執行策略）
> - 風險緩解措施（如何降低重構風險）
> - 程式碼範例（關鍵重構的前後對比範例）
>
> **需人工確認**：
> - ✅ 策略選擇是否合適
> - ✅ 技術手法是否正確
> - ✅ 測試策略是否充分
> - ✅ 風險是否可接受
>
> **產出文件**：
> - 重構策略文件 (Refactoring Strategy)
> - 技術手法指南 (Refactoring Techniques Guide)
> - 測試策略 (Testing Strategy)
> - 程式碼範例集 (Code Examples)

---

### 階段 5：逐步重構實作指引 (40-60 分鐘)

#### 步驟 5.1：觸發實作規劃
```
執行指令：
「請制定詳細的重構實作步驟和檢查清單」
```

#### 步驟 5.2：重構步驟拆解 (Dev-Senior)

**Phase 1 範例：測試補強** (詳細步驟)

```
步驟 1.1：識別測試缺口 (1-2 天)
[ ] 執行測試覆蓋率工具
[ ] 識別未覆蓋的關鍵路徑
[ ] 優先級排序（業務價值 x 風險）

步驟 1.2：補充單元測試 (2-3 天)
[ ] UserService 類別測試（目標 80%+）
[ ] AuthenticationManager 測試
[ ] PaymentProcessor 測試
[ ] 驗證測試通過

步驟 1.3：補充整合測試 (1-2 天)
[ ] API 端點測試
[ ] 資料庫整合測試
[ ] 第三方服務整合測試

步驟 1.4：建立 Golden Master (1 天)
[ ] 記錄現有系統行為
[ ] 建立特徵測試
[ ] 驗證測試可重現
```

**Phase 2 範例：模組解耦** (詳細步驟)

```
步驟 2.1：抽取介面 (2-3 天)
[ ] 識別需要解耦的依賴
[ ] 定義介面 (IUserRepository, IEmailService)
[ ] 更新相依類別使用介面
[ ] 驗證測試通過

步驟 2.2：引入依賴注入 (2-3 天)
[ ] 選擇 DI 框架（或手動 DI）
[ ] 配置依賴注入容器
[ ] 重構類別建構子
[ ] 更新測試使用 Mock
[ ] 驗證功能正常

步驟 2.3：消除循環依賴 (1-2 天)
[ ] 分析循環依賴鏈
[ ] 重新組織模組邊界
[ ] 引入中介層（如需要）
[ ] 驗證依賴圖無循環
```

#### 步驟 5.3：每個重構的安全檢查清單

**重構前檢查**：
- [ ] 相關測試已補充並通過
- [ ] 已建立 feature branch
- [ ] 已通知團隊成員（避免衝突）
- [ ] 已備份資料（如涉及資料遷移）

**重構中檢查**：
- [ ] 小步前進（每次 commit 可編譯、測試通過）
- [ ] 頻繁執行測試
- [ ] 保持功能不變（行為等價）
- [ ] 及時 commit（每完成一個重構技術）

**重構後檢查**：
- [ ] 所有測試通過（單元/整合/E2E）
- [ ] 代碼審查通過
- [ ] 效能無退化（benchmark 對比）
- [ ] 文檔已更新
- [ ] 程式碼品質指標改善（SonarQube 等）

> **⚠️ Git 回滾策略 (Rollback Strategies)**
>
> 當重構出現問題時,根據情況選擇合適的回滾策略:
>
> **策略 1: Revert Commit (推薦用於已 Push 的變更)**
> ```bash
> # 撤銷最近一次 commit (保留歷史記錄)
> git revert HEAD
> 
> # 撤銷特定 commit
> git revert <commit-hash>
> 
> # 撤銷多個 commits
> git revert <oldest-commit>..<newest-commit>
> ```
> **適用**: 已 push 到共享分支,需要保留歷史記錄
> **優點**: 安全,不改寫歷史
> **缺點**: 會產生新的 revert commit
>
> **策略 2: Reset (用於本地未 Push 的變更)**
> ```bash
> # Soft reset: 保留變更在暫存區
> git reset --soft HEAD~1
> 
> # Mixed reset: 保留變更在工作區 (預設)
> git reset HEAD~1
> 
> # Hard reset: 完全丟棄變更 ⚠️ 危險!
> git reset --hard HEAD~1
> ```
> **適用**: 本地開發,尚未 push
> **優點**: 乾淨,不產生額外 commit
> **缺點**: 改寫歷史,不適合共享分支
>
> **策略 3: 分支切換與保留 (用於大規模重構失敗)**
> ```bash
> # 保留當前重構工作在新分支
> git checkout -b refactor-backup
> git push origin refactor-backup
> 
> # 切回主分支,從乾淨狀態重新開始
> git checkout main
> git pull origin main
> ```
> **適用**: 重構方向錯誤,但想保留已做的探索
> **優點**: 不丟失工作成果,可隨時參考
>
> **策略 4: Cherry-pick (用於部分成功的重構)**
> ```bash
> # 從失敗的重構中挑選成功的 commits
> git checkout main
> git cherry-pick <good-commit-1> <good-commit-2>
> ```
> **適用**: 部分重構成功,部分失敗
> **優點**: 保留有價值的變更
>
> **回滾決策樹**:
> ```
> 重構出現問題
> │
> ├─ 已 push 到共享分支?
> │  ├─ 是 → 使用 git revert (策略 1)
> │  └─ 否 → 繼續判斷
> │
> ├─ 是否要保留當前工作?
> │  ├─ 是 → 使用分支備份 (策略 3)
> │  └─ 否 → 繼續判斷
> │
> ├─ 部分工作是否可用?
> │  ├─ 是 → 使用 cherry-pick (策略 4)
> │  └─ 否 → 使用 git reset --hard (策略 2)
> ```
>
> **回滾後檢查清單**:
> - [ ] 執行完整測試套件確認系統正常
> - [ ] 檢查資料庫遷移是否需要回滾
> - [ ] 通知團隊成員回滾情況
> - [ ] 更新 issue/ticket 說明回滾原因
> - [ ] 安排事後檢討 (Retrospective),找出問題根因

- [ ] 程式碼品質指標改善（SonarQube 等）

#### 步驟 5.4：常見陷阱與避免方式

**陷阱 1：範圍蔓延**
- ❌ 「既然要重構，不如順便加個新功能」
- ✅ 重構就是重構，功能增強另開分支

**陷阱 2：過度重構**
- ❌ 追求完美，引入不必要的抽象層
- ✅ 遵循 YAGNI 原則（You Aren't Gonna Need It）

**陷阱 3：缺少測試保護**
- ❌ 「代碼簡單，不需要測試」
- ✅ 重構前必須有測試，否則先補測試

**陷阱 4：大爆炸式重構**
- ❌ 一次重構整個系統
- ✅ 分階段、小步快跑

**陷阱 5：忽視效能影響**
- ❌ 為了「優雅」犧牲效能
- ✅ 重構前後 benchmark 對比

#### 步驟 5.5：實作指引確認點 (15 分鐘)

> 🔴 **人機協作點：實作指引確認**
>
> **AI 提供**：
> - 詳細步驟清單（每個 Phase 的具體執行步驟）
> - 時間估算（每個步驟的預估工時）
> - 依賴關係（步驟間的先後順序）
> - 檢查清單（每個階段的驗證項目）
> - 程式碼範例（關鍵重構的實作範例）
>
> **需人工確認**：
> - ✅ 步驟拆解是否合理
> - ✅ 時間估算是否可行
> - ✅ 檢查清單是否完整
> - ✅ 是否有遺漏的風險
>
> **產出文件**：
> - 重構實作計畫 (Refactoring Implementation Plan)
> - 步驟檢查清單 (Step-by-Step Checklist)
> - 程式碼範例 (Code Examples - Before/After)
> - 陷阱避免指南 (Pitfall Avoidance Guide)

---

### 階段 6：驗證與品質確認 (30-40 分鐘)

#### 步驟 6.1：觸發驗證規劃
```
執行指令：
「請制定重構後的驗證計畫，確保品質改善」
```

#### 步驟 6.2：多維度驗證策略 (QA + Code-Analyzer)

**功能正確性驗證**：
- [ ] 所有單元測試通過
- [ ] 所有整合測試通過
- [ ] 所有 E2E 測試通過
- [ ] 手動 Smoke Testing
- [ ] UAT (User Acceptance Testing)

**效能驗證**：
- [ ] Benchmark 對比（重構前 vs 後）
- [ ] 響應時間無退化
- [ ] 記憶體使用無增加
- [ ] CPU 使用無增加
- [ ] 資料庫查詢效能

**品質指標驗證**：
- [ ] 循環複雜度降低（Cyclomatic Complexity）
- [ ] 認知複雜度降低（Cognitive Complexity）
- [ ] 維護性指標改善（Maintainability Index）
- [ ] 測試覆蓋率提升
- [ ] Code Smell 減少
- [ ] 技術債降低（SQALE Rating）

**架構品質驗證**：
- [ ] 依賴關係改善（無循環依賴）
- [ ] 模組耦合度降低
- [ ] 模組內聚度提升
- [ ] 設計原則遵循（SOLID）

**🆕 技術棧遷移驗證** (僅「技術棧遷移」類型適用)：

**資料庫遷移驗證**：
- [ ] Schema 轉換正確性（所有表/欄位/約束/索引對齊）
- [ ] 資料完整性（逐表行數比對、主鍵完整性）
- [ ] 資料準確性（關鍵金額欄位加總比對、抽樣明細比對）
- [ ] 外鍵參照完整性（所有外鍵約束均可通過）
- [ ] Sequence/自增值連續性
- [ ] Stored Procedure 邏輯等價驗證（同輸入→同輸出）
- [ ] 觸發器邏輯等價驗證

**跨系統一致性驗證**：
- [ ] 新舊系統 API 響應結果比對（同一請求→同一回傳）
- [ ] 新舊系統業務計算結果比對（進貨/銷貨/庫存結餘）
- [ ] 新舊系統報表數據比對
- [ ] 新舊系統並行運行無衝突

**行動端驗證** (涉及新平台時)：
- [ ] 多裝置測試（Android 各版本 / macOS 各版本）
- [ ] 掃碼功能測試（QR Code / Barcode 各格式）
- [ ] 離線/弱網路環境測試
- [ ] 資料同步正確性（離線→上線後同步）
- [ ] 裝置權限測試（相機/存儲/網路）

**部署驗證**：
- [ ] 藍綠部署/金絲雀發布流程驗證
- [ ] 回滾機制測試（新系統異常→自動回切舊系統）
- [ ] 資料庫雙寫一致性驗證
- [ ] 監控告警正常觸發

**推薦驗證工具**：
| 驗證類型 | 工具建議 |
|---------|---------|
| DB Schema 比對 | pgloader --dry-run, ora2pg --test |
| DB 資料比對 | 自建 SQL 比對腳本, Apache Griffin |
| API 比對 | Pact (Contract Testing), Diffy |
| E2E 測試 | Cypress (Web), Appium (Mobile) |
| 效能比對 | k6, JMeter, Lighthouse |

**🔄 微服務拆分指引** 🆕 (v0.01 主流程提升)

> **適用情境**：當重構目標涉及從單體架構拆分為微服務時，請參考以下指引。

**微服務拆分適用性評估**：

| 評估維度 | 建議拆分 | 不建議拆分 |
|---------|---------|-----------|
| **系統規模** | 代碼 > 50K LOC | 代碼 < 20K LOC |
| **團隊規模** | > 5 人獨立團隊 | < 3 人團隊 |
| **部署頻率需求** | 每日/每週部署 | 每月部署即可 |
| **擴展性需求** | 各模組擴展需求不同 | 統一擴展即可 |
| **技術棧多樣性** | 不同模組需要不同技術 | 統一技術棧 |

**微服務拆分決策流程**：
```
1. 識別業務邊界 (Domain-Driven Design)
   ↓
2. 評估耦合程度 (Database / API / Event)
   ↓
3. 選擇拆分模式 (Strangler Fig / Branch by Abstraction)
   ↓
4. 建立基礎設施 (API Gateway / Service Mesh / Message Queue)
   ↓
5. 漸進式遷移 (優先低風險、高價值模組)
   ↓
6. 驗證與切換
```

**拆分模式選擇**：

| 模式 | 優點 | 缺點 | 適用情境 |
|-----|------|------|---------|
| **Strangler Fig** | 風險低、漸進式 | 週期長 | ✅ 推薦首選 |
| **Branch by Abstraction** | 並行開發 | 複雜度高 | 團隊經驗豐富 |
| **Big Bang** | 一次到位 | 風險極高 | ⚠️ 不建議 |

> 📋 **詳細案例**：完整的微服務遷移案例請參考 [附錄 D：案例研究 - 架構遷移](#案例-2架構遷移-monolith--microservices)

**可維護性驗證**：
- [ ] 代碼可讀性改善（主觀評估）
- [ ] 新人上手時間縮短
- [ ] Bug 修復時間縮短
- [ ] 功能開發速度提升

#### 步驟 6.3：自動化驗證工具

**推薦工具清單**：

**JavaScript/TypeScript**：
- ESLint + Prettier（代碼風格）
- Jest（測試 + 覆蓋率）
- SonarQube（品質分析）
- Code Climate（可維護性）
- Lighthouse（前端效能）

**Python**：
- Pylint / Flake8（代碼品質）
- pytest + coverage（測試）
- Radon（複雜度分析）
- Bandit（安全檢查）

**Java**：
- Checkstyle（代碼風格）
- JUnit（測試）
- JaCoCo（覆蓋率）
- SonarQube（品質）
- PMD（代碼分析）

**C#**：
- StyleCop（代碼風格）
- xUnit / NUnit（測試）
- Coverlet（覆蓋率）
- NDepend（品質分析）

#### 步驟 6.4：驗證計畫確認點 (10 分鐘)

> 🔴 **人機協作點：驗證計畫確認**
>
> **AI 提供**：
> - 驗證檢查清單（完整的驗證項目）
> - 品質指標基準線（重構前的基準數據）
> - 目標指標（重構後應達到的目標）
> - 自動化驗證腳本（可執行的驗證指令）
> - 驗收標準（何時可認定重構成功）
>
> **需人工確認**：
> - ✅ 驗證計畫是否完整
> - ✅ 目標指標是否合理
> - ✅ 驗收標準是否清晰
>
> **產出文件**：
> - 驗證計畫 (Validation Plan)
> - 品質指標基準線 (Quality Baseline)
> - 驗收標準 (Acceptance Criteria)
> - 自動化驗證腳本 (Validation Scripts)

---

### 階段 7：前後對比與成果展示 (30 分鐘)

#### 步驟 7.1：觸發成果分析
```
執行指令：
「請生成重構前後對比報告」
```

#### 步驟 7.2：對比報告生成 (Code-Analyzer + Technical-Writer)

**量化指標對比**：

| 指標 | 重構前 | 重構後 | 改善幅度 |
|------|--------|--------|---------|
| 循環複雜度（平均） | 12.5 | 6.8 | ↓ 45.6% |
| 認知複雜度（平均） | 18.3 | 9.2 | ↓ 49.7% |
| 測試覆蓋率 | 45% | 82% | ↑ 82.2% |
| Code Smell 數量 | 127 | 23 | ↓ 81.9% |
| 技術債（天） | 15.2 天 | 3.8 天 | ↓ 75.0% |
| 類別平均行數 | 450 行 | 180 行 | ↓ 60.0% |
| 方法平均行數 | 35 行 | 12 行 | ↓ 65.7% |
| 依賴循環 | 5 個 | 0 個 | ✅ 消除 |

**程式碼範例對比**：

````markdown
#### 重構前 (Before)
```javascript
// UserService.js - 450 行，複雜度 45
class UserService {
  createUser(name, email, password, role, dept, manager, ...) {
    if (name && email && password) {
      if (this.validateEmail(email)) {
        if (this.checkPasswordStrength(password)) {
          // 50 行的業務邏輯...
          const user = new User();
          user.name = name;
          user.email = email;
          // 直接 SQL 查詢
          db.query("INSERT INTO users...");
          // 發送 email（直接在這裡）
          sendEmail(email, "Welcome");
          return user;
        } else {
          throw new Error("Password too weak");
        }
      } else {
        throw new Error("Invalid email");
      }
    } else {
      throw new Error("Missing required fields");
    }
  }
}
```

#### 重構後 (After)
```javascript
// UserService.js - 120 行，複雜度 8
class UserService {
  constructor(userRepository, emailService, validator) {
    this.userRepository = userRepository;
    this.emailService = emailService;
    this.validator = validator;
  }

  async createUser(userDto) {
    this.validator.validate(userDto);

    const user = User.from(userDto);
    await this.userRepository.save(user);
    await this.emailService.sendWelcomeEmail(user);

    return user;
  }
}

// UserValidator.js - 單一職責
class UserValidator {
  validate(userDto) {
    this.validateRequiredFields(userDto);
    this.validateEmail(userDto.email);
    this.validatePassword(userDto.password);
  }
}

// UserRepository.js - 資料存取抽象
class UserRepository {
  async save(user) {
    return await this.db.users.create(user);
  }
}
```
````

**架構改善視覺化**：
- 依賴關係圖（Before vs After）
- 複雜度熱力圖（Before vs After）
- 模組耦合度矩陣

**效能改善**：
- 響應時間對比
- 記憶體使用對比
- 資料庫查詢次數對比

#### 步驟 7.3：團隊回饋收集

**開發者體驗改善**：
- 新功能開發速度提升 X%
- Bug 修復時間縮短 X%
- 程式碼審查時間縮短 X%
- 新人上手時間縮短 X 天

**業務價值**：
- 技術債降低 X 天（省下 Y 開發成本）
- 系統穩定性提升（Bug 率降低 X%）
- 交付速度提升（Sprint Velocity 提升 X%）

#### 步驟 7.4：成果報告確認點 (10 分鐘)

> 🔴 **人機協作點：成果報告確認**
>
> **AI 提供**：
> - 量化指標對比表（所有品質指標的前後對比）
> - 程式碼範例集（典型重構的前後對比）
> - 視覺化報告（圖表展示改善成果）
> - ROI 計算（投資回報分析）
> - 經驗總結（重構過程的學習和最佳實踐）
>
> **需人工確認**：
> - ✅ 量化指標是否真實反映改善
> - ✅ 程式碼範例是否具代表性
> - ✅ ROI 計算是否合理
> - ✅ 經驗總結是否完整
>
> **產出文件**：
> - 重構成果報告 (Refactoring Results Report)
> - 前後對比分析 (Before/After Analysis)
> - ROI 報告 (Return on Investment Report)
> - 經驗總結 (Lessons Learned)

---

### 階段 8：知識沉澱與文件更新 (20-30 分鐘)

#### 步驟 8.1：文檔更新
```
執行指令：
「請列出需要更新的文檔清單」
```

#### 步驟 8.2：文檔更新內容 (Technical-Writer)

**技術文檔更新**：
- [ ] 架構文檔（反映新的架構設計）
- [ ] API 文檔（如有介面變更）
- [ ] 資料模型文檔（如有變更）
- [ ] 開發者指南（新的最佳實踐）
- [ ] 程式碼註解和 README

**知識庫更新**：
- [ ] 架構決策記錄 (ADR)
- [ ] 重構模式庫（可重用的重構方案）
- [ ] 常見問題 FAQ
- [ ] Troubleshooting Guide

**團隊知識分享**：
- [ ] 重構分享會（內部技術分享）
- [ ] Code Walkthrough（程式碼導覽）
- [ ] 最佳實踐文件
- [ ] 重構 Playbook（可複製的流程）

#### 步驟 8.3：持續改進機制建立

**建立重構文化**：
- 定期代碼品質審查（每季度）
- 技術債管理流程
- Boy Scout Rule（隨手改善原則）
- 重構時間預算（Sprint 的 10-20%）

**自動化品質守護**：
- CI/CD Pipeline 整合品質檢查
- Pre-commit Hooks（代碼風格、測試）
- Pull Request 品質門檻
- 品質儀表板（持續監控）

**產出文件**：
- 文檔更新清單 (Documentation Updates)
- 架構決策記錄 (Architecture Decision Records)
- 重構 Playbook (Refactoring Playbook)
- 持續改進指南 (Continuous Improvement Guide)

#### 步驟 8.4：知識沉澱確認點 (10 分鐘)

> 🔴 **人機協作點：文件更新與知識沉澱確認**
>
> **AI 提供**：
> - 文檔更新完成度檢核表
> - ADR 摘要清單
> - 重構 Playbook 大綱
> - 持續改進建議
>
> **需人工確認**：
> - 所有必要文檔是否已更新？
> - ADR 記錄是否完整？
> - 重構經驗是否已整理為可複用知識？
> - 持續改進機制是否可行？

---

## 🎯 成功標準

### 品質改善達標
- [ ] 循環複雜度降低 ≥30%
- [ ] 測試覆蓋率提升到目標值
- [ ] Code Smell 減少 ≥50%
- [ ] 技術債降低 ≥40%

### 功能完整性
- [ ] 所有測試通過（單元/整合/E2E）
- [ ] 無功能退化
- [ ] 效能無明顯退化（<5%）
- [ ] 無新增安全性漏洞

### 架構改善
- [ ] 循環依賴消除
- [ ] 模組耦合度降低
- [ ] 設計原則遵循（SOLID）
- [ ] 可擴展性改善

### 團隊效能提升
- [ ] 開發速度提升（主觀評估）
- [ ] Bug 率降低
- [ ] 程式碼審查時間縮短
- [ ] 新人上手更容易

### 文檔完整性
- [ ] 架構文檔已更新
- [ ] ADR 已記錄
- [ ] 重構經驗已分享
- [ ] 知識已沉澱

### 持續改進機制
- [ ] 品質監控已建立
- [ ] 重構流程已固化
- [ ] 團隊共識已達成

---

## 📊 時間分配參考

| 階段 | 預估時間 | 可彈性調整 |
|------|---------|-----------|
| 啟動和情境確認 | 20 分鐘 | ±5 分鐘 |
| 代碼品質深度分析 | 1-1.5 小時 | 視代碼規模 |
| 重構目標設定與範圍界定 | 30-40 分鐘 | - |
| 重構策略制定 | 1-1.5 小時 | - |
| 逐步重構實作指引 | 40-60 分鐘 | 視複雜度 |
| 驗證與品質確認 | 30-40 分鐘 | - |
| 前後對比與成果展示 | 30 分鐘 | - |
| 知識沉澱與文件更新 | 20-30 分鐘 | - |
| **準備階段總計** | **3-4 小時** | |
| **實際重構執行** | 1-8 週 | 依範圍而定 |

---

## 💡 最佳實踐

### 1. 測試先行，重構保險
- 重構前必須有測試保護
- 測試覆蓋率不足時，先補測試
- 使用 Golden Master Testing 建立安全網
- 保持測試持續綠燈

### 2. 小步快跑，頻繁提交
- 每次重構只做一件事
- 每完成一個重構技術就 commit
- 保持每個 commit 可編譯、測試通過
- 出問題時容易回滾

### 3. 行為等價，功能不變
- 重構 ≠ 功能增強
- 保持對外行為完全一致
- 內部實作可改變，介面不變
- 效能改善是副作用，不是主要目標

### 4. 避免過度設計
- 遵循 YAGNI 原則
- 不要為了「未來可能需要」而抽象
- 設計模式要適當，不要濫用
- 簡單優於複雜

### 5. 代碼審查不可少
- 重構 PR 需要仔細審查
- 多雙眼睛發現問題
- 知識分享和傳承
- 確保團隊理解新設計

### 6. 量化改善成果
- 使用工具量化品質改善
- 記錄前後對比數據
- 計算 ROI，證明價值
- 持續監控，避免退化

---

## 🚨 常見陷阱

### ❌ 避免這些錯誤

**1. 規劃階段**
- ❌ 沒有明確目標就開始重構
- ❌ 範圍過大，想一次改完所有問題
- ❌ 沒有測試保護就開始動手
- ❌ 低估重構的時間和風險

**2. 執行階段**
- ❌ 邊重構邊加功能（範圍蔓延）
- ❌ 步子太大，一次改動太多
- ❌ 忽視測試，依賴手動驗證
- ❌ 過度設計，引入不必要的複雜度

**3. 驗證階段**
- ❌ 只測試 Happy Path
- ❌ 忽視效能影響
- ❌ 沒有量化改善成果
- ❌ 缺少前後對比

**4. 協作階段**
- ❌ 獨自重構，不通知團隊
- ❌ PR 過大，難以審查
- ❌ 缺少知識分享
- ❌ 沒有更新文檔

**5. 文化階段**
- ❌ 一次性重構，之後又累積技術債
- ❌ 沒有建立持續改進機制
- ❌ 重構成果沒有宣傳，團隊感受不到價值
- ❌ 沒有固化最佳實踐

---

## 🔍 特殊情境處理

### 情境 A：無測試的 Legacy 代碼
**特徵**：代碼年代久遠、完全沒有測試、文檔缺失

**特殊策略**：
1. **Phase 0：建立安全網** (額外 1-2 週)
   - 使用 Characterization Tests（特徵測試）
   - Approval Tests（快照測試）記錄現有行為
   - Golden Master Testing
   - 至少達到 50% 覆蓋率再開始重構

2. **採用絞殺者模式**：
   - 不直接改舊代碼
   - 在舊代碼外建立新實作
   - 逐步遷移流量
   - 最終淘汰舊代碼

### 情境 B：高風險核心業務邏輯
**特徵**：涉及金流、訂單、庫存等關鍵邏輯

**特殊策略**：
1. **平行運行驗證**：
   - 新舊實作同時執行
   - 對比結果，記錄差異
   - 在 Staging 環境長時間運行
   - 確認一致性後才切換

2. **Feature Flag 控制**：
   - 使用 Feature Flag 動態切換
   - 逐步放量（1% → 10% → 50% → 100%）
   - 可隨時回滾
   - 監控關鍵指標

### 情境 C：效能敏感系統
**特徵**：高 QPS、低延遲要求、效能關鍵

**特殊策略**：
1. **Benchmark 驅動**：
   - 重構前建立 benchmark
   - 每個重構步驟後執行 benchmark
   - 效能退化超過 5% 需調整
   - 使用 profiler 找出瓶頸

> **⚠️ 效能測量和 Benchmark 工具建議**
>
> **Benchmark 工具選擇 (依語言/平台)**:
>
> | 語言/平台 | Benchmark 工具 | Profiler 工具 | 適用場景 |
> |----------|---------------|--------------|---------|
> | **Node.js** | `autocannon`, `clinic.js` | `clinic flame`, `0x` | API 效能測試、事件循環分析 |
> | **Python** | `pytest-benchmark`, `locust` | `cProfile`, `py-spy` | 計算密集任務、併發測試 |
> | **Java** | JMH (Java Microbenchmark Harness) | JProfiler, VisualVM | JVM 優化、GC 分析 |
> | **Go** | `go test -bench`, `vegeta` | `pprof` | 高併發服務、記憶體分析 |
> | **前端** | Lighthouse CI, WebPageTest | Chrome DevTools Profiler | 頁面載入、渲染效能 |
> | **資料庫** | `EXPLAIN ANALYZE`, `pg_stat_statements` | Query Profiler | SQL 查詢優化 |
>
> **效能閾值定義範例**:
> ```yaml
> performance_thresholds:
>   api_response_time:
>     p50: 100ms    # 50% 請求需在 100ms 內完成
>     p95: 300ms    # 95% 請求需在 300ms 內完成
>     p99: 500ms    # 99% 請求需在 500ms 內完成
>   
>   throughput:
>     min_qps: 1000  # 最低每秒請求數
>   
>   resource_usage:
>     max_cpu: 70%   # CPU 使用率上限
>     max_memory: 2GB # 記憶體使用上限
>   
>   degradation_tolerance:
>     max_regression: 5%  # 效能退化容忍度
> ```
>
> **自動化效能測試範例 (CI/CD 整合)**:
> ```yaml
> # .github/workflows/performance-test.yml
> name: Performance Benchmark
> on: [pull_request]
> 
> jobs:
>   benchmark:
>     runs-on: ubuntu-latest
>     steps:
>       - uses: actions/checkout@v3
>       - name: Run Benchmark
>         run: npm run bench
>       
>       - name: Compare with Baseline
>         run: |
>           node scripts/compare-benchmark.js \
>             --baseline benchmarks/baseline.json \
>             --current benchmarks/current.json \
>             --threshold 5
>       
>       - name: Comment PR with Results
>         if: github.event_name == "pull_request"
>         uses: actions/github-script@v6
>         with:
>           script: |
>             const results = require("./benchmarks/comparison.json");
>             github.rest.issues.createComment({
>               issue_number: context.issue.number,
>               owner: context.repo.owner,
>               repo: context.repo.repo,
>               body: `## Performance Benchmark Results\n${results.summary}`
>             });
> ```

   - 使用 profiler 找出瓶頸

2. **分階段優化**：
   - 先重構提升可維護性
   - 再針對性效能優化
   - 不要為了「優雅」犧牲效能
   - 效能和可維護性平衡

### 情境 D：分散式系統重構
**特徵**：多個服務、複雜依賴、部署複雜

**特殊策略**：
1. **服務間契約測試**：
   - 使用 Contract Testing (Pact)
   - 確保 API 相容性
   - 版本管理策略
   - 向下相容性保證

2. **分階段部署**：
   - 先部署被依賴的服務
   - 藍綠部署或金絲雀部署
   - 監控依賴鏈健康度
   - 準備快速回滾

---

## 📞 需要幫助？

### 卡在某個階段
```
「我在 [階段名稱] 遇到困難，具體是 [描述問題]」
```

### 不知道如何重構某段代碼
```
「以下代碼有 [具體問題]，應該如何重構？
[貼上代碼]」
```

### 重構策略選擇
```
「此重構涉及 [描述]，應該採用哪種策略？請提供建議」
```

### 測試補強困難
```
「此代碼 [描述問題]，難以編寫測試，有何建議？」
```

### 效能退化
```
「重構後效能退化 X%，如何在保持代碼品質的同時優化效能？」
```

---

## 📚 實際案例走查

### 案例 1：巨型函式重構 (God Function → Clean Code)

#### 背景
某電商平台的訂單處理函式 `processOrder()` 累積至 850 行程式碼，循環複雜度達 45，維護困難且 Bug 頻發。需要重構以提升可維護性和可測試性。

#### 挑戰
- ❌ **巨型函式**：單一函式 850 行，處理訂單建立、庫存扣減、金額計算、優惠券、支付、通知等所有邏輯
- ❌ **高複雜度**：循環複雜度 CC = 45，深層嵌套 if-else (7 層)
- ❌ **難以測試**：缺乏單元測試，只能整合測試
- ❌ **重複代碼**：多處重複的驗證邏輯
- ❌ **業務風險**：訂單處理是核心業務，不能出錯

#### 執行步驟

**Week 1：程式碼分析與測試補強**
```
載入 AISDLC_INIT.md + Code-Analyzer
→ 使用 Lizard 分析複雜度
→ 識別重複代碼 (使用 jscpd)
→ 🔴 確認重構策略

分析結果:
- 函式長度: 850 行
- 循環複雜度: 45
- 參數數量: 12 個
- 重複代碼: 15 處 (30% 重複率)
- 深層嵌套: 最深 7 層 if-else
- 測試覆蓋率: 0% (單元測試)

補充測試 (Golden Master Testing):
1. 記錄現有 processOrder() 的所有輸出
2. 建立 50 個測試案例 (涵蓋正常/異常/邊界)
3. 使用 Approval Tests 記錄快照
4. 確保重構前測試全通過
```

**Week 2：Extract Method (提取方法) - 第一輪拆分**
```
問題代碼 (Before - 簡化版):
async function processOrder(orderData) {
  // 驗證 (100 行)
  if (!orderData.userId) throw new Error('User ID required');
  if (!orderData.items || orderData.items.length === 0) throw new Error('Items required');
  // ... 50 行驗證邏輯

  // 庫存檢查與扣減 (150 行)
  for (const item of orderData.items) {
    const product = await Product.findByPk(item.productId);
    if (!product) throw new Error(`Product ${item.productId} not found`);
    if (product.stock < item.quantity) throw new Error(`Insufficient stock`);
    product.stock -= item.quantity;
    await product.save();
    // ... 更多庫存邏輯
  }

  // 金額計算 (200 行)
  let subtotal = 0;
  for (const item of orderData.items) {
    const product = await Product.findByPk(item.productId);
    subtotal += product.price * item.quantity;
    if (product.onSale) {
      subtotal -= product.price * item.quantity * product.discountRate;
    }
    // ... 複雜的折扣計算
  }

  // 優惠券處理 (150 行)
  if (orderData.couponCode) {
    const coupon = await Coupon.findOne({ where: { code: orderData.couponCode } });
    if (!coupon) throw new Error('Invalid coupon');
    if (coupon.expiresAt < new Date()) throw new Error('Coupon expired');
    // ... 優惠券驗證和計算
  }

  // 支付處理 (100 行)
  const payment = await PaymentService.processPayment({
    amount: total,
    method: orderData.paymentMethod,
    userId: orderData.userId
  });
  // ... 支付邏輯

  // 建立訂單記錄 (100 行)
  const order = await Order.create({ ... });
  // ... 訂單建立邏輯

  // 發送通知 (50 行)
  await EmailService.sendOrderConfirmation(orderData.userId, order.id);
  await SMSService.sendOrderSMS(orderData.userId, order.id);
  // ... 通知邏輯

  return order;
}

重構後 (After - Extract Method):
// 主函式變得簡潔清晰
async function processOrder(orderData) {
  validateOrderData(orderData);
  await checkAndReserveStock(orderData.items);

  const subtotal = calculateSubtotal(orderData.items);
  const discount = await applyDiscount(subtotal, orderData.couponCode);
  const total = subtotal - discount;

  const payment = await processPayment({
    amount: total,
    method: orderData.paymentMethod,
    userId: orderData.userId
  });

  const order = await createOrderRecord({
    ...orderData,
    subtotal,
    discount,
    total,
    paymentId: payment.id
  });

  await sendOrderNotifications(order);

  return order;
}

// 提取的子函式
function validateOrderData(orderData) {
  if (!orderData.userId) throw new Error('User ID required');
  if (!orderData.items || orderData.items.length === 0) {
    throw new Error('Items required');
  }
  // ... 其他驗證
}

async function checkAndReserveStock(items) {
  for (const item of items) {
    const product = await Product.findByPk(item.productId);
    if (!product) throw new Error(`Product ${item.productId} not found`);
    if (product.stock < item.quantity) {
      throw new Error(`Insufficient stock for ${product.name}`);
    }
    await product.decrement('stock', { by: item.quantity });
  }
}

function calculateSubtotal(items) {
  return items.reduce((sum, item) => {
    return sum + (item.price * item.quantity);
  }, 0);
}

async function applyDiscount(subtotal, couponCode) {
  if (!couponCode) return 0;

  const coupon = await Coupon.findValidCoupon(couponCode);
  return coupon.calculateDiscount(subtotal);
}

async function processPayment(paymentData) {
  return await PaymentService.processPayment(paymentData);
}

async function createOrderRecord(orderData) {
  return await Order.create(orderData);
}

async function sendOrderNotifications(order) {
  await Promise.all([
    EmailService.sendOrderConfirmation(order.userId, order.id),
    SMSService.sendOrderSMS(order.userId, order.id)
  ]);
}

改善結果:
- 主函式: 850 行 → 25 行 (-97%)
- 循環複雜度: 45 → 5 (-89%)
- 可讀性大幅提升
```

**Week 3：Extract Class (提取類別) - 引入領域模型**
```
進一步重構: 引入 Order 領域類別

class OrderProcessor {
  constructor(inventoryService, paymentService, notificationService) {
    this.inventoryService = inventoryService;
    this.paymentService = paymentService;
    this.notificationService = notificationService;
  }

  async process(orderData) {
    this.validate(orderData);

    await this.inventoryService.reserveStock(orderData.items);

    const pricing = this.calculatePricing(orderData);
    const payment = await this.paymentService.process({
      amount: pricing.total,
      method: orderData.paymentMethod,
      userId: orderData.userId
    });

    const order = await this.createOrder({
      ...orderData,
      ...pricing,
      paymentId: payment.id
    });

    await this.notificationService.sendOrderConfirmation(order);

    return order;
  }

  validate(orderData) {
    // 驗證邏輯
  }

  calculatePricing(orderData) {
    const subtotal = this.calculateSubtotal(orderData.items);
    const discount = this.calculateDiscount(subtotal, orderData.couponCode);
    const total = subtotal - discount;

    return { subtotal, discount, total };
  }

  // ... 其他方法
}

// 使用依賴注入
const orderProcessor = new OrderProcessor(
  new InventoryService(),
  new PaymentService(),
  new NotificationService()
);

const order = await orderProcessor.process(orderData);

改善結果:
- 單一職責原則 (SRP): ✅
- 依賴注入: ✅ (易於測試)
- 可測試性: 大幅提升
```

**Week 4：測試驗證與效能確認**
```
1. 單元測試 (新增)
describe('OrderProcessor', () => {
  let orderProcessor;
  let mockInventory, mockPayment, mockNotification;

  beforeEach(() => {
    mockInventory = {
      reserveStock: jest.fn().mockResolvedValue(true)
    };
    mockPayment = {
      process: jest.fn().mockResolvedValue({ id: 'pay-123' })
    };
    mockNotification = {
      sendOrderConfirmation: jest.fn().mockResolvedValue(true)
    };

    orderProcessor = new OrderProcessor(
      mockInventory,
      mockPayment,
      mockNotification
    );
  });

  it('should process order successfully', async () => {
    const orderData = {
      userId: 'user-123',
      items: [{ productId: 'prod-1', quantity: 2, price: 100 }],
      paymentMethod: 'credit_card'
    };

    const order = await orderProcessor.process(orderData);

    expect(order).toBeDefined();
    expect(mockInventory.reserveStock).toHaveBeenCalled();
    expect(mockPayment.process).toHaveBeenCalledWith(
      expect.objectContaining({ amount: 200 })
    );
  });

  // ... 50+ 測試案例
});

2. Golden Master Tests (回歸測試)
- 所有 50 個測試案例通過 ✅
- 輸出與重構前完全一致 ✅

3. 效能測試
- Benchmark 對比:
  Before: 450ms ± 50ms
  After:  420ms ± 30ms (-7%, 效能略有提升)
```

#### 關鍵成果
- ✅ **程式碼長度**：850 行 → 分散至 8 個小函式 (平均 50 行/函式)
- ✅ **循環複雜度**：45 → 5 (-89%)
- ✅ **測試覆蓋率**：0% → 95%
- ✅ **可維護性指標 (MI)**：23 → 85 (+270%)
- ✅ **Bug 率降低**：重構後 3 個月 Bug -60%

#### 時程與成本
- **總時程**：4 週
- **人力**：1 資深後端工程師
- **成本**：約 $12k
- **ROI**：維護成本降低 40% (每年節省 $50k)

#### 重構技術總結
| 重構技術 | 適用場景 | 改善指標 |
|---------|---------|---------|
| **Extract Method** | 長函式 (>50 行) | 複雜度 -80%+ |
| **Extract Class** | 職責過多的類別 | 耦合度 -60%+ |
| **Replace Conditional with Polymorphism** | 大量 if-else/switch | 複雜度 -70%+ |
| **Introduce Parameter Object** | 參數過多 (>3 個) | 可讀性 +50%+ |
| **Dependency Injection** | 強耦合 | 可測試性 +200%+ |

#### 經驗教訓
1. **測試先行**：Golden Master Testing 保證重構安全
2. **小步快跑**：每次重構一個技術，頻繁 commit
3. **持續驗證**：每次重構後執行完整測試套件
4. **效能監控**：重構不應導致效能退化
5. **程式碼審查**：重構 PR 需要嚴格審查

---

### 案例 2：架構遷移 (Monolith → Microservices)

#### 背景
某 SaaS 平台採用單體架構 (Monolith) 運行 5 年，隨著業務成長面臨擴展性、部署效率、團隊協作等瓶頸。決定逐步拆分為微服務架構。

#### 挑戰
- ❌ **單體龐大**：50 萬行程式碼，12 個核心模組
- ❌ **強耦合**：模組間緊密耦合，難以拆分
- ❌ **共享資料庫**：所有模組共用一個資料庫
- ❌ **部署困難**：單一服務部署需要 2 小時停機
- ❌ **團隊協作**：20 位工程師在同一 Codebase 協作，衝突頻繁

#### 執行步驟

**Phase 1：領域分析與服務拆分策略 (1 個月)**
```
載入 AISDLC_INIT.md + SD-Architect
→ 使用 DDD (Domain-Driven Design) 分析業務領域
→ 識別有界上下文 (Bounded Context)
→ 🔴 確認服務拆分方案

領域分析:
1. User Management (使用者管理)
   - 註冊、登入、權限
   - 使用者: 所有服務
   - 依賴: 無

2. Product Catalog (商品目錄)
   - 商品管理、分類、搜尋
   - 使用者: 訂單、推薦
   - 依賴: 無

3. Order Processing (訂單處理)
   - 訂單建立、支付、物流
   - 使用者: 前端、報表
   - 依賴: User, Product, Inventory, Payment

4. Inventory Management (庫存管理)
   - 庫存追蹤、補貨、預警
   - 使用者: Order, Product
   - 依賴: Product

5. Payment Gateway (支付閘道)
   - 支付處理、退款
   - 使用者: Order
   - 依賴: User

6. Notification Service (通知服務)
   - Email、SMS、Push 通知
   - 使用者: Order, User
   - 依賴: User

7. Reporting & Analytics (報表分析)
   - 業務報表、資料分析
   - 使用者: 管理後台
   - 依賴: Order, User, Product

拆分順序 (依賴度由低到高):
1. Notification Service (最低依賴)
2. User Management
3. Product Catalog
4. Inventory Management
5. Payment Gateway
6. Order Processing (最高依賴)
7. Reporting & Analytics
```

**Phase 2：建立微服務基礎設施 (2 個月)**
```
1. API Gateway (使用 Kong/AWS API Gateway)
   - 統一入口
   - 路由管理
   - 認證/授權
   - Rate Limiting

2. Service Mesh (使用 Istio)
   - 服務間通訊
   - 負載均衡
   - 斷路器
   - 分散式追蹤

3. Message Queue (使用 RabbitMQ/Kafka)
   - 非同步通訊
   - Event-Driven Architecture
   - 解耦服務

4. 配置中心 (使用 Consul/Spring Cloud Config)
   - 集中配置管理
   - 環境變數管理

5. 服務註冊與發現 (使用 Consul/Eureka)
   - 服務註冊
   - 健康檢查
   - 動態發現

6. 監控與日誌 (使用 Prometheus + Grafana + ELK)
   - Metrics 收集
   - 分散式日誌聚合
   - 告警機制
```

**Phase 3：絞殺者模式逐步拆分 (6 個月，每月拆 1-2 個服務)**
```
Month 1: Notification Service (最簡單，試點)
- 從 Monolith 抽取通知邏輯
- 建立獨立 Notification Service (Node.js)
- 使用 Message Queue 接收通知請求
- Monolith 發送通知請求到 MQ
- 監控 2 週，確認穩定

Month 2: User Management Service
- 抽取使用者管理邏輯
- 建立獨立資料庫 (PostgreSQL - users schema)
- 實作 User Service (Java Spring Boot)
- API Gateway 路由 /api/users/* → User Service
- 雙寫: Monolith 同時寫入新舊資料庫
- 資料驗證，切換資料來源

Month 3: Product Catalog Service
- 抽取商品管理邏輯
- 建立獨立資料庫 (MongoDB - products)
- 實作 Product Service (Python FastAPI)
- 資料遷移與驗證

Month 4: Inventory Management Service
- 抽取庫存管理邏輯
- 使用 Event Sourcing 模式
- Inventory Service 訂閱 Order Events
- 自動扣減庫存

Month 5: Payment Gateway Service
- 抽取支付邏輯
- Payment Service (Node.js)
- 整合第三方支付 API

Month 6: Order Processing Service
- 最複雜,最後拆分
- 整合所有已拆分服務
- Saga Pattern 處理分散式交易
- 使用 Choreography (事件驅動) 協調服務
```

**Phase 4：資料庫拆分與資料同步 (2 個月)**
```
挑戰: 共享資料庫需拆分為獨立資料庫

策略:
1. 識別資料依賴 (使用 SQL 查詢分析工具)
2. 設計新資料模型 (每個服務獨立 Schema)
3. 雙寫階段 (Monolith 同時寫入新舊 DB)
4. 使用 CDC (Change Data Capture) 同步歷史資料
5. 驗證資料一致性
6. 切換資料來源
7. 停用舊資料表

資料同步工具:
- Debezium (PostgreSQL CDC)
- AWS DMS (Database Migration Service)
```

**Phase 5：完全解耦與 Monolith 退役 (2 個月)**
```
1. 移除 Monolith 對微服務的依賴
2. 所有流量切換至微服務
3. 保留 Monolith 30 天 (備援)
4. 關閉 Monolith
5. 資料庫歸檔
```

#### 關鍵成果
- ✅ **部署效率**：停機部署 2 小時 → 零停機滾動部署 < 10 分鐘
- ✅ **擴展性**：單一服務 → 每個服務獨立水平擴展
- ✅ **開發效率**：團隊可並行開發，衝突率 -80%
- ✅ **故障隔離**：單一服務故障不影響其他服務
- ✅ **技術異構**：可使用最適合的技術棧 (Java, Node.js, Python, Go)

#### 時程與成本
- **總時程**：13 個月
- **人力**：10 後端工程師 + 2 DevOps + 1 架構師
- **成本**：約 $1.2M (人力) + $200k (基礎設施)
- **ROI**：開發效率提升 40%、部署頻率提升 10x、故障率降低 70%

#### 架構對比
| 指標 | Monolith | Microservices | 改善幅度 |
|------|----------|---------------|---------|
| **部署時間** | 2 小時 | < 10 分鐘 | -98% |
| **部署頻率** | 每月 1 次 | 每日 10+ 次 | +3000% |
| **單一服務故障影響** | 全站當機 | 局部功能降級 | -90% 可用性損失 |
| **擴展靈活性** | 整體擴展 | 按需擴展特定服務 | 成本降低 60% |
| **開發速度** | 衝突頻繁 | 並行開發 | 效率 +40% |

#### 經驗教訓
1. **漸進式遷移**：絞殺者模式降低風險，避免 Big Bang
2. **先易後難**：先拆分低依賴服務，積累經驗
3. **資料同步**：雙寫 + CDC 確保資料一致性
4. **監控必須**：分散式追蹤 (Jaeger/Zipkin) 不可少
5. **團隊準備**：微服務需要 DevOps 文化和技能

---

## 🎓 相關資源

- [Refactoring Prompt Templates](../../prompts/scenario-prompts/refactoring-prompts.md)
- [Refactoring Planning Workflow](../../workflow/scenario-specific/refactoring-planning-flow.md)
- [Code Analyzer Agent](../../agent/specialized/code-analyzer-zh.yaml)
- [Dev Senior Agent](../../agent/specialized/dev-senior-zh.yaml)
- [分析文檔模板](../../docs_template/scenario_specific/analysis/) - Legacy 系統分析、影響分析、差距分析

---

## 📚 推薦閱讀

- **書籍**：
  - "Refactoring" by Martin Fowler
  - "Working Effectively with Legacy Code" by Michael Feathers
  - "Clean Code" by Robert C. Martin

- **線上資源**：
  - [Refactoring Guru](https://refactoring.guru/)
  - [SourceMaking - Refactoring](https://sourcemaking.com/refactoring)

---

**下一步**：準備好材料後，執行 [階段 1](#階段-1啟動和情境確認-20-分鐘) 開始你的代碼重構之旅！
