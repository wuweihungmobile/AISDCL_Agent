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
| 1 | pm-planner→pm-po | orchestrator yaml + subagent_contract.py 雙端對稱 | grep 無殘留；契約測試 19 passed（DEF-AGTREV-007 校正：原誤記 24，e796c1f 起逐位元實為 19） |
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

## 8. 獨立重審輪補強（2026-06-22，使用者再次請求；🔴 signoff：就地修 v0.18）

第一輪結案後，使用者再次請求「agent/* 全面 SDD/架構符規審查並修復」。依 zero-trust 紀律視為**獨立重審**：派 Architect/SA-SD/QA 三鏡獨立查證（不採信本文件前 7 節），過濾過度回報後揪出 **4 類前次未竟殘留**（DEF-AGTREV-005~007，詳見 `AutoSDD_Defect_Log.md` 重審輪追記）：

| # | 殘留缺陷 | 嚴重度 | 根因 | 修法 |
|---|---------|--------|------|------|
| 005 | 34 條 broken template 假綠（12 core 裸名 `template_path` + 19 `sdd_skills.*.template` 誤指 `docs/` + 3 dependencies 裸名） | P1 | `agent_template_lint` TOK regex 只認 `docs_template/` 前綴 → 裸名/docs 誤指**盲區**，前次「broken=0」僅窄範圍成立 | 12 方案一 rewire（1 刪欄）+ 19 全域重指 `docs_template/sdd/*` + 3 重指；lint 加 `BARE`+`dependencies.templates` YAML 雙檢查封閉盲區 |
| 006 | 4 specialized persona agent 缺 `collaboration_rules` | P2 | symmetry lint 只掃 7 core | 各補合角色 rules（peer 對互相對稱）；lint 加 `find_missing_collaboration_rules` presence 檢查 |
| 007 | `test_subagent_contract` 三處「24 passed」實為 19（從未 24）；README 同檔計數矛盾 | P3 | 前次誤記 + README 樹狀圖/Q&A 未同步 | 三處 24→19 校正；README 補列 5 sdd-* runtime、Q&A 校正 |
| 008 | **QA 閉環複審補抓**：005 的 BARE regex 只匹配 `.md`，漏 2 條 `.yaml` template（`05.sd:256`/`integration-specialist:536` 誤指 `docs/02_architecture/api/CONTRACT-TEMPLATE.yaml`）；真實總 broken=36（34+2） | P1 | 盲區修復的盲區（副檔名限縮 `.md`） | 2 條重指 `docs_template/sdd/api/CONTRACT-TEMPLATE.yaml`；BARE 改 `_TMPL_EXT`（md/yaml/yml/json）+2 測試 |

**新測試（機械防復發）**：`test_agent_template_lint.py` 9 case（前次此 lint 零測試；含 .yaml 誤指 + 合法 .yaml）+ `test_collaboration_symmetry_lint.py` +3 case。

**重審輪驗證（親跑）**：完整 `bash scripts/ci-gate.sh` **exit 0** — v0.01:1478 / v0.18:1611（零退化）/ scripts/tests:**81**（69→81）；`agent_template_lint`（盲區封閉後，副檔名涵蓋 md/yaml/yml/json）/ `collaboration_symmetry_lint`（含 presence 檢查）皆 ✅；arch_fitness fail=0；FRAMEWORK_STATUS fresh；FF-13 26/26 agent 合法；26/26 safe_load OK、template broken=0（窮盡掃描證）。**DEF-AGTREV-001~008 至此全閉。**

> 重審輪僅改 agent YAML 描述性內容（template_path 重指既有有效模板、additive 補 collaboration_rules）+ `AISDLC_SDD/scripts/` 共用 lint（versioned 目錄外 shared infra）+ 文檔；FSM/`*.tla` 逐位元零差異，不觸發五軌 TLC。

---

**修復成果置於 `AISDLC_SDD/AISDLC_SDD_v0.18/`（凍結 v0.17 唯讀保留）+ `AISDLC_SDD/scripts/` 共用 lint。** 待掌舵者指示後直推 main。

---

## 9. 第四輪獨立重審（2026-06-22，使用者再次請求 agent/* 全面 SDD/架構符規審查並修復）

依 zero-trust 紀律視為**獨立第四輪重審**（不採信前三輪報告）：派 **Architect / SA / SD / QA 四鏡**主樹並行親查證，過濾過度回報後揪出 **3 類前次未竟殘留**（DEF-AGTREV-014~016），掌舵者就兩項真正需 SSOT/scope 裁決者拍板後修復。

### 四鏡分工與結論
| 鏡 | 視角 | 結論 |
|----|------|------|
| **Architect** | 結構/schema（YAML 解析、persona 模板區塊、version、icon、dependencies） | **全查證乾淨，零 P0~P2 殘留** |
| **SA** | SDD 方法論（SCG 號碼/名稱/owner、scenario_usage、RTM stage） | SCG/RG-*/owner/stage **乾淨**；揪出 scenario_usage 計數 P1×1+P2×2 + frequency off-by-one |
| **SD** | 跨檔引用 + 架構（template_path、agent id、collaboration 對稱、Rule 9 相容） | template(54 條)/id 互引/skill/Rule 9 **乾淨**；揪出 upstream 反向斷鏈 lint 盲區 |
| **QA** | 完整性/誠實性（計數、簡體、佔位符、跨檔矛盾） | 計數誠實性/簡體**乾淨**；揪出 4 個 P2 文件引用/標頭殘留 |

### 掌舵者裁決（兩項 SSOT/scope 決策，Rule 7 浮現衝突而非取平均）
- **Q1 frequency SSOT**：四鏡查出 frequency 在「SCENARIO_AGENT_MAPPING.md 統計段」與「各 agent 自列場景數」系統性不一致。掌舵者裁定 **統計段為唯一 SSOT，全對齊**。
- **Q2 協作反向邊**：SD 鏡查出 upstream 反向單向邊（現行 lint 刻意只查 down→up + peer~peer）。掌舵者裁定 **補對稱邊 + 擴 lint**。

### 三類殘留修復（DEF-AGTREV-014~016，詳見 Defect_Log）
| # | 殘留缺陷 | 嚴重度 | 修法 |
|---|---------|--------|------|
| 014 | collaboration upstream 反向斷鏈：`ba` upstream←PM/PO 但 pm-po 結構化 collaboration_rules 完全不提 BA（惟 pm-po 自身 mermaid+review_participants 確有與 BA 協作）；symmetry lint 只查 down→up + peer~peer，漏 upstream 反向 | P2 | pm-po 補 `downstream→BA`（鏡像）；`collaboration_symmetry_lint` 加 upstream 反向檢查（接受 down 或 peer 為合法對側，不誤判視角差）+2 test。SD-1（sd↔pm-po 視角差）判 by-design 不動 |
| 015 | scenario_usage frequency 與 SSOT 系統性漂移（6 agent off-by-one）+ integration「1/10 vs 自列 4」內部矛盾 + pm-po 計入非法場景「Sprint Planning」（非 10 場景之一）+ sd-architect 漏 Migration（其 notes 自稱「唯一不參與純Testing」=9 卻寫 8）；全框架**無** frequency 守門 | P2 | 掌舵者 signoff「統計段為唯一 SSOT」全對齊 8 agent（freq 分子＝統計段＝清單項數三者一致，逐場景對應表交叉核對成員）；新增 `scenario_frequency_lint.py`（SSOT 跨源 + 內部一致雙檢查）+6 test + 接入 ci-gate；mapping doc Refactoring supporting 補 qa-automation 收斂統計段↔逐場景表雙視圖 |
| 016 | 文件交叉引用/標頭殘留：`README.md:244` 行號 71→76 失準；`core/README.md:68` 複數 `agents/` 斷鏈（實為單數 `agent/`）；`core/README.md` 標頭滯留 v0.01/2026-04-15；`AGENT_PHASE2_UPDATE_GUIDE.md:402` 離群 `/9`（DEF-AGTREV-010 同類修漏網） | P3 | 四處就地校正（行號、單數路徑、標頭 v0.18、/9→/10） |

### 第四輪驗證全綠（親跑 + QA 複審鏡 zero-trust）
- 26/26 agent YAML `safe_load` OK；8 agent frequency 三者一致（QA 複審鏡親數逐項吻合）；「Sprint Planning」確認非 `scenarios/` 10 場景；pm-po↔BA 對稱閉合。
- 完整 `bash scripts/ci-gate.sh` **exit 0**：v0.01:1478 / v0.18:1611（零退化，agent YAML/.md 非 pytest 標的）/ scripts/tests **81→89**（+2 collaboration upstream 反向 case + 6 frequency case）；6 lint 全 ✅（含新 `scenario_frequency_lint`）；arch_fitness fail=0（僅 FF-16 GC advisory，與基線同）；FRAMEWORK_STATUS fresh；FF-13 26 agent 全合法。
- 兩新/擴 lint **非空殼**（含 SSOT 漂移 / 內部矛盾 / upstream 反向斷鏈 / 突變退化負向 case，真能轉紅）。
- FSM/`transition_rules.py`/五軌 `*.tla` 對 v0.18 前狀態**逐位元零差異** → **不觸發五軌 TLC**（Rule 9.18.1）。

### by-design / 誠實標記（非缺陷）
- **SD-1（sd-architect upstream←PM/PO vs pm-po peer~SD 視角差）**：pm-po.peer 已含 SD，雙向皆有宣告，屬可接受的協作視角不對稱，**不強制統一階層**以免連鎖改寫；新 lint 刻意接受 down 或 peer 任一為合法對側故不誤判。
- **frequency off-by-one 的 SSOT 雙視圖**：統計段（SSOT）與逐場景對應表對 qa-automation/qa-tester 等的成員數本有微張力；本輪以統計段為準對齊 agent + 同步逐場景表（補 qa-automation 於 Refactoring），雙視圖現收斂。

**臨時審查塊 DEF-AGTREV-001~016 至此全閉、零 routed 殘留。** 修復成果置於 `AISDLC_SDD/AISDLC_SDD_v0.18/` + `AISDLC_SDD/scripts/` 共用 lint，待掌舵者指示後直推 main。

---

## 第五度獨立重審（2026-06-22，使用者第五次請求）— 四鏡 + parent 對鏡子再 zero-trust

派 Architect/SA/SD/QA 四鏡主樹並行重審（不採信前四輪宣稱）。四鏡共報 ~16 條，**parent 逐條親驗**：確認 **4 條真缺陷（DEF-AGTREV-017~020，全 fixed@v0.18）**、**駁回 4 類鏡子幻覺**。真缺陷共同根因＝機械 lint 涵蓋不到的「第三來源 / guides 層 / 碼定義」語意盲區。

### 真缺陷（已修，詳見 Defect_Log DEF-AGTREV-017~020）
- **017（P2）README 摘要表 frequency 第三來源盲區**：`agent/README.md` 核心表 ba/dev/qa 分子滯留 DEF-015 對齊前舊值（4/7/7 vs yaml SSOT 3/4/8）。`scenario_frequency_lint` 只查 yaml↔統計段↔清單、不查 README 表。**修**：對齊 3 分子 + pm-po 標籤；lint 加 `check_readme_table`（yaml 為基準）+2 test。
- **018（P3）SCG-5 owner 同族漏網**：`SDD_GUIDE.md:38` `qa-tester`→`qa-lead`（DEF-013 漏修同表；兩權威源皆 qa-lead）。
- **019（P3）導覽連結滯留 v0.01 絕對路徑**：`core/README:68-69`、`specialized/README:103`→相對路徑。`AGENT_PHASE2_UPDATE_GUIDE:578` 屬歷史敘述段**不改**（駁回 QA 鏡 stale-path 誤判）。
- **020（P3）角色 sub-gate 缺權威碼定義**：RG-TEST/SEC/PERF（v0.18 本輪所創別名）agent 21 處引用但 `SDD_GUIDE` 補充閘門表僅以名稱定義 → 補「代碼」欄 + 註腳。

### parent 駁回鏡子幻覺（zero-trust 對鏡子本身，誠實記錄）
1. **QA 鏡「FRAMEWORK_STATUS.md / scenario_frequency_lint.py / collaboration_symmetry_lint.py 不存在」＝假陰性**：三者皆存在、本輪 parent 親跑全綠；QA 鏡在 `v0.18/` 內找，實在父層 `AISDLC_SDD/`（FRAMEWORK_STATUS）與 `AISDLC_SDD/scripts/`（lint，versioned 目錄外共享 infra）。
2. **SD 鏡「BA↔SD/PM-PO/Dev 協作非對稱」＝假發現**：親讀 `02.ba` 實為 up←PM/PO、down→SA+SD、peer~QA 對稱完整（`collaboration_symmetry_lint` 通過為機械證）。
3. **Architect/SD 鏡「5 sdd-* runtime agent 缺 collaboration_rules / scenario_usage」＝by-design**：`README.md:107` 明文「runtime schema 刻意不遵 persona 模板」+ 兩 lint 明確豁免無 `persona:`/無 `scenario_usage` 者；部分 runtime agent 額外帶 collaboration_patterns 屬 additive 無害。
4. **QA 鏡「sdd-playbook-compiler 分類歧義」＝by-design**：FRAMEWORK_STATUS SSOT 計「runtime（sdd-*）＝5」README 與之一致；INIT「4 runtime+1 bridge」為更細子分仍 net 5/19，無數字錯誤。

### 第五輪驗證全綠（親跑 + parent zero-trust 對鏡子再驗）
- 26/26 agent YAML `safe_load` OK；README 表 7 列分子與 yaml 逐列吻合；SDD_GUIDE SCG-5 owner 三源一致；3 導覽連結相對路徑目標 `test -d/-f` 親驗存在；RG-* 21 引用全可追溯。
- 完整 `bash scripts/ci-gate.sh` **exit 0**：v0.01:1478 / v0.18:1611（零退化，agent .md/.yaml 非 pytest 標的）/ scripts/tests **89→91**（+2 README 表 case）；6 lint 全 ✅；arch_fitness fail=0（僅 FF-16 GAP-X1/X2 既存 advisory）；FRAMEWORK_STATUS fresh；FF-13 26 agent 全合法。
- 擴充 `check_readme_table` **非空殼**（README 7 vs yaml 4 漂移轉紅，突變實證）。
- FSM/`transition_rules.py`/五軌 `*.tla` **逐位元零差異** → **不觸發五軌 TLC**（Rule 9.18.1）。

**臨時審查塊 DEF-AGTREV-001~020 至此全閉、零 routed 殘留；4 類鏡子幻覺經 parent 親驗誠實駁回並記錄。** 修復成果置於 `AISDLC_SDD/AISDLC_SDD_v0.18/` + `AISDLC_SDD/scripts/` 共用 lint，待掌舵者指示後直推 main。

---

## 第六度獨立重審（2026-06-22，使用者第六次請求）— 四鏡 + parent 親驗

派 Architect/SA/SD/QA 四鏡主樹並行重審（工作樹乾淨、無 untracked，主樹派發合 DEF-24-001 判準；不採信前五輪宣稱）。**Architect 鏡 + QA 鏡獨立雙鏡收斂**揪出 **1 條 agent/* 範圍內真缺陷（DEF-AGTREV-021）**；SD 鏡零新缺陷；SA 鏡 agent/* 內 0 P0~P2 + 2 項標的外邊界觀察（OBS-1/OBS-2）。

### 四鏡分工與結論
| 鏡 | 視角 | 結論 |
|----|------|------|
| **Architect** | 結構/schema（YAML 解析、version、icon、persona 區塊、dependencies） | 26 YAML 全解析、version 全 v0.18、id/name/icon 零碰撞、persona 區塊完整、5 runtime + 4 extends 皆 by-design、零簡體日韓 → **唯 1 項 P3：COLLABORATION 標頭滯留 v0.01** |
| **SA** | SDD 方法論（SCG/RG owner、scenario_usage frequency、RTM stage、ADR 路徑） | RG-* 5 碼權威定義齊全、frequency 三向一致、SCG-5 owner 三源對齊、RTM stage 對齊 SCG → agent/* **0 P0~P2**；2 項標的外觀察（OBS-1 scenarios/ 統計段 vs 場景區塊、OBS-2 guides/ SCG-4 owner 粒度） |
| **SD** | 跨檔引用 + 架構（template_path、id 互引、collaboration 對稱、Rule 9） | 54 template 引用全命中磁碟、dispatchable 17 id 全存在無幻影、4 extends base 有效、collaboration 雙向皆宣告、Rule 9 人工閘門無越權 → **零新缺陷** |
| **QA** | 完整性/誠實性（計數、連結、標頭、簡體、佔位符） | 計數全鏈一致（SSOT 26＝7+19、runtime 5）、frequency README 表與 yaml 吻合、9 導覽連結可解析、零簡體/佔位符 → **與 Architect 收斂同 1 項 P3：COLLABORATION 標頭/內文/版本歷史滯留 v0.01** |

### 真缺陷（已修，詳見 Defect_Log DEF-AGTREV-021）
- **021（P3）現役協作指南版本滯留 v0.01**：`agent/AGENT_COLLABORATION_PATTERNS.md:4/6/7/22/653` 標頭與內文仍標 v0.01（該檔自建版 commit 後 5 輪 AGTREV 均未碰標頭），與同層三份 README（皆 v0.18）漂移。**修**：標頭→v0.18、最後更新→2026-06-22（對齊同層 README 慣例）；內文 `:22`/`:653` 敘述改 version-agnostic 根因消除防再漂移；版本歷史新增 v0.18 條目；`:849` v0.01 史實條目與 `AGENT_PHASE2_UPDATE_GUIDE.md`（升級指南主題本身）保留不動。

### agent/* 標的外邊界觀察（誠實記錄，本輪不擴 scope）
- **OBS-1（P3，routed）**：`scenarios/SCENARIO_AGENT_MAPPING.md:368` 統計段 qa-tester `8/10` vs 同檔場景區塊實際 6 處出現＝mapping 檔**內部**不一致（parent grep 親驗屬實）。agent yaml 已正確對齊掌舵者裁定之 SSOT（統計段），**agent/* 無缺陷**；矛盾在 scenarios/ 層，`scenario_frequency_lint` 未下探場景區塊。待掌舵者裁決是否另開 scenarios/ 清理輪。
- **OBS-2（P3，by-design）**：SCG-4 owner `SDD_GUIDE:37`=dev-senior vs `Core_Principles:53`=dev-senior/qa-lead，語意相容（主責 vs PR 雙人複核），非 agent/* 標的，不強制統一。

### 第六輪驗證全綠（親跑 + parent zero-trust 對鏡子再驗）
- 26/26 agent YAML `safe_load` OK；`AGENT_COLLABORATION_PATTERNS.md` 除 `:853-854` 歷史條目外零 v0.01 殘留；同層四份文件版本標頭全 v0.18 收斂。
- 完整 `bash scripts/ci-gate.sh` **exit 0**（基線實測 v0.01:1478 / v0.18:1611、6 lint 全 ✅、arch_fitness fail=0、FRAMEWORK_STATUS fresh、FF-13 26 agent 全合法）；本輪僅改 1 個 .md 描述性標頭/敘述（**非 pytest/lint 標的**故 ci-gate 數字與基線逐位元一致＝零退化）。
- FSM/`transition_rules.py`/五軌 `*.tla` **逐位元零差異** → **不觸發五軌 TLC**（Rule 9.18.1）。

### parent 對鏡子之過度回報控管（誠實記錄）
- 本輪四鏡**未**出現前輪那類「把存在的東西報成不存在」之假陰性（QA 鏡已知前輪教訓、本輪明確查證 FRAMEWORK_STATUS/lint 在父層）；雙鏡（Architect+QA）對 DEF-021 獨立收斂提高可信度，parent 親讀四處 + 同層 README 對照後採信。
- SA 鏡之 OBS-1/OBS-2 正確標示為「根因在 agent/* 標的外」，parent 親驗後同意不擴 scope（Rule 3 surgical + 使用者標的為 agent/*）。

**臨時審查塊 DEF-AGTREV-001~021 至此全閉；OBS-1 routed、OBS-2 by-design 誠實記錄。** 修復成果置於 `AISDLC_SDD/AISDLC_SDD_v0.18/`，待掌舵者指示後直推 main。
