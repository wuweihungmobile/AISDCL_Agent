# AutoSDD 裁決呈報單 — 技術債分診「等裁決」28 筆（R121 分診批）

> **Status**: Adopted（2026-09-04 掌舵者落款：本檔推薦全數採用；逐筆結案由收尾單人窗口進行）
> **日期**：2026-09-02（提出）／2026-09-04（落款）
> **落款範圍**：本檔〈逐筆裁決卡〉的推薦欄位全數生效。此前已有多批結案逐筆引用本檔作為
> 裁決依據（`docs/06_quality/CrossPlatform_R121_Debt_Closure.md`、`_R126_*`、`_R127_*`
> 三份證據檔的同名 `§DEF-ID` 小節），落款只是把檔頭狀態欄對齊既成事實；落款前的每一次
> 引用在形式上都是引用一份 Proposed 文件。
> 🔴 **落款同輪查出一筆推薦的事實前提為錯，已於該筆就地加訂正註記**：`DEF-200-182` ②
> 的 `closed-by-decision` 理由（「繞過手段永不可知」）預設了「那次 push 繞過了 pre-push」，
> 而該前提經落款當回合親驗為假——見本檔 `§DEF-200-182` 的訂正註記。**落款範圍不含那條
> 已被推翻的理由**：一份文件的推薦被整體採用，不等於其中每條理由都經過覆核。
> **來源**：分診工作流 8 唯讀包對帳本 52 筆未結列的全量分類結果；本檔收錄其中
> `category=needs-arch-decision` 27 筆與 `category=needs-user` 1 筆（`DEF-200-182`），
> 共 28 筆。每筆皆於本檔撰寫當回合以 Read/Grep/PowerShell 現查帳本原文與相關程式碼，
> 逐筆核對分診結果是否忠實；不忠實處已在文末〈核對發現〉節列出並以帳本原文為準。
> **證據檔**：`docs/06_quality/CrossPlatform_R121_Debt_Closure.md` 於本檔內多處被引用
> 作為裁決落地後的存證檔——**本輪新建，撰寫本檔當下尚不存在**；裁決落地時比照
> `AutoSDD_Adjudication_Record_R110.md`／`_R120.md` 體例寫入對應 `§DEF-ID` 小節。
> **用法**：掌舵者對每筆的「推薦」欄位勾選 A／B（或另行指示），一次回覆「28 筆全採推薦」
> 或列出例外（如「124 用 B 不用 A」）即可；裁決落款後由收尾單人窗口依〈逐筆裁決卡〉
> 的「裁後動作」欄逐筆改寫帳本狀態欄並寫入證據檔對應小節。
> **體例**：本檔不使用「延後到R／交給R／留給R／承接輪次：R」等前瞻輪號句型；提及下一次
> 動工窗口一律寫「下一結案窗口」或「下一結案單人窗口」。表格儲存格內不使用半形 `|`，
> 分隔一律用全形「／」。

---

## 一、一頁總表

| ID | P | 一句話缺陷 | 推薦 | 裁後結案形態 | 批次 |
|---|---|---|---|---|---|
| DEF-101-736 | P2 | 已結列 DEF-101-729 退場後「跨樹一致性保障消失」的殘留待辦，四筆真待辦已併入本列承載 | 方向B | 部分closed-by-decision（跨樹鎖不重建；557/649/880 三子項仍各自殘留） | A |
| DEF-200-124 | P2 | prose 分桶棘輪以 chunk 為計量單位，含單一路徑指標的整塊會被誤算進 prose 桶 | 方向A | 仍open需開發 | A |
| DEF-200-172 | P3（⑦待複評） | R96 收斂窗口彙整的八子項散雜發現，⑦已修其餘七項各自殘留 | 分項裁 | 部分closed-by-decision＋部分仍open | A |
| DEF-200-213 | P3 | R100 收尾窗口彙整的帳本體例三筆殘留，現查②③④皆已滿足 | 方向B | closed-by-decision | A |
| DEF-200-241 | P3 | 帳本時鐘凍結（零輪號紀律）× 豁免面 shrink-only 兩條紀律相乘造成結構性結案死結 | 方向B | 仍open需開發 | A |
| DEF-200-207 | P1 | ADR-XPLAT-013 機械物已在生產跑但文件狀態仍卡 Proposed，§7 解鎖清單多項未清 | 分項裁 | 部分：doc-fix＋仍open待複審 | B |
| DEF-101-610 | P2 | 「同輪並行修復包互不知情致設計文件前提失效」已於 ADR-XPLAT-002 復發四次 | 方向A | closed-by-decision | B |
| DEF-200-137 | P2 | draining() 只做 PRD §4.3 第二個 AND 條件的一半，缺 COMPACT_COST_BUDGET_PP 邊際 | 方向A | 仍open需開發 | C |
| DEF-200-242 | P2 | `_cap_for()` 對 free 帶四格 horizon 恆回 None，PRD §11.2「重置後不暴衝」無落點 | 方向A | 仍open需開發 | C |
| DEF-200-243 | P3 | `windows()` 鄰軸繼承通道方向未經證據裁決，量測顯示繼承會讓保守設計反而加速 | 方向B | 仍open需開發 | C |
| DEF-200-244 | P3 | gate 聚合面 `gate_list or readings` 是 §4.2.2-b(4) 未涵蓋的第三通道，動它會碰兩次憲法裁決 | 方向B | 仍open需開發 | C |
| DEF-200-065 | P2 | skip_* 六模組族收斂重構診斷未動，②③兩子項現查已緩解/已修 | 方向B | closed-by-decision | D |
| DEF-101-951 | P3 | skip 判準被 LOC tier 切成 6 模組，兩支 compat-ci workflow 各自抄一份清單共 4 處複本 | 方向B | 仍open需開發 | D |
| DEF-200-155 | P3（判準的結構性後果） | skip 天花板棘輪分母隨對面平台工作變動，每次平台切換工作必先重釘常數 | 方向B | closed-by-decision | D |
| DEF-101-863 | P2 | 全樹 skip reason 是否要逐支套用「含可執行指令/旗標名」的可操作性鎖 | 方向B | closed-by-decision | D |
| DEF-101-867 | P2 | 帳本內部矛盾（同輪兩列互相矛盾宣稱）偵測器原型訊噪比僅約 25% | 方向B | closed-by-decision | D |
| DEF-101-981 | P2 | R81 收尾窗口彙整六項 not_done，現查①③已兌現、②仍待開發、④⑤⑥各自需裁 | 分項裁 | 部分closed-by-decision＋部分仍open | D |
| DEF-101-060 | P3 | AutoClaude/pyproject.toml 17 個套件依賴宣告無版本上限 | 方向B | closed-by-decision | E |
| DEF-101-856 | P2 | R76 收斂包彙整六項 not_done，現查①⑤已兌現、②③④⑥各自殘留 | 分項裁 | 部分closed-by-decision＋部分仍open | E |
| DEF-101-926 | P3 | 兩支 monorepo 級 hook 實際住 AutoClaude 子專案樹，靠根 settings.json 橋接生效 | 方向B | closed-by-decision | E |
| DEF-101-938 | P3 | shellcheck 閘門本機零接線，僅 shellcheck-ci.yml 單邊執行 | 方向A | 仍open需開發 | E |
| DEF-200-084 | P1 | 另一 Claude session 於同棵樹 git stash 清空追蹤檔，本 hook 結構上看不到別的 session | 方向B | closed-by-decision | F |
| DEF-200-118 | P1 | PRD §15.6 靜默計費告警半邊現查程式面零命中，保險軸移出 cap 聚合後在多數帶零觀測者 | 方向A | 仍open需開發 | F |
| DEF-200-191 | P2 | 「錨不到＝放行」的鮮度判準製造反向誘因（照實引舊值被唸、憑空捏造反而放行） | 方向B | closed-by-decision | F |
| DEF-101-803 | P2 | 零相依探針今日不重跑整棵樹依賴 MIN_TESTS 餘裕的巧合，非結構保證 | 方向B | 仍open需開發 | F |
| DEF-200-206 | P2 | PRD v2.1 與實作三處歧異（STATE_RETAIN_VERSIONS／CONFLICT_POLICY／env 讀取路徑） | 分項裁 | 仍open需開發 | G |
| DEF-200-182 | P1 | 交件〈驗證〉節漏列 local_ci_gate／AISDLC_SDD 測試套，繞過手段的取證載體已不存在 | 分項裁 | 部分closed-by-decision＋needs-user核准後開發 | G |
| DEF-200-167 | P2 | DEF-200-150 修復未採 R91 §I-22 正解，仍是模組屬性替身、同族替身≥14 站點 | 方向A | 仍open需開發 | G |

---

## 二、分批議程

七批，依主題分組——同批內的裁決共用同一組事實或同一鎖持有面，一次呈報可省去重複舉證：

### 批次 A｜帳本治理與流程機械物（5 筆：736／124／172／213／241）
五筆都是帳本自身的記帳機制問題（併列殘留、分桶棘輪計量單位、時鐘凍結死結），不是產品程式碼缺陷。共用同一套「合法狀態首詞／ROW_MAX_BYTES／棘輪 shrink-only」帳本編輯紀律，且部分共用鎖持有面（`tools/lib/defect_ledger_index.py`／`tools/tests/test_adr_xplat001_c1c2_lock.py` 的棘輪常數），一次裁決可避免同一份棘輪被重釘五次。

### 批次 B｜ADR-XPLAT-013／ADR-XPLAT-002 治理槓桿（2 筆：207／610）
兩筆都在問「一份治理設計文件自身的可轉紅不變式，能否替代一道獨立閘門」；610 的裁決先例（ADR 自身 SC 條款隨 `run_root_unittests.py` 執行即等於前提清單重跑）可直接作為 207 判斷 U1~U4 審查形式的參照，同批裁一次講清楚判準比分兩次省。

### 批次 C｜配速／額度修憲殘留（4 筆：137／242／243／244）
四筆都是 `PRD_Amendment_R108_Pacing.md`（已 Adopted）留下的「還差一個方向裁決」殘留項，鎖持有面同樣落在 `tools/lib/quota_policy.py` 的 `decide()`／`_cap_for()`／`_pace_of()` 一組函式與同一批 `test_quota_policy.py` 方向鎖，且四筆都要進同一場四方複審佇列——一次呈報可省下四次重開「配速修憲」複審的成本。

### 批次 D｜skip 剖面與平台判準體系（6 筆：065／951／155／863／867／981）
六筆都圍繞 `tools/lib/skip_*.py` 家族——是否要新建偵測器／白名單／同步鎖，還是接受「平台切換必重釘」為既定儀式。同一條政策判準（「訊噪比 <80% 不上新機械物」「重釘儀式已有 SOP 且被共同變更鎖機械化」）可以一次回答六筆裡的多數，避免逐筆重複論證同一套政策。

### 批次 E｜R76～R81 舊債／護欄層歸屬（4 筆：060／856／926／938）
四筆都是 R76～R81 掃描期間發現、迄今數十輪未有人動工的「是否值得建新機械物」問題。「改派輪次卻無人接手 N 輪以上」本身就是可觀測的成本效益訊號，同批用同一條「無人動工的持續期間即是證據」的判準收斂最省。

### 批次 F｜跨 session／哨兵事故防護與探針結構邊界（4 筆：084／118／191／803）
四筆的共同結構是「保護機制存在盲區，但盲區是設計邊界還是待修」——跨 session 事故、告警半邊零觀測者、錨不到判準的放行設計、探針逾時的巧合式安全。同一條「先偵測出聲、不做過度阻斷」的姿態選擇可以一次適用於前三筆，第四筆（803）雖屬同批但落點是小型結構修，仍共用「這是設計取捨而非工程量」的討論框架。

### 批次 G｜PRD／實作對齊與交付稽核（3 筆：206／182／167）
三筆都是「規格與實作出現落差時，修規格還是修實作」的裁決類型（PRD 三鍵歧異、驗證清單缺口、替身注入點契約），適用同一套「憲法優先順序」判準：實作沒照 PRD 做 → 修實作；PRD 與實測不符 → 修憲。

---

## 三、逐筆裁決卡

### 批次 A｜帳本治理與流程機械物

#### DEF-101-736（P2／批次A）
**發現情境**：R69 終審 QA 覆核 archive_48 已結列的殘留待辦時發現——`DEF-101-729` 標 fixed 並歸檔，但其退場後「跨樹一致性保障消失」的承接項沒有任何機械追蹤載體，本列即該承接項的獨立載體；後續四筆真待辦（557／560／649／880）依判例併入本列承載。
**字面解鎖條件**：「解鎖條件＝(i) 逐字回讀 archive_48 內 DEF-101-729 全欄確認該保障的原始射程；(ii) 補上替代鎖並附注入紅綠，或以 closed-by-decision 具名裁決；(iii) 落地後本列改 fixed」
**方向 A**：重建跨樹「安全性質對齊」契約檔／黃金樣本（兩側各自讀同一份危險輸入清單，不互相 import），估新增測試約 40 行，且橫跨 `tools/tests/` 與 `AISDLC_SDD/scripts/tests/` 兩個持有面，鐵律七下不得並行派工。
**方向 B**：closed-by-decision——原鎖真正缺陷是「跨子專案 import」而非「兩側行為分歧」，兩側今日各自已有獨立鎖（`tools/tests/test_windows_forbidden_filename_parity.py`／AISDLC_SDD 側 `test_component_sanitizer_reserved_trailing_space.py`），且 R57 起兩側同步修改有帳可查。
**推薦**：方向 B——射程 P1 的 `DEF-101-729` 已結案，跨樹鎖成本高於它所防的風險；但併入的四筆真待辦各自狀態不同，不能靠這一項裁決把整列一次結清：557 已由 `DEF-101-916` 滿足、560 已有 `CrossPlatform_R85_Ledger_Closure.md §11` 的三點具名不修理由（待正式裁 wontfix）、649 待 Darwin 真機執行、880 待以新尺重算違規率。
**裁後動作**：
> 部分closed-by-decision（跨樹一致性鎖不重建：兩側各自已有獨立鎖，原缺陷屬「跨專案 import」非「行為分歧」，依據見 `CrossPlatform_R85_Ledger_Closure.md §11`）；併入子項 557 依 `DEF-101-916` 已滿足、560 另裁 wontfix、649 待 Darwin 真機、880 待重算違規率——詳 `CrossPlatform_R121_Debt_Closure.md §DEF-101-736`；2026-09-02

**開發量**：零程式碼（跨樹鎖裁決本身）；殘留 649／880 各需 S 級後續動作（分別待 macOS 真機與重新量測，非本裁決單射程）。

---

#### DEF-200-124（P2／批次A）
**發現情境**：R89 收尾窗口發現 `guard_bucket_policy.py` 的 prose 分桶棘輪以 AST 頂層 chunk 為計量單位而非行數——`test_quota_policy.py` 三個因搬遷體例帶了一行 `docs/` 指標的區塊，被整塊算進 prose 桶，造成 +6 行實質卻讀出 +157、以及 −74／−69 的假減法訊號。
**字面解鎖條件**：「候選＝指標行單獨形成的 prose 歸屬比照 `reference_counts()` 的 `self_name` 先例。需四方複審」
**方向 A**：指標行遮罩——`reference_counts()` 在計數前把「整行只有一個 `docs/…` 路徑指標」的行遮成 `\x00` 再計數，比照既有 `self_name` 先例；塊仍以 chunk exclusive 歸屬，只是純指標行不再把整塊翻進 prose。落地後需同窗重釘 `_FROZEN_SHRINK_ONLY_BUCKET_LINES` 為下修後的實測值，估新增測試約 20 行。
**方向 B**：wontfix——把此現象寫進 `guard_bucket_policy.py` 已知射程上限段，作為已知的、可容忍的 artefact，不改判準。
**推薦**：方向 A——改動最小、是列上原本具名的候選、且保留既有 chunk 粒度設計理由不動搖；但常數／判準／消費端／史料四面分住不同檔（鐵律七），只能由單一包一次做完，且需先過四方確認方向本身。
**裁後動作**：
> open（2026-09-02 裁決方向 A：`reference_counts()` 新增純路徑指標行遮罩，比照 `self_name` 先例；落地後同窗重釘 `_FROZEN_SHRINK_ONLY_BUCKET_LINES`；設計與紅綠規格見 `CrossPlatform_R121_Debt_Closure.md §DEF-200-124`；承接：下一結案單人窗口）

**開發量**：M

---

#### DEF-200-172（P3（⑦待複評）／批次A）
**發現情境**：R96 修復包 C1+D1 收斂窗口彙整的八筆順手項發現：①`SentinelWiringTest` 正負向等待時間無方向鎖；②`_HOME_ARTIFACT_DIRS` 豁免面過寬；③帳本體例三筆殘留；④座標漂移；⑤`mkdtemp`/`rmtree` 比例失衡；⑥沙箱鎖 docstring 與實作不符；⑦`_DISPOSABLE_WT` 對 `..` 穿越失明；⑧`setup_logger` 沿用舊握把無鎖。
**字面解鎖條件**：「逐筆明細＝R96 掃描發現 §F」；狀態欄另記「③ 第三筆須改根 CLAUDE.md」。
**現查更新**：⑦已由 P0-1 改 realpath+normcase 前綴比對修復，針對性測試 `test_dotdot_traversal_disguised` 現查為 `1 passed, 157 deselected, 2 subtests passed`。
**方向 A**：逐子項各自裁決/派工——②⑤③.1③.2 判 closed-by-decision（②常數已自辯別台機器分佈量不到、⑤tempdir 殘留是既有取證路徑且 OS 會回收、③.1③.2 屬帳本既有體例規則已涵蓋）；⑦以座標補憑證結案；①⑥⑧④各自需一道新鎖（needs-dev，可各自單獨派工，不互相阻塞）；③.3 為 doc-fix 但因改動根 `CLAUDE.md` 主檔須收尾單人窗口執行。
**方向 B**：維持整列 open 直到八個子項全部完工才結案——代價是已完工的⑦與可裁決的四個子項持續佔用未結分母（帳本治理根因五：併列壓縮使部分完成卡 open）。
**推薦**：方向 A——依 §5 發現節流閘精神拆分處置，避免單一併列因一個子項卡住而讓其餘七個已可處理的子項一起被鎖住。
**裁後動作**：
> 部分closed-by-decision（⑦已修待憑證入證：`test_dotdot_traversal_disguised` 現查 1 passed；②⑤③.1③.2 依 2026-09-02 裁決 closed-by-decision，理由與座標見證據檔；①④⑥⑧ 留 needs-dev 各自派工，③.3 doc-fix 留收尾單人窗口）；詳 `CrossPlatform_R121_Debt_Closure.md §DEF-200-172`；2026-09-02

**開發量**：分項混合——⑦②⑤③.1③.2③.3 零程式碼；①④⑥⑧ 各 S 級（合計約當 L）。

---

#### DEF-200-213（P3／批次A）
**發現情境**：R100 收尾窗口彙整帳本治理殘留三筆：①`DEF-200-137` 的 F3/F4 兩筆無關發現仍與主發現擠同一列（該列 699 bytes 已頂 `ROW_MAX_BYTES`）；②`DEF-200-195` 當時無回歸鎖；③crossref 曾列出 18 筆已結列殘留待辦。
**字面解鎖條件**：「① 拆列須配合 archive 搬遷；② 落 `tools/tests/` 受 DEF-200-208 死結阻擋；③ 真待辦須拆出獨立列」
**現查更新**：②現查 `TestDef200195CrossRowReceiptFreshnessIsNotSelfSatisfied` 為 `4 passed`，已落地；③現查 `check_defect_log_crossref.py` 輸出全為 ✅、無「已結列殘留待辦」告警，殘留待辦現值為 0，無可拆對象；僅①（F3/F4 拆解）仍待裁決。
**方向 A**：F3／F4 各自拆成獨立未結列——在純結案輪淨額棘輪「新增 ≤ 結案」的約束下等於新增 2 筆未結列。
**方向 B**：依 Playbook §5 第 2 條把 F3／F4 改判為 advisory 記入具名證據檔（不佔未結分母），`DEF-200-137` 列本體待其自身結案時隨 archive 搬遷順帶清理。
**推薦**：方向 B——F3 自書「今日 0 例」、F4 自書「脆弱綠非假綠」皆屬觀察級而非本回合觸發的缺陷，且 `DEF-200-137` 列已頂 `ROW_MAX_BYTES` 無法就地改動。
**裁後動作**：
> closed-by-decision（②③現查已滿足：`TestDef200195...` 4 passed、殘留待辦現值 0；①F3/F4 改判 advisory 記入證據檔、不另立列，依據：兩者皆觀察級且非本回合觸發缺陷）；詳 `CrossPlatform_R121_Debt_Closure.md §DEF-200-213`；2026-09-02

**開發量**：零程式碼

---

#### DEF-200-241（P3／批次A）
**發現情境**：212 結案批交付時發現的結構死結——「發現情境」欄零輪號紀律使 `current_round()` 凍結於歷史值（自動祖父化永不觸發），與豁免面 shrink-only 禁止增長兩條各自正確的紀律相乘，使已完工的 `DEF-200-212` 卡成結構性不可結案；掌舵者已核准 D8 一次性把 `_CARRIER_DOC_EXEMPTIONS_MAX_ENTRIES` 從 3 調到 5，並明文「不得援引為再次調高的先例」。
**字面解鎖條件**：「治本二擇一：時鐘前進機制／祖父化改讀結案事實；D8 一次性核准不得重複」
**方向 A**：時鐘前進機制——讓 `current_round()` 不再只讀「發現情境」欄輪號（改讀證據檔／交棒書最大號，或設一個顯式時鐘常數每輪重釘）；風險是重新引入一個每輪要人手推的數字，且與「發現情境欄零輪號＝不推時鐘」的既有紀律初衷相乘。
**方向 B**：祖父化改讀結案事實——交接載體前瞻行指名的 DEF-ID，只要在帳本狀態欄已為 `fixed`／`closed-by-decision`／`wontfix`／`no_action_needed` 即自動出局，不再比較「目標輪 < 當前輪」；優點是語意等同「那件事真的做完了」、不依賴任何時鐘，既有 5 筆豁免可望全數退場讓上限回到 0；需注意判準只讀帳本狀態首詞、不讀其他欄位，以避免「寫帳本改變閘門輸入」型迴圈重演。
**推薦**：方向 B——語意最貼近實情，且能讓豁免表歸零而非持續累積；本身需要新讀取帳本狀態的邏輯，成本可控，但依裁決要求需先過四方複審才能動碼。
**裁後動作**：
> open（2026-09-02 裁決方向 B：`check_handoff_carriers.py` 判準改為讀帳本狀態首詞而非比較輪號，指名 DEF-ID 已 `fixed`／`closed-by-decision`／`wontfix`／`no_action_needed` 即出局；設計與風險緩解見 `CrossPlatform_R121_Debt_Closure.md §DEF-200-241`；四方複審通過後方可動碼；承接：下一結案單人窗口）

**開發量**：L（判準改寫＋self-test 紅綠＋豁免表淨減，鐵律七限單人窗口一次做完）

---

### 批次 B｜ADR-XPLAT-013／ADR-XPLAT-002 治理槓桿

#### DEF-200-207（P1／批次B）
**發現情境**：R100 收尾窗口稽核護欄層治理時發現 `ADR-XPLAT-013`（LOC 計價／assertion-only 政策）機械物已在生產跑，但 ADR 文件狀態仍卡 `Proposed`；§7 解鎖清單 U1~U10 中多項未清，其中 U9（`[ROOT-TOOLS]` 舊尺度技術債真拆）依到期輪常數現查已到期，若不處理會在本輪收尾前轉紅。
**字面解鎖條件**：「四方已重開並裁決 E1/E4；E3 已改判 provenance；`--repin-cap`／`--update` 已於收尾追加回合實跑」
**現查更新**：U10 現查 `check_loc_budget.py --json` 已回 `cap_basis_pinned: true`，但 §7 表格文字仍標 ☐，屬純文件同步問題；U9 現查 `root_tools_debt_due_problems(latest_round=121)` 會回報「技術債逾期」，`_RESOLVED=False`；U1~U4（四方獨立審查）現查仍全數 ☐ 未進行。
**方向 A**：立即真拆 `[ROOT-TOOLS]` 四支檔約 −187 行以清償 U9——時限最硬但工程量中等，且需同窗處理另外三筆檔案的重構風險。
**方向 B**：由本次裁決具名展延 U9 到期輪並附理由，避免收尾窗口被鎖死；同批完成零程式碼的 U10 文件字面訂正，並啟動 U1~U4 的四方獨立審查以推進 ADR 狀態轉 `Accepted`。
**推薦**：方向 B——U9 真拆屬獨立中型工程，不應與本裁決單捆綁；U10 是零成本的文件同步，可立即做；U1~U4 審查應盡快啟動但非本裁決單能自行完成（需主控／收尾窗口開啟審查）。
**裁後動作**：
> 部分（U10 doc-fix：§7 表訂正為現值 `cap_basis_pinned=true`；U9 到期債具名展延並附理由——見 `CrossPlatform_R121_Debt_Closure.md §DEF-200-207`；U1~U4 四方獨立審查與 U7 逐站點訂正留待下一結案窗口）；2026-09-02

**開發量**：U10 零程式碼；U9 真拆與 U7 逐站點訂正另計 M～L（非本裁決單射程）。

---

#### DEF-101-610（P2／批次B）
**發現情境**：R60 交件時揭露「同輪內並行修復包互不知情、致設計文件前提失效」的失效模式，已在 `ADR-XPLAT-002` 復發四次（`DEF-101-610`／`615`／`626` 及訂正句自身）；R67 已在該 ADR §9.1 落下 SC-1～SC-10 等可轉紅不變式並由 `tools/run_root_unittests.py` 消費，針對性測試現查 `12 passed, 50 subtests passed`。
**字面解鎖條件**：「① 設計文件在收輪前必須重跑一次自身前提清單，目前沒有任何閘門在跑 SC 條款的 rc；② 解鎖＝把 SC 條款搬進 `tools/tests/` 的既有鎖檔並由 `tools/run_root_unittests.py` 消費；③ 具名承接者須在動工當輪的帳本列寫明」
**現查更新**：條件②現查已達成（`_SPEC_ADR2` 與 `TestSection91InvariantsAreLive`／`TestSection91InvariantsHaveTeeth` 皆在，針對性實跑綠）；條件①③現查仍未有通用機械物或具名承接者，但四次復發全部發生在同一份 ADR 文件內。
**方向 A（甲）**：closed-by-decision——裁定「SC-1～SC-10 隨每次 `tools/run_root_unittests.py` 執行，即等於每輪收輪前重跑一次該 ADR 的前提清單」，把本失效模式視為已被機械承接；若未來出現第二份設計文件同型失效，屆時另立新列。
**方向 B（乙）**：建立通用的跨設計文件「前提清單重跑」機制——但現查 repo 內沒有任何其他設計文件持有可機械讀的前提清單，屬 L 級新設計，且尚無第二個案例證明通用性需求。
**推薦**：方向 A（甲）——四次復發皆集中在同一份文件、該文件已有十條可轉紅不變式且進 pre-push；乙屬無實證支持的過度設計。
**裁後動作**：
> closed-by-decision（本列訴求已由 `ADR-XPLAT-002 §9.1` SC-1～SC-10 隨 `tools/run_root_unittests.py` 每輪執行機械承接；依據：四次復發皆在同一份文件、十條不變式已進 pre-push，通用跨文件機制無第二案例佐證；若日後出現第二份文件同型失效另立新列）；2026-09-02

**開發量**：零程式碼

---

### 批次 C｜配速／額度修憲殘留

#### DEF-200-137（P2／批次C）
**發現情境**：R91 QA 複審發現 PRD §4.3 的第二個 AND 條件只做一半——`draining()` 僅判斷 `U5h ≥ DRAIN`，缺 `COMPACT_COST_BUDGET_PP`（PRD §6 定義為 3pp）的邊際，`(DRAIN−3, DRAIN]` 區間內仍會誤發 compact 建議；全 repo 對該常數現查為零命中。
**字面解鎖條件**：「接進 `draining()`；F3＝`emit_to_model` 事件名沿用首次，漏帶 `event=` 的新 PostToolUse 站點即兩則全丟、零鎖；F4＝`LatchRearmTest` stdout 斷言被前次 tmp 閂鎖過度決定＝脆弱綠非假綠」
**方向 A**：實作 PRD 字面——`draining()` 在 five_hour 軸以 `pct + COMPACT_COST_BUDGET_PP > DRAIN(prepare_pct)` 判定，常數居所待落地包定案（`quota_policy.py` 或 `quota_gate.py`），`PrdDrainPercentMapsToTheBandsTest` 加一格對帳，估新增生產約 10 行、測試約 25 行。
**方向 B**：修憲——PRD §4.3 改為以 band 邊界近似、刪除 3pp 邊際，理由是 autocompact 已由 harness 機械觸發（`ADR-XPLAT-008`），hook 本身只勸不執行。
**推薦**：方向 A——PRD §0 第 1 條把此列為阻斷級，生產文字（`_NEXT_STEP["no"]`）已自陳這個缺口，工程量小；但常數居所與軸選擇屬設計裁決，需先定案才能動碼。F3（`event=` 靜態鎖）另案裁是否需要；F4 屬觀察級，本次不影響主項分類。
**裁後動作**：
> open（2026-09-02 裁決方向 A：`draining()` 補 `COMPACT_COST_BUDGET_PP=3pp` 邊際，常數居所與軸選擇待落地包定案；F3／F4 兩項記入證據檔為觀察級、不另裁；設計見 `CrossPlatform_R121_Debt_Closure.md §DEF-200-137`；承接：下一結案單人窗口）

**開發量**：M

---

#### DEF-200-242（P2／批次C）
**發現情境**：P1-8 盤點揭露 `_cap_for()`（`tools/lib/quota_policy.py:424-437`）對 free 帶四格 horizon 恆回 `None`，使 PRD §11.2「重置後不暴衝」在 free 帶完全無落點；既有測試已把 free 帶 `cap is None` 釘成錨點①（例如 `test_context_budget_guard.py:9358`），任何修法都要先動這個錨點。
**字面解鎖條件**：「free 帶 cap 語意需先有證據再定向；§4.2.4 (c) 等本列落地」
**方向 A**：時窗限定 cap 夾層——只在「reset 翻頁後第一拍」對 free 帶套 `cap ≤ cap_notice`，穩態 free 帶維持 `None`；落地前需先從 `quota_burn.jsonl` 量出翻頁後第一拍的實際扇出／燃燒證據，同時滿足 PRD §11.2 與錨點①。
**方向 B**：修憲——改 PRD §11.2 讓錨點①明文優先、free 帶維持不設限，等於把「翻頁暴衝」風險寫成可接受的既定行為。
**推薦**：方向 A——但落地前必須先出量測（唯讀探針），量出證據後才能正式改 `quota_policy.py` 與四處 `assertIsNone` 錨點測試；本裁決單先確立方向，量測工作留給下一結案窗口先行。
**裁後動作**：
> open（2026-09-02 裁決方向 A：free 帶採時窗限定 cap 夾層，僅限 reset 翻頁後第一拍生效；落地前需先出 `quota_burn.jsonl` 翻頁扇出量測，探針規格見 `CrossPlatform_R121_Debt_Closure.md §DEF-200-242`；承接：下一結案單人窗口）

**開發量**：M（含量測與四處錨點測試同步）

---

#### DEF-200-243（P3／批次C）
**發現情境**：P1-8 盤點揭露 `quota_pace.windows()` 對文法解不出窗長的軸，會由「同 reset 的鄰軸」繼承最短窗長；`R110` 裁決 Q9(ii) 已明文要求「另立缺陷列」，但繼承方向本身尚未經證據裁決。
**字面解鎖條件**：「先量測繼承通道的實際影響再裁向」
**現查更新**：量測數據其實已存在於 `PRD_Amendment_R108_Pacing.md §8-11`：把 L2 整拿掉只留 L1，109,800 個加軸對中仍有 1972 個讓 rec 變大；加回 L2 則有 2036 個；首例顯示「spend 剩 504 分無鄰軸時窗長 `None`⇒far×0.5，加同 `resets_at` 的 `weekly_all` 後繼承 10080⇒near×2.0⇒rec 4→16」——缺的是方向裁決本身。
**方向 A**：保留現行繼承（docstring 理由：取最短鄰軸窗長更保守）——但實測首例顯示繼承讓判定從 far×0.5 翻成 near×2.0、rec 4→16，方向其實是加速，與「加速是唯一會燒掉額度的方向」的自陳原則矛盾。
**方向 B**：拆掉 horizon 對繼承的依賴——文法解不出窗長時該軸一律走絕對門檻（沿既有 `thresholds()` 的 `window None` 分支），繼承值只留給顯示／L2 分類以外的用途，符合「不確定時不放寬」的 fail-safe 原則。
**推薦**：方向 B——量測數據已在案，改動最小（`quota_policy._pace_of` 或 `windows()` 呼叫端一處），封閉面實測顯示 0 個受影響案例；需四方確認不觸及 `R110` 裁決 Q9(i) 既有的 A2=4 結論。
**裁後動作**：
> open（2026-09-02 裁決方向 B：`windows()` 鄰軸繼承拆離 horizon 判定，文法解不出窗長時一律走絕對門檻、不放寬；量測依據見 `PRD_Amendment_R108_Pacing.md §8-11` 與 `CrossPlatform_R121_Debt_Closure.md §DEF-200-243`；四方確認不觸 `R110` Q9(i) 後落地；承接：下一結案單人窗口）

**開發量**：S

---

#### DEF-200-244（P3／批次C）
**發現情境**：P1-8 盤點揭露 `decide()` 內 `gate_list or readings`（`tools/lib/quota_policy.py:634-635`）是 PRD §4.2.2-b(4) 條文未涵蓋的第三條聚合通道——`gate_list` 由空翻非空時，`FALLBACK_KINDS`／未命中的 `MODEL_SCOPED_KINDS` 軸會整批離開聚合面；量測顯示定向兩例 rec 從 4 變 16，動它會碰到 `R89`／`R98` 兩次憲法裁決與明文 fail-safe。
**字面解鎖條件**：「憲法級：先四方對 (4) 第三通道定條文再動碼」
**方向 A**：加單調性夾層——`gate_list` 由空翻非空時 rec 不得高於「全部軸參與」的結果，即 `min(rec_with_gate, rec_all)`；後果是保險軸／未命中模型軸重新透過夾層否決主力，實質推翻 `R89`「保險池不得一票否決主力」的既有裁決，代價高。
**方向 B**：條文明文承認 gate 面切換是 (4) 的設計內例外（新增 (4c)：排除保險軸／未命中 scoped 軸屬取數層裁決，不受多軸單調律約束），並保留既有 fail-safe；程式零改，只補 `gate_excluded=<kinds>` 進 reason 提高可觀測性。
**推薦**：方向 B——實測 4→16 正是 `R89` 裁決想要的方向（訂閱窗有餘裕時不被關著的保險池壓成 cap=0），用方向 A 治它等於重開已判過的憲法。
**裁後動作**：
> open（2026-09-02 裁決方向 B：PRD §4.2.2-b 新增 (4c) 明文承認 gate 聚合面切換為設計內例外，程式僅補 `gate_excluded` 痕跡；理由見 `CrossPlatform_R121_Debt_Closure.md §DEF-200-244`；四方複審為必經前置；承接：下一結案單人窗口）

**開發量**：S（一則條文＋一條 note 測試）

---

### 批次 D｜skip 剖面與平台判準體系

#### DEF-200-065（P2／批次D）
**發現情境**：R84 護欄層盤點發現 `skip_*` 六模組族疑似複製 quota 族的「固定成本大於內容」形態（如 `skip_source_io.py` 曾只 35 loc），應收斂成政策／掃描／門面三支；另兩子項為 `skip_group_policy.py` 曾 399/400 貼牆、`quota_ledger.py:6` 散文數字曾失實。
**字面解鎖條件**：「①是重構、②的可行出口是剖面登記表改放低占用檔」
**現查更新**：②現查 `skip_group_policy.py` 現值 362/400（餘裕 38），已非貼牆狀態；③現查 `quota_ledger.py:6` 已有訂正段對齊現值（`SPECIAL_FILES` 門檻現查為 1089），與散文一致；①（六模組合併）現查近期 commit 記錄無任何合併重構，`skip_source_io.py` 現值 18 loc（列上「僅 35 loc」已過時）。
**方向 A**：派重構——把 6 支合成政策／掃描／門面三支；但 `skip_group_policy`（362）＋`skip_tag_policy`（298）任兩支合併即超過 `guardrail_lib` 400 行上限，hub tier 名額已被 `quota_gate` 佔用，需同時動 `check_loc_budget.py` 常數，屬 L 級架構變更。
**方向 B**：closed-by-decision——六支各自低於 400 行上限，`P1-6` 共同變更鎖已把「四層漏補」的一致性風險機械化，收斂的原始動機（固定成本大於內容、貼牆）現查已不成立。
**推薦**：方向 B——裁決後同時把②③現值寫入狀態欄訂正。
**裁後動作**：
> closed-by-decision（skip_* 六模組族不合併：六支各自低於 `guardrail_lib` 400 行上限，`P1-6` 共同變更鎖已機械化跨檔一致性風險，原「固定成本大於內容」動機現查已不成立——`skip_group_policy.py` 現值 362/400）；②③現值已訂正；詳 `CrossPlatform_R121_Debt_Closure.md §DEF-200-065`；2026-09-02

**開發量**：零程式碼

---

#### DEF-101-951（P3／批次D）
**發現情境**：R80 包 C 發現 skip 判準被 LOC tier 切成 6 個模組，清單在兩支 compat-ci workflow（`windows-compat-ci.yml`／`macos-compat-ci.yml`）各抄一份，共 4 處複本；AISDLC_SDD 側 `test_ci_paths_cover_root_consumers.py` 雖有相等鎖，但現查該鎖不在根層 unittest 閘門射程內。
**字面解鎖條件**：「建議先下沉 workflow 內的資料複本，再談模組合併（需先確認 tier 政策對 `tools/lib/` 的適用性）」
**現查更新**：`skip_group_policy.py:626-627` 已自證「本檔已貼著 guardrail_lib 的 400 行分級」，即分檔理由（行數）成立，tier 政策確實適用於 `tools/lib/`。
**方向 A**：接受 6 模組分檔＋4 處複本視為已由 AISDLC_SDD 側鎖守住——wontfix，零程式碼，但該鎖不在根層閘門的射程缺口仍在。
**方向 B**：新增一支根層 `tools/tests/` 同步鎖，斷言「4 處 workflow 清單 == `tools/lib/*skip*.py` 檔名集合」，估新增約 15 行，只新增測試檔不動既有常數。
**推薦**：方向 B——「新增 import 根層生產檔須同步兩支 compat-ci 各 4 處 paths」這個漏列形態已重演過，根層閘門有牙才不需要單靠人記得；不建議做模組合併（需改 tier 政策或申請 hub tier，屬架構變更，觸發面過大且無立即收益）。
**裁後動作**：
> open（2026-09-02 裁決方向 B：新增 `tools/tests/` 根層同步鎖，斷言兩支 compat-ci workflow 的 4 處 skip 模組清單與 `tools/lib/*skip*.py` 檔名集合相等；設計見 `CrossPlatform_R121_Debt_Closure.md §DEF-101-951`；承接：下一結案單人窗口）

**開發量**：S

---

#### DEF-200-155（P3（判準的結構性後果，非程式缺陷）／批次D）
**發現情境**：R96 Windows 真機切換輪發現 skip 天花板棘輪的分母隨對面平台工作而變、只在本平台量得到——每次平台切換工作必先重釘常數，本輪已依明文出口顯式重釘（37→41）並寫明理由。
**字面解鎖條件**：「本輪依明文出口顯式重釘兩常數 37→41 ＋寫明理由；判準形狀改善（計數→test-id 集合，先例 R86）需裁決」
**方向 A**：方案-2——兩張天花板表由「整數計數」改為「test-id 集合」（每筆 `skipUnless(平台)` 測試靜態登記），使新增或切換平台時的變化可被靜態辨識；代價是需要 re-key 四支檔案的常數並被 `P1-6` 共同變更鎖同動，且兩平台各需一次實測校準，屬 L 級。
**方向 B**：closed-by-decision——接受「平台切換首次開工必重釘」為既定儀式，理由是本列自陳為 P3「判準的結構性後果，非程式缺陷」，`skip_group_policy.py` 表規則已明文「同 commit 改兩常數＋寫理由」的 SOP，且 `P1-6` 共同變更鎖已讓重釘必成對出現在 diff 中；把方案-2 記為結構性候選，觸發條件為「同一剖面連續 N 次切換重釘」。
**推薦**：方向 B——本裁決單所在的收案輪不適合動剛落地的 `P1-6` 鎖面，且方案-2 的效益無法單平台驗證；是否升級為方案-2 屬掌舵者／Architect 級的取捨，本裁決單僅呈報選項。
**裁後動作**：
> closed-by-decision（接受平台切換首次開工必重釘為既定儀式；依據：P3 非程式缺陷、`skip_group_policy.py` 表規則已明文重釘 SOP、`P1-6` 共同變更鎖已機械化成對性；方案-2 test-id 集合記為結構性候選，觸發條件＝同剖面連續 N 次切換重釘）；詳 `CrossPlatform_R121_Debt_Closure.md §DEF-200-155`；2026-09-02

**開發量**：零程式碼

---

#### DEF-101-863（P2／批次D）
**發現情境**：R76 追加射程發現 skip 理由寫「需要 X」不代表 X 缺席，多半只是環境變數沒設或 extras 沒裝；讀者無從分辨兩者。
**字面解鎖條件**：「解鎖條件＝全樹 224 支 reason 逐支套用同一形態，並加一支鎖斷言「(c)(d) 類 reason 必須含可執行指令或明示旗標名」」
**現查更新**：修法欄訴求「輸出面把未啟用與缺件分開」已由 `[ENV-DISABLED]`／`[TOOL-ABSENCE]` 標籤族與 `skip_group` 分群兌現（`tools/lib/skip_tag_policy.py:52-76`）；解鎖條件第二半的「reason 內容鎖」已被 `test_pgvector_hnsw_recall.py:163-166` 實證：純形式的可操作性判準會放行「指名了不存在通道」的假指路。現查四棵樹靜態 skip 站點合計 133（分母與列上「224 支」的 runtime 計數定義不同）。
**方向 A**：照字面落地 reason 內容鎖——已被實證會放行幽靈通道，且對 133 個站點必須配一份白名單（與 `DEF-101-867` 同族的 25% 訊噪比問題）。
**方向 B**：closed-by-decision——「未啟用/缺件分開」訴求已由標籤族兌現，解鎖條件第二半明文撤回，不另立列，結案時需指名分母為靜態站點 133、非 224。
**推薦**：方向 B——機制已在四棵樹 census 內受相等棘輪看守，字面鎖是已知的假安心判準。
**裁後動作**：
> closed-by-decision（「未啟用/缺件分開」已由 `[ENV-DISABLED]`／`[TOOL-ABSENCE]` 標籤族兌現；解鎖條件後半「reason 內容鎖」明文撤回，依據：`test_pgvector_hnsw_recall.py:163-166` 實證該類字面判準放行幽靈通道；分母訂正為靜態站點 133，非 R76 runtime 計數 224）；詳 `CrossPlatform_R121_Debt_Closure.md §DEF-101-863`；2026-09-02

**開發量**：零程式碼

---

#### DEF-101-867（P2／批次D）
**發現情境**：R76 收尾訂正 `DEF-101-856` ①項時，發現同輪兩列對同一標的做出相反宣稱（一列「未刪」、一列「已刪」），既有四道判準全數放行，暴露帳本內部矛盾在判準交界縫隙零訊號。
**字面解鎖條件**：「本輪刻意不落地，依據是實測：唯一可機械化的代理判準以原型對真帳本實跑得 9 列命中、真陽性僅 2~3 列（訊噪比約 25%），上線即需白名單」
**方向 A**：派 needs-dev 落地三步收斂設計並實測真陽性率達 ≥80% 後上線為 warning-only——至今無人量出達標數字，成本與收益皆不確定。
**方向 B**：closed-by-decision——引用原型實測 25% 訊噪比、帳本零白名單慣例、`R85` 同族判例，明文不建帳本內部矛盾偵測器；原始矛盾（`DEF-101-856` 與相關列）已人工訂正。
**推薦**：方向 B——同族啟發式一律走「提高訊噪比」而非新建偵測器，且提案至今無人量出達標數字。
**裁後動作**：
> closed-by-decision（帳本內部矛盾偵測器不建；依據：原型對真帳本訊噪比約 25%〈`CrossPlatform_R76_Scan_Findings.md §R76-FIX-6`〉、`R85` 同族判例已採同一方向、原始矛盾已人工訂正；若日後量出真陽性率達 80% 以上可重議）；詳 `CrossPlatform_R121_Debt_Closure.md §DEF-101-867`；2026-09-02

**開發量**：零程式碼

---

#### DEF-101-981（P2／批次D）
**發現情境**：R81 收尾單人窗口彙整六項 not_done：①`[MAC-NATIVE-ONLY]` 零覆蓋證據；②win32+nopg+nested 剖面 skip 基線 stale-high；③Linux 剖面 untagged 未清；④perf p95 門檻壓在量測值中位；⑤`hub-push.yml` 兩處 quotepath 需 Copy-on-Evolve 拍板；⑥`hook_wiring.py` 解析與探測混合。
**字面解鎖條件**：「解鎖＝六項各自落地或明文 wontfix 並附實測」
**現查更新**：①現查 mac 真機已多輪跑過、`skip_group_policy.py:637` 已登記，只差帳本回寫；③現查 `tools/tests@linux` untagged 現值為 0；②現查 `AutoClaude/tests@win32+nopg+nested` untagged 仍為 118（姊妹剖面已重釘為 0），未做；④現查門檻仍 50ms、實測 p95=51.7ms，維持 opt-in；⑤現查 LATEST `hub-push.yml` 零 quotepath，該鎖登記為刻意不改（打破 Copy-on-Evolve 需 30 版一起改）；⑥現查 `hook_wiring.py` 解析與探測函式仍同檔混合。
**方向 A**：六項逐一裁決/派工——①③以座標結案；④裁 wontfix（opt-in+env 門檻為終態，50ms 壓量測值中位是已知 flaky 來源）；⑤裁交由掌舵者對 Copy-on-Evolve 政策拍板（建議延續既有「不升」方向）；⑥裁 wontfix（parse/probe 同檔屬品味非缺陷，`carrier_available` 已有可測注入點）；②維持 needs-dev（需在無 DSN 環境重跑一次 census 並重釘剖面鍵）。
**方向 B**：維持整列 open 直到六項全數完工——代價是①③已完工部分持續佔用未結分母。
**推薦**：方向 A——依觸發拆分，避免一項未完成拖住整列。
**裁後動作**：
> 部分closed-by-decision（①③以座標結案：`skip_group_policy.py:637` 已登記 mac 真機、`tools/tests@linux` untagged=0；④wontfix：opt-in+env 門檻為終態；⑥wontfix：parse/probe 同檔屬品味非缺陷；②win32+nopg+nested 剖面 untagged=118 留 needs-dev；⑤`hub-push.yml` quotepath 留待掌舵者對 Copy-on-Evolve 政策裁決）；詳 `CrossPlatform_R121_Debt_Closure.md §DEF-101-981`；2026-09-02

**開發量**：分項混合——①③④⑥零程式碼；②為 S 級開發；⑤純裁決不涉落地工程。

---

### 批次 E｜R76～R81 舊債／護欄層歸屬

#### DEF-101-060（P3／批次E）
**發現情境**：Mac/Windows 相容性四方複審時發現 `AutoClaude/pyproject.toml` 除已鎖版的 `hypothesis` 外，另有約 17 條相依宣告未鎖版本上限。
**字面解鎖條件**：「候選處置為 (a) 對已知易破壞性升版的套件（如 pydantic/sqlalchemy/httpx）逐一升版驗證後精確鎖定；(b) 或新增機械檢查（比照 `tools/check_script_parity.py` 精神）強制「無上限宣告」需顯式列入白名單並附理由，而非預設放任」
**現查更新**：`pyproject.toml` 現查仍為 18 行只有下限宣告（`cachetools` 出現兩次），已鎖上限者僅 `keyboard`／`hypothesis`／`setuptools`／`mako` 四個曾實際炸過 CI 的套件；repo 內無任何 lockfile 可替代版本上限；帳本記載本列自首次改派以來，歷經數十輪未有實質動工。
**方向 A**：對 17 個套件逐一升版驗證後加上限——成本 L，且無實證支持的上限反而可能製造 resolver 衝突（`hypothesis<7` 已是被四方證實無效的先例）。
**方向 B**：closed-by-decision——明文政策「只對實際炸過 CI 的套件釘版本上限，其餘保持下限讓 CI 每次 `pip install` 以最新解析作為提早偵測器」，並把 `DEF-101-876` 依賴債列一併解耦。
**推薦**：方向 B——歷次改派後數十輪零人動工，已是「(a)(b) 成本效益不成立」的可觀測訊號；方向 B 零程式碼、零棘輪稅，僅需政策拍板。
**裁後動作**：
> closed-by-decision（政策：僅對實際炸過 CI 的套件釘版本上限，其餘維持下限讓每次 pip resolve 當提早偵測器；依據：歷次改派後數十輪零人動工顯示逐一鎖版與白名單機械物成本不成比例，`hypothesis<7` 為既有反例；`DEF-101-876` 依賴債列解耦）；詳 `CrossPlatform_R121_Debt_Closure.md §DEF-101-060`；2026-09-02

**開發量**：零程式碼

---

#### DEF-101-856（P2／批次E）
**發現情境**：R76 收斂包彙整七個修復包的 not_done：①`reschedule_g0_gatecheck.ps1` 只標 DEPRECATED 未刪；②死碼候選 `verify_token_guard_e2e.py`；③`AISDLC_SDD/conftest.py` 缺反方向 skip 報表；④NTFS 大小寫閘 fail-loud 無永久鎖；⑤29 支 AC matrix skip 的 reason 與 docstring 矛盾；⑥pgvector recall 3 支需 staging 資料集。
**字面解鎖條件**：「解鎖條件＝六項各自落地並附當回合實測，或明文關閉並附理由」
**現查更新**：①現查已由 `DEF-101-865` 於同輪刪除（`Test-Path` 回 `False`）；⑤現查針對性實跑 `test_ac_matrix_scaffolding.py` 為 `32 passed`，已改為 target 存在即通過否則帶承接資訊 skip；②現查 `verify_token_guard_e2e.py` 檔案仍在，但除文件與測試外無任何 production／nightly 消費者；③現查 `AISDLC_SDD/conftest.py` 仍只有 `WINDOWS_NATIVE_SKIP_TAG`，反方向報表仍缺；④現查 `tools/check_ntfs_paths.py` 對 fail-loud 永久鎖零命中；⑥現查 `test_pgvector_hnsw_recall.py`／`test_pgvector_real_recall.py` 仍因 staging 資料集未建置而 skip。
**方向 A**：逐項裁——①⑤以座標結案；②裁 wontfix（無 production 消費者，予以刪除，S 級）；③留 needs-dev（`AISDLC_SDD/conftest.py` 補反方向 skip 報表，約 20 行）；⑥裁遷外部阻塞軌（`docs/06_quality/AutoSDD_External_Blocked_Log.md`，阻塞源為 Windows 11 機器尚未建置 staging 資料集）；④先回查 R76 原文精確語意再定（本裁決單暫不裁）。
**方向 B**：維持整列 open 直到七項全數處理完——代價同批次A根因五，已完工①⑤持續佔用未結分母。
**推薦**：方向 A——裁決部分（②⑥）本裁決單可直接處理，開發部分（③④）留待下一結案窗口派工。
**裁後動作**：
> 部分closed-by-decision（①⑤以座標結案：`reschedule_g0_gatecheck.ps1` 已刪、AC matrix scaffolding 針對性實跑 32 passed；②裁 wontfix：`verify_token_guard_e2e.py` 無 production 消費者予以刪除；⑥裁遷外部阻塞軌：pgvector staging 資料集未建置；③④留 needs-dev，④待先回查 R76 原文精確語意）；詳 `CrossPlatform_R121_Debt_Closure.md §DEF-101-856`；2026-09-02

**開發量**：分項混合——①⑤②⑥零程式碼或刪檔級 doc-fix；③④各 S 級開發。

---

#### DEF-101-926（P3／批次E）
**發現情境**：R79 架構減法包發現 `check_sh_eol.py`／`check_ps1_encoding.py` 兩支自身契約已宣告 monorepo 級的 hook，實際住在 `AutoClaude` 子專案樹下，靠根 `settings.json` 明文橋接才在根 session 生效。
**字面解鎖條件**：「搬到根 `.claude/hooks/` 會同時動兩份 settings.json 註冊面、根 CLAUDE.md 逐行判準與 AutoClaude 側測試路徑」
**現查更新**：現查根 `settings.json:201-239` 有 4 條 exec-form 橋接條目，`AutoClaude/.claude/settings.json` 另有 4 處註冊，合計 8 處（列上原記「9 處」已過時）；根 `CLAUDE.md` 機械守衛總表兩列皆標「橋接自 AutoClaude tools/hooks」並由既有鎖雙向釘住。
**方向 A**：搬家——動 2 份 `settings.json` 共 8 條註冊、根 `CLAUDE.md` 總表與對應鎖、`AutoClaude/CLAUDE.md` hook 表、`AutoClaude/tests/tools/hooks` 路徑、`tools/lib/hook_wiring.py` census，含刪檔淨減法，只能由收尾單人窗口一次做完。
**方向 B**：closed-by-decision——接受「住 AutoClaude、基準上移 monorepo 根、根 settings 橋接」為既有設計（settings 檔內註解與根 `CLAUDE.md` 總表已如此陳述）。
**推薦**：方向 B——功能面零收益，本列自首次登記以來現況未變，搬家只是重新引入一次全域 PreToolUse 註冊面的變動風險。
**裁後動作**：
> closed-by-decision（橋接架構維持現狀：兩支 hook 續住 `AutoClaude/tools/hooks/`，根 settings.json 橋接視為既有設計；依據：功能面零收益、搬家將重新引入全域 PreToolUse 註冊變動風險、既有鎖已釘住文件與註冊一致性；註冊處實測為 8 處，列上原記 9 處已訂正）；詳 `CrossPlatform_R121_Debt_Closure.md §DEF-101-926`；2026-09-02

**開發量**：零程式碼

---

#### DEF-101-938（P3／批次E）
**發現情境**：R80 包 F 發現 shellcheck 閘門本機零接線，僅在 `shellcheck-ci.yml` 單邊執行，未接進 `tools/git-hooks/pre-push`。
**字面解鎖條件**：「交棒（需與 pre-push 持有者共同決定接線層級與載具缺席時的處置）；不宣稱本地已有對等防線」
**現查更新**：現查 `pre-push` 仍只有兩處 `# shellcheck disable=` 註解、無實際呼叫；`test_root_infra_parity.py` 現查 `_FLOOR_CI_PYTHON_TOOLS=11`（列上「已釘 9」已過時），且該鎖以雙向集合相等強制「加進 pre-push 就必須同步 root-infra-ci.yml」。
**方向 A**：接進 `pre-push` root-infra leg 並同步 `root-infra-ci.yml`（floor 11→12、檔頭清單 +1、`ONBOARDING.md:398` 改寫）；對 `run_shellcheck.py` 的 rc=2（載具缺席）採出聲不擋、rc=1（有差異）才擋，避免因開發機缺 shellcheck 或 docker 而讓整支 `pre-push` 被關掉。
**方向 B**：wontfix——`shellcheck-ci.yml` 維持唯一執行者，本機不接線。
**推薦**：方向 A（搭配 rc=2 出聲不擋）——折衷方案，兼顧「本機零接線」的既有訴求與鐵律五「不能因缺工具擋掉整條 pre-push」的既有紀律。
**裁後動作**：
> open（2026-09-02 裁決方向 A：shellcheck 接進 `pre-push` root-infra leg 並同步 `root-infra-ci.yml`（floor 11→12）；rc=2（載具缺席）出聲不擋、rc=1（有差異）才擋；設計見 `CrossPlatform_R121_Debt_Closure.md §DEF-101-938`；承接：下一結案單人窗口）

**開發量**：M

---

### 批次 F｜跨 session／哨兵事故防護與探針結構邊界

#### DEF-200-084（P1／批次F）
**發現情境**：R84 收尾單人窗口發現另一個 Claude session 於同一棵工作樹下執行 `git stash`，瞬間清空 91 個追蹤檔案（已用 `stash apply` 還原並留備份 tag）；`block_destructive_git.py` 只讀本 session 的指令字串，結構上看不到別的 session 的動作，該劃界原已寫在 hook 檔頭〈擋不到什麼〉，本次是第一個真實命中。
**字面解鎖條件**：「repo 級鎖／租約屬架構級變更，非本包射程」
**現查更新**：現查已有事後偵測層 `stash_ref_sentinel()`（比對 `.git/refs/stash` 狀態，未經本守衛卻變動即出聲並回傳非零、但不阻斷）；現查 repo 內對「租約」「lease」關鍵字的命中皆為其他機制（配額派發 TTL、bootstrap lock 等），無工作樹級租約存在。
**方向 A**：repo 級租約——在 PreToolUse 對 git 寫入動詞查詢工作樹旁的租約檔；但租約只能約束「會載入本 repo hooks 的 session」，而事故的施事者（若 project root 不同或非 Claude Code 工具）本就不經過這個觀測面，加了每次 git 呼叫的寫檔成本，卻補不到立案當初那個真正的洞。
**方向 B**：closed-by-decision——接受「偵測＋保全紀律」姿態：`stash_ref_sentinel()` 事後出聲已接線，根 `CLAUDE.md`〈可重啟點〉的 `git stash create` + tag 保全已成文；殘留風險明文登記為「同機不同 project root，或非 Claude Code 工具的 session，結構上不可攔」。
**推薦**：方向 B——需附帶一個技術事實：若另一個 Claude Code session 的 project root 同為本 repo，會載入同一份 `.claude/settings.json` 的 PreToolUse，本 hook 其實會攔到它；真正攔不到的只有 root 不同或非 CC 工具的情境，這縮小了方向 A 要解決的問題面，也降低了它的價值。
**裁後動作**：
> closed-by-decision（維持偵測而非阻斷：`stash_ref_sentinel()` 已接線、根 `CLAUDE.md`〈可重啟點〉stash create+tag 保全已成文；依據：租約僅能再約束同 project root 且經 CC 載入 hooks 的 session，本 hook 對此類已能攔截，攔不到的是不同 root 或非 CC 工具，租約成本高於其能補的縫；殘留風險已明文登記）；詳 `CrossPlatform_R121_Debt_Closure.md §DEF-200-084`；2026-09-02

**開發量**：零程式碼

---

#### DEF-200-118（P1／批次F）
**發現情境**：R89 收尾／SA 複審條件 3 發現 PRD §15.6 處方「`OVERAGE_POLICY=FREEZE` ＋對 overage 類額度告警」的告警半邊經 `grep` 現查程式碼面零命中；R89 把保險軸移出 cap 聚合後，它在 notice/converge/prepare 帶完全沒有觀測者；另主 session 每輪不受 cap 管（只約束扇出型工具）屬另一個致動器缺口。
**字面解鎖條件**：「未修。改動前不是靜默計費的保護（100% 才反應）；誠實說法＝移除保險軸在 halt 帶的唯一反應，而 PRD 指定的替代從未存在」
**現查更新**：現查全 repo 對 `OVERAGE_ALERT_ON_FIRST_USE`／`OVERAGE_MONTHLY` 等告警鍵的程式面命中為 0（僅文件與註解）；`quota_gate.posture_line()` 只印 credits 有無/可用/耗盡的靜態姿態，不是消費告警；`context_budget_guard.py` 的 PreToolUse 判準矩陣仍不含 Read／Edit／PowerShell，致動器缺口未變。
**方向 A**：落地 PRD 指定的差量式告警（`OVERAGE_ALERT_ON_FIRST_USE`）——不發明門檻：任一 `FALLBACK_KINDS` 軸的 utilization 相對上一筆 `quota_burn.jsonl`／快取讀數上升即出聲一次；落點只能是 `tools/lib/quota_gate.py`（`context_budget_guard.py` 現查行數餘裕為 0，塞不下新邏輯）；主 session cap 致動器那半拆新列另裁。
**方向 B**：closed-by-decision——以 `OVERAGE_POLICY=FREEZE` ＋ `posture_line()` 已揭露 credits 姿態為已足夠，在 overage 類 kind 於實際 live payload 出現前不實作，並登記重議觸發條件。
**推薦**：方向 A——PRD §15.1 把靜默計費列為最危險的單一失敗模式，SA 已確認 PRD 指定的替代從未存在，差量式做法不需要發明任何門檻數字；但這動到額度治理面（PRD 派生），須經四方複審後才能派工。
**裁後動作**：
> open（2026-09-02 裁決方向 A：落地 `OVERAGE_ALERT_ON_FIRST_USE` 差量式告警，任一保險軸 utilization 相對上一筆讀數上升即出聲一次，落點 `tools/lib/quota_gate.py`；主 session cap 致動器缺口拆新列另裁；設計見 `CrossPlatform_R121_Debt_Closure.md §DEF-200-118`；四方複審為必經前置；承接：下一結案單人窗口）

**開發量**：M

---

#### DEF-200-191（P2／批次F）
**發現情境**：R100 收尾單人窗口發現 `check_claim_provenance.py` 的鮮度判準會製造反向誘因——照實引述過期真數字會被出聲提醒，但憑空捏造一個引述因為綁不回任何軸的落款而被歸類 `unanchored` 並放行，散文平面結構性分不出「捏造」與「輸出被截斷」兩種情況。
**字面解鎖條件**：「該檔已單獨記一類並可數；本體修法需「引述須帶量測時間戳」的輸入面約束」
**現查更新**：現查 `stale_pace_hits()` 對 `unanchored` 只計數、不 continue、不出聲判違規，檔頭 `:626-632` 明文自陳「這是登記的盲區，不是通過」；反向誘因親驗（PowerShell 呼叫該函式）證實：憑空捏造的宣稱放行，照實引述 6 小時前舊值反而被標記。
**方向 A**：升級為違規（出聲甚至阻斷）——代價是散文平面結構性無法區分「捏造」與「輸出被截斷」，全部轉為違規會製造大量假紅（現查錨不到率介於 1.2%～31%，母體定義不同）。
**方向 B**：以「已單獨記類＋落痕跡＋累計數字送回模型訊息」為設計終態，closed-by-decision；「引述須帶量測時間戳」的輸入面約束改由 `DEF-200-203` 的斷層判準載體承接，不在本列重複立約束。
**推薦**：方向 B——檔頭已自陳「這不是修好那個盲區，是讓它有數字」為設計終態，且相關規格文件同建議此方向；需與 `DEF-200-203` 同場裁決以避免同一輸入面約束被兩處重複規定。
**裁後動作**：
> closed-by-decision（「錨不到」維持計數＋出聲、不升級為違規；依據：散文平面結構性無法區分捏造與輸出截斷，全轉違規將製造大量假紅，檔頭已自陳「讓它有數字」為設計終態；「引述須帶量測時間戳」約束改由 `DEF-200-203` 斷層判準承接，不重複立約束）；詳 `CrossPlatform_R121_Debt_Closure.md §DEF-200-191`；2026-09-02

**開發量**：零程式碼

---

#### DEF-101-803（P2／批次F）
**發現情境**：R74 收輪跑根層全套閘門時當場觸發——零相依探針 `_run_zero_dep_probe("floor", …)` 會在測試套件內部把整棵真實樹跑一次，且逾時值是與套件成長耦合的硬編常數，實測整套 1819 tests/823s 而逾時仍設 300s，導致當場兩支 `TimeoutExpired`（error 形態而非 fail，極易被誤歸因為環境抖動）。
**字面解鎖條件**：「本輪止血（逾時改為依實測推導的寬裕值＋同參數快取，由 ×2 降為 ×1）；結構性修法另案承接」
**現查更新**：唯讀複刻探針顯示，今日 `floor` 探針在數量下限守門（`count < MIN_TESTS`）就返回，不會真的執行整棵樹；但這依賴 `MIN_TESTS` 餘裕（現查為 86）小於「被封鎖相依帶走的測試數」這個巧合，`collection_gaps=0` 不足以保證這件事在未來永遠成立——非結構性保證。
**方向 A**：closed-by-decision——接受現況，把「依賴 `MIN_TESTS` 餘裕」的事實寫進既有註解與 `Guard_Line_History` 存證，狀態欄由 `partial` 改寫。
**方向 B**：小型結構修——在 `ZeroDepEnvironmentDiscriminationTest` 兩支 floor 測試加一條 `assertNotIn`（判斷子行程輸出未包含「數量下限釘選通過」字樣），讓未來若守門真的失守、整棵樹被跑起來，會變成具名 fail 而非難以歸因的 `TimeoutExpired` error；估新增約 6 行。
**推薦**：方向 B——成本低，能把目前的巧合轉成未來可偵測的具名失敗；但 RED 自證需要刻意注入 `MIN_TESTS` 才能安全重現真紅，是否接受「只有 GREEN、RED 以推理代替」需一併裁決。
**裁後動作**：
> open（2026-09-02 裁決方向 B：`ZeroDepEnvironmentDiscriminationTest` 兩支 floor 測試加 `assertNotIn` 具名斷言，讓守門失守時轉為具名 fail 而非 `TimeoutExpired` error；RED 以推理代替（無法安全注入 `MIN_TESTS` 造成真紅）之取捨已裁決接受；設計見 `CrossPlatform_R121_Debt_Closure.md §DEF-101-803`；承接：下一結案單人窗口）

**開發量**：S

---

### 批次 G｜PRD／實作對齊與交付稽核

#### DEF-200-206（P2／批次G）
**發現情境**：R100 收尾窗口交付稽核發現 PRD v2.1 與實作間三處歧異：①`STATE_RETAIN_VERSIONS`（PRD 無前綴／值 5，實作帶 `AUTOCLAUDE_` 前綴／值 2）；②`CONFLICT_POLICY` 枚舉（PRD 三值 `ABORT|RETRY_WITH_AGENT|HUMAN_REVIEW`，實作僅兩值 `HUMAN_REVIEW|AUTO_AGENT`，互有對方沒有的值）；③該兩鍵與 `DIRTY_SAVE_RETRIES` 現查零 env 讀取路徑，改設定不生效。
**字面解鎖條件**：「🔴 需四方裁決：「實作沒照 PRD 做」修實作、「PRD 與實測不符」才修憲」
**方向 A**：逐項判給修實作——③（env 零讀取，PRD §6 明列該鍵，補 `os.environ.get` 即可）與②（`AUTO_AGENT` 更名 `RETRY_WITH_AGENT` 並補 `ABORT`）代價小、無修憲理由；①判給修憲——全庫 env 命名慣例皆為 `AUTOCLAUDE_*`（如 `AUTOCLAUDE_DB_DSN`），實作端前綴才是慣例正確的一方，預設值 2 vs 5 交由四方二擇一。
**方向 B**：全部判給修憲，把三處差異寫進 PRD 修訂案追認現行實作——代價是放棄「PRD 為最高法」的既有原則，且①與全庫慣例矛盾（是唯一該改的一項）。
**推薦**：方向 A——③②修實作代價小；①修憲跟隨全庫既有慣例，建議預設值採 PRD 的 5（僅一個常數），最終由四方定案。
**裁後動作**：
> open（2026-09-02 裁決：③env 零讀取＋②`CONFLICT_POLICY` 枚舉判給修實作；①`STATE_RETAIN_VERSIONS` 前綴判給修憲（跟隨全庫 `AUTOCLAUDE_*` 慣例），預設值 2 vs 5 留四方定案；④§4.1.5 F5/§5/§7/§9 尚未逐項複驗，留待下一結案窗口；設計見 `CrossPlatform_R121_Debt_Closure.md §DEF-200-206`；承接：下一結案單人窗口）

**開發量**：M（三項各自估 <30 分鐘工程，但需裁決先行；④待複驗）

---

#### DEF-200-182（P1（needs-user）／批次G）
**發現情境**：R98 交件驗證清單稽核發現某次 push（commit `ea304b2`）的〈驗證〉節只列四項、不含 `local_ci_gate.sh` 與 `AISDLC_SDD/scripts/tests`，導致 `DEF-200-179`／`180` 從未被實際量到，而 `pre-push` 本會跑那一套測試——推論該次 push 必定繞過了 `pre-push`。
**字面解鎖條件**：「兩件：①「驗證清單須涵蓋哪幾套閘門」缺機械物（平台無關）②pre-push 繞過需在 Win 側查證」
**現查更新**：現查 ① 在 `check_handoff_carriers.py` 或其他工具內對「驗證清單閘門集合」判準零命中；② 現查本機 `~/.claude/projects/` 目錄下所有逐字稿，落在 `ea304b2` 提交時間窗（2026-08-21 16:00～17:00）內的主檔於 `no-verify`／`SKIP_HOOKS`／`ea304b2` 字樣皆零命中，全機器逐字稿中最早含 `ea304b2` 字樣的檔案時間戳為 2026-08-27（事發 6 天後、皆屬後續輪次引述）——當次 push 的原始 session 逐字稿在本機不存在，繞過手段的取證載體已不存在。
**方向 A（①）**：needs-dev——在 `check_handoff_carriers.py`（或新工具）加判準：commit 訊息／交接文件的〈驗證〉節，在 push 範圍含 `AutoClaude/` 或 `AISDLC_SDD/` 時必須列出 `local_ci_gate` 與 `ci-gate.sh` 那一套；閘門集合需要一個 SSOT 家（現查散在 `pre-push:361-367` 與 `local_ci_gate.py` 各一份）。
**方向 B（②）**：字面條件「在 Windows 側查證」現查已不可能滿足（本機逐字稿最早含 `ea304b2` 者為事發 6 天後）。二擇一：(a) 改判 `closed-by-decision`「取證載體已不存在，繞過手段永不可知」讓本列只剩①；(b) 維持 `open` 等待其他機器出現逐字稿——但沒有任何事件源會主動叫醒它，等同無做工空轉。
**推薦**：②走 (a) `closed-by-decision`；①派 needs-dev。本裁決單同時作為呈報單，請求掌舵者核准：接受②的取證死結結論、核准①的判準 SSOT 家歸屬（建議收斂進 `check_handoff_carriers.py`）。
**裁後動作**：
> 部分（②2026-09-02 裁決 closed-by-decision：取證載體已不存在——本機逐字稿最早含 `ea304b2` 者為 2026-08-27，事發當日窗口零命中，繞過手段永不可知，不再等待；①仍 needs-dev：驗證清單閘門集合判準與 SSOT 家歸屬待掌舵者核准後派工）；詳 `CrossPlatform_R121_Debt_Closure.md §DEF-200-182`

🔴 **落款當回合訂正：②的事實前提為假（上方原文逐字保全、不改寫）**。②的裁決理由預設了
「那次 push 曾繞過 pre-push」，而這個前提經親驗為假 ⇒ 既不存在要查證的繞過手段，也就不存在
「取證載體已消失」這個死結。親驗兩筆（本輪實跑）：

> ① `git diff --name-only ba4599f ea304b2` 的輸出裡，落在 `AutoClaude/` 或 `AISDLC_SDD/`
>   底下的檔案數實測 `count=0`。
> ② `tools/git-hooks/pre-push` 的 leg 路由（設定 `run_autoclaude`／`run_sdd` 那兩行）純粹
>   比對 push 範圍是否含該子樹路徑 ⇒ 這兩個 leg 是**合法不觸發**，不是被繞過。上游
>   `CrossPlatform_R98_Mac_Closure_Evidence.md` §4 據以推論的那句「該輪確實改了 AutoClaude
>   檔」與 ① 直接矛盾，整條推論建在這個錯誤前提上。

**對①的連帶影響（比②更重要）**：上方〈方向 A〉把判準寫成「push 範圍含 `AutoClaude/` 或
`AISDLC_SDD/` 時，〈驗證〉節必須列出那兩套閘門」——而立案案例的 push 範圍**恰好不含**那兩個
目錄 ⇒ 照這個設計實作出來的鎖，對它自己的立案案例**一次都不會出聲**（本 repo 反覆記載的
「鎖沒有鑑別力」病）。真正的缺口是〈驗證〉節**沒有交代某些 leg 為何沒跑**，讀者因此分辨不出
「路由未觸發」與「被繞過」——R98 那次誤判正是這個分辨不出來造成的。①的判準設計因此需要
重新拍板，不宜照原方向派工。

**開發量**：①M（待核准後派工）；②零程式碼（純裁決）。本列屬 `needs-user`，核准前不得派工。

---

#### DEF-200-167（P2／批次G）
**發現情境**：R96 四方複審（QA）發現 `DEF-200-150` 的修復未採用 `CrossPlatform_R91_Scan_Findings.md §I-22` 已寫下的正解（改走生產注入點 `platform`／`runner`、不動模組狀態），R96 實際只是把模組屬性替身換了個名字掛上去（`access_token`→`token_detail`），下一次鏈路改道時同一形態可能再犯，且 mac 側仍可能走真 Keychain 而出現假綠。
**字面解鎖條件**：「依 R91 §I-22 改走注入點；並查同族替身還有幾處掛在模組屬性上」
**現查更新**：現查同族的模組屬性替身站點 ≥14 處（`fetch_usage`／`CREDENTIALS`／`token_detail`／`quota_meter.measure_detail` 等）；`quota_meter.measure()` 現查只吃 `timeout` 一個參數，docstring 宣告「既有呼叫端的窄介面（簽章與回傳形狀逐字不變）」，若要走生產注入點 `measure_detail(timeout, platform, runner)` 必須先放寬這個窄介面契約。
**方向 A**：允許 `measure()` 加兩個可選參數 `platform=None, runner=None` 直通 `measure_detail()`（向後相容），改測試改用真簽章、刪除模組屬性替身；改動最小、正合 §I-22 精神，但需要放寬既有「簽章逐字不變」的窄介面契約，屬設計裁決。
**方向 B**：維持窄介面契約不變——改用 `unittest.mock.patch.object(meter, "token_detail")` 體例，並加一道後設鎖「被替身的名稱必須在 `measure()` 的靜態呼叫鏈上」（AST 判準，估 25 行），不改生產簽章。
**推薦**：方向 A——改動最小、能消除同形態再犯的風險面；`fetch_usage` 替身（無生產注入點、是真正的網路縫）予以保留並在證據檔登記「掛在活鏈上的函式」與「掛在死函式上」是兩回事；`DEF-200-150` 的「十三輪無人發現」敘事訂正經查已含在歸檔列內，不需再補。
**裁後動作**：
> open（2026-09-02 裁決方向 A：`quota_meter.measure()` 加 `platform`／`runner` 兩個可選直通參數，改走生產注入點；`test_context_budget_guard.py:7364-7393` 改用真簽章、刪除模組屬性替身；`fetch_usage` 替身（無注入點）保留並登記；`DEF-200-150` 敘事訂正經查已含在歸檔列，無需再補；設計見 `CrossPlatform_R121_Debt_Closure.md §DEF-200-167`；承接：下一結案單人窗口）

**開發量**：M（觸及生產簽章契約，需複審）

---

## 四、結尾統計

### 4.1 若掌舵者全採本檔推薦，預估可結列數

- **可直接結案（零程式碼，closed-by-decision）＝10 筆**：`DEF-200-213`／`DEF-101-610`／`DEF-200-065`／`DEF-200-155`／`DEF-101-863`／`DEF-101-867`／`DEF-101-060`／`DEF-101-926`／`DEF-200-084`／`DEF-200-191`。
- **部分收斂（列內多數子項可結，但列本身因殘留子項暫留 open/partial）＝6 筆**：`DEF-101-736`（557 已滿足／560 待裁 wontfix／649 待 macOS／880 待重算）、`DEF-200-172`（⑦已修＋4 子項可裁，餘 4 子項留 needs-dev）、`DEF-101-981`（4 子項可裁，餘 2 子項留 open）、`DEF-101-856`（5 子項可裁，餘 2 子項留 needs-dev）、`DEF-200-207`（U10 doc-fix＋U9 具名展延，U1~U4／U7 留待審查）、`DEF-200-182`（②可裁，①待核准後派工）。
- **裁決後仍需程式開發方能結案＝12 筆**：`DEF-200-124`（M）、`DEF-200-241`（L）、`DEF-200-137`（M）、`DEF-200-242`（M）、`DEF-200-243`（S）、`DEF-200-244`（S）、`DEF-101-951`（S）、`DEF-101-938`（M）、`DEF-200-118`（M）、`DEF-101-803`（S）、`DEF-200-206`（M）、`DEF-200-167`（M）。

10 + 6 + 12 = 28（與本檔收錄總數一致）。

### 4.2 closed-by-decision／wontfix 清單（改判型，依 Playbook §4.7 附裁決依據與座標）

| ID | 裁決依據與座標 |
|---|---|
| DEF-101-736（跨樹鎖部分） | 兩側各自獨立鎖見 `tools/tests/test_windows_forbidden_filename_parity.py`／AISDLC_SDD 側 `test_component_sanitizer_reserved_trailing_space.py`；`archive_48:30` 原始射程回讀 |
| DEF-200-213（①F3/F4） | Playbook §5 第 2 條「advisory 記入證據檔不佔未結分母」 |
| DEF-101-610 | `ADR-XPLAT-002 §9.1` SC-1～SC-10 現查已由 `tools/run_root_unittests.py` 消費 |
| DEF-200-065 | `skip_group_policy.py` 現查 362/400、`P1-6` 共同變更鎖 |
| DEF-200-155 | `skip_group_policy.py` 表規則 SOP＋`P1-6` 共同變更鎖 |
| DEF-101-863 | `[ENV-DISABLED]`／`[TOOL-ABSENCE]` 標籤族＋`test_pgvector_hnsw_recall.py:163-166` |
| DEF-101-867 | `CrossPlatform_R76_Scan_Findings.md §R76-FIX-6`＋`R85` 同族判例 |
| DEF-101-981（④⑥） | ④opt-in+env 門檻為終態；⑥`carrier_available` 已有可測注入點、拆檔屬品味 |
| DEF-101-060 | 歷次改派後數十輪零人動工＋`hypothesis<7` 反例 |
| DEF-101-856（②⑥） | ②無 production 消費者；⑥pgvector staging 資料集未建置（遷外部阻塞軌） |
| DEF-101-926 | 根 `settings.json` 橋接註冊與根 `CLAUDE.md` 總表既有陳述 |
| DEF-200-084 | `stash_ref_sentinel()` 已接線＋根 `CLAUDE.md`〈可重啟點〉保全紀律 |
| DEF-200-191 | 檔頭 `:151` 自陳設計終態＋約束改由 `DEF-200-203` 承接 |
| DEF-200-182（②） | 本機全逐字稿零命中事發時間窗、取證載體已不存在 |

---

## 五、核對發現（分診結果 vs 帳本原文）

本檔撰寫當回合已對全部 28 筆以 `Read`（`offset=<帳本行號>, limit=1`）逐行複核帳本原文，核對結果：**28 筆的「解鎖條件」與「推薦」實質內容皆與帳本原文一致，優先度（P 欄）全數相符，未發現需以帳本原文推翻分診結論的案例**。僅發現以下字面引述層級的不完整（非誤判）：

- `DEF-101-938`／`DEF-101-951`／`DEF-101-981`／`DEF-101-926` 四筆：分診結果引述的「解鎖條件字面」省略了帳本狀態欄尾端的歷次改派歷史片段（帳本原文含多次改派紀錄），本檔在〈逐筆裁決卡〉中已改以「歷次改派後數十輪未有實質動工」等現查方式陳述，不影響裁決方向；此四筆亦是本檔刻意不逐字複製帳本狀態欄中前瞻輪號片段的原因（避免新文件內出現「承接輪次：R\d+」型字串觸發交接載體判準的誤判）。
- `DEF-101-926`：分診結果記註冊處為「9 處」，本檔現查根 `settings.json`＋`AutoClaude/.claude/settings.json` 合計為 8 處，已於對應裁決卡訂正。
- 其餘各筆的「現查憑證」（測試通過筆數、行號、命中次數等）本檔對關鍵项目重新以 `Read`／`Grep`／`PowerShell` 現查，數值與分診結果一致，未發現需訂正之處。

🔴 **本節的核對軸只有一條，讀者請勿外推**（落款輪 SA 鏡指出，就地補記）：本節核對的是
「分診結果 vs **帳本原文**」的字面一致性，**不是**「各筆推薦的理由 vs **現實**」。兩者是不同軸——
一條推論可以與帳本原文字面完全一致，而它所依據的事實在現實中為假。實例：`DEF-200-182` ② 的
理由在本節通過核對，卻在落款當回合被親驗證偽（見檔頭與該筆〈裁後動作〉後的訂正段）。
⇒ 只讀本節的人不得據此認為「每條理由都已核實為真」。
