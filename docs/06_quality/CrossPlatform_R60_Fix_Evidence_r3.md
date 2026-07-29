# 跨平台相容性 R60 — 修復證據全文（round 3）

> **本檔是 `CrossPlatform_R60_Fix_Evidence.md` 的姊妹檔**，承載 R60 **round 3** 的逐字證據
> （`DEF-101-568` ~ `DEF-101-586`，共 19 節）。拆分理由與對照表見**入口檔**
> `CrossPlatform_R60_Fix_Evidence.md` 開頭（`DEF-101-587`）。
>
> **本檔內容為逐字搬移，非重寫**：拆分時以「兩檔位元組總和 == 原檔位元組 + 新增檔頭與
> 對照表」機械驗證，搬移的每一個位元組都與拆分前相同。

## DEF-101-568

**現象（四方 findings：`SD-R60-R2-05` ①②③、`SA-R60R2-04` ③、`ARCH-R60R2-04` ⑤、`SD-R60-R2-06` ⑤）**：
round 2 才落地的 ADR C1/C2 機械鎖 `tools/tests/test_adr_xplat001_c1c2_lock.py` 自身有五項實質缺陷。

1. **日界對本輪自己的產出無效**：`_BASELINE_FROZEN_AT = "2026-07-28"` 搭配嚴格 `>`，而本輪新列的發現日期恰為同一天，
   於是檔頭宣稱的「日界之後的新列在結構上不可能被塞進基線」對本輪產出完全不成立。
   SD 實測：造一筆同日合成列、登記進豁免表、上限 +1 ⇒ 全綠；把日期改成隔天才紅。
2. **`shrink-only` 是人審慣例而非機制**：只斷言「筆數 ≤ 上限」，所以把上限改大不會紅。
   SD 實測 `_MAX_BASELINE_ENTRIES` → 9 不紅、→ 7 才紅（後者是因為實際筆數超過上限，不是因為「調升」被偵測）。
3. **archive 是繞道面**：掃描面只有主檔，而落入 ADR §4.3.1 的列典型狀態是 `wontfix`，
   那正是 `archive_defect_log.py` 判準① **允許搬遷**的狀態 ⇒「新增違規列 ＋ 同輪歸檔」可整條繞過硬擋。
4. **`_MIN_LEDGER_ROWS = 60` 餘裕見底**：主檔列數會因歸檔而結構性下降，下限釘在主檔就必然反覆重釘。
5. **自己違反自己訂的紀律**：該檔宣告「筆數不寫在散文裡」，卻在幾十行後自己寫死三處
   （豁免筆數、帳本列數、「一次紅 N 個」）。

**修法**：

- ① 移除日期日界，改為與日曆脫鉤的 `_BASELINE_ID_CEILING = "DEF-101-526"`（＝ADR 落地前的最後一筆帳本列），
  判準改用 `(輪次, 流水號)` 字典序；另補一條輔助判準「登記列的發現日期不得晚於上界列自身日期」，
  上界列的日期**自帳本現查**而不寫死。此設計沿用 `ADR-SD09-011` 的既有先例（把證據從日曆解綁、改綁源碼演進證據）。
- ② 新增 `read_previous_self_source()`（以 `git show HEAD:<鎖檔>` 取上一版自身原始碼）＋ `ratchet_problems()`，
  同時看守 `_MAX_BASELINE_ENTRIES` 與 `_BASELINE_ID_CEILING`；常數被改名時抽不到值，一律**紅而非略過**。
  HEAD 尚無本檔時 `skipTest`，並由 `run_root_unittests.py::report_all_skips` 逐處印出理由（非靜默）。
- ③ 掃描面擴到帳本家族全檔，家族枚舉一律 **import `archive_defect_log._family_files()`**（未自寫 glob），
  並訂「ADR 落地後的新列不接受豁免登記，搬進 archive 也一樣擋」。
- ④ 刪 `_MIN_LEDGER_ROWS`，改 `_MIN_FAMILY_ROWS = 665`（家族總列數下限；家族受「只增不刪」＋搬遷守恆保護，餘裕只增）。
- ⑤ 三處全改為不引數字（**刻意不把舊數字改成新的正確值**——那只是把過期時點往後挪一輪），
  並新增 `_BARE_COUNT_RE` 自檢掃自己整檔是否出現「阿拉伯數字＋筆／列／個／支／處」，含假陽性對照組
  （`§9 列` 這種節號引用不得誤報，以 `(?<![§\d])` 排除；實作時真的踩到過）。
  `_OLD_ROW_C2_OWNER` 等三筆 owner 由「下次觸及本列的輪次」改為「承接輪次：**未指派**（觸發點＝…）」形態。

**Pkg-P5 獨立重驗（逐條實跑，非採信任務書）**：

```
python -m unittest tools.tests.test_adr_xplat001_c1c2_lock   → Ran 44 tests / OK (skipped=1) / REAL_RC=0
```

以生產物件實算（`sys.path.insert(0,'tools')` 後直接呼叫該模組公開函式）：

```
_BASELINE_ID_CEILING = DEF-101-526     _MAX_BASELINE_ENTRIES = 8
len(_BASELINE_WAIVERS) = 8             _MIN_FAMILY_ROWS = 665
archive_defect_log._family_files()     → 32 檔
audit_family(read_family(), read_onboarding()) → 落入 §4.3.1 共 13 筆：
  DEF-101-003/004/019/020/040/359（主檔，unmet=C2）、DEF-101-324（主檔，unmet=C1）、
  DEF-101-393（主檔，unmet=C1+C2）、DEF-101-056/057/534（主檔，unmet 空）、
  DEF-43-011（archive_01，unmet=C1+C2）、DEF-101-357（archive_22，unmet=C1+C2）
hard_block_offenders(result, _BASELINE_WAIVERS) → {}      ⇒ 擴面零假紅
```

兩筆 archive 側 unmet（`DEF-43-011`、`DEF-101-357`）**皆遠早於上界 `DEF-101-526`**，依設計不追溯 ⇒ 擴面未造成任何假紅；
換句話說**繞道面尚未被利用**，本次是先把門關上。
ADR §4.3.4 側雙向綁定亦實查吻合：該節第 254 行寫「**ID 上界**＝`DEF-101-526`（鎖內 `_BASELINE_ID_CEILING`）」，
第 267~268 行寫 shrink-only 棘輪「由鎖以 `git show HEAD:<鎖檔>` 取上一版常數機械比對，調升即紅」。

**🔴 刻意不修的殘留（已寫入該檔 docstring 邊界段，不是隱藏缺口）**：

1. ID 上界＋日期輔助判準擋不住「回填一個未用過的舊號碼、且同時回填一個舊日期」的**雙欄位造假**。
2. 棘輪在本鎖檔的**首個 commit 上空轉**（HEAD 無上一版可比）；實測本輪確實走 `skipTest` 分支，
   理由逐字為「HEAD 尚無 `tools/tests/test_adr_xplat001_c1c2_lock.py`（本檔為未提交的新增檔）⇒ 無上一版可比，
   棘輪本輪空轉；commit 後即永久生效。鑑別力見 `test_raising_either_constant_is_detected`」。
3. ADR 落地前的 archive 列**設計上不追溯**（有 `test_pre_adr_archive_row_is_out_of_scope_by_design` 對照組明文劃界）。

**Pkg-P5 實查結論**：五項缺陷與五項修法全部證實。**唯一未能證實者＝「該鎖 25 → 44 支」的「25」**——
該檔目前是 untracked 新增檔（`git status` 為 `??`，且鎖自己的 skip 理由即載明 HEAD 無此檔），
故 round 2 的支數無法從 git 取證；44 支為本包實測值。
另訂正任務書一處轉述：`_MIN_FAMILY_ROWS = 665` 被描述為「＝家族總列數」，實測 `family_row_total()` 在
本包寫入前為 671、寫入後為 683 ⇒ 665 是**釘選時點的值、現作為下限**，並非「當前總列數」。

## DEF-101-569

**現象（`ARCH-R60R2-01`／`SA-R60R2-01`／`SD-R60-R2-01`／`QA2-R60-03` 四方全數獨立命中，本輪收斂度最高的一組之一）**：
歸檔索引涵蓋性零判準。磁碟上 31 支 archive，主檔索引只有 30 條 bullet，`archive_31` 零登記，
標題還寫死「三十檔」；而當時的四項判準完全不看索引，於是 `--check` 照印 rc=0。
最尖銳的一點是：**同一支閘門在同一個 session 印出的是「32 檔」**（家族檔數＝主檔 + 31 支 archive），
兩個互相矛盾的數字並存在同一份輸出裡，而沒有任何人被擋下。

**修法**：

1. **判準⑤ 上線**：磁碟上每一支 archive 都必須在主檔「已歸檔內容」段有一條以它為主體的 bullet，
   且 bullet 數 == 實查 archive 檔數（**雙向**：多出來的 bullet 也是失實）。
2. **根因級**：`apply()` **自己把索引 bullet 寫進主檔**，並把新增位元組顯式列進守恆算式
   （`新主檔 + 釋出 == 舊主檔 + 新增`）。於是 bullet 少寫一個字、或主檔在別處被偷改，
   都會讓不變量不成立而**拒絕落地**——「歸檔完忘記更新索引」在結構上不再可能。
3. 補登 `archive_31` bullet。
4. **份數改為不寫死**（現場核算）。ARCH／SA／QA 三方要求改成「三十一檔」，SD 要求「別再寫死」，
   **主控裁決採 SD**：同一句在這份檔案已經 stale 過三次（R56 註自己就記著「原寫二十一檔在 HEAD 時點即已 stale」），
   把過期時點往後挪一輪不是修復。
5. 四支注入測試：刪一條 bullet／磁碟多一支未登記的 archive／索引指向不存在的檔／`apply()` 恰好註冊一條。

**Pkg-P5 實測**：

```
python tools/archive_defect_log.py --check   → REAL_RC=0
✅ …（判準⑤ 關鍵斷言）歸檔索引 31 條 bullet 對 31 支 archive
```

主檔第 156 行實查確認份數已改為不寫死，逐字為「**已歸檔內容**（🔴 **份數刻意不寫死**——由
`python tools/archive_defect_log.py --check` 判準⑤ 現場核算「bullet 數 == 實查 archive 檔數」並在失實時逐支指名…）」。

**Pkg-P5 實查結論**：全部證實。**其餘計數刻意不複寫進帳本列**——本包寫入 12 列之後，
同一支閘門的 ID 數由 679 變 691、引述處數由 16 變 23，若當初把它們抄進帳本，本包自己就會在同一次交件內把它寫成 stale。
這一點反過來佐證了判準④ 的設計方向（份數現場核算）是對的。

## DEF-101-570

**現象（`ARCH-R60R2-05`）**：`CrossPlatform_R60_Fix_Evidence.md:9` 與 `CrossPlatform_Scan_Dimensions.md:186`
都寫成 `立帳見缺陷帳本 DEF-…` 形態。以生產物件實測，這種第三方言當時**完全逸出稽核**：
`POINTER_RE.findall()` 回 `[]`（scope 群組當時只收 `本表`／`主檔` 兩種）、`POINTER_VERB in line` 為 True、
`_quotation_kind()` 回 None、而檔案又不在 `_family_files()` 裡 ⇒
**同一個動詞在帳本家族內是硬錯誤、在家族外零檢查**。

**🔴 裁決過程（本節重點，下一輪不要重辯）**：

主控**初裁方案(乙)**：`立帳見` 定為家族專用語法、家族外禁用（把那兩處改寫成別的說法）。
**隨後主控自己推翻**：(乙) 會讓那兩處指針**完全失去居所稽核**。ARCH 的證據正指出 `DEF-101-555` 是
待 R61 承接的**活列**，一旦它被搬進 archive，`Scan_Dimensions.md:186` 那句就靜默失實——
與 archive_26/27 → `DEF-101-493` 完全同一劇本，而 493 正是 `ARCH-R60-01` 的原始案例。
**把語法禁掉＝把偵測面一起丟掉。**

**改採方案(甲) 擴面**：

- `POINTER_RE` 的 scope 增收 `缺陷帳本`（語意等同「主檔」）。
- 稽核面由 `_family_files()` 擴為 `_pointer_audit_files()` ＝ 帳本家族 ∪ 具名治理文件（`_GOVERNANCE_DOCS`，2 份）。
  治理文件**不參與**居所判定的來源（居所一律由帳本家族的表格列決定），只是「會寫出指針宣稱」的地方。
- 例外由兩種增為四種：(甲) 動詞落在 inline code span 內＝引述語法；(乙) 動詞後緊接 `」`＝術語提及；
  (丙) 落在 ``` 圍籬區塊內＝逐字重現的原文／工具輸出；(丁) **僅限治理文件**內未跟可解析 DEF-ID 的提及＝談論這個語法本身。
- **(丁) 的判定刻意留在呼叫端**：只有那裡知道動詞後面有沒有跟上 ID。下沉進 `_quotation_kind()` 會失去這個資訊、
  於是必然一起豁免掉帳本家族內的散句——那正是 `ARCH-R60-01` ③ 的原始缺陷型，等於把修好的洞重新打開。

**Pkg-P5 實測**：`_family_files()` = 32、`_pointer_audit_files()` = 34（＝家族 ∪ 2 份治理文件），
`--check` REAL_RC=0，例外處逐處分類列印（不靜默豁免），例如：

```
· CrossPlatform_R60_Fix_Evidence.md:843  [(丁) 治理文件內非宣稱提及（未跟 DEF-ID）] …
· AutoSDD_Defect_Log.md:140             [code span 引述（判準⑥ 形態）] '見 DEF-101-481（現居 archive_27）'
```

**Pkg-P5 實查結論**：全部證實（含 `_GOVERNANCE_DOCS` 確為 2 份、路徑刻意以 `_REPO_ROOT` 而非 `_QUALITY_DIR` 為基準，
以免測試沙箱 monkeypatch `_QUALITY_DIR` 時把真鎖變成沙箱內的假訊號）。
**額外實證（本包自己撞到）**：Pkg-P5 第一版帳本列在散文裡逐字引述了 `立帳見缺陷帳本 DEF-…` 與初裁方案的引文，
`--check` 當場 **REAL_RC=1** 攔下 3 筆（主檔 139~140 行），逐字訊息並附上處置建議
（「若這裡是**引述判準語法**而非做出指針宣稱，請用 markdown inline code（反引號）包住整段引文」）。
依該建議改為 code span 後 REAL_RC=0 ⇒ **這道擴面後的鎖對本包這個真實新寫入具備鑑別力，不是紙上機制**。

## DEF-101-571

**現象（`SA-R60R2-03`）**：`archive_26.md:7` 原寫 `見主檔 DEF-101-481` 而失實（該 ID 實居 archive_27），
而 `POINTER_RE` 硬要求字面「立帳見」，少兩個字就完全逸出 ⇒ 稽核照印「19/19 皆…一致」。
這句話**在它自己界定的範圍內為真**，但讀起來像整個類別已經閉合——與 `DEF-101-562` 記載的認定門檻缺口同型。

**修法**：`archive_26.md:7` 訂正為帶現居註記的形態；新增**判準⑥** 涵蓋 `見主檔 DEF-x` 與
`見 DEF-x（現居 archive_NN）` 兩種方言，一律驗居所。`(?<!立帳)` 前瞻用來避免與判準④ 重複報同一處。

**Pkg-P5 實測**：`archive_26.md:7` 現為 `見 DEF-101-481（現居 archive_27）` 形態（連同同行的 `DEF-101-483`）；
`--check` REAL_RC=0 且訊息載明「**4 個**「見主檔／現居」居所指針」全數驗過居所一致。

**Pkg-P5 實查結論**：全部證實。附帶佐證：本包在帳本列中逐字引述**原失實形態**時，判準⑥ 立刻把它當成
一個新的失實居所宣稱擋下（下方輸出逐字重現於 ``` 圍籬內，故本節自身未做出該居所宣稱）⇒ 判準⑥ 同樣具鑑別力。

```
AutoSDD_Defect_Log.md:140：居所指針「見主檔 DEF-101-481」失實 — 依「主檔」scope（無 scope 字樣者同此），
該 ID 應在 AutoSDD_Defect_Log.md，實居 ['AutoSDD_Defect_Log_archive_27.md']。
```

**🔴 Pkg-P5 順帶實測到的稽核面不對稱（新發現，本輪未修，已記入 `DEF-101-571` 列）**：
判準④（`立帳見`）的稽核面已由 `ARCH-R60R2-05` 擴為 `_pointer_audit_files()`＝家族 ∪ 具名治理文件，
但**判準⑥ 仍只掃 `_family_files()`**（`check()` 內 `for p in files:`，而 `files = _family_files()`）。
決定性實測：本節初稿在治理文件內寫出一個真正失實的 `見主檔 DEF-101-481`（跨行反引號未閉合 ⇒ code span 例外不成立），
以生產物件驗證 `NONVERB_RESIDENCE_RE.findall(該行)` 回 `[('主檔', 'DEF-101-481', '')]`、
`_CODE_SPAN_RE.findall(該行)` 回 `[]`，而 `--check` 仍 **REAL_RC=0** ⇒ 治理文件內的判準⑥ 形態零檢查。
這與 `DEF-101-570` 修掉的缺口**同型、只差一個判準沒跟上擴面**。Pkg-P5 已改寫本節文字消除該失實宣稱。

**🔴 交件前複驗：該不對稱已由 Pkg-P7（P7-5）於同輪修復。** Pkg-P5 重新實查 `check()` 的 (6) 段，
稽核面已由 `_family_files()` 改為 `_pointer_audit_files()`、與判準(4) 共用同一份 SSOT，
例外沿用 (甲) code span ＋ (丙) 圍籬（同一個 WHY：兩者內都是逐字重現的工具輸出／原文＝證據，不是宣稱），
並**刻意不設 (丁) 對等例外**（WHY：沒有 ID 就根本不命中，無物可豁免）。
Pkg-P7 的落地註解逐字重現了本節的沙箱實測（「治理文件寫一句非 code span、非圍籬的失實
`見主檔 DEF-101-481` ⇒ 正則命中、`check()` 仍 rc=0」），並實測「現行兩份治理文件的 5 處命中全落在這兩種例外內、
家族側 6 處命中則零處落在圍籬 ⇒ 補上 (丙) 對家族既有稽核面零削弱」。
⇒ 本筆自此**無殘留**，原先寫進跨包請求的項目已結案。

## DEF-101-572

**現象（`SA-R60R2-06`）**：帳本狀態欄首詞合法值的硬斷言從未裝上。
round 1 已證 `_classify()` 的寬鬆前綴比對會讓 `partially-fixed` 靜默命中 `fixed`
（「只修了一部分」在閘門眼中等於「已修」）；round 2 雖然把 4 筆存量非法首詞清乾淨（`DEF-101-556`），
**但產生它們的機制沒有變**，且 `check_defect_log_crossref.py` 與 `tools/tests/` 皆零命中該斷言 ⇒
「把樣本清乾淨＝把鎖裝好」的錯覺。

**修法**：新增 `status_first_word_problems()` 硬斷言。合法值與主檔《格式定義》新增的**權威散文雙向綁定**
（兩邊不一致即紅），且刻意**仍逐列比對**——否則「改壞散文」就成了關掉整道鎖的捷徑。
**零白名單上線**：靠 `DEF-101-556` 先把 4 筆存量清乾淨，故沒有任何「暫時容忍」清單可腐化。
`workaround` **刻意不列為合法首詞**（依 `_STATUS_KEYWORDS` 判例它歸類為 `open`，正規寫法是 `open（workaround-applied …）`）；
`partial` 僅限 ADR-XPLAT-001 §4.3.3 的降級出口。

**Pkg-P5 實測**：

```
python tools/check_defect_log_crossref.py                     → REAL_RC=0
  ✅ …另全部表格列的狀態欄首詞皆落在《格式定義》宣告的 7 個合法值內（散文與程式常數雙向綁定）
python -m unittest test_check_defect_log_crossref（於 tools/tests/）
  第一次量測 → Ran 41 tests / OK / REAL_RC=0
  第二次量測 → Ran 51 tests / OK / REAL_RC=0   ← Pkg-P4 期間補上正負樣本，+10 支
```

主檔《格式定義》第 18 行實查逐字為：
「🔴 **合法首詞**＝`open`／`routed`／`fixed`／`wontfix`／`closed-by-decision`／`no_action_needed`／`partial`。」，
其後並附權威散文說明它與 `_STATUS_FIRST_WORDS` 雙向綁定。

**Pkg-P5 實查結論**：全部證實（含「零白名單」＝程式內確無容忍清單）。
本包 12 列的狀態首詞全為 `fixed`，落在 7 個合法值內。

## DEF-101-573

**現象（`QA2-R60-04`）**：`AutoClaude/tests/tools/test_run_local_nightly_static.py` 的
`_TEST_MUTEX_NAME = "Global\\AutoClaude_Nightly_Run_TestOnly"` 是**機器級命名空間 ＋ 固定名**，
而其中一支測試會持有它 6 秒 ⇒ 任何同時進行的第二個 pytest 行程只要跑到「鎖是空的」那支就必然假紅。
QA 第一次全跑即中招（rc=1「1 failed, 3755 passed」），隔離重跑與全套重跑皆 rc=0 ⇒ 假紅、非回歸。
**非本輪引入**（該檔最新 commit 為 R44 `68c159d`），但本輪「四方各自重跑全套」的複審協定與此測試的設計
**結構性衝突**——協定越嚴格，這個假紅越必然發生。

**修法**：名稱改帶 `os.getpid()` + `uuid4().hex[:8]` 行程唯一後綴，並加靜態斷言「不得回退為固定名」。
Pkg-P5 實查該檔現有四條斷言：`startswith` 前綴、`!= "Global\\AutoClaude_Nightly_Run_TestOnly"`、
`str(os.getpid()) in name`、以及形狀 `Global\\AutoClaude_Nightly_Run_TestOnly_\d+_[0-9a-f]{8}`。
主控實測兩行程取到 `..._29208_af82814b` 與 `..._12968_651f31d8`（不同），並行 A/B 皆 rc=0（各 2 passed）；
修復前 QA 實測為 A=0／B=1。

**🔴 並行跑全套的假紅成因累積清單（本節的主要價值：讓下一輪能立刻歸因而不是重新調查）**：

| # | 成因 | 出處 | 典型訊號 |
|---|------|------|---------|
| 1 | pytest `__pycache__` 位元碼寫入競態 | `DEF-101-268` | 隨機 import／collect 錯誤，像 flaky |
| 2 | 就地突變 tracked 生產碼，多鏡互踩 | 記憶檔 `parallel-mutation-audit-collision` | 別的鏡的斷言莫名翻紅 |
| 3 | **機器全域具名 mutex**（本列） | `QA2-R60-04` | 「另一個 nightly 行程持有去重鎖」 |

**🔴 Pkg-P5 另發現的第四個候選成因（本輪未修，根因未定位）**：

Pkg-P5 把 `python tools/run_root_unittests.py` 丟到背景跑，**同時**並行了 6 個其他 python 行程
（`unittest` 兩支、`check_defect_log_crossref.py`、`archive_defect_log.py --check`、`ruff`、`check_script_parity.py`），
其中一支正是被測模組對應的生產腳本本身。該次結果：

```
（並行）  Ran 894 tests … FAILED (failures=4, skipped=11)   REAL_RC=1
          4 筆全部落在 test_check_defect_log_crossref.TestMain，症狀一致為 m.main() 回 1 而非 0
（獨占）  python tools/run_root_unittests.py            → 發現 906 個測試／Ran 906／OK (skipped=11)／REAL_RC=0
（獨占）  再跑一次（discover 於 tools/tests）            → Ran 906 / OK / REAL_RC=0
（獨占）  模組單跑 test_check_defect_log_crossref        → Ran 41 tests / OK / REAL_RC=0
```

⇒ 判定為假紅。但**收集數本身少了 12 支**（894 vs 906）這一點**無法由上列三個成因中的任何一個解釋**
（`__pycache__` 競態會產生 import 失敗，而 unittest 會把它轉成 `_FailedTest` 並**計入**數量，不會讓總數變少）。
根因未定位。Pkg-P5 無 `.py` 檔案所有權，故不修、如實記載，交 R61。
**對下一輪的操作建議**：跑 `run_root_unittests.py` 取權威計數時**獨占跑**，不要與任何其他 python 行程並行；
這與記憶檔既有的「並行派多 audit 鏡須序列化或用 worktree」是同一條紀律，只是這次的受害者是計數本身。

**Pkg-P5 實查結論**：mutex 修法與四條靜態斷言全部證實。
QA 側的 rc／passed 數字與主控的兩個 mutex 實例名為轉述、本包未重現（**未能證實但無矛盾**）。

## DEF-101-574

**現象（`SD-R60-R2-09`）**：`AutoClaude/tests/tools/test_local_ci_gate_shell_arg_parity.py` 的守門判準
`if\s*\(\s*[^)]*\$PytestArgs` 中，`[^)]*` 容許任意前置，於是**寬化守門** `if ($Act -or $PytestArgs)`
實測 `total=7 red=0` ＝**假綠**；而它的實跑後果與原缺陷相同——`-Act` 為真且未給 pytest 參數時，
會把 `['']` 送進核心。正控確認 `if ($true)` 那種注入會 5 red，故這是**窄縫而非整體失效**。

**修法**：判準收緊為「條件必須**恰好**是 `$PytestArgs` 真值判斷」。Pkg-P5 實查逐字為：

```python
_PS1_PYTESTARGS_GUARD_RE = re.compile(r"if\s*\(\s*\$PytestArgs\s*\)")
```

對抗式自測 total 17 項，`widened_or`（`if ($Act -or $PytestArgs)`）由 red=0 轉為 **5 failed／rc=1**；
檔頭另補記原本沒寫的方向「寬化守門會假綠」。

**🔴 誠實劃界（Pkg-P5 實查所得，不是任務書轉述）**：收緊之後，本鎖自此是「符合單一寫法」型守門，
**誤紅的是「行為上不劣於現行守門的等價寫法」，不是守門的寬化／窄化**——寬化與窄化守門兩個方向都會
**正確**轉紅（窄化守門是反方向的真缺陷：`$Act` 為假時使用者給的 pytest 參數會被靜默丟棄，
故列在該檔 `_GUARD_REJECT_SAMPLES` 第 ④ 項）。真正會誤紅的是該檔 `_GUARD_KNOWN_FALSE_RED_SAMPLES`
明列的兩種等價寫法（其中 `IsNullOrWhiteSpace` 甚至比現行守門更嚴）：

<!-- 🔴 R60 round 3 訂正（回報者 SA-R60R3-03）：本段原寫「**窄化守門也會誤紅**。該檔以
     `_PS1_NARROWED_FORMS` 明列…」。`_PS1_NARROWED_FORMS` 這個識別字在程式側全庫零命中
     （實際常數是 `_GUARD_KNOWN_FALSE_RED_SAMPLES`），且語意與該檔檔頭 :29~31 相反——
     檔頭寫的是「寬化／窄化守門會**正確**轉紅；而行為上可接受的等價寫法會**誤紅**」，
     原文把「窄化守門」與「等價寫法」兩個相反類別對調了。已依實查訂正。 -->

```
if (-not [string]::IsNullOrWhiteSpace($PytestArgs)) { $CliArgs += ($PytestArgs -split '\s+') }
if ($PytestArgs.Length -gt 0)                       { $CliArgs += ($PytestArgs -split '\s+') }
```

檔頭 :29~31 已把這個代價寫成明文邊界，逐字為「本鎖自此是『符合單一寫法』型守門——寬化／窄化守門會
**正確**轉紅；而行為上可接受的等價寫法（`IsNullOrWhiteSpace` 等，見 `_GUARD_KNOWN_FALSE_RED_SAMPLES`）
會**誤紅**，須實測新形態行為後同步本鎖」，故**不是隱藏缺口**；若未來要改用那兩種寫法，須同步放寬判準。
這是本包對該修法唯一的保留意見，如實記載而不掩飾。

<!-- 🔴 R60 round 3 訂正（同 SA-R60R3-03）：原文只引到「寬化／窄化守門會…」就以刪節號截斷，
     而被截掉的正是「**正確**轉紅」四個字——刪節號本身製造了與上一段相同的語意反轉。
     改為逐字引全句。 -->

**Pkg-P5 實查結論**：現象、收緊後的判準、誤紅風險三者皆證實。任務書要求本包「自己去讀那支檔確認實際收緊成什麼判準、
有沒有誤紅風險，不要照抄」——已照辦，並把誤紅風險（任務書未提）補進帳本列。

## DEF-101-575

**現象（`QA2-R60-06`）**：`ruff --isolated --select W605` 原有 **7 errors**，落在
`tools/tests/test_extras_quoting_zsh_safety.py`／`test_nightly_interpreter_determinism.py`／`test_ps51_compat.py` 三支檔，
皆登記在 `tools/tests/test_no_invalid_escape_sequences.py` 的 `_KNOWN_DEBT`，
但**無承接輪次、帳本亦無對應條目** ⇒「無承接者的 backlog」，正是本輪硬規則② 在治的形態，
只是它從帳本搬進了程式碼裡的名冊——換個載體就逃過稽核。

**🔴 修復時的重要反轉（Pkg-P3 實測發現，必須記）**：原名冊三筆的 WHY 都寫「處置＝改 `r"""`（零語意變更）」，
實測**這個判斷是錯的**。raw 化會讓同一 docstring 內**既有的合法轉義**跟著改變 rendered 內容：

- `test_ps51_compat.py` 有 8 處 `\\`（本意是顯示單一反斜線的正則，raw 後會變成顯示兩個，**文件反而變錯**）
- `test_nightly_interpreter_determinism.py` 有 2 處
- `test_extras_quoting_zsh_safety.py` 甚至有一個合法的 `\t`（rendered 是真 TAB）
- 三檔 `ast.get_docstring()` 皆 `differs_if_made_raw=True`

反之「把該處反斜線加倍」對**非法**轉義是恆等變換（Python 對非法轉義原樣保留反斜線），
實測三檔 rendered docstring 的 len 與 sha256 前後完全相同。故**首選處置改為「把該處反斜線加倍」**，
raw 前綴只是次選、且只有在該字串內**沒有**任何合法轉義時才等價。

**Pkg-P5 實測**：

```
python -m ruff check --isolated --select W605 .   → All checks passed!   REAL_RC=0
tools/tests/test_no_invalid_escape_sequences.py:86 → _KNOWN_DEBT: dict[str, str] = {}   （已空）
```

該檔另有 stale 自檢（已修好的檔必須從名冊移除＝**強制回收豁免**）、`entries_missing_why` 斷言，
以及一支在名冊為空時明記「上面兩支對真名冊的斷言恆真」的自證測試，避免機制在名冊清空後靜默失效。
檔內並明文拒絕「加進 `_KNOWN_DEBT` 當修法」：「名冊是**既有存量債**的凍結清單」。

**Pkg-P5 實查結論**：全部證實，逐字確認了訂正段的內容（任務書要求本包自己讀、不照抄轉述——已照辦）。
附註：該次 ruff 執行另印一則與本項無關的既有警告
（`AutoClaude\autoclaude\models\playbook.py:61` 的 `# noqa` 指示碼格式不合法），非本輪引入、不在本包範圍，如實記載。

## DEF-101-576

**現象（主控自查，非四方回報——如實標明無 finding id）**：主控把 `sync_onboarding_baselines.py --check-snapshot`
接為 pre-push leg ③ 的第 8 支守門後，`tools/tests/test_pre_push_dispatcher.py` 建的暫存 fake repo 裡沒有那支檔，
於是 3 支測試紅。

**修法**：fixture 補 stub，且**照既有慣例檢查 argv**——Pkg-P5 實查逐字為：

```python
"tools/sync_onboarding_baselines.py",
…
'raise SystemExit(0 if "--check-snapshot" in sys.argv else 4)\n',
```

於是這支 fake-repo 測試同時成為「守門迴圈項可帶子指令、分詞機制正確」的端到端驗證。
Pkg-P5 實查 `tools/git-hooks/pre-push:223~228` 該迴圈確有 8 項，其中**兩項各帶不同子指令**：

```sh
for guard in "tools/check_script_parity.py" "tools/check_ntfs_paths.py" \
             "tools/check_defect_log_crossref.py" "tools/check_wrapper_thinness.py" \
             "tools/check_pytest_baseline_sites.py" "tools/check_gha_action_versions.py" \
             "tools/archive_defect_log.py --check" \
             "tools/sync_onboarding_baselines.py --check-snapshot"; do
  # shellcheck disable=SC2086  # 刻意分詞：項目可帶子指令（archive_defect_log --check）
  if ! python $guard; then …
```

**兩支各帶不同子指令的守門併看，即證明分詞對多項皆成立**（不是只對其中一支碰巧可行）。

**Pkg-P5 實測**：`python -m unittest tools.tests.test_pre_push_dispatcher` → `Ran 10 tests / OK / REAL_RC=0`。

**Pkg-P5 實查結論**：全部證實。

## DEF-101-577

**現象（主控自查；本輪自己犯的同型錯）**：`archive_defect_log.check()` 的 docstring 在 round 3 收斂後仍寫
「**七項**都是實作」「同一條紀律在 round 2 又抓到 **(5)(6)(7)** 三個」，
而作廢的第(7)項（方案乙的反向鎖，即 `DEF-101-570` 記載被推翻的那個方案）已被刪除、實際只有六項；
判準④ 的例外也已由「只有兩種」增為四種而散文沒跟上。
**這正是本工具立帳要消滅的病（宣稱一道檢查存在而它不在）在工具自己的 docstring 上復發**，而且是在同一輪內。

**已完成的修法**：`check()` docstring 的六項／四種例外／`governance` 分流全部訂正。Pkg-P5 實查逐字確認：

- 首句已為「事後保全稽核。六項**都是實作**，成功訊息只准宣稱這六項：」
- 判準④ 的例外已列 (甲) code span／(乙) 術語提及／(丙) ``` 圍籬／(丁) **僅限治理文件**內未跟 DEF-ID 的提及
- 末段已有「🔴 **`governance` 分流（round 3，勿誤放寬）**」整段，明寫 (丁) 只對 `_GOVERNANCE_DOCS` 開放、
  帳本家族內同一形態維持**硬錯誤**，並說明 (丁) 的判定為何刻意留在呼叫端
- 另新增測試斷言 docstring 必須寫明治理文件與家族的分流（防下一輪誤放寬）

**🔴 Pkg-P5 實查揪出同一份檔案仍有兩處未訂正的「第七項」殘留**（同型錯、同一輪內第二次復發）：

1. **`tools/archive_defect_log.py:747`（`apply()` 寫進 archive 標頭的散文）仍列七項**，且第(7)項逐字為
   「具名治理文件無家族專用語法的指針宣稱（共七項，逐項定義見該檔 `check()` docstring）」——
   那正是**被作廢的方案乙反向鎖**（`DEF-101-570` 已裁決不採用）。後果比 docstring 更嚴重：
   **每一支新建立的 archive 標頭都會複製一份失實宣稱**，而 archive 是「原文逐字保全、零刪除」的檔案，
   等於把失實敘述永久刻進歷史。
2. **`tools/archive_defect_log.py:359`（`_fenced_line_numbers()` 的 docstring）仍寫「判準⑦ 用」**，
   而 ``` 圍籬在現行設計裡是判準④ 的例外(丙)、不是獨立判準。

**🔴 交件前複驗：兩處殘留皆已由 Pkg-P7（P7-4）於同輪修復，且修法是根因級的。**

Pkg-P7 沒有只把「七」改成「六」（那只是把過期時點往後挪一輪），而是新增判準清單 SSOT：

```
CHECK_CRITERIA: tuple[tuple[str, str], ...]   # 7 項（第 7 項＝「表格列欄數」，Pkg-P7 新增的真判準）
MOVE_CRITERIA:  tuple[str, ...]               # 搬遷判準 5 項
⇒ check() 的成功訊息與 apply() 寫進 archive 標頭的散文**全部由這兩個常數生成**，不得手寫第二份清單。
```

該檔並逐字記下了為何必須生成而非各寫一份——與本節的歸因完全一致：
「R60 round 2 主控推翻方案(乙)、刪掉 `check()` 的第(7)項…卻**漏改 `apply()` 標頭裡手寫的「共七項」清單**。
而 archive 是**零刪除的史料檔** ⇒ 每跑一次 `--apply` 就把那份失實宣稱複製成一份新的永久紀錄。」

對應機械鎖 `tools/tests/test_archive_defect_log.py::TestCriteriaListIsASingleSsot` 三項：
(a) `check()` docstring 的 `(N) 標題` 逐項與常數**雙向**互比；(b) 每一項都必須在 `check()` 實作裡有 `# (N)` 段落標記
（宣稱一項就得有一段程式）；(c) `apply()` 產生的標頭必須逐字含每一項標題，且**不得出現超出項數的項次編號**。
第二處（`_fenced_line_numbers()` 的「判準⑦ 用」）亦已訂正，並在原處留下說明：
「第(7)項『家族專用語法反向鎖』是 round 2 被主控推翻的方案(乙)、程式早已刪除，這行註解是收斂不完整的殘留；
現行第(7)項是表格列欄數」。

**Pkg-P5 實查結論**：主控訂正在 `check()` 範圍內證實，但其「全部訂正」的**範圍宣稱當時不成立**（同檔另有兩處）——
本包據此把狀態寫為「部分」並列入跨包請求；Pkg-P7 隨即以根因級修法收斂兩處，故交件時狀態改回 `fixed@R60 r3`、
跨包請求結案。**這一筆的完整價值在於它示範了「範圍宣稱」本身也要被稽核**：
「我修好了 X」與「X 這一類已經沒有了」是兩句不同的話，後者才是讀者真正會依賴的。

## DEF-101-578

**現象（主控自查；流程缺陷，非程式缺陷）**：round 3 派出三包並行修復，其中兩包被
`You've hit your session limit` 中途砍斷，**但它們已寫入磁碟的修改仍在**：

- `tools/archive_defect_log.py` 留下未定義的 `FAMILY_ONLY_SYNTAX_DOCS` ⇒ NameError，11 支測試 ERROR
- `check_defect_log_crossref.py` 的新斷言缺主檔權威散文 ⇒ 4 支 FAIL
- 兩包都沒來得及交 `cross_package_requests`

**🔴 根因與教訓**：本 repo 已有記載「agent 回傳 null 不等於沒動磁碟」（`workflow-agent-null-result-still-mutates`）。
**本次是同一形態的第二次實例**——只是這次的死因是 API session 上限，而不是 API 錯誤。
處置紀律因此定為：agent 異常結束後**一律先獨立盤點磁碟真實狀態**
（`git status --short` ＋ `git diff --numstat` 逐檔 ＋ 實跑相關測試取錯因），
**不採信任何「它應該沒做完所以沒影響」的推測**。
本次即靠實跑 root 全套取回完整失敗清單並逐支歸因，才發現兩包其實各自完成了大部分工作
（P3 三項全做完，並誠實訂正了一個錯判斷＝`DEF-101-575` 的 raw 化反轉；P1 完成了 `apply()` 自動註冊與 `added` 入帳），
只差收斂。主控接手收斂並補齊 P1 未完成的注入測試（判準⑤ 四支 ＋ 覆寫拒絕一支）。

**Pkg-P5 實測**：`FAMILY_ONLY_SYNTAX_DOCS` 已全庫零命中（`grep` 於 `tools/archive_defect_log.py` 及全 repo 皆無）；
`tools/archive_defect_log.py --check` 與 `tools/check_defect_log_crossref.py` 皆 REAL_RC=0 ⇒ 半套狀態已收斂完畢。

**Pkg-P5 實查結論**：證實。本列刻意以流程缺陷入帳而非只寫進對話——
「留在對話裡的教訓會隨 compact 消失」本身就是本 repo 既有的紀律。

## DEF-101-579

**現象（`ARCH-R60R2-06` 的 round 3 續量）**：護欄層規模趨勢。
**判定與處置已在 `DEF-101-565`／`DEF-101-561` 記載，本節不重複**；本列只履行其量測義務。

**Pkg-P5 round 3 實測（皆親跑，不用加法推算）**：

```
ls tools/tests/*.py | wc -l          → 56               （round 1＝52、round 2＝56）
cat tools/tests/*.py | wc -l         → 23,599 → 23,999  （round 1＝20,188、round 2＝22,524）
python tools/check_script_parity.py  → REAL_RC=0
  ✅ 腳本註冊完整性：13 對 + 18 支單邊皆已納管（遞迴掃描 3 棵 SSOT 樹 + LATEST tools）
python tools/run_root_unittests.py   → REAL_RC=0（兩次皆獨占跑，中間無並行行程）
  第一次 ✅ 發現 906 個測試（下限 845）／Ran 906 tests in 82.736s／OK (skipped=11)
  第二次 ✅ 發現 916 個測試（下限 845）／Ran 916 tests in 89.216s／OK (skipped=11)
```

**🔴 本節的數字是移動標的，不是最終值。** 兩次量測之間 Pkg-P4 仍在落地
（`tools/tests/test_check_defect_log_crossref.py` 由 41 → 51 支、`tools/tests/` 總行數 23,599 → 23,999），
故收集數 906 → 916。工作樹的 untracked 清單前後完全相同（無新檔），成長全部來自既有檔擴充。
**權威值一律依 `MIN_TESTS` 自己訂的重釘紀律辦**——該常數的註解逐字要求「由主控在**所有並行修復包與四方複審
agent 全部停工後**，於最終工作樹實跑 `python3 tools/run_root_unittests.py` 取其印出的『發現 N 個測試』直接填入，
不做任何加減推算」（R57 曾兩度用算式推得 552／558，兩次都當場與實況不符）。
本節只留 Pkg-P5 量測期間的實測區間供趨勢判讀，**不冒充凍結值**。

`check_script_parity` 的 13 對 + 18 支單邊與 round 2 **相同、未下降**。

**🔴 誠實揭露**：round 3 的修復**再次讓護欄行數上升**（22,524 → 23,599，+1,075 行）。
緩解措施是**零新增鎖檔**（全部擴充既有檔，故支數維持 56 不變），
淨效果是把 ONBOARDING §7 表② 那 4 格「零機制」欄位收進既有機制 ⇒ 未受檢面淨減少；
但**行數確實仍在漲（22,524 → 23,999），ARCH 的警告第三次成立**。

**🔴 Pkg-P5 訂正主控任務書的兩處轉述數字**（zero-trust 對主控同樣適用）：

| 任務書寫 | 實測 | 說明 |
|---|---|---|
| `tools/tests/*.py` 56 支／**23,329** 行 | 56 支／**23,599 → 23,999** 行 | 支數吻合；行數任務書偏低，且在本包量測期間仍在成長（Pkg-P4） |
| 根層 unittest 收集總數 **845** → round 3 實測值 | **906 → 916** 支 | 845 是 `run_root_unittests.py` 的 `MIN_TESTS` **下限常數**，不是實測總數；已累積 +71，尚未達 `MIN_TESTS × 0.25`（＝211）的重釘門檻 |

**Pkg-P5 實查結論**：量測義務已履行；兩處轉述數字已訂正為實測值（並標明其為區間而非凍結值）。

## DEF-101-580

**現象（Pkg-P4 於測試時挖到、Pkg-P6 獨立重驗後修復；`P4→P6` 交棒）**：
`tools/check_defect_log_crossref.py` 自己的欄位切分有一個假綠面——它把表格列切欄時寫成
`[c.strip() for c in re.split(...) if c.strip()]`，**`if c.strip()` 把空欄整個濾掉**，
而且全程沒有任何「欄數 == 表頭欄數」（arity）的檢查。後果是**狀態欄留空時 `cells[-1]` 會靜默位移到
左鄰的「分流去向」欄**，於是那一欄的文字被當成狀態來裁決。

Pkg-P6 的構造輸入實測（**未動主檔**，全部在暫存 fixture 上跑）：

```
(a) 狀態欄空白 ＋ 分流去向＝「已於上游 fixed 故不另修」
    ⇒ _load_ledger_status() 回 {'DEF-01-001': 'fixed'}        ← 一筆沒有狀態的列被判為「已修」
(b) 最壞複合：狀態欄空白 ＋ 分流去向以合法關鍵字開頭（`open 待下輪處理`）
    ⇒ status_first_word_problems() 回 []                       ← 首詞鎖也沒訊號
    ⇒ 兩道檢查同時零訊號
```

且在修復前「碰巧擋到」的情況下，訊息會誤植成「狀態欄原文開頭：'去向'」——
**指向錯的欄位，比沒擋更危險**：讀者會照著那句話去查一個根本不是狀態欄的地方。

**修法（採「保留空欄 ＋ 表頭定位 ＋ arity 硬閘」三件一組）**：

- `_row_cells()`：切出**全部**欄位並各自 strip，**保留空欄**（含首尾空片段）。該函式 docstring 已釘上
  「🔴 絕對不可再寫回 `[... for c in ... if c.strip()]`」及其理由。
- `_table_layout()`：回傳 `(切片數, ID 欄索引, 狀態欄索引)`，以**表頭欄名**（`ID`／`狀態`）定位而非位置猜測；
  找不到合格表頭時**刻意不退回 `cells[-1]`**，而是報「欄位定位失去依據」（退回位置猜測正是本缺陷的成因）。
- `row_arity_problems()`：每一缺陷列切出的欄數必須等於表頭欄數。
- 訊息改**逐欄傾印**（行號 ＋ 全部切片、每欄截 40 字，`_cells_digest()`），並在狀態欄為空時額外警示。

**🔴 方法論界線（本筆最有價值的部分，且是一筆「主控任務書事實錯誤被下游正確駁回」的紀錄——不美化）**：

主控在任務書裡要求「(a)(b) 修復後必須紅並指出『欄數不符』」。**該期望經實測為錯**：
那兩列的**欄數本來就是對的**（9 個切片 ＝ 表頭欄數），所以**只加 arity 斷言完全抓不到它們**；
真正承重的是「保留空欄 ＋ 由表頭定位狀態欄」。arity 斷言治的是**另一種**列形——
欄內未轉義的字面豎線導致**多切出一欄**（`DEF-101-560` 的形狀），此時表頭索引指到的就不再是狀態欄。

**兩個機制互補、不可互相冒充。** 而且若硬把訊息印成「欄數不符」，反而正好犯下本筆要治的
「訊息誤植 ⇒ 指向錯的欄位」——用同一種病去治這種病。修復者拒絕照做，並把這條界線釘成專門測試。

Pkg-P5 實查確認該界線在 repo 內有兩處常駐載體（不是只寫在對話裡）：

```
tools/tests/test_check_defect_log_crossref.py:483
  def test_arity_check_alone_would_not_have_caught_the_column_shift(self)
tools/tests/test_check_defect_log_crossref.py:429~432（該類 docstring）
  「前兩個復現輸入的**欄數是對的**，所以「只加 arity 斷言」根本抓不到它們；真正承重的是
   「保留空欄 ＋ 由表頭定位狀態欄」。arity 斷言治的是另一種列（欄內未轉義字面豎線 ⇒ 欄數變多,
   DEF-101-560）。兩者互補、缺一不可，不可互相冒充。」
tools/tests/test_check_defect_log_crossref.py:497
  def test_unescaped_literal_pipe_row_is_flagged_by_arity_check(self)   ← arity 真正治的形態
```

**Pkg-P5 逐項實測（以生產物件，非採信轉述）**：

```
_table_layout(主檔)            → (9, 1, 7)     ＝9 切片／ID 欄 idx 1／狀態欄 idx 7
row_arity_problems(主檔)       → 0 筆
主檔含空欄的缺陷列              → 0 列
archive 側切片數 != 表頭 9 者    → 14 列（該閘門對 archive 只 stat() 量大小，不在其解析面內）
python -m unittest test_check_defect_log_crossref（於 tools/tests/）→ Ran 51 tests / OK / rc=0
python tools/check_defect_log_crossref.py → rc=0，成功訊息新增「全部表格列的欄數皆等於表頭欄數、
  狀態欄由表頭定位（非 cells[-1] 位置猜測）」
```

**Pkg-P5 實查結論**：現象、三件一組的修法、以及方法論界線**全部證實**，且界線有常駐測試與 docstring 雙載體。
嚴重度 P2「潛伏非現行」亦證實（主檔 0 列含空欄、0 列 arity 不符 ⇒ 今日無活體後果）。
**未能證實**：任務書所述「兩個突變體分別殺 4／5 支、控制組 0/0」——這組數字在 repo 內找不到常駐痕跡
（`grep` 該測試檔的「突變／控制組」字樣只命中一處與本項無關的交集收窄註解），
屬 Pkg-P6 的對話內宣稱，如實標明而不代為背書。

## DEF-101-581

**現象（Pkg-P5 交件前複驗時實測撞到；非四方回報，且發現者不是肇事包）**：

Pkg-P7 為收斂切欄 SSOT（見 `DEF-101-560` 補述、`DEF-101-580`），把 `tools/archive_defect_log.py` 的
`_CELL_SPLIT_RE` 與 `_cells()` 本地複本刪除、改為全部委派 `gate.*`。**該收斂本身是對的**——
被刪掉的 `_cells()` 正是寫成 `[... if c.strip()]`＝Pkg-P6 明文標「絕對不可再寫回」的形態。

但 `tools/tests/test_adr_xplat001_c1c2_lock.py` 的 `row_cells()` **刻意**取用 `ADL._CELL_SPLIT_RE`
當唯一真相源，其 docstring（`:274~276`）逐字寫著：

```
刻意不直接用 `ADL._cells()`：那支是為 `cells[0]`／`cells[-1]` 設計的，會用
`if c.strip()` 丟掉空格子——中間任一欄留空就整排錯位，而本鎖要的是第 6／第 7 欄。
切格的正則本身仍取歸檔工具的 SSOT（`ADL._CELL_SPLIT_RE`），不自寫第二份。
```

於是符號一被刪，該行 `:278` 立刻 `AttributeError`：

```
File "tools/tests/test_adr_xplat001_c1c2_lock.py", line 278, in row_cells
    parts = ADL._CELL_SPLIT_RE.split(line)
AttributeError: module 'archive_defect_log' has no attribute '_CELL_SPLIT_RE'
```

**Pkg-P5 實測（獨占跑，無並行行程）**：

```
python -m unittest tools.tests.test_adr_xplat001_c1c2_lock
  → Ran 29 tests / FAILED (errors=9, skipped=1) / REAL_RC=1      （修復前為 44 支 OK）
python tools/run_root_unittests.py
  → 發現 916 個測試 ／ Ran 916 ／ FAILED (errors=9, skipped=11) ／ REAL_RC=1
grep -rn 'ADL\._CELL_SPLIT_RE|archive_defect_log\._CELL_SPLIT_RE' tools/
  → 僅 test_adr_xplat001_c1c2_lock.py 的 :276（註解）與 :278（呼叫）兩處
```

注意收集數由 44 掉到 29：`setUpClass` 也踩到同一個符號，所以整個 class 直接 error 而非逐支 fail。

**建議修法（Pkg-P5 已實測可行性，但無 `.py` 所有權故未施作）**：⚠️ **本小節記載的是 Pkg-P5 當時的建議，其中被列為「最小改動」的路徑(甲)（改引用 `gate._CELL_SPLIT_RE`）並非實際落地的修法**——實際採用的是路徑(乙)（`gate._row_cells()`）。原文逐字保留（時代快照），訂正與等價性證據見本節末的「🔴 R60 r3 Pkg-P11 訂正」段。

- **最小改動**：把 `:278` 改成 `gate._CELL_SPLIT_RE`。Pkg-P5 實測 `archive_defect_log.gate is
  check_defect_log_crossref` 為 `True`、其 `_CELL_SPLIT_RE.pattern` 為 `(?<!\)\|`，
  與原先 `ADL._CELL_SPLIT_RE` 是**同一份正則**（Pkg-P7 只是把它移回上游）⇒ 語意零變更。
- **更好的改法**：直接呼叫 `gate._row_cells()` 再自行去頭尾。理由：`_row_cells()` **已保留空欄**
  （Pkg-P6 在 `DEF-101-580` 修的正是這件事），而該 docstring 當初避開 `ADL._cells()` 的唯一理由
  就是「它會用 `if c.strip()` 丟掉空格子」——那個理由現在已經不存在了。
  換言之這個缺陷順帶暴露出：`row_cells()` 的存在理由已被上游修復抹除，它可以整支收斂掉。

**🔴 教訓（與 `DEF-101-578` 同族：並行修復包之間的介面破壞）**：

1. **刪掉一個帶底線前綴的符號仍然是破壞性介面變更**。`_` 前綴表示「模組內部」，但本 repo 的
   SSOT 紀律**鼓勵**跨檔引用彼此的判準物件（就是為了不要有第二份），於是 `_` 名稱事實上是公開契約。
   收斂 SSOT 時必須先 `grep -rn` 全庫引用面，不能只看自己這一支檔跑得過。
2. **受害者是因為遵守紀律才被打斷**——`row_cells()` 沒有自寫第二份正則，完全照 SSOT 紀律走，
   結果反而比「偷偷複製一份」的寫法更脆弱。這說明 SSOT 紀律必須配一道「引用面不得靜默斷裂」的機械保護，
   否則紀律本身會懲罰遵守者。
3. **本輪的閘門組合沒有攔下它**：`check_defect_log_crossref.py` 與 `archive_defect_log.py --check`
   都是 rc=0（它們不 import 那支測試），只有跑**全套** unittest 才會紅。
   ⇒ 「兩道帳本閘門綠」不等於「帳本相關的護欄都健康」，交件前必須獨占跑一次 `run_root_unittests.py`。

**Pkg-P5 實查結論**：現象、單一成因、blast radius（9 errors／單一行／全 repo 僅一處引用）、
兩種修法的可行性**全部親自實測證實**。**狀態刻意寫 `open`（承接輪次未指派）而非 `fixed`**：
本包無 `.py` 檔案所有權，且**不得為了讓交件看起來乾淨而把紅燈記成綠燈**。
🔴 **這是本包唯一一筆 `open` 的列，也是唯一一項阻擋 push 的事項**，請主控優先指派。

### 🔴 R60 r3 Pkg-P11 訂正（DEF-101-581 的落地修法與等價性證據）

**被訂正的宣稱**：本節上方「建議修法」把「單行改引用 `gate._CELL_SPLIT_RE`」列為最小改動
（路徑(甲)），帳本該列原先的狀態欄也照抄了這個說法。**實際落地的是路徑(乙)**：

```
tools/tests/test_adr_xplat001_c1c2_lock.py::row_cells()
    return ADL.gate._row_cells(line)[1:-1]
```

即**不再借上游的正則零件，而是消費上游的函式**，順帶把「自己再切一次」的中間層整支拿掉。
選(乙) 的理由已寫進該函式 docstring：當初繞開 `ADL._cells()` 的唯一理由是「它會 `if c.strip()`
丟掉空欄」，而 `_row_cells()` 早已被 `DEF-101-580` 修成保留空欄 ⇒ 那個理由不存在了；
**引用面愈少零件，愈不容易被上游重構打斷**。

**等價性證明＝全家族逐行比對、零差異、非抽樣**（不是抽幾列看看）。Pkg-P11 以生產物件實跑，
對帳本家族每一份檔的每一行同時求值兩條路徑並逐行比對：

```python
jia = [c.strip() for c in gate._CELL_SPLIT_RE.split(ln)[1:-1]]   # 路徑(甲)
yi  = gate._row_cells(ln)[1:-1]                                  # 路徑(乙)＝實際落地
```

量測時點＝Pkg-P11 動工（歸檔 `archive_32` 之前），輸出：

```
family_files=32 lines_compared=2161 table_rows=699 diffs=0
```

⚠️ **上列數字是量測時點的快照**（家族檔數與行數每次歸檔／寫入都會變），
判準本身不依賴它們；重現方式＝以 `archive_defect_log._family_files()` 取家族清單，
對每一行同時求值上面兩式並比對。結構上兩者本就同值——`_row_cells()` 的定義是
`[c.strip() for c in _CELL_SPLIT_RE.split(line)]`，(甲) 是「切→取中段→strip」、
(乙) 是「切→strip→取中段」，strip 與切片可交換；**逐行實跑是為了不靠推理下結論**。

**根層全套（獨占跑，量測時點宣告：Pkg-P11 交件前）**：見本檔末尾「Pkg-P11 交付門檻實測」段。

**🔴 根因級補述——反向契約鎖（本輪落地）**：載體是三支模組級純函式 ＋
`TestArchiveIsNotAnEscapeHatch` 內的上游契約測試（支數與名稱一律以該 class 現場為權威）：

| 純函式 | 職責 | 抓的形狀 |
|--------|------|---------|
| `upstream_refs(source)` | AST 現查本檔對上游的引用鏈**＋行號**（巢狀鏈連中間節點一起收） | 引用清單本身 |
| `dangling_upstream_refs(refs, root)` | 逐一 `hasattr` 解析 | **被引用名稱消失**（`DEF-101-581` 那一型） |
| `incompatible_upstream_calls(source, root)` | AST 取引數形狀後 `Signature.bind` 靜態驗 arity | **上游簽名改變**（`TypeError`、只在該行被求值時才炸，冷路徑會一路綠） |

鑑別力（沙箱替身，突變不外洩到真模組——測試自帶「真模組未被污染」的反向斷言）：

- **歷史事故重演**：餵修復前的 source ⇒ 鎖紅並**逐字指名** `_CELL_SPLIT_RE` 與本檔引用行號。
  ⇒ **這道鎖若當時存在，`DEF-101-581` 會在肇事當輪就紅，而不是等到交件前複驗才撞到。**
- 受害名稱刻意涵蓋三種形狀：巢狀函式（`_row_cells`，即真實事故那一處）、頂層函式
  （`_family_files`）、模組別名本身（`gate`，斷在鏈的中間節點）。
- 對照組＝什麼都不拔／什麼都不改簽名的同型替身 ⇒ 零問題，證明紅是「拔掉」造成的、
  不是替身不透明。
- 抽取器**非空轉**斷言：逐字釘住判準本體實際消費的幾個上游名稱，抽不到即紅。

---

## DEF-101-582

**現象（Pkg-P11 自查；非四方回報，如實標明無 finding id）**：
ADR C1/C2 鎖以**散文註解**宣告帳本欄序，其中**第四欄欄名與磁碟不符**——
散文寫「現象與證據」，磁碟真表頭逐字為「現象與證據（file:line）」。

**為何值得立帳（而不是改個字了事）**：兩者之間**沒有任何機械關係**。散文改壞不會紅、
表頭改動也不會讓散文紅 ⇒ 這是本帳本反覆在治的「散文複本必然過期」在**同一輪、同一份新落地
的鎖檔**上的實例。它同時是新斷言（欄序對釘）落地後**第一次執行就在真實資料上抓到**的一筆
——不是構造出來的樣本。

**活體後果（誠實劃界）**：今日**零**。第四欄不被任何判準消費（判準讀的是 ID／日期／分流／
狀態四欄），所以欄名寫錯不影響任何裁決。P2 給的是「機制」而非「後果」。

**修法**：欄名散文升為 `_COL_HEADERS` tuple，並以新測試把四者對釘：
①散文欄序 ②寫死的欄位索引（`_IDX_ID`／`_IDX_DATE`／`_IDX_TRIAGE`／`_IDX_STATUS`）
③磁碟上的真表頭 ④閘門 `_table_layout()` 的定位結果。任一側漂移即紅，且訊息直接給出改法。

---

## DEF-101-583

**現象（Pkg-P11 自查；與 `DEF-101-580` 同機制，但落在另一支工具、後果更重）**：
`archive_defect_log.py` 的切欄複本會**依誤讀的狀態把「狀態不明的列」真的寫進 archive**。

**實測構造**（狀態欄留空 ＋ 分流去向欄寫一句含 `fixed` 的散文）：

```
| DEF-999-901 | 2026-07-29 | 構造 | 構造現象 | P3 | 已於上游 fixed 故不另修 |  |
```

修前行為：`_cells` 只切出 6 欄（末欄空字串被 `if c.strip()` 濾掉）⇒ `cells[-1]` 讀到
**分流去向欄** ⇒ `_classify` 在該散文裡命中 `fixed` ⇒ `cls='fixed'`、`blockers=[]`
⇒ **判為可搬**。

**為何比 crossref 那側重**：`check_defect_log_crossref.py` 的同型缺陷（`DEF-101-580`）
只是「讀錯狀態並印出來」——人還看得到、還能對帳。**本工具會依這個裁決真的把該列寫進
`archive_NN.md`**，而 archive 是逐字保全、零刪除的史料檔 ⇒ **一筆狀態不明的缺陷被靜默下葬、
主檔零承接者**。這與 `DEF-101-517`／`526` 被誤搬（散文裡有活 backlog 卻當一般已結列搬走）
是同一個後果類別，只是觸發面從「散文」換成「欄位定位」。

**修法＝雙防線**（缺一都不夠）：

1. **表頭定位**：切欄改以表頭實測欄數定位欄位，不再靠 `if c.strip()` 過濾
   （委派 `gate._row_cells()`，該函式明文「絕對不可再寫回 `if c.strip()`」）。
2. **判準⑤ 欄數守門**：新增搬遷判準「該列切出的欄數 != 表頭欄數 ⇒ **一律不判讀狀態、
   一律不可搬**」。⇒ 就算未來有人在定位邏輯上再犯一次，壞列也走不進 archive。

第 2 道是刻意的冗餘：第 1 道是「把讀對」，第 2 道是「讀不準時**不准動作**」，
後者對「零刪除史料檔」這種不可逆寫入才是正確的失敗模式。

---

## DEF-101-584

**現象（Pkg-P7 自查 P7-4；Pkg-P11 複核 blast radius）**：
round 2 主控推翻方案(乙)、刪掉 `check()` 第(7)項「具名治理文件無家族專用語法的指針宣稱」
反向鎖的**程式**，卻漏改兩處散文：

1. `apply()` 標頭裡**手寫**的「共七項」保全判準清單（含已作廢的第(7)項逐字內容）；
2. `_fenced_line_numbers()` docstring 的「判準⑦ 用」。

**為何是 P2 而不是筆誤級**：**archive 是零刪除的史料檔**。`apply()` 的標頭散文每跑一次
`--apply` 就會被寫成一份**新的永久紀錄** ⇒ 那句失實宣稱會被一次次鑄進歷史，而歷史依政策
不改寫。這與本工具立帳要消滅的病完全同型（`archive_30` 標頭的第 1 項缺陷：
「宣稱一道機械檢查存在、而它不可重跑，等同沒有檢查」），**且是在同一輪、同一支工具身上復發**。

**🔴 Pkg-P11 界定 blast radius（誠實劃界，不誇大）**：

```
磁碟上 32 支 archive 逐檔搜「七項」／「具名治理文件無家族專用語法」→ 零命中
（唯一含該字串的檔是本證據檔，即這筆缺陷的紀錄本身）
```

⇒ 該失實標頭在被修掉前**從未真的被 `--apply` 寫出過**（引入與修復之間沒有任何一次歸檔）。
**性質＝「地雷已裝好但還沒踩到」，不是既成的史料污染。** 這一點很重要：
若照「失實宣稱已刻進歷史」來寫，本身就是一次未經實查的誇大。

**修法（根因級，不是把「七」改成「六」）**：新增兩個判準清單 SSOT 常數
`CHECK_CRITERIA`／`MOVE_CRITERIA`；`check()` 的成功訊息與 `apply()` 寫進 archive 標頭的
散文**全部由常數生成**（項數與各項標題現場算、不手寫）⇒ 「兩份說法」在結構上不可能出現。
機械鎖 `TestCriteriaListIsASingleSsot` 三項：(a) docstring 的 `(N) 標題` 與常數**雙向**互比；
(b) 每一項都必須在 `check()` 實作裡有對應的 `# (N)` 段落標記（**宣稱一項就得有一段程式**）；
(c) `apply()` 產生的標頭必須逐字含每一項標題，且不得出現超出項數的項次編號。

**Pkg-P11 落地驗證**：本輪 `--apply` 建立 `archive_32` 時，標頭確實由常數生成，
逐項與 `--check` 成功訊息一致（兩者同源）。

**🔴 Pkg-P11 額外實測：這道反向鎖的掃描面涵蓋「被搬進 archive 的表格列」，帳本因此不得逐字
複寫被作廢的字面。**

`TestCriteriaListIsASingleSsot::test_a_new_archive_header_is_generated_and_carries_no_retracted_claim`
在沙箱跑一次真的 `apply()`，然後對 **新建 archive 檔的前 4000 字元** 斷言不得出現三個作廢字樣。
4000 字元的窗口意在涵蓋「標頭」，但實務上會**溢進表格列**：Pkg-P11 把本筆缺陷寫進帳本、
其現象欄逐字引用了那句被作廢的清單字面，於該沙箱歸檔後即落在窗口內 ⇒ **鎖翻紅**
（`AssertionError: '…' unexpectedly found in "# AutoSDD Defect Log — Archive 87…`）。

判斷：**這是掃描面過寬造成的假陽性形狀**——「記錄一個關於某字面的缺陷」與
「宣稱該字面所述的檢查存在」是兩件事，前者不該被擋。它的實際後果是
**帳本永遠無法逐字保存自己要消滅的那句話**，而本 repo 的史料紀律恰恰重視逐字保全。

Pkg-P11 的處置（**不改 `.py`，本包無該所有權**）：帳本列改為描述性寫法
（「手寫的『七項』保全判準清單」）並在列內註明「該字面刻意不在本列逐字複寫」，
逐字原文保留在**本節**（證據檔不會被 `apply()` 搬進 archive，故不在該鎖的掃描面內）。
**跨包請求**：把該斷言的掃描面由「前 4000 字元」收斂為「標頭區段」
（例如切到第一個 `## 缺陷總表` 之前），使它只管它真正要管的那段散文。

---

## DEF-101-585

**現象（Pkg-P7 自查 P7-5；沙箱重現）**：判準(6)（非「立帳見」方言的居所宣稱）的**稽核面**
與判準(4)（「立帳見」指針）不對稱——判準(4) 已於 round 2（`ARCH-R60R2-05`）擴為
「帳本家族 ∪ 具名治理文件」，(6) 沒跟上，於是**治理文件內的「見主檔 DEF-x」失實宣稱零檢查**。

沙箱重現：在治理文件內寫一處失實的 `見主檔 DEF-x` ⇒ (6) 的正則命中該行，
但因該檔不在 (6) 的稽核面內，`--check` 照印 rc=0、**零訊號**。
⇒ 同一類失實宣稱在帳本家族內是硬錯誤、在治理文件內完全放行；
**這是同一支工具內部稽核面的自我不一致**，不是設計取捨。

**修法**：(6) 的稽核面收斂到與 (4) **同一份** `_pointer_audit_files()` SSOT
（工具內不另生第二條 glob），並補兩種**對稱**例外：(甲) code span 引述、(丙) 圍籬區塊。

**擴面後的兩項實測（各處數一律以 `python tools/archive_defect_log.py --check` 現場輸出為
權威，本節不寫死）**：

- **治理文件側**：(6) 形態的命中**全部落在例外內** ⇒ 擴面後**零誤紅**（不是靠放寬判準換來的）。
- **家族側**：(6) 形態的命中**零處**落在圍籬區塊內 ⇒ 補 (丙) 對家族**既有**稽核面**零削弱**
  （新開的例外沒有順手放掉任何原本擋得住的東西——這是補例外時必須自證的那一半）。

**🔴 刻意不設 (丁) 對等例外（WHY 全文）**：

(丁)＝「治理文件內未跟 DEF-ID 的提及」豁免。它存在的理由是判準(4) 對「動詞在、卻沒跟 ID」
下了**硬要求**（「立帳見」是家族專用語法，出現就得跟 ID），而治理文件會把該語法當**術語**提及。

判準(6) 的正則**結構上不同**：它要求「見主檔／見 …（現居 archive_NN）」後面跟得上可解析的
DEF-ID，**沒有 ID 就根本不命中**——所以「動詞在卻沒跟 ID」這個誤報形態在 (6) 上不存在，
**無物可豁免**。反過來說，若硬要給 (6) 也開一個 (丁)，就得先把 (6) 改成對「見」下硬要求；
而「見」是中文常用單字（本 repo 散文裡無處不在），那等於把整個 repo 的中文散文變成錯誤。
⇒ **不對稱在這裡是正確的**，對稱化才是缺陷。此段刻意寫全，避免下一輪把「(4) 有四種例外、
(6) 只有兩種」當成漏做而去補齊。

---

## DEF-101-586

**架構洞見立帳（Pkg-P9 裁決；`DEF-101-581` 的根因級歸納）**

### 洞見：SSOT 紀律必須與「引用面契約鎖」成套供應

P9 原話（保留其論證力道，逐字引用）：

> 這次的形狀比一般 refactor 事故更難防：**受害者是因為遵守 SSOT 紀律才被打斷**
> （它沒自寫第二份正則，照規矩引用上游）。所以任何「鼓勵引用 SSOT」的紀律都會同步放大
> 「上游一改就斷」的暴露面 ⇒ SSOT 紀律必須與引用面契約鎖成套供應，
> 否則等於一邊要求依賴、一邊不保護依賴。

這條的份量在於它**反轉了誘因方向**：本 repo 反覆在抓「散文/程式長出第二份複本」，
處置一律是「收斂成 SSOT、大家去引用它」。但每一次收斂都在增加「引用面」，
而引用面在本 repo **完全沒有機械保護**（`_` 前綴名稱在跨檔 SSOT 引用的慣例下事實上是公開契約，
卻沒有任何工具知道誰在引用誰）。**於是最守規矩的那支檔案暴露面最大** ——
`DEF-101-581` 的受害者正是唯一一支明文寫著「不自寫第二份」的呼叫端。

### 三點閘門盲區判斷（🔴 不是實作漏洞，是射程本來就不含）

1. **兩道帳本閘門稽核的是帳本「資料」，斷的是 Python「介面」。**
   `check_defect_log_crossref.py` 與 `archive_defect_log.py --check` 都不 import 那支測試，
   而帳本一字未動 ⇒ 它們回 rc=0 是**正確**的。要求它們攔下這件事等於要求它們超出射程。
2. **唯一看得到這件事的載體是根層 unittest 全套**——而它同時是最貴、最晚跑、
   最容易被「我只改了一個檔」說服自己不跑的那一個。
   ⇒ **事故被發現的時點取決於「有沒有人跑全套」，而不是閘門設計。**
   （本例即是：肇事包沒撞到，是下游 Pkg-P5 交件前複驗才撞到。）
3. **閘門數量給了假的安心感。** pre-push 有十幾道守門、其中兩道專看帳本，
   於是「帳本相關的東西有兩道閘門守著」這個直覺**成立**，但對這次的失敗模式**完全無效**。
   ⇒ 閘門清單的長度不是覆蓋率；問「哪一道會紅」才是。

### 處置：兩個半套，方向相反、缺一不可

| | 方向 | 落地 |
|--|------|------|
| **前半套（`P7`）** | 不准長出**複本** | 判準清單 SSOT、切欄收斂、`_COL_HEADERS`、`CHECK_CRITERIA`／`MOVE_CRITERIA` |
| **後半套（`P9`）** | 引用面不得**懸空** | `upstream_refs()`／`dangling_upstream_refs()`／`incompatible_upstream_calls()` ＋ `TestArchiveIsNotAnEscapeHatch` 內的上游契約測試 |

只有前半套＝一邊要求依賴、一邊不保護依賴（就是 `DEF-101-581` 發生的條件）；
只有後半套＝複本照樣長，鎖只是把一堆複本各自釘住。

### R61 承接（具體、可直接執行）

把那三支引用面掃描純函式**由測試內函式升級為 `tools/` 下的通用閘門**，覆蓋全庫而非只覆蓋
一支鎖檔。判準形狀不變（AST 取引用鏈＋行號 → `hasattr` 驗名稱 → `Signature.bind` 驗 arity），
要解的是三件工程問題：①掃描面（哪些檔算「跨檔引用 SSOT」）；②import 成本
（現行做法要 import 上游真模組才 `hasattr`，全庫化需處理 import 副作用）；
③既有債基線（比照 `_ARITY_BASELINE`／`_BASELINE_WAIVERS` 的具名 ＋ stale 自檢 ＋ 只准往下改）。

⚠️ **本輪刻意只補到「單一鎖檔」**：全庫化屬新工具、跨檔重構，不在本輪射程（Rule 3 外科式）。
把它寫成 R61 承接而不是「已解決」，是為了不讓下一輪讀到一個比實況樂觀的結論。

---

## Pkg-P11 交付門檻實測（量測時點：R60 round 3 Pkg-P11 交件前）

⚠️ 下列數字皆為**該次執行**的快照；判準本身不依賴它們，重跑指令逐條列出。
取 rc 一律 `cmd > out 2>&1; echo REAL_RC=$?`（接 pipe 後的 `$?` 是 pipe 尾端的，會騙人）。

```
python tools/check_defect_log_crossref.py                 → REAL_RC=0
  ✅ 缺陷帳本跨文件狀態一致：帳本 107 筆有效狀態紀錄、4 份掃描目標皆無矛盾；
     另全部表格列的狀態欄首詞皆落在《格式定義》宣告的合法值內（散文與程式常數雙向綁定）；
     全部表格列的欄數皆等於表頭欄數、狀態欄由表頭定位（非 cells[-1] 位置猜測）
  ⇒ **未印任何體積 warning**（該閘門只在主檔 >= warn 線時才印，故「沒印」即為退出 warn 帶的憑證）

python tools/archive_defect_log.py --check                → REAL_RC=0
python -O tools/archive_defect_log.py --check             → REAL_RC=0
  ✅ 帳本保全稽核通過（歸檔索引 bullet 數 == 實查 archive 檔數，判準⑤ 雙向）

python tools/run_root_unittests.py                        → REAL_RC=0
  Ran 976 tests / OK (skipped=11)
```

**🔴 過程中本包自己造成的兩支紅、如實留痕（不美化為一次做對）**

交件前第一次跑全套是 **`Ran 976 / FAILED (failures=2, skipped=11)` REAL_RC=1**，兩支都是本包寫入
造成的，逐支歸因與修法：

1. `test_archive_defect_log.TestCriteriaListIsASingleSsot::
   test_a_new_archive_header_is_generated_and_carries_no_retracted_claim` (stale='共七項')
   ——本包在帳本 `DEF-101-584` 列逐字引用了被作廢的清單字面，而該鎖的掃描面是「新建 archive
   的前 4000 字元」、會溢進被搬進去的表格列。**歸因＝掃描面過寬的假陽性形狀**，
   完整判斷與跨包請求見本檔 `## DEF-101-584` 節末段；本包處置＝帳本改描述性寫法、
   逐字原文只留在證據檔。
2. `test_defect_id_reference_integrity::test_every_referenced_defect_id_exists_in_ledger_family`
   ——本包在 `## DEF-101-583` 節的構造範例用了 101 系列的合成空號（此處刻意不逐字重寫該編號——本鎖掃描面含本檔，逐字寫出就等於再造一次空號引用），
   而該鎖要求任何被引用的 `DEF-101-NNN` 都必須在帳本家族有一列。**這道鎖是對的**
   （空號指針會把讀者導向不存在的條目），修法＝合成 ID 改用非 101 系列 `DEF-999-901`
   （與該鎖自身測試用的 `DEF-999-920` 同慣例）。

⇒ 兩支都不是既有債、也不是別包造成，是本包當輪自造並當輪修掉。第二次全套即 `OK`。

**帳本體積（LF 基準；閘門常數：warn = 240*1024 = 245,760、fail = 256*1024 = 262,144）**

| 時點 | 主檔 bytes | 距 warn | 距 fail |
|------|-----------|--------|--------|
| Pkg-P11 動工 | 245,600 | 160 | 16,544 |
| 歸檔 `archive_32`（12 筆／20,204 B）後 | 230,070 | 15,690 | 32,074 |
| 交件（寫入 5 新列 ＋ 2 補述 ＋ 指路段後） | 見下方實測指令 | — | — |

交件實數一律以 `wc -c docs/06_quality/AutoSDD_Defect_Log.md` 為權威——本表刻意不寫死交件值，
因為「寫死數字必過期」在本帳本已重演多次（`DEF-101-493`／`archive_29` 標頭的 SA-R59-08 訂正）。
