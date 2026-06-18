# AutoSDD_improving_24 — A 軌雙向橋接（SDD→Playbook 逆向回寫閉環）

> **本輪主柱**：**A 軌（整合）** — 推進 AISDLC-SDD × AutoClaude 深度整合。
> **下一份**：`AutoSDD_improving_25.md`（按需）。
> **防跨軌誤指**：本輪在 **A 柱（雙向協作）**，非 B 柱（手腳框架）亦非 C 柱（指揮官內部）。
> 本輪**零框架 v0.0X 變更**（無 Copy-on-Evolve、五軌 TLC 不觸發），所有交付在 AutoClaude 側。
>
> **角色**：Dr. Alan（L10 自治系統與微核心架構總監）
> **日期**：2026-06-17 ｜ **承上**：improving_23 結案（tag v2026.06.17-21）

---

## 0. 北極星對齊

對齊北極星**第 3 點「完美協調溝通機制」**：AutoClaude 利用 AISLDC_SDD 進行軟體開發、建立兩者**雙向橋接**，成為端到端自動化開發 Agent。階段一測繪揭露 A 軌目前**單向偏科**——正向 `SDD→Playbook`（消費側 `SddToPlaybookAdapter`）成熟、逆向 `Playbook→SDD`（執行結果回饋 RTM）幾乎空白，閉環是斷的。本輪補上逆向回寫，使 SDD 規格 → Playbook → 執行 → **覆蓋度/gap 報告回流** 成為完整迴圈。

成熟度三軸（`AutoSDD_Maturity_Rubric.md`，`L_合體 = min(A,B,C)`）：本輪推 **A 軌（協作自治）**——把「規格驅動執行」延伸為「執行結果可機械回饋規格覆蓋度」，降低 A 軸對人工讀 log 判斷覆蓋的依賴。

---

## 1. 階段一：現況重偵察（Zero-Trust Re-Audit）— 實測事實

派三組 Explore agent 親跑實測（**硬閘 PASS**，准入階段二）：

| 檢查 | 實測 | 判定 |
|------|------|------|
| AutoClaude pytest | **3112 passed / 122 skipped / 0 failed / 0 errors** | ✅ floor=3112 |
| lint-imports | 8 kept / 0 broken | ✅ |
| LOC budget | total=17794 / cap=20438，violations=0 | ✅ |
| snapshot | FRESH | ✅ |
| AISDLC_SDD ci-gate | v0.01:1478 + v0.14:1593 + scripts:27 = 3098 passed / 0 failed；arch_fitness exit 0 | ✅ |
| 最新框架版本 | v0.14 | — |

**improving_23 構件複核**：Folding 降維（`recursion_topology_view.py` `RenderBudget.fold_*`/`fold_topology()` + 11 fold 測試）真實落地、零虛報。

**A 軌標的測繪（決定 W 項）**：

| 方向 | 構件 | 成熟度 |
|------|------|--------|
| 正向 SDD→Playbook | `infra/adapters/sdd_to_playbook_adapter.py`（29 測試） | ~80% |
| goal 拆解側 | `execution/goal_decomposer.py`（21 測試） | 成熟 |
| **逆向 Playbook→SDD** | **無（缺 RTM 回寫 / coverage 報告）** | **~30%（本輪標的）** |

**SDD 端事實**：RTM 模板（`docs_template/sdd/testing/RTM-TEMPLATE.md`）為 **Markdown only，無機器可讀版本**；AC/AT 命名 `AC-{NNN}-{Y}` / `AT-{NNN}-{Y}-{Z}`；SCG-5 = RTM 100% AC 覆蓋（人工 `qa-lead` 所有）。

---

## 2. 階段二：增量設計 + `<Architecture_Design_Review>`

### 2.1 W 項（A 軌逆向回寫閉環，🔴 掌舵者選定 scope）

| W 項 | 構件 | 檔案 | tier/LOC |
|------|------|------|----------|
| **W-24-1a** | `RtmCoverageReport` + `IRtmSink` + `NullRtmSink` | `core/ports/rtm_sink.py` | data ≤150 |
| **W-24-1b** | `PlaybookToRtmAdapter`（純函式 compile + render） | `infra/adapters/playbook_to_rtm_adapter.py` | adapter ≤400 |
| **W-24-1c** | `FileRtmSink`（IRtmSink 檔案實作） | `infra/adapters/rtm_file_sink.py` | adapter ≤400 |
| **W-24-2** | `RtmWritebackPlugin`（POST_RUN 觸發） | `plugins/rtm_writeback_plugin.py` | plugin ≤250 |

### 2.2 介面 delta

- **新 port**（與 `ISpecSource` 對稱）：`RtmCoverageReport`（frozen dataclass：scenario/spec_digest/total_at/passed_at/failed_at_ids/ac_coverage + 衍生 property coverage_pct/ac_covered/is_fully_covered）；`IRtmSink.write_report(name, content, *, fmt)`；`NullRtmSink` no-op fallback（仿 `IObservabilityPort`/`NullObservability` 樣式）。
- **逆向 adapter**：`compile_report(tasks, completed_step_ids, *, spec_digest="") -> RtmCoverageReport`（純函式）；`render_yaml(report, *, generated_at=None)`、`render_gap_markdown(report)`。step_id 反解（`sdd-{scenario}-{at_id.lower()}` → at_id，優先用 `task.name`，fallback 反解 step_id），AT→AC 聚合（保守判定：全 AT 通過才算 AC 覆蓋）。
- **plugin**：訂閱 `POST_RUN`（仿 `GoalProgressPlugin`），濾 `step_id` 前綴 `sdd-` 的 task；**非 SDD playbook 全程 no-op**；adapter/sink 經 wiring 注入（Any 型別，不 import infra）；寫出失敗 warning 吞掉不阻斷。
- **wiring**：`_build_rtm_writeback(cfg, observability)` 延遲 import infra（core-purity 豁免點）；加入 `plugins` dict + `_REGISTER_ORDER`（priority=52，goal_progress(50) 後、convergence(65) 前）。

### 2.3 `<Architecture_Design_Review>`（寫實質 Python 前自我驗證）

1. **架構純潔性**：無 God-object；plugin 經建構式注入、不 import infra；core port 僅 import stdlib，不觸 execution/infra。Thin Facade 不動。
2. **持久化相容**：**零 checkpoint schema 變更**——POST_RUN 由現有 `completed_step_ids` + `playbook.tasks` 重建覆蓋度，無新欄位；DAL 三後端零影響。
3. **安全防護網**：本輪**不**新增「從文件生成 shell 指令」路徑（只讀執行結果、寫報告檔）；CONDITIONAL 三層防禦不受影響。報告基名經 `_sanitize_name` 消毒（杜絕路徑穿越）。
4. **對外 I/O 安全**：**未**新增 `ToolInvocationPort` 外呼路徑（只寫本機檔），allowlist 不涉及。
5. **importlinter 影響**：新 port/adapter/plugin 順既有分層；**8 kept / 0 broken 不變**（實測確認）。
6. **回寫安全（關鍵決策）**：**不自動覆寫人工 `RTM-{System}.md`**（SCG-5 人工所有），改另產機器可讀 `RTM-COVERAGE-{project}.yaml` + 人類可讀 `RTM-GAP-{project}.md` 作為**諮詢輸入**，對齊「RTM/SPEC-PATCH 絕不自動套用」紅線。

### 2.4 B 軌 dogfooding — SCG 閘門對應

| SCG | 載體 |
|-----|------|
| SCG-0/1（需求/規格凍結） | 本計畫書 §0~§2 + 🔴 掌舵者 scope 選定 |
| SCG-2（介面設計） | §2.2 介面 delta + §2.3 設計審查 |
| SCG-3（契約） | `IRtmSink` Protocol + `RtmCoverageReport` schema（凍結後實作） |
| SCG-4（PR/實作） | §3 實作 + 單元/契約測試全綠 |
| SCG-5（RTM 覆蓋） | §4 RTM（本輪 AT 100% 覆蓋） |

---

## 3. 階段三：實作與雙重驗證

逐支開發-編譯-測試循環（絕不累積）。新增 4 支源碼 + 3 支測試，並同步 3 處 count-pin（新增 plugin SOP）：

- `autoclaude/core/ports/rtm_sink.py`（port + dataclass，100% cov）
- `autoclaude/infra/adapters/playbook_to_rtm_adapter.py`（逆向 adapter，99% cov）
- `autoclaude/infra/adapters/rtm_file_sink.py`（FileRtmSink，100% cov）
- `autoclaude/plugins/rtm_writeback_plugin.py`（plugin，100% cov）
- wiring 註冊 + `plugins/__init__.py` 匯出
- count-pin 同步：`tests/contract/test_plugin_walk_through.py`（PLUGIN_REGISTRY +1、_REGISTER_ORDER expected +rtm_writeback、≥18）、`tests/tools/test_snapshot_sync_plugin_count.py`（17→18 static / 16→17 active）、CLAUDE.md snapshot 重生（plugin 17 active / port +rtm_sink）+ 合併開頭兩 H1 回收 1 行守 ≤400

---

## 4. RTM（需求追溯矩陣）— 本輪 AT 100% 覆蓋

| AC | AT | 測試 | 狀態 |
|----|----|------|------|
| AC-24-1（逆向 adapter 還原覆蓋度） | AT-24-1-1 pass/fail 分類 | `test_playbook_to_rtm_adapter.py::test_basic_pass_fail` | ✅ |
| AC-24-1 | AT-24-1-2 非 SDD task 忽略 | `::test_non_sdd_tasks_ignored` | ✅ |
| AC-24-1 | AT-24-1-3 completed 去重防 >100% | `::test_completed_dedup` | ✅ |
| AC-24-1 | AT-24-1-4 AC 保守判定 | `::test_ac_conservative_coverage` | ✅ |
| AC-24-1 | AT-24-1-5 step_id 反解 | `::test_step_id_reverse_when_name_missing` | ✅ |
| AC-24-1 | AT-24-1-6 render YAML/gap | `::TestRender` 4 case | ✅ |
| AC-24-1 | AT(unresolved) 畸形記事件跳過 | `::test_unresolvable_sdd_step_recorded_and_skipped` | ✅ |
| AC-24-2（FileRtmSink 寫出） | AT-24-1-7~9 寫檔/副檔名/路徑消毒 | `test_rtm_file_sink.py` 6 case | ✅ |
| AC-24-3（plugin POST_RUN 回寫） | AT-24-2-1 SDD 寫兩報告 | `test_rtm_writeback_plugin.py::test_writes_two_reports_for_sdd_playbook` | ✅ |
| AC-24-3 | AT-24-2-2 非 SDD no-op | `::test_noop_for_non_sdd_playbook` | ✅ |
| AC-24-3 | AT-24-2-3/4 deps/phase no-op | `::test_noop_when_deps_missing` / `::test_noop_for_other_phase` | ✅ |
| AC-24-3 | AT-24-2-5 寫出失敗吞掉 | `::test_writeback_failure_swallowed` | ✅ |
| AC-24-3 | AT-24-2-6 EventBus 整合真實寫檔 | `::TestEventBusIntegration` | ✅ |
| AC-24-4（雙向橋接對稱閉環） | AT-24-2-7 spec→playbook→rtm round-trip | `::TestClosureRoundTrip` | ✅ |

**覆蓋率**：本輪 4 AC / 全部 AT 100% 通過。

---

## 5. 階段四：CI 平價收斂（零退化驗證矩陣）

| 檢查 | 命令 | floor | 實測 | 判定 |
|------|------|-------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3112 / 0 failed | **3146 passed / 122 skipped / 0 failed** | ✅ |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | 8 kept / 0 broken | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0 | total=18157 / cap=20438，violations=0 | ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | FRESH | OK + CLAUDE.md 400≤400 | ✅ |
| 新模組 coverage | per-file cov | ≥90% | 99%（port/sink 100%、adapter 99%、plugin 100%） | ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | 全綠 | **不受影響**（零框架變更，階段一 3098 passed 維持） | ✅（unchanged） |
| 五軌 TLC | （僅 FSM 變更時） | — | **不觸發**（無 `_HAPPY_PATH`/`*.tla` 變更） | N/A |
| DAL 等價 | equivalence | 三後端等價 | 由全套 pytest 涵蓋（無 checkpoint/repository 變更） | ✅ |

**+34 測試**（30 新測試 + walk-through 參數化 +4 case），只增不減、0 failed。

---

## 6. 缺陷分流

- 本輪**未發現新框架缺陷**（零框架變更、純 AutoClaude 整合層擴充）。
- open/routed 既有缺陷：DEF-23-005（RFC 生命週期自動化，routed B 軌下輪，**非本輪 A 軌 scope**）、DEF-01-007（cc-switch GUI，環境側 P3）、DEF-01-009（plugin LOC watch，本輪 rtm_writeback 為**新檔**未動 sdd_governance，不觸發）、DEF-19-001（catch 漸進，未推進）。詳見 `AutoSDD_Defect_Log.md`。

---

## 7. 結案四件套

1. 本計畫書 `docs/04_planning/AutoSDD_improving_24.md`
2. `docs/06_quality/AutoSDD_ZeroTrust_Audit_24.md`（審計 + 三鏡複審證據）
3. `docs/06_quality/AutoSDD_Defect_Log.md`（更新：本輪零新缺陷，open 項複驗）
4. 框架本體改進：**無**（零 v0.0X 變更）
