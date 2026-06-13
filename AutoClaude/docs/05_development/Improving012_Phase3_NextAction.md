# Improving012 Phase 2 複審 + Phase 3 規格草擬後 Next Action

**日期**: 2026-06-13 | **狀態**: **Improving_012 全數結案**（A/B/C 三能力 + SCG-6 waiver + 流程護欄 #9/#10 全交付；2026-06-13 收尾輪雙方 zero-trust audit OVERALL PASS P0=0/P1=0）
**權威計畫**: [AutoClaude_Improving_012.md](../04_planning/AutoClaude_Improving_012.md)（SCG-0 凍結）

## 本輪結果摘要

### 1. Phase 0/1/2 zero-trust 複審（三方並行 Architect·SD / QA / SA·RTM·nightly）
- **結論**：OVERALL PASS，**P0=0 / P1=0**，僅 **5 條 P2（皆文件層）**。Phase 1/2 架構與功能正確、**修復方向正確**、nightly 程式正確。
- **親跑複核（主 agent，紀律 #17）**：full pytest **3,020 passed / 122 skipped**（92.71s，與聲稱基線一致）；importlinter 8 kept；LOC violations=0；snapshot OK；驗證鏡子測試 137 passed；nightly forensic log（run_id=040216）5 stage 全綠可引行號。
- **攔截點實證**：`_impl.py:297`（escalate 唯一 call site）/ `:368`（max_retries）親查確認。

### 2. P2 文件修復（已全修，純文件、零程式碼變更）
| 修復 | 內容 |
|------|------|
| SRD/ADR 行號漂移 ×6 | `_impl.py:278→297`、`:338→368`、ErrorBudget `:299-324→327-329`、`_loop_state.py:53-61→77-78`（alert_ladder resume）、`pg_state_repository.py:463→482`（load）、ADR-AGT-004 §2.1 攔截點 `:278→297` |
| 撤銷誤報 | Arch P2-1「byte-level 用詞」實已限定「控制流」（SRD:71/config.py:126），精確無需改；Arch P2-2「GoalProgressLedger 是 port」文件未如此宣稱 → 皆 agent 行號記憶誤差，撤銷 |
- **QA 複審修復**：純行號訂正未觸碰程式碼，pytest 3,020/122 不受影響、無破壞收斂閉環、原設計功能完整 → PASS。

### 3. Phase 3 規格草案（**DRAFT，待 🔴**）
- SCG-1：[SRD_AGT_Phase3_Autonomy.md](../02_architecture/SRD_AGT_Phase3_Autonomy.md)（F-A2 ToolInvocationPort + allowlist / F-A1 GoalDecomposer）
- SCG-2：[ADR-AGT-001](../04_planning/ADR/ADR-AGT-001-tool-invocation-security-gate.md)（工具安全閘）/ [ADR-AGT-002](../04_planning/ADR/ADR-AGT-002-decomposition-boundedness.md)（拆解有界性）
- 重要精化：Port 12→**13**（僅新增 `IToolInvocation`；`PreferenceStorePort` 已於 Phase 1 交付，凍結計畫 §2「10→12」描述須以實況校正）；`IBrain` 新增 `decide_decomposition`（capability 守門）；send_message 經 EventBus 委派既有 notification plugin。

## 進度更新（2026-06-13 開發輪）

- **🔴 SCG-1 + SCG-2 已簽署**（koalawu 2026-06-13，AskUserQuestion 互動核准後回填文件）：SRD_AGT_Phase3 v1.0 凍結、ADR-AGT-001/002 轉 ACCEPTED。
- **F-A2 ✅ 已交付**（tag v2026.06.13-05，commit cbb846d）：`IToolInvocation` port（ports 12→13）+ `ToolInvocationAdapter`（預設 deny + allowlist domain/子域比對 + 全程審計 log via IObservabilityPort + send_message 委派 `utils.notifier.notify`）+ `ToolInvocationConfig`（flag off）。閘門：full pytest **3,035/122**（+15 零回歸）、新模組 coverage **100%**、importlinter 8 kept、LOC=0、新檔 ruff 零違規。
- **實作精化留證**（SRD §0）：send_message 改委派 notifier（非裸 EventBus，因 EventBus 為 phase-based 非通用匯流排）；F-A2 adapter 尚未 wiring 接線（無消費者，避免 dead code），待 F-A1 GoalDecomposer 注入消費。

## F-A1 交付（2026-06-13，Phase 3 收尾）✅

- **交付**：`IBrain.decide_decomposition` + `BrainCapabilities.supports_decomposition`（additive 預設 False，capability 守門不靜默降級）+ MinimaxBrain/MinimaxClient/prompt_builder 拆解鏈 + `execution/goal_decomposer.py`（三道機械有界閘 ≤24`min()`鉗制／Kahn 無環／非空 prompt，超限拒絕不截斷不重試，1 次 Brain 呼叫非遞迴）+ `DecompositionDraft` frozen + 🔴 signoff 硬閘（`release_for_execution` 未簽拒絕 + 審計人/日期/goal hash）+ `wiring.build_goal_decomposer` 注入 F-A2 `ToolInvocationAdapter`（消費 allowlist，不再 dead code）。沿用既有 Playbook schema 產 YAML 草稿。
- **閘門**：full pytest **3,056/122**（前基線 3,035，+21 零回歸）、新模組 coverage 100%、importlinter 8 kept、LOC=0（goal_decomposer 機械錨定 strategy ≤300）、新檔 ruff 零違規。
- **三方 zero-trust audit**（Architect·SD / QA·RTM 並行）：OVERALL **PASS**，P0=0 / P1=0；2 項 P2 已修（① LOC tier 錨定 `check_loc_budget.py` strategy patterns 補 goal_decomposer.py；② evaluator_command 往返斷言補測）。QA 突變實證：signoff 閘與步驟數閘改 `if False:` → 對應測試 FAILED（證非套套邏輯）；收斂閉環未污染（playbook_runner/kernel 對 GoalDecomposer 零匹配）；ADR-AGT-002 有界性 + 人工棘輪原設計完整無弱化。
- **未採納 P2**（QA P2-1）：port `decide_decomposition` kw-only vs client positional — 與既有 `decide_correction`（port kw-only / client positional / adapter 橋接）同一模式，符合 codebase 慣例（Rule 11），非缺陷。

## Next Action（依凍結計畫順序）

1. ~~F-A1 GoalDecomposer~~ ✅ 已交付（見上）。**Improving_012 三能力 A/B/C 全數完成。**
2. ~~SCG-6（Phase 2 殘留）：alert_ladder.enabled nightly 連 7 天綠後轉 on~~ ✅ **2026-06-13 人工 waiver 結案**（koalawu 拍板提前轉正，預設改 on，免 7 天 soak）。已知行為影響：diverging 升級時序 2→3 次 evaluate（仍有界）；同步更新 `test_alert_ladder.py` + `test_escalation_on_diverging`、config.py docstring、計畫 §SCG-6 waiver、ADR-AGT-004 addendum、SRD_Phase2。設 `enabled=False` 可還原。**Improving_012 全數結案（含 SCG-6）。**
3. **backlog**（沿用，非阻斷）：ruff 鎖版全量清理、新模組 mutation 強度擴範圍、PG pg_real e2e、perf 載具偽陽性。~~舊 editable install 殘留~~ ✅ 流程問題 #9 結案。

## 2026-06-13 收尾輪（流程護欄 + 雙方 zero-trust 複審）✅

- **盤點結論**：Improving_012 三能力 A/B/C 已交付且 SCG-0 凍結（親跑複核屬實：full pytest 3,056/122、importlinter 8 kept、LOC=0、snapshot OK、editable 哨兵 PASS）。唯一殘留＝流程問題 #9(b)(c) + #10(a)(b) 之**預防性護欄**（CI 哨兵 / hook / 顯式 gate）。
- **本輪交付護欄**：#10a `loc_budget_check.py::check_claude_md_line_length`（單行 >800 codepoint → exit 2，僅 root CLAUDE.md，對齊 contract）+ 4 單元測試；#10b `local_ci_gate.ps1` gate 2b（顯式跑 contract test）；#9c gate 0（editable 哨兵）；#9b Nightly_Forensic_Discipline.md 紀律 #19（v1.5）+ CLAUDE.md 摘要同步。**full pytest 3,060/122**（+4 護欄測試，零回歸）、importlinter 8 kept、LOC=0、snapshot OK、CLAUDE.md 398 行（<400）。
- **雙方 zero-trust audit（Architect·SD / QA·RTM 並行背景代理）**：**OVERALL PASS，P0=0 / P1=0**。
  - QA：雙向突變實證證 4 護欄測試非套套邏輯（`if True:return 0`→`test_..._long_line_blocks` FAILED；`return 2`→3 個 pass-path 測試 FAILED）；A/B/C 7 檔 85 passed；RTM US-AGT-001~004 TC 覆蓋齊備、F-A1 五有界性測試斷言有效；工作樹突變零殘留。
  - Architect：F-A1 三道有界閘逐符號核對（`min()`鉗制 L78 / Kahn 無環 L214 / 非空 prompt L178 / 未簽 raise L140 / capability 守門 L99）；F-A2 預設 deny + `enabled is True` 防 Mock truthy；F-B flag-off byte-level 一致不污染收斂；F-C 符 Hexagonal；護欄三層縱深（edit #10a hook 已 wired settings.json / commit #10b gate / CI）鎖同一根因。
  - **修復方向正確、nightly 程式正確、執行過程與結果正確**經雙方獨立親跑複核確認。
- **新增 P2 backlog（前瞻性，非當前缺陷）**：
  - P2-1：`wiring.build_goal_decomposer` 無 CLI/execution 呼叫端——屬刻意設計（signoff 人工硬閘不全自動串接，adapter 已被 GoalDecomposer 構造式消費非 dead code）；後續若加 CLI entry 補「signoff 前零步驟執行」e2e。
  - P2-2：`ToolInvocationAdapter` host allowlist 比對目前對 stub no-op handler；未來注入真實 I/O handler 時補「畸形 URL / userinfo@host / IDN punycode」對抗測試防繞過。
  - P2-3（流程）：見流程問題 #11——並行 audit 含就地突變者改 `isolation: worktree` 起代理。

## 2026-06-13 驗證收尾輪（主 agent 獨立親跑複核，tag v2026.06.13-09）✅

- **觸發**：使用者要求再次確認凍結 + zero-trust 全面驗證「修復方向／nightly／執行結果是否正確」+ 是否仍有未完成項目。
- **主 agent 獨立親跑複核（非橡皮圖章，紀律 #17）**：full pytest **3,060 passed / 122 skipped**（99.56s，與 v2026.06.13-08 聲稱逐字一致）；importlinter **8 kept / 0 broken**；LOC violations=**0**（total=17508 baseline=17032）；snapshot OK；CLAUDE.md 398 行。git：HEAD=origin/main=`68cf6cb`、tag `v2026.06.13-08` 均已推遠端。
- **實碼抽查**：`goal_decomposer.py` 三道有界閘實際存在且有效 — `min()` 鉗制 L78、capability 守門 L99、Kahn 無環 L186-216、signoff/approver raise L128/142、非空 prompt L184。
- **結論**：凍結計畫範圍內項目（A/B/C + F-A1/A2/B1/B2/C1/C2/C3 + SCG-6 waiver + 護欄 #9/#10）**全數交付、已 commit、已 push，無未完成項目**。經使用者拍板（AskUserQuestion）：接受已推送之雙方 audit + 本輪獨立複核，於同 commit 打驗證 tag **v2026.06.13-09** 收尾，不重派冗餘第 5 輪稽核。殘留僅前瞻性 P2 backlog（P2-1/P2-2/流程 #11，皆需未來新增 CLI entry／真實 handler／worktree 隔離才有意義，非當前缺陷）。

## Audit / 觀察 backlog（沿用、未阻斷）
| 項目 | 說明 |
|------|------|
| ruff 鎖版 + 全量清理 | ~1,330 errors；ci.yml 不跑 ruff；本輪僅守新增檔零違規 |
| 新模組 mutation 強度 | alert_ladder/correction_verifier 僅行覆蓋 100%，待 Phase 3 搭 nightly mutation 擴範圍 |
| PG pg_real e2e | counters/preference adapter 有 mock 防線，真 PG e2e 待 `SD07_REAL_PG_E2E_ENABLED` |
| perf 載具偽陽性 | agent PowerShell 載具 CPU 膨脹（穩定模式）；建議 perf stage BLOCK 時自動 Bash 對照重測 |

## AISDLC_SDD_v0.01 開發流程問題記錄（下輪改善，依使用者指示）

| # | 問題 | 證據（本輪實證） | 建議改善 |
|---|------|----------------|---------|
| 8 | **SRD/ADR 引用之源碼 `檔案:行號` 於 LANDED 後隨源碼演進漂移，無機械校驗** | 本輪三方 audit 揪出 6 處行號漂移（`_impl.py:278` 實為 :297 等）；功能/測試全正確，純文件行號失準，違背 SRD §0「附 檔案:行號 且已驗證觸發」承諾與 nightly 紀律 #15 | 二擇一機械化：(a) SCG-4 交付時對文件內所有 `xxx.py:NN` 引用做靜態校驗（grep 該行內容是否仍含宣稱符號，漂移即 fail）；(b) **SRD/ADR 一律引用穩定的函式/類別名錨點，避免裸行號**（本輪 Phase 3 草案已採此法，延伸流程改善 #6/#7 的機械校驗精神） |
| 9 | **舊 editable install 殘留指向遷移前路徑，工作樹驗證易誤命中舊源碼** | F-A1 開發中發現 `pip show autoclaude` 之 Editable project location = 遷移前舊路徑 `D:\CursorProject\AutoClaude`（5/7 舊副本）；從 cwd 跑 `python -m pytest`/`python -c` 時 cwd 會 shadow 故正確，但 `python /tmp/xxx.py`（sys.path 不含 cwd）會誤命中舊副本 → 一度 ImportError 誤判新符號不存在。屬環境殘留非源碼缺陷，但違 nightly 紀律 #17「zero-trust 須雙向、可機械驗證者親跑複核」之載具一致性精神 | (a) `pip install -e .` 重指向本 repo 覆蓋舊 .pth，或移除舊 `D:\CursorProject\AutoClaude` 副本；(b) 驗證 SOP 明示「一律從專案 cwd 跑 pytest/`python -c`，禁 `python <repo 外路徑>.py`」；(c) CI/local_ci_gate 可加 `assert 'AISDCL_Agent' in autoclaude.__file__` 哨兵 — **✅ 2026-06-13 全數結案**：(a) editable 重指向 monorepo（哨兵 PASS）；(b) Nightly_Forensic_Discipline.md 紀律 #19 + CLAUDE.md 摘要同步；(c) `local_ci_gate.ps1` gate 0 editable 哨兵落地。 |
| 10 | **CLAUDE.md 累積敘事行反覆破 `test_claude_md_no_long_lines`（≤800 codepoint）contract，且 commit 前閘門未攔 → 交付聲稱與 committed 實況不一致** | 本輪零信任親跑揪出：committed F-A1（commit `c435425`）之 CLAUDE.md line 4（Status 行）=**815 字元 > 800**，contract test **實際 FAILED**，但 F-A1 交付文件聲稱「full pytest 3,056 passed」。屬 Phase 0 同型 P0（「CLAUDE.md:4 行長 842cp 破 contract」）**復發**。根因：Claude Code PostToolUse hook `loc_budget_check.py` 只查 CLAUDE.md **行數 ≤400**，**未查單行字元 ≤800**；後者僅在 pytest/CI 才失敗 → 編輯可過 hook 卻破 contract，且本機 commit 未跑全套即 push | (a) `loc_budget_check.py` hook 增「CLAUDE.md 單行 >800 codepoint → exit 2 阻斷」；(b) `local_ci_gate.ps1` 納入 contract test；(c) Status/v-note 行採短摘要慣例 — **✅ 2026-06-13 結案**：(a) hook `check_claude_md_line_length`（MAX=800 codepoint，僅 root CLAUDE.md，對齊 contract 口徑）+ 4 單元測試（雙向突變實證非套套邏輯）；(b) `local_ci_gate.ps1` gate 2b 顯式跑 contract test；(c) 慣例沿用（commit `74ecba7` 已修當次 815cp 回歸）。三層縱深（edit/commit/CI）鎖同一根因。 |
| 11 | **並行派 zero-trust audit 子代理時，QA 突變實證會暫時改寫活體源碼，與其他子代理/主 agent 的 pytest 同跑恐誤命中突變態假紅** | 本輪同時派 Architect/SD + QA/RTM 兩背景代理；QA 為驗 Rule 9 反套套邏輯需把 `check_claude_md_line_length` 暫改 `if True: return 0/2` 跑測試，期間 loc_budget_check.py 處突變態。本輪未實際撞紅（QA 改→測→還原為原子序、Architect 跑 pytest 時點未重疊），但屬 nightly 紀律 #18「mutation 須隔離樹、禁就地突變活體工作樹」精神在「agent 編排層」的延伸風險 | (a) QA 突變實證 SOP 明示「就地突變期間禁其他載具並行跑全套 pytest」，或突變於 git worktree 隔離分支（對齊紀律 #18）；(b) 主 agent 派並行 audit 時，凡含「就地突變」者改 `isolation: worktree` 起子代理；(c) 突變實證後主 agent 須複核工作樹零殘留（本輪已做：git status 僅 5 護欄檔 + 重跑 14 passed） |

---
**產出**: 主 agent（Claude Code）依 AISDLC_SDD SCG 流程執行；audit 取證見三方 agent 報告（行號/數字均經主 agent 親跑複核）。
