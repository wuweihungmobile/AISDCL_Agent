# 五問覆核審計協定（判準②′ 的審計錨；輪不變模板）

用途：把「每輪四方覆核怎麼做」凍結成可雜湊的模板，讓「近 6 輪窗口」有一個不會被悄悄改動的分母。
判準②′ 的提案全文見 `docs/06_quality/CrossPlatform_R191_FiveQuestion_Verification_Evidence.md`〈八〉
（「判準②′ 修憲」），採納經過見 `docs/06_quality/CrossPlatform_R192_FiveQuestion_Convergence_Evidence.md`
〈八〉；量測由 `tools/probe/audit_session.py` 執行（只印不擋）。

## 目錄
- `charter_{arch,sa,sd,qa}.md`：四個角色的章程（角色、審查面、輸出格式）；事實一律用槽位。
- `discipline.md`：共同紀律（工具上限、唯讀、rc 不接管線、鐵律四、回傳格式、判決規則、Windows 形態）。
- `severity.md`：嚴重度口徑、家族登記制、拆殘判法。
- `probes/PA|PB|PC.txt`：活體探針三型 prompt 逐字（`<n>`／`<scratchpad>`／`<shell_read>` 與 `{{ROUND}}` 為槽位；`<shell_read>`＝執行機合法的 shell 讀檔式——Mac／Linux 填「Bash 的 cat」、Windows 填「PowerShell 的 Get-Content」。探針 prompt 不得要求執行機上被鐵律禁用的工具：Windows 的 Bash 會被鐵律一 hook 正確擋下，而 Q1′c 分子含正確攔截，每支這樣的探針就自帶一次命中）。
- `params.json`：②′ 全部判準常數都住這裡（本段點名的鍵集合與該檔逐字相等，有測試釘住）：
  - 數值：`q1b_min_n`（Q1′b 的最小母體，不足印 NOT-EVALUABLE，不再對 0／0 印 PASS）、`q1c_gate`／
    `q1c_n`（Q1′c 取最近幾支；取到每輪 1～3 支真實 session 的窗口內可達）／`q1c_first_calls`（Q1′c 看前幾個
    呼叫；與 `q2_max_index`／`claim_max_uses` 同寬，早期的阻斷才看得到）、`claim_max_uses`（Q1′b 只計前幾個
    呼叫內的宣稱）、`claim_lookback`（宣稱往回看幾個 tool_result 找阻斷）、`q2_max_index`／`q2_min_n`、
    `q3_n`／`q3_min_pairs`／`q3_tolerance_tokens`、`q3_quiescent_seconds`（Q3′ 只納入靜止配對：feed 與
    逐字稿最後 usage 較晚者已過這麼多秒；在途視窗的逐字稿落盤落後 feed 一則，不靜止者排除並印
    NOT-QUIESCENT）、`q4_max_age_days`（Q4′ 證據新鮮度）、`rounds_required`。
  - 句型（正則是 JSON 字串，反斜線雙寫）：`claim_re`／`claim_exc_re`／`quote_re`（宣稱、排除、引述）、
    `planner_re`、`feed_read_re`（Q2′ 認列的唯讀現查退路：Read context feed 或額度快取檔）。
  - 工具集：`converge_tools`（收斂型工具）、`parity_non_shell_tools`（`--parity` 逐支崩塌判準不計入的
    非 shell 內建工具；此前寫死在量測器碼裡）。
  - 收斂判定 v2（R197 起；見〈窗口規則與收斂判定〉）：`symptom_baseline_since`（症狀基線時刻＝DEF-200-481
    lint 精準化落地 commit 89dcb35 的 committer 時刻；凍結於雜湊、不得隨輪滑動）、`symptom_streak_required`
    （連續幾次評估達標才宣告收斂）、`exposure_min_hits`（真實語料非探針種子最少命中筆數，低於此＝理論洞 P4）。
  - 🔴 **量測器碼不入 manifest，判準常數全部住 `params.json`**：改任何判準數字或句型＝改本檔＝重置窗口；
    碼裡不得再寫死判準常數（定義漂移不重置窗口，正是這條規定要堵的洞）。

## 事實槽位（不入雜湊）
`{{ROUND}}` 輪號、`{{HEAD}}` 起算 commit、`{{DATE}}` 日期、`{{PREV_ROUND}}` 上輪結論指標。
每輪任務書＝本目錄模板＋槽位填值；填值只住當輪任務書，不寫進本目錄。

## 雜湊規則
manifest＝本目錄每個檔的（相對路徑, sha256(內容；CRLF 先正規化為 LF)），依路徑排序；
`protocol_sha256`＝sha256(`json.dumps(manifest, ensure_ascii=False)`)。算法在 `audit_session.py --protocol-status`
（實作住 `tools/probe/fivequestion_ledger.py`），結果登記在輪帳本 `FiveQuestion_Round_Ledger.jsonl`
（append-only，每輪一列）。

## 窗口規則與收斂判定（R197 起＝評估式 v2：症狀閘為主、家族計數為資訊欄）
`window_len`＝輪帳本尾端連續同 `protocol_sha256` 的列數（遇 `window_reset:true` 即止）。

**收斂＝症狀閘達標**，每輪由主控親跑下列三項（兩條量測指令＋一條狀態指令）、逐字貼進證據檔（`--exclude-self`；
基線＝`params.json` 的 `symptom_baseline_since`，值由該檔現查、以**原字串**代入、不抄進本檔——PowerShell 的
`ConvertFrom-Json` 會把 ISO 字串轉成 DateTime 而丟掉格式，`--record-since` 直接 traceback rc=1；用 Read／`Select-String` 取字串）：
1. `python tools/probe/audit_session.py --five-question --exclude-self --record-since <symptom_baseline_since> --entrypoint cli,claude-vscode,sdk-cli`
   → Q1′a（修法後 MISBLOCK 0）、Q1′b（裸宣稱 0）、Q1′c（≤ `q1c_gate`）、Q3′（全對 ≤ `q3_tolerance_tokens`）四行皆 PASS
   （合併真實層與探針層：探針是真實 headless session，開窗行為同屬症狀面；NOT-EVALUABLE＝量不到、不算達標）。Q1′c 量的是「新窗前 `q1c_first_calls` 個呼叫有沒有被 hook 擋」——分子**含正確攔截**（誤擋另由 Q1′a 量），視窗＝母體最近 `q1c_n` 支；故探針不得要求執行機禁用的工具（見〈目錄〉`<shell_read>`），否則 3 支 PB／PC 即可把 0/10 推到 2/10、章程 9 支即自造 FAIL。
2. 同指令**不帶** `--entrypoint`（真實層 cli／claude-vscode）→ Q2′ 行 PASS（n ≥ `q2_min_n`、逾期 0；探針被告知先現查，
   不得混入分母；分母只含 ≥ `q2_max_index` 個工具呼叫的 session，呼叫數不足的窗不入分母也不入 n）。
3. `python tools/probe/audit_session.py --protocol-status`（`fivequestion_ledger.py` 是函式庫，直接執行無輸出、rc=0）
   的 Q4′ **兩平台（win32 與 darwin 各一行）**九格 ✓ 且 ≤ `q4_max_age_days`：它只讀本機 `trace_dir` 的丙案 JSON，另一台的
   `session_gate_acceptance_*.json` 須先拷入本機 `trace_dir`（缺檔＝量不到＝不達標；工具不會標出缺哪台，只印一行＝未達標；**過期 JSON 印 FAIL 而非量不到**，依計次規則會把 `symptom_streak` 歸零 ⇒ 評估機跑指令 3 前先確認兩份 JSON 皆在效期內，過期者先重產／重攜回）；
   `verify_hint` 兩格量的是 Windows 專屬提示字樣是否出現在產出機簡報，win32 須在、darwin 須不在（兩平台期望值相反）；
   該指令印的「評估:」行是家族計數資訊欄，不是收斂依據。
機器範圍（跨機輪次）：三項的母體皆為**執行機本機**——逐字稿＝本機 `claude_home()/projects/<本機 repo 路徑 slug>`、Q3′ feed＝
本機 `context_feed`、Q4′＝本機 `trace_dir`；他機的真實窗與 feed 都不在母體，三條指令照上列字面跑（`--exclude-self`／`--record-since`／`--entrypoint` 是字面的一部分），不得再加 `--project-dir`／`--exclude-sid` 等改變母體的旗標。
評估機＝掌舵者症狀回報機（現＝Windows；改指定須掌舵者明示並重置協定）。他機輪次照跑三項，結果以
`[他機:<host>] PASS|FAIL|NOT-EVALUABLE（母體 N 支）` 寫入該列 `note`、不計次、`symptom_streak` 沿用上一列——含 FAIL：他機輪次的 FAIL 只入 `note`、不歸零。
計次只在評估機輪次：三項同時成立＝一次評估達標 ⇒ `symptom_streak`＝上值 +1；評估機輪次任一行 FAIL ⇒ 寫 0（HUMAN-REVIEW＝Q1′b 有裸宣稱：逐句人工複核，句前真無阻斷＝該行 FAIL、正則假陽（引述／轉述／否定）＝註明後視為 PASS，複核句逐字入證據檔）；
NOT-EVALUABLE ⇒ 沿用上值（不得用來蓋掉壞樣本：評估機母體數不得低於該機上次評估，保留期清理例外須證據檔明載）；
相鄰兩次達標相距不得超過 `q4_max_age_days` 天（宣告前的計次連續性規則；宣告後不再數 streak）。連續 `symptom_streak_required` 次評估（不同輪、後一次母體含 ≥1 支
評估機新真實窗）達標 ⇒ 宣告收斂，宣告範圍＝評估機行為面＋兩平台 Q4′ 靜態九格、他機行為面標「未驗」；之後只在下列
再評觸發 S1～S6 成立時再評。達標次數寫在輪帳本列 `symptom_streak` 欄（`--protocol-status` 照印）。

**收斂宣告後的再評觸發（唯一真相源＝本節；根 CLAUDE.md〈守衛面准入〉只引用、不複寫）**：只由症狀、或守衛面／權限姿態的實際變更驅動：下列任一成立才開一輪再評；沒有任何日曆、版本號或證據效期觸發，退役後也沒有任何自動排程的再評（S1～S6 由掌舵者或主控看到時啟動）。
- S1 掌舵者真機回報症狀（附 session id 或畫面原文（`severity.md`〈暴露度〉(a)））。
- S2（原 T2）評估機上任一量測器紅：指令 1～3 任一行 FAIL（含 HUMAN-REVIEW 複核後判 FAIL）（NOT-EVALUABLE 不算；Q4′ 僅因 `generated_at` 過期而 ✗ 不算——過期是再評輪的開場步驟、不是症狀；他機輪次的 FAIL 只入 `note`，其中 Q4′ 兩平台行非因過期的 ✗ 由主控在 `note` 裁定是否視同本條）。
- S3（原 T5）主控視窗的前 `q1c_first_calls` 個呼叫內出現誤擋（oracle 判 misblock）、分類器拒絕或權限詢問；hook 正確攔截不算。
- S4（原 T4）任何一輪出現 P≤2，或「宣稱被擋而前面沒有真阻斷」。
- S5（原 T1 反轉）守衛面有變動，且該變動附有暴露證據（暴露證據的定義在根 CLAUDE.md〈守衛面准入〉）。
- S6（原 T6）權限姿態或 `permissions` 內容變更。
明文退役（原 R196 證據檔〈八〉的 T3／T7／兜底，不得再當觸發）：Claude Code 版本變更、Q4′ 證據逼近 `q4_max_age_days` 天、「連續 3 個降頻輪或距上次完整四方 14 天必開一輪」。
宣告一經作成，`symptom_streak` 歸零或協定重置（`window_reset`）皆不撤回；撤回須掌舵者明示並記入輪帳本 `note`。
WHY：時間型觸發在沒有任何症狀時也會開輪，是再評永遠做不完的永動機——R205 因 Claude Code 2.1.290→2.1.291 再評、三項量測全 PASS、無退化，而 2026-10-07 實測已是 2.1.292，同一條件又成立；版本變更若真改了權限姿態由 S6 接住、若真造成症狀由 S1／S3 接住，不必拿版本號當代理指標（決策檔 `docs/06_quality/CrossPlatform_R207_FiveQuestion_Retire_Time_Triggers_Decision.md`）。

Q4′ 攜回：產出機把 `session_gate_acceptance_<host>.json` 原文逐字貼進當輪證據檔附錄（不得手改、JSON 為純 ASCII）；
另一台以**同檔名**存入本機 `trace_dir`，且本機 HEAD 已含其 `repo_head`（先 pull）後再跑指令 3；效期自 `generated_at` 起
`q4_max_age_days` 天；過期**不構成日曆義務**，只在再評輪開場檢查，過期者該輪開場先重產／攜回。獨立憑證：Q1′a 的 oracle 與 hook 同碼、
對修法後視窗是同義反覆（ARCH-195-06）⇒ 另附 Q1′b、掌舵者回報、答案表兩引擎重測；分類器拒絕
（`automode-blocked`）不入分子但逐筆歸因。全史（不帶 `--record-since`）數字受 Claude Code 逐字稿保留期影響、隨時間
縮水（同一指令同一 HEAD 7 分鐘內母體 38→36 曾實測發生），證據檔引用時必附量測時刻與母體數；收斂判定只用基線切片。

家族計數（舊評估式：window_len ≥ `rounds_required`、近 6 輪 `new_p_le2` 合計 ≤ 2、`p1` = 0、末輪 0；
`--protocol-status` 照印 PASS／FAIL／NOT-EVALUABLE）**自 R197 起降為資訊欄，不再是收斂宣告的依據**。
WHY：它的分子是審查對「每輪都在擴張的守衛面」做對抗搜尋的產出——無不動點、雙向可操作（多查漲、少查歸零）、
與掌舵者症狀無量值對應；R179～R196 守衛面淨增 10,139 行、發現率約 0.8 P2／輪，連 4 輪零新的機率約 4%
（R197 證據檔〈三〉Architect 列；〈四〉為根因敘述）。量測器 rc 恆 0，不得接閘門。

## 更動＝重置，不是紅燈
改本目錄任一檔（含一個字）→ `--protocol-status` 印 `PROTOCOL-CHANGED`；須追加新列帶
`window_reset:true`＋理由，窗口自該列重數。不得無聲換協定，也不必為了換協定而假裝沒換。
完整性閘（`new_p_le2`／`excluded_p_le2` 必須涵蓋窗口內所有 P1／P2 列）見 `severity.md`；
`--protocol-status` 會印出該檢查的結果（`完整性閘 ✓`／`✗ 漏列：…`，rc 恆 0）。
