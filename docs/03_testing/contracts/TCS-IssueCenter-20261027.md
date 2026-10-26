# Test Contract Specification — 議題中心（Issue Center）：議題聚合與中文對照、`issues` 動詞與匯出、Bridge 兩個 GET、console-api 讀取與優先順序、前端 `/issues`
# 測試契約規格文件（新功能；FRD-lite 併入檔頭；一份 TCS 涵蓋兩把 SDD 鍵）

> **上位 PRD digest**：`sha256:a162a104dc8217730fa42ed00cb7c071105943d4808bc7e5aa05efd5035408a7`（`docs/01_requirements/Issue_Center_PRD.md` v1.0；LF-only，95,802 bytes；2026-10-27 於 HEAD `1e82dd18` 兩鍵 Stage-1 凍結）。本檔不改 PRD；PRD 的問題一律寫 §7.3。
> **範圍**：階段一（唯讀議題中心）加階段二（優先順序與「待您決定」按鈕）合訂一份（PRD §11）。PRD 的 AC 共 90 條（任務書寫 85，PRD 三輪審查後為 90，本檔以 PRD 為準）；每條 AC 至少一個正向與一個反向 AT。

## 文件資訊

| 項目 | 內容 |
|---|---|
| 檔案 | `docs/03_testing/contracts/TCS-IssueCenter-20261027.md`（新；SDD 規格階段 Stage-2 契約，置於 03_testing/contracts） |
| 版本與狀態 | v1.0 草案，待 Stage-2 凍結（兩鍵）；2026-10-27 起草；作者角色＝SA／Architect（Sonnet 5.5，依主控任務書）；〈勘誤〉節凍結前留空 |
| 上位規格 | `docs/01_requirements/Issue_Center_PRD.md` v1.0（digest 見檔頭）；先例 TCS：`TCS-SelfImproving-P3-20261024.md`（節體例）、`API_Contract_SelfImproving_P1b.md`（契約體例） |
| SDD 鍵（BRIDGE §8，一功能一鍵） | `monorepo-issue-center`（根層半）、`agentconsole-issue-center`（Console 半）；兩把鍵的 `spec-frozen` 都凍結同一份 PRD 與本檔；Console 側不另起 TCS |
| 規模 | R 條文 75 條；AT 223 個（正向 121、反向 102）；AC 90／90 全覆蓋（§1、§6）；契約節＋5.7 兩半各一張檔案集合表；閘門指令兩半各一組（SCG-4 通過標準） |
| 載具與判定指令 | 根層 unittest（`python -m unittest discover -s tools/tests -p <檔> -k <AT 底線形>_`）；Bridge pytest（`-k`）；backend JUnit 5（`gradlew test --tests`）；frontend vitest（`-t`）；Playwright（`-g`）；審查閘（G 編號指令）。細節見 §2 |
| 讀法 | 開發棒各取一半：根層半＝R-IC-01～R-IC-44＋§C1、§C2＋根層 AT＋5.7 根層表；Console 半＝R-IC-45～R-IC-75＋§C3～§C6＋Bridge、backend、frontend AT＋5.7 Console 表。兩半共同的只有匯出形狀（§C1、§C2），它由根層半先交付 |

### 凍結後修訂路由（QA 三審 N-5 殘餘：凍結後任何修訂走哪把鍵）

1. 只動根層半（R-IC-01～R-IC-44、§C1、§C2、根層 AT、5.7 根層表、D-R 表）的勘誤：由 `monorepo-issue-center` 先 `spec-refreeze`，勘誤落本檔〈勘誤〉節並附新 digest。
2. 只動 Console 半（R-IC-45～R-IC-75、§C3～§C6、Bridge／backend／frontend AT、5.7 Console 表、D-C 表）的勘誤：由 `agentconsole-issue-center` `spec-refreeze`。
3. 跨兩半的勘誤（例：匯出形狀改一個鍵）：先 `monorepo-issue-center` refreeze，再由 `agentconsole-issue-center` 引同一勘誤條號 refreeze；兩鍵最終引用的本檔 digest 必須相同，不同＝後 refreeze 的那把鍵視為未凍結、開發棒不得續做。
4. 上位 PRD 的修訂（PRD 已凍結、不可原地改）：依 PRD §11 與 BRIDGE §8，由 `monorepo-issue-center` 先走 PRD 勘誤並同步更新本檔檔頭 digest，`agentconsole-issue-center` 隨後 refreeze。
5. 兩把鍵都列同一份 TCS 與同一份 PRD；任何一鍵 refreeze 後，另一鍵在下一次 `spec-frozen` 前須先核對 digest 一致。凍結審批依根 CLAUDE.md〈凍結常態規則〉（審查 PASS 且主控親驗無 P1、P2 才代執行）。

## 增量變更專用：FRD-lite 與〈增量追溯表〉

### FRD-lite

**Before／After（現值皆於 HEAD `1e82dd18` 實查；每處上修都是同 commit 的可見釘值上修）**

| 面 | Before | After |
|---|---|---|
| 根層 CLI 動詞 | 23 個（`selfimproving.py:6`、`_HELP` 長度 23、`console_obs:921` 動詞集合 23） | 24 個（加 `issues`） |
| `export.KINDS`／`si_cli.SI_KINDS` | 5 個（observations、events、proposals、runs、status） | 6 個（末位加 `issues`） |
| `CAPABILITY`（`test_selfimproving_capability.py:30`） | 48 鍵（36 ro、8 rw、2 net、2 exec）；無 `meaplan` 變體 47 鍵 | 50 鍵（38 ro）；變體 49 鍵（37 ro） |
| Bridge 路由 | 6 個 GET（`SIX_PATHS`） | 8 個 GET（加 `/si/issues`、`/si/issues/{id}`） |
| `AgentBridge.siExport` | 4 參數 `(kind, since, limit, id)` | 6 參數（加 `status`、`source`）；`si` 起頭方法仍 5 個 |
| backend 路徑／操作（`OpenApiIT`） | 71 路徑、81 操作 | 74 路徑、85 操作（+3、+4） |
| Flyway | V1～V13 | V1～V14（`V14__issue_priority.sql`） |
| 前端 `endpoints.ts` 匯出函式 | 79 個 | 83 個（`getIssues`、`getIssue`、`putIssuePriority`、`deleteIssuePriority`） |
| 導覽登記表 | 7 項 | 8 項（`issues`，order 55，陣列末尾） |
| 黃金檔鏈 | 5 kind＋單筆提案（A 態 6 鍵、B 態 5 鍵） | 加 `issues` 鍵（A、B 兩態；Bridge、backend、frontend 三份副本） |
| compat-ci `paths` | 無本功能檔 | 加 PRD、本檔、兩姊妹軌帳本（兩支 workflow） |

**使用者故事（US，一 FR 一則；AC 對應見 §1、§6）**

| US | 身為掌舵者，我要… | 以便… | FR |
|---|---|---|---|
| US-IC-01 | 看到的狀態、結果、來源、嚴重度全是中文，對不上時明說「未歸類」 | 不被英文機器值或靜默漏列誤導 | FR-IC-01 |
| US-IC-02 | 每個議題標明是誰提的（使用者、系統缺陷、研究、改善） | 一眼分辨來歷 | FR-IC-02 |
| US-IC-03 | 只有「已成立」的項目才成為待辦，候選不吵我 | 清單只有真待辦 | FR-IC-03 |
| US-IC-04 | 每列都有下一步一句話、關聯與可展開的原列與時間線 | 不必翻帳本 | FR-IC-04 |
| US-IC-05 | 最重要、最久沒動的排前面，可分頁、可篩、數字是整本帳 | 抓得到重點 | FR-IC-05 |
| US-IC-06 | 議題中心不動帳本、兩個出口一致、不存第二份詞彙 | 帳本仍是唯一真相 | FR-IC-06 |
| US-IC-07 | 讀取走 Bridge 與 console-api，失敗時明說原因而非空表 | 「量不到」不被誤讀成「沒有」 | FR-IC-07 |
| US-IC-08 | 畫面四分頁、八欄、詳情與「狀態說明」都是中文、純文字 | 看得懂也安全 | FR-IC-08 |
| US-IC-09 | 對待辦排優先順序（只有 ADMIN 能改） | 我的順序排在前面 | FR-IC-09 |
| US-IC-10 | 在待您決定列直接按鈕，走既有簽章對話框 | 不離開頁面就能決定 | FR-IC-10 |
| US-IC-11 | 左列有「議題中心」，且「自我進化」不變 | 找得到、不迷路 | FR-IC-11 |
| US-IC-12 | 快、跨平台、不快取、既有功能不壞、鍵盤可用 | 日常可靠 | FR-IC-12 |

**User Story INVEST 自檢（SCG-0；AC 與 AT 數由 §1、§3 機械計算）**

| US | I 獨立 | N 可協商 | V 有價值 | E 可估 | S 夠小 | T 可測（AC／AT） |
|---|---|---|---|---|---|---|
| US-IC-01 | 是（最先交付） | 是 | 是 | 是 | 否（FR 級，11 條 AC） | 是（11／34） |
| US-IC-02 | 依 US-IC-01 | 是 | 是 | 是 | 是（5 條 AC） | 是（5／11） |
| US-IC-03 | 依 US-IC-01 | 是 | 是 | 是 | 否（FR 級，7 條 AC） | 是（7／16） |
| US-IC-04 | 依 US-IC-01～03 | 是 | 是 | 是 | 否（FR 級，11 條 AC） | 是（11／27） |
| US-IC-05 | 依 US-IC-01～04 | 是 | 是 | 是 | 否（FR 級，7 條 AC） | 是（7／16） |
| US-IC-06 | 依 US-IC-01～05 | 是 | 是 | 是 | 是（5 條 AC） | 是（5／17） |
| US-IC-07 | 依 US-IC-01～05（匯出形狀） | 是 | 是 | 是 | 否（FR 級，9 條 AC） | 是（9／22） |
| US-IC-08 | 依 US-IC-07 | 是 | 是 | 是 | 否（FR 級，11 條 AC） | 是（11／24） |
| US-IC-09 | 依 US-IC-07 | 是 | 是 | 是 | 否（FR 級，11 條 AC） | 是（11／26） |
| US-IC-10 | 依 US-IC-08、既有 SI 對話框 | 是 | 是 | 是 | 是（5 條 AC） | 是（5／11） |
| US-IC-11 | 是 | 是 | 是 | 是 | 是（3 條 AC） | 是（3／6） |
| US-IC-12 | 跨切面，依 US-IC-01～10 | 是 | 是 | 是 | 是（5 條 AC） | 是（5／13） |

註：N 的可協商處＝中文用語與畫面細節（鎖的是結構與詞彙集合）；S 為「否」者是 FR 級故事，以 AC 為最小可測單位、以持有面（根層半、Console 半）為最小派工單位，不再拆成更小的 US；I 的依賴即派工順序（根層先、Console 後）。以上為本檔作者的自檢，凍結審查可推翻。

**持有面、鎖的住所與提交順序（鐵律七：一道鎖的常數、史料、消費端若不在同一持有面，不得派並行包）**

| 鎖或件 | 常數（真相） | 史料與消費端 | 持有面與順序 |
|---|---|---|---|
| `CAPABILITY` 計數、動詞數、`_HELP` | `test_selfimproving_capability.py`、`selfimproving.py` | `p3_meta:293-298`、`console_obs:921` | 根層半（同 commit 收齊） |
| 匯出形狀（§C1、§C2） | `issues.py` 的輸出 | Bridge 透傳、backend camelCase、前端型別、黃金檔 | 根層半先交付，Console 半後 |
| 黃金檔三份副本 | `si_golden_regen.py` 的輸出 | Bridge `fixtures/si_golden`、backend `resources/si`、frontend `tests/fixtures/si` | Bridge＋backend 包負責重產三份（含前端那份複本）；前端包只讀；先 Bridge 後 backend 後前端 |
| `OpenApiIT` 計數、`schema.d.ts` | backend 路徑與操作 | 前端 `schema.d.ts`（`npm run gen:api` 對在線 backend 重產） | backend 先，前端重產後入庫 |
| issue 類 reason 雙向鎖 | `API_Contract_IssueCenter.md` 的 reason 表（由 backend 包依 §C5 建檔） | `ErrorReasons`、前端 `ISSUE_REASONS` | 契約檔與 `ErrorReasons` 同包先做；前端 `ISSUE_REASONS` 後做並與表逐字相同 |
| 導覽登記表、`endpoints.ts` 計數 | `registry.ts`、`endpoints.ts` | `registry.test.ts`、`ToolsRegion.test.tsx`、`endpoints.test.ts`、`si.endpoints.test.ts` | 前端包（同 commit 收齊） |
| 落點規範、compat-ci `paths`、護欄層棘輪重釘 | `Root_Layout_and_Module_Placement.md` §3、兩支 workflow、`test_adr_xplat001_c1c2_lock.py` | 落點鎖、`AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py` | 根層半；重釘與淨減法只由收尾單人窗口做（鐵律七） |

**D 表：根層半（`monorepo-issue-center`）的 TCS 定案；開發棒照做，不得另取他法**

| D | 定案 |
|---|---|
| D-R1 | 住所與依賴：`issuemap.py`＝常數與純函式（公共面簽章見本表後〈issuemap 公共面〉；含參數化的 `closure_problems(upstream=None)`，以便合成上游自證紅綠）；`issues.py`＝聚合，以 `from . import fold as si_fold`、`events as si_events`、`card as si_card`、`status as si_status` 的**模組屬性**呼叫（使 §5.2 注入縫成立）；兩者皆 `ro`；不改 `fold.py`、`rows.py`、`events.py` |
| D-R2 | 公共入口：`issues.build(repo, git, params, *, since=None, limit=None, ident=None, statuses=None, sources=None) -> dict`（export 形狀）；`issues.sort_for_display(items, rule)`（`rule` 為 `'pending'` 或 `'done'`）；`issues.render_text(obj, statuses=None) -> str`；`export.build` 對 `kind=='issues'` 轉呼叫 `issues.build`；CLI `issues` 與 `export --kind issues` 取同一個物件 |
| D-R3 | 回滾計法（QA 三審 R3-05 定案，R-IC-19）：`decided(p)`＝事件中 `kind=='dec'`、`dkind=='rollback'`、`prop==p.id`、`seq>p.promote_seq` 的筆數（`promote_seq` 為 None 則 0）；`pending(p)`＝`Prop.pending_rollbacks`；`consumed(p)`＝`decided−pending`；不改 `fold.py` |
| D-R4 | 游標基數 S＝10,000,000（< 2^31，相容 backend `Integer since`）：觀察＝OBS 號；缺陷＝S＋主檔資料列行號；提案＝2S＋PROP 號；`AutoSDD_External_Blocked_Log.md` 孤列＝3S＋行號；`AutoSDD_Structural_Debt_Log.md` 孤列＝4S＋行號；號碼或行號 ≥ S 者不成議題、計 `ROW-ARITY`（detail「編號或行號過大，游標無法編碼」；該碼的 legend 釋義在 PRD §4.5 句後加一句，見 §C1.3） |
| D-R5 | `summary.by_tab` 的 null 對映（QA 三審 R3-07 定案）：觀察帳本或事件帳本不可用→三格皆 null；缺陷主檔或任一姊妹軌不可用→待處理與已完成為 null、待您決定照算 |
| D-R6 | CLI 文字表的頁內顯示序：`--status` 非空且各值皆屬 {待解、進行中、觀察中、待您決定、待處理}→第一條（無順位）；否則第二條（無置頂）；只排本頁；`--json` 與 `export` 的 `items` 永遠是游標序 |
| D-R7 | `defs.DefRow` 增 `lineno: int = 0`、`arity_ok: bool = True`（有預設值，既有呼叫端與走訪不變）；`lineno`＝該列在 `text.splitlines()` 的 1 起算序號（沿 `load_rows` 既有走訪；含 U+0085、U+2028 的檔會與編輯器行號不同，記 §7.3 第 4 點） |
| D-R8 | 姊妹軌在 `issues.py` 內解析（以 `ledger.split_cells` 切欄；表頭須含 `DEF-ID`、`解鎖條件（可機械查）`、`最近複查日`）；不改 `defs.py` 去讀姊妹軌（`load_rows` 認的是主檔欄名） |
| D-R9 | `closed` 提案的生效量測結果＝`si_fold.effective_windows(f)` 中該 PROP 第一個窗的 `effective`。`fold` 讓 pending 窗的提案停在 `measuring`（`mea.close` 結果為 pending 時狀態仍是 measuring，`mea.amend` 自 pending 落定才轉 closed），所以 closed 不會自然帶 pending；`effective` 不在 {clean、recurred、rolled-back}（無窗，或注入縫 S2 構造）＝量不到→已完成、「未歸類：closed」、計 `UNMAPPED`（PRD §4.2「量不到」列；判序見 R-IC-19，記 §7.3 第 3 點） |
| D-R10 | `ne.field` 命名：整本帳 `ledger.observation`、`ledger.observation.<歸檔檔名>`、`ledger.defect`、`ledger.sibling.<檔名>`、`ledger.events`、`head_sha`；項目級 `issues.<ID>.<欄>`，欄∈{severity、updated_at、title、next_step}；`source` 為 null 一律由整本帳級 `ne` 說明、不另生項目級 |
| D-R11 | 測試檔以 2 支為上限（PRD §9）：夾具建構函式放 `test_selfimproving_issues.py` 模組層，`test_selfimproving_issuemap.py` 以 `import test_selfimproving_issues as ti` 取用；不新增輔助檔；既有 `_selfimproving_*_fixtures.py` 只讀取用、不修改 |
| D-R12 | 排序範例表只在 §5.5；根層與前端各嵌一份相同的表與預期序（不設共用檔）；兩邊預期序以 §5.5 為準 |
| D-R13 | 「帳本不可用」的判法：`issues.py` 先自行讀檔——缺檔、`OSError`、`UnicodeDecodeError` 即不可用；缺陷主檔與姊妹軌另須有合格表頭（缺陷主檔＝`defs.columns(path)` 非 None；姊妹軌＝含 `DEF-ID` 表頭），否則也算不可用（不可據 `defs.load_rows` 的空串列判斷，它對不可讀與無表頭一律回空） |
| D-R14 | 事件來源：折疊與時間線的輸入一律 `si_events.load_sound_events(path)`（注入縫 S3 的目標）；`EVENT-PARSE`、`EVENT-UNSOUND` 另讀原始行（`si_events.read_lines(path.read_bytes())`：`obj is None`→PARSE；`validate(obj)` 非空→UNSOUND，subject 取 `Line.no`），不經 S3；兩者合起來等於 `export` 既有 `_events` 的逐行判準加不合格事件 |

**issuemap 公共面（D-R1 的簽章清單；`test_selfimproving_issuemap.py` 依此呼叫，改名須勘誤）**

| 名稱 | 簽章 | 回傳與用途 |
|---|---|---|
| `STATUSES`、`RESULTS`、`SOURCES`、`SEVERITIES` | `tuple[str, ...]` | 七狀態（順序固定）、八結果、四來源（順位序）、四嚴重度名（緊急、高、中、低） |
| `DEF_SEVERITIES` | `tuple[str, ...]` | `('P0','P1','P2','P3','P4')`（缺陷嚴重度子集鎖的常數） |
| `status_of(kind, key, **cond)` | `kind`∈`'obs'`、`'def'`、`'prop'`；`key`＝處置首詞（`rows.disp_token` 的值）、缺陷狀態類（`defs.classify_status`）或提案態；`cond` 關鍵字：`decision`、`established`、`sibling`、`window`、`decided`、`pending`、`consumed` | `(status, result)` 或 `None`（表外）；closed、promoted、measuring 的判序依 R-IC-19 |
| `severity_of(group, raw)` | `group`∈`'obs'`、`'def'`；`raw`＝嚴重度欄原文 | `(名稱, rank)` 或 `None`（表外）；缺陷組依 R-IC-05 取首碼 |
| `source_of(marks, category, *, is_def=False)` | `marks`＝`rows.row_marks` 的結果；`category`＝分類欄 | 四來源之一（R-IC-16 的觀察列順位） |
| `labels()` | 無 | dict：legend 的全部中文（`statuses`、`results`、`sources`、`severities`、`problem_codes`、`ne_reasons`、`unmapped_label`、`updated_at_note`）；legend 的唯一來源 |
| `event_label(kind)`、`dkind_label(dkind)`、`route_label(route)` | `str` | 事件動作、決定動詞、通道（`handoff:` 後綴）的中文；表外回 `None` |
| `unmapped(raw, limit=80)` | `str` | 「未歸類：<原值>」（超過 `limit` 個 code point 取前 `limit` 個加「…」，「…」不計入；R-IC-06） |
| `closure_problems(upstream=None)` | `upstream`＝dict 或 `None`（None＝真上游） | `list[str]`（空＝封閉；R-IC-03） |

**D 表：Console 半（`agentconsole-issue-center`）的 TCS 定案**

| D | 定案 |
|---|---|
| D-C1 | Bridge 輸入驗證的 `rule` 名：`unknown_parameter`、`invalid_format`（沿既有）；新增 `too_long`、`leading_dash`、`control_char`（`status`／`source` 各值）；欄名 `field` 為參數名；一次列全部違規 |
| D-C2 | console-api 轉發：`status`、`source` 為 null 則省略；空字串照轉（CLI rc 3→503，不特判）；值先嚴格 percent-encode 再 `URI.create`；單筆與 `/si/status` 不帶任何查詢參數 |
| D-C3 | 優先順序合併：每個清單請求一次讀順位表（以本頁項目的 ID 集合）；讀取失敗＝整個請求失敗（5xx、無 `data`）；單筆同理 |
| D-C4 | PUT 流程：先 `siExport("issues", null, null, id, null, null)` 取單筆（空 `items`→404 `si_not_found`），再判 `rankable`（false→409 `issue_not_rankable`，`details`＝`{id, status}`），最後 UPSERT；`setBy`＝JWT 帳號、`setAt`＝伺服器時間（帶 offset） |
| D-C5 | 新 reason：`issue_not_rankable`（409）；中文訊息逐字「此議題目前的狀態不能設定優先順序」；三處同字：契約表、前端 `ISSUE_REASONS`、後端 409 的 `message`；後端 `ErrorReasons.ISSUE_NOT_RANKABLE`＝識別字；契約 reason 表只列 issue 類（`invalid_request` 沿 P2b，不入表） |
| D-C6 | `invalid_request`（422）沿 P2b：後端以區域常數持有（比照 `SiWriteGates`）、不進 `ErrorReasons`；`details.violations[{field,message}]` 與 `errors[]` 互為鏡像 |
| D-C7 | Bridge 夾具倉（`fixtures/si_repo`）不新增帳本檔：缺陷主檔與姊妹軌缺檔，故 `issues` 黃金檔的 `ne` 含 `DEFECT-LEDGER-UNAVAILABLE` 與兩筆 `SIBLING-LEDGER-UNAVAILABLE`（確定性、屬真輸出）；`si_golden_regen.py` 的 `STATE_KEYS` A、B 各加 `issues`；黃金檔數 4＋4＋2 不變 |
| D-C8 | 前端測試鉤：以 `getByRole`／文字為主、`data-testid` 為輔，testid 表見 §5.4；§5.4 的 22 個英文詞表在 `lib/domain/issues.ts` 以常數持有並被測試引用（單一份） |
| D-C9 | 兩支 e2e：`issues.mock.spec.ts`（mock API，進 CI，AC-IC-12-5）；`issues-docker.stack.ts`（全棧，SCG-5 實機證據：AC-IC-09-6 的重啟持久、AC-IC-07-2 的 console-api 全鏈中文篩選；非每 commit 閘） |
| D-C10 | AC-IC-09-6 雙載具：`IssuePriorityMigrationIT`（升級、約束、validate）進 `gradlew clean build`；容器重啟持久由 `issues-docker.stack.ts` 在 SCG-5 留證據 |
| D-C11 | 契約檔 `API_Contract_IssueCenter.md` 由 backend 包依 §C 逐表抄成（TCS 為真相）；與 `ISSUE_REASONS`、`ErrorReasons` 雙向鎖；`Architecture.md`、`reasons.ts`、`API_Contract_P3-6.md` 不改 |
| D-C12 | `MiniBridge` 加 `GET /si/issues`、`GET /si/issues/{id}`（記錄沿 `MINI.requests()`，`si.seen` 同型）；黃金檔鍵 `issues` 供 `IssueApiIT` 比對 |
| D-C13 | PUT 本文承接：以 `JsonNode`（或 `Map`）承接、不綁具型別 DTO（否則 Jackson 對 `rank` 為字串或小數會落 400）；`rank`、`note` 的型別與值域一律由輸入閘一次全列（`violations`）回 422；只有本文不是 JSON 物件（或 JSON 語法錯）才 400（reason `MALFORMED_REQUEST_BODY`，沿既有 `handleUnreadable`；`[]`、`"x"` 這類合法但非物件的 JSON 與語法錯得到同一回應） |
| D-C14 | OpenAPI 錯誤文件（`ErrorResponseDocumentation.java`）：`CONFLICT_ENDPOINTS` 加 `PUT /api/v1/issues/{id}/priority`；`NEVER_NOT_FOUND` 加 `DELETE /api/v1/issues/{id}/priority`（冪等）；`NOT_FOUND_DESCRIPTION` 加 `GET /api/v1/issues/{id}`（`si_not_found`、「查無此議題」）；`EXTRA` 加四端點的 422／502／503／504 說明；以 `OpenApiIT` 紅綠為準 |

**三項「待 TCS 釘單一取法」（QA 三審 R3-05、R3-07、取捨 a）已定案**：已消耗 `app.rollback` 的計法＝D-R3；事件缺檔時的 byTab 對映＝D-R5；契約 reason 表只列 issue 類＝D-C5。

**追溯矩陣**：F-IC（議題中心）← PRD FR-IC-01～12（§8 的 90 條 AC）、§2～§7（來源、成立、對照表、資料模型、介面、畫面）、§9（模組落點與既有鎖）、§10（NFR）、§11（分階段與派工）、§12（不做）；US-IC-01～US-IC-12 → AC-IC-01-1～AC-IC-12-5（PRD §8）→ AT（本檔 §1）；R-IC-01～R-IC-75 → AC（R 條文表的 AT 欄）。

**〈增量追溯表〉**（SCG-0～3 每個清單項一列；「已凍結上位文件」均相對 `spec-frozen --root`＝monorepo 根；兩把 FSM 鍵 `monorepo-issue-center`、`agentconsole-issue-center` 凍結同一份 PRD 與本檔）

| 清單項（閘門／項目） | 追溯 ID | 已凍結上位文件（路徑） | 凍結摘要 |
|---------------------|---------|----------------------|---------|
| SCG-0／PRD 版本已鎖定（Status: Approved） | PRD v1.0 全文（§11 分階段；SCG-0 三輪審查 F-01～F-30、N-1～N-11、R3-01～R3-08 已結）；Stage-1 於兩把鍵凍結，審批依常態規則由主控執行 | docs/01_requirements/Issue_Center_PRD.md | sha256:a162a104dc8217730fa42ed00cb7c071105943d4808bc7e5aa05efd5035408a7 |
| SCG-0／FRD 覆蓋所有 PRD 功能項目（F-XXX 追溯） | F-IC（本功能）＝FR-IC-01～12（PRD §8）；本檔 FRD-lite 的 US-IC-01～12 與 §1 | docs/01_requirements/Issue_Center_PRD.md | sha256:a162a104dc8217730fa42ed00cb7c071105943d4808bc7e5aa05efd5035408a7 |
| SCG-0／NFR 已量化定義 | PRD §10（≤2 秒、單頁 ≤1 MB、不快取、UTF-8、可及性）與 AC-IC-12-1～12-5；本檔 §6.2 | docs/01_requirements/Issue_Center_PRD.md | sha256:a162a104dc8217730fa42ed00cb7c071105943d4808bc7e5aa05efd5035408a7 |
| SCG-0／User Story 已完成 INVEST 檢查 | US-IC-01～12（本檔〈User Story INVEST 自檢〉表與其註） | docs/01_requirements/Issue_Center_PRD.md | sha256:a162a104dc8217730fa42ed00cb7c071105943d4808bc7e5aa05efd5035408a7 |
| SCG-0／利害關係人已確認簽核 | PRD 檔頭立案（掌舵者 2026-10-26，sid 0a41ada1-921d-48d4-bb4b-4cc4a18190e8）、範圍裁決（互動選項「階段一和二一起做」）、主控裁決 2026-10-26（PRD §13）；凍結依常態規則由主控執行，掌舵者可隨時以 T1 推翻 | docs/01_requirements/Issue_Center_PRD.md | sha256:a162a104dc8217730fa42ed00cb7c071105943d4808bc7e5aa05efd5035408a7 |
| SCG-0／RTM 初版已建立 | 本增量自帶：本檔 §1 與 §6；Console 側 RTM 回填 `AgentConsole/docs/06_quality/RTM.md` §2.4 子表一列 | （本檔；隨 Stage-2 凍結，非上位文件） | n/a（自引） |
| SCG-1／SRD 完成並通過 Review | 不適用（功能級增量；設計載於 PRD §2～§7）；最近依據 PRD §4（對照表）、§5（資料模型） | docs/01_requirements/Issue_Center_PRD.md | sha256:a162a104dc8217730fa42ed00cb7c071105943d4808bc7e5aa05efd5035408a7 |
| SCG-1／API Spec 草稿完成 | PRD §6（CLI、匯出、Bridge、console-api、資料庫、前端）；介面細則＝本檔 §C1～§C6；契約檔 `API_Contract_IssueCenter.md` 由 Console 開發棒依 §C 產出 | docs/01_requirements/Issue_Center_PRD.md | sha256:a162a104dc8217730fa42ed00cb7c071105943d4808bc7e5aa05efd5035408a7 |
| SCG-1／資料模型設計完成 | PRD §5.1（議題物件）、§5.4（游標、legend、summary）、§6.5（`console.issue_priority`）；本檔 R-IC-22～R-IC-37、R-IC-59、D-R4、§C1、§C6 | docs/01_requirements/Issue_Center_PRD.md | sha256:a162a104dc8217730fa42ed00cb7c071105943d4808bc7e5aa05efd5035408a7 |
| SCG-1／NFR 設計對應完成 | PRD §10 對應本檔 R-IC-42（確定性）、R-IC-43（零寫入與能力類別）、R-IC-44（效能與編碼）、R-IC-45（無快取）、R-IC-74（可及性） | docs/01_requirements/Issue_Center_PRD.md | sha256:a162a104dc8217730fa42ed00cb7c071105943d4808bc7e5aa05efd5035408a7 |
| SCG-1／整合架構說明完整 | 無第三方服務；依賴＝`tools/lib/selfimproving/` 既有 ro 模組、Bridge 子行程（`si export`）、backend JDBC（PostgreSQL）、前端既有元件（`SiDecideDialog`、`SiObsCloseDialog`、`PillTabs`）；PRD §6.3、§6.4、§9 | docs/01_requirements/Issue_Center_PRD.md | sha256:a162a104dc8217730fa42ed00cb7c071105943d4808bc7e5aa05efd5035408a7 |
| SCG-2／C4 Context 圖完成 | PRD §1、§4～§6（三類帳本→議題視角→Bridge→console-api→前端）；不新增系統邊界（Console 新增的唯一自有資料＝優先順序表） | docs/01_requirements/Issue_Center_PRD.md | sha256:a162a104dc8217730fa42ed00cb7c071105943d4808bc7e5aa05efd5035408a7 |
| SCG-2／C4 Container 圖完成 | PRD §9 模組落點表（根層 `tools/lib/selfimproving/`、Bridge `engine-bridge/`、backend `com/aisdlc/console/`、frontend `app/issues/` 與 `components/domain/issues/`）；本檔 §5.7 兩半檔案集合 | docs/01_requirements/Issue_Center_PRD.md | sha256:a162a104dc8217730fa42ed00cb7c071105943d4808bc7e5aa05efd5035408a7 |
| SCG-2／所有架構決策有對應 ADR | 本增量無新架構決策：沿 ADR-SI-12（Bridge 以子行程透傳 `si export`、Console 不寫帳本）；PRD §12 與主控裁決 2026-10-26（PRD §13）；不另開 ADR（PRD 檔頭） | docs/01_requirements/Issue_Center_PRD.md | sha256:a162a104dc8217730fa42ed00cb7c071105943d4808bc7e5aa05efd5035408a7 |
| SCG-2／Trust Boundary Map 完成 | 不適用（brownfield）；要點：根層與 Bridge 零寫入帳本、Console 唯一寫入＝順位表（僅 ADMIN）、`status`／`source` 輸入衛生（PRD §6.3）、純文字渲染（PRD §7）；本檔 R-IC-43、R-IC-46、R-IC-58、R-IC-68 | docs/01_requirements/Issue_Center_PRD.md | sha256:a162a104dc8217730fa42ed00cb7c071105943d4808bc7e5aa05efd5035408a7 |
| SCG-2／Before／After 架構對比 | 本檔 FRD-lite〈Before／After〉；PRD §9 模組落點表 | docs/01_requirements/Issue_Center_PRD.md | sha256:a162a104dc8217730fa42ed00cb7c071105943d4808bc7e5aa05efd5035408a7 |
| SCG-3／OpenAPI 3.1 規格完整 | 本檔 §C3（Bridge 兩路由）、§C4（console-api 四端點）；機器可讀版由 backend `/v3/api-docs` 與 `schema.d.ts` 鎖住（`OpenApiIT` 74 路徑、85 操作） | （本檔 §C0～C6；隨 Stage-2 凍結，自引、非上位文件） | n/a（自引） |
| SCG-3／Request／Response Schema 定義完整 | 本檔 §C1（匯出形狀、鍵序、snake／camel 對照）、§C4.1～C4.4、§C6 | （本檔 §C0～C6；隨 Stage-2 凍結，自引、非上位文件） | n/a（自引） |
| SCG-3／錯誤碼定義 | 本檔 §C3 驗證 rule 表、§C4 驗證序與狀態碼表、§C5（issue 類 reason 表；`issue_not_rankable`） | （本檔 §C0～C6；隨 Stage-2 凍結，自引、非上位文件） | n/a（自引） |
| SCG-3／Consumer Contract 完成 | 消費者＝前端 `/issues`（`lib/api`、`lib/domain/issues.ts`）、既有 `SiDecideDialog`／`SiObsCloseDialog`、掌舵者（SCG-5 實機）；黃金檔三份副本即消費者對拍（D-C7）；PRD §6.6、§7 | docs/01_requirements/Issue_Center_PRD.md | sha256:a162a104dc8217730fa42ed00cb7c071105943d4808bc7e5aa05efd5035408a7 |
| SCG-3／API ID 與 RTM 已對應 | API-IC-01～04（本檔 §C4）↔ AC-IC-07-4、07-5、09-1～09-11；AT 到 RTM 見本檔 §1 與 §6 | docs/01_requirements/Issue_Center_PRD.md | sha256:a162a104dc8217730fa42ed00cb7c071105943d4808bc7e5aa05efd5035408a7 |
| SCG-3／Contract 已 Review 通過 | 由未參與規格與實作的 QA 於 SCG-4 獨立審查（兩把鍵各自的審查報告）；SCG-3 預審 FAIL（T-01～T-19）已於凍結前併入本檔正文 | docs/01_requirements/Issue_Center_PRD.md | sha256:a162a104dc8217730fa42ed00cb7c071105943d4808bc7e5aa05efd5035408a7 |

> 凍結摘要＝該文件在 `frozen_stages[*].spec_doc_digests` 的值。PRD 的值是 Stage-1 凍結的 digest；本檔作者於 2026-10-27 以 SHA-256 對工作樹現況重算一致（`a162a104…5408a7`；LF-only，95,802 bytes），HEAD `1e82dd18d5d2b4950ebe30b8e939a35953871c7a`。凍結後的實際 digest 以該鍵 `show --json` 的 `frozen_stages[-1].spec_doc_digests` 為準，與本表不符時以 `show` 為準並更正本表。

### R 條文（把 PRD §2～§7 逐條化；每條可判定）

「突變」欄＝會使對應 AT 轉紅的最小改動（QA 在 `git archive` 匯出的暫存副本上套用，不動工作樹）；「AT」欄為 AC 簡碼（例 `01-1`＝`AT-IC-01-1-*` 全部）。

#### A 對照表與 fail-loud（PRD §4；`issuemap.py`、`issues.py`）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-IC-01 | `issuemap.py` 是顯示層唯一真相源：七狀態（候選、待您決定、待解、進行中、觀察中、延後、已完成；順序固定）、八結果、四來源（順位：使用者提案＞系統缺陷＞研究提案＞系統改善）、四嚴重度（緊急 1、高 2、中 3、低 4）、21 事件動作、9 決定動詞、4 通道、5 problems 碼、9 ne 理由；其他檔不得持有第二份 | 刪一個狀態；對調兩來源順位 | 01-1、01-5、01-7、06-2 |
| R-IC-02 | 歸類函式：機器值→（狀態，結果）依 PRD §4.2 全表；每個機器值（含條件欄每種取值）恰一個歸類；表外回 `None`、由呼叫端 fail-loud | `merged@` 歸「已修復」 | 01-1、01-3 |
| R-IC-03 | 雙向封閉鎖 `issuemap.closure_problems(upstream=None)`：鍵集合與 `events.PROP_STATES`（10）、`KINDS`（21）、`DKINDS`（9）、`ROUTES` 的 `handoff:` 後綴（4）、`rows.CATEGORIES`（5）、`SEVERITIES`（4）、處置首詞（8）、`defs` 狀態標籤（5）雙向相等；上游有而表無＝回非空 | 上游加一值而表不登記 | 01-1、01-7 |
| R-IC-04 | 處置首詞：八個探針逐一餵 `rows.disp_token`；`DISP_TOKEN_RE.pattern` 第一個捕捉群組內分支數＝8（解析 pattern 字串，不改 `rows.py`） | pattern 加第 9 分支 | 01-1 |
| R-IC-05 | 嚴重度兩組鍵：觀察組＝`rows.SEVERITIES` 雙向；缺陷組＝`issuemap.DEF_SEVERITIES`（P0～P4）子集鎖；缺陷嚴重度取欄首 `P`＋數字（只略過開頭空白、`*`、`_`；後綴不看）；P0、P1→緊急、P2→高、P3→中、P4→低；不以 P0～P4 起頭（含 P5、P10）＝表外值 | P0 歸高；P5 歸低 | 01-4 |
| R-IC-06 | 表外值 fail-loud：狀態、結果、來源、嚴重度的表外值一律顯示「未歸類：<原值>」（來源查不到者為來源項目 ID 以「、」相接）；不歸入任何類、不丟該筆；`severity_rank` 為 null、`rankable` false、`action` null；顯示原值超過 80 code point 取前 80 加「…」（不計入），`problems.detail` 逐字完整 | 表外值靜默歸候選；截斷也截 detail | 01-2、01-3、01-4、01-10、04-10 |
| R-IC-07 | `problems` 一筆一值：每個表外值各一筆 `{subject:<議題 ID>, code:'UNMAPPED', detail:'<維度>：<原值>'}`（維度詞：狀態、結果、來源、嚴重度、時間線動作、決定動詞、通道）；同值不合併、不彙總；未歸類議題只在無 `status` 篩選的結果出現、不計前三分頁，`summary.unmapped` 另計 | 同值合併為一筆 | 01-2、01-6 |
| R-IC-08 | `problems` 碼封閉五個（`ROW-ARITY`、`ID-DUP`、`UNMAPPED`、`EVENT-PARSE`、`EVENT-UNSOUND`）、`ne` 理由封閉九個；`issues.py` 只產出表內者（產出⊆表）且表內每項至少有一個夾具觸發（表⊆產出）；各有非空中文 | 新增未登記碼 `FOO`；表多一碼而無夾具 | 01-7 |
| R-IC-09 | 量不到≠表外值：欄位根本沒有值（來源項目全查不到嚴重度、時間欄解不出、卡面建不出、量測窗進度量不到）＝該欄 null 或固定句並列 `ne`，顯示「—」；不顯示成零、低或空字串 | null 改為「低」 | 01-4、04-2、04-3、04-7 |
| R-IC-10 | 整本帳不可用（觀察主檔、缺陷主檔、姊妹軌之一、事件帳本缺檔或不可讀；缺陷主檔與姊妹軌另含無合格表頭；判法見 D-R13）：該類議題整批缺席，`ne` 各多一筆（`OBS-`、`DEFECT-`、`SIBLING-`、`EVENT-LEDGER-UNAVAILABLE`；事件帳本缺檔不再另報 `carrier-not-established`）；`by_tab` 依 D-R5 為 null；`total`、`by_status` 只計讀得到的；rc 0 | 缺檔拋例外；`by_tab` 顯示 0 | 01-8 |
| R-IC-11 | 連帶規則：觀察帳本讀不到時，來源項目含觀察號的提案其 `source`、`severity` 為 null（僅有 DEF 號來源者照常判定），不走 `UNMAPPED`、不另生逐項 `ne`；事件帳本讀不到時，需 attr 判定的 open 觀察列暫列候選（decision 類與路徑 B 照常） | 缺檔時提案來源判為「未歸類」 | 01-11 |
| R-IC-12 | 事件帳本結構問題：非 JSON 物件的行（含空白行；檔尾單一換行不計）＝`EVENT-PARSE`（subject `L<行號>`）；JSON 物件但 `events.validate` 非空＝`EVENT-UNSOUND`（subject `L<行號>`，一筆一事件、不進折疊）；其餘事件照常 | 不合格事件仍進折疊 | 01-9 |

#### B 來源與成為正式議題（PRD §2、§3）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-IC-13 | 議題集合：觀察＝主檔加 `SelfImproving_Observation_Ledger_archive*.md`（依檔名排序、先中者勝）的每個九欄合法列；缺陷＝`AutoSDD_Defect_Log.md` 主檔的每個資料列（`defs.load_rows`，**不讀** `AutoSDD_Defect_Log_archive_*.md`）；姊妹軌孤列；提案＝`fold.fold` 折疊的每個 PROP（取最新修訂）；RUN、ATT、DEC、APP、MEA 不是議題 | 讀缺陷歸檔檔；RUN 成議題 | 06-5、04-9 |
| R-IC-14 | 壞列與重複：觀察列欄數不符或 ID 欄不合、缺陷列 `arity_ok` 為假＝不成議題、各一筆 `ROW-ARITY`；同 ID 多列只收第一列，後列 `ID-DUP`；缺陷 ID 欄不合者由 `load_rows` 略過（已知限制，不計 problems）；`problems`、`ne` 為整本帳一份 | 後列覆蓋前列 | 04-9、05-5 |
| R-IC-15 | 姊妹軌：〈缺陷總表〉表頭含 `DEF-ID`、`解鎖條件（可機械查）`、`最近複查日` 者依欄名定位；欄數與表頭不符的列不採用並 `ROW-ARITY`（subject `<檔名>:L<行號>`）；DEF-ID 在主檔有列＝該議題延後；主檔找不到＝孤列議題（系統缺陷、延後、title「（主帳本列已歸檔）」、severity null 並列 `ne`、不進 problems）；「格式定義」節兩欄表不是資料表；兩檔重複 ID 後者 `ID-DUP` | 孤列丟棄；孤列進 problems | 04-5 |
| R-IC-16 | 來源順位（觀察列）：標記 `來源=人` 或 `carrier=console`→使用者提案；否則分類 bug→系統缺陷；否則 `回報者=研究者`（全等）→研究提案；否則系統改善；缺陷列一律系統缺陷；提案取 `sources` 各項判定中順位最前者，查不到者略過，全查不到＝「未歸類：<ID 以「、」相接>」＋`UNMAPPED` | 研究者與 bug 順位對調 | 02-1、02-2、02-3、02-4、02-5 |
| R-IC-17 | 觀察 open：路徑 A＝存在 attr（type root 的 `obs` 含該列，或 type link 的 `from` 為該列）且 `Att.settled[0]=='attr.confirm'`；路徑 B＝標記 `carrier=console` 或 `來源=人`；分類 decision→待您決定（不論路徑）；其餘 A 或 B 成立→待解；否則候選；未確認或 `attr.reject`＝仍候選；終值與 deferred 永不為候選 | attr.reject 也算成立 | 03-1、03-2、03-3、03-4 |
| R-IC-18 | 待您決定恰四類成員：提案 proposed、提案 verified、復發待回滾的 closed 提案、分類 decision 的 open 觀察列；改善類（process、tooling、doc）的正式議題進待解 | 改善類進待您決定 | 03-6、04-10 |
| R-IC-19 | closed 提案（D-R3、D-R9）：依序判——`rolled-back` 或 `consumed≥1`＝已完成、已回滾；生效結果不在 {clean、recurred}＝已完成「未歸類：closed」（量不到，排在已回滾之後）；`pending≥1`＝進行中；`decided=0` 且 `recurred`＝待您決定；其餘（clean）＝已完成、已採納。promoted／measuring 且 `pending≥1`＝進行中，否則觀察中。待您決定者與 `meaplan.rollback_pending` 差分相等（限合法事件鏈） | 改 `decided` 計法；把量不到的判序移到已回滾之前 | 03-7、01-3 |
| R-IC-20 | 提案其餘態：proposed、verified→待您決定；approved、returned、sandboxed→進行中；rejected→已完成、已否決；handed-off→已完成、已轉交；`PROP_STATES` 之外＝表外 | approved 歸待您決定 | 01-2、03-4、04-10 |
| R-IC-21 | 觀察處置（`rows.disp_token`）：deferred→延後；`fixed@`→已修復；decided→已裁決；retired→已退役；`merged@`→已合併；`DEF-`、`proposed@`→已轉交；`None`＝表外。缺陷：open→待解、routed→進行中、fixed→已修復、wontfix→已否決、closed-by-decision→已裁決（皆已完成除前二）；在姊妹軌→延後；`status is None`＝表外 | wontfix 歸已裁決 | 01-2、01-3、04-5 |

#### C 欄位與下一步（PRD §5.1、§5.2）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-IC-22 | 議題物件鍵序固定（§C1.2）；清單項目不含 `raw`、`timeline`、`priority`、`priority_note`；單筆另有 `raw`、`timeline`（置於 `action` 之後） | 清單項目帶 `raw` | 04-6、05-1 |
| R-IC-23 | `title`：觀察＝症狀欄；缺陷＝現象與證據欄；提案＝卡面〈一、症狀〉（`card.build().fields['symptom']`）；孤列固定「（主帳本列已歸檔）」；移除 `**`、`__`、`~~`、反引號、空白折疊後 ≤80 code point（超過取前 80 加「…」）；`CardError`＝「（提案 <ID>：卡面量不到）」＋`ne` `CARD-UNAVAILABLE` | 以 UTF-16 單元計長 | 04-3、04-7 |
| R-IC-24 | `updated_at`（`YYYY-MM-DD`；日期部分直取、不換算時區）：觀察＝時間欄起日（區間取起），若有該列 `obs.close` 事件則取兩日較晚者；缺陷＝發現日期；孤列＝最近複查日；提案＝`last_seq` 事件的日期；解不出＝null＋`ne` `TIME-UNPARSEABLE` | obs.close 日期覆蓋較晚的起日 | 04-3 |
| R-IC-25 | `source` 見 R-IC-16；`severity`：觀察取嚴重度欄、缺陷依 R-IC-05、提案取 `sources` 中最嚴重者；孤列與全查不到＝null＋`ne` `SEVERITY-UNAVAILABLE`（field `issues.<ID>.severity`） | 提案取最輕者 | 01-4、04-5 |
| R-IC-26 | `origin`：觀察、缺陷 `{ledger, file, line}`（`ledger` 為「觀察帳本」「缺陷帳本」；`file` 為 repo 相對 POSIX 路徑；`line` 為 1 起算行號，缺陷＝`DefRow.lineno`）；孤列 `file` 為姊妹軌檔；提案 `{ledger:'事件帳本', file, seq}`（`seq`＝`prop` 事件 `created_seq`） | file 用反斜線 | 04-8 |
| R-IC-27 | `links`（去重、依 ID 排序）：雙向類＝提案 `sources`↔來源議題、觀察處置指向的 `DEF-`／`merged@`／`proposed@`↔目標議題；單向類＝標記 `rel`（取冒號後的 ID）、`reopens`、attr link 的 `from`→`reopens`（只有起點含目標）；指向主檔以外 DEF 的處置仍列入 | 單向類也回列 | 04-4 |
| R-IC-28 | `rankable`＝狀態∈{待您決定、待解、進行中}；`action`：待您決定的提案→`decide-proposal`、待您決定的觀察→`close-observation`、其餘 null；未歸類議題 `rankable` false、`action` null | 觀察中 `rankable` 為真 | 04-10、03-3 |
| R-IC-29 | `raw`（僅單筆）：觀察九欄與缺陷七欄（孤列為姊妹軌五欄）以帳本表頭為標籤、值逐字；提案＝`提案卡`（全文；`CardError` 時省略）加 `狀態`、`路由`、`類別`、`動作`、`修訂`、`摘要碼`、`來源項目`（原值） | 值被截斷 | 04-6、04-7 |
| R-IC-30 | `timeline`（僅單筆；`[{seq,t,by,action}]` 依 `seq` 升冪）：引用鍵見 PRD §5.1；`action` 取 §4.5 中文，`dec` 顯示「決定：<動詞中文>」；`research.*`、`resume` 不掛任何議題；表外動作或動詞＝「未歸類：<原值>」＋`UNMAPPED` | 以降冪輸出 | 04-6、04-11 |
| R-IC-31 | `next_step`：PRD §5.2 十九情境各恰一句（§5.3 的 N01～N19），全句 ≤80 code point、不含 §5.4 英文詞（議題 ID 形態與延後列方括號內原文節錄除外）；代入值 `[rev]`（折疊後 `Prop.rev`）、`[n_opp]／[w_opp]`、`[通道中文]`、`[結果]`、`[目標 ID]`、延後原文截 40 code point（空節錄＝「（帳本未寫明）」）；已完成的提案已否決者加「；同型冷卻中」（`f.cooldowns` 有該提案）或「；冷卻已解除」（`unblocked`） | verified 句寫成「驗證通過」 | 04-1 |
| R-IC-32 | 量測窗進度：measuring 取 `status.measure_value(...)['windows']` 中該 PROP 的 `n_opp` 與該提案 `mea.open` 的 `w_opp`→「量測窗 n／w」；NOT-EVALUABLE 或查無該窗→「量測窗進度量不到」＋`ne` `MEASURE-UNAVAILABLE`（field `issues.<ID>.next_step`）；`issues.py` 原始碼不含 `window_rows` | 直呼 `meaplan.window_rows` | 04-2 |

#### D 排序、游標、摘要、legend（PRD §5.3、§5.4）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-IC-33 | 顯示序兩條：第一條（待處理、待您決定）＝順位升冪（無順位或非 rankable 排最後）→`severity_rank`（前端 `severityRank`）升冪（null 最後）→`updated_at`（前端 `updatedAt`）升冪（null 最後）→`id` 升冪；第二條（已完成、全部）＝`updated_at` 降冪（null 最後）→`id` 升冪；全部分頁另把待您決定列置頂（其內依第一條）；根層與前端各一份（前端一份屬 Console 半）、同表兩端驗 | 排序鍵對調；null 排最前 | 05-1、05-7、09-10 |
| R-IC-34 | CLI 文字表頁內顯示序依 D-R6 選規則；`--json` 與 `export` 的 `items` 永遠依游標升冪 | `--json` 也套顯示序 | 05-1、05-6 |
| R-IC-35 | 游標依 D-R4；`items` 依游標升冪；`since` 取游標嚴格大於；篩選先於分頁；`limit` 缺省＝`export_limit_max`；`truncated`＝符合者多於上限；`next_since`＝本頁最後一項游標、末頁 null；附加新列不改既有項游標；號碼或行號 ≥S 者不成議題、`ROW-ARITY`（detail「編號或行號過大，游標無法編碼」；該碼的 legend 釋義在 PRD §4.5 句後加「；編號或行號過大而無法編入游標者同樣不成議題」） | 游標改用 DEF 號；`since` 改大於等於 | 05-2、05-3 |
| R-IC-36 | `summary`＝`{total, by_status{七狀態}, by_tab{待處理、待您決定、已完成}, unmapped}`：整本帳計數、不受篩選、`since`、`limit` 影響；`total`＝七狀態件數和加 `unmapped`；`by_status` 七鍵恆在；`by_tab` 的 null 依 D-R5；`by_tab.待處理`＝待解＋進行中＋觀察中 | 計數套用篩選 | 05-5、01-8、01-6 |
| R-IC-37 | `legend`（僅清單回應）：`statuses[{name,meaning,tab,rankable}]`（7）、`results[{name,meaning}]`（8）、`sources[{name,meaning}]`（4，依順位）、`severities[{name,rank,meaning}]`（4）、`problem_codes[{code,meaning}]`（5）、`ne_reasons[{reason,meaning}]`（9）、`unmapped_label`（「未歸類」）、`updated_at_note`（含「最後已知動靜」）；全取自 `issuemap`；單筆不帶 `legend`、`summary` | legend 少一個結果 | 01-5、04-6、08-2 |

#### E CLI 與匯出（PRD §6.1、§6.2；`selfimproving.py`、`export.py`）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-IC-38 | `issues` 動詞（薄殼，判準全在 `lib/`）：旗標 `--status`、`--source`、`--since`、`--limit`、`--json`、`--repo`；預設輸出中文表（欄依顯示寬度對齊、欄間兩空白；每列「編號、來源、嚴重度、狀態（已完成併列「・結果」）、最後更新、標題→下一步」；null 顯示「—」）；末行「共 N 件；問題 M 筆」（N＝本頁列數、M＝`len(problems)`），被截斷加「；尚有更多，--since <next_since>」；`--json`＝與 `export --kind issues` 同一物件（一行 JSON、LF） | 全形字按 1 寬對齊 | 05-6、06-2 |
| R-IC-39 | 篩選：`--status` 值＝七狀態名或「待處理」（＝待解＋進行中＋觀察中）；`--source` 值＝四來源名；逗號取聯集、兩旗標取交集；未知值（含空字串、含前後空白）→rc 3 且 stderr 列合法值；`--since`≥0、`--limit` 介於 1 與 `export_limit_max` 否則 rc 3；rc 0＝已執行、3＝用法或輸入錯誤；唯讀、不讀家目錄 | 未知值被忽略 | 05-2、05-4 |
| R-IC-40 | `export --kind issues`：`KINDS` 加 `issues`；`--json` 仍必填；`--id` 接受 `OBS-SI-\d{3,}`、`PROP-SI-\d{3,}`、`DEF-\d+-\d+` 三種且不與 `--status`、`--source` 併用；`--status`、`--source` 只配 `--kind issues`（其餘 kind 帶它們＝rc 3）；形狀沿既有、`schema_rev` 維持 1 | `--id` 接受小寫 ID | 05-4、04-6、06-2 |
| R-IC-41 | `ne` 條目 `{field, reason}` 與 `problems` 條目 `{subject, code, detail}` 的欄位命名依 D-R10 與 §C1.5；`generated_at`、`head_sha` 沿既有（git 取不到＝null＋`git-unavailable`） | field 用中文 | 01-7、01-8 |
| R-IC-42 | 確定性：同帳本與 repo 兩次輸出逐位元相同（`generated_at` 除外） | items 依 dict 雜湊序 | 06-2、12-3 |
| R-IC-43 | 零寫入與能力類別：`issues.py`、`issuemap.py` 登記 `ro`（無寫檔、無網路、無子行程）；不 import rw、net、exec 模組；不讀家目錄；不新增守衛碼；動詞數只比功能前多 `issues` | 加寫檔原語 | 06-1、06-3、06-4、03-5 |
| R-IC-44 | 效能與編碼：真帳本 ≤2 秒（連 5 次）、單頁 ≤1 MB；合成規模（觀察 5,000、缺陷 2,000、事件 500）≤2 秒；stdout 為 UTF-8 無 BOM、LF；中文 argv 跨平台一致 | 逐項重讀帳本（O(n²)） | 12-1、12-2 |

#### F Engine Bridge（PRD §6.3；`si_cli.py`、`routers/si.py`）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-IC-45 | 路由 `GET /si/issues`、`GET /si/issues/{id}`：每請求恰啟動一次 `si export` 子行程、無快取；200 本文＝子行程輸出解析後逐值透傳；其他方法 405；與同參數根層 `export --kind issues` 逐值相同（`generated_at` 除外） | 加快取；透傳時重排鍵 | 07-1、12-3、06-1 |
| R-IC-46 | 輸入驗證在子行程之前（422 `invalid_request`，`violations[{field,rule,message}]`，D-C1）：清單只收 `since`、`limit`、`status`、`source`（其餘 `unknown_parameter`）；單筆不收任何查詢參數；`status`／`source` 值 ≤64 字元（`too_long`）、不以 `-` 起頭（`leading_dash`）、不含 U+0000～U+001F、U+007F（`control_char`），不合不啟動子行程；`{id}` 須符三種格式（`invalid_format`）；合法而查無 404 `si_not_found` | 長度改 ≤65；漏擋 U+007F | 07-1、07-2 |
| R-IC-47 | argv：`build_argv` 增 `status`、`source` 參數，以單一 argv `--status=<值>`、`--source=<值>` 傳入（位於 `--limit` 之後、`--id` 之前）；`SI_KINDS` 末位加 `issues`；組 argv 的函式仍恰兩個、`Popen` 呼叫仍一處（AST 鎖不變） | 拆成兩個 argv；加 `shell=True` | 07-2、07-3 |
| R-IC-48 | 失敗映射：CLI rc≠0（含未知篩選值 rc 3、`limit` 越界）→503 `si_unavailable`（`cause=nonzero_rc`，`detail` 逐字）；其餘 cause 沿既有九值；空字串篩選值不特判（rc 3→503） | rc 3 改回 422 | 07-3 |

#### G console-api 讀取（PRD §6.4；`IssueController`、`BridgeHttpAdapter`）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-IC-49 | `GET /api/v1/issues?status=&source=&since=&limit=`：VIEWER 以上；轉遞 Bridge 物件（鍵經 `SiKeyNames`、值不動）並於每筆加 `priority`、`priorityNote`（僅 `rankable` 為真且有列→值，否則 null；加在 `action`、`raw`、`timeline` 之後）；`since`<0、`limit`<1＝400 且不觸及 Bridge；每請求恰一次 Bridge 呼叫（連線 2 秒、讀取 20 秒、不重試）與一次順位表讀取；任何失敗無 `data` | 失敗時回空 `items`；null 改補 0 | 07-4、07-7、12-3 |
| R-IC-50 | `GET /api/v1/issues/{id}`：含 `raw`、`timeline`、`links` 與 priority；404 `si_not_found`（訊息「查無此議題」、`details.id`）；格式不合 422（頂層 reason `引擎拒絕此請求`、`details.bridgeReason`＝`invalid_request`）；不收查詢參數 | 訊息沿用「查無此提案」 | 07-5 |
| R-IC-51 | `AgentBridge.siExport(kind, since, limit, id, status, source)` 六參數（String、Integer、Integer、String、String、String）；`si` 起頭方法仍恰五個；`SiMirrorQueryService`、`SiReconcileService` 補 `null`；`BridgeHttpAdapter.siExport` 對 `status`、`source` 嚴格 percent-encode（UTF-8、僅非保留字元原樣、大寫十六進位）再 `URI.create` | 漏編空白或豎線；改用範本引擎 | 07-2、07-6 |
| R-IC-52 | 失敗沿 SI 唯讀端點：Bridge 503→503 `si_unavailable`（`details.cause`、`detail` 逐字）、連線拒絕→502、逾時→504、順位表讀取失敗→5xx；皆無 `data`、不重試 | 逾時重試一次 | 07-3、07-7 |
| R-IC-53 | `IssueController` 名稱不符 `Si*Controller`（不受該組計數鎖）；恰一個 `@PutMapping`、一個 `@DeleteMapping`；`SiController` 的 GET 七、POST 四不變；Issue* 類別呼叫 `AgentBridge` 的方法只有 `siExport` | 加第二個 `@PutMapping` | 07-6、09-8 |

#### H 優先順序（PRD §6.4、§6.5；`IssuePriority*`、V14）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-IC-54 | `PUT /api/v1/issues/{id}/priority`：僅 ADMIN；body `{rank, note}`；`rank` 必填整數 1～9999（null、缺、0、-1、1.5、字串、`true`、`[]`、`{}`、10000＝422，**不**當清除）；`note` 選填（缺＝空字串；數字與 null＝422）、≤200 code point（全形與表情符號各算 1）、不含 U+0000～U+001F、U+007F（含首尾換行）；本文不是 JSON 物件＝400 `MALFORMED_REQUEST_BODY`；成功 200 `{id, rank, note, setBy, setAt}` | note 以 UTF-16 單元計；rank=null 當清除；`[]` 本文回 422 | 09-1、09-3、09-7 |
| R-IC-55 | PUT 驗證序：401→403 `ACCESS_DENIED`→422 `invalid_request`（`violations[{field,message}]` 一次全列；`id` 格式與 DB CHECK 同式）→取該議題（D-C4）：503／502／504、查無 404 `si_not_found`、`rankable` 為 false 409 `issue_not_rankable`→UPSERT；任一前序失敗零寫入；422 之前 Bridge 零呼叫 | 先 UPSERT 再驗 `rankable` | 09-3、09-5 |
| R-IC-56 | `DELETE …/priority`：僅 ADMIN；無 body；成功 204；列不存在也 204（冪等）；不呼叫 Bridge；驗證序 401→403→422（`id` 格式）→DELETE；議題已完成或已不存在仍清得掉遺留順位 | 列不存在回 404 | 09-4、09-10 |
| R-IC-57 | PUT、DELETE 都不要求 `console.si.deciders` 名單（優先順序不是帳本決定） | 套用名單檢查 | 09-1 |
| R-IC-58 | 安全層：`SecurityConfig` 在通用 `/api/v1/**` 規則**之前**加 `PUT`、`DELETE` 的 `/api/v1/issues/**`＝ADMIN（各一條）；`AuditLoggingFilter`（位於授權之前）對成功與被拒（401、403）與失敗（422、409）都在 `console.audit_log` 留一列 | 兩條規則放在通用規則之後 | 09-2、09-11 |
| R-IC-59 | V14：`console.issue_priority(issue_id VARCHAR(64) PK CHECK(格式), rank INTEGER NOT NULL CHECK(1～9999), note VARCHAR(200) NOT NULL DEFAULT '', set_by VARCHAR(64) NOT NULL, set_at TIMESTAMPTZ NOT NULL)`；JDBC 配接器、無 JPA 實體；寫入敘述恰兩條（UPSERT、DELETE）加唯讀 SELECT；只有一個 persistence adapter 觸及該表；順位可重複；不存歷史 | 加第三條 UPDATE；rank 可為 NULL | 09-6、09-8 |
| R-IC-60 | 遺留列：非 `rankable` 的議題 `priority`、`priorityNote`＝null 且不參與排序；PUT→409；DELETE 清得掉 | 遺留順位仍顯示 | 09-10、05-1 |
| R-IC-61 | reason：新增 `issue_not_rankable`（409；`ErrorReasons.ISSUE_NOT_RANKABLE`；`details`＝`{id, status}`）；中文訊息住 `ISSUE_REASONS`、與契約表逐字相同；不進 `reasons.ts`；契約 reason 表只列 issue 類（D-C5）；兩端與契約表雙向鎖 | 前端訊息差一字 | 07-8、07-9、09-5 |

#### I 前端（PRD §6.6、§7；`/issues`）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-IC-62 | 路由與導覽：`/issues`（`app/issues/page.tsx` 只殼；title「議題中心」）；登記表第八項 `issues`（label「議題中心」、order 55、href `/issues`、mobile false、roles 缺、enabled true）加在陣列末尾；原七列各欄與位置不變；顯示序 monitor、issues、settings、self-improving；mobile 為 true 仍 6 項；`ToolsRegion.tsx` 不改 | 插在陣列中間 | 11-1、11-2、11-3 |
| R-IC-63 | 版面：標題列（「狀態說明」鈕）→摘要列（待處理 N、待您決定 M、已完成 K〔現存帳本內〕取 `summary.byTab`，null 格「—」，可點切分頁）→四個 pill 分頁（預設待處理，沿用 `PillTabs`）→篩選列（來源下拉；關鍵字＝編號與標題、只篩已載入的頁）→提示條（`ne`、`problems` 非空時，說明取自 `legend`）→清單 | 摘要 null 顯示 0 | 08-2、08-3、08-5、08-9 |
| R-IC-64 | 四分頁 `status` 傳值：待處理→「待處理」、待您決定→「待您決定」、已完成→「已完成」、全部→不帶；前端不持有狀態成員清單；待處理上方計件條六格（緊急、高、中、低、—、未歸類）加總＝待處理件數 | 前端展開成員清單 | 08-3、08-9、06-2 |
| R-IC-65 | 清單八欄（編號、來源、標題、嚴重度、狀態〔已完成併列結果〕、優先順序〔只對 rankable〕、最後更新、下一步〔待您決定列按鈕在此欄尾〕）；詳情側面板（不換路由）：頭部→下一步→原列（唯一可見英文原值處）→時間線→關聯（可點；查無顯示「不在議題中心（可能已歸檔）」）；已完成者日期旁註「最後已知動靜」（取 `legend.updatedAtNote`） | 詳情換路由；註記寫死 | 08-4、08-11 |
| R-IC-66 | 全部分頁：七顆狀態 pill（文字取 `legend`）加「未歸類」、來源下拉、關鍵字；待您決定列置頂（`data-testid="issue-top-pinned"`、`aria-label="置頂"`；其內依第一條）；已完成分頁：來源下拉、結果快篩（選項＝`legend.results`）、關鍵字，三者取交集 | 置頂元素漏 aria | 05-7、08-8、08-10 |
| R-IC-67 | 載入與空錯：逐頁取、沿 `SI_AUTO_LOAD_MAX_PAGES` 自動載完，到上限仍有未載入明說「結果不完整」並顯示已載入件數；真的沒有議題＝「這個分頁目前沒有議題」；Bridge 503、504＝整片顯示 `cause`、`detail` 逐字、摘要列「—」；某帳本讀不到＝依賴格「—」加提示條；進頁與重新整理都重取 | 錯誤時顯示空表 | 08-5、08-6、08-8、12-3 |
| R-IC-68 | 純文字：帳本與備註文字一律純文字；`components/domain/issues/**` 無 `dangerouslySetInnerHTML` 與 Markdown 渲染器 | 引入 react-markdown | 08-7 |
| R-IC-69 | 中文判準：可見文字（排除標題、ID、原列展開區、優先順序備註、延後列原文節錄）不含 §5.4 英文詞表（整詞比對）；詞表以 `lib/domain/issues.ts` 常數單一份持有 | 狀態 pill 顯示 `measuring` | 08-1 |
| R-IC-70 | 優先順序 UI：ADMIN 對 rankable 列有「排序」鈕→對話框（順位 1～9999、備註 ≤200 code point；儲存＝PUT、清除＝DELETE）；儲存後以回應為準重排（不樂觀）；非 ADMIN 看得到順位與備註、無編輯控制項、網路層無 PUT 與 DELETE | 儲存後先重排再等回應 | 09-9、09-10 |
| R-IC-71 | 決定按鈕（僅 ADMIN）：提案列「決定」＝先 `getSiProposal(id)` 取快照再開 `SiDecideDialog`（`target={{kind:"prop", proposal}}`，綁快照 digest；closed 提案動詞只有「回滾」）；觀察列「關閉並裁決」＝`SiObsCloseDialog`（`target={{obsId}}`）；簽章成功只代表稽核檔已落地，列不樂觀移動；非 ADMIN 該欄顯示「需要 ADMIN 角色才能操作」且無按鈕 | 用清單項的 digest | 10-1、10-2、10-4、10-5 |
| R-IC-72 | 議題中心唯一寫入＝PUT 優先順序與上述兩個既有對話框；`components/domain/issues/`、`lib/domain/issues.ts`、`Issue*.java` 無對 `/si/` 寫入端點的直接呼叫、無 `si decide`、`obs-close` 字樣 | 直呼 `postSiDecide` | 10-3 |
| R-IC-73 | 單一真相靜態鎖：新檔（`issues.py`、`components/domain/issues/**`、`lib/domain/issues.ts`、`Issue*.java`）不得含 ≥4 個不同的 `issuemap` 狀態鍵（詞表現讀其鍵集合）；掃描器自帶負控；前端掃描沿 `si.static.test.ts` 的 `walk`（略過 `tests` 目錄、`*.test.ts(x)`、`*.d.ts`）並明寫排除 `*.fixtures.ts` | 前端內嵌狀態詞清單 | 06-2 |
| R-IC-74 | 可及性：分頁、對話框、按鈕沿用既有元件（`PillTabs`、`Dialog`、`Button`）；鍵盤可切分頁、開詳情、開對話框、Esc 關閉、焦點回到觸發鈕；皆有 aria 標籤 | 自刻對話框漏焦點回歸 | 12-5 |
| R-IC-75 | 相容：既有「自我進化」頁、`/si/*` 六個 GET、`/api/v1/si/*` 七個 GET 與四個 POST 行為不變；既有測試除 §5.7 同步鎖外不改、不刪斷言；`schemaRev` 維持 1 | 順手改既有測試的斷言 | 12-4、11-2、07-6 |

### 契約節（可直接抄進 `AgentConsole/docs/02_architecture/API_Contract_IssueCenter.md`；本節為真相，契約檔不得與它不同）

#### C0 共通約定

| 項目 | 約定 |
|---|---|
| 命名 | `export`、CLI `--json`、Bridge 一律 snake_case；console-api 與畫面一律 camelCase（`SiKeyNames.camel`：鍵符合 `^[a-z][a-z0-9]*(_[a-z0-9]+)+$` 者轉換，其餘鍵恆等；**值一律不動**）。下表鍵名兩種寫法並列（snake／camel）；單字鍵兩者相同 |
| 封包 | 成功沿 P1b §0.2 `ApiResult<T>`：`{code:200, message:'success', data, timestamp, traceId}`；失敗沿 `ApiError`：`{code, message, reason?, errors[{field,message}], details?, timestamp, traceId}`；任何失敗沒有 `data` |
| 編碼與鍵序 | UTF-8、無 BOM、LF；`export` 為單一 JSON 文件一行；鍵序固定（下表由上而下；backend 以保序 Map）；console-api 追加的鍵在該物件最後 |
| 缺鍵與 null | 缺鍵與 `null` 語意不同（沿 P1b §0.2）：單筆缺 `legend`、`summary` 是「不適用」；`null` 是「量不到」 |

#### C1 `export --kind issues`（根層半交付；Bridge、backend 透傳）

**C1.1 頂層物件（鍵序）**

| snake／camel | 型別 | 清單 | 單筆（`--id`） | 說明 |
|---|---|---|---|---|
| `schema_rev`／`schemaRev` | int | 有 | 有 | 恆為 1 |
| `kind` | string | 有 | 有 | 恆為 `issues` |
| `generated_at`／`generatedAt` | string | 有 | 有 | ISO-8601 帶 offset、秒精度（沿既有 export） |
| `head_sha`／`headSha` | string 或 null | 有 | 有 | git 取不到＝null 並列 `ne` `git-unavailable` |
| `items` | array | 有 | 有（恰一筆；查無＝空陣列） | 議題物件（§C1.2） |
| `next_since`／`nextSince` | int 或 null | 有 | 有（恆 null） | 本頁最後一項游標；末頁 null |
| `truncated` | bool | 有 | 有（恆 false） | 符合者多於本頁上限 |
| `ne` | array | 有 | 有 | `{field, reason}`（§C1.5） |
| `problems` | array | 有 | 有 | `{subject, code, detail}`（§C1.5） |
| `legend` | object | 有 | **缺鍵** | §C1.3 |
| `summary` | object | 有 | **缺鍵** | §C1.4 |

**C1.2 議題物件（鍵序；`raw`、`timeline` 只在單筆；`priority`、`priorityNote` 只由 console-api 加，export 與 CLI 沒有）**

| snake／camel | 型別 | 值域與說明 |
|---|---|---|
| `id` | string | `OBS-SI-NNN`、`DEF-<族>-<序>`、`PROP-SI-NNN` |
| `source` | string 或 null | 使用者提案、系統缺陷、研究提案、系統改善、「未歸類：<原值>」；null＝所屬帳本讀不到（並列 `ne`） |
| `title` | string | R-IC-23；≤80 code point 加「…」 |
| `severity` | string 或 null | 緊急、高、中、低、「未歸類：<原值>」；null＝量不到 |
| `severity_rank`／`severityRank` | int 或 null | 1～4；量不到或表外＝null |
| `status` | string | 七狀態之一或「未歸類：<原值>」 |
| `result` | string 或 null | 八結果之一或「未歸類：<原值>」；僅 `status`＝已完成有值 |
| `updated_at`／`updatedAt` | string 或 null | `YYYY-MM-DD`；解不出＝null |
| `next_step`／`nextStep` | string | R-IC-31 |
| `origin` | object | 觀察、缺陷 `{ledger, file, line}`；提案 `{ledger:'事件帳本', file, seq}` |
| `links` | string[] | R-IC-27 |
| `rankable` | bool | R-IC-28 |
| `action` | string 或 null | `decide-proposal`、`close-observation`、null |
| `raw`（單筆） | `[{label, value}]` | R-IC-29；兩者皆 string |
| `timeline`（單筆） | `[{seq, t, by, action}]` | R-IC-30；`seq` int、`t` ISO-8601 帶 offset、`by`、`action` string |
| `priority`（console-api） | int 或 null | 僅 `rankable` 為真且有列＝值；否則 null |
| `priority_note`→`priorityNote`（console-api） | string 或 null | 同上；有列時可為空字串 |

**C1.3 `legend`（鍵序）**：`statuses[{name, meaning, tab, rankable}]`（7；`tab` 為專屬分頁名、候選與延後為 null）、`results[{name, meaning}]`（8）、`sources[{name, meaning}]`（4，依順位）、`severities[{name, rank, meaning}]`（4）、`problem_codes`→`problemCodes[{code, meaning}]`（5）、`ne_reasons`→`neReasons[{reason, meaning}]`（9）、`unmapped_label`→`unmappedLabel`（「未歸類」）、`updated_at_note`→`updatedAtNote`（含「最後已知動靜」）。

`problem_codes` 的 `ROW-ARITY` 釋義＝PRD §4.5 該句「帳本列欄數不符（觀察列另含 ID 格式不合），該列不成議題」後加「；編號或行號過大而無法編入游標者同樣不成議題」。

**C1.4 `summary`（鍵序）**：`total`（int）、`by_status`→`byStatus`（七狀態名→int，鍵序＝候選、待您決定、待解、進行中、觀察中、延後、已完成）、`by_tab`→`byTab`（`待處理`、`待您決定`、`已完成`→int 或 null，D-R5）、`unmapped`（int）。

**C1.5 `ne` 與 `problems` 條目**

| 清單 | 條目 | 鍵序與值 |
|---|---|---|
| `ne` | `{field, reason}` | `field`：整本帳 `ledger.observation`、`ledger.observation.<歸檔檔名>`、`ledger.defect`、`ledger.sibling.<檔名>`、`ledger.events`、`head_sha`；項目級 `issues.<ID>.<欄>`（欄∈severity、updated_at、title、next_step）。`reason`：九個封閉值（R-IC-08） |
| `problems` | `{subject, code, detail}` | `subject`：議題 ID、`L<行號>`（觀察無效列、事件帳本行）、`<檔名>:L<行號>`（姊妹軌列）；`code`：五個封閉值；`detail`：`UNMAPPED` 為「<維度>：<原值>」；`ROW-ARITY` 為「欄數與表頭不符」「ID 欄不合 OBS-SI-NNN」「編號或行號過大，游標無法編碼」三者之一；其餘為中文說明 |

**C1.6 游標（D-R4；S＝10,000,000）**

| 來源 | 游標 | 備註 |
|---|---|---|
| 觀察（含歸檔檔） | OBS 號的數字 | 範圍 [0, S) |
| 缺陷主檔 | S＋主檔資料列行號 | 行號＝`DefRow.lineno` |
| 提案 | 2S＋PROP 號的數字 | |
| `AutoSDD_External_Blocked_Log.md` 孤列 | 3S＋該檔行號 | |
| `AutoSDD_Structural_Debt_Log.md` 孤列 | 4S＋該檔行號 | |

`items` 依游標升冪；`since` 取游標嚴格大於者；號碼或行號 ≥ S 者不成議題（`ROW-ARITY`，detail「編號或行號過大，游標無法編碼」）；最大游標 4S＋行號 < 2^31。

**C1.7 範例（snake_case 原形；議題物件範例見 PRD §5.1 的 PROP-SI-005，清單與單筆只差 `raw`、`timeline`）**

```json
{"field": "ledger.sibling.AutoSDD_External_Blocked_Log.md", "reason": "SIBLING-LEDGER-UNAVAILABLE"}
{"field": "issues.PROP-SI-004.next_step", "reason": "MEASURE-UNAVAILABLE"}
{"subject": "OBS-SI-001", "code": "UNMAPPED", "detail": "狀態：later"}
{"subject": "L5", "code": "EVENT-UNSOUND", "detail": "事件未通過 events.validate，已略過"}
{"total": 597, "by_status": {"候選": 0, "待您決定": 0, "待解": 0, "進行中": 0, "觀察中": 2, "延後": 51, "已完成": 544}, "by_tab": {"待處理": 2, "待您決定": 0, "已完成": 544}, "unmapped": 0}
```

前四行依序是 `ne` 條目、`problems` 的 `UNMAPPED` 與 `EVENT-UNSOUND` 條目；末行是 `summary`（2026-10-26 真帳本參考值，非釘值）。`detail` 的中文說明字句不入 AT（AT 只驗 `code`、`subject`、`UNMAPPED` 的 detail 形如「<維度>：<原值>」）。

#### C2 根層 CLI（`tools/selfimproving.py`）

| 項目 | 約定 |
|---|---|
| `issues` | `python tools/selfimproving.py issues [--status <中文[,中文…]>] [--source <中文[,中文…]>] [--since N] [--limit N] [--json] [--repo <路徑>]`；rc 0＝已執行、3＝用法或輸入錯誤（stderr 一行「selfimproving: …」；未知篩選值列合法值）；唯讀 |
| 文字表 | 每列：`編號  來源  嚴重度  狀態[・結果]  最後更新  標題→下一步`（欄間兩空白、依顯示寬度對齊、null＝「—」）；末行 `共 N 件；問題 M 筆`＋被截斷時 `；尚有更多，--since <next_since>` |
| `export` | `python tools/selfimproving.py export --json --kind issues [--since N] [--limit N] [--id <ID>] [--status …] [--source …]`；`--id` 與 `--status`／`--source` 不併用；後二者只配 `--kind issues` |

#### C3 Engine Bridge（唯讀；每請求恰一次 `si export` 子行程；無快取）

| 路由 | 查詢參數 | argv（`<py>` 為直譯器、`<S>` 為腳本） | 成功 |
|---|---|---|---|
| `GET /si/issues` | `since`、`limit`、`status`、`source`（其餘 422 `unknown_parameter`） | `<py> <S> export --json --kind issues [--since N] [--limit N] [--status=<值>] [--source=<值>]` | 200，本文＝子行程輸出解析後逐值透傳 |
| `GET /si/issues/{id}` | 無（任何參數 422 `unknown_parameter`） | `<py> <S> export --json --kind issues --id <ID>` | 200（`items` 恰一筆）；`items` 空＝404 `si_not_found`（`id`） |

| 驗證（子行程之前；422 `invalid_request`，`violations[{field, rule, message}]`） | `rule` |
|---|---|
| 未知查詢參數 | `unknown_parameter` |
| `{id}` 不符 `OBS-SI-\d{3,}`、`PROP-SI-\d{3,}`、`DEF-\d+-\d+` | `invalid_format` |
| `status`／`source` 超過 64 字元 | `too_long` |
| `status`／`source` 以 `-` 起頭 | `leading_dash` |
| `status`／`source` 含 U+0000～U+001F、U+007F | `control_char` |

失敗映射沿 P1b §2.3：CLI rc≠0（含未知篩選值 rc 3）→503 `si_unavailable`（`cause=nonzero_rc`、`detail` 逐字）；其餘 cause 不變。其他 HTTP 方法 405。

#### C4 console-api（`/api/v1`；operationId 與 tag「議題中心（Issue Center）」）

| # | 方法與路徑 | operationId | 角色 | Bridge 呼叫 |
|---|---|---|---|---|
| API-IC-01 | `GET /api/v1/issues` | `getIssues` | VIEWER 以上 | `siExport('issues', since, limit, null, status, source)` |
| API-IC-02 | `GET /api/v1/issues/{id}` | `getIssue` | VIEWER 以上 | `siExport('issues', null, null, id, null, null)` |
| API-IC-03 | `PUT /api/v1/issues/{id}/priority` | `putIssuePriority` | 僅 ADMIN | 先 `siExport('issues', null, null, id, null, null)` 取單筆（D-C4） |
| API-IC-04 | `DELETE /api/v1/issues/{id}/priority` | `deleteIssuePriority` | 僅 ADMIN | 無 |

**C4.1 `GET /api/v1/issues`**：查詢 `status`（string，選填；七狀態名或「待處理」，逗號分隔）、`source`（string，選填；四來源名，逗號分隔）、`since`（int ≥0，選填）、`limit`（int ≥1，選填；上限住根層參數檔、不在此複製）。200 `data`＝§C1.1（含 `legend`、`summary`）經 camelCase、每筆加 `priority`、`priorityNote`。

| 狀態 | reason | details | 條件 |
|---|---|---|---|
| 400 | （無） | `errors[{field, message}]` | `since`<0、`limit`<1、型別不符（例 `since=abc`）；不觸及 Bridge |
| 401 | `UNAUTHENTICATED`／`TOKEN_EXPIRED`／`TOKEN_INVALID` | | 無有效 JWT |
| 422 | `引擎拒絕此請求` | `bridgeReason=invalid_request`、`violations` 逐項 | Bridge 422（`status`／`source` 衛生） |
| 502 | `引擎橋接服務無法連線`／`引擎橋接服務錯誤` | `bridgeStatus`（有才帶） | Bridge 不可達、回其他 4xx／5xx 或 200 本文非 JSON 物件 |
| 503 | `si_unavailable` | `cause`、`detail` 逐字 | Bridge 503（含 CLI rc≠0）；順位表讀取失敗為 5xx（無 `data`） |
| 504 | `引擎橋接服務逾時` | | 讀取逾時（約 20 秒、不重試） |

**C4.2 `GET /api/v1/issues/{id}`**：不收查詢參數。200 `data`＝§C1.1 單筆形（無 `legend`、`summary`；項目含 `raw`、`timeline`、`priority`、`priorityNote`）。錯誤同 C4.1，另：404 `si_not_found`（`details.id`；訊息「查無此議題」）；422 `引擎拒絕此請求`（`bridgeReason=invalid_request`，`{id}` 格式不合）。

**C4.3 `PUT /api/v1/issues/{id}/priority`**：body `{rank, note}`（見下表）；200 `data`＝`{id, rank, note, setBy, setAt}`（`setAt` 為 ISO-8601 帶 offset）。

| 欄位 | 型別與規則 |
|---|---|
| 路徑 `id` | 符 `^(OBS-SI-[0-9]{3,}\|PROP-SI-[0-9]{3,}\|DEF-[0-9]+-[0-9]+)$`（與 DB CHECK 同式） |
| `rank` | 必填；整數 1～9999；`null`、缺鍵、0、-1、1.5、字串、`true`、`[]`、`{}`、10000 一律 422（欄 `rank`），**不是 400**、不當清除 |
| `note` | 選填（缺＝空字串；只有缺鍵才是缺省）；string（數字與 `null` 一律 422，欄 `note`）；≤200 code point（全形與表情符號各算 1）；不含 U+0000～U+001F、U+007F |

| 驗證序（先中者定案） | 狀態 | reason | details |
|---|---|---|---|
| 無有效 JWT | 401 | `UNAUTHENTICATED` 等 | |
| 角色非 ADMIN | 403 | `ACCESS_DENIED` | |
| 本文不是 JSON 物件（`[]`、`"x"`；JSON 語法錯亦同） | 400 | `MALFORMED_REQUEST_BODY`（既有 reason，沿 `GlobalExceptionHandler.handleUnreadable`） | |
| 輸入閘 | 422 | `invalid_request` | `violations[{field, message}]` 一次全列（與 `errors[]` 互為鏡像） |
| Bridge 失敗 | 503／502／504 | 同 C4.1 | 同 C4.1 |
| 查無議題 | 404 | `si_not_found` | `id` |
| `rankable` 為 false | 409 | `issue_not_rankable` | `id`、`status`（中文狀態） |
| 成功（UPSERT） | 200 | | |

**C4.4 `DELETE /api/v1/issues/{id}/priority`**：無 body；成功 204（無本文）；列不存在也 204；不呼叫 Bridge。驗證序：401→403 `ACCESS_DENIED`→422 `invalid_request`（`id` 格式）→DELETE。兩個寫入端點都不要求 `console.si.deciders`；`AuditLoggingFilter` 對成功（200、204）、被拒（401、403）與失敗（422、409）各留一列 `console.audit_log`。

#### C5 reason

**C5.1 issue 類 reason 表（雙向鎖的對象；契約檔內以標題 `issue 類 reason 表` 起頭的第一張表為準，欄序固定）**

| reason | 狀態碼 | details | 中文訊息 | 意義 |
|---|---|---|---|---|
| `issue_not_rankable` | 409 | `id`、`status` | 此議題目前的狀態不能設定優先順序 | 議題狀態不是待您決定、待解、進行中（候選、觀察中、延後、已完成、未歸類）；PUT 不寫入 |

**C5.2 沿用的 reason（不入鎖表）**：`si_unavailable`（503）、`si_not_found`（404）沿 P1b；`invalid_request`（422）沿 P2b（後端區域常數）；`ACCESS_DENIED`（403）、`MALFORMED_REQUEST_BODY`（400）、`引擎拒絕此請求`、`引擎橋接服務無法連線`、`引擎橋接服務錯誤`、`引擎橋接服務逾時` 沿 P3-6 附錄 B。`reasons.ts`、`API_Contract_P3-6.md`、`Architecture.md` 一字不改（AC-IC-07-8）。

#### C6 資料所有權（V14）

```sql
CREATE TABLE console.issue_priority (
    issue_id VARCHAR(64) PRIMARY KEY CHECK (issue_id ~ '^(OBS-SI-[0-9]{3,}|PROP-SI-[0-9]{3,}|DEF-[0-9]+-[0-9]+)$'),
    rank     INTEGER      NOT NULL CHECK (rank BETWEEN 1 AND 9999),
    note     VARCHAR(200) NOT NULL DEFAULT '',
    set_by   VARCHAR(64)  NOT NULL,
    set_at   TIMESTAMP WITH TIME ZONE NOT NULL
);
```

寫入者只有 `IssuePriorityAdapter`（JDBC；UPSERT 與 DELETE 各一條敘述，另有唯讀 SELECT）；無 JPA 實體；不存歷史（變更軌跡在 `console.audit_log`）；順位可重複。

## 1. AC → AT 映射表

PRD 的 90 條 AC 逐條映射；每條至少一個正向 AT（`AT-IC-<FR>-<AC>-<n>`）與一個反向 AT（`AT-IC-<FR>-<AC>-E-<n>`；負控、邊界或錯誤路徑）。「載具」欄為 §3 的載具代碼。審查核對型（AC-IC-07-8、11-2、12-4）與實機型（AC-IC-09-6 的容器重啟、AC-IC-07-2 的 console-api 全鏈）分別走 G 編號審查閘與 Docker 全棧載具，見 §3 的 `GT`、`ES`。

#### FR-IC-01　對照表封閉、唯一歸類、fail-loud（PRD §4） — 11 條 AC、US-IC-01

| AC | 重點 | 正向 AT | 反向 AT | 載具 |
|---|---|---|---|---|
| AC-IC-01-1 | 對照表與上游集合雙向封閉；處置首詞探針與分支數 | AT-IC-01-1-1、AT-IC-01-1-2 | AT-IC-01-1-E-1、AT-IC-01-1-E-2 | RM |
| AC-IC-01-2 | 表外值 fail-loud：未歸類、problems 一值一筆 | AT-IC-01-2-1 | AT-IC-01-2-E-1 | RI |
| AC-IC-01-3 | 終態結果對照（八結果）；closed 量測量不到 | AT-IC-01-3-1、AT-IC-01-3-2 | AT-IC-01-3-E-1 | RI |
| AC-IC-01-4 | 嚴重度兩組鍵對照與表外值 | AT-IC-01-4-1、AT-IC-01-4-2、AT-IC-01-4-3 | AT-IC-01-4-E-1、AT-IC-01-4-E-2 | RM、RI |
| AC-IC-01-5 | legend 的內容、計數與順序 | AT-IC-01-5-1 | AT-IC-01-5-E-1 | RI、RX |
| AC-IC-01-6 | 三個表外值：problems 恰三筆、不合併 | AT-IC-01-6-1 | AT-IC-01-6-E-1 | RI |
| AC-IC-01-7 | problems 碼與 ne 理由：產出⊆表且表⊆產出 | AT-IC-01-7-1、AT-IC-01-7-2 | AT-IC-01-7-E-1 | RI、RM |
| AC-IC-01-8 | 四種帳本缺檔：ne、byTab 為 null、其餘照常 | AT-IC-01-8-1、AT-IC-01-8-2、AT-IC-01-8-3、AT-IC-01-8-4 | AT-IC-01-8-E-1、AT-IC-01-8-E-2 | RI |
| AC-IC-01-9 | 事件帳本 EVENT-PARSE、EVENT-UNSOUND | AT-IC-01-9-1 | AT-IC-01-9-E-1 | RI |
| AC-IC-01-10 | 表外原值的 80 code point 截斷 | AT-IC-01-10-1 | AT-IC-01-10-E-1 | RI |
| AC-IC-01-11 | 帳本缺檔的連帶規則（提案來源、候選） | AT-IC-01-11-1、AT-IC-01-11-2 | AT-IC-01-11-E-1 | RI |

#### FR-IC-02　來源判定（PRD §2） — 5 條 AC、US-IC-02

| AC | 重點 | 正向 AT | 反向 AT | 載具 |
|---|---|---|---|---|
| AC-IC-02-1 | 使用者提案判定 | AT-IC-02-1-1 | AT-IC-02-1-E-1 | RI |
| AC-IC-02-2 | 研究提案判定 | AT-IC-02-2-1 | AT-IC-02-2-E-1、AT-IC-02-2-E-2 | RI |
| AC-IC-02-3 | 系統缺陷判定 | AT-IC-02-3-1 | AT-IC-02-3-E-1 | RI |
| AC-IC-02-4 | 系統改善判定 | AT-IC-02-4-1 | AT-IC-02-4-E-1 | RI |
| AC-IC-02-5 | 提案來源取順位最前；查不到者略過 | AT-IC-02-5-1 | AT-IC-02-5-E-1 | RI |

#### FR-IC-03　成為正式議題（PRD §3） — 7 條 AC、US-IC-03

| AC | 重點 | 正向 AT | 反向 AT | 載具 |
|---|---|---|---|---|
| AC-IC-03-1 | 候選：open、無 attr、無使用者標記 | AT-IC-03-1-1 | AT-IC-03-1-E-1 | RI |
| AC-IC-03-2 | 路徑 A：attr 已確認成立 | AT-IC-03-2-1 | AT-IC-03-2-E-1 | RI |
| AC-IC-03-3 | 路徑 B 與 decision 類 | AT-IC-03-3-1、AT-IC-03-3-2 | AT-IC-03-3-E-1 | RI |
| AC-IC-03-4 | 終值與 deferred 永不為候選；缺陷、提案不經候選 | AT-IC-03-4-1 | AT-IC-03-4-E-1 | RI |
| AC-IC-03-5 | 尚未入帳的 Console 稽核檔不是議題 | AT-IC-03-5-1 | AT-IC-03-5-E-1 | RI |
| AC-IC-03-6 | 待您決定四成員；改善類進待解 | AT-IC-03-6-1 | AT-IC-03-6-E-1 | RI |
| AC-IC-03-7 | closed 提案五夾具（復發待回滾等） | AT-IC-03-7-1、AT-IC-03-7-2 | AT-IC-03-7-E-1 | RI |

#### FR-IC-04　下一步與欄位（PRD §5） — 11 條 AC、US-IC-04

| AC | 重點 | 正向 AT | 反向 AT | 載具 |
|---|---|---|---|---|
| AC-IC-04-1 | next_step 十九情境句型與英文詞檢查 | AT-IC-04-1-1 | AT-IC-04-1-E-1、AT-IC-04-1-E-2 | RI |
| AC-IC-04-2 | measuring 的量測窗進度 | AT-IC-04-2-1 | AT-IC-04-2-E-1、AT-IC-04-2-E-2 | RI |
| AC-IC-04-3 | title 截斷與去記號；updated_at 規則 | AT-IC-04-3-1、AT-IC-04-3-2 | AT-IC-04-3-E-1 | RI |
| AC-IC-04-4 | links 方向（雙向類與單向類） | AT-IC-04-4-1、AT-IC-04-4-2 | AT-IC-04-4-E-1 | RI |
| AC-IC-04-5 | 延後（觀察、姊妹軌）與姊妹軌孤列 | AT-IC-04-5-1 | AT-IC-04-5-E-1、AT-IC-04-5-E-2 | RI |
| AC-IC-04-6 | 單筆 raw、timeline；清單不含 | AT-IC-04-6-1 | AT-IC-04-6-E-1 | RX |
| AC-IC-04-7 | 提案卡面量不到 | AT-IC-04-7-1 | AT-IC-04-7-E-1 | RI |
| AC-IC-04-8 | origin 的 file、line、seq | AT-IC-04-8-1 | AT-IC-04-8-E-1 | RI |
| AC-IC-04-9 | ROW-ARITY、ID-DUP；整本帳一份 | AT-IC-04-9-1 | AT-IC-04-9-E-1 | RI |
| AC-IC-04-10 | rankable 與 action 矩陣 | AT-IC-04-10-1 | AT-IC-04-10-E-1 | RI |
| AC-IC-04-11 | 時間線動作中文與表外動作 | AT-IC-04-11-1 | AT-IC-04-11-E-1 | RI |

#### FR-IC-05　排序、分頁、篩選、摘要（PRD §5.3、§5.4） — 7 條 AC、US-IC-05

| AC | 重點 | 正向 AT | 反向 AT | 載具 |
|---|---|---|---|---|
| AC-IC-05-1 | 排序兩規則（根層與前端同表） | AT-IC-05-1-1、AT-IC-05-1-2 | AT-IC-05-1-E-1、AT-IC-05-1-E-2 | RI、FL |
| AC-IC-05-2 | 游標分頁：無重複無遺漏；用法錯誤 rc 3 | AT-IC-05-2-1 | AT-IC-05-2-E-1 | RI |
| AC-IC-05-3 | 附加新列後以舊游標續取 | AT-IC-05-3-1 | AT-IC-05-3-E-1 | RI |
| AC-IC-05-4 | --status、--source 篩選與錯誤 | AT-IC-05-4-1 | AT-IC-05-4-E-1 | RI |
| AC-IC-05-5 | summary 恆為整本帳 | AT-IC-05-5-1 | AT-IC-05-5-E-1 | RI |
| AC-IC-05-6 | 文字表：中文、對齊、末行 | AT-IC-05-6-1 | AT-IC-05-6-E-1 | RI |
| AC-IC-05-7 | 全部分頁的置頂 | AT-IC-05-7-1 | AT-IC-05-7-E-1 | FV |

#### FR-IC-06　零寫入與單一真相 — 5 條 AC、US-IC-06

| AC | 重點 | 正向 AT | 反向 AT | 載具 |
|---|---|---|---|---|
| AC-IC-06-1 | 零寫入（根層、Bridge、console-api） | AT-IC-06-1-1、AT-IC-06-1-2、AT-IC-06-1-3 | AT-IC-06-1-E-1 | RI、BR、BI |
| AC-IC-06-2 | 同一帳本兩出口一致；靜態鎖只掃新檔 | AT-IC-06-2-1、AT-IC-06-2-2、AT-IC-06-2-3、AT-IC-06-2-4 | AT-IC-06-2-E-1、AT-IC-06-2-E-2、AT-IC-06-2-E-3 | RX、RI、FS、BS |
| AC-IC-06-3 | 動詞數與 CAPABILITY 登記 | AT-IC-06-3-1 | AT-IC-06-3-E-1 | RI |
| AC-IC-06-4 | si check 與 params.json 不變 | AT-IC-06-4-1 | AT-IC-06-4-E-1 | RI、GT |
| AC-IC-06-5 | 缺陷歸檔檔不讀；觀察歸檔檔照讀 | AT-IC-06-5-1 | AT-IC-06-5-E-1 | RI |

#### FR-IC-07　Bridge 與 console-api 傳遞（PRD §6.3、§6.4） — 9 條 AC、US-IC-07

| AC | 重點 | 正向 AT | 反向 AT | 載具 |
|---|---|---|---|---|
| AC-IC-07-1 | Bridge 兩路由：差分、405、422、404 | AT-IC-07-1-1 | AT-IC-07-1-E-1 | BR |
| AC-IC-07-2 | status／source 衛生與編碼 | AT-IC-07-2-1、AT-IC-07-2-2 | AT-IC-07-2-E-1、AT-IC-07-2-E-2 | BR、ES、BU |
| AC-IC-07-3 | CLI rc 非 0 → 503；console-api 無 data | AT-IC-07-3-1、AT-IC-07-3-2 | AT-IC-07-3-E-1 | BR、BI |
| AC-IC-07-4 | console-api 清單：camelCase、priority、400／401 | AT-IC-07-4-1 | AT-IC-07-4-E-1 | BI |
| AC-IC-07-5 | console-api 單筆：raw、timeline、404、422 | AT-IC-07-5-1 | AT-IC-07-5-E-1 | BI |
| AC-IC-07-6 | AgentBridge 簽章鎖與控制器計數 | AT-IC-07-6-1 | AT-IC-07-6-E-1 | BB |
| AC-IC-07-7 | 任何失敗都沒有 data | AT-IC-07-7-1 | AT-IC-07-7-E-1 | BI |
| AC-IC-07-8 | 變更清單不含三個凍結／雙向鎖檔（審查核對） | AT-IC-07-8-1 | AT-IC-07-8-E-1 | GT |
| AC-IC-07-9 | issue 類 reason 與契約表雙向鎖 | AT-IC-07-9-1、AT-IC-07-9-2 | AT-IC-07-9-E-1 | FL、BC |

#### FR-IC-08　畫面與中文（PRD §7） — 11 條 AC、US-IC-08

| AC | 重點 | 正向 AT | 反向 AT | 載具 |
|---|---|---|---|---|
| AC-IC-08-1 | 可見文字無英文機器值 | AT-IC-08-1-1 | AT-IC-08-1-E-1 | FV、FL |
| AC-IC-08-2 | 狀態說明取自 legend | AT-IC-08-2-1 | AT-IC-08-2-E-1 | FG |
| AC-IC-08-3 | 預設分頁、status 傳值、摘要列 | AT-IC-08-3-1 | AT-IC-08-3-E-1 | FV |
| AC-IC-08-4 | 清單八欄與詳情 | AT-IC-08-4-1 | AT-IC-08-4-E-1 | FV、FD |
| AC-IC-08-5 | 錯誤顯示；某帳本讀不到；提示條 | AT-IC-08-5-1、AT-IC-08-5-2 | AT-IC-08-5-E-1 | FV |
| AC-IC-08-6 | 自動載完與結果不完整 | AT-IC-08-6-1 | AT-IC-08-6-E-1 | FV |
| AC-IC-08-7 | 純文字渲染與靜態掃描 | AT-IC-08-7-1、AT-IC-08-7-2 | AT-IC-08-7-E-1 | FV、FS |
| AC-IC-08-8 | 全部分頁的快篩與空狀態 | AT-IC-08-8-1 | AT-IC-08-8-E-1 | FV |
| AC-IC-08-9 | 計件條六格與摘要列切分頁 | AT-IC-08-9-1 | AT-IC-08-9-E-1 | FV、FL |
| AC-IC-08-10 | 已完成分頁的三項篩選 | AT-IC-08-10-1 | AT-IC-08-10-E-1 | FV |
| AC-IC-08-11 | 最後已知動靜註記 | AT-IC-08-11-1 | AT-IC-08-11-E-1 | FD |

#### FR-IC-09　優先順序（階段二；PRD §6.4、§6.5） — 11 條 AC、US-IC-09

| AC | 重點 | 正向 AT | 反向 AT | 載具 |
|---|---|---|---|---|
| AC-IC-09-1 | PUT 成功與 upsert | AT-IC-09-1-1 | AT-IC-09-1-E-1 | BI |
| AC-IC-09-2 | 非 ADMIN：403、零寫入、audit | AT-IC-09-2-1 | AT-IC-09-2-E-1 | BI |
| AC-IC-09-3 | PUT 輸入驗證與邊界 | AT-IC-09-3-1 | AT-IC-09-3-E-1、AT-IC-09-3-E-2 | BI |
| AC-IC-09-4 | DELETE 冪等 | AT-IC-09-4-1 | AT-IC-09-4-E-1 | BI |
| AC-IC-09-5 | 不可排（409）、查無、Bridge 失敗 | AT-IC-09-5-1 | AT-IC-09-5-E-1 | BI |
| AC-IC-09-6 | V14 升級、約束與持久 | AT-IC-09-6-1、AT-IC-09-6-2 | AT-IC-09-6-E-1 | BM、ES |
| AC-IC-09-7 | 後者生效；併發 | AT-IC-09-7-1 | AT-IC-09-7-E-1 | BI |
| AC-IC-09-8 | 零帳本寫入與 ArchUnit | AT-IC-09-8-1、AT-IC-09-8-2 | AT-IC-09-8-E-1 | BA、BI |
| AC-IC-09-9 | 前端優先順序 UI 與權限 | AT-IC-09-9-1、AT-IC-09-9-2 | AT-IC-09-9-E-1 | FV、FP |
| AC-IC-09-10 | 狀態轉為已完成後的遺留列 | AT-IC-09-10-1 | AT-IC-09-10-E-1 | BI、FL |
| AC-IC-09-11 | audit_log 稽核列 | AT-IC-09-11-1 | AT-IC-09-11-E-1 | BI |

#### FR-IC-10　待您決定按鈕（階段二；PRD §7） — 5 條 AC、US-IC-10

| AC | 重點 | 正向 AT | 反向 AT | 載具 |
|---|---|---|---|---|
| AC-IC-10-1 | 「決定」按鈕與快照 | AT-IC-10-1-1 | AT-IC-10-1-E-1 | FV |
| AC-IC-10-2 | 「關閉並裁決」按鈕 | AT-IC-10-2-1 | AT-IC-10-2-E-1 | FV |
| AC-IC-10-3 | 寫入面靜態掃描 | AT-IC-10-3-1、AT-IC-10-3-2 | AT-IC-10-3-E-1 | FS、BS |
| AC-IC-10-4 | 不做樂觀移動 | AT-IC-10-4-1 | AT-IC-10-4-E-1 | FV |
| AC-IC-10-5 | 非 ADMIN 無按鈕 | AT-IC-10-5-1 | AT-IC-10-5-E-1 | FV |

#### FR-IC-11　導覽接入（PRD §6.6） — 3 條 AC、US-IC-11

| AC | 重點 | 正向 AT | 反向 AT | 載具 |
|---|---|---|---|---|
| AC-IC-11-1 | 登記表恰八項與順序 | AT-IC-11-1-1 | AT-IC-11-1-E-1 | FN |
| AC-IC-11-2 | 既有導覽測試只改釘值（審查核對） | AT-IC-11-2-1 | AT-IC-11-2-E-1 | GT |
| AC-IC-11-3 | href、match、ToolsRegion 不改 | AT-IC-11-3-1 | AT-IC-11-3-E-1 | FN、GT |

#### FR-IC-12　非功能（PRD §10） — 5 條 AC、US-IC-12

| AC | 重點 | 正向 AT | 反向 AT | 載具 |
|---|---|---|---|---|
| AC-IC-12-1 | 效能（真帳本與合成規模） | AT-IC-12-1-1、AT-IC-12-1-2 | AT-IC-12-1-E-1 | RI |
| AC-IC-12-2 | 跨平台 UTF-8、LF、中文 argv | AT-IC-12-2-1 | AT-IC-12-2-E-1 | RI |
| AC-IC-12-3 | 不快取 | AT-IC-12-3-1、AT-IC-12-3-2 | AT-IC-12-3-E-1 | BI、BR、FV |
| AC-IC-12-4 | 既有測試不回歸（審查核對） | AT-IC-12-4-1 | AT-IC-12-4-E-1 | GT |
| AC-IC-12-5 | 鍵盤可及 | AT-IC-12-5-1、AT-IC-12-5-2 | AT-IC-12-5-E-1 | FV、E2、FP |

## 2. 可自動化 AT 格式規範

**編號與命名**：AT 編號 `AT-IC-<FR>-<AC>-<n>`（正向）、`AT-IC-<FR>-<AC>-E-<n>`（反向），`<FR>`、`<AC>` 取 PRD AC 編號的兩段（`AC-IC-01-10`→`AT-IC-01-10-1`）；`n` 為 1～9。測試函式或標題一律以 AT 編號的底線形開頭：

| 載具 | 命名 | 例 |
|---|---|---|
| 根層 unittest | `test_AT_IC_<FR>_<AC>_<n>_<slug>`、`test_AT_IC_<FR>_<AC>_E_<n>_<slug>`（slug 為 ASCII 蛇形）；**不得以 `test_AT_3`、`test_AT_2` 開頭**（`test_selfimproving_p3_meta.py:389` 與 p2_meta 的錨定鎖會把數字前綴當自己的） | `test_AT_IC_01_2_1_unmapped_values_fail_loud` |
| Bridge pytest | 同根層（函式名以 `test_AT_IC_…` 起頭） | `test_AT_IC_07_2_E_1_hygiene_rejects_before_spawn` |
| backend JUnit 5 | `AT_IC_<FR>_<AC>_<n>_<camelSlug>`（沿 `AT_950_8_2_…` 先例） | `AT_IC_09_3_1_invalidBodiesAre422WithAllViolations` |
| frontend vitest | `it('AT_IC_<FR>_<AC>_<n> <中文描述>', …)`（標題以底線形開頭，沿 `AT_932_6_1 …` 先例） | `it('AT_IC_11_1_1 登記表恰八項…', …)` |
| Playwright | `test('AT_IC_12_5_2 <描述>', …)` | |

**判定指令樣板**（`<id>` 為 AT 編號的底線形，例 `AT_IC_01_2_1`；一律在該載具的工作目錄執行；rc 先存變數再讀，見 SCG-4 通過標準）：

- 根層：`python -m unittest discover -s tools/tests -p "<檔>" -k <id>_`
- Bridge：`python -m pytest tests/test_si_issues.py -k <id>_ -q -p no:xdist -o addopts=`
- backend：`.\gradlew.bat test --tests "*<類別>.<id>_*"`
- frontend：`npx vitest run <檔> -t "<id>"`；Playwright：`npx playwright test <檔> -g "<id>"`

**零測試視為失敗**：`Ran 0 tests`、`no tests ran`、`No test files found`、Gradle `No tests found` 一律 FAIL（`-k` 無命中＝該 AT 未實作）。

**AT 區塊樣式（P3 TCS 的 Gherkin 區塊壓縮成表列，三項後設資料由載具代碼與樣板推得）**

```
# AT-IC-01-2-1                         # 對應 AC: AC-IC-01-2（PRD §4.6；R-IC-06、R-IC-07）
# 測試類型: Integration                # 自動化工具: unittest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m unittest discover -s tools/tests -p "test_selfimproving_issues.py" -k AT_IC_01_2_1_
Given 三個表外值（提案 state＝zombie 由注入縫 S1 構造、觀察處置 later、缺陷狀態欄無關鍵字）
When  建議題並匯出
Then  三議題 status 皆為「未歸類：<原值>」；problems 三筆 UNMAPPED；summary.unmapped＝3；rc 0
```

**根層測試檔規則**（兩支新檔 `test_selfimproving_issues.py`、`test_selfimproving_issuemap.py`；既有 `test_selfimproving_export_status.py` 擴充同規則）：

1. 每個 `TestCase` 類別的 docstring **第一句**指名受測模組路徑（`tools/lib/selfimproving/issues.py`、`tools/lib/selfimproving/issuemap.py`；分桶棘輪判準）；`test_selfimproving_export_status.py` 內另開新類別 `TestIssuesExport`（docstring 指名 `issues.py`）承載 RX 的 AT。
2. 每行顯示寬度 ≤ 100（CJK 算 2）；以 `ruff check --isolated --select E501 --line-length 100 --output-format concise <新檔>` 驗新長行 0（G-R7）。
3. 假 DEF 編號一律 `DEF-999-nnn`（999 族為合成測試保留；測試碼用本檔自備的 `def999(n)`，見 §5.1）或中性字串；假 OBS 編號不得寫成 `OBS-SI-` 接數字（R18 掃全 repo），一律由夾具函式依序產生；真 ID 只准 PRD 與 TCS 已引的（`OBS-SI-001`、`PROP-SI-004` 等）。
4. 不得出現「測試摘要字樣＋4 位數字」同行；不新增守衛碼、不改 `.claude/**`、不改 `settings*.json`。
5. 夾具建構函式放 `test_selfimproving_issues.py` 模組層（D-R11）；既有 `_selfimproving_*_fixtures.py` 只讀取用。

**突變規格**：每個 R 條文在 R 條文表的「突變」欄有至少一個會使所列 AT 轉紅的最小改動。QA 在 `git archive <HEAD>` 匯出到暫存目錄的副本上逐一套用（**不在工作樹套用**、不用 `git checkout --` 還原），各跑所列 AT 的判定指令，須見轉紅（rc≠0 且至少一個 AT 失敗）；回報「突變 R-IC-nn：killed／survived」。倖存者＝該 R 條文缺鑑別力，須補 AT（補在 §3 並勘誤）。

## 3. AT 完整清單

### 3.1 載具代碼與判定指令（每個 AT 的「載具」欄；判定指令樣板見 §2）

| 代碼 | 載具 | 檔案 | 判定指令樣板 | 持有面 | AT 數 |
|---|---|---|---|---|---|
| RI | 根層 unittest | `tools/tests/test_selfimproving_issues.py`（新） | `python -m unittest discover -s tools/tests -p "test_selfimproving_issues.py" -k {id}_` | 根層 | 104 |
| RM | 根層 unittest | `tools/tests/test_selfimproving_issuemap.py`（新） | `python -m unittest discover -s tools/tests -p "test_selfimproving_issuemap.py" -k {id}_` | 根層 | 7 |
| RX | 根層 unittest | `tools/tests/test_selfimproving_export_status.py`（既有，擴充） | `python -m unittest discover -s tools/tests -p "test_selfimproving_export_status.py" -k {id}_` | 根層 | 4 |
| BR | Bridge pytest | `AgentConsole/engine-bridge/tests/test_si_issues.py`（新） | `python -m pytest tests/test_si_issues.py -k {id}_ -q -p no:xdist -o addopts=` | Console | 8 |
| BU | backend JUnit 5 | `…/adapter/out/bridge/BridgeHttpAdapterSiTest.java`（既有，擴充） | `.\gradlew.bat test --tests "*BridgeHttpAdapterSiTest.{id}_*"` | Console | 1 |
| BI | backend JUnit 5（IT） | `…/adapter/in/web/IssueApiIT.java`（新） | `.\gradlew.bat test --tests "*IssueApiIT.{id}_*"` | Console | 26 |
| BM | backend JUnit 5（IT） | `…/infrastructure/persistence/IssuePriorityMigrationIT.java`（新） | `.\gradlew.bat test --tests "*IssuePriorityMigrationIT.{id}_*"` | Console | 2 |
| BA | backend JUnit 5（ArchUnit） | `…/architecture/IssuePriorityArchTest.java`（新） | `.\gradlew.bat test --tests "*IssuePriorityArchTest.{id}_*"` | Console | 2 |
| BB | backend JUnit 5（ArchUnit） | `…/architecture/IssueBridgeArchTest.java`（新） | `.\gradlew.bat test --tests "*IssueBridgeArchTest.{id}_*"` | Console | 2 |
| BC | backend JUnit 5 | `…/architecture/IssueReasonsContractTest.java`（新） | `.\gradlew.bat test --tests "*IssueReasonsContractTest.{id}_*"` | Console | 1 |
| BS | backend JUnit 5 | `…/architecture/IssueStaticLockTest.java`（新） | `.\gradlew.bat test --tests "*IssueStaticLockTest.{id}_*"` | Console | 3 |
| FL | frontend vitest | `lib/domain/issues.test.ts`（新） | `npx vitest run lib/domain/issues.test.ts -t "{id}"` | Console | 7 |
| FV | frontend vitest | `components/domain/issues/IssuesView.test.tsx`（新） | `npx vitest run components/domain/issues/IssuesView.test.tsx -t "{id}"` | Console | 28 |
| FD | frontend vitest | `components/domain/issues/IssueDetail.test.tsx`（新） | `npx vitest run components/domain/issues/IssueDetail.test.tsx -t "{id}"` | Console | 3 |
| FP | frontend vitest | `components/domain/issues/IssuePriorityDialog.test.tsx`（新） | `npx vitest run components/domain/issues/IssuePriorityDialog.test.tsx -t "{id}"` | Console | 3 |
| FG | frontend vitest | `components/domain/issues/IssueLegend.test.tsx`（新） | `npx vitest run components/domain/issues/IssueLegend.test.tsx -t "{id}"` | Console | 2 |
| FS | frontend vitest（靜態） | `components/domain/issues/issues.static.test.ts`（新） | `npx vitest run components/domain/issues/issues.static.test.ts -t "{id}"` | Console | 6 |
| FN | frontend vitest | `lib/nav/issues-nav.test.ts`（新） | `npx vitest run lib/nav/issues-nav.test.ts -t "{id}"` | Console | 3 |
| E2 | Playwright（mock API） | `tests/e2e/issues.mock.spec.ts`（新） | `npx playwright test tests/e2e/issues.mock.spec.ts -g "{id}"` | Console | 1 |
| ES | Playwright（Docker 全棧；SCG-5 實機證據，非每 commit 閘） | `tests/e2e/issues-docker.stack.ts`（新） | `npx playwright test -c tests/e2e/docker.config.ts -g "{id}"（須先依 docker.config.ts 啟全棧）` | Console | 2 |
| GT | 審查閘（指令型 AT，不入單元測試） | SCG-4 通過標準的 G 編號指令 | `見該 AT 的 Then 欄所指 G 編號` | 共同 | 8 |

### 3.2 AT 清單（依 FR；每列＝一個 AT）

Given（夾具）與 Then（判定）；R 條文對應見 R 條文表的 AT 欄與 §6 RTM。夾具名詞（S1～S5、N01～N19、§5.5 範例表）定義於 §5。

#### FR-IC-01 的 AT　對照表封閉、唯一歸類、fail-loud（PRD §4）

| AT | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|
| AT-IC-01-1-1 | RM | 真上游：`events.PROP_STATES`、`KINDS`、`DKINDS`、`ROUTES`、`rows.CATEGORIES`、`SEVERITIES`、`defs` 狀態標籤五個 | `issuemap.closure_problems()` 回空；每個機器值（含條件欄每種取值）恰一個歸類；表內沒有可鎖集合以外的鍵（缺陷嚴重度見 01-4） |
| AT-IC-01-1-2 | RM | 八個探針 `open`、`deferred`、`retired`、`decided`、`fixed@abc1234`、`DEF-1-1`、`merged@OBS-SI-001`、`proposed@PROP-SI-001`，另 `later`、`closed` | 逐一餵 `rows.disp_token` 各辨識為對應鍵（`fixed@`、`merged@`、`proposed@`、`DEF-` 以前綴為鍵）；`later`、`closed` 回 `None`；`DISP_TOKEN_RE.pattern` 第一個捕捉群組分支數＝8 |
| AT-IC-01-1-E-1 | RM | 合成上游（`closure_problems(upstream=…)` 注入）：`PROP_STATES` 加 zombie、`KINDS` 加 foo、`DKINDS` 加 bar、`CATEGORIES` 加 ux、處置探針加第 9 分支、defs 標籤加 stale | 六種變體各使鎖回報「上游有而表無」且點名該值；對照組（真上游）回空 |
| AT-IC-01-1-E-2 | RM | 合成對照表：刪一鍵（`promoted`）、多一鍵（`ghost`） | 分別回報「表缺」「表多」（雙向各一），訊息點名該鍵 |
| AT-IC-01-2-1 | RI | 三個表外值：提案 state 為 zombie（注入縫 S1，見 §5.2）、觀察處置 later、缺陷狀態欄無可辨識關鍵字 | 三議題 `status` 皆為「未歸類：<原值>」；`problems` 三筆 `UNMAPPED`（subject＝議題 ID、detail 形如「狀態：zombie」）；`summary.unmapped`＝3；只出現在無 `status` 篩選的結果；rc 0 |
| AT-IC-01-2-E-1 | RI | 同夾具另加候選、待解、已完成各一合法議題 | 合法議題歸類與無表外值夾具逐值相同（不受牽連）；`--status 待處理` 的結果不含三個未歸類議題 |
| AT-IC-01-3-1 | RI | 終態表驅動：觀察六終值（`fixed@`、`decided`、`retired`、`merged@`、`DEF-`、`proposed@`）、缺陷三終類（fixed、wontfix、closed-by-decision）、提案 rejected、handed-off、closed×3（clean、rolled-back、recurred 且 app.rollback 已消耗） | `status` 皆為已完成，`result` 依序為已修復、已裁決、已退役、已合併、已轉交、已轉交；已修復、已否決、已裁決；已否決、已轉交；已採納、已回滾、已回滾 |
| AT-IC-01-3-2 | RI | 候選、待您決定、待解、進行中、觀察中、延後各一議題 | `result` 全為 `null` |
| AT-IC-01-3-E-1 | RI | closed 提案而生效量測結果量不到（注入縫 S2：`effective_windows` 回 []；另一例窗換成 pending；再一例同注入但已有 `dec(rollback)` 與 `app.rollback`） | 前二例：`status`＝已完成、`result`＝「未歸類：closed」、`problems` 一筆 `UNMAPPED`（detail「結果：closed」）、不進待您決定與進行中；第三例：`result`＝已回滾、無 `UNMAPPED`（已回滾先於量不到，R-IC-19） |
| AT-IC-01-4-1 | RM | 觀察 P1～P4、缺陷 P0～P4（含「**P1** 說明」「 P2（後綴）」的開頭空白與強調記號） | 嚴重度函式回：P0、P1→(緊急,1)；P2→(高,2)；P3→(中,3)；P4→(低,4)；後綴說明不影響；開頭只略過空白、`*`、`_` |
| AT-IC-01-4-2 | RM | 真缺陷主檔 `AutoSDD_Defect_Log.md` 的嚴重度欄首碼集合（唯讀） | 集合 ⊆ `DEF_SEVERITIES`（P0～P4） |
| AT-IC-01-4-3 | RI | 提案 `sources` 含 P3、P2 的觀察與 P0 的缺陷 | 提案 `severity`＝緊急、`severity_rank`＝1（取最嚴重者） |
| AT-IC-01-4-E-1 | RI | 缺陷嚴重度欄為「—（流程紀錄）」「P5」「P10」 | `severity` 為「未歸類：<原值>」、`severity_rank` 為 `null`、各一筆 `UNMAPPED`（detail「嚴重度：…」） |
| AT-IC-01-4-E-2 | RI | 提案 `sources` 全查不到（來源項目都不存在） | `severity`、`severity_rank` 為 `null`；`ne` 一筆 `SEVERITY-UNAVAILABLE`（field `issues.<PROP>.severity`）；顯示「—」不補成低 |
| AT-IC-01-5-1 | RI | 任一清單回應（含空帳本夾具） | `legend` 恰 7 statuses、8 results、4 sources、4 severities（rank 1～4）、5 problem_codes、9 ne_reasons，每項 meaning 非空；`statuses[].tab` 同 PRD §4.1（候選、延後為 null）；`sources` 依順位；`unmapped_label`＝「未歸類」；`updated_at_note` 含「最後已知動靜」 |
| AT-IC-01-5-E-1 | RX | `export --kind issues --id <ID>` 單筆 | 回應沒有 `legend`、`summary` 鍵；清單回應的 `legend` 與 `issues --json` 的逐值相同 |
| AT-IC-01-6-1 | RI | 三個觀察列各有一個表外處置值（兩個同為 later、一個為 soon） | `problems` 恰三筆 `UNMAPPED`（subject 各為其議題 ID）、不合併不彙總；三者 `status` 皆顯示「未歸類：<原值>」（later、later、soon） |
| AT-IC-01-6-E-1 | RI | 同上夾具 | `summary.unmapped`＝3 且 `total`＝七狀態件數和＋`unmapped`；`problems` 長度為 3（不是 2） |
| AT-IC-01-7-1 | RI | 探針夾具逐一觸發五個 problems 碼與九個 ne 理由（含無 git 的夾具觸發 `git-unavailable`：夾具不是 git repo；另一例 `PATH` 無 git） | 實際產出的碼與理由 ⊆ `issuemap` 表，且各有非空中文；無 git 兩例 `head_sha`＝null、其餘議題照常、rc 0 |
| AT-IC-01-7-2 | RM | 通道、時間線動作、決定動詞三本字典 | 通道鍵恰為 `events.ROUTES` 的 `handoff:` 後綴（DEF、R、T1、PRD）；動作鍵恰為 `events.KINDS`（21）、決定動詞恰為 `events.DKINDS`（9）；中文非空且互異 |
| AT-IC-01-7-E-1 | RI | 表 ⊆ 產出：夾具清單覆蓋表中每個碼與理由；合成表多一碼（無夾具）、產出多一碼（patch 產出 `FOO`） | 表中每項至少被一個夾具觸發；兩種合成變體各使自證測試轉紅 |
| AT-IC-01-8-1 | RI | 觀察主檔缺檔夾具 | 觀察議題整批缺席；`ne` 恰多一筆 `OBS-LEDGER-UNAVAILABLE`（field `ledger.observation`）；其餘帳本議題照常；rc 0；`by_tab` 三格皆 `null` |
| AT-IC-01-8-2 | RI | 缺陷主檔缺檔夾具 | `ne` 恰多一筆 `DEFECT-LEDGER-UNAVAILABLE`；`by_tab` 待處理、已完成為 `null`、待您決定非 `null`；其餘議題照常 |
| AT-IC-01-8-3 | RI | 姊妹軌兩檔之一缺檔夾具 | `ne` 恰多一筆 `SIBLING-LEDGER-UNAVAILABLE`（field `ledger.sibling.<檔名>`）；`by_tab` 同缺陷主檔缺檔 |
| AT-IC-01-8-4 | RI | 事件帳本缺檔夾具 | `ne` 恰多一筆 `EVENT-LEDGER-UNAVAILABLE`，不再另報 `carrier-not-established`；提案整批缺席；`by_tab` 三格皆 `null` |
| AT-IC-01-8-E-1 | RI | 四本帳各改為同名目錄（不可讀）；另有觀察歸檔檔不可讀 | 同樣只多對應的一筆 `ne`、rc 0；僅一本缺時其餘三種理由都不出現（不連坐）；歸檔檔不可讀＝`OBS-LEDGER-UNAVAILABLE`（field `ledger.observation.<檔名>`）、主檔議題照常 |
| AT-IC-01-8-E-2 | RI | 缺陷主檔存在但表頭被破壞（無「ID」「狀態」欄名的表頭）；姊妹軌存在但無 `DEF-ID` 表頭（D-R13） | 視同不可用：`ne` 各一筆 `DEFECT-LEDGER-UNAVAILABLE`、`SIBLING-LEDGER-UNAVAILABLE`；不得回「0 件」；`by_tab` 對應格為 `null` |
| AT-IC-01-9-1 | RI | 事件帳本含一行非 JSON 文字（行 3）與一筆缺 `seq` 的 JSON 物件（行 5），其餘合法 | `problems`：`EVENT-PARSE` 一筆（subject `L3`）、`EVENT-UNSOUND` 一筆（subject `L5`）；其餘提案照常；rc 0 |
| AT-IC-01-9-E-1 | RI | 兩筆不合格事件、一個空白行、檔尾單一換行 | 兩筆 `EVENT-UNSOUND`（一筆一事件、不合併）、空白行一筆 `EVENT-PARSE`、檔尾換行不計；不合格事件不進折疊（其所指提案狀態不受影響） |
| AT-IC-01-10-1 | RI | 表外處置值為 100 個 code point（含全形字與表情符號）的觀察列 | 顯示「未歸類：」加原值前 80 個 code point 再加「…」（「…」不計入）；`problems.detail` 的原值逐字完整、不截；計一筆 `UNMAPPED` |
| AT-IC-01-10-E-1 | RI | 恰 80 與恰 81 個 code point 的表外值（含代理對字元）；另一組以組合附加符號（U+0301）構成的 80 與 81 個 code point 值 | 80 者不加「…」、81 者加；以 code point（非 UTF-16 單元、非字素叢集）計，組合附加符號各算 1；代理對不被截成孤立代理；四者各一筆 `UNMAPPED` |
| AT-IC-01-11-1 | RI | 觀察帳本缺檔而事件帳本在，提案來源項目含觀察號 | 該提案 `source`、`severity` 為 `null`，僅由同一筆 `OBS-LEDGER-UNAVAILABLE` 說明（無逐項 `ne`）；不計 `UNMAPPED` |
| AT-IC-01-11-2 | RI | 事件帳本缺檔而觀察列 open、需 attr 判定 | 該列暫列候選，由 `EVENT-LEDGER-UNAVAILABLE` 明說 |
| AT-IC-01-11-E-1 | RI | 對照例：來源項目只有 DEF 號的提案（觀察帳本缺檔）；decision 類與路徑 B 的 open 觀察列（事件帳本缺檔） | 前者仍照常判為系統缺陷；後者仍為待您決定、待解（不受事件帳本缺檔影響） |

#### FR-IC-02 的 AT　來源判定（PRD §2）

| AT | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|
| AT-IC-02-1-1 | RI | 觀察列標記含 `carrier=console`（另一例 `來源=人`）且分類 bug | `source`＝使用者提案（優先於系統缺陷） |
| AT-IC-02-1-E-1 | RI | 標記只有 `來源=代理` 的 bug 列 | `source`＝系統缺陷（不是使用者提案） |
| AT-IC-02-2-1 | RI | 標記含 `回報者=研究者`、分類 tooling、來源非人 | `source`＝研究提案 |
| AT-IC-02-2-E-1 | RI | 回報者為研究者但分類 bug | `source`＝系統缺陷（順位在研究提案之前） |
| AT-IC-02-2-E-2 | RI | 標記 `回報者=研究員`（PRD 階段的研究代理）且分類 doc | `source`＝系統改善（全等比對，不是子字串） |
| AT-IC-02-3-1 | RI | 缺陷帳本任一列；觀察列分類 bug（來源非人，含研究者回報的） | `source`＝系統缺陷 |
| AT-IC-02-3-E-1 | RI | 分類 tooling 的觀察列 | `source`＝系統改善（不是系統缺陷） |
| AT-IC-02-4-1 | RI | 觀察列分類 process、tooling、doc 或 decision（來源非人、非研究者） | `source`＝系統改善 |
| AT-IC-02-4-E-1 | RI | 分類 bug 的觀察列 | `source`＝系統缺陷（不是系統改善） |
| AT-IC-02-5-1 | RI | 提案 `sources` 含使用者提案觀察與缺陷；另一提案含研究提案觀察與 DEF 號 | 前者＝使用者提案；後者＝系統缺陷（取順位最前者） |
| AT-IC-02-5-E-1 | RI | `sources` 內有查不到的觀察（略過）；另一提案 `sources` 全查不到 | 前者依其餘來源判定；後者 `source`＝「未歸類：<ID1>、<ID2>」（依 sources 次序、以「、」相接）且 `problems` 一值一筆（detail「來源：…」） |

#### FR-IC-03 的 AT　成為正式議題（PRD §3）

| AT | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|
| AT-IC-03-1-1 | RI | 觀察列 open、分類 bug、來源代理、無任何 attr | `status`＝候選；不在待處理與待您決定；`rankable`＝false |
| AT-IC-03-1-E-1 | RI | 同夾具 | 候選不計入 `summary.by_tab` 三格（`by_status.候選` 加 1）；`--status 待處理`、`--status 待您決定` 皆不含它 |
| AT-IC-03-2-1 | RI | 同列另有 attr（type root 的 `obs` 含該列；另一例 type link 的 `from` 為該列）且 `attr.confirm` 已入帳 | `status`＝待解 |
| AT-IC-03-2-E-1 | RI | attr 未確認；attr 被 `attr.reject`；確認者等於提出者（`CONFIRMER-IS-PROPOSER`） | 前二者仍為候選；第三者不改變判定（仍待解） |
| AT-IC-03-3-1 | RI | open 且標記含 `carrier=console`（另一例 `來源=人`）、分類 process | `status`＝待解（不需 attr） |
| AT-IC-03-3-2 | RI | 分類 decision 的 open 列（來源代理、無 attr；另一例路徑 B） | `status`＝待您決定、`action`＝close-observation、`rankable`＝true（不論路徑） |
| AT-IC-03-3-E-1 | RI | 分類 process、來源代理、無 attr、無路徑 B 標記 | `status`＝候選（不因「像改善」而成立） |
| AT-IC-03-4-1 | RI | 終值（六種）與 deferred 的觀察列；缺陷 open；提案 proposed | 觀察列永不為候選；缺陷 open＝待解；提案 proposed＝待您決定（不經候選） |
| AT-IC-03-4-E-1 | RI | deferred 觀察列且路徑 A、B 皆成立 | 仍為延後（不因成立而變待解） |
| AT-IC-03-5-1 | RI | `HOME`、`USERPROFILE`、`AUTOSDD_SI_DIR` 指向 tmp 家目錄，其下 `console_audit/<uuid>.json` 放一份合法稽核檔 | 議題清單不含它；`issues` 與 `export` 不讀家目錄（patch `Path.home` 為拋例外仍 rc 0） |
| AT-IC-03-5-E-1 | RI | 稽核檔入帳後（帳本出現 `carrier=console` 的觀察列） | 該列成為議題（來源使用者提案）；入帳前後差異只來自帳本 |
| AT-IC-03-6-1 | RI | 已成立（路徑 A、B）的 process、tooling、doc 觀察列 open | `status`＝待解、`action`＝null、不在待您決定 |
| AT-IC-03-6-E-1 | RI | 全狀態夾具 | 狀態為待您決定的成員恰為四類（提案 proposed、verified、復發待回滾的 closed、decision 的 open 觀察列）；雙向：四類成員皆在、無其他成員 |
| AT-IC-03-7-1 | RI | 五提案皆 `promoted(R)` 起（n＝PROP 號）：①`mea_chain(R,P,'recurred')`；②`mea_chain(R,P,'clean')`（另一例 'recurred'）＋`fx.dec_ev(n,'rollback')`；③'recurred'＋`dec_ev`＋`fx.rollback_ev(n)`；④'clean'；⑤只 `promoted(R)`＋`dec_ev`（另一例 `mea_chain(R,P,'recurred',stop_at='open')`＝measuring） | ①待您決定（`rankable`＝true、next_step「量測窗內復發，等您決定是否回滾（目前只有「回滾」動詞）」）；②⑤進行中（「已決定回滾，等執行回滾」）；③已完成、已回滾；④已完成、已採納 |
| AT-IC-03-7-2 | RI | 同上夾具（合法事件鏈）另建 `mea.build_ctx` 的 ctx | `meaplan.rollback_pending(ctx)` 的集合與 issues 中「closed 提案且待您決定」的 ID 集合逐值相同（差分；含多提案夾具；僅限合法事件鏈） |
| AT-IC-03-7-E-1 | RI | 非法的 `dec(rollback)`（seq 早於 `app.promote`，fold 記 TRANSITION-ILLEGAL） | 不算已決定（D-R3）：closed、recurred 的提案仍為待您決定；此情形與 `meaplan.rollback_pending`（不判事件合法性）刻意不同，故 AT-IC-03-7-2 的差分只限合法事件鏈 |

#### FR-IC-04 的 AT　下一步與欄位（PRD §5）

| AT | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|
| AT-IC-04-1-1 | RI | PRD §5.2 十九情境各一夾具（§5.3 的 N01～N19） | `next_step` 恰為該列句型（含代入值）、非空、≤80 code point、不含英文詞（§5.4；先剔除議題 ID 形態；通道已中文化；延後列方括號內原文只驗截 40）；verified 句型不預設驗證結果 |
| AT-IC-04-1-E-1 | RI | 英文詞偵測器負控：合成字串含 open、fixed@abc、measuring、closed-by-decision、handed-off；另含 PROP-SI-004、DEF-999-001、中文通道名 | 前五者逐一被抓、後者不誤抓；邊界依「前後字元不屬英數與 `-`」判 |
| AT-IC-04-1-E-2 | RI | 延後列帳本原文含英文片段；另一列處置附加文字為空 | 方括號內節錄原樣保留且截 40 code point、其餘句型仍過英文詞檢查；空節錄＝「等再開症狀出現：（帳本未寫明）」 |
| AT-IC-04-2-1 | RI | measuring 提案；`status.measure_value` 回該窗 `n_opp`＝0、該提案 `mea.open` 的 `w_opp`＝5 | `next_step` 含「量測窗 0／5」 |
| AT-IC-04-2-E-1 | RI | `measure_value` 為 NOT-EVALUABLE（注入縫 S5）或查無該窗 | `next_step`＝「量測窗進度量不到」；`ne` 一筆 `MEASURE-UNAVAILABLE`（field `issues.<PROP>.next_step`）；不顯示 0／5 |
| AT-IC-04-2-E-2 | RI | `issues.py` 原始碼靜態鎖 | 不含識別字 `window_rows`（AST 與字面皆無） |
| AT-IC-04-3-1 | RI | 症狀含 markdown 記號（`**`、`__`、`~~`、反引號）、轉義的 `\|`、`<script>`，且超過 80 code point（含全形與表情符號）的觀察列 | `title` 去記號、空白折疊、取前 80 個 code point 再加「…」（「…」不計入）；`<script>` 與轉義的 `\|` 保留為純文字、JSON 轉義正確；原文在 `raw`（單筆） |
| AT-IC-04-3-2 | RI | updated_at 夾具：A 時間欄「2026-10-18 22:47～10-19 02:20」無 obs.close；B 起日 2026-10-18 另有日期 2026-10-20 的 obs.close；C 時間欄「2026-10-18 23:30 +08:00」；缺陷；提案（最後事件 `t`＝「2026-10-18T23:30:00+08:00」） | A＝2026-10-18；B＝2026-10-20；C＝2026-10-18；缺陷＝發現日期；提案＝最後事件（last_seq）日期 2026-10-18；日期部分直取、不換算時區 |
| AT-IC-04-3-E-1 | RI | 時間欄解不出；obs.close 日期早於起日 | 前者 `updated_at`＝null 並列 `ne` `TIME-UNPARSEABLE`（field `issues.<ID>.updated_at`）；後者取起日（取較晚者） |
| AT-IC-04-4-1 | RI | 提案 `sources` 含某觀察；觀察處置為 `DEF-`（該 DEF 是議題）、`merged@`、`proposed@` | 提案與來源、處置指向者雙向互含（去重、依 ID 排序） |
| AT-IC-04-4-2 | RI | 觀察標記 `rel=corrects:<ID>`、`rel=recurs:<ID>`；attr link 的 `from`→`reopens` | 單向：只有起點含目標、目標不回列 |
| AT-IC-04-4-E-1 | RI | 處置指向主檔以外 DEF；雙向類與單向類性質檢查 | 指向主檔以外 DEF 仍列入該觀察的 `links`；雙向類兩端皆議題時 A∈links(B)⇔B∈links(A)；單向類不對稱 |
| AT-IC-04-5-1 | RI | 觀察處置「deferred；再開症狀：X」；缺陷 ID 列在姊妹軌表（合成夾具） | 狀態＝延後；`next_step` 含 X；缺陷者含「解鎖條件」原文與「（最近複查 <日期>）」 |
| AT-IC-04-5-E-1 | RI | 姊妹軌 DEF-ID 在主檔找不到 | 仍成議題：`source` 系統缺陷、延後、`title`「（主帳本列已歸檔）」、`severity` null 並列 `ne` `SEVERITY-UNAVAILABLE`、不進 `problems` |
| AT-IC-04-5-E-2 | RI | 姊妹軌欄數與表頭不符的列；「格式定義」節的兩欄表；兩姊妹軌重複 ID | 欄數不符者不採用並 `ROW-ARITY`（subject `<檔名>:L<行號>`）；格式定義表不是資料表；重複者後者 `ID-DUP` |
| AT-IC-04-6-1 | RX | 存在的議題 `export --kind issues --id <ID>` | `items` 恰一筆，含 `raw`（標籤為帳本表頭或 PRD §5.1 所列中文）與 `timeline`（seq 升冪、action 為中文） |
| AT-IC-04-6-E-1 | RX | 清單回應；查無的 ID | 清單項目不含 `raw`、`timeline`、`priority`；單筆回應無 `legend`、`summary`；查無 ID＝`items` 空、rc 0 |
| AT-IC-04-7-1 | RI | 兩提案：一筆卡面可建、一筆不可建（注入縫 S4：`card.build` 對它拋 `CardError`） | 前者 `title`＝卡面〈一、症狀〉；後者 `title`＝「（提案 <ID>：卡面量不到）」並列 `ne` `CARD-UNAVAILABLE`（field `issues.<ID>.title`） |
| AT-IC-04-7-E-1 | RI | 同夾具 | 卡面量不到不影響其他議題；單筆 `raw` 省略提案卡項、保留狀態等原值；`problems` 不增 |
| AT-IC-04-8-1 | RI | 觀察主檔、缺陷主檔各一列、一筆提案 | `origin.line` 為該列在檔內 1 起算行號（缺陷＝`DefRow.lineno`）；提案 `origin.seq`＝`prop` 事件的 `created_seq`；`origin.file` 為 repo 相對 POSIX 路徑 |
| AT-IC-04-8-E-1 | RI | Windows 夾具（觀察、缺陷（含姊妹軌）、事件三本帳皆改寫為 CRLF 行尾並前置 UTF-8 BOM）；歸檔觀察列；姊妹軌孤列 | 與 LF 版逐值相同（含 `origin.line`）；`origin.file` 不含反斜線；歸檔列的 file 為該歸檔檔、line 為歸檔檔內行號；孤列 file 為姊妹軌檔 |
| AT-IC-04-9-1 | RI | 欄數不符的觀察列、ID 欄不合 `OBS-SI-NNN` 的觀察列（小寫 `obs-si-001`、兩位數字的觀察 ID 各一列）、欄數不符的缺陷列、重複 ID 的觀察列與缺陷列 | 前三類（含兩種近似 ID 各一列）的每一列都不成議題並各一筆 `ROW-ARITY`；重複的後列不收並計 `ID-DUP`；其餘議題照常；rc 0 |
| AT-IC-04-9-E-1 | RI | 以不同 since、limit、status 取數頁 | 各頁 `problems` 與 `ne` 逐值相同（整本帳一份、不受篩選影響） |
| AT-IC-04-10-1 | RI | 七狀態各一議題（含 proposed、verified、復發待回滾 closed、decision 的 open 觀察） | `rankable` 只有待您決定、待解、進行中為真；`action`：待您決定的提案（含復發待回滾）＝decide-proposal、待您決定的觀察＝close-observation、其餘 null |
| AT-IC-04-10-E-1 | RI | 未歸類議題；觀察中、延後、候選、已完成各一 | `rankable`＝false、`action`＝null |
| AT-IC-04-11-1 | RI | 夾具使 `attr*`、`prop`、`obs.*`、`card`、`dec`（各決定動詞，resume 除外）、`heldout.freeze`、`app.*`、`mea.*`、`run.open`／`run.close` 各見於某議題 | `export --id` 的 timeline `action` 全為中文；`dec` 顯示「決定：<動詞中文>」；seq 升冪 |
| AT-IC-04-11-E-1 | RI | 表外動作與動詞（注入縫 S3：事件含 `zombie.act`、`dkind`＝zombie）；`research.*` 與 `resume` 事件 | 表外者顯示「未歸類：<原值>」並計 `UNMAPPED`；`research.*`、`resume` 不掛在任何議題（timeline 不含） |

#### FR-IC-05 的 AT　排序、分頁、篩選、摘要（PRD §5.3、§5.4）

| AT | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|
| AT-IC-05-1-1 | RI | §5.5 範例表（無順位） | `sort_for_display(items, 'pending')`＝§5.5 預期序一；`'done'`＝預期序二 |
| AT-IC-05-1-2 | FL | §5.5 同一張範例表（含順位、非 rankable 卻有遺留順位者） | `sortIssues` 待處理依第一條：順位升冪（無順位最後）→severityRank→updatedAt→id；已完成與全部依第二條；無順位子集結果與 RI 預期序相同 |
| AT-IC-05-1-E-1 | RI | `updated_at` 與 `severity_rank` 為 null 的項 | 兩規則皆排最後（第一條：各鍵 null 後排；第二條：日期 null 後排） |
| AT-IC-05-1-E-2 | FL | 非 rankable 卻有遺留順位；順位相同者 | 遺留順位不參與排序（視為無順位）；同順位回到後續鍵（severityRank、updatedAt、id） |
| AT-IC-05-2-1 | RI | 議題數 30、limit 7 的夾具；以 `next_since` 迴圈取頁，同一夾具連跑兩次 | 全部取回、無重複無遺漏；非末頁 `next_since`＝本頁最後一項游標；末頁 `truncated`＝false 且 `next_since`＝null；兩次連跑的各頁項目序與 `next_since` 逐值相同（游標序確定） |
| AT-IC-05-2-E-1 | RI | `--limit 0`、`--limit 501`（超過 `export_limit_max`）、`--since -1`、`--since` 非整數；對照 `--limit 500`、`--since 0`、`--limit 1`；另 `--since` 大於最大游標 | 前四者 rc 3 且 stderr 說明；後三者 rc 0；`--since` 大於最大游標＝rc 0、`items` 空、`truncated`＝false、`next_since`＝null |
| AT-IC-05-3-1 | RI | 取第一頁後帳本新增一列觀察、一列缺陷（其 DEF 族數小於已見項）與一筆提案 | 以舊 `next_since` 續取：已見項不重現、未見項不遺漏、游標較大的新項出現 |
| AT-IC-05-3-E-1 | RI | 游標基數檢查；編號或行號 ≥ S（D-R4） | 觀察＝OBS 號、缺陷＝S＋主檔行號、提案＝2S＋PROP 號、孤列＝3S 或 4S＋行號，不重疊且附加不改既有項；≥ S 者不成議題並 `ROW-ARITY`（detail「編號或行號過大，游標無法編碼」）；`legend.problem_codes` 的 `ROW-ARITY` 釋義含「游標」 |
| AT-IC-05-4-1 | RI | 各狀態議題夾具；另含重複值「待解,待解」與成員並列值「待處理,待解」 | `--status 待處理`＝待解、進行中、觀察中的聯集；`--status 待您決定,延後` 為聯集；`--source 研究提案`；兩旗標並用取交集；重複值去重、「待處理,待解」＝「待處理」本身；篩選先於分頁（limit、next_since 取自篩選後） |
| AT-IC-05-4-E-1 | RI | 未知值；空片段「待解,,延後」；前後帶空白的值（「 待解」、「待解 」）；全形逗號「待解，延後」（比對為全等、不折疊全半形）；`export --kind issues` 的 `--id` 為小寫 `obs-si-001`、兩位數字的觀察 ID、`PROP-SI-4`、`DEF-x-y`；`--id` 併 `--status`；`--status` 配 `export --kind observations`；空字串 `--status=` | 皆 rc 3（未知值時 stderr 列合法值）；未歸類議題只在無 `--status` 時出現 |
| AT-IC-05-5-1 | RI | 任何篩選、`since`、`limit` 組合 | `summary.by_status`、`by_tab` 恆為整本帳計數；`total`＝七狀態件數和＋`unmapped` |
| AT-IC-05-5-E-1 | RI | 各組合；另含空帳本夾具（四本帳都在但為空：只有表頭、事件帳本為空 jsonl） | `by_status` 七鍵恆在（0 亦在）；`by_tab.待處理`＝待解＋進行中＋觀察中；`problems`、`ne` 同為整本帳；空帳本：`items`＝[]、`by_status` 七鍵皆 0、`by_tab` 三格為 0（不是 null）、`problems`＝[]、`legend` 在、rc 0 |
| AT-IC-05-6-1 | RI | 含全形字元的夾具、文字表（無 `--json`） | 狀態、結果、來源、嚴重度、下一步皆中文（標題與 ID 除外）；欄依顯示寬度對齊（全形算 2，沿 `card.width`）；末行「共 N 件；問題 M 筆」；被截斷時末行加「；尚有更多，--since <next_since>」；列序依 D-R6（`--status 待處理` 用第一條、無 `--status` 用第二條） |
| AT-IC-05-6-E-1 | RI | 未截斷；零件結果（同空帳本夾具）；null 欄 | 末行無「尚有更多」；零件＝「共 0 件；問題 0 筆」；null 欄顯示「—」；輸出為 LF 行尾 |
| AT-IC-05-7-1 | FV | 全部分頁含待您決定與其他狀態的列 | 待您決定的列全部置頂（先於其他列、帶 `data-testid="issue-top-pinned"` 與 `aria-label="置頂"`，其內依第一條）；其餘依第二條且無該元素；待您決定分頁每列同樣帶該元素 |
| AT-IC-05-7-E-1 | FV | 同夾具 | 置頂只改顯示序：`summary` 數字與各分頁件數不變；待處理與已完成分頁沒有該元素 |

#### FR-IC-06 的 AT　零寫入與單一真相

| AT | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|
| AT-IC-06-1-1 | RI | 乾淨工作樹；各跑 `issues`、`export --kind issues`（含 `--id` 與篩選） | 前後 `git status --porcelain` 相同；四類帳本與提案目錄位元組不變；不讀不寫家目錄 |
| AT-IC-06-1-2 | BR | Bridge GET `/si/issues` 與 `/si/issues/{id}`（`make_si_repo` 複本倉） | `repo_snapshot` 前後相同（status、HEAD、檔案雜湊）；家目錄隔離未被碰 |
| AT-IC-06-1-3 | BI | console-api GET 清單與單筆 | `MiniBridge.requests()` 全為 GET；無任何寫入呼叫 |
| AT-IC-06-1-E-1 | RI | 寫入探針：patch 寫入模式 `open`、`Path.write_text`、`write_bytes`、`mkdir`、`os.replace` 為拋例外 | `issues` 與 `export --kind issues` 仍成功（證明零寫入） |
| AT-IC-06-2-1 | RX | 同一帳本快照；各入口連跑兩次（兩次間隔 ≥1.1 秒） | `issues --json` 與 `export --kind issues` 的 `items`、`legend`、`summary` 逐值相同；同一入口兩次輸出除 `generated_at` 外逐位元相同（與牆鐘無關） |
| AT-IC-06-2-2 | RI | 靜態鎖：`issues.py`（只掃新檔；`issuemap.py` 與既有檔除外） | 不含 ≥4 個不同的 `issuemap` 狀態鍵（詞表現讀 `issuemap` 鍵集合、測試不另抄） |
| AT-IC-06-2-3 | FS | `components/domain/issues/**` 與 `lib/domain/issues.ts`（略過 `tests/` 目錄、`*.test.ts(x)`、`*.d.ts`，另明寫排除 `*.fixtures.ts`） | 同判準（詞表讀 `tests/fixtures/si/A.camel.json` 的 `issues.legend.statuses[].name`） |
| AT-IC-06-2-4 | BS | `Issue*.java` | 同判準（詞表讀 `src/test/resources/si/A.camel.json` 的 `issues.legend`） |
| AT-IC-06-2-E-1 | RI | 根層掃描器自帶負控 | 含 4 個不同狀態鍵者回非空；含 3 個者回空；同一鍵重複 4 次者回空（不同鍵才算） |
| AT-IC-06-2-E-2 | FS | 前端掃描器自帶負控；排除規則樣本：`components/domain/issues/tests/issues.fixtures.ts`（含七個狀態詞）與置於元件目錄、檔名不是 `*.fixtures.ts` 的同內容檔（例 `issues.statusWords.sample.ts`） | 同判準的違規與良性樣本各回非空、空；前者不被掃進、後者被抓 |
| AT-IC-06-2-E-3 | BS | Java 掃描器自帶負控 | 同判準的違規與良性樣本各回非空、空 |
| AT-IC-06-3-1 | RI | 功能完成 | `selfimproving.py --help` 動詞集合＝既有 23 個（逐名釘在 §5.5）加 `issues`（共 24）；`CAPABILITY` 登記 `issues.py`、`issuemap.py` 為 ro；`capability_problems` 回空 |
| AT-IC-06-3-E-1 | RI | 合成樹：issues.py 加 `open(…,'w')`、加 subprocess、加 socket；ro 模組 import rw 模組 | `capability_problems` 各回非空 |
| AT-IC-06-4-1 | RI | 真 repo 跑 `si check` | rc 0、33 項（無 FAIL），與功能前相同 |
| AT-IC-06-4-E-1 | GT | `params.json` 位元組（功能前 sha256 `fc48653b…bf197`，1994 bytes） | G-R14：`git diff --exit-code <base> -- docs/06_quality/SelfImproving_Protocol/params.json` 無差異；`issues` 只用既有鍵（`export_limit_max`、`MEASURE_KEYS`） |
| AT-IC-06-5-1 | RI | 缺陷帳本歸檔檔夾具（含欄數不符與重複 ID 的列） | 只讀缺陷主檔與兩姊妹軌：歸檔列不成議題、不進 `problems`（以檔案讀取紀錄判定歸檔檔未被開啟） |
| AT-IC-06-5-E-1 | RI | 觀察帳本歸檔檔夾具（含與主檔重複的 ID） | 照常讀，已結列成議題；重複者主檔先中、歸檔列 `ID-DUP` |

#### FR-IC-07 的 AT　Bridge 與 console-api 傳遞（PRD §6.3、§6.4）

| AT | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|
| AT-IC-07-1-1 | BR | Bridge 在線（真 CLI、`make_si_repo` A 態） | `GET /si/issues`、`GET /si/issues/{id}` 每請求恰一次子行程；200 本文與同參數根層 `export --kind issues` 輸出逐值相同且各層鍵序相同（保序解析後比對鍵序列；差分，`generated_at` 除外）；其他方法 405 |
| AT-IC-07-1-E-1 | BR | 清單類未知查詢參數（foo=1）、單筆任何查詢參數、`{id}` 格式不符（小寫 `obs-si-001`、兩位數字的觀察 ID、`PROP-SI-4`、`DEF-x-y` 各一）、合法而查無 | 前三者 422 `invalid_request`（rule 依序為 `unknown_parameter`、`unknown_parameter`、`invalid_format`；`{id}` 四個近似值皆 `invalid_format`）；查無 404 `si_not_found`（`id`） |
| AT-IC-07-2-1 | BR | `status` 為中文、`source` 含空白；另三值：恰 64 字元的值、`a=b`、含 U+0085 與 U+009F 的值 | argv 記錄為單一元素 `--status=待處理`、`--source=a b`；真 CLI 端到端回對應篩選結果、不亂碼、不 500（本機 Windows 與 CI Linux 皆跑）；另三值皆通過驗證並啟動子行程，argv 為單一元素（如 `--status=a=b`）；下游 CLI 不認該值而 rc 3→503 屬預期、不是 422（只擋 U+0000～U+001F、U+007F） |
| AT-IC-07-2-2 | ES | Docker 全棧：console-api 經真 Bridge 到真 CLI；`GET /api/v1/issues` 帶中文 `status`、含空白的 `source` | 200 且 `items` 為篩選後結果、不亂碼、不 500（SCG-5 實機證據；補 AT-IC-07-2-1 缺的 console-api 這一段） |
| AT-IC-07-2-E-1 | BR | `status` 或 `source` 以 `-` 起頭、恰 65 字元、含控制字元（`%00`、`%0A`、`%7F`） | 422（rule 依序 `leading_dash`、`too_long`、`control_char`）且 `record_si_popen` 顯示未啟動子行程（不是 500） |
| AT-IC-07-2-E-2 | BU | `BridgeHttpAdapter.siExport` 對 `status`、`source` 值「待處理」、含空白與豎線字元的「a b」、含 `%`、`&`、`=`、`#` 的值 | `requestTo` 所見的編碼後網址，查詢字串為嚴格 percent-encode（UTF-8、僅非保留字元原樣、大寫十六進位）；`URI.create` 不拋例外；解碼後等於原值的對拍留在 `IssueApiIT`（AT-IC-07-4-E-1） |
| AT-IC-07-3-1 | BR | 真 CLI 回 rc 3（未知 `status` 值）；`limit` 超過 `export_limit_max`；另以 monkeypatch 縮小輸出上限常數與逾時常數各一例 | Bridge 503 `si_unavailable`（前兩例 `cause`＝`nonzero_rc`、`detail` 逐字含 stderr 尾段；後兩例 `cause` 為既有的 `output_too_large` 與逾時 cause，issues 不新增 cause） |
| AT-IC-07-3-2 | BI | MiniBridge 對 issues 回 503 `si_unavailable` | console-api 503 同 reason、`details.cause`、`detail` 逐字、本文沒有 `data` |
| AT-IC-07-3-E-1 | BR | 空字串 `status=` | 不特判：照傳給 CLI（rc 3）→ 503（不 200、不 500） |
| AT-IC-07-4-1 | BI | VIEWER 的 JWT 呼叫 `GET /api/v1/issues` | 200；鍵為 camelCase（severityRank、updatedAt、nextStep、nextSince、byStatus、byTab…）、值不動（逐值等於 `A.camel.json` 的 `issues`）；每筆帶 `priority`、`priorityNote`（rankable 為真且有列才有值，其餘 null） |
| AT-IC-07-4-E-1 | BI | 無 JWT；`since`＝-1、`limit`＝0、`since`＝abc、`since`＝2147483648；對照 `since`＝2147483647；帶 `status`、`source` | 401；前四個 `since`／`limit` 例皆 400 且 MiniBridge 零呼叫（型別不符不觸及 Bridge）；`since`＝2147483647 為 200 並原樣轉發；`status`、`source` 原樣轉發（MiniBridge 見到解碼後的同值） |
| AT-IC-07-5-1 | BI | `GET /api/v1/issues/{id}`（存在） | 含 `raw`、`timeline`、`links` 與 `priority`、`priorityNote`；沒有 `legend`、`summary` |
| AT-IC-07-5-E-1 | BI | 查無；格式不合 | 404 reason `si_not_found`、訊息「查無此議題」、`details.id`；422（頂層 reason `引擎拒絕此請求`、`details.bridgeReason`＝`invalid_request`） |
| AT-IC-07-6-1 | BB | ArchUnit 檢查 `AgentBridge`、`SiController` | `si` 起頭方法仍恰五個；`siExport` 參數型別依序 String、Integer、Integer、String、String、String；`SiController` 的 GET 七與 POST 四不變 |
| AT-IC-07-6-E-1 | BB | ArchUnit 檢查 Issue* 類別 | 它們呼叫 `AgentBridge` 的方法只有 `siExport`；`IssueController` 名稱不符 `Si*Controller`（不受該組計數鎖） |
| AT-IC-07-7-1 | BI | MiniBridge 停用（連線拒絕）、讀取逾時、優先順序表讀取失敗（`IssuePriorityRepository` 替身拋 `DataAccessException`） | `GET /api/v1/issues` 非 2xx 且本文沒有 `data`（不回空表、不回缺 priority 的清單） |
| AT-IC-07-7-E-1 | BI | Bridge 503、連線拒絕、逾時、順位表失敗各一 | 依序 503 `si_unavailable`、502、504、5xx；皆無 `data`；Bridge 單次呼叫（逾時不重試） |
| AT-IC-07-8-1 | GT | 本功能完整變更清單 | G-C4：`git status --porcelain -uall`（以開工前快照相減）與已 commit 後的 `git diff --name-only <base>..HEAD` 皆不含 `reasons.ts`、`API_Contract_P3-6.md`、`Architecture.md` |
| AT-IC-07-8-E-1 | GT | G-C4 的自證負控：以 here-string 餵含 `reasons.ts` 的合成清單 | 同一檢查函式回非 0 |
| AT-IC-07-9-1 | FL | `ISSUE_REASONS`（`lib/domain/issues.ts`）與 `API_Contract_IssueCenter.md` 的 reason 表（只列 issue 類） | reason 鍵集合與中文訊息逐字雙向相等 |
| AT-IC-07-9-2 | BC | `ErrorReasons` 的 `ISSUE_` 前綴常數與契約表；`IssueApiIT` 的 409 本文 | identifier 集合雙向相等；409 的 `message` 與契約表中文訊息逐字相同 |
| AT-IC-07-9-E-1 | FL | 合成契約表字串：多一列、少一列、訊息差一字、欄序對調；另一例在標題 `issue 類 reason 表` 之前放一張他表、之後放第二張表 | 比對函式前四者各回非空；他表與第二張表不影響結果（只取標題後第一張表，回空）；後端 `BC` 以同五種合成字串各得同結果 |

#### FR-IC-08 的 AT　畫面與中文（PRD §7）

| AT | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|
| AT-IC-08-1-1 | FV | 夾具涵蓋七狀態、八結果、四來源、四嚴重度 | 渲染清單、詳情、狀態說明：可見文字（排除標題、ID、原列展開區、優先順序備註、延後列原文節錄）不含 §5.4 英文詞（整詞比對）；原列展開區顯示原值且標籤為中文 |
| AT-IC-08-1-E-1 | FL | 英文詞偵測函式負控 | 含 open、fixed@abc、handed-off 者回非空；含 PROP-SI-004、中文、「P1」者回空；詞表與 §5.4 的 22 詞逐字相同 |
| AT-IC-08-2-1 | FG | 按「狀態說明」 | 對話框由 `legend` 渲染（七狀態、八結果、四來源、四嚴重度各一行；`updatedAtNote` 同在其中） |
| AT-IC-08-2-E-1 | FG | 把 `legend` 每個 `meaning` 換成哨兵字串；`legend` 缺 `updatedAtNote` | 對話框只顯示哨兵（沒有第二份說明文字）；缺註記時不出現（不寫死） |
| AT-IC-08-3-1 | FV | 開頁 | 預設分頁＝待處理；四分頁各以 §7 的 `status` 向 API 取資料（待處理→「待處理」、待您決定→「待您決定」、已完成→「已完成」、全部→不帶）；摘要列三數字＝`summary.byTab`；待處理上方有計件條；沒有「本週完成」 |
| AT-IC-08-3-E-1 | FV | 網路層間諜 | 切到待處理恰一個請求且 `status`＝「待處理」（不是三個成員的列舉）；與 AT-IC-06-2-3 互證前端不持有成員清單 |
| AT-IC-08-4-1 | FV | 清單 | 固定八欄依序：編號、來源、標題、嚴重度、狀態、優先順序、最後更新、下一步；點編號開側面板詳情（同頁、不換路由；原列、時間線、關聯） |
| AT-IC-08-4-E-1 | FD | 詳情的關聯 ID | 可點（跳到該議題詳情）；查無該議題＝顯示「不在議題中心（可能已歸檔）」且不可點 |
| AT-IC-08-5-1 | FV | Bridge 503 或 504 | 整片顯示原因（`cause`、`detail` 逐字）；摘要列三數字顯示「—」；不顯示「0 件」或空表 |
| AT-IC-08-5-2 | FV | 某帳本讀不到（`ne` 含 `*-LEDGER-UNAVAILABLE`、`summary.byTab` 對應格 null） | 該格顯示「—」、其餘格與清單照常；提示條（說明取自 `legend`）明說哪一本讀不到 |
| AT-IC-08-5-E-1 | FV | `ne` 或 `problems` 非空；兩者皆空 | 前者一律顯示提示條但清單照常；後者沒有提示條 |
| AT-IC-08-6-1 | FV | `truncated` 為 true | 自動載完（`SI_AUTO_LOAD_MAX_PAGES` 內）；全部取回後沒有「結果不完整」 |
| AT-IC-08-6-E-1 | FV | 取完第 20 頁（`SI_AUTO_LOAD_MAX_PAGES`＝20）後仍有下一頁；恰 20 頁取完且已無下一頁 | 前者明說「結果不完整」並顯示已載入件數；後者不顯示 |
| AT-IC-08-7-1 | FV | 帳本文字與優先順序備註含 `<script>`、`**`、反引號 | 一律純文字顯示（不執行、不成元素、不渲染 markdown） |
| AT-IC-08-7-2 | FS | `components/domain/issues/**` 靜態掃描 | 無 `dangerouslySetInnerHTML`、無 Markdown 渲染器 import |
| AT-IC-08-7-E-1 | FS | 掃描器自帶負控 | 違規樣本（`dangerouslySetInnerHTML`、react-markdown import）逐一回非空；良性樣本回空 |
| AT-IC-08-8-1 | FV | 全部分頁 | 七顆狀態 pill 快篩（文字取自 `legend`）加「未歸類」、來源下拉、關鍵字（編號與標題）；待您決定的列置頂 |
| AT-IC-08-8-E-1 | FV | 分頁真的沒有議題；關鍵字（大小寫混用，如 `prop-si` 對編號 `PROP-SI-004`；只出現在標題的字串；空白關鍵字；列表只載入部分頁時輸入） | 顯示「這個分頁目前沒有議題」（與錯誤整片顯示不同）；關鍵字為不分大小寫（ASCII）子字串、比對編號與標題、只篩已載入的頁；空白關鍵字＝不篩 |
| AT-IC-08-9-1 | FV | 待處理分頁含各嚴重度、null、表外值議題 | 計件條六格（緊急、高、中、低、—、未歸類）加總＝待處理件數；點摘要列三數字之一切到對應分頁 |
| AT-IC-08-9-E-1 | FL | 計件函式表驅動（固定種子的生成式夾具） | severity null 計「—」、「未歸類：P5」類計「未歸類」、未知 rank 不計入前四格；加總不變式恆成立 |
| AT-IC-08-10-1 | FV | 已完成分頁含各來源與八種結果的議題 | 依來源下拉、結果快篩（選項＝`legend.results`）、關鍵字篩：三者取交集 |
| AT-IC-08-10-E-1 | FV | 清掉篩選；改 `legend` 的一個結果名 | 回到全部已完成議題；結果快篩選項隨 `legend.results` 改變（不寫死） |
| AT-IC-08-11-1 | FD | 已完成議題開詳情 | 日期旁註明「最後已知動靜」（文字取自 `legend.updatedAtNote`）；詳情頭部日期＝該議題 `updatedAt` |
| AT-IC-08-11-E-1 | FD | 非已完成議題；`legend` 換字 | 不帶此註記；註記隨 `legend` 換字 |

#### FR-IC-09 的 AT　優先順序（階段二；PRD §6.4、§6.5）

| AT | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|
| AT-IC-09-1-1 | BI | ADMIN（不在 `console.si.deciders`）、議題 rankable＝true；PUT `{"rank":2,"note":"先做"}` | 200 回 `{id, rank:2, note:"先做", setBy:<帳號>, setAt}`；`console.issue_priority` 恰一列；之後 GET 帶 `priority`＝2、`priorityNote`＝「先做」 |
| AT-IC-09-1-E-1 | BI | note 缺省；再以同值 PUT 同一議題；另一議題 PUT 同一 `rank`；ADMIN 不在 deciders 名單 | note 存成空字串、GET 回 `""`；同值再 PUT 仍 200 且仍恰一列；兩議題同 `rank` 時兩列皆存（無唯一鍵）；仍 200（不要求名單） |
| AT-IC-09-2-1 | BI | OPERATOR 與 VIEWER 的 JWT 各 PUT、DELETE | 403 `ACCESS_DENIED`；表零寫入；MiniBridge 零呼叫；`console.audit_log` 各留一列拒絕紀錄 |
| AT-IC-09-2-E-1 | BI | 無 JWT；規則序 | 401（audit_log 同樣留一列）；OPERATOR 不得因通用 `/api/v1/**` 規則通過（兩條 ADMIN 規則置於通用規則之前） |
| AT-IC-09-3-1 | BI | ADMIN PUT 且 `rank` 為 null、缺鍵、0、-1、1.5、"a"、`true`、`[]`、`{}`、10000，或 `note` 為數字（5）、`null`、超過 200 code point（含全形與表情符號各算 1）或含控制字元 | 422 `invalid_request`（欄 `rank`／`note`，不是 400）；`details.violations[{field,message}]` 一次全列；表零寫入；Bridge 零呼叫（`rank`＝null 不是清除；`note`＝null 不是缺省，只有缺鍵才是） |
| AT-IC-09-3-E-1 | BI | 邊界：rank＝1 與 9999；note 缺省；恰 200 code point 的 note（含表情符號）；201 個；含 U+007F 或首尾換行 | 前四者皆 200；後二者 422 |
| AT-IC-09-3-E-2 | BI | ADMIN PUT 且本文為 `[]`、`"x"`（合法 JSON 但不是物件）、`{`（JSON 語法錯） | 皆 400 `MALFORMED_REQUEST_BODY`（不是 422）；表零寫入；Bridge 零呼叫 |
| AT-IC-09-4-1 | BI | 已有順位；DELETE 連送兩次 | 第一次 204、該列被刪、GET `priority`＝null；第二次仍 204（冪等）；全程 MiniBridge 零呼叫 |
| AT-IC-09-4-E-1 | BI | 對已完成或已不存在的議題 DELETE；`id` 格式不合 | 204 且遺留順位清得掉；格式不合 422（不碰 DB） |
| AT-IC-09-5-1 | BI | 議題狀態為已完成、延後、候選、觀察中；PUT rank 1 | 409 `issue_not_rankable`（`details.id`、`details.status`）；零寫入 |
| AT-IC-09-5-E-1 | BI | 查無議題；Bridge 失敗（503 `si_unavailable`、502、504）；對照 rankable 議題 | 404 `si_not_found`；失敗碼同 SI 唯讀端點且零寫入；rankable（待您決定、待解、進行中）→ 200 |
| AT-IC-09-6-1 | BM | 既有資料庫（V13 狀態含 SI 稽核列）升級到 V14 | Flyway 升級成功；`ddl-auto=validate` 通過；版本清單含「14」 |
| AT-IC-09-6-2 | ES | Docker 全棧：設定順位後重啟 backend 與資料庫容器 | GET 仍回同值（SCG-5 實機證據；非每 commit 閘） |
| AT-IC-09-6-E-1 | BM | INSERT：`issue_id` 格式不合、`rank` 為 0／10000／NULL、`note` 為 NULL；合法邊界（rank 1、9999、note 200 字） | 前者各被 CHECK 或 NOT NULL 拒絕（SQLState 23514、23502）；後者可寫 |
| AT-IC-09-7-1 | BI | 兩個 ADMIN 先後 PUT 同一議題 | 後者生效；`setBy`、`setAt` 為後者 |
| AT-IC-09-7-E-1 | BI | 兩執行緒同時 PUT 同一議題；期間第三執行緒反覆 GET 該議題 | 恰一列、無 500、結果為其中一筆完整值（不混合 rank 與 note）；GET 只見舊值或新值、不見半寫（單列原子） |
| AT-IC-09-8-1 | BA | ArchUnit：順位表寫入敘述、persistence adapter、`IssueController` 映射 | 寫入敘述恰兩條（UPSERT、DELETE，另有唯讀 SELECT）；只有一個 persistence adapter 觸及該表；恰一個 `@PutMapping` 與一個 `@DeleteMapping` |
| AT-IC-09-8-2 | BI | 任一 PUT 或 DELETE 前後 | 四類帳本位元組不變；`MiniBridge.requests()` 只含 GET |
| AT-IC-09-8-E-1 | BA | 掃描器負控：合成類含第三條寫入敘述、第二個 persistence adapter、第二個 `@PutMapping` | 各使檢查回違規 |
| AT-IC-09-9-1 | FV | 非 ADMIN 開頁 | 看得到順位與備註；沒有編輯控制項；網路層無 PUT 與 DELETE |
| AT-IC-09-9-2 | FP | ADMIN | 只對 rankable 的列有「排序」鈕；對話框（順位、備註、儲存＝PUT、清除＝DELETE）；儲存後以回應重排（不做樂觀更新）；順位欄只對 rankable 的列顯示 |
| AT-IC-09-9-E-1 | FP | 非 rankable 列；ADMIN 於 rankable 列輸入順位 0、10000、1.5、「１２」（全形數字）、「1e3」與備註 201 code point；另輸入順位「 12 」（前後空白）、備註恰 200 code point | 非 rankable 列無排序鈕、順位欄不顯示遺留順位；前述不合者被表單驗證擋下、不送請求並就地說明；「 12 」去前後空白後送出 rank 12、備註恰 200 通過 |
| AT-IC-09-10-1 | BI | 議題曾有順位、後來狀態變成已完成（遺留列仍在表中） | GET 清單該議題 `priority`、`priorityNote`＝null；PUT 它＝409；ADMIN DELETE 204 後表中該列消失 |
| AT-IC-09-10-E-1 | FL | 遺留順位與排序 | 不參與排序（同 AT-IC-05-1-E-2）；順位欄對非 rankable 列空白 |
| AT-IC-09-11-1 | BI | ADMIN 成功 PUT、DELETE 各一次 | `console.audit_log` 各多一列（subject＝操作者、method、path 含議題 ID、status 200／204） |
| AT-IC-09-11-E-1 | BI | 被拒（401、403）與失敗（422、409）的 PUT、DELETE | 同樣各留一列（status 如實；對照 AT-IC-09-2） |

#### FR-IC-10 的 AT　待您決定按鈕（階段二；PRD §7）

| AT | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|
| AT-IC-10-1-1 | FV | ADMIN 在待您決定分頁看到提案列（`action`＝decide-proposal）；按「決定」 | 先呼叫 `getSiProposal(id)` 取快照，再開 `SiDecideDialog`（`target={{kind:"prop", proposal}}`，綁該快照 digest）；closed 提案動詞只有「回滾」；送出走 `POST /api/v1/si/proposals/{id}/decide` |
| AT-IC-10-1-E-1 | FV | `getSiProposal` 失敗 | 不開對話框、顯示錯誤；對話框的 digest 取自快照而非清單項 |
| AT-IC-10-2-1 | FV | 待您決定的觀察列（`action`＝close-observation）；按「關閉並裁決」 | 開 `SiObsCloseDialog`（`target={{obsId}}`），送出走既有關閉端點 |
| AT-IC-10-2-E-1 | FV | 各列按鈕 | 觀察列沒有「決定」鈕、提案列沒有「關閉並裁決」鈕；`action` 為 null 的列沒有任何按鈕 |
| AT-IC-10-3-1 | FS | 靜態掃描 `components/domain/issues/`、`lib/domain/issues.ts` | 沒有對 `/si/` 寫入端點的直接呼叫、沒有 `si decide`、`obs-close` 字樣；唯一寫入是 PUT 優先順序與兩個既有對話框 |
| AT-IC-10-3-2 | BS | 掃描 `Issue*.java` | 同判準：沒有 `siWrite*` 呼叫與 `/si/` 寫入路徑字面 |
| AT-IC-10-3-E-1 | FS | 掃描器負控：含 `fetch("/api/v1/si/…decide")`、「si decide」、`postSiDecide` 直呼的樣本 | 回非空；良性樣本回空 |
| AT-IC-10-4-1 | FV | 簽章成功（回 201 receipt）但帳本尚未入帳；重新整理 | 該列仍在待您決定（狀態只跟帳本走） |
| AT-IC-10-4-E-1 | FV | 入帳後（夾具第二次載入回新狀態） | 列移到新狀態；簽章成功當下列不樂觀移動（狀態文字不變） |
| AT-IC-10-5-1 | FV | 非 ADMIN 開待您決定分頁 | 待您決定列顯示「需要 ADMIN 角色才能操作」且沒有按鈕；網路層零寫入請求 |
| AT-IC-10-5-E-1 | FV | ADMIN；VIEWER；OPERATOR | ADMIN 顯示按鈕且不顯示該提示；VIEWER、OPERATOR 皆視為非 ADMIN |

#### FR-IC-11 的 AT　導覽接入（PRD §6.6）

| AT | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|
| AT-IC-11-1-1 | FN | `NAV_REGISTRY` | 恰八項，id 依陣列序 dashboard、projects、import、execute、monitor、settings、self-improving、issues；`issues`＝label「議題中心」、order 55、href `/issues`、mobile false、roles 缺、enabled true；`visibleNavEntries` 顯示序完整八項：dashboard、projects、import、execute、monitor、issues、settings、self-improving；mobile 為 true 的項數 6 |
| AT-IC-11-1-E-1 | FN | 原七列逐欄快照 | 各欄與陣列位置全不變；`self-improving` 的 label「自我進化」、order 70 不變 |
| AT-IC-11-2-1 | GT | `registry.test.ts`、`ToolsRegion.test.tsx` 的 `git diff -U0` | G-C5：只含 §5.7 所列釘值行（`AT_932_6_1`、`AT_950_10_E_1` 改八列並各保留原意；ToolsRegion 連結數與預期序改八項、示範項不再與議題中心同為 order 55） |
| AT-IC-11-2-E-1 | GT | 同兩檔 | 被刪除的 `expect(` 行數＝0（只允許同行改值）；其餘導覽測試原樣通過（`lib/nav` 與 `components/layout` 全綠） |
| AT-IC-11-3-1 | FN | 登記表與路由 | `issues` 的 href 對應存在的 `app/issues/page.tsx`；`match` 對 `/issues`、`/issues/x` 只命中本項、對 `/self-improving` 不命中；`PATHS` 補這兩列 |
| AT-IC-11-3-E-1 | GT | `ToolsRegion.tsx` | G-C6：`git diff --exit-code <base> -- AgentConsole/frontend/components/layout/ToolsRegion.tsx` 無差異 |

#### FR-IC-12 的 AT　非功能（PRD §10）

| AT | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|
| AT-IC-12-1-1 | RI | 真帳本現況；連跑 5 次 `export --kind issues`（子行程含 Python 啟動） | 每次 ≤ 2 秒；單頁輸出 ≤ 1 MB |
| AT-IC-12-1-2 | RI | 合成夾具（觀察 5,000 列、缺陷主檔 2,000 列、事件 500 行；§5.5 產生器） | 同樣 ≤ 2 秒 |
| AT-IC-12-1-E-1 | RI | 合成夾具 `limit`＝500（其中一列症狀欄為 10 KB）；另取該列單筆 `--id` | 輸出 ≤ 1 MB；`items` 不含 `raw`、`timeline`；10 KB 列的 `title` 仍截 80 code point、單筆 `raw` 為 10 KB 全文；鍵序與小夾具相同（效能不改形狀） |
| AT-IC-12-2-1 | RI | `issues --status 待處理 --json`（Windows 與 macOS 或 Linux 皆跑） | stdout 為 UTF-8 位元組（無 BOM、LF 行尾）、rc 0；中文 argv 兩平台一致 |
| AT-IC-12-2-E-1 | RI | stderr；文字表輸出；`--status 待處理` 與 `--status=待處理` 兩種寫法 | stderr 為空；文字表同為 LF、無 BOM；`--status 待處理` 與 `--status=待處理` 結果相同 |
| AT-IC-12-3-1 | BI | 兩次 GET 之間 MiniBridge 的 issues 回應換成新內容 | 第二次請求反映新內容（backend 不快取） |
| AT-IC-12-3-2 | BR | 兩次 GET 之間改動複本倉帳本 | 第二次回應反映新內容；兩請求各啟動一次子行程 |
| AT-IC-12-3-E-1 | FV | 進頁；按「重新整理」 | 各重取一次（網路間諜；無快取命中） |
| AT-IC-12-4-1 | GT | 既有 SelfImproving 根層測試、Bridge `test_si_*`、backend `Si*` 測試、前端 `si` 目錄測試 | G-R5、G-B2、G-K1、G-F3：除 §5.7 同步鎖釘值外全數原樣通過 |
| AT-IC-12-4-E-1 | GT | 既有測試檔的 `git diff` | G-C5：檔案 ⊆ §5.7 同步鎖列；每個 hunk 只動釘值或預期清單；被刪 assert、expect、assertThat 行＝0（hunk 清單供人工核對） |
| AT-IC-12-5-1 | FV | `/issues` 只用鍵盤 | `PillTabs` 可切換；清單列可開詳情；ADMIN 可開排序對話框與決定對話框並以 Esc 關閉、焦點回到觸發鈕 |
| AT-IC-12-5-2 | E2 | Playwright mock 規格：鍵盤走完一輪（Tab 到分頁、方向鍵切換、Enter 開詳情、開排序對話框、Esc 關閉） | 全程通過；a11y 掃描（沿 `a11y.ts`）無嚴重違規 |
| AT-IC-12-5-E-1 | FP | 排序對話框 | Tab 焦點循環困在對話框內；分頁、對話框、按鈕皆有 aria 標籤（`getByRole` 以名稱取得） |

## 4. 邊界與錯誤測試規格

下列邊界各自由所列 AC 的 AT（含反向 AT）覆蓋；開發棒不得因「看起來不會發生」而省略夾具。「覆蓋」欄為 AC 簡碼。對應 AT 的 Given 含覆蓋欄所指 B 列全部值（覆蓋欄列多個 AC 者，各值由所列 AC 的 AT 合併涵蓋、每個值至少出現在一個 AT 的 Given）；開發棒逐值各備夾具，不得只取代表值。

| B | 邊界或錯誤路徑 | 規格（可判定） | 覆蓋 |
|---|---|---|---|
| B-01 | code point 與 UTF-16 | 所有長度上限（`title` 80、表外原值 80、`note` 200）以 code point 計：全形字、U+1F600 之類表情符號各算 1；組合附加符號各算 1（不做字素叢集）；代理對不得被截成孤立代理 | 01-10、04-3、09-3 |
| B-02 | 日期取法 | 時間欄「2026-10-18 23:30 +08:00」→ `2026-10-18`；事件 `t` 「2026-10-18T23:30:00+08:00」→ `2026-10-18`；一律取字串日期部分、不換算時區；不合 `rows.TIME_RE` → null＋`TIME-UNPARSEABLE`（事件 `t` 不合格式者屬 `EVENT-UNSOUND`、不進折疊，不走此路徑） | 04-3 |
| B-03 | 空帳本 | 四本帳都在但為空（只有表頭、空 jsonl）→ `items`＝[]、`summary` 七狀態皆 0 且 `by_tab` 為 0（不是 null）、`problems`＝[]、`legend` 在、rc 0；CLI 文字表末行「共 0 件；問題 0 筆」 | 05-5、05-6 |
| B-04 | 游標與上限 | `since`＝0、`limit`＝1、`limit`＝500 接受；`limit`＝501、`since`＝-1 → rc 3；`since` 大於最大游標 → `items` 空、`truncated` false、`next_since` null；游標序在兩次相同呼叫間完全一致 | 05-2、05-3 |
| B-05 | 篩選值語法 | 「待解,,延後」（空片段）、前後帶空白的值、未知值皆 rc 3；重複值去重；「待處理」與其成員並列取聯集；`--status=待處理` 與 `--status 待處理` 等價；篩選值比對為全等（不做大小寫或全半形折疊） | 05-4、12-2 |
| B-06 | CRLF 與 BOM | 觀察、缺陷帳本以 CRLF 與 UTF-8 BOM 寫入 → 結果與 LF 版逐值相同（含 `origin.line`）；事件帳本 BOM 與行尾單一 CR 容忍（沿 `events.read_lines`） | 04-8、04-9 |
| B-07 | 不可讀檔 | 以「同名目錄取代檔案」構造（跨平台，不依賴 `chmod`）→ `OSError` 路徑＝`*-LEDGER-UNAVAILABLE`；歸檔檔同理 | 01-8 |
| B-08 | 路徑分隔 | `origin.file` 一律 `/`、repo 相對；Windows 夾具不出現 `\` | 04-8 |
| B-09 | 近似 ID | `obs-si-001`、兩位數字 ID、`PROP-SI-4`、`DEF-x-y` 不是合法議題 ID：觀察列→`ROW-ARITY`（ID 欄不合）；`--id` 或 Bridge `{id}`→rc 3 或 422 | 04-9、05-4、07-1 |
| B-10 | 文字內容 | 帳本文字含轉義 `\|`、反引號、`<script>`、`**` → `title` 去 `**`、`__`、`~~`、反引號後仍為純文字、JSON 轉義正確；前端不渲染 markdown | 04-3、08-7 |
| B-11 | 超長欄位 | 症狀欄 10 KB → `title` 截 80 code point、`raw` 全文（僅單筆）；500 筆一頁仍 ≤1 MB（清單不含 `raw`、`timeline`） | 12-1、04-3 |
| B-12 | 無 git | 夾具不是 git repo 或 PATH 無 git → `head_sha` null＋`ne` `git-unavailable`；其餘照常、rc 0 | 01-7 |
| B-13 | 時間依賴 | 除 `generated_at` 外，輸出與牆鐘無關（連跑兩次逐位元相同） | 06-2、12-3 |
| B-14 | Bridge 輸出超量與逾時 | 沿既有 `output_too_large`、逾時 cause（issues 不新增 cause）；以 monkeypatch 縮小常數驗證 503 與 `cause` | 07-3 |
| B-15 | Bridge 篩選值長度與字元 | 恰 64 字元接受、65 拒絕（`too_long`）；含 `=` 的值（`a=b`）→ 單一 argv `--status=a=b` 原樣；U+0080 以上的控制類字元不在拒絕範圍（只擋 U+0000～U+001F、U+007F） | 07-2 |
| B-16 | backend 整數邊界 | `since`＝2147483647 接受；2147483648 或 `abc` → 400（型別不符，不觸及 Bridge） | 07-4 |
| B-17 | PUT 本文型別 | `rank` 為 `true`、`[]`、`{}`、字串、小數 → 422（欄 `rank`，不是 400）；`note` 為數字或 `null` → 422（只有缺鍵才是缺省）；本文不是 JSON 物件（`[]`、`"x"`；JSON 語法錯亦同）→ 400 `MALFORMED_REQUEST_BODY`（既有 reason） | 09-3 |
| B-18 | 併發 | 兩執行緒同時 PUT 同一議題→恰一列、無 500、值完整；PUT 期間的 GET 只見舊值或新值、不見半寫（單列原子） | 09-7 |
| B-19 | 冪等 | DELETE 連送兩次皆 204；PUT 同值兩次 200 且仍一列 | 09-4、09-1 |
| B-20 | 順位重複 | 兩議題同 `rank` → 兩列皆存（無唯一鍵）；顯示序回到後續鍵（severityRank→updatedAt→id） | 05-1、09-1 |
| B-21 | 前端關鍵字 | 關鍵字為不分大小寫（ASCII）子字串，比對編號與標題；只篩已載入的頁；空白關鍵字＝不篩 | 08-8、08-10 |
| B-22 | 前端順位表單 | 去前後空白後須全為數字且 1～9999（`^[0-9]{1,4}$` 後轉數）；備註 ≤200 code point；不合不送請求並就地說明 | 09-9 |
| B-23 | 自動載入上限 | 頁數恰等於 `SI_AUTO_LOAD_MAX_PAGES`（20）且已無下一頁→不顯示「結果不完整」；上限後仍有下一頁→顯示並帶已載入件數 | 08-6 |
| B-24 | 契約檔 reason 表解析 | 以標題 `issue 類 reason 表` 起頭的第一張表為準；欄序固定；多一列、少一列、訊息差一字皆使鎖轉紅 | 07-9 |
| B-25 | 零測試與假綠 | 判定指令收集 0 個測試＝FAIL；`-k` 無命中＝AT 未實作；跳過（skip）不算通過（根 CLAUDE.md 規則 12） | 全部 |

## 5. 測試資料規格

### 5.1 根層夾具與建構器（`test_selfimproving_issues.py` 模組層；D-R11）

| 建構器 | 用途 |
|---|---|
| `issue_repo(tmp, *, obs=(), defs=(), sib_blocked=(), sib_debt=(), events=(), obs_archive=None, def_archive=None, git=True) -> Path` | 建 hermetic tmp repo（沿 `fx.make_p1_repo`：`fx.put` 寫 `docs/06_quality/` 的觀察帳本、`AutoSDD_Defect_Log.md`、兩姊妹軌、事件帳本、複製真 `params.json`；`git init`＋`fx.commit_all`）；缺帳本以參數省略；歸檔檔以 `obs_archive`、`def_archive` 寫入 |
| `obs_row(n, cat='bug', sev='P3', disp='open', marks='來源=代理', symptom=…, time='2026-10-18 10:00 +08:00')` | 九欄觀察列；ID 由 `fx.obs_id(n)` 產生（測試碼不寫 `OBS-SI-` 接數字） |
| `def999(n)` | 本檔自備：`def999(n)`＝`f"DEF-999-{n:03d}"`（建議以 `"DEF" + f"-999-{n:03d}"` 組字，沿 `fx.def_id` 的執行期組字慣例）；缺陷列與姊妹軌列的 ID 一律用它；不改 `_selfimproving_fixtures.py`（其 `fx.def_id(n)` 回 200 族 9000 號段的編號，不是 999 保留族） |
| `def_row(n, sev='P2', status='open', date='2026-10-18', evidence=…)`、`sib_row(n, unlock=…, review='2026-10-20')` | 缺陷七欄列、姊妹軌五欄列；ID＝`def999(n)` |
| 事件鏈 | 重用 `fx.prop_ev`、`dec_ev`、`rollback_ev`、`fx.write_events`、`fx.append_events`；P2（`_selfimproving_p2_fixtures`）：`drive_to`、`cli` |
| P3 夾具（`_selfimproving_p3_fixtures`） | `promoted(R)`（回 PROP 號，狀態 promoted）、`mea_chain(R, P, result, stop_at=None)`（`'recurred'`、`'clean'`、`'rolled-back'`；`stop_at='open'` 停在 measuring）、`root_attr`、`link_attr`；`s_rec`、`s_pend` 是量測窗候選情境（帶 `reopens` 的列），**不用於** closed 或待回滾的配方 |
| `run_issues(repo, *argv) -> (rc, out, err)` | 子行程跑 `tools/selfimproving.py`（任意 cwd、UTF-8）；`build_obj(repo, **kw)` 為 in-process 呼叫 `issues.build`（注入縫僅此路徑可用） |
| `make_scale_repo(tmp, obs=5000, defs=2000, events=500)` | 規模夾具（AC-IC-12-1）：列由模板迴圈產生、事件為合法鏈（提案卡面量不到屬預期，僅驗效能與形狀） |

### 5.2 注入縫（僅 in-process；`mock.patch.object`；D-R1）

| 縫 | 目標 | 注入內容 | 用於 |
|---|---|---|---|
| S1 | `issues.si_fold.fold` | 包裝真 `fold`，把指定 PROP 的 `state` 改成 `zombie` | 01-2 |
| S2 | `issues.si_fold.effective_windows` | 回 `[]`，或把該 PROP 窗的 `effective` 換成 `pending` | 01-3 |
| S3 | `issues.si_events.load_sound_events` | 回含 `kind='zombie.act'`、`dkind='zombie'` 的事件清單（繞過 `validate`）；只影響折疊與時間線的輸入，`EVENT-PARSE`、`EVENT-UNSOUND` 由原始行另算、不受影響（D-R14） | 04-11 |
| S4 | `issues.si_card.build` | 對指定 PROP 拋 `si_card.CardError` | 04-7 |
| S5 | `issues.si_status.measure_value` | 回 `{'status':'NOT-EVALUABLE','reason':'params-invalid'}` | 04-2 |

### 5.3 PRD §5.2 十九情境的夾具配方（AT-IC-04-1-1 表驅動；句型逐字取 PRD §5.2 同序列）

| N | 情境 | 夾具配方 |
|---|---|---|
| N01 | 候選 | 觀察 open、bug、來源代理、無 attr |
| N02 | 待您決定・提案 proposed（loop） | `fx2.drive_to(R, 'proposed')`（`prop` route=loop） |
| N03 | 待您決定・提案 proposed（handoff） | `prop` route=`handoff:T1`（通道中文「掌舵者指令」），狀態 proposed |
| N04 | 待您決定・提案 verified | `fx2.drive_to(R, 'verified')`（鏈到 `app.verify` 後狀態 verified） |
| N05 | 待您決定・closed 復發待回滾 | `P=promoted(R)`＋`mea_chain(R,P,'recurred')`（closed、recurred，從未 `dec(rollback)`） |
| N06 | 待您決定・觀察（decision） | 觀察 open、分類 decision |
| N07 | 待解・缺陷 | 缺陷列 status open（無姊妹軌） |
| N08 | 待解・觀察 | 觀察 open、process、標記 `carrier=console` |
| N09 | 進行中・缺陷 routed | 缺陷列狀態 routed |
| N10 | 進行中・approved | `fx2.drive_to(R, 'approved')` |
| N11 | 進行中・returned | `dec(return)` 後 returned（`Prop.rev`＝1）→ 句型含「第 1 版」（`[rev]`＝折疊後 `Prop.rev`） |
| N12 | 進行中・sandboxed | `fx2.drive_to(R, 'sandboxed')` |
| N13 | 進行中・已決定回滾 | `P=promoted(R)`＋`fx.append_events(R, [fx.dec_ev(n,'rollback')])`（n＝P 的號；promoted 變體）；另兩變體：先 `mea_chain(R,P,'recurred',stop_at='open')`（measuring）、先 `mea_chain(R,P,'recurred')`（closed）；皆不加 `fx.rollback_ev` |
| N14 | 觀察中・promoted | `app.promote` 後 promoted、尚無 `mea.open` |
| N15 | 觀察中・measuring | `mea.open`（`w_opp`=5）、`n_opp`=0 → 「量測窗 0／5」 |
| N16 | 延後・觀察 | 處置「deferred；再開症狀：X」 |
| N17 | 延後・缺陷（姊妹軌） | 缺陷 ID 列在姊妹軌表（解鎖條件、最近複查日） |
| N18 | 已完成 | 五個子夾具：觀察 `fixed@`（「已結案（已修復）」）；觀察已轉交 DEF（加「，見 <ID>」）；提案 handed-off（加「，通道：<中文>」）；提案 rejected 冷卻中；提案 rejected 且 `unblocked`（加「；冷卻已解除」） |
| N19 | 未歸類 | 注入縫 S1 構造的表外值 → 「帳本值不在對照表內，請查原列」 |

### 5.4 前端與跨端共用詞表、測試鉤

**英文詞表 `ENGLISH_STATE_WORDS`（22 詞；整詞比對、前後字元不屬英數與 `-`；議題 ID 形態先剔除）**：`open`、`deferred`、`fixed`、`decided`、`retired`、`merged`、`proposed`、`routed`、`wontfix`、`closed-by-decision`、`no_action_needed`、`partial`、`workaround`、`verified`、`approved`、`returned`、`sandboxed`、`promoted`、`measuring`、`closed`、`rejected`、`handed-off`。根層 `issues.py` 的下一步與前端的可見文字檢查都引用這 22 詞（前端常數住 `lib/domain/issues.ts`，D-C8）。

**前端測試鉤**：以 `getByRole`（`tab`、`dialog`、`button`）與文字為主；下列 `data-testid` 為輔，名稱逐字固定。

| testid | 元素 |
|---|---|
| `issues-page`、`issues-error-panel`、`issues-empty`、`issues-incomplete`、`issues-hint-bar` | 頁根；整片錯誤；空分頁；「結果不完整」；提示條 |
| `issues-summary-pending`、`issues-summary-decide`、`issues-summary-done` | 摘要列三個可點數字（null 格文字「—」） |
| `issues-sev-<urgent｜high｜mid｜low｜none｜unmapped>` | 待處理計件條六格 |
| `issues-filter-source`、`issues-filter-result`、`issues-filter-keyword`、`issues-status-pill-<狀態名>` | 來源下拉、結果快篩、關鍵字、全部分頁的狀態 pill（含「未歸類」） |
| `issue-row-<ID>`、`issue-top-pinned`（PRD 指定，帶 `aria-label="置頂"`） | 清單列；置頂標記 |
| `issue-detail`、`issue-detail-date`、`issue-detail-raw`、`issue-detail-timeline`、`issue-detail-links` | 詳情與其區塊 |
| `issues-legend-open`、`issues-legend-dialog` | 「狀態說明」鈕與對話框 |
| `issue-priority-open-<ID>`、`issue-priority-dialog`、`issue-priority-rank`、`issue-priority-note`、`issue-priority-save`、`issue-priority-clear` | 排序鈕與對話框 |
| `issue-decide-<ID>`、`issue-close-<ID>`、`issue-admin-only-<ID>` | 「決定」、「關閉並裁決」、「需要 ADMIN 角色才能操作」 |

### 5.5 範例排序表（AT-IC-05-1；D-R12：根層與前端各嵌一份相同的表與預期序）

**規則一（待處理、待您決定；根層無順位）**：項目（`id` ／ `severity_rank` 或 `severityRank` ／ `updated_at` 或 `updatedAt`；根層用 snake_case、前端用 camelCase）：`DEF-999-001` 1／2026-10-10、`DEF-999-002` 1／2026-10-05、`DEF-999-003` 2／2026-10-01、`DEF-999-004` null／2026-10-02、`DEF-999-005` 3／null、`DEF-999-006` 3／2026-10-20、`DEF-999-007` 1／2026-10-05。預期序一：002、007、001、003、006、005、004。

**規則二（已完成、全部）**：`DEF-999-011` 2026-10-20、`DEF-999-012` 2026-10-20、`DEF-999-013` 2026-10-25、`DEF-999-014` null、`DEF-999-015` 2026-09-30。預期序二：013、011、012、015、014。

**前端含順位（僅 `lib/domain/issues.test.ts`）**：同規則一的七項，另設：003＝順位 1、002＝順位 2、001＝順位 2、005＝非 rankable 卻有遺留順位 1（不參與排序）。預期序三：003、002、001、007、006、005、004。

**規模夾具（AC-IC-12-1）**：觀察 5,000 列、缺陷主檔 2,000 列、事件 500 行；上限 2 秒（含 Python 啟動）、`limit`＝500 的單頁 ≤ 1 MB。

**根層動詞釘值（AC-IC-06-3）**：既有 23 個動詞＝`check`、`status`、`scan`、`card`、`export`、`run-open`、`run-close`、`attr`、`attr-confirm`、`attr-reject`、`prop-new`、`prop-revise`、`research`、`decide`、`heldout-freeze`、`sandbox`、`verify`、`promote`、`rollback`、`obs-add`、`obs-close`、`measure`、`capacity`；功能後加 `issues`。

### 5.6 Bridge、backend、frontend 夾具

| 載具 | 夾具與輔助 |
|---|---|
| Bridge | `si_repo_support.make_si_repo(tmp, 'A'｜'B')`（複本倉＋真 CLI；閉包以 `tools/lib/selfimproving/` 目錄複製，無需改 `CLI_CLOSURE`）；`record_si_popen`（記錄 argv 與 Popen 次數）；`fake_si`（假 CLI：旗標解析認 `--status=`、`--source=`、含 `issues` 罐頭）；`cli_export`（對照真輸出）；`repo_snapshot`；`isolate_home`。夾具倉不增帳本檔（D-C7） |
| backend | `AbstractExecutionIT`、`ApiClient`、JWT 輔助（`viewer()`、`operator()`、`admin()`）、`MiniBridge.Si`（記錄 `MINI.requests()`；加 `/si/issues` 兩路由與失敗模式：503、連線拒絕、逾時）、黃金檔 `si/A.camel.json` 的 `issues` 鍵、`console.issue_priority` 與 `console.audit_log` 的 JDBC 查詢、`IssuePriorityRepository` 失敗替身 |
| frontend | `tests/fixtures/si/A.camel.json` 的 `issues` 鍵（真輸出形）；`components/domain/issues/tests/issues.fixtures.ts`（測試支援檔，置於 `tests/` 子目錄：`si.static.test.ts` 先例的 `SKIP_DIRS` 含 `tests`，且 FS 掃描器另明寫排除 `*.fixtures.ts`，免得夾具內的七狀態詞被當成違規；內容＝七狀態、八結果、四來源、四嚴重度、null 與表外值的 `legend` 與項目）；沿 `SiView.test.tsx` 的 API mock 與角色切換作法；Playwright 沿 `mockApi.ts` 作法在 spec 內自帶 `/api/v1/issues*` 路由（不改 `mockApi.ts`，Q7） |

### 5.7 允許變更的檔案集合（兩半各一張；`git diff --name-only <base>` 必須 ⊆ 本節；「同步鎖」＝PRD §9 的〈需同步改的既有鎖〉逐檔逐行照抄，2026-10-27 於 HEAD `1e82dd18` 重核行號與值全數吻合，皆為同 commit 的可見上修、不刪斷言）

**根層半（`monorepo-issue-center`）**

| 路徑 | 類別 | 內容 |
|---|---|---|
| `tools/lib/selfimproving/issuemap.py`、`issues.py` | 新增 | 對照表與聚合（皆 `ro`） |
| `tools/tests/test_selfimproving_issuemap.py`、`test_selfimproving_issues.py` | 新增 | 兩支測試檔（上限 2 支） |
| `tools/lib/selfimproving/export.py` | 修改 | `KINDS` 加 `issues`；`build` 加 `statuses`、`sources`；轉呼叫 `issues.build` |
| `tools/lib/selfimproving/defs.py` | 修改 | `DefRow` 增 `lineno`、`arity_ok`（有預設值） |
| `tools/selfimproving.py` | 修改＋同步鎖 | `:6`（檔頭「共 23 個」→24）；`_HELP`、`_HANDLERS` 同步；`issues` 動詞；`export` 加 `--status`、`--source` |
| `tools/tests/test_selfimproving_export_status.py` | 修改 | 擴充 RX 的 AT（既有斷言不動） |
| `tools/tests/test_selfimproving_p3_meta.py` | 同步鎖 | `:293`（`len(_HELP)` 23→24）、`:294-298`（`CAPABILITY` 47／48→49／50，分項 `(35／36,8,2,2)`→`(37／38,8,2,2)`） |
| `tools/tests/test_selfimproving_capability.py` | 同步鎖 | `:4`（檔頭「48 個鍵：36 `ro`」）、`:410`（48→50）、`:647-648`（同兩組分項）；`CAPABILITY` 加 `issuemap.py`、`issues.py` 兩個 `ro` 鍵 |
| `tools/tests/test_selfimproving_console_obs.py` | 同步鎖 | `:921`（動詞集合 23→24） |
| `docs/02_architecture/Root_Layout_and_Module_Placement.md` | 文件連動 | §3 SelfImproving 列加兩支檔名與測試檔（反引號納入落點鎖 `test_root_module_layout.py`） |
| `.github/workflows/windows-compat-ci.yml`、`macos-compat-ci.yml` | 連動 | `paths`（push 與 pull_request 各處）加 PRD、本檔、`AutoSDD_External_Blocked_Log.md`、`AutoSDD_Structural_Debt_Log.md`；精確清單以 `AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py` 為準（G-R12） |
| 護欄層棘輪重釘（`tools/tests/test_adr_xplat001_c1c2_lock.py` 與其逐檔表所列證據檔） | 收尾單人窗口 | 兩支新測試檔的重釘稅；開發棒不碰（鐵律七） |

**不得變更**：七個帳本路徑（觀察帳本與其歸檔、`AutoSDD_Defect_Log*.md`、兩姊妹軌、事件帳本、`SelfImproving_Proposals/`）、`params.json`、PRD、`tools/lib/selfimproving/` 內除 `export.py`、`defs.py` 與兩支新檔外的一切檔（含 `fold.py`、`rows.py`、`events.py`）、`.claude/**`、`settings*.json`、守衛面清單檔；開發棒階段 `docs/06_quality/` 整個零差異（G-C2）。

**Console 半（`agentconsole-issue-center`；皆在 `AgentConsole/` 下，路徑省略前綴者相對各子專案）**

| 路徑 | 類別 | 內容 |
|---|---|---|
| `engine-bridge/tests/test_si_issues.py` | 新增 | Bridge 新測試 |
| `engine-bridge/app/si_cli.py`、`app/routers/si.py` | 修改 | `SI_KINDS` 末位加 `issues`、`build_argv` 補 `status`／`source`；兩路由與輸入驗證 |
| `engine-bridge/tests/test_si_cli.py` | 同步鎖 | `:367`（`SI_KINDS` 釘值加 `"issues"`）、`:329-336`（argv 組合加 `issues` 與兩旗標） |
| `engine-bridge/tests/test_si_readonly_lock.py` | 同步鎖 | `:66-68`（`KINDS`、`FLAG_COMBOS`）、`:475`（組合總數隨之驗） |
| `engine-bridge/tests/test_si_routes.py` | 同步鎖 | `:24、41、58`（路徑表與 405 矩陣只增不改，補兩條新路徑案；`:58` 的 5 隨表長上修） |
| `engine-bridge/tests/si_repo_support.py`、`fake_si.py`、`si_golden_regen.py` | 同步鎖 | `si_repo_support.py:78、365`（`KINDS` 取自 `SI_KINDS`，自動含 `issues`）、`fake_si.py:46-51`（旗標解析認 `--status=`、`--source=`；加 `issues` 罐頭）；`si_golden_regen.py` 的 `STATE_KEYS` A、B 各加 `issues` |
| `engine-bridge/tests/test_si_export_differential.py` | 同步鎖 | `:165`（子集比對）、`:189`（黃金檔數 4＋4＋2 不變） |
| `engine-bridge/tests/fixtures/si_golden/*`、`backend/src/test/resources/si/*`、`frontend/tests/fixtures/si/*` | 重產 | 黃金檔 A、B 兩態三份副本（`si_golden_regen.py` 產出，位元組相同） |
| `engine-bridge/README.md` | 文件 | 路由清單加兩條 |
| backend main：`IssueController`、`Issue*` DTO、`IssueQueryService`、`IssuePriorityService`、`application/port/{in,out}/Issue*`、`domain/model/issue/*`、`IssuePriorityAdapter`、`V14__issue_priority.sql` | 新增 | 路徑見 PRD §9（`com/aisdlc/console/` 下） |
| backend test：`IssueApiIT`、`IssuePriorityMigrationIT`、`IssuePriorityArchTest`、`IssueBridgeArchTest`、`IssueReasonsContractTest`、`IssueStaticLockTest` | 新增 | 路徑見 §3 載具表 |
| backend：`AgentBridge.java`、`BridgeHttpAdapter.java`、`SiMirrorQueryService.java:69`、`SiReconcileService.java:158`、`SecurityConfig.java`、`ErrorReasons.java` | 修改 | `siExport` 增 `status`、`source`（兩呼叫端補 `null`）、percent-encode、兩條 ADMIN 規則、`ISSUE_NOT_RANKABLE` |
| backend `adapter/in/web/ErrorResponseDocumentation.java` | 修改 | OpenAPI 錯誤文件（D-C14）：`CONFLICT_ENDPOINTS` 加 PUT 優先順序、`NEVER_NOT_FOUND` 加 DELETE 優先順序、`NOT_FOUND_DESCRIPTION` 加 `GET /api/v1/issues/{id}`、`EXTRA` 加四端點的 422／502／503／504 說明（以 `OpenApiIT` 紅綠為準） |
| backend：`minibridge/MiniBridge.java`、`MiniBridgeController.java` | 修改（測試輔助） | 加兩個 `/si/issues` 路由與失敗模式 |
| backend `architecture/SiReadOnlyArchTest.java` | 同步鎖 | `:100-101`（`siExport` 參數型別 4→6） |
| backend `adapter/out/bridge/BridgeHttpAdapterSiTest.java` | 同步鎖＋擴充 | `:116、117、144、152、184、265`（四參數呼叫補兩個 `null`）；另加編碼 AT |
| backend `infrastructure/config/OpenApiIT.java` | 同步鎖 | `:130、154`（路徑 71→74，`EXPECTED` 加三路徑）、`:138`（操作 81→85）、`:32` 註解 |
| backend `infrastructure/persistence/{SchemaMigrationIT,SiConsoleWritesMigrationIT,V5UpgradeMigrationIT}.java` | 同步鎖 | `:68`、`:129`、`:135`（版本清單「1」～「13」補「14」） |
| frontend：`app/issues/page.tsx`、`components/domain/issues/*`（五元件、`tests/issues.fixtures.ts`、四支 `*.test.tsx`、`issues.static.test.ts`）、`lib/domain/issues.ts`、`issues.test.ts`、`lib/nav/issues-nav.test.ts`、`tests/e2e/issues.mock.spec.ts`、`issues-docker.stack.ts` | 新增 | 五元件：`IssuesView`、`IssueTable`、`IssueDetail`、`IssueLegend`、`IssuePriorityDialog` |
| frontend：`lib/api/{endpoints,queries,types}.ts`、`lib/api/schema.d.ts`、`lib/nav/registry.ts` | 修改 | 四個新函式與型別；`schema.d.ts` 由 `npm run gen:api`（backend 在線）重產入庫；登記表末尾加 `issues`（`ListChecks`，已查 `lucide-react` 存在且與原七個圖示互異） |
| frontend `vitest.config.mts` | 修改 | `coverage.include` 加 `lib/domain/issues.ts`（純邏輯層先例：`lib/domain/sdd.ts` 等；Q10）；門檻不動（lines 70、statements 70、functions 70、branches 60） |
| frontend `lib/nav/registry.test.ts` | 同步鎖 | `:16-37`（`PATHS` 補 `/issues`、`/issues/x`）、`:100-106`（`AT_932_6_1` 長度與四張清單補第八項）、`:120`（icon 互異 7→8）、`:136`（字串 href 清單補 `/issues`）、`:350-361`（`AT_950_10_E_1`） |
| frontend `components/layout/ToolsRegion.test.tsx` | 同步鎖 | `:77、80、82、85-93`（示範項與議題中心同為 order 55：預期序與 `links[5]` 索引改）、`:114`（`original` 補議題中心）、`:146、155`（7→8）、`:160`（`max-md:hidden` 判準加議題中心） |
| frontend `lib/api/endpoints.test.ts`、`si.endpoints.test.ts` | 同步鎖 | `endpoints.test.ts:187、190`（總數 79→83，`EXPECTED` 加四列）；元鎖 `si.endpoints.test.ts:43-46`（釘值字串 79→83、標題同步）；`:34-41` 的 `Si` 前綴鎖不受影響 |
| `docs/02_architecture/API_Contract_IssueCenter.md` | 新增 | 依 §C 逐表抄成（D-C11） |
| `AgentConsole/docs/06_quality/RTM.md` | 收尾（主控） | §2.4 子表一列；開發棒交 rtm_backfill 檔、不直接改 |

**已複核不需改（Console）**：`si-login-gate.test.tsx:66`（「自我進化」label 不改名）、`ToolsRegion.test.tsx:139、165-167`、`layout.test.tsx:135-137`、E2E 的導覽斷言（`shells-and-layout.spec.ts:26-41`、`p9-w7-ui.spec.ts:180-206`；逐名點選、不計項數，G-F5 以真跑複核）；新增前端檔須遵守 `tests/design-rules.test.ts`。**不得變更**：`reasons.ts`、`API_Contract_P3-6.md`、`Architecture.md`、`ToolsRegion.tsx`、既有 `Si*` 元件。

## 6. RTM 連結確認

### 6.1 US → FR → AC → AT（數字由 §1、§3 機械計算；AC 90／90）

| FR | US | AC 數 | 正向 AT | 反向 AT | 載具 | R 條文 |
|---|---|---|---|---|---|---|
| FR-IC-01 | US-IC-01 | 11 | 20 | 14 | RM、RI、RX | R-IC-01、02、03、04、05、06、07、08、09、10、11、12、19、20、21、25、36、37、41 |
| FR-IC-02 | US-IC-02 | 5 | 5 | 6 | RI | R-IC-16 |
| FR-IC-03 | US-IC-03 | 7 | 9 | 7 | RI | R-IC-17、18、19、20、28、43 |
| FR-IC-04 | US-IC-04 | 11 | 13 | 14 | RI、RX | R-IC-06、09、13、14、15、18、20、21、22、23、24、25、26、27、28、29、30、31、32、37、40 |
| FR-IC-05 | US-IC-05 | 7 | 8 | 8 | RI、FL、FV | R-IC-14、22、33、34、35、36、38、39、40、60、66 |
| FR-IC-06 | US-IC-06 | 5 | 10 | 7 | RI、BR、BI、RX、FS、BS、GT | R-IC-01、13、38、40、42、43、45、64、73 |
| FR-IC-07 | US-IC-07 | 9 | 12 | 10 | BR、ES、BU、BI、BB、GT、FL、BC | R-IC-45、46、47、48、49、50、51、52、53、61、75 |
| FR-IC-08 | US-IC-08 | 11 | 13 | 11 | FV、FL、FG、FD、FS | R-IC-37、63、64、65、66、67、68、69 |
| FR-IC-09 | US-IC-09 | 11 | 14 | 12 | BI、BM、ES、BA、FV、FP、FL | R-IC-33、53、54、55、56、57、58、59、60、61、70 |
| FR-IC-10 | US-IC-10 | 5 | 6 | 5 | FV、FS、BS | R-IC-71、72 |
| FR-IC-11 | US-IC-11 | 3 | 3 | 3 | FN、GT | R-IC-62、75 |
| FR-IC-12 | US-IC-12 | 5 | 8 | 5 | RI、BI、BR、FV、GT、E2、FP | R-IC-42、44、45、49、67、74、75 |
| 合計 | 12 | 90 | 121 | 102 | | R-IC-01～R-IC-75（75 條） |

### 6.2 行為規則與非功能（PRD §10）→ AT（R→AT 見 R 條文表的 AT 欄；下表為 NFR→AT）

| NFR | 條文 | 覆蓋 AT（AC 簡碼） |
|---|---|---|
| 唯讀與零帳本寫入、不快取 | Bridge 與 backend 每請求重算；Console 唯一寫入是順位表 | 06-1、09-8、12-3 |
| 效能 | 真帳本 ≤2 秒、單頁 ≤ 1 MB；合成規模 ≤2 秒 | 12-1 |
| fail-loud | 表外值「未歸類」；量不到「—」；缺帳本 `ne`；失敗不回空表 | 01-2、01-6、01-8、01-9、01-11、07-7、08-5 |
| 跨平台與語言 | 中文 argv 與 stdout UTF-8；介面繁體中文 | 12-2、07-2、08-1 |
| 相容 | `schema_rev` 1；既有 SI 面不變；既有測試除同步鎖外不改 | 12-4、07-6、11-2 |
| 安全 | 寫入只限 ADMIN；查詢參數衛生；純文字渲染 | 09-2、07-2、08-7 |
| 可及性 | 沿既有元件；鍵盤與 aria | 12-5 |

### 6.3 R→AC 與 AC→R 連結

R 條文表每條 R 的 AT 欄皆指向存在的 AC；PRD 的 90 條 AC 每條至少被一條 R 引用（由組裝腳本於本檔產生時檢查，缺漏＝組裝失敗）。Console 半的 RTM 回填：`AgentConsole/docs/06_quality/RTM.md` §2.4 本地子表一列，開發棒交 rtm_backfill 檔、由主控回填。

## 7. 本檔採用的預設裁決與開放問題（掌舵者可推翻；推翻走 T1 或本檔修訂，凍結前由主控回報掌舵者）

### 7.1 預設裁決（本檔已定案；可推翻）

| # | 裁決 | 預設（出處） |
|---|---|---|
| 1 | 游標基數與編號超出範圍的處置 | S＝10,000,000；≥S 者不成議題、`ROW-ARITY`（D-R4） |
| 2 | `closed` 提案的生效結果量不到（無窗或注入構造；`fold` 不讓 closed 帶 pending） | 判序：已回滾先於量不到；量不到→已完成、「未歸類：closed」、`UNMAPPED`（D-R9、R-IC-19；§7.3 第 3 點） |
| 3 | 已決定與已消耗回滾的計法 | `decided`（seq>promote_seq 的 `dec(rollback)`）、`pending`、`consumed`＝差（D-R3） |
| 4 | CLI 文字表頁內顯示序 | 依 `--status` 選規則一或二，只排本頁（D-R6） |
| 5 | 姊妹軌欄數不符的列 | 不採用並 `ROW-ARITY`（R-IC-15） |
| 6 | `ne.field` 命名 | `ledger.*`、`issues.<ID>.<欄>`（D-R10） |
| 7 | 夾具檔與跨檔取用 | 不新增輔助檔；`issuemap` 測試 import `test_selfimproving_issues`（D-R11） |
| 8 | 缺陷嚴重度取法 | 欄首略過空白、`*`、`_` 後的 `P`＋數字（R-IC-05） |
| 9 | 提案 `raw` 欄位集合 | 提案卡、狀態、路由、類別、動作、修訂、摘要碼、來源項目（R-IC-29） |
| 10 | 空字串 `status=` | 不特判，照傳→rc 3→503（D-C2） |
| 11 | 409 的 `details` 與訊息 | `{id, status}`；訊息逐字「此議題目前的狀態不能設定優先順序」（D-C5） |
| 12 | PUT 的 `note: null` 與型別不符 | 422（B-17） |
| 13 | 前端關鍵字比對 | 不分大小寫（ASCII）子字串、只篩已載入頁（B-21） |
| 14 | 延後列處置附加文字為空 | 「等再開症狀出現：（帳本未寫明）」（R-IC-31） |
| 15 | AC-IC-09-6 的容器重啟 | Migration IT＋Docker 全棧實機證據雙載具（D-C10） |
| 16 | 審查核對型 AC（07-8、11-2、12-4） | 以 G-C4、G-C5、G-C6 審查閘承載（非單元測試） |
| 17 | AC-IC-07-2「Windows 與 Linux 皆測」的取捨 | Windows 側只覆蓋 Bridge→CLI 這一層（AT-IC-07-2-1 於本機 Windows 與 CI Linux 皆跑；根層 AT-IC-12-2-1 於 windows-compat-ci 與 macos-compat-ci 跑）；console-api→Bridge 的編碼是平台中立的純字串運算（AT-IC-07-2-E-2，任何平台相同）；全鏈（AT-IC-07-2-2）只在 Docker（Linux）；Windows 原生同時起 Bridge 與 backend 不是既有 CI 形態，不列 |
| 18 | PUT 本文承接與狀態碼 | `JsonNode` 承接、型別與值域不符一律 422、只有非 JSON 物件才 400（D-C13） |

### 7.2 開放問題與預設（凍結前由主控回報掌舵者）

| # | 問題 | 預設 |
|---|---|---|
| Q1 | 任務書的測試類名（`IssueControllerTest`、`IssuePriorityIT`）與 PRD §9（`IssueApiIT`、`IssuePriorityArchTest`、`IssueReasonsContractTest`）不同，用哪組？ | 以 PRD §9 為準；另新增 `IssuePriorityMigrationIT`、`IssueBridgeArchTest`、`IssueStaticLockTest` |
| Q2 | PRD §9 把 AC-IC-01 整組指給 `test_selfimproving_issuemap.py`；需 repo 夾具的 FR-IC-01 AT 是否放 `test_selfimproving_issues.py`？ | 放 `issues` 測試檔；`issuemap` 測試只放純表 AT（01-1、01-4 的函式與子集鎖、01-7 的字典鎖） |
| Q3 | compat-ci `paths` 只列要加的四個路徑、位置由 `test_ci_paths_cover_root_consumers.py` 紅綠決定？ | 同意 |
| Q4 | `issues-docker.stack.ts` 是否進 CI？ | 不進；只在 SCG-5 留實機證據 |
| Q5 | Docker 全棧 e2e 的環境（docker compose、金鑰）掌舵者機器是否具備？ | 具備（沿 `p9-w7-docker.stack.ts` 先例） |
| Q6 | `PillTabs` 的方向鍵行為是否另立規格？ | 不另立，沿既有元件 |
| Q7 | Playwright mock 路由放 `mockApi.ts`（改既有檔）或 spec 內自帶？ | spec 內自帶（不改既有 `mockApi.ts`） |
| Q8 | 效能 2 秒門檻在慢速 CI 是否放寬？ | 不放寬（PRD 原文）；若 CI 出現偽陽性再走勘誤 |
| Q9 | 根層新測試檔以 2 支為上限下，規模夾具產生器與兩支檔的重釘稅由誰承擔？ | 收尾單人窗口一次重釘（鐵律七）；若逼近單輪淨額上限，走一次性例外名冊（先例：SelfImproving P0 的 +2,196，上限 4→5 可見上修） |
| Q10 | `lib/domain/issues.ts` 是否納入 `vitest.config.mts` 的 `coverage.include`（現列的是單元測試負責的邏輯層，先例 `lib/domain/sdd.ts`）？ | 納入（單行加入，列入 §5.7 Console 表；門檻 lines 70、statements 70、functions 70、branches 60 不動）；`lib/api/endpoints.ts` 已在 include，四個新函式須被至少一個測試實際呼叫（fetch 替身） |

### 7.3 PRD 修訂建議（凍結檔不改；列此供 T1 或 PRD 修訂）

1. 任務書稱 AC 共 85 條；PRD v1.0 經三輪審查為 90 條。本檔以 PRD 為準（90／90）；引用「85」的任務書與帳本處應更正。
2. 任務書稱能力登記在 `check.py`；實況是 `tools/tests/test_selfimproving_capability.py:30` 的 `CAPABILITY` 字典（`check.py` 無此登記）。PRD §9 連動面寫對，本檔 5.7 以實況為準。
3. PRD §4.2 的 `closed` 提案列只涵蓋 clean、recurred、rolled-back 與「量不到」，未說明 `pending` 窗。實況：`fold` 讓 pending 窗的提案停在 `measuring`（`mea.close` 結果為 pending 時狀態仍是 measuring，`mea.amend` 自 pending 落定才轉 closed），所以 closed 不會自然帶 pending，「量不到」只由事件異常（無窗）或注入縫構造觸發，PRD 列沒有缺口；建議 PRD 勘誤在「量不到」列補一句此前提（pending 窗的提案屬觀察中，進度顯示於下一步）。本檔 D-R9、R-IC-19 的判序：已回滾先於量不到。
4. PRD AC-IC-04-8 稱「檔內 1 起算行號」；`defs.load_rows` 以 `splitlines()` 走訪，含 U+0085、U+2028 等分隔字元的帳本檔會與編輯器行號不同。本檔 D-R7 沿既有走訪、夾具不含此類字元；建議 PRD 註明「以 `load_rows` 走訪序號為準」。
5. PRD §9 的測試檔分配（見 Q2）：建議改寫為「`issuemap` 測試承載純表 AT，需 repo 夾具的 FR-IC-01 AT 在 `issues` 測試」。
6. PRD §9〈待 TCS 階段核對〉已全數結案：既有鎖行號與值（2026-10-27 重核吻合）、`ListChecks` 存在且與原七個圖示互異、`closed` 提案的回滾計法＝D-R3、姊妹軌表頭與行號＝D-R8、游標編碼＝D-R4、compat-ci 精確清單以 `test_ci_paths_cover_root_consumers.py`（實住 `AISDLC_SDD/scripts/tests/`）為準。
7. PRD AC-IC-07-8、11-2、12-4 是審查核對型、AC-IC-09-6 含容器重啟：本檔以 G 編號審查閘與 Docker 全棧載具承載（見 §3 的 `GT`、`ES`），不寫成單元測試。
8. PRD §6.4 未明寫 PUT 的 `note: null` 與 `rank` 型別不符（字串、小數）的狀態碼；本檔 B-17 取 422（不是 400）。
9. PRD §5.1 的 `raw`（提案）只寫「提案卡全文加原值（狀態、路由…）」；本檔 R-IC-29 定為八項，建議 PRD 勘誤列全。
10. PRD §4.6 只把「檔缺或不可讀」列為帳本不可用；缺陷主檔或姊妹軌「存在但表頭被破壞」會使整本議題無聲消失、摘要顯示成「0 件」，與 fail-loud 精神相違。本檔 D-R13、AT-IC-01-8-E-2 將無合格表頭一併視為不可用；建議 PRD 勘誤補入。
11. 任務書 §必含內容 4 的「`git diff --stat -- docs/06_quality/` 為空」與收尾重釘（會寫 `docs/06_quality/` 證據檔）衝突；本檔拆成 G-C2（開發階段整個 `docs/06_quality/` 零差異）與 G-C3（任何階段七個帳本路徑零差異）。

## SCG-4 通過標準

**通過條件**（全部成立才算過；審查報告逐字貼各 G 指令的 rc 與輸出尾段）：

1. **AC 90／90**：每個 AT 的判定指令 rc 0 且收集 ≥1 個測試（§2 零測試規則）；審查閘型 AT 以所指 G 編號指令的輸出為證。
2. **兩半閘門全綠**：根層 G-R1～G-R14、Bridge G-B1～G-B3、backend G-K1～G-K2、frontend G-F1～G-F6、共同 G-C1～G-C6；收尾窗口另跑 G-R15。
3. **突變**：R 條文表的 R-IC-01～R-IC-75 每條至少一個突變轉紅（killed）；倖存者補 AT 並勘誤。
4. **四道差分**：Bridge↔CLI（AT-IC-07-1-1）、console-api↔黃金檔（AT-IC-07-4-1）、`issues --json`↔`export`（AT-IC-06-2-1）、`meaplan.rollback_pending`↔議題（AT-IC-03-7-2）。
5. **出口判準（PRD §11）**：階段一 (b)＝G-R10 獨立算法對帳（`summary.by_status` 與只用文字處理的計法逐項相等，`problems` 為空或逐筆對得到真實異常列；2026-10-26 參考值：總數 597＝待處理 2、待您決定 0、延後 51、已完成 544，凍結日重算）；(c)＝G-C3；(d)＝AT-IC-01-1-*。
6. **SCG-5 實機證據（掌舵者）**：階段一 (a)（不看英文答出三問）；階段二 (a) 排序→處理→完成、(b) 決定在稽核檔與事件帳本都查得到且無旁路、(c) 非 ADMIN 看得到按不到且網路層零寫入、(d)＝AT-IC-09-6-2 重啟後順位仍在；同一次實機另留 AT-IC-07-2-2（console-api 全鏈中文篩選）。
7. 無 P1、P2 未結；凍結與放行依根 CLAUDE.md〈凍結常態規則〉與 BRIDGE §8。

**閘門指令**（`<repo>`＝monorepo 根，現查 `git rev-parse --show-toplevel`；`<base>`＝開發棒開工時的 HEAD，由主控在任務書寫明；`<snap>`＝同一時刻 `git status --porcelain -uall` 的輸出檔，由主控存檔並在任務書寫明路徑；每條在「目錄」欄執行；PowerShell 形態、rc 先存變數再讀；不得裸 `cd`；shell 狀態不跨呼叫，所以 Python 閘門的 venv 啟動必須與指令在同一呼叫內）：

```powershell
# Python 閘門（根層、Bridge）：同一呼叫內先啟根 venv
Push-Location <repo>\<目錄>; & <repo>\.venv\Scripts\Activate.ps1; $o = & <指令與參數> 2>&1; $rc = $LASTEXITCODE; Pop-Location; "rc=$rc"; $o | Select-Object -Last 20
# backend、frontend、git 閘門：不需 venv
Push-Location <repo>\<目錄>; $o = & <指令與參數> 2>&1; $rc = $LASTEXITCODE; Pop-Location; "rc=$rc"; $o | Select-Object -Last 20
# git status 閘門（G-C1～G-C4；G-C2～G-C4 在 -uall 後加 -- <路徑>）：輸出逐行去掉 <snap> 已有的行，剩下的才判定（既有髒檔不計）
$snap = Get-Content -LiteralPath <snap 檔> -Encoding utf8; $o = git -C <repo> status --porcelain -uall; $rc = $LASTEXITCODE; "rc=$rc"; $o | Where-Object { $snap -notcontains $_ }
```

| G | 目錄 | 指令 | 期望 |
|---|---|---|---|
| G-R1 | `<repo>` | `python -m unittest discover -s tools/tests -p "test_selfimproving_issues.py"` | rc 0、≥1 測試 |
| G-R2 | `<repo>` | `python -m unittest discover -s tools/tests -p "test_selfimproving_issuemap.py"` | rc 0、≥1 測試 |
| G-R3 | `<repo>` | `python -m unittest discover -s tools/tests -p "test_selfimproving_p3_meta.py"` | rc 0（同步鎖） |
| G-R4 | `<repo>` | `python -m unittest discover -s tools/tests -p "test_selfimproving_export_status.py"` | rc 0 |
| G-R5 | `<repo>` | `python -m unittest discover -s tools/tests -p "test_selfimproving_*.py"` | rc 0（全 SI 根層測試，含 capability、console_obs） |
| G-R6 | `<repo>` | `python -m ruff check <本功能改到的 .py 檔>` | rc 0 |
| G-R7 | `<repo>` | `python -m ruff check --isolated --select E501 --line-length 100 --output-format concise tools/tests/test_selfimproving_issues.py tools/tests/test_selfimproving_issuemap.py` | 無輸出（新長行 0） |
| G-R8 | `<repo>` | `python tools/selfimproving.py check` | rc 0、33 項、無 FAIL |
| G-R9 | `<repo>` | `python tools/selfimproving.py issues`；再 `… issues --json` 以 `json.loads` 解析 | rc 0；末行「共 N 件；問題 M 筆」 |
| G-R10 | `<repo>` | QA 獨立算法腳本（scratchpad；不 import `issues.py`；只用文字處理計各處置首詞與缺陷狀態首詞）對帳 `summary.by_status` | 逐項相等 |
| G-R11 | `<repo>` | `python AutoClaude/tools/check_loc_budget.py --json` | `issues.py`、`export.py` 在 `tools/lib` 分級內無違規 |
| G-R12 | `<repo>` | `python -m pytest AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py -q -p no:xdist -o addopts=` | rc 0 |
| G-R13 | `<repo>` | `python -m unittest discover -s tools/tests -p "test_root_module_layout.py"` | rc 0（落點鎖） |
| G-R14 | `<repo>` | `git diff --exit-code <base> -- docs/06_quality/SelfImproving_Protocol/params.json` | 無差異 |
| G-R15 | `<repo>` | `python tools/run_root_unittests.py`（收尾單人窗口；重釘後再跑一次） | rc 0 |
| G-B1 | `<repo>\AgentConsole\engine-bridge` | `python -m ruff check .`；再於 `<repo>` 跑 `python -m ruff check AgentConsole\engine-bridge`（各一次呼叫，皆先啟 venv） | 兩視角各 rc 0 |
| G-B2 | 同上 | `python -m pytest -q` | rc 0（含既有 `test_si_*`） |
| G-B3 | 同上 | `python tests/si_golden_regen.py`，再跑一次 | 第二次全為 `same`；三份副本位元組相同 |
| G-K1 | `<repo>\AgentConsole\backend` | `.\gradlew.bat clean build` | BUILD SUCCESSFUL（含 ArchUnit、Flyway＋validate、JaCoCo ≥80%） |
| G-K2 | 同上 | `.\gradlew.bat test --tests "*Issue*"` | rc 0、≥1 測試 |
| G-F1 | `<repo>\AgentConsole\frontend` | `npm run lint` | rc 0 |
| G-F2 | 同上 | `npx tsc --noEmit` | rc 0 |
| G-F3 | 同上 | `npm run test:cov` | rc 0（含 `si` 目錄與導覽測試）；覆蓋率文字表含 `lib/domain/issues.ts` 列（`lib/domain` 目錄段下的 `issues.ts`）；`vitest.config.mts` 的覆蓋率門檻 lines 70、statements 70、functions 70、branches 60（`lib/domain/issues.ts` 納入 include，Q10） |
| G-F4 | 同上 | `npm run build` | rc 0 |
| G-F5 | 同上 | `npx playwright test tests/e2e/issues.mock.spec.ts tests/e2e/shells-and-layout.spec.ts` | rc 0（導覽斷言複核） |
| G-F6 | 同上（backend 在線） | `npm run gen:api` | `schema.d.ts` 差異只含 issue 相關 |
| G-C1 | `<repo>` | `git status --porcelain -uall`（含未追蹤檔並逐檔展開；開發棒階段尚未 commit，各半各取一次；已 commit 後改 `git diff --name-only <base>..HEAD`） | 以開工前快照相減；既有髒檔（例 `AutoClaude/.perf_baseline.toml`）不計；餘下每個路徑 ⊆ §5.7 對應半的表 |
| G-C2 | `<repo>` | `git status --porcelain -uall -- docs/06_quality/`（開發階段） | 相減後為空 |
| G-C3 | `<repo>` | `git status --porcelain -uall -- docs/06_quality/SelfImproving_Observation_Ledger*.md docs/06_quality/AutoSDD_Defect_Log*.md docs/06_quality/AutoSDD_External_Blocked_Log.md docs/06_quality/AutoSDD_Structural_Debt_Log.md docs/06_quality/SelfImproving_Event_Ledger.jsonl docs/06_quality/SelfImproving_Proposals`（任何階段；已 commit 後另跑 `git diff --stat <base>..HEAD --` 同七路徑） | 相減後為空 |
| G-C4 | `<repo>` | `git status --porcelain -uall`（含未追蹤；以快照相減）與已 commit 後的 `git diff --name-only <base>..HEAD`，各篩 `reasons.ts`、`API_Contract_P3-6.md`、`Architecture.md` | 無輸出（AC-IC-07-8；自證負控見 AT-IC-07-8-E-1） |
| G-C5 | `<repo>` | `git diff -U0 <base> --` 既有測試檔（§5.7 各「同步鎖」列所列檔） | 人工核對：每 hunk 只動釘值或預期清單；被刪 assert、expect、assertThat 行＝0（AC-IC-11-2、12-4） |
| G-C6 | `<repo>` | `git diff --exit-code <base> -- AgentConsole/frontend/components/layout/ToolsRegion.tsx` | 無差異（AC-IC-11-3） |

## 勘誤（本檔凍結之後的訂正；凍結前留空）

（凍結前留空；凍結後依〈凍結後修訂路由〉走對應的鍵 refreeze，並於此逐條附新 digest。）
