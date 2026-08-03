# AutoSDD ZeroTrust Audit 67 — A 軌雙向橋接加固（signal_class 分類 + 規格格式版本 fail-closed 閘）

> **對應計畫書**：`docs/04_planning/AutoSDD_improving_67.md`｜**日期**：2026-06-25｜**柱位**：A 軌
> **審查模式**：多專家 zero-trust（Architect / SA-SD / QA 三鏡並行，**主樹派發**——本輪變更為未提交 tracked 檔修改，worktree 由 HEAD 建樹看不到 → 依 DEF-24-001 判準「審查未提交/untracked 改動 → 主樹」）。

## §1 階段一基線（改動前實測，全錨定本 session tool 輸出）

| 項目 | 命令 | 結果 |
|------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | 3315 passed / 122 skipped / 0 failed（77.06s）|
| lint-imports | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken（195 files / 489 deps）|
| LOC / snapshot | `check_loc_budget` / `snapshot_sync --check` | violations=0（total=18999）/ OK FRESH |
| SDD ci-gate | `bash scripts/ci-gate.sh` | exit 0（v0.01:1478 / v0.26:1665 / scripts:129）|

**硬閘**：基線零退化、不低於上輪 floor 3315 → 准進後續階段。

## §2 階段四收斂（改動後實測）

| 檢查 | 結果 | 對比 floor |
|------|------|-----------|
| AutoClaude 全套 | **3327 passed / 122 skipped / 0 failed**（68.10s）| floor 3315 + 12 新測試（5 port + 1 plugin + 6 adapter），精確對齊 |
| lint-imports | **8 kept / 0 broken** | 持平 |
| LOC 分級 | **violations=0**（total=19054）；translation_learning 129/150、spec_source 68/400、sdd_to_playbook_adapter 286/400 | 全在預算內 |
| snapshot --check | **OK FRESH** | 持平 |
| SDD ci-gate | **exit 0**（v0.01:1478 / v0.26:1665 / scripts:129）| 持平（本輪零 SDD 框架變更）|
| 五軌 TLC | n/a（零 `*.tla`/`_HAPPY_PATH` 變更）| — |

## §3 變更面（git diff --stat，本輪僅改 tracked 檔 + 1 untracked 計畫書）

```
 AutoClaude/autoclaude/core/ports/spec_source.py            |  9 +++   （+SpecFormatVersionError）
 AutoClaude/autoclaude/core/ports/translation_learning.py   | 25 +++   （+signal_class +_classify_signal）
 AutoClaude/autoclaude/infra/adapters/sdd_to_playbook_adapter.py | 36 +++（+版本閘）
 AutoClaude/autoclaude/plugins/translation_learner_plugin.py |  1 +    （emit signal_class）
 AutoClaude/tests/infra/test_sdd_to_playbook_adapter.py     | 65 +++   （+6 版本閘測試）
 AutoClaude/tests/plugins/test_translation_learner.py       | 11 +++   （+1 emit 測試）
 AutoClaude/tests/test_translation_learning_port.py         | 48 +++   （+5 signal_class 測試）
```
**零碰**：FSM / `*.tla` / `_HAPPY_PATH` / checkpoint / DAL / ports 數量 / AISLDC_SDD 框架本體。

## §4 多專家 zero-trust 裁決（三鏡並行，主樹）

> 下列為三審查 agent 親跑/親讀回報摘要，主 agent 對可機械驗證之 finding 親自複核（[[no-fabricated-tool-output]]、Nightly #17 雙向 zero-trust）。

### 4.1 Architect（架構紅線）— **PASS（P0=0, P1=0）**
- 6 條架構紅線全 PASS：微核心純度（port 仍 stdlib + 同層 dataclass、adapter→core/ports 方向正確）、不創 God-object（`_classify_signal` 純函數無 self/IO；唯一新「類別」是 exception）、Thin Facade（`playbook_runner.py` 零變更）、fail-closed 一致性（未知版本真 raise、缺欄預設 1.0 放行）、紅線守恆（signal_class 純諮詢、status 恆 proposed、無 shell/外呼）。
- 親跑機械閘門：`lint-imports` **8 kept / 0 broken**（195 files / 489 deps）；`check_loc_budget` **violations=0**（translation_learning 129/150、spec_source 68/150[實歸 data tier]、adapter 286/400）。
- **插曲（已查清）**：Architect 首跑三檔組合出現 1 failed（`test_signal_class_both` 得 `execution_failure`），歸因「stale bytecode」清 cache 後 113 passed。**主 agent 追究**：該失敗態恰為 QA 鏡突變 (a)「both→execution_failure」，更可能是**並行 in-tree 突變撞車**而非 stale bytecode → 記 **DEF-67-001**（審查編排流程摩擦，P3，最終裁決正確零淨影響）。

### 4.2 SA-SD（規格↔實作一致性）— **PASS**
- 三測試檔親跑 **113 passed**（0.63s）。
- RTM 8 條逐條「需求→設計落點 file:line→測試函數 file:line」三段對齊，測試函數親驗存在且名實相符（R-67-7 實際拆兩函數、覆蓋面超出宣稱，屬正向偏差非虛報）。
- 設計三宣稱與實作逐行一致：`_classify_signal` 三類窮盡（both/execution_failure/translation_weak）；未知版本 `raise`；缺欄預設 1.0 + `declared` 旗標區分明示/兜底。
- 延後誠實性機械證實：`git diff --stat HEAD -- AISDLC_SDD/` **輸出為空**（本輪零碰 SDD 框架本體）；延後屬「需跨專案協調」正當類別、非藏債。
- scope：`git diff --name-only` 無 `.tla`/checkpoint/repositories 檔；Port 仍 18 個（僅既有檔加例外類 + 模組級私有純函數，無新 Protocol/port）。
- 向後相容：signal_class 預設 "" 與 spec 缺欄預設 1.0 皆有對應測試守護，既有 adapter 26 測試全綠。
- 次要建議（已採納）：§6 R-67-7 測試名對齊實際函數名——主 agent 已於結案前修正。

### 4.3 QA（測試真實性 + 零退化 + 突變驗證）— **PASS（4/4）**
- 獨立親跑全套 **3327 passed / 122 skipped / 0 failed**（71.11s）——與本輪宣稱數字相符、≥floor 3315。
- 新測試非空殼（Rule 9）突變驗證：(a) 改壞 `_classify_signal` 的 `"both"` 分支 → `test_signal_class_both_is_deepest_concern` 轉紅；(b) 把 `_check_spec_format_version` 的 `raise` 改 `pass` → `test_unknown_spec_version_fail_closed` + `test_version_audit_event_emitted_on_reject` 轉紅。證測試綁真實 business logic。
- 確定性測試為真逐欄比對（往復兩次呼叫 `first == second` + signal_class 列表比對）。
- 零退化：既有 select_proposals/adapter 測試全綠；additive 欄未破壞既有斷言。
- **突變還原證據（QA 附 + 主 agent 親自複核）**：`return "both"`/`execution_failure`/`translation_weak` 三分支完整、`raise SpecFormatVersionError` 完整、突變殘留掃描零命中、還原後三新測試檔複跑 **113 passed**。

### 4.4 OVERALL — **PASS（三鏡全 PASS）**
- Architect PASS（P0=0/P1=0）、SA-SD PASS（RTM 8 條三段對齊、零碰 SDD/tla/DAL/ports）、QA PASS（4/4，突變驗證 + 獨立 3327/0 + 主 agent 親驗還原乾淨）。
- 主 agent 對可機械驗證 finding 親自複核（Nightly #17 雙向 zero-trust）：QA 突變還原乾淨經親驗（三分支/raise 完整、零殘留、113 passed）；Architect「stale bytecode」插曲追究為並行突變撞車 → 入 DEF-67-001。
- **准予結案**。

## §5 缺陷帳本處置

- 本輪 A 軌**無新框架/程式碼缺陷**（純 AutoClaude 側 additive 增量，未觸發框架摩擦/文檔不符/hook 誤攔）。
- **新增 1 筆審查編排流程摩擦 DEF-67-001（P3，fixed@improving_67）**：三鏡並行派發時「會突變的 QA 鏡」與「唯讀 Architect 鏡」共用主樹致 Architect 首跑撞車假紅；最終裁決正確、零淨影響；紀律延伸＝含突變鏡之未 commit 審查輪須序列派突變鏡或先 commit 走 worktree。
- 延後一項（justified，非技術債遺失）：W-67-2 的「SDD 模板端 `spec-format-version` producer」延 improving_68（需 Copy-on-Evolve v0.27 + 跨 SDD 框架協調；本輪正向 adapter fail-closed 防禦已對未來不相容規格生效、既有規格零退化）。
