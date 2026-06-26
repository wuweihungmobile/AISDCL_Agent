# AISDLC-SDD DevOps 指令集

**情境**: DevOps — SCG 閘門整合的 CI/CD 自動化
**版本**: v0.01（SDD 版）
**最後更新**: 2026-04-15

---

## 🚀 標準啟動

```
我需要建立 CI/CD Pipeline 並整合 SDD SCG 閘門，使用 SDD DevOps 情境。

載入：AISDLC_SDD_v0.01/scenarios/devops/SDD_DEVOPS_ENHANCEMENT.md

DevOps 需求：
- 目標平台：[GitHub Actions / GitLab CI / Jenkins]
- 環境：[Dev / Staging / Production]
- SCG 閘門整合：[SCG-4 PR Check / SCG-6 Release Gate]
- 技術棧：[描述]
```

## 📊 Pipeline 規格

### Pipeline 設計（含 SCG 閘門）
```
請設計 CI/CD Pipeline 規格，整合 SDD SCG 閘門。

平台：[GitHub Actions]
Pipeline 階段：
1. Build & Lint
2. Unit Tests（RTM 覆蓋率檢查）
3. SCG-4 Check：實作 vs 規格一致性
4. Integration Tests（Contract Testing）
5. Security Scan（OWASP）
6. Staging Deploy
7. SCG-6 Gate：發布前最終驗證
8. Production Deploy

產出：CI/CD Pipeline 規格文件
```

### GitHub Actions 配置
```
請生成 GitHub Actions Workflow 配置（含 SCG 閘門）。

Workflow 要求：
- PR 觸發：執行 SCG-4 Check（實作與 OpenAPI 規格比對）
- Main 觸發：完整 Pipeline + SCG-6 Gate
- 品質閘門：測試覆蓋率 < 80% 則失敗

參考 SDD CI/CD 規格：AISDLC_SDD_v0.01/cicd/SDD_TESTING_CICD.md
```

### SCG-4 PR Check 自動化
```
請設計 SCG-4 PR Review 自動化檢查。

檢查項目：
1. OpenAPI 規格比對（實作端點 vs 規格）
2. 新 API 是否有對應的 Contract Test
3. 是否有未記錄的 ADR 決策

工具：[Spectral / openapi-diff / 自訂 script]
```

### SCG-6 Release Gate
```
請設計 SCG-6 Release Gate（發布前最終驗證）。

Gate 項目：
- 所有 SCG-0~5 狀態：已通過 ✅
- RTM 覆蓋率：100%
- 效能測試：SLO 達標
- 安全掃描：無 Critical 漏洞
- 測試通過率：100%

若任一項目未通過，阻止發布並通知負責人。
```

## 🔄 常見變體

### 快速 CI 基礎設定
```
我只需要基本的 CI（Build + Test），先不考慮完整 SCG 整合。

平台：[GitHub Actions]
最小需求：
- PR 時：Build + Unit Test
- Merge 時：Build + 全測試 + 覆蓋率報告

SCG 整合可以後續逐步加入。
```

### 現有 Pipeline 補充 SCG 閘門
```
我有現有的 CI/CD Pipeline，需要補充 SDD SCG 閘門。

現有 Pipeline：[描述或路徑]

請評估：
1. 可以在哪些步驟加入 SCG-4/SCG-6 檢查？
2. 最小改動方案是什麼？
```
