# AutoSDD_improving_61 — A 軌協作自治 L5 加固：weak_regex 第二信號併入轉譯元學習

> **軌道**：① 整合迭代｜**本輪柱位**：**A 軌（雙向協作橋接）**｜**下一份**：`AutoSDD_improving_62.md`
> **日期**：2026-06-24｜**驅動器**：`AutoSDD_Iteration_Prompt_Template.md`｜**成熟度量表 SSOT**：`AutoSDD_Maturity_Rubric.md`
> **本輪定位**：A 軸 L5 **加固**（非升級）——維持 `L_合體=L5`，把轉譯元學習從**單一信號**（執行失敗頻次）升為**雙獨立信號**（＋轉譯保真度弱信號 weak_regex），回應 improving_60 §3「A L5 本輪新活化」誠實邊界
> **狀態**：階段二設計（計畫 = SCG-0/1 載體；§4 介面 = SCG-2；§5 轉譯契約 = SCG-3）

---

## §1 上輪繼承（improving_60 結案 + 缺陷帳本）

- **improving_60**（A 軌 L4→L5 轉譯策略元學習活體化）已 commit（`a56c60d`），RTM R-60-1~9 全 ✅；**首破 `L_合體=min(A=L5,B=L5,C=L5)=L5`**。最新框架版＝**v0.23**（未變）。
- improving_60 §8 明列**後續精修候選＝「weak_regex 事件作為第二信號併入元學習」**——本輪即此項。
- improving_60 §3 誠實標記：A 軸 L5 為**本輪新活化**（單一信號 `failed_at_ids` 頻次），與 B 軌歷經多輪 opt-in 硬化不同。本輪**加固該 L5 主張**：補第二獨立信號使元學習更穩健（不過度依賴單一執行失敗信號），同 B 軌多輪硬化精神。
- **缺陷帳本 open/routed 項**（本輪處置）：
  - `DEF-01-007`（P3, cc-switch GUI）：維持 open（環境工具缺裝，非倉內可修；不阻擋 A 軌）。
  - `DEF-01-009`（P3, sdd_governance_plugin LOC watch）：維持 open watch（本輪零擴充該檔）。
  - `DEF-17-001`/`DEF-18-001`/`DEF-19-001`（P3, B 軌遙測/catch 歸因）：本輪非 B 軌 scope，維持 routed。
  - `DEF-59-001`（P2）：已 fixed@improving_59，保留紀錄。
  - 本輪新發現缺陷見 `AutoSDD_Defect_Log.md`（行進中即記）。

## §2 階段一零信任重偵察（實測事實，全部錨定本輪 tool 輸出）

| 項目 | 實測命令 | 結果 | 硬閘 |
|------|---------|------|------|
| (a) AutoClaude 全套 | `python -m pytest tests/ -q` | **3296 passed / 122 skipped / 0 failed**（129.71s） | ✅ ＝上輪 floor 3296，零退化 |
| (b) 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken**（195 files / 489 deps） | ✅ |
| (c) AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **exit 0**；v0.01:1478 / v0.23:1656 / scripts:129；全 SSOT/lint 綠 | ✅ |
| (d) 上輪構件存在性 | 讀檔複核 | `translation_learning.py`（port）、`translation_learner_plugin.py`、`translation_learning_sink.py` + 對應測試**皆存在** | ✅ |
| (e) 缺陷帳本 open 項 | 讀帳本 | 6 項皆 P3 環境/watch；DEF-59-001 已 fixed；無 open DEF-60 | ✅ |
| (f) 外部工具依賴 | — | 本輪純 AutoClaude 內部碼，無新外部 CLI/服務/訊息平台依賴 | n/a |

**硬閘結論**：基線零退化、零 failed、不低於上輪（3296 ≥ floor 3296）→ **准予進入階段二**。

## §3 三軸成熟度現況 + 本輪定位

成熟度量表三軸現級（錨定 improving_60 §3 + 本輪 §2 實測）：

| 軸 | 現級 | 證據 |
|----|------|------|
| **A 協作自治** | **L5** | improving_60 轉譯策略元學習活體化（`translation_learner` plugin propose 預設 ON）。**本輪加固**：補 weak_regex 第二信號。 |
| **B 流程自治** | **L5** | improving_59 SLV 自動提議活體化（`_slv_auto_propose_enabled()` 預設 ON）。 |
| **C 引擎自治** | **L5** | 自演化 wire 進 ESCALATION + 跨 session DAL 元學習（`FailureKnowledgeBase`）。 |

`L_合體 = min(A=L5, B=L5, C=L5) = **L5**`（本輪**維持**，非升級）。

**本輪定位（A→L5 加固，非升級）**：improving_60 的元學習僅憑單一信號（`failed_at_ids` 跨 session 失敗頻次）。本輪補**第二獨立信號 weak_regex**——轉譯時 Gherkin 無法編出強斷言 regex 而 fallback 標記（`SpecContract.weak_regex`，由 `sdd_to_playbook_adapter._parse_contracts` 既有計算）。此信號與「執行失敗」**正交**：weak_regex 反映**轉譯保真度本身的弱點**（即使該 AT 偶然通過，弱 regex 也可能誤判），是「該檢視轉譯規則」的更早期、更直接信號。雙信號 OR 觸發 → 元學習不再過度依賴單一執行結果，**穩健度提升**（回應 improving_60 §3 誠實邊界）。

> **🔴 誠實邊界（zero-trust 紀律）**：
> 1. **maturity 不變**：本輪是 L5 機制**加固**，`L_合體` 維持 L5，**不宣稱任何升級**。
> 2. **零退化根保證不變**：proposals 仍恆 `status="proposed"`、**絕不自動套用**改轉譯行為（apply=人工 signoff）。weak_regex 信號搭載**既有持久化鏈**（improving_56 `PlaybookTask.spec_digest` 先例：forward adapter 填結構化欄 → writeback 讀回 → RTM-COVERAGE-HISTORY jsonl），轉譯**輸出**（regex / evaluator_cmd / step 序列）byte-identical 不變。
> 3. **無新 sink / 無新 wiring port / 無新 alembic / 無框架本體改動**（免 Copy-on-Evolve v0.24、免五軌 TLC）。

---

## §4 <Architecture_Design_Review>（寫任何實質 Python 前必出）

### 4.1 架構純潔性
- **不創 God-object**：改動全為既有構件之 additive 欄位/參數，無新類別職責膨脹。
- **Thin Facade 維持**：`playbook_runner.py` 零改動。weak_regex 搭載既有 forward/reverse adapter 與 `translation_learner` plugin，皆走既有 EventBus/注入路徑。
- **微核心邊界**：新增欄位皆落 data tier（`PlaybookTask` model / `RtmCoverageReport` / `TranslationProposal` dataclass）；`select_proposals` 仍純函數（stdlib + 同層 dataclass）；plugin 仍僅 import `core.ports.translation_learning` + `core.hookspec`。**零 plugin 互 import、零 plugin import infra**。

### 4.2 持久化相容
- **無新持久化路徑**：weak_regex 信號搭 RTM-COVERAGE-HISTORY jsonl（既有）。`coverage_report_to_doc`/`coverage_report_from_doc` additive 新增 `weak_regex_at_ids`（**舊紀錄無此欄 → 讀回 fail-soft 預設 `()`，向後相容**）。
- **proposals JSONL additive**：`TranslationProposal.weak_runs` additive（預設 0）；sink write/read 採顯式欄 `doc.get("weak_runs", 0)` → **improving_60 既有 proposals 紀錄無此欄亦正確讀回 0**。
- **無新 alembic、無 DAL 三後端等價負擔**：學習器與兩 adapter 皆不碰 `state_repository`。`PlaybookTask.weak_regex` additive `bool=False`（Pydantic model 預設值，舊 playbook 反序列化相容）。

### 4.3 安全防護網
- **無新 shell 指令生成路徑**：weak_regex 為純 bool 信號搭載 + 純資料統計，**不生成 evaluator_command、不改 adapter 轉譯輸出** → CONDITIONAL 三層消毒不需擴充（本輪零新增鏈式攻擊面）。
- **路徑/自我放大防護**：沿用 improving_60——sink 基名消毒不變；proposals 不觸發再拆解/再提議（無遞迴）；每 run 提議數仍有界（§4.5）。

### 4.4 對外 I/O 安全
- 本輪**無新增 `ToolInvocationPort` 外呼路徑**（純本地讀寫，零網路 I/O）→ allowlist/SSRF 攻防測試 n/a。

### 4.5 L5「有界自演化、人在環上」要件維持（加固後仍守界）
| L5 要件 | 加固後落點 | 守界硬閘 |
|---------|-----------|---------|
| 主動（活體） | flag `enable_translation_auto_propose` 仍預設 ON（不變） | env/config 可關，零退化還原 |
| 跨 session 持久化 | `read_history` 報告現多帶 `weak_regex_at_ids`（同 jsonl） | — |
| **元學習（加固）** | `select_proposals` **雙信號**：失敗頻次 OR weak_regex 頻次 | 兩門檻各自獨立（`min_failing_runs` / `min_weak_runs`） |
| 範圍·預算有界 | `max_new` cap 不變（合併雙信號候選後仍截斷） | 超限截斷、不重試 |
| 終止守界 | 單次 POST_RUN 一次提議、不遞迴、dedup（不變） | — |
| **人工 signoff 守 apply** | proposals 恆 `status:"proposed"`（不變） | apply 由人工 review→手動改 adapter |

---

## §5 增量設計（W 項 / 介面 delta / LOC / 契約影響）= SCG-2/SCG-3

**Brownfield SOP**（B 軌）：本計畫＝SCG-0/1；§4 介面＝SCG-2；下列轉譯契約＝SCG-3。

### W-61-1 — weak_regex 信號搭載既有持久化鏈
嚴格沿用 improving_56 W-56-2（`PlaybookTask.spec_digest`）先例：forward adapter 填結構化欄 → reverse adapter 讀回 → 既有 HISTORY jsonl 持久化。

1. **`models/playbook.py`**：`PlaybookTask` additive `weak_regex: bool = False`（鏡像 `spec_digest: Optional[str]`）。
2. **`infra/adapters/sdd_to_playbook_adapter.py compile_tasks`**：建 `PlaybookTask` 時加 `weak_regex=c.weak_regex`（`c` 為 `SpecContract`，欄位既有）。轉譯**輸出語意不變**（僅多搭一個既算好的旗標）。
3. **`core/ports/rtm_sink.py RtmCoverageReport`**：additive `weak_regex_at_ids: tuple[str,...] = field(default=())`。
4. **`infra/adapters/playbook_to_rtm_adapter.py compile_report`**：篩 sdd task 時收集 `task.weak_regex` 為真者之 at_id → 填 `weak_regex_at_ids`（確定性排序）。`render_yaml` additive 輸出該欄（一致性）。
5. **`core/ports/rtm_feedback.py`**：`coverage_report_to_doc` additive `"weak_regex_at_ids"`；`coverage_report_from_doc` 讀回（fail-soft 預設 `()`）。
- **importlinter 影響**：皆同層/既有依賴，**無契約變動**。
- **LOC**：各檔 +數行，皆遠低於 tier 上限（data/adapter/contract）。

### W-61-2 — `select_proposals` 雙信號元學習（`core/ports/translation_learning.py`，data tier ≤150）
介面 delta：
```python
@dataclass(frozen=True)
class TranslationProposal:
    at_id: str
    failing_runs: int
    total_runs: int
    rationale: str
    status: str = "proposed"
    weak_runs: int = 0   # ← 新增：跨 session weak_regex 出現的 run 計數（第二信號強度）

def select_proposals(
    history, already_proposed_at_ids, *,
    min_failing_runs: int = 2, max_new: int = 3,
    min_weak_runs: int = 2,   # ← 新增：weak_regex 頻次門檻
) -> tuple[TranslationProposal, ...]:
    """雙信號元學習：at_id 達 (失敗頻次≥min_failing_runs) OR (weak_regex 頻次≥min_weak_runs)
    且未提議過者 → 提議。rationale 明示哪個信號觸發（XAI 可審）。
    確定性排序：依 (max(失敗頻次,weak頻次) desc, at_id asc)。"""
```
- weak_counter 自 `report.weak_regex_at_ids` 統計（同 fail_counter 模式，run 內去重計 run 數）。
- rationale 分三型：純失敗 / 純 weak_regex / 雙信號（明示信號來源與計數）。
- **importlinter 影響**：仍僅 stdlib + 同層 `rtm_sink` dataclass → 不破壞 core-purity。

### W-61-3 — plugin + config + wiring 接線
6. **`infra/adapters/translation_learning_sink.py`**：write/read additive `weak_runs`（`doc.get("weak_runs", 0)` fail-soft）。
7. **`plugins/translation_learner_plugin.py`**：constructor additive `min_weak_runs: int = 2`，傳入 `select_proposals`；`_emit` additive `weak_runs` 入 observability event。
8. **`utils/config.py PlaybookConfig`**：additive `translation_min_weak_runs: int = Field(default=2, ge=1, le=20)`。
9. **`core/wiring.py`**：plugin 建構傳 `min_weak_runs=cfg.playbook.translation_min_weak_runs`。
- **env**：不新增 env 旗標（沿用既有 opt-out `AUTOCLAUDE_ENABLE_TRANSLATION_AUTO_PROPOSE` 一鍵關全機制）。

### 不需動的部分（scope 收斂證據）
- **SDD 框架本體零改動** → 無 Copy-on-Evolve v0.24、無 `*.tla`/`_HAPPY_PATH` 變更、**無五軌 TLC**。
- `playbook_runner.py`、`goal_decomposer.py` **零改動**；轉譯**輸出** byte-identical（`compile_tasks` 僅多搭旗標、不改 regex/cmd/step）＝零退化根保證。
- 無新 sink、無新 wiring port、無 alembic、無新 DAL 後端。

---

## §6 RTM（需求→設計→測試 追溯）

| RTM | 需求 | 設計落點 | 驗證（測試）| 狀態 |
|-----|------|---------|-----------|------|
| R-61-1 | weak_regex 旗標搭載 PlaybookTask 並由 forward adapter 填 | W-61-1.1/1.2 | `test_sdd_to_playbook_adapter.py::test_compile_tasks_carries_weak_regex`（+`::test_weak_regex_does_not_alter_translation_output`）| ✅ |
| R-61-2 | RtmCoverageReport 帶 weak_regex_at_ids 並由 reverse adapter 填 | W-61-1.3/1.4 | `test_playbook_to_rtm_adapter.py`（TestWeakRegexCollection 3 測：正交收集/空預設/render）| ✅ |
| R-61-3 | coverage doc 往返保 weak_regex_at_ids + 舊紀錄 fail-soft | W-61-1.5 | `test_rtm_feedback.py::test_coverage_doc_roundtrip_weak_regex`、`::test_legacy_doc_missing_weak_field_defaults_empty` | ✅ |
| R-61-4 | weak_regex 第二信號可獨立觸發提議 | W-61-2 | `test_translation_learning_port.py::test_weak_only_signal_proposes`、`::test_proposals_always_proposed_status_dual_signal` | ✅ |
| R-61-5 | 雙信號 OR 語意 + rationale 區分信號來源 | W-61-2 | `::test_dual_signal_rationale_distinguishes`、`::test_fail_only_still_proposes` | ✅ |
| R-61-6 | weak_runs 門檻獨立、降噪 | W-61-2 | `::test_weak_below_threshold_no_propose` | ✅ |
| R-61-7 | 合併候選後仍有界（max_new）+ 確定性 + dedup | W-61-2 | `::test_dual_signal_bounded_and_deterministic`（QA 突變實證）、`::test_dual_signal_dedup_skips_already_proposed` | ✅ |
| R-61-8 | proposals JSONL additive weak_runs round-trip + 舊紀錄相容 | W-61-3.6 | `test_translation_learning_sink.py::test_roundtrip_weak_runs`、`::test_legacy_proposal_missing_weak_runs_reads_zero` | ✅ |
| R-61-9 | plugin 傳 min_weak_runs + config/wiring 接線 | W-61-3.7/8/9 | `test_translation_learner.py`（TestWeakRegexSecondSignal 3 測：驅動/門檻接線/obs weak_runs）| ✅ |
| R-61-10 | 零退化基線 | 全項 §7 矩陣 | pytest **3315/0**（+19）、lint 8 kept、LOC=0、snapshot fresh、ci-gate exit 0 | ✅ |
| R-61-11 | maturity 不變（L5 加固非升級）誠實 | §3 + §4.5 | 三鏡 audit **OVERALL PASS（P0=P1=0）**，見 `AutoSDD_ZeroTrust_Audit_61.md` | ✅ |

> **結案實測**（2026-06-24，parent 親跑）：AutoClaude pytest **3315 passed / 122 skipped / 0 failed**（130.76s；floor 3296，+19）；lint-imports 8 kept / 0 broken；LOC violations=0；snapshot fresh（本輪零新 plugin/port → snapshot 計數不變）；ci-gate exit 0（v0.01:1478 / v0.23:1656 / scripts:129＝階段一同值，證**零接觸 SDD 框架本體**、免 Copy-on-Evolve/免五軌 TLC）。`L_合體` 維持 **L5**（本輪為 A 軸 L5 機制加固，非升級）。

## §7 零退化驗證矩陣（floor = improving_60 §2 實測；通過條件每輪實測，禁寫死）

| 檢查 | 命令 | 通過條件 |
|------|------|---------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ **3296** passed / 0 failed（新測只增不減）|
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過 |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0（pytest not-chaos 全綠 + arch_fitness）|
| DAL 等價 | equivalence job | 三後端等價（學習器/adapter 不碰 state_repository）|
| 五軌 TLC | （僅 FSM 變更時）| **n/a（本輪零 FSM/tla 變更）** |

## §8 缺陷 / 延後

- 行進中框架/工程摩擦發現即記入 `AutoSDD_Defect_Log.md`（DEF-61-NNN）。
- 本輪刻意**不**把 proposals 接成自動 apply（人工 signoff＝L5 守界要件，非延後缺陷）。
- weak_regex 信號目前以「轉譯時 fallback 標記」為來源；未來若引入「regex 實際誤判率」量測作第三信號＝後續輪精修候選（本輪雙信號已足加固 L5）。
