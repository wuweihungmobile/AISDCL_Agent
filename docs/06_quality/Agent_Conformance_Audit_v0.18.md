# Agent 定義檔符規審查與修復報告（v0.17 審查 → v0.18 修復）

> **觸發**：使用者臨時請求「AISDLC_SDD_v0.xx 中 agent/* 所有 Agent 是否合 SDD 與目前架構，請 Architect/SA/SD/QA 專家檢視，不當則派全能專家修復」
> **日期**：2026-06-22 ｜ **審查標的**：AISDLC_SDD **v0.17**（最新凍結版）agent/ 全 26 個 YAML
> **修復落點**：Copy-on-Evolve **v0.18**（v0.17 凍結唯讀）
> **結論**：四專家 zero-trust 審查 → 11 項可自主修復 + broken template 全面重新接線（方案一）已套用並驗證 **OVERALL PASS**（ci-gate 全綠）
> **產出四件套**：本報告 + `Agent_BrokenTemplate_Disposition.md`（裁決書）+ `AutoSDD_Defect_Log.md`（DEF-AGTREV-001~004）+ `v0.18/EVOLUTION_LOG.md`·`releases/CHANGELOG.md`

---

## 0. 健康度總評

26 個 agent YAML（7 core 含模板 + 19 specialized）**基礎健康度良好**：YAML 全可解析、零佔位符殘留、name/id 全唯一且與檔名零錯置、零簡體/日韓殘留、persona agent 全含「編號選項協議」、5 個 sdd-* runtime agent 與 Rule 9 自動化防護**零越權**。問題集中在「符規一致性」與「跨檔引用」兩層，**無 P0 阻斷級結構崩壞**。

## 1. 四專家審查視角與分工

| 專家 | 視角 | 主要發現 |
|------|------|---------|
| **Architect** | 結構符規（template schema） | 缺 dependencies（2）、version 三處矛盾、icon 三撞；**誤報「4 變體缺 3 區塊」已剔除** |
| **SA** | SDD 方法論一致性 | SCG-4/5/6 命名漂移（跨 6+ 檔）、RTM Stage 編號與 Core_Principles 不符、generate_adr 路徑 |
| **SD** | 跨檔引用解析 + 架構一致性 | **pm-planner 幻影 id（P0）**、~80 broken template_path、WRONGDIR 3、BA 下游斷鏈 |
| **QA** | 完整性/品質/誠實性 | README/CLAUDE 計數失真（14 vs 19、漏列 5 runtime）、icon 三撞、合規稱呼不一 |

## 2. Zero-Trust 交叉裁決（Rule 7：不平均，親自查證）

審查出現**一處直接矛盾**，已親跑 grep 裁決：

- Architect 稱 qa-mobile/qa-web/sd-mobile/sd-web **缺 3 區塊**；SA 稱「用 `extends` 繼承、乾淨」；SD 稱「**無**任何 agent 用 extends」。
- **實測**（`grep -rn extends`）：四檔 line 12-13 **確用 `extends: "qa-tester"/"sd-architect"`**。→ **SA 正確；SD 錯誤；Architect 誤報**（缺 3 區塊係 extends 繼承所致的 by-design，非缺陷，已剔除）。

**P0 核驗**：orchestrator:183 與 subagent_contract.py:54 皆登記 `pm-planner`，但實際 PM agent id 為 `pm-po`；契約測試僅比對 yaml↔runtime（兩邊都寫 pm-planner 故過 CI），不比對實際 agent 檔 → 幻影確認為真（潛伏：目前 step_4 未實派 PM 故未咬人）。

## 3. 11 項可自主修復（v0.18，掌舵者定調：開 v0.18 修可自主項 + SCG 改角色閘門別名）

| # | 修復 | 範圍 | 獨立驗證 |
|---|------|------|---------|
| 1 | pm-planner→pm-po | orchestrator yaml + subagent_contract.py 雙端對稱 | grep 無殘留；契約測試 24 passed |
| 2 | icon 去碰撞 | BA 🧭 / code-analyzer 🔬 / qa-tester 🔍 | 三者互異 |
| 3 | agent.version 統一 v0.18 | 26 檔（含模板） | 無 v0.01/02/03 殘留 |
| 4 | 補 dependencies 區塊 | compliance / security（子鍵留空） | 兩檔皆有、未引新 broken path |
| 5 | SCG-4/5/6 → RG-TEST/RG-SEC/RG-PERF | 22 處（8 檔） | 舊名零殘留；integration SCG-3 未誤改；`spec_gate` tools/ 零解析故零退化 |
| 6 | RTM Stage→SCG 編號 | traceability 區（~6 檔）+ 04.sa rtm_at_column | 舊 Stage 零殘留 |
| 7 | qa-automation `# planned` 移出引號 | line 70,85 | 無引號內污染 |
| 8 | generate_adr → docs_template/sdd/adr | ~18 檔；output 產出路徑不動 | 無 docs/ 殘留 |
| 9 | WRONGDIR template 3 處重指 | SRD→core/srd、Perf/Sec_Test→core/tests | 目標 test -f 皆存在 |
| 10 | sd-web/sd-mobile 孤兒載入 | INIT greenfield supporting_agents | INIT yaml 區塊 safe_load 通過 |
| 11 | README/INIT 計數 + 雙 schema 宣告 | agent/README、specialized/README、INIT | 19 specialized（含 5 runtime）、補列、稱呼統一 |

## 4. by-design（非缺陷，已文件化）
- 5 個 sdd-* runtime agent 採 runtime schema（responsibilities/inputs/workflow/outputs），刻意不遵 persona 模板 → 已於 README 明文宣告雙 schema 並存。
- 4 變體 agent 用 `extends` 繼承 → 合理（Architect 誤報已剔除）。
- runtime agent 與 Rule 9 自動化防護高度相容、零越權自動跳過 🔴 人工閘門（三位審查者一致確認）。

## 5. broken template_path — 已決並套用（方案一，掌舵者 signoff）
- 掌舵者拍板**方案一 + 配套**：67 條 rewire 至既有最接近模板、26 條 Category D 正規化（移除 `../` 統一根相對）、9 條確無對應刪除（方案三 fallback）→ 功能性 broken ~75→**0**。
- 配套：新增 `AISDLC_SDD/scripts/agent_template_lint.py` 硬閘 + 接入 `ci-gate.sh`（掃最新版 agent template 引用存在性與根相對，杜絕再生）。詳見 `Agent_BrokenTemplate_Disposition.md` §5。

## 5b. 仍 routed（本輪未改）
- collaboration_rules BA 下游斷鏈（BA→SA/SD 單向、對方 upstream 未列 BA）→ 記 DEF-AGTREV-003（routed，下輪處理，屬語意一致性非斷裂）。
- 根/子 `CLAUDE.md` agent 計數陳述過期（25 vs 26、18 vs 19、4 vs 5 runtime）→ 因兩份 CLAUDE.md 整體仍 v0.01-scoped，piecemeal 改單一計數反不一致；記 DEF-AGTREV-004（routed，建議隨 CLAUDE.md 整體刷新一併修，本輪不動 live override 檔）。

## 6. 零退化驗證（v0.18 親跑實測）

| 檢查 | 命令 | 結果 |
|------|------|------|
| 完整 ci-gate | `bash scripts/ci-gate.sh` | **全綠**：v0.01:1478 / v0.18:1611 / scripts/tests:56 |
| arch_fitness | `arch_fitness --strict` | **fail=0**（exit 1＝僅 3 advisory warn，gate 判準 exit<2 PASS；與 v0.17 baseline 同 3 warn，零退化）|
| 三 lint | RFC / gitignore / **agent_template** | 全 ✅（新 agent_template_lint 已接入 ci-gate） |
| template 引用 | agent_template_lint | 功能性 broken=0（67 rewire + 26 正規化 + 9 刪除） |
| YAML 解析 | safe_load 26 檔 | 26/26 OK |
| Copy-on-Evolve 潔淨度 | `git add -A -n` | would-add 858、零 runtime 夾帶（.gitignore 補 v0.18 block）|
| 換行 | autocrlf=true | 工作樹混合 CRLF/LF 為良性，commit 正規化為 LF（與 v0.17 儲存形式一致）|

> 唯一改動之 runtime 程式為 `subagent_contract.py`（pm-po）；FSM/`transition_rules.py`/5 軌 `*.tla` 對 v0.17 逐位元零差異 → **不觸發五軌 TLC**（Rule 9.18.1）。

## 7. 多專家 zero-trust 複審結論

獨立複審專家（QA+Architect+SD 合一、主樹派發審 untracked 新檔、親跑全測）：**11 項逐項正確且完整、零退化、改動範圍嚴格限縮 11 項** → **OVERALL PASS**。

---

**修復成果置於 `AISDLC_SDD/AISDLC_SDD_v0.18/`（凍結 v0.17 唯讀保留）。** 尚未 commit/push——依專案紀律待掌舵者指示後直推 main。
