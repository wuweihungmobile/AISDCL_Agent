# AutoSDD_improving_88 — production Kernel self-correction × expected_output_regex 閘交互修復（C 軌）

> **本輪柱位**：**C 軌（指揮官 AutoClaude 自身能力：self-correction loop 收斂正確性）**，觸及 A 軌（Brain↔Kernel prompt 餵回語意）。對齊北極星第 1 點——AutoClaude＝以狀態機管理執行流程／重試／錯誤升級的引擎；self-correction 必須在「step 同時有 regex 閘 + evaluator 閘」時仍能正確收斂，否則閉環在常見 playbook 形態下假性卡死到 escalate。
> **下一份**：improving_89。
> **框架版**：本輪零碰 AISLDC_SDD 框架本體（生產碼全在 AutoClaude `core/kernel.py` + 測試）→ 免 Copy-on-Evolve、維持 v0.27。`L_合體=min(A,B,C)=L5` 不變（缺陷修復/收斂正確性加固，非成熟度推進）。
> **掌舵者裁示**：2026-06-27 裁定 DEF-87-001 production 方向＝**「Kernel 自動保留 regex 約束」**（選項 A，AskUserQuestion 紀錄）。即套用 Brain CORRECTION 時，若該 step 有 `expected_output_regex`，由 Kernel 確定性地把該約束重新注入修正後 prompt，使 Brain 改寫永不丟失輸出約束——兩道閘並存、不靠 Brain 自律。

---

## §1 本輪輸入（自上輪繼承）

### 1.1 improving_87 結案狀態（RTM 收尾）
- improving_87＝C 軌 × A 軌 Brain 指揮 Claude Code self-correction 閉環「端到端真跑」首證（commit b057e63）。
- 已完成 W 項：W-87-1（mock brain × 真 Claude 閉環真跑，連 3 跑穩定）/ W-87-2（真 Minimax × 真 Claude，真 key 不入庫）。未完成 W 項：無。
- 上輪審計三鏡（Architect / SA-SD / QA）全 OVERALL PASS（P0=0/P1=0）。
- **上輪真跑揪出的最有價值缺陷 DEF-87-001（P2 production 級）即為本輪標的**：87 輪 smoke 端已緩解（改用 pytest 當唯一權威閘），production 端是否由 Kernel 自動保留 regex 為設計決策 → 掌舵者已裁示選項 A（見上）。

### 1.2 缺陷帳本 open / routed（本輪處置計畫）
| 缺陷 | 狀態 | 本輪處置 |
|------|------|---------|
| **DEF-87-001（self-correction × regex 閘交互 P2，production）** | partially-fixed@87（smoke）+ routed（production 決策） | **本輪 W-88-1 修復 production Kernel；掌舵者裁示選項 A** |
| DEF-87-002（生產 logger cp950 console ✓ 崩潰 P3） | open（routed） | 本輪不取（非致命，utf-8 檔案 log 完整）→ 維持 routed |
| DEF-01-007（cc-switch GUI P3） | open | 不涉多後端切換 → 維持 |
| DEF-01-009（sdd_governance_plugin LOC watch P3） | open watch | 零碰該檔 → 維持 |
| DEF-23-005 / DEF-62-001 / DEF-17-001 / DEF-19-001 / DEF-35-001 | open / routed | 不涉本輪 scope → 維持 |

### 1.3 上輪遺留候選處置
- improving_87 §8 backlog 首位＝DEF-87-001 production 決策 → **本輪取**。其餘（SD_09 W1 source-sha 閘門、更長 playbook per-step token%、v2.0 格式漂移閘 production 攔阻）本輪不取。

---

## §2 階段一實測（Zero-Trust Re-Audit，2026-06-27）

> 派 Explore agent 主樹親跑（非採信文件宣稱），硬閘 PASS 才進階段二。

| 項目 | 命令 | 實測 | 狀態 |
|------|------|------|------|
| (a) AutoClaude 全套 pytest | `python -m pytest tests/ -q`（Bash） | **3514 passed / 0 failed / 122 skipped**（與上輪基線完全一致） | ✅ 硬閘 PASS |
| (b) lint-imports | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | ✅ |
| (c) LOC budget | `python tools/check_loc_budget.py` | violations=0（total 19783 / baseline 17032 / cap 20438） | ✅ |
| (d) snapshot | `python tools/snapshot_sync.py --check` | OK（FRESH） | ✅ |
| (e) AISDLC_SDD ci-gate | `bash scripts/ci-gate.sh` | N/A①（本輪零碰 AISLDC_SDD/，上輪已驗 exit 0；git 僅 `?? ci-gate-output.log` 偵測檔） | ✅ |
| (f) git 工作樹 | `git status --short` | 乾淨（僅 untracked `AISDLC_SDD/ci-gate-output.log`） | ✅ |
| (g) improving_87 構件 | grep/開檔/pytest | correction_loop_smoke.yaml / ab_configs/correction_{mock,real}_config.yaml / tools/correction_loop_verify.py / tests/tools/test_correction_loop_verify.py（7 passed）/ improving_87.md / Audit_87.md 全存在 | ✅ 無虛報 |
| (h) DEF-87-001 機制複驗 | 開檔 | `core/kernel.py:259-260` `if c.correction_prompt: task.prompt = c.correction_prompt` 真實存在 → 問題機制仍在 production 碼 | ✅ 確認待修 |

### 2.1 接線實測（決定本輪設計的關鍵事實）
- **CORRECTION 套用點**（`core/kernel.py:259-260`）：`if c.correction_prompt: task.prompt = c.correction_prompt`——Brain 修正 prompt **整個取代** `task.prompt`，原 prompt 內隱含的「輸出須含某 keyword」要求隨之丟失。
- **雙重驗證閘**（`infra/adapters/shell_evaluator.py`，經 `self._eval.evaluate(task, output)`）：先比對 `task.expected_output_regex`（ANSI strip 後），再跑 `evaluator_command`；**任一失敗即回 failure_reason**。
- **DEF-87-001 失效鏈**：step 同掛 `expected_output_regex`（要求輸出含 keyword X）+ `evaluator`（如 pytest）→ 程式 bug 致 evaluator 初次失敗 → Brain 回修正 prompt（只談「修程式」，丟掉 keyword X 要求）→ `task.prompt` 被取代 → 重試：程式修對了、evaluator 過了，但**輸出不再含 keyword X → regex 閘永遠不過** → 重試耗盡 → escalate（首跑即實證 CORRECTION×3 後 escalated=True）。
- **task 結構**：`task = playbook.tasks[step_idx]`（`models/playbook.py:PlaybookTask`），`expected_output_regex` 為其欄位（可為 None）。
- **CorrectionDecision**（`models/decision.py:8-13`）：`correction_prompt: str` + `reasoning` + `task_goal_summary?` + `step_mutation?`。

**硬閘 PASS** → 進階段二。

---

## §3 階段二增量設計

### 3.1 本輪 W 項（單項，聚焦）
| W 項 | 內容 | 柱位 | LOC 落點 |
|------|------|------|---------|
| **W-88-1** | production Kernel 套用 Brain CORRECTION 時，若該 step 有 `expected_output_regex`，自動把該約束重新注入修正後 prompt（確定性保留輸出契約，不靠 Brain 自律）。掌舵者裁示選項 A。 | C 軌（A 軌語意） | `core/kernel.py`（default tier ≤750；新增私有 helper ~8 logical LOC，零新增 import） |

### 3.2 介面 delta
- **無對外介面變更**：不改 `IBrain` port、不改 `CorrectionDecision` 模型、不改 `PlaybookTask` 模型、不改 checkpoint 結構。
- **內部**：`core/kernel.py` 新增私有方法 `_preserve_output_contract(task, correction_prompt) -> str`；`_run_step` 內 line 259-260 的賦值改走此 helper。
- **additive 行為**：
  - `task.expected_output_regex` 為 falsy（None/空）→ 原樣回傳 `correction_prompt`（**與現行行為位元級一致 → 零退化**）。
  - `correction_prompt` 已含該 regex pattern（Brain 自己保留了）→ 原樣回傳（**冪等、不重複附加**）。
  - 否則 → 在 `correction_prompt` 後附加一段「硬約束·勿遺漏：輸出須匹配 expected_output_regex: {regex}」。
- **冪等性**：helper 永遠以 Brain 當次回傳的**新鮮** `c.correction_prompt` 為基底再附加（非累加在 `task.prompt` 上），加上「已含則跳過」守衛 → 多次 correction 不會累積膨脹。

### 3.3 對 `.importlinter` 各 contract 影響分析
| Rule | 影響 |
|------|------|
| 1 Plugins 互不 import | 無（不動 plugins） |
| 2 core(excl. wiring) 不依賴 execution/infra | 無（helper 僅用 `PlaybookTask`（已 import）+ 字串操作，零新 import） |
| 3 `_runner_internals` 不被 core/plugins import | 無 |
| 4/5 Brain↔Executor 不互 import | 無（不動 adapters） |
| 6 runner/strategy 不 import checkpoint 內部 | 無 |
| 7 plugins 不 import observability helper | 無 |
| 8 plugin 不直接 import IKbMetricStore | 無 |
→ **預期 8 kept / 0 broken 不變。**

### 3.4 checkpoint additive 欄位需求
- **無**。本輪不新增任何持久化欄位；`task.prompt` 的 in-memory 改寫行為與既有 line 259-260 同性質（既有亦改寫 task.prompt），既有 `last_correction_prompt` checkpoint 欄位語意不變。→ DAL 三後端零停機維持、無新 round-trip 契約。

### 3.5 RTM 需求列（驗證對應，§5 階段三/四回填實測）
| RTM-ID | 需求 | 驗證測試（規劃） |
|--------|------|----------------|
| RTM-88-1 | 同掛 regex+evaluator 的 step，Brain 丟 keyword 的修正下仍能收斂成功（不 escalate） | `test_correction_preserves_regex_converges`（FakeBrain 丟 keyword + echo executor + regex 閘 → success） |
| RTM-88-2 | 套用 correction 後 `task.prompt` 確實含 regex 約束 | `test_correction_appends_regex_to_prompt` |
| RTM-88-3 | 無 regex 的 step → 修正後 prompt 與 Brain 回傳位元級一致（零退化） | `test_no_regex_correction_prompt_unchanged` |
| RTM-88-4 | Brain 修正 prompt 已含 regex pattern → 不重複附加（冪等） | `test_idempotent_no_double_append` |
| RTM-88-5 | 多次 correction 不累積膨脹（每次以新鮮 correction_prompt 為基底） | `test_multi_correction_no_accumulation` |
| MUT-88-1 | 受控突變：把 helper 還原成 `task.prompt = c.correction_prompt` → RTM-88-1 轉紅（證測試有牙） | 手動突變 + Edit 還原（禁 git checkout，遵記憶紀律） |

### 3.6 <Architecture_Design_Review>（寫實質 Python 前必輸出）
1. **架構純潔性 / Thin Facade**：是否創 God-object？→ 否。helper 為 kernel 內 ~8 行私有方法，緊鄰既有 `task.prompt = c.correction_prompt`（既有 correction 處理：decide_correction 呼叫、CORRECTION marker log、mutation apply 全在 kernel inline，非走 bus）→ 新 helper 與既有慣例一致（工程紀律 Rule 11）。是否該走 `bus.emit` 委外？→ 否：此為**確定性字串組裝**、僅 gate 在既有 `task.expected_output_regex` 欄位，無業務判定/無外部副作用，路由成新 hook/plugin 屬過度設計（Rule 2 簡單優先）。kernel docstring 設計企圖 ≤250；機械閘 default tier=750，新增 ~8 行安全。
2. **持久化相容**：新狀態是否 additive 寫入 PlaybookCheckpoint？→ 本輪零新增持久化欄位；in-memory `task.prompt` 改寫與既有同性質。DAL 三後端零停機維持。
3. **安全防護網（CONDITIONAL）**：本輪是否新增「從文件生成指令」路徑？→ 否。helper 僅把既有 `task.expected_output_regex`（使用者於 playbook 已宣告之 regex 字串）**回填進 prompt 文字**（給 Claude 閱讀，非組裝 shell 指令）→ 不經 CONDITIONAL 指令生成路徑、不弱化白名單/黑名單/shell=False 三層防禦。
4. **對外 I/O 安全**：本輪是否新增 `ToolInvocationPort` 外呼路徑？→ 否。無網路 I/O、無新外呼能力。
→ **四項自我驗證全 PASS，准予實作。**

---

## §4 階段三：實作與雙重驗證

### 4.1 實作紀錄
- **生產碼**（`autoclaude/core/kernel.py`）：
  - 新增 `@staticmethod _preserve_output_contract(task, correction_prompt) -> str`（~8 logical LOC + docstring）：無 regex 或 correction_prompt 已含該 pattern → 原樣回傳；否則附加「[硬約束·勿遺漏] …expected_output_regex：{regex}」。
  - `_run_step` 內 line 259-260 賦值由 `task.prompt = c.correction_prompt` 改為 `task.prompt = self._preserve_output_contract(task, c.correction_prompt)`。
  - 零新增 import（`PlaybookTask` 已 import）；kernel.py default tier=750，新增後仍 violations=0。
- **測試**（`tests/core/test_kernel.py`）：新增 `TestKernelCorrectionPreservesRegex`（5 測試，對應 RTM-88-1~5）+ 3 個本地 fake（`_EchoExecutor`/`_RegexGateEvaluator`/`_DropKeywordBrain`）。
- **開發-編譯-測試循環**：改 kernel → 立即跑 `test_kernel.py`（首跑揪出測試自身缺陷：echo executor 太字面 + 帶反斜線 regex 字串無法自我匹配 → 改用純 keyword regex `KEYWORD_X`，純測試修正、零碰生產碼）→ 20 passed。

### 4.2 受控突變結果（MUT-88-1）
- 突變：把 line 260 還原成 `task.prompt = c.correction_prompt`（移除 regex 保留）。
- 結果：`TestKernelCorrectionPreservesRegex` **2 failed / 3 passed**——走 kernel 路徑的整合測試 RTM-88-1（收斂）+ RTM-88-2（prompt 含 regex）**轉紅**；3 個直接呼叫 helper 的純函式測試（RTM-88-3/4/5）仍綠（合理：突變的是 kernel 賦值點、非 helper 本身）。→ **證整合測試確實咬住生產碼修復點，測試有牙。**
- 還原：以 Edit 改回（遵記憶〔git-checkout-mutation-revert-hazard〕禁 `git checkout --`），還原後 5 passed。

---

## §5 階段四：零退化驗證矩陣（結構同步 improving_01 §5.3；通過條件以本輪實測為準，floor=improving_87 實測）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 3514 passed / 0 failed（floor=improving_87 實測；新測只增不減） | ✅ **3519 passed / 0 failed / 122 skipped**（=3514 +5 新測） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken | ✅ **8 kept / 0 broken** |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0 | ✅ **violations=0**（total 19783→**19802**，+19 全在 kernel helper；cap 20438） |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | ✅ **OK（FRESH）** |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | N/A①（零碰 AISLDC_SDD/，附 git diff 鐵證；上輪已驗 exit 0） | ✅ **N/A①**：`git status --short` ＝ `M AutoClaude/autoclaude/core/kernel.py`/`M AutoClaude/tests/core/test_kernel.py`/`M docs/06_quality/AutoSDD_Defect_Log.md`（帳本更新）/`?? docs/04_planning/AutoSDD_improving_88.md`，**零 AISLDC_SDD/ 改動** |
| DAL 等價 | equivalence job | N/A②（`tests/equivalence/` 隨全套 pytest 通過；本輪無新 DAL/checkpoint 改動故無新增 round-trip 契約） | ✅ **N/A②**：`tests/equivalence/` **86 passed**（隨全套通過；本輪零 DAL/checkpoint 改動故無新增 round-trip） |
| 五軌 TLC | `bash scripts/ci-gate.sh --full-tlc` | N/A①（零碰 `*.tla`/FSM；TLC 不在 pytest 全套、需 Java；附 git diff 鐵證） | ✅ **N/A①**：git diff 零碰 `*.tla`/FSM（改動僅 kernel.py 字串組裝 helper，未觸 `_HAPPY_PATH`/狀態機） |

---

## §6 多專家 Zero-Trust 審查（主樹派發，禁 worktree）
三鏡全 **OVERALL PASS（P0=0 / P1=0）**，完整證據見 [AutoSDD_ZeroTrust_Audit_88.md](../06_quality/AutoSDD_ZeroTrust_Audit_88.md) §4：
- **Architect**：架構純潔（純函式單一職責、零新 import、未破壞既有 correction 流程）、lint 8 kept、LOC violations=0、零碰 AISLDC_SDD/*.tla。
- **SA-SD**：獨立親跑複核數字逐一吻合（3519/0/122、equivalence 86、regex 5 passed）；規格→實作→測試三者一致。
- **QA**：主樹序列突變還原驗紅（突變後 RTM-88-1/88-2 轉紅精確重現失效鏈、Edit 還原後 5 passed）；揪 §5 漏記 Defect_Log P2 已當場補正。

## §7 結案四件套
1. `docs/04_planning/AutoSDD_improving_88.md`（本檔）✅
2. `docs/06_quality/AutoSDD_ZeroTrust_Audit_88.md` ✅
3. `docs/06_quality/AutoSDD_Defect_Log.md`（DEF-87-001 → fixed@improving_88，累積更新）✅
4. 框架本體改進：N/A（本輪零碰 AISLDC_SDD 框架本體，免 Copy-on-Evolve，維持 v0.27）✅

## §8 本輪遺留候選 / 下輪輸入（improving_89）
- **DEF-87-002（P3，生產 logger cp950 console ✓ 崩潰）**：本輪未取（非致命，utf-8 檔案 log 完整）→ 維持 routed，列 improving_89 候選（可考慮 logger console handler 對 Windows cp950 做 ASCII fallback）。
- **真跑加值（選配）**：本輪以 in-process FakeBrain 整合測試確定性證明閘交互修復收斂（機制驗證充分）。可選在 improving_89 用 improving_87 既有 correction_loop 載具（真 Claude + 同掛 regex+evaluator 的 playbook）做端到端真跑，驗 production Kernel 在真模型下亦收斂（品質驗證）——非必要，因 87 已證閉環真跑、本輪只改確定性字串組裝。
- **SD_09 W1 source-sha 閘門**（~6/29 成熟）、**v2.0 格式漂移閘 production 攔阻**：續列候選。
- 下輪柱位對齊提醒：動工前先用根 CLAUDE.md〈三條改進軌道〉表對齊「在哪一柱 A/B/C、下一份檔名」。
