# AutoSDD_improving_95 — A 軌：PRD→playbook 橋接「端到端真跑」首證

> **柱**：A 軌（雙向協作橋接 SDD↔AutoClaude）。對齊北極星第 3 點——成為端到端自動化開發 Agent。
> **下一份**：`AutoSDD_improving_96.md`。
> **本輪定位**：improving_94 交付了 PRD→playbook 橋接的**靜態構件**（Archy 前端 agent + `tools/three_tier_to_playbook.py`
> compiler + v0.28），但從未把整條鏈**真正串起來跑一次**。本輪補上這條鏈的「端到端真跑」首證：
> 給一份小型 PRD → Archy 真跑拆解出三層 YAML → compiler 攤平 → AutoClaude 真 Claude token 執行 →
> 取證（逐步驟通過 / token% / goal_task_id 分組 / evaluator 閉環）。
>
> **掌舵者 signoff（2026-06-29）**：四選一裁定「A 軌：橋接端到端真跑」。
>
> **本輪邊界（Rule 2 最小但可用）**：PRD 刻意小型（字串工具庫 strutils，2 功能），使 Archy 拆出的
> execution_item 數有界且**可被機械驗證**——混合「規格步（regex DONE keyword 驗證）」+「自包含 TDD 程式步
> （pytest evaluator 親跑驗證）」，使真跑同時走過 SCG 規格關與 SCG-4 實作關，evaluator 閉環真正收斂。
> 不追求完整 PRD→FRD→SRD→Contract→RTM 全生命週期巨型真跑（不可靠且超 token），只證**橋接鏈本身通**。

---

## §1 本輪輸入（自上輪繼承）

1. **improving_94 結案態**（commit 186894e / 09aac92）：交付 W-94-1（兩 data model additive：`PlaybookTask.goal_task_id`
   + `ExecutionItem.prompt/expected_output_regex/evaluator_command`）、W-94-2（`tools/three_tier_to_playbook.py`
   薄 compiler + 26 攤平/攻防測試）、W-94-3（Copy-on-Evolve v0.28 + Archy agent `sdd-prd-to-playbook-zh.yaml` + 三處註冊）。
   全套 3593 passed / 0 failed / 122 skipped。
   - **94 未竟之處（本輪補）**：橋接只有靜態構件 + 一次 demo 煙霧（compiler 攤平 3 task → `Playbook.model_validate` 載入），
     **PRD→Archy→compiler→AutoClaude 整鏈從未端到端真跑**。bridge workflow 文件
     （`v0.28/workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md`）目前只記載 Compily 末端路徑（凍結 spec→playbook），
     **Archy 前端路徑無 SOP、無真跑證據**。
2. **缺陷帳本**（`docs/06_quality/AutoSDD_Defect_Log.md`）：實測 **0 open / 0 routed-未修**（最近 CLDREV-006/007/008 皆 fixed@v0.19）。
   本輪無繼承缺陷待處理。
3. **上輪遺留候選**（記憶與 93 §7）：SD_09 W1 source-sha、DEF-19-001 catch 覆蓋、重負載長 playbook 撞 80% compact——
   皆非本輪 scope（掌舵者裁 A 軌橋接），滾入 improving_96 候選。

## §2 階段一實測（Zero-Trust Re-Audit，2026-06-29）

派 Explore agent 在 monorepo 實測（命令真跑、非文件宣稱）：

| 項目 | 命令 | 實測 | 通過 |
|------|------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | **3593 passed / 0 failed / 122 skipped**（75.93s） | ✅（= 94 最終態，零退化） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | **total=19895 / violations=0**（cap 20438） | ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | **OK** | ✅ |

**硬閘判定**：基線 = 上輪 floor **3593**，無 failed、無低於上輪 → **通過，准進階段二**。

**外部依賴 invocation 形態（階段一 (f)）**：本輪涉真跑，已確認 `claude` CLI **2.1.144** 認證 OK（PATH CLI、非 GUI）；
真跑路徑沿用 93 既驗之 **Brain off + dummy minimax key + 真 Claude token** 配置（`scripts/ab_configs/ab_pty_config.yaml`：
`enable_kernel_brain=false` → brain=None → dummy key 永不被呼叫；`--permission-mode bypassPermissions` 使 `claude -p` 非互動可寫檔；
`storage.mode=yaml_only` 零 PG 依賴）。`.env` 無 ANTHROPIC_API_KEY 不影響（用本機 `claude login` 認證）。

## §3 本輪增量設計（階段二）

### §3.1 <Architecture_Design_Review>（寫任何 Python 前必輸出）
1. **架構純潔性**：無 God-object。本輪**零碰** `core`/`plugins`/`infra`/`playbook_runner` thin facade、**零碰 autoclaude/ 生產碼**。
   W-95-2 新 harness 落 `tools/`（不在 LOC SCAN_ROOT、不在 importlinter 8 contract，比照既有 `ab_compare_backends.py`/
   `three_tier_to_playbook.py`），僅**複用** W-94-2 compiler（`compile_to_playbook`）+ **subprocess 呼叫生產入口** `python -m autoclaude`
   （最忠實的端到端：走真實 CLI → main.py → Kernel → executor，不重寫測試替身）。harness 不含 AI/業務邏輯，純編排 + 解析取證。
2. **持久化相容**：本輪**不新增 PlaybookCheckpoint 欄位**、不碰 DAL 三後端寫入路徑。`--out` JSON 是 harness 輸出檔（證據），
   非 checkpoint。真跑用 `--fresh` 忽略既有 checkpoint。DAL 零停機相容維持。
3. **安全防護網（CONDITIONAL 等強度）**：compiler 的 evaluator 白名單消毒（`sanitize_evaluator` 三層：黑名單字元 ⊇ CONDITIONAL +
   白名單首 token pytest/python + `python -c` 禁用）在本輪真跑路徑**仍是唯一指令生成關**——Archy 產的 three_tier YAML 經 compiler
   攤平時，任何惡意 evaluator_command 一律 fail-closed 拒絕。harness 不繞過 compiler 自造指令。本輪新增測試覆蓋「Archy 產物經 compiler
   消毒後才進真跑」這條鏈（注入向量隨 W-94-2 既有 9 條攻防測試守住）。
4. **對外 I/O 安全**：本輪**不新增 `ToolInvocationPort` 外呼路徑**。harness 為本機 subprocess（`python -m autoclaude` + `claude` CLI），
   無網路 allowlist 議題。真跑打 Claude 是既有 executor 路徑（PtyExecutor），非新外呼能力。N/A。

### §3.2 W 項（本輪 3 項，A 軌）

| W 項 | 軌 | 內容 | 檔案 / 介面 delta | LOC 落點 | contract 影響 |
|------|----|------|-------------------|---------|--------------|
| **W-95-1** | A | 小型 PRD + **Archy 真跑**拆解 → three_tier plan YAML（committed fixture）。PRD = 字串工具庫 strutils（2 功能 slugify/truncate），刻意小型使拆解有界、execution_item 可機械驗證 | 新 `docs/01_requirements/AutoSDD_improving_95_strutils_prd.md`（PRD）；新 `AutoClaude/scripts/bridge_e2e/strutils_prd_plan.yaml`（Archy 真跑產物，committed fixture） | data（非掃描） | 無 |
| **W-95-2** | A | 端到端 bridge harness：three_tier.yaml →（複用 W-94-2 compiler）→ playbook.yaml →（subprocess `python -m autoclaude` 真跑）→ `--out` JSON 證據（per-step：step_id/goal_task_id/success/evaluator_passed/token_pct；aggregate：pass_rate/steps）。確定性部分（compile→write、證據彙總、stdout 解析）有單測；LLM 真跑不寫死測試 | 新 `AutoClaude/tools/run_bridge_e2e.py`（~180 行，純編排 + Click CLI）；新測 `AutoClaude/tests/tools/test_run_bridge_e2e.py` | tools/（不掃描） | 無（tools/ 不在 8 contract；import autoclaude.models + tools.three_tier_to_playbook 合法） |
| **W-95-3** | A | 本 session 端到端真跑取證：strutils_prd_plan.yaml × harness，真 Claude token（Brain off），`--out` 落 JSON 證據 + 真跑差異報告。誠實標記真跑涵蓋（哪些步成功 / evaluator 是否真閉環 / token% 分佈） | 產物：`docs/03_testing/AutoSDD_improving_95_bridge_e2e_evidence.json` + 報告段（§4.3 / ZeroTrust_Audit_95） | 無（執行+取證） | 無 |

> **與 93 真跑的區隔（防混淆）**：93＝C 軌，比較 pty/sdk **兩後端**在手寫長 playbook 的 per-step token% 分佈（執行器層）。
> 95＝A 軌，證 **PRD→three_tier→compiler→AutoClaude 整條橋接鏈**端到端通（單後端 pty，重點在鏈路串接與 evaluator 閉環，非後端對比）。

### §3.3 端到端鏈與真跑配置（確定性編排）
```
PRD.md
  └─[Archy agent 真跑（W-95-1，一次真 LLM 拆解，產物 committed 使下游可重現）]
      └─→ strutils_prd_plan.yaml（three_tier：Project→GoalTask→ExecutionItem）
          └─[compiler 複用 W-94-2 compile_to_playbook（確定性 + evaluator 白名單消毒）]
              └─→ playbook.yaml（扁平 tasks[]，每 task 帶 goal_task_id）
                  └─[python -m autoclaude playbook.yaml --config ab_pty_config.yaml --fresh（真 Claude token, Brain off）]
                      └─→ KernelResult + checkpoint + per-step token% observability
                          └─[harness 解析 → evidence.json]
```
- **PRD 拆解骨架（Archy 依 goal_to_scg_skill_map）**：
  - `GT-SPEC`（需求/設計凍結，SCG-0~1）：1 execution_item＝產一份精簡 spec（功能契約：slugify/truncate 行為），regex `\[SPEC_DONE\]` 驗證（無 pytest——「無可機械檢查者留空」）。
  - `GT-IMPL`（實作至綠，SCG-4）：3~4 execution_item＝自包含 TDD（先測後實作），每步 `evaluator_command: pytest ...` 親跑驗證。
- **有界**：goal_task depth≤3（three_tier model 既有強制）；總步數 ≤ 6（小型 PRD 刻意控制）。
- **真跑配置**：沿用 `scripts/ab_configs/ab_pty_config.yaml`（Brain off + dummy key + bypassPermissions + yaml_only）。

### §3.4 RTM 需求列（SCG-5 對應，實測欄階段三/四回填）

| RTM-ID | 需求 | 驗證方式 | 實測（回填） |
|--------|------|---------|------------|
| RTM-95-1 | 小型 PRD + Archy 真跑產出合法 three_tier YAML（可被 `load_projects` 載入、depth≤3、每 goal_task ≥1 execution_item） | W-95-1 真跑 + compiler 載入煙霧 | （回填） |
| RTM-95-2 | three_tier plan 經 W-94-2 compiler 攤平為合法 Playbook（step 數 = Σ execution_items、每 task goal_task_id 對應其 GoalTask、evaluator 白名單消毒通過） | 新單測 `test_compile_strutils_plan_*` + harness compile 段 | （回填） |
| RTM-95-3 | harness 確定性部分正確：compile→write playbook、stdout 解析出 per-step 結果、evidence JSON schema 完整可讀回 | 新單測 `test_run_bridge_e2e_*`（mock subprocess / dry-run，不打真 LLM） | （回填） |
| RTM-95-4 | 端到端真跑：strutils 鏈跑通，逐步驟通過率 / evaluator 閉環（pytest 步真綠）/ token% 分佈有量化證據 | W-95-3 真跑 + evidence JSON | （回填，§4.3） |
| RTM-95-5 | 安全：Archy 產物經 compiler evaluator 白名單消毒才進真跑；惡意 evaluator 注入 fail-closed（鏈路測試） | 新單測 `test_bridge_e2e_evaluator_sanitize_chain` + W-94-2 既有 9 攻防 | （回填） |
| RTM-95-6 | 零退化：全套 ≥3593、lint 8 kept、LOC 0、snapshot OK、ci-gate 全綠 | 階段四矩陣 | （回填，§5） |

### §3.5 SCG 進程（B 軌 dogfooding 自身）
- SCG-0/1＝本計畫書 §1-3（需求+設計凍結）；SCG-2＝§3.2 介面 delta + §3.3 鏈路設計；SCG-3＝harness 無新對外 API 契約
  （tools/ 內部 + 複用既有 compiler 白名單即契約）；SCG-4＝實作 PR（§4）；SCG-5＝§3.4 RTM + §5 驗證矩陣。
- 本輪**不碰** `_HAPPY_PATH`/`*.tla`/fsm_runtime、**不碰** AISDLC_SDD 框架本體（Archy agent 已在 v0.28，本輪只「使用」不「修改」）→
  **無 Copy-on-Evolve、五軌 TLC N/A**（階段四以 git diff 鐵證）。bridge workflow 文件補 Archy 前端 SOP 段——**待真跑成功後**評估是否
  值得落 v0.29（若僅文件補述，依 Copy-on-Evolve 須複製新版；本輪傾向**先在 monorepo docs/ 記錄真跑 SOP**，框架本體文件補述列 improving_96 候選，避免為單段文件起整版 v0.29）。

---

## §4 實作與雙重驗證（階段三）— 實測回填

### §4.1 W-95-1：小型 PRD + Archy 真跑 → three_tier plan fixture ✅
- 新 PRD `docs/01_requirements/AutoSDD_improving_95_strutils_prd.md`（strutils 字串工具庫，2 功能 slugify/truncate，
  刻意小型 + 通過標準明確）。
- **Archy 真跑**（2026-06-29，一次真 LLM 拆解，以 Archy persona + three_tier schema 合約派 agent）：產出
  `AutoClaude/scripts/bridge_e2e/strutils_prd_plan.yaml`——**1 GT-SPEC（1 規格步，regex `[SPEC_DONE]`）+ 1 GT-IMPL
  （4 自包含 TDD 步：先測 slugify→實作 slugify→加測 truncate→實作 truncate，2 步帶 `pytest` evaluator）= 5 execution_items**，
  depth 全 1，落在 5~6 界內。
- **RTM-95-1/2 驗證**：`python tools/three_tier_to_playbook.py --source ... --out ...` 攤平成功＝**5 task**，每 task 帶 goal_task_id
  （GT-SPEC×1 / GT-IMPL×4），evaluator 白名單消毒通過（E-IMPL-2/E-IMPL-4＝`pytest test_strutils.py -q`），可被 `Playbook.model_validate` 載入。

### §4.2 W-95-2：端到端 bridge harness `tools/run_bridge_e2e.py` ✅
- 新 `tools/run_bridge_e2e.py`（純編排 + Click CLI，tools/ 不掃描）：`compile_plan`（複用 W-94-2 compiler）→
  `run_autoclaude`（subprocess `python -m autoclaude --config --fresh`，真跑副作用，不在單測覆蓋）→
  `parse_e2e_log`（解析引擎 log：step ✓ / STEP_TOKEN_PEAK / KernelResult，確定性純函式）→
  `build_evidence`（per-step join goal_task_id + aggregate pass_rate/分組，schema `autosdd_bridge_e2e_evidence/v1`）。
  CLI 支援 `--compile-only`（驗鏈路前段不花 token）與真跑兩模式。
- **安全（RTM-95-5）**：evaluator 唯一生成關仍是 compiler 的 `sanitize_evaluator`（三層白名單，fail-closed）；harness 不繞過自造指令。
- **新測 `tests/tools/test_run_bridge_e2e.py`：7 passed**（compile 攤平/goal 分組/可載回、惡意 evaluator fail-closed 鏈路、
  log 解析 step/token/KernelResult、無標記空態、證據 join+aggregate、部分失敗 pass_rate 反映真值）。確定性部分全綠、不打真 LLM。
- compile-only CLI smoke：exit 0。`claude -p` 認證 OK。

### §4.3 W-95-3：本 session 端到端真跑取證 ✅（橋接端到端在 sdk 後端證通）
端到端鏈真跑（2026-06-29，真 Claude token，Brain off）。**兩後端各跑一次**，揭露真實差異：

| 後端 | 步成功 | pass_rate | kernel_success | escalated | peak_token% | 證據 |
|------|--------|-----------|----------------|-----------|-------------|------|
| **sdk** | **5/5** | **1.0** | **True** | False | 3.0 | `docs/03_testing/AutoSDD_improving_95_bridge_e2e_evidence.json` |
| pty | 0/5 | 0.0 | False | True（卡 E-SPEC-1） | 0.0 | `..._evidence_pty.json` |

- **🎯 核心成果（北極星第 3 點首證）**：**PRD → Archy 真跑拆解 → compiler 攤平 → AutoClaude 真跑** 整條橋接鏈在 **sdk 後端端到端跑通**——
  5 步（1 規格步 regex + 4 自包含 TDD 步）全過、`completed_step_ids=['E-SPEC-1','E-IMPL-1','E-IMPL-2','E-IMPL-3','E-IMPL-4']`、
  **evaluator pytest 閉環真綠**（E-IMPL-2/E-IMPL-4 親跑 pytest 通過）。**獨立複跑驗證非空殼**：Claude 在工作目錄真建出 `strutils.py`+`test_strutils.py`，
  parent `python -m pytest test_strutils.py -q` 複跑＝**13 passed**（slugify/truncate 含邊界全綠）。per-step token% sdk 平穩 2-3%（與 93 吻合）。
- **🔴 真實發現（DEF-95-002，pty 後端）**：pty 後端 `--output-format json` 對「寫檔步驟」擷取不可靠（4 次 attempt 全 `輸出無法解析為 JSON → 退回原始輸出`，DEF-81-001 族），
  退回的原始輸出未含完成 keyword `[SPEC_DONE]` → E-SPEC-1 regex 不過 → escalated 整輪停。**值得強調的誠實點：Claude 其實已正確寫出 SPEC.md（4151 bytes）**，
  是「keyword 回顯 + pty json 擷取」雙重脆弱致判定失敗、非實際工作失敗。→ 記 DEF-95-002（P3，routed improving_96：doc 步改用 artifact-existence evaluator 使橋接 backend-robust）。
- **🔴 harness 解析 bug（DEF-95-001，本輪 zero-trust 自揪自修）**：初版 harness per-step `✓` regex 的 `\[([A-Za-z0-9_\-]+)\]` 會誤匹配 log 等級標籤 `[INFO]`，
  非貪婪 gap 跨越吃掉真正的 `[E-SPEC-1] ✓` → sdk 真跑被**誤報 4/5**。經比對 kernel 權威 `completed_step_ids`（5/5）揪出 → **fixed@improving_95**：
  ① gap 改 `[^\[\n]*?`（不跨 `[`）；② success 改以 kernel 權威 `completed_step_ids` 為準（fallback ✓）。回歸鎖入單測（`[INFO]` 前綴 canned log + `"INFO" not in ok_steps` 斷言）。
  修後 sdk 真值＝**5/5**（與 kernel completed_steps=5 一致）。

## §5 零退化驗證矩陣（階段四）— 實測回填

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 3593 passed / 0 failed | **3600 passed / 0 failed / 122 skipped**（78.08s）✅（+7＝新 harness 測；floor 3593 = improving_94） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept / 0 broken | **8 kept / 0 broken** ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | **total=19895 / violations=0**（cap 20438）✅（harness 在 tools/、fixture 在 scripts/、測試在 tests/ 皆不掃描） |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **OK** ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | not-chaos 全綠 | **N/A 第一種**：本輪**零碰** `AISDLC_SDD/`（只「使用」v0.28 Archy agent 讀檔、未修改框架本體），`git status` 鐵證無任何 `AISDLC_SDD/` 變更 → 無 Copy-on-Evolve、ci-gate 不觸發 |
| DAL 等價 | equivalence | 三後端等價 | **N/A 第二種**：`tests/equivalence/` 隨全套 3600 通過，本輪無新 DAL/checkpoint 改動故無新 round-trip 契約 ✅ |
| 五軌 TLC | `bash scripts/ci-gate.sh --full-tlc` | 五軌 0 violation | **N/A 第一種**：本輪零碰 `*.tla`/FSM/`_HAPPY_PATH`（改動僅 AutoClaude tools/+scripts/+tests/ + monorepo docs/），TLC 不在 not-chaos pytest、需 Java，本輪確未跑（`git status` 鐵證零碰觸發路徑） |

> **架構紅線複核**：git diff 證**零碰** `autoclaude/`（core/ports/infra/plugins/playbook_runner thin facade）生產碼 — harness 純落 `tools/`（不在 LOC SCAN_ROOT、不在 importlinter 8 contract，比照 ab_compare_backends.py）。安全：evaluator 唯一生成關仍走 compiler `sanitize_evaluator`（CONDITIONAL 等強度白名單，fail-closed），harness 不繞過。無新 `ToolInvocationPort` 外呼路徑。

## §6 多專家 Zero-Trust 審查
（見 `docs/06_quality/AutoSDD_ZeroTrust_Audit_95.md`：Architect / SA-SD / QA 三鏡證據；缺陷帳本誠實性核對。）

## §7 結語（階段四回填）

**本輪定位**：A 軌（雙向協作橋接）——把 improving_94 留下的「靜態橋接構件」串成**端到端真跑首證**，直接服務北極星第 3 點（成為端到端自動化開發 Agent）。`L_合體=min(A,B,C)=L5` 維持（本輪為能力落地/取證輪、非成熟度推進）。

**核心成果**：**PRD → Archy（真 LLM 拆解）→ three_tier YAML → compiler 攤平 → AutoClaude 真跑** 整條橋接鏈在 **sdk 後端端到端跑通**——
strutils 小型 PRD 經 Archy 拆 5 步（1 規格 + 4 TDD），AutoClaude 真 Claude token 跑完 **5/5 全過**、evaluator pytest 閉環真綠、
獨立複跑 Claude 產出的 strutils 測試 **13 passed**。這是「橋接能跑」從靜態構件首次變成**可運行的事實**。

**三 W 項**：W-95-1（strutils PRD + Archy 真跑 → three_tier plan fixture）；W-95-2（端到端 harness `tools/run_bridge_e2e.py` + 7 單測，
compile→真跑→解析→證據 JSON，安全鏈 fail-closed）；W-95-3（本 session 雙後端真跑取證 + evidence JSON + 報告）。

**本輪缺陷（zero-trust 自揪）**：DEF-95-001（P2，harness per-step `✓` regex 誤匹配 log 等級標籤 `[INFO]` → sdk 真跑誤報 4/5；
比對 kernel 權威 completed_step_ids 揪出 → **fixed@improving_95**：gap 不跨 `[` + 改用權威 completed_step_ids + 回歸鎖測）；
DEF-95-002（P3，pty 後端 `--output-format json` 對寫檔步驟擷取不可靠 → keyword 未擷到致 escalated，Claude 實際已正確寫檔 → **routed improving_96**）。

**零退化**：pytest 3593→**3600**/0/122；lint 8 kept；LOC 0；snapshot OK；ci-gate / 五軌 TLC N/A 第一種（git 證零碰框架/`*.tla`）；DAL N/A 第二種。

**下一份 improving_96 候選**：(a) **DEF-95-002 修**＝Archy 對 doc/spec 步改產 artifact-existence evaluator（如 `python -m ...` 檢查產物存在），
使橋接 backend-robust、不靠 keyword 回顯（需 Copy-on-Evolve v0.28→v0.29 改 Archy agent）；(b) bridge workflow 文件補 Archy 前端 SOP 段（同需 v0.29）；
(c) SD_09 W1 source-sha 觀察期閘門（~6/29 已到期）；(d) DEF-19-001 catch 覆蓋。
