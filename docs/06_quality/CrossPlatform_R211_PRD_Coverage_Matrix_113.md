# CrossPlatform R211（improving_113）PRD v2.1 覆蓋度矩陣——盤點 agent 唯讀交件原文

> 姊妹檔：主審計證據檔＝`docs/06_quality/CrossPlatform_R211_ZeroTrust_Audit_113.md`。本檔為 2026-10-09 盤點 agent（Sonnet，唯讀）交件逐字保全（408 個 path:line 經腳本驗證行號有效、語意抽樣 70 個），供下一輪重盤對照；數字的權重敏感度見其 §1.2。

# PRD v2.1 覆蓋度零信任重盤（improving_113 輸入）

- 基準：repo HEAD `93929947`（工作樹乾淨），日期 2026-10-09；PRD＝`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`（2657 行）。
- 方法：PRD 逐章讀完；每個 ✅ 都附本輪 grep／Read 現查的 `file:line`（全檔共 408 個 `path:line` 引用，已用腳本逐一驗證行號未超出檔案長度；PRD 行座標逐行比對過標題文字）；R98 差距分析只當待驗清單，不當證據。
- 唯讀紀律：未改 repo 任何檔、未跑 git 寫入、未跑全套測試、未起背景任務、未打 `/api/oauth/usage`。唯一的執行動作：`python AutoClaude/tools/check_loc_budget.py --json`（唯讀）、`claude --help`／`claude --version`、三個 `claude <旗標> --help` 零 token 探針（見 §4）。
- 圖例：✅ 落地（規範性機制在、且有測試／鎖）｜⚠️ 部分（有規範性機制缺漏；括號內 S/M/L＝缺口量級）｜❌ 未做｜➖ 架構性替代或依設計不做（不計分母）｜❓ 本輪未查證。僅『驗收資料／校準值』缺漏者仍計 ✅ 並在備註登記殘留。

## 0. 結論（先講）

1. **覆蓋度 (a)＝60.3%**（任務書點名範圍 80 列：✅22／⚠️44／❌7／➖7；分母扣掉 ➖ 後 73 列；⚠️ 計 0.5）；加 §10／§11／§15.5 共 90 列＝58.6%；再加 7 份修憲施工圖 11 列＝59.9%。**⚠️ 權重是最大不確定源**：improving_112 引用的 65% 對應 w≈0.58（含附加列 0.61）、『72～75%』對應 w≈0.70（含附加列 0.73）——也就是說，『還剩 25～30%』只在把⚠️算成約七成落地時成立；按『有規範性機制缺漏即 ⚠️』逐列誠實計（w=0.5），約剩 4 成（40%～41%）。
2. **覆蓋度 (b)＝R98 12 項完成 3 項＋部分 2 項**：嚴格 3/12＝25%，部分計半分 4.0/12＝33%（R98 當時 0/12）。完成＝#3 DEF-200-176、#6 §4.2.4 平穩性、#7 §8-4 checksum；部分＝#1 LOC 瘦身（三檔仍零餘裕）、#10 §8 items 11~14；未做＝#2 §8 三大真空（僅 DIRTY_UNSAVED 1/4）、#5、#8、#9、#11、#12；#4 本輪未查證。
3. **剩下的缺口不是一塊，是四塊**：(甲) 已決策不做、暴露 0（DEF-200-246／458／199-L2L3／234／242）；(乙) **從未決策也無帳列**的缺口（429 jitter、index.lock、NEEDS_HUMAN、MAX_STEP_*、`resume_cost_pp`、§9 指標、PreCompact／COMPACT_MIN_INTERVAL、模擬器／24h e2e、H1 fixture、容器偵測）；(丙) **Adopted／Proposed 卻零落地**（R108 BURN-DOWN＝Adopted；R121 受控 commit/push＝Proposed）；(丁) PRD 文字債 12 筆修憲候選＋1 筆程序債（§5）。
4. **對『無人值守續航』真正有幫助的未落地項只有四處**：R121（喚醒窗不能 commit/push，最大授權缺口）、`resume_cost_pp`（喚醒成本無資料，REQ-W6(b)(c) 與 §11.3／§9 同欠）、**AutoClaude 引擎獨立跑時額度軸不存在**（`AutoClaude/autoclaude/core/ports/quota_meter.py:15-45` 自陳『遲到時間無上界』；缺第三方寫入者，improving_112 §4-3，全 docs 零追蹤列）、引擎路徑的單次長睡（`AutoClaude/autoclaude/core/services/auto_resume.py:218,283`，PRD §4.5.2／§4.5.5 針對的同型病；哨兵路徑已走 OS 排程，引擎路徑沒有）。
5. **守衛面零餘裕**：`tools/lib/quota_escalation.py` 400/400、`tools/session_resume_planner.py` 746/750、`tools/lib/quota_gate.py` 495/500、`.claude/hooks/context_budget_guard.py` 1089/1089（`check_loc_budget --json` 本輪現跑）。落點在這四檔的 W 必須同窗淨減；本輪推薦的 W 全部避開它們。
6. **本輪 W 候選（不含 W1）**：W-B `resume_cost_pp` 落帳（推薦首選）／W-C′ 引擎無人值守硬化包（第三方額度刷新者＋分片休眠）／W-E R121 決策包（只出決策、不寫碼）／W-A PRD 修憲整理批／W-D CLI 版本清單刷新。控制器草稿 `improving_113_draft.md` 標題預留 W2／W3 兩格：建議 **W2＝W-B、W3＝W-C′**（皆不碰守衛面），W-A 與 W-E 決策包可由主控以文件工作順手帶。詳 §6。
7. **PRD 條文被實況推翻的修憲候選 12 筆**（5 筆是 ADR-XPLAT-014 §3.5 Q4 自 v2.1.11 起就欠的『生效後施工項』、1 筆已登記 DEF-200-242、6 筆本輪新列）＋ 修訂表四列字面落差 1 筆程序債；`[需核對]` 11 處＋B.3 五項現況見 §4。

## 1. 覆蓋度兩個數字與算法

### 1.1 (a) 以 PRD 模組列數加權

- **算法**：score ＝ (Σ✅×1 ＋ Σ⚠️×w) ÷ (列數 − Σ➖)。主算 w＝0.5；❌＝0；➖（PRD 自身或 ADR 指定的架構性替代／依設計不做）不入分母；❓ 計入分母、記 0。
- **列的粒度**：§3／§4.1.1 各來源／§4.1.2~§4.1.5／§4.2.1~§4.2.8／§4.3／§4.4.1~§4.4.3／§4.5.1~§4.5.10／§4.6／§4.7／§5／§6（三個區塊群＋§6.1＋§6.2 三條 R）／§7／§8 十四項＋1b／§9 三項／§12 七項／§13 兩項／§15.4 P0~P5 為『任務書點名範圍』；另 §10、§11 八組驗收、§15.5 紅線為附加列；修憲施工圖 7 份拆 11 列。
- **規則（避免自由心證）**：缺『規範性機制』⇒ ⚠️；只缺『驗收資料／校準值』⇒ 仍 ✅＋備註。例：§4.2.4 H1 fixture 零命中、H7 後半占位 60s ⇒ ✅＋殘留註記；§4.5.10 缺 R-4.5.10-1『行程內重量』機制 ⇒ ⚠️(S)。

| 範圍 | ✅ | ⚠️ | ❌ | ➖ | ❓ | 分母 | 分子(w=0.5) | **覆蓋度** |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| (a) 任務書點名範圍（80 列） | 22 | 44 | 7 | 7 | 0 | 73 | 44.0 | **60.3%** |
| (a′) ＋§10／§11／§15.5（90 列） | 23 | 49 | 9 | 9 | 0 | 81 | 47.5 | **58.6%** |
| (a+) ＋7 份修憲施工圖（101 列） | 29 | 51 | 11 | 10 | 0 | 91 | 54.5 | **59.9%** |

### 1.2 敏感度（誠實標示不確定度）

| 計法 | (a) 點名範圍 | (a′) ＋附加 | (a+) ＋施工圖 |
| :--- | ---: | ---: | ---: |
| ⚠️ 權重 0.25 | 45.2% | 43.5% | 45.9% |
| ⚠️ 權重 0.5（主算） | 60.3% | 58.6% | 59.9% |
| ⚠️ 權重 0.72（≈improving_112 引用的 72~75%） | 73.5% | 72.0% | 72.2% |
| ⚠️ 權重 1.0（⚠️ 視同落地） | 90.4% | 88.9% | 87.9% |
| 缺口量級加權（⚠️-S＝0.75、M＝0.5、L＝0.25） | 66.1% | 64.5% | 65.4% |
| **下限**：➖ 全計 ❌（連架構性替代也不認），w＝0.5 | 55.0% | 52.8% | 53.0%（另把 closed-by-decision 的未做部分降級） |

- 反推：要讓 (a) 等於 improving_112 §0 的 65%，⚠️ 權重須約 0.58（含附加列 0.61）；等於 72~75%（取 72.5%），須約 0.70（0.73）。**本檔不主張哪個權重對**，只主張：按『有規範性機制缺漏即 ⚠️』的逐列規則，w=0.5 時 (a)＝60.3%（含附加列 58.6%），下限（➖ 全計 ❌）55.0%～52.8%，⚠️ 視同七成落地時 73~74%。
- **(c) 補充：§6 .env 鍵級落地率**（PRD §6 共 78 鍵，逐鍵見 §7）：✅14／⚠️21／❌28／➖15 ⇒ (14＋0.5×21)÷63＝**38.9%**。鍵級低≠功能缺：PRD §6 以 Daemon 形態寫成，實作換形態後多數鍵無對映（15 鍵判 ➖、AUTOSDD_QUOTA_* 與 PRD 鍵名不同源）。

### 1.3 (b) 以 R98 12 項完成數計

- ✅3（#3、#6、#7）＋⚠️2（#1、#10）＋❌6（#2、#5、#8、#9、#11、#12）＋❓1（#4）。嚴格＝3/12＝**25%**；部分計半分＝4.0/12＝**33%**。逐項證據見 §3。

### 1.4 剩餘缺口的構成（回答『沒落地的那 25～30% 在哪』；範圍＝(a′) 全部 PRD 本文列，缺口質量＝❌×1＋⚠️×0.5）

| 主題 | 非落地列數 | 缺口質量 | 占總缺口 | 列分佈（❌／⚠️L／⚠️M／⚠️S） | 主要缺什麼 |
| :--- | ---: | ---: | ---: | :--- | :--- |
| H 安全／合規／紅線 | 9 | 5.5 | 16% | 2／0／0／7 | bypass 容器偵測、寫入範圍清單、供應鏈規則、index.lock、injection 網路確認、使用條款人工檢核 |
| E 多 Agent 整合／帳號仲裁／state schema | 8 | 5.0 | 15% | 2／2／1／3 | 整合佇列／多 worktree／state agents[]／lease 仲裁——皆需多 agent 並行才有意義（DEF-200-246 重開條件②） |
| A 遙測來源與量測資料 | 7 | 4.5 | 13% | 2／0／2／3 | T1 OTel／T4 /usage 未接；T3 只服務 context 尺；T2 僅地板；新鮮度三段式與 EWMA 無消費者 |
| B 引擎無人值守（額度軸／休眠／硬預算） | 8 | 4.0 | 12% | 0／1／4／3 | 引擎獨立跑額度軸不存在（無第三方刷新者）、單次長睡、Step 硬預算只剩牆鐘、NEEDS_HUMAN、CLI 清單過期 |
| I 驗收與長跑證據 | 6 | 3.5 | 10% | 1／0／5／0 | 6h 零 token、24h e2e、模擬器七情境、5 秒落盤計時、`resume_cost_pp`、P4／P5 出場條件 |
| C 配速／致動器長尾與壓縮 | 6 | 3.0 | 9% | 0／0／3／3 | 模型降級致動器／任務類別過濾未做、BURSTING 無呼叫端、無 PreCompact／COMPACT_MIN_INTERVAL、HALTED_MANUAL、離線模擬器／DRY_RUN 一週 |
| D 喚醒鏈細節 | 6 | 3.0 | 9% | 0／0／4／2 | 凍結 7 步缺逐 worktree commit／5 秒落盤、RESET_CONFIRM／jitter、RESUME 門檻單位與 weekly 規則、行程內重量 |
| F 設定面與啟動不變式／API_KEY | 5 | 3.0 | 9% | 1／1／3／0 | 78 鍵中 28 鍵無對映（週額度獨立門檻、MAX_STEP_*、API_*、METRICS…）；啟動不變式 7／7b／8／9 未做；§5 API_KEY 整章 |
| G 可觀測性輸出 | 3 | 2.0 | 6% | 1／0／0／2 | Prometheus 12 指標零；日誌非逐決策全量；告警缺 NEEDS_HUMAN／429 突增／遙測全失效桌面通知 |
| **合計** | 58 | 33.5 | 100% | — | 對應 (a′) 分母 81 列中缺 33.5 列＝41.4% |

> 讀法（H 列數最多，但 9 列中 7 列只是 S 級小缺口）：A／B／C／D 四塊（遙測、引擎無人值守、配速長尾、喚醒鏈細節）才是『還能直接提升續航』的缺口；E／F／G 多半依賴多 Agent 並行或是 Daemon 形態寫成的設定鍵，**實作換形態後本來就不會落地**——處置是修憲標註而非補程式碼（見 §5、W-A）。

## 2. 逐章矩陣

### 2.1 PRD 本文

| ID | PRD 座標 | 項目 | 狀態 | 證據（本輪現查 file:line） | 缺口／備註 |
| :--- | :--- | :--- | :---: | :--- | :--- |
| §3.1 | L166-190 | 架構圖：單一 Daemon＋7 模組 | ➖ | `tools/lib/quota_boot_check.py:2-10`（「本 repo 沒有常駐 daemon」）；PRD §15.2/§15.3 `L2355-2408` 自訂『薄治理層＋採用原生能力』；實際載具＝hook `.claude/hooks/context_budget_guard.py` ＋哨兵 `tools/session_resume_planner.py:1424` | 架構性替代（非缺漏） |
| §3.2 | L192-229 | 10 態 FSM＋單向鎖存＋轉移圖 | ⚠️(M) | 無狀態純函式 `tools/lib/quota_policy.py:682`（decide）、帶別 `:105-110`；halt 閂鎖 `tools/lib/quota_gate.py:302`；`HALTED_MANUAL` 僅近似＝ESC+F12 全域中斷 `AutoClaude/autoclaude/plugins/hotkey_plugin.py:42`（只中止，無 pause/resume）；BURSTING 無狀態物件（見 §4.2.5） | 缺 `autoclaude pause/resume` 人工覆寫；其餘為設計替代 |
| §4.1.1-T1 | L241 | T1 OTel 本機遙測 | ❌ | `CLAUDE_CODE_ENABLE_TELEMETRY`／`OTEL_`／prometheus 在 `tools/`、`.claude/`、`AutoClaude/autoclaude/` 零命中（grep 實查） | PRD 稱『首選官方正途』，與 T5 並行不互為替代（L328-330）；從未接線 |
| §4.1.1-T2 | L242 | T2 逐字稿本機加總 | ⚠️(S) | 僅『撞線地板』：`tools/lib/quota_gate.py:768`（quota_floor_reading）←`tools/lib/quota_limits.py:378`（unhandled_limit_event；`:319` rglob 含 subagents） | 無 token 加總；T5 為主源，加總只是後備 |
| §4.1.1-T3 | L243 | T3 statusLine 回寫 | ⚠️(M) | 讀端 `.claude/hooks/context_budget_guard.py:500`（read_context_feed）、安裝器 `tools/install_statusline.py:132`、producer `tools/statusline_context_feed.py`；實查 `~/.autosdd/context_feed/*.json` 只含 model＋context_window，無 `rate_limits.*`；`~/.claude/settings.json:44` 本機已設（每機各裝） | 只服務 K_ctx（context 尺），不服務 U5h/U7d |
| §4.1.1-T4 | L244 | T4 /usage 程式化解析 | ❌ | 零命中（grep） | PRD 排最後（低可靠），影響小 |
| §4.1.1-T5 | L245-257 | T5 OAuth usage 認可主源（v2.1.4） | ✅ | `tools/lib/quota_meter.py:76`（USAGE_URL）、`:298-300`（access_token：token 不落痕跡）；TTL `tools/lib/quota_gate.py:168`；單一居所鎖 `tools/tests/test_quota_policy.py:3919` | — |
| §4.1.1-引擎 | L166-190／L245-257 | 引擎獨立執行（無 Claude Code session）時的額度遙測 | ⚠️(L) | 只讀快取、過期回 None：`AutoClaude/autoclaude/infra/adapters/file_quota_meter.py:79,121`（TTL 1800s）；`AutoClaude/autoclaude/core/ports/quota_meter.py:15-45`（劃界自陳『額度軸會在無人看管那一跑上安靜地不存在，遲到時間無上界』）；零寫入者被釘住 `AutoClaude/tests/test_r82_quota_axis_and_shipped_defaults.py:797-830`；唯一寫入者在 harness `tools/lib/quota_gate.py:707`（刷新 CLI `tools/lib/quota_meter.py:891` `--refresh`） | 缺『第三方寫入者』（排程／哨兵定期刷快取）＝improving_112 §4-3；全 docs 零追蹤列（grep『第三方刷新』只命中 improving_112）；引擎側 `pct is None` ⇒ 不擋 |
| §4.1.1-LOCAL | L258-260 | 本機推估安全邊際 15pp | ➖ | 無『本機加總』路徑（T5 為帳號級讀數）；全庫零命中 | 架構性替代 |
| §4.1.2 | L262-271 | 新鮮度三段式（180/600/1200s） | ⚠️(S) | TTL 180s `tools/lib/quota_gate.py:168`；過期→`unmeasured`→degraded cap `:451`、`tools/lib/quota_policy.py:700` | 600s→DRAINING／1200s→FREEZING 無；v2.1.8 §4.1.5 已改 cap 語意 |
| §4.1.3 | L273-281 | 視窗重置偵測 | ✅ | `tools/lib/quota_pace.py:112`（_ROLLOVER_EPS=0.5）、`:549`（segments）、`:625`（row_of）；DEF-200-200 fixed | 參數與 PRD 不同（0.5pp vs 20pp，見修憲候選 C12） |
| §4.1.4 | L284-340 | 帳號/方案變更偵測 | ✅ | `tools/lib/quota_policy.py:144`（KNOWN_KINDS）、`tools/lib/quota_gate.py:330`（core_signature）、`tools/lib/quota_meter.py:658`（account_key_of）；tests `tools/tests/test_quota_policy.py:1805,2088` | — |
| §4.1.5 | L341-436 | 遙測全失效收斂（cap≤cap_prepare） | ✅ | `tools/lib/quota_policy.py:240,248`（degraded_cap=2=cap_prepare）、`:700`（夾制）；ENV `tools/lib/quota_policy_env.py:98`；F5 對映 `tools/tests/test_context_budget_guard.py:13341`；訊息 `tools/lib/quota_gate.py:665` | — |
| §4.2.1 | L440-448 | EWMA 燃燒率 | ⚠️(S) | `tools/lib/quota_pace.py:733`（ewma_burn_rate）、`:680-681`（V_FLOOR／ALPHA）；僅診斷，生產呼叫端零（grep 排除 tests）；`tools/tests/test_quota_policy.py:3822` | 庫在、無消費者；PRD §4.2.8 自陳可由 pace_index 取代 |
| §4.2.2 | L450-463 | 安全燃燒率／目標併發公式 | ➖ | 被 §4.2.8 pace_index 取代；R108 §6.2 廢 T_MIN→`wrap_minutes` `tools/lib/quota_policy.py:287,740` | PRD 自身指定替代路線 |
| §4.2.3a | L465-486 | 閘門優先序（短路） | ✅ | `tools/lib/quota_policy.py:682`（decide）、`:131`（FALLBACK_KINDS）、`:483`（MODEL_SCOPED_KINDS）、`:653`（_in_cap_gate）；`tools/tests/test_quota_policy.py:146` | — |
| §4.2.3b | L482-491 | 致動器表：併發／模型降級／任務類別／硬預算 | ⚠️(M) | 併發＝cap `tools/lib/quota_policy.py:442` ✅；模型降級僅『建議』`Decision.model_hint` `tools/lib/quota_policy.py:323,793`／`tools/lib/quota_messages.py:810`（`CLAUDE_CODE_SUBAGENT_MODEL` 零命中＝無致動器）；任務類別過濾零命中；硬預算見 §4.4.3 | 模型降級致動器與任務類別過濾未做（W1 可補前半） |
| §4.2.4 | L493-686 | 平穩性 (a)~(e)＋H1~H7 | ✅ | `tools/lib/quota_availability.py:187,250`；`tools/lib/quota_stability.py:168,215`；接線 `tools/lib/quota_gate.py:97,101,966-976,1100-1112`；啟動自檢 `tools/lib/quota_boot_check.py`＋`tools/session_resume_planner.py:1532`；tests `tools/tests/test_quota_policy.py:2828,3036,3681,3781` | 驗收資料殘留（不降級）：H1 fixture 零命中；H7 後半＝占位 60s；`tools/lib/quota_availability.py:55-58` 檔頭仍寫『不交付接線』＝過期註解 |
| §4.2.5 | L688-701 | BURSTING 六條件 | ⚠️(S) | `tools/lib/quota_pace.py:684`（bursting_ok 六條件全寫）；生產呼叫端零；DEF-200-458 closed-by-decision@R209 | 暴露 0；重開條件見 DEF-200-458 |
| §4.2.6 | L703-918 | 參考實作（dataclass 控制器） | ➖ | PRD §4.2.8 自陳可被 pace_index 完全取代 | — |
| §4.2.7 | L920-934 | 情境試算表 | ➖ | 範例表；斷言形態見 §11.2（TestDecisionTable `tools/tests/test_quota_policy.py:146`） | — |
| §4.2.8 | L936-961 | pace_index 對齊 CLI 配速門檻 | ✅ | `tools/lib/quota_pace.py:213`（pace_index）、`:202`（lead_pp）；`tools/lib/quota_policy_env.py:91`（pace_ceiling 出廠 1.0）；`tools/tests/test_quota_policy.py:2310` | 建議值 1.25/1.50 未採用（修憲候選 C8） |
| §4.3 | L963-987 | 上下文壓縮策略（三 AND） | ⚠️(S) | K_ctx 84% `.claude/hooks/context_budget_guard.py:196-197`；成本邊際 `tools/lib/quota_policy.py:284`＋`tools/lib/quota_gate.py:496-515`；機械 autocompact `.claude/settings.json:4,8` | `COMPACT_MIN_INTERVAL_SECONDS` 零命中；PreCompact hook 無（settings 無條目） |
| §4.4.1 | L991-1004 | Worktree 建立 | ➖ | PRD §0.6 `L87`／附錄 B-20：採原生 `isolation:'worktree'`；`.autoclaude/worktrees` 零命中 | PRD 自身指定採用原生 |
| §4.4.2 | L1006-1019 | 序列化整合佇列（rebase→驗證→ff-only） | ❌ | 僅 `AutoClaude/autoclaude/utils/checkpoint_manager.py:83` 欄位＋`AutoClaude/autoclaude/execution/boot_self_check.py:79-153` 讀者，零生產寫者（DEF-200-246 closed-by-decision；tripwire `AutoClaude/tests/contract/test_def200246_integration_queue_tripwire.py`） | 需多 agent worktree 並行才有意義；重開條件見 PRD L2035-2040 |
| §4.4.3 | L1021-1034 | Agent 硬性預算（turns／wall／quota_pp／×0.5） | ⚠️(M) | 只有 `AutoClaude/autoclaude/utils/config.py:166`（step_timeout_seconds=600）＋`AutoClaude/autoclaude/core/kernel.py:184`；`MAX_STEP_TURNS`／`MAX_STEP_QUOTA_PP`／`DRAIN_BUDGET_FACTOR` 零命中；SDK 有 `max_turns`（`.venv/lib/python3.11/site-packages/claude_agent_sdk/types.py:2015`）但 adapter 未傳（`AutoClaude/autoclaude/infra/adapters/sdk_executor_adapter.py:167-172`） | turns／quota_pp 兩軸缺；`--max-turns` CLI 旗標在 2.1.295 help 零命中（C3） |
| §4.5.1 | L1038-1054 | 凍結流程 7 步 | ⚠️(M) | halt→checkpoint `AutoClaude/autoclaude/core/services/auto_resume.py:368`；救援前置 `:296`（_freeze_is_safe）；RELAY 任務書 `tools/session_resume_planner.py:354,783` | 缺『逐 worktree commit [skip ci]』、『5 秒內落盤』計時驗收 |
| §4.5.2 | L1056-1068 | 分片休眠＋時鐘跳躍偵測 | ⚠️(M) | 哨兵路徑＝OS 排程一次性喚醒（架構性替代）；**引擎路徑** `AutoClaude/autoclaude/core/services/auto_resume.py:218,283` 為單次 `time.sleep(wait_secs)`（無切片、無跳躍偵測；`SLEEP_SLICE_SECONDS`／`CLOCK_JUMP_TOLERANCE_SECONDS` 零命中）；`_WAITABLE_KINDS` 只含 5h 軸 `AutoClaude/autoclaude/core/ports/quota_meter.py:80` | 引擎路徑獨有缺口（PRD §0 第 2 條阻斷級的同型病） |
| §4.5.3 | L1070-1078 | 重置驗證與喚醒（RESET_CONFIRM／full-jitter／C=1 起步） | ⚠️(M) | `tools/session_resume_planner.py:476`（probe_quota）、`tools/lib/quota_gate.py:742-765`（L0 零成本端點：每軸<100% 即 open） | `RESET_CONFIRM_PERCENT`(10) 零命中、jitter 序列無（修憲候選 C2） |
| §4.5.4 | L1080-1110 | 喚醒策略 AUTO／RESUME／FRESH | ⚠️(M) | `tools/session_resume_planner.py:1136`（choose_resume_route）、`:1097-1112`（bytes 上限）；argv `tools/lib/resume_route.py:114,129,150` | 缺 token 門檻、U7d→FRESH 規則、`--max-turns`／`--allowed-tools`（C3/C4/C6） |
| §4.5.5 | L1112-1127 | 長休眠交棒 OS 排程 | ✅ | `tools/session_resume_planner.py:776`（register_endurance）、`:683`（endurance_schtasks_script）；`tools/lib/schedule_backend.py:297,387,856`（Schtasks／Launchd／select） | 引擎路徑 >7200s 交棒見 §4.5.2 |
| §4.5.6 | L1129-1176 | 撞線喚醒閉環 R-1~6／A1~A5 | ✅ | `tools/lib/quota_limits.py:378,319`；`tools/session_resume_planner.py:610,363`；`tools/lib/quota_escalation.py:378`；tests `tools/tests/test_sentinel_tick_e2e_r145.py`、`tools/tests/test_wake_chain_halt_r278.py` | — |
| §4.5.7 | L1178-1247 | 主控閒置盲區 B1~B3 | ✅ | `tools/lib/quota_escalation.py:292,328,525`；`tools/session_resume_planner.py:1424`；tests `tools/tests/test_context_budget_guard.py:6945,7057` | — |
| §4.5.8 | L1249-1307 | 哨兵漂移自癒 C1~C4 | ✅ | `tools/lib/sentinel_lifecycle.py:198`（armed_but_missing）；`tools/lib/quota_escalation.py:378`；`tools/tests/test_context_budget_guard.py:7092` | — |
| §4.5.9 | L1309-1528 | 髒污工作樹救援 D1~D9 | ✅ | `AutoClaude/autoclaude/infra/adapters/dirty_worktree_rescue.py:272,375`；接線 `AutoClaude/autoclaude/core/wiring.py:75`、`AutoClaude/autoclaude/main.py:243-247`、`AutoClaude/autoclaude/core/services/auto_resume.py:296`；`AutoClaude/tests/test_r100_dirty_worktree_rescue.py` | 殘餘僅 DEF-200-246（見 §6.2-2） |
| §4.5.10 | L1530-1671 | 醒來確認額度 E1~E5 | ⚠️(S) | `tools/session_resume_planner.py:520`（PATROL_HANDBACK）、`:530-566`（tick_plan）；E5 `tools/tests/test_context_budget_guard.py:1569` | R-4.5.10-1『行程內重量 ≤3 次／≤90s』零命中；暴露 0 |
| §4.6 | L1673-1683 | 跨平台防休眠 | ➖ | 刻意不做 keep-awake；替代＝OS 排程喚醒＋睡眠姿態出聲 `tools/lib/endurance_env.py:356-397`（pmset -g custom）；`caffeinate`／`SetThreadExecutionState`／`systemd-inhibit` 零程式碼命中 | 已知邊界：睡著的 Mac 不被喚醒（根 CLAUDE.md〈mac 已知邊界〉）；下限敏感度計為 ❌ |
| §4.7 | L1684-1703 | 帳號配額仲裁 | ⚠️(S) | 目錄項派發帳 `tools/lib/quota_ledger.py:99,133`、`tools/lib/quota_gate.py:164,204`（FANOUT_WINDOW=300s、O_EXCL） | 無 lease TTL／daemon_id／`daemon.lock`；功能等價 |
| §5 | L1705-1719 | API_KEY 模式 | ❌ | `AUTH_MODE`／`API_BUDGET_*`／`API_AUTO_CONTINUE` 全庫零命中；docs 零決策記錄 | 建議以修憲標『依設計未實作』（本專案純 OAuth），見 W-A |
| §6-A | L1731-1801 | 區塊 1~4b：帳號／遙測／水位／週額度／超額 | ⚠️(L) | ✅ TOKEN_*↔`tools/lib/quota_policy_env.py:63,65,67`（對映鎖 `tools/tests/test_context_budget_guard.py:13213-13224`）；✅ TELEMETRY_UNMEASURED_CAP↔`tools/lib/quota_policy_env.py:98`；❌ AUTH_MODE／ACCOUNT_TYPE／SOURCE_ORDER／WEEKLY_*／PACE_*／OVERAGE_ALLOW*（逐鍵見 §7） | 週額度獨立門檻被單一 band 組取代（C8） |
| §6-B | L1803-1856 | 區塊 5~9：上下文／併發／突刺／硬預算／休眠喚醒 | ⚠️(M) | ✅ COMPACT_COST_BUDGET_PP `tools/lib/quota_policy_env.py:75`；✅ AVAILABILITY_* `tools/lib/quota_policy_env.py:111,113`；❌ MAX_STEP_*／RESET_CONFIRM／SLEEP_SLICE／CLOCK_JUMP／MAX_INPROCESS_WAIT | 逐鍵見 §7 |
| §6-C | L1857-1914 | 區塊 10~15：防休眠／Git／狀態／安全／可觀測／API | ⚠️(M) | ✅ CONFLICT_POLICY `AutoClaude/autoclaude/execution/boot_self_check.py:45`；✅ STATE_RETAIN `AutoClaude/autoclaude/infra/repositories/file_state_repository.py:42`；✅ DIRTY_SAVE_RETRIES `AutoClaude/autoclaude/infra/adapters/dirty_worktree_rescue.py:58`；✅ AGENT_PERMISSION_MODE `AutoClaude/autoclaude/utils/config.py:401`；❌ METRICS_EXPORT／ALERT_WEBHOOK／ALLOW_PERMISSION_BYPASS／INTEGRATION_*／API_* | 逐鍵見 §7 |
| §6.1 | L1916-1952 | 啟動自檢不變式 1~13 | ⚠️(M) | ✅1,4,6：`tools/lib/quota_policy_env.py:257-297`、`tools/lib/quota_boot_check.py`；✅11,12,13：`AutoClaude/autoclaude/execution/boot_self_check.py`；⚠️5（H7 占位 60s）、10；➖2,3,7c；❌7,7b,8,9（容器偵測／`.autoclaude/` gitignore 檢查零命中） | `load_policy` 越界＝整組退回預設＋出聲，PRD 原文『拒絕啟動』（C11） |
| §6.2-1 | L1972-2017 | 殘留整合佇列：開機掃描重排 | ⚠️(L) | `AutoClaude/autoclaude/execution/boot_self_check.py:79,97`；`AutoClaude/autoclaude/main.py:108-160` | 掃描已接電、輸入恆空（零生產寫者，DEF-200-246 closed-by-decision） |
| §6.2-2 | L2018-2042 | CLI 版本相容＋DRY_RUN | ⚠️(S) | `AutoClaude/autoclaude/execution/boot_self_check.py:155-197,298-301`；清單 `AutoClaude/autoclaude/utils/verified_cli_versions.py:16`（僅 2.1.223／2.1.233；本機 `claude --version`＝2.1.295 ⇒ 每次啟動 loud＋DRY_RUN） | DRY_RUN 未接執行器（PRD L2033『依設計未實作』）；清單過期 62 個小版 |
| §6.2-3 | L2043-2062 | 可用空間（bytes）＋清理 | ✅ | `AutoClaude/autoclaude/execution/boot_self_check.py:200-253`；`AutoClaude/autoclaude/main.py:136-153`；`AutoClaude/tests/test_r100_boot_self_check.py` | — |
| §7 | L2078-2184 | state.json schema v2 | ⚠️(M) | 實際為 PlaybookCheckpoint `AutoClaude/autoclaude/utils/checkpoint_manager.py:30-83`（含 integration_queue）＋checksum `AutoClaude/autoclaude/infra/repositories/file_state_repository.py:256-276`＋原子寫入 `:176-216`；RELAY 狀態塊 `tools/session_resume_planner.py:354,363,383` | 缺 agents[]／quota_snapshot／結構化 resume_plan（多 Agent 才需要） |
| §8-1 | L2190 | 非預期 429（推論端） | ⚠️(M) | 引擎端：limit 字樣→halt `AutoClaude/autoclaude/plugins/token_guard/policy.py:194`、`AutoClaude/autoclaude/core/kernel.py:215`；地板 `tools/lib/quota_gate.py:768` | 無 Retry-After 遵循／full-jitter／5 次重試；全 docs（帳本／ADR／證據檔）零決策記錄 |
| §8-1b | L2191 | 遙測端 429＝量不到 | ✅ | `tools/lib/quota_meter.py:141,782`（http-429-unmeasured）；`tools/lib/quota_messages.py:503`；`tools/tests/test_quota_policy.py:4210`；DEF-200-197/459 fixed | — |
| §8-2 | L2192 | 重置時間漂移 | ⚠️(S) | 同 §4.5.10 | 同 §4.5.10 |
| §8-3 | L2193 | git index.lock 陳舊檢查 | ❌ | 零命中；唯一現象＝R206 證據檔瞬時鎖 rc=128、數秒自解（`docs/06_quality/CrossPlatform_R206_FiveQuestion_MacRound_Q4Regen_CarriersQuoteFilter_Evidence.md:133`，非陳舊鎖） | 暴露弱（retry 即過） |
| §8-4 | L2194 | 斷電／checksum 回退 | ✅ | `AutoClaude/autoclaude/infra/repositories/file_state_repository.py:42,101,107,176,256`；`AutoClaude/tests/test_r100_power_loss_protection.py` | — |
| §8-5 | L2195 | 等待中睡著 | ⚠️(M) | OS 排程 StartWhenAvailable／WakeToRun（根 CLAUDE.md 取證規則）＋姿態出聲 `tools/lib/endurance_env.py:356-397` | 引擎路徑無時鐘跳躍偵測（見 §4.5.2） |
| §8-6 | L2196 | 遙測永久失效 | ✅ | 同 §4.1.5 | — |
| §8-7 | L2197 | 同帳號多 Daemon 超燒 | ⚠️(S) | 同 §4.7 | 同 §4.7 |
| §8-8 | L2198 | 髒污工作樹 | ✅ | 同 §4.5.9 | — |
| §8-9 | L2199 | Agent 卡死／NEEDS_HUMAN | ⚠️(S) | step timeout→ESCALATION `AutoClaude/autoclaude/core/kernel.py:184`；無進度即停 `tools/lib/relay_machine.py:214,293` | `NEEDS_HUMAN` 零命中 |
| §8-10 | L2200 | 喚醒後 context 不可用→FRESH | ✅ | `tools/session_resume_planner.py:1136-1160` | — |
| §8-11 | L2201 | 整合驗證失敗 | ⚠️(L) | 同 §6.2-1 | 同 §6.2-1 |
| §8-12 | L2202 | Prompt injection | ⚠️(S) | allowlist `AutoClaude/autoclaude/infra/adapters/sdk_executor_adapter.py:60`；`.claude/settings.unattended.json`（allow 16／deny 9） | 無『網路存取需確認』獨立層 |
| §8-13 | L2203 | CLI 版本升級 | ⚠️(S) | 同 §6.2-2 | 同 §6.2-2 |
| §8-14 | L2204 | 磁碟空間不足 | ✅ | 同 §6.2-3 | — |
| §9-指標 | L2212-2226 | 12 個 Prometheus 指標 | ❌ | prometheus／otlp／`autoclaude_*` 零命中；等價痕跡＝`quota_burn.jsonl`（`tools/lib/quota_gate.py:306`，本機 399 列自 2026-08-12） | R98 P3 評估項；需先確認有無下游消費者 |
| §9-日誌 | L2228 | 結構化決策日誌 | ⚠️(S) | JSONL 痕跡家族 `tools/lib/quota_gate.py:306,633,665`、`tools/lib/quota_escalation.py:352` | 非逐決策全量 |
| §9-告警 | L2230 | 告警（DRAINING 以上／DIRTY_UNSAVED／NEEDS_HUMAN／429 突增） | ⚠️(S) | halt／prepare 桌面通知 `tools/lib/quota_escalation.py:549,770`；DIRTY_UNSAVED 走 notifier `AutoClaude/autoclaude/core/wiring.py:75`；遙測全失效＝stderr＋模型面 `tools/lib/quota_gate.py:665` | `NEEDS_HUMAN`／429 突增零命中 |
| §12-憑證 | L2295 | 憑證唯讀、不落痕跡 | ✅ | `tools/lib/quota_meter.py:298-300`、`:216`（macOS Keychain） | — |
| §12-權限旗標 | L2296 | 不預設 skip-permissions／白名單／bypass 需容器偵測 | ⚠️(S) | 預設與喚醒窗皆不用 bypass：`tools/lib/resume_route.py:114`（acceptEdits＋settings）；`--dangerously-skip-permissions` 在 `tools/`／`.claude/`／`AutoClaude/autoclaude/` 僅註解 `AutoClaude/autoclaude/utils/config.py:138` | `ALLOW_PERMISSION_BYPASS` 容器偵測零命中（§6.1-8）；引擎 `ExecutorConfig.permission_mode` 允許 bypassPermissions 且無容器偵測 `AutoClaude/autoclaude/utils/config.py:401-403` |
| §12-寫入範圍 | L2297 | 寫入範圍／治理檔禁寫 | ⚠️(S) | `.claude/hooks/block_destructive_git.py:1443-1459`（`_GOV_EXACT`＋`.autoclaude/` 前綴） | 『每 Agent 只寫自己 worktree』靠原生 isolation；`~/.ssh` 等未列 |
| §12-injection | L2298 | prompt injection／狀態回報 schema | ⚠️(S) | `AutoClaude/autoclaude/infra/adapters/sdk_executor_adapter.py:60` | 狀態回報＝一般型別化 dataclass，非針對偽造設計 |
| §12-命令執行 | L2299 | 命令來自設定、state 不含可執行字串 | ✅ | `tools/lib/resume_route.py:129,150`（argv 由參數組裝）；RELAY 為參數 `tools/session_resume_planner.py:354` | — |
| §12-日誌 | L2300 | 日誌遮蔽 | ⚠️(S) | token 不落痕跡 by design（`tools/lib/quota_meter.py:298`）；`AutoClaude/autoclaude/infra/repositories/pg_state_repository.py:75`（_redact） | 無全域 `REDACT_SECRETS_IN_LOGS` 開關 |
| §12-供應鏈 | L2301 | 不得無人確認新增依賴／postinstall | ⚠️(S) | 無人喚醒窗 allowlist 預設拒絕 `.claude/settings.unattended.json` | 無顯式 install 規則；引擎路徑未覆蓋 |
| §13-禁令 | L2307-2311 | 三項禁令（帳號輪替／繞限流／高頻探測） | ✅ | 全庫零帳號輪替／池化／憑證共享／偽裝；一帳一帳本 `tools/lib/quota_gate.py:164`；TTL≥180s `:168` | — |
| §13-條款 | L2313 | 使用條款人工檢核 | ❌ | docs 除 PRD 與 R98 外零記錄（grep） | 人工事項，非程式碼缺口 |
| P0 | L2413-2418 | P0 觀測 | ⚠️(M) | `tools/lib/quota_meter.py` --watch；burn ledger `tools/lib/quota_gate.py:306`（本機 `~/.autosdd/traces/quota_burn.jsonl` 399 列） | statusLine→governance.json、OTel→Grafana ❌；出場題『單 Step 燒幾 pp』無資料（step_quota 零命中） |
| P1 | L2420-2425 | P1 保全 | ⚠️(M) | checkpoint 原子＋checksum `AutoClaude/autoclaude/infra/repositories/file_state_repository.py:176-276`；resume ✅ | PreCompact hook ❌、5 秒落盤計時 ❌ |
| P2 | L2427-2432 | P2 配速 | ⚠️(M) | pace_index ✅ `tools/lib/quota_pace.py:213`；性質測試 `tools/tests/test_quota_policy.py` | 離線模擬器 ❌、DRY_RUN 一週 ❌ |
| P3 | L2434-2438 | P3 閘門 | ⚠️(S) | PreToolUse 攔截 Agent／Workflow `.claude/hooks/context_budget_guard.py`＋`tools/lib/quota_gate.py:1046` | 動態 `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` 無（hook 直接 deny）；模型降級致動器僅建議 |
| P4 | L2440-2442 | P4 韌性 | ⚠️(M) | 週額度長休眠 ✅ `tools/session_resume_planner.py:776`；仲裁 ⚠️ §4.7；OVERAGE 事實上 FREEZE `tools/lib/quota_policy.py:131` | 防休眠 ➖、`ALLOW_WITH_CAP`／首次動用告警 ❌ |
| P5 | L2444-2446 | P5 硬化 | ⚠️(M) | 安全 §12 ✅/⚠️；不變式 §6.1 ⚠️；CLI 版本檢查 ✅（清單過期） | 24 小時端到端 ❌ |
| §10 | L2234-2247 | v1→v2 設定遷移 | ➖ | v1 從未實作（R98 §1.11）⇒ 無遷移對象 | — |
| §11.1 | L2251-2254 | 零 Token 遙測 6h 驗證 | ❌ | 未見 6 小時純遙測驗證紀錄（docs grep） | 非程式碼缺口（需人工長跑） |
| §11.2 | L2256-2264 | 離線模擬器＋性質測試 | ⚠️(M) | 性質測試 `tools/tests/test_quota_policy.py:794`（單調）、`:3036`（穩定）；無獨立模擬器、無 §4.2.7 七情境斷言、無 DRY_RUN 一週 | 『重置後不暴衝』被實況推翻（C1） |
| §11.3 | L2266-2270 | 凍結與喚醒（5s／kill -9／喚醒成本／FRESH） | ⚠️(M) | kill -9 回退 ✅ `AutoClaude/tests/test_r100_power_loss_protection.py`；FRESH 降級 ✅ `tools/session_resume_planner.py:1136` | 5 秒計時、`resume_cost_pp` 零命中 |
| §11.4 | L2272-2274 | 週上限長休眠 | ✅ | `tools/session_resume_planner.py:776`；`tools/tests/test_quota_policy.py:2373`（halt 依最早可 reset 軸武裝） | 週軸門檻 95 非 90（C8） |
| §11.5 | L2276-2278 | 防休眠驗收 | ➖ | 同 §4.6 | — |
| §11.6 | L2280-2281 | 多 Agent 隔離與整合 | ❌ | 同 §4.4.2 | — |
| §11.7 | L2283-2284 | 多實例配額 | ⚠️(S) | 派發帳測試僅在 `tools/tests/test_context_budget_guard.py`（claim_dispatch／count_dispatches） | 無『兩專案併發≤1.2×』整合測試 |
| §11.8 | L2286-2289 | 24h 端到端 | ⚠️(M) | PRD 修訂表 `L20`（v2.1.13）記 2026-08-31 單次 reset 喚醒實戰全通 | 無 24h／≥4 次 reset 紀錄 |
| §15.5 | L2448-2461 | 紅線 1~12 | ⚠️(S) | ✅1,3,4,6,8,9,10,12（`tools/lib/quota_meter.py:76`、根 CLAUDE.md 工具選型表、`.claude/hooks/block_destructive_git.py:1443`）；⚠️2（FREEZE 事實成立、無 ALLOW_WITH_CAP）、11（清單過期）；➖5,7 | — |

> §14（路線圖）已被 §15.4 取代，不計列；附錄 A（問題清冊）為歷史對照，不計列；附錄 B 的 [需核對]／B.3 見 §4。

### 2.2 修憲施工圖（`docs/04_planning/PRD_Amendment_R*.md` 7 份，PRD 修訂表 v2.1.10~v2.1.15 的施工圖；『不疊層』判例＝條文不併入 PRD 本文）

| ID | 施工圖 | 內容 | 狀態 | 證據 | 缺口／備註 |
| :--- | :--- | :--- | :---: | :--- | :--- |
| A1 | R108 配速批 W0~W2.5 | DEF-200-200 row_of 落 resets_at／DEF-200-198 cap 夾 1.0＋『等同無節流』出聲／DEF-200-197 429→unmeasured＋Retry-After 旁檔 | ✅ | `tools/lib/quota_pace.py:625`；`tools/lib/quota_policy.py:449`（min(1.0,_mult)）；`tools/lib/quota_meter.py:141,782`；`tools/tests/test_quota_policy.py:4161,4210`；DEF-200-197/198/200 fixed | — |
| A2 | R108 配速批 W3 | DEF-200-199：L1-γ＋(4d) 已落地；L2／L3／P16／(a) thrifty floor 未做 | ✅ | `tools/lib/quota_policy.py:597`（_rec_of_gate）；`tools/tests/test_quota_policy.py:4434`；`docs/06_quality/AutoSDD_Defect_Log.md:153`（closed-by-decision 2026-10-05，暴露 0） | L2／L3／P16 屬行為改良，守衛面准入不放行 |
| A3 | R108 配速批 W4／W6 | bursting_ok 接線（B1 出聲／B2 near 條件制）＋must-finish 升 30 分 | ➖ | `tools/lib/quota_pace.py:684`（無生產呼叫端）；`docs/06_quality/AutoSDD_Defect_Log.md:231`（DEF-200-458 closed-by-decision@R209） | 功能願望、查無實損；嚴格版計 ❌ |
| A4 | R108 BurnDown 增補 | §4.2.9 清倉模式（持久落款授權＋kill-switch） | ❌ | `AUTOSDD_QUOTA_BURNDOWN`／burn_down 在 `tools/`、`.claude/`、`AutoClaude/autoclaude/` 零命中；PRD 本文無 §4.2.9（`grep -n '4\.2\.9' PRD`）；帳本無開帳列（DEF-200-232 只收『Proposed→Adopted』） | Adopted 但零落地且無追蹤列；若做＝碰守衛面（quota_policy.decide） |
| A5a | R112 喚醒閉環 REQ-W1／W3／W4／W5／W7 | 撞線→零人工閉環／mac 對等／prepare 預檢／演算法入程式／通知重投 | ✅ | `tools/lib/quota_escalation.py:549,568,770`；`tools/session_resume_planner.py:610,1424`；DEF-200-231/235/236 fixed | — |
| A5b | R112 REQ-W2 無主模式 | 主控 429 死亡時背景 agent 的處置面 | ⚠️(S) | 偵測面已落地 `tools/lib/quota_escalation.py:483,519`（_orphan_watch→orphan_agents_detected）；處置面（cap 收斂、任務書注入無主清單）未做 | DEF-200-234 closed-by-decision@R209（暴露 0） |
| A5c | R112 REQ-W6 喚醒成本治理 | (a) spawn 前授權 fail-fast ✅；(b) 成本閘導出式 ❌；(c) resume_cost_pp 落帳 ❌ | ⚠️(M) | (a) `tools/lib/resume_route.py:160`（preflight_problem）；(b)(c) `resume_cost`／`REPLAY_BUDGET` 零命中，成本閘仍是 32MiB 常數 `tools/session_resume_planner.py:1098` | (b)(c) 為 R112 自述『規格既存實作債』 |
| A6 | R113 最後一哩 G1~G4 | 無頭權限姿態／handback 可見／配額內接力狀態機／哨兵 fire 後重掛 | ✅ | `.claude/settings.unattended.json`；`tools/lib/resume_route.py:65-100,108-126,160`；`tools/lib/relay_machine.py:303,320,434`；tests `tools/tests/test_context_budget_guard.py:3053,3222` | Windows 實機親驗仍待掌舵者 |
| A7 | R121 無人續跑受控 commit／push | §4.5.11 G-a~G-f 六道護欄 | ❌ | Status＝Proposed（`docs/04_planning/PRD_Amendment_R121_UnattendedCommitPush.md:3`）；`AUTOSDD_UNATTENDED_PUSH_OFF` 零命中；`.claude/settings.unattended.json` deny `git commit*`／`git push*` | 最大的『完全不需人』授權缺口；若做＝碰守衛面 |
| A8 | R126 gate 聚合面 (4c) | `gate_excluded=` 可觀測 | ✅ | `tools/lib/quota_policy.py:723-746`；`tools/tests/test_quota_policy.py:4064`；DEF-200-244 fixed@R126 | — |
| A9 | R127 環境鍵前綴對齊 | CONFLICT_POLICY／STATE_RETAIN_VERSIONS／DIRTY_SAVE_RETRIES | ✅ | `AutoClaude/autoclaude/execution/boot_self_check.py:45,48`；`AutoClaude/autoclaude/infra/repositories/file_state_repository.py:42`；`AutoClaude/autoclaude/infra/adapters/dirty_worktree_rescue.py:58`；DEF-200-206 fixed@R127 | — |

## 3. R98『下一波建議任務清單』12 項逐項重驗

| # | R98 項目 | 狀態 | 證據 | 備註 |
| ---: | :--- | :---: | :--- | :--- |
| 1 | P0 前置：quota_gate／quota_policy／planner 三支零餘裕瘦身 | ⚠️ | 本輪現跑 `.venv/bin/python AutoClaude/tools/check_loc_budget.py --json`（rc=0）：ROOT-TOOLS-WARN＝`tools/lib/quota_escalation.py` 400/400、`tools/session_resume_planner.py` 746/750、`tools/lib/quota_gate.py` 495/500；SPECIAL-WARN＝`.claude/hooks/context_budget_guard.py` 1089/1089；`tools/lib/quota_policy.py` assertion 291/400 已不在警告帶（已拆 `quota_policy_env.py` 178、`quota_pace.py` 366） | 三支中只有 quota_policy 解圍；gate／planner／escalation 仍 ≤5 行餘裕 ⇒ 任何落點在此三檔的 W 必須同窗淨減 |
| 2 | §8 三大真空（429 full-jitter／index.lock 陳舊檢查／DIRTY_UNSAVED＋NEEDS_HUMAN） | ❌ | 429 jitter 零命中（jitter 僅 `AutoClaude/autoclaude/infra/adapters/minimax_brain.py:38` 無關）；index.lock 零命中；DIRTY_UNSAVED ✅ `AutoClaude/autoclaude/infra/adapters/dirty_worktree_rescue.py:297`；NEEDS_HUMAN 零命中 | 4 個子項只完成 1 個（25%）；其餘三項全 docs 零決策記錄 |
| 3 | 修復 DEF-200-176（SddToPlaybookAdapter 規格檔選擇歧義） | ✅ | `docs/06_quality/AutoSDD_Defect_Log_archive_67.md:96`（fixed@R99，官方命名優先＋無法唯一鎖定 fail-loud） | — |
| 4 | 以真實 AISDLC_SDD 專案實跑 SCG 閘門 Veto 的 E2E | ❓ | `AutoClaude/tests/integration/test_sdd_bridge/test_topology_bridge_e2e.py:32,61` 以真 AISDLC_SDD_v0.05 渲染器產物測消費端；`SddGovernancePlugin` 真 spec_dir＋真 token 的越閘 Veto 證據未見 | 非 Token PRD 本體；本輪未深查，計 0 |
| 5 | archive_defect_log --apply／snapshot --write 自動化進 nightly | ❌ | `tools/git-hooks/pre-push:501` 僅 `--check`；`*.ps1`／`*.sh`／`*.yml` 無任何 `--apply` 呼叫（grep） | — |
| 6 | §4.2.4 平穩性機制 | ✅ | 見矩陣 §4.2.4；DEF-200-204 fixed@R102（`docs/06_quality/AutoSDD_Defect_Log_archive_67.md:156`） | H1 fixture／H7 占位 60s 為殘留驗收資料債 |
| 7 | §8-4 checksum＋版本保留 | ✅ | `AutoClaude/autoclaude/infra/repositories/file_state_repository.py:42,107,176,256`（R100 P2-C） | — |
| 8 | §9 可觀測性（OTel／Prometheus） | ❌ | 零命中；等價＝JSONL 痕跡家族（見 §9 列） | R98 原建議『先確認有無下游消費者』仍未確認 |
| 9 | §5 API Key 模式 | ❌ | 零命中；docs 零決策記錄 | 建議以修憲標『依設計未實作』（W-A） |
| 10 | §8 items 11~14（整合驗證失敗／CLI 版本／磁碟空間） | ⚠️ | 13 ✅（清單過期）`AutoClaude/autoclaude/execution/boot_self_check.py:155-197`；14 ✅ `:200-253`；11 ⚠️ 掃描已接電、零生產寫者（DEF-200-246） | 3 項中 2.5 項 |
| 11 | §7 state.json v2 多 Agent 陣列 schema | ❌ | agents[]／quota_snapshot／結構化 resume_plan 零命中（checksum／原子寫入／integration_queue 欄位已有，見 #7） | 僅在 Console UI 多服務並行立案後才有意義 |
| 12 | §13 使用條款人工檢核 | ❌ | docs 除 PRD 與 R98 外零記錄（grep） | 人工事項；R98 已指出 |

## 4. `[需核對]`、B.3 與『依設計未實作』現況

### 4.1 `[需核對]` 11 處（`grep -n '需核對' PRD` 實查：標準寫法 9 處＋變體 2 處〔`L1714`『[需核對標頭名稱]』、`L1894`『【需核對旗標名稱】』〕）

| # | PRD 行 | 待核對內容 | 現況 | 解決證據／座標 | 備註 |
| ---: | :--- | :--- | :--- | :--- | :--- |
| 1 | L26 | （說明句）『核實來源是實作內部字串，非官方契約』 | 說明性 | 同 B.0 `L2584-2595` | 非待辦 |
| 2 | L115 | 三種限制的確切名稱／單位／重置語意 | 部分核實 | B-01/B-02 `L2601-2602`；實測 kinds `tools/lib/quota_policy.py:134-147`；重置語意＝滾動視窗只能觀測（`tools/session_resume_planner.py:536`、`tools/probe/reset_window_distribution.py`） | 『以官方文件為準』不可達（B.0：官方網域 403）；本文未回填指針 |
| 3 | L241 | T1 OTel 啟用方式與 metric 名稱 | 已核實（附錄）／未實作 | B-03 `L2603` | T1 從未接線（矩陣 §4.1.1-T1） |
| 4 | L242 | T2 逐字稿路徑與 schema | 已核實＋已用 | B-04 `L2604`；`tools/lib/quota_limits.py:319`、`tools/lib/quota_escalation.py:193-213` | 主文未回填指針 |
| 5 | L491 | 模型降級旗標＋訂閱制是否內建自動降級 | 前半已核實／後半未核實 | 前半 B-11 `L2611`（Agent 工具 schema 本 session 實見 model enum＝sonnet／opus／haiku／fable）；後半無任何記錄（L491 自註『仍未核實』） | W1 相關（見 §6.3） |
| 6 | L987 | §4.3 (a) 內建自動壓縮 (b) headless 可否外部觸發 (c) pre-compact hook | (a)(c) 已核實／(b) 以設計繞過 | B-07 `L2607`；(b)＝改機械 autocompact＋『模型自身打不了 /compact』（`.claude/hooks/context_budget_guard.py:865`；ADR-XPLAT-008）；PreCompact hook 存在但未使用（`.claude/settings.json` 無條目） | — |
| 7 | L1034 | §4.4.3 最大回合數旗標名稱＋headless 訊號落盤 | 旗標存疑／訊號未核實 | B-10 `L2610` 標 ✅，但 CLI 2.1.295 `claude --help` 對 `max-turns` 零命中（本輪實跑，311 行 help 全文 grep）；`--help`／`--version` 會短路未知旗標檢查，無法以它證偽；ADR-XPLAT-014 `L437` 已於 2.1.223 記同結論 | 正面證偽法＝`claude --max-turns 3 mcp list`（零 token、有 MCP 連線副作用），本輪未執行 |
| 8 | L1102 | §4.5.4 旗標與權限模式名稱 | 大致已核實 | `tools/lib/resume_route.py:18`（`--permission-mode`／`--settings` 以 `claude --help` 正面核對）；本輪探針：`claude --permission-mode default --help` rc=0、對照 `--permission-mode zzzz --help` rc=1（choices 錯誤字樣）⇒ `default` 被接受（隱藏別名，help choices 列 manual 不列 default）；`--allowed-tools`／`--resume`／`--model`／`--add-dir` 皆在 help；`--max-turns` 不在 | C3／C4／C7 見 §5 |
| 9 | L1714 | §5 429 回應標頭名稱 | 已核實（附錄） | B-13 `L2613`；實作只消費 `anthropic-organization-id`／`-workspace-id` 雜湊（`tools/lib/quota_meter.py:658`）與 `Retry-After`（旁檔，R190 勘誤 d） | §5 API_KEY 模式本身未實作 |
| 10 | L1894 | §6 AGENT_PERMISSION_MODE 旗標名稱 | 已核實 | B-09 `L2609`；`AutoClaude/autoclaude/utils/config.py:401`（Literal 含 default／acceptEdits／plan／bypassPermissions／dontAsk／auto）；SDK 以 `--permission-mode` 傳（`claude_agent_sdk/_internal/transport/subprocess_cli.py:626-627`） | — |
| 11 | L2313 | §13 使用條款對自動化／未公開端點／無人看管的規定 | 未核實（法務） | B-16 `L2616`＝無法核實；docs 零記錄；B.3 #1 `L2636` | 人工事項；R98 #12 同 |

**共通觀察**：11 處中 8 處的答案其實已在附錄 B（B-01~B-13），但主文沒有回填指針（只有 `L491` 加了 v2.1.4 指針）；真正『未解』的只有 3 件——`L491` 後半（訂閱制是否內建自動降級）、`L1034`（`--max-turns`／headless 訊號落盤）、`L2313`（使用條款）。

### 4.2 附錄 B.3『仍待人工確認』5 項

| # | PRD 行 | 項目 | 現況 |
| ---: | :--- | :--- | :--- |
| 1 | L2636 | 使用條款 | ❌ 零記錄 |
| 2 | L2637 | 帳號是否啟用付費超額／月度上限 | ⚠️ `tools/lib/quota_meter.py:367` 註解曾見 `extra_usage {is_enabled:false, monthly_limit:500}`（一次性觀測）；無人工確認紀錄 |
| 3 | L2638 | 續接長對話的實際額度成本 | ❌ `resume_cost_pp` 全庫零命中（R112 REQ-W6(c) 自述『兩夜皆無此值』） |
| 4 | L2639 | 提示快取 TTL／模型定價 | ❌ B-12 `L2612`／B-15 `L2615` 未核實，無後續 |
| 5 | L2640 | 各方案可見的額度分軌項目 | ⚠️ 本機帳號實測 kinds 已入碼（`tools/lib/quota_policy.py:126-147,478`），其他方案無 |

### 4.3 本輪新增的零 token 旗標探針（claude 2.1.295，rc 逐字）

- `claude --permission-mode default --help` → rc=0（印 help）；對照 `claude --permission-mode zzzz --help` → rc=1，stderr 逐字：`error: option '--permission-mode <mode>' argument 'zzzz' is invalid. Allowed choices are acceptEdits, auto, bypassPermissions, manual, dontAsk, plan.` ⇒ **`default` 被 CLI 接受**（help 的 choices 不列）。
- `claude --max-turns 3 --help` → rc=0；**但對照** `claude --definitelynotaflag --help` 亦 rc=0 ⇒ `--help` 會短路未知旗標檢查，這組探針**不能**證實或證偽 `--max-turns` 存在（與 `AutoClaude/autoclaude/utils/verified_cli_versions.py` 檔頭『`--version` 會短路旗標檢查』同型）。可說的只有：`claude --help` 全文（311 行）對 `max-turns`／`max_turns`／`maxTurns` **零命中**，有 `--max-budget-usd`（僅 `--print`）。

### 4.4 PRD 內『依設計未實作』標記 2 處（`grep -n '依設計未實作'` 實查）

| PRD 行 | 內容 | 現況 | 實況 | 重開條件 |
| :--- | :--- | :--- | :--- | :--- |
| L2033 | R-6.2-2 ③ 註記：DRY_RUN 的語意必須是真的不動作 | closed-by-decision（DEF-200-246，`docs/06_quality/AutoSDD_Defect_Log.md:161`） | 現交付＝桌面 loud＋自檢印 DRY_RUN（`AutoClaude/autoclaude/main.py:99-107`）；`integration_queue` 零生產寫者 | 重開觸發（PRD L2035-2040）：①`autoclaude/` 出現 integration_queue 第一個生產寫者（tripwire `AutoClaude/tests/contract/test_def200246_integration_queue_tripwire.py` 轉紅）；②多 agent worktree 整合功能立案；③出現『哪些 playbook 該被 dry_run 擋』的判準 |
| L2071 | §6.2 驗收 G5：DRY_RUN 真的不動作（零派工／零 worktree 寫入／零排程註冊） | 同上 | `dry_run` 判決未接進執行器；僅 cleanup 走 dry-run（`AutoClaude/autoclaude/main.py:149`） | 同上（單一出處） |

> 建議（見 W-A）：§5（API_KEY 整章）、§6 區塊 15、§6.1 不變式 7、§10 比照此二處，補『依設計未實作』標記＋重開條件，讓分母誠實。這是**決策**不是實作，需掌舵者裁決。

## 5. PRD 條文已被程式實況推翻（修憲候選）

> 判準沿 memory『Token 治理 PRD 是最高憲法＋修憲程序』：『實作沒照 PRD 做』修實作；『PRD 與實測不符』才修憲。下列 12 筆都是後者（或 PRD 內部自相矛盾）。

| ID | 主題 | PRD 座標 | 實況座標 | 性質 | 建議處置 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| C1 | §11.2『重置後不暴衝』：翻頁後第一拍 cap≤cap_notice（BAND_FREE 的 None 不得出現） | PRD `L2261`；另 §4.2.4(c) `L560` 以此為『已有守衛』的論據 | `tools/lib/quota_stability.py:36-37`（free 帶 cap=None 直通並清空持久狀態）；`docs/06_quality/AutoSDD_Defect_Log.md:160`（DEF-200-242 closed-by-decision 2026-10-05，暴露 0，『PRD §11.2 待承重標註維持』） | 已登記（DEF-200-242） | §11.2 該列改寫為『free 帶直通為設計』並刪 L560 括號論據（或指向 DEF-200-242）；否則兩處互相引為依據而實況不成立 |
| C2 | §4.5.3 步驟 1／R-4.5.10-1：喚醒前確認 U5h < RESET_CONFIRM_PERCENT(10) | PRD `L1073`、`L1568`、`L1850` | `tools/lib/quota_gate.py:742-765`（endpoint_probe_verdict：端點新鮮且**每軸 <100%** 即 open）；`RESET_CONFIRM_PERCENT` 全庫零命中 | 新（本輪） | 改寫為『每軸 <100% 且端點新鮮；負向由付費探針拍板（互動）或掛回巡邏（無人）』，或補一個真的 <10% 的確認門檻（會讓『剛翻頁但仍有殘量』的窗被誤判未恢復，需裁決） |
| C3 | §4.5.4 喚醒指令範例與 §4.4.3 帶 `--max-turns 40`；附錄 B-10 標 ✅ | PRD `L1106`、`L1034`、`L2610` | CLI 2.1.295 `claude --help` 對 max-turns 零命中（本輪）；`docs/04_planning/ADR/ADR-XPLAT-014-resume-chain-hardening.md:437`；實際迴圈上界＝1 小時牆鐘 timeout＋`tools/lib/relay_machine.py:105` max_spawns＋INV4 | 已登記（ADR-014 §3.5 Q4①；PRD 修訂表 `L16` 稱『內文對齊＝生效後施工項』，至今未施工） | 刪範例旗標、B-10 改 ⚠️＋註記實測版本 |
| C4 | §4.5.4 範例帶 `--allowed-tools` 白名單 | PRD `L1105` | `tools/lib/resume_route.py:114`（`--permission-mode acceptEdits --settings .claude/settings.unattended.json`，三層白名單住 settings 檔，不用旗標） | 已登記（Q4③，施工項未做） | 範例改『白名單由 unattended settings 承接（unattended_authz／block_destructive_git）』 |
| C5 | §4.5.2／§6：reset 後等多久才叫醒＝RESET_BUFFER_SECONDS=30 | PRD `L1059`、`L1849` | `tools/session_resume_planner.py:217`（RESET_SKEW_SECONDS=120） | 已登記（Q4②，施工項未做） | 合併『一個語意一個名字』＋交叉標註兩值；不合併數值 |
| C6 | §4.5.4 AUTO 判準：RESUME_MAX_TRANSCRIPT_TOKENS=60000（token）；U7d≥weekly_warn 一律 FRESH | PRD `L1094-1096`、`L1855` | `tools/session_resume_planner.py:1097-1098,1112`（AUTOSDD_RESUME_MAX_TRANSCRIPT_BYTES＝32MiB，比的是 `stat().st_size`）；無 weekly→FRESH 規則（`resume_route.py`／planner 內 weekly／seven_day 零命中） | 已登記（Q4④『本批只登記』）＋R112 REQ-W6(b) 提案導出式（未落地） | 標單位差異；weekly→FRESH 規則二選一：補實作或刪條文 |
| C7 | 附錄 B-09 權限模式表含 `default` 並標 ✅ | PRD `L2609` | CLI 2.1.295 `claude --help` choices＝acceptEdits／auto／bypassPermissions／manual／dontAsk／plan（無 default）；但本輪探針 `--permission-mode default --help` rc=0（對照 `zzzz` rc=1）⇒ default 被接受 | 已登記（Q4⑤），本輪補實測 | B-09 註記：default＝隱藏別名（help 不列）；最保守模式 help 名為 manual |
| C8 | 週額度獨立門檻：WEEKLY_WARN/DRAIN/HALT＝70/80/90 → LONG_HIBERNATE；WEEKLY_PACE_CEILING＝1.25/1.50；FIVE_HOUR_PACE_CEILING＝1.25；PACING_MODE | PRD `L472`、`L958-960`、`L1775-1783` | `tools/lib/quota_policy_env.py:61-67,91`（同一組 band 50/70/85/95 套全軸；pace_ceiling 單鍵出廠 1.0）；WEEKLY_*／FIVE_HOUR_PACE_CEILING／PACING_MODE／PACE_MIN_UTILIZATION 零命中 | 新（本輪） | §6 區塊 3/4 改寫為『單一 band 組＋單一 pace_ceiling』並說明 weekly halt＝95、以最早可 reset 軸武裝（R-4.5.6-5）；或補鍵 |
| C9 | §1.2-2 原則：『嚴禁用 Prompt 探測額度』 | PRD `L123` | `tools/session_resume_planner.py:476-516`（probe_quota 後備：互動回合付費 `claude -p ok --model haiku`，`:502`；無人模式 INV1 禁，`:490-497`）；背景＝ADR-XPLAT-005 §3.3 | 新（本輪；有 ADR 背景） | 原則加『互動回合且 L0 零成本端點無法給正向結論時的單次付費探針例外；無人回合零付費』 |
| C10 | §4.5.5：weekly_reset_timestamp 不可得 → 保守推估＋每 30 分鐘輪詢 | PRD `L1126` | `tools/session_resume_planner.py:536`（『不猜』保留，reset 只能觀測不能算）；PRD 自身 §4.5.10 R-4.5.10-2 `L1587-1590`（掛回巡邏） | 新（PRD 內部矛盾） | 刪『保守推估』，改指 §4.5.10 |
| C11 | §6.1 末句：違反→明確錯誤訊息＋非零退出碼；不得以預設值靜默帶過 | PRD `L1947`、`L1963` | `tools/lib/quota_policy_env.py:257-297`（load_policy 越界＝整組退回預設＋回 problems 出聲）；CLI 側 `tools/session_resume_planner.py:1532-1536`（H6/H7 越界 rc=2） | 新（本輪） | 分兩層：hook 側 fail-open＋loud（刻意）／CLI 側拒絕啟動 |
| C12 | §4.1.3 視窗重置判準：跌幅 ≥ RESET_DROP_THRESHOLD(20pp) | PRD `L276`、`L2261` | `tools/lib/quota_pace.py:112`（_ROLLOVER_EPS=0.5：任一下降 >0.5pp 即斷點）；另有 resets_at 過期判準（DEF-200-200 fixed） | 新（低） | 註記實作值與理由（更靈敏、方向安全） |

**N1｜修訂表狀態字面落差（程序債，非條文衝突）**：PRD 座標＝PRD `L10`（v2.1.5『待四方複審後生效』）、`L11`（v2.1.6『規格化後待實作』）、`L13`（v2.1.8『僅完成規格化』）、`L14`（v2.1.9『待再審』）；實況＝對應內容已落地並有複審紀錄：§4.5.6／§4.5.7／§4.5.8（DEF-200-146/148 fixed@R95，`docs/06_quality/AutoSDD_Defect_Log_archive_67.md:159,98`）、§4.5.9／§4.5.10／§6.2／§4.2.4（R100/R102，DEF-200-204/205 fixed；R102 四方終審 4/4 APPROVE_WITH_FIXES，`docs/06_quality/AutoSDD_Defect_Log_archive_67.md:156`）；備註＝是否算『已生效』須掌舵者／程序裁決（R110『未生效修憲不疊層』判例；v2.1.10 列 `L15` 已逐字承認這四列維持待審字面）；本盤點只指出字面與實況的落差。

- 計數：已知且**欠施工**（ADR-XPLAT-014 §3.5 Q4①②③④⑤，PRD 修訂表 `L16` 稱『生效後施工項』，至今 PRD 本文 `L1059/L1105-1106/L1849/L2609-2610` 一字未改）＝C3、C4、C5、C6、C7 共 5 筆；已登記帳列＝C1（DEF-200-242）；**本輪新列**＝C2、C8、C9、C10、C11、C12 共 6 筆。
- 注意連動鎖：PRD 被 `tools/tests/test_context_budget_guard.py:13213-13224`（`PrdDrainPercentMapsToTheBandsTest._PAIRS`，分母直讀 PRD）與 `:13341`（`TELEMETRY_UNMEASURED_CAP` 對映）釘住；改 §6 區塊 2/3 的鍵行前須先跑這兩支。

## 6. 未落地項目排名與本輪 W 候選

### 6.1 未落地清單（按對『無人值守續航』的價值÷成本，並標風險與守衛面）

| 排名 | 項目 | 座標 | 價值（無人值守） | 成本（LOC／檔） | 風險 | 碰守衛面 | 備註 |
| ---: | :--- | :--- | :---: | :--- | :---: | :---: | :--- |
| 1 | `resume_cost_pp` 落帳（＋導出式 RESUME 門檻的資料前置） | PRD `L2223`／`L2269`／`L2425`／`L2471`／`L2490`／`L2638`；R112 REQ-W6(b)(c) | M-H | M：+100 產品碼，tools/lib 2 檔 | L | 否 | **W-B**；喚醒成本全無資料，C6 的單位爭議無從校準 |
| 2 | 引擎獨立跑的額度軸第三方刷新者（排程刷 `quota_meter.py --refresh`） | PRD §3.1／§4.1.1；improving_112 §4-3；`AutoClaude/autoclaude/core/ports/quota_meter.py:15-45` | H（僅引擎獨立跑） | M：安裝器 ~120＋測試 ~100，新檔為主 | M | 否（新檔；須對紅線 1 四條件自證） | **W-C′(i)**；引擎側零寫入者被 `test_r82…:797` 釘住（寫入者留在 harness 才不違 ports 劃界） |
| 3 | R121 無人續跑受控 commit／push | `PRD_Amendment_R121_*.md` §2 G-a~G-f | H | 決策包 S／碼 L | H | **是** | **W-E（只出決策包）**；喚醒窗現能改檔、不能 commit/push |
| 4 | PRD 修憲整理批（C1~C12＋§5 非目標＋修訂表字面＋[需核對] 回指） | §5 全表 | M（間接） | S–M：docs +250~400 | L | 否 | **W-A**；5 筆欠施工自 v2.1.11（2026-09-01） |
| 5 | 引擎分片休眠＋時鐘跳躍＋>2h 拒絕長睡 | PRD `L1056-1068`／`L1112-1127`；`AutoClaude/autoclaude/core/services/auto_resume.py:218,283` | M（僅引擎路徑） | S–M：+60／3 檔 | L | 否 | **W-C′(ii)** |
| 6 | CLI 已驗證清單刷新（2.1.295） | PRD `L2018-2042`；`AutoClaude/autoclaude/utils/verified_cli_versions.py:16` | L–M | S：+25 | L | 否 | **W-D**；現況每次啟動 loud＋DRY_RUN |
| 7 | §4.4.3 Step 硬預算（SDK `max_turns`／quota_pp） | PRD `L1021-1034`；`AutoClaude/autoclaude/infra/adapters/sdk_executor_adapter.py:167-172` | M | M：+60／3 檔 | L–M | 否 | opt-in 旋鈕無校準資料則無實益；`--max-turns` CLI 旗標存疑（C3） |
| 8 | BURN-DOWN 清倉模式 | `PRD_Amendment_R108_BurnDown_Addendum.md` §7 | M（掌舵者原意：額度不用即失效） | L | H | **是**（quota_policy.decide） | Adopted 零落地、無帳列；先開帳列再議 |
| 9 | R-4.5.10-1 行程內重量（≤3 次／≤90s） | PRD `L1567-1585` | L | S–M | M | **是**（quota_gate／planner 零餘裕） | 暴露 0 |
| 10 | 模型降級致動器（W1 之後半：依 U7d_model 觸發） | PRD `L476`／`L487` | M | M | M | **是**（quota_policy／quota_messages） | W1 只補『角色→模型映射』前半 |
| 11 | H1 fixture（37 符號／19 翻動＋時間戳） | PRD `L656`／`L665-685`；DEF-200-204 殘留 | L（測試資料債） | S–M | L | 否 | 原始痕跡 `autosdd_quota_degraded.jsonl` 住系統暫存，重開機即蒸發；本機是否還有 08-21~22 窗未查證；不得以合成序列頂替（PRD `L684-685`） |
| 12 | §8-9 `NEEDS_HUMAN`／§8-1 jitter／§8-3 index.lock／§9 指標 | PRD `L2190,2193,2199`、`L2212` | L | 各 S–M | L–M | 部分 | 全 docs 零決策記錄；暴露弱（見矩陣）；先決策再議 |
| 13 | OVERAGE `ALLOW_WITH_CAP`／首次動用告警 | PRD `L1792-1801` | M（計費安全） | M | M | **是** | 本機帳號 `extra_usage.is_enabled=false`（`tools/lib/quota_meter.py:367`）⇒ 暴露 0 |
| 14 | §5 API_KEY 模式／§4.4.2 整合佇列／§7 多 Agent state／§11.6 | 各章 | — | L | — | — | 建議決策式收斂（標依設計未實作）而非實作 |
| 15 | §11.8 24h 端到端／§11.1 6h 零 token 驗證／§13 使用條款 | 各章 | M（證據） | 時間成本高 | L | 否 | 非程式碼缺口 |

### 6.2 本輪 W 候選（最多 5 個；不含已定的 W1）

| 排名 | W 項 | 價值 | 成本 | 風險 | 碰守衛面 | 估 LOC（產品／測試） |
| ---: | :--- | :---: | :---: | :---: | :---: | :--- |
| 1 | **W-B** `resume_cost_pp` 喚醒成本落帳 | M-H | M | L | 否 | +100／+120~150 |
| 2 | **W-C′** 引擎無人值守硬化包：(i) 第三方額度刷新者 (ii) 分片休眠＋長睡拒絕 | H（僅引擎獨立跑）| M–L | M | 否（新檔／AutoClaude 子專案） | (i) ~120／~100；(ii) +60／+100~130 |
| 3 | **W-E** R121 受控 commit/push：只出決策包 | H（碼面）| S（決策）| H（碼面）| 決策包否／碼面**是** | 0／0（決策後 ~200／~300） |
| 4 | **W-A** PRD 修憲整理批（docs） | M | S–M | L | 否 | docs +250~400／+60~90 |
| 5 | **W-D** CLI 已驗證清單刷新 | L–M | S | L | 否 | +25／+20 |

排序理由：W-B 是唯一『補資料而非補機制』且完全避開守衛面的項目（PRD 自己在 §15.4 P1 `L2425` 說這個數字『會影響後續所有設計』）；W-C′ 補的是 PRD 真正的主角（AutoClaude 引擎）在無人看管下**沒有額度軸**與**單次長睡**這兩個已被自己的檔頭與測試承認的缺口，且新檔為主、不碰守衛面；W-E 單位成本最低而解鎖價值最高，但碼面必碰守衛面，所以本輪只收決策；W-A 是不寫守衛碼就能讓覆蓋度數字變誠實的唯一路；W-D 小而低風險。W-B／W-C′ 的鎖持有面不重疊（`tools/lib`＋`tools/tests` 對 `AutoClaude/`＋`tools/install_*`）。

#### W-B｜`resume_cost_pp` 喚醒成本落帳（PRD `L2223`／`L2269`／`L2425`／`L2471`／`L2490`／`L2638`；R112 REQ-W6(c)）

- **要做什麼**：無人續跑每個窗收尾時，記錄『該窗第一個 assistant 請求的實際輸入成本』並落一行 jsonl：`{session_id, relay_seq, first_assistant_ts, input_tokens, cache_creation_input_tokens, cache_read_input_tokens, pct_before, pct_after, measured}`；量不到寫 `measured:false`，**不得寫 0**。資料全部來自本機逐字稿（零 token、零網路）：第一筆 `type=assistant` 且時間戳晚於該窗 spawn 的 `message.usage`；`pct_before/after` 只在兩次額度快取讀數皆量得到時才填。用途：(i) 校準 `AUTOSDD_RESUME_MAX_TRANSCRIPT_BYTES`（C6）；(ii) 為 R112 REQ-W6(b) 導出式門檻鋪資料；(iii) 補 §11.3『記錄本次喚醒的實際額度成本』與 §9 `autoclaude_resume_cost_pp` 的資料面。
- **動哪些檔**：新 `tools/lib/resume_cost.py`（純函式與 I/O 分離，~90 assertion 行，`guardrail_lib` ≤400）；`tools/lib/relay_machine.py:434`（`settle_window` 收尾處 +≈8 行；現 251/400 assertion）；只讀引用 `tools/lib/endurance_env.py:147`（trace_dir）、`tools/lib/quota_ledger.py:298`（append_record）、`tools/lib/quota_gate.py:306`（額度快取讀法）。**spawn 時刻**：`spawn_at` 目前只是 `_run_resume` 的區域變數（`tools/session_resume_planner.py:1181`），planner 餘裕 4 行且屬守衛面 ⇒ 不要動它，改在逐字稿內以『最後一筆早於 `state['reset_at']` 的 assistant 之後的第一筆』定位（`state['transcript']` 已有，`tools/lib/relay_machine.py:369-381`）。
- **估 LOC**：產品碼 +100；測試 +120~150。
- **測試**：新 `tools/tests/test_resume_cost.py`——(1) 合成逐字稿：首筆 assistant usage 取值正確、cache_creation／cache_read 分流；(2) 無 usage 欄／逐字稿缺席／無 assistant ⇒ `measured:false` 且數值欄不為 0（『量不到 ≠ 量到零』紀律）；(3) 零喚醒 ⇒ 痕跡檔位元組數不變（可偵測性鎖，同 §4.5.10 E5）；(4) 原子 append 不掉行；(5) 既有 `ResumeTickWritesStateOnlyAfterConfirmingTest` 不得轉紅（settle_window 契約）；(6) AST 鎖：`resume_cost.py` 不得 import `quota_gate`／`quota_escalation`（防成環，同 `tools/lib/quota_availability.py` 檔頭判詞）。
- **守衛面**：否（`relay_machine.py` 與新檔皆不在〈守衛面准入〉清單；`.claude/hooks/block_destructive_git.py:1443-1459` 的 `_GOV_EXACT` 亦不含 relay_machine）；`tools/session_resume_planner.py` 零改動。
- **價值／成本／風險**：M-H／M／L。注意：`tools/tests/` 新檔要走棘輪表同步（memory『tools/tests 改動要同步多張棘輪表』）、commit 前最後一步回填 ONBOARDING 表②；與 W1 若同動 `tools/tests/` 須串行（鐵律七檢查表 #2）。

#### W-C′｜AutoClaude 引擎無人值守硬化包（兩個可獨立拆包的子項）

**(i) 第三方額度刷新者**（improving_112 §4-3；`AutoClaude/autoclaude/core/ports/quota_meter.py:15-45` 劃界自陳『缺的是刷新者不是讀者』）

- **要做什麼**：補『第三方寫入者』——一個週期性（≤300s，≥`QUOTA_CACHE_TTL_SECONDS`=180s 以守 PRD §15.5 紅線 1 (c)）執行既有刷新 CLI `python tools/lib/quota_meter.py --refresh`（`tools/lib/quota_meter.py:891`，註明『fire-and-forget 刷新器用』）的排程工作，使 AutoClaude 獨立跑（無 Claude Code session）時 `FileQuotaMeterAdapter` 的快取不過期（現況 TTL 1800s 一過即回 None＝量不到＝引擎側**不擋**，`AutoClaude/autoclaude/infra/adapters/file_quota_meter.py:79,121`）。**不**把 harness 路徑寫進 `autoclaude/` 套件（ports 檔頭三條硬邊界①②③）；寫入者仍只在 harness 側 ⇒ `AutoClaude/tests/test_r82_quota_axis_and_shipped_defaults.py:797-830` 的『引擎側零寫入者』釘住不動。載體沿 `tools/install_windows_nightly.ps1`／`tools/install_mac_nightly.sh` 的安裝器體例（哨兵專用的 `tools/lib/schedule_backend.py` `arm()`〔`:312,415,824`〕是一次性／巡邏語意，不適合直接套）。
- **動哪些檔**：新 `tools/install_quota_refresher.ps1`／`.sh`（或單支 py 依平台分派）；`tools/lib/quota_meter.py` 零改動（CLI 已有）；同 commit 更新 `AutoClaude/autoclaude/core/ports/quota_meter.py:15-45` 散文（『刷新者已有，需安裝』）而不動 `AutoClaude/tests/test_r82_quota_axis_and_shipped_defaults.py:797` 判準。
- **估 LOC**：安裝器 ~120（雙平台）＋測試 ~100。
- **測試**：安裝器紅綠自證——週期 <TTL 必紅；命令不含 `--refresh` 必紅；取證輸出含排程器自報憑證（Windows `NextRunTime`／mac `launchctl` rc，根 CLAUDE.md 反事後諸葛）；`.ps1` CRLF／`.sh` LF／exec bit 鐵律三機械物不得紅；工作名**不得**落入 `AutoSDD_Sentinel_*` 前綴（哨兵 GC 會碰，DEF-200-281／455 家族）。
- **守衛面**：否（新檔；`tools/lib/quota_meter.py` 零改動）。但『新增週期性打真實 usage 端點的排程』須逐項對 §15.5 紅線 1 四條件（唯讀 GET／單一程式站點／TTL≥180s／失效降級出聲）自證；已知邊界：睡著的 Mac／關機的 Windows 不會跑（同根 CLAUDE.md〈mac 已知邊界〉）。
- **價值／成本／風險**：H（僅引擎獨立跑；有 Claude Code session 時 PostToolUse 每 180s 已在刷）／M／M。

**(ii) 分片休眠＋長睡拒絕**（PRD §4.5.2／§4.5.5；`AutoClaude/autoclaude/core/services/auto_resume.py:218,283`）

- **要做什麼**：`AutoResumeService` 兩處 `time.sleep(wait_secs)`（`:218` checkpoint 續跑、`:283` halt 等待）改走純函式 `sliced_sleep(wait, slice_s, tol_s, wall, mono, sleep, stop)`：每片比較 wall／monotonic 增量差 >tol ⇒ 重算剩餘（`seconds_until_resume`）；收到中斷（既有 hotkey／`_interrupt_event`）優雅退出；剩餘 >`max_inprocess_wait`（PRD 7200s）時**不**長睡，以『checkpoint 已落＋非零 rc＋明示需外部續跑』返回（OS 排程交棒屬根層 `tools/`，`.importlinter` 禁 autoclaude 反向 import `tools/`，引擎側只做拒絕＋明示，交棒由根層哨兵承接）。
- **動哪些檔**：`AutoClaude/autoclaude/core/services/auto_resume.py:218,283`；新 `AutoClaude/autoclaude/utils/sliced_sleep.py`（~45 行）；`AutoClaude/autoclaude/utils/config.py:253-255`（token_guard 加三欄 `sleep_slice_seconds`／`clock_jump_tolerance_seconds`／`max_inprocess_wait_seconds`，`Field(ge,le)`）；測試新 `AutoClaude/tests/utils/test_sliced_sleep.py`＋既有 auto_resume 相關鎖。
- **估 LOC**：產品 +60（含 config）；測試 +100~130。
- **測試**：注入式時鐘（不真睡）：(1) 正常睡滿；(2) wall 跳躍 >tol ⇒ 重算並可提早結束；(3) 剩餘 >max_inprocess ⇒ 拒絕長睡、rc 非零、checkpoint 已落；(4) 中斷 ⇒ 優雅退出；(5) wait≤0 ⇒ 零 sleep；(6) AST 鎖：`auto_resume.py` 不得再直接呼叫 `time.sleep`；AutoClaude 覆蓋 ≥90%、`lint-imports` rc=0。
- **守衛面**：否（AutoClaude 子專案，不在根守衛面清單）。先現查 LOC 餘裕：`auto_resume.py` raw 442 行，所屬 tier 餘裕以 `check_loc_budget --json` 為準。
- **價值／成本／風險**：M（PRD §4.5.2 針對的『睡著後醒來超時／無法修正時鐘』病；macOS 睡眠期間的補睡行為本輪未實測）／S–M／L。

#### W-E｜R121 受控 commit／push：本輪只出決策包

- **要做什麼**：不寫碼。把 `docs/04_planning/PRD_Amendment_R121_UnattendedCommitPush.md` §4 的 Q-A／Q-B／Q-C 整成一頁式裁決單，並對 G-a~G-f 逐條標『現有機械物／缺哪支』：G-a（本機全套 rc=0）→`tools/run_root_unittests.py` 現有；G-b（四方複審紀錄可稽核）→**無機械物**；G-c（毀滅性仍禁）→`.claude/hooks/block_destructive_git.py` 現有；G-d（治理面唯讀）→`:1443-1459` 現有；G-e（`AUTOSDD_UNATTENDED_PUSH_OFF` 出口）→零命中、須新增；G-f（全程留痕）→`tools/lib/relay_machine.py` 的 trace 可承接。
- **若裁決通過，碼面落點（本輪不做）**：`.claude/settings.unattended.json`（deny `git commit*`／`git push*` 行）、`tools/lib/unattended_authz.py:71`（authz_hits）、`.claude/hooks/block_destructive_git.py`（`AUTOSDD_UNATTENDED` 分支）、`tools/lib/resume_route.py:108-126`（posture argv）、新 env `AUTOSDD_UNATTENDED_PUSH_OFF`。
- **估 LOC**：決策包 docs +40~60；碼面（決策後）產品 ~200、測試 ~300。
- **守衛面**：決策包否；碼面**是**（`.claude/settings*.json` ＋ hooks）⇒ R197 准入須先附暴露證據。『掌舵者 2026-09-02 選全自動』是**意向**不是暴露證據；暴露證據應是一次有 sid＋seq 的『喚醒窗改完檔卻因不能 commit，隔日才由人收尾』實錄（本輪未查到）。
- **價值／成本／風險**：H（碼面）／S（決策）→L（碼）／H（碼面）。DEF-200-231 ② 已讓喚醒窗能改檔，commit/push 是續跑鏈『完全不需人』的最後一段（R121 §5 自述）。

#### W-A｜PRD 修憲整理批（docs）

- **要做什麼**：(1) §5 的 C1~C12 逐條施工；(2) §5／§6 區塊 15／§6.1 不變式 7／§10 標『依設計未實作』＋重開條件（**需掌舵者裁決**：API_KEY 是否為非目標）；(3) 修訂表 `L10／L11／L13／L14` 字面回填（引 R100／R102／R107 複審紀錄座標；是否算『已生效』由掌舵者／程序裁）；(4) 十一處 `[需核對]` 補回指附錄 B 條目；(5) §6 前加『PRD 鍵↔實作鍵』對照表（本檔 §7 的 78 鍵即初稿）；(6) 新增 v2.1.16 修訂表列＋施工圖 `docs/04_planning/PRD_Amendment_R1xx_*.md`（R110『不疊層』判例：條文不併入、只加註記與痕跡）。
- **動哪些檔**：`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`（`L10-14,L123,L472,L560,L958-960,L1059,L1073,L1094-1096,L1105-1106,L1126,L1568,L1705-1719,L1775-1783,L1849-1855,L1947,L2261,L2609-2610`）；新施工圖；`tools/tests/test_context_budget_guard.py:13213-13224`（`_PAIRS` 分母直讀 PRD）；`tools/lib/governance_docs.py`（登記新文件）。
- **估 LOC**：docs +250~400（PRD 淨 +80~150）；測試 +60~90。
- **測試**：(1) 分母鎖：PRD §6 `.env` 區塊每個鍵必須在『實作對映表／依設計未實作標記／實作面鍵』三者之一登記（仿 `_PAIRS`）；(2) 反向存在鎖：已改名／廢除的字面（`RESET_CONFIRM_PERCENT`、`--max-turns 40` 等）不得再以『現行規範』出現（帶『歷史／已廢除／v2.1.x 修憲』標記的行豁免）；(3) 既有 `PrdDrainPercentMapsToTheBandsTest`（`tools/tests/test_context_budget_guard.py:13205`）與 `:13341` 對映鎖不得紅。
- **守衛面**：否（docs＋tests）。程序：修憲＝四方獨立審查→全修→複審全 APPROVE（memory『四方審查閉環』）；子 agent model=sonnet、派工前先 `--pace`。
- **價值／成本／風險**：M（間接）／S–M／L（唯一風險＝改到被後設鎖直讀的行）。

#### W-D｜CLI 已驗證清單刷新

- **要做什麼**：`VERIFIED_CLI_VERSIONS` 補 `2.1.295`，`verified` 欄只寫本輪零 token 實測事實：`claude --version`＝`2.1.295 (Claude Code)`；`--permission-mode default` 被接受（對照 zzzz 被拒，見 §4.3）；`--settings`／`--add-dir`／`--allowed-tools`／`--resume`／`--model` 在 help；`--max-turns` 不在 help（**不得寫『存在』**）。動機：現況每次 `python -m autoclaude` 都 loud＋DRY_RUN（`AutoClaude/autoclaude/execution/boot_self_check.py:298-301`），噪音讓 R-6.2-2 的 loud 失去鑑別力。
- **動哪些檔**：`AutoClaude/autoclaude/utils/verified_cli_versions.py:16-34`；`AutoClaude/tests/test_r100_boot_self_check.py`（+1~2 測）。
- **估 LOC**：+25 data；測試 +20。
- **測試**：(1) 每筆 `verified`／`source` 非空；(2) `cli_version_verdict('2.1.295')` ⇒ dry_run False；(3) 反向：`verified` 文字不得含 `--max-turns` 字面（防把沒驗過的寫成已驗）。
- **守衛面**：否。**不要**做成『自動寫入清單』——檔頭明文拒絕『全部已驗證』的失效形態。
- **價值／成本／風險**：L–M／S／L。

**並行派工防互踩（根 CLAUDE.md 鐵律七檢查表）**：W-A（PRD＋`tools/tests` 後設鎖）、W-B（`tools/lib`＋`tools/tests`）與 W1（ENV_SPEC `tools/lib/quota_policy_env.py`＋`.env.example`＋`tools/tests`）三者都動 `tools/tests/` 棘輪表 ⇒ **串行**、repin 只准收尾單人窗口；W-C′(i)（新 `tools/install_*`＋少量 `tools/tests`）亦動 `tools/tests/` ⇒ 與前三者同列串行；W-C′(ii)／W-D 在 `AutoClaude/`，鎖持有面不重疊，可與前者並行，但任何測試檔位元組變動都會漂移 ONBOARDING 表②指紋 ⇒ 回填單人、commit 前最後一步。建議把 W1＋W-B 設為同一條串行鏈，W-C′(ii)＋W-D 設為另一條 AutoClaude 鏈。

### 6.3 W1（模型角色參數化）相關的 PRD 條文座標

| 座標 | 條文 | 現況 |
| :--- | :--- | :--- |
| PRD `L476`（§4.2.3 步驟 7）、`L487`（致動器表『模型層級降級』）、`L199`（§3.2 THROTTLING 動作含模型降級）、`L150`（`U7d_model`） | 『`U7d_model ≥ MODEL_DOWNGRADE_PERCENT → 模型降級，併發不變`』；觸發＝THROTTLING 或 U7d_model 超標 | 只有**建議行**：`tools/lib/quota_policy.py:319-323,793`（`Decision.model_hint`）、`tools/lib/quota_messages.py:810`；致動器零（`CLAUDE_CODE_SUBAGENT_MODEL` 全庫零命中）；`MODEL_DOWNGRADE_PERCENT` 只活在註解 `tools/lib/quota_policy.py:470-472`（由 notice 錨點 50 兼任） |
| PRD `L491`（[需核對]） | 前半『具體旗標』已由 B-11 核實；後半『訂閱制是否內建自動降級』**仍未核實** | W1 落地時一併記錄『後半未核實』，避免與官方內建降級互相牴觸（PRD 原則：不牴觸、只在更早水位主動降級） |
| PRD `L2611`（附錄 B-11）、`L2602`（B-02）、`L2436`（§15.4 P3『模型降級致動器（依 seven_day_opus／sonnet 分軌）』）、`L2488`（§15.7『優先投資模型降級與任務篩選』）、`L1776`（§6 `MODEL_DOWNGRADE_PERCENT=50`） | B-11：`--model`；`Agent` 工具 `model` 欄 enum；`CLAUDE_CODE_SUBAGENT_MODEL`；`/model`。本 session 內 Agent 工具 schema 實見 `model` enum＝sonnet／opus／haiku／fable，與 B-11 相符 | 現行『角色→模型』只靠人工紀律（memory『子 agent 用 Sonnet、主控用 Fable』）；工程面既有載體：`AutoClaude/autoclaude/utils/config.py:404`（`ExecutorConfig.model`，None＝SDK 預設，config.yaml 非 .env）、`tools/session_resume_planner.py:476`（探針預設 `model='haiku'`）、`:901`（`--pace --model`）、`AutoClaude/autoclaude/main.py:~181`（`MINIMAX_MODEL` 是 Brain 用，與 Claude 模型無關） |

**判讀**：W1 補的是 §4.2.3b 致動器表『模型降級』格的**前半**（角色→模型映射的設定面）；『依 U7d_model／THROTTLING 自動降級』的**後半**（hint→actuator）仍未做，且會碰守衛面（`quota_policy`／`quota_messages`）。若 W1 把映射放進 `ENV_SPEC`（`tools/lib/quota_policy_env.py:60-143`，非守衛面清單內），務必同步 `.env.example`（生成物，`render_env_example()`；`tools/tests/test_quota_policy.py:1120` M6 雙向鎖）。

### 6.4 不推薦本輪做（及理由）

- **BURN-DOWN 清倉模式**（A4）：Adopted 但零落地、無帳列；若做＝改 `quota_policy.decide()`（守衛面）、需持久落款載體＋四條底線，成本 L、風險 H；先開帳列、補暴露證據再議。
- **R-4.5.10-1 行程內重量**、**H1 fixture**、**NEEDS_HUMAN**、**429 jitter**、**index.lock**、**§9 指標**、**OVERAGE ALLOW_WITH_CAP**：全 docs 零決策記錄且暴露 0／弱；落點多在零餘裕守衛檔；R197『量、不挖』——先決策（標依設計未實作）比先實作划算。
- **§5 API_KEY／§4.4.2 整合佇列／§7 多 Agent state／§11.6**：需多 agent 並行才有意義（DEF-200-246 重開條件②），建議決策式收斂。

### 6.5 improving_112（R95）§4『下輪開場即辦』四項承接現況（控制器草稿 §1 表的『盤點後填』）

| 項 | 內容 | 現況 | 證據 |
| :--- | :--- | :---: | :--- |
| §4-1 | 水位預警哨兵擴充＋PRD v2.1.6 落款 | ✅ 已落地（程序債未清） | 機制：`tools/lib/quota_escalation.py:292,328,525`（B1~B3）、`tools/tests/test_context_budget_guard.py:6945,7057`；帳本 DEF-200-148 fixed@R95（`docs/06_quality/AutoSDD_Defect_Log_archive_67.md:98`）；PRD 修訂表 `L12`（v2.1.7）已寫『落地』，但 `L11`（v2.1.6）仍『規格化後待實作』＝§5 N1 |
| §4-2 | Windows 側待驗清單 | ➖ 本輪不排 | 只能在 Windows 機驗；承接＝`docs/06_quality/CrossPlatform_R210_Debt_Closure_Final_Evidence.md`〈八〉 |
| §4-3 | 引擎側額度軸接電（第三方刷新者） | ❌ 未做，**已知且被測試釘住** | `AutoClaude/autoclaude/core/ports/quota_meter.py:15-45`、`AutoClaude/tests/test_r82_quota_axis_and_shipped_defaults.py:797-830`；`grep -rn '第三方刷新' docs AutoClaude/autoclaude` 只命中 improving_112 ⇒ 帳本／ADR 零追蹤列；建議開帳列或併 W-C′(i)。前置『AutoClaude 總量 cap 重校雙簽程序』本輪未查證 |
| §4-4 | SD/Arch 順手項（prepare 閂鎖鍵、混軸鍵補記來源軸） | ❓ 未查證 | 本輪未逐項重驗 |
## 7. 附錄：§6 78 個 .env 鍵逐鍵普查

> 鍵名取自 PRD §6 區塊（`sed -n 1721,1915p | grep -oE '^[A-Z_0-9]+='`）。『實作面對應』多數是 `AUTOSDD_QUOTA_*`（`tools/lib/quota_policy_env.py:60-143` 的 `ENV_SPEC`，政策 21 鍵＋逃生口 5 鍵）或 AutoClaude `config.yaml` 欄位，不是同名 env。

統計：✅14／⚠️21／❌28／➖15（共 78）。

| PRD 鍵 | 狀態 | 實作面對應／證據 |
| :--- | :---: | :--- |
| `AUTOCLAUDE_AUTH_MODE` | ❌ | 純 OAuth；零命中 |
| `AUTOCLAUDE_ACCOUNT_TYPE` | ➖ | PRD 自註『僅提示性欄位，不得用於推算額度』；零命中 |
| `TELEMETRY_SOURCE_ORDER` | ❌ | 固定鏈 T5→快取→逐字稿地板，寫死於 `tools/lib/quota_gate.py:420`（read_quota） |
| `MONITOR_POLL_INTERVAL_SECONDS` | ⚠️ | 常數 QUOTA_CACHE_TTL_SECONDS=180（`tools/lib/quota_gate.py:168`），非 env |
| `TELEMETRY_TIMEOUT_SECONDS` | ➖ | 被 §4.1.5 取代：過期於 TTL 即 unmeasured（`tools/lib/quota_gate.py:451`） |
| `TELEMETRY_UNMEASURED_CAP` | ✅ | ↔ AUTOSDD_QUOTA_DEGRADED_CAP `tools/lib/quota_policy_env.py:98`；對映鎖 `tools/tests/test_context_budget_guard.py:13341` |
| `LOCAL_ESTIMATE_SAFETY_MARGIN_PP` | ➖ | 無本機推估路徑 |
| `TOKEN_WARN_PERCENT` | ✅ | ↔ AUTOSDD_QUOTA_CONVERGE_PCT `tools/lib/quota_policy_env.py:63`（70）；`_PAIRS` `tools/tests/test_context_budget_guard.py:13213` |
| `TOKEN_DRAIN_PERCENT` | ✅ | ↔ AUTOSDD_QUOTA_PREPARE_PCT `tools/lib/quota_policy_env.py:65`（85） |
| `TOKEN_HALT_PERCENT` | ✅ | ↔ AUTOSDD_QUOTA_HALT_PCT `tools/lib/quota_policy_env.py:67`（95） |
| `ENABLE_WEEKLY_LIMIT_GUARD` | ➖ | 週軸恆參與 band 聚合，無獨立開關（總逃生口 AUTOSDD_QUOTA_GUARD_OFF） |
| `WEEKLY_HALT_PERCENT` | ❌ | C8：週軸與 5h 軸同走 halt_pct＝95 |
| `MODEL_DOWNGRADE_PERCENT` | ⚠️ | 由 notice 錨點（50）兼任，僅『建議』`tools/lib/quota_policy.py:470-472`；無致動器 |
| `PACING_MODE` | ➖ | 只有 PACE_INDEX 路線 |
| `WEEKLY_PACE_CEILING_THROTTLE` | ❌ | C8：單鍵 AUTOSDD_QUOTA_PACE_CEILING（出廠 1.0）`tools/lib/quota_policy_env.py:91` |
| `WEEKLY_PACE_CEILING_DRAIN` | ❌ | 同上 |
| `FIVE_HOUR_PACE_CEILING` | ❌ | 同上 |
| `PACE_MIN_UTILIZATION` | ❌ | 零命中 |
| `WEEKLY_WARN_PERCENT` | ❌ | C8 |
| `WEEKLY_DRAIN_PERCENT` | ❌ | C8 |
| `OVERAGE_POLICY` | ⚠️ | 事實上 FREEZE（`tools/lib/quota_policy.py:113-131`、`tools/lib/quota_meter.py:512`）；無鍵、無 ALLOW_WITH_CAP |
| `OVERAGE_HARD_CAP_USD` | ❌ | 零命中 |
| `OVERAGE_ALERT_ON_FIRST_USE` | ❌ | 零命中（僅撞月度上限才 escalate：`tools/lib/quota_limits.py` LIMIT_SPEND） |
| `OVERAGE_MONTHLY_UTILIZATION_HALT` | ❌ | 零命中 |
| `CONTEXT_COMPACT_PERCENT` | ⚠️ | 常數 WARN_RATIO=0.84 `.claude/hooks/context_budget_guard.py:196`，非 env |
| `COMPACT_COST_BUDGET_PP` | ✅ | ↔ AUTOSDD_QUOTA_COMPACT_COST_BUDGET_PP `tools/lib/quota_policy_env.py:75` |
| `COMPACT_MIN_INTERVAL_SECONDS` | ❌ | 零命中 |
| `AGENT_MIN_CONCURRENCY` | ➖ | cap≥1 禁止靜默鎖死（`quota_policy.py` _clamp） |
| `AGENT_DEFAULT_CONCURRENCY` | ➖ | 無 setpoint；band 階梯導出 |
| `AGENT_MAX_CONCURRENCY` | ⚠️ | ↔ AUTOSDD_QUOTA_MAX_FANOUT `tools/lib/quota_policy_env.py:93`（16） |
| `AGENT_THROTTLE_CONCURRENCY` | ⚠️ | ↔ AUTOSDD_QUOTA_CAP_NOTICE／CONVERGE／PREPARE `tools/lib/quota_policy_env.py:81,83,85` |
| `BURN_RATE_EWMA_ALPHA` | ⚠️ | 常數 `tools/lib/quota_pace.py:681`，僅診斷 |
| `CONTROL_INTERVAL_SECONDS` | ➖ | PRD 自註保留相容鍵；實作＝FANOUT_WINDOW_SECONDS `tools/lib/quota_gate.py:164` |
| `AVAILABILITY_EXIT_STREAK` | ✅ | ↔ AUTOSDD_QUOTA_AVAILABILITY_EXIT_STREAK `tools/lib/quota_policy_env.py:111` |
| `AVAILABILITY_MIN_DWELL_SECONDS` | ✅ | ↔ AUTOSDD_QUOTA_AVAILABILITY_MIN_DWELL_SECONDS `tools/lib/quota_policy_env.py:113` |
| `FAIL_SAFE_CONCURRENCY` | ➖ | PRD 自註保留鍵；cap 語意 |
| `ENABLE_BURSTING` | ⚠️ | bursting_ok kwarg 預設 False（`tools/lib/quota_pace.py:684`），無 env、無呼叫端 |
| `BURST_WINDOW_MINUTES` | ⚠️ | kwarg 預設 30（同上） |
| `BURST_MAX_U5H_PERCENT` | ⚠️ | kwarg 預設 60（同上） |
| `BURST_WEEKLY_GUARD_PERCENT` | ⚠️ | kwarg 預設 60（同上） |
| `MAX_STEP_TURNS` | ❌ | 零命中 |
| `MAX_STEP_WALL_SECONDS` | ⚠️ | ↔ playbook.step_timeout_seconds=600 `AutoClaude/autoclaude/utils/config.py:166` |
| `MAX_STEP_QUOTA_PP` | ❌ | 零命中 |
| `DRAIN_BUDGET_FACTOR` | ❌ | 零命中 |
| `AGENT_TERMINATION_GRACE_SECONDS` | ⚠️ | 行為近似：收殺行程樹 `AutoClaude/autoclaude/perception/pty_wrapper.py:355-364`（SIGTERM→SIGKILL）；無 grace 秒數鍵 |
| `RESET_BUFFER_SECONDS` | ⚠️ | ↔ RESET_SKEW_SECONDS=120 `tools/session_resume_planner.py:217`（C5） |
| `RESET_CONFIRM_PERCENT` | ❌ | C2：零命中 |
| `SLEEP_SLICE_SECONDS` | ❌ | 引擎路徑單次 sleep（`AutoClaude/autoclaude/core/services/auto_resume.py:283`） |
| `CLOCK_JUMP_TOLERANCE_SECONDS` | ❌ | 零命中 |
| `MAX_INPROCESS_WAIT_SECONDS` | ❌ | 零命中 |
| `RESUME_STRATEGY` | ⚠️ | AUTO 行為存在（`tools/session_resume_planner.py:1136`），無 env 強制 SESSION_RESUME／FRESH |
| `RESUME_MAX_TRANSCRIPT_TOKENS` | ⚠️ | ↔ AUTOSDD_RESUME_MAX_TRANSCRIPT_BYTES `tools/lib/quota_policy_env.py:126`（bytes，C6） |
| `OS_KEEP_AWAKE_DRIVER` | ➖ | 刻意不做（§4.6） |
| `KEEP_AWAKE_ALLOW_DISPLAY_SLEEP` | ➖ | 同上 |
| `KEEP_AWAKE_VERIFY_ON_START` | ➖ | 替代＝睡眠姿態出聲 `tools/lib/endurance_env.py:356-397` |
| `ENABLE_WORKTREE_ISOLATION` | ➖ | 原生 isolation |
| `AUTOCLAUDE_WORKTREE_DIR` | ➖ | 原生 isolation |
| `INTEGRATION_BRANCH` | ❌ | 零命中 |
| `AUTOCLAUDE_CONFLICT_POLICY` | ✅ | `AutoClaude/autoclaude/execution/boot_self_check.py:45,48` |
| `INTEGRATION_VERIFY_CMD` | ❌ | 零命中 |
| `AUTOCLAUDE_STATE_FILE` | ⚠️ | checkpoint 目錄制（cfg.checkpoint_dir），無單檔路徑鍵 |
| `AUTOCLAUDE_CHECKPOINT_DIR` | ✅ | cfg.checkpoint_dir（`AutoClaude/autoclaude/main.py:136-153`、dirty_worktree_rescue） |
| `STATE_WRITE_MODE` | ✅ | 原子寫入為固定行為 `AutoClaude/autoclaude/infra/repositories/file_state_repository.py:176-216`（無鍵） |
| `AUTOCLAUDE_STATE_RETAIN_VERSIONS` | ✅ | `AutoClaude/autoclaude/infra/repositories/file_state_repository.py:42` |
| `AUTOCLAUDE_DIRTY_SAVE_RETRIES` | ✅ | `AutoClaude/autoclaude/infra/adapters/dirty_worktree_rescue.py:58` |
| `ALLOW_PERMISSION_BYPASS` | ❌ | 零命中；`ExecutorConfig.permission_mode` 允許 bypassPermissions 且無容器偵測 `AutoClaude/autoclaude/utils/config.py:401-403` |
| `AGENT_PERMISSION_MODE` | ✅ | ↔ ExecutorConfig.permission_mode `AutoClaude/autoclaude/utils/config.py:401`（config.yaml，非 .env）；喚醒窗 `tools/lib/resume_route.py:114` |
| `AGENT_ALLOWED_TOOLS` | ✅ | ↔ ExecutorConfig.sdk_tool_allowlist `AutoClaude/autoclaude/utils/config.py:409`；`.claude/settings.unattended.json` |
| `REDACT_SECRETS_IN_LOGS` | ⚠️ | token 不落痕跡 by design；`AutoClaude/autoclaude/infra/repositories/pg_state_repository.py:75`；無全域開關 |
| `LOG_LEVEL` | ⚠️ | AutoClaude logger（`setup_logger(cfg.log_dir)`），無同名鍵 |
| `LOG_FILE` | ⚠️ | cfg.log_dir=logs `AutoClaude/autoclaude/utils/config.py:424` |
| `METRICS_EXPORT` | ❌ | 零命中 |
| `ALERT_WEBHOOK_URL` | ❌ | 僅桌面通知 `tools/lib/quota_escalation.py:549` |
| `DRY_RUN` | ⚠️ | boot_self_check DRY_RUN 文字＋cleanup dry-run（`AutoClaude/autoclaude/main.py:149`）；未接執行器（DEF-200-246） |
| `AUTOCLAUDE_DAEMON_LOCK` | ➖ | 無 Daemon |
| `API_BUDGET_PERIOD` | ❌ | §5 整章未實作 |
| `API_BUDGET_HARD_USD` | ❌ | 同上 |
| `API_AUTO_CONTINUE_NEXT_PERIOD` | ❌ | 同上 |

## 8. 誠實劃界與未查證

- **未重跑任何測試**（任務書禁令）：所有 ✅ 的『有測試』是指測試類別／檔案存在並在 file:line 命中，**不是**本輪重跑綠燈；綠燈基準由主控背景跑（`scratchpad/113/baseline_*.txt`）。
- **R98 #4（SDD 真跑 E2E）本輪未深查**，計 0；它不屬 Token PRD 本體。
- **✅ 的驗收判準『逐格有對應測試』只做抽樣核對**：已確認測試類別／檔案存在並命中行號者＝B1~B3（`tools/tests/test_context_budget_guard.py:6945,7057`）、C1~C4（`:7092`）、E5（`:1569`）、F5（`:13341`）、H 系列類別（`tools/tests/test_quota_policy.py:2828,3036,3681,3781`）、R100 三支 AutoClaude 測試檔；A1~A5、D1~D9、E1~E4、G1~G10 未逐格重驗，依據是對應 DEF 列的『fixed＋四方複審』紀錄（DEF-200-146/148/204/205 等，座標見 §5 N1 與 §3）。
- **行號驗證方式**：腳本確認全檔每個 `path:line` 的路徑存在、行號未超出檔案長度（408 個引用 0 異常）；另隨機抽 70 個引用逐一印出目標行比對語意（1 個歸屬歧義已訂正為全路徑）；**未**對全部 408 個引用逐一做語意核對。
- **Windows 側全部未驗**：本機是 macOS；Windows 排程／PS 5.1／schtasks 路徑的 ✅ 皆來自程式與測試存在，真機親驗仍待掌舵者（memory『R158 待 Windows 親驗』）。
- **§4.5.2 引擎路徑的實害程度未量測**：`time.sleep` 在 macOS 睡眠期間的補睡行為未實驗，只依 PRD §4.5.2 自述與程式現況判定『規範性機制缺漏』。
- **H1 fixture 可否由本機痕跡重建未查證**：`~/.autosdd/traces/quota_burn.jsonl` 存在（399 列自 2026-08-12），但 measured⇄unmeasured 的 U 側來源 `autosdd_quota_degraded.jsonl` 住系統暫存，未確認 08-21~22 窗是否仍在。
- **`--max-turns` 是否被 2.1.295 接受**：help 零命中但 `--help` 短路未知旗標檢查，無法證偽；正面證偽法（`claude --max-turns 3 mcp list`）有 MCP 連線副作用，未執行。
- **覆蓋度權重主觀**：⚠️ 權重與 S/M/L 缺口量級皆由本檔判定；§1.2 已並列敏感度，請以區間而非單點引用。
- **未涵蓋**：附錄 A（43 項 v1 問題清冊）逐條對照未做（歷史對照，非現行規範）；`docs/04_planning/ADR/` 其餘 ADR 的條文未逐條與 PRD 比對。

