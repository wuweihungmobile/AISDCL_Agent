# SDD Drift Monitor — Continuous Drift Monitor 規格（Phase G M4 / ACT-039/040）

**對應規則**: CLAUDE.md §9.17
**FSM 狀態**: `DRIFT_OBSERVATION`（observation type，不阻塞 tool calls）
**對應 tag**: `phase-g-final`

---

## 1. drift_score 計算公式（v1）

### 1.1 API drift（權重 0.6）

```
api_endpoints_spec  = parse openapi.yaml -> set of "{METHOD} {path}"
api_endpoints_code  = scan code routes (FastAPI/Flask/Express) -> set of "{METHOD} {path}"
api_drift = |spec △ code| / max(|spec ∪ code|, 1)
```

### 1.2 Type drift（權重 0.4）

```
types_spec = extract types from FRD (### type: Foo with fields {a, b, c})
types_code = scan code class/enum definitions -> {class: {fields}}
type_drift = sum_per_type(missing_fields(spec, code)) / max(total_spec_fields, 1)
```

### 1.3 總分

```
drift_score = 0.6 * api_drift + 0.4 * type_drift
```

範圍：[0, 1]。0 = 完全對齊，1 = 完全脫節。

### 1.4 v2 預留：Behavior drift（NLP AC↔Test）— 暫不實作

---

## 2. 觸發點

| 觸發點 | 動作 | 阻擋？ |
|-------|------|-------|
| `git commit` | PostCommit hook 計算 drift_score | **不阻擋**（Rule 9.17.1，僅寫 .git/COMMIT_DRIFT_WARNING） |
| `drift_score ≥ 0.3`（單次） | 自動 enter `DRIFT_OBSERVATION` | 不阻塞 |
| 連續 3 commits drift_score ≥ 0.3 | 自動轉 SPEC_AUDIT（Rule 9.17.3） | 不阻塞但要求 audit |
| 02:30 UTC daily | 產出 `build/reports/drift/DAILY-{date}.md` 滾動 7 天（Rule 9.17.4） | — |

---

## 3. 報告路徑

| 類型 | 路徑 | 寫入時機 |
|------|------|---------|
| 單 commit drift | `build/reports/drift/COMMIT-{sha}.yaml` | PostCommit hook |
| 每日滾動 | `build/reports/drift/DAILY-{YYYY-MM-DD}.md` | cron 02:30 UTC |
| 連續 drift 警告 | `build/reports/drift/CONSECUTIVE-{date}.yaml` | 連續 3 次觸發時 |

---

## 4. PostCommit Hook 約束

- 機制：git native（per OPEN-G.4 — 與 Claude Code session lifecycle 解耦）
- Budget：< 2s（Rule 9.17.1，超時自動 skip 並寫 warning）
- 安裝：opt-in via `tools/install_post_commit_hook.sh` / `.ps1`，非 settings.json 強制
- 失敗策略：**advisory** — 不阻擋 commit，僅寫 `.git/COMMIT_DRIFT_WARNING` 與 `build/reports/drift/COMMIT-{sha}.yaml`

---

## 5. DRIFT_OBSERVATION 狀態（FSM 整合）

- 類型：`observation`（同 PRODUCTION_SIGNAL/LEARNING_COMMIT/HUB_SYNC/TRAJECTORY_PREDICTED）
- 不阻塞 tool calls
- 入口：任何 retry-prone state（非 Terminal/觀測態之外的 state）；以 `enter_drift_observation(commit_sha, score)` 顯式進入
- 出口：
  - `continue` → resume_state（單次 drift，警告但繼續）
  - `switch_to_audit` → SPEC_AUDIT（連續 3 commits ≥ 0.3 累積）
- 必須加入 `tools/fsm_runtime/formal/SDD_FSM.tla` 的 `ObservationStates`，重跑 TLC 驗證 reachable coverage 仍 ≥ 95%（Rule 9.18.1）

---

## 6. 驗收

- [ ] PostCommit hook 100 commit 平均 < 2s（Rule 9.17.1）
- [ ] API drift 對 fixture 準確率 ≥ 95%
- [ ] 連續 drift → SPEC_AUDIT 整合測試通過
- [ ] TLC 重跑 27/27 = 100% reachable coverage（Rule 9.18.3 守門）
- [ ] DAILY drift report 連續 7 天累積驗證
