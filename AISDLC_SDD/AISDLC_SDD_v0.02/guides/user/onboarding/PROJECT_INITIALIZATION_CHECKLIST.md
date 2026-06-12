# AISDLC 專案初始化檢查清單
# AISDLC Project Initialization Checklist

> **🎯 目的**: 確保專案啟動時 AISDLC 框架設定完整無誤
> **📋 使用時機**: 新專案啟動的第一步

---

**版本**: v0.01
**最後更新**: 2026-06-06

---

**🔴 重要觀念（2026-06-06 更新）**：
- ✅ **AISDLC 框架本身就是專案工作目錄**
- ✅ **專案文件直接寫入 AISDLC_SDD_v0.01/docs/ 目錄**
- ✅ **不需要在其他地方建立專案目錄**
- ✅ **不需要建立符號連結或 AISDLC/framework/ 結構**

---

## 📋 快速檢查清單（可列印版本）

```
□ 階段 1: 環境準備 (3 分鐘)
  □ 1.1 切換至 AISDLC_SDD_v0.01/ 目錄
  □ 1.2 確認 Git 已初始化
  □ 1.3 確認開發情境類型（十種情境之一）

□ 階段 2: 專案文檔目錄檢查 (2 分鐘)
  □ 2.1 檢查 docs/ 子目錄完整性
  □ 2.2 執行初始化腳本（如需要）
  □ 2.3 建立情境專屬目錄（依情境類型）
  □ 2.4 建立 .gitkeep 保留空目錄

□ 階段 3: 專案配置檔建立 (5 分鐘)
  □ 3.1 建立 AISDLC_PROJECT_CONFIG.md（可選）
  □ 3.2 填寫專案元數據
  □ 3.3 填寫團隊資訊
  □ 3.4 確認文檔產出位置設定

□ 階段 4: Git 提交 (2 分鐘)
  □ 4.1 確認 .gitignore 存在
  □ 4.2 提交初始化變更
  □ 4.3 建立初始 Git Tag (可選)

□ 階段 5: 最終驗證 (3 分鐘)
  □ 5.1 目錄結構完整性驗證 (tree docs/)
  □ 5.2 配置檔完整性驗證
  □ 5.3 Git 提交狀態驗證
  □ 5.4 團隊同步確認
```

---

## 📊 詳細檢查清單（逐項說明）

### 階段 1: 環境準備

#### ✅ 1.1 切換至 AISDLC_SDD_v0.01/ 目錄

**執行命令**:
```bash
cd /path/to/AISDLC_ALL/AISDLC_SDD_v0.01
pwd  # 確認當前在 AISDLC_SDD_v0.01/ 目錄
```

**預期結果**:
- 顯示路徑如 `/Users/你的名字/AISDLC_ALL/AISDLC_SDD_v0.01`
- 執行 `ls` 可看到 AISDLC_SDD_INIT.md, docs/, agent/, workflow/ 等目錄

---

#### ✅ 1.2 確認 Git 已初始化

**檢查方式**:
```bash
git status
```

**預期結果**:
- 顯示 `On branch main` 或 `On branch master`
- 如未初始化，執行 `git init`

**失敗處理**:
```bash
# 如果 Git 未初始化
git init
git branch -m main  # 設定主分支名稱為 main
```

---

#### ✅ 1.3 確認開發情境類型

**檢查方式**:
與團隊確認屬於以下哪一種情境：

| 情境類型 | 適用場景 | 關鍵字 |
|---------|---------|-------|
| **Greenfield** | 全新專案開發 | 從零開始、新產品、MVP |
| **Brownfield** | 既有系統維護 | 既有系統、修改功能、Bug 修復 |
| **Refactoring** | 系統重構 | 代碼重構、架構優化、技術債 |
| **Integration** | 第三方整合 | API 整合、第三方服務、SSO |
| **Performance** | 效能優化 | 回應時間、併發處理、資源優化 |
| **Testing** | 測試策略 | 測試自動化、測試覆蓋率、QA 流程 |
| **Security** | 安全審查 | 安全漏洞、合規要求、OWASP |
| **DevOps** | CI/CD 部署 | 自動化部署、容器化、基礎設施 |
| **Documentation** | 技術文檔 | API 文檔、使用者手冊、知識庫 |
| **Migration** | 技術棧/平台遷移 | 系統遷移、資料庫切換、雲端搬遷 |

**記錄位置**: 稍後填入 `AISDLC_PROJECT_CONFIG.md`（可選）

---

### 階段 2: 專案文檔目錄檢查

#### ✅ 2.1 檢查 docs/ 子目錄完整性

**執行命令**:
```bash
ls -la docs/
```

**預期結果**:
應包含以下 8 個編號目錄（開發專注版）：
- `01_requirements/`
- `02_architecture/`
- `03_testing/`
- `04_planning/`
- `05_development/`
- `06_quality/`
- `07_design/`
- `08_deployment/`

---

#### ✅ 2.2 執行初始化腳本（如需要）

**如果 docs/ 子目錄不完整，執行**:

**macOS/Linux**:
```bash
bash tools/init_project.sh
```

**Windows**:
```powershell
powershell tools/init_project.ps1
```

**驗證**:
```bash
tree -L 2 docs/
```

---

### 階段 3: 專案文檔目錄建立

**注意**: 通常執行初始化腳本後，基本子目錄已自動建立。以下為進階情境專屬目錄建立（可選）。

---

#### ✅ 3.1 建立情境專屬目錄（可選）

**Greenfield 專屬**:
```bash
mkdir -p docs/04_planning/sprints/{sprint_1,sprint_2,sprint_3}
mkdir -p docs/01_requirements/mvp
```

**Brownfield 專屬**:
```bash
mkdir -p docs/06_quality/analysis/{codebase,legacy_system}
mkdir -p docs/08_deployment/migration
```

**Refactoring 專屬**:
```bash
mkdir -p docs/06_quality/refactoring/{before,after,migration_plan}
```

**Integration 專屬**:
```bash
mkdir -p docs/02_architecture/integration/{api_research,authentication,data_mapping}
```

**Performance 專屬**:
```bash
mkdir -p docs/06_quality/performance/{baseline,profiling,optimization}
```

**Testing 專屬**:
```bash
mkdir -p docs/03_testing/{strategy,automation,coverage}
```

**Security 專屬**:
```bash
mkdir -p docs/06_quality/security/{threat_model,vulnerability,compliance}
```

**DevOps 專屬**:
```bash
mkdir -p docs/08_deployment/devops/{pipeline,infrastructure,monitoring}
```

**Documentation 專屬**:
```bash
mkdir -p docs/07_design/documentation/{api_docs,user_guides,developer_guides}
```

**Migration 專屬**:
```bash
mkdir -p docs/02_architecture/migration/{contract_map,compatibility}
mkdir -p docs/08_deployment/{cutover,rollback}
```

---

#### ✅ 3.2 建立 .gitkeep 保留空目錄

**執行命令**:
```bash
find docs -type d -empty -exec touch {}/.gitkeep \;
```

**驗證**:
```bash
find docs -name ".gitkeep"
```

---

### 階段 4: 專案配置檔建立（可選）

#### ✅ 4.1 建立 AISDLC_PROJECT_CONFIG.md（可選）

**執行命令**:
```bash
touch AISDLC_PROJECT_CONFIG.md
```

---

#### ✅ 4.2 填寫專案元數據

**編輯 AISDLC_PROJECT_CONFIG.md**，填入以下內容：

```markdown
# AISDLC 專案配置

## 專案元數據
- **專案名稱**: [請填寫專案名稱]
- **專案代號**: [請填寫專案代號，如 MTP]
- **AISDLC 版本**: v0.01
- **開發情境**: [選擇：Greenfield/Brownfield/Refactoring/Integration/Performance/Testing/Security/DevOps/Documentation/Migration]
- **目標平台**: [選擇：Web/iOS/Android/Cross-Platform/Backend/Other]
- **技術棧**: [請填寫，如 React + Node.js + MongoDB]
- **專案啟動日期**: [YYYY-MM-DD]
- **預計交付日期**: [YYYY-MM-DD]

## 團隊資訊
- **PM/PO**: [姓名]
- **SA (System Analyst)**: [姓名]
- **BA (Business Analyst)**: [姓名]
- **SD-Architect**: [姓名]
- **QA Lead**: [姓名]
- **Tech Lead**: [姓名]
- **團隊規模**: [X 人]

## 文檔產出位置（開發專注版 v0.01）
- **需求文檔**: `docs/01_requirements/`
- **架構設計**: `docs/02_architecture/`
- **測試文檔**: `docs/03_testing/`
- **專案規劃**: `docs/04_planning/`
- **迭代執行**: `docs/05_development/`
- **程式碼品質**: `docs/06_quality/`
- **設計文檔**: `docs/07_design/`
- **部署維運**: `docs/08_deployment/`

## AISDLC 框架設定
- **框架版本**: AISDLC-SDD v0.01
- **工作目錄**: `/path/to/AISDLC_ALL/AISDLC_SDD_v0.01/`
- **情境 SOP**: `scenarios/[scenario]/SOP.md`
- **Agent 配置**: `agent/`
- **文檔模板**: `docs_template/`

## 專案階段追蹤
- **目前階段**: [AISDLC Stage 1: 需求收集]
- **已完成階段**: [ ]
- **下一階段**: [AISDLC Stage 2: 需求驗證]
```

---

#### ✅ 4.3 填寫團隊資訊

**檢查項目**:
- [ ] PM/PO 姓名已填寫
- [ ] SA 姓名已填寫
- [ ] 至少有一位技術負責人（Tech Lead/SD-Architect）
- [ ] QA Lead 姓名已填寫（如有）

---

#### ✅ 4.4 確認文檔產出位置設定

**檢查**:
- [ ] 所有文檔位置均為 `docs/` 開頭
- [ ] 路徑與階段 2 建立的目錄一致

---

### 階段 5: Git 提交

#### ✅ 5.1 確認 .gitignore 存在

**檢查 .gitignore 是否已存在**:
```bash
cat .gitignore
```

**如果不存在，建立它**:
```bash
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
.vscode/
.idea/

# 建置產出
build/
dist/
node_modules/
__pycache__/
*.pyc

# 環境變數
.env
.env.local
EOF
```

---

#### ✅ 5.2 提交初始化變更

**執行命令**:
```bash
git add .
git commit -m "chore: initialize AISDLC-SDD v0.01 project structure

- Add docs/ directory structure (development-focused v0.01)
- Add AISDLC_PROJECT_CONFIG.md (optional)
- Configure for [Greenfield/Brownfield/...] scenario"
```

**驗證**:
```bash
git log --oneline -1
```

---

#### ✅ 5.3 建立初始 Git Tag（可選）

**執行命令**:
```bash
git tag -a v0.0.0 -m "Initial AISDLC-SDD v0.01 project setup"
```

---

### 階段 6: 最終驗證

#### ✅ 6.1 目錄結構完整性驗證

**執行命令**:
```bash
tree -L 2 docs/
```

**預期結果**:
至少包含以下目錄（開發專注版）：
- `docs/01_requirements/`
- `docs/02_architecture/`
- `docs/03_testing/`
- `docs/04_planning/`
- `docs/05_development/`
- `docs/06_quality/`
- `docs/07_design/`
- `docs/08_deployment/`

---

#### ✅ 6.2 配置檔完整性驗證（可選）

**如果建立了 AISDLC_PROJECT_CONFIG.md，執行**:
```bash
cat AISDLC_PROJECT_CONFIG.md | grep "專案名稱"
cat AISDLC_PROJECT_CONFIG.md | grep "開發情境"
cat AISDLC_PROJECT_CONFIG.md | grep "PM/PO"
```

**預期結果**:
- 專案名稱已填寫（不是 `[請填寫]`）
- 開發情境已選擇（不是 `[選擇：...]`）
- PM/PO 已填寫（不是 `[姓名]`）

---

#### ✅ 6.3 Git 提交狀態驗證

**執行命令**:
```bash
git status
git log --oneline -3
```

**預期結果**:
- 工作目錄乾淨（`nothing to commit, working tree clean`）
- 至少有一次提交記錄

---

#### ✅ 6.4 團隊同步確認

**檢查項目**:
- [ ] 團隊成員已知悉 AISDLC_SDD_v0.01/ 為工作目錄
- [ ] 團隊成員已知悉文檔產出位置為 `docs/` 目錄
- [ ] 團隊成員已知悉 8 層編號目錄結構（開發專注版）
- [ ] 團隊成員已 Pull 最新變更（如已 Push 到遠端）

---

## ✅ 完成確認

當所有檢查項目都打勾後，恭喜！專案初始化完成！

### 下一步行動

1. **閱讀情境 SOP**
   ```bash
   cat scenarios/[your-scenario]/SOP.md
   ```

2. **開始執行 AISDLC 流程**
   - Greenfield: 參考 [scenarios/greenfield/SOP.md](../../../scenarios/greenfield/SOP.md)
   - Brownfield: 參考 [scenarios/brownfield/SOP.md](../../../scenarios/brownfield/SOP.md)
   - 其他情境: 參考對應 SOP

3. **建立第一份文檔**
   - 複製 AISDLC 文檔模板到 `docs/` 對應目錄
   - 開始填寫專案需求

---

## 🆘 疑難排解

### 問題 1: docs/ 子目錄缺失

**症狀**:
```bash
ls docs/
# 缺少某些編號目錄
```

**解決方式**:
```bash
# 執行初始化腳本
bash tools/init_project.sh    # macOS/Linux
# 或
powershell tools/init_project.ps1  # Windows
```

---

### 問題 2: 配置檔缺少必填欄位（如果使用配置檔）

**症狀**:
配置檔中仍有 `[請填寫]` 或 `[選擇：...]` 標記

**解決方式**:
重新編輯 `AISDLC_PROJECT_CONFIG.md`，填寫所有必填欄位

---

### 問題 3: 目錄結構與情境 SOP 不匹配

**症狀**:
AISDLC SOP 要求的情境專屬目錄不存在

**解決方式**:
回到 **階段 3**，依照情境類型建立對應的專屬目錄

---

## 📚 相關文檔

- [PROJECT_INITIALIZATION_GUIDE.md](PROJECT_INITIALIZATION_GUIDE.md) - 詳細初始化指南
- [PROJECT_DOCUMENTATION_STANDARDS.md](../standards/PROJECT_DOCUMENTATION_STANDARDS.md) - 文檔產出規範
- [AISDLC_SDD_INIT.md](../../../AISDLC_SDD_INIT.md) - AISDLC 框架初始化
- [docs/README.md](../../../docs/README.md) - docs/ 目錄使用說明

---

**維護者**: AISDLC Framework Team
**最後更新**: 2026-06-06
**版本**: v0.01（開發專注版）
