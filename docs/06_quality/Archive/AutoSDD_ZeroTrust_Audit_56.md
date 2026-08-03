# AutoSDD ZeroTrust Audit 56 — A 軌 spec_digest 閉環不變量 + 真實規模雙向 e2e

> **日期**：2026-06-24 ｜ **對應計畫**：[AutoSDD_improving_56.md](../04_planning/AutoSDD_improving_56.md)
> **軌道**：軌道① A 軌（協作橋接 L3→L4 進展）｜整合層 AutoClaude，免 Copy-on-Evolve、免五軌 TLC。
> **審查模式**：三鏡（Architect / SA-SD / QA）主樹並行獨立。**標的含 1 untracked 新測試檔 → 依 DEF-24-001 鐵律「審 untracked 新檔走主樹、禁 worktree」**（worktree 由 HEAD 建樹不攜 untracked，會看不到新檔產生假陰性）。
> **結論**：**三鏡全 OVERALL PASS、P0=P1=0**。零退化確認。

---

## 1. 階段一基線（parent 親跑，硬閘通過）

| 項目 | 命令 | 實測 |
|------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | **3248 passed / 122 skipped / 0 failed** |
| lint-imports | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken |
| LOC | `python tools/check_loc_budget.py` | violations=0（baseline 17032） |
| snapshot | `python tools/snapshot_sync.py --check` | OK |
| ci-gate（SDD） | `bash scripts/ci-gate.sh` | exit 0；v0.01:1478 / v0.21:1654 / scripts:127 |

三軸成熟度實測（三 Explore agent）：C=L5（相符）/ B=L3 / A=L3 → `L_合體=min=L3`，A 與 B 雙瓶頸。

## 2. 變更清單（git status，全屬 A 軌整合層）

```
 M AutoClaude/autoclaude/infra/adapters/sdd_to_playbook_adapter.py   # compile_tasks 填全 digest
 M AutoClaude/autoclaude/models/playbook.py                           # PlaybookTask 加 spec_digest 欄
 M AutoClaude/autoclaude/plugins/rtm_writeback_plugin.py              # _extract_digest 優先讀結構欄
 M AutoClaude/tests/plugins/test_rtm_writeback_plugin.py              # +4 case
?? AutoClaude/tests/integration/test_sdd_bridge/test_bridge_rtm_e2e.py # +3 case（untracked 新檔）
```
零 AISDLC_SDD/ 變更（免 TLC 成立）；`.perf_baseline.toml`/`.drift_log_history.jsonl` 經 pytest 碰動後已 `git checkout` 還原（保 diff 外科手術式）。

## 3. 三鏡結果

### 3.1 Architect 鏡 — OVERALL PASS（0 finding）
- **架構純潔性**：`spec_digest: Optional[str]=None`（playbook.py:30）純資料欄、無邏輯膨脹、無 God-object；playbook_runner thin facade 未動。
- **plugin 隔離**：rtm_writeback import 清單僅 `core.hookspec` + `core.ports.rtm_feedback`，**零 SddGovernancePlugin/infra import**；`_extract_digest` 以 `getattr(task, "spec_digest")` 讀屬性。`lint-imports` 8 kept / 0 broken。
- **LOC**：playbook.py 74/150（data）、adapter 342/400、plugin 107/250，violations=0。
- **持久化相容**：Optional=None YAML round-trip 相容；舊 playbook 缺欄自動 None。
- **雙向橋接一致性**：digest `spec.digest`(全)→`PlaybookTask.spec_digest`→`RtmCoverageReport.spec_digest` 單一真相源閉環；prompt digest8 人類提示保留、反解降 fallback。

### 3.2 SA-SD 鏡 — OVERALL PASS（P0=P1=0）
- **修復方向正確**：親讀三檔確認 digest 端到端不再經 prompt 截斷。
- **fallback 正確**：`test_writes_two_reports_for_sdd_playbook` 仍斷言 spec_digest=="abcdef12"（實跑 PASS）。
- **邊角案例實跑**（scratchpad）：None/空/純空白→""（`.strip()` 守）；多 task 取首個非空；結構欄空+prompt 有值→正確 fallback。皆 ✅。
- **e2e 真實性**：test_bridge_rtm_e2e 3 case 實跑 PASS，partial-coverage case 確驗逆向橋接非 happy-path-only。
- **P2-1（誠實性）**：要求計畫文件標「progress toward L4（2/3）」而非「達成 L4」、合體仍 L3 → **已於 improving_56.md §8 + 結論先行遵守**。P3-1（測試覆蓋 nice-to-have）無須阻擋。

### 3.3 QA 鏡 — OVERALL PASS（P0=P1=0）
- **focused 零退化**：3 路徑（rtm + bridge + adapter）實跑 **106 passed**。
- **lint/LOC**：8 kept/0 broken、violations=0，核實。
- **突變實證非空殼（Rule 9，QA 獨立親跑）**：
  - **M-W562**（`if False and structured`）→ `test_structured_field_carries_full_digest` + `test_structured_field_wins_over_divergent_prompt` **2 failed**、另 2 passed；Edit 還原後 **4 passed**。
  - **M-W561**（forward `spec_digest=None`）→ e2e `test_reverse_report_carries_full_authoritative_digest` **1 failed**；還原後 **1 passed**。
  - 兩突變還原後 `git diff autoclaude/` grep `if False`/`spec_digest=None` **CLEAN**、git status 回精確 5 檔。
- **收斂未破壞**：契約 8/0、git status 無 AISDLC_SDD 變更、無 perf/drift 殘留。
- **P2-001（數字不符）**：QA 報 focused 3 路徑 106 vs parent 先前報 218。**parent 核實化解**：106（3 路徑）+ 112（`test_yaml_import.py`，parent 為驗 YAML 向後相容額外納入第 4 路徑）= 218（4 路徑），兩數皆真實、命令範圍差異，**非虛假基線、非缺陷**。權威零退化數＝全套 **3255 passed**。

## 4. 零退化最終態（parent 親跑複核）

| 檢查 | 實測 |
|------|------|
| AutoClaude 全套 pytest | **3255 passed / 122 skipped / 0 failed**（floor 3248 + 7 新測試） |
| lint-imports | 8 kept / 0 broken |
| LOC | violations=0 |
| snapshot | OK |
| ci-gate（SDD，未動本體） | 維持階段一 exit 0 / v0.21:1654（git status 零 SDD 變更） |
| 五軌 TLC | N/A（未動 FSM/`*.tla`/transition_rules） |

## 5. 缺陷處置

| 缺陷 | 嚴重度 | 狀態 | 說明 |
|------|--------|------|------|
| **DEF-56-001** | P2 | **fixed@improving_56** | spec_digest 雙重脆弱漂移（全 sha256 截斷成 8 字元 + prompt 正則反解）→ 結構化欄單一真相源閉環。整合層就地修（免 Copy-on-Evolve）。 |

無新 open 缺陷。SA-SD P2-1（誠實標註）+ QA P2-001（數字核實）皆已於文件落實/化解，非遺留。

## 6. 收斂判定

三鏡全 OVERALL PASS、P0=P1=0；零退化（3255≥3248、0 failed）；架構契約 8 kept；未觸 SDD 本體與五軌 TLC。**A 軸 progress toward L4（補 2/3 缺口），合體仍 L3（誠實標註，未虛報級別）**。據實結案。
