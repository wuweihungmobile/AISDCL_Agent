# Hub Registry — 倉儲規格（Hub 端參考實作）

**ACT**: ACT-030（Phase F M2 D-30.9）
**版本**: v1（schema_version: `phase-f-v1`）
**狀態**: ✅ APPROVED — 與 Phase F M2 同批簽核（2026-04-25）
**建立日期**: 2026-04-25
**對應規格**:
- [HUB-GOVERNANCE-SPEC.md](../../docs/06_quality/HUB-GOVERNANCE-SPEC.md) G-30.1~G-30.8
- [trust-ladder.md](trust-ladder.md)（升級 / 衝突契約）
- [hub-registry.yaml](../hub-registry.yaml)（Client 端 allow-list）
- [.github/workflows/hub-push.yml](../../.github/workflows/hub-push.yml)（D-30.10 sample）

> **適用對象**：本規格描述「Hub Registry repo 本身」的拓撲與 PR-review gate 流程，**不是** AISDLC-SDD framework repo 自己。下游若要架設自家 Hub，照本規格 fork / 自建。

---

## 壹、倉儲拓撲（Git-based）

### 1.1 設計原則

- **Git-based**：Registry 即一個 GitHub private repo，所有規則檔以 plain YAML / Markdown 落地，可 diff、可審計、可 GPG 簽章。
- **Branch-per-rule**：每條 SLV/FPL 的新增或修改走獨立 branch（`rule/SLV-XXX`、`fpl/FPL-XXX`），透過 PR 合入 `main`。禁止直接 push `main`。
- **Append-only metadata**：`metadata/` 目錄記錄歷次變更摘要（GPG fingerprint、reviewer、PR ID），不允許 force-push 重寫歷史。
- **PR-review gate**：所有合入 `main` 的變更必經 PR + GitHub Action 自動驗證（D-30.10）+ reviewer signoff。

### 1.2 對應 Client 端

| Client 端（AISDLC-SDD instance） | Hub 端（本規格） |
|---------------------------------|----------------|
| `knowledge/hub-registry.yaml` allow-list | Hub repo URL + GPG fingerprint |
| `tools/fsm_runtime/hub_sync.py pull()` | clone / fetch `main` 後讀 `rules/` `failure-patterns/` |
| `tools/fsm_runtime/hub_sync.py push()` | 在 Hub repo 開新 branch + PR；merge 由 reviewer 完成 |
| `tools/fsm_runtime/hub_merge.py` 三向合併 | 衝突落地於 Client 本地 `knowledge/hub/CONFLICTS/` |

---

## 貳、目錄結構

```
<hub-registry-repo>/
├── README.md                          # repo 簡介、貢獻流程
├── REGISTRY-SPEC.md                   # 本規格的 mirror（每次升版同步）
├── rules/                             # SLV 規則（external 預設）
│   ├── SLV-008.yaml                   # 一檔一規則，沿用 framework schema
│   ├── SLV-009.yaml
│   └── ...
├── failure-patterns/                  # FPL 失敗模式（external 預設）
│   ├── FPL-001-temporal-inconsistency.md
│   ├── FPL-INDEX.md                   # 索引（自動產出，CI 校驗）
│   └── templates/                     # 共享模板
├── metadata/
│   ├── CONTRIBUTORS.yaml              # GPG fingerprint allow-list（reviewer 名單）
│   ├── HISTORY.yaml                   # append-only 變更摘要（每次 PR 自動 append）
│   ├── SCHEMA-VERSION.yaml            # 本 registry 的 schema_version
│   └── REJECTED-LOG.yaml              # Hub 端駁回紀錄（與 Client 端 REJECTED-LOG 對齊）
├── tools/                             # Hub 端工具（建議以 git submodule 引用 framework）
│   ├── pii_scanner.py                 # G-30.7 二次掃描用，與 framework 同源
│   ├── anonymizer.py                  # 同上
│   └── schema_validator.py            # SLV YAML / FPL frontmatter 校驗
├── .github/
│   └── workflows/
│       ├── hub-push.yml               # D-30.10 PR 驗證 pipeline
│       └── nightly-audit.yml          # 每日 PII 全掃 + schema sweep
└── docs/
    └── ARCHITECTURE.md                # Hub 端維運手冊（可選）
```

**強制規則**：
- `rules/` 下每個 SLV 一個檔，命名 `SLV-XXX.yaml`，schema 與 framework `slv_generator._validate_rule_doc()` 完全相容（不允許 Hub 端額外擴充必填欄位）。
- `failure-patterns/` 下每個 FPL 一個檔，命名 `FPL-XXX-<kebab-title>.md`，frontmatter schema 對齊 framework `knowledge/failure-patterns/templates/`。
- `metadata/HISTORY.yaml` append-only — CI 校驗禁止刪除既有條目（hash chain 確保完整性）。

---

## 參、Branch-per-rule 策略

### 3.1 命名規則

| 變更類型 | Branch 前綴 | 範例 |
|---------|-----------|------|
| 新增 SLV | `rule/SLV-XXX-add` | `rule/SLV-012-add` |
| 修改 SLV | `rule/SLV-XXX-update` | `rule/SLV-008-update` |
| 駁回 / 撤銷 SLV | `rule/SLV-XXX-revoke` | `rule/SLV-099-revoke` |
| 新增 FPL | `fpl/FPL-XXX-add` | `fpl/FPL-005-add` |
| Metadata 維運 | `meta/<topic>` | `meta/contributor-rotation` |

### 3.2 PR 標題與 body

- 標題：`[SLV-XXX] <kebab-title>` 或 `[FPL-XXX] <kebab-title>`
- Body 必填：
  - 變更摘要（Why）
  - 對應 framework FPL / SLV 連結
  - PII 自審清單（pusher 簽名）
  - GPG signed commits 檢查項

### 3.3 Merge 策略

- `main` 設定 branch protection：禁止直接 push、禁止 force-push、禁止 delete。
- 所有 PR 必須通過 4 個 GitHub Action job（D-30.10）：`pii-rescan` / `gpg-verify` / `schema-validate` / `anonymize-check`。
- Reviewer signoff：至少 1 名 `metadata/CONTRIBUTORS.yaml` 內登記的 reviewer 簽核（可由 self-review，沿用 OPEN-G.2 單人 RACI 決議）。
- 合入方式：squash merge（保留單一可追溯 commit），合入後自動觸發 nightly audit。

---

## 肆、PR-review Gate 流程（與 D-30.10 對應）

```
[1] Pusher 在本地透過 hub_sync.py push() 建立 PR
   ↓ 本地 PII Scanner + Anonymizer 已過（G-30.7 第一道）
[2] PR 觸發 .github/workflows/hub-push.yml（D-30.10）
   ↓ Job: pii-rescan         → 對 PR diff 重跑 pii_scanner.py（防本地漏掃）
   ↓ Job: gpg-verify         → 驗 commit signature 對應 CONTRIBUTORS allow-list
   ↓ Job: schema-validate    → SLV YAML / FPL frontmatter schema 驗證
   ↓ Job: anonymize-check    → 客戶名 / 內部專案名殘留掃描
[3] 任一 job 失敗 → PR 自動 fail → 不可 merge
[4] 全綠 → reviewer 人工 review YAML diff → approve
[5] Squash merge → main → metadata/HISTORY.yaml append-only 紀錄
[6] Nightly audit（次日 02:00 UTC）對全 repo 重掃 PII + schema sweep
```

**禁止行為**：
- 在 PR 內以「force-push」覆寫已 review 過的 commit（GPG audit 鏈會中斷）。
- 略過 `gpg-verify` job（即便 reviewer 是 maintainer 也不可 admin override）。
- 將失敗 PR 刪除 branch 後重開以「洗白」歷史 — `metadata/HISTORY.yaml` 仍會記錄 rejected 紀錄。

---

## 伍、trust_level 升級流程對應

本規格不重複定義升級階段，沿用 [trust-ladder.md](trust-ladder.md) 三階 trust_level（external / proposed / verified）+ `review_status` 子欄位。Hub 端對應行為：

| Hub 端動作 | Client 端 trust_level | review_status |
|-----------|---------------------|--------------|
| Hub PR 合入 `main`（rule 首次發布） | Client pull 後寫 `external` | `pending` |
| Client 人工 review 後同意適用 | （Client 自行）改 `verified` | `reviewed` |
| Client 升 verified → push back to Hub？ | **不適用** — verified 是 Client per-instance 決議，不回流 Hub |
| Hub 駁回 PR | Client 端不會看到該規則 | n/a |
| Hub 端撤銷已合入規則 | Client 下次 pull 時 hub_merge 偵測 base→remote diff → HUMAN_PENDING | n/a |

**關鍵對齊**：Hub 端規則一律是 `external` 來源；`verified` 是 Client 端的個體承諾，**不**因 Hub PR review 通過就自動升級。這保留 RuleOverwriteProtected 寫入保護鏈（CLAUDE.md Rule 9.11.2）的單向流動。

---

## 陸、與 hub-registry.yaml allow-list 的對應

[hub-registry.yaml](../hub-registry.yaml) 的 `allowed_endpoints[]` 必須與本規格描述的 Hub repo 一一對應：

| `allowed_endpoints[]` 欄位 | 來源 |
|--------------------------|------|
| `url` | Hub repo `git+https://github.com/<org>/<repo>` |
| `protocol` | 固定 `git+https`（M2 不支援其他協議） |
| `branch` | 固定 `main`（branch-per-rule 都是 PR 階段，最終匯入 `main`） |
| `gpg_fingerprint` | Hub `metadata/CONTRIBUTORS.yaml` 內某條 reviewer 的 fingerprint |

**deny_unlisted: true** 為硬性宣告（hub_sync.py 同步硬編碼）— 即便修改 yaml 也無法放行非 allow-list endpoint，必須以一次性 `SDD_HUB_ALLOWLIST_OVERRIDE=<reason>` 並寫 audit log（G-30.6）。

---

## 柒、治理規則 G-30.1~G-30.8 在 Hub 端的執行落點

| 規則 | Hub 端對應落點 |
|------|--------------|
| G-30.1 Pre-push PII 強制 | `pii-rescan` job（D-30.10）對 PR diff 重掃，補強 Client 漏掃 |
| G-30.2 商業機密 pattern | `pii-rescan` 同 job 套用 deny-list（CONTRIBUTORS.yaml `deny_list_customers/products`） |
| G-30.3 預設 opt-in | Hub 端不直接強制（在 Client `hub_sync.push()` 已強制）；本規格 §參 PR body 要求 pusher 自審 |
| G-30.4 Pull 預設 external | Hub 規則一律以 `trust_level: external` 發布（pre-merge schema-validate 強制檢查） |
| G-30.5 升級需 reviewer signoff | 不適用 Hub（verified 是 Client per-instance）；Hub 內 PR approve 是另一條 audit chain |
| G-30.6 Endpoint allow-list | Client 端強制；Hub 端被動（GitHub repo URL 即 endpoint） |
| G-30.7 雙層掃描 | **Hub 端是第二層**：本規格 §肆 PR pipeline `pii-rescan` job |
| G-30.8 Quarantine 不可自動清除 | Hub 端對應：失敗 PR 不可 force-delete branch；`metadata/REJECTED-LOG.yaml` append-only |

---

## 捌、Conflict Resolution 策略

Hub 端不解 Client 端衝突 — 衝突解析屬 Client 職責，由 [`hub_merge.py`](../../tools/fsm_runtime/hub_merge.py)（D-30.8）執行三向合併（base / local / remote）。Hub 端只保證：

1. `main` 上每條規則的歷史線性（squash merge）。
2. 規則檔內容是 fully-validated（schema + PII 雙掃過）。
3. `metadata/HISTORY.yaml` 提供 base 比對基準（Client `hub_merge.py` 計算三向 diff 用）。

衝突 artifact 落地路徑（Client 端，**非** Hub 端）：
- `knowledge/hub/CONFLICTS/SLV-XXX-{timestamp}.yaml`（trust-ladder.md §陸）
- 解決後刪除 conflict artifact + commit，本機事務閉環，**不**回流 Hub。

---

## 玖、Schema Version 與向後相容承諾

| 版本 | 範圍 | 承諾 |
|------|------|------|
| `phase-f-v1` | 本規格首版 | 對應 Phase F M2 凍結；rules/ 結構、metadata/ schema 不再有 break-change 直到 Phase G |
| 預期演進 | 新增欄位 | 必須對 Client `_validate_rule_doc()` 向後相容（unknown fields 忽略而非報錯） |
| break-change | 結構變更 | 必須 bump 至 `phase-g-v1`，並在 `metadata/SCHEMA-VERSION.yaml` 並列雙版本至少 1 個 minor cycle |

**強制規則**：
- Client 端 `hub_sync.pull()` 讀 Hub `metadata/SCHEMA-VERSION.yaml`，schema 不相容時拒絕 pull 並提示升 framework。
- 本規格 §貳 目錄結構任何變動 → bump schema_version；trust_level 列舉值絕對不擴增（CLAUDE.md Rule 9.12.2）。

---

## 拾、驗收條件

- [ ] Hub repo 完整實作 §貳 目錄結構（rules/ failure-patterns/ metadata/ .github/workflows/ tools/）
- [ ] `metadata/HISTORY.yaml` append-only 性質有 CI 校驗（hash chain 或對比前次 commit）
- [ ] `.github/workflows/hub-push.yml` 4 個 job 全綠才能 merge（D-30.10 對應）
- [ ] `metadata/CONTRIBUTORS.yaml` GPG fingerprint 與 Client `hub-registry.yaml` allow-list 對齊
- [ ] PR-review gate 流程在 fork 範例 repo 驗證至少一條 SLV 與一條 FPL 的端到端流動

---

## 拾壹、相關文件

- 治理規則：[HUB-GOVERNANCE-SPEC.md](../../docs/06_quality/HUB-GOVERNANCE-SPEC.md)
- 信任階梯：[trust-ladder.md](trust-ladder.md)
- Client allow-list：[hub-registry.yaml](../hub-registry.yaml)
- PR-review pipeline：[.github/workflows/hub-push.yml](../../.github/workflows/hub-push.yml)（D-30.10）
- Client Hub Sync：[tools/fsm_runtime/hub_sync.py](../../tools/fsm_runtime/hub_sync.py)
- 衝突合併：[tools/fsm_runtime/hub_merge.py](../../tools/fsm_runtime/hub_merge.py)
- CI/CD 規格：[cicd/SDD_HUB_SYNC.md](../../cicd/SDD_HUB_SYNC.md)
- 藍圖來源：[build/planning/active/SDD_improving_Automation_05.md](../../build/planning/active/SDD_improving_Automation_05.md) §4.2 D-30.9

---

**作者**: Architect（Phase F 單人 RACI）
**對應 Issue**: [#1 ACT-030](https://github.com/wuweihungmobile/AISDLC_SDD/issues/1)
