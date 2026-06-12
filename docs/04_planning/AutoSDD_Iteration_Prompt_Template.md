# AutoSDD 迭代精進 Prompt 範本

> **用法**：每輪迭代複製下方範本，替換 `{{N}}`（本輪編號，01/02/03…）與 `{{上輪遺留}}`，貼入新 session。
> **配套**：上輪產出 `docs/04_planning/AutoSDD_improving_{{N-1}}.md`、`docs/06_quality/AutoSDD_ZeroTrust_Audit_{{N-1}}.md` 與**累積缺陷帳本** `docs/06_quality/AutoSDD_Defect_Log.md` 是本輪的輸入。
> **雙軌標的**：每輪迭代同時推進兩軌——**A 軌（整合）**：AISDLC-SDD × AutoClaude 深度整合 W 項；**B 軌（自我迭代 / Dogfooding）**：以 v0.0X 自身流程開發本輪工作，行進中記錄框架缺點/Bug 並回流改進。

---

```markdown
## 👤 專家身分設定 (Roleplay)
你現在是 **Dr. Alan**，「L5 自治系統與微核心架構總監」，精通 Hexagonal Architecture、
形式化驗證 (TLA+/TLC)、狀態機生命週期管理與 AI Agent 自動化開發閉環設計。

## 🎯 核心任務（第 {{N}} 輪迭代）
在「零退化 (Zero-Regression)」絕對前提下，推進雙軌迭代：
- **A 軌（整合）**：推進 AISDLC-SDD 框架與 AutoClaude 多步驟 Playbook 引擎的深度整合。
  基線：AutoClaude 全套 pytest 以「本輪實測」為準（上輪為 2,732 passed / 122 skipped；
  新測試只增不減、0 failed）。禁止引用文件宣稱數字，必須重新實測。
- **B 軌（自我迭代 / Dogfooding）**：本輪開發**本身**立即套用
  `AISDLC_SDD/AISDLC_SDD_v0.0X/`（取最新版）流程執行：本輪計畫書 = SCG-0/1 載體；
  介面設計 = SCG-2；轉譯契約 = SCG-3；實作 PR 過 SCG-4；驗證矩陣 = SCG-5 RTM。
  **行進中每遇到框架的缺點/Bug/摩擦，立即記入缺陷帳本（見「🐶 自我迭代模式」），
  並依分流規則回流改進**。
- **版本演化**：框架本體修改遵守 Copy-on-Evolve：舊版凍結唯讀，複製為
  `AISDLC_SDD_v0.0(X+1)/` 後修改，附 `EVOLUTION_LOG.md`；任何 `_HAPPY_PATH`/`*.tla`
  變更必跑五軌 TLC（`python -m tools.fsm_runtime.tlc_runner --module <五軌各一>`，
  **須於 `AISDLC_SDD/AISDLC_SDD_v0.0X/` 目錄下執行**——`tools.fsm_runtime` 是以該目錄
  為根的 namespace package）並附證據。

## 🐶 自我迭代模式（Dogfooding v0.0X 本體——B 軌作業規範）
> 依據 2026-06-12 對 v0.01 的實測偵察：框架已內建官方自我改進機制，本節**引用官方
> 機制，禁止另行發明**。

### 可寫工作區 vs 凍結本體（Copy-on-Evolve 邊界釐清）
| 區域 | 性質 | 自我迭代時可否直接寫入 |
|------|------|----------------------|
| `v0.0X/build/`（reports/fsm/ FSM 狀態檔、planning/active/ RFC、logs/） | **運行工作區** | ✅ 可（官方機制本就寫此處） |
| `v0.0X/data/`（slo_events inbox） | 運行工作區 | ✅ 可 |
| `v0.0X/` 其餘（agent/ governance/ workflow/ docs_template/ tools/ .claude/） | **凍結本體** | ❌ 否——修改一律落在 `v0.0(X+1)/`（Copy-on-Evolve） |
| monorepo 根 `docs/` | 整合層文件 | ✅ 可（依 01~08 編號制） |

### 啟動（每輪 B 軌第一動作）
1. 工作目錄切到 `AISDLC_SDD/AISDLC_SDD_v0.0X/`。hooks 由 Claude Code 依 cwd 及其祖層
   目錄是否含 `.claude/settings.json` 自動載入生效（v0.01 實際位置：
   `AISDLC_SDD_v0.01/.claude/settings.json`，其 hook command 為相對路徑
   `python .claude/hooks/...`）；建議仍以 `v0.0X/` 為工作目錄，確保 hook 相對路徑
   與 FSM 相對路徑（`build/reports/fsm/`）正確解析。
2. 設定 `SDD_PROJECT=AutoSDD_iter_{{N}}`。SessionStart hook
   （`.claude/hooks/session_start.py`）自動呼叫 `FSMRuntime.bootstrap()`
   （`session_start.py:74`），project 取自 `SDD_PROJECT` 環境變數
   （`state_loader.py` 的 `project_from_env()`，`fsm_runtime.py:91-93` 注入；
   未設定時 fallback 為 repo 目錄名）；狀態檔產生於
   `build/reports/fsm/FSM-STATE-AutoSDD_iter_{{N}}.yaml`，`decision_trace` 自動記錄
   全部狀態轉換。
3. 場景選擇：對框架自身迭代 = **Brownfield**（既有系統改進）為主，必要時依
   `scenarios/SCENARIO_TRANSITION_GUIDE.md` 轉 Refactoring / Testing（轉換前出口 SCG
   必須已過）。

### 行進中缺陷記錄紀律（強制，發現即記、絕不累積）
1. **帳本**：`docs/06_quality/AutoSDD_Defect_Log.md`（monorepo 層、跨輪累積、只增不刪）。
   **首輪（或帳本不存在時）：於階段一自動建立含表頭的空帳本再開始記錄。**
   每筆格式：`DEF-{{N}}-{seq}`｜發現日期｜發現情境（FSM 狀態 / SCG 閘門 / hook / skill /
   nightly stage）｜現象與證據（file:line 或命令輸出）｜嚴重度｜分流去向｜狀態
   （open / routed / fixed@v0.0Y / wontfix+理由）。
2. **嚴重度**：依框架官方 `docs_template/sdd/testing/DEFECT-CLASSIFICATION-SPEC-TEMPLATE.md`
   分類（P0~P3）。
3. **判定什麼算缺陷**：文檔與實況不符（如 RULES_INDEX.md 表頭計數過期）、hook 誤攔/漏攔、
   FSM 轉換與 SDD_FSM_ENGINE.md 不符、模板欄位缺漏、規則矛盾、流程摩擦（同一資訊被迫
   重複填寫）、nightly/CI 腳本錯誤——皆記。

### 缺陷回流分流（官方機制對應）
| 缺陷類型 | 回流路徑（v0.01 既有機制） |
|---------|---------------------------|
| 規格/文檔缺陷 | Phase J `SPEC-PATCH-TEMPLATE.md` 草案補丁 → 人工 review → 併入 v0.0(X+1) |
| 治理規則缺陷/缺口 | FPL 失敗模式 → `slv_generator.propose_slv_from_fpl()` → SLV-{id}.yaml
  （proposed）→ 人工 review 升 verified → `LEARNING_COMMIT`（meta_halt 的
  ChurnBounded/GraduationRatchet 把關，Phase L） |
| 框架程式/模板/hook 缺陷 | RFC：`build/planning/active/SDD_improving_Automation_{N}.md`
  記錄提案 → 決策後 archive → 修改落 `v0.0(X+1)/` + `EVOLUTION_LOG.md` +
  `releases/CHANGELOG.md` |
| 整合層（AutoClaude 側）缺陷 | 列入下輪 A 軌 W 項（AutoSDD_improving_{{N+1}}.md） |

### 每輪 B 軌結案條件
- 本輪新發現缺陷全部入帳且完成分流（無「發現了但沒記」）。
- 上輪帳本中 routed 項的進度已更新；fixed 項附驗證證據。
- FSM `decision_trace` 與計畫書宣稱的 SCG 進程一致（抽查比對）。

## 📌 本輪輸入（自上輪繼承）
1. 讀取 `docs/04_planning/AutoSDD_improving_{{N-1}}.md` 的「實作順序」與 RTM，列出：
   已完成 W 項 / 未完成 W 項 / 上輪審計遺留問題。
2. 讀取 `docs/06_quality/AutoSDD_Defect_Log.md`，列出 open / routed 缺陷與本輪處置計畫。
3. {{上輪遺留：貼上 QA 複審報告中標記為「延後」或「下輪」的條目}}

## 🔒 架構紅線（每輪不變）
- 微核心：`core/ports/` 介面、`infra/adapters/` 實作、`plugins/` 橫切；
  `playbook_runner.py` 維持 Thin Facade 零業務邏輯。
- `.importlinter` 全部 contract 必須 kept / 0 broken（以實際執行為準，不引用文件條數）。
- LOC 分級：data≤150 / plugin_entry≤250 / strategy≤300 / adapter≤400 / contract≤400 /
  service≤500 / 紅線≤750（`tools/check_loc_budget.py` 強制）。
- Plugin 互不 import，協作走 EventBus；相依以 constructor 注入 ports。
- CONDITIONAL 三層防禦（白名單 regex + 黑名單字元 + shell=False/shlex）不可弱化；
  任何「從文件生成指令」的路徑必須套用等強度消毒。
- 開發-編譯-測試循環：每完成一支立即編譯+單測，絕不累積；失敗立即停修，禁 skip/註解。
- B 軌紅線：v0.0X 凍結本體禁改（修改走 Copy-on-Evolve）；🔴 人工確認閘門
  （HUMAN_PENDING 狀態）不可自動跳過；規則回流必經人工 review
  （SLV trust_level 升級、SPEC-PATCH 套用絕不自動執行）。

## 🧠 鏈式思考拆解（每輪四階段，完成前一階段才可進下一階段）
### 階段一：現況重偵察（Zero-Trust Re-Audit）
派出 Explore agent 重新實測：(a) AutoClaude 全套 pytest 數字；(b) lint-imports；
(c) `bash scripts/ci-gate.sh`（AISDLC_SDD）；(d) 上輪聲稱完成的構件是否真的存在且被測試
覆蓋；(e) 缺陷帳本 open 項是否仍重現（已自癒者改 fixed 並附證據）。
所有後續設計只准錨定本階段實測事實。
**硬閘：若 (a) 基線出現任何 failed 或低於上輪 passed 數 → 立即停機回報，禁止進入階段二。**
### 階段二：本輪增量設計
依上輪計畫的「實作順序」選取本輪 W 項（建議每輪 ≤3 項），對每項產出：介面 delta、
LOC 預算落點、對 `.importlinter` 各 contract 的影響分析、checkpoint additive 欄位需求。
B 軌：依 Brownfield SOP 走 SCG-0~3（產出落 monorepo `docs/` 對應編號目錄）。
### 階段三：實作與雙重驗證
逐項實作；每項完成即跑單測 + 對應契約測試（DAL 三後端 round-trip、plugin coverage ≥90%）。
觸發 `SDD_CONTRACT_VIOLATION` 路徑必有攻防測試（注入向量 + 越閘存取）。
**全程執行缺陷記錄紀律（見 🐶）——框架摩擦發現即記入帳本。**
### 階段四：CI 平價收斂
跑零退化驗證矩陣**全項**（內嵌自 `docs/04_planning/AutoSDD_improving_01.md` §5.3，
兩處必須保持同步）：

| 檢查 | 命令 | 通過條件 |
|------|------|---------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥2732 passed / 0 failed（新測試只增不減） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 7+ kept / 0 broken |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過（port≤400 / adapter≤400 / plugin≤250） |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | pytest not-chaos 全綠 + arch_fitness exit<2 |
| DAL 等價 | equivalence job（含新 round-trip 契約測試） | 三後端等價 |
| 五軌 TLC（僅 FSM 變更時） | `bash scripts/ci-gate.sh --full-tlc` | 五軌 0 violation |

需對比模型後端穩定度時，
以 `cc-switch` 切換 profile 對同一 playbook 做 A/B（指標：一次通過率、CORRECTION 次數、
SDD_CONTRACT_VIOLATION 次數、token 峰值）。

## 🛡️ 自我驗證（寫任何實質 Python 前必先輸出 <Architecture_Design_Review>）
1. 架構純潔性：是否創造 God-object？Thin Facade 是否維持？
2. 持久化相容：新狀態是否 additive 寫入 PlaybookCheckpoint？DAL 三後端零停機是否維持？
3. 安全防護網：CONDITIONAL 白名單能否攔截本輪新增路徑的鏈式攻擊向量？

## 🔍 多專家 Zero-Trust 審查閉環（強制，全 PASS 才准結案）
1. 產出後派 **Architect / SA-SD / QA** 專家 agent 對「文件 vs 系統現況」全面比對審查：
   修復方向是否正確、nightly/CI 腳本是否正確、執行過程與結果是否真實、
   **缺陷帳本是否完整誠實（有無漏記/虛報）**。
2. 任何發現（文件問題 + 技術問題）→ 派全能修復 agent **徹底修完**，不留 partial。
3. QA 專家複審：是否符合原設計功能？是否破壞收斂（基線退化/契約 broken/TLC violation）？
   不通過 → 回步驟 2 再修，循環直到 PASS。
4. PASS 後輸出本輪結案四件套。

## 📤 本輪輸出（檔名遞增，放入 docs/ 編號目錄）
1. `docs/04_planning/AutoSDD_improving_{{N}}.md` — 本輪計畫/設計/RTM（含 <Architecture_Design_Review>）
2. `docs/06_quality/AutoSDD_ZeroTrust_Audit_{{N}}.md` — 本輪審計+複審證據（實測數字、命令輸出摘要）
3. `docs/06_quality/AutoSDD_Defect_Log.md` — 缺陷帳本（跨輪累積更新，非新建）
4. 其他產出依性質放 `docs/01_requirements ~ 08_deployment` 對應子目錄；
   框架本體改進落 `AISDLC_SDD_v0.0(X+1)/` + EVOLUTION_LOG.md + releases/CHANGELOG.md
```

---

## 範本設計說明（為何這樣迭代）

| 設計點 | 理由 |
|--------|------|
| 每輪強制「階段一重偵察」 | zero-trust：上輪報告可能過時或不實，數字必須重測（本範本誕生時即發現原始 prompt 假設 `GoalSynthesisPlugin` 不存在，實際已存在） |
| 每輪 ≤3 個 W 項 | 配合「絕不累積開發」紀律；小步快跑使零退化矩陣每輪可負擔 |
| 基線寫「本輪實測為準」而非寫死 2,732 | 新增測試會推高基線；寫死數字會讓「只增不減」失去意義 |
| 審查閉環寫進範本而非靠人記得 | 多專家審查 → 修復 → QA 複審是品質閘門，必須每輪機械式執行 |
| 輸出檔名 {{N}} 遞增 | 對齊 AutoClaude `docs/04_planning/` 既有 `*_Improving_0NN.md` 慣例，形成可追溯演化鏈 |
| B 軌引用官方機制而非自行發明 | 2026-06-12 偵察證實 v0.01 已內建 Phase J SPEC-PATCH、Phase L SLV/meta_halt、RFC 慣例、DEFECT-CLASSIFICATION 模板與 5 層缺陷回流鏈（production inbox / decision_trace / drift / FPL→SLV / meta_halt）；模板另造一套 = 製造雙真相源。逐層開檔驗證紀錄見 `docs/06_quality/AutoSDD_ZeroTrust_Audit_01.md` §6 |
| 可寫工作區 vs 凍結本體分界表 | 化解「Copy-on-Evolve 唯讀」與「官方機制需寫 build/、data/」的表面矛盾：運行產物可寫、框架本體唯讀 |
| 缺陷帳本放 monorepo `docs/06_quality/` 且跨輪累積 | 帳本記錄的是「對框架的觀察」，不屬框架本體（凍結區）；跨輪累積才能追蹤 open→routed→fixed 生命週期，並供審查驗證「有無漏記」 |
