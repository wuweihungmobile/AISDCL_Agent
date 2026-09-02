# CrossPlatform R121 技術債結案證據檔

> 輪籤：R121（技術債總清償循環令第四投；純結案輪／收尾單人窗口）
> 範圍：掌舵者 2026-09-02 裁「降帳本」，採呈報單 `docs/04_planning/AutoSDD_Adjudication_Packet_R121.md`
> 推薦。本輪對 10 筆 closed-by-decision 候選逐筆對抗式證偽（工作流 wf_5d8ebbc6-3d3，
> 每筆一個高強度證偽員查四道：矛盾列／殘留子項／依據真實性／狀態首詞合法），
> **9 筆存活結案、1 筆（DEF-200-065）被駁回維持 open**。本檔逐節記各筆裁決依據與
> 證偽當回合親查的座標；帳本列只放索引，詳情在此（依 Playbook §4.6）。

## §裁決總覽

| DEF-ID | 裁決 | 證偽四道結果 |
|---|---|---|
| DEF-200-213 | **維持 open（卡 DEF-200-241）** | 實質已解但形式結案觸發凍結時鐘死結，見 §DEF-200-213 |
| DEF-101-610 | closed-by-decision | 同上 |
| DEF-101-863 | closed-by-decision | 同上 |
| DEF-101-867 | closed-by-decision | 同上 |
| DEF-101-926 | closed-by-decision | 同上（註冊處實測 8 處，帳本原記 9 已訂正） |
| DEF-101-060 | closed-by-decision | 同上 |
| DEF-200-084 | closed-by-decision | 同上 |
| DEF-200-155 | closed-by-decision | 同上 |
| DEF-200-191 | closed-by-decision | 同上 |
| DEF-200-065 | **駁回，維持 open** | 殘留子項①（見 §DEF-200-065-駁回） |

---

## §DEF-200-213

**裁決：維持 open——實質已解、形式結案被 DEF-200-241 凍結時鐘死結卡住。**

證偽四道本身全過（矛盾列 none、無殘留、依據真、首詞合法）：`TestDef200195CrossRowReceiptFreshnessIsNotSelfSatisfied` 現查 4 passed（②已落地）、`check_defect_log_crossref.py` 輸出全 ✅、殘留待辦現值 0（③無可拆對象）；①（F3／F4）屬觀察級可改判 advisory。

**但形式結案觸發連鎖紅**（本輪實測，非預想）：本列被 `CrossPlatform_R100_Scan_Findings.md:103／:305` 兩行前瞻交棒行（「交由 R101 … DEF-200-213」）指名。`check_handoff_carriers.py` 判準② 要求前瞻行指名的 DEF-ID 必須是**未結列**；一旦本列結案，那兩行失去承接目標 ⇒ rc=1。出口二選一皆不可行：①補承接列＝重開已解的列；②登記進 `_CARRIER_DOC_EXEMPTIONS`＝該表已滿 5 筆（shrink-only，D8 明文「不得援引為再調高的先例」）。這正是 DEF-200-241 描述的「凍結時鐘 × 豁免 shrink-only 相乘」死結的又一次具體發生。

**處置**：維持 open，狀態欄註明實質已解＋卡點。DEF-200-241 治本（祖父化改讀結案事實）落地後，`R100_Scan_Findings.md` 那兩行會自動出局，本列隨之可結。教訓：對抗式證偽的四道未涵蓋「結案是否令他處前瞻行失承接目標」，下輪證偽應補此第五道。

## §DEF-101-610

**裁決**：closed-by-decision。「同輪並行修復包互不知情致設計文件前提失效」失效模式，已由 ADR-XPLAT-002 §9.1 的 SC-1～SC-10 機械承接。

**證偽親查**：矛盾列＝none；非多子項併列（①②③為解鎖條件）；依據真：`tools/tests/test_adr_xplat001_c1c2_lock.py` 的 SC-1～SC-10 共 10 條 Check（:5094-5103），本場實跑 `TestSection91InvariantsAreLive`／`HaveTeeth`／`SpecIsBoundToTheseLocks`＝16 passed／59 subtests passed，模組由 `run_root_unittests.py` discover 消費。

**依據**：四次復發（610／615／626 及訂正句自身）全在同一份 ADR，該檔十條可轉紅不變式已進 pre-push；通用跨設計文件「前提清單重跑」機制（方向 B）無第二案例佐證，屬過度設計而婉拒。若日後出現第二份文件同型失效另立新列。屬合法改判型結案（帳本 R68 回執曾以①③未達成維持 open，本輪以裁決權認定單一文件已被 SC 承接）。

## §DEF-101-863

**裁決**：closed-by-decision。skip reason「未啟用 vs 缺件」不可分辨的訴求已由標籤族兌現。

**證偽親查**：矛盾列＝none（`CrossPlatform_R113_Ledger_Closure.md:110` 為支持性延後註記非相反裁決）；單一訴求無殘留；依據真：`tools/lib/skip_tag_policy.py:52-76` 確含 `[TOOL-ABSENCE]`／`[ENV-DISABLED]` 兩標籤族常數，`test_pgvector_hnsw_recall.py:163-166` 實證純形式可操作性判準會放行「指名不存在通道」的假指路。

**依據**：「輸出面把未啟用與缺件分開」已由標籤族＋`skip_group` 分群兌現，四棵樹 census 由相等棘輪看守；解鎖條件後半「reason 內容鎖」明文撤回（字面鎖是已證的假安心判準）。分母訂正為靜態站點 133，非 R76 runtime 計數 224。

## §DEF-101-867

**裁決**：closed-by-decision。帳本內部矛盾偵測器不建。

**證偽親查**：矛盾列＝none（R82 收尾同向「不上、先降訊噪比」）；單一訴求無殘留；依據真：`CrossPlatform_R76_Scan_Findings.md §R76-FIX-6` 逐字載明原型對真帳本命中 9 列、真陽性僅 2~3 列（訊噪比約 25%）、零白名單慣例；`R85` 同族判例採同方向；原始矛盾已由 `DEF-101-856`① 收尾註記「該檔已刪，Test-Path 回 False」訂正。

**依據**：同族啟發式一律走「提高訊噪比」而非新建偵測器；提案至今無人量出真陽性率達標數字。若日後量出 ≥80% 可重議。

## §DEF-101-926

**裁決**：closed-by-decision。兩支 monorepo 級 hook 橋接架構維持現狀。

**證偽親查**：矛盾列＝none（互參皆為改派與 R80 S5-09「EOL 那一對是合理雙層」支持性裁決）；單一架構訴求無殘留；依據真：親查根 `.claude/settings.json` 4 條橋接（`check_ps1_encoding`／`check_sh_eol`）＋`AutoClaude/.claude/settings.json` 4 條＝實測 8 處；根 `CLAUDE.md` 機械守衛總表兩列皆逐字含「橋接自 AutoClaude tools/hooks」。

**依據**：兩支 hook 續住 `AutoClaude/tools/hooks/`，根 settings.json 橋接視為既有設計；功能面零收益、搬家將重新引入全域 PreToolUse 註冊變動風險、既有鎖已釘住文件與註冊一致性。帳本列原記「9 處」為過時，實測 8 處已訂正。

## §DEF-101-060

**裁決**：closed-by-decision。依賴版本上限採政策式處置。

**證偽親查**：矛盾列＝none（`CrossPlatform_R99_Ledger_Closure.md:98`「依賴債未清前不得結案」針對 DEF-101-876 非 060，且 876 已於 R107 closed-by-decision，R107 明言「殘餘由 DEF-101-060 單一載體承接」為 060 處置鋪路而非禁止）；單一主題無殘留；依據真：親查 `AutoClaude/pyproject.toml` 仍約 18 條純下限宣告，已鎖上限者僅 `setuptools<81`／`keyboard`／`mako<1.4`／`hypothesis==6.156.6` 四個曾炸過 CI 者；`hypothesis<7` 無效反例（PyPI 從未發行 7.x）。

**依據**：政策「僅對實際炸過 CI 的套件釘版本上限，其餘維持下限讓每次 pip resolve 當提早偵測器」；歷次改派（R81→R82→R99→R107）後數十輪零人動工，顯示逐一鎖版與白名單機械物成本不成比例。`DEF-101-876` 依賴債列一併解耦。

## §DEF-200-084

**裁決**：closed-by-decision。跨 session stash 事故維持「偵測而非阻斷」姿態。

**證偽親查**：矛盾列＝none（DEF-200-194「不可結案」針對 134 不同標的）；單一訴求無殘留（方向 A repo 租約已依成本效益否決）；依據真：AST 確認 `stash_ref_sentinel()` 定義於 `block_destructive_git.py:815`、主流程呼叫 :1294、return 1 if note else 0（出聲不阻斷）；根 `CLAUDE.md`〈可重啟點〉stash create+tag 保全成文於 :110／:218。

**依據**：租約僅能再約束同 project root 且經 CC 載入 hooks 的 session，本 hook 對此類已能攔截；真正攔不到的是不同 project root 或非 CC 工具的 session，租約成本高於其能補的縫。殘留風險明文登記為結構上不可攔。

## §DEF-200-155

**裁決**：closed-by-decision。接受「平台切換首次開工必重釘 skip 天花板」為既定儀式。

**證偽親查**：矛盾列＝none；殘留＝false（方案-2 已明文記為結構性候選、定觸發條件，屬已裁定延後非未裁）；依據真：`SKIP_GROUP_PLATFORM` 現值 41 於 `_RUNTIME_SKIP_CEILING`（:402）與 `_RUNTIME_SKIP_CEILING_MAX`（:543）兩表皆 41（37→41 已落地）；`test_skip_ceiling_ratchet_direction.py` 的 P1-6 段親跑 13 passed（含成對性斷言 `test_both_raised_together_is_still_caught`）。

**依據**：本列 P3「判準的結構性後果、非程式缺陷」；`skip_group_policy.py` 表規則已明文「同 commit 改兩常數＋寫理由」SOP；`P1-6` 共同變更鎖已機械化成對性。方案-2（計數→test-id 集合）記為結構性候選，觸發條件＝同剖面連續 N 次切換重釘，效益無法單平台驗證，屬 Architect 級取捨。

## §DEF-200-191

**裁決**：closed-by-decision。「錨不到＝放行」的鮮度判準維持計數＋出聲、不升級為違規。

**證偽親查**：矛盾列＝none（主檔＋archive 零反向裁決）；單一訴求無殘留；依據真：`check_claim_provenance.py:147-149` 明文散文平面無法區分捏造與輸出截斷、:151「這不是修好那個盲區，是讓它有數字」＝設計終態；`stale_pace_hits()` 對 `unanchored` 只 append 不 continue 不判違規（`_pace_messages()` 出 ℹ️ 計數非 🔴 違規）。

**依據**：散文平面結構性無法區分捏造與輸出截斷，全轉違規將製造大量假紅（錨不到率 1.2%~31%，母體定義不同）；檔頭已自陳「讓它有數字」為設計終態。「引述須帶量測時間戳」的輸入面約束改由 `DEF-200-203` 的斷層判準承接，不在本列重複立約束。

---

## §DEF-200-065-駁回（維持 open，未結案）

**證偽判決：refuted=true（殘留子項①未乾淨撤回）。** 本列為①②③併列：
- ②（`skip_group_policy.py` 曾 399/400 貼牆）現查 362/400，已緩解；
- ③（`quota_ledger.py:6` 散文數字失實）現查已對齊現值 1089，已修；
- **①（skip_* 六模組收斂成政策／掃描／門面三支的重構）自 R84「只登記診斷、未動工」，經 R95→R98→R101 改派，R89 明文「①②仍在故不結」（`CrossPlatform_R89_Closure_Evidence.md:1864`）——從未動工。**

呈報單以 wontfix 撤回①，論據「固定成本大於內容動機已不成立」**經證偽駁回**：ARCH-09 原始症狀正是「小模組固定成本＞內容」，而 `skip_source_io.py` 現值 18 loc 比立案時 35 loc **更小、更符合**該症狀；呈報單把「②貼牆已解」誤混為「固定成本＞內容已解」，屬把部分子項可結（②③）擴張成整列可結。

**處置**：維持 open。①要嘛真做六模組收斂重構（L 級架構，需動 `check_loc_budget.py` 常數）、要嘛另備一個站得住的 wontfix 論據（不能用「②貼牆已解」代替「①重構動機消失」）。②③現值訂正已隨本輪順帶查明，記於此供下一結案窗口參考。
