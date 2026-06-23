# AutoSDD improving_55 — B 軌實作：其他守門機制覆蓋度量（Copy-on-Evolve v0.20→v0.21）

> **軌道定位**：軌道① **B 軌**（手腳 AISLDC_SDD 框架本體 dogfooding，柱②）。本輪＝improving_54 設計探索 **signoff 後之實作輪**。
> **標的**：DEF-19-001（closed@improving_40）點名之後續「其他守門機制覆蓋度量」。實作 improving_54 §4 之 MVP：W-54-1 守門機制分類機讀 SSOT、W-54-2 誠實守門覆蓋證書。
> **掌舵者 signoff（improving_54 閘門）**：AskUserQuestion 核可「開 improving_55 實作」+ 分類落點「**per-rule yaml 欄**」+ E 類誠實排除確認。此即框架本體 RFC + Copy-on-Evolve 的 🔴 人工 signoff。
> **下一份**：`AutoSDD_improving_56.md`（按需）。**日期**：2026-06-24。
> **結論先行**：🟢 W-54-1 + W-54-2 經 Copy-on-Evolve **v0.20→v0.21** 落地。把守門「覆蓋」從不可能的『runtime 是否有效』誠實重構為『守門機制是否真實分類 + (escalation 類) catch 是否接線』靜態-結構覆蓋；manual 類誠實排除於自動分母、hook/lint_tlc/meta_loop runtime 度量 justified-deferred。**零退化**：ci-gate exit 0（v0.01:1478 / v0.21:**1654**〔v0.20 floor 1646 + 8 新測試〕/ scripts:127）。**FSM/`*.tla` 對 v0.20 逐位元零差異 → 不觸發五軌 TLC。** 修復 DEF-54-001。

---

## 1. 本輪輸入（自上輪繼承）

- 上輪＝improving_54（B 軌設計探索，藍圖 signoff）。最新框架版 v0.20（improving_53）。
- 缺陷帳本可動項：**DEF-54-001**（improving_54 設計期揭露：守門五分類僅存 archive 散文無機讀 SSOT）＝本輪 W-54-1 修復標的。其餘 routed/open（DEF-53-001 latent、DEF-01-007/009、DEF-17/18/19 已結）維持原狀態不動。
- 上輪審計遺留：無 partial。improving_54 設計輪三決策點已 signoff。

## 2. 階段一：現況重偵察（Zero-Trust Re-Audit，parent 親跑）

| 項目 | 命令 | 實測 |
|------|------|------|
| HEAD/工作樹 | `git status` | HEAD=`22782fe`；improving_54 三件套已落（未 commit） |
| **B 軌零退化基線** | `bash scripts/ci-gate.sh` | **exit 0**；v0.01:1478 / v0.20:1646 / scripts:127（與 improving_53 零漂移） |
| 五分類權威源 | 親讀 archive `AutoSDD_improving_39.md` §2 + v0.20 39 檔 R-*.yaml | A(7)/B(3)/C(3)/D(14)/E(12)=39，完整 partition（見 improving_54 §3.1） |
| escalation SSOT 常數 | 親讀 `fsm_runtime.py:231` | `_ESCALATION_ATTRIBUTABLE_RULE_IDS`＝{9.1,9.2,9.3,9.7,9.21,9.22,SELF-STRIDE}，與 A 類一致 |
| invocation 形態 | — | 純框架本體（yaml metadata + 純讀方法），無外部 CLI/GUI/API；headless 可驗 |

**硬閘**：基線無 failed、未低於 floor（v0.20 1646）→ 通過。

## 3. 階段二：增量設計落點（依 improving_54 §4 藍圖）

承 improving_54 設計：MVP ≤2 W 項，落 Copy-on-Evolve v0.21，不觸 `_HAPPY_PATH`/`*.tla`。

### <Architecture_Design_Review>（實作前）
1. **架構純潔性**：`rule_loader.Rule` 加 additive 欄、`fsm_runtime` 加 class 常數 + 純讀方法、規則 yaml 加 metadata；無 God-object、不動 transition/Thin Facade。✅
2. **持久化相容**：不碰 PlaybookCheckpoint/FSM-STATE/DAL；`_write_rule` round-trip **非空才寫**（同 failure_mode 潔淨度），避免對未分類規則注入空欄污染（DEF-11-002 家族）。✅
3. **安全防護網**：不新增「從文件生成指令」路徑、不弱化 CONDITIONAL。✅
4. **對外 I/O 安全**：不新增 `ToolInvocationPort` 外呼（純本地 yaml 讀）。✅
5. **誠實性紅線**：manual 類不灌假覆蓋率（auto_measurable 排除）；證書純讀 fail-closed；永不 set_maturity（R-9.20 #11）。✅

## 4. 階段三：實作與雙重驗證

### W-54-1：守門機制分類機讀 SSOT（修復 DEF-54-001）
- `rule_loader.py`：`Rule` 新增 `enforcement_mechanism: str = ""`；`_load_rule_file` 解析；`_write_rule` **非空才寫回**（置 test_ref 後、failure_mode 前；防 round-trip 對未分類規則注入空欄）。
- 39 條 active R-*.yaml 各補 `enforcement_mechanism`（escalation 7 / hook 3 / lint_tlc 3 / meta_loop 14 / manual 12，依 W-39-1）。
- `fsm_runtime.py`：class 常數 `_ENFORCEMENT_MECHANISMS`（enum）+ `_AUTO_MEASURABLE_MECHANISMS`/`_DEFERRED_RUNTIME_MECHANISMS`/`_NON_AUTO_MEASURABLE_MECHANISMS`。

### W-54-2：誠實守門覆蓋證書
- `FSMRuntime.comprehensive_governance_coverage()`（純讀、零副作用、零轉態、fail-closed、永不 set_maturity）：`by_mechanism` 分區 + `escalation_coverage`（沿用 catch-attribution，wired ⊆ escalation SSOT、100%）+ manual 誠實排除（`non_auto_measurable_mechanisms`）+ hook/lint_tlc/meta_loop 標 deferred + `denominator_note` + `unclassified_rule_ids`（非空＝分類缺口，fail-closed）。

### 雙重驗證（dev-build-test 循環）
- 焦點測試 `tools/fsm_runtime/tests/test_governance_coverage.py` **8 passed**（分類完整 / 五分類分布鎖 7-3-3-14-12 / **escalation 交叉鎖** / round-trip 保欄 / 證書分區加總 / escalation 沿用 catch-attribution / manual 誠實排除 / deferred 標記）。
- **Rule 9 受控突變實證非空殼**：
  - **M1**（竄改 R-9.1 分類 escalation→manual）→ 3 測轉紅（distribution / cross-lock / certificate partition），還原後綠。
  - **M2**（破 `_write_rule` round-trip：`if False and ...`）→ round-trip 測試轉紅（`'' == 'hook'` 失敗），還原後 8 passed、grep `if False` 零殘留。

## 5. 階段四：CI 平價收斂（零退化矩陣，parent 親跑）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| SDD 框架雙軌 + scripts | `bash scripts/ci-gate.sh` | exit 0；v0.21 ≥ floor 1646 / 0 failed | ✅ **exit 0**；**v0.01:1478 / v0.21:1654 / scripts:127** |
| 架構適應度 | arch_fitness --strict | structural fail=0 | ✅ fail=0（僅 FF advisory，不阻擋） |
| SSOT 4 lint | framework_status / skill_header / sync_exposed_skills / router_hook_coverage | 全 fresh/對齊/綠 | ✅ FRESH / 對齊 v0.21（45 檔戳記）/ 父層==LATEST 59 檔 / 三 event 全可達 |
| 其餘 shared-infra lint | gitignore / agent_template / collaboration / scenario_frequency / rfc | 全 ✅ | ✅（gitignore v0.21 block 已補） |
| Copy-on-Evolve 潔淨度 | `git add -A -n` would-add 審查 | 零 runtime 夾帶 | 由 Architect 鏡親驗 |
| 五軌 TLC | （僅 FSM/`*.tla` 變更時） | — | **N/A**（formal/ 與 transition_rules.py 對 v0.20 逐位元零差異，不觸發） |

> v0.21:1654 = v0.20 floor 1646 + 8 新 `test_governance_coverage`（只增不減，0 failed＝零退化）。

## 6. RTM（本輪需求追溯）

| 需求 | 驗收標準 | 證據 | 狀態 |
|------|---------|------|------|
| R-54-1 守門機制分類 SSOT（修復 DEF-54-001） | 39 條全分類 + lint + A 類與 escalation 常數交叉鎖 | §4 W-54-1 + test_governance_coverage（cross-lock/distribution case） | ✅ |
| R-54-2 誠實覆蓋證書 | 逐類靜態驗證 + E 類誠實排除 + fail-closed | §4 W-54-2 + 證書 case（manual 排除/deferred/分區） | ✅ |
| R-54-3 零退化 / Copy-on-Evolve v0.21 / 免 TLC | ci-gate exit 0 ≥1646；formal 零差異 | §5 矩陣 | ✅ |
| R-54-4 Rule 9 回歸鎖非空殼 | M1/M2 受控突變轉紅、還原綠 | §4 突變實證 | ✅ |
| R-54-5 四鏡 zero-trust 全 PASS | Architect/SA/SD/QA 主樹獨立審查 | `AutoSDD_ZeroTrust_Audit_55.md` | ✅（見 §7） |

## 7. 四鏡 zero-trust 結果

**Architect / SA / SD / QA 全 OVERALL PASS、P0=P1=P2=0**（詳見 `docs/06_quality/AutoSDD_ZeroTrust_Audit_55.md`）。v0.21 全新 untracked → 依 DEF-24-001「審 untracked 新檔走主樹」鐵律，四鏡皆主樹派發、禁 worktree。

## 8. 結論

improving_54 設計探索 signoff 後，本輪實作落地守門機制覆蓋度量 MVP（Copy-on-Evolve **v0.20→v0.21**）：W-54-1 把 W-39-1 五分類機讀化（39 條 `enforcement_mechanism` 欄 + rule_loader round-trip 保欄 + 與既有 escalation SSOT 交叉鎖，修復 **DEF-54-001**）；W-54-2 誠實守門覆蓋證書（`comprehensive_governance_coverage`，manual 誠實排除、hook/lint_tlc/meta_loop deferred、fail-closed、永不 set_maturity）。核心＝把不可能的「守門 runtime 有效性」誠實重構為可驗證的「守門機制存在性/接線」靜態覆蓋——直接承襲 DEF-18-001/19-001 家族「寧缺勿濫、不灌假信號」紀律。**零退化**：ci-gate exit 0（v0.01:1478 / v0.21:1654 / scripts:127）、SSOT 4 lint 全綠、FSM/`*.tla` 逐位元零差異不觸發五軌 TLC。**回流**：DEF-54-001 → fixed@v0.21（人工 signoff＝掌舵者 improving_54 AskUserQuestion）。

**延後（justified，維持原狀態）**：B/D 類 runtime 計數埋點（無消費者+Rule 2 speculative+meta_loop 恐觸 TLC）、DEF-53-001（latent）、DEF-01-007（cc-switch 環境）、DEF-01-009（LOC watch）。
