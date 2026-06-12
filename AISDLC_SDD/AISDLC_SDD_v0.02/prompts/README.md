# AISDLC-SDD Prompts

**版本**: v0.01（SDD 版）
**最後更新**: 2026-04-15

AISDLC-SDD 使用者指令集，涵蓋快速啟動、完整流程範例、10 個場景專用指令。

---

## 目錄結構

```
prompts/
├── quick-start/                    ← 快速開始指引
│   ├── 5-minute-start.md           ← 5 分鐘體驗 SDD Spec-First
│   ├── common-commands.md          ← 常用指令速查（含 SCG 閘門）
│   ├── scenario-quick-reference.md ← 10 場景快速啟動指令
│   └── troubleshooting-quick-guide.md ← SDD 常見問題解決
│
├── complete-flow/                  ← 完整流程範例
│   ├── end-to-end-greenfield-example.md ← Greenfield 端到端範例（含所有 SCG）
│   └── multi-scenario-combination-example.md ← 多情境組合範例
│
└── scenario-prompts/               ← 10 個場景專用指令集
    ├── README.md
    ├── greenfield-prompts.md
    ├── brownfield-prompts.md
    ├── refactoring-prompts.md
    ├── documentation-prompts.md
    ├── testing-prompts.md
    ├── devops-prompts.md
    ├── integration-prompts.md
    ├── migration-prompts.md
    ├── performance-prompts.md
    └── security-prompts.md
```

---

## 建議使用順序

1. **新手入門** → [quick-start/5-minute-start.md](quick-start/5-minute-start.md)
2. **選擇場景** → [quick-start/scenario-quick-reference.md](quick-start/scenario-quick-reference.md)
3. **執行指令** → [scenario-prompts/](scenario-prompts/) 對應場景
4. **完整範例** → [complete-flow/](complete-flow/) 參考完整流程
5. **遇到問題** → [quick-start/troubleshooting-quick-guide.md](quick-start/troubleshooting-quick-guide.md)
