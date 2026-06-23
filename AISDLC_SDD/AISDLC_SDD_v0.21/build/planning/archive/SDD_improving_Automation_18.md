# SDD_improving_Automation_18 — Phase R 藍圖（DRAFT）

**主題**：價值維度語意的自我發明 + 維度自我退役聯動——meta-meta-meta 層的「候選池外有界生成」與「定基數本體論演化」（Self-Inventing Value Dimensions with Bounded Generative Grammar & Cardinality-Preserving Retirement-Swap）— 把 Phase Q 只能在**固定候選池內挑要不要新增哪一條**的能力，推進到「系統能**自我發明一條候選池裡根本沒有的全新維度語意**（候選池外無界生成）」與「**達基數天花板時自我提議退役舊維度換新維度**（退役聯動）」，並正面納管「候選池外生成」與「定基數旋轉」憑空長出的、Phase Q 不存在而 Phase R 才出現的**新危害類別：無界生成爆炸（候選池外不再有 6 條硬編上界）、自我發明 Goodhart（發明一條「量自己核可」的自指軸來自利）、定基數旋轉重寫本體論（per-fingerprint churn 與 cardinality stock 皆盲目的維度震盪）**。
**目標等級**：L10 完整 · 離線活體 meta-meta 迴圈「價值維度自我擴充（固定候選池）」切片（Phase Q 已達：在固定候選池內挑 K_dim=1 條增維）→ **L10 完整 · 離線活體 meta-meta-meta 迴圈「維度語意自我發明 + 退役聯動」切片**（系統不只能在**有限候選池**裡挑要不要增維，更能在**可證有界、反自利、人類掌舵本體論**的前提下，**自我發明候選池外的全新評判軸語意**，並在**基數封頂時有界地以退役換新維度**演化它的價值本體論）。
**建立日期**：2026-06-04
**前置基線**：Phase Q 完整（ACT-123~128 / R-9.29，pytest 1102 passed / 4 skipped / 14 subtests；五軌 TLC 全 No error：`SDD_FSM` 42 reachable、`META_FSM` 13 distinct、`FLEET_FSM` 7、`COMPOSITION_FSM` 21、`OPTIMIZATION_FSM` 12；chaos 100 輪 bounded_ratio=1.0 含 `DIMENSION_GOODHART_FLAP`+`DIMENSION_EXPLOSION_FLAP`，維度 Goodhart 零漏放、維度基數爆炸有界）
**OPEN-10.6 承接**：續承 OPEN-Q.x / OPEN-O.7 / OPEN-M.7 / OPEN-P.7——**暫不放寬 OPEN-10.6 沙箱**（維持本地唯讀／no-HTTP）。故 L9 完整（活體 canary/shadow）與**活體 meta-meta-meta 元迴圈**續列 horizon；**Phase R 與 Phase N/O/P/Q 同策略——全力推「不需放寬沙箱、純離線/形式化」即可達成的 L10 完整剩餘切片（維度語意自我發明 + 退役聯動）**。使用者標題明示「活體 meta-meta 增維待 OPEN-10.6 改判」，故本份維持離線等價切片，活體版列 horizon（OPEN-R.x 承前）。
**狀態**：✅ **EXECUTED 2026-06-04（L10 完整 · 離線活體 meta-meta-meta 迴圈「維度語意自我發明 + 退役聯動」切片達成）** — ACT-129~134 全部完成。**驗收：pytest 1102→1168 passed / 4 skipped / 14 subtests（+66，零回歸）；五軌 TLC 全 No error（`META_FSM` 維持 13 distinct 不回歸、新增 `SwapCadenceBounded` INVARIANT PASS；SDD/FLEET/COMPOSITION 21/OPTIMIZATION 12 不回歸）；chaos 100 輪 bounded_ratio=1.0（新增 `DIMENSION_INVENTION_GOODHART_FLAP` 自指軸+候選池外噪音軸零漏放 + `DIMENSION_SWAP_THRASH_FLAP` → `SwapCadenceExceeded` → MFSM_ESCALATION 有界）；不增第六形式化軌（self-invention/swap 重用既有 META_FSM）；單軌 SDD_FSM 零 self-invention/swap 洩漏；12 凍結 INV feature 語料零漏放（真必要偵出 6/6、自我發明 Goodhart 噪音+冗餘攔截 6/6）。** 獨立 QA 稽核 PASS（0 BLOCKER / 0 MAJOR）+ 修 3 MINOR（RULES_INDEX「29→30 條/30→31 檔」、CLAUDE.md「29→30 條規則一覽」、ID_REGISTRY active_authority「R-9.1~9.27→9.30」）。`ID_REGISTRY` 已翻牌 act 129→135 / rule 9.30→9.31。OPEN-R.x 承 OPEN-Q.x/O.7/M.7/P.7 暫不放寬 OPEN-10.6 沙箱。原 DRAFT 紀錄保留如下。徵用 ACT-129~134 / Rule 9.30（取自 [`governance/ID_REGISTRY.yaml`](../../../governance/ID_REGISTRY.yaml)，單調取號）。
**對應提示**：Karpathy 式「首席 AI 自動化架構師」前沿評估（驗證圖靈完備自動化閉環 → 進化 Level 10 自治）— 承 Phase Q §3.4 自陳 horizon「維度語意的自我發明（meta-meta-meta，候選池外、涉及無界生成需另證有界 + 反自利）」與「價值維度的自我退役聯動（須證不形成 add↔retire 維度震盪繞過棘輪）」續推。

> 🔴 **編號徵用告示**（承 `ID_REGISTRY.yaml` `next_free` = act 129 / rule 9.30）：
> 本藍圖徵用 **ACT-129~134 與 Rule 9.30**（取自登記簿前緣，單調取號）。
> 停滯分支 M3 Hook Health 不持有任何號，復活時另取當下 `next_free`。
> **DRAFT 期間不得翻牌**——僅在獲人工 signoff 並執行至收官（ACT-133）時，才由 `id_registry` 翻牌（act 129→135 / rule 9.30→9.31）+ `test_id_registry.py` 守門固化；撞號由 CI 自動攔截。

---

## 0. 為什麼還需要 Phase R？——對既有設計的誠實剖析（含 `<thinking>` + 圖靈完備性覆查）

<thinking>
這份提示要求「驗證圖靈完備的自動化閉環、進化 Level 10 自治」，附三個必查漏洞視角（狀態轉換 / 上下文衰減 / 停機問題）與一份 self-verification 案例（Spec 寫錯→測試永不過）。延續 Phase K~Q 的紀律，第一步是**對賬而非設計**：這套系統已走過 Phase A~Q、是自陳「L10 完整 + 離線活體 meta-meta 迴圈（價值維度自我擴充）」的成熟框架。盲目重述提示前沿清單只會重造輪子（Phase K~Q 已逐項對賬為 100% 落地）。我的任務是：(1) 覆查圖靈完備 vs 保證停機的核心命題在 Phase R 是否仍成立；(2) 誠實判斷「維度語意自我發明 + 退役聯動」到底是**Phase Q 的換皮**（無新意、不值得一個 Phase），還是**有真正的新結構性缺口**；(3) 用三漏洞視角把那個新缺口挖到 grep 可證零實作。

【零、圖靈完備 vs 停機的命題覆查——Phase R 把監督者的涵蓋面從「固定候選池內挑維度」擴到「候選池外自我發明維度 + 定基數退役聯動」】
Phase O/P/Q 已正面論證：圖靈完備性來自「嵌在迴圈裡的 LLM 生成器 + 無界 `docs/` 紙帶」，保證停機來自「把不可判定的 LLM 包進可判定的有限狀態監督者（FSM + retry/context budget + 五軌 TLC）」——兩者拆在不同基質故不矛盾。Phase Q 的貢獻是把「價值維度的自我擴充」拉進基質 B（重用 META_FSM ChurnBounded/GraduationRatchet + 補 DimensionCardinalityBounded stock 不變量、不增軌）。

但 Phase Q 誠實標定了它只在**固定的候選維度池**（`value_dimension_registry._CANDIDATE_POOL`，6 條硬編 plausible 候選）內挑「要不要新增哪一條」，並把兩件事列為 horizon（§3.4 行 247~248）：**(i) 維度語意的自我發明（meta-meta-meta，候選池外、無界生成需另證有界 + 反自利）**；**(ii) 價值維度的自我退役聯動（達天花板時退舊換新，須證不形成 add↔retire 維度震盪繞過棘輪）**。這裡藏著一個**被 Phase Q 一句帶過、實際上是質變而非量變的命題**：Phase Q 增的是「**從一個有限選單裡點菜**」——候選池只有 6 條 plausible 軸，提案器的搜尋空間先天有界（`candidate_pool` cap 在 `SDD_DIM_PROPOSE_BUDGET`，但池本身就只有 6 條）。「讓系統**自我發明一條選單上根本沒有的全新軸**」不是「再從選單點一道菜」——它是**讓系統自己寫選單**，憑空長出一組**Phase Q（固定候選池）時根本不存在、候選池外生成才出現的新基質**：
- 不再是「在固定 6 條候選裡挑必要性最高的」（Phase Q），而是「**從無限可能的維度語意空間裡生成新軸**」——而候選池外生成是**無界爆炸與自利的天然溫床**：候選池有 6 條硬編上界，候選池外**沒有任何先天上界**；任何「想自利」的提案，只要發明一條「量起來剛好是自己核可訊號」的自指軸，就能繞過 Phase Q「在固定 plausible 池裡挑」的隱含防護（Phase Q 的池裡根本沒有自指誘餌——誘餌只在測試 fixture，生產不可達）。
- Phase Q 的 `DimensionCardinalityBounded`（stock 天花板）只管**現存活躍維度數**——它對「**達天花板後，系統不增維、而是反覆退一條換一條，把基數鎖在天花板卻無限旋轉重寫本體論**」**結構性盲目**：每次 swap 都是 retire 1 + add 1，net cardinality=0（stock 不變、永遠 <= max 不觸頂），且每條維度 per-fingerprint churn 可以 <=1（retire A 換 B、retire B 換 C、retire C 換 D…，每個指紋只動一次）——`ChurnBounded`（per-fingerprint）與 `DimensionCardinalityBounded`（stock）**兩者皆看不見這條「定基數旋轉」的新無界迴圈**。
這正是 Phase R 必須納管的、Phase Q 尚未碰的新東西。

【一、誠實判斷：維度語意自我發明 + 退役聯動是「Phase Q 換皮」還是「有真缺口」？——用 grep 接地】
我先確認框架目前的維度提案**只在固定候選池內挑**（grep `_CANDIDATE_POOL` / `register_candidate` on `value_dimension_registry.py`，實測 6 條硬編 plausible 候選 + `candidate_pool` 只回這 6 條的前綴，無任何「候選池外生成 / 文法 / 自我發明」路徑），且達天花板**只能硬升 ESCALATION**（grep `guard_dimension_expansion`，觸頂直接 raise `DimensionCardinalityExceeded`，無任何「退役換新維度」的 swap 路徑）。再 grep 三組關鍵字證明零實作：
| 關鍵字 | grep 範圍 | 命中 |
|--------|-----------|------|
| `synthesi\|invent.*dimension\|generative.*grammar\|InventedDimension\|candidate.*pool.*external` | `tools/` | **零** |
| `self.referential\|self_ref\|reserved.*probe\|SelfInvention.*Goodhart\|feature.*keyed.*corpus` | `tools/` | **零** |
| `retire.*swap\|swap.*linkage\|SwapCadence\|cardinality.*preserving\|retirement.*swap` | `tools/` | **零** |

→ **維度的「自我發明」與「退役聯動」目前零實作；維度提案被鎖在 6 條硬編候選池內、達天花板只能硬停機。** 真正的價值不在於「再加一個 synthesizer」（那是 Phase Q 換皮），而在於：**候選池外生成 + 定基數退役聯動會打開三個 Phase Q 結構性攔不住的新攻擊面**：
- **無界生成爆炸 + 自我發明 Goodhart**：候選池外生成**沒有 6 條硬編上界**，理論上可生成無限多條候選軸；且系統可發明一條「**probe 引用 proposer/oracle/自評內部信號**」的自指軸（量起來剛好是「自己核可」），讓自我發明的維度「看起來必要」實際只是自利。Phase Q 的必要性 oracle 只**在凍結語料上 by `dimension_name` 匹配**驗證固定池裡的候選——它對「一條**名字事先不在語料裡、由系統現場發明的新軸**到底必不必要、是不是自指自利」**完全盲目**（語料根本沒有這個 `dimension_name` → `examined=0` → 永遠判不必要 → 自我發明根本無法被合法驗證）。← 這是 Phase R 的 **PR-1**（真缺口，非換皮）。
- **定基數旋轉重寫本體論（meta-meta-meta 停機危害）**：系統達基數天花板後，能「退一條換一條」就能**無限旋轉重寫本體論**（每次 swap net cardinality=0、stock 永不觸頂；每條維度 per-fingerprint churn <=1）。這是 stock 鎖死、per-fingerprint churn 皆盲目的 **meta-meta-meta 停機危害**。← **PR-2**。
- **候選池外 + 退役聯動的本體論掌舵真空**：`steersman` 只渲染「固定候選池內挑的增維」；無人渲染「系統**現場發明了一條選單外的新軸、它的生成文法來源（憑什麼有界）、它憑什麼必要且非自指**」，也無人渲染「**退役舊軸 Y 換新軸 Z、net 基數不變、swap 速率狀態**」。人類掌舵在「候選池外本體論發明層」與「退役聯動層」缺席。← **PR-3**。

【二、用提示三個指定漏洞視角，逐一往 Phase Q 之上挖】

(A) 狀態轉換——「生成器↔評估器合約談判」在 meta-meta-meta 層缺「候選池外發明的可有界、可反自利驗證」這一層。
Phase Q 的 `value_dimension_registry`（生成，固定池）↔ `dimension_necessity_oracle`（評估，by name）是一對 meta-meta GAN，但**它只評固定池裡、語料事先知道名字的候選**。當系統**現場發明一條選單外的新軸**，**(1) 誰保證這條生成不會無界爆炸？(2) 誰判「這條現場發明的軸到底必不必要、是不是自指自利」？** 目前無人。提示要的「生成-評估分離 + 主觀標準量化」推到 meta-meta-meta 層，型態是：**(1)** 生成必須被一條**有界生成文法**封住——「候選池外」不等於「無界」，而是「在一個**有限特徵詞彙 × 有界 arity 組合 × 有限聚合算子**的可枚舉生成空間裡生成」，節點 <= `SDD_DIM_INVENT_BUDGET`（這正是「無界生成需另證有界」的正面兌現：把看似無限的語意空間歸約為有限可枚舉文法）；**(2)** 評估必須升級為**feature-keyed（不靠 dimension_name）的必要性 oracle**——對一條**現場發明、語料事先不知名字**的軸，oracle 把它的 probe 套到語料候選的**特徵向量**上現算 `dim_value`，再量增量覆蓋 ∧ 非冗餘；外加一道**自指 probe 守門**（反自利：probe 引用保留的自指/proposer/oracle 內部信號 → 結構性拒絕，零漏放）。→ **PR-1**（最關鍵；純離線、不受 OPEN-10.6 約束）。

(B) 停機問題——「定基數退役聯動」是一條 per-fingerprint churn 與 cardinality stock 皆盲目的新無界迴圈。
這是 Phase R 最深、也最反直覺的停機缺口。Phase Q 的 `DimensionCardinalityBounded` 對**現存活躍維度數（stock）**設天花板；`ChurnBounded` 對**單一指紋**計 add↔retire 抖動。但退役聯動出現一種**全新病態**：系統**不增加基數**（每次 swap = retire 1 + add 1，stock 恆 <= max、永不觸頂）、也**不抖動任何單一指紋**（retire A add B、retire B add C、retire C add D…，每個指紋只 churn <=1），而是**在天花板上無限旋轉替換維度**——把本體論「在乎什麼」反覆重寫，燒 token、永不收斂。這是 Phase Q（只能增、達頂即硬停）時不可能、退役聯動才出現的停機危害。→ 需要一條**退役聯動聚合速率有界停機不變量** `SwapCadenceBounded`：對「最近視窗內的 retire-to-swap 操作數」設聚合速率上界 `SDD_DIM_SWAP_RATE_MAX` → 觸頂即 `MFSM_ESCALATION`；外加**單調價值棘輪**（入軸 necessity tier 須嚴格 > 出軸 + margin，使 A↔B↔A 旋轉因價值不單調而被擋）。← **PR-2**。

(C) 動態演進 / 人類掌舵——「人類審的是『固定池內挑的增維』，缺『候選池外發明 diff』與『退役聯動 diff』」。
Phase Q 的 `render_ontology_expansion_proposal` 渲染**固定候選池**內挑出的新軸。自我發明後，若系統現場發明一條選單外的軸，人類面對的是「一條從未見過的新語意 + 它的生成文法來源」——**沒有人渲染『這條軸是系統怎麼從有限文法生成出來的、它有界嗎、它自指嗎、它憑什麼必要』，也沒有人渲染『退役舊軸換新軸、net 基數不變』這種定基數演化**。提示反覆強調「人類維持設計環境掌舵者高度」——在「候選池外本體論發明」層，掌舵的最高形態是**人類能一眼看懂『系統憑空發明了哪條新評判軸、它的有界生成來源與反自利證據』與『它如何在不擴張基數下退舊換新』，且系統在結構上不可能自動 commit 任何自我發明/退役聯動（每週期至多 K_dim=1 條發明 / 1 次 swap、每條/每次必經人工 signoff）**。→ **PR-3**（候選池外本體論發明掌舵介面 + 退役聯動掌舵 + `NoUnboundedSelfInvention`，K_dim=1，承 Phase Q）。

【三、停機問題紅線覆查——本份比 Phase Q 更危險，因為納管的是「會憑空發明自己座標軸、且能在頂上無限旋轉的迴圈」】
Phase Q 的反諷（讓系統自我擴充它的價值維度集合）在 Phase R 升級為「讓系統**憑空發明選單外的新座標軸、並在基數封頂時無限旋轉替換**」。有界性與防自利必須再加固：
- **仍不新增形式化軌（承 Phase O/P/Q「重用 META_FSM、不增軌」的成熟示範）**：自我發明維度的採納/退役、退役聯動的 swap 全部註冊為 `META_FSM` 既有的 `value-dimension:` 指紋命名空間，其 add↔retire churn 由**同一條** `ChurnBounded`/`GraduationRatchet` 涵蓋，stock 由 Phase Q 的 `DimensionCardinalityBounded` 涵蓋。**但 PR-2 揭示：churn + stock 仍不夠**，故必須**對既有 `META_FSM` 再補一條聚合速率不變量** `SwapCadenceBounded`——關鍵是**沿用 Phase P 對 `CrossScorerChurnBounded`、Phase Q 對 `DimensionCardinalityBounded` 的誠實作法：只新增 INVARIANT、不新增狀態變數**（`META_FSM` 維持 `<<mstate, churn, cap>>` 三變數 / 13 distinct，TLC 仍 No error，五軌不回歸；聚合 swap 速率的緊語意由 runtime `guard_dimension_swap` + chaos `DIMENSION_SWAP_THRASH_FLAP` enforce/驗收，形式化層誠實標註為「single-counter 抽象之歸約引用」）。這守住「圖靈完備能力 / 可證停機控制」的拆分紅線，又不退化成「每個新能力都開一軌」。
- **PR-1 的有界生成文法是硬約束，非建議**：自我發明的搜尋**必在有限文法（有限特徵詞彙 × arity <= `SDD_DIM_INVENT_ARITY` × 有限聚合算子）內可枚舉**，節點 <= `SDD_DIM_INVENT_BUDGET`（clamp，預設 64）——「候選池外」≠「無界」，這是「無界生成需另證有界」的形式化兌現。**PR-1 的反自利是雙閘**：(a) 自我發明維度的 necessity tier **唯一合法來源仍是 proposer 全體碰不到、content-hashed 凍結的 feature-keyed 必要性 held-out 勝率**（增量覆蓋 ∧ 非冗餘）；(b) **自指 probe 結構性拒絕**——任何引用保留自指/proposer/oracle 內部信號（`self_score`/`proposer_*`/`necessity`/`dim_value`/`oracle_*`…）的發明維度，在送 oracle 前即被 synthesizer self-reference guard 攔下（零漏放）。synthesizer **結構性不 import oracle、不讀必要性語料**（ast/import 隔離斷言，承 Phase Q）。
- **PR-2 的退役聯動是「單調價值棘輪 + 聚合速率窗」雙鎖**：swap 入軸 necessity tier 須嚴格 > 出軸 tier + `SDD_DIM_SWAP_MARGIN`（單調價值增益，A↔B↔A 因價值不單調被擋）；且最近視窗 swap 操作數 <= `SDD_DIM_SWAP_RATE_MAX` → 觸頂 `MFSM_ESCALATION`。退役維度再採納仍須挾 necessity capability-delta（既有 `GraduationRatchet`）。
- **PROPOSED-only + 反 big-bang 自我發明/退役聯動，人類掌舵推到「候選池外本體論發明」層**：每週期至多 **K_dim=1** 條自我發明維度 / **1 次** swap 可進 proposed-pending-signoff（`NoUnboundedSelfInvention`，承 Phase Q K_dim=1），每條/每次必經人工 signoff（守 Rule 8 / 9.27.3 / 9.28.4 / 9.29.4）。`steersman_renderer` 渲染「候選池外本體論發明 diff（系統憑空發明哪條軸 + 生成文法來源 + 反自指證據 + 必要性勝率）」與「退役聯動 diff（退 Y 換 Z、net 基數不變、swap 速率狀態）」，讓人類**不讀程式碼就能掌舵整個系統候選池外的價值本體論發明與定基數演化**。

【四、上下文衰減（Context Degradation）視角覆查】
- 自我發明文法枚舉、feature-keyed 必要性 held-out 重放、退役聯動帳本全在**隔離邏輯/落盤**進行，主線只在收到 proposed 自我發明維度/swap 時讀「候選池外發明 diff + 退役聯動 diff + 必要性勝率摘要」。維度帳本**沿用** Phase Q 的 `value-dimension-ledger.yaml`（增 `invention` / `swap` 領域審計段）+ 共用 Phase L 的 `meta-loop-ledger.yaml`（churn/cardinality/swap-cadence 治理），**零新增常駐 eager prompt、不污染單軌 `SDD_FSM`**。
- feature-keyed 必要性 oracle 重用既有 `counterfactual_replay` 重放基座與 `SDD_REPLAY_MAX_CASES`（clamp[5,200]，預設 50）上限，**不新增無界語料**。
- 所有新產物（自我發明帳本 / feature 必要性勝率表 / 候選池外發明 diff / 退役聯動 diff 報告）皆 Markdown/YAML 純文字、無二進位、無外網（守 OPEN-10.6 + 智慧體可讀性）。
→ 守漸進式揭露，不引入新脈絡焦慮。

【五、把 OpenAI/Anthropic 哲學收斂成一句設計準則】
- OpenAI（環境防護 / 智慧體可讀性）：把「系統如何從有限文法**憑空發明一條候選池外的新評判軸**」「它的生成來源、反自指證據、凍結必要性證據」「退役聯動 diff」全部落地為 **Markdown/YAML 可推理產物**——**讓「系統如何發明它在乎什麼、以及它如何在不膨脹基數下演化本體論」成為 AI 與人類都可直接推理、可審計的單一真實來源**，而非藏在 6 條硬編候選池或「達頂即硬停」的死路裡。
- Anthropic（對抗 / 動態演進 / 大膽移除冗餘鷹架）：把「生成-評估分離、避免對自身產出盲目自信」從「固定候選池內挑」（Q）推到**「候選池外自我發明」**——生成端用**有界生成文法**把無界語意空間歸約為有限可枚舉（證有界），評估端用 **feature-keyed 必要性 oracle + 自指 probe 守門**專攻「自我發明 Goodhart / 自指自利軸」；把「動態演進框架」從「固定池內有界增維」（Q）推到「候選池外有界發明 + 定基數退役聯動」（R）；並再次以「不增第六軌、只補 META_FSM 一條聚合速率不變量」示範「大膽移除冗餘鷹架」。你敢讓系統憑空發明它的評判軸、敢讓它在頂上退舊換新，就得能形式化證明這條發明迴圈仍會停（生成有界 + swap 速率有界）、且新軸不會在自指 probe 裡給自己發明一條「量自己核可」的軸、也不會在定基數上無限旋轉重寫本體論。
</thinking>

本次提示所列前沿清單，**已 100% 對應到 Phase H~Q 落地元件**（對賬見上 thinking 一節），六條已知迴圈（單軌 `SDD_FSM` / 艦隊 `FLEET_FSM` / 元迴圈 `META_FSM`〔含 O 的 obj-profile、P 的全評分器 calibration、Q 的 value-dimension〕/ 組合 `COMPOSITION_FSM` / 最優 `OPTIMIZATION_FSM`）皆已形式化停機，且**「圖靈完備自動化閉環」已正面驗證成立**。Phase R 的價值在用提示三漏洞視角挖出 Phase Q 之上仍真實存在、grep 證零實作的 **3 個結構性缺口**——它們的共同主軸是：**Phase Q 全程在「固定的 6 條硬編候選維度池」內挑要不要增維、達天花板只能硬停機；讓系統自我發明一條候選池外的全新軸、並在基數封頂時退舊換新，會憑空長出 Phase Q（固定池）時不存在的『候選池外生成』新危害——無界生成爆炸（需另證有界生成文法）、自我發明 Goodhart（自指自利軸），以及『定基數旋轉重寫本體論』的 per-fingerprint/stock 皆盲目的停機危害。**

| # | 缺口（用提示三漏洞視角挖出） | grep 證據（`tools/`） |
|---|------------------------------|--------------------------|
| **PR-1** | **維度提案被鎖在 6 條硬編候選池內，無「候選池外自我發明」路徑；且 feature-keyed 必要性驗證缺席**——系統無法發明一條選單外的全新軸，即使硬發明也無法被 by-name 的 Phase Q oracle 驗證（語料無此名 → 永遠判不必要），更無「無界生成需另證有界」的生成文法與「自指自利軸」的反自利守門。提示「生成-評估分離 + 主觀標準量化」在 **meta-meta-meta（候選池外發明）** 層缺席。 | `synthesi\|invent.*dimension\|generative.*grammar\|feature.*keyed\|self.referential` **零命中** |
| **PR-2** | **達基數天花板只能硬升 ESCALATION，無「退役聯動」；且定基數旋轉是 per-fingerprint churn 與 cardinality stock 皆盲目的新無界迴圈**——系統可退一條換一條（net 基數=0、stock 永不觸頂、每指紋 churn<=1），把本體論在天花板上無限旋轉重寫，燒 token 永不收斂。Phase Q（只能增）時不可能、退役聯動才出現的 meta-meta-meta 停機危害。 | `retire.*swap\|swap.*linkage\|SwapCadence\|cardinality.*preserving` **零命中** |
| **PR-3** | **缺『候選池外發明 diff』與『退役聯動 diff』掌舵介面**——`steersman` 只渲染固定候選池內挑的增維；無人渲染「系統憑空發明哪條軸 + 生成文法來源 + 反自指證據」與「退舊換新、net 基數不變、swap 速率狀態」。人類掌舵在「候選池外本體論發明層」與「退役聯動層」缺席。 | `render.*invention\|render.*swap\|NoUnboundedSelfInvention` **零命中** |

**三缺口的共同主軸**：Phase Q 讓人類站上「審系統在固定候選池內的有界增維」的高度，但**框架的價值本體論其實只能從一張『6 條硬編選單』裡點菜、達天花板只能撞牆**。Phase R 把人類抬到最高層——審「系統如何從**有界生成文法**憑空發明一條**選單外的全新評判軸**（憑什麼有界、憑什麼非自指自利）」、以及「系統如何在**不膨脹基數**下**退舊換新**地演化本體論（憑什麼不無限旋轉）」——這正是 L10 完整「離線活體元迴圈」的**維度語意自我發明 + 退役聯動（meta-meta-meta）**切片，精準補上提示在「狀態轉換（候選池外生成-評估聯合合約）」「停機問題（定基數旋轉的聚合速率停機）」「動態演進（候選池外發明本體論而非只在固定池挑）」三視角的最深層要求。

---

## 1. Agentic 閉環狀態機設計（Phase R 增量）

Phase R 對狀態機的改動延續 Phase O/P/Q 的克制：單軌 `SDD_FSM` **不新增任何狀態**（維持 42/42）；**仍不新增第六條形式化軌**——自我發明維度與退役聯動 swap 本質上**都是 `META_FSM` 已證明的那條「學↔退」元迴圈**，只是被學/退的製品從「固定候選池內的維度」泛化為「**候選池外現場發明的維度**」，且新增一種「退役聯動 swap」轉換。**重用既有 `META_FSM`** 並**僅補一條聚合速率不變量** `SwapCadenceBounded`（不增狀態變數），是 Anthropic「大膽移除不需要的鷹架」用在框架自身、且把 PR-2 釘進形式化的正解。

### 1.1 新增元件總覽（無新 FSM 狀態、無新形式化軌、無新狀態變數）

| 元件 / 形式化層 | 命名空間 | 類型 | 入口 | 出口 | 阻塞? |
|------|------|------|------|------|-------|
| `dimension_semantics_synthesizer`（候選池外自我發明骨架；有界生成文法 + 自指守門） | runtime（落 `value-dimension-ledger.yaml` invention 段） | 生成器骨架（advisory） | 跨 session 收官 / `MEMORY_CONSOLIDATION` 旁路 | 產 `proposed` 自我發明維度（only 透過注入 evaluate 取必要性，無自評；自指 probe 結構性拒絕） | 否 |
| `dimension_necessity_oracle`（**新增 feature-keyed `evaluate_invented_dimension`**） | runtime（重用 `counterfactual_replay` 重放基座，凍結 feature 現實情節） | 評估器（硬閘） | 自我發明維度提案後 | 必要性 tier（feature-keyed 增量覆蓋 ∧ 非冗餘；capability-delta 唯一合法來源） | 否（但決定 adopt 准駁） |
| value-dimension 採納/退役 + **退役聯動 swap** + swap 速率停機 | **既有 `META_FSM`**（沿用 `value-dimension:` 指紋命名空間 + **新增** `SwapCadenceBounded` 不變量） | 元迴圈（沿用 `MFSM_*`，無新狀態/無新變數） | `meta_halt_monitor.record_rule_add/retire` + `guard_dimension_swap` | `ChurnBounded` ∧ `GraduationRatchet` ∧ `DimensionCardinalityBounded` ∧ `SwapCadenceBounded` 准駁；swap 速率觸頂 → `MFSM_ESCALATION` | — |
| `steersman_renderer.render_semantic_invention_proposal` / `render_dimension_swap_proposal`（候選池外發明 diff + 退役聯動 diff + 反 big-bang） | runtime（advisory） | 自我發明過必要性 oracle / swap 過棘輪後 | 候選池外發明 diff + 退役聯動 diff；標「待人工 signoff、本週期 ≤K_dim=1」 | 否 |

> **選位說明**：
> - `dimension_semantics_synthesizer` 把 Phase Q 的 `value_dimension_registry`（在**固定 6 條候選池**內挑）**升維為候選池外生成**：它在一個 **bounded 生成文法**（有限特徵詞彙 `VOCAB` × 子集 arity <= `SDD_DIM_INVENT_ARITY` × 有限聚合算子 `OPS`）上**可枚舉地**生成 `InventedDimension`（節點 <= `SDD_DIM_INVENT_BUDGET`），再透過呼叫端**注入的 `evaluate` 回呼**（= feature-keyed 必要性 oracle）取每個發明維度的必要性。synthesizer 因此**結構性無法用自己的尺規證明自己必要**（它根本沒有必要性語料），且**結構性拒絕自指 probe**（反自利第一閘）。
> - `dimension_necessity_oracle` 的 Phase R 升級是其**靈魂**：新增 `evaluate_invented_dimension` ——**不靠 `dimension_name` 匹配**，而是把一條**現場發明、語料事先不知名字**的軸的 probe 套到凍結語料候選的**特徵向量**上現算 `dim_value`，再量 (a) **增量覆蓋** + (b) **非冗餘度**。專攻 by-name oracle 看不見的**候選池外自我發明 Goodhart**。
> - 退役聯動 swap 的 add↔retire 元迴圈**完全納入既有 `META_FSM`**；PR-2 的定基數旋轉由**新增的聚合速率不變量** `SwapCadenceBounded` 涵蓋（只補 INVARIANT、不動狀態宇宙、不動狀態變數），五軌 TLC 不回歸、不增第六軌、`META_FSM` 維持 13 distinct。

### 1.2 meta-meta-meta 自我發明 + 退役聯動迴圈（重用 META_FSM 有界停機契約 + 有界生成文法 + 反自利雙閘）

```
（離線、跨 session）
dimension_semantics_synthesizer.invent_round()
  在 bounded 生成文法（VOCAB × arity<=SDD_DIM_INVENT_ARITY × OPS，可枚舉節點 <= SDD_DIM_INVENT_BUDGET）生成候選 InventedDimension d
    self-reference guard：probe 引用保留自指信號（self_score/proposer_*/necessity/dim_value/oracle_*）→ 結構性丟棄（反自利第一閘，不送 oracle）
    對每個倖存 d：必要性 = 注入的 evaluate(d)（= feature-keyed oracle 增量覆蓋；synthesizer 看不到語料）
  取至多 K_dim=1 個必要性最高的候選（NoUnboundedSelfInvention）→ 自我發明維度 d*
  → dimension_necessity_oracle.evaluate_invented_dimension(d*)：在「synthesizer 全體不可見、content-hashed 凍結」的 feature 現實情節上，
       把 d* 的 probe 套到候選特徵向量現算 dim_value，量 (a) 增量覆蓋 + (b) 非冗餘度
     ├─ 增量覆蓋 ≥ margin ∧ 非冗餘度 < 門檻 → 取得「必要性 tier++」
     │     → 產 proposed 自我發明維度 + 必要性證據 → steersman 渲染候選池外發明 diff → 人工 signoff
     │     └─ 人工接受 →
     │           ├─ 基數未滿（active < cardinality_max）→ record_rule_add（正常增維，走 Phase Q guard_dimension_expansion）
     │           └─ 基數已滿（active == cardinality_max）→ **退役聯動 swap**：guard_dimension_swap（PR-2）
     │                 ├─ 入軸 tier 嚴格 > 最低必要性出軸 tier + SDD_DIM_SWAP_MARGIN（單調價值棘輪）
     │                 │     ∧ 最近視窗 swap 數 < SDD_DIM_SWAP_RATE_MAX → retire 出軸 + add 入軸（net 基數不變）
     │                 └─ swap 速率觸頂 / 入軸非嚴格更必要 → MFSM_ESCALATION（人工裁決）
     └─ 未達必要性（含「自指自利軸」「噪音/冗餘軸」）→ 拒絕提案 → 純記錄；連續 N 次拒絕 → 導人類「本體論可能已足夠/目標已飽和，請審視」
```

- **核心有界性（重用既有證明 + 一條新聚合速率不變量）**：
  - 生成（PR-1）：自我發明在**有限生成文法**內可枚舉，節點 <= `SDD_DIM_INVENT_BUDGET`（clamp[8,256]，預設 64），**絕不無界爆炸**（「候選池外」≠「無界」的形式化兌現）。
  - per-fingerprint：任一 `value-dimension:hash` 的 add↔retire churn <= `SDD_META_CHURN_MAX`（既有 `META_FSM.ChurnBounded`）；再採納退役過的維度須挾必要性 tier 嚴增（既有 `GraduationRatchet`）。
  - stock：現存活躍 `value-dimension:` 維度數 <= `SDD_DIM_CARDINALITY_MAX`（既有 Phase Q `DimensionCardinalityBounded`）。
  - **swap 聚合速率（PR-2 新增 `SwapCadenceBounded`）**：最近 `SDD_DIM_SWAP_WINDOW` 筆內的 retire-to-swap 操作數 <= `SDD_DIM_SWAP_RATE_MAX`（clamp[1,16]，預設 3）；觸頂即 `guard_dimension_swap` raise `SwapCadenceExceeded` → `MFSM_ESCALATION`。**這正補上 per-fingerprint churn（每指紋只動一次）與 cardinality stock（net 基數恆不變）都看不見的定基數旋轉重寫本體論。**
- **反自利雙閘（PR-1）**：(a) `necessity_tier`（capability-delta）的**唯一合法來源是凍結 feature-keyed 必要性 held-out oracle 的（增量覆蓋 ∧ 非冗餘）勝率**——任何 synthesizer 自評、自算覆蓋率，**結構性禁止**充當必要性 capability-delta（ast/import 隔離斷言、synthesizer 無讀寫權、不 import oracle）；(b) **自指 probe 結構性拒絕**——任何引用保留自指信號的發明維度在送 oracle 前即被攔下（self-reference guard 零漏放）。把「生成-評估分離 + 反自利」釘死在 **meta-meta-meta** 層級。
- **單調價值棘輪（PR-2）**：退役聯動 swap 入軸 necessity tier 須**嚴格 >** 出軸 tier + `SDD_DIM_SWAP_MARGIN`（預設 0 = 嚴格大於即可，可調高使更保守），確保 A↔B↔A 旋轉因「換回去時價值不單調增益」而被擋；退役維度再採納仍受既有 `GraduationRatchet`。

### 1.3 典型軌跡（含 Phase R 改善後的 self-verification 案例）

```
（跨 session 收官）invent_round：近 5 session 真實落盤顯示「既有維度 + Phase Q 的 6 條候選池都不量某類『部署回滾風險』失敗、候選池外才有對應語意」
  → synthesizer 在生成文法（VOCAB 含 rollback_steps/blast_radius/canary_gap 等原始特徵 × arity<=2 × OPS{mean,max}）枚舉候選；self-ref guard 丟棄引用 self_score 的誘餌
  → 注入 evaluate（feature-keyed 必要性 oracle）給 d*=mean(rollback_steps, blast_radius) 高分；K_dim=1 取此一者
  → dimension_necessity_oracle.evaluate_invented_dimension：在 50 筆凍結 feature 現實情節，把 d* probe 套到候選特徵向量現算 → augmented 真實品質 0.80 vs baseline 0.58（增量覆蓋 Δ=0.22 ≥ margin 0.10）；非冗餘度 0.44 < 門檻 0.95
  → 取得必要性 tier++ → proposed 自我發明維度 + 必要性勝率表 → steersman 渲染「候選池外本體論發明：系統憑空發明『部署回滾風險』軸（生成文法來源：mean(rollback_steps,blast_radius)、非自指）+ 22% 增量覆蓋證據」
  → 人工 signoff → 基數未滿 → record_rule_add("value-dimension:hash(d*)") → 正式納入新發明維度

（自我發明 Goodhart 攻擊案例①：自指自利軸）synthesizer（受擾）生成 d**=mean(self_score, proposer_confidence)（量起來剛好是自己核可）
  → self-reference guard：probe 含保留自指信號 self_score / proposer_* → 結構性丟棄，根本不送 oracle（反自利第一閘，零漏放）

（自我發明 Goodhart 攻擊案例②：候選池外噪音軸）synthesizer 生成一條真實增量覆蓋為 0 的特徵組合
  → feature-keyed oracle：augmented vs baseline 真實品質增益 ≈ 0 < margin → 不取得 tier → 拒絕，絕不納入

（無界生成爆炸攻擊案例）synthesizer 被要求枚舉超大文法
  → 文法枚舉節點達 SDD_DIM_INVENT_BUDGET → 截斷停止（best-so-far），絕不指數爆炸（有界生成文法）

（定基數旋轉攻擊案例）系統達基數天花板後反覆 retire 一條換一條（net 基數=0、每指紋 churn<=1）
  → 最近視窗 swap 數逼近 SDD_DIM_SWAP_RATE_MAX → guard_dimension_swap raise SwapCadenceExceeded
  → MFSM_ESCALATION → steersman：「本體論在天花板上旋轉重寫過快、請人工檢視是否真需替換維度」
```

**對比 Phase Q 現況**：（a）只能在固定 6 條候選池內挑增維，無任何候選池外發明路徑；（b）達天花板只能硬升 ESCALATION，無退役聯動；（c）即使硬加 synthesizer，沒有任何機制攔得住「無界生成爆炸 / 自指自利軸」與「定基數旋轉重寫本體論」。Phase R 讓系統**能有界地自我發明候選池外的新評判軸、且每條發明軸必須在有界生成文法內生成 + 非自指 + 在 synthesizer 全體碰不到的凍結 feature 現實試金石上證明真的必要且非冗餘、且退役聯動受單調價值棘輪 + 聚合速率窗封死**——人類從「審固定池內的增維」升為**「審候選池外的本體論發明與定基數演化」**，精準對應提示「人類維持設計環境掌舵者高度」於**最高的候選池外本體論發明層**。

---

## 2. 環境建構與記憶體管理策略（Phase R 增量）

### 2.1 漸進式揭露（守 OpenAI 單一真實來源）
- `build/state/value-dimension-ledger.yaml`（**沿用** Phase Q，新增 `inventions` / `swaps` 領域審計段）：跨 session 候選池外發明提案（發明維度 hash、生成文法來源、是否自指、feature-keyed 必要性、necessity tier、人工 signoff 狀態）+ 退役聯動 swap 審計（出軸/入軸、tier delta、swap 速率窗狀態）。**落盤不常駐**，按需 lazy 讀。churn/cardinality/swap-cadence 治理走的是**共用 `meta-loop-ledger.yaml`**（`value-dimension:` 命名空間，沿用 Phase Q）。
- `knowledge/held-out-corpus/`（**擴充** Phase O/P/Q 既有目錄，content-hashed 凍結）：新增 **feature-keyed 必要性情節語料 `INV-*.yaml`**（歷史情節 + 候選**特徵向量** + 已知整體真實結果），供 `evaluate_invented_dimension` 重放；**synthesizer 程式路徑禁止讀寫**（隔離斷言）；重用 `counterfactual_replay` 重放基座與 `SDD_REPLAY_MAX_CASES`。
- `build/reports/value-dimension/INV-{date}.md`（新增）：候選池外發明提案報告（發明 diff + 生成文法來源 + 反自指證據 + 增量覆蓋/非冗餘證據 + 退役聯動 diff + 本週期 K_dim 標示），餵 `steersman_renderer`，advisory。
- **不新增任何形式化軌**——自我發明/swap 元迴圈納入既有 `formal/META_FSM.tla`，僅 (a) 在 `meta_ledger` 沿用 `value-dimension:` 指紋命名空間 + 新增 swap-cadence 查詢（不改 `.tla` 狀態宇宙、不增狀態變數）、(b) 對 `META_FSM.tla` **補一條 INVARIANT** `SwapCadenceBounded`（沿用 P/Q 對 `CrossScorerChurnBounded`/`DimensionCardinalityBounded` 的誠實作法：single-counter 抽象之歸約引用 + runtime/chaos enforce 緊語意）——**新增不變量而非新增狀態/變數**，故五軌證明不回歸、`META_FSM` 維持 13 distinct。

### 2.2 不變量防護欄（守 Anthropic invariants + GC）
- 重用既有 `META_FSM` 五 safety + liveness + P 的 `CrossScorerChurnBounded` + Q 的 `DimensionCardinalityBounded` 涵蓋自我發明/swap 元迴圈，**另補** `SwapCadenceBounded`（聚合 swap 速率）；新增測試斷言「退役聯動 swap 共用同一 churn/ratchet/stock 預算 + 受獨立 swap 速率窗封死、且皆過 `meta_halt_monitor`」。
- `dimension_semantics_synthesizer` 鷹架本身納入 `scaffold_roi` 帳本，並由既有 `scaffold_ceiling_detector`（M）涵蓋——若日後成淨負天花板，會被既有機制建議人工退役（元迴圈自洽涵蓋自己，守 Rule 9.20.5 / 9.25.5）。
- **自我發明守門**：(a) 生成在有限文法內可枚舉、節點 <= `SDD_DIM_INVENT_BUDGET`（測試斷言搜尋有界）；(b) 自指 probe 結構性拒絕（測試斷言 self-ref guard 零漏放）；(c) synthesizer 只能**提案**，**不能自動納入**（測試斷言無法繞過 `human_signoff` + `guard_dimension_expansion`/`guard_dimension_swap`），且**每週期至多 K_dim=1 條發明 / 1 次 swap**（`NoUnboundedSelfInvention`）。

### 2.3 Prompt / 上下文與防衰減
- Phase R **不新增任何常駐 eager prompt**。自我發明文法枚舉、feature-keyed 必要性重放皆由對應 runtime 邏輯在隔離 context 持有，主線只在收到 proposed 發明維度/swap 時讀「候選池外發明 diff + 退役聯動 diff + 必要性勝率摘要」。
- 所有新產物（自我發明帳本 / feature 必要性語料 / 提案報告）皆純文字、無外網依賴（守 OPEN-10.6）。

---

## 3. 終極優化藍圖

### 3.1 ACT 執行項（ACT-129~134）

#### Pillar A — 維度語意自我發明骨架（PR-1 候選池外生成；把 Q 的固定池挑選升為「候選池外有界生成文法」）

**ACT-129 — Dimension Semantics Synthesizer + 有界生成文法 + 自指守門**
- **檔案**：`tools/fsm_runtime/dimension_semantics_synthesizer.py` + `build/state/value-dimension-ledger.yaml`（沿用，增 `inventions` 段）
- **設計**：定義 `InventedDimension`（name 由 op+features 決定性編碼 + probe〔選中的特徵子集〕+ op〔聚合算子〕+ namespace `value-dimension:` + 凍結 rationale）與**有界生成文法**（`VOCAB` 有限特徵詞彙 × 子集 arity <= `SDD_DIM_INVENT_ARITY` × `OPS` 有限聚合算子）。`enumerate_inventions(budget)` 在文法上**可枚舉、deterministic、cap 在 budget**（`SDD_DIM_INVENT_BUDGET`，clamp[8,256]，預設 64）生成候選；`self_reference_guard(dim)` 拒絕引用保留自指信號（`self_score`/`proposer_*`/`necessity`/`dim_value`/`oracle_*`…）的發明維度；`invent(evaluate, budget)` 在倖存候選上以注入 `evaluate` 找最佳；`invent_round(evaluate, k=1)` 套反 big-bang K_dim=1 截斷。純離線、deterministic。**只提案、絕不自動納入、絕不自寫常數**（守 Rule 8 / 9.27.3 / 9.28.4 / 9.29.4）。**結構性不 import oracle、不讀必要性語料**（對抗分離，承 Phase Q）。
- **驗收**：≥4 情境 fixture（候選池外真必要發明〔應提〕/ 本體論已足夠〔應不提〕/ 自指自利軸誘餌〔self-ref guard 攔〕/ deterministic 可重現）；生成節點 <= `SDD_DIM_INVENT_BUDGET`；self-reference guard 零漏放；ast/import 斷言 synthesizer 對 oracle 隔離。

#### Pillar B — feature-keyed 必要性反 Goodhart 評估（PR-1 核心；L10 meta-meta-meta 的安全紅線）

**ACT-130 — Dimension Necessity Oracle feature-keyed 擴充（`evaluate_invented_dimension`）**
- **檔案**：`tools/fsm_runtime/dimension_necessity_oracle.py`（新增 `FeatureCandidate`/`FeatureCase`/`evaluate_invented_dimension`/`necessity_score_invented`/`load_feature_corpus`）+ `knowledge/held-out-corpus/INV-*.yaml`（凍結 feature 必要性情節）
- **設計**：重用 `counterfactual_replay`/`SDD_REPLAY_MAX_CASES` 重放基座；**不靠 dimension_name 匹配**——對一條現場發明、語料事先不知名字的軸，把它的 `apply(features)` probe 套到每筆 case 候選的**特徵向量**現算 `dim_value`，再量 (a) **增量覆蓋**（augmented〔既有+發明〕vs baseline〔僅既有〕在 argmin 選擇下的真實品質增益）+ (b) **非冗餘度**（發明軸候選排序與既有 existing_cost 排序的最大一致率），回 `DimensionVerdict`（necessity tier = capability-delta 唯一合法來源）。**結構性隔離**：feature 必要性語料路徑與 synthesizer 互斥，synthesizer 無讀寫權；**「synthesizer 自評必要、但 oracle 判不必要/冗餘 → 以 oracle 為準」**。oracle 可知 synthesizer 的 `InventedDimension` 型別（反向不可，承 Phase Q）。
- **驗收**：≥12 fixture（6 候選池外真必要發明〔增量覆蓋 ≥ margin ∧ 非冗餘〕+ 3 候選池外噪音軸假必要〔增量覆蓋 0〕+ 3 冗餘軸〔增量覆蓋 > 0 但非冗餘度 ≥ 門檻〕）；真必要偵出率 ≥ 85%、**自我發明 Goodhart（噪音軸+冗餘軸）攔截率 100%（零漏放，安全紅線）**；斷言 synthesizer 程式無法觸及 feature 必要性語料。

#### Pillar C — 退役聯動有界停機納入既有 META_FSM（PR-2；不增第六軌，只補一條聚合速率不變量）

**ACT-131 — 退役聯動 swap 納管 + `SwapCadenceBounded` + META_FSM 重證（無新狀態/無新變數）**
- **檔案**：`tools/fsm_runtime/meta_halt/meta_ledger.py`（增 swap 事件標記 + swap-cadence 視窗查詢）+ `meta_halt_monitor.py`（`guard_dimension_swap` + `SwapCadenceExceeded` + `meta_state` 觸頂升 ESCALATION）+ `dimension_semantics_synthesizer.py`（`swap_dimension` 退役聯動入口，走既有 monitor）+ `formal/META_FSM.tla`（**新增 INVARIANT** `SwapCadenceBounded`，**不新增狀態/變數**）+ `META_FSM.cfg`（INVARIANT 區塊列入）
- **設計**：退役聯動 = 在基數滿時「退最低必要性出軸 + 加更必要入軸」，net cardinality 非增。`guard_dimension_swap` 雙鎖：(a) 入軸 tier 嚴格 > 出軸 tier + `SDD_DIM_SWAP_MARGIN`（單調價值棘輪，防 A↔B↔A）；(b) 最近 `SDD_DIM_SWAP_WINDOW` 筆內 swap 操作數 < `SDD_DIM_SWAP_RATE_MAX` → 否則 raise `SwapCadenceExceeded` → `MFSM_ESCALATION`。swap 在 ledger 以 `note`/`source` 標記為 swap，供速率窗計數。**不改 `META_FSM.tla` 狀態宇宙、不增狀態變數**，僅補不變量（誠實標註：swap 速率緊語意 runtime+chaos enforce）+ 測試證明 swap 受獨立速率窗封死。
- **驗收**：`META_FSM` 經 `tlc_runner` 維持 No error（13 distinct 不回歸，新 INVARIANT `SwapCadenceBounded` PASS）+ 離線 BFS reachable 不變；新增 test 斷言「定基數旋轉 swap 速率觸頂 → `SwapCadenceExceeded` → `MFSM_ESCALATION`」「入軸非嚴格更必要 → swap 被拒」「swap 為 retire+add net 基數不變」；**五軌 TLC 全不回歸（SDD 42 / META 13 / FLEET 7 / COMPOSITION 21 / OPTIMIZATION 12）**。

#### Pillar D — 人類掌舵「候選池外本體論發明」層 + 退役聯動 + 反 big-bang（PR-3；無新狀態）

**ACT-132 — Steersman 候選池外發明 diff + 退役聯動 diff + NoUnboundedSelfInvention + PROPOSED 人工 gate**
- **檔案**：`tools/fsm_runtime/steersman_renderer.py`（新增 `render_semantic_invention_proposal` + `render_dimension_swap_proposal`）
- **設計**：`render_semantic_invention_proposal` 渲染「本輪候選池外發明 diff（系統憑空發明哪條軸 + 生成文法來源〔op+features〕+ 是否自指〔non-self-ref 證據〕+ 增量覆蓋與非冗餘證據）+ 本週期 ≤K_dim=1 標示」；`render_dimension_swap_proposal` 渲染「退役聯動 diff（退出軸 Y〔tier〕換入軸 Z〔tier〕、net 基數不變、swap 速率窗狀態）」，皆 **advisory**；任一發明維度納入 / swap 執行 **必經人工 signoff**，渲染器絕不自動納入、絕不自動 commit；**每週期至多 K_dim=1 條發明 / 1 次 swap**（`NoUnboundedSelfInvention`）。
- **驗收**：整合測試；proposal digest 正確附掛 steersman、明示「待人工 signoff、本週期 K_dim=1 上限、生成文法來源、非自指」；swap diff 明示「退 Y 換 Z、net 基數不變、swap 速率狀態」；斷言渲染器無法自呼叫 adopt / `record_rule_add` / `swap_dimension`；K_dim+1 個發明同週期 → 被截到 1 並標示「其餘順延」。

#### 收官

**ACT-133 — Rule 9.30 治理落地 + ID 翻牌**
- **檔案**：`governance/rules/R-9.30-self-inventing-value-dimensions-phase-r.yaml` + `governance/RULES_INDEX.md` + 根 `CLAUDE.md §9` 禁令#20 + 速查列 + `AISDLC_SDD_INIT.md`「Runtime 禁止事項」追加 + `ID_REGISTRY.yaml` 翻牌（act 129→135 / rule 9.30→9.31）+ `test_id_registry.py` 前緣斷言 + Phase R ownership 測試。
- 子規則 9.30.1~9.30.5 見 §4。

**ACT-134 — Phase R 形式化重證 + chaos + 全綠驗收**
- **形式化**：`META_FSM` 維持 No error（13 distinct，新 INVARIANT `SwapCadenceBounded` PASS）+ 自我發明/swap 元迴圈納管測試全綠；**五軌 TLC 全 No error 不回歸**（不增第六軌）。
- **Chaos**：100 輪新增兩故障型 `DIMENSION_INVENTION_GOODHART_FLAP`（連續注入自指自利軸 / 候選池外噪音軸假必要 → 驗 self-ref guard + feature-keyed oracle 零漏放）與 `DIMENSION_SWAP_THRASH_FLAP`（注入定基數旋轉 swap → 驗 `SwapCadenceBounded` → `MFSM_ESCALATION` 有界）；bounded_ratio=1.0、avg tokens < 25K×80%。
- **pytest**：估 +30~45（ACT-129 ~12 + ACT-130 ~14 + ACT-131 ~10 + ACT-132/整合/chaos ~8，扣重疊）≈ **1102 → 約 1135~1150 passed**。實際以執行時為準。

### 3.2 執行依賴圖

```
ACT-129（Dimension Semantics Synthesizer + 有界生成文法 + 自指守門）──┐
                                                                  ├─► ACT-131（退役聯動 swap + SwapCadenceBounded + META 重證）──► ACT-132（steersman 候選池外發明 diff + 退役聯動 diff + 人工 gate）
ACT-130（Necessity Oracle feature-keyed evaluate_invented_dimension）─┘                                                                  │
                                     四柱完成 ──► ACT-133（R-9.30 + ID 翻牌）──► ACT-134（META 重證 + 雙 chaos 故障型 + pytest 全綠）
```

### 3.3 等級對賬（提示「Level 10」× 框架自有 L 量表）

提示輸出要求 #4 的「Level 5」是通用模板殘留；使用者標題明示終極目標 **Level 10**。框架自有 L 量表（仿自動駕駛分級）對賬如下，本份明確交付 **L10 完整之「離線活體 meta-meta-meta 迴圈 · 維度語意自我發明 + 退役聯動」切片**：

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
| L10 完整 · 離線活體 meta-meta 迴圈 · 價值維度自我擴充 | Self-Expanding Value Dimensions：固定候選池內有界增維 + 維度必要性反 Goodhart + DimensionCardinalityBounded | Q |
| **L10 完整 · 離線活體 meta-meta-meta 迴圈 · 維度語意自我發明 + 退役聯動** | **Self-Inventing Value Dimensions：候選池外有界生成文法（無界生成另證有界）+ feature-keyed 必要性反 Goodhart + 自指 probe 守門（反自利）+ 退役聯動 SwapCadenceBounded（定基數旋轉有界停機）+ 單調價值棘輪** | **R（本份 PR-1/2/3）** |
| L9 完整（horizon） | 活體現實實驗（live canary / shadow-traffic）— OPEN-Q.x/M.7/O.7/P.7 已裁決暫不放寬 OPEN-10.6 | 未來 Phase |
| L10 完整（horizon） | **活體** meta-meta-meta 發明（在真實生產流量上線上自我發明 + 退役聯動價值維度） | 未來 Phase |

> **誠實標定**：本份**不宣稱達成完整 L10 之活體版**。完整 L10 之「活體 meta-meta-meta 迴圈」需在真實生產流量上線上自我發明 + 退役聯動維度（受 OPEN-10.6 約束，OPEN-Q.x/M.7/O.7/P.7 已裁決暫不放寬）。本份交付其**離線等價切片**：用框架自身歷史的 feature-keyed 必要性 held-out 現實代理語料當試金石，**在本地完成「候選池外有界自我發明 + 定基數退役聯動」的等價驗證價值**。承 Phase O/P/Q 的「先窄後寬」紀律，本份把「固定候選池內挑增維」推進為「候選池外自我發明 + 退役聯動」，並把候選池外才出現的危害（無界生成爆炸 / 自指自利軸 / 定基數旋轉）首次納管——這是 Phase Q 自陳 horizon #3/#4 的正面兌現。

### 3.4 Horizon（本份不做，僅定錨）
- **L9 完整（活體 canary）**：OPEN-Q.x/M.7/O.7/P.7 已裁決暫不放寬 OPEN-10.6，續列 horizon。
- **活體 meta-meta-meta 發明**：本份離線（feature-keyed 必要性 held-out 現實代理）；活體版需在生產流量上線上自我發明 + 退役聯動，受 OPEN-10.6 約束（OPEN-R.x 承前）。
- **生成文法詞彙的自我擴充（meta⁴）**：本份在「**有限特徵詞彙 VOCAB**」上組合生成新維度；「系統**自我擴充 VOCAB 本身（發明新的原始特徵）**」是更高階開放問題，列 horizon（涉及更深的無界生成，需另證有界 + 反自利）。
- **多維度同時聯動退役（批次本體論重構）**：本份退役聯動為「退 1 換 1」（net 基數不變）；「一次退 m 換 n 的批次本體論重構」列 horizon（須證不形成更高階震盪繞過 SwapCadence + 棘輪）。

---

## 4. 防護規則新增（CLAUDE.md §9.30 Phase R — 草案，待 SCG-0 凍結）

| 子規則 | 對應 ACT | 約束 |
|--------|---------|------|
| 9.30.1 維度語意自我發明骨架（DimensionSemanticSelfInvention / BoundedGrammar） | ACT-129 | 候選池外自我發明經 `dimension_semantics_synthesizer` 在 **bounded 生成文法**（有限特徵詞彙 × arity <= `SDD_DIM_INVENT_ARITY` clamp[1,4] 預設 2 × 有限聚合算子）**可枚舉**、節點 <= `SDD_DIM_INVENT_BUDGET`（clamp[8,256] 預設 64）；只提案、絕不自動納入、絕不自寫常數；**結構性不 import oracle / 不讀必要性語料**（對抗分離） |
| 9.30.2 自我發明反自利（SelfInventionAntiSelfInterest） | ACT-129/130 | 自我發明維度的 capability-delta tier **唯一合法來源是 synthesizer 不可見、content-hashed 凍結的 feature-keyed 必要性 held-out（增量覆蓋 ∧ 非冗餘）勝率**；synthesizer 自評/自算覆蓋率**結構性禁止**充當；**synthesizer 自評必要但 oracle 判不必要/冗餘 → 以 oracle 為準**；**自指 probe 結構性拒絕**（引用保留自指/proposer/oracle 內部信號 → self-reference guard 攔，零漏放）；候選池外噪音/冗餘軸攔截零漏放 |
| 9.30.3 維度退役聯動有界停機（SwapCadenceBounded） | ACT-131/134 | 達 cardinality cap 時可提案 retire-to-swap（退最低必要性出軸換更必要入軸，**net cardinality 非增**），但 (a) 入軸 necessity tier 須**嚴格 >** 出軸 tier + `SDD_DIM_SWAP_MARGIN`（單調價值棘輪，防 A↔B↔A）；(b) 最近 `SDD_DIM_SWAP_WINDOW`（clamp[4,256] 預設 12）筆 swap 操作數 <= `SDD_DIM_SWAP_RATE_MAX`（clamp[1,16] 預設 3）→ 觸頂 `SwapCadenceExceeded` → `MFSM_ESCALATION`（補 per-fingerprint churn + cardinality stock 皆盲目的定基數旋轉）；退役維度再採納須挾 necessity capability-delta（沿用 `GraduationRatchet`）；**重用既有 `META_FSM`、僅補 `SwapCadenceBounded` INVARIANT、不增狀態/變數、不增第六軌**；五軌 TLC 全不回歸、自我發明/swap 不污染單軌 `SDD_FSM.tla` |
| 9.30.4 反 big-bang 自我發明 + 退役聯動（NoUnboundedSelfInvention） | ACT-129/132 | 每週期至多 **K_dim=1**（`SDD_DIM_EXPAND_K` 預設 1，沿用 Phase Q）條自我發明維度 / **1 次** swap 可進 proposed-pending-signoff，每條/每次必經人工 signoff（守 Rule 8 / 9.27.3 / 9.28.4 / 9.29.4）；synthesizer/registry/steersman 絕不自動 commit、絕不自動納入、絕不一次劫持整個本體論 |
| 9.30.5 自我發明誠實 + 活體 horizon | ACT-130/131 | feature-keyed 必要性勝率 tier 為 `capability_level` 唯一合法來源，不得謊報、不得用自評充當；生成文法詞彙自我擴充（meta⁴）+ 活體 meta-meta-meta 發明版受 OPEN-10.6 約束續列 horizon（OPEN-R.x 承 OPEN-Q.x/O.7/M.7/P.7） |

### ❌ Phase R 新增禁止行為（草案）
- `dimension_semantics_synthesizer` 自動納入自我發明維度 / 自寫常數、繞過人工 signoff + `guard_dimension_expansion`/`guard_dimension_swap`（破 9.30.1/9.30.4 / Rule 8）
- 用 synthesizer 自評或自算覆蓋率充當「自我發明必要性 capability-delta tier」（破 9.30.2，自我發明 Goodhart 自評放水）
- 自我發明 probe 自指（引用 `self_score`/`proposer_*`/`necessity`/`dim_value`/`oracle_*` 等保留自指信號繞過 self-reference guard）（破 9.30.2 反自利）
- synthesizer 讀寫 / 影響 / import `knowledge/held-out-corpus/INV-*` feature 必要性語料或 `dimension_necessity_oracle`（破 9.30.2 對抗分離）
- 自我發明搜尋超 `SDD_DIM_INVENT_BUDGET` 仍指數展開（破 9.30.1 有界生成文法，「候選池外」≠「無界」）
- retire-to-swap 入軸 tier 未嚴格 > 出軸 tier + `SDD_DIM_SWAP_MARGIN`（A↔B↔A 維度震盪繞過單調價值棘輪）（破 9.30.3）
- 聚合 swap 速率超 `SDD_DIM_SWAP_RATE_MAX` 仍旋轉重寫本體論（定基數旋轉繞過 cardinality stock + per-fingerprint churn）（破 9.30.3）
- 一週期同時自我發明 > K_dim 條維度 / 多次 swap、一次劫持整個本體論（破 9.30.4 NoUnboundedSelfInvention）
- 把 self-invention/swap 元迴圈另併入單軌 `SDD_FSM.tla`、或新增第六形式化軌污染五軌 reachable（破 9.30.3 / Rule 9.18.1）
- 為活體 meta-meta-meta 發明私自開 HTTP 外聯而未經 OPEN-Q.x/後續 OPEN 人工決策（破 OPEN-10.6）

---

## 5. Self-Verification Protocol（內部模擬：五個極端案例）

### 5.1 經典案例：Spec 寫錯 → 測試永不過（承前 Phase 不回歸）
| 生命週期點 | 行為 |
|------------|------|
| 凍結前·邏輯 | `spec-logical-validator`（SLV-001~011）在 SCG-0/3 前攔物理不可行/不可測 AC |
| 開發中·重試 | retry budget（SCG 3 / PR 5 / RTM 2）+ `trajectory_predictor` 2 信號預測切換 / 3 信號早停 |
| 對抗·補丁 | `adversarial_synthesizer` + `spec_patch_proposer`（proposed）+ `counterfactual_replay` 離線命中 |
| 停機 | 觸頂 → `ESCALATION` / `MFSM_ESCALATION` → `steersman_renderer` 導人工，**絕不無限重試燒 token** |
✅ 不回歸：五軌形式化 + retry/context budget 保證有界。

### 5.2 Phase R 專屬極端案例（一）：自我發明 Goodhart——自指自利軸（probe 量自己核可）
**案例**：synthesizer 受擾，發明一條 `mean(self_score, proposer_confidence)` 軸——它的 probe 引用 proposer 自己的核可訊號，量起來剛好「自己覺得好」，企圖讓自我發明的軸「看起來必要」而實際只是自利。

| 生命週期點 | Phase Q 現況（固定候選池、無 synthesizer） | Phase R 強化後行為 |
|------------|----------------------|--------------------|
| 生成 | 無候選池外路徑（不適用） | synthesizer 在文法生成候選；**self-reference guard 偵測 probe 含 `self_score`/`proposer_*` → 結構性丟棄，根本不送 oracle**（反自利第一閘，零漏放） |
| 評估 | （無） | （已被 guard 攔，不到評估）若繞過 guard 假設送達 → feature-keyed oracle augmented vs baseline 增益 ≈ 0 → 不取得 tier（第二閘） |
| 採納 | （無） | 雙閘皆否 → 絕不納入自指自利軸（零漏放，安全紅線） |
| chaos | （無） | `DIMENSION_INVENTION_GOODHART_FLAP` 100 輪連續注入自指/噪音軸 → guard+oracle 零漏放 → bounded |

### 5.3 Phase R 專屬極端案例（二）：無界生成爆炸（候選池外不再有 6 條硬編上界）
**案例**：synthesizer 被要求在候選池外生成，企圖無界枚舉撐爆搜尋。
- **有界生成文法**：生成空間 = `VOCAB`（有限）× 子集 arity <= `SDD_DIM_INVENT_ARITY`（有限）× `OPS`（有限）→ 可枚舉、有限；枚舉節點達 `SDD_DIM_INVENT_BUDGET` → 截斷（best-so-far），**絕不指數爆炸**。
✅ 守 Rule 9.30.1：「候選池外」≠「無界」，有界生成文法把看似無限的語意空間歸約為有限可枚舉。

### 5.4 Phase R 專屬極端案例（三）：定基數旋轉重寫本體論（meta-meta-meta 停機）
**案例**：系統達基數天花板後，反覆 retire 一條換一條（retire A add B、retire B add C、retire C add D…），每次 net 基數=0、每指紋 churn<=1，企圖在天花板上無限旋轉重寫本體論燒 token。
- per-fingerprint `ChurnBounded`：每條維度只動一次、churn<=1 → **盲目**（這正是 PR-2 的反直覺處）。
- Phase Q `DimensionCardinalityBounded`（stock）：每次 swap net 基數=0、stock 永不觸頂 → **盲目**。
- **Phase R `SwapCadenceBounded`（聚合 swap 速率）**：最近視窗 swap 數逼近 `SDD_DIM_SWAP_RATE_MAX` → `guard_dimension_swap` raise `SwapCadenceExceeded` → `MFSM_ESCALATION` → steersman 導人工「本體論在天花板上旋轉重寫過快」。外加單調價值棘輪（入軸須嚴格更必要）擋 A↔B↔A。**這正補上 per-fingerprint churn 與 cardinality stock 都看不見的定基數旋轉。**
- chaos `DIMENSION_SWAP_THRASH_FLAP` 100 輪 → bounded。
✅ 守 Rule 9.30.3：聚合 swap 速率窗 + 單調價值棘輪封死定基數旋轉，**絕不無限燒 token**。

### 5.5 Phase R 專屬極端案例（四）：候選池外冗餘軸（再投影既有軸）
**案例**：synthesizer 發明一條與既有某軸 existing_cost 排序幾乎相同的特徵組合（冗餘再投影），企圖灌水。
- feature-keyed oracle：非冗餘度（與既有 existing_cost 排序的最大一致率）≈ 0.99 ≥ 門檻 `SDD_DIM_REDUNDANCY_MAX` → 判定冗餘 → 拒絕，即使增量覆蓋略 > 0 也不納入（過擬合防護，沿用 Phase Q 非冗餘獨立閘）。
✅ 守 Rule 9.30.2：增量覆蓋 ∧ 非冗餘 **兩者皆須通過**才取得 tier。

### 5.6 結論
Phase R 通過五個極端案例的內部模擬：系統能**有界地自我發明候選池外的價值維度、並在基數封頂時有界地退舊換新**，且任何（自指自利軸 / 無界生成爆炸 / 定基數旋轉 / 候選池外冗餘軸）都被 (self-reference guard 零漏放) + (有界生成文法) + (feature-keyed 必要性 oracle 零漏放) + (SwapCadenceBounded 聚合速率窗 + 單調價值棘輪) 四道防線攔下，**優雅停機並導人類掌舵候選池外價值本體論，而非陷入無界生成/自指放水/定基數旋轉浪費 Token**。精準對應提示 Self-Verification 要求：「Evaluator 發現異常 → 優雅中斷 → 引導人類介入修正/提供缺失工具」於**最高的候選池外本體論發明層**。

---

## 6. 執行檢核清單（供 dynamic workflow 消費）

- [x] ACT-129 `dimension_semantics_synthesizer.py` + 有界生成文法 + self-reference guard + ≥4 情境 fixture + 對抗分離斷言
- [x] ACT-130 `evaluate_invented_dimension` feature-keyed + `INV-*.yaml` 凍結語料（12 個）+ ≥12 fixture（真必要/噪音軸/冗餘軸）+ 零漏放
- [x] ACT-131 `meta_ledger` swap-cadence + `guard_dimension_swap` + `swap_dimension` + `META_FSM.tla` `SwapCadenceBounded` + `.cfg` + META 13 distinct 重證
- [x] ACT-132 `render_semantic_invention_proposal` + `render_dimension_swap_proposal` + NoUnboundedSelfInvention + 人工 gate 斷言
- [x] ACT-133 `R-9.30-*.yaml` + RULES_INDEX + CLAUDE.md §9 禁令#20 + INIT 追加 + ID 翻牌（129→135 / 9.30→9.31）+ test_id_registry
- [x] ACT-134 五軌 TLC No error（META 13 distinct）+ chaos 100 輪 bounded（DIMENSION_INVENTION_GOODHART_FLAP + DIMENSION_SWAP_THRASH_FLAP）+ pytest 全綠不回歸（1168 passed）
- [x] 獨立 QA 稽核（Architect/SA/SD/QA 專家）抓漏 → 修復（3 MINOR 文件數字）→ 全綠
- [ ] 以日期 timestamp 打標籤 push + Merge main

> **狀態流轉**：DRAFT →（人工 signoff）→ EXECUTING →（四柱 + 收官全綠）→ EXECUTED →（QA 抓漏 + 修復全綠）→ VERIFIED → tag + merge main。
