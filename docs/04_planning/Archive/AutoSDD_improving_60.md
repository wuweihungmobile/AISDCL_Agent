# AutoSDD_improving_60 — A 軌協作自治 L4→L5：轉譯策略元學習活體化

> **軌道**：① 整合迭代｜**本輪柱位**：**A 軌（雙向協作橋接）**｜**下一份**：`AutoSDD_improving_61.md`
> **日期**：2026-06-24｜**驅動器**：`AutoSDD_Iteration_Prompt_Template.md`｜**成熟度量表 SSOT**：`AutoSDD_Maturity_Rubric.md`
> **掌舵者裁示**：一輪到位 A→L5 活體化（learning/propose 預設 ON；apply 仍 🔴 人工 signoff）
> **狀態**：階段二設計（計畫 = SCG-0/1 載體；§4 介面 = SCG-2；§5 轉譯契約 = SCG-3）

---

## §1 上輪繼承（improving_59 結案 + 缺陷帳本）

- **improving_59**（B 軌 L4→L5 SLV 自動提議活體化）已 commit（`aa6d15a`），RTM R-59-1~8 全 ✅；最新框架版＝**v0.23**。
- 上輪標示**下輪候選＝A→L5 協作元學習**（improving_59.md:4）——本輪即 improving_60。
- **缺陷帳本 open/routed 項**（本輪處置）：
  - `DEF-01-007`（P3, cc-switch GUI）：維持 open（環境工具缺裝，非倉內可修；不阻擋 A 軌）。
  - `DEF-01-009`（P3, sdd_governance_plugin LOC watch）：維持 open watch（本輪零擴充該檔）。
  - `DEF-17-001`/`DEF-18-001`/`DEF-19-001`（P3, B 軌遙測/catch 歸因）：本輪非 B 軌 scope，維持 routed。
  - `DEF-20-001`（P2）：已 fixed@improving_21（closure_evidence_verify.py），保留紀錄。
  - 本輪新發現缺陷見 `AutoSDD_Defect_Log.md`（行進中即記）。

## §2 階段一零信任重偵察（實測事實，全部錨定本輪 tool 輸出）

| 項目 | 實測命令 | 結果 | 硬閘 |
|------|---------|------|------|
| (a) AutoClaude 全套 | `python -m pytest tests/ -q` | **3265 passed / 122 skipped / 0 failed**（126.92s） | ✅ ＝上輪 floor 3265，零退化 |
| (b) 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken**（192 files / 483 deps） | ✅ |
| (c) AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **exit 0**；v0.01:1478 / v0.23:1656 / scripts:129；全 SSOT/lint 綠 | ✅ |
| (d) 上輪構件存在性 | 讀檔複核 | `sdd_to_playbook_adapter.py`、`goal_decomposer.py` + 對應測試**皆存在** | ✅ |
| (e) 缺陷帳本 open 項 | 讀帳本 | 6 項，皆有正當延後/進行中證據；DEF-59-001/58-002 已 fixed | ✅ |
| (f) 外部工具依賴 | — | 本輪純 AutoClaude 內部碼，無新外部 CLI/服務/訊息平台依賴 | n/a |

**硬閘結論**：基線零退化、零 failed、不低於上輪 → **准予進入階段二**。

## §3 三軸成熟度現況 + 本輪定位

成熟度量表（`AutoSDD_Maturity_Rubric.md`）三軸現級（錨定 improving_59 §2.3 實測，非文件宣稱）：

| 軸 | 現級 | 證據 |
|----|------|------|
| **A 協作自治** | **L4** | improving_57 有界自動凍結 signoff（`goal_decomposer.auto_release`）+ improving_27 RTM 反饋讀回邊（`IRtmFeedbackSource`，**諮詢-only、消費端 flag 預設 OFF**）。**缺**轉譯策略元學習迴圈。 |
| **B 流程自治** | **L5** | improving_59 SLV 自動提議活體化（`_slv_auto_propose_enabled()` 預設 ON）。 |
| **C 引擎自治** | **L5** | 自演化 wire 進 ESCALATION + 跨 session DAL 元學習（`FailureKnowledgeBase`）。 |

`L_合體 = min(A=L4, B=L5, C=L5) = **L4**`，**卡點唯一在 A 軸**。

**本輪定位（A→L5）**：在既有 `IRtmFeedbackSource` 回流邊上，補建**轉譯策略元學習器**——把「執行結果跨 session 回流」從**諮詢**升級為**主動元學習＋自動提議改進**（活體 propose 預設 ON），達成 Rubric L5「有界自演化、人在環上」。達成後 `L_合體 = min(L5,L5,L5) = **L5**`。

> **🔴 誠實邊界（zero-trust 紀律）**：A→L5 的 L5 主張立基於「**主動（預設 ON）＋跨 session 持久化（read_history）＋元學習（頻次推導提議）＋有界硬閘＋人工 signoff 守 apply**」六要件齊備（§4.4 對照 Rubric 逐條）。與 B 軌歷經多輪 opt-in 硬化不同，本機制為**本輪新活化**；故 §7 以「**proposals 純諮詢、絕不自動套用**」保證：無論機制成熟度，轉譯行為零退化（apply 一律人工）。

---

## §4 <Architecture_Design_Review>（寫任何實質 Python 前必出）

### 4.1 架構純潔性
- **不創 God-object**：新增職責拆為三個既有 tier 構件（port / adapter / plugin），各守 LOC 分級。
- **Thin Facade 維持**：`playbook_runner.py` 零改動；學習器為獨立 plugin，走 EventBus phase 訂閱（`POST_RUN`），不侵入 runner。
- **微核心邊界**：plugin 僅 import `core/ports/translation_learning`（port）+ `core/hookspec`，**不 import infra**（sink 經 wiring constructor 注入，型別標 `Any`，鏡像 evolution_plugin 對 `rtm_feedback` 的作法）；plugin 間零互 import（協作走注入 port）。

### 4.2 持久化相容
- **無新 alembic、無 DAL 三後端等價負擔**：沿用 `rtm_sink`/`rtm_feedback` 既有先例——A 軌回流/寫出側是 **File-only**（`FileRtmSink`/`FileRtmFeedbackSource`，無 PG 後端），故本輪 `FileTranslationLearningSink` 亦 File-only，proposals 落 append-only JSONL（`{checkpoint_dir}/translation_learning/PROPOSALS-{project}.jsonl`）。`state_repository` DAL 三後端等價**不受影響**（學習器不碰 state_repository）。
- **跨 session 持久化**：學習基質＝既有 `IRtmFeedbackSource.read_history(project)`（已持久化 `RTM-COVERAGE-HISTORY-*.jsonl`，跨輪）；proposals dedup 經 sink `list_proposals(project)` 讀回既有提議 → **無需新增 `PlaybookCheckpoint` 欄位**（比 F-B1/F-B2 的 additive 欄更輕，零 checkpoint schema 變動）。

### 4.3 安全防護網
- **無新 shell 指令生成路徑**：學習器只讀 history、寫 proposals JSONL（純資料），**不生成 evaluator_command、不改 adapter 轉譯輸出** → CONDITIONAL 三層消毒不需擴充（本輪零新增鏈式攻擊面）。
- **路徑穿越防護**：sink 寫檔 project 基名沿用 `FileRtmSink._sanitize_name` 同模式消毒（防 `../`/絕對路徑挾帶）。
- **自我放大防護**：proposals 不觸發再拆解/再提議（無遞迴）；每 run 提議數有界（§4.5 硬閘）。

### 4.4 對外 I/O 安全
- 本輪**無新增 `ToolInvocationPort` 外呼路徑**（學習器純本地讀寫檔，零網路 I/O）→ allowlist/SSRF 攻防測試 n/a。

### 4.5 L5「有界自演化、人在環上」六要件對照（Rubric §3 L5 判準）
| L5 要件 | 本設計落點 | 守界硬閘 |
|---------|-----------|---------|
| 主動（活體，非 opt-in OFF） | flag `enable_translation_auto_propose` **預設 ON**（opt-out，鏡像 SLV） | env/config 可關，零退化還原 |
| 跨 session 持久化 | `read_history` + proposals JSONL | — |
| 元學習 | 純函數 `select_proposals()` 依跨 run 失敗**頻次**推導候選 | — |
| 範圍·預算有界 | `translation_max_proposals_per_run`（預設 3）+ `min_failing_runs` 門檻（預設 2） | 超限截斷、不重試 |
| 終止守界 | 單次 POST_RUN 一次提議、不遞迴、dedup 去重 | — |
| **人工 signoff 守 apply** | proposals = `status:"proposed"`，**絕不自動套用**改轉譯行為 | 對齊 RTM/SLV/SPEC-PATCH 紅線；apply 由人工 review→手動改 adapter |

---

## §5 增量設計（W 項 / 介面 delta / LOC / 契約影響）= SCG-2/SCG-3

**Brownfield SOP**（B 軌）：本計畫＝SCG-0/1（需求＋設計凍結載體）；§4 介面＝SCG-2（架構凍結）；下表轉譯契約＝SCG-3（契約凍結）。

### W-60-1 — 新 port `core/ports/translation_learning.py`（data tier ≤150）
介面 delta（純 Protocol + dataclass + 純函數，零 IO、零外部依賴；鏡像 `rtm_feedback.py` 結構）：
```python
@dataclass(frozen=True)
class TranslationProposal:
    at_id: str            # 反覆失敗的契約 AT id（轉譯改進候選錨點）
    failing_runs: int     # 跨 session 失敗 run 計數（元學習信號強度）
    total_runs: int       # 觀察窗口內總 run 數
    rationale: str        # 人類可讀提議理由（XAI：為何建議檢視此 AT 轉譯）
    status: str = "proposed"   # 恆 "proposed"；apply 由人工，絕不自動改 verified

@runtime_checkable
class ITranslationLearningSink(Protocol):
    def record_proposal(self, project: str, proposal: TranslationProposal) -> None: ...
    def list_proposals(self, project: str) -> tuple[TranslationProposal, ...]: ...

def select_proposals(
    history: tuple[RtmCoverageReport, ...],   # 既有 rtm_feedback 跨 session 報告
    already_proposed_at_ids: frozenset[str],  # dedup（讀 sink 既有提議）
    *, min_failing_runs: int = 2, max_new: int = 3,
) -> tuple[TranslationProposal, ...]:
    """純元學習：統計各 at_id 跨 run 失敗頻次，達門檻且未提議過者 → 提議（有界 max_new）。"""
```
- **importlinter 影響**：port 僅 import stdlib + 同層 `rtm_sink.RtmCoverageReport`（與 `rtm_feedback.py` 同模式）→ 不破壞 core-purity contract。

### W-60-2 — 新 adapter `infra/adapters/translation_learning_sink.py`（adapter tier ≤400，實際 <120）
- `FileTranslationLearningSink(base_dir)`：`record_proposal` append JSONL；`list_proposals` 讀回（per-line fail-soft）。鏡像 `FileRtmFeedbackSource`。project 基名消毒同 `_sanitize`。
- **importlinter 影響**：infra adapter，無契約限制變動。

### W-60-3 — 新 plugin `plugins/translation_learner_plugin.py`（plugin_entry ≤250）
- `TranslationLearnerPlugin`：`subscribed_phases()=[POST_RUN]`；`on_event` 流程：
  1. flag OFF（opt-out）或非 SDD playbook（`workflow_type` 非 `aisdlc_sdd` / 無 sdd- 步驟）→ **no-op 回 None**（零退化）。
  2. 注入之 `rtm_feedback` 為 None → no-op（fail-soft）。
  3. `history = rtm_feedback.read_history(project)`；`already = {p.at_id for p in sink.list_proposals(project)}`。
  4. `proposals = select_proposals(history, already, max_new=cfg cap)`（純函數）。
  5. 逐筆 `sink.record_proposal(project, p)` + `observability.record_event("sdd.translation_proposal", ...)`（XAI 審計痕）。
  - 全程 fail-soft（任何例外吞掉，諮詢功能不阻斷主流程，鏡像 evolution_plugin）。
  - **絕不**改 adapter 轉譯邏輯、絕不釋出可執行變更（apply=人工）。
- **importlinter 影響**：plugin 僅 import `core/ports/translation_learning` + `core/hookspec`；sink/rtm_feedback 經 wiring 注入（`Any` 型別）→ 不破壞「plugin 不 import infra」「plugin 互不 import」。

### W-60-4 — config + wiring 接線
- `PlaybookConfig`（config.py）additive 兩欄：`enable_translation_auto_propose: bool = True`（**預設 ON＝活體**，opt-out）、`translation_max_proposals_per_run: int = 3`（有界）。
- `wiring.py`：`_build_translation_learning_sink(cfg)` → `FileTranslationLearningSink(f"{cfg.checkpoint_dir}/translation_learning")`；`_build_plugin_set` 新增 `"translation_learner": TranslationLearnerPlugin(...)`；`_REGISTER_ORDER` 插入（置於 `rtm_writeback` 之後、`convergence` 之前，與 A 軌反饋族群相鄰）。
- env 覆寫：`AUTOCLAUDE_ENABLE_TRANSLATION_AUTO_PROPOSE`（opt-out，與 SLV `SDD_ENABLE_SLV_AUTO_PROPOSE` 對稱語意：未設=ON，`0/false/no/off`=OFF）。

### 不需動的部分（scope 收斂證據）
- **SDD 框架本體零改動** → 無 Copy-on-Evolve v0.24、無 `*.tla`/`_HAPPY_PATH` 變更、**無五軌 TLC**。
- `playbook_runner.py`、`sdd_to_playbook_adapter.py`、`goal_decomposer.py` **零改動**（轉譯行為不變＝零退化根保證）。
- 無 alembic、無新 DAL 後端。

---

## §6 RTM（需求→設計→測試 追溯）

| RTM | 需求 | 設計落點 | 驗證（測試）| 狀態 |
|-----|------|---------|-----------|------|
| R-60-1 | A 軌具跨 session 轉譯元學習 | W-60-1 `select_proposals` 純函數 | `test_translation_learning_port.py`（9 測：頻次/門檻/有界/dedup/確定性）| ✅ |
| R-60-2 | 提議活體（預設 ON） | W-60-4 flag 預設 True | `test_translation_learner.py::test_default_on_proposes_from_history` | ✅ |
| R-60-3 | opt-out 零退化 | flag/env OFF → no-op | `::test_config_opt_out_noop`、`::test_env_opt_out_noop` | ✅ |
| R-60-4 | proposals 絕不自動套用（紅線） | plugin 只寫 proposed、不改 adapter | `::test_recorded_proposals_all_proposed_status`（+ SA-SD 鏡 grep 複核）| ✅ |
| R-60-5 | 提議數有界（硬閘） | `max_new` cap | `::test_bounded_cap`、port `::test_bounded_max_new_cap`（QA M2 突變實證）| ✅ |
| R-60-6 | 非 SDD playbook no-op | workflow_type 守門 | `::test_non_sdd_playbook_noop` | ✅ |
| R-60-7 | proposals 跨 session 持久化 + dedup | sink JSONL round-trip | `test_translation_learning_sink.py`（6 測：round-trip/dedup/fail-soft/穿越消毒）| ✅ |
| R-60-8 | 零退化基線 | 全項 §7 矩陣 | pytest **3296/0**（+31）/ lint 8 kept / ci-gate exit 0 | ✅ |
| R-60-9 | A→L5 達成、L_合體=L5 誠實 | §3 + §4.5 六要件對照 | 三鏡 audit **OVERALL PASS（P0=P1=0）**| ✅ |

> **結案實測**（2026-06-24，parent 親跑）：AutoClaude pytest **3296 passed / 122 skipped / 0 failed**（floor 3265，+31）；lint-imports 8 kept / 0 broken；LOC violations=0；snapshot fresh；ci-gate exit 0（v0.01:1478 / v0.23:1656 / scripts:129）。三鏡（Architect/SA-SD/QA）OVERALL PASS、P0=P1=0；三鏡 P3/P2 finding 全修（見 `AutoSDD_ZeroTrust_Audit_60.md`）。**達成 `L_合體=min(A=L5,B=L5,C=L5)=L5`**。

## §7 零退化驗證矩陣（floor = improving_59 §2 實測；通過條件每輪實測，禁寫死）

| 檢查 | 命令 | 通過條件 |
|------|------|---------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ **3265** passed / 0 failed（新測只增不減）|
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過（新 port≤150 / adapter≤400 / plugin≤250）|
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮（新 port/plugin 入 snapshot）|
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0（pytest not-chaos 全綠 + arch_fitness）|
| DAL 等價 | equivalence job | 三後端等價（學習器 File-only，不影響）|
| 五軌 TLC | （僅 FSM 變更時）| **n/a（本輪零 FSM/tla 變更）** |

## §8 缺陷 / 延後

- 行進中框架/工程摩擦發現即記入 `AutoSDD_Defect_Log.md`（DEF-60-NNN）。
- 本輪刻意**不**把 proposals 接成自動 apply（保留人工 signoff＝L5 守界要件，非延後缺陷）。
- weak_regex 事件作為第二信號併入元學習＝後續輪精修候選（本輪以 `failed_at_ids` 跨 session 頻次為主信號，已足證 L5 迴圈）。
