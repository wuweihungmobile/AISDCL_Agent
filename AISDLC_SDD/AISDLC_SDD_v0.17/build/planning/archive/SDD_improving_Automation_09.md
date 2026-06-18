# SDD 自動化進化藍圖 09 — Phase I：可信賴的規模化現實自治（Trustworthy Scaled Reality-Grounded Autonomy）

> **作者角色**：首席 AI 自動化架構師（Chief AI Automation Architect）
> **產出日期**：2026-05-31
> **對應 tag（規劃）**：`phase-i-tsg`
> **前置基線**：Phase H GAE（L5 Reality-Grounded，tag `phase-h-gae`，pytest 440 passed / chaos bounded_ratio=1.0 / FSM 30 狀態 / DockerBackend 真實執行接地）
> **驗證方法**：8 探針並行對「Anthropic 動態對抗框架 + OpenAI 智慧體優先環境」前沿思維做 **Post-Phase-H** 缺口稽核（workflow `sdd-l5plus-gap-audit`，16 agents / 634K subagent tokens），每個判定附 file:line 證據並經獨立 skeptic 對抗驗證、重新校準嚴重度
> **狀態**：✅ **全部已實作**（2026-06-01，tag `phase-i-tsg` → `phase-i-fleet`）— M1~M5（ACT-059~072）完成。
> - M1~M4（ACT-059~069）：三 Pillar 判官自審/系統增殖/可持續證明。
> - **EventuallyTerminal 已完整證明**（不再暫緩）：根因為原 .tla 未編碼 AUTO_COMPACT/HUB 的有界 re-entry（現實由 `MAX_AUTO_COMPACT_PER_STAGE` 強制有界）；加 `compact`/`hub` 有界計數器消除 wildcard 假 2-cycle 後，TLC 窮舉證 `EventuallyTerminal` + `ObservationsTransient` 全 PASS（Rule 9.21.7）。
> - **M5 艦隊並行已實作**（ACT-070~072）：track 維度 state key + sandbox namespacing、`fleet_orchestrator`（全域鎖序防死鎖 + textual/semantic 仲裁 + join）、parametric `FLEET_FSM.tla`（`pc[Feature]` + symmetry，TLC 證 LockMutex/NoPartialHold/AllEventuallyDone）。
> - 驗收：pytest 483 passed（+43）/ chaos 100 輪 bounded_ratio=1.0 / TLC SDD_FSM（safety+liveness）+ FLEET_FSM（parametric）雙 PASS / §6 e2e 三關攔截。詳見 CLAUDE.md Rule 9.21。

---

## 0. 終極結論（Executive Verdict）

| 維度 | 現況評級（Post-Phase-H） | 說明 |
|------|------------------------|------|
| **單軌閉環的現實接地** | ✅ **已達成（L5 Reality-Grounded）** | Phase H 補齊 G1~G8：DockerBackend 真實執行、生成-評估分離、測試合約談判、鷹架代謝、舵手交棒。單一 feature 的 SPEC→IMPL→EVAL 串行閉環，已能「按下執行鍵」並有界停機。 |
| **評估接地的「可信度」** | 🟠 **接地了，但沒人評估評估器** | Evaluator 第一次接觸現實，但這次接觸**本身不可信**：OQS 評分標準靜態不可校準、Test-Oracle 凍結後會 stale、執行非確定性（flaky）會污染裁決、執行器跑的是**自己生成的不可信程式碼**卻零隔離硬化。閉環接地了，但接地線可能通往一個會漂移、會被騙、會被入侵的判官。 |
| **自治的「規模」** | 🟠 **單軌、被動、只記失敗** | 系統是 single-track（一次一個 feature）、reactive-goal（人工種子驅動，不自選價值最高目標）、failure-only-learning（只結晶失敗 FPL→SLV，從不結晶成功）。它能可靠地「執行被給定的一件事」，但不能「並行做很多事」「自己決定先做哪件」「把成功變成永久能力」。 |
| **保證的「可持續性」** | 🟠 **證明在原地，現實在長大** | TLC 是 explicit-state 單軌 720-cell 模型，liveness 仍是 TODO；並行已在執行層（Evaluator 獨立 worktree）悄悄到場，形式化模型卻沒跟上。每加一個狀態都在打爆自己的證明——正是 Phase H 鷹架代謝想解決卻尚未對齊形式化層的張力。 |

**一句話診斷**：
> Phase H 讓機器**第一次、串行地、在可信地基上、按下了一次執行鍵**。Phase I 要問的是更難的問題：**它能不能在不可信的地基上、並行地、按下很多次執行鍵——而且既不盲信自己的判官、也不被執行結果的隨機性與惡意性擊穿，最後仍然優雅停機、仍然學習、仍然讓人類維持舵手而非被告警洪水淹沒？** Phase H 解決了「能不能接觸現實」；Phase I 解決「這次接觸**值不值得信任**，以及能不能**規模化**」。

---

## 1. `<thinking>` — 深度推理與漏洞挖掘

```
<thinking>

【第一性原理：Phase H 之後，閉環還缺什麼？】
Phase H 用「圖靈機紙帶 = 運行中的軟體」這個比喻補上了 I/O 通道（execution
grounding）。但我重讀那個比喻時發現它埋了一個未被檢視的假設：它假設「讀紙帶
的那隻手是可信的、讀一次就準的、只有一隻手」。Phase I 的八個洞，全部從拆解
這三個假設長出來：

  假設 A：「判官可信」  → 但 discriminator 也會過擬合（PI-2）
  假設 B：「讀一次就準」 → 但真實執行是非確定的（PI-3）
  假設 C：「只有一隻手」 → 但真實自治是艦隊規模（PI-1/PI-7）

再加上 Phase H 引入執行接地時，順手打開了三扇沒上鎖的門：
  - 跑的是「自己生成的不可信碼」，卻零隔離（PI-4 安全）
  - 生產現實只用「數字 SLO」回饋，功能性偏差被 schema 擋在門外（PI-5）
  - 只結晶失敗、把成功軌跡 FIFO 丟棄（PI-6 記憶）
  - 形式化證明還停在單軌，撐不住規模（PI-8）

【套用 Anthropic 對抗框架，挖最深的洞：誰評估評估器？（PI-2）】
GAN 的精髓從來不是「分離生成器與判別器」——那只是第一步。精髓是「兩者
共同演進」。Phase H 只做了一半：它防了 generator 過擬合（oracle 對 dev 不可
見，08.md:243），卻**完全沒防 discriminator 自己漂移**。讀 output_quality_
scorer.py：_WEIGHTS（0.40/0.25/0.20/0.15）、BLOCK_THRESHOLD=0.80 全是硬編碼
常數，score() 是純函式，無 record_calibration 入口（對比 path_cost.py:178-213
明明有完整校準鏈、ambiguity_scorer 有 invalidate_cache）。這意味著：

  - dev 只要學會「堆無意義但會過的測試」就能衝高 test_pass_rate（權重最大
    0.40）→ 這正是 GAN 的 mode collapse 在工程上的復現：生成器學會騙判別器。
  - 模型變強後 0.80 門檻過鬆，系統無法自察。
  - 更隱蔽的——Test-Oracle 在 TEST_CONTRACT_NEGOTIATED 凍結後（subagent_
    contract.py:371-379 record 字典無 frozen_spec_sha），當 spec 經 SPEC_AUDIT/
    DRIFT_OBSERVATION→SPEC_DRAFTING 演進，oracle 變 stale，評估器拿**舊考卷
    改新答案**，卻無任何新鮮度檢測。

這是最危險的洞：它不會讓系統「崩」，而是讓 EXECUTION_EVALUATION 在數十次
迭代後**悄悄退化成另一種 false-green**——Phase H 剛剛除掉的那個 stub 零觀測
false-green，會以「漂移的判官蓋章放行」的形式借屍還魂。Phase H 量化了「輸入
規格的模糊度」（AmbiguityScorer）也量化了「輸出的執行品質」（OQS），但它忘了
量化「量化器本身的可信度」。主觀標準量化必須是**動態、可校準、被監控的不變量**，
而不是凍結的常數。

【非確定性 vs 有界停機：Phase H 自己埋的地雷（PI-3，探針驗證階段失敗，我親自補）】
這個洞是 Phase H「接地」與 Rule 9「有界停機」的正面對撞，而且因為它太
反直覺，連稽核 workflow 的 verify 階段都沒能結構化它——但它恰恰是最該被看見
的。讀 sandbox_runner.py:107-125：DockerBackend.run() 是**單發執行**（跑一次、
取 exit code、解析摘要）。真實軟體執行是非確定的：flaky test、時間相依、網路
抖動、並發 race、記憶體在第 N 次才洩漏。一個 60% 機率通過的 flaky test 會發生
什麼？

  - 它時好時壞 → EXECUTION_EVALUATION 的 retry budget（EXEC_EVAL_LIMIT）被一個
    **本質隨機的訊號**消耗。
  - 更糟：TrajectoryPredictor 的 S1「同 pattern 連續失敗」會把 flaky 的隨機
    失敗誤判為「穩定失敗模式」，提早 switch_to_audit；或反之，隨機通過讓它
    永遠湊不滿信號，retry 燒到上限才停。
  - chaos_runner 的 FAULT_TYPES（STATE_CORRUPTION/RETRY_TAMPER/...）**沒有
    FLAKY_EVAL 這一型**——也就是說，框架引以為傲的「100 輪 bounded_ratio=1.0」
    從未在「執行結果本身隨機」的前提下被驗證過。Phase H 的有界停機證明，建立
    在「執行是確定函數」的假設上，而 Phase H 自己引入的真實容器執行打破了
    這個假設。

這不是能力缺口，是**正確性缺口**：它直接威脅 Phase I 之前所有 Phase 的招牌
（bounded halting）。flaky 必須被當作**第三種 verdict**（不是 pass、不是 fail，
是 FLAKY/inconclusive-nondeterministic），用「同輸入重跑 N 次取共識 + 不一致
即隔離」處理，而不是丟進 retry 迴圈裡當成 fail。

【OpenAI 環境防護：執行器自己成了攻擊面（PI-4）】
Phase H 最興奮的一刻——「按下執行鍵」——也是框架最脆弱的一刻。讀 sandbox_
runner.py:110：`docker run --rm <image> <test_cmd>`，唯一的安全控制是
wall-clock timeout。全檔 grep 零命中 --network none / --cap-drop / --read-only
/ --pids-limit / --memory / --user / --security-opt no-new-privileges / seccomp。
這個容器：以 root 跑、預設可出網、無資源上限、執行的是**Generator 生成的、
從未經人類審查的程式碼 + 它拉取的第三方相依套件**。

框架對「被開發的產品」做了完整 STRIDE（FSM_SECURITY.md、security-engineer
agent），卻對「現在會自動執行不可信 artifact 的執行器自己」**零威脅模型**。
這是經典的「燈下黑」：你替客戶的房子裝了防盜系統，自己的後門卻大開。一個
被污染的相依套件、一段會 phone-home 的生成碼、一份被注入的 spec——在零 jail
的容器裡都能直達 host 網路與權限。Phase H 把攻擊面從「文字規格」擴張到「任意
程式碼執行」，卻沒同步擴張威脅模型。引入 docker 時應該同步引入 docker 的
threat model，這是 L6 自治擴權前必補的安全前沿。

【現實只用數字說話：behavioral 偏差被擋在門外（PI-5）】
讀 production_monitor.py:143-160：validate_schema 強制 observed/target/
duration_minutes 三個**數值**欄位。這意味著生產現實只能用「P95 超標」「錯誤率
3%」這種數字進入閉環；而「API 回傳結構偏離契約」「業務流程順序錯了」「某個
業務不變量在生產被違反」這類**功能性 behavioral 偏差**——連 schema 都過不了，
直接被 quarantine。更深：slv_generator 的唯一輸入是人工撰寫的 FPL markdown
（slv_generator.py:55-57），生產真實行為**永遠進不了 learning 層**。OpenAI 講
「絕對可觀測性」，Phase H 卻把兩條現實通道刻意分離（08.md:293「pull 給生產 SLO、
query 給沙箱失敗」），讓「生產真實行為 → 可查詢 → 推理 → spec 演進」這條最重要
的閉環從未接上。Reality-Grounded 只做到了「開發期沙箱」，沒做到「交付後生產」。

【只會記仇，不會記恩：學習層的結構性不對稱（PI-6）】
這個洞最有 Karpathy 味道。整條學習迴路——FPL→SLV、scaffold_gc、hub mirror、
6 個 observation 態、nightly cron——**全部是失敗/漂移/成本導向**。scaffold_gc.py
的 audit_decision_trace 把軌跡標成 led_to_escalation/led_to_drift/productive，
但 productive（成功）的軌跡只被**計數**（line 145-148），從不被萃取。rule_loader
的 propose_graduation 只會 active→audit-only→deprecated 單向退化，沒有反向把
「反覆成功的 scaffold」固化成新能力。FPL-INDEX.md:12 甚至寫著「即使最終 PASS
也歸納為失敗模式」——框架**結構上沒有「成功模式庫」的概念**。

一個只記得失敗、把成功 FIFO 丟棄的系統，會永遠從零重新摸索已經解過的問題，
token 成本與失敗率無法隨經驗單調下降。Phase H 教會了系統「丟棄自己」（鷹架
代謝的減法），但代謝是雙向的——生命同時需要分解代謝（退役）與合成代謝（結晶）。
缺了合成代謝，這個系統會越活越瘦，而不是越活越強。對應 Voyager 的 skill
library：成功必須結晶成可複用技能。

【自治的天花板：執行給定目標 vs 自選價值目標 + 人類注意力預算（PI-7）】
真正的 autonomy 不只是 task execution，是 goal selection。讀 transition_rules.py:
13-16：happy-path 入口 INIT→SCENARIO_DETECT→AGENT_LOAD→SPEC_DRAFTING——系統
一啟動就假設「做哪個 spec」已由人工給定。系統內唯一的 ROI（scaffold_gc 的
catch/fire）衡量的是治理規則價值，不是 feature 商業價值。系統能完美執行被指派
的任務，卻不能自主決定「在 backlog 裡先做哪個價值最高」。

對偶的另一面更隱蔽：Phase H 的 steersman_renderer 把單一事件的交棒做得很漂亮，
但讀 snapshot.py:165-241，save_abort_report 是 one-event-one-report，無 severity
排序、無跨事件去重、無批次彙總。timeout_checker 只有單實例的 72h/168h 逾時。
這意味著：**艦隊規模下，人類會被獨立 abort 報告淹沒**。Rule 9.2 給了 token 一個
預算，卻沒給「人類注意力」這個更稀缺的資源任何預算。當 N 個實例並行 escalate，
未分級/批次/去重的告警洪水會把人類從「設計舵手」沖回「告警分類員」——這正是
Phase H 舵手交棒想避免的降級，只是換了個規模才發生。（公道話：production_
monitor.py 已有成熟的 24h rolling-window + 去重先例，attention budget 應複用它
而非重造。）

【形式化證明撐不住現實的長大（PI-8）】
讀 SDD_FSM.tla:31：`VARIABLES <<state, retry, recovery>>`——三個純量。SDD_FSM.cfg
狀態空間硬編碼 30×6×4=720 cells。這對當前單軌完全 sound，但有兩個裂縫：
  - 並行已經悄悄到場：sdd-evaluator 在獨立 worktree 啟動沙箱，事實上的並行
    執行已存在，但 FSM/TLA 仍只描述單一 current_state 軌道。一旦 Phase I 走向
    多 feature 並行，explicit-state TLC 會狀態爆炸。
  - liveness 還是 TODO：SDD_FSM.cfg:19-26 的 EventuallyTerminal/Observations
    Transient 仍是註解，只 check 4 條 safety invariant。框架的招牌「bounded
    halting」的 liveness 部分，其實**從未被機器證明**（chaos 100 輪是經驗性、
    非窮舉）。
而且——這是 Phase I 最反身性的張力——上面七個洞的修復方案，幾乎每個都想加
新 FSM 狀態（EVALUATOR_AUDIT、SANDBOX_HARDENING_GATE、PRODUCTION_BEHAVIORAL_
SIGNAL、MEMORY_CONSOLIDATION、BACKLOG_PRIORITIZED、MONITOR_VIOLATION...）。
如果照單全收，FSM 會從 30 膨脹到 ~40，每加一個就打爆既有 TLC 證明。這正是
08.md:94-95 自己點出的「只會長不會瘦的系統會被自己的鷹架壓垮」。所以 Phase I
不能是又一輪純加法——它必須先讓「證明能隨狀態增長而維持」（runtime monitor
synthesis + parametric proof），加新狀態這件事本身才可持續。Pillar C 不是
可選項，是讓其他所有 Pillar 能安全落地的地基。

【收斂：八個洞，三條主軸】
Pillar A 可信接地：PI-2（誰評估評估器）+ PI-3（非確定性 vs 停機）+ PI-4（自身安全）
  → 「這次接觸現實，值得信任嗎？」
Pillar B 規模增殖：PI-1（艦隊並行）+ PI-7（價值目標 + 注意力預算）+ PI-6（成功
  結晶）+ PI-5（生產 behavioral 回饋）→ 「能不能並行、自選、越活越強？」
Pillar C 可持續證明：PI-8（runtime monitor + parametric + liveness）
  → 「現實長大時，停機保證還撐得住嗎？」

主軸：Phase H 讓系統「能接觸現實」；Phase I 讓系統「**值得信任地、規模化地**
接觸現實」。三件事——讓判官自審（A）、讓系統增殖（B）、讓證明可持續（C）。

【自我驗證協議的新極端案例】
08.md 跑過「spec 寫錯」。Phase I 該跑一個正中三大新洞的案例：
**一段含 flaky test（60% 通過）+ 會 phone-home 的相依套件的生成碼，餵給一個
已悄悄漂移的 OQS。** 這個案例同時觸發 PI-2（漂移判官）+ PI-3（flaky）+ PI-4
（惡意執行）。若 Phase I 優化後的流程能擋下它、優雅停機、給人類精準舵手請求，
則三大 Pillar 的協同得證。詳見 §6。

</thinking>
```

---

## 2. 缺口矩陣（Verified Gap Matrix）

> 全部經獨立 skeptic 對抗驗證；severity 為驗證後校準值（括號內為探針初判）。PI-3 因稽核 workflow 的 verify 階段未回傳結構化輸出而被丟棄，由架構師依 `sandbox_runner.py` 一手證據親自補回並標註。

| ID | 缺口 | Pillar | 對應前沿思維 | 判定 | 校準後嚴重度 | 核心證據 |
|----|------|--------|------------|------|------------|---------|
| **PI-2** | 誰評估評估器：OQS 評分標準不可校準、Test-Oracle 凍結後無新鮮度檢測 | A 可信接地 | Anthropic：生成-評估**共同演進**（discriminator 也會過擬合）；主觀標準量化的**動態性** | ✅ confirmed | 🔴 **critical→high** | `output_quality_scorer.py:15-26,60` 權重/門檻硬編碼、無 record_calibration（對比 `path_cost.py:178-213` 有）；`subagent_contract.py:371-379` oracle record 無 frozen_spec_sha；`test_phase_h.py` grep oracle/stale/calibrat/drift 零命中 |
| **PI-3** | 非確定性執行威脅有界停機：sandbox 單發執行、無 flaky 隔離、chaos 無 FLAKY 故障型 | A 可信接地 | Phase H 接地 × Rule 9 有界停機的正面對撞（正確性缺口） | ✅ confirmed（架構師補） | 🔴 **high** | `sandbox_runner.py:107-125` DockerBackend.run 單發、唯一控制是 timeout；`chaos_runner` FAULT_TYPES 無 FLAKY_EVAL；EXECUTION_EVALUATION retry budget 會被隨機訊號污染、TrajectoryPredictor S1 會誤判 flaky 為穩定模式 |
| **PI-4** | 自治執行迴圈無 STRIDE：執行「自己生成的不可信碼」零隔離硬化、無 supply-chain/注入防護 | A 可信接地 | OpenAI：智慧體優先**環境的安全維度** | ✅ confirmed | 🔴 **high** | `sandbox_runner.py:110-125` `docker run --rm` 無 --network none/--cap-drop/--read-only/--user/--memory/seccomp，以 root + 可出網 + 無資源上限執行；`FSM_SECURITY.md` STRIDE 對象僅「產品」非「執行器自己」；無 image allow-list/spec 簽章/lockfile 雜湊；`observability_query` 裸 json.loads 不可信容器日誌（telemetry 注入面） |
| **PI-5** | 現實→規格閉環只覆蓋數值 SLO，behavioral 偏差被 schema 擋門外、無 telemetry→FPL→SLV 鏈 | B 規模增殖 | OpenAI：絕對可觀測性；Anthropic：讓現實反哺框架 | ✅ confirmed | 🟠 **high** | `production_monitor.py:143-160` REQUIRED_FIELDS 強制三數值欄、`:234-245` 非數值 return None；`slv_generator.py:55-57` 唯一輸入是人工 FPL；`fsm_runtime.py:1103-1119` PRODUCTION_SIGNAL 出口僅 {SPEC_DRAFTING,RELEASE} 無法導向 LEARNING_COMMIT |
| **PI-6** | 學習層只結晶失敗（FPL→SLV），無成功 episode→可複用技能/正向 scaffold 的 sleep phase | B 規模增殖 | Anthropic：scaffold 隨經驗**升級**而非僅退役；Voyager skill library / 記憶鞏固 | ✅ confirmed | 🟠 **high**（能力缺口） | `scaffold_gc.py:74-103,145-148` productive 軌跡僅計數不萃取；`rule_loader.py:150-167` propose_graduation 單向退化無反向固化；`slv_generator.py:263-312` 只接受單一 FPL；`FPL-INDEX.md:11-13` 連最終成功也只導向失敗庫；無 skill-patterns/ 目錄、無 sleep-phase cron |
| **PI-7** | 價值驅動目標自治缺失 + 艦隊規模人類注意力預算缺口 | B 規模增殖 | OpenAI：維持人類「設計舵手」高度（注意力是有限預算）；Anthropic：autonomy=goal selection 非僅 execution | ✅ confirmed | 🟠 **high** | `transition_rules.py:13-16` 入口假設目標已給定、無 value/ROI 排序態；`snapshot.py:165-241` save_abort 一事一報、無 severity/去重/批次（同日同 category 還會**覆寫**遺失審計）；`timeout_checker.py` 僅單實例逾時；（`production_monitor.py` 已有 rolling-window 去重先例可複用）|
| **PI-8** | 形式化保證不可擴展：explicit-state 單軌 TLC、無 runtime monitor synthesis、liveness 未證 | C 可持續證明 | Anthropic：框架隨模型變強要能演進**而非被自己的證明壓垮** | ✅ confirmed | 🟡 **high→medium** | `SDD_FSM.tla:31` 三純量無 feature index；`SDD_FSM.cfg:19-31` 720-cell 硬編碼、EventuallyTerminal/ObservationsTransient 仍 TODO；`fsm_runtime.py:105` assert_transition 僅驗邊合法性、四條 safety invariant 未編譯成 runtime assertion；並行已在 worktree 層出現但模型未跟上 |
| **PI-1** | FSM 與執行接地皆單軌，缺艦隊/組合級並行編排、跨軌 spec 依賴鎖、merge-conflict 回饋 | B 規模增殖 | Anthropic：orchestrator-worker 大規模編排；OpenAI：並行下的環境防護 | ✅ confirmed | 🟡 **high→medium**（擴展天花板，非正確性缺陷；條件性） | `state_loader.py:32-33,252` 以 project 為唯一 key 無 track 維度；`transition_rules.py:13-121` 單一線性管線；`sandbox_runner.py:107-125` 無 container name/port namespacing、N 軌同跑撞 port；`SDD_FSM.tla:31` scalar state 無法表達 N-track |

> **誠實標註（驗證階段校準）**：
> - **PI-1 / PI-8 並行部分**降為 medium：並行已在「執行/worktree 層」出現，但仍匯流回單一 `current_state`，故現行模型對**當前** runtime 仍 sound。這是「未來擴展懸崖」而非「當下正確性破洞」，且**唯有使用者明確要求「同一專案多 feature 並行自治」時才浮現**——屬條件性前沿，不應與 Pillar A 的當下風險同等急迫。
> - **PI-6** 為**能力缺口**（效率/複用）非正確性/安全缺陷：缺它不會錯誤停機或錯誤裁決，但會讓系統無法越活越強。
> - **PI-3** 是八洞中唯一的**正確性缺口**且直接威脅招牌（bounded halting），但稽核 workflow 的 verify 階段恰好沒能結構化它——這本身是個教訓：最反直覺的洞最容易被自動化流程漏掉，需人工補位（呼應 Rule 9.8 對抗驗證的必要性）。

---

## 3. Agentic 閉環狀態機設計（Pillar A/B/C 三層演進）

### 3.1 核心架構轉變：從「單軌可信閉環」到「自審視·可規模化閉環」

```
                         ┌──────────────────────────────────────────────┐
   Pillar C（地基）       │   🆕 RUNTIME MONITOR（從 .tla invariant 合成）  │  ← 補 PI-8
   ─────────────         │   每次 transition 後執行期斷言 TypeOK/Retry-    │
   證明可持續              │   Bounded/RecoveryBounded/NotInBothSets        │
                         │   違反 → MONITOR_VIOLATION → ESCALATION         │
                         └────────────────────┬─────────────────────────┘
                                              │ 守護所有狀態轉移
        ┌──────────────────────────────────────────────────────────────────────┐
        │                       Pillar A — 可信的評估接地                          │
        │                                                                        │
        │  IMPLEMENTATION                                                        │
        │      │                                                                 │
        │      ▼                                                                 │
        │  🆕 SANDBOX_HARDENING_GATE（補 PI-4）                                   │
        │      image allow-list + spec 簽章 + 依賴 lockfile 雜湊                   │
        │      fail → ESCALATION（sub_type=sandbox_policy_violation/structural）   │
        │      │ pass                                                            │
        │      ▼                                                                 │
        │  EXECUTION_EVALUATION（強化：補 PI-3 非確定性）                          │
        │      ├ 同輸入重跑 N 次取共識（hermetic）                                 │
        │      ├ 不一致 → 第三 verdict = FLAKY（不計 pass/fail，隔離）              │
        │      └ 確定性結果 → OQS                                                 │
        │      │                                                                 │
        │      ▼ verdict                                                         │
        │  🆕 EVALUATOR_AUDIT（observation，補 PI-2「誰評估評估器」）              │
        │      OQS 校準鏈（verdict↔生產回饋配對）+ Oracle 新鮮度檢測               │
        │      漂移 → 人工 recalibrate gate（bump SCORER_VERSION）                 │
        └──────────────────────────────────────────────────────────────────────┘
                                              │ 可信 verdict
        ┌──────────────────────────────────────────────────────────────────────┐
        │                       Pillar B — 規模化的自治                            │
        │                                                                        │
        │  🆕 BACKLOG_PRIORITIZED（補 PI-7 目標自治）  人工 signoff 選最高 ROI      │
        │  🆕 MEMORY_CONSOLIDATION（補 PI-6 成功結晶） nightly sleep-phase         │
        │  🆕 PRODUCTION_BEHAVIORAL_SIGNAL（補 PI-5）  生產 behavioral→FPL→SLV      │
        │  🆕 attention_router（補 PI-7 注意力預算）   分級/去重/批次 digest        │
        │  ⏳ FLEET（補 PI-1，條件性：須 Pillar C parametric 證明先落地）           │
        └──────────────────────────────────────────────────────────────────────┘
```

### 3.2 新增 / 修改的 FSM 狀態（依 Pillar 與優先序）

| 狀態 | Pillar | 類型 | 入口 | 出口 | 補的洞 |
|------|--------|------|------|------|--------|
| **`MONITOR_VIOLATION`** | C | observation（非阻塞） | runtime monitor 偵測 invariant 破壞時 | → `ESCALATION`（不可恢復）或 resume_state | PI-8 |
| **`SANDBOX_HARDENING_GATE`** | A | gatekeep（阻塞） | `IMPLEMENTATION` → 此 → `EXECUTION_EVALUATION` | pass→`EXECUTION_EVALUATION`；fail→`ESCALATION`（sandbox_policy_violation） | PI-4 |
| **`EVALUATOR_AUDIT`** | A | observation（非阻塞 transient） | `{EXECUTION_EVALUATION, PRODUCTION_SIGNAL, DRIFT_OBSERVATION}` | continue→resume_state；recalibrate→人工 gate 後 `RELEASE`/`SPEC_DRAFTING` | PI-2 |
| **`MEMORY_CONSOLIDATION`** | B | observation（非阻塞 transient） | nightly sleep-phase cron / `LEARNING_COMMIT`/`RELEASE` 後 | `{RELEASE, SPEC_DRAFTING}` | PI-6 |
| **`PRODUCTION_BEHAVIORAL_SIGNAL`** | B | observation（非阻塞 transient） | `{RELEASE, RELEASE_READY, PRODUCTION_SIGNAL}` | `{SPEC_DRAFTING, RELEASE, LEARNING_COMMIT}` | PI-5 |
| **`BACKLOG_PRIORITIZED`** | B | gatekeep（人工 signoff） | 人工候選 spec/epic 池 | → `SPEC_DRAFTING`（選定最高 ROI） | PI-7 |
| ⏳ `FLEET_ORCHESTRATION` / `SPEC_DEPENDENCY_LOCK` / `MERGE_ARBITRATION` / `PARALLEL_TRACK_JOIN` | B/C | observation + gatekeep | （條件性，見 §5.4） | — | PI-1 |

> **PI-3 不新增狀態**：flaky 處理內建於 `EXECUTION_EVALUATION` 的執行策略（重跑取共識 + FLAKY 第三 verdict），並在 `chaos_runner` 新增 `FLAKY_EVAL` 故障型驗證有界性——避免狀態爆炸，符合 Pillar C 紀律。
> **PI-7 attention budget 不新增狀態**：為橫切 escalation 渲染層，在 `ESCALATION`/`ESCALATION_FINAL`/`HUMAN_PENDING` 出口接線 `attention_router`。

### 3.3 關鍵轉換規則（接續 `transition_rules._HAPPY_PATH`，**必須同步 SDD_FSM.tla — Rule 9.18.1**）

```python
# Phase I 新增（規劃）— 寫入 _HAPPY_PATH 時須同步 .tla 並重跑 TLC
# Pillar A
_HAPPY_PATH["IMPLEMENTATION"] = {"PR_REVIEW", "SPEC_AUDIT", "SANDBOX_HARDENING_GATE"}  # 改：插入硬化閘
_HAPPY_PATH["SANDBOX_HARDENING_GATE"] = {"EXECUTION_EVALUATION", "ESCALATION"}
# EXECUTION_EVALUATION 出口維持不變（PI-3 為內部執行策略，非新邊）
OBSERVATION_STATES |= {"EVALUATOR_AUDIT", "MONITOR_VIOLATION",
                       "MEMORY_CONSOLIDATION", "PRODUCTION_BEHAVIORAL_SIGNAL"}
_HAPPY_PATH["EVALUATOR_AUDIT"] = {"EXECUTION_EVALUATION", "RELEASE", "SPEC_DRAFTING"}
# Pillar C
_HAPPY_PATH["MONITOR_VIOLATION"] = {"ESCALATION"}  # runtime monitor 補位：違反即升級
# Pillar B
_HAPPY_PATH["BACKLOG_PRIORITIZED"] = {"SPEC_DRAFTING"}
_HAPPY_PATH["MEMORY_CONSOLIDATION"] = {"RELEASE", "SPEC_DRAFTING"}
_HAPPY_PATH["PRODUCTION_BEHAVIORAL_SIGNAL"] = {"SPEC_DRAFTING", "RELEASE", "LEARNING_COMMIT"}
```

> **有界性保證（必須）**：`EXECUTION_EVALUATION` 沿用 `EXEC_EVAL_LIMIT=3` + flaky 重跑次數 `FLAKY_RERUN_N=5`（硬上限，避免重跑本身變無界）；所有 observation 態不阻塞、不可進 Terminals（Rule 9.18.4）。新狀態加入後**必重跑 TLC** 且**必須先有 Pillar C 的 runtime monitor 補位**——否則新增狀態會在 explicit-state 模型重算 reachable 前留下證明空窗。Phase I 的狀態增量本身就是「系統能否在不打爆證明的前提下成長」的試金石。

### 3.4 生成–評估的「共同演進」硬約束（補 PI-2，深化 Phase H 的 §3.4）

Phase H 已立下「Generator 看不到 oracle」防 generator 過擬合。Phase I 補上對稱的另一半——**Evaluator 自己也會過擬合/漂移，必須被監控**：

1. **OQS 校準回饋鏈**：每次 `EXECUTION_EVALUATION` verdict 與下游真實結果（`PR_REVIEW` 是否回退、`PRODUCTION_SIGNAL`/`PRODUCTION_BEHAVIORAL_SIGNAL` 是否在同 AC 觸發違反）配對，rolling-N 計命中率；連續 N 次「OQS pass 但生產違反」→ 寫 `OQS-DRIFT-{date}.yaml`、進 `EVALUATOR_AUDIT`、要求人工調 `_WEIGHTS`/`BLOCK_THRESHOLD` 並 bump `SCORER_VERSION`（嚴格沿用 `path_cost.record_calibration` + Rule 9.16.4 invalidate 慣例）。
2. **Oracle 新鮮度戳記**：`record_test_standard_agreement` 加 `frozen_spec_sha`；進 `EXECUTION_EVALUATION` 前比對當前 spec sha 與 oracle 凍結 sha，不符 → oracle stale → advisory 提示回 `TEST_CONTRACT_NEGOTIATED` 重談判（差異閾值化，僅實質影響該 AC 的變更才判 stale，避免抖動）。
3. **評分基準永不自動改**：OQS 權重/門檻的調整一律經人工 gate（仿 `rule_loader.set_maturity(reviewed_by=)`）——否則 discriminator 可被間接 game（自我放鬆門檻）。
4. **flaky 不污染判官（PI-3 協同）**：FLAKY verdict 不進 OQS 計分，也不進 OQS 校準樣本——隨機訊號既不該蓋章放行，也不該污染校準。

---

## 4. 環境建構與記憶體管理策略

### 4.1 執行接地的可信化（Pillar A，補 PI-3 + PI-4）— 接地線本身要硬化、要去隨機

**問題**：Phase H 的接地是「單發、零 jail、執行不可信碼」。接地線本身既不安全也不確定。

**方案：Hermetic + Hardened Sandbox**

```
tools/fsm_runtime/sandbox_runner.py（強化）
  DockerBackend.run() 預設安全 profile（補 PI-4）：
    --network none（UI/integration 需網路時改專屬 egress-allowlist 內部橋接）
    --cap-drop=ALL  --read-only + 受控 tmpfs  --pids-limit
    --memory/--cpus  --user（非 root）  --security-opt no-new-privileges + seccomp
    image 走 allow-list；test_cmd/start_cmd 走白名單而非任意 sh -c
  flaky 處理（補 PI-3）：
    同 SandboxSpec 重跑 FLAKY_RERUN_N=5 → 全 pass=PASS / 全 fail=FAIL /
    混合=FLAKY（第三 verdict，隔離不計分，寫 build/reports/eval/FLAKY-{date}.yaml）

tools/fsm_runtime/loop_threat_model.py（新）+ governance/rules/R-SELF-STRIDE.yaml
  對「執行器自己」的 6 類 STRIDE 控制與斷言（漸進揭露，rule_loader 於
  EXECUTION_EVALUATION/SANDBOX_HARDENING_GATE 載入）
  + 依賴 lockfile 雜湊鎖定（supply-chain）+ spec 簽章驗證
  + SLV-012「自治迴圈安全不變量」（trust_level=proposed→人工 review 升 verified）
```

- `observability_query` 對讀入的 ndjson 做來源標記與 schema 驗證（防被污染 telemetry 注入 Evaluator 推理）。
- 安全/確定性的環境差異風險（darwin vs CI linux 的 seccomp/cap-drop 行為不一致）由分級 profile + CI 環境矩陣吸收，避免引入新的非確定性與 Pillar C 的有界停機目標衝突。

### 4.2 記憶體管理：從「只記失敗」到「記且結晶成功」（Pillar B，補 PI-6）

- **保留**並肯定既有：stage-compaction / CONTEXT-SNAPSHOT / decision_trace（active 50 + FIFO）/ RESUME_VERIFICATION——Phase H 強項，不動。
- **新增成功模式庫（與失敗鏈對稱）**：

```
knowledge/skill-patterns/SPL-NNN.yaml    ← 與 failure-patterns/FPL 對稱的「成功技能庫」
   schema: trigger_states / abstracted_steps（多 productive episode 聚合）/
           reuse_count / provenance(source_episodes[]) / trust_level（三階）
tools/fsm_runtime/spl_consolidator.py    ← 掃 decision_trace(+flushed)，對 productive
   軌跡用 pattern_matcher.is_same_pattern 聚類（沿用 ACT-021），≥N 次同模式成功
   → propose trust_level=proposed 的 SPL 草案（人工 verified gate，禁自動 verified）
```

- **decision_trace flush 改為「先嘗試結晶再丟棄」**：成功訊號不再永久遺失（補 §4.2 的記憶回收面）。
- **反向 graduation**：`rule_loader` 對 catch/fire ROI 高且穩定的 scaffold，可 propose 為「固化技能」（仍經 `set_maturity(reviewed_by=)` 人工 gate）——讓鷹架代謝從**單向減法**升級為**雙向代謝**（退役 + 結晶）。
- **與 SCAFFOLD_GC 的優先序**：退役提案 > 結晶提案（避免剛固化又被退役震盪）。

### 4.3 運行時可觀測性：從「沙箱失敗根因」延伸到「生產真實行為」（Pillar B，補 PI-5）

**設計原則**：嚴守 OPEN-10.6「禁 HTTP endpoint」，但讓**生產的功能性現實**也能進閉環。

```
data/observability/production/*.ndjson   ← 生產遙測落地（file-based pull，沿用 OPEN-10.6）
tools/fsm_runtime/observability_query.py（擴）  ← 資料源從 sandbox-only 擴成可指向 production/
tools/fsm_runtime/behavioral_drift_scorer.py（新）
   比對生產遙測 vs 凍結 AC/OpenAPI/INV，量化功能性偏差 0~1
   divergence_kind ∈ {contract_shape, ordering, invariant_violation, missing_branch}
   v1 限 rule-based 結構比對（保確定性零成本，呼應 ambiguity_scorer v1 原則）
tools/fsm_runtime/production_to_fpl.py（新）
   同一 behavioral divergence 窗口內 ≥3 次 → 自動生成 FPL-NNN 草案
   （source=PROD-auto-generated，trust_level=proposed，advisory-only per Rule 9.11.3）
   → 餵入既有 slv_generator.propose_slv_from_fpl → SLV/AC 草案 → 人工 review 升 verified
```

- 打通「生產真實行為 → 可查詢 drill-down → FPL → SLV/新 AC」單一閉環，全程 advisory + 人工 gate，不破壞既有 NFR pull 與沙箱 query 契約。
- **明確區隔**：`drift_monitor.py` 是 commit-time 靜態 code↔spec diff；`behavioral_drift_scorer` 是生產 runtime 行為 drift——資料源不同，不可混為一談。

### 4.4 不變量防護欄：從「設計時證明」到「執行期 monitor」（Pillar C，補 PI-8）

- 既有 SLV-001~011 + AmbiguityScorer + OQS 保留。
- **新增 runtime monitor synthesis（價值最高、成本最低，建議優先）**：

```
tools/fsm_runtime/spec_monitor.py（新）
   從 SDD_FSM.tla 的 4 條 safety invariant（TypeOK/RetryBounded/RecoveryBounded/
   NotInBothSets）自動編譯成執行期 assertion，掛在 FSMRuntime.transition() 每次轉移後；
   違反 → 寫 build/reports/fsm/MONITOR-VIOLATION-*.yaml → 轉 MONITOR_VIOLATION → ESCALATION
```

- 這補上「設計時 TLC 證明」與「執行期實際轉移」之間的脫鉤：目前 retry/recovery 上限靠手寫 imperative if-check（`fsm_runtime.py:178`、`auto_recovery.py:107/113`），可與 .tla 靜默漂移；runtime monitor 讓**證明與執行對齊**成為持續性質而非一次性。
- **補齊 liveness**：在 .tla 對關鍵 progress transition 加 `SF_vars`，啟用 `EventuallyTerminal`/`ObservationsTransient`——把「bounded halting」從口號變成被 check 的 property。

---

## 5. 終極優化藍圖 — 升級至 L6 自治（含自審、增殖、可持續保證）

### 5.1 三 Pillar 達成判準

| Pillar | 判準 | 現況（L5 Reality-Grounded） | Phase I 目標 |
|--------|------|---------------------------|-------------|
| **A 可信接地** | 評估器自審 | OQS/oracle 凍結即終局、無校準 | ✅ OQS 校準鏈 + oracle 新鮮度 + EVALUATOR_AUDIT |
| | 執行去隨機 | 單發執行，flaky 污染 retry | ✅ hermetic 重跑取共識 + FLAKY 第三 verdict + chaos FLAKY 故障型 |
| | 執行器安全 | 零 jail 跑不可信碼 | ✅ 硬化 profile + SANDBOX_HARDENING_GATE + loop self-STRIDE + supply-chain 鎖 |
| **B 規模增殖** | 成功結晶 | 只記失敗，成功 FIFO 丟棄 | ✅ SPL 技能庫 + spl_consolidator + MEMORY_CONSOLIDATION sleep-phase + 反向 graduation |
| | 生產 behavioral 回饋 | 只認數值 SLO | ✅ behavioral_drift_scorer + production_to_fpl + PRODUCTION_BEHAVIORAL_SIGNAL |
| | 目標自治 | 人工種子驅動 | ✅ value_planner + BACKLOG_PRIORITIZED（人工 signoff gate）|
| | 注意力預算 | 一事一報、會淹沒 | ✅ attention_router（分級/去重/批次 digest，複用 production_monitor rolling-window）|
| | 艦隊並行 | 單軌 | ⏳ 條件性（見 §5.4，須 Pillar C 先落地）|
| **C 可持續證明** | runtime monitor | 設計時↔執行期脫鉤 | ✅ spec_monitor 從 .tla 合成執行期 assertion + MONITOR_VIOLATION |
| | liveness | TODO M5 v2 | ✅ 補 SF_vars 啟用 EventuallyTerminal |
| | parametric proof | explicit-state 單軌 | ⏳ 條件性（僅在艦隊並行落地時，Apalache）|

### 5.2 鷹架代謝的完成式：雙向代謝（補 PI-6，深化 Phase H §5.1）

Phase H 教會系統「分解代謝」（退役過時鷹架）。Phase I 補上「合成代謝」（結晶成功經驗）。**雙向代謝**讓系統真正活著：

| 方向 | 機制 | Phase | 落地 |
|------|------|-------|------|
| 分解（減法） | Scaffold ROI + Rule Graduation（active→audit-only→deprecated） | H ✅ | `scaffold_gc` / `rule_loader.propose_graduation` |
| **合成（加法）** | **Success Crystallization（productive episode→SPL→反向 graduation）** | **I 🆕** | `spl_consolidator` / `rule_loader` 反向固化 |

> **與形式化驗證協同**：合成代謝**會加狀態/規則**，這正是 PI-8 警告的「打爆證明」風險的試金石。所以 Pillar C（runtime monitor + parametric）必須與 Pillar B 同步或先行——這是 Phase I 三 Pillar 不可拆開單做的根本原因。

### 5.3 人類舵手協作介面：從「單事件交棒」到「艦隊級注意力治理」（補 PI-7）

Phase H 的 steersman_renderer 把**單一事件**交棒做到尊嚴級。Phase I 補上**規模下**的注意力治理：

```
tools/fsm_runtime/attention_budget.py（新）— Rule 9.2 token budget 的對偶
  attention_router：
    ① severity 分級（復用 diagnostic.category：structural > transient + retry 接近度）
    ② 同 capability_gap/sub_type 去重合併（復用 pattern_matcher.is_same_pattern）
    ③ 批次彙總成單一 DIGEST-{date}.md（top-N by severity，其餘折疊）
    ④ per-window attention budget（如每 24h 最多 N 個 P0），超量自動降級非 P0 為 digest-only
  硬白名單：P0/structural 永不被 budget 降級或折疊（類比 Rule 9.14.3）
  save_abort_report 改為先寫 raw event（timestamp/uuid 後綴，修正同日同 category 覆寫
    的審計遺失點）再經 router 產 digest；raw 為底層 audit、digest 為人類入口
```

- **複用而非重造**：`production_monitor.py` 已有成熟的 24h rolling-window + persistent_threshold=3 + 同 key 去重——attention_router 直接泛化此機制到 abort/escalation/reminder 通道，降風險、維持架構一致性。
- **價值目標自治（advisory）**：`value_planner.py` v1 rule-based 評分 `business_value × confidence / estimated_cost`（cost 復用 `path_cost`、不確定性復用 `ambiguity_scorer`），輸出 `BACKLOG-RANK-{date}.yaml`，**人工 signoff 後才選定**——value model 只排序不裁決，嚴守人類設計舵手 gate。

### 5.4 艦隊並行：條件性前沿（補 PI-1，明確劃為後段）

> **架構紀律**：PI-1/PI-8 並行部分經驗證降為 medium、定性為「擴展天花板，非當下正確性缺陷」。**唯有使用者明確要求「同一專案多 feature 並行自治」時才啟動**，且**必須先完成 Pillar C 的 parametric proof**，否則加軌即狀態爆炸。

| 子項 | 局部嚴重度 | 觸發前提 |
|------|----------|---------|
| Track 維度 state key（`FSM-STATE-{project}-{track_id}.yaml`）+ sandbox container name/port namespacing | medium | 多 feature 並行需求 |
| `SPEC_DEPENDENCY_LOCK`（跨軌共享 spec 區段 advisory lock + 全域鎖序防死鎖） | high（條件性） | 並行落地後 |
| `MERGE_ARBITRATION`（試 merge，textual conflict→IMPLEMENTATION、semantic→SPEC_AUDIT） | high（條件性） | 並行落地後 |
| Apalache parametric TLA（VARIABLES `state[Feature]`，symmetry reduction） | 研究級 | 真要 N-track FSM 時 |

---

## 6. 自我驗證協議重演（新極端案例：flaky + 惡意碼 + 漂移判官）

**案例**：Generator 產出一段含 **flaky test（60% 通過）** + **會 phone-home 的相依套件**的程式碼，餵給一個 **OQS 已悄悄漂移**（過去 N 次 pass 但生產違反）的評估器。此案例同時引爆 PI-2 + PI-3 + PI-4。

**Phase I 優化前（僅 Phase H）**：
```
sandbox 單發執行 → flaky test 恰好通過 → OQS（已漂移、門檻過鬆）判 pass
  → false-green 放行；同時容器以 root + 可出網，相依套件 phone-home 滲出資料
  → 閉環「成功」→ 交付一個既壞又被入侵的軟體。
（或 flaky 恰好失敗 → EXECUTION_EVALUATION retry budget 被隨機訊號燒乾、
 TrajectoryPredictor 誤判，停機但浪費 token 且根因錯誤。）
```

**Phase I 優化後（三 Pillar 協同）**：
```
1. SANDBOX_HARDENING_GATE（PI-4）：`--network none` 阻斷 phone-home；
   supply-chain lockfile 雜湊不符 → fail → ESCALATION
   （DiagnosticAgent sub_type=sandbox_policy_violation/structural，不可 auto-recover）。
   ✅ 惡意碼在「按下執行鍵之前」就被擋下。
2. 若改用合法依賴通過硬化閘 → EXECUTION_EVALUATION 重跑 5 次（PI-3 hermetic）：
   3/5 通過 → 判 FLAKY（第三 verdict）→ 隔離、不計分、不進 retry 迴圈、不污染 OQS 校準。
   ✅ 隨機訊號不被誤當 fail，retry budget 不被燒，TrajectoryPredictor 不被污染。
3. EVALUATOR_AUDIT（PI-2）：OQS 校準鏈早已偵測「OQS pass 但生產違反」連續 N 次
   → 寫 OQS-DRIFT → 進 EVALUATOR_AUDIT → 要求人工 recalibrate（bump SCORER_VERSION）。
   ✅ 漂移的判官被自審機制抓出，而非繼續蓋章。
4. MONITOR_VIOLATION（PI-8）：若 flaky storm 期間任一轉移觸及 retry/recovery 上限，
   runtime monitor 從 .tla invariant 合成的執行期 assertion 立即捕捉 → ESCALATION。
   ✅ 有界停機由「設計時證明 + 執行期 monitor」雙保險。
5. Steersman Renderer（沿用 Phase H）：abort 報告精準寫出
   「偵測到 flaky test（3/5）需確定性 repro / 依賴 lockfile 雜湊不符需提供已簽署清單 /
    OQS 已漂移需人工 recalibrate」——三段式環境請求，而非「retry exhausted」。
6. attention_router（PI-7）：若艦隊中多 track 同時撞 flaky，同 capability_gap 去重
   合併為單一 DIGEST，人類收到「N 個 track 共同的 flaky 根因」而非 N 份報告。
```

✅ **結論**：優化後系統在**三道遞進關卡**（硬化閘擋惡意 / hermetic 重跑去隨機 / EVALUATOR_AUDIT 抓漂移）攔截此案例，最早在「執行前」就擋下惡意碼；flaky 被當作獨立 verdict 而非無界 retry 來源，**有界停機在非確定性前提下仍成立**（且由 runtime monitor 雙保險）；最關鍵——**人類收到的是「請提供確定性 repro / 簽署依賴清單 / recalibrate 判官」的舵手級請求**，而判官的漂移被系統自己揪出。Phase H 讓系統能接觸現實；Phase I 讓這次接觸**即使在不可信、非確定、惡意的前提下，仍然值得信任**。

---

## 7. 執行計畫（Phase I：Trustworthy Scaled Reality-Grounded Autonomy）

> 接續既有 ACT 編號（現至 ACT-058），Phase I 為 ACT-059 起。每個 milestone 完成須過對應 gate 並重跑 TLC + chaos（含新增 FLAKY_EVAL 故障型）。**Pillar C（保證可持續）必須與 Pillar A/B 同步或先行，否則新增狀態會留下證明空窗。**

### M1 — Pillar A：可信的評估接地（最高優先，含唯一正確性缺口 PI-3）

| ACT | 任務 | 產出 | Gate |
|-----|------|------|------|
| ACT-059 | EXECUTION_EVALUATION hermetic 重跑（取共識）+ FLAKY 第三 verdict + chaos 新增 `FLAKY_EVAL` 故障型 | `sandbox_runner.py` 重跑邏輯 + `chaos_runner` FAULT_TYPES | chaos 含 FLAKY_EVAL 100 輪 bounded_ratio=1.0 |
| ACT-060 | Sandbox 安全硬化 profile（--network none/--cap-drop/--read-only/--user/--memory/seccomp）+ image allow-list + 命令白名單 | `sandbox_runner.py` DockerBackend 強化 | 安全回歸測試：出網被阻、root escalation 失敗、未簽署 spec 被拒 |
| ACT-061 | `SANDBOX_HARDENING_GATE` 閘 + spec 簽章 + 依賴 lockfile 雜湊（supply-chain）+ loop self-STRIDE + SLV-012 | FSM + `.tla` 同步 + `loop_threat_model.py` + `governance/rules/R-SELF-STRIDE.yaml` + diagnostic sub_type=`sandbox_policy_violation` | TLC reachable 維持 100%（30→+1）|
| ACT-062 | OQS 校準回饋鏈（verdict↔生產回饋配對 + OQS-DRIFT）+ SCORER_VERSION 人工 gate | `oqs_calibration.py` | 連續 N 次漂移→OQS-DRIFT，調權重須 bump version |
| ACT-063 | Oracle 新鮮度（`frozen_spec_sha` + freshness.check）+ `EVALUATOR_AUDIT` observation 態 | `subagent_contract.py` 擴 + `oracle_freshness.py` + FSM + `.tla` | spec 演進後 oracle stale 被偵測（advisory）|

### M2 — Pillar C：可持續的保證（與 M1 同步，為 M3 加狀態鋪路）

| ACT | 任務 | 產出 | Gate |
|-----|------|------|------|
| ACT-064 | Runtime Monitor Synthesis：從 .tla 4 safety invariant 合成執行期 assertion + `MONITOR_VIOLATION` 態 | `spec_monitor.py` + FSM + `.tla` 同步 | 注入 invariant 違反 → MONITOR_VIOLATION → ESCALATION |
| ACT-065 | 補 liveness：.tla 加 `SF_vars` 啟用 `EventuallyTerminal`/`ObservationsTransient` | `SDD_FSM.tla`/`.cfg` | TLC liveness property 全 PASS |

### M3 — Pillar B：規模化的自治（依賴 M2 的 monitor 補位）

| ACT | 任務 | 產出 | Gate |
|-----|------|------|------|
| ACT-066 | 成功結晶：`SPL` 技能庫 + `spl_consolidator`（productive episode 聚類）+ `MEMORY_CONSOLIDATION` sleep-phase cron（03:00 UTC）+ 反向 graduation | `knowledge/skill-patterns/` + `spl_consolidator.py` + FSM + `.tla` | SPL 草案 trust=proposed 須人工 verified；reachable 維持 100% |
| ACT-067 | Behavioral Reality Loop：`behavioral_drift_scorer` + `production_to_fpl` + `PRODUCTION_BEHAVIORAL_SIGNAL` 態 | `behavioral_drift_scorer.py` + `production_to_fpl.py` + `observability_query` 擴 production/ + FSM + `.tla` | 生產 behavioral 偏差 ≥3 次→FPL 草案（advisory）；守 OPEN-10.6 |
| ACT-068 | 價值目標自治 + 注意力預算：`value_planner` + `BACKLOG_PRIORITIZED` 閘 + `attention_router`（複用 production_monitor rolling-window）+ 修正 abort 覆寫審計遺失 | `value_planner.py` + `attention_budget.py` + `snapshot.py` 改 + FSM + `.tla` | 目標選定須人工 signoff；P0/structural 永不被折疊 |

### M4 — Phase I 驗收

| ACT | 任務 | 判準 |
|-----|------|------|
| ACT-069 | 全量回歸 + chaos 100 輪（含 FLAKY_EVAL）+ TLC（含新狀態 + liveness）+ §6 自我驗證腳本自動化 | bounded_ratio=1.0；TLC reachable=100%；4 safety + liveness 全 PASS；pytest 全綠；§6 flaky+惡意+漂移 e2e 在「執行前/重跑去隨機/自審抓漂移」三關攔截並輸出舵手級 digest |

### M5 — 條件性後段：艦隊並行（PI-1，**僅在多 feature 並行需求觸發 + Pillar C parametric 就緒後**）

| ACT | 任務 | 前提 |
|-----|------|------|
| ACT-070 | Track 維度 state key + sandbox container/port namespacing | 多 feature 並行需求明確 |
| ACT-071 | `SPEC_DEPENDENCY_LOCK`（全域鎖序防死鎖）+ `MERGE_ARBITRATION`（textual vs semantic conflict 區分） | ACT-070 完成 |
| ACT-072 | Apalache parametric TLA（`state[Feature]` + symmetry reduction）取代 explicit-state | N-track FSM 確定引入時 |

---

## 8. 風險與防護

| 風險 | 防護 |
|------|------|
| 純加法陷阱：Phase I 想加 6+ 狀態，重演 G6「只長不瘦打爆證明」 | Pillar C（runtime monitor + liveness）與 Pillar B 同步/先行；PI-3 用內部執行策略而非新狀態；艦隊並行劃為條件性後段；每 ACT 完成即重跑 TLC，coverage < 100% 不得 merge |
| flaky 重跑本身變無界 | `FLAKY_RERUN_N=5` 硬上限；FLAKY verdict 隔離不進 retry；chaos 新增 FLAKY_EVAL 驗有界性 |
| 安全硬化打斷合法 e2e（--network none 阻斷需網路場景）| 分級 profile + egress-allowlist 內部橋接；WAIVER 人工 gate（waiver 本身亦受 audit）|
| seccomp/cap-drop 跨 OS 行為不一致引入新非確定性 | CI 環境矩陣吸收；分級 profile；與 Pillar A 去隨機目標一致對待 |
| OQS 校準若全自動調權重 = 判官自我放鬆門檻 | 一律人工 gate + bump SCORER_VERSION；FLAKY 不進校準樣本 |
| 生產→spec 自動演化繞過人工 | 全程 advisory + trust_level=proposed + reviewed_by signoff 才 enforce（Rule 9.11.3 / Rule 8）|
| 成功結晶過擬合（偶發成功誤結晶為技能）| pattern_matcher 同模式 ≥N 次 + 人工 verified gate；退役提案優先於結晶提案防震盪 |
| 注意力 router 去重過度折疊真 critical | P0/structural 硬白名單永不降級；raw event 全保留為底層 audit |
| value model 自主亂選目標 | 只排序不裁決，人工 signoff gate；冷啟動採保守 default 標 cold_start（仿 Rule 9.19.1）|
| SPL 經 Hub 跨實例散播時上游標 verified 繞過 gate | 沿用 Rule 9.12.6 `_stamp_external_trust_level` 強制 stamp external |

---

## 9. 一頁總結

> **Phase H 讓機器第一次按下了執行鍵——串行地、在可信地基上、執行一件被給定的事。它證明了「能接觸現實」。**
>
> **但 Phase I 發現：那隻按按鈕的手，判官可能在漂移（PI-2）、結果可能是隨機的（PI-3）、執行的是自己生成的不可信碼卻零防護（PI-4）；而且這隻手只有一隻（PI-1）、只會執行不會自選價值（PI-7）、只記仇不記恩（PI-6）、生產現實只聽得懂數字（PI-5）、它的停機證明還停在原地撐不住長大（PI-8）。**
>
> Phase I 做三件事，讓系統從 **L5 Reality-Grounded** 跨入 **L6 Trustworthy-Scaled**：
> 1. **自審（Pillar A / PI-2,3,4）**：讓判官被監控（OQS 校準 + oracle 新鮮度）、讓執行去隨機（hermetic 重跑 + FLAKY 第三 verdict）、讓執行器硬化（self-STRIDE + sandbox jail）。**這次接觸現實，值得信任。**
> 2. **增殖（Pillar B / PI-1,5,6,7）**：讓系統並行（條件性艦隊）、自選價值目標、把成功結晶成永久技能（雙向代謝）、讓生產的功能性現實反哺規格、用注意力預算保護人類舵手。**越活越強、規模化、不淹沒人。**
> 3. **可持續證明（Pillar C / PI-8）**：讓 .tla 證明合成執行期 monitor、補齊 liveness——**現實長大時，有界停機的招牌仍然撐得住。**
>
> Phase H 的招牌「執行接地」維持不動；Phase I 補上最危險的盲區——**接地線本身的可信度**。八個洞，三條主軸：判官自審、系統增殖、證明可持續。閉環不只接上了現實，現在還**信得過自己這次接觸現實的方式**。

---

*本藍圖由 8 探針並行缺口稽核（workflow `sdd-l5plus-gap-audit`，16 agents / 634K subagent tokens）對 Post-Phase-H 系統驗證，所有缺口判定附 file:line 證據並經獨立 skeptic 對抗驗證、重新校準嚴重度。PI-3（非確定性 vs 有界停機）因稽核流程 verify 階段未結構化而由架構師依一手證據親自補回——此遺漏本身印證 Rule 9.8 對抗驗證對「最反直覺缺口」的不可或缺。待人工 review 後進入 Phase I 實作。*
