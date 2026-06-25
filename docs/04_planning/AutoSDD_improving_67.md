# AutoSDD_improving_67 — A 軌雙向橋接加固：提議信號分類（XAI 可審批）+ 規格格式版本 fail-closed 閘（防漂移）

> **軌道**：① 整合迭代｜**本輪柱位**：**A 軌（雙向協作橋接 SDD↔Playbook）**｜**下一份**：`AutoSDD_improving_68.md`
> **日期**：2026-06-25｜**驅動器**：`AutoSDD_Iteration_Prompt_Template.md`｜**成熟度量表 SSOT**：`AutoSDD_Maturity_Rubric.md`
> **本輪性質**：A 軌正逆雙向各一增量（純 AutoClaude 側，無 Copy-on-Evolve、無 `*.tla`/TLC、不動 ports）。
> **柱位選擇理由**：上輪 66 為 B 軌第 5 連發；指名候選 SD_09 W1 因觀察期未滿（~06-29 後成熟）本輪做不了（時間閘）；連續多輪未碰 A 軌，平衡三軸（A≤min(B,C) 不變式下 A 仍 L5），掌舵者本輪拍板推 A。
> **driver instance**：本輪不取新 ACT/Rule（純 adapter/port 內部增量，無新形式化合約）。

---

## §1 上輪繼承（improving_66 結案 + 缺陷帳本）

- **improving_66**（B 軌 GAP-Y2 closure 實作輪）已 commit（`2961459`），DEF-65-001 fixed@v0.26，L_合體 維持 L5。
- **缺陷帳本 open/routed 項**（本輪處置）：本輪 A 軌**無新框架缺陷預期**（純 AutoClaude 側增量）。既有 open/routed（DEF-01-007 cc-switch GUI／DEF-01-009／DEF-19-001 catch 漸進／DEF-32-002/17-001/37-001/42-001/53-001/62-001/CLDREV-030 等）皆非本輪 scope，維持原狀態。
- **SD_09 W1 launch**：觀察期 #3/observability 未滿 30 天（~06-29~07-01 成熟），時間閘、非本輪 scope（下輪候選）。

## §2 階段一零信任重偵察（實測事實，全錨定本輪 tool 輸出）

| 項目 | 實測命令 | 結果 | 硬閘 |
|------|---------|------|------|
| (a) AutoClaude 全套 | `python -m pytest tests/ -q` | **3315 passed / 122 skipped / 0 failed**（77.06s） | ✅ ＝上輪 floor 3315 |
| (b) 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken**（195 files / 489 deps） | ✅ |
| (c) LOC / snapshot | `check_loc_budget` / `snapshot_sync --check` | **violations=0（total=18999）/ OK FRESH** | ✅ |
| (d) AISLDC_SDD 閘門（改動前基線） | `bash scripts/ci-gate.sh` | **exit 0**（v0.01:1478 / v0.26 LATEST:1665 / scripts:129） | ✅ |
| (e) 最新框架版 | `ls -d AISDLC_SDD_v0.*` | v0.01~**v0.26** 連續無缺號；LATEST=v0.26 | n/a |
| (f) 外部工具依賴 | — | 本輪純 AutoClaude 側讀檔/記憶體，無新外部 CLI/服務/網路依賴 | n/a |

**硬閘結論**：基線零退化、零 failed、不低於上輪（AutoClaude 3315 ≥ floor 3315；SDD ci-gate exit 0）→ 准予進入後續階段。
**活體旁注（非硬閘範圍）**：今日 nightly `perf stage=1`（dry_run_e2e p95 6.2→12.2ms），屬 SD_09 觀察期 `runs=0/7` 新 baseline 採集中、非鎖定 regression，不在本輪四項硬閘（pytest/lint/loc/ci-gate）內，據實記錄。

### §2.1 零信任複核「Explore 候選 vs 現碼」（推翻假設前先親驗，[[no-fabricated-tool-output]]）

| 查證點 | 命令/檔 | 實證（推翻 Explore 假設） |
|--------|---------|------|
| rtm_sink 是否需新增 | `ls core/ports/rtm_sink.py` | **已存在**（115 行，data tier）——Explore「新增 rtm_sink」假設錯誤 |
| 雙信號是否已分離 | `translation_learning.py:101-119` | `select_proposals` **早已**分 `fail_counter`/`weak_counter`，rationale 已區分——Explore「W-67-1/2 分類/診斷」多為既有功能重包裝 |
| 正向 adapter 版本檢查 | `sdd_to_playbook_adapter.py:112-122` | `load_spec` 有凍結閘（`_assert_frozen`）但**無規格格式版本檢查**——真實缺口 |
| 提議落地審批面 | `translation_learner_plugin.py:118-132` `_emit` | 提議僅帶 fail/weak/total/status，**無結構化分類欄**供舵手一眼分流——真實 XAI 缺口 |

**結論**：捨棄 Explore 冗餘候選，重定為「提議信號分類（補審批面）」+「規格格式版本 fail-closed 閘（補正向防漂移）」兩項真實增量。

## §3 三軸成熟度現況 + 本輪定位

| 軸 | 現級 | 證據 |
|----|------|------|
| **A 協作自治** | **L5** | improving_60/61 轉譯策略元學習活體化 + weak_regex 第二信號；本輪補審批面 + 正向防漂移（L5 加固，不升級） |
| **B 流程自治** | **L5** | 翻環家族 + XAI Turn（improving_62~66） |
| **C 引擎自治** | **L5** | 自演化 wire + 跨 session DAL 元學習；SD_09 W1 待觀察期（~06-29） |

`L_合體 = min(A=L5, B=L5, C=L5) = **L5**`（本輪**維持**——雙向橋接加固屬「審批可解釋性 + 防漂移韌性」，不新增自治能力）。

---

## §4 <Architecture_Design_Review>（寫實質 Python 前必出）

### 4.1 架構純潔性
- **不創 God-object**：W-67-1 純在既有 `select_proposals` 純函數內加分類計算（無新類別，`signal_class` 為既有 `TranslationProposal` 的 additive 欄）；W-67-2 在既有 adapter 加一個防禦方法 `_check_spec_format_version` + 一個與既有 fail-closed 例外同族的 `SpecFormatVersionError`。
- **Thin Facade 維持**：`playbook_runner.py` 零變更（不觸執行流程）。
- **複用既有合約**：W-67-1 複用 `fail_counter`/`weak_counter` 既算值；W-67-2 複用 `load_spec` 既有讀檔流程與 observability 出口。

### 4.2 持久化相容
- **W-67-1**：`signal_class` additive 寫入 `PROPOSALS-*.jsonl`（經 record_proposal 序列化）；舊 jsonl 無此欄 → dataclass 預設 `""` fail-soft 讀回（向後相容）。**不觸 PlaybookCheckpoint、不觸 DAL 三後端**（A 軌提議落 File-only sink，沿 improving_60 先例）。
- **W-67-2**：純讀取 + 例外，**零新持久化**。

### 4.3 安全防護網
- **W-67-2 fail-closed**：未知/不相容規格格式版本 → raise（拒絕編譯為 PlaybookTask），與 §1.3 鏈式攻擊截斷點同向「不信任輸入、預設拒絕」。缺版本欄 → 預設 "1.0"（既有規格皆無此欄，零退化）。
- **無新 shell 指令生成路徑**：兩項皆不觸 `_build_evaluator_cmd` / 白名單模板，CONDITIONAL 三層防禦不變。

### 4.4 對外 I/O 安全
- **無新增 `ToolInvocationPort` 外呼路徑**（兩項皆純本機讀檔/記憶體計算）→ allowlist/SSRF 攻防 n/a。

---

## §5 增量設計（W 項 / 介面 delta / LOC 落點）

### W-67-1 — 逆向橋接：提議信號分類（XAI 可審批性）
- **檔**：`autoclaude/core/ports/translation_learning.py`（data tier，現 136 行）+ `autoclaude/plugins/translation_learner_plugin.py`。
- **介面 delta**：
  - `TranslationProposal` 加 `signal_class: str = ""`（additive，恆由 `select_proposals` 填）。
  - 新增模組級純函數 `_classify_signal(fail_runs, weak_runs, min_failing, min_weak) -> str`：
    - 雙信號皆達門檻 → `"both"`（規格與實作雙弱，最該深查）；
    - 僅失敗達門檻 → `"execution_failure"`；
    - 僅 weak 達門檻 → `"translation_weak"`。
  - `select_proposals` 構造每筆 proposal 時填 `signal_class=_classify_signal(...)`。
  - plugin `_emit` 的 observability payload 加 `"signal_class": proposal.signal_class`。
- **LOC 落點**：data tier，+~10 行（136→~146，仍 <150）；plugin +1 行。
- **紅線守恆**：proposals 恆 `proposed`、apply 仍人工 signoff；`signal_class` 純諮詢分流欄，不改 apply 流程。

### W-67-2 — 正向橋接：規格格式版本 fail-closed 閘（防漂移）
- **檔**：`autoclaude/core/ports/spec_source.py`（contract tier）+ `autoclaude/infra/adapters/sdd_to_playbook_adapter.py`（adapter tier，現 345 行）。
- **介面 delta**：
  - `spec_source.py` 加 `SpecFormatVersionError(RuntimeError)`（與 `SpecNotFrozenError`/`SpecTaintedError` 同 fail-closed 家族；docstring 標明）。
  - `sdd_to_playbook_adapter.py`：
    - 模組常數 `_SUPPORTED_SPEC_FORMAT_VERSIONS = frozenset({"1.0"})` + `_DEFAULT_SPEC_FORMAT_VERSION = "1.0"` + `_SPEC_VERSION_RE`（不分大小寫擷取 `spec-format-version` / `spec_format_version` 後的 `\d+\.\d+`）。
    - 新增 `_check_spec_format_version(text)`：擷取版本；缺欄 → 預設 "1.0"（向後相容）；版本不在支援集 → raise `SpecFormatVersionError`；無論放行與否經 observability 留審計痕（`sdd.spec_format_version`）。
    - `load_spec` 於 `_assert_frozen` 後、build SddSpec 前呼叫 `_check_spec_format_version(text)`。
- **LOC 落點**：adapter +~15 行（345→~360，<400）；port +1 例外類。
- **紅線守恆**：fail-closed（預設拒絕未知）；既有規格（無版本欄）零退化。

### 不需動的部分（scope 收斂證據）
- **零碰 ports 數量/契約**（僅在既有 dataclass 加 additive 欄 + 既有 port 模組加例外類）→ `.importlinter` 8 contract 不受影響（port 仍 stdlib + 同層 dataclass）。
- **零碰 FSM/`*.tla`/`_HAPPY_PATH`/checkpoint/DAL** → 免五軌 TLC、免 DAL 等價連動。
- **零碰 AISLDC_SDD 框架本體** → 免 Copy-on-Evolve（SDD 模板端版本 producer 明確延後 improving_68，理由見 §8）。

---

## §6 RTM（需求→設計→測試 追溯）

| RTM | 需求 | 設計落點 | 驗證（DoD） | 狀態 |
|-----|------|---------|------------|------|
| R-67-1 | 提議落地帶結構化信號分類，舵手可一眼分流（both/execution_failure/translation_weak） | W-67-1 `_classify_signal` + `signal_class` | `test_signal_class_execution_failure_only` / `_translation_weak_only` / `_both_is_deepest_concern`（三類各一） | ✅ |
| R-67-2 | `signal_class` additive、舊 jsonl fail-soft 讀回（向後相容） | W-67-1 dataclass 預設 `""` | `test_signal_class_default_empty_backward_compat` | ✅ |
| R-67-3 | 提議排序確定性（meta-learning 依賴）有測試守護 | W-67-1 既有 sort | `test_proposals_fully_deterministic_across_calls`（折入 Explore W-67-4 關切） | ✅ |
| R-67-4 | plugin 將 signal_class 入 observability 審計痕 | W-67-1 plugin `_emit` | `test_observability_emits_signal_class` | ✅ |
| R-67-5 | 未知規格格式版本 fail-closed 拒絕（防漂移） | W-67-2 `_check_spec_format_version` | `test_unknown_spec_version_fail_closed` + `test_version_audit_event_emitted_on_reject` | ✅ |
| R-67-6 | 缺版本欄向後相容（預設 1.0 放行，既有規格零退化） | W-67-2 預設 | `test_missing_spec_version_defaults_1_0` + `test_default_version_marked_not_declared` | ✅ |
| R-67-7 | 合法版本放行 + observability 留審計痕 | W-67-2 emit | `test_supported_version_accepted` + `test_version_audit_event_emitted_on_accept` | ✅ |
| R-67-8 | 零退化 + 免五軌 TLC（無 `*.tla` 變更） | §7 | ci-gate exit 0、AutoClaude ≥ floor 3315 | ✅ |

## §7 零退化驗證矩陣（floor = improving_67 §2 實測；本輪僅改 4 既有檔 + 2 測試檔）

| 檢查 | 命令 | 通過條件 | 結案實測 |
|------|------|---------|---------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ **3315** passed / 0 failed（新測試只增不減）| **3327 / 122 / 0 failed**（68.10s；floor 3315 + 12 新測試＝5 port+1 plugin+6 adapter，精確對齊）|
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken | **8 kept / 0 broken** |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過（data≤150 / adapter≤400 / contract≤400）| **violations=0**（total=19054；translation_learning 129/150、spec_source 68/400、adapter 286/400）|
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **OK FRESH** |
| AISLDC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0（本輪零 SDD 框架變更，應持平 v0.01:1478/v0.26:1665/scripts:129）| **exit 0**（v0.01:1478 / v0.26:1665 / scripts:129，持平）|
| 五軌 TLC | （僅 FSM 變更時）| **n/a（本輪零 `*.tla`/`_HAPPY_PATH` 變更）** | n/a |

> 本輪程式碼變更面：`translation_learning.py`（+signal_class+_classify_signal）/ `translation_learner_plugin.py`（+emit 欄）/ `spec_source.py`（+SpecFormatVersionError）/ `sdd_to_playbook_adapter.py`（+版本閘）+ 對應測試。**FSM/`*.tla`/checkpoint/DAL/ports 數量零變更**。

---

## §8 缺陷 / 延後

- **延後（justified，非技術債遺失）**：W-67-2 的「**SDD 模板端 `spec-format-version` producer**」（讓未來規格實際宣告版本）需 Copy-on-Evolve 到 `AISDLC_SDD_v0.27/` + 跨 SDD 框架模板協調，超出單輪 scope。本輪只先落**正向 adapter 的 fail-closed 防禦**（對未來不相容規格生效、既有規格零退化）。列 improving_68 B 軌候選。**延後類型＝「需跨專案協調 + 不做本輪有界完成優點」**（符合 [[no-defer-unless-justified]] 兩類正當延後）。
- **SD_09 W1 launch**：觀察期未滿（~06-29~07-01 成熟），時間閘、非延後技術債；下輪 C 軌可於成熟後接。
- **本輪 A 軌無新框架/程式碼缺陷**（純 AutoClaude 側增量，未觸發框架摩擦/文檔不符/hook 誤攔）。
- **新增 DEF-67-001（P3，審查編排流程摩擦，fixed@improving_67）**：三鏡並行派發時「會突變的 QA 鏡」與「唯讀 Architect 鏡」共用主樹致 Architect 首跑撞車假紅（最終裁決正確、零淨影響）；紀律延伸＝含突變鏡之未 commit 審查輪須序列派突變鏡或先 commit 走 worktree（詳見 `AutoSDD_Defect_Log.md` DEF-67-001）。
