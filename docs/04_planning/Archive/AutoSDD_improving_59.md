# AutoSDD improving_59 — B 軌成熟度推進：規則自演化「活體化」（SLV 自動提議預設 ON，B L4→L5）

> **軌道定位**：軌道① **B 軌（柱②手腳 AISLDC_SDD）成熟度推進輪**。把規則自演化「自動提議」從 opt-in 鷹架（預設 OFF）翻為**活體常態**（預設 ON、顯式 opt-out），鏡像 W-15 AUTO_RECOVERY（B L3→L4）的翻環先例。
> **下一份**：`AutoSDD_improving_60.md`（候選＝A→L5 協作元學習，解除 L_合體 最後綁定）。**日期**：2026-06-24。
> **driver instance**：W-16 自動提議活體化（**非** XAI Turn——本輪不涉 meta⁷⁺／良基終止／互遞迴／具身接地，🔭 視覺化轉向不觸發）。
> **結論先行**：階段一硬閘全綠（AutoClaude 3265/0、ci-gate exit 0：v0.01:1478/v0.22:1655/scripts:128、lint 8/0、LOC 0、snapshot fresh、improving_58 構件全真、無 open in-repo 缺陷）。本輪 Copy-on-Evolve 建 **v0.23**，翻 `_slv_auto_propose_enabled()` 預設 OFF→ON（保留顯式 opt-out + 全紅線：R-9.11 proposed 恆不自動升 verified、R-9.24 meta-halt、reviewed_by 必填）。回歸面經 zero-trust 掃描精確收斂為**僅 1 處測試**（Case 1）。**免五軌 TLC**（零 `_HAPPY_PATH`/`*.tla` 變更，僅翻 side-effect 預設；與 W-15 同型，[fsm_runtime.py:42-43](../../AISDLC_SDD/AISDLC_SDD_v0.22/tools/fsm_runtime/fsm_runtime.py) 先例自證）。**誠實會計**：B L4→L5 為真，但 `L_合體=min(A=L4,B=L5,C=L5)=L4` **本輪不變**（綁定約束由 {A,B} 縮為僅 A）；reach L_合體=L5 需後續 A→L5 輪。

---

## 1. 本輪輸入（自上輪繼承）

- 上輪＝improving_58（B 軌補救輪，揭露並修復 57 帶紅入庫）。最新框架版 **v0.22**。
- 上輪 RTM：R-58-1~7 全 ✅；無未完成 W 項。
- 缺陷帳本（Explore 複核）：DEF-23-005/30-001/31-001/32-002/19-001 皆已 fixed/closed；**無乾淨可在倉內就地修的 open B 軌缺陷**。DEF-01-007（cc-switch 環境）、DEF-01-009（LOC watch）、DEF-17-001（fire 遙測 routed）、DEF-53-001（latent routed）維持原狀（justified）。
- 上輪審計遺留：無 partial。

## 2. 階段一：現況重偵察（Zero-Trust Re-Audit，parent 親跑 + 3 Explore agent 複核）

### 2.1 零退化基線（硬閘）

| 項目 | 命令 | 實測 | floor | 結果 |
|------|------|------|-------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | **3265 passed / 122 skipped / 0 failed** | 3265 | ✅ 持平 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | — | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0（total=18663/cap=20438） | — | ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | fresh | — | ✅ |
| AISDLC_SDD ci-gate | `bash scripts/ci-gate.sh; echo $?` | **exit 0**（v0.01:1478 / v0.22:1655 / scripts:128） | — | ✅ |

**硬閘判定**：(a) AutoClaude pytest 無 failed、未低於 floor 3265；(c) ci-gate 真實 exit 0（58 已清 57 隱性紅）→ **准進階段二**。

### 2.2 自演化機具現狀（zero-trust 實測，檔:行號見 §下）

派兩 Explore agent 對 `AISLDC_SDD_v0.22/tools/fsm_runtime/` 自演化機具測繪，**關鍵裁決一個跨 agent 矛盾**（Rule 7）：

- **矛盾**：agent-1 稱「翻 env 預設 ON 必須重跑五軌 TLC」（理由：churn 會累積）；agent-2 稱「零架構變更、TLC 免重跑」（理由：只改 side-effect、轉態邊/*.tla 不變）。
- **裁決＝agent-2 正確**。鐵證：[fsm_runtime.py:42-43](../../AISDLC_SDD/AISDLC_SDD_v0.22/tools/fsm_runtime/fsm_runtime.py)（W-15 AUTO_RECOVERY 翻環先例）明文「轉態邊與 `_HAPPY_PATH`/`*.tla` **零變更**（improving_15 已模型化、五軌 TLC 已證有界），本輪僅翻轉『誰觸發』的預設」。META_FSM.tla 的 `ChurnBounded`/`GraduationRatchet` 是**靜態不變量**，TLC 早已窮舉 MAX_CHURN 內全部 churn 值——runtime 預設 ON/OFF 不改模型。agent-1 把「runtime churn 會累積」誤當「模型變了」。
- **side-effect gate**（[fsm_runtime.py:2687](../../AISDLC_SDD/AISDLC_SDD_v0.22/tools/fsm_runtime/fsm_runtime.py)）：`if decision=="learn" and _slv_auto_propose_enabled() and fpl_id:` ——**無 fpl_id → 不 draft**。
- **紅線實證**（exit_learning_commit）：approve 前強制 `trust_level=="verified"` 且 `reviewed_by` 非空，否則 raise（R-9.11）；meta-halt 違反 → 改導 ESCALATION（R-9.24）。皆**不在本輪改動面**。

### 2.3 三軸成熟度（階段一實測）

| 軸 | 實測級（本輪起點） | 依據 |
|----|------|------|
| **C 引擎**（AutoClaude） | **L5** | 自演化 wire 進 ESCALATION 閉環 + 跨 session DAL 元學習（沿用） |
| **B 流程**（AISLDC_SDD） | **L4 →（本輪）L5** | 起點：AUTO_RECOVERY 預設 ON（L4）；SLV/GC/遙測自演化機具皆 opt-in OFF（未活體）。本輪翻 SLV 自動提議活體 → L5 自演化常態 |
| **A 協作**（雙向橋接） | **L4** | 有界自動凍結 signoff；無失敗→轉譯策略元學習迴圈。本輪不動 |

**上捲（本輪終局）**：`L_合體=min(A=L4, B=L5, C=L5)=**L4**`。
> **🔴 誠實標註**：B 確實 L4→L5（自演化活體化為真），但 **L_合體 維持 L4**——綁定約束由 improving_58 的「{A=L4, B=L4} 雙綁」縮為「**僅 A=L4** 綁」。本輪**不謊報 L_合體 推進**；reach L_合體=L5 須後續 A→L5 輪。不變式 `A ≤ min(B,C)=L5` 翻後成立（A 有成長空間）。

## 3. 階段二：增量設計

### <Architecture_Design_Review>（實作前）

1. **架構純潔性**：零 AutoClaude `core/`/`plugins/` 變更（不碰微核心）。SDD 側僅翻 1 個 env-flag 預設函式（`_slv_auto_propose_enabled` 邏輯 OFF-default→opt-out 形態，鏡像既有 `_auto_recovery_enabled`）+ 同步註解/docstring。**無新狀態、無新轉態邊、無 God-object**。✅
2. **持久化相容**：不碰 PlaybookCheckpoint/DAL schema；`learning_commit_tracking` 既有 additive 欄位（origin/auto_proposed_count）不變。✅
3. **安全防護網**：自動 draft 僅產 `trust_level=proposed` 草案（R-9.11 守界不可繞），無 shell/外部輸入、無 CONDITIONAL 路徑變更。✅
4. **對外 I/O 安全**：本輪不新增 `ToolInvocationPort` 外呼路徑。✅
5. **誠實性/零退化**：floor AutoClaude 3265 / v0.23 繼承 v0.22:1655（+本輪新測試只增不減）；ci-gate 退出碼直取 `echo $?` 不經 `| tail`。✅

### Copy-on-Evolve / 五軌 TLC 判定

- 改動落在 `tools/fsm_runtime/fsm_runtime.py`（v0.22 **凍結本體**）→ **必須 Copy-on-Evolve 建 v0.23**（不可原地改凍結版）。本輪同時 dogfood improving_58 的 DEF-58-002 硬化（`copy_on_evolve.sh` 建版即自動同步戳記）。
- **無 `_HAPPY_PATH` / `*.tla` / `*.cfg` / `transition_rules.py` 變更** → **免五軌 TLC**（僅翻 side-effect 預設，同 W-15 先例）。ci-gate 的 `test_tla_python_sync` 仍守雙源無漂移；若工具鏈具 Java+tla2tools.jar，另跑 `--full-tlc` 作補強證據（非必要）。

### 本輪 W 項（≤3，B 軌 Brownfield SCG-0~3）

| W 項 | 內容 | 落點 | 對應紅線/契約 |
|------|------|------|--------------|
| **W-59-1** | Copy-on-Evolve v0.22 → **v0.23**（驗 DEF-58-002 硬化自動同步戳記） | `AISDLC_SDD_v0.23/` + EVOLUTION_LOG + CHANGELOG | Copy-on-Evolve |
| **W-59-2** | v0.23 翻 `_slv_auto_propose_enabled()` 預設 OFF→ON（顯式 opt-out 保留）+ 同步 docstring/comment（line 60/2656）+ EVOLUTION_LOG 回退指引更新 | `v0.23/tools/fsm_runtime/fsm_runtime.py` | R-9.11 / R-9.24 不弱化 |
| **W-59-3** | 測試遷移 + 活體驗收 + Rule 9 突變：Case 1 改 opt-out 語意（+`_redirect_rules`）；新增 default-ON 活體 case（env unset → 自動 draft proposed）；新增紅線恆守 case（default-ON 下 proposed 仍不自動升 verified） | `v0.23/.../tests/test_slv_auto_propose_wiring.py` | Rule 9 非空殼 |

### 回歸面（zero-trust 掃描結論）

- 全 v0.22 learn-path 呼叫點：`test_phase_i.py:328`（**無 fpl_id** → gate 不觸發，default-ON 安全）；`test_slv_auto_propose_wiring.py` 多處（除 Case 1 外皆顯式設 env）。
- production runtime **無**自動呼叫 `exit_production_behavioral_signal("learn", fpl_id=...)`（僅測試/互動 CLI 驅動）→ 翻預設 ON 不造成失控自動寫入。
- **唯一回歸**：Case 1 `test_flag_off_learn_pure_transition_no_auto_slv`（`delenv`+fpl_id → 斷言無 auto_slv）。翻預設後須改為 opt-out 語意，且補 `_redirect_rules`（避免 default-ON 寫進真實 rules 目錄）。
- chaos（nightly，非 PR 閘）：驗證無場景斷言 default-OFF（階段三/審計複核）。

## 4. 階段三：實作與雙重驗證（實測）

### W-59-1（R-59-1 fixed）Copy-on-Evolve 建 v0.23 + DEF-58-002 dogfood
`bash scripts/copy_on_evolve.sh AISDLC_SDD_v0.22 AISDLC_SDD_v0.23` → 匯出 860 tracked 檔；**DEF-58-002 硬化端到端 dogfood 成功**：建版後自動跑 `skill_header_sync --write`（45 檔戳記同步 v0.23）+ `sync_exposed_skills --write`（59 檔父鏡像重生），零人工後步驟。EVOLUTION_LOG.md / releases/CHANGELOG.md 補 v0.22→v0.23 條目；FRAMEWORK_STATUS.md 重生（LATEST→v0.23）。

### W-59-2（R-59-2 fixed）SLV 自動提議活體化
`v0.23/tools/fsm_runtime/fsm_runtime.py:_slv_auto_propose_enabled()` 翻 opt-out 語意（unset→True；顯式 falsy→opt-out OFF），鏡像 `_auto_recovery_enabled()`。同步 docstring（line 2664「預設 ON、顯式 opt-out」）。**紅線零弱化**：gate `decision=="learn" and _slv_auto_propose_enabled() and fpl_id`、草案恆 proposed、`exit_learning_commit` verified+reviewed_by 強制檢查不動。

### W-59-3（R-59-3/R-59-5 fixed）測試遷移 + 活體驗收 + 突變
`test_slv_auto_propose_wiring.py` 9→10 case：Case 1 改寫為 `test_default_on_learn_auto_drafts_proposed_def_59`（unset→自動 draft proposed）；新增 `test_default_on_redline_proposed_never_auto_promotes_def_59`（預設活體下 approve-without-verify 仍 raise，R-9.11）；`test_explicit_opt_out_is_sole_switch_even_with_fpl`（顯式 opt-out 純轉態零退化）。**受控突變 M-W592**：把 `_slv_auto_propose_enabled` 預設改回 False → 2 個 default-ON case 轉紅（其餘 8 顯式設 env 仍綠），還原後 10 passed、grep `MUTATION` 零殘留。

### W-59-4（DEF-59-001 fixed，dogfooding 意外發現的根因硬化）
階段四 ci-gate 當場揭露：建 v0.23 後 `.gitignore` 無 v0.23 runtime block → gitignore 覆蓋 lint 報紅（**DEF-58-002 同根因家族**：人工後步驟未釘進腳本）。① 立即修 `.gitignore` 補 v0.23 block；② **根因硬化** `copy_on_evolve.sh` 建版後自動 append 新版 .gitignore block（idempotent、grep-skip 首行 path、`set -e` fail-loud）；③ 回歸鎖 `test_copy_on_evolve.py::test_auto_appends_gitignore_block_on_evolve_def_59_001`（scripts/tests 128→129）。**受控突變 M-W593**：`if false &&` 停用自動補 → 該測轉紅（58 戳記測試仍綠），還原 9 passed。

### 回歸面實證（zero-trust 掃描兌現）
唯一回歸＝Case 1（已遷移）。v0.23 全套 not-chaos **1656 passed**（v0.22 1655 +1 淨新增），翻預設零波及其他測試；`test_phase_i.py:328`（無 fpl_id）gate 不觸發；chaos 無 SLV 場景（grep 零命中）。

## 5. 階段四：CI 平價收斂（零退化矩陣，parent 親跑、退出碼不遮蔽，實測）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3265 / 0 failed | ✅ **3265 / 122 skipped / 0 failed**（本輪零 AutoClaude 變更） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept | ✅ **8 kept / 0 broken** |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | ✅ violations=0（total=18663/cap=20438） |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh; echo $?` | **exit 0**（不經 `\| tail`） | ✅ **CIGATE_EXIT=0**；v0.01:1478 / v0.23:1656 / scripts:**129** |
| 戳記/skills SSOT | ci-gate 內 lint | OK | ✅ skill-header LATEST=v0.23 全對齊、skills-ssot 父鏡像==v0.23 59 檔 |
| gitignore 覆蓋 | ci-gate 內 lint（DEF-37-001） | block 齊備 | ✅ v0.23 runtime block 齊備（DEF-59-001 修後） |
| 潔淨度 dry-run | `git add -A -n`（DEF-11-002） | 零 runtime 漏網 | ✅ 911 would-add，v0.23 無 build/reports/.pyc/states/lib 漏網 |
| 五軌 TLC | — | 僅 FSM 變更時 | N/A（`transition_rules.py` + 5 `*.tla`/`.cfg` 對 v0.22 逐位元零差異，diff 證） |

## 6. RTM（本輪需求追溯）

| 需求 | 驗收標準 | 證據 | 狀態 |
|------|---------|------|------|
| R-59-1 Copy-on-Evolve 建 v0.23 | v0.23 結構同構 + 戳記自動同步 v0.23（DEF-58-002 dogfood）+ EVOLUTION_LOG/CHANGELOG | §4 W-59-1 | ✅ 860 檔、戳記 45+鏡像 59 自動同步 |
| R-59-2 SLV 自動提議活體化 | `_slv_auto_propose_enabled()` unset→ON、顯式 falsy→opt-out OFF；docstring 同步 | §4 W-59-2 | ✅ |
| R-59-3 紅線零弱化 | default-ON 下 proposed 恆不自動升 verified（R-9.11）、meta-halt 仍守（R-9.24）、reviewed_by 必填 | §4 W-59-3 測試 | ✅ test_default_on_redline_... |
| R-59-4 零退化 | AutoClaude 3265、v0.23 ci-gate exit 0（≥1655 + 新測試）、TLC 免 | §5 矩陣 | ✅ 全項綠 |
| R-59-5 回歸鎖非空殼 | 突變：翻 default 回 OFF → 活體 case 轉紅；還原綠 | §4 M-W592/M-W593 | ✅ 兩突變實證 |
| R-59-6 三鏡 zero-trust 全 PASS | Architect/SA-SD/QA 審查（主樹派發） | `AutoSDD_ZeroTrust_Audit_59.md` | ✅（見 §7） |
| R-59-7 成熟度誠實 | B L4→L5 有據；L_合體 維持 L4 不謊報 | §2.3 | ✅ |
| R-59-8 DEF-59-001 根因硬化 | copy_on_evolve.sh 自動補 .gitignore block + 回歸鎖 | §4 W-59-4 | ✅ |

## 7. 三鏡 zero-trust 結果

見 `docs/06_quality/AutoSDD_ZeroTrust_Audit_59.md`。本輪含大批 **untracked 新檔**（`AISDLC_SDD_v0.23/` 860 檔）→ 三鏡皆**主樹派發**（DEF-24-001 鐵律：審 untracked 新檔嚴禁 worktree；無並行突變）。潔淨度依 DEF-11-002 跑 `git add -A -n`（911 would-add，零 runtime 漏網）。

## 8. 結論與誠實級別標註

本輪＝**B 軌成熟度推進輪**（L4→L5）+ dogfooding 意外捕獲一個 DEF-58-002 同家族根因（DEF-59-001）並當場硬化。誠實重點：

1. **B L4→L5 為真，但 L_合體 維持 L4（不謊報）**：規則自演化「自動提議」由 opt-in 鷹架翻為活體常態（鏡像 W-15 AUTO_RECOVERY 翻環先例），B 軸自演化常態化＝L5。但 `L_合體=min(A=L4, B=L5, C=L5)=L4` **本輪不變**——綁定約束由 improving_58 的「{A,B} 雙綁」縮為「**僅 A=L4** 綁」，reach L_合體=L5 須後續 A→L5 輪（improving_60 候選）。**不變式 `A ≤ min(B,C)=L5` 翻後成立**（A 有成長空間）。
2. **紅線零弱化**：翻預設僅改 side-effect（自動 draft proposed），R-9.11（proposed 恆不自動升 verified）、R-9.24（meta-halt）、reviewed_by 必填皆不動，並以 `test_default_on_redline_proposed_never_auto_promotes_def_59` 鎖住「活體化不得順帶弱化人類掌舵紅線」。
3. **免五軌 TLC 有據**：`transition_rules.py` + 全部 5 `*.tla`/`.cfg` 對 v0.22 **逐位元零差異**（diff 證），僅翻 runtime 預設；META_FSM 的 ChurnBounded/GraduationRatchet 為靜態不變量，與 runtime 預設無關。裁決了階段一兩 Explore agent 對「是否需重跑 TLC」的矛盾（Rule 7）。
4. **dogfooding 根因硬化（DEF-59-001）**：improving_58 把戳記同步釘進建版腳本，本輪建 v0.23 即踩到「.gitignore block 補寫」這個**同家族**未釘進腳本的人工後步驟。依 [[no-defer-unless-justified]] 當場根因硬化（非貼 OK 繃），使下次 Copy-on-Evolve 不再復發。

**延後（justified，維持原狀態）**：DEF-01-007（cc-switch 環境）、DEF-01-009（LOC watch）、DEF-17-001（fire 遙測 routed；本輪刻意未翻 RULE_FIRE_TELEMETRY 預設，屬 L5-internal 代謝 arm，非本輪核心自演化信號）、DEF-53-001（latent routed）。
**B 軸 L5 殘留 opt-in arm（誠實標註，非本輪 scope）**：SCAFFOLD_GC_AUTO_PROPOSE / RULE_FIRE/CATCH_TELEMETRY 仍預設 OFF（arch_fitness FF-16 advisory 點名「GC 從未產退役 ROI」即此）——本輪 B=L5 立基於**核心規則自演化迴圈活體**，代謝/遙測 arm 為 L5-internal 精修，候選後續輪（避免一次翻多旗增回歸面，Rule 2）。

**回流**：框架本體改動落 `AISDLC_SDD_v0.23/`（Copy-on-Evolve）+ EVOLUTION_LOG + CHANGELOG；DEF-59-001 根因硬化落 shared infra `scripts/`（免 Copy-on-Evolve）。無 `*.tla` 變更（人工 signoff＝掌舵者 AskUserQuestion 授權翻預設）。
