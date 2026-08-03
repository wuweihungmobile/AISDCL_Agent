# AutoSDD_improving_94 — PRD→playbook 專職 Agent + 三層橋接（A/B/C 三軌）

> **本輪柱位**：**三軌齊發**（罕見全幅輪）——
> **A 軌（協作橋接）**：建立「PRD → 專案→目標→任務 playbook.yaml」雙向協作橋，直接服務北極星第 3 點
> （AutoClaude 利用 AISLDC_SDD 做端到端開發）。
> **B 軌（手腳框架 dogfooding）**：新 agent 落 AISDLC_SDD 框架本體，走 Copy-on-Evolve v0.27→v0.28。
> **C 軌（指揮官能力）**：AutoClaude schema additive 擴充（`PlaybookTask.goal_task_id` + `ExecutionItem`
> 可執行欄）+ 新薄 compiler，使既有 three_tier 規劃模型能攤平成可執行 Playbook。
> **下一份**：improving_95。
> **掌舵者裁示（2026-06-27 三問 signoff）**：①playbook 形態＝**SDD 全流程驅動器**；②三層編碼＝
> **重用既有 three_tier_schema + 薄橋接**（而非在 Playbook 另加平行 goals[]，避免兩套三層模型）；
> ③流程＝**直接完整入框架**（Copy-on-Evolve + 三處註冊 + 四件套）。

---

## §1 本輪輸入

### 1.1 本輪緣起（掌舵者需求，非自上輪 W 項繼承）
- 掌舵者直接需求：「在 AISDLC_SDD 建立一個專職 Agent，把 PRD 轉成詳細的 專案→目標→任務 playbook.yaml，
  且這份 playbook 可搭配 AutoClaude + AISDLC_SDD 進行 PRD 完整產品開發。」
- 此為 improving_93 §7 已預告的 A 軌標的（PRD→spec→playbook 缺口），掌舵者裁示本輪即接。

### 1.2 上輪 improving_93 結案狀態
- 已完成 W 項：W-93-1（長 playbook 基準）、W-93-2（A/B 載具 stdev/p50/p95 + --out）、W-93-3（N=3 真跑取證）。
  **未完成 W 項：無**。本輪非延續 93 的載具線，改開 A 軌新標的。
- improving_93 §7 列 94 候選 (a)SD_09 W1 source-sha (b)DEF-19-001 (c)重負載門檻真跑——**本輪掌舵者改派 PRD→playbook
  橋接（更高北極星對齊）**，上述三候選順延 improving_95。

### 1.3 缺陷帳本 open / routed（本輪處置）
- 皆 P3、無 P0/P1 阻斷：DEF-19-001（catch 覆蓋，routed 待後輪）、DEF-62-001 / DEF-01-009（註解滯後 / LOC watch，
  本輪不觸發）、DEF-01-007（cc-switch GUI，本輪 A/B 不依賴，未觸發）、DEF-23-005（RFC 生命週期，routed 待 B 軌）。
- 本輪 B 軌走 Copy-on-Evolve，會觸及「大批新檔入庫潔淨度」（DEF-11-002 紀律）——階段四以 `git add -A -n` dry-run 審查。

### 1.4 本輪新登缺陷
- 階段一/三實作中發現即記入 `docs/06_quality/AutoSDD_Defect_Log.md`（DEF-94-NN），§6 彙整。

---

## §2 階段一實測（Zero-Trust Re-Audit）

> **硬閘**：(a) 基線須 = 上輪 floor（3563 passed）且 0 failed，否則停機禁進階段二/三。
> **判定（2026-06-27 實測）**：(a) 3563 = floor、0 failed → **PASS，准進階段三**。

| 項 | 命令 | 實測結果 |
|----|------|---------|
| (a) AutoClaude 全套 | `python -m pytest tests/ -q` | **3563 passed / 0 failed / 122 skipped**（68.68s）✅ = 上輪 floor |
| (b) 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** ✅ |
| (c) LOC | `python tools/check_loc_budget.py` | **total=19885 / violations=0**（cap 20438）✅ |
| (c') Snapshot | `python tools/snapshot_sync.py --check` | **OK 新鮮** ✅ |
| (d) AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **基線背景實測中**（v0.28 建立後重跑；floor v0.01 1478 + v0.27 1665 + infra 129 = 3272） |
| (e) open 缺陷重現 | — | 皆 P3 watch/routed，本輪未觸發（§1.3） |
| (f) 既有構件存在性核對 | grep + Read | three_tier_schema.py（Project/GoalTask/ExecutionItem）、migrate_yaml_to_db.py、GoalProgressLedger、
  PlaybookCheckpoint.goal_task_id 皆**真實存在且被測**（test_three_tier_schema.py / test_yaml_import.py / test_three_tier_crud_e2e.py）✅ |

### 2.1 階段一關鍵架構偵察結論（zero-trust，§3 設計只錨定此）
1. **AutoClaude 已有完整三層規劃模型**：`autoclaude/models/three_tier_schema.py`（97 行，data tier）
   ——`Project(專案) → GoalTask(目標/任務，可巢狀 depth≤3) → ExecutionItem(原子單元)`；配 PG 三表（alembic 0009）、
   `tools/migrate_yaml_to_db.py`（YAML→DB）、`GoalProgressLedger`（跨 run 進度，鍵 goal_task_id）。
2. **缺口**：此三層模型是「規劃/持久化層」，與「runner 真正執行的扁平 `Playbook`」**未接通**——無「三層 → 可執行
   playbook.yaml」反向橋。`ExecutionItem` 僅有 `exec_id/action/status/estimated_minutes`，**裝不下可執行 task 的
   prompt/regex/evaluator**。
3. **PlaybookTask 無 goal_task_id**（僅 PlaybookCheckpoint 有）——攤平後的 task 目前無法標記所屬目標。
4. **零退化安全裕度**（improving_94 schema 偵察報告）：Playbook 載入走 Pydantic `model_validate`（`extra` 預設
   ignore）；PlaybookCheckpoint 不內嵌 Playbook 本體；playbook.py 81/150、three_tier_schema.py 97/150（皆有裕度）；
   `test_playbook_yaml_backward_compat.py` 機械守舊 YAML 載入——**純 additive Optional 欄位零退化**。

---

## §3 增量設計（階段二）

### §3.0 設計依據實證（zero-trust）
- **形態決策**（掌舵者①）：playbook 為「SDD 全流程驅動器」——goal_task = SDD 階段/產品目標，execution_item =
  驅動 SDD skill（`/sa-analyst`、`/sd-architect`、`/sdd-gate` 等）的步驟，evaluator 檢查該關 SCG 產物。
- **編碼決策**（掌舵者②）：**重用 three_tier_schema**，不在 Playbook 另加平行 goals[]（避免兩套三層模型互相維護、
  概念重複——Rule 8）。三層的「容器」沿用 Project/GoalTask；缺的只是「底層單元裝得下可執行 task」+「攤平後 task
  記得所屬 goal」兩個 additive 欄位 + 一個攤平 compiler。
- **職責分工**（Rule 5）：**agent 做判斷**（PRD→專案/目標/任務結構與每步 prompt）；**compiler 做確定性轉換**
  （三層→扁平 playbook，純函式、無 AI）。禁用 AI 做確定性攤平。

### §3.1 <Architecture_Design_Review>（寫任何 Python 前必輸出）
1. **架構純潔性**：無 God-object。W-94-1＝兩 data model additive 欄（playbook.py / three_tier_schema.py，皆 data tier）；
   W-94-2＝`tools/` 新 compiler（純函式 flatten + Click CLI，**不在 LOC SCAN_ROOT、不在 importlinter 8 contract**，
   比照既有 migrate_yaml_to_db.py）；不碰 `core`/`plugins`/`playbook_runner` thin facade。runner 仍只讀
   `.tasks/.project/.global_goal/.workflow_type`，新 `goal_task_id` 為 task 上純 metadata、執行邏輯零影響。
2. **持久化相容**：`PlaybookTask.goal_task_id` 與 `ExecutionItem` 新欄皆 `Optional[...] = None` → 舊 YAML/checkpoint
   反序列化自動補 None；**不新增 PlaybookCheckpoint 欄位**（goal_task_id 該欄 SD_06 W5 已存在）；不碰 DAL 三後端
   寫入路徑。DAL 零停機相容維持。
3. **安全防護網**：compiler 從三層 YAML 生成 `evaluator_command` —— 屬「從文件生成指令」路徑，**必須套 CONDITIONAL
   等強度消毒**：evaluator 僅允許白名單前綴（`pytest`/`python -m`/SDD skill 既有模板），自由字串拒絕；prompt 為靜態
   文字。新增注入向量攻防測試（W-94-2 單測含惡意 action 注入 case）。
4. **對外 I/O 安全**：本輪**不新增 `ToolInvocationPort` 外呼路徑**（compiler 純本機檔案 I/O；agent 為 Claude persona
   定義檔，不含網路呼叫）。N/A。

### §3.2 W 項（本輪 3 項）

| W 項 | 軌 | 內容 | 檔案 / 介面 delta | LOC 落點 | contract 影響 |
|------|----|------|-------------------|---------|--------------|
| **W-94-1** | C | 兩 data model additive 擴充：①`PlaybookTask.goal_task_id: Optional[str]=None`（攤平後 task 標記所屬目標，連 checkpoint/GoalProgressLedger）；②`ExecutionItem` 加 optional `prompt`/`expected_output_regex`/`evaluator_command`（使三層底層單元裝得下可執行 task） | `autoclaude/models/playbook.py`（81→~84）；`autoclaude/models/three_tier_schema.py`（97→~108） | data ≤150（皆過） | 無（純 additive，無 import 變動） |
| **W-94-2** | C | 新薄 compiler：three_tier YAML（Project/ThreeTierFixture）→ 可執行 `Playbook`。DFS 走 goal_tasks，每 ExecutionItem→1 PlaybookTask（帶 goal_task_id + prompt/regex/evaluator）；project→Playbook.project、description→global_goal。evaluator 白名單消毒 + Click CLI `--source/--out` | 新檔 `tools/three_tier_to_playbook.py`（純函式 + CLI，~180 行）；新測 `tests/tools/test_three_tier_to_playbook.py` | tools/（不掃描） | 無（tools/ 不在 8 contract；import autoclaude.models 合法） |
| **W-94-3** | A/B | Copy-on-Evolve v0.27→v0.28 + 新 agent `sdd-prd-to-playbook-zh.yaml`（讀 PRD→產三層結構 YAML，goal=SDD 階段/目標、execution_item=驅動 SDD skill 的步驟）+ 三處註冊（agent/README.md、AISDLC_SDD_INIT.md **Specialized Agents 清單表列**〔cross-scenario bridge 不綁場景，不進 auto_load_config 場景載入區〕）+ EVOLUTION_LOG + CHANGELOG | `AISDLC_SDD/AISDLC_SDD_v0.28/`（複製自 v0.27）+ 新 agent yaml + 註冊 + EVOLUTION_LOG.md + releases/CHANGELOG.md | 框架資產（非 AutoClaude LOC） | N/A（AISDLC_SDD 側） |

> **新 agent 與既有 `sdd-playbook-compiler`（Compily）清楚區隔（防混淆鐵律）**：
> - **Compily（既有）**＝流程**末端**：吃**已凍結的 TEST-CONTRACT-SPEC**（AC→AT Gherkin），靠 SddToPlaybookAdapter
>   編成「測試→實作」playbook（SCG-4 精神）。
> - **新 agent（本輪）**＝流程**前端**：吃**原始 PRD**，產出**驅動整條 SDD（PRD→FRD→SRD→Contract→實作→RTM）**的
>   三層 playbook。兩者上下游互補、不重疊。

### §3.3 W-94-2 compiler 攤平規則（確定性，無 AI）
```
Project.project_id/name           → Playbook.project（name 優先）
Project.description               → Playbook.global_goal
DFS(goal_tasks, 含 sub_tasks)：
  for each GoalTask gt（depth 順序）:
    for each ExecutionItem ei in gt.execution_items:
      → PlaybookTask(
          step_id = ei.exec_id,
          name    = (gt.title + " / " + ei.action) 經 max_len=80 有界截斷,
          prompt  = ei.prompt or ei.action,          # 無 prompt 時退回 action 描述
          expected_output_regex = ei.expected_output_regex or 預設 DONE keyword 約定,
          evaluator_command     = 白名單消毒(ei.evaluator_command),   # 非白名單→拒絕（raise）
          goal_task_id = gt.goal_task_id,             # ← 三層分組落地處
        )
```
- **有界**：sub_tasks depth≤3 由 three_tier_schema model_validator 既有強制；compiler 不自我放大（純一次走訪）。
- **消毒**：evaluator_command 僅允許白名單前綴；任意 shell 元字元/非白名單 → `ValueError` fail-closed（攻防測試覆蓋）。

### §3.4 RTM 需求列（SCG-5 對應，實測欄階段三/四回填）

| RTM-ID | 需求 | 驗證方式 | 實測（回填） |
|--------|------|---------|------------|
| RTM-94-1 | `PlaybookTask.goal_task_id` additive；舊 playbook YAML（無此欄）仍載入、預設 None | 新單測 + 既有 backward_compat 隨全套 | （回填） |
| RTM-94-2 | `ExecutionItem` 新 optional 欄 additive；既有 sample_goal_tasks.yaml / migrate 工具 round-trip 不破 | 新單測 + test_yaml_import 隨全套 | （回填） |
| RTM-94-3 | compiler 攤平正確：三層→扁平 tasks，step 數 = Σ execution_items、每 task goal_task_id 對應其 GoalTask | 新單測 `test_flatten_*` | （回填） |
| RTM-94-4 | compiler evaluator 白名單消毒：惡意 action/evaluator 注入被拒（fail-closed） | 新單測 `test_compiler_evaluator_sanitize_*`（攻防） | （回填） |
| RTM-94-5 | compiler 產物可被 `Playbook.model_validate` 載入、過 pre_run_validator 煙霧 | 新單測 `test_compiled_playbook_loads_*` | （回填） |
| RTM-94-6 | 新 agent sdd-prd-to-playbook 落 v0.28 + 三處註冊一致；v0.28 = v0.27 + 本輪 delta（Copy-on-Evolve 潔淨） | ci-gate v0.28 + `git add -A -n` dry-run 審 | （回填） |
| RTM-94-7 | 零退化：全套 ≥3563、lint 8 kept、LOC 0、snapshot OK、ci-gate（含 v0.28）全綠 | 階段四矩陣 | （回填，§5） |

### §3.5 SCG 進程（B 軌 dogfooding）
- SCG-0/1＝本計畫書 §1-3（需求+設計凍結）；SCG-2＝§3.2 介面 delta + §3.3 攤平規則；SCG-3＝compiler 無新對外 API
  契約（tools 內部 + 白名單消毒即契約）；SCG-4＝實作 PR（§4）；SCG-5＝§3.4 RTM + §5 驗證矩陣。
- B 軌觸及框架本體 → **Copy-on-Evolve v0.27→v0.28**；本輪**不碰** `_HAPPY_PATH`/`*.tla`/fsm_runtime（僅加 agent 資產
  + 註冊文件）→ 五軌 TLC N/A（階段四以 git diff 鐵證）。

---

## §4 實作與雙重驗證（階段三）— 實測回填

### W-94-1：兩 data model additive 擴充 ✅
- `autoclaude/models/playbook.py`：`PlaybookTask` 加 `goal_task_id: Optional[str]=None`（81→89 行，data tier ≤150）。
- `autoclaude/models/three_tier_schema.py`：`ExecutionItem` 加 optional `prompt`/`expected_output_regex`/
  `evaluator_command`（97→~110 行，data tier ≤150）。
- 向後相容實證：既有 `test_three_tier_schema.py` / `test_yaml_import.py` / `test_playbook_yaml_backward_compat.py`
  / `test_three_tier_crud_e2e.py` 隨全套 **193 passed / 15 skipped**（skip=PG-real）→ 舊 YAML/checkpoint 零破。

### W-94-2：three_tier→Playbook 薄 compiler ✅
- 新檔 `tools/three_tier_to_playbook.py`（純函式 `flatten_project`/`sanitize_evaluator`/`compile_to_playbook`
  + Click CLI `--source/--out/--project-id/--workflow-type`；tools/ 不在 LOC SCAN_ROOT、不在 importlinter 8 contract）。
- evaluator 三層消毒（對齊 `sdd_to_playbook_adapter._DENY`）：黑名單字元 ⊇ CONDITIONAL + 白名單首 token
  （pytest/python）+ 安全字集；不過即 `CompileError` fail-closed。
- 新測 `tests/tools/test_three_tier_to_playbook.py`：**26 passed**（攤平正確/巢狀 goal_task_id 下傳/prompt 退回 action/
  空單元拒絕/round-trip/多 project 選擇/**9 條 evaluator 注入攻防全擋**）。
- 端到端煙霧：demo PRD-project YAML → CLI 產出 playbook.yaml（3 task、goal_task_id 分組 GT-REQ/GT-REQ/GT-IMPL、
  workflow_type=aisdlc_sdd）→ `Playbook.model_validate` 載入成功。

### W-94-3：v0.28 + 新 agent + 註冊 ✅
- `scripts/copy_on_evolve.sh AISDLC_SDD_v0.27 AISDLC_SDD_v0.28`：git archive 純 tracked 匯出 862 檔（結構性排除
  runtime 產物）+ 自動同步版本戳（45 檔→v0.28）+ 重生父層 skills 鏡像（59 檔）+ 補 .gitignore runtime block。
- 新 agent `AISDLC_SDD_v0.28/agent/specialized/sdd-prd-to-playbook-zh.yaml`（Archy，前端橋接；YAML 語法驗證 OK）：
  讀 PRD→產 three_tier 結構（goal_to_scg_skill_map 把目標↔SCG 閘門↔SDD skill 對照骨架內建）；agent 檔頭 +
  INIT 敘述明示與 Compily 分界（前端規劃 vs 末端編譯，防混淆）。
- 三處註冊：`agent/README.md`（樹列 + 清單）、`AISDLC_SDD_INIT.md`（Specialized 19→20、+2 橋接敘述、auto_load_config 表列）、
  `EVOLUTION_LOG.md`（v0.27→v0.28 entry）+ `releases/CHANGELOG.md`（[v0.28]）。
- `FRAMEWORK_STATUS.md` 重生且 `--check` 新鮮（版本/計數 SSOT）。

---

## §5 零退化驗證矩陣（階段四）— 實測回填

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 3563 passed / 0 failed | **3593 passed / 0 failed / 122 skipped**（70.90s，修復後最終態）✅（+30＝新 compiler 測；初測 3589，三鏡修復再 +4 攻防/放行 case） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept / 0 broken | **8 kept / 0 broken** ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | **total=19895 / violations=0**（cap 20438）✅（model 加欄仍在 data≤150；compiler 在 tools/ 不掃） |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **OK** ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | not-chaos 全綠 + arch_fitness exit<2（含新 v0.28） | **exit 0；v0.01 1478 + v0.28 1665 + scripts 129 = 3272 passed / 0 failed**；LATEST 切 v0.28、skills SSOT 59 一致、router 覆蓋 OK ✅ |
| DAL 等價 | equivalence | 三後端等價 | **N/A 第二種**：`tests/equivalence/` 隨全套 3589 通過，本輪無新 DAL/checkpoint 改動故無新 round-trip 契約 ✅ |
| 五軌 TLC | `bash scripts/ci-gate.sh --full-tlc` | 五軌 0 violation | **N/A 第一種**：本輪零碰 `*.tla`/FSM/`_HAPPY_PATH`（改動僅 AutoClaude model+tools + v0.28 新增 agent YAML/註冊文件），TLC 不在 not-chaos pytest、需 Java，本輪確未跑（EVOLUTION_LOG 載明逐位元零差異） |
| 入庫潔淨度 | `git add -A -n` dry-run | 無 runtime/stale 產物誤入庫 | **v0.28 863 檔 would-add、零 runtime/stale**（無 build/reports、arch-fitness.json、formal/states、__pycache__、.pyc；git archive 結構性排除）✅（DEF-11-002 紀律） |

---

## §6 多專家 Zero-Trust 審查
（見 `docs/06_quality/AutoSDD_ZeroTrust_Audit_94.md`：Architect / SA-SD / QA 三鏡證據；缺陷帳本誠實性核對。）

---

## §7 結語（階段四回填）
（本輪交付摘要 + 核心價值 + 下一份 improving_95 候選。）
