# AISDLC 專案初始化指南
# AISDLC Project Initialization Guide

> **🎯 適用對象**: 所有新啟動的專案
> **📖 適用情境**: 十種開發情境（Greenfield, Brownfield, Refactoring, Integration, Performance, Testing, Security, DevOps, Documentation, Migration）

---

**版本**: v0.01
**最後更新**: 2026-06-06
**文檔類型**: 使用者指南 | 專案初始化
**維護者**: AISDLC Framework Team

---

## 🎯 文檔目的

**🔴 重要觀念：AISDLC 框架本身就是專案工作目錄**

本指南說明 AISDLC 框架的正確使用方式：
1. ✅ **專案文件直接寫入 `AISDLC_v0.0x/docs/` 目錄**
2. ✅ **不需要在專案根目錄另建目錄結構**
3. ✅ **框架目錄結構已完整，可直接使用**
4. ✅ **初始化腳本僅用於建立缺少的 docs/ 子目錄**

---

## 📚 目錄

- [快速啟動（5 分鐘）](#快速啟動5-分鐘)
- [標準初始化流程](#標準初始化流程)
- [十種情境專屬設定](#十種情境專屬設定)
- [常見問題](#常見問題)

---

## 🚀 快速啟動

### 🎯 方式一：直接使用（推薦，0 秒）

**AISDLC 框架本身就是專案工作目錄，無需初始化**：

```bash
# 1. 進入 AISDLC 框架目錄
cd /path/to/AISDLC_ALL/AISDLC_SDD_v0.01

# 2. 開始工作！文件直接寫入 docs/ 目錄
# - PRD 寫入 docs/01_requirements/
# - SRD 寫入 docs/02_architecture/
# - 測試文件寫入 docs/03_testing/
# ... 以此類推
```

**目錄結構已完整**：
```
AISDLC_SDD_v0.01/
├── AISDLC_SDD_INIT.md              # 框架初始化文件
├── CLAUDE.md                   # Claude Code 專案指引
├── docs/                       # 專案文件輸出目錄 ✅
│   ├── 01_requirements/        # 需求文檔
│   ├── 02_architecture/        # 架構設計
│   ├── 03_testing/             # 測試文檔
│   ├── 04_planning/            # 專案規劃
│   ├── 05_development/         # 迭代執行
│   ├── 06_quality/             # 程式碼品質
│   ├── 07_design/              # 設計文檔
│   └── 08_deployment/          # 部署文檔
├── agent/                      # Agent 配置
├── workflow/                   # Workflow 定義
└── ...
```

### 🔧 方式二：初始化腳本（僅建立缺少的子目錄）

**僅當 docs/ 子目錄缺失時使用**：

```bash
# 進入 AISDLC 框架目錄
cd /path/to/AISDLC_ALL/AISDLC_SDD_v0.01

# 執行初始化腳本（僅建立缺少的 docs/ 子目錄）
bash tools/init_project.sh
```

**腳本僅執行**：
- ✅ 檢查 docs/ 子目錄是否存在
- ✅ 建立缺少的子目錄（01_requirements ~ 08_deployment）
- ❌ **不建立** AISDLC/ 目錄（已在框架內）
- ❌ **不建立** framework 連結（不需要）

---

## 📋 正確使用方式

### 工作流程

**🔴 關鍵觀念：直接在 AISDLC_SDD_v0.01/ 目錄內工作**

```bash
# 1. 進入框架目錄
cd /path/to/AISDLC_ALL/AISDLC_SDD_v0.01

# 2. 檢查 docs/ 子目錄是否完整（可選）
ls -la docs/

# 3. 如果子目錄缺失，執行初始化腳本
bash tools/init_project.sh

# 4. 開始工作！
# - 撰寫 PRD → docs/01_requirements/PRD_YourProject.md
# - 撰寫 SRD → docs/02_architecture/SRD_System_Design.md
# - 撰寫測試計畫 → docs/03_testing/Test_Plan.md
# ... 以此類推
```

### 目錄結構說明（開發專注版 v0.01）

| 目錄 | 用途 | 主要產出文檔 |
|------|------|------------|
| `docs/01_requirements/` | 需求文檔 | PRD, FRD, User Stories, Epic Backlog |
| `docs/02_architecture/` | 架構設計 | SRD, API Specification, Architecture Diagram |
| `docs/03_testing/` | 測試文檔 | Test Plan, Test Cases, Test Reports, AT |
| `docs/04_planning/` | 專案規劃 | Roadmap, Effort Estimation, Task Breakdown |
| `docs/05_development/` | 迭代執行 | Iteration Plans, Progress Logs, Sprint Reports |
| `docs/06_quality/` | 程式碼品質 | Code Quality Reports, Security Audits, Performance Analysis |
| `docs/07_design/` | 設計文檔 | UI/UX Design, Database Schema, ER Diagram |
| `docs/08_deployment/` | 部署維運 | CI/CD Config, Release Notes, Deployment Guide, CHANGELOG |

---

## 🎯 情境專屬初始化（可選）

### 根據十種情境建立額外子目錄

根據十種情境執行額外設定：

#### 4.1 Greenfield（新專案開發）

```bash
# 建立額外目錄
mkdir -p docs/04_planning/sprints/{sprint_1,sprint_2,sprint_3}
mkdir -p docs/01_requirements/mvp

# 拷貝 Greenfield 專用檢查清單
cp scenarios/greenfield/checklists/* docs/04_planning/
```

#### 4.2 Brownfield（舊專案維護）

```bash
# 建立現有系統分析目錄
mkdir -p docs/06_quality/analysis/{codebase,legacy_system}
mkdir -p docs/08_deployment/migration

# 拷貝 Brownfield 專用工具
cp scenarios/brownfield/tools/* docs/06_quality/analysis/
```

#### 4.3 Refactoring（系統重構）

```bash
# 建立重構計劃目錄
mkdir -p docs/06_quality/refactoring/{before,after,migration_plan}

# 拷貝重構檢查清單
cp scenarios/refactoring/checklists/* docs/06_quality/refactoring/
```

#### 4.4 Integration（第三方整合）

```bash
# 建立整合文檔目錄
mkdir -p docs/02_architecture/integration/{api_research,authentication,data_mapping}

# 拷貝 Integration QuickRef
cp scenarios/integration/SOP_QuickRef.md docs/04_planning/
```

#### 4.5 Performance（效能優化）

```bash
# 建立效能分析目錄
mkdir -p docs/06_quality/performance/{baseline,profiling,optimization}

# 拷貝效能測試模板
cp scenarios/performance/templates/* docs/06_quality/performance/
```

#### 4.6 Testing（測試策略）

```bash
# 建立測試策略目錄
mkdir -p docs/03_testing/{strategy,automation,coverage}

# 拷貝測試檢查清單
cp scenarios/testing/checklists/* docs/03_testing/
```

#### 4.7 Security（安全審查）

```bash
# 建立安全審查目錄
mkdir -p docs/06_quality/security/{threat_model,vulnerability,compliance}

# 拷貝安全檢查清單
cp scenarios/security/checklists/* docs/06_quality/security/
```

#### 4.8 DevOps（CI/CD 部署）

```bash
# 建立 DevOps 目錄
mkdir -p docs/08_deployment/devops/{pipeline,infrastructure,monitoring}

# 拷貝 CI/CD 模板
cp scenarios/devops/templates/* docs/08_deployment/devops/
```

#### 4.9 Documentation（技術文檔）

```bash
# 建立文檔維護目錄
mkdir -p docs/07_design/documentation/{api_docs,user_guides,developer_guides}

# 拷貝文檔模板
cp scenarios/documentation/templates/* docs/07_design/documentation/
```

#### 4.10 Migration（技術棧遷移）

```bash
# 建立遷移文檔目錄
mkdir -p docs/02_architecture/migration/{contract_map,compatibility}
mkdir -p docs/08_deployment/{cutover,rollback}

# 拷貝 Migration QuickRef
cp scenarios/migration/SOP_QuickRef.md docs/04_planning/
```

---

### 階段 5: Git 初始化與提交（2 分鐘）

```bash
# 建立 .gitignore
cat > .gitignore << 'EOF'
# AISDLC 臨時文件
docs/**/temp/
docs/**/*.backup
docs/**/*.tmp

# 編輯器臨時文件
.DS_Store
*.swp
*.swo
*~

# 建置產出
build/
dist/
EOF

# 提交初始化
git add .
git commit -m "chore: initialize AISDLC project structure

- Add AISDLC framework (v0.01)
- Create standard docs/ directory structure
- Add AISDLC_PROJECT_CONFIG.md
- Configure for [Scenario] scenario"
```

---

## 🎯 十種情境專屬設定

### 完整檢查清單矩陣

| 情境 | 額外目錄（開發專注版） | 必要檔案 | 推薦工具 |
|------|---------|---------|---------|
| **Greenfield** | `docs/04_planning/sprints/`, `docs/01_requirements/mvp/` | 72 個標準確認問題, Completeness Checklist | Cost Estimation Template |
| **Brownfield** | `docs/06_quality/analysis/`, `docs/08_deployment/migration/` | Legacy System Analysis, Code Audit Report | Dependency Graph Tool |
| **Refactoring** | `docs/06_quality/refactoring/before/`, `docs/06_quality/refactoring/after/` | Refactoring Plan, Code Quality Report | Code Analyzer |
| **Integration** | `docs/02_architecture/integration/api_research/`, `docs/02_architecture/integration/auth/` | API Specification, Integration Test Plan | Postman/Swagger |
| **Performance** | `docs/06_quality/performance/baseline/`, `docs/06_quality/performance/profiling/` | Performance Baseline, Optimization Plan | Profiler, Load Testing Tool |
| **Testing** | `docs/03_testing/strategy/`, `docs/03_testing/automation/` | Test Strategy, Test Automation Plan | Selenium, Jest, Pytest |
| **Security** | `docs/06_quality/security/threat_model/`, `docs/06_quality/security/compliance/` | Threat Model, Security Checklist | OWASP ZAP, SonarQube |
| **DevOps** | `docs/08_deployment/devops/pipeline/`, `docs/08_deployment/devops/infrastructure/` | CI/CD Pipeline Config, Deployment Guide | Jenkins, GitLab CI, Terraform |
| **Documentation** | `docs/07_design/documentation/api_docs/`, `docs/07_design/documentation/guides/` | Documentation Standards, API Doc Template | Swagger, Docusaurus, MkDocs |
| **Migration** | `docs/02_architecture/migration/`, `docs/08_deployment/cutover/` | Migration Contract Map, Cutover/Rollback Spec | Schema Diff Tool, Contract Test |

---

## 📚 文檔產出規範

### 文檔命名規範

#### 需求文檔 (`docs/01_requirements/`)
```
格式: {DOCTYPE}_{MODULE_NAME}.md
範例:
  - PRD_MoneyTracker_Pro.md
  - FRD_Core_Transaction_Module.md
  - Epic_UserStory_Backlog.md
```

#### 架構設計 (`docs/02_architecture/`)
```
格式: {DOCTYPE}_{MODULE_NAME}.md
範例:
  - SRD_System_Architecture.md
  - API_Specification_Cloud_Sync.md
  - Architecture_Design_Document.md
```

#### 測試文檔 (`docs/03_testing/`)
```
格式: {DOCTYPE}_{TEST_TYPE}_{MODULE}.md
範例:
  - Test_Plan_Acceptance_Testing.md
  - AT_Core_Transaction_Module.md
  - Test_Report_Sprint_1.md
```

#### 專案規劃 (`docs/04_planning/`)
```
格式: {PLAN_TYPE}_{DESCRIPTION}.md
範例:
  - Effort_Estimation_Resource_Planning.md
  - Sprint_1_Execution_Plan.md
  - MVP_Definition_Plan.md
```

#### 迭代執行 (`docs/05_development/`)
```
格式: Iteration_{N}_{DESCRIPTION}.md
範例:
  - Iteration_1_Plan.md
  - Iteration_1_Progress_Log.md
  - Sprint_Report_Week_1.md
```

#### 程式碼品質 (`docs/06_quality/`)
```
格式: {QUALITY_TYPE}_{DESCRIPTION}.md
範例:
  - Code_Quality_Report_Sprint_1.md
  - Security_Audit_Report.md
  - Performance_Analysis_Report.md
```

### 文檔模板使用

所有文檔應使用 AISDLC 提供的標準模板：

```bash
# 需求文檔模板
docs_template/core/prd/PRD_Universal_Template.md
docs_template/core/frd/FRD_Universal_Template.md

# 架構設計模板
docs_template/core/srd/SRD_Module_Template.md
docs_template/core/api/API_Specification_Template.md

# 測試模板
docs_template/core/tests/AT_Module_Template.md
docs_template/core/tests/Test_Report_Template.md
```

### 文檔元數據

每個文檔應包含標準元數據：

```markdown
## 文檔元數據
- **專案名稱**: [專案名稱]
- **文檔類型**: [PRD/FRD/SRD/API/AT/...]
- **文檔版本**: v1.0
- **建立日期**: YYYY-MM-DD
- **最後更新**: YYYY-MM-DD
- **負責人**: [姓名 (角色)]
- **文檔狀態**: [Draft/Review/Final]
- **追溯編號**: [US-XXX, EPIC-XXX, etc.]
```

---

## 🔍 驗證檢查清單

### 初始化完成驗證

- [ ] **目錄結構檢查（開發專注版 v0.01）**
  - [ ] `AISDLC/` 目錄存在且可訪問
  - [ ] `docs/01_requirements/` ~ `docs/08_deployment/` 已建立
  - [ ] 情境專屬目錄已建立（如適用）

- [ ] **配置檔檢查**
  - [ ] `AISDLC_PROJECT_CONFIG.md` 已建立且填寫完整
  - [ ] 專案元數據正確無誤
  - [ ] 團隊資訊已填寫

- [ ] **文檔模板檢查**
  - [ ] AISDLC 文檔模板可訪問
  - [ ] 情境專用模板已拷貝（如適用）

- [ ] **Git 檢查**
  - [ ] `.gitignore` 已建立
  - [ ] 初始化已提交

### 執行驗證命令

```bash
# 驗證目錄結構
tree -L 2 docs/

# 驗證 AISDLC 框架連結
ls -la AISDLC_SDD_INIT.md

# 驗證 Git 提交
git log --oneline -1
```

---

## ❓ 常見問題

### Q1: docs/ 目錄結構可以自訂嗎？

**A**: 可以，但建議保留以下核心目錄（開發專注版）：
- ✅ 必須保留: `01_requirements/`, `02_architecture/`, `03_testing/`
- 📝 建議保留: `04_planning/`, `05_development/`, `06_quality/`, `07_design/`, `08_deployment/`
- 🔄 可自訂: 各目錄內的子目錄根據專案需求調整

### Q2: 如何更新 AISDLC 框架版本？

**A**: 使用 Git 更新框架版本：
```bash
cd /path/to/AISDLC_ALL/AISDLC_SDD_v0.01
git pull origin main
```

### Q3: 多個情境混合使用怎麼辦？

**A**: 建立多個情境的合併目錄（開發專注版）：

```bash
# 範例：Greenfield + Integration + DevOps
mkdir -p docs/{04_planning/sprints,02_architecture/integration,08_deployment/devops}
cp scenarios/{greenfield,integration,devops}/checklists/* docs/04_planning/
```

### Q4: 舊專案如何補充初始化？

**A**:
1. 備份現有文檔
2. 執行標準初始化流程
3. 將現有文檔移動到對應目錄
4. 補充缺失的配置檔和目錄

```bash
# 備份
cp -r docs docs.backup

# 執行初始化（不覆蓋現有文件）（開發專注版）
mkdir -p docs/{01_requirements,02_architecture,03_testing,04_planning,05_development,06_quality,07_design,08_deployment}

# 移動現有文檔
# （根據實際情況手動移動）
```

---

## 📋 快速參考

### 完整初始化命令集合（複製即用）

```bash
#!/bin/bash
# AISDLC-SDD v0.01 專案快速初始化腳本
# 使用方式: cd /path/to/AISDLC_ALL/AISDLC_SDD_v0.01 && bash init-project.sh

echo "🚀 初始化 AISDLC-SDD v0.01 專案"

# 步驟 1: 使用內建初始化腳本
bash tools/init_project.sh

# 步驟 2: 建立配置檔（可選）
cat > AISDLC_PROJECT_CONFIG.md << EOF
# AISDLC 專案配置

## 專案元數據
- **專案名稱**: [請填寫]
- **AISDLC 版本**: v0.01
- **開發情境**: $SCENARIO
- **初始化日期**: $(date +%Y-%m-%d)
EOF

# 步驟 4: 情境專屬設定（開發專注版）
case "$SCENARIO" in
  greenfield)
    mkdir -p docs/04_planning/sprints/{sprint_1,sprint_2,sprint_3}
    ;;
  brownfield)
    mkdir -p docs/06_quality/analysis/{codebase,legacy_system}
    ;;
  integration)
    mkdir -p docs/02_architecture/integration/{api_research,authentication,data_mapping}
    ;;
esac

# 步驟 5: Git 初始化
cat > .gitignore << EOF
docs/**/temp/
docs/**/*.backup
.DS_Store
EOF

find docs -type d -empty -exec touch {}/.gitkeep \;

echo "✅ 初始化完成！請執行："
echo "   git add ."
echo "   git commit -m 'chore: initialize AISDLC project'"
```

---

## 📚 相關文檔

- [AISDLC_SDD_INIT.md](../../../AISDLC_SDD_INIT.md) - AISDLC 框架初始化配置
- [FILE_DIRECTORY_RULES.md](../../../FILE_DIRECTORY_RULES.md) - 檔案目錄維護規則
- [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) - AISDLC 快速啟動指南
- [Scenario SOPs](../../../scenarios/) - 十種情境 SOP

---

**維護者**: AISDLC-SDD Framework Team
**最後更新**: 2026-06-06
**版本**: v0.01
