# AISDLC-SDD 框架升版 SOP

**文件版本**: v0.01
**適用範圍**: AISDLC-SDD v0.01 → 未來版本升版
**最後更新**: 2026-04-15

---

## 📋 升版前必讀

升版 AISDLC-SDD 框架時，必須同時維護：
1. **本文件**（SOP 流程）
2. **`AISDLC_SDD_UPGRADE_CHECKLIST.md`**（逐項勾選清單）

⚠️ **強制規則**：所有升版步驟完成後，CHECKLIST 必須全部打勾，升版才算完成。

---

## 升版資訊填寫

升版開始前填寫：

```
源版本: v0.[  ]
目標版本: v0.[  ]
升版日期: YYYY-MM-DD
執行者: [名稱]
升版原因: [簡述]
```

---

## 階段 1：升版前準備

### 1.1 備份現有版本
```bash
# 建立備份
tar -czf releases/backups/AISDLC_SDD_v[OLD]_backup_$(date +%Y-%m-%d).tar.gz \
  AISDLC_SDD_v[OLD]/

# 驗證備份
ls -la releases/backups/
```

### 1.2 確認當前版本完整性
- 執行 `AISDLC_SDD_UPGRADE_CHECKLIST.md` 中的「升版前驗證」清單
- 確認所有 SCG 閘門文件完整
- 確認 CLAUDE.md 引用的文件存在

### 1.3 建立升版分支（git）
```bash
git checkout -b upgrade/v[OLD]-to-v[NEW]
```

---

## 階段 2：框架內容升版

### 2.1 建立新版本目錄
```bash
cp -r AISDLC_SDD_v[OLD]/ AISDLC_SDD_v[NEW]/
```

### 2.2 更新版本號（批次替換）
需要更新版本號的檔案：
- `AISDLC_SDD_INIT.md`：更新 `framework_version`
- `SDD_Core_Principles.md`：更新版本
- `FILE_DIRECTORY_RULES.md`：更新版本
- 所有 Agent YAML：更新 `version` 欄位
- 所有 Skills SKILL.md：更新版本
- `CLAUDE.md`（專案根目錄）：更新框架版本

### 2.3 執行新增改善項目
依升版規劃文件（`build/planning/active/`）逐項執行。

### 2.4 更新 SDD_VERSION_HISTORY.md
在版本歷程中新增當前版本的變更記錄。

---

## 階段 3：驗證

### 3.1 結構驗證
確認以下目錄存在且完整：
- `agent/core/`（7 core agents）
- `agent/specialized/`（14 specialized agents）
- `scenarios/`（10 scenarios + 跨場景指南）
- `workflow/core/`（8 workflows）
- `workflow/scenario-specific/`（13 workflows）
- `docs_template/sdd/`
- `prompts/`
- `cicd/`（5 SDD CI/CD 規格）

### 3.2 SCG 框架驗證
確認所有 SCG 閘門文件存在：
- `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`
- SCG-0~6 的驗證標準已定義

### 3.3 CLAUDE.md 更新
更新專案根目錄 `CLAUDE.md` 中的：
- 框架版本號
- SDD 轉型狀態
- 新增的功能說明

---

## 階段 4：打包發布

### 4.1 建立發布包
```bash
# 建立發布目錄
mkdir -p releases/v[NEW]/

# 打包
tar -czf releases/v[NEW]/AISDLC_SDD_v[NEW]_release_$(date +%Y-%m-%d).tar.gz \
  AISDLC_SDD_v[NEW]/

# 生成校驗碼
sha256sum releases/v[NEW]/AISDLC_SDD_v[NEW]_release_*.tar.gz > \
  releases/v[NEW]/AISDLC_SDD_v[NEW]_release_*.tar.gz.sha256
```

### 4.2 建立發布說明
在 `releases/v[NEW]/` 建立 `RELEASE_NOTES_v[NEW].md`，包含：
- 新增功能清單
- 改善項目清單
- 破壞性變更（若有）
- 升版指引

---

## 階段 5：完成確認

- 更新 `AISDLC_SDD_UPGRADE_CHECKLIST.md` 所有項目打勾
- 更新 `SDD_VERSION_HISTORY.md` 新增版本記錄
- Commit 所有變更

```bash
git add .
git commit -m "chore: 升版 AISDLC-SDD v[OLD] → v[NEW]"
```

---

## ⚠️ 注意事項

1. **不可跳過備份步驟**：備份遺失無法復原
2. **CLAUDE.md 必須更新**：版本號不一致會導致框架混亂
3. **SDD_VERSION_HISTORY.md 必須更新**：版本歷程是升版驗證的一部分
4. **發布包必須建立**：沒有發布包等於升版未完成

---

**最後更新**: 2026-04-15
**維護者**: AISDLC-SDD Framework Team
