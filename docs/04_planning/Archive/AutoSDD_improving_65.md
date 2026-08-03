# AutoSDD_improving_65 — B 軌可解釋性轉向：meta⁸ 可審批儀表板「最後一哩」缺口設計（GAP-Y2，舵手 K=1 signoff 觸達）

> **軌道**：① 整合迭代｜**本輪柱位**：**B 軌（手腳框架 AISLDC_SDD dogfooding／XAI 可解釋性轉向）**｜**下一份**：`AutoSDD_improving_66.md`
> **日期**：2026-06-25｜**驅動器**：`AutoSDD_Iteration_Prompt_Template.md`｜**成熟度量表 SSOT**：`AutoSDD_Maturity_Rubric.md`
> **本輪性質**：**設計輪（藍圖 + GitHub Issue 規格草案，供掌舵者 signoff）**——依範本「🔭 高階方向：可解釋性轉向（XAI Turn）」driver instance 之輸出定義，本輪**不寫 production 程式**、**不 Copy-on-Evolve**（實作待 signoff 後接 v0.26）。
> **疊加視角**：首席 AI 自動化架構師（Karpathy × Anthropic 機制可解釋性 × 高階形式化驗證）——觸發條件成立（本輪觸及 meta⁸ well-founded 終止證書 + 互遞迴呼叫圖 + steersman 渲染合約）。
> **driver instance**：**ACT-162 / R-9.37**（Phase Y 可審批儀表板 runtime 觸達；承 ACT-160 topology view + ACT-161 dashboard renderer 之最後一哩）。
> **框架版本**：n/a（本輪純設計，無 AISLDC_SDD 凍結本體變更）。
> **🔴 人工 signoff 軌跡**：本輪方向經掌舵者 **2 次 AskUserQuestion + 1 次零信任反轉**逐步定錨——①「方向定錨」選「啟動 XAI 視覺化大標的」→ ②（parent 親讀現碼揭露**大標的已在 v0.25 100% 建好**、推翻 greenfield 前提）「重新定錨」選「深挖視覺化真實缺口」→ parent 親查 grep/read 確認唯一未建且不抵觸紅線之缺口＝**GAP-Y2（儀表板 runtime 無觸達路徑）**。

---

## §1 上輪繼承（improving_64 結案 + 缺陷帳本）

- **improving_64**（C 軌 perf 取證載具去環境依賴化）已 commit（`92bf5bc`），RTM R-64-1~7 全 ✅；**本輪階段一已驗其修復在 nightly 生效**：`.perf_history.jsonl` 末筆 06-24（commit 2bc6f43）`decide_correction` p95 **4.0ms**（從 06-23 的 3701ms 巨幅下修），假 BLOCK 已消除。
- **SD_09 W1 launch**：觀察期 #3（drift）/observability 仍未滿 30 天（drift_log 末筆 06-22 count=0 ≈23/30；預估 ~06-29~07-01 成熟），**今天 06-25 W1 launch 仍不可啟動**（時間閘、非寫碼能解）——與 improving_64 §8 預估一致。
- **缺陷帳本 open/routed 項**（本輪處置）：DEF-01-007（cc-switch GUI，本輪不涉多後端）、DEF-01-009（sdd_governance LOC watch，本輪零擴充該檔）、DEF-19-001（catch 漸進 7/39，本輪未動）、DEF-32-002/17-001/37-001/42-001/53-001/62-001/CLDREV-030（皆非本輪 scope，維持 routed/open）。本輪新增 **DEF-65-001**（GAP-Y2，本輪設計、實作待 signoff）。

## §2 階段一零信任重偵察（實測事實，全錨定本輪 tool 輸出）

| 項目 | 實測命令 | 結果 | 硬閘 |
|------|---------|------|------|
| (a) AutoClaude 全套 | `python -m pytest tests/ -q` | **3315 passed / 122 skipped / 0 failed**（67s） | ✅ ＝上輪 floor 3315 |
| (b) 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** | ✅ |
| (c) LOC / snapshot / git | `check_loc_budget` / `snapshot_sync --check` / `git status` | **violations=0（total=18999）/ FRESH / 工作樹乾淨** | ✅ |
| (d) AISLDC_SDD 五軌 TLA+ | `ls formal/*.tla` | 五軌齊（SDD/META/COMPOSITION/OPTIMIZATION/FLEET），本輪零 `*.tla`/`_HAPPY_PATH` 變更 | n/a |
| (e) nightly 觀察期/perf | `.perf_history.jsonl` / `.drift_log_history.jsonl` / `.ac4_history.jsonl` 末筆 | perf decide_correction 06-24 **4.0ms**（DEF-64-001 修復生效）；drift 末筆 06-22 count=0（≈23/30 未滿）；ac4 06-24 p95=45.76（達標） | ✅ |
| (f) 外部工具依賴 | — | 本輪純設計（讀 AISLDC_SDD 現碼），無新外部 CLI/服務依賴 | n/a |

**硬閘結論**：基線零退化、零 failed、不低於上輪（3315 ≥ floor 3315）→ 准予進入後續階段。

### §2.1 🔴 關鍵零信任發現（推翻「XAI 大標的＝greenfield」前提 — zero-trust 雙向紀律，同 improving_64 §2.1 / improving_60 family）

掌舵者首次定錨選「啟動 XAI 視覺化大標的」（為 meta⁸ 良基終止 + 互遞迴呼叫圖開發人類視覺化儀表板）。**parent 親讀 v0.25 現碼證實此 driver instance 已 100% 建好**——整支即 [`recursion_topology_view.py`](../../AISDLC_SDD/AISDLC_SDD_v0.25/tools/fsm_runtime/recursion_topology_view.py)（Phase Y / ACT-160/161 / Rule 9.37），範本列為「設計必整合的前沿思維」每一條皆已落地：

| 範本要求 | 現碼實證（file:line） | 狀態 |
|---------|---------------------|------|
| XAI 第一等公民 + **AST 同構** | PY-1 `to_dict()` 確定性純投影（`recursion_topology_view.py:10,13,205`），不獨立再推導拓樸 | ✅ 已建 |
| **視覺化防偽/對抗（拓樸一致性稽核）** | PY-2 `verify_topology_consistency`（`:691-880`）反解析渲染、獨立重算、fail-closed；**強化到不信任 renderer 自報 budget/cursor/n_total**（`:697-713,769-806`） | ✅ 已建 |
| **確定性觀測（Playwright/ExecutionObservation）** | `GroundingView`+`render_grounding_panel`（`:594-613`），零觀測灰佔位嚴格不 false-green（`_obs_has_signal :472-487`） | ✅ 已建 |
| **防彈渲染器（有界截斷 + 分頁）** | PY-3 `RenderBudget`（node/edge/depth/char clamp，`:62-87`）+ 窗格切片 O(node_budget)（`:236-243`） | ✅ 已建 |
| **認知超載：折疊/最危險路徑標記** | `fold_topology`（W-23-1 鏈塌縮，`:377-461`）+ critical path 🔴 max-fuel（`:287-293`）+ ⛔ fuel 歸零（`:302-313`） | ✅ 已建 |
| **狀態漂移防護（指紋）** | `audit_digest`/`_canonical_graph` 正規化指紋雙證（`:183-191,873-879`） | ✅ 已建 |
| **TLA+ VisualizationBounded** | `formal/META_FSM.tla` + 憲法 **Rule 9.37** + `guard_visualization_bounded`（`meta_halt_monitor.py:1213`） | ✅ 已建 |
| **15 算子極端圖自我驗證** | `tests/test_phase_y.py`（**590 行**） | ✅ 已建 |

**結論**：照字面再造儀表板＝重造輪子（違 Rule 2/3）且是虛報（違 [[no-fabricated-tool-output]]）。範本提的延伸缺口多半**抵觸憲法**：①「四源一致性自動稽核（加 vs FSM-STATE.yaml 交叉核對）」破 **Rule 9.37.4**（視覺化模組 read-only 純觀察者、禁讀寫 FSM-STATE）；②TLA↔Python 同構＝與五軌 TLC 同性質之 by-design 人工同構，非可自動化的新檢查。→ 推翻 greenfield 前提，掌舵者重定錨選「深挖視覺化真實缺口」。

### §2.2 本輪實質 delta（GAP-Y2：唯一未建且不抵觸紅線的真實缺口）

parent grep + read 親查（零信任於自身宣稱，[[no-fabricated-tool-output]]）：

| 查證點 | 命令/檔 | 實證 |
|--------|---------|------|
| 舵手面儀表板誰呼叫 | `grep render_recursion_topology_dashboard` | 定義在 `steersman_renderer.py:890`（標 **K=1 advisory**），**呼叫點僅 `tests/test_phase_y.py:421,423`**——runtime 零 wire |
| 有無人類 CLI 入口 | `grep __main__ recursion_topology_view.py steersman_renderer.py` | **皆無 `__main__`** |
| `render_dashboard_markdown` 非測試呼叫 | `grep` | 僅 `meta_halt_monitor.py:1232`（防偽 guard **內部**自我重算，非給人看） |
| proposed 算子是否持久化 | `operator_recursion_genesis.py:794` | 一輪提案落 `value-dimension-ledger.yaml` 的 `recursion_inventions` 段（raw rank dict，file_lock 保護） |
| genesis 提案路徑是否吐儀表板 | `grep topology\|dashboard\|render operator_recursion_genesis.py` | **零命中**——舵手 K=1 signoff 時只看到原始 rank 鄰接 dict |
| 依賴方向（對抗分離） | `steersman_renderer.py:904` | 只 `import recursion_topology_view`（viz→viz，皆對抗分離乾淨）；generator→viz 為安全方向 |

**GAP-Y2 = GAP-Y1 的「最後一哩」斷裂**：模組 docstring（`recursion_topology_view.py:6-10`）自陳建造動機＝消滅舵手「盲簽」（meta⁸ 停機證書一路 machine-verified、從未 human-auditable）。但渲染器**從未接進真正的 K=1 signoff/ESCALATION 交接流程、也無 CLI**——舵手實際簽核 proposed 互遞迴算子時，打開 `value-dimension-ledger.yaml` 看到的仍是原始 `recursion_inventions`（帶 rank 的鄰接表），**盲簽問題只在測試裡解決了，活迴圈裡沒有**。此為真實、非虛構、且**純讀取不抵觸 read-only/對抗分離**的缺口。

## §3 三軸成熟度現況 + 本輪定位

| 軸 | 現級 | 證據 |
|----|------|------|
| **A 協作自治** | **L5** | improving_60/61 轉譯策略元學習活體化 + weak_regex 第二信號 |
| **B 流程自治** | **L5** | 翻環家族收齊；本輪為**可解釋性轉向設計輪**（XAI Turn），補 Phase Y 可審批性最後一哩 |
| **C 引擎自治** | **L5** | 自演化 wire + 跨 session DAL 元學習；SD_09 W1 待觀察期（~06-29） |

`L_合體 = min(A=L5, B=L5, C=L5) = **L5**`（本輪**維持**——設計輪不改成熟度；GAP-Y2 closure 屬「可審批性最後一哩」加固，不新增自治能力）。

---

## §4 <Architecture_Design_Review>（寫任何實質 Python 前必出——本輪雖為設計輪，仍依範本先出）

### 4.1 架構純潔性
- **不創 God-object**：closure 方案為一支唯讀 CLI（`render_topology_dashboard.py` 或 `steersman_renderer.py` `__main__`），職責單一：讀 ledger 的 proposed 算子 → 過 `guard_visualization_bounded` → 印 `render_recursion_topology_dashboard`。無新類別/業務邏輯。
- **Thin Facade 維持**：n/a（純 AISLDC_SDD 框架側觀察者工具；不觸 AutoClaude kernel/plugins/ports）。
- **複用既有合約**：100% 複用既有 `extract_topology`/`guard_visualization_bounded`/`render_recursion_topology_dashboard`——CLI 僅是「讀檔 + 既有有界渲染管線」的薄殼。

### 4.2 持久化相容
- **零新持久化、零寫入**。CLI 只**讀** `value-dimension-ledger.yaml` 既有 `recursion_inventions` 段（genesis 既已持久化）。**不寫 FSM-STATE、不影響 churn、不影響 meta-loop**（守 Rule 9.37.4 read-only 純觀察者）。

### 4.3 安全防護網
- **無新 shell 指令生成路徑**。CLI 輸入＝ledger 路徑 + 可選 rule_id 篩選（白名單/路徑正規化即可，無 shell=True）；輸出純 Markdown 到 stdout。
- **拓樸防偽不繞過**：CLI 呈現前**必過** `guard_visualization_bounded`（render budget + PY-2 拓樸同構 + 接地 fail-closed），與既有 dashboard 合約一致——CLI 不得提供繞過 guard 的「raw 渲染」開關。

### 4.4 對外 I/O 安全
- **無新增外呼路徑**（CLI 純本機讀檔 + stdout）→ allowlist/SSRF 攻防 n/a。**嚴禁**借 CLI 開 HTTP 外聯做活體 Playwright 軌跡渲染（守 OPEN-Y.x / Rule 9.37）。

### 4.5 設計抉擇記錄（為何 CLI 而非「wire 進 genesis 提案路徑」）
- **為何 CLI（讀 ledger）而非改 `operator_recursion_genesis` 在提案時自動吐 dashboard**：①CLI 讀既有持久化 artifact ＝**純讀取觀察者**，零碰 generator → 完全合 Rule 9.37.4、零污染 genesis 對抗分離與停機證書路徑（Rule 9.35）；②generator→viz 雖為安全方向，但改 frozen body 的 genesis 熱路徑風險/scope 大於薄殼 CLI（Rule 3 surgical）；③舵手的真實需求是「簽核前 on-demand 看這張圖」——CLI `--rule-id RCR-xxx` 正中此需求，且可在任何時點重跑（不綁 genesis 執行當下）。
- **為何不新增 TLA+ 不變量**：closure 完全複用既有 `VisualizationBounded`（Rule 9.37 / META_FSM.tla）——CLI 只是既有 guarded 渲染管線的新「呼叫者」，未改 _HAPPY_PATH/任何 `*.tla`/FSM 狀態 → **免五軌 TLC**（沿 Rule 9.18.1：無 `*.tla` 變更不觸發）。詳見 §8 TLA+ 評估。
- **為何設計輪不直接實作**：①範本 XAI driver instance 輸出定義＝「藍圖 + GitHub Issue 規格草案，供 steersman signoff」（設計先行）；②實作落 frozen body → 須 Copy-on-Evolve v0.26，遞版成本應與掌舵者對 closure 方案（CLI vs wiring）的 signoff 綁定，避免先斬後奏。

---

## §5 增量設計（W 項 / closure 藍圖 / 介面 delta）

> 本輪為**設計輪**，W 項為「設計藍圖」而非「已實作」；實作待 §8 GitHub Issue signoff 後於 improving_66（或 signoff 當輪）落 v0.26。

### W-65-1（藍圖）— 舵手可審批儀表板 CLI（read-only observer）
- **新增**：`AISDLC_SDD_v0.26/tools/fsm_runtime/render_topology_dashboard.py`（或 `steersman_renderer.py` 增 `__main__`）。
- **介面**：`python -m tools.fsm_runtime.render_topology_dashboard [--ledger <path>] [--rule-id RCR-xxx] [--page N]`
  - 讀 `value-dimension-ledger.yaml` 的 `recursion_inventions` 段 → 取目標 proposed 算子的序列化 dict（即 `RecursiveOperator.to_dict()` 等價內容）。
  - `extract_topology(op_dict, budget=render_budget(), page_cursor=N)` → `TopologyView`。
  - **必過** `guard_visualization_bounded(view, op_dict)`（fail-closed：budget 逃逸/拓樸欺騙/零觀測 false-green 任一 → 非零 exit + 不印綠勾）。
  - 過關 → 印 `render_recursion_topology_dashboard(view, capability=...)` 到 stdout。
- **LOC 預算落點**：薄殼 CLI 估 ≤120 行（strategy/tool tier ≤300，餘裕充足）。
- **紅線守恆**：零寫入（read-only）、不 import 任何 generator（只 import view + steersman_renderer + meta_halt guard）、不提供繞過 guard 開關。

### W-65-2（藍圖）— 回歸鎖測試
- `AISDLC_SDD_v0.26/tools/fsm_runtime/tests/test_phase_y.py`（或新檔）增 CLI 級測試：①正常 proposed 算子 → 印含拓樸/終止/接地三視圖且過 guard；②**受控突變**：餵 budget 逃逸/偽 rank/零觀測 false-green 算子 → CLI 非零 exit + 不印綠勾（證 guard 在 CLI 路徑有效、非空殼）；③ledger 缺段/rule_id 不存在 → fail-loud 明確訊息（非靜默空輸出）。

### 不需動的部分（scope 收斂證據）
- **零碰 generator**（`operator_recursion_genesis.py` 不改）、零碰 FSM-STATE、零 `*.tla`/`_HAPPY_PATH` 變更 → 免五軌 TLC、免 Copy-on-Evolve 之 TLA 連動。
- **零 AutoClaude 變更** → AutoClaude 基線 3315/0 本輪結構性不受影響。

---

## §6 RTM（需求→設計→測試 追溯）

| RTM | 需求 | 設計落點 | 驗證（DoD） | 狀態 |
|-----|------|---------|------------|------|
| R-65-1 | 零信任證實「XAI 大標的已建好」、不虛造重造 | §2.1 | 8 項範本要求逐條對應 v0.25 file:line；改走真實缺口 | ✅（本輪達成） |
| R-65-2 | 定位唯一未建且不抵觸紅線的真實缺口（GAP-Y2） | §2.2 | grep 證 dashboard runtime 零 wire + 無 CLI + genesis 提案路徑零吐圖 | ✅（本輪達成） |
| R-65-3 | closure 方案守 Rule 9.37.4 read-only / 對抗分離 | §4.1-4.5、W-65-1 | CLI 純讀 ledger、零寫 FSM-STATE、不 import generator、必過 guard | ⏳（藍圖，待實作驗） |
| R-65-4 | 複用既有 VisualizationBounded、免新 TLA+ 不變量 | §8 TLA+ 評估 | 無 `*.tla`/_HAPPY_PATH 變更 → 免五軌 TLC | ⏳（藍圖） |
| R-65-5 | 零退化基線（設計輪） | §7 | full pytest 3315/0、lint 8/0、LOC 0、ci-gate exit 0 | ✅（階段一實測；本輪零碼變更維持） |
| R-65-6 | 產出 GitHub Issue 規格草案供 signoff | §8 | 含 `<thinking>`/架構資料流/視覺化策略/TLA+評估/完整 DoD | ✅（本輪達成） |

## §7 零退化驗證矩陣（floor = improving_64 §2 實測；設計輪零碼變更，基線結構性不變）

| 檢查 | 命令 | 通過條件 | 結案實測 |
|------|------|---------|---------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ **3315** passed / 0 failed | **3315 / 122 / 0 failed**（67s，階段一實測）|
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken | **8 kept / 0 broken** |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過 | **violations=0**（total=18999）|
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **OK FRESH** |
| AISLDC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0 | 本輪零 SDD 碼變更（純讀現碼設計）；實作輪 v0.26 時必跑 |
| 五軌 TLC | （僅 FSM 變更時）| **n/a（本輪零 `*.tla`/`_HAPPY_PATH` 變更）** | n/a |

> 本輪為設計輪、零程式碼變更（僅新增 3 件審計/規劃文件）→ 基線數字沿用階段一實測，git status 將僅顯示 `docs/` 三檔。

---

## §8 GitHub Issue 規格草案（driver instance ACT-162 / R-9.37——供 steersman signoff）

> **標題**：`[Phase Y / ACT-162] meta⁸ 可審批儀表板「最後一哩」—— render_recursion_topology_dashboard runtime 觸達（CLI, read-only observer）`
> **標籤**：`xai-turn` `meta8` `rule-9.37` `read-only-observer` `copy-on-evolve:v0.26` `needs-steersman-signoff`

### `<thinking>` 可解釋性轉向深度推理與漏洞挖掘

**核心哲學落地**：再高深的良基終止證書，若舵手在 K=1 signoff 當下看不到，就等於沒有可解釋性——「architecture 失控」不只發生在程式失控，也發生在**人類審批介面缺席**。Phase Y（ACT-160/161）已造好可審批儀表板，卻把它鎖在測試裡：這是「造了儀表卻沒接到駕駛艙」的典型最後一哩失敗。GAP-Y2 的本質是**可達性（reachability）缺口**，非渲染能力缺口。

**漏洞挖掘**：
1. **盲簽復現路徑**：舵手收到 proposed `RCR-xxx` → 開 `value-dimension-ledger.yaml` → 見 `recursion_inventions` 原始鄰接+rank → 無拓樸/critical-path/接地視圖 → 盲簽。CLI 直接斷此鏈。
2. **「假可審批」風險**：若 CLI 提供「跳過 guard 的 raw 渲染」便利開關 → 攻擊者/疲憊舵手可繞過 PY-2 拓樸防偽看到「被簡化的假圖」。**DoD 明令 CLI 無此開關，呈現前必過 `guard_visualization_bounded`**。
3. **資料源信任**：CLI 讀 ledger（genesis 寫出），ledger 內容即 genesis 真相；PY-2 以 `op_dict` 為真相獨立重算，故即便 ledger 被竄改，guard 仍以 op_dict 自洽性把關（攻擊者須同時改 op_dict 真相，但那會被 RecursionClosureBounded 良基證書攔）。
4. **OOM/token 爆炸**：CLI 對 10⁶ 節點 ledger 條目仍走 `extract_topology` 窗格切片 O(node_budget) + 分頁 → 不卡死（VisualizationBounded 既有保障，CLI 不繞過）。

### 儀表板架構與資料流（meta⁸ AST 拓樸特徵 × 沙箱日誌結合）

```
value-dimension-ledger.yaml          operator_recursion_genesis (frozen, 不改)
  └─ recursion_inventions[RCR-xxx]        └─ to_dict(): {ranks, edges, fuel, entry, terminating...}
        │ (read-only)                              │ (PY-1 AST 同構純投影)
        ▼                                          ▼
   [W-65-1 CLI] ── extract_topology(op_dict, budget, page) ──► TopologyView
        │                                          │ (PY-2 拓樸防偽 + PY-3 有界)
        ▼                                          ▼
   guard_visualization_bounded(view, op_dict)  ◄── fail-closed（budget逃逸/拓樸欺騙/零觀測false-green → 非零 exit）
        │ (pass)
        ▼
   render_recursion_topology_dashboard(view)  ──► stdout Markdown
        ├─ ① 拓樸視圖（Mermaid，🔴 critical max-fuel，每邊 Δrank，⛔ fuel 歸零）
        ├─ ② 終止視圖（rank/fuel 階梯，良基測度遞減證明）
        └─ ③ 接地視圖（OQS，零觀測灰佔位嚴格不 false-green）
```

具身接地（ExecutionObservation/沙箱日誌）已由既有 `GroundingView` 投影；CLI 不新增沙箱呼叫，僅渲染 ledger 內若已附帶的 grounding 紀錄，無則灰佔位。

### 視覺化與降維策略（Markdown + Mermaid.js + JSON schema）
- **沿用既有**：`render_mermaid`/`render_termination_ladder`/`render_grounding_panel`/`render_json`（schema_version=1）。CLI 預設輸出組合 Markdown（`render_dashboard_markdown`），可選 `--json` 輸出機讀 JSON。
- **降維**：認知超載交既有 `fold_topology`（`--fold` 開關映 `SDD_VIZ_FOLD`）+ critical path 標記 + 分頁（`--page`）。CLI 零自創降維邏輯。

### TLA+ 不變量擴充評估
- **結論：免新 `VisualizationBounded` 證明，沿用既有框架。** 理由：CLI 是既有 guarded 渲染管線的新**呼叫者**，未改 `_HAPPY_PATH`、未改任何 `*.tla`、未新增/移動 FSM 狀態、未碰 meta-loop。`guard_visualization_bounded` 與 META_FSM.tla `VisualizationBounded` 的 100% 同構合約**原樣適用**於 CLI 路徑（CLI 不過是讓人類觸發同一條 guarded path）。→ 依 Rule 9.18.1「無 `*.tla` 變更不觸發五軌 TLC」，**免五軌 TLC**。

### 完整 DoD（驗收定義）
1. **技術實作**：CLI 落 `v0.26`（Copy-on-Evolve from v0.25）；`python -m tools.fsm_runtime.render_topology_dashboard --rule-id RCR-xxx` 對 ledger 中 proposed 算子印出三視圖 Markdown。
2. **形式化同構證明**：CLI 路徑呈現前必過 `guard_visualization_bounded`；無任何繞過 guard 的開關（程式碼審查 + 測試證）。
3. **拓樸防偽有效（非空殼）**：受控突變測試——餵 budget 逃逸/偽 rank/零觀測 false-green 算子，CLI **非零 exit + 不印綠勾**；還原後正常 exit 0。
4. **read-only / 對抗分離**：`grep` 證 CLI 零寫 FSM-STATE、零 import generator；`git status` 證實作輪僅動 v0.26 預期檔。
5. **Token 預算稽核**：對極端圖（≥256 節點/10⁶ 條目）CLI 輸出 ≤ char_budget、分頁有界、不 OOM/不卡死。
6. **UI/UX 審批標準**：舵手不讀程式碼即可從輸出看出 (a) 哪算子吃最多 fuel（🔴）、(b) 迴圈如何在 rank→0 ∧ fuel→0 被強制打斷（⛔ + break_point 文字）、(c) 具身接地是否退步或灰佔位。
7. **零退化**：v0.26 `ci-gate.sh` exit 0（pytest not-chaos 全綠 + arch_fitness exit<2）；AutoClaude 基線不受影響（零 AutoClaude 變更）。

## §9 缺陷 / 延後

- **DEF-65-001**（P3，GAP-Y2 儀表板 runtime 無觸達）本輪**記入帳本 + 設計藍圖完成**。**🔴 掌舵者已 signoff（2026-06-25）批准 §8 CLI closure 方案**→ 實作放行，落 improving_66（或指定當輪）v0.26 Copy-on-Evolve：W-65-1 唯讀 CLI + W-65-2 受控突變回歸鎖 + 三鏡 zero-trust（免五軌 TLC、複用既有 VisualizationBounded）。
- **SD_09 W1 launch**：觀察期 #3/observability 未滿 30 天（~06-29~07-01 成熟），**時間閘、非延後技術債**；下輪可於成熟後接（含改 token_guard 解 unique-sha 閘）。
- **其餘 open/routed 缺陷**（DEF-01-007/01-009/19-001/32-002/62-001/CLDREV-030…）非本輪 scope，維持原狀態（見 §1）。
