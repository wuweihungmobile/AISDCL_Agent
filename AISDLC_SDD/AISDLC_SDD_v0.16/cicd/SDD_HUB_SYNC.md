# SDD Hub Sync — ACT-030 / Phase F M2
# Cross-Project Learning Hub CI/CD 規格

**版本**: v1.0
**建立日期**: 2026-04-25
**對應 ACT**: Phase F / M2 / ACT-030
**文件類型**: 部署規格（Deployment Specification）
**所屬分類**: `AISDLC_SDD_v0.01/cicd/`
**FSM 狀態**: `HUB_SYNC`（非阻塞觀測）
**對應規格**: [`docs/06_quality/HUB-GOVERNANCE-SPEC.md`](../docs/06_quality/HUB-GOVERNANCE-SPEC.md)、[`knowledge/hub/trust-ladder.md`](../knowledge/hub/trust-ladder.md)

---

## 🎯 目的

把單一 AISDLC-SDD 實例與「跨專案 Learning Hub（FPL/SLV 共享 registry）」串接，讓新專案能繼承既有失敗模式與驗證規則，並在 governance 紅線內安全地貢獻新規則。

1. **Pull**：session_start 自動拉取 external 規則（24h cache、非阻塞失敗）
2. **Push**：人工 confirmed 後，PII 強制掃描 + 雙層驗證 + GPG 簽章
3. **Promote**：external → verified 升級需人工 reviewer signoff（沿用 ACT-028 schema）
4. **Conflict**：3-way merge；衝突進 HUMAN_PENDING；verified 永不被覆寫

> **Design Intent**：HUB_SYNC 是「觀測」而非「阻塞」狀態 — Hub 失效（timeout / 500 / GPG fail）一律不升 ESCALATION，session 繼續正常運作。

---

## 🏗️ Pipeline 架構

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
      └──── 3-way merge (local / cached-base / hub-remote) ─────┘
```

---

## 🔁 CI/CD 步驟

### 本地 Pipeline（`session_start` + manual CLI）

| Step | 觸發點 | 動作 | 失敗模式 |
|------|--------|------|---------|
| 1 | `SessionStart` hook | `HubSyncClient.pull()` — 若 cache > 24h 才實打 | non-blocking warn 寫 `additionalContext` |
| 2 | 使用者執行 `python -m tools.fsm_runtime.hub_sync push <artifacts>` | dry-run 強制；除非 `SDD_HUB_PUSH_CONFIRMED=<reason>` 設妥 | 預設 dry-run，不真 push |
| 3 | push 內部 Step 1 | PII Scanner（L2 patterns）→ 命中即 `QUARANTINE-{date}-{seq}.yaml` 寫 `build/reports/hub/` | 中止本批 push |
| 4 | push 內部 Step 2 | Anonymizer（L1 patterns）替換為 `<CATEGORY_X>` placeholder | — |
| 5 | push 內部 Step 3 | 二次 L2 scan（防 anonymizer 漏網，G-30.7） | 命中即 quarantine 中止 |
| 6 | push 真寫 | 寫入 `build/reports/hub/push-outbox/<endpoint_id>/` 供 git push 使用 | 寫 `PUSH-AUDIT.yaml` 紀錄 |
| 7 | promote | `hub_sync promote <SLV-XXX.yaml> --reviewer <name>` 將 external → verified | YAML schema 驗證失敗即拒 |

### Hub 端 Pipeline（GitHub Actions sample）

> 本檔僅描述 *contract*。實際 workflow YAML：
> - **Framework repo 內的 sample**：`AISDLC_SDD_v0.01/.github/workflows/hub-push.yml`（D-30.10，巢狀路徑為刻意，僅作為參考實作；framework repo 不執行）
> - **下游 Hub Registry repo 端執行位置**：複製至自家 `.github/workflows/hub-push.yml`
> - 對比 `fsm-chaos-nightly.yml`（Rule 9.9.4 框架自我 dogfood，必置於 framework repo root）與 `drift-daily.yml`（Rule 9.17.4 同上），二者皆 active；`hub-push.yml` 唯一仍為 reference-only。

| Stage | 動作 | 對應 G-30 規則 |
|-------|------|--------------|
| `pii_double_scan` | 在 PR 內以 `pii_scanner.py` 對所有 changed files 二次掃描 | G-30.7 |
| `gpg_verify` | 驗證 commit GPG 簽章 fingerprint 匹配 `hub-registry.yaml` allow-list | G-30.6 |
| `schema_validate` | 對 `rules/*.yaml` 跑 `slv_generator._validate_rule_doc()` | G-30.5 |
| `auto_close` | 任一 stage fail → 自動 close PR + 開 incident issue | G-30.1 / G-30.2 |

---

## 📐 Schema 與 artifact

| 路徑 | 說明 |
|------|------|
| `knowledge/hub-registry.yaml` | endpoint allow-list、sync_policy、cache 路徑 |
| `tools/fsm_runtime/anonymizer_rules.yaml` | L0/L1/L2 patterns + allow_list / deny_list |
| `build/reports/hub/QUARANTINE-{date}-{seq}.yaml` | PII 命中時的 quarantine 紀錄（log 不留原文，§5.1）|
| `build/reports/hub/PUSH-AUDIT.yaml` | 每次 push attempt 的 events log |
| `build/reports/hub/pull-cache/META.yaml` | 24h cache TTL 元資料 |
| `build/reports/hub/pull-cache/<endpoint_id>/` | 各 endpoint 拉取下來的 mirror |
| `knowledge/hub/CONFLICTS/<rule_id>-<ts>.yaml` | 3-way merge 衝突報告 |
| `knowledge/hub/REJECTED-LOG.yaml` | 拒絕匯入的 hub 規則歷史 |
| `build/reports/hub/push-outbox/<endpoint_id>/` | confirmed push 的暫存 outbox |

---

## 🔐 治理紅線（直接引用，不重述）

- G-30.1 ~ G-30.8 治理規則：見 [HUB-GOVERNANCE-SPEC.md §參](../docs/06_quality/HUB-GOVERNANCE-SPEC.md)
- 信任階梯升級：見 [trust-ladder.md §肆](../knowledge/hub/trust-ladder.md)
- Override env：`SDD_HUB_PUSH_CONFIRMED=<reason>`（必填）、`SDD_HUB_ALLOWLIST_OVERRIDE=<audit_reason>`（記 audit log）、`SDD_HUB_DISABLE=1`（停用 auto-pull）

---

## 🧪 驗收條件（A-30.1 ~ A-30.5）

| ID | 描述 | 自動化測試對應 |
|----|------|--------------|
| A-30.1 | 兩專案 push/pull 端到端：PII 擋件 + anonymize + 升 verified | `tests/test_hub_sync.py::test_a30_1_two_project_flow` |
| A-30.2 | 20 條 fixture 100% PII 替換 + 語義骨架保留 | `tests/test_hub_sync.py::test_a30_2_anonymize_coverage` |
| A-30.3 | verified 衝突 → HUMAN_PENDING（不覆寫） | `tests/test_hub_sync.py::test_a30_3_verified_conflict_blocked` |
| A-30.4 | 非 allow-list endpoint → 拒連 | `tests/test_hub_sync.py::test_a30_4_endpoint_allowlist` |
| A-30.5 | Hub 失效（timeout / 500 / GPG fail）→ 非阻塞，FSM 不升 ESCALATION | `tests/test_hub_sync.py::test_a30_5_failure_non_blocking` |

---

## 🚦 FSM 整合

| 事件 | FSM 動作 |
|------|---------|
| `HubSyncClient.pull()` 開始 | `FSMRuntime.enter_hub_sync(direction="pull")` 進入 HUB_SYNC |
| pull 成功 | `exit_hub_sync("success")` 回 resume_state |
| pull failed | `exit_hub_sync("failed")` 回 resume_state（不升 ESCALATION） |
| `push()` 結果含衝突或 quarantine | `exit_hub_sync("partial")` → HUMAN_PENDING |
| 觀測期間 tool calls | **不阻擋**（HUB_SYNC ∈ OBSERVATION_STATES，與 PRODUCTION_SIGNAL / LEARNING_COMMIT 同類）|

---

## 🛡️ Rollback

```markdown
**Rollback**:
- Code Revert: git revert <PR-SHA>
- State Cleanup:
    rm -rf build/reports/hub/pull-cache/
    rm -rf build/reports/hub/push-outbox/
    rm -rf knowledge/hub/CONFLICTS/
- Env / Config: unset SDD_HUB_PUSH_CONFIRMED / SDD_HUB_ALLOWLIST_OVERRIDE
- 緊急停 Hub：設 `SDD_HUB_DISABLE=1` 並通知使用者
```

---

## 📁 相關文件

- 治理規格：[`HUB-GOVERNANCE-SPEC.md`](../docs/06_quality/HUB-GOVERNANCE-SPEC.md)
- 信任階梯：[`trust-ladder.md`](../knowledge/hub/trust-ladder.md)
- Anonymizer 規則：[`anonymizer_rules.yaml`](../tools/fsm_runtime/anonymizer_rules.yaml)
- Registry：[`hub-registry.yaml`](../knowledge/hub-registry.yaml)
- FSM 狀態：[`SDD_FSM_ENGINE.md`](../workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md)（ACT-030 段落，於 M2 末尾追加）

---

**所屬 Phase**: Phase F（精準閉環之上的跨實例學習）
**前置 Phase**: Phase E 全量完成（phase-e-final tag）
**驗收 tag**: `phase-f-m2`
