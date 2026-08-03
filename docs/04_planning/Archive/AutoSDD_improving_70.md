# AutoSDD improving_70 — act-first warn→硬擋（fail-closed raise，無關閉鍵）

> **軌道**：① 整合迭代（範本驅動）。**本輪柱位**：**C 軌**（指揮官 AutoClaude 自身能力）。
> **承接**：improving_69（commit 0472189）唯一遞延＝W-69-3 act-first warn→硬擋（掌舵者裁延本輪）。
> **下一份**：improving_71。
> **日期**：2026-06-26 ｜ **driver**：掌舵者 AskUserQuestion 裁「只做 W-70-1 act-first 硬擋；語義採 fail-closed raise + 無關閉鍵」。

---

## 1. 本輪範圍（掌舵者拍板）

| W 項 | 內容 | 狀態 |
|------|------|------|
| **W-70-1** | act-first warn→硬擋 — 執行期判定排序明確不安全（`safe=False`）時由 warn-only 升級為 fail-closed `raise ActFirstOrderingError`（無關閉鍵；「無法判定」維持 best-effort 放行） | ✅ 完成（5 單元測 + 突變實證） |

**掌舵者兩問拍板**（AskUserQuestion）：①scope＝「只做 W-70-1（推薦）」；②語義＝「fail-closed raise，無關閉鍵（推薦）」。完整 pty-vs-sdk 指標 A/B 與 SD_09 W1 續列 improving_71 候選。

---

## 2. 階段一：零信任重偵察（硬閘通過，全部實測）

| 檢查 | 實測 | floor 對比 |
|------|------|-----------|
| AutoClaude 全套 pytest | **3349 passed / 122 skipped / 0 failed**（73s） | = 上輪 floor 3349，硬閘未觸發 |
| lint-imports | 8 kept / 0 broken | 持平 |
| LOC 分級 | violations=0（total 19367 / cap 20438） | 過 |
| snapshot --check | FRESH | 過 |
| improving_69 構件 | `sdk_tool_allowlist` config 字段（config.py:240）/ `build_tool_allowlist_predicate`（sdk_executor_adapter.py:48）/ main.py 接線（97-117）/ `_wrap_can_use_tool` fail-closed（270-290）— 全部開檔確認存在且被測試覆蓋，查無虛報 | 收斂屬實 |
| W-69-3 範圍 | 計畫表§1 + 缺陷帳本誠實標「延後 improving_70」，現碼 `_verify_act_first` 仍 warn-only（241-248），無實作痕跡 | 誠實 |
| SDD ci-gate | exit 0（v0.01:1478 / v0.26:1665 / scripts:129，arch_fitness fail=0） | 全綠 |
| SDD LATEST | v0.26（磁碟＝FRAMEWORK_STATUS，無漂移） | 持平 |
| 缺陷帳本 | open 3（DEF-01-007 / DEF-01-009 / DEF-62-001）/ routed 3（DEF-17-001 / DEF-19-001 / DEF-42-001），全 P3 | 健康，無 P0/P1/P2 |

---

## 3. 階段二：增量設計

### 3.1 <Architecture_Design_Review>（寫實質 Python 前自審）

1. **架構純潔性**：無 God-object。改動全落單一 adapter 模組——新增 module-level 例外 `ActFirstOrderingError(RuntimeError)`（~10 行含 docstring）+ `_verify_act_first` 的 `logger.warning` → `raise`。`playbook_runner.py` Thin Facade 零改動（未碰）；純函式 `verify_act_first_ordering` 判定權威源逐字不動。
2. **持久化相容**：**無新 PlaybookCheckpoint 欄位**。`_act_first_safe` 為既有 in-memory 觀測旗標（raise 前仍照設），DAL 三後端完全不觸碰 → 零停機。
3. **安全防護網**：本輪**不新增任何「從文件生成指令」或 shell 路徑** → CONDITIONAL 三層防線不需擴充。act-first 硬擋本身＝安全強化（把「SDK autocompact 搶先撞掉形式化 halt 門檻權威」從 warn-only 升級為 fail-closed 阻斷，縮小攻擊面）。
4. **對外 I/O 安全**：**不新增 `ToolInvocationPort` 外呼路徑**、無 Web/HTTP/訊息新能力 → allowlist/SSRF 攻防測試本輪 N/A。

### 3.2 介面 delta

| 構件 | delta | LOC 落點 |
|------|-------|---------|
| `sdk_executor_adapter.py` `ActFirstOrderingError(RuntimeError)` | 新增 module-level 例外（含 docstring 說明「無關閉鍵」設計） | +10 行 |
| `sdk_executor_adapter.py` `_verify_act_first` | `safe=False` 由 `logger.warning(...)` → `raise ActFirstOrderingError(...)`（診斷訊息含 threshold/halt/max_tokens + 三槓桿指引） | 淨 ~0（替換） |
| 「無法判定」3 路徑（usage 例外 / 非 dict / threshold\|max_tokens falsy） | 維持 early return 不擋 | 不變 |

**LOC 結果**：adapter 305→318 行，仍 <400（adapter tier）；total violations=0。**importlinter**：不新增跨層 import → 8 kept 不變（新例外為 adapter 模組內類，已受 executor 雙向隔離契約涵蓋）。

### 3.3 硬擋語義（掌舵者裁定 + 設計史對齊）

- **fail-closed raise**：`safe=False` → `raise ActFirstOrderingError` → `_run_async` → `anyio.run` → `execute()` 既有 `except Exception` 接住 → 回 `ExecutionOutput(completed=False, exit_code=1)`（fail-loud，不靜默完成）。守門在 `client.query(prompt)` **之前**，硬擋確實阻止任務啟動（query 不被送出）。
- **無關閉鍵**：無 config 繞過旗標。使用者若要放行須調整 Token Guard 三槓桿（halt_pct / max_tokens / autocompact 門檻）使排序回到安全——沿 commit 76a710e「Token Guard 權威三槓桿（act-first 無需關閉鍵）」設計，而非繞過檢查。
- **「無法判定」≠「不安全」**：取不到 usage / 非 dict / 缺 threshold|max_tokens → 維持 best-effort early-return 放行，避免真實環境偶發取用量失敗誤擋（零退化保護）。

---

## 4. 階段三：實作與雙重驗證

### 4.1 實作（純 AutoClaude C 軌、無 Copy-on-Evolve）

- [autoclaude/infra/adapters/sdk_executor_adapter.py](../../AutoClaude/autoclaude/infra/adapters/sdk_executor_adapter.py)：`ActFirstOrderingError` + `_verify_act_first` raise 升級。
- [tests/infra/adapters/test_sdk_executor_adapter.py](../../AutoClaude/tests/infra/adapters/test_sdk_executor_adapter.py)：act-first 測試群改寫為硬擋語義（5 測）。

### 4.2 測試（5 act-first 測，全綠）

| 測試 | 驗什麼 |
|------|--------|
| `test_act_first_unsafe_raises_actfirst_error` | 不安全 → `_verify_act_first` 拋 `ActFirstOrderingError`（突變核心） |
| `test_act_first_unsafe_fails_closed_via_execute` | 端對端：不安全 → `execute()` 回 completed=False/exit_code=1 + **query 未送出** |
| `test_act_first_safe_does_not_raise` | 安全（180k<190k）→ 不擋，正常完成、query 送出 |
| `test_act_first_missing_fields_does_not_raise` | 缺欄位 → 無法判定（`_act_first_safe=None`）→ 不誤擋 |
| `test_act_first_usage_exception_does_not_raise` | get_context_usage 拋例外 → best-effort 放行不誤擋（SA-SD 鏡缺口補測） |

**受控突變實證非空殼**：把 `raise ActFirstOrderingError(...)` 退回 `logger.warning`（模擬業務邏輯改回舊行為）→ unsafe 相關 **2 測轉紅**（raise 直驗 + execute fail-closed），safe/無法判定 2 測維持綠；以 Edit 精確還原（**禁 git checkout**，遵 [[git-checkout-mutation-revert-hazard]] 教訓）後複跑 5 passed。

---

## 5. 階段四：零退化驗證矩陣（全項實測，結案）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3349 / 0 failed | **3351 / 122 / 0**（floor 3349 + 5 新測 − 3 改寫舊測 = 淨 +2） ✅ |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept | **8 kept / 0 broken** ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | **violations=0**（adapter 318<400） ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **FRESH** ✅ |
| AISDLC_SDD 閘門 | 階段一已實測 | exit 0 | v0.01:1478 / v0.26:1665 / scripts:129 ✅（本輪零 SDD 變更） |
| 五軌 TLC | — | 僅 FSM 變更時 | **N/A**（未碰 `*.tla`/FSM） |
| DAL 等價 | — | — | **N/A**（未碰 DAL） |

---

## 6. RTM（需求追溯矩陣）

| 需求 | 來源 | 驗證 |
|------|------|------|
| R-70-1 不安全排序 fail-closed raise | `_verify_act_first` raise（sdk_executor_adapter.py） | `test_act_first_unsafe_raises_actfirst_error` |
| R-70-2 硬擋阻止任務啟動（query 不送出） | 守門在 query 之前 | `test_act_first_unsafe_fails_closed_via_execute`（assert query_prompts==[]） |
| R-70-3 fail-loud 不靜默完成 | execute except → completed=False/exit_code=1 | `test_act_first_unsafe_fails_closed_via_execute` |
| R-70-4 安全設定不誤擋 | safe=True 不 raise | `test_act_first_safe_does_not_raise` |
| R-70-5 「無法判定」best-effort 放行 | 缺欄位 / usage 例外 早返 | `test_act_first_missing_fields_does_not_raise` + `test_act_first_usage_exception_does_not_raise` |
| R-70-6 無關閉鍵 | 無 config 繞過旗標（Architect 鏡 grep 確認） | 架構審查 |
| R-70-7 零退化（預設 pty 不受影響） | backend=pty 不經此路徑 | 收斂矩陣 3351/0、8 kept、LOC 0 |

---

## 7. 多專家 Zero-Trust 審查結論

三鏡主樹並行（本輪 tracked 未 commit 修改 → 依 DEF-24-001 主樹派發禁 worktree）：**Architect / SA-SD / QA 全 OVERALL PASS、P0=P1=0**。

- **Architect**：架構純潔（例外位置合理、Thin Facade 未污染）、微核心紅線（無新跨層 import、例外傳播乾淨不洩漏 Kernel/EventBus）、無關閉鍵（grep 無 act_first 旗標）、零退化（預設 pty 不經此路徑）、LOC 318<400 — 全 PASS。
- **SA-SD**：fail-closed 語義正確（不安全擋、無法判定放行三路徑齊全）、守門時序（raise 在 query 前、query 未送出）、判定權威源未破壞（`verify_act_first_ordering` 逐字不動）、Rule 9 測試覆蓋意圖 — PASS（提一缺口：get_context_usage 例外路徑無顯式測試 → **本輪當場補測** `test_act_first_usage_exception_does_not_raise`）。
- **QA**：獨立親跑 3350→（補測後）3351/122/0、act-first 5 測全綠、**突變實證非空殼**（退回 warn → 2 測轉紅、Edit 還原乾淨 git CLEAN）、lint 8 kept、誠實性檢查（無 skip/xfail/註解規避）— 全 PASS。

---

## 8. 誠實級別標註

本輪＝**C 軌指揮官 AutoClaude 安全閘加固輪（act-first 由 warn-only 升級 fail-closed 硬擋），非成熟度推進**，`L_合體=min(A=L5,B=L5,C=L5)=L5` 維持。

- **首要成果**：把 improving_68/69 已知的 act-first warn-only 缺口（SDK autocompact 可能搶先撞掉 AutoClaude 形式化 halt 門檻權威）升級為 fail-closed 硬擋，且「無關閉鍵」對齊三槓桿設計、「無法判定」維持 best-effort 放行不誤擋（零退化）。
- **誠實邊界**：SA-SD 鏡提出的 get_context_usage 例外路徑測試缺口，依「能當場補就別延後」（[[no-defer-unless-justified]]）本輪即補（5 測），未列下輪。
- **本輪無新框架缺陷**（純 AutoClaude C 軌 additive 升級，未觸 SDD 框架本體 → 免 Copy-on-Evolve、免五軌 TLC）。
- **遞延 improving_71 候選**：完整 pty-vs-sdk 指標 A/B（一次通過率/CORRECTION/token 峰值）；SD_09 W1（觀察期 #1 source-sha 源碼演進閘門）。

三件套：improving_70 / ZeroTrust_Audit_70 / Defect_Log（append recap，本輪無新框架缺陷）。
