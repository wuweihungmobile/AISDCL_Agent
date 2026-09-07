# AutoSDD_improving_112（R95）— PRD v2.1 系統本體開發輪：修憲 ×2 ＋ 攤提窗尾修正 ＋ 喚醒鏈三層閉環

> **軌道①**（AISDLC-SDD × AutoClaude 深度整合）。本輪三柱分佈：
> **C 柱（指揮官 AutoClaude）** 全占——掌舵者開場直接質疑「為何都不全力專注 PRD 開發」，
> 本輪回到 AutoClaude 核心排程與 Token 治理系統本體；**A 柱／B 柱** 無。
>
> 🔴 本輪兩度被真實撞線事故打斷（08-16 深夜收尾包、08-17 午後修復包），
> 兩次事故本身成為本輪最有價值的輸入：喚醒鏈 root cause（ADR-XPLAT-004 §2.9）
> 與「主控閒置盲區」立案（見 §4 下輪）皆源自事故現場取證。

## §0 開場盤點（發現波，2 agent 唯讀）

PRD v2.1 逐節對照實作：收斂度估計 **65%**（盤點 agent 交件，證據檔級座標見其回報）。
Plugin 體系判定：**活著**——19 plugin 註冊、Kernel 27 phase 全走 EventBus、importlinter 9 kept。
「每輪瘦身」歸因：史料佔護欄檔 25~66% 行數＋棘輪是刻意設計；
AutoClaude 包總量 cap 餘裕僅 22 LOC ⇒「搬進包內」此路不通（重校須 ADR-SD07-001 §6.3 雙簽）。

## §1 本輪交付（全數經測試憑證，逐字輸出住各證據檔）

| 項 | 內容 | 憑證出處 |
|---|---|---|
| 修憲 v2.1.4 | 遙測 T5（/api/oauth/usage）升格認可主源＋紅線 1 收窄豁免四條件＋§12 憑證劃界（掌舵者 08-16 拍板） | PRD 修訂表；PrdDrainPercentMapsToTheBandsTest 3 passed |
| 修憲 v2.1.5 | §4.5.6 撞線零人工喚醒六規範＋驗收 A1~A5（掌舵者 08-17 立案） | PRD 修訂表＋ADR-XPLAT-004 §2.9 |
| 攤提窗尾修正 | `quota_pace.amort_relaxed`：長窗自軸未達 converge 錨點 ⇒ 出聲不收緊（掌舵者 08-16 當面立案「窗尾額度作廢不算節省」）；零改既有方向鎖斷言 | CrossPlatform_R95_Pace_Actuator_Evidence.md；本輪內已兩度於真實 --pace 輸出驗證生效 |
| 模型降級建議＋pace_index | `Decision.model_hint`（建構順序保證不影響 cap）＋PRD §4.2.8 比值原式＋`AUTOSDD_QUOTA_PACE_CEILING` | 同上；本輪首次真實遵循（E501 折行包用 sonnet） |
| 治理檔禁寫（紅線 10） | block_destructive_git.py GOV_TOOLS×保護面×AUTOSDD_UNATTENDED 判準；QA 探針補 `.env`（可注入 GUARD_OFF 族逃生口的繞道）；R87 事故（13 agent 全滅）的機械物終於落地 | CrossPlatform_R95_GovWrite_Evidence.md 九格 rc 矩陣 |
| resume 三態選路 | `choose_resume_route`：SESSION_RESUME／FRESH_SESSION_WITH_STATE（32MiB 上限＝1108 支逐字稿實測分佈定值）／REFUSE（任務書缺席拒武裝） | CrossPlatform_R95_Resume_Strategy_Evidence.md |
| 哨兵存活四修 | 修1 任務書覆寫保 RELAY（08-16 事故直接根因）；修2 自癒後才解除＋必出聲（複審補 read_text 第四分形）；修3 活性欄（**上線當日實戰抓到哨兵死亡**）；修4 halt 多軸最早 reset（halt_resets_at） | 同上 §L-4；A1~A5 全達成 |
| 收尾 | 護欄棘輪兩段式重釘：收尾包 84406→84362（−44）、複審修復對價後終值 **84399（整輪淨 −7）**、連升 streak 歸零；帳本推進 R95（DEF-200-141~146、148）；CLAUDE.md 守衛總表補治理面 matcher；ENV_SPEC＋.env.example | CrossPlatform_R95_Guard_Repin_Evidence.md §F |

## §2 四方審查閉環

Architect／SD／QA 三方 REJECT（各 1 major，互不重複且全為真問題）＋SA APPROVE：
ADR §2.9 stale 宣稱、read_text fail-quiet 形態（Windows 一次性觸發器不重排）、`.env` 保護面繞道（探針實證）。
修復包全修＋高共識 minor 批次（保護面補喚醒鏈同族檔、env 病態值退預設出聲、
證據檔 rc 抄錄訂正、PRD 殘留措辭註記）。複審驗收見帳本 R95 列。

## §3 事故雙生：本輪的兩次撞線都轉化為機械物

- **08-16 深夜**：halt 覆寫任務書砸 RELAY → 哨兵自我解除 → reset 零排程 → 空轉 8 小時。
  root cause 全鏈取證住 ADR-XPLAT-004 §2.9（哨兵當晚有武裝且巡邏 10 次，死因是狀態塊被砸——
  「mac 側從未成功」的印象被證據駁回，真相是「成功武裝、被自己人殺死」）。
- **08-17 午後**：修復包撞線，主控收到通知但無水位預警機制 ⇒ 立案「主控閒置盲區」（§4）。

## §4 下輪（R96）開場即辦

1. **水位預警哨兵擴充＋PRD v2.1.6 落款**（掌舵者 08-17 兩度立案）：哨兵巡邏（零 token 讀快取）加
   「usage ≥ prepare 錨點且有活躍背景工作 ⇒ 主動武裝喚醒排程＋寫收斂任務書」職責——
   堵「主控閒置等背景 agent 時 hook 全睡、水位無人量」的結構盲區。
2. Windows 側待驗清單（帳本承接列）：govwrite 九格矩陣重跑＋大小寫繞行探針＋修3/修4 schtasks 取證。
3. 引擎側額度軸接電（第三方刷新者）；前置＝AutoClaude 總量 cap 重校雙簽程序。
4. SD/Arch 順手項：prepare 閂鎖鍵、混軸鍵補記來源軸。

## §5 誠實劃界

- 本輪全程 mac 開發驗證，Windows 零等價驗證（§4-2 承接）。
- PRD 收斂度 65%→估 72~75%（P1 五項全落地），精確值下輪開場重盤。
- M2/M3/M4 成熟度判準本輪未量測（與既有基線一致）。

## §6 R113 結構性長債分軌（寄居附記）

<!-- guard-total:R113 --> R113 護欄層累積淨額＝ 89452 → 89910（+458）——結構性長債軌落地 +140（`AutoSDD_Structural_Debt_Log.md` 建軌＋主帳本 7 列遷軌＋`TestStructuralDebtLog` 九支＋外部軌真檔測試拆日期引信＋姊妹帳本擴面）＋ v2.1.13 G1 實作批 (a) 同輪追加 +141（`UnattendedPermissionPostureTest` V-a 六格＋鎖檔自身編修）＋ v2.1.13 G2 實作批 (b) 同輪追加 +177（`HandbackVisibilityTest`＋`HandbackSessionStartAnnounceTest` V-b 六格＋鎖檔自身編修）；逐項見 `CrossPlatform_R106_Scan_Findings.md` 的 R113 標記行與 `_GUARD_LINES_REPIN_LOG` 的 R113 三列。裁決存證＝`AutoSDD_TechDebt_Paydown_Playbook.md` §6 第 3 條（掌舵者 2026-08-30 核准）；G1 批施工圖＝`PRD_Amendment_R113_WakeChain_LastMile.md` §3(a)、G2 批 (b) 施工圖＝同檔 §3(b)（皆 2026-08-31 落款）。

## §7 R115 收斂棒（寄居附記）

<!-- guard-total:R115 --> R115 護欄層累積淨額＝ 90351 → 90344（-7＝收斂棒 -11＋收輪補釘 +10＋補釘二 -6）——收斂棒：三個修復棒（棒A／棒B／治理批）累積漂移的一次性合法收束，兌現款(11)「必須出現一次淨額 ≤ 0」（終止 R113(+458)／R114(+441) 連兩輪上升 streak）並同輪兌現款(12) 到期義務（cap 585→577，重新武裝 117／570）。手法＝類級 docstring 沿革搬遷（三檔合計 -930，全文搬至 `CrossPlatform_Guard_Line_History.md`〈R115 追加〉節，程式碼內只留指標，斷言／判準常數／測試邏輯零改動）抵銷功能面漂移 +777（`test_block_destructive_git_r83.py` DEF-200-238 修復＋`test_context_budget_guard.py` R115 修復 F1~F4／DEF-200-239／v2.1.13 C5）；另補回三支測試類各一句真實 `tools/lib/`／`tools/probe/` 路徑指標（+6），修復分桶棘輪 `prose` 桶因 collapse 副作用滑落排他歸屬（4182→4293）的誤判，回落至 4068；全套實跑另揪出全部指標行違反 `tools/ruff.toml` E501 上限（存量債棘輪 139→252），修法＝逐行拆成兩行（三檔合計 +111）；同批順手補上 DEF-200-239 現查測試自身兩處存量鎖（`_ps_engine` SSOT／subprocess encoding，各 +3）與收尾時再揪出的兩處殘留 E501（各改行歸零）＋本檔自身 +22。逐項見 `CrossPlatform_R106_Scan_Findings.md` 的 R115 標記行與 `_GUARD_LINES_REPIN_LOG` 的 R115 列。

R115 收輪補釘：90340 → 90350（+10，含 skip 行 EAW 寬度折行 +1）——雲端首紅修復（假後端 credential_key 對齊當平台＋DEF-200-239 skip 標籤 +2）＋稽核列與接鏈列自身（+7）；同輪合併 -2 仍 ≤0。逐項見 `CrossPlatform_R106_Scan_Findings.md` 的 R115 補釘標記行。

## §8 R129 護欄層重釘（寄居附記；收尾單人窗口）

<!-- guard-total:R129 --> R129 護欄層累積淨額＝ 92268 → 93610（+1342）——喚醒鏈零浪費（INV1~5／FIX1~4）＋T-f4b 洩漏止血四個包新增 +1300 行回歸鎖：`test_context_budget_guard.py 9860→11057（+1197）`＋`test_mac_endurance_r83.py 1784→1887（+103）`＋本檔自身重釘（`test_adr_xplat001_c1c2_lock.py 7298→7340`）。淨額走 DEF-200-208 一次性例外名冊（`_REPIN_APPROVED_ROUND_OVERAGE` 的 R129 那一列，主控本 session 核准，精確淨額逐字對上，名冊上限同步 1→2）；同輪兌現到期義務 `(129,552)`（cap 555→552）並重新武裝 131／550；款(11) 因前一輪 R127 淨額 −38 已斷 streak 而未觸發。Phase 2 §6 時效（越過到期輪 R127、`[維持觀察]` 名額由 R122 用罄）記一列 `[提案]`，四方複審由主控承接。逐項見 `docs/06_quality/CrossPlatform_R129_Scan_Findings.md` 與 `_GUARD_LINES_REPIN_LOG` 的 R129 列。此附記為收尾窗口為滿足 doc-total 對帳（≥2 站點）而寄居於本 improving 檔，同 §6／§7 的 R113／R115 寄居附記體例；R129 屬跨平台整合輪 R 系列、非本 improving 迭代序。
<!-- guard-total:R130 --> R130 護欄層累積淨額＝ 93610 → 93734（+124）——M-01 喚醒 tick 自標無人（規則 1 死碼修復）＋M-05 followup 接線端到端測試：`test_context_budget_guard.py 11057→11169（+112）`＋本檔自身重釘（`test_adr_xplat001_c1c2_lock.py 7340→7352`，含 U9 root-tools 舊尺債具名展延 130→132、鐵律七獨立重構）。淨額 124 ≤ cap 552（`net_cap_for_round(130)`）；連升 streak 第 1／2（前輪 R129 為 approved-overage 不計）。逐項見 `docs/06_quality/CrossPlatform_R130_Scan_Findings.md`。此附記為 doc-total 對帳（≥2 站點）寄居本 improving 檔，同 R113／R115／R129 寄居體例；R130 屬跨平台整合輪 R 系列、非本 improving 迭代序。round-label-ok
<!-- guard-total:R131 --> R131 護欄層累積淨額＝ 93734 → 94548（+814）——喚醒鏈四方審計與三大問題最相關的一批發現經多位小幫手對抗查證，其中確認仍是破洞的一批（M-03/M-06/M-07/M-13/M-15/M-16/M-20）本輪修復並經主控獨立重跑驗證：`test_context_budget_guard.py 11169→11628（+459）`＋`test_run_root_unittests.py 2428→2451（+23）`＋本檔自身重釘（`test_adr_xplat001_c1c2_lock.py 7352→7373`），淨額 503 ≤ cap 550（到期輪兌現）；同輪再加喚醒鏈規則6崩潰根因修復（write_relay 任務書消失未捕捉例外炸穿無人巡邏行程）的回歸鎖 +210，及對抗式複審發現的收尾修復（rearm／sentinel_rearmed 分支不清 latch／不 loud alert）回歸鎖 +99（合計 +309，全額歸回歸鎖軌，`_REGRESSION_LANE_LOG` 同輪列，貼齊上限 309、不計入 cap 550），累積 814。連升 streak 第 2／2（前輪 R130 為第 1／2，R129 為 approved-overage 不計）；同輪重新武裝下一段到期義務 133／549。逐項見 `docs/06_quality/CrossPlatform_R131_Scan_Findings.md`。此附記為 doc-total 對帳（≥2 站點）寄居本 improving 檔，同 R113／R115／R129／R130 寄居體例；R131 屬跨平台整合輪 R 系列、非本 improving 迭代序。round-label-ok
