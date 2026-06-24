# guides/user/ - 使用者參考文件目錄
# User Reference Documents Directory

> **👥 人類使用者專用參考文件**
>
> 本目錄包含給 **人類使用者** 閱讀的指南和教學文件。
> 這些文件以易讀、友善的方式幫助使用者理解和使用 AISDLC Framework。

---

**版本**: v0.01
**建立日期**: 2025-12-01
**維護者**: AISDLC Framework Team
**適用範圍**: AISDLC-SDD v0.01+

---

## 📋 目錄說明

### 用途定位

**user/** 目錄用於存放：
- ✅ **易讀、友善的表達方式** - 包含範例、教學、決策樹
- ✅ **給人類使用者閱讀的指南** - 幫助理解和使用 AISDLC
- ✅ **操作指引和最佳實踐** - 流程、標準、技術選型建議

**不應放在此目錄**:
- ❌ 給 AI Agent 使用的技術規範 → 應放在 `guides/system/`
- ❌ 結構化的規則定義 → 應放在 `guides/system/`

---

## 📁 子目錄結構

### 🎓 onboarding/ - 新手入門
**用途**: 幫助新手快速上手 AISDLC Framework

**檔案清單**:
- [QUICK_START_GUIDE.md](onboarding/QUICK_START_GUIDE.md) - 快速上手指南（5 分鐘了解 AISDLC）
- [QUICK_START_TEMPLATES.md](onboarding/QUICK_START_TEMPLATES.md) - 快速啟動範本庫
- [QUICK_WINS_GUIDE.md](onboarding/QUICK_WINS_GUIDE.md) - 快速優化指南
- [SCENARIO_SELECTOR.md](onboarding/SCENARIO_SELECTOR.md) - 情境選擇助手（決策樹）
- [TUTORIAL_MODE.md](onboarding/TUTORIAL_MODE.md) - 教學模式（Learning-by-Doing）

**目標使用者**: 完全新手、初次使用 AISDLC 的開發者

**使用時機**: 專案啟動前、學習階段

---

### 📏 standards/ - 標準與規範
**用途**: 文檔撰寫標準、可讀性指南

**檔案清單**:
- [DOCUMENTATION_READABILITY_GUIDE.md](standards/DOCUMENTATION_READABILITY_GUIDE.md) - 文檔可讀性指南

**目標使用者**: 文件撰寫者、技術文件維護者

**使用時機**: 撰寫文檔時、文檔品質審查時

---

### 🔧 technical/ - 技術指引
**用途**: 技術選型、智能預設值配置

**檔案清單**:
- [SMART_DEFAULTS.md](technical/SMART_DEFAULTS.md) - 智能預設值配置（80/20 原則）

**目標使用者**: 技術決策者、架構師、PM/PO

**使用時機**: Greenfield SOP Stage 3（技術選型階段）

---

### 🔄 process/ - 流程與管理
**用途**: 開發流程、Code Review、協作方式

**檔案清單**:
- [Code_Review_Guidelines.md](process/Code_Review_Guidelines.md) - Code Review 指南

**目標使用者**: 開發者、QA、團隊 Lead

**使用時機**: Stage 7-8（開發與測試階段）、每個 Pull Request 送出後

---

## 🎯 使用場景快速導航

### 📌 我是新手，想快速上手
1. 從 [QUICK_START_GUIDE.md](onboarding/QUICK_START_GUIDE.md) 開始
2. 使用 [SCENARIO_SELECTOR.md](onboarding/SCENARIO_SELECTOR.md) 找到適合的情境
3. 參考 [QUICK_START_TEMPLATES.md](onboarding/QUICK_START_TEMPLATES.md) 使用範本

### 📌 我要選擇技術棧
1. 參考 [SMART_DEFAULTS.md](technical/SMART_DEFAULTS.md) 了解預設值
2. 檢視 [../system/architecture/Web_Architecture_Decision_Tree.md](../system/architecture/Web_Architecture_Decision_Tree.md) 架構決策樹

### 📌 我要撰寫文檔
1. 參考 [DOCUMENTATION_READABILITY_GUIDE.md](standards/DOCUMENTATION_READABILITY_GUIDE.md) 可讀性指南
2. 使用 [../system/quality/Document_Quality_Checklist.md](../system/quality/Document_Quality_Checklist.md) 檢查品質

### 📌 我要進行 Code Review
1. 參考 [Code_Review_Guidelines.md](process/Code_Review_Guidelines.md) 完整指南

---

## 🔄 維護規則

### 新增檔案時

當需要新增使用者參考文件時，請遵循以下決策流程：

```
問題：這個檔案的主要目標讀者和用途是什麼？
│
├─ 新手入門、快速上手、教學 → onboarding/
├─ 文檔撰寫標準、可讀性指南 → standards/
├─ 技術選型、智能預設值、技術建議 → technical/
└─ 開發流程、Code Review、協作方式 → process/
```

### 檔案命名規範

- ✅ 使用友善的名稱: `QUICK_START_GUIDE.md`
- ✅ 強調行動導向: `QUICK_WINS_GUIDE.md`
- ✅ 明確目標受眾: `TUTORIAL_MODE.md`
- ✅ 使用大寫 + 底線（onboarding 檔案）: `SCENARIO_SELECTOR.md`
- ✅ 使用 PascalCase + 底線（其他檔案）: `Code_Review_Guidelines.md`

---

## 📚 相關文檔

- [guides/system/README.md](../system/README.md) - 系統參考文件目錄說明
- [guides/README.md](../README.md) - Guides 總覽與導航
- [FILE_DIRECTORY_RULES.md](../../FILE_DIRECTORY_RULES.md) - 檔案目錄維護規則

---

**最後更新**: 2025-12-01
