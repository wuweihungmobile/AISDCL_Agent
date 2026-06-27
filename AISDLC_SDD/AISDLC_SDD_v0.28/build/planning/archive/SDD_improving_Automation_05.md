# SDD_improving_Automation_05 — Phase F 藍圖草擬（DRAFT）

> **性質**：本文件為 Phase F 藍圖草擬（Blueprint Draft），**尚未啟動、尚未排程**。
> 用途：定義 Phase F 的範疇、交付物、前置條件、依賴、風險與使用者決策點，供後續評審啟動。
>
> **前身**：[SDD_improving_Automation_04.md](SDD_improving_Automation_04.md)（Phase E 全量完成，9.4/10）
> **目標**：從 L4.9（精準有界停機 + 半自動學習）→ **L5.5（跨專案自演化 + 多模態 Spec 一致性）**
> **建立日期**：2026-04-24
> **狀態**：🟢 ACTIVE — OPEN-F.1~F.7 全數 RESOLVED（2026-04-24，使用者採默認答），可進入 Stage 0 Pre-flight
> **本輪聚焦**：ACT-030 Cross-Project Learning Hub + ACT-031 多模態 Spec 驗證
> **藍圖保留**（完整版）：ACT-032 SLV 全自動演化、ACT-033 AI 對話品質 Benchmark

---

## 壹、背景與定位

### 1.1 Phase E 達成狀態（2026-04-24）

| 維度 | Phase D 末 | Phase E 末 | Phase F 目標 |
|------|-----------|-----------|-------------|
| 狀態機完備性 | 10 | 10 | 10 |
| 有界停機精度 | 8 | 9.5 | 9.5 |
| 上下文管理 | 9 | 9.5 | 9.5 |
| Spec 邏輯驗證 | 8.5 | 9.5 | **10**（多模態補齊）|
| Test→Fix 閉環 | 8 | 8.5 | 9 |
| Subagent 隔離 | 3 | 9 | 9 |
| 場景覆蓋 | 8 | 8.5 | 9 |
| 學習能力 | 4 | 8 | **9.5**（跨專案 + 全自動）|
| 生產回饋 | 2 | 8 | 8.5 |
| **總分** | **8.3/10** | **9.4/10** | **9.7~9.8/10** |

### 1.2 Phase F 的兩個核心命題

1. **跨專案學習**（L5 → L5.5）— 單一實例的 FPL/SLV 知識如何安全擴散至多專案，讓新專案「繼承前人教訓」。
2. **多模態 Spec 一致性**（Spec 邏輯驗證 → 多媒介）— 將 SLV 從「文字 Spec vs 文字 Spec」擴充至「UI mockup ↔ FRD / OpenAPI ↔ UI 元件 / DB Schema ↔ API Response」等跨媒介驗證。

### 1.3 Phase E 末遺留問題（Phase F 必須解）

| 編號 | 來源 | 問題 | Phase F 對應 ACT |
|------|------|------|----------------|
| R-F.1 | §7.2 item 1 | ACT-028 SLV 仍需人工 review（半自動） | ACT-032（保留）|
| R-F.2 | §7.2 item 2 | 跨語言/多模態 Spec 驗證未支援 | **ACT-031**（本輪）|
| R-F.3 | §7.2 item 3 | AI 對話品質缺客觀評估 | ACT-033（保留）|
| R-F.4 | §9.1 Hub 策略 | 商業機密治理規格未定義 | **ACT-030**（本輪，治理先行）|
| R-F.5 | §12 Phase F 保留項 | SLV 全自動演化需 LLM backend 成熟 | ACT-032（保留）|

---

## 貳、Phase F 範疇與本輪聚焦

### 2.1 本輪啟動（Scope IN）

| ACT | 名稱 | 優先序 | 預估工時 |
|-----|------|--------|---------|
| **ACT-030** | Cross-Project Learning Hub | P1 | 7 天（含治理規格先行 2 天）|
| **ACT-031** | 多模態 Spec 驗證（UI/Schema/Diagram） | P1 | 10 天 |

### 2.2 藍圖保留（Scope OUT，列入完整版）

| ACT | 名稱 | 阻塞條件 | 最早評估 |
|-----|------|----------|---------|
| ACT-032 | SLV 全自動演化（無需人工 review）| ACT-028 verified 規則累積 ≥ 5 條 + 誤報率統計 | 2026-Q4 |
| ACT-033 | AI 對話品質 Benchmark（Claude 遵 Spec 度）| ACT-031 多模態基礎 + Ground Truth 語料集 | 2027-Q1 |

### 2.3 非目標（明確排除）

- ❌ 取代 Claude Code 原生 context 壓縮（Phase E 已收斂）
- ❌ 引入新語言（Rust / Go）的工具鏈 — 保持 Python + YAML 為唯一實作語言
- ❌ Hub 對公開 internet 暴露任何 HTTP endpoint（延續 §OPEN-10.6 決策精神）

---

## 參、前置條件盤點（Phase F Kick-off 必備）

| # | 前置項 | 當前狀態 | 負責 | 啟動前 Due |
|---|-------|---------|------|-----------|
| P-F.1 | Phase E 全量穩定 7 天（193+14 tests 連續通過）| ⏳ 觀察中（2026-04-24~05-01）| Runtime | 2026-05-01 |
| P-F.2 | Automation_04 歸檔至 archive/ | ⏳ 待本輪藍圖評審後執行 | User | Phase F 啟動日 |
| P-F.3 | 商業機密治理規格文件產出（ACT-030 前置）| ❌ 尚未啟動 | User + Security | 2026-06-15（Hub 啟動前 14 天）|
| P-F.4 | 多模態 LLM 後端選定（ACT-031 前置）| ❌ 尚未啟動 | User | 2026-06-30（ACT-031 啟動前 7 天）|
| P-F.5 | Hub endpoint 載體選定（GitHub repo / 私有 git / S3）| ❌ 尚未啟動 | User | 2026-06-15 |
| P-F.6 | Synthetic Test Project 擴充（支援多模態 fixture）| 🟡 部分（Phase E M2.5 已建立文字基準）| Runtime | 2026-06-30 |
| P-F.7 | Hook 效能預算（§OPEN-10.4）延伸至 Hub pull / 多模態驗證 | 🟡 Phase E 已立 p95 < 200ms 框架 | Runtime | Phase F M2 開工前 |

---

## 肆、ACT-030：Cross-Project Learning Hub（詳細規劃）

### 4.1 目標

單一 AISDLC-SDD 實例可**安全、去識別化、可審計**地參與跨專案 FPL/SLV 共享（讀寫中央 registry），新專案能立即繼承既有失敗模式與驗證規則。

### 4.2 交付物清單（14 項）

| # | 交付物 | 路徑 | 說明 |
|---|-------|------|------|
| **治理層（先行）**|||
| D-30.1 | 商業機密治理規格 | `docs/06_quality/HUB-GOVERNANCE-SPEC.md` | 定義「可 push / 必阻擋」的資料類別、PII 樣式、商業機密 pattern |
| D-30.2 | 去識別化規則庫 | `tools/fsm_runtime/anonymizer_rules.yaml` | 專案名、ID、endpoint URL、人名、IP/Email 正則 |
| D-30.3 | 信任階梯契約 | `knowledge/hub/trust-ladder.md` | external → reviewed → verified 升級流程與簽核 |
| **Client 實作**|||
| D-30.4 | Registry schema | `knowledge/hub-registry.yaml` | hub_endpoint / sync_policy / cache_ttl / trust_on_pull |
| D-30.5 | Hub Sync Client | `tools/fsm_runtime/hub_sync.py` | `pull()` / `push()` / `dry_run()` / `diff()` CLI |
| D-30.6 | PII Scanner | `tools/fsm_runtime/pii_scanner.py` | Pre-push 強制掃描，依 D-30.2 規則 |
| D-30.7 | Anonymizer | `tools/fsm_runtime/anonymizer.py` | 自動替換為 `<PROJECT_A>`, `<ID_NNNN>`；保留語義骨架 |
| D-30.8 | Conflict Resolver | `tools/fsm_runtime/hub_merge.py` | Pull 時與本地 FPL/SLV 衝突的三向合併 |
| **Hub 端（參考實作）**|||
| D-30.9 | Registry 倉儲規格 | `knowledge/hub/REGISTRY-SPEC.md` | Git-based registry（branch-per-rule + PR review）|
| D-30.10 | Push GitHub Action | `.github/workflows/hub-push.yml`（sample）| 二次 PII 掃描；GPG 簽章驗證 |
| **整合層**|||
| D-30.11 | session_start 整合 | `.claude/hooks/session_start.py` | Pull 快取 24h；新規則載入 `trust_level: external` |
| D-30.12 | FSM 狀態擴充 | `transition_rules.py` | 新增 `HUB_SYNC` observation state（非阻塞，不入 happy-path）|
| D-30.13 | CI/CD 規格 | `cicd/SDD_HUB_SYNC.md` | Hub pull dry-run CI、push quarantine pipeline |
| **測試**|||
| D-30.14 | 測試套件 | `tools/fsm_runtime/tests/test_hub_sync.py` | PII scan、anonymize、pull/push、merge conflict、trust ladder |

### 4.3 架構草圖

```
┌──────────────────┐        pull (24h cache)         ┌─────────────────────┐
│  Local AISDLC    │ ────────────────────────────────>│   Hub Registry      │
│  instance A      │                                   │ (Git-based repo)    │
│                  │ <──── external rules ─────────── │                     │
│  ┌─────────────┐ │        (trust_level=external)    │  rules/             │
│  │ PII Scanner │ │                                   │  ├─ SLV-XXX.yaml    │
│  └──────┬──────┘ │                                   │  └─ FPL-XXX.md      │
│         │ fail → quarantine                          │                     │
│  ┌──────▼──────┐ │        push (anonymized)          │  PR-review gate     │
│  │ Anonymizer  │ │ ────────────────────────────────>│  GPG signed         │
│  └─────────────┘ │                                   │                     │
└──────────────────┘                                   └─────────────────────┘
      ▲                                                         ▲
      │ Conflict Resolver                                       │
      └──── 3-way merge (local / hub / base) ───────────────────┘
```

### 4.4 FSM 整合（HUB_SYNC 狀態）

- **類型**：observation state（非阻塞，同 PRODUCTION_SIGNAL / LEARNING_COMMIT）
- **入口**：`FSMRuntime.enter_hub_sync(direction: "pull" | "push")`，需顯式 API 呼叫；happy-path 不包含
- **合法前置狀態**（實作 `HUB_SYNC_ALLOWED_SOURCES`，共 8 個）：
  ```
  {INIT, SCENARIO_DETECT, SPEC_DRAFTING, SPEC_FROZEN,
   RELEASE, RELEASE_READY, LEARNING_COMMIT, HUMAN_PENDING}
  ```
  - **session_start auto-pull 場景**：INIT / SCENARIO_DETECT / SPEC_DRAFTING / HUMAN_PENDING（會話啟動或暫停期間皆可拉新規則）
  - **顯式 push 場景**：SPEC_FROZEN / RELEASE / RELEASE_READY / LEARNING_COMMIT（規格已凍結或交付完成後才允許輸出）
  - **明確排除**：ESCALATION / TERMINATED / TOKEN_BUDGET_CRITICAL / AUTO_COMPACT_PENDING / IMPLEMENTATION（防爆衝期間 Hub 干擾）
- **出口**：`exit_hub_sync(outcome: "success" | "partial" | "failed")`
  - success → 回原狀態（透過 resume_from 記錄）
  - partial → HUMAN_PENDING（衝突待 review）
  - failed → 紀錄 decision_trace 但不升 ESCALATION（Hub 失效不阻本地工作）

### 4.5 治理規則（MUST，§4.2 D-30.1）

| 規則 | 說明 | 違反後果 |
|------|------|---------|
| G-30.1 Pre-push PII 強制 | 具名人員、Email、IP、內部專案名、API token | Push 中止、寫 quarantine |
| G-30.2 商業機密 pattern | 客戶名、契約金額、內部網域、產品代號 | Push 中止、寫 quarantine |
| G-30.3 預設 opt-in | 每次 push 需人工確認（環境變數 `SDD_HUB_PUSH_CONFIRMED=<reason>`）| 未設即 dry-run |
| G-30.4 Pull 預設 external | 所有 pull 規則 `trust_level: external`，Advisory-only 不阻 SCG | 違反即當 verified 使用 |
| G-30.5 升級需 reviewer signoff | external → reviewed → verified 各需人工 YAML 簽核 | 不允許自動升級 |
| G-30.6 Hub endpoint allow-list | `knowledge/hub-registry.yaml` 明列允許 endpoint，非清單內拒連 | 防「投毒 hub」 |

### 4.6 驗收條件

1. **A-30.1**：模擬 2 個專案 — A push 3 條 FPL（含假商業機密），B pull 後：
   - A push 前 PII scanner 擋下 1 條、anonymize 2 條；quarantine 報告完整
   - B pull 後本地 `knowledge/failure-patterns/` 有 2 條 `trust_level: external` 規則
   - B 手動 review 升至 verified，下次 SCG-0 立即生效

2. **A-30.2**：去識別化覆蓋率 — 對 20 條含 PII 的測試 FPL，anonymize 後：
   - 100% PII 替換為 placeholder
   - 語義骨架保留（regex、qualifier、scope 欄位完整）
   - 下游 `slv_generator.propose_slv_from_fpl()` 能正常處理 anonymized 輸入

3. **A-30.3**：衝突合併 — 本地 SLV-007 已 verified，Hub 有同 ID 不同 pattern：
   - `hub_merge.py` 偵測衝突 → HUMAN_PENDING
   - 不自動覆寫 verified 規則（沿用 ACT-028 `RuleOverwriteProtected`）

4. **A-30.4**：惡意 Hub 防護 — 模擬 endpoint allow-list 外的 URL：
   - Client 拒連；session_start additionalContext 顯示 `[SDD-HUB] endpoint rejected`

5. **A-30.5**：Chaos 驗證 — Hub 失效（timeout / 500 / PGP 驗證失敗）時：
   - session_start 不阻塞；FSM 不升 ESCALATION；decision_trace 記錄失敗原因

### 4.7 工時分解（7 天）

| 日 | 任務 | 交付 |
|----|------|------|
| D1 | 治理規格文件（D-30.1 + D-30.2） | 使用者 review |
| D2 | 治理規格落地 + anonymizer 框架（D-30.3 + D-30.7） | — |
| D3 | PII Scanner + 測試 20 條 fixture（D-30.6 + 部分 D-30.14） | — |
| D4 | Hub Sync Client CLI + registry schema（D-30.4 + D-30.5） | — |
| D5 | Conflict Resolver + FSM 狀態擴充（D-30.8 + D-30.12） | — |
| D6 | session_start 整合 + Hub 端參考實作（D-30.9~D-30.11） | — |
| D7 | CI/CD 規格 + 完整驗收 + A-30.1~A-30.5（D-30.13 + D-30.14） | PR |

### 4.8 風險矩陣

| 風險 | 嚴重度 | 紓緩 |
|-----|--------|------|
| R-30.1 PII scanner false-negative（規則未覆蓋）| 🔴 CRITICAL | 預設 opt-in + 二次 review + GitHub Action 再掃 |
| R-30.2 Hub 端被投毒（惡意 PR merge）| 🔴 CRITICAL | GPG 簽章 + reviewer signoff + pull 預設 external |
| R-30.3 去識別化破壞語義（規則失效）| 🟡 HIGH | 20 條 fixture regression；語義骨架保留測試 |
| R-30.4 Endpoint allow-list 繞過 | 🟡 HIGH | 硬編碼檢查 + env 覆寫需 `SDD_HUB_ALLOWLIST_OVERRIDE=<audit_reason>` |
| R-30.5 Hub 服務中斷影響本地工作 | 🟢 MEDIUM | Pull fallback 至快取；非阻塞失敗 |

---

## 伍、ACT-031：多模態 Spec 驗證（詳細規劃）

### 5.1 目標

將 SLV（Spec Logical Validator）從「文字 Spec ↔ 文字 Spec」擴充至「文字 Spec ↔ 非文字 artifact（UI mockup、DB Schema、C4 diagram、API Response sample）」的一致性驗證。

### 5.2 交付物清單（16 項）

| # | 交付物 | 路徑 | 說明 |
|---|-------|------|------|
| **核心引擎**|||
| D-31.1 | 多模態 Validator | `tools/fsm_runtime/multimodal_validator.py` | 統一入口；路由至各 modality adapter |
| D-31.2 | UI/Mockup adapter | `tools/fsm_runtime/modality/ui_adapter.py` | 解析 Figma/PNG/HTML → widget tree → 對應 FRD AC |
| D-31.3 | OpenAPI↔UI adapter | `tools/fsm_runtime/modality/api_ui_adapter.py` | OpenAPI endpoint 對應 UI 操作流程 |
| D-31.4 | DB Schema adapter | `tools/fsm_runtime/modality/db_schema_adapter.py` | SQL DDL / ERD → 對應 FRD 資料模型 |
| D-31.5 | C4 Diagram adapter | `tools/fsm_runtime/modality/c4_adapter.py` | PlantUML/Mermaid C4 → 對應 SRD component |
| D-31.6 | LLM Backend 抽象層 | `tools/fsm_runtime/modality/llm_backend.py` | Claude Code Session / Claude API / Minimax API drop-in 介面 |
| **Spec Anchor 機制**|||
| D-31.7 | Anchor schema | `docs_template/sdd/architecture/SPEC-ANCHOR-TEMPLATE.md` | FRD/SRD 內埋 `<!-- anchor:ui:LoginScreen -->` 對應非文字 artifact |
| D-31.8 | Media Store | `docs/99_media/` | 多模態 artifact 統一存放（Git LFS tracked）|
| **規則擴充**|||
| D-31.9 | SLV-008 UI↔FRD 一致性 | `.claude/skills/spec-logical-validator/rules/SLV-008.yaml` | 「UI mockup 元件必對應 FRD AC」|
| D-31.10 | SLV-009 API↔UI 一致性 | `.claude/skills/spec-logical-validator/rules/SLV-009.yaml` | 「每個 UI 操作對應 OpenAPI endpoint」|
| D-31.11 | SLV-010 DB↔FRD 一致性 | `.claude/skills/spec-logical-validator/rules/SLV-010.yaml` | 「DB schema 欄位對應 FRD 資料需求」|
| D-31.12 | SLV-011 C4↔SRD 一致性 | `.claude/skills/spec-logical-validator/rules/SLV-011.yaml` | 「C4 component 對應 SRD 模組」|
| **整合**|||
| D-31.13 | spec-logical-validator Skill 擴充 | `.claude/skills/spec-logical-validator/SKILL.md` | 新增 modality 段；SCG-1/2 強制呼叫 |
| D-31.14 | CI/CD 整合 | `cicd/SDD_CICD_BASE_LAYER.md` | 新增 `Multimodal SpecTrace` step |
| **測試**|||
| D-31.15 | 測試套件 | `tools/fsm_runtime/tests/test_multimodal_validator.py` | 4 adapter × 正反例；Anchor 漏接偵測 |
| D-31.16 | Benchmark fixture | `tools/fsm_runtime/tests/fixtures/multimodal/` | 小型 UI/API/DB/C4 樣本 + 期望結果 YAML |

### 5.3 Spec Anchor 機制（核心創新）

文字 Spec 透過錨點宣告依賴的非文字 artifact，Validator 雙向驗證：

```markdown
<!-- FRD-Auth.md 摘錄 -->
## F-010 登入流程
AC-010-1: 用戶輸入 Email + 密碼，點擊「登入」後導向首頁
<!-- anchor:ui:LoginScreen -->     → docs/99_media/ui/login-screen.png
<!-- anchor:api:POST /auth/login --> → docs/02_architecture/api/auth.yaml#/paths/~1auth~1login/post
<!-- anchor:db:users --> → docs/07_design/db/schema.sql#L42-L58
```

Validator 驗證鏈：
1. UI mockup 是否有 `Email` / `Password` / `登入` 三個 widget？（ui_adapter）
2. OpenAPI `POST /auth/login` 是否存在且 request body 含 email + password？（api_ui_adapter）
3. DB `users` table 是否有 email 欄位？（db_schema_adapter）

### 5.4 LLM Backend 抽象層（§OPEN-10.7 補述落地）

```python
class ModalityBackend(Protocol):
    def extract_widget_tree(self, image_path: Path) -> WidgetTree: ...
    def compare_widgets_to_ac(self, widgets: WidgetTree, ac: str) -> ComparisonResult: ...

class ClaudeCodeSessionBackend(ModalityBackend):  # 預設，本機 Session
class ClaudeAPIBackend(ModalityBackend):          # 遠端 API（含 vision）
class MinimaxAPIBackend(ModalityBackend):         # OPEN-10.7 補述保留
```

選定 backend 經 env var：`SDD_MULTIMODAL_BACKEND ∈ {session, claude-api, minimax}`；預設 `session`（零外部依賴）。

### 5.5 FSM 整合

- **不新增狀態** — 多模態驗證整合進 SLV，於 `SPEC_LOGICAL_VALIDATE` step 內執行
- **SCG-1 / SCG-2 強制**：若 FRD/SRD 內含 anchor → Multimodal Validator 必跑 → 違反即 CRITICAL FAIL

### 5.6 驗收條件

1. **A-31.1**：UI↔FRD 正例 — 提供 login-screen.png 與 AC-010-1，Validator 回報 `consistent: true`
2. **A-31.2**：UI↔FRD 反例 — 移除 mockup 的「登入」按鈕，Validator 回報 `missing_widget: 登入 button`
3. **A-31.3**：API↔UI 正例 — OpenAPI `POST /auth/login` 與 UI 登入表單對齊 → `consistent: true`
4. **A-31.4**：API↔UI 反例 — OpenAPI request body 缺 password → `missing_field: password`
5. **A-31.5**：DB↔FRD — users table 缺 email 欄位 → `schema_mismatch`
6. **A-31.6**：C4↔SRD — C4 component 未對應 SRD 模組 → `orphan_component`
7. **A-31.7**：Anchor 漏接 — FRD 內 `anchor:ui:LoginScreen` 但 `docs/99_media/ui/` 無檔案 → `missing_anchor_target`
8. **A-31.8**：Backend 切換 — 同一 fixture 在 `session` / `claude-api` / `minimax` 三後端結果相同（±5% 容錯）
9. **A-31.9**：CI 整合 — `cicd/SDD_CICD_BASE_LAYER.md` 新增 step 成功阻擋反例 PR

### 5.7 工時分解（10 天）

| 日 | 任務 | 交付 |
|----|------|------|
| D1 | Spec Anchor schema + Media Store 目錄規格（D-31.7 + D-31.8）| — |
| D2 | LLM Backend 抽象層 + ClaudeCodeSession 實作（D-31.6）| — |
| D3 | UI adapter + SLV-008（D-31.2 + D-31.9）| — |
| D4 | OpenAPI↔UI adapter + SLV-009（D-31.3 + D-31.10）| — |
| D5 | DB Schema adapter + SLV-010（D-31.4 + D-31.11）| — |
| D6 | C4 adapter + SLV-011（D-31.5 + D-31.12）| — |
| D7 | Multimodal Validator 統一入口 + SLV Skill 擴充（D-31.1 + D-31.13）| — |
| D8 | 測試 fixture + 8 項驗收 case（D-31.15 + D-31.16）| — |
| D9 | CI/CD 整合 + Backend 切換驗收（D-31.14 + A-31.8）| — |
| D10 | 3 backend regression + 文件同步 + PR | PR |

### 5.8 風險矩陣

| 風險 | 嚴重度 | 紓緩 |
|-----|--------|------|
| R-31.1 LLM 幻覺（widget 誤判）| 🔴 CRITICAL | 多 backend 交叉驗證；`consistency_confidence` 低於 0.8 強制 HUMAN_PENDING |
| R-31.2 多模態成本暴增（API token 費用）| 🟡 HIGH | 預設 session backend 零成本；遠端 backend 僅 CI 夜跑；每 session 預算 `SDD_MULTIMODAL_BUDGET_USD` |
| R-31.3 非文字 artifact 隱私洩漏（PII 入 LLM）| 🔴 CRITICAL | 本地 session backend 優先；遠端 backend 呼叫前經 ACT-030 anonymizer |
| R-31.4 Git LFS 體積膨脹 | 🟢 MEDIUM | `docs/99_media/` 建議壓縮 < 500KB；超標 CI warn |
| R-31.5 Adapter 覆蓋不全（第 5 種 modality 如音訊/影片）| 🟢 MEDIUM | 本輪僅 UI/API/DB/C4 四類；其他延 Phase G |

---

## 陸、ACT-032 / ACT-033（藍圖保留，完整版待評估）

### 6.1 ACT-032 SLV 全自動演化

- **條件**：ACT-028 累積 ≥ 5 條 verified 規則 + 2 個月誤報率 < 5%
- **範疇**：`slv_generator` 新增 `auto_promote_to_verified` 模式；需通過自動化「反向驗證」（規則需能被既有合法 Spec 通過）
- **最早評估**：2026-Q4

### 6.2 ACT-033 AI 對話品質 Benchmark

- **條件**：ACT-031 多模態基礎就位 + Ground Truth 語料集（10 個完整 SDD 專案）
- **範疇**：每次 Claude 輸出對照「Spec 遵循度」打分；長期追蹤 Claude 模型版本對 SDD workflow 的品質影響
- **最早評估**：2027-Q1

---

## 柒、Milestone、依賴拓撲、並行排程

### 7.1 Phase F 里程碑

| Milestone | 範疇 | 工時 | 期望完成 |
|-----------|------|------|---------|
| **M1 — 治理先行** | ACT-030 D-30.1~D-30.3（治理規格 + trust ladder） | 2 天 | Phase F 啟動 +2 |
| **M2 — Hub Client** | ACT-030 D-30.4~D-30.14（實作 + 測試） | 5 天 | M1 +5 |
| **M3 — 多模態基礎** | ACT-031 D-31.1~D-31.8（Anchor + Backend 抽象 + 4 adapter） | 6 天 | M2 +6 |
| **M4 — 多模態整合** | ACT-031 D-31.9~D-31.16（SLV 規則 + CI + 驗收） | 4 天 | M3 +4 |
| **總計** | ACT-030 + ACT-031 | **17 天** | **啟動日 +17** |

### 7.2 依賴拓撲

```
P-F.3 治理規格 ──┐
                 ├─→ M1 治理先行 ──→ M2 Hub Client ──┐
P-F.5 endpoint ──┘                                   │
                                                      ├─→ (Phase F 達成)
P-F.4 LLM backend ──┐                                 │
                     ├─→ M3 多模態基礎 ──→ M4 整合 ──┘
P-F.6 fixture 擴充 ─┘
```

**關鍵路徑**：P-F.3 → M1 → M2 → M4（Hub client 延 M3 起跑）
**可並行**：M2 與 M3 可完全並行（無 runtime code overlap，僅 FSM 狀態不衝突）
**最短完成**：並行排程下 **12 天**（M1:2 + max(M2:5, M3:6) + M4:4）

### 7.3 並行排程建議（假設 2026-07-01 啟動）

```
Week 1 (07-01 ~ 07-05): M1 (D1-D2) + M3 先行 (D1 Anchor schema)
Week 2 (07-06 ~ 07-12): M2 (D3-D7 Hub Client) ‖ M3 (D2-D5 backend + 3 adapter)
Week 3 (07-13 ~ 07-19): M3 (D6-D7 收尾) → M4 (D8-D10 驗收 + PR)
```

### 7.4 對應 §OPEN-10.x 歷史決策的一致性

| OPEN | Phase E 決策 | Phase F 繼承 |
|------|------------|-------------|
| OPEN-10.1 RACI | 單人（User）| 延續；ACT-030/031 各開 1 GitHub Issue |
| OPEN-10.2 測試環境 | Synthetic + Meta-test 雙軌 | 延續；多模態 fixture 加入 Meta-test |
| OPEN-10.3 Rollback | 輕量化 checklist + schema_version | schema_version: `phase-f-v1`；每 PR 三行 rollback 宣告 |
| OPEN-10.4 Hook 預算 | p95 < 200ms | 延續；Hub pull 單次 ≤ 500ms（較寬鬆，非每 tool call）|
| OPEN-10.6 生產回饋 | File-based Pull 禁 HTTP | **Hub 同原則** — 使用 Git pull 非 HTTP API |
| OPEN-10.7 LLM 後端 | Claude Code Session | 多模態預設同；Minimax 保留介面 |

---

## 捌、風險登記簿（Phase F 特有）

| ID | 風險 | 類型 | 嚴重度 | 紓緩 | Owner |
|----|------|------|--------|------|-------|
| RF-1 | Hub 投毒（惡意規則）| 安全 | 🔴 CRITICAL | GPG + allow-list + external 預設（§4.5）| User |
| RF-2 | PII/商業機密洩漏 | 合規 | 🔴 CRITICAL | D-30.1 治理規格 + opt-in + 雙層掃描 | User + Security |
| RF-3 | 多模態 LLM 幻覺 | 品質 | 🔴 CRITICAL | 多 backend 交叉 + confidence 門檻 + HUMAN_PENDING | Runtime |
| RF-4 | 多模態 API 成本失控 | 成本 | 🟡 HIGH | 預設 session backend；預算 env；CI 夜跑限 | Runtime |
| RF-5 | Hub 服務中斷 | 可用性 | 🟢 MEDIUM | 快取 24h；非阻塞失敗；decision_trace 記錄 | Runtime |
| RF-6 | Git LFS 體積膨脹 | 性能 | 🟢 MEDIUM | 壓縮建議 + CI warn | Runtime |
| RF-7 | schema_version 向後相容破壞 | 穩定性 | 🟡 HIGH | Loader 寬鬆解析（§OPEN-10.3）| Runtime |
| RF-8 | Phase F 侵入 Phase E Runtime 導致回歸 | 穩定性 | 🟡 HIGH | 每 PR 跑 chaos 50 輪 smoke；fsm_runtime 測試全綠 | Runtime |
| RF-9 | 多模態 adapter 範圍蔓延 | 範疇 | 🟢 MEDIUM | 本輪硬性鎖定 4 類（UI/API/DB/C4）；第 5 類延 Phase G | User |

---

## 玖、Rollback 策略

### 9.1 沿用 Phase E §OPEN-10.3 輕量化 checklist

每個 ACT-030/031 PR 強制包含三行 rollback 宣告：
```markdown
**Rollback**:
- Code Revert: git revert <PR-SHA>
- State Data Cleanup: 刪除 hub_sync_state.yaml / multimodal_cache/（若存在）
- Env/Config Changes: unset SDD_HUB_PUSH_CONFIRMED / SDD_MULTIMODAL_BACKEND（若有設）
```

### 9.2 Schema 版本控制

| 檔案 | 欄位 | Phase F 新增 |
|------|------|-------------|
| `build/reports/fsm/FSM-STATE-TEMPLATE.yaml` | `schema_version: "phase-f-v1"` | `hub_sync_tracking`（hub endpoint / last_pull_at / trust_ladder_events）|
| `knowledge/hub-registry.yaml` | `registry_version: "1.0"` | 全新檔 |
| `.claude/skills/spec-logical-validator/rules/*.yaml` | rule schema | 新增 `modality` / `anchor_type` / `backend_hint` 選欄 |

**Loader 寬鬆解析**：Phase D/E runtime 讀 phase-f-v1 state 時，`hub_sync_tracking` 視為可忽略；Phase F runtime 讀 phase-e-v1 state 時，`hub_sync_tracking` 預設空 dict。

### 9.3 Git 標記

- Phase F 啟動前：`phase-e-final` tag（目前應已標記）
- M1 結束：`phase-f-m1` tag（治理先行）
- M2 結束：`phase-f-m2` tag（Hub Client）
- M4 結束：`phase-f-final` tag（多模態 + Hub 全量）

### 9.4 降級路徑

| 觸發 | 動作 |
|-----|------|
| ACT-030 PII scanner false negative 事件 | 立即 `SDD_HUB_PUSH_CONFIRMED` 撤銷；Hub push 全停；git revert 至 phase-f-m1 |
| ACT-031 LLM 幻覺誤擋大量 PR | `SDD_MULTIMODAL_BACKEND=disabled`；SLV-008~011 trust_level 降至 `external`（Advisory-only）|
| FSM 回歸（chaos 50 輪有任一未停機）| 立即退回 phase-e-final；開緊急 issue |

---

## 拾、Open Issues（已決議歷史）

| ID | 項目 | 狀態 | 決議內容 | 決議日 |
|----|------|------|---------|--------|
| **OPEN-F.1** | Hub endpoint 載體選擇 | 🟢 RESOLVED | **GitHub private repo**（沿用 §OPEN-10.6 Git pull 精神，降低自維運負擔；endpoint 寫入 `knowledge/hub-registry.yaml` allow-list）| 2026-04-24 |
| **OPEN-F.2** | 商業機密治理規格是否委外 legal review？ | 🟢 RESOLVED | **不委外**，架構師起草 D-30.1 + 使用者人工 review（與 OPEN-10.x 單人 RACI 風格一致）| 2026-04-24 |
| **OPEN-F.3** | 多模態 LLM backend 優先序 | 🟢 RESOLVED | **session > claude-api > minimax**；預設 `SDD_MULTIMODAL_BACKEND=session`（零成本優先；minimax 保留 drop-in 介面）| 2026-04-24 |
| **OPEN-F.4** | Git LFS 使用策略 | 🟢 RESOLVED | **啟用 Git LFS**；單檔 < 500KB 硬上限（CI warn）；`docs/99_media/` 統一管理 | 2026-04-24 |
| **OPEN-F.5** | Phase F 驗收專案 | 🟢 RESOLVED | **Meta-test 為主**（沿用 Phase E §OPEN-10.2 雙軌策略）；canary 視 Phase F M4 完成度再決定，不阻擋啟動 | 2026-04-24 |
| **OPEN-F.6** | Phase F 期間 Phase E Runtime 凍結條款 | 🟢 RESOLVED | **Phase E 僅允許 P0 bug hotfix**；其他凍結直至 phase-f-final tag | 2026-04-24 |
| **OPEN-F.7** | 是否納入 ACT-032/033 至 Phase F 完整版？ | 🟢 RESOLVED | **另開 Phase G**（ACT-032 SLV 全自動 + ACT-033 對話品質 benchmark 獨立評估，不與 Phase F 綑綁）| 2026-04-24 |

**啟動阻擋**：✅ 全數解除（P0×2、P1×3、P2×2 全 RESOLVED）。Phase F 可進入 Stage 0 Pre-flight。

---

## 拾壹、整合點與後續動作

### 11.1 本藍圖通過後需更新的文件

| 文件 | 更新範疇 | 時點 |
|------|---------|------|
| `AISDLC_SDD_INIT.md` | §Phase D·E 表新增 Phase F 欄位（啟動後）；保留項目指向本檔 | Phase F 啟動日 |
| `CLAUDE.md` Rule 9 | 新增 Rule 9.12（ACT-030 Hub 治理）+ 9.13（ACT-031 多模態）| ACT 實作 PR 同步 |
| `SDD_FSM_ENGINE.md` | 新增 HUB_SYNC 狀態章節 | ACT-030 M2 |
| `SDD_CICD_BASE_LAYER.md` | 新增 Multimodal SpecTrace step | ACT-031 M4 |
| `cicd/SDD_HUB_SYNC.md` | 全新檔 | ACT-030 M2 |
| `FILE_DIRECTORY_RULES.md` | 新增 `docs/99_media/`、`knowledge/hub/` 目錄規則 | ACT-030 M1 |

### 11.2 本藍圖不需立即更新的文件

- `Automation_04.md` — 僅加尾註指向本檔（不歸檔，保留 Phase E 審計依據）
- 各 Scenario Enhancement — Phase F ACT 實作時再按需更新

### 11.3 Phase F 啟動條件清單（Gate）

Phase F 啟動前必須全部滿足：

- [x] **OPEN-F.1~F.7 使用者決議完成**（2026-04-24，採默認答全數 RESOLVED）
- [x] Phase E 全量穩定驗證（2026-04-25：208 tests + 14 subtests 全綠 + chaos 50 輪 100% bounded halt / avg 1980 tokens；7 天觀察窗轉為 nightly chaos 持續監控）
- [x] Automation_04.md 歸檔至 `build/planning/archive/`（2026-04-25 Stage 0 執行）
- [x] Git 標記 `phase-e-final`（2026-04-25 Stage 0 執行）
- [x] GitHub Issue 各 ACT-030 / ACT-031 建立完成（2026-04-25 Stage 0 執行）
- [ ] Synthetic Test Project 擴充多模態 fixture 目錄結構（Stage 3 開工前完成）
- [ ] 商業機密治理規格草案（D-30.1）完成（Stage 1 / M1 第 1 天交付）

### 11.4 Next Action（已啟動，等候 Phase E 穩定觀察窗）

✅ **OPEN-F.1~F.7 全 RESOLVED**（採默認答），Phase F 進入啟動序列：

1. **觀察窗**（now ~ 2026-05-01）：監控 Phase E nightly chaos + 193+14 tests 穩定性，無 P0 即進入 Stage 0
2. **Stage 0 Pre-flight**（推薦 2026-05-01 起 1 天）：歸檔 Automation_04 / git tag phase-e-final / 開 GitHub Issue
3. **M1~M4 排程**（2026-05-02 ~ 2026-05-18，並行 12 工作天）：依 §柒 7.3 並行排程執行
4. **PR 合併與 phase-f-final tag**（推薦 2026-05-20 前完成）

**Pro Plan Token 預算切分**：9 Sessions（Stage 0:1 / M1:1 / M2:2 / M3:3 / M4:2），每 Session 結束強制 `/stage-compaction`（Rule 9.4）。

---

**建立日期**：2026-04-24
**版本**：Phase F Blueprint v1（OPEN-F.1~F.7 已決議 ACTIVE）
**作者**：Architect（單人模式，延續 Phase E RACI）
**啟動條件**：Phase E 穩定觀察窗（now ~ 2026-05-01）通過後即進入 Stage 0
**歸檔時點**：Phase F 全量完成後，本檔連同執行紀錄歸檔至 `build/planning/archive/`
