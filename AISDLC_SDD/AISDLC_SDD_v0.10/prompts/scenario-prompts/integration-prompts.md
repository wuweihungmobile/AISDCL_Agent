# AISDLC-SDD Integration 指令集

**情境**: Integration — Contract-First 第三方服務整合
**版本**: v0.01（SDD 版）
**最後更新**: 2026-04-15

---

## 🚀 標準啟動

```
我需要整合第三方服務，使用 SDD Integration 情境（Contract-First）。

載入：AISDLC_SDD_v0.01/scenarios/integration/SDD_INTEGRATION_ENHANCEMENT.md

整合需求：
- 服務名稱：[Stripe/Firebase/SendGrid/AWS/自訂 API]
- 整合類型：[REST API / Webhook / SDK / GraphQL]
- 目的：[描述業務需求]

SDD 原則：Consumer Contract 必須在整合實作前定義（Contract-First）。
```

## 📊 階段推進

### Consumer Contract 定義
```
請定義與 [服務名稱] 的 Consumer Contract。

我方（Consumer）需要：
- 端點：[列出需要調用的 API 端點]
- 請求格式：[描述]
- 回應格式：[描述]
- 錯誤處理：[需要處理哪些錯誤碼]

產出：Consumer Contract 文件（Pact 格式或 OpenAPI 子集）
凍結後才開始整合實作。
```

### 整合設計（ADR）
```
請為 [服務名稱] 整合生成 ADR。

決策：如何整合 [服務名稱]
背景：[業務需求]
選項：
- 選項 A：直接 SDK 整合
- 選項 B：自建 Wrapper Service
- 選項 C：[其他]

請分析各選項優劣並推薦。
```

### Webhook 處理設計
```
我需要處理 [服務名稱] 的 Webhook 事件。

Webhook 事件：[列出需要處理的事件]
安全要求：[Webhook 簽名驗證方式]

請設計：
- Webhook 接收端點規格（OpenAPI）
- 事件處理流程
- 冪等性設計（防重複處理）
- 錯誤重試策略
```

### 整合測試規格
```
請設計 [服務名稱] 整合測試規格。

測試策略：
- Mock Server（開發/CI 環境）
- Sandbox（測試環境）
- 真實 API（驗收環境）

Consumer Contract Test：
- 驗證我方實作是否符合定義的 Contract
```

## 🔄 常見變體

### Stripe 支付整合
```
請協助設計 Stripe 支付整合（Contract-First）。

需要的功能：
- [結帳/訂閱/一次性付款/退款]

請先定義 Consumer Contract，再設計整合架構。
參考：AISDLC_SDD_v0.01/guides/ 下的相關整合指南
```

### 內部微服務整合
```
我需要整合公司內部的 [服務名稱] 微服務。

現有 API 文件：[路徑或描述]

請建立 Consumer Contract，定義我方需要的最小 API 子集，
並設計防止 Provider 變更破壞我方的契約測試。
```
