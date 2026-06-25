# AISDLC-SDD Greenfield 指令集

**情境**: Greenfield — Spec-First 全新專案開發
**版本**: v0.01（SDD 版）
**最後更新**: 2026-04-15

---

## 🚀 標準啟動

```
我要開發一個全新專案，請使用 AISDLC-SDD Greenfield Spec-First 流程。

載入：AISDLC_SDD_v0.01/scenarios/greenfield/SDD_GREENFIELD_ENHANCEMENT.md

專案資訊：
- 專案名稱：[名稱]
- 業務目標：[描述]
- 目標平台：[Web/Mobile/Backend]

SDD 執行順序：PRD → SCG-0 → SRD/C4/ADR → SCG-1~2 → OpenAPI → SCG-3 → 開發
每個 SCG 閘門在通過前等待我確認。
```

## 📊 階段推進

### SCG-0 前：需求分析
```
請執行需求分析，產出 PRD 和 FRD。

需求素材：[截圖/文字/混合]
包含：F-XXX 功能需求 + NFR-XXX 非功能需求 + Business Invariants（若有）

完成後執行 SCG-0 閘門驗證。
```

### SCG-1~2 前：架構設計
```
SCG-0 已通過，請開始架構設計。

請產出：
- SRD（系統需求文檔）
- C4 Context + Container 圖
- ADR-001：[主要技術決策]

完成後依序執行 SCG-1（設計凍結）和 SCG-2（架構凍結）。
```

### SCG-3 前：API Contract
```
SCG-2 已通過，請生成 OpenAPI 3.1 規格（Contract Freeze）。

API 模組：[列出主要模組]
格式：OpenAPI 3.1

凍結後後端實作才可開始。
```

### SCG-5 前：RTM
```
請生成 RTM 並確認覆蓋率達 100%。

對應 FRD 中的所有 F-XXX 需求，每個需求至少有一個 TC-XXX。
```

## 🔄 常見變體

### MVP 快速版
```
我想快速打造 MVP，使用 Greenfield 情境但縮短文檔範圍。

MVP 核心功能：[列出最小集合]
時程：[X 週]

請聚焦必要的 SCG 閘門（SCG-0 和 SCG-3 為最低要求），
其他文件可在 MVP 後補齊。
```

### 平台特化（Web）
```
請使用 sd-web-architect 和 qa-web-tester，執行 Web 平台特化設計。
技術棧偏好：[React/Vue/Next.js] + [Node.js/Python/Go]
```

### 平台特化（Mobile）
```
請使用 sd-mobile-architect 和 qa-mobile-tester，執行 Mobile 特化設計。
目標平台：[iOS/Android/跨平台]
跨平台方案：[React Native/Flutter/原生]
```
