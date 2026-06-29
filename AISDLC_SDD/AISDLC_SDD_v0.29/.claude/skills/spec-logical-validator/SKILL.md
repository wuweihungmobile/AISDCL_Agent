---
name: spec-logical-validator
description: 執行 Spec 邏輯一致性驗證（SLV-001~014：含 Phase E 學習層 + Phase F 多模態 + 自治迴圈沙箱硬化），在 SCG 格式驗證之前，偵測物理不可行需求、不可測試 AC、業務不變量矛盾、UI/API/DB/C4 跨媒介不一致等邏輯錯誤
user-invocable: true
disable-model-invocation: false
argument-hint: "<scope: full|nfr|ac|invariant|contract|test|dependency|temporal|cache|proposed|verified|multimodal|ui|api|db|c4|SANDBOX_HARDENING_GATE>"
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Spec Logical Validator Skill（SDD 原生 — 規則引擎化）

**在 SCG 格式/完整性驗證之前**，執行邏輯一致性檢查。
格式正確但邏輯不可解的規格，會在此被攔截，避免進入無限實作迴圈。

> **Phase E M4（2026-04-24）變更**：本 Skill 已從「硬編碼 6 條規則」升級為**規則引擎**——核心邏輯不變，規則定義改由 `rules/*.yaml` 動態載入；SLV-007 起的新規則透過 `/slv-generator propose <FPL-ID>` 自動生成 `trust_level: proposed` 草案，人工 review approve 後始成 `verified` 啟用。

---

## 觸發時機

| 時機 | 觸發條件 |
|------|---------|
| **SCG-0 前置** | FRD / AC 草稿完成，即將執行需求凍結閘門前 |
| **SCG-3 前置** | API Contract 草稿完成，即將執行 Contract Freeze 前 |
| **SPEC_AUDIT 觸發** | PR_REVIEW 相同失敗模式 × 3，FSM 自動觸發 |
| **手動觸發** | `/spec-logical-validator` |

---

## 觸發方式

```bash
/spec-logical-validator                  # 執行所有 verified + proposed 規則
/spec-logical-validator nfr              # 只執行 scope=nfr 的規則（SLV-001）
/spec-logical-validator ac               # 只執行 scope=ac 的規則（SLV-002）
/spec-logical-validator invariant        # 只執行 scope=invariant 的規則（SLV-003）
/spec-logical-validator contract         # scope=contract（SLV-004）
/spec-logical-validator test             # scope=test（SLV-005）
/spec-logical-validator dependency       # scope=dependency（SLV-006）
/spec-logical-validator temporal         # scope=temporal（SLV-007 起 — 時序/穩態類）
/spec-logical-validator multimodal       # SLV-008~011 — 跨媒介錨點驗證（UI/API/DB/C4）
/spec-logical-validator ui               # 只執行 SLV-008（UI mockup ↔ FRD AC）
/spec-logical-validator api              # 只執行 SLV-009（OpenAPI ↔ UI form）
/spec-logical-validator db               # 只執行 SLV-010（DB schema ↔ FRD 欄位）
/spec-logical-validator c4               # 只執行 SLV-011（C4 component ↔ SRD 模組）
/spec-logical-validator proposed         # 僅執行 trust_level=proposed 的 draft 規則
/spec-logical-validator verified         # 僅執行 trust_level=verified 的 enforce 規則
```

> **🔴 scope vs anchor_type（DEF-CLDREV-021）**：`ui` / `api` / `db` / `c4` / `multimodal`
> 子命令是依規則的 **`anchor_type`（媒介類別）** 篩選，**非** yaml `scope` 欄——SLV-008~010 的
> `scope=SCG-1`、SLV-011 的 `scope=SCG-2`（見各 rules/*.yaml），其 `anchor_type` 才是 ui/api/db/c4。
> 其餘子命令（nfr/dependency/temporal/contract/test…）才是依 `scope` 篩選。

---

## 前置條件

- 至少完成 FRD 初版（含 AC 章節）
- `docs/01_requirements/` 目錄有對應文件
- Rules 目錄 `.claude/skills/spec-logical-validator/rules/` 至少含 SLV-001~006（builtin）

---

## 規則引擎架構（Phase E M4 / ACT-028）

### Rule 檔案格式

每條規則是 `rules/SLV-NNN.yaml`，必帶欄位：

```yaml
id: SLV-007
name: "時序語義矛盾"
source: "FPL-001 auto-generated 2026-04-24"   # builtin 或 FPL 來源
trust_level: proposed                          # verified | proposed | external
reviewed_by: null                              # 人工 review 通過後填 email
reviewed_at: null                              # 人工 review 通過後填 ISO date
scope: temporal                                # nfr/ac/invariant/contract/test/dependency/temporal/cache/generic
purpose: "..."
scan_targets:
  - "docs/01_requirements/FRD-*.md"
required_qualifiers:
  - "明確的穩態條件（例：『快取命中時』）"
  - "明確的量測統計（P50/P95 + 樣本數）"
failure_examples: [...]
pass_examples: [...]
pattern_regex: "(第[一二三四五六七八九十0-9]+次|N\\+?1).*?%"  # optional
severity: CRITICAL
blocks_scg: true
source_fpl: FPL-001                            # 溯源（若由 slv_generator 產生）
```

### Trust Level 語意

| Trust Level | 意義 | SCG 行為 |
|-------------|------|---------|
| `verified` | 內建規則或已通過 sa-analyst review | CRITICAL FAIL 阻塞 SCG |
| `proposed` | `/slv-generator propose` 自動生成，待人工審核 | 報告中標記為 🟡 Advisory，**不阻塞** SCG |
| `external` | 跨專案 Hub 拉入規則（Phase F） | 標記 🟣 Quarantine，人工確認前不阻塞 |

> **關鍵原則**：proposed / external 規則**絕不可**自動升級為 verified。升級必須透過：
> 1. 人工編輯 YAML，填寫 `reviewed_by` 與 `reviewed_at`，將 `trust_level` 改為 `verified`；或
> 2. FSM 走 `LEARNING_COMMIT → exit_learning_commit("approved")` 流程（記錄完整審計鏈）。

> **去重閘（DEF-CLDREV-011，治本）**：`/slv-generator propose <FPL>` 落盤時，若該 FPL **已有 id 不同的
> verified 規則**，`write_rule_candidate` 直接 raise `FplAlreadyVerified`（CLI 回 exit 3 + 跳過訊息），
> **不再為已 verified 的 FPL 配新 id 產 proposed 重複**（過去 FPL-001 已升 verified SLV-007 仍重生
> SLV-013/014 之根因）。明確需要變體時以 `--allow-duplicate-fpl` 覆寫。

### 載入流程

```
階段 1：掃描 rules/*.yaml
階段 2：載入並驗證每條規則 schema（id/name/trust_level/scope 必填）
階段 3：依 argument filter（scope / anchor_type〔ui/api/db/c4〕/ trust_level〔proposed/verified〕）篩選
階段 4：依 scope 讀取對應 scan_targets 檔案
階段 5：執行驗證（regex + required_qualifier 檢核）
```

---

## 內建規則清單（verified）

| ID | Name | Scope | 對應舊版 |
|----|------|-------|---------|
| [SLV-001](rules/SLV-001.yaml) | NFR 物理可行性 | nfr | 原 SKILL.md SLV-001 |
| [SLV-002](rules/SLV-002.yaml) | AC 可測試性 | ac | 原 SKILL.md SLV-002 |
| [SLV-003](rules/SLV-003.yaml) | Business Invariant 矛盾偵測 | invariant | 原 SKILL.md SLV-003 |
| [SLV-004](rules/SLV-004.yaml) | API Contract vs FRD 相容性 | contract | 原 SKILL.md SLV-004 |
| [SLV-005](rules/SLV-005.yaml) | Test Contract 可達性 | test | 原 SKILL.md SLV-005 |
| [SLV-006](rules/SLV-006.yaml) | API 依賴循環偵測 | dependency | 原 SKILL.md SLV-006 |

## 學習層已升級規則清單（verified — 完成 review）

| ID | Name | Scope | 來源 | Review 紀錄 |
|----|------|-------|------|------------|
| [SLV-007](rules/SLV-007.yaml) | 時序語義矛盾（N+1 vs N 無穩態條件） | temporal | FPL-001（ACT-028 首次產出） | wu.weihung@gmail.com @ 2026-04-24 |

> **審計鏈 Reference（SLV-007）**：此規則是 Phase E M4 學習層自動化鏈路的首個
> 完整範例，流程為 `FPL-001 → propose_slv_from_fpl → SLV-007.yaml(proposed)
> → 人工 review → 填寫 reviewed_by/reviewed_at → trust_level=verified → SCG enforce`。
> 後續透過 FSM `enter_learning_commit → exit_learning_commit("approved")` 落在
> `learning_commit_tracking.proposals_history` 的事後審計鏈紀錄，可跨 session 回查。

## proposed / advisory 規則清單（trust_level=proposed — 待 review，🟡 不阻塞 SCG）

> 引擎動態掃 `rules/*.yaml`；下表為磁碟實有之 proposed 規則，僅作 advisory 報告，
> **絕不**自動升級為 verified（升級須走人工 review 填 reviewed_by/reviewed_at）。

| ID | Name | Scope | 來源 | 備註 |
|----|------|-------|------|------|
| [SLV-008](rules/SLV-008.yaml) | UI mockup ↔ FRD AC 錨點一致 | SCG-1 | Phase F 多模態 | 跨媒介·anchor_type=ui |
| [SLV-009](rules/SLV-009.yaml) | OpenAPI ↔ UI form 錨點一致 | SCG-1 | Phase F 多模態 | 跨媒介·anchor_type=api |
| [SLV-010](rules/SLV-010.yaml) | DB schema ↔ FRD 欄位錨點一致 | SCG-1 | Phase F 多模態 | 跨媒介·anchor_type=db |
| [SLV-011](rules/SLV-011.yaml) | C4 component ↔ SRD 模組錨點一致 | SCG-2 | Phase F 多模態 | 跨媒介·anchor_type=c4 |
| [SLV-012](rules/SLV-012.yaml) | 自治迴圈安全不變量（執行器自身硬化） | SANDBOX_HARDENING_GATE | ACT-061 manual-authored | self-STRIDE 6 類硬化 |
| [SLV-013](rules/SLV-013.yaml) | 時序語義矛盾（proposed 重生） | temporal | FPL-001 auto 2026-06-15 | ⚠️ `superseded_by: SLV-007`（與 verified 全同，不另升級） |
| [SLV-014](rules/SLV-014.yaml) | 時序語義矛盾（proposed 重生） | temporal | FPL-001 auto 2026-06-15 | ⚠️ `superseded_by: SLV-007`（與 verified 全同，不另升級） |

> **SLV-013/014 重複說明（DEF-CLDREV-008）**：兩者係 `slv_generator` 由 FPL-001 二次自動產出之
> proposed 草案，邏輯/scope/regex 與 **verified SLV-007 完全相同**。已於 yaml 標 `superseded_by:
> SLV-007` 並改名破除重複命名；保留為學習層審計痕跡，**不可升級為第二條 verified**。

---

## 執行流程

### 階段 1：素材收集

掃描 `rules/*.yaml`，建立規則快取；依 argument 過濾 scope 與 trust_level。

```
讀取 .claude/skills/spec-logical-validator/rules/*.yaml
讀取 docs/01_requirements/FRD-*.md（AC + NFR 章節）
讀取 docs/01_requirements/INVARIANT-SPEC-*.md（如存在）
讀取 docs/02_architecture/api/CONTRACT-*.yaml（如存在）
讀取 docs/02_architecture/SRD-*.md（如存在）
讀取 docs/03_testing/contracts/TCS-*.md（如存在）
```

### 階段 2：逐規則執行

對每條通過 filter 的規則：
- 執行 `pattern_regex`（若有）於 scan_targets 中搜尋可疑段落
- 對命中段落檢查 `required_qualifiers` 是否滿足
- 分類嚴重程度（CRITICAL / WARNING — CRITICAL 僅限 verified）

### 階段 3：輸出驗證結果

> **分類契約（Phase E M4 / ACT-028 — P1-4 補強）**：每個 rule hit 由
> `slv_generator.classify_result(rule, fail)` 分類為：
>
> | 分類 | 條件 | SCG 行為 |
> |------|------|---------|
> | 🔴 **CRITICAL FAIL** (`blocking`) | fail=True + trust_level=`verified` | **阻塞 SCG** — 退回修正 |
> | 🟡 **ADVISORY** (`advisory`) | fail=True + trust_level ∈ {`proposed`, `external`} | **不阻塞 SCG** — 僅報告提醒，sa-analyst review 時作為 approve 證據 |
> | ✅ **PASS** (`pass`) | fail=False | 繼續下一規則 |
>
> 實作單一真相：`tools/fsm_runtime/slv_generator.py:classify_result`；SKILL 報告產出層與任何未來 rule-engine 實作都必須依此函式分類，不可自行繞道。

```markdown
## SLV 驗證結果

**執行日期**: {date}
**執行範圍**: {full / scope / trust_level filter}
**觸發時機**: {SCG-0前置 / SCG-3前置 / SPEC_AUDIT / 手動}
**載入規則**: verified={N}, proposed={M}, external={K}

### 通過項目 ✅
- SLV-001: NFR 物理可行性（verified）— 全部通過
- SLV-006: 依賴循環（verified）— 無循環

### 失敗項目 🔴 CRITICAL FAIL（verified, 阻塞 SCG）
| 規則 | 位置 | 問題描述 | 嚴重程度 |
|------|------|---------|---------|
| SLV-002 | FRD-OrderSystem.md L87 | AC-003-1 使用模糊詞彙「很快」 | CRITICAL |

### 🟡 ADVISORY（proposed / external, **不阻塞** SCG）
| 規則 | 位置 | 問題描述 | 建議動作 |
|------|------|---------|---------|
| SLV-008 (proposed) | FRD-OrderSystem.md L120 | AC-015-1 對應的 UI mockup 缺 `anchor:ui` 標記（UI mockup ↔ FRD AC 錨點不一致） | 建議補充錨點；等 sa-analyst review SLV-008 後改為強制 |

### 結論
🔴 SLV 未通過（1 個 verified CRITICAL 問題）
→ **SCG 閘門被阻塞**，請修正後重新執行
→ 另有 1 個 advisory 建議優先處理

### 修正指引
1. AC-003-1：將「很快」改為具體量化數值，例如「P95 < 200ms」
```

---

## 阻塞行為

```yaml
blocking_behavior:
  on_verified_critical_fail:
    - "SCG 閘門阻塞（禁止進入人工審查）"
    - "退回對應 Agent 修正"
    - "記錄 retry_count（計入 SCG retry budget）"

  on_proposed_fail:
    - "僅輸出 Advisory（報告標記 🟡），不阻塞 SCG"
    - "Rule accumulates evidence — sa-analyst review 時作為 approve 決策依據"

  on_external_fail:
    - "輸出 🟣 Quarantine 建議，不阻塞 SCG"
    - "Phase F Hub 啟用後才會有 external 規則"

  on_warning_only:
    - "SCG 閘門允許繼續"
    - "Warning 記錄至驗證報告"
    - "下一 Sprint 前必須處理"

  on_all_pass:
    - "繼續執行 SCG 格式/完整性驗證（spec_compliance_check）"
```

---

## 強制產出

| 產出物 | 路徑 | 說明 |
|--------|------|------|
| SLV 驗證報告 | `build/reports/verification/SLV-{date}-{gate}.md` | 每次執行必產出 |

---

## Phase E M4 學習閉環（ACT-028）

當 FSM 偵測到 ESCALATION 且根因為「SLV 未捕獲的 Spec 歧義」：

```
1. Orchestrator 分析 abort_report → 產出 FPL 條目（knowledge/failure-patterns/FPL-NNN-*.md）
2. 呼叫 tools/fsm_runtime/slv_generator.py:
     python -m tools.fsm_runtime.slv_generator propose FPL-NNN
   → 產出 rules/SLV-MMM.yaml（trust_level: proposed）
3. FSM enter_learning_commit(fpl_id, proposed_slv_id) → LEARNING_COMMIT state
4. 人工 review YAML：
     - 確認 pattern_regex / required_qualifiers 合理
     - 填 reviewed_by, reviewed_at, 改 trust_level: verified
5. FSM exit_learning_commit("approved") → RELEASE（下次 session 規則生效）
   or exit_learning_commit("rejected") → ESCALATION（人工 triage）
```

---

## 多模態擴充（Phase F M4 / ACT-031）

新增 SLV-008~011 透過 `<!-- anchor:<modality>:<id> -->` 機制驗證跨媒介一致性。

### 觸發點

| 時機 | 觸發條件 |
|------|---------|
| **SCG-1 前置** | FRD 含任一 `anchor:ui` 或 `anchor:api` 或 `anchor:db` |
| **SCG-2 前置** | SRD 含任一 `anchor:c4` |
| **CI/CD** | `cicd/SDD_CICD_BASE_LAYER.md` 的 Multimodal SpecTrace step |

### 執行入口

```bash
python -m tools.fsm_runtime.multimodal_validator <spec_paths...> \
    [--backend session|claude-api|minimax] [--strict]
```

- 預設 `session` backend（零外部依賴，OPEN-F.3 RESOLVED）
- `--strict` 才會以 exit 1 阻擋 PR；無此 flag 為 advisory（per Rule 9.11.3）
- SLV-008~011 預設 `trust_level: proposed` → 不阻 SCG，僅報告

### Anchor 規格

詳見 [`docs_template/sdd/architecture/SPEC-ANCHOR-TEMPLATE.md`](../../../docs_template/sdd/architecture/SPEC-ANCHOR-TEMPLATE.md)。

| Modality | 對應 artifact 路徑 |
|----------|-------------------|
| `ui` | `docs/99_media/ui/<kebab-id>.{html,md,png,svg}` |
| `api` | `docs/02_architecture/api/*.yaml` 內 `paths.<PATH>.<method>` |
| `db` | `docs/07_design/db/{schema.sql,*.yaml}` 內 CREATE TABLE / `<table>:` |
| `c4` | `docs/02_architecture/C4-*.md` 內 Component(...) / Mermaid 節點 |

### Backend 切換

| Backend | 用途 | 限制 |
|---------|------|------|
| `session` | 預設；HTML/Markdown/SQL/YAML 純規則解析 | PNG/JPG 僅檢查存在；信心度 0.5 |
| `claude-api` | Vision 解析 PNG mockup | stub；待 SDK + key 配置後啟用 |
| `minimax` | OPEN-F.3 補述保留 | stub；NotImplementedError |

---

## 相關 Skill / 工作流

- `/sdd-gate` — SLV 的結果影響 SCG 閘門是否可進入
- `/spec-compliance-check` — SLV PASS 後才執行格式驗證
- `tools/fsm_runtime/slv_generator.py` — Phase E M4 規則生成器（ACT-028）
- `tools/fsm_runtime/multimodal_validator.py` — Phase F M4 多模態驗證入口（ACT-031）
- [SDD_FSM_ENGINE.md](../../../workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md) — FSM 狀態定義（LEARNING_COMMIT / SPEC_AUDIT 觸發）
- [SDD_ESCALATION_PROTOCOL.md](../../../workflow/sdd-escalation/SDD_ESCALATION_PROTOCOL.md) — 矛盾確認後退場
- [FPL-INDEX.md](../../../knowledge/failure-patterns/FPL-INDEX.md) — Failure Pattern Library
- [SPEC-ANCHOR-TEMPLATE.md](../../../docs_template/sdd/architecture/SPEC-ANCHOR-TEMPLATE.md) — Phase F 多模態 anchor 規格

---

**基於**: AISDLC-SDD v0.29（Phase E M4 / ACT-028 規則引擎化 + Phase F M4 / ACT-031 多模態擴充）
**對應藍圖**: SDD_improving_Automation_04.md §ACT-028 + SDD_improving_Automation_05.md §伍 ACT-031（均已歸檔 ../../../build/planning/archive/）
