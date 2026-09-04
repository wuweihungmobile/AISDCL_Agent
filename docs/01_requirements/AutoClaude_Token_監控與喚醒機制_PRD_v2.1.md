# AutoClaude 核心排程與 Token 治理系統規格說明書 (PRD)

| 文件版本 | 修訂日期 | 狀態 | 核心目標 |
| :---- | :---- | :---- | :---- |
| **v2.1.0 (Revised + Verified)** | 2026-08-14 | Ready for Implementation | 在**遵守** Anthropic 額度限制的前提下，實現零 Token 消耗的額度遙測、可收斂的動態併發配速、以及成本可預期的無損暫停／喚醒 |
| **v2.1.1 (R92 修憲)** | 2026-08-16 | Ready for Implementation | 掌舵者裁決：`CONTEXT_COMPACT_PERCENT` 75→84（§4.3、§6 兩站點），並首次把 context 硬線 94% 入憲（此前僅存在於實作層 `HARD_RATIO`，PRD 未定義）；與額度尺 85/95 錯開保鑑別力。機械 autocompact 設定之取捨見 ADR-XPLAT-008 |
| **v2.1.2（R93 新增）** | 2026-08-16 | Ready for Implementation | 新增 §4.1.4：跨窗攤提的核心指紋隨帳號/方案核心桶集合變化自動分區，解決 `DEF-200-122`（換方案上升跳變污染燃燒率估計）；`DEF-200-114` 的機制本體同輪落地。設計細節見 ADR-XPLAT-009 |
| **v2.1.3（R93 二次訂正）** | 2026-08-16 | Ready for Implementation | 獨立 Architect 複審 REJECT 承接：§4.1.4「同方案換帳號需帳號識別，非本節範圍」與 `docs/06_quality/Quota_R90_CrossAccount_Experiment.md` 實測不符（核心桶集合指紋本身不具身分鑑別力：3 命中 2 假陽性、29% 偽陰性），訂正為已解決——帳號身份訊號（回應標頭雜湊，零額外網路/token/憑證處理）併入核心指紋；補齊「不同方案桶名集合相同」邊界。設計細節見 ADR-XPLAT-009 §6 |
| **v2.1.4（T5 修憲）** | 2026-08-16 | 經掌舵者 2026-08-16 拍板；**R107 四方複審通過（Architect／SA／SD／QA 各自獨立，4×APPROVE_WITH_CONDITIONS，條件已於同批落款；紀錄＝`docs/06_quality/CrossPlatform_R107_Review.md`）＝已生效**（2026-08-28；機械驗證同日有人窗口重跑：`tools.tests.test_quota_policy` 全綠＋`tools/check_defect_log_crossref.py` rc=0） | 解除 PRD 內部三角衝突（§15.5 紅線 1「不碰未公開端點」↔ 現行唯一取數源即 §4.1.1 T5 ↔ §12「不得讀 OAuth token」為呼叫 T5 的必要前提所必違）：T5 升格為認可主源（零 token、帳號層級權威讀數、R90 四通道實測勝出、失效 fail-safe 降級 cap＝`Policy.degraded_cap` 現查（SSOT＝`tools/lib/quota_policy.py`；上界不變式見 §4.1.5），見 §4.1.1〈T5 升格依據〉）；紅線 1 加收窄豁免（唯讀 GET／單一程式站點 `tools/lib/quota_meter.py`／TTL≥180s 節流／失效降級出聲）；§12 憑證條改為「允許唯讀取用、禁止落痕跡」劃界。§0.6 表與附錄 B-05 的「T5 可整條刪除」保留為 v2.1 核實當時的歷史紀錄，不再是現行規範 |
| **v2.1.5（撞線喚醒閉環修憲）** | 2026-08-17 | 經掌舵者 2026-08-17 立案（「Token 用盡時，為何沒有啟動下一個 Reset 的喚醒機制，不需要人類介入」）、待四方複審後生效 | 新增 §4.5.6：需求層明確化「任一執行層級撞線 → 零人工 → reset 喚醒續跑」，覆蓋面必含 (a) subagent／workflow agent 撞線、(b) **主 session 活著但帳號級撞線**（該回合死於 API 層、hook 體系零觸發點）兩情境；喚醒機制自身失效必須 fail-loud 且可自癒（禁止 fail-quiet 自我解除）；可重啟點任務書的骨架重寫不得摧毀機器可讀狀態塊（單檔雙寫者禁令）。立案證據＝2026-08-16/17 事件（哨兵武裝且巡邏十次全綠，卻在撞線落地後 4 分鐘死於被 halt 動作覆寫的任務書而自我解除，03:50 reset 時機器上零排程，空轉至人工介入；逐字證據與逐環驗證見 ADR-XPLAT-004 §2.9）。設計細節與實作工作清單見 ADR-XPLAT-004 §2.9 |
| **v2.1.6（主控閒置盲區修憲）** | 2026-08-17/18 | 經掌舵者定級 P0「會破產的嚴重 BUG」立案、規格化後待實作 | 新增 §4.5.7：撞線那一刻**之前**主控完全不知道水位已逼近（等 subagent 回覆期間零工具呼叫，`context_budget_guard.py` 只掛 Pre/PostToolUse，該窗口結構上不會被觸發），且撞線那一刻通知能不能送達也未受保障。立案＝`DEF-200-148`，2026-08-16/17 收尾包與修復包兩次實證（皆為「subagent 背景耗至 session 38% 期間主控零喚醒」）。三條規範性要求：R-4.5.7-1（主控閒置盲區量測）／R-4.5.7-2（prepare 帶預防性提醒、不寫任務書骨架）／R-4.5.7-3（通知走桌面通道、不依賴主控下一次工具呼叫）。本版僅完成規格化，實作與回歸鎖見 v2.1.7 |
| **v2.1.7（哨兵武裝狀態漂移自癒 ＋ §4.5.7 落地）** | 2026-08-20 | 經本輪落地並回歸鎖驗證通過 | §4.5.7（B1~B3）與新增 §4.5.8（C1~C4）**全數完整實作**：主控閒置量測、prepare 帶預防性桌面通知、哨兵武裝狀態對排程器現查漂移時的自動重新武裝。落地在 `tools/lib/quota_escalation.py`（`patrol_housekeeping()` 一族）與 `tools/lib/sentinel_lifecycle.py`（`armed_but_missing()`），由 `tools/session_resume_planner.py` 的 `_sentinel_tick()` 接線；回歸鎖見 `tools/tests/test_context_budget_guard.py` 的 `ControllerIdlePrepareWatchTest`／`PatrolNoticeIsDesktopNotHookTest`／`ArmedDriftSelfHealTest` |
| **v2.1.8（四段結構性修憲：救援序列／管家事項／醒來確認／平穩機制運算元）** | 2026-08-22 | 經掌舵者裁決「走理想版」立案，本版僅完成規格化，實作由後續階段接手 | 四段原條文與本 repo 憲法或本實作結構直接衝突，一律**不降規**改寫為更強解，並各自保留「原條文 → 改後條文 → 為什麼（含實測數字）」對照：**(A) §8-8 存檔救援序列**——原文前兩步 `commit --no-verify`／`git stash` 被憲法直接禁止（鐵律五機械阻斷 stash 全族、根 CLAUDE.md 逐字列 `--no-verify` 為禁止事項），刪除該兩步並把第三步升級為「patch 寫完必須重新開檔讀回驗 SHA-256、驗不過 fail-loud」（新增 §4.5.9）；**(B) §8-11／§8-13／§8-14**——三項以「長駐 Daemon」為前提而本 repo 刻意不做 Daemon，**意圖全部保留、只換實現**，塌成「開機自檢」形態掛上 §6.1（新增 §6.2、§6.1 不變式 11~13）；**(C) §8-2 醒來確認**——固定級距 30s→300s×10 是在猜 reset 時刻（與「reset 只能觀測不能算」直接衝突），而現行實作「解不出就硬停」會永眠 ⇒ 改為觀測優先、解不出**掛回零成本哨兵巡邏**兜底（新增 §4.5.10）；**(D) §4.2.4 平穩機制**——運算元 `C_current`／`C_target`（持久併發設定點）在本實作結構上不存在，且 watermark 遲滯要防的病量不到（本包當回合實測 `~/.autosdd/traces/quota_burn.jsonl` 十天 119 筆／8 軸／819 個逐軸讀數：band 變動 77 次，其中下降 33 次**全部**是視窗翻頁（跌幅 ≥ 20pp），小幅擺動反轉 **0** 次），真正在抖的是量測可得性（同段痕跡合併實測：12 小時內 measured⇄unmeasured 翻動 **19** 次）⇒ (a)(b)(c)(d) 改寫為 cap 語意、遲滯與最小停留時間**改掛量測可得性軸**，(e) 保留並列為優先實作；順帶兩項：§8-6 全失效姿態按 fail-safe 修憲為「收斂到 `cap_prepare` 語意」（新增 §4.1.5；立案＝實測 `degraded_cap == cap_converge` 為 `True`、`cap_prepare=2`，且 `draining()` 對 `unmeasured` 明文回 `"unknown"` ⇒ 原文「全失效 → DRAINING」在本實作結構上到不了），以及「訊息中的姿態字面必須與 `decide()` 實際 cap 一致」（`tools/lib/quota_gate.py:551` 逐字「本次不節流，扇出照常放行」與同檔 `:832` 註解自述互相矛盾） |
| **v2.1.9（v2.1.8 四段修憲的否決權複審承接：1 blocker ＋ 6 major ＋ 4 minor）** | 2026-08-23 | 經獨立複審 **REJECT** 承接、逐條修訂後待再審 | v2.1.8 四段條文本身帶有**與它自己要獵的那一族同型**的缺陷（判準會綠、而它要防的事照樣發生），一律不降規改寫，並保留「原條文 → 改後 → 為什麼（含實測數字）」對照。**🔴 BLOCKER §4.5.9 救援序列救不到未追蹤檔案，而四道斷言全部會綠**——R-4.5.9-1 把救援釘死成 `git diff HEAD --binary --no-color`，而該指令的射程**結構上**只有 index 與 HEAD 認識的路徑；當回合合成 worktree 實測：`?? brand_new.py` 存在時 patch 仍為 `135` bytes 非空、`grep -c 'brand_new'` ⇒ **`0`**、SHA-256／位元組數／非空／語意閘全過 ⇒ 「已驗證存檔成功」與「全新工作被靜默丟掉」外觀完全相同。修法＝母體改為「tracked 變更 ∪ untracked 新檔」（② 走 `ls-files --others --exclude-standard -z` 逐檔 `diff --no-index`，實測 `status --porcelain` 前後字串相等 ⇒ 同時滿足原禁令「救援不得改動工作樹」），新增斷言 (d) 覆蓋率與判準 **D8**（紅綠自證＝退回單一來源必須讓 D8 轉紅）、D5b、D9（自我遞迴）。順帶治好第二道語意閘：天真寫法在髒工作樹上**實測恆紅**（rc=1），改為「臨時索引 read-tree 到記錄的 base_sha ＋ `apply --check --cached`」（實測 rc=0，真索引與工作樹皆未動），並禁用 `--3way`（實測會把套不上 fuzz 成 rc=0）、判準改為 `rc == 0`（截半 patch 實測回 **128** 而非 1）。**MAJOR**：① §4.5.10 具名它正在改的 `tools/session_resume_planner.py::tick_plan()` 與兩個既有常數（`MAX_PROBE_ATTEMPTS` 實查 5、`TRANSIENT_RETRY_SECONDS` 實查 300；三者此前全 PRD `grep` 命中 **0**），並逐一登記三支既有鎖的「現在斷言什麼 → 該斷言什麼 → 為什麼改是對的」——其中 transient 那一支判為**一字不改**（兩個數字量的不是同一段時間：行程內 vs 跨醒來），並同步收窄 R-4.5.10-1 的射程免除衝突；② §6.2 掃描集合的 `QUEUED`／`VERIFY_FAILED` 在 §7 schema 不存在（唯一定義過的字面是 `PENDING_VERIFY`）⇒ 照原文實作會掃出 **0 筆**而 G1 注入 `QUEUED` 仍綠＝**結構性假綠**，改以 `PENDING_VERIFY` 為注入值、枚舉補進 §7 並要求「注入值必須是生產真的會寫出來的字面」；③ §4.2.4 挑的 `endurance_env.trace_dir()` **本身就有兩處靜默退回** `tempfile.gettempdir()`（OSError 分支 ＋ `os.access` 三元運算），正是同節花整段論證絕不能用的那個失效 ⇒ 加規範性 loud ＋ 降級標示 ＋ 收緊側 cap，並把 **H4 拆成 H4a／H4b 兩格**（沙箱那格結構上踩不到退回，退回真的發生時仍是綠的）；④ §4.2.4 指定的寫入原語`quota_ledger.append_record()` 自陳〈誠實劃界〉「**仍可能掉行**……不是唯一那一半」、`claim_once()` 是 TTL 閂鎖而非狀態存取器，兩者都承載不了「dwell 判決的唯一真相源」⇒ 改寫死 tmp → fsync → `os.replace` 原子換名（與 §4.5.1 步驟 4 及 R-4.5.9-3 一致）；⑤ R-4.5.10-4 的既有分支枚舉寫「四」而 `sentinel_decide()` AST 實查有 **5** 個相異 action（缺 **`probe`**，且同節 R-4.5.10-3 自己就引用了它＝節內自相矛盾）⇒ 實作者把新事件命名為 `probe` 會**通過 E5** 卻撞名，正好摧毀本條要保護的東西；補齊五元素並要求 E5 的集合由 AST 現查、不得手抄。**MINOR**：`DIRTY_SAVE_RETRIES` 補進 §6 區塊 12（出廠 1、值域 0~3；此前 D6 斷言一個沒有家的鍵）；訂正三處引文／事實（「非 halt 一律 ≥1：禁止靜默鎖死」歸屬 `_clamp()` **不是** `_bound()`——後者函式體實查只有 `min(rec, cap)` 沒有下界／刪除「unmeasured→measured 是**唯一**沒有中間級的躍遷」（`notice → free` 同型，`BAND_FREE` 三個 horizon 皆 `None`）並改由既有的「重置後不暴衝」承重／F3 補上「`None`＝不設限不受此條約束」——照原字面寫成測試會在 `BAND_FREE` 那格 `TypeError`）；`TELEMETRY_UNMEASURED_CAP` 與既有 `AUTOSDD_QUOTA_DEGRADED_CAP`（→ `Policy.degraded_cap`，實查出廠 4【v2.1.4 落款注：此為 v2.1.9 立案當時實測，保留為歷史證據；R100 已收緊出廠值，現值一律現查 `ENV_SPEC`】、下界 1.0）判為**同一旋鈕的兩個命名面**（沿用本文件既有的 `_PAIRS` 對映判例），三候選逐一記錄取捨，並修掉「留空＝取 cap_prepare」與「留空＝取實作預設」的矛盾（前者在實作面不成立：留空得 4 > cap_prepare 2）；H1／§11.2「無抖動」的 37 字元 U/M 序列補時間戳（dwell 以秒計，序列本身決定不了那一半），fixture 須 git-tracked 且自帶 `len==37`／`flips==19` 不變式。🔴 本輪只改 `.md`，零 `.py` 改動；三道閘門的實測輸出與「PRD 不在治理面清單內」的唯讀證明見交件回報 |
| **v2.1.10（R108 證據制配速修憲＋BURN-DOWN 清倉增補，合併同批）** | 2026-09-01 | **經 R108 三審承接（紀錄＝`docs/06_quality/CrossPlatform_R108_Review.md`）＋掌舵者 R110 方向裁決（Q1~Q9／QB1~QB6＝`docs/04_planning/AutoSDD_Adjudication_Record_R110.md`）後，掌舵者 2026-09-01 技術債總清償循環令 D2 落款生效**。落款時修訂表具名現況：v2.1.5／v2.1.6／v2.1.8／v2.1.9 四列維持待審／待實作字面（D2 依 R110「未生效修憲不疊層」判例補齊落款程序）；與現行 `--pace` 實作重疊處＝落款後對齊帳、差異列缺陷（D2 逐字） | 證據制動態配速（主提案）＋掌舵者顯式清倉指令這條路（獨立增補、隨主批合併落款）：施工圖＝`docs/04_planning/PRD_Amendment_R108_Pacing.md`＋`docs/04_planning/PRD_Amendment_R108_BurnDown_Addendum.md`，本表不重抄 |
| **v2.1.11（ADR-XPLAT-014 續跑鏈加固＋PRD 五歧異對齊）** | 2026-09-01 | **經 R108 二審承接修訂（blocking 2 筆全修、紀錄見該 ADR 檔頭）＋掌舵者 R110 方向裁決（§3.5 Q1~Q6）後，掌舵者 2026-09-01 技術債總清償循環令 D1 落款生效**。§7 Q4 的 ①②③⑤ 四處 PRD 內文對齊＝生效後施工項（④ 只登記；對齊完成前，內文與本列不一致處以施工圖為準） | 續跑鏈三道縫加固＋PRD 與現況五歧異修正：施工圖＝`docs/04_planning/ADR/ADR-XPLAT-014-resume-chain-hardening.md`（§7 Q4／§8 工作表），本表不重抄。批次序在 v2.1.10 之後、兩批間無承重依賴（該 ADR §7 Q4 逐條核對） |
| **v2.1.12（usage 水位喚醒閉環）** | 2026-09-01 | **R111 設計波四職能（Architect／SA／SD／Developer）合成產出；獨立四方複審紀錄＝零（`docs/06_quality/` 對本案零命中，落款當日現查）；掌舵者 2026-09-01 技術債總清償循環令 D2 裁決直接落款生效**。批次序＝v2.1.10→v2.1.11→本批（R110 裁決鏈） | 撞線→喚醒閉環的 usage 水位監控機制化：施工圖＝`docs/04_planning/PRD_Amendment_R112_WakeChain.md`（§3-4 持久 notify_queue＋巡邏重投＋TTL＋delivered 憑證＝`DEF-200-236` 載體），本表不重抄 |
| **v2.1.14（§4.2.2-b (4c) gate 聚合面切換為設計內例外）** | 2026-09-04 | **掌舵者 2026-09-02 採 R121 呈報單 `DEF-200-244` 方向 B；R126 四方設計複審 4×APPROVE（Architect／SA／SD／QA，紀錄＝`docs/06_quality/CrossPlatform_R126_Debt_Closure.md` §D）；程式面同批落地並過定點複審** | 新增 (4c)：排除 `FALLBACK_KINDS`／未命中 `MODEL_SCOPED_KINDS` 屬取數層裁決（R89／R98），不受 (4) 多軸單調律約束；`gate = gate_list or readings` fail-safe 保留；實作義務＝`Decision.reason` 帶 `gate_excluded=<kinds>` 可觀測。施工圖＝`docs/04_planning/PRD_Amendment_R126_GateExclusion.md`（本表不重抄）。依 R110 判例不疊層：只加條文與痕跡，不改 v2.1.10 既有條文 |
| **v2.1.15（DEF-200-206：§6 三鍵前綴對齊＋CONFLICT_POLICY 三值行為補述）** | 2026-09-04 | **掌舵者 2026-09-02 採 R121 呈報單 `DEF-200-206` 方向 A（③②修實作、①修憲）；R127 三方設計複審（Architect／SA／SD，`model: sonnet`）Q1 出廠值定案採 PRD 的 5、Q2 前綴、Q3 ABORT 語意；程式面同批落地並過定點複審** | §6 區塊 11／12 三鍵改為 `AUTOCLAUDE_CONFLICT_POLICY`／`AUTOCLAUDE_STATE_RETAIN_VERSIONS`／`AUTOCLAUDE_DIRTY_SAVE_RETRIES`（跟隨全庫 `AUTOCLAUDE_*` 慣例；此前 PRD 同區塊有無前綴混用、且後兩鍵在實作零讀取路徑）；R-6.2-1 補述三值各一種行為（`ABORT`＝拒絕啟動）並在 G1 驗收表加控制組 (iii)(iv)；§8 列 4／列 11 同步。實作：`execution/boot_self_check.py`（枚舉對齊＋`conflict_policy_from_env`）、`infra/adapters/dirty_worktree_rescue.py`（`dirty_save_retries_from_env`）、`core/wiring.py`／`main.py` 接線、`file_state_repository.py` 出廠值 2→5。施工圖＝`docs/04_planning/PRD_Amendment_R127_EnvKeyAlignment.md`（本表不重抄）。依 R110 判例不疊層：只改鍵名字面、補述與痕跡，不改既有條文語意 |
| **v2.1.13（R113/R114 喚醒鏈最後一哩）** | 2026-08-31 | **經 R114 四方複審收斂後，掌舵者 2026-08-31 落款生效**（一輪 Architect/QA REJECT＋SA/SD AWC＝去重 13 blocking；修訂三批；二輪 4×AWC；SD 定點複核 APPROVE；紀錄＝`docs/06_quality/CrossPlatform_R114_WakeChain_Review.md` §2） | 喚醒鏈最後一哩四缺口閉合：G1 無頭窗口權限姿態（三層白名單＋雙平台孿生 allow/deny）／G2 handback 交接可見性（雙載體＋SessionStart 偵測）／G3 配額內接力狀態機（判定序 ③→④→②→①、煞車一出廠 1、失敗態全重掛）／G4 哨兵 fire 後重掛＋patrol 自檢。設計全文與驗收 V-a1~V-e2e＝`docs/04_planning/PRD_Amendment_R113_WakeChain_LastMile.md`（本表不重抄，該檔為 v2.1.13 唯一施工圖）。依 R110 判例不疊層：v2.1.10~12 仍 Proposed、未隨本批生效，與本批的前置關係見該檔 §0。2026-08-31 實戰佐證（本 repo 當日 session）：偵測撞線→武裝→reset 後準時醒→探測 rc=0 全通，斷點＝`quota_back_no_resume`（`AUTOSDD_RESUME_OFF` User 層）＋G1~G4，見同檔 §7 |

> **v2.1 的變更**：附錄 B 的事實核對清單已**實際核實完成**（方法見附錄 B 開頭）。核實結果顯示 Claude Code v2.1.x **已內建**本 PRD 原本打算自建的多項能力（原生 worktree 隔離、任務 DAG、排程喚醒、零 Token 用量遙測、併發上限、官方配速門檻）。因此新增 [§15 執行方法論](#15-執行方法論與注意事項v21-新增)，並將建議架構從「大型自建 Daemon」縮減為「薄治理層 + 採用原生能力」。**§15 是實際動工時應遵循的章節**（含動工前置檢查、採用 vs 自建決策矩陣、P0–P5 分階段步驟、12 條紅線注意事項、參數校準方法與交付目錄結構）。

> **v1.0.0 → v2.0.0 修訂性質**：本版並非潤稿，而是修正 v1 中 **3 項架構級邏輯錯誤**、**6 項控制理論缺陷**、**11 項規格缺漏**與若干事實／數值錯誤。完整問題清冊見 [附錄 A](#附錄-av1--v2-問題清冊issue-register)。
>
> **重要前提（v2.1 更新）**：文中 `[需核對]` 標記多數已於附錄 B 完成核實，核實方法為直接檢視 `@anthropic-ai/claude-code` v2.1.232 的官方 npm 發佈內容與原生二進位。**但核實來源是實作內部字串，不是官方文件承諾的公開介面** —— 其中部分為功能旗標或內部識別字，可能隨版本變動。凡標示「內部」者，實作時必須有降級路徑，不可硬依賴。

---

## 目錄

**如果你只讀一章：** 決策者讀 [§0](#0-修訂重點摘要給決策者的-5-分鐘版)；**要動工的人讀 [§15](#15-執行方法論與注意事項v21-新增)**（前置檢查、決策矩陣、P0–P5 步驟、紅線清單、參數校準）。

| 章節 | 內容 | 誰該讀 |
| :---- | :---- | :---- |
| [0. 修訂重點摘要](#0-修訂重點摘要給決策者的-5-分鐘版) | v1 的 12 項主要問題與修正 | 決策者 |
| [0.6 情勢變更](#06-情勢變更cli-已內建的能力v21-核實結果) | **CLI 已內建、不必自建的能力清單** | 決策者、架構 |
| [1. 設計原則](#1-執行摘要與核心設計原則) | 七項原則、非目標 | 全體 |
| [2. 名詞與量測定義](#2-名詞與量測定義v1-缺此章是多數錯誤的根因) | 額度率 vs 上下文佔用率的區分 | 全體（**v1 錯誤根源**） |
| [3. 架構與狀態機](#3-系統架構與狀態機) | 狀態表、進入／離開條件、轉移圖 | 架構、開發 |
| [4. 模組規格](#4-模組規格) | 遙測、配速、壓縮、隔離、喚醒、防休眠、仲裁 | 開發 |
| [4.2.8 配速門檻對齊](#428-與-cli-內建配速門檻對齊v21-核實新增) | `pace_index` 形式與官方參考值 | 開發（**建議主控訊號**） |
| [5. API Key 模式](#5-api-key-模式v1-只提一句實際無法運作) | 正規化層與硬性預算 | 開發（僅 API 模式） |
| [6. 設定檔規範](#6-設定檔規範envexample修訂版) | `.env.example` 全量 + 啟動不變式 | 開發、運維 |
| [7. state.json Schema](#7-狀態資料結構規格statejson-schema-v2) | 治理層持久化結構 | 開發 |
| [8. 例外與邊界條件](#8-例外與邊界條件擴充) | 14 項異常處置 | 開發、測試 |
| [9. 可觀測性](#9-可觀測性v1-完全缺漏) | 指標、日誌、告警 | 運維 |
| [10. 設定遷移對照](#10-v1--v2-設定遷移對照) | v1 → v2 參數變更 | 已有 v1 實作者 |
| [11. 驗收與測試標準](#11-驗收與測試標準改為可量測並解決-v1-的矛盾) | 8 組可量測判準 | 測試 |
| [12. 安全性](#12-安全性v1-完全缺漏) | 憑證、權限、注入、供應鏈 | 全體 |
| [13. 合規聲明](#13-合規聲明v1-缺漏但對本類工具至關重要) | 禁止事項與待確認法務項 | 決策者 |
| [14. 路線圖（已被 §15.4 取代）](#14-實作路線圖建議v1-無此章) | v2.0 舊版規劃，僅供對照 | — |
| **[15. 執行方法論與注意事項](#15-執行方法論與注意事項v21-新增)** | **前置檢查、決策矩陣、最小架構、P0–P5、紅線、校準、目錄結構** | **動工前必讀** |
| [附錄 A：問題清冊](#附錄-av1--v2-問題清冊issue-register) | 43 項 v1 問題逐條對應修正 | 審查者 |
| [附錄 B：事實核對結果](#附錄-b事實核對結果v21-已核實) | 核實方法、12 項已確認、8 項新發現、5 項待人工確認 | 開發（**動工前必讀**） |

---

## 0. 修訂重點摘要（給決策者的 5 分鐘版）

| # | v1 的問題 | 嚴重度 | v2 的修正 |
| :-- | :---- | :---- | :---- |
| 1 | **把「上下文視窗佔用率」與「額度使用率」當成同一個指標**，於額度 90% 時觸發 `/compact` | 🔴 阻斷級 | 兩者拆成獨立的量測軸（`U5h/U7d` vs `K_ctx`）。壓縮由上下文佔用驅動，且**壓縮本身會消耗額度**，故必須在 WARN 階段前完成並預留成本預算 |
| 2 | **週上限（7 天）觸發後仍只休眠到 5 小時視窗重置** | 🔴 阻斷級 | 新增 `LONG_HIBERNATE` 狀態與 OS 排程器交棒機制（最長 7 天，不可靠 in-process sleep 撐過） |
| 3 | **配速公式與狀態機互相矛盾**：驗收標準要求 75% 時收斂到 `C_min`，但公式在該情境可能算出 `C_max` | 🔴 阻斷級 | 引入「狀態併發上限表 `C_cap(state)`」，公式的輸出必須再經狀態上限夾緊 |
| 4 | 無遲滯（hysteresis）、無變化率限制、無停留時間 → 在 70%／85% 邊界會震盪抖動 | 🟠 高 | 加入遲滯帶、±1 變化率限制、最小停留時間、EWMA 平滑、死區 |
| 5 | `V_actual` 冷啟動下限在公式（0.01）與程式碼（0.02）不一致；視窗重置時 `ΔU` 為負會誤判成「零燃燒」而暴衝 | 🟠 高 | 統一為單一常數，並新增「視窗重置偵測」清空歷史緩衝 |
| 6 | 遙測失效時的失效方向未定義（fail-open 會直接爆額度） | 🟠 高 | 明定 **fail-safe**：遙測過期即降級，超時即排空 |
| 7 | 宣稱「無損喚醒不重複消耗 Token」，但 `--resume` 在快取失效後會**全額重讀整段對話** | 🟠 高 | 承認並量化此成本；新增 `RESUME_STRATEGY` 讓大型對話改用「新 Session + state.json 交棒」 |
| 8 | 預設在喚醒指令中使用 `--dangerously-skip-permissions` | 🟠 高（安全） | 改為權限模式 + 工具白名單；旁路模式需顯式開啟並隔離於容器 |
| 9 | 多 Agent 以 `git worktree` 隔離，但合併策略只寫「Fast-Forward」 | 🟡 中 | 新增序列化整合佇列（rebase → 驗證 → FF-only merge），並處理分支已存在、worktree 未提交變更、`.gitignore` 等實務問題 |
| 10 | 同帳號多專案／多 Daemon 會各自以為額度充足 | 🟡 中 | 新增帳號層級配額仲裁鎖與 Token Bucket 分配 |
| 11 | `state.json` 只能記錄單一 worktree／session，與多 Agent 設計衝突；`git_commit_hash` 長度非法；`reset_timestamp` 比 `saved_at` 晚 24 小時（5 小時視窗不可能） | 🟡 中 | Schema 升級為 v2（agents 陣列、原子寫入、校驗欄位），並修正範例數值 |
| 12 | 缺少：可觀測性、安全、ToS 合規、Agent 硬性停止、時鐘漂移、Linux 支援、dry-run、人工覆寫 | 🟡 中 | 新增第 12～15 章與相關設定項 |

### 0.6 情勢變更：CLI 已內建的能力（v2.1 核實結果）

核實後最重要的結論：**本 PRD 有將近一半的模組不需要自建。** Claude Code v2.1.x 已提供對應原生能力，自建版本只會多一份要維護的、且更容易出錯的程式碼。

| PRD 原計畫自建 | CLI 已內建（已核實） | 建議 |
| :---- | :---- | :---- |
| §4.1 遙測引擎（含未公開端點） | statusLine hook 的輸入 JSON 直接含 `rate_limits.five_hour.used_percentage` / `.resets_at`、`rate_limits.seven_day.*`、`subscription_type`、`session.total_cost_usd` | **採用**。原 T5（未公開端點）整條刪除【v2.1.4 指針：本格「整條刪除」為 v2.1 核實當時的結論，保留為歷史紀錄、**不再是現行規範**——v2.1.4 起 T5 已升格認可主源（§4.1.1〈T5 升格依據〉、§15.5 紅線 1 豁免四條件）；statusLine 只回 five_hour／seven_day 兩軸，看不到 R87 事故軸 `spend`／`extra_usage`】 |
| §9 可觀測性 | `CLAUDE_CODE_ENABLE_TELEMETRY` + OpenTelemetry 匯出，含 `claude_code.token.usage`、`claude_code.cost.usage`、`claude_code.compaction`、`claude_code.subagent.spawn` 等；支援 OTLP 與 **Prometheus exporter** | **採用**。自建指標只補「治理決策」層 |
| §4.4.1 自建 git worktree 管理 | `Agent` 工具的 `isolation: "worktree"`；`EnterWorktree` / `ExitWorktree`（含未提交變更的拒絕保護與 `discard_changes` 二次確認） | **採用**。自建 worktree 腳本刪除 |
| §7 `state.json` 內的 task DAG | `TaskCreate` / `TaskUpdate` / `TaskList` / `TaskGet` / `TaskStop`，支援 `addBlocks` / `addBlockedBy` / `metadata` / `owner` | **採用**為主，`state.json` 只保留治理層狀態 |
| §4.2 併發致動器（自行管理多個 CLI 行程） | `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`、`CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION`、`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`、`CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` | **改為調整設定值**，而非自建行程池（大幅簡化） |
| §4.5.5 OS 排程器交棒 | `CronCreate`（`durable: true` → 寫入 `.claude/scheduled_tasks.json`，跨 session 存活，**7 天後自動過期**）；`ScheduleWakeup`（延遲**夾在 60–3600 秒**） | **混合**：短等待用 `ScheduleWakeup`，跨 5h 用 cron 或 OS 排程；`ScheduleWakeup` 上限 1 小時，**無法單次撐過 5 小時視窗** |
| §4.2 配速門檻（憑猜測） | CLI 內建的「超前燃燒」判準表（見 §4.2.8），提供官方參考值 | **對齊**，不再自訂憑感覺的水位 |
| §4.3 壓縮治理 | 自動壓縮已內建（`CLAUDE_CODE_AUTO_COMPACT_WINDOW`）；`PreCompact` / `PostCompact` hook 存在 | **採用** hook 做壓縮前 checkpoint，不自行下達壓縮指令 |

**新發現、PRD 完全遺漏的維度：**

1. **超額用量（overage / extra usage）**：額度類型除 `five_hour`、`seven_day` 外，還有 `seven_day_opus`、`seven_day_sonnet`、`seven_day_overage_included`、`overage`、`extra_usage`，且有月度支出上限與 `overage-utilization` 概念。**這代表達到訂閱限制後可能可以付費續跑**，治理決策從「凍結」變成「凍結 or 付費續跑」二選一 —— 必須是顯式設定，不能預設替使用者花錢。見 §6 的 `OVERAGE_POLICY`。
2. **額度狀態是枚舉不只是百分比**：`allowed` / `allowed_warning` / `rejected`，配合 `resetsAt` 與 `rateLimitType`。**應以此枚舉為主要狀態訊號**，百分比僅作為配速輸入 —— 比自訂水位可靠得多。🔴 **通道限定（R90 補；語意不變，只補「它住在哪」——附錄 B-13 已寫對，本條與 §15.5 紅線 7 漏寫）**：此枚舉的唯一載體是**模型 API 呼叫的限流回應標頭**（`anthropic-ratelimit-unified-status`）。⇒ 本條只對「本身會發模型請求、因而拿得到那組標頭」的元件成立；**不發模型請求的純觀測型元件結構上取不到它**，對它們而言百分比不是「次要訊號」而是唯一可得訊號。依據＝R90 四通道實測（`/api/oauth/usage` body 與其回應標頭、statusLine stdin、逐字稿，四條皆 0 命中），見 `docs/06_quality/Quota_R90_CrossAccount_Experiment.md`。
3. **週額度依模型分軌**：`seven_day_opus`、`seven_day_sonnet` 為獨立額度（Max / Team 方案可見），證實 v2 的「模型降級致動器」方向正確且可實作。
4. **前置條件**：Node.js ≥ 22；CLI 現以各平台原生二進位發佈（含 `linux-x64-musl`、`linux-arm64`、`win32-arm64`）。v2 對 Linux 支援的批評（A-24）成立。

---

## 1. 執行摘要與核心設計原則

### 1.1 背景與痛點（維持 v1 判斷，補充精確定義）

以 Claude Code 進行長時間、多 Agent 自動開發時，額度限制會以三種不同機制生效，**三者需分別治理**：

1. **5 小時使用視窗**：達上限後暫停使用，等待該視窗重置。
2. **每週（7 天）上限**：達上限後最長需等待數天，**無法靠短暫休眠規避**。
3. **每週特定模型上限**（如高階模型另有獨立週額度）。

缺乏外部治理時的具體損害：
- 任務在 Token 耗盡瞬間被截斷 → 程式碼半寫入、Git 工作區髒污、測試狀態不明。
- 固定併發數在額度充裕時吃不滿、在額度告急時瞬間撞 429。
- 缺乏喚醒機制 → 上下文丟失，或喚醒時付出未預期的全額上下文重讀成本。

> `[需核對]` 上述三種限制的**確切名稱、單位、重置語意（固定視窗 vs 滾動視窗）與是否對外暴露 reset timestamp**，必須以官方文件為準。v1 文中「72 小時／7 天」的混用已刪除——「72 小時」並非已知的限制週期。

### 1.2 核心架構原則（新增 3 項）

1. **控制面／執行面分離（Control Plane vs Execution Plane）**
   - **LLM 是執行者（Worker）**：只負責程式碼生成與工具調用。
   - **Daemon 是指揮官（Governor）**：獨立行程，負責遙測、配速、生命週期、狀態保全。Daemon 本身**不得**呼叫任何 LLM。
2. **零 Token 消耗遙測（Zero-Token Telemetry）**
   - 一律透過**本地既有產物**（結構化遙測輸出、對話記錄檔、statusline 回寫）取得用量；**嚴禁**用 Prompt 探測額度。
3. **雙軸額度防護（5h Window ∧ Weekly Cap）**
   - 任何派工決策必須同時通過 5 小時視窗閘門與週上限閘門，取**最保守**者。
4. **狀態無損與優雅退場（Graceful Drain & Lossless Resume）**
   - 階梯式減速 → 排空 → Git 交易保護 → Session 保存 → 精準喚醒。
5. **【新增】失效即保守（Fail-Safe, Not Fail-Open）**
   - 任何遙測不可得、逾時、解析失敗、時鐘異常，系統一律往**更保守**的方向收斂（降併發 → 排空 → 凍結），絕不維持或提高併發。
6. **【新增】量測軸分離（Quota ≠ Context）**
   - 「帳號額度使用率」與「單一 Session 上下文佔用率」是兩個獨立變數，各有各的門檻與動作，不得混用（v1 的核心錯誤）。
7. **【新增】合規優先（Compliance by Design）**
   - 本系統的目的是**尊重並平順地貼合**額度限制，而非規避。明確列為非目標：多帳號輪替／共用、憑證共享、任何形式的限流繞過。

### 1.3 非目標（Out of Scope）

- 多帳號輪替或帳號池化以擴大額度。
- 逆向工程／繞過 Anthropic 限流或計費機制。
- 取代 CI/CD；本系統只負責在**開發階段**的自動排程與整合前置作業。
- 為 API Key 模式提供「無上限自動燒錢」；API 模式必須有使用者自訂的硬性預算上限。

---

## 2. 名詞與量測定義（v1 缺此章，是多數錯誤的根因）

| 符號 | 名稱 | 範圍 | 單位 | 資料來源 | 說明 |
| :---- | :---- | :---- | :---- | :---- | :---- |
| `U5h` | 5 小時視窗使用率 | **帳號層級**（跨所有 session/專案） | % (0–100) | 遙測引擎 | 決定 WARN／DRAIN／HALT 狀態轉移 |
| `U7d` | 週額度使用率 | **帳號層級** | % (0–100) | 遙測引擎 | 週上限安全閥；亦為 BURSTING 的否決條件 |
| `U7d_model` | 特定模型週額度使用率 | 帳號層級 | % (0–100) | 遙測引擎 | 觸發「模型降級」動作 |
| `T_rem` | 5 小時視窗剩餘分鐘 | 帳號層級 | 分鐘 | `reset_timestamp - now` | 配速分母 |
| `T_rem_7d` | 週額度重置剩餘秒數 | 帳號層級 | 秒 | `weekly_reset_timestamp - now` | `LONG_HIBERNATE` 依據 |
| `K_ctx` | **上下文視窗佔用率** | **單一 Session 層級** | % (0–100) | 對話記錄檔 / statusline | 觸發壓縮的**唯一**依據 |
| `V_safe` | 安全燃燒率 | 帳號層級 | %/分鐘 | 計算值 | 剩餘額度均攤到剩餘時間 |
| `V_actual` | 實測燃燒率（EWMA） | 帳號層級 | %/分鐘 | 計算值 | 平滑後的觀測值 |
| `C(t)` | 當前允許併發 Agent 數 | 系統層級 | 整數 | 計算值 | 控制器輸出 |

**關鍵釐清（v1 錯誤來源）**

- `/compact` 壓縮的是 `K_ctx`（上下文視窗），**不會**降低 `U5h`／`U7d`。
- 壓縮動作本身需要模型讀完整段對話並產生摘要，因此**會顯著推升 `U5h`**。在 `U5h = 90%` 時執行壓縮是反向操作。
- 「額度」是帳號共享資源；「上下文」是每個 session 各自的資源。兩者的門檻不可共用同一組環境變數（v1 的 `TOKEN_COMPACT_PERCENT=90` 已廢除，見 §10 遷移對照表）。

---

## 3. 系統架構與狀態機

### 3.1 架構圖

```
┌───────────────────────────────────────────────────────────────────────┐
│                  AutoClaude Daemon (單一實例，檔案鎖保護)              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ 1 遙測引擎    │→ │ 2 配速控制器  │→ │ 3 派工/生命週期│  │ 5 可觀測性 │ │
│  │  Telemetry   │  │  Pacing Ctrl │  │  Dispatcher   │  │ Metrics/  │ │
│  │  (零 Token)  │  │  (含遲滯)     │  │  (硬性預算)   │  │ Log/Alert │ │
│  └──────────────┘  └──────────────┘  └──────┬───────┘  └───────────┘ │
│         │                  │                │                         │
│         ▼                  ▼                ▼                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ 帳號配額仲裁  │  │ 4 狀態保全與  │  │ 6 Git 整合    │  │ 7 防休眠   │ │
│  │ (跨專案共享)  │  │   喚醒 Resume │  │   佇列        │  │ Keep-Awake│ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └───────────┘ │
└──────────────────────────────┬────────────────────────────────────────┘
                               ▼
        ┌──────────────────────────────────────────────────┐
        │  Claude Code CLI 實例 × C(t)（各綁定獨立 worktree）│
        │  headless 模式 + hooks 回報 + 硬性 turn/時間上限   │
        └──────────────────────────────────────────────────┘
```

### 3.2 狀態機（補上 v1 缺少的進入／離開條件、遲滯、單向鎖存）

| 狀態 | 進入條件 | 離開條件 | `C_cap` | 允許的動作 |
| :---- | :---- | :---- | :---- | :---- |
| `INIT` | 程序啟動 | 環境驗證通過且取得首次遙測 | 0 | 驗證設定不變式、取得帳號基準、掃描殘留 state.json |
| `CRUISING` | `U5h ≤ WARN − HYST` 且週閘門通過 | 任一升級條件成立 | `C_max` | 正常派工 |
| `BURSTING` | 見 §4.4 突刺判準（全部成立） | 任一判準失效 | `C_max` | 全速派工 |
| `THROTTLING` | `U5h ≥ WARN` 或 `U7d ≥ WEEKLY_WARN` 或 遙測過期 | `U5h ≤ WARN − HYST` 且遙測新鮮 | `C_throttle` (1) | 降併發、模型降級、禁止高成本任務類別 |
| `DRAINING` | `U5h ≥ DRAIN` 或 `U7d ≥ WEEKLY_DRAIN` 或 遙測逾時 | **僅能由視窗重置離開（單向鎖存）** | 0 | 停止派新工，允許進行中 Step 收尾（受硬性預算限制） |
| `FREEZING` | `U5h ≥ HALT` 或 排空逾時 或 429 重試耗盡 | 保全完成 | 0 | 寫 state.json（原子）、各 worktree commit、釋放 Agent |
| `WAITING_RESET` | 保全完成且 `T_rem_7d` 未觸發長休眠 | 到達 `reset + buffer` 且遙測確認已重置 | 0 | 分片休眠、保持喚醒、定期驗證 |
| `LONG_HIBERNATE` | `U7d ≥ WEEKLY_HALT` | 到達週重置時間 | 0 | **交棒給 OS 排程器**、釋放防休眠、Daemon 可安全退出 |
| `RESUMING` | 遙測確認額度已重置 | 首個 Agent 成功接手 | 1 | 依 `RESUME_STRATEGY` 喚醒；失敗則退避重試 |
| `HALTED_MANUAL` | 使用者下 `autoclaude pause` | 使用者下 `resume` | 0 | 人工覆寫，優先於一切自動決策 |

**單向鎖存（Latching）設計理由**：`DRAINING` 以上狀態不可因用量讀數小幅回落而退回 `CRUISING`。額度使用率是單調遞增的（在同一視窗內），任何「回落」都代表遙測抖動或視窗重置；前者不該觸發升併發，後者應走正式的重置流程。v1 未定義此點，會導致在 85% 邊界反覆進出排空。

### 3.3 狀態轉移圖

```
 INIT ──► CRUISING ◄────────────► BURSTING
            │  ▲                      │
     U5h≥70 │  │ U5h≤67              │ 判準失效
            ▼  │                      │
        THROTTLING ◄──────────────────┘
            │
     U5h≥85 │ (單向)
            ▼
        DRAINING ──► FREEZING ──┬──► WAITING_RESET ──► RESUMING ──► CRUISING
                                │                          ▲
                     U7d≥90     └──► LONG_HIBERNATE ───────┘
                                       (OS 排程器交棒)

 任一狀態 ──(使用者指令)──► HALTED_MANUAL
 任一狀態 ──(遙測逾時>600s)──► DRAINING
```

---

## 4. 模組規格

### 4.1 遙測引擎（Telemetry Engine）

#### 4.1.1 資料來源分層（v1 的重大缺漏：只寫了未公開端點）

依**可靠性與合規性**排序，實作時必須全部支援並可降級：

| 層級 | 來源 | 可靠性 | 備註 |
| :---- | :---- | :---- | :---- |
| **T1（首選）** | Claude Code 的結構化遙測輸出（OpenTelemetry metrics 匯出至本地 collector） | 高，官方支援 | `[需核對]` 啟用方式與 metric 名稱／attributes。此為零 Token、官方支援的正途 |
| **T2** | 本地對話記錄檔（session transcript，內含每則訊息的 token usage） | 中高 | `[需核對]` 檔案路徑與 schema。可自行加總得到「本機消耗」，但**看不到其他機器／其他專案的消耗** |
| **T3** | statusline hook 回寫：由 CLI 主動呼叫的 statusline 腳本，將取得的 session/用量資訊寫入 Daemon 監看的檔案 | 中 | 注意方向：statusline 是 **CLI 呼叫腳本**，不是 Daemon 去輪詢 CLI（v1 描述方向錯誤） |
| **T4** | 官方用量查詢介面（如 CLI 的用量指令）之程式化解析 | 低（輸出格式可能變動） | 需容錯解析，格式變動時降級而非崩潰 |
| **T5（v2.1.4 升格：認可主源）** | 未公開的 OAuth usage HTTP 端點（唯讀 `GET /api/oauth/usage`） | 中高（未公開介面仍可能變動，故失效降級路徑不可拆除） | v1 列為主要方案、v2 降為選用；**v2.1.4 經掌舵者 2026-08-16 拍板升格為認可主源**（依據見下方〈T5 升格依據〉；使用邊界受 §15.5 紅線 1 豁免條款四條件約束） |

**T5 升格依據（v2.1.4，掌舵者 2026-08-16 拍板；R107 四方複審通過＝4×APPROVE_WITH_CONDITIONS，條件已同批落款，已生效；紀錄＝`docs/06_quality/CrossPlatform_R107_Review.md`）**——四項皆為實測結論，不是偏好：

1. **零 token 成本**：該呼叫不是模型推論，不吃額度、不進 5 小時視窗（`tools/lib/quota_meter.py` 檔內 `USAGE_URL` 註解逐字；R90 探針同一結論）。
2. **帳號層級權威讀數**：server 依帳號方案自己算好 utilization 回百分比，本機不自行推導分母；且回應含**全部**計費軸（R90 實測頂層 17 鍵）。對照 T3 statusLine 只回 five_hour／seven_day 兩軸的 `used_percentage`／`resets_at`，結構上看不到 `spend`／`extra_usage`——正是 §15.1 第 3 項認定「本專案最危險的單一失敗模式」所在的軸（R87 事故：該軸撞頂時 13 個 subagent 全滅、燒 1,319,703 tokens，而訂閱窗還有 37% 餘裕）。
3. **R90 四通道實測勝出**：本機可達四通道（端點 body／同 API 回應標頭／statusLine stdin JSON／逐字稿）逐一量測，唯端點 body 給出全軸讀數；見 `docs/06_quality/Quota_R90_CrossAccount_Experiment.md` §一。
4. **失效 fail-safe**：任何失效（斷網／401／schema 變動／無憑證）一律回「量不到」且各有可分辨的失效字面；量不到**不是不設限**——降級 cap＝`Policy.degraded_cap` 現查（SSOT＝`tools/lib/quota_policy.py`，本 PRD 不複寫數字；上界不變式 `1 ≤ degraded_cap ≤ cap_prepare` 見 §4.1.5），方向保守。

**T1／T5 劃界（v2.1.4 落款補注）**：T5 升格不改變 T1 的「首選」地位——兩者量的不是同一軸：T1（OTEL）匯出的是**本機行程**的消耗指標，T5 給的是**帳號層級**全計費軸權威讀數（含 R87 事故軸 `spend`／`extra_usage`）；帳號層級水位治理以 T5 為認可主源，T1 是官方支援的本機遙測正途，兩者並行、不互為替代。

T5 的實作站點唯一（端點知識不得有第二個家）＝`tools/lib/quota_meter.py`。§6 與本節升格的整合已由 R107 四方複審一併裁決（4×APPROVE_WITH_CONDITIONS，同批落款；紀錄＝`docs/06_quality/CrossPlatform_R107_Review.md`）：**不做 `TELEMETRY_ALLOW_UNDOCUMENTED_ENDPOINT` kill-switch 旗標**——該旗標全庫零實作（2026-08-28 現查：全庫命中僅文件 3 處、零程式／設定消費端），紙上開關只會製造「有守衛」的假外觀；未文件化端點（T5）的遙測**恆啟用**，防護不靠開關、靠 §15.5 紅線 1 豁免四條件（唯讀 GET／單一程式站點／TTL≥180s 節流／失效降級出聲），落字見 §6 區塊 2。

**關鍵限制（必須寫入文件並告知使用者）**：`U5h`／`U7d` 是**帳號層級**指標。T2/T3 只能觀測本機用量。若同一帳號在其他裝置或 Claude 網頁端使用，本機推估會**低估**真實用量。因此：
- 必須支援「權威來源」（T1/T4/T5）與「本機推估」（T2/T3）的差異偵測；
- 當只有本機推估可用時，強制套用 `LOCAL_ESTIMATE_SAFETY_MARGIN`（預設 15 個百分點）壓低所有門檻。

#### 4.1.2 新鮮度與失效處理（v1 完全缺漏）

```
telemetry_age = now_monotonic − last_successful_poll
  age ≤ POLL_INTERVAL × 3           → 正常
  age >  POLL_INTERVAL × 3 (180s)   → 強制 THROTTLING，發警示
  age >  TELEMETRY_TIMEOUT (600s)   → 強制 DRAINING
  age >  TELEMETRY_TIMEOUT × 2      → 強制 FREEZING（視為額度狀態不明）
```
輪詢自身失敗需採指數退避，避免對來源造成壓力；退避期間**不放寬**任何門檻。

#### 4.1.3 視窗重置偵測

```
若 U5h(t) < U5h(t−Δ) − RESET_DROP_THRESHOLD (預設 20 pp):
    判定為 5 小時視窗已重置
    → 清空燃燒率歷史緩衝
    → V_actual ← V_safe（中性初值，使比率=1，輸出 C_default）
    → 若處於 WAITING_RESET，轉入 RESUMING
```
v1 的 `delta_u = max(0.0, ...)` 會把重置造成的負差值壓成 0，使 `V_actual` 掉到下限、比率暴衝，喚醒後第一個控制週期就直接跳到 `C_max` —— 這是最容易在重置後立刻再撞牆的路徑。

#### 4.1.4 帳號／方案變更偵測（Plan-Change Adaptive Amortization）（R93 新增）

**問題**：§4.2 的跨窗攤提換算比（實作見 ADR-XPLAT-005／R86 校準文件）從歷時
落款差分推估，該落款持久且永不輪替。帳號的容量發生變更時（更換訂閱方案，
或更換同組織下容量不同的帳號），舊方案與新方案的樣本會混在同一個估計池，
導致換算比被錯誤方案的燃燒特性汙染——這個風險**不隨時間自癒**（落款是持久
的，不像快取有 TTL）。

**核心指紋**：以帳號本次讀數中「屬於既有已分類桶名集合（`KNOWN_KINDS`，見
ADR-XPLAT-005/007 既有定義）」的 kind 集合作為指紋。伺服器新推出一個尚未
分類的計費軸（schema 演進）**不算**方案變更；已分類軸的增減（例如訂閱方案
變更導致某個既有額度類型消失或新增）**才算**方案變更訊號。

**適配機制**：每一次落款附帶當時的核心指紋；估計換算比時只採信與**當前**
核心指紋相符的歷史樣本。方案容量無論從大變小或從小變大，只要核心桶集合
因此改變，舊樣本結構上都不會混入新方案的估計池——兩個方向對稱處理，不需要
額外的「哪個方向該不該計入」判斷。

**已知限制**（誠實揭露，非缺失）：

🔴 **R93 二次訂正（獨立 Architect 複審 REJECT 承接，`DEF-200-114`）**：下面第一點
「需要帳號身份識別（涉及憑證處理，非本節範圍）」與實測不符，PRD 與實作已於本輪
一併修正——`docs/06_quality/Quota_R90_CrossAccount_Experiment.md` §2.3-2.4 用
真實 Pro→Team 換帳號資料證明：核心桶集合指紋本身**不具身分鑑別力**（真實換帳號
差異軸與同帳號兩次自然翻動逐字相同，3 命中 2 假陽性；29% 的舊帳號樣本與新帳號
指紋逐字相同，偽陰性，且不限同方案）。帳號身份識別**不涉憑證處理**——
`anthropic-organization-id`／`anthropic-workspace-id` 就在既有取數呼叫的回應
標頭裡，本輪已納入指紋（見 ADR-XPLAT-009 §6 的完整訂正），第一點限制範圍因此
收窄。核心指紋機制（前段〈適配機制〉描述的桶名集合分區）本身**不變**、仍是
安全方向，只是不再單獨承擔「偵測換帳號」的角色。

- ~~同一方案下更換帳號、核心桶集合恰好相同時，本機制與 §4.1.1 既有的帳號層級
  盲區同型，結構上偵測不到，需要帳號身份識別（涉及憑證處理，非本節範圍）。~~
  **本輪已解決**：帳號身份訊號（回應標頭雜湊，零額外網路／token／憑證處理）
  併入核心指紋，同方案換帳號現在可以被拆開。殘餘限制縮小為：同一個
  組織／工作區下方案原地變更、且核心桶集合恰好沒變時仍抓不到（需要伺服器
  揭露方案本身的識別欄位，payload 現況無此欄）。
- **新補齊的邊界**（本節此前漏列，獨立 Architect 複審指出）：不同方案但核心
  桶集合恰好相同時，若對應到不同帳號（組織／工作區不同），本輪的帳號身份
  訊號一併解決；若是同一個組織／工作區下發生，仍是上一點的殘餘情境。
- 快取新鮮度視窗（§4.1.2，180 秒）只判斷時間新鮮度，不判斷帳號/方案身份；
  換帳號後最多 180 秒的窗口內可能仍採信切換前的讀數，下一次量測即自我修正。
- 換方案發生當下已經在執行中的 Agent／扇出工作不受本機制的未來派工決策
  影響，會依原方案／新方案的實際容量自然消耗至結束，這是物理限制而非設計
  疏漏。
- 歷史校準基準（本節之前累積的樣本）在本機制上線的當下因缺乏指紋資訊而
  永久不再參與估計，是刻意的、方向安全的信心度重置，而非資料遺失。
- 帳號身份訊號上線那一刻對既有樣本池同樣是一次性、方向安全的信心度重置
  （既有落款皆無帳號標籤），與上一點同型。
- 帳號身份訊號跨機器／同帳號多工作區的穩定性尚未有一手觀測驗證；方向仍安全
  （過度區分只讓樣本池變小、退回保守估計，不會讓攤提放寬）。

**非目標澄清**（呼應 §1.3）：本機制的目的是被動適配使用者已經自然發生的
合法方案/帳號變更，其估計結果只會讓攤提**更貼近真實情況**（可能更寬鬆也
可能更保守，取決於新方案的實際容量），**不是**協助偵測或切換帳號以規避
額度限制的機制。

#### 4.1.5 遙測全失效時的收斂姿態（v2.1.8 修憲；標的＝§8-6）

**原條文（§8-6／§4.1.2）**：全部失效 → `DRAINING` + 告警，絕不猜測用量繼續派工；
`age > TELEMETRY_TIMEOUT (600s)` → 強制 `DRAINING`。

**衝突事實（本包當回合實測）**：

| 觀測 | 實測值／逐字 | 為什麼這讓原條文在本實作裡到不了 |
| :---- | :---- | :---- |
| 量不到時的 cap | `tools/lib/quota_policy.py` 出廠 `degraded_cap=4`、`cap_converge=4`、`cap_prepare=2`；本包實跑 `degraded_cap == cap_converge` ⇒ **`True`**【v2.1.4 落款注：此欄為 v2.1.8 立案當時實測，保留為歷史證據；R100 已依 R-4.1.5-1 收緊出廠值至 ≤ `cap_prepare`，現值一律現查 `ENV_SPEC`】 | 「完全量不到」與「量到 70% CONVERGE 帶」在致動器上是**同一個 cap** ⇒ 量不到沒有換來任何收緊 |
| 量不到時的帶別 | `tools/lib/quota_gate.py::draining()` 對 `BAND_UNMEASURED` 明文 `return "unknown"` | `draining()` 結構上永遠不會對量不到回 `"yes"` ⇒「全失效 → `DRAINING`」在本實作**沒有可達路徑** |
| 訊息面 | `tools/lib/quota_gate.py:551` 逐字：`⚠️  額度水位**量不到**（source=...）⇒ 本次不節流，扇出照常放行。`；同檔 `:832` 註解自述「量不到時 `decide()` 回 `degraded_cap`（不是不設限、也永不 halt）」 | 同一個決策有兩份互相矛盾的敘述，而**只有訊息那一份有讀者** |

**R-4.1.5-1（量不到 ⇒ 收斂到 `cap_prepare` 語意）** 遙測全失效（`TELEMETRY_SOURCE_ORDER`
逐一降級完畢，且逐字稿裡沒有可當地板的未復原撞線）時，致動器的硬上限必須**至少**收到
「準備下一次 reset」那一帶的緊度：`cap ≤ cap_prepare`。

- **為什麼改寫成 cap 而不是維持 `DRAINING`**：`DRAINING` 是**狀態機**的字，本實作沒有那個
  狀態物件，只有 band ＋ cap（唯一判讀入口＝`quota_policy.decide()`）。用不存在的物件寫
  需求，下游只能靠推論落地，而推論不會轉紅。改寫成 cap 語意後方向完全相同、且更緊
  （`cap_prepare` 嚴格緊於現行 `degraded_cap`），並且**可以直接驗收**。
- **為什麼不是 `cap = 0`**：0＝靜默鎖死，本實作已明文禁止。🔴 **引文歸屬（v2.1.9 訂正）**：
  「非 halt 一律 `>=1`：**禁止靜默鎖死**；上界 `max_fanout`」這句掛的是
  `tools/lib/quota_policy.py::_clamp()`，**不是** `_bound()`——後者函式體實查只有
  `return rec if cap is None else min(rec, cap)`（沒有任何下界），它的註解講的是另一件事
  （`rec > cap` 是自相矛盾的建議）。兩支同在該檔相鄰兩處、名字相似，而只有 `_clamp()` 真的
  夾下界 ⇒ 依錯的那一支去找實作會找到一個不存在的保證。量不到不是「已經撞線」，把它折成
  halt 就是把「量不到」當成「量到 100%」——與下一段那條紀律的另一邊撞上。

**🔴 與既有紀律「量不到 ≠ 量到零」如何共存（本節最容易被誤讀的一格）**

那條紀律禁止的是**把 unmeasured 當成一個具體讀數去做推論**——當 0% 而放行、當 100% 而
halt、把過期讀數「上調一個安全邊際」當成新讀數（`read_quota()` 的 `stale-cache` 分支
逐字：「這個量非單調（視窗翻頁會驟降）也非等速……所以『上調一個安全邊際』同樣是猜」）。
它**不**禁止「在不知道的情況下把行為收緊」：收緊不需要一個假讀數當前提，它需要的只是
「我不知道」這件事本身。

兩者在判準上也分得開，而且分界線是機械可查的：

- 造假讀數 ⇒ `band` 會變成一個具體帶別（可觀測的違規）。
- 依「不知道」收緊 ⇒ 只動 `cap`，`band` 逐字仍為 `BAND_UNMEASURED`。

⇒ **規範性要求**：本條只動 `cap`。`band` 必須繼續是 `unmeasured`、`draining()` 必須繼續
回 `"unknown"`；既有鎖 `tools/tests/test_context_budget_guard.py::
PrdDrainPercentMapsToTheBandsTest::test_the_three_state_answer_never_folds_unmeasurable_into_no`
不得因本條而鬆動。

**🔴 這個旋鈕有幾個家（v2.1.9 補；擇一寫死，並修掉一處自相矛盾）**

`§6` 區塊 2 的 `TELEMETRY_UNMEASURED_CAP` 與實作面既有的 `AUTOSDD_QUOTA_DEGRADED_CAP`
（→ `tools/lib/quota_policy.py::Policy.degraded_cap`；`tools/lib/quota_policy_env.py::ENV_SPEC`
實查 `EnvVar("AUTOSDD_QUOTA_DEGRADED_CAP", "degraded_cap", 4, "int", 1.0, None, "量不到時的
上限（絕不是「不設限」）", "policy")`）**治的是同一個數字**。三個候選處置與判決：

| # | 候選 | 判決 |
| :-- | :---- | :---- |
| (i) | **同一旋鈕的兩個命名面**（PRD 面 `TELEMETRY_UNMEASURED_CAP` ↔ 實作面 `AUTOSDD_QUOTA_DEGRADED_CAP`），對映機械登記，數值 SSOT 在實作面 | ✅ **採用**。本文件**已有同型判例**：`TOKEN_WARN_PERCENT`／`TOKEN_DRAIN_PERCENT`／`TOKEN_HALT_PERCENT` 三個 PRD 面名字對映到 `Policy.converge_pct`／`prepare_pct`／`halt_pct`，而那個對映**已經有機械物**＝`tools/tests/test_context_budget_guard.py::PrdDrainPercentMapsToTheBandsTest._PAIRS`（分母直接讀本 PRD 檔）⇒ 沿用既有形態，不發明第二種 |
| (ii) | 新旋鈕再夾（`cap = min(degraded_cap, TELEMETRY_UNMEASURED_CAP)`） | ❌ 同一個數字兩個家：讀者要判「現在生效的是哪一個」得讀程式碼。兩個家的漂移方向是**放寬**（任一家被調鬆就鬆） |
| (iii) | 只在 `decide()` 內夾死、不設任何 env 鍵 | ❌ operator 失去唯一的收緊手段，而本節整段的立案就是「量不到時要能收得更緊」 |

⇒ **規範性要求**：
1. 對映必須進 `_PAIRS` 那張表（同形新增一列 `("TELEMETRY_UNMEASURED_CAP", "degraded_cap")`），
   於是兩邊漂開時會**真的轉紅**，而不是靠讀者自行推論。
2. **不新增第二個 env 鍵**。`.env.example` 的 `TELEMETRY_UNMEASURED_CAP` 是 PRD 面的名字，
   載入時映到 `degraded_cap`。
3. **出廠值的家在實作面**，本 PRD 不複寫數字（現查 `ENV_SPEC`）；本 PRD 只登記**約束**：
   `1 ≤ degraded_cap ≤ cap_prepare`。上界是本次修憲新增的部分，也是 F1 唯一的內容。
4. 🔴 **修掉一處自相矛盾**：原 `.env` 註解寫「留空＝取 `cap_prepare`」，而同一次修憲新增的
   `AVAILABILITY_MIN_DWELL_SECONDS` 寫「留空＝取實作預設」——兩種「留空」語意不同，且前者
   在實作面**不成立**（留空時 `ENV_SPEC` 給的是 `degraded_cap` 的出廠值 **4**，而
   `cap_prepare` 實查為 **2**，`4 > 2` 直接違反本節上界）。統一為「**留空＝取實作面出廠值**」，
   並把「≤ cap_prepare」從「留空時的取值規則」改成「**對出廠值本身的不變式**」——即出廠值
   必須被調到滿足上界，而不是靠留空時偷偷換一個值。兩者的差別是可觀測的：後者會讓
   `.env` 顯式寫 `4` 與留空得到**不同**結果，而那正是 operator 最容易誤判的形態。

**R-4.1.5-2（訊息中的姿態字面必須與 `decide()` 實際 cap 一致）** 任何對外的降級告警，其
**姿態字面**（節流／不節流、放行／收緊、cap 數值）一律由該次 `decide()` 的回傳值算出來，
不得寫成常數字串；同一個決策不得有兩份敘述。

- **為什麼這是修憲層級而不是文案問題**：訊息是這條路上**唯一**的讀者介面（`decide()` 算
  出來的 cap 不會出現在畫面上，`note_degraded()` 檔頭已記載「這條路此前是零 stderr、零
  痕跡，與『額度很健康』外觀一模一樣」）。訊息說「照常放行」而致動器其實收到一個上限，
  兩個方向的誤判都會發生：operator 以為沒保護而過度手動收斂，或以為有保護而放心加派。
- 🔴 **判準必須是「同源」而不是「字面比對」**：斷言訊息裡的 cap 數字**取自**同一次
  `decide()` 的結果（例如把 `degraded_cap` 換成一個哨兵值，訊息必須跟著變），而不是斷言
  訊息裡出現某個特定字串——後者只鎖死一句文案，改用詞就假紅。

**驗收判準（全部可機械查證）**：

| # | 判準 | 查證方式 |
| :---- | :---- | :---- |
| F1 | `axes == ()`（量不到）⇒ `decide().cap ≤ cap_prepare` | 單元測試。**紅綠自證**：把 `degraded_cap` 調回等於 `cap_converge` 的值即必須轉紅（否則這條測試對本次修憲沒有鑑別力） |
| F2 | 同一輸入下 `band` 仍為 `BAND_UNMEASURED`、`draining()` 仍回 `"unknown"` | 控制組單元測試 ＋ 既有鎖 `test_the_three_state_answer_never_folds_unmeasurable_into_no` 必須繼續綠 |
| F3 | `cap ≥ 1`（禁止靜默鎖死） | 單元測試（掃 band × horizon 全笛卡兒積）。🔴 **判準的精確形態（v2.1.9 訂正）：`cap is None`（＝不設限）不受本條約束；只有「有限的 cap」才須 ≥ 1，且 `BAND_HALT` 的 0 是唯一例外。** 照原字面「非 halt 一律 ≥ 1」寫成測試會在 `BAND_FREE` 那一格**失敗**——當回合實查 `_cap_for(BAND_FREE, h, p)` 在 `near`／`mid`／`far` 三個 horizon 皆為 `None`，而 `None >= 1` 在 Python 直接 `TypeError`。可查形態：`assert cap is None or cap >= 1 or band == BAND_HALT` |
| F4 | 降級告警的 cap 數字隨 `decide()` 變動，且不得出現與實際 cap 相反的姿態字面 | 單元測試：注入哨兵 `degraded_cap` ⇒ 斷言訊息含該值；另斷言「不節流」「照常放行」這類**放行姿態字面**在 cap 有限時不出現（判準取姿態詞彙表，不取整句文案） |
| F5 | 【v2.1.9 新增】`TELEMETRY_UNMEASURED_CAP` ↔ `Policy.degraded_cap` 的對映是**機械登記**的，且出廠值滿足 `1 ≤ degraded_cap ≤ cap_prepare` | 後設鎖：在 `PrdDrainPercentMapsToTheBandsTest._PAIRS` 同形新增一列，分母直接讀本 PRD 檔 ⇒ 兩邊漂開必紅。**紅綠自證**：把實作面出廠值改成 `cap_converge`（實查 4）必須讓上界斷言轉紅。🔴 另需一格**反向**斷言：不得同時存在第二個治同一個數字的 env 鍵（判準＝`ENV_SPEC` 內 `attr == "degraded_cap"` 的項恰好一個） |

### 4.2 配速控制器（Pacing Controller）— 修正後的數學模型

#### 4.2.1 燃燒率估計（加入 EWMA 與統一下限）

```
Δ          = MONITOR_POLL_INTERVAL_SECONDS / 60           # 取樣間隔（分鐘）
v_sample   = max(0, U5h(t) − U5h(t−Δ)) / Δ                # 瞬時值 (%/min)
V_actual   = α · v_sample + (1 − α) · V_actual(t−Δ)        # α = BURN_RATE_EWMA_ALPHA (0.25)
V_eff      = max(V_FLOOR, V_actual)                        # V_FLOOR = 0.02 %/min（單一定義，不再有 0.01/0.02 分歧）
```
`BURNING_RATE_WINDOW_MINUTES=15` 由 EWMA 取代；若保留固定視窗，需明確定義為長度 `window/Δ` 的環形緩衝，且在重置時清空。EWMA 的等效時間常數約為 `Δ·(1/α) = 4 分鐘`（以 60 秒取樣、α=0.25），可藉 α 調整。

#### 4.2.2 安全燃燒率與目標併發

```
U_rem      = max(0, DRAIN_PERCENT − U5h_effective)         # U5h_effective 已含本機推估安全邊際
T_rem      = (reset_timestamp − now) / 60                   # 分鐘

# 重置臨界處理（v1 用 max(1, ...) 會製造假暴衝）
若 T_rem < T_MIN_MINUTES (2):
    → 不派新工，進入短暫 hold，等待重置事件
V_safe     = U_rem / max(T_MIN_MINUTES, T_rem)

C_raw      = floor(C_default × V_safe / V_eff)
C_target   = clamp(C_raw, C_min, C_cap(state))              # ← v1 缺少狀態上限，是驗收矛盾的根源
```

#### 4.2.3 閘門與致動器優先序（先否決、後配速）

決策順序固定，任一步命中即短路：

```
1. HALTED_MANUAL                         → C = 0
2. 遙測狀態不明（見 §4.1.2）              → C = 0 或 1（依 FAIL_SAFE_MODE）
3. U7d ≥ WEEKLY_HALT_PERCENT             → C = 0，狀態 = LONG_HIBERNATE
4. U5h ≥ HALT_PERCENT                    → C = 0，狀態 = FREEZING
5. U5h ≥ DRAIN_PERCENT                   → C = 0，狀態 = DRAINING
6. U7d ≥ WEEKLY_DRAIN_PERCENT            → C = min(C_target, 1)
7. U7d_model ≥ MODEL_DOWNGRADE_PERCENT   → 模型降級（見下），併發不變
8. 其他                                   → C = C_target
```

🔴 **model-scoped 軸的 cap 聚合劃界（v2.1.4 落款補注；`DEF-200-157`）**：cap 聚合對 model-scoped 軸（第 7 步的 `U7d_model`，如 `seven_day_opus`）依 `active_model` 過濾——僅當該軸對應模型與當前活躍模型相符才進 cap 聚合（R98 `MODEL_SCOPED_KINDS`＋`_in_cap_gate`、R105 `active_model` 接線，皆已落地：`tools/lib/quota_policy.py`、`tools/lib/quota_gate.py`）⇒ 模型降級後，高階模型的週軸真的退出 cap，降級換得到放行空間。

**致動器不只有「併發數」**（v1 只有一個致動器，控制力不足）：

| 致動器 | 效果 | 觸發時機 |
| :---- | :---- | :---- |
| 併發 Agent 數 `C(t)` | 線性影響燃燒率 | 全程 |
| **模型層級降級** | 高階模型的額度消耗率遠高於中階模型，降級的節流效果通常大於減併發 | `THROTTLING` 或 `U7d_model` 超標 |
| **任務類別過濾** | 暫停「大規模重構」「全庫檢索」等高成本類別，只放行小型任務 | `THROTTLING` 起 |
| **Agent 硬性預算** | 單一 Step 的 turn 數／時間／估計 token 上限，防止單一 Agent 在 `DRAINING` 期間衝破 `HALT` | 全程，`DRAINING` 期間收緊 |

> `[需核對]` 模型降級的具體旗標，以及訂閱制方案是否已內建自動降級行為（若已內建，本模組應以「不牴觸」為原則，僅在更早的水位主動降級）。【v2.1.4 指針：前半「具體旗標」已於附錄 B-11 核實（`--model`／`Agent` 工具 `model` 欄／`CLAUDE_CODE_SUBAGENT_MODEL`），模型分軌額度見 B-02；後半「訂閱制方案是否已內建自動降級行為」仍未核實，保留待核對】

#### 4.2.4 平穩性機制（v1 完全缺漏，是實務上最會出事的部分）

🔴 **v2.1.8 修憲**：運算元從 `C_current`／`C_target` 改為本實作的 cap 語意，且遲滯與
最小停留時間**改掛「量測可得性」軸**（不是掛在 watermark 上）。以下先記原條文與判決
依據，再給新條文全文。

**原條文（v2.0~v2.1.7，逐字保留供對照）**：

```
# (a) 遲滯帶：避免在門檻附近抖動
進入 THROTTLING: U5h ≥ WARN
離開 THROTTLING: U5h ≤ WARN − WATERMARK_HYSTERESIS_PP (3)
# (b) 死區：微小變化不動作            若 |C_target − C_current| < 1 → 不變更
# (c) 變化率限制（slew rate）         C_next = clamp(C_target, C_current − 1, C_current + 1)
#     例外：升級到 DRAINING/FREEZING 時允許直接歸零（安全方向不限速）
# (d) 最小停留時間                    若 (now − last_change) < MIN_DWELL_SECONDS (300) → 不變更（僅「增加」方向）
# (e) 控制週期 vs 死時間              CONTROL_INTERVAL_SECONDS ≥ 2× 單一 Step 的中位執行時間
```

**判決依據（兩項，皆為本包當回合實測；探針為唯讀）**：

| # | 量測 | 母體與方法 | 結果 |
| :-- | :---- | :---- | :---- |
| 1 | watermark 遲滯要防的病，這台機器**得不到** | `~/.autosdd/traces/quota_burn.jsonl` 全量重放（span `2026-08-12T22:45:43+08:00` .. `2026-08-22T07:01:10+08:00`，**119 筆 / 8 軸 / 819 個逐軸讀數**）；逐軸把 pct 換成 `quota_policy.pct_band()` 的帶別，數「一次下降之後緊接著一次上升」的次數，並把跌幅 ≥ 20pp（§4.1.3 `RESET_DROP_THRESHOLD`）的下降剔為視窗翻頁 | `band_changes=77 up=44 down=33 down_of_which_window_resets=33` ⇒ **`SMALL_WOBBLE_REVERSALS=0`**。**33 次下降穿越全部是視窗翻頁**，視窗內 usage 單增 ⇒ 結構上不可能來回穿越門檻 |
| 2 | 真正在抖的是**量測可得性** | 同期兩串痕跡按時間合併：measured 事件源＝burn ledger（只有量到才落款）／unmeasured 事件源＝`autosdd_quota_degraded.jsonl`（`note_degraded()` 每 180s 閂鎖一次 ⇒ 每筆代表一個相異降級視窗）。窗＝degraded 痕跡存在的那段（`2026-08-21T18:56:59+08:00` .. `2026-08-22T07:01:10+08:00`） | `measured_events=23 unmeasured_events=14` ⇒ **`AVAILABILITY_FLIPS=19`**（約 12 小時）。序列逐字：`UMMMUMMMMUMUMMUMMUUUMMMMUMMMUUMUUMUMM` |

⇒ **遲滯必須掛在真的會抖的那一軸**。掛在 watermark 上不是「多一層保險」，是把一個機制
建在它自己的盲區上（十天 819 個讀數換來 0 次動作），同時讓真正每小時翻好幾次的那一軸
完全裸奔。

**運算元對照（本實作沒有持久的併發設定點，這是整段要改寫的根因）**：

| 原條文運算元 | 本實作的等價物 | 差異在哪 |
| :---- | :---- | :---- |
| `C_current`（持久的併發設定點） | **不存在**。致動器是「每次工具呼叫的准入控制」：`quota_policy.decide()` 每次重算 `cap`（硬上限，`None`＝不設限）＋ 300 秒滾動派發帳 `live_dispatches()`（`tools/lib/quota_gate.py::FANOUT_WINDOW_SECONDS`） | 沒有 setpoint 可以「比較上一次」⇒ (b)(c)(d) 三條原文字面無物可依 |
| `C_target` | `decide().cap`（硬上限）／`decide().recommended_fanout`（諮詢值） | `cap` 是**無狀態純函式**：由 `(band, horizon)` 導出（`_cap_for()`），不帶記憶 |
| `WATERMARK_HYSTERESIS_PP` | **廢除**（見上表判決依據 1）。遲滯改掛可得性軸（新常數見 (a)） | 遲滯的宿主換軸，不是換值 |
| 「控制週期」 | 派發帳滾動視窗 `FANOUT_WINDOW_SECONDS`（現值現查該檔） | 「量測週期」對應 `QUOTA_CACHE_TTL_SECONDS`（額度快取 TTL） |

**新條文（v2.1.8 起生效）**：

```
# (a) 遲滯帶 —— 掛在「量測可得性」軸，不是 watermark
availability ∈ {measured, unmeasured}                    # 唯一有遲滯的軸
進入 unmeasured：本次 read_quota() 不 usable（含 bad-cache / stale-cache 兩形態）
                 ⇒ 立即生效，收緊方向不受遲滯與 dwell 約束（同原文 (c) 的例外條款）
離開 unmeasured：連續 AVAILABILITY_EXIT_STREAK 次（≥2）read_quota() 皆 usable
                 且 (now − availability_entered_at) ≥ AVAILABILITY_MIN_DWELL_SECONDS

# (b) 死區 —— 由 band 量化本身提供，不是另一個門檻
cap 一律由 band 導出（_cap_for(band, horizon, p)），**不得**由 pct 連續函數直接算。
理由：帶別是階梯函數，帶內任何 pct 噪音都不產生任何動作 ⇒ 死區是結構性的、不需要
      第二個參數；改成連續函數則死區當場消失，而失效外觀與「調得比較靈敏」相同。
諮詢值 recommended_fanout 另有顯示層死區：|new − last| < 1 ⇒ 不改寫顯示。

# (c) 變化率限制 —— 安全方向不限速，放寬方向走階梯
收緊方向（cap 變小、或 measured→unmeasured）：不限速，允許直接到位。
放寬方向：受 (a) 的 streak ＋ (d) 的 dwell 管；且 cap 對 band 必須單調
          （水位愈高 cap 不得愈鬆），由既有 quota_policy 的單調性自檢守住
          （違反時逐字印 `[非單調] ... ⇒ 水位愈高反而愈鬆`）。
🔴 unmeasured → measured 是「沒有中間級」的躍遷（有限的 degraded cap ↔ 可能直接到不設限）
   ⇒ 它是 (c) 要限速的那一格，而限速手段即 (a)(d)，不另立第三個機制。
   【v2.1.9 訂正】原文寫「**唯一**沒有中間級」，該字已刪：實查 `_cap_for()` 的階梯，
   measured 軸**內部**同型的躍遷至少還有一個——`notice → free` 是「有限 cap → None
   （不設限）」，且 `BAND_FREE` 在 near／mid／far 三個 horizon 皆為 `None`
   （`notice` 於 mid 為 8）⇒ 一樣沒有中間級。原文用「唯一」去論證「(c) 不需要第三個
   機制」，論據因此不完整；結論仍成立，但改由**另一個**理由承重：那一格已經有既有守衛
   （§11.2「重置後不暴衝」逐字要求翻頁後第一拍 `cap ≤ cap_notice`，即 `None` 不得在翻頁
   後第一拍出現）⇒ 不是沒人管，是**已經由別條管**，不必在本節再立第三個機制。

# (d) 最小停留時間 —— 只約束放寬方向，狀態必須落磁碟
遲滯要記住的只有兩格：(availability, availability_entered_at)
不變式：QUOTA_CACHE_TTL_SECONDS ≤ AVAILABILITY_MIN_DWELL_SECONDS ≤ SENTINEL_INTERVAL_SECONDS
  下界：dwell 短於量測週期＝結構上無效（翻動的成因就是快取 TTL 邊界）
  上界：dwell 長於「reset 之後最壞多久才會有人動作」＝一次瞬時降級把整段時間鎖在
        degraded cap 上，而那段時間本機自己都已經反應過一輪了
  兩個界都是**導出的**、且各有既有的家 ⇒ 現值一律現查實作，本 PRD 不複寫數字

# (e) 控制週期 vs 死時間 —— 保留，且列為本段的優先實作項
FANOUT_WINDOW_SECONDS ≥ 2× 單一 Step 的中位牆鐘執行時間（量測值，現查）
FANOUT_WINDOW_SECONDS ≥ QUOTA_CACHE_TTL_SECONDS      # 控制不得比量測快（＝原文的積分飽和）
```

**🔴 遲滯狀態記在哪（本段唯一需要新增持久化的東西，先劃清「不算新開一層」的界線）**

- **家**：`tools/lib/endurance_env.py::trace_dir()`（出廠 `~/.autosdd/traces`，逃生口
  `AUTOSDD_TRACE_DIR`）底下**一支專屬檔**，經一支與 `tools/lib/quota_gate.py::
  burn_ledger_path()` 同形的 `*_path()` 存取器取得。
- **為什麼不用系統暫存**：這一格的**全部職責就是記住**。`tempfile.gettempdir()` 的痕跡
  重開機即消失（本 repo 明文紀律：「查不到」≠「沒發生」）⇒ 遲滯狀態蒸發＝dwell 計時器
  歸零＝回到翻動，而失效外觀與「遲滯正常運作」完全相同。
- 🔴 **`trace_dir()` 自己就會靜默退回系統暫存 ⇒ 選它當家並不足以滿足上一條**（v2.1.9
  補；此前本節花整段論證「絕不能用系統暫存」，卻挑了一個會自己退回系統暫存的存取器）。
  函式體逐字有**兩處**這種退回：

```
    try:
        want.mkdir(parents=True, exist_ok=True)
    except OSError:
        return Path(tempfile.gettempdir())              # ← 退回 ①（OSError 分支）
    return want if os.access(want, os.W_OK) else Path(tempfile.gettempdir())
                                                        # ← 退回 ②（不可寫的三元運算）
```

  該函式檔頭並已逐字自陳這是**刻意**的設計：「拿不到就退回 `$TMPDIR`（**退化，不是失敗**：
  痕跡留不下來絕不可反過來變成續航本身的故障源）」，且「兩層都檢查是刻意的：`mkdir` 成功
  不等於寫得進去……而那種失敗的表徵正好是**痕跡檔不會長大**——與『沒觸發』完全同形」。
  ⇒ 對**痕跡**而言退化是對的（少一筆稽核紀錄，不影響決策）；對**遲滯狀態**而言退化是
  **決策層的失效**（dwell 是判決的唯一真相源，狀態沒了就等於遲滯沒了）。同一個存取器，
  兩種消費者，容忍度不同。

  🔴 **規範性要求（不改 `trace_dir()` 的既有語意，改的是本節這個消費者的姿態）**：
  1. 取得目錄後必須**判定它是不是那個持久目錄**（＝與 `AUTOSDD_TRACE_DIR`／
     `~/.autosdd/traces` 的解析結果相等）。相等⇒正常路徑。
  2. **不相等（即已退回系統暫存）時，三件事同時做**：(i) 走 §4.5.7 R-4.5.7-3 的通道
     **loud 一次**（不是只寫進痕跡——痕跡正是此刻壞掉的那個東西）；(ii) 自檢輸出必須逐字
     標明**「遲滯已降級」**並附退回後的實際路徑；(iii) 該次決策的 cap 一律走**收緊側**
     （視同 `unmeasured`），因為此刻 dwell 這半邊的判決能力確實已經沒有了。
  3. **不得**把退回當成正常路徑靜默吃掉。判準的可查形態：降級時自檢輸出含「遲滯已降級」
     字樣；未降級時**不得**含（兩向都要驗，否則常印那句話等於沒印）。
- **為什麼不併進 `quota_burn.jsonl`**：(1) 一份檔一個寫者（§4.5.6 R-4.5.6-3 的單檔雙寫者
  禁令，立案＝哨兵死於被覆寫的任務書）；(2) burn ledger **只在量到時落款**，結構上記不下
  `unmeasured` 那一半——併進去就是把這個機制建在它自己的盲區上（與上表判決依據 1 同型的
  錯誤）。
- **為什麼這不算「新開一層」**：新增的是**既有持久痕跡層的一個成員**，逃生口與沙箱隔離
  兩件事都沿用既有機制。⇒ **規範性要求**：該存取器必須登記進既有的沙箱隔離表
  （`tools/tests/test_context_budget_guard.py::_TRACE_ISOLATION`，現有四格
  `quota_trace_path`／`degraded_stamp_path`／`refresh_stamp_path`／`burn_ledger_path`）。
  漏登記的後果該表已逐字記載：跑一次測試就往生產面寫假紀錄並吃掉真的閂鎖。
- **寫入必須原子**：多個 hook 行程並行是已觀測輸入形態（`note_degraded()` 檔頭記載 42 個
  平行 hook 同時降級、`claim_refresh_slot()` 記載 16 個壁鐘 barrier 對齊行程實測
  `CLAIM=16 SKIP=0` 的 check-then-act 事故）⇒ **不得**自己寫 check-then-act。

  🔴 **原語必須寫死，而 v2.1.8 指的那兩支都承載不了這個狀態**（v2.1.9 訂正；原條文寫
  「一律走既有的 `quota_ledger.claim_once()`／`append_record()` 原語」，而遲滯狀態是
  **dwell 判決的唯一真相源**，不是一筆事後痕跡）：

  | 原語 | 它實際是什麼 | 為什麼承載不了 |
  | :---- | :---- | :---- |
  | `quota_ledger.append_record()` | `O_APPEND` ＋單次 `os.write` 的**追加**器 | 該模組 docstring〈誠實劃界〉逐字：「它在同一瞬間 N 個行程同時寫時**仍可能掉行**。這是刻意的取捨而不是漏看……痕跡是事後可稽核的那一半，**不是唯一那一半**。」掉一行痕跡＝少一筆稽核；掉一次狀態更新＝dwell 計時器停在舊值 ⇒ 該放寬的不放寬、或該擋的不擋。**追加**語意本身也不對：這一格要的是「**替換**一份 2 欄狀態」，append 會留下 N 個版本而讀者得自己決定哪一個是現在 |
  | `quota_ledger.claim_once()` | **TTL 閂鎖**（`O_CREAT\|O_EXCL` 的一次性佔位），回 `bool` | 它回答的是「這一屆是不是我的」，**不是狀態存取器**：既寫不進 `(availability, availability_entered_at)` 這兩個值，也讀不出來。它在本節仍有正當用途——把 loud（上一條第 2 點的 (i)）節流成「每 TTL 一次」——但那是**另一件事** |

  ⇒ **規範性形態（擇一寫死，本 PRD 選第一種）**：**tmp → `flush()` → `os.fsync(fd)` →
  `close()` → `os.replace(tmp, final)` 的原子換名**，每次寫入整份取代那 2 欄狀態。

  - **為什麼選它**：§4.5.1 步驟 4 已逐字是這個紀律（`原子寫入 state.json（tmp → fsync →
    rename）`），R-4.5.9-3 步驟 1 也剛剛沿用同一套 ⇒ 同一份規格裡只有一種「原子寫一份小
    狀態」的手法，讀者不必猜。`os.replace` 在 POSIX 與 Windows 上皆為原子換名。
  - **兩個必須一起寫下來的平台事實**（鐵律三）：(i) `os.replace` 在 Windows 覆寫「被別人
    開著」的目的檔會 **WinError 5**（鐵律三該列機械物＝`TestDirEntryPrimitivesAreAccountedFor`）
    ⇒ 讀取端必須「開檔、讀完、立刻關」，不得長期持有 handle；(ii) tmp 檔必須與 final
    **同一個目錄**（跨檔案系統的 `os.replace` 不是原子的，且會拋 `OSError`）。
  - **讀取端的失效姿態**：讀不到／解不出（首次啟動、或檔被外力刪除）⇒ 視同「剛進入
    unmeasured」而**不是**「dwell 已滿」。兩者的差別就是 fail-safe 的方向：前者收緊、
    後者放行。
  - **替代形態（若實作者選它，必須在 PR 描述裡具名並說明為何）**：在 `quota_ledger` 增設
    一支 read-modify-write 存取器（例如 `swap_state(path, fn)`）並把上述原子換名收在裡面。
    這是同一件事的不同放置處，**不是**放寬——`append_record()` 這條路無論放在哪裡都不合格。

**驗收判準（全部可機械查證；§11.2 兩支性質測試的新語意見該節）**：

| # | 判準 | 查證方式 |
| :---- | :---- | :---- |
| H1 | 遲滯掛在可得性軸：以本節實測序列 `UMMMUMMMMUMUMMUMMUUUMMMMUMMMUUMUUMUMM`（**37 個符號、19 次翻動**，兩者皆機械現查）**＋每個符號一個時間戳**為輸入，開啟遲滯的 cap 變動次數 **嚴格小於** 關閉遲滯者 | 單元測試（對照組即紅綠自證）。母體刻意用實測形態而非合成隨機走：合成序列證明不了「這台機器真的會這樣抖」。🔴 **時間戳是判準的一部分，不是佈景**（v2.1.9 補）：dwell 以**秒**計，而 37 個字元的 U/M 序列**不含任何時間資訊** ⇒ 光靠它決定不了 (d) 那一半，同一個序列在「翻動間隔 1 秒」與「間隔 1 小時」下的正確答案相反（前者 dwell 全程未滿、後者全滿）。補法見下方〈H1 的時間軸怎麼補〉，通過門檻唯一 |
| H2 | 收緊方向不限速（measured→unmeasured 立即生效，不等 streak／dwell） | 單元測試。控制組：把收緊也套上 dwell ⇒ 必須紅（那會讓量不到的期間繼續放行，方向與 §0 第 6 條 fail-safe 相反） |
| H3 | 放寬方向必過 streak ＋ dwell：任何一次 unmeasured→measured 的 cap 放寬，其 `now − entered_at ≥ AVAILABILITY_MIN_DWELL_SECONDS` | 單元測試（注入時間，不睡） |
| H4a | 遲滯狀態存活於行程之外：兩次獨立行程呼叫之間 dwell 計時器不得歸零 | 整合測試（兩次 subprocess，共用沙箱 `AUTOSDD_TRACE_DIR`）。**這一條是本段最容易被實作成假綠的一格**——把狀態放在模組級變數，單元測試會全綠而生產零效果 |
| H4b | 🔴 **持久目錄拿不到時必須出聲**：**不**設 `AUTOSDD_TRACE_DIR`、而是讓解析出來的持久目錄變成**不可寫**（`chmod` 掉寫位元，或指向一個 `mkdir` 會 `OSError` 的路徑），斷言 (i) loud 恰好發生一次、(ii) 自檢輸出含「遲滯已降級」＋退回後的實際路徑、(iii) 該次 cap 走收緊側 | 整合測試。**🔴 為什麼必須與 H4a 分成兩格**：H4a 走的是 `AUTOSDD_TRACE_DIR` 沙箱＝**永遠是可寫的持久目錄**，於是它結構上永遠踩不到 `trace_dir()` 的兩處退回 ⇒ 退回真的發生時 H4a 仍是綠的。**控制組**：目錄可寫時**不得**出現「遲滯已降級」字樣（只有單向斷言的話，一個「每次都印」的實作會通過）。🔴 兩處退回**各要一格**：`mkdir` 失敗（OSError 分支）與 `os.access` 為假（三元運算分支）是不同的程式路徑，只驗一個等於只守一半 |
| H5 | cap 一律由 band 導出（(b) 的死區） | 靜態判準：`_cap_for()` 的入參不得含連續的 pct；＋既有單調性自檢必須繼續綠 |
| H6 | 不變式 `QUOTA_CACHE_TTL_SECONDS ≤ AVAILABILITY_MIN_DWELL_SECONDS ≤ SENTINEL_INTERVAL_SECONDS` 在啟動自檢被驗（§6.1 第 4 條） | 單元測試（三個值任一越界即拒絕啟動） |
| H7 | (e)：`FANOUT_WINDOW_SECONDS ≥ QUOTA_CACHE_TTL_SECONDS` 且 ≥ 2× Step 中位牆鐘時間 | 單元測試（前半為常數比較）＋ §9 需新增 Step 牆鐘時間 histogram 才能驗後半（見 §9 該列） |

**🔴 H1 的時間軸怎麼補（v2.1.9；實作者不得自行選一種，本段寫死使通過門檻唯一）**

原始序列是從兩串痕跡按時間合併算出來的，**時間戳在來源裡就有**，是摘要成字串時掉的：
`measured` 事件源＝burn ledger（`quota_burn.jsonl`，每筆帶落款時刻）／`unmeasured` 事件源＝
`autosdd_quota_degraded.jsonl`（`note_degraded()` 每 180s 閂鎖一次 ⇒ 每筆代表一個相異降級
視窗）。⇒ 補的方式是**取回**，不是編造：

1. **母體形態**：`(symbol, offset_seconds)` 的序列，`offset_seconds` 為相對序列首筆的秒數
   （整數，單調不減）。序列長度必須仍是 **37**，翻動數必須仍是 **19**（兩個數字是本節立案
   母體的指紋，變了就不是同一個母體）。
2. **時間戳從哪來**：由實作者以唯讀探針對上述兩串痕跡重跑一次合併，把每個符號的落款時刻
   一併取出，落成一份 **git-tracked 的 fixture 檔**（理由同 §6.2 R-6.2-2 第 2 點：本機痕跡
   檔不隨 clone 走，跑在另一台機器上會變成空母體而測試靜默轉綠）。
3. **fixture 必須自帶不變式**：載入時斷言 `len == 37` 且 `flips == 19` 且 offsets 單調不減；
   任一不成立即 fail-loud。🔴 這一格是防止「fixture 被後續某輪順手改小」——那種改動不會讓
   任何測試轉紅，除了這一格。
4. **窗長也要對得上**：整段 offsets 的跨距應落在立案窗（`2026-08-21T18:56:59+08:00` ..
   `2026-08-22T07:01:10+08:00`，約 12 小時）的量級。斷言取寬鬆上下界（例如 6~24 小時）而
   不是等值——痕跡可能被輪替，而過緊的斷言會變成假紅。
5. 🔴 **痕跡不可得時的姿態＝skip 並出聲，不得靜默降級成無時間戳版本**：後者會讓 H1 退回
   「只驗 (a) 不驗 (d)」而外觀全綠，正是本列在修的失效。


#### 4.2.5 突刺（BURSTING）判準 — v1 未定義且有觀念錯誤

v1 的「額度即將過期，全力拉滿」隱含「未用完的 5 小時額度會浪費」的假設。但**週上限是更長期的約束**：在 5 小時視窗末端暴衝，等於提前燒掉週額度，可能換來數天停權。因此突刺必須被週額度否決：

```
BURSTING 需全部成立：
  T_rem ≤ BURST_WINDOW_MINUTES (30)
  U5h   ≤ BURST_MAX_U5H_PERCENT (60)
  U7d   ≤ BURST_WEEKLY_GUARD_PERCENT (60)      ← v1 缺此條，是最危險的缺漏
  U7d 的線性預算進度 ≥ 當前 U7d（即本週尚未超支）
  待派工佇列非空且任務為可中斷型（不可中斷的長任務不得在視窗末端啟動）
  ENABLE_BURSTING = true
```
另需檢查：若 `T_rem ≤ 預估 Step 執行時間`，則新 Step 極可能跨越重置點被截斷 —— 應延後派工至重置後，而非搶跑。

#### 4.2.6 參考實作（修正版）

```python
"""AutoClaude 配速控制器 — 參考實作（v2）

與 v1 的差異：
  1. 加入狀態併發上限 C_cap(state)（修正驗收矛盾）
  2. 加入週額度閘門
  3. EWMA 平滑 + 單一 V_FLOOR 常數
  4. 視窗重置偵測（不再把負差值壓成 0）
  5. 變化率限制、死區、最小停留時間
  6. 遙測新鮮度 fail-safe
  7. 使用 monotonic 計時，wall clock 僅用於絕對重置時間
"""
from __future__ import annotations
import math
import time
from dataclasses import dataclass, field
from enum import Enum


class State(str, Enum):
    INIT = "INIT"
    CRUISING = "CRUISING"
    BURSTING = "BURSTING"
    THROTTLING = "THROTTLING"
    DRAINING = "DRAINING"
    FREEZING = "FREEZING"
    WAITING_RESET = "WAITING_RESET"
    LONG_HIBERNATE = "LONG_HIBERNATE"
    RESUMING = "RESUMING"
    HALTED_MANUAL = "HALTED_MANUAL"


V_FLOOR = 0.02          # %/min，冷啟動與除零防護的唯一定義
T_MIN_MINUTES = 2.0     # 重置臨界保護


@dataclass
class Telemetry:
    u5h: float                    # 帳號 5h 使用率 %
    u7d: float                    # 帳號週使用率 %
    u7d_model: float              # 高階模型週使用率 %
    reset_timestamp: float        # 5h 視窗重置（wall clock, epoch 秒）
    weekly_reset_timestamp: float | None
    fetched_at_monotonic: float
    source_tier: str              # "T1".."T5"
    is_local_estimate: bool       # 僅本機推估 → 需套用安全邊際


@dataclass
class Config:
    warn_percent: float = 70.0
    drain_percent: float = 85.0
    halt_percent: float = 95.0
    weekly_warn_percent: float = 70.0
    weekly_drain_percent: float = 80.0
    weekly_halt_percent: float = 90.0
    model_downgrade_percent: float = 50.0
    c_min: int = 1
    c_default: int = 2
    c_max: int = 5
    c_throttle: int = 1
    ewma_alpha: float = 0.25
    hysteresis_pp: float = 3.0
    min_dwell_seconds: float = 300.0
    poll_interval_seconds: float = 60.0
    telemetry_timeout_seconds: float = 600.0
    local_estimate_margin_pp: float = 15.0
    enable_bursting: bool = True
    burst_window_minutes: float = 30.0
    burst_max_u5h: float = 60.0
    burst_weekly_guard: float = 60.0
    fail_safe_concurrency: int = 0   # 0 = 立即排空；1 = 保留一個 Agent


@dataclass
class ControllerState:
    state: State = State.INIT
    concurrency: int = 0
    v_actual: float | None = None
    last_u5h: float | None = None
    last_change_monotonic: float = field(default_factory=time.monotonic)
    latched_drain: bool = False      # DRAINING 以上為單向鎖存


C_CAP = {
    State.INIT: 0,
    State.CRUISING: None,            # None → 用 c_max
    State.BURSTING: None,
    State.THROTTLING: "throttle",
    State.DRAINING: 0,
    State.FREEZING: 0,
    State.WAITING_RESET: 0,
    State.LONG_HIBERNATE: 0,
    State.RESUMING: 1,
    State.HALTED_MANUAL: 0,
}


def _cap_for(state: State, cfg: Config) -> int:
    cap = C_CAP[state]
    if cap is None:
        return cfg.c_max
    if cap == "throttle":
        return cfg.c_throttle
    return int(cap)


def update_burn_rate(cs: ControllerState, u5h: float, cfg: Config,
                     reset_detected: bool, v_safe_hint: float) -> float:
    """回傳平滑後的有效燃燒率 (%/min)。"""
    if reset_detected or cs.last_u5h is None:
        # 中性初值：使 v_safe / v_eff == 1，輸出 c_default，避免重置後暴衝
        cs.v_actual = max(V_FLOOR, v_safe_hint)
        cs.last_u5h = u5h
        return cs.v_actual

    delta_min = cfg.poll_interval_seconds / 60.0
    v_sample = max(0.0, u5h - cs.last_u5h) / max(delta_min, 1e-9)
    prev = cs.v_actual if cs.v_actual is not None else v_sample
    cs.v_actual = cfg.ewma_alpha * v_sample + (1 - cfg.ewma_alpha) * prev
    cs.last_u5h = u5h
    return max(V_FLOOR, cs.v_actual)


def decide(tel: Telemetry | None, cs: ControllerState, cfg: Config,
           now_monotonic: float, now_wall: float,
           queue_has_work: bool, manual_pause: bool,
           reset_detected: bool = False) -> tuple[State, int, str]:
    """回傳 (下一狀態, 允許併發數, 決策理由)。純函式，便於單元測試。"""

    # ── 閘門 1：人工覆寫優先於一切 ──
    if manual_pause:
        return State.HALTED_MANUAL, 0, "manual_pause"

    # ── 閘門 2：遙測新鮮度（fail-safe，絕不 fail-open）──
    if tel is None:
        return State.DRAINING, cfg.fail_safe_concurrency, "telemetry_unavailable"
    age = now_monotonic - tel.fetched_at_monotonic
    if age > cfg.telemetry_timeout_seconds * 2:
        return State.FREEZING, 0, f"telemetry_stale_critical:{age:.0f}s"
    if age > cfg.telemetry_timeout_seconds:
        return State.DRAINING, 0, f"telemetry_stale:{age:.0f}s"

    # 本機推估 → 悲觀化讀數
    margin = cfg.local_estimate_margin_pp if tel.is_local_estimate else 0.0
    u5h = min(100.0, tel.u5h + margin)
    u7d = min(100.0, tel.u7d + margin)

    stale_soft = age > cfg.poll_interval_seconds * 3

    # ── 閘門 3：週上限（最長 7 天，無法靠短休眠解決）──
    if u7d >= cfg.weekly_halt_percent:
        cs.latched_drain = True
        return State.LONG_HIBERNATE, 0, f"weekly_halt:{u7d:.1f}%"

    # ── 閘門 4/5：5 小時視窗硬水位 ──
    if u5h >= cfg.halt_percent:
        cs.latched_drain = True
        return State.FREEZING, 0, f"u5h_halt:{u5h:.1f}%"
    if u5h >= cfg.drain_percent or cs.latched_drain:
        cs.latched_drain = True
        return State.DRAINING, 0, f"u5h_drain:{u5h:.1f}%"

    # ── 配速計算 ──
    t_rem_min = (tel.reset_timestamp - now_wall) / 60.0
    if t_rem_min < T_MIN_MINUTES:
        return cs.state, 0, "reset_imminent_hold"

    u_rem = max(0.0, cfg.drain_percent - u5h)
    v_safe = u_rem / max(T_MIN_MINUTES, t_rem_min)
    v_eff = update_burn_rate(cs, u5h, cfg, reset_detected, v_safe)

    # ── 狀態判定（含遲滯與週額度警戒）──
    if u5h >= cfg.warn_percent or u7d >= cfg.weekly_warn_percent or stale_soft:
        next_state = State.THROTTLING
        reason = "throttle"
    elif cs.state == State.THROTTLING and u5h > cfg.warn_percent - cfg.hysteresis_pp:
        next_state = State.THROTTLING          # 遲滯：尚未跌破退出門檻
        reason = "throttle_hysteresis"
    elif (cfg.enable_bursting and queue_has_work
          and t_rem_min <= cfg.burst_window_minutes
          and u5h <= cfg.burst_max_u5h
          and u7d <= cfg.burst_weekly_guard):
        next_state = State.BURSTING
        reason = "burst"
    else:
        next_state = State.CRUISING
        reason = "cruise"

    # ── 目標併發 → 狀態上限 → 平穩性機制 ──
    c_raw = math.floor(cfg.c_default * (v_safe / v_eff))
    c_target = max(cfg.c_min, min(c_raw, _cap_for(next_state, cfg)))

    # 週額度排空警戒：壓到 1
    if u7d >= cfg.weekly_drain_percent:
        c_target = min(c_target, 1)
        reason += "+weekly_drain"

    c_next = c_target
    if c_target > cs.concurrency:
        # 只有「增加」方向受停留時間與變化率限制；「減少」不限速
        if now_monotonic - cs.last_change_monotonic < cfg.min_dwell_seconds:
            c_next = cs.concurrency
            reason += "+dwell_hold"
        else:
            c_next = min(c_target, cs.concurrency + 1)
    elif c_target < cs.concurrency:
        c_next = max(c_target, cs.concurrency - 1)

    return next_state, c_next, (
        f"{reason} u5h={u5h:.1f} u7d={u7d:.1f} t_rem={t_rem_min:.0f}m "
        f"v_safe={v_safe:.3f} v_eff={v_eff:.3f} c_raw={c_raw} c={c_next}"
    )
```

#### 4.2.7 情境試算驗證表（修正版）

v1 的四個情境算術正確，但**未反映狀態上限與變化率限制**，故第 3 列與驗收標準第 3 條矛盾。以下為修正後（假設 `C_current` 已達穩態、停留時間已滿足）：

| # | 情境 | `U5h` | `U7d` | `T_rem` | `U_rem` | `V_safe` | `V_eff` | `C_raw` | 狀態 | `C_cap` | **最終 C** | 決策說明 |
| :-- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| 1 | 視窗將重置、額度多、**週額度健康** | 20% | 40% | 30m | 65 | 2.167 | 0.20 | 21 | `BURSTING` | 5 | **5** | 允許突刺（但受 ±1 變化率限制，需數個週期爬升） |
| 1b | 同上，但**週額度已 75%** | 20% | 75% | 30m | 65 | 2.167 | 0.20 | 21 | `THROTTLING` | 1 | **1** | **v1 會誤判為衝刺 →** 週額度否決 |
| 2 | 標準巡航 | 40% | 45% | 150m | 45 | 0.300 | 0.30 | 2 | `CRUISING` | 5 | **2** | 燃燒率符合預算 |
| 3 | 燃燒過快 | 65% | 50% | 180m | 20 | 0.111 | 0.60 | 0 | `CRUISING` | 5 | **1** | `C_raw=0` 被 `C_min` 抬升到 1 |
| 3b | **驗收標準指定情境**：75% | 75% | 50% | 240m | 10 | 0.042 | 0.30 | 0 | `THROTTLING` | **1** | **1** | v1 公式在 `T_rem` 較短時可能算出 >1；v2 由 `C_cap` 保證為 1 |
| 4 | 達排空線 | 86% | 50% | 60m | 0 | 0 | 0.40 | 0 | `DRAINING` | 0 | **0** | 單向鎖存，不再回退 |
| 5 | **視窗剛重置** | 2% | 52% | 298m | 83 | 0.279 | 0.279（中性初值） | 2 | `RESUMING`→`CRUISING` | 1→5 | **1→2** | v1 會因 `V_actual` 觸底而直接跳 `C_max` |
| 6 | **遙測中斷 11 分鐘** | (舊值 30%) | — | — | — | — | — | — | `DRAINING` | 0 | **0** | v1 未定義，會沿用舊讀數繼續派工 |
| 7 | 週上限 92% | 30% | 92% | 200m | 55 | 0.275 | 0.20 | 2 | `LONG_HIBERNATE` | 0 | **0** | v1 只會休眠到 5h 重置，醒來立刻再撞牆 |

#### 4.2.8 與 CLI 內建配速門檻對齊（v2.1 核實新增）

核實發現 CLI 內部帶有一組「超前燃燒」判準，其結構是 **利用率 vs 視窗已流逝比例**：

| 額度類型 | 視窗長度 | 內建判準（利用率 / 已流逝時間比） | 換算配速指數 |
| :---- | :---- | :---- | :---- |
| `five_hour` | 18,000 秒（5 小時） | 0.90 / 0.72 | 1.25 |
| `seven_day` | 604,800 秒（7 天） | 0.75 / 0.60 · 0.50 / 0.35 · 0.25 / 0.15 | 1.25 · 1.43 · 1.67 |

這驗證了 v2 的 `V_safe` 觀念，並可寫成更簡潔的等價形式：

```
elapsed_frac = 1 − T_rem / WINDOW_MINUTES
pace_index   = utilization / max(ε, elapsed_frac)
  pace_index ≈ 1  → 正好照預算燃燒
  pace_index > 1  → 超前燃燒（會提前用完）
  pace_index < 1  → 落後（額度用不完）
```
`C(t) = clamp(floor(C_default / pace_index), C_min, C_cap(state))` 與 §4.2.2 的 `V_safe / V_eff` 形式數學上同源，但**不需要估計瞬時燃燒率**，因而完全免除冷啟動、EWMA 調參與視窗重置誤判的問題。**建議實作採用 `pace_index` 為主控訊號，`V_eff` 僅作為輔助診斷指標。**

**對 v2 預設值的兩點重要修正：**

1. **週額度必須用配速判準，不能用絕對水位。** v2 設 `WEEKLY_WARN_PERCENT=70` 太晚了 —— 依內建判準，週額度在流逝 15% 時利用率就不該超過 25%。若照 v2 的絕對水位治理，週三就可能燒到 70%，剩下四天全在 `LONG_HIBERNATE`。**改為配速門檻**：`WEEKLY_PACE_CEILING_THROTTLE=1.25`（超過即 `THROTTLING`）、`WEEKLY_PACE_CEILING_DRAIN=1.50`（併發壓到 1）。對應設定見 §6 第 4 節。
2. **5 小時視窗可以比 v2 更寬鬆。** 內建判準到 0.90/0.72 才示警，而 v2 在 70% 就開始節流。在**週額度配速健康**的前提下，`TOKEN_WARN_PERCENT` 可放寬到 80（並設 `FIVE_HOUR_PACE_CEILING=1.25`），把 5 小時視窗吃得更滿（反正它會重置）。真正需要嚴管的是週額度 —— 這與 v2 §4.2.5 的論證一致，現在有了實作證據。

> **注意**：上述內建數值取自 v2.1.232 的實作字串，屬**內部**啟發式，非公開契約。應作為「校準參考」而非硬編碼依賴；實作時放在設定檔中，並以 §15.7 的觀測資料再校準。

### 4.3 上下文壓縮策略（v1 邏輯錯誤，本節整體重寫）

**原則**：壓縮由 `K_ctx`（上下文佔用率）驅動，且必須在**額度尚有餘裕時**執行。

```
壓縮觸發條件（AND）：
  K_ctx ≥ CONTEXT_COMPACT_PERCENT (84)        # 單一 session 的上下文佔用
                                              # ↑ R92 修憲（v2.1.1）：75 → 84；同輪首次把 context 硬線 94% 入憲
                                              #   （實作層 HARD_RATIO 0.90 → 0.94，PRD 此前未定義硬線）。
                                              #   與額度尺 85/95 錯開以保鑑別力（R92 掌舵者裁決）。
                                              #   注意：機械 autocompact（PCT=90）的分母是 auto-compact window，
                                              #   官方未公開其與模型全窗的比例 ⇒「84 早於壓縮點」不可證，
                                              #   方向安全（至多提早壓縮），詳 ADR-XPLAT-008 §4。
  U5h + COMPACT_COST_BUDGET_PP ≤ DRAIN_PERCENT # 壓縮本身要燒額度，須先確認燒得起
  距上次壓縮 ≥ COMPACT_MIN_INTERVAL_SECONDS   # 防止反覆壓縮

若 K_ctx 已高但額度不足以支付壓縮成本：
  → 不壓縮，直接走 FREEZING 路徑
  → 理由：state.json 才是耐久記憶體，上下文不是。犧牲上下文、保留額度，
          是比「花掉最後 5% 額度做壓縮然後沒額度繼續」更好的選擇。
```

`COMPACT_COST_BUDGET_PP` 需以實測校準（壓縮一次的額度成本 ≈ 完整上下文的一次讀取 + 摘要輸出）。建議初值 3 個百分點，並在執行後回寫實測值做自適應。

> `[需核對]` (a) CLI 是否已內建自動壓縮及其觸發點；(b) 在非互動（headless）模式下能否由外部觸發壓縮；(c) 是否有 pre-compact 類的 hook 可讓 Daemon 在壓縮前先寫 checkpoint。若 (b) 不可行，本模組應改為「在 `K_ctx` 超標時主動結束該 Step 並以新 session 交棒」，而非嘗試遠端下達壓縮指令 —— v1 假設 Daemon 可任意觸發 `/compact`，此假設需驗證。

### 4.4 多 Agent 隔離與整合（v1 過於簡略）

#### 4.4.1 Worktree 建立（修正實務問題）

```bash
# v1: git worktree add .autoclaude/worktrees/agent-<ID> -b feature/agent-<ID>
#     問題：分支已存在時失敗；worktree 目錄在 repo 內未被忽略；無基準點鎖定

BASE_SHA=$(git rev-parse HEAD)                 # 明確鎖定基準，避免各 Agent 基準不一
BRANCH="autoclaude/agent-${AGENT_ID}-${RUN_ID}" # 含 RUN_ID 保證唯一
git worktree add -B "$BRANCH" \
  ".autoclaude/worktrees/agent-${AGENT_ID}" "$BASE_SHA"
```
- `.autoclaude/` 必須加入 `.gitignore`（且 `worktrees/` 不得被 Agent 的檔案掃描納入上下文，否則會重複讀入他人程式碼並浪費 token）。
- 啟動前檢查 `git worktree prune`，清理上次異常退出的殘留。
- 每個 Agent 的 CLI 實例必須以其 worktree 為工作目錄，並限制檔案寫入範圍在該目錄內。

#### 4.4.2 整合佇列（v1 的「Fast-Forward 合併」不可行）

多 Agent 並行時各分支必然分歧，FF 只在「無其他分支已合併」時成立。修正為序列化整合佇列：

```
對每個完成的 Agent 分支，Daemon 依序（單執行緒、持有整合鎖）執行：
  1. git fetch/更新 integration 分支
  2. git rebase integration <agent-branch>          # 衝突 → 標記 CONFLICT，交人工或重派
  3. 執行驗證閘門（lint / build / unit test）        # 失敗 → 退回佇列，不合併
  4. git merge --ff-only <agent-branch>            # rebase 後 FF 必然成立
  5. git worktree remove + 刪除分支
衝突策略：CONFLICT_POLICY = ABORT | RETRY_WITH_AGENT | HUMAN_REVIEW（預設 HUMAN_REVIEW）
```
**重要**：步驟 2 的衝突解決若交由 Agent 處理，會消耗額度 —— 必須納入配速預算，且在 `DRAINING` 以上狀態禁止啟動衝突解決任務。

#### 4.4.3 Agent 硬性預算（v1 缺漏）

`DRAINING` 狀態「允許進行中的 Step 收尾」是危險的開放式承諾：一個大型 Step 可能在收尾期間把 `U5h` 從 85% 推到 100%。必須有硬性上限：

```
每個 Step 啟動時設定：
  MAX_STEP_TURNS            (預設 40)      # CLI 的最大回合數旗標
  MAX_STEP_WALL_SECONDS     (預設 900)
  MAX_STEP_QUOTA_PP         (預設 5)       # 該 Step 允許推升的 U5h 百分點
DRAINING 狀態下上述值乘以 DRAIN_BUDGET_FACTOR (0.5)
超出任一上限 → 優雅終止（SIGINT → 等待 → SIGTERM → SIGKILL），
               並將該 Step 標記為 PARTIAL 寫入 state.json
```
> `[需核對]` 最大回合數旗標名稱、以及 headless 模式下訊號處理是否會正確落盤對話記錄。

### 4.5 狀態保全與喚醒（Lossless Resume）— 修正成本假設

#### 4.5.1 凍結流程

```
[U5h ≥ HALT] 
   │
   ├─► 1. 停止派工，向所有 Agent 發出優雅終止
   ├─► 2. 每個 worktree 各自 commit（不是只有一個！）
   │        git -C <wt> add -A
   │        git -C <wt> commit -m "autoclaude: checkpoint (pre-reset) [skip ci]"
   │        允許空提交失敗（無變更時跳過）
   ├─► 3. 收集每個 Agent 的 session_id / 分支 / SHA / 未完成檔案
   ├─► 4. 原子寫入 state.json（tmp → fsync → rename）
   ├─► 5. 驗證：重新讀取並校驗 schema + checksum
   ├─► 6. 釋放 Agent 行程，啟動防休眠（僅在需等待 < MAX_INPROCESS_WAIT 時）
   └─► 7. 狀態 → WAITING_RESET 或 LONG_HIBERNATE
```
**所有凍結動作皆為零 Token 操作**（git、檔案 I/O），可安全在 95% 執行。這是把壓縮移出此路徑的另一個理由。

#### 4.5.2 休眠等待（修正 v1 的單次長 sleep）

```
target_wall = reset_timestamp + RESET_BUFFER_SECONDS
while True:
    remaining = target_wall − now_wall()
    if remaining <= 0: break
    sleep(min(remaining, SLEEP_SLICE_SECONDS))       # 分片，預設 30s
    # 偵測系統睡眠／NTP 跳躍：monotonic 與 wall clock 增量差 > CLOCK_JUMP_TOLERANCE (120s)
    if clock_jump_detected(): re-poll telemetry, 重算 target_wall
    if received_signal(): 優雅退出（state.json 已落盤，可安全重啟）
```
理由：單次 `sleep(5h)` 無法回應訊號、無法修正時鐘漂移、機器睡著後醒來會嚴重超時或早醒。

#### 4.5.3 重置驗證與喚醒

```
1. 重新輪詢遙測，確認 U5h 已顯著下降（< RESET_CONFIRM_PERCENT，預設 10）
2. 未確認 → 以 full-jitter 退避重試（30s 起，上限 300s，最多 10 次），
            仍失敗 → 回到 WAITING_RESET 並延長等待（後端重置漂移）
3. 確認後 → 依 RESUME_STRATEGY 喚醒（見 4.5.4）
4. 以 C=1 起步，成功接手後才交還配速控制器（避免喚醒瞬間齊發撞牆）
```

#### 4.5.4 喚醒策略 — v1 的成本盲點

> **v1 的核心誤解**：「同一 Session 續接 = 不重複消耗 Token」。實際上，續接一段長對話時，模型必須重新讀入完整歷史；提示快取（prompt cache）的存活時間遠短於 5 小時，休眠後必然是**快取未命中**，因此喚醒的第一個請求會產生**全額輸入 token 費用**。對話越長，喚醒越貴 —— 而喚醒的時機正好是額度剛重置、最該省著用的時候。

因此提供三種策略：

| 策略 | 做法 | 喚醒成本 | 上下文保真度 | 適用 |
| :---- | :---- | :---- | :---- | :---- |
| `SESSION_RESUME` | 續接原 session | 高（≈ 完整歷史一次重讀） | 最高 | 對話短、任務高度依賴細節脈絡 |
| `FRESH_SESSION_WITH_STATE` | 新 session，開場給 state.json + 必要檔案清單 | 低（僅摘要 + 少量檔案） | 中（依賴 state.json 品質） | 對話長、步驟邊界清楚 |
| `AUTO`（**預設**） | 依對話規模自動選擇 | — | — | 一般情況 |

```
AUTO 判準：
  估計對話 token 數 ≤ RESUME_MAX_TRANSCRIPT_TOKENS (60000)  → SESSION_RESUME
  否則 → FRESH_SESSION_WITH_STATE
另：若 U7d 已高於 weekly_warn，一律採 FRESH_SESSION_WITH_STATE（省額度優先）
```

喚醒指令（**移除 v1 的 `--dangerously-skip-permissions` 預設**）：

```bash
# 建議形式（旗標與權限模式名稱 [需核對]）
claude --resume "<SESSION_ID>" \
       --permission-mode acceptEdits \
       --allowed-tools "Read,Edit,Write,Bash(npm test:*),Bash(git status)" \
       --max-turns 40 \
       -p "額度已重置。請讀取 .autoclaude/state.json，從 interrupted_step 繼續執行；
           先確認工作區狀態與測試結果，再繼續未完成項目。"
```
安全說明見 §13。**只有**在容器／VM 等隔離環境且使用者明確設定 `ALLOW_PERMISSION_BYPASS=true` 時，才可使用完全跳過權限的旗標。

#### 4.5.5 長休眠（`LONG_HIBERNATE`）— v1 完全缺漏

週上限觸發時等待期可達 7 天，不能用 in-process sleep 或防休眠硬撐（電力／穩定性／使用者體驗皆不可接受）：

```
若 T_rem_7d > MAX_INPROCESS_WAIT_SECONDS (預設 7200):
  1. 完成凍結流程（state.json 落盤）
  2. 向 OS 排程器註冊一次性喚醒任務：
       macOS   : launchd plist (StartCalendarInterval) 
       Windows : schtasks /create /sc once /st <time>
       Linux   : systemd-run --on-calendar / systemd timer
  3. 釋放防休眠，Daemon 退出（狀態完全在磁碟上）
  4. 排程時間到 → Daemon 重啟 → INIT 掃描 state.json → 驗證額度 → RESUMING
若 weekly_reset_timestamp 不可得：
  → 保守推估（依帳號起算日或最近觀測到的重置點），並在到期前每 30 分鐘輪詢一次確認
```

#### 4.5.6 撞線喚醒閉環的覆蓋面與失效紀律（v2.1.5 新增；立案證據＝2026-08-16/17 事件）

**立案事實（證據鏈全文見 ADR-XPLAT-004 §2.9）**：2026-08-16 深夜，喚醒機制的每一環能力都已存在
（撞線偵測判準 D、`sentinel_decide` 四分支、launchd `StartCalendarInterval`、`choose_resume_route`
三態選路），哨兵當晚亦已武裝並成功巡邏十次；但 00:42 額度 halt 動作把「可重啟點任務書」整檔覆寫成
不含機器可讀狀態塊的骨架，00:51 subagent 撞線（逐字「You've hit your session limit · resets 3:50am
(Asia/Taipei)」）落入主逐字稿、主 session 自己的回合同時死於 API 層，00:55 哨兵因「狀態塊讀不出來」
**靜默自我解除**，03:50 reset 時機器上零排程，空轉至次日人工介入。⇒ 失效的不是任何單環能力，
而是機制間的**互相摧毀**與失效時的**靜默**。故本節立以下需求（均為規範性要求）：

**R-4.5.6-1（覆蓋面）** 撞線偵測與喚醒續跑必須覆蓋三個執行層級：主 session API 回合、Task subagent、
workflow agent。判準以逐字稿合成權威記錄（`type=assistant` ＋ `model=<synthetic>`）為形狀、以
「事件之後全域有無成功 API 回應」為已處理證據（即現行判準 D），掃描面必含主逐字稿與其
`subagents/` 整棵子樹。

**R-4.5.6-2（主 session 活著但帳號級撞線）** 此情境下該回合死於 API 層、hook 體系零觸發點
（PreToolUse／PostToolUse 皆不會被叫到，session 事後也發不出任何工具呼叫）⇒ 逐字稿巡邏哨兵是
**唯一**事中機械物。因此哨兵自身的可用性即本情境的全部可用性：哨兵任何 fail-quiet 形態
（含自我解除、痕跡不分形、stderr 無人收）都等同本情境整格失效，一律按 P0 處理。

**R-4.5.6-3（單檔雙寫者禁令）** 任何寫入「可重啟點任務書」的路徑（骨架產生、prepare/halt 帶動作、
武裝、重排）**不得**摧毀該檔既有的機器可讀狀態塊（RELAY 塊）。驗收（機械）：對已含狀態塊的任務書
執行骨架重寫後，`parse_relay()` 非 None 且既有 state 逐格保留；此判準必須有紅面（在修正落地前的
實作上必紅）。

**R-4.5.6-4（失效必出聲、先自癒後解除）** 哨兵讀不出狀態塊時：(a) 必須先嘗試以呼叫端引數與任務書
檔名重建最小狀態塊並續巡（自癒）；(b) 重建不能才允許解除，且解除必經桌面級告警
（`escalation.alert(loud=True)` 等級，不得只印 stderr）；(c) 「檔不存在／無狀態塊／JSON 壞掉」三種
失效與「正常下班」的痕跡必須分形可稽核。

**R-4.5.6-5（halt 武裝的多軸裁決）** halt 閂鎖的喚醒武裝分支不得只看 binding 單軸：當 binding 軸無
reset（extra_usage／spend）但存在其他 ≥halt 且有 reset 的軸時，必須以「最早可 reset 軸」武裝喚醒；
僅當全軸皆無 reset 才允許 escalate-only。（立案反例：本事件 binding=extra_usage@None ⇒ escalate-only
未武裝，而 five_hour 軸 03:50 reset 後工作實際可續。）

**R-4.5.6-6（憑證紀律）** 「已武裝」宣稱一律附排程器自報憑證：Windows＝`NextRunTime` 非空值；
macOS＝`launchctl print gui/<uid>/<label>` 的 rc（不存在＝113）＋ plist 路徑回讀（launchd 不提供
NextRunTime，rc 才是憑證）。無憑證即不得宣稱，違者按 §15.5 紅線「排程也是一種 PASS 聲稱」處理。

**驗收判準（全部可機械查證）**：

| # | 判準 | 查證方式 |
| :---- | :---- | :---- |
| A1 | 含狀態塊的任務書經任何骨架重寫路徑後狀態塊存活 | 單元測試（紅綠自證，R-4.5.6-3） |
| A2 | 哨兵於「狀態塊缺席×逐字稿存在」輸入下不得 unregister，且告警注入點被呼叫 | 單元測試（R-4.5.6-4） |
| A3 | binding 無 reset ＋他軸有 reset ⇒ halt 分支回 arm；全軸無 reset ⇒ escalate | 單元測試（R-4.5.6-5） |
| A4 | 本事件重演劇本（撞線記錄落逐字稿 → 下一巡）產出 `arm_reset` 且武裝憑證非空 | 整合測試以真實逐字稿片段注入（R-4.5.6-1/2/6） |
| A5 | 巡邏／武裝／自癒／解除各步在痕跡檔留下**互異**事件名 | 痕跡 jsonl 斷言（R-4.5.6-4c） |

#### 4.5.7 主控閒置盲區與預防性水位提醒（v2.1.6 新增；掌舵者定級 P0「會破產的嚴重 BUG」，
立案＝`DEF-200-148`，2026-08-16/17 收尾包＋修復包兩次實證）

**立案事實**：08-16 收尾包與 08-17 修復包各撞線一次，兩次皆為「subagent 背景耗至 session 38%
期間主控零喚醒」——§4.5.6 修好的是「哨兵撞線後怎麼正確武裝續跑」，本節修的是**更早一步**：
撞線那一刻**之前**，主控完全不知道水位已逼近，而撞線那一刻**通知能不能送達**也未受保障。三個
結構洞（均為規範性要求）：

**R-4.5.7-1（主控閒置盲區）** `.claude/hooks/context_budget_guard.py` 的水位量測只掛在
PostToolUse／PreToolUse（見根 CLAUDE.md〈機械守衛總表〉），主控在等待 subagent 回覆期間**零工具
呼叫** ⇒ 該窗口內水位機制結構上不會被觸發。修法：既有哨兵巡邏（`tools/session_resume_planner.py
--arm-sentinel` 武裝的 schtasks／launchd 排程，`tools/lib/sentinel_lifecycle.py` 為巡邏邏輯本體）
於每次巡邏時，除既有「逐字稿有沒有撞線」判準外，**新增**一項：讀主逐字稿最後一筆
`type=assistant`／`type=tool_use` 事件的時間戳，與巡邏當下時刻相減；超過閒置門檻
（建議與巡邏間隔同量級，現查 `tools/lib/quota_policy.py --print-env-example`，不寫死於本 PRD）
且該 session 仍為 active（無 `Stop` 事件）時，判定為「主控閒置中」，進入 R-4.5.7-2 的水位查核。

**R-4.5.7-2（預防性水位提醒）** 現行 `sentinel_decide()` 四分支只認「逐字稿已出現撞線字樣」
（見 §4.5.6 R-4.5.6-2），對「水位正在逼近但尚未撞線」零觀測。修法：哨兵巡邏（含 R-4.5.7-1 判定
為閒置的巡邏）額外讀一次額度快取（`tools/lib/quota_meter.py` 既有讀法，同 `--pace` 的資料源），
若任一節流軸進入 prepare 帶（85~95%，門檻沿用 `tools/lib/quota_policy.py` 既有三段式定義，見根
CLAUDE.md〈三段式水位〉）且尚未進入 halt，發出一則「即將撞線」的預防性提醒（走 R-4.5.7-3 的通知
通道），**不**觸發 §4.5.6 的重啟任務書骨架寫入——任務書骨架仍只在真正撞線（halt）時產生，避免
提醒與重啟兩種語意的任務書互相覆寫（同 R-4.5.6-3 單檔雙寫者禁令的精神）。

**R-4.5.7-3（通知到達保障）** R-4.5.6-2 已指出「主 session 活著但帳號級撞線」時 hook 體系零觸發
點；本節補上通知**送達**面的保障——撞線與 R-4.5.7-2 預防性提醒兩種通知，一律走**不消耗額度**
的通道（桌面通知 `escalation.alert(loud=True)`／Windows Toast／macOS 通知中心，既有機制見
`autoclaude/utils/notifier.py`），不得只依賴「寫回逐字稿等主控下次工具呼叫時讀到」——若主控自己
也同時在額度限制內，它可能永遠不會有下一次工具呼叫去讀那則訊息。桌面通知不佔用 API 額度，故此
通道在「主控與哨兵同時撞線」的最壞情境下仍然成立。

**驗收判準（全部可機械查證）**：

| # | 判準 | 查證方式 | 狀態 |
| :---- | :---- | :---- | :---- |
| B1 | 巡邏讀出主逐字稿最後事件時間戳並算出閒置秒數 | 單元測試（合成逐字稿注入不同時間戳）：`tools/tests/test_context_budget_guard.py::ControllerIdlePrepareWatchTest`（`test_b1_*` 三支） | 已實作 |
| B2 | 閒置且水位進入 prepare 帶時發出預防性提醒、且不寫任務書骨架 | 單元測試（紅綠自證：R-4.5.7-2 分支開關）：同上類別 `test_b2_*` 三支 | 已實作 |
| B3 | 預防性提醒與撞線提醒皆走桌面通知通道，且不依賴主控下一次工具呼叫 | 整合測試（mock 通知器，斷言呼叫發生於巡邏行程而非 hook 行程）：`tools/tests/test_context_budget_guard.py::PatrolNoticeIsDesktopNotHookTest` | 已實作 |

**🔴 施工狀態（誠實記載，不得曖昧）**：本節（v2.1.6）已完整實作，不再是規格化階段。三條
R-4.5.7-x 的機制本體落在 `tools/lib/quota_escalation.py`（`_main_transcript_idle_seconds()` /
`_idle_prepare_watch()` / `patrol_housekeeping()`），由 `tools/session_resume_planner.py` 的
`_sentinel_tick()` 於每次巡邏 tick 呼叫；桌面通知走既有的 `quota_escalation.notify()`
（Windows Toast／macOS 通知中心／`notify-send`，`AUTOSDD_DESKTOP_NOTIFY` 預設關閉的既有非模態
管道）。B1~B3 三支測試（外加 `test_b1_a_tool_use_record_also_counts_as_activity` 等變體）全數
綠燈，回歸鎖見上表。

🔴 **對規格文字的兩處刻意偏離（誠實記載，非疏漏）**：

1. 本節原文把 R-4.5.7-1 的落點寫在 `tools/lib/sentinel_lifecycle.py`；實作時發現該檔在
   `guardrail_lib` tier（400 行）下**僅剩 3 行餘裕**（`python AutoClaude/tools/check_loc_budget.py
   --json` 現查），塞不下完整的逐字稿掃描邏輯，遂改落地在同層、餘裕充裕的
   `tools/lib/quota_escalation.py`（該檔既有「續航協定的兩件事：叫人與扇出續跑清單」定位，
   §4.5.8 的漂移自癒也落在這裡，屬同一主題的自然延伸）。`tools/lib/sentinel_lifecycle.py`
   保留一支 3 行的 `armed_but_missing()` 純判準（供 §4.5.8 呼叫），用滿其僅剩的餘裕；
   `tools/session_resume_planner.py`（`guardrail_cli` tier 750/750、零餘裕）淨改動為 0 行——
   巡邏 tick 的既有呼叫點 `snapshot_fanout(transcript, event)` 換成 `patrol_housekeeping(
   transcript, event, now, state, idle_threshold, tick, log)`，同一物理行、未新增任何一行。
2. 本節原文（R-4.5.7-3）把桌面通道寫成 `escalation.alert(loud=True)`／既有機制見
   `autoclaude/utils/notifier.py`；實作改走 `quota_escalation.notify()`（同一支檔既有的
   Windows Toast／macOS `osascript`／`notify-send` 三態非模態通道，`AUTOSDD_DESKTOP_NOTIFY`
   預設關閉）。理由：`autoclaude/utils/notifier.py` 住在 `AutoClaude/` 子專案，其套件現查
   **未安裝於根層 `.venv`**（`Test-Path .venv/Lib/site-packages/autoclaude` 為 `False`），
   而 `tools/session_resume_planner.py`／`tools/lib/*` 一律跑在根層 `.venv` 下；跨子專案
   import 會在這台機器上直接 `ImportError`。`quota_escalation.notify()` 已是同一份程式碼、
   同一份「不消耗額度」承諾下的既有機制（R-4.5.6-4b 的桌面告警走的正是它），選它是沿用
   既有的家，不是發明第二份通知知識。`escalation.alert()` 本身仍保留給撞線／終態叫人用
   （見 §4.5.6），本節的預防性提醒刻意走更輕量的 `notify()`，因為它不需要 `alert()` 附帶的
   寫紙／扇出清單那些終態語意。

#### 4.5.8 哨兵武裝狀態漂移自癒（v2.1.7 新增）

**立案事實**：§4.5.6 R-4.5.6-6 已要求「已武裝」宣稱必須附排程器自報憑證，而 §4.5.6 修好的是
「武裝那一刻要有憑證」；本節修的是**武裝之後**——排程器裡的哨兵工作可能因系統重開機、
Windows 工作排程器的到期清理、或其他外部因素而在武裝之後**憑空消失**，本機的 armed stamp
標記檔卻不會跟著更新，於是「宣稱已武裝」與「排程器現查實況」之間出現漂移。立案證據＝本輪
現查 `python tools/session_resume_planner.py --pace` 時工具自己印出的警語：「🔴 哨兵活性：
armed stamp 說 `AutoSDD_Sentinel_<session>` 已武裝，排程器現查卻沒有這支工作 ⇒ 哨兵已死、
喚醒鏈斷線」——`sentinel_lifecycle.liveness_line()`（R95／ADR-XPLAT-004 §2.9 修3 的既有機制）
此前只在人手動執行 `--pace`／`--check` 時**出聲**，且只印警語、**不動作**，要求人手動重跑
`--arm-sentinel` 才能恢復，不符合「不需要人類介入」的自動化閉環要求（R-4.5.6-2 已定調：哨兵
自身的可用性即帳號級撞線情境的全部可用性，任何 fail-quiet 形態一律按 P0 處理——「武裝了卻
沒人發現已經死掉」正是這個形態的一種）。

**R-4.5.8-1（每次巡邏自我健檢）** 哨兵巡邏邏輯（`_sentinel_tick()`）於每次巡邏時，除既有
判準外，新增一項核對：比對「本機 armed stamp 宣稱的武裝狀態」（`sentinel_lifecycle.
arm_marker_path()`／狀態塊 `task_name`）與「排程器現查的實際狀態」（`sentinel_lifecycle.
sentinel_task_names()`——Windows 走 `Get-ScheduledTask`、macOS 走 `launchctl list`，同
R-4.5.6-6 的既有憑證判準）。純判準 `armed_but_missing(task, jobs)`：`jobs is None`（量不到）
與 `jobs` 不含 `task`（真漂移）必須分得開——量不到不得誤判成漂移（同本 repo 通篇「量不到 ≠
量到零」的紀律），只有後者才進入 R-4.5.8-2 的自癒動作。

**R-4.5.8-2（偵測到漂移即自動重新武裝）** 真的漂移時，直接呼叫既有的排程器介面
（`schedule_backend.select().arm(...)`，與 `--arm-sentinel`／`register_endurance()` 底層共用
同一支後端方法，不重新發明武裝流程）就地重新武裝，武裝的下次喚醒時刻沿用巡邏間隔
（`SENTINEL_INTERVAL_SECONDS`，同一般巡邏重排的既有邏輯）。已達終態（`state` 屬於
`sentinel_lifecycle.TERMINAL_STATES`）的哨兵不觸發自癒——那是正常下班，不是漂移。

**R-4.5.8-3（痕跡可分辨）** 自癒動作在稽核痕跡檔留一筆**與既有『巡邏／武裝／自癒（RELAY
版，R-4.5.6-4）／解除』互異**的事件名（`sentinel_armed_drift_healed`），比照 R-4.5.6-4c
的紀律：不同失效形態要能從痕跡分辨出來，不能只靠 `sentinel_decided` 多幾個稽核欄位（那一行
每次巡邏都會印，欄位增減不足以讓「這次巡邏發生過漂移」在痕跡上一眼可辨）。自癒失敗（例如
排程器本身不可用、`arm()` 回非零 rc）記在同一事件的 `armed_drift_healed=False` 欄位裡，
本節**不**額外定義一條「自癒失敗才升級叫人」的路徑——排程器完全不可用時，該情境已由
R-4.5.6-4b 的桌面級告警機制涵蓋（讀不出狀態塊、自癒不了才會走到那一層）。

**🔴 誠實劃界（結構性限制，不是待修 bug）**：本檢查依附在巡邏 tick 本身執行——若排程器裡的
哨兵工作被整條刪除、且**再也不會觸發下一次 tick**，本機制沒有任何辦法把它救回來（沒有事件源
可以叫醒一支已經不存在的排程，同鐵律六「任何停等都必須有一個會主動叫醒我的事件源」的反面：
一支已死的排程本身就不再是事件源）。它能治的是「工作還在（tick 因此被叫起），但 armed stamp
與現查不一致」這一類**可觀測**的漂移；真正「整條排程消失且永不再觸發」的最壞情境，仍要靠人
或 AutoClaude 在下一次主動介入時（例如手動 `--pace`）才會被發現——本節把「發現後怎麼辦」從
「要求人手動重跑 `--arm-sentinel`」降級為「大多數漂移情境下不需要人介入」，而不是宣稱涵蓋
排程器徹底消失且 tick 永不再被觸發的那個子情境（宣稱涵蓋會是一句結構上不成立的話，比沒有
這個功能更糟，同 `snapshot_fanout()` 對 `resumeFromRunId` 同 session only 那條既有紀律）。

**驗收判準（全部可機械查證）**：

| # | 判準 | 查證方式 | 狀態 |
| :---- | :---- | :---- | :---- |
| C1 | armed stamp 存在且排程器現查確定不含該工作 ⇒ 自動重新武裝 | 單元測試（mock 排程器查詢結果）：`tools/tests/test_context_budget_guard.py::ArmedDriftSelfHealTest::test_armed_stamp_present_but_scheduler_shows_missing_self_heals` | 已實作 |
| C2 | 排程器現查確實還在 ⇒ 不觸發自癒（控制組） | 同上類別 `test_when_the_scheduler_still_shows_the_task_nothing_is_re_armed` | 已實作 |
| C3 | 排程器量不到（`None`）不得誤判成漂移 | 同上類別 `test_unmeasurable_scheduler_listing_is_not_mistaken_for_drift` | 已實作 |
| C4 | 自癒動作留下與既有事件名互異的痕跡 | 同 C1 測試方法內斷言 `sentinel_armed_drift_healed` 事件與既有家族不撞名 | 已實作 |

**🔴 施工狀態**：已實作。純判準 `armed_but_missing()` 落在 `tools/lib/sentinel_lifecycle.py`；
自癒動作本體（`_heal_armed_drift()`）與痕跡寫入（`_append_trace()`）落在
`tools/lib/quota_escalation.py`，由同檔的 `patrol_housekeeping()` 於每次巡邏 tick 呼叫（接線
方式同 §4.5.7）。C1~C4 四支驗收判準全數綠燈，回歸鎖見上表。

#### 4.5.9 髒污工作樹的存檔救援序列（v2.1.8 修憲；標的＝§8-8）

**原條文（§8-8）**：`Worktree 有未提交變更且無法提交` ⇒ 依序嘗試
`commit --no-verify` → `git stash` → 產生 patch 檔存入 checkpoints 目錄；三者皆失敗 →
標記 `DIRTY_UNSAVED`。

**衝突事實**：前兩步被本 repo 憲法**直接禁止**，不是「不建議」：

| 原步驟 | 禁令出處（逐字可查） | 為什麼禁令是對的（不是形式主義） |
| :---- | :---- | :---- |
| `commit --no-verify` | 根 CLAUDE.md〈可重啟點四條件〉第 3 條把 `--no-verify` 逐字列為任務書必寫的**禁止事項** | pre-commit 閘門是「這份變更還沒過品質閘」的**唯一**告知管道；繞過它會把半套工作寫成一個外觀已驗證的 commit，而下一輪讀者無從分辨 |
| `git stash` | 鐵律五 PreToolUse 機械阻斷 stash **全族**（裸 `stash`＝push／`push`／`pop`／`apply`／`drop`／`clear`／`save`），機械物＝`.claude/hooks/block_destructive_git.py` | 立案＝多包並行**共用工作樹**上的真實事故。`stash` 會把變更從工作樹**移走**——對一個無人看管的凍結流程，那正是最壞的失敗形態：變更消失且沒有人知道 |

> 🔴 **不得用「`git stash create` 是放行的」來繞過**：那一支放行是因為它**不動工作樹**
> （產出一個 dangling commit 物件），本就是〈可重啟點四條件〉第 1 條指定的**互動情境**
> 保全手法（且必須配 `git tag` 才有 ref 指著它、否則 `gc` 可回收）。它不是本節要的東西：
> 本節要的是「**存檔了沒**」這個問題可以靠讀一個檔回答，而 object database 裡的
> dangling commit 回答不了它。

**裁決（理想版）：救援序列只有一個動作（產生 patch，不動工作樹），但它的母體有兩段
（tracked 變更 ∪ untracked 新檔——v2.1.9 補上後者）；第三步升級為「寫完必須讀回來驗」。**

**R-4.5.9-1（單步救援，且不得改動工作樹）** 救援序列＝把**兩段**輸出依序落盤成**同一份**
patch 檔（順序是規範性的：① 在前，② 在後）：

```
① tracked 變更（相對 R-4.5.9-2 記錄的那個 HEAD）：
     git -C <wt> diff HEAD --binary --no-color
② untracked 新檔（逐檔，NUL 分隔以承受含空白／非 ASCII 的檔名）：
     git -C <wt> ls-files --others --exclude-standard -z
       ⇒ 對每一個 <path>：
     git -C <wt> diff --no-index --binary --no-color -- /dev/null <path>
```

序列中**不得**出現任何會改動工作樹或索引的 git 動詞（`add`／`commit`／`stash`
（`create` 除外）／`checkout`／`restore`／`reset --hard|--merge|--keep`／`clean`／
`switch -f`），也**不得**出現 `--no-verify`。救援跑完後 `git -C <wt> status --porcelain`
必須逐字不變。

🔴 **② 是 v2.1.9 補上的缺口，不是原設計的一部分。缺它會產生「四道斷言全綠、而全新工作被
靜默丟掉」**——本輪否決權複審立案，當回合以合成 worktree 實測逐字：

| 步驟 | 實測輸出（逐字） |
| :---- | :---- |
| 工作樹狀態 | `git status --porcelain` ⇒ ` M tracked.txt` ／ `?? brand_new.py` |
| 只跑 ① | `patch bytes = 135`（非空）；`grep -c 'brand_new' rescue.patch` ⇒ **`0`**（`grep rc=1`） |
| 四道斷言 | (a) SHA-256 相等 ✅　(b) 位元組數相等 ✅　(c) `n_written > 0` ✅　第二道語意閘 ✅ |
| ⇒ 結論 | **「已驗證存檔成功」與「`brand_new.py` 被靜默丟掉」外觀完全相同** |
| 補上 ② | patch `1283`→（排除自我遞迴後）覆蓋兩者，`grep -c 'brand_new'` ⇒ **`4`**，且 `status --porcelain` 前後字串**相等** |

`git diff HEAD` 的射程**結構上**只有 index 與 HEAD 認識的路徑；untracked 正是 index 不認識
的那一半 ⇒ 這不是參數調得不對，是**母體少了一半**。而「全新的檔」恰好是最貴的那一半：
tracked 變更在 HEAD 裡至少還留著一個祖先版本，untracked 新檔一丟就是歸零。

🔴 **為什麼修法不是「把 `add` 從禁用動詞裡放出來」**（原禁令的理由要先讀懂，再談新修法）：
`git add` 改動**索引**，`git status --porcelain` 的第一欄會從 `??` 變成 `A ` ⇒ 直接違反本條
最後一句。禁令守的不是「別寫 add 這三個字」，是**救援不得改變下一個讀者看到的工作樹狀態**
——一個無人看管的凍結流程把檔案 stage 起來就走，下一輪的人會看到一棵「有人動過但沒說為
什麼」的樹，而 pre-commit 閘門對已 stage 與未 stage 的內容行為並不相同。
`git diff --no-index` 把兩個路徑當**檔案系統上的兩份檔**比：一個 git 物件都不寫、索引一個
位元組都不動 ⇒ 同時滿足「覆蓋 untracked」與「工作樹逐字不變」兩個約束。
同理 `git stash create -u` 仍被明文擋掉，理由是**兩個**而非一個：`-u` 那一支**會**把
untracked 檔從工作樹移走（那正是 `stash` 全族被機械阻斷的立案理由本身），且它的產物住
object database ⇒ 回答不了本節唯一要能回答的那個問題「存檔了沒，可以靠讀一個檔知道嗎」。

🔴 **② 的自我遞迴必須被排除，而排除它的東西是既有不變式、不是新規則**：patch 檔落在
`AUTOCLAUDE_CHECKPOINT_DIR`（出廠 `.autoclaude/checkpoints`，位置在 repo 內）⇒ 若
`.autoclaude/` 不在 `.gitignore`，它自己會被 ② 列舉到（把自己抄進自己），且
`status --porcelain` 會多一行而違反本條。§6.1 不變式 9 已逐字要求「`.autoclaude/` 已在
`.gitignore`」，`--exclude-standard` 於是結構上跳過它。當回合兩種姿態各實測一次：
**未** ignore ⇒ `status verbatim unchanged? NO` 且 patch 內含自己（`1283` bytes，含
`rescue.patch`／`rescue2.patch` 兩段自我抄錄）；**已** ignore ⇒
`status verbatim unchanged? YES`、`grep -c 'dirty.patch'` 自身檔名為 **`0`**。
⇒ **規範性要求**：本條的整合測試必須把「`.autoclaude/`（或當次 `AUTOCLAUDE_CHECKPOINT_DIR`
的頂層目錄）落在 `--exclude-standard` 的排除面內」當**前置斷言顯式驗一次**，不得只依賴
§6.1 在別處驗過——那條不變式若失效，本條的失效形態是靜默的（patch 照樣非空、斷言照樣全綠）。

**R-4.5.9-2（落地路徑與檔名）** patch 檔落在 `AUTOCLAUDE_CHECKPOINT_DIR`（§6 出廠值
`.autoclaude/checkpoints`），檔名 `dirty-<agent_id>-<offset-aware ISO8601 basic>-<short_sha>.patch`，
同目錄再寫一份同名 `.sha256` 側檔。

🔴 **`short_sha` 是哪一個 commit：`git -C <wt> rev-parse --short HEAD`，且必須在跑 ①
之前取、之後不再重取**（v2.1.9 寫死；此前規格未指名，而它決定第二道閘的成敗）。

- **為什麼必須是那一個**：① 產出的 hunk 是**相對該 HEAD** 的 diff。第二道語意閘問的正是
  「這份 patch 套不套得回它宣稱的基準」⇒ 基準寫錯，閘門測的就是另一個問題。當回合實測：
  同一份 patch 對正確 HEAD 的臨時索引 `apply --check --cached` ⇒ **rc=0**；救援後多做一個
  commit 讓 HEAD 前進一格再測同一份 patch ⇒ **rc=1**（逐字 `error: patch failed: staged.txt:1`／
  `error: tracked.txt: patch does not apply`）。
- **不是 integration 分支的 SHA**：救援發生在 agent 自己的 worktree，`integration` 可能早已
  前進；用它命名會讓檔名指向一個這份 patch 從來沒有對齊過的基準。
- **HEAD 在救援之後會動**（§6.2 R-6.2-1 的重排、§4.4.2 的 `--ff-only` 併入都會動它）⇒
  檔名裡那個值是**寫入當下的事實快照**，這正是它有價值的原因：人在下一輪拿到這份 patch
  時，唯一能靠它回答「該對著哪一棵樹套」的東西就是檔名裡的那七個字元。
- **同一個值必須同時進 state.json**（R-4.5.9-4 的四個可重驗值旁），理由是檔名可能被人重
  命名而 state.json 不會 ⇒ 兩處相等本身就是一道可查的斷言。

- **為什麼沿用 checkpoint 目錄**：§6 設定區塊 12 已把它定義為狀態持久化的家，§10 升級程序
  也已把備份寫在那裡 ⇒ 沿用既有的家，不新開一層。
- **為什麼帶時間戳、不覆寫**：救援可能連續發生（同一個 worktree 在兩次 reset 視窗各髒一
  次），覆寫等於把上一次救援**靜默**丟掉。
- **時間戳必須帶 offset**：鐵律三已有機械物 `tools/tests/test_platform_neutral_paths.py::
  TestNaiveLocalTimestampsAreNotPersisted`——naive 本地時間戳跨 DST 相減完全靜默。
- **不覆寫也是繞開一個平台事實**：`os.replace` 在 Windows 上覆寫「被別人開著」的目的檔
  會 WinError 5（鐵律三該列機械物＝`TestDirEntryPrimitivesAreAccountedFor`）。

**R-4.5.9-3（checksum 演算法＝SHA-256，且驗證必須是「重新開檔讀回」）**

- **演算法選 SHA-256**：§7 的 `checksum_sha256` 已是本文件既有的完整性欄位；同一份規格裡
  不該有第二種完整性演算法（讀者要判「這個 checksum 是什麼」就得猜）。`hashlib` 內建、
  跨平台一致，且對「寫一半」與「寫壞」兩種形態同樣敏感。
- **為什麼不用檔案大小**：磁碟滿的典型形態是最後一個 block 寫不進去；patch 恰好在 block
  邊界結束時，大小看起來是對的。
- **為什麼語意閘不能取代它（但要當第二道）**：語意閘驗的是「這個 patch 套不套得回它宣稱
  的基準」——那是另一個問題，而完整性是寫入當下就該定案的性質。兩者不互相取代：SHA-256
  是第一道（磁碟完整性），語意閘是第二道（語意可用性），**兩道都必須過**才算救援成功。
- 🔴 **第二道閘的形態必須寫死，因為天真寫法「`git -C <wt> apply --check <patch>`」在本節
  唯一會被跑到的情境下結構上恆紅**（v2.1.9 訂正；當回合實測）。救援發生時工作樹**定義上
  是髒的**——那些變更已經在樹上，再套一次當然衝突。實測逐字：

  | 形態 | index == HEAD | 有 staged 變更（index ≠ HEAD） | 判決 |
  | :---- | :---- | :---- | :---- |
  | 在髒工作樹上 `apply --check <p>` | **rc=1**（`error: brand_new.py: already exists in working directory`） | **rc=1** | ❌ 結構上恆紅，無鑑別力 |
  | `apply --check --cached <p>`（吃真索引） | rc=0 | **rc=1**（`error: patch failed: staged.txt:1`） | ❌ ① 是對 HEAD 的 diff，不是對索引 |
  | `apply --check --cached --3way <p>` | rc=0 | rc=0（逐字 `Applied patch to 'staged.txt' cleanly.`） | ❌ **禁用**：`--3way` 會把「套不上」fuzz 成綠 |
  | **臨時索引 read-tree 到記錄的 HEAD，再 `--check --cached`** | rc=0 | **rc=0** | ✅ 唯一形態 |

  ⇒ **規範性形態**（`<idx>` 為 checkpoint 目錄下的臨時索引檔，用完刪除）：

```
GIT_INDEX_FILE=<idx> git -C <wt> read-tree <R-4.5.9-2 記錄的 short_sha>
GIT_INDEX_FILE=<idx> git -C <wt> apply --check --cached <patch>
```

  - **它為什麼不動工作樹**：`--check` 從不寫入；`--cached` 只碰索引，而 `GIT_INDEX_FILE`
    把「索引」換成一個一次性檔案 ⇒ 真索引與工作樹皆零改動。當回合實測：跑完後
    `real status verbatim unchanged? YES`，且真索引裡原本 staged 的檔仍 staged
    （`git diff --cached --name-only` ⇒ `staged.txt`）。
  - 🔴 **判準是 `rc == 0`，不是「`rc == 1` 才算失敗」**：截半的 patch（磁碟滿的典型形態）
    實測回 **rc=128**（`error: patch with only garbage at line 10`）。寫成 `rc == 1` 的實作
    會把 128 當成通過。
  - **誠實劃界（這一道的盲區，也是 SHA-256 必須留在第一道的理由）**：new-file hunk 不需要
    context 就能套 ⇒ 只損壞 untracked 那一段的內容時本閘實測回 **rc=0**。它守得住的是
    tracked context 損壞（實測 rc=1）與基準錯（實測 rc=1）。

- **驗證程序（順序是規範性的）**：

```
0. 取基準：base_sha = git -C <wt> rev-parse --short HEAD      # R-4.5.9-2；之後不再重取
   取母體：tracked  = git -C <wt> diff HEAD --name-only
           untracked = git -C <wt> ls-files --others --exclude-standard -z
   expected_paths = tracked ∪ untracked                       # 🔴 聯集，不是只有 tracked
1. 寫 patch：tmp 檔 → flush() → os.fsync(fd) → close() → os.replace(tmp, final)
             （原子換名，同 §4.5.1 步驟 4 的既有紀律）；記下寫入位元組數 n_written
2. 寫 .sha256 側檔（同樣 fsync + replace）
3. 🔴 重新開檔讀回 final（**不得**複用寫入時的 buffer／記憶體內容——那樣驗的是記憶體
   不是磁碟，而磁碟才是這一條要治的東西），逐塊算 SHA-256
4. 四個斷言全過才算成功（(a)~(c) 的母體是磁碟，(d) 的母體是 expected_paths）：
   (a) 讀回的 SHA-256 == 側檔內容
   (b) 讀回位元組數 == n_written
   (c) n_written > 0                      # 空檔 vs 空檔的 SHA-256 會一致 ⇒ 第一個漏洞
   (d) 🔴 覆蓋率：expected_paths 的**每一個**路徑，都必須在讀回的 patch 內容裡出現於
       某一段 `diff --git a/<X> b/<Y>` 標頭的 **X 或 Y 任一側**；缺任何一個即失敗。
       這一格是 v2.1.9 補的第二個漏洞——(a)(b)(c) 全部只問「磁碟上那份檔完不完整」，
       沒有一格問「它裝的東西夠不夠」。母體來自步驟 0 的**列舉**而不是 patch 自己，
       否則就是拿答案去對答案。
5. 第二道語意閘（形態見上表；失敗的處置同驗證失敗），跑完刪除 <idx>
```
🔴 **(d) 為什麼是「X 或 Y 任一側」而不是 `a/<path> b/<path>`（v2.1.9；當回合實測，寫死以免
假紅把整條判準關掉）**：git 對**改名**產生的標頭兩側路徑**不同**，而 `--name-only` 只報新名。
合成 worktree 實測（同時含改名／刪除／修改／untracked 四種）逐字：

```
git status --porcelain           ⇒   D del.txt /  M keep.txt / R  ren.txt -> renamed.txt / ?? brand.py
git diff HEAD --name-only        ⇒  del.txt / keep.txt / renamed.txt          ← 只有新名
實際產生的標頭                    ⇒  diff --git a/del.txt b/del.txt
                                     diff --git a/keep.txt b/keep.txt
                                     diff --git a/ren.txt b/renamed.txt        ← 兩側不同名
                                     diff --git a/brand.py b/brand.py
```

⇒ 寫成 `a/<path> b/<path>` 的實作會對 `renamed.txt` 判**失敗**，而那是一次**假紅**：patch
其實完整涵蓋了它。假紅的下場本 repo 已有判例（擋到讓人無法工作的守衛會被整個關掉，比沒有
守衛更糟）⇒ 這一格必須是判準本文的一部分。
🔴 **反向也要有一格控制組**：真的少一個路徑時 (d) 必須紅——否則「兩側任一」放寬到最後會
變成「只要 patch 非空就算涵蓋」。

**R-4.5.9-4（驗證失敗的狀態轉移：fail-loud，且絕不 fail-open）**

- 進入條件改寫：由原文的「三者皆失敗」改為「**驗證失敗**」（含 R-4.5.9-3 任一斷言不成立）
  即進入既有終態 `DIRTY_UNSAVED`（狀態名沿用，不改編號骨架）。
- `DIRTY_UNSAVED` 的語意收緊為三件事**同時**成立：
  1. state.json 內明確警示，且必須帶可重驗的四個值：patch 路徑、期望 checksum、實測
     checksum、位元組數（寫入時 vs 讀回時）。只寫「救援失敗」等於把下一輪的診斷成本
     推給人。
  2. **禁止自動喚醒**（需人工確認；沿用原條文）。
  3. 走 §4.5.7 R-4.5.7-3 的桌面通知通道 **loud 一次**。🔴 原條文只要求「在 state.json 中
     明確警示」——state.json **沒有讀者會主動去看它**，那是 fail-quiet，而本節整段修憲的
     出發點正是「patch 寫下去了沒人驗它讀不讀得回來」這種靜默。
- 🔴 **重試不得無上限**：磁碟滿是最可能的成因，每一次重試再吃一份空間。上限
  `DIRTY_SAVE_RETRIES`（建議 1 次重試），且第二次寫入**之前**必須先跑一次 §6.2 R-6.2-3 的
  可用空間檢查；仍失敗即終態。
- 🔴 **絕不 fail-open**：驗證失敗時**不得**繼續轉入 `WAITING_RESET`／`LONG_HIBERNATE`。
  那兩個狀態的語意是「工作已保全，可以安全睡」，而此刻工作沒有保全。

**驗收判準（全部可機械查證）**：

| # | 判準 | 查證方式 |
| :---- | :---- | :---- |
| D1 | 救援序列不含任何改動工作樹的 git 動詞、不含 `--no-verify`、不含 `git stash create -u`、不含 `--3way`；救援後 `git status --porcelain` 逐字不變 | 靜態詞彙掃描（判準形態同 `.claude/hooks/block_destructive_git.py`）＋ 對真 worktree 的整合測試（前後兩次 `status --porcelain` 字串相等）。🔴 整合測試的工作樹**必須同時含 tracked 變更與 untracked 新檔**——只有 tracked 的樹讓 D8 結構上跑不到 |
| D2 | patch 落在 `AUTOCLAUDE_CHECKPOINT_DIR`、檔名時間戳帶 offset、連續兩次救援產出**兩個**檔 | 整合測試（連跑兩次，斷言檔數 == 2） |
| D3 | **驗證真的重新開檔**：寫入後把檔案截半（模擬磁碟滿）⇒ 必須判失敗 | 單元測試 ＋ **紅綠自證**：把驗證改成「用寫入時的 buffer 算」必須讓本測試轉綠 ⇒ 該對照組是本條的鑑別力憑證，不可省 |
| D4 | 驗證失敗 ⇒ 狀態 `DIRTY_UNSAVED`、`resume` 被拒、桌面通知恰好發生一次、state.json 帶齊四個可重驗值 | 單元測試。**控制組**：驗證成功 ⇒ 狀態為 `WAITING_RESET`／`LONG_HIBERNATE` 且**無**通知 |
| D5 | 0 bytes patch 不得被判成救援成功 | 單元測試（空 diff 的路徑本就不該進救援；若進了，(c) 斷言必須擋下） |
| D5b | patch **非空但內容不足** 也不得被判成救援成功 | 單元測試。(c) 只問「有沒有位元組」，D8 才問「裝的東西夠不夠」；本列是兩者之間那道界線的守衛：注入「① 有輸出、② 為空」⇒ 必須失敗 |
| D6 | 重試上限：注入永久失敗 ⇒ 寫入嘗試次數 ≤ `DIRTY_SAVE_RETRIES + 1`，且不進入無限迴圈 | 單元測試（計數注入）。理由掛鐵律六：等待／重試機制自己靜默壞掉 ⇒ 無做工空轉 |
| D7 | 第二道語意閘走**臨時索引 read-tree 到 R-4.5.9-2 記錄的 base_sha ＋ `apply --check --cached`**，判準為 `rc == 0`，且失敗處置與驗證失敗相同 | 整合測試（構造一個 checksum 正確但套不回 base_sha 的 patch ⇒ 實測 rc=1）＋ 三道形態控制組，每一道都必須紅：(i) 改成在髒工作樹上裸跑 `apply --check`（實測 rc=1，恆紅＝無鑑別力）；(ii) 改成吃真索引的 `--cached`（有 staged 變更時實測 rc=1，假紅）；(iii) 加上 `--3way`（實測把套不上 fuzz 成 rc=0，假綠）。🔴 另需一格斷言真索引與 `status --porcelain` 跑完後皆未變 |
| D8 | 🔴 **救援的母體是「tracked 變更 ∪ untracked 新檔」**：在**同時**含 tracked 變更與 untracked 新檔的髒工作樹上跑救援，patch 內容必須涵蓋**該 untracked 新檔** | 整合測試：`?? brand_new.py` 存在 ⇒ 讀回的 patch 內必須有 `diff --git a/brand_new.py b/brand_new.py`。**🔴 紅綠自證（本列的鑑別力憑證，不可省）＝把實作退回「維持現行 `git diff HEAD` 單一來源」必須讓 D8 轉紅**；退不紅就表示本測試沒有在測它宣稱要測的東西。立案實測：單一來源下 patch `135` bytes 非空、四道斷言全綠、`grep -c 'brand_new'` ⇒ `0` |
| D8b | (d) 的路徑比對是**兩側任一**，不是 `a/<p> b/<p>` | 整合測試：工作樹同時含改名／刪除／修改／untracked 四種（實測標頭 `diff --git a/ren.txt b/renamed.txt` 兩側不同名，而 `--name-only` 只報 `renamed.txt`）⇒ 寫成兩側同名的實作必須紅（假紅示範），寫成兩側任一的必須綠。**反向控制組**：真的抽掉一個路徑時 (d) 仍必須紅 |
| D9 | patch 檔自己不得被列舉進自己（自我遞迴） | 整合測試：把 `AUTOCLAUDE_CHECKPOINT_DIR` 的頂層目錄從 `.gitignore` 移除 ⇒ 必須紅（實測：`status` 前後不相等，且 patch 內含自身檔名）；在 `.gitignore` 內 ⇒ 綠（實測 `grep -c` 自身檔名 `0`）。前置斷言見 R-4.5.9-1 末段 |

#### 4.5.10 醒來確認額度是否已恢復（v2.1.8 修憲；標的＝§8-2）

**原條文（§8-2／§4.5.3 步驟 2）**：醒來後確認 `U5h < RESET_CONFIRM_PERCENT`；未達則退避
重試（`30s→300s`，最多 10 次），仍未達則延長等待並告警。

**兩端都不是理想（兩個失效方向各自具名）**：

| 形態 | 為什麼會壞 | 出處 |
| :---- | :---- | :---- |
| 固定級距 `30s→300s ×10` | **是在猜 reset 時刻** ⇒ 會醒在錯的時間，白燒一個額度視窗；而且「猜出來的排程照樣拿得到 `NextRunTime`」＝取證規則全綠的假綠 | 本 repo 已立案「reset 時刻是滾動視窗，只能觀測不能算」（ADR-XPLAT-004 §2.1；分佈現查 `python tools/probe/reset_window_distribution.py`）。現行實作對此已有具名鎖 `tools/tests/test_context_budget_guard.py::SentinelDecisionTest::test_an_unparseable_reset_refuses_to_guess`，逐字要求 `escalate` 且理由含「拒絕用猜的」 |
| 現行實作的另一端「解不出就硬停不猜」 | 方向對，但終點是**永眠**：伺服器永遠不報時刻就永遠不醒 | 同上鎖的四分支：解不出 ⇒ `escalate`（叫人）。叫人本身沒錯，但它把「等一個零成本事件源」也一起排除了 |
| 原條文的終點「延長等待並告警」 | 沒定義延長多久、也**沒有任何事件源會叫醒它** ⇒ 直接違反鐵律六（除「等額度 reset」與「等人介入」，任何停等都必須有一個會主動叫醒我的事件源） | 根 CLAUDE.md 鐵律六 |

**裁決（理想版）：永不在錯誤時刻喚醒，也永不無限期沉睡。觀測優先；解不出時不是終止，
而是掛回零成本巡邏由它兜底重試。**

**🔴 本節在改什麼：具名標的、既有常數、以及必然轉紅的既有鎖（v2.1.9 補；此前全 PRD
對這三個名字零命中，等於在無記錄的情況下推翻三支既有機械鎖與兩個既有常數）**

| 面 | 座標（機械現查得到） | 現況逐字 |
| :---- | :---- | :---- |
| 本節真正在改寫的**判定函式** | `tools/session_resume_planner.py::tick_plan(state, verdict, now)` | 純函式，回 `{action, reason, at, state}`；`action ∈ {resume, rearm, stop}`（AST 實查三個相異值）。docstring 逐字「探測完之後**該做什麼**的唯一判定……整條續航鏈的大腦」 |
| 既有常數 ①（探測次數上限） | 同檔 `MAX_PROBE_ATTEMPTS`（實查 **5**） | 檔內 WHY 逐字自陳「**這個數字是挑的、不是量出來的**」，並記載上界估算 `5 × 一次探測（31,847 tokens／$0.0176）≈ 16 萬 tokens` |
| 既有常數 ②（暫時性錯誤重排間隔） | 同檔 `TRANSIENT_RETRY_SECONDS`（實查 **300**） | 註解逐字「不計入 `MAX_PROBE_ATTEMPTS`——壞的是別的東西，不是額度」 |

**三支既有鎖逐一登記（皆住 `tools/tests/test_context_budget_guard.py::TickDecisionTest`）**：

| 鎖（全名） | 它**現在**斷言什麼 | 新條文下**該**斷言什麼 | 為什麼改是對的 |
| :---- | :---- | :---- | :---- |
| `test_still_closed_without_a_parseable_reset_refuses_to_guess` | `action == "stop"`，且 `reason` 含「拒絕」 | `action ==` R-4.5.10-4 的**新事件名**（掛回巡邏），`state` **不得**為 `abandoned`；而 `reason` 仍必須含「拒絕」族措辭 | 這支鎖同時鎖住**兩件**事，而只有一件是對的：「拒絕用猜的」是本 repo 憲法（reset 只能觀測不能算）⇒ **必須原封不動保留**；「所以只能死」是它自己多出來的結論——`stop`／`abandoned` 的代價是永眠（伺服器永遠不報時刻就永遠不醒）。改後兩件事分離：不猜（保留）＋不死（改）。🔴 因此本鎖**不得整支刪掉**，只准改那一個 assert；刪掉它就把「不猜」一起丟了 |
| `test_the_attempt_cap_actually_stops` | 在 `attempts == MAX_PROBE_ATTEMPTS - 1` 時 `action == "stop"` 且 `state == "abandoned"` | 同一輸入下 `action ==` 新事件名、`state != "abandoned"`，**並新增**一格斷言：該路徑此後**不得再產生任何付費探測**（`action != "rearm"`，即不再排一次會花 token 的醒） | 上限的 WHY 逐字是「沒有硬上限的重排會在額度最緊的時候持續燒」——它要保護的是**不要再燒**，不是**要死掉**。掛回巡邏的成本結構恰好滿足它：巡邏只讀逐字稿 ＋ 一次 `stat`，**零 token** ⇒ 上限的目的達成、而永眠這個副作用消失。新增的那格斷言是把「不再燒」變成可查的，否則改完之後沒有人守得住原本那個目的 |
| `test_transient_retries_without_spending_an_attempt` | `action == "rearm"`，且 `at − now == TRANSIENT_RETRY_SECONDS`（＝**300s**） | **一字不改，繼續綠** | 🔴 這一支是三支裡唯一**不該**改的，而不改的理由必須寫下來，否則實作者會照 R-4.5.10-1 的「≤ 90s」把 300 砍掉：**兩個數字量的不是同一段時間**。`TRANSIENT_RETRY_SECONDS` 是**跨醒來**的重排間隔（一次 `schtasks`／`launchctl` 觸發＝一次行程 spawn），而 R-4.5.10-1 的「≤ 3 次／≤ 90s」是**單次醒來之內**的行程內重量。把跨醒來間隔壓到 90s 等於每 90 秒 spawn 一個行程去問同一件事——那正是「掛回零成本巡邏」要取代的東西。⇒ R-4.5.10-1 的射程已同步收窄成「行程內」（見下條），兩者於是不再互相矛盾 |

> 🔴 **登記這件事本身是規範性的**：以上三個座標與兩個常數必須在實作 PR 的描述裡逐一
> 對帳。理由是本節此前的失效形態——條文推翻了鎖，而鎖的名字一次都沒出現在條文裡 ⇒
> 實作者改鎖時無從分辨「這支鎖過期了」與「我改壞了」。

**R-4.5.10-1（觀測優先；固定級距只准治「這一次量測失敗」）** 醒來後先重新觀測。確認
`U5h < RESET_CONFIRM_PERCENT` ⇒ 走 §4.5.3 步驟 3。未確認時**不得**用固定級距重試 10 次
然後放棄。full-jitter 退避保留，但**降級**為單一觀測動作的重試（治的是取數端點瞬時
5xx 這種東西）：上限 3 次、總時長 ≤ 90s。

🔴 **這條「≤ 3 次／≤ 90s」的射程只有「同一次醒來的行程內」**（v2.1.9 收窄；不收窄的話
它會與既有常數 `TRANSIENT_RETRY_SECONDS`＝300 直接衝突，而該常數量的是**跨醒來**的重排
間隔）。兩層各自的家與判準：

| 層 | 家 | 值 | 判準 |
| :---- | :---- | :---- | :---- |
| 行程內重量（本條） | 實作本節時新增 | ≤ 3 次、總時長 ≤ 90s | E1 |
| 跨醒來重排（既有） | `tools/session_resume_planner.py::TRANSIENT_RETRY_SECONDS` | 現值現查（實查 300） | 既有鎖 `test_transient_retries_without_spending_an_attempt` 繼續綠 |

⇒ 實作時**不得**把兩層折成一個數字。折起來的失效方向是可預測的：取 90s 會讓跨醒來重排
變成每 90 秒一次行程 spawn；取 300s 會讓「端點瞬時 5xx」這種該立刻再量一次的事白等五分鐘。

> 🔴 這兩件事此前混在同一個退避階梯裡，是本節要拆開的東西：「這一次量測失敗」與
> 「reset 還沒到」的正確處置完全不同——前者該立刻再量一次，後者該去等一個事件。

**R-4.5.10-2（解不出 ⇒ 掛回零成本巡邏，不是終止）** 確認不了 reset（量不到、或量到但仍
高於 `RESET_CONFIRM_PERCENT`、或訊息裡解不出時刻）時，狀態**不轉終態**，而是掛回既有的
零成本巡邏：

- **掛點（指名真實存在的東西，不得寫成抽象的「排程機制」）**：
  `python tools/session_resume_planner.py --arm-sentinel`（SessionStart 已自動武裝；本條是
  「確認失敗」這條路徑上的**再**武裝）。它註冊的是 Windows `schtasks`／macOS `launchctl`
  排程；巡邏本體＝`tools/session_resume_planner.py::_sentinel_tick()` →
  `tools/lib/quota_escalation.py::patrol_housekeeping()`；四分支判定＝同檔
  `sentinel_decide()`；痕跡與憑證紀律沿用 §4.5.6 R-4.5.6-6。
- **為什麼「掛回巡邏」不是換一種等待**：巡邏**只讀逐字稿 ＋ 一次 `stat`，零 token**——
  `SENTINEL_INTERVAL_SECONDS` 上方的既有 WHY 逐字如此，並記載「這一側沒有需要權衡的
  東西」。⇒ 它可以無限期掛著，而固定級距不能（每一次醒來都是一次真的探測成本）。
- **巡邏偵測到新的可觀測 reset 時刻** ⇒ 自動轉續航排程（`arm_reset` 分支），回到
  R-4.5.10-1 的確認流程。這就是「兜底重試」的全部機制，不新增第二套。
- 🔴 **兩個例外必須繼續走 `escalate`（叫人），不得掛回巡邏**：
  1. 月度支出上限（SSOT＝`tools/lib/quota_limits.py::LIMIT_SPEND`，hook 側為再匯出）——等到
     天荒地老都不會回來，只有人去提額。既有鎖
     `test_a_spend_limit_escalates_instead_of_waiting` 不得因本節而鬆掉。
  2. 逐字稿判定「工作已結束」（自我解除門檻成立，見 R-4.5.10-3）——那是正常下班。

**R-4.5.10-3（兩個常數只登記方向與導出關係，數值不進本 PRD）**

- **巡邏間隔的上界是導出的，不是選的**：間隔決定「reset 之後最壞多久才會有人動作」
  ⇒ **只准調小**。家＝`tools/session_resume_planner.py::SENTINEL_INTERVAL_SECONDS`；方向鎖＝
  `tools/tests/test_context_budget_guard.py::SentinelDecisionTest::
  test_the_patrol_interval_bounds_the_post_reset_dead_time`（該測試並明文禁止改成 50 分鐘
  ——那個數字是 `ScheduleWakeup` 的 `delaySeconds` 上限外溢出來的，`schtasks` 沒有那個
  上限）。
  - 🔴 **已被證偽、不得再引用的舊說法**：「間隔小於最短觀測窗」。R80 以全庫 1,433 支逐字稿
    重量得最短窗 **0.5 分鐘** ⇒ 該宣稱字面不成立。窗比間隔短時走的是 `probe` 分支，
    **代價是一次探測，不是失效**。
- **自我解除門檻必須大於一個完整的額度視窗**：等額度那段期間逐字稿本來就不會更新，門檻
  若短於視窗，哨兵會在最需要它的時候把自己拆掉。家＝同檔 `SENTINEL_IDLE_SECONDS`；
  方向鎖＝同檔 `test_the_idle_threshold_outlives_a_whole_quota_window`。
- 🔴 **為什麼 PRD 只登記方向**：把數字複寫進來會製造第二個家。本文件已有同型判例——
  §4.5.7 R-4.5.7-1 逐字寫「不寫死於本 PRD」。

**R-4.5.10-4（「掛回巡邏」與「終止」在痕跡上必須可分辨）**

痕跡兩處、壽命不同（既有事實，照抄不重新發明）：事件檔 `autosdd_resume_log_*.jsonl` 住
系統暫存（重開機即消失 ⇒「查不到」≠「沒發生」）；分支／等待痕跡落
`tools/lib/endurance_env.py::trace_dir()`（出廠 `~/.autosdd/traces`，逃生口
`AUTOSDD_TRACE_DIR`，唯讀時退回暫存）。

規範性要求：三種結局各有**互異的事件名**，且「沒觸發＝檔不長大」這個可偵測性不得被破壞。

| 結局 | 事件名要求 | 何時出現 |
| :---- | :---- | :---- |
| 掛回巡邏（本節新增） | 必須與 `sentinel_decide()` 既有的**五**個分支名（`arm_reset`／`disarm`／`escalate`／`patrol`／**`probe`**）**都不同**——它是「確認失敗但刻意不終止」，那五個名字沒有一個表達這件事 | R-4.5.10-2 主路 |
| 終止（`disarm`） | 沿用 | 僅自我解除門檻成立時 |
| 叫人（`escalate`） | 沿用 | 僅 R-4.5.10-2 那兩個例外 |

🔴 **禁止用「同一個事件名 ＋ 一個布林欄位」表達這三者**。理由沿用 §4.5.8 R-4.5.8-3 的逐字
紀律：`sentinel_decided` 那一行每次巡邏都會印，欄位增減不足以讓「這次是確認失敗掛回去」
在痕跡上一眼可辨。

🔴 **既有分支到底有幾個：五個，不是四個**（v2.1.9 訂正；當回合對
`tools/session_resume_planner.py::sentinel_decide()` 做 AST 實查，取所有 `action` 字面）：

```
sentinel_decide actions = ['disarm', 'probe', 'patrol', 'escalate', 'escalate', 'arm_reset']
distinct = ['arm_reset', 'disarm', 'escalate', 'patrol', 'probe']   count = 5
```

- **缺的那一個是 `probe`**：`reset_at` 已過（`at <= now`）時走它，逐字理由「花一次探測確認
  額度回來了沒」。它是五個分支裡**唯一會花錢**的那一個 ⇒ 恰好是最不能與「掛回零成本巡邏」
  撞名的一個。
- **為什麼原條文寫「四」不是筆誤而是有代價的**：本節 R-4.5.10-3 自己就引用了 `probe`
  （「窗比間隔短時走的是 `probe` 分支」）⇒ 節內自相矛盾。而 E5 的判準是「名稱集合互斥」：
  實作者把新事件命名為 `probe` 會**通過 E5**，卻與既有分支撞名——正好摧毀本條唯一要保護的
  「痕跡上一眼可辨」。判準寫錯方向時，通過判準的實作就是壞的那一個。
- 🔴 **`sentinel_decide()` 自己的 docstring 逐字仍寫「四分支判定」**，與函式體實有的 5 個
  action 不一致。那份 docstring 的訂正屬**實作面**（本節不改 `.py`），但實作本節時必須一併
  修掉——否則 E5 的實作者會照 docstring 而不是照函式體去數，重犯同一個錯。

**驗收判準（全部可機械查證）**：

| # | 判準 | 查證方式 |
| :---- | :---- | :---- |
| E1 | 觀測優先：未確認時的量測重試 ≤ 3 次、總時長 ≤ 90s，且最終動作是「重新武裝巡邏」而非放棄 | 單元測試（注入未確認讀數，斷言呼叫序列） |
| E2 | 解不出 ⇒ 掛回巡邏而非終止 | 單元測試 ＋ **紅綠自證**：把該分支改回 `disarm`／`escalate` 必須轉紅 |
| E3 | 月度支出上限仍 `escalate`（控制組） | 既有鎖 `test_a_spend_limit_escalates_instead_of_waiting` 必須繼續綠 |
| E4 | 兩個常數的方向鎖仍在：巡邏間隔只准調小、自我解除門檻大於一個完整額度視窗 | 後設斷言：那兩支既有測試的**名字**必須仍存在於檔內（本節新增了一條依賴它們的路徑 ⇒ 它們被刪掉時必須有人知道） |
| E5 | 三種結局事件名互異，**且新事件名與 `sentinel_decide()` 的五個既有 action 皆不同**；零觸發 ⇒ 痕跡檔位元組數不變 | 單元測試：互斥集合是**五元素**（`arm_reset`／`disarm`／`escalate`／`patrol`／`probe`）＋ 新名，共 6 個相異字串。🔴 **五元素那一半必須由 AST 從 `sentinel_decide()` 現查取得，不得在測試裡手抄常數清單**——手抄就是把同一份清單放進第二個家，而本列立案的成因正是一份手抄清單漏了 `probe`。**紅綠自證**：把新事件名改成 `probe` 必須轉紅 ＋ 整合測試（不觸發後 `stat` 位元組數相等） |

### 4.6 跨平台防休眠（修正 v1 的技術細節）

| 平台 | 實作 | v1 的問題與修正 |
| :---- | :---- | :---- |
| **macOS** | `caffeinate -i -m -w <DAEMON_PID>` | v1 用 `-s`：**`-s` 僅在接電源時有效，電池模式下機器仍會睡**。改用 `-i`（防閒置睡眠）+ `-m`（防硬碟睡眠），並以 `-w <PID>` 綁定 Daemon 生命週期，避免 Daemon 崩潰後 caffeinate 變孤兒程序永久阻止睡眠。不使用 `-d`（依需求允許螢幕關閉；v1 註解列出 `-d` 與其宣稱目標矛盾） |
| **Windows** | `SetThreadExecutionState(ES_CONTINUOUS \| ES_SYSTEM_REQUIRED)` | v1 的三個問題：(a) 此 API 是**執行緒層級**，若在短命執行緒中呼叫，執行緒結束即失效 → 必須在長駐主執行緒呼叫並保持存活；(b) `ES_AWAYMODE_REQUIRED` 是給媒體播放場景，一般背景運算不宜使用，且在 Modern Standby (S0ix) 機器上行為不同；(c) 未定義還原：退出時必須呼叫 `SetThreadExecutionState(ES_CONTINUOUS)` 清除 |
| **Linux** | `systemd-inhibit --what=idle:sleep --who=autoclaude --why="token wait" <cmd>` | v1 **完全未支援 Linux**（但 Claude Code 支援 Linux／WSL） |
| **驗證** | macOS `pmset -g assertions`；Windows `powercfg /requests`；Linux `systemd-inhibit --list` | v1 無驗證手段。防休眠是否生效必須可觀測，並寫入啟動自檢 |

補充：防休眠**只用於短等待**（`< MAX_INPROCESS_WAIT_SECONDS`）；長等待改用 §4.5.5 的排程器交棒。另需處理「防休眠失效、機器仍睡著」的情況：醒來後偵測時鐘跳躍 → 重新輪詢遙測 → 若已過重置點則直接進入 `RESUMING`。

### 4.7 帳號配額仲裁（v1 缺漏的多實例問題）

額度是**帳號層級**資源，但 Daemon 是**專案層級**行程。同帳號同時跑兩個專案時，兩個 Daemon 各自看到「還有 60% 可用」，合起來就會超燒。

```
仲裁機制：
  ~/.autoclaude/accounts/<account_fingerprint>/     # fingerprint 為帳號識別的雜湊，不存明文憑證
    ├── quota.lock          # 檔案鎖，序列化配額決策
    ├── telemetry.json      # 共享的權威遙測快取（含 fetched_at）
    └── leases/<daemon_id>.json   # 各 Daemon 的併發租約（含到期時間）

分配規則：
  總可用併發 C_account 由讀取共享遙測後統一計算
  各 Daemon 依 lease 取得配額，lease 有 TTL（預設 120s），過期自動回收
  無法取得鎖 → 視為遙測不可得 → fail-safe 降級
單機單專案時此機制近乎零成本（無競爭）。
```
另需 Daemon 單實例鎖：`.autoclaude/daemon.lock`（含 PID 與啟動時間，偵測陳舊鎖）。

---

## 5. API Key 模式（v1 只提一句，實際無法運作）

v1 的配速演算法完全建立在「百分比 + 重置時間」之上，但 API Key 模式沒有這兩者。必須有正規化層：

| 項目 | OAUTH 模式 | API_KEY 模式 |
| :---- | :---- | :---- |
| 使用率 | 原生百分比 | `U := max(已用預算/預算上限, 觀測 TPM/TPM 上限)` × 100 |
| 「重置時間」 | 視窗重置時間戳 | **使用者定義的預算週期**（`API_BUDGET_PERIOD=DAILY\|WEEKLY\|MONTHLY`）的結束時間 |
| 硬性上限 | 平台強制 | `API_BUDGET_HARD_USD`（**必填**，無預設值，未設定則拒絕啟動） |
| 限流訊號 | 429 | 429 + 回應標頭中的剩餘配額／重試建議 `[需核對標頭名稱]` |
| 成本計算 | 不適用 | 需依模型單價表計算；單價表需可設定且標註更新日期 |

**安全要求**：API 模式下 `TOKEN_HALT_PERCENT` 對應的是「花光使用者自訂預算」，而非平台限制。達 HALT 後**不得**自動在下個週期繼續（避免無人看管的持續支出），需 `API_AUTO_CONTINUE_NEXT_PERIOD=false`（預設）。

---

## 6. 設定檔規範（.env.example，修訂版）

```dotenv
# ==============================================================================
# AutoClaude Token & Agent Dispatch Configuration  (schema v2)
# 不變式由啟動自檢驗證，違反則拒絕啟動（見 §6.1）
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. 帳號與認證
# ------------------------------------------------------------------------------
AUTOCLAUDE_AUTH_MODE=OAUTH                  # OAUTH | API_KEY
AUTOCLAUDE_ACCOUNT_TYPE=MAX                 # 僅作為預設值提示；實際額度一律以遙測為準
                                            # （v1 隱含以帳號等級推算額度，不可靠）

# ------------------------------------------------------------------------------
# 2. 遙測來源（依序嘗試，全部失敗則 fail-safe）
# ------------------------------------------------------------------------------
TELEMETRY_SOURCE_ORDER=OAUTH_USAGE,OTEL,TRANSCRIPT,STATUSLINE,CLI_USAGE
#   ↑【v2.1.4 落款補 T5】OAUTH_USAGE＝§4.1.1 T5 認可主源（帳號層級全計費軸權威讀數，故列首）；
#   T1（OTEL）官方正途地位不變——兩者量測軸不同，劃界見 §4.1.1〈T1／T5 劃界〉。
# 【v2.1.4 落款裁決（R107 四方複審）】原 `TELEMETRY_ALLOW_UNDOCUMENTED_ENDPOINT` kill-switch
#   旗標**不做、已移除**：該旗標全庫零實作（2026-08-28 現查：命中僅文件 3 處、零程式／設定
#   消費端），紙上開關＝「有守衛」的假外觀。未文件化端點（T5）的遙測**恆啟用**；防護不靠
#   開關，靠 §15.5 紅線 1 豁免四條件（唯讀 GET／單一程式站點 tools/lib/quota_meter.py／
#   TTL≥180s 節流／失效降級出聲），任一條件破缺即回到禁令本身。
MONITOR_POLL_INTERVAL_SECONDS=60
TELEMETRY_TIMEOUT_SECONDS=600               # 超時 → 收斂到 cap_prepare 語意（v2.1.8：原文寫 DRAINING，本實作無該狀態物件，見 §4.1.5）
TELEMETRY_UNMEASURED_CAP=                   # 【v2.1.8 新增／v2.1.9 訂正】留空＝取實作面出廠值。
#   🔴 這**不是新旋鈕**：它與實作面既有的 `AUTOSDD_QUOTA_DEGRADED_CAP`（→ `Policy.degraded_cap`，
#   出廠值不複寫、一律現查 `ENV_SPEC`【v2.1.4 落款訂正：原「實查出廠值 4」寫於 R100 收緊前，
#   R100 已依 R-4.1.5-1 收緊至 ≤ cap_prepare】；值域下界 1.0，`ENV_SPEC` 逐字說明
#   「量不到時的上限（絕不是『不設限』；≤ cap_prepare）」）
#   是**同一個旋鈕的兩個命名面**——PRD 面／實作面。三個候選處置裡選這一個的理由，以及被否決
#   的兩個，見 §4.1.5〈這個旋鈕有幾個家〉。值域：1 ≤ 本鍵 ≤ cap_prepare（下界沿用實作面
#   ENV_SPEC，上界為 v2.1.8 修憲新增）。數值一律以實作面為 SSOT，本檔不複寫。
LOCAL_ESTIMATE_SAFETY_MARGIN_PP=15          # 僅有本機推估時，所有水位悲觀化的百分點

# ------------------------------------------------------------------------------
# 3. 額度水位（5 小時視窗，單位 %）
#    不變式：0 < WARN < DRAIN < HALT <= 100  且  HALT - DRAIN >= 5
# ------------------------------------------------------------------------------
TOKEN_WARN_PERCENT=70                       # → THROTTLING
TOKEN_DRAIN_PERCENT=85                      # → DRAINING（單向鎖存）
TOKEN_HALT_PERCENT=95                       # → FREEZING
# 已廢除（v2.1.8）：WATERMARK_HYSTERESIS_PP —— 遲滯帶改掛「量測可得性」軸。
#   立案實測：十天 819 個逐軸讀數，小幅擺動反轉 0 次（33 次下降穿越全部是視窗翻頁）
#   ⇒ 掛在 watermark 上結構上得不到動作。改後的運算元與新鍵見 §4.2.4、下方區塊 6。

# ------------------------------------------------------------------------------
# 4. 週額度安全閥
#    不變式：WEEKLY_WARN < WEEKLY_DRAIN < WEEKLY_HALT
# ------------------------------------------------------------------------------
ENABLE_WEEKLY_LIMIT_GUARD=true
WEEKLY_HALT_PERCENT=90                      # → LONG_HIBERNATE（絕對上限仍需保留）
MODEL_DOWNGRADE_PERCENT=50                  # 高階模型週額度達此值 → 降級

# 【v2.1 修正】週額度改以「配速指數」治理，不用絕對水位。
# 理由見 §4.2.8：依 CLI 內建判準，週視窗流逝 15% 時利用率就不該超過 25%，
# 用絕對水位（如 70%）會太晚，導致週三燒完、後四天全在等。
PACING_MODE=PACE_INDEX                      # PACE_INDEX（建議）| ABSOLUTE_WATERMARK（v2.0 舊行為）
WEEKLY_PACE_CEILING_THROTTLE=1.25           # pace_index 超過 → THROTTLING
WEEKLY_PACE_CEILING_DRAIN=1.50              # pace_index 超過 → 併發壓到 1
FIVE_HOUR_PACE_CEILING=1.25                 # 5h 視窗的配速上限（對齊內建判準 0.9/0.72）
PACE_MIN_UTILIZATION=0.05                   # 利用率低於此值時不套用配速判準（避免視窗開頭誤判）

# 保留為 ABSOLUTE_WATERMARK 模式的後備門檻（PACING_MODE=PACE_INDEX 時僅作為硬上限）
WEEKLY_WARN_PERCENT=70
WEEKLY_DRAIN_PERCENT=80

# ------------------------------------------------------------------------------
# 4b. 超額用量治理（v2.1 新增 — v1/v2.0 完全遺漏的維度）
#     核實發現額度類型含 overage / extra_usage / seven_day_overage_included，
#     且有月度支出上限。若帳號已啟用付費超額，達訂閱限制後可能「不停止而開始計費」，
#     使凍結邏輯永不觸發卻默默產生帳單。這是本系統最危險的單一失敗模式。
# ------------------------------------------------------------------------------
OVERAGE_POLICY=FREEZE                       # FREEZE（預設，絕不動用超額）| ALLOW_WITH_CAP
OVERAGE_HARD_CAP_USD=                       # OVERAGE_POLICY=ALLOW_WITH_CAP 時必填，無預設
OVERAGE_ALERT_ON_FIRST_USE=true             # 一旦偵測到 overage 類額度被動用即告警
OVERAGE_MONTHLY_UTILIZATION_HALT=80         # 月度超額利用率達此值 → 強制 FREEZE

# ------------------------------------------------------------------------------
# 5. 上下文管理（與額度水位「無關」，v1 混用是錯誤的）
# ------------------------------------------------------------------------------
CONTEXT_COMPACT_PERCENT=84                  # 【新增】單一 session 上下文佔用率（R92 掌舵者裁決 75→84：與額度尺 85/95 錯開以保鑑別力）
COMPACT_COST_BUDGET_PP=3                    # 【新增】一次壓縮預估消耗的額度百分點
COMPACT_MIN_INTERVAL_SECONDS=1800           # 【新增】
# 已廢除：TOKEN_COMPACT_PERCENT（語意錯誤，見 §10 遷移對照）

# ------------------------------------------------------------------------------
# 6. 動態併發
# ------------------------------------------------------------------------------
AGENT_MIN_CONCURRENCY=1
AGENT_DEFAULT_CONCURRENCY=2
AGENT_MAX_CONCURRENCY=5                     # 亦受 CPU/RAM 與平台併發限制夾緊
AGENT_THROTTLE_CONCURRENCY=1                # 【新增】THROTTLING 狀態上限
BURN_RATE_EWMA_ALPHA=0.25                   # 【新增】取代固定 15 分鐘視窗
# 【v2.1.8 修憲】本區塊三個鍵的運算元改寫，理由與對照見 §4.2.4。
#   舊：CONTROL_INTERVAL_SECONDS / CONCURRENCY_MIN_DWELL_SECONDS 綁「持久併發設定點」，
#       而本實作沒有那個物件（致動器＝每次工具呼叫的准入控制 + 300s 滾動派發帳）。
CONTROL_INTERVAL_SECONDS=120                # 保留為 Daemon 形態的相容鍵；本實作的控制週期＝派發帳滾動視窗
#   ↑ 本實作對應物：tools/lib/quota_gate.py::FANOUT_WINDOW_SECONDS（現值現查該檔）
AVAILABILITY_EXIT_STREAK=2                  # 【v2.1.8 新增】離開 unmeasured 需連續幾次量得到（≥2）
AVAILABILITY_MIN_DWELL_SECONDS=             # 【v2.1.8 新增】留空＝取實作預設；不變式見 §6.1 第 4 條
#   ↑ 不變式：QUOTA_CACHE_TTL_SECONDS ≤ 本值 ≤ SENTINEL_INTERVAL_SECONDS（兩界皆導出，現值現查實作）
# 已廢除（v2.1.8）：CONCURRENCY_MIN_DWELL_SECONDS —— dwell 改掛可得性軸（見上一鍵）
FAIL_SAFE_CONCURRENCY=0                     # 保留鍵；本實作以 cap 語意表達，且量不到時 cap ≤ cap_prepare 且 ≥ 1（禁止靜默鎖死，見 §4.1.5）

# ------------------------------------------------------------------------------
# 7. 突刺（BURSTING）
# ------------------------------------------------------------------------------
ENABLE_BURSTING=true
BURST_WINDOW_MINUTES=30
BURST_MAX_U5H_PERCENT=60                    # 【新增】
BURST_WEEKLY_GUARD_PERCENT=60               # 【新增】v1 缺此閘門 → 會提前燒光週額度

# ------------------------------------------------------------------------------
# 8. Agent 硬性預算（v1 缺漏）
# ------------------------------------------------------------------------------
MAX_STEP_TURNS=40
MAX_STEP_WALL_SECONDS=900
MAX_STEP_QUOTA_PP=5
DRAIN_BUDGET_FACTOR=0.5
AGENT_TERMINATION_GRACE_SECONDS=30

# ------------------------------------------------------------------------------
# 9. 重置、休眠與喚醒
# ------------------------------------------------------------------------------
RESET_BUFFER_SECONDS=30
RESET_CONFIRM_PERCENT=10                    # 【新增】喚醒前確認 U5h 已低於此值
SLEEP_SLICE_SECONDS=30                      # 【新增】分片休眠（可回應訊號）
CLOCK_JUMP_TOLERANCE_SECONDS=120            # 【新增】偵測系統睡眠/NTP 跳躍
MAX_INPROCESS_WAIT_SECONDS=7200             # 【新增】超過則交棒 OS 排程器
RESUME_STRATEGY=AUTO                        # 【新增】AUTO|SESSION_RESUME|FRESH_SESSION_WITH_STATE
RESUME_MAX_TRANSCRIPT_TOKENS=60000          # 【新增】AUTO 的切換門檻

# ------------------------------------------------------------------------------
# 10. 防休眠
# ------------------------------------------------------------------------------
OS_KEEP_AWAKE_DRIVER=AUTO                   # AUTO|MACOS_CAFFEINATE|WIN32_API|LINUX_SYSTEMD|NONE
KEEP_AWAKE_ALLOW_DISPLAY_SLEEP=true
KEEP_AWAKE_VERIFY_ON_START=true             # 【新增】啟動自檢是否真的生效

# ------------------------------------------------------------------------------
# 11. Git 與整合
# ------------------------------------------------------------------------------
ENABLE_WORKTREE_ISOLATION=true
AUTOCLAUDE_WORKTREE_DIR=.autoclaude/worktrees
INTEGRATION_BRANCH=autoclaude/integration    # 【新增】不直接動 main
AUTOCLAUDE_CONFLICT_POLICY=HUMAN_REVIEW      # 【新增；v2.1.15 前綴對齊】ABORT|RETRY_WITH_AGENT|HUMAN_REVIEW
#   開機自檢對殘留整合項的處置：ABORT＝拒絕啟動（非零退出碼、清單照列、零重排）／
#   RETRY_WITH_AGENT＝重排給 agent 重試（DRAINING 以上與 DRY_RUN 改只登記）／HUMAN_REVIEW＝只登記。
#   非法字面 ⇒ §6.1 不變式 11 報紅、拒絕啟動（不得靜默退回出廠值）。
INTEGRATION_VERIFY_CMD="npm run lint && npm test"  # 【新增】合併前閘門

# ------------------------------------------------------------------------------
# 12. 狀態持久化
# ------------------------------------------------------------------------------
AUTOCLAUDE_STATE_FILE=.autoclaude/state.json
AUTOCLAUDE_CHECKPOINT_DIR=.autoclaude/checkpoints
STATE_WRITE_MODE=ATOMIC                      # 【新增】tmp → fsync → rename
AUTOCLAUDE_STATE_RETAIN_VERSIONS=5           # 【新增；v2.1.15 前綴對齊】保留歷史版本供人工回溯，值域 0..9
AUTOCLAUDE_DIRTY_SAVE_RETRIES=1              # 【v2.1.9 新增；v2.1.15 前綴對齊】存檔救援驗證失敗時的**重試**次數
#   （總寫入嘗試 = 本值 + 1）。值域 0 ≤ 本值 ≤ 3；0＝不重試（合法）。
#   🔴 上界不是風格問題：磁碟滿是最可能的失敗成因，每一次重試再吃一份空間 ⇒ 重試本身會讓
#   它更不可能成功。第二次寫入**之前**必須先跑一次 §6.2 R-6.2-3 的可用空間檢查。全文見 §4.5.9
#   R-4.5.9-4，判準＝該節 D6（此前本鍵只在 §4.5.9 節內出現、§6 無登記 ⇒ D6 斷言的是一個沒有
#   家的鍵，而「鍵沒有家」的失效形態是實作者各自挑一個預設值）。

# ------------------------------------------------------------------------------
# 13. 安全（v1 缺此整段）
# ------------------------------------------------------------------------------
ALLOW_PERMISSION_BYPASS=false                # 【新增】true 僅限隔離容器
AGENT_PERMISSION_MODE=acceptEdits            # 【需核對旗標名稱】
AGENT_ALLOWED_TOOLS="Read,Edit,Write,Bash(npm test:*),Bash(git status)"
REDACT_SECRETS_IN_LOGS=true                  # 【新增】

# ------------------------------------------------------------------------------
# 14. 可觀測性與運維
# ------------------------------------------------------------------------------
LOG_LEVEL=INFO
LOG_FILE=.autoclaude/logs/daemon.log
METRICS_EXPORT=PROMETHEUS_TEXTFILE           # NONE|PROMETHEUS_TEXTFILE|OTLP
ALERT_WEBHOOK_URL=                           # 【新增】狀態升級/凍結/衝突時通知
DRY_RUN=false                                # 【新增】只決策不派工，用於調參
AUTOCLAUDE_DAEMON_LOCK=.autoclaude/daemon.lock

# ------------------------------------------------------------------------------
# 15. API_KEY 模式專用（AUTH_MODE=API_KEY 時必填）
# ------------------------------------------------------------------------------
API_BUDGET_PERIOD=DAILY                      # 【新增】DAILY|WEEKLY|MONTHLY
API_BUDGET_HARD_USD=                         # 【新增】必填，無預設
API_AUTO_CONTINUE_NEXT_PERIOD=false          # 【新增】
```

### 6.1 啟動自檢不變式（v1 缺漏，必須實作）

```
1.  0 < WARN < DRAIN < HALT ≤ 100  且  HALT − DRAIN ≥ 5
2.  WEEKLY_WARN < WEEKLY_DRAIN < WEEKLY_HALT ≤ 100
3.  1 ≤ C_min ≤ C_default ≤ C_max  且  C_throttle ≥ C_min
4.  【v2.1.8 改寫】遲滯改掛「量測可得性」軸 ⇒ 等價不變式為雙邊：
      QUOTA_CACHE_TTL_SECONDS ≤ AVAILABILITY_MIN_DWELL_SECONDS ≤ SENTINEL_INTERVAL_SECONDS
      且 AVAILABILITY_EXIT_STREAK ≥ 2
      （原式 WATERMARK_HYSTERESIS_PP < (DRAIN − WARN) 是**上界**，防遲滯吃掉整個帶而讓狀態機
        失去鑑別力；新式的上界同型——dwell 不得長於「reset 之後最壞多久才會有人動作」；
        新增的下界防的是另一個方向：dwell 短於量測週期＝遲滯結構上無效。理由見 §4.2.4）
5.  【v2.1.8 改寫】控制不得比量測快 ⇒ FANOUT_WINDOW_SECONDS ≥ QUOTA_CACHE_TTL_SECONDS
      且 FANOUT_WINDOW_SECONDS ≥ 2 × median(單一 Step 牆鐘秒數)（後者為量測值，現查；見 §4.2.4 (e)）
      （原式 CONTROL_INTERVAL_SECONDS ≥ MONITOR_POLL_INTERVAL_SECONDS 的等價物；同一件事——
        對尚未反映在用量上的決策重複反應＝積分飽和）
6.  COMPACT_COST_BUDGET_PP < (DRAIN − WARN)
7.  AUTH_MODE=API_KEY → API_BUDGET_HARD_USD 必須有值
7b. OVERAGE_POLICY=ALLOW_WITH_CAP → OVERAGE_HARD_CAP_USD 必須有值，否則拒絕啟動
7c. PACING_MODE=PACE_INDEX → 各 PACE_CEILING 需滿足 THROTTLE < DRAIN 且均 > 1.0
8.  ALLOW_PERMISSION_BYPASS=true → 必須偵測到容器/VM 環境，否則拒絕啟動
9.  Git repo 存在、工作區乾淨或已確認、.autoclaude/ 已在 .gitignore
10. 至少一個遙測來源可用；防休眠驅動可用（若需要）
11. 【v2.1.8 新增，見 §6.2 R-6.2-1】待整合佇列**可讀**（讀不出即明確回報「狀態不明」，
      不得靜默視為 0 筆）；CONFLICT_POLICY 值落在合法枚舉內；【v2.1.9】每一筆 integration_queue
      項的 `status` 亦須落在 §7 定義的枚舉內（`PENDING_VERIFY|CONFLICT|VERIFY_FAILED|MERGED`），
      未知字面**視為讀不出來**而非略過——略過等於把一筆殘留整合靜默丟掉
12. 【v2.1.8 新增，見 §6.2 R-6.2-2】`claude --version` 可讀且落在 git-tracked 的已驗證清單內；
      否則以 DRY_RUN 啟動並 loud 一次（**不阻止啟動**——CLI 一升版就整套停擺的守衛會被關掉）
13. 【v2.1.8 新增，見 §6.2 R-6.2-3】可用空間 ≥ 本次預估凍結寫入位元組數 + 常數餘裕；
      不足 → 清理**已 --ff-only 併入**的 worktree 後重測；仍不足即 loud（不得只印一行 log）
違反 → 明確錯誤訊息 + 非零退出碼；不得以預設值靜默帶過
🔴 例外只有第 12 條（未知 CLI 版本 → DRY_RUN 而非拒絕啟動），且該例外必須 loud；
   其餘各條違反一律拒絕啟動。
```

---

### 6.2 開機自檢：把「長駐管家才做得到的事」塌成「醒來時做一次」（v2.1.8 修憲）

**立案**：§8-11／§8-13／§8-14 三列的原條文都以「長駐 Daemon ＋ 多 worktree 生命週期管理」
為前提——有一個永遠活著的行程，可以在任意時點做家事。本 repo **刻意不做 Daemon**（§15.3
的「薄治理層 + 採用原生能力」；喚醒改由 OS 排程重啟，見 §4.5.5 與 ADR-XPLAT-004 §2.3）
⇒ 那個前提在本實作裡不存在。

🔴 **三項的意圖全部保留，只換實現**。不得把它們標成「架構性不適用」而刪掉——那是把意圖
跟實現一起丟掉。塌成的形態是**開機自檢**：原本「持續看著」的事，改成「每次醒來看一次」，
掛在 §6.1 既有的啟動自檢不變式那一層（違反 → 明確錯誤訊息 + 非零退出碼，不得以預設值
靜默帶過）。

> **為什麼「醒來時做一次」在覆蓋面上不弱於長駐管家**：本實作的執行單位就是「一次被排程
> 叫起來的行程」。長駐管家的價值在「事件發生的那一刻就處置」，而這三項要處置的事
> （沒做完的整合、CLI 換版、磁碟滿）**下一次派工之前處置就夠了**——它們都不是必須在
> 毫秒內反應的事。真正必須即時的那一類（撞線喚醒）本 repo 走的是另一條路（§4.5.6~§4.5.8
> 的哨兵巡邏），不在本節射程。

#### R-6.2-1（§8-11 意圖保留：沒做完的整合，醒來時掃一次並重排）

- **原意圖**：整合驗證失敗 → 退回佇列並記錄；`CONFLICT_POLICY` 決定是否派 Agent 修復
  （並計入額度預算）。
- **原實現前提**：有一個 Daemon 持有整合鎖、序列化跑佇列（§4.4.2）。
- **新實現**：佇列本身改為**磁碟上的狀態**，住 state.json 的既有結構（§7）——不新開一個檔
  （一份檔一個寫者，同 §4.5.6 R-4.5.6-3）。啟動自檢時掃一次：任何 status 落在**待處理集合**
  的整合項，依 `CONFLICT_POLICY` 重排；`CONFLICT_POLICY=HUMAN_REVIEW`（出廠值）者
  **不自動重排**，只在自檢輸出裡逐項列出並要求人工處置。**【v2.1.15 補述】** 三值各一種
  行為：`RETRY_WITH_AGENT` ⇒ 重排（`DRAINING` 以上與 DRY_RUN 改只登記）；`HUMAN_REVIEW` ⇒
  只登記；`ABORT` ⇒ **拒絕啟動**（非零退出碼、清單照列、零重排、零 worktree 寫入）——它是
  使用者顯式 opt-in 的硬停，與不變式 12「CLI 版本未知不阻止啟動」（防守衛被整個關掉）方向
  相反是刻意的：前者是人選的策略，後者是系統被動漂移。

- 🔴 **待處理集合的枚舉（v2.1.9 訂正；此前寫錯，且錯法會讓 G1 結構性假綠）**：

  | status 字面 | 出處 | 語意 | 在待處理集合內？ |
  | :---- | :---- | :---- | :---- |
  | `PENDING_VERIFY` | **§7 schema 的既有值**（該節 `integration_queue` 範例逐字唯一出現過的字面） | 已入列、驗證尚未跑完 | ✅ **必須在**（見下） |
  | `CONFLICT` | §4.4.2 步驟 2 逐字（`衝突 → 標記 CONFLICT`） | rebase 衝突，待 `CONFLICT_POLICY` 決定 | ✅ |
  | `VERIFY_FAILED` | 本次修憲新增；§8-11 原文「整合驗證失敗 → 退回佇列」的那個狀態此前沒有字面 | 驗證跑完且失敗 | ✅（同時進 §7，見下） |
  | `MERGED` | 本次修憲新增（終態，補齊枚舉才使「不在集合內」有意義） | 已 `--ff-only` 併入 integration | ❌ 終態 |

  ⇒ **§7 的 `integration_queue.status` 枚舉同步定義為 `PENDING_VERIFY | CONFLICT |
  VERIFY_FAILED | MERGED`**（見該節「Schema 設計要點」新增列）。本次**不引入** `QUEUED`：
  它與 `PENDING_VERIFY` 語意重疊，而 §7 已經有後者 ⇒ 引入前者等於給同一個狀態開第二個家，
  並需要一次沒有必要的資料遷移。

- 🔴 **為什麼這一格是「結構性假綠」而不是筆錯字**（立案逐字，v2.1.9）：原條文的掃描集合是
  `{QUEUED, CONFLICT, VERIFY_FAILED}`，而 `QUEUED` 與 `VERIFY_FAILED` 在**全 PRD 只出現在
  本次新增的文字裡**（`grep -n` 實查：僅 §6.2 條文與 G1 兩處），§7 schema 唯一定義過的字面
  是 `PENDING_VERIFY`。照原條文實作 ⇒ 生產環境的殘留項全帶 `PENDING_VERIFY`、掃出 **0 筆**，
  而 G1 的判準是「注入 `QUEUED` 必須被掃到」⇒ **測試綠、生產零覆蓋**。這正是本 repo 反覆
  記載的「注入值與生產真的會寫出來的值不同」那一族。
  ⇒ **規範性要求**：G1（與任何以注入殘留項為輸入的測試）的注入值**必須是生產路徑真的會
  寫出來的那個字面**。判準是可查的：注入值必須取自 §7 schema 的枚舉，不得是測試自己造的
  字串。
- 🔴 **重排必須先過額度閘**：重排會派工、派工會燒額度。啟動當下若已在 `DRAINING` 以上
  （本實作的等價述詞＝`band ∈ (prepare, halt)`，唯一對映登記在
  `tools/lib/quota_gate.py::DRAINING_BANDS`），**只登記不重排**——這是 §4.4.2 逐字既有的
  「在 `DRAINING` 以上狀態禁止啟動衝突解決任務」，此處只是把它接到開機這一刻。
- 🔴 **「掃一次」不得變成靜默的「掃 0 筆」**：佇列讀不出來（檔不存在／schema 不符／
  checksum 失敗）與「佇列是空的」必須**分開回報**（同本 repo 通篇「量不到 ≠ 量到零」）。
  讀不出來 ⇒ 依 §8-4 既有的 checksum 回退路徑處理，並在自檢輸出明說「佇列狀態不明」，
  **不得**印成「0 筆待整合」。

#### R-6.2-2（§8-13 意圖保留：CLI 版本相容性在啟動時判一次）

- **原意圖**：CLI 版本升級破壞相容性（旗標／輸出格式改變）⇒ 啟動時記錄 CLI 版本並比對已
  驗證清單；未知版本 → 進入 `DRY_RUN` 並要求人工確認。
- 這一列的原條文**本來就寫「啟動時」** ⇒ 意圖與「開機自檢」形態原生相容。本節補的是它
  缺的三件事：
  1. **版本從哪裡讀**：`claude --version`（唯讀、零 token）。讀不到版本字串 ⇒ **視為未知
     版本**。🔴 不得因為讀不到就當成已驗證——那是 fail-open，而失效外觀與「版本沒變」相同。
  2. **已驗證清單住哪**：一份 repo 內、**git-tracked** 的清單（人可讀、可 review、隨 clone
     走），不是本機狀態檔。本機檔不隨 clone 走 ⇒ 換一台機器就變成「全部未知」或「全部已
     驗證」，兩種都錯。附錄 B 已把「核實來源是實作內部字串，不是官方文件承諾的公開介面」
     寫成前提 ⇒ 清單必須帶「**這一版核實過什麼**」欄位，不能只有版號（只有版號的清單在
     下一次介面變動時給不出任何判斷依據）。
  3. **`DRY_RUN` 的語意必須是真的不動作**：未知版本下不得派工、不得寫 worktree、不得註冊
     排程；只做觀測與自檢輸出。
- 🔴 **未知版本不阻止啟動**（阻止啟動＝CLI 一升版就整套停擺，那種守衛會被整個關掉，比沒有
  守衛更糟），但必須 **loud**：走 §4.5.7 R-4.5.7-3 的桌面通道一次，並在自檢輸出印出「本次
  以 DRY_RUN 執行」與確認方式。

#### R-6.2-3（§8-14 意圖保留：可用空間在啟動與凍結前各檢一次）

- **原意圖**：磁碟空間不足（worktrees 與記錄檔累積）⇒ 啟動與凍結前檢查可用空間；不足則
  清理已合併 worktree 並告警。
- 這一列的原條文**本來就寫「啟動與凍結前」** ⇒ 同樣原生相容。本節補的是它缺的四件事：
  1. 🔴 **凍結前那一次是寫 patch 的硬前置**：§8-8／R-4.5.9 的救援序列會寫 patch 檔，而
     **磁碟滿正是它最可能的失敗成因** ⇒ 空間檢查必須在寫 patch **之前**，不是之後。順序
     錯了，這道檢查在它唯一要治的情境下根本不會被跑到（本 repo 反覆記載的「機制蓋好沒
     接電」的一種）。
  2. **門檻不得只看百分比**：要比的是「本次凍結預估要寫多少 bytes」對「可用 bytes」。
     預估來源＝各 worktree `git diff HEAD --binary` 的位元組數（唯讀、零 token）＋
     state.json 與其 `STATE_RETAIN_VERSIONS` 份保留版本的大小 ＋ 一個常數餘裕。
     百分比門檻在小容量磁碟上太鬆、在大容量磁碟上太緊。
  3. **清理只准動「已合併」的 worktree**：判準是「該分支已 `--ff-only` 併入 integration」
     （§4.4.2 步驟 4 的既有出口），**不是** mtime、**不是**目錄大小。🔴 清理動作本身受
     鐵律五管：不得用 `git clean`／`git reset --hard`；移除 worktree 走
     `git worktree remove`（§4.4.2 步驟 5 的既有動詞）。
  4. **清理後仍不足** ⇒ 這是 R-4.5.9 驗證失敗的**前置警報**，直接走 `DIRTY_UNSAVED` 那條
     路的桌面通知通道 loud 一次，不得只印一行 log。

#### R-6.2 三項共同的驗收判準（全部可機械查證）

| # | 判準 | 查證方式 |
| :---- | :---- | :---- |
| G1 | 佇列有殘留項時，啟動自檢**真的**重排（不是只印一行） | 整合測試：注入 `status=PENDING_VERIFY` 一筆 ⇒ 斷言重排動作發生。🔴 注入值刻意用 **`PENDING_VERIFY`**（§7 schema 既有、生產路徑真的會寫出來的那個字面）而不是 `QUEUED`——後者在本實作沒有寫者，注入它會讓本列**測試綠而生產零覆蓋**（立案見 R-6.2-1 末段）。**遍歷要求**：待處理集合的**每一個**字面各注入一次（`PENDING_VERIFY`／`CONFLICT`／`VERIFY_FAILED`），漏一個就是漏一種殘留項。**控制組兩格**：(i) `CONFLICT_POLICY=HUMAN_REVIEW` ⇒ 不重排但必須逐項列出；(ii) `status=MERGED`（終態）⇒ **不得**被掃出來重排。**【v2.1.15】再加兩格**：(iii) `CONFLICT_POLICY=ABORT` ＋ 有殘留項 ⇒ 自檢 `problems` 非空（拒絕啟動）、清單照列、零重排；空佇列 ⇒ 照常放行；(iv) `RETRY_WITH_AGENT` 在 `DRAINING` 以上或 DRY_RUN ⇒ 改只登記（既有 G3／G5 的同一判準） |
| G2 | 佇列讀不出來 ≠ 0 筆 | 單元測試：注入壞 checksum ⇒ 輸出含「狀態不明」，且**不得**含「0 筆」。**這一格是本節最容易寫成假綠的地方** |
| G3 | 啟動當下已在 `DRAINING` 以上 ⇒ 只登記不重排 | 單元測試（注入 band=prepare／halt 兩例） |
| G4 | `claude --version` 讀不到 ⇒ 視為未知版本並進 DRY_RUN（fail-safe） | 單元測試（讀取失敗注入）。**紅綠自證**：把它改成「讀不到就當已驗證」必須轉紅 |
| G5 | DRY_RUN 真的不動作 | 整合測試：斷言零派工、零 worktree 寫入、零排程註冊 |
| G6 | 已驗證清單是 git-tracked 檔 | 靜態判準：`git ls-files` 命中該路徑（本機狀態檔會落空 ⇒ 紅） |
| G7 | 空間檢查發生在寫 patch **之前** | 單元測試：以呼叫順序斷言（mock 兩支，比對呼叫序）。順序反了必須紅——這正是本條的全部價值 |
| G8 | 門檻是 bytes 對 bytes | 單元測試：同一個「可用百分比」下，預估寫入量大／小兩例必須得到不同判定 |
| G9 | 清理只動已 `--ff-only` 併入者，且不使用 `git clean`／`reset --hard` | 整合測試（未合併分支必須留下）＋ 靜態詞彙掃描（判準形態同鐵律五 hook） |
| G10 | 清理後仍不足 ⇒ 桌面通知恰好一次 | 單元測試（mock 通知器） |

## 7. 狀態資料結構規格（state.json schema v2）

修正 v1 的問題：單一 worktree/session 欄位（與多 Agent 矛盾）、非法 SHA 長度、`reset_timestamp` 與 `saved_at` 相距 24 小時（5 小時視窗不可能）、缺少校驗與續作指令的安全問題。

```json
{
  "schema_version": "2.0.0",
  "checksum_sha256": "<除本欄位外之序列化內容的 SHA-256，用於偵測半寫入>",
  "saved_at": "2026-08-14T10:52:00+08:00",
  "saved_at_epoch": 1786675920,
  "reason": "U5H_HALT_REACHED",
  "reason_detail": "u5h=95.2 >= halt=95.0",
  "daemon": {
    "daemon_id": "d-7f3a91",
    "pid": 48213,
    "version": "2.0.0",
    "host": "macbook-pro-dev",
    "project_root": "/Users/dev/orders-api",
    "dry_run": false
  },
  "quota_snapshot": {
    "auth_mode": "OAUTH",
    "telemetry_source": "T1_OTEL",
    "is_local_estimate": false,
    "u5h_percent": 95.2,
    "u7d_percent": 68.4,
    "u7d_high_tier_model_percent": 41.0,
    "reset_at": "2026-08-14T13:00:00+08:00",
    "reset_timestamp": 1786683600,
    "weekly_reset_at": "2026-08-18T09:00:00+08:00",
    "weekly_reset_timestamp": 1787014800,
    "observed_burn_rate_pct_per_min": 0.42
  },
  "agents": [
    {
      "agent_id": "agent-1",
      "session_id": "6f1c9d84-2b7e-4a03-9c51-8ad30f6b2e77",
      "model": "<實際使用的模型識別字串>",
      "worktree_path": ".autoclaude/worktrees/agent-1",
      "git_branch": "autoclaude/agent-1-r0042",
      "base_sha": "3c1e77a95b40d2f8ae61c04b9d7f2513ab8e6c90",
      "checkpoint_sha": "a8f3b4c91023d8e9f0c7b21d4e5a6f7089c3d1b2",
      "working_tree_clean": true,
      "context_utilization_percent": 62.5,
      "transcript_estimated_tokens": 48210,
      "termination": "GRACEFUL",
      "assigned_step": 3
    }
  ],
  "task_state": {
    "task_id": "TASK-2026-088",
    "dag": {
      "nodes": [
        { "step": 1, "title": "DB Schema Migration",            "deps": [] },
        { "step": 2, "title": "Implement Repository",            "deps": [1] },
        { "step": 3, "title": "Build REST Controller & Tests",   "deps": [2] },
        { "step": 4, "title": "E2E Integration Test",            "deps": [3] },
        { "step": 5, "title": "Update API Docs",                 "deps": [3] }
      ]
    },
    "total_steps": 5,
    "completed_steps": [
      { "step": 1, "status": "COMPLETED", "completed_at": "2026-08-14T09:14:00+08:00", "quota_cost_pp": 8.1 },
      { "step": 2, "status": "COMPLETED", "completed_at": "2026-08-14T10:02:00+08:00", "quota_cost_pp": 12.4 }
    ],
    "interrupted_steps": [
      {
        "step": 3,
        "status": "PAUSED_AT_QUOTA_LIMIT",
        "agent_id": "agent-1",
        "progress_note": "controller 骨架與 3/8 單元測試已完成；剩餘測試未撰寫",
        "files_modified": ["src/controllers/order.controller.ts"],
        "files_pending": ["test/order.controller.spec.ts"],
        "verification_status": "TESTS_NOT_RUN",
        "quota_cost_pp_so_far": 21.7
      }
    ],
    "remaining_steps": [4, 5],
    "blocked_steps": []
  },
  "resume_plan": {
    "strategy": "AUTO_RESOLVED_TO_SESSION_RESUME",
    "strategy_reason": "transcript_tokens=48210 <= threshold=60000",
    "not_before": "2026-08-14T13:00:30+08:00",
    "prompt": "額度已重置。請讀取 .autoclaude/state.json，從 interrupted_steps 繼續；先執行 npm test 確認現況，再補齊 test/order.controller.spec.ts。",
    "permission_mode": "acceptEdits",
    "allowed_tools": ["Read", "Edit", "Write", "Bash(npm test:*)"],
    "max_turns": 40,
    "retry_count": 0,
    "max_retries": 5
  },
  "integration_queue": [
    { "agent_id": "agent-1", "branch": "autoclaude/agent-1-r0042", "status": "PENDING_VERIFY" }
  ]
}
```

**Schema 設計要點**
- `resume_plan` 只存**參數**，不存可直接執行的完整 shell 命令字串。v1 把 `resumption_command` 存成完整命令（含引號內的中文提示）會有 shell 注入與引號轉義風險，且讓 state.json 從資料變成可執行碼。
- `agents` 為陣列；每個 Agent 有自己的 session、分支、checkpoint。
- 記錄 `quota_cost_pp`：累積實際成本資料，可用於「Step 額度預算」的自適應校準。
- 【v2.1.9 新增】`integration_queue[].status` 的枚舉為 **`PENDING_VERIFY | CONFLICT | VERIFY_FAILED | MERGED`**（前三者＝§6.2 R-6.2-1 的「待處理集合」，`MERGED` 為終態）。上方範例的 `PENDING_VERIFY` 是這個枚舉的成員，不是自由字串。🔴 枚舉必須在**這一節**定義而不是散落在各節條文裡：§6.2 的掃描集合、§6.1 不變式 11 與 §11.6 的驗收都以它為分母，分母若沒有單一的家，各處各抄一份的漂移方向是**漏抄**（本次修憲即因此把不存在的 `QUEUED` 寫進掃描集合，見 R-6.2-1）。
- `checksum_sha256` + 原子寫入：防止在凍結途中斷電造成半寫入而無法恢復。
- SHA 使用完整 40 字元十六進位（v1 的 16 字元非法）。
- 時間同時提供 ISO 8601（含時區）與 epoch，且兩者必須一致（v1 範例不一致）。

---

## 8. 例外與邊界條件（擴充）

| # | 異常事件 | 觸發情境 | 防禦機制 |
| :-- | :---- | :---- | :---- |
| 1 | **非預期 429** | 遙測落後於真實用量，或其他裝置同時消耗 | 優先**遵循回應中的重試建議標頭**；無標頭時採 full jitter 退避：`sleep = rand(0, min(300, 10·2^n))`，最多 5 次。v1 的固定 10/30/90s 無 jitter，多 Agent 同時撞牆會同步重試造成雷群。重試耗盡 → `FREEZING`。**且必須把 429 視為遙測低估的證據**，將 `U5h` 推估值上修 |
| 2 | **重置時間漂移** | 後端重置延遲 | **【v2.1.8 修憲，全文見 §4.5.10】** 觀測優先：醒來重新觀測 `U5h < RESET_CONFIRM_PERCENT`；確認不了**既不猜也不終止**，掛回零成本哨兵巡邏兜底重試（掛點＝`tools/session_resume_planner.py --arm-sentinel`）。**原條文的固定級距（30s→300s、最多 10 次）已降級**為「單次量測失敗」的重試（≤3 次／≤90s，🔴 **【v2.1.9】射程限於「同一次醒來的行程內」**——跨醒來的重排間隔是另一層，家＝既有常數 `tools/session_resume_planner.py::TRANSIENT_RETRY_SECONDS`，兩層不得折成一個數字），不再是「等 reset」的主路——固定級距是在猜 reset 時刻，與「reset 只能觀測不能算」直接衝突。例外：月度支出上限仍 `escalate`（等不回來） |
| 3 | **Git index.lock 殘留** | 中斷時 git 操作未完成 | 檢查鎖檔 **mtime 與持有 PID 是否存活**；僅清理確認陳舊者。v1 的「清理陳舊鎖」若無存活檢查，可能刪掉正在使用的鎖而毀損 repo |
| 4 | **斷電／強制重啟** | — | `INIT` 掃描 state.json + checksum 驗證；提供 `autoclaude resume` 與 `--force-fresh`。若 checksum 失敗 → 回退到 `AUTOCLAUDE_STATE_RETAIN_VERSIONS`（【v2.1.15】前綴對齊全庫慣例，出廠值 5）中最近的有效版本 |
| 5 | **【新增】機器在等待中睡著** | 防休眠失效 / Modern Standby | 醒來偵測時鐘跳躍 → 立即重新輪詢 → 若已過重置點直接 `RESUMING`；記錄防休眠失效事件並告警 |
| 6 | **【新增】遙測來源永久失效** | 未公開端點被移除、記錄檔格式變更 | **【v2.1.8 修憲，全文見 §4.1.5】** 依 `TELEMETRY_SOURCE_ORDER` 降級；全部失效 → **cap 收斂到 `cap_prepare` 語意**（且 ≥1，禁止靜默鎖死）＋ 告警，**絕不**猜測用量繼續派工。原文寫 `DRAINING` 是**狀態機的字**，本實作只有 band + cap 且實測 `degraded_cap == cap_converge` 為 `True`、`draining()` 對 `unmeasured` 明文回 `"unknown"` ⇒ 原條文在本實作結構上沒有可達路徑。🔴 `band` 必須繼續是 `unmeasured`（「量不到 ≠ 量到零」只禁造假讀數，不禁收緊） |
| 7 | **【新增】同帳號多 Daemon 超燒** | 兩個專案同時跑 | §4.7 帳號配額仲裁鎖 + 租約 |
| 8 | **【新增】Worktree 有未提交變更且無法提交** | 檔案權限、pre-commit hook 失敗 | **【v2.1.8 修憲，全文見 §4.5.9】** 救援序列**只有一個動作且不動工作樹**：產生 patch 檔存入 `AUTOCLAUDE_CHECKPOINT_DIR`，**寫完必須重新開檔讀回並驗 SHA-256**（＋位元組數相等、＋非空、＋**覆蓋率**、＋第二道語意閘）；🔴 **【v2.1.9】patch 的母體是「tracked 變更 ∪ untracked 新檔」**——`git diff HEAD` 從不含 untracked，只用它會讓四道斷言全綠而全新工作被靜默丟掉（實測 patch `135` bytes 非空、`grep -c` 目標檔名 `0`）；第二道語意閘走「臨時索引 read-tree 到記錄的 `base_sha` ＋ `apply --check --cached`」，天真寫法在髒工作樹上實測恆紅；任一不成立 → fail-loud 進 `DIRTY_UNSAVED`（state.json 帶齊四個可重驗值 ＋ 桌面通知一次 ＋ 禁止自動喚醒），**絕不** fail-open 轉入 `WAITING_RESET`／`LONG_HIBERNATE`。原條文前兩步（`commit --no-verify`、`git stash`）**已刪除**——本 repo 憲法直接禁止（鐵律五機械阻斷 stash 全族；`--no-verify` 為逐字禁止事項） |
| 9 | **【新增】Agent 無回應／卡死** | 等待外部指令、無限循環 | 硬性預算逾時 → 優雅終止序列；連續 `N` 次卡死同一 Step → 標記 `NEEDS_HUMAN` |
| 10 | **【新增】喚醒後上下文已不可用** | session 記錄被清理、CLI 升級不相容 | 自動降級為 `FRESH_SESSION_WITH_STATE`；此為 `SESSION_RESUME` 的必備退路（v1 無退路） |
| 11 | **【新增】整合驗證失敗** | 測試在合併前不通過 | 退回佇列並記錄；`CONFLICT_POLICY` 決定是否派 Agent 修復（並計入額度預算）。**【v2.1.8 修憲，全文見 §6.2 R-6.2-1】** 原實現前提（長駐 Daemon 持整合鎖）在本 repo 不存在 ⇒ **意圖保留、實現換成開機自檢**：佇列住 state.json，醒來時掃一次殘留項並重排；`DRAINING` 以上只登記不重排；**讀不出來必須回報「狀態不明」，不得印成「0 筆」**。掛 §6.1 不變式 11。**【v2.1.15】** `ABORT` ⇒ 有殘留項即拒絕啟動（見 R-6.2-1 補述） |
| 12 | **【新增】Prompt injection** | Agent 讀入 repo 中含惡意指令的檔案／依賴 | 工具白名單 + 寫入範圍限制在 worktree + 禁止未經確認的網路存取；Daemon 對 Agent 產出的「狀態回報」做 schema 驗證，不直接信任自然語言 |
| 13 | **【新增】CLI 版本升級破壞相容性** | 旗標／輸出格式改變 | 啟動時記錄 CLI 版本並比對已驗證清單；未知版本 → 進入 `DRY_RUN` 並要求人工確認。**【v2.1.8 修憲，全文見 §6.2 R-6.2-2】** 本列原文已是「啟動時」形態 ⇒ 意圖不動，補齊三件缺項：版本讀自 `claude --version`（讀不到＝未知，**不得** fail-open）、已驗證清單須為 **git-tracked** 且帶「這一版核實過什麼」欄位、`DRY_RUN` 必須真的零派工／零 worktree 寫入／零排程註冊。未知版本**不阻止啟動**但必須 loud。掛 §6.1 不變式 12 |
| 14 | **【新增】磁碟空間不足** | worktrees 與記錄檔累積 | 啟動與凍結前檢查可用空間；不足則清理已合併 worktree 並告警。**【v2.1.8 修憲，全文見 §6.2 R-6.2-3】** 本列原文已是「啟動與凍結前」形態 ⇒ 意圖不動，補齊四件缺項：凍結前那一次是**寫 patch 的硬前置**（順序錯了這道檢查在它唯一要治的情境下跑不到）、門檻改為 **bytes 對 bytes**（不是百分比）、清理**只准動已 `--ff-only` 併入**者且不得用 `git clean`／`reset --hard`（鐵律五）、清理後仍不足即桌面通知。掛 §6.1 不變式 13 |

---

## 9. 可觀測性（v1 完全缺漏）

**必要指標**（供事後調參與事故分析）

| 指標 | 型別 | 用途 |
| :---- | :---- | :---- |
| `autoclaude_u5h_percent` / `autoclaude_u7d_percent` | gauge | 額度趨勢 |
| `autoclaude_burn_rate_pct_per_min{kind="safe\|actual"}` | gauge | 配速器是否貼合預算 |
| `autoclaude_concurrency{kind="target\|actual"}` | gauge | 控制器行為 |
| `autoclaude_state` | gauge (enum) | 狀態滯留時間分析 |
| `autoclaude_state_transitions_total{from,to,reason}` | counter | 抖動偵測（同一組 from/to 高頻 → 遲滯參數不足） |
| `autoclaude_telemetry_age_seconds{source}` | gauge | 遙測健康度 |
| `autoclaude_step_quota_cost_pp` | histogram | 校準 `MAX_STEP_QUOTA_PP` |
| `autoclaude_step_wall_seconds` | histogram | **【v2.1.8 新增】** §4.2.4 (e) 的不變式（控制週期 ≥ 2× Step 中位牆鐘時間）需要這個中位數才驗得起來；沒有它，該不變式只有前半（`FANOUT_WINDOW_SECONDS ≥ QUOTA_CACHE_TTL_SECONDS`）是可查證的 |
| `autoclaude_availability_flips_total` | counter | **【v2.1.8 新增】** measured⇄unmeasured 翻動次數。§4.2.4 把遲滯改掛這一軸，而遲滯有沒有生效**唯一**能看的就是這個計數在遲滯上線前後的變化（立案母體＝本包實測 12 小時 19 次） |
| `autoclaude_resume_cost_pp` | histogram | 量化喚醒成本，驗證 `RESUME_STRATEGY` 門檻 |
| `autoclaude_429_total` | counter | 遙測低估的直接證據 |
| `autoclaude_freeze_duration_seconds` | histogram | 等待時間佔比（效率指標） |
| `autoclaude_integration_outcome_total{result}` | counter | 合併成功率／衝突率 |

**結構化日誌**：每次決策輸出一行 JSON（含所有輸入變數與決策理由），使任一決策皆可重現。**憑證與 token 一律遮蔽**。

**告警**：狀態升級至 `DRAINING` 以上、`LONG_HIBERNATE`、遙測全失效、`DIRTY_UNSAVED`、`NEEDS_HUMAN`、429 突增。

---

## 10. v1 → v2 設定遷移對照

| v1 設定 | v2 處置 | 說明 |
| :---- | :---- | :---- |
| `TOKEN_COMPACT_PERCENT=90` | **廢除** → `CONTEXT_COMPACT_PERCENT` | 語意由「額度 %」改為「上下文佔用 %」，兩者不可互換 |
| `WEEKLY_LIMIT_HALT_PERCENT` | 更名 `WEEKLY_HALT_PERCENT`，並新增 WARN/DRAIN 兩級 | v1 只有單一硬停，缺少漸進收斂 |
| `BURNING_RATE_WINDOW_MINUTES=15` | 保留但預設不使用；改由 `BURN_RATE_EWMA_ALPHA` 控制 | 固定視窗在重置時會產生假訊號 |
| `OS_KEEP_AWAKE_DRIVER=MACOS_CAFFEINATE` | 預設改 `AUTO`，新增 `LINUX_SYSTEMD` | 硬編碼平台會使 Linux/WSL 使用者無防護 |
| `AUTOCLAUDE_ACCOUNT_TYPE` | 保留為提示性欄位 | 不得用於推算額度上限；一律以遙測為準 |
| `resumption_command`（state.json） | 改為結構化 `resume_plan` | 避免 shell 注入與轉義問題 |

**升級程序**：Daemon 讀到 `schema_version: "1.0.0"` 的 state.json 時，執行一次性遷移（補齊 `agents` 陣列、重算 checksum、清除 `resumption_command`），備份原檔至 `checkpoints/`。

---

## 11. 驗收與測試標準（改為可量測，並解決 v1 的矛盾）

### 11.1 零 Token 遙測驗證
- **方法**：啟動 Daemon 於純遙測模式（`DRY_RUN=true`）連續運行 6 小時，不派任何工。
- **判準**：期間 `U5h` 相對於獨立取得的權威用量讀數，增量為 **0**；本機對話記錄檔的 token 加總無新增。
- 若啟用了未公開端點，額外驗證：關閉該端點後系統能自動降級且不中斷。【v2.1.4 指針（R95 修復包補注，納入殘留面清單）：「若啟用了」的措辭寫於 T5 仍為選用時；v2.1.4 起 T5 已升格認可主源（§4.1.1），本條驗證項自此**必做**而非條件式——降級行為即紅線 1 豁免條件 (d)】

### 11.2 配速控制器（以模擬器測試，不燒真實額度）
必須提供**離線模擬器**（餵入合成的 `U5h/U7d/T_rem` 時間序列），對 §4.2.7 的 7 個情境做斷言。額外性質測試：
- **無抖動【v2.1.8 改寫】**：原判準「`U5h` 於 68%–72% 隨機遊走 60 個控制週期，`THROTTLING ⇄ CRUISING` 轉移次數 ≤ 3」在本實作**量不到它要防的病**——本包當回合對 `~/.autosdd/traces/quota_burn.jsonl` 全量重放（十天、119 筆、8 軸、819 個逐軸讀數）得 `band_changes=77 up=44 down=33 down_of_which_window_resets=33` ⇒ **小幅擺動反轉 0 次**（視窗內 usage 單增，結構上不可能來回穿越門檻）。改為掛在真的會抖的那一軸（同期痕跡合併實測：12 小時內 measured⇄unmeasured 翻動 **19** 次）：
  以**實測形態**序列 `UMMMUMMMMUMUMMUMMUUUMMMMUMMMUUMUUMUMM`（本包從 burn ledger ＋ `autosdd_quota_degraded.jsonl` 按時間合併算出；機械現查 **37 個符號、19 次翻動**）**＋每個符號一個時間戳**為輸入，斷言「開啟遲滯」的 cap 變動次數 **嚴格小於**「關閉遲滯」者；且不得出現任何一次「dwell 未滿就放寬」。🔴 母體刻意用實測形態而非合成隨機走——合成序列證明不了「這台機器真的會這樣抖」，那正是原判準失效的成因。🔴 **時間戳不可省（v2.1.9 補）**：後半那句「dwell 未滿就放寬」以**秒**為單位，而 37 個字元的序列不含任何時間資訊 ⇒ 只有前半（變動次數）驗得起來，後半會靜默變成沒人驗。母體形態、fixture 的家與其自帶不變式、痕跡不可得時的姿態，一律照 §4.2.4〈H1 的時間軸怎麼補〉（該處為唯一真相源，本節不複寫）。
- **無暴衝【v2.1.8 改寫】**：原判準「任何單一控制週期的併發增量 ≤ 1」的運算元（持久併發設定點）在本實作不存在。等價物：**放寬方向必經 band 階梯，不得跳級**——對每一對相鄰決策斷言 `cap_next` 不超過 `cap_prev` 的下一個較寬階梯；**收緊方向不設限**（安全方向，同 §4.2.4 (c) 的例外條款）。並補一格原判準沒有的：`unmeasured → measured` 是「沒有中間級」的躍遷 ⇒ 那一次的放寬必須同時滿足 `AVAILABILITY_EXIT_STREAK` 與 `AVAILABILITY_MIN_DWELL_SECONDS`。【v2.1.9 訂正】「**唯一**」一字已刪——measured 軸內部的 `notice → free`（有限 cap → `None` 不設限）同型，理由與該格由誰承重見 §4.2.4 (c) 的同名訂正。⇒ 本節的斷言母體因此必須**兩格都掃**：`unmeasured → measured` 走 streak ＋ dwell，`* → free` 走下一列（重置後不暴衝）的 `cap ≤ cap_notice`。
- **重置後不暴衝【v2.1.8 改寫】**：視窗翻頁（pct 跌幅 ≥ `RESET_DROP_THRESHOLD`）後第一次決策的 cap ≤ `cap_notice`；即**不設限（`BAND_FREE` 的 `None`）不得在翻頁後第一拍出現**。原判準的 `C_default` 在本實作沒有對應物，`cap_notice` 是最寬的**有限** cap。
- **收斂性**：模擬固定燃燒率下，併發在 10 個週期內收斂並穩定（不再變動）。
- **驗收標準 3b（v1 的矛盾點）**：`U5h = 75%` 時併發必定為 `AGENT_THROTTLE_CONCURRENCY`，**由 `C_cap` 保證，不依賴公式湊巧**。
- **fail-safe**：注入遙測中斷 11 分鐘 → 併發歸零；注入 429 → 用量推估上修且退避有 jitter。

### 11.3 凍結與喚醒
- 人工注入 95% 訊號，斷言：**5 秒內**完成所有 worktree 的 checkpoint 與 state.json 原子寫入，且 `git status` 在每個 worktree 皆為 clean。
- 在 state.json 寫入過程中 `kill -9` → 重啟後能以 checksum 偵測損壞並回退到上一有效版本。
- 喚醒後斷言：接續的是正確的 `interrupted_step`，且**記錄本次喚醒的實際額度成本**（`autoclaude_resume_cost_pp`）。此為 v1 未驗證的關鍵成本項。
- `SESSION_RESUME` 不可用時（刪除 session 記錄）能自動降級為 `FRESH_SESSION_WITH_STATE` 並完成任務。

### 11.4 週上限與長休眠
- 注入 `U7d = 92%` → 斷言進入 `LONG_HIBERNATE`、成功註冊 OS 排程任務、Daemon 退出、排程時間到能自行重啟並恢復。
- 斷言：週上限觸發時**不會**只休眠到 5 小時重置（v1 的缺陷）。

### 11.5 防休眠
- macOS（電池與接電源**兩種**情境）、Windows 11（含 Modern Standby 機型）、Linux：5 小時無操作掛機。
- 判準：`pmset -g assertions` / `powercfg /requests` / `systemd-inhibit --list` 顯示預期的 assertion；主機未進入睡眠；螢幕依設定關閉；Daemon 計時誤差 < 60 秒；Daemon 被 kill 後 assertion 在 10 秒內自動解除（無孤兒 caffeinate）。

### 11.6 多 Agent 隔離與整合
- 3 個 Agent 同時修改**有重疊 import 的相鄰模組**，斷言：無檔案互相覆蓋；整合佇列序列化執行；至少一次衝突能正確走 `CONFLICT_POLICY`；所有 worktree 最終被清理（`git worktree list` 無殘留）。

### 11.7 多實例配額
- 同帳號同時啟動兩個專案的 Daemon，斷言：兩者併發總和不超過單一 Daemon 情境的上限；`U5h` 燃燒率不超過 `V_safe` 的 1.2 倍。

### 11.8 端到端（長時測）
- 24 小時連續運行，跨越至少 4 次 5 小時視窗重置。判準：0 次非預期任務截斷、0 次髒污工作區、`U7d` 未觸及 `WEEKLY_HALT`、有效工作時間佔比（非等待時間 / 總時間）達成設定目標。

---

## 12. 安全性（v1 完全缺漏）

| 面向 | 要求 |
| :---- | :---- |
| **憑證** | 【v2.1.4 劃界修正】允許**唯讀**本機憑證存放處（`~/.claude/.credentials.json`；macOS 為 login Keychain）取得 OAuth token，**僅限**作為呼叫 §4.1.1 T5 認可主源的必要前提，token 唯一去處＝該次請求的 `Authorization` 標頭；除此之外 Daemon 不得複製、轉發或記錄 OAuth token／API key 明文——token **禁止**寫入任何痕跡檔／日誌／快取／任務書。帳號識別一律使用不可逆雜湊。共享遙測快取只存用量數字，不存憑證 |
| **權限旗標** | 預設**不使用**完全跳過權限的旗標。改用權限模式 + 工具白名單。`ALLOW_PERMISSION_BYPASS=true` 需通過容器／VM 環境偵測才允許 |
| **寫入範圍** | 每個 Agent 只能寫入自己的 worktree；禁止寫入 `.git/`、`.env`、`~/.ssh`、`.autoclaude/state.json` |
| **Prompt injection** | repo 內容與第三方依賴皆視為不可信輸入。Agent 的狀態回報必須通過 schema 驗證後才寫入 state.json；不得讓 Agent 直接改寫 Daemon 的控制參數 |
| **命令執行** | 整合驗證命令來自設定檔而非 Agent 產出；state.json 不含可執行命令字串 |
| **日誌** | `REDACT_SECRETS_IN_LOGS=true`；對常見金鑰樣式做遮蔽 |
| **供應鏈** | Agent 不得在無人確認下新增依賴或執行 `postinstall`；建議整合驗證階段跑於離線／受限網路 |

---

## 13. 合規聲明（v1 缺漏，但對本類工具至關重要）

本系統的設計目標是**在額度限制內平順地運作**，並在達限時安全暫停。明確禁止並不予實作：

- 多帳號輪替、帳號池化、憑證共享，以規避單帳號限制。
- 任何形式的限流／計費繞過、請求偽裝。
- 對未公開介面的高頻探測（選用的 T5 來源必須遵守輪詢間隔且失敗即降級）。【v2.1.4 指針（R95 修復包補注，納入殘留面清單）：「選用的」三字寫於升格前；v2.1.4 起 T5 為認可主源（§4.1.1、§15.5 紅線 1 豁免四條件），「遵守輪詢間隔（TTL≥180s）且失敗即降級」的約束原文不變且已機械化】

`[需核對]` 實作前應確認：使用條款對「自動化使用」「未公開端點存取」的規定，以及訂閱制方案是否允許長時間無人看管的自動化運行。此為**上線前的必要檢核項**，非技術問題。

---

## 14. 實作路線圖（建議，v1 無此章）

> **v2.1 註**：本章為 v2.0 基於「大型自建 Daemon」假設所寫的路線圖。核實後建議架構已大幅縮減，**請以 [§15.4](#154-分階段執行步驟) 的階段規劃為準**；本章保留作為對照。

| 階段 | 範圍 | 出場條件 |
| :---- | :---- | :---- |
| **P0 觀測** | 遙測引擎（T1/T2）+ 可觀測性 + `DRY_RUN` | 能連續 24h 正確記錄 `U5h/U7d`，零 token 消耗；取得真實燃燒率分布以校準參數 |
| **P1 保全** | 凍結 / state.json v2 / 分片休眠 / 喚醒（單 Agent） | 通過 11.3；能自動跨越 5 小時視窗重置完成一個長任務 |
| **P2 配速** | 配速控制器 + 離線模擬器 + 平穩性機制 | 通過 11.2 全部性質測試 |
| **P3 並行** | Worktree 隔離 + 整合佇列 + 硬性預算 | 通過 11.6 |
| **P4 韌性** | 週上限長休眠 + 多實例仲裁 + 防休眠三平台 | 通過 11.4、11.5、11.7 |
| **P5 硬化** | 安全、API_KEY 模式、遷移工具 | 通過 11.8 與 §12 檢核 |

**強烈建議**：P0 必須先於 P2。v1 的配速參數（`C_default=2`、水位 70/85/95、15 分鐘視窗）**沒有經驗依據**；在取得真實燃燒率分布前，這些數字只是猜測。P0 的觀測資料應回頭校準所有預設值。

---

## 15. 執行方法論與注意事項（v2.1 新增）

> **本章回答：「v2 是否已完整涵蓋 v1？只執行 v2 即可嗎？」**
>
> **是。** v2 是 v1 的嚴格超集 —— v1 的七個章節（執行摘要、架構與狀態機、五個功能模組、`.env`、`state.json`、邊界條件、驗收標準）全部保留並擴充，沒有任何 v1 內容被刪除而未被取代。**只需執行 v2.1，v1 僅作為變更歷程存檔。**
>
> 唯一需要注意的**語意變更**：v1 的 `TOKEN_COMPACT_PERCENT=90` 在 v2 被廢除而非改名 —— 因為它的定義本身是錯的（見 §2）。若已有依此撰寫的程式碼，必須改寫而非改參數名。完整對照見 [§10](#10-v1--v2-設定遷移對照)。

### 15.1 動工前置檢查（15 分鐘，必做）

```bash
node --version                      # 必須 ≥ 22.0.0
claude --version                    # 記錄版本，寫入 README；本文核實基準為 2.1.232
git --version && git worktree list  # 確認 worktree 可用
```
另外必須人工確認三件本文無法代為驗證的事：

1. **方案類型與額度分軌**：執行 `/usage`，記下實際看到的額度項目（是否有「Current week (Sonnet only)」等分軌）。**不同方案看到的項目不同**，治理邏輯要依實際看到的來寫。
2. **使用條款**：確認方案允許長時間、無人看管的自動化運行。這是**法務問題不是技術問題**，且是唯一可能讓整個專案作廢的風險項。
3. **超額用量設定**：確認帳號目前是否啟用付費超額。若啟用，達到訂閱限制時**不會停止而會開始計費** —— 這會讓「凍結等待」邏輯永遠不觸發，卻默默產生帳單。**這是本專案最危險的單一失敗模式。**

### 15.2 「先採用、後自建」決策矩陣

每個模組動工前先問這三題，依序：

```
Q1. CLI 是否已有原生能力？（查 §0.6 表格 / sdk-tools.d.ts / --help）
      有 → 採用，只寫轉接層。停。
Q2. 是否能用 hook + settings.json 達成？（不需要常駐行程）
      能 → 用 hook。停。
Q3. 是否真的需要一個常駐 Daemon？
      需要的唯一正當理由：跨 session、跨專案的「帳號層級」決策。
      其餘一律不需要。
```
依此矩陣，**真正必須自建的只有四項**：

| 必建模組 | 為何無法用原生能力取代 | 規模估計 |
| :---- | :---- | :---- |
| 治理決策器（配速 + 狀態機） | 原生只有「示警」，沒有「依配速自動調整併發與模型」的決策邏輯 | ~400 行 + 測試 |
| 帳號層級配額仲裁（§4.7） | 額度是帳號共享，CLI 只看得到自己那個 session | ~150 行 |
| 跨 5 小時視窗的長等待與交棒（§4.5.5） | `ScheduleWakeup` 上限 3600 秒，撐不過 5 小時視窗 | ~200 行 |
| 治理層狀態持久化（縮減版 `state.json`） | 任務 DAG 交給原生 Task 工具後，只需存治理狀態 | ~100 行 |

其餘（worktree、任務 DAG、遙測、可觀測性、壓縮、子代理併發上限）**全部採用原生能力**。v2.0 規劃的自建規模因此縮減約 60%。

### 15.3 建議的最小可行架構（修訂後）

```
┌─────────────────────────────────────────────────────────────┐
│ statusLine hook (CLI 主動呼叫，零 Token)                     │
│   讀 stdin JSON → 抽出 rate_limits.* → 寫 governance.json    │
│   → 印出狀態列文字（順便給人看）                              │
└───────────────────────┬─────────────────────────────────────┘
                        │ 檔案（含 mtime 作為新鮮度）
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 治理決策器 (輕量常駐行程，或由 hook 觸發的無狀態函式)          │
│   讀 governance.json + 帳號仲裁鎖                             │
│   → 算 pace_index → 決定 (併發上限, 模型, 是否放行)            │
│   → 寫 .claude/settings.local.json 的 env 區塊                │
│      與 .autoclaude/governance-decision.json                 │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ PreToolUse hook (閘門)                                       │
│   Agent 工具被呼叫時 → 讀決策 → 超出配額則拒絕並回傳原因       │
│   這是「不派新工」最可靠的實作點：在工具層攔截，而非管行程     │
└─────────────────────────────────────────────────────────────┘
        ＋ PreCompact hook：壓縮前寫 checkpoint
        ＋ Stop / SubagentStop hook：回收 worktree、更新治理狀態
        ＋ OTel → Prometheus：所有指標
```
**關鍵洞察**：v2.0 假設治理層必須「管理多個 CLI 行程」。但用 `PreToolUse` hook 在 `Agent` 工具層攔截，加上調整 `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`，就能達到同樣的併發控制，**且不需要行程池、不需要 worktree 管理、不需要訊號處理**。這是本次核實帶來最大的簡化。

### 15.4 分階段執行步驟

每階段都是**可獨立交付、可獨立回滾**的，且順序不可調換。

#### P0 — 觀測（1–2 天）｜先量測，不控制
- 寫 statusLine 腳本：讀 stdin、抽 `rate_limits.five_hour.used_percentage` / `.resets_at` / `seven_day.*`、附加 `fetched_at`，原子寫入 `.autoclaude/governance.json`，並印出精簡狀態列。
- 開啟 `CLAUDE_CODE_ENABLE_TELEMETRY` + Prometheus exporter，接一個本地 Grafana。
- **正常使用 2–3 天，什麼都不控制。**
- **出場條件**：能畫出「利用率 vs 時間」曲線，並回答：一次典型 Step 燒掉多少百分點？週額度平均一天燒幾 %？`pace_index` 的實際分布長什麼樣？
- ⚠️ **不要跳過這階段直接做 P2。** v1 的所有參數（70/85/95、`C_default=2`、15 分鐘）都是猜的；P0 的資料是把它們變成有根據的唯一途徑。

#### P1 — 保全（2–3 天）｜先能安全停，再談能跑多快
- `PreCompact` hook 寫 checkpoint；`Stop` hook 更新治理狀態。
- 縮減版 `state.json`（原子寫入 + checksum）。
- 分片休眠 + 重置確認 + `ScheduleWakeup`／cron 交棒。
- **出場條件**：手動注入高水位訊號，能在 5 秒內落盤且工作區乾淨；重置後能自動接續；`kill -9` 途中能偵測損壞並回退。
- ⚠️ 這階段就要決定 `RESUME_STRATEGY`，並**實測**喚醒的實際額度成本（§11.3）。這個數字會影響後續所有設計。

#### P2 — 配速（2–3 天）｜先離線模擬，再上線
- **先寫離線模擬器**，餵合成時間序列，跑完 §11.2 的全部性質測試。
- 決策器改用 `pace_index`（§4.2.8），用 P0 的資料校準門檻。
- 以 `DRY_RUN=true` 上線一週：只決策、只記錄、不真的限制。比對「若當時照決策執行，結果會如何」。
- **出場條件**：DRY_RUN 一週內決策無震盪（狀態轉移次數合理）、無會導致撞牆的漏放。
- ⚠️ **絕對不要在真實額度上調參**。每次調參要驗證都得等 5 小時，一週只能做十幾次實驗；模擬器一分鐘做幾千次。

#### P3 — 閘門（1–2 天）｜開始真的限制
- `PreToolUse` hook 攔截 `Agent` 工具 + 動態調整 `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`。
- 模型降級致動器（依 `seven_day_opus` / `seven_day_sonnet` 分軌）。
- 改用原生 `isolation: "worktree"`，**不要自建 worktree 腳本**。
- **出場條件**：§11.6 通過；拒絕派工時 Agent 收到清楚的原因而非莫名失敗。

#### P4 — 韌性（2–3 天）
- 帳號層級仲裁鎖、週額度長休眠、三平台防休眠、`OVERAGE_POLICY`。
- **出場條件**：§11.4／11.5／11.7 通過。

#### P5 — 硬化（2 天）
- 安全（§12）、設定不變式自檢（§6.1）、CLI 版本相容性檢查、告警。
- **出場條件**：§11.8 的 24 小時端到端測試通過。

### 15.5 執行注意事項（紅線清單）

1. **不要碰未公開的 HTTP 端點。** 🔴 **唯一豁免（v2.1.4 修憲，掌舵者 2026-08-16 拍板；R107 四方複審通過＝4×APPROVE_WITH_CONDITIONS，紀錄＝`docs/06_quality/CrossPlatform_R107_Review.md`，已生效）**：§4.1.1 T5 之唯讀 `GET /api/oauth/usage`，且必須**同時**滿足四條件，缺一即回到禁令本身：(a) **僅限唯讀 GET**，不得對該端點發任何寫入型請求；(b) **端點知識只准有一個程式站點**＝`tools/lib/quota_meter.py`（`USAGE_URL` 常數；不得出現第二個家，現查：全庫 `.py` 內完整 URL 字面僅該檔一處，其餘命中皆為指向該常數的註解與文件）；(c) **TTL≥180 秒節流**（現行 `tools/lib/quota_gate.py` 的 `QUOTA_CACHE_TTL_SECONDS=180`，每 TTL 視窗至多補量一次）；(d) **端點失效時必須降級出聲**（回「量不到」＋降級 cap，見 §4.1.1〈T5 升格依據〉第 4 項），**禁止重試轟炸**。豁免範圍外的未公開端點依然全面禁止。本條原文「statusLine 已提供你需要的一切」經 R90 實測證偽——statusLine 只回 five_hour／seven_day 兩軸，看不到 R87 事故軸 `spend`／`extra_usage`（見 `docs/06_quality/Quota_R90_CrossAccount_Experiment.md`）；原文不再是現行規範，保留於版本歷史。
2. **超額用量必須是顯式的 opt-in。** 預設 `OVERAGE_POLICY=FREEZE`。一個「自動繞過限制繼續跑」的系統，配上啟用的付費超額，等於自動花錢機器。
3. **`ScheduleWakeup` 的延遲被夾在 60–3600 秒。** 別以為傳 18000 就會睡 5 小時 —— 它會被靜默夾成 3600，然後你的系統會提早 4 小時醒來、看到還在限流、可能陷入迴圈。
4. **`CronCreate` 的 durable 任務 7 天後自動過期。** 不能當成永久排程。
5. **不要在真實額度上調參**（見 P2）。
6. **失效方向永遠往保守。** 讀不到治理狀態、檔案過期、鎖搶不到 → 一律當成「額度不明」而降級，絕不「先跑再說」。
7. **以 `status` 枚舉為主，百分比為輔。** `rejected` / `allowed_warning` 是平台給的權威判斷；自訂百分比水位只是預測。兩者衝突時信前者。🔴 **通道限定（R90 補；語意不變，只補「它住在哪」——附錄 B-13 已寫對，本條與 §0.6 新發現 2 漏寫）**：枚舉只隨**模型 API 呼叫的限流回應標頭** `anthropic-ratelimit-unified-status` 回來，四條本機可達通道（`/api/oauth/usage` body、同一支 API 的回應標頭、statusLine stdin JSON、逐字稿）R90 實測**全部 0 命中**。⇒ 不發模型請求的元件**沒有「兩者」可衝突**，照本條字面寫出的枚舉分支會是一段永遠走不到的死碼；那種元件的正確作法是把百分比當唯一訊號並在痕跡裡說出「枚舉不可得」，而不是留一個恆假的判斷。依據見 `docs/06_quality/Quota_R90_CrossAccount_Experiment.md`。
8. **本機推估看不到其他裝置的用量。** 若你同時在別的機器或網頁端用同一帳號，statusLine 的讀數不一定同步。務必保留 §4.1.1 的安全邊際，並把 429 當成「推估偏低」的證據。
9. **`--dangerously-skip-permissions` 不要當預設。** 用 `--permission-mode` 加工具白名單。若真的需要旁路，關在容器裡。
10. **不要讓 Agent 修改治理層的設定或狀態檔。** `PreToolUse` hook 要把 `.autoclaude/`、`.claude/settings*.json` 列為禁寫。否則一個「幫我把併發調高」的合理請求就能拆掉整套治理。
11. **記錄 CLI 版本並訂閱其變更。** 本文的核實基準是 2.1.232；內部識別字與旗標會變。升級後先跑 `DRY_RUN` 再放行。
12. **憑證不要進日誌、不要進 `state.json`、不要進遙測標籤。**

### 15.6 常見失敗模式與預防

| 失敗模式 | 徵兆 | 預防 |
| :---- | :---- | :---- |
| 重置後立刻再撞牆 | 每個視窗開頭 20 分鐘就燒掉 40% | 重置後以 `C_min` 起步爬升（§4.5.3）；`pace_index` 天然免疫此問題 |
| 週三就把週額度燒完 | 前三天正常、後四天全在等 | 週額度用配速門檻而非絕對水位（§4.2.8 修正 1） |
| 併發在邊界抖動 | 狀態轉移計數暴增、吞吐反而下降 | 遲滯 + 死區 + 停留時間（§4.2.4） |
| 靜默計費 | 沒觸發過凍結，但帳單出現 | `OVERAGE_POLICY=FREEZE` + 對 `overage` 類額度告警 |
| 喚醒比工作還貴 | `resume_cost_pp` 接近單一 Step 成本 | 量測它（§11.3），超標就切 `FRESH_SESSION_WITH_STATE` |
| 工作區髒污累積 | worktree 越來越多、合併衝突變常態 | 原生 `ExitWorktree` 的未提交變更保護 + 序列化整合佇列（§4.4.2） |
| 治理層被 Agent 改掉 | 參數莫名變寬 | 禁寫清單（紅線 10） |

### 15.7 參數校準方法（用資料取代猜測）

P0 收完資料後，依序推導、不要憑感覺設定：

```
1. 從 claude_code.token.usage 與利用率曲線，算出「單一 Step 的百分點成本」分布
      → MAX_STEP_QUOTA_PP = P95(step_cost_pp) × 1.2
2. 從 5 小時視窗內的實際 Step 數，算出可持續併發
      → C_default = floor(0.85 × 100 / (P50(step_cost_pp) × steps_per_hour × 5))
3. 從 pace_index 的歷史分布，取超前燃燒的容忍點
      → PACE_CEILING = P75(pace_index)，並以 §4.2.8 的 1.25 為上界參考
4. 從一週的日燒率，算出週預算
      → 若日燒率 × 7 > 90%，則系統本質上就是週額度受限，
        應優先投資「模型降級」與「任務篩選」，而非提高併發
5. 從實測喚醒成本
      → RESUME_MAX_TRANSCRIPT_TOKENS = 使 resume_cost_pp ≤ MAX_STEP_QUOTA_PP 的門檻
```
**第 4 點是最重要的**：多數使用者的真正瓶頸是週額度，不是 5 小時視窗。如果 P0 資料顯示如此，那麼「動態併發配速」的價值遠低於「少用高階模型 + 只做值得做的任務」—— 這會改變整個專案的優先序，甚至可能讓 P3 之後的工作變得不必要。**讓資料決定要不要繼續蓋。**

### 15.8 交付物與目錄結構

```
專案根目錄/
├── .claude/
│   ├── settings.json              # 版控：hooks、permissions、statusLine
│   ├── settings.local.json        # 不版控：治理器動態寫入的 env 區塊
│   └── scheduled_tasks.json       # CLI 管理，不手改
├── .autoclaude/                   # 全部加入 .gitignore
│   ├── governance.json            # statusLine 寫入的額度快照
│   ├── governance-decision.json   # 決策器輸出（給 PreToolUse hook 讀）
│   ├── state.json                 # 治理層狀態（縮減版）
│   ├── checkpoints/
│   ├── logs/
│   └── daemon.lock
├── hooks/
│   ├── statusline.sh              # P0
│   ├── pre_tool_use.py            # P3 閘門
│   ├── pre_compact.py             # P1 checkpoint
│   └── stop.py                    # P1 狀態更新
├── governor/
│   ├── decide.py                  # 純函式決策器（§4.2.6）
│   ├── simulate.py                # 離線模擬器（P2 先寫這個）
│   ├── telemetry.py
│   └── arbiter.py                 # 帳號層級仲裁
├── tests/
│   └── test_decide.py             # §11.2 的性質測試
├── .env.example                   # §6
└── README.md                      # 記錄 CLI 核實版本與前置條件
```
`~/.autoclaude/accounts/<fingerprint>/` 放跨專案共享的仲裁鎖與遙測快取。

---

## 附錄 A：v1 → v2 問題清冊（Issue Register）

| ID | 章節 | 類型 | 嚴重度 | v1 的問題 | v2 修正位置 |
| :-- | :---- | :---- | :---- | :---- | :---- |
| A-01 | 3.1 / 4 | 邏輯錯誤 | 🔴 | 混用「額度使用率」與「上下文佔用率」；在額度 90% 觸發壓縮，而壓縮本身會消耗額度 | §2、§4.3 |
| A-02 | 3.4 | 邏輯錯誤 | 🔴 | 週上限觸發後仍只休眠至 5 小時重置，醒來立即再撞牆 | §4.5.5 |
| A-03 | 3.2 vs 7 | 內部矛盾 | 🔴 | 驗收要求 75% 收斂至 `C_min`，但公式無此保證 | §4.2.2、§4.2.7(3b) |
| A-04 | 3.2 | 控制缺陷 | 🟠 | 無遲滯 → 70%/85% 邊界抖動 | §4.2.4(a) |
| A-05 | 3.2 | 控制缺陷 | 🟠 | 無變化率限制 → 併發可從 1 直跳 5 | §4.2.4(c) |
| A-06 | 3.2 | 控制缺陷 | 🟠 | 無最小停留時間／死區 → 控制器快於任務生命週期 | §4.2.4(b)(d)(e) |
| A-07 | 3.2.2 | 數值不一致 | 🟠 | 公式用 `max(0.01,…)`、程式碼用 `max(0.02,…)` | §4.2.1（單一 `V_FLOOR`） |
| A-08 | 3.2.2 | 邏輯錯誤 | 🟠 | `delta_u = max(0, …)` 使視窗重置的負差值被壓為 0 → `V_actual` 觸底 → 重置後立刻暴衝至 `C_max` | §4.1.3、§4.2.6 |
| A-09 | 3.2 | 邏輯錯誤 | 🟠 | `T_rem = max(1, …)` 在重置前一分鐘製造巨大 `V_safe` 假暴衝 | §4.2.2（`T_MIN_MINUTES` hold） |
| A-10 | 3.2 / 3.1 | 缺漏 | 🟠 | 突刺無週額度否決條件；隱含「未用額度會浪費」的錯誤假設 | §4.2.5、§4.2.7(1b) |
| A-11 | 3.1 | 缺漏 | 🟠 | 未定義遙測失效時的失效方向（fail-open 會爆額度） | §4.1.2、§1.2(5) |
| A-12 | 3.4 | 成本錯誤 | 🟠 | 宣稱同 session 續接不重複消耗 token；實際上快取失效後會全額重讀 | §4.5.4 |
| A-13 | 3.4 | 安全 | 🟠 | 預設使用完全跳過權限的旗標 | §4.5.4、§12 |
| A-14 | 3.1 | 事實風險 | 🟠 | 把未公開 OAuth usage 端點列為主要遙測方案，無降級路徑 | §4.1.1（分層 T1–T5） |
| A-15 | 3.1 | 事實錯誤 | 🟡 | 「Statusline 探針」方向反了（statusline 由 CLI 呼叫腳本，非 Daemon 輪詢 CLI） | §4.1.1(T3) |
| A-16 | 1.1 | 事實錯誤 | 🟡 | 「72 小時 / 7 天每週上限」中的「72 小時」並非已知限制週期 | §1.1（刪除） |
| A-17 | 3.1 | 缺漏 | 🟡 | `U5h` 是帳號層級指標，但未說明本機推估看不到其他裝置用量 | §4.1.1（安全邊際） |
| A-18 | 3.3 | 缺漏 | 🟡 | 「Fast-Forward 合併」在多分支分歧時不成立 | §4.4.2（整合佇列） |
| A-19 | 3.3 | 實務缺陷 | 🟡 | `worktree add -b` 分支已存在則失敗；未鎖定基準 SHA；未處理 `.gitignore` 與 prune | §4.4.1 |
| A-20 | 3.4 | 缺漏 | 🟡 | 只 commit 一個 worktree，與多 Agent 設計矛盾 | §4.5.1、§7 |
| A-21 | 2 / 3 | 缺漏 | 🟡 | `DRAINING` 允許「收尾」但無硬性上限，收尾可衝破 `HALT` | §4.4.3 |
| A-22 | 3.5 | 技術錯誤 | 🟡 | `caffeinate -s` 僅在接電源時有效；未綁定 PID（孤兒程序風險）；註解中的 `-d` 與需求矛盾 | §4.6 |
| A-23 | 3.5 | 技術錯誤 | 🟡 | `SetThreadExecutionState` 是執行緒層級，短命執行緒呼叫即失效；`ES_AWAYMODE_REQUIRED` 用途不符；未還原 | §4.6 |
| A-24 | 3.5 | 缺漏 | 🟡 | 完全未支援 Linux / WSL | §4.6 |
| A-25 | 3.4 | 實作缺陷 | 🟡 | 單次長 sleep 無法回應訊號、無法修正時鐘漂移與系統睡眠 | §4.5.2 |
| A-26 | 5 | 資料錯誤 | 🟡 | `reset_timestamp` 比 `saved_at` 晚 **24 小時**（5 小時視窗不可能） | §7（修正為 +2h08m） |
| A-27 | 5 | 資料錯誤 | 🟡 | `git_commit_hash` 為 16 字元，非合法 Git SHA 長度 | §7（40 字元） |
| A-28 | 5 | 安全 | 🟡 | `resumption_command` 存完整 shell 命令 → 注入與轉義風險 | §7（結構化 `resume_plan`） |
| A-29 | 5 | 缺漏 | 🟡 | 無 checksum／原子寫入／版本保留 → 凍結途中斷電即無法恢復 | §7、§8(4) |
| A-30 | 6 | 缺漏 | 🟡 | 429 退避無 jitter，多 Agent 會同步重試（雷群） | §8(1) |
| A-31 | 6 | 缺漏 | 🟡 | 清理 index.lock 未檢查持有 PID 是否存活 | §8(3) |
| A-32 | — | 缺漏 | 🟡 | 同帳號多專案／多 Daemon 會各自超燒 | §4.7 |
| A-33 | 3.1 | 缺漏 | 🟡 | API_KEY 模式提及 TPM/RPM/餘額，但演算法完全以 % 為基礎，無法運作；且無硬性預算上限 | §5 |
| A-34 | 4 | 缺漏 | 🟡 | 無設定不變式驗證（如 WARN<DRAIN<HALT） | §6.1 |
| A-35 | — | 缺漏 | 🟡 | 無可觀測性、日誌、告警、dry-run、人工覆寫 | §9、§6(14) |
| A-36 | — | 缺漏 | 🟡 | 無安全章節（憑證、寫入範圍、prompt injection、供應鏈） | §12 |
| A-37 | — | 缺漏 | 🟡 | 無合規／ToS 章節與非目標宣告 | §1.3、§13 |
| A-38 | 3.2 | 設計限制 | 🟡 | 只有「併發數」單一致動器，控制力不足（模型層級對燃燒率影響更大） | §4.2.3 |
| A-39 | 7 | 不可測 | 🟡 | 「不得產生任何 token 費用」未定義量測方法 | §11.1 |
| A-40 | 2 | 缺漏 | 🟡 | 狀態機無進入／離開條件、無優先序、`BURSTING` 與 `CRUISING` 百分比區間重疊 | §3.2 |
| A-41 | 3.4 | 缺漏 | 🟡 | `SESSION_RESUME` 無失敗退路（session 記錄不存在時） | §8(10) |
| A-42 | — | 缺漏 | 🟢 | 參數（70/85/95、`C_default=2`、15 分鐘）無經驗依據 | §14（P0 先觀測後調參） |
| A-43 | 全篇 | 文件品質 | 🟢 | Google Docs 匯出殘留（`1\.`、`5h`、`> *` 混排、逐行反引號 ASCII 圖、LaTeX 在多數 Markdown 渲染器不顯示） | 全篇改用標準 Markdown + 程式碼區塊 |

嚴重度：🔴 阻斷級（照 v1 實作會造成系統性失效）／🟠 高（會導致額度超燒、成本失控或安全風險）／🟡 中（缺漏或實務缺陷）／🟢 低（品質與可維護性）

---

## 附錄 B：事實核對結果（v2.1 已核實）

### B.0 核實方法與其限制

**官方文件網域在本次作業環境中不可存取**（`docs.claude.com`、`docs.anthropic.com`、`code.claude.com` 皆回傳 `403 host_not_allowed`）。改採替代路徑：

1. 從 npm registry 取得 `@anthropic-ai/claude-code` 的發佈中介資料（最新 `2.1.232`，另有 `stable = 2.1.223`）。
2. 下載官方發佈的 wrapper 套件，取得 `package.json`、`README.md`、`sdk-tools.d.ts`（**內建工具的完整 TypeScript 介面定義**，官方隨套件發佈）。
3. 下載對應平台的原生二進位套件（`claude-code-linux-x64`，解壓後 323 MB），對其做字串比對，驗證環境變數、CLI 旗標、遙測指標名稱、額度欄位與 HTTP 標頭。

**這個方法的限制必須明講：**

- `sdk-tools.d.ts` 是官方隨套件發佈的介面定義，可信度高。
- 二進位字串則是**實作內部細節**：其中可能包含未啟用的功能旗標、內部識別字、測試用途字串。**看到字串不等於該功能對使用者可用、也不等於它是穩定契約。**
- 本核實**無法**驗證任何非技術事項（使用條款、方案定價、額度實際數值）。
- 核實基準版本為 **2.1.232**；升級後應重跑核實。

### B.1 已核實項目

| # | 原待核對項目 | 結果 | 核實內容 | 對 PRD 的影響 |
| :-- | :---- | :---- | :---- | :---- |
| B-01 | 5 小時視窗語意 | ✅ | 額度類型 `five_hour`，`windowSeconds = 18000`；有 `resets_at` / `resetsAt` 欄位可讀 | 配速與休眠邏輯成立；重置時間可取得，無需推估 |
| B-02 | 週額度與模型分軌 | ✅ | `seven_day`（`windowSeconds = 604800`）、`seven_day_opus`、`seven_day_sonnet`、`seven_day_overage_included`；UI 標題為「Current session」「Current week (all models)」「Current week (Sonnet only)」，後者於 max / team 方案顯示 | 週閘門與模型降級致動器**確認可實作**；分軌額度是 v2 未預期的細節 |
| B-03 | 官方遙測機制 | ✅ | `CLAUDE_CODE_ENABLE_TELEMETRY`；完整 OTLP 環境變數族；**含 `OTEL_EXPORTER_PROMETHEUS_HOST/PORT`**；指標含 `claude_code.token.usage`、`claude_code.cost.usage`、`claude_code.compaction`、`claude_code.subagent.spawn`、`claude_code.llm_request`、`claude_code.hook`、`claude_code.tool.execution`、`claude_code.active_time.total` 等 | §9 可觀測性**大部分免費取得**；T1 為首選確認正確 |
| B-04 | 對話記錄檔路徑與格式 | ✅ | `~/.claude/projects/<sanitized-cwd>/*.jsonl`，每行一個 JSON 物件；工具呼叫出現在 `assistant` 訊息的 `message.content[]` | T2 遙測與上下文估算可實作 |
| B-05 | statusLine 輸入結構 | ✅ **關鍵** | stdin JSON 含 `rate_limits.five_hour.used_percentage`、`.resets_at`、`rate_limits.seven_day.*`、`rate_limits.model_scoped`、`rate_limits_available`、`subscription_type`、`session.total_cost_usd` / `.total_api_duration_ms` / `.model_usage` / `.total_lines_added`；二進位內含 jq 範例腳本 | **這是零 Token 遙測的正解**。T5（未公開端點）可完全刪除【v2.1.4 指針：本格結論為 v2.1 核實當時的歷史紀錄、**不再是現行規範**——v2.1.4 起 T5 已升格認可主源（§4.1.1）；statusLine 缺 R87 事故軸 `spend`／`extra_usage`（R90 實測），「可完全刪除」已被推翻】 |
| B-06 | 用量查詢指令 | ⚠️ 部分 | `/usage` 存在且有「非互動模式的格式化成本摘要」；另有 `/usage-credits`、`/status`、`/model`、`/compact` | 可用但格式非契約；優先用 B-05 |
| B-07 | 壓縮觸發與 hook | ✅ | 自動壓縮相關：`CLAUDE_CODE_AUTO_COMPACT_WINDOW`、`CLAUDE_CODE_COLD_COMPACT`、`CLAUDE_CODE_DISABLE_PRECOMPACT_SKIP`；hook 事件含 **`PreCompact` 與 `PostCompact`** | §4.3 的擔憂成立：**不需自行下達壓縮指令**，改用 hook 在壓縮前寫 checkpoint |
| B-08 | `--resume` 行為 | ⚠️ 部分 | `--resume`、`--continue`、`--session-id`、**`--fork-session`** 皆存在；另有 `CLAUDE_CODE_RESUME_TOKEN_THRESHOLD`、`CLAUDE_CODE_RESUME_INTERRUPTED_TURN`、`CLAUDE_CODE_RESUME_PROMPT`、`CLAUDE_CODE_RESUME_INTERRUPTED_TURN_MAX_AGE_MS` | 旗標確認；**但「續接是否重新計費完整歷史」仍需實測**（§11.3 已納入量測）。`--fork-session` 是 v2 未考慮的選項：可在不變更原 session 的前提下續接 |
| B-09 | 權限模式與工具白名單 | ✅ | 權限模式：`default`、`plan`、`acceptEdits`、`bypassPermissions`、`dontAsk`、`auto`；旗標 `--permission-mode`、`--allowed-tools`（亦接受 `--allowedTools`）、`--disallowedTools`、`--dangerously-skip-permissions`；子代理繼承父 session 的權限模式，agent 定義的 frontmatter 可覆寫 | §12 的建議可直接實作；`dontAsk` / `auto` 是 v2 未知的中間選項，值得評估 |
| B-10 | 硬性預算旗標 | ✅ | `--max-turns`、`CLAUDE_CODE_MAX_TURNS`、`CLAUDE_CODE_MAX_OUTPUT_TOKENS`、`CLAUDE_CODE_MAX_CONTEXT_TOKENS`、`CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS`、`CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION` | §4.4.3 可實作，且顆粒度比 v2 設想的更細 |
| B-11 | 模型選擇與降級 | ✅ | `--model`；`Agent` 工具的 `model` 欄位可取 `"sonnet" \| "opus" \| "haiku" \| "fable"`；`CLAUDE_CODE_SUBAGENT_MODEL`；`/model` 指令 | 模型降級致動器**確認可實作**，且可針對個別子代理 |
| B-12 | 提示快取存活時間 | ❌ 未能核實 | 二進位中未找到明確的 TTL 值 | §4.5.4 的成本論述**改以實測為依據**（§11.3），不依賴假設值 |
| B-13 | 限流標頭 | ✅ | `retry-after`；**`anthropic-ratelimit-unified-status`、`-reset`、`-representative-claim`、`-fallback`、`-grace-status`、`-upgrade-paths`、`-overage-status`、`-overage-utilization`、`-overage-reset`、`-overage-period`、`-overage-period-monthly-utilization`**；狀態枚舉 `allowed` / `allowed_warning` / `rejected` | §8(1) 可實作且**應優先信任 `status` 枚舉**而非自訂百分比水位 |
| B-14 | 併發上限 | ✅ | `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`（超出時錯誤訊息明示「請使用者調高此變數」）、`CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION`、`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`、`CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` | **併發致動器改為調整設定值**，不需自建行程池 —— 本次核實帶來的最大簡化 |
| B-15 | 模型計價 | ❌ 未能核實 | 二進位不含價目表 | §5 的成本計算需以官方定價頁為來源，且價目表必須可設定 |
| B-16 | 使用條款 | ❌ 無法核實 | 屬法務事項，非技術可驗證 | **仍為上線前必要檢核項**（§15.1 第 2 點） |
| B-17 | 套件與前置條件 | ✅ | `@anthropic-ai/claude-code`，**Node.js ≥ 22**；現以各平台原生二進位發佈（`darwin-arm64/x64`、`linux-x64/arm64` 含 `-musl` 與 `-android`、`win32-x64/arm64`）；安裝後不常駐 Node 行程 | **Linux 支援確認**（A-24 成立）；PRD 應新增前置條件章節（已補於 §15.1） |

### B.2 核實中發現的、原清單未列的重要事實

| # | 發現 | 為何重要 |
| :-- | :---- | :---- |
| B-18 | **超額用量維度**：額度類型含 `overage`、`extra_usage`、`seven_day_overage_included`；標頭含 `-overage-utilization`、`-overage-period-monthly-utilization`、`-overage-disabled-reason`；訊息提及月度支出上限與 `/usage-credits` | 達訂閱限制後**可能付費續跑而非停止**。這讓「凍結等待」邏輯可能永不觸發卻默默計費 —— PRD 完全遺漏，且是最危險的失敗模式 |
| B-19 | **CLI 內建配速判準**：`five_hour` → `{utilization: 0.9, timePct: 0.72}`；`seven_day` → `{0.75, 0.6}`、`{0.5, 0.35}`、`{0.25, 0.15}` | 驗證 `V_safe` 觀念，並提供官方參考值。導出更穩健的 `pace_index` 形式（§4.2.8），可完全免除燃燒率估計的冷啟動與調參問題 |
| B-20 | **原生 worktree 隔離**：`Agent` 工具 `isolation: "worktree" \| "remote"`；`EnterWorktree` / `ExitWorktree`（`action: keep \| remove`，未提交變更時拒絕並要求 `discard_changes: true`）；`worktree.bgIsolation` 設定 | §4.4.1 的自建腳本不需要了；原生版本的未提交變更保護正是 §8(8) 想解決的問題 |
| B-21 | **原生任務 DAG**：`TaskCreate` / `TaskUpdate` / `TaskList` / `TaskGet` / `TaskStop` / `TaskOutput`，支援 `addBlocks` / `addBlockedBy` / `owner` / `metadata` / 狀態 `pending \| in_progress \| completed \| deleted` | §7 的 `task_state.dag` 可交給原生工具，`state.json` 縮減為純治理狀態 |
| B-22 | **原生排程**：`CronCreate`（5 欄位 cron、`recurring`、`durable` → `.claude/scheduled_tasks.json` 跨 session 存活、**7 天後自動過期**）、`CronList`、`CronDelete`；`ScheduleWakeup`（**`delaySeconds` 被夾在 [60, 3600]**，含 `wasClamped` 回報） | §4.5.5 部分可用原生。但 `ScheduleWakeup` 上限 1 小時，**單次無法撐過 5 小時視窗** —— 若誤以為可以，系統會提早 4 小時醒來 |
| B-23 | **`Monitor` 工具**：以 shell 命令或 WebSocket 持續監看，每行 stdout 為一事件，`persistent` 可存活整個 session | 遙測攝取的另一條路徑，可能免除獨立輪詢行程 |
| B-24 | **完整 hook 事件集**：`PreToolUse`、`PostToolUse`、`PreCompact`、`PostCompact`、`SessionStart`、`SessionEnd`、`Stop`、`SubagentStop`、`Notification`、`UserPromptSubmit` | 使 §15.3 的「hook 為主、Daemon 為輔」架構成為可能 —— 治理閘門放在 `PreToolUse` 比管理行程可靠得多 |
| B-25 | 其他相關環境變數：`CLAUDE_CODE_RATE_LIMIT_TIER`、`CLAUDE_CODE_IDLE_TOKEN_THRESHOLD`、`CLAUDE_CODE_TOTAL_TOKENS_REMINDER_BUDGET`、`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`、`CLAUDE_CODE_ENABLE_TOKEN_USAGE_ATTACHMENT` | 可能提供更直接的治理槓桿，值得逐一試驗（屬**內部**，需驗證） |

### B.3 仍待人工確認（本次無法核實）

| # | 項目 | 建議做法 |
| :-- | :---- | :---- |
| 1 | 使用條款對長時間無人看管自動化的規定 | 閱讀條款；必要時聯繫 Anthropic。**這是唯一可能讓專案作廢的風險項** |
| 2 | 帳號是否已啟用付費超額、月度支出上限為何 | 執行 `/usage`、`/usage-credits` 並檢視帳號設定 |
| 3 | 續接長對話的實際額度成本 | 依 §11.3 實測，這是無法從程式碼推導的數字 |
| 4 | 提示快取 TTL、模型定價 | 查官方文件（下方連結） |
| 5 | 各方案實際可見的額度分軌項目 | 在目標帳號上執行 `/usage` 並記錄 |

### B.4 文件入口（已更新）

原清單中的 `docs.anthropic.com/en/docs/claude-code/...` 路徑已過期。核實發現官方 README 現指向：

- **Claude Code 文件**：`https://code.claude.com/docs/en/overview`
- **資料使用政策**：`https://code.claude.com/docs/en/data-usage`
- **Claude Code 首頁**：`https://claude.com/product/claude-code`
- **商業使用條款**：`https://www.anthropic.com/legal/commercial-terms`
- **Claude API 文件**：`https://docs.claude.com/en/api/overview`
- **問題回報**：`https://github.com/anthropics/claude-code/issues`

---

*文件結束。*

*v2.1 修訂原則：能核實的就核實並註明來源與版本；不能核實的就明說不能，不用推測填空。已內建的能力優先採用，自建範圍壓到最小。所有控制迴路必須可離線模擬與斷言，所有失效路徑往保守方向收斂。*
