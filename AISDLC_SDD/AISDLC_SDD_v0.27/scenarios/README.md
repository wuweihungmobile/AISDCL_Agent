# AISDLC-SDD 情境目錄
# Scenarios Directory

**框架版本**: AISDLC-SDD v0.01
**基於**: AISDLC-SDD v0.01
**最後更新**: 2026-04-15

---

## 概覽

AISDLC-SDD v0.01 提供 **10 大開發情境**，每個情境整合 **SDD Spec-First Gate（規格先行閘門）**，確保規格文件在實作前完成並通過 SCG 驗證。

---

## 📂 目錄結構

```
scenarios/
├── README.md                          # 本文件
├── SCENARIO_AGENT_MAPPING.md          # 情境 Agent 配置映射表（含 SDD 技能）
├── SCENARIO_TRANSITION_GUIDE.md       # 情境銜接指南（含 SCG 閘門轉換規則）
├── ERROR_RECOVERY_GUIDE.md            # 錯誤恢復機制指南（含 SCG 失敗恢復）
├── FRONTEND_SPECIFIC_GUIDE.md         # 前端開發特化指引（含 SDD 前端規格要求）
├── SCALING_GUIDE.md                   # 專案規模化調整指引（含 SDD 規格深度調整）
│
├── greenfield/                        # 新專案開發（SCG-0 → SCG-6 完整閘門）
│   ├── SDD_GREENFIELD_ENHANCEMENT.md  # SDD 增強說明
│   ├── SOP.md
│   ├── SOP_DeepDive.md
│   ├── SOP_QuickRef.md
│   ├── Parallel_Execution_Guide.md
│   └── checklists/                    # 輔助清單與模板（9個）
│
├── brownfield/                        # 舊專案維護（逆向規格工程）
│   ├── SDD_BROWNFIELD_ENHANCEMENT.md
│   ├── SOP.md
│   ├── SOP_DeepDive.md
│   └── SOP_QuickRef.md
│
├── refactoring/                       # 系統重構（Business Invariants 保護）
│   ├── SDD_REFACTORING_ENHANCEMENT.md
│   ├── SOP.md
│   ├── SOP_DeepDive.md
│   └── SOP_QuickRef.md
│
├── migration/                         # 技術棧遷移（Contract-Driven 遷移）
│   ├── SDD_MIGRATION_ENHANCEMENT.md
│   ├── SOP.md
│   └── SOP_QuickRef.md
│
├── performance/                       # 效能優化（PBS + SLO 規格先行）
│   ├── SDD_PERFORMANCE_ENHANCEMENT.md
│   ├── SOP.md
│   ├── SOP_DeepDive.md
│   └── SOP_QuickRef.md
│
├── integration/                       # 系統整合（Consumer Contract 驗證）
│   ├── SDD_INTEGRATION_ENHANCEMENT.md
│   ├── SOP.md
│   ├── SOP_DeepDive.md
│   └── SOP_QuickRef.md
│
├── devops/                            # DevOps 建置（SDD Pipeline Spec 先行）
│   ├── SDD_DEVOPS_ENHANCEMENT.md
│   ├── SOP.md
│   ├── SOP_DeepDive.md
│   └── SOP_QuickRef.md
│
├── testing/                           # 測試策略（RTM + Invariant Contract）
│   ├── SDD_TESTING_ENHANCEMENT.md
│   ├── SOP.md
│   ├── SOP_DeepDive.md
│   └── SOP_QuickRef.md
│
├── documentation/                     # 技術文檔（Living Documentation 策略）
│   ├── SDD_DOCUMENTATION_ENHANCEMENT.md
│   ├── SOP.md
│   ├── SOP_DeepDive.md
│   └── SOP_QuickRef.md
│
└── security/                          # 安全合規（STRIDE 威脅模型先行）
    ├── SDD_SECURITY_ENHANCEMENT.md
    ├── SOP.md
    ├── SOP_DeepDive.md
    └── SOP_QuickRef.md
```

---

## 🗺️ 十大情境總覽

| 情境代碼 | 中文名稱 | Primary Agents | SDD 核心閘門 | Enhancement |
|---------|---------|----------------|------------|-------------|
| `greenfield` | 新專案開發 | pm-po, sa-analyst | SCG-0~6 全套 | ✅ |
| `brownfield` | 舊專案維護與改造 | sa-analyst, dev-senior | SCG-0~4（逆向） | ✅ |
| `refactoring` | 系統重構 | sa-analyst, sd-architect | INV Gate + SCG-4 | ✅ |
| `migration` | 技術棧遷移 | sd-architect, sa-analyst | MCM Validate + SCG-3 | ✅ |
| `performance` | 效能優化 | performance-engineer | PBS Gate + SCG-6 | ✅ |
| `integration` | 系統整合 | integration-specialist | Consumer Contract + SCG-3 | ✅ |
| `devops` | DevOps 建置與 CI/CD | devops-engineer | Pipeline Spec + SCG-4 | ✅ |
| `testing` | 測試策略與自動化 | qa-lead | RTM Gate + SCG-5 | ✅ |
| `documentation` | 技術文檔撰寫 | technical-writer | Living Doc + SCG-4 | ✅ |
| `security` | 安全合規 | security-engineer | STRIDE + SCG-5 | ✅ |

---

## 🔴 SDD Spec-First Gate（各情境核心閘門）

SDD 框架在傳統 AISDLC 情境之上，強制要求所有情境遵守 **規格先行** 原則：

| SCG 閘門 | 時機 | 適用情境 |
|---------|------|---------|
| **SCG-0** | 需求凍結前（PRD+FRD 完整性） | 所有情境 |
| **SCG-1** | 設計凍結前（SRD+API Spec） | Greenfield, Brownfield, Migration |
| **SCG-2** | 架構凍結前（C4+ADR） | Greenfield, Refactoring, Migration |
| **SCG-3** | 開發啟動前（OpenAPI 3.1 凍結） | Greenfield, Integration, Migration |
| **SCG-4** | PR Review（實作與規格一致性） | 所有情境 |
| **SCG-5** | 交付前（RTM 100% 覆蓋） | Testing, Security |
| **SCG-6** | 發布前（所有閘門通過） | 所有情境 |

> ⚠️ 閘門不可跳過。若閘門未通過，必須等待修正後再繼續。
> 詳見：`workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`

---

## 📄 SOP 文件說明

每個情境包含最多三層 SOP 文件：

| 文件 | 用途 | 建議閱讀時間 |
|------|------|------------|
| `SOP_QuickRef.md` | 5分鐘快速掌握核心流程 | ~5 分鐘 |
| `SOP.md` | 完整標準作業程序（含 SCG 閘門節點） | ~30 分鐘 |
| `SOP_DeepDive.md` | 深度技術指南（含邊界案例和 SDD 規格細節） | ~60 分鐘 |
| `SDD_*_ENHANCEMENT.md` | SDD 增強說明（新增的 SDD 規格要求） | ~15 分鐘 |

> **建議閱讀順序**: SDD_ENHANCEMENT → QuickRef → SOP → DeepDive（按需）

---

## 📚 根目錄共用指南

| 文件 | 說明 | 使用時機 |
|------|------|---------|
| `SCENARIO_AGENT_MAPPING.md` | 情境 Agent 配置映射表（含 SDD 技能） | 確認情境對應 Primary/Supporting Agents |
| `SCENARIO_TRANSITION_GUIDE.md` | 情境銜接指南（含 SCG 閘門轉換要求） | 在不同情境間切換時 |
| `ERROR_RECOVERY_GUIDE.md` | 錯誤恢復機制指南（含 SCG 失敗恢復） | SOP 執行中遇到錯誤或 SCG 未通過時 |
| `FRONTEND_SPECIFIC_GUIDE.md` | 前端開發特化指引（含 SDD 前端規格） | 涉及前端架構、UI/UX 設計時 |
| `SCALING_GUIDE.md` | 專案規模化調整指引（含 SDD 規格深度） | 不同規模專案調整 SDD 深度時 |

---

## 🚀 快速啟動

使用前必讀：`AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md`

```
Greenfield:    SCG-0 需求凍結 → SCG-1 設計凍結 → SCG-3 Contract → 開發 → SCG-4 PR → SCG-6 發布
Brownfield:    As-Is 分析 → Gap Analysis → SCG-0 → 改造 → SCG-4 PR
Refactoring:   Business Invariants → INV Gate → 重構 → SCG-4 PR
Migration:     Before Arch → MCM → SCG-3 Contract Freeze → 分層遷移
Performance:   SLO 定義 → PBS Gate → 優化 → SCG-6 驗收
Integration:   Consumer Contract → SCG-3 Freeze → 整合 → SCG-4 PR
DevOps:        Pipeline Spec → SCG-4 → 建置 → SCG-6
Testing:       RTM → SCG-5 覆蓋 → 執行 → SCG-6
Documentation: Living Doc Strategy → SCG-4 → 撰寫
Security:      STRIDE → SCG-5 → 審查 → SCG-6
```

---

## 🔗 相關文檔

- [AISDLC_SDD_INIT.md](../AISDLC_SDD_INIT.md) - 框架初始化與 Agent 自動載入配置
- [SDD_Core_Principles.md](../SDD_Core_Principles.md) - SDD 三大支柱原則
- [workflow/sdd-spec-first-gate/](../workflow/sdd-spec-first-gate/) - SCG 閘門執行規範
- [guides/user/onboarding/SCENARIO_SELECTOR.md](../guides/user/onboarding/SCENARIO_SELECTOR.md) - 情境選擇器

---

**維護者**: AISDLC-SDD Framework Team
**SDD 版本**: v0.01
