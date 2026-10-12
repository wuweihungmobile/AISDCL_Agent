VERDICT: APPROVE
理由：清倉模式（DEF-200-528）從附錄規格到函式到鎖的追溯成立、無 P≤2，PRD §16.2 全表機械核對無破損引用；但「現在可派」多 1 只發生在被點名軸低於 prepare 錨點（出廠 85%）時（本機週軸 83% 正逼近）、A4 落款與骨架有多處措辭過樂觀、Q2「逐功能 E to E」半句前六次從未被回答，三者須在 commit 前訂正（〈三〉〈六〉）。

# CrossPlatform R212 第五列 SA 鏡 findings（需求追溯；唯讀）

## 〈零〉體例與範圍

- 角色＝SA 鏡（需求追溯，Sonnet 唯讀）。本鏡沒有改任何 repo 檔（除本檔）、沒有 commit、沒有碰 `.claude/`、launchd、哨兵。作業期間（約 20:27 起）工作樹出現主控的新編修（附錄訂正注、骨架、PRD、主檔證據；見〈七〉），非本鏡所為；本檔〈一〉～〈六〉以本鏡讀取當時（約 19:40～20:25）的版本為準，座標與行號亦然。
- 標記：〔本鏡親跑〕＝本鏡當回合跑的指令與輸出；〔讀檔〕＝讀碼或讀證據檔；〔逐字稿〕＝唯讀讀本 session 逐字稿（`~/.claude/projects/<專案 slug>/ed1c9022-22cc-4974-a8b3-9d4ebfa5f6bd.jsonl`，行號＝0 起算的 jsonl 行序）；〔推論〕＝無直接輸出的推得。
- 零信任：對主控骨架、前六次宣稱、Dev 報告一律重驗。為保獨立，本鏡沒有讀其他鏡的 findings 檔（工作樹已出現 `CrossPlatform_R212_Row5_Findings_Architect.md`，未開）。
- 本鏡沒做：根層全套（QA 鏡跑）、`--pace`（會動快取與圍籬）、`wakechain_e2e.py --run`（真機燒額度）、任何額度端點刷新。唯一的網路呼叫＝`gh run list --commit <完整 sha>` 唯讀查詢。
- 突變實驗全在隔離副本（scratchpad `sa/mut/repo/tools/{lib,tests}`），repo 本體零改動；指令與結果檔見〈五〉。
- 判決摘要：P≤2＝0；P3＝11（commit 前必改 4：P3-1、P3-2、P3-3、P3-8）；P4＝13；〈六〉文件訂正清單 28 條（A1～F6）。
- 行政：本檔名符合 `CrossPlatform_*.md` 命名慣例；本鏡 20:3x 重讀 `git diff tools/lib/governance_docs.py`，四份 Row5 findings 已由主控登記進 `_GOVERNANCE_DOCS`，`python tools/check_defect_log_crossref.py` rc=0（具名治理文件 172 份皆已登記、未逾體積上限）。

## 〈一〉對四問宣稱的逐項核對表

欄位：子項｜前六次宣稱｜本鏡驗到（座標）｜判定（完備／部分／未做）。

### 一-0 授權與口徑（本窗 T1 原文的一句話，骨架與任務書引文都漏了）

| 子項 | 前六次宣稱／骨架 | 本鏡驗到 | 判定 |
|---|---|---|---|
| T1 授權句 | 骨架〈一〉與脈絡包 A 逐字引了四問與「派出 Architect／SA／SD／QA」，沒有引授權句；骨架〈二-2〉卻以「掌舵者 T1 授權『依最佳化代決』」為設計裁決依據 | 〔逐字稿第 12 行〕T1 貼文逐字含：「以上若需要我決策，請依照最佳化, 最理想, 最適當的解決方案，我授權幫我決策, 若真需要我決定, 請以最簡單的解釋, 讓我互動選項決策」。授權句存在，〈二-2〉的依據成立；但〈一〉的 T1 原文應補上這句，否則〈二-2〉的依據在檔內查無出處。另：授權句同時要求「真需要我決定時用互動選項、最簡單的解釋」——本列有一題真需要他決定（見〈一-5〉效果帶），前六次中本鏡查得到的決策題（Run4〈一〉W4）用的是文字題（「說『重開第 N 項／全部重開』」），不是互動選項 | 部分 |
| T1 貼文含前一輪的結論 | 前六次把貼文當「第七次同題」 | 〔逐字稿第 12 行〕貼文＝前一輪結論三句＋四問＋授權句；也就是掌舵者每次把上一輪結論與四問一起貼回。結論三句是他唯一讀到的答案，所以其中措辭（〈六-F〉）比證據檔更重要 | 說明 |

### 一-1 問 1（找根因、徹底解決、想盡辦法完成收斂）

| 子項 | 前六次宣稱 | 本鏡驗到（座標） | 判定 |
|---|---|---|---|
| 1a 找到「沒法完成收斂」的根因 | 兩層：A-1 入口時間閘缺席；喚醒鏈接縫從沒在真排程器上整段跑過；收斂＝症狀驅動（主檔〈二-0〉） | 〔讀檔〕主檔 `CrossPlatform_R212_WakeChain_EnvLayer_Evidence.md` 第 32～40 行三點屬實，與 Run4〈二〉〈三〉互相對得上。本鏡補第三層（需求層）：七次同題貼文＝掌舵者對「收斂終點」的字面要求（所有功能＋逐項 E to E）與 PRD §16.1 的命題（101 列各落四格）之間沒有他明示追認——PRD 修訂表 v2.1.17 列自陳「各列歸格＝主控代決（掌舵者授權…，非逐列明示追認）」。這一層沒有被當成「沒法收斂的根因」寫出來，只在 Run4〈一〉W4 以「兩讀並陳」帶過 | 部分（工程層完備；需求層根因未明寫） |
| 1b 徹底解決 | 5 個真機暴露缺陷已修；跑法④ 22 項判決全過；入庫 `tools/probe/wakechain_e2e.py` | 〔本鏡親跑〕`python tools/probe/wakechain_e2e.py --selftest` rc=0，尾行 `SELFTEST rc=0（bypass 為負對照，必須紅在 S2／S3／S5a／S5b）`；抽跑喚醒鏈相關模組 `test_sentinel_tick_e2e_r145`（12 項）、`test_wake_chain_halt_r278`（58 項）、`test_mac_endurance_r83`（133 項）rc=0（〈五〉）。已走過的真機面與未走過的面，Run4〈三〉末段逐項列出（真 429 寫標記端、`RELAY_NEXT`／`quota_stop`／`relay_exhausted`、FRESH／PATROL、24 小時多次 reset、睡眠喚醒、R212 範圍內 Windows 真機樣本 0 筆）；本鏡讀過的主檔〈二-0〉〈六-3〉〈八-4〉與 Run4〈一〉〈三〉〈五〉內，未發現「寫成已驗而實未驗」的句子 | 部分（已覆蓋面完備且可重驗；未覆蓋面如實列出） |
| 1c 想盡所有辦法 | 症狀驅動收斂；Windows 清單留該機 | 本鏡找出三件前六次沒做、成本低的辦法：①把 Q2 的定義分歧用互動選項交給掌舵者（授權句明文要求）；②§16.2 📎 八列中 Mac 零成本可補的件（〈一-2-d〉給確切指令）；③把 §16.2 結案格計數改成腳本可數（〈一-2-a〉的小腳本），避免快照數字與表內現況漂移 | 部分 |

### 一-2 問 2（完成實作 PRD 所有功能；逐功能 E to E 全功能驗證）

| 子項 | 前六次宣稱 | 本鏡驗到（座標） | 判定 |
|---|---|---|---|
| 2a 實作所有功能 | 依 §16.1 早就做完（101 列各落四格）；第六次結論三句：「✅30、依設計不做 33、等症狀 30、只欠驗收紀錄 8」 | 〔本鏡親跑〕解析 PRD §16.2 結案格欄：本列後現況＝✅31／➖33／⏸29／📎8（見〈一-2-a〉）。字面「所有功能」：未實作的是 29 列（等症狀）；8 列機制已在、只欠驗收紀錄（PRD §16.3 (c) 把它們計入落地）；33 列依設計不做 | 部分（§16.1 定義內完備；字面未做） |
| 2b 逐功能 E to E 驗證 | 第六次結論三句沒有回答這半句；主檔〈六-3〉有誠實限定句：§16.1 對 ✅ 的定義是「機制在、有測試或鎖」而不是「真機走通」 | 〔本鏡〕不存在逐機制 E2E 台帳；本鏡補〈一-2-g〉：真機整段 E2E 只有喚醒鏈尾段（mac）與單次真機觀測（`--pace`、清倉三連、`--env-doctor`）；其餘 ✅ 列只有單元／契約／鎖測試；R212 範圍內 Windows 真機樣本 0 筆 | 未做（逐項 E2E 不成立；已覆蓋面與缺口現已逐列可查） |
| 2c 本列新增的 A4 清倉 | PRD v2.1.19 與 A4 落款：BD-1～BD-9＋BD-2′ 落地，親驗 `--pace` cap 由 1 升至 `cap_converge` | 見〈一-5〉：機制完備；「親驗」一句過樂觀（標題 cap＝2、現在可派＝2、效果只在被點名軸 <85% 時存在），列入〈三〉P3-1／P3-2 | 部分 |

#### 一-2-a §16.2 結案格現況與快照

| 項 | 值 | 座標 |
|---|---|---|
| §16.2 結案格欄計數（72 列） | ✅2／➖33／⏸29／📎8；加矩陣原判 ✅29 列＝全母體 ✅31／➖33／⏸29／📎8（合計 101） | 〔本鏡親跑〕小腳本解析 PRD 第 2604～2790 行（見〈五〉第 12 項） |
| §16.3 (b) 凍結快照 | ✅29／➖33／⏸31／📎8；差 2 格＝§12 權限旗標（Run4 轉）與施工圖 A4（本列轉）各自 ⏸→✅；PRD 明文快照不重算（修訂表 v2.1.18／v2.1.19） | 〔讀檔〕PRD §16.3、修訂表 |
| §16.3 交叉表 | 「⚠️→✅」「❌→✅」兩格仍寫 0，現況各為 1 | 同上 |
| 判定 | 不是錯（快照語意），但快照與現況已有兩格差，讀者只能手數 | 見〈六-E7〉 |

#### 一-2-b 機械核對結果

| 檢查 | 方法 | 結果 |
|---|---|---|
| 引用路徑 | 解析 §16.2＋§16.6 全部反引號路徑（tools／AutoClaude／.claude／docs／ONBOARDING.md／env.shared） | 76 處；75 處存在；缺的 `AutoClaude/.env` 是 gitignored 本機檔（§16.6 載入鏈名詞，不是引用） |
| 符號 | 90 個 snake／Camel 反引號詞，對 tools、AutoClaude/autoclaude、AutoClaude/tests、AutoClaude/scripts、.claude 做字面 grep | 64 命中；26 零命中：22 個是該列自陳零命中的鍵／狀態字（如 `AUTH_MODE`、`MAX_STEP_TURNS`、`NEEDS_HUMAN`），2 個是點號形式（`ExecutorConfig.permission_mode`、`boot_self_check.cli_version_verdict`，成員存在），1 個是 PRD 公式變數（`V_safe`），1 個是 A4 列保留的舊「零命中」敘述（`burn_down`，見〈六-E5〉）；沒有「列宣稱存在而實際零命中」 |
| DEF-ID | 抽出 §16 內 9 個 DEF-ID（020／146／198／204／234／242／246／458／508，全為 `DEF-200-NNN` 形式） | 全在帳本（主檔或 archive）；狀態與列內引用一致（closed-by-decision／fixed） |
| ADR／docs | ADR-XPLAT-007 與 7 份 docs 路徑 | 全存在；§12 列引的 `SddBridge_RealRun_Evidence_20261011.md` 第 13／80～84／391 行〔本鏡親讀〕逐字屬實 |
| ⏸ 29 列 | 每列含「再開症狀＝」且症狀句不含輪號／日期／待排程字樣 | 29／29 通過；§4.5.1 與施工圖 A7 兩列以「有 sid＋seq 的…實錄」表述，仍屬可觀測 |
| ➖ 33 列 | 每列含「依據」與座標（DEF-ID／ADR／修訂表／矩陣／§） | 33／33 通過 |
| 📎 8 列 | 每列含「殘留」 | 8／8 通過（§15.5 與 §11.2 兩列的「殘留」文字與 📎 定義有落差，見〈三〉P3-9） |
| 逐列結果 | 〈一-2-h〉附表 72 列 | 0 列失敗 |

#### 一-2-c ✅ 列抽樣核對（29 個矩陣原判 ✅ 的 ID 全數做符號／檔案存在檢查，其中 §8-6、§8-8、§8-14 三列在矩陣即寫「同 §4.1.5／§4.5.9／§6.2-3」；46 項存在性斷言 0 失敗；下列模組本鏡實跑）

| 矩陣 ID | 機制（HEAD 現查） | 測試／鎖（本鏡實跑） | rc |
|---|---|---|---|
| §4.1.1-T5、§4.1.3、§4.1.4、§4.1.5、§8-1b、§8-6 | `quota_meter.USAGE_URL`／`access_token`、`quota_gate.QUOTA_CACHE_TTL_SECONDS`／`core_signature`、`quota_pace._ROLLOVER_EPS`／`segments`、`degraded_cap`、`http-429-unmeasured` | `test_quota_policy`（339 項） | 0 |
| §4.2.3a、§4.2.4、§4.2.8、A1、A2、A8 | `_in_cap_gate`／`FALLBACK_KINDS`、`gate_excluded`、`quota_availability.evaluate`／`quota_stability`、`pace_index`／`lead_pp`、`row_of`、`_rec_of_gate` | 同上 | 0 |
| §4.5.5、§11.4 | `register_endurance`、`endurance_schtasks_script`、`schedule_backend` 的 Schtasks／Launchd | `test_mac_endurance_r83`（133 項） | 0 |
| §4.5.6、A5a | `unhandled_limit_event`、`quota_escalation` | `test_sentinel_tick_e2e_r145`（12 項）、`test_wake_chain_halt_r278`（58 項） | 0 |
| §4.5.7、§4.5.8（併 A5b） | `quota_escalation`、`sentinel_lifecycle.armed_but_missing` | `test_context_budget_guard` 的 `ControllerIdlePrepareWatchTest`／`ArmedDriftSelfHealTest`／`OrphanModeWatchTest`（20 項） | 0 |
| §4.5.9、§8-8 | `dirty_worktree_rescue` | `AutoClaude/tests/test_r100_dirty_worktree_rescue.py`（33 項） | 0 |
| §6.2-3、§8-14、A9 | `boot_self_check`（磁碟空間、環境鍵前綴） | `AutoClaude/tests/test_r100_boot_self_check.py`（58 項） | 0 |
| §8-4 | `file_state_repository`（checksum／版本保留） | `AutoClaude/tests/test_r100_power_loss_protection.py`（16 項） | 0 |
| §12-憑證、§12-命令執行、§13-禁令 | `access_token`（不落痕跡）、`resume_route`（argv 由參數組裝）、`FANOUT_WINDOW_SECONDS`（一帳一帳本） | §13 為設計；派發帳併發另有 `FanoutLedgerConcurrencyTest`（5 項） | 0 |
| A6、§8-10 | `resume_route.preflight_problem`、`relay_machine`、`.claude/settings.unattended.json`、FRESH 降級 | 符號存在；測試住 `test_context_budget_guard`（巨型模組，本鏡只抽跑上列 25 項） | — |
| §12 權限旗標（Run4 轉 ✅） | `boot_self_check.permission_bypass_verdict`（不變式 8） | `AutoClaude/tests/execution/test_prd12_permission_bypass_invariant8.py`（86 項） | 0 |
| 施工圖 A4（本列轉 ✅） | `tools/lib/quota_burndown.py` 等 | `tools/tests/test_quota_burndown.py`（14 項） | 0 |

#### 一-2-d 📎 八列：殘留是否仍成立、Mac 現在能否零／低成本補件、確切指令

| 列 | 殘留仍成立？ | 可補嗎（Mac） | 判定 |
|---|---|---|---|
| §6.2 R-6.2-2 CLI 版本相容＋DRY_RUN | 部分：patch 升版已由家族判定治好（本鏡現查 `family_verdict('2.1.296')`＝`('family','2.1.295')`，rc=0）；新 minor／major 仍需補清單 | 零成本；現況不需補件 | 殘留成立（範圍已縮） |
| §8 列 13 CLI 版本升級 | 同上 | 同上 | 同上 |
| §11.1 零 Token 遙測 6h | 成立（docs 無 6 小時純遙測紀錄）。Run4〈六〉#53 已說明既有四段 ≥6 小時靜止窗只證「哨兵巡邏零 token」、遙測當時沒被輪詢，所以不算 | 可補：token 成本 0、牆鐘 6 小時、需窗內帳號無其他用量；`quota_meter.py --watch SECONDS` 是現成的輪詢入口（每 N 秒一次唯讀 GET 並印一行） | 殘留成立；可補 |
| §11.2 離線模擬器＋性質測試 | 成立；且列內自陳 (b)「離線模擬器是交付物、不是驗收資料」，與 📎 定義（機制已 ✅、只欠驗收資料）字面不符 | 不可低成本補：H1 母體（37 符號／19 翻動）已蒸發，PRD 禁合成頂替；模擬器是交付物 | 殘留成立；格的字面有落差（〈三〉P3-9） |
| §11.3 凍結與喚醒 | 部分成立：寫入步的計時斷言其實已有（`AutoClaude/tests/integration/test_sigint_checkpoint.py` 的 ≤2 秒 SLA，量真實 `FileStateRepository` 三段落盤，於 signal handler 內執行）；缺的是「注入 95% → 整段凍結 ≤5 秒」；`pct_before`／`pct_after`（v1 恆 null）屬守衛面，須先附暴露證據 | 計時斷言可補：零 token、約 30 行測試；`pct_*` 不屬低成本 | 殘留成立但寫得略悲觀（低估既有 2 秒 SLA 測試） |
| §11.7 多實例配額 | 成立：既有 `FanoutLedgerConcurrencyTest`（5 項通過）用多行程壁鐘 barrier 驗帳本併發，但沒有「兩個專案」的變體；派發帳是機器級（`fanout_ledger_path()`＝`tempfile.gettempdir()` 下的檔，`quota_gate.py` 第 295 行），專案維度不影響帳本 | 帳本層可補：零 token、約 20 行；「`U5h` 燃燒率 ≤ `V_safe`×1.2」要真燒用量，有 token 成本 | 殘留成立；可補一半 |
| §11.8 24h 端到端 | 成立（需 24 小時、至少 4 次 5 小時視窗、真實 token） | 不可低成本補：Run4 單次約 40 分鐘、約 $0.03，只累積「單次 reset 事件」，不等於連續 24 小時 | 殘留成立 |
| §15.5 紅線 1～12 | 該列「殘留」欄其實是狀態清單（各紅線有機械物），唯一資料殘留＝紅線 11 的版本清單（同 §6.2 R-6.2-2，範圍已縮） | 同第一列，零成本 | 殘留近乎空；文字應改寫（〈三〉P3-9） |

確切指令（皆已在本機確認指令形態可跑；只讀或零 token；`$SCRATCH` 請換成 scratchpad 絕對路徑）：

```bash
# §6.2／§8 列 13：現查當前 CLI 版本的家族判定（本鏡 rc=0，輸出 ('family', '2.1.295')）
cd AutoClaude && python -c "from autoclaude.utils.verified_cli_versions import family_verdict; print(family_verdict('2.1.296'))"

# §11.1：6 小時純遙測（零 token）。窗前基準；之後 run_in_background 跑 --watch 300（21600 秒後停止）
python tools/lib/quota_meter.py --from-cache --json > "$SCRATCH/e11_1_before.json"
python tools/lib/quota_meter.py --watch 300 > "$SCRATCH/e11_1_watch.log" 2>&1
# 判準：窗內 find ~/.claude/projects -name '*.jsonl' -newermt "<窗起>" ! -newermt "<窗迄>" 應無輸出；
# 窗前後各人工讀一次 Claude Code /usage 當「獨立權威讀數」（PRD §11.1 字面）；--watch 的逐行輸出就是「確實在輪詢」的證據

# §11.3：現況 12 項通過；補件＝在 tests/core/test_kernel_token_halt.py 加一支 FileStateRepository＋計時器的 TOKEN_HALT 測試（斷言 <5 秒）
cd AutoClaude && python -m pytest tests/core/test_kernel_token_halt.py tests/integration/test_sigint_checkpoint.py -q -n 0 -p no:cacheprovider

# §11.7：現況 5 項通過；補件＝同檔 _barrier_run 再開兩個 CLAUDE_PROJECT_DIR 不同的行程對同一帳本跑 gate job，斷言放行總數 ≤ cap
cd tools/tests && AUTOSDD_SENTINEL_OFF=1 python -B -m unittest test_context_budget_guard.FanoutLedgerConcurrencyTest
```

#### 一-2-e ⏸ 29 列與 T4 對照

- 症狀句可觀測性：29／29 通過（〈一-2-b〉）。沒有一列把症狀寫成日期、輪號或「待排程」。
- 觀察者缺口（誠實劃界，不是缺陷）：§3.2、§13、§9 告警、§12 日誌遮蔽等列的症狀只有掌舵者回報或某視窗撞見才會被看到；§16.5 已明文「⏸ 沒有掃描器」，本鏡不改判。
- T4 對照：Run4〈四〉記命中 1（§12 權限旗標，已轉 ✅）。本列新命中 1（施工圖 A4，已轉 ✅）。F-SBR-001 C4 對 §8 列 9／§9 告警：DEF-200-518（本鏡讀帳本第 291 行）的「分流去向」寫「C4 實跑命中」，而 Run4〈四〉與 PRD 兩列都不轉格（理由＝NEEDS_HUMAN／告警機制未落地）；該兩列症狀句字面是「桌面通知與 ESCALATION 皆未觸發」，C4 的事實是 ESCALATION 觸發了、善後（dump／通知）缺失——字面不符。帳本措辭（命中）與 PRD 結案帳（⏸）不一致，§16.5 對「命中但不轉格」沒有規則，登〈四〉P4-12。

#### 一-2-f §16.6 兩列依據

| 列 | 依據是否成立 | 本鏡驗到 |
|---|---|---|
| 2026-10-10 CLI 家族級判定 ✅ | 成立 | `verified_cli_versions.family_verdict`（第 81 行）存在，`boot_self_check.py` 第 24／194 行消費它；`test_r100_boot_self_check.py`（58 項）rc=0；`family_verdict('2.1.296')` 與 `('2.2.0')` 本鏡實跑分別回 `('family','2.1.295')`／`('unknown', None)`，與列內「新 minor 仍 DRY_RUN」一致 |
| 2026-10-11 env.shared 參數檔分層與自動同步 ✅ | 成立（Windows 部分列內已自陳未驗） | `env.shared`（4 鍵）、`quota_env_layers.py`、`tools/git-hooks/post-merge`（git 索引模式 100755）存在；`.claude/hooks/block_destructive_git.py` 第 1446 行 `_GOV_EXACT` 含 `.env`、`env.shared`、`tools/lib/quota_env_layers.py`；`TestPostMergeHook` 七支；`test_quota_env_layers`（38 項）rc=0；`--env-doctor` rc=0 |

#### 一-2-g 逐機制 E2E 分級（Q2 後半句「逐功能 E to E」的回答）

分級：A＝真機整段 E2E（真排程器／真 claude／真 hook，有逐字痕跡）；B＝真機單次觀測（真資料餵真碼，不是驗收腳本）；C＝只有單元／契約／鎖測試；D＝零（未實作、依設計不做、只欠驗收）。所有列的 Windows 面：R212 範圍內 0 筆樣本。

| 機制群（§16.2 ✅ 列） | 分級 | 證據座標 | 缺口 |
|---|---|---|---|
| 額度遙測取數＋TTL＋429 處理（§4.1.1-T5、§8-1b、§12-憑證） | B＋C | 骨架〈二-1〉〈三-3〉的 `--pace` 逐字（`來源=cache 量測於=…`）；Run4〈二〉事件 `probed … source=endpoint`；`test_quota_policy` 339 項 | §11.1（6 小時零 token 驗證）＝📎 |
| 視窗翻頁、方案指紋、遙測失效收斂（§4.1.3／§4.1.4／§4.1.5／§8-6） | §4.1.4 為 B（落款 `core_signature` 比對 ✓，〈三-3〉）；其餘 C | 同上；DEF-200-242 的「本機落款 50 次翻頁」是重放資料，不是 E2E | 無整段 E2E |
| 閘門優先序、平穩性、pace_index（§4.2.3a／§4.2.4／§4.2.8、A1／A2／A8） | B＋C | `--pace` 逐字含 `gate_excluded=spend,missing`、`⏳ 目前 cap=2 由遲滯維持`、`pace_index=0.60` | 離線模擬器、H1 fixture、DRY_RUN 一週＝§11.2 📎 |
| 撞線喚醒閉環、長休眠交棒、續跑視窗、哨兵自癒（§4.5.5／§4.5.6／§4.5.8／§11.4、A5a／A6／§8-10） | A（僅 mac） | 主檔〈十一〉三次（2026-10-11）、Run4〈二〉跑法④ 22 項判決、2026-10-10 真撞線事故（主檔〈二-0〉）；C：四組測試合計 223 項本鏡實跑 rc=0 | 真 429 寫標記端、`RELAY_NEXT`／`quota_stop`／`relay_exhausted`、FRESH／PATROL、24 小時多次 reset、睡眠喚醒（Run4〈三〉末段） |
| 主控閒置盲區（§4.5.7） | B＋C | Run4〈六〉#53 四段 ≥6 小時靜止窗（他包回報＋QA 重掃）；`ControllerIdlePrepareWatchTest` | 無 |
| 髒污工作樹救援（§4.5.9、§8-8） | C | 33 項 | 本鏡在 R212 三份證據檔與矩陣備註找不到真機樣本 |
| 磁碟、斷電 checksum、開機自檢（§6.2-3／§8-4／§8-14／A9） | C（開機自檢另有 B） | 58＋16 項；F-SBR-001 r5 真跑 log 內「開機自檢」前綴行 3 行（Run4〈四〉，證據在 scratchpad 不入庫） | 斷電真機演練無 |
| 引擎權限旗標不變式 8（§12，Run4 轉 ✅） | C＋B（n=1） | 86 項；F-SBR-001 r5 真跑 3／3 步成功（haiku、僅 mac；證據不入庫） | VM 不偵測；`--settings`／使用者層 `defaultMode` 不在射程（列內自陳） |
| 清倉模式（A4，本列轉 ✅） | B＋C | `--issue`→`--pace`→`--status` 逐字（〈三-3〉）；本鏡 `--status` 現查 rc=0；落款後本視窗 Agent 派工 4 次全放行（〔逐字稿第 731／733／781／788 行〕；其中第 3、4 次是主控等 330 秒遲滯後才派，hook 的拒絕分支沒被觸發）；14 項 | 過期自動回復與 `--revoke` 沒有真機樣本（效期到 2026-10-17） |
| 命令執行、禁令（§12-命令執行、§13-禁令） | C／設計 | argv 由參數組裝；一帳一帳本；`FanoutLedgerConcurrencyTest` 5 項 | E2E 不適用 |
| CLI 版本家族判定（§16.6 第 1 列） | B＋C | `claude --version`＝2.1.296 → `('family','2.1.295')`（本鏡）；58 項 | 新 minor／major 未發生 |
| 額度／模型參數檔與自動同步（§16.6 第 2 列、問 3） | mac 為 B＋C；Windows 為 D（R212 範圍內 0 筆） | `--env-doctor` rc=0（本鏡）；`.env.example` 與生成值相同；hook 以暫存 repo 真 `git pull` 驗（主檔〈二-11〉，Developer 包，git 2.54）；38 項 | Windows 首次 `git pull`、`core.hooksPath`、cp950 顯示（主檔〈八-4〉第 6 項） |
| ⏸ 29／➖ 33／📎 8 | D | §16.2 | 依設計不做、等症狀或只欠驗收 |

結論：「每個功能都已 E to E 驗證」不成立；成立的是「喚醒鏈尾段在 Mac 真機整段走過，其餘機制有單元／鎖，部分有單次真機觀測」。前六次的誠實限定句（主檔〈六-3〉）與此一致，但沒有被寫進對掌舵者的結論三句。

#### 一-2-h 附表：§16.2 72 列逐列機械核對

欄位：路徑＝存在數／引用數（「—」＝該列無路徑引用）；符號＝零命中的反引號詞（皆屬該列自陳零命中、點號形式或 PRD 變數，見〈一-2-b〉）；依據／再開症狀＝⏸ 列看症狀句、➖ 列看依據座標、📎 列看殘留、✅ 列看 2026-10-12 落款。

| # | PRD 座標（截 22 字） | 結案格 | 路徑 | 符號（零命中者） | 依據／再開症狀 |
|---|---|---|---|---|---|
| 1 | §3.1 架構圖：單一 Daemon＋7 模 | ➖ | 3/3 | — | 依據✓ |
| 2 | §3.2 10 態 FSM＋單向鎖存＋轉移圖 | ⏸ | 2/2 | HALTED_MANUAL | 症狀✓ |
| 3 | §4.1.1 T1（OTel 本機遙測） | ⏸ | 3/3 | CLAUDE_CODE_ENABLE_TELEMETRY | 症狀✓ |
| 4 | §4.1.1 T2（逐字稿本機加總） | ⏸ | 2/2 | — | 症狀✓ |
| 5 | §4.1.1 T3（statusLine 回 | ⏸ | 3/3 | — | 症狀✓ |
| 6 | §4.1.1 T4（/usage 程式化解析 | ➖ | — | — | 依據✓ |
| 7 | §4.1.1 引擎獨立執行（無 Claude | ⏸ | 2/2 | — | 症狀✓ |
| 8 | §4.1.1 本機推估安全邊際 15pp | ➖ | — | — | 依據✓ |
| 9 | §4.1.2 新鮮度三段式（180／600／ | ➖ | — | — | 依據✓ |
| 10 | §4.2.1 EWMA 燃燒率 | ➖ | — | — | 依據✓ |
| 11 | §4.2.2 安全燃燒率／目標併發公式 | ➖ | — | — | 依據✓ |
| 12 | §4.2.3 致動器表：併發／模型降級／任務 | ⏸ | 1/1 | — | 症狀✓ |
| 13 | §4.2.5 BURSTING 六條件 | ➖ | — | — | 依據✓ |
| 14 | §4.2.6 參考實作（dataclass  | ➖ | — | — | 依據✓ |
| 15 | §4.2.7 情境試算表 | ➖ | 1/1 | — | 依據✓ |
| 16 | §4.3 上下文壓縮策略（三 AND） | ⏸ | 1/1 | COMPACT_MIN_INTERVAL_SECONDS | 症狀✓ |
| 17 | §4.4.1 Worktree 建立 | ➖ | — | — | 依據✓ |
| 18 | §4.4.2 序列化整合佇列（rebase→ | ➖ | 1/1 | — | 依據✓ |
| 19 | §4.4.3 Agent 硬性預算（turn | ⏸ | — | MAX_STEP_TURNS、MAX_STEP_QUOTA_PP、DRAIN_BUDGET_FACTOR | 症狀✓ |
| 20 | §4.5.1 凍結流程 7 步 | ⏸ | — | — | 症狀✓ |
| 21 | §4.5.2 分片休眠＋時鐘跳躍偵測 | ⏸ | 1/1 | — | 症狀✓ |
| 22 | §4.5.3 重置驗證與喚醒（RESET_C | ➖ | 1/1 | RESET_CONFIRM_PERCENT | 依據✓ |
| 23 | §4.5.4 喚醒策略 AUTO／RESUM | ⏸ | — | weekly_warn | 症狀✓ |
| 24 | §4.5.10 醒來確認額度 E1～E5 | ⏸ | — | — | 症狀✓ |
| 25 | §4.6 跨平台防休眠 | ➖ | 1/1 | — | 依據✓ |
| 26 | §4.7 帳號配額仲裁 | ➖ | 2/2 | daemon_id | 依據✓ |
| 27 | §5 API_KEY 模式 | ➖ | — | AUTH_MODE、API_AUTO_CONTINUE | 依據✓ |
| 28 | §6 區塊 1～4b：帳號／遙測／水位／週額 | ➖ | 1/1 | — | 依據✓ |
| 29 | §6 區塊 5～9：上下文／併發／突刺／硬預 | ➖ | — | RESET_CONFIRM_PERCENT、COMPACT_MIN_INTERVAL_SECONDS、CLOCK_JUMP_TOLERANCE_SECONDS、MAX_INPROCESS_WAIT_SECONDS | 依據✓ |
| 30 | §6 區塊 10～15：防休眠／Git／狀態 | ➖ | — | METRICS_EXPORT、ALERT_WEBHOOK_URL | 依據✓ |
| 31 | §6.1 啟動自檢不變式 1～13 | ⏸ | 2/2 | — | 症狀✓ |
| 32 | §6.2 R-6.2-1 殘留整合佇列：開機 | ➖ | — | — | 依據✓ |
| 33 | §6.2 R-6.2-2 CLI 版本相容＋ | 📎 | 1/1 | — | 殘留✓ |
| 34 | §7 state.json schema v | ➖ | — | quota_snapshot | 依據✓ |
| 35 | §8 列 1 非預期 429（推論端） | ⏸ | 2/2 | — | 症狀✓ |
| 36 | §8 列 2 重置時間漂移 | ⏸ | — | — | 症狀✓ |
| 37 | §8 列 3 git index.lock  | ⏸ | — | — | 症狀✓ |
| 38 | §8 列 5 等待中睡著 | ➖ | 2/2 | — | 依據✓ |
| 39 | §8 列 7 同帳號多 Daemon 超燒 | ➖ | — | — | 依據✓ |
| 40 | §8 列 9 Agent 卡死／NEEDS_ | ⏸ | 2/2 | NEEDS_HUMAN | 症狀✓ |
| 41 | §8 列 11 整合驗證失敗 | ➖ | — | — | 依據✓ |
| 42 | §8 列 12 Prompt injecti | ⏸ | 2/2 | — | 症狀✓ |
| 43 | §8 列 13 CLI 版本升級 | 📎 | — | — | 殘留✓ |
| 44 | §9 12 個 Prometheus 指標 | ⏸ | — | — | 症狀✓ |
| 45 | §9 結構化決策日誌 | ⏸ | 2/2 | — | 症狀✓ |
| 46 | §9 告警（DRAINING 以上／DIRT | ⏸ | — | NEEDS_HUMAN | 症狀✓ |
| 47 | §12 權限旗標（不預設 skip-perm | ✅ | 4/4 | ExecutorConfig.permission_mode | 落款✓ |
| 48 | §12 寫入範圍／治理檔禁寫 | ⏸ | 3/3 | — | 症狀✓ |
| 49 | §12 prompt injection／狀 | ⏸ | — | — | 症狀✓ |
| 50 | §12 日誌遮蔽 | ⏸ | 2/2 | REDACT_SECRETS_IN_LOGS | 症狀✓ |
| 51 | §12 供應鏈（不得無人確認新增依賴／pos | ⏸ | 1/1 | — | 症狀✓ |
| 52 | §13 使用條款人工檢核 | ⏸ | — | — | 症狀✓ |
| 53 | §15.4 P0 觀測 | ➖ | — | autoclaude_step_quota_cost_pp | 依據✓ |
| 54 | §15.4 P1 保全 | ➖ | — | — | 依據✓ |
| 55 | §15.4 P2 配速 | ➖ | — | — | 依據✓ |
| 56 | §15.4 P3 閘門 | ➖ | — | CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS | 依據✓ |
| 57 | §15.4 P4 韌性 | ⏸ | 3/3 | OVERAGE_ALERT_ON_FIRST_USE | 症狀✓ |
| 58 | §15.4 P5 硬化 | ➖ | — | — | 依據✓ |
| 59 | §10 v1→v2 設定遷移 | ➖ | — | — | 依據✓ |
| 60 | §11.1 零 Token 遙測 6h 驗證 | 📎 | — | — | 殘留✓ |
| 61 | §11.2 離線模擬器＋性質測試 | 📎 | — | — | 殘留✓ |
| 62 | §11.3 凍結與喚醒（5s／kill -9 | 📎 | 2/2 | — | 殘留✓ |
| 63 | §11.5 防休眠驗收 | ➖ | — | — | 依據✓ |
| 64 | §11.6 多 Agent 隔離與整合 | ➖ | — | — | 依據✓ |
| 65 | §11.7 多實例配額 | 📎 | 1/1 | V_safe | 殘留✓ |
| 66 | §11.8 24h 端到端 | 📎 | 1/1 | — | 殘留✓ |
| 67 | §15.5 紅線 1～12 | 📎 | — | — | 殘留✓ |
| 68 | 施工圖 A3：R108 配速批 W4／W6（ | ➖ | — | — | 依據✓ |
| 69 | 施工圖 A4：R108 BurnDown 增 | ✅ | 5/5 | burn_down | 落款✓ |
| 70 | 施工圖 A5b：R112 REQ-W2 無主 | ➖ | — | — | 依據✓ |
| 71 | 施工圖 A5c：R112 REQ-W6 喚醒 | ⏸ | — | — | 症狀✓ |
| 72 | 施工圖 A7：R121 無人續跑受控 com | ⏸ | 2/2 | AUTOSDD_UNATTENDED_PUSH_OFF | 症狀✓ |

### 一-3 問 3（兩邊 .env 同步、哪邊正確、如何維護、自動同步、Windows、驗證）

| 子項 | 前六次宣稱 | 本鏡驗到（座標） | 判定 |
|---|---|---|---|
| 3a 哪邊才正確完整 | 兩邊 `.env` 都不是標準；標準＝repo 的 `env.shared`＋出廠值（`ENV_SPEC`）；`.env.example` 是生成物 | 〔本鏡親跑〕`python tools/lib/quota_policy.py --env-doctor` rc=0：印「載入鏈（高→低）：行程 env > AutoClaude/.env > .env > env.shared > 出廠」，本機 `env.shared` 存在 4 鍵、`.env` 存在 4 鍵、`AutoClaude/.env` 不存在；`--print-env-example` 與 `.env.example` 逐位元組相同（`diff` rc=0，本列新增的 `AUTOSDD_QUOTA_BURNDOWN_OFF` 兩行已在內）；ONBOARDING §2.2（第 103～130 行）同義 | 完備 |
| 3b 參數檔如何維護 | 改 `env.shared`＋commit＋push；`.env` 只放本機例外（行尾 `# override-ok: <WHY>`）；`--env-doctor [--fix]` | 〔讀檔〕`env.shared` 檔頭維護規則（每鍵上方一行 WHY、機密不得入檔）；ONBOARDING §2.2 的四檔表；`--env-doctor` 輸出逐鍵標〔來源〕 | 完備 |
| 3c 自動同步機制 | git `post-merge` hook：pull／merge 成功後自動體檢；問題全是可自動修的旗標才 `--fix`（先備份）；永遠 exit 0 | 〔本鏡親跑〕`git ls-files -s tools/git-hooks/post-merge`＝100755；`git config core.hooksPath` 指向本 clone 的 `tools/git-hooks`；`TestPostMergeHook` 七支（四支行為鎖＋三支靜態鎖）；`test_quota_env_layers` 38 項 rc=0 | 完備（Mac） |
| 3d 「下次在 Windows 執行時自動同步」 | 機制已交付；Windows 驗收一行（`RESULT: PASS`）；Windows 真機未驗 | 〔讀檔〕主檔〈八-4〉第 1～6 項與 Run4〈五〉：Windows 面 R212 範圍內 0 筆真機樣本；CI 的間接證據被如實標「推論，未見逐測試通過列」；在本鏡讀過的主檔〈二-11〉〈八〉與 Run4〈五〉內，推論皆標〔推論〕，沒有被寫成已驗 | 部分（機制已交付；「是否 OK」只能由該機驗） |
| 3e 「請進行驗證功能是否 OK」 | 第六次結論三句：「Mac 這邊全部驗過」 | 〔讀檔〕主檔〈二-11〉：hook 控制流以暫存 repo 的真 `git pull` 加替身 python 驗，並明寫「絕不對真 repo 根跑 `--fix`」；本鏡 Mac 側驗到 `--env-doctor` rc=0、`.env.example` 生成值相符、38 項、七支 hook 鎖。「全部」略寬：對真 repo 根的 `--fix` 與真 `pick_repo_python` 解析（鎖內是替身）沒有走過 | 部分（措辭過寬，〈六-F4〉） |

### 一-4 問 4（要不要馬上切 Windows）

| 子項 | 前六次宣稱 | 本鏡驗到（座標） | 判定 |
|---|---|---|---|
| 4a 結論 | 不需要；開發留 Mac；理由＝mac 專屬驗收在 Windows 驗不了、windows-compat-ci 綠、晚切代價小（`--ff-only` 失敗時 loud 且不改樹） | 〔本鏡親跑〕`gh run list --commit 1818de87fbbb5a96673008d50eeb1e619ce22223` 回 6 支 completed success（windows-compat-ci 38230301093、root-infra-ci 38230301052、AutoClaude CI 38230301082、macos-compat-ci 38230301062、arch-fitness 38231604962、drift-daily 38230947003）；`git show --stat 1818de87` 為 29 個檔；理由三點與證據一致 | 完備 |
| 4b 「你只剩在 Windows 貼一行指令，沒有別的事」 | 第六次結論三句 | 〔讀檔〕主檔〈八-4〉列 6 項 Windows 專屬待驗；Run4〈五〉自己寫「含三件（估 1～2 小時）」（啟動提示詞、表② 回填、驗收一行）。「只剩一行」低估 | 部分（結論成立；措辭過樂觀，〈六-F1〉） |
| 4c 本列新增的 Windows 驗證面 | Dev 報告只列「Windows 實機」未做 | 〔讀檔〕`quota_gate.py` 第 98 行無 try 直接 import `quota_burndown`；其 CLI 於 cp950 的中文輸出屬 DEF-200-525 同型風險面（`__main__` 已呼叫 `init_utf8_streams()`）。建議把 `& .\.venv\Scripts\python.exe tools/lib/quota_burndown.py --status` 加進 Windows 驗收（預期 rc=1、首行「清倉授權：沒有有效落款」、中文不亂碼），一行同時驗載入與編碼 | 建議（〈六-E6〉） |

### 一-5 新增指令與清倉模式（DEF-200-528）的需求追溯

#### 一-5-a 掌舵者兩則新增指令與骨架〈二-1〉的時序

- 〔逐字稿第 173／210 行〕兩則逐字：「這次請儘量使用，我還有一次Token reset的用量」（10:19:26Z＝18:19:26 +08:00）、「我還有一次週Token reset用量，所以儘量使用！」（10:20:32Z＝18:20:32 +08:00）。骨架〈一〉逐字引用屬實。
- 〔逐字稿第 36／37 行〕骨架〈二-1〉引為暴露證據的 `--pace` 逐字畫面，是本視窗第二個工具呼叫（第一個是 `--check`），時戳 10:16:49Z＝18:16:49 +08:00，**早於兩則指令 2 分 37 秒與 3 分 43 秒**。指令之後、落款之前（11:34:11Z＝19:34:11 +08:00）逐字稿沒有任何 `--pace` 呼叫（落款後首次是第 694 行，11:34:21Z）。所以〈二-1〉「指令在、cap=1 在、sid 在 ⇒ 命中」成立的是「同窗、同狀態」，不是「指令之後 `--pace` 仍壓 cap≤2」的字面時序；下令前後的對照也不是同一組讀數（18:16 週 75%／短窗 8%，落款後 19:34 週 78%／短窗 29%）。判級 P3（〈三〉P3-3）：暴露本身真實（真實互動窗、掌舵者自己的指令與 sid），不影響守衛面准入，但文字要如實寫。

#### 一-5-b 效果實測：同一份讀數、有無授權（〔本鏡親跑〕唯讀）

| 情境 | 無授權（cap, 現在可派, band, binding） | 有授權 | 座標 |
|---|---|---|---|
| 本機真實快取，量測於 2026-10-12T20:16:29+08:00（週 83%、短窗 55%；同一份讀數、同一 ratio、同一政策；落款 45c49b8e35 生效中） | (2, 1, converge, seven_day) | (4, 2, converge, seven_day)，effect＝relaxed | scratchpad `sa/probe_real_ab.py` |
| 合成：週軸 70%～84%（converge 帶；短窗 20% 或 55%；出廠政策、r=5.0） | (1, 1, prepare, five_hour) | (4, 2, converge, seven_day) | `sa/probe_effect_band.py` |
| 合成：週軸 60%、短窗 20% | (4, 2, notice, seven_day) | (8, 4, notice, seven_day) | 同上 |
| 合成：週軸 ≥86%（prepare 帶） | (1, 1, prepare, seven_day) | **(2, 1, prepare, seven_day)** | 同上 |

判讀：
1. 授權讓「現在可派」多 1（1→2）只發生在被點名軸低於 prepare 錨點（出廠 85%）的區間；被點名軸進 prepare 帶後，授權只把該軸 cap 由 1 放到 2，「現在可派」維持 1。這與附錄 §4.4 值域表（prepare 列 (1,1)→(2,1)）、QB1（夾層 `cap_notice`、「保留一層」）和附錄 §4.3 理由 1（「要的是把額度用完，不是拆掉煞車」）一致，是已裁決的設計結果，不是缺陷。
2. 本機週軸：75%（18:16）→78%（19:34）→83%（20:16）。照此速度很快越過 85%；越過之後 `--pace` 會同時顯示「🔥清倉模式生效中」與「現在可派 1」——形狀與 A4 再開症狀（「掌舵者下清倉指令而 `--pace` 仍把派工壓在 cap≤2」）相同。A4 落款、骨架〈三-3〉、對掌舵者的說明都沒有寫「效果帶」（〈三〉P3-1）。
3. 落款後標題 cap 先 2（遲滯維持，軸值 4），每 ≥300 秒 +1 到 4（Dev 報告 §0-4；骨架〈三-3〉有逐字）；「現在可派」上限＝min(rec, cap−live)，rec 在 converge×mid 為 `cap_prepare`＝2。本視窗實況〔逐字稿第 731／733／744／778／779 行〕：先派 2 位鏡，主控等 330 秒遲滯後再派 2 位。

#### 一-5-c 需求追溯表（附錄＋QB1～QB6＋BD-2′ → 函式 → 鎖 → 紅面實況）

行號＝本鏡 `grep -n` 現查（`tools/lib/quota_burndown.py` 簡稱 qb；`tools/tests/test_quota_burndown.py` 簡稱 tq）。突變代號見〈一-5-d〉。

| # | 規格條款 | 實作座標 | 鎖（測試名：tq 行） | 紅面實況（隔離副本突變） | 判定 |
|---|---|---|---|---|---|
| 1 | §3.1／QB3 載體三收：落款檔＋CLI 唯一寫入口＋env 只准關 | qb `directive_path` 80、`issue` 247、`revoke` 318、`main` 329；`ENV_SPEC` 的 `AUTOSDD_QUOTA_BURNDOWN_OFF`（`quota_policy_env.py` 162） | `test_issue_status_revoke_roundtrip_and_argument_errors`：255 | 生產呼叫端只有 `quota_gate.py` 的 `active`×2、`log_decision`×1（grep 全 repo）；`issue(` 只被 `main()` 叫 | 完備 |
| 2 | §3.2 六欄＋id＋schema | qb `FIELDS` 65、`read_directive` 85；`issue` 內組 record 274～277 | 同上（`all(rec[k] for k in B.FIELDS)`、readings 長度 4、`until_resets_at`、`core_signature`） | N11（readings 寫空）殺、N12（指紋寫死）殺；**N13／P03（`issued_at` 去掉 offset）存活** | 部分：§3.2 明文要求 aware，無斷言 |
| 3 | §3.2 `until_resets_at` 伺服器原字串 | qb `issue` 275（取 `named.resets_at`） | 同上（`rec["until_resets_at"] == at(7663)`） | — | 完備 |
| 4 | §3.2 落款檔住持久目錄 | qb `directive_path`→`endurance_env.trace_dir()` | `setUp` 以 `AUTOSDD_TRACE_DIR` 隔離；`test_pace_and_the_dispatch_hook_both_carry_the_directive`：273 用預設路徑讀寫同一份 | — | 完備 |
| 5 | §3.3 生效判準六項合取、fail-closed | qb `verdict` 102、`active` 211、`_left` 96 | `test_valid_then_each_conjunct_breaks_it`：217；`test_bd6_bd7_a_turned_over_or_unparseable_window_is_never_armed`：230 | M12 殺（指紋）；M10／M11／M13 各自存活但屬等價（`active()` 另有 kill-switch 早退、被點名軸缺席由 `StopIteration` 被 `except` 吞成 `None`；N05 兩處都拆則殺） | 完備（冗餘防線；`--status` 的 ✗ 字樣未鎖，P4-13） |
| 6 | §4.1／QB6 qualifying：被點名軸＋同窗鄰軸（`resets_at` 字串全等） | qb `Burn.masks` 171（`same`） | `test_neighbours_need_string_equality`：119（差 1 微秒＝不同窗） | M17（放寬成分鐘精度）殺；**N03（`active()` 不把 `named.resets_at` 帶進 `Burn`）存活** | 部分：單元鎖有，生產路徑接線無鎖 |
| 7 | §4.1／§5 合取底線：halt／FALLBACK／MODEL_SCOPED／時鐘 | qb `_eligible` 131 | `test_red_every_floor_conjunct_is_load_bearing`：154；`test_bd3_halt_still_stops`：138；`test_bd4_fallback_kinds_are_never_relaxed_even_when_named`：147 | M04／M05／M06／M07／M29 全殺 | 完備 |
| 8 | §4.2 BD-1：視野乘數地板 1.0、不送加速 | `quota_pace.py` `resolve(floor=)` 407～436（`if lift and horizon == AXIS_FAR: horizon = AXIS_MID`） | `test_naming_the_long_window_relaxes_boundedly_and_leaves_the_floors_alone`：85；`test_naming_the_short_window_gets_only_the_same_window_effect`：110 | M18／M19（地板變加速）殺 | 完備 |
| 9 | BD-2′（Q-cross）：攤提暫停＋供給軸守門 | qb `Burn.masks` 的 `hold` 185；`quota_pace.band_inputs(hold=)` 370～381 | 85（session／five_hour band prepare→free）、110（點名短窗時 `hold` 全空） | M15（拿掉供給軸守門）殺、M28（hold 對所有軸）殺；M16（拿掉被點名軸守門）存活，屬近等價（`named` 與 `total` 實務上互相蘊含） | 完備 |
| 10 | §4.3／QB1 夾層：只准往上、cap=None 不動、不得用 ceil 夾原值 | qb `_merge` 150 | `test_bd2_the_ladder_never_tightens_over_every_cell`：126（4 pct 帶×4 horizon 窮舉＋錨點①）；85 | M01（拿掉上限）殺、M02（用 ceil 夾原值）殺、M03（None 格被夾成有限）殺；**P01／P02（cap 升而逐軸 rec 反降／歸零）存活** | 部分：窮舉以字典序比較（cap 先），附錄 BD-2 要求 cap、rec 兩分量各自單調；逐軸 `recommended` 不進聚合（`_rec_of_gate` 由 band／horizon／cap 重算），所以只影響顯示欄位、不影響派工 |
| 11 | §5① halt 不變 | qb `_eligible`；`quota_policy.decide` 聚合 | 138（含 halt×4 horizon） | M06／M29 殺 | 完備 |
| 12 | §5② FALLBACK 永不（含明文點名） | qb `_eligible`、`verdict` 第 3 步、`issue` 254 | 147；217（`axis_kind: spend`）；`test_refusals_never_leave_a_file`：244 | M04 殺；**M27／P04（`issue()` 不擋 FALLBACK／MODEL_SCOPED）存活**：測試的 `spend`／`weekly_scoped` 兩臂靠「合成快取沒有這兩軸」而 rc=1，拒絕分支本身沒被走到（本鏡以含該兩軸的快取實跑，兩臂皆 rc=1，生產行為正確） | 部分：測試咬合缺口；生產上另有 `verdict` 第 3 步 |
| 13 | §5③ scoped 不納入、note 照印 | qb `_eligible` | 85（該軸 `resets_at` 差 218 微秒，走不到同窗分支）；154（`resets_at` 全等，單元級） | M05 殺；本鏡以同窗全等的 scoped 軸端到端實跑（`active_model` 為 `None` 與 `fable`）：逐格不變、note 保留、理由「model-scoped 不納入」 | 完備（端到端同窗臂只有本鏡探針） |
| 14 | §5④ must-finish 勝出 | `quota_policy.py` 755（`wrap`）、799（`min(rec, cap_prepare) if wrap`） | `test_bd8_must_finish_wins_over_the_relaxation`：168 | M20（拿掉收尾保留段）殺；該測試輸入的放寬是 no-op（free×near，inert）；本鏡另以「放寬有效（週軸 converge×far）＋另一軸 3 分鐘後 reset」實跑：cap 2→4、`recommended_fanout`＝2＝`cap_prepare`、reason 含 `must-finish` | 完備（測試輸入偏弱，行為實測成立） |
| 15 | §6.1／R-4.2.9-4 出聲：原值→放寬值、未放寬軸＋具名理由、過期後消失 | qb `Burn.apply` 187～208；`quota_policy.describe` 821～828；`quota_messages.pace_line` 754～774 | 85（needle：「清倉模式生效中」「落款 bd1」「cap 1→」「cap 2→」「kind=spend（fallback 不納入）」「kind=weekly_scoped（model-scoped 不納入）」）；176；230（過期後無「清倉」） | M14／M24／M25 殺；**N08（拿掉發令時刻、效期終點、效期剩餘、must-finish 門檻）存活**；**N09／N10（未放寬理由文字換掉）存活** | 部分：R-4.2.9-4 ②發令時刻 ③效期終點與附錄 §9-9「效期剩／must-finish 門檻並列」皆已實作但沒被斷言 |
| 16 | §6.2 燃燒落款 `bd` 欄 | `quota_pace.row_of(bd=)` 635；`quota_gate.record_burn(bd=)` 358、`pace_report` 946／959 | 273（ledger 末列 `bd`＝落款 id；無授權的 `row_of` 之 `bd` 為 null） | M22 殺 | 完備 |
| 17 | §6.3 兩計數器（relaxed／inert） | qb `log_decision` 226；`pace_report` 962 | 273（events 末列 `effect=="relaxed"`）；176（`Applied.effect=="inert"`） | M23、N07 殺；events 檔的 inert 列沒有單獨斷言；只有 `--pace` 路徑寫（hook 熱路徑不落檔，Dev 已揭露） | 完備（以 JSONL 為計數器等價物，A4 落款未提） |
| 18 | §7.2 kill-switch（只准關） | `ENV_SPEC` 162；qb `active` 214、`verdict` 第 2 步 | 217；273 末（`--pace` 路徑 `policy_env` 設 OFF 後無「清倉」） | N15 殺；**N04（派工 hook 路徑 `quota_gate()` 的 `env` 改傳 `{}`）存活** | 部分：`--pace` 路徑有鎖、派工 hook 路徑沒有 |
| 19 | §7.2 `BURNDOWN_CAP_CEILING`（夾層上限旋鈕，只准調小） | 無 | 無 | 全 repo grep：僅附錄自身 3 處命中 | 缺：未實作，A4 落款、骨架、Dev 報告皆未揭露（〈三〉P3-4） |
| 20 | R-4.2.9-1 只由操作者顯式指令觸發 | `issue()` 為唯一寫入口 | 244 | — | 完備（載體不具防偽性質，附錄 §3.4 已入憲，本鏡不另判） |
| 21 | 2026-08-28 立案情境須「誠實不生效」（QB2 α） | qb `Burn.masks` 的 `total` 守門 | 無專測 | 本鏡以附錄 §2.2 讀數合成實跑（週 56%、Fable scoped 91%、短窗 49%）：`active_model` 為 `None`／`fable` 時 `Amort.total_kind`＝`weekly_scoped`、授權 effect＝inert、畫面「本次未放寬任何軸：kind=session（與被點名軸不同窗）…」；`active_model=sonnet` 時別家分軌軸被攤提遮掉，無授權即 cap 8 | 完備（與附錄 §9-1、QB2 一致） |

BD 索引（附錄 §8）：

| 判準 | 測試（tq 行） | 狀態 |
|---|---|---|
| BD-1 | 85、110 | 有 |
| BD-2 | 126 | 有（字典序比較，rec 分量盲區） |
| BD-3 | 138 | 有 |
| BD-4 | 147、154 | 有（寫入端第二臂弱） |
| BD-5 | 85、119、154 | 有（端到端同窗臂缺） |
| BD-6 | 230 | 有 |
| BD-7 | 230（消費端）、244（寫入端三臂；本鏡實跑確認三臂 rc=1 的理由分別是 `missing`、`bad-horizon`、`bad-horizon`，不是軸被丟掉） | 有 |
| BD-8 | 168 | 有（未 gated：`wrap_minutes`／`NOTE_MUST_FINISH` 已在 HEAD） |
| BD-9 | 176 | 有 |
| BD-2′ | 85、110 | 有 |
| 無對應鎖 | §7.2 `BURNDOWN_CAP_CEILING`（無實作）、§3.2 `issued_at` aware、§6.3 events 檔 inert 列 | 缺 |

#### 一-5-d 「紅面」是否真的是「拆掉具名機制」

- 測試檔裡的「紅面」有兩種：(i) 對錯誤版算式的獨立重算（不跑被拆掉的碼）——`assertIsNone(Q._cap_for(Q.BAND_FREE, Q.AXIS_FAR, P))`、`assertGreater(max(d.cap, P.cap_prepare), 0)`、`assertEqual(B._left(until, NOW) or INF, INF)`、`swapped > cap_prepare`、`wrong < anchor[0][3]` 五處；(ii) 對 production 輸出的斷言。(i) 本身不會因 production 碼被改而變紅，咬合由旁邊的 (ii) 提供。
- 本鏡不採信「紅面」字樣，直接做突變：隔離副本 49 個單點突變（具名機制被拆、順序被換、接線被拔），**31 個被殺、18 個存活**。(i) 那五處各自對應的具名機制（夾層上限 M01、ceil 夾原值 M02、halt 合取 M06、過期判準 M08 與解不出當永久 M09、收尾保留段 M20）全被 (ii) 殺掉。沒有發現「紅面其實只是改一個數字」的測試。
- 18 個存活突變：6 個等價／冗餘防線（M10、M11、M13、M16、M30、N02）；12 個、8 類屬真缺口，都是測試咬合度，沒有任何一個對應到 production 碼已經錯（8 類見〈三〉P3-5）。

| 批 | 突變數 | 殺 | 存活 | 存活清單 |
|---|---|---|---|---|
| 第一批（具名機制：夾層、底線合取、判準、接電） | 30 | 24 | 6 | M10、M11、M13、M16、M27、M30 |
| 第二批（落款欄位、出聲字樣、接線） | 15 | 7 | 8 | N02、N03、N04、N08、N09、N10、N13、N14 |
| 第三批（BD-2 分量、寫入端） | 4 | 0 | 4 | P01、P02、P03、P04 |
| 合計 | 49 | 31 | 18 | |

## 〈二〉P≤2 清單

**無。**

口徑：產品／文件輪＝結案不成立、不誠實、終點設計有結構漏洞；守衛面行為缺陷＝`severity.md`〈暴露度〉（真實暴露才 P2）。本鏡評估了三個最接近 P2 的候選，全部判 P3，理由如下：

1. 清倉效果帶未揭露（〈三〉P3-1）：效果帶是已裁決的設計結果（附錄 §4.4 與 QB1），數字在證據檔可見，沒有不實陳述；未揭露的是它對掌舵者當前處境（週軸正逼近 85%）的後果。判 P3，但屬 commit 前必改，且該題是授權句所說「真需要我決定」的題。
2. Q2 後半句「逐功能 E to E」前六次沒有回答（〈三〉P3-8）：證據檔（主檔〈六-3〉）已誠實限定，沒有把推論寫成已驗；缺的是對掌舵者結論三句的回答，〈一-2-g〉已補。
3. A4 落款「cap 由 1 升至 `cap_converge`」（〈三〉P3-2）：同批證據檔有正確數字（標題 cap＝2、軸值 4）；屬措辭。

守衛面准入：本列新增的守衛碼（`quota_burndown.py` 與 `quota_gate`／`quota_policy`／`quota_pace`／`quota_messages` 的接線）有暴露證據——真實互動窗、掌舵者自己的兩則指令與 sid；時序措辭的瑕疵（〈三〉P3-3）不改變准入結論。沒有編修 `.claude/**`。

## 〈三〉P3（當輪改文字或補斷言；皆非決策缺陷）

欄位：座標／重現法／判準／處置。標「必改」者＝commit 前須訂正，否則對掌舵者的說明會失真。

**P3-1（必改）清倉效果帶沒有被寫出來。**
- 座標：〈一-5-b〉表；PRD A4 落款的「劃界」句、骨架〈三-3〉判讀；本機落款 45c49b8e35。
- 重現：本鏡實測（唯讀）——真實快取 20:16:29 +08:00（週 83%、短窗 55%）：無授權 (cap 2, 現在可派 1)、有授權 (4, 2)；合成週軸 ≥86%：無授權 (1, 1)、有授權 (2, 1)（`sa/probe_effect_band.py`；在 repo 內等價作法＝用 `tools/tests/test_quota_burndown.py` 的 `state()`／`dec()`／`burn()`，把 `real()` 的週軸 pct 改 86、短窗改 55，比較 `dec(s, None, 5.0)` 與 `dec(s, burn(), 5.0)`）。
- 判準：文件輪「不誠實」的近端——落款文字讓讀者以為 A4 症狀已治，而同一台機器上週軸越過 prepare 錨點後 `--pace` 會重現「清倉生效中、現在可派 1」。
- 處置：A4 落款與骨架〈三-3〉補一句「效果帶＝被點名軸低於 prepare 錨點（出廠 85%）；≥ 錨點時授權只把該軸 cap 1→2、現在可派維持 1」。對掌舵者的說明同。另請主控用互動選項請掌舵者裁一題：「週軸過 85% 之後要不要仍放寬？A 維持現狀（慢慢用，1 個並行）；B 另立修憲，授權期間 prepare 帶比照 converge 帶（仍保留 halt 與 must-finish）」。B 要走修憲與守衛面准入，那時的暴露證據就是這次實況（附 `--pace` 畫面與 sid）。

**P3-2（必改）A4 落款「親驗…`--pace` cap 由 1 升至 `cap_converge`」過度樂觀。**
- 座標：PRD A4 列 2026-10-12 落款句；骨架〈三-3〉`--pace` 逐字「現在可派 2 個 agent（硬上限 cap=2，…）」「⏳ 目前 cap=2 由遲滯維持（這條軸自己的 cap 是 4）」。
- 判準：措辭（severity.md：P3＝訊息誤導／措辭／歸屬）。
- 處置：改「標題 cap 1→2（遲滯維持；軸值＝`cap_converge`＝4，之後每 ≥300 秒 +1）、現在可派 1→2」。

**P3-3（必改）暴露證據的時序與歸屬措辭。**
- 座標：〈一-5-a〉；逐字稿第 36／37／173／210／694 行；PRD 修訂表 v2.1.19 與 A4 落款的「暴露度＝掌舵者真機回報 sid＋畫面字樣」；骨架〈二-1〉「命中」句與〈三-3〉判讀 (1)「下令前後同一組軸」。
- 判準：歸屬／措辭。畫面是主控自跑、先於指令 2 分 37 秒與 3 分 43 秒；落款前後的兩次讀數不是同一組。
- 處置：改寫為「真實互動窗：掌舵者指令（逐字稿第 173／210 行）與 sid；`--pace` 畫面為主控自跑、先於指令約 3 分鐘，同一快取 TTL 窗內水位未變〔推論〕」；〈三-3〉判讀 (1) 的「下令前後同一組軸」改「落款前（18:16）與落款後（19:34）兩次讀數，軸值不同組」。

**P3-4 規範與碼不一致、以及未揭露的未交付項。**
- (a) 骨架〈二-2〉Q-cross 定義「`Amort.total_kind` == 被點名軸」，碼是「`Amort.total_kind` 的軸是 Q-same」（超集，qb 第 183～185 行的 `total`／`hold`；〈三-1〉(c) 已自揭）；PRD v2.1.19 把〈二-2〉當 BD-2′ 的規範文本引用。以碼為準改寫〈二-2〉（〈六-C2〉有建議句）。
- (b) 附錄 §7.2 區塊 7b 的第二鍵 `BURNDOWN_CAP_CEILING`（只准調小的夾層上限旋鈕）未實作（全 repo grep 僅附錄自身 3 處）；PRD v2.1.19 的規範範圍寫「附錄 §3～§6、§8」（不含 §7 草案文字），可讀作有意排除，但沒有明說；§7.3 例外表第 10 列與 §9 兩個指標名同。處置：A4 落款加一句「§7（併入 PRD 本文的草案文字）不在本版射程：`BURNDOWN_CAP_CEILING`、§8 例外表第 10 列、§9 指標名未落地；§6.3 兩計數器以 `autosdd_burndown_events.jsonl` 為等價物（僅 `--pace` 路徑寫）」。

**P3-5 測試咬合度：8 類缺口（突變存活）。** 重現＝〈五〉第 2 項的突變指令；判準＝附錄 §8 與 `Rule 9`（一支不可能失敗的斷言是壞斷言）；存活的突變沒有任何一個對應到 production 碼已經錯。處置＝補斷言；🔴 回歸鎖軌只剩 4 行餘裕（`_REGRESSION_LANE_LOG` R213 列 305 ≤ 309），全補約 +10～15 行，超過軌上限，需同時搬等量史料或擇優只補前四類（≤4 行）後走收尾單人窗口重釘。

| # | 缺口 | 對應需求 | 存活突變 | 建議最小斷言 |
|---|---|---|---|---|
| 1 | `issued_at` 無 offset 不會被發現 | §3.2「aware，帶 offset」 | N13、P03 | 255 行測試加 `datetime.fromisoformat(rec["issued_at"]).utcoffset() is not None`（1 行） |
| 2 | `active()` 沒把被點名軸 `resets_at` 帶進 `Burn` 不會被發現（同窗鄰軸在生產路徑靜默失效） | QB6 | N03 | 217 行測試加 `self.assertEqual(self.active().named_resets_at, WEEK)`（1 行） |
| 3 | 發令時刻、效期終點、效期剩餘、must-finish 門檻未被斷言 | R-4.2.9-4 ②③、附錄 §9-9 | N08 | 85 行 needle 元組加「發令」「作用至」「效期剩」「must-finish 門檻」（0～1 行） |
| 4 | 未放寬軸的具名理由文字未被斷言 | BD-9 | N09、N10 | 110 行測試加 `"與被點名軸不同窗" in dec(s, short).burndown.text`（1 行） |
| 5 | 寫入端對 FALLBACK／MODEL_SCOPED 的拒絕分支沒被走到（快取沒有該軸而 rc=1） | BD-4 第二臂寫入端 | M27、P04 | 244 行測試的合成快取加兩軸後 `issue(kind)` 斷言 rc=1 且訊息含「屬付費保險軸」（約 3 行） |
| 6 | 派工 hook 路徑的 kill-switch 沒被鎖 | QB3 | N04 | 273 行末段：`policy_env` 設 OFF 時 `QG.quota_gate(...)` 的 spy `burndown` 為 `None`（約 3 行） |
| 7 | `--status --model` 沒被鎖 | §4.1 底線③ 的 `--status` 面 | N14 | `B.status(NOW, {}, self.path, model="fable")` 對照預設（1～2 行；優先序最低） |
| 8 | BD-2 窮舉以字典序比較，rec 分量單調沒有獨立斷言（逐軸 rec 只影響顯示） | 附錄 BD-2 兩分量 | P01、P02 | 126 行把比較拆成 cap 與 rec 兩個斷言（+1 行） |

等價／冗餘存活（非缺口，供對照）：M10、M11（kill-switch 在 `verdict` 與 `active()` 各有一道，單拆一道不改行為；兩道都拆＝N05 被殺）、M13（被點名軸缺席由 `StopIteration` 被 `except` 吞成 `None`）、M16（`named` 與 `total` 實務上互相蘊含）、M30（夾層後 `min(rec, cap)` 在數學上多餘）、N02（`_in_cap_gate` 與 `_eligible` 的 FALLBACK／MODEL_SCOPED 判斷重疊）。

**P3-6 清倉段在 `--pace` 輸出裡出現兩次。**
- 座標：骨架〈三-3〉逐字——第 1 行（`pace_line`，`quota_messages.py` 第 774 行）與第 3 行尾（`describe()`，`quota_policy.py` 第 828 行）各一份 382 字元（本鏡以骨架逐字量得）的相同字串。
- 判準：冗長但不誤導，決策無影響。
- 處置二選一：(i) `describe()` 不附、保留 `pace_line` 與 `status()` 兩處（缺點：`quota_gate.py` 第 1009 行的 hook 警語也用 `describe()`，會失去清倉段）；(ii) 維持現狀並在 A4 落款註明「`--pace` 會出現兩次」。本鏡建議 (ii)；若要消重，改 `pace_report` 的組字讓它只出現一次，不動 `describe()`。

**P3-7 操作者入口沒有常設文件。**
- 座標：`grep -rln quota_burndown --include=*.md`（本鏡親跑；寫本檔前）只命中 PRD、缺陷帳本、`AutoSDD_improving_112.md`、`CrossPlatform_R145_Scan_Findings.md`、本列證據檔與他鏡 findings；根 CLAUDE.md〈現查指令速查表〉、`ONBOARDING.md`、`useMacWin.md` 皆零命中。
- 判準：規範性機制的可用性——撤銷法（`--revoke`、`AUTOSDD_QUOTA_BURNDOWN_OFF=1`）只存在於證據檔與 Dev 報告（scratchpad 不入庫）。
- 處置：A4 落款加一句三個入口（`--issue`／`--status`／`--revoke`＋kill-switch）；是否在根 CLAUDE.md 速查表加一列由主控裁決（該檔被多族測試釘住，動前先盤鎖）。

**P3-8（必改）Q2 後半句「逐功能 E to E」前六次沒有被回答。**
- 座標：〈一-2〉2b 與〈一-2-g〉；第六次結論三句第 2 點。
- 判準：需求追溯（問 2 的第二個可驗收項沒有對應交付）。
- 處置：把〈一-2-g〉併入證據檔〈六〉，對掌舵者的答覆寫「E to E 只有這些」（喚醒鏈尾段 Mac 整段；`--pace`／清倉／`--env-doctor` 單次真機觀測；其餘只有單元與鎖；R212 範圍內 Windows 真機樣本 0 筆）。

**P3-9 §16.2 三列 📎 的文字。** §11.3 的殘留低估既有 ≤2 秒 SLA 測試（`AutoClaude/tests/integration/test_sigint_checkpoint.py`，量真實落盤路徑），應收窄為「注入 95% → 整段凍結的計時」；§11.2 自陳殘留含「交付物」，與 📎 定義（機制已 ✅、只欠驗收資料）字面不符，應在列內說明交付物那一半由 `decide()`＋性質測試承接，或改判 ⏸ 並附再開症狀；§15.5 的「殘留」欄是狀態清單，應改寫成一句（唯一資料殘留＝紅線 11 的版本清單，範圍已因家族判定縮小）。不改格。

**P3-10 T1／T4 標示與 R213 標籤敘述。**
- 座標：骨架〈一〉(c)「T4 的最小響應＝直接做事＋commit」；範本〈🏁〉該句屬 T1，並附「碰 PRD 修憲／守衛面／需跨軌設計時才開 `AutoSDD_improving_N`」；〈三-2〉以 R213 標籤重釘，而範本〈證據檔命名與護欄棘輪〉路徑 (c) 寫「餘裕用盡才換新標籤＝開 R 輪並承擔其義務」。
- 判準：文件一致性（機械鎖全綠：`test_adr_xplat001_c1c2_lock` 187 項通過）。
- 處置：〈一〉(c) 改「T1（掌舵者新指令）與 T4（A4 症狀）同時成立；沿用 R212 第一至四列的 R 系列形態（證據檔＋缺陷帳本入口），不開軌道① 計畫書；重釘標籤前進到 R213 屬範本路徑 (c)，到期義務（`_REPIN_NET_CAP_DUE_ROUND`＝214）尚未觸發，檔名鐘（`current_round()`）仍＝R212」。

**P3-11 前六次對掌舵者的措辭**：見〈六-F1～F6〉。

## 〈四〉P4 理論洞（只登記、不修；各附一句可觀測再開症狀）

| # | 洞 | 暴露度 | 再開症狀 |
|---|---|---|---|
| P4-1 | 效期只比 wall-clock（`_left`：`now < until`），不比被點名軸現讀的 `resets_at`；附錄 §3.1／§7.3 的敘述「新視窗的 `resets_at` 是另一個字串、舊落款結構上不匹配」在碼裡並不成立。伺服器提前重置視窗時，新視窗仍被舊落款放寬到原 `until` | 讀碼（qb 第 96～99 行）＋前提已在真實語料發生：〔本鏡親跑〕`~/.autosdd/traces/quota_burn.jsonl` 的 `weekly_all` 205 列讀數有 205 個相異 `resets_at` 字串（亞秒抖動），其中 1 次相鄰兩列 −20 小時（2026-09-10 14:01:56→16:31:44 +08:00，`resets_at` 由 09-12 18:00 前移到 09-11 21:59:59，週軸 pct 75→29；提前改錨，正是落款會活過視窗的方向）、1 次 +20 小時（2026-09-16 23:00:12→2026-09-17 10:06:59，由 09-18 21:59:59 後移到 09-19 18:00，pct 67→46；後移改錨，落款會提早失效＝fail-closed 的方向）；兩次發生時沒有落款在場，所以不是暴露證據 | `--status` 全 ✓，而被點名軸現讀 pct 較落款內 `readings_at_issue` 驟降、`resets_at` 現讀值比落款 `until_resets_at` 晚（附兩份畫面） |
| P4-2 | 單槽落款：`issue()` 覆蓋舊檔（只在訊息提「覆蓋舊落款 id」）、`revoke()` unlink；燃燒落款與 events 檔只存 id。附錄 §3.4(1)「可稽核」只在落款檔存在期間成立；同窗兩則不同軸指令也只能擇一 | 構造；本窗兩則指令實際只落了週軸一份 | `quota_burn.jsonl` 出現某 `bd` id，而 `~/.autosdd/traces` 已無含該 id 的落款、也查不到指令逐字（附列座標） |
| P4-3 | `tools/lib/quota_burndown.py` 不在 `_GOV_EXACT`（`.claude/hooks/block_destructive_git.py` 第 1445 行起，含同族的 `quota_gate`／`quota_policy`／`quota_pace`／`quota_messages`／`quota_env_layers`）；落款檔住專案根外，治理面禁寫射程外。無人值守窗口可改寫該檔或偽造落款（附錄 §3.4 已接受載體不防偽；碼檔保護是另一層）。修需動 `.claude/hooks/**`，無暴露證據不得動 | 構造 | `AUTOSDD_UNATTENDED` 有設的逐字稿出現對該檔的 Edit／Write，且 hook 痕跡無阻斷（附 sid＋seq） |
| P4-4 | events 檔列的 `cap` 記未經遲滯的 `decision.cap`（本機實測 4），而同刻 `--pace` 標題顯示 2：`log_decision`（`quota_gate.py` 第 962 行）在平穩性步驟之前 | 本機真列：`autosdd_burndown_events.jsonl` 唯一一列 `cap:4`、標題 cap＝2 | 對帳時 events 列 cap 與同刻標題 cap 被當成矛盾（附兩處座標） |
| P4-5 | `hold` 遮罩對所有合格軸成立，未放寬理由字樣對「不同窗的長窗軸」寫成「已在放寬上限，無可再放」。合成重現：加一條 60%、43200 分鐘後 reset 的未知 kind 軸，無授權與有授權皆 (notice, far, cap 4, rec 2)，清倉段卻寫 `kind=nimbus_quill（已在放寬上限，無可再放）`（cap 4 < `cap_notice`）。今日帳號沒有這種軸 | 構造（`sa/probe_why2.py`） | 真實 `--pace` 清倉段出現「已在放寬上限」，而該軸 cap 小於 `cap_notice` 且與無授權逐格相同（附畫面） |
| P4-6 | 同窗鄰軸零容差：本機實測 `weekly_scoped` 與 `weekly_all` 的 `resets_at` 差 218 微秒（附錄 §9-5 觀察項）；`seven_day` 與 `weekly_all` 字串全等。若伺服器對非分軌的同窗軸也吐微秒差，鄰軸靜默不放寬 | 本機真實 218 微秒（分軌軸，已被底線③擋掉，不影響結果） | `--status` 清倉段把 `seven_day`（或其他同窗合格軸）標「與被點名軸不同窗」，而兩軸 `resets_at` 只差微秒（附 `quota_meter.py --from-cache --json` 兩軸字串） |
| P4-7 | `quota_gate.py` 斷言行 497／500（hub tier 上限，〔他包回報：Dev 報告 §1〕）；再增任何斷言行即觸 hub 上限 | 本鏡 `check_loc_budget --json` rc=0、四類違規皆空（現況不違規） | 下一次對 `quota_gate.py` 的淨增編修使 `check_loc_budget.py --json` 的 `tier_violations`／`special_violations` 非空（附輸出） |
| P4-8 | 回歸鎖軌餘 4 行（`_REGRESSION_LANE_LOG` R213 列 305 ≤ 軌上限 309）；任何 `tools/tests` 淨增超過 4 行即超軌 | 本鏡 `test_adr_xplat001_c1c2_lock` 187 項通過 | `repin_growth_problems()` 回「超出每輪上限」或「回歸鎖軌超上限」（附輸出） |
| P4-9 | 方案指紋變動（帳號鍵缺席或軸集合改變）使落款靜默失效（fail-closed；`--status` 第 4 項可偵測）。本機落款的指紋含帳號雜湊與六個桶名（雜湊不入本檔） | 構造 | `--status` 第 4 項 ✗，而使用者沒換帳號（附 `--status` 與 `quota_meter.py --json` 的 `account_key` 欄） |
| P4-10 | `readings_at_issue` 只存不比對：附錄 §3.4(2)「偽造可對帳」只在人工對帳層，沒有任何碼把它與同時刻 `quota_burn.jsonl` 比較 | 構造 | 落款內 `readings_at_issue` 與同時刻燃燒落款列不一致，而 `--status` 全 ✓（附兩處） |
| P4-11 | Windows 面：`quota_gate.py` 第 98 行無 try 直接 import `quota_burndown`；它若在 hook 載具的 Python 載入失敗，整條額度軸短路（Dev 報告 §8 已述；本機以 py39 掃描器與全套測試釘住） | R212 範圍內 Windows 樣本 0 筆 | Windows 機 `& .\.venv\Scripts\python.exe tools/lib/quota_burndown.py --status` 非預期 rc 或 ImportError（附輸出） |
| P4-12 | §16.5 (iii)「命中而不轉格」沒有規則：DEF-200-518 的分流去向寫「C4 實跑命中」，PRD §8 列 9／§9 告警仍 ⏸（症狀句字面「桌面通知與 ESCALATION 皆未觸發」與 C4 事實不符） | 帳本與 PRD 措辭不一致（〈一-2-e〉） | 同一 ⏸ 列再被某 DEF 列標「命中」而 PRD 格不動（附兩處座標） |
| P4-13 | `--status` 對 kill-switch 與「被點名軸缺席」兩項的 ✗ 字樣沒有鎖（M10／M13 等價存活的另一面：`active()` 行為不變，但 `--status` 畫面會少一行） | 構造 | 設 `AUTOSDD_QUOTA_BURNDOWN_OFF=1` 後 `--status` 第 2 項不是 ✗（附輸出） |

## 〈五〉本鏡跑過的指令與 rc（逐字摘要；pytest 數字以「N 項通過」表示）

環境：mac、`.venv` python 3.11；`tools/tests` 子集一律 `export AUTOSDD_SENTINEL_OFF=1`、`unset AUTOSDD_PARALLEL_TESTS`、`python -B`、`cd tools/tests`。scratchpad 絕對路徑（以下簡稱 `SA/`）：`/private/tmp/claude-501/-Users-wuweihong-Antigravity-AISDCL-Agent/ed1c9022-22cc-4974-a8b3-9d4ebfa5f6bd/scratchpad/sa`。

1. `python -B -m unittest -v test_quota_burndown` → rc=0；`Ran 14 tests in 0.019s`／`OK`。
2. 突變實驗（隔離副本 `SA/mut/repo/tools/{lib,tests}`；基線副本 `Ran 14 tests`／`OK`，`SA/mut_base.log`）：`python mutate.py`（30 個）、`python mutate2.py`（15 個）、`python mutate3.py`（4 個）→ 各 rc=0；結果 `SA/mut_results.txt`、`SA/mut2_results.txt`、`SA/mut3_results.txt`；合計 49 個、殺 31、存活 18（〈一-5-d〉）。每個突變只替換一個（或兩處）字面、跑 `python -B -m unittest test_quota_burndown`、立刻還原；repo 本體零改動。
3. 根層 unittest，全部 rc=0：`test_sentinel_tick_e2e_r145`（Ran 12 tests／OK）、`test_wake_chain_halt_r278`（Ran 58／OK）、`test_quota_env_layers`（Ran 38／OK）、`test_quota_policy`（Ran 339／OK）、`test_mac_endurance_r83`（Ran 133／OK）、`test_quota_reconcile_gap`（Ran 9／OK）、`test_adr_xplat001_c1c2_lock`（Ran 187／OK）、`test_context_budget_guard.FanoutLedgerConcurrencyTest`（Ran 5／OK）、`test_context_budget_guard.ControllerIdlePrepareWatchTest` 加 `ArmedDriftSelfHealTest` 加 `OrphanModeWatchTest`（Ran 20／OK）。quota 四模組 339＋38＋9＋14＝400，與 Dev 報告「Ran 400 tests」一致。
4. AutoClaude（`cd AutoClaude && python -m pytest <檔> -q -p no:cacheprovider -n 0`）全部 rc=0：`tests/test_r100_boot_self_check.py` 58 項通過、`tests/test_r100_power_loss_protection.py` 16 項通過、`tests/test_r100_dirty_worktree_rescue.py` 33 項通過、`tests/execution/test_prd12_permission_bypass_invariant8.py` 86 項通過、`tests/integration/test_sigint_checkpoint.py` 加 `tests/core/test_kernel_token_halt.py` 12 項通過。
5. `python tools/lib/quota_policy.py --env-doctor` → rc=0（載入鏈「行程 env > AutoClaude/.env > .env > env.shared > 出廠」；`env.shared` 4 鍵、`.env` 4 鍵、`AutoClaude/.env` 不存在；`AUTOSDD_QUOTA_HALT_PCT = 98〔env.shared〕`）；`python tools/lib/quota_policy.py --print-env-example` → rc=0，與 `.env.example` `diff` rc=0。
6. `python tools/lib/quota_burndown.py --status`（唯讀；真落款 45c49b8e35）→ rc=0：六項皆 ✓；「🔥清倉模式生效中（…效期剩 7552 分鐘／must-finish 門檻 5 分鐘）⇒ 本次放寬：kind=session band prepare→free cap 2→8 rec 1→8、kind=weekly_all cap 2→4 rec 1→2、kind=five_hour band prepare→free cap 2→8 rec 1→8、kind=seven_day cap 2→4 rec 1→2；未放寬：kind=weekly_scoped（model-scoped 不納入）、kind=spend（fallback 不納入）」。落款檔與 events 檔的 mtime 作業前後皆 19:34 未變。
7. `python tools/probe/wakechain_e2e.py --selftest` → rc=0；尾行 `SELFTEST rc=0（bypass 為負對照，必須紅在 S2／S3／S5a／S5b）`。
8. `python tools/check_defect_log_crossref.py --unresolved-count` → rc=0；`未結列數＝0／全部 229 列`（`warn=86 fail=98` 是門檻值，不是命中數）。
9. `python AutoClaude/tools/check_loc_budget.py --json` → rc=0；`root_tools_violations`／`tier_violations`／`special_violations`／`absolute_violations` 皆 `[]`，`total_violation` 為 False。
10. `python tools/check_handoff_carriers.py` → rc=0；census 行「commit 訊息＝757 則」且前瞻宣告 0 筆（寫本檔前）；寫本檔後重跑的結果見本節末。
11. `gh run list --commit 1818de87fbbb5a96673008d50eeb1e619ce22223 --json databaseId,name,conclusion,status` → rc=0；6 筆全 completed／success（38231604962、38230947003、38230301093、38230301052、38230301082、38230301062）；`git show --stat 1818de87` → `29 files changed, 1543 insertions(+), 47 deletions(-)`。
12. §16.2 解析（python3 內嵌小腳本，讀 PRD 第 2604～2790 行）→ rc=0：72 列、結案格 ✅2／➖33／⏸29／📎8；路徑 76 處（75 存在）；符號 90 個（64 命中）；DEF-ID 9 個全在帳本；ADR 1＋docs 7 皆存在；逐列結果表 `SA/rows_table.md`（已併入〈一-2-h〉）。
13. `claude --version` → `2.1.296 (Claude Code)`；`cd AutoClaude && python -c "from autoclaude.utils.verified_cli_versions import family_verdict; print(family_verdict('2.1.296')); print(family_verdict('2.2.0'))"` → rc=0，`('family', '2.1.295')`、`('unknown', None)`。
14. 逐字稿唯讀解析（python3 內嵌）：兩則指令 enqueue 10:19:26Z／10:20:32Z（第 173／210 行）；`--check`／`--pace` 同為 10:16:49Z（第 36／37 行）；落款 11:34:11Z、落款後 `--pace` 11:34:21Z（第 694 行）；後續 Agent 派工第 716／717（11:36）與 778／779（11:43）行；T1 貼文第 12 行（含授權句）。
15. 純函式探針（隔離副本，零 I/O；唯一例外是 `probe_real_ab.py`，它唯讀 import repo 的 `tools/lib` 並讀真快取）：`probe_real_ab.py`（rc=0；真讀數 20:16:29 的有無授權對照）、`probe_effect_band.py`、`probe_0828.py`、`probe_bd8.py`、`probe_bd2.py`、`probe_bd5.py`、`probe_why.py`、`probe_why2.py`、`probe_bd7_writer.py`，皆 rc=0，輸出已併入各節。
16. `git status --short`：作業初 15 筆既有改動；作業期間新增主控編修的 `docs/04_planning/PRD_Amendment_R108_BurnDown_Addendum.md`、`docs/06_quality/CrossPlatform_R212_WakeChain_EnvLayer_Evidence.md`（mtime 20:27／20:30）與他鏡 findings；本鏡審的六支 `tools/lib/quota_*.py`（含 `quota_burndown.py`）、`tools/tests/test_quota_burndown.py`、`test_adr_xplat001_c1c2_lock.py`、`test_run_root_unittests.py` 與 `.env.example` 的 mtime 皆 ≤ 19:24，作業期間未變；唯一變動的程式檔是 `tools/lib/governance_docs.py`（20:27，主控登記四份 findings）；本鏡未改任何 repo 檔（除本檔）。
17. `quota_burn.jsonl` 唯讀掃描（python3 內嵌）：`weekly_all` 有 `resets_at` 的列 205、相異字串 205；相鄰列回退超過 1 小時 1 次（−20.0 小時）、前移 1 小時至 6 天之間 1 次（+20.0 小時）。
18. 本鏡沒跑：根層全套（QA 鏡）、`python tools/session_resume_planner.py --pace`、`python tools/probe/wakechain_e2e.py --run`、`quota_meter` 的 refresh、任何會寫真實 `~/.autosdd/traces` 的指令（`--issue`／`--revoke` 皆未跑）。

## 〈六〉文件訂正清單（對主控骨架、PRD v2.1.19／A4 落款、前六次宣稱的措辭）

方向欄：樂觀＝寫得太樂觀；悲觀＝寫得太悲觀；歸屬＝歸屬／出處；不一致＝與碼或他處不一致。

### 六-A 證據檔骨架〈一〉

| # | 位置 | 原句（摘） | 方向 | 建議訂正 |
|---|---|---|---|---|
| A1 | 〈一〉T1 原文 | 引到「4.需要馬上切到Windows…嗎？」＋「派出 Architect／SA／SD／QA…」 | 歸屬 | 補授權句逐字（〔逐字稿第 12 行〕）：「以上若需要我決策，請依照最佳化, 最理想, 最適當的解決方案，我授權幫我決策, 若真需要我決定, 請以最簡單的解釋, 讓我互動選項決策」——〈二-2〉的依據在此 |
| A2 | 〈一〉(a)「再開症狀實際發生」 | 以〈二-1〉畫面為證 | 樂觀 | 補時序句（見 P3-3）：「`--pace` 畫面 18:16:49 先於兩則指令（18:19:26／18:20:32）；指令後、落款前未再跑 `--pace`；同一快取 TTL 窗內水位未變〔推論〕」 |
| A3 | 〈一〉(c) | 「T4 的最小響應＝直接做事＋commit」 | 不一致 | 見 P3-10 建議句 |

### 六-B 骨架〈二-1〉

| # | 位置 | 原句（摘） | 方向 | 建議訂正 |
|---|---|---|---|---|
| B1 | 〈二-1〉末段 | 「指令在（兩則逐字）、cap=1 在、sid 在 ⇒ 命中」 | 樂觀 | 同 A2 |
| B2 | 〈二-1〉末段 | 「與…§2.3 的 2026-08-28 立案實測同形」 | 樂觀 | 改「與 2026-08-28 同為短窗被跨窗攤提抬帶；差別在供給軸：當時是 `weekly_scoped`（BD-2′ 治不到，現行碼誠實 inert），本次是被點名的 `weekly_all`（BD-2′ 治得到）」（本鏡以 08-28 讀數合成實跑：`active_model` 為 `None`／`fable` 時 inert） |

### 六-C 骨架〈二-2〉

| # | 位置 | 原句（摘） | 方向 | 建議訂正 |
|---|---|---|---|---|
| C1 | 標題 | 「掌舵者 T1 授權『依最佳化代決』」 | 歸屬 | 補出處：逐字稿第 12 行授權句（同 A1） |
| C2 | Q-cross 條 | 「`Amort.total_kind` == 被點名軸、被點名軸本身 Q-same 成立」 | 不一致 | 以碼為準：「Q-cross＝進 cap gate 的合格軸，且本次攤提的長窗供給軸 `Amort.total_kind` 的軸是 Q-same（被點名軸或其同窗鄰軸），且被點名軸本身 Q-same 成立 ⇒ 該軸攤提暫停；實際只在 `window == Amort.rate_window` 的短窗軸上生效」 |
| C3 | Q-same 條 | 「享 BD-1 與 BD-2」 | 不一致 | 補「BD-2 的 `hold` 遮罩對所有合格軸成立，但只在短窗軸生效；Q-same 長窗軸實際只享 BD-1」 |
| C4 | 全節 | 未載 | 樂觀 | 補三項：單槽落款（同窗兩則不同軸指令只落一份）；遲滯爬升（標題 cap 先 2、每 ≥300 秒 +1）；`BURNDOWN_CAP_CEILING` 未交付（P3-4b） |

### 六-D 骨架〈三〉

| # | 位置 | 原句（摘） | 方向 | 建議訂正 |
|---|---|---|---|---|
| D1 | 〈三-2〉 | 「兩個鐘不混」「R212 時鐘不前進」與 R213 標籤 | 不一致 | 見 P3-10 建議句 |
| D2 | 〈三-3〉判讀 (1) | 「下令前後同一組軸（週軸 78%、短窗 29%）由 `cap=1 …` 變為 `cap=2 …`」 | 樂觀 | 下令前的 `--pace` 是 18:16（週 75%／短窗 8%），落款後是 19:34（週 78%／短窗 29%），不是同一組讀數；改「落款前（18:16）與落款後（19:34）兩次讀數，軸值不同組」；並補效果帶（P3-1）與本鏡同讀數對照（20:16：無授權 (2, 1)、有授權 (4, 2)） |
| D3 | 〈三-3〉判讀 (1) | 「與附錄 §4.4 值域表及〈二-2〉裁決逐格相符」 | 樂觀 | 限定「本次讀數涉及的格」；§4.4 表 horizon `none` 四列依附錄 §4.1（距 reset 解得出且 ≥0）不放寬，與表值不同（附錄內部不一致，碼取 §4.1，`test_bd2…` 的 `minutes=None` 臂斷言不變） |
| D4 | 〈三-3〉判讀 (2) | 「清倉段在 pace_line 標題行與 describe() 行各印一次（同一字串重複）」 | — | 本鏡判 P3-6 |
| D5 | 〈三-3〉判讀 (3) | 「Dev 作業期間週軸由 75% 升到 78%（…符合每 Sonnet 包約 1～3pp）」 | 樂觀 | 帳號跨 session 共用，歸因於 Dev 是〔推論〕；補後續讀數（本鏡 20:16 現查週 83%） |
| D6 | 〈三-1〉(d) | 「第一次 `--pace` 標題 cap 1→2」 | 悲觀 | 補「現在可派 1→2；標題最高 2（rec＝`cap_prepare`），軸值才會爬到 4」（骨架其實已記，但 A4 落款沒承接） |

### 六-E PRD v2.1.19 與 A4 落款

| # | 位置 | 原句（摘） | 方向 | 建議訂正 |
|---|---|---|---|---|
| E1 | A4 落款「親驗」 | 「`--pace` cap 由 1 升至 `cap_converge`」 | 樂觀 | 見 P3-2 |
| E2 | v2.1.19 觸發欄／A4 落款 | 「暴露度＝掌舵者真機回報 sid＋畫面字樣」 | 歸屬 | 見 P3-3 |
| E3 | v2.1.19 實作座標 | 「`decide()`／`band_inputs()` 各加一個預設不生效的參數」 | 悲觀 | 實際 7 處簽章／欄位：`decide(burndown)`、`axes_of(relax)`、`resolve(floor, hold)`、`band_inputs(hold)`、`row_of(bd)`、`record_burn(bd)`、`Decision.burndown`，另加 `pace_line`／`describe` 兩處渲染追加；改「共 7 處預設不生效的簽章／欄位（`quota_policy`／`quota_pace`／`quota_gate`），另 2 處渲染追加（`quota_messages`／`quota_policy`）」 |
| E4 | v2.1.19 規範文本範圍 | 「附錄 §3～§6、§8」 | 不一致 | 見 P3-4b：明寫 §7 不在本版射程 |
| E5 | A4 列與 §12 列 | 舊「現況」（A4：「零落地…零命中…帳本無開帳列」；§12：「…容器偵測零命中」）與同列新落款並存 | 不一致 | `【2026-10-12 落款】` 標記使時序可辨，但單看前半句會讀成現況；在舊句前加「（凍結日現況）」 |
| E6 | A4 落款「劃界」 | 缺項 | 樂觀 | 補：效果帶（P3-1）；遲滯爬升；單槽落款；Windows 新增面（`quota_gate.py` 無 try 直接 import；CLI 於 cp950 的輸出）；入口三指令與 kill-switch（P3-7）；Windows 驗收可加一行 `& .\.venv\Scripts\python.exe tools/lib/quota_burndown.py --status`（預期 rc=1、首行「清倉授權：沒有有效落款」） |
| E7 | §16.3 (b) 與 §16.2 | 快照 29／33／31／8 與結案格欄現況 31／33／29／8 | 不一致 | 修訂表 v2.1.19 或 §16.3 加一句「現況由 §16.2 結案格欄機械可數（本鏡腳本：解析表格第 3 欄分組計數）」 |

### 六-F 前六次對掌舵者的結論三句（第六次；掌舵者貼回的原文）

| # | 原句（摘） | 方向 | 建議訂正（下次對掌舵者的答覆可直接用） |
|---|---|---|---|
| F1 | 「你只剩在 Windows 貼一行指令，沒有別的事」 | 樂觀 | 「Windows 那台要驗的有三件（約 1～2 小時，主檔〈八-4〉共 6 項）：同步＋hook 首次實跑、表② 回填、驗收一行；本次再加一行 `quota_burndown.py --status`」 |
| F2 | 「照你 10-10 自己立案的定義（101 項各有歸宿），早就『做完』」 | 歸屬 | PRD 修訂表 v2.1.17 自陳「各列歸格＝主控代決（掌舵者授權…，非逐列明示追認；掌舵者可隨時推翻）」。改「依 PRD §16.1（10-10 由我代決落款、你可隨時推翻）」 |
| F3 | 問 2 只答「做完」 | 悲觀 | 補〈一-2-g〉：E to E 只有喚醒鏈尾段（Mac 整段）與單次真機觀測，其餘只有單元與鎖，Windows 0 筆（R212 範圍內） |
| F4 | 「Mac 這邊全部驗過」 | 樂觀 | 「Mac：`--env-doctor` 乾淨、`.env.example` 與生成值相同、hook 以暫存 repo 的真 pull 驗；對真 repo 根的 `--fix` 刻意沒跑」 |
| F5 | 「現在：✅30、依設計不做 33、等症狀 30、只欠驗收紀錄 8」 | 不一致 | 本列後 ✅31／➖33／⏸29／📎8 |
| F6 | 問 1 只講工程根因 | 悲觀 | 補需求層一句：「七次同題的縫在終點定義——你要的字面（所有功能＋逐項 E to E）與 §16.1 之間沒有你明示追認；要收斂，請在互動選項選：A 維持 §16.1；B 只補 Mac 零成本的 📎（§11.1／§11.3／§11.7）；C 全部重開」 |

### 六-G 本鏡認為前六次宣稱中「寫得對、不必改」的幾處（對照用）

- 「六支 CI 全 success」「29 個檔」「帳本未結 0」「入庫工具 `--run` 只被 mock 驗過」：本鏡現查全部屬實（〈五〉第 8、11 項；Run4〈二〉檔頭自陳 `--run` 只被 mock 驗過）。
- 「收斂是症狀驅動、Windows 零量測、真 429 寫標記端沒有新樣本、24 小時多次 reset 連續閉環未做」：與證據檔逐字一致，沒有被寫成已驗。
- 「§12 權限旗標 ⏸→✅」：機制、86 項測試、症狀座標（SddBridge 證據第 13／80～84／391 行）皆屬實；r5 真跑證據在 scratchpad 不入庫（Run4〈四〉自陳）。

## 〈七〉重讀快照：主控在本鏡作業期間的編修與本鏡條目的處置現況（20:34:00 快照；以現查指令為準）

背景：主控自 20:27（檔案 mtime；本鏡約 20:31 發現）起即時套用各鏡 findings（附錄〈落地訂正注〉、骨架〈一〉〈二〉〈三〉〈四〉、PRD v2.1.19 列與 A4／§11.2／§11.3／§15.5／§16.3 (b) 欄、主檔〈二-0〉追記，並登記四份 findings）。下表用 `grep -c` 針對每個條目的訂正字面現查；`PRD`＝`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`，`證據`＝`docs/06_quality/CrossPlatform_R212_BurnDown_FourParty_Evidence.md`。主控仍在編修，請重跑指令。獨立性說明：〈一〉～〈六〉在讀到主控更新前已寫成；本節與 P4-1 暴露度欄的真實語料數字，是讀到主控轉述的「205 列／改錨 2 次」之後，本鏡自行用 `quota_burn.jsonl` 唯讀重算的（〈五〉第 17 項，數字為本鏡自己的輸出）；本鏡仍未開任何他鏡的 findings 檔。

| 本鏡條目 | 現查（needle 於檔） | 快照值 | 判讀 |
|---|---|---|---|
| P3-1 效果帶 | 「效果帶」於 PRD／證據 | 1／3 | 文件面已處置；〈六〉向掌舵者的互動選項與最終答覆仍待落 |
| P3-2 cap 措辭 | 「現在可派 1→2」於 PRD | 1 | 已處置 |
| P3-3 暴露度歸屬 | 「暴露度＝掌舵者真機回報」於 PRD（應為 0） | 1 | 部分：v2.1.19 列與證據〈二-1〉已改；A4 列落款仍寫舊句，兩處不一致 |
| P3-4a Q-cross 定義 | 「以碼為準的定義」於證據 | 1 | 已處置（附錄訂正注 ② 同） |
| P3-4b §7 射程 | 「不在本版射程」於 PRD | 1 | 已處置 |
| P3-5 測試咬合度 | 測試檔 `named_resets_at`／`utcoffset`；測試檔 mtime | 0／0；19:21、295 行 | 未動；證據〈四〉記為修復包 Dev-2 的 C6（hook 路徑 kill-switch、寫入端 QB4、Q-cross 底線、`--status` OFF、刪恆真斷言）。🔴 回歸鎖軌餘 4 行，須以「等量換掉恆真斷言」進行 |
| P3-6 清倉段重複 | `quota_messages.py`／`quota_policy.py` mtime | 18:53／18:50 | 未動；證據〈四〉記 C1 |
| P3-7 操作入口 | 「操作入口」於 PRD | 1 | 已處置（根 CLAUDE.md 速查表是否加列屬主控裁決，未動） |
| P3-8 Q2(ii) 回答 | 證據〈六〉「（待填」殘留數 | 3 | 未處置 |
| P3-9 三列 📎 文字 | 「整段凍結」「唯一資料殘留」於 PRD | 2／1 | 已處置 |
| P3-10 T1／T4 標示 | 「T1（掌舵者新指令）與 T4」於證據 | 1 | 已處置 |
| 〈六〉A1 授權句 | 「我授權幫我決策」於證據 | 1 | 已處置 |
| 〈六〉C4 單槽 | 「單槽」於證據 | 1 | 已處置 |
| 〈六〉D3 逐格 | 「逐格相符」於證據（應為 0） | 0 | 已處置 |
| 〈六〉D5 歸因 | 「Dev 作業期間週軸」於證據（應為 0） | 1 | 未處置（輕微） |
| 〈六〉E3 簽章數 | 「各一個預設不生效」於 PRD（應為 0） | 1 | 未處置 |
| 〈六〉E5 舊現況 | 「凍結日現況」於 PRD | 2 | 已處置 |
| 〈六〉F1～F6 | 取決於對掌舵者的最終答覆 | — | 套用於最終答覆 |

另有三處是本鏡讀到主控新編修後的補充意見：

1. 附錄〈落地訂正注〉④ 與 A4 落款「劃界」寫「週軸另有提前改錨，真實語料 2 次」。本鏡以 `quota_burn.jsonl` 唯讀重算（〈五〉第 17 項）：2 次改錨皆伴隨週軸 pct 下降，但方向相反——1 次提前 20 小時（75→29%）、1 次後移 20 小時（67→46%）。建議改「改錨 2 次（1 次提前、1 次後移；提前者會讓落款活過視窗，後移者讓落款提早失效）」；這也補強〈四〉P4-1 的前提（真實語料已有 1 次落款會活過視窗的方向）。
2. 骨架〈四〉表中本鏡一列「（待其落檔後填）」現可填：`VERDICT: APPROVE`；P≤2＝0、P3＝11、P4＝13；findings 檔＝`CrossPlatform_R212_Row5_Findings_SA.md`。
3. PRD v2.1.19 列寫「P3 全數於同批處置」：本鏡 P3-5（測試咬合度 8 類）、P3-6、P3-8 在 20:34 快照仍是未動或進行中；請在 commit 前以上表的現查結果為準，而不是以「全數」二字為準。
