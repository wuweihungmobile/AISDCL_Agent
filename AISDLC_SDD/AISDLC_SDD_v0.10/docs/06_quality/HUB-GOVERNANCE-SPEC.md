# HUB-GOVERNANCE-SPEC — Cross-Project Learning Hub 商業機密治理規格

**ACT**: ACT-030（Phase F M1 D-30.1）
**版本**: v1（治理先行）
**建立日期**: 2026-04-25
**狀態**: ✅ APPROVED — 2026-04-25 通過 🔴 Human Checkpoint（OPEN-G.1~G.3 採建議默認）
**對應規則**: CLAUDE.md Rule 9.12（Phase F ACT 實作 PR 同步建立）
**藍圖來源**: `build/planning/active/SDD_improving_Automation_05.md` §肆 4.5

---

## 壹、目的與範疇

本規格定義 AISDLC-SDD 實例參與「跨專案 Learning Hub（FPL/SLV 共享）」時的**資料治理紅線**：什麼可以出去、什麼必須擋下、出問題如何究責。

**適用對象**：
- 透過 `tools/fsm_runtime/hub_sync.py` push / pull 的所有 artifact
- 落地於 `knowledge/failure-patterns/`、`.claude/skills/spec-logical-validator/rules/` 的規則檔

**不適用於**：
- 純本地（never-push）的專案 docs/、build/reports/
- 已加密的私有附件（不在 Hub 流動範圍）

**OPEN 對齊**：
- OPEN-F.1 Hub 載體 → GitHub private repo（沿用 §OPEN-10.6 Git pull 精神）
- OPEN-F.2 治理 review → 不委外，本規格由架構師起草 + 使用者人工簽核

---

## 貳、資料分級與處置矩陣

### 2.1 三級分類

| 級別 | 名稱 | 範例 | 預設處置 |
|------|------|------|---------|
| **L0** | 公開（Open）| 通用失敗模式（temporal-inconsistency、testability-violation 等抽象描述）、SDD 規則骨架 | ✅ 允許 push（仍經 anonymizer 過 redact） |
| **L1** | 內部（Internal）| 專案代號、模組名、模糊化後的 issue/PR 編號、time-window 區間 | 🟡 允許 push 但須經 anonymizer **強制替換**為 placeholder |
| **L2** | 機密（Confidential）| 客戶名、合約金額、內部網域、員工 Email、API token、IP 位址、PII | 🔴 **禁止 push** — 命中即 quarantine，停止整批 |

### 2.2 分類判定流程（machine-first）

```
artifact 進入 hub_sync.push() 入口
  ↓
[Step 1] PII Scanner（D-30.6）依 anonymizer_rules.yaml L2 patterns 掃描
  ↓ 命中 → quarantine（寫 build/reports/hub/QUARANTINE-{date}-{id}.yaml）→ 中止
  ↓ 未命中
[Step 2] Anonymizer（D-30.7）依 L1 patterns 自動替換 placeholder
  ↓
[Step 3] 二次 PII Scan（防 anonymizer 漏網）
  ↓ 命中 → quarantine → 中止
  ↓
[Step 4] dry-run diff 顯示給使用者
  ↓
[Step 5] 使用者設 SDD_HUB_PUSH_CONFIRMED=<reason> → 真 push
```

---

## 參、強制治理規則（G-30.x）

| ID | 規則 | 違反後果 |
|----|------|---------|
| **G-30.1** | Pre-push PII 強制（L2 patterns） | Push 中止；寫 quarantine；不重試 |
| **G-30.2** | 商業機密 pattern 強制（客戶名/金額/網域/產品代號） | 同 G-30.1 |
| **G-30.3** | Push 預設 opt-in：每次 push 須設 `SDD_HUB_PUSH_CONFIRMED=<audit_reason>`，未設一律 dry-run | dry-run，不真 push |
| **G-30.4** | Pull 預設 `trust_level: external`，Advisory-only 不阻 SCG | 違反即視同 verified 使用 → 阻塞 SCG 是錯誤行為 |
| **G-30.5** | external → verified 升級需人工填 `reviewed_by` + `reviewed_at`（沿用 ACT-028 schema），不允許自動升級 | YAML schema 驗證失敗 |
| **G-30.6** | Hub endpoint 須在 `knowledge/hub-registry.yaml` allow-list；非清單拒連 | Client 直接 raise；session_start `additionalContext` 顯示 `[SDD-HUB] endpoint rejected` |
| **G-30.7** | 二次掃描原則：本地 push 前 + Hub 端 GitHub Action 各掃一次（D-30.10） | Hub 端發現 PII → revert PR + 通知 |
| **G-30.8** | Quarantine 不可自動清除：人工 review 並產出 `QUARANTINE-RESOLUTION-{id}.md` 後才能刪除 | 防止靜默吞 PII 違規 |

---

## 肆、PII / 商業機密 Pattern 清單

> 詳細 regex 與 placeholder 對應見 [D-30.2 anonymizer_rules.yaml](../../tools/fsm_runtime/anonymizer_rules.yaml)。本節定義**類別**與覆蓋預期，pattern 細節由 anonymizer_rules.yaml 維護。

### 4.1 L2（必擋）

| 類別 | 範例命中 | placeholder |
|------|---------|------------|
| Email（具名） | `john.doe@acme.com` | `<EMAIL_REDACTED>` |
| IPv4 / IPv6 | `192.168.1.1`、`fe80::1` | `<IP_REDACTED>` |
| API Token / Bearer | `sk-...`、`ghp_...`、`AKIA...` | `<TOKEN_REDACTED>` |
| 信用卡 / 身分證 | 16 位連號、台灣身分證格式 | `<PII_REDACTED>` |
| 客戶名（allow-list 外） | 「ACME 公司」、「XX 銀行」 | quarantine（不替換） |
| 內部網域 | `*.corp.example.internal` | quarantine |

### 4.2 L1（自動替換）

| 類別 | 範例 | placeholder |
|------|------|------------|
| 專案代號（allow-list 外） | `proj-foo`、`order-system` | `<PROJECT_X>`（按出現序遞增 X=A,B,C...）|
| 模組名（FRD/SRD 內具名） | `OrderModule` | `<MODULE_X>` |
| Issue / PR 編號 | `#42`、`PR-123` | `<ISSUE_NN>`、`<PR_NN>` |
| 時間區間（含具體日期） | `2026-04-20`、`Q3-2025` | `<DATE_RELATIVE>`（保留相對語意如「7 天前」）|
| 人名（@mention） | `@alice` | `<USER_X>` |
| 檔案路徑（含具名專案層） | `src/order/module.py` | `<PATH_RELATIVE>` |

### 4.3 語義骨架保留要求

Anonymizer 必須**保留**以下欄位以利 Hub 下游使用：
- regex pattern 本身（PII 規則的核心）
- qualifier（`scope`、`severity`、`trust_level`）
- 失敗模式類別（FPL category）
- AC ID 數量級（具體 ID 替換為占位但保留 count）

---

## 伍、Quarantine 與審計

### 5.1 Quarantine 寫入格式

`build/reports/hub/QUARANTINE-{YYYY-MM-DD}-{seq}.yaml`：
```yaml
quarantine_id: QUARANTINE-2026-04-25-001
created_at: 2026-04-25T10:30:00+00:00
trigger: pre_push_pii_scan      # pre_push_pii_scan | post_anonymize_scan | hub_side_action
artifact_path: knowledge/failure-patterns/FPL-005-customer-leak.md
hit_patterns:
  - pattern_id: L2.email_named
    line: 42
    matched: <REDACTED_IN_LOG>   # 不在 log 中暴露原文
  - pattern_id: L2.customer_name
    line: 88
    matched: <REDACTED_IN_LOG>
resolution_status: pending       # pending | resolved | escalated
resolved_by: null
resolved_at: null
notes: null
```

### 5.2 解除流程

1. 使用者讀 `QUARANTINE-{id}.yaml`，到原 artifact 手動清理
2. 產出 `QUARANTINE-RESOLUTION-{id}.md`：說明命中原因、清理方式、避免再發機制
3. 將 `resolution_status: resolved` 並填 `resolved_by` / `resolved_at`
4. 重新 push（仍須過 PII Scanner）

### 5.3 Hub 端複查（G-30.7 對應）

- 本地通過 → push 至 Hub repo PR
- Hub repo `.github/workflows/hub-push.yml`（D-30.10）二次跑 `pii_scanner.py`
- 命中即自動 close PR + 開 issue 通知 pusher
- 三次 false-positive 同帳號 → reviewer 介入

---

## 陸、Allow-list 機制

### 6.1 Hub Endpoint Allow-list

`knowledge/hub-registry.yaml` 範例：
```yaml
registry_version: "1.0"
allowed_endpoints:
  - url: https://github.com/aisdlc-sdd-org/learning-hub
    fingerprint: <GPG-KEY-ID>
    last_pulled_at: null
    cache_ttl_hours: 24
deny_unlisted: true   # 預設 true，禁止連線非清單 URL
```

### 6.2 客戶名 / 專案代號 Allow-list（避免誤殺）

`tools/fsm_runtime/anonymizer_rules.yaml` 內 `allow_list` 區塊：
- 公開技術名詞（例如 `OAuth`、`PostgreSQL`、`Redis`）保留原文
- 公開開源專案名稱（例如 `linux`、`react`）保留
- 不包含內部專案代號、客戶名

---

## 柒、Override 與緊急流程

### 7.1 環境變數 Override（最小化）

| 變數 | 用途 | 風險 | 稽核 |
|------|------|------|------|
| `SDD_HUB_PUSH_CONFIRMED=<reason>` | G-30.3 一次性確認 push | 中（仍經 PII Scanner）| `<reason>` 寫入 `build/reports/hub/PUSH-AUDIT.yaml` |
| `SDD_HUB_ALLOWLIST_OVERRIDE=<audit_reason>` | G-30.6 一次性連非清單 endpoint | **高** | 寫 audit log；session 結束自動 unset |

**禁止**設於 `.claude/settings.json` env 區塊（必須臨時設）— PreToolUse hook 偵測常駐設定即 deny。

### 7.2 緊急停 Hub

若懷疑 PII 已外洩：
1. 立即 `git revert` Hub repo 對應 commit（GitHub repo settings → branch protection 應允許 admin override）
2. 設 `SDD_HUB_DISABLE=1`，session_start 改為 skip pull/push
3. 開 incident issue（GitHub Issue 模板：「security/hub-leak」）
4. 7 天內產出 `build/reports/hub/INCIDENT-{date}.md`

---

## 捌、與既有 Phase E 規則對齊

| Phase E 規則 | Hub 場景行為 |
|-------------|------------|
| Rule 9.5 ESCALATION 不可自動退出 | Hub failure 不升 ESCALATION（非阻塞）；只記 `decision_trace` 並繼續本地工作 |
| Rule 9.10.2 HMAC 強制（生產回饋） | Hub 場景改用 GPG 簽章（規則檔 git-based，沿用 git signed commit）|
| Rule 9.11.2 trust_level + 寫入保護 | Hub external 規則沿用 `RuleOverwriteProtected`：既有 verified 不被 Hub pull 覆寫 |
| Rule 9.11.3 advisory-only | Hub external trust_level 一律 advisory，不阻 SCG（直到人工升 verified）|

---

## 玖、驗收條件（M1 凍結門檻）

- [ ] 本規格通過 🔴 Human Checkpoint 簽核
- [ ] anonymizer_rules.yaml（D-30.2）pattern 清單覆蓋本規格 §肆 全部類別
- [ ] trust-ladder.md（D-30.3）四階流程與本規格 G-30.4/G-30.5 一致
- [ ] 本規格 §壹~§捌 內所有路徑、env 變數、檔名與 Automation_05.md §肆 4.5 / 4.7 工時表一致

---

## 拾、Open Issues（已決議）

| ID | 項目 | 狀態 | 決議內容 | 決議日 |
|----|------|------|---------|--------|
| OPEN-G.1 | 客戶名 / 商業機密 deny-list 範圍 | 🟢 RESOLVED | **空 list（最嚴）** — 所有具名客戶/產品代號一律當 L2 命中 quarantine；後續若需放行特定公開名稱，須以 PR 修改 `anonymizer_rules.yaml` 的 `deny_list_customers` / `deny_list_products` + 本規格更新 | 2026-04-25 |
| OPEN-G.1.1 | deny_list 為空時的兜底機制（Phase F.1 advisory）| 🟢 RESOLVED | 新增 `L2.corporate_suffix_starter` 規則：以中英文法人後綴（公司/股份有限公司/銀行/集團/Inc/Corp/Ltd/LLC/GmbH/SA/SAS/Pty 等）為保守兜底 pattern。即使 per-project `deny_list_customers` 未配置，仍能攔截多數具名法人；命中即 L2 quarantine 由人工於 PR 確認 | 2026-04-25 |
| OPEN-G.2 | Hub 端 reviewer 角色 | 🟢 RESOLVED | **單人 self-review**（沿用 §OPEN-10.1 Phase E 單人 RACI）— external→verified 升級僅需 `reviewed_by: <self>` 簽核；未來若團隊擴張再評估第三 reviewer | 2026-04-25 |
| OPEN-G.3 | Quarantine retention 政策 | 🟢 RESOLVED | **90 天 + 解除後可刪除** — `build/reports/hub/QUARANTINE-*.yaml` 預設保留 90 天；`resolution_status: resolved` 後使用者可手動刪除（但 `QUARANTINE-RESOLUTION-*.md` 永久保留作審計）| 2026-04-25 |

**啟動阻擋**：✅ 全數解除。M1 治理規格進入 commit + tag phase-f-m1。

---

**作者**: Architect（Phase F 單人 RACI，沿用 OPEN-10.1）
**Review 預定**: M1 第 2 天（🔴 Human Checkpoint）
**對應 Issue**: [#1 ACT-030](https://github.com/wuweihungmobile/AISDLC_SDD/issues/1)
