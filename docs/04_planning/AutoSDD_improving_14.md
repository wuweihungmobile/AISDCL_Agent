# AutoSDD_improving_14 — AISDLC-SDD × AutoClaude 深度整合執行計畫（第 14 輪）

> **版本**：14（第十四輪迭代，按需）
> **日期**：2026-06-15
> **作者**：Dr. Alan（L10 自治系統與微核心架構總監）
> **狀態**：✅ 結案（含 zero-trust 多專家複審）。
> **本輪柱別**：**A 軌（整合，疊加 XAI Turn 首席架構師視角）**。下一份：`AutoSDD_improving_15.md`（按需）。
> **驅動（🔴 人工於階段二後 signoff 選定）**：把 AISDLC_SDD（手腳）已落地的 **meta⁸ 互遞迴拓樸審批儀表板**（Phase Y / ACT-160~161 / R-9.37）**橋接到 AutoClaude（指揮官）的 signoff / escalation 人類審批介面**——對齊北極星 #3（雙向橋接）與〈XAI Turn〉哲學「人類無法審批＝架構失控」。
> **絕對前提**：零退化（Zero-Regression）— AutoClaude 基線 **3091 passed / 122 skipped / 0 failed**（2026-06-15 階段一本機實測）；交付後 **3112 passed / 122 skipped / 0 failed**（+21＝W-14-1 8 + W-14-2 8 + W-14-3 5，0 failed）。lint-imports 8 kept/0 broken、LOC violations=0（plugin 243 / helper 27）、snapshot OK（新增第 14 port）、AISDLC_SDD ci-gate exit 0（v0.01:1478 / v0.05:1499 / scripts:24，與基線一致＝SDD 本體零改）。

---

## 0. 階段一 Zero-Trust 重偵察實測事實基線（2026-06-15，非文件宣稱）

主 agent 親跑（非引用文件）：

| # | 事實 | 證據 | 對本輪影響 |
|---|------|------|-----------|
| F1 | AutoClaude 全套（**改動前**）= **3091 passed / 122 skipped / 0 failed**（99.36s） | `python -m pytest tests/ -q` | 硬閘 floor=3091，0 failed → **通過** |
| F2 | `lint-imports` = **8 kept / 0 broken** | `PYTHONUTF8=1 lint-imports` | 架構紅線 8 條全保 |
| F3 | LOC violations=**0**（total 17713 / cap 20438） | `python tools/check_loc_budget.py` | 分級政策全過 |
| F4 | AISDLC_SDD `ci-gate.sh` = **exit 0**；v0.01:1478 / v0.05:1499 / scripts:24 | `bash scripts/ci-gate.sh` | 雙軌＋共享 infra 健康 |
| **F5（關鍵）** | **XAI 視覺化儀表板在 AISDLC_SDD（手腳）已完整交付** | `recursion_topology_view.py`(686 行) + `steersman_renderer.render_recursion_topology_dashboard`(:890) + `test_phase_y.py`(37 case) + R-9.37 + META_FSM `VisualizationBounded` | 驅動**重定調**：非「建儀表板」（已建），而是橋接 |
| **F6（關鍵）** | **AutoClaude（指揮官）對該儀表板零消費** | `grep -rln "recursion_topology\|render_recursion_topology_dashboard\|steersman_renderer" AutoClaude/` = **0 筆** | 真缺口＝A 軌橋接（舵手在指揮官端只能盲簽） |

**硬閘判定**：F1 基線 0 failed 且 3091 = 上輪 floor → **通過**，准進階段二。

**F5/F6 即本輪 zero-trust 最重要產出**：原始驅動「為 meta⁸ 開發人類視覺化儀表板」若照字面開輪＝**重造既有成熟構件**（違反零退化/surgical 原則）。zero-trust 實測攔下此誤判，將本輪正確重定調為「橋接既有手腳構件到指揮官審批面」。

### 0.1 三軸成熟度對位（本輪 A 軸觸及）

本輪非「成熟度三軸實測升軸」型（improving_13 已做），而是按需 A 軌橋接。但對 **A 協作自治軸** 有實質意義：improving_13 評 A=L3（卡點「規格→playbook 自動編譯但**人類審批面僅文字、無高階構件可視化**」）。本輪把手腳側已證良基終止的互遞迴圖**有界、可稽核地**呈現到指揮官審批面，是 A 軸朝「人類舵手能直觀審批高階自治產物」邁進的一塊基石（未宣稱躍升 L4——僅單一構件橋接，非全鏈；維持 zero-trust 不虛報）。

---

## 1. `<Architecture_Design_Review>`（寫任何實質 Python 前的強制自我檢核）

> **本輪改動面**：純 AutoClaude 整合層。**AISDLC_SDD v0.01~v0.05 凍結本體零改動**（git status `AISDLC_SDD/` 全潔淨 → 故無 Copy-on-Evolve、無 `_HAPPY_PATH`/`.tla` 變更、無五軌 TLC 觸發）。

### 核心架構決策：橋接＝資料消費，非程式碼耦合

AutoClaude 是獨立 package，**不能** import SDD 的 `tools.fsm_runtime`（跨 package、namespace 衝突、破微核心邊界）。故橋接鏡像既有 `ISpecSource` 讀 `build/reports/fsm/FSM-STATE-*.yaml` 的模式——**消費 SDD 渲染產物（Markdown + JSON sidecar），AutoClaude 純當 presenter**。否決的替代：① import SDD（破邊界）；② 在 AutoClaude 重寫渲染器（DRY/雙頭漂移）。

| 檢核項 | 結論 |
|--------|------|
| 1.1 架構純潔性 | **維持**。新增 read-only port（core 僅依賴介面）+ infra adapter（封裝產物格式知識）+ plugin 經 constructor 注入 port；`playbook_runner` Thin Facade 零業務邏輯（僅 choke-point `dump_escalation_impl` 加防禦性 resolver）。零 God-object。 |
| 1.2 持久化相容 | **維持**。`SddGovernancePlugin.snapshot()`/`restore()` additive 加 `topology_dashboard` 鍵（向後相容，舊 checkpoint 無此鍵時 restore no-op）；`EscalationDump` additive 加 `topology_dashboard` 欄（預設 ""）。零 DAL 觸碰、零 alembic。DAL 三後端零停機維持。 |
| 1.3 安全防護網（fail-closed 反視覺欺騙） | **強化**。本橋接的存在理由＝防止「把 SDD 端稽核不過的圖盲簽端到舵手面前」。adapter 三道 fail-closed：①缺 sidecar→raise；②`consistency.verified` 非 True→raise；③**獨立重算** sidecar 自報 (nodes,edges) 的 digest 與其宣稱 `audit_digest` 不符→raise（AutoClaude 端不盲信標籤，與 SDD 端 PY-2「渲染↔to_dict() 真相」互補成縱深兩道）。plugin 端 fail-closed advisory（吞例外回 "" + 審計事件，絕不拖垮 escalation 鏈）。 |
| 1.4 對外 I/O 安全 | **N/A**。零 `ToolInvocationPort` 外呼路徑；adapter 僅讀本機 SDD 產出檔，無網路 I/O。 |

**結論：四項全數維持/N/A/強化，無架構衝突、無凍結本體誤改、無安全弱化。**

---

## 2. 本輪增量設計 — W 項（≤3，純 AutoClaude 整合層）

### 2.1 W-14-1：`ITopologyDashboardSource` port + File adapter（fail-closed）— 升 A 軸橋接基石

**介面 delta**：
- 新 `autoclaude/core/ports/topology_dashboard.py`（contract tier）：`ITopologyDashboardSource` Protocol + `TopologyDashboard` frozen dataclass（markdown / operator_fingerprint / terminating / consistency_verified / audit_digest）+ `DashboardNotVerifiedError` + `canonical_graph_digest()`/`recompute_sidecar_digest()`（鏡像 SDD `_canonical_graph` 正規化雜湊慣例，供 import-free 獨立重算）。
- 新 `autoclaude/infra/adapters/sdd_topology_dashboard_adapter.py`（adapter tier）：`SddTopologyDashboardAdapter.load_dashboard()` 讀 Markdown + `.json` sidecar，三道 fail-closed 稽核後回 `TopologyDashboard`。
- `core/ports/__init__.py` 匯出新介面。

**LOC/契約影響**：port count_loc=75（contract≤400 ✓）、adapter=83（adapter≤400 ✓）；`.importlinter` 8 條全 kept（新 port 純 stdlib+typing 不破 core-purity；adapter 在 infra）。

**產物約定**（鏡像 ISpecSource）：`<path>` = `render_recursion_topology_dashboard` 的 Markdown；`<path>`.json = `render_json` sidecar + 補 `consistency.verified`(SDD 端 verify 結果)。

### 2.2 W-14-2：surface 進人類審批介面 — `EscalationDump` + `SddGovernancePlugin`

**介面 delta**：
- `models/escalation.py`：`EscalationDump` additive `topology_dashboard: str = ""` + `to_markdown()` 條件渲染「🧭 meta⁸ 互遞迴拓樸審批儀表板」段。
- `plugins/sdd_governance_plugin.py`：constructor 注入 `topology_dashboard_source` + `dashboard_artifact`（預設 `build/reports/recursion_topology_dashboard.md`）；PRE_RUN 自 `<workflow_path>/<artifact>` fail-closed 載入 → state；`load_signoff_dashboard()` / `pending_topology_dashboard()` 公開 API；snapshot/restore additive。
- `plugins/_sdd_topology_signoff.py`（**新 helper，DEF-01-009 紀律**）：把載入邏輯抽出，使 plugin 維持 plugin_entry≤250 餘量（plugin 由 250→243）。
- choke-point：`execution/escalation_dumper.dump_escalation_impl` + `plugins/checkpoint/{plugin,_escalation}` 線程 `topology_dashboard: str = ""`（4 個 `_save_escalation_dump` 呼叫點全經此單一匯流點，零改呼叫點）；`_resolve_topology_dashboard(runner)` 防禦性自 runner 上可選 `_sdd_governance_plugin` 取 pending 儀表板，缺則 ""（facade 路徑零退化）。
- `core/wiring._build_sdd_governance`：注入 `SddTopologyDashboardAdapter`（kernel 路徑 plugin 取得來源；wiring 為 core-purity 唯一豁免點）。

**LOC/契約影響**：plugin 243（≤250 ✓）、helper 27、escalation.py 150（data≤150 ✓，精簡後恰守）；`.importlinter` 8 kept（helper 非 Rule 1 independence 清單成員，plugin→helper 合法）。

### 2.3 W-14-3：e2e 橋接載具（真實 SDD 渲染器）+ fail-closed 攻防

**介面 delta**：純新增 `tests/integration/test_sdd_bridge/test_topology_bridge_e2e.py`（5 case）。以 subprocess（cwd=v0.05 namespace root，`-c` 使 sys.path[0]=cwd）跑 producer——用**真實** `RecursiveOperator.chain` + `render_recursion_topology_dashboard` + `verify_topology_consistency` 產出產物 → AutoClaude adapter 消費。SDD 目錄缺席則 skip（不阻斷 AutoClaude 獨立 CI）。

**壓測之未覆蓋路徑**：
1. **真實渲染器產物**消費（非 unit 合成 sidecar）→ 證 presenter 契約端到端成立。
2. **跨端 digest 同步**（AT-14-3-3）：AutoClaude 端獨立重算 digest **== 真實 render_json 的 audit_digest**——SDD 慣例若漂移即時失敗揭露。
3. 真實儀表板 surface 進 `EscalationDump.to_markdown`（舵手可見）。
4. **fail-closed 反視覺欺騙**：竄改真實產物 node rank（偽更良基圖）留原 digest → 獨立重算攔截；撤 verified verdict → 拒呈現。

---

## 3. RTM（需求→實作→測試 追溯矩陣）

| AC | 需求 | 實作（file） | 測試（AT） | 狀態 |
|----|------|-------------|-----------|------|
| AC-14-1 | 指揮官端以 read-only port 消費手腳渲染產物，不 import SDD 程式碼 | `core/ports/topology_dashboard.py`、`infra/adapters/sdd_topology_dashboard_adapter.py` | AT-14-1-1（round-trip）、AT-14-3-1（真實產物） | ✅ |
| AC-14-2 | 產物缺 / 未過 PY-2 verdict / sidecar 不自洽 → fail-closed 拒呈現（反視覺欺騙） | adapter 三道稽核 + `recompute_sidecar_digest` | AT-14-1-2~8（缺檔/缺 sidecar/未 verified/verified 缺失/digest 竄改/不可解析/nodes 畸形）、AT-14-3-4/5（竄改真實產物） | ✅ |
| AC-14-3 | 儀表板 surface 進人類審批介面（EscalationDump），舵手於指揮官端可見 | `models/escalation.py`、`SddGovernancePlugin` PRE_RUN 自載 + accessor、`dump_escalation_impl` resolver | AT-14-2-1/6（自載/渲染）、AT-14-2-8（resolver）、AT-14-3-2（真實 surface） | ✅ |
| AC-14-4 | 零退化：非 SDD / 無產物 / 預設 flag 全程無行為變更 | additive 欄預設 ""、PRE_RUN no-op、facade resolver 回 "" | AT-14-2-2/4/7（無產物/非 SDD/無儀表板 dump 不變）、全套 3112 0 failed | ✅ |
| AC-14-5 | 跨 session 持久 + DEF-01-009 紀律（擴充前拆 helper） | snapshot/restore additive、`_sdd_topology_signoff.py` 抽出 | AT-14-2-5（snapshot/restore round-trip）、LOC plugin 243≤250 | ✅ |

---

## 4. 零退化驗證矩陣（全項實測，2026-06-15）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3091 / 0 failed | **3112 passed / 122 skipped / 0 failed** ✅ |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept | **8 kept / 0 broken** ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | **violations=0** ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **OK**（第 14 port 收錄，CLAUDE.md 399≤400）✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | 全綠 + arch_fitness exit<2 | **exit 0**，v0.01:1478/v0.05:1499/scripts:24 ✅ |
| DAL 等價 | equivalence（pytest 內） | 三後端等價 | 含於 3112 ✅ |
| 五軌 TLC | （僅 FSM 變更時） | — | **未觸發**（零 `.tla`/`_HAPPY_PATH` 變更）N/A |

---

## 5. 缺陷處置（本輪）

- **DEF-01-009（watch，P3）觸發並處置**：W-14-2 擴充 `sdd_governance_plugin.py` 使 count_loc 自 224→250（恰貼上限）。依該 watch「擴充前先拆」紀律，抽出 `plugins/_sdd_topology_signoff.py` helper，plugin 降回 **243**（餘 7）。詳見 Defect_Log。
- 本輪**未新增**框架缺陷（B 軌 SDD 本體零改、git 潔淨）；既有 open 項（DEF-01-007/009、DEF-11-001、DEF-12-002）非本輪範圍，狀態於 Defect_Log 維持。

## 6. 結案四件套

1. 本檔 `docs/04_planning/AutoSDD_improving_14.md`（計畫/設計/RTM/矩陣）
2. `docs/06_quality/AutoSDD_ZeroTrust_Audit_14.md`（多專家審計+複審證據）
3. `docs/06_quality/AutoSDD_Defect_Log.md`（DEF-01-009 處置更新）
4. 產出碼：port + adapter + helper + 4 改檔 + 3 測試檔（見 §2 / git status）
