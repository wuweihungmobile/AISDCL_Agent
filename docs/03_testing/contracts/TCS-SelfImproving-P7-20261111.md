# Test Contract Specification — SelfImproving P7（核准流程全程 UI 化・第一波主機端：提案詳情匯出、巡邏快照、M 類自動推進、自動推送）
# 測試契約規格文件（增量變更；FRD-lite 併入檔頭；根層單半，Console 端由 `agentconsole-si-flow-visibility` 鍵交付）

**文件類型**: Test Contract Specification (TCS)　**SDD Gate**: SCG-4　**spec-format-version**: 1.0　**scenario**: brownfield
**使用時機**: 已凍結系統（PRD v0.15 於 P6 鍵凍結）的單一 Feature（P7）；FSM 功能鍵 `monorepo-si-p7-flow-visibility`；`spec-frozen --doc` 指向本檔
**存放位置**: `docs/03_testing/contracts/TCS-SelfImproving-P7-20261111.md`　**輸入快照**: HEAD `e1ad0ac0`（寫稿時現查，工作樹乾淨；本稿作者只讀程式碼、只寫文件）
**建立日期**: 2026-11-11　**QA**: SCG-4 獨立 QA 棒（規格作者＝本 SA 棒，實作者＝Developer 棒＋主控〔收尾、真機、重釘〕，三方不同）　**SCG Gate**: SCG-4 □ 待審
**對齊**: 已對齊主控裁決 1～11（1 回報通道＝唯讀 bind `console_report`＋原子覆寫 `patrol.json`、不簽章；2 `sched_auto_push` 預設 true＋守門；3 **S4U 巡邏器本體永不推送、推送由互動登入型任務 `AutoSDD_SI_Push` 執行 `push-run`**；4 R156／目標運轉／cancel 屬第二波、本波只白話顯示原因；5 新鮮度判武裝；6 M 類不加互動視窗安靜前置；7 `heldout-freeze` 低於下限只警告；8 原因碼→白話單一真相源、凡帶碼處同帶白話；9 console-writes 十一鍵不動、前端以稽核編號對照 `ingest[]`；10 OFF 仍寫快照、衝突走勘誤列；11 黃金樣本路徑由本檔 §3 定義）；一審（`docs/06_quality/SCG0-REVIEW-SelfImprovingP7FlowVisibility-20261111.md`，CONDITIONAL）發現 R-01～R-22、C-01、C-02、C-13 已於本修訂處置。
**範圍界線**: 本檔只涵蓋**根層**（`tools/`、`docs/`）。Console 端（Bridge `GET /si/patrol`、compose 唯讀 bind、前端以稽核編號 `auditRef` 對照快照 `ingest[]`〔console-writes 既有十一鍵不動，裁決 9；backend 的 `SiKeyNames.camelKeys` 已深層對映整棵樹，無須改動〕、前端詳情抽屜與巡邏狀態卡、每頁說明）由 `agentconsole-si-flow-visibility` 鍵的 Console TCS 交付；本檔第 2 節〈介面契約定稿〉是兩端共用欄位的唯一本文（匯出 `detail` 欄與 `patrol.json`），Console 端 TCS 以「路徑＋章節」引用、不複寫。第二波（`monorepo-si-p8-flow-crud`：目標運轉、自動凍結／修訂、`cancel`、R156 改寫）**不在本檔**。

---

## 增量追溯表（BRIDGE §8.5；SCG-0～3 每個清單項一列）

> **誠實揭露**：P7 自己的上位文件（PRD v0.16、SOP、`Root_Layout`）於本稿寫成時**尚未在 P7 鍵凍結**，不能被引用為已凍結。①**繼承項**追溯到 P6 鍵已凍結的 PRD v0.15／SOP／TCS-P6（路徑如下，摘要現查 `show`）；②**P7 新增項**標 `P7-PENDING`，由主控在 P7 鍵完成 Stage-1 凍結後回填；**未回填前不得 `spec-frozen --stage Stage-2`**。

| 清單項（閘門／項目） | 追溯 ID | 已凍結上位文件（路徑） | 凍結摘要 |
|---|---|---|---|
| SCG-0／需求完整（FR 與 AC 皆有 Given-When-Then） | FR-SI-47、FR-SI-48、FR-SI-49 | `docs/01_requirements/SelfImproving_PRD.md`（v0.16） | `P7-PENDING` |
| SCG-0／AC 可測且可判定 | AC-SI-47-1～47-15、48-1～48-5、49-1～49-13、自增 AC-P7-090-1～5 | 同上＋本檔 §1 | `P7-PENDING` |
| SCG-0／上位繼承：run-scoped 授權、巡邏心跳、Console 稽核通道、M 類旗標 | FR-SI-36～39、FR-SI-35、AC-SI-38-3 | `docs/01_requirements/SelfImproving_PRD.md`（v0.15）；`TCS-SelfImproving-P4-20261109.md` | `ADOPTED-BY-REFERENCE`（現查 P6 鍵 `show`） |
| SCG-1／架構與元件落點（C4、模組落點表） | C28、C29、PRD §9.9.1；`Root_Layout_and_Module_Placement.md` §3 SelfImproving 列加 P7 句 | PRD v0.16 §9.1、§9.9；`docs/02_architecture/Root_Layout_and_Module_Placement.md` | `P7-PENDING`（PRD）；Root_Layout 非 FSM 凍結文件以 `git` 為準 |
| SCG-1／資料模型與介面契約 | §9.9.2（`detail`、`patrol.json`、`push/` 家目錄檔、結果碼）、本檔 §2 | PRD v0.16 §9.9 | `P7-PENDING` |
| SCG-2／重大架構決策有 ADR | ADR-SI-19（巡邏器永不推送、推送交互登入任務；PRD §9.5 加列，不開 ADR 檔，C.2 #15） | PRD v0.16 §9.5 | `P7-PENDING` |
| SCG-2／安全與停機（遠端寫入的權力邊界、鎖、牆鐘） | PRD §9.4〈P7 增補〉；繼承 NFR-SI-01／02／09 | PRD v0.16 §9.4 | `P7-PENDING` |
| SCG-3／介面契約（CLI 動詞、檔案契約） | §9.3 `push-run` 列、`export --kind proposals --id` 的 `detail`、`sched arm|disarm` 增補 | PRD v0.16 §9.3 | `P7-PENDING` |
| SCG-3／OpenAPI delta | **無**（本鍵不新增任何 HTTP 端點；Bridge `GET /si/patrol` 與 backend 對映屬 Console 鍵） | — | — |
| SCG-4～6 | 不因增量而縮減（SCG-4 獨立 QA、RTM、RELEASE_READY 照走；真機 V 項見 §6） | — | — |
| 下位繼承（AT 體例、同步站點、範圍守衛形態） | `TCS-SelfImproving-P6-20261110.md`（表格式 AT、`-k` 錨定、`px` 夾具、`SI_SCOPE_BASE` 守衛） | `docs/03_testing/contracts/TCS-SelfImproving-P6-20261110.md` | `ADOPTED-BY-REFERENCE` |
| 上位 SOP（巡邏、M 類旗標、held-out、提案檔、任務書範本） | SOP〈巡邏與無人運轉（P4）〉〈M 類旗標〉〈held-out 目錄〉〈提案檔〉〈無人運轉任務書範本〉；新增〈自動推送（P7）〉〈巡邏快照與 M 類自動推進（P7）〉 | `docs/05_development/SelfImproving_Operations_SOP.md` | `P7-PENDING` |

## FRD-lite（US／AC；AC 本文以 PRD v0.16 為準，本表只列編號與一句話，避免第二份真相源）

| US ID | User Story | AC ID | AC（一句話；全文見 PRD） |
|---|---|---|---|
| US-P7-01 | 身為掌舵者，我要在 Console 看到提案的全部內容與評估證據，不必開 CLI | AC-SI-47-1～47-7 | `export --kind proposals --id` 的 `detail`：patch／本文／來源觀察／評估集狀態／沙盒與驗證證據／下一步／時間線 |
| US-P7-02 | 身為掌舵者，我要知道每個提案現在卡在哪、等誰，我的決定為什麼沒入帳，以及排程／立即啟動為什麼沒開運轉 | AC-SI-47-8～47-12、47-15 | 巡邏快照 `patrol.json`（心跳、入帳被拒碼、每 PROP 卡點、運轉、跳過原因、推送）與白話對照表單一家 |
| US-P7-03 | 身為維護者，我要評估集不足與 SOP 文字不再誤導凍結者 | AC-SI-47-13、47-14 | `heldout-freeze` 低於下限只警告；SOP 三處勘誤與範本補句 |
| US-P7-04 | 身為掌舵者，我要 M 類（記憶）提案也能自動走沙盒、驗證、晉升 | AC-SI-48-1～48-5 | 巡邏器帶 `--memory-dir` 推進 M 類；解析不到記原因碼；前／後像驗證 |
| US-P7-05 | 身為掌舵者，我要巡邏器 commit 之後自動推上遠端，不必開 CLI，也不會推出別人的半成品 | AC-SI-49-1～49-13 | `sched_auto_push` 與守門三條件、`push-run`、互動登入型任務 `AutoSDD_SI_Push`、結果碼與重試上限 |
| US-P7-06 | 身為維護者，我要新增的模組守得住既有純度與範圍護欄，且兩端共用同一份黃金樣本 | AC-P7-090-1～090-5（自增） | 能力登記、參數與同步站點、不退化、範圍守衛、黃金樣本 |

**Before／After（寫稿時現查，`檔:行`）**：Before——`export` 的 `proposals` 項無 `detail`（`export.py:90-96`）；巡邏器入帳被拒只寫日誌（`patrol.py:206-211`）；M 類 `approved`／`verified` 與已晉升待回滾一律記 `MEMORY-DIR` 不推進（`patrolrun.py:360-363`）；`_commit` 訊息寫「不 push」且無 trailer（`patrolrun.py:335-336`）；`sched_auto_push` 為 `never` 型、值為 true 即 `PARAM-RANGE`（`params.py:37,58-59`）；`PARAM_SPECS` 44 鍵（P6）；`C_CLASS` 15 動詞（`unattended.py:23-25`）；`schedarm.arm` 只裝 `AutoSDD_SI_Patrol` 一支（`schedarm.py:158-183`）；`heldout-freeze` 無下限提示（`sandbox.py:324-345`）；SOP 第 480 行「`sched_auto_push` 只准 false」。After——`detail` 八欄；`<si>/console_report/patrol.json` 每心跳原子覆寫；M 類帶 `--memory-dir` 推進；`_commit` 帶兩條 trailer；`sched_auto_push` 為 `bool` 型（預設 true）＋三個新鍵，`PARAM_SPECS` 47；`C_CLASS` 16（`push-run`）；`sched arm` 另裝 `AutoSDD_SI_Push`；`heldout-freeze` 低於下限印警告；SOP 勘誤與兩個新節。**不含**：Console 程式、真機（V-P7-1～V-P7-8，不入 AT）、第二波、macOS 真機（標「未驗」）。**不變**：`KINDS` 27、`EVENT_LABELS` 27、`check` 35 項、`status` 20 鍵、`CHECK_RULES_REV` 6、`FINGERPRINT_EXCLUDED`、`export` 的 `KINDS`——本鍵不新增事件種類、不改 `status`，使既有同步站點最少。

**編號**：FR 47、48、49＋自增 AC `AC-P7-090-1`～`-5`；AT 編號 `AT-7<FR 兩位>-<AC 序>-<序>`（承 P6 體例；`E` 為負控）：`AT-747-*`、`AT-748-*`、`AT-749-*`、`AT-790-*`（自增）。**AT 共 127（正控 80、負控 47）**；測試檔（每階段 ≤3 檔，Root_Layout §2）：RD＝`tools/tests/test_selfimproving_p7_report.py`（FR-47 全部＋SY）、MM＝`tools/tests/test_selfimproving_p7_memory.py`（FR-48）、PU＝`tools/tests/test_selfimproving_p7_push.py`（FR-49）；夾具＝`tools/tests/_selfimproving_p7_fixtures.py`（`p7x`，§3）。

**交付物與順序**：①夾具與既有測試同步站點（§2）先行（先把期望值改為新值再寫碼，使紅燈來自「碼未到位」）→②`nextstep`（純函式與白話表，先寫先測）→③`propdetail`＋`export` 接線→④`params`（四鍵）＋`params.json`＋基準檔活值→⑤`memdir`＋`patrolrun` M 類接線→⑥`pushguard`（純判準）→⑦`patrolreport`＋`patrol`／`patrolrun` 的 `Ctx.notes` 與寫快照接線→⑧`patrolpush`＋入口 `push-run`＋`unattended.C_CLASS`→⑨`schedarm` 的 `AutoSDD_SI_Push` 安裝／現查／移除→⑩`heldout-freeze` 警告（`sandbox.py`）→⑪能力登記與重釘。每支程式完成立即跑該區 AT。
**提交程序（沿 TCS-P5 D-EQA-5、D-EQA-9、P6 E-7）**：①規格 commit（PRD、SOP、`Root_Layout`、本 TCS、P4／P5／P6 TCS 勘誤）不含允許集合路徑；②規格與實作 commit 連續、同一次 push；③實作 commit 不得含 PRD、SOP、TCS、`Root_Layout`；本機跑範圍守衛（AT-790-4-1）才設 `SI_SCOPE_BASE=<規格 commit>`（可選 `SI_SCOPE_TIP`）；開發期以 `-k "not AT_790_4_"` 排除；④本檔日後勘誤單獨 commit；⑤重釘儀式另一 commit（主控收尾）。**第一次真推送前須完成一次互動主控推送**：遷移期內已存在的、無 trailer 的本機提交（例如 `e1ad0ac0` 等 SI 帳本提交）會使守門判 `PUSH-FOREIGN-COMMITS`，由互動主控以 `git push` 推一次（V-P7-3 前置）。

---

## 1. AC → AT 映射

**共同判定指令**：`python -m pytest <檔> -k <AT 底線形>_ -q -p no:xdist -o addopts=`，預期 `1 passed`（rc 0）；AT 底線形＝把 `-` 換成 `_`，尾端底線錨定。**預期突變**欄＝把該行改成「錯的」會使該 AT 紅（QA 逐條突變鏡要重跑）。`p7x`＝夾具建構器（§3）。所有 AT hermetic：不碰真帳本、不連網（`socket.socket.connect` 注入 `AssertionError`）、不註冊真 OS 任務、不 `git push` 到真遠端（遠端一律是夾具的本機 bare repo）。

### AC-SI-47-1 `detail` 欄位集合（RD）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-747-1-1 | RD | `p7x.repo()`：一個 `verified` 的 PROP（r1.patch、r1.md、`heldout.freeze`、`app.sandbox`、`app.verify`、`card` 皆在）。`export --kind proposals --id <PROP>` ⇒ `items` 恰一筆、含鍵 `detail`、`detail` 鍵集合恰 `{patch, body, sourceObs, heldout, sandbox, verify, next, timeline}`；原有 20 鍵（`id`…`window`）一個不少、值與無 `--id` 時逐鍵相等 | 少一鍵、多一鍵、或改動原有鍵 ⇒ 紅 |
| AT-747-1-E-1 | RD | 同夾具：不帶 `--id` 的 `export --kind proposals` ⇒ 每筆都**沒有** `detail` 鍵；`--kind observations｜events｜runs｜status` 加 `--id` ⇒ 輸出位元組與修改前相同（`detail` 只在 proposals 且帶 `--id` 時出現）；`--id` 查無 ⇒ `items` 空、rc 0 | 清單模式也算 `detail`（N×patch 讀檔）⇒ 紅 |

### AC-SI-47-2 patch／本文截斷與讀不到（RD）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-747-2-1 | RD | r1.patch 恰 `propdetail.DETAIL_TEXT_MAX`（262144）bytes、r1.md 短 ⇒ `patch={rel,bytes,text,truncated:false}`，`bytes`＝262144、`text` 位元組等於檔；`rel`＝`docs/06_quality/SelfImproving_Proposals/<PROP>/r1.patch`（正斜線）；`body.rel` 同目錄 `r1.md` | 常數被改、`rel` 用反斜線 ⇒ 紅 |
| AT-747-2-E-1 | RD | patch 為 262145 bytes（末尾為 3 位元組中文字元使上限落在字元中間）⇒ `truncated:true`、`bytes`＝262145、`text.encode("utf-8")` 長度 ∈ [262141, 262144] 且為合法 UTF-8；不拋例外 | 以字元數而非位元組截斷、或半個字元造成例外 ⇒ 紅 |
| AT-747-2-E-2 | RD | r1.patch 被刪（或為目錄）⇒ `patch:null`、`ne` 多一筆 `{"field":"proposals.<PROP>.detail.patch","reason":"PATCH-UNREADABLE","text":"<白話，取自 nextstep.reason>"}`（**新碼的 `ne` 項帶 `text`；既有 `ne` 項形狀 `{field,reason}` 不變**）；`body` 同理 `BODY-UNREADABLE`；其餘 `detail` 欄與 rc 不受影響（rc 0） | 讀不到時整個 `detail` 為 null 或 rc≠0 ⇒ 紅 |

### AC-SI-47-3 來源觀察（RD）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-747-3-1 | RD | PROP `sources` 為 `[OBS-SI-001, OBS-SI-002]`，OBS 帳本兩列存在 ⇒ `sourceObs` 為兩筆、依 `sources` 序、每筆鍵恰 `{id, context, symptom, severity, disposition}`，值取自帳本對應欄（原文，不截斷、不含 `｜`） | 缺欄、依帳本序而非 `sources` 序 ⇒ 紅 |
| AT-747-3-E-1 | RD | `sources` 含一個帳本中不存在的 ID（含 DEF-…）⇒ 該筆為 `{"id":"<ID>","missing":true}`，其餘照常；帳本讀不到 ⇒ 每筆皆 `missing:true` 且 `ne` 多一筆 `OBS-LEDGER-UNREADABLE` | 缺列拋例外或略過該筆 ⇒ 紅 |

### AC-SI-47-4 評估集狀態（RD）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-747-4-1 | RD | 已凍結（n=4，`min_heldout`=5，digest `sha256:abcd…`）⇒ `heldout` 鍵集合恰 `{frozen, seq, n, min, belowMin, frozenBy, digest8, neNote}`；值依序 `true`、事件 `seq`、4、5、`true`、事件 `frozen_by`、`"abcd…"` 前 8 碼（去 `sha256:` 前綴）、`neNote` 含「驗證必判 NE」「4」「5」；n=5 ⇒ `belowMin:false`、`neNote:null` | 邊界 n==min 判成 below ⇒ 紅 |
| AT-747-4-E-1 | RD | 未凍結 ⇒ `{frozen:false, seq:null, n:null, min:5, belowMin:null, frozenBy:null, digest8:null, neNote:null}`；`params.json` 讀不到 `min_heldout` ⇒ `min:null`、`belowMin:null`、`ne` 多 `HELDOUT-MIN-UNKNOWN` | 未凍結時 `belowMin` 為 false ⇒ 紅 |
| AT-747-4-E-2 | RD | **零洩漏**：held-out 目錄夾具（`~/.autosdd/selfimproving/heldout/<PROP>/` 內案例 id、探針檔名、突變檔內容各含一個唯一字串）⇒ 整份 `export` 輸出（`--id` 與清單）對這些字串**零命中**；程式碼面：`propdetail.py` 不含 `heldout` 目錄路徑建構（AST：無 `"heldout"` 字串與 `si_dir()` 呼叫）、不開任何家目錄檔 | `propdetail` 讀家目錄 held-out ⇒ 紅 |

### AC-SI-47-5 沙盒與驗證證據（RD）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-747-5-1 | RD | 同 rev 兩筆 `app.sandbox`、兩筆 `app.verify`（先 NE 後 PASS）⇒ `sandbox` 取**最近一筆**同 rev，鍵恰 `{seq,id,applied,touchedOk,rollbackOk,failCode,failText}`（`failText`＝`nextstep.reason(failCode).text`，`failCode` 為 null 時為 null；`applied=false` 而 `failCode` 為 null 時 `failCode` 記 `SANDBOX-NOT-APPLIED`、`failText` 取其白話）；`verify` 取最近一筆，鍵恰 `{seq,id,verdict,baselineRed,patchedGreen,mutatedRed,probesN,carrierProof,reasons}`，其中 `baselineRed`／`patchedGreen`／`mutatedRed`／`carrierProof` 型別皆為 `bool｜null`（取自事件原值，不轉字串），`probesN` 為 int；`reasons` 為 `[{code,text}]`；rev 不同的事件不取 | 取最早一筆或跨 rev ⇒ 紅 |
| AT-747-5-2 | RD | `verify.reasons[].code` 序列等於 `verdict.verdict_of(sandbox, verify, freeze, min_heldout)` 對同事件的第二回傳值（n=4、min=5 夾具含 `HELDOUT-TOO-SMALL`）；`text` 取自 `nextstep.reason(code).text`；事件記錄的 `reasons` 與重算不同時以**重算**為準 | 直接抄事件 `reasons`、或自寫判準 ⇒ 紅 |
| AT-747-5-E-1 | RD | 無 `app.sandbox`／`app.verify`（PROP 為 `approved`）⇒ `sandbox:null`、`verify:null`；`verify` 有而 `sandbox` 缺（損壞帳本）⇒ `verify.reasons` 照算（`sandbox=None` 走 `verdict_of` 的 `SANDBOX-NOT-APPLIED`）、不拋例外 | 缺 sandbox 時拋例外 ⇒ 紅 |

### AC-SI-47-6 下一步 `next`（RD）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-747-6-1 | RD | `nextstep.of(fold, prop, params)` 對附錄 A.2 的**每一列**（含 PASS／NE／FAIL 三種 verified 變體）各一夾具 ⇒ `code`、`who` 逐列相等、`text` 非空單行 ≤80 字元；`who` ∈ {掌舵者、巡邏器、無人運轉、主機管理者、無} | 任一列的 code／who 被改 ⇒ 該列紅 |
| AT-747-6-E-1 | RD | 未知狀態字串 ⇒ `{"code":"UNKNOWN-STATE","who":"無","text":…}`，不拋例外；`params` 缺 `min_heldout` ⇒ 不拋（`HELDOUT-BELOW-MIN` 不判） | 未知狀態 KeyError ⇒ 紅 |
| AT-747-6-2 | RD | `nextstep.of` 純函式性：同輸入兩次輸出相等；AST：`nextstep.py` 不 import `os`／`subprocess`／`socket`／`datetime.now`／`time`（不讀時鐘、不讀檔）；`export` 的 `detail.next` 與 `patrolreport` 對同 PROP（無本心跳 note）的 `props[].{code,who,text}` 相等（兩處共用同一函式） | 兩處各自實作 ⇒ 紅 |

### AC-SI-47-7 時間線（RD）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-747-7-1 | RD | PROP 有 `prop`、`card`、`dec(approve)`、`heldout.freeze`、`app.sandbox`、`app.verify`、`dec(promote)` 與另一 PROP 的事件 ⇒ `timeline` 依 `seq` 升冪、只含提到本 PROP 的事件（`prop`＝自己、`id`＝自己）、每筆鍵恰 `{seq,t,by,kind,action}`；`action` 取 `issuemap.event_label(kind)`，`dec` 為 `DEC_PREFIX`＋`dkind_label`；研究類事件不入 | 混入他 PROP 事件、或排序錯 ⇒ 紅 |
| AT-747-7-E-1 | RD | 事件 `kind` 不在 `EVENT_LABELS`（夾具注入）⇒ `action` 為 `kind` 原字串、不拋例外；單一 PROP 事件超過 500 筆 ⇒ 取**最後** 500 筆（`ne` 多 `TIMELINE-TRUNCATED`） | 未知 kind 拋例外、或不設上限 ⇒ 紅 |

### AC-SI-47-8 快照寫入（RD）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-747-8-1 | RD | `patrol` 一次心跳（`Deps` 替身）後 `<si>/console_report/patrol.json` 存在；UTF-8 無 BOM、LF、結尾一個 LF、`json.loads` 通過；頂層鍵集合恰 §2.2 所列；`schema_rev==1`；`ledger_seq`＝該心跳結束時事件帳本最大 `seq`（無事件＝0）；`generated_at` 帶 offset；`heartbeat_minutes`＝`params.json` 值；`console_report/` 下無 `.tmp` 殘留；**寫快照不新增 stdout 的 `step=` 行、`--json` 的 `steps` 長度仍為 5**（巡視、入帳、到期、運轉、推進；P4 AT-436-3-1 維持成立），快照 `steps[]` 即這五項 | 缺鍵、`ledger_seq` 取開頭值、naive 時間、輸出第六個 step ⇒ 紅 |
| AT-747-8-2 | RD | **原子性**：`os.replace` 注入 `PermissionError` ⇒ 舊 `patrol.json` 位元組不變、無 `.tmp` 殘留、日誌多一行 `code=REPORT-WRITE-FAILED`、`patrol` rc 與無注入時相同（不因快照失敗而改變 rc）；注入 `OSError` 於目錄建立 ⇒ 同 | 失敗時留半截檔或改 rc ⇒ 紅 |
| AT-747-8-3 | RD | **大小**：`ingest` 250 筆被拒＋`props` 300 筆 ⇒ 序列化位元組 ≤ `patrolreport.REPORT_MAX_BYTES`（524288）、`ingest`／`props` 各截至前 200 筆、頂層 `truncated:true`；未超界 ⇒ `truncated:false`；`text` 欄一律單行且 ≤120 字元 | 無上限或不標 `truncated` ⇒ 紅 |
| AT-747-8-4 | RD | **新鮮度**：`patrolreport.is_stale(report, now)`＝`now - generated_at > 2×heartbeat_minutes + 5 分`（嚴格大於）：恰等於界 ⇒ False、多 1 秒 ⇒ True；`generated_at` 缺或非 ISO ⇒ True（fail-closed）；`now` naive ⇒ `ValueError` | 用 ≥、或缺欄判 False ⇒ 紅 |
| AT-747-8-E-1 | RD | `patrol --dry-run` ⇒ 不寫 `console_report/`（目錄不存在則不建）；`AUTOSDD_UNATTENDED` 有設 ⇒ rc 1 `UNATTENDED-REFUSED`、不寫快照；取不到 `patrol.lock`（他心跳在跑）⇒ rc 0、不寫快照（舊檔保留） | dry-run 寫檔 ⇒ 紅 |
| AT-747-8-E-2 | RD | **未預期例外**：`launch_all` 注入例外（心跳進 `PATROL-EXCEPTION`）⇒ 仍寫快照，`steps[]` 末項 `result` 含 `PATROL-EXCEPTION`；快照已含例外前各步的 `ingest`／`props` 資料 | 例外時不寫快照 ⇒ 紅 |

### AC-SI-47-9 快照 `ingest[]`（RD）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-747-9-1 | RD | 稽核目錄三檔：①`decide` 的卡面過期（`STALE-CARD`）②`obs-add` 金鑰環空（`AUDIT-KEY-MISSING`）③`obs-add` 合法 ⇒ 心跳後 `ingest[]` 恰兩筆（③已入帳不出現）；①＝`{audit_ref,kind:"decide",status:"rejected",code:"STALE-CARD",text,permanent:true}`；②＝`status:"deferred"`、`permanent:false`；鍵恰此六個；`text`＝`nextstep.reason(code).text` | 入帳成功者也列出、或 permanent 判反 ⇒ 紅 |
| AT-747-9-2 | RD | **無狀態**：同一被拒稽核檔連續兩次心跳 ⇒ 兩次 `ingest[]` 皆含它（不因日誌去重而消失）；修好（補金鑰）後第三次心跳該筆消失且事件帳本多一筆 `obs.add`；`patrol.log` 仍只記一次拒收（沿既有去重） | 因日誌去重而從快照消失 ⇒ 紅 |
| AT-747-9-E-1 | RD | 稽核檔 `kind` 不在 `consoleaudit.KINDS`（`kind:null`）⇒ `code:"AUDIT-KIND-UNKNOWN"`、`kind:null`；未列於附錄 A.1 的碼 ⇒ 落 `nextstep.reason` 的通用列（`permanent:true`、`who:"主機管理者"`、`text` 含該碼原字串）；`console_pending` 量不到（目錄不存在以外的原因）⇒ `ingest:[]` 且 `steps[]` 入帳項 `result` 含「量不到」 | 未知碼拋例外 ⇒ 紅 |
| AT-747-9-3 | RD | `permanent` 判準表（附錄 A.1 逐碼）：`AUDIT-KEY-MISSING`、`AUDIT-KEY-UNKNOWN`、`LOCK-BUSY`、`LEDGER-WRITE-FAILED`、`HOME-UNWRITABLE`、`GIT-UNAVAILABLE`、`STATE-CHANGED` 為 false，其餘列出碼皆 true（**含 `AUDIT-REF-REUSED`**：已入帳的編號不會再入帳，P4 D-IMP-6 (4)）；`reason(code).permanent` 逐碼等於表 | 表與程式不同步 ⇒ 紅 |

### AC-SI-47-10 快照 `props[]`（RD）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-747-10-1 | RD | 帳本含 `proposed`、`approved`（無凍結）、`approved`（已凍結 n<min）、`sandboxed`、`verified`（已發卡、無晉升決定）、`returned`、`rejected`（冷卻中）、`measuring`、`closed` 各一 PROP ⇒ `props[]` 含前七者與（若 `measuring` 有待回滾）該者；**不含** `closed` 與無待回滾的 `measuring`；每筆鍵恰 `{id,state,code,who,text}`；`code`／`who` 等於附錄 A.2 對該狀態的列 | 列出已終態者、或漏列 `returned` ⇒ 紅 |
| AT-747-10-2 | RD | 本心跳的 note 覆蓋帳本推導：`approved`＋已凍結的 PROP 在工作樹髒時被 `promote` 前置擋下（`verified`＋`dec(promote)` 夾具）⇒ `code:"dirty-tree"`（附錄 A.3）、`who:"主機管理者"`；`sandbox` 被拒（`first_code` 為 `SANDBOX-…`）⇒ `code` 為該碼；`COMMIT-FAILED`（commit hook 拒）⇒ 該 PROP `code:"COMMIT-FAILED"`；note 只活一個心跳：下一心跳無 note 時退回帳本推導 | note 跨心跳殘留或不覆蓋 ⇒ 紅 |
| AT-747-10-3 | RD | `Ctx.notes`：`_advance_prop` 的每個提前 `return` 點（`NO-HELDOUT`、`dirty-tree`、`PUSH-IN-PROGRESS`、`MEMORY-DIR-UNRESOLVED`、`_step` 失敗）皆呼叫 `ctx.note(pid, code, detail)`；AST：`patrolrun._advance_prop` 內每個 `ctx.log("推進", …, <非 None 的碼>, …)` 與其同分支的 `ctx.note` 碼字面相同（對照表） | 只寫日誌不 note ⇒ 紅 |

### AC-SI-47-11 快照 `runs`、`push`、`off`（RD）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-747-11-1 | RD | 一個進行中無人運轉（`spawn.json` 存活、未逾牆；`run.open` trigger f）⇒ `runs.live` 一筆 `{run,purpose:"scheduled",started_at,wall_due_at}`；trigger a＋Console 載體 ⇒ `purpose:"console"`；其他 ⇒ `"manual"`；已 `closed_at` 者不列；`runs` 鍵集合恰 `{live,waiting,queued}`，`runs.queued` 恆為 `[]`（第二波預留鍵，W1 不得有元素；W2 元素形狀見 §2.2） | 缺 `queued` 鍵、或列出已結案運轉 ⇒ 紅 |
| AT-747-11-2 | RD | `AUTOSDD_SI_PATROL_OFF` 有設 ⇒ 心跳仍寫快照：`off:true`、`ingest:[]`、`props:[]`、`runs`（`live`／`waiting`／`queued` 皆 `[]`）、`schedule:null`、`steps:[]`、`push.state:"off"`、`generated_at` 為本次時間；未設 ⇒ `off:false`；**OFF 路徑的副作用邊界（P4 AT-436-5-E-1 不變）**：不取 `locks/patrol.lock`（鎖檔不存在）、不呼叫 `pushguard`（git 呼叫 0 次）、`patrol.log` 恰增既有的一行 `code=PATROL-OFF`（快照寫入成功不另加日誌行；寫入失敗才加 `REPORT-WRITE-FAILED` 一行）、repo 位元組不變 | OFF 時不寫快照、或取鎖、或多寫日誌行 ⇒ 紅 |
| AT-747-11-3 | RD | `push` 區塊鍵集合恰十個 `{enabled,state,code,text,retry,sha,ahead,attempts,finished_at,tick_at}`（§2.2 為準）；型別：`enabled` bool、`state`／`code`／`text` **恆為非空 str**、`retry` 為 `wait｜exhausted｜never｜null`、`sha` str｜null、`ahead` int、`attempts` int、`finished_at`／`tick_at` ISO str｜null；各狀態取值由 AT-749-10-* 逐一驗 | 鍵集合不符、或 `code`／`text` 出現 null ⇒ 紅 |

### AC-SI-47-12 白話表單一家（RD）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-747-12-1 | RD | `nextstep.REASON` 含附錄 A 每個碼（A.1 入帳、A.2 狀態、A.3 巡邏器、A.4 推送、A.5 驗證 reasons 與沙盒碼、A.6 排程跳過與運轉等待、A.7 匯出 `ne` 新碼）；每筆鍵 `{who,permanent,text}`；`text` 單行、非空、≤80 字元、不含 `｜`、含至少一個 CJK 字元；`who` ∈ 五值 | 缺碼或空白話 ⇒ 紅 |
| AT-747-12-2 | RD | `nextstep.reason("<任意未登記碼>")` ⇒ 通用列；`reason(code, detail="x"*300)` ⇒ `detail` 截至 80 字元並去除換行與 `｜`；`text` 內 `{detail}` 占位被填、無殘留花括號 | detail 不消毒 ⇒ 紅 |
| AT-747-12-3 | RD | **單一家**：全 `tools/lib/selfimproving/` 的字串常數中，附錄 A 白話句的前 8 個字元只出現在 `nextstep.py`（AST 掃字串常數；`patrolreport`、`propdetail`、`patrol*`、`pushguard` 皆不內嵌白話）；`patrolreport` 與 `propdetail` 以 `nextstep.reason` 取字 | 他檔複製白話 ⇒ 紅 |

### AC-SI-47-13 `heldout-freeze` 低於下限只警告（RD）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-747-13-1 | RD | held-out 目錄 manifest 的 `cases` 為 4 筆、`min_heldout`=5 ⇒ `heldout-freeze` rc 0、`heldout.freeze` 事件照寫（`n=4`）、**stdout 與無警告時逐字同形**（同一夾具改 5 筆對照：stdout 僅 `n`、`digest` 之值不同）、stderr 含一行 `warn HELDOUT-BELOW-MIN n=4 min=5`；n=5 ⇒ stderr 無此字樣 | 拒收（rc 1）、或警告進 stdout ⇒ 紅 |
| AT-747-13-E-1 | RD | `--json` 模式 ⇒ stdout 仍是單一 JSON（鍵與無警告時相同），警告只在 stderr；卡面核心區（`card`）位元組與修改前相同（對照既有卡面黃金夾具）；`params.json` 讀不到 `min_heldout` ⇒ 不印警告、不拒收 | 警告混入 JSON 或改動卡面 ⇒ 紅 |

### AC-SI-47-14 SOP 勘誤與補句（RD）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-747-14-1 | RD | 以 SOP 標題切段（`section(text, "<標題>")`，LF 正規化）判：〈held-out 目錄〉含 `min_heldout`、`HELDOUT-TOO-SMALL`、`NO-PROBES`、`warn HELDOUT-BELOW-MIN` 四片段；〈提案檔〉含 `RUN-NOT-OPEN`、`RESEARCH-MISSING` 兩前置碼；〈無人運轉任務書範本〉第 7 步（凍結者）含 `<MIN_HELDOUT>` 與「驗證必判 NE」；`patrolbrief.template_problems(sop)`、`_selfimproving_fixtures.sop_problems`、`_selfimproving_p5_fixtures.sop_p5_problems` 皆回空 | 任一片段缺 ⇒ 紅 |
| AT-747-14-2 | RD | 範本新占位符 `<MIN_HELDOUT>` 由 `patrolrun.compose` 填入 `params.json` 的 `min_heldout` 值（夾具 5 ⇒ 任務書含「下限 5」）；`template_problems` 對「缺 `<MIN_HELDOUT>`」的範本回非空；任務書不含其他迴圈層量測值（既有判準不退化） | `compose` 漏填占位符 ⇒ 任務書留 `<MIN_HELDOUT>` 紅 |
| AT-747-14-E-1 | RD | SOP 不得再含「`sched_auto_push` 只准 false」字樣；〈巡邏與無人運轉（P4）〉節開頭句改為「巡邏器本體不 push；推送由〈自動推送（P7）〉的互動登入任務執行」；新節〈自動推送（P7）〉〈巡邏快照與 M 類自動推進（P7）〉存在且位於〈無人運轉任務書範本〉**之前**（`patrolbrief.template_of` 取圍欄不受影響） | 舊字樣殘留或新節放在範本之後 ⇒ 紅 |

### AC-SI-47-15 快照 `schedule` 與 `runs.waiting`：為什麼沒有啟動運轉（RD）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-747-15-1 | RD | 一次心跳後快照 `schedule` 鍵集合恰 `{enabled,current,last_skip}`：`enabled`＝`sched.state_of` 的啟用旗標；`current`＝本心跳 `patrol.due` 的結果 `{code,text}`：停用⇒`SCHED-DISABLED`、本格已有 (f)⇒`SCHED-CELL-RAN`、七種跳過原因成立⇒`SKIP-BLACKOUT`／`SKIP-QUOTA-BAND`／`SKIP-OTHER-DRIVER`／`SKIP-DIRTY-TREE`／`SKIP-RUN-OPEN`／`SKIP-SPAWN-FAILED`（`disabled` 對 `SCHED-DISABLED`）、到期且全不成立⇒`SCHED-DUE`；`last_skip`＝事件帳本最近一筆 `sched.skip` 的 `{seq,t,code,text,audit_ref}`（`reason` 對映為 `SKIP-*`；`audit_ref` 為該事件的 Console 稽核編號或 null），無則 null；`text` 取 `nextstep.reason`（附錄 A.6） | 缺碼、或用自由文字取代碼 ⇒ 紅 |
| AT-747-15-2 | RD | **Console「立即啟動」被消耗成跳過**：已有未關運轉時入帳一筆 `run-request` ⇒ 帳本多一筆 `sched.skip(run-open, carrier=console, audit_ref=<ref>)`；快照 `schedule.last_skip.code`＝`SKIP-RUN-OPEN`、`audit_ref`＝該稽核編號、`text` 含「已有未關運轉」與運轉編號與「第二波起可由 Console 處理」；**只顯示，行為不變**（仍記 `sched.skip`、不開運轉，P4 R146／R156 不動；AT-436-* 全綠） | 改變消耗行為、或快照看不出被消耗 ⇒ 紅 |
| AT-747-15-3 | RD | `runs.waiting[]`＝已 `run.open`、尚未 spawn 的巡邏器運轉（`patrol._pending`）：每筆 `{run,code,text}`，`code`∈`SKIP-*`（該運轉本心跳被 `decide_skip` 擋）或 `RUN-BUSY`（已有進行中無人運轉而延後 spawn）；已 spawn 者不在此；本心跳 `launch_all` 的被擋原因以 `Ctx.run_notes[run]` 傳遞（與 `Ctx.notes` 同形，只活一個心跳） | 只寫日誌不進快照 ⇒ 紅 |
| AT-747-15-E-1 | RD | `AUTOSDD_SI_PATROL_OFF` 或 `--dry-run` ⇒ 不產 `schedule`（OFF 為 null）；`due()` 拋例外 ⇒ `schedule.current` 為 null、其餘欄仍寫；附錄 A.6 的 `text` 皆單行、≤80 字元 | 例外時整份快照不寫 ⇒ 紅 |
### AC-SI-48-1 M 類帶 `--memory-dir`（MM）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-748-1-1 | MM | `p7x.repo_m()`：M 類 PROP `approved`＋已凍結；`claude_home()` 指向暫存、`transcript_dir(repo)/memory/` 內有 `MEMORY.md`；`Deps.verbs` 記錄 argv。一次心跳 ⇒ 記錄含 `["sandbox", PROP, "--memory-dir", <解析路徑>, "--by", "patrol", "--repo", …]`；續跑 `sandboxed` ⇒ `verify … --memory-dir <同>`；`verified`＋`dec(promote)` ⇒ `promote … --memory-dir <同>`；`promoted`＋`dec(rollback)` ⇒ `rollback … --memory-dir <同>`；`card --issue` **不帶** `--memory-dir` | 任一動詞漏旗標、或 P 類帶旗標 ⇒ 紅 |
| AT-748-1-2 | MM | `memdir.resolve(repo)`＝`str(transcript.transcript_dir(repo) / "memory")` 且 `is_dir()` 且含 `MEMORY.md` 才回，否則 `None`；slug 與 `transcript_dir` 同式（`repo.resolve()`、非英數轉 `-`）；Windows 與 POSIX 路徑各以注入的 `claude_home` 驗（不依賴本機平台） | 自寫 slug 規則 ⇒ 與 `transcript_dir` 不一致紅 |
| AT-748-1-E-1 | MM | P 類 PROP（對照組）一次心跳 ⇒ 任何動詞 argv 都不含 `--memory-dir`；M 類 PROP 為 `proposed`／`returned`／`rejected` ⇒ 不呼叫任何動詞、不解析記憶目錄（`memdir.resolve` 呼叫 0 次） | 無待辦也解析 ⇒ 紅 |

### AC-SI-48-2 解析不到記原因碼（MM）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-748-2-1 | MM | 記憶目錄不存在／存在但無 `MEMORY.md`／是檔案 ⇒ 三子案皆：不呼叫 `sandbox`／`verify`／`promote`／`rollback`（`verbs` 記錄零 M 類推進動詞）、`ctx.notes[PROP]`＝`MEMORY-DIR-UNRESOLVED`、快照 `props[]` 該筆 `code:"MEMORY-DIR-UNRESOLVED"`、`who:"主機管理者"`、`text` 含解析後的路徑；日誌一行 `code=MEMORY-DIR-UNRESOLVED`（同心跳每 PROP 一行） | 仍呼叫動詞而不帶旗標（會得 `MEMORY-DIR-MISSING`）⇒ 紅 |
| AT-748-2-E-1 | MM | 舊碼 `MEMORY-DIR`（「須人工給 --memory-dir」）不再由 `patrolrun` 產生（AST：字串常數 `"MEMORY-DIR"` 在 `patrolrun.py` 零出現）；`ledger` 內舊日誌行不影響快照 | 舊碼殘留 ⇒ 紅 |

### AC-SI-48-3 無互動視窗安靜前置（MM）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-748-3-1 | MM | `Deps.driver_quiet` 回 False（近期有對話）⇒ M 類 `verified`＋`dec(promote)` 照常呼叫 `promote --memory-dir`（與 P 類對照組結果相同）；快照**不含**任何 `OTHER-DRIVER-M` 碼（附錄 A 無此碼；`nextstep.REASON` 不含它） | 為 M 類加 other-driver 前置 ⇒ 紅 |

### AC-SI-48-4 前像與後像（MM）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-748-4-1 | MM | 記憶檔在 `verify` 之後被他人改過（pre-image 不符）⇒ `promote` 回 `PREIMAGE-MISMATCH`（既有判準）⇒ `ctx.notes`＝該碼、`who:"主機管理者"`、`text` 含「重新上卡」；不重試、不寫 `app.promote`、不 commit；下一心跳記憶仍不符 ⇒ 同碼（無狀態） | 吞掉拒收碼 ⇒ 紅 |
| AT-748-4-2 | MM | **後像**：M 類 promote 成功後 `memdir.post_image_problems(repo, events, PROP, mem)` 以 `manifest.paths_manifest(mem, touched, strip="memory/")` 重算並與 `app.promote.post_sha256` 比對：相符 ⇒ 回 `None`；promote 之後立即有人改記憶檔（夾具於 `promote` 與驗證之間注入）⇒ `POSTIMAGE-MISMATCH`，`ctx.notes` 記之、日誌一行；**不自動回滾**（無 `rollback` 呼叫）、`measure` 仍照做、commit 仍照做 | 不驗後像、或不符時自動回滾 ⇒ 紅 |
| AT-748-4-E-1 | MM | P 類 PROP 的 promote 不呼叫 `post_image_problems`（零次）；M 類 `rollback` 成功後同樣驗後像（對 `app.rollback.post_sha256`），不符 ⇒ `POSTIMAGE-MISMATCH` | P 類也驗 ⇒ 紅 |

### AC-SI-48-5 回歸（MM）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-748-5-1 | MM | D-IMP-9 (d) 回歸：M 類 `promoted`／`measuring`／`closed` 且無待回滾 ⇒ 零動作、零日誌碼、`props[]` 不含（measuring 無待回滾不列）、不解析記憶目錄；`verified` 的 M 類未發卡 ⇒ 呼叫 `card --issue`（不再被 `MEMORY-DIR` 擋）且只一次；已發卡、無決定 ⇒ 零動作 | 已晉升 M 類每心跳報碼，或 verified M 類不發卡 ⇒ 紅 |
| AT-748-5-2 | MM | 完整鏈：M 類 `approve`→（心跳 1）sandbox→verify→card；掌舵者 `dec(promote)` 入帳→（心跳 2）promote→commit（trailer 兩行）→measure；快照 `props[]` 在心跳 1 後為 `WAIT-PROMOTE-DECISION`、心跳 2 後 PROP 離開 `props[]`（measuring 無待回滾） | 鏈中斷 ⇒ 紅 |

### AC-SI-49-1 參數（PU）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-749-1-1 | PU | 真 `params.json` 與 `params.PARAM_SPECS`：兩者鍵集合相等且共 47 個；頂層鍵依位元組序；`sched_auto_push` 為 `true`（型別 `bool`）、`sched_push_wall_minutes` 45、`sched_push_attempts_max` 3、`sched_push_retry_minutes` 360；`param_findings(真值)` 為空；對真 repo `check` 的 `params.keys` 為 `PASS`；`SCHED_KEYS` 含四個新鍵（`sched_` 前綴）；`params.json` 位元組 UTF-8 無 BOM、LF、結尾換行 | 鍵缺或預設值錯 ⇒ 紅 |
| AT-749-1-E-1 | PU | 負控（一次改一處）：`sched_auto_push` 為整數 1 ⇒ `PARAM-TYPE`；**為 true／false 皆無問題**（P4 AT-440-2-E-1 的「true 紅」已勘誤）；`sched_push_wall_minutes` 為布林 ⇒ `PARAM-TYPE`；為 0 ⇒ `PARAM-RANGE`；121 ⇒ `PARAM-RANGE`（跨鍵上限 120）、120 ⇒ 無問題；`sched_push_attempts_max` 0 ⇒ `PARAM-RANGE`；`sched_push_retry_minutes` 0 ⇒ `PARAM-RANGE`；缺各鍵 ⇒ `PARAM-MISSING` | 上限未判、或 true 仍紅 ⇒ 紅 |
| AT-749-1-2 | PU | 指紋與基準檔：`fingerprint` 在 `params.json` 改動後換代（預期；`FINGERPRINT_EXCLUDED` 不含 `params.json`）；`docs/06_quality/SelfImproving_LedgerDb_P0_Baseline.md` 的 `params.json` 列（位元組數、sha256）等於磁碟現值（沿 P5 活值更新先例）；`metrics.md`、`research_sources.json`、`research_registry.json` 位元組不變 | 基準檔未同步 ⇒ P0 基準測試紅 |

### AC-SI-49-2 commit trailer（PU）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-749-2-1 | PU | 夾具 repo（本機 bare 遠端）：`verified`＋`dec(promote)`，`sched_auto_commit` 為 true，promote 成功 ⇒ 產生的 commit 訊息：首行 `chore(selfimproving): promote <PROP>（<DEC>、<APP>）`；本文**不含**「不 push」字樣；末段（空行後）恰兩個 trailer 行 `SI-Patrol-App: <APP>` 與 `SI-Patrol-Prop: <PROP>`，APP 為該次 `app.promote` 的 ID；`git interpret-trailers --parse` 可解析；rollback 同形（APP 取 `app.rollback`）；commit 成功後 `<si>/push/commits.jsonl` 多一行 `{"sha":"<40>","app":"<APP>","prop":"<PROP>","at":"<ISO+offset>"}`（`patrolreport.record_commit`；不在 repo 內） | 缺 trailer、APP 取錯事件或不記紀錄 ⇒ 紅 |
| AT-749-2-E-1 | PU | 既有行為不退化：`sched_auto_commit=false` ⇒ 不 commit；commit hook 拒（rc 1）⇒ `COMMIT-FAILED` 日誌、OBS 草稿、不重試、不 `--no-verify`（`git commit` argv 不含旁路旗標）；`_commit` 仍只 `git add` 白名單路徑 | 加 `--no-verify` 或 `git add -A` ⇒ P4 AT-438-5-* 與本 AT 紅 |
| AT-749-2-2 | PU | **`_commit` 與守門共用同一份允許清單（R-25、R-28）**：`pushguard.commit_allow(prop, touched, cls)` 為單一來源，回（事件帳本、OBS 帳本、`docs/06_quality/SelfImproving_Proposals/<該 PROP>/`、〔非 M 類〕該 PROP 位於 repo 內的 `touched` 檔）；`patrolrun._commit` 的 `git add` 與 `git commit` 範圍＝此清單中真有改動者（AST：`_commit` 不再含字面 `PROPOSALS_REL` 整目錄；`git commit` 帶 pathspec `-- <changed>`，不吃整個 index）。夾具（**只放 `sched.dirty_paths` 會排除的 SI 自有路徑，使 promote 與守門都不先被 `dirty-tree`／`PUSH-DIRTY-TREE` 擋住**；`dirty_paths` 排除 `sched._OWN_PREFIXES`＝事件帳本、提案目錄、OBS 帳本前綴、`research_registry.json`、回測目錄）：①另一個 PROP 的提案目錄有未提交檔；②`docs/06_quality/SelfImproving_Protocol/research_registry.json` 有**已暫存**（`git add`）的改動（在 `_OWN_PREFIXES` 內、不在 `commit_allow` 內）⇒ 先斷言 `sched.dirty_paths` 為空、promote 成功；`git show --name-only` 該巡邏提交只含本 PROP 路徑（①②皆不在內）；①②仍留在工作樹／index；`ctx.notes` 對該 PROP 記 `COMMIT-LEFTOVER`；隨後 `pushguard.evaluate` 回 `ok=True`（`dirty_paths` 仍為空），`push-run` 對本機 bare 遠端真推送成功（證明常態下不被 `PUSH-PATH-OUTSIDE` 擋） | `_commit` 加整個提案目錄或吃整個 index，或夾具含非自有髒檔使本 AT 不可通過 ⇒ 紅 |
| AT-749-2-3 | PU | **提交紀錄寫入（R-26 a）**：`patrolreport.record_commit` 在 `_commit` 成功後記 `{sha,app,prop,at}` 一行（O_APPEND、單行 JSON）；寫入失敗（注入 `OSError`）⇒ 日誌一行 `COMMIT-RECORD-FAILED`、`ctx.notes` 記之、**不重試、不回滾提交**；之後守門對該提交回 `PUSH-NOT-RECORDED`（安全側失敗，不推送） | 寫失敗仍可被自動推送 ⇒ 紅 |
| AT-749-2-4 | PU | **紀錄的 sha 來源（R-30）**：`record_commit` 的 `sha` 取自 `_commit` 在 `git commit` 成功後執行的 `git rev-parse HEAD`（完整 40 碼），不取 commit 前的值、不取訊息；斷言紀錄的 sha 等於 `git rev-parse HEAD` 與 `git log -1 --format=%H`。**誠實劃界子案**：夾具在 `git commit` 與 `git rev-parse HEAD` 之間插入一個他人提交 ⇒ 紀錄記到他人的 sha（與該提交 trailer 不符或該提交無 trailer），守門回 `PUSH-RECORD-MISMATCH`／`PUSH-FOREIGN-COMMITS`、不推送（安全側） | 紀錄 sha 取自 commit 前 ⇒ 紅 |
| AT-749-2-5 | PU | **`_commit` 先跑與守門同一套帳本差分規則（R-31）**：`pushguard.ledger_rule_problems(prop, changes)` 為單一函式（輸入＝每個變更路徑的（狀態、舊內容、新內容）；回 `None` 或違規描述），**`patrolrun._commit` 於 `git add` 之前**對「將要提交的差分」（HEAD 內容 vs 工作樹內容，限 `commit_allow` 內有改動者）呼叫它，**守門對每個領先提交（父 vs 該提交）呼叫同一個函式**（AST：兩處皆呼叫、全套件無第二份帳本規則實作）。正向：①OBS 追加兩列＋既有 open 列處置欄轉終值、②提案目錄新增檔、③事件帳本尾端追加 ⇒ `_commit` 照常提交 | 兩處各自實作規則 ⇒ 紅 |
| AT-749-2-E-2 | PU | **`COMMIT-LEDGER-RULE`（R-31）**：promote 成功後工作樹出現違規改動（①OBS 既有列的症狀欄被改寫、②事件帳本既有行被改、③本 PROP 提案目錄既有 `r1.md` 被改）各一子案 ⇒ `_commit` **不提交**（HEAD 不變、index 不變）、不寫 `commits.jsonl`、日誌一行 `code=COMMIT-LEDGER-RULE`、`ctx.notes` 記該碼（`who:"主機管理者"`，白話「帳本或提案檔有不合規則的改動，巡邏器沒有提交，請人工檢查」）、快照 `props[]` 帶出；`measure` 仍照做；不重試、不繞過；人工檢查後自行提交 | `_commit` 不先驗而照提交 ⇒ 紅 |

### AC-SI-49-3 守門判準：放行（PU）
**守門判準（`pushguard.evaluate`，對領先範圍每個提交逐一判；PRD AC-SI-49-3／49-4 為準）**：(i) 末段 trailer 區恰含 `SI-Patrol-App`、`SI-Patrol-Prop`；(ii) APP 為事件帳本中的 **`app.promote` 或 `app.rollback`** 且其 `prop` 等於 `SI-Patrol-Prop`；(iii) **一個 APP 恰對應一個提交**：領先範圍內同一 APP 至多一個提交，且 `origin/main` 的歷史中沒有任何提交帶同一 APP；(iv) 非 merge；(v) `git diff-tree` 路徑 ⊆「允許清單」＝**`pushguard.commit_allow(prop, touched, cls)`**（與 `patrolrun._commit` 共用的單一來源，R-25）＝（該 PROP 的 `touched` 中位於 repo 內者，M 類除外）∪ **`SI_OWN_ALLOW`**（明確清單，不是前綴泛稱：事件帳本 `docs/06_quality/SelfImproving_Event_Ledger.jsonl`、OBS 帳本 `docs/06_quality/SelfImproving_Observation_Ledger.md`、該 PROP 的提案目錄 `docs/06_quality/SelfImproving_Proposals/<PROP>/`；**不含** `sched._OWN_PREFIXES` 的其他路徑〔`research_registry.json`、回測目錄〕、他 PROP 的提案目錄、`params.json`）；M 類 PROP 的提交只准 `SI_OWN_ALLOW`；(vi) **內容綁定**：該提交的事件帳本 blob **新增了該 APP 的事件行**（父提交的 blob 不含、本提交的 blob 含，且父 blob 為本 blob 的位元組前綴＝追加式）；P 類另須該提交樹中 `touched` 路徑以 `manifest.paths_manifest` 同規則算出的 sha256 等於該 APP 事件的 `post_sha256`；(vii) **提交紀錄（R-26 a）**：`<si>/push/commits.jsonl`（SI 家目錄、不在 repo 內，由巡邏器 `_commit` 成功後經 `patrolreport.record_commit` 追加）中，每個領先提交的**完整 sha** 都有紀錄，且紀錄的 `app`、`prop` 等於該提交的 trailer；紀錄缺（含檔案缺席、寫入失敗）＝`PUSH-NOT-RECORDED`（白話「這個提交沒有巡邏器的紀錄，請人工檢查後推送」，安全側失敗），紀錄與 trailer 不符＝`PUSH-RECORD-MISMATCH`；amend、rebase 或照抄的提交 sha 不同，必被擋；(viii) **帳本差分規則（R-26 b）**：對每個領先提交對其父提交的 diff——事件帳本只准在尾端追加（父 blob 為前綴）；OBS 帳本只准追加新列，或把既有列的處置欄由 `open` 轉為終值一次（該列其餘欄位元組不變、不刪列、表頭不變）；該 PROP 提案目錄只准新增檔（`--diff-filter=A`），不准改、刪、改名既有檔；違反＝`PUSH-LEDGER-RULE`。判序（碼序）：`PUSH-FOREIGN-COMMITS`→`PUSH-NOT-RECORDED`→`PUSH-RECORD-MISMATCH`→`PUSH-APP-KIND-INVALID`→`PUSH-APP-REUSED`→`PUSH-PATH-OUTSIDE`→`PUSH-LEDGER-RULE`→`PUSH-CONTENT-MISMATCH`。

| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-749-3-1 | PU | `p7x.push_repo()`：`main` 追蹤 `origin/main`（本機 bare）、領先 2 個巡邏提交（一個 `app.promote`、一個 `app.rollback`；各帶兩 trailer、各自新增自己的 APP 事件行、帳本追加式、P 類觸及檔雜湊等於 `post_sha256`、路徑 ⊆ 允許清單、`commits.jsonl` 有各自完整 sha 的紀錄且 app／prop 相符、帳本差分規則皆合）、工作樹乾淨 ⇒ `pushguard.evaluate(...)` 回 `ok=True`、`sha`＝HEAD 全 40 碼、`ahead=2`；M 類 PROP 的提交（只含 `SI_OWN_ALLOW` 路徑、事件帳本新增其 APP 行）同樣放行 | 放行集合少算清單內路徑，或 APP 種類／綁定／紀錄／差分判準缺一 ⇒ 紅 |
| AT-749-3-2 | PU | **帳本差分規則的正向**：①OBS 帳本追加兩個新列＋把一個既有 `open` 列的處置欄轉為 `fixed@<sha>`（其餘欄位元組不變）；②提案目錄新增 `verify2.json`；③事件帳本尾端追加多筆（含他人寫入的合法事件）⇒ `evaluate` 放行 | 把合法追加判成違規（假紅）⇒ 紅 |

### AC-SI-49-4 守門判準：拒（PU；每一種繞過手法一條負向 AT）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-749-4-1 | PU | 逐子案（每案獨立夾具，其餘條件皆合）皆回 `code="PUSH-FOREIGN-COMMITS"` 且 `text` 含**第一個不符的 sha 前 8 碼**：①其中一個提交無 trailer；②trailer 的 APP 不在帳本；③APP 在帳本但 `app.prop` 不等於 `SI-Patrol-Prop`；④只有一個 trailer（缺 `SI-Patrol-Prop`）；⑤trailer 在訊息本文中段而非末段 trailer 區；⑥領先範圍含一個 merge commit | 任一子案放行 ⇒ 紅 |
| AT-749-4-E-1 | PU | **照抄格式、APP 取驗證證據**：人工／代理提交完整照抄巡邏提交的首行與兩 trailer，APP 取該 PROP 的 `app.sandbox` 或 `app.verify`（在帳本、prop 相符）⇒ `PUSH-APP-KIND-INVALID`、不放行 | 只判「APP 在帳本」⇒ 紅 |
| AT-749-4-E-2 | PU | **同一 APP 兩個提交**：巡邏提交之後再有一個照抄同一 APP trailer 的提交（含 `--allow-empty`）⇒ 判第二個 `PUSH-APP-REUSED` | 不判重複 ⇒ 紅 |
| AT-749-4-E-3 | PU | **APP 已在遠端歷史**：`origin/main` 已含一個帶同一 APP trailer 的提交，本機領先又一個帶同 APP 的提交 ⇒ `PUSH-APP-REUSED` | 只查領先範圍、不查遠端歷史 ⇒ 紅 |
| AT-749-4-E-4 | PU | **路徑在清單外（repo 內一般檔）**：提交除合法內容外多改 `README.md` ⇒ `PUSH-PATH-OUTSIDE` | 路徑判準放寬 ⇒ 紅 |
| AT-749-4-E-5 | PU | **SI 自有但不在明確清單**：提交多改 `docs/06_quality/SelfImproving_Protocol/research_registry.json`、他 PROP 的提案目錄檔、`docs/06_quality/SelfImproving_Protocol/params.json` 各一例 ⇒ 各回 `PUSH-PATH-OUTSIDE`（以前綴泛稱判會放行） | 以 `_OWN_PREFIXES` 前綴判 ⇒ 紅 |
| AT-749-4-E-6 | PU | **M 類提交夾帶 repo 內非清單路徑**：M 類 PROP 的提交含任一 `touched` 以外、`SI_OWN_ALLOW` 以外的檔（含該 PROP 的 `memory/…` 邏輯路徑被當成 repo 內路徑）⇒ `PUSH-PATH-OUTSIDE` | M 類沿用 P 類路徑集合 ⇒ 紅 |
| AT-749-4-E-7 | PU | **內容與結果摘要不符**：P 類提交的 `touched` 檔比 `post_sha256` 多改一行 ⇒ `PUSH-CONTENT-MISMATCH` | 不比對 `post_sha256` ⇒ 紅 |
| AT-749-4-E-8 | PU | **提交未新增該 APP 事件行**：照抄 trailer 掛在另一個只改 `touched` 檔（或無帳本變動）的提交上 ⇒ `PUSH-CONTENT-MISMATCH` | 只看 trailer 不看帳本差分 ⇒ 紅 |
| AT-749-4-E-9 | PU | **事件帳本被改寫**（紀錄存在、APP 相符，僅差分違規）：提交的事件帳本 blob 不以父 blob 為位元組前綴（既有行被改或刪）⇒ `PUSH-LEDGER-RULE` | 不驗追加式 ⇒ 紅 |
| AT-749-4-E-10 | PU | **判序與多違規**：領先 [巡邏、人工、巡邏] ⇒ 判第一個不符者（人工）的 sha；單一提交同時多違規時回碼序最前者（`PUSH-FOREIGN-COMMITS`→`PUSH-NOT-RECORDED`→`PUSH-RECORD-MISMATCH`→`PUSH-APP-KIND-INVALID`→`PUSH-APP-REUSED`→`PUSH-PATH-OUTSIDE`→`PUSH-LEDGER-RULE`→`PUSH-CONTENT-MISMATCH`）；全部不符時回最早者 | 判序錯 ⇒ 紅 |
| AT-749-4-E-11 | PU | 含空格與中文路徑的檔以 `-z`＋`-c core.quotepath=false` 解析正確（不被引號化路徑誤判）；git 對該提交的 `diff-tree`、`cat-file` 失敗 ⇒ `PUSH-GIT-UNAVAILABLE`（fail-closed，不放行） | 不用 `-z` 或失敗時 fail-open ⇒ 紅 |
| AT-749-4-E-12 | PU | **amend 改寫 OBS 既有列**：巡邏提交被 `git commit --amend`（sha 改變）後改了 OBS 帳本某既有列的症狀欄 ⇒ `PUSH-NOT-RECORDED`（新 sha 無紀錄）；另一子案：偽造紀錄使 sha 有紀錄且 app／prop 相符，但該提交把既有 OBS 列的非處置欄改寫 ⇒ `PUSH-LEDGER-RULE`；再一子案：既有列處置欄由終值改成另一終值（第二次改）⇒ `PUSH-LEDGER-RULE`；刪列或改表頭同判 | 只判路徑不判內容 ⇒ 紅 |
| AT-749-4-E-13 | PU | **amend 夾帶檔**：巡邏提交被 amend 夾帶一個在允許清單內的檔（本 PROP 提案目錄新增 `x.txt`）⇒ `PUSH-NOT-RECORDED`；夾帶改既有提案檔（紀錄被偽造的子案）⇒ `PUSH-LEDGER-RULE` | amend 後仍被放行 ⇒ 紅 |
| AT-749-4-E-14 | PU | **紀錄檔缺席**：`commits.jsonl` 不存在或為空、其餘條件皆合 ⇒ `PUSH-NOT-RECORDED`、不推送；損壞 JSON 行不視為紀錄 | 缺紀錄時 fail-open ⇒ 紅 |
| AT-749-4-E-15 | PU | **紀錄與 APP 不符**：紀錄的 `app` 或 `prop` 與提交 trailer 不同 ⇒ `PUSH-RECORD-MISMATCH`；同一 sha 有多筆紀錄且最後一筆不符亦同 | 只查 sha 存在 ⇒ 紅 |
| AT-749-4-E-16 | PU | **紀錄寫入失敗＝安全側、終局**：AT-749-2-3 的提交（紀錄寫入被注入失敗）⇒ `evaluate` 回 `PUSH-NOT-RECORDED`，`push-run` 不呼叫 `run_argv`；**沒有任何補寫紀錄的機制**（程式與 SOP 皆無該動詞／旗標；AST：`record_commit` 只被 `patrolrun._commit` 呼叫），`PUSH-NOT-RECORDED` 對自動推送是終局，只能由人檢查後手動 `git push`；**提交與寫紀錄之間巡邏被殺**（夾具：`_commit` 在 `git commit` 成功後、`record_commit` 前拋例外／行程終止）⇒ 下次心跳 `evaluate` 一樣回 `PUSH-NOT-RECORDED`（安全側） | 存在補寫機制或寫失敗仍被推送 ⇒ 紅 |
| AT-749-4-E-17 | PU | **提案目錄改既有檔**：提交改動本 PROP 提案目錄已存在的 `r1.md`（紀錄被偽造的子案）或他 PROP 目錄任一檔 ⇒ `PUSH-LEDGER-RULE`（他 PROP 目錄＝`PUSH-PATH-OUTSIDE` 先判） | 提案目錄放寬為可改 ⇒ 紅 |
### AC-SI-49-5 前置序（PU）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-749-5-1 | PU | 逐條件單獨成立、其餘皆合，`evaluate` 的 `code` 依序為：`sched_auto_push=false`⇒`PUSH-OFF`；分支為 `feature`⇒`PUSH-NOT-MAIN`；無上游或上游非 `origin/main`⇒`PUSH-NOT-MAIN`；領先 0⇒`PUSH-NOT-AHEAD`（`state:"idle"`）；`push/current.json` 存活⇒`PUSH-RUNNING`；工作樹有非 SI 自有改動（`sched.dirty_paths`）⇒`PUSH-DIRTY-TREE`；有外來提交⇒`PUSH-FOREIGN-COMMITS`（含 AC-SI-49-4 的 `PUSH-NOT-RECORDED`／`PUSH-RECORD-MISMATCH`／`PUSH-APP-KIND-INVALID`／`PUSH-APP-REUSED`／`PUSH-PATH-OUTSIDE`／`PUSH-LEDGER-RULE`／`PUSH-CONTENT-MISMATCH` 專屬碼，皆屬 `blocked`） | 序錯或漏碼 ⇒ 紅 |
| AT-749-5-E-1 | PU | **先中者定案**：同時 `PUSH-OFF` 與 `PUSH-DIRTY-TREE` ⇒ `PUSH-OFF`；同時 NOT-MAIN 與 DIRTY ⇒ NOT-MAIN；同時 DIRTY 與 FOREIGN ⇒ DIRTY；git 不可用／逾時 ⇒ `PUSH-GIT-UNAVAILABLE`（不拋例外、不放行） | 例外外洩或 fail-open ⇒ 紅 |

### AC-SI-49-6 推送執行形態（PU）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-749-6-1 | PU | `push-run`（`runner.run_argv` 替身記錄 argv／env／timeout／cwd）於守門放行時：argv 恰為 `["git","-C",<repo>,"push","origin","<HEAD 40 碼>:refs/heads/main"]`（逐元素）；不含 `--force`、`-f`、`--force-with-lease`、`--no-verify`、`--delete`、`HEAD`（裸字）；env **不含** `AUTOSDD_UNATTENDED`、`AUTOSDD_SI_PATROL_RUN`、`AUTOCLAUDE_SKIP_HOOKS`、`GIT_DIR`／`GIT_WORK_TREE`／`GIT_INDEX_FILE`，**含** `GIT_TERMINAL_PROMPT=0` 與 `GCM_INTERACTIVE=never`，並含父環境的 `PATH`、`HOME`／`USERPROFILE`、`APPDATA`、`LOCALAPPDATA`、`SYSTEMROOT`（存在者）；`timeout`＝`sched_push_wall_minutes×60`；`cwd`＝repo | 推 `HEAD` 字面或帶旁路旗標 ⇒ 紅 |
| AT-749-6-2 | PU | 真 git（夾具 bare 遠端）：放行後 `push-run` rc 0、遠端 `refs/heads/main` 前進至該 sha、`push/results/<sha12>.json` 為 `PUSH-OK`；**推明確 sha**：守門之後、push 之前注入「HEAD 再多一個人工提交」（`pushguard`／`patrolpush` 間的注入縫）⇒ 遠端只前進到守門時的 sha（不含人工提交） | 推 HEAD 而非 sha ⇒ 紅 |
| AT-749-6-3 | PU | **閘門期間工作樹變動（R-14）**：`run_argv` 替身於執行中新增一個 `sched.dirty_paths` 會回報的未提交檔，推送結束（成功或失敗）後 `push-run` 再查一次 `sched.dirty_paths`：變髒 ⇒ 結果檔 `tree_changed:true` 且 `text` 附註「閘門期間工作樹有變動」，**碼不變**；乾淨 ⇒ `tree_changed:false`；守門「工作樹乾淨」＝`sched.dirty_paths` 為空（該函式已排除 `sched._OWN_PREFIXES` 的 SI 自有路徑：事件帳本、提案目錄、OBS 帳本前綴、`research_registry.json`、回測目錄；偏離裁決 2 字面「乾淨」的 WHY：巡邏器自己的寫入必然使這些路徑髒，見 PRD AC-SI-49-5） | 不復查、復查結果改變碼，或乾淨判準與 `sched.dirty_paths` 不同 ⇒ 紅 |
| AT-749-6-E-1 | PU | AST：全套件 `"push"` 作為 git 子命令字面只出現在 `patrolpush.py`；`patrol.py`、`patrolrun.py`、`patrolbrief.py`、`schedarm.py`、`sched.py`、`schedwrite.py`、`pushguard.py` 零出現（P4 AT-438-7-1 的 `V-PUSH` 判準不退化）；`patrolpush.py` 內 `subprocess` 字樣零出現（只經 `runner.run_argv`） | 在巡邏檔內推送 ⇒ 紅 |

### AC-SI-49-7 結果分類碼（PU）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-749-7-1 | PU | `pushguard.classify(rc, timed_out, output)` 表驅動（輸出取自真 git 的逐字樣本，隨測試檔提交）。**判序＝先 hook 標記**：①`timed_out` ⇒ `PUSH-WALL-EXCEEDED`；②rc 0 ⇒ `PUSH-OK`；③輸出含 `[pre-push dispatcher]` 標記時，取**最後一個含該標記的行之後的尾段**：尾段含認證樣式（`Authentication failed`、`could not read Username`、`terminal prompts disabled`、`Permission denied (publickey)`、`returned error: 401／403`）⇒ `PUSH-AUTH`；含遠端拒絕樣式（`! [rejected]`、`! [remote rejected]`、`non-fast-forward`、`fetch first`、`Updates were rejected`、`protected branch`）⇒ `PUSH-REJECTED`；含網路樣式（`Could not resolve host`、`Connection timed out／refused`、`unable to access`、`early EOF`、`RPC failed`）⇒ `PUSH-FAILED`；**尾段不含任何這些樣式 ⇒ `PUSH-HOOK-FAILED`**；④無該標記 ⇒ 對全部輸出依 AUTH→REJECTED→網路→其餘（`PUSH-FAILED`）判 | 任一樣本分類錯 ⇒ 紅 |
| AT-749-7-E-1 | PU | **hook 日誌含認證／網路字樣不得誤判（R-13）**：輸出為 `[pre-push dispatcher] …`、其後測試日誌含 `Connection refused`、`Authentication failed`、`unable to access`、再接 `[pre-push dispatcher] ❌ …` 與 git 自己的 `error: failed to push some refs`（尾段無樣式）⇒ `PUSH-HOOK-FAILED`；hook 通過（dispatcher 行之後無失敗）而 git 尾段為 `fatal: Authentication failed` ⇒ `PUSH-AUTH`；hook 通過而尾段 `! [rejected] … (fetch first)` ⇒ `PUSH-REJECTED`；`timed_out` 優先於一切；輸出為空且 rc≠0 ⇒ `PUSH-FAILED` | 認證樣式先於 hook 標記判 ⇒ 紅 |
| AT-749-7-2 | PU | **遮罩**：結果 `text`＝輸出**最後一個非空行**；含「網址內嵌帳密」的遠端網址（形如 `https://`＋`<帳號>`＋`:`＋`<權杖>`＋`@github.com/x.git`；夾具字串由測試在執行期拼出、權杖含唯一字串 `SECRET`，規格與測試檔都不落完整字面，以免被機密掃描閘擋下）⇒ 帳密段整段以 `***` 取代（結果為 `https://***@github.com/x.git`）；含 `token=abc123`／`password: xyz` ⇒ 值遮為 `***`；`text` ≤160 字元；結果檔與 stdout 對植入的唯一字串（`SECRET`、`abc123`、`xyz`）零命中 | 憑證進結果檔 ⇒ 紅 |

### AC-SI-49-8 重試政策（PU）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-749-8-1 | PU | 同 sha 已有 `PUSH-HOOK-FAILED`／`PUSH-REJECTED`／`PUSH-AUTH` 結果 ⇒ 下一次 `evaluate` 回 `PUSH-ATTEMPTS-EXHAUSTED`、不 spawn、`attempts` 不增；**HEAD 換成新 sha**（新的巡邏提交）⇒ 守門重新放行（新 sha 無結果檔）；結果檔屬舊 sha 不影響 | 同 sha 無限重試 ⇒ 紅 |
| AT-749-8-2 | PU | 可重試碼（`PUSH-FAILED`、`PUSH-WALL-EXCEEDED`）：`attempts=1`、`finished_at` 距今 < `sched_push_retry_minutes` ⇒ `PUSH-RETRY-WAIT`（不推）；≥ 且 `attempts < sched_push_attempts_max` ⇒ 放行、結果檔 `attempts` 增 1；`attempts == max` ⇒ `PUSH-ATTEMPTS-EXHAUSTED`；時間比較帶 offset、注入 `now` | 忽略間隔或上限 ⇒ 紅 |
| AT-749-8-3 | PU | 失敗後成功：`PUSH-FAILED`（attempts 1）→ 間隔後重試 → `PUSH-OK` ⇒ 結果檔記 `PUSH-OK`、`attempts` 2；之後 `ahead=0` ⇒ 快照 `push.state:"ok"`、`code:"PUSH-OK"` | 成功未覆寫舊失敗結果 ⇒ 紅 |

### AC-SI-49-9 鎖、牆鐘、單例（PU）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-749-9-1 | PU | 兩個 `push-run` 行程同時（一個持 `locks/push.lock`）⇒ 後者 rc 0、輸出 `PUSH-RUNNING`、不呼叫 `run_argv`、不改結果檔；持鎖者結束後再跑可推；鎖陳舊（持鎖 pid 已死且逾 `wall+600` 秒）⇒ 回收後可推（沿 `apply_lock` 陳舊回收） | 兩者同推 ⇒ 紅 |
| AT-749-9-2 | PU | **牆鐘**：`run_argv` 替身回 `timed_out=True`（已殺行程樹）⇒ 結果 `PUSH-WALL-EXCEEDED`、`current.json` 已刪、`attempts` 增 1、rc 1；真行程驗（夾具 bare 遠端的 `pre-receive`／本機 `pre-push` 睡眠 5 秒、`sched_push_wall_minutes` 以測試縫縮為 1 秒）⇒ 行程樹被殺、無孤兒 `git` 行程 | 逾時不殺樹 ⇒ 紅 |
| AT-749-9-3 | PU | **崩潰窗口**：`current.json` 殘留且其 pid 已死 ⇒ 下一次 `push-run` 與 `pushguard.evaluate` 視為不在跑（`PUSH-RUNNING` 不成立）、覆寫之；pid 存活但已逾 `wall_due_at` ⇒ 視為不在跑並回收（不殺他人行程）；`current.json` 損壞 JSON ⇒ 同「不在跑」 | 殘留檔永久卡住推送 ⇒ 紅 |
| AT-749-9-E-1 | PU | 結果檔寫入失敗（`os.replace` 注入 `OSError`）⇒ rc 1、輸出 `PUSH-RESULT-WRITE-FAILED`、但**不重推**（同一次執行不重試 push）；`current.json` 仍刪除 | 寫結果失敗後重推 ⇒ 紅 |
| AT-749-9-4 | PU | **未處理例外（R-15）**：`pushguard.evaluate`／`run_argv` 替身拋 `RuntimeError("boom token=abc123")` ⇒ `push-run` 最外層攔住：rc 1、寫 `push/last_error.json`＝`{"at":"<ISO+offset>","code":"PUSH-INTERNAL-ERROR","text":"<例外型別＋遮罩後訊息，≤160 字元>"}`、`current.json` 已刪、鎖已釋放、不重推；下一次 `push-run` 成功或守門未放行後該檔不再影響狀態（見附錄 A.4b 判定序：`last_error.at` 晚於最近結果才算）；快照 `push.state:"failed"`、`code:"PUSH-INTERNAL-ERROR"`；`abc123` 零命中 | 例外外洩（pythonw 下無人知）或快照恆 `pending` ⇒ 紅 |

### AC-SI-49-10 巡邏本體不推送與快照 `push` 區塊（PU）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-749-10-1 | PU | 巡邏心跳全程（`ctx.git().run` 記錄全部 git 子命令）⇒ 子命令集合 ⊆ P4 `ALLOWED_GIT`（`status`、`add`、`commit`、`rev-parse`、`diff`、`log`、`show`）∪ 僅出現在 `pushguard` 的唯讀 `rev-list`、`diff-tree`、`symbolic-ref`、`for-each-ref`（由 `pushguard` 發出）；`push` 零次；`patrol` 不 import `patrolpush` | 巡邏呼叫 push ⇒ 紅 |
| AT-749-10-2 | PU | **`push` 區塊狀態表驅動（附錄 A.4b 為準；各態互斥、依判定序先中者定案）**：夾具逐列造（`now`、`tick.json`、`current.json`、結果檔、守門輸入皆可控），斷言 `{state, code, retry}` 與 `text`＝附錄 A.4 該碼的固定句：`sched_auto_push=false`⇒`off`／`PUSH-OFF`；`current.json` 存活⇒`running`／`PUSH-RUNNING`；領先 0 且最近結果 `PUSH-OK`⇒`ok`／`PUSH-OK`；領先 0 其餘⇒`idle`／`PUSH-NOT-AHEAD`；守門被擋（`PUSH-NOT-MAIN`、`PUSH-DIRTY-TREE`、`PUSH-FOREIGN-COMMITS`、七個專屬碼〔`PUSH-NOT-RECORDED`／`PUSH-RECORD-MISMATCH`／`PUSH-APP-KIND-INVALID`／`PUSH-APP-REUSED`／`PUSH-PATH-OUTSIDE`／`PUSH-LEDGER-RULE`／`PUSH-CONTENT-MISMATCH`〕、`PUSH-GIT-UNAVAILABLE`）⇒`blocked`／該碼；守門可推而同 sha 有失敗結果且（不可重試碼⇒`retry:"never"`；可重試碼用盡⇒`retry:"exhausted"`；可重試碼未到間隔⇒`retry:"wait"`）⇒`failed`／**該最近結果的碼**；`last_error.json` 晚於最近結果且守門可推⇒`failed`／`PUSH-INTERNAL-ERROR`；守門可推且可立即（重）試：`tick.json` 在 `2×心跳＋5 分` 內⇒`pending`／`PUSH-PENDING`、缺或逾界⇒`waiting-login`／`PUSH-WAITING-LOGIN`；`retry` 於非 `failed` 態恆為 null；`ahead` 為領先提交數；**同一夾具不得同時滿足兩列**（以 `evaluate` 輸入窮舉檢查：每組輸入恰得一個 `state`） | 狀態判錯或兩態並存 ⇒ 該列紅 |
| AT-749-10-3 | PU | `PUSH-IN-PROGRESS`：`current.json` 存活時，`verified`＋`dec(promote)` 或 `dec(rollback)` 的 PROP 在 `_advance_prop` 被擋：不呼叫 `promote`／`rollback`、`ctx.notes`＝`PUSH-IN-PROGRESS`、快照該 PROP `who:"巡邏器"`；`sandbox`／`verify`／`card --issue` 不受影響；push 結束後下一心跳照常 promote | 推送中仍 promote（改工作樹影響 pre-push 測試）⇒ 紅 |
| AT-749-10-E-1 | PU | 快照的 `push` 區塊對 git 不可用 ⇒ `state:"blocked"`、`code:"PUSH-GIT-UNAVAILABLE"`，其餘快照欄不受影響；`pushguard.evaluate` 在每心跳只被呼叫一次、其 git 逾時不超過 20 秒（`Git.run(timeout=20)`），整個評估總牆鐘 ≤60 秒（不拖慢心跳） | 評估拋例外中斷心跳 ⇒ 紅 |

### AC-SI-49-11 `push-run` 授權與 rc 契約（PU）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-749-11-1 | PU | `AUTOSDD_UNATTENDED` 有設（含字面 `0`）⇒ rc 1、碼 `UNATTENDED-REFUSED`、零寫入（`push/tick.json` 也不寫）、`run_argv` 呼叫 0 次；`unattended.C_CLASS` 含 `push-run` 且恰 16 個；`gate("push-run", None, env)` 在 `AUTOSDD_UNATTENDED` 未設時回空 | 漏登 C 類 ⇒ 紅 |
| AT-749-11-2 | PU | **rc 契約**：守門放行且推成功⇒0；守門未放行（任一 `PUSH-*` 前置碼，含 `PUSH-OFF`、`PUSH-NOT-AHEAD`、`PUSH-RETRY-WAIT`、`PUSH-ATTEMPTS-EXHAUSTED`、`PUSH-RUNNING`）⇒0 且 stdout 含該碼（無事可做不是錯誤）；推送失敗（`PUSH-AUTH`／`REJECTED`／`HOOK-FAILED`／`WALL-EXCEEDED`／`FAILED`）⇒1；用法錯誤（未知旗標）⇒3；每次執行（除授權拒收與 `--dry-run`）先寫 `push/tick.json`（`tick_at` 帶 offset）；`--dry-run`⇒只評估、印碼、不寫任何檔、不呼叫 `run_argv`、rc 0 | rc 對映錯 ⇒ 紅 |
| AT-749-11-E-1 | PU | 入口薄殼：`python tools/selfimproving.py push-run --help` 列出 `--repo`、`--json`、`--dry-run`；`--json` 輸出單一 JSON 物件 `{ok,kind:"push-run",code,sha,ahead,attempts}`；入口動詞總數 30（P6 的 29＋`push-run`）；`push-run` 不在 `READONLY` 清單 | 動詞數不同步 ⇒ 紅 |

### AC-SI-49-12 OS 任務安裝、現查、移除（PU）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-749-12-1 | PU | Windows（`sys.platform` 以 `mock.patch.object(schedarm.sys, "platform", "win32")` 注入、`run_argv` 替身）：`sched arm` 在 `sched_auto_push=true` 時，除巡邏任務安裝外再呼叫一次 `powershell.exe -NoProfile -NonInteractive -Command <註冊指令>`；該指令含 `Register-ScheduledTask`、任務名 `AutoSDD_SI_Push`、`-LogonType Interactive`、`-RunLevel Limited`、`-UserId`（取呼叫端 `$env:USERDOMAIN\$env:USERNAME`）、動作 `Execute`＝`<repo>\.venv\Scripts\pythonw.exe`、`Argument`＝`"<repo>\tools\selfimproving.py" push-run`、觸發為每 `sched_heartbeat_minutes` 分鐘重複、`MultipleInstancesPolicy IgnoreNew`、`ExecutionTimeLimit PT3H`、`StartWhenAvailable`、`DisallowStartIfOnBatteries:$false`、`StopIfGoingOnBatteries:$false`、**不含** `-WakeToRun`、不含 `S4U`；現查 `Get-ScheduledTask -TaskName 'AutoSDD_SI_Push'…NextRunTime` 回非空字串才算成功，輸出含 `push_task_credential=<NextRunTime>`；憑證空 ⇒ rc 1 `SCHED-NO-CREDENTIAL`（輸出不得宣稱已建立） | 缺旗標、用了 S4U、或不驗憑證 ⇒ 紅 |
| AT-749-12-2 | PU | `sched_auto_push=false` ⇒ `sched arm` 不註冊推送任務，且若現查任務存在則移除之（`Unregister-ScheduledTask -TaskName 'AutoSDD_SI_Push'`）；`sched disarm` 同時移除巡邏與推送兩支並現查兩者皆不見才 rc 0（只移除這兩支，argv 不含 `AutoClaude_Nightly`／`AutoClaude_WindowsSmoke`／`-Uninstall`）；巡邏任務移除成功而推送任務殘留 ⇒ rc 1 | disarm 漏推送任務或誤殺 nightly ⇒ 紅 |
| AT-749-12-3 | PU | 失敗碼：註冊輸出含 `Access is denied`／`拒絕存取`／`elevat` ⇒ `SCHED-ELEVATION-REQUIRED`（提示「以系統管理員身分重跑 `sched arm`；任務主體仍為目前使用者互動登入型」）；其他失敗 ⇒ `SCHED-PUSH-TASK-FAILED`（輸出明說巡邏任務已安裝與否）；兩者 rc 1；**巡邏段與推送段獨立（R-17）**：巡邏段回 `SCHED-ELEVATION-REQUIRED`（非提權）時，`sched arm`（不帶旗標）**仍嘗試推送段**，最終 rc 1、輸出同時列「巡邏任務：<碼>」「推送任務：<已建立／碼>」；新旗標 `sched arm --push-only` 只裝／重裝推送任務（不呼叫巡邏安裝器、不需提權；`sched_auto_push=false` 時回 rc 1 `SCHED-PUSH-OFF` 並不動作）；`sched disarm --push-only` 只移除推送任務；`-UserId` 與註冊者不同 ⇒ 現查回讀的 `Principal.UserId` 不等於預期使用者 ⇒ rc 1 `SCHED-PUSH-TASK-FAILED` | 錯誤碼混用或不查 UserId ⇒ 紅 |
| AT-749-12-4 | PU | macOS（`sys.platform` 注入 `darwin`、`plist_dir` 暫存）：`sched arm` 另寫 `AutoSDD_SI_Push.plist`（`Label`＝`AutoSDD_SI_Push`、`StartInterval`＝心跳秒、`ProgramArguments`＝[`<repo>/.venv/bin/python`、`<repo>/tools/selfimproving.py`、`push-run`、`--repo`、`<repo>`]、`RunAtLoad:false`），`launchctl bootstrap gui/<uid>`；憑證＝`launchctl list AutoSDD_SI_Push` rc 0 與 plist 回讀（rc，非時間值）；Windows 專屬字面（`powershell.exe`、`Register-ScheduledTask`）只住 `sys.platform` 守衛分支（鐵律三；`TestForeignExecutableArgvIsGuarded` 不新增站點） | Windows 字面外洩到 mac 分支 ⇒ 紅 |
| AT-749-12-5 | PU | 不註冊 S4U 的原因與限制寫入程式與 SOP：`schedarm` 模組字串含 `Interactive` 與 `S4U` 兩個字樣於註解／說明；任務為使用者**未登入時不執行**（`push.state:"waiting-login"` 由 AT-749-10-2 驗）；`scheduled_task_expectations.json` 與 `install_windows_nightly.ps1` **位元組不變**（推送任務不納入該 SSOT 與其「任務集合逐字相等」鎖，WHY 見 PRD ADR-SI-19） | 把推送任務塞進 nightly 安裝器 ⇒ 該檔位元組變而紅 |
| AT-749-12-6 | PU | `--push-only` 與獨立性（R-17）：①`sched arm --push-only`：`run_argv` 呼叫恰一次（推送註冊）＋現查，不含 `install_windows_nightly.ps1`；成功 rc 0；②`sched arm`（無旗標）巡邏安裝器回 `Access is denied` ⇒ 仍呼叫推送註冊（共兩次安裝類呼叫），推送成功時輸出含 `push_task_credential`、整體 rc 1 `SCHED-ELEVATION-REQUIRED`；③巡邏段成功而推送段失敗 ⇒ rc 1 `SCHED-PUSH-TASK-FAILED`、輸出明說巡邏任務已安裝；④`sched disarm --push-only` 只呼叫推送任務的 `Unregister-ScheduledTask` 與現查，不動巡邏任務 | 推送段隨巡邏段失敗而被跳過 ⇒ 紅 |

### AC-SI-49-13 憑證不落地（PU）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-749-13-1 | PU | 全程（`push-run`、`sched arm`、快照、結果檔、`last_error.json`、`patrol.log`；推送任務沒有 `tick.log`，其痕跡只有 `push/` 下的檔）植入唯一字串於環境變數 `GITHUB_TOKEN`、`GH_TOKEN`、`AUTOSDD_SI_AUDIT_KEY`、遠端 URL userinfo ⇒ 所有落地檔與 stdout／stderr 對這些字串零命中；`push-run` 的 env 傳給 git 時**不剔除**使用者的憑證類變數（它要用）但**不寫入**任何檔；程式碼面：全套件無 `credential`／`token` 寫檔路徑（AST：`patrolpush.py` 的 `write_text`／`write_bytes`／`open(...,"w")` 的內容只來自結果／tick／current 三種 dict） | 結果檔記下 env 或 URL userinfo ⇒ 紅 |
| AT-749-13-E-1 | PU | `AUTOSDD_SI_AUDIT_KEY` 不傳給 git：`push-run` 傳給 `run_argv` 的 env 剔除名稱含 `AUDIT_KEY` 者（金鑰屬入帳面，與 push 無關）；`GIT_ASKPASS`／`SSH_ASKPASS` 保留（使用者既有設定） | 金鑰環變數洩給 git 子行程 ⇒ 紅 |

### 自增 AC：能力登記、參數與同步站點、不退化、範圍守衛（RD）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-790-1-1 | RD | `capability_problems(PKG, CAPABILITY, ENTRY)==[]`；`CAPABILITY` 鍵數＝P6 現值＋6；新 6 檔類別：`nextstep`／`propdetail`／`memdir`／`pushguard` 為 `ro`、`patrolreport` 為 `rw`、`patrolpush` 為 `exec`；全套件含 `subprocess` 字樣者仍只有 `git.py`、`runner.py`；`import runner` 的檔（含 `patrolpush`）皆登記 `exec`；`net` 類仍只有 `fetch`、`research` | 新檔含 `subprocess` 字樣（含註解）⇒ 紅 |
| AT-790-1-E-1 | RD | 注入變體（沿 `test_selfimproving_capability.py` 形態）：`ro` 檔（`nextstep`）加 `open(…,"w")`／`import socket`；`propdetail` 加 `import os`＋`environ`；`patrolreport` 相對 import `patrolpush`；`pushguard` 加 `subprocess`；`memdir` 相對 import `runner`；登記表漏登新檔 ⇒ 各回對應問題 | 登記判準退化 ⇒ 紅 |
| AT-790-2-1 | RD | 同步站點逐一為新值（§2 表）：`PARAM_SPECS` 47、`C_CLASS` 16、入口動詞 30、`CAPABILITY` +6；**未變**：`KINDS` 27、`EVENT_LABELS` 27、`check` 項目 35、`status` 鍵 20、`CHECK_RULES_REV` 6、`FINGERPRINT_EXCLUDED`、`export.KINDS`；`tools/lib/selfimproving/` 檔頭 LOC 分級：`patrol.py`、`patrolrun.py` 每檔斷言行 ≤400（`check_loc_budget` 同判準）且各自相對 P6 現值**淨增 ≤30 行**（新邏輯一律進新模組） | 在 `patrol*.py` 內塞新邏輯而超界 ⇒ 紅 |
| AT-790-3-1 | RD | 不退化：既有 SI 測試檔全綠（§2 清單已改期望值）；`research --skip`、`registry-ingest`、`backtest`、`fourq` 行為位元組不變；P4 的 `AT-438-7-1`（巡邏檔呼叫集合）、`AT-438-4-E-1`（巡邏不 decide）全綠；`export` 清單模式（不帶 `--id`）輸出對 P6 黃金夾具位元組不變；`card` 輸出位元組不變 | 任一既有行為被改 ⇒ 既有 AT 紅 |
| AT-790-4-1 | RD | 範圍守衛（允許集合見 §4）：讀 `SI_SCOPE_BASE`（可選 `SI_SCOPE_TIP`），只比對已提交差異，未設＝guard-not-triggered；差分觸及允許集合時，差分 ⊆ 允許集合且 PRD、SOP、`TCS-SelfImproving-P*`、`Root_Layout` 差異為空；**不得改**：`fold.py`、`writeverbs.py`、`.claude/**`、`AgentConsole/**`、`.github/**`、`install_windows_nightly.ps1`、`scheduled_task_expectations.json`、`research_sources.json` | 實作 commit 夾帶 PRD ⇒ 紅 |
| AT-790-5-1 | RD | **黃金樣本（裁決 11；本檔自增 AC-P7-090-5）**：`tools/tests/fixtures/selfimproving/p7/patrol.golden.json` 與 `detail.golden.json` 存在（路徑寫死，不存在＝紅、不 skip）；`p7x.golden_patrol()`、`p7x.golden_detail()` 以固定夾具重新產生的位元組（`json.dumps(ensure_ascii=False, separators=(",",":"))`＋LF）逐位等於檔位元組；兩檔 LF、無 BOM、結尾恰一個 LF；patrol 樣本涵蓋 §3 所列各欄情境，detail 樣本八欄皆非 null | 樣本被改一字、遺漏欄位、或產生規則漂移 ⇒ 紅 |
| AT-790-5-E-1 | RD | 樣本與 §2 契約同構：patrol 樣本頂層鍵集合、`ingest[]`／`props[]`／`runs.*`／`schedule`／`push` 各子物件鍵集合與型別（含可空性）逐一等於 §2.2；detail 樣本鍵集合等於 §2.1；樣本中任何 `code` 皆在附錄 A 的對應表內且 `text` 等於 `nextstep.reason` 輸出；**零洩漏**：兩樣本對 held-out 目錄夾具的唯一字串、URL userinfo、`token=` 樣式零命中 | 樣本含契約外欄位或未登記碼 ⇒ 紅 |
| AT-790-4-2 | RD | **四守衛一致**：`px.scope_verdict` 夾具 repo 上，以 P7 實作 commit 的典型差分（新 6 檔、三個新測試檔、`_selfimproving_p7_fixtures.py`、`params.json`、`SelfImproving_LedgerDb_P0_Baseline.md`、`tools/selfimproving.py`、既有同步測試檔）驗：P4 `AT-440-8-1`、P5 `AT-444-6-1`／`AT-445-5-1`、P6 `AT-690-4-1`、P7 `AT-790-4-1` 各自的 `ALLOWED`／`FORBIDDEN` 皆對此差分回空（P6 的 `FORBIDDEN` 不再含 `params.json` 與 P0 基準檔；各守衛的 `ALLOWED` 取「自身集合 ∪ `p7x.P7_ALLOWED`」，`P7_ALLOWED` 單一來源）；負控：差分夾帶 `AgentConsole/x` ⇒ 四者皆紅 | 只改一處守衛而其他三處仍誤紅 ⇒ 紅 |

---

## 2. 介面契約定稿（兩端共用；欄名以此為準，Console TCS 引用本節）

### 2.1 `export --kind proposals --id <PROP>` 新增 `items[0].detail`

| 欄 | 型別 | 來源 |
|---|---|---|
| `patch` | `{rel:str, bytes:int, text:str, truncated:bool}`｜null | `docs/06_quality/SelfImproving_Proposals/<PROP>/r<rev>.patch`；`text` 上限 `propdetail.DETAIL_TEXT_MAX`＝262144 bytes（模組常數，不進 params）；讀不到＝null＋`ne` 一筆 `PATCH-UNREADABLE` |
| `body` | 同上形 | 同目錄 `r<rev>.md`；讀不到＝null＋`ne` `BODY-UNREADABLE` |
| `sourceObs` | `[{id, context, symptom, severity, disposition}]`｜缺列者 `{id, missing:true}` | PROP 的 `sources` 依序對 OBS 帳本；原文不截斷 |
| `heldout` | `{frozen:bool, seq:int｜null, n:int｜null, min:int｜null, belowMin:bool｜null, frozenBy:str｜null, digest8:str｜null, neNote:str｜null}` | `heldout.freeze` 事件（`seq`、`n`、`frozen_by`、`digest` 去 `sha256:` 取前 8 碼）＋ `params.json` 的 `min_heldout`；**不含任何評估集內容**；`neNote`＝`belowMin` 為 true 時的白話（含 n 與 min），否則 null |
| `sandbox` | `{seq:int,id:str,applied:bool,touchedOk:bool｜null,rollbackOk:bool｜null,failCode:str｜null,failText:str｜null}`｜null | 同 rev 最近一筆 `app.sandbox`；`failText`＝`nextstep.reason(failCode).text`（`failCode` 為 null 時 null；`applied=false` 而事件 `fail_code` 為 null 時 `failCode` 記 `SANDBOX-NOT-APPLIED`） |
| `verify` | `{seq:int,id:str,verdict:"PASS"｜"FAIL"｜"NE",baselineRed:bool｜null,patchedGreen:bool｜null,mutatedRed:bool｜null,probesN:int,carrierProof:bool｜null,reasons:[{code:str,text:str}]}`｜null | 同 rev 最近一筆 `app.verify`；`reasons` 以 `verdict.verdict_of` **重算**，`text` 取 `nextstep.reason` |
| `next` | `{code:str, who:"掌舵者"｜"巡邏器"｜"無人運轉"｜"主機管理者"｜"無", text:str}` | `nextstep.of(fold, prop, params)`（只看帳本） |
| `timeline` | `[{seq,t,by,kind,action}]`（升冪，至多最後 500 筆） | 事件帳本中提到該 PROP 者；`action` 取 `issuemap.event_label`／`DEC_PREFIX`＋`dkind_label` |

**與設計稿的差異**（Console 端 SA 須對齊）：`heldout` 增 `digest8`、`neNote`；新增 `sourceObs`、`timeline` 兩欄（時間線不必再打 `GET /si/issues/{PROP}`，但該端點保留不動）；`sandbox`／`verify` 欄名為 camelCase（`touchedOk` 等），來自 snake_case 事件鍵，backend 的 `SiKeyNames.camelKeys` 已深層對映整棵樹，**不需改動 backend**（Console 鍵只補測試）。


**`ne` 項（既有契約，補充）**：`export` 的 `ne[]` 既有形狀 `{field,reason}` 不變；**本鍵新增的碼**（附錄 A.7：`PATCH-UNREADABLE`、`BODY-UNREADABLE`、`OBS-LEDGER-UNREADABLE`、`HELDOUT-MIN-UNKNOWN`、`TIMELINE-TRUNCATED`）的 `ne` 項多一鍵 `text`（`nextstep.reason` 白話），使「凡帶碼處同帶白話」（裁決 8）成立而不改既有項形狀。
### 2.2 `<AUTOSDD_SI_DIR>/console_report/patrol.json`（`schema_rev:1`）

```
{ "schema_rev":1, "generated_at":"<ISO+offset>", "off":false, "heartbeat_minutes":15,
  "ledger_seq":112, "truncated":false,
  "steps":[{"step":"巡視|入帳|到期|運轉|推進","result":"<一行>"}],
  "schedule":{"enabled":true,
              "current":{"code":"SKIP-RUN-OPEN","text":"<白話>"},
              "last_skip":{"seq":99,"t":"<ISO>","code":"SKIP-RUN-OPEN","text":"<白話>","audit_ref":"<uuid>|null"}},
  "ingest":[{"audit_ref":"<uuid>","kind":"decide|obs-add|…|null","status":"rejected|deferred",
             "code":"STALE-CARD","text":"<白話>","permanent":true}],
  "props":[{"id":"PROP-SI-008","state":"verified","code":"WAIT-PROMOTE-DECISION",
            "who":"掌舵者","text":"<白話一句>"}],
  "runs":{"live":[{"run":"RUN-SI-011","purpose":"scheduled|console|manual",
                   "started_at":"…","wall_due_at":"…"}],
          "waiting":[{"run":"RUN-SI-012","code":"SKIP-OTHER-DRIVER","text":"<白話>"}],
          "queued":[]},
  "push":{"enabled":true,"state":"off|idle|pending|waiting-login|running|ok|failed|blocked",
          "code":"PUSH-PENDING","text":"<白話>","retry":"wait|exhausted|never|null",
          "sha":"<40 碼>|null","ahead":0,"attempts":0,"finished_at":"<ISO>|null","tick_at":"<ISO>|null"} }
```
**型別與可空性（Console 以此為準）**：`generated_at` str（ISO＋offset，非空）；`off` bool；`heartbeat_minutes` int；`ledger_seq` int（無事件＝0）；`truncated` bool；`steps` list（恆 5 項，OFF 時 `[]`）；`schedule` object｜null（OFF 時 null）：`enabled` bool、`current` `{code:str,text:str}`｜null（`due()` 失敗時 null）、`last_skip` `{seq:int,t:str,code:str,text:str,audit_ref:str｜null}`｜null；`ingest[]` 每筆六鍵，`kind` str｜null，`status`∈{rejected,deferred}，`permanent` bool；`props[]` 每筆五鍵皆 str 非空，`who` 五值；`runs.live[]` 四鍵 str，`purpose`∈{scheduled,console,manual}；`runs.waiting[]` 三鍵 str；`runs.queued` 恆 `[]`（W1 不得有元素；W2 元素 `{purpose,target,why}`，W1 Console 不得依賴）；`push.enabled` bool；`push.state`、`push.code`、`push.text` 恆為非空 str（見附錄 A.4b 的單一對映表）；`push.retry` 僅 `state:"failed"` 且 `code` 為 `PUSH-HOOK-FAILED`／`PUSH-REJECTED`／`PUSH-AUTH`（`never`）或 `PUSH-WALL-EXCEEDED`／`PUSH-FAILED`（`wait`／`exhausted`）時非 null，其餘恆 null；`push.sha` str｜null（`ahead>0`、`running` 或最近結果對應之 sha，否則 null）；`push.ahead` int；`push.attempts` int（無結果＝0）；`push.finished_at`、`push.tick_at` ISO str｜null。鍵序固定（如上）、`json.dumps(ensure_ascii=False, separators=(",",":"))`＋LF。`ingest` 只列被拒與延後；`permanent`：false 者條件解除後自動入帳。`props[]` 的收錄範圍與 `code` 見附錄 A.2／A.3；`schedule`、`runs.waiting[]` 的碼見附錄 A.6；`push` 的狀態、碼與白話句見附錄 A.4／A.4b。`ledger_seq` 為快照產生當下的事件帳本最大 `seq`（Console 據以判斷「快照是否比 PROP 的 `lastSeq` 舊」）。新鮮度＝`now − generated_at > 2×heartbeat_minutes + 5 分`（AT-747-8-4）。`off:true` ⇒ 其餘陣列皆空、`push.state:"off"`。

**與設計稿的差異**：新增頂層 `truncated`、`schedule`、`runs.waiting[]`；`push.state` 值域改為 `off｜idle｜pending｜waiting-login｜running｜ok｜failed｜blocked`（設計稿 `idle|running|ok|failed|skipped`），且 `push.code`／`push.text` 恆非空、新增 `push.retry`、`push.tick_at`；`runs.live[].purpose` W1 值域為 `scheduled｜console｜manual`（W2 再加 `freeze|revise|propose`）；`runs.queued` W1 恆空、元素結構留給 W2；`ingest[].status` 由 `permanent` 導出。
### 2.3 `<AUTOSDD_SI_DIR>/push/` 檔案契約（`tick.json`、`current.json`、`results/`、`last_error.json` 只由 `push-run` 寫、由巡邏器唯讀；`commits.jsonl` 反向：只由巡邏器 `_commit` 寫、由 `push-run`／`pushguard` 唯讀）

| 檔 | 內容 | 寫入者 |
|---|---|---|
| `push/tick.json` | `{"tick_at":"<ISO+offset>","by":"<任務或手動>"}`；每次 `push-run` 開頭覆寫（原子換檔） | `push-run` |
| `push/current.json` | `{"sha":"<40>","pid":N,"started_at":"…","wall_due_at":"…"}`；推送期間存在，結束即刪 | `push-run` |
| `push/results/<sha12>.json` | `{"sha","finished_at","rc","code","text","attempts","tree_changed"}`；同 sha 覆寫（`attempts` 累計；`tree_changed` 為推送結束後復查工作樹是否變髒） | `push-run` |
| `push/commits.jsonl` | 每行 `{"sha":"<40>","app":"APP-SI-NNN","prop":"PROP-SI-NNN","at":"<ISO+offset>"}`；**巡邏器**於 `_commit` 成功後追加（`patrolreport.record_commit`，O_APPEND 單行）；`push-run`／`pushguard` 只讀；不在 repo 內；寫入失敗＝該提交不可自動推送 | `patrolrun._commit`（經 `patrolreport`） |
| `push/last_error.json` | `{"at":"<ISO+offset>","code":"PUSH-INTERNAL-ERROR","text":"<遮罩後，≤160 字元>"}`；`push-run` 最外層攔到未處理例外時覆寫；`pythonw` 下無 stderr，這是唯一可見痕跡 | `push-run` |
| `locks/push.lock` | `apply_lock` 獨佔鎖 | `push-run` |

### 2.4 `push-run` 動詞

`python tools/selfimproving.py push-run [--repo DIR] [--json] [--dry-run]`；C 類動詞；rc：0＝推成功或無事可做（含任何 `PUSH-*` 守門未放行碼）；1＝授權拒收、推送失敗，或**未處理例外（`PUSH-INTERNAL-ERROR`，已寫 `last_error.json`）**（碼在輸出）；3＝用法錯誤。

---

## 3. 夾具（`p7x`，`tools/tests/_selfimproving_p7_fixtures.py`）

- `p7x.repo(**kw)`：沿 `px.repo`／`fx.p1_base()` 建合成 repo（含協定目錄與 `params.json` 的 47 鍵副本），家目錄 `AUTOSDD_SI_DIR` 指向暫存；可選一組 PROP（任一狀態）、`heldout.freeze`（n、digest）、`app.sandbox`、`app.verify`、`card`、`dec`。`p7x.repo_m()`＝M 類版本，另造 `claude_home()/projects/<slug>/memory/MEMORY.md`（`claude_home` 以 `mock.patch` 指向暫存）。
- `p7x.push_repo(ahead=[...])`：暫存目錄真 git（`git init`、本機 user.name／email、`core.autocrlf=false`）＋**本機 bare 遠端**（`file://` 路徑）、`main` 追蹤 `origin/main`；`ahead` 描述每個領先提交（`kind`：`patrol`／`human`／`merge`、trailer 變體、觸及路徑）；可選 `pre-push` hook（成功／失敗／睡眠）。**測試不得連真遠端**。
- `p7x.run_argv_spy()`：替身 `runner.run_argv`，記錄 argv／env／timeout／cwd，可回注入的 `RunResult`。
- `p7x.P7_ALLOWED`：§4 允許集合的單一來源（供四個範圍守衛取聯集，AT-790-4-2）。
- **黃金樣本（裁決 11；R-01、C-01；兩端共用，本節為唯一路徑定義）**：`tools/tests/fixtures/selfimproving/p7/patrol.golden.json`（快照）與 `tools/tests/fixtures/selfimproving/p7/detail.golden.json`（`export --kind proposals --id PROP-SI-901` 的 `items[0]`，單一 JSON 物件）；落點＝既有 `tools/tests/fixtures/selfimproving/`（P6 的 `G-S1.audit.json` 同目錄體例）下的 `p7/`。LF、無 BOM、結尾恰一個 LF；序列化＝`json.dumps(obj, ensure_ascii=False, separators=(",",":"))`。由 `p7x.golden_patrol()`／`p7x.golden_detail()` 以固定常數確定性產出（固定 `now`＝`2026-11-11T12:00:00+08:00`、固定 PROP／APP／DEC／audit_ref／sha），AT-790-5-1 重新產生並逐位元組比對。**patrol 樣本須涵蓋**：`off:false`；`ingest` 兩筆（`rejected`＋`permanent:true`、`deferred`＋`permanent:false`）；`props` 三筆（`who` 取掌舵者、巡邏器、主機管理者各一）；`runs.live` 一筆、`runs.waiting` 一筆；`schedule`（`current` 與 `last_skip` 皆非 null，`last_skip.audit_ref` 非 null）；`push.state:"waiting-login"`；`truncated:false`。**detail 樣本須涵蓋**：八欄皆非 null；`sandbox.failText` 非 null；`verify.reasons` 兩筆；`heldout.belowMin:true` 與 `neNote`；`sourceObs` 含一筆 `missing:true`；`timeline` ≥3 筆。**根層先提交、Console 後**：Console 鍵把同一份複製到其 fixtures，驗法＝兩側 `sha256` 相等（PowerShell `Get-FileHash -Algorithm SHA256 <檔>`；mac／Linux `shasum -a 256 <檔>`）；任一側改檔＝走 PRD 修訂與本檔勘誤、不得單側改。
- 時鐘縫：`patrolpush`、`pushguard`、`patrolreport` 的 `now` 皆可注入且須帶 offset（鐵律三）；注入縫：`patrolpush.AFTER_GUARD_HOOK`（守門之後、`run_argv` 之前；預設 `None`；僅測試以 `mock.patch.object` 設定，AT-749-6-2）、`patrolpush.WALL_SECONDS_OVERRIDE`（測試縮短牆鐘；預設 `None`）。

## 4. 實作 commit 的允許集合（AT-790-4-1；實作 commit 的差分必須 ⊆ 本表；`p7x.P7_ALLOWED`）

| 類別 | 路徑 |
|---|---|
| 新程式（6） | `tools/lib/selfimproving/{nextstep,propdetail,memdir,pushguard,patrolreport,patrolpush}.py` |
| 改程式（各限 PRD §9.9.1 所列呼叫點） | `tools/lib/selfimproving/{export,params,sandbox,patrol,patrolrun,patrolbrief,schedarm,unattended}.py`、`tools/selfimproving.py` |
| 協定資料與基準 | `docs/06_quality/SelfImproving_Protocol/params.json`（47 鍵）、`docs/06_quality/SelfImproving_LedgerDb_P0_Baseline.md`（`params.json` 列活值） |
| 新測試與夾具 | `tools/tests/test_selfimproving_p7_{report,memory,push}.py`、`tools/tests/_selfimproving_p7_fixtures.py`、黃金樣本 `tools/tests/fixtures/selfimproving/p7/{patrol,detail}.golden.json` |
| 既有測試同步（§2 表所列，且僅限列明的站點） | `tools/tests/test_selfimproving_{capability,schedule_gate,schedule_advance,schedule_patrol,schedule_model,sandbox,check,registry,fourq_gate,backtest,export_status,events,ledgerdb_p0}.py`、`tools/tests/_selfimproving_fixtures.py`、`tools/tests/_selfimproving_p5_fixtures.py`、`tools/tests/_selfimproving_p6_fixtures.py`、`tools/tests/test_root_module_layout.py`（落點鎖，實作 commit 後加反引號路徑） |
| 重釘（主控收尾另一 commit，不在實作 commit；R-22；各站點現查、不寫死數字） | `tools/tests/test_adr_xplat001_c1c2_lock.py`（護欄層行數棘輪、`tools/tests` 檔數下限 `_TREE_FILE_FLOORS` 與每階段新檔計數、E501 東亞寬度、兩站點 guard-total）、onboarding 測試基線快照（`ONBOARDING.md` §7，跑 `sync_onboarding_baselines` 同批重釘）、`tools/tests/test_root_module_layout.py`（實作 commit 後加回新 6 檔與新測試檔的反引號路徑）；compat-ci `paths` 不需新增（無新根層路徑）；既有「重釘三檔」（`AutoSDD_improving_*`、`CrossPlatform_R*_Scan_Findings` 等計數文件）依 `guard-ratchet` 儀式現查 |
| **不得改** | PRD、SOP、`TCS-SelfImproving-P*`、`Root_Layout_and_Module_Placement.md`、`fold.py`、`writeverbs.py`、`.claude/**`、`AgentConsole/**`、`.github/**`、`tools/install_windows_nightly.ps1`、`tools/scheduled_task_expectations.json`、`docs/06_quality/SelfImproving_Protocol/research_sources.json` |

## 4A. 勘誤路由與待回填

- 本檔與 PRD v0.16 不一致處以 PRD 為準；本檔日後勘誤單獨 commit。
- **P7-PENDING 回填**：PRD v0.16／SOP／本檔在 P7 鍵凍結後，主控把摘要回填追溯表。**`spec-frozen` 前檢核清單（R-21）**：①追溯表無 `P7-PENDING`（Stage-1 凍結後回填）；②PRD §14 與附錄 C.2 #26 的 T1 座標（sid＋line）由主控補齊，仍標 `[他包回報]` 者須說明；③§5 計數、§2 契約與 Console TCS §0.2 逐欄相符；④黃金樣本路徑兩端一致。
- 本鍵對已發布 TCS 的勘誤（P4、P5、P6）已就地訂正並各加勘誤列，詳見各檔勘誤表；需 refreeze 的鍵：`monorepo-si-p4-schedule`、`monorepo-si-p5-expert-review`、`monorepo-si-p6-registry-backtest`（P6 鍵另含 PRD／SOP／Root_Layout 的新摘要）。TCS-P6 附錄 A～D 一字未動，Console 鍵 `agentconsole-research-registry` 的 `sha256` 引用不受影響。

---

## 5. 計數與對照

**AT 共 127（正控 80、負控 47）**；各檔：RD 54、MM 11、PU 62。

**每條 FR／AC → AT 對照表**（機械產生：由 §1 每列的 AT 編號推得；每條 AC 至少一個 AT）

| AC | AT |
|---|---|
| AC-SI-47-1 | AT-747-1-1、AT-747-1-E-1 |
| AC-SI-47-2 | AT-747-2-1、AT-747-2-E-1、AT-747-2-E-2 |
| AC-SI-47-3 | AT-747-3-1、AT-747-3-E-1 |
| AC-SI-47-4 | AT-747-4-1、AT-747-4-E-1、AT-747-4-E-2 |
| AC-SI-47-5 | AT-747-5-1、AT-747-5-2、AT-747-5-E-1 |
| AC-SI-47-6 | AT-747-6-1、AT-747-6-E-1、AT-747-6-2 |
| AC-SI-47-7 | AT-747-7-1、AT-747-7-E-1 |
| AC-SI-47-8 | AT-747-8-1、AT-747-8-2、AT-747-8-3、AT-747-8-4、AT-747-8-E-1、AT-747-8-E-2 |
| AC-SI-47-9 | AT-747-9-1、AT-747-9-2、AT-747-9-E-1、AT-747-9-3 |
| AC-SI-47-10 | AT-747-10-1、AT-747-10-2、AT-747-10-3 |
| AC-SI-47-11 | AT-747-11-1、AT-747-11-2、AT-747-11-3 |
| AC-SI-47-12 | AT-747-12-1、AT-747-12-2、AT-747-12-3 |
| AC-SI-47-13 | AT-747-13-1、AT-747-13-E-1 |
| AC-SI-47-14 | AT-747-14-1、AT-747-14-2、AT-747-14-E-1 |
| AC-SI-47-15 | AT-747-15-1、AT-747-15-2、AT-747-15-3、AT-747-15-E-1 |
| AC-SI-48-1 | AT-748-1-1、AT-748-1-2、AT-748-1-E-1 |
| AC-SI-48-2 | AT-748-2-1、AT-748-2-E-1 |
| AC-SI-48-3 | AT-748-3-1 |
| AC-SI-48-4 | AT-748-4-1、AT-748-4-2、AT-748-4-E-1 |
| AC-SI-48-5 | AT-748-5-1、AT-748-5-2 |
| AC-SI-49-1 | AT-749-1-1、AT-749-1-E-1、AT-749-1-2 |
| AC-SI-49-2 | AT-749-2-1、AT-749-2-E-1、AT-749-2-2、AT-749-2-3、AT-749-2-4、AT-749-2-5、AT-749-2-E-2 |
| AC-SI-49-3 | AT-749-3-1、AT-749-3-2 |
| AC-SI-49-4 | AT-749-4-1、AT-749-4-E-1、AT-749-4-E-2、AT-749-4-E-3、AT-749-4-E-4、AT-749-4-E-5、AT-749-4-E-6、AT-749-4-E-7、AT-749-4-E-8、AT-749-4-E-9、AT-749-4-E-10、AT-749-4-E-11、AT-749-4-E-12、AT-749-4-E-13、AT-749-4-E-14、AT-749-4-E-15、AT-749-4-E-16、AT-749-4-E-17 |
| AC-SI-49-5 | AT-749-5-1、AT-749-5-E-1 |
| AC-SI-49-6 | AT-749-6-1、AT-749-6-2、AT-749-6-3、AT-749-6-E-1 |
| AC-SI-49-7 | AT-749-7-1、AT-749-7-E-1、AT-749-7-2 |
| AC-SI-49-8 | AT-749-8-1、AT-749-8-2、AT-749-8-3 |
| AC-SI-49-9 | AT-749-9-1、AT-749-9-2、AT-749-9-3、AT-749-9-E-1、AT-749-9-4 |
| AC-SI-49-10 | AT-749-10-1、AT-749-10-2、AT-749-10-3、AT-749-10-E-1 |
| AC-SI-49-11 | AT-749-11-1、AT-749-11-2、AT-749-11-E-1 |
| AC-SI-49-12 | AT-749-12-1、AT-749-12-2、AT-749-12-3、AT-749-12-4、AT-749-12-5、AT-749-12-6 |
| AC-SI-49-13 | AT-749-13-1、AT-749-13-E-1 |
| AC-P7-090-1～090-5 | AT-790-1-1、AT-790-1-E-1、AT-790-2-1、AT-790-3-1、AT-790-4-1、AT-790-5-1、AT-790-5-E-1、AT-790-4-2 |

| FR | 涵蓋的 AC |
|---|---|
| FR-SI-47 | AC-SI-47-1～47-15（15 條） |
| FR-SI-48 | AC-SI-48-1～48-5（5 條） |
| FR-SI-49 | AC-SI-49-1～49-13（13 條） |
| 自增 | AC-P7-090-1～090-5（5 條；AT 編號為 `AT-790-1-*`～`AT-790-5-*`） |

AC 共 38 條（PRD 新增 33 條＋自增 5 條），皆有 AT。

---

## 6. 真機驗證項（V 項；不入 AT；RTM 標「真機待驗」，鍵停 RELEASE_READY 至全部完成或如實標「未達成」）

| 編號 | 內容 | 通過判準 | 失敗時 |
|---|---|---|---|
| V-P7-1 | **非提權註冊可行性**：在**非系統管理員**的 PowerShell 跑 `python tools\selfimproving.py sched arm --push-only`（`sched_auto_push` 為 true；不呼叫巡邏安裝器，與巡邏任務是否已裝無關；R-17） | `Get-ScheduledTask -TaskName AutoSDD_SI_Push \| Get-ScheduledTaskInfo` 的 `NextRunTime` 為非空值、`Principal.LogonType` 為 `Interactive`、`UserId` 為目前使用者；輸出含 `push_task_credential=` | 回 `SCHED-ELEVATION-REQUIRED`：安裝路徑＝**以系統管理員 PowerShell 重跑 `sched arm --push-only`（或不帶旗標的 `sched arm`，推送段與巡邏段獨立）**，任務主體仍是登入使用者（`-UserId` 取呼叫端、AT-749-12-3 回讀驗證）；兩條路徑皆失敗＝本鍵不得 RELEASE，回 SA（不改用 S4U、不存密碼） |
| V-P7-2 | 快照真機：兩次真實心跳後 `patrol.json` 的 `generated_at` 前進；Console 鍵的唯讀 bind 讀到同一份（與 Console 鍵 V 項合併驗） | 容器內 `generated_at` ＝主機檔 | Docker Desktop 目錄 bind 看不到 `os.replace` 後新檔（PRD §10 風險）⇒ 改 Bridge 每次重新 open（Console 鍵處置） |
| V-P7-3 | **互動登入下真推送**：先由互動主控推送所有舊提交；造一個帶兩 trailer 的巡邏式提交（拋棄式 PROP 或真 M 類 promote）；等 ≤2 個心跳 | 遠端 `main` 前進到該 sha；`push/results/<sha12>.json` 為 `PUSH-OK`；`Get-ScheduledTaskInfo` 的 `LastTaskResult` 為 0；快照 `push.state` 為 `ok`；pre-push 閘門真跑完（十分鐘以上也不被牆鐘殺：`sched_push_wall_minutes`＝45） | 依碼處置；`PUSH-AUTH` 見 V-P7-6 |
| V-P7-4 | **未登入**：鎖定或登出使用者後造同型提交、等 >2×心跳＋5 分 | 快照 `push.state` 為 `waiting-login`、`text`＝「等使用者登入後自動推送」；重新登入後 ≤1 個心跳內自動推送 | 狀態判錯⇒修 `pushguard` |
| V-P7-5 | 拋棄式 clone＋本機 bare 遠端：真 `pre-push` 失敗、non-fast-forward、睡眠逾牆各一次 | 分別得 `PUSH-HOOK-FAILED`、`PUSH-REJECTED`、`PUSH-WALL-EXCEEDED`；同 sha 第二次不再推（`PUSH-ATTEMPTS-EXHAUSTED`）；牆鐘殺後無孤兒 `git`／`bash` 行程 | 分類表依真輸出修訂（TCS 勘誤） |
| V-P7-6 | 認證輸出樣本：拋棄式 clone 指向真遠端 URL，`-c credential.helper=` 清空、`GIT_TERMINAL_PROMPT=0`，`git push --dry-run` 取真輸出 | 輸出被分類為 `PUSH-AUTH`（不執行真推送；不動使用者憑證） | 分類表加樣本（TCS 勘誤） |
| V-P7-7 | M 類真機：下一個真實 M 類 PROP（或拋棄式記憶目錄＋夾具 repo）走完 sandbox→verify→（掌舵者 Console 決定 promote）→promote→commit→快照 | 記憶檔後像符合、無 `POSTIMAGE-MISMATCH`；S4U 巡邏任務環境能解析到記憶目錄（`MEMORY-DIR-UNRESOLVED` 不出現；若出現且原因為 `CLAUDE_CONFIG_DIR` 只在互動視窗設定，記為環境差異並於 SOP 註明） | 見 AC-SI-48-2 的碼；環境差異寫入 SOP，不寫死路徑 |
| V-P7-8 | macOS：`launchctl` 載入 `AutoSDD_SI_Push` 後以 keychain 憑證推送 | **標「未驗」**（無 macOS 實機）；mac 邊界＝睡著的 Mac 不推送（同 P4） | — |
| V-P7-9 | **端到端不開 CLI（R-18；第一波範圍的總驗收）**：唯一允許的人工前置＝凍結評估集（`heldout-freeze`，凍結者≠提案者）與由主控／無人運轉產生提案；之後全程只用 Console 與巡邏器：①Console 對該 PROP 下 `approve`→巡邏心跳入帳、`sandbox`→`verify`→發卡；②Console 詳情看到 patch、評估集狀態、驗證證據與「下一步」；③Console 下 `promote`（NE 則勾未驗採納）→巡邏 `promote`→本機 commit（帶兩 trailer）；④`AutoSDD_SI_Push` 自動推送；⑤Console 巡邏狀態卡顯示 `push.state:"ok"`、遠端 `main` 含該 commit；全程不開 PowerShell 跑任何 `selfimproving.py` 動詞（`sched arm` 安裝除外）。本項與 Console 鍵 §6.2 的端到端項互引、RTM 兩鍵各列一行 | 各步 Console 畫面與 `patrol.json`、`push/results`、遠端 sha 皆吻合；`Get-ScheduledTaskInfo` 的 `LastTaskResult` 為 0 | 依碼處置；任一步需要開 CLI＝記為缺口，回 SA |

## 7. SOP-REQ（對 SOP 的必含片段要求；由 AT-747-14-* 與 AT-790-1～3 機械鎖）

| 編號 | SOP 位置 | 必含 |
|---|---|---|
| SOP-REQ-1 | 〈held-out 目錄〉 | `min_heldout`（值現查 `params.json`）、`HELDOUT-TOO-SMALL`（n<下限⇒驗證必判 NE、晉升只能走「未驗採納」式）、`NO-PROBES`、`warn HELDOUT-BELOW-MIN`（stderr、rc 0、凍結照寫） |
| SOP-REQ-2 | 〈提案檔〉 | `prop-new` 兩項前置：目標運轉須 open（`RUN-NOT-OPEN`）、運轉內須已有研究事件（`RESEARCH-MISSING`）；並指向 P5 的四問前置 |
| SOP-REQ-3 | 〈無人運轉任務書範本〉第 7 步 | 占位符 `<MIN_HELDOUT>`；「案例數對照下限；不足時照實凍結並在 handback〈卡在哪〉寫『案例 n＜下限，驗證必判 NE』」 |
| SOP-REQ-4 | 〈巡邏與無人運轉（P4）〉開頭句、〈安裝與憑證〉、〈每心跳做什麼〉、〈停用與逃生口〉 | 「巡邏器本體不 push」；第二支任務 `AutoSDD_SI_Push` 的安裝（`sched arm` 一併）與憑證（`Get-ScheduledTask … NextRunTime`）；步 1 入帳碼進快照、步 4 M 類帶 `--memory-dir`、快照寫入（心跳之後，**不是第六步**、不進 stdout 與 `--json` 的 `steps`）；`AUTOSDD_SI_PATROL_OFF` 時快照 `off:true`（OFF 路徑不取鎖、不加日誌行）；`sched arm --push-only`、`sched disarm --push-only` |
| SOP-REQ-5 | 新節〈自動推送（P7）〉 | 守門三條件與前置序、`push-run` rc 契約、結果碼與處置表、同 sha 不重試、遷移期須互動主控推一次舊提交、macOS 對等載具、「使用者未登入時不推送」、停用（`sched_auto_push=false`）與逃生 |
| SOP-REQ-6 | 新節〈巡邏快照與 M 類自動推進（P7）〉 | `patrol.json` 讀法、原因碼→處置對照（指向 `nextstep` 為單一真相源）、M 類記憶目錄解析與 `MEMORY-DIR-UNRESOLVED`、前／後像碼處置 |
| SOP-REQ-7 | 〈rc 契約表〉 | `push-run` 一列（0／1／3） |

---

## 📋 SCG 檢核表（本檔作者自檢；QA 須獨立重驗，不得採信本欄）

| Gate | 檢核 | 現況 |
|---|---|---|
| SCG-0 | 每條 FR 有 AC、每條 AC 有 Given／When／Then 可機械判定的 AT | □ 待 QA（AC 38 條皆有 AT，見 §5） |
| SCG-0 | 無「待定」「之後再看」；真機項只在 §6 | □ 待 QA |
| SCG-1 | 元件落點照根 `CLAUDE.md`〈根層模組落點〉填寫（PRD §9.9.1）；新檔不散落 | □ 待 QA |
| SCG-2 | 重大決策（巡邏器永不推送）有 ADR-SI-19；S4U 與互動型任務的取捨有證據（P4 安裝器註解：S4U 註冊需提權、Interactive 在未登入時不跑） | □ 待 QA |
| SCG-3 | CLI 契約（`push-run`）、檔案契約（`detail`、`patrol.json`、`push/`）完整；無 OpenAPI delta | □ 待 QA |
| SCG-4 | 實作後 AT 全綠、突變鏡、範圍守衛、真機 V 項 | □ 實作後 |
| 反 Goodhart | `nextstep`／快照只描述現況，不產生分數、不接閘門、不進 M1～M5 | □ 待 QA |
| 純度 | `propdetail` 不讀家目錄 held-out；`pushguard` 不 import `runner`；推送只在 `patrolpush` | □ 待 QA（AT-747-4-E-2、AT-749-6-E-1、AT-790-1-*） |

---

## 附錄 A　原因碼表（`nextstep.REASON` 的規格；白話 `text` 由實作者依下列「語意」撰寫，≤80 字元、單行；`who`／`permanent` 為判準）

`who` 五值：掌舵者、巡邏器、無人運轉、主機管理者、無。`permanent`：條件不解除不會自動入帳（需人處理）＝true。

### A.1 入帳被拒碼（快照 `ingest[]`）

| 碼 | permanent | who | 語意 |
|---|---|---|---|
| `STALE-CARD` | true | 掌舵者 | 提案卡面已更新，你按的是舊卡面；請看新卡面重新決定 |
| `CARD-CHANGED`、`CARD-NOT-ISSUED` | true | 掌舵者 | 卡面變更或尚未發卡；請等新卡面 |
| `PRECONDITION-STATE`、`STATE-ILLEGAL`、`TRANSITION-ILLEGAL` | true | 掌舵者 | 提案目前的狀態不允許這個決定（可能已被處理） |
| `PRECONDITION-VERDICT`、`PROMOTE-FORM-MISMATCH` | true | 掌舵者 | 決定的式樣與驗證結果不符（NE 須用「未驗採納」式） |
| `PROMOTE-PREMISE-ROLLBACK`、`PROMOTE-PREMISE-TOUCHED` | true | 掌舵者 | 沙盒前提不成立（回滾乾跑或觸及範圍），不能晉升 |
| `ROUTE-VERB-MISMATCH`、`ROUTE-HANDOFF`、`KIND-MISMATCH` | true | 掌舵者 | 這種提案不能用這個決定（轉交型與迴圈型動詞不同） |
| `NOT-IN-COOLDOWN`、`NOT-SUSPENDED`、`RUN-MISMATCH`、`RUN-NOT-FOUND` | true | 掌舵者 | 解除或恢復的對象狀態不對或已不存在 |
| `PROP-NOT-FOUND`、`OBS-NOT-FOUND`、`OBS-ARCHIVED`、`NOT-OPEN` | true | 掌舵者 | 找不到對象，或觀察已不是 open |
| `REASON-CLASS-MISSING`、`REASON-CLASS-INVALID`、`REASON-CLASS-UNEXPECTED`、`REASON-CLASS-MISMATCH`、`REASON-EMPTY`、`DISPOSITION-INVALID`、`DISPOSITION-TEXT-MISSING`、`PIPE-IN-FIELD`、`CTRL-CHAR`、`FIELD-BLANK`、`FIELD-TOO-LONG`、`AUDIT-BODY-INVALID` | true | 掌舵者 | 送出的內容格式不合（理由、類別、處置欄）；請修正後重送 |
| `AUDIT-SCHEMA`、`AUDIT-REF-MISMATCH`、`AUDIT-KIND-MISMATCH`、`AUDIT-KIND-UNKNOWN`、`AUDIT-USER-FORMAT`、`AUDIT-TIME-FORMAT`、`AUDIT-SUBJECT-MISMATCH`、`AUDIT-FILE-MISSING`、`AUDIT-FILE-TOO-LARGE` | true | 主機管理者 | 稽核檔本身格式有誤，需查 Console 與主機版本是否一致 |
| `ROLE-NOT-ADMIN` | true | 主機管理者 | 送出者不是管理員，主機不受理 |
| `AUDIT-MAC-MISMATCH` | true | 主機管理者 | 簽章不符：金鑰錯誤或稽核檔被改過 |
| `AUDIT-KEY-MISSING`、`AUDIT-KEY-UNKNOWN` | **false** | 主機管理者 | 主機沒有或找不到對應金鑰；修好後下一心跳自動入帳 |
| `LOCK-BUSY`、`LEDGER-WRITE-FAILED`、`HOME-UNWRITABLE`、`GIT-UNAVAILABLE`、`STATE-CHANGED` | **false** | 巡邏器 | 暫時性衝突或寫入失敗；下一心跳自動重試 |
| `AUDIT-REF-REUSED` | true | 主機管理者 | 這個稽核編號已入帳過（重複送出），不會再入帳；請看帳本是否已有對應結果（P4 D-IMP-6 (4)：已入帳的編號不再重試） |
| `REG-STALE`、`REGISTRY-*`、`REG-*` | true | 掌舵者 | 研究來源登記同步被拒；請在 Console 重新同步 |
| `PERIOD-OUT-OF-RANGE`、`SCHED-QUOTE-REQUIRED`、`SCHED-NOT-ENABLED` | true | 掌舵者 | 排程設定不被接受（週期超界或未啟用） |
| 其他未登記碼（通用列） | true | 主機管理者 | 主機拒收（碼 {detail}）；請讀巡邏日誌 |

### A.2 依帳本推導的狀態（`nextstep.of`；`props[].code`／`detail.next.code`）

| 狀態與條件 | code | who | 語意 |
|---|---|---|---|
| `proposed`、route `loop` | `WAIT-DECISION` | 掌舵者 | 等你核准、否決或退回 |
| `proposed`、route `handoff:*` | `WAIT-HANDOFF` | 掌舵者 | 等你決定是否轉交給對應流程 |
| `approved`、無凍結 | `NO-HELDOUT` | 主機管理者 | 尚未凍結評估集；需有人用 `heldout-freeze`，巡邏器不會自己湊 |
| `approved` 或 `sandboxed`、已凍結且 n＜min | `HELDOUT-BELOW-MIN` | 巡邏器 | 會照常驗證，但案例數低於下限，驗證必判 NE（未驗證） |
| `approved`、已凍結（n≥min 或 min 未知） | `WAIT-SANDBOX` | 巡邏器 | 等巡邏器下一次心跳做沙盒套用 |
| `sandboxed`（n≥min） | `WAIT-VERIFY` | 巡邏器 | 等巡邏器下一次心跳做驗證 |
| `verified`、verify 後尚無 `card` | `WAIT-CARD` | 巡邏器 | 驗證完成，等巡邏器重發卡面 |
| `verified`、已發卡、無待決 promote、verdict PASS | `WAIT-PROMOTE-DECISION` | 掌舵者 | 驗證通過，等你決定是否晉升 |
| 同上、verdict NE | `WAIT-PROMOTE-DECISION` | 掌舵者 | 驗證未能判定（NE），要晉升須勾「未驗採納」；否則不晉升 |
| 同上、verdict FAIL | `WAIT-PROMOTE-DECISION` | 掌舵者 | 驗證未通過（FAIL），只能退回或不晉升 |
| `verified`、有待決 promote | `WAIT-PROMOTE` | 巡邏器 | 你已決定晉升，等巡邏器下一次心跳套用 |
| `promoted`／`measuring`／`closed`、待回滾≥1 | `WAIT-ROLLBACK` | 巡邏器 | 你已決定回滾，等巡邏器下一次心跳執行 |
| `promoted`／`measuring`、無待回滾 | `MEASURING` | 無 | 已晉升，量測成效中 |
| `closed` | `CLOSED` | 無 | 已結案 |
| `returned` | `WAIT-REVISION` | 主機管理者 | 已被退回；需有人用 `prop-revise` 修訂後重送（第二波起可由 Console 請求） |
| `rejected`、冷卻中 | `COOLDOWN` | 掌舵者 | 已否決並進冷卻；可由你解除 |
| `rejected`、冷卻已過 | `REJECTED` | 無 | 已否決 |
| `handed-off` | `HANDED-OFF` | 無 | 已轉交對應流程 |
| 其他 | `UNKNOWN-STATE` | 無 | 狀態未知 |

### A.3 巡邏器本心跳的 note（覆蓋 A.2；只活一個心跳）

| code | who | 語意 |
|---|---|---|
| `dirty-tree` | 主機管理者 | 工作樹有非 SI 自有改動，巡邏器不晉升／回滾；請先提交或還原 |
| `PUSH-IN-PROGRESS` | 巡邏器 | 正在推送，等推送結束後再晉升／回滾 |
| `MEMORY-DIR-UNRESOLVED` | 主機管理者 | 巡邏器找不到記憶目錄 {detail} |
| `PREIMAGE-MISMATCH` | 主機管理者 | 記憶檔在驗證後被改過，需重新上卡 |
| `POSTIMAGE-MISMATCH` | 主機管理者 | 晉升後記憶檔與預期不符，請人工檢查（不自動回滾） |
| `COMMIT-FAILED` | 主機管理者 | 本機 commit 失敗（可能是 git hook 拒絕）；需人處理，不重試 |
| `COMMIT-LEDGER-RULE` | 主機管理者 | 帳本或提案檔有不合規則的改動，巡邏器沒有提交，請人工檢查 |
| `COMMIT-LEFTOVER` | 主機管理者 | 還有不在本次提交範圍的相關未提交檔（{detail}），巡邏器沒有提交它們 |
| `COMMIT-RECORD-FAILED` | 主機管理者 | 提交已完成但巡邏器的提交紀錄寫入失敗，這個提交不會自動推送，請人工檢查後推送 |
| `APPLY-FAILED`、`NON-EVOLVABLE-NOW`、`DIGEST-MISMATCH`、`STATE-NOT-VERIFIED`、`NO-PROMOTE-DEC`、`NO-ROLLBACK-DEC`、`TREE-CHANGED`、`ROLLBACK-NOT-EXACT`、`MEMORY-DIR-MISSING` | 主機管理者 | 晉升／回滾被前置檢查擋下；碼為原因，詳見日誌 |
| `SANDBOX-NOT-APPLIED`、`SANDBOX-EXPORT-FAILED`、`SANDBOX-APPLY-TIMEOUT`、`TOUCHED-SUPERSET`、`ROLLBACK-DRYRUN-FAILED` | 主機管理者 | 沙盒套用失敗；提案需退回或修訂 |
| 其他 `_step` 失敗碼（`first_code`） | 主機管理者 | 巡邏器的這一步被拒（碼 {detail}）；請讀日誌 |

### A.4 推送（快照 `push.code`／`push.text`；每碼的 `state`、`retry` 與**固定白話句**；`text` 一字不改，但 `{detail}` 處填入細節）

| code | state | retry | who | 固定白話句 |
|---|---|---|---|---|
| `PUSH-OFF` | off | null | 無 | 自動推送已關閉 |
| `PUSH-RUNNING` | running | null | 巡邏器 | 正在推送，請稍候 |
| `PUSH-OK` | ok | null | 無 | 已推送成功 |
| `PUSH-NOT-AHEAD` | idle | null | 無 | 沒有待推送的提交 |
| `PUSH-NOT-MAIN` | blocked | null | 主機管理者 | 目前不在 main 分支或沒有 origin/main 上游，不自動推送 |
| `PUSH-DIRTY-TREE` | blocked | null | 主機管理者 | 工作樹有未提交改動，請先提交或還原 |
| `PUSH-FOREIGN-COMMITS` | blocked | null | 主機管理者 | 待推送的提交含非巡邏器產生者（{detail}），請由人推送 |
| `PUSH-APP-KIND-INVALID` | blocked | null | 主機管理者 | 提交的 APP 標記不是晉升或回滾（{detail}），疑似照抄格式，不自動推送 |
| `PUSH-APP-REUSED` | blocked | null | 主機管理者 | 同一個 APP 標記出現在多個提交（{detail}），不自動推送 |
| `PUSH-PATH-OUTSIDE` | blocked | null | 主機管理者 | 提交改了允許範圍外的檔案（{detail}），不自動推送 |
| `PUSH-CONTENT-MISMATCH` | blocked | null | 主機管理者 | 提交內容與帳本記錄不符（{detail}），不自動推送 |
| `PUSH-NOT-RECORDED` | blocked | null | 主機管理者 | 這個提交沒有巡邏器的紀錄，請人工檢查後推送（{detail}） |
| `PUSH-RECORD-MISMATCH` | blocked | null | 主機管理者 | 提交與巡邏器的紀錄不符（{detail}），請人工檢查後推送 |
| `PUSH-LEDGER-RULE` | blocked | null | 主機管理者 | 提交對帳本或提案檔的改動超出允許規則（{detail}），不自動推送 |
| `PUSH-GIT-UNAVAILABLE` | blocked | null | 主機管理者 | git 不可用或逾時，無法判定推送條件 |
| `PUSH-HOOK-FAILED` | failed | never | 主機管理者 | 推送前的本機檢查沒通過，請看檢查輸出後由人推送 |
| `PUSH-REJECTED` | failed | never | 主機管理者 | 遠端有新提交，請先整合（rebase 或 merge）再由人推送 |
| `PUSH-AUTH` | failed | never | 主機管理者 | 遠端認證失敗，請在互動視窗手動 git push 一次更新憑證 |
| `PUSH-WALL-EXCEEDED` | failed | wait／exhausted | 巡邏器 | 推送逾時被終止；稍後自動重試（用盡後請由人推送） |
| `PUSH-FAILED` | failed | wait／exhausted | 巡邏器 | 推送失敗（多為網路）；稍後自動重試（用盡後請由人推送） |
| `PUSH-INTERNAL-ERROR` | failed | null | 主機管理者 | 推送程式發生未預期錯誤（{detail}），請查 push 目錄的 last_error |
| `PUSH-PENDING` | pending | null | 巡邏器 | 等推送任務下一次執行（每個心跳一次） |
| `PUSH-WAITING-LOGIN` | waiting-login | null | 主機管理者 | 等使用者登入後自動推送 |
| （push-run 輸出碼，不單獨成快照態）`PUSH-RETRY-WAIT`、`PUSH-ATTEMPTS-EXHAUSTED`、`PUSH-RESULT-WRITE-FAILED` | — | — | — | 快照以最近一筆結果的碼加 `retry` 表達；`PUSH-RESULT-WRITE-FAILED` 於快照呈現為 `PUSH-INTERNAL-ERROR` |

### A.4b `push.state` 判定序（單一對映表；互斥，先中者定案；AT-749-10-2 表驅動窮舉）

輸入：`enabled`（`sched_auto_push`）、`current`（`push/current.json` 且 pid 存活未逾牆）、`guard`（本心跳 `pushguard.evaluate` 的前置結果，含 `ahead`）、`last`（HEAD sha 對應的 `push/results/<sha12>.json`，無則 null；`ahead=0` 時取最近一筆 `PUSH-OK`）、`err`（`push/last_error.json`）、`tick`（`push/tick.json` 的 `tick_at`）。

1. `enabled=false` ⇒ `off`／`PUSH-OFF`。
2. `current` 存活 ⇒ `running`／`PUSH-RUNNING`。
3. `guard.ahead=0` ⇒ 最近一筆結果碼為 `PUSH-OK` ⇒ `ok`／`PUSH-OK`；否則 `idle`／`PUSH-NOT-AHEAD`。
4. `guard` 回前置阻擋碼（`PUSH-NOT-MAIN`、`PUSH-DIRTY-TREE`、`PUSH-FOREIGN-COMMITS`、`PUSH-APP-KIND-INVALID`、`PUSH-APP-REUSED`、`PUSH-PATH-OUTSIDE`、`PUSH-CONTENT-MISMATCH`、`PUSH-NOT-RECORDED`、`PUSH-RECORD-MISMATCH`、`PUSH-LEDGER-RULE`、`PUSH-GIT-UNAVAILABLE`）⇒ `blocked`／該碼。
5. `last` 為失敗結果且（碼屬不可重試〔`PUSH-HOOK-FAILED`／`PUSH-REJECTED`／`PUSH-AUTH`〕⇒`retry:"never"`；可重試碼且 `attempts ≥ sched_push_attempts_max` ⇒ `retry:"exhausted"`；可重試碼且距 `finished_at` 未滿 `sched_push_retry_minutes` ⇒ `retry:"wait"`）⇒ `failed`／`last` 的碼。
6. `err` 存在且其 `at` 晚於 `last.finished_at`（無 `last` 則存在即可）⇒ `failed`／`PUSH-INTERNAL-ERROR`（`retry:null`）。
7. 其餘（守門可推，含「可重試碼已過間隔、下一次執行會重試」）：`tick` 在 `2×sched_heartbeat_minutes＋5 分` 內（嚴格不大於）⇒ `pending`／`PUSH-PENDING`；`tick` 缺、非 ISO 或逾界 ⇒ `waiting-login`／`PUSH-WAITING-LOGIN`。

`push.code` 與 `push.text` 恆取自本表與 A.4（`text` 的 `{detail}`：`PUSH-FOREIGN-COMMITS` 等各守門專屬碼填第一個不符提交的 sha 前 8 碼，`PUSH-INTERNAL-ERROR` 填 `err.text`）。
### A.5 驗證 `reasons` 碼（`detail.verify.reasons[].text`）

`VERIFY_REASONS` 全部成員（現查 `evspec.VERIFY_REASONS`）：至少含 `NO-PROBES`（沒有探針，驗證無法判定）、`CARRIER-PROOF-FAILED`（載具自證失敗）、`HELDOUT-DIGEST-MISMATCH`（評估集 digest 不符）、`HELDOUT-TOO-SMALL`（評估集案例數低於下限）、`HELDOUT-EXPOSED`、`EXPOSURE-UNKNOWN`、`PROBE-TIMEOUT`、`BASELINE-NOT-RED`（修復前探針沒有變紅）、`PATCHED-NOT-GREEN`（套用後探針仍紅）、`MUTATION-NOT-RED`、`MUTATION-ABSENT`、`SANDBOX-NOT-APPLIED`、`SANDBOX-EXPORT-FAILED`、`SANDBOX-APPLY-TIMEOUT`、`TOUCHED-SUPERSET`、`ROLLBACK-DRYRUN-FAILED`；`who` 一律「無」（說明性）；`REASON` 須涵蓋 `VERIFY_REASONS` 的**每一個**成員（AT-747-12-1 以 `set(VERIFY_REASONS) ⊆ set(REASON)` 判）。

### A.6 排程跳過與運轉等待碼（快照 `schedule.current`／`schedule.last_skip`／`runs.waiting[]`；只顯示、不改 R156 行為）

| code | who | 固定白話句 |
|---|---|---|
| `SCHED-DISABLED` | 掌舵者 | 自動演化排程目前停用（Console 立即啟動仍可用） |
| `SCHED-CELL-RAN` | 無 | 本期已經跑過一次，等下一期 |
| `SCHED-DUE` | 巡邏器 | 本期到期，巡邏器正在開運轉 |
| `SKIP-BLACKOUT` | 無 | 現在在黑窗時段（{detail}），不開運轉 |
| `SKIP-QUOTA-BAND` | 無 | 額度帶不允許（{detail}），不開運轉 |
| `SKIP-OTHER-DRIVER` | 無 | 近期有人在互動視窗工作，巡邏器先不開運轉 |
| `SKIP-DIRTY-TREE` | 主機管理者 | 工作樹有非自我進化的未提交改動，不開運轉 |
| `SKIP-RUN-OPEN` | 主機管理者 | 已有未關運轉（{detail}），排程與立即啟動都會等它關閉（第二波起可由 Console 處理） |
| `SKIP-SPAWN-FAILED` | 主機管理者 | 無人運轉主控無法啟動（{detail}），請查巡邏日誌 |
| `RUN-BUSY` | 巡邏器 | 已有進行中的無人運轉，這個運轉等它結束後再啟動 |

### A.7 匯出 `ne` 新碼（`detail` 相關；其 `ne` 項帶 `text`）

| code | who | 固定白話句 |
|---|---|---|
| `PATCH-UNREADABLE` | 主機管理者 | 讀不到提案的 patch 檔 |
| `BODY-UNREADABLE` | 主機管理者 | 讀不到提案本文檔 |
| `OBS-LEDGER-UNREADABLE` | 主機管理者 | 讀不到觀察帳本，來源觀察無法顯示 |
| `HELDOUT-MIN-UNKNOWN` | 主機管理者 | 讀不到評估集下限參數，無法判斷案例數是否足夠 |
| `TIMELINE-TRUNCATED` | 無 | 事件太多，時間線只顯示最後 500 筆 |
---

## 勘誤（凍結後的訂正；內文已就地訂正、被訂正的原文逐字保留於下表；走 spec-refreeze）

| 編號 | 日期 | 位置 | 原文 | 訂正 | 原因與證據 |
|------|------|------|------|------|------------|
| （凍結前留空） | | | | | |
