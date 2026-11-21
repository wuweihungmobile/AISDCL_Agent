# R215 〔OI-20261120-017〕待驗清單收斂設計（Pending Verification Closure）

**狀態**：設計稿（Architect＋SA 合一棒，2026-11-18；唯讀分析，未改程式／帳本）。
**立案**：掌舵者 2026-11-18 20:40 原話：〔OI-20261120-017〕「請把待驗清單改正，冷窗轉送改列為備援, 將所有的問題與帳本,Bug 全部清除, 才算完成本次任務! 若AutoClaude沒有辦法執行完任務, 應算BUG」；同日追加：「請將所有功能都寫好完整的E To E測試案例,不要遺漏任何一個!」。
**判準**：本檔所有「已驗」都附逐字稿座標或指令輸出；沒有座標的一律寫「未驗」。

---

## 0. 結論先講

1. 38 處〔OI-20261120-017〕「待真機／待重測／待目視」＋帳本「fixed 但帶待驗尾巴」各列＋SI 2 筆＋殘局 1 筆，去重後**獨立項目 54 項**，分類：**A 34／B 8／C 9／D 2 項（產出 4 個缺陷 D-1～D-4）／✅ 已驗可直接關 1**（V-F2）。混合項以主類計。分類規則見 §1。
2. **B 類大多其實可以用機器驗**：Claude Code 逐字稿把 hook 的輸出存成固定格式的記錄，介面畫面就是讀這些記錄畫出來的——
   - Stop 推回 ⇒ `attachment.type=hook_blocking_error`（含 `blockingError` 全文）＋`hook_system_message`（例：sid `245e80aa` 2026-11-01T17:50:57.673Z，check_pending_handoff）；
   - Stop `systemMessage` ⇒ `attachment.type=hook_system_message, hookEvent=Stop`（sessionctl_guard 目前共 114 筆）；
   - UserPromptSubmit 擋下 ⇒ `type=system, subtype=informational, level=warning, preventContinuation=true`，內容以 `UserPromptSubmit operation blocked by hook:` 開頭（sid `7f29adfb` 2026-11-18T00:29:59.753Z）。
   - **對照基準**：掌舵者 08:31 貼回的畫面原文（sid `85bcbec8` 第 1186 行）跟上面那筆 `7f29adfb` 記錄**逐字相同**。也就是說「記錄裡有」＝「畫面上有」已經有一次人眼對照。之後 B 類的判準改成「逐字稿有這類記錄」（機器判），只剩「終端機有沒有真的畫出來」留給掌舵者目視，**不擋結案**。
   - **RV-L2 實測（2026-11-18，WP-1，真 `claude -p` 2.1.327，沙盒探針 hook；`python tools/realverify.py run --case RV-L2` 可重跑）：`-p` 與互動模式記錄格式相同，B→機驗換算成立**。
     - Stop `decision:block` ⇒ `attachment.type=hook_blocking_error`，欄位 `hookEvent:"Stop"`、`blockingError:{blockingError:"<reason>",command:"<hook 命令>"}`；另有 `type=user isMeta` 內容 `Stop hook feedback:\n<reason>`，與 `system/stop_hook_summary`（`hookErrors:["<reason>"]`、`hasOutput:true`）。
     - UserPromptSubmit 擋下 ⇒ `{"type":"system","subtype":"informational","content":"UserPromptSubmit operation blocked by hook:\nRV_UPS_BLOCK_REASON\n\nOriginal prompt: RV_BLOCK_PROMPT hello","level":"warning","preventContinuation":true,"promptSubmitEnding":{"ending":{"kind":"blocked_by_hook","reason":"RV_UPS_BLOCK_REASON"},"promptKept":false}}`；`-p` 的 stdout 也印同一段文字，rc 0。
     - 另兩項實測事實：①沙盒中 CC 把 `CLAUDE_PROJECT_DIR` 設成沙盒根，repo 的 `_hook_launcher.py` 因此找不到目標腳本而 **fail-open 假綠**，沙盒 hook 必須用「venv 直譯器＋repo 腳本絕對路徑」直接 spawn；②`--debug hooks` 日誌的成功行格式是 `Hooks: <事件>:<matcher> [<命令>] finished with status 0 (<ms>)`，不是設計稿推測的 `Hook … success`（RV-L1 判準已改）。
3. **V-F1（冷窗轉送）＝C（備援）**，而且找到更根本的原因：`idleCompaction`（Claude Code 預設開）在對話大於 200,000 token、閒置約 1 小時、**快取過期之前**會自動壓縮，所以「大上下文＋快取已冷」這個條件在正常流程中幾乎不會成立。
4. **找到 4 個真缺陷（D）**，其中兩個有今天的實際證據：
   - **D-1** 快取冷熱判準看不到壓縮：`cachestate.py` 只看最後一筆帶 usage 的 assistant 記錄，沒看 `compact_boundary`。實際證據：sid `85bcbec8` 09:26:36 被閒置壓縮，20 分鐘後（09:46:35）UserPromptSubmit 還是判「快取已冷，建議改到新 session」（`hook_additional_context` 記錄）。
   - **D-2** 已交棒的舊視窗被閒置壓縮、而且行程一直活著：sid `742135ef` 11:16:00 封存、11:16:25 新視窗 ack；12:11:21 被閒置壓縮（上下文約 259k）；20:4x `sessionctl status` 還看得到「視窗行程 pid 8136 sid 742135ef」。
5. **「AutoClaude 自己驗不完＝BUG」的成因**：A 類目前沒有任何一個載具同時具備「真的 `claude -p` 子行程＋沙盒專案＋真 schtasks＋讀真逐字稿判定」。現有 19 支相關測試都是「hook 子行程＋人工合成的 payload／逐字稿」，屬於元件整合測試，不算 E2E。§4 設計最小可行自驗載具 `realverify`，§5 列逐功能 E2E 全覆蓋表，§6 列工作包。

---

## 1. 分類規則

| 類 | 定義 | 結案方式 |
|---|---|---|
| A | 本機可用真行程自己驗（真 `claude -p`、真 schtasks、真逐字稿重放、`--debug hooks` 日誌、`gh`、docker） | 寫進 `realverify` 案例或一次性指令；判準＝§2 寫的通過條件；結果寫進帳本 |
| B | 只能靠互動畫面看 | 先找機器可驗的替代證據（§0-2）；找到就把判準改成可機驗，殘留的「畫面有沒有畫出來」改列「掌舵者目視（非阻塞）」並寫 WHY |
| C | 正常流程結構上走不到／不在本機或本期範圍 | 改列「備援／另機／第二期」，寫明觸發條件與已有的自動測試覆蓋；不再算〔OI-20261120-017〕待驗主項 |
| D | 真缺陷（有暴露證據） | 給修法；守衛面依〈守衛面准入〉附暴露證據 |

---

## 2. 盤點表（獨立項目 54 項）

### 2.1 根 CLAUDE.md（3 處）

| # | 座標 | 項目 | 現狀 | 類 | 處置／判準 |
|---|---|---|---|---|---|
| 1 | CLAUDE.md:86 | 守衛總表 sessionctl 列：「互動畫面是否顯示 block 理由、真 spawn 新視窗是否讀到轉送檔」仍〔OI-20261120-017〕待目視 | 待目視 | B→機驗 | 改寫成：「block 理由以逐字稿 `hook_blocking_error`／`system informational` 記錄機驗（RV-C1、RV-F2）；畫面渲染＝掌舵者目視（非阻塞，2026-11-18 V-F2 已人眼對照一次）；轉送檔讀取＝備援路徑 RV-F1」 |
| 2 | CLAUDE.md:147 | 〔OI-20261120-017〕「Stop 的 systemMessage 與 TCS §3 V1～V8 仍待真機目視」 | 待目視 | B→機驗 | 改指向本檔 §5；V1～V8 逐條依 #8～#15 結案後刪掉這句 |
| 3 | CLAUDE.md:177 | 〔OI-20261120-017〕「轉送與告知的真機畫面顯示待掌舵者目視（V-F1）」 | 待目視 | C | 改寫成：「告知（V-F2）已驗；轉送（V-F1）＝備援路徑，只在『已封存未 spawn＋快取冷＋未被閒置壓縮』時觸發」 |

### 2.2 TCS-SessionCtl-20261113.md（3 處，展開成 V1～V8、V-W2～V-F2、AT-HV2-9）

| # | 座標 | 項目 | 類 | 通過判準（機驗） |
|---|---|---|---|---|
| 4 | :5 | R3 增量〔OI-20261120-017〕「§3b 待掌舵者目視」 | — | 隨 #16～#21 結案改寫 |
| 5 | :282 | AT-HV2-9 接續測驗四題（未實作） | A | RV-H5：沙盒 haiku 只讀交接包回答四題，四題答案用 regex 比對機械層事實（HEAD、未完成項、下一步指令、禁止事項），4/4 才算通過 |
| 6 | :309 | §3b 標題〔OI-20261120-017〕「待真機」 | — | 隨項目結案改寫 |
| 8 | §3 V1 | `sessionctl status` | A | 今天 20:4x 主控／本棒實跑 rc 0，列出代理與排程**名稱**，但**沒有印 NextRunTime 值**（判準要值）⇒ 先確認是不是要加 `--verify`；不是的話列 D-4 |
| 9 | §3 V2 | E2 重放 `--sentinel-tick` 隔離目錄 | A | RV-N4：痕跡 `sentinel_superseded`、無 `probed`、`Get-ScheduledTask` 查不到該名 |
| 10 | §3 V3 | 互動 handoff→finalize→spawn→ack | A | **事實上已驗多次**：`85bcbec8`→`742135ef`（`.sealed` 09:47:48、`.ack` 09:48:14）、`742135ef`→`89c354d9`（`.sealed` 11:16:00、`.ack` 11:16:25）。「新視窗 `$env:CLAUDECODE` 為空」判準本身有問題（Claude Code 行程內這個變數一定是 1；真正的風險是「巢狀 claude 拒絕啟動」，新逐字稿有產生就證明沒有發生）⇒ 判準改寫，重跑交給 RV-H3 |
| 11 | §3 V4 | 無人 SendMessage 續舊代理被擋 | A | RV-M1：`AUTOSDD_UNATTENDED=1 claude -p` 沙盒，逐字稿出現 PreToolUse SendMessage 的阻斷記錄（rc 2） |
| 12 | §3 V5 | Stop `systemMessage` 畫面看得到 | B→機驗 | 逐字稿 `hook_system_message`（Stop、sessionctl_guard）已有 114 筆 ⇒ 機驗通過；畫面＝掌舵者目視（非阻塞） |
| 13 | §3 V6 | `stop --window <假 sid>` | A | RV-T2：起一支命令列帶假 sid 的 `pwsh -NoExit` 會被砍、對照組不會 |
| 14 | §3 V7 | `--pace` 模型建議 | A | RV-T3：輸出有模型建議那行，數字跟 `--pace` 兩週軸一致 |
| 15 | §3 V8 | `claude -p --debug hooks` | A | RV-L1：日誌有 `Hook Stop.*success`，以及 SendMessage 觸發的 PreToolUse |
| 16 | §3b V-W2 | 監督閘推回／看管中 | B→機驗 | RV-S1／S2：逐字稿 `hook_blocking_error`（supervise）／`hook_system_message` 含「看管中」；歷史上已有 8 筆 sessionctl 的 `hook_blocking_error` |
| 17 | §3b V-W3 | watch 保溫點叫醒主控 | A（長案） | RV-W6：要真的閒置約 55 分鐘，只在 nightly 跑；判準是 `WATCH_VERDICT=keepwarm`，而且叫醒後第一個回合的 `cache_read ≥ 0.95×` 前一回合。**跟 idleCompaction 有交互**（閒置約 1 小時才會壓縮）：保溫點一定要早於這個時間，案例裡要斷言「保溫之前沒有 `compact_boundary`」 |
| 18 | §3b V-W4 | interim 卷 `meta.finished` | A | RV-W1 附帶記錄實值；斷言 all_done 不會提早成立 |
| 19 | §3b V-F1 | 冷窗轉送 | **C 備援** | 觸發條件：已封存 ∧ 還沒 spawn／ack ∧ 快取冷 ∧ 沒有被閒置壓縮。正常流程封存後會立刻 `--spawn`，走的是路徑二。自動覆蓋：`test_sessionctl_forward.py`、`test_def609_*`（含真實重放）；E2E 由 RV-F1 用沙盒逐字稿把時間往前推來驗。**依賴 D-1 修好**，不然冷熱判斷本身就是錯的 |
| 20 | §3b V-F2 | 已交棒告知 | ✅ 已驗 | 逐字稿 `7f29adfb` 00:29:59.753Z 記錄＋掌舵者貼回的畫面（`85bcbec8`:1186）逐字相同 ⇒ 直接關閉 |
| 21 | §3b V-HOOK | UserPromptSubmit 註冊 | （已驗） | 原文已寫「已驗」，不計入 |

### 2.3 TCS-SessionPark-20261116.md（5 處）

| # | 座標 | 項目 | 類 | 判準 |
|---|---|---|---|---|
| 22 | :4／:216 | 狀態行／章標題〔OI-20261120-017〕「待真機」 | — | 隨下列項目改寫 |
| 23 | :222 V-PK2 ③ | 新視窗 `CLAUDECODE` 為空 | A（判準改寫） | 同 #10：改成「新逐字稿有產生、SessionStart 有公告交接包」；11-16 那次 `ff1000ed` 已符合 |
| 24 | :222 V-PK2 ④ | Principal＝Interactive | A | RV-K1：排程註冊後、觸發前先 `(Get-ScheduledTask …).Principal.LogonType` 回讀 `Interactive` |
| 25 | :222 V-PK2 ⑥ | macOS launchd | C（另機） | 本機是 Windows，結構上走不到；改列「mac 另機 A」，用 `test_mac_endurance_r83.py` 的既有測試覆蓋 |
| 26 | :223 V-PK3 | 到點前舊視窗有人在動 ⇒ 跳過 | A | RV-K2：真 schtasks、到點前 2 分鐘時沙盒 session 用 `claude -p -r` 送一句話 ⇒ 痕跡 `handoff_spawn_skipped reason=live_driver`、job 自己拆掉 |
| 27 | :224 V-PK4 | Stop park 推回畫面可見 | B→機驗 | RV-K7：用 env 把 prepare 門檻調低 ⇒ 逐字稿 `hook_blocking_error` 內容含 `sessionctl.py park` |
| 28 | :225 V-PK5 | 上線 14 天後重跑基線 | A（到期日 2026-11-30） | 是時間閘、不是驗收閘：改列「排程觀察項」，到期時由 SI 巡邏或 nightly 自動跑 `waste_census --resume-metrics` |

### 2.4 TCS-TokenWaste-20261114.md（4 處）

| # | 座標 | 項目 | 類 | 判準 |
|---|---|---|---|---|
| 29 | :268 CR1 | 事故重放 | A | `waste_census --incident-sid` 重放：20:52 之後第一個 Stop 命中封存閘（RV-C3） |
| 30 | :281／:555 V-P1～V-P3 | 配速床擋派工、趕工戳記、熱讀 | A | RV-R1：用 env 調低允許線讓床開起來，接著 `claude -p` 沙盒連派 3 次 Agent ⇒ 第 3 次的 PreToolUse 阻斷含 `pace-floor`；`rush` 期間放行、到期後恢復擋 |
| 31 | :562～564 V-P4～V-P6 | burst 上界、無人 rush、回放 | A | 純指令：V-P4 `.env` 設 25 ⇒ 出聲並採用 20；V-P5 rc 2；V-P6 rc 0 |
| 32 | :566 V-K1～V-C4 | 第二期前置 | C（第二期） | 本期只登記；**V-K3 已由官方文件解答**（settings-reference `idleCompaction`：預設 true、門檻 200,000、閒置約 1 小時、可用 `CLAUDE_CODE_IDLE_COMPACT_MIN_TOKENS` 調整），改寫成已查證 |

### 2.5 ADR-XPLAT-004（11 處）

| # | 座標 | 項目 | 類 | 處置 |
|---|---|---|---|---|
| 33 | :524 | R3 落地狀態列「V-F1 待重測」 | C | 跟 #19 同 |
| 34 | :721 | 第二段〔OI-20261120-017〕「V1～V8 待真機目視」 | A/B | 跟 #8～#15 同 |
| 35 | :797 P3 | 互動與 `-p` 工具集是否一致 | A | RV-L2：兩邊逐字稿的 `deferred_tools_delta`／`agent_listing_delta` 附件做 diff |
| 36 | :799 P5 | idleCompaction 跟保溫的交互 | D（→D-1、D-2） | 官方文件已查證；實證見 §3 |
| 37 | :810 補5 | 快取讀取怎麼折算進額度 | C（研究題） | 不是驗收項：改列「研究題」，沒有掛任何閘門 |
| 38 | :814 | 文件未讀（idleCompaction／statusline） | A | idleCompaction 本棒已讀（見 #32）；statusline 頁由 WP-7 用 WebFetch 讀完回填 |
| 39 | :1055 | RDP 斷線情境 | C | 本機使用型態沒有 RDP；改列「情境外」 |
| 40 | :1060 | 真排程啟動時的 cwd | A | 11-16 那次 `ff1000ed` 逐字稿的 `cwd` 欄位可以直接回讀（WP-7 一行指令）；RV-K1 也會斷言 |
| 41 | :1062 | 同 #23～#26 | — | 同上 |
| 42 | :1132／:1133 | V-F1 第二步重測、V-W2 〔OI-20261120-017〕待目視 | C／B→機驗 | 同 #19、#16 |

### 2.6 帳本 AutoSDD_Defect_Log.md（fixed 但帶〔OI-20261120-017〕待驗尾巴，共 11 列）

| # | 列 | 尾巴 | 類 | 處置 |
|---|---|---|---|---|
| 43 | DEF-200-594（:367） | V-PK2 其他項〔OI-20261120-017〕待真機 | A | 隨 #23～#27 結案 |
| 44 | DEF-200-596（:369） | V-PK4 | B→機驗 | 隨 #27 |
| 45 | DEF-200-597（:370） | V-W3 | A | 隨 #17 |
| 46 | DEF-200-609（:382） | 待重測 | C | 前置排除邏輯已有 `test_def609_*` 真實重放；路徑本身是備援 ⇒ 狀態改成「fixed；E2E RV-F1」 |
| 47 | DEF-200-584（:357）／587（:360） | V1～V8／「真機項待主控」 | A/B | 隨 #8～#16 |
| 48 | DEF-200-593（:366） | CI 牆鐘待首次真跑 | A | `gh run list --workflow windows-compat-ci` 取分片後各 job 的牆鐘（< 60 分鐘、而且比 59 分鐘的基線短）。用 `ci_wait.py`，不要自己寫輪詢迴圈 |
| 49 | DEF-200-461（:234）／462（:235） | 「效果待量」／「TUI 人眼待」 | A／B→機驗 | 461：重跑 `tools/probe/misstep_attribution.py` 比對 R191 之後的命中；462：逐字稿 SessionStart 的 `hook_system_message` 有安裝提示 ⇒ 機驗 |
| 50 | DEF-200-266／267（:166／:167） | 「工作樹待收尾 commit」 | A | 這是過時的文字：`git log -S` 確認修法已經在 HEAD，改寫狀態欄（不是〔OI-20261120-017〕待驗） |

（DEF-200-313、419、458 的「待」字分別是：已移出外部軌結案、修法說明文字、closed-by-decision 的重開條件 ⇒ 都不是〔OI-20261120-017〕待驗，不計入。）

### 2.7 其他文件（6 處）

| # | 座標 | 項目 | 類 | 判準 |
|---|---|---|---|---|
| 51 | AutoClaude_Token_…PRD_v2.1.md:2715 | `AutoResumeService._wait` 拒絕長睡後交給排程器 | A | AutoClaude 側：真 schtasks、睡眠秒數設短的整合案例（WP-7） |
| 52 | SelfImproving_PRD.md:1430 V-P7-2 | Docker Desktop 對 `os.replace` 後新檔的可見性 | A | `docker run -v` 唯讀 bind；主機 `os.replace` 之後容器 `cat` 讀到新內容 |
| 53 | CrossPlatform_R213…W4.md:38 | §4.5.2 自標〔OI-20261120-017〕待真機 | A | WP-7 讀該節再定；先列為 A |
| 54 | CrossPlatform_R68…:52 | Windows smoke 新 step 沒在 Windows 實跑 | A | 本機就是 Windows：`powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/windows_smoke_local.ps1`，rc 0＋該 step 有 PASS |
| 55 | RTM-SelfImproving-P6:5 | AT-645-4-1 巡邏自動入帳路徑 | A | SI 巡邏每天都在跑：查事件帳本有沒有巡邏寫入的對應事件（seq 151～155 已經有巡邏寫入，需比對 AT 斷言） |
| 56 | SessionCtl_Defect_Evidence:50／:68 | V1～V8；SEC-4／5／8／9／10／11／12 | A／C | SEC-4 `taskkill /T` 殘留 ppid、SEC-5 行程名、SEC-8 `washed_env`、SEC-10 跨 session 代理 id ⇒ A（WP-7 沙盒實測）；SEC-9、SEC-12 沒有暴露證據 ⇒ C（理論洞清單）；SEC-11 ⇒ 主控代決：無人模式下 GUARD_OFF 可以關屬於設計取捨（逃生口要在啟動 claude 前設、模型碰不到），寫 WHY 結案 |
| 57 | WakeChain_IronLaws_Verification.md:98 | M-19 `Get-ScheduledTask` 解析沒在真 Windows 實測 | A | 本機實跑 M-19 對應測試（不 skip），貼出 rc |

（表號 7 跳過、#21 原文已驗不計；扣掉重複引用列〔#4、#6、#22、#41〕後 #1～#57 共 51 項，加 §2.8 三項＝54。主類：B＝#1、2、12、16、27、44、S1、S2；C＝#3、19、25、32、33、37、39、42、46；D＝#36（→D-1、D-2）、R1（→D-3）；D-4 出自 #8；✅＝#20；其餘為 A。）

### 2.8 SI 與殘局

| # | 項目 | 現狀 | 類 | 處置 |
|---|---|---|---|---|
| S1 | ATT-SI-004（seq 38，link：OBS-SI-340 重開 OBS-SI-016） | 沒有 settle | B（治理） | `attr.confirm`／`reject` 的 `by` 必須**不是**提出者（`fold.py:161` CONFIRMER-IS-PROPOSER）。兩筆的提出者都是「主控」⇒ 需要掌舵者或獨立審查者確認。內容是 MEMORY 索引反覆溢位這條重開鏈（016→340→367），而 367 已經由 PROP-SI-006／007 處理 ⇒ 建議 confirm |
| S2 | ATT-SI-005（seq 52，link：OBS-SI-367 重開 OBS-SI-340） | 同上 | B（治理） | 同上 |
| R1 | 殘局代理 `a51fe52e56c8ed299`（P7 重釘儀式，擁有者 `7ba13bb7`，最後 2026-11-17 22:24） | 名冊永遠列著 | D-3 | 見 §3 |

---

## 3. 缺陷（D）與修法

| 編號 | 暴露證據（非構造） | 成因 | 最小修法 | 守衛面 |
|---|---|---|---|---|
| **D-1** 快取冷熱判準看不到壓縮 | `85bcbec8.jsonl`：01:26:36Z `Compacted while idle`（第 1259 行）→ 01:46:35Z UserPromptSubmit `hook_additional_context`「建議改到新 session（快取已冷）」 | `cachestate.cache_state` 只拿最後一筆帶 usage 的 assistant 記錄計時；壓縮請求不會留下 assistant usage。上下文大小也是用壓縮前的值 ⇒ 會判成「又大又冷」 | 尾段掃描時，如果最後一筆 usage 之後還有 `type=system, subtype=compact_boundary` ⇒ 回傳 `compacted_after=True`，上下文改用壓縮之後的值（拿不到就當成小）；`forward` 路徑一、SendMessage 冷熱閘、`switch` R1 都把「壓縮之後」視為「不需要換 session」。回歸：拿 `85bcbec8` 那段做真實重放 | 是（`tools/lib/sessionctl/**`），證據如左 |
| **D-2** 已交棒的舊視窗沒關、被閒置壓縮 | `742135ef.jsonl`：最後一次活動 03:16:26Z、`.ack` 03:16:25Z、04:11:20Z `compact_boundary`、04:11:21Z `Compacted while idle`（壓縮前上下文約 259k）；20:4x `sessionctl status`「視窗行程：pid 8136 sid 742135ef」 | spawn／ack 之後沒有任何東西會去關舊視窗；idleCompaction 照樣對它花一次壓縮請求，壓縮完還會再跑 SessionStart:compact hooks | **ack 時順便收掉舊視窗**：新 session `handoff --ack` 成功之後，找到舊 sid 的視窗行程（用 `procstop` 既有的身分驗證：命令列含舊 sid、是 claude 行程），而且舊逐字稿最後一筆是回合結束（`turn_duration`／`stop_hook_summary`）、閒置 ≥ 60 秒，才送關閉；驗不到身分就只出聲、不砍。逃生口：`AUTOSDD_SESSION_SWITCH_MODE=notify`。**否決** 專案層 `idleCompaction:false`：它對正在用的長 session 是省錢的（人離開超過 1 小時回來，只要送摘要，不用整份冷重寫）；關掉會讓冷重寫的情況變多 | 是，證據如左 |
| **D-3** 殘局記錄永遠留在名冊 | 今天 `sessionctl status` 還列著 `a51fe52e56c8ed299`（擁有者行程已經不在、記錄停在昨天 22:24） | `roster.py` 的 residue 沒有壽命上限，也沒有確認收尾的動作 | 殘局超過 `ROSTER_RESIDUE_TTL_HOURS`（建議 24）就不列在預設名冊（`status --all` 仍可看）；收尾前先確認該代理的成品已經在 HEAD（P7 重釘 → 查 7ba13bb7 那輪的 commit） | 是；證據＝今天的 status 輸出 |
| **D-4**（待確認） V1 status 沒印 NextRunTime | 今天的 status 只印排程名稱 | 判準要「值」（取證規則：憑證是 NextRunTime 這個值） | 先確認 `status` 是否設計成只有 `--verify` 才查排程器；如果是，就把 TCS V1 判準改成 `status --verify`；如果不是，就在 status 補印值 | 視確認結果 |

---

## 4. 自驗載具設計：`realverify`

### 4.1 為什麼 A 類一直沒有被自動驗
- 現有測試（`test_sessionctl_hooks.py:227` 等）是把 hook 當子行程起來、餵**合成的** payload 跟逐字稿；真 schtasks 只在 park 的 `FakeRunner` 之外沒有人碰；`test_sentinel_tick_e2e_r145.py` 跑的是真的 tick 但用假排程器。
- 沒有任何東西會：①起真的 `claude -p`（真的 harness、真的 hook 接線、真的逐字稿格式）；②註冊／觸發／回讀真 schtasks 並保證清掉；③從真逐字稿裡斷言 `hook_blocking_error`／`hook_system_message`／`compact_boundary` 這類記錄。所以每個 V 項都只能等主控或掌舵者手動做——**這就是「AutoClaude 自己驗不完」的結構性成因**，算 BUG（立案為 DEF-200-612：缺真機自驗載具（原建議號 611 已被壓縮冷熱缺陷佔用））。

### 4.2 落點（依 Root_Layout §2）

| 內容 | 落點 |
|---|---|
| 函式庫 | `tools/lib/realverify/`：`sandbox.py`（在 scratch 建一個 repo 外的專案目錄＋git init＋`.claude/settings.json`，hook 條目用絕對路徑指回本 repo 的 `_hook_launcher`）、`driver.py`（`claude -p --model haiku [-r sid]`，帶 env 覆寫、牆鐘上限、`--debug hooks --debug-file`）、`transcript.py`（找沙盒 slug 下的逐字稿，提供 `has_blocking_error(hook=…)`、`has_system_message(...)`、`has_compact_boundary_after(...)` 等斷言）、`sched.py`（`AutoSDD_RV_*` 前綴、try/finally 一定清掉、回讀 NextRunTime／Principal）、`cases/<family>.py`（各案例包，**自動發現**，免得多包搶同一個登記檔）、`ledger.py` |
| 入口 | `tools/realverify.py run --case <id>|--family <f>|--all [--long]`，末行 `REALVERIFY_VERDICT=pass|fail n=… fail=[…]` |
| 測試 | `tools/tests/test_realverify_lib.py`（只測函式庫判準，用假逐字稿；**不算 E2E**） |
| 帳本 | `docs/06_quality/RealVerify_Result_Ledger.md`（每次執行一列：案例、rc、逐字稿座標、時間戳） |
| 協定資料 | `docs/06_quality/RealVerify_Protocol/cases.json`（案例 id → 對應的 V／AT／DEF，給盤點表反查） |

### 4.3 設計約束
- **隔離**：沙盒專案在 repo 外 ⇒ 不會載入根 CLAUDE.md，token 成本低；逐字稿落在另一個 slug，不會污染主 slug 的名冊與普查。🔴 交接包目錄（`~/.autosdd/handoff`）跟痕跡目錄要能指到沙盒：痕跡有 `AUTOSDD_TRACE_DIR`；交接包目錄**是否有 env 出口要現查**，沒有的話得補一個只能「縮到沙盒」的出口（守衛面，暴露證據＝本次掌舵者指令下 A 類無法自驗的事實；這點我最不確定，見回報）。
- **不偽造**：時間類條件（快取冷、閒置）一律用「改寫沙盒自己逐字稿的時間戳」或 env 下修門檻來做，不改守衛判準本身；長等案例（保溫 55 分鐘、真 reset）標 `--long`，只在 nightly 跑。
- **清理**：每個案例都要 `finally` 拆掉 `AutoSDD_RV_*` 排程、殺掉沙盒開出來的視窗（procstop 身分驗證）、刪掉沙盒目錄；收尾時現查 `Get-ScheduledTask AutoSDD_RV_*` 必須是 0。
- **閘門位置**：CI 沒有 Claude 認證 ⇒ 不進 CI；接進 `run_local_nightly.ps1` 新 stage＋手動 `realverify run`。失敗要寫進帳本，**不能**靜默 skip（沒有 `claude` 執行檔 ⇒ rc 非 0，不是 skip）。
- **成本**：haiku、沙盒沒有 CLAUDE.md；每支案例預估約 2～4 萬 token，全套（不含 `--long`）約 40 支。派工前照樣查 `--pace`。

---

## 5. E2E 測試案例全覆蓋表（sessionctl＋哨兵續航；單元測試／hook 子行程合成測試都不算 E2E）

「現有 E2E」欄只認真行程＋真逐字稿；只有 hook 子行程＋合成 payload 的寫「無（僅整合）」。

| 功能 | 現有 E2E | 現有最接近的自動測試 | 缺口 → 案例 | WP |
|---|---|---|---|---|
| handoff `--build` | 無（僅整合） | `test_sessionctl_handoff.py:1036` 入口逐動詞跑 | RV-H1：沙盒 `claude -p` 產生真逐字稿 → build → 機械層含真 HEAD／真提示 | WP-2 |
| `--finalize`（seal） | 無（真實使用有痕跡，但不可重跑） | `test_sessionctl_seal.py` | RV-H2：主控層缺節 ⇒ rc≠0 而且沒有 `.sealed`；補齊 ⇒ 產生 `.sealed`＋`.prompts.md` | WP-2 |
| `--spawn` | 無可重跑案例（真實：`85bcbec8`→`742135ef`→`89c354d9`） | `test_sessionctl_handoff.py:1009` | RV-H3：真的開互動視窗 `claude "<prompt>"` → 新 slug 逐字稿出現、SessionStart 公告交接包 → procstop 收掉 | WP-2 |
| `--ack` | 同上 | handoff 測試 | RV-H4：新視窗 ack ⇒ 有 `.ack`；再開一窗不再公告；（D-2 修好後）舊視窗被收掉 | WP-2 |
| 交接包足以接續（AT-HV2-9） | 無 | 無 | RV-H5（#5） | WP-2 |
| forward 路徑一（冷窗轉送，備援） | 無（09:46 真機 FAIL→已修） | `test_sessionctl_forward.py`、`test_def609_*` | RV-F1：已封存未 spawn、沙盒逐字稿時間往前推 > 1h、沒有壓縮 ⇒ `-r` 送一句 ⇒ 被擋、有原文檔、新視窗開出；另一個變體是有 `compact_boundary` ⇒ 不轉送（D-1） | WP-2 |
| forward 路徑二（已交棒告知） | ✅ 真機 1 次（`7f29adfb` 00:29:59Z） | forward 測試 | RV-F2：沙盒已 ack ⇒ `claude -p -r` 送一句 ⇒ 被擋、有原文檔（變成可重跑） | WP-2 |
| `留：` 前綴放行 | 無 | forward 測試 | RV-F3 | WP-2 |
| converge 封存閘（Stop） | 無（真實觸發有 8 筆 sessionctl `hook_blocking_error`，但不可重跑） | `test_sessionctl_converge.py`、`HookConvergeTest` | RV-C1：env 把 R1 調到很低 ⇒ 逐字稿有 `hook_blocking_error` 而且內容含 `--finalize`；第二次 Stop 放行 | WP-2 |
| 冷叫醒閘 | 無 | converge 測試 | RV-C2：已封存＋背景 shell 還在跑 ⇒ 推回、要求 TaskStop | WP-2 |
| 事故重放 CR1 | 無 | TokenWaste AT | RV-C3（#29） | WP-2 |
| supervise 監督閘 | 無 | `test_sessionctl_supervise.py` | RV-S1：有背景代理、沒掛 watch ⇒ 推回；RV-S2：掛了 watch ⇒ `hook_system_message` 含「看管中」 | WP-3 |
| watch `all_done`(0) | 無 | `test_sessionctl_watch.py` | RV-W1：沙盒裡真的背景代理交卷 ⇒ `WATCH_VERDICT=all_done`，記錄 `meta.finished` 實值（V-W4） | WP-3 |
| watch `overrun`(2) | 無 | 同上 | RV-W2：單支逾時門檻用參數調低 | WP-3 |
| watch `stall`(3) | 無 | 同上 | RV-W3：`--stall-min 1`、代理停住 | WP-3 |
| watch `budget`(4) | 無 | 同上 | RV-W4：單支上下文門檻用 env 調低 | WP-3 |
| watch `quota`(5) | 無 | 同上 | RV-W5：prepare 門檻用 env 調低 | WP-3 |
| watch `keepwarm`(6) | 無 | 同上 | RV-W6（`--long`，V-W3，斷言保溫之前沒有被壓縮） | WP-3 |
| SendMessage 冷熱閘 | 無 | `test_sessionctl_cachegate.py`、`ResumeGateFunctionTest` | RV-M1：無人模式 ⇒ rc 2；RV-M1b：互動＋冷＋上下文大 ⇒ 擋；訊息帶 `續棒理由：` ⇒ 放行 | WP-3 |
| 硬門檻擋派工（PreToolUse Agent） | 無 | converge 測試 | RV-M2 | WP-3 |
| check_pending_handoff 散文交棒 | 無（真實 8 筆 `hook_blocking_error`） | `test_check_pending_handoff.py` | RV-P1：要 haiku 照字面輸出一段交棒句 ⇒ 被推回一次、第二次放行 | WP-3 |
| 半路停工（midwork） | 無 | `test_check_pending_handoff.py` | RV-P2：沙盒 git 有未提交的修改＋輸出進行式句子＋沒有背景任務 ⇒ 推回；帶 `park` 標記的句子 ⇒ 放行 | WP-3 |
| park（armed＋fire） | ✅ 真機 1 次（11-16 `f2260ce7`→`ff1000ed`，不可重跑） | `test_sessionctl_park.py`（FakeRunner） | RV-K1：真 schtasks `--at +3min` ⇒ NextRunTime 值、Principal＝Interactive、到點開出新逐字稿、job 自己拆、cwd 正確 | WP-4 |
| park 跳過（有人在動） | 無 | park 測試 | RV-K2（V-PK3） | WP-4 |
| park `--done`／`--cancel`／`--why`／`--at` | 無 | park 測試 | RV-K3～K6：各自檢查憑證檔與排程器狀態（cancel ⇒ `Get-ScheduledTask` 查不到） | WP-4 |
| park Stop 推回 | 無 | `HookParkTest` | RV-K7（V-PK4） | WP-4 |
| rush／配速床 | 無 | `test_quota_rush.py`、`test_quota_pace_floor.py` | RV-R1（V-P1～P3）、RV-R2（V-P4～P6） | WP-4 |
| `status` | 無（今天手動跑過） | roster 測試 | RV-T1：沙盒有代理、排程 ⇒ 都列出來，排程帶 NextRunTime 值（D-4） | WP-4 |
| `stop --window` | 無 | roster／procstop 測試 | RV-T2（V6） | WP-4 |
| `--pace` 模型建議 | 無 | `test_sessionctl_modelmix.py` | RV-T3（V7） | WP-4 |
| 哨兵 arm | 無（真實使用：`AutoSDD_Sentinel_89c354d9…` 存在） | `test_context_budget_guard.py::SentinelWiringTest` | RV-N1：`--arm-sentinel` 綁沙盒 sid ⇒ NextRunTime 值；拆掉後查不到 | WP-4 |
| 哨兵 patrol tick | 半（`test_sentinel_tick_e2e_r145.py` 真 tick、假排程器） | 同左 | RV-N2：真 tick＋真逐字稿（沒有撞線）⇒ patrol、不 spawn | WP-4 |
| 哨兵 resume（撞線後續跑） | 無 | `test_sessionctl_switch.py`、`test_resume_cost.py` | RV-N3：沙盒逐字稿植入撞線記錄、reset 時刻設在過去 ⇒ tick 走 resume、真的 `claude -p -r` 開出 | WP-4 |
| 哨兵自我解除（superseded） | 無 | `test_sessionctl_switch.py:328` | RV-N4（V2） | WP-4 |
| 哨兵讓路 park | 無 | park 測試 | RV-N5：park armed ⇒ tick 一律 patrol | WP-4 |
| hook 活性 | 半（`check_hooks_liveness.py` 出聲層） | `test_check_hooks_liveness.py` | RV-L1（V8）、RV-L2（#35 互動 vs `-p` 工具集） | WP-1 |

合計 40 支案例（其中 `--long` 1 支：RV-W6）。

---

## 6. SD 工作包

| WP | 內容 | 要動的檔 | 測試／通過判準 | 鎖持有面 | 可並行 |
|---|---|---|---|---|---|
| **WP-1** realverify 核心 | §4 函式庫＋入口＋帳本＋協定資料；RV-L1／L2 當冒煙案例 | `tools/lib/realverify/*`、`tools/realverify.py`、`tools/tests/test_realverify_lib.py`、Root_Layout §2 登記列、根 CLAUDE.md 速查表一列、compat-ci `paths` | `realverify run --family hooks` 回 rc 0、帳本寫入一列；收尾 `Get-ScheduledTask AutoSDD_RV_*`＝0 | Root_Layout SSOT、`_TREE_FILE_FLOORS`／onboarding 基線（新測試檔） | 跟 WP-5、WP-7 並行 |
| **WP-5** 缺陷修復 D-1→D-2→D-3（＋D-4 確認） | D-1 `cachestate.py`＋`forward.py`／`switch.py` 消費端；D-2 `handoff.py`（ack）＋`procstop.py`；D-3 `roster.py`；新增回歸用既有測試檔（不新增檔） | `tools/lib/sessionctl/{cachestate,forward,switch,handoff,procstop,roster}.py`、`test_sessionctl_{cachegate,forward,handoff,roster}.py`、ADR-XPLAT-004 §2.18、TCS-SessionCtl | D-1 用 `85bcbec8` 真實重放：修前判冷、修後判「壓縮之後」；D-2 用 `742135ef` 時序重放＋身分驗證不到 ⇒ 不砍；突變轉紅 | `tools/lib/sessionctl/**`（守衛面）——**三項串行、同一棒** | 跟 WP-1、WP-7 並行（檔案不重疊） |
| **WP-2** 案例：handoff／seal／spawn／ack／forward／converge | `tools/lib/realverify/cases/sessionctl_handoff.py`、`cases/sessionctl_forward.py`、`cases/sessionctl_converge.py` | 同左 | RV-H1～H5、F1～F3、C1～C3 全部 pass | 只動自己的 cases 檔（自動發現） | 依賴 WP-1＋WP-5；跟 WP-3、WP-4 並行 |
| **WP-3** 案例：supervise／watch／SendMessage／派工擋／pending_handoff／midwork | `cases/sessionctl_watch.py`、`cases/sessionctl_gates.py`、`cases/pending_handoff.py` | 同左 | RV-S1～S2、W1～W6、M1～M2、P1～P2 | 同上 | 跟 WP-2、WP-4 並行 |
| **WP-4** 案例：park／rush／status／stop／pace／哨兵 | `cases/sessionctl_park.py`、`cases/quota_rush.py`、`cases/sessionctl_status.py`、`cases/sentinel.py` | 同左 | RV-K1～K7、R1～R2、T1～T3、N1～N5；真 schtasks 一律 `AutoSDD_RV_` 前綴 | 同上；**真 schtasks 案例彼此串行**（同一個排程器命名空間），由 runner 鎖控制 | 跟 WP-2、WP-3 並行 |
| **WP-7** 非 sessionctl 的 A 項一次性驗證 | #48 CI 牆鐘、#49 misstep、#50 `git log -S`、#51 AutoResumeService、#52 docker、#53 R213 §4.5.2、#54 windows smoke、#55 RTM P6、#56 SEC-4／5／8／10、#57 M-19、#38 statusline 文件、#40 cwd 回讀 | 不改程式；只產證據到 scratchpad | 每項附指令＋rc＋輸出座標 | 無（唯讀＋執行） | 跟 WP-1、WP-5 並行 |
| **WP-6** 收尾單人窗口 | 依 WP-2～4、7 的結果改寫 #1～#57 全部座標的文字（〔OI-20261120-017〕待驗 → 已驗／備援／非阻塞目視）；缺陷帳本 11 列狀態欄、立案 DEF-200-612（缺自驗載具）＋D-1～D-4；SI S1／S2 由掌舵者或獨立審查者 `attr.confirm`；殘局 R1 收尾；測試棘輪重釘；nightly 接上 realverify stage | CLAUDE.md、TCS×3、ADR、帳本、`run_local_nightly.ps1` | `check_defect_log_crossref.py` 未結 0，而且全 repo Grep「待真機\|待重測\|待目視\|待掌舵者目視\|仍待真機」只剩明寫「掌舵者目視（非阻塞）」或「備援」的列 | 三本帳、棘輪重釘、CLAUDE.md（鐵律七：只能單窗） | 不並行，最後做 |

**派工順序**：第一波並行 {WP-1、WP-5、WP-7} → 主控親驗 → 第二波並行 {WP-2、WP-3、WP-4}（真 schtasks 案例由 runner 串行）→ WP-6 收尾單人窗口。

---

## 6b. 主控親驗與裁決（2026-11-18 21:0x，sid 89c354d9；本節優先於上文）

1. **D-2 原修法否決（證據誤讀）**：主控親跑 `Get-CimInstance Win32_Process -Filter "ProcessId=8136"` ⇒ `claude.exe`，命令列＝`claude "按交接包繼續：讀 …742135ef…_20261118T031511Z.md …"`，且本主控 shell 祖先鏈 `3700:pwsh <- 8624:cmd <- 8136:claude` ⇒ **pid 8136 是 742135ef 交棒開出的「新」視窗（＝sid 89c354d9 本身）**，不是舊視窗；舊視窗 742135ef 已於 19:47 由掌舵者關閉。「命令列含舊 sid」判準會命中新視窗（新視窗的開場提示就含舊交接包路徑），照原修法做會**殺掉新視窗**。⇒ D-2 改為兩件：
   - **D-2a（status 標示誤導）**：`sessionctl status` 的「視窗行程：pid 8136 sid 742135ef」把**新視窗 pid** 掛在**來源 sid** 旁，連 Architect 都誤讀。改成「新視窗 pid 8136（由 742135ef 交棒開出；舊視窗不在此列）」這類不會誤讀的字樣；暴露證據＝本次誤讀本身（非構造）。
   - **D-2b（舊視窗沒關會被閒置壓縮）**：不自動砍任何視窗。`--spawn` 成功的輸出末行與 `--ack` 成功輸出加一句「舊視窗可以關閉（不關會被 Claude Code 閒置壓縮，多花一次請求）」。
2. **交接包目錄不加 env 出口**：沙盒 session 的 sid 天生唯一，交接包／封存／ack 檔都以 sid 命名 ⇒ realverify 直接用真目錄 `~/.autosdd/handoff`，每個案例 `finally` 依沙盒 sid 精確刪除自己產生的檔（只刪檔名以沙盒 sid 開頭者）。不動守衛面、不需暴露證據。痕跡照用 `AUTOSDD_TRACE_DIR` 指到沙盒。
3. **RV-L2 是第二波的前置**：WP-1 必須先用真 `claude -p` 實證 Stop block／UserPromptSubmit block 在 `-p` 逐字稿的記錄格式；格式與互動模式不同時，B→機驗的判準改用 `-p` 實際格式，並把差異寫回本檔 §0-2。
4. **D-4**：WP-5 先讀 `tools/lib/sessionctl/roster.py`／`sessionctl.py status` 實作確認；`--verify` 才查排程器屬設計者，改 TCS V1 判準為 `status --verify`（WP-6 改文字）；否則補印值。

5. **WP-5 親驗（主控 21:0x）**：`unittest -p "test_sessionctl_*.py"` rc 0；`ruff` rc 0；`sessionctl status` 實印「交棒開出的新視窗：pid 8136（來源 742135ef）」。D-4 結論＝設計如此（status 唯讀零外呼，NextRunTime 由 `park --status --verify`／`--verify-schtasks` 查）⇒ WP-6 把 TCS V1 判準改為這兩條。
6. **WP-7 親驗**：報告存 `docs/06_quality/CrossPlatform_R215_WP7_OneShot_Evidence.md`（原始輸出在主控 scratchpad wp7\，會隨重開機消失，報告為準）。主控現查殘留 `AutoSDD_EngineResume*`／`AutoSDD_RV_*` 排程＝0、smoke `PASS=13 FAIL=0`。**SEC-10 改判 C（理論洞清單）**：需兩個互動 session 互打 agent id，屬 harness 行為、無暴露證據（守衛面准入）。WP-6 另改兩處過時文字：帳本 :166／:167「工作樹待收尾 commit」（修法 b1ef81f5／bfb07cf1 已在 HEAD）、RTM-SelfImproving-P6 檔頭〔OI-20261120-017〕「AT-645-4-1 仍待真機觸發」（表內已 ✅ seq 98／99）。#51 AutoResumeService 只驗到排程觸發與自拆（engine 用壞 yaml 免耗 token）⇒ 第二波 RV 案例補「engine 真跑出結果」一支。

## 7. 不確定處（交棒前請主控親驗）

1. 交接包目錄有沒有 env 出口可以指到沙盒（沒有的話 WP-1 會碰到守衛面，暴露證據只能拿「本次 A 類無法自驗」來論證，可能不符〈守衛面准入〉三種證據裡的任何一種）。
2. D-2「ack 時收掉舊視窗」對掌舵者來說是不是可以接受（舊視窗的捲動紀錄會消失；逐字稿還在，可以 `claude -r`）。替代方案只有「只出聲提示關窗」。
3. `claude -p` 裡 Stop `decision:block` 以及 UserPromptSubmit 擋下的記錄格式，是否跟互動模式一樣（`hook_blocking_error`／`system informational`）——本棒只看到互動模式的實例；RV-L2 要先驗這件事，B→機驗的換算才站得住。

## R216 收尾：DEF-200-611～615 詳情（缺陷帳本列只留索引，長文住此）

- **DEF-200-611（快取冷熱與上下文看不見壓縮；真機 V-F1 第二步後續）**：壓縮請求本身重寫快取，閒置壓縮後逐字稿最後一筆 assistant usage 已是壓縮前，`cachestate`／`roster` 因此把剛被砍到 1～2 萬的 session 當成大上下文＋熱快取。修法與座標見 ADR-XPLAT-004 §2.18.6（D-1～D-4）。同批：交棒後新視窗加「舊視窗可以關閉」提醒（不自動關窗，命令列辨識會命中新視窗）。
- **DEF-200-612（缺真機自驗載具）**：本檔 §0 的結構性成因（沒有東西能起真 `claude -p`、真 schtasks、讀真逐字稿斷言）。立案號原建議 611，已被上列缺陷佔用，改 612。修法＝`tools/realverify.py`＋`tools/lib/realverify/`（沙盒在 repo 外、排程前綴 `AutoSDD_RV_`、全域鎖串行、必清、回讀 NextRunTime）；R216 收尾補修三點：排程載具改走 `quiet_python()`（驗證載具不得在桌面畫 console 視窗，`test_check_hooks_liveness` 的排程 Action 判準）；Windows 專屬的行程驗證／收窗函式加 `os.name` 守衛（非 Windows 一律環境缺件 rc 2，不假綠）；全部案例 id 登記進 `RealVerify_Protocol/cases.json`。
- **DEF-200-613（watch 額度條件一掛上就觸發）**：短窗原始讀數在 prepare 帶時 `quota_hit_now()` 每次輪詢皆成立 ⇒ `sessionctl watch` 一掛即 `WATCH_VERDICT=quota rc=5`；處置表要求「代理快完成 ⇒ 重掛」但重掛必再觸發（主控 2026-11-18 21:26 `watch1.log` 與重掛 `bd116c583` 兩次實證）。修法＝閂鎖（設計 `SessionSwitch_CostModel_Design.md` §4.3）：鍵 `(sid, reset 分鐘, 帶級)`，同窗同帶只觸發一次、帶升級或 reset 改變再觸發、閂鎖讀寫失敗照觸發並 stderr 出聲；否決 `--ack-quota`（旗標無到期、帶旗標會吞掉升級到 halt）。
- **DEF-200-614（reset 抖動閂鎖誤判）**：RealVerify 真機實證——watch 00:48 讀到 reset 04:00:00、00:54 讀到 03:59:00，額度快取的 reset 在分鐘邊界來回 ±1 分，字串比對把它誤判成新窗而再度 rc 5。修法 `keepwarm._same_reset`：字面相同或差 ≤300 秒視為同窗（帶級升級照樣再觸發）；回歸 `test_reset_jitter_across_a_minute_boundary_is_the_same_window`。
- **DEF-200-615（監督憑證字面子字串比對落空）**：`supervise._main_proof` 以字面 `sessionctl.py watch` 比對 background_tasks 命令；PowerShell 形態命令是 `& 'py' 'C:\..\sessionctl.py' watch`（腳本路徑後帶引號），比不到 ⇒ 憑證誤判為無（RealVerify `sessionctl_watch` 修復前 fail n=7：RV-S2／W4／W5）。為 ADR-XPLAT-004 §2.18.3 登記的理論洞 P6H F5 的真機實例。修法＝`_WATCH_CMD_RE`（容忍腳本路徑後的引號與空白）取代字面比對，並刪除已無使用方的 `WATCH_CMD_MARK` 常數；回歸 `test_main_proof_recognises_quoted_script_path`；案例 `RV-W5` 改用沙盒專屬額度快取、沙盒 env 設 `AUTOSDD_KEEPWARM_OFF=1`（保溫閘與 watch 族驗證目標正交，另由 keepwarm 族驗）。