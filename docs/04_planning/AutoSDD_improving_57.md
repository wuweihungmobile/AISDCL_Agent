# AutoSDD improving_57 — A①+B② 並進：合體成熟度 L3→L4（自動凍結 signoff + AUTO_RECOVERY 常態化）

> **軌道定位**：軌道① **A 軌（柱③雙向協作）＋ B 軌（柱②手腳 AISLDC_SDD）並進**。掌舵者 AskUserQuestion 裁定「**A①+B② 並進（真正推合體 L4）**」，明確 signoff 兩個治理/安全政策 flip。
> **下一份**：`AutoSDD_improving_58.md`（按需）。**日期**：2026-06-24。
> **結論先行**：🟢 **首次把合體成熟度 `L_合體=min(A,B,C)` 從 L3 推到 L4**——A 軸補齊最後缺口（goal→playbook 端到端**有界自動凍結 signoff**，IGoalFreezeGate，A:L3→L4）+ B 軸把 AUTO_RECOVERY 由 opt-in 翻轉為**常態化預設 ON**（流程自治 B:L3→L4），C 軸維持 L5 → **`L_合體=min(L4,L4,L5)=L4`**。**誠實標註**：兩個缺口本質皆為**治理/安全政策 flip**，已獲掌舵者明確 signoff；兩者皆**fail-closed 保留人工逃生口**（A：條件不足回退 🔴 人工 signoff；B：顯式 `SDD_ENABLE_AUTO_RECOVERY=0` opt-out）。**零退化**：AutoClaude pytest **3255→3265**（+10 A 軌測試、0 failed）；lint-imports 8 kept；LOC violations=0；ci-gate v0.01:1478 / **v0.22:1655**（≥floor v0.21:1654）/ scripts:127；chaos 34 passed（bounded_ratio==1.0 於預設 ON 成立）；五軌 TLC 0 violation。

---

## 1. 本輪輸入（自上輪繼承）

- 上輪＝improving_56（A 軌實作，spec_digest 閉環 + 真實規模雙向 e2e；補 A 軸 L4 三缺口中 2 個，合體仍 L3）。最新框架版 **v0.21**。
- 上輪結論／下輪建議：合體仍 `min(A=L3,B=L3,C=L5)=L3`；推 L3→L4 需 **A 軌第 3 缺口（無人工 FSM 凍結 signoff）+ B 軌 AUTO_RECOVERY 常態化**並進，後者動 FSM 行為恐觸 TLC、須審慎 signoff。
- 缺陷帳本 open 項：DEF-01-007（cc-switch GUI 環境）、DEF-01-009（LOC watch）、DEF-23-005 / DEF-19-001 / DEF-17-001 / DEF-53-001——全 P3/latent、框架側或環境工具，無乾淨可修之 in-repo 缺陷。
- 上輪審計遺留：無 partial。

## 2. 階段一：現況重偵察（Zero-Trust Re-Audit，parent 親跑）

### 2.1 零退化基線（硬閘）

| 項目 | 命令 | 實測 | floor | 結果 |
|------|------|------|-------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | **3255 passed / 122 skipped / 0 failed** | 3255 | ✅ 持平 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | — | ✅ |
| git 完整性 | `git log/status` | 乾淨停在 3a03be2，自 56 輪位元級零變更 | — | ✅ |

**硬閘**：無 failed、未低於 floor → 通過，准進階段二。

### 2.2 三軸成熟度實測（AutoSDD_Maturity_Rubric SSOT，git 證零變更沿用 improving_56 量測）

git 證自 improving_56（3a03be2）位元級零變更 → 三軸量表仍有效（無須重派三鏡）：

| 軸 | 實測級 | 距上一級缺口（本輪標的） |
|----|--------|----------------------|
| **C 引擎**（AutoClaude） | **L5** | （本輪不動） |
| **B 流程**（AISLDC_SDD） | **L3** | **AUTO_RECOVERY 預設 OFF（opt-in）**＝L4 骨架閘關著（`fsm_runtime.py:47` unset→False）→ **本輪翻轉常態化 = B:L3→L4** |
| **A 協作**（雙向橋接） | **L3** | spec 路徑 `_assert_frozen` 已自動化；**goal 路徑 GoalDecomposer.approve 仍 🔴 人工 signoff**（`goal_decomposer.py:125-144`）→ **本輪以 IGoalFreezeGate 有界自動化 = A:L3→L4** |

**上捲目標**：補 A、B 雙瓶頸後 `L_合體=min(L4,L4,L5)=**L4**`（首次推動合體針）。

### 2.3 兩缺口風險勘查（zero-trust，含對 Explore agent 輸出之主 agent 複核訂正）

| 缺口 | Copy-on-Evolve | 五軌 TLC | 本質 | 風險 |
|------|---------------|---------|------|------|
| ① A軌 自動凍結 signoff | ❌ 免（AutoClaude 整合層） | ❌ 免 | 治理：自動跳過既有 🔴 人工 signoff 閘（fail-closed 回退人工） | 中 |
| ② B軌 AUTO_RECOVERY 常態化 | ✅ **必走 v0.22**（`fsm_runtime.py` 屬 `tools/` 凍結本體區——訂正 Explore agent 誤判為免） | ⚠️ *.tla 未變但 safety-default 翻轉宜重跑確認 | 安全政策翻轉：FSM 自我修復免人工 | 中（實測 blast radius 小） |

**B軌 blast radius 實測（zero-trust 不臆測）**：以 v0.22 程式級翻轉預設後跑全套揭露——not-chaos 4 測 + chaos 2 測 = 6 個「不設 env 驅動 escalation 並斷言 ESCALATION」之既有測試受影響（與 auto-recovery 正交，顯式 opt-out 隔離即可）。**教訓**：先前以 `SDD_ENABLE_AUTO_RECOVERY=1` 跑全套得「0 fail」係**失真**——`test_auto_recovery_wiring` 的 tearDown `os.environ.pop` 清掉 shell 設的 env，後續 escalation 測試又看 unset→OFF 而誤過；真實 blast radius 須以程式級翻轉揭露（zero-trust 須對自己的量測）。

## 3. 階段二：增量設計

### <Architecture_Design_Review>（實作前）

1. **架構純潔性**：A 軌新 port `core/ports/goal_freeze_gate.py`（data tier）純 Protocol + frozen dataclass，**只收原語**（goal_hash/step_count/prompts），不 import execution → 保 core-purity contract #2；adapter `infra/adapters/goal_freeze_gate.py` duck-type 實作（鏡像 ToolInvocationAdapter 慣例）；GoalDecomposer 加 `auto_release`（~20 行，strategy tier ≤300 仍守）；playbook_runner thin facade 未動。B 軌僅改 `fsm_runtime.py` 一函式預設 + 測試對齊，無新 God-object。✅
2. **持久化相容**：A 軌不碰 PlaybookCheckpoint/DAL（純拆解期閘）；B 軌不碰狀態 schema（既有 FSM-STATE 檔完全相容，純 runtime 預設翻轉）。✅
3. **安全防護網**：A 軌 BoundedGoalFreezeGate 含注入嫌疑字元黑名單（⊇ CONDITIONAL/_DENY）深度防禦，**自動放行前再消毒**；B 軌 fail-closed 紅線零弱化（Rule 9.14 全守界不變）。✅
4. **對外 I/O 安全**：本輪不新增 `ToolInvocationPort` 外呼路徑（A 軌純本地拆解期判定、B 軌純 FSM 內部）。✅
5. **誠實性/零退化**：A 軌 `freeze_gate=None` 時 auto_release 拒絕（回退人工，零行為變更）；B 軌保留 opt-out。兩缺口皆 fail-closed 保留人工逃生口。floor: AutoClaude 3255 / v0.21:1654。✅

### 設計 delta

- **A 軌（缺口①，IGoalFreezeGate）— A:L3→L4**：
  - 新 port `core/ports/goal_freeze_gate.py`：`FreezeVerdict`（auto_approved/reason/conditions 可解釋）+ `IGoalFreezeGate.evaluate(*, goal_hash, step_count, prompts)`。
  - 新 adapter `infra/adapters/goal_freeze_gate.py`：`BoundedGoalFreezeGate` 有界策略——(1) 1≤步驟數≤max_auto_steps（預設 12=硬上限 24 之半，可下調不可上調）、(2) 無 prompt 含注入嫌疑字元、(3) 具 goal_hash；任一不過 → auto_approved=False + 理由（fail-closed）。
  - `execution/goal_decomposer.py`：加 `freeze_gate` 注入 + `auto_release(draft)`（gate 准予則以 `approver="auto:GoalFreezeGate"` 自動 signoff 釋出，否則 raise 回退人工；裁決全程入審計 XAI 可審）。**人工路徑（approve/release_for_execution）100% 保留**。
  - `core/wiring.py`：`build_goal_decomposer` 注入 `BoundedGoalFreezeGate()`。
- **B 軌（缺口②，AUTO_RECOVERY 常態化）— B:L3→L4，Copy-on-Evolve v0.22**：
  - `tools/fsm_runtime/fsm_runtime.py:_auto_recovery_enabled()`：unset→**True（預設 ON）**；顯式 falsy（0/false/no/off）→ False（保留 opt-out）。
  - 測試對齊：`DefaultOnNormalizationTests`（unset→ON 進 recovery + opt-out 仍停 ESCALATION）；6 個正交於 auto-recovery 之 escalation/tamper 測試顯式 opt-out 隔離。
  - **無 FSM 狀態/規則/`*.tla` 變更**（對 v0.21 逐位元零差異，僅翻轉「誰觸發既有邊」之 runtime 預設）。

## 4. 階段三：實作與雙重驗證

### A 軌（3 新檔 + 1 改 + wiring + 10 新測試）
`test_goal_decomposer.py` 由 21→**31 passed**（+10）：auto_release 無 gate 回退人工／小規模乾淨自動 signoff（審計 approver=auto:GoalFreezeGate）／超上限 fail-closed 拒絕（審計留拒絕痕 + 人工仍可放行）／注入 prompt 拒絕／傳原語非 execution 物件給 gate；BoundedGoalFreezeGate 4 case（界內准、空/超限拒、缺 goal_hash 拒、max_auto_steps 可下調不可上調）；wiring 注入閘。lint-imports 8 kept、LOC violations=0、ruff clean。

### B 軌（Copy-on-Evolve v0.22 + 1 改 + 測試對齊）
`scripts/copy_on_evolve.sh AISDLC_SDD_v0.21 AISDLC_SDD_v0.22`（git archive 純 tracked，匯出 860 檔、零 runtime 夾帶）。v0.22 not-chaos **1655 passed**（≥floor 1654）、chaos **34 passed**。

### 受控突變實證非空殼（Rule 9）
- **M-A1**（A 軌：停用 auto_release fail-closed 拒絕分支 `and False`）→ `test_auto_release_rejects_oversize_draft_fails_closed` + `test_auto_release_rejects_injection_tainted_prompt` **轉紅**，還原後 31 passed、grep `MUTATION` 零殘留。
- **B 軌 blast radius 即天然突變實證**：程式級翻轉預設 ON 使 6 個 escalation 測試**轉紅**（證這些測試真能捕捉 auto-recovery 行為差異），opt-out 隔離後復綠。

## 5. 階段四：CI 平價收斂（零退化矩陣，parent 親跑）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3255 / 0 failed | ✅ **3265 passed / 122 skipped / 0 failed**（3255+10） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept / 0 broken | ✅ **8 kept / 0 broken** |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | ✅ violations=0（port goal_freeze_gate data 49、adapter 72、goal_decomposer strategy 287/300） |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | ✅（Port 16→17 重生） |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0 | ✅ **exit 0**；v0.01:1478 / **v0.22:1655** / scripts:127 |
| chaos（R-9.9 有界） | `pytest -m chaos` | bounded_ratio==1.0 | ✅ **34 passed**（100 輪有界場景於預設 ON 跑過） |
| 五軌 TLC | `tlc_runner --module <各軌>` | 0 violation | ✅ 見 §5.1（formal 模型對 v0.21 逐位元零差異，仍實跑確認） |

### 5.1 五軌 TLC 證據（v0.22，safety-default 翻轉之審慎舉證）

> **Rule 9.18.1 義務性**：`formal/*.tla`/`.cfg` 與 `transition_rules.py`（`_HAPPY_PATH`）對 v0.21 `diff` exit 0 → **無重跑義務**。仍實跑五軌確認（safety-default 翻轉）：

| 軌 | DISTINCT | GENERATED | DEPTH | 結果 |
|----|----------|-----------|-------|------|
| SDD_FSM | 855 | 4706 | 14 | ✅ No error found |
| META_FSM | 13 | 24 | 6 | ✅ No error found |
| FLEET_FSM | 7 | 8 | 7 | ✅ No error found |
| COMPOSITION_FSM | 21 | 28 | 7 | ✅ No error found |
| OPTIMIZATION_FSM | 12 | 21 | 5 | ✅ No error found |

> 五軌 0 violation，與 v0.04 EVOLUTION 記錄之歷史值逐欄吻合（佐證 formal 模型對 v0.21 位元級不變、有界停機保持）。

## 6. RTM（本輪需求追溯）

| 需求 | 驗收標準 | 證據 | 狀態 |
|------|---------|------|------|
| R-57-1 A 軸自動凍結 signoff（A:L3→L4） | goal→playbook 有界自動 signoff + fail-closed 回退人工 | §4 A軌 + IGoalFreezeGate/auto_release 11 case | ✅ |
| R-57-2 B 軸 AUTO_RECOVERY 常態化（B:L3→L4） | 預設 ON + opt-out 保留 + Rule 9.14 零弱化 | §4 B軌 + DefaultOnNormalizationTests | ✅ |
| R-57-3 合體 L3→L4 | `min(A=L4,B=L4,C=L5)=L4` | §2.2 + §8 | ✅ |
| R-57-4 零退化 | pytest 3266≥3255、v0.22:1655≥1654、chaos 34、TLC 0 violation | §5 矩陣 | ✅ |
| R-57-5 回歸鎖非空殼 | M-A1 轉紅還原 + B 軌 blast radius 天然突變 | §4 突變實證 | ✅ |
| R-57-6 三鏡 zero-trust 全 PASS | Architect/SA-SD/QA 主樹獨立審查 | `AutoSDD_ZeroTrust_Audit_57.md` | ✅（見 §7） |
| R-57-7 fail-closed 人工逃生口 | A：條件不足回退人工；B：env=0 opt-out | §3 + §4 | ✅ |

## 7. 三鏡 zero-trust 結果

見 `docs/06_quality/AutoSDD_ZeroTrust_Audit_57.md`。標的含 untracked 新增檔（A 軌 2 新源碼 + B 軌 v0.22 新目錄）→ 依 **DEF-24-001「審 untracked 新檔走主樹」鐵律**三鏡皆主樹派發、禁 worktree。

## 8. 結論與誠實級別標註

本輪首次把合體成熟度 `L_合體=min(A,B,C)` 由 **L3 推到 L4**——A、B 雙軸瓶頸同時補齊：

- **A 軌（缺口①）**：以 `IGoalFreezeGate` 把 goal→playbook 端到端的人工膠水（GoalDecomposer 🔴 手動 signoff），升級為「**有界、可稽核、可解釋、fail-closed 回退人工**」的自動凍結 signoff——僅在可機械證明之有界條件（步驟≤12、prompt 無注入、有審計鍵）全成立時自動放行，否則回退人工。A:L3→**L4**。
- **B 軌（缺口②）**：把 improving_15 已接入主迴圈但 opt-in 的 AUTO_RECOVERY 翻轉為**常態化預設 ON**（流程自治由「失敗即停等人」升為「有界自動恢復 default」），fail-closed 紅線零弱化、保留 opt-out。B:L3→**L4**（Copy-on-Evolve v0.22）。

**🔴 誠實級別標註**：本輪達成 **`L_合體`=L4**（C 維持 L5）。兩缺口本質皆為**治理/安全政策 flip**，非純工程——已獲掌舵者 AskUserQuestion 明確 signoff（這即範本要求之 🔴 人工確認）。兩者皆 fail-closed 保留人工逃生口，未弱化任何架構/安全紅線。

**延後（justified，維持原狀態）**：DEF-01-007（cc-switch 環境）、DEF-01-009（LOC watch）、DEF-23-005 / DEF-19-001 / DEF-17-001 / DEF-53-001（framework-side latent/routed）。

**回流**：本輪 B 軌無新框架缺陷（純預設常態化）；A 軌整合層就地實作。框架本體改進落 `AISDLC_SDD_v0.22/` + EVOLUTION_LOG + CHANGELOG（人工 signoff＝掌舵者 A①+B② 並進裁定）。
