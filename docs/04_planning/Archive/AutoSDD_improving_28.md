# AutoSDD_improving_28 — A 軌 RTM 跨輪覆蓋趨勢讀回（閉合 W3 冷資料斷鏈）

> **本輪主柱**：**A 軌（整合 / 雙向協作）** — 推進 AISDLC-SDD × AutoClaude 深度整合（北極星第 3 點）。
> **下一份**：`AutoSDD_improving_29.md`（按需）。
> **防跨軌誤指**：本輪在 **A 柱（雙向協作）**，非 B 柱（手腳框架）亦非 C 柱（指揮官內部）。
> 本輪**零框架 v0.0X 變更**（無 Copy-on-Evolve、五軌 TLC 不觸發），所有交付在 AutoClaude 側。
>
> **角色**：Dr. Alan（L10 自治系統與微核心架構總監）
> **日期**：2026-06-17 ｜ **承上**：improving_27 結案（A 軌 RTM 反饋讀回閉環，tag `v2026.06.17-25` / commit `4bfb987`）

---

## 0. 北極星對齊

對齊北極星**第 3 點「完美協調溝通機制」**：AutoClaude 利用 AISLDC_SDD 進行軟體開發、建立兩者**雙向橋接**，成為端到端自動化開發 Agent。

improving_24 補上逆向 `Playbook→SDD` 覆蓋報告**寫出**；improving_27 補上 RTM **讀回**諮詢邊（`read_report` 最新單筆 → evolution rationale）+ 跨輪趨勢 **W3** 持久化（`append_report_line` 寫 `RTM-COVERAGE-HISTORY-*.jsonl`）。但**階段一測繪揭露 improving_27 自己「報告產出後無人讀」的斷鏈模式在 W3 趨勢層復發**——`read_history` grep 全倉**生產端零消費**（僅測試呼叫），跨輪趨勢成冷資料。本輪 W-28-1 補上趨勢讀回的生產消費端（諮詢註記），閉合該斷鏈。

成熟度三軸（`AutoSDD_Maturity_Rubric.md`，`L_合體 = min(A,B,C)`）：本輪續推 **A 軌（協作自治）L3→L4**——把 W3 冷資料接上生產消費邊。**禁宣稱 L 級躍升**：本輪僅補一條趨勢讀回邊（flag-gated、諮詢用），完全比照 improving_27 W1 紀律，是 L3→L4 的最小誠實一步，`L_合體` 仍受最弱軸卡住、不變。

---

## 1. 階段一：現況重偵察（Zero-Trust Re-Audit）— 實測事實

派背景 agent 親跑實測（**硬閘 PASS**，准入階段二）。所有數字來自當前回合真實 tool_result：

| 檢查 | 命令 | 實測 | 判定 |
|------|------|------|------|
| AutoClaude pytest | `python -m pytest tests/ -q` | **3175 passed / 122 skipped / 0 failed**（120.41s） | ✅ floor=3175 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | ✅ |
| LOC budget | `python tools/check_loc_budget.py` | total=18399 / cap=20438，violations=0 | ✅ |
| snapshot | `python tools/snapshot_sync.py --check` | FRESH（port 16 / plugin 17） | ✅ |
| AISDLC_SDD ci-gate | `bash scripts/ci-gate.sh` | exit 0（v0.01:1478 + v0.14:1593 + scripts:27），arch_fitness advisory warn 不阻擋 | ✅ |
| 最新框架版本 | — | **v0.14**（本輪零觸碰） | — |

**外部工具依賴（階段一 (f)）**：本輪純 AutoClaude 整合層擴充（讀本機 history jsonl），無 A/B 後端切換、無外部 CLI/服務、無訊息平台——不適用（DEF-01-007 cc-switch 維持 open，與本輪無關）。

**A 軌標的測繪（決定 W 項，zero-trust 親 grep 碼，遵 DEF-26-001/DEF-27-001）**：

| 段 | 構件 | 現況（file:line） |
|----|------|-------------------|
| 正向 SDD→Playbook | `sdd_to_playbook_adapter.py`（29 測試） | 成熟 ~80%（缺 Given/When、複雜斷言組合——非本輪 scope） |
| 逆向寫出 | `rtm_writeback_plugin.py:80-97` + `playbook_to_rtm_adapter.py` | 存在（improving_24/27） |
| 逆向讀回（最新單筆） | `evolution_plugin.py:129` `_rtm_gap_annotation` 消費 `read_report` | 存在（improving_27 W1，諮詢用） |
| **逆向讀回（跨輪趨勢）** | `read_history` 接口存在（`rtm_file_feedback_source.py:51-75`），**grep 全倉生產端零消費**（僅測試呼叫） | **本輪標的（W3 冷資料斷鏈）** |

---

## 2. 階段二：增量設計（🔴 掌舵者選定 W-28-1）

### 2.1 scope 決策

🔴 掌舵者選定主柱＝**A 軌**、driver＝**沿用上輪未完 W 項**。階段一揭露 improving_27 **W1+W3 全結、W2 撤除＝無字面未完 W 項**；「沿用」忠實錨定到 **W3 趨勢 `read_history` 冷資料斷鏈**——這正是 improving_27 自己發現並修正（對 `read_report`）的「報告產出後無人讀」模式在趨勢層的復發。

**🔴 DEF-27-001 級紅線陷阱（已主動規避）**：測繪 agent 把「history 讀回」候選寫成「**驅動保守/激進演化策略選擇**」——該版本撞 `max_evolutions` 時序紅線（`config.py:52`）+ 違反「RTM/SPEC 不自動套用」停機級紅線，**不採信**。改採**安全且忠實版本**：趨勢讀回做成**諮詢註記**（完全比照 improving_27 W1），不改 mutation 決策、不碰 max_evolutions、flag 預設 OFF。

### 2.2 本輪 W 項（單一 W，Rule 2 最小）

| W 項 | 構件 | 檔案 | tier/LOC |
|------|------|------|----------|
| **W-28-1a** | `CoverageTrend` dataclass + `coverage_trend(history)` 純函式（以 `ac_coverage_pct` 為指標，計算上輪/本輪/delta/連續下降/方向；空→None、單輪→`single`） | `core/ports/rtm_feedback.py` | data ≤150 |
| **W-28-1b** | `EvolutionPlugin._rtm_trend_annotation`（消費 `read_history`，與 gap 同守門＋fail-soft，附趨勢諮詢到 rationale）+ surgical 接入 `_handle_propose` | `plugins/evolution_plugin.py` | strategy ≤300 |

**不新增 config flag**：複用既有 `enable_rtm_feedback`（預設 OFF）——趨勢是同一 RTM 反饋諮詢功能消費 history 而非最新單筆（Rule 2，零新 config surface）。

### 2.3 `<Architecture_Design_Review>`（寫實質 Python 前自我驗證）

1. **架構純潔性**：`coverage_trend` 為純函式（無副作用、無 I/O），落 port 層與既有 `coverage_report_to_doc/from_doc` 同模式（Rule 5：可程式判定不交模型）；plugin 經建構式注入的 source 取 history、不 import infra（source 為 Any）。plugin 新增 import 邊 `plugins → core.ports.rtm_feedback`（純 port，非 infra，不破任何 importlinter contract）。無 God-object，`playbook_runner.py` Thin Facade 不動。✅
2. **持久化相容**：**零 checkpoint schema 變更、零 DAL 變更**（只讀既有 history jsonl，不新增持久化）——三後端零影響。✅
3. **安全防護網**：無「從文件生成 shell 指令」新路徑（只讀 history）；history 讀回沿用 improving_27 `FileRtmFeedbackSource` 既有 `_sanitize` 路徑穿越防護（本輪未改 adapter）。✅
4. **對外 I/O 安全**：未新增 `ToolInvocationPort` 外呼路徑（只讀本機檔），allowlist 不涉及。✅
5. **紅線守界（關鍵）**：趨勢反饋**僅在 rationale 增補諮詢文字，不改 mutation 決策、不碰 max_evolutions、不自動套用 RTM/SPEC**；flag `enable_rtm_feedback` 預設 **OFF**（零退化）；演化仍走 `require_evolution_signoff` + `max_evolutions` 硬閘。fail-soft：讀回任何例外吞掉回 ""，不阻斷主流程。✅

### 2.4 B 軌 dogfooding — SCG 閘門對應

| SCG | 載體 |
|-----|------|
| SCG-0/1（需求/規格凍結） | 本計畫書 §0~§2 + 🔴 掌舵者 scope 選定（W-28-1，紅線守界 flag-gated） |
| SCG-2（介面設計） | §2.2 介面 delta + §2.3 設計審查 |
| SCG-3（契約） | `coverage_trend` 純函式契約 + `CoverageTrend` dataclass（凍結後實作） |
| SCG-4（PR/實作） | §3 實作 + 單元/契約測試全綠 |
| SCG-5（RTM 覆蓋） | §4 RTM（本輪 AT 100% 覆蓋） |

---

## 3. 階段三：實作與雙重驗證

逐支開發-編譯-測試循環（絕不累積）。新增 **0 支源碼檔**（純 additive 至既有 2 檔），surgical 改 2 支源碼 + 2 支測試檔：

- `autoclaude/core/ports/rtm_feedback.py`（+`CoverageTrend` + `coverage_trend` 純函式 + import dataclass + `__all__` 補 2 名）
- `autoclaude/plugins/evolution_plugin.py`（+`_rtm_trend_annotation` + import `coverage_trend` + `_handle_propose` rationale surgical 接入）
- `tests/core/ports/test_rtm_feedback.py`（+`TestCoverageTrend` **7 case**，7→14）
- `tests/plugins/test_evolution_rtm_feedback.py`（+`TestTrendAnnotation` **7 case** + 擴 `_FakeFeedback` 支援 history，8→15）

**共 +14 測試**（3175→3189），只增不減、0 failed。

---

## 4. RTM（需求追溯矩陣）— 本輪 AT 100% 覆蓋

| AC | AT | 測試 | 狀態 |
|----|----|------|------|
| AC-28-1（趨勢純函式契約） | AT-28-1-1 空 history→None | `test_rtm_feedback.py::TestCoverageTrend::test_empty_history_returns_none` | ✅ |
| AC-28-1 | AT-28-1-2 單輪→single/previous=None | `::test_single_round_is_single_direction` | ✅ |
| AC-28-1 | AT-28-1-3 improving（40→80） | `::test_two_rounds_improving` | ✅ |
| AC-28-1 | AT-28-1-4 declining（80→40） | `::test_two_rounds_declining` | ✅ |
| AC-28-1 | AT-28-1-5 連續下降計數（100→80→40） | `::test_consecutive_declines_counts_trailing_drops` | ✅ |
| AC-28-1 | AT-28-1-6 flat（50→50） | `::test_flat_trend` | ✅ |
| AC-28-1 | AT-28-1-7 先升後降只計末段下降 | `::test_recover_then_dip_only_counts_last_decline` | ✅ |
| AC-28-2（plugin 趨勢諮詢，flag-gated） | AT-28-2-1 flag OFF→"" | `test_evolution_rtm_feedback.py::TestTrendAnnotation::test_flag_off_no_trend` | ✅ |
| AC-28-2 | AT-28-2-2 無 source→"" | `::test_no_source_no_trend` | ✅ |
| AC-28-2 | AT-28-2-3 非 SDD step→"" | `::test_non_sdd_step_no_trend` | ✅ |
| AC-28-2 | AT-28-2-4 單輪 history→"" | `::test_single_round_no_trend` | ✅ |
| AC-28-2 | AT-28-2-5 下降趨勢→諮詢註記（含連續下降+紅線標記） | `::test_declining_trend_produces_annotation` | ✅ |
| AC-28-2 | AT-28-2-6 read_history 例外 fail-soft | `::test_read_history_error_fail_soft` | ✅ |
| AC-28-2 | AT-28-2-7 端到端 rationale 含趨勢（不改 mutation） | `::test_trend_in_end_to_end_rationale` | ✅ |

**覆蓋率**：本輪 2 AC / 全部 14 AT 100% 通過。

---

## 5. 階段四：CI 平價收斂（零退化驗證矩陣）

| 檢查 | 命令 | floor（improving_27 實測） | 本輪實測 | 判定 |
|------|------|------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3175 / 0 failed | **3189 passed / 122 skipped / 0 failed**（115.70s） | ✅ +14 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | 8 kept / 0 broken | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0 | total=18482 / cap=20438，violations=0 | ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | FRESH | FRESH（無新 port/plugin，純 additive） | ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | 全綠 | exit 0（v0.01:1478 + v0.14:1593 + scripts:27） | ✅（持平，本輪未動框架） |
| DAL 等價 | equivalence | 三後端等價 | 零 checkpoint/repository 變更（只讀 history），含於全套 | ✅ |
| 五軌 TLC | （僅 FSM 變更時） | — | **不觸發**（零 `_HAPPY_PATH`/`*.tla` 變更） | N/A |

---

## 6. 缺陷分流

- **本輪零新框架缺陷、零新整合層缺陷**（純 AutoClaude 諮詢讀回擴充，零框架 v0.0X 變更）。
- **DEF-27-001 教訓主動應用**：測繪 agent 的「history 讀回驅動演化策略」建議撞 max_evolutions 時序紅線，本輪 zero-trust 複核後改採諮詢版本（§2.1），未盲信。
- open/routed 既有缺陷複驗：DEF-23-005（RFC 生命週期自動化，routed B 軌，**非本輪 A 軌 scope**）、DEF-01-007（cc-switch GUI，環境側）、DEF-01-009（sdd_governance LOC watch，本輪未動該 plugin，不觸發）、DEF-19-001（catch 漸進覆蓋，routed B 軌）、DEF-17-001（fire 側已 fixed/catch routed）——詳見 `AutoSDD_Defect_Log.md`。

**本輪新增防退化資產（非缺陷）**：趨勢純函式 `coverage_trend` 由 `test_rtm_feedback.py::TestCoverageTrend` 7 case 鎖定方向/連續下降判定；plugin 諮詢註記由 `TestTrendAnnotation` 7 case 鎖定 flag-gate + fail-soft + 紅線（不改 mutation）。`read_history` 由此取得首個生產消費端，W3 冷資料斷鏈閉合。

---

## 7. 結案四件套

1. 本計畫書 `docs/04_planning/AutoSDD_improving_28.md`
2. `docs/06_quality/AutoSDD_ZeroTrust_Audit_28.md`（審計 + 三鏡複審證據）
3. `docs/06_quality/AutoSDD_Defect_Log.md`（improving_28 複驗註記；零新缺陷）
4. 框架本體改進：**無**（零 v0.0X 變更）
