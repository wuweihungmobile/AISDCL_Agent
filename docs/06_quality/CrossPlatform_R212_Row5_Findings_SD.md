VERDICT: APPROVE
設計↔實作逐點相符；不下令時 `decide()` 於 6000 組隨機語料逐位元不變、有授權的 23000 餘組語料量到 0 筆方向／底線違反；無 P≤2，P3 六項屬訊息／測試覆蓋，當輪可處置。

# CrossPlatform R212 第五列 SD（系統設計師）鏡 findings：清倉模式（DEF-200-528）設計↔實作一致性

> 角色與紀律：唯讀複審鏡。手動重現一律在隔離環境做（`AUTOSDD_TRACE_DIR`／`AUTOSDD_QUOTA_CACHE_DIR`／`HOME`／`TMPDIR` 皆指向 scratchpad 子目錄），真 `~/.autosdd` 只做唯讀讀取（見〈五〉末的未動證明）。依根 CLAUDE.md〈守衛面准入〉「量、不挖」：本檔所有構造性實驗只用來量既有判準（規格不變式、逐字不變、方向鎖），不作對抗搜尋；構造性命中最高計 P4。對主控骨架與前六次宣稱一律零信任，宣稱與現況不符處在〈一〉〈六〉寫明。

## 〈一〉對四問宣稱的逐項核對表

### 一-A 四問宣稱（本鏡射程內）

| 宣稱 | 我驗到的 | 判定 |
|---|---|---|
| Q1 喚醒鏈收斂：接縫真機整段跑過；判決 22 項全過；入庫 `tools/probe/wakechain_e2e.py` | `--selftest` rc=0（strict-pass FAIL=[]／post-hoc FAIL=[] WARN=2／負對照 bypass 紅在 S2、S3、S5a、S5b）。`--judge 14fb33dc-4ffc-40c9-b62b-9dcf801d02f4 --since 2026-10-12T13:16:00+08:00` rc=0：S14-core 8/8 PASS＋tail 7/7 PASS＋WARN 2（事後暫存物已清，工具設計內降級）。入庫判決器共 17 列（15 PASS＋2 WARN）；「22 項」是未入庫的 judge4.py 的項數。工具檔頭自陳 `--run` 只被 mock 驗過、未在真機整段跑過（R212 範圍內），覆蓋面僅 NO_PROGRESS_STOP＋S14 早退。「Windows 零真機樣本／24h 連續閉環未做」的劃界與工具檔頭、證據檔〈八〉一致 | 成立；措辭須把「judge4（22）」與「入庫工具（17）」分開寫，並帶出 `--run` 未實跑（見〈六〉8） |
| Q2 PRD 功能完成、逐功能 E2E | PRD §16.2 表自計 72 列：➖33／⏸29／📎8／✅2；加矩陣原判 ✅29 ⇒ 全母體 ✅31／➖33／⏸29／📎8（合計 101），與修訂表 v2.1.19（A4 ⏸→✅）算術一致；§16.3 凍結快照（✅29／⏸31）刻意不重算。不變式 8 讀碼：`boot_self_check.permission_bypass_verdict` 兩要件（旗標明確為真＋偵測到容器）缺一拒絕；只認 Linux；生產接線在 `AutoClaude/autoclaude/main.py` 行 140～158（`executor.permission_mode`＋`claude.extra_args` 兩條路都餵）、非零 rc 停機（行 254）；測試 144 項通過 | 本鏡射程（A4 清倉＋不變式 8）內成立；對「所有功能都已完備」整句不成立——仍有 ⏸29／📎8（帳面自己如實登記），本鏡不為其背書 |
| Q3 .env 同步：標準＝`env.shared`＋出廠 `ENV_SPEC`；本機 `.env` 只放例外；四層載入鏈；`--env-doctor [--fix]`；`post-merge` 自動對齊 | 載入鏈（高→低）行程 env > `AutoClaude/.env`（引擎 3 鍵）> 根 `.env` > `env.shared` > 出廠。harness 側 `quota_env_layers.merged_file_env`＋`quota_gate.policy_env`；引擎側 `autoclaude/utils/config.py::_ENV_FILES`（`AutoClaude/.env`、根 `.env`、`env.shared`，第一個非空命中贏）同序，雙邊對跑鎖在 `test_quota_env_layers`（含於 400 項測試，全綠）。`tools/git-hooks/post-merge` 每條路徑皆 `exit 0`（advisory）；可自動修旗標 `redundant|shadows-shared|dead|engine`、需人判斷旗標 `unknown|bad-value|duplicate|unreadable|missing-shared|bom`（混合情境一檔不動）；`AUTOSDD_UNATTENDED` 鍵存在即只體檢不修；`--fix` 先 `shutil.copy2` 備份成 `.env.bak.<UTC>` 再寫。真 repo 根 `--env-doctor` rc=0（`env.shared` 4 鍵、`.env` 4 鍵但無有值行、`[empty-local]`）。引擎取檔內第一個同名行、harness 取最後一個，`duplicate` 旗標已把這個分歧列為需人判斷 | 成立；Windows 真機同步未驗，帳面已如實標註 |
| Q4 不需要馬上切 Windows | 非本鏡射程；與證據檔〈八〉Windows 待驗清單不矛盾 | 未驗（非本鏡射程） |
| 宣稱數字：commit 1818de87（29 檔）／回填 8395affa／六支 CI 全 success／根層全套 rc=0／AutoClaude 全套／帳本未結 0 | 本鏡未驗（QA 鏡射程）。另記工作樹現況：`python tools/check_defect_log_crossref.py` rc=1（見〈五〉9、〈六〉11） | 未驗 |

### 一-B 清倉模式（DEF-200-528）設計↔實作逐點對帳

依據：`docs/04_planning/PRD_Amendment_R108_BurnDown_Addendum.md`（§3～§6、§8）、`docs/04_planning/AutoSDD_Adjudication_Record_R110.md` 第 46～52 行 QB1～QB6、證據檔〈二-2〉BD-2′。

| # | 條款 | 實作座標 | 我驗到的 | 判定 |
|---|---|---|---|---|
| 1 | 落款六欄＋id（附錄 §3.2） | `quota_burndown.FIELDS`／`read_directive`（缺檔、壞 JSON、schema 不符、前五欄非空字串、後兩欄非 list ⇒ `None`） | 真落款（唯讀讀取）六欄俱全：`id=45c49b8e35`、`axis_kind=weekly_all`、`until_resets_at=2026-10-17T17:59:59.540762+00:00`（伺服器原字串）、`core_signature`、`readings_at_issue` | 相符 |
| 2 | 生效判準全合取、解不出＝不生效（§3.3） | `verdict()` 六步＋`active()`（任何例外 ⇒ `None`） | 六步＝落款存在／OFF 未設／被點名軸非 fallback、scoped（QB4）／`core_signature` 全等／軸仍在讀數／`now < until` 且解得出（嚴格小於；附錄的「解得出」與「未過期」併為一步）。隔離重現：`until` 為過去、naive、`""`、`garbage`、null 五種，`--status` 皆 rc=1 且 decide 無清倉字面；方案指紋改變（快取去掉 account_key）、被點名軸消失皆 rc=1 | 相符（六步＝附錄六合取，其中兩項併一步，另加底線②③一步） |
| 3 | `until_resets_at` 伺服器原字串（§3.2） | `issue()` 寫 `named.resets_at` 原值 | 真落款字串與快取原字串一致，未轉本地。注意：實作以「時間比較」判效期，不比對本次讀數同軸字串；真快取同軸 `resets_at` 於 14 分鐘內自 `…17:59:59.540762` 漂到 `…18:00:00.301550`，故精確字串比對不可行 | 相符；附錄 §3.1／§7.3「字串不匹配自動失效」由時間比較承擔（P4-5） |
| 4 | kill-switch 只准關（QB3） | `ENV_SPEC` escape 列、`attr=None`；`active()`／`verdict` 各讀一次；`.env.example` 重生 +2 行 | `AUTOSDD_QUOTA_BURNDOWN_OFF=1`：`--status` rc=1（✗ OFF 未設）、decide 回 cap=1 rec=1 band=prepare（與無落款逐字同）；任何非空白值（含 `0`／`false`／`no`）皆算「設了」＝只往關的方向；`.env` 設也有效（`policy_env(root)` 實測回 `'1'`） | 相符 |
| 5 | Q-same：被點名軸＋同窗鄰軸字串全等（§4.1／QB6） | `Burn.masks()`：`a.kind == axis_kind` 或 `resets_at` 非空且字串全等，合取 `_eligible` 與 `_in_cap_gate` | 真帳 205 列（有 resets_at 者）：`weekly_all==seven_day` 205/205、`session==five_hour` 203/203、`weekly_all==weekly_scoped` 0/204。非分軌鄰軸在真資料上字串穩定全等；分軌軸從不誤入同窗（附錄 §9-5「零容差會靜默不觸發」在目前資料上未發生） | 相符 |
| 6 | Q-cross（BD-2′，主控裁決） | `hold = named ∧ total ∧ ok`；`total`＝`Amort.total_kind` 的軸是 Q-same | 實作是〈二-2〉文字（`total_kind == 被點名軸`）的超集，Dev 自報、〈三-1〉(c) 採納，〈二-2〉文字未同步（見〈六〉3）。獨立 oracle（只用附錄／裁決文字、不呼叫實作內部函式）對 23425 組隨機狀態：實際被改動的軸 ⊆ 規格允許集合，band 只在 Q-cross 軸變、horizon 只在 Q-same 軸變，未授權改動 0 | 相符（文字須同步） |
| 7 | BD-1 乘數地板（§4.2） | `quota_pace.resolve(floor=)`：視野 label far→mid，near 不動 | `_cap_for`／`_rec_for`／`_pace_of`／`_rec_of_gate` 皆對 label 單調，夾 label 同時夾 cap／rec／聚合；地板不送加速（突變「far→near」被測試殺掉）。偏差：附錄 §4.4 值域表的 `none` 四列（被抬）在實作中不放寬——§4.1「距 reset 解得出且 ≥0」合取項使 `none` 軸不 qualifying（附錄 §4.1 與 §4.4 自身不一致，實作取保守側） | 相符（保守側偏差，見〈六〉7） |
| 8 | 夾層：`ceil=cap_notice`、None 格不動、只准往上（§4.3／QB1） | `_merge()` | 隨機 23094 組含授權語料：逐軸與聚合的 cap／rec 不收緊、不製造不設限、不超 cap_notice、原 None 格不被改成有限、amortize 取數面（`Decision.amort`）逐位元不變，違反 0；錨點① free×near rec 16 逐格不變；附錄 §0.2 的錯版 `min(max(r0,r_bd),ceil)` 被測試殺掉 | 相符 |
| 9 | 聚合順序：逐軸放寬 → min 聚合 → must-finish → model_hint（§5④／BD-8） | `decide()` 在 `gate_list` 之前呼叫 `burndown.apply` | 突變「把授權套在聚合之後的全域地板」被 BD-3／BD-8 測試殺掉；隨機語料中 must-finish 觸發集合不因授權改變、觸發時 `rec ≤ cap_prepare` 恆成立 | 相符 |
| 10 | 底線①②③＋時鐘（§5） | `_eligible()` 合取 | 隨機語料：halt 水位軸、fallback 軸、model-scoped 軸、時鐘解不出軸的逐格值，有／無授權相同，違反 0；halt 聚合 cap 仍為 0 | 相符 |
| 11 | `pace_line` 清倉段三要求（§6.1） | `Applied.text`；`quota_messages.pace_line` 尾段 | ①原值→放寬值兩數 ✓（`cap 1→8 rec 1→4`）；②未放寬軸＋理由 ✓（理由準確度見 P3-3）；③過期後消失 ✓（五種過期／壞值 until 皆無清倉字面）；另依 §9-9 並列「效期剩 N 分鐘／must-finish 門檻 5 分鐘」✓。實作同時把同一段接到 `describe()`，`--pace` 因此印兩次（P3-1） | 相符＋重複 |
| 12 | `row_of` 的 `bd`／`bd_effect` | `row_of(bd=)`／`record_burn(bd=)`；`log_decision` → `autosdd_burndown_events.jsonl` | `bd` 欄 ✓（隔離重現：下令後列帶 `"bd":"<id>"`；無授權列為 null；真帳下令後寫入的列 `"bd":"45c49b8e35"`）。`bd_effect` 不在 `row_of`，改由事件檔承載（附錄 §6.3 兩計數器的等價物）；原因＝effect 在 `decide` 之後才知，搬動 `record_burn` 會改換算比，Dev 說明成立 | 相符（`bd_effect` 住處是主控任務書的偏離，附錄只要求 `bd`） |
| 13 | CLI 三臂 rc 與不落檔（BD-7） | `issue`／`status`／`revoke`／`main` | `--issue` 點名 `weekly_scoped`、`spend`、不存在軸：rc=1 且落款檔位元組不變（`cmp`）；空 `--directive`：CLI 層 argparse rc=2（函式層 `issue()` 為 rc=1）；`--status` 生效 rc=0／不生效 rc=1；`--revoke` rc=0（無落款亦 rc=0） | 相符 |
| 14 | 不下令時 `decide()` 逐字不變 | `decide(burndown=None)`、`axes_of(relax=None)`、`resolve(floor=(),hold=())`、`band_inputs(hold=())` | 6000 組隨機狀態（含攤提、must-finish、分軌、halt 各帶）對 HEAD 與工作樹各跑 `decide`／`describe`／`pace_line`／`axes_of`，輸出 JSONL `cmp` 逐位元相同；另 4 模組 400 項、`test_context_budget_guard` 810 項全綠 | 相符 |
| 15 | 接電：兩個派工呼叫端 | `pace_report`、`quota_gate()` 帶 `burndown`；`halted_pace_text`／`draining`／relay／escalation／criteria／session_brief 不帶 | 與 Dev 報告 §0-2 一致。真機佐證（唯讀）：`autosdd_quota_stability_fable.json` `cap=4`（`last_change` 19:39:29）＝派工 hook 已在放寬值（無授權時該形狀為 cap=2）；`..._fable_pace.json` cap=2（19:34:35）＝`--pace` 標題 cap 仍在遲滯爬升。簡報未接見 P4-1 | 相符 |
| 16 | 放寬仍過遲滯（PRD §4.2.4） | `quota_stability.evaluate` 在 `decide()` 之後 | `--pace` 標題 cap 1→2（+1／≥300 s），hook 穩定值已 4；證據〈三-3〉如實寫「由遲滯維持」 | 相符 |
| 17 | Python 3.9 載具可載入 | 新模組鏈 | `/usr/bin/python3`（3.9.6）匯入 `quota_policy`／`quota_pace`／`quota_burndown`／`quota_gate` 皆成功；`--issue`／`--status`／`pace_report` 於 3.9 下 rc=0 | 相符 |
| 18 | 「授權路徑絕不成為決策路徑的故障源」 | `active()` 有 try／`apply()` 無 try | 20000 組畸形輸入（NaN／inf／負值／亂字串 resets_at／空 kind／重複 kind；其中 17105 組帶非空軸與授權）：無例外，base 路徑與授權路徑皆 0 | 相符（量測面；`apply()` 無 try 是結構事實，本量測未構成登記理由） |
| 19 | 測試承重 | `tools/tests/test_quota_burndown.py` 14 項 | 隔離複本 35 個單點突變：30 殺、5 存活——M14（寫入端 QB4 拒絕）與 M34（Q-cross 底線合取）為覆蓋缺口，M38（`--status` 的 OFF 顯示）為顯示面缺口，M35／M36 為等價／冗餘突變（見 P3-4） | 大致承重；缺口見 P3-4 |
| 20 | 附錄 §7.2 `BURNDOWN_CAP_CEILING`（只准調小的選配鍵） | 無 | 未實作；ceil 固定＝`Policy.cap_notice`（QB1 已裁 cap_notice）。屬草案選配項，方向保守 | 偏離（保守；須在附錄落地注載明，見〈六〉7） |

### 一-C 立案情境手動重現（隔離；合成讀數＝證據檔〈二-1〉：session 8%@233、weekly_all 75%@7663、weekly_scoped 41%@7663＋218 微秒、five_hour 8%@233、seven_day 75%@7663、spend 0；換算比取真帳複本 r=5.0、n=67）

```text
下令前（decide 原始決策）: cap=1 rec=1 band=prepare binding=five_hour      ← 與〈二-1〉逐字吻合
下令後（未過遲滯）      : cap=4 rec=2 band=converge binding=seven_day
  session / five_hour : band prepare→free  cap 1→8  rec 1→4   （Q-cross：攤提暫停；夾層 cap_notice）
  weekly_all / seven_day: cap 2→4  rec 1→2                      （Q-same：視野地板）
  weekly_scoped / spend : 逐格不動（未放寬：model-scoped 不納入、fallback 不納入）
```

四情境：kill-switch（rc=1、逐字同無授權）；過期 until 五種（皆不生效）；點名 `five_hour`（rc=0；只有同窗效果：session／five_hour cap 1→2，週軸「與被點名軸不同窗」不動，標題 cap=2 rec=1）；點名 `weekly_scoped`（rc=1，訊息「拒絕：kind=weekly_scoped 屬付費保險軸或模型分軌軸（底線②③；QB4：指令不得點名）」，落款檔位元組不變）。反事實重算：〈三-3〉真落款時刻的讀數（29%／78%、r=5.0）無授權為 `cap=1 rec=1 band=prepare binding=five_hour`、有授權為 `cap=4 rec=2 band=converge binding=seven_day`，與骨架宣稱一致。

## 〈二〉P≤2 清單

無。依據：設計↔實作逐點對帳 20 列全部相符或為保守側偏差（〈一-B〉）；不下令逐字不變（6000 組）；有授權的方向、底線、順序不變式於 23094／23425 組隨機語料違反 0；授權路徑於 20000 組畸形輸入未增加例外；真機佐證（hook 穩定 cap 已達 4）顯示放寬在真路徑上生效；所有未過的項目皆無暴露證據或僅影響訊息／測試覆蓋。

## 〈三〉P3（訊息誤導或附屬細節；當輪可改，不改判）

### P3-1 清倉段在 `--pace` 輸出重複兩次（任務書指定判級）

- 座標：`tools/lib/quota_messages.py` 的 `pace_line` 尾段，加 `tools/lib/quota_policy.py` 的 `describe` 尾段；`tools/lib/quota_gate.py::pace_report` 回傳字串同時含兩者。
- 重現：隔離環境（落款有效、快取新鮮）跑 `pace_report`（同 `session_resume_planner --pace` 路徑）；第 1 行（`現在可派 …｜最緊的一條＝…｜🔥清倉模式生效中（落款 …）⇒ 本次放寬：…；未放寬：…`）與第 2 行（逐軸明細末尾）各含同一段 382 字元的清倉文字（逐字相同）。真機〈三-3〉逐字亦同。
- 判準：附錄 §6.1 只要求 `pace_line()` 具名標示；`describe()` 帶同段是 Dev 為了讓 hook 阻斷訊息（`quota_throttle_message` 的 head 取 `describe`，該路徑沒有 `pace_line`）也看得到清倉脈絡。重複不影響任何決策，且「同一件事兩個數／兩處」在本 repo 屬不可信號。
- 級：P3（訊息；一次呼叫內即可恢復）。
- 建議處置：`describe()` 增參數（例：`burndown=True`），`pace_report` 第二行傳 False，hook 阻斷訊息維持帶；測試中 `assertIn(d.burndown.text, Q.describe(d))` 同步拆成兩條（`describe` 預設帶、`pace_report` 第二行不帶）。

### P3-2 幽靈鍵鎖靠旁註通過（Dev 報告 §6 第 2 點的判級）

- 座標：`tools/tests/test_context_budget_guard.py::QuotaEnvFileIsActuallyLoadedTest.test_every_key_in_the_example_is_one_the_code_reads`；其 `consumers` 元組只含 `quota_gate.py`、hook 主檔、`session_resume_planner.py`、`relay_machine.py`、`model_roles.py`。`AUTOSDD_QUOTA_BURNDOWN_OFF` 在這五支檔內唯一命中＝`tools/lib/quota_gate.py:1100` 的註解；真讀取點 `tools/lib/quota_burndown.py` 不在元組內。
- 重現：`grep -n "AUTOSDD_QUOTA_BURNDOWN_OFF" tools/lib/quota_gate.py .claude/hooks/context_budget_guard.py tools/session_resume_planner.py tools/lib/relay_machine.py tools/lib/model_roles.py` 只回 `quota_gate.py:1100` 一行（註解）。
- 判準：該鎖的 docstring 逐字「範例檔的每個鍵都必須真的有讀取點（防幽靈鍵）」；現況下把 `quota_burndown.py` 的讀取整段刪掉，此鎖仍綠（只有 BD 專屬測試會紅，kill-switch 功能面另由 `test_valid_then_each_conjunct_breaks_it` 與接電測試守住）。屬 Rule 9「測試在業務邏輯改變時必須能紅」的削弱，且是本列自己引入的形態（為過鎖在守衛面檔案寫一句旁註）。
- 級：P3（無暴露；功能面另有覆蓋）。
- 建議處置：把 `_REPO_ROOT / "tools" / "lib" / "quota_burndown.py"` 加進 `consumers` 元組（測試檔 +1 行；回歸鎖軌餘裕 4 行足夠，需同步重釘 `_FROZEN_GUARD_LINES`／sha／接鏈列）；`quota_gate.py:1099～1100` 的說明可留作文件，但不再承擔過鎖。

### P3-3 BD-9「未放寬理由」在兩類情形說錯根因

- 座標：`tools/lib/quota_burndown.py::_why`（行 137～147）與 `Burn.apply` 的 `kept` 組字（行 194～197）。成因：`hold` 遮罩對所有 eligible 且在 cap gate 的軸為真（含非短窗軸），`flagged=True` 即套用「已在放寬上限，無可再放」；而「攤提供給軸不 qualifying」沒有專屬理由。
- 重現（純函式，`decide(burndown=…)`；合成輸入）：
  1. 立案原型形狀（08-28：scoped 91% 為攤提供給軸，`model=fable`，r=5.2）：effect=`inert`，`session`／`five_hour` 的理由印「與被點名軸不同窗」，而真正的阻擋是 `Amort.total_kind=weekly_scoped`（model-scoped，QB2 α）——附錄 §9-1(b) 點名的那個根因不在畫面上。
  2. 同形狀 `model=sonnet`：`session`／`five_hour` 為 free/far cap=None rec=4（Q-cross 不享 BD-1），理由印「已在放寬上限，無可再放」，但 rec 4 < cap_notice 8，並非在上限。
  3. hook 路徑（`decide` 不帶 ratio）真實形狀 29%／78%：free 帶的 `session`／`five_hour` 被列在「未放寬：…（與被點名軸不同窗）」，其實本來就不受限。
- 判準：附錄 §6.1(2)／BD-9「授權在但結構上沒生效」必須具名且正確的理由。
- 級：P3（訊息誤導，不影響 cap／rec；真機現形狀攤提供給軸為 `weekly_all`，情形 1 尚未在真機出現）。
- 建議處置：`_why` 增兩支——`flagged` 且 `cap` 未達 `cap_notice`（或原本不受限）⇒「本軸無攤提上調可暫停（Q-cross 不享視野地板）」；rate-window 軸 `hold` 假因 `total` 假 ⇒「攤提供給軸 kind=X 不 qualifying（model-scoped／fallback／不同窗）」。補一條 08-28 形狀的文字斷言。

### P3-4 測試覆蓋缺口（突變存活）

- 座標與重現（隔離複本，單點突變後跑 `test_quota_burndown`）：
  1. M14：把 `quota_burndown.issue()` 行 254～255 的 `if kind in Q.FALLBACK_KINDS or kind in Q.MODEL_SCOPED_KINDS:` 改成 `if False:`，測試仍 rc=0。原因：`test_refusals_never_leave_a_file` 的合成快取（`put_cache`）只有 session／weekly_all／five_hour／seven_day 四軸，`("nope","weekly_scoped","spend")` 三個 kind 全由「快取沒有這一軸」分支拒絕，QB4 寫入端拒絕分支從未被區分。
  2. M34：`masks()` 的 `hold` 去掉 `ok`（底線①②③＋時鐘合取）仍 rc=0——Q-cross 的底線合取在 decide 層沒有直接測試（生產上等價：halt 水位軸 hold 回原值＝攤提上調值本就等於原值，時鐘解不出軸 `read_quota` 已整體擋掉；但規格要求的合取項沒被釘住）。
  3. M38：`verdict` 的 OFF 步驟改成恆真仍 rc=0（`active()` 另有第一行 OFF 判斷）——`--status` 的 OFF 顯示行沒有測試。
  4. 另：測試中數行「紅面」是對政策常數的算術（例：`assertGreater(max(d.cap, P.cap_prepare), 0)`、`assertGreater(swapped, P.cap_prepare)`），恆真、對生產碼改動不會紅；承重的是主斷言（35 個突變 30 個被殺）。
- 判準：Rule 9；附錄 BD-4「點名它也不行」寫入端臂、§5 底線對 Q-cross 的合取。
- 級：P3（消費端 `verdict` 步驟 3 另擋＝縱深防禦，無實害）。
- 建議處置：`put_cache` 補 `weekly_scoped`（含 `scope_model`）與 `spend` 兩軸，斷言 rc=1 且訊息含「QB4」；補一條 decide 層測試（短窗軸 pct 在 halt 邊緣／時鐘為負時，`hold` 為假、輸出等於無授權）；`--status` 在 OFF 設定下斷言輸出含 `✗ AUTOSDD_QUOTA_BURNDOWN_OFF`。證據檔措辭「每條帶合成注入紅面」改為「每條有主斷言，並就地重現錯誤版判準作對照」。

### P3-5 清倉生效時，節流期程行與降級建議仍勸人「改做不吃額度的工作／降扇出／切小模型」

- 座標：`tools/lib/quota_messages.py::throttle_horizon_line`（行 569～574）與 `model_lines`（降級建議）。
- 重現：隔離 `pace_report`（stability 檔空白、cap 直達 4）第 4 行逐字：`⏳ 這一條的 reset 在 2026-10-18T03:34:55.246210+08:00（**遠超 6 小時**） ⇒ 這個 cap 會**連續套用好幾天**（水位不變時，隨 reset 逼近才逐步放寬）。改做不吃額度的工作，或降扇出／切小模型。`，同輸出另有 `🔻 降級建議：kind=seven_day,weekly_all 已進收緊帶 ⇒ 建議派工帶 model: sonnet/haiku 續跑`。真機〈三-3〉因遲滯行佔位未印出前者，待穩定 cap 追上後才會出現。
- 判準：清倉＝操作者要求「用完」，BD-1 已預先收回遠期減速，「隨 reset 逼近才逐步放寬」不再為真，「改做不吃額度的工作」與下令意圖相反。附錄未要求改這兩句（model_hint 一字不改是附錄 §5④ 的意思），這是訊息一致性。
- 級：P3（建議性文字，不影響 cap）。
- 建議處置：`decision.burndown` 在場時，`throttle_horizon_line` 改印「清倉模式：cap 不隨 reset 逼近再放寬」或省略建議句；降級建議行維持（只建議、不影響 cap），可補一句「清倉模式下僅供參考」。

### P3-6 R213 標籤預支回歸鎖軌額度，〈三-2〉未揭露後果

- 座標：`tools/tests/test_adr_xplat001_c1c2_lock.py` 的 `_GUARD_LINES_REPIN_LOG` 新列（R213，+305）與 `_REGRESSION_LANE_LOG` 新列（R213，305）；證據檔〈三-2〉。
- 重現：`git diff -- tools/tests/test_adr_xplat001_c1c2_lock.py`；Dev 報告與重釘列文字皆載軌上限 309、餘 4。
- 判準：〈三-2〉寫「R213 在新一輪是全新額度」，但沒寫後果——此列把 R213 標籤下回歸鎖軌 309 用掉 305，若以 R213 為輪號開證據檔，該輪回歸鎖軌只剩 4 行；兩鐘（重釘標籤 R213、檔名鐘 R212）已誠實分開，但額度被預支這件事沒有寫。另，重釘列註解內含「成長拆給…輪」類前瞻拆輪句型，與範本〈🏁〉「不寫延後句型」的紀律不合。
- 級：P3（文字揭露；鎖本身綠）。
- 建議處置：〈三-2〉補一句後果；重釘列註解改寫為「以 R213 標籤記帳（兩鐘關係見證據檔〈三-2〉）」並去掉前瞻拆輪字樣。

## 〈四〉P4 理論洞（構造性命中、無暴露證據；只登記，各附一句可觀測再開症狀）

### P4-1 SessionStart 簡報額度行不帶清倉授權

- 座標：`tools/lib/session_brief.py::quota_line`（行 210～245）呼叫 `decide(read_quota, at, policy, active_model=…)`，無 `burndown`。
- 重現（隔離）：落款有效（`quota_burndown.active` 為真）時 `quota_line(quota_gate, now, "fable")` 末段逐字 `⇒ cap=2 recommended=1 band=converge binding=seven_day reason=ok,burn-ahead,gate_excluded=spend,missing　active_model=fable`，不含「清倉」；同形狀的 hook `decide(burndown=…)` 為 cap=4 rec=2（真機 `autosdd_quota_stability_fable.json` cap=4）。
- 判準：簡報額度行須與 `--pace`／守衛同尺（該函式 docstring 逐字引 DEF-200-432 的先例：簡報與 `--pace` 不同尺曾被當缺陷修）。暴露度：構造性——落款（19:34）之後修改過的 session 逐字稿只有本 session（啟動早於落款），沒有任何新視窗的 SessionStart 實錄；`session_brief.py` 屬守衛面，依〈守衛面准入〉無暴露證據不得新增碼。
- 級：P4。
- 再開症狀：清倉效期內啟動的新視窗，其 SessionStart additionalContext 的額度行不含「清倉模式」而同刻 `--pace` 含（逐字稿命中 ≥1）；屆時依 severity.md 屬 P3 訊息誤導（決策仍在 hook，簡報只偏保守）。處置只需在 `quota_line` 傳入 `quota_burndown.active(...)` 的結果（一處）。

### P4-2 `--revoke`／過期不重寫配速契約檔

- 座標：`quota_burndown.revoke()` 只刪落款檔；引擎讀的 `autosdd_pace.json` 的 cap 在下一次 `--pace` 之前仍是放寬值，上界＝引擎端 `PACE_TTL_SECONDS=900`（`AutoClaude/autoclaude/infra/adapters/file_quota_meter.py`，以契約內 `measured_at` 計）；hook 路徑每次工具呼叫重算，不受影響。
- 重現：隔離環境（穩定狀態檔空白）`--issue` → `pace_report`（契約 cap=4）→ `--revoke`，契約檔 cap 仍為 4；再跑一次 `pace_report` 立即收緊為 cap=1 band=prepare。
- 判準：Dev 報告「收緊（過期／撤銷）一步到位」對 hook 與 `decide` 成立，對契約檔有至多 900 s 的滯後；方向為「該收緊而晚收緊」，且引擎端有效併發＝`min(靜態上限, cap)`。
- 級：P4。
- 再開症狀：`--revoke` 之後超過 900 s，引擎窗仍以放寬 cap 併發（契約檔 cap 高於同刻 `--pace` 值）。

### P4-3 無人值守窗內模型可自行 `--issue`

- 座標：`tools/lib/quota_burndown.py::issue`／`main`（無 `AUTOSDD_UNATTENDED` 或呼叫者身分判斷）。
- 重現：純讀碼；落款檔是普通 JSON，CLI 不查呼叫者。
- 判準：QB3 已裁決並於附錄 §3.4 明文「載體不具防偽性質」；本項只指出無人值守場景下同樣成立。
- 級：P4（已被裁決接受；本機無實錄）。
- 再開症狀：無人值守逐字稿出現 `quota_burndown.py --issue`，而同稿前文沒有任何人類指令。

### P4-4 `trace_dir()` 退回暫存時 `--issue` 不出聲

- 座標：`quota_burndown.directive_path()`／`issue`；`tools/lib/endurance_env.py::_durable_dir_status` 於家目錄建不出或不可寫時回 `tempfile.gettempdir()`。
- 重現：純讀碼；`issue()` 不查 degraded 旗標，只在成功訊息列出檔案路徑。
- 判準：附錄 §3.2「持久目錄…唯讀時退回暫存並出聲」；macOS 各 launchd 服務的 `$TMPDIR` 不同，落在暫存的落款對 launchd 側 tick 不可見、重開機即消失（失效方向＝不放寬，保守）。
- 級：P4（需唯讀家目錄）。
- 再開症狀：`--issue` 回報的檔案路徑在 `/var/folders/…` 或 `$TMPDIR` 而非 `~/.autosdd/traces`。

### P4-5 提前翻窗時舊落款續生效到舊 until

- 座標：`quota_burndown.verdict` 的「now < until_resets_at」一步；附錄 §3.1／§7.3 稱「新視窗的 resets_at 是另一個字串、舊落款結構上不匹配」。
- 重現：純讀碼＋真資料——實作只比時間；真快取同軸 `resets_at` 於同一視窗內有亞秒漂移（`…17:59:59.540762` → `…18:00:00.301550`），精確字串比對不可行，需要容差。
- 判準：伺服器若提前翻窗（新視窗 `resets_at` 晚於落款 `until`），授權在新視窗內續生效至舊 `until`（放寬方向）。
- 級：P4（無實錄）。
- 再開症狀：被點名軸本次讀數的 `resets_at` 與落款 `until_resets_at` 差 >1 分鐘而 `now < until`（`--status` 全 ✓）。

### P4-6 `ALLOW_PERMISSION_BYPASS` 只認行程 env；VM 不偵測

- 座標：`AutoClaude/autoclaude/execution/boot_self_check.py::permission_bypass_allowed_from_env`（docstring 刻意不讀 `.env`）；`detect_isolation_env` 只認 Linux 容器訊號（`/.dockerenv`、`/proc/1/cgroup`、`container=`／`KUBERNETES_SERVICE_HOST`）。
- 重現：純讀碼；PRD §6 區塊 13 把該鍵列在設定檔區塊，PRD §6.1 不變式 8 條文寫「容器／VM」。
- 判準：設計選擇（安全閘要由啟動方式明確注入；macOS 一律視為主機）與 VM 缺口都已寫在函式 docstring 與註解，PRD 側未同步註記。
- 級：P4。
- 再開症狀：使用者把該鍵寫進 `.env` 後仍被拒絕啟動，訊息「目前＝未設」。

## 〈五〉我跑過的指令與 rc（逐字摘要；暫存腳本在 scratchpad 的 `sd/lib/`，不入庫）

唯讀測試（`export AUTOSDD_SENTINEL_OFF=1`；根層測試在 `tools/tests` 下以 `python -B -m unittest <模組>`）：

```text
1  python -B -m unittest test_quota_burndown test_quota_policy test_quota_env_layers test_quota_reconcile_gap
   → 400 項測試、OK、RC=0（7.980 s）                     ［Dev 報告 400＝386＋14，吻合］
2  python -B -m unittest test_context_budget_guard
   → 810 項測試、OK、11 項略過、RC=0（55.466 s）
3  python -B -m unittest test_adr_xplat001_c1c2_lock
   → 187 項測試、OK、RC=0（14.182 s）；尾行 [Scan-H triplet] UEP=5 AC=47 GLC_FILES=93 GLC_LINES=116734
4  cd AutoClaude && python -B -m pytest tests/test_r100_boot_self_check.py \
     tests/execution/test_prd12_permission_bypass_invariant8.py -q -p no:cacheprovider -n 0
   → 144 項通過（1.26 s）、RC=0
```

工具與檢查：

```text
5  python tools/probe/wakechain_e2e.py --selftest
   → RC=0；strict-pass FAIL=[] WARN=0／post-hoc FAIL=[] WARN=2／bypass FAIL=['S2','S3','S5a','S5b']
6  python tools/probe/wakechain_e2e.py --judge 14fb33dc-4ffc-40c9-b62b-9dcf801d02f4 --since 2026-10-12T13:16:00+08:00
   → RC=0；S14-core: PASS（8/8）｜tail: PASS（7/7）｜WARN 2；尾行 WAKECHAIN-E2E rc=0
7  python tools/lib/quota_policy.py --env-doctor
   → RC=0；結論：0 個問題 ⇒ rc=0（[empty-local] 提示）
8  python AutoClaude/tools/check_loc_budget.py --json
   → RC=0；total_violation false、四類違規皆 []；tools/lib/quota_gate.py loc 497／budget 500／headroom 3
9  python tools/check_defect_log_crossref.py
   → RC=1：CrossPlatform_R212_Row5_Findings_Architect.md 符合治理文件命名慣例卻未登記進 _GOVERNANCE_DOCS；
     另有 12 道後續檢查未執行（工作樹現況，非本鏡造成；本檔落地後會再多一筆同類）
10 /usr/bin/python3 -B（3.9.6）：匯入 quota_policy／quota_pace／quota_burndown／quota_gate 皆 OK；
   隔離環境 --issue、--status、pace_report、純函式情境腳本皆 RC=0
```

隔離重現與量測（`HOME`／`TMPDIR`／`AUTOSDD_TRACE_DIR`／`AUTOSDD_QUOTA_CACHE_DIR` 皆指向 scratchpad 子目錄；快取以真快取為模板、數字照〈二-1〉合成；`quota_burn.jsonl` 複本取自真帳以得 r=5.0、n=67）：

```text
11 python tools/lib/quota_burndown.py --status（下令前）            → RC=1，「✗ 落款檔存在且六欄齊全」
12 … --issue weekly_all --directive "測試"                          → RC=0，已落款 54f961aba1
13 … --status（下令後）                                              → RC=0，六步全 ✓＋清倉段
14 compare（decide 有／無授權；不經遲滯）                            → 無授權 cap=1 rec=1 band=prepare binding=five_hour
                                                                       有授權 cap=4 rec=2 band=converge binding=seven_day
15 pace_report(model=fable)（同 --pace 路徑）                         → RC=0；清倉段於第 1、2 行各一次；事件列 relaxed；
                                                                       燃燒落款含 "bd"；契約檔 cap=4（隔離檔）
16 kill-switch／過期 until×5／方案指紋變／軸消失／點名 five_hour／weekly_scoped／spend／nope／空指令 → 見〈一-C〉，皆如預期
17 --revoke 兩次                                                      → RC=0／RC=0（第二次「沒有有效落款可撤銷」）
18 PYTHONIOENCODING=cp1252 的 --help／--status                        → RC=0／RC=0（init_utf8_streams 生效）
```

差分、量測、突變（皆純函式或隔離複本）：

```text
19 差分：同一份 6000 組隨機狀態（seed 20261012）對 HEAD（git archive 複本）與工作樹各跑 decide/describe/pace_line/axes_of
   → 兩份 JSONL cmp 退出 0（逐位元相同）；語料含 halt 2091／prepare 1599／converge 915／notice 694／free 701，
     攤提 711、must-finish 1786、model-scoped-excluded 3695
20 規格不變式量測（有授權 vs 無授權）：23094 組有效案例（relaxed 7445／inert 15649）→ 違反 0
21 獨立 oracle 對帳：23425 組（Q-cross 非空 1736；被改動軸 10530）→ 規格未授權的改動 0
22 畸形輸入：20000 組（17105 組帶非空軸與授權）→ base 路徑例外 0、授權路徑例外 0
23 單點突變（隔離複本）：35 個，30 殺、5 存：M14、M34、M35、M36、M38（分析見 P3-4；M35／M36 等價或冗餘）
24 真帳統計（唯讀）：205 列 weekly_all==seven_day 205/205；203 列 session==five_hour 203/203；weekly_all==weekly_scoped 0/204
```

未動證明（交件前）：`~/.autosdd/traces/autosdd_burndown_directive.json` mtime 19:34、`id=45c49b8e35`、`axis_kind=weekly_all` 未變；`autosdd_burndown_events.jsonl` 仍 1 行；`git status --short` 與本鏡開工時逐列相同（本檔為唯一新增）。

## 〈六〉文件訂正清單（對主控骨架與前六次宣稱的措辭訂正）

1. PRD §16.2 A4 列「親驗＝同窗 `--issue weekly_all` 後 `--pace` cap 由 1 升至 `cap_converge`」→ 改為「`--pace` 標題 cap 由 1 升至 2（遲滯 +1／≥300 s；binding 軸自身 cap 為 4＝`cap_converge`）；派工 hook 的穩定 cap 於 19:39:29 已達 4（`autosdd_quota_stability_fable.json` 現查）」。證據〈三-3〉逐字是 cap=2，現行措辭讀起來像標題已到 4。
2. PRD v2.1.19 修訂列與 A4 列「`decide()`／`band_inputs()` 各加一個預設不生效的參數」→ 實為六個簽章：`decide(burndown)`、`axes_of(relax)`、`resolve(floor, hold)`、`band_inputs(hold)`、`row_of(bd)`、`record_burn(bd)`。
3. 證據〈二-2〉Q-cross 定義「`Amort.total_kind` == 被點名軸」→ 與〈三-1〉(c) 及實作一致，改成「`Amort.total_kind` 的軸是 Q-same（相等時逐字相同；避免被點名軸與同窗鄰軸平手時因 axes 順序靜默不觸發）」。
4. 證據〈三-3〉判讀(1)「下令前後同一組軸（週軸 78%、短窗 29%）由 `cap=1 …` 變為…」→「下令前」並非同讀數的實測（〈二-1〉是 18:16、短窗 8%／週 75%；29%／78% 讀數下令前沒有 `--pace` 實錄）。本鏡以真落款時刻的讀數（29%／78%、r=5.0）重算：無授權 `cap=1 rec=1 band=prepare binding=five_hour`，與骨架宣稱一致；請改寫為「下令前＝〈二-1〉實測與同讀數重算；下令後＝實測」。
5. 證據〈三-3〉(2)（清倉段重複）處置後更新；並載明兩點：事件列 `autosdd_burndown_events.jsonl` 的 `cap`／`rec` 是遲滯前的 `decide` 原值（真事件列 `cap:4`，同刻標題 `cap=2`），且只計 `--pace` 決策、不含 hook 決策（附錄 §6.3 的 relaxed／inert 比值因此只量 `--pace` 面，模組檔頭已自陳，證據檔未寫）。
6. 證據〈三-2〉補 R213 標籤的後果：回歸鎖軌 309 已用 305（見 P3-6）。
7. 增補檔 `docs/04_planning/PRD_Amendment_R108_BurnDown_Addendum.md` 檔首 Adopted 狀態與 P1-8 盤點注（「零落地」）已過時：加一則 2026-10-12 落地注（只加注、不改原文），並載明 §7.2 `BURNDOWN_CAP_CEILING` 未實作、§4.4 `none` 四列不放寬（§4.1 時鐘合取項）、§9-5 零容差實測結果（真帳 205 列：非分軌鄰軸 205/205 全等、分軌 0/204）、BD-8 已不 gated。
8. 前六次宣稱與 commit 訊息「判決 22 項全 PASS」→ 分寫：judge4.py 22 項（未入庫）；入庫 `wakechain_e2e.py --judge` 重放 17 列（15 PASS＋2 WARN，WARN 為事後暫存物已清）；`--run` 只被 mock 驗過、未在真機整段跑過（工具檔頭自陳）。
9. PRD §6 區塊 13 `ALLOW_PERMISSION_BYPASS` 加註：實作只認行程環境（刻意不讀 `.env`），VM 不偵測（見 P4-6）。
10. 證據〈三-3〉判讀(1)「與附錄 §4.4 值域表及〈二-2〉裁決逐格相符」→ 週軸兩列（converge×far：cap 2→4 rec 1→2）與表相符；短窗兩列（band prepare→free）不在該表內（表未含 BD-2′），其依據是〈二-2〉裁決，請分開寫。
11. 流程項：本檔與同列其他鏡的 `CrossPlatform_R212_Row5_Findings_*.md`（交件時工作樹已見 Architect、SA）皆符合 `docs/06_quality/CrossPlatform_*.md` 發現面；須在 `tools/lib/governance_docs.py` 的 `_GOVERNANCE_DOCS` 登記（或併入證據檔後刪除），否則 `check_defect_log_crossref.py` 維持 rc=1 且其後 12 道檢查不執行，QA 鏡的全套會帶紅。
