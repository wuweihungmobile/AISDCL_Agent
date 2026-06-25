# AutoSDD improving_71 — pty-vs-sdk 完整 A/B 指標載具 + 真跑（揪修 pty CLI 崩潰 DEF-71-001）

> **軌道**：① 整合迭代（範本驅動）。**本輪柱位**：**A 軌**（AISDLC-SDD × AutoClaude 深度整合 — 執行器後端對比驗收）。
> **承接**：improving_70（commit 87f1b4d）遞延候選「完整 pty-vs-sdk 指標 A/B」。
> **下一份**：improving_72。
> **日期**：2026-06-26 ｜ **driver**：掌舵者 AskUserQuestion 兩問拍板——①scope＝「pty-vs-sdk 完整 A/B（A 軌）」；②實跑深度＝「pty+sdk 雙跑對比（授權真 token）」。

---

## 1. 本輪範圍（掌舵者拍板）

| W 項 | 內容 | 狀態 |
|------|------|------|
| **W-71-1** | pty/sdk A/B **指標載具** `tools/ab_compare_backends.py` — 純 log 解析四指標（一次通過率／CORRECTION 次數／SDD_CONTRACT_VIOLATION 次數／token 峰值），零行為變更 | ✅ 完成（11 單元測 + 突變實證；含 W-71-2 真跑揭露後改錨 Kernel 路徑） |
| **W-71-2** | **真跑 A/B**（pty + sdk 各一次 smoke，真 token）+ 真跑揭露之兩缺口閉環：①修 `main.py` pty 後端 CLI 崩潰（**DEF-71-001**）；②為 Kernel 補 CORRECTION observability 標記使第四指標可測 | ✅ 完成（真跑成功、DEF-71-001 fixed + 3 回歸測、kernel 標記 + 2 測） |

**SD_09 W1** 因觀察期時間閘（drift/obs ~2026-06-29~07-01）未到，本輪不列（誠實排除）。

---

## 2. 階段一：零信任重偵察（硬閘通過，全部實測）

| 檢查 | 實測 | floor 對比 |
|------|------|-----------|
| AutoClaude 全套 pytest | **3351 passed / 122 skipped / 0 failed**（68s） | = 上輪 floor 3351，硬閘未觸發 |
| lint-imports | 8 kept / 0 broken | 持平 |
| LOC 分級 | violations=0（total 19377 / cap 20438） | 過 |
| snapshot --check | FRESH | 過 |
| SDD ci-gate | exit 0（v0.01:1478 / v0.26:1665 / scripts:129） | 全綠 |
| improving_70 構件 | `ActFirstOrderingError`(adapter:48)＋`raise`(:257)＋5 act-first 測，開檔確認存在無虛報 | 收斂屬實 |
| SDD LATEST | v0.26（磁碟＝FRAMEWORK_STATUS，無漂移） | 持平 |
| 外部依賴 (f) | claude CLI 在 PATH ✅、`~/.claude/.credentials.json` ✅、外網通 ✅；**cc-switch CLI NOT FOUND**（DEF-01-007 仍 open，本輪 A/B 為 pty-vs-sdk **執行器後端**對比，非 cc-switch 模型 profile 對比，故不阻擋） | 健康 |
| 缺陷帳本 | open 3（DEF-01-007 / DEF-01-009 / DEF-62-001）/ routed 3（DEF-17-001 / DEF-19-001 / DEF-42-001），全 P3 | 無 P0/P1/P2 |

---

## 3. 階段二：增量設計

### 3.1 <Architecture_Design_Review>（寫實質 Python 前自審）

1. **架構純潔性**：無 God-object。A/B 載具落 `tools/`（非 `autoclaude/` 套件層，不受 import-linter／LOC 治理但仍精簡）；純函式 `parse_run_metrics` 無副作用。`main.build_executor` 為**接線重構**（將原內聯 if/else 抽為可測單元）— Thin Facade（`playbook_runner.py`）零改動。kernel 僅加一行 observability-only `logger.info`。
2. **持久化相容**：**無新 PlaybookCheckpoint 欄位**。設計關鍵：成功完成後 checkpoint 被清除（`playbook_runner.py:429`／`boot_helper.py`）→ 指標一律取自 log，**不新增 checkpoint 欄位、不動 DAL 三後端** → 零停機。
3. **安全防護網**：本輪**不新增「從文件生成指令」或 shell 路徑**、不弱化 CONDITIONAL 三層防線。A/B 載具 subprocess 以固定 argv list 呼叫 `python -m autoclaude`（非 shell 字串），無注入面。
4. **對外 I/O 安全**：**不新增 `ToolInvocationPort` 外呼路徑**、無 Web/HTTP/訊息新能力 → allowlist/SSRF 攻防本輪 N/A。kernel CORRECTION 標記僅記 step_id/attempt（無敏感資料）。

### 3.2 介面 delta

| 構件 | delta | LOC 落點 |
|------|-------|---------|
| `tools/ab_compare_backends.py`（新） | `RunMetrics` dataclass + 純函式 `parse_run_metrics` / `format_comparison` / `run_backend` + CLI | 新檔 ~200 行（tools/ 不受 tier 治理；<750 絕對線） |
| `autoclaude/main.py` `build_executor`（新模組級函式） | 抽出 backend 建構為可測單元；**修正 pty 接線** `PtyExecutor(cfg.claude, cfg.loop, log_dir=cfg.log_dir, hotkey=hotkey)`（原 `PtyExecutor(cfg)` 崩潰，DEF-71-001） | main.py 131→145 行（無 tier，<750） |
| `autoclaude/core/kernel.py` `_run_step` | 取得有效修正後加 observability-only `logger.info("=== STATE: CORRECTION \| step=.. attempt=.. ===")`（零行為變更，使 A/B 可計 CORRECTION） | kernel.py 284→291 行（service ≤500，過） |

**importlinter**：無新跨層 import → 8 kept 不變。**LOC**：violations=0（結案實測）。

### 3.3 設計關鍵：指標來源錨點（W-71-2 真跑揭露並訂正）

- **初版誤錨**：載具初版錨 `steps_orchestrator/_impl.py` 的 `=== STATE: EXECUTE/EVALUATE ===` 標記——但真跑揭露那是**已棄用的 runner 路徑**；production **Kernel（`core/kernel.py`）路徑不發那些標記**（成功標記 `✓ (attempt N)` 僅進 `step_log`，最終以 `KernelResult(...)` repr 落 log）。
- **訂正後錨點**（錨 Kernel 真實輸出）：最終 `KernelResult(success/completed_steps/total_steps/escalated)` 行（權威）＋ step_log 內 `✓ (attempt N)`（→ 完成/一次通過）＋ 本輪為 Kernel 補的 `STATE: CORRECTION` 標記＋ `SDD-VIOLATION[`＋ `TOKEN_COMPACT NN%`。
- **編碼**：Windows console（cp950）會 mangle 中文/✓，故 run 模式讀引擎 utf-8 log 檔 `<workdir>/logs/autoclaude.log`，非擷取 stdout。

---

## 4. 階段三：實作與雙重驗證

### 4.1 實作（純 AutoClaude A 軌整合層、無 Copy-on-Evolve）

- [tools/ab_compare_backends.py](../../AutoClaude/tools/ab_compare_backends.py)：A/B 指標載具（純 log 解析 + subprocess 實跑 + 對比表）。
- [autoclaude/main.py](../../AutoClaude/autoclaude/main.py)：`build_executor` 可測單元 + **DEF-71-001 修復**。
- [autoclaude/core/kernel.py](../../AutoClaude/autoclaude/core/kernel.py)：CORRECTION observability 標記。
- 測試：[tests/tools/test_ab_compare_backends.py](../../AutoClaude/tests/tools/test_ab_compare_backends.py)（11）+ [tests/test_main_build_executor.py](../../AutoClaude/tests/test_main_build_executor.py)（3）+ [tests/core/test_kernel_pre_correction.py](../../AutoClaude/tests/core/test_kernel_pre_correction.py)（+2）。

### 4.2 真跑 A/B 結果（N=1，真 token，誠實標註）

兩後端各跑 `scripts/sdd_bridge_smoke.yaml` 一次（yaml_only config、臨時工作目錄、mock_brain 兜底），載具解析真實 Kernel log：

| 指標 | pty | sdk |
|------|-----|-----|
| 一次通過率 | 0% | 100% |
| CORRECTION 次數 | 0 | 0 |
| SDD_CONTRACT_VIOLATION 次數 | 0 | 0 |
| token 峰值 | 0% | 0% |
| 完成步驟 / 總步驟 | 0/2 | 1/2 |
| run 成功 / escalated | False / True | False / True |

**解讀（執行器層真實差異）**：
- **sdk**：S01 attempt 1 即過（一次通過率 100% of 已完成）、但 S02 retry 4 次耗盡 → escalated（completed 1/2）。S01「過」係 keyword `[TEST_READY]` 命中但 **permission_mode=default 無人核准 → 檔案實際未建**，S02 evaluator 親跑 pytest 抓到檔不存在（雙重驗證設計奏效）。
- **pty**：S01 keyword `[TEST_READY]` 未被 wexpect 擷取 → 第一步即 escalated（completed 0/2）。
- **CORRECTION 皆 0**：印證**預設 config brain=None**（DEF-01-008 flag-gated）→ 失敗步驟盲 retry 無修正（sdk S02 [FAIL] attempt 4 即 4 次無修正重試）。此為結構性事實，非缺陷。
- **誠實邊界**：N=1、smoke 刻意簡短，本 A/B 量的是**執行器層行為差異 + 載具管線正確性**，非模型統計對比；真統計 A/B 需多輪（列下輪候選）。

### 4.3 受控突變實證（測試非空殼）

- 載具 first-pass 判定 `== 1`→`== 2` → `test_perfect_run_all_first_pass` + roundtrip 2 測轉紅；Edit 還原（**禁 git checkout**，新 untracked 檔，遵 [[git-checkout-mutation-revert-hazard]]）→ 11 passed。
- kernel CORRECTION 標記字串 `STATE: CORRECTION`→`STATE: CORR_MUTATED` → `test_correction_marker_emitted_once` 轉紅；Edit 還原（tracked 檔但本輪改動未 commit，git checkout 會抹掉 W-71-2 編輯故禁用）→ 復綠。

---

## 5. 階段四：零退化驗證矩陣（全項實測，結案）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3351 / 0 failed | **3367 / 122 / 0**（floor 3351 + 16 新測：11 載具 + 3 build_executor + 2 kernel） ✅ |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept | **8 kept / 0 broken** ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | **violations=0**（kernel 291<500、main 145<750） ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **FRESH** ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0 | 階段一 exit 0（本輪零 SDD 變更） ✅ |
| 五軌 TLC | — | 僅 FSM 變更時 | **N/A**（未碰 `*.tla`/FSM） |
| DAL 等價 | — | — | **N/A**（未碰 DAL/checkpoint 欄位） |

---

## 6. RTM（需求追溯矩陣）

| 需求 | 來源 | 驗證 |
|------|------|------|
| R-71-1 A/B 載具解析四指標 | `parse_run_metrics`（ab_compare_backends.py） | `test_perfect_run_all_first_pass` 等 11 測 |
| R-71-2 一次通過率＝attempt 1 即過 / 已完成 | `RunMetrics.first_pass_rate` + step_log ✓ 解析 | `test_correction_lowers_first_pass_rate` |
| R-71-3 完成步數取 KernelResult 權威值 | KernelResult 行解析 | `test_kernel_result_completed_is_authoritative_over_marks` / `test_escalated_run_completed_from_kernel_result` |
| R-71-4 CORRECTION 可觀測（Kernel 標記） | kernel `_run_step` logger.info | `test_correction_marker_emitted_once_per_correction` / `test_no_marker_when_first_attempt_passes` |
| R-71-5 預設 pty 後端 CLI 不崩（DEF-71-001） | `main.build_executor` 接線修正 | `test_default_backend_builds_pty_executor_without_crash` / `test_pty_executor_receives_claude_and_loop_cfg` |
| R-71-6 sdk 後端建構正確 | `build_executor` sdk 分支 | `test_sdk_backend_builds_sdk_adapter` |
| R-71-7 真跑 A/B 對比（pty+sdk） | 真跑 + 載具解析真實 log | §4.2 對比表（N=1 實測） |
| R-71-8 零退化 | 收斂矩陣 | 3367/0、8 kept、LOC 0、snapshot FRESH |

---

## 7. 多專家 Zero-Trust 審查結論

見 [AutoSDD_ZeroTrust_Audit_71.md](../06_quality/AutoSDD_ZeroTrust_Audit_71.md)。三鏡主樹並行（本輪含 untracked 新檔 → 依 DEF-24-001 主樹派發禁 worktree；突變已全數還原無並行突變鏡）。

---

## 8. 誠實級別標註

本輪＝**A 軌執行器後端 A/B 載具 + 真跑驗收輪（並揪修長期潛伏的 pty CLI 崩潰 DEF-71-001），非成熟度推進**，`L_合體=min(A=L5,B=L5,C=L5)=L5` 維持。

- **首要成果**：①交付可重複的 pty/sdk A/B 指標載具（零碰執行語意）；②真跑揭露並當場修復 **DEF-71-001**（預設 pty 後端經 CLI 必崩、長期潛伏因 main 接線無測試覆蓋）；③為 Kernel 補 CORRECTION observability 使第四指標可測。
- **誠實邊界**：(a) 載具初版誤錨棄用 runner 路徑標記，**由真跑當場揭露並改錨 Kernel 真實輸出**——這正是「真跑驗收」的價值（非紙上 A/B）；(b) A/B 為 N=1、smoke 刻意簡短，量執行器層差異非模型統計；(c) CORRECTION 皆 0 係預設 brain=None 結構性事實（DEF-01-008），非缺陷。
- **本輪新框架缺陷**：DEF-71-001（整合層 AutoClaude 側，當場修；非 SDD 本體 → 免 Copy-on-Evolve、免五軌 TLC）。
- **遞延 improving_72 候選**：完整**統計** A/B（多輪 + 讓 smoke 真通過：sdk 配 bypassPermissions / pty 調 claude -p 擷取）；SD_09 W1 觀察期 #1 source-sha 閘門（時間閘 ~06-29~07-01 成熟後）。

三件套：improving_71 / ZeroTrust_Audit_71 / Defect_Log（DEF-71-001 + recap）。
