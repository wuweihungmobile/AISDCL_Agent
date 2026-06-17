# AutoSDD_improving_27 — A 軌 RTM 反饋迴圈 + 跨輪覆蓋趨勢持久化

> **本輪主柱**：**A 軌（整合 / 雙向協作）** — 推進 AISDLC-SDD × AutoClaude 深度整合（北極星第 3 點）。
> **下一份**：`AutoSDD_improving_28.md`（按需）。
> **防跨軌誤指**：本輪在 **A 柱（雙向協作）**，非 B 柱（手腳框架）亦非 C 柱（指揮官內部）。
> 本輪**零框架 v0.0X 變更**（無 Copy-on-Evolve、五軌 TLC 不觸發），所有交付在 AutoClaude 側。
>
> **角色**：Dr. Alan（L10 自治系統與微核心架構總監）
> **日期**：2026-06-17 ｜ **承上**：improving_26 結案（C 軌引擎成熟度認證，tag `v2026.06.17-24` / commit `6331b74`）

---

## 0. 北極星對齊

對齊北極星**第 3 點「完美協調溝通機制」**：AutoClaude 利用 AISLDC_SDD 進行軟體開發、建立兩者**雙向橋接**，成為端到端自動化開發 Agent。improving_24 補上逆向 `Playbook→SDD`（執行結果 → RTM coverage 報告**寫出**），使閉環有出口；但階段一測繪揭露**閉環仍斷在「報告產出後無人讀」**——報告寫到磁碟後 grep 全倉無消費端，「執行結果 → 覆蓋度回流 → 驅動下一動作」的**讀回邊缺失**。本輪補上讀回側（W1）+ 跨輪趨勢持久化（W3），使 A 軸「執行結果可機械回饋」而非僅人工讀 log。

成熟度三軸（`AutoSDD_Maturity_Rubric.md`，`L_合體 = min(A,B,C)`）：本輪推 **A 軌（協作自治）L3→L4**——補上反饋讀回邊（被測試鎖定的真實閉環），降低 A 軸對人工讀覆蓋 log 的依賴。**禁宣稱 L 級躍升**：本輪僅補一條讀回邊（flag-gated、諮詢用），是 L3→L4 的最小誠實一步，`L_合體` 仍受最弱軸卡住、不變。

---

## 1. 階段一：現況重偵察（Zero-Trust Re-Audit）— 實測事實

派背景 agent 親跑實測（**硬閘 PASS**，准入階段二）。所有數字來自本回合真實 tool_result：

| 檢查 | 命令 | 實測 | 判定 |
|------|------|------|------|
| AutoClaude pytest | `python -m pytest tests/ -q` | **3146 passed / 122 skipped / 0 failed**（114.58s） | ✅ floor=3146 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken（188 files / 474 deps） | ✅ |
| LOC budget | `python tools/check_loc_budget.py` | total=18157 / cap=20438，violations=0 | ✅ |
| snapshot | `python tools/snapshot_sync.py --check` | FRESH | ✅ |
| AISDLC_SDD ci-gate | `bash scripts/ci-gate.sh` | exit 0（v0.01:1478 + v0.14:1593 + scripts:27），arch_fitness exit 0 | ✅ |
| 最新框架版本 | — | v0.14（本輪零觸碰） | — |

**外部工具依賴（階段一 (f)）**：本輪純 AutoClaude 整合層擴充（讀寫本機報告檔），無 A/B 後端切換、無外部 CLI/服務、無訊息平台——不適用（DEF-01-007 cc-switch 維持 open，與本輪無關）。

**A 軌標的測繪（決定 W 項）** — 派 Explore agent read-only 偵察，附 file:line：

| 方向 | 構件 | 現況 |
|------|------|------|
| 正向 SDD→Playbook | `infra/adapters/sdd_to_playbook_adapter.py`（29 測試） | 成熟 ~80% |
| 逆向 Playbook→RTM **寫出** | `plugins/rtm_writeback_plugin.py` + `playbook_to_rtm_adapter.py`（improving_24） | 存在 |
| 逆向 RTM **讀回**（消費端） | **無**——`rtm_writeback_plugin.py:63-72` 寫報告後 `return None`，grep 全倉無消費端 | **本輪標的（斷鏈）** |

---

## 2. 階段二：增量設計 + zero-trust 對測繪建議的三次修正

### 2.1 🔴 掌舵者 scope 決策 + 三次設計修正（本輪方法論價值）

測繪 agent 初版建議 W1（RTM→evolution 反饋）+ W2（統一路由層）+ W3（checkpoint snapshot 持久化）。主 agent 依範本 zero-trust 紀律（#17：agent 結論本身須複核）對每項做**系統實況複核**，發現**三處設計缺陷**，均經 🔴 掌舵者知情後修正：

| # | 測繪建議 | zero-trust 複核發現 | 修正 | 證據 |
|---|---------|--------------------|------|------|
| 修正① | W1 RTM 報告 → 同次 run 的 evolution 消費 | **時序矛盾**：報告在 POST_RUN（run 完整走完）產出，evolution 在 ON_ESCALATION（run 中途）觸發，同次 run 無法消費自己尚未產出的報告 | 改為**讀回上次留下的報告**作諮詢信號 | `kernel.py:127`（POST_RUN）vs `evolution_plugin` ON_ESCALATION |
| 修正② | W2 workflow_type/goal/manual 統一路由層 | **過度抽象**（Rule 2/3）：`workflow_type` 已是 SSOT 判別欄、`boot_helper.py:92` 已有解析點、SDD（執行中守門）與 goal_decompose（執行前產草稿）本在不同生命週期、`GoalDecomposer.decompose()` 甚至無生產呼叫端——為不存在的衝突建抽象 | **W2 撤除**，🔴 掌舵者改選 W3 | `sdd_governance_plugin.py:159`、`boot_helper.py:92-96`、grep `decompose(` 無生產呼叫端 |
| 修正③ | W3 POST_RUN 注入 checkpoint JSONB snapshot | **時序矛盾**：`playbook_runner.py:428-429` 成功 run 立即 clear checkpoint，而 RTM 報告僅在成功完成的 POST_RUN 產出；中斷未完成的 run 不走 POST_RUN（無報告）→ checkpoint 載體無有效保存路徑 | 改採**無矛盾載體**：append-only history 檔（`RTM-COVERAGE-HISTORY-{project}.jsonl`），與 W1 feedback source 對稱整合 | `playbook_runner.py:428-429`、`kernel.py:127` |

**方法論結論**：三次修正皆「測繪/設計 agent 的增量建議未經系統實況（時序、抽象必要性）驗證」——正是範本 zero-trust 紀律的價值。記入缺陷帳本 **DEF-27-001**（P3 流程觀察）防未來輪盲信 agent 設計建議。

### 2.2 本輪 W 項（A 軌反饋讀回 + 趨勢持久化，🔴 掌舵者選定 W1+W3）

| W 項 | 構件 | 檔案 | tier/LOC |
|------|------|------|----------|
| **W1a** | `IRtmFeedbackSource`（read_report/read_history）+ `NullRtmFeedbackSource` + `coverage_report_to_doc`/`from_doc` 共用序列化 | `core/ports/rtm_feedback.py` | data ≤150 |
| **W1b** | `FileRtmFeedbackSource`（讀 yaml/jsonl 反序列化，fail-soft） | `infra/adapters/rtm_file_feedback_source.py` | adapter ≤400 |
| **W1c** | EvolutionPlugin 注入 `rtm_feedback` + `enable_rtm_feedback`；ON_ESCALATION SDD step 讀回 gap 附 `rationale`（諮詢） | `plugins/evolution_plugin.py`（surgical） | strategy ≤300 |
| **W1d** | `PlaybookConfig.enable_rtm_feedback: bool=False` + wiring 注入 feedback source | `utils/config.py` / `core/wiring.py` | — |
| **W3a** | `IRtmSink.append_report_line` + `FileRtmSink`/`NullRtmSink` 實作 | `core/ports/rtm_sink.py` / `infra/adapters/rtm_file_sink.py` | data/adapter |
| **W3b** | `rtm_writeback_plugin` POST_RUN append coverage snapshot 到 history jsonl | `plugins/rtm_writeback_plugin.py`（surgical） | plugin_entry ≤250 |

### 2.3 `<Architecture_Design_Review>`（寫實質 Python 前自我驗證）

1. **架構純潔性**：W1 新 port `rtm_feedback`（仿 `rtm_sink`，僅 import stdlib + 同層 dataclass，不觸 execution/infra）；新 adapter 順既有分層；EvolutionPlugin / rtm_writeback 經建構式注入、不 import infra（feedback source 為 Any 型別）。無 God-object，`playbook_runner.py` Thin Facade 不動。✅
2. **持久化相容**：W3 改採 history 檔（修正③），**零 checkpoint schema 變更、零 DAL 變更**——繞過 PG 逐欄位映射成本，三後端零影響。✅
3. **安全防護網**：無「從文件生成 shell 指令」新路徑（只讀/寫報告檔）；reader `_sanitize` 與 sink `_sanitize_name` 對稱消毒，防 project 名路徑穿越讀到 base_dir 外。✅
4. **對外 I/O 安全**：未新增 `ToolInvocationPort` 外呼路徑（只讀寫本機檔），allowlist 不涉及。✅
5. **紅線守界（關鍵）**：W1 反饋**僅在 evolution `rationale` 增補諮詢文字，不改 mutation 決策、不自動套用 RTM/SPEC**；flag `enable_rtm_feedback` 預設 **OFF**（零退化）；演化仍走 `require_evolution_signoff` + `max_evolutions` 硬閘（對齊「RTM/SPEC-PATCH 絕不自動套用」紅線 + `enable_kernel_brain`/DEF-13-004 flag-gate 雙前例）。fail-soft：讀回任何例外吞掉，不阻斷主流程。✅

### 2.4 B 軌 dogfooding — SCG 閘門對應

| SCG | 載體 |
|-----|------|
| SCG-0/1（需求/規格凍結） | 本計畫書 §0~§2 + 🔴 掌舵者 scope 選定（W1+W3，紅線守界 flag-gated） |
| SCG-2（介面設計） | §2.2 介面 delta + §2.3 設計審查 |
| SCG-3（契約） | `IRtmFeedbackSource` Protocol + `coverage_report_to_doc/from_doc` 序列化契約（凍結後實作） |
| SCG-4（PR/實作） | §3 實作 + 單元/契約測試全綠 |
| SCG-5（RTM 覆蓋） | §4 RTM（本輪 AT 100% 覆蓋） |

---

## 3. 階段三：實作與雙重驗證

逐支開發-編譯-測試循環（絕不累積）。新增 2 支源碼 + 3 支測試檔，surgical 改 6 支既有檔：

- `autoclaude/core/ports/rtm_feedback.py`（新 port + 共用序列化，**7 測試**）
- `autoclaude/infra/adapters/rtm_file_feedback_source.py`（reader，**9 測試**）
- `autoclaude/core/ports/rtm_sink.py`（+`append_report_line` Protocol/Null）
- `autoclaude/infra/adapters/rtm_file_sink.py`（+`append_report_line` 實作，**+3 測試**＝9）
- `autoclaude/plugins/evolution_plugin.py`（+`rtm_feedback` 注入 + `_rtm_gap_annotation`，**8 測試**，既有 15 零退化）
- `autoclaude/utils/config.py`（+`enable_rtm_feedback` flag）
- `autoclaude/core/wiring.py`（+`_build_rtm_feedback_source` + EvolutionPlugin 注入）
- `autoclaude/plugins/rtm_writeback_plugin.py`（POST_RUN +append history，**+2 測試**＝12）
- count-pin：snapshot 重生（port 15→16 含 `rtm_feedback`）+ CLAUDE.md 過期 port 註解壓縮（10→實況，回收行數守 398≤400）

**共 +29 測試**（3146→3175），只增不減、0 failed。

---

## 4. RTM（需求追溯矩陣）— 本輪 AT 100% 覆蓋

| AC | AT | 測試 | 狀態 |
|----|----|------|------|
| AC-27-1（反饋讀回契約） | AT-27-1-1 Null no-op | `test_rtm_feedback.py::TestNullFeedbackSource` 2 case | ✅ |
| AC-27-1 | AT-27-1-2 to_doc/from_doc round-trip | `::test_to_doc_from_doc_restores_fields` | ✅ |
| AC-27-1 | AT-27-1-3 解析既有 render_yaml（格式一致鎖定） | `::test_from_doc_parses_render_yaml_output` | ✅ |
| AC-27-1 | AT-27-1-4 畸形 doc fail-soft | `::TestFailSoft` 2 case | ✅ |
| AC-27-2（FileRtmFeedbackSource 讀回） | AT-27-2-1 不存在→None | `test_rtm_file_feedback_source.py::test_missing_returns_none` | ✅ |
| AC-27-2 | AT-27-2-2 sink→source 端到端 round-trip | `::test_roundtrip_sink_to_source` | ✅ |
| AC-27-2 | AT-27-2-3 history 順序 + limit | `::TestReadHistory` 3 case | ✅ |
| AC-27-2 | AT-27-2-4 畸形 yaml/jsonl fail-soft | `::test_malformed_*` 3 case | ✅ |
| AC-27-2 | AT-27-2-5 project 名路徑穿越消毒對稱 | `::test_traversal_project_name_sanitized` | ✅ |
| AC-27-3（sink append + W3b 寫入） | AT-27-3-1~3 append 累積/消毒/observability | `test_rtm_file_sink.py::TestFileRtmSinkAppendHistory` 3 case | ✅ |
| AC-27-3 | AT-27-3-4 SDD playbook POST_RUN append snapshot | `test_rtm_writeback_plugin.py::test_appends_history_snapshot_for_sdd_playbook` | ✅ |
| AC-27-3 | 非 SDD 零退化（不 append） | `::test_no_history_for_non_sdd_playbook` | ✅ |
| AC-27-4（evolution 諮詢接入，flag-gated） | AT-27-4-1 flag OFF 零退化 | `test_evolution_rtm_feedback.py::test_flag_off_*` | ✅ |
| AC-27-4 | AT-27-4-2 flag ON+SDD+gap→rationale 附摘要 | `::test_gap_produces_annotation` / `::test_flag_on_rationale_includes_feedback` | ✅ |
| AC-27-4 | AT-27-4-3 非 SDD/無 source/全覆蓋→無註記 | `::TestAnnotationBranches` 3 case | ✅ |
| AC-27-4 | AT-27-4-4 read 例外 fail-soft | `::test_read_error_fail_soft` | ✅ |

**覆蓋率**：本輪 4 AC / 全部 AT 100% 通過。

---

## 5. 階段四：CI 平價收斂（零退化驗證矩陣）

| 檢查 | 命令 | floor（improving_26 實測） | 本輪實測 | 判定 |
|------|------|------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3146 / 0 failed | **3175 passed / 122 skipped / 0 failed**（112s） | ✅ +29 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | 8 kept / 0 broken | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0 | total=18399 / cap=20438，violations=0 | ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | FRESH | FRESH（CLAUDE.md 398≤400） | ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | 全綠 | exit 0（v0.01:1478 + v0.14:1593 + scripts:27） | ✅（持平） |
| DAL 等價 | equivalence | 三後端等價 | 零 checkpoint/repository 變更（W3 改 history 檔），含於全套 | ✅ |
| 五軌 TLC | （僅 FSM 變更時） | — | **不觸發**（零 `_HAPPY_PATH`/`*.tla` 變更） | N/A |

---

## 6. 缺陷分流

- **DEF-27-001（本輪新增，P3 流程觀察）**：測繪/設計 agent 的增量建議須經主 agent zero-trust 對「系統實況（時序、抽象必要性）」複核，不可直接採信——本輪三次修正（W1/W3 時序、W2 過度抽象）實證。詳見 Defect_Log。
- **本輪零新框架缺陷**（純 AutoClaude 整合層擴充，零框架 v0.0X 變更）。
- open/routed 既有缺陷複驗：DEF-23-005（RFC 生命週期自動化，routed B 軌，**非本輪 A 軌 scope**）、DEF-01-007（cc-switch GUI，環境側）、DEF-01-009（sdd_governance LOC watch，本輪未動該 plugin，不觸發）、DEF-19-001（catch 覆蓋 4/39，routed B 軌）、DEF-17-001（fire 側已 fixed/catch routed）——詳見 `AutoSDD_Defect_Log.md`。

---

## 7. 結案四件套

1. 本計畫書 `docs/04_planning/AutoSDD_improving_27.md`
2. `docs/06_quality/AutoSDD_ZeroTrust_Audit_27.md`（審計 + 三鏡複審證據）
3. `docs/06_quality/AutoSDD_Defect_Log.md`（新增 DEF-27-001 + improving_27 複驗註記）
4. 框架本體改進：**無**（零 v0.0X 變更）
