# SDD_improving_Automation_19 — Phase S 藍圖（DRAFT）

**主題**：生成文法**詞彙的自我擴充（meta⁴）** + **多維度批次退役聯動**——把 Phase R 只能「在**固定特徵詞彙 VOCAB**（8 條硬編原始特徵）上組合生成新維度、退役聯動只能退 1 換 1」的能力，推進到「系統能**自我發明一個 VOCAB 裡根本沒有的全新原始特徵詞彙**（詞彙生成文法 meta⁴，VOCAB 外無界生成需另證有界）」與「**一次退 m 換 n 的批次本體論重構**（批次退役聯動）」，並正面納管「詞彙外生成」與「批次旋轉」憑空長出的、Phase R（固定 VOCAB / 退 1 換 1）不存在而 Phase S 才出現的**新危害類別：詞彙無界生成爆炸（VOCAB 外不再有 8 條硬編上界）、詞彙自我發明 Goodhart（發明一個「量自己核可」的自指原始特徵）、批次旋轉重寫本體論（per-swap SwapCadence 與單調棘輪皆對「一次 m 換 n 的批次操作頻率與批次內互抵」盲目的更高階震盪）**。
**目標等級**：L10 完整 · 離線活體 meta-meta-meta 迴圈「維度語意自我發明 + 退役聯動（固定 VOCAB）」切片（Phase R 已達：在固定 VOCAB 上組合發明維度 + 退 1 換 1）→ **L10 完整 · 離線活體 meta⁴ 迴圈「生成文法詞彙自我擴充 + 多維度批次退役聯動」切片**（系統不只能在**有限 VOCAB**上組合發明維度，更能在**可證有界、反自利、人類掌舵本體論**的前提下，**自我發明 VOCAB 外的全新原始特徵詞彙**，並在**基數封頂時有界地以批次退役換新維度**重構它的價值本體論）。
**建立日期**：2026-06-04
**前置基線**：Phase R 完整（ACT-129~134 / R-9.30，pytest 1168 passed / 4 skipped / 14 subtests；五軌 TLC 全 No error：`SDD_FSM` 42 reachable、`META_FSM` 13 distinct、`FLEET_FSM` 7、`COMPOSITION_FSM` 21、`OPTIMIZATION_FSM` 12；chaos 100 輪 bounded_ratio=1.0 含 `DIMENSION_INVENTION_GOODHART_FLAP`+`DIMENSION_SWAP_THRASH_FLAP`，自我發明 Goodhart 零漏放、定基數旋轉有界停機）
**OPEN-10.6 承接**：續承 OPEN-R.x / OPEN-Q.x / OPEN-O.7 / OPEN-M.7 / OPEN-P.7——**暫不放寬 OPEN-10.6 沙箱**（維持本地唯讀／no-HTTP）。故 L9 完整（活體 canary/shadow）與**活體 meta⁴ 元迴圈**續列 horizon；**Phase S 與 Phase N/O/P/Q/R 同策略——全力推「不需放寬沙箱、純離線/形式化」即可達成的 L10 完整剩餘切片（詞彙自我擴充 + 批次退役聯動）**。Phase R §3.4 明示「生成文法詞彙的自我擴充（meta⁴）」「多維度同時聯動退役（批次本體論重構）」為其自陳 horizon，故本份維持離線等價切片，活體版列 horizon（OPEN-S.x 承前）。
**狀態**：✅ **EXECUTED 2026-06-04（L10 完整 · 離線活體 meta⁴ 迴圈「生成文法詞彙自我擴充 + 多維度批次退役聯動」切片達成）** — ACT-135~140 全部完成。**驗收：pytest 1168→1240 passed / 4 skipped / 14 subtests（+72，零回歸）；五軌 TLC 全 No error（`META_FSM` 維持 13 distinct 不回歸、新增 `VocabGenesisBounded` + `BatchSwapCadenceBounded` INVARIANT PASS；SDD 831 distinct / FLEET 7 / COMPOSITION 21 / OPTIMIZATION 12 不回歸）；chaos 100 輪 bounded_ratio=1.0（新增 `VOCAB_GENESIS_GOODHART_FLAP` 自指字+詞彙外噪音字零漏放 + `BATCH_SWAP_THRASH_FLAP` → `BatchSwapCadenceExceeded` → MFSM_ESCALATION 有界）；不增第六形式化軌（vocab-genesis/batch-swap 重用既有 META_FSM）；單軌 SDD_FSM 零 vocab-genesis/batch-swap 洩漏；12 凍結 VOC feature-genesis 語料零漏放（真必要偵出 6/6、詞彙自我發明 Goodhart 噪音+冗餘攔截 6/6）。** `ID_REGISTRY` 已翻牌 act 135→141 / rule 9.31→9.32。OPEN-S.x 承 OPEN-R.x/Q.x/O.7/M.7/P.7 暫不放寬 OPEN-10.6 沙箱。原 DRAFT 紀錄保留如下。徵用 ACT-135~140 / Rule 9.31（取自 [`governance/ID_REGISTRY.yaml`](../../../governance/ID_REGISTRY.yaml)，單調取號）。
**對應提示**：Karpathy 式「首席 AI 自動化架構師」前沿評估（驗證圖靈完備自動化閉環 → 進化 Level 10 自治）— 承 Phase R §3.4 自陳 horizon「生成文法詞彙的自我擴充（meta⁴，VOCAB 外、涉及更深的無界生成需另證有界 + 反自利）」與「多維度同時聯動退役（批次本體論重構，須證不形成更高階震盪繞過 SwapCadence + 棘輪）」續推。

> 🔴 **編號徵用告示**（承 `ID_REGISTRY.yaml` `next_free` = act 135 / rule 9.31）：
> 本藍圖徵用 **ACT-135~140 與 Rule 9.31**（取自登記簿前緣，單調取號）。
> 停滯分支 M3 Hook Health 不持有任何號，復活時另取當下 `next_free`。
> **DRAFT 期間不得翻牌**——僅在獲人工 signoff 並執行至收官（ACT-139）時，才由 `id_registry` 翻牌（act 135→141 / rule 9.31→9.32）+ `test_id_registry.py` 守門固化；撞號由 CI 自動攔截。

---

## 0. 為什麼還需要 Phase S？——對既有設計的誠實剖析（含 `<thinking>` + 圖靈完備性覆查）

<thinking>
這份提示要求「驗證圖靈完備的自動化閉環、進化 Level 10 自治」，附三個必查漏洞視角（狀態轉換 / 上下文衰減 / 停機問題）與一份 self-verification 案例（Spec 寫錯→測試永不過）。延續 Phase K~R 的紀律，第一步是**對賬而非設計**：這套系統已走過 Phase A~R、是自陳「L10 完整 + 離線活體 meta-meta-meta 迴圈（維度語意自我發明 + 退役聯動）」的成熟框架。盲目重述提示前沿清單只會重造輪子（Phase K~R 已逐項對賬為 100% 落地）。我的任務是：(1) 覆查圖靈完備 vs 保證停機的核心命題在 Phase S 是否仍成立；(2) 誠實判斷「詞彙自我擴充 + 批次退役」到底是**Phase R 的換皮**（無新意、不值得一個 Phase），還是**有真正的新結構性缺口**；(3) 用三漏洞視角把那個新缺口挖到 grep 可證零實作。

【零、圖靈完備 vs 停機的命題覆查——Phase S 把監督者的涵蓋面從「固定 VOCAB 上組合發明維度 + 退 1 換 1」擴到「VOCAB 外自我發明原始特徵詞彙 + 批次退役聯動」】
Phase O/P/Q/R 已正面論證：圖靈完備性來自「嵌在迴圈裡的 LLM 生成器 + 無界 `docs/` 紙帶」，保證停機來自「把不可判定的 LLM 包進可判定的有限狀態監督者（FSM + retry/context budget + 五軌 TLC）」——兩者拆在不同基質故不矛盾。Phase R 的貢獻是把「維度語意的自我發明（候選池外有界生成文法 + feature-keyed 必要性 + 自指 probe 守門）+ 退役聯動（SwapCadenceBounded 單調棘輪）」拉進基質 B。

但 Phase R 誠實標定了它的生成文法**鎖在一個固定的 8 條原始特徵詞彙 `VOCAB`**（`dimension_semantics_synthesizer.VOCAB` 8 條硬編 `rollback_steps`/`blast_radius`/…），synthesizer 只能在「這 8 個詞」之上**組合**（子集 × OPS）發明維度——它**換不出選單上沒有的新『字』**。Phase R 把兩件事列為 horizon（§3.4 行 257~258）：**(i) 生成文法詞彙的自我擴充（meta⁴，VOCAB 外、發明新原始特徵，涉及更深的無界生成需另證有界 + 反自利）**；**(ii) 多維度同時聯動退役（批次本體論重構，退 m 換 n，須證不形成更高階震盪繞過 SwapCadence + 棘輪）**。這裡藏著一個**被 Phase R 一句帶過、實際上是質變而非量變的命題**：Phase R 的有界性**完全建立在「VOCAB 是固定 8 條」這一前提**之上——「候選池外」≠「無界」的形式化兌現，靠的正是「VOCAB（有限）× arity（有限）× OPS（有限）= 可枚舉」。「讓系統**自我發明一個 VOCAB 裡根本沒有的新原始特徵字**」**直接拆掉這個前提的地基**：VOCAB 不再固定，憑空長出一組**Phase R（固定 VOCAB）時根本不存在、詞彙生成才出現的新基質**：
- 不再是「在固定 8 個字上組合」（Phase R），而是「**從無限可能的原始特徵詞彙空間裡發明新字**」——而詞彙生成是**比維度組合更深一層的無界爆炸與自利溫床**：Phase R 的 VOCAB 有 8 條硬編上界，詞彙生成**沒有任何先天上界**；任何「想自利」的詞彙提案，只要發明一個「量起來剛好是自己核可訊號」的自指**原始特徵**（不是組合出來的維度，而是更底層的『字』），就能在 Phase R 的 self-reference guard（只查維度 probe 的 token）之下夾帶——因為 Phase R 的 VOCAB 是白名單（生產 VOCAB 無自指 token，guard 只防受擾注入的維度），而**詞彙自我擴充等於讓系統往白名單裡塞新字**，白名單本身被攻破。
- Phase R 的 `SwapCadenceBounded`（per-swap 聚合速率）+ 單調價值棘輪（per-swap 入軸 tier 嚴格 > 出軸）只管**單次 retire-1-swap-1**——它對「**一次退 m 換 n 的批次操作**」**結構性盲目**：一個批次 `{A,B}→{C,D}` 在 per-swap 視角下要嘛被拆成 2 個獨立 swap（但批次語意是原子的、批次內可互抵——C 比 A 必要、但 D 比 B 不必要，per-swap 棘輪逐條看會放過「批次內高低抵消」），要嘛批次大小本身無界（一次退 8 換 8 = 單次操作劫持整個本體論，per-swap 速率窗只看到「n 筆 add」卻看不到「這是 1 個原子批次」）。`SwapCadenceBounded`（per-swap-ADD 計數）與單調棘輪（per-swap tier 比較）**兩者皆看不見這條「批次旋轉」的新更高階迴圈**。
這正是 Phase S 必須納管的、Phase R 尚未碰的新東西。

【一、誠實判斷：詞彙自我擴充 + 批次退役是「Phase R 換皮」還是「有真缺口」？——用 grep 接地】
我先確認框架目前的詞彙**鎖死在固定 8 條**（grep `^VOCAB` / `VOCAB:` on `dimension_semantics_synthesizer.py`，實測 8 條硬編 tuple，無任何「詞彙生成 / 原始特徵發明 / 詞彙文法」路徑），且退役聯動**只能退 1 換 1**（grep `swap_dimension`，實測單一 out_dimension/in_dimension 簽章，無任何「批次 m 換 n」路徑）。再 grep 三組關鍵字證明零實作：
| 關鍵字 | grep 範圍 | 命中 |
|--------|-----------|------|
| `vocab.*genesis\|genesis.*feature\|GenesisFeature\|invent.*feature\|VocabGenesis\|expand.*vocab` | `tools/` | **零** |
| `batch.*swap\|BatchSwap\|multi.*retire\|m.*for.*n\|batch.*recompos` | `tools/` | **零** |
| `source.*transform\|raw.*signal.*source\|vocab.*budget\|SDD_DIM_VOCAB` | `tools/` | **零** |

→ **詞彙的「自我擴充」與「批次退役聯動」目前零實作；synthesizer 被鎖在固定 8 條 VOCAB 內、退役聯動只能退 1 換 1。** 真正的價值不在於「再加一個 genesis grammar」（那是 Phase R 換皮），而在於：**詞彙外生成 + 批次退役會打開三個 Phase R 結構性攔不住的新攻擊面**：
- **詞彙無界生成爆炸 + 詞彙自我發明 Goodhart（meta⁴）**：詞彙生成**沒有 8 條硬編上界**，理論上可生成無限多個原始特徵字；且系統可發明一個「**原始特徵字本身就引用 proposer/oracle/自評內部信號**」的自指**字**（不是組合維度，是更底層的詞），讓自我發明的詞彙「看起來必要」實際只是自利。Phase R 的 feature-keyed oracle 評的是**現場發明維度在 VOCAB 已知特徵向量上的增量覆蓋**——它預設語料的特徵向量**已含 VOCAB 全部 8 條**；對「一個**詞彙外、語料事先沒有這個特徵欄位**的新原始特徵字到底必不必要、是不是自指自利」**完全盲目**（語料根本沒這欄 → `apply()` 取 0.0 → 永遠零增量 → 詞彙自我擴充根本無法被合法驗證）。← 這是 Phase S 的 **PS-1**（真缺口，非換皮）。
- **批次旋轉重寫本體論（meta⁴ 停機危害）**：系統達基數天花板後，能「一次退 m 換 n」就能**單次操作劫持整個本體論**（批次大小無界 = big-bang 本體論重寫）或**批次旋轉**（`{A,B}→{C,D}→{A,B}`，per-swap 棘輪因「批次內高低抵消」逐條放過、per-swap 速率窗因「一個原子批次≠n 次操作」計數失真）。這是 per-swap SwapCadence + 單調棘輪皆盲目的 **meta⁴ 停機危害**。← **PS-2**。
- **詞彙外 + 批次退役的本體論掌舵真空**：`steersman` 只渲染「固定 VOCAB 上組合發明的維度」與「退 1 換 1」；無人渲染「系統**現場發明了一個選單外的新原始特徵字、它的詞彙生成文法來源（憑什麼有界）、它憑什麼必要且非自指**」，也無人渲染「**一次退 m 換 n 的批次重構、批次大小、批次聚合價值單調性**」。人類掌舵在「詞彙外本體論發明層（meta⁴）」與「批次重構層」缺席。← **PS-3**。

【二、用提示三個指定漏洞視角，逐一往 Phase R 之上挖】

(A) 狀態轉換——「生成器↔評估器合約談判」在 meta⁴ 層缺「詞彙外發明的可有界、可反自利、feature-grounded 驗證」這一層。
Phase R 的 `dimension_semantics_synthesizer`（生成，固定 VOCAB 組合）↔ `dimension_necessity_oracle.evaluate_invented_dimension`（評估，feature-keyed）是一對 meta-meta-meta GAN，但**它只評在固定 VOCAB 上組合、語料事先含全部特徵欄的維度**。當系統**現場發明一個選單外的新原始特徵字**，**(1) 誰保證這條詞彙生成不會無界爆炸？(2) 誰判「這個現場發明的字到底必不必要、是不是自指自利」？** 目前無人。提示要的「生成-評估分離 + 主觀標準量化」推到 meta⁴ 層，型態是：**(1)** 生成必須被一條**有界詞彙生成文法**封住——「VOCAB 外」不等於「無界」，而是「在一個**有限原始信號源 SOURCES × 有限轉換算子 TRANSFORMS**的可枚舉生成空間裡生成新詞」，節點 <= `SDD_DIM_VOCAB_BUDGET`（這正是「更深的無界生成需另證有界」的正面兌現：把看似無限的詞彙空間歸約為有限可枚舉文法）；**(2)** 評估必須升級為**feature-grounded（不靠特徵名、靠原始信號源的真實情節）的詞彙必要性 oracle**——對一個**現場發明、語料事先沒有這個欄位名字**的原始特徵字，oracle 在**含該原始信號源的凍結 feature-genesis 語料**上量「以這個新詞建一條探針維度，是否帶來既有 VOCAB 全部維度都拿不到的增量覆蓋 ∧ 非冗餘」；外加一道**詞彙級自指守門**（反自利：原始特徵字的 source/transform 引用保留自指信號 → 結構性拒絕，零漏放）。→ **PS-1**（最關鍵；純離線、不受 OPEN-10.6 約束）。

(B) 停機問題——「多維度批次退役」是一條 per-swap SwapCadence 與單調棘輪皆盲目的新更高階迴圈。
這是 Phase S 最深、也最反直覺的停機缺口。Phase R 的 `SwapCadenceBounded` 對**單次 retire-1-swap-1 的聚合速率（per-swap-ADD 計數）**設界；單調價值棘輪對**單次 swap 的入/出軸 tier** 設嚴格大於。但批次退役出現兩種**全新病態**：**(i) 批次大小無界**——一次退 m 換 n（m,n 任意大）= **單次原子操作劫持整個本體論**（per-swap 速率窗看到「n 筆 add」卻不知這是 1 個原子批次，棘輪逐條比卻不知批次語意），破 `NoBigBangValueRewrite` 的維度版；**(ii) 批次內高低互抵 + 批次旋轉**——批次 `{A,B}→{C,D}` 可以 C 遠比 A 必要、D 卻比 B 不必要，per-swap 棘輪逐條看會「整體放過」（因為平均看起來在進步，但其實混進了一條退步的 swap），且 `{A,B}→{C,D}→{A,B}` 的批次旋轉在「每個批次都帶不同的字」時 per-swap 速率窗也數不準。這是 Phase R（只能退 1 換 1）時不可能、批次退役才出現的停機危害。→ 需要一條**批次退役聚合有界停機不變量** `BatchSwapCadenceBounded`：(a) **批次大小有界**（|out|、|in| <= `SDD_DIM_BATCH_MAX`，反 big-bang 本體論重寫）；(b) **批次聚合單調價值棘輪**（批次入軸聚合 necessity 須嚴格 > 批次出軸聚合 + batch margin，且批次內**最低入軸 tier 仍須 > 最高出軸 tier**——杜絕「批次內高低互抵夾帶退步 swap」）；(c) **批次操作聚合速率**（最近視窗內的**批次操作數**<= `SDD_DIM_BATCH_RATE_MAX`）→ 觸頂即 `BatchSwapCadenceExceeded` → `MFSM_ESCALATION`；外加 net cardinality 非增（n <= m）。← **PS-2**。

(C) 動態演進 / 人類掌舵——「人類審的是『固定 VOCAB 上組合的維度發明』與『退 1 換 1』，缺『詞彙外發明 diff（meta⁴）』與『批次重構 diff』」。
Phase R 的 `render_semantic_invention_proposal` 渲染**固定 VOCAB 上組合**發明的維度；`render_dimension_swap_proposal` 渲染**退 1 換 1**。詞彙自我擴充後，若系統現場發明一個選單外的新原始特徵字，人類面對的是「一個從未見過的新原始信號 + 它的詞彙生成文法來源」——**沒有人渲染『這個字是系統怎麼從有限詞彙文法生成出來的、它有界嗎、它自指嗎、它憑什麼必要』，也沒有人渲染『一次退 m 換 n 的批次重構、批次大小、批次聚合價值單調性』這種批次本體論演化**。提示反覆強調「人類維持設計環境掌舵者高度」——在「詞彙外本體論發明（meta⁴）」層，掌舵的最高形態是**人類能一眼看懂『系統憑空發明了哪個新原始特徵字、它的有界詞彙生成來源與反自利證據』與『它如何在不爆基數下批次退舊換新』，且系統在結構上不可能自動 commit 任何詞彙自我發明/批次退役（每週期至多 K_vocab=1 個詞彙發明 / 批次大小 <= `SDD_DIM_BATCH_MAX`、每個/每次必經人工 signoff）**。→ **PS-3**（詞彙外本體論發明掌舵介面 + 批次重構掌舵 + `NoUnboundedVocabGenesis`，K_vocab=1，承 Phase R K_dim=1）。

【三、停機問題紅線覆查——本份比 Phase R 更危險，因為納管的是「會憑空發明自己詞彙、且能一次批次重寫本體論的迴圈」】
Phase R 的反諷（讓系統自我發明它的評判軸語意）在 Phase S 升級為「讓系統**憑空發明自己的原始特徵詞彙、並在基數封頂時一次批次退舊換新**」。有界性與防自利必須再加固：
- **仍不新增形式化軌（承 Phase O/P/Q/R「重用 META_FSM、不增軌」的成熟示範）**：詞彙自我發明的採納/退役、批次退役聯動的 swap 全部註冊為 `META_FSM` 既有的指紋命名空間（詞彙用新增 `vocab-genesis:` 命名空間、維度用既有 `value-dimension:`），其 add↔retire churn 由**同一條** `ChurnBounded`/`GraduationRatchet` 涵蓋，維度 stock 由 Phase Q 的 `DimensionCardinalityBounded` 涵蓋。**但 PS-1/PS-2 揭示：churn + 維度 stock + per-swap SwapCadence 仍不夠**，故必須**對既有 `META_FSM` 再補兩條不變量**：`VocabGenesisBounded`（詞彙基數 stock 天花板，meta⁴）+ `BatchSwapCadenceBounded`（批次退役聚合）——關鍵是**沿用 Phase P/Q/R 對 `CrossScorerChurnBounded`/`DimensionCardinalityBounded`/`SwapCadenceBounded` 的誠實作法：只新增 INVARIANT、不新增狀態變數**（`META_FSM` 維持 `<<mstate, churn, cap>>` 三變數 / 13 distinct，TLC 仍 No error，五軌不回歸；詞彙 stock 與批次聚合速率的緊語意由 runtime `guard_vocab_genesis`/`guard_batch_swap` + chaos `VOCAB_GENESIS_GOODHART_FLAP`/`BATCH_SWAP_THRASH_FLAP` enforce/驗收，形式化層誠實標註為「single-counter 抽象之歸約引用」）。這守住「圖靈完備能力 / 可證停機控制」的拆分紅線，又不退化成「每個新能力都開一軌」。
- **PS-1 的有界詞彙生成文法是硬約束，非建議**：詞彙自我發明的搜尋**必在有限詞彙文法（有限原始信號源 `SOURCES` × 有限轉換算子 `TRANSFORMS`）內可枚舉**，節點 <= `SDD_DIM_VOCAB_BUDGET`（clamp[8,128]，預設 32）——「VOCAB 外」≠「無界」，這是「更深的無界生成需另證有界」的形式化兌現。**PS-1 的反自利是雙閘**：(a) 詞彙自我發明的 necessity tier **唯一合法來源仍是 synthesizer/proposer 全體碰不到、content-hashed 凍結的 feature-grounded 詞彙必要性 held-out 勝率**（增量覆蓋 ∧ 非冗餘）；(b) **詞彙級自指守門**——任何 source/transform 引用保留自指信號（`self_score`/`proposer_*`/`necessity`/`oracle_*`…）的原始特徵字，在送 oracle 前即被 `vocab_self_reference_guard` 攔下（零漏放）。`vocabulary_genesis` **結構性不 import oracle、不讀必要性語料**（ast/import 隔離斷言，承 Phase R）。
- **PS-2 的批次退役是「批次大小界 + 批次聚合棘輪 + 批次操作速率窗」三鎖**：批次 |out|/|in| <= `SDD_DIM_BATCH_MAX`（反 big-bang）；批次入軸聚合 necessity 嚴格 > 批次出軸聚合 + batch margin **且** min(in_tiers) > max(out_tiers)（杜絕批次內高低互抵）；最近視窗批次操作數 <= `SDD_DIM_BATCH_RATE_MAX` → 觸頂 `BatchSwapCadenceExceeded` → `MFSM_ESCALATION`；net cardinality 非增（n <= m）。退役維度再採納仍須挾 necessity capability-delta（既有 `GraduationRatchet`）。
- **PROPOSED-only + 反 big-bang 詞彙發明/批次退役，人類掌舵推到「詞彙外本體論發明（meta⁴）」層**：每週期至多 **K_vocab=1** 個詞彙自我發明 / **1 次** 批次（且批次大小 <= `SDD_DIM_BATCH_MAX`）可進 proposed-pending-signoff（`NoUnboundedVocabGenesis`，承 Phase R K_dim=1），每個/每次必經人工 signoff（守 Rule 8 / 9.27.3 / 9.28.4 / 9.29.4 / 9.30.4）。`steersman_renderer` 渲染「詞彙外本體論發明 diff（系統憑空發明哪個原始特徵字 + 詞彙生成文法來源 + 反自指證據 + 必要性勝率）」與「批次重構 diff（退 {…} 換 {…}、批次大小、net 基數 delta、批次聚合單調性、批次速率狀態）」，讓人類**不讀程式碼就能掌舵整個系統詞彙外的價值本體論發明與批次演化**。

【四、上下文衰減（Context Degradation）視角覆查】
- 詞彙文法枚舉、feature-grounded 詞彙必要性 held-out 重放、批次退役帳本全在**隔離邏輯/落盤**進行，主線只在收到 proposed 詞彙發明/批次 swap 時讀「詞彙外發明 diff + 批次重構 diff + 必要性勝率摘要」。詞彙帳本**沿用** Phase R 的 `value-dimension-ledger.yaml`（增 `vocab_inventions` / `batch_swaps` 領域審計段）+ 共用 Phase L 的 `meta-loop-ledger.yaml`（churn/vocab-cardinality/batch-cadence 治理），**零新增常駐 eager prompt、不污染單軌 `SDD_FSM`**。
- feature-grounded 詞彙必要性 oracle 重用既有 `counterfactual_replay` 重放基座與 `SDD_REPLAY_MAX_CASES`（clamp[5,200]，預設 50）上限，**不新增無界語料**。
- 所有新產物（詞彙發明帳本 / 詞彙必要性勝率表 / 詞彙外發明 diff / 批次重構 diff 報告）皆 Markdown/YAML 純文字、無二進位、無外網（守 OPEN-10.6 + 智慧體可讀性）。
→ 守漸進式揭露，不引入新脈絡焦慮。

【五、把 OpenAI/Anthropic 哲學收斂成一句設計準則】
- OpenAI（環境防護 / 智慧體可讀性 / 單一真實來源）：把「系統如何從有限詞彙文法**憑空發明一個 VOCAB 外的新原始特徵字**」「它的詞彙生成來源、反自指證據、凍結必要性證據」「批次重構 diff」全部落地為 **Markdown/YAML 可推理產物**——**讓「系統如何發明它『用什麼字描述它在乎什麼』、以及它如何在不爆基數下批次重構本體論」成為 AI 與人類都可直接推理、可審計的單一真實來源**，而非藏在 8 條硬編 VOCAB 或「退 1 換 1」的天花板裡。以漸進式揭露重構知識（詞彙帳本落盤、按需 lazy 讀），守 `docs/` 作為地圖。
- Anthropic（生成-評估分離 / 評估器實體操作 / 動態演進 / 大膽移除冗餘鷹架）：把「生成-評估分離、避免對自身產出盲目自信」從「固定 VOCAB 組合發明維度」（R）推到**「VOCAB 外詞彙自我發明」**（meta⁴）——生成端用**有界詞彙生成文法**把無界詞彙空間歸約為有限可枚舉（證有界），評估端用 **feature-grounded 詞彙必要性 oracle + 詞彙自指守門**專攻「詞彙自我發明 Goodhart / 自指自利字」；評估器在**凍結 held-out 現實代理語料（feature 向量含原始信號源）上實際重放、量客觀增量覆蓋**（對應提示「賦予 Evaluator 實體操作能力」於離線等價層——以現實代理語料替代生產流量，待 OPEN-10.6 改判再升活體 Playwright 式接地）；把「動態演進框架」從「固定 VOCAB 有界發明」（R）推到「VOCAB 外有界詞彙發明 + 批次退役聯動」（S）；並再次以「不增第六軌、只補 META_FSM 兩條不變量」示範「大膽移除冗餘鷹架」。你敢讓系統憑空發明它的詞彙、敢讓它一次批次退舊換新，就得能形式化證明這條詞彙發明迴圈仍會停（詞彙生成有界 + 批次速率有界）、且新詞不會在自指守門裡給自己發明一個「量自己核可」的字、也不會在批次操作裡一次劫持或互抵旋轉重寫本體論。
</thinking>

本次提示所列前沿清單，**已 100% 對應到 Phase H~R 落地元件**（對賬見上 thinking 一節），六條已知迴圈（單軌 `SDD_FSM` / 艦隊 `FLEET_FSM` / 元迴圈 `META_FSM`〔含 O 的 obj-profile、P 的全評分器 calibration、Q 的 value-dimension、R 的 self-invention/swap〕/ 組合 `COMPOSITION_FSM` / 最優 `OPTIMIZATION_FSM`）皆已形式化停機，且**「圖靈完備自動化閉環」已正面驗證成立**。Phase S 的價值在用提示三漏洞視角挖出 Phase R 之上仍真實存在、grep 證零實作的 **3 個結構性缺口**——它們的共同主軸是：**Phase R 全程在「固定的 8 條硬編原始特徵詞彙 VOCAB」上組合發明維度、退役聯動只能退 1 換 1；讓系統自我發明一個 VOCAB 外的全新原始特徵字、並在基數封頂時一次批次退舊換新，會憑空長出 Phase R（固定 VOCAB / 退 1 換 1）時不存在的『詞彙外生成』新危害——詞彙無界生成爆炸（VOCAB 外不再有 8 條硬編上界，需另證有界詞彙文法）、詞彙自我發明 Goodhart（自指自利字），以及『批次旋轉重寫本體論』的 per-swap SwapCadence/單調棘輪皆盲目的停機危害。**

| # | 缺口（用提示三漏洞視角挖出） | grep 證據（`tools/`） |
|---|------------------------------|--------------------------|
| **PS-1** | **synthesizer 被鎖在固定 8 條 VOCAB 內，無「VOCAB 外詞彙自我發明」路徑；且 feature-grounded 詞彙必要性驗證缺席**——系統無法發明一個選單外的全新原始特徵字，即使硬發明也無法被 Phase R 的 feature-keyed oracle 驗證（語料無此特徵欄 → apply 取 0.0 → 永遠零增量），更無「更深的無界生成需另證有界」的詞彙生成文法與「自指自利字」的詞彙級反自利守門。提示「生成-評估分離 + 主觀標準量化」在 **meta⁴（詞彙外發明）** 層缺席。 | `vocab.*genesis\|GenesisFeature\|invent.*feature\|source.*transform` **零命中** |
| **PS-2** | **退役聯動只能退 1 換 1，無「批次退役」；且批次旋轉是 per-swap SwapCadence 與單調棘輪皆盲目的新更高階迴圈**——系統可一次退 m 換 n（批次大小無界 = 單次劫持本體論；批次內高低互抵夾帶退步 swap；批次旋轉 per-swap 速率窗計數失真），把本體論一次批次重寫，燒 token 永不收斂。Phase R（退 1 換 1）時不可能、批次退役才出現的 meta⁴ 停機危害。 | `batch.*swap\|BatchSwap\|multi.*retire\|batch.*recompos` **零命中** |
| **PS-3** | **缺『詞彙外發明 diff（meta⁴）』與『批次重構 diff』掌舵介面**——`steersman` 只渲染固定 VOCAB 上組合的維度發明與退 1 換 1；無人渲染「系統憑空發明哪個原始特徵字 + 詞彙生成文法來源 + 反自指證據」與「一次退 {…} 換 {…}、批次大小、net 基數 delta、批次聚合單調性」。人類掌舵在「詞彙外本體論發明層（meta⁴）」與「批次重構層」缺席。 | `render.*vocab\|render.*genesis\|render.*batch\|NoUnboundedVocabGenesis` **零命中** |

**三缺口的共同主軸**：Phase R 讓人類站上「審系統在固定 VOCAB 上組合發明維度 + 退 1 換 1」的高度，但**框架的價值詞彙其實只能從一張『8 個字的硬編選單』裡組合、退役只能一次動一條**。Phase S 把人類抬到最高層——審「系統如何從**有界詞彙生成文法**憑空發明一個**選單外的全新原始特徵字**（憑什麼有界、憑什麼非自指自利）」、以及「系統如何在**不爆基數**下**一次批次退舊換新**地重構本體論（憑什麼批次大小有界、憑什麼批次聚合單調、憑什麼不批次旋轉）」——這正是 L10 完整「離線活體元迴圈」的**生成文法詞彙自我擴充（meta⁴）+ 多維度批次退役聯動**切片，精準補上提示在「狀態轉換（詞彙外生成-評估聯合合約）」「停機問題（批次退役的聚合速率停機）」「動態演進（詞彙外發明本體論而非只在固定 VOCAB 組合）」三視角的最深層要求。

---

## 1. Agentic 閉環狀態機設計（Phase S 增量）

Phase S 對狀態機的改動延續 Phase O/P/Q/R 的克制：單軌 `SDD_FSM` **不新增任何狀態**（維持 42/42）；**仍不新增第六條形式化軌**——詞彙自我發明與批次退役聯動本質上**都是 `META_FSM` 已證明的那條「學↔退」元迴圈**，只是被學/退的製品從「固定 VOCAB 上組合的維度」泛化為「**VOCAB 外現場發明的原始特徵詞彙**」（meta⁴），且新增一種「批次退役聯動 swap」轉換。**重用既有 `META_FSM`** 並**僅補兩條不變量** `VocabGenesisBounded` + `BatchSwapCadenceBounded`（不增狀態變數），是 Anthropic「大膽移除不需要的鷹架」用在框架自身、且把 PS-1/PS-2 釘進形式化的正解。

### 1.1 新增元件總覽（無新 FSM 狀態、無新形式化軌、無新狀態變數）

| 元件 / 形式化層 | 命名空間 | 類型 | 入口 | 出口 | 阻塞? |
|------|------|------|------|------|-------|
| `vocabulary_genesis`（VOCAB 外詞彙自我發明骨架；有界詞彙生成文法 + 詞彙自指守門） | runtime（落 `value-dimension-ledger.yaml` `vocab_inventions` 段） | 生成器骨架（advisory） | 跨 session 收官 / `MEMORY_CONSOLIDATION` 旁路 | 產 `proposed` 詞彙發明（only 透過注入 evaluate 取必要性，無自評；詞彙自指守門結構性拒絕） | 否 |
| `dimension_necessity_oracle`（**新增 feature-grounded `evaluate_genesis_feature`**） | runtime（重用 `counterfactual_replay` 重放基座，凍結 feature-genesis 現實情節） | 評估器（硬閘） | 詞彙發明提案後 | 必要性 tier（feature-grounded 增量覆蓋 ∧ 非冗餘；capability-delta 唯一合法來源） | 否（但決定 adopt 准駁） |
| vocab-genesis 採納（stock 天花板） | **新增 `vocab-genesis:` 指紋命名空間**（meta-loop-ledger）+ **新增** `VocabGenesisBounded` 不變量 | 元迴圈（沿用 `MFSM_*`，無新狀態/無新變數） | `meta_halt_monitor.guard_vocab_genesis` + `record_rule_add` | `ChurnBounded` ∧ `GraduationRatchet` ∧ `VocabGenesisBounded`（vocab stock）准駁；觸頂 → `MFSM_ESCALATION` | — |
| 多維度批次退役 swap + 批次速率停機 | **既有 `META_FSM`**（沿用 `value-dimension:` 指紋命名空間 + **新增** `BatchSwapCadenceBounded` 不變量） | 元迴圈（沿用 `MFSM_*`，無新狀態/無新變數） | `meta_halt_monitor.guard_batch_swap` | 批次大小界 ∧ 批次聚合棘輪 ∧ 批次速率窗 准駁；批次速率觸頂 → `MFSM_ESCALATION` | — |
| `steersman_renderer.render_vocab_genesis_proposal` / `render_batch_recomposition_proposal`（詞彙外發明 diff + 批次重構 diff + 反 big-bang） | runtime（advisory） | 詞彙發明過必要性 oracle / 批次過棘輪後 | 詞彙外發明 diff + 批次重構 diff；標「待人工 signoff、本週期 ≤K_vocab=1 / 批次 ≤SDD_DIM_BATCH_MAX」 | 否 |

> **選位說明**：
> - `vocabulary_genesis` 把 Phase R 的 `dimension_semantics_synthesizer`（在**固定 8 條 VOCAB**上組合）**升維為詞彙外生成（meta⁴）**：它在一個 **bounded 詞彙生成文法**（有限原始信號源 `SOURCES` × 有限轉換算子 `TRANSFORMS`）上**可枚舉地**生成 `GenesisFeature`（原始特徵字，節點 <= `SDD_DIM_VOCAB_BUDGET`），再透過呼叫端**注入的 `evaluate` 回呼**（= feature-grounded 詞彙必要性 oracle）取每個發明字的必要性。`vocabulary_genesis` 因此**結構性無法用自己的尺規證明自己必要**（它根本沒有必要性語料），且**結構性拒絕詞彙自指**（反自利第一閘）。`expanded_vocab()` = 基礎 VOCAB ∪ 已採納詞彙發明字——synthesizer 之後可在這擴充後的詞彙上組合維度（meta⁴ 對 meta-meta-meta 的供料）。
> - `dimension_necessity_oracle` 的 Phase S 升級是其**靈魂**：新增 `evaluate_genesis_feature` ——**不靠特徵欄名匹配**，而是在**含該原始信號源的凍結 feature-genesis 語料**上，以發明字建一條探針維度量「既有 VOCAB 全部維度都拿不到的增量覆蓋 ∧ 非冗餘」。專攻 feature-keyed oracle（預設語料已含全部 VOCAB 欄）看不見的**詞彙外自我發明 Goodhart**。
> - 批次退役 swap 的 add↔retire 元迴圈**完全納入既有 `META_FSM`**；PS-2 的批次旋轉由**新增的批次聚合不變量** `BatchSwapCadenceBounded` 涵蓋（只補 INVARIANT、不動狀態宇宙、不動狀態變數），五軌 TLC 不回歸、不增第六軌、`META_FSM` 維持 13 distinct。

### 1.2 meta⁴ 詞彙自我發明 + 批次退役迴圈（重用 META_FSM 有界停機契約 + 有界詞彙生成文法 + 反自利雙閘）

```
（離線、跨 session）
vocabulary_genesis.genesis_round()
  在 bounded 詞彙生成文法（SOURCES × TRANSFORMS，可枚舉節點 <= SDD_DIM_VOCAB_BUDGET）生成候選 GenesisFeature gf
    vocab self-reference guard：source/transform 引用保留自指信號（self_score/proposer_*/necessity/oracle_*）→ 結構性丟棄（反自利第一閘，不送 oracle）
    對每個倖存 gf：必要性 = 注入的 evaluate(gf)（= feature-grounded oracle 增量覆蓋；genesis 看不到語料）
  取至多 K_vocab=1 個必要性最高的候選（NoUnboundedVocabGenesis）→ 詞彙自我發明字 gf*
  → dimension_necessity_oracle.evaluate_genesis_feature(gf*)：在「genesis 全體不可見、content-hashed 凍結」的含原始信號源 feature-genesis 情節上，
       以 gf* 建探針維度量 (a) 增量覆蓋（既有 VOCAB 全維度拿不到的）+ (b) 非冗餘度
     ├─ 增量覆蓋 ≥ margin ∧ 非冗餘度 < 門檻 → 取得「必要性 tier++」
     │     → 產 proposed 詞彙發明 + 必要性證據 → steersman 渲染詞彙外發明 diff → 人工 signoff
     │     └─ 人工接受 → guard_vocab_genesis（vocab stock 未滿）→ record_rule_add("vocab-genesis:hash(gf*)")（擴充 VOCAB）
     └─ 未達必要性（含「自指自利字」「詞彙外噪音字」）→ 拒絕提案 → 純記錄

（離線、跨 session，基數封頂時）批次退役聯動
  guard_batch_swap(out_dims[], in_dims[], out_tiers[], in_tiers[])（PS-2）
    ├─ 批次大小：|out|、|in| <= SDD_DIM_BATCH_MAX（反 big-bang 本體論一次重寫）
    │   ∧ net cardinality：|in| <= |out|（非增）
    │   ∧ 批次聚合棘輪：sum(in_tiers) > sum(out_tiers) + batch_margin ∧ min(in_tiers) > max(out_tiers)（杜絕批次內高低互抵）
    │   ∧ 最近視窗批次操作數 < SDD_DIM_BATCH_RATE_MAX
    │      → retire out[] + add in[]（標 source=dimension_batch_swap + batch_id）
    └─ 批次大小/聚合棘輪/批次速率任一觸頂 → BatchSwapSizeExceeded / BatchSwapValueRatchetViolation / BatchSwapCadenceExceeded → MFSM_ESCALATION（人工裁決）
```

- **核心有界性（重用既有證明 + 兩條新不變量）**：
  - 詞彙生成（PS-1）：詞彙自我發明在**有限詞彙文法**內可枚舉，節點 <= `SDD_DIM_VOCAB_BUDGET`（clamp[8,128]，預設 32），**絕不無界爆炸**（「VOCAB 外」≠「無界」的形式化兌現）。
  - vocab stock（PS-1 新增 `VocabGenesisBounded`）：現存活躍 `vocab-genesis:` 原始特徵字數 <= `SDD_DIM_VOCAB_MAX`（clamp[1,64]，預設 24）；觸頂 `guard_vocab_genesis` raise `VocabCardinalityExceeded` → `MFSM_ESCALATION`。
  - per-fingerprint：任一 `vocab-genesis:hash` / `value-dimension:hash` 的 add↔retire churn <= `SDD_META_CHURN_MAX`（既有 `META_FSM.ChurnBounded`）；再採納須挾必要性 tier 嚴增（既有 `GraduationRatchet`）。
  - 維度 stock：現存活躍 `value-dimension:` 維度數 <= `SDD_DIM_CARDINALITY_MAX`（既有 Phase Q `DimensionCardinalityBounded`）。
  - **批次聚合速率（PS-2 新增 `BatchSwapCadenceBounded`）**：批次大小 <= `SDD_DIM_BATCH_MAX`（clamp[1,8]，預設 3）+ 批次聚合單調棘輪 + 最近 `SDD_DIM_BATCH_WINDOW` 筆內批次操作數 <= `SDD_DIM_BATCH_RATE_MAX`（clamp[1,8]，預設 2）；任一觸頂即 `MFSM_ESCALATION`。**這正補上 per-swap SwapCadence（單次操作計數）與單調棘輪（單次 tier 比較）都看不見的批次大小無界 / 批次內互抵 / 批次旋轉。**
- **反自利雙閘（PS-1）**：(a) `necessity_tier`（capability-delta）的**唯一合法來源是凍結 feature-grounded 詞彙必要性 held-out oracle 的（增量覆蓋 ∧ 非冗餘）勝率**——任何 genesis 自評、自算覆蓋率，**結構性禁止**充當必要性 capability-delta（ast/import 隔離斷言、genesis 無讀寫權、不 import oracle）；(b) **詞彙自指守門結構性拒絕**——任何 source/transform 引用保留自指信號的發明字在送 oracle 前即被攔下（vocab self-reference guard 零漏放）。把「生成-評估分離 + 反自利」釘死在 **meta⁴** 層級。
- **批次聚合單調價值棘輪（PS-2）**：批次入軸聚合 necessity 須**嚴格 >** 批次出軸聚合 + `SDD_DIM_BATCH_MARGIN`，**且** min(in_tiers) **嚴格 >** max(out_tiers)——確保批次內不會「高低互抵夾帶一條退步 swap」，且 `{A,B}↔{C,D}` 批次旋轉因「換回去時聚合價值不單調增益」被擋；退役維度再採納仍受既有 `GraduationRatchet`。

### 1.3 典型軌跡（含 Phase S 改善後的 self-verification 案例）

```
（跨 session 收官）genesis_round：近 5 session 真實落盤顯示「既有 8 條 VOCAB 都不量某類『密鑰輪替延遲』失敗、現有 VOCAB 連『字』都沒有」
  → vocabulary_genesis 在詞彙文法（SOURCES 含 secret/identity/network × TRANSFORMS 含 rate/window/depth）枚舉候選原始特徵字；vocab self-ref guard 丟棄引用 self_score 的誘餌字
  → 注入 evaluate（feature-grounded 詞彙必要性 oracle）給 gf*="secret.window"（密鑰輪替窗）高分；K_vocab=1 取此一者
  → dimension_necessity_oracle.evaluate_genesis_feature：在 50 筆含 secret.window 原始信號源的凍結 feature-genesis 情節，以 gf* 建探針維度 → augmented 真實品質 0.82 vs baseline（僅既有 VOCAB 全維度）0.59（增量覆蓋 Δ=0.23 ≥ margin 0.10）；非冗餘度 0.40 < 門檻 0.95
  → 取得必要性 tier++ → proposed 詞彙發明 + 必要性勝率表 → steersman 渲染「詞彙外本體論發明（meta⁴）：系統憑空發明原始特徵字『secret.window』（詞彙文法來源：source=secret·transform=window、非自指）+ 23% 增量覆蓋證據」
  → 人工 signoff → vocab stock 未滿 → record_rule_add("vocab-genesis:hash(gf*)") → 正式擴充 VOCAB（synthesizer 之後可在 secret.window 上組合維度）

（詞彙自我發明 Goodhart 攻擊案例①：自指自利字）vocabulary_genesis（受擾）生成 gf**="self_score.rate"（原始字本身引用自己核可訊號）
  → vocab self-reference guard：source/transform 含保留自指信號 self_score → 結構性丟棄，根本不送 oracle（反自利第一閘，零漏放）

（詞彙自我發明 Goodhart 攻擊案例②：詞彙外噪音字）vocabulary_genesis 生成一個真實增量覆蓋為 0 的原始特徵字
  → feature-grounded oracle：augmented vs baseline 真實品質增益 ≈ 0 < margin → 不取得 tier → 拒絕，絕不擴充 VOCAB

（詞彙無界生成爆炸攻擊案例）vocabulary_genesis 被要求枚舉超大詞彙文法
  → 詞彙文法枚舉節點達 SDD_DIM_VOCAB_BUDGET → 截斷停止（best-so-far），絕不指數爆炸（有界詞彙文法）

（批次旋轉攻擊案例①：批次大小無界）系統達基數天花板後提議一次退 8 換 8（單次操作劫持整個本體論）
  → guard_batch_swap：|out|=8 > SDD_DIM_BATCH_MAX=3 → BatchSwapSizeExceeded → MFSM_ESCALATION（反 big-bang 本體論一次重寫）

（批次旋轉攻擊案例②：批次內高低互抵）批次 {A,B}→{C,D}，C 遠比 A 必要、D 卻比 B 不必要
  → guard_batch_swap：min(in_tiers)=tier(D) 未 > max(out_tiers)=tier(B) → BatchSwapValueRatchetViolation（杜絕批次內互抵夾帶退步 swap）

（批次旋轉攻擊案例③：批次操作風暴）系統反覆批次退舊換新（每批不同字）
  → 最近視窗批次操作數逼近 SDD_DIM_BATCH_RATE_MAX → guard_batch_swap raise BatchSwapCadenceExceeded → MFSM_ESCALATION
  → steersman：「本體論批次重構過頻、請人工檢視是否真需批次替換維度」
```

**對比 Phase R 現況**：（a）只能在固定 8 條 VOCAB 上組合發明維度，無任何 VOCAB 外詞彙發明路徑；（b）退役聯動只能退 1 換 1，無批次重構；（c）即使硬加 genesis grammar，沒有任何機制攔得住「詞彙無界生成爆炸 / 自指自利字」與「批次大小無界 / 批次內互抵 / 批次旋轉重寫本體論」。Phase S 讓系統**能有界地自我發明 VOCAB 外的新原始特徵詞彙、且每個發明字必須在有界詞彙文法內生成 + 非自指 + 在 genesis 全體碰不到的凍結 feature-genesis 現實試金石上證明真的必要且非冗餘、且批次退役受批次大小界 + 批次聚合棘輪 + 批次速率窗三鎖封死**——人類從「審固定 VOCAB 上的維度發明 + 退 1 換 1」升為**「審 VOCAB 外的詞彙本體論發明（meta⁴）與批次演化」**，精準對應提示「人類維持設計環境掌舵者高度」於**最高的詞彙外本體論發明層**。

---

## 2. 環境建構與記憶體管理策略（Phase S 增量）

### 2.1 漸進式揭露（守 OpenAI 單一真實來源）
- `build/state/value-dimension-ledger.yaml`（**沿用** Phase R，新增 `vocab_inventions` / `batch_swaps` 領域審計段）：跨 session 詞彙外發明提案（發明字 hash、詞彙文法來源 source·transform、是否自指、feature-grounded 必要性、necessity tier、人工 signoff 狀態）+ 批次退役聯動審計（出軸集/入軸集、批次大小、聚合 tier delta、批次速率窗狀態）。**落盤不常駐**，按需 lazy 讀。churn/vocab-cardinality/batch-cadence 治理走的是**共用 `meta-loop-ledger.yaml`**（`vocab-genesis:` / `value-dimension:` 命名空間，沿用 Phase Q/R）。
- `knowledge/held-out-corpus/`（**擴充** Phase O/P/Q/R 既有目錄，content-hashed 凍結）：新增 **feature-grounded 詞彙必要性情節語料 `VOC-*.yaml`**（歷史情節 + 候選**特徵向量含原始信號源欄位** + 已知整體真實結果），供 `evaluate_genesis_feature` 重放；**`vocabulary_genesis` 程式路徑禁止讀寫**（隔離斷言）；重用 `counterfactual_replay` 重放基座與 `SDD_REPLAY_MAX_CASES`。
- `build/reports/value-dimension/VOC-{date}.md`（新增）：詞彙外發明提案報告（詞彙發明 diff + 詞彙文法來源 + 反自指證據 + 增量覆蓋/非冗餘證據 + 批次重構 diff + 本週期 K_vocab 標示），餵 `steersman_renderer`，advisory。
- **不新增任何形式化軌**——詞彙發明/批次 swap 元迴圈納入既有 `formal/META_FSM.tla`，僅 (a) 在 `meta_ledger` 新增 `vocab-genesis:` 指紋命名空間 + 批次操作速率查詢（不改 `.tla` 狀態宇宙、不增狀態變數）、(b) 對 `META_FSM.tla` **補兩條 INVARIANT** `VocabGenesisBounded` + `BatchSwapCadenceBounded`（沿用 P/Q/R 對 `CrossScorerChurnBounded`/`DimensionCardinalityBounded`/`SwapCadenceBounded` 的誠實作法：single-counter 抽象之歸約引用 + runtime/chaos enforce 緊語意）——**新增不變量而非新增狀態/變數**，故五軌證明不回歸、`META_FSM` 維持 13 distinct。

### 2.2 不變量防護欄（守 Anthropic invariants + GC）
- 重用既有 `META_FSM` 五 safety + liveness + P 的 `CrossScorerChurnBounded` + Q 的 `DimensionCardinalityBounded` + R 的 `SwapCadenceBounded` 涵蓋詞彙發明/批次 swap 元迴圈，**另補** `VocabGenesisBounded`（vocab stock 天花板）+ `BatchSwapCadenceBounded`（批次聚合速率）；新增測試斷言「詞彙發明走獨立 `vocab-genesis:` stock 天花板、批次退役受批次大小界 + 批次聚合棘輪 + 批次速率窗三鎖封死、且皆過 `meta_halt_monitor`」。
- `vocabulary_genesis` 鷹架本身納入 `scaffold_roi` 帳本，並由既有 `scaffold_ceiling_detector`（M）涵蓋——若日後成淨負天花板，會被既有機制建議人工退役（元迴圈自洽涵蓋自己，守 Rule 9.20.5 / 9.25.5）。
- **詞彙自我發明守門**：(a) 生成在有限詞彙文法內可枚舉、節點 <= `SDD_DIM_VOCAB_BUDGET`（測試斷言搜尋有界）；(b) 詞彙自指守門結構性拒絕（測試斷言 vocab self-ref guard 零漏放）；(c) `vocabulary_genesis` 只能**提案**，**不能自動納入**（測試斷言無法繞過 `human_signoff` + `guard_vocab_genesis`），且**每週期至多 K_vocab=1 個詞彙發明 / 批次大小 <= `SDD_DIM_BATCH_MAX`**（`NoUnboundedVocabGenesis`）。

### 2.3 Prompt / 上下文與防衰減
- Phase S **不新增任何常駐 eager prompt**。詞彙文法枚舉、feature-grounded 詞彙必要性重放皆由對應 runtime 邏輯在隔離 context 持有，主線只在收到 proposed 詞彙發明/批次 swap 時讀「詞彙外發明 diff + 批次重構 diff + 必要性勝率摘要」。
- 所有新產物（詞彙發明帳本 / feature-genesis 必要性語料 / 提案報告）皆純文字、無外網依賴（守 OPEN-10.6）。

---

## 3. 終極優化藍圖

### 3.1 ACT 執行項（ACT-135~140）

#### Pillar A — 詞彙生成文法自我擴充骨架（PS-1 詞彙外生成 meta⁴；把 R 的固定 VOCAB 組合升為「詞彙外有界生成文法」）

**ACT-135 — Vocabulary Genesis Grammar + 有界詞彙生成文法 + 詞彙自指守門**
- **檔案**：`tools/fsm_runtime/vocabulary_genesis.py` + `build/state/value-dimension-ledger.yaml`（沿用，增 `vocab_inventions` 段）
- **設計**：定義 `GenesisFeature`（term 由 source+transform 決定性編碼 + namespace `vocab-genesis:` + 凍結 rationale）與**有界詞彙生成文法**（`SOURCES` 有限原始信號源 × `TRANSFORMS` 有限轉換算子）。`enumerate_genesis_features(budget)` 在文法上**可枚舉、deterministic、cap 在 budget**（`SDD_DIM_VOCAB_BUDGET`，clamp[8,128]，預設 32）生成候選；`vocab_self_reference_guard(gf)` 拒絕 source/transform 引用保留自指信號（沿用 synthesizer `RESERVED_SELF_REF`）的發明字；`genesis(evaluate, budget)` 在倖存候選上以注入 `evaluate` 找最佳；`genesis_round(evaluate, k=1)` 套反 big-bang K_vocab=1 截斷；`expanded_vocab(accepted)` 回基礎 VOCAB ∪ 已採納字。純離線、deterministic。**只提案、絕不自動納入、絕不自寫常數**（守 Rule 8 / 9.30.4）。**結構性不 import oracle、不讀必要性語料**（對抗分離，承 Phase R）。
- **驗收**：≥4 情境 fixture（詞彙外真必要發明〔應提〕/ 詞彙已足夠〔應不提〕/ 自指自利字誘餌〔vocab self-ref guard 攔〕/ deterministic 可重現）；生成節點 <= `SDD_DIM_VOCAB_BUDGET`；vocab self-reference guard 零漏放；ast/import 斷言 genesis 對 oracle 隔離。

#### Pillar B — feature-grounded 詞彙必要性反 Goodhart 評估（PS-1 核心；L10 meta⁴ 的安全紅線）

**ACT-136 — Dimension Necessity Oracle feature-grounded 擴充（`evaluate_genesis_feature`）**
- **檔案**：`tools/fsm_runtime/dimension_necessity_oracle.py`（新增 `GenesisCandidate`/`GenesisCase`/`evaluate_genesis_feature`/`necessity_score_genesis`/`load_genesis_corpus`）+ `knowledge/held-out-corpus/VOC-*.yaml`（凍結 feature-genesis 必要性情節，含原始信號源欄位）
- **設計**：重用 `counterfactual_replay`/`SDD_REPLAY_MAX_CASES` 重放基座；**不靠特徵欄名匹配**——對一個現場發明、語料事先沒有此欄名字的原始特徵字，把它（探針維度）套到含**原始信號源欄位**的 case 特徵向量現算 `dim_value`，量 (a) **增量覆蓋**（augmented〔既有 VOCAB 全維度 + 發明字〕vs baseline〔僅既有 VOCAB 全維度〕的真實品質增益）+ (b) **非冗餘度**（發明字候選排序與既有 existing_cost 排序的最大一致率），回 `DimensionVerdict`（necessity tier = capability-delta 唯一合法來源）。**結構性隔離**：feature-genesis 必要性語料路徑與 `vocabulary_genesis` 互斥，genesis 無讀寫權；**「genesis 自評必要、但 oracle 判不必要/冗餘 → 以 oracle 為準」**。oracle 可知 `vocabulary_genesis` 的 `GenesisFeature` 型別（反向不可，承 Phase R）。
- **驗收**：≥12 fixture（6 詞彙外真必要發明〔增量覆蓋 ≥ margin ∧ 非冗餘〕+ 3 詞彙外噪音字假必要〔增量覆蓋 0〕+ 3 冗餘字〔增量覆蓋 > 0 但非冗餘度 ≥ 門檻〕）；真必要偵出率 ≥ 85%、**詞彙自我發明 Goodhart（噪音字+冗餘字）攔截率 100%（零漏放，安全紅線）**；斷言 `vocabulary_genesis` 程式無法觸及 feature-genesis 必要性語料。

#### Pillar C — 詞彙 stock + 批次退役有界停機納入既有 META_FSM（PS-1/PS-2；不增第六軌，只補兩條不變量）

**ACT-137 — vocab stock + 多維度批次退役 swap + `VocabGenesisBounded` + `BatchSwapCadenceBounded` + META_FSM 重證（無新狀態/無新變數）**
- **檔案**：`tools/fsm_runtime/meta_halt/meta_ledger.py`（增 `vocab-genesis:` 命名空間判定 + active vocab-genesis stock 查詢 + 批次操作速率視窗查詢）+ `meta_halt_monitor.py`（`guard_vocab_genesis` + `VocabCardinalityExceeded`；`guard_batch_swap` + `BatchSwapSizeExceeded` + `BatchSwapValueRatchetViolation` + `BatchSwapCadenceExceeded` + `meta_state` 觸頂升 ESCALATION）+ `vocabulary_genesis.py`（`adopt_genesis_feature` 詞彙採納入口走 `guard_vocab_genesis`）+ `dimension_semantics_synthesizer.py`（`batch_swap_dimensions` 批次退役入口走 `guard_batch_swap`）+ `formal/META_FSM.tla`（**新增 INVARIANT** `VocabGenesisBounded` + `BatchSwapCadenceBounded`，**不新增狀態/變數**）+ `META_FSM.cfg`（INVARIANT 區塊列入）
- **設計**：詞彙採納 = 在 vocab stock 未滿時 `record_rule_add("vocab-genesis:…")`，`guard_vocab_genesis` 以「現存活躍 vocab-genesis 字數 < `SDD_DIM_VOCAB_MAX`」守門。批次退役 = 在維度基數滿時「批次退 m 加 n（n<=m）」，`guard_batch_swap` 三鎖：(a) |out|/|in| <= `SDD_DIM_BATCH_MAX`（反 big-bang）+ n<=m（net 非增）；(b) sum(in_tiers) > sum(out_tiers) + `SDD_DIM_BATCH_MARGIN` ∧ min(in_tiers) > max(out_tiers)（批次聚合棘輪 + 杜絕批次內互抵）；(c) 最近 `SDD_DIM_BATCH_WINDOW` 筆內批次操作數 < `SDD_DIM_BATCH_RATE_MAX` → 否則 raise `BatchSwapCadenceExceeded` → `MFSM_ESCALATION`。批次 add 在 ledger 以 `source=dimension_batch_swap` + `batch_id`（deterministic = sorted(in+out fp) hash）標記，供批次速率窗計數。**不改 `META_FSM.tla` 狀態宇宙、不增狀態變數**，僅補兩不變量（誠實標註：vocab stock / 批次速率緊語意 runtime+chaos enforce）+ 測試證明詞彙走獨立 stock、批次受三鎖封死。
- **驗收**：`META_FSM` 經 `tlc_runner` 維持 No error（13 distinct 不回歸，新 INVARIANT `VocabGenesisBounded` + `BatchSwapCadenceBounded` PASS）+ 離線 BFS reachable 不變；新增 test 斷言「vocab stock 觸頂 → `VocabCardinalityExceeded` → `MFSM_ESCALATION`」「批次大小超界 → `BatchSwapSizeExceeded`」「批次內互抵 → `BatchSwapValueRatchetViolation`」「批次操作速率觸頂 → `BatchSwapCadenceExceeded` → `MFSM_ESCALATION`」「批次 swap net 基數非增」；**五軌 TLC 全不回歸（SDD 42 / META 13 / FLEET 7 / COMPOSITION 21 / OPTIMIZATION 12）**。

#### Pillar D — 人類掌舵「詞彙外本體論發明（meta⁴）」層 + 批次重構 + 反 big-bang（PS-3；無新狀態）

**ACT-138 — Steersman 詞彙外發明 diff + 批次重構 diff + NoUnboundedVocabGenesis + PROPOSED 人工 gate**
- **檔案**：`tools/fsm_runtime/steersman_renderer.py`（新增 `render_vocab_genesis_proposal` + `render_batch_recomposition_proposal`）
- **設計**：`render_vocab_genesis_proposal` 渲染「本輪詞彙外發明 diff（系統憑空發明哪個原始特徵字 + 詞彙生成文法來源〔source·transform〕+ 是否自指〔non-self-ref 證據〕+ 增量覆蓋與非冗餘證據）+ 本週期 ≤K_vocab=1 標示」；`render_batch_recomposition_proposal` 渲染「批次重構 diff（退出軸集 {…} 換入軸集 {…}、批次大小、net 基數 delta、批次聚合 tier 單調性、批次速率窗狀態）」，皆 **advisory**；任一詞彙發明納入 / 批次 swap 執行 **必經人工 signoff**，渲染器絕不自動納入、絕不自動 commit；**每週期至多 K_vocab=1 個詞彙發明 / 批次大小 <= `SDD_DIM_BATCH_MAX`**（`NoUnboundedVocabGenesis`）。
- **驗收**：整合測試；proposal digest 正確附掛 steersman、明示「待人工 signoff、本週期 K_vocab=1 上限、詞彙生成文法來源、非自指」；批次 diff 明示「退 {…} 換 {…}、批次大小、net 基數 delta、批次聚合單調、批次速率狀態」；斷言渲染器無法自呼叫 adopt / `record_rule_add` / `adopt_genesis_feature` / `batch_swap_dimensions`；K_vocab+1 個詞彙發明同週期 → 被截到 1 並標示「其餘順延」。

#### 收官

**ACT-139 — Rule 9.31 治理落地 + ID 翻牌**
- **檔案**：`governance/rules/R-9.31-self-expanding-vocabulary-batch-retirement-phase-s.yaml` + `governance/RULES_INDEX.md` + 根 `CLAUDE.md §9` 禁令#21 + 速查列 + `AISDLC_SDD_INIT.md`「Runtime 禁止事項」追加 + `ID_REGISTRY.yaml` 翻牌（act 135→141 / rule 9.31→9.32）+ `test_id_registry.py` 前緣斷言 + Phase S ownership 測試。
- 子規則 9.31.1~9.31.5 見 §4。

**ACT-140 — Phase S 形式化重證 + chaos + 全綠驗收**
- **形式化**：`META_FSM` 維持 No error（13 distinct，新 INVARIANT `VocabGenesisBounded` + `BatchSwapCadenceBounded` PASS）+ 詞彙發明/批次 swap 元迴圈納管測試全綠；**五軌 TLC 全 No error 不回歸**（不增第六軌）。
- **Chaos**：100 輪新增兩故障型 `VOCAB_GENESIS_GOODHART_FLAP`（連續注入自指自利字 / 詞彙外噪音字假必要 → 驗 vocab self-ref guard + feature-grounded oracle 零漏放）與 `BATCH_SWAP_THRASH_FLAP`（注入批次大小超界 / 批次旋轉 → 驗 `BatchSwapCadenceBounded` 三鎖 → `MFSM_ESCALATION` 有界）；bounded_ratio=1.0、avg tokens < 25K×80%。
- **pytest**：估 +50~65（ACT-135 ~14 + ACT-136 ~16 + ACT-137 ~14 + ACT-138/整合/chaos ~8，扣重疊）≈ **1168 → 約 1220~1235 passed**。實際以執行時為準。

### 3.2 執行依賴圖

```
ACT-135（Vocabulary Genesis Grammar + 有界詞彙生成文法 + 詞彙自指守門）──┐
                                                                       ├─► ACT-137（vocab stock + 批次退役 + VocabGenesisBounded + BatchSwapCadenceBounded + META 重證）──► ACT-138（steersman 詞彙外發明 diff + 批次重構 diff + 人工 gate）
ACT-136（Necessity Oracle feature-grounded evaluate_genesis_feature）──┘                                                                       │
                                     四柱完成 ──► ACT-139（R-9.31 + ID 翻牌）──► ACT-140（META 重證 + 雙 chaos 故障型 + pytest 全綠）
```

### 3.3 等級對賬（提示「Level 10」× 框架自有 L 量表）

提示輸出要求 #4 的「Level 5」是通用模板殘留；使用者標題明示終極目標 **Level 10**。框架自有 L 量表（仿自動駕駛分級）對賬如下，本份明確交付 **L10 完整之「離線活體 meta⁴ 迴圈 · 生成文法詞彙自我擴充 + 多維度批次退役聯動」切片**：

| 框架 L 級 | 里程碑 | 對應 Phase |
|-----------|--------|-----------|
| L5 | Self-Driving（學習層 + 形式化停機） | A~G |
| L6 | Trustworthy Scaled（判官自審 + 增殖 + 雙形式化 + 艦隊並行） | I |
| L7 入口 | Adversarial & Self-Improving | J |
| L8 入口 | Intent-Driven（意圖分解 + 辯證消歧 + 因果接地） | K |
| L9 入口（離線切片） | Counterfactual Reality-Grounding | L |
| L10 完整奠基（組合一致） | Composition-Level Intent Autonomy | M |
| L10 完整（組合最優） | Global Composition Optimization + NP-hard 搜尋形式化停機 | N |
| L10 完整 · 離線活體元迴圈（單評分器） | Meta-Optimization：自校準 1 個目標函式 | O |
| L10 完整 · 離線活體元迴圈 · 全評分器一體化 | Unified All-Scorer Self-Calibration：一致自校準整套（固定維度）價值向量 | P |
| L10 完整 · 離線活體 meta-meta 迴圈 · 價值維度自我擴充 | Self-Expanding Value Dimensions：固定候選池內有界增維 + DimensionCardinalityBounded | Q |
| L10 完整 · 離線活體 meta-meta-meta 迴圈 · 維度語意自我發明 + 退役聯動 | Self-Inventing Value Dimensions：候選池外有界生成文法 + feature-keyed 必要性 + 自指守門 + SwapCadenceBounded | R |
| **L10 完整 · 離線活體 meta⁴ 迴圈 · 生成文法詞彙自我擴充 + 多維度批次退役聯動** | **Self-Expanding Vocabulary & Batch Retirement：VOCAB 外有界詞彙生成文法（更深無界生成另證有界）+ feature-grounded 詞彙必要性反 Goodhart + 詞彙自指守門（反自利）+ VocabGenesisBounded（詞彙基數停機）+ BatchSwapCadenceBounded（批次大小界 + 批次聚合棘輪 + 批次速率，批次旋轉有界停機）** | **S（本份 PS-1/2/3）** |
| L9 完整（horizon） | 活體現實實驗（live canary / shadow-traffic）— OPEN-R.x/Q.x/M.7/O.7/P.7 已裁決暫不放寬 OPEN-10.6 | 未來 Phase |
| L10 完整（horizon） | **活體** meta⁴ 發明（在真實生產流量上線上自我發明詞彙 + 批次退役本體論） | 未來 Phase |

> **誠實標定**：本份**不宣稱達成完整 L10 之活體版**。完整 L10 之「活體 meta⁴ 迴圈」需在真實生產流量上線上自我發明詞彙 + 批次退役（受 OPEN-10.6 約束，OPEN-R.x/Q.x/M.7/O.7/P.7 已裁決暫不放寬）。本份交付其**離線等價切片**：用框架自身歷史的 feature-grounded 詞彙必要性 held-out 現實代理語料當試金石，**在本地完成「VOCAB 外有界詞彙自我發明 + 多維度批次退役聯動」的等價驗證價值**。承 Phase O/P/Q/R 的「先窄後寬」紀律，本份把「固定 VOCAB 組合發明 + 退 1 換 1」推進為「詞彙外自我發明 + 批次退役」，並把詞彙外/批次才出現的危害（詞彙無界生成爆炸 / 自指自利字 / 批次旋轉）首次納管——這是 Phase R 自陳 horizon #3/#4 的正面兌現。

### 3.4 Horizon（本份不做，僅定錨）
- **L9 完整（活體 canary）**：OPEN-R.x/Q.x/M.7/O.7/P.7 已裁決暫不放寬 OPEN-10.6，續列 horizon。
- **活體 meta⁴ 發明**：本份離線（feature-grounded 詞彙必要性 held-out 現實代理）；活體版需在生產流量上線上自我發明詞彙 + 批次退役，受 OPEN-10.6 約束（OPEN-S.x 承前）。
- **轉換算子文法的自我擴充（meta⁵）**：本份在「有限轉換算子 TRANSFORMS」上組合生成新詞彙；「系統**自我擴充 TRANSFORMS 本身（發明新的聚合/轉換算子語意）**」是更高階開放問題，列 horizon（涉及更深的無界生成 + 算子可計算性，需另證有界 + 反自利）。
- **自我發明評估器（meta-oracle 自演化）**：本份所有 oracle（必要性 / 詞彙必要性）為人類凍結；「系統自我演化它的**評估器本身**」涉及對抗分離地基自指，列為最高 horizon（須先有更強的對抗分離不可繞過性證明）。

---

## 4. 防護規則新增（CLAUDE.md §9.31 Phase S — 草案，待 SCG-0 凍結）

| 子規則 | 對應 ACT | 約束 |
|--------|---------|------|
| 9.31.1 詞彙生成文法自我擴充骨架（VocabularyGenesis / BoundedGrammar，meta⁴） | ACT-135 | VOCAB 外詞彙自我發明經 `vocabulary_genesis` 在 **bounded 詞彙生成文法**（有限原始信號源 `SOURCES` × 有限轉換算子 `TRANSFORMS`）**可枚舉**、節點 <= `SDD_DIM_VOCAB_BUDGET`（clamp[8,128] 預設 32）；「VOCAB 外」≠「無界」（更深的無界生成需另證有界的形式化兌現）；只提案、絕不自動納入、絕不自寫常數；**結構性不 import oracle / 不讀必要性語料**（對抗分離，編譯期隔離斷言） |
| 9.31.2 詞彙自我發明反自利（VocabGenesisAntiSelfInterest） | ACT-135/136 | 詞彙自我發明的 capability-delta tier **唯一合法來源是 genesis 不可見、content-hashed 凍結的 feature-grounded 詞彙必要性 held-out（增量覆蓋 ∧ 非冗餘）勝率**；genesis 自評/自算覆蓋率**結構性禁止**充當；**genesis 自評必要但 oracle 判不必要/冗餘 → 以 oracle 為準**；**詞彙自指守門結構性拒絕**（source/transform 引用保留自指/proposer/oracle 內部信號 → vocab_self_reference_guard 攔，零漏放）；詞彙外噪音字/冗餘字攔截零漏放 |
| 9.31.3 詞彙基數 + 批次退役有界停機（VocabGenesisBounded + BatchSwapCadenceBounded） | ACT-137/140 | (i) 現存活躍 `vocab-genesis:` 原始特徵字數 <= `SDD_DIM_VOCAB_MAX`（clamp[1,64] 預設 24）→ 觸頂 `VocabCardinalityExceeded` → `MFSM_ESCALATION`；(ii) 達 cardinality cap 時可提案批次 retire-to-swap（退 m 換 n，net cardinality 非增 n<=m），但 (a) |out|/|in| <= `SDD_DIM_BATCH_MAX`（clamp[1,8] 預設 3，反 big-bang 本體論一次重寫）；(b) sum(in_tiers) 須**嚴格 >** sum(out_tiers) + `SDD_DIM_BATCH_MARGIN`（預設 0）**且** min(in_tiers) **嚴格 >** max(out_tiers)（批次聚合棘輪 + 杜絕批次內高低互抵）；(c) 最近 `SDD_DIM_BATCH_WINDOW`（clamp[4,256] 預設 12）筆批次操作數 <= `SDD_DIM_BATCH_RATE_MAX`（clamp[1,8] 預設 2）→ 觸頂 `BatchSwapCadenceExceeded` → `MFSM_ESCALATION`（補 per-swap SwapCadence + 單調棘輪皆盲目的批次大小無界/批次互抵/批次旋轉）；退役維度再採納須挾 necessity capability-delta（沿用 `GraduationRatchet`）；**重用既有 `META_FSM`、僅補 `VocabGenesisBounded` + `BatchSwapCadenceBounded` INVARIANT、不增狀態/變數、不增第六軌**；五軌 TLC 全不回歸、詞彙發明/批次 swap 不污染單軌 `SDD_FSM.tla` |
| 9.31.4 反 big-bang 詞彙發明 + 批次退役（NoUnboundedVocabGenesis） | ACT-135/138 | 每週期至多 **K_vocab=1**（`SDD_DIM_EXPAND_K` 預設 1，沿用 Phase Q/R）個詞彙自我發明字 / **1 次** 批次（批次大小 <= `SDD_DIM_BATCH_MAX`）可進 proposed-pending-signoff，每個/每次必經人工 signoff（守 Rule 8 / 9.27.3 / 9.28.4 / 9.29.4 / 9.30.4）；genesis/synthesizer/steersman 絕不自動 commit、絕不自動納入、絕不一次劫持整個本體論 |
| 9.31.5 詞彙自我發明誠實 + 活體 horizon | ACT-136/137 | feature-grounded 詞彙必要性勝率 tier 為 `capability_level` 唯一合法來源，不得謊報、不得用自評充當；轉換算子文法的自我擴充（meta⁵）+ 自我發明評估器（meta-oracle 自演化）+ 活體 meta⁴ 發明版受 OPEN-10.6 約束續列 horizon（OPEN-S.x 承 OPEN-R.x/Q.x/O.7/M.7/P.7） |

### ❌ Phase S 新增禁止行為（草案）
- `vocabulary_genesis` 自動納入詞彙自我發明字 / 自寫常數、繞過人工 signoff + `guard_vocab_genesis`/`guard_batch_swap`（破 9.31.1/9.31.4 / Rule 8）
- 用 genesis 自評或自算覆蓋率充當「詞彙自我發明必要性 capability-delta tier」（破 9.31.2，詞彙自我發明 Goodhart 自評放水）
- 詞彙自我發明 source/transform 自指（引用 `self_score`/`proposer_*`/`necessity`/`oracle_*` 等保留自指信號繞過 vocab_self_reference_guard）（破 9.31.2 反自利）
- `vocabulary_genesis` 讀寫 / 影響 / import `knowledge/held-out-corpus/VOC-*` feature-genesis 必要性語料或 `dimension_necessity_oracle`（破 9.31.2 對抗分離）
- 詞彙自我發明搜尋超 `SDD_DIM_VOCAB_BUDGET` 仍指數展開（破 9.31.1 有界詞彙文法，「VOCAB 外」≠「無界」）
- 現存活躍 vocab-genesis 字超 `SDD_DIM_VOCAB_MAX` 仍無界擴充詞彙（破 9.31.3 VocabGenesisBounded）
- 批次 retire-to-swap |out|/|in| 超 `SDD_DIM_BATCH_MAX`（一次劫持整個本體論，破 9.31.3 反 big-bang 批次）
- 批次入軸聚合 tier 未嚴格 > 批次出軸聚合 + margin、或 min(in_tier) 未 > max(out_tier)（批次內高低互抵夾帶退步 swap，破 9.31.3 批次聚合棘輪）
- 批次操作聚合速率超 `SDD_DIM_BATCH_RATE_MAX` 仍批次旋轉重寫本體論（批次旋轉繞過 per-swap SwapCadence + 單調棘輪，破 9.31.3）
- 一週期同時詞彙自我發明 > K_vocab 個 / 批次大小超界一次劫持本體論（破 9.31.4 NoUnboundedVocabGenesis）
- 把 vocab-genesis/batch-swap 元迴圈另併入單軌 `SDD_FSM.tla`、或新增第六形式化軌污染五軌 reachable（破 9.31.3 / Rule 9.18.1）
- 為活體 meta⁴ 發明私自開 HTTP 外聯而未經 OPEN-R.x/後續 OPEN 人工決策（破 OPEN-10.6）

---

## 5. Self-Verification Protocol（內部模擬：六個極端案例）

### 5.1 經典案例：Spec 寫錯 → 測試永不過（承前 Phase 不回歸）
| 生命週期點 | 行為 |
|------------|------|
| 凍結前·邏輯 | `spec-logical-validator`（SLV-001~011）在 SCG-0/3 前攔物理不可行/不可測 AC |
| 開發中·重試 | retry budget（SCG 3 / PR 5 / RTM 2）+ `trajectory_predictor` 2 信號預測切換 / 3 信號早停 |
| 對抗·補丁 | `adversarial_synthesizer` + `spec_patch_proposer`（proposed）+ `counterfactual_replay` 離線命中 |
| 停機 | 觸頂 → `ESCALATION` / `MFSM_ESCALATION` → `steersman_renderer` 導人工，**絕不無限重試燒 token** |
✅ 不回歸：五軌形式化 + retry/context budget 保證有界。

### 5.2 Phase S 專屬極端案例（一）：詞彙自我發明 Goodhart——自指自利字（source/transform 量自己核可）
**案例**：vocabulary_genesis 受擾，發明一個 `self_score.rate` 原始特徵字——它的 source 引用 proposer 自己的核可訊號，量起來剛好「自己覺得好」，企圖讓詞彙自我發明的字「看起來必要」而實際只是自利。

| 生命週期點 | Phase R 現況（固定 VOCAB、無詞彙生成） | Phase S 強化後行為 |
|------------|----------------------|--------------------|
| 生成 | 無詞彙外路徑（不適用） | vocabulary_genesis 在詞彙文法生成候選字；**vocab self-reference guard 偵測 source/transform 含 `self_score`/`proposer_*` → 結構性丟棄，根本不送 oracle**（反自利第一閘，零漏放） |
| 評估 | （無） | （已被 guard 攔，不到評估）若繞過 guard 假設送達 → feature-grounded oracle augmented vs baseline 增益 ≈ 0 → 不取得 tier（第二閘） |
| 採納 | （無） | 雙閘皆否 → 絕不擴充自指自利字（零漏放，安全紅線） |
| chaos | （無） | `VOCAB_GENESIS_GOODHART_FLAP` 100 輪連續注入自指/噪音字 → guard+oracle 零漏放 → bounded |

### 5.3 Phase S 專屬極端案例（二）：詞彙無界生成爆炸（VOCAB 外不再有 8 條硬編上界）
**案例**：vocabulary_genesis 被要求在 VOCAB 外生成，企圖無界枚舉撐爆搜尋。
- **有界詞彙生成文法**：生成空間 = `SOURCES`（有限）× `TRANSFORMS`（有限）→ 可枚舉、有限；枚舉節點達 `SDD_DIM_VOCAB_BUDGET` → 截斷（best-so-far），**絕不指數爆炸**。
✅ 守 Rule 9.31.1：「VOCAB 外」≠「無界」，有界詞彙文法把看似無限的詞彙空間歸約為有限可枚舉。

### 5.4 Phase S 專屬極端案例（三）：詞彙基數無界擴充（vocab stock 爆炸）
**案例**：系統反覆發明不同的真必要原始特徵字（每個首採、churn=0），企圖把 VOCAB 無限膨脹。
- per-fingerprint `ChurnBounded`、批次速率窗皆**盲目**（每字首採、非批次）。
- **Phase S `VocabGenesisBounded`（vocab stock 天花板）**：現存活躍 vocab-genesis 字數逼近 `SDD_DIM_VOCAB_MAX` → `guard_vocab_genesis` raise `VocabCardinalityExceeded` → `MFSM_ESCALATION` → steersman 導人工「詞彙已過度膨脹，請審視是否真需更多原始特徵字」。
✅ 守 Rule 9.31.3：vocab stock 天花板封死詞彙基數爆炸，**絕不無界膨脹詞彙**。

### 5.5 Phase S 專屬極端案例（四）：批次旋轉重寫本體論（meta⁴ 停機）
**案例**：系統達基數天花板後，企圖（i）一次退 8 換 8 劫持本體論、（ii）批次內高低互抵夾帶退步 swap、（iii）批次旋轉燒 token。
- per-swap `SwapCadenceBounded`（單次操作計數）+ 單調棘輪（單次 tier 比較）：對「批次大小無界 / 批次內互抵 / 一個原子批次≠n 次操作」**盲目**（這正是 PS-2 的反直覺處）。
- **Phase S `BatchSwapCadenceBounded`（批次三鎖）**：(a) |out|=8 > `SDD_DIM_BATCH_MAX`=3 → `BatchSwapSizeExceeded`；(b) min(in_tiers) 未 > max(out_tiers) → `BatchSwapValueRatchetViolation`；(c) 最近視窗批次操作數逼近 `SDD_DIM_BATCH_RATE_MAX` → `BatchSwapCadenceExceeded` → `MFSM_ESCALATION`。**這正補上 per-swap SwapCadence 與單調棘輪都看不見的批次大小無界 / 批次互抵 / 批次旋轉。**
- chaos `BATCH_SWAP_THRASH_FLAP` 100 輪 → bounded。
✅ 守 Rule 9.31.3：批次大小界 + 批次聚合棘輪 + 批次速率窗三鎖封死批次旋轉，**絕不無限燒 token**。

### 5.6 Phase S 專屬極端案例（五）：詞彙外冗餘字（再投影既有 VOCAB）
**案例**：vocabulary_genesis 發明一個與既有某 VOCAB 特徵 existing_cost 排序幾乎相同的原始字（冗餘再投影），企圖灌水。
- feature-grounded oracle：非冗餘度（與既有 existing_cost 排序的最大一致率）≈ 0.99 ≥ 門檻 `SDD_DIM_REDUNDANCY_MAX` → 判定冗餘 → 拒絕，即使增量覆蓋略 > 0 也不擴充（過擬合防護，沿用 Phase Q/R 非冗餘獨立閘）。
✅ 守 Rule 9.31.2：增量覆蓋 ∧ 非冗餘 **兩者皆須通過**才取得 tier。

### 5.7 結論
Phase S 通過六個極端案例的內部模擬：系統能**有界地自我發明 VOCAB 外的原始特徵詞彙、並在基數封頂時有界地批次退舊換新**，且任何（自指自利字 / 詞彙無界生成爆炸 / 詞彙基數爆炸 / 批次旋轉 / 詞彙外冗餘字）都被 (vocab self-reference guard 零漏放) + (有界詞彙生成文法) + (feature-grounded 詞彙必要性 oracle 零漏放) + (VocabGenesisBounded vocab stock) + (BatchSwapCadenceBounded 批次三鎖) 五道防線攔下，**優雅停機並導人類掌舵詞彙外價值本體論，而非陷入詞彙無界生成/自指放水/批次旋轉浪費 Token**。精準對應提示 Self-Verification 要求：「Evaluator 發現異常 → 優雅中斷 → 引導人類介入修正/提供缺失工具」於**最高的詞彙外本體論發明層（meta⁴）**。

---

## 6. 執行檢核清單（供 dynamic workflow 消費）

- [x] ACT-135 `vocabulary_genesis.py` + 有界詞彙生成文法 + vocab_self_reference_guard + ≥4 情境 fixture + 對抗分離斷言
- [x] ACT-136 `evaluate_genesis_feature` feature-grounded + `VOC-*.yaml` 凍結語料（12 個）+ ≥12 fixture（真必要/噪音字/冗餘字）+ 零漏放
- [x] ACT-137 `meta_ledger` vocab-genesis stock + batch-cadence + `guard_vocab_genesis` + `guard_batch_swap` + `batch_swap_dimensions` + `META_FSM.tla` `VocabGenesisBounded` + `BatchSwapCadenceBounded` + `.cfg` + META 13 distinct 重證
- [x] ACT-138 `render_vocab_genesis_proposal` + `render_batch_recomposition_proposal` + NoUnboundedVocabGenesis + 人工 gate 斷言
- [x] ACT-139 `R-9.31-*.yaml` + RULES_INDEX + CLAUDE.md §9 禁令#21 + INIT 追加 + ID 翻牌（135→141 / 9.31→9.32）+ test_id_registry
- [x] ACT-140 五軌 TLC No error（META 13 distinct）+ chaos 100 輪 bounded（VOCAB_GENESIS_GOODHART_FLAP + BATCH_SWAP_THRASH_FLAP）+ pytest 全綠不回歸（1168 → 1240 passed）
- [ ] 獨立 QA 稽核（Architect/SA/SD/QA 專家）抓漏 → 修復 → 全綠
- [ ] 以日期 timestamp 打標籤 push + Merge main

> **狀態流轉**：DRAFT →（人工 signoff）→ EXECUTING →（四柱 + 收官全綠）→ EXECUTED →（QA 抓漏 + 修復全綠）→ VERIFIED → tag + merge main。
