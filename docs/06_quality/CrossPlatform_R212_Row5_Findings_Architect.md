VERDICT: APPROVE
理由：清倉層四條底線皆以合取項／建構順序落地（本鏡窮舉 400 組合零收緊、零 None／有限互換），PRD §16 四格獨立重數吻合主控（✅31／➖33／⏸29／📎8＝101），喚醒鏈終點定義自洽且誠實，未見 P≤2；另有 14 項 P3（記載與措辭訂正，提交前改）與 14 項 P4（登記）。

# CrossPlatform R212 第五列：Architect 鏡 findings（清倉模式 DEF-200-528 ＋ 前六次響應完備性）

> 角色：L10 架構總監、唯讀複審。對主控骨架（`CrossPlatform_R212_BurnDown_FourParty_Evidence.md`）與前六次響應宣稱一律零信任；所有「驗到的」皆為本鏡當回合讀碼、跑指令或讀真實痕跡所得，輸出逐字見〈五〉。未碰 `.claude/`、launchd、哨兵、真實落款；隔離實驗一律 `AUTOSDD_TRACE_DIR`／`AUTOSDD_QUOTA_CACHE_DIR` 指向 scratchpad 子目錄，真實檔只讀或先複製。
> 本檔新檔名符合 `docs/06_quality/CrossPlatform_*.md` 發現面，須由主控登記到 `tools/lib/governance_docs.py`（本鏡唯讀、未改）。

---

## 〈一〉對四問宣稱的逐項核對

### 一-A 喚醒鏈接縫：以兩張表為母體，再從碼畫自己的清單

**步驟 1：兩張表本身的口徑。** 主檔〈十一-5〉S1～S16 與 Run4〈三〉續表的「真」皆指「真 launchd 行程內實跑」；表內**沒有 Windows 欄**，Windows 只在末列與 Run4〈三〉末段各有一句全域聲明（「R212 第四列沒有 Windows 真機樣本」）。因此表的「真」不能外推到 Windows。

**步驟 2：本鏡從碼畫出的接縫清單**（座標＝`tools/session_resume_planner.py`、`tools/lib/relay_machine.py`、`tools/lib/schedule_backend.py`、`.claude/hooks/context_budget_guard.py`〔唯讀〕、`tools/lib/quota_gate.py`）。「兩表」欄：列＝已在表內；未驗＝兩表明列為未驗；聚合＝只有全域一句；未列＝兩表皆沒有。

| # | 接縫（碼座標） | 兩表 | mac 真後端樣本 | Windows 樣本（R212 各列範圍） | 判定 |
|---|---|---|---|---|---|
| 1 | SessionStart 清閂鎖＋簡報（hook SessionStart；`sentinel_lifecycle_arm.clear_arm_latch`） | 未列（常態路徑） | 每個互動窗皆走 | 無 | 無缺口 |
| 2 | PostToolUse 累積→`maybe_arm`→`spawn_sentinel`→planner `--arm-sentinel`→`_arm_sentinel`→`backend.arm` | S9／S14 只涵蓋「重掛」與「窗內早退」，首次武裝未列 | 大量（`~/.autosdd/traces/` 219 個檔，其中哨兵 bootout 日誌 90 個、launchd 日誌 87 個） | 無（現碼） | 非缺口（日常即樣本）；Windows 現碼零樣本 |
| 3 | 自願 halt 標記**生產端**：`quota_gate()` halt 分支→`quota_halt_actions`→`write_halt_marker` | 未驗（7-E 生產端） | 手寫標記 4 筆；真生產 0 | 無 | 已列 |
| 4 | 真 429 逐字稿事件→`unhandled_limit_event`→`sentinel_decide` | 未驗（Run4〈三〉末段） | 歷史真撞線窗：2026-10-10 一個（sid 5535e815，修前碼；成本帳首列與主檔〈二-0〉可對）、PRD v2.1.13 列另記 2026-08-31 一次；修後 0 | 無 | 已列 |
| 5 | 哨兵 tick 五分支 `arm_reset`／`probe`／`patrol`／`disarm`／`escalate`（`sentinel_decide`） | 部分（`escalate` 0 筆於 Run4 明列；`arm_reset` 僅手寫標記） | patrol／disarm 真；probe 真（含修前）；arm_reset 手寫 | 無 | 已列 |
| 6 | 早醒時間閘 `reset_not_reached`（S2） | 列 | 真 | **設計上不觸發**（Windows `-Once` 單一觸發器） | launchd 專屬構造 |
| 7 | 探測 `probe_quota`：L0 正向（S3） | 列 | 真（自取＋沿用快取兩型） | 無 | 已列 |
| 8 | 探測負向三出口 `rearm`／`patrol_handback`／`stop`；無人不付費探針（INV1） | 未驗 | 真痕跡 `probed` 6 筆全為 `quota_open=true` | 無 | 已列 |
| 9 | 路由 SESSION_RESUME（S4）；FRESH／PATROL 兩路由 | 列／未驗 | `route_chosen` 5 筆全為 SESSION_RESUME | 無 | 已列 |
| 10 | spawn argv／env（S5）；失敗態 `resume_failed`／REFUSE／`rc=None` 重掛 | 列／未驗 | 真／0 | 無 | 已列 |
| 11 | handback 後檢（S6）、settle→DONE（S7） | 列 | 真 | 無 | 已列 |
| 12 | settle 其餘出口：`no_progress` 真 1 筆；`RELAY_NEXT`／`quota_stop`／`relay_exhausted` | 列／未驗 | 1／0 | 無 | 已列 |
| 13 | 排程後端：LaunchdBackend（S8 自拆、S9 C-A、S10 基線、S12 calendar＋deferred 重載＋F5） | 列 | 真 | S8／S9／S10／S12 五個接縫是 launchd 專屬構造，Windows 無對應列 | 見 AR-09 |
| 14 | 排程後端：`SchtasksBackend`（`endurance_schtasks_script`、`run_powershell`、`Get-ScheduledTask` 憑證、S4U→Interactive 回退、`pythonw` 無 console 載具、UTF-8 BOM／CRLF 落檔） | **聚合**（全域一句）；逐接縫無列 | 不適用 | 無（歷史輪有，現碼已多輪變動） | 已聲明未驗，但未逐接縫登記（AR-09） |
| 15 | 成本帳（S16） | 列 | 真 | 無 | 已列 |
| 16 | **人類面**（loud 出口）：`quota_escalation.alert`→紙條 `$TMPDIR/AUTOSDD_ATTENTION.md`（揮發）／桌面通知（`AUTOSDD_DESKTOP_NOTIFY` 預設關，`notify_rc=-2`）／持久結局檔＋`--pace`／`--check` 未讀游標（`endurance_env.py` F3-FIX3） | 只在 Run4 旁及（`notify_rc=-2`） | 結局列 1 筆真；顯示路徑僅「游標被消耗」的間接證據（`autosdd_unattended_outcome.cursor`＝4） | 無 | **兩表未列**（AR-10） |
| 17 | **清倉層在 `--pace` 的消費點**（`quota_gate.py:946,962`） | 新增（兩表成稿時尚無） | `--pace` 真機 1 筆（本列〈三-3〉） | 無 | 本列新接縫，已有親驗 |
| 18 | **清倉層在派工 hook 的消費點**（`quota_gate.py:1101-1102`；hook 路徑 `ratio=None` ⇒ 無攤提） | 新增 | 僅單元測試以 spy 讀 `decide` kwargs；無真 Agent 派發樣本 | 無 | **兩表未列**；本鏡讀碼結論見〈一-C〉 |
| 19 | 清倉層 × 接力 band 判準②（`relay_machine.py:137` `current_band`→`band_ok`：只認 free／notice） | 未列 | 無 | 無 | **兩表未列**（AR-02） |
| 20 | 清倉層 × 引擎併發契約檔（`pace_report` 於穩定化後寫 pace 契約） | 未列 | 無 | 無 | 未列；讀碼推得放寬值經穩定化後才進契約（`quota_gate.py:973-974`） |
| 21 | 24 小時／至少 4 次 reset 連續閉環 | 未驗 | 無 | 無 | 已列 |
| 22 | 睡眠喚醒（#1） | 未驗 | 無（`pmset` 僅出聲不保證） | 無 | 已列 |
| 23 | 時區／DST：本機 naive 字串送 `New-ScheduledTaskTrigger -At`／`StartCalendarInterval`（無年份欄） | 未列 | Asia/Taipei 無 DST，無暴露 | 無 | 未列（AR-14，構造性） |
| 24 | 真實痕跡純度：夾具列混入真實痕跡目錄 | 未列 | 實測 3 列夾具（`autosdd_unattended_outcome.jsonl`） | — | 未列（AR-11） |

**對任務書點名的四個候選的結論：** (1) Windows schtasks 後端＝兩表只有全域一句「無樣本」，**逐接縫未登記**（#14，P4 AR-09）；(2) 真 429 寫標記端＝已列未驗（#3、#4）；(3) 24h／≥4 次 reset＝已列未驗（#21）；(4) 清倉層在 hook 路徑的消費點＝兩表未列、本列新增（#18），另有兩個相鄰消費面（#19、#20）設計上不帶授權。兩表另未列者：人類面（#16）、時區／DST（#23）、痕跡純度（#24）。

**終點定義（「收斂＝症狀驅動」）是否有結構洞：判定＝無 P≤2。** 定義自洽、邊界逐項自陳（〈二-0〉第 3 點、〈六-3〉、Run4〈三〉末段「本清單為本列已知項，不是完整宣告」）。本鏡指出的是三個**結構限制**，皆已在文件中揭露、但沒有被命名成限制：

1. **歸屬**：§16.1 的結案定義（62／101 列歸 ➖／⏸）依 v2.1.17 修訂表為「主控代決、掌舵者授權依最佳理想化代為決策、非逐列明示追認」。掌舵者以同一份 T1 重貼七次，最可能的殘餘根因不是第八個技術接縫，而是**驗收定義尚未經掌舵者明示追認**（他的字面驗收是「完成所有功能＋E2E 全功能驗證」，§16.1 的 ✅ 是「機制在、有測試或鎖」）。主檔〈二-0〉的根因只有技術兩層。見 P3-01。
2. **平台**：§16.1 邊界明文「Windows 真機親驗不入本表」，✅ 定義平台中立；而喚醒鏈的真機樣本只有 mac（表內「真」＝launchd）。對「下次在 Windows 執行」的掌舵者，✅ 不是 Windows 上的保證。
3. **觀察者依賴**：⏸ 沒有掃描器（§16.5），再開靠「掌舵者回報，或任一視窗寫新 DEF／證據檔時對照」；未驗接縫清單散落三處（主檔〈十一-5〉末列、〈六-3〉兩段追記、Run4〈三〉末段）加〈五〉理論洞表，沒有單一清單（AR-08）。

### 一-B PRD §16 結案帳（工作樹現況）

| 宣稱 | 本鏡驗到的 | 判定 |
|---|---|---|
| 四格＝✅31（矩陣原判 29＋§16.2 內 2）／➖33／⏸29／📎8＝101 | 以腳本解析 §16.2 表（第 2634～2711 行）：表列 72＝✅2／➖33／⏸29／📎8；另以腳本抽出「未重列的 ✅ 矩陣 ID」句＝29 個；合計 31＋33＋29＋8＝101。矩陣原判分佈 ⚠️51（S24／M23／L4）＋❌11＋➖10＝72，與 §16.2 首段「⚠️51／❌11／➖10」吻合。 | 站得住，與主控數字一致 |
| §16.3 數字 | §16.3 (b) 仍寫 ✅29／⏸31（v2.1.17 當日快照；§16.3 讀法段與 §16.5 末段明文「之後不重算」）。現況為 31／29。 | 字面合規；對掌舵者報數須用現況 31／33／29／8（見〈六〉第 9 項） |
| 29 列 ⏸ 的再開症狀符合 §16.1 寫法紀律（一句、具體可觀測、無輪號、無日期、無排程類字樣） | 逐列抽出「再開症狀」之後的文字並以規則式掃描：29 列皆含標示；皆單句；輪號 0 命中、排程類前瞻字樣 0 命中；日期只命中 §6.1 列（第 2670 行），該日期位於症狀句**之後**的 `【2026-10-12】` 落款註記內。➖ 33 列皆含依據座標、📎 8 列皆含「殘留」字樣（腳本）。 | 站得住（P3-04：§6.1 列症狀前半已被實際觸發卻仍留原字面） |
| A4 的 §16.5 (iii) 操作只動一格＋修訂表一列＋DEF 入口 | PRD 本檔 diff 共 3 行（新增 v2.1.19 修訂列 1 行；A4 列 1 刪 1 增）；DEF-200-528 列在帳本、「分流去向」欄標「PRD §16.2 A4 列 ⏸→✅（§16.5 (iii)）」；§16.3、其餘 100 列、全部既有條文零改動。**多動**：無。**少動**：附錄 §7.2 草案鍵 `BURNDOWN_CAP_CEILING`（只准調小的營運旋鈕）在 `tools`、`AutoClaude/autoclaude`、`env.shared`、`.env.example` 零命中，A4 落款與〈三-1〉出入清單皆未列（P3-09）。 | 操作面站得住 |
| A4 落款與修訂表 v2.1.19「親驗＝`--issue weekly_all` 後 `--pace` cap 由 1 升至 `cap_converge`」 | 證據〈三-3〉逐字：標題 `cap=2`（「目前 cap=2 由遲滯維持（這條軸自己的 cap 是 4）」），「現在可派」＝2。軸自身 cap＝4＝`cap_converge`，但標題 cap 是 2；`rec` 封頂 `cap_prepare`（Dev 報告 §0-4）。 | **寫太樂觀**（P3-02） |
| 修訂表 v2.1.19「四方（Architect／SA／SD／QA）複審見證據檔」；DEF-200-528「fixed」 | 證據檔〈四〉〈五〉目前為「待填」。 | 寫在審查完成之前（P3-03：提交順序） |

### 一-C 清倉模式設計審（附錄 §3～§6、§8＋QB1～QB6＋BD-2′ 對 `git diff` 與 `quota_burndown.py`）

| 審查點 | 本鏡驗到的（座標＋方法） | 判定 |
|---|---|---|
| 四底線是合取項／建構順序而非散文 | 底線①②③＋時鐘＝`_eligible`（`quota_burndown.py:131-135`）一條合取式：`kind ∉ FALLBACK_KINDS ∧ kind ∉ MODEL_SCOPED_KINDS ∧ 0≤pct<halt_pct ∧ minutes 解得出且≥0`；`_merge` 在 `on` 為假時原樣回傳（`:150-153`）⇒ halt 帶軸結構上不被放寬。底線④＝順序：`decide()` 在 `quota_policy.py:718-719` 先放寬逐軸輸入，之後才 `gate_list`／`min`／`_rec_of_gate`；must-finish 的收緊（`wrap` 為真時 `recommended_fanout` 夾 `cap_prepare`）在 return 組裝時最後套用（`:797-808`）；`model_hint` 只讀 `gate`、不影響 cap／rec。紅綠測試各有注入紅面（`test_bd3`／`bd4`／`red_every_floor_conjunct`／`bd8`）。 | 成立 |
| 放寬在 min 聚合之前、must-finish 之前（must-finish 最後求值） | 如上；附錄 §5④ 字面寫「cap/rec 聚合→清倉放寬→must-finish」，與 §4.3「只改逐軸輸入、聚合仍是 min」自相矛盾；實作取 §4.3。④ 的承重性質（must-finish 最後）成立。 | 成立；附錄字面矛盾 P3-06 |
| 夾層不得把 None 格變有限、也不得把有限格變 None、不得收緊 | 隔離實驗 E1：把 `_merge` 對「20 格 `(band×horizon)` ×20 格」共 400 個 `(b, n)` 組合窮舉：違規數＝0（無 None／有限互換、cap 不降、rec 不降）。 | 成立 |
| BD-2′ 是否放寬到「未點名、不同窗、非供給關係」的軸 | `Burn.masks`（`:171-185`）：`hold[i]＝named ∧ total ∧ ok[i]`；`ok[i]`＝底線合取＋進 cap gate；`total`＝`Amort.total_kind` 的軸本身是 Q-same。`hold` 只在 `quota_pace.band_inputs` 對 `win == amort.rate_window` 的軸改回原始 pct（`quota_pace.py:381`），其餘軸 `hold` 為 no-op（只讓 `_merge` 走一遍，E1 已證不收緊）。實況：被放寬者＝本次攤提所餵的短窗軸（`session`／`five_hour`），即 BD-2′ 的本意。第三個長窗軸的構造實驗（E2：另加一個 40000 分鐘窗的軸）使攤提的 `total_kind` 變成該軸（`amort.total_kind = monthly_x`）、BD-2′ 反而不觸發（保守）。 | 成立；僅文字面有誤標（P3-05） |
| QB6 同窗鄰軸「`resets_at` 字串全等」在真實資料上是否可行 | 真實 `~/.autosdd/traces/quota_burn.jsonl`（205 列含 `resets_at`）：`weekly_all`＝`seven_day` 205／205 全等；`session`＝`five_hour` 203／203 全等；`weekly_scoped` 與 `weekly_all` 0／204 全等（恆差亞秒）。附錄 §9-5 的觀察項由此量測：今日要緊的兩對 100% 全等、分軌軸恆不全等（正好被底線③排除）。 | 零容差判準在現伺服器資料上可行 |
| 載體 QB3「三收」（落款檔＋CLI 唯一寫入口＋env 只准關） | env：`AUTOSDD_QUOTA_BURNDOWN_OFF` 在 `ENV_SPEC` 為 `escape` 類、`attr=None`，讀取點 `active()`（`:211-224`）；全 repo 沒有任何 env 能「開」清倉。CLI：`issue()` 零網路、拒絕 FALLBACK／MODEL_SCOPED／空指令／缺快取／解不出 `resets_at`，拒絕皆不落檔（測試 `test_refusals_never_leave_a_file`）。「唯一寫入口」是文件宣示、非機制：落款是普通 JSON（附錄 §3.4 已明文不具防偽）。 | 成立（防偽劃界屬實；對帳器缺席見 AR-04） |
| 「授權在但一軸都沒放寬」說得出來 | `Applied(effect="inert")` 文字含「本次未放寬任何軸：＋具名理由」（BD-9 測試）。但理由字面在週軸低於 converge 帶時是錯的：隔離實驗 E4（週軸 55%／65%、點名 `weekly_all`）印出「未放寬：kind=session（已在放寬上限，無可再放）」——真因是 R95 攤提在該帶本就只出聲不收緊。 | 說得出來，但該帶理由為假（P3-05） |
| 與 R98 model-scoped 排除的對稱性 | R98：未命中模型的分軌軸不進 gate；清倉：分軌軸**一律**不被放寬（含命中者，QB4）。比 R98 更保守，不存在「用指令燒沒在用的模型」。實況：本機 `--pace` 的 `active_model` 解為 fable，`weekly_scoped` 在 gate 內且 `cap=None`（free），保守側此刻不影響結果。 | 成立 |
| 落款生效判準是否綁「視窗身分」 | `verdict`（`:102-128`）只比 `now < until_resets_at`（時刻），不比現讀被點名軸的 `resets_at`。真實語料：週軸 `resets_at` 每次讀數都是不同字串（205 列 205 個相異值，距整點 −0.89～+1.00 秒），字串鍵結構上不可行；且週軸有「提前改錨」事件 2 次（2026-09-10：reset 提前、用量 75→29；2026-09-17：reset 變晚、用量 67→46）。隔離實驗 E3：落款 `until`＝+7663 分鐘、現讀視窗改錨到 +1500 分鐘時 `active()` 仍回 Burn（效期剩 7663 分鐘）。 | 與附錄 §3.1(ii)／§7.3「結構性不匹配」的前提不符（P3-08）；行為洞登 AR-01（無實害暴露＝P4） |

**對 BD-2′（主控代決）的獨立意見：有條件同意。**
- 同意的理由：(a) 附錄 QB6 尾句要求的「跨窗點名（含短窗軸）」增補提案迄今無檔，而立案情境（短窗被攤提壓成 prepare）在沒有它時 BD-1 單獨只把 cap 由 1 推到 2、rec 不動——是「入憲了但治不到」；(b) 結構守門保留（供給軸本身須 Q-same，等於 QB2 α 的「不間接放寬沒在用的模型的煞車」不破）；(c) 只暫停「攤提上調」、回的是原始 pct，方向鎖「永不調低」成立；halt／fallback／分軌／must-finish 皆不受影響；(d) Dev 偏離 (c)（供給軸取「`total_kind` 的軸是 Q-same」之超集）正確：它處理 `weekly_all`／`seven_day` 同值平手時 `max` 取第一個軸的順序依賴。
- 條件（皆為文字面、不阻擋合入）：(1) 把 BD-2′ 的規範文本放進附錄（沿用 2026-09-02 盤點注體例加一則日期訂正注），現況只住證據檔〈二-2〉，而附錄 §4.1／§9-1 仍寫「短窗軸不是 qualifying、仍治不到」，與出貨行為矛盾（P3-07）；(2) A4 落款的劃界補三句：效果有界（標題 cap 1→2、軸 cap 4、`rec` 封頂 2，每放寬 1 階需遲滯 ≥300 秒）、落款綁的是 `until` 時刻而非視窗身分、清倉只涵蓋 `--pace` 與派工 hook（接力 band 判準②等呼叫端不帶授權）；(3) 修正 `_why` 的未放寬理由字面（P3-05）。

### 一-D `env.shared` 四層載入鏈與 post-merge hook

| 宣稱 | 本鏡驗到的 | 判定 |
|---|---|---|
| harness 與引擎同序同語意 | harness：`quota_env_layers.merged_file_env`（`:54`）＝`env.shared`（低）→`.env`（高），空白值不遮蔽下層，再疊 `os.environ`（`quota_gate.policy_env`）。引擎：`config.py:31` `_ENV_FILES`＝(`AutoClaude/.env`, 根 `.env`, 根 `env.shared`)，取第一個**非空**命中，`os.environ` 最高。兩側序一致（引擎多一層僅引擎 3 鍵的 `AutoClaude/.env`）；`TestEngineMirrorsTheHarnessChain` 以 6 組合成語料雙邊對跑、AST 對照 `_ENV_FILES` 檔名序、引擎鍵清單與覆寫標記字面（本鏡跑 `test_quota_env_layers`，OK）。 | 同序成立 |
| 同語意 | 隔離實驗 E5（根 `env.shared` 設 `HALT_PCT=98`，行程 env 三種狀態）：未設 ⇒ harness 98／引擎 98／doctor 98；**設成空字串 ⇒ harness 95（出廠）／引擎 98／doctor 98〔env.shared〕**；設成 95 ⇒ 三者 95。即 `policy_env()`＝`{**檔案層, **os.environ}` 讓空字串行程 env 遮住共享值，而引擎與 doctor 把空白當不存在。 | 幾乎同語意；一處構造性差異（AR-12，P4） |
| post-merge「永不讓 merge 失敗」 | `tools/git-hooks/post-merge` 只有 `set -u`（無 `set -e`），所有出口皆 `exit 0`（第 46／63／79／90／95／100／115 行）；`grep -c` 的 rc=1 以 `|| true` 與命令替換吸收；缺 `.venv` 直譯器、doctor 自己壞（rc≠0 卻無旗標行）皆走出聲後 `exit 0`。 | 在碼裡 |
| 「含需人判斷旗標則一個檔不動」 | 第 85～91 行：`n_human>0` 分支先出聲再 `exit 0`，**早於**第 103 行唯一的 `_doctor --fix`；`--fix` 射程只有 `.env` 與 `AutoClaude/.env`（`quota_env_layers._fix_one` 呼叫處），不碰 `env.shared`；無人值守（第 98 行 `AUTOSDD_UNATTENDED` 鍵存在即算）只體檢不修。備份 `.env.bak.<UTC>` 被 `.gitignore:36` 的 `.env.*` 擋住（`git check-ignore` 命中）。`TestPostMergeHook` 一併在本鏡跑的 52 項內，OK。 | 在碼裡；Windows 實機未驗屬實 |

### 一-E 其餘宣稱與主控裁決

| 宣稱／裁決 | 本鏡驗到的 | 判定 |
|---|---|---|
| commit `1818de87` 29 檔；六支 CI 全 success；未結 0 | `git show --stat`：`29 files changed, 1543 insertions(+), 47 deletions(-)`；`gh run list --commit 1818de87fbbb…`：六筆 `conclusion=success`（arch-fitness／drift-daily／windows-compat-ci／root-infra-ci／AutoClaude CI／macos-compat-ci）；`check_defect_log_crossref.py --unresolved-count`：「未結列數＝0／全部 229 列」。 | 站得住 |
| 根層全套 rc=0、AutoClaude 5248／156（通過／略過） | 不在本鏡射程（QA 鏡跑根層全套），標〔他包回報〕，不核。 | 未核 |
| Dev 四處出入（Dev 報告 §0） | (a) `decide(` 呼叫端：`quota_gate.py:518` 是 `draining()`、`quota_messages.py:164` 是 halted 短路、`relay_machine.py:137`／`quota_escalation.py:334` 答續航與哨兵——Dev 的 grep 糾正屬實，任務書座標有誤；(b) `bd_effect` 改走事件列、`row_of()` 加 `bd` 欄——與附錄 §6.2／§6.3 實質等價；(c) Q-cross 守門取超集——同意（見〈一-C〉）；(d) 放寬後 cap 仍過 `quota_stability`——屬實且符合 PRD §4.2.4，標題數字因 `rec` 封頂而最高 2。 | 四處皆站得住；另兩處 Dev 未列的出入見 P3-09、P3-13 |
| 主控「棘輪標籤＝R213（非 R212）」裁決 | 見下段。 | 站得住（有條件，P3-11） |

**棘輪標籤裁決（R213 對 R212）的獨立判斷：站得住，三點記載須補。**
- 算式屬實：`repin_round_nets` 末列 R211＝+822、R212＝+796、R213＝+305；回歸鎖軌 R213＝305≤軌上限 309；主−軌＝0，款(11) 不計連升；R212 若再追加 +305 則主軌 487＋305 超過該輪上限 516（款(10)）。`_REPIN_APPROVED_ROUND_OVERAGE` 名冊 4／4 已滿，走例外需先上修名冊上限（砸溫度計）；搬 ~290 行史料有誤刪風險。三個出口中取「新標籤」是鎖自己列出的、成本最低的一個。本鏡跑 `test_adr_xplat001_c1c2_lock`（含 `test_quota_policy`，共 526 項）OK。
- 但標籤不是事件：`live_repin_round()` 只取稽核痕跡最大輪號，**不連結** R 系列檔名鐘（`current_round()`＝R212）。同一真實輪（R 系列鐘＝212）內 tools/tests 護欄層淨額合計 +1101（796＋305），大於該標籤上限 516＋軌上限 309＝825 的單輪合計；這是鎖的既有設計（標籤即帳戶），不是本列新造，登 P4（AR-13 備註）。
- R213 是最後一個尚未觸發到期義務的標籤：`_PHASE2_DUE_ROUND`＝213（判準 `live > due`，`test_adr_xplat001_c1c2_lock.py:7819`），`_REPIN_NET_CAP_DUE_ROUND`＝214 且目標 515。此後任何以 R214 為標籤的重釘將**同時**要付 Phase-2 追列與上限 516→515 兩筆義務。〈三-2〉只寫「由鎖自己在到期時喚醒，本列不預作」，沒點出兩者同時到期。


---

## 〈二〉P≤2 清單

**無。** 以下為本鏡評過、但依嚴重度口徑（`severity.md`：P2＝錯誤決策／漏攔／誤擋且有暴露證據）**未升到 P2** 的候選，列出理由供主控與其他鏡覆核：

| 候選 | 為何不是 P≤2 |
|---|---|
| 落款不綁視窗身分（週軸提前改錨，真實語料 2 次） | 前提在真實語料出現過，但當時沒有落款存在、沒有任何錯誤決策發生（暴露度只到「前提實現」，未到「錯誤決策」）；且該案實害有限（新視窗用量低、放寬在 free 帶幾乎無作用；改錨使 reset 變晚時落款反而提早失效＝保守）。登 AR-01（P4）。 |
| 清倉不涵蓋接力 band 判準②、`draining()`、簡報等 `decide()` 呼叫端 | 附錄 §1.3 明文「不進狀態機、不改 `draining()`／`reset_branch()`」，`quota_burndown.py` 檔頭〈誠實劃界〉已寫；A4 再開症狀字面限定 `--pace` 與派工。缺的是 PRD／證據的劃界句，不是錯誤決策。登 AR-02（P4）；劃界句併入〈六〉。 |
| `Burn.apply()` 未包 fail-closed（`active()` 有） | 構造性；`apply` 內無新的例外源（同樣的 `amort_for` 在 `decide()` 末段本就無保護地呼叫）。登 AR-03（P4）。 |
| 結案定義未經掌舵者明示追認 | 有掌舵者 standing 授權（「依最佳理想化代為決策」）、修訂表逐處自陳、掌舵者可隨時以 §16.5 (i) 推翻；無宣稱失實。降為流程面 P3-01。 |
| 棘輪標籤超前 R 系列鐘 | 為鎖自己列出的出口之一、算式屬實、全鎖綠；主控已在〈三-2〉如實寫出兩個鐘不同。降為記載補強 P3-11。 |
| A4「cap 由 1 升至 `cap_converge`」 | 證據檔〈三-3〉逐字是 `cap=2`＋遲滯說明，PRD 簡寫過度但可由同一引用核對。P3-02。 |

---

## 〈三〉P3（本輪改文字／記載；每條：座標、重現法、判準、處置）

**P3-01 驗收定義歸屬（Q1 根因的第三層：流程面）**
- 座標：主檔〈二-0〉第 32～39 行（兩層結論皆技術層）；PRD 修訂表 v2.1.17 列「各列歸格＝主控代決…非逐列明示追認」；證據〈一〉「T1 第七次貼同一份」。
- 重現法：對照 §16.1 ✅ 定義（「機制在、且有測試或鎖」）與 T1 第 2 問字面（「完成實作…所有功能！==> 請檢視驗證每個功能都已經完成 E to E 全功能驗證！」）。
- 判準：記載缺漏（無錯誤決策、無宣稱失實；各文件逐處自陳）＝P3。
- 處置：〈二-0〉補一句「定義歸屬：§16.1 結案定義為代決、未經掌舵者明示追認」；〈六〉Q1／Q2 答覆末尾附一個明確二選一請求（追認 §16.1 定義，或指名要實作的 ⏸ 列）——對應「僵局交還使用者決策」，同一 T1 已重貼七次即屬此型。不新增守衛碼。

**P3-02 A4 落款「cap 由 1 升至 `cap_converge`」寫成軸值、親驗的是標題值**
- 座標：PRD 第 2708 行 A4 列落款與第 24 行 v2.1.19 列同句；證據〈三-3〉`--pace` 逐字「現在可派 2 個 agent（硬上限 cap=2…）」「目前 cap=2 由遲滯維持（這條軸自己的 cap 是 4）」。
- 重現法：兩處並讀。
- 判準：宣稱先於查證（軸值當標題值）。
- 處置：改「標題 cap 1→2（遲滯維持；週軸自身 cap＝`cap_converge`，每 ≥300 秒最多放寬 1 階）；現在可派 1→2（`rec` 封頂 `cap_prepare`）」；〈三-1〉(d) 補「現在可派封頂 2」。

**P3-03 提交順序：三處「完成」字樣先於審查結論**
- 座標：PRD 第 24 行「四方…複審見證據檔」；帳本 DEF-200-528「fixed（2026-10-12）」；PRD 第 2708 行 ✅；證據〈四〉〈五〉「（待填）」。
- 重現法：`grep -n "待填" docs/06_quality/CrossPlatform_R212_BurnDown_FourParty_Evidence.md`。
- 判準：同 P3-02。
- 處置：審查結論與修復落檔後才提交；任一鏡判 P≤2 時三處同步回撤。

**P3-04 §6.1 列：症狀前半已實際觸發、字面仍留原樣**
- 座標：PRD 第 2670 行。
- 重現法：讀該列「再開症狀＝啟動自檢缺席的不變式所防之事實際發生（`bypassPermissions` 於非容器環境啟動、`.autoclaude/` 進了 commit）」與其後 `【2026-10-12】…再開症狀前半…與 §12 權限旗標列同一事件…格不變`。
- 判準：§16.1「一句具體可觀測」＋§16.5 末段；前半已被觸發、不變式 8 已落地，症狀字面卻仍把它描述成待發生。
- 處置：追記改寫為「殘存症狀＝7b／9 所防之事（`ALLOW_WITH_CAP` 上限值缺席、`.autoclaude/` 進 commit；附 sid 或 commit 座標）」，格不變。

**P3-05 未放寬理由字面為假（週軸低於 converge 帶）**
- 座標：`tools/lib/quota_burndown.py:137-148`（`_why`）、`:187-209`（`apply` 的 `kept` 分支）。
- 重現法：隔離實驗 E4（〈五〉）：週軸 55%／65%、短窗 8%、點名 `weekly_all` ⇒「未放寬：kind=session（已在放寬上限，無可再放）、kind=five_hour（已在放寬上限，無可再放）」。
- 判準：R-4.2.9-4 ⑤ 要求具名理由為真；該帶 R95 的 `amort_relaxed` 使攤提本就只出聲不收緊，並非「已在放寬上限」。訊息誤導、一次呼叫內可恢復＝P3。可達性：2026-10-12 當日 04:30～14:53 的真實燒帳列（週軸 53～67%）若當時已落款即會印出此句。
- 處置：`flagged` 為真且無變動時改印「攤提在此帶未收緊（無可放寬）」。

**P3-06 附錄 §5④ 與 §4.3 的順序字面互相矛盾**
- 座標：附錄第 330 行（§5 ④：「`cap/rec 聚合 → 清倉放寬 → must-finish 收斂 → model_hint`」）對第 272 行（§4.3：「跨軸聚合：仍是既有的 min…本段不改聚合，只改逐軸輸入」）；實作 `quota_policy.py:718-719`（放寬）早於 `gate_list`／`min`／`wrap`。
- 重現法：讀兩處＋`decide()`。
- 判準：文件內部矛盾；④ 的承重性質（must-finish 最後求值）不受影響。
- 處置：附錄加一則訂正注：「順序＝逐軸放寬→min 聚合→must-finish→model_hint；§5④ 的『聚合→放寬』字面作廢」。

**P3-07 BD-2′ 的規範文本只住證據檔、附錄仍寫「治不到」**
- 座標：PRD 第 24 行「規範文本＝…主控增補『BD-2′』〔證據檔〈二-2〉〕」；附錄 §4.1（「`five_hour`／`session`…今天不是 qualifying 軸」）、§9-1（「本條文對立案情境今天治不到」）。
- 重現法：讀兩處。
- 判準：規範性增補應住規範性文件；證據檔是帳本級治理文件、非規範。
- 處置：附錄加日期訂正注指向 BD-2′ 並寫出 Q-cross 定義（體例同 2026-09-02 盤點注）。

**P3-08 附錄 §3.1(ii)／§7.3「以 `resets_at` 字串為鍵、結構性不匹配」的前提與真實語料不符**
- 座標：附錄第 181 行、第 457 行；實作 `quota_burndown.py:102-128`（只比 `now < until_resets_at`）。
- 重現法：〈五〉真實語料統計：週軸 205 列 205 個相異字串（同窗亞秒抖動，距整點 −0.89～+1.00 秒）。
- 判準：設計文件對伺服器行為的假設與量測不符（文字面）。
- 處置：A4 落款劃界補一句「落款綁的是 `until` 時刻、不是視窗身分；同窗 `resets_at` 每次讀數皆不同字串，週軸另有提前改錨（真實語料 2 次）」；行為洞登 AR-01。

**P3-09 `BURNDOWN_CAP_CEILING` 未做、未列入出入清單**
- 座標：附錄第 447、451 行；`grep -rn BURNDOWN_CAP_CEILING tools AutoClaude/autoclaude env.shared .env.example` rc=1（零命中）。
- 判準：實作對附錄草案的出入應全列（〈三-1〉現列四項）。
- 處置：〈三-1〉補第五項：只准調小的營運旋鈕未做；上限直接取 `Policy.cap_notice`（可由 `AUTOSDD_QUOTA_CAP_NOTICE` 間接調小，但會同時改 notice 帶本身）。

**P3-10 幽靈鍵鎖被註解滿足，對「真讀取點被拆」失明**
- 座標：`tools/tests/test_context_budget_guard.py:9876-9890`（consumers＝quota_gate／hook／planner／relay_machine／model_roles 的文字串接，`assertIn(spec.name, consumers)`）；`quota_gate.py:1100` 註解含 `AUTOSDD_QUOTA_BURNDOWN_OFF`；真讀取點 `quota_burndown.py:60`（`OFF_ENV`）不在清單。
- 重現法：讀碼推得（把真讀取拆掉、保留註解，該鎖仍綠）；未做突變。
- 判準：弱鎖；Dev 報告 §6-2 已揭露「二選一」，〈三〉未記處置。
- 處置：把 `quota_burndown.py` 加進 consumers 元組（tools/tests +1 行，須重釘），或在〈三〉明記「以註解滿足、鎖弱」。擇一並記。

**P3-11 棘輪標籤裁決的記載補強（裁決本身站得住）**
- 座標：`tools/tests/test_adr_xplat001_c1c2_lock.py` 新增 R213 重釘列的理由欄（含一句把成長歸到另一輪標籤的預告式字樣）；證據〈三-2〉；`:7819`（Phase-2 `live > due`）、`:3285`（`_REPIN_NET_CAP_DUE_ROUND = 214`）。
- 重現法：〈五〉E7 唯讀印出 `live_repin_round=213`、`_PHASE2_DUE_ROUND=213`、`DUE_ROUND=214`。
- 判準：預告式句型與「不製造日期／輪號義務」原則有張力；兩筆到期義務同時到期未揭露；標籤≠事件。
- 處置：(1) 重釘列理由欄改事實句：「以新標籤 R213 重釘；回歸鎖軌 305＜軌上限 309；R212 主軌餘裕 29」；(2)〈三-2〉補「R213 為最後一個未觸發到期義務的標籤；以 R214 為標籤的重釘將同時觸發 Phase-2 追列與上限 516→515」；(3) 單一真實輪內淨額合計 +1101、標籤即帳戶，登 P4（見 AR-13 備註）。

**P3-12 清倉段在標題行與 `describe()` 行各印一次**
- 座標：證據〈三-3〉`--pace` 逐字；`quota_messages.py:775`（`pace_line` 的 `tail`）、`quota_policy.py:828`（`describe` 追加）。
- 判準：標題行是「現在可派幾個」的人讀入口，約 600 字的清倉段把數字埋掉；非失實＝P3（主控自列，此處判級）。
- 處置：標題行只留短標記（≤40 字，含落款 id 與「放寬 N 軸」），全文留 `describe` 行。

**P3-13 事件列 `cap` 記的是穩定化前的決策值**
- 座標：`quota_gate.py:962`（`log_decision`）早於 `:973-974`（`quota_stability.evaluate`）；真實檔 `~/.autosdd/traces/autosdd_burndown_events.jsonl` 唯一列 `"cap": 4`，同刻 `--pace` 標題 `cap=2`。
- 判準：事件列的 `cap` 會被讀成有效上限；實為 `decide()` 原值。
- 處置：欄名改 `decided_cap`，或在〈三-1〉(b) 加註「事件列 cap 為穩定化前的決策值」。

**P3-14 〈三-3〉「同一組軸」缺同讀數反事實輸出**
- 座標：證據〈三-3〉判讀 (1)「下令前後同一組軸（週軸 78%、短窗 29%）」；下令前 `--pace`（〈二-1〉）量測於 18:16（週 75%／短窗 8%），下令後量測於 19:32（78%／29%）。
- 重現法：E6（〈五〉）：以 `quota_burn.jsonl` 的 19:32:54 列重建六軸、r=5.0、`active_model=fable`、`burndown=None` ⇒ `cap=1 rec=1 band=prepare binding=five_hour`（note=amortized）；同讀數有落款 ⇒ `cap=4 rec=2`（與真實事件列 `autosdd_burndown_events.jsonl` 19:34:35 的 `cap=4 rec=2` 相符）。
- 判準：宣稱實質成立（本鏡已補重放），但證據檔沒有可貼的同讀數輸出。
- 處置：把 E6 的重放指令與兩行輸出收進〈三-3〉，或把「同一組軸」改寫為「相近讀數（週軸 75→78%、短窗 8→29%）」。


---

## 〈四〉P4 理論洞（只登記、不修；編號 AR-xx 為本鏡局部號，併入證據檔〈七〉時接全域連號 #58 之後）

| # | 洞（座標） | 暴露度（量法與結果） | 再開症狀（一句、可觀測） |
|---|---|---|---|
| AR-01 | 落款不綁視窗身分：`verdict`（`quota_burndown.py:102-128`）只比 `now < until_resets_at`，不比現讀被點名軸 `resets_at`；`Burn.until` 取自落款（`:211-224`） | 真實語料量測前提：週軸 `resets_at` 位移 8 次，其中提前改錨 2 次（2026-09-10、2026-09-17）；落款存活由構造實驗 E3 重現；真實落款期間尚無改錨發生 ⇒ 前提實現、無錯誤決策 | `autosdd_burndown_events.jsonl` 有 `bd` 列的時段內，同時段 `quota_burn.jsonl` 被點名軸的 `resets_at` 與落款 `until_resets_at` 相差 >1 小時（附兩檔列座標） |
| AR-02 | 清倉不涵蓋 `decide()` 其他呼叫端：`relay_machine.py:137`（接力 band 判準②，只認 free／notice）、`quota_escalation.py:334`、`quota_gate.py:518`（`draining`）、`quota_messages.py:164`（halted 短路） | 讀碼；`quota_burndown.py` 檔頭〈誠實劃界〉已寫，PRD／證據未寫；現況週軸 81%（converge）⇒ 若此刻有無人續跑窗，`band_ok` 為假 | 落款效期內出現 `relay_stopped why=band`（附 sid＋resume log 列＋落款 id） |
| AR-03 | `Burn.apply()` 未包 fail-closed：`quota_policy.py:718-719` 無 try，`active()` 有 | 構造性（讀碼）；`apply` 內無新例外源 | 落款在場時 PreToolUse hook stderr 出現含 `quota_burndown` 的 traceback（附 sid＋stderr） |
| AR-04 | 落款載體三個劃界：(a)「偽造可對帳」無對帳器——`readings_at_issue` 只在寫入端存，消費端只驗 `core_signature`；(b) `tools/lib/quota_burndown.py` 不在 `block_destructive_git.py:1445` `_GOV_EXACT`（`quota_policy_env.py`、`quota_stability.py`、`relay_machine.py` 同樣不在名冊）；(c) 落款住專案根外，無人窗口能否寫它取決於權限姿態（`settings.unattended.json` 的額外目錄只有 `~/.autosdd/handback`、續跑窗 argv 另加 `~/.autosdd/plans`，皆不含 `~/.autosdd/traces`；allow 清單不含 `quota_burndown.py` CLI） | 構造性；(c) 為讀碼推得、未實測 | 無人窗口逐字稿對 `autosdd_burndown_directive.json` 出現 Write／Edit／`--issue` 呼叫（附 sid＋seq），或落款 `readings_at_issue` 與同時刻 `quota_burn.jsonl` 讀數不符 |
| AR-05 | 底線②③ 為具名清單、unknown kind 預設 eligible：`_eligible`（`:131-135`） | 今日 unknown 軸 `nimbus_quill` 因 `resets_at` 不明被時鐘合取項擋下；其餘構造 | 清倉文字「本次放寬」段出現 `kind` ∉ `Q.KNOWN_KINDS` |
| AR-06 | 燃燒帳 `bd` 欄語意＝呼叫當下授權，而列 `ts`＝量測時刻 | 真實 1 筆：列 `ts=2026-10-12T19:32:54+08:00` 帶 `bd=45c49b8e35`，落款 `issued_at=19:34:11`；無決策消費該欄 | 以 `bd` 非空列統計「授權期間燃燒」時，首列 `ts` 早於落款 `issued_at` |
| AR-07 | §16.2 無機械普查：`tools`、`tools/tests` 無鎖綁四格值域、101 列、⏸ 紀律（只有本鏡一次性腳本） | 本鏡腳本 0 違規 ⇒ 無暴露 | §16.2 出現第五種格字面或空格欄，或 ⏸ 症狀含輪號／日期，而全套測試仍綠 |
| AR-08 | 未驗接縫清單散落三處、無單一清單：主檔〈十一-5〉末列、〈六-3〉兩段追記、Run4〈三〉末段（各自自稱「已知項、非完整宣告」） | 〈一-A〉對帳表：兩表未列者 3 類（人類面、時區、痕跡純度）＋清倉層 3 個消費面 | 兩處清單對同一接縫的已驗／未驗標記相反 |
| AR-09 | 接縫表只有 launchd 欄；Windows 專屬接縫無列：S2／S8／S9／S10／S12 為 launchd 構造；`SchtasksBackend`（`PRINCIPAL-FALLBACK=default-interactive` 回退、`pythonw` 無 console、BOM／CRLF 落檔、NextRunTime 憑證）無 S 列 | 讀碼；ONBOARDING 表② Windows 欄上次量測 2026-10-04 為測試套件基線、非喚醒鏈 | Windows 真機任一 `sentinel_woken`／`woken` 痕跡之後缺 `probed`／`resumed`／`relay_done` 對應事件（附 sid＋resume log） |
| AR-10 | 人類面預設通道弱：桌面通知預設關（`AUTOSDD_DESKTOP_NOTIFY` opt-in）、紙條住 `$TMPDIR`（揮發）、持久結局檔＋未讀游標為唯一預設通道；顯示路徑只有游標被消耗的間接證據 | Run4 一筆 `notify_rc=-2`＋紙條；`autosdd_unattended_outcome.cursor`＝4 | 掌舵者回報「續跑停了而我不知道」（附 sid＋`autosdd_unattended_outcome.jsonl` 列） |
| AR-11 | 真實痕跡含夾具列：`~/.autosdd/traces/autosdd_unattended_outcome.jsonl` 第 1～3 列 session＝`sid-chain`／`sid-noprog`／`sid-refuse`，handback 指向 `/var/folders/…/replay-r113-chain-*`（2026-10-10T00:29:57+0800）；依 `reason` 計 `no_progress` 列數會得 3（真實只有 1） | 真實 3 列 | 該檔出現 session 非 UUID 形的列 |
| AR-12 | 行程 env 空字串語意不同：harness 的 `policy_env()`＝`{**檔案層, **os.environ}` 讓空字串遮住共享值；引擎與 doctor 把空白當不存在 | 構造實驗 E5：harness 95／引擎 98／doctor 98 | `--env-doctor` 顯示〔env.shared〕值，而同機 `--pace` 的 halt 線為出廠值 |
| AR-13 | hub 飽和、私有函式耦合、標籤即帳戶：`quota_gate.py` 斷言行 497／500（Dev 報告 §1）；`Burn.masks`／`apply` 直呼 `quota_policy` 私有函式 `_in_cap_gate`／`_rows`／`_amort_skip`／`_delta_minutes`；單一真實輪內護欄層淨額 +1101 對單輪合計上限 825 | Dev 報告量測值；E7 | 要動 `quota_gate.py` 的守衛面功能被 LOC 閘擋下；或上述私有函式改簽章時 `test_quota_burndown` 轉紅 |
| AR-14 | 本機 naive 字串送排程器、無年份欄：`register_endurance`（`session_resume_planner.py:781-785`）→ `New-ScheduledTaskTrigger -At`／launchd `StartCalendarInterval` | Asia/Taipei 無 DST，本機無暴露；`_calendar_still_ahead` 已守過期 calendar | 跨 DST 或換時區後哨兵／續跑在錯的時刻醒（附 `sentinel_rearmed` 的 `fire_at` 與實際 `woken` 時戳） |


---

## 〈五〉本鏡跑過的指令與 rc（逐字；工作目錄 `/Users/wuweihong/Antigravity/AISDCL_Agent`）

通則：所有 `tools/tests` 子集皆 `cd tools/tests`、`export AUTOSDD_SENTINEL_OFF=1`、`unset AUTOSDD_PARALLEL_TESTS`，直譯器 `../../.venv/bin/python`；隔離實驗腳本住 scratchpad `arch_exp/`（`burn_probe.py`／`burn_probe2.py`／`burn_probe3.py`／`blank_env_probe.py`／`cf/cf.py`／`cf/cf2.py`／`corpus_stats.py`／`prd_census.py`），以 `AUTOSDD_TRACE_DIR`／`AUTOSDD_QUOTA_CACHE_DIR` 指向 scratchpad 子目錄；真實 `~/autosdd_quota.json`、`quota_burn.jsonl`、落款檔皆先**複製**到 scratchpad 再讀。未跑 `--pace`、未呼叫 `quota_meter` 補量、未碰 launchd／哨兵／`.claude/`、未動真實落款。

### 五-1 repo 現況與 PRD 普查

`git status --short`、`git diff --stat`：與任務書附帶的工作樹快照一致（15 個改動檔＋1 個未追蹤證據檔；`quota_burndown.py`／`test_quota_burndown.py` 為 intent-to-add）。

`.venv/bin/python arch_exp/prd_census.py`（rc=0）：
```text
§16.2 表列數: 72 ｜結案格: {'➖': 33, '⏸': 29, '📎': 8, '✅': 2}
矩陣原判分佈: {'➖': 10, '⚠️(M)': 23, '❌': 11, '⚠️(S)': 24, '⚠️(L)': 4}
未重列 ✅ 矩陣 ID 數: 29 ｜四格合計: 31 + 33 + 29 + 8 = 101
⏸ 列數: 29 ｜寫法紀律命中: [(2670, '日期', ['2026-10-12'])]
➖無依據座標／📎無殘留字樣: []
```
（⏸ 唯一命中的日期在第 2670 行 §6.1 列：位於症狀句之後的 `【2026-10-12】` 落款註記內，見 P3-04。）

### 五-2 單元測試子集

`cd tools/tests && ../../.venv/bin/python -B -m unittest test_quota_burndown test_quota_env_layers`（RC=0）：
```text
....................................................
----------------------------------------------------------------------
Ran 52 tests in 1.825s

OK
```
`cd tools/tests && ../../.venv/bin/python -B -m unittest test_quota_policy test_adr_xplat001_c1c2_lock`（RC=0；含 5 支 `TestGuardLayerRatchet`）：
```text
Ran 526 tests in 20.324s

OK
[Scan-H triplet] UEP=5 AC=47 GLC_FILES=93 GLC_LINES=116734
```

### 五-3 其他閘門與對帳

- `.venv/bin/python AutoClaude/tools/check_loc_budget.py --json`：rc=0；`total_violation=False`、`absolute_violations`／`tier_violations`／`special_violations`／`root_tools_violations` 皆空。
- `.venv/bin/python tools/sync_onboarding_baselines.py --check-snapshot`：rc=0。
- `.venv/bin/python tools/check_defect_log_crossref.py --unresolved-count`：rc=0；`未結列數＝0／全部 229 列｜warn=86 fail=98`。
- `git show --stat --format=%h 1818de87fbbb5a96673008d50eeb1e619ce22223` 末行：`29 files changed, 1543 insertions(+), 47 deletions(-)`。
- `gh run list --commit 1818de87fbbb5a96673008d50eeb1e619ce22223 --json name,conclusion,status,databaseId`：rc=0；六筆皆 `"conclusion":"success","status":"completed"`（arch-fitness 38231604962／drift-daily 38230947003／windows-compat-ci 38230301093／root-infra-ci 38230301052／AutoClaude CI 38230301082／macos-compat-ci 38230301062）。
- `grep -rn BURNDOWN_CAP_CEILING tools AutoClaude/autoclaude env.shared .env.example`：rc=1（零命中）。
- `git check-ignore -v .env.bak.20261012T000000Z AutoClaude/.env.bak.20261012T000000Z env.shared`：rc=0；命中 `.gitignore:36:.env.*` 與 `AutoClaude/.gitignore:18:.env.*`；`env.shared` 無輸出（追蹤檔，`git ls-files` 有列）。
- 抽驗 Run4 真痕跡（唯讀 `cat`）：`~/.autosdd/traces/autosdd_sentinel_bootout_AutoSDD_Sentinel_14fb33dc-4ffc-40c9-b62b-9dcf801d02f4.log` 第 5 行逐字 `{"event": "arm_skipped_inside_job", "label": "AutoSDD_Sentinel_14fb33dc-4ffc-40c9-b62b-9dcf801d02f4", "job_pid": 63538, "pid": 63598, "ppid": 1, "xpc": "0", "at": "2026-10-12T13:55:03+0800"}`（與 Run4〈三〉「`xpc="0"`、`ppid=1`」相符）；`autosdd_resume_cost.jsonl` 末列 `model=claude-haiku-5-5`、`recorded_at=2026-10-12T13:55:17+08:00`；`autosdd_unattended_outcome.jsonl` 共 4 列（其中前 3 列為夾具，見 AR-11）。
- 真實落款與事件列（唯讀 `cat`）：`autosdd_burndown_directive.json` 的 `id=45c49b8e35`、`axis_kind=weekly_all`、`until_resets_at=2026-10-17T17:59:59.540762+00:00`、`core_signature` 六軸＋帳號指紋；`autosdd_burndown_events.jsonl` 唯一列 `{"bd": "45c49b8e35", "cap": 4, "effect": "relaxed", "rec": 2, "ts": "2026-10-12T19:34:35.494060+08:00"}`，均與證據〈三-3〉相符。

### 五-4 隔離實驗（純函式，零 I/O）

**E1／E2／E3**（`arch_exp/burn_probe.py`；E1＝`_merge` 對 20×20 格全窮舉；E2＝另加一個 40000 分鐘窗的軸；E3＝落款 `until`＝+7663 分鐘、現讀被點名軸 `resets_at`＝+1500 分鐘且用量 29%）：rc=0
```text
E1 _merge 全窮舉(400 組合) 違規數 = 0 []
E1 含『n 比 b 更緊』的組合也在上述 400 組合內：違規數同上
E2 text: ｜🔥清倉模式生效中（落款 bdX，發令 2026-10-12T10:37:00+00:00，作用至 kind=weekly_all reset 2026-10-17T18:20:00+00:00；效期剩 7663 分鐘／must-finish 門檻 5 分鐘）⇒ 本次放寬：kind=weekly_all cap 2→4 rec 1→2、kind=seven_day cap 2→4 rec 1→2；未放寬：kind=session（與被點名軸不同窗）、kind=five_hour（與被點名軸不同窗）、kind=monthly_x（與被點名軸不同窗）
E3 提前改錨後 active() = ('bdE3', '2026-10-17T18:20:00+00:00', 7663) | 現讀 named.resets_at = 2026-10-13T11:37:00+00:00
```
**E2 補充**（`arch_exp/burn_probe3.py`）：rc=0
```text
E2 amort.total_kind = monthly_x | rate_kind = session
```
**E4**（`arch_exp/burn_probe2.py`；週軸 55%／65%／72%、短窗 8%、點名 `weekly_all`、r=5.0）：rc=0
```text
weekly=55.0: 無落款 cap=4 rec=2 | 有落款 cap=8 rec=4 effect=relaxed
     本次放寬：kind=weekly_all cap 4→8 rec 2→4、kind=seven_day cap 4→8 rec 2→4；未放寬：kind=session（已在放寬上限，無可再放）、kind=five_hour（已在放寬上限，無可再放）、kind=spend（fallback 不納入）
weekly=65.0: 無落款 cap=4 rec=2 | 有落款 cap=8 rec=4 effect=relaxed
     本次放寬：kind=weekly_all cap 4→8 rec 2→4、kind=seven_day cap 4→8 rec 2→4；未放寬：kind=session（已在放寬上限，無可再放）、kind=five_hour（已在放寬上限，無可再放）、kind=spend（fallback 不納入）
weekly=72.0: 無落款 cap=1 rec=1 | 有落款 cap=4 rec=2 effect=relaxed
     本次放寬：kind=session band prepare→free cap 1→8 rec 1→4、kind=weekly_all cap 2→4 rec 1→2、kind=five_hour band prepare→free cap 1→8 rec 1→4、kind=seven_day cap 2→4 rec 1→2；未放寬：kind=spend（fallback 不納入）
```
**E5**（`arch_exp/blank_env_probe.py`；根 `env.shared` 設 `AUTOSDD_QUOTA_HALT_PCT=98`，行程 env 三種狀態；用 `.venv` 直譯器）：rc=0
```text
[未設] 真 harness(load_policy∘policy_env)=98.0  引擎(_quota_env)=98.0  doctor: AUTOSDD_QUOTA_HALT_PCT                       = 98〔env.shared〕
[設成空字串] 真 harness(load_policy∘policy_env)=95.0  引擎(_quota_env)=98.0  doctor: AUTOSDD_QUOTA_HALT_PCT                       = 98〔env.shared〕
[設成95] 真 harness(load_policy∘policy_env)=95.0  引擎(_quota_env)=95.0  doctor: AUTOSDD_QUOTA_HALT_PCT                       = 95〔process-env〕
```
**E6**（同讀數反事實；`arch_exp/cf/cf2.py`：以真實 `quota_burn.jsonl` 的列重建六軸、r=5.0、不帶落款）：rc=0
```text
現行快取 axes: [('session', 43.0, '2026-10-12T14:09:59.706052+00:00'), ('weekly_all', 81.0, '2026-10-17T17:59:59.706074+00:00'), ('weekly_scoped', 45.0, '2026-10-17T17:59:59.706255+00:00'), ('five_hour', 43.0, '2026-10-12T14:09:59.706052+00:00'), ('seven_day', 81.0, '2026-10-17T17:59:59.706074+00:00'), ('spend', 0.0, None)]
2026-10-12T18:16:51+08:00 model=None: 無落款 cap=1 rec=1 band=prepare binding=five_hour reason=ok,amortized,burn-ahead,burn-ahead+model-scoped-excluded,gate_excluded=spend+weekly_scoped,missing
2026-10-12T18:16:51+08:00 model='fable': 無落款 cap=1 rec=1 band=prepare binding=five_hour reason=ok,amortized,burn-ahead,gate_excluded=spend,missing
      five_hour 8.0 band prepare hor far cap 1 note amortized
      session 8.0 band prepare hor far cap 1 note amortized
      seven_day 75.0 band converge hor far cap 2 note burn-ahead
      spend 0.0 band free hor none cap None note missing
      weekly_all 75.0 band converge hor far cap 2 note burn-ahead
      weekly_scoped 41.0 band free hor far cap None note burn-ahead
2026-10-12T18:16:51+08:00 model='sonnet': 無落款 cap=1 rec=1 band=prepare binding=five_hour reason=ok,amortized,burn-ahead,burn-ahead+model-scoped-excluded,gate_excluded=spend+weekly_scoped,missing
2026-10-12T19:32:54+08:00 model=None: 無落款 cap=1 rec=1 band=prepare binding=five_hour reason=ok,amortized,burn-ahead,burn-ahead+model-scoped-excluded,gate_excluded=spend+weekly_scoped,missing
2026-10-12T19:32:54+08:00 model='fable': 無落款 cap=1 rec=1 band=prepare binding=five_hour reason=ok,amortized,burn-ahead,gate_excluded=spend,missing
      five_hour 29.0 band prepare hor far cap 1 note amortized
      session 29.0 band prepare hor far cap 1 note amortized
      seven_day 78.0 band converge hor far cap 2 note burn-ahead
      spend 0.0 band free hor none cap None note missing
      weekly_all 78.0 band converge hor far cap 2 note burn-ahead
      weekly_scoped 44.0 band free hor far cap None note burn-ahead
2026-10-12T19:32:54+08:00 model='sonnet': 無落款 cap=1 rec=1 band=prepare binding=five_hour reason=ok,amortized,burn-ahead,burn-ahead+model-scoped-excluded,gate_excluded=spend+weekly_scoped,missing
```
（本鏡另以真實快取複本 `cf/cf.py`〔`measured_at=2026-10-12T19:58:09+08:00`，週軸 81%／短窗 43%〕對照有／無落款：無落款 `cap=2 rec=1 band=converge binding=seven_day`、有落款 `cap=4 rec=2`；session／five_hour `band prepare→free cap 2→8 rec 1→8`，週軸兩軸 `cap 2→4 rec 1→2`，`weekly_scoped`／`spend` 逐格不動。）

**E7**（唯讀 import 棘輪鎖模組印常數，`cd tools/tests`）：rc=0
```text
live_repin_round = 213
_REPIN_NET_CAP_DUE_ROUND = 214  TARGET = 515
_PHASE2_DUE_ROUND = 213  last review = (208, '[提案]')  window= 5
net_cap_for_round(213) = 516  (212)= 516  (214)= 516
repin nets last 6: [(208, 309), (209, 131), (210, 21), (211, 822), (212, 796), (213, 305)]
lane nets last 6: [(208, 309), (209, 131), (210, 21), (211, 309), (212, 309), (213, 305)]
_REGRESSION_LANE_ROUND_CAP = 309
```

### 五-5 真實語料統計（唯讀；`arch_exp/corpus_stats.py`，rc=0）
```text
quota_burn.jsonl 總列數 = 442 ｜含 resets_at 的列 = 205
同列 resets_at 字串全等 weekly_all＝seven_day：205／205
同列 resets_at 字串全等 session＝five_hour：203／203
同列 resets_at 字串全等 weekly_all＝weekly_scoped：0／204
weekly_all resets_at 相異字串數／列數 = 205／205
weekly_all 距整點偏差秒 min／median／max = -0.894 0.119 1.004
週軸 resets_at 位移 >1 小時的事件（ts｜舊 reset→新 reset｜用量變化｜舊視窗是否已到期）：
  2026-09-06T02:31:57+08:00 ｜ 2026-09-05T17:59:59.629563+00:00 → 2026-09-12T18:00:00.407273+00:00 ｜ 35.0 → 0.0 ｜ 已到期
  2026-09-10T16:31:44+08:00 ｜ 2026-09-12T18:00:00.479302+00:00 → 2026-09-11T21:59:59.928196+00:00 ｜ 75.0 → 29.0 ｜ 未到期（提前改錨）
  2026-09-12T11:03:26+08:00 ｜ 2026-09-11T22:00:00.849152+00:00 → 2026-09-18T22:00:00.766758+00:00 ｜ 81.0 → 2.0 ｜ 已到期
  2026-09-17T10:06:59+08:00 ｜ 2026-09-18T21:59:59.965357+00:00 → 2026-09-19T18:00:00.019182+00:00 ｜ 67.0 → 46.0 ｜ 未到期（提前改錨）
  2026-09-20T02:49:24+08:00 ｜ 2026-09-19T18:00:00.729568+00:00 → 2026-09-26T18:00:00.958715+00:00 ｜ 72.0 → 2.0 ｜ 已到期
  2026-09-27T09:25:03+08:00 ｜ 2026-09-26T18:00:00.032667+00:00 → 2026-10-03T17:59:59.695699+00:00 ｜ 57.0 → 0.0 ｜ 已到期
  2026-10-05T21:31:43+08:00 ｜ 2026-10-03T18:00:00.118885+00:00 → 2026-10-10T17:59:59.591050+00:00 ｜ 94.0 → 0.0 ｜ 已到期
  2026-10-11T02:04:00+08:00 ｜ 2026-10-10T18:00:00.316608+00:00 → 2026-10-17T18:00:00.116155+00:00 ｜ 93.0 → 0.0 ｜ 已到期
fp 相異值（次數）： [(365, '["account=34cd3507237f", "five_hour", "session", "seven_day"'), (73, 'null'), (3, '["five_hour", "session", "seven_day", "spend", "weekly_all",'), (1, '[]')]
autosdd_unattended_outcome.jsonl： [('sid-chain', 'exhausted', '2026-10-10T00:29:57+0800'), ('sid-noprog', 'no_progress', '2026-10-10T00:29:57+0800'), ('sid-refuse', 'no_progress', '2026-10-10T00:29:57+0800'), ('14fb33dc-4ffc-', 'no_progress', '2026-10-12T13:55:17+0800')]
```

---

## 〈六〉文件訂正清單（對主控骨架與前六次宣稱的措辭訂正）

**A. 對本列證據檔骨架（`CrossPlatform_R212_BurnDown_FourParty_Evidence.md`）**

1. 〈二-0〉（主檔）／〈六〉Q1 答覆：補第三層根因「定義歸屬」——結案定義（§16.1）為代決、未經掌舵者明示追認；並在答覆末尾附一個明確二選一請求（追認，或指名要實作的 ⏸ 列）。對應 P3-01。
2. 〈三-1〉出入清單：(d) 句尾補「標題『現在可派』因 `rec` 封頂 `cap_prepare` 最高 2」；新增第五項「附錄 §7.2 草案鍵 `BURNDOWN_CAP_CEILING` 未做（上限直接取 `Policy.cap_notice`）」、第六項「事件列 `cap` 為穩定化前的決策值」。對應 P3-02、P3-09、P3-13。
3. 〈三-2〉：補「R213 為最後一個未觸發到期義務的標籤；以 R214 為標籤的重釘將同時觸發 Phase-2 追列與上限 516→515」；並說明單一真實輪內淨額合計 +1101（標籤即帳戶，鎖不連結 R 系列鐘）。對應 P3-11。
4. 〈三-3〉判讀 (1)：把「下令前後同一組軸（週軸 78%、短窗 29%）」改為「相近讀數」，或收進 E6 的同讀數重放輸出（本鏡已跑：無落款 `cap=1 rec=1 band=prepare binding=five_hour`，有落款 `cap=4 rec=2`）；判讀 (2) 依 P3-12 處置。對應 P3-14、P3-12。
5. 〈四〉〈五〉：填入四鏡判決與處置後再提交（P3-03）。

**B. 對 PRD（`AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`）**

6. 第 2708 行 A4 落款：把「`--pace` cap 由 1 升至 `cap_converge`」改為「`--pace` 標題 cap 1→2（遲滯維持；週軸自身 cap＝`cap_converge`，每 ≥300 秒最多放寬 1 階），現在可派 1→2」；劃界補三句：效果有界（`rec` 封頂 `cap_prepare`）；落款綁 `until` 時刻、不綁視窗身分；清倉只涵蓋 `--pace` 與派工 hook（接力 band 判準②、`draining`、簡報、idle-prepare 不帶授權）。對應 P3-02、P3-08、AR-02。
7. 第 24 行 v2.1.19 修訂列：「四方…複審見證據檔」在審查結論填入前不得提交（P3-03）；其餘措辭不動。
8. 第 2670 行 §6.1 列追記：改寫為「殘存症狀＝7b／9 所防之事」，格不變（P3-04）。
9. §16.3 (b) 為 v2.1.17 當日快照（✅29／⏸31），**現況＝✅31／➖33／⏸29／📎8＝101**；對掌舵者報數與回答 Q2 一律用現況（本鏡腳本重數，見〈五-1〉）。

**C. 對清倉附錄（`PRD_Amendment_R108_BurnDown_Addendum.md`；沿用 2026-09-02 盤點注體例加日期訂正注，不改原文）**

10. 注一：BD-2′ 的 Q-cross 定義與其結構守門（供給軸須 Q-same；回的是原始 pct；Q-cross 不享 BD-1）（P3-07）。
11. 注二：順序以 §4.3 為準＝逐軸放寬→min 聚合→must-finish→model_hint，§5④ 的「聚合→放寬」字面作廢（P3-06）。
12. 注三：§3.1(ii)／§7.3「以 `resets_at` 字串為鍵」的前提與真實語料不符（同窗每次讀數皆不同字串；週軸提前改錨 2 次），實作為 `now < until_resets_at` 時刻比較（P3-08）；§9-5 觀察項已量測：`weekly_all`＝`seven_day` 205／205、`session`＝`five_hour` 203／203、分軌軸 0／204。
13. 注四：`BURNDOWN_CAP_CEILING` 未做（P3-09）。

**D. 對前六次響應宣稱的措辭**

14. 「Windows 零真機樣本」→「R212 各列範圍內無 Windows 真機樣本（歷史輪有；喚醒鏈程式已多輪變動，歷史樣本不外推）」。
15. 接縫表的「真」→ 一律限定詞「真 launchd（mac）」；「收斂」→「mac launchd 到點後尾段在已列接縫上無已知缺陷；症狀驅動」。
16. Q2「完成實作 PRD」→「101 列依 §16.1 定義全數歸格；✅＝機制在、有測試或鎖，不是真機走通；⏸／➖ 計 62 列為代決歸格」。
17. Q3「harness 與引擎同序同語意」→「同序；語意同，唯行程 env 為空字串時 harness 取出廠值、引擎與 doctor 取共享值（構造性，AR-12）」。
18. Q4「不需要馬上切到 Windows」→ 附註：S2／S8／S9／S10／S12 五個 launchd 專屬接縫在 Windows 無對應樣本；首次 Windows 續航窗即為驗證（AR-09）。

**E. 收尾實務提醒（不屬判級）**

19. 本鏡建議的 P3-10 處置若採「加 consumers 元組一行」，tools/tests 回歸鎖軌餘裕只剩 4 行（305／309），任何更大的測試增補需先搬史料抵銷並重釘；P3-05 若改 `quota_burndown.py` 理由字面，須重跑 `test_quota_burndown`（BD-9 的字面斷言）與 M7 判準。
20. 四鏡 findings 檔皆命中 `CrossPlatform_*.md` 發現面，須由主控一併登記到 `tools/lib/governance_docs.py`。
