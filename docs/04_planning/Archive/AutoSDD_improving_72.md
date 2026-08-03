# AutoSDD improving_72 — pty-vs-sdk 完整統計 A/B：讓兩後端 smoke 真通過 + N=3 多輪統計（揪修 DEF-72-001）

> **軌道**：① 整合迭代（範本驅動）。**本輪柱位**：**A 軌**（AISDLC-SDD × AutoClaude 深度整合 — 執行器後端對比驗收，承接 improving_71）。
> **承接**：improving_71（commit 60687ca）遞延首選「完整**統計** A/B（多輪 + 讓 smoke 真通過：sdk 配 bypassPermissions / pty 調 claude -p 擷取）」。
> **下一份**：improving_73。
> **日期**：2026-06-26 ｜ **driver**：掌舵者 AskUserQuestion 兩問拍板——①scope＝「完整統計 A/B（A 軌）」；②真跑深度＝「讓 smoke 真通過 + 小樣本多輪（授權真 token）」。

---

## 1. 本輪範圍（掌舵者拍板）

| W 項 | 內容 | 狀態 |
|------|------|------|
| **W-72-1** | 讓 pty/sdk 兩後端 smoke **真的跑通兩步**：新增 `scripts/ab_configs/ab_pty_config.yaml`（pty + `--permission-mode bypassPermissions`）與 `ab_sdk_config.yaml`（sdk + `permission_mode=bypassPermissions`），兩者 dummy minimax key + `goal_synthesis_enabled=false` | ✅ 完成（含真跑揭露並當場修 **DEF-72-001** pty 複雜-prompt 殘缺） |
| **W-72-2** | 載具**多輪統計聚合**：`AggregateMetrics` + 純函式 `aggregate_runs`（mean/母體stdev/min/max + success/escalated 計數）+ `format_aggregate_comparison` + `run_backend_n`（每輪獨立乾淨子目錄）+ CLI `--n` | ✅ 完成（6 新單元測 + 突變實證） |
| **W-72-3** | **真跑 N=3 多輪統計**（pty + sdk 各 3 輪，真 token）+ 誠實標註 | ✅ 完成（兩後端 3/3、100%/0/0/0；誠實邊界見 §4.2） |

---

## 2. 階段一：零信任重偵察（硬閘通過，全部實測）

| 檢查 | 實測 | floor 對比 |
|------|------|-----------|
| AutoClaude 全套 pytest | **3367 passed / 122 skipped / 0 failed**（68.9s） | = 上輪 floor 3367，硬閘未觸發 |
| lint-imports | 8 kept / 0 broken | 持平 |
| LOC 分級 | violations=0（total 19390） | 過 |
| snapshot --check | FRESH | 過 |
| SDD ci-gate | exit 0（v0.01:1478 / v0.26:1665 / scripts:129） | 全綠 |
| improving_71 構件 | `ab_compare_backends.py`(`parse_run_metrics`)、`main.build_executor`、`kernel` CORRECTION 標記、3 測檔——開檔確認存在無虛報 | 收斂屬實 |
| 外部依賴 (f) | claude CLI **v2.1.144** 在 PATH ✅、`~/.claude/.credentials.json` ✅、`claude_agent_sdk` extra 已裝 ✅ | 健康，真跑基礎設施就位 |
| 缺陷帳本 | open 3（DEF-01-007 / DEF-01-009 / DEF-62-001）/ routed 3（DEF-17-001 / DEF-19-001 / DEF-42-001），全 P3 | 無 P0/P1/P2 |

---

## 3. 階段二：增量設計

### 3.1 <Architecture_Design_Review>（寫實質 Python 前自審）

1. **架構純潔性**：無 God-object。聚合邏輯落 `tools/ab_compare_backends.py`（tools/ 不受 import-linter／LOC tier 治理，仍守 <750 絕對線；190→約 290 行）；`aggregate_runs`/`format_aggregate_comparison` 為**純函式無副作用**，`run_backend_n` 僅 subprocess 編排（複用既有 `run_backend`）。**DEF-72-001 修復**為 `pty_wrapper._start_wexpect` 的**參數傳遞訂正**（shell-join 字串→arg list），非執行語意改寫；`playbook_runner.py` Thin Facade 零改動。
2. **持久化相容**：**無新 PlaybookCheckpoint 欄位**、不動 DAL 三後端、不動 checkpoint。多輪指標一律取自每輪獨立 log（沿用上輪「成功完成後 checkpoint 清除→取 log」設計）→ 零停機。
3. **安全防護網**：**不新增「從文件生成指令」或 shell 字串路徑**、不弱化 CONDITIONAL 三層。`bypassPermissions` 僅作用於 A/B smoke 臨時工作目錄（自包含 add(a,b) 載具，無外呼）；DEF-72-001 修復實際上是**移除**一個非預期的 shell parsing 面（arg list 不經 shell），降低注入面。subprocess 仍固定 argv list。
4. **對外 I/O 安全**：**不新增 `ToolInvocationPort` 外呼路徑**、無 Web/HTTP/訊息新能力 → allowlist/SSRF 攻防本輪 N/A。

> **設計增補（真跑後）**：原 ADR 宣稱「零碰執行語意」，但真跑揭露 pty 後端對複雜 prompt 默默失效（DEF-72-001）。比照 improving_71 DEF-71-001「真跑揪 bug 當場修」紀律，本輪修復 `pty_wrapper`（production）——屬參數傳遞訂正（非控制流/語意改寫），並補先前無覆蓋的 wexpect 路徑回歸測。

### 3.2 介面 delta

| 構件 | delta | LOC 落點 |
|------|-------|---------|
| `scripts/ab_configs/ab_pty_config.yaml`（新） | pty 後端 A/B config（`--permission-mode bypassPermissions` + dummy key + goal_synthesis off） | config，不受治理 |
| `scripts/ab_configs/ab_sdk_config.yaml`（新） | sdk 後端 A/B config（`permission_mode=bypassPermissions` + dummy key + goal_synthesis off） | config，不受治理 |
| `tools/ab_compare_backends.py` | `AggregateMetrics` dataclass + `aggregate_runs`/`format_aggregate_comparison`/`run_backend_n` + CLI `--n` | tools/ 不受 tier；約 290 行 <750 |
| `autoclaude/perception/pty_wrapper.py` `_start_wexpect`（**DEF-72-001 修**） | `" ".join(...)` 單一 shell 字串 → `wexpect.spawn(command, args=list(args), encoding=...)` arg list | pty_wrapper 172→177 行（perception，<750） |
| 測試 | `tests/tools/test_ab_compare_backends.py` +6（聚合）；`tests/test_perception.py` +1（DEF-72-001 回歸） | — |

**importlinter**：無新跨層 import → 8 kept 不變。**LOC**：violations=0（結案實測）。

### 3.3 設計關鍵：為何兩後端都需權限旁路 + 為何 config 移子目錄

- **權限旁路**：smoke S01/S02 需 claude **實際寫檔**（smoke_add_test.py / smoke_add.py）。sdk→`permission_mode=bypassPermissions`（傳 SDK client）；pty→claude CLI flag `--permission-mode bypassPermissions`（經 extra_args）。improving_71 真跑 sdk「S01 keyword 命中但 permission=default 未建檔」即此缺口。
- **dummy minimax key**：`MinimaxClient.__init__`（config.py:102）要求 api_key 非空否則 main return 1；`enable_kernel_brain=false`→brain=None→該 key 永不真呼叫。
- **goal_synthesis off**：DONE 前 `GoalSynthesisPlugin` 會用 client 真打 minimax（dummy key 失敗雖優雅 catch 但含重試拖慢多輪）；對兩後端一致關閉＝A/B 公平，且非四指標之一。
- **config 移 `scripts/ab_configs/` 子目錄**：`tests/integration/test_yaml_import.py` glob `scripts/*.yaml`（非遞迴）並斷言皆為 playbook；A/B config 非 playbook → 移子目錄避開（測試對 scripts/ 根僅放 playbook 的假設合理，非缺陷）。

---

## 4. 階段三：實作與雙重驗證

### 4.1 實作（純 AutoClaude A 軌整合層、無 Copy-on-Evolve）

- [scripts/ab_configs/ab_pty_config.yaml](../../AutoClaude/scripts/ab_configs/ab_pty_config.yaml)、[ab_sdk_config.yaml](../../AutoClaude/scripts/ab_configs/ab_sdk_config.yaml)：兩後端 A/B config。
- [tools/ab_compare_backends.py](../../AutoClaude/tools/ab_compare_backends.py)：多輪統計聚合（`AggregateMetrics` / `aggregate_runs` / `format_aggregate_comparison` / `run_backend_n` / `--n`）。
- [autoclaude/perception/pty_wrapper.py](../../AutoClaude/autoclaude/perception/pty_wrapper.py)：**DEF-72-001 修復**（`_start_wexpect` arg list）。
- 測試：[tests/tools/test_ab_compare_backends.py](../../AutoClaude/tests/tools/test_ab_compare_backends.py)（+6）+ [tests/test_perception.py](../../AutoClaude/tests/test_perception.py)（+1 DEF-72-001 回歸）。

### 4.2 真跑 A/B 結果（N=3，真 token，誠實標註）

兩後端各跑 `scripts/sdd_bridge_smoke.yaml` 3 輪（每輪獨立乾淨子目錄），載具解析真實 Kernel log：

| 指標 | pty（N=3） | sdk（N=3） |
|------|-----------|-----------|
| run 成功 / escalated | 3 / 0 | 3 / 0 |
| 一次通過率 (mean ±stdev [min~max]) | 100% ±0% [100%~100%] | 100% ±0% [100%~100%] |
| CORRECTION 次數 (total) | 0 | 0 |
| SDD_CONTRACT_VIOLATION (total) | 0 | 0 |
| token 峰值 (max) | 0% | 0% |
| 完成步驟均值 / 總步驟 | 2.0/2 | 2.0/2 |

**解讀（執行器層真實差異）**：
- **修復前**（DEF-72-001 未修）：pty 0/2 escalated（複雜 prompt 殘缺、raw log 0 bytes）vs sdk 2/2 success（bypassPermissions 後真建檔）——**巨大二元差異**。
- **修復後**：兩後端皆 3/3、四指標收斂相同。**smoke 刻意簡短**（兩步、自包含 add(a,b)、無 compaction）→ 四指標自然收斂；本輪 A/B 真正分出的是**「能不能跑」的二元差異**（pty 原本壞、修好後可用），這正是真跑驗收的價值。
- **誠實邊界**：(a) N=3、smoke 短，量的是**執行器層可用性 + 載具管線正確性**，非模型統計對比；(b) token 峰值皆 0% 係任務太小未觸發 compaction（誠實表「低於記錄門檻」非 0 消耗）；(c) 要分出 token/CORRECTION 差異需更長/會觸發 compaction 的 playbook（列下輪候選）。

### 4.3 受控突變實證（測試非空殼）

- 載具 `agg.first_pass_rate_mean = statistics.mean(fpr)`→`= fpr[0]`（取首輪非均值）→ `test_aggregate_mean_stdev_range_across_runs` 轉紅（1.0≠0.75）；Edit 還原（**禁 git checkout**，本輪含 untracked 新檔 + tracked 未 commit 改動，遵 [[git-checkout-mutation-revert-hazard]]）→ 復綠。
- pty_wrapper `_start_wexpect` 還原成 `" ".join` join 版 → `test_wexpect_spawn_passes_args_as_list_not_shell_joined` 轉紅；cp 備份還原 → 復綠。

---

## 5. 階段四：零退化驗證矩陣（全項實測，結案）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3367 / 0 failed | **3374 / 122 / 0**（floor 3367 + 7 新測：6 聚合 + 1 DEF-72-001 回歸） ✅ |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept | **8 kept / 0 broken** ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | **violations=0**（pty_wrapper 177、tools/ 不受 tier） ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **FRESH** ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0 | **exit 0**（v0.01:1478 / v0.26:1665 / scripts:129；本輪零 SDD 變更） ✅ |
| 五軌 TLC | — | 僅 FSM 變更時 | **N/A**（未碰 `*.tla`/FSM） |
| DAL 等價 | — | — | **N/A**（未碰 DAL/checkpoint 欄位） |

---

## 6. RTM（需求追溯矩陣）

| 需求 | 來源 | 驗證 |
|------|------|------|
| R-72-1 sdk smoke 真通過（bypassPermissions） | `ab_sdk_config.yaml` | 真跑 sdk 2/2 + N=3 全 3/3（§4.2） |
| R-72-2 pty smoke 真通過（DEF-72-001 修） | `pty_wrapper._start_wexpect` arg list | 真跑 pty 修後 2/2 + N=3 全 3/3；`test_wexpect_spawn_passes_args_as_list_not_shell_joined` |
| R-72-3 多輪統計聚合（mean/stdev/min/max） | `aggregate_runs` | `test_aggregate_mean_stdev_range_across_runs` |
| R-72-4 空輸入安全 | `aggregate_runs` 空 list 守衛 | `test_aggregate_empty_is_zero_no_crash` |
| R-72-5 N=1 退化不失真 | `aggregate_runs`（pstdev n=1→0） | `test_aggregate_single_run_degenerates_to_value_stdev_zero` |
| R-72-6 success/escalated 計數 | `aggregate_runs` | `test_aggregate_success_escalated_counts` |
| R-72-7 多輪每輪乾淨子目錄 | `run_backend_n`（run_1..run_N） | 設計（避免 smoke 建檔殘留污染）+ 真跑 N=3 無污染 |
| R-72-8 零退化 | 收斂矩陣 | 3374/0、8 kept、LOC 0、snapshot FRESH、SDD exit 0 |

---

## 7. 多專家 Zero-Trust 審查結論

見 [AutoSDD_ZeroTrust_Audit_72.md](../06_quality/AutoSDD_ZeroTrust_Audit_72.md)。三鏡主樹並行（本輪含 untracked 新檔〔2 config + 計畫/審計文件〕→ 依 DEF-24-001 主樹派發禁 worktree；突變已全數還原無並行突變鏡）。

---

## 8. 誠實級別標註

本輪＝**A 軌執行器後端完整統計 A/B + 真跑驗收輪（並揪修長期潛伏的 pty 複雜-prompt 殘缺 DEF-72-001），非成熟度推進**，`L_合體=min(A=L5,B=L5,C=L5)=L5` 維持。

- **首要成果**：①讓 pty/sdk 兩後端 smoke 真通過（sdk bypassPermissions / pty DEF-72-001 修）；②交付可重複的多輪統計 A/B 載具（mean/stdev/min/max + success 計數）；③真跑 N=3 收統計（修復後兩後端等價）。
- **本輪新框架缺陷**：DEF-72-001（整合層 AutoClaude 側，當場修；非 SDD 本體 → 免 Copy-on-Evolve、免五軌 TLC）。
- **誠實邊界**：(a) smoke 短 → 四指標收斂相同，本輪量「執行器可用性 + 載具管線」非模型統計；(b) token 峰值皆 0 係任務未觸發 compaction；(c) pty raw log 0 bytes 觀測缺口（logfile_read adapter 未捕獲，不影響步驟成功）列下輪觀察。
- **教訓**：①連續兩輪真跑各揪一個潛伏 P1（DEF-71-001 接線崩潰、DEF-72-001 prompt 殘缺），共同根因＝**pty 路徑長期無測試覆蓋**（wexpect Windows-only + 既有測試全走 subprocess 分支）——真跑＋補測試是揭露此類缺陷的唯一途徑。②「smoke 看似簡短沒差異」的結論本身要靠真跑才站得住：修復前 pty 0%/sdk 100%（巨大差異），修復後才收斂為等價。
- **遞延 improving_73 候選**：(a) pty raw log 0 bytes 觀測缺口；(b) 用更長/會觸發 compaction 的 playbook 跑 A/B 分出 token 峰值差異；(c) SD_09 W1 觀察期 #1 source-sha 閘門（時間閘 ~06-29~07-01 成熟後）。

三件套：improving_72 / ZeroTrust_Audit_72 / Defect_Log（DEF-72-001 + recap）。
