# SDD_improving_Automation_24 — Phase X 藍圖（具身接地轉向 / Embodied Grounding Pivot）

**主題**：**把 meta-evolution 迴圈接地回具身評估器（Embodied Evaluator Re-grounding）+ 首次行使鷹架代謝（Scaffold Metabolism Genesis）+ meta⁹ 停機臨界的誠實 horizon 對賬**——Phase L~W（meta¹~meta⁸）連續 8 個 phase 把系統的自我演化能力全押在「合成算子代數的自我發明」上（held-out 語料 + 形式化停機證書），愈來愈抽象、也愈來愈**脫離真實軟體交付**；而本框架**早在 Phase H（ACT-045~055）就建好了完整的「具身評估器 + 運行時可觀測性 + 常駐鷹架 GC」**，卻被近 8 個 meta phase 晾在一邊（GC 至今 **0-fire**）。本 Phase 不再往算子代數塔上加第 9 層（meta⁹ 會真正跨入圖靈完備、無靜態 device 可保證停機，違反 R-9.35.5），而是**轉向 Anthropic「大膽移除冗餘鷹架」與 OpenAI「絕對運行時可觀測性」的最誠實兌現**：把元迴圈的「生成-評估分離」從合成語料重新接地到 `sdd-evaluator` 的沙箱實跑 + `observability_query`，並讓 `sdd-gc` 第一次真正代謝一個過時鷹架。

**目標等級**：L10 完整 · 離線活體 meta⁸ 迴圈（Phase W 已達）→ **L10 完整 · 具身接地的元迴圈切片**（系統的自我演化不再只在合成算子代數上自證，而是**把「生成器產出 → 具身評估器在隔離沙箱實跑 → 運行時可觀測性推理客觀錯誤 → 鷹架 ROI 代謝」這條 Phase H 既有具身鏈，接地進 meta-loop 的自我演化判定**）。

**建立日期**：2026-06-05
**前置基線**：Phase W 完整（ACT-153~155 / R-9.35，commit `0e860cb`；pytest **1401 passed / 4 skipped**〔non-chaos PR gate 基線〕；五軌 TLC 全 No error：`SDD_FSM` 42 reachable / 831 distinct、`META_FSM` 13 distinct、`FLEET_FSM` 7、`COMPOSITION_FSM` 21、`OPTIMIZATION_FSM` 12；chaos 100 輪 bounded_ratio=1.0；`arch_fitness` 15 FF structural fail=0〔含 1 條既有 FF-5 advisory：CLAUDE.md §9 約 4.7 頁 > 1.2 頁目標，故全量 score=1，非 0〕）
**對應提示**：Karpathy 式「首席 AI 自動化架構師」前沿評估——驗證「圖靈完備自動化閉環」並進化 Level 10 自治。本份**承認提示前沿清單已 100% 在 Phase H~W 落地**，故價值不在重述清單，而在用同一套前沿透鏡**反向稽核**：被建好的具身能力是否仍接地、是否被元迴圈漂移晾置、鷹架是否該代謝。
**執行策略（本輪，依使用者 2026-06-05 拍板）**：**兩者並陳藍圖（具身轉向為主線 + meta⁹ 誠實 horizon 章節）+ 可驗證切片落地（不消耗 ACT/R-9.x，走既有 `SDD_SELF_EVOLUTION` 的 FSE/arch_fitness 自我演化通道，落 FF-16 / 路線圖 R16，實跑 pytest）**。Phase X 完整版（ACT-156~158 / R-9.36，把具身評估接地進 META_FSM 自我演化判定）登記為下一輪 EXECUTING 候選，本輪只落「量測接地度 + 鎖具身鷹架不被 bit-rot」這一可驗證、低風險切片。

> 🔴 **編號策略說明（與 Phase A~W 不同，刻意為之）**：本輪可驗證切片**不徵用** ACT/R-9.x 號（`next_free` 維持 act 156 / rule 9.36 不動）。理由：新增一條 `arch_fitness` 適應度函式（FF-16）屬 `workflow/sdd-self-evolution/SDD_SELF_EVOLUTION.md` 的 **FSE 自我演化路線圖（R1~R15 既有，本輪續 R16）**，與 Phase A~W 的「ACT + R-9.x 治理規則 + 五軌 TLA」重型機制**正交**——FF 是「唯讀、確定性、會回歸」的架構守門，非新治理規則、非新 FSM 狀態。這正是框架自身 §0「治理規則本身的熵增無收斂閘」的解法通道，沿用 R15（FF-15）完全相同的落地形態。**完整版 Phase X（把具身評估接地進元迴圈自我演化判定，需新 META_FSM 不變量 + ACT-156~158 / R-9.36）列為下一輪候選，待本輪 signoff。**

> 🟦 **Level 量表釐清（提示 header 寫 Level 10、Output Requirement 4 寫 Level 5 的不一致）**：本框架自有 L0~L10 成熟度量表（見 §3.3）。提示通用模板的「Level 5 自治開發流程」對應本框架早在 Phase E 跨越的 L5（學習層入口）。本份**不降級**回 L5——延續框架實況推進「L10 完整之具身接地切片」，並在 §3.3 對賬「為何此刻的最高 ROI 不是 meta⁹ 加塔，而是具身接地 + 鷹架代謝」。

---

## 0. 為什麼是 Phase X？——對既有設計的誠實剖析（含 `<thinking>`）

<thinking>
提示要我以 Karpathy 式首席 AI 自動化架構師的高度，用 Anthropic 對抗框架（生成-評估分離、評估器實體操作、主觀標準量化、動態演進大膽移除鷹架）+ OpenAI 環境防護（漸進式揭露、智慧體可讀性、絕對運行時可觀測性、不變量 linter + 常駐 GC）兩套哲學，驗證這套系統是否具備「圖靈完備的自動化閉環」、並推進到 Level 10。附三個必查漏洞（狀態轉換 / 上下文衰減 / 停機問題）與一份 self-verification（Spec 寫錯 → 測試永不過）。

延續 Phase K~W 的鐵律：**第一步是對賬（audit），不是設計（design）。** 這套系統不是 greenfield——它走過 Phase A~W、是自陳「L10 完整 + 離線活體 meta⁸ 迴圈」的成熟框架，有 1401 個 pytest、五軌 TLC、100 輪 chaos、15 個架構適應度函式。盲目重述提示的前沿清單只會重造輪子、甚至羞辱這套系統的工程深度。我的任務是反過來用這兩套哲學當**手術刀**，去切：**這套系統把前沿清單做到極致之後，自己漂移出了什麼新的、grep 可證的結構性病灶？**

【零、先把提示的「前沿清單」逐項對賬到磁碟——證明它不缺能力，缺的是「能力的接地與代謝」】
我逐項 grep / 讀檔對賬，結論是提示視為「建議」的東西**全部已落地**，且落地得比提示描述的還深：

| 提示前沿建議 | 框架實況（磁碟接地） | 狀態 |
|---|---|---|
| 評估器有 Playwright 類工具、在隔離環境實操 App、捕捉客觀錯誤 | `agent/specialized/sdd-evaluator-zh.yaml`（Phase H/ACT-046）+ `tools/fsm_runtime/sandbox_runner.py` + `EXECUTION_EVALUATION` 狀態（`transition_rules.py:59` 狀態 key 定義）；verdict ∈ {pass, runtime_fail, spec_defect} | ✅ 已建 |
| 運行時可觀測性 LogQL/PromQL 暴露給 AI 推理錯誤 | `tools/fsm_runtime/observability_query.py`（Phase H/ACT-053）`logql_lite()`/`promql_lite()`，讀 `data/observability/*.ndjson` | ✅ 已建（lite + file-based，OPEN-10.6 禁 HTTP） |
| 生成-評估分離（GAN 啟發、避免盲目自信）+ 主觀標準量化 | `output_quality_scorer.py`（OQS）+ held-out-corpus oracle（oracle 對 generator 不可見）+ skeptic 對抗 refute（Rule 9.8）+ ADVERSARIAL_EVALUATION 狀態（ACT-074） | ✅ 已建（且推到 meta⁸） |
| 漸進式揭露、docs/ 單一真實來源、放棄龐大單一指令檔 | `rule_loader.load_for_state()` 逐態注入 + CLAUDE.md §9 裁剪 724→43 行 + `governance/rules/R-*.yaml` registry | ✅ 已建（FF-2 量化遷移健康度） |
| 不變量 linter 防護邊界 + 常駐 GC 清技術債 | `tools/arch_fitness/arch_fitness.py`（15 個 fitness function）+ `agent/specialized/sdd-gc-zh.yaml` + `SCAFFOLD_GC` 狀態 + `scaffold_gc` 模組 | ✅ 已建 |
| 動態演進框架、大膽移除不再需要的鷹架 | Rule 9.20 GAE（鷹架畢業）+ `scaffold_roi`（fire/catch/false_positive）+ FF-9 data-gated 0-fire 偵測 | ⚠️ **已設計、從未行使（0-fire）** |
| Planner 宏觀規格擴展 → Generator/Evaluator 微觀合約談判 | `INTENT_DECOMPOSITION` 狀態（ACT-081）+ `TEST-CONTRACT-NEGOTIATION` 模板 + workflow `CONTRACT_NEGOTIATION` | ✅ 已建 |

**對賬結論翻轉了任務的性質**：提示要我「驗證是否具備圖靈完備自動化閉環」——答案是**早已具備且過度完備**。圖靈完備性來自「嵌在迴圈裡的 LLM 生成器 + 無界 `docs/` 紙帶」，保證停機來自「把不可判定的 LLM 包進可判定的有限狀態監督者（五軌 FSM + retry/context budget + 良基停機證書）」——Phase O~W 已反覆形式化證明這條拆分。所以本份**不**重證它。我要切的是**對賬時跳出來的兩個刺眼異常**，它們恰好就是提示自己最強調的兩個哲學（評估器接地、大膽移除鷹架）在這套系統裡**被它自己的成功漂移掉了**：

【一、核心病灶 GAP-X1：元迴圈接地真空（Meta-loop Grounding Vacuum）——生成-評估分離是真的，但在元迴圈層「評估」評的是合成算子代數，不是實跑的軟體】
Phase H 把具身評估器（`sdd-evaluator` + `sandbox_runner` + `observability_query` + OQS）接進**微觀迴圈**：每個 feature 的 `IMPLEMENTATION → EXECUTION_EVALUATION`，在沙箱實跑 App、用 logql_lite 對日誌推理根因、產 verdict。這是提示「評估器實體操作」的教科書級兌現。

但**系統真正會自我演化、自我發明的地方不是微觀迴圈，是 META_FSM（Phase L~W 的元迴圈）**。而元迴圈的「生成-評估分離」評的是什麼？grep `dimension_necessity_oracle` / `evaluate_genesis_*`：**它評的是「自我發明的算子在 12 個凍結 feature 語料上的覆蓋率勝率」——一個合成的、純數值的、與任何實跑軟體無關的算子代數。** 元迴圈的 Evaluator 從不啟動沙箱、從不查一行真實日誌、從不跑一個真 App。

這就是 GAP-X1：**系統的自我演化能力（meta¹~meta⁸）是在「玩具算子代數」上被證明的，不是在「具身的真實軟體交付」上被證明的。** 用 Anthropic 的話說——元迴圈的 Evaluator 對「自我發明的東西在真實環境裡到底有沒有用」**盲目自信**，因為它的 oracle 是合成語料，不是具身觀測。提示的「評估器實體操作能力（Playwright / 隔離環境 / 客觀錯誤）」在**微觀層滿分、在元迴圈層 0 分**。grep 證據：`operator_recursion_genesis.py` / `dimension_necessity_oracle.py` **零** import `sandbox_runner` / `observability_query` / `output_quality_scorer`。生成-評估分離在元迴圈是真的，但**未接地（un-grounded）**。

【二、核心病灶 GAP-X2：鷹架代謝從未行使（Scaffold Metabolism Never Fired）——「大膽移除鷹架」寫在憲法裡，但 GC 0-fire】
提示最 Karpathy 的一句是「動態演進框架，大膽移除不再需要的鷹架」。本框架把這句做成了制度：Rule 9.20 GAE（規則畢業）、`scaffold_roi`（每條規則記 fire/catch/false_positive）、`sdd-gc` 常駐 agent、`SCAFFOLD_GC` 狀態、FF-9 偵測長期 0-fire 鷹架。**制度齊備，但 grep `scaffold_gc` 的 runtime 帳本 + 讀 FF-9 邏輯：aggregate fire == 0 < 門檻 20，gate 永遠關閉——`sdd-gc` 至今沒有真正提議退役過任何一個鷹架。**

更尖銳的是：**最該被代謝的鷹架，恰恰是 meta⁵~meta⁸ 這座塔本身。** Phase T~W 連續 4 個 phase 自我發明「算子（T）/ 字母（U）/ 深度（V）/ 互遞迴（W）」，每一層都更抽象、held-out 語料每層只有 12 條、且**從未有一個被自我發明的算子真正進入過任何真實 SDD 專案的交付**。用 GAE 的語言：這些是 `fire=0` 的鷹架——它們防的是「假想中系統會自我發明出有害算子」的危害，但系統從沒在真實交付裡發明過算子。**提示「大膽移除鷹架」在這裡有一個血淋淋的對象，而框架的 GC 卻從沒敢開第一槍。** 這是 GAP-X2：代謝機制存在，但「代謝肌肉」從未收縮過——它不知道自己會不會動。

【三、用提示三個指定漏洞視角逐一覆查】

(A) 狀態轉換——「Planner 宏觀 → Generator/Evaluator 微觀合約談判」這層**在微觀迴圈存在（INTENT_DECOMPOSITION + TEST-CONTRACT-NEGOTIATION），但在元迴圈缺一個「具身合約」**。
微觀層：feature 開發前，Planner（intent）擴展規格 → Generator（dev-senior）與 Evaluator（sdd-evaluator）對「TEST-CONTRACT-AGREEMENT」達成共識（每 AC 的 pass/fail 準則凍結）→ 才開發。這完全符合提示「開發前對測試標準達成共識」。
元迴圈層：Generator（`operator_genesis`）發明算子 → Evaluator（`necessity_oracle`）用合成語料評勝率 → 但**沒有一個「具身合約」說『這個自我發明的能力，要在一個真實沙箱專案上證明它降低了 OQS 失敗率 / 真實 runtime 錯誤』**。元迴圈的合約談判是「合成勝率達標」，不是「具身客觀錯誤下降」。→ 這是 GAP-X1 在狀態轉換視角的投影。

(B) 上下文衰減（Context Degradation）——**這套系統是反例教材，但具身接地會引入新的脈絡管理需求**。
框架的脈絡治理是模範生：`context_ledger_pre/post` 四階 token 預算（70/85/90/95%）、95% 強制停機產 Context Snapshot、`stage-compaction` 凍結後壓縮、Decision Trace 注入最近 5 筆、Session 恢復流程。提示的「脈絡重置 + 結構化交接避免脈絡焦慮」已滿分。**但具身接地會帶來一個新衰減面**：沙箱實跑的日誌（`logs.ndjson`）會無界增長，若元迴圈每次自我演化都全量讀日誌進主線脈絡，會炸 token。故本份的接地設計**必嚴守「查詢而非灌入」**——沿用 `observability_query.logql_lite`（已是 `{level="error"} |= "deadlock"` 的選擇器查詢，不是全量 dump），讓 Evaluator 在隔離 context 查根因、只把「verdict + 一行根因摘要」交回主線。這是把 OpenAI「可觀測性」與框架「脈絡治理」**正確縫合**的關鍵，避免接地反而引爆脈絡焦慮。

(C) 停機問題與防護（Halting Problem & Guardrails）——**meta⁹ 是框架自己畫的不可逾越線；正確的回應不是逾越它，而是橫向接地**。
這是本份與 Phase W roadmap 的正面交鋒。Phase W 的 R-9.35.5 白紙黑字：**「讓算子代數真正跨入圖靈完備（移除良基測度約束 / 帶無界記憶使停機不可判定）而謊稱可證停機」= 違反即停機**——因為「真圖靈完備無靜態 device 可保證停機，須誠實標為 horizon」。memory roadmap 也載「續推 ACT-156/R-9.36（…真·圖靈完備算子代數 meta⁹+ 無靜態 device 可保證停機）」。

**這就是停機問題視角給出的最深判斷**：算子代數自我發明這條軸，**已經抵達它的理論天花板**。Phase T 用「有界步數」、U 用「閉包步數」、V 用「cost==depth」、W 被迫換成「良基測度終止證書」——每一層停機證明都更費力，而 W 已經逼到「可判定 vs 不可判定」的臨界線本身。再走一步（meta⁹：算子帶無界記憶 / 真自由互遞迴）就是停機不可判定，**沒有任何靜態 device 能救**。框架的憲法已經誠實地把這標成紅線。

提示說「遇到死迴圈啟動退場機制時，系統是否能引導人類提供 AI 缺失的『工具』或『環境限制』，確保人類維持設計環境掌舵者高度」。把這句**套到框架自己身上**：算子代數塔撞到 meta⁹ 停機天花板，就是元迴圈層的「死迴圈臨界」。正確的退場不是硬闖（那違反 R-9.35.5），而是**人類舵手介入、橫向轉軸**——把投資從「垂直加塔（更抽象的自我發明）」轉到「水平接地（讓既有的具身評估器真正餵養元迴圈 + 第一次行使鷹架代謝）」。**這正是 Anthropic「大膽移除鷹架」與「停機防護引導人類補環境」兩條哲學在 meta⁸→meta⁹ 臨界點的合流。** Phase X 就是這個轉軸。

【四、Self-Verification 內部模擬（提示指定：Spec 寫錯 → 測試永不過）】
我讓「Spec 寫錯導致測試永不過」這個極端案例跑過接地後的流程，確認它優雅停機、導人類修 Spec，而非無限重試燒 token——並確認**接地不會破壞既有的這條停機保證**（見 §5 完整模擬）。要點：具身評估器的 verdict 三分類 {pass, runtime_fail, **spec_defect**} 裡，`spec_defect` 正是「實作對了、但測試契約本身矛盾 / 物理不可行」的客觀信號——`EXECUTION_EVALUATION → SPEC_AUDIT`（而非 → IMPLEMENTATION 重試）。接地讓這條判斷**從合成語料升級為沙箱實跑的客觀證據**：當 Spec 寫錯，沙箱實跑會持續 runtime_fail，但 `spec-logical-validator`（SLV）+ retry budget（SCG 3 / PR 5）觸頂 → ESCALATION → 導人類修 Spec。接地**強化**而非削弱這條：因為 `observability_query` 能讓 Evaluator 在日誌裡指出「為何永遠失敗」，把「無界重試」更早地轉成「客觀 spec_defect 證據 → 人類舵手」。

【五、把兩套哲學收斂成一句 Phase X 設計準則】
- OpenAI（單一真實來源 / 智慧體可讀性 / 絕對可觀測性）：**元迴圈的自我演化判定，必須能引用具身觀測（沙箱 verdict + logql 根因 + OQS），而非只引用合成勝率**；且這些觀測落地為 Markdown/YAML 可推理產物。
- Anthropic（生成-評估分離 / 評估器實體操作 / 動態演進大膽移除鷹架）：**生成-評估分離要接地到具身評估器**（評估器已有實體操作能力，只是沒被元迴圈用上）；並**第一次真正行使鷹架代謝**——讓 `sdd-gc` 對「meta⁵~meta⁸ 塔」這個最該被代謝的對象，至少跑出第一份有界、advisory、人類掌舵的退役 ROI 提案（不自動退役，守 Rule 8 + Rule 9.20）。
一句話：**停止加塔，開始接地與代謝。** 這是把這套已經 L10 的系統，從「在玩具算子代數上自證自治」拉回「在具身真實交付上接地自治」的關鍵轉軸。
</thinking>

本次提示所列前沿清單，**已 100% 對應到 Phase H~W 落地元件**（對賬見上 thinking 第零節）。「圖靈完備自動化閉環」**已正面驗證成立且過度完備**。Phase X 的價值不在重述清單，而在用同一套前沿透鏡**反向稽核**，挖出框架因自身成功而漂移出的 **3 個結構性病灶**——其共同主軸是：**框架把「具身評估器 + 鷹架代謝」建好後，元迴圈卻連續 8 個 phase 漂移進合成算子代數自我發明，把這兩套最該接地的能力晾置**。

| # | 病灶（用提示三漏洞視角挖出） | grep / 讀檔證據 |
|---|------------------------------|------------------|
| **GAP-X1** | **元迴圈接地真空**——具身評估器（`sdd-evaluator`+`sandbox_runner`+`observability_query`+OQS）只接微觀 `EXECUTION_EVALUATION`；元迴圈（META_FSM）的自我演化判定只引用 `dimension_necessity_oracle` 的合成語料勝率，**從不啟動沙箱 / 查真實日誌 / 跑真 App**。生成-評估分離在元迴圈為真但**未接地**。 | `operator_*_genesis.py` / `dimension_necessity_oracle.py` **零** import `sandbox_runner`\|`observability_query`\|`output_quality_scorer` |
| **GAP-X2** | **鷹架代謝從未行使**——Rule 9.20 GAE + `scaffold_roi` + `sdd-gc` + `SCAFFOLD_GC` + FF-9 制度齊備，但 aggregate fire==0 < 門檻 20，GC gate 永遠關閉、**從未提議退役任何鷹架**；最該被代謝的 meta⁵~meta⁸ 塔（fire=0，從未在真實交付發明過算子）卻無人敢開第一槍。 | FF-9 `SDD_FF9_STALE_MIN_AGGREGATE` gate；`build/reports/gc/` 無 SCAFFOLD-ROI 退役提案歷史 |
| **GAP-X3** | **meta⁹ 停機臨界 = 該轉軸的信號**——算子代數自我發明軸已抵理論天花板；再走一步（meta⁹ 真圖靈完備）即停機不可判定、無靜態 device 可救（R-9.35.5 紅線）。提示「停機防護引導人類補環境/限制、維持舵手高度」在此 = **人類介入、橫向接地，而非垂直硬闖**。 | R-9.35.5 / `INIT.md:190` 禁令；memory roadmap「meta⁹ 無靜態 device 可保證停機」 |

**三病灶的共同主軸**：Phase W 讓人類站上「審系統在互遞迴上自我發明 + 良基停機證書」的最高抽象高度，但**這座塔的每一層都離真實軟體交付更遠**。Phase X 把人類拉回**最該掌舵的地方**——審「系統自我演化出的能力，到底在具身的、實跑的、可觀測的真實環境裡有沒有用、該不該保留」。這正是 L10 完整「離線活體元迴圈」缺的最後一塊：**不是更深的自我發明，而是把自我發明接地到具身評估 + 學會代謝自己。**

---

## 1. Agentic 閉環狀態機設計（生成 / 評估 / 合約談判，含具身接地）

> 提示 Output Requirement 2。本節給「元迴圈具身接地」的嚴謹狀態流轉。**刻意不增第六形式化軌**（承 Phase O~W「協調層/元迴圈不污染單軌 SDD_FSM」），具身接地以 **既有 `EXECUTION_EVALUATION` 狀態 + 既有 `META_FSM` 不變量** 承載；完整版（下一輪）才補 META_FSM 不變量。

### 1.1 現況：兩條分離的生成-評估迴圈（病灶可視化）

```
微觀迴圈（Phase H 已接地，✅）：
  Planner          Generator          Evaluator（具身）            裁決
  INTENT_DECOMP ─► IMPLEMENTATION ──► EXECUTION_EVALUATION ──────► {pass→PR_REVIEW
   (規格擴展)       (dev-senior 寫碼)   sandbox_runner 實跑          runtime_fail→IMPLEMENTATION
        │                              observability_query 查根因    spec_defect→SPEC_AUDIT}
        └─ TEST-CONTRACT-NEGOTIATION（開發前凍結 oracle，合約談判）

元迴圈（Phase L~W，❌ 未接地）：
  Generator                    Evaluator（合成）            裁決
  operator_*_genesis ───────► dimension_necessity_oracle ─► {勝率達標→proposed-signoff}
   (自我發明算子/互遞迴)         held-out 12 條合成語料         ⚠️ 從不啟動沙箱
                                                              ⚠️ 從不查真實日誌
                                                              ⚠️ verdict 無 OQS 接地
```

### 1.2 Phase X 目標：把元迴圈的 Evaluator 接地到具身評估器

```
            ┌────────────────────────────────────────────────────────────────────┐
            │         META_FSM 自我演化（具身接地後；不增軌，補既有不變量）          │
            └────────────────────────────────────────────────────────────────────┘

  [META_PROPOSE] ──► [SYNTHETIC_EVAL] ──► [EMBODIED_GROUNDING_GATE] ──► [HUMAN_SIGNOFF]
   生成器自我發明      合成 oracle 勝率      🆕 具身接地閘：把自我發明的能力          🔴 人類掌舵
   （現有）            （現有，必要非充分）   套到一個真實沙箱基準專案，由               （現有，K=1）
                                           sdd-evaluator 實跑 + observability_query
                                           查客觀錯誤，產 grounded-verdict
                                              │
                          ┌───grounded pass───┤───grounded fail / 無具身增益───┐
                          ▼                                                     ▼
                   [META_ADOPT]                                         [META_REJECT]
                   （納入，churn 記帳）                                  （退回，不污染棘輪）
                          │
                          ▼
                   [SCAFFOLD_GC] 🆕 首次行使
                   sdd-gc 對全鷹架算 ROI，對 fire=0 的 meta-塔發 advisory 退役提案
                   （不自動退役，交 LEARNING_COMMIT 人工 gate）
```

| 狀態 | 角色 | 守門（客觀） | 接地點 |
|------|------|--------------|--------|
| `META_PROPOSE` | 生成（現有） | 有界生成文法內可枚舉 ≤ budget | `operator_*_genesis` |
| `SYNTHETIC_EVAL` | 評估·合成（現有） | held-out 勝率 ≥ tier（**必要非充分**） | `dimension_necessity_oracle` |
| `EMBODIED_GROUNDING_GATE` | 評估·具身（🆕 Phase X 完整版） | 自我發明能力在真實沙箱基準專案上，OQS 不退步 ∧ 無新增 runtime_fail（`sdd-evaluator` 實跑 + `observability_query` 客觀證據） | `sandbox_runner` + `observability_query` + `output_quality_scorer` |
| `HUMAN_SIGNOFF` | 掌舵（現有，K=1） | 🔴 人工 signoff（Rule 8 / 9.27~9.35） | `steersman_renderer` |
| `META_ADOPT` / `META_REJECT` | 收斂（現有） | churn 記帳，`GraduationRatchet`/`ChurnBounded` | `META_FSM` |
| `SCAFFOLD_GC` | 代謝（🆕 首次行使） | `scaffold_gc.compute_proposals()` 對 fire=0 鷹架出 advisory 退役提案；**不自動退役** | `sdd-gc` + `scaffold_roi` |

**合約談判（Contract Negotiation）的元迴圈升級**：現況元迴圈的「合約」是合成勝率達標；Phase X 把合約升級為**雙簽具身合約**——`SYNTHETIC_EVAL` 勝率（必要）∧ `EMBODIED_GROUNDING_GATE` 具身不退步（充分）。即「自我發明的能力要被納入，不只要在合成語料贏，還要在一個真實沙箱專案上由具身評估器證明它沒讓客觀 OQS / runtime 錯誤變糟」。這正是提示「開發前對測試標準達成共識」推到元迴圈、且**接地到實體操作**的兌現。

### 1.3 本輪可驗證切片落地的子集（不增軌、不消耗 ACT/R）

完整 1.2 需新 META_FSM 不變量（`EmbodiedGroundingBounded`）+ ACT-156~158 / R-9.36，列下一輪。**本輪只落最小可驗證、能鎖住病灶不惡化的一塊**：

> **FF-16（arch_fitness 第 16 條適應度函式 / FSE 路線圖 R16）：具身評估器 & 鷹架代謝工具鏈接地完整性。**
> 把 GAP-X1/X2 從「藏在元迴圈漂移裡、無人量測的盲區」轉為**靜態可稽核、會回歸的不變量 + advisory backlog**——與 FF-11（Skill）/ FF-13（Agent）/ FF-15（Template）的 artifact 結構守門、FF-7/10/14 的引用完整性家族同源。詳見 §4。

---

## 2. 環境建構與記憶體管理策略（Prompt / 漸進式揭露 / 不變量防護欄）

> 提示 Output Requirement 3。框架在此面已是模範生，本節給「具身接地不破壞既有脈絡治理」的工程縫合。

### 2.1 Prompt / 漸進式揭露（Progressive Disclosure）—— 接地不得回退單一巨檔

- **沿用 `rule_loader.load_for_state(state)` 逐態注入**：具身接地的元迴圈規則（完整版的 R-9.36）必須走 registry lazy-load，**禁止**把具身評估流程細節 eager-load 回 CLAUDE.md（守 FF-2 漸進揭露遷移健康度、守 Phase H ACT-051 設計意圖）。
- **`docs/` 作為地圖與單一真實來源**：具身 verdict 落 `build/reports/eval/EVAL-{stage}-{date}.yaml`、鷹架代謝提案落 `build/reports/gc/SCAFFOLD-ROI-{date}.md`——皆 Markdown/YAML 純文字、AI 可直接推理（智慧體可讀性），主線脈絡只持「指標 + 連結」，不持全文。
- **不變量 linter 即 `arch_fitness`**：本輪 FF-16 即新增一條「防護邊界」，把「具身評估器工具鏈接地完整」這條先前無人守的不變量，變成 nightly-strict 會擋的靜態守門。

### 2.2 記憶體 / 上下文衰減防護 —— 「查詢而非灌入」

| 衰減風險（接地新引入） | 防護設計 | 既有接地點 |
|---|---|---|
| 沙箱日誌 `logs.ndjson` 無界增長，全量灌入炸 token | **logql 選擇器查詢**：`{level="error"} \|= "<symptom>"`，只回匹配行，不 dump | `observability_query.logql_lite()` |
| 元迴圈具身評估在主線跑，污染脈絡 | 具身評估在**隔離 context / git worktree**（`sdd-evaluator` 既有 boundary），主線只收 verdict + 一行根因 | `sdd-evaluator` workflow step_6 |
| 多輪自我演化累積 Decision Trace 膨脹 | 沿用 active 50 + flushed FIFO（M2） | `state_loader` Decision Trace |
| token ≥ 95% | 強制停機產 Context Snapshot（Rule 9.2，接地不豁免） | `context_ledger_pre` |

### 2.3 不變量防護欄（Invariants Guardrails）—— 接地的紅線

接地**絕不可**破壞既有反 Goodhart 對抗分離地基（這是 Phase O~W 全部保證的命根）：

1. **具身 oracle 仍對 generator 不可見**：`EMBODIED_GROUNDING_GATE` 的沙箱基準專案 + verdict 準則，`operator_*_genesis` 結構性不可 import / 不可讀（ast/import 隔離斷言，承 Rule 9.32.2~9.35.2 對抗分離）。
2. **具身接地是「必要充分雙簽」不是「替換」**：合成 oracle 仍在（防 generator 在具身基準上過擬合），具身閘是**外加**的接地證據，不取代合成勝率。
3. **GC 不自動退役**：`sdd-gc` 只出 advisory 提案，退役必經 `set_maturity(reviewed_by=)` 人工 gate（Rule 9.20.5 / Rule 8）；守「自動退役 active 規則而不經人工」= 違反即停機（CLAUDE.md 禁令 #11）。
4. **OPEN-10.6 不放寬**：具身沙箱維持本地、no-HTTP、ndjson file-based；活體 canary/shadow 仍列 horizon。

---

## 3. 終極優化藍圖（Level 10 自治 · 具身接地的最後一塊）

> 提示 Output Requirement 4：升級到 Level 5（按 §3.3 對賬讀作「L10 完整之具身接地切片」），含系統垃圾回收機制與人類協作介面。

### 3.1 三支柱藍圖

**支柱 A — 元迴圈具身接地（GAP-X1 解）**
- `EMBODIED_GROUNDING_GATE`：自我發明能力 → 套真實沙箱基準專案 → `sdd-evaluator` 實跑 → `observability_query` 查客觀錯誤 → grounded-verdict 雙簽。
- 完整版需 META_FSM 新不變量 `EmbodiedGroundingBounded`（具身接地閘有界、verdict 必基於 ExecutionObservation 客觀資料、沙箱硬 timeout 保有界停機）。

**支柱 B — 系統垃圾回收機制（GAP-X2 解，提示明列「系統垃圾回收機制」）**
- `sdd-gc` 首次行使：對全 35 條治理規則 + meta⁵~meta⁸ 鷹架算 `scaffold_roi`，對長期 fire=0 者產 **advisory 退役 ROI 提案**。
- **誠實設計（防全 0 誤報，沿用 FF-9 data-gate）**：aggregate fire < 門檻時 gate 關閉、不誤報；隨 runtime 累積自動啟動。本輪先以 FF-16 把「GC 從未行使」這個盲區量測出來、鎖住代謝肌肉的接線完整。
- **代謝對象的誠實清單**：meta⁵~meta⁸ 是 fire=0 鷹架的最大候選；但**退役須人類舵手裁定**（它們防的是真實的、雖未發生的自我發明危害類別）——GC 只**提供 ROI 證據**，不替人類決定。

**支柱 C — 人類協作介面（提示明列「人類協作介面」+「設計環境掌舵者高度」）**
- `steersman_renderer` 升級：渲染「自我發明能力的**具身接地 diff**」——不只渲染合成勝率，還渲染「在真實沙箱基準上 OQS 變化 / 新增 runtime 錯誤 / logql 根因」，讓人類一眼看懂「這個自我發明的東西在實跑環境裡到底有沒有用」。
- **K=1 不變**：每週期至多 1 個元迴圈自我發明進 proposed-signoff；每個必經人工 signoff。人類審的是「具身接地證據」而非「合成勝率」——這是把舵手從「審合成算子代數」抬到「審具身真實效用」的最高形態。

### 3.2 成熟度量表對賬（§3.3）—— 為何此刻最高 ROI 不是 meta⁹

| Level | 定義 | 框架實況 |
|---|---|---|
| L0~L4 | 人工主導 → 規則自動化 → 精準停機 | Phase A~D 達成 |
| **L5** | 學習層入口（提示 Output Req 4 的「Level 5 自治」） | **Phase E 達成（2026-04）** |
| L6~L9 | 自癒 / 跨專案 / 意圖規劃 / 離線反事實 | Phase G~L 達成 |
| **L10** | 完整自治元迴圈（組合/最優/元最佳化/自我發明本體論） | Phase M~W 達成（meta¹~meta⁸） |
| **L10 完整剩餘** | **具身接地的元迴圈**（自我演化判定引用具身觀測 + 學會代謝自己） | ⬅️ **Phase X 補這塊** |
| L10+ / horizon | meta⁹ 真圖靈完備 / 活體 canary / meta-oracle 自演化 | **誠實 horizon，見 §3.4** |

**為何不是 meta⁹**：算子代數自我發明軸的邊際效用已遞減（每層 held-out 只 12 條合成語料、fire=0、離真實交付愈遠），且 meta⁹ 跨入停機不可判定（R-9.35.5 紅線）。**最高 ROI 是把已建好卻晾置的具身評估器接地進元迴圈 + 行使從未動過的代謝肌肉**——這比「在玩具算子代數上再自證一層」對「真實 L10 自治」的貢獻大一個量級。

### 3.3 §3.3 即上表 L 量表對賬（提示 Level 5↔Level 10 不一致已釐清）。

### 3.4 誠實 Horizon 章節（meta⁹ / 活體 / meta-oracle 自演化）

> 兩者並陳：以下三項**明確不在 Phase X 做**，誠實標為 horizon，並說明為何此刻接地優先於它們。

- **H-1：meta⁹ 真·圖靈完備算子代數（無靜態 device 可保證停機）**。讓算子帶無界記憶 / 真自由互遞迴 ⇒ 停機不可判定 ⇒ **沒有任何靜態 device（有界步數 / 良基測度）能保證停機**（R-9.35.5）。採納它**必須**誠實放棄「靜態可證停機」，改用「執行期 fuel 硬截斷 + 人類舵手」——這是**能力與保證的質變權衡**，超出「不放寬沙箱、純離線/形式化」策略，列最高理論 horizon。**Phase X 的具身接地是它的前置**：唯有元迴圈先接地到具身評估，未來若真要走 meta⁹，才有「具身 fuel 截斷 + 客觀 runtime 觀測」當執行期後盾，而非裸奔。
- **H-2：活體 canary / shadow（放寬 OPEN-10.6）**。具身接地完成後的自然下一步是把沙箱從本地推到真實 canary，但需放寬 no-HTTP 資安決策，列 horizon（OPEN-X.x 承 OPEN-10.6）。
- **H-3：meta-oracle 自演化（自我發明評估器）**。讓系統自我演化它的必要性 oracle 本身——這**自指地破壞 Phase O~W 全部反 Goodhart 保證所賴以成立的對抗分離地基**，採納須先有「對抗分離不可繞過性」形式化證明。**Phase X 的具身接地恰是它的對立解**：與其讓 oracle 自演化（風險），不如把 oracle 接地到**人類無法竄改的客觀具身觀測**（沙箱 verdict）——具身觀測是比「自演化 oracle」更可信的對抗分離來源。

---

## 4. 本輪可驗證切片：FF-16 規格（執行錨點）

> 走 `SDD_SELF_EVOLUTION` 的 FSE 通道（R16）。**唯讀、確定性、無網路、無副作用**（沿用全部 15 個既有 FF 的契約）。新增於 `tools/arch_fitness/arch_fitness.py`，回歸守門於 `tests/test_arch_fitness.py`。

**FF-16 — 具身評估器 & 鷹架代謝工具鏈接地完整性（Embodied-Evaluator & Scaffold-Metabolism Toolchain Grounding Integrity）**

兩道檢查，與 FF-7/10/14/15 引用完整性家族同源：

- **(A) structural fail — 具身/代謝能力的引用接地完整**：系統級 `sdd-evaluator` / `sdd-gc` agent 宣告依賴的 runtime 模組（`sandbox_runner` / `output_quality_scorer` / `observability_query` / `scaffold_gc`）必須在磁碟存在，且其綁定的 FSM 狀態（`EXECUTION_EVALUATION` / `SCAFFOLD_GC`）必須存在於 `transition_rules` canonical 狀態宇宙。任一 dangling = 具身評估器/GC 是 governance-theater（宣稱能力、無 backing code）。**因四模組 + 兩狀態現皆存在 → 綠燈鎖（structural pass），ENFORCING 未來 bit-rot / 誤刪被 nightly-strict 擋下。**
- **(B) advisory — 具身接地 / 代謝行使漂移（surface GAP-X1/X2）**：偵測 (i) 元迴圈生成器模組（`operator_*_genesis` / `dimension_necessity_oracle`）是否**零引用**具身評估器工具鏈（GAP-X1：元迴圈未接地）；(ii) `scaffold_gc` 是否從未產出退役提案（`build/reports/gc/` 無 SCAFFOLD-ROI 提案 / aggregate fire==0，GAP-X2：代謝肌肉從未收縮）。advisory（已知漸進缺口，鏡像 FF-2/FF-9/FF-13 哲學）——把病灶轉為被追蹤的 backlog，**不自動阻擋**（守 Rule 8 人類舵手）。

**驗收（客觀、可機器判定）**：
| 守門 | 通過條件 |
|------|----------|
| `arch_fitness --only FF-16` | structural pass（4 模組 + 2 狀態皆解析）；advisory 誠實 surface GAP-X1/X2（或 0，若未來接地完成） |
| 回歸測試 | `tools/fsm_runtime/tests/test_arch_fitness.py` +7 測試全綠（模組缺失 fail / 狀態缺失 fail / agent 缺失 fail 三合成案例 / repo structural 綠燈鎖 / meta-loop ungrounded↔grounded 雙向 / GC fired 案例） |
| 不回歸 | `python -m pytest -m "not chaos"` 1401→**1408** passed / 4 skip 不變 / 0 回歸；15 FF→16 FF structural fail=0（FF-16 advisory 不計入 structural；全量 score 1→3，含既有 FF-5 + FF-16 兩條刻意 surface 的 GAP advisory） |
| QA 抓漏 | 獨立專家 agent 0 BLOCKER；所有文件 + 技術問題全修 |

---

## 5. Self-Verification 完整模擬（Spec 寫錯 → 測試永不過 → 優雅停機導人類）

> 提示 Self-Verification Protocol。確認接地後流程能優雅中斷、引導人類修 Spec / 補工具，而非無限重試燒 token，**且接地強化而非削弱這條保證**。

**案例**：某 feature 的 AC 寫成「回應時間必須 < 0ms」（物理不可行）/ 或互相矛盾的兩條 AC。

| 步驟 | 接地後的流程 | 停機保證 |
|------|--------------|----------|
| 1 | `SPEC_DRAFTING` 後，`spec-logical-validator`（SLV-001 物理不可行 / SLV-003 矛盾 AC）**在 SCG-0/3 前**攔下 | 多數情況**根本進不了實作**（Rule 9.3） |
| 2 | 若漏網進 `IMPLEMENTATION → EXECUTION_EVALUATION`：`sdd-evaluator` 沙箱實跑，`observability_query` 查日誌 → 持續 runtime_fail，但根因被客觀定位 | 具身證據，非主觀猜測 |
| 3 | Evaluator verdict = `spec_defect`（實作對、契約本身矛盾）→ `EXECUTION_EVALUATION → SPEC_AUDIT`（**不**回 IMPLEMENTATION 盲目重試） | 接地讓「無界重試」更早轉「客觀 spec_defect」 |
| 4 | 若仍卡在重試：SCG retry budget 3 / PR 5 / RTM 2 觸頂 → **ESCALATION** | Rule 9.1 有界停機 |
| 5 | ESCALATION 產 Abort Report，**導人類舵手**：「測試契約矛盾，請修 Spec 或補缺失工具/環境限制」——**絕不自動恢復**（Rule 9.5），**絕不註解掉測試假綠**（Rule 4） | 人類維持設計環境掌舵者高度 |
| 6 | token ≥ 95% 任一時點 → 強制 Context Snapshot 停機 | Rule 9.2 |

**結論**：接地**強化**了這條停機保證——`observability_query` 讓 Evaluator 能在日誌裡指出「為何永遠失敗」，把「無界重試燒 token」更早、更客觀地轉成「`spec_defect` 證據 → 人類修 Spec」。Self-Verification PASS。

---

## 6. 執行檢核清單（本輪可驗證切片）

- [x] §0~§5 藍圖凍結（已撰，使用者 2026-06-05 拍板 signoff）
- [x] FF-16 實作於 `tools/arch_fitness/arch_fitness.py`（structural (A) + advisory (B)）
- [x] FF-16 接入 `main()` dispatch + `--only FF-16` + docstring（15→16 FF）+ 退出碼說明
- [x] +7 回歸測試於 `tools/fsm_runtime/tests/test_arch_fitness.py`（3 合成 fail + repo 綠燈鎖 + ungrounded↔grounded 雙向 + GC fired）
- [x] `arch_fitness --only FF-16` → structural pass（ff16-ok）+ advisory 誠實 surface GAP-X1/X2（warn=2）
- [x] `python -m pytest -m "not chaos"` → 1401→**1408** passed / 4 skip 不變 / 0 回歸
- [x] `arch_fitness`（全量）→ 16 FF structural fail=0（全量 score=3：FF-5 既有 + FF-16×2 GAP advisory）
- [x] QA 專家 agent 抓漏（文件 + 技術）→ 0 BLOCKER / 0 MAJOR(技術)；2 MAJOR + 數 MINOR 皆文件事實，已修
- [x] FIX 修復全部 issue（文件事實 + 測試隔離強化）→ 獨立稽核 agent 複驗
- [ ] 成熟度評估 + 文件歸檔 + diff 摘要 → 🔴 **待使用者確認才 tag/push/merge**（使用者 2026-06-05 拍板「push 前讓我看」）

---

## 7. 與既有框架的整合點

| 既有元件 | 整合方式 |
|---------|---------|
| `arch_fitness`（15 FF） | FF-16 純加法接入，沿用 Finding/FitnessReport + `--only` + 退出碼語意 |
| `sdd-evaluator` / `sandbox_runner` / `observability_query` / OQS | FF-16 (A) 驗其接地完整；完整版 `EMBODIED_GROUNDING_GATE` 直接消費 |
| `sdd-gc` / `scaffold_gc` / `scaffold_roi` / FF-9 | FF-16 (B) 與 FF-9 互補：FF-9 守 scaffold_roi schema 完整，FF-16 守「代謝肌肉是否曾收縮」 |
| `SDD_SELF_EVOLUTION`（FSE） | FF-16 = 路線圖 R16，沿用 R1~R15 落地形態；不消耗 ACT/R-9.x |
| `META_FSM`（完整版） | 下一輪補 `EmbodiedGroundingBounded` 不變量（不增軌，承 Phase P~W 示範） |
| nightly CI `arch-fitness.yml` | FF-16 自動流入 PR-advisory + nightly-strict |

---

**藍圖狀態**：✅ 已撰，待人工 signoff → 執行 §6 可驗證切片。
