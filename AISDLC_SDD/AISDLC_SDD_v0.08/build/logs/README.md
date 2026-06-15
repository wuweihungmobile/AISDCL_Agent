---
title: Build Logs Directory
version: v0.01-SDD
updated: 2026-04-16
---

# build/logs/ — 建置日誌目錄

本目錄存放 AISDLC-SDD 框架執行過程中產生的日誌文件。

## 日誌類型

| 日誌類型 | 命名格式 | 說明 |
|---------|---------|------|
| SCG 閘門驗證日誌 | `SCG-{N}_gate_{YYYY-MM-DD}.log` | 各 SCG 閘門執行結果 |
| CI/CD 執行日誌 | `cicd_{scenario}_{YYYY-MM-DD}.log` | CI/CD pipeline 執行紀錄 |
| 追溯鏈驗證日誌 | `traceability_{YYYY-MM-DD}.log` | verify_traceability.sh 執行輸出 |
| QA 稽核日誌 | `qa_audit_{YYYY-MM-DD}.log` | QA 稽核過程紀錄 |

## 使用說明

日誌文件由以下工具自動產生：
- `tools/verify_traceability.sh` — 追溯鏈驗證
- `.github/workflows/` CI/CD pipelines — 自動化閘門驗證

日誌文件不納入 git 版本控制（應在 `.gitignore` 中排除 `build/logs/*.log`）。

## 目錄狀態

初始建立時為空目錄。正式執行 CI/CD 或工具腳本後，日誌文件將自動產生於此。
