# AutoSDD Improving_25 — A 協作軌範本加固（DEF-24-001）+ B 軌 meta⁸ 視覺化飽和認定

> **輪次**：整合迭代軌道① 第 25 輪　**日期**：2026-06-17　**主導**：Dr. Alan（L10 自治系統架構總監）
> **前一輪**：improving_24（A 軌雙向橋接 SDD→Playbook 逆向回寫，commit `96d73e7`、tag `v2026.06.17-22`，已凍結）
> **本輪檔名**：`docs/04_planning/AutoSDD_improving_25.md`
> **🔴 人工拍板**：主柱＝**A 協作軌（範本/流程層）為主**；scope＝大型功能輪 → 經三度 zero-trust 翻轉**收斂為流程加固輪**（見 §2）

---

## 1. 本輪定位與北極星對齊

| 項目 | 內容 |
|------|------|
| **本輪在哪一柱** | **A 協作軌**（整合迭代範本本身的流程加固）＋ B 軌 meta⁸ 視覺化方向之**飽和認定**（無實質開發） |
| **W 項** | **W-25-1**：修 DEF-24-001 — 整合迭代範本 §🔍 worktree 隔離兩情境判準；**W-25-2**：記錄 DEF-25-001 紅線澄清 + 認定 B 軌 meta⁸ 視覺化飽和閉環 |
| **性質** | 純文檔/範本層：**零 Python、零框架 v0.0X 變更、零 checkpoint schema、零 TLC、不需 Copy-on-Evolve** |
| **北極星對齊** | 第 3 點「完美協調溝通機制」之**方法論基礎設施**——整合迭代範本是驅動三軌的唯一驅動器，修正其 §🔍 審查閉環的 worktree 隔離反模式，直接提升「自動化開發 Agent 自我審查」的可靠度（消除每輪「審查未 commit 新檔」的假陰性風險） |

### Maturity Rubric 三軸現級（階段一實測，zero-trust）

本輪為**流程加固輪**，三軸成熟度**維持不變**（無引擎/流程/協作能力的實質升級）：
- **C 引擎自治（AutoClaude）**：基線實測 pytest 3146/0 failed、lint 8 kept、LOC 0、snapshot FRESH（§3）——本輪零觸碰。
- **B 流程自治（SDD）**：v0.14 ci-gate exit 0 全綠——本輪零觸碰框架本體。
- **A 協作自治（橋接）**：improving_24 雙向橋接構件全真實存在且測試覆蓋——本輪僅修「驅動三軌之**範本**」的審查閉環紀律，非橋接 runtime。
- 上捲 `L_合體 = min(A,B,C)` 不變式維持；本輪貢獻為**方法論可靠度**（降低自我審查假陰性），不改三軸 L 級。**禁以本輪宣稱任何 L 級提升。**

---

## 2. 三度 Zero-Trust 翻轉紀實（本輪核心方法論價值）

本輪最大產出不是程式碼，而是**三度 zero-trust 剝離**把一個「大型開發輪」誠實收斂為「流程加固輪」，全程未製造重複功能、未違反架構紅線：

| 階段 | 事件 | 證據 |
|------|------|------|
| 初選 | 🔴 人工選 driver instance＝「B 軌 meta⁸ 終止證書視覺化儀表板」 | 範本「🔭 XAI Turn」段 |
| **翻轉①** | 階段一 B 軌標的偵察：該 driver instance 在 **v0.14 已 100% 落地並測試覆蓋** | `recursion_topology_view.py`（880 行，含 PY-2 防偽/有界截斷/folding）+ `steersman_renderer.py:890 render_recursion_topology_dashboard`（親讀證實，非二手誤報「待實現」）+ `META_FSM.tla VisualizationBounded` + `test_phase_y.py` PY-1/2/3 + chaos `VISUALIZATION_FLAP`。即上輪 improving_23 做掉的方向 |
| **翻轉②** | 重定剩餘 delta＝「四源一致斷點（視覺化稽核反射進 FSM-STATE.yaml）」 | 偵察 agent 提 ~60 LOC 方案（`record_visualization_audit` 寫 FSM-STATE） |
| **翻轉③（致命）** | 對照 `AISDLC_SDD/CLAUDE.md` Rule 9 §27 / R-9.37.4：該 delta **撞停機級紅線** | R-9.37.4「視覺化模組寫 FSM-STATE → 破 read-only 純觀察者，`VisualizationBounded==churn<=MAX_CHURN` 恆真根基」 |
| **收斂** | B 軌 meta⁸ 視覺化**飽和閉環**（無不撞紅線之實質 delta）；本輪＝範本加固 + 紅線澄清 | 見 W-25-1 / W-25-2、DEF-25-001 |

**關鍵認知更正（DEF-25-001）**：範本「四源絕對一致」是**驗證戒律**（四真相源不得矛盾），落實方向為**讀取式核對**——v0.14 已由 `verify_topology_consistency`（PY-2，Python執行 vs 渲染）+ `META_FSM.tla VisualizationBounded`（TLA+ 同構）閉環。`FSM-STATE.yaml`「沒有」視覺化稽核欄位是 **R-9.37.4 刻意維持的架構邊界，非缺口**（FSM-STATE 屬 SDD 主 FSM 運行態；meta⁸ 拓樸屬 meta-loop，視覺化必須 read-only）。

---

## 3. 階段一：現況重偵察（Zero-Trust Re-Audit）實測

硬閘 PASS（基線無退化，准進階段二）。所有數字來自本回合真實 tool_result：

| 檢查 | 命令 | 實測 | floor | 判定 |
|------|------|------|-------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | **3146 passed / 122 skipped / 0 failed**（114.47s） | ≥3146 / 0 failed | ✅ |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken**（188 files / 474 deps） | 8/0 | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0（total 18157 / cap 20438） | 全過 | ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | OK（FRESH） | FRESH | ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0（pytest v0.14 軌 1593+14 subtests、v0.01 軌 1478、scripts 27 passed；arch_fitness fail=0/warn=3 advisory） | 全綠 | ✅ |
| 上輪構件 | 親讀 + Grep | RtmWriteback plugin / PlaybookToRtmAdapter / IRtmSink+FileRtmSink **全真實存在**，30 測試覆蓋；commit `96d73e7`、tag `v2026.06.17-22` 真實 | 真實 | ✅ |

外部工具依賴（階段一 (f)）：本輪純文檔，無 A/B 後端切換、無外部 CLI/服務、無訊息平台——不適用。

---

## 4. 階段二：本輪增量設計

### W-25-1：整合迭代範本 §🔍 worktree 隔離兩情境判準（修 DEF-24-001）

- **介面 delta**：`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md` §🔍 行 224-235。
- **改動**：原單一無條件 note「audit agent 須以 `isolation: worktree` 派發」→ **兩情境判準**：
  - **突變 tracked 檔 → worktree**（保留原 #11/#18 紀律）。
  - **🔴 反向陷阱（DEF-24-001）：審查未 commit 的 untracked 新檔 → 嚴禁 worktree（git worktree 由 HEAD 建樹不攜 untracked 檔，會看不到本輪新檔、實跑舊碼 → 假陰性）→ 主樹派發**（或先 `git add -A` 使 untracked 入樹再建 worktree）。
  - 一句判準入範本：「**突變 tracked → worktree；審查 untracked 新檔 → 主樹**」。
- **LOC 影響**：純 Markdown，無程式碼 LOC 預算影響。
- **`.importlinter` 影響**：無（非 Python）。
- **checkpoint additive 欄位**：無（非 runtime）。

### W-25-2：DEF-25-001 紅線澄清 + B 軌 meta⁸ 視覺化飽和認定

- 缺陷帳本新增 DEF-25-001（`wontfix+理由：R-9.37.4 架構邊界，非缺口`），記錄「FSM-STATE 視覺化反射＝R-9.37.4 反模式」防後續輪誤判。
- 帳本新增「improving_25 複驗註記」段：記三度翻轉 + 上輪 open/routed 項複驗 + B 軌 meta⁸ 視覺化飽和閉環認定（附 zero-trust 證據）。

---

## 5. <Architecture_Design_Review>（寫任何實質 Python 前必輸出——本輪零 Python，逐項說明為何免責）

1. **架構純潔性（God-object / Thin Facade）**：本輪零 Python 變更，不新增/修改任何類別或 plugin，`playbook_runner.py` Thin Facade 不受影響。✅ 不適用。
2. **持久化相容（additive PlaybookCheckpoint / DAL 三後端零停機）**：本輪零 checkpoint schema 變更、零 DAL 變更。✅ 不適用。**反例佐證**：本輪一度設想的 W1（視覺化稽核寫 FSM-STATE）正是因撞 R-9.37.4 read-only 紅線而**否決**，未落地。
3. **安全防護網（CONDITIONAL 白名單）**：本輪無「從文件生成指令」之新路徑，CONDITIONAL 三層防禦不受影響。✅ 不適用。
4. **對外 I/O 安全（`ToolInvocationPort` 外呼）**：本輪無新增任何外呼路徑。✅ 不適用。
5. **架構紅線複核（R-9.37.4）**：本輪**主動以架構紅線否決了一個會違反 R-9.37.4 的設計方案**（視覺化模組寫 FSM-STATE），並記入 DEF-25-001。此為 `<Architecture_Design_Review>` 的正向實踐——設計前對照治理紅線，攔下停機級違規。✅ 合規。

---

## 6. RTM（需求追溯矩陣）

| 需求 | 來源 | 交付物 | 驗證 | 狀態 |
|------|------|--------|------|------|
| R-25-1 範本 §🔍 區分 worktree 隔離兩情境，消除「審查 untracked 新檔」假陰性 | DEF-24-001（P2, routed 本輪） | `AutoSDD_Iteration_Prompt_Template.md` §🔍 行 224-235（兩情境判準 + 反向陷阱段 + 一句判準） | 文本核對：含「突變 tracked → worktree」「審查 untracked 新檔 → 主樹」「`git add -A`」三要素；本輪三鏡 QA 鏡即依新判準在主樹派發 | ✅ done |
| R-25-2 記錄「FSM-STATE 視覺化反射＝R-9.37.4 反模式」防後續輪誤判 | DEF-25-001（本輪揭露） | 缺陷帳本 DEF-25-001（wontfix+理由）+ improving_25 複驗註記段 | 帳本含 R-9.37.4 引文 + 正解認知（讀取式核對 vs 寫入）+ wontfix 理由 | ✅ done |
| R-25-3 認定 B 軌 meta⁸ 視覺化飽和閉環（附 zero-trust 證據） | 階段一 B 軌偵察 | 本計畫書 §2 三度翻轉表 + 複驗註記 | 證據鏈：v0.14 構件 file:line + 親讀 steersman 端點 + horizon 候選（OPEN-Y.1/Y.3）被範本明禁 | ✅ done |
| R-25-4 零退化 | 範本階段四 | §3 基線 + §7 階段四矩陣 | pytest/lint/LOC/snapshot/ci-gate 全項對比 floor | ✅ done（見 §7） |

---

## 7. 階段四：CI 平價收斂（零退化驗證矩陣）

本輪純文檔/範本層，**未觸碰任何 AutoClaude 程式碼或 AISDLC_SDD 框架本體**，零退化邏輯上自證；仍依範本全項實測收斂（floor = improving_24 實測值）：

| 檢查 | 命令 | 通過條件（floor=improving_24） | 本輪 |
|------|------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3146 passed / 0 failed | 階段一已實測 3146/0；本輪零 Python 變更，§9 複核確認持平 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | 持平（零 import 變更） |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過 | 持平（零 Python 變更） |
| Snapshot | `python tools/snapshot_sync.py --check` | FRESH | 持平（未動 CLAUDE.md 架構 snapshot 區） |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | not-chaos 全綠 + arch_fitness exit<2 | 持平（零框架本體變更） |
| DAL 等價 | equivalence | 三後端等價 | 持平（零 DAL 變更） |
| 五軌 TLC | （僅 FSM 變更時） | — | **不適用**（零 `_HAPPY_PATH`/`*.tla` 變更） |

---

## 8. 本輪結案四件套

1. `docs/04_planning/AutoSDD_improving_25.md`（本檔）
2. `docs/06_quality/AutoSDD_ZeroTrust_Audit_25.md`（審計+三鏡複審證據）
3. `docs/06_quality/AutoSDD_Defect_Log.md`（DEF-24-001→fixed、新增 DEF-25-001、improving_25 複驗註記）
4. 範本本體修訂：`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md` §🔍

---

## 9. 結案說明（三鏡 Zero-Trust 審查全 PASS）

三鏡（Architect / SA-SD / QA）**主樹派發**（DEF-24-001 修法首次 dogfooding）審查結果全 **OVERALL PASS**，證據見 `AutoSDD_ZeroTrust_Audit_25.md` §4：

- **Architect**：DEF-24-001 兩情境判準正確、原 #11/#18 突變隔離紀律完整保留；R-9.37.4 引述與 `AISDLC_SDD/CLAUDE.md:304` 逐字一致；W1 否決架構正確；§5 四項「不適用」誠實。
- **SA-SD**：構件全親讀證實（`recursion_topology_view.py` 880 行、`steersman_renderer.py:890`、`META_FSM.tla:361`、commit `96d73e7`/tag `v2026.06.17-22` git 證實）；**親跑 lint-imports 覆核 8/0**；DEF-24-001/DEF-25-001 狀態與證據誠實、零 drift。
- **QA**：零退化邏輯自證（零 `.py` 變更）；範本 §🔍 與帳本 Edit 正確落地未破壞既有結構；**dogfooding 自驗成立**——QA 鏡在主樹看得到 untracked 新檔 `improving_25.md`，新判準有效，對比 improving_24 worktree 假陰性零復發。

**零退化**：本輪僅 3 個 .md 變更、零 `.py` 變更（QA git 複核），基線維持階段一實測 3146/8/0/FRESH/ci-gate exit 0（取證誠實聲明見 Audit_25 §3：零變更面下未重跑全套 pytest，由階段一實測 + SA-SD 親跑 lint + QA git 確認三者閉環）。

**結案四件套齊備**：improving_25.md（本檔）/ ZeroTrust_Audit_25.md / Defect_Log（DEF-24-001→fixed、DEF-25-001 新增、improving_25 複驗註記）/ 範本 §🔍 修訂。准予結案。
