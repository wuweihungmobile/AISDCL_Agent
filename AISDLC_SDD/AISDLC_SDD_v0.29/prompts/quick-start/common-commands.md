# AISDLC-SDD v0.01 常用指令速查

**版本**: v0.01（SDD 版）
**用途**: SDD Spec-First 最常用指令的快速參考
**最後更新**: 2026-04-15

---

## 🚀 啟動與初始化

### 框架初始化
```
請載入 AISDLC-SDD v0.01 框架。
執行指令：請閱讀並載入 AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md
```

### 查看可用情境
```
請列出 AISDLC-SDD v0.01 所有可用的 10 個情境及其 SCG 閘門說明。
```

### 情境選擇協助
```
我不確定應該使用哪個 SDD 情境。

我的任務是：[描述你的任務]

請協助我選擇最適合的情境，並說明需要通過哪些 SCG 閘門。
```

---

## 🔴 SCG 閘門指令

### 執行 SCG 閘門驗證
```
請執行 SCG-[0~6] 閘門驗證。

待驗證文件：
- [文件路徑或內容]

驗證標準：[使用預設標準]
```

### SCG 閘門狀態查詢
```
請列出當前專案所有 SCG 閘門的狀態。
顯示：已通過 / 待驗證 / 尚未執行
```

### 閘門快速參考
| Gate | 時機 | 強制文件 |
|------|------|---------|
| SCG-0 | 需求凍結前 | PRD + FRD 完整性 |
| SCG-1 | 設計凍結前 | SRD + API Spec |
| SCG-2 | 架構凍結前 | C4 圖 + ADR |
| SCG-3 | 開發啟動前 | OpenAPI 3.1 凍結 |
| SCG-4 | PR Review | 實作與規格一致性 |
| SCG-5 | 交付前 | RTM 100% 覆蓋 |
| SCG-6 | 發布前 | 所有閘門通過 |

---

## 📊 執行 Workflows

### 啟動場景 Workflow
```
請執行 [情境名稱]-complete-flow workflow。

[提供必要的輸入資訊]
請在每個 SCG 閘門處等待我確認後才繼續。
```

### 從特定階段開始
```
我已經完成了 SCG-[N] 閘門驗證。

請從下一個階段繼續執行，當前規格文件位置：[路徑]
```

---

## 🤖 Agent 調用

### 調用特定 Agent
```
請調用 [agent-name] agent 協助我。

任務：[描述任務]
SDD 上下文：[當前 SCG 狀態 / 規格文件路徑]
```

### 核心 Agent 快速調用

#### SA 分析師 — 需求 + 逆向規格工程
```
請 SA 分析師協助我：[需求分析 / 逆向規格工程 / Gap Analysis]

輸入：[需求素材 / 現有代碼路徑]
```

#### SD 架構師 — As-Is/To-Be + ADR
```
請 SD 架構師協助我：[架構設計 / As-Is SRD / C4 圖 / ADR 生成]

SRD 路徑：[路徑]
```

#### QA 測試師 — RTM + Invariant Contract
```
請 QA 測試師協助我：[RTM 生成 / Invariant Test Contract / 測試規格]

FRD 路徑：[路徑]
```

#### Code Analyzer — Tech Debt 規格化
```
請 Code Analyzer 協助我分析代碼並規格化技術債（TD-XXX）。

代碼路徑：[路徑]
```

---

## 📝 SDD 文檔生成

### 生成 PRD（SCG-0 前置）
```
請根據以下需求生成 PRD（SDD 格式）。

業務目標：[描述]
需求描述：[描述]
利害關係人：[列表]

生成後請執行 SCG-0 閘門驗證。
```

### 生成 FRD（SCG-0 組件）
```
請根據 PRD 生成 FRD（SDD 格式）。

PRD 位置：[路徑]
包含：User Stories, Acceptance Criteria, Business Invariants
生成後請確認 SCG-0 所有項目已通過。
```

### 生成 SRD + C4（SCG-1~2）
```
請根據 FRD 生成 SRD 和 C4 架構圖（SDD 格式）。

FRD 位置：[路徑]
技術棧：[已選定]
包含：As-Is/To-Be SRD, C4 Model, ADR 清單
```

### 生成 OpenAPI 3.1（SCG-3 Contract Freeze）
```
請為以下 API 生成 OpenAPI 3.1 規格（Contract Freeze）。

API 模組：[模組名稱]
參考 SRD：[路徑]
凍結後：不可在 SCG-3 通過前變更 API 簽名
```

### 生成 RTM（SCG-5）
```
請生成 RTM 需求追蹤矩陣。

FRD 路徑：[路徑]
測試案例路徑：[路徑]
目標：100% 覆蓋所有 F-XXX 需求
```

### 生成 ADR
```
請生成 ADR（架構決策記錄）。

決策主題：[主題]
背景：[為什麼需要做這個決策]
選項：[列出考慮過的選項]
決策：[最終選擇]
```

---

## ✅ 驗證與檢查

### 規格合規性檢查
```
請執行 spec-compliance-check。

文件類型：[PRD/FRD/SRD/API]
文件路徑：[路徑]
```

### RTM 完整性驗證
```
請執行 rtm-generate workflow 並驗證 RTM 完整性。

目標：每個 F-XXX 需求都有對應的測試案例（TC-XXX）
```

### API Contract 凍結確認
```
請確認 API Contract 是否符合 SCG-3 凍結標準。

OpenAPI 規格：[路徑]
確認後將標記為 Contract Frozen，後端實作才可開始。
```

---

## 🔖 快速參考表

| 需求 | 指令關鍵字 | Agent | SCG 閘門 | 產出 |
|------|-----------|-------|---------|------|
| 需求分析 | requirements-extraction | SA 分析師 | SCG-0 | PRD, FRD |
| 逆向規格 | as-is-reverse-spec | SA + SD | - | As-Is SRD |
| Gap 分析 | gap-analysis | SA 分析師 | SCG-0 | Gap Analysis |
| 架構設計 | system-design | SD 架構師 | SCG-1~2 | SRD, C4, ADR |
| API 規格 | contract-generate | SD 架構師 | SCG-3 | OpenAPI 3.1 |
| RTM 生成 | rtm-generate | QA 測試師 | SCG-5 | RTM |
| 技術債 | tech-debt-spec | Code Analyzer | - | TD-XXX 清單 |
| 閘門驗證 | sdd-gate | 自動 | 各 SCG | 驗證報告 |

---

**版本**: v0.01（AISDLC-SDD）
**最後更新**: 2026-04-15
**提示**: 記住 Spec-First 原則：規格文件通過 SCG 閘門後才進入下一階段！
