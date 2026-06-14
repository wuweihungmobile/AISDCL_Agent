# SDD_improving_Automation_16 — Phase P 藍圖（DRAFT）

**主題**：全評分器一體化自校準的耦合感知有界元最佳化（Unified All-Scorer Self-Calibration with Coupling-Aware Bounded Meta-Optimization）— 把 Phase O 只示範在**單一** `composition_objective_scorer` 的「tuner + held-out oracle + META_FSM 納管」骨架，**泛化到全部評分器版本面（≥8 個凍結側寫）**，並正面納管「多評分器同時自校準」憑空長出的**新危害類別：跨評分器耦合的元 Goodhart 與耦合式震盪**
**目標等級**：L10 完整 · 離線活體元迴圈切片（Phase O 已達單評分器版）→ **L10 完整 · 離線活體元迴圈「全評分器一體化」切片**（系統不只能自校準「一個」價值權重，更能在**一致、可證有界、跨評分器反自評**的前提下，自校準**整個價值系統向量**）
**建立日期**：2026-06-03
**前置基線**：Phase O 完整（ACT-111~116 / R-9.27，pytest 951 綠 / 7 skipped；五軌 TLC 全 No error：`SDD_FSM` 42 reachable、`META_FSM` 13、`FLEET_FSM` 7、`COMPOSITION_FSM` 21、`OPTIMIZATION_FSM` 12；chaos 100 輪 bounded_ratio=1.0 含 `OBJECTIVE_TUNE_FLAP`，Goodhart 提案零漏放）
**OPEN-O.7 / OPEN-M.7 承接**：✅ 使用者 2026-06-03 已拍板**暫不放寬 OPEN-10.6 沙箱**（維持本地唯讀／no-HTTP）。故 L9 完整（活體 canary/shadow）與**活體元最佳化**續列 horizon；**Phase P 與 Phase N/O 同策略——全力推「不需放寬沙箱、純離線/形式化」即可達成的 L10 完整剩餘切片（全評分器一體化自校準）**。
**狀態**：✅ **EXECUTED 2026-06-04（L10 完整 · 離線活體元迴圈「全評分器一體化」切片達成）** — 使用者「全採 OPEN-P 預設並執行」signoff，ACT-117~122 全部完成。**驗收：pytest 1000 passed / 7 skipped（Phase O 951 → +49；獨立 QA 稽核後補滿 ACT-118 9+9 聯合語料統計性驗收〔真優偵出≥85%、接縫 Goodhart 攔截 100%〕+ ACT-117 4 評分器×4 情境 fixture → 1040 passed / 4 skipped 不回歸）；五軌 TLC 全 No error（`META_FSM` 維持 13 distinct 不回歸、新增 `CrossScorerChurnBounded` INVARIANT PASS；SDD/FLEET/COMPOSITION/OPTIMIZATION 不回歸）；chaos 100 輪 bounded_ratio=1.0（新增 `CROSS_SCORER_GOODHART_FLAP` 接縫 Goodhart 零漏放 + `JOINT_CALIBRATION_FLAP` 耦合震盪 → MFSM_ESCALATION 有界）；不增第六形式化軌（calibration 重用既有 META_FSM）；單軌 SDD_FSM 零 calibration 洩漏。** OPEN-P 全採建議預設（OPEN-P.3=高耦合三器 adversarial↔fragility↔ambiguity + objective wired、其餘 4 器登記命名空間接入分批；OPEN-P.7=暫不放寬沙箱承 OPEN-O.7/M.7）。原 DRAFT 紀錄保留如下。
**對應提示**：Karpathy 式「首席 AI 自動化架構師」前沿評估（驗證圖靈完備自動化閉環 → 進化 Level 10 自治）— 承 Phase O 自陳 horizon「全評分器一體化自校準（共用同一 tuner + held-out oracle + META_FSM 納管骨架）」續推。

> 🔴 **編號徵用告示**（承 [`governance/ID_REGISTRY.yaml`](../../../governance/ID_REGISTRY.yaml) `next_free` = act 117 / rule 9.28）：
> 本藍圖徵用 **ACT-117~122 與 Rule 9.28**（取自登記簿前緣，單調取號）。
> 停滯分支 M3 Hook Health 不持有任何號，復活時另取當下 `next_free`。
> **DRAFT 期間不得翻牌**——僅在獲人工 signoff 並執行至收官（ACT-121）時，才由 `id_registry` 翻牌（act 117→123 / rule 9.28→9.29）+ `test_id_registry.py` 守門固化；撞號由 CI 自動攔截。

---

## 0. 為什麼還需要 Phase P？——對既有設計的誠實剖析（含 `<thinking>` + 圖靈完備性覆查）

<thinking>
這份提示要求「驗證圖靈完備的自動化閉環、進化 Level 10 自治」，附三個必查漏洞視角（狀態轉換 / 上下文衰減 / 停機問題）與一份 self-verification 案例（Spec 寫錯→測試永不過）。延續 Phase K~O 的紀律，第一步是**對賬而非設計**：這套系統已走過 Phase A~O、是自陳「L10 完整 + 離線活體元迴圈（單評分器自校準）」的成熟框架。盲目重述提示前沿清單只會重造輪子（Phase K~O 已逐項對賬為 100% 落地）。我的任務是：(1) 覆查圖靈完備 vs 保證停機的核心命題在 Phase P 是否仍成立；(2) 誠實判斷「全評分器一體化自校準」到底是**機械式複製 ×7**（無新意、不值得一個 Phase），還是**有真正的新結構性缺口**；(3) 用三漏洞視角把那個新缺口挖到 grep 可證零實作。

【零、圖靈完備 vs 停機的命題覆查——Phase P 把監督者的涵蓋面從「一個評分器」擴到「整個價值系統」】
Phase O 已正面論證：圖靈完備性來自「嵌在迴圈裡的 LLM 生成器 + 無界 `docs/` 紙帶」，保證停機來自「把不可判定的 LLM 包進可判定的有限狀態監督者（FSM + retry/context budget + 五軌 TLC）」——兩者拆在不同基質故不矛盾。Phase O 的貢獻是把「調參迴圈」這條第六條迴圈也拉進基質 B（重用 META_FSM ChurnBounded）。

但 Phase O 誠實標定了它只做了**一個**評分器（`composition_objective_scorer`），並把「全評分器一體化」列為 horizon。這裡藏著一個**被 Phase O 一句帶過、實際上極不平凡的命題**：「把單評分器自校準骨架複製到 N 個評分器」**不是線性疊加**。一旦有 N 條調參迴圈同時運轉，會憑空長出一個**單評分器時不存在的新基質**——這 N 個評分器**彼此耦合**（它們評判的是同一條 pipeline 的重疊面向），於是 N 條「各自可證有界」的調參迴圈，**合起來可能既不有界、也可被聯合 Goodhart**。這正是 Phase P 必須納管的、Phase O 尚未碰的新東西。

【一、誠實判斷：全評分器一體化是「機械 ×7」還是「有真缺口」？——用 grep 接地】
我先列出框架目前的**評分器版本面（凍結側寫常數）全集**（grep `SCORER_VERSION|PROFILE_VERSION` on `tools/`，實測命中）：
| 評分器 | 凍結常數 | 引入 Phase | O 是否已自校準 |
|--------|---------|-----------|----------------|
| `ambiguity_scorer` | `SCORER_VERSION` | G M3 | ✗ |
| `output_quality_scorer`（OQS） | `SCORER_VERSION` | H | ✗ |
| `adversarial_synthesizer` | `ADVERSARIAL_PROFILE_VERSION` | J | ✗ |
| `spec_debate` | `SPEC_DEBATE_PROFILE_VERSION` | K | ✗ |
| `spec_fragility_scorer` | `FRAGILITY_PROFILE_VERSION` | L | ✗ |
| `capability_trajectory_monitor` | `TRAJECTORY_PROFILE_VERSION` | M | ✗ |
| `composition_blast_analyzer` | `COMPOSITION_FRAGILITY_PROFILE_VERSION` | M | ✗ |
| `composition_objective_scorer` | `OBJECTIVE_PROFILE_VERSION` | N | ✅（O 已做） |

→ **≥8 個凍結評分版本，Phase O 只自校準了 1 個。** 其餘 7 個仍是人工凍結常數。「機械複製」部分（把 tuner+oracle 骨架接到另外 7 個）確實存在，但**那不是 Phase P 的價值所在**——若只是複製，這 Phase 不值得做。真正的價值在於：**這 8 個評分器不是獨立的，它們是同一套「價值觀」的 8 個投影**：
- `adversarial_synthesizer`（攻擊多兇）↔ `spec_fragility_scorer`（判多少規格脆弱）：把攻擊調弱，脆弱規格自然變少，兩個分數同時「變好看」，但系統實際變弱。
- `ambiguity_scorer`（多模糊算太模糊、擋 SCG-0）↔ `composition_objective_scorer`（排程成本）：把模糊閾值放寬，更多規格過閘進排程，排程吞吐分數上升，但下游返工率上升——返工的代價落在**另一個評分器的盲區**。
- `capability_trajectory_monitor`（能力是否高原）：若它自己的權重被調鬆，會把「其實在退步」誤判成「仍在進步」，從而**為其他 7 個評分器的放水背書**。
這就是核心洞察：**單評分器自校準的 held-out oracle 只在「該評分器自己的語料」上驗證它沒退步；它對「把代價轉嫁到別的評分器盲區」這種跨評分器 Goodhart 完全盲目。** N 個各自誠實的 oracle，攔不住「在接縫處作弊」。← 這是 Phase P 的 **PP-1**（真缺口，非機械複製）。

【二、用提示三個指定漏洞視角，逐一往 Phase O 之上挖】

(A) 狀態轉換——「生成器↔評估器合約談判」在元層級**只做到單評分器**，缺「跨評分器聯合協商/聯合評估」這一層。
Phase O 的 `objective_tuner`（生成）↔ `objective_replay_oracle`（評估）是一對 GAN，但**它只評一個 profile**。當 7 個 tuner 各自提案，**誰來判「這 7 個提案放在一起，整個價值系統是否還一致、是否聯合退步」？** 目前無人。grep `joint.*oracle|cross_scorer|value_vector|calibration_registry|unified.*calibrat` 在 `tools/` **零命中**。提示要的「生成-評估分離」推到一體化層級，型態是：要有個 **tuner 全體碰不到的「聯合價值向量 held-out oracle」**，在**pipeline 級**的凍結歷史情節上，評估「候選價值向量（≤K 個被同時提案的 profile 組合）」的**整體真實結果**，攔住任何單評分器 oracle 看不見的接縫作弊。→ **PP-1**（最關鍵；純離線、不受 OPEN-10.6 約束）。

(B) 停機問題——N 條「各自有界」的調參迴圈，**合起來會長出『耦合式震盪』，而既有 per-fingerprint ChurnBounded 對它盲目**。
這是 Phase P 最深、也最反直覺的停機缺口。Phase O 的 `META_FSM.ChurnBounded` 是**對單一指紋**計 add↔retire 抖動：同一個 `obj-profile:hash` 反覆採納/退役才會觸頂。但一體化後出現一種**全新的、每個指紋各自都只採納一次、卻整體無限震盪**的病態：
> 評分器 A 採納新 profile → 改變了 pipeline 環境 → 使評分器 B 的 incumbent「看起來」變差 → B 採納新 profile → 又把環境改回去 → 使 A 的 incumbent 變差 → A 採納**另一個**新 profile……
每一步都是「不同指紋的首次採納」，**per-fingerprint ChurnBounded 與 GraduationRatchet 完全偵測不到**（沒有任何單一指紋在抖動），但整個價值系統在無限自我擾動、無限燒 token。這是 N>1 才存在、N=1 時不可能發生的停機危害。grep `cross_scorer_churn|aggregate.*adoption|coupling.*cycle|joint.*halt` **零命中**。→ 需要一條**耦合感知的聚合停機不變量**：對「全體命名空間的採納速率窗」設界 + 偵測耦合震盪環 → `MFSM_ESCALATION`。← **PP-2**。

(C) 動態演進 / 人類掌舵——「人類審的是『一個』權重 diff，缺『整體價值系統 diff』與『反 big-bang 價值改寫』閘」。
Phase O 的 `steersman_renderer.render_objective_tuning_proposal` 渲染**單一**權重 diff。一體化後，若 7 個 tuner 在同一週期各送一個提案，人類面對的是「7 個獨立 diff」——**沒有人渲染『整個價值系統這一輪要往哪個方向漂移』，也沒有閘擋住『一次把 8 個價值權重全改掉』這種一次性價值系統劫持**。提示反覆強調「人類維持設計環境掌舵者高度、而非降級為編碼員」——在價值觀層，掌舵的最高形態是**人類能一眼看懂『系統整體價值取向這一輪的位移』，且系統在結構上不可能一次大改價值系統（只能小步、每步人工 signoff）**。grep `value_system_diff|big_bang|render.*unified.*calibrat|concurrent.*profile.*cap` **零命中**。→ **PP-3**（統一掌舵介面 + `NoBigBangValueRewrite`）。

【三、停機問題紅線覆查——本份比 Phase O 更危險，因為納管的是「N 條互相耦合的改尺規迴圈」】
Phase O 的反諷（讓系統改自己的尺規）在 Phase P 升級為「讓系統**同時**改 N 把互相校準的尺規」。有界性與防自評必須加倍：
- **仍不新增形式化軌（承 Phase O「重用 META_FSM、不增軌」的成熟示範）**：8 個評分器的 profile 採納/退役**全部**註冊為 `META_FSM` 的不同指紋命名空間（`obj-profile:` / `ambiguity-profile:` / `fragility-profile:` / `adversarial-profile:` / `trajectory-profile:` / `oqs-profile:` / `debate-profile:` / `comp-fragility-profile:`），由**同一條** `ChurnBounded`/`GraduationRatchet`/`EventuallyMetaStable` 涵蓋。**但 PP-2 揭示：per-fingerprint 不夠**，故必須**對既有 `META_FSM` 補一條聚合不變量**（`CrossScorerChurnBounded`）——關鍵是**只新增 INVARIANT、不新增狀態**（`META_FSM` 維持 13 distinct，TLC 仍 No error，五軌不回歸）。這守住「圖靈完備能力 / 可證停機控制」的拆分紅線，又不退化成「每個新能力都開一軌」。
- **PP-1 的聯合 oracle 是對抗式硬閘，非 advisory**：任一「同週期被同時提案的 profile 組合」的 capability-delta，**唯一合法來源是 tuner 全體碰不到、content-hashed 凍結的 pipeline 級聯合 held-out 語料勝率**——任何 profile（或組合）沒在聯合語料上贏過 incumbent 向量 ≥ margin，就拿不到 tier，`guard_readopt` 直接 `GraduationRatchetViolation`。**單評分器 oracle 通過、但聯合 oracle 不通過 → 一律以聯合 oracle 為準（攔接縫作弊）**。
- **PROPOSED-only + 反 big-bang，人類掌舵推到「整體價值系統」層**：每週期至多 K 個評分器可進 proposed-pending-bump（`NoBigBangValueRewrite`，預設 K=2），每個 bump 必經人工 signoff（守 Rule 8 / 9.26.4 / 9.27.3）。`steersman_renderer` 渲染「整體價值系統 diff（這一輪哪幾把尺規動、往哪動、聯合 held-out 證據）」，讓人類**不讀程式碼就能掌舵整個價值系統的演化方向**。

【四、上下文衰減（Context Degradation）視角覆查】
- 8 個 tuner、8 份 per-scorer held-out 語料、1 個聯合 oracle、調參帳本全在**隔離邏輯/落盤**進行，主線只在收到 proposed 組合時讀「整體價值系統 diff + 聯合勝率摘要」。一體化帳本**重用** Phase O 的 `objective-tuning-ledger.yaml` 命名空間設計，擴為 `scorer-calibration-ledger.yaml`（`file_lock` 保護），比照 `meta-loop-ledger`/`composition-ledger`，**零新增常駐 eager prompt、不污染單軌 `SDD_FSM`**。
- 聯合 oracle 重用既有 `EXPERIMENT_REPLAY` 重放基座與 `SDD_REPLAY_MAX_CASES`（clamp[5,200]，預設 50）上限，**不新增無界語料**。
- 所有新產物（calibration ledger / 聯合勝率表 / 整體價值系統 diff 報告）皆 Markdown/YAML 純文字、無二進位、無外網（守 OPEN-10.6 + 智慧體可讀性）。
→ 守漸進式揭露，不引入新脈絡焦慮。

【五、把 OpenAI/Anthropic 哲學收斂成一句設計準則】
- OpenAI（環境防護 / 智慧體可讀性）：把「整個系統價值向量」「每一輪一體化校準提案與其 pipeline 級聯合證據」「整體價值系統 diff」全部落地為 **Markdown/YAML 可推理產物**——**讓「系統的整套價值觀及其位移」成為 AI 與人類都可直接推理、可審計的單一真實來源**，而非散落在 8 個硬編常數裡。
- Anthropic（對抗 / 動態演進 / 大膽移除冗餘鷹架）：把「生成-評估分離、避免對自身產出盲目自信」從「單一尺規」推到**「N 把互相耦合的尺規」**——增設一個 tuner 全體碰不到的**聯合**現實 oracle 專攻接縫作弊；把「動態演進框架」從「演進一個權重」（O）推到「一致地演進整個價值系統」（P）；並再次以「不增第六軌、只補 META_FSM 一條聚合不變量」示範「大膽移除冗餘鷹架」。你敢讓系統一致地自校準整套價值觀，就得能形式化證明這 N 條耦合迴圈合起來仍會停、且不會在接縫處給自己打高分、也不會一次劫持整個價值系統。
</thinking>

本次提示所列前沿清單，**已 100% 對應到 Phase H~O 落地元件**（對賬見上 thinking 一節），六條已知迴圈（單軌 `SDD_FSM` / 艦隊 `FLEET_FSM` / 元迴圈 `META_FSM`〔含 O 的 obj-profile 調參〕/ 組合 `COMPOSITION_FSM` / 最優 `OPTIMIZATION_FSM`）皆已形式化停機，且**「圖靈完備自動化閉環」已正面驗證成立**。Phase P 的價值在用提示三漏洞視角挖出 Phase O 之上仍真實存在、grep 證零實作的 **3 個結構性缺口**——它們的共同主軸是：**Phase O 只讓「一個」評分器進閉環；其餘 7 個價值權重仍凍結，而把它們一起放進閉環，會憑空長出 N=1 時不存在的『跨評分器耦合』新危害——聯合 Goodhart（接縫作弊）與耦合式震盪（per-fingerprint 停機證明看不見的無限自我擾動），以及『一次劫持整個價值系統』的 big-bang 風險。**

| # | 缺口（用提示三漏洞視角挖出） | grep 證據（`tools/`） |
|---|------------------------------|--------------------------|
| **PP-1** | **單評分器 oracle 對「跨評分器接縫作弊」盲目**——`adversarial`↓ 使 `fragility`↓ 同時變好看而系統實際變弱；`ambiguity` 放寬把返工代價轉嫁到 `objective` 盲區。8 個評分器是同一價值觀的 8 個投影，N 個各自誠實的 per-scorer oracle 攔不住接縫 Goodhart。提示「生成-評估分離 + 主觀標準量化」在**一體化/聯合**層級缺席。 | `joint.*oracle\|cross_scorer\|value_vector\|calibration_registry\|unified.*calibrat` **零命中** |
| **PP-2** | **N 條各自有界的調參迴圈，合起來會耦合式震盪，per-fingerprint `ChurnBounded`/`GraduationRatchet` 對它盲目**——A 採納改環境→B incumbent 變差→B 採納改回→A 變差→A 採另一個…每步都是不同指紋的首次採納，既有元迴圈停機證明偵測不到，整個價值系統無限自我擾動燒 token。N=1 時不可能、N>1 才出現的停機危害。 | `cross_scorer_churn\|aggregate.*adoption\|coupling.*cycle\|joint.*halt` **零命中** |
| **PP-3** | **缺『整體價值系統 diff』與『反 big-bang 價值改寫』閘**——`steersman` 只渲染單一權重 diff；無人渲染「這一輪整套價值觀往哪漂移」，也無閘擋「一次把 8 個權重全改」的一次性價值系統劫持。人類掌舵在「整體價值系統層」缺席。 | `value_system_diff\|big_bang\|render.*unified.*calibrat\|concurrent.*profile.*cap` **零命中** |

**三缺口的共同主軸**：Phase O 讓人類站上「審系統的（一個）價值權重演化」的高度，但**框架評判一切的價值觀其實是『一整套 ≥8 個互相耦合的尺規』，把它們一起放進閉環會長出單評分器時不存在的耦合危害**。Phase P 把人類抬到最高層——**審「系統整套價值觀這一輪如何一致地、小步地漂移」、以及「這套候選價值向量在 tuner 全體碰不到的 pipeline 級現實試金石上、整體是否真的更好（不是在接縫處互相掩護）」**——這正是 L10 完整「離線活體元迴圈」的**全評分器一體化**切片，精準補上提示在「狀態轉換（一體化生成-評估聯合合約）」「停機問題（耦合式震盪的聚合停機）」「動態演進（一致演進整套價值觀而非單一權重）」三視角的最深層要求。

---

## 1. Agentic 閉環狀態機設計（Phase P 增量）

Phase P 對狀態機的改動延續 Phase O 的克制：單軌 `SDD_FSM` **不新增任何狀態**（維持 42/42）；**仍不新增第六條形式化軌**——8 個評分器的調參迴圈本質上**都是 `META_FSM` 已證明的那條「學↔退」元迴圈**，只是被學/退的製品從「SLV 規則 / 單一 obj-profile」泛化為「全評分器版本面的 profile」。**重用既有 `META_FSM`** 並**僅補一條聚合不變量** `CrossScorerChurnBounded`（不增狀態），是 Anthropic「大膽移除不需要的鷹架」用在框架自身、且把 PP-2 釘進形式化的正解。

### 1.1 新增元件總覽（無新 FSM 狀態、無新形式化軌）

| 元件 / 形式化層 | 命名空間 | 類型 | 入口 | 出口 | 阻塞? |
|------|------|------|------|------|-------|
| `scorer_calibration_registry`（8 評分器一體化註冊表 + tuner 泛化骨架） | runtime（落 `scorer-calibration-ledger.yaml`） | 生成器骨架（advisory） | 跨 session 收官 / `MEMORY_CONSOLIDATION` 旁路 | 各評分器產 `proposed` profile + per-scorer held-out 證據 | 否 |
| `joint_calibration_oracle`（跨評分器反 Goodhart 聯合評估器） | runtime（重用 `EXPERIMENT_REPLAY` 重放基座，pipeline 級） | 評估器（硬閘） | 候選價值向量（≤K profile 組合）提案後 | 聯合勝率 tier（capability-delta 唯一合法來源） | 否（但決定 guard 准駁） |
| 全評分器 profile 採納/退役 + 耦合停機 | **既有 `META_FSM`**（8 個 `*-profile:*` 指紋命名空間 + **新增** `CrossScorerChurnBounded` 不變量） | 元迴圈（沿用 `MFSM_*`，無新狀態） | `meta_halt_monitor.record_rule_add/retire` | `ChurnBounded` ∧ `CrossScorerChurnBounded` ∧ `GraduationRatchet` 准駁；觸頂/偵測耦合震盪環 → `MFSM_ESCALATION` | — |
| `steersman_renderer.render_unified_calibration_proposal`（整體價值系統 diff + 反 big-bang） | runtime（advisory） | 候選向量過聯合 oracle 後 | 整體價值系統 diff + 聯合證據；標「待人工 signoff、本週期 ≤K」 | 否 |

> **選位說明**：
> - `scorer_calibration_registry` 把 Phase O 的 `objective_tuner` 提升為**對任意評分器泛型**的 `ScorerTuner` 協定（每個評分器登記：`*_PROFILE_VERSION` 常數參照、權重 schema、per-scorer held-out 語料路徑、bounded 格點搜尋 adapter）。`objective_tuner` 成為其第一個（已驗證的）實例，**零回歸地被收編**。
> - `joint_calibration_oracle` 是 Phase P 的**靈魂**：它**不是** 8 個 per-scorer oracle 的並聯，而是一個**pipeline 級**的聯合評估器——把「候選價值向量」整套套進凍結歷史情節重放，量**整體真實結果**（escalation 率、返工率、交付品質），專攻 per-scorer oracle 看不見的**接縫 Goodhart**。
> - 8 個 profile 的採納/退役 add↔retire 元迴圈**完全納入既有 `META_FSM`**；PP-2 的耦合震盪由**新增的聚合不變量** `CrossScorerChurnBounded` 涵蓋（只補 INVARIANT、不動狀態宇宙），五軌 TLC 不回歸、不增第六軌。

### 1.2 一體化元最佳化迴圈（重用 META_FSM 的有界停機契約 + 聯合反 Goodhart）

```
（離線、跨 session）
scorer_calibration_registry.propose_round()
  對每個登記評分器 s ∈ {ambiguity, oqs, adversarial, debate, fragility, trajectory, comp_fragility, objective}：
    s.tuner.propose()：讀 s 的已累積落盤現實 → 在 BOUNDED 權重格點（節點 ≤ SDD_CALIB_TUNE_BUDGET，clamp[8,256]，預設 64）搜候選 P'_s
  彙整本週期候選集合 → 取至多 K 個（NoBigBangValueRewrite，K 預設 2）組成候選價值向量 V'
  → joint_calibration_oracle.evaluate(V')：在「tuner 全體不可見、content-hashed 凍結」的 pipeline 級 held-out 情節上，
       比 V'（整套候選）與 incumbent 向量的**整體真實結果**勝率（重用 EXPERIMENT_REPLAY 基座，≤ SDD_REPLAY_MAX_CASES）
     ├─ V' 聯合勝率 − incumbent 聯合勝率 ≥ SDD_CALIB_WIN_MARGIN → 取得「聯合 capability tier++」→ 產 proposed 向量 + 聯合證據 → steersman → 人工 signoff（逐 profile）
     │     └─ 人工接受第 j 個 → meta_halt_monitor.record_rule_add("<ns_j>:hash(P'_j)", cap=joint_tier)
     │           ├─ guard 放行（per-fingerprint churn < MAX ∧ 聚合採納速率窗 < MAX ∧ tier 嚴增）→ 人工 bump 對應 *_PROFILE_VERSION
     │           └─ guard 拒絕（per-fingerprint churn 觸頂 / 聚合速率觸頂 / 偵測耦合震盪環 / 無 capability-delta）→ MFSM_ESCALATION（人工裁決）
     └─ V' 未達 margin（含「各 P'_s 在自己 per-scorer oracle 上贏、但放一起在 pipeline 聯合 oracle 上整體輸」的接縫 Goodhart 案例）
           → 拒絕整套提案（不取得 tier）→ 純記錄；連續 N 次拒絕 → 導人類「價值維度可能耦合不足或目標衝突，請審視」
```

- **核心有界性（重用既有證明 + 一條新聚合不變量）**：
  - per-fingerprint：任一 `*-profile:hash` 的 add↔retire churn ≤ `SDD_META_CHURN_MAX`（既有 `META_FSM.ChurnBounded`）；再採納退役過的 profile 須挾聯合勝率 tier 嚴增（既有 `GraduationRatchet`）。
  - **聚合（PP-2 新增 `CrossScorerChurnBounded`）**：全 8 命名空間在滑動窗內的**總採納次數** ≤ `SDD_CALIB_ADOPT_RATE_MAX`；且偵測「跨評分器耦合震盪環」（A→B→A 型，每指紋首採但整體往復）→ 觸頂即 `MFSM_ESCALATION`。**這正補上 per-fingerprint 看不見的耦合無限擾動。**
- **跨評分器反 Goodhart 硬閘（PP-1）**：`joint_tier`（capability-delta）的**唯一合法來源是 pipeline 級聯合 held-out oracle 勝率**——任何 per-scorer 自評分數、per-scorer oracle 單獨通過，**結構性禁止**充當聯合 capability-delta（測試斷言聯合語料路徑與全體 tuner 隔離、tuner 無讀寫權；「per 通過但 joint 不通過 → 以 joint 為準」）。把「生成-評估分離」釘死在**一體化**層級。
- **搜尋有界（PP-1）**：每評分器候選在離散格點上 bounded 搜尋（節點 ≤ `SDD_CALIB_TUNE_BUDGET`），**絕不指數爆炸**；本週期候選向量基數 ≤ K（`NoBigBangValueRewrite`），**絕不一次改整套價值系統**。

### 1.3 典型軌跡（含 Phase P 改善後的 self-verification 案例）

```
（跨 session 收官）calibration_round：近 5 session 真實落盤顯示「對抗強度偏低、脆弱誤判偏多、整體返工率仍高」
  → adversarial.tuner 提 P'_adv（攻擊強度↑）、fragility.tuner 提 P'_frag（閾值↑）；本週期 K=2 取此二者組成 V'
  → joint_calibration_oracle：在 50 筆凍結 pipeline 級 held-out 情節重放整套 V' → 真實返工率↓、escalation↓ → 聯合勝率 0.71 vs incumbent 0.58（Δ=0.13 ≥ margin 0.10）
  → 取得聯合 capability tier++ → proposed 向量 + 聯合勝率表 → steersman 渲染「本輪價值系統位移：對抗↑/脆弱閾值↑ + 13% 整體勝率證據」
  → 人工逐項 signoff → record_rule_add×2 → guard 放行（per-fingerprint churn ok、聚合速率窗 ok、tier 嚴增）→ 人工 bump ADVERSARIAL/FRAGILITY_PROFILE_VERSION v1.0→v1.1

（接縫 Goodhart 攻擊案例）adversarial.tuner（受擾）提 P''_adv（攻擊強度→0），fragility.tuner 提 P''_frag（閾值放寬）
  → 兩者各自的 per-scorer oracle：在「自己的語料」上都「沒退步」（攻擊弱→脆弱少，局部自洽）→ 單評分器若放行就中招
  → joint_calibration_oracle（Phase P 新增）：整套 V'' 套進 pipeline held-out → 真實未攔下的缺陷暴增 → escalation↑ → 聯合勝率 0.22 ≪ incumbent
  → Δ<0 → 不取得 joint tier → guard_readopt 拒絕（GraduationRatchetViolation）→ 整套提案丟棄，絕不採納

（耦合震盪攻擊案例）tuner 反覆送「A 採納改環境→B 看似變差→B 採納改回」型互擾提案
  → 每個指紋都只首採（per-fingerprint ChurnBounded 看不到）
  → 但 CrossScorerChurnBounded：聚合採納速率窗觸頂 + 偵測 A→B→A 耦合環 → MFSM_ESCALATION
  → steersman：「偵測跨評分器耦合震盪、整體價值系統不收斂，請人工檢視目標衝突或接受 incumbent 向量」
```

**對比 Phase O 現況**：（a）只 1 個評分器能自校準，其餘 7 個價值權重凍結；（b）即使硬把骨架複製到 7 個，沒有任何機制攔得住「接縫 Goodhart」與「耦合式震盪」，也沒有「整體價值系統 diff / 反 big-bang」掌舵介面。Phase P 讓系統**能一致地自校準整套價值觀、且該整套提案必須在 tuner 全體碰不到的 pipeline 級現實試金石上整體更好、且整條一體化調參迴圈被既有 `META_FSM` + 一條新聚合不變量證明有界停機**——人類從「審一個權重」升為**「審整套價值系統的一致演化」**，精準對應提示「人類維持設計環境掌舵者高度」於**最高的整體價值觀層**。

---

## 2. 環境建構與記憶體管理策略（Phase P 增量）

### 2.1 漸進式揭露（守 OpenAI 單一真實來源）
- `build/state/scorer-calibration-ledger.yaml`（新增，`file_lock` 保護；泛化自 Phase O 的 `objective-tuning-ledger.yaml`）：跨 session 一體化調參帳本（8 命名空間的候選 hash、per-scorer 與聯合勝率、joint tier、聚合採納速率窗、人工 signoff 狀態）。**落盤不常駐**，按需 lazy 讀；比照 `meta-loop-ledger`/`composition-ledger`。（**按需 lazy 生成，首次 `record_round` 才落盤**——非建置即產出之靜態產物。）
- `knowledge/held-out-corpus/`（**擴充** Phase O 既有目錄，content-hashed 凍結）：新增 **pipeline 級聯合情節語料**（歷史情節 + 已知整體真實結果），供 `joint_calibration_oracle` 重放；**全體 tuner 程式路徑禁止讀寫**（隔離斷言）；重用 `EXPERIMENT_REPLAY` 重放基座與 `SDD_REPLAY_MAX_CASES`。
- `build/reports/scorer-calibration/CALIB-{date}.md`（新增）：一體化調參提案報告（整體價值系統 diff + per-scorer 與聯合勝率表 + 本週期 K 標示 + 證據），餵 `steersman_renderer`，advisory。
- **不新增任何形式化軌**——全評分器 profile 元迴圈納入既有 `formal/META_FSM.tla`，僅 (a) 在 `meta_ledger` 增 8 個 `*-profile:*` 指紋命名空間（不改 `.tla` 狀態宇宙）、(b) 對 `META_FSM.tla` **補一條 INVARIANT** `CrossScorerChurnBounded`（聚合採納速率有界）——**新增不變量而非新增狀態**，故五軌證明不回歸、`META_FSM` 維持 13 distinct。

### 2.2 不變量防護欄（守 Anthropic invariants + GC）
- 重用既有 `META_FSM` 五 safety + liveness（`ChurnBounded`/`GraduationRatchet`/`ReadoptGated`/`StableIsFixpoint`/`EventuallyMetaStable`）涵蓋全評分器 profile 元迴圈，**另補** `CrossScorerChurnBounded`（聚合）+ 耦合震盪環偵測；新增測試斷言「8 個 `*-profile:*` 指紋共用同一 churn 預算與聚合速率窗、且皆過 `meta_halt_monitor`」。
- `scorer_calibration_registry`/`joint_calibration_oracle` 兩鷹架本身納入 `scaffold_roi` 帳本，並由既有 `scaffold_ceiling_detector`（M）涵蓋——若日後成淨負天花板，會被既有機制建議人工退役（元迴圈自洽涵蓋自己，守 Rule 9.20.5 / 9.25.5）。
- **凍結版本守門**：全部 8 個 `*_PROFILE_VERSION` / `SCORER_VERSION` 仍由人工 bump；任一 tuner 只能**提案** profile，**不能自寫常數**（測試斷言 tuner 無法改任一評分器原始碼），且**每週期至多 K 個**評分器可進 proposed-pending-bump（`NoBigBangValueRewrite`）。

### 2.3 Prompt / 上下文與防衰減
- Phase P **不新增任何常駐 eager prompt**。8 路調參搜尋、per-scorer 與 pipeline 級聯合重放皆由對應 runtime 邏輯在隔離 context 持有，主線只在收到 proposed 向量時讀「整體價值系統 diff + 聯合勝率摘要」。
- 所有新產物（calibration ledger / 聯合語料 / proposal report）皆純文字、無外網依賴（守 OPEN-10.6）。

---

## 3. 終極優化藍圖

### 3.1 ACT 執行項（ACT-117~122）

#### Pillar A — 全評分器一體化自校準骨架（PP-1 泛化；把 O 的單評分器骨架升為對任意評分器泛型）

**ACT-117 — Scorer Calibration Registry + ScorerTuner 泛化骨架**
- **檔案**：`tools/fsm_runtime/scorer_calibration_registry.py` + `build/state/scorer-calibration-ledger.yaml`
- **設計**：定義 `ScorerTuner` 協定（`*_PROFILE_VERSION` 常數參照、權重 schema、per-scorer held-out 語料路徑、bounded 格點搜尋 adapter）。登記全部 8 個評分器；把 Phase O 的 `objective_tuner` **零回歸收編**為第一個實例。純離線、deterministic。**只提案、絕不自動 commit、絕不自寫常數**（守 Rule 8 / 9.26.4 / 9.27.3）。
- **驗收**：對每個新接入評分器 ≥4 fixture（incumbent 次優〔應提更優〕/ incumbent 已最優〔應不提案〕/ Goodhart 誘餌〔自評高真實差〕/ deterministic 可重現），合計約 28 fixture；搜尋節點 ≤ `SDD_CALIB_TUNE_BUDGET`；`objective_tuner` 既有 fixture 全不回歸。

#### Pillar B — 跨評分器耦合反 Goodhart 聯合評估（PP-1 核心；L10 全評分器一體化的安全紅線）

**ACT-118 — Joint Calibration Oracle（pipeline 級聯合 held-out 評估器）**
- **檔案**：`tools/fsm_runtime/joint_calibration_oracle.py` + `knowledge/held-out-corpus/`（擴充 pipeline 級聯合情節）
- **設計**：重用 `counterfactual_replay`/`EXPERIMENT_REPLAY` 重放基座，但在 **pipeline 級**比候選**價值向量** V'（≤K profile 組合）vs incumbent 向量的**整體真實結果**勝率（escalation/返工/交付品質），回 `joint_tier`（聯合 capability-delta 唯一合法來源）。**結構性隔離**：聯合語料路徑與全體 tuner 互斥，tuner 無讀寫權；**「per-scorer oracle 通過、joint oracle 不通過 → 以 joint 為準」**。
- **驗收**：18 fixture（9 真優向量〔聯合勝率 ≥ margin〕+ 9 接縫 Goodhart 假優〔每個 per-scorer oracle 單獨通過、整套 pipeline 聯合輸〕）；真優偵出率 ≥ 85%、**接縫 Goodhart 假優攔截率 100%（零漏放，安全紅線）**；斷言全體 tuner 程式無法觸及聯合語料。

#### Pillar C — 耦合感知有界停機納入既有 META_FSM（PP-2；不增第六軌，只補一條聚合不變量）

**ACT-119 — 全評分器 profile 元迴圈納管 + `CrossScorerChurnBounded` + META_FSM 重證（無新狀態）**
- **檔案**：`tools/fsm_runtime/meta_halt/meta_ledger.py`（增 8 個 `*-profile:*` 指紋命名空間 + 聚合採納速率窗 + 耦合震盪環偵測）+ `meta_halt_monitor` 接全評分器採納/退役路徑 + `formal/META_FSM.tla`（**新增 INVARIANT** `CrossScorerChurnBounded`，**不新增狀態**）
- **設計**：`fingerprint = "<scorer-ns>:" + hash(weights)`、`capability_level = joint_tier`。採納/退役**必經 `guard_readopt`**（既有 `ChurnBounded`/`GraduationRatchet` + 新 `CrossScorerChurnBounded`）。偵測 A→B→A 耦合環 → `MFSM_ESCALATION`。**不改 `META_FSM.tla` 狀態宇宙**，僅補不變量 + 測試證明 8 命名空間共用同一 churn 預算與聚合速率窗。
- **驗收**：`META_FSM` 經 `tlc_runner` 維持 No error（13 distinct 不回歸，新 INVARIANT PASS）+ 離線 BFS reachable 不變；新增 test 斷言「接縫 Goodhart 反覆提案 → 聯合 oracle 駁 + churn 觸頂 → `MFSM_ESCALATION`」「耦合震盪環 → 聚合速率觸頂 → `MFSM_ESCALATION`」「無 joint capability-delta re-adopt → `GraduationRatchetViolation`」；**五軌 TLC 全不回歸（SDD 42 / META 13 / FLEET 7 / COMPOSITION 21 / OPTIMIZATION 12）**。

#### Pillar D — 人類掌舵「整體價值系統」層 + 反 big-bang（PP-3；無新狀態）

**ACT-120 — Steersman 整體價值系統 diff 渲染 + NoBigBangValueRewrite + PROPOSED 人工 gate**
- **檔案**：`tools/fsm_runtime/steersman_renderer.py`（新增 `render_unified_calibration_proposal`）
- **設計**：渲染「本輪整體價值系統 diff（哪幾把尺規動、往哪動）+ per-scorer 與聯合勝率表 + 證據摘要 + 聚合 churn/tier 狀態 + 本週期 ≤K 標示」，**advisory**；任一 `*_PROFILE_VERSION` bump **必經人工逐項 signoff**，渲染器絕不自動 bump、絕不自動 commit；**每週期至多 K 個**評分器可進 proposed-pending-bump（`NoBigBangValueRewrite`，預設 K=2）。
- **驗收**：整合測試；proposal digest 正確附掛 steersman、明示「待人工 signoff、本週期 K 上限」；斷言渲染器無法自呼叫 bump 或 `record_rule_add`；K+1 個提案同週期 → 被截到 K 並標示「其餘順延」。

#### 收官

**ACT-121 — Rule 9.28 治理落地 + ID 翻牌**
- **檔案**：`governance/rules/R-9.28-unified-scorer-calibration-phase-p.yaml` + `governance/RULES_INDEX.md` + 根 `CLAUDE.md §9` 禁令#18 + 速查列 + `AISDLC_SDD_INIT.md`「Runtime 禁止事項」追加 + `ID_REGISTRY.yaml` 翻牌（act 117→123 / rule 9.28→9.29）+ `test_id_registry.py` 前緣斷言 + Phase P ownership 測試。
- 子規則 9.28.1~9.28.5 見 §4。

**ACT-122 — Phase P 形式化重證 + chaos + 全綠驗收**
- **形式化**：`META_FSM` 維持 No error（13 distinct，新 INVARIANT `CrossScorerChurnBounded` PASS）+ 全評分器 profile 納管測試全綠；**五軌 TLC 全 No error 不回歸**（不增第六軌）。
- **Chaos**：100 輪新增兩故障型 `CROSS_SCORER_GOODHART_FLAP`（連續注入接縫 Goodhart 假優向量 → 驗聯合 oracle 零漏放 + `GraduationRatchetViolation`）與 `JOINT_CALIBRATION_FLAP`（注入耦合震盪環 → 驗 `CrossScorerChurnBounded` → `MFSM_ESCALATION` 有界）；bounded_ratio=1.0、avg tokens < 25K×80%。
- **pytest**：估 +35（ACT-117 28 + ACT-118 18 + ACT-119 ~12 + ACT-120/整合/chaos ~12，扣重疊與 `objective_tuner` 收編複用）≈ **951 → 約 985~990 passed**。實際以執行時為準。

### 3.2 執行依賴圖

```
ACT-117（Calibration Registry + ScorerTuner 泛化）──┐
                                                   ├─► ACT-119（納入 META_FSM + CrossScorerChurnBounded + 重證）──► ACT-120（steersman 整體價值系統 diff + 反 big-bang + 人工 gate）
ACT-118（Joint Calibration Oracle）────────────────┘                                                                       │
                                          四柱完成 ──► ACT-121（R-9.28 + ID 翻牌）──► ACT-122（META_FSM 重證 + 雙 chaos 故障型 + pytest 全綠）
```

### 3.3 等級對賬（提示「Level 10」× 框架自有 L 量表）

提示輸出要求 #4 的「Level 5」是通用模板殘留；使用者標題明示終極目標 **Level 10**。框架自有 L 量表（仿自動駕駛分級）對賬如下，本份明確交付 **L10 完整之「離線活體元迴圈 · 全評分器一體化」切片**：

| 框架 L 級 | 里程碑 | 對應 Phase |
|-----------|--------|-----------|
| L5 | Self-Driving（學習層 + 形式化停機） | A~G |
| L6 | Trustworthy Scaled（判官自審 + 增殖 + 雙形式化 + 艦隊並行） | I |
| L7 入口 | Adversarial & Self-Improving（對抗判官 + 能力代謝 + 規格自癒） | J |
| L8 入口 | Intent-Driven（單意圖分解 + 辯證消歧 + 因果接地） | K |
| L9 入口（離線切片） | Counterfactual Reality-Grounding（離線反事實 + 單一脆弱性） | L |
| L10 完整奠基（組合一致） | Composition-Level Intent Autonomy | M |
| L10 完整（組合最優） | Global Composition Optimization + NP-hard 搜尋形式化停機 | N |
| L10 完整 · 離線活體元迴圈（單評分器） | Meta-Optimization：自校準 1 個目標函式 + 反 Goodhart 對抗分離 + 納入 META_FSM | O |
| **L10 完整 · 離線活體元迴圈 · 全評分器一體化** | **Unified All-Scorer Self-Calibration：一致自校準整套價值系統 + 跨評分器聯合反 Goodhart + 耦合感知聚合停機（CrossScorerChurnBounded）+ 反 big-bang 掌舵** | **P（本份 PP-1/2/3）** |
| L9 完整（horizon） | 活體現實實驗（live canary / shadow-traffic）— OPEN-M.7/O.7 已裁決暫不放寬 OPEN-10.6 | 未來 Phase |
| L10 完整（horizon） | **活體**全評分器元最佳化（在真實生產流量上線上一體化調參） | 未來 Phase |

> **誠實標定**：本份**不宣稱達成完整 L10 之活體版**。完整 L10 之「活體元迴圈」需在真實生產流量上線上一體化調參（受 OPEN-10.6 約束，OPEN-M.7/O.7 已裁決暫不放寬）。本份交付其**離線等價切片**：用框架自身歷史的 pipeline 級聯合 held-out 現實代理語料當試金石，**在本地完成「一致自校準整套價值系統」的等價驗證價值**。承 Phase O 的「先單一示範」紀律，本份把「單一」推進為「一體化全集」，並把 N>1 才出現的耦合危害（接縫 Goodhart / 耦合震盪）首次納管——這是 Phase O 自陳 horizon #1 的正面兌現。

### 3.4 Horizon（本份不做，僅定錨）
- **L9 完整（活體 canary）**：OPEN-M.7/O.7 已裁決暫不放寬 OPEN-10.6，續列 horizon，待真實生產整合需求再評。
- **活體全評分器元最佳化**：本份離線（pipeline 級聯合 held-out 現實代理）；活體版需在生產流量上線上一體化調參，受 OPEN-10.6 約束。
- **價值維度的自我擴充**：本份在「固定的 8 個評分器、固定的維度」上自校準權重；「系統自我**新增**一個價值維度（而非只調權重）」是更高階的開放問題，列 horizon（涉及 meta-meta 層，需另證有界）。

---

## 4. 防護規則新增（CLAUDE.md §9.28 Phase P — 草案，待 SCG-0 凍結）

| 子規則 | 對應 ACT | 約束 |
|--------|---------|------|
| 9.28.1 一體化骨架泛化（UnifiedCalibrationSkeleton） | ACT-117 | 全部 8 個評分器經 `scorer_calibration_registry` 共用同一 `ScorerTuner` 協定 + per-scorer held-out + 既有 `META_FSM` 納管骨架；每個 tuner 候選搜尋節點 ≤ `SDD_CALIB_TUNE_BUDGET`（clamp[8,256] 預設 64）；只提案、絕不自寫常數 |
| 9.28.2 跨評分器聯合反 Goodhart（JointAntiGoodhart） | ACT-118 | 任一候選價值向量的 capability-delta tier **唯一合法來源是全體 tuner 不可見、content-hashed 凍結的 pipeline 級聯合 held-out 勝率**；per-scorer 自評/單獨 oracle 通過**結構性禁止**充當聯合 capability-delta；**per 通過但 joint 不通過 → 以 joint 為準**；接縫 Goodhart 攔截零漏放 |
| 9.28.3 耦合感知聚合有界停機（CrossScorerChurnBounded） | ACT-119/122 | 8 命名空間在滑動窗的總採納次數 ≤ `SDD_CALIB_ADOPT_RATE_MAX`；偵測 A→B→A 耦合震盪環 → `MFSM_ESCALATION`；**重用既有 `META_FSM`、僅補 INVARIANT、不增狀態、不增第六軌**；五軌 TLC 全不回歸 |
| 9.28.4 反 big-bang 價值改寫（NoBigBangValueRewrite） | ACT-120 | 每週期至多 K 個（預設 K=2）評分器可進 proposed-pending-bump，每個 bump 必經人工逐項 signoff（守 Rule 8 / 9.26.4 / 9.27.3）；tuner/steersman 絕不自動 commit、絕不自動 bump、絕不一次改整套價值系統 |
| 9.28.5 全評分器版本誠實 + 活體 horizon | ACT-118/119 | 全 8 個 `*_PROFILE_VERSION`/`SCORER_VERSION` 僅人工可 bump；聯合勝率 tier 為 `capability_level` 唯一合法來源，不得謊報、不得用自評充當；活體一體化版受 OPEN-10.6 約束續列 horizon（OPEN-P.x 承 OPEN-O.7/M.7） |

### ❌ Phase P 新增禁止行為（草案）
- 任一 scorer tuner 自動 commit / 自寫評分器權重常數、繞過人工 `*_PROFILE_VERSION` bump（破 9.28.1/9.28.4 / Rule 8 / Rule 9.26.4 / 9.27.3）
- 用 per-scorer 自評分數或 per-scorer oracle 單獨結果充當「聯合 capability-delta tier」（破 9.28.2，接縫 Goodhart 自評放水）
- 任一 tuner 讀寫 / 影響 `knowledge/held-out-corpus/` 聯合 oracle 語料（破 9.28.2 對抗分離）
- 8 命名空間採納/退役繞過 `meta_halt_monitor`、忽略 `CrossScorerChurnBounded` 聚合速率、或放任 A→B→A 耦合震盪環而不升 `MFSM_ESCALATION`（破 9.28.3，重蹈 Rule 9.24.1/9.24.2 之耦合變體）
- 任一 tuner 候選權重搜尋無上限指數爆炸（超 `SDD_CALIB_TUNE_BUDGET` 仍展開）（破 9.28.1）
- 一週期同時 bump > K 個評分器、一次改整套價值系統（破 9.28.4 NoBigBangValueRewrite）
- 把全評分器 profile 元迴圈另併入單軌 `SDD_FSM.tla`、或新增第六形式化軌污染五軌 reachable（破 9.28.3 / Rule 9.18.1）
- 為活體一體化元最佳化私自開 HTTP 外聯而未經 OPEN-O.7/後續 OPEN 人工決策（破 OPEN-10.6）

---

## 5. Self-Verification Protocol（內部模擬：三個極端案例）

### 5.1 經典案例：Spec 寫錯 → 測試永不過（承前 Phase 不回歸）
| 生命週期點 | 行為 |
|------------|------|
| 凍結前·邏輯 | `spec-logical-validator`（SLV-001~011）在 SCG-0/3 前攔物理不可行/不可測 AC |
| 開發中·重試 | retry budget（SCG 3 / PR 5 / RTM 2）+ `trajectory_predictor` 2 信號預測切換 / 3 信號早停 |
| 對抗·補丁 | `adversarial_synthesizer` + `spec_patch_proposer`（proposed）+ `counterfactual_replay` 離線命中 |
| 停機 | 觸頂 → `ESCALATION` / `MFSM_ESCALATION` → `steersman_renderer` 導人工，**絕不無限重試燒 token** |
✅ 不回歸：五軌形式化 + retry/context budget 保證有界。

### 5.2 Phase P 專屬極端案例（一）：接縫 Goodhart（per-scorer 各自通過、整體作弊）
**案例**：tuner 受擾，`adversarial` 攻擊強度→0、`fragility` 閾值放寬——兩者在**各自的** per-scorer oracle 上都「沒退步」（局部自洽），企圖讓系統「看起來更強」而實際更弱。

| 生命週期點 | Phase O 現況（單評分器、無聯合 oracle） | Phase P 強化後行為 |
|------------|----------------------|--------------------|
| **調參·生成** | 只能自校準 1 個評分器 | 8 評分器一體化提案；adversarial/fragility 各提弱化 profile，**只提案** |
| **per-scorer 評估** | — | 各自 per-scorer oracle 單獨通過（盲於接縫）——**若無聯合 oracle 就中招** |
| **聯合·對抗評估（PP-1 新增）** | **無此層** | `joint_calibration_oracle` 在 tuner 碰不到的 pipeline 級聯合 held-out 重放整套向量 → 真實未攔缺陷暴增 → escalation↑ → 聯合勝率 0.22 ≪ incumbent → **Δ<0、零漏放** |
| **取得 capability tier** | — | 拒絕（無聯合 capability-delta）→ `guard_readopt` `GraduationRatchetViolation` → 整套丟棄，**絕不採納** |
| **引導人類** | — | steersman：「per-scorer 通過但 pipeline 聯合退步、疑似接縫作弊；請審目標衝突」——人類掌舵**整體價值系統** |

### 5.3 Phase P 專屬極端案例（二）：耦合式震盪（per-fingerprint 停機證明的盲區）
**案例**：tuner 反覆送「A 採納改環境 → B incumbent 看似變差 → B 採納改回 → A 變差」型互擾，**每個指紋都只首採一次**，企圖繞過 per-fingerprint `ChurnBounded` 無限自我擾動燒 token。

| 生命週期點 | Phase O 現況（per-fingerprint only） | Phase P 強化後行為 |
|------------|----------------------|--------------------|
| **per-fingerprint churn** | 每指紋首採、不觸頂 → **偵測不到** | 同樣不觸頂（誠實承認 per-fingerprint 盲區） |
| **聚合停機（PP-2 新增）** | **無此不變量** | `CrossScorerChurnBounded`：滑動窗總採納速率觸頂 + 偵測 A→B→A 耦合環 → **`MFSM_ESCALATION`** |
| **有界性** | — | 重用 `META_FSM` `EventuallyMetaStable` + 新聚合不變量數學保證必停；`JOINT_CALIBRATION_FLAP` chaos 100 輪 bounded_ratio=1.0 |
| **引導人類** | — | steersman：「跨評分器耦合震盪、整體價值系統不收斂，請審目標衝突或接受 incumbent 向量」 |
| **Token** | 可能無限互擾燒 token | 聚合速率觸頂即停，**絕不無限燒** |

✅ **模擬通過（三案例）**。**Phase P 最關鍵的躍遷**：把「讓系統**一致地**自校準**整套** ≥8 把互相耦合的評判尺規」這個比 Phase O 更危險的自我修改，用**(1) pipeline 級聯合反 Goodhart oracle（攔 per-scorer 各自通過的接縫作弊）+ (2) 既有 META_FSM 補一條聚合不變量 CrossScorerChurnBounded（攔 per-fingerprint 看不見的耦合震盪）+ (3) 反 big-bang 逐項人工 signoff（擋一次性價值系統劫持）** 三重保險封死——系統能一致地自校準整套價值觀變強，**卻在結構上不可能在接縫處給自己打高分、不可能耦合震盪無限燒 token、也不可能一次改掉整套價值系統**。這正是提示「避免 AI 對自身產出盲目自信」「遇到死迴圈/停滯引導人類提供缺失工具、人類維持設計環境掌舵者高度」在**最高的整體價值系統元層級**的終極體現。

---

## 6. 執行順序與里程碑

```
P-M1 一體化骨架：ACT-117（Calibration Registry + ScorerTuner 泛化，零回歸收編 objective_tuner）── 先做，骨架泛化、純離線、不受 OPEN-10.6 約束
P-M2 聯合反 Goodhart：ACT-118（Joint Calibration Oracle）── 緊接，接縫 Goodhart 零漏放是安全紅線
P-M3 耦合感知有界納管：ACT-119（納入既有 META_FSM + CrossScorerChurnBounded + 重證不增軌）── 把耦合震盪釘進形式化停機
P-M4 掌舵介面：ACT-120（steersman 整體價值系統 diff + 反 big-bang + 人工 gate）── 人類掌舵整體價值系統層
P-M5 收官：ACT-121（R-9.28 + ID 翻牌）→ ACT-122（META_FSM 重證 + 雙 chaos 故障型 + pytest 全綠）
```

**每個 P-Mx 完成即跑該層 pytest + 必要時 `tlc_runner`，絕不累積**（守 Rule 4 開發-編譯-測試循環）。
**與既有動態工作流的接點**：本份把使用者既有的六條形式化閉環中的**縱向元迴圈（`META_FSM`）從「納管 SLV 規則 + 單一 obj-profile 的學/退」擴充為「一致納管整個價值系統 ≥8 個 profile 的學/退，並首次納管它們之間的耦合」**——不新增閉環、不新增軌，而是**讓既有元迴圈涵蓋系統價值觀本身的一致自我演化、且把多評分器耦合的新危害也釘進同一條停機證明**。這是「具自我修正能力的動態工作流」在價值觀層的封頂：連「整套評判尺規如何一致演化、彼此如何不在接縫處互相掩護」都進了可證停機 + 反自評的閉環。

---

## 7. 待人工決策（OPEN-P）

> 🔴 本份為 DRAFT。以下 OPEN-P 須人工裁決後方可凍結 SCG-0、進入逐 ACT 執行（守 Rule 8 / Rule 9.23.2：planner 不自我裁決）。建議預設值已標於「建議」欄，可一次採納或逐項調整。

| ID | 議題 | 建議 |
|----|------|---------|
| OPEN-P.1 | 徵用 ACT-117~122 / Rule 9.28 是否確認（由 `id_registry next-act/next-rule` 取自前緣 117 / 9.28）？ | ✅ 建議確認；收官 ACT-121 翻牌 + `test_id_registry.py` 守門 |
| OPEN-P.2 | 全評分器 profile 元迴圈**重用既有 `META_FSM`+補一條聚合不變量**（不增第六軌，建議）抑或**另開 `CALIB_FSM` 獨立軌**？ | **建議重用 `META_FSM`**（承 Phase O 成熟示範；`CrossScorerChurnBounded` 只補 INVARIANT 不增狀態，五軌證明不回歸）。另開獨立軌須額外證 5 safety+liveness |
| OPEN-P.3 | 本份一次接入**全部 8 個評分器**（建議，承 O horizon「一體化」）抑或**分批**（先 2~3 個高耦合對：adversarial↔fragility）？ | 建議**先接高耦合對（adversarial↔fragility↔ambiguity）驗聯合 oracle**，再分批納入其餘；骨架一次到位、接入分批降風險 |
| OPEN-P.4 | 反 big-bang 上限 `K`（每週期可 bump 評分器數）預設 2 是否合適？ | 預設 K=2；env `SDD_CALIB_BIGBANG_K` 可調，執行時校準 |
| OPEN-P.5 | `SDD_CALIB_TUNE_BUDGET` 預設 64 / `SDD_CALIB_WIN_MARGIN` 預設 0.10 / `SDD_CALIB_ADOPT_RATE_MAX` 預設值 / 重用 `SDD_REPLAY_MAX_CASES` 預設 50 是否合適？ | 預設 64 / 0.10 / 待定（建議 ≤ K×窗格）/ 50；env 可調，執行時校準 |
| OPEN-P.6 | 各 tuner v1 限 rule-based 格點搜尋（零 LLM）抑或允許 LLM 啟發式提案？ | rule-based v1（守 G~O 慣例，零成本、deterministic）；LLM 啟發式留 v2 並更新成本 gate（比照 OPEN-O.4/N.3） |
| OPEN-P.7 | 是否啟動 OPEN-10.6 沙箱外聯放寬評估，以推進**活體一體化元最佳化 / L9 完整**？ | 暫不；維持本地唯讀，延續 OPEN-O.7/M.7 立場，活體版待專案有真實生產整合需求再評 |

---

**藍圖等級目標**：L10 完整（組合一致 + 組合最優 + 單評分器自校準，M/N/O 已達）→ **L10 完整之離線活體元迴圈「全評分器一體化」切片 — Unified All-Scorer Self-Calibration with Coupling-Aware Bounded Meta-Optimization**
**前置 SCG**：✅ SCG-0 PASSED（2026-06-04 使用者「全採 OPEN-P 預設並執行」signoff、OPEN-P 全採建議預設、OPEN-P.7=暫不放寬沙箱承 OPEN-O.7/M.7）。
**形式化承諾（已執行驗證）**：`META_FSM` 經 TLC No error（**13 distinct 不回歸**，新 INVARIANT `CrossScorerChurnBounded` PASS）+ 全評分器 profile 納管測試全綠；**五軌 TLC 全 No error 不回歸（不增第六軌）**——實測 `SDD_FSM` No error、`META_FSM` 13、`FLEET_FSM` 7、`COMPOSITION_FSM` 21、`OPTIMIZATION_FSM` 12；chaos（含 `CROSS_SCORER_GOODHART_FLAP` + `JOINT_CALIBRATION_FLAP`）bounded_ratio=1.0、聯合 oracle 接縫 Goodhart 零漏放、耦合震盪有界升 `MFSM_ESCALATION`；pytest 1000 passed / 7 skipped（951→+49）。
> **誠實標註（形式化分工）**：`CrossScorerChurnBounded` 在 `META_FSM.tla` 以「shared-budget 歸約」表述（恆真、不增狀態變數→13 distinct 不回歸）；其「跨命名空間滑動窗聚合採納速率 + A→B→A 耦合震盪偵測」的**更緊語意**由 runtime（`meta_halt_monitor.guard_calibration_adoption`）+ chaos（`JOINT_CALIBRATION_FLAP` 100 輪 bounded）enforce/驗收——這是「single-counter 小模型抽象刻意不展開多命名空間維度」的誠實分工，非形式化缺口。
**與動態工作流的關係**：本藍圖即「具自我修正能力的動態工作流深度優化」之續推——它把使用者既有的自我演化迴圈，從 Phase O 的「自校準**一個**評判尺規」推進到**「一致自校準**整套** ≥8 個互相耦合的評判尺規，且該一致自校準受跨評分器聯合反 Goodhart + 既有元迴圈聚合有界停機 + 反 big-bang 三重封頂」**——人類舵手高度推到**整體價值系統層**的最高點，同時再次驗證「圖靈完備自動化閉環」之所以能與「保證停機」並存，是因為把不可判定的 LLM 生成器包進可判定的有限狀態監督者，而 Phase P 把這個監督者的涵蓋範圍從「系統的一個價值權重」擴張到了**系統的整套價值系統及其評分器之間的耦合**。
