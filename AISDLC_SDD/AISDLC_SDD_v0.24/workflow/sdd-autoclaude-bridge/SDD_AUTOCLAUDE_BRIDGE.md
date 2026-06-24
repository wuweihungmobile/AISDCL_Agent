# SDD_AUTOCLAUDE_BRIDGE — SDD 文件 → AutoClaude Playbook 標準作業（Phase Z / ACT-162）

> **版本**：v0.02（Phase Z：AutoClaude 執行引擎橋接，ACT-162~171）
> **依據**：monorepo `docs/04_planning/AutoSDD_improving_01.md`（已凍結，2026-06-12）
> **配套 Agent**：`agent/specialized/sdd-playbook-compiler-zh.yaml`
> **配套規則**：`governance/rules/R-9.38-playbook-translation-fidelity.yaml`

---

## 1. 目的與邊界

把已凍結的 SDD 規格（TEST-CONTRACT-SPEC，AC→AT 100% 映射）編譯為 AutoClaude
標準 playbook YAML，交由 AutoClaude 微核心引擎自動執行實作與雙重驗證，形成
「規格 → 執行 → 驗證 → 回饋」全自動閉環。

**邊界（不可越）**：
- 規格未達 `SPEC_FROZEN`（`fsm_state.frozen_stages` 為空且 `current_state`
  未達凍結後狀態）→ 編譯器 fail-closed 拒絕（Spec-First Gate）。
- 編譯產物 = 待審工件：兩段之間必須人工 review（SCG-4 精神），凍結後才執行。
- 🔴 人工確認點不可由 AutoClaude 自動跳過（Rule 8 / R-9.5）。

## 2. 標準作業流程（compile-then-run 兩段式）

```
[第一段：編譯]（在 AutoClaude/ 目錄）
python -m autoclaude.tools.sdd_compile \
    --spec-dir <SDD 專案 docs/ 路徑> \
    --out playbooks/sdd_bridge.yaml \
    --project <專案名> [--test-path tests]

  exit 0=成功 / 2=規格未凍結 / 3=規格遭汙染(SPEC_TAINTED) / 4=缺檔或無契約

[人工檢視點] review 生成的 YAML（step_id / expected_output_regex /
             evaluator_command 白名單模板 / weak_regex audit log）

[第二段：執行]
python -m autoclaude playbooks/sdd_bridge.yaml [--fresh]
  → SddGovernancePlugin（PRIORITY=45）自動啟用：
    SCG 閘門守門（越閘 deny）/ 契約違反記帳 / spec digest 防 drift /
    sdd_governance 掛入 checkpoint
```

## 3. 轉譯契約（AT↔step 100% 雙向映射，R-9.38）

| SDD 來源 | PlaybookTask 欄位 | 規則 |
|----------|------------------|------|
| AT-XXX-Y-Z | `step_id` | `sdd-{scenario}-{at_id}`（kebab-case 全 playbook 唯一） |
| Gherkin Given/When | `prompt` | 「依下列契約實作並使測試通過」模板 + 規格出處 digest |
| Gherkin Then | `expected_output_regex` | 引號字面值 / 狀態碼推導；不可推導 → `\bPASS(ED)?\b` 並標 weak_regex 入 audit log |
| AT 測試類型 | `evaluator_command` | 僅白名單模板 `python -m pytest {path} -k "{at}" -q` |
| Unit/Integration/Contract → SCG-4；E2E → SCG-5 | `max_retries` | SCG-4=5 / SCG-5=2（對齊 RETRY_LIMITS） |
| 同 AC 連續 AT | `maintain_context` | 同 AC=true / 跨 AC=false |

**保真驗收**：playbook steps 數 = 規格 AT 條數；雙向可追溯（step_id ↔ at_id）；
缺漏或多餘 → R-9.38 違反 → `SPEC_AUDIT`。

## 4. 治理回路（AutoClaude 側 ↔ SDD 側）

| AutoClaude 事件 | SDD 對應 |
|----------------|---------|
| `SDD-VIOLATION[at_id]`（ErrorClass.SDD_CONTRACT_VIOLATION） | 契約違反記入 `sdd_governance.contract_violations` |
| 同模式違反 ≥3 | `IBrain.decide_escalation` 諮詢（鏡像 SCG-4「3 次→SPEC_AUDIT」） |
| `sdd.spec_drift` 事件 | 規格在執行中被改 → SPEC_AUDIT 需求（advisory） |
| ESCALATION_FINAL 等價（演化亦失敗） | checkpoint 全量保存 → 人工接管（不自動恢復） |

## 5. `AUTOCLAUDE_DELEGATED` 觀察態（提案，未落地）

v0.02 **不新增** FSM 狀態（`_HAPPY_PATH` 零修改 → 五軌 TLC 維持有效，N/A）。
落地前置條件（缺一不可，AutoSDD_improving_01.md §6）：
(a) `SDD_FSM_ENGINE.md` delta（入邊自 IMPLEMENTATION / 出邊回 IMPLEMENTATION 或
ESCALATION）+ 納入 `transition_rules.OBSERVATION_STATES`；(b) 同步
`formal/SDD_FSM.tla`（Rule 9.18.1）；(c) 五軌 TLC 預跑全綠 + PR 附
TLC_DISTINCT/GENERATED/DEPTH 輸出。
