# ADR-SD09-004 — trace_id multi-process 邊界傳播

| 項目 | 內容 |
|------|------|
| 文件版本 | **v1.0（PM 拍板路徑 (b) W3C TraceContext finalized；未選路徑 (a)/(c) 已 git rm）** |
| 建立日期 | 2026-05-19 |
| 最後更新 | **2026-05-20**（T0-F4：PM #4 拍板 (b) W3C TraceContext → 移除路徑 (a)/(c) 章節 + Execution_Guide W3 同步）|
| 狀態 | **ACCEPTED — PM 形式核准 2026-05-20（場景 A dev 自核）** |
| 對應 Sprint | SD_Improving_09 議題 F（trace_id multi-process）|
| 前置 | [ADR-SD08-004](ADR-SD08-004-observability-port.md) v1.0（同 process trace_id 已落地）|

---

## §1. 背景

SD_08 W4 落地 `trace_id: ContextVar` 同 process 邊界傳播 + NonBlockingStreamReader `copy_context()` daemon thread 包裝。

SD_08 §7 L1 限制：**trace_id 在 subprocess 邊界不傳播**（ContextVar 限同 process）；SD_09 W3 落地 multi-process 解決方案。

---

## §2. 決策（**PM #4 拍板 (b) W3C TraceContext finalized 2026-05-20**）

### §2.1 拍板結果

| 項目 | 內容 |
|------|------|
| PM 拍板路徑 | **(b) W3C TraceContext header（`TRACEPARENT` env）為 SD_10 OTel 過渡** |
| 拍板日 | 2026-05-19（PM zero-trust audit） |
| 形式核准 | 2026-05-20（場景 A dev 自核 commit） |
| importlinter contract 結果 | **Rule 7 已覆蓋 plugin 端禁直接 import；不新增 Rule 8**（**Arch-M3 / SD-M2 修復**：Rule 8 為冗餘，改採 contract test 覆蓋） |
| AC16 條目數 | **3**（路徑 b） |
| 預估 W3 PD | 3 PD |

> **未選路徑（已 git rm）**：
> - 路徑 (a) 環境變數 `AUTOCLAUDE_TRACE_ID`：T0-F4 已刪除 T3-F1a~F4a 章節
> - 路徑 (c) 延 SD_10：T0-F4 已刪除延期 backlog 章節
>
> **Rule 8 取消新增決議**：Rule 7 「Plugins must not directly import utils.observability helpers (use IObservabilityPort)」已禁 plugin import `utils.trace_context` 整個模組（含路徑 b 新增的 `to_traceparent_header` / `from_traceparent_header`）。新增 Rule 8 將與 Rule 7 重複；改採 contract test `tests/contract/test_trace_context_plugin_isolation.py`（≥ 2 case：plugin path 禁直接 import / propagate_to_subprocess_env helper 走 Port 注入）覆蓋。**保持 importlinter 7 kept / 0 broken**（W3 G3 + W6 G6 驗證統一）。

### §2.2 W3 落地任務（路徑 b 專屬）

W3 落地任務見 [SD09_Execution_Guide.md §3 W3 — F 議題群路徑 (b)](../../05_development/SD09_Execution_Guide.md)。

### §2.3 subprocess 注入點全覆蓋清單（**SD-C5 修復：9 處檔案明確列舉**）

1. `autoclaude/perception/pty_wrapper.py`（PTY subprocess 啟動）
2. `autoclaude/execution/cross_step_validator.py`（git status 偵測 subprocess）
3. `autoclaude/execution/pre_run_validator.py`（pre-run 環境檢查）
4. `autoclaude/execution/evaluator.py`（evaluator_command 子進程）
5. `autoclaude/execution/mutation_applier/_conditional.py`（mutation 條件評估 subprocess）
6. `autoclaude/plugins/fast_path_plugin.py`（fast-path 子進程）
7. `autoclaude/plugins/token_guard/git_verifier.py`（git verifier subprocess）
8. `autoclaude/decision/prompt_builder.py`（prompt 建構 subprocess 呼叫）
9. `autoclaude/core/services/mutation/_conditional_evaluator.py`（mutation 條件評估）

> **集中式 helper 建議（SD-C5 / 補強 1）**：避免散裝改 9 處遺漏，於 `autoclaude/utils/trace_context.py` 內聚 helper：
> ```python
> def propagate_to_subprocess_env(env: dict[str, str]) -> dict[str, str]:
>     """將當前 ContextVar trace_id 寫入 env dict（路徑 b 用 TRACEPARENT W3C header）。"""
>     ...
> ```
> 9 處注入點統一呼叫此 helper（traceability + 單元測試集中於 `tests/utils/test_trace_context_subprocess_env.py`；R22 命名一致性：實作沿用 W0 既有檔擴展 W3C 區段，不另建 _w3c.py）。
>
> **當前實作狀態（2026-05-21 W0 校正）**：`autoclaude/utils/trace_context.py:136-146` 已存在 `propagate_to_subprocess_env(env)` helper，但**過渡實作仍寫入 `AUTOCLAUDE_TRACE_ID` 環境變數**（路徑 a 命名殘留），**非 W3C `TRACEPARENT` 標準格式**。
>
> W0 不變更此實作（避免在 PM 拍板 (b) 後 W1-W2 之間出現相容性窗口）；**W3 T3-F1b 落地時統一改寫**為：
> - 讀取 ContextVar trace_id → 組裝 `traceparent` 格式：`00-<32hex_trace_id>-<16hex_span_id>-<2hex_flags>`
> - env 鍵名 `AUTOCLAUDE_TRACE_ID` → `TRACEPARENT`（搭配 caller env override 處理 §2.4）
> - 9 處注入點 caller 不變（仍呼叫 helper），W3C 標準化集中於本檔
>
> 對應 W3 G3 驗證命令：`grep -n "TRACEPARENT\|traceparent" autoclaude/utils/trace_context.py`（W3 落地後命中；W0~W2 期間僅 `AUTOCLAUDE_TRACE_ID`）。

### §2.4 env override 衝突處理

- caller 已設 `TRACEPARENT` 時不覆蓋（讀取 + 傳播 W3C header）

---

## §3. 模組內聚設計（**SD M5 + Architect 補強建議 7 修復 + Arch-C1/SD-C2 LOC 影響分析**）

路徑 (b) W3C TraceContext parser **內聚於 `autoclaude/utils/trace_context.py`**（不新建模組）：
- 新增 `to_traceparent_header() -> str`
- 新增 `from_traceparent_header(h: str) -> str`
- 新增 `propagate_to_subprocess_env(env: dict) -> dict`（集中式 helper，9 處注入點統一呼叫）
- 與既有 `trace_id: ContextVar` + `with_trace_id()` + `start_thread_with_context()` 共置

### §3.0 LOC 影響分析（**Arch-C1 / SD-C2 修復**）

| 項目 | 當前 LOC | 路徑 b 落地後預估 | LOC tier 狀態 |
|------|---------|------------------|--------------|
| `autoclaude/utils/trace_context.py` | **156 LOC**（2026-05-21 W0 重測；W0 過渡 helper）→ **229 LOC 實測**（R41 路徑 b 已落地，見下方 §3.0 R41 校正 note） | ~195 LOC（W0 預估）→ **229 LOC 實測**（W3C docstring + 嚴格格式驗證較預估多，仍 ≪ 750） | **unclassified**（位於 `utils/`，不在 LOC tier patterns 內 → `tools/check_loc_budget.py` 走 `ABSOLUTE_LIMIT = 750`）|

**注意事項**：
- 既有 docstring 自我宣稱「≤ 150 LOC，contract tier」**為錯標**（已 W0 修正：實測 156 LOC 已超 150；另一 Agent 處理 docstring 修正，本 ADR 不重複）
- 路徑 b 落地後 ≤ 195 LOC，**仍遠低於 absolute_limit 750**
- **建議**：路徑 b 落地時於 `.loc-budget.toml` 顯式標 `trace_context.py` 為 contract tier ≤ 400（雙簽核 — Architect + Tech Lead），讓 `check_loc_budget.py` 正確識別並警示
- T3-F1b 補預檢命令：`wc -l autoclaude/utils/trace_context.py`（落地後驗證 ≤ 400 警示）

> **R41 校正（2026-05-28，SD zero-trust audit P2）**：路徑 b W3C helper（`to_traceparent_header` / `from_traceparent_header` / W3C 版 `propagate_to_subprocess_env`）**已實際落地**於 `autoclaude/utils/trace_context.py:136-217`，**實測 229 行（`wc -l`）**，較 W0 預估 ~195 多（W3C 規格 docstring + 嚴格格式驗證所致），**仍遠低於 absolute_limit 750**。§3 建議之 `.loc-budget.toml` contract tier ≤ 400 顯式 override **尚未落地**（`utils/` 仍走 unclassified→750）— 列 W3 T3-F1b 收尾項。

### §3.1 紅線 ❌23（更新後拆分為 ❌23-A / ❌23-B；**Arch-M3 / SD-m2 修復**）

- **❌23-A**：W0 PM 路徑拍板未完成前推進 W3 trace_id 實作（不論 a/b/c）
- **❌23-B**：路徑 (b) 落地但 **contract test `test_trace_context_plugin_isolation.py` 未覆蓋**（取代原「Rule 8 未建立」）→ `git revert HEAD`
- **Rule 8 取消新增**：保持 importlinter 7 kept（W3 G3 + W6 G6 驗證統一）

### §3.2 OTel 過渡相容性（路徑 b）

路徑 (b) W3C TraceContext header 為 SD_10 OTel 整合鋪路：
- `traceparent` header 為 W3C 標準（`00-<trace_id>-<span_id>-<flags>`）
- SD_10 引入 OTel SDK 時可直接以 `opentelemetry.propagators.textmap.TextMapPropagator` 對接
- 路徑 (a) 環境變數則需在 SD_10 額外轉換層

### §3.3 multi-process 30 天觀察期解耦（**Architect C3 修復**）

multi-process trace_id GA 觀察期：
- W3 落地後起算 30 天觀察
- **不計入 W5 雙條件**（ADR-SD09-001 §2.2 明訂 W5 條件為「同 process」GA）
- multi-process GA 視觀察結果延 W6 / SD_10

---

## §4. 測試規範

### §4.1 路徑 (b) W3C TraceContext 測試（**本 Sprint 唯一保留**）

`tests/utils/test_trace_context_subprocess_env.py`（W0 5 case + W3 7 W3C case = 12 case；R22 命名一致性修復 — 沿用 W0 既有檔擴展，不另建 _w3c.py）：
1. traceparent 解析（合法格式 `00-<trace_id>-<span_id>-<flags>`）
2. 不合法格式（return None / 拒絕）
3. 父子 process 串接（subprocess env=propagate_to_subprocess_env(...)）
4. OTel 過渡相容（W3C 標準格式可直接餵入 OTel propagator）
5. roundtrip：to_traceparent_header → from_traceparent_header 還原
6. caller 已設 TRACEPARENT 時不覆蓋（W3C distributed tracing semantics）
7. 過長 trace_id 截斷至 32 chars

`tests/contract/test_trace_context_plugin_isolation.py`（≥ 2 case，**Rule 8 替代方案**；**W0 已先行落地 9/9 PASSED**，2026-05-20 QA zero-trust audit 確認）：
1. AST 掃描禁 plugin 直接 import `utils.trace_context.to_traceparent_header` / `from_traceparent_header`
2. plugin 必須走 `IObservabilityPort` 或 `ContextVar` 注入

---

## §5. 對應參考

- [SD_Improving_09.md](../SD_Improving_09.md) §1.6 議題 F（PM #4 拍板 (b)）
- [SD09_Execution_Guide.md](../../05_development/SD09_Execution_Guide.md) W3 — F 議題群路徑 (b)
- [ADR-SD08-004](ADR-SD08-004-observability-port.md) v1.0
- [SD_Improving_08.md](../SD_Improving_08.md) §7 L1（multi-process 限制）

---

**簽核**：✅ ACCEPTED — 2026-05-20（場景 A 個人開發 dev 自核 commit；PM #4 (b) W3C TraceContext finalized；未選路徑 a/c 已 git rm）
