# Hub Trust Ladder — 跨專案 FPL/SLV 信任階梯契約

**ACT**: ACT-030（Phase F M1 D-30.3）
**版本**: v1
**狀態**: ✅ APPROVED — 2026-04-25 通過 🔴 Human Checkpoint
**建立日期**: 2026-04-25
**對應規格**: [HUB-GOVERNANCE-SPEC.md](../../docs/06_quality/HUB-GOVERNANCE-SPEC.md) G-30.4 / G-30.5
**沿用機制**: ACT-028 SLV `trust_level` schema（`tools/fsm_runtime/slv_generator.py` VALID_TRUST_LEVELS）

---

## 壹、設計原則

1. **既有 schema 完全相容**：本契約**不**新增 `trust_level` 列舉值（仍是 `verified` / `proposed` / `external`），避免衝擊 ACT-028 已驗證的寫入保護鏈（`RuleOverwriteProtected`）。
2. **Hub 場景概念上四階**：external → reviewed → verified（→ promoted）。`reviewed` 是**過程狀態**（review_status 欄位），不是 trust_level 列舉。
3. **單向升級**：external → verified 必經人工 YAML 簽核；不允許自動升級。降級允許（verified → external）但須留 audit。
4. **既有 verified 不被覆寫**：Hub pull 觸發既有 `verified` 同 ID 規則衝突 → 進 HUMAN_PENDING（不自動覆寫）。
5. **Advisory-only by default**：所有 Hub pull 規則一律 advisory，**不阻 SCG**，直到使用者升 verified。

---

## 貳、四階概念 vs 三階 trust_level 對照

| 概念階 | trust_level | review_status | SCG 行為 | 寫入保護 |
|--------|------------|---------------|---------|---------|
| **External**（剛 pull） | `external` | `pending` | Advisory（不阻塞） | overwrite_proposed=True 可覆寫 |
| **Reviewed**（人工初審） | `external` | `reviewed` | Advisory（仍不阻塞） | 同上 |
| **Verified**（簽核升級） | `verified` | `reviewed` | Blocking（CRITICAL FAIL 阻 SCG） | `RuleOverwriteProtected` 完全鎖定 |
| **Rejected**（駁回） | （刪除規則檔）| `rejected`（記入 `knowledge/hub/REJECTED-LOG.yaml`）| 不適用 | 不適用 |

**為何不引入新 trust_level 值**：ACT-028 既有 verified/proposed/external 三階已透過 208+ tests 驗證，新增列舉會破壞 `slv_generator._validate_rule_doc()` schema 與 `evaluate_rule_outcome()` 路由邏輯；用 `review_status` 子欄位表達過程狀態，邏輯隔離。

---

## 參、規則 YAML 擴充欄位（Hub 場景）

```yaml
# .claude/skills/spec-logical-validator/rules/SLV-XXX.yaml（external 範例）
id: SLV-008
name: ui-frd-consistency
trust_level: external           # ★ Hub pull 規則預設 external
scope: SCG-1
severity: high
description: |
  UI mockup 元件必對應 FRD AC...
pattern_yaml: |
  ...

# Hub 場景擴充欄位（M1 起新增，向後相容）
hub_metadata:
  source: hub                   # local | hub | proposed_by_slv_generator
  pulled_from: https://github.com/aisdlc-sdd-org/learning-hub
  pulled_at: 2026-07-05T08:00:00+00:00
  source_commit: <hub-commit-sha>
  gpg_signature_verified: true  # G-30.6 對應
review_status: pending           # pending | reviewed | rejected
review_history:
  - reviewer: null
    reviewed_at: null
    decision: null               # approve | reject | needs_clarification
    notes: null

# verified 必填（沿用 ACT-028 schema）— 升 verified 時填入
reviewed_by: null
reviewed_at: null
```

---

## 肆、升級流程（external → verified）

### 4.1 步驟

```
[1] hub_sync.pull() 寫入 SLV-008.yaml（trust_level: external, review_status: pending）
   ↓
[2] session_start additionalContext 提示「N 條新 external 規則待 review」
   ↓
[3] 使用者人工 review：讀規則內容、判斷適用性
   ↓
[4a] 升級 → 編輯 YAML：
      trust_level: verified
      review_status: reviewed
      reviewed_by: <user-handle>
      reviewed_at: <ISO-8601 UTC>
      review_history[].reviewer/decision/notes
[4b] 駁回 → 刪除 SLV-XXX.yaml + append REJECTED-LOG.yaml（id, reason, rejected_at）
[4c] 標記已審但未升 → 編輯 YAML：
      trust_level: external（不變）
      review_status: reviewed
      review_history[] 補完
   ↓
[5] slv_generator._validate_rule_doc() 驗證 schema：
    - verified → reviewed_by/reviewed_at 必填（既有檢查）
    - schema 不合 → SchemaViolation 阻擋 commit
   ↓
[6] 通過 → 規則生效（verified 開始阻 SCG）
```

### 4.2 簽核資料完整性

| 欄位 | external→reviewed 必填 | reviewed→verified 必填 |
|------|---------------------|---------------------|
| `review_status` | ✅ 設為 `reviewed` | ✅ 維持 `reviewed` |
| `review_history[].reviewer` | ✅ | ✅ |
| `review_history[].reviewed_at` | ✅ | ✅ |
| `review_history[].decision` | ✅（`approve` / `needs_clarification`） | ✅（`approve`） |
| `reviewed_by` | ❌（仍 external） | 🔴 **必填**（沿用 ACT-028）|
| `reviewed_at` | ❌ | 🔴 **必填**（沿用 ACT-028）|
| `gpg_signature_verified` | ✅ pull 時填 | 維持 |

---

## 伍、降級流程（verified → external）

### 5.1 觸發情境

- 規則誤殺率高於閾值（per-project 觀察）
- 上游 Hub 發現原規則有缺陷（push notice）
- 使用者主動撤銷信任

### 5.2 步驟

```
[1] 使用者編輯 SLV-XXX.yaml：
      trust_level: external（從 verified 改回）
      review_status: reviewed（保留審計）
      review_history[] 補一筆 decision: revoked + reason
   ↓
[2] reviewed_by / reviewed_at 保留作為「歷史 verified 簽核紀錄」
   ↓
[3] _validate_rule_doc() 對 external 不要求 reviewed_by 欄位非空，通過驗證
   ↓
[4] commit + 訊息註明「revoke verified for SLV-XXX: <reason>」
```

**注意**：無「自動降級」機制；所有降級必須人工觸發 + commit。

---

## 陸、衝突解決（Hub pull vs 本地）

### 6.1 三種衝突類型

| 衝突 | 處理 |
|------|------|
| Hub pull SLV-008（external）vs 本地不存在 | 直接寫入（OK） |
| Hub pull SLV-008（external）vs 本地 SLV-008（external，舊版本） | 覆寫（overwrite_proposed=True；review_status 重設為 pending）|
| Hub pull SLV-008（external）vs 本地 SLV-008（**verified**） | 🔴 進 HUMAN_PENDING；**禁止**自動覆寫（沿用 RuleOverwriteProtected） |
| Hub pull SLV-008（external）vs 本地 SLV-008（proposed） | 衝突（proposed 是 slv_generator 自動產出）→ HUMAN_PENDING |

### 6.2 三向合併（hub_merge.py，M2 D-30.8 實作）

```
base = 本地上次 pull 後的 SLV-008（cache 中）
local = 當前本地 SLV-008
remote = 本次 Hub pull 的 SLV-008

if local 與 base 相同 → fast-forward（直接覆寫）
if local 與 remote 相同 → no-op
if local ≠ base 且 remote ≠ base 且 local ≠ remote → conflict → HUMAN_PENDING
```

衝突 artifact 寫入 `knowledge/hub/CONFLICTS/SLV-XXX-{timestamp}.yaml`，含三方 diff 與建議。

---

## 柒、與既有 ACT-028 機制的整合點

| ACT-028 機制 | Hub 場景行為 |
|-------------|------------|
| `RuleOverwriteProtected` | **完全沿用**：Hub pull 不覆寫 verified；衝突即 HUMAN_PENDING |
| `_validate_rule_doc()` reviewed_by/reviewed_at 強制 | **完全沿用**：Hub external 升 verified 必填；違反 SchemaViolation |
| `evaluate_rule_outcome()` advisory vs blocking | **完全沿用**：external = advisory；verified = blocking |
| `slv_generator.write_rule_candidate()` | **不適用**：Hub pull 不經 generator，直接由 `hub_sync.pull()` 寫入；但 `overwrite_proposed=False` 旗標仍可用於阻擋 verified 覆寫 |
| `learning_commit_tracking` audit chain | **延伸**：Hub external 升 verified 也記入 `review_history`，但**不**寫 `learning_commit_tracking`（後者專屬 ACT-028 自動產出規則） |

---

## 捌、REJECTED-LOG.yaml 範例

`knowledge/hub/REJECTED-LOG.yaml`：
```yaml
schema_version: "phase-f-v1"
rejected:
  - rule_id: SLV-099
    pulled_from: https://github.com/aisdlc-sdd-org/learning-hub
    pulled_at: 2026-07-08T10:00:00+00:00
    rejected_at: 2026-07-08T15:30:00+00:00
    rejected_by: user_handle
    reason: "規則覆蓋與 SLV-007 重疊且誤殺率預估 > 30%"
    raw_yaml_archived: knowledge/hub/REJECTED/SLV-099-2026-07-08.yaml.bak
```

---

## 玖、驗收條件

- [ ] 本契約與 HUB-GOVERNANCE-SPEC.md G-30.4/G-30.5 完全對齊
- [ ] 不破壞 ACT-028 既有 schema：M2 實作 hub_sync 後跑全套 208+ 測試仍綠
- [ ] external→verified 升級流程在 D-30.5 hub_sync 客戶端有對應 CLI（`hub_sync.py promote --rule SLV-XXX`）
- [ ] 所有衝突路徑（§陸）有對應 D-30.8 hub_merge.py 測試案例

---

**作者**: Architect（Phase F 單人 RACI）
**Review 預定**: M1 第 2 天（🔴 Human Checkpoint，與 D-30.1/D-30.2 同批）
**對應 Issue**: [#1 ACT-030](https://github.com/wuweihungmobile/AISDLC_SDD/issues/1)
