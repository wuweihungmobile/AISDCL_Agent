# SDD Scenario Prompts

**版本**: v0.01（SDD 版）
**最後更新**: 2026-04-15

10 個 SDD 場景的指令集，每個場景含：標準啟動指令、階段推進指令、常見變體。

| 檔案 | 場景 | 核心 SDD 特性 |
|------|------|-------------|
| [greenfield-prompts.md](greenfield-prompts.md) | Greenfield | SCG-0~6 完整 Spec-First |
| [brownfield-prompts.md](brownfield-prompts.md) | Brownfield | 逆向規格工程 + Gap Analysis |
| [refactoring-prompts.md](refactoring-prompts.md) | Refactoring | Invariant 保護 + SCG-4 |
| [documentation-prompts.md](documentation-prompts.md) | Documentation | ADR Archaeology + Living Doc |
| [testing-prompts.md](testing-prompts.md) | Testing | RTM 100% + Contract Testing |
| [devops-prompts.md](devops-prompts.md) | DevOps | SCG 閘門整合 Pipeline |
| [integration-prompts.md](integration-prompts.md) | Integration | Consumer Contract-First |
| [migration-prompts.md](migration-prompts.md) | Migration | MCM Validate + 零停機 |
| [performance-prompts.md](performance-prompts.md) | Performance | PBS SLO + SCG-6 PBS Gate |
| [security-prompts.md](security-prompts.md) | Security | STRIDE + SCG-5 Validate |

## 使用方式

1. 選擇對應場景的 prompts 檔案
2. 複製「標準啟動」指令，填入專案資訊
3. 依 SDD 流程推進，在 SCG 閘門等待確認
4. 按需使用「常見變體」指令

## 多場景組合

參考 [../complete-flow/multi-scenario-combination-example.md](../complete-flow/multi-scenario-combination-example.md)
