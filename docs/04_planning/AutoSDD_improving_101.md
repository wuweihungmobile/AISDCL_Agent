# AutoSDD_improving_101 — C 軌：SD_09 W1 鎖定判準解除日曆綁定（規格先行・待 PM signoff）

> **柱別**：C 軌（指揮官 AutoClaude / SD_09 工作流帳本）。
> **狀態**：**規格先行設計階段 — 待 PM（掌舵者）signoff ADR-SD09-011 後才動 `mutation_baseline_lock.py`**（🔴 人工確認閘門，不可自動跳過）。
> **掌舵者輸入**：improving_100 結案後質疑「為何排每日 JOB 才算過？空轉一個月是好設計嗎？請徹底規劃解決」→ 裁定續觀察 (a)，並要求徹底重新規劃鎖定機制。
> **框架版**：v0.30 不變（本輪標的在 AutoClaude `tools/`，非 AISLDC_SDD 框架本體、非 autoclaude/ 微核心源碼，無 Copy-on-Evolve；AutoClaude 走自身 G0~G6）。

---

## §1　本輪輸入
- improving_100（commit 724bda4、tag v2026.06.30-51）結案：補測試殺真缺口 + 文件校準，但揭露「unique sha 鎖定難收斂」。
- 掌舵者質疑直指**機制設計缺陷**（非單輪執行）：鎖定綁日曆天 → 空轉。要求徹底解決。
- improving_100 §8 routed：DEF-100-002（L49 死分支）——本輪暫不處理（聚焦鎖定機制；列 improving_102 候選）。

## §2　階段一：現況重偵察（Zero-Trust 實測）

### 2.1 基線（硬閘通過）
| 項目 | 命令 | 實測 |
|------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q -p no:cacheprovider` | **3618 passed / 122 skipped / 0 failed**（fresh，與 improving_100 收尾一致） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken（improving_100 已驗，本輪零 import 變更） |

### 2.2 空轉根因（鐵證）
1. **觸發**：`tools/run_local_nightly.ps1:25` schtasks `/SC DAILY` + `ci.yml:317` cron — 每日一次。
2. **M-05 去重**：`mutation_baseline_lock.py:197-203` 去重鍵＝「同 module + 同 UTC 日期」（不看 sha）→ 同日多 sha 只留 1 筆。
3. 疊加 ⇒ unique sha 每日最多 +1、7 個需 ≥7 日曆天、idle 稀釋 tail7 ⇒ 空轉。
4. **確定性反證**：mutation test 確定性，同 sha 重跑無新資訊；防抖動已由 unique sha + ±2pp tolerance + `compute_consistency_warning`(L265) 三機制承擔 ⇒ 日曆綁定是無防護目標的遺留懲罰。

詳見 [ADR-SD09-011](../../AutoClaude/docs/04_planning/ADR/ADR-SD09-011-mutation-lock-decouple-calendar.md) §1。

## §3　階段二：增量設計（待 signoff）

### 3.1 設計主張
鎖定要求「**N 個真實不同源碼版本（unique sha）都達標**」，與日曆時間解耦。反作弊強度與門檻數值全不變，只取消與安全無關的日曆懲罰。權威設計＝ADR-SD09-011（三改動）。

### 3.2 W 項（signoff 後實作）
- **W-101-1**：`append_history` 去重鍵 UTC 日期 → `source_sha256`（同 sha 留最新；legacy 缺 sha 沿用 `MAX_BACKWARD_COMPAT_MISSING`）。
- **W-101-2**：觸發解耦——新增 token_guard 源碼變動觸發（pre-push hook 或 CI on-path-change）；nightly 角色註解轉為「監控漂移 + flaky」（紀律 #6 分軌）。
- **W-101-3**：既有 `.mutation_history.jsonl` 30 筆按 sha 壓縮（ADR §4 方案 A）+ 原檔備份；`should_lock` tail 語意對齊。
- **W-101-4**：文件——ADR-SD09-011 轉 ACCEPTED、ADR-SD08-002 §2.4 / ADR-SD09-009 §11.6 supersede 註記、CLAUDE.md SD_09 段、缺陷帳本。

### 3.3 介面 delta / LOC / importlinter 影響
- 改 `tools/mutation_baseline_lock.py`（tools/ 在 LOC SCAN_ROOT 外、不影響預算；非 autoclaude/ 微核心 → importlinter 8 kept 不受影響）。
- 新增 hook/CI 配置（`tools/git-hooks/` 或 `.github/workflows/`）。
- 零碰 autoclaude/ 微核心、ports、plugins → 架構紅線不觸及。

### 3.4 <Architecture_Design_Review>
1. **架構純潔性**：改動限於 `tools/` 量測載具 + CI 配置，非微核心；無 God-object、Thin Facade 不受影響。✅
2. **持久化相容**：`.mutation_history.jsonl` 格式 additive（既有欄位不刪，去重鍵邏輯變更）；方案 A 壓縮附備份、可回溯。✅
3. **安全防護網**：反作弊強度不減（ADR §3 對照表）；未新增指令生成/CONDITIONAL/對外 I/O 路徑。✅
4. **對外 I/O**：零新增 `ToolInvocationPort` 外呼。✅
5. **ADR 合規**：本輪即為 ADR-SD09-011 提案；supersede 限「日曆綁定語意」，unique sha 反作弊 + 門檻數值保留。✅

### 3.5 RTM 需求列（實作後回填）
| RTM | 需求 | 測試 | 受控突變 | 實測 |
|-----|------|------|---------|------|
| RTM-101-1 | 同日多個不同 sha 皆計入（不再覆寫） | test_append_history | MUT：還原為 date 去重 → 應有測試轉紅 | 待 signoff/實作 |
| RTM-101-2 | 同 sha 重跑只留最新一筆（確定性去重） | test_append_history | MUT | 待 signoff/實作 |
| RTM-101-3 | tail N unique sha 語意（idle 不稀釋） | test_should_lock | MUT | 待 signoff/實作 |
| RTM-101-4 | legacy 缺 sha 寬鬆處理不破壞 | test_should_lock | — | 待 signoff/實作 |
| RTM-101-5 | 既有 history 方案 A 壓縮不假鎖定（壓縮後 unique ≤ 真實版本數） | test_migration | — | 待 signoff/實作 |
| RTM-101-6 | on-change 觸發只跑 token_guard 單模組 | （hook/CI 配置驗證） | — | 待 signoff/實作 |

## §4　階段三：實作與雙重驗證（已完成，PM signoff 2026-06-30）

### 4.1 W-101-1 去重鍵 date→sha（`tools/mutation_baseline_lock.py`）
- 新增 `_dedup_key(record)`：`source_sha256` 優先、無則 fallback `_utc_date_of_record`（legacy 向後相容）。
- `append_history` 去重鍵改用 `_dedup_key`：同 module 同去重鍵覆寫舊筆。效果＝同日多 sha 皆計入、同 sha 留最新。

### 4.2 W-101-3 migration（方案 A）
- 新增 `compact_history_by_sha(history_path, backup=True)`：按 (module, 去重鍵) 分組、留 timestamp 最新、備份 `<path>.pre_sd09_010.bak`。
- main 新增 `--migrate-compact-sha` 子命令（migration 模式免帶 module/log）。
- **真實數據驗證**：對 `.mutation_history.jsonl` 副本跑 → **30 筆 → 6 筆**（4 unique sha `5208cff/20940e1b/4af78567/55013d0a` + 2 legacy 缺 sha）；壓縮後 unique=4 < 7 → **不假鎖定**（誠實：真實只演進 4 版）。原檔 gitignored、未動。
- `should_lock` tail 語意：改 sha 去重後 history 每 sha 一筆、tail N 自然＝最近 N 個 unique sha，**邏輯無需改 code**（unique sha 守門/CONSECUTIVE_RUNS=7/0.68 threshold/MAX_BACKWARD_COMPAT_MISSING=2 全保留）。

### 4.3 W-101-2 觸發解耦（兩者皆備，掌舵者裁）
- **CI**：新 `.github/workflows/mutation-on-change.yml`（`on: push: paths: token_guard/**` + workflow_dispatch、continue-on-error 非阻塞）＝unique-sha 累積權威通道。
- **本地**：`tools/git-hooks/pre-push` 加 on-change 偵測段（opt-in `AUTOCLAUDE_MUTATION_ON_PUSH=1`、非阻塞、誠實反映 Windows mutmut 限制）。
- **nightly 角色轉監控**：`ci.yml` mutation step 加註解（鎖定累積改 on-change 驅動、nightly＝漂移監控/flaky，紀律 #6 分軌）。

### 4.4 受控突變驗牙（MUT-101-1）+ 新測試（+4）
- 新測試：`test_append_history_same_date_different_sha_all_kept`（RTM-101-1）、`_same_sha_keeps_latest`（RTM-101-2）、`_same_sha_idle_rerun_dedups_across_days`（idle 不稀釋）、`test_compact_history_by_sha_collapses_duplicates_with_backup`（RTM-101-5）。
- **MUT-101-1**（bytes 級保留 LF 行尾，遵 [[git-checkout-mutation-revert-hazard]] 教訓）：停用 `_dedup_key` sha 優先分支（退回純 date 去重）→ `same_date_different_sha`（assert 1==2）+ `idle_rerun`（assert 8==1）雙轉紅 → 還原 byte-level 乾淨。QA 鏡獨立複跑確認。

### 4.5 ADR 編號撞號修正（QA 鏡發現）
- 階段二誤以為 SD09-009 最高、新 ADR 編 SD09-010 與既有 `ADR-SD09-010-ps1-to-helper-ssot-governance.md` **撞號**（QA 鏡附帶觀察揪出）。當輪修（遵 [[no-defer-unless-justified]]）：mutation-lock ADR 改 **SD09-011**，bytes 替換本輪 8 檔 19 處 SD09-010→011（既有 ps1 的 SD09-010 在未碰檔，完好未誤傷）。

## §5　階段四：CI 平價收斂 — 零退化驗證矩陣（floor 3618，待回填）
| 檢查 | 通過條件 | 實測 |
|------|---------|------|
| AutoClaude 全套 | ≥ 3618 / 0 failed | ✅ **3622 passed / 122 skipped / 0 failed**（fresh，floor 3618 +4 新測；QA 鏡獨立複跑一致） |
| 架構契約 | 8 kept / 0 broken | ✅ **8 kept / 0 broken**（零碰 autoclaude/ 微核心、改動限 tools/+CI 配置） |
| LOC 分級 | violations=0 | ✅ **violations=0**（mutation_baseline_lock.py 在 tools/、不計 SCAN_ROOT） |
| Snapshot | 新鮮 | ✅ **OK**（零 plugin/port 增減） |
| AISDLC_SDD 閘門 | N/A①（零碰框架/*.tla） | ✅ N/A①（git status 證零碰 AISLDC_SDD/、*.tla、*.cfg） |
| DAL 等價 | N/A②（無 DAL 改動） | ✅ N/A②（零碰 infra/repositories/、tests/equivalence 隨全套通過） |
| 五軌 TLC | N/A①（零碰 *.tla） | ✅ N/A①（git status 證零碰 *.tla/FSM/_HAPPY_PATH） |

## §6　缺陷帳本本輪處置
- **DEF-101-001**（P2，mutation 鎖定日曆綁定設計缺陷，**fixed@improving_101**）已入主表（`docs/06_quality/AutoSDD_Defect_Log.md`）。
- 上輪 routed DEF-100-002（L49 死分支重構）本輪未觸及，維持 routed（improving_102 候選）。

## §7　待 PM signoff 的決策點（🔴 動 code 前須拍板）
1. **ADR-SD09-011 整體方向**：unique-sha 計數與日曆解耦，approve？
2. **Migration 方案**：方案 A（按 sha 壓縮既有 30 筆 + 備份，傾向）vs 方案 B（日切）？
3. **on-change 觸發形態**：pre-push git hook（本地、可 opt-in）vs CI on-path-change（雲端非阻塞）vs 兩者皆備？
4. **CONSECUTIVE_RUNS 是否仍維持 7**（unique sha 版本數），或調整？

## §8　誠實性標記
1. **規格先行已守**：本輪分兩段——先產出設計（ADR-SD09-011 + 計畫書設計段）停在 signoff 閘門 → PM signoff（approve、方案 A、兩者皆備）後才動 `mutation_baseline_lock.py`。signoff 前確實未動 code。
2. **收斂未結案、仍需源碼演進**：本輪解除「機制空轉」，但 token_guard 真實只演進 4 個 unique sha（壓縮後實證），距 7 還差 **3 次真實 token_guard 源碼改進**。新機制讓這 3 次可**隨開發節奏快速累積、不必熬日曆**（如 improving_102 的 DEF-100-002 L49 重構即會 +1）；最終鎖定/退出仍需 PM 決策（HUMAN_PENDING）。
3. **Windows 無法本機跑 mutmut（需 WSL/docker）**：故 on-change 累積以 CI（`mutation-on-change.yml`）為權威通道、本地 hook 為 opt-in 提示。真實 kill_rate / unique sha 累積由 CI 在 Linux 跑。
4. **N/A 兩型精確**：ci-gate/五軌 TLC＝類型①（git status 證零碰 AISLDC_SDD/*.tla/*.cfg）；DAL＝類型②（tests/equivalence 隨全套 3622 通過、無新 DAL 改動）。
5. **本輪改 tracked 源碼（tools/）非純測試**（與 improving_100 不同），但零碰 autoclaude/ 微核心。

## §9　多專家 Zero-Trust 審查閉環（三鏡全 OVERALL PASS）
序列化派發避 [[parallel-mutation-audit-collision]]：Architect + SA-SD 唯讀並行 → QA 獨佔（跑全套 + 受控突變改 tools/）。主樹派發（untracked 新檔，遵 DEF-24-001 禁 worktree）。

- **Architect（PASS P0=P1=P2=0）**：去重鍵邏輯正確、反作弊五層守門全保留（ADR §3 對照屬實）、compact 不假鎖定、零碰微核心、CI/hook 配置合理、ADR 完整。
- **SA-SD（PASS P0=P1=P2=0）**：ADR 設計 vs 實作一致、空轉根因 file:line 鐵證準確、真實 30 筆 unique sha=4 獨立驗算吻合、supersede 註記準確、RTM/N/A 一致。
- **QA（對抗，PASS P0=P1=P2=0）**：獨佔跑全套 3622、受控突變兩測有牙（FAIL→還原 PASS、byte-level 乾淨）、compact 30→6 精準、反作弊未弱化、新測非空殼、零碰微核心。
- **🔴 finding 處理**：
  - QA 揪出 **ADR 編號撞號**（我的 SD09-010 與既有 ps1-governance 撞）→ 當輪修為 SD09-011（§4.5）。
  - SA-SD 報「缺陷帳本無 DEF-101」經 parent 親核**駁回為假陰性**（QA 推定肇因＝SA-SD grep 路徑錯置 `AutoClaude/docs/` vs monorepo 根 `docs/`；parent grep count=1 證 DEF-101-001 在）。又一「對 audit agent 結論亦須 zero-trust 親核」實證（同 improving_100 codepoint 假陽性家族）。
- **結案判定**：三鏡技術全 PASS、撞號當輪修畢、假陰性駁回、無真實未修缺陷 → **准予結案**。
