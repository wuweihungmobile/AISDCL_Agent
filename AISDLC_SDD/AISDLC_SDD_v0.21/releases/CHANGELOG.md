# AISDLC-SDD Framework CHANGELOG

**維護者**: AISDLC-SDD Framework Team
**最後更新**: 2026-06-24

---

## [v0.21] - 2026-06-24（Copy-on-Evolve 自 v0.20；v0.20 凍結唯讀）

> 使用者請求：推進整合迭代；improving_54 設計探索 signoff 後之實作輪（improving_55）。掌舵者 AskUserQuestion 核可「開 improving_55 實作」+ 分類落點「per-rule yaml 欄」+ E 類誠實排除確認。B 軌 dogfooding 推進 DEF-19-001（closed@improving_40）點名之後續標的「其他守門機制覆蓋度量」，無 A/C 軌新功能、無 FSM/`*.tla` 變更。

### 治理可觀測性（DEF-54-001，守門機制覆蓋度量）
- **守門機制分類機讀化（W-54-1）**：FSM-escalation catch 達結構天花板 7/7=100% 後，其餘 32 條（hook/lint_tlc/meta_loop/manual）守門覆蓋零度量、且 W-39-1 五分類僅存 archive 散文無機讀 SSOT。為 39 條 active 規則各補 additive 欄 `enforcement_mechanism`（escalation 7/hook 3/lint_tlc 3/meta_loop 14/manual 12），`rule_loader` 解析 + round-trip 保欄（非空才寫，同 failure_mode 潔淨度）。新增 `fsm_runtime` enum 常數 + lint 測試斷言「全分類 fail-closed」「五分類分布鎖」「**escalation 類 yaml 與 `_ESCALATION_ATTRIBUTABLE_RULE_IDS` 交叉鎖防兩 SSOT 漂移**」。
- **誠實守門覆蓋證書（W-54-2）**：`FSMRuntime.comprehensive_governance_coverage()`（純讀、fail-closed、永不 set_maturity）把「覆蓋」從不可能的『守門 runtime 是否有效』誠實重構為『守門機制是否真實分類 + (escalation 類) catch 是否接線』靜態-結構度量；manual 類誠實排除於自動分母、hook/lint_tlc/meta_loop 標 deferred（justified：無消費者+Rule 2+meta_loop 恐觸 TLC），不灌假覆蓋率（DEF-18-001 寧缺勿濫家族）。
- **回歸鎖**：`test_governance_coverage.py` 8 case，受控突變實證非空殼（Rule 9）。

### 驗證
- 見 improving_55.md §階段四（parent 親跑 ci-gate exit 0、≥ floor v0.20:1646、四鏡 zero-trust）。**FSM/`*.tla` 對 v0.20 逐位元零差異 → 不觸發五軌 TLC。**

---

## [v0.20] - 2026-06-24（Copy-on-Evolve 自 v0.19；v0.19 凍結唯讀）

> 使用者請求：推進整合迭代；掌舵者 AskUserQuestion 拍板「B 軌 清 routed RFC（v0.20）」＝清償上輪 routed 框架本體 RFC **DEF-CLDREV-030**（improving_50 第八輪 SA 鏡 F-02 揪出之 `hub_sync.py` 對外 yaml 缺大小上限深防禦缺口）。B 軌 dogfooding，無 A/C 軌新功能、無 FSM/`*.tla` 變更。

### 安全強化（DEF-CLDREV-030，對外輸入域記憶體 DoS 深防禦）
- **`hub_sync.py` 對外/快取 hub yaml 大小上限**：`safe_load` 已擋 `!!python/object` RCE，但 PyYAML 無 document-size／alias 展開上限 → 惡意/錯置 hub 之超大或深巢狀 yaml 理論可記憶體耗盡。新增模組常數 `MAX_HUB_FILE_BYTES = 1 MiB`（可由 registry `sync_policy.pull.max_file_bytes` 覆寫）+ `HubContentTooLarge(HubConfigError)` + 純函式 helper `_read_text_bounded()`，套用於**僅 3 處對外不受信讀取**（L334 pull stamp 的 hub rules yaml＝主攻擊面 fail-soft skip+audit；`diff()` cached 內容；`promote()` 可為 cached 路徑＝fail-closed 不得升入信任階梯）。PR-gated 本地 registry 與自寫且累積增長之 audit log 刻意不 cap。
- **registry 自我文件化**：`knowledge/hub-registry.yaml` 補 `sync_policy.pull.max_file_bytes: 1048576`（值＝常數預設）。
- **回歸鎖**：`TestHubFileSizeCap` +8 case，3 anchor 經受控突變實證非空殼（Rule 9）。

### 驗證
- 完整 `bash scripts/ci-gate.sh` **exit 0**：**v0.01:1478 / v0.20:1646（v0.19 1638 + 8 新測試，零退化）/ scripts/tests:127**；arch_fitness fail=0；SSOT 4 lint 重生後全 ✅（FRAMEWORK_STATUS fresh、skill_header 對齊 v0.20、skills 鏡像==LATEST 59 檔、router_hook_coverage 綠）；gitignore v0.20 block 已補；Copy-on-Evolve 859 tracked 檔零 runtime 夾帶；四鏡 zero-trust 複審 OVERALL PASS。**FSM/`*.tla` 逐位元零差異 → 不觸發五軌 TLC。**

---

## [v0.19] - 2026-06-22（Copy-on-Evolve 自 v0.18；v0.18 凍結唯讀）

> 使用者請求：「AISDLC_SDD_v0.xx 中 .claude 的 hooks 與 skills 是否都可完整使用，徹底驗證並做架構調整」。Architect/SA-SD/QA 三鏡 zero-trust 審查「monorepo 根 session 下 .claude hooks/skills 可用性」→ 結論架構本體健全，4 項邊角修復（整合層 DEF-43-008，B 軌 dogfooding，無 A/C 軌新功能、無 FSM/`*.tla` 變更）。掌舵者 AskUserQuestion 拍板「立即開 v0.19 全修」。

### 修正（4 項；git advisory hook 入口 + 安裝器 + settings 元資料 + shared-infra lint）
- **DEF-A（P2）drift hook repo-root 對稱化**：`.claude/hooks/post_commit_drift.py` 原裸 `parents[2]` 指向版本目錄（monorepo 收斂後無 `.git`），致 drift 告警靜默蒸發 + `compute_drift` 掃錯目錄；對稱於姊妹 `closure_evidence.repo_root_from()`，分離 `_PKG_ROOT`（import 根）與 `REPO_ROOT`（git toplevel 真實 monorepo 根）。
- **DEF-C（P3）安裝器動態 LATEST**：`tools/install_hooks/install_post_commit.{sh,ps1}` 原寫死 drift→v0.01／closure→v0.12（致修了 drift bug 也裝不到、與「指向 LATEST」原則不一致）→ 改動態解析 LATEST（對齊 ci-gate `sort -V | tail -1`），修復立即生效、永不再 stale。
- **D-1（P3）settings.json 標頭版本中性化**：`.claude/settings.json` description 原滯留「AISDLC-SDD v0.01 — Phase D…」（全 18 版 stale 標頭，DEF-AGTREV-021 同類）→ 版本中性描述實際 hook 行為。
- **DEF-B（P3）router 覆蓋機械守護**：新增 `scripts/router_hook_coverage_lint.py`（+16 test），斷言最新演化版宣告之 CC hook event ⊆（root router `_HOOK_MAP` 涵蓋 ∩ 根 settings wire），不可達即硬閘擋下；接入 `ci-gate.sh` 杜絕未來新增第 4 種 CC event 卻忘改根 router/settings 致治理 hook 靜默失效。

### 驗證
- 完整 `bash scripts/ci-gate.sh` 全綠：**v0.01:1478 / v0.19:1611（與 v0.18 同數，零退化）/ scripts/tests:109**（93→109，+16 router lint test，實測）；arch_fitness fail=0；8 道 shared-infra lint（rfc/gitignore/agent_template/collaboration_symmetry/scenario_frequency/FRAMEWORK_STATUS/skills SSOT/**router_hook_coverage**）全 ✅；Copy-on-Evolve would-add 零 runtime 夾帶（.gitignore 補 v0.19 block）；三鏡 zero-trust 複審 OVERALL PASS。

---

## [v0.18] - 2026-06-22（Copy-on-Evolve 自 v0.17；v0.17 凍結唯讀）

> 使用者臨時請求：agent/* 全面 SDD 與架構符規審查並修復（B 軌 dogfooding，無 A/C 軌新功能）。Architect/SA/SD/QA 四專家 zero-trust 審查 v0.17 全 26 個 agent YAML → 套用 11 項可自主修復。

### 修正（11 項，純 agent 定義檔/registry/文檔，無 FSM/`*.tla` 變更）
- **pm-planner 幻影 id → pm-po**：`agent/specialized/sdd-orchestrator-zh.yaml` registry + `tools/fsm_runtime/subagent_contract.py` 雙端對齊（原登記名與實際 agent id 不符、契約測試自指故 CI 盲區）。
- **icon 去碰撞**：🔍 三方撞 → BA 🧭 / code-analyzer 🔬 / qa-tester 維持 🔍。
- **agent.version 統一 v0.18**：原 v0.01/02/03 混雜（26 檔含模板）。
- **補 dependencies 區塊**：compliance-officer / security-engineer（子鍵留空，不引新 broken path）。
- **SCG-4/5/6 角色閘門別名化**：自創閘門佔用官方 SCG 槽位 → RG-TEST/RG-SEC/RG-PERF（22 處；`spec_gate` 純描述性、零 runtime 解析）。
- **RTM 觸發 Stage → SCG 編號**：對齊 SDD_Core_Principles（FRD後=SCG-0/SRD後=SCG-1/測試計畫後=SCG-4）；修 04.sa-analyst rtm_at_column 自相矛盾。
- **qa-automation `# planned` 路徑值汙染修正**；**generate_adr template → docs_template/sdd/adr**；**WRONGDIR template 3 處重指**（目標皆確認存在）。
- **sd-web/sd-mobile-architect 孤兒載入**：INIT greenfield 加 extends 條件式載入。
- **README/INIT 計數更正 + 雙 schema 宣告**：14→19 specialized（含 5 系統級 runtime agent）、補列 sdd-* runtime、runtime schema 說明、合規稱呼統一。
- **broken `template_path` 全面重新接線（方案一 + 配套）**：67 rewire 至既有最接近模板 + 26 Category D 正規化（移除 `../` 統一根相對）+ 9 確無對應刪除；功能性 broken ~75→**0**。新增 `scripts/agent_template_lint.py` 硬閘並接入 `ci-gate.sh`。

### 驗證
- 完整 `bash scripts/ci-gate.sh` 全綠：**v0.01:1478 / v0.18:1611 / scripts/tests:56**；arch_fitness fail=0（exit<2）；RFC/gitignore/agent_template 三 lint 全 ✅；26/26 agent YAML safe_load 通過、template broken=0；獨立 zero-trust 複審 OVERALL PASS。

### 同日收尾補強（2026-06-22，使用者再次請求；獨立 zero-trust 重審揪出首版未竟殘留）
- **DEF-AGTREV-005/008**：首版「broken=0」僅在 lint 窄範圍成立。實揪 36 條 broken template（12 core 裸名 `template_path` + 19 `sdd_skills.*.template` 誤指 `docs/` 之 `.md` + 3 `dependencies.templates` 裸名 + **QA 閉環複審補抓 2 條 `.yaml` 誤指 `docs/`**）→ 全數 rewire 至既有 `docs_template/` 模板（1 條無對應刪欄）；`agent_template_lint` 加 `BARE`（涵蓋 md/yaml/yml/json）+ `dependencies.templates` YAML 雙檢查封閉盲區。
- **DEF-AGTREV-006**：4 specialized persona agent（qa-mobile/qa-web-tester、sd-mobile/sd-web-architect）補 `collaboration_rules`；`collaboration_symmetry_lint` 加 persona-schema presence 檢查防復發。
- **DEF-AGTREV-007**：`test_subagent_contract` 三處「24 passed」校正為實測 19；README 同檔計數矛盾（樹狀圖/Q&A 14 vs 19）校正。
- **新測試**：`test_agent_template_lint.py` 9 case（前次零測試）+ `test_collaboration_symmetry_lint.py` +3 case。
- **驗證**：完整 ci-gate **exit 0**：v0.01:1478 / v0.18:1611（零退化）/ scripts/tests:**81**；窮盡掃描 template broken=0；DEF-AGTREV-001~008 全閉。

### 三度收尾（2026-06-22，使用者第三次請求；四鏡 zero-trust 重審揪出語意層殘留）
> 派 Architect/SA/SD/QA **四鏡**獨立重審全 26 agent + 3 根文檔。機械閘門（兩 lint + SSOT fresh）皆綠，聚焦 lint 抓不到的語意/架構符規缺口。查證 5 類真實殘留（fixed）+ 5 類親驗判定 by-design（不修、誠實記分歧）。

#### 修正（5 項，純 agent 定義檔/根文檔，無 FSM/`*.tla`/test 變更）
- **DEF-AGTREV-009（P1）spec_gate 號碼/名稱張冠李戴**：7 處「SCG-1 Requirement Spec Gate」（官方 SCG-0=Requirement、SCG-1=Design）→ 分情境修：SRD 產物（`04.sa-analyst` 2 處）改「SCG-1 **Design** Spec Gate」；FRD/PRD/RTM 產物（`04.sa-analyst` 2 處 + `03.pm-po` + `technical-writer` 2 處）改「SCG-0 Requirement Spec Gate」。
- **DEF-AGTREV-010（P2）scenario_usage 分母 /9→/10**：場景實為 10（devops/mapping 已 /10）→ 15 live agent + `AGENT_PHASE2_UPDATE_GUIDE` 14 處範例全修，保留分子。
- **DEF-AGTREV-011（P3）sa-analyst 漏 Migration**：9/9→10/10 + supporting 補 Migration（sd-architect 為主力、sa 需求面支援）。
- **DEF-AGTREV-012（P3）architect SRD 模板重複行**：`sd-web`/`sd-mobile-architect` 各去重一條（lint 盲區：路徑存在故漏抓）。
- **DEF-AGTREV-013（P2）core/README SCG-5 owner 誤標 qa-tester**：官方 owner=qa-lead → 改「RTM 覆蓋率支援（SCG-5 閘門 owner：qa-lead）」。

#### 親驗判定 by-design / 不修（與專家分歧之誠實記錄，Rule 7）
- **A-01 駁回**：4 個 extends-agent（sd-web/mobile、qa-web/mobile）缺 document_responsibilities/supported_workflows 係 `extends` base 繼承，非缺漏（補上反致 base 漂移）。
- **A-04 駁回**：「21 個 Agents」= 21 persona-schema agent（Phase 2 對象，5 runtime 不在內），歷史正確。
- **A-05 defer**：.md 標頭 v0.01 漂移屬文檔新鮮度（agent.version 機械 SSOT 已全 v0.18），需逐處人工判歷史 vs 現況，列觀察項。
- **A-02 / SD-06**：compiler schema 歸類近似、workflow_name 為邏輯標籤（綁定走 workflow 端 agent_binding）—— 皆 by-design。

#### 驗證
- 完整 `bash scripts/ci-gate.sh` **exit 0**：v0.01:1478 / v0.18:1611（**零退化**，agent YAML/.md 非 pytest 標的）/ scripts/tests:81；arch_fitness fail=0；兩 agent lint + SSOT fresh 皆 ✅；26/26 agent YAML safe_load OK；QA 複審鏡實測 5 修復項全成立、無誤傷合法 SCG 引用、同類 0 殘留。DEF-AGTREV-009~013 全閉。

### 四度收尾（2026-06-22，使用者第四次請求；四鏡 zero-trust 重審 + 掌舵者 SSOT/scope 裁決）
> 派 Architect/SA/SD/QA **四鏡**主樹並行獨立重審。**Architect 鏡全乾淨**（schema 五類零殘留）；三 lint + SSOT 皆綠。揪出 3 類殘留（DEF-AGTREV-014~016），兩項經掌舵者拍板（Q1 frequency「統計段為唯一 SSOT 全對齊」、Q2 協作「補對稱邊 + 擴 lint」）。

#### 修正（DEF-AGTREV-014~016，純 agent 定義檔/共用 lint/文檔，無 FSM/`*.tla` 變更）
- **DEF-AGTREV-014（P2）collaboration upstream 反向斷鏈 + lint 盲區**：`02.ba` upstream←PM/PO 但 `03.pm-po` 結構化 collaboration_rules 完全不提 BA（其 mermaid/review_participants 確有協作）；symmetry lint 只查 down→up + peer~peer → pm-po 補 `downstream→BA`，`collaboration_symmetry_lint` 加 upstream 反向檢查（接受 down 或 peer 為合法對側）+2 test。SD-1（sd↔pm-po 視角差）判 by-design。
- **DEF-AGTREV-015（P2）scenario_usage frequency 與 SSOT 系統性漂移**：integration「1/10 vs 自列 4」內部矛盾 + 6 agent off-by-one + pm-po 計入非法場景「Sprint Planning」+ sd-architect 漏 Migration（notes 自稱 9 卻寫 8）；全框架無 frequency 守門 → 掌舵者裁定統計段為唯一 SSOT，**8 agent 全對齊**（freq 分子＝統計段＝清單項數三者一致，逐場景表交叉核對成員）；新增 `scripts/scenario_frequency_lint.py`（SSOT 跨源 + 內部一致雙檢查）+6 test + 接入 ci-gate；mapping doc Refactoring supporting 補 qa-automation 收斂雙視圖。
- **DEF-AGTREV-016（P3）文件交叉引用/標頭殘留**：`README.md:244` 行號 71→76；`core/README.md:68` 複數 `agents/`→`agent/`（斷鏈）；`core/README.md` 標頭 v0.01→v0.18；`AGENT_PHASE2_UPDATE_GUIDE.md:402` 離群 `/9`→`/10`。

#### 驗證
- 完整 `bash scripts/ci-gate.sh` **exit 0**：v0.01:1478 / v0.18:1611（**零退化**）/ scripts/tests **81→89**（+2 collaboration upstream 反向 case + 6 frequency case）；6 lint 全 ✅（含新 `scenario_frequency_lint`）；arch_fitness fail=0；FRAMEWORK_STATUS fresh；26/26 agent YAML safe_load OK；8 agent frequency 三者一致（QA 複審鏡親數吻合）；兩新/擴 lint 經突變實證非空殼。DEF-AGTREV-001~016 全閉、零 routed 殘留。

---

## [v0.17] - 2026-06-18（Copy-on-Evolve 自 v0.16；v0.16 凍結唯讀）

> AutoSDD_improving_39 — B 軌 dogfooding 度量誠實化（無 A/C 軌新功能）。DEF-39-001 fixed：catch_attribution_coverage 分母正當性透明化。

### 背景（DEF-19-001 候選枯竭 → 轉分母正當性調查）
- 階段一機械證實 `fsm_runtime.py` 9 個生產 escalation 落點＝7 已接線 + 2 正交無規則（implementation-budget-exceeded / spec_patch unable-to-draft），DEF-19-001 沿「1:1 落點接線」乾淨候選**枯竭**、7/39 達結構天花板。
- **W-39-1 分類調查**：39 條非 deprecated 規則僅 **7 條** catch-可歸因（R-9.1/9.2/9.3/9.7/9.21/9.22/R-SELF-STRIDE，與 `rules_with_failure_mode` 精確吻合）；其餘 32 條由 hook(3)/lint·TLC(3)/meta-loop guard(14)/人工·advisory·憲法(12) 守門＝本質非 FSM-escalation catch-可歸因（catch_count 恆 0 屬設計使然非缺口）。

### 新增（W-39-2 純 additive，DEF-39-001 fixed）
- `tools/fsm_runtime/fsm_runtime.py` — class 常數 `_ESCALATION_ATTRIBUTABLE_RULE_IDS`（7 條 SSOT，drift-proof 註解）；`rule_fire_telemetry_stats()` 於 `catch_attribution_coverage` additive 加 `escalation_attributable_rule_ids` / `escalation_attributable_total`(=7) / `escalation_scoped_coverage_pct`(=100.0) / `non_escalation_governed_total`(=32) / `denominator_note`。
- `tools/fsm_runtime/tests/test_w39_coverage_denominator.py` — **+6 case**（註冊表釘 7 / 真實規則 escalation-scoped=100% / breakdown 誠實 32=39−7 / 舊欄位零退化 / numerator⊆正當分母 / 靜態掃描防漂移）。runtime `escalation_scoped_coverage_pct` 實測 **100.0**（7/7）。

### 紅線守界（B 軌）
- **零退化** — 既有三欄位（rules_with_failure_mode=7 / rules_total=39 / attributed_rule_ids）逐字不變；純度量、永不 set_maturity（R-9.20 #11）。
- **DEF-18-001 寧缺勿濫** — 分母校正不放寬接線門檻（numerator ⊆ 正當分母，由測試鎖定）。
- **無 FSM 變更** — `transition_rules.py` + 5 `*.tla`/`.cfg` 對 v0.16 逐位元零差異，Rule 9.18.1 不啟動。

## [v0.16] - 2026-06-18（Copy-on-Evolve 自 v0.15；v0.15 凍結唯讀）

> AutoSDD_improving_38 — B 軌 dogfooding 缺陷漸進清償（無 A/C 軌新功能）。DEF-19-001 catch 歸因覆蓋 5/39 → 7/39（+2）。

### 新增（DEF-19-001 catch 覆蓋補強，沿用既有 R-9.3 / R-SELF-STRIDE，不取新 ACT/Rule）
- **W-38-1（R-SELF-STRIDE，5/39→6/39）** — `governance/rules/R-SELF-STRIDE.yaml` 補 `failure_mode`（SANDBOX_HARDENING_GATE policy_violation → ESCALATION structural，**唯一生產落點**；明文 verdict=pass 不歸因、與既有 5 條零交集）；`tools/fsm_runtime/fsm_runtime.py` `exit_sandbox_hardening_gate` 的 policy_violation 分支接 `_record_escalation_catches(["R-SELF-STRIDE"])`。
- **W-38-2（R-9.3，6/39→7/39）** — `governance/rules/R-9.3-logical-consistency-guard.yaml` 補 `failure_mode`（record_spec_audit 的 SPEC_AUDIT 耗盡 → ESCALATION；**明文排除** implementation-budget-exceeded 直接 escalate〔正交、無規則〕與 R-9.1 gate-retry 落點，杜絕雙重歸因）；`record_spec_audit` 的 escalate 分支接 `_record_escalation_catches(["R-9.3"])`。
- `tools/fsm_runtime/tests/test_w38_catch_wiring.py` — **+8 case**（R-SELF-STRIDE / R-9.3 各：flag ON catch+1、flag OFF 零退化、**非重疊守門**；真實規則具非空 failure_mode×2）。runtime `catch_attribution_coverage` 實測 **7/39**。

### 紅線守界（B 軌）
- **DEF-18-001 寧缺勿濫** — 只接「有唯一生產 escalation 落點 + 可定義 failure_mode + 無雙重歸因」的規則；R-9.3 的 failure_mode 明文排除正交落點（同 improving_37 R-9.7「僅 9.7.2」範式）。
- **無 FSM 狀態/規則/`*.tla`/`.cfg` 變更**（catch 純記帳、不寫 FSM-STATE、不 churn；`transition_rules.py` + 5 `*.tla`/`.cfg` 對 v0.15 **逐位元零差異** → **免五軌 TLC**，Rule 9.18.1 不啟動）；flag `SDD_ENABLE_RULE_CATCH_TELEMETRY` 預設 OFF；不碰 meta⁹/meta-oracle；不提 Token 上限；ID_REGISTRY 不取新 ACT/rule。
- 驗證：v0.16 `pytest -m "not chaos"` = **1605 passed / 4 skipped / 0 failed**（v0.15 1597 + 8）。Copy-on-Evolve 以 `scripts/copy_on_evolve.sh` 匯出 856 tracked 檔（零 runtime cruft）。

---

## [v0.15] - 2026-06-18（Copy-on-Evolve 自 v0.14；v0.14 凍結唯讀）

> AutoSDD_improving_37 — B 軌 dogfooding 缺陷漸進清償（無 A/C 軌新功能）。DEF-19-001 catch 歸因覆蓋 4/39 → 5/39。

### 新增（W-37-1：DEF-19-001 catch 覆蓋補強，沿用既有 R-9.7，不取新 ACT/Rule）
- `governance/rules/R-9.7-precise-halt-m1.yaml` — 補 `failure_mode` 欄位（可參與 catch 自動歸因）。**明文僅涵蓋 9.7.2**（HUMAN_PENDING 逾時 ≥168h → 自動 ESCALATION），排除 9.7.3（AUTO_COMPACT per-stage 超限，歸 R-9.2 `trigger_auto_compact`），杜絕雙重歸因（DEF-18-001 寧缺勿濫）。
- `tools/fsm_runtime/fsm_runtime.py` — 新增 thin 方法 `escalate_human_pending_timeout(reason=...)`：record_escalation + flag-gated `_record_escalation_catches(["R-9.7"])` 同落點（與 R-9.1/R-9.2/R-9.21/R-9.22 四條既有接線同範式）。
- `.claude/hooks/session_start.py` — ACT-023 HUMAN_PENDING 逾時 ESCALATION 分支改委派 `rt.escalate_human_pending_timeout(reason=reason)`（catch 與 escalation 同落點才不漏記）。
- `tools/fsm_runtime/tests/test_w37_catch_wiring.py` — **+4 case**（flag ON catch+1 / flag OFF 零退化 / 非重疊守門：9.7.3 路徑只 R-9.2 catch+1、R-9.7 恆 0 / 真實 R-9.7 具非空 failure_mode）。

### 紅線守界（B 軌）
- **R-9.9 降級不接** — 親驗無唯一生產 escalation 落點（state_loader 損毀 `raise` 非 escalate；chaos_runner record_escalation 屬測試載具模擬其他規則失敗模式），依 DEF-18-001 不臆測歸因（掌舵者預授權 fallback）。
- **無 FSM 狀態/規則/`*.tla`/`.cfg` 變更**（catch 純記帳、不寫 FSM-STATE、不 churn；`transition_rules.py` + 5 `*.tla`/`.cfg` 對 v0.14 **逐位元零差異** → **免五軌 TLC**，Rule 9.18.1 不啟動）；flag `SDD_ENABLE_RULE_CATCH_TELEMETRY` 預設 OFF；不碰 meta⁹/meta-oracle；不提 Token 上限；ID_REGISTRY 不取新 ACT/rule。
- 驗證：v0.15 `pytest -m "not chaos"` = **1597 passed / 4 skipped / 0 failed**（v0.14 1593 + 4）。Copy-on-Evolve 以 `git archive` 匯出 855 tracked 檔（零 runtime cruft）。

---

## [v0.14] - 2026-06-17（Copy-on-Evolve 自 v0.13；v0.13 凍結唯讀）

> AutoSDD_improving_23 — B 軌 XAI 深化（dogfooding，無 A/C 軌新功能）。補完 Phase Y 視覺化儀表板 `_26.md` 列入、§D 收官以 pagination 替代而靜默未交付的 Folding 降維子項。

### 新增（W-23-1：Folding 降維補完，隸屬既有 R-9.37 PY-3，不取新 ACT/Rule）
- `tools/fsm_runtime/recursion_topology_view.py` — fold env 旋鈕 `SDD_VIZ_FOLD`(預設 **OFF**＝v0.13 行為) / `SDD_VIZ_FOLD_MIN`(預設 3, clamp[2,64])；`RenderBudget` additive `fold_enabled`/`fold_min`；`TopoNode` additive `folded`/`folds`。新增純函式 `fold_topology(view)`：把窗內極大「內部簡單鏈」（連續 in==1∧out==1∧非 kept-node）塌縮為單一 `[+k more]` 折疊超節點（錨定鏈首 + 商圖重接邊）；**永不折疊 entry/critical/分支/匯聚/sink/未訪問節點**（結構要角恆可見）。`extract_topology` 末尾 flag-gated 套用。
- `render_mermaid` 折疊超節點專屬 `classDef fold` 渲染；`render_json` additive 輸出 `folded`/`folds`。
- **PY-2 fold-aware 誠實收縮稽核** — `verify_topology_consistency` 擴充：以 expanded（含折疊展開）窗格錨定（真實大小誠實 nothing dropped）+ 折疊合法性 f1（窗內成員 in==1∧out==1 + 連續真實呼叫邊）/ f2（鏈 rank 嚴格遞減）/ f3（不藏 entry）+ 商圖邊比對（折疊內部邊吸收、跨群邊保留，杜絕杜撰/漏畫）。**fold OFF 時 group=identity、expanded=shown，五道恆過 ⇒ 與 v0.13 逐位元行為相容**。
- `chaos_runner.py` — `VISUALIZATION_FOLD_DRIFT_FLAP` + `_visualization_fold_drift_flap_is_bounded`（偽造折疊吞 sink / 丟成員必被攔、忠實折疊放行，納入 100 輪 bounded）。
- `tools/fsm_runtime/tests/test_phase_y.py` — **+13 case**（fold OFF 零退化 / 鏈塌縮 / 不折要角 / 誠實 verify+guard / 4 道折疊偽造 fail-closed / env clamp / 10⁶ 有界 / fold_topology 零 while 零遞迴 / chaos fold-drift 註冊+bounded）。

### 流程修復
- **DEF-23-002** — `build/planning/active/SDD_improving_Automation_26.md`（Phase Y §D 已收官）、`_27.md`（closure §6 標 archive）兩份已完成 RFC `git mv` 入 `build/planning/archive/`（修「active=待決 / archive=已決」生命週期漂移；v0.13 凍結不回改）。
- **DEF-23-001**（文檔計數口徑釐清）— v0.13 CHANGELOG 上條稱 `test_cross_version_guard.py`「+2 case（25→27）」，**口徑釐清：27＝`scripts/tests/` 全套合計（跨檔），非單檔函式數**（該檔單檔實測為 10 個 test 函式 / 10 passed、無 parametrize；DEF-12-002/DEF-22-001 回歸鎖確在檔內）。

### 紅線守界（B 軌）
- **無 FSM 狀態/規則/`*.tla`/`.cfg` 變更**（Folding 為 `recursion_topology_view` 內 read-only 純投影轉換、不寫 FSM-STATE/不 churn；`transition_rules.py` + 5 `*.tla`/`.cfg` 對 v0.13 **逐位元零差異** → **免五軌 TLC**，Rule 9.18.1 不啟動）；`VisualizationBounded==churn<=MAX_CHURN` 不受影響；不碰 meta⁹/meta-oracle；不提 Token 上限；ID_REGISTRY 不取新 ACT/rule（沿用 _27/DEF-20-001 前例 + Rule 2）。
- 驗證：v0.14 `pytest -m "not chaos"` = **1593 passed / 4 skipped / 0 failed**（v0.13 1580 + 13）；chaos **34 passed**（100 輪 bounded_ratio==1.0 含新 FOLD_DRIFT）；AutoClaude **3112 passed / 0 failed** 持平；lint 8 kept。Copy-on-Evolve 以 `git archive` 匯出 853 tracked 檔（零 runtime cruft）。

---

## [v0.13] - 2026-06-17（Copy-on-Evolve 自 v0.12；v0.12 凍結唯讀）

> AutoSDD_improving_22 缺陷清償輪（B 軌 dogfooding，無 A/C 軌新功能）。

### 重構（W-22-2：DEF-15-001 深層 — FSM 種子模板移出 runtime 輸出目錄，本版觸發者）
- `tools/fsm_runtime/state_loader.py` — `TEMPLATE_PATH` 由 `REPO_ROOT/build/reports/fsm/FSM-STATE-TEMPLATE.yaml` 改為與 loader 同層的 tracked 源碼位 `Path(__file__).resolve().parent/"templates"/"FSM-STATE-TEMPLATE.yaml"`（docstring 同步）。`DEFAULT_STATE_DIR`（runtime 狀態檔輸出 = build/reports/fsm/）**不變** → **輸入（種子模板）/ 輸出（runtime 狀態檔）分離**。
- 物理移檔 `build/reports/fsm/FSM-STATE-TEMPLATE.yaml` → `tools/fsm_runtime/templates/FSM-STATE-TEMPLATE.yaml`（內容逐位元零變更）；同步 3 處文件連結（`SDD_FSM_ENGINE.md` / `AISDLC_SDD_UPGRADE_SOP.md` / `test-failure-analyzer/SKILL.md`）。
- `AISDLC_SDD/.gitignore` v0.13 區塊：模板移出後 build/reports/ **整樹排除、不再需 negate idiom**（消除 DEF-11-001/15-001 反覆打補丁的結構異味根因）；`copy_on_evolve.sh` 補回模板特例對 v0.13+ 自然成 no-op（保留供 ≤v0.12 舊佈局相容）。
- `tools/fsm_runtime/tests/test_template_location.py` — **3 case**（TEMPLATE_PATH 在 templates/ 非 build/reports / 模板 is_file 且 `_load_template` 載入非空 dict / DEFAULT_STATE_DIR 仍 build/reports/fsm）。

### 修復（W-22-1：shared infra `AISDLC_SDD/scripts/`，免 Copy-on-Evolve）
- **DEF-12-002** — `cross_version_guard._is_path_arg` 在 `os.path.exists` 前剝 `token.split("::",1)[0]`，修 pytest nodeid（`path::test`）含 `::` 被誤判非路徑 → bare 分支誤展全版 false fire。
- **DEF-22-001**（dogfooding 當場揭露，P2 真 bug）— `VERSION_RE=AISDLC_SDD_v0\.0\d+` 僅匹配 v0.00–v0.09，對現役 v0.10~v0.13 失效（DEF-19-002 同根十位數跨越，當時漏修此處）→ 放寬 `v0\.\d+` 通則化。`scripts/tests/test_cross_version_guard.py` +2 case（25→27）。

### 紅線守界（B 軌）
- **無 FSM 狀態/規則/`*.tla` 變更**（模板移位純屬檔案位置 + 路徑常數；`transition_rules.py` + 5 `*.tla` 對 v0.12 **逐位元零差異**，`diff -q` 實測全 IDENTICAL → **免五軌 TLC**，Rule 9.18.1 不啟動）；ID_REGISTRY 不取新 ACT/rule。
- 驗證：v0.13 `pytest -m "not chaos"` = **1580 passed / 0 failed**（v0.12 1577 + 3）；ci-gate 雙軌 exit 0 v0.01:1478 / **v0.13:1580** / scripts/tests:27（FF-17 自證 v0.13 入閘）；AutoClaude **3112 passed / 0 failed** 持平；lint 8 kept；LOC 0；snapshot 新鮮；潔淨度 `git add -A -n` 853 無 runtime 殘留（模板正常 tracked、build/reports 整樹忽略）。

---

## [v0.12] - 2026-06-16（Copy-on-Evolve 自 v0.11；v0.11 凍結唯讀）

### 新增（B 軌 DEF-20-001 反幻覺機械閘門 — 結案證據強制重推導；AutoSDD_improving_21 W-21-1/W-21-2）
- `tools/fsm_runtime/closure_evidence.py` — 純函式邏輯模組（同 `drift_monitor.py` 慣例）。**廉價層** `verify_git_facts`：對 improving_NN.md 末尾 `closure-evidence` 契約宣稱的 `claimed_commits`/`claimed_tag`，以 `git cat-file -e`+`merge-base --is-ancestor`+`rev-parse --verify` 就 monorepo 根真實狀態重推導（白名單正則消毒、list-form argv shell=False），任一無法重推導 → **FAIL**（直擊「編造 commit/push/tag」幻覺事故核心）。**昂貴層** `verify_expensive_claims`：pytest passed / ci-gate floors **不重跑**，改驗綁定當前 HEAD 的 rederive 證書（`write_rederive_cert` stamp HEAD），契約 base_sha≠HEAD 或證書缺失/數字不符 → **INCONCLUSIVE**（fail-closed 不綠勾，比照 embodied_grounding 零觀測語意，絕不假綠）。`synthesize_verdict` 三分支優先序 FAIL>INCONCLUSIVE>VERIFIED。
- `.claude/hooks/closure_evidence_verify.py` — thin git post-commit hook（同 `post_commit_drift.py`）：`repo_root_from()` 以 git toplevel 定位 monorepo 根、**永遠 exit 0 / <2s budget / fail-soft / 不阻擋 commit**，verdict 寫 `.git/CLOSURE_EVIDENCE_VERDICT` + `build/reports/closure/VERDICT-<sha>.yaml`。**把反幻覺紀律由「agent 跨 session 自律」升級為框架機械可驗閘門**。
- `tools/install_hooks/install_post_commit.{sh,ps1}` — 擴充串接 drift（指 v0.01）+ closure（指 v0.12），opt-in 不經 settings.json deny 層。
- CLI 入口 `_main(argv, repo_root=None)` + `__main__`（`--rederive --observed '<json>'` stamp HEAD 落盤證書 / 無參數 evaluate 印 verdict）。**DEF-21-003**（dogfooding 揭露 → fixed@v0.12）：hook INCONCLUSIVE 訊息承諾的 `python -m ... --rederive` 原無 CLI 入口、指令無動作，本輪補完。
- `tools/fsm_runtime/tests/test_closure_evidence.py` — **22 case**（tmp 真實 git repo 驗 cat-file/merge-base/rev-parse 真實行為：真 commit PASS/編造 FAIL/非祖先 FAIL/注入拒絕/真 tag PASS/缺 tag FAIL；昂貴層 stale base_sha + 缺證書 INCONCLUSIVE、證書符 VERIFIED、不符 FAIL；verdict 三分支；last-match 解析；端到端+持久化；CLI rederive 寫證書/bad-json/無參數 evaluate）。
- 結案契約 schema＝`docs/04_planning/AutoSDD_improving_NN.md` 末尾 ```yaml ``closure-evidence`` 區塊（機器可讀宣稱來源）。RFC：`build/planning/active/SDD_improving_Automation_27.md`。

### 修復（DEF-21-001 dogfooding 衍生 → fixed@v0.12）
- `tools/fsm_runtime/closure_evidence.py:parse_closure_evidence` — improving_NN.md 多 `closure-evidence` yaml 區塊（§4 schema 範例 + 末尾真實契約）致解析歧義，改 **last-match**（對齊 DEF-02-002 `tlc_runner.parse_tlc_summary` findall[-1] 紀律）；計畫書 §4 schema fence 改 ```text 雙保險。

### 紅線守界（B 軌）
- **決策不新增 R-9.x**（advisory hook 不需規則承載即可運作，避免牽動 RULES_INDEX/ID_REGISTRY 取號與五軌 reachable，同 DEF-10-002 前例 + Rule 2）。治理規則承載 + catch 覆蓋面推進 + closure 接入 SCG-4/5 機械閘門 → routed 未來輪。
- **無 FSM 狀態/規則/`*.tla` 變更**（hook 不新增狀態/轉換、不寫 FSM-STATE；`transition_rules.py` + 5 `*.tla` 對 v0.11 逐位元零差異 → **免五軌 TLC**，Rule 9.18.1 不啟動）。closure hook advisory 不阻擋 commit、零觸碰 FSM/規則/既有測試。驗證：v0.12 `pytest -m "not chaos"` = **1577 passed / 0 failed**（v0.11 1555 + 22 新測試〔19 核心 + 3 CLI〕）；ci-gate 雙軌 exit 0 v0.01:1478 / v0.12:1574 / scripts:25（FF-17 自證 v0.12 入閘；ci-gate 跑於 CLI 補完前）；AutoClaude **3112 passed / 0 failed** 持平；lint 8 kept；LOC 0；snapshot 新鮮；潔淨度無 runtime 殘留（closure runtime 產物根 gitignore，DEF-21-002）。**dogfooding 自驗**：commit A `5f8b633` 後回填真實契約 + rederive 證書 → hook VERIFIED（反幻覺迴圈閉合）。

---

## [v0.11] - 2026-06-16（Copy-on-Evolve 自 v0.10；v0.10 凍結唯讀）

### 新增（B 軌「鷹架代謝」L4→L5 catch 覆蓋補強；AutoSDD_improving_20 W-20-1）
- `governance/rules/R-9.2-context-budget.yaml` — 補 `failure_mode`：per-stage `auto_compact` 超限 → ESCALATION（R-9.2 守望的失敗模式）。
- `governance/rules/R-9.22-adversarial-self-improving-phase-j.yaml` — 補 `failure_mode`：`spec_patch` per-AC 上限耗盡 → 直升 ESCALATION（R-9.22 守望的失敗模式）。
- `tools/fsm_runtime/fsm_runtime.py` — 在兩個既有 `record_escalation` 呼叫點接 v0.10 既有 `_record_escalation_catches()`：`trigger_auto_compact` per-stage 超限分支歸因 `["R-9.2"]`、`enter_spec_patch_proposal` per-AC 超限分支歸因 `["R-9.22"]`。**catch 自動歸因覆蓋 2/39 → 4/39**（沿用 v0.10 catch 三要件契約：failure_mode 自描述 ∧ 攔截事件真實發生 ∧ 結構化歸因 rule_id，顯式可歸因非時序猜測）。**預設 OFF＝v0.10 行為（零退化）**；fail-closed；只增 catch_count 永不 set_maturity（R-9.20 #11）。**閉合 DEF-19-001 兩條確定路徑**。
- `tools/fsm_runtime/tests/test_w20_catch_wiring.py` — 6 新測試（R-9.2/R-9.22 各 flag ON 真記+1 + flag OFF 零退化 + 真實凍結規則具非空 failure_mode）。

### 修復（W-20-2 / DEF-19-002 通則化 → fixed@v0.11）
- `tools/arch_fitness/arch_fitness.py` — FF-17 驗證正則 `_CI_GATE_LATEST_GLOB_RE` 由寫死 `AISDLC_SDD_v0\.0\*` 放寬為通則 `AISDLC_SDD_v0\.[0-9\[*]`（接受 `v0.0*` / `v0.[0-9]*` / `v0.[1-9]*` / `v0.*`），**解除 improving_19 雙 glob 修復被迫保留 `v0.0*` 子串的結構耦合異味**（ci-gate.sh 此後可清掉子串改純通則化仍過 FF-17）；同步更新兩處顯示字串。
- `tools/fsm_runtime/tests/test_arch_fitness.py` — 4 新測試（FF-17 接受 4 種通則 glob 形式）。

### 紅線守界（B 軌）
- W-20-1 沿用 v0.10 既有 catch helper，零新增方法、零 FSM 拓樸變更。**無 FSM 狀態/規則/`*.tla` 變更**（`transition_rules.py` + 5 `*.tla` 對 v0.10 逐位元零差異 → 免五軌 TLC）。catch 記帳只增 `catch_count`、永不 `set_maturity`（退役維持 🔴 人工，R-9.20 #11）；R-9.2/R-9.22 之外 35 規則 failure_mode 未定義者 fail-closed 不記（DEF-19-001 漸進補強）。驗證：v0.11 `pytest -m "not chaos"` = **1555 passed / 0 failed**；ci-gate v0.01:1478 / v0.11:1555 / scripts:25；AutoClaude 3112 持平；lint 8 kept；LOC 0；snapshot 新鮮。

---

## [v0.10] - 2026-06-16（Copy-on-Evolve 自 v0.09；v0.09 凍結唯讀）

### 新增（B 軌「鷹架代謝」L4→L5 信號 — catch 側契約定義並接入 FSM 主迴圈；AutoSDD_improving_19 W-19-1/W-19-2/W-19-3）
- `tools/fsm_runtime/rule_loader.py` — `Rule` 新增 optional `failure_mode`（規則自描述守望的失敗模式）；`_write_rule` **條件寫回 failure_mode**（非空才寫，解決 fire/catch round-trip 抹欄之持久化潔淨度陷阱）；新增 `record_state_catches(attributed_rule_ids)`（對「歸因∩failure_mode非空∩非deprecated」子集各記 catch+1，fail-closed）。
- `tools/fsm_runtime/fsm_runtime.py` — 把 catch 記帳**接入主迴圈**：新增 `_RULE_CATCH_TELEMETRY_ENV="SDD_ENABLE_RULE_CATCH_TELEMETRY"` 開關 + `_rule_catch_telemetry_enabled()` + `_record_escalation_catches()`；接在兩個 `record_escalation` 呼叫點（`record_attempt` escalate→`["R-9.1"]`、`exit_monitor_violation`→`["R-9.21"]`）。`rule_fire_telemetry_stats()` 證書 **翻 `catch_side_wired=True`** + 新增 `total_catches` + `catch_attribution_coverage`（誠實揭露覆蓋率）。**預設 OFF＝v0.09 行為（零退化）**；fail-closed：catch 記帳失敗絕不阻塞已落定的 escalation。**閉合 DEF-18-001「catch 側語意未定義」**——catch 契約三要件（failure_mode 自描述 ∧ 攔截事件真實發生 ∧ 結構化歸因 rule_id），**顯式可歸因、非時序鄰近猜測**。
- `governance/rules/R-9.1` / `R-9.21` — 補 `failure_mode` 欄（兩條確定可歸因規則）。
- `tools/fsm_runtime/tests/test_rule_catch_telemetry_wiring.py` — 11 新測試（含持久化陷阱回歸鎖 + monitor violation 整合真接 + 要件①無 failure_mode 不歸因 + 空歸因寧缺勿濫）；fire 測試 Case 7 同步斷言。

### 紅線守界（B 軌）
- `record_state_catches` 只增 `catch_count` 計數、**永不自動退役 active 規則**；退役維持 🔴 人工 `set_maturity(reviewed_by=...)`（R-9.20 #11 不弱化）。catch_count>0 是 `propose_graduation` 保護有用規則不被誤退役的依據，補實 arch_fitness FF-16 GAP-X2 的真實資料缺口。**未歸因 escalation / 無 failure_mode 規則 fail-closed 不記、不污染 ROI**（DEF-18-001 寧缺勿濫）。**無 FSM 狀態/規則/`*.tla` 變更**（diff v0.09 逐位元零差異 → 免五軌 TLC）。**新記 DEF-19-001**（P3, routed）：catch 歸因目前覆蓋 2/39 規則，餘漸進補強（coverage 誠實揭露）。

---

## [v0.09] - 2026-06-16（Copy-on-Evolve 自 v0.08；v0.08 凍結唯讀）

### 新增（B 軌「鷹架代謝」L4→L5 信號 — 規則命中遙測接入 FSM 主迴圈；AutoSDD_improving_18 W-18-1/W-18-2）
- `tools/fsm_runtime/rule_loader.py` — 新增批次 helper `record_state_fires(state, *, caught=False)`：單次 `load_all`、對 `load_for_state(state)` 命中規則一次性增 `scaffold_roi.fire_count` 各寫一次（避 per-rule O(N²) 重載；deprecated 不記）。
- `tools/fsm_runtime/fsm_runtime.py` — 把 `record_fire` on-watch 記帳**接入主迴圈**：新增 `_RULE_FIRE_TELEMETRY_ENV="SDD_ENABLE_RULE_FIRE_TELEMETRY"` 開關 + `_rule_fire_telemetry_enabled()` + `rule_fire_telemetry_stats()`（L5 可量測信號：fire_ladder 降冪 / `retirement_eligible` + XAI 安全證書）；`transition()` 於 `save_state` 後 flag-gated 呼 `record_state_fires(dst)`。**預設 OFF＝v0.08 行為（零退化）**；fail-closed：記帳失敗絕不阻塞已落定的轉態。**閉合 DEF-17-001 點名的「`fire_count=0` 根因」**——使 GC 有非零資料可驅動退役提議（上輪只接決策側 run_gc，本輪接遙測側）。
- `tools/fsm_runtime/tests/test_rule_fire_telemetry_wiring.py` — 8 新測試（flag off 零退化 ×2 / flag on 命中記 on-watch fire + 選擇性 / fire_count 累積持久化 / 記帳失敗 fail-closed / 遙測零 set_maturity 呼叫〔R-9.20 #11〕/ stats 度量穩健+證書誠實揭露 / fire_ladder 降冪+retirement_eligible）。

### 紅線守界（B 軌）
- `record_state_fires` 只增 `fire_count` 計數、**永不自動退役 active 規則**；退役維持 🔴 人工 `rule_loader.set_maturity(reviewed_by=...)`（R-9.20 絕對禁令 #11 不弱化）＝rubric「L5 在環上守界」之守界；`rule_fire_telemetry_stats` 純讀不碰 meta-oracle。**誠實揭露**：`safety_certificate.catch_side_wired=False`——本輪只接 fire 側，catch 側語意未定義（**DEF-18-001**，routed），ROI 為單側信號。**無 FSM 狀態/規則/`*.tla` 變更**（diff v0.08 逐位元零差異 → 免五軌 TLC）。

---

## [v0.08] - 2026-06-16（Copy-on-Evolve 自 v0.07；v0.07 凍結唯讀）

### 新增（B 軌「鷹架代謝」L4→L5 信號 — GC 自動提議退役接入 FSM 主迴圈；AutoSDD_improving_17 W-17-1/W-17-2）
- `tools/fsm_runtime/fsm_runtime.py` — 把既有 `scaffold_gc.run_gc()`（產 `RetirementProposal` proposed 退役提議，原測試-only / 手動）**接入主迴圈**：新增 `_SCAFFOLD_GC_AUTO_PROPOSE_ENV` 開關 + `_scaffold_gc_auto_propose_enabled()` + `scaffold_gc_stats()`（L5 可量測信號 + XAI 安全證書）；`enter_scaffold_gc()` 進態 SCAFFOLD_GC 後 flag-gated 自動跑 `run_gc` 算 ROI 落 `SCAFFOLD-ROI-{date}.md` + 填 `scaffold_gc_tracking`。**預設 OFF＝v0.07 行為（零退化）**；fail-closed：run_gc 任何失敗進態仍成功、不偽造報告。行使 arch_fitness FF-16 GAP-X2「代謝肌肉從未收縮」之 Rule 9.20.5。
- `tools/fsm_runtime/tests/test_scaffold_gc_auto_propose_wiring.py` — 9 新測試（flag off 零退化 ×2 / flag on 自走 run_gc+tracking / 報告真實落盤 / run_gc 失敗 fail-closed / GC 零 set_maturity 呼叫〔R-9.20 #11〕/ 非 RELEASE 源仍 raise / 零提議度量穩健 / roi_ladder 升冪+by_transition）。

### 紅線守界（B 軌）
- `run_gc` 只產退役提議、**永不自動退役 active 規則**；退役維持 🔴 人工 `rule_loader.set_maturity(reviewed_by=...)`（R-9.20 絕對禁令 #11 不弱化）＝rubric「L5 在環上守界」之守界；`scaffold_gc_stats` 純讀不碰 meta-oracle（GC 是 ROI 統計層非生成器）。**無 FSM 狀態/規則/`*.tla` 變更**（diff v0.07 逐位元零差異 → 免五軌 TLC）。

---

## [v0.07] - 2026-06-15（Copy-on-Evolve 自 v0.06；v0.06 凍結唯讀）

### 新增（B 軌「規則自演化」L4→L5 信號 — SLV 自動提議接入 FSM 主迴圈；AutoSDD_improving_16 W-16-1/W-16-2）
- `tools/fsm_runtime/fsm_runtime.py` — 把既有 `slv_generator.propose_slv_from_fpl()`（`trust_level:proposed` 草案合成，原 proposal-only / 手動 CLI）**接入主迴圈**：新增 `_SLV_AUTO_PROPOSE_ENV` 開關 + `_slv_auto_propose_enabled()` + staticmethod `_auto_draft_slv(fpl_id)`（純合成 fail-closed）+ `learning_loop_stats()`（L5 可量測信號 + XAI 良基終止證書）；`exit_production_behavioral_signal()` 加 optional `fpl_id`，**learn 分支**轉態到 LEARNING_COMMIT 後 flag-gated 自動 draft proposed 草案 + 填 `learning_commit_tracking`。**預設 OFF＝v0.06 行為（零退化）**；附帶修 **DEF-16-001**（learn 採納鏈結構性斷裂）。
- `tools/fsm_runtime/tests/test_slv_auto_propose_wiring.py` — 9 新測試（flag off 零退化 ×2 / flag on 自走 draft+tracking / learn→人 verify→approve 鏈閉合 / 未 verify approve→raise〔R-9.11〕/ FPL 不存在 fail-closed / 合成失敗 fail-closed / 零事件度量穩健 / 計數+churn_max 一致）。

### 紅線守界（B 軌）
- 草案恆 `trust_level:proposed`（R-9.11，永不自動升 verified）；`trust_level→verified` 維持 🔴 人工（`exit_learning_commit` verified 強制檢查不動）＝rubric「L5 在環上守界」之守界；採納經 `meta_halt_monitor` ChurnBounded/GraduationRatchet（R-9.24 不弱化）；`learning_loop_stats` 純讀不碰 meta-oracle（R-9.37）。

### 不變
- **無 FSM 狀態/規則變更**：`LEARNING_COMMIT` 既有 state、`PRODUCTION_BEHAVIORAL_SIGNAL→LEARNING_COMMIT`（learn）既有邊，`transition_rules.py` + 全 5 `*.tla` 對 v0.06 **逐位元零差異**（diff 實測全 ZERO DIFF），Rule 9.18.1 不啟動、五軌 TLC 既有證明維持有效；ID_REGISTRY 不取新 ACT/rule。

### 驗證
- v0.07 `pytest -m "not chaos"` = 1517 passed / 4 skipped（v0.06 1508 + 9，只增不減）；新 wiring 9 passed；flag OFF 既有 37 相關 passed 零退化；雙軌 ci-gate exit 0「v0.01 凍結基線 + v0.07 最新演化版」（FF-17 自證入閘）。

---

## [v0.06] - 2026-06-15（Copy-on-Evolve 自 v0.05；v0.05 凍結唯讀）

### 新增（B 軌「流程自治」L3→L4 升級 — auto_recovery 接入 FSM 主迴圈；AutoSDD_improving_15 W-15-1）
- `tools/fsm_runtime/fsm_runtime.py` — 把既有 `auto_recovery.py`（Rule 9.14 有界 1-shot 自癒，原 proposal-only / 需 orchestrator 手動觸發）**接入主迴圈**：新增 `_AUTO_RECOVERY_ENV` 開關常數 + `_auto_recovery_enabled()` + `_gate_is_resumable()` 預檢 + `auto_recovery_stats()`（L4 可量測信號）；`record_gate_result()` escalate 分支 **flag-gated 自動嘗試** `enter_auto_recovery`，把既有 `ESCALATION→AUTO_RECOVERY_ATTEMPT` 邊（TLA `T_EnterAutoRecover` 已模型化）由手動改自動觸發。**預設 OFF＝v0.05 行為（零退化）**；fail-closed（structural/bounds→ESCALATION_FINAL、例外停 ESCALATION）。
- `tools/fsm_runtime/tests/test_auto_recovery_wiring.py` — 9 新測試（flag off 零退化 / flag on 自走進 recovery / 完整閉環 success 回 gate / structural→FINAL / bounds→FINAL / fail→FINAL / resumable 預檢 / 空 session 零率）。

### 不變
- **無 FSM 狀態/規則變更**：`AUTO_RECOVERY_ATTEMPT` 為既有合法 state、`ESCALATION→AUTO_RECOVERY_ATTEMPT` 為既有合法邊，`_HAPPY_PATH` 與全部 `*.tla` 零改動（僅改 Python 觸發者、非狀態宇宙），Rule 9.18.1 不啟動、五軌 TLC 既有證明維持有效；ID_REGISTRY 維持 act=173 / rule="9.39"（接線既有能力，不取新 ACT/rule）。

### 驗證
- v0.06 `pytest -m "not chaos"` = 1508 passed / 4 skipped（v0.05 1499 + 9，只增不減）；flag OFF 既有 86 passed 零退化；雙軌 ci-gate exit 0「v0.01 凍結基線 + v0.06 最新演化版」（FF-17 自證 v0.06 自動入閘）。

### 共享 infra 同輪修（DEF-15-001，免 Copy-on-Evolve）
- `scripts/copy_on_evolve.sh` — 修 `tar --exclude build/reports` 誤殺 FSM 種子模板 `build/reports/fsm/FSM-STATE-TEMPLATE.yaml`（state_loader 必需真輸入）：排除後補回該模板；`scripts/tests/test_copy_on_evolve.py` 加回歸鎖 case。首次真實 v0.06 演化當場揭露（46+ FSM 測試全紅）。

---

## [v0.05] - 2026-06-15（Copy-on-Evolve 自 v0.04；v0.04 凍結唯讀）

### 新增（DEF-10-002b 回流 — Copy-on-Evolve 演化版必納官方閘門固化；AutoSDD_improving_11 W-11-2）
- `tools/arch_fitness/arch_fitness.py` — 新增 **FF-17「Copy-on-Evolve 演化版必納官方閘門」** 結構守門：把 improving_04 對 DEF-03-001 的雙軌**點修**固化為**結構不變量**。新增常數 `CI_GATE_PATH`、純函式 `_latest_version_dir()`、`check_ff17_evolution_version_gate_coverage()`（靜態讀 `scripts/ci-gate.sh`，斷言四錨點動態最新版偵測；退回靜態寫死＝`structural fail`），註冊進 `ALL_CHECKS`；docstring 16→17、exit-code 清單補 FF-17。與 FF-14 同源（靜態讀 CI 腳本、純讀、跨平台不執行 shell）。
- `tools/fsm_runtime/tests/test_arch_fitness.py` — 5 新測試（真 repo 涵蓋最新版 / 合成雙軌 PASS / 寫死單版 fail / 漏 append-latest fail / 腳本缺 INFO 略過）。
- **設計決策**：不另開 R-9.x 規則（會連鎖 FF-8/10/12 且屬自演化 meta-loop 異類關注點）；arch_fitness 本即治理層 fitness-function 套件，FF-17 即最小正確固化（Rule 2/3）。

### 不變
- **無 FSM 狀態/規則變更**（`_HAPPY_PATH` 與 `*.tla` 零改動，Rule 9.18.1 不啟動）；ID_REGISTRY 維持 next_free act=173 / rule="9.39"（純 fitness-function 新增，不取新 ACT/rule）。

### 驗證
- v0.05 `pytest -m "not chaos"` = 1499 passed / 4 skipped（v0.04 1494 + 5，只增不減）；arch_fitness 87 passed；雙軌 ci-gate exit 0「v0.01:1478 v0.05:1499」——v0.05 作為最新演化版自動納入官方閘門，自證 FF-17 不變量。

---

## [v0.04] - 2026-06-14（Copy-on-Evolve 自 v0.03；v0.03 凍結唯讀）

### 修正（DEF-02-002 回流 — tlc_runner 計數標籤接反；AutoSDD_improving_03 W2）
- `tools/fsm_runtime/tlc_runner.py` — 抽出 module-level `parse_tlc_summary(out)`：以 **last-match**（`re.findall[-1]`）取最終 summary，取代舊 **first-match**（`re.search`）誤抓中途 progress 行；加 fail-closed 斷言 `generated >= distinct`（違反即 `raise RuntimeError`）。
- `tools/fsm_runtime/tests/test_tlc_runner_parsing.py` — 4 新測試（last-match / 正常不誤報 / 畸形 raise / 無匹配回 0；純字串、不需 Java）。

### 不變
- **無 FSM 狀態/規則變更**（`_HAPPY_PATH` 與 `*.tla` 零改動，Rule 9.18.1 不啟動）；ID_REGISTRY 維持 next_free act=173 / rule="9.39"。

### 形式化驗證
- 五軌 TLC 重跑驗證修正本身（last-match 取對 + generated ≥ distinct + 0 violation）；數據見 `EVOLUTION_LOG.md` v0.03→v0.04 段。

---

## [v0.03] - 2026-06-13（Copy-on-Evolve 自 v0.02；v0.02 凍結唯讀）

### 新增（Phase Z′ — AUTOCLAUDE_DELEGATED 觀察態落地，ACT-172；AutoSDD_improving_02 W1）
- `tools/fsm_runtime/transition_rules.py` — `_HAPPY_PATH` 新增 `AUTOCLAUDE_DELEGATED`（出邊 `{IMPLEMENTATION, ESCALATION}`）+ `OBSERVATION_STATES` 新增成員
- `tools/fsm_runtime/fsm_runtime.py` — 新增 `enter_autoclaude_delegated()` / `exit_autoclaude_delegated()`（forced-transition，比照 `enter_memory_consolidation`）
- `tools/fsm_runtime/formal/SDD_FSM.tla` — `ObservationStates` + 入/出邊 action（`T_EnterAutoclaudeDelegated` / `T_AutoDelegToImpl` / `T_AutoDelegToEsc`）+ `Next` + Fairness `SF_vars(T_AutoDelegToImpl)`（Rule 9.18.1 雙源同步）
- `workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md` — 狀態轉換表新增 AUTOCLAUDE_DELEGATED 兩出口列
- `tools/fsm_runtime/tests/test_phase_z.py` — 8 新測試（enter/exit/邊界/不變量）
- `governance/ID_REGISTRY.yaml` — 登記 ACT-172、next_free 推進 act=173

### 形式化驗證
- **五軌 TLC 重跑全綠**（SDD_FSM/META_FSM/FLEET_FSM/COMPOSITION_FSM/OPTIMIZATION_FSM）：`_HAPPY_PATH` + `SDD_FSM.tla` 變更觸發 Rule 9.18.1 義務，TLC_DISTINCT/GENERATED/DEPTH 見 EVOLUTION_LOG。

---

## [v0.02] - 2026-06-12（Copy-on-Evolve 自 v0.01；v0.01 凍結唯讀）

### 新增（Phase Z — AutoClaude 執行引擎橋接，ACT-162~171）
- `workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md` — SDD 文件 → AutoClaude playbook 標準作業（compile-then-run 兩段式）
- `agent/specialized/sdd-playbook-compiler-zh.yaml` — SDD Playbook 編譯專家角色
- `governance/rules/R-9.38-playbook-translation-fidelity.yaml` — AT↔step 100% 雙向映射保真規則（違反→SPEC_AUDIT）
- 10 場景 SOP 各加「AutoClaude 自動化執行」小節（QuickRef 同步）
- `EVOLUTION_LOG.md` — 版本演化紀錄（含 TLC 證據與回退指引）

### 修正（AutoSDD_Defect_Log 分流項）
- DEF-01-001：`governance/RULES_INDEX.md` 計數過期（35→39 檔）+ next-act/next-rule 前緣同步
- DEF-01-002：`tools/fsm_runtime/formal/run_tlc.sh` 補「五軌請走 tlc_runner.py」legacy 註記
- DEF-01-003：補 `tools/__init__.py` 顯式 package 宣告

### 形式化驗證
- `_HAPPY_PATH` / `*.tla` 零修改 → 五軌 TLC 既有證明維持有效（N/A）；
  `AUTOCLAUDE_DELEGATED` 觀察態維持提案（落地前置條件見 SDD_AUTOCLAUDE_BRIDGE.md §5）

---

## [v0.01] - 2026-04-17

### 新增（SDD 轉型）

#### SDD 核心機制
- 整合 SDD Spec-First Gate（SCG-0~SCG-6）機制，建立 7 道規格品質閘門
- 新增 SDD Core Principles（`guides/system/sdd/SDD_Core_Principles.md`）— 三大支柱定義
- 新增 SDD Guide（`guides/system/sdd/SDD_GUIDE.md`）— SDD 快速指引

#### SDD Skills（6 個新增）
- `sdd-gate` — 執行 SCG 閘門驗證（所有情境通用）
- `sdd-review` — SCG-4 PR Review 輔助，驗證實作與規格一致性
- `spec-compliance-check` — SDD 文件格式與完整性驗證
- `rtm-generate` — 生成/更新需求追溯矩陣（RTM），確保 SCG-5 100% 覆蓋
- `contract-generate` — 生成 API Contract（OpenAPI 3.1）或 Consumer-Driven Contract
- `adr-generate` — 生成 Architecture Decision Record（ADR）

#### SDD 文檔模板（51+ 個）
- 新增 `docs_template/sdd/` 目錄，含 51+ 個 SDD 專屬文檔模板
- 涵蓋：需求（PRD/FRD/Invariant Spec）、架構（SRD/C4/ADR/As-Is/Trust Boundary）、測試（RTM/Contract Test Spec/Invariant Test Contract）、規劃（Gap Analysis/PBS/Refactor Plan）、品質（Tech Debt Spec/Code Quality Baseline）、安全（SAD/STRIDE/Compliance Matrix）、部署（Pipeline Spec/IaC Spec/Runbook）等

#### SDD CI/CD 規格（9 個）
- `cicd/SDD_CICD_BASE_LAYER.md` — 基礎層（全場景通用）
- `cicd/SDD_GREENFIELD_CICD.md` — Greenfield 場景
- `cicd/SDD_BROWNFIELD_CICD.md` — Brownfield 場景
- `cicd/SDD_REFACTORING_CICD.md` — Refactoring 場景
- `cicd/SDD_TESTING_CICD.md` — Testing 場景
- `cicd/SDD_PERFORMANCE_CICD.md` — Performance 場景
- `cicd/SDD_SECURITY_CICD.md` — Security 場景
- `cicd/SDD_MIGRATION_CICD.md` — Migration 場景
- `cicd/SDD_INTEGRATION_CICD.md` — Integration 場景

#### SDD 場景增強文件（10 個）
- 新增各情境 `SDD_{SCENARIO}_ENHANCEMENT.md`，定義 SDD Spec-First 流程補強
- 涵蓋全部 10 大情境：greenfield / brownfield / refactoring / documentation / devops / integration / migration / performance / security / testing

#### 文檔目錄結構（SDD 8 層）
- `docs/01_requirements/` — PRD / FRD / Invariant Spec / Third-Party API Research
- `docs/02_architecture/` — SRD / C4 / ADR / As-Is / Trust Boundary Map
- `docs/02_architecture/adr/` — ADR-{NNN} 架構決策記錄
- `docs/02_architecture/api/` — OpenAPI 3.1 Contract / Consumer Contract
- `docs/03_testing/` — RTM / Test Plan / Test Strategy / Defect Classification
- `docs/03_testing/contracts/` — Invariant Test Contract / Contract Test Spec / Chaos Contract
- `docs/04_planning/` — Gap Analysis / Refactor Plan
- `docs/04_planning/performance/` — Performance Baseline Spec（PBS）
- `docs/05_development/` — Living Doc Strategy
- `docs/06_quality/` — Code Quality Baseline / Tech Debt Spec
- `docs/06_quality/security/` — SAD / STRIDE / Compliance Matrix / Asset Inventory
- `docs/07_design/` — UI/UX / Database Design
- `docs/08_deployment/` — CI/CD Pipeline Spec / Monitoring Alert Spec / Release Notes / Runbook / Cutover Plan
- `docs/08_deployment/iac/` — IaC Specifications

---

### 修改（v0.09 → v0.01 升級）

#### Agents（21 個全部更新）
- 21 個 Agents 版本更新至 v0.01（7 core + 14 specialized）
- 核心 Agents 新增 SDD 技能：
  - `sa-analyst`：逆向規格工程（As-Is SRD）、Gap Analysis、Business Invariants 提取（INV-XXX）
  - `sd-architect`：As-Is C4 Model、ADR Archaeology、Before/After 架構對比、Migration Contract Map
  - `qa-tester`：As-Is 測試規格基線、Invariant Test Contract、Consumer Contract 測試
  - `dev-developer`：Strangler Fig 模式、Branch by Abstraction、Contract-First 開發
  - `code-analyzer`：Tech Debt 規格化（TD-XXX）、Code Quality Baseline Spec
  - `technical-writer`：Living Documentation 策略、ADR 維護、API 文件從 Contract 生成

#### Workflows（23 個全部更新）
- 所有 23 個 Workflows 整合 SCG 閘門驗證點
- 新增 SDD Spec-First Gate Workflow（`workflow/sdd-spec-first-gate/`）
- 核心 8 個 Workflow + 13 個場景特定 Workflow + 1 個 ADR Workflow

#### 場景 SOP（10 個全部更新）
- 所有 10 個場景 SOP 反映 SDD Spec-First 流程
- 每個場景新增強制 SCG 閘門步驟說明
- Brownfield / Refactoring / Migration 場景新增逆向規格工程步驟

#### 工具與腳本
- `tools/init_project.sh` 新增 `--sdd` 模式（v3.3-SDD），自動建立 SDD 8 層 docs/ 目錄結構

#### 指南文件更新
- `guides/user/onboarding/QUICK_START_GUIDE.md` — 新增 SDD 三大支柱說明與 SCG 閘門引導
- `guides/user/onboarding/SCENARIO_DECISION_TREE.md` — 各情境新增對應 SCG 閘門說明
- `guides/user/standards/PROJECT_DOCUMENTATION_STANDARDS.md` — 目錄結構更新為 SDD 8 層，FILE_DIRECTORY_RULES.md 引用
- `agent/AGENT_COLLABORATION_PATTERNS.md` — 新增「SDD SCG 閘門協作模式」章節
- `agent/AGENT_PHASE2_UPDATE_GUIDE.md` — 更新為 v0.09 → v0.01 升級指南
- `scenarios/SCENARIO_TRANSITION_GUIDE.md` — 新增「場景切換前的 SCG 驗證」強制章節
- `scenarios/SCENARIO_AGENT_MAPPING.md` — 新增各情境 SCG 對照說明與特殊情境說明

---

### 歸檔

- AISDLC v0.09 保留於 `AISDLC_v0.09/` 目錄（僅供參考，不修改）
- v0.09 版本歷史已歸檔至 `build/planning/archive/SDD_VERSION_HISTORY.md`

---

## [v0.09] - 2026-04-14（歸檔）

> 此版本為 AISDLC 開發專注版（Development-Focused Edition），版本歷史已歸檔至 `build/planning/archive/SDD_VERSION_HISTORY.md`。
>
> v0.09 定義了 10 大情境、21 個 Agents、23 個 Workflows 的基礎框架，v0.01 在此基礎上加入 SDD Spec-First Gate 機制完成框架轉型。

### 主要特性（v0.09 歸檔記錄）
- 10 大開發情境（含 migration）
- 21 個 Agents（7 core + 14 specialized）
- 23 個 Workflows
- 雙層 guides 架構（system + user）
- 中文優先 Agents（-zh.yaml）
- 開發專注版 docs/ 目錄結構（8 個目錄）
