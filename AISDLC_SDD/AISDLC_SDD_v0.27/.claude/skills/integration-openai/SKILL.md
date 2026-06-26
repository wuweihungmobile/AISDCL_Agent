---
name: integration-openai
description: OpenAI API 整合，ADR 記錄 AI 策略，Prompt Contract 設計先行，NFR 成本量化，RTM 追蹤
user-invocable: true
disable-model-invocation: false
argument-hint: "<use_case: chat|embedding|vision|function-calling> [model: gpt-4o|gpt-4o-mini|claude]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Integration OpenAI Skill（SDD 原生）

AI API 整合在 SDD 中必須設計先行：AI 使用策略需有 ADR（含成本估算），Prompt 設計必須以 Prompt Contract 形式凍結（防止 Prompt Injection），AI 行為需要量化 NFR（回應品質 / 延遲 / 成本上限），整合結果需 RTM 追蹤。

---

## 觸發方式

```bash
/integration-openai chat
/integration-openai embedding
/integration-openai function-calling
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 SCG-1 通過 | AI 功能架構確定 | SRD 含 AI 整合章節 |
| FRD AI 需求 | AI 功能已定義為 F-XXX | 含 AC（回應品質 / 延遲 / 成本）|
| NFR-AI 量化 | AI 性能需求量化 | NFR-AI-001（延遲）/ NFR-AI-002（成本）|

---

## 執行流程

### 階段 1：AI 整合策略 ADR

呼叫 `/adr-generate "AI 整合策略"`：

```markdown
# ADR-{NNN}: AI API 整合策略

## Decision
使用 {GPT-4o-mini / Claude Haiku} 作為主要 LLM

## Rationale（對應需求）
| 面向 | 決策 | 依據 |
|------|------|------|
| 模型選型 | GPT-4o-mini | 成本/品質平衡（NFR-AI-002：月成本 < $X）|
| 串流模式 | Streaming ON | NFR-AI-001（P99 首 Token < 2s）|
| 成本控制 | max_tokens 限制 | NFR-AI-002（每次呼叫 token 上限）|
| Fallback | 系統降級 | NFR-A001（AI 不可用時降級處理）|

## Security（Prompt Injection 防護）
- System Prompt 硬編碼，不接受用戶直接修改
- 用戶輸入 Sanitize（對應 STRIDE T-002）
- API Key Rotation 週期：90 天
```

---

### 階段 2：Prompt Contract 設計

**文件路徑**：`docs/02_architecture/INTEGRATION-SPEC-AI-Prompt-{System}.md`

```markdown
# Prompt Contract — {System}

**版本**: {N}.{N}（修改 Prompt 需更新版本 + 重新測試）
**對應 STRIDE**: T-002 Tampering（Prompt Injection 防護）

## Prompt 清單（對應 FRD Feature）

### PROMPT-001: 客服 AI 助手（對應 F-AI-001）

**System Prompt**（凍結，不接受用戶修改）:
```
你是 {SystemName} 的客服助手。
你的職責：[具體職責清單]
你不可以：[禁止行為清單，如討論競品、洩漏系統資訊]
當用戶問及不相關問題，禮貌地引導回主題。
```

**User Prompt 模板**:
```
用戶問題：{sanitized_user_input}
```

**輸出規格**:
- 語言：繁體中文
- 最大長度：{NFR-AI-003：max_tokens 設定值}
- 格式：純文字（不含 Markdown）

**品質 AC（對應 RTM）**:
- AC-AI-001-1: 回應不包含系統內部資訊
- AC-AI-001-2: Prompt Injection 嘗試被拒絕

### PROMPT-002: 文本嵌入（對應 F-SEARCH-001）
...
```

---

### 階段 3：NFR 成本監控設計

```markdown
## AI 成本 NFR 監控（對應 NFR-AI-002）

| 監控指標 | 告警閾值 | 對應 NFR |
|---------|---------|---------|
| 日消費 token | > $X/日 | NFR-AI-002（月上限）|
| P99 首 Token 延遲 | > 2000ms | NFR-AI-001 |
| API 錯誤率 | > 1% | NFR-A001 |
```

---

### 階段 4：RTM 更新 🔴

```bash
/rtm-generate update
/spec-compliance-check docs/02_architecture/INTEGRATION-SPEC-AI-Prompt-{System}.md
```

🔴 確認點：Prompt Injection TC 已建立；成本 NFR TC 已建立。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| AI 整合策略 ADR | `docs/02_architecture/adr/ADR-{NNN}-ai-strategy.md` | SCG-2 |
| Prompt Contract | `docs/02_architecture/INTEGRATION-SPEC-AI-Prompt-{System}.md` | SCG-3 後 |

---

**基於**: AISDLC-SDD v0.27
**對應情境**: Integration 場景
