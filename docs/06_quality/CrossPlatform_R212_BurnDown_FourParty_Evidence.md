# CrossPlatform R212 第五列證據檔：清倉模式（BURN-DOWN）T4 落地 ＋ 四方完備性獨立審查

> 本檔是帳本級治理文件（登記於 `tools/lib/governance_docs.py`）：承載 DEF-200-528 的暴露證據、主控設計裁決（BD-2′）、Dev 與四面鏡的逐字判決。R212 時鐘不前進（同輪第五列）。

## 〈一〉掌舵者原文（T1 第七次貼同一份＋兩則新增指令）與本列範圍

- T1 原文（2026-10-12，與前六次相同的四問）：「1.請徹底完成以上任務，找到沒法完成收斂的根因，徹底解決？請想盡所有辦法完成收斂任務！ 2.完成實作AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md裡面所有功能！==> 請檢視驗證每個功能都已經完成 E to E 全功能驗證！ 3.如何將兩邊的 .env同步，哪邊才是正確完整的？這個參數檔該如何維護？ 幫我設計自動同步機制！==> 下次在Windows執行時，幫我自動同步！請進行驗證功能是否ＯＫ？ 4.需要馬上切到Windows執行及開發嗎？」＋「派出Architect / SA / SD / QA 四方專家獨立審查,請確認以上功能都已經完備！」
- 授權句（T1 原文末段逐字）：「以上若需要我決策，請依照最佳化, 最理想, 最適當的解決方案，我授權幫我決策, 若真需要我決定, 請以最簡單的解釋, 讓我互動選項決策」——〈二-2〉主控代決的依據在此。
- 新增指令（同 sid `ed1c9022-22cc-4974-a8b3-9d4ebfa5f6bd`，視窗中途兩則，逐字）：「這次請儘量使用，我還有一次Token reset的用量」／「我還有一次週Token reset用量，所以儘量使用！」
- 本列範圍：(a) 上述新增指令＝PRD §16.2「施工圖 A4：R108 BurnDown 增補（擬 §4.2.9 清倉模式）」列的再開症狀實際發生（§16.5 (iii)，T4）⇒ 立 DEF-200-528、落地清倉模式；(b) 四方（Architect／SA／SD／QA，Sonnet 唯讀鏡）獨立審查「前六次響應宣稱的完備性」與本列的清倉變更；(c) T1（掌舵者新指令）與 T4（A4 症狀）同時成立；沿用 R212 第一至四列的 R 系列形態（證據檔＋缺陷帳本入口），不開軌道① 計畫書、不產四件套（範本〈🏁〉：T1 最小響應＝直接做事＋commit，碰守衛面故四方）；護欄棘輪重釘標籤前進到 R213 屬範本〈證據檔命名與護欄棘輪〉路徑 (c)，到期義務（`_REPIN_NET_CAP_DUE_ROUND`＝214）尚未觸發，檔名鐘（`current_round()`）仍＝R212（詳〈三-2〉）。

## 〈二〉T4 立案：暴露證據與主控設計裁決

### 二-1 暴露證據（`severity.md`〈暴露度〉(a)：掌舵者真機回報 sid＋畫面字樣）

主控於同視窗第二個工具呼叫親跑 `python tools/session_resume_planner.py --pace`（2026-10-12 18:16 +08:00 量測，來源＝cache），逐字：

```text
現在可派 1 個 agent（硬上限 cap=1，本視窗已用 0 次）｜band=prepare｜最緊的一條＝five_hour 8% 剩 233 分鐘
  kind=session 8% 剩 233 分鐘 band=prepare horizon=far cap=1 note=amortized；kind=weekly_all 75% 剩 7663 分鐘 band=converge horizon=far cap=2 note=burn-ahead；kind=weekly_scoped 41% 剩 7663 分鐘 band=free horizon=far cap=None model=Fable note=burn-ahead；kind=five_hour 8% 剩 233 分鐘 band=prepare horizon=far cap=1 note=amortized；kind=seven_day 75% 剩 7663 分鐘 band=converge horizon=far cap=2 note=burn-ahead；kind=spend 0% reset 距離不明 band=free horizon=none cap=None note=missing　⇒ cap=1 recommended=1 band=prepare binding=five_hour reason=ok,amortized,burn-ahead,gate_excluded=spend,missing
  攤提：kind=weekly_all 剩 25pp／距 reset 7663 分鐘 ÷ 25.5 個 kind=session 窗 = 每窗 0.98pp ×r=5.0（n=67 ⇒ 取中位數）⇒ 本窗配額 4.9pp；kind=session 已用 8pp 剩 233 分鐘 ⇒ 本窗餘裕 -3.1pp
```

對照 A4 列再開症狀「掌舵者下清倉指令（明示要用掉將作廢的額度）而 `--pace` 仍把派工壓在 cap≤2」：指令在（兩則逐字，真實互動窗逐字稿第 173／210 行〔SA 鏡核對〕）、cap=1 在、sid 在 ⇒ 命中。時序歸屬如實：`--pace` 畫面為主控自跑、**先於**掌舵者兩則指令約 3 分鐘（18:16 量測 vs 指令 18:19／18:20），同一快取 TTL 窗內水位未變〔推論〕；暴露證據的主體＝掌舵者指令＋sid，畫面是同窗的機械讀數，不是掌舵者回報的畫面。擋住清倉的是**跨窗攤提**（five_hour／session 原始 8%＝free 帶，被攤提抬成 prepare 帶），與 `PRD_Amendment_R108_BurnDown_Addendum.md` §2.3 的 2026-08-28 立案實測同為「短窗被跨窗攤提抬帶」；差別在供給軸：當時是 `weekly_scoped`（BD-2′ 治不到，現行碼誠實 inert〔SA 鏡以 08-28 讀數合成實跑〕），本次是被點名的 `weekly_all`（BD-2′ 治得到）。

### 二-2 主控設計裁決（掌舵者 T1 授權「依最佳化代決」；可隨時以 §16.5 (i) 推翻）

附錄（Adopted，v2.1.10）§4.1／§4.2 自陳：被點名的週軸與 binding 的短窗軸不同窗 ⇒ 短窗軸不 qualifying，且 BD-2 的結構守門要求攤提供給軸也 qualifying ⇒ 對立案情境「入憲了但治不到」；QB6 尾句要求的「跨窗點名（含短窗軸）」增補提案迄今無檔。本列裁決＝**BD-2′ 跨窗攤提暫停**：

- Q-same（附錄原文不動）：被點名軸、與其 `resets_at` 字串全等且在 cap gate 的鄰軸；合取底線①②③與「距 reset 解得出且 ≥0」。享 BD-1（horizon 乘數地板 1.0，不送加速）與 BD-2。
- Q-cross（本列增補，只給 BD-2′；**以碼為準的定義**，Dev 落地時取主控原寫法的超集並自報）：進 cap gate 的短窗軸，且本次攤提 `Amort.total_kind` **的軸是 Q-same**（被點名軸本身 Q-same 成立；`total_kind` 恰為被點名軸或其同窗鄰軸皆成立——避免同窗平手時因 axes 順序靜默不觸發）⇒ 該短窗軸餵給 `pct_band` 的水位改用原始 pct。不享 BD-1。底線①②③同樣合取。WHY：攤提存在的唯一目的是保護長窗軸；掌舵者點名那條長窗軸清倉＝明示解除該保護；不放寬任何沒被點名、不同窗、或非短窗供給關係的軸。
- 補述（SA 鏡 C3／C4）：BD-2 的 `hold` 遮罩對所有合格軸成立，但只在 `window == Amort.rate_window` 的短窗軸生效，Q-same 長窗軸實際只享 BD-1；落款為單槽（同窗第二則不同軸指令覆寫前一份）；標題 cap 經 `quota_stability` 遲滯逐階爬升（先 2、每 ≥300 秒 +1）；附錄 §7.2 的 `BURNDOWN_CAP_CEILING` 未交付（上限直接取 `cap_notice`）。
- 夾層（QB1）：`ceil = cap_notice`，逐軸、min 聚合之前；原 cap None 的格不動；非 qualifying 軸逐格不動；聚合律／must-finish／model_hint 一字不改（底線④ 建構順序）。
- 載體（QB3）：落款檔（六欄）住 `trace_dir()`；唯一寫入口 CLI；`AUTOSDD_QUOTA_BURNDOWN_OFF` 只准關；明文不具防偽性質。
- 四條底線①～④（附錄 §5）全部保留為 qualifying 合取項或建構順序。

## 〈三〉實作與主控親驗

### 三-1 Dev-1（Sonnet，一包）交件摘要〔他包回報；報告全文＝scratchpad `dev1_burndown_report.md`，不入庫〕

- 改動面（`git status --short` 逐字，Dev 交件時）：`A tools/lib/quota_burndown.py`（356 行；落款檔／`verdict`／`active`／`Burn.masks`＋`apply`／CLI `--issue`／`--status`／`--revoke`／決策事件 `log_decision`）、`M tools/lib/quota_policy.py`（`decide(burndown=)`／`axes_of(relax=)`）、`M tools/lib/quota_pace.py`（`band_inputs(hold=)`／`resolve(floor=)`）、`M tools/lib/quota_gate.py`（`pace_report` 與 `quota_gate()` 兩個真實派工呼叫端接落款；`record_burn(…, bd)`）、`M tools/lib/quota_messages.py`（`pace_line` 清倉段）、`M tools/lib/quota_policy_env.py`（`AUTOSDD_QUOTA_BURNDOWN_OFF` escape 類）、`M .env.example`（重生）、`A tools/tests/test_quota_burndown.py`（Dev-1 交件 295 行、14 支；修復包後 297 行、13 支：BD-1～BD-9＋BD-2′＋CLI 三臂＋接電，每條有主斷言並就地重現錯誤版判準作對照）、`M tools/tests/test_adr_xplat001_c1c2_lock.py`（棘輪重釘，見三-2）、`M tools/tests/test_run_root_unittests.py`（已知寫端集合加本檔，0 淨行）。
- Dev 與主控任務書的四處出入（Dev 自報，主控採納）：(a) `decide(` 真實派工呼叫端＝`quota_gate.py` 的 `pace_report`／`quota_gate()`，任務書點名的 `:517` 是 `draining()`、`quota_messages.py:164` 是 halted 短路——刻意不接（halt 帶底線①）；(b) `bd_effect`（relaxed／inert）不進 `row_of()`（`record_burn` 先於 `decide`，搬動會改換算比＝改不下令時的輸出），改由 `<trace_dir>/autosdd_burndown_events.jsonl` 承載（每次授權在場的 `--pace` 決策一列；hook 熱路徑不落檔）；`row_of()` 加 `bd` 欄；(c) Q-cross 守門取「`Amort.total_kind` 的軸是 Q-same」＝主控寫法的超集（相等時逐字相同；避免被點名軸與供給軸同窗平手時因 axes 順序靜默不觸發）；(d) 放寬後 cap 仍過 `quota_stability`（PRD §4.2.4 (c)(d)：增加方向每次 +1、≥300 秒），故第一次 `--pace` 標題 cap 1→2，之後每 ≥5 分鐘再 +1 至軸值 4；「現在可派」＝min(rec, cap−live)，本案 rec＝`cap_prepare`，標題數字封頂 2（**不是放到 8**）。(e)〔Architect 鏡 P3-09〕附錄 §7.2 草案鍵 `BURNDOWN_CAP_CEILING` 未做：上限直接取 `Policy.cap_notice`（可由 `AUTOSDD_QUOTA_CAP_NOTICE` 間接調小，但會同時改 notice 帶本身）。(f)〔Architect 鏡 P3-13〕事件檔 `autosdd_burndown_events.jsonl` 的 cap／rec 是 `decide()` 原值（穩定化前）；修復包改欄名 `decided_cap`／`decided_rec`。(g)〔QA 鏡突變 B31〕`--issue` 接受逾 TTL 的快取＝刻意：`resets_at` 在視窗內不變；reset 之後舊 `until` 已在過去 ⇒ 落款立即失效（fail-closed）；修復包加一句警示。(h)〔SD 鏡 P3-4、QA 鏡 P3-6(c)〕Dev 自報「每條帶合成注入紅面」措辭過強：每條有主斷言並就地重現錯誤版判準作對照，但數行「紅面」是對政策常數的恆真算術；修復包以真斷言等量換掉。
- Dev 自跑閘門（rc 逐字見其報告 §5）：quota 四模組 `Ran 400 tests … OK`（基線 386＋14）；AutoClaude 契約側四檔 259 項通過；`check_loc_budget --json` 四類違規皆 `[]`；`ruff check tools/` rc=0；`check_pytest_baseline_sites`／`check_defect_log_crossref`／`check_handoff_carriers`／`check_ntfs_paths` 皆 rc=0；根層全套第四輪（最終樹）rc=1：5352 個測試、5 紅＝`TestGuardLayerRatchet` 五支，同一原因「`guard-total:R213` 標記行在 docs 掃描面 0 份」（Dev 禁碰 docs）。

### 三-2 護欄棘輪：標籤拍板＝R213（主控裁決）

- 算式（Dev-1 報告 §0-1；數字為 Dev-1 交件時，修復包後最終值見下）：`_REPIN_NET_CAP_SCHEDULE` 的 R212 上限 516；R212 已有三列（+739／−24／+81）＝+796，扣回歸鎖軌 309（軌上限，已申報滿）＝主軌 487，餘裕 29 行；新測試檔最小可行約 300 行 ⇒ 以 R212 標籤追加必觸發款(10)。鎖自己列的三個出口：①同輪搬約 290 行史料（候選 47 段、849 行，需逐段人判）；②改記在新標籤名下（鎖原文語意）；③`_REPIN_APPROVED_ROUND_OVERAGE` 一次性例外（名冊 `MAX_ENTRIES=4` 已滿，上修須四方核准）。**裁決＝②**：以 `R213` 標籤重釘。WHY：②是鎖自己寫明的出口且成本最低；①的人工判斷成本與誤刪史料風險高於它省下的行數；③要先改鎖的上限＝砸溫度計。
- 兩個鐘不混：重釘日誌的輪標籤（`live_repin_round()`）前進到 213；R 系列檔名鐘（`current_round()`）仍＝R212（本列證據檔沿用 R212 前綴、不建 R213 檔）。標籤到期義務（`_REPIN_NET_CAP_DUE_ROUND=214`／Phase-2）由鎖自己在到期時喚醒，本列不預作。〔三鏡記載補強〕後果如實寫出：(i) 本列把 R213 標籤下的回歸鎖軌 309 用掉 308（餘 1 行）——之後任何以 R213 標籤記帳的 tools/tests 成長都要靠淨減抵銷；(ii) Architect 鏡唯讀印出 `live_repin_round=213`、`_PHASE2_DUE_ROUND=213`、`DUE_ROUND=214`：R213 是最後一個未觸發到期義務的標籤，以 R214 為標籤的重釘將同時觸發 Phase-2 追列與上限 516→515；(iii) 單一真實輪（檔名鐘 R212）內 tools/tests 淨額合計 +796＋308＝+1104、「標籤即帳戶」的形態登〈七〉P4；(iv) 鎖列理由欄的預告式字樣由修復包改為事實句。
- 逐檔清單（款(9) 指名本檔為家；**修復包後最終值**）：`tools/tests/test_quota_burndown.py` 0→297（新；Dev-1 交件 295）；`tools/tests/test_context_budget_guard.py` 14923→14924（+1＝幽靈鍵鎖 consumers 元組加 `quota_burndown.py`）；`tools/tests/test_adr_xplat001_c1c2_lock.py` 8579→8589（+10＝本列、回歸鎖軌同輪列、接鏈列）；其餘 `tools/tests/test_*.py` 0 變動。總量 116429→116737（+308；Dev-1 交件時 +305）；`_REGRESSION_LANE_LOG` 新列 `("R213", 308, …)`（≤ 軌上限 309，**餘 1 行**）；主−軌＝0（款(11) 不計連升）；`_REPIN_LOG_FROZEN_PREFIX_LEN` 338→339；`_REPIN_LOG_HISTORY_SHA256` `c72c9866f024…`；`_FROZEN_PREFIX_REWRITE_LEDGER` 接鏈列 `("R213","cff55af4647d","c72c9866f024","DEF-200-528")`。`<!-- guard-total:R213 -->` 兩站＝`docs/04_planning/AutoSDD_improving_112.md`（R212 標記下一行）與 `docs/06_quality/CrossPlatform_R145_Scan_Findings.md`（同）——沿用 R212 兩站，主控補寫。🔴 任何包之後再動 `tools/tests` ⇒ 收尾單人窗口重跑 `--print-guard-lines` 重釘並重算兩站標記行。

### 三-3 主控親驗（真落款；sid `ed1c9022-22cc-4974-a8b3-9d4ebfa5f6bd`，2026-10-12 19:34 +08:00）

`python tools/lib/quota_burndown.py --status`（下令前，rc=1）：

```text
清倉授權：沒有有效落款
  ✗ 落款檔存在且六欄齊全
載體不具防偽性質：落款只讓事後可稽核、偽造可對帳、失效可偵測，不代表「已驗證是人下的令」。
```

`python tools/lib/quota_burndown.py --issue weekly_all --directive "我還有一次週Token reset用量，所以儘量使用！"`（rc=0）：

```text
已落款 45c49b8e35：kind=weekly_all 作用至 reset 2026-10-17T17:59:59.540762+00:00（距今 7585 分鐘）；檔案 /Users/wuweihong/.autosdd/traces/autosdd_burndown_directive.json
載體不具防偽性質：落款只讓事後可稽核、偽造可對帳、失效可偵測，不代表「已驗證是人下的令」。
```

`python tools/session_resume_planner.py --pace`（下令後，rc=0；對照〈二-1〉下令前的 `cap=1 band=prepare binding=five_hour`）：

```text
session 來源＝環境變數 CLAUDE_CODE_SESSION_ID（sid=ed1c9022-22cc-4974-a8b3-9d4ebfa5f6bd）
現在可派 2 個 agent（硬上限 cap=2，本視窗已用 0 次）｜band=converge｜最緊的一條＝seven_day 78% 剩 7585 分鐘｜🔥清倉模式生效中（落款 45c49b8e35，發令 2026-10-12T19:34:11.353965+08:00，作用至 kind=weekly_all reset 2026-10-17T17:59:59.540762+00:00；效期剩 7585 分鐘／must-finish 門檻 5 分鐘）⇒ 本次放寬：kind=session band prepare→free cap 1→8 rec 1→4、kind=weekly_all cap 2→4 rec 1→2、kind=five_hour band prepare→free cap 1→8 rec 1→4、kind=seven_day cap 2→4 rec 1→2；未放寬：kind=weekly_scoped（model-scoped 不納入）、kind=spend（fallback 不納入）
  kind=session 29% 剩 155 分鐘 band=free horizon=far cap=8；kind=weekly_all 78% 剩 7585 分鐘 band=converge horizon=mid cap=4 note=burn-ahead；kind=weekly_scoped 44% 剩 7585 分鐘 band=free horizon=far cap=None model=Fable note=burn-ahead；kind=five_hour 29% 剩 155 分鐘 band=free horizon=far cap=8；kind=seven_day 78% 剩 7585 分鐘 band=converge horizon=mid cap=4 note=burn-ahead；kind=spend 0% reset 距離不明 band=free horizon=none cap=None note=missing　⇒ cap=2 recommended=2 band=converge binding=seven_day reason=ok,burn-ahead,gate_excluded=spend,missing｜🔥清倉模式生效中（落款 45c49b8e35，發令 2026-10-12T19:34:11.353965+08:00，作用至 kind=weekly_all reset 2026-10-17T17:59:59.540762+00:00；效期剩 7585 分鐘／must-finish 門檻 5 分鐘）⇒ 本次放寬：kind=session band prepare→free cap 1→8 rec 1→4、kind=weekly_all cap 2→4 rec 1→2、kind=five_hour band prepare→free cap 1→8 rec 1→4、kind=seven_day cap 2→4 rec 1→2；未放寬：kind=weekly_scoped（model-scoped 不納入）、kind=spend（fallback 不納入）
  攤提：kind=weekly_all 剩 22pp／距 reset 7585 分鐘 ÷ 25.3 個 kind=session 窗 = 每窗 0.87pp ×r=5.0（n=67 ⇒ 取中位數）⇒ 本窗配額 4.4pp；kind=session 已用 29pp 剩 155 分鐘 ⇒ 本窗餘裕 -24.6pp；短窗自軸 pace_index=0.60（≤1＝短窗自身未超線性；分母是短窗流逝比，與本窗餘裕不同軸、不可互抵）
  派工前置：方案指紋=five_hour+session+seven_day+spend+weekly_all+weekly_scoped｜此帳號**沒有** usage credits ⇒ 訂閱窗本身即硬牆
   ⏱ 扇出視窗：300s 內帳上 0 筆 ⇒ **視窗全空**，現在派不必等
   ⏳ 目前 cap=2 由遲滯維持（這條軸自己的 cap 是 4）：各軸水位不變的話，每個最小停留時間（出廠 300 秒，可由 env.shared 或 .env 調）最多放寬 1 階，不是要等到那條軸的 reset。
   🔻 降級建議：kind=seven_day,weekly_all 已進收緊帶 ⇒ 建議派工帶 model: sonnet/haiku 續跑（只建議不自動改模型；cap 不受本行影響）。
   🤖 模型角色（env.shared／.env AUTOSDD_MODEL_*）：主控=fable｜子代理=sonnet｜降級=haiku（主控值只管無人喚醒窗口；互動視窗自己的模型 env.shared／.env 管不到，派工請明寫 model:）
  來源=cache 量測於=2026-10-12T19:32:54+08:00
```

`python tools/lib/quota_burndown.py --status`（下令後，rc=0）：

```text
清倉授權：落款 45c49b8e35（發令 2026-10-12T19:34:11.353965+08:00；kind=weekly_all 作用至 reset 2026-10-17T17:59:59.540762+00:00）
指令逐字：我還有一次週Token reset用量，所以儘量使用！
  ✓ 落款檔存在且六欄齊全
  ✓ AUTOSDD_QUOTA_BURNDOWN_OFF 未設
  ✓ 被點名軸不是 fallback／model-scoped（底線②③，QB4）
  ✓ 方案指紋與落款相同
  ✓ 被點名軸仍在本次讀數
  ✓ now < until_resets_at（解得出且未過期）
  🔥清倉模式生效中（落款 45c49b8e35，發令 2026-10-12T19:34:11.353965+08:00，作用至 kind=weekly_all reset 2026-10-17T17:59:59.540762+00:00；效期剩 7585 分鐘／must-finish 門檻 5 分鐘）⇒ 本次放寬：kind=session band prepare→free cap 1→8 rec 1→4、kind=weekly_all cap 2→4 rec 1→2、kind=five_hour band prepare→free cap 1→8 rec 1→4、kind=seven_day cap 2→4 rec 1→2；未放寬：kind=weekly_scoped（model-scoped 不納入）、kind=spend（fallback 不納入）
載體不具防偽性質：落款只讓事後可稽核、偽造可對帳、失效可偵測，不代表「已驗證是人下的令」。
```

判讀：(1) 下令前的 `--pace`（〈二-1〉，18:16 讀數：週 75%／短窗 8%）與下令後（19:34 讀數：78%／29%）**不是同一組讀數**；同讀數反事實由兩鏡各自以落款檔 `readings_at_issue` 重算〔他包回報：Architect 鏡〈五〉E6、QA 鏡〈一-D〉〕：無授權 ⇒ `cap=1 rec=1 band=prepare binding=five_hour`（note=amortized）；有授權 ⇒ `cap=4 rec=2 binding=seven_day`（與事件檔 19:34:35 列 cap=4 rec=2 相符）。在此之上，`--pace` 標題由 cap=1 變為 cap=2（遲滯維持；週軸自身 cap＝`cap_converge`＝4）、binding 由 five_hour 轉 seven_day、band 由 prepare 轉 converge，短窗軸 band prepare→free、原 cap 1→8（夾層 `cap_notice`）、週軸 cap 2→4（BD-1 收回 far 減速）；model-scoped（weekly_scoped）與 fallback（spend）逐格不動並被點名「未放寬」——與附錄 §4.4 值域表**本次讀數涉及的格**及〈二-2〉裁決相符（§4.4 表 horizon `none` 四列依附錄 §4.1「距 reset 解得出且 ≥0」不放寬、與表值不同＝附錄內部不一致，碼取 §4.1〔SA 鏡〕）。(2) 主控觀察到的措辭問題：清倉段在 `pace_line` 標題行與 `describe()` 行各印一次（同一字串重複）；四鏡皆判 P3，修復包 C1 處置。(2′)〔SA 鏡 P3-1 必改〕**效果帶**：授權只在被點名軸低於 prepare 錨點（出廠 85%）時有並行效果——SA 鏡唯讀實測：真實快取 20:16（週 83%／短窗 55%）無授權 (cap 2, 現在可派 1)、有授權 (4, 2)；合成週軸 ≥86%：無授權 (1, 1)、有授權 (2, 1)。即週軸越過 85% 後 `--pace` 會印「清倉生效中」而現在可派仍 1（附錄 §4.4 prepare×far：(1,1)→(2,1)，QB1 夾層刻意保留 prepare 帶）；要不要在授權期間把 prepare 帶比照 converge 帶，是另一次修憲（〈六〉向掌舵者提問）。(3) Dev 作業期間週軸由 75% 升到 78%——帳號跨 session 共用，歸因於 Dev 包是〔推論〕；四鏡期間續升（SA 鏡 20:16 現查週 83%／短窗 55%）。

### 三-4 修復包後主控親驗（2026-10-12 21:14 +08:00；真落款仍在；rc=0）

`python tools/session_resume_planner.py --pace`（修復包 C1／C2／C5 的真機形狀；此時週軸已 86%＝越過 prepare 錨點、**效果帶之外**：授權只把週軸 cap 1→2、現在可派 1——SA 鏡 P3-1 預告的形狀當場出現；短窗軸 76% 為 converge 帶 cap 2→4）：

```text
session 來源＝環境變數 CLAUDE_CODE_SESSION_ID（sid=ed1c9022-22cc-4974-a8b3-9d4ebfa5f6bd）
現在可派 1 個 agent（硬上限 cap=2，本視窗已用 1 次）｜band=prepare｜最緊的一條＝seven_day 86% 剩 7484 分鐘｜🔥清倉 45c49b8e35：放寬 4 軸／未放寬 2 軸
  kind=session 76% 剩 54 分鐘 band=converge horizon=mid cap=4；kind=weekly_all 86% 剩 7484 分鐘 band=prepare horizon=mid cap=2 note=burn-ahead；kind=weekly_scoped 47% 剩 7484 分鐘 band=free horizon=far cap=None model=Fable note=burn-ahead；kind=five_hour 76% 剩 54 分鐘 band=converge horizon=mid cap=4；kind=seven_day 86% 剩 7484 分鐘 band=prepare horizon=mid cap=2 note=burn-ahead；kind=spend 0% reset 距離不明 band=free horizon=none cap=None note=missing　⇒ cap=2 recommended=1 band=prepare binding=seven_day reason=ok,burn-ahead,gate_excluded=spend,missing
  🔥清倉模式生效中（落款 45c49b8e35，發令 2026-10-12T19:34:11.353965+08:00，作用至 kind=weekly_all reset 2026-10-17T17:59:59.540762+00:00；效期剩 7484 分鐘／must-finish 門檻 5 分鐘）⇒ 本次放寬：kind=session band prepare→converge cap 2→4 rec 1→2、kind=weekly_all cap 1→2 rec 1→1、kind=five_hour band prepare→converge cap 2→4 rec 1→2、kind=seven_day cap 1→2 rec 1→1；未放寬：kind=weekly_scoped（model-scoped 不納入）、kind=spend（fallback 不納入）
  攤提：kind=weekly_all 剩 14pp／距 reset 7484 分鐘 ÷ 24.9 個 kind=session 窗 = 每窗 0.56pp ×r=5.0（n=67 ⇒ 取中位數）⇒ 本窗配額 2.8pp；kind=session 已用 76pp 剩 54 分鐘 ⇒ 本窗餘裕 -73.2pp；短窗自軸 pace_index=0.93（≤1＝短窗自身未超線性；分母是短窗流逝比，與本窗餘裕不同軸、不可互抵）
  派工前置：方案指紋=five_hour+session+seven_day+spend+weekly_all+weekly_scoped｜此帳號**沒有** usage credits ⇒ 訂閱窗本身即硬牆
   ⏱ 扇出視窗：剩 296 秒（帳上 1 筆，最舊 4 秒前）⇒ 再等 296 秒，最舊那筆就滾出 300s 視窗、釋出 1 個名額
   ⏳ 這一條的 reset 在 2026-10-17T17:59:59.919871+00:00（**遠超 6 小時**） ⇒ 這個 cap 會**連續套用好幾天**（清倉模式生效：cap 不隨 reset 逼近再放寬（遠期減速已由 BD-1 收回））。
   🔻 降級建議：kind=five_hour,session,seven_day,weekly_all 已進收緊帶 ⇒ 建議派工帶 model: sonnet/haiku 續跑（只建議不自動改模型；cap 不受本行影響）。（清倉模式下僅供參考，不影響 cap）
   🤖 模型角色（env.shared／.env AUTOSDD_MODEL_*）：主控=fable｜子代理=sonnet｜降級=haiku（主控值只管無人喚醒窗口；互動視窗自己的模型 env.shared／.env 管不到，派工請明寫 model:）
  來源=cache 量測於=2026-10-12T21:14:10+08:00
```

判讀：標題行只剩短標記（`🔥清倉 45c49b8e35：放寬 4 軸／未放寬 2 軸`）、全文清倉段獨立一行只印一次（C1）；節流期程行改印「清倉模式生效：cap 不隨 reset 逼近再放寬（遠期減速已由 BD-1 收回）」、降級建議行尾加「（清倉模式下僅供參考，不影響 cap）」（C5）；「未放寬」清單只列 model-scoped／fallback 兩軸、理由為真（C2）。`--status` rc=0、六項判準全 ✓（逐字同三-3 形狀，略）。

## 〈四〉四方獨立審查（Architect／SA／SD／QA；Sonnet 唯讀鏡；各自落檔；互不交談）

共同脈絡包＝scratchpad `review_context_pack.md`（四問原文、前六次宣稱、座標、判決口徑、交件格式；不入庫）。四面鏡皆於主控真落款**之後**審（可讀真 `--status`、不得 `--pace`／`--issue`／`--revoke`）。

| 鏡 | 判決（首行逐字＋回覆理由摘要） | P≤2 | P3 | P4 | findings 檔 |
|---|---|---|---|---|---|
| Architect | `VERDICT: APPROVE`（回覆摘要：無 P≤2；14 項 P3 為提交前改的文字／記載訂正，14 項 P4 登記） | 0 | 14 | 14 | `CrossPlatform_R212_Row5_Findings_Architect.md` |
| SD | `VERDICT: APPROVE` | 0 | 6 | 6 | `CrossPlatform_R212_Row5_Findings_SD.md` |
| QA | `VERDICT: APPROVE`（回覆摘要：無 P≤2；P3 共 11 條、P4 共 8 條） | 0 | 11 | 8 | `CrossPlatform_R212_Row5_Findings_QA.md` |
| SA | `VERDICT: APPROVE`（理由句：追溯成立、無 P≤2；授權效果帶、措辭過樂觀、Q2 後半句未被回答三者須 commit 前訂正） | 0 | 11 | 13 | `CrossPlatform_R212_Row5_Findings_SA.md` |

三鏡的獨立量測（摘要；逐字見各檔〈五〉）：Architect——24 個接縫清單（兩表未列者：清倉層 hook 消費點、人類面 loud 出口、時區／DST、痕跡夾具列）、§16 四格獨立重數 ✅31／➖33／⏸29／📎8、`_merge` 20×20 窮舉零收緊零 None／有限互換、真實語料 `weekly_all`＝`seven_day` 205／205 字串全等、分軌軸 0／204；SD——6000 組隨機狀態對 HEAD 與工作樹 `decide`／`describe`／`pace_line`／`axes_of` 逐位元相同（不下令逐字不變）、23094 組有授權語料規格不變式違反 0、隔離重現立案情境下令前 cap=1 binding=five_hour／下令後 cap=4 binding=seven_day、派工 hook 穩定 cap 已達 4（`autosdd_quota_stability_fable.json`）；QA——根層全套 rc=0（5352 項、47 項平台標籤略過）、AutoClaude 全套 rc=0（dev venv 5248 項通過／156 項略過；同 commit CI 出廠環境 5146／224）、六個 CI run id 逐一吻合皆 success（4 支 push＋2 支 schedule）、有效 64 個突變殺 53、`--status` 重跑 rc=0。

三鏡 P3 的合併處置：程式面 8 項（C1 清倉段重複→標題短標記＋全文一行一次；C2 「未放寬」理由字面；C3 幽靈鍵鎖 consumers 元組；C4 事件檔欄名 `decided_cap`；C5 清倉生效時節流期程行措辭；C6 測試牙口（hook 路徑 kill-switch／寫入端 QB4／Q-cross 底線／`--status` OFF／刪恆真斷言）；C7 鎖列理由改事實句；C8 逾 TTL 快取警示）交修復包 Dev-2；文件面由主控改（見〈五〉）。

## 〈五〉修復與複審

### 五-1 修復包 Dev-2（Sonnet，一包；報告＝scratchpad `dev2_fixpack_report.md`，不入庫）〔他包回報〕

- C1 清倉段只印一次：`Applied` 加 `mark` 欄（短標記 ≤30 字）；`describe(d, *, burndown=True)` 預設帶全文（hook 阻斷訊息沿用）；`pace_report` 第二行 `burndown=False`＋獨立一行 `full_line`；零網路真渲染驗整份輸出全文恰 1 次。
- C2 「未放寬」理由：`_why` 重寫為四句真話（供給軸不 qualifying 指名 `total_kind`／視野已不在 far／攤提在此帶未收緊／本軸無攤提可暫停），舊「不同窗」「已在放寬上限」全刪；08-28 原型與真機 hook 形狀各有文字斷言。
- C3 幽靈鍵鎖：`test_context_budget_guard.py` consumers 元組加 `quota_burndown.py`（+1 行）；`quota_gate.py` 註解不再含鍵名。C4 事件列欄名 `decided_cap`／`decided_rec`。C5 `NOTE_HORIZON`／`NOTE_HINT`（halt 帶不替換）。C6(a)～(e) 全做。C7 鎖列理由改事實句。C8 逾 TTL 警示＋docstring。
- SA 四條最小斷言：`issued_at` 帶 offset、`active().named_resets_at`、needle 四字串、BD-2 cap／rec 分開斷言——對應存活突變 N13／P03／N03／N08／P01／P02 皆已殺。
- 行數：tools/tests 相對 Dev-1 +3（lane 305→308；軌上限 309，**餘 1 行**）；總量 116737；`--print-guard-lines` 淨額 +0；`quota_gate.py` LOC 499／500（餘 1）、`quota_messages.py` 391／400、`quota_burndown.py` 392 行（斷言行 260／400）。
- 變異實驗（隔離副本）97 個：85 殺、12 存活（7 個等價或冗餘；5 個 P4 級缺口：halt 理由文字、時鐘不明理由文字、`Burn.left` 無獨立釘、`active()` 外層 try、`--status --model`——補任一條即用盡 lane，主控裁決不補、登〈七〉#101～#105）。
- Dev-2 揭露：(a) 其 scratchpad 端到端腳本因圍籬覆蓋 env **誤打了一次真實 usage 端點**（唯讀 GET；違反任務書「不碰網路」）；核對真實落款 id／事件檔／燃燒帳／配速檔 mtime 皆未變，腳本隨即改成網路必拋例外——登〈七〉#106（流程面）。(b) 全套第一輪抓到其造成的 4 個 ERROR（`test_model_roles` 的 `SimpleNamespace` 替身無 `.burndown`），以 `getattr` 修。
- 交件時 13 紅全在 docs 側（Dev 禁碰）：2 支 `guard-total:R213` 標記數字（116734→116737）＋ 11 支 SC-9 連鎖（三份 findings 檔各一行「某平台零真機」宣稱無輪次界定）——主控改標記行、三行各加「（R212 範圍內）」後 `test_adr_xplat001_c1c2_lock` 187 項通過（rc=0；逐字見〈八〉）。

### 五-2 主控文件面處置（四鏡 P3 的文件項）

套用清單：Architect P3-01（主檔〈二-0〉定義歸屬追記＋〈六-5〉題一）、P3-02／P3-03（A4 與 v2.1.19 措辭；〈四〉〈五〉填妥後才提交）、P3-04（§6.1 列殘存症狀句）、P3-06／07／08（附錄〈落地訂正注〉①～⑤）、P3-09（〈三-1〉(e)）、P3-11(2)(3)（〈三-2〉後果＋〈七〉#100）、P3-14（〈三-3〉改落款檔讀數重算）；SD P3-6（〈三-2〉後果）、〈六〉C2（〈二-2〉Q-cross 以碼為準）；QA P3-1／2／5／9（〈六-6〉限定句）、P3-4（§16.3 (b) 快照標記）、P3-10（四份 findings 登記 `governance_docs.py`）、P3-11（〈三-3〉判讀 (1)）；SA P3-1（效果帶：A4／〈三-3〉／〈六-5〉題二）、P3-3（暴露證據時序歸屬）、P3-4a/b、P3-7（A4 操作入口；根 CLAUDE.md 速查表不動）、P3-8（〈六-2〉逐機制 E2E 表）、P3-9（§11.3／§11.2／§15.5 三列 📎 文字）、P3-10（〈一〉(c)）、〈六〉A1／B2／C3／C4／D3／D5／E3／E5／E6／F1～F6。未採：根 CLAUDE.md 速查表加列（該檔九族測試釘住，不在本列射程）。

### 五-3 QA 二審（Sonnet 唯讀鏡；`CrossPlatform_R212_Row5_Findings_QA2.md`；登記於 governance_docs）〔他包回報〕

- 判決首行逐字：`VERDICT: APPROVE`。C1～C8＋SA 四條逐項驗證全部成立、各有會紅的測試；32 個隔離突變殺 30（任務書點名四個皆被預期斷言殺掉）、存活 2 皆非 P≤2（P4-A `_why` 分界 `and not held` 無釘、P4-B `_merge` 的 `max(b.cap, …)` 等價防禦）。
- 不下令時對 HEAD 逐字不變：800 組隨機狀態＋真實燃燒帳 443 列×6 變體＋12 份 `pace_report` 零差異；唯一差異＝`row_of()` 每列多 `"bd": null`（PRD v2.1.19 該句已限定範圍）。
- 閘門：根層全套兩輪 rc=0（各 5351 項、47 項平台標籤略過；兩輪前後樹指紋相同）；五模組 unittest rc=0（1387 項）；ruff／`check_loc_budget` 四類違規皆 0；baseline_sites／crossref／carriers／ntfs／`--env-doctor` 皆 rc=0；真實 `--status` rc=0 且 `~/.autosdd` 前後快照零差異；`tools/tests/test_model_roles.py` 60 項 rc=0（Dev-2 的 4 個 ERROR 已修）。
- 新 P3 共 7：P3-1（程式面）C5 替代句條件過寬——以「授權在場」而非「binding 軸被放寬」為條件；真實燃燒帳反事實重放 251 筆替換中 163 筆（65%）binding 軸未被放寬 ⇒ **主控當輪修**（`Applied` 加 `relaxed` 欄、`throttle_horizon_line` 只在 binding 軸 kind 在已放寬集合內才替換；見五-4）；P3-2～7 為文件措辭（〈六-2〉測試數 14→13、〈三-2〉拆輪字樣、PRD v2.1.19「逐位元不變」限定、〈六-3〉〈六-6〉輪次界定、〈四〉表頭、佔位列）——全數套用。
- 開了→收了：六份 `tools/.last_failure_*.log` 逐一 rm；哨兵 2→2→2→2；無殘留行程；沙箱不入庫。

### 五-4 主控對 QA2 P3-1 的修法（收尾單人窗口；守 lane 餘裕）

`tools/lib/quota_burndown.py`：`Applied` 新增 `relaxed: tuple`（已放寬軸的 kind 集合），`Burn.apply` 填入；`tools/lib/quota_messages.py::throttle_horizon_line` 的替換條件改為「`decision.burndown` 在場 ∧ 非 halt ∧ `decision.binding.kind ∈ burndown.relaxed`」，不成立時沿用原句（含勸退句）；`model_hint_line` 的 `NOTE_HINT` 維持「授權在場即附註」（只建議、不影響 cap）。測試：`tools/tests/test_quota_burndown.py` 既有 C5 斷言改成同時斷言真機形狀（binding seven_day 已放寬 ⇒ 替換）與 08-28 原型（binding 為 model-scoped 軸、未放寬 ⇒ 不替換、勸退句在），零增行。驗證＝〈八-1〉末段。

## 〈六〉四問答覆現況核對（T1 第七次；對照前六次宣稱；四鏡訂正已套用）

### 六-1 問 1「找到沒法完成收斂的根因，徹底解決」

- 前六次宣稱：根因兩層（程式小洞＋接縫從未在真排程器整段跑過）；第四列真跑尾段；收斂＝症狀驅動。四鏡核對：屬實、未寫成已驗（SA 鏡〈六-G〉；Architect 鏡接縫表：24 個接縫，兩表未列者＝清倉層 hook 消費點〔本列新增〕、人類面 loud 出口、時區／DST、痕跡夾具列——皆 P4 登記）。
- **第三層根因（需求層；Architect P3-01／SA F6，本列新增）**：七次同題的縫在**終點定義的歸屬**——掌舵者字面要求「所有功能＋逐項 E to E」，而 PRD §16.1 的四格結案定義（與主檔〈二-0〉的收斂定義）皆為主控代決、未經掌舵者明示追認。技術面已無 P≤2（四鏡 4×APPROVE），剩下的是一個**只有掌舵者能回答的問題**（六-5）。

### 六-2 問 2「完成實作 PRD 所有功能 ⇒ 每個功能都已完成 E to E 全功能驗證」

- §16.2 四格現況（Architect 鏡獨立重數＝主控數）：✅31／➖33／⏸29／📎8＝101（§16.3 (b) 仍是 v2.1.17 快照 29／33／31／8，已加快照標記、不重算）。本列轉格：A4 清倉模式 ⏸→✅（§16.5 (iii)）。
- **Q2 後半句「逐功能 E to E」前六次從未正面回答（SA P3-8 必改）**。SA 鏡的逐機制分級（A＝真機整段 E2E／B＝真機單次觀測／C＝只有單元・契約・鎖／D＝零；Windows 面 R212 範圍內 0 筆）逐字收錄如下：

分級：A＝真機整段 E2E（真排程器／真 claude／真 hook，有逐字痕跡）；B＝真機單次觀測（真資料餵真碼，不是驗收腳本）；C＝只有單元／契約／鎖測試；D＝零（未實作、依設計不做、只欠驗收）。所有列的 Windows 面：R212 範圍內 0 筆樣本。

| 機制群（§16.2 ✅ 列） | 分級 | 證據座標 | 缺口 |
|---|---|---|---|
| 額度遙測取數＋TTL＋429 處理（§4.1.1-T5、§8-1b、§12-憑證） | B＋C | 骨架〈二-1〉〈三-3〉的 `--pace` 逐字（`來源=cache 量測於=…`）；Run4〈二〉事件 `probed … source=endpoint`；`test_quota_policy` 339 項 | §11.1（6 小時零 token 驗證）＝📎 |
| 視窗翻頁、方案指紋、遙測失效收斂（§4.1.3／§4.1.4／§4.1.5／§8-6） | §4.1.4 為 B（落款 `core_signature` 比對 ✓，〈三-3〉）；其餘 C | 同上；DEF-200-242 的「本機落款 50 次翻頁」是重放資料，不是 E2E | 無整段 E2E |
| 閘門優先序、平穩性、pace_index（§4.2.3a／§4.2.4／§4.2.8、A1／A2／A8） | B＋C | `--pace` 逐字含 `gate_excluded=spend,missing`、`⏳ 目前 cap=2 由遲滯維持`、`pace_index=0.60` | 離線模擬器、H1 fixture、DRY_RUN 一週＝§11.2 📎 |
| 撞線喚醒閉環、長休眠交棒、續跑視窗、哨兵自癒（§4.5.5／§4.5.6／§4.5.8／§11.4、A5a／A6／§8-10） | A（僅 mac） | 主檔〈十一〉三次（2026-10-11）、Run4〈二〉跑法④ 22 項判決、2026-10-10 真撞線事故（主檔〈二-0〉）；C：四組測試合計 223 項本鏡實跑 rc=0 | 真 429 寫標記端、`RELAY_NEXT`／`quota_stop`／`relay_exhausted`、FRESH／PATROL、24 小時多次 reset、睡眠喚醒（Run4〈三〉末段） |
| 主控閒置盲區（§4.5.7） | B＋C | Run4〈六〉#53 四段 ≥6 小時靜止窗（他包回報＋QA 重掃）；`ControllerIdlePrepareWatchTest` | 無 |
| 髒污工作樹救援（§4.5.9、§8-8） | C | 33 項 | 本鏡在 R212 四份證據檔與矩陣備註找不到真機樣本 |
| 磁碟、斷電 checksum、開機自檢（§6.2-3／§8-4／§8-14／A9） | C（開機自檢另有 B） | 58＋16 項；F-SBR-001 r5 真跑 log 內「開機自檢」前綴行 3 行（Run4〈四〉，證據在 scratchpad 不入庫） | 斷電真機演練無 |
| 引擎權限旗標不變式 8（§12，Run4 轉 ✅） | C＋B（n=1） | 86 項；F-SBR-001 r5 真跑 3／3 步成功（haiku、僅 mac；證據不入庫） | VM 不偵測；`--settings`／使用者層 `defaultMode` 不在射程（列內自陳） |
| 清倉模式（A4，本列轉 ✅） | B＋C | `--issue`→`--pace`→`--status` 逐字（〈三-3〉）；本鏡 `--status` 現查 rc=0；落款後本視窗 Agent 派工 4 次全放行（〔逐字稿第 731／733／781／788 行〕；其中第 3、4 次是主控等 330 秒遲滯後才派，hook 的拒絕分支沒被觸發）；14 項 | 過期自動回復與 `--revoke` 沒有真機樣本（效期到 2026-10-17）；測試數＝13 項（修復包後） |
| 命令執行、禁令（§12-命令執行、§13-禁令） | C／設計 | argv 由參數組裝；一帳一帳本；`FanoutLedgerConcurrencyTest` 5 項 | E2E 不適用 |
| CLI 版本家族判定（§16.6 第 1 列） | B＋C | `claude --version`＝2.1.296 → `('family','2.1.295')`（本鏡）；58 項 | 新 minor／major 未發生 |
| 額度／模型參數檔與自動同步（§16.6 第 2 列、問 3） | mac 為 B＋C；Windows 為 D（R212 範圍內 0 筆） | `--env-doctor` rc=0（本鏡）；`.env.example` 與生成值相同；hook 以暫存 repo 真 `git pull` 驗（主檔〈二-11〉，Developer 包，git 2.54）；38 項 | Windows 首次 `git pull`、`core.hooksPath`、cp950 顯示（主檔〈八-4〉第 6 項） |
| ⏸ 29／➖ 33／📎 8 | D | §16.2 | 依設計不做、等症狀或只欠驗收 |

結論：「每個功能都已 E to E 驗證」不成立；成立的是「喚醒鏈尾段在 Mac 真機整段走過，其餘機制有單元／鎖，部分有單次真機觀測」。前六次的誠實限定句（主檔〈六-3〉）與此一致，但沒有被寫進對掌舵者的結論三句。

- 白話結論：「每個功能都已 E to E 驗證」**不成立**；成立的是「喚醒鏈尾段在 Mac 真機整段走過（A），清倉模式／`--pace`／`--env-doctor`／方案指紋／CLI 版本家族有單次真機觀測（B），其餘機制只有單元與鎖（C）」。要把 C 升成 A 的代價＝逐機制設計真機演練（如斷電 checksum、髒污救援）；📎 八列中 Mac 零／低成本可補者＝§11.3 整段凍結計時、§11.7 兩專案同時啟動、§11.1 六小時零 token（SA 鏡〈一-2-d〉給了確切指令）——是否要做，見六-5 的選項 B。

### 六-3 問 3「.env 同步、哪邊正確、如何維護、自動同步、Windows 驗證」

- 標準、載入鏈、`--env-doctor`、`post-merge` hook：四鏡核對設計與碼一致（Architect：harness 與引擎同序、引擎多 `AutoClaude/.env` 一層；hook 所有出口 `exit 0`、需人判斷旗標先出聲且早於唯一 `--fix`；一處構造差異＝行程 env 設成空字串時 harness 取出廠、引擎與 doctor 取 env.shared，登 P4 AR-12）。
- 訂正（SA F4）：「Mac 這邊全部驗過」改為「Mac：`--env-doctor` 乾淨、`.env.example` 與生成值相同、hook 以暫存 repo 的真 pull 驗；對真 repo 根的 `--fix` 刻意沒跑」。Windows 仍 0 筆真機樣本（R212 範圍內；主檔〈八-4〉六項）；本列新增一行驗收 `quota_burndown.py --status`（預期 rc=1）。

### 六-4 問 4「要不要馬上切 Windows」

- 不需要（四鏡無異議）。訂正（SA F1）：「你只剩在 Windows 貼一行指令」過樂觀——Windows 那台要做的有三件（約 1～2 小時）：同步＋hook 首次實跑、表② 回填、驗收一行；本列再加一行清倉 `--status`。

### 六-5 向掌舵者提出的決策（互動選項；主控不代決的兩題）

- **題一（終點定義歸屬；Architect P3-01／SA F6）**：A 追認 PRD §16.1 四格結案定義為「做完」的判準（技術面已 4×APPROVE，之後只由 T1～T4 事件再開）；B 在 A 之上補做 Mac 零／低成本的 📎 三列（§11.1 六小時零 token、§11.3 整段凍結計時、§11.7 兩專案同時啟動）；C 以「逐功能 E to E」字面為判準全部重開（代價＝逐機制真機演練，週額度不夠）。主控建議 **A**（B 可作為 T1 單獨立案）。
- **題二（清倉效果帶；SA P3-1）**：週軸越過 prepare 錨點（85%）後，授權只把 cap 1→2、現在可派維持 1。A 維持現狀（過 85% 後慢慢用、一次 1 個並行；halt 與 must-finish 照舊）；B 另立修憲：授權期間 prepare 帶比照 converge 帶（仍保留 halt 與 must-finish；屬守衛面變更，暴露證據＝本列實況）。主控建議 **A**（prepare 帶是 PRD 自設的「準備」帶，清倉不應拆到停機線前一格）。

### 六-6 前六次宣稱中寫得對、不必改的（SA 鏡〈六-G〉對照）

「六支 CI 全 success」「29 個檔」「帳本未結 0」（限定：主帳本；外部阻塞軌 5 筆、結構性長債軌 6 筆另列）「入庫工具 `--run` 只被 mock 驗過」「收斂是症狀驅動、Windows 零量測（R212 範圍內）、真 429 寫標記端沒有新樣本、24 小時多次 reset 連續閉環未做」皆屬實；數字限定（QA P3-1／P3-2／P3-5）：六支 workflow＝4 支 push 觸發＋2 支 schedule（headSha 皆 1818de87）；AutoClaude 全套 5248／156 是 dev venv（含 PG extras），同 commit CI 出廠環境 5146／224；「22 項判決」出自不入庫的手動判決器 `judge4.py`，入庫 `--judge` 涵蓋 17 項（事後重判真痕跡＝15 項 PASS／2 項 WARN）。

## 〈七〉理論洞新增（P4；只登記、不修；全域連號接 Run4 檔〈六〉最大號 #58）

四鏡的 P4 各住其 findings 檔〈四〉（每列附暴露度與一句可觀測再開症狀；四份皆為登記的治理文件）。全域連號以鏡序配號、不逐列抄錄：

| 全域 # | 來源（局部號） | 筆數 | 本列主控另加的一筆 |
|---|---|---|---|
| #59～#72 | Architect 鏡 AR-01～AR-14（含 AR-01 落款不綁視窗身分、AR-02 清倉不涵蓋接力／`draining()`／簡報、AR-12 行程 env 空字串時 harness 與引擎取值不同、AR-13 標籤即帳戶） | 14 | — |
| #73～#78 | SD 鏡 P4 六項（含 SessionStart 簡報額度行不帶清倉授權、隔離重現 cap=2 對 hook cap=4） | 6 | — |
| #79～#86 | QA 鏡 P4 八項（含突變存活 B42 顯示面、B43 外層 fail-closed 網） | 8 | — |
| #87～#99 | SA 鏡〈四〉13 項 | 13 | — |
| #101～#105 | 主控（Dev-2 變異存活 5 個真缺口，不補以守 lane）：W7 halt 軸未放寬理由文字無斷言／W8 時鐘不明軸理由文字無斷言／R2 `Burn.left` 無獨立釘／R3 `active()` 外層 fail-closed try 無釘／S2 `--status --model` 無釘 | 隔離副本變異存活；生產碼正確（二鏡各自證） | 任一條對應的理由文字或 fail-closed 行為在真機 `--pace`／`--status` 畫面或 hook 阻斷訊息中出現錯誤字面或例外（附 sid＋畫面） |
| #106 | 流程面：Dev-2 的 scratchpad 端到端腳本因圍籬覆蓋 env 誤打一次真實 usage 端點（唯讀 GET），違反任務書禁令；狀態檔零變動 | 真機 1 筆（Dev-2 自報） | 任一包的實驗腳本再度對真端點發出請求（`quota_meter` 痕跡或端點呼叫計數 ≥1 於實驗窗內；附 sid＋時刻）——派工任務書應改為「圍籬以 urlopen 替身強制、不靠 env」 |
| #100 | 主控：單一真實輪（檔名鐘 R212）內 tools/tests 淨額 +1104 以 R212／R213 兩個標籤記帳（標籤即帳戶），`repin_growth_problems` 的每輪上限在「同輪多列」形態下由標籤切分而非由檔名鐘切分 | 讀碼推得；鎖全綠 | 同一檔名鐘輪內出現第三個重釘標籤，或 R214 標籤重釘時 Phase-2／516→515 到期義務被略過而鎖未紅（附 `--print-guard-lines` 與測試輸出） |

## 〈八〉本機閘門與雲端對帳

### 八-1 主控親跑（收尾單人窗口；每條 rc 單獨印）

- `python tools/check_defect_log_crossref.py` rc=0（帳本 229 筆、具名治理文件 172 份皆已登記；四份 findings 登記後）；`python tools/check_handoff_carriers.py` rc=0（新文件 `git add -N` 後掃描；前瞻延後 0 筆）；`python tools/check_pytest_baseline_sites.py` rc=0（未納管存量 114 不增）；`cd tools/tests && AUTOSDD_SENTINEL_OFF=1 python -m unittest test_adr_xplat001_c1c2_lock` → `Ran 187 tests … OK`、`GLC_LINES=116737`（標記行與 SC-9 三行修後）；`python -m unittest test_check_defect_log_crossref test_defect_id_reference_integrity test_check_pytest_baseline_sites test_archive_defect_log` → `Ran 495 tests … OK`（主控文件草稿期）。
- 全套與 AutoClaude 側：一審 QA 鏡（修復前）根層 rc=0（5352 項、47 項平台標籤略過）、AutoClaude rc=0（5248／156，dev venv）；修復後由 QA 二審重跑兩輪 rc=0（五-3）；push 前 pre-push 全套另跑一次（結果見八-2）。
- 主控最終樹（QA2 P3-1 修法套用後；收尾單人窗口親跑）：`ruff check tools/lib/quota_burndown.py tools/lib/quota_messages.py tools/tests/test_quota_burndown.py` rc=0、`ruff check tools/` rc=0（`All checks passed!`）；`cd tools/tests && AUTOSDD_SENTINEL_OFF=1 python -B -m unittest test_quota_burndown test_quota_policy test_quota_env_layers test_context_budget_guard test_adr_xplat001_c1c2_lock test_subprocess_encoding_hygiene` → `OK (skipped=11)`、`GLC_LINES=116737`（測試檔仍 297 行、全形寬度 >100 的行 0 支——E501 存量棘輪 `test_e501_debt_only_shrinks` 首跑紅一次（新行 101／103 寬）、縮短後綠）；`check_loc_budget --json` 四類違規皆 `[]`（`quota_gate.py` 499／500）；`check_defect_log_crossref` rc=0（具名治理文件 173 份皆已登記，含 QA2 findings）；`check_handoff_carriers` rc=0；`check_pytest_baseline_sites` rc=0；`check_ntfs_paths` rc=0；根層全套最終樹結果見八-2。

### 八-2 commit／push／雲端對帳

- 根層全套（最終樹；主控親跑 `unset AUTOSDD_PARALLEL_TESTS; AUTOSDD_SENTINEL_OFF=1 python tools/run_root_unittests.py`）：`ROOT_RC=0`；skip census `tools/tests@darwin 共 47 支：platform=47／…／untagged=0`；`真實 TEMP 圍籬：…零變動`；跑後 `tools/.last_failure_*.log` 3 份（runner 自測落檔）已 rm；哨兵 2→2。
- commit／push／CI：本列 commit 由 push 觸發 workflow，對帳結果以回填 commit 追記於本節（回填 commit 本身不再回填）。

## 〈九〉開了→收了（本列）

| 開了 | 收了 |
|---|---|
| 真落款 `~/.autosdd/traces/autosdd_burndown_directive.json`（id 45c49b8e35，掌舵者指令） | **刻意不收**：依掌舵者「儘量使用」，效期到 2026-10-17T17:59:59Z 週 reset 自動失效；要提前停用 `python tools/lib/quota_burndown.py --revoke` 或 `AUTOSDD_QUOTA_BURNDOWN_OFF=1` |
| 事件檔 `autosdd_burndown_events.jsonl`（首列仍為舊欄名 `cap`／`rec`，零讀端） | 不動（真實痕跡不改寫） |
| launchd 哨兵 | 2→2（四鏡與兩包前後各記；一審 QA、二審 QA 皆核） |
| scratchpad：`review_context_pack.md`、`brief_*.md`、`dev1_burndown_report.md`、`dev2_fixpack_report.md`、各鏡隔離副本與突變驅動器 | 不入庫；session 結束隨 scratchpad 清除；各包自報沙箱已收 |
| `tools/.last_failure_*.log`（gitignored，全套自寫） | 各包跑完已刪；主控收尾 `ls tools/.last_failure_*` 現查 |
| 本機 `.env` | 全程未動（`--env-doctor` rc=0） |

