# AutoSDD_improving_90 — production Kernel self-correction「regex + evaluator 雙閘並存」真模型端到端真跑 + regex 約束保留可觀測性（C 軌）

> **本輪柱位**：**C 軌（指揮官 AutoClaude 自身能力：self-correction loop 真模型收斂驗證 + 可觀測性）**，觸及 A 軌（Brain↔Kernel prompt 餵回語意）。對齊北極星第 1 點——AutoClaude＝以狀態機管理執行流程／重試／錯誤升級的引擎。**88 輪以 in-process FakeBrain 單元測「確定性」證明 `_preserve_output_contract` 收斂；本輪補上「真 Minimax × 真 Claude」端到端真跑的品質證據**，閉合 88 輪 §8 明列的「真跑加值（選配）」候選。
> **下一份**：improving_91。
> **掌舵者裁示**：2026-06-27 三選一裁定本輪標的＝**「真模型端到端真跑驗 production Kernel 收斂」**（AskUserQuestion 紀錄；候選另含 SD_09 W1 source-sha 閘門、缺陷清理批次、DEF-19-001 catch 覆蓋）。
> **框架版**：本輪零碰 AISLDC_SDD 框架本體（生產碼全在 AutoClaude `core/kernel.py` + `tools/` 載具 + 測試 + 新 playbook/config 資料檔）→ 免 Copy-on-Evolve、維持 v0.27。`L_合體=min(A,B,C)=L5` 不變（真跑品質佐證 + observability-only 加固，非成熟度推進）。

---

## §1 本輪輸入（自上輪繼承）

### 1.1 improving_89 結案狀態（RTM 收尾）
- improving_89＝C 軌 production logger Windows cp950 編碼容錯（閉合 DEF-87-002，commit bfd3454）。
- 已完成 W 項：W-89-1（`_EncodingSafeStreamHandler` + 7 測 + MUT-89-1 突變驗牙）。未完成 W 項：無。
- 上輪審計三鏡（Architect / SA-SD / QA）全 OVERALL PASS（P0=0/P1=0）。
- 階段一基線（2026-06-27 實測）：**3526 passed / 0 failed / 122 skipped**。

### 1.2 缺陷帳本 open / routed（本輪處置計畫）
| 缺陷 | 狀態 | 本輪處置 |
|------|------|---------|
| DEF-87-001（self-correction × regex 閘交互 P2，production） | fixed@improving_88（單元測） | **本輪 W-90-1 以真模型真跑補上品質證據（reproduce→pass）；W-90-2 加可觀測 marker** |
| DEF-87-002（生產 logger cp950 console ✓ 崩潰 P3） | fixed@improving_89 | 已閉合 → 不取 |
| DEF-01-007（cc-switch GUI P3） | open | 不涉多後端切換 → 維持 |
| DEF-01-009（sdd_governance_plugin LOC watch P3） | open watch | 零碰該檔 → 維持 |
| DEF-19-001（catch 歸因覆蓋面 P3） | routed 漸進中 | 不涉本輪 scope → 維持 |
| DEF-42-001（test_file_lock Windows flaky P3） | routed | 非本輪回歸 → 維持 |
| DEF-62-001（auto_recovery 註解滯後 P3） | open routed | 不涉本輪 scope → 維持 |

### 1.3 上輪遺留候選處置
- improving_88 §8 backlog 首位＝「真跑加值（選配）：用 improving_87 既有 correction_loop 載具（真 Claude + 同掛 regex+evaluator 的 playbook）做端到端真跑，驗 production Kernel 在真模型下亦收斂」→ **本輪取**（掌舵者裁示）。
- improving_89 §backlog（真模型端到端驗收斂 / SD_09 W1 ~6/29 / DEF-01-009 watch）→ 本輪取「真模型端到端」一項；其餘續列候選。

---

## §2 階段一實測（Zero-Trust Re-Audit，2026-06-27）

> 派 3 個 Explore agent 主樹親跑（非採信文件宣稱），硬閘 PASS 才進階段二。

| 項目 | 命令 | 實測 | 狀態 |
|------|------|------|------|
| (a) AutoClaude 全套 pytest | `python -m pytest tests/ -q` | **3526 passed / 0 failed / 122 skipped**（73.5s，與上輪 floor 完全一致） | ✅ 硬閘 PASS |
| (b) lint-imports | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken（199 files / 502 deps） | ✅ |
| (c) LOC budget | `python tools/check_loc_budget.py` | violations=0（total 19820 / baseline 17032 / cap 20438） | ✅ |
| (d) snapshot | `python tools/snapshot_sync.py --check` | OK（FRESH） | ✅ |
| (e) AISDLC_SDD ci-gate | `bash scripts/ci-gate.sh` | 全綠（v0.01:1478 / v0.27:1665 / scripts:129 passed），arch_fitness fail=0（warn=3 advisory，exit 0） | ✅ |
| (f) 外部依賴形態（本輪涉真實模型後端） | 偵察 brain adapter / config / .env | 真模型端到端＝**真 Minimax Brain（M2.7，`MinimaxBrainAdapter`）指揮 × 真 Claude Code（PtyExecutor，`claude` CLI）執行**；`.env` 已含真實 `MINIMAX_API_KEY`/`BASE_URL`/`MODEL`（不入庫）；`correction_real_config.yaml` 不設 base_url，靠 `.env` 注入（env 優先於 config，main.py:103-107）；87 輪 W-87-2 已驗證此真跑路徑可通 | ✅ 形態確認 |
| (g) 89 輪構件 | grep/開檔/pytest | logger.py `_EncodingSafeStreamHandler`(L7) / tests/test_logger.py（7 測）/ improving_89.md / Audit_89.md 全存在；DEF-87-002 已記 fixed | ✅ 無虛報 |
| (h) DEF-87-001 修復機制複驗 | 開檔 | `core/kernel.py:293-313` `_preserve_output_contract` staticmethod 真實存在；L260 `task.prompt = self._preserve_output_contract(task, c.correction_prompt)` 接線在位 | ✅ 確認待真跑驗 |

### 2.1 接線實測（決定本輪設計的關鍵事實）
- **CORRECTION 套用點**（`core/kernel.py:259-260`）：`if c.correction_prompt: task.prompt = self._preserve_output_contract(task, c.correction_prompt)`。
- **`_preserve_output_contract`**（`core/kernel.py:293-313`，@staticmethod）：`regex = getattr(task, "expected_output_regex", None); if not regex or regex in correction_prompt: return correction_prompt`（零退化/冪等守衛）；否則附加「[硬約束·勿遺漏]…expected_output_regex：{regex}」。**目前實際附加時無任何 log marker（silent）**——載具無法從 log 解析「regex 約束保留路徑是否被觸發」，僅能靠 final_success 隱含推斷。
- **既有 observability-only marker 慣例**（`core/kernel.py:252-258`，improving_71 W-71-2）：CORRECTION marker `=== STATE: CORRECTION | step=%s attempt=%d ===` 為「零行為變更、僅供載具計數」之先例；本輪 W-90-2 新增 regex-preserved marker 沿此慣例。
- **既有真跑載具**（`tools/correction_loop_verify.py`，improving_87）：`parse_correction_evidence(log_text)` 純函式解析 correction_count / final_success / escalated；`run_verification` orchestration 真跑（耗額度）；已有 7 單元測（`tests/tools/test_correction_loop_verify.py`）。
- **既有 smoke playbook**（`scripts/correction_loop_smoke.yaml`，improving_87）：S02 **刻意不設 regex**（87 輪當時 production 尚未修復 DEF-87-001，同掛 regex 會永不收斂）。本輪新建的 regex 版正是要在 88 修復後驗證「雙閘並存」可收斂。
- **base_url 滯後觀察**（非本輪 scope）：`config.yaml` 全域預設 `minimax.base_url=https://api.minimax.io/anthropic` 與 `.env` 的 `https://api.minimax.io/v1/text/chatcompletion_v2` 不一致；真跑走 `correction_real_config.yaml`+`.env`（不碰 config.yaml 預設）故不受影響，但記為觀察候選（見 §8）。

**硬閘 PASS** → 進階段二。

---

## §3 階段二增量設計

### 3.1 本輪 W 項（聚焦 2 項）
| W 項 | 內容 | 柱位 | LOC 落點 | token 成本 |
|------|------|------|---------|-----------|
| **W-90-1** | 新建 `scripts/correction_regex_smoke.yaml`（S02 **同掛 `expected_output_regex` + `evaluator_command`**，首次刻意 stub 失敗）；真 Minimax × 真 Claude 端到端真跑，驗 production Kernel（88 `_preserve_output_contract`）在真模型 CORRECTION 迴圈下使「regex 閘 + evaluator 閘」雙閘並存**收斂成功**（不 escalate）。 | C 軌（A 軌語意） | 純資料檔（yaml，無 LOC tier） | **燒真實 token**（Minimax M2.7 + Claude Code），需掌舵者批准 |
| **W-90-2** | (a) `core/kernel.py` `_preserve_output_contract` 在**實際附加約束時** emit observability-only marker `=== REGEX CONTRACT PRESERVED \| step=X ===`（鏡像 kernel.py:252-258 CORRECTION marker 慣例，零行為變更）；(b) `tools/correction_loop_verify.py` `parse_correction_evidence` 增 `regex_contract_preserved` 證據欄位（純函式）；(c) 對應單元測（合成 log）。 | C 軌 | kernel.py（absolute_limit≤750，+~3 LOC）；correction_loop_verify.py（tool，+~4 LOC） | **零 token**（純確定性 + 單元測） |

### 3.2 介面 delta
- **無對外介面變更**：不改 `IBrain` port、不改 `CorrectionDecision`/`PlaybookTask` 模型、不改 checkpoint 結構、不改 DAL。
- **W-90-2(a) kernel**：`_preserve_output_contract` 內，在「決定附加約束」分支（`regex` 存在且未含）的 return 前，新增一行 `logger.info("=== REGEX CONTRACT PRESERVED | step=%s ===", task.step_id)`。**僅在實際附加時 emit**（零退化分支不 emit）；模組級 `logger` 既有，零新 import。
- **W-90-2(b) 載具**：`parse_correction_evidence` 回傳 dict 新增 key `regex_contract_preserved: int`（marker 出現次數）；新增模組級 `_RE_REGEX_PRESERVED` 編譯 regex。`run_verification` 真跑報告印該欄位。**additive**：既有 3 個 key（correction_count/final_success/escalated）語意與既有 7 單元測位元級不變。
- **W-90-1 playbook**：新資料檔，不影響任何既有契約。

### 3.3 對 `.importlinter` 各 contract 影響分析
| Rule | 影響 |
|------|------|
| 1 Plugins 互不 import | 無（不動 plugins） |
| 2 core(excl. wiring) 不依賴 execution/infra | 無（仅加 logger.info，零新 import） |
| 3 `_runner_internals` 不被 core/plugins import | 無 |
| 4/5 Brain↔Executor 不互 import | 無（不動 adapters） |
| 6 runner/strategy 不 import checkpoint 內部 | 無 |
| 7 plugins 不 import observability helper | 無（kernel 用既有模組級 logger，非 plugin） |
| 8 plugin 不直接 import IKbMetricStore | 無 |
→ **預期 8 kept / 0 broken 不變。**（載具 `tools/` 不在 importlinter scope。）

### 3.4 checkpoint additive 欄位需求
- **無**。本輪零新增持久化欄位；marker 為 log-only、`regex_contract_preserved` 為載具記憶體內解析結果，皆不落 checkpoint。→ DAL 三後端零停機維持、無新 round-trip 契約。

### 3.5 RTM 需求列（驗證對應，§5 階段三/四回填實測）
| RTM-ID | 需求 | 驗證測試/證據（規劃） | token |
|--------|------|----------------------|-------|
| RTM-90-1 | `_preserve_output_contract` 實際附加約束時 emit `REGEX CONTRACT PRESERVED` marker（含 step_id） | `test_preserve_output_contract_emits_marker_when_appended`（caplog 斷言）— 於 `tests/core/test_kernel.py` | 0 |
| RTM-90-2 | 零退化分支（無 regex / 已含 pattern）**不** emit marker | `test_preserve_output_contract_no_marker_when_passthrough`（caplog 斷言無 marker） | 0 |
| RTM-90-3 | `parse_correction_evidence` 正確計數 `regex_contract_preserved` marker | `test_parse_counts_regex_contract_preserved`（合成 log）— 於 `tests/tools/test_correction_loop_verify.py` | 0 |
| RTM-90-4 | 既有 3 證據欄位（correction_count/final_success/escalated）語意不退化 | 既有 7 單元測續綠（位元級不變） | 0 |
| RTM-90-5 | **真模型端到端**：同掛 regex+evaluator 的 S02 首次失敗 → 真 Minimax 回 CORRECTION → 真 Claude 改對 → 最終 final_success=True 且 escalated=False（雙閘並存收斂）；真跑 log 含 ≥1 `REGEX CONTRACT PRESERVED` marker | `python tools/correction_loop_verify.py --config correction_real_config.yaml --playbook scripts/correction_regex_smoke.yaml`（退碼 0） | **真跑燒 token** |
| MUT-90-1 | 受控突變：把 W-90-2(a) marker 行刪除 → RTM-90-1 轉紅（證 marker 測試有牙） | 手動突變 + Edit 還原（禁 git checkout，遵記憶紀律） | 0 |

> **真模型真跑 flaky 控制**：沿用 87 輪 smoke 設計——S02 prompt 明確（stub `return 0` → pytest 三斷言必失敗）+ 修正方向唯一（multiply 應為乘法、pytest 已示期望值）+ `maintain_context=true`（`--continue` 帶失敗脈絡）→ attempt 1 必改對。本輪額外掛 regex 閘（要求輸出含 keyword），88 修復確保 regex 約束在 CORRECTION 後被保留 → 雙閘並存仍收斂。真跑非確定性，若單跑 flaky 以「誠實兩態」如實回報（不重試掩蓋），並輔以 W-90-2 確定性單元測 + 88 既有 MUT-88-1 構成完整證據鏈。

### 3.6 <Architecture_Design_Review>（寫實質 Python 前必輸出）
1. **架構純潔性 / Thin Facade**：是否創 God-object？→ 否。W-90-2(a) 為既有 `_preserve_output_contract` 內加一行 observability log，完全鏡像 kernel.py:252-258 既有 CORRECTION marker 慣例（improving_71 已立先例：Kernel inline observability marker 為既有設計，非走 bus）→ 與既有慣例一致（工程紀律 Rule 11）。是否該走 `bus.emit`？→ 否：observability-only 確定性 log，無業務判定/無外部副作用，路由成新 hook 屬過度設計（Rule 2）。載具 W-90-2(b) 為純函式擴充，零新職責。kernel.py absolute_limit=750，+3 行安全。
2. **持久化相容**：新狀態是否 additive 寫入 PlaybookCheckpoint？→ 本輪零新增持久化欄位（marker 為 log-only、證據欄位為載具記憶體內）。DAL 三後端零停機維持。
3. **安全防護網（CONDITIONAL）**：本輪是否新增「從文件生成指令」路徑？→ 否。W-90-1 playbook 的 `evaluator_command: "pytest calc_test.py -q"` 為靜態固定指令（同既有 smoke），不從文件動態生成 shell；regex 約束僅回填進 prompt **文字**（給 Claude 閱讀，非組裝 shell）→ 不經 CONDITIONAL 指令生成路徑、不弱化三層防禦。
4. **對外 I/O 安全**：本輪是否新增 `ToolInvocationPort` 外呼路徑？→ 否。真跑的 Minimax API 呼叫走既有 `MinimaxClient`（87/88 輪既有路徑），本輪零新增外呼能力。
→ **四項自我驗證全 PASS，准予實作。**

---

## §4 階段三：實作與雙重驗證

> （階段三回填：實作紀錄、開發-編譯-測試循環、MUT-90-1 突變結果、W-90-1 真跑證據）

### 4.1 實作紀錄
- **W-90-2(a) 生產碼**（`autoclaude/core/kernel.py`）：`_preserve_output_contract` 在「實際附加 regex 約束」分支的 return 前新增 `logger.info("=== REGEX CONTRACT PRESERVED | step=%s ===", task.step_id)`（observability-only，鏡像同檔 CORRECTION marker 慣例 improving_71 W-71-2）。**僅附加分支 emit**，零退化 passthrough（無 regex / 已含 pattern）不 emit。零新增 import（模組級 logger 既有，kernel.py:24）。
- **W-90-2(b) 載具**（`tools/correction_loop_verify.py`）：新增模組級 `_RE_REGEX_PRESERVED`；`parse_correction_evidence` 回傳新增 `regex_contract_preserved` key（additive，既有 3 key 語意位元級不變）；`run_verification` 真跑報告印該欄位。
- **W-90-1 資料檔**（`scripts/correction_regex_smoke.yaml`）：S02 同掛 `expected_output_regex: \[MULTIPLY_FIXED\]` + `evaluator_command: pytest`，首次 stub `return 0`（regex 過、evaluator 擋）。
- **測試**：`tests/core/test_kernel.py` 新增 RTM-90-1/2（caplog 斷言 marker emit/passthrough 不 emit）；`tests/tools/test_correction_loop_verify.py` 新增 RTM-90-3（合成 log 計數 + RTM-90-4 既有欄位不退化）。
- **開發-編譯-測試循環**：改 kernel → 立即跑 `-k "PreservesRegex or preserve_output"`（7 passed）；改載具 → 跑 `test_correction_loop_verify.py`（8 passed）→ 全套 3529 passed（無累積開發）。

### 4.2 受控突變結果（MUT-90-1）
- 突變：把 W-90-2(a) marker 行改為 `logger.info("=== MUT-90-1 MUTATED ===")`（破壞 marker 內容）。
- 結果：`test_preserve_output_contract_emits_marker_when_appended`（RTM-90-1）**轉紅**（caplog 找不到 `=== REGEX CONTRACT PRESERVED | step=S02 ===`，captured log 顯示 `=== MUT-90-1 MUTATED ===`）；`test_preserve_output_contract_no_marker_when_passthrough`（RTM-90-2）仍綠（突變字串不含關鍵字，passthrough 判定仍正確）。→ **證 RTM-90-1 確實咬住 marker 內容，測試有牙。**
- 還原：以 Edit 改回（遵記憶〔git-checkout-mutation-revert-hazard〕禁 `git checkout --`）；單一 agent 序列執行，無並行 audit 互踩風險（記憶〔parallel-mutation-audit-collision〕）。還原後相關測試復綠、全套 3529。

### 4.3 W-90-1 真模型端到端真跑證據（2026-06-27 15:32，掌舵者批准「直接真 Minimax × 真 Claude」）
- 命令：`set -a && . ./.env && set +a && python tools/correction_loop_verify.py --config scripts/ab_configs/correction_real_config.yaml --playbook scripts/correction_regex_smoke.yaml`
- 後端：真 Minimax M2.7（`MinimaxBrainAdapter`，base_url=`https://api.minimax.io/v1/text/chatcompletion_v2`）× 真 Claude Code（PtyExecutor，`claude --permission-mode bypassPermissions --continue`）。autoclaude 子程序在臨時 workdir（rmtree 清理）執行 claude；惟其 checkpoint/log/escalation 等 runtime 產物寫入 `AutoClaude/checkpoints/`、`logs/`（**gitignored**，既有 autoclaude 行為，非本輪引入）→ **零污染 git tracked 檔**（git status 僅本輪 4 個改動 + 3 個 untracked 產出），但會寫 gitignored runtime 目錄（見 §4.4 取證教訓）。
- **真跑 log 關鍵證據鏈**（autoclaude.log 摘錄）：
  1. S02 attempt 0：calc.py stub `return 0` → `pytest calc_test.py -q` 失敗（`assert 0 == 12` / `assert 0 == -10`）→ evaluator 閘擋。
  2. `=== STATE: CORRECTION | step=S02 attempt=1 ===`（Brain 真被呼叫）。
  3. **`=== REGEX CONTRACT PRESERVED | step=S02 ===`**（W-90-2(a) marker 在真模型迴圈 emit）。
  4. 餵回 claude 的修正 prompt（log 可見）：真 Minimax 主體談「將 multiply 從 stub 改為 `return a * b`」，**末尾被 Kernel 確定性附加**「[硬約束·勿遺漏] 你的輸出仍必須匹配以下 expected_output_regex（…不可省略）：\[MULTIPLY_FIXED\]」——此約束為 `_preserve_output_contract` 補回（真 Minimax 修正主體未自帶），**直證 DEF-87-001 修復生效**。
  5. S02 attempt 1：`=== STEP_TOKEN_PEAK | step=S02 pct=9.4877 ===`；`pytest calc_test.py -q` `exit=0`（evaluator 過）+ 輸出含 `[MULTIPLY_FIXED]`（regex 過）→ **雙閘並存皆過**。
  6. `Playbook 結束 | KernelResult(success=True, completed_steps=2, total_steps=2, reason='success', escalated=False, peak_token_pct=9.4877)`。
- **載具判定**（退碼 0）：CORRECTION marker=1（RTM-87-1 ✓）/ **REGEX CONTRACT PRESERVED=1（RTM-90-5 ✓）** / final_success=True（RTM-87-3 ✓）/ escalated=False。
- **結論**：production Kernel 在真 Minimax × 真 Claude 端到端，於「step 同掛 regex 閘 + evaluator 閘」下，套用 self-correction 後**保留 regex 輸出契約並雙閘收斂**——88 輪以 FakeBrain 單元測證明的修復，本輪取得真模型品質證據。首跑即綠（無 flaky，未重試）。

### 4.4 取證教訓（stale cache 少報 → DEF-90-001，誠實性紀律）
- **現象**：W-90-2 後首次跑全套得 `3529 passed`；階段四 fresh 重跑穩定 `3535 passed`（差 6 collected）。
- **根因**：MUT-90-1 受控突變留下 `.pytest_cache`（lastfailed/nodeids）異常狀態，使後續全套**少 collect 6 個**——典型「舊 cache 騙過驗證」（對應 AutoClaude CLAUDE.md Nightly 紀律 #7「cache 路徑強制 fresh」）。
- **權威 fresh 取證**（清 `.pytest_cache/.hypothesis/checkpoints/logs` 後）：同 session 環境 **stash HEAD = 3532 passed / 122 skipped**；**本輪 = 3535 passed / 122 skipped**；`--collect-only` diff 精確 3 行（皆本輪 RTM-90-1/2/3 新測）→ **本輪嚴格 +3、0 failed、0 移除**。
- **floor 對齊**：89 輪階段一報 floor=3526（其量測環境，疑亦受 cache/環境差異少報）；本 session fresh 權威基線=3532。本輪 3535 **同時** ≥ 3526（89 floor）且 = 3532+3（同環境 +3）→ 兩種比法皆零退化。
- **教訓入帳**：DEF-90-001（P3 流程/誠實性，fixed@本輪）——突變/驗證前須 fresh cache，引用 pytest 數字前以清 cache 重跑確立真值，禁採信 stale cache 瞬時數。

---

## §5 階段四：零退化驗證矩陣（結構同步 improving_01 §5.3；通過條件以本輪實測為準，floor=improving_89 實測 3526）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套（fresh cache） | `python -m pytest tests/ -q` | ≥ 3526 passed / 0 failed（floor=improving_89 報；新測只增不減） | ✅ **3535 passed / 0 failed / 122 skipped**（fresh）；同環境 stash HEAD=3532 → 本輪嚴格 **+3**（RTM-90-1/2/3），collect-only diff 精確 3 行（見 §4.4） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken | ✅ **8 kept / 0 broken** |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0 | ✅ **violations=0**（total 19821 / baseline 17032 / cap 20438；+1 全在 kernel marker 行） |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | ✅ **OK（FRESH）** |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | N/A①（零碰 AISLDC_SDD/，附 git diff 鐵證；階段一已驗全綠） | ✅ **N/A①**：`git status` 零 AISLDC_SDD/ 改動（本輪改動全在 AutoClaude/ + 根 docs/）；階段一已實測 ci-gate 全綠（v0.01:1478 / v0.27:1665 / scripts:129，arch_fitness fail=0） |
| DAL 等價 | equivalence job | N/A②（`tests/equivalence/` 隨全套 pytest 通過；本輪無新 DAL/checkpoint 改動故無新增 round-trip 契約） | ✅ **N/A②**：`tests/equivalence/` 隨 fresh 全套通過；本輪零 DAL/checkpoint 改動（W-90-2 marker 為 log-only、載具欄位為記憶體內）故無新增 round-trip |
| 五軌 TLC | `bash scripts/ci-gate.sh --full-tlc` | N/A①（零碰 `*.tla`/FSM；TLC 不在 pytest 全套、需 Java；附 git diff 鐵證） | ✅ **N/A①**：git status 零碰 `*.tla`/FSM（本輪改動僅 kernel.py 加一行 observability logger.info + 載具/測試/yaml/docs，未觸 `_HAPPY_PATH`/狀態機） |

---

## §6 多專家 Zero-Trust 審查（主樹派發，禁 worktree——本輪含 untracked 新檔）
三鏡全 **OVERALL PASS（P0=0 / P1=0 / P2=0）**，零修復循環。完整證據見 [AutoSDD_ZeroTrust_Audit_90.md](../06_quality/AutoSDD_ZeroTrust_Audit_90.md)：
- **SA-SD**（唯一跑 pytest 全套鏡）：fresh 全套 **3535/0/122**、`git stash` HEAD=**3532**、嚴格 **+3**（RTM-90-1/2/3）、collect-only diff 精確 3 行、stash pop 確認還原無遺失；§5 N/A①②標註精確有 git 鐵證。
- **Architect**（lint/LOC，不碰 pytest cache）：kernel marker 為一行 observability log（零新 import、僅附加分支 emit、未破 Thin Facade）；lint 8 kept / LOC violations=0 / 零碰 AISLDC_SDD·*.tla；observability 慣例一致（引 improving_71 W-71-2 先例）。
- **QA**（純唯讀）：真跑證據自洽（marker 格式 kernel↔載具逐字對齊）、MUT-90-1 無殘留（git diff + grep）、帳本誠實（DEF-87-001 補/DEF-90-001 新）、計畫書「污染」措辭誠實、規格先行體例符合。
- 分工避互踩：因 DEF-90-001 實證 stale cache 風險，僅 SA-SD 跑全套（清 cache 獨佔），Architect/QA 不碰 pytest cache。

## §7 結案四件套
1. `docs/04_planning/AutoSDD_improving_90.md`（本檔）
2. `docs/06_quality/AutoSDD_ZeroTrust_Audit_90.md`
3. `docs/06_quality/AutoSDD_Defect_Log.md`（DEF-87-001 補真跑品質證據，累積更新）
4. 框架本體改進：N/A（本輪零碰 AISLDC_SDD 框架本體，免 Copy-on-Evolve，維持 v0.27）

## §8 本輪遺留候選 / 下輪輸入（improving_91）
- **base_url 預設滯後（觀察候選）**：`config.yaml` 全域 `minimax.base_url` 為 `/anthropic` 端點，與 `.env` 的 `/v1/text/chatcompletion_v2` 不一致；真跑走 `correction_real_config.yaml`+`.env` 不受影響，但直接用 config.yaml 預設真跑會打錯端點 → 評估是否對齊或文件標註（若本輪真跑揪出實際影響則升缺陷）。
- **SD_09 W1 source-sha 閘門**（~6/29 成熟）：續列候選。
- **DEF-01-009（sdd_governance_plugin LOC watch）**、**DEF-19-001 catch 覆蓋推進**、**DEF-42-001 file_lock flaky 加重試**：續列候選。
- 下輪柱位對齊提醒：動工前先用根 CLAUDE.md〈三條改進軌道〉表對齊「在哪一柱 A/B/C、下一份檔名」。
