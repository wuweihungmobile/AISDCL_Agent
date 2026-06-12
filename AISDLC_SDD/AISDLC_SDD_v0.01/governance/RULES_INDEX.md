# Rule Registry — 治理規則地圖（唯一 eager-load）

> **Phase H M3 / ACT-051**：落實 SDD_improving_Automation_08.md §4.1 / §G4 漸進式揭露。
> 本檔是治理規則的**地圖**（單一真實來源指標），每條規則一行；細節 lazy-load 自
> `governance/rules/R-*.yaml`，由 `rule_loader.load_for_state(state)` 依當前 FSM 狀態
> 只載入命中的規則，取代 CLAUDE.md Rule 9 散文巨表的 eager-load。
>
> **遷移狀態（2026-06-05 更新）**：**Phase 1 抽取完成** — CLAUDE.md 全部 34 條 Rule 9.x
> 已抽成結構化 `R-*.yaml`（共 35 檔，含 R-SELF-STRIDE），由
> `tests/test_rules_index_sync.py` 守 RULES_INDEX ↔ R-*.yaml 雙向同步。
> **Phase 2（待辦）**：把 CLAUDE.md 的 Rule 9.x 散文裁剪為 ≤1 頁禁令摘要 + 指回本 registry，
> 以實現 eager-load token 節省（動到 always-loaded 指令檔，須獨立 PR 謹慎 review）。
> 在 Phase 2 完成前，CLAUDE.md 仍為 Rule 9 的權威全文；本 registry 為機器可查詢副本。

## 載入協議

```python
from tools.fsm_runtime import rule_loader
rules = rule_loader.load_for_state("IMPLEMENTATION")   # 只載 trigger_states 命中者
```

## 規則索引

| id | 標題 | 觸發狀態 | 嚴重度 | maturity | 規則檔 |
|----|------|---------|--------|----------|--------|
| R-9.1 | FSM Retry Budget | SCG_VALIDATION / PR_REVIEW / RTM_VERIFY / SPEC_REGRESSION_CHECK | critical | active | R-9.1-fsm-retry-budget.yaml |
| R-9.2 | Context Budget（Token 預算） | * | high | active | R-9.2-context-budget.yaml |
| R-9.3 | 邏輯一致性防護（SLV 前置） | SCG_VALIDATION / SPEC_DRAFTING / SPEC_AUDIT / PR_REVIEW | high | active | R-9.3-logical-consistency-guard.yaml |
| R-9.4 | SPEC_FROZEN 強制壓縮 | SPEC_FROZEN | high | active | R-9.4-spec-frozen-compaction.yaml |
| R-9.5 | ESCALATION 不可自動退出 | ESCALATION / ESCALATION_FINAL / TERMINATED | critical | active | R-9.5-escalation-no-auto-exit.yaml |
| R-9.6 | Phase D Hooks（Runtime 強制層） | * | critical | active | R-9.6-phase-d-hooks.yaml |
| R-9.7 | Phase E M1 精準停機 | * / HUMAN_PENDING / AUTO_COMPACT_PENDING | critical | active | R-9.7-precise-halt-m1.yaml |
| R-9.8 | Phase E M2 閉環品質鏈 | * / PR_REVIEW / IMPLEMENTATION | high | active | R-9.8-closed-loop-quality-m2.yaml |
| R-9.9 | Phase E M2.5 Chaos 有界停機驗收 | * | critical | active | R-9.9-chaos-bounded-halt.yaml |
| R-9.10 | Phase E M3 Production Feedback | PRODUCTION_SIGNAL / RELEASE | high | active | R-9.10-production-feedback-m3.yaml |
| R-9.11 | Phase E M4 Learning Layer | LEARNING_COMMIT / SCG_VALIDATION | high | active | R-9.11-learning-layer-m4.yaml |
| R-9.12 | Phase F M2 Cross-Project Hub | HUB_SYNC | high | active | R-9.12-cross-project-hub.yaml |
| R-9.13 | Phase F M3+M4 多模態 Spec 驗證 | SCG_VALIDATION / SPEC_DRAFTING | high | active | R-9.13-multimodal-spec-validation.yaml |
| R-9.14 | Self-Healing 有界復原 | ESCALATION | critical | active | R-9.14-self-healing.yaml |
| R-9.15 | Phase G M2 Predictive Halt | TRAJECTORY_PREDICTED / IMPLEMENTATION / PR_REVIEW / RTM_VERIFY / SCG_VALIDATION / SPEC_REGRESSION_CHECK | high | active | R-9.15-predictive-halt-m2.yaml |
| R-9.16 | Phase G M3 Ambiguity Quantifier | SCG_VALIDATION / SPEC_DRAFTING | high | active | R-9.16-ambiguity-quantifier-m3.yaml |
| R-9.17 | Phase G M4 Continuous Drift Monitor | DRIFT_OBSERVATION / SPEC_FROZEN / IMPLEMENTATION / PR_REVIEW | high | active | R-9.17-continuous-drift-monitor-m4.yaml |
| R-9.18 | Phase G M5 Formal Halt Verification | * | critical | active | R-9.18-formal-halt-verification-m5.yaml |
| R-9.19 | Phase G M6 Cost-Aware Orchestration | PR_REVIEW / IMPLEMENTATION | high | active | R-9.19-cost-aware-orchestration-m6.yaml |
| R-9.20 | Phase H 生成-對抗-執行閘 | SPEC_FROZEN / TEST_CONTRACT_NEGOTIATED / IMPLEMENTATION / EXECUTION_EVALUATION / SCAFFOLD_GC | high | active | R-9.20-phase-h-gae.yaml |
| R-9.21 | Phase I 可信賴的規模化現實自治 | SANDBOX_HARDENING_GATE / EXECUTION_EVALUATION / EVALUATOR_AUDIT / MONITOR_VIOLATION / MEMORY_CONSOLIDATION / PRODUCTION_BEHAVIORAL_SIGNAL | high | active | R-9.21-trustworthy-scaled-phase-i.yaml |
| R-9.22 | Phase J 對抗式自我改進現實自治 | ADVERSARIAL_EVALUATION / CAPABILITY_BENCHMARK / SPEC_PATCH_PROPOSAL | high | active | R-9.22-adversarial-self-improving-phase-j.yaml |
| R-9.23 | Phase K 意圖規劃+辯證消歧+因果定位 | INTENT_DECOMPOSITION / SPEC_DEBATE | high | active | R-9.23-intent-planning-dialectic-phase-k.yaml |
| R-9.24 | Phase L 元迴圈形式化停機+離線反事實+主動脆弱性 | LEARNING_COMMIT / SCAFFOLD_GC / SPEC_PATCH_PROPOSAL / EXPERIMENT_REPLAY | high | active | R-9.24-meta-halting-offline-experiment-phase-l.yaml |
| R-9.25 | Phase M 組合級意圖自治+進步性監測+組合脆弱性 | BACKLOG_PRIORITIZED / SCAFFOLD_GC / MEMORY_CONSOLIDATION | high | active | R-9.25-composition-autonomy-progress-monitoring-phase-m.yaml |
| R-9.26 | Phase N 全域組合最佳化+NP-hard 搜尋形式化停機 | BACKLOG_PRIORITIZED / INTENT_DECOMPOSITION | high | active | R-9.26-global-composition-optimization-phase-n.yaml |
| R-9.27 | Phase O 自我調參的對抗式有界元最佳化 | LEARNING_COMMIT / MEMORY_CONSOLIDATION | high | active | R-9.27-meta-optimization-self-tuning-phase-o.yaml |
| R-9.28 | Phase P 全評分器一體化自校準的耦合感知有界元最佳化 | LEARNING_COMMIT / MEMORY_CONSOLIDATION | high | active | R-9.28-unified-scorer-calibration-phase-p.yaml |
| R-9.29 | Phase Q 價值維度的自我擴充（meta-meta 層有界本體論演化） | LEARNING_COMMIT / MEMORY_CONSOLIDATION | high | active | R-9.29-self-expanding-value-dimensions-phase-q.yaml |
| R-9.30 | Phase R 價值維度語意的自我發明 + 退役聯動（meta-meta-meta 層候選池外有界生成與定基數本體論演化） | LEARNING_COMMIT / MEMORY_CONSOLIDATION | high | active | R-9.30-self-inventing-value-dimensions-phase-r.yaml |
| R-9.31 | Phase S 生成文法詞彙的自我擴充（meta⁴）+ 多維度批次退役聯動（VOCAB 外有界詞彙生成與批次本體論重構有界停機） | LEARNING_COMMIT / MEMORY_CONSOLIDATION | high | active | R-9.31-self-expanding-vocabulary-batch-retirement-phase-s.yaml |
| R-9.32 | Phase T 轉換算子文法的自我擴充（meta⁵）（TRANSFORMS/OPS 外有界算子生成文法 + 算子可計算性有界停機） | LEARNING_COMMIT / MEMORY_CONSOLIDATION | high | active | R-9.32-self-expanding-operator-grammar-phase-t.yaml |
| R-9.33 | Phase U 組合算子文法的自我擴充（meta⁶）（PRIMITIVES/COMBINATORS 外有界字母表生成文法 + 可計算性閉包有界停機） | LEARNING_COMMIT / MEMORY_CONSOLIDATION | high | active | R-9.33-self-expanding-operator-alphabet-phase-u.yaml |
| R-9.34 | Phase V 算子組合深度文法的自我擴充（meta⁷）（深度 <=2 外有界深度生成文法 + 深度可計算性閉包有界停機，因 cost==depth） | LEARNING_COMMIT / MEMORY_CONSOLIDATION | high | active | R-9.34-self-expanding-operator-depth-phase-v.yaml |
| R-9.35 | Phase W 算子間互遞迴文法的自我擴充（meta⁸）（非遞迴外有界互遞迴生成文法 + 良基停機證書有界停機，因互遞迴=停機可判定性臨界線） | LEARNING_COMMIT / MEMORY_CONSOLIDATION | high | active | R-9.35-self-expanding-operator-recursion-phase-w.yaml |
| R-9.36 | Phase X 具身接地接入 META_FSM（具身評估器接地元迴圈自我演化判定 + EmbodiedGroundingBounded 有界停機，因「真實沙箱可能 hang」是新不停機源） | LEARNING_COMMIT / MEMORY_CONSOLIDATION | high | active | R-9.36-embodied-grounding-phase-x.yaml |
| R-9.37 | Phase Y meta⁸ 互遞迴呼叫圖人類視覺化儀表板（可解釋性轉向：可證良基終止 + 互遞迴呼叫圖有界可稽核投影成人類可審批拓樸 + VisualizationBounded 有界停機，因「渲染無界大圖可能 token 爆炸/OOM」是新不停機源） | LEARNING_COMMIT / MEMORY_CONSOLIDATION | high | active | R-9.37-recursion-topology-visualization-phase-y.yaml |
| R-SELF-STRIDE | 自治執行迴圈自身安全（Loop Self-STRIDE） | SANDBOX_HARDENING_GATE / EXECUTION_EVALUATION | critical | active | R-SELF-STRIDE.yaml |

> maturity ∈ {active, audit-only, deprecated}；降級/退役須 `set_maturity(reviewed_by=...)`
> 人工 review（§5.1 Rule Graduation）。Scaffold ROI 由 `rule_loader.record_fire()` 記帳。

---

## 編號分配權威（ACT / Rule）

> **單一真實來源**：[`governance/ID_REGISTRY.yaml`](ID_REGISTRY.yaml)。本表只列 **active** 規則（磁碟即真實）；
> 「下一個可用號 / 保留號 / 停滯分支」一律以 ID_REGISTRY 為準，杜絕跨 Phase/分支撞號。

- 分配新號前必查：`python -m tools.fsm_runtime.id_registry next-act`（現為 **ACT-159**）／`next-rule`（現為 **R-9.37**）。
- 機器守門：`tools/fsm_runtime/tests/test_id_registry.py`（每次 pytest/CI 強制檢查重疊/跳號/前緣漂移，撞號即 fail）。
- 分配原則：**一律從 `next_free` 單調取號**；停滯/備援分支（如 M3 Hook Health）**不預留任何號**，復活時重新取當下 `next_free`。
- 現況保留：**Phase K** 持有 ACT-081~088 / **R-9.23**（已 active）；**Phase L** 持有 ACT-089~096 / **R-9.24**（已 active，元迴圈停機+離線反事實+主動脆弱性）；**Phase M** 持有 ACT-097~104 / **R-9.25**（已 active，組合級意圖自治+進步性監測+組合脆弱性）；**Phase N** 持有 ACT-105~110 / **R-9.26**（已 active，全域組合最佳化+NP-hard 搜尋形式化停機）；**Phase O** 持有 ACT-111~116 / **R-9.27**（已 active，自我調參的對抗式有界元最佳化）；**Phase P** 持有 ACT-117~122 / **R-9.28**（已 active，全評分器一體化自校準 + 跨評分器聯合反 Goodhart + 耦合感知聚合停機 CrossScorerChurnBounded）；**Phase Q** 持有 ACT-123~128 / **R-9.29**（已 active，價值維度的自我擴充 meta-meta：value_dimension_registry + 維度必要性反 Goodhart〔增量覆蓋 ∧ 非冗餘〕+ DimensionCardinalityBounded 維度基數有界停機 + 反 big-bang 本體論掌舵）；**Phase R** 持有 ACT-129~134 / **R-9.30**（已 active，價值維度語意的自我發明 + 退役聯動 meta-meta-meta：dimension_semantics_synthesizer 候選池外有界生成文法〔無界生成另證有界〕+ feature-keyed 必要性反 Goodhart + 自指 probe 守門〔反自利〕+ SwapCadenceBounded 退役聯動定基數旋轉有界停機 + 單調價值棘輪）；**Phase S** 持有 ACT-135~140 / **R-9.31**（已 active，生成文法詞彙的自我擴充 meta⁴ + 多維度批次退役聯動：vocabulary_genesis VOCAB 外有界詞彙生成文法〔更深無界生成另證有界〕+ feature-grounded 詞彙必要性反 Goodhart + 詞彙自指守門〔反自利〕+ VocabGenesisBounded 詞彙基數有界停機 + BatchSwapCadenceBounded 批次三鎖〔批次大小界 + 批次聚合棘輪 + 批次速率，批次旋轉有界停機〕）；**Phase T** 持有 ACT-141~146 / **R-9.32**（已 active，轉換算子文法的自我擴充 meta⁵：operator_genesis TRANSFORMS/OPS 外有界算子生成文法〔PRIMITIVES × COMBINATORS，更深無界生成另證有界〕+ feature-grounded 算子必要性反 Goodhart + 算子自指守門〔反自利〕+ OperatorGenesisBounded 算子基數有界停機 + OperatorComputabilityBounded 算子可計算性〔全函式 + 有界步數 + 零遞迴零迴圈，把停機問題釘進自我擴充產物本身〕）；**Phase U** 持有 ACT-147~149 / **R-9.33**（已 active，組合算子文法的自我擴充 meta⁶：operator_alphabet_genesis PRIMITIVES/COMBINATORS 外有界字母表生成文法〔ATOM_REDUCERS × POST_MAPS + BINARY_ATOMS，更深無界生成另證有界〕+ feature-grounded 字母必要性反 Goodhart + 字母自指守門〔反自利〕+ AlphabetGenesisBounded 字母基數有界停機 + ComputabilityClosureBounded 可計算性閉包〔擴充字母表後 G(A') 整個算子代數全函式 + 有界步數 + 零遞迴零迴圈，把停機問題釘進自我擴充的生成規則本身〕）；**Phase V** 持有 ACT-150~152 / **R-9.34**（已 active，算子組合深度文法的自我擴充 meta⁷：operator_depth_genesis 深度 <=2 外有界深度生成文法〔有限深度-2 基底 × 一元鏈，鏈長 <= depth_limit-2，更深無界生成另證有界〕+ feature-grounded 深度必要性反 Goodhart + 深度自指守門〔反自利〕+ DepthGenesisBounded 深度算子基數有界停機 + DepthClosureBounded 深度可計算性閉包〔擴充深度後 G(A,depth) 整個深度算子代數全函式 + cost==depth<=step_max + 零遞迴零迴圈，把停機問題釘進自我擴充文法的結構性深度=步數參數本身，因 cost==depth 而最直接〕）；**Phase W** 持有 ACT-153~155 / **R-9.35**（已 active，算子間互遞迴文法的自我擴充 meta⁸：operator_recursion_genesis 非遞迴外有界互遞迴生成文法〔有限節點集 × 有限帶 rank 呼叫邊集，只生成 DAG ∨ 每邊嚴格遞減下有界 rank，更深無界生成另證有界〕+ feature-grounded 互遞迴必要性反 Goodhart + 互遞迴自指守門〔反自利〕+ RecursionGenesisBounded 互遞迴算子基數有界停機 + RecursionClosureBounded 良基停機證書〔呼叫圖帶良基 ranking function：每條呼叫邊嚴格遞減下有界 rank ⟹ 良基無環 ⟹ 終止（well_founded ∧ acyclic 雙證）+ fuel<=step_max + 整代數全函式 + 求值器零真遞迴零 while；把停機問題釘在可判定 vs 不可判定臨界線本身，device 之新在於用「呼叫圖上的 ranking function」承載 Phase V 線性深度鏈表達不出的分支/共享/重匯聚呼叫圖（見 fan）、取代「有界運算式樹深度」，不 admit 真正含環算子、侷限可證良基終止之全函式片段〕）；**Phase X** 持有 ACT-156~158 / **R-9.36**（已 active，具身接地接入 META_FSM：把元迴圈自我演化判定從合成語料勝率接地到具身評估器〔EMBODIED_GROUNDING_GATE：sdd-evaluator 沙箱實跑 + observability_query 客觀錯誤 + output_quality_scorer OQS〕+ embodied_grounding_oracle 具身增益判據〔OQS 不退步 ∧ 無新增 runtime_fail，generator 不可見對抗分離〕+ guard_embodied_grounding fail-closed〔與 TLA+ EmbodiedGroundingBounded 100% 同構：缺客觀 ExecutionObservation → MFSM_ESCALATION；沙箱硬 timeout → grounded_fail，FSM 不 wall-clock wait；guard 獨立重新計分不盲信 oracle 標籤〕+ EmbodiedGroundingBounded 不增軸不增狀態變數，把「真實沙箱可能 hang」這個具身接地引入的新不停機源封死；橫向接地不碰 meta⁹）。
