# SD_Improving_05 W0 T0-6 — TokenGuardPlugin 子模組命名設計

| 項目 | 內容 |
|------|------|
| 文件版本 | v1.1（W0 G0 三方覆驗後 SA 簽核） |
| 建立日期 | 2026-05-16 |
| 適用 Wave | W2 將實作；W0 只完成命名設計 |
| 對應 SD_05 | §3 Wave 表 W2 / §6 Plugin 拆分藍圖第 1 列（TokenGuardPlugin +180 → 308 LOC） |
| 規範來源 | SD_05 §5 紅線 #4「LOC 超 250 必拆 package」 |

---

## 1. W2 吸收方法群（由 `_runner_internals.py` 下沉）

| # | 來源方法 | 預估 LOC | 子模組歸屬 |
|---|---------|----------|----------|
| 1 | `_execute_prompt`（token watch 部分） | ~50 | `watcher.py` |
| 2 | `_should_compact_now` | ~25 | `thresholds.py`（合併） |
| 3 | `_send_compact` | ~40 | `compactor.py` |
| 4 | `_get_dynamic_compact_threshold` | ~30 | `thresholds.py`（合併） |
| 5 | `_verify_correction_applied`(git diff 部分) | ~35 | `git_verifier.py` |

加上既有 `token_guard_plugin.py` (~120 LOC) 與 per-step override（M-7, +30 LOC），總計約 **330 LOC**，超 250 → 必拆 package。

---

## 2. token_guard/ package 結構（W2 實作目標）

```
autoclaude/plugins/token_guard/
├── __init__.py              # re-export TokenGuardPlugin；保持外部 import 不變
├── plugin.py                # TokenGuardPlugin 主類別（≤ 80 行）
│                            # - name/priority/subscribed_phases
│                            # - on_event 分派至子模組
│                            # - record_compact_failure() 唯一入口（M-2 拔雙寫）
├── watcher.py               # token_pct 監測邏輯（≤ 80 行）
│                            # - parse_token_usage(output) -> float | None
│                            # - 7 個 context regex（M-8 涵蓋率測試對象）
├── compactor.py             # /compact 發送 + 結果驗證（≤ 80 行）
│                            # - send_compact(executor, ctx) -> bool
│                            # - 連續失敗計數（從 record_compact_failure 唯一更新）
├── thresholds.py            # 門檻計算（compact / halt + per-step override，≤ 80 行）
│                            # - should_compact(token_pct, cfg) -> bool
│                            # - should_halt(token_pct, cfg) -> bool
│                            # - dynamic_compact_threshold(attempt, max_retries) -> float
│                            # - resolve_per_step_config(task, global_cfg) -> TokenGuardConfig
│                            #   （M-7：PlaybookTask.token_guard 優先序）
└── git_verifier.py          # git diff 驗證（≤ 80 行）
                             # - verify_correction_applied(repo_path, hint) -> bool
                             # - 觸發於 PRE_CORRECTION 或 POST_CORRECTION
```

合計 5 × 80 = **400 LOC**（檔內含註解、空行；check_loc_budget 實際 count 預估 ≤ 200 per file，遠低於 250 上限）。

---

## 3. 對外 API 不變（保證 import 相容）

- `autoclaude.plugins.token_guard_plugin` 仍可 import → 在 W2 切換時，留 1 個 sub-task 週期作為 shim：
  ```python
  # autoclaude/plugins/token_guard_plugin.py（W2 中間階段）
  from .token_guard import TokenGuardPlugin  # noqa: F401
  ```
- W3 (或 W6) 清除 shim
- `from autoclaude.plugins import TokenGuardPlugin` 在 `__init__.py` 切換 import 路徑即可

---

## 4. W2 切換驗收條件（與 SD_05 §3 G2 一致）

| 項目 | 目標 |
|------|------|
| 全測 | ≥ 1199 passed（不下降） |
| equivalence 13 fixture | 全綠 |
| `tools/check_loc_budget.py` | token_guard/ 各 module ≤ 250；total 不增加 |
| 雙寫消除 | `grep "_consecutive_compact_failures\|compact_failure_count" autoclaude/execution/_runner_internals.py` 回傳 0 行 |
| `tests/contract/test_playbook_yaml_backward_compat.py` | 60+ YAML 載入綠 + per-step token_guard 優先序 AC |
| coverage | ≥ 82% |

---

## 5. 子模組間相依規則

- ❌ 子模組之間**不可** import 其他子模組（除了 `plugin.py` 作為 facade 可 import 所有子模組）
- ❌ 子模組**不可** import 其他 Plugin（紅線 #1）
- ❌ 子模組**不可** import `infra/`（紅線 #2）
- ✅ 子模組可 import `core/hookspec.py`、`utils/config.py`、`models/`
- ✅ 子模組可呼叫被 plugin.py 注入的 port 抽象（IExecutor / IEvaluator）

---

## 6. 風險與緩解

| 風險 | 緩解 |
|------|------|
| import 路徑改變導致下游測試大量 patch 失敗 | W5 批 1 統一處理；W2 期間維持 shim |
| watcher.py 7 個 regex 涵蓋率不足 | W5 批 3-B 補 `tests/test_token_pattern_coverage.py` + ≥ 30 樣本 |
| per-step override 與全域 cfg 優先序混亂 | thresholds.py 統一 `resolve_per_step_config()` 入口 + AC 鎖定 |
| compactor.py 雙寫遺漏 | M-2 強制：`record_compact_failure()` 由 compactor 唯一呼叫，watcher / plugin 透過事件廣播 |

---

## 7. 與 W0 hookspec 擴張的綁定

W0 T0-1 已新增 phase：`PRE_COMPACT`、`POST_COMPACT`（PHASE_RESULT_CONTRACT 對應 `{ResourceRequest, VetoResult}` / `{ResourceRequest}`）。W2 切換時：

- `plugin.py` 在 compact 行為前後 emit 上述 phase（透過 attach_bus 取得 EventBus）
- 其他 Plugin（如 CrossStepValidatorPlugin）可訂閱 `PRE_COMPACT` 並 `VetoResult` 否決 compact（例如 git 工作樹有未提交變更時）

---

**簽核狀態**：
- ✅ Dev（命名設計，W0 T0-6，2026-05-16）
- ✅ Architect / SA / SD 三方覆驗（W0 G0 簽核時一併確認 2026-05-16）
- ✅ QA 四方核准（W0 G0 通過 2026-05-16）
