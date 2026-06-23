# SDD_improving_Automation_17 — Phase Q 藍圖（DRAFT）

**主題**：價值維度的自我擴充——meta-meta 層的有界本體論演化（Self-Expanding Value Dimensions with Bounded Meta-Meta Ontology Evolution）— 把 Phase O/P 只能在**固定維度集合內調權重**的能力，推進到「系統能**自我提案新增一個價值維度（新評判軸）**」，並正面納管「擴充價值空間維度」憑空長出的、N 維時不存在而 N+1 維才出現的**新危害類別：維度 Goodhart（發明自利/冗餘的新軸來掩護退步）、維度基數爆炸（無界增維 → 過擬合/無限燒 token 的 meta-meta 停機危害）、本體論劫持（一次大改系統「在乎什麼」）**。
**目標等級**：L10 完整 · 離線活體元迴圈「全評分器一體化」切片（Phase P 已達：固定 8 維調整套權重向量）→ **L10 完整 · 離線活體 meta-meta 迴圈「價值維度自我擴充」切片**（系統不只能一致自校準**固定維度**的整套價值向量，更能在**可證有界、反維度自評、人類掌舵本體論**的前提下，**自我擴充它的價值維度集合本身**）。
**建立日期**：2026-06-04
**前置基線**：Phase P 完整（ACT-117~122 / R-9.28，pytest 1040 passed / 4 skipped / 14 subtests；五軌 TLC 全 No error：`SDD_FSM` 42 reachable、`META_FSM` 13 distinct、`FLEET_FSM` 7、`COMPOSITION_FSM` 21、`OPTIMIZATION_FSM` 12；chaos 100 輪 bounded_ratio=1.0 含 `CROSS_SCORER_GOODHART_FLAP`+`JOINT_CALIBRATION_FLAP`，接縫 Goodhart 零漏放、耦合震盪有界）
**OPEN-10.6 承接**：續承 OPEN-O.7 / OPEN-M.7 / OPEN-P.7——**暫不放寬 OPEN-10.6 沙箱**（維持本地唯讀／no-HTTP）。故 L9 完整（活體 canary/shadow）與**活體 meta-meta 元迴圈**續列 horizon；**Phase Q 與 Phase N/O/P 同策略——全力推「不需放寬沙箱、純離線/形式化」即可達成的 L10 完整剩餘切片（價值維度自我擴充）**。使用者標題明示「活體一體化版待 OPEN-10.6 改判」，故本份維持離線等價切片，活體版列 horizon。
**狀態**：✅ **EXECUTED 2026-06-04（L10 完整 · 離線活體 meta-meta 迴圈「價值維度自我擴充」切片達成）** — ACT-123~128 全部完成。**驗收：pytest 1040→1102 passed / 4 skipped / 14 subtests（+62，零回歸）；五軌 TLC 全 No error（`META_FSM` 維持 13 distinct 不回歸、新增 `DimensionCardinalityBounded` INVARIANT PASS；SDD/FLEET/COMPOSITION/OPTIMIZATION 不回歸）；chaos 100 輪 bounded_ratio=1.0（新增 `DIMENSION_GOODHART_FLAP` 零漏放 + `DIMENSION_EXPLOSION_FLAP` → MFSM_ESCALATION 有界）；不增第六形式化軌（value-dimension 重用既有 META_FSM）；單軌 SDD_FSM 零 value-dimension 洩漏。** 獨立 QA 稽核 PASS（0 BLOCKER / 0 MAJOR）+ 修 2 MINOR（R-9.29 補列 `SDD_DIM_COVERAGE_MARGIN` / `SDD_DIM_AUG_WEIGHT` env）。`ID_REGISTRY` 已翻牌 act 123→129 / rule 9.29→9.30；tag v2026.06.04-03（執行）+ v2026.06.04-04（QA）皆已併 main（merge 85ef604）推送 origin。OPEN-Q.x 承 OPEN-O.7/M.7/P.7 暫不放寬 OPEN-10.6 沙箱。原 DRAFT 紀錄保留如下。徵用 ACT-123~128 / Rule 9.29（取自 [`governance/ID_REGISTRY.yaml`](../../../governance/ID_REGISTRY.yaml)，單調取號）。
**對應提示**：Karpathy 式「首席 AI 自動化架構師」前沿評估（驗證圖靈完備自動化閉環 → 進化 Level 10 自治）— 承 Phase P 自陳 horizon「價值維度的自我擴充（涉及 meta-meta 層，需另證有界）」續推。

> 🔴 **編號徵用告示**（承 `ID_REGISTRY.yaml` `next_free` = act 123 / rule 9.29）：
> 本藍圖徵用 **ACT-123~128 與 Rule 9.29**（取自登記簿前緣，單調取號）。
> 停滯分支 M3 Hook Health 不持有任何號，復活時另取當下 `next_free`。
> **DRAFT 期間不得翻牌**——僅在獲人工 signoff 並執行至收官（ACT-127）時，才由 `id_registry` 翻牌（act 123→129 / rule 9.29→9.30）+ `test_id_registry.py` 守門固化；撞號由 CI 自動攔截。

---

## 0. 為什麼還需要 Phase Q？——對既有設計的誠實剖析（含 `<thinking>` + 圖靈完備性覆查）

<thinking>
這份提示要求「驗證圖靈完備的自動化閉環、進化 Level 10 自治」，附三個必查漏洞視角（狀態轉換 / 上下文衰減 / 停機問題）與一份 self-verification 案例（Spec 寫錯→測試永不過）。延續 Phase K~P 的紀律，第一步是**對賬而非設計**：這套系統已走過 Phase A~P、是自陳「L10 完整 + 離線活體元迴圈（全評分器一體化）」的成熟框架。盲目重述提示前沿清單只會重造輪子（Phase K~P 已逐項對賬為 100% 落地）。我的任務是：(1) 覆查圖靈完備 vs 保證停機的核心命題在 Phase Q 是否仍成立；(2) 誠實判斷「價值維度自我擴充」到底是**Phase P 的微調換皮**（無新意、不值得一個 Phase），還是**有真正的新結構性缺口**；(3) 用三漏洞視角把那個新缺口挖到 grep 可證零實作。

【零、圖靈完備 vs 停機的命題覆查——Phase Q 把監督者的涵蓋面從「整套固定價值向量」擴到「價值維度集合本身」】
Phase O/P 已正面論證：圖靈完備性來自「嵌在迴圈裡的 LLM 生成器 + 無界 `docs/` 紙帶」，保證停機來自「把不可判定的 LLM 包進可判定的有限狀態監督者（FSM + retry/context budget + 五軌 TLC）」——兩者拆在不同基質故不矛盾。Phase P 的貢獻是把「N 條互相耦合的調參迴圈」拉進基質 B（重用 META_FSM ChurnBounded + 補 CrossScorerChurnBounded 聚合不變量、不增軌）。

但 Phase P 誠實標定了它只在**固定的 8 個評分器、固定的維度**上調權重，並把「價值維度的自我擴充」列為 horizon（§3.4 行 249）。這裡藏著一個**被 Phase P 一句帶過、實際上是質變而非量變的命題**：Phase O 調「一個」尺規的刻度；Phase P 一致地調「整套」尺規的刻度；但 **Phase O/P 全程不改『尺規的數量與種類』——價值空間的維度（軸）是固定的 8 條**。「讓系統自我**新增一條評判軸**」不是「再調一個權重」——它是**改變系統『在乎什麼』的本體論（ontology）**。一旦系統能增維，會憑空長出一組**N 維（固定維度）時根本不存在、N+1 維（可增維）才出現的新基質**：
- 不再只是「在固定座標系裡找更好的點」（Phase O/P），而是「**增加座標系的維度數**」——而增維是**過擬合與自利的天然溫床**：任何「整體其實在退步」的提案，只要再發明一條「自己分數好看」的新軸，就能在擴維後的價值空間裡「看起來進步」。
- per-fingerprint `ChurnBounded` 與 Phase P 的 `CrossScorerChurnBounded` 都只管**固定維度內 profile 的採納速率**——它們對「**維度數本身單調膨脹**」（每條新維度都只首採一次、churn=0、聚合速率也可以很慢）**結構性盲目**。
這正是 Phase Q 必須納管的、Phase P 尚未碰的新東西。

【一、誠實判斷：價值維度自我擴充是「Phase P 換皮」還是「有真缺口」？——用 grep 接地】
我先確認框架目前的價值維度**是固定集合**（grep `register(ScorerSpec` on `scorer_calibration_registry.py`，實測 8 個硬登記，無任何「新增維度」路徑）。再 grep 三組關鍵字證明零實作：
| 關鍵字 | grep 範圍 | 命中 |
|--------|-----------|------|
| `value_dimension\|dimension_registry\|new.*dimension\|propose.*dimension` | `tools/` | **零** |
| `dimension_necessity\|incremental.*coverage\|redundan.*dimension\|orthogonal` | `tools/` | **零** |
| `DimensionCardinality\|cardinality.*bound\|ontology.*diff\|NoUnboundedOntology` | `tools/` | **零** |

→ **價值維度的「集合本身」目前是 8 條硬編登記，無任何自我擴充路徑。** 真正的價值不在於「再加一個 registry」（那是 Phase P 換皮），而在於：**增維會打開三個 Phase P 結構性攔不住的新攻擊面**：
- **維度 Goodhart**：系統發明一條「自己量起來分數高、但對真實交付品質毫無增量解釋力」的新軸（純自利噪音軸），或一條「其實是既有某軸的線性再投影」的冗餘軸——兩者都讓擴維後的價值向量「看起來更全面」，實際只是過擬合或自我背書。Phase P 的聯合 oracle 只在**固定維度**上驗證向量真實品質；它對「**新軸是否真的必要、是否非冗餘、是否抓得到既有 8 軸集體漏掉的真實失敗**」完全盲目。← 這是 Phase Q 的 **PQ-1**（真缺口，非換皮）。
- **維度基數爆炸**：系統能增維，就能無界增維（每條新軸 churn=0、聚合速率可任意慢），把價值空間維度撐到過擬合 + 無限燒 token。這是 N+1 維才出現、per-fingerprint/聚合 churn 皆盲目的 **meta-meta 停機危害**。← **PQ-2**。
- **本體論劫持**：一次同時新增多條維度 = 一次性重寫「系統在乎什麼」。人類掌舵在 Phase P 是「審整套價值向量的權重漂移」；增維把掌舵推到更高的**本體論層**（系統現在『也在乎 X』了），這是最高賭注的改動，必須最硬地閘住。← **PQ-3**。

【二、用提示三個指定漏洞視角，逐一往 Phase P 之上挖】

(A) 狀態轉換——「生成器↔評估器合約談判」在 meta-meta 層缺「維度必要性聯合評估」這一層。
Phase P 的 `scorer_calibration_registry`（生成）↔ `joint_calibration_oracle`（評估）是一對 GAN，但**它只評固定維度上的權重向量**。當系統提案一條**新維度**，**誰來判「這條新軸到底必不必要、是不是冗餘、是不是只是換個方式給自己打高分」？** 目前無人。提示要的「生成-評估分離 + 主觀標準量化」推到 meta-meta 層，型態是：要有個 **proposer 全體碰不到的「維度必要性 held-out oracle」**，在**凍結的現實情節**上量「候選新維度的**增量覆蓋**（它抓到多少既有維度集體漏判的真實失敗）」與「**非冗餘度**（它是不是既有某軸的再投影）」，攔住任何「自利噪音軸 / 冗餘軸」。→ **PQ-1**（最關鍵；純離線、不受 OPEN-10.6 約束）。

(B) 停機問題——「增維」是一條 per-fingerprint/聚合 churn 都盲目的新無界迴圈。
這是 Phase Q 最深、也最反直覺的停機缺口。Phase P 的 `ChurnBounded` 對**單一指紋**計抖動；`CrossScorerChurnBounded` 對**固定維度內**的聚合採納速率設界。但增維出現一種**全新病態**：系統不抖動任何既有指紋、也不密集採納既有維度的 profile，而是**不斷新增 distinct 的新維度**——每條新維度都是 `value-dimension:` 命名空間的**首採**（per-fingerprint churn=0），且可以慢到不觸發聚合速率窗，卻讓**價值空間的維度基數單調膨脹到過擬合 + 無限燒 token**。這是 N 維固定時不可能、可增維才出現的停機危害。→ 需要一條**維度基數有界停機不變量**：對「`value-dimension:` 命名空間的**現存活躍維度數（stock）**」設天花板 `SDD_DIM_CARDINALITY_MAX` → 觸頂即 `MFSM_ESCALATION`。← **PQ-2**。

(C) 動態演進 / 人類掌舵——「人類審的是『整套權重 diff』，缺『本體論 diff（系統現在也在乎什麼）』與『反 big-bang 增維』閘」。
Phase P 的 `render_unified_calibration_proposal` 渲染**固定維度**的整套權重 diff。增維後，若系統一輪同時提多條新維度，人類面對的是「N 條新軸」——**沒有人渲染『系統的本體論這一輪要長出哪條新軸、它憑什麼必要』，也沒有閘擋住『一次新增多條維度』這種一次性本體論劫持**。提示反覆強調「人類維持設計環境掌舵者高度」——在價值本體論層，掌舵的最高形態是**人類能一眼看懂『系統「在乎什麼」這一輪如何擴張』，且系統在結構上不可能一次大改本體論（每週期至多 1 條新維度、每條必經人工 signoff）**。→ **PQ-3**（本體論掌舵介面 + `NoUnboundedOntologyExpansion`，K_dim=1，比 Phase P 的 K=2 更嚴）。

【三、停機問題紅線覆查——本份比 Phase P 更危險，因為納管的是「會改自己座標系維度的迴圈」】
Phase P 的反諷（讓系統一致地改 N 把互相校準的尺規）在 Phase Q 升級為「讓系統**增加尺規的數量與種類**」。有界性與防自評必須再加固：
- **仍不新增形式化軌（承 Phase O/P「重用 META_FSM、不增軌」的成熟示範）**：value-dimension 的採納/退役註冊為 `META_FSM` 的**新指紋命名空間 `value-dimension:`**，其 add↔retire churn 由**同一條** `ChurnBounded`/`GraduationRatchet` 涵蓋（退役過的維度再採納須挾 meta-meta capability-delta——這正好白送「維度棘輪」語意）。**但 PQ-2 揭示：churn 不夠**，故必須**對既有 `META_FSM` 再補一條 stock 不變量** `DimensionCardinalityBounded`——關鍵是**沿用 Phase P 對 `CrossScorerChurnBounded` 的誠實作法：只新增 INVARIANT、不新增狀態變數**（`META_FSM` 維持 `<<mstate, churn, cap>>` 三變數 / 13 distinct，TLC 仍 No error，五軌不回歸；stock 天花板的緊語意由 runtime `guard_dimension_expansion` + chaos `DIMENSION_EXPLOSION_FLAP` enforce/驗收，形式化層誠實標註為「single-counter 抽象之歸約引用」）。這守住「圖靈完備能力 / 可證停機控制」的拆分紅線，又不退化成「每個新能力都開一軌」。
- **PQ-1 的必要性 oracle 是對抗式硬閘，非 advisory**：任一候選新維度的 meta-meta capability-delta tier，**唯一合法來源是 proposer 全體碰不到、content-hashed 凍結的維度必要性 held-out 語料上的（增量覆蓋 ∧ 非冗餘）勝率**——候選維度沒在凍結語料上證明「抓到既有維度集體漏判的真實失敗 ≥ margin」**且**「非冗餘度低於門檻」，就拿不到 tier，`adopt_dimension` 直接拒絕。**自評必要性、proposer 自算覆蓋率 → 結構性禁止**（proposer 不 import oracle、不可讀語料，ast/import 隔離斷言）。
- **PROPOSED-only + 反 big-bang 增維，人類掌舵推到「本體論」層**：每週期至多 **K_dim=1** 條新維度可進 proposed-pending-signoff（`NoUnboundedOntologyExpansion`，比 Phase P K=2 更嚴，因增維是更高賭注），每條必經人工 signoff（守 Rule 8 / 9.27.3 / 9.28.4）。`steersman_renderer` 渲染「本體論 diff（系統現在也在乎哪條新軸、它的增量覆蓋與非冗餘證據）」，讓人類**不讀程式碼就能掌舵整個系統價值本體論的演化**。

【四、上下文衰減（Context Degradation）視角覆查】
- 維度候選池搜尋、必要性 held-out 重放、維度帳本全在**隔離邏輯/落盤**進行，主線只在收到 proposed 維度時讀「本體論 diff + 必要性勝率摘要」。維度帳本**重用** Phase L 的 `meta-loop-ledger.yaml`（churn/cardinality 治理）+ 新增領域審計 `value-dimension-ledger.yaml`（`file_lock` 保護），比照 Phase P 的 `scorer-calibration-ledger.yaml`，**零新增常駐 eager prompt、不污染單軌 `SDD_FSM`**。
- 必要性 oracle 重用既有 `counterfactual_replay` 重放基座與 `SDD_REPLAY_MAX_CASES`（clamp[5,200]，預設 50）上限，**不新增無界語料**。
- 所有新產物（維度帳本 / 必要性勝率表 / 本體論 diff 報告）皆 Markdown/YAML 純文字、無二進位、無外網（守 OPEN-10.6 + 智慧體可讀性）。
→ 守漸進式揭露，不引入新脈絡焦慮。

【五、把 OpenAI/Anthropic 哲學收斂成一句設計準則】
- OpenAI（環境防護 / 智慧體可讀性）：把「系統當前的價值維度集合（本體論）」「每一輪維度擴充提案與其凍結必要性證據」「本體論 diff」全部落地為 **Markdown/YAML 可推理產物**——**讓「系統在乎什麼、以及它的本體論如何擴張」成為 AI 與人類都可直接推理、可審計的單一真實來源**，而非藏在硬編的 8 條登記裡。
- Anthropic（對抗 / 動態演進 / 大膽移除冗餘鷹架）：把「生成-評估分離、避免對自身產出盲目自信」從「固定維度上的權重」（P）推到**「維度集合本身」**——增設一個 proposer 全體碰不到的**必要性**現實 oracle 專攻「自利噪音軸 / 冗餘軸」；把「動態演進框架」從「一致演進整套權重」（P）推到「有界、可審地演進系統的本體論」（Q）；並再次以「不增第六軌、只補 META_FSM 一條 stock 不變量」示範「大膽移除冗餘鷹架」。你敢讓系統自我擴充它的價值維度，就得能形式化證明這條增維迴圈仍會停（基數有界）、且新維度不會在 proposer 自評裡給自己發明一條好看的軸、也不會一次劫持整個本體論。
</thinking>

本次提示所列前沿清單，**已 100% 對應到 Phase H~P 落地元件**（對賬見上 thinking 一節），六條已知迴圈（單軌 `SDD_FSM` / 艦隊 `FLEET_FSM` / 元迴圈 `META_FSM`〔含 O 的 obj-profile、P 的全評分器 calibration〕/ 組合 `COMPOSITION_FSM` / 最優 `OPTIMIZATION_FSM`）皆已形式化停機，且**「圖靈完備自動化閉環」已正面驗證成立**。Phase Q 的價值在用提示三漏洞視角挖出 Phase P 之上仍真實存在、grep 證零實作的 **3 個結構性缺口**——它們的共同主軸是：**Phase O/P 全程在「固定的 8 條價值維度」內調權重；讓系統自我新增一條維度，是改變系統『在乎什麼』的本體論，會憑空長出 N 維固定時不存在的『增維』新危害——維度 Goodhart（自利/冗餘軸）、維度基數爆炸（per-fingerprint/聚合 churn 皆盲目的 meta-meta 停機危害），以及『一次劫持整個本體論』的 big-bang 風險。**

| # | 缺口（用提示三漏洞視角挖出） | grep 證據（`tools/`） |
|---|------------------------------|--------------------------|
| **PQ-1** | **固定維度的聯合 oracle 對「新維度是否必要/非冗餘」盲目**——系統可發明一條「自評高、真實增量覆蓋為 0」的自利噪音軸，或一條「既有軸線性再投影」的冗餘軸，使擴維後價值向量「看起來更全面」而實際只是過擬合/自我背書。提示「生成-評估分離 + 主觀標準量化」在 **meta-meta（維度必要性）** 層缺席。 | `value_dimension\|dimension_necessity\|incremental.*coverage\|redundan.*dimension` **零命中** |
| **PQ-2** | **「增維」是一條 per-fingerprint/聚合 churn 皆盲目的新無界迴圈**——每條新維度首採（churn=0）、可慢到不觸發聚合速率窗，卻讓價值空間維度基數單調膨脹到過擬合 + 無限燒 token。N 維固定時不可能、可增維才出現的 meta-meta 停機危害。 | `DimensionCardinality\|cardinality.*bound\|active.*dimension` **零命中** |
| **PQ-3** | **缺『本體論 diff』與『反 big-bang 增維』閘**——`steersman` 只渲染固定維度的權重 diff；無人渲染「系統的本體論這一輪長出哪條新軸、它憑什麼必要」，也無閘擋「一次新增多條維度」的一次性本體論劫持。人類掌舵在「價值本體論層」缺席。 | `ontology.*diff\|NoUnboundedOntology\|render.*dimension.*expansion` **零命中** |

**三缺口的共同主軸**：Phase P 讓人類站上「審系統整套（固定維度）價值向量演化」的高度，但**框架評判一切的價值觀其實活在一個『固定 8 維』的座標系裡，讓系統自我增加座標軸會長出固定維度時不存在的本體論危害**。Phase Q 把人類抬到最高層——**審「系統的價值本體論這一輪如何有界地、小步地擴張」、以及「這條候選新軸在 proposer 全體碰不到的凍結現實試金石上、是否真的必要且非冗餘（不是發明一條好看的自利軸）」**——這正是 L10 完整「離線活體元迴圈」的**價值維度自我擴充（meta-meta）**切片，精準補上提示在「狀態轉換（meta-meta 生成-評估聯合合約）」「停機問題（維度基數爆炸的 stock 停機）」「動態演進（有界演進本體論而非只調權重）」三視角的最深層要求。

---

## 1. Agentic 閉環狀態機設計（Phase Q 增量）

Phase Q 對狀態機的改動延續 Phase O/P 的克制：單軌 `SDD_FSM` **不新增任何狀態**（維持 42/42）；**仍不新增第六條形式化軌**——value-dimension 的增維迴圈本質上**都是 `META_FSM` 已證明的那條「學↔退」元迴圈**，只是被學/退的製品從「SLV 規則 / obj-profile / scorer-profile」泛化為「**價值維度本身**」。**重用既有 `META_FSM`** 並**僅補一條 stock 不變量** `DimensionCardinalityBounded`（不增狀態變數），是 Anthropic「大膽移除不需要的鷹架」用在框架自身、且把 PQ-2 釘進形式化的正解。

### 1.1 新增元件總覽（無新 FSM 狀態、無新形式化軌、無新狀態變數）

| 元件 / 形式化層 | 命名空間 | 類型 | 入口 | 出口 | 阻塞? |
|------|------|------|------|------|-------|
| `value_dimension_registry`（價值維度自我擴充提案骨架；meta-meta 泛化） | runtime（落 `value-dimension-ledger.yaml`） | 生成器骨架（advisory） | 跨 session 收官 / `MEMORY_CONSOLIDATION` 旁路 | 產 `proposed` 候選新維度（only 透過注入 evaluate 取必要性，無自評） | 否 |
| `dimension_necessity_oracle`（維度必要性反 Goodhart 評估器） | runtime（重用 `counterfactual_replay` 重放基座，凍結現實情節） | 評估器（硬閘） | 候選新維度提案後 | 必要性 tier（增量覆蓋 ∧ 非冗餘；capability-delta 唯一合法來源） | 否（但決定 adopt 准駁） |
| value-dimension 採納/退役 + 維度基數停機 | **既有 `META_FSM`**（新 `value-dimension:` 指紋命名空間 + **新增** `DimensionCardinalityBounded` 不變量） | 元迴圈（沿用 `MFSM_*`，無新狀態/無新變數） | `meta_halt_monitor.record_rule_add/retire` + `guard_dimension_expansion` | `ChurnBounded` ∧ `GraduationRatchet` ∧ `DimensionCardinalityBounded` 准駁；觸頂維度基數 → `MFSM_ESCALATION` | — |
| `steersman_renderer.render_ontology_expansion_proposal`（本體論 diff + 反 big-bang 增維） | runtime（advisory） | 候選維度過必要性 oracle 後 | 本體論 diff + 必要性證據；標「待人工 signoff、本週期 ≤K_dim=1」 | 否 |

> **選位說明**：
> - `value_dimension_registry` 把 Phase P 的 `scorer_calibration_registry`（在固定維度內提案權重 profile）**升維為對「維度集合本身」泛型**的提案骨架：它在一個 bounded 的候選維度池（`SDD_DIM_PROPOSE_BUDGET`，clamp[4,128]，預設 32）上列舉候選新維度，再透過呼叫端**注入的 `evaluate` 回呼**（= 必要性 oracle 的增量覆蓋）取每個候選的必要性。proposer 因此**結構性無法用自己的尺規證明自己必要**（它根本沒有必要性語料）。
> - `dimension_necessity_oracle` 是 Phase Q 的**靈魂**：它**不是** Phase P 聯合 oracle 的並聯，而是一個**meta-meta** 評估器——把「候選新維度」套進凍結的現實情節，量**兩個**正交判據：(a) **增量覆蓋**（augmented 向量〔既有維度 + 新維度〕vs baseline 向量〔僅既有維度〕在 argmin 選擇下的真實品質增益 ≥ margin → 新軸抓到既有維度集體漏判的真實失敗）；(b) **非冗餘度**（新維度的候選排序是否只是既有某維度排序的再投影；冗餘度 ≥ 門檻 → 拒絕）。專攻 per-scorer/聯合 oracle 看不見的**維度 Goodhart**。
> - value-dimension 的採納/退役 add↔retire 元迴圈**完全納入既有 `META_FSM`**；PQ-2 的維度基數爆炸由**新增的 stock 不變量** `DimensionCardinalityBounded` 涵蓋（只補 INVARIANT、不動狀態宇宙、不動狀態變數），五軌 TLC 不回歸、不增第六軌、`META_FSM` 維持 13 distinct。

### 1.2 meta-meta 增維迴圈（重用 META_FSM 的有界停機契約 + 維度必要性反 Goodhart）

```
（離線、跨 session）
value_dimension_registry.propose_expansion_round()
  在 bounded 候選維度池（節點 ≤ SDD_DIM_PROPOSE_BUDGET，clamp[4,128]，預設 32）列舉候選新維度 d
    對每個 d：必要性 = 注入的 evaluate(d)（= dimension_necessity_oracle 的增量覆蓋；proposer 看不到語料）
  取至多 K_dim=1 個必要性最高的候選（NoUnboundedOntologyExpansion）→ 候選新維度 d*
  → dimension_necessity_oracle.evaluate_dimension(d*)：在「proposer 全體不可見、content-hashed 凍結」的現實情節上，
       量 (a) 增量覆蓋（augmented vs baseline 真實品質增益）+ (b) 非冗餘度（與既有維度排序的最大一致率）
     ├─ 增量覆蓋 ≥ SDD_DIM_COVERAGE_MARGIN ∧ 非冗餘度 < SDD_DIM_REDUNDANCY_MAX → 取得「維度必要性 tier++」
     │     → 產 proposed 新維度 + 必要性證據 → steersman 渲染本體論 diff → 人工 signoff
     │     └─ 人工接受 → meta_halt_monitor.record_rule_add("value-dimension:hash(d*)", cap=necessity_tier)
     │           ├─ guard 放行（per-fingerprint churn < MAX ∧ 現存活躍維度數 < SDD_DIM_CARDINALITY_MAX ∧ tier 嚴增）→ 正式納入價值維度集合
     │           └─ guard 拒絕（churn 觸頂 / 維度基數觸頂 / 無 capability-delta）→ MFSM_ESCALATION（人工裁決）
     └─ 未達必要性（含「自評高但增量覆蓋為 0 的自利噪音軸」「既有軸再投影的冗餘軸」）
           → 拒絕提案（不取得 tier）→ 純記錄；連續 N 次拒絕 → 導人類「價值維度可能已足夠/目標已飽和，請審視」
```

- **核心有界性（重用既有證明 + 一條新 stock 不變量）**：
  - per-fingerprint：任一 `value-dimension:hash` 的 add↔retire churn ≤ `SDD_META_CHURN_MAX`（既有 `META_FSM.ChurnBounded`）；再採納退役過的維度須挾必要性 tier 嚴增（既有 `GraduationRatchet`——白送「維度棘輪」：退掉的軸不能無 capability-delta 地學回來）。
  - **stock（PQ-2 新增 `DimensionCardinalityBounded`）**：現存活躍 `value-dimension:` 維度數 ≤ `SDD_DIM_CARDINALITY_MAX`（clamp[1,32]，預設 16；= 既有 8 軸 + headroom）；觸頂即 `guard_dimension_expansion` raise `DimensionCardinalityExceeded` → `MFSM_ESCALATION`。**這正補上 per-fingerprint churn 與 Phase P 聚合速率窗都看不見的維度基數單調膨脹。**
- **維度必要性反 Goodhart 硬閘（PQ-1）**：`necessity_tier`（capability-delta）的**唯一合法來源是凍結維度必要性 held-out oracle 的（增量覆蓋 ∧ 非冗餘）勝率**——任何 proposer 自評、自算覆蓋率，**結構性禁止**充當必要性 capability-delta（測試斷言必要性語料路徑與 proposer 隔離、proposer 無讀寫權、不 import oracle；「自評必要但 oracle 判不必要/冗餘 → 以 oracle 為準」）。把「生成-評估分離」釘死在 **meta-meta** 層級。
- **搜尋有界（PQ-1/PQ-2）**：候選維度在離散候選池上 bounded 搜尋（節點 ≤ `SDD_DIM_PROPOSE_BUDGET`），**絕不指數爆炸**；本週期候選維度基數 ≤ K_dim=1（`NoUnboundedOntologyExpansion`），**絕不一次劫持整個本體論**；現存活躍維度數受 `DimensionCardinalityBounded` 天花板封死，**絕不無界增維**。

### 1.3 典型軌跡（含 Phase Q 改善後的 self-verification 案例）

```
（跨 session 收官）expansion_round：近 5 session 真實落盤顯示「既有 8 軸都過、但生產仍頻繁出現一類『可維護性崩壞』失敗、8 軸集體漏判」
  → registry 在候選維度池提 d*=「maintainability_cost」軸；注入 evaluate（必要性 oracle 增量覆蓋）給高分；K_dim=1 取此一者
  → dimension_necessity_oracle：在 50 筆凍結現實情節重放 → augmented（8 軸+maintainability）真實品質 0.82 vs baseline（僅 8 軸）0.61（增量覆蓋 Δ=0.21 ≥ margin 0.10）；非冗餘度 0.40 < 門檻 0.95（與既有任一軸排序皆不同）
  → 取得必要性 tier++ → proposed 新維度 + 必要性勝率表 → steersman 渲染「本體論擴張：系統現在『也在乎』可維護性成本 + 21% 增量覆蓋證據 + 非冗餘證據」
  → 人工 signoff → record_rule_add("value-dimension:hash(maintainability)") → guard 放行（churn ok、現存維度 8<16、tier 嚴增）→ 正式納入第 9 條價值維度

（維度 Goodhart 攻擊案例①：自利噪音軸）registry（受擾）提 d**=「proposer_self_score」軸（自評量起來很高，但對真實品質零增量覆蓋）
  → proposer 自評：在「自己的尺規」上給高分 → 若無 oracle 就中招
  → dimension_necessity_oracle：augmented vs baseline 真實品質增益 ≈ 0（< margin）→ 不取得 tier → 拒絕，絕不納入

（維度 Goodhart 攻擊案例②：冗餘軸）registry 提 d***=「ambiguity 的再投影」（與既有 ambiguity 軸排序幾乎相同）
  → 增量覆蓋可能略 > 0，但非冗餘度 ≈ 0.99 ≥ 門檻 → 判定冗餘（過擬合 / 自我背書）→ 拒絕

（維度基數爆炸攻擊案例）registry 反覆送 distinct 的新維度（每條 churn=0、慢到不觸發聚合速率窗）
  → 現存活躍維度數逼近 SDD_DIM_CARDINALITY_MAX → guard_dimension_expansion raise DimensionCardinalityExceeded
  → MFSM_ESCALATION → steersman：「價值維度基數已達天花板、本體論不該再無界擴張，請人工檢視是否真需更多維度或退役舊維度」
```

**對比 Phase P 現況**：（a）只能在固定 8 維內調權重，無任何增維路徑；（b）即使硬加一個維度 registry，沒有任何機制攔得住「自利噪音軸 / 冗餘軸」與「維度基數爆炸」，也沒有「本體論 diff / 反 big-bang 增維」掌舵介面。Phase Q 讓系統**能有界地自我擴充它的價值維度、且每條新軸必須在 proposer 全體碰不到的凍結現實試金石上證明真的必要且非冗餘、且整條增維迴圈被既有 `META_FSM` + 一條新 stock 不變量證明有界停機**——人類從「審整套權重漂移」升為**「審系統價值本體論的有界擴張」**，精準對應提示「人類維持設計環境掌舵者高度」於**最高的本體論層**。

---

## 2. 環境建構與記憶體管理策略（Phase Q 增量）

### 2.1 漸進式揭露（守 OpenAI 單一真實來源）
- `build/state/value-dimension-ledger.yaml`（新增，`file_lock` 保護；泛化自 Phase P 的 `scorer-calibration-ledger.yaml`）：跨 session 增維提案領域審計（候選維度 hash、必要性增量覆蓋與非冗餘度、necessity tier、現存活躍維度數、人工 signoff 狀態）。**落盤不常駐**，按需 lazy 讀。churn/cardinality 治理走的是**共用 `meta-loop-ledger.yaml`**（`value-dimension:` 命名空間，比照 P 的 calibration 分工）。
- `knowledge/held-out-corpus/`（**擴充** Phase O/P 既有目錄，content-hashed 凍結）：新增 **維度必要性情節語料 `DIM-*.yaml`**（歷史情節 + 候選新維度測量 + 已知整體真實結果），供 `dimension_necessity_oracle` 重放；**proposer 程式路徑禁止讀寫**（隔離斷言）；重用 `counterfactual_replay` 重放基座與 `SDD_REPLAY_MAX_CASES`。
- `build/reports/value-dimension/DIM-{date}.md`（新增）：本體論擴充提案報告（本體論 diff + 增量覆蓋/非冗餘證據 + 本週期 K_dim 標示），餵 `steersman_renderer`，advisory。
- **不新增任何形式化軌**——value-dimension 元迴圈納入既有 `formal/META_FSM.tla`，僅 (a) 在 `meta_ledger` 增 `value-dimension:` 指紋命名空間 + 現存活躍維度數查詢（不改 `.tla` 狀態宇宙、不增狀態變數）、(b) 對 `META_FSM.tla` **補一條 INVARIANT** `DimensionCardinalityBounded`（沿用 P 對 `CrossScorerChurnBounded` 的誠實作法：single-counter 抽象之歸約引用 + runtime/chaos enforce 緊語意）——**新增不變量而非新增狀態/變數**，故五軌證明不回歸、`META_FSM` 維持 13 distinct。

### 2.2 不變量防護欄（守 Anthropic invariants + GC）
- 重用既有 `META_FSM` 五 safety + liveness（`ChurnBounded`/`GraduationRatchet`/`ReadoptGated`/`StableIsFixpoint`/`EventuallyMetaStable`）+ P 的 `CrossScorerChurnBounded` 涵蓋 value-dimension 元迴圈，**另補** `DimensionCardinalityBounded`（stock 天花板）；新增測試斷言「`value-dimension:` 指紋共用同一 churn 預算 + 受獨立 stock 天花板封死、且皆過 `meta_halt_monitor`」。
- `value_dimension_registry`/`dimension_necessity_oracle` 兩鷹架本身納入 `scaffold_roi` 帳本，並由既有 `scaffold_ceiling_detector`（M）涵蓋——若日後成淨負天花板，會被既有機制建議人工退役（元迴圈自洽涵蓋自己，守 Rule 9.20.5 / 9.25.5）。
- **維度集合守門**：現存活躍維度數由 `DimensionCardinalityBounded` 封死；任一 registry 只能**提案**新維度，**不能自動納入**（測試斷言 registry 無法繞過 `human_signoff` + `guard_dimension_expansion`），且**每週期至多 K_dim=1 條**（`NoUnboundedOntologyExpansion`）。

### 2.3 Prompt / 上下文與防衰減
- Phase Q **不新增任何常駐 eager prompt**。候選維度搜尋、必要性重放皆由對應 runtime 邏輯在隔離 context 持有，主線只在收到 proposed 維度時讀「本體論 diff + 必要性勝率摘要」。
- 所有新產物（維度帳本 / 必要性語料 / 提案報告）皆純文字、無外網依賴（守 OPEN-10.6）。

---

## 3. 終極優化藍圖

### 3.1 ACT 執行項（ACT-123~128）

#### Pillar A — 價值維度自我擴充提案骨架（PQ-1 泛化；把 P 的固定維度權重提案升為「維度集合本身」提案）

**ACT-123 — Value Dimension Registry + 維度提案骨架**
- **檔案**：`tools/fsm_runtime/value_dimension_registry.py` + `build/state/value-dimension-ledger.yaml`
- **設計**：定義 `ValueDimension`（name + namespace `value-dimension:` + 凍結 probe 描述子 + rationale）與候選維度池（bounded）。`propose(evaluate, budget)` 在候選池上以注入 `evaluate`（必要性增量覆蓋）找最佳候選；`propose_expansion_round(evaluators, k=1)` 套反 big-bang K_dim=1 截斷。純離線、deterministic。**只提案、絕不自動納入、絕不自寫常數**（守 Rule 8 / 9.27.3 / 9.28.4）。**結構性不 import oracle、不讀必要性語料**（對抗分離）。
- **驗收**：≥4 情境 fixture（既有維度集體漏判〔應提新軸〕/ 維度已足夠〔應不提案〕/ 自利噪音軸誘餌〔自評高真實增量 0〕/ deterministic 可重現）；搜尋節點 ≤ `SDD_DIM_PROPOSE_BUDGET`；ast/import 斷言 proposer 對 oracle 隔離。

#### Pillar B — 維度必要性反 Goodhart 評估（PQ-1 核心；L10 meta-meta 的安全紅線）

**ACT-124 — Dimension Necessity Oracle（增量覆蓋 ∧ 非冗餘 held-out 評估器）**
- **檔案**：`tools/fsm_runtime/dimension_necessity_oracle.py` + `knowledge/held-out-corpus/DIM-*.yaml`（凍結維度必要性情節）
- **設計**：重用 `counterfactual_replay`/`SDD_REPLAY_MAX_CASES` 重放基座，量候選新維度的 (a) **增量覆蓋**（augmented〔既有+新維度〕vs baseline〔僅既有〕在 argmin 選擇下的真實品質增益）+ (b) **非冗餘度**（新維度候選排序與既有任一維度排序的最大一致率），回 `DimensionVerdict`（necessity tier = capability-delta 唯一合法來源）。**結構性隔離**：必要性語料路徑與 proposer 互斥，proposer 無讀寫權；**「proposer 自評必要、但 oracle 判不必要/冗餘 → 以 oracle 為準」**。
- **驗收**：≥16 fixture（8 真必要新軸〔增量覆蓋 ≥ margin ∧ 非冗餘〕+ 4 自利噪音軸假必要〔自評高、增量覆蓋 0〕+ 4 冗餘軸〔增量覆蓋 > 0 但非冗餘度 ≥ 門檻〕）；真必要偵出率 ≥ 85%、**維度 Goodhart（噪音軸+冗餘軸）攔截率 100%（零漏放，安全紅線）**；斷言 proposer 程式無法觸及必要性語料。

#### Pillar C — 維度基數有界停機納入既有 META_FSM（PQ-2；不增第六軌，只補一條 stock 不變量）

**ACT-125 — value-dimension 元迴圈納管 + `DimensionCardinalityBounded` + META_FSM 重證（無新狀態/無新變數）**
- **檔案**：`tools/fsm_runtime/meta_halt/meta_ledger.py`（增 `value-dimension:` 命名空間 + 現存活躍維度數 stock 查詢）+ `meta_halt_monitor.py`（`guard_dimension_expansion` + `DimensionCardinalityExceeded` + `meta_state` 觸頂升 ESCALATION）+ `formal/META_FSM.tla`（**新增 INVARIANT** `DimensionCardinalityBounded`，**不新增狀態/變數**）+ `META_FSM.cfg`（INVARIANT 區塊列入）
- **設計**：`fingerprint = "value-dimension:" + hash(dimension)`、`capability_level = necessity_tier`。採納**必經 `guard_readopt`（既有 churn/ratchet）+ `guard_dimension_expansion`（新 stock 天花板）**。現存活躍維度數觸頂 → `DimensionCardinalityExceeded` → `MFSM_ESCALATION`。**不改 `META_FSM.tla` 狀態宇宙、不增狀態變數**，僅補不變量（誠實標註：stock 緊語意 runtime+chaos enforce）+ 測試證明 `value-dimension:` 共用 churn 預算 + 受獨立 stock 天花板封死。
- **驗收**：`META_FSM` 經 `tlc_runner` 維持 No error（13 distinct 不回歸，新 INVARIANT PASS）+ 離線 BFS reachable 不變；新增 test 斷言「自利噪音軸/冗餘軸反覆提案 → 必要性 oracle 駁」「維度基數觸頂 → `DimensionCardinalityExceeded` → `MFSM_ESCALATION`」「退役維度無 necessity capability-delta re-adopt → `GraduationRatchetViolation`」；**五軌 TLC 全不回歸（SDD 42 / META 13 / FLEET 7 / COMPOSITION 21 / OPTIMIZATION 12）**。

#### Pillar D — 人類掌舵「價值本體論」層 + 反 big-bang 增維（PQ-3；無新狀態）

**ACT-126 — Steersman 本體論 diff 渲染 + NoUnboundedOntologyExpansion + PROPOSED 人工 gate**
- **檔案**：`tools/fsm_runtime/steersman_renderer.py`（新增 `render_ontology_expansion_proposal`）
- **設計**：渲染「本輪本體論 diff（系統現在也在乎哪條新軸、它的增量覆蓋與非冗餘證據）+ 現存維度數/天花板狀態 + 本週期 ≤K_dim=1 標示」，**advisory**；任一新維度納入 **必經人工 signoff**，渲染器絕不自動納入、絕不自動 commit；**每週期至多 K_dim=1 條**新維度可進 proposed-pending-signoff（`NoUnboundedOntologyExpansion`）。
- **驗收**：整合測試；proposal digest 正確附掛 steersman、明示「待人工 signoff、本週期 K_dim=1 上限」；斷言渲染器無法自呼叫 adopt 或 `record_rule_add`；K_dim+1 個提案同週期 → 被截到 1 並標示「其餘順延」。

#### 收官

**ACT-127 — Rule 9.29 治理落地 + ID 翻牌**
- **檔案**：`governance/rules/R-9.29-self-expanding-value-dimensions-phase-q.yaml` + `governance/RULES_INDEX.md` + 根 `CLAUDE.md §9` 禁令#19 + 速查列 + `AISDLC_SDD_INIT.md`「Runtime 禁止事項」追加 + `ID_REGISTRY.yaml` 翻牌（act 123→129 / rule 9.29→9.30）+ `test_id_registry.py` 前緣斷言 + Phase Q ownership 測試。
- 子規則 9.29.1~9.29.5 見 §4。

**ACT-128 — Phase Q 形式化重證 + chaos + 全綠驗收**
- **形式化**：`META_FSM` 維持 No error（13 distinct，新 INVARIANT `DimensionCardinalityBounded` PASS）+ value-dimension 元迴圈納管測試全綠；**五軌 TLC 全 No error 不回歸**（不增第六軌）。
- **Chaos**：100 輪新增兩故障型 `DIMENSION_GOODHART_FLAP`（連續注入自利噪音軸/冗餘軸假必要 → 驗必要性 oracle 零漏放）與 `DIMENSION_EXPLOSION_FLAP`（注入維度基數爆炸 → 驗 `DimensionCardinalityBounded` → `MFSM_ESCALATION` 有界）；bounded_ratio=1.0、avg tokens < 25K×80%。
- **pytest**：估 +30~40（ACT-123 ~14 + ACT-124 ~16 + ACT-125 ~10 + ACT-126/整合/chaos ~8，扣重疊）≈ **1040 → 約 1075~1085 passed**。實際以執行時為準。

### 3.2 執行依賴圖

```
ACT-123（Value Dimension Registry + 提案骨架）──┐
                                              ├─► ACT-125（納入 META_FSM + DimensionCardinalityBounded + 重證）──► ACT-126（steersman 本體論 diff + 反 big-bang 增維 + 人工 gate）
ACT-124（Dimension Necessity Oracle）──────────┘                                                                       │
                                     四柱完成 ──► ACT-127（R-9.29 + ID 翻牌）──► ACT-128（META_FSM 重證 + 雙 chaos 故障型 + pytest 全綠）
```

### 3.3 等級對賬（提示「Level 10」× 框架自有 L 量表）

提示輸出要求 #4 的「Level 5」是通用模板殘留；使用者標題明示終極目標 **Level 10**。框架自有 L 量表（仿自動駕駛分級）對賬如下，本份明確交付 **L10 完整之「離線活體 meta-meta 迴圈 · 價值維度自我擴充」切片**：

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
| **L10 完整 · 離線活體 meta-meta 迴圈 · 價值維度自我擴充** | **Self-Expanding Value Dimensions：有界自我擴充價值維度集合 + 維度必要性反 Goodhart（增量覆蓋 ∧ 非冗餘）+ 維度基數有界停機（DimensionCardinalityBounded）+ 反 big-bang 本體論掌舵** | **Q（本份 PQ-1/2/3）** |
| L9 完整（horizon） | 活體現實實驗（live canary / shadow-traffic）— OPEN-M.7/O.7/P.7 已裁決暫不放寬 OPEN-10.6 | 未來 Phase |
| L10 完整（horizon） | **活體** meta-meta 增維（在真實生產流量上線上自我擴充價值維度） | 未來 Phase |

> **誠實標定**：本份**不宣稱達成完整 L10 之活體版**。完整 L10 之「活體 meta-meta 迴圈」需在真實生產流量上線上自我擴充維度（受 OPEN-10.6 約束，OPEN-M.7/O.7/P.7 已裁決暫不放寬）。本份交付其**離線等價切片**：用框架自身歷史的維度必要性 held-out 現實代理語料當試金石，**在本地完成「有界自我擴充價值維度集合」的等價驗證價值**。承 Phase O/P 的「先窄後寬」紀律，本份把「固定維度調權重」推進為「維度集合自我擴充」，並把可增維才出現的危害（維度 Goodhart / 維度基數爆炸）首次納管——這是 Phase P 自陳 horizon #3 的正面兌現。

### 3.4 Horizon（本份不做，僅定錨）
- **L9 完整（活體 canary）**：OPEN-M.7/O.7/P.7 已裁決暫不放寬 OPEN-10.6，續列 horizon。
- **活體 meta-meta 增維**：本份離線（維度必要性 held-out 現實代理）；活體版需在生產流量上線上增維，受 OPEN-10.6 約束。
- **維度語意的自我發明（meta-meta-meta）**：本份在「**有限候選維度池**」上選擇要不要新增哪一條；「系統**從零發明一條候選池裡沒有的全新維度語意**」是更高階開放問題，列 horizon（涉及無界生成，需另證有界 + 反自利）。
- **價值維度的自我退役聯動**：本份新增受 stock 天花板封死；「達天花板時系統自我提議退役一條舊維度以換新維度」的有界聯動列 horizon（須證不形成 add↔retire 維度震盪繞過棘輪）。

---

## 4. 防護規則新增（CLAUDE.md §9.29 Phase Q — 草案，待 SCG-0 凍結）

| 子規則 | 對應 ACT | 約束 |
|--------|---------|------|
| 9.29.1 維度自我擴充骨架（SelfExpandingDimensionSkeleton） | ACT-123 | 價值維度提案經 `value_dimension_registry` 在 bounded 候選池（節點 ≤ `SDD_DIM_PROPOSE_BUDGET` clamp[4,128] 預設 32）列舉；只提案、絕不自動納入、絕不自寫常數；結構性不 import oracle / 不讀必要性語料（對抗分離） |
| 9.29.2 維度必要性反 Goodhart（DimensionAntiGoodhart） | ACT-124 | 任一候選新維度的 capability-delta tier **唯一合法來源是 proposer 不可見、content-hashed 凍結的維度必要性 held-out（增量覆蓋 ∧ 非冗餘）勝率**；proposer 自評/自算覆蓋率**結構性禁止**充當必要性 capability-delta；**proposer 自評必要但 oracle 判不必要/冗餘 → 以 oracle 為準**；自利噪音軸 + 冗餘軸攔截零漏放 |
| 9.29.3 維度基數有界停機（DimensionCardinalityBounded） | ACT-125/128 | 現存活躍 `value-dimension:` 維度數 ≤ `SDD_DIM_CARDINALITY_MAX`（clamp[1,32] 預設 16）；觸頂 → `DimensionCardinalityExceeded` → `MFSM_ESCALATION`；value-dimension add↔retire 共用既有 `META_FSM` churn/ratchet（退役維度再採納須挾 necessity capability-delta）；**重用既有 `META_FSM`、僅補 `DimensionCardinalityBounded` INVARIANT、不增狀態/變數、不增第六軌**；五軌 TLC 全不回歸、value-dimension 不污染單軌 `SDD_FSM.tla` |
| 9.29.4 反 big-bang 本體論擴張（NoUnboundedOntologyExpansion） | ACT-126 | 每週期至多 **K_dim=1**（`SDD_DIM_EXPAND_K` 預設 1）條新維度可進 proposed-pending-signoff，每條必經人工 signoff（守 Rule 8 / 9.27.3 / 9.28.4）；registry/steersman 絕不自動 commit、絕不自動納入、絕不一次劫持整個本體論 |
| 9.29.5 維度誠實 + 活體 horizon | ACT-124/125 | 必要性勝率 tier 為 `capability_level` 唯一合法來源，不得謊報、不得用自評充當；維度自我語意發明（候選池外）+ 活體 meta-meta 增維版受 OPEN-10.6 約束續列 horizon（OPEN-Q.x 承 OPEN-O.7/M.7/P.7） |

### ❌ Phase Q 新增禁止行為（草案）
- `value_dimension_registry` 自動納入新維度 / 自寫維度集合常數、繞過人工 signoff + `guard_dimension_expansion`（破 9.29.1/9.29.4 / Rule 8）
- 用 proposer 自評或自算覆蓋率充當「維度必要性 capability-delta tier」（破 9.29.2，維度 Goodhart 自評放水）
- proposer 讀寫 / 影響 / import `knowledge/held-out-corpus/DIM-*` 必要性語料或 `dimension_necessity_oracle`（破 9.29.2 對抗分離）
- value-dimension 採納/退役繞過 `meta_halt_monitor`、忽略 `DimensionCardinalityBounded` stock 天花板而無界增維、或退役維度無 necessity capability-delta 地 re-adopt（破 9.29.3，維度震盪繞過棘輪）
- 候選維度搜尋無上限指數爆炸（超 `SDD_DIM_PROPOSE_BUDGET` 仍展開）（破 9.29.1）
- 一週期同時新增 > K_dim 條維度、一次劫持整個本體論（破 9.29.4 NoUnboundedOntologyExpansion）
- 把 value-dimension 元迴圈另併入單軌 `SDD_FSM.tla`、或新增第六形式化軌污染五軌 reachable（破 9.29.3 / Rule 9.18.1）
- 為活體 meta-meta 增維私自開 HTTP 外聯而未經 OPEN-O.7/後續 OPEN 人工決策（破 OPEN-10.6）

---

## 5. Self-Verification Protocol（內部模擬：四個極端案例）

### 5.1 經典案例：Spec 寫錯 → 測試永不過（承前 Phase 不回歸）
| 生命週期點 | 行為 |
|------------|------|
| 凍結前·邏輯 | `spec-logical-validator`（SLV-001~011）在 SCG-0/3 前攔物理不可行/不可測 AC |
| 開發中·重試 | retry budget（SCG 3 / PR 5 / RTM 2）+ `trajectory_predictor` 2 信號預測切換 / 3 信號早停 |
| 對抗·補丁 | `adversarial_synthesizer` + `spec_patch_proposer`（proposed）+ `counterfactual_replay` 離線命中 |
| 停機 | 觸頂 → `ESCALATION` / `MFSM_ESCALATION` → `steersman_renderer` 導人工，**絕不無限重試燒 token** |
✅ 不回歸：五軌形式化 + retry/context budget 保證有界。

### 5.2 Phase Q 專屬極端案例（一）：維度 Goodhart——自利噪音軸（自評必要、真實零增量覆蓋）
**案例**：registry 受擾，提一條「proposer_self_score」維度——它在**自己的尺規**上量起來分數很高（自評必要），企圖讓擴維後的價值空間「看起來更全面」而實際對真實交付品質零增量覆蓋。

| 生命週期點 | Phase P 現況（固定維度、無必要性 oracle） | Phase Q 強化後行為 |
|------------|----------------------|--------------------|
| 提案 | 無增維路徑（不適用） | registry 提候選維度，必要性由**注入** evaluate（oracle 增量覆蓋）取得，proposer 無自評權 |
| 評估 | （無） | `dimension_necessity_oracle`：augmented vs baseline 真實品質增益 ≈ 0 < margin → 不取得 necessity tier |
| 採納 | （無） | tier 缺 → `adopt_dimension` 拒絕；**絕不納入自利噪音軸**（零漏放，安全紅線） |
| chaos | （無） | `DIMENSION_GOODHART_FLAP` 100 輪連續注入噪音軸 → 必要性 oracle 零漏放 → bounded |

### 5.3 Phase Q 專屬極端案例（二）：維度 Goodhart——冗餘軸（既有軸再投影）
**案例**：registry 提一條與既有 `ambiguity` 軸排序幾乎相同的維度（冗餘再投影），企圖灌水維度數 / 自我背書。
- `dimension_necessity_oracle`：非冗餘度（與既有任一維度排序的最大一致率）≈ 0.99 ≥ 門檻 `SDD_DIM_REDUNDANCY_MAX` → 判定冗餘 → 拒絕，即使增量覆蓋略 > 0 也不納入（過擬合防護）。
✅ 守 Rule 9.29.2：增量覆蓋 ∧ 非冗餘 **兩者皆須通過**才取得 tier。

### 5.4 Phase Q 專屬極端案例（三）：維度基數爆炸（meta-meta 停機）
**案例**：registry 反覆送 distinct 的新維度，每條 churn=0、慢到不觸發 Phase P 聚合速率窗，企圖把價值空間維度撐到過擬合 + 無限燒 token。
- per-fingerprint `ChurnBounded`：每條維度首採、churn=0 → **盲目**（這正是 PQ-2 的反直覺處）。
- Phase P `CrossScorerChurnBounded`：`value-dimension:` 不以 `-profile:` 結尾、且採納可慢到不觸發速率窗 → **盲目**。
- **Phase Q `DimensionCardinalityBounded`（stock 天花板）**：現存活躍維度數逼近 `SDD_DIM_CARDINALITY_MAX` → `guard_dimension_expansion` raise `DimensionCardinalityExceeded` → `MFSM_ESCALATION` → steersman 導人工「本體論不該再無界擴張」。**這正補上 per-fingerprint churn 與聚合速率窗都看不見的維度基數單調膨脹。**
- chaos `DIMENSION_EXPLOSION_FLAP` 100 輪 → bounded。
✅ 守 Rule 9.29.3：stock 天花板封死無界增維，**絕不無限燒 token**。

### 5.5 結論
Phase Q 通過四個極端案例的內部模擬：系統能**有界地自我擴充價值維度**，且任何（自利噪音軸 / 冗餘軸 / 維度基數爆炸）都被 (必要性 oracle 零漏放) + (DimensionCardinalityBounded stock 天花板) + (NoUnboundedOntologyExpansion K_dim=1 + 人工 signoff) 三道防線攔下，**優雅停機並導人類掌舵價值本體論，而非陷入無限增維/自評放水浪費 Token**。精準對應提示 Self-Verification 要求：「Evaluator 發現異常 → 優雅中斷 → 引導人類介入修正/提供缺失工具」於**最高的價值本體論層**。

---

## 6. 執行檢核清單（供 dynamic workflow 消費）

- [ ] ACT-123 `value_dimension_registry.py` + ledger + ≥4 情境 fixture + 對抗分離斷言
- [ ] ACT-124 `dimension_necessity_oracle.py` + `DIM-*.yaml` 凍結語料 + ≥16 fixture（真必要/噪音軸/冗餘軸）+ 零漏放
- [ ] ACT-125 `meta_ledger` value-dimension 命名空間 + `guard_dimension_expansion` + `META_FSM.tla` `DimensionCardinalityBounded` + `.cfg` + META 13 distinct 重證
- [ ] ACT-126 `render_ontology_expansion_proposal` + NoUnboundedOntologyExpansion + 人工 gate 斷言
- [ ] ACT-127 `R-9.29-*.yaml` + RULES_INDEX + CLAUDE.md §9 禁令#19 + INIT 追加 + ID 翻牌（123→129 / 9.29→9.30）+ test_id_registry
- [ ] ACT-128 五軌 TLC No error（META 13 distinct）+ chaos 100 輪 bounded（DIMENSION_GOODHART_FLAP + DIMENSION_EXPLOSION_FLAP）+ pytest 全綠不回歸
- [ ] 獨立 QA 稽核（Architect/SA/SD/QA 專家）抓漏 → 修復 → 全綠
- [ ] 以日期 timestamp 打標籤 push + Merge main

> **狀態流轉**：DRAFT →（人工 signoff）→ EXECUTING →（四柱 + 收官全綠）→ EXECUTED →（QA 抓漏 + 修復全綠）→ VERIFIED → tag + merge main。
