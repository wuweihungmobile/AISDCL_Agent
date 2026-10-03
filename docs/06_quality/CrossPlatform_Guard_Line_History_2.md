# 護欄層行數棘輪 — 逐輪判準敘事史料歸檔（第二冊）

- **建立日期**：2026-09-30
- **建立者**：R186 收尾單人窗口 Trim 棒（款(11) 淨減法抵銷：本輪護欄層新增行數，以本冊搬遷的純史料抵銷）

## 這份文件是什麼、為什麼要有第二冊

`CrossPlatform_Guard_Line_History.md`（下稱第一冊）自 R98 起承載 `tools/tests/*.py` 的逐輪敘事史料，
搬遷當下已逼近 Read 工具單次讀取上限 262,144 bytes（餘裕僅 12,286 bytes，裝不下本輪要搬的量），
依 DEF-101-587 的拆分慣例另開姊妹檔。本冊體例與第一冊相同：`tools/tests/*.py` 內「純史料」的
註解／docstring 段**原文逐字**搬到這裡（僅去掉註解前綴與縮排，置於 fenced 區塊保全原貌），
原位只留判準邏輯與一行指標；知識零刪除，只是換地方住——被棘輪管轄的測試檔不該承載逐輪敘事。

🔴 每一節的 `§N` 編號即原始碼指標 `〈R186 淨減法搬遷〉§N` 所指的位置；索引依編號排列。 R194 的搬遷節（§82 起連號，指標 `〈R194 淨減法搬遷〉§N`）接在檔尾。

**索引**：

1. §1 `_platform_helpers.py` 收斂沿革：strip_ps_comments 家族（R57）與 usable_bash_for_fixture（R69）
2. §2 PowerShell 引擎述詞 SSOT：模組 docstring 沿革（語意①~⑤、DEF-101-509 方向衝突、R69／R73 訂正）
3. §3 act 本機 runner 映像鎖：三處 tag 必須綁在一起的實測破口（R77）
4. §4 `TestRunActShellFlagParity` 立案：兩道專職對等檢查器同時放行的落差（R77）
5. §5 `TestStableSnapshotRejectsTornConcurrentWrites` WHY：沙箱拷貝撕裂內容（DEF-200-380）
6. §6 bash 3.2 相容鎖第二掃描面：workflow inline `run:` 的缺陷本體與落地實測（R81 包 G）
7. §7 wrapper thinness 鎖：為何併進本檔而非另立新檔（R74 棘輪語意沿革）
8. §8 wrapper thinness 鎖：判準由 `glob("check_*.py")` 改為 CLI 入口的射程修復（R74）
9. §9 共用淨化層架構鎖：方法論推導與為何用 subprocess（R45）
10. §10 共用淨化層架構鎖：R66 追加 `sdd_latest` 回歸鎖的落點沿革（DEF-101-627）
11. §11 context 守衛測試模組的排程器 pin：立案與還原時機（R84／C3-P4c、SA84-01、DEF-200-350）
12. §12 context 守衛 console-free 掃描面：具名納入站點的逐項理由（R84／C3-A、console_qa 事故、DEF-200-418）
13. §13 DEF-ID 引用完整性鎖：WHY（R60 的 21 處誤引事故）
14. §14 dev_start ps1 lastexitcode 鎖：PATH 指向空目錄而非 /usr/bin:/bin 的原因（R67 round 3）
15. §15 dev_start ps1 lastexitcode 鎖：OutputEncoding 設 UTF-8 的修復沿革（R42，DEF-101-350）
16. §16 dev_start ps1／sh 被 source 鎖：class 級 skip 述詞由 os.name 改為「兩支殼都解不到」（R79／R82）
17. §17 ADR 量測 token 鎖：R71 錨點改指的經過
18. §18 鐵律三覆蓋率清單：R80 三項移出本清單與低報分子的訂正
19. §19 基線豁免 shrink-only 天花板：R79 立案理由與逐格收緊沿革（33→25）
20. §20 第三態來源自證：補洞前的缺陷與本機實測（R82／P4）
21. §21 交棒宣稱區塊切分：R82 Q4-01 上一版只看條目的缺陷
22. §22 交棒宣稱鎖：登記表需要的理由（R82 Q4-01 誠實劃界）
23. §23 extras 引號鎖：掃描面逐輪擴面的沿革與實測（R57 round 1／R59）
24. §24 extras 引號鎖：豁免預算必須分兩本帳的問題立案（R59 ARCH-R59-02）
25. §25 find_git_bash 結構等價鎖：Scan-A 兩處語意分歧與 R60 P10-2 相反裁決的逐項說明
26. §26 整合閘門本機活體載具：為何住在 find_git_bash 鎖檔（R67-C18／R78 棘輪語意訂正）
27. §27 整合閘門本機活體載具：WHY（R67 全庫普查：零呼叫端＝實質已死）
28. §28 workflow 結構鎖：B 節不用 pyyaml、C 節用 pyyaml 的取捨（R57／R68）
29. §29 線上排程期望值 SSOT 鎖：為何併進 install_windows_nightly 鎖檔（R74／R78）
30. §30 macOS smoke「SKIP 誠實外顯」鎖：缺陷現象與實測（R60 Scan-F F-01）
31. §31 成熟度判準 M1／M5／M6 機械物：被守的四筆實測缺陷（R79）
32. §32 成熟度判準機械物：為何新增一支檔而不是併進既有鎖檔（R79）
33. §33 否定存在宣稱鎖：立案事故（R82／Q4-02，交棒書斷言閂鎖尚未落地而同 commit 已落地）
34. §34 否定存在宣稱鎖：為何新增一支檔而不是併進 doc_loc 鎖檔（R82）
35. §35 nightly 直譯器決定性鎖：模組 docstring 沿革（DEF-101-506／DEF-200-302／DEF-200-314／DEF-200-315）
36. §36 noqa 指令形態鎖：R69 終審 P1（本節第一版自己犯了它要治的病，兩層）
37. §37 作用域級存量債表：上方註解壓縮前原文（逐筆沿革另見第一冊〈作用域級存量債表沿革〉）
38. §38 目錄項原語存量表：凍結版不入掃描面的量測與 DEF-200-202 修復窗口說明
39. §39 M5 注入矩陣：R85／ARCH-02 手抄清單與 AST 對帳不符的實測
40. §40 `_repo_py_files()` 沿革：納入 untracked 的理由與 `_zzz_` 前綴排除（R70／DEF-200-274）
41. §41 `_scan_repo_py_for()` 沿革：掃描面名實不符（R57 A5）、git ls-files 取捨與 R57 實測、讀不到檔案的紅燈
42. §42 行內 stdio 複本棘輪：R75 訂正（兩個各自宣稱 SSOT 的家）
43. §43 行內 stdio 複本棘輪：診斷階段轉述數字不複現的逐項實測（R74）
44. §44 pre-commit dispatcher 鎖：行尾閘為何併進本檔（R74／R78 棘輪語意訂正）
45. §45 pre-push dispatcher 鎖：指名鎖檔必須存在的 WHY（R67 round 2，QA-R67-03）
46. §46 PS 5.1 相容鎖：既有防護都驗不到 5.1 的三項逐條說明（R56／R57 訂正）
47. §47 `python -c` 百分號 shim 鎖：真實事故經過（DEF-101-503）
48. §48 量不到原因表：第二個成員 `http-429-floor` 為何不登記進 `_UNMEASURABLE_REASONS`（R100）
49. §49 `run_with_floor` 平台閘測試：patch 目標由行程全域 `os.name` 改為 windows_skip_tags 的判定（R72／R82 SA B-1／R100）
50. §50 零相依探針子行程環境：強制序列的緣由（DEF-200-274 第九輪 P0，遞迴熱點 823s→3813s）
51. §51 外部可執行檔前置宣告 SSOT：WHY 與 SSOT 放測試檔的取捨（R69 終審 SD）
52. §52 parallel 例外安全測試：mock Popen 漏 `returncode` 的既存 fixture 缺口（第四輪複審）
53. §53 `save_live_cache()` merge-prune 回歸鎖：震盪機制鏈與父鍵回填補強（DEF-200-363 第十五輪）
54. §54 過期 advisory 比對合併活體快取回歸鎖：場景與假時鐘取捨（DEF-200-386）
55. §55 `merge_results()` skip census parity 鎖：為何手造 per-worker payload（DEF-200-274 第十輪 SA-01）
56. §56 排程能力對照契約：背景（DEF-101-233 五輪未落地的治理縫隙）
57. §57 排程能力對照契約：R60 DEF-101-539（pytest 風格被 discover 整檔零收集）
58. §58 排程能力對照契約：`_SCAN_FLOOR` 取消第二個家的沿革（R85／訴求 2）
59. §59 排程能力對照契約：R83 本地基底鏈判準（共用夾具子類別假紅）
60. §60 腳本掃描面 SSOT 鎖：R79 ARCH 取代 866 行對抗式正則錨的舊形狀與新形狀
61. §61 腳本掃描面 SSOT 鎖：R79 四方複審補進 `--with-latest` 的實測
62. §62 skip 天花板共同變更鎖：立案（漏補第四層 M6 落款）與粒度由檔案級改剖面鍵值級（R115／R119）
63. §63 示範指令單平台鎖：指引措辭加詞（`請設定`／`使用`）的逐筆實測（R83／W2-B）
64. §64 subprocess 編碼鎖：`tools` 樹檔數下限逐輪重釘沿革（77→92→110→131→156→186）
65. §65 Windows 禁用檔名交叉一致性鎖：R57 訂正（檔頭「三處」與檔身「四處」矛盾）
66. §66 Windows 禁用檔名鎖：repo-wide 前瞻枚舉鎖的 WHY 與三段式邊界宣稱（R59／R82 訂正）
67. §67 Windows 禁用檔名鎖：R69 兩筆「AISDLC_SDD 側跨樹 import autoclaude」的收容背景
68. §68 Windows nightly 錨點鎖：補在本檔而非 smoke 步驟的取捨與註解剝除沿革（R57）
69. §69 WindowsApps bash guard：`_CALLER_FILES` R56 補登記三支呼叫端與 LATEST 動態解析訂正
70. §70 WindowsApps bash guard：`_EXEMPT_SH_FILES` 豁免理由須自足的告示沿革（R43 二審／R56）
71. §71 WindowsApps bash guard：`run_mutmut_in_docker.sh` 豁免的論證沿革（R44 新增／R56 訂正）
72. §72 WindowsApps bash guard：`_tracked_non_sh_shell_scripts()` 的存在理由（R67 B4 實測）
73. §73 WindowsApps bash guard：R80 S5-07 刪除四支路徑段判準測試的逐案對照表
74. §74 WindowsApps guard 收斂鎖：背景（三份內嵌複本、復發四次、R37 抽出共用函式）
75. §75 WindowsApps guard：④ repo-wide 前瞻防增生鎖的背景（R40）
76. §76 WindowsApps guard：`_EXEMPT_PS1_FILES` 清空的經過（R44 兩輪對抗式複審）
77. §77 WindowsApps guard：ps1 裸 python 呼叫點判準由檔案層級改呼叫點層級的證偽實測（R44 SA 一審）
78. §78 WindowsApps guard：Python 側「零 guard 裸 python 名稱」repo-wide 前瞻掃描的 WHY 與三段式邊界（R60，B-01）
79. §79 workflow 許可／併發鎖聚落：R68 擴充四類別的事故說明與 R69 訂正（DEF-101-703）
80. §80 workflow concurrency repo-wide 枚舉：缺陷本體（R77-55，修站點不修判準）
81. §81 schedule cron 同步鎖：R15 SCAN-C-9 整行註解剝除取捨
82. §82 extras 引號鎖：`_UNQUOTED_EXTRAS_RE` 逐分支 (a)~(e) 的訂正沿革（R57 round 1 SD 複審、R59 新增三件）
83. §83 extras 引號鎖：已加引號形態下限（`_MIN_QUOTED_DOT`／`_MIN_QUOTED_NAMED`）的實測分解（R57／R59、二審 QA-R59-P3-2 訂正）
84. §84 extras 引號鎖：`_MAX_EXEMPTIONS` 由寫死的 10 改為衍生值（R59 二審 ARCH-R59-02-C1 訂正）
85. §85 extras 引號鎖：`_scan_targets()` 由 tracked-only 改為聯集掃描面的立案沿革（R69 真 fail-open、R70／DEF-101-752）
86. §86 extras 引號鎖：豁免總數上限的 R59 實測與單一總上限缺陷的訂正沿革（R57 的 5 調到 10、R59 二審再訂正）
87. §87 交棒宣稱鎖：R82 Q4-01 的另一半——命中數加總使最新一份掉到 0 打不出來（R78 SD-03 同病在同檔復發）
88. §88 退場判準／改派判準：R76-08 缺陷本體——綁字面 token 的判準讓「照規矩訂正文件」反而轉紅
89. §89 活文件掃描面納入 `AutoSDD_improving_*.md`：R81 QA B-3 的注入實測與存量成本
90. §90 路徑宣稱判準：`path_claim_bases()` 兩個多出基準的實測筆數（7 筆／6 筆）與 R73 判例
91. §91 雲端 nightly 紅燈判準（表③）：R76-03 立案——run 層 conclusion 通道零讀者，continue-on-error 讓紅 job 下 run 仍 success
92. §92 表① 受鎖欄欄頭鎖：WHY——平台中立的 MIN_TESTS 釘選掛在標示「Windows 11 實測」的欄頭底下（SA-R67-07、DEF-101-562 欄頭版）
93. §93 表① macOS 欄鎖：WHY——macOS 欄是純散文、寫死的 `616（skipped=4；R57 量測）` 落後實況約九輪而無機械物看見（R60 ARCH-R60-03）
94. §94 nightly_summary 有界讀取鎖：上一版是零鑑別力的死鎖（把 `f.seek` 整行刪掉仍 6/6 全綠；與 DEF-101-763 同構）
95. §95 幽靈路徑基線：R81 SA-B3 登記的 `CrossPlatform_R81_Review.md` 於本輪建立後被自清機制要求刪除（豁免不會永久化的活體證據）
96. §96 subprocess 編碼鎖：per-tree 檔數下限「腐化偵測帶」的缺陷本體（R75 QA 實測 files=81 對 floor=18、DEF-101-800）
97. §97 dev_start ps1／sh 被 source 鎖：兩部分的立案沿革（DEF-101-304／R35 發現、R67-C17 併入既有鎖檔、CI 帳務停擺）
98. §98 `_platform_helpers.py` `_PS_COMMENT_LEAD`：R57 round 3／4 補右括號類與引號類收尾字元、「為什麼安全」理由訂正與全語料實掃
99. §99 wrapper thinness 鎖：R10 守門改制（黑名單軍備競賽三輪被繞過）與 R60 Scan-E E-A-02 關鍵字偵測由串聯改並聯
100. §100 PowerShell 引擎 SSOT 鎖：機器屬性寫成常數的立案（R69 原案、R73 擴射程 DEF-101-777、DEF-101-757 同型復發）
101. §101 PowerShell 引擎 SSOT 鎖：`_STALE_CLAIM_RE` 主語與否定詞視窗 8→16 字的經過（R74 DEF-101-777）與 R73 教訓
102. §102 排程能力對照契約：R75 訂正（SD 追加②）——寫死的下限 40 腐化、改與 skip_tag_policy 共用逐樹下限政策
103. §103 WindowsApps guard 交叉一致性鎖：站點偵測三輪訂正逐步收斂鑑別力（函式名錨→雙錨→re.I、scoped_prefixes 縮面漏 16 支）
104. §104 WindowsApps guard 交叉一致性鎖：R44 SA 一審追加揪出——初版判準是檔案層級（1 處 guard、15+ 處裸呼叫仍全綠）
105. §105 dev_start 版本探測碼逐字相同鎖：R71（DEF-101-760）——上面那支鎖只看版本數字，單邊改掉探測碼時本檔與 CI 全綠
106. §106 dev_start Mutex 鎖：R59 QA-R59-05——原為全檔 assertIn，Mutex 名在 .ps1 內出現兩次而被訊息字面滿足（DEF-101-504 保護歸零）
107. §107 dev_start 新四態 str 態：斷言不得寫死 POSIX 字面值 `/elsewhere`（R69 windows-compat-ci 實紅；改比對 `str(Path(...))`）
108. §108 WindowsApps bash guard：`_tracked_*` 掃描面擴為 tracked ∪ untracked 的 R82（DEF-101-752）立案與姊妹函式刻意不比照的理由
109. §109 WindowsApps bash guard 行為測試：fixture 路徑由 bash 自身 `mktemp -d` 建立的緣由（R43 實測：磁碟機代號冒號腰斬 `$PATH`）
110. §110 WindowsApps bash guard：`_CALLER_FILES` R55 新增一支——原登記於 `_EXEMPT_SH_FILES` 的豁免理由論證方向錯誤
111. §111 歸檔判準③：R68 改寫（DEF-101-676）——取代舊的 `assertNotIn(v["id"], claimed)`，改寫動機與代價量化
112. §112 歸檔樣本座標鎖：為何需要（那句話原本不寫樣本住哪一支檔，被以主檔為掃描面的複查讀成 stale）
113. §113 root-infra 對等鎖：R56 立案——檔頭第 1 道敘述是被指定的真相源卻在掃描面擴張時漏改（R54 DEF-101-431／R55「9 支」同形狀）
114. §114 帳本交叉參照鎖：R75 把指針樣式由「只認 R60 那一組檔名」放寬為任一輪的 `CrossPlatform_R<n>_*.md`（R60／R68／R75 兩層化）
115. §115 smoke ↔ CI 同步：`--workflow` 接上後第一次真跑踩到的假綠（act 對事件對不上的 workflow 不跑任何 job 卻回 rc=0；全庫 5/11 支 on: 不含 push）
116. §116 Windows 禁用檔名鎖：構造形判準的 WHY——R60 插入新裝置名使間隙由 ≤5 變 17，三處實作同時掉出錨①而註冊表等值斷言毫無反應
117. §117 Windows 禁用檔名鎖：logger.py 以 rsplit 剝副檔名而漏判多重副檔名保留名（R33 QA 二審、DEF-101-295 追加修復）
118. §118 platform_utils 收斂止血鎖：模組 docstring 的立案沿革（R16 架構最佳化、R66 DEF-101-629、R70 DEF-101-751／752）
119. §119 掃描面盲區封閉鎖：R85／QA-06 探針由 repo 根改造在拋棄式 git repo 內的緣由（pid 只讓自己的目錄唯一，擋不住別的行程掃到探針）
120. §120 掃描面盲區封閉鎖：事故本身——`platform_caps.py` 在 R69 全程 untracked 而躲過四輪四方複審與多次全套實跑（R70／DEF-101-752）
121. §121 bootstrap_core pick_python() WindowsApps 空殼排除 guard 回歸鎖：WHY 全文（DEF-101-273/279 兩輪修復、R16 架構收斂後缺 guard、R31 補齊）
122. §122 subprocess 編碼鎖：WHY 這道到 R74 才出現——判準一（parent 解碼）合規的那一行 hook 在 windows-latest（cp1252）把中文指引印成亂碼（DEF-101-789）
123. §123 hook 註冊普查：R79 由並行包新增的 PreToolUse 條目（`.claude/settings.json` 不在本包所有權內）的交接註記
124. §124 Windows nightly 安裝器：R73（DEF-101-779）原本斷言 help 區塊含某個時刻字面值而把觸發時間釘進鎖裡（ADR-SD09-012 五項排程設定連兩輪沒人敢套）
125. §125 dev_start：DEF-101-762 在 LATEST 版 SDD 樹上的兩個同形態站點（以 `git rev-parse` 輸出反推路徑，cp950 下損毀）與 R71 參數化到第二支
126. §126 check_script_parity 具名輪次正控樣本：E-05／R77-13 訂正——原本寫死一個不存在的輪號（與「未指派」等效的假承諾），改自帳本現查當前輪推導下一輪
127. §127 check_script_parity：R80 S5-05——原本逐一寫 `patches[0]…patches[5]` 六個索引（`_patched()` 少回一個元素時是 IndexError 而非有意義的紅燈），改用 ExitStack 依實際長度展開
128. §128 PS 5.1 相容鎖：R56 round 5 修正（QA B-3）——`keys_and_floors_pinned` 名實不符，只比 keys、`_floor` 從未進入斷言
129. §129 claim provenance 第三判準：規格版紅綠自證（插入 4 小時前的『量測於』⇒ 回空清單）把事故寫成契約，「在場即抑制」型抑制器在整個母體上一次都沒做對過
130. §130 sanitize 凍結版鎖：R44 QA 一審發現的時序缺陷——初版用 `git show HEAD:<path>`，本輪修復一旦 commit 就對全部 7 個 subTest 恆紅，改錨定固定 SHA
131. §131 sanitize 凍結版鎖：bug-injection「修復前」重放基準點固定錨定在 DEF-101-357 修復前的父提交（R43 收尾 commit），不用 `git show HEAD:<path>`
132. §132 dev_start mac nightly 鎖：R59 ARCH-R59-04——原寫 `.split("/")[-1]` 只鎖檔名不鎖目錄，鎖目錄搬走而檔名不變時本鎖照綠、DEF-101-504 復發且零訊號
133. §133 DEF-200-481：lint 規則①換成真機三條件判準——devB 從 `.claude/hooks/lint_powershell_command.py` 等檔刪除／改寫的原文（逐字，行號＝HEAD 版）
134. §134 DEF-200-477：SessionStart 簡報當第三判準錨點——devC 從 `.claude/hooks/check_claim_provenance.py` 改寫／刪除的散文（逐字，行號＝HEAD 7efc4c0）
135. §135 DEF-200-479／481／482：`quota_gate.py`／`audit_session.py`——devD 被改寫／刪除的散文與被取代的程式碼（逐字）
136. §136 本輪新增測試的 docstring 壓縮前原文（逐字；Trim 棒壓成 ≤3 行，保留 DEF 編號與 WHY）

---

## R186 淨減法搬遷

> 搬遷自 `tools/tests/*.py`（2026-09-30 R186 收尾單人窗口，款(11) 淨額抵銷；原文全文保全、知識零刪除；僅去掉註解前綴與縮排）。原位各留一行指標，或壓成只剩現行行為說明的短註解。

### §1 `_platform_helpers.py` 收斂沿革：strip_ps_comments 家族（R57）與 usable_bash_for_fixture（R69）

原址：`tools/tests/_platform_helpers.py` 模組 docstring 後半（兩次複本收斂的立案敘事）。

```text
R57 SA-R57R2-03 收斂：`cut_ps_inline_comment`／`strip_ps_comments`（PowerShell
註解剝除，供「錨點只認功能碼、不認註解」的靜態鎖使用）原本在
`test_find_git_bash_parity.py` 與 `test_windows_nightly_anchor_parity.py` 各存一份
AST 逐字相同的複本，且無一致性鎖——同輪卻把 `_ci_scan_anchors.py` 的三份複本以
「三份複製只是把同一個盲點抄了三遍」為由收斂，兩套標準。事後被 A-R57R2-02／
R57R2-QA-01 證實：兩份複本確實同時帶著同一個 here-string 起始誤判的 fail-open。
故一併收斂進本檔，呼叫端一致性由
`test_find_git_bash_parity.py::TestPsCommentStripperSsotCallsiteLock` 機械守護。

R69 後續（DEF-101-753）同判例第二次套用：`usable_bash_for_fixture()`（取得一支真的
能跑 .sh 的 bash）原本在 `test_bash_probe_spec_contract.py` 與
`test_macos_smoke_skip_honesty.py` 各存一份 fixture 用途複本、且**排除規則不一致**，
而 `test_smoke_ci_sync.py` 乾脆兩份都沒用、直接把字面值 `"bash"` 交給 subprocess ⇒
Windows CI 上跑到 WSL 佔位 bash 翻紅。三處收斂為本檔一份，呼叫端一致性由
`test_bash_probe_spec_contract.py::TestNoBareBashInvocationInToolsTests` 機械守護。
```

### §2 PowerShell 引擎述詞 SSOT：模組 docstring 沿革（語意①~⑤、DEF-101-509 方向衝突、R69／R73 訂正）

原址：`tools/tests/_ps_engine.py` 模組 docstring（WHY 全文、另立模組理由、守門清單）。

```text
WHY：`tools/tests/` 內對「本機有哪個 PowerShell 引擎、要拿哪一個去跑」這件事，
R60 實查有 **6 個檔案／10 處行內寫法／5 種語意**，無具名 SSOT、也沒有任何鎖防止
第 N+1 份選錯（而「選錯」在本 repo 已有兩次實證：DEF-101-285、DEF-101-509）：

  語意①「生產引擎，5.1 優先」`which("powershell") or which("pwsh")`——6 處。
  語意②「有沒有任一引擎」（skip 述詞）`which(...) is None and which(...) is None`——5 處。
  語意③「在 Windows 且有任一引擎」（`.cmd`／PATHEXT 語意測試專用）——2 處。
  語意④「只認原生 5.1，不得 fallback」`which("powershell")` 單獨用——2 處。
  語意⑤「**pwsh 7 優先**」`which("pwsh") or which("powershell")`——1 處（3 個消費點）。

⑤ 與 R59 **DEF-101-509 拍板的判準方向相反**。該判準原文（`test_install_windows_nightly.py`
的 WHY 區塊）：「生產是以 `powershell -ExecutionPolicy Bypass -File` 執行＝5.1，而 `pwsh`
解析用的是 PS 7 文法…本檔所在的 `tools/` 樹受 `test_ps51_compat.py` 的『PS 5.1 相容』
政策約束，故以 5.1 優先解析與該政策一致」。⑤ 會靜默 fallback 到另一個引擎、測不出差別；GitHub-hosted
runner、任何 `winget install Microsoft.PowerShell` 過的開發機、以及 `brew install
powershell` 過的 macOS 開發機都同時有兩者（🔴 **R69 訂正、R74 改寫**：本段原先把撰寫
當下那台機器的引擎清單寫成了本檔的常數，R69 在 macOS 真機上實測推翻。引擎可用性是
**機器屬性**，一律現查 `available_engines()`；R74 另把原訂正註記裡逐字保留的那句舊話
一併刪除——留著它等於在樹裡多存一句假話，而擴射程後的鎖正好抓到它），
於是會用 **PS 7** 去驗一支受 5.1 政策約束的檔案——與 DEF-101-509 修掉的是同一類判準
錯誤、只是方向相反。本檔因此把「生產引擎＝5.1 優先」寫成唯一的
具名述詞（`production_engine()`），讓「選誰」這件事只有一處可改、且有鎖看著。

**為何另立一支模組、不塞進 `_platform_helpers.py`**：該檔 docstring 自己已明列收納
契約僅兩類（跨平台測試 fixture、供靜態鎖消費的原始碼解析 SSOT），並記載 R57 因塞進
第三類而出現「雜物抽屜的早期訊號」的教訓。引擎述詞既非 fixture 也非原始碼解析器，
故比照同目錄 `_ci_scan_anchors.py` 的先例，單一關注點獨立成檔。

守門：`tools/tests/test_ps_engine_ssot.py`
  - 優先序（含「兩引擎都在」的合成情境——合成是為了讓判準在**任何**機器上都測得到
    方向，不依賴該機器剛好裝了哪些引擎；R69 訂正：原註記把引擎可用性寫成了本機常數。
    🔴 R73 補記（DEF-101-777）：該註記的訂正只涵蓋本檔，射程外的同型句子四輪後同時
    變成假事實——鎖已擴至整個 `tools/` 樹，見 `test_ps_engine_ssot.py`
    `TestNoStaleLocalEngineClaims`）
  - `native_ps51()` 不得 fallback
  - repo-wide 反增生掃描：`tools/tests/*.py` 不得再出現行內引擎挑選（附具名豁免＋stale
    自檢）。**判定走 `ast`**（R60 round-2 訂正）：只認真正的 `shutil.which("powershell"
    |"pwsh")` 呼叫節點，docstring／註解／字串常數內拿舊實作當史料引述**不算命中**。
    先前的逐行文字判定會被史料引述誤命中，使檔案級豁免永遠退不了場、被豁免的檔案
    零覆蓋（ARCH-R60-06／SA-R60-03／SD-R60-03／QA-R60-07 四方獨立命中）。
  - 正向委派鎖：已遷移消費檔的引擎述詞函式本體必須呼叫 `production_engine()`、
    不得回退成行內 `shutil.which`（import 級鎖看不到「留 import、改本體」這條路）
```

### §3 act 本機 runner 映像鎖：三處 tag 必須綁在一起的實測破口（R77）

原址：`tools/tests/test_act_local_runner_image.py` 模組 docstring（WHY 全文）。

```text
WHY 這三處必須被綁在一起（R77 實測到的破口與它的修法）：
  `act -n`（dry-run）對 root-infra-ci.yml 回 rc=0，但**真跑**到第 3 個 step
  （`pwsh 語法解析 + UTF-8 BOM 守門`）就 `exitcode 127` —— `.actrc` 釘的
  `catthehacker/ubuntu:act-latest` 沒有 pwsh，而 GitHub 的 ubuntu-latest runner 自帶。
  修法是自建一顆薄映像（base ＋ pwsh ＋ gh）並把 `.actrc` 指過去。於是「映像 tag」這個
  字面值同時住在三個地方：`.actrc` 的 `-P` 行、`run_act_core.RUNNER_IMAGE`（`--build-image`
  build 出來的 tag、`ensure_images()` 檢查存在性的對象）、以及 Dockerfile 檔頭的說明。
  三處只要有一處漂掉，失敗方向都是**靜默的**：

    · `.actrc` 指到一個不存在的 tag ⇒ act 帶 `--pull=false` 會去 pull 一個 registry 上
      不存在的映像然後失敗 —— 這一種還算大聲。
    · `.actrc` 指回 base、而 `run_act_core` 仍 build/檢查自建 tag ⇒ `ensure_images()`
      一路綠燈（那顆自建映像確實在），act 卻起 base 容器，pwsh 那步**又**回 127。
      畫面上是「準備階段全綠、跑到一半才炸」，而準備階段的綠與這次失敗毫無關係。
      這正是本 repo 反覆在治的「鎖存在但沒有鑑別力」。
```

### §4 `TestRunActShellFlagParity` 立案：兩道專職對等檢查器同時放行的落差（R77）

原址：`tools/tests/test_act_local_runner_image.py` `TestRunActShellFlagParity` class docstring 第二段。

```text
🔴 這條鎖存在的理由是一個真實的、被兩道專職對等檢查器同時放行的落差：R77 給
`run_act.sh` 接上了 `--workflow`／`--event`，`run_act.ps1` 卻沒有——Windows 是本 repo
的主要開發平台，而它的薄殼因此指不到 11 支 workflow 裡的 10 支。當時
`check_script_parity.py` 與 `check_wrapper_thinness.py` **雙雙 rc=0**：
  · `check_wrapper_thinness` 是**逐檔** hash 釘選 —— 它問「這份檔案有沒有變」，
    兩側各自更新各自的 pin 就都是綠的，它從不把兩側拿來互相比較；
  · `check_script_parity` 對 hash 釘選類的對子只做「有沒有納管」與鍵集合交叉鎖，
    _MARKER_PAIRS（唯一會比對兩側內容的機制）對這一對是空的。
⇒ 專門守對等的鎖看不見對等落差。只補旗標而不補判準，同型缺陷會再來一次。
```

### §5 `TestStableSnapshotRejectsTornConcurrentWrites` WHY：沙箱拷貝撕裂內容（DEF-200-380）

原址：`tools/tests/test_archive_defect_log.py` `TestStableSnapshotRejectsTornConcurrentWrites` class docstring。

```text
WHY：`_ledger_sandbox()` 原本用 `shutil.copy2` 直接拷貝帳本家族——若拷貝當下有人
（或記帳 agent）正在編輯帳本，`copy2` 可能拷到『半新半舊』的撕裂內容，而撕裂內容
仍可能通過表頭判準，讓依賴沙箱的測試偶發假紅（誤判撕裂內容裡缺了什麼）或假綠
（撕裂剛好拼出看似合法的狀態）——兩者都與被測程式碼的真實行為無關，是**測試載具
自己的瑕疵**冒充成受測程式的訊號。修法要求『讀前讀後 stat 相同才算穩定』，本測試
坐實兩件事：(a) 永遠等不到穩定窗口的來源必須 fail loud，不能安靜吞下最後一次讀到
的撕裂內容去污染下游斷言；(b) 穩定的來源必須原樣正常回傳，不能因為修法而誤傷了
原本就會過的情況（控制組——沒有它，上面那條可以被『凡是重試就報錯』滿足）。
```

### §6 bash 3.2 相容鎖第二掃描面：workflow inline `run:` 的缺陷本體與落地實測（R81 包 G）

原址：`tools/tests/test_bash32_compat.py` `# R81 包 G（XPL-S1-02）` 區段註解（缺陷本體）。

```text
缺陷本體：本檔的知識寫得很完整（連 `tools/macos_smoke_local.sh` 檔頭都逐字複述一遍），
但**同一份知識住兩個家、只有 `.sh` 那個家被鎖**——`_scan_trees()` 實測回傳 6 棵、
合計 29 支檔，副檔名集合是 `['.sh', '<none>']`，`.yml` **一支都不看**。

危害面是不對稱的：Windows 開發機的 Git Bash 帶 GNU userland、ubuntu CI 也是 GNU，
兩邊都會給出「這樣寫沒問題」的假訊號；只有 macos-latest 的 BSD userland 會炸，而
`macos-compat-ci.yml` 的 inline `run:` 剛好就是唯一跑在那裡的東西，也剛好一個觀測者
都沒有。落地當回合實測：用**本檔自己的 `_PATTERNS`** 掃 12 支 workflow 的 inline
`run:`，命中 3 筆 `date -d`（GNU-only），全在 `root-infra-ci.yml`。
```

### §7 wrapper thinness 鎖：為何併進本檔而非另立新檔（R74 棘輪語意沿革）

原址：`tools/tests/test_check_wrapper_thinness.py` `# R74：根層守門工具的「未知引數 fail-loud」行為級鎖` 區段註解第一段。

```text
🔴 **為何併進本檔而非另立新檔**：`tools/tests/test_adr_xplat001_c1c2_lock.py` 的
`TestGuardLayerRatchet` 是 shrink-only 棘輪，`DEF-101-561③` 明文裁決「禁止新增
鎖檔、只准合併／刪除」（🔴 R78 ARCH-03 訂正：那是 R74 當時**檔數**棘輪的語意；R77 起
換成逐檔行數表，現行語意是**淨行數不得上升**。R73 首版新建獨立檔案當場被擋下的實錄見
`test_check_hooks_liveness.py` 同款註記）。本檔是「根層守門工具自身契約」的既有家。
```

### §8 wrapper thinness 鎖：判準由 `glob("check_*.py")` 改為 CLI 入口的射程修復（R74）

原址：`tools/tests/test_check_wrapper_thinness.py` R74 區段註解第二段（射程修復）。

```text
🔴 **R74 射程修復（SD 獨立複審抓到）：判準原本是 `glob("check_*.py")`，用檔名劃界**
——於是不叫 `check_*` 的工具全部在射程外，而**後果最大的那一支正好在射程外**：
`tools/run_root_unittests.py` 是 pre-push root-infra leg ＋ 三支 CI 真正執行的那一支，
修前全檔 grep `argv|argparse|_cli_flags` 零命中，帶未知旗標時直接跑預設路徑、跑完整棵樹
（逾 120 秒），最終 rc 反映的是「套件結果」而非「旗標被拒收」。它逃掉的唯一原因是檔名。
⇒ 判準改為 **`tools/*.py` 中帶 `if __name__ == "__main__"` 者**（＝真正的 CLI 入口）。
這與 `DEF-101-757`「已知的鎖射程缺口不得只以劃界結案」同型，只是這次的界是**檔名**；
修法刻意**不是**「把那一支加進白名單」——那等於把同一個機制再用一次。
```

### §9 共用淨化層架構鎖：方法論推導與為何用 subprocess（R45）

原址：`tools/tests/test_component_sanitizer_shared_layer_lock.py` 模組 docstring「方法論」兩段。

```text
方法論：對每個版本目錄用 subprocess 起一個乾淨行程匯入該版本的
`tools.fsm_runtime.state_loader`（cwd/sys.path 皆限定該版本根目錄），實測呼叫
`_sanitize_component()` 對已知危險輸入的行為，而非只做文字 pattern 比對——
behavioral 驗證比純文字比對更難被規避：若日後有人把委派邏輯內嵌展開成看似
不同的寫法，文字比對可能誤判為異常，但只要行為仍等價，behavioral 驗證仍會
通過；反之若有人真的另外寫了一份新的弱化實作，文字比對可能因湊巧含有相似
字串而誤判通過，behavioral 驗證則不會被騙。

刻意用 subprocess 而非同行程 import（理由同
`tools/tests/test_sanitize_component_frozen_sdd_versions_lock.py`::
`_latest_sdd_version_name` 與 `test_state_component_sanitizer_parity.py` 的既有
選擇）：30 個版本的 `tools.fsm_runtime.state_loader` 是同一個完全限定模組
名稱，同行程內用 `sys.path` 插拔 + `sys.modules` 手動清快取雖然可行，但每次
都要正確清乾淨三層（`tools` / `tools.fsm_runtime` / `tools.fsm_runtime.
state_loader`），一次沒清乾淨就會讓後面的版本悄悄沿用前一個版本已快取的模組
物件、產生假陽性通過；subprocess 天生行程隔離，不需要人工維護清快取的
正確性，用執行時間換正確性。
```

### §10 共用淨化層架構鎖：R66 追加 `sdd_latest` 回歸鎖的落點沿革（DEF-101-627）

原址：`tools/tests/test_component_sanitizer_shared_layer_lock.py` 模組 docstring「R66 追加」段。

```text
R66 追加（Review round 1 QA 發現，DEF-101-627）：`tools/lib/sdd_latest.py`
（R66 新增，DEF-101-624）當時只做手動 bug-injection 驗證、未落成任何測試檔的
永久斷言。本應為它新增專屬 `tools/tests/test_sdd_latest.py`，但 `DEF-101-561③`
棘輪（`TestGuardLayerRatchet`）自 R61 起要求 `tools/tests/` 擴充既有檔、或先合併／
刪除等量舊物再加（🔴 R78 ARCH-03 訂正：R66 當時量的是**檔數**，R77 起改量逐檔行數的
**淨額**——新增檔案本身不違規，淨額上升才違規）——故改把 `FROZEN_VERSION_DIR_RE`
的 `.fullmatch()` 回歸鎖、`resolve_latest_name`/`resolve_latest_root` 的
success/fail-loud 覆蓋，併入本檔（本檔是原始兩個肇事呼叫端之一，且已 import
`sdd_latest`）；`exclude_frozen_sdd_versions` 的過濾語意併入姊妹檔
`test_sanitize_component_frozen_sdd_versions_lock.py`（見該檔同款追加段）。
```

### §11 context 守衛測試模組的排程器 pin：立案與還原時機（R84／C3-P4c、SA84-01、DEF-200-350）

原址：`tools/tests/test_context_budget_guard.py` `setUpModule()` docstring。

```text
"""🔴 R84／C3-P4c：整個測試模組**一律不准碰真的排程器**（in-process 那一半，子行程
半邊由 `_isolated_env(real_scheduler=False)` 負責）。立案：`_gate()` 同行程呼叫走真的
`quota_halt_actions` → `spawn_sentinel`，會在開發機上留一支永遠沒人收的 launchd job。
🔴 R84／SA84-01：還原動作**不**掛 `addModuleCleanup`（巢狀 runner 會觸發它提前 flush，
pin 當場消失且後續測試失去保護）；捕捉原值只做一次（`_SENTINEL_PIN_CAPTURED`）。
完整立案敘事見證據檔 §I-17。
🔴 DEF-200-350／F-QA-01：pin 同時罩住 `quota_policy.ENV_SPEC` 每一個鍵，理由見
`_pin_sentinel_off`；發現經過與立案敘事已搬至 R86 護欄重釘證據檔 §F。
```

### §12 context 守衛 console-free 掃描面：具名納入站點的逐項理由（R84／C3-A、console_qa 事故、DEF-200-418）

原址：`tools/tests/test_context_budget_guard.py` `ConsoleFreeSpawnTest._sources()` 函式內的具名站點註解。

```text
🔴 R84／C3-A：`schedule_backend.py` 具名加入（不叫 quota_*/sentinel_* ⇒ glob
罩不到，而它是哨兵路徑僅存兩個裸 spawn 的家）。全文＝Resume 證據檔 §L-4.7。
🔴 console_qa 事故輪：另外四支具名加入——`AISDLC_SDD/scripts/sdd_version.py`／
`tools/lib/sdd_latest.py`／`tools/lib/git_paths.py` 三支都不叫 quota_*/sentinel_*
也不住 `.claude/hooks/`，此前對本鎖完全隱形（`sdd_latest.py` 以
`importlib.util.spec_from_file_location` 動態載入 `sdd_version.py`，任何靜態
import 掃描都看不到這條邊；本輪事故正是它們缺 `creationflags` 而彈出 630 個
OpenConsole.exe）；`tools/lib/platform_utils.py`／`tools/_stdio_utf8.py` 這一對
同理補上（`platform_utils.py` 也用 `spec_from_file_location` 動態載入
`_stdio_utf8.py`）——見 `test_every_reachable_dynamic_load_target_is_registered`
那條新規則：動態載入目標必須在這份掃描面裡找得到，否則獨立紅。
🔴 DEF-200-418：`tools/probe/` 此前完全不在掃描面（兩位獨立審查員實跑同一判準
各抓到 3 個假紅站點：`shell_command_corpus.py`／`xplat_hazard_census.py`／
`xplat_injection_matrix.py` 皆是 `subprocess.run(["git", …])` 缺
`creationflags`）。**刻意具名列舉四支，不 glob 整個 `tools/probe/`**——該目錄
大半是文件字串／測試替身裡才提 `subprocess.run` 的分析腳本
（如 `replay_r113_lastmile_driver.py`），全拉進來會製造一批要逐一辯護的假紅
（同本函式 docstring「全拉進來＝要逐一辯護的假紅」的既有原則）。
`console_spawn_watch.py` 本就合規（既有 `NO_WINDOW`），具名納入是為了讓射程
縮小時指名道姓地紅（同下方 `test_the_scan_surface_has_not_silently_shrunk`
的具名斷言紀律）。
```

### §13 DEF-ID 引用完整性鎖：WHY（R60 的 21 處誤引事故）

原址：`tools/tests/test_defect_id_reference_integrity.py` 模組 docstring「WHY」段。

```text
R60 有 21 處 tracked 檔（生產腳本／測試／CI workflow）引用的 DEF-ID 與帳本實際
條目不符——並行修復包在還沒配號時用了暫用號，書面請求主控收尾替換，主控漏辦。
**三個被誤引的號都真實存在但內容完全不同**，於是
`tools/check_defect_log_crossref.py` rc=0（它只在「ID 緊接括號且括號內含狀態
關鍵字」時比對，那些括號裡是「Scan-C C-02」「R60 實測」等非狀態詞 ⇒ 靜默放行），
四道閘門全綠，最後是靠 SA 與 QA 兩位複審者人工逐處對帳才抓出來。
同族的另一半（引用了**不存在**的號）此前也零覆蓋：任何一次打錯字、複製貼上
改錯位數、或帳本歸檔時搬檔搬掉，追溯鏈就靜默斷掉且沒有任何訊號。
```

### §14 dev_start ps1 lastexitcode 鎖：PATH 指向空目錄而非 /usr/bin:/bin 的原因（R67 round 3）

原址：`tools/tests/test_dev_start_ps1_lastexitcode.py` `test_*` 函式內 PATH 隔離註解（Linux 上原寫法為假的實測敘事）。

```text
原寫法自稱「PATH 只留最基本目錄，排除任何 py/python 候選」——那句話在
macOS（12.3 起 `/usr/bin/python` 已移除，只剩 `python3`）與 Windows
（沒有 `/usr/bin`）上恰好為真，在 **Linux 上為假**：ubuntu runner 的
`/usr/bin/python` 是實存可執行檔 ⇒ `Test-IsRealPython` 命中、
「找不到 Python 直譯器」那條**受測分支從頭到尾沒被執行**，腳本改去執行
不存在的 `tools/dev_start.py`，測試看到的是 python 自己的
`can't open file` 與 `RC_AFTER=2`。CI 首次在 Linux 跑本鎖即紅
（root-infra-ci run 30697855439），紅的不是受測物，是測試的前提。
```

### §15 dev_start ps1 lastexitcode 鎖：OutputEncoding 設 UTF-8 的修復沿革（R42，DEF-101-350）

原址：`tools/tests/test_dev_start_ps1_lastexitcode.py` `test_*` 函式內 PATH 隔離註解後段。

```text
[Console]::OutputEncoding 設 UTF-8（R42 修復，DEF-101-350）：本機
為繁體中文 Windows（Big5/950 codepage），dev_start.ps1 的中文錯誤
訊息若不明確指定輸出編碼會被以錯誤 codepage 解讀成亂碼，斷言
因而誤判失敗——同一根因/同一修法比照本輪稍早
test_install_post_commit_windowsapps_guard.py::_run_with_shadowed_python()
的既有修復。
```

### §16 dev_start ps1／sh 被 source 鎖：class 級 skip 述詞由 os.name 改為「兩支殼都解不到」（R79／R82）

原址：`tools/tests/test_dev_start_ps1_lastexitcode.py` `TestDevStartShSourcedRcSemantics` 上方的 skip 述詞註解。

```text
🔴 R79（D-skipped #6）：reason 前綴補 `[POSIX-NATIVE-ONLY]`。這個站點與同 repo 8 筆
已標籤者**完全同形**（例 `test_dev_start.py:1362`），差別只在沒帶標籤，於是 runner 的
skip 明細把它底下的 6 支測試印成「未標籤」，與真正的環境性 skip（缺 zsh／缺舊直譯器／
無 symlink 權限，共 5 筆）混在同一桶。後果不是美觀問題：S3「徹底消除 skipped」的分流
者照那份輸出讀，會把「補環境就能救回」的工作量高估一倍，或反過來去修根本不該在
Windows 跑的測試。標上之後 `_POSIX_TAG_RATCHET["tools/tests"]` 由 1 降為 0（連同
shrink-only 天花板一起下修——天花板不跟著降＝把剛還掉的欠債額度留著日後無聲用回去）。
🔴 R82 CARRIER-02：class 級述詞由 `os.name == "nt"` 改成「兩支殼都解不到」。

舊述詞把 6 支整組判成 `[POSIX-NATIVE-ONLY]`，理由是「不在 Windows 上驗證非目標平台
的殼」。R82 逐支實跑推翻了那個歸類：Windows 上 **Git Bash 是真的 bash**（不是模擬層），
上面七項契約（sourced 偵測、`${BASH_SOURCE[0]}` 路徑解析、rc 透傳、venv 啟用、零殘留）
走的就是 `.sh` 那條程式碼路徑，一項都沒有依賴 POSIX 專屬語意。實測：只把 `_SH_BASH`
換成 Git Bash 絕對路徑，bash 三支立刻 2 綠 1 紅，而唯一那個紅是斷言把 `/` 與 `\` 當成
不同字串（Git Bash 回報的 `VIRTUAL_ENV` 用正斜線），不是受測物的行為缺陷。
⇒ 這 6 支裡真正 mac-only 的只有 zsh 那 3 支（見各自的 method 級 skip）。
```

### §17 ADR 量測 token 鎖：R71 錨點改指的經過

原址：`tools/tests/test_doc_loc_baseline_freshness_r60.py` `# R69：ADR 內量測 token ↔ 現查` 區段註解 ④(c)。

```text
         🔴 **R71 錨點改指（本條原文自己預告過的那件事真的發生了）**：原文寫「改為指向
         live 來源而不寫死數字本身是更好的作法，但它會讓本鎖失去唯一的活體比對——真要
         那樣改，請在同一個 commit 內把本條錨點自檢改指新的活體站點」。R71 正是那一輪：
         `ADR-XPLAT-003` 的四處 `total=／cap=` 已全數改為時代快照（掛豁免）或改指 SSOT，
         `ADR-XPLAT-002` 的兩處本來就掛著豁免 ⇒ 非豁免受管 token 歸零。
         依原文指示同 commit 完成兩件事：
           ① 本條的計數改為「**掃描面上還看得見 LOC token 的形態**」（豁免者也計入）——
              它守的是「regex 與掃描面還活著」，這一層仍然有效且仍會在整段刪除時翻紅；
           ② **活體比對改指 `ONBOARDING.md` §7 表① 的 `loc-baseline-live:` 那一格**，
              由本檔 `TestR69AdrMeasurementTokensAreLive::
              test_live_loc_ssot_station_carries_the_live_comparison` 直接對現查值比對。
              該格本就是本 repo 指定的唯一 live 家、且有 `--write` 一鍵回填，
              ADR 不必也不該再開第二個家（理由與 ADR §8(b) 對 pytest 計數一字不差）。
```

### §18 鐵律三覆蓋率清單：R80 三項移出本清單與低報分子的訂正

原址：`tools/tests/test_doc_loc_baseline_freshness_r60.py` `_IRON_LAW3_*` 清單旁的 R80 註解。

```text
🔴 R80（包 B）：`$env:*` 讀取／`Get-Command` 解析／大小寫敏感度 三項移出本清單。
前兩項是**本輪補上站點級判準**（`TestPowerShellPlatformSensitiveSites`）⇒ 分子 +1 +1；
第三項則是**訂正一筆假事實**——`tools/check_ntfs_paths.py` 的大小寫碰撞正規化鍵
早就存在、也早就接在 pre-commit 與四支 CI workflow 上，本表卻自 R74 起一直說沒人守。
這個方向（**低報分子**）本鎖結構上看不見：它只讀那張表**自己說**有沒有機械物，
從不問「這句話是真的嗎」。補上的證偽判準住在
`tools/tests/test_platform_neutral_paths.py::TestIronLaw3NoMechanismClaimsAreFalsifiable`
——每一格自陳沒人守者必須登記一組證偽探針（token × 已審視清單）並通過它。
```

### §19 基線豁免 shrink-only 天花板：R79 立案理由與逐格收緊沿革（33→25）

原址：`tools/tests/test_doc_loc_baseline_freshness_r60.py` `_BASELINE_*_MAX` 常數上方的 `#:` 註解。

```text
為何需要它（R79 立案理由）：上方那句「只准變少」在 R78~R79 之間**只是散文**——
`test_the_baseline_is_not_stale` 只管「已解析得到／已無人引用」這兩種 stale，
對「順手多登記一筆新幽靈」零訊號，而那正是這道鎖最省力的關法。
擴掃描面而多看見存量時，重釘本值並在交件回報寫出前後值與理由（同 `_FROZEN_GUARD_LINES`
的重釘紀律）；**不得**為了讓一筆新寫下的懸空引用過關而調高它。
33→32→31→30→29 的逐格收緊沿革（R85／R89／R95／R115）已搬至 round-label-ok
CrossPlatform_R127_Guard_Prose_Migration.md。26→25：幽靈已清（DEF-200-306 收尾）。
```

### §20 第三態來源自證：補洞前的缺陷與本機實測（R82／P4）

原址：`tools/tests/test_doc_loc_baseline_freshness_r60.py` `test_a_machine_local_ignore_rule_never_grants_the_third_state` docstring 第二段。

```text
補洞前的缺陷：判準只問「被不被 ignore」而不問「**是誰宣告的**」，於是
`$GIT_DIR/info/exclude`（`git clone` 就地新建、untracked）與 `core.excludesFile`
（使用者家目錄的全域 ignore）也能授予第三態。那兩個檔都不隨 repo 走 ⇒ 同一條宣稱
在 A 機器判 `'ignored'`、在 B 機器判 `'missing'`，紅照樣在平台間漂移——與本包原本
要治的病同型，只是量測面從「檔案系統」換成「這台機器的 git 設定」。複驗當回合在
本機實測它已經活著：`.git/info/exclude` 有 10 條 repo 完全沒宣告的 `**/.claude/*`
規則，`AutoClaude/.claude/agent-registry.json` 因此被判成第三態。
```

### §21 交棒宣稱區塊切分：R82 Q4-01 上一版只看條目的缺陷

原址：`tools/tests/test_doc_loc_baseline_freshness_r60.py` `_handoff_claim_blocks()` docstring 第二段。

```text
🔴 R82 Q4-01（本輪改的就是這一段）：上一版**只看條目**——`_HANDOFF_ITEM_RE` 不命中
就不開區塊，於是整段散文連同它底下的 fenced code 一律被丟掉。當時寫下的理由是
「前言是體例與訂正說明的住處，把它當成宣稱會逼人在規則本身上貼標記（噪音）」，
而 R81 的交棒書把那個理由的前提打掉了：它的 §3「交給 R82 的待辦」七個小節**一條
list item 都沒有**，全是段落散文＋fenced code ⇒ 整節不進分母，該份交棒書當回合
實測**整份 0 命中**（探針：直接 import 本模組呼叫 `_handoff_problems`）。
也就是說「用散文寫」變成一個免費的逃逸口，而且是**無聲**的——鎖照跑、照綠。
```

### §22 交棒宣稱鎖：登記表需要的理由（R82 Q4-01 誠實劃界）

原址：`tools/tests/test_doc_loc_baseline_freshness_r60.py` 交棒書宣稱零命中具名登記表上方的 `#:` 註解。

```text
🔴 為何需要這張表（R82 Q4-01 的誠實劃界）：反崩塌斷言由「跨文件加總 ≥1」改成
「逐文件 ≥1」之後，這三份當回合實測就是 0。成因**不是**它們沒有待辦，而是取材面
還有**第二個縫**，在 `_HANDOFF_SECTION_WORDS`（章節觸發字）那一軸：
  · R75／R76 的待辦大節叫「交給 R76／R77 的事」，不含任何觸發字 ⇒ 整份 blocks=0；
  · R78 的「交給 R79 的事」同理，其條目用「未溯源／未指派」這類不在
    `_HANDOFF_STALE_WORDS` 的措辭 ⇒ 收到了區塊也命中 0。
本輪刻意不動那一軸：把「交給」加進觸發字，R76 §5-1 會當場轉紅（實測 1 筆），
而那三份檔不在本包的檔案所有權內，並行輪次動它們會與別包互踩。⇒ 登記＋交棒。
```

### §23 extras 引號鎖：掃描面逐輪擴面的沿革與實測（R57 round 1／R59）

原址：`tools/tests/test_extras_quoting_zsh_safety.py` `_SCAN_PATHSPECS` 上方註解。

```text
R57 round 1 Architect／QA 交叉指出（DEF-101-479）：原掃描面只有 tracked `*.md`，
完全看不到**執行期真的印給使用者複製貼上**的訊息——`AutoClaude/tools/git-hooks/pre-push`
與 `AutoClaude/tools/local_ci_gate.py` 當時各有一處壞形態，這道鎖卻全綠。那比文件更要命：
那是 push 被擋當下的唯一指引，mac 使用者照做 → `zsh: no matches found` → 再 push 再被擋，
形成迴圈。故掃描面擴為「tracked *.md + *.sh + *.py + 三處 git-hooks 無副檔名檔」。
R59（DEF-101-507）再加 `*.toml`/`*.yaml`/`*.yml`：`AutoClaude/pyproject.toml` 的 extras
註解（6 處）與 `AutoClaude/config.yaml`（1 處）原本連掃描面都進不去，而 pyproject 的
註解正是「要裝選配時最先讀到的一行」；`.github/workflows/*.yml` 已全用雙引號，加入
後實跑確認零誤報。`.ps1` 仍刻意不納入：PowerShell 無此 glob 語意，納入只會製造偽陽性。
R59 SD-R59-06：加入 `*.yaml` 後掃描面由 ~3,000 暴增到 24,140 份（單模組 20.3s，
且是每次 pre-push／根層 unittest 都要付的延遲），暴增主因是 AISDLC_SDD 30 個凍結版
的 governance/R-*.yaml 與 docs_template。凍結版依 Copy-on-Evolve 政策不回改，
掃它們對本鎖零收益，故以 pathspec 排除；LATEST 版仍在掃描面內。
```

### §24 extras 引號鎖：豁免預算必須分兩本帳的問題立案（R59 ARCH-R59-02）

原址：`tools/tests/test_extras_quoting_zsh_safety.py` `# ── R59 ARCH-R59-02：豁免預算必須分兩本帳` 區段註解「問題」段。

```text
問題（Architect 一審實測）：`_MAX_EXEMPTIONS` 的設計意圖是偵測「豁免被當成繞過後門」，
但實測 9 筆已用豁免裡有 8 筆**在本鎖檔自己內部**——因為判準 (4) 的三段式邊界宣稱
**要求**逐項列出被涵蓋／不涵蓋的壞形態，而列出壞形態就得引述壞形態、就得申請豁免。
於是這個計數器現在量的主要是「本鎖的規格文件有多長」，不是「有沒有人濫用豁免」。
後果可預測：下一輪只要新增一種形態、依判準補一行病例樣本就撞頂，而撞頂訊息會說
「疑似被當成繞過手段」——**把成因指錯人**，最省力的反應就是再調高上限（R57→R59 已
調過一次 5→10）。這正是姊妹檔 test_windowsapps_guard_cross_consistency.py 的腐化
路徑起點：機制被自己的文件需求推著鬆綁。
```

### §25 find_git_bash 結構等價鎖：Scan-A 兩處語意分歧與 R60 P10-2 相反裁決的逐項說明

原址：`tools/tests/test_find_git_bash_parity.py` 模組 docstring「背景」三點。

```text
背景（Scan-A 掃描實證的兩處真實語意分歧，已於本輪修復）：
  1. 環境變數空值處理：`tools/lib/Find-GitBash.ps1` 舊版對
     `$env:ProgramFiles(x86)` 等環境變數不存在時直接做字串插值，會插出裸路徑
     （如缺變數時 `"${env:ProgramFiles(x86)}\\Git\\bin\\bash.exe"` 變成
     `"\\Git\\bin\\bash.exe"`）仍呼叫 `Test-Path`；
     `tools/integration_gate_core.py::find_git_bash()` 明確 `if not base: continue`
     跳過。PS1 版已改用 `[System.Environment]::GetEnvironmentVariable` + 明確空值
     判斷對齊。
  2. System32 排除鬆緊：PS1 版 regex `-notmatch '\\System32\\'` 要求完整路徑段
     匹配；Python 版原本 `"system32" not in found.lower()` 任意子字串命中即排除
     （較寬鬆，可能誤傷路徑含 "system32" 子字串但非該目錄段的候選）。Python 版
     已改為 `_has_system32_segment()` 依 `PureWindowsPath` 路徑段逐一比對對齊。

  3. **R60 P10-2（真 parity 缺陷，兩側對同一輸入相反裁決）**：上述第 2 點的靜態鎖
     只比對「兩邊拿哪個**字面詞**去比」，對「用什麼**手法**比」全然盲目。實測
     `C:/Windows/System32/bash.exe`（正斜線寫法；Windows 上與反斜線寫法指向同一個
     檔案）PS 側行內 regex `-notmatch '\\System32\\'` 判**放行**、Python 側
     `PureWindowsPath` 逐段比對判**排除**；且可觸達——`(Get-Command bash).Source` 由
     「PATH 條目 + 檔名」拼成，PATH 條目寫正斜線時 Source 就帶正斜線，修前
     `Find-GitBash` 實測回傳了 WSL 的 bash。PS 側已改為 `Test-HasSystem32Segment`
     逐段比對（Python 側為正解、不動），並新增下方 `TestSystem32VerdictParity`
     **行為表 parity 鎖**。
```

### §26 整合閘門本機活體載具：為何住在 find_git_bash 鎖檔（R67-C18／R78 棘輪語意訂正）

原址：`tools/tests/test_find_git_bash_parity.py` `# R67-C18：tools/integration_gate…` 區段註解第一段。

```text
為何住在本檔（收納契約，非雜物抽屜）：本檔已是 `tools/integration_gate_core.py` 的
既有鎖檔（上方 `find_git_bash` 家族即該模組的函式），import 與 `_PY_PATH` 都指著它。
`DEF-101-561③`（由 `test_adr_xplat001_c1c2_lock.py::TestGuardLayerRatchet` 機械強制）
要求「把新判準擴充進既有鎖檔」，本節即依該裁決把新判準併進同一模組的既有鎖檔。
🔴 R78 ARCH-03 訂正：該棘輪量的已不是**檔數**（R77 退場），而是逐檔行數表的**淨額**
——新增檔案只要同一次變更內刪掉等量以上的行就合法，別把舊語意當現行規則照抄。
```

### §27 整合閘門本機活體載具：WHY（R67 全庫普查：零呼叫端＝實質已死）

原址：`tools/tests/test_find_git_bash_parity.py` `# R67-C18` 區段註解第二段。

```text
WHY 這組鎖必須存在（Rule 9 — 鎖意圖而不只鎖行為）：
整合層閘門的存在理由是「兩子專案各自綠燈不代表整合綠燈」（[3/5] SDD bridge 整合煙霧、
[4/5] 回退驗證、[5/5] cc-switch A/B）。但 R67 全庫普查實測：它在整個自動化層**零呼叫端**
——唯二執行者是 .github/workflows/macos-compat-ci.yml 與 windows-compat-ci.yml 各一行
（`bash tools/integration_gate.sh --skip-full` / `./tools/integration_gate.ps1 -SkipFull`），
而兩支 compat-CI 因 CI 帳務停擺（DEF-101-081）已多輪未真正執行。
**雲端是唯一執行者的東西＝實質已死**：閘門本體被改壞在本機任何流程都不會紅。
```

### §28 workflow 結構鎖：B 節不用 pyyaml、C 節用 pyyaml 的取捨（R57／R68）

原址：`tools/tests/test_gha_action_versions.py` 模組 docstring「【B 節為何不用 pyyaml、C 節為何可以】」段。

```text
【B 節為何不用 pyyaml、C 節為何可以】B 節立於「根層 stdlib-only」前提（R57），
自帶縮限用途的縮排掃描器 `parse_shell_distribution()`（已實測涵蓋根層 11 支
workflow 中 7 支、與 `yaml.safe_load` 逐 job 比對全部相等；帶 `defaults:` 區塊的
4 支主動 raise 不猜測；非本 repo 的任意 YAML 寫法一律不保證，失效方向是紅燈）。
R68 起該前提已由 repo 自己推翻——`tools/run_root_unittests.py` 的
`_THIRD_PARTY_PREREQS` 已把 pyyaml 列為受管相依（三道機械物看守安裝），C 節
因此直接用 pyyaml 判「run 本體」這個值，不重複造第二套掃描器；B 節維持原樣
（不改動既有綠鎖）。史料見 CrossPlatform_DEF200275_Context_Metering_Evidence.md
〈第七輪 史料搬遷〉。
```

### §29 線上排程期望值 SSOT 鎖：為何併進 install_windows_nightly 鎖檔（R74／R78）

原址：`tools/tests/test_install_windows_nightly.py` `# R74 — 線上排程設定的期望值 SSOT ＋ 漂移偵測器` 區段註解第一段。

```text
🔴 **為何併進本檔而非另立新檔**：`tools/tests/` 有一道護欄層 shrink-only 棘輪
（`DEF-101-561③`；R74 當時量的是檔數，🔴 R78 ARCH-03 訂正：R77 起已換成
`test_adr_xplat001_c1c2_lock.py::TestGuardLayerRatchet` 的逐檔行數表，現行語意是
**淨行數不得上升**、不是「禁止新增檔案」）。本檔是最貼近的家——它本來就是這兩支排程任務與其安裝器
的鎖之家，上方 TestUnattendedExecutionHardening 鎖的正是同一組設定值。
```

### §30 macOS smoke「SKIP 誠實外顯」鎖：缺陷現象與實測（R60 Scan-F F-01）

原址：`tools/tests/test_macos_smoke_skip_honesty.py` 模組 docstring「缺陷現象」段。

```text
缺陷現象（R60 Scan-F F-01，實測於 Windows 11 + Git Bash MINGW64_NT-10.0-26200）：
該腳本在**非 Darwin** 平台把兩項無法驗證的子測試以「SKIP-計-PASS」計入 PASS，
收尾印出的 `===== 彙總：PASS=13 FAIL=0 =====` ＋ `全部通過 ✅` ＋ `rc=0` 與**真
macOS 滿版全驗**逐字相同、計數相同（兩平台皆恰 13——兩處互斥分支已由
`tools/tests/test_smoke_ci_sync.py::_SH_EXCLUSIVE_PASS_GROUPS` 登記），事後稽核
無從分辨「在 Windows 上跑過」與「在 macOS 上全綠」。R59 由 DEF-101-511/512 立的
原則（「讓結論自己說出降級事實」）當輪未回頭套用到這支腳本。
```

### §31 成熟度判準 M1／M5／M6 機械物：被守的四筆實測缺陷（R79）

原址：`tools/tests/test_maturity_criteria_r79.py` 模組 docstring「被守的是什麼」四筆缺陷。

```text
0. **M1 在自己的 SSOT 裡有兩個不等價定義**（R79 四方複審 ARCH blocking，收輪後補）。
   門檻欄只提 UEP／ADR、且是「二擇一」；〈五個收斂條件〉第 1 條卻寫「鎖檔行數不再上升」。
   達標判定走的是門檻欄那一個 ⇒ 寫一段 ADR 宣告 UEP 為終態，M1 就翻成達標，而護欄層
   可以繼續每輪長近兩千行——**「護欄層停止自我增殖」這條判準，可以在護欄層根本沒有
   停止增殖的情況下被滿足**。修法：門檻改成合取（UEP 半 **且** 護欄行數半），
   三處措辭統一，並由 `TestM1ThresholdIsAConjunction` 機械守（刪掉任一半即紅）。
1. **M5 可以靠加語料刷分。** SSOT 開宗明義寫「成熟度的量必須量缺陷穿過幾道閘，不能量
   有幾道閘——後者可以靠新增鎖無限刷分」，並特別點名 M5「加鎖不會讓它上升」。實測是：
   M5 當時的門檻是**比率**，而唯一在守它的棘輪釘的是**絕對攔截數**，分母完全不受任何
   約束 ⇒ 複製十幾題「現行判準本來就攔得到」的語料（語料裡現成就有可抄的），兩個方向
   的比率都能跨門檻、差距也在容許內，而 `test_the_corpus_covers_both_directions_and_
   is_not_shrinking`（題數只准增）、`test_the_interception_rate_only_improves`（攔截數
   只准升）、`test_every_sample_matches_its_recorded_verdict`（判決要相符）**三支全綠**。
   ⇒ 這份專門用來防刷分的文件，自己有一條是可以刷的。

2. **刪難題補簡單題**也能讓數字變好看：既有的 `len(corpus) >= 22` 只看總數，一題換一題
   不會被它看見，而「換掉的是唯一一題攔不到的」與「換掉一題攔得到的」在它眼裡一樣。

3. **M6 的達標判定綁在一份輪次專屬的凍結檔上。** R78 ARCH-05 的整個立論是「活判準不能
   寄生在輪次專屬文件裡，那種文件按定義不會有人回頭維護」；判準表搬了家，M6 的證據面
   沒搬——同一個病只治了上半身。
```

### §32 成熟度判準機械物：為何新增一支檔而不是併進既有鎖檔（R79）

原址：`tools/tests/test_maturity_criteria_r79.py` 模組 docstring 末段「為何新增一支檔案」。

```text
唯一在守成熟度 SSOT 的既有鎖住在 `test_doc_loc_baseline_freshness_r60.py`——那支檔案
本輪已被獨立判為「雜物抽屜」（5,649 行／32 class／橫跨 R60~R78，檔名只描述其中一小塊）
且由別的包在改。往一個已知過載、且正被別人動的檔案裡再塞一段，是把兩個問題疊在一起。
代價明說：`tools/tests/test_adr_xplat001_c1c2_lock.py` 的 `_FROZEN_GUARD_LINES` 逐檔
行數棘輪會因此暫時紅，重釘一律由收尾包在所有包停工後做一次——**不在本包射程內**，
已列入交件回報。這是已知且已回報的狀態，不是漏看。
```

### §33 否定存在宣稱鎖：立案事故（R82／Q4-02，交棒書斷言閂鎖尚未落地而同 commit 已落地）

原址：`tools/tests/test_negative_existence_claims_r82.py` 模組 docstring「立案」段。

```text
Q4 那一輪重跑歸因後最大的一桶是「**宣稱先於查證**」，而 repo 現有的三面 CLAIM-FIRST
判準（幽靈路徑／幽靈符號／機械物實質）**全部只判正向存在**——文件說某個檔／符號／機械物
在，就去驗它真的在。反向那一半（「尚未落地」「零交付」「沒有任何一行」）全庫零判準。

它放過的第一個真實案例就寫在同一輪的交棒書裡：`docs/04_planning/R81_HANDOFF.md` §3.2
斷言那道降級閂鎖還沒有被寫出來，而它在**同一個 commit**（`692753e`）裡就已經落地。
那句話同時逃過兩道既有的鎖——幽靈路徑鎖只判路徑存在，交棒宣稱鎖那一輪對整份 R81
交棒書收到 **0 筆**條目（散文體例不進它的分母，屬 Q4-01，另一包在修）。
```

### §34 否定存在宣稱鎖：為何新增一支檔而不是併進 doc_loc 鎖檔（R82）

原址：`tools/tests/test_negative_existence_claims_r82.py` 模組 docstring 末段。

```text
🔴 為何新增一支檔而不是併進 `test_doc_loc_baseline_freshness_r60.py`
-------------------------------------------------------------------
那支檔本輪由**另一包**在改（Q4-01 正是改它的 `_handoff_claim_blocks()`），兩包同時動
同一支檔會互踩成假紅。代價明說：`tools/tests/test_adr_xplat001_c1c2_lock.py` 的
`_FROZEN_GUARD_LINES` 逐檔行數棘輪會因此暫時紅，重釘由收尾包在所有包停工後做一次
——**不在本包射程內**，已列入交件回報。這是已知且已回報的狀態，不是漏看。
```

### §35 nightly 直譯器決定性鎖：模組 docstring 沿革（DEF-101-506／DEF-200-302／DEF-200-314／DEF-200-315）

原址：`tools/tests/test_nightly_interpreter_determinism.py` 模組 docstring（事故立案、DEF-200-302 訂正、B~H 各項逐字說明、原 A／D 項移除說明）。

```text
DEF-200-302 起改為「釘死」而非「使其等價」，見下方訂正）。

WHY（2026-07-27 真機事故，DEF-101-506 立案時的原始問題）：
`run_local_nightly.ps1` 把直譯器存成字面 token `$script:PyExe = 'python'`，每個
呼叫點都由 PATH **現場解析**。於是同一支 nightly：

  - schtasks 排程下 → pyenv-win 的 python（`python.bat` shim，且裝了 psycopg2）
  - 已啟用 monorepo .venv 的終端機／agent 下 → `.venv\\Scripts\\python.exe`
    （真 .exe，且**未**裝 `[postgres,pgvector]` 選配）

兩者跑出來的紅綠不可互相比較：實測一次以 .venv 跑出 `pg-e2e=1`（psycopg2 缺席）
與 `perf=1` 兩個假紅並寫進 `nightly_latest.log`；更隱蔽的是它讓 DEF-101-503
（`%` 被 batch shim 吃掉）的修復「綠得沒有鑑別力」——真 .exe 本來就不觸發該 bug，
沒修也會綠。而 log 當時只印字面 token「python」，事後完全無法指認是哪一顆。

🔴 **DEF-200-302 訂正（掌舵者 2026-09-15 裁決 B 案）**：DEF-101-506 當時的修法＝讓
schtasks 與已啟用 venv 兩種啟動方式「殊途同歸」（互動 shell 偵測到已啟用 venv
就把它的 Scripts 從本行程 PATH 剝除，使解析退回 pyenv 全域）；本檔原本因此在
下方（已刪除的）A/D 兩類鎖住這段「正規化」邏輯與其斜線比對細節。前提已由主控
本場實測推翻：根層 .venv 的 `pyvenv.cfg` home 本身就是同一顆 pyenv-win 3.11.9
二進位，且 xdist／psycopg2／sqlalchemy／pgvector／asyncpg／alembic／pytest 七
項在 pyenv 全域與根 .venv 兩邊皆 PRESENT——「兩套互不受控、可能分岔的依賴集
合」這個風險已不成立（2026-09-13 nightly 曾因 PATH 上的 pyenv 全域缺 xdist 而
pytest rc=4，正是那個風險的真實代價）。故 Windows 側改為與 mac 側同款「絕對路
徑釘死」：不論 schtasks 或已啟用 venv 的終端機／agent 觸發，`run_local_nightly.
ps1`／`windows_smoke_local.ps1` 一律直接使用 `<repo 根>/.venv/Scripts/python.exe`
絕對路徑，不再靠 PATH 現場解析「使其等價」；找不到就 fail-loud（exit 1）。

本檔鎖五件事（B/C 為既有行級靜態檢查；E 為 Windows 絕對路徑釘死鎖，鎖的三支檔＝
`AutoClaude/tools/run_local_nightly.ps1`／`tools/windows_smoke_local.ps1`／
`AutoClaude/tools/local_ci_gate.ps1`；新增 F 為 DEF-200-302 mac 側補齊，鎖的兩支
檔＝`AutoClaude/tools/run_local_nightly.sh`／`tools/macos_smoke_local.sh`）：
  B. 兩支載具都必須把**解析後的直譯器路徑**寫進 log（禁止只印字面 token）。
  C. mac 側維持「絕對路徑釘死」而非 PATH 現場解析（見 F：本輪起兩支 .sh 皆已
     拔除缺席時的 PATH 退路，不再只是「主路徑釘死、缺席仍退回現場解析」）。
  E.（DEF-200-302 新增）Windows 側兩支 .ps1（`run_local_nightly.ps1`／
     `windows_smoke_local.ps1`）都必須絕對路徑釘死根層 `.venv\\Scripts\\
     python.exe`、都必須有 fail-loud 分支（`Test-Path` 不成立即 `exit 1`）；
     `run_local_nightly.ps1` 不得再把 PATH 現場解析的 `Test-IsRealPython
     -CandidateName 'python'` 當直譯器決定者，也不得再含「偵測 `$env:VIRTUAL_ENV`
     即剝除其 Scripts」的正規化區塊；nightly 對 `local_ci_gate.ps1` 的呼叫必須
     帶 `--unattended`（DEF-200-291 無人值守 advisory 降級的前置條件）。
  F.（DEF-200-302 mac 側補齊，2026-09-15）`run_local_nightly.sh` 與
     `macos_smoke_local.sh` 都必須絕對路徑釘死根層 `.venv/bin/python`、都必須
     有 fail-loud 分支（`[ ! -x "$PY" ]`／`[ ! -x "$python_bin" ]` 不成立即
     `exit 1`）；兩檔皆不得再含 `command -v python || command -v python3` 這類
     缺席時退回 PATH 現場解析的分支——`run_local_nightly.sh` 原本就有這段退路
     （C 項此前只驗證「主路徑有沒有釘死」，沒驗證「缺席時是否真的 fail-loud」，
     故放過了它），`macos_smoke_local.sh` 則原本只用 `is_real_python_candidate
     python` 判斷 PATH 上的 python 是否為真直譯器，未保證它就是本 repo 根層
     .venv 那一顆。
  G.（DEF-200-314 新增，2026-09-17）mac launchd nightly 三症狀之二：
     `run_local_nightly.sh` 對 `local_ci_gate.sh` 的呼叫必須帶 `--unattended`
     （E 項已鎖 Windows 側 `-Unattended`，本項補 mac 對稱半——鐵律三漏補）；
     且必須以存在性探測 prepend 兩種 Homebrew bin 前綴（`/opt/homebrew/bin`
     與 `/usr/local/bin`，不可用 `brew --prefix`），修 launchd 極簡 PATH 缺
     pwsh 導致需要 powershell/pwsh 的測試從 platform skip 落成 untagged、
     撞 skip 天花板的問題。
  H.（DEF-200-315 新增，2026-09-19 掌舵者裁決）：互動式入口（git hooks／
     integration_gate／ci-gate）改優先釘死 repo 根層 .venv，不再從 PATH 現場挑
     python/python3——與本檔既有 B~G 項守的「nightly 載具」屬同一類危害的
     不同呼叫面。本輪（Dev-A1）鎖住五組檔：`tools/git-hooks/pre-commit`／
     `tools/git-hooks/pre-push`／`tools/integration_gate.sh`／
     `tools/integration_gate.ps1`／`AISDLC_SDD/scripts/ci-gate.sh`／
     `AISDLC_SDD/scripts/ci-gate.ps1`（Dev-A2 會再擴充
     `_INTERACTIVE_ENTRY_FILES`）。
     Dev-A2 棒擴充 AutoClaude/tools 消費端＋安裝共用核心＋copy_on_evolve：
     `AutoClaude/tools/local_ci_gate.sh`／`.ps1`、`AutoClaude/tools/run_act.sh`／
     `.ps1`、`AutoClaude/tools/g0_gate_check.ps1`、
     `AutoClaude/tools/sd06_w3_staging_dryrun.sh`、
     `AISDLC_SDD/scripts/copy_on_evolve.sh`、`tools/lib/git_hooks_install_common.sh`、
     `tools/lib/GitHooksInstallCommon.ps1` 皆呼叫標準 SSOT，套用 H1~H3。
     🔴 `AutoClaude/tools/git-hooks/pre-push`／`pre-commit`（子 hook，非根層
     dispatcher）判準不同：它們維持自己既有的 ①②③ 候選鏈（根層 .venv 健康探針
     → 子專案 venv 只警告 → PATH python/python3），不呼叫 `pick_repo_python`
     本身，只把既有 ③ PATH 段落包進
     `repo_python_path_fallback_allowed` 條件——標準 H1/H2 判準不適用，改由 H5
     以專屬正則驗證該包住形態。

原 A 項（Windows PATH 正規化區塊行級檢查）與 D 項（該正規化比對式的行為級鎖，
DEF-101-522）鎖的正是本輪拔除的那段邏輯，隨程式碼一併移除——史料見 git 歷史與
docs/06_quality/AutoSDD_Defect_Log.md 的 DEF-200-302 條目，不再保留無程式碼可
對照的死鎖。

刻意仍不鎖「兩平台必須用同一顆直譯器」這個問題本身的框架：mac 釘
`.venv/bin/python`、Windows 釘 `.venv\\Scripts\\python.exe`，兩邊本就分屬各自
平台的 `.venv`、路徑分隔符也天然不同——這不是「兩顆不同的直譯器」，只是同一
種「絕對路徑釘死」政策在兩個平台上的自然表達。
```

### §36 noqa 指令形態鎖：R69 終審 P1（本節第一版自己犯了它要治的病，兩層）

原址：`tools/tests/test_no_invalid_escape_sequences.py` `# ---- R69（DEF-101-702／R68-39）：noqa 指令本體的形態` 區段註解後段。

```text
🔴 R69 終審 P1（本節第一版自己犯了它要治的病，兩層）：
  ① 上面這幾行原本把「井號＋noqa」的組合逐字寫在**註解**裡當說明，而 ruff 解析註解時
     不管它是不是說明——冷 cache 實測本檔逐次吐三條 `warning: Invalid ... directive`
     （235／237／242 行）。示範壞形態的**註解**會被工具當真，這正是本檔檔頭
     警告過的「示範壞形態的文件會反咬自己」，只是換了一個工具。
     （本段連引述那句 warning 都不敢寫全，正是因為引述本身就會再製造一條 warning。）
     修法：散文一律不寫出該組合（改稱「noqa 指令」），要示範就用下面的 `_HASH` 拼。
  ② 樣本字串（`test_detector_*` 的輸入）也讓**本檔自己**被自己的掃描器命中，於是第一版
     加了一條「整檔自我豁免」——本鎖對最該被守的那支檔（它自己）射程為零，且該豁免還
     掩護了 ① 那個真的壞掉的指令。修法：樣本改用 `_HASH` 動態拼接，源碼任何一行都不再
     出現可被解析的指令，整檔豁免隨之刪除（同本檔既有 `chr(92)` 合成壞形態的慣例）。
```

### §37 作用域級存量債表：上方註解壓縮前原文（逐筆沿革另見第一冊〈作用域級存量債表沿革〉）

原址：`tools/tests/test_platform_neutral_paths.py` 作用域級存量債表上方 `#:` 註解。

```text
站點級判準上線當回合的**存量**：檔案級特赦收成作用域級之後，仍未被任何作用域
守衛罩住的使用點數，逐檔精確計數。
判準是**雙向精確比對**：多一筆紅（新增了未守衛的使用點）、少一筆也紅（債已還，
請把數字改小）——只准降不准升的單邊寫法會讓這張表變成一張永久保護傘。
合法出口只有兩條：① 把站點改成作用域內守衛；② 該行行尾加 `_XPLAT_OK_MARKER` 標記。
（本註解刻意不寫出那個標記的字面值——本檔自己也在掃描面內，寫出來就會被
  `_xplat_markers()` 當成一個真的豁免標記而判 stale。）
🔴 表列債的逐筆沿革——R79 誠實劃界（`tools/dev_start.py` 訊號 handler 不屬包所有權、
  只登記不代改）與 R81（XPL-S1-04）詞彙表補 `ctypes.*` 後 4→5 的逐點實測（9 站點
  8 個被既有作用域守衛罩住、`:1051` 安全性寄託呼叫端）——
  全文搬至 CrossPlatform_Guard_Line_History.md〈作用域級存量債表沿革〉節。
```

### §38 目錄項原語存量表：凍結版不入掃描面的量測與 DEF-200-202 修復窗口說明

原址：`tools/tests/test_platform_neutral_paths.py` `_DIRENT_UNGUARDED_DEBT` 上方註解。

```text
存量：**live 樹**內未處置 `PermissionError`／`OSError` 的站點數。
判準是雙向精確比對（同本檔其餘欠債表的理由）。
🔴 掃描面刻意不含凍結版 v0.01~v0.29，兩個理由缺一不可：① Copy-on-Evolve 禁改
  凍結版，那裡結構上不會出現「新寫的」違規，掃它得不到可行動的訊號；② 當回合
  實測含凍結版時整支測試要 **133 秒**（凍結版 1,131 筆是同一批程式碼被複製 29 次），
  而護欄層的執行時間本身已是本輪一筆獨立 finding。凍結版的那 1,131 筆是**已量到、
  刻意不進帳**的事實，不是沒看見。
DEF-200-202 四方複審修復窗口：`QuotaGateIsWiredToTheBurnPathTest` 新增回歸測試
多用了一次既有 fixture 慣用句式 `<Path>.replace(qg.quota_cache_path())`
（同檔既有測試已大量使用同一句式，未另立新形態）。
沿革已搬至 CrossPlatform_R151_Guard_Prose_Migration.md〈_DIRENT_UNGUARDED_DEBT 逐輪重釘〉節。
```

### §39 M5 注入矩陣：R85／ARCH-02 手抄清單與 AST 對帳不符的實測

原址：`tools/tests/test_platform_neutral_paths.py` `_injection_criteria()` docstring。

```text
🔴 R85／ARCH-02：這句話在 R85-P12 之後有一段時間是**假的**。當時 AST 對帳實測
「12 定義 / 8 接線」——`scan_foreign_exe_argv`（P12 同輪新增）與另外三道從未被接進來。
後果不是「少擋一點」而是**方向相反**：M5 注入矩陣量到的攔截率會低報，而低報會讓
下一輪去補一道已經存在的判準（同 R80 對「大小寫敏感度」那一格低報分子的判決）。
實測直呼 `scan_foreign_exe_argv` 對 b8／b11 兩題 HIT，而表上兩題都記著 False。
本輪把**全部 12 道**接齊；另三道對現行語料零命中（實測），接進來是為了讓上面那句
宣稱不再需要人記得去維護——分母由函式定義本身決定，不是由這張手抄清單決定。
```

### §40 `_repo_py_files()` 沿革：納入 untracked 的理由與 `_zzz_` 前綴排除（R70／DEF-200-274）

原址：`tools/tests/test_platform_utils_dedup.py` `_repo_py_files()` docstring。

```text
為何要納入 untracked：見檔頭②。`git ls-files` 的 tracked-only 語意讓「還沒
`git add` 的新檔」對本鎖完全不存在，而**新檔正是複製貼上最可能發生的地方**；
R69 的 `platform_caps.py` 全程 untracked，四輪四方複審＋多次全套實跑零訊號。
`-o --exclude-standard` 仍尊重 `.gitignore`，故原本靠 `.gitignore` 排除
`.venv/`／`__pycache__/`（實測 `AISDLC_SDD/` 下有 4,800+ 支這類 `.py`）的效果
一個都沒少——實測本 repo untracked-not-ignored 的 `.py` 現為 0 支，
即本次擴面對**耗時**同樣近乎零代價。

`_zzz_` 前綴排除（DEF-200-274 第六輪）：擴面納入 untracked 後，本函式會與
`tools/tests/` 內其他測試（`LoadBalancingRegressionTest`／
`ParallelShardStderrBackpressureRegressionTest` 等）動態建立又
`addCleanup` 刪除的合成暫存模組（`_zzz_*.py`）產生 TOCTOU 競態——本函式列出
時檔案還在，讀取時已被另一條 worker thread 的 cleanup 刪除，觸發
`FileNotFoundError`。這些合成檔從不是本鎖要驗的「真實原始碼」，先例見
`test_pre_push_dispatcher.py`／`test_ps_engine_ssot.py`（同一批第五輪修法）。
```

### §41 `_scan_repo_py_for()` 沿革：掃描面名實不符（R57 A5）、git ls-files 取捨與 R57 實測、讀不到檔案的紅燈

原址：`tools/tests/test_platform_utils_dedup.py` `_scan_repo_py_for()` docstring 三段。

```text
R57 修正（A5）：兩支掃描測試的 docstring 都自稱「全 repo 機械掃描」，實際
掃描面卻只有 `AutoClaude/` 與根層 `tools/` 兩棵樹——`AISDLC_SDD/`（含
`scripts/`、`conftest.py`、各版 `tools/fsm_runtime/`）與 `.claude/hooks/`
下的 `.py` 全部在外，第 9 份複製貼上落在那些位置時本鎖零訊號。名實不符的
掃描面本身就是誤導：複審者讀 docstring 會以為已全域覆蓋而不再追查。

改用 `git ls-files` 而非 `rglob`：`AISDLC_SDD/` 底下有數千個 venv/快取 `.py`
（實測 4,829 支），rglob 全掃既慢又得維護排除清單；追蹤檔天然排除這些，且與
同 repo 姊妹鎖（`test_windowsapps_guard_cross_consistency.py` 的 repo-wide
掃描）採同一政策。R57 實測：擴面後三個函式名的命中集合皆不變（仍只有
`tools/lib/platform_utils.py`），新增偽陽性 0，故擴面在**命中集合**上零代價
（R57 round 1 QA-R57-06 訂正：健壯性與耗時上並非零代價——實測 5,427 支
tracked `.py`、單次模組耗時約 2.7s，且 `git ls-files` 會列出「index 有、工作樹
沒有」的檔案）。

讀不到的檔案一律**紅燈**（SD-R57-04／QA-R57-06）：git 追蹤卻讀不到 ⇒ 本鎖
宣稱的「全 repo 掃描面」已縮小，而縮小掉的內容無從得知（sparse checkout 下
缺席的檔案在 repo 裡是有內容的，靜默跳過＝真 fail-open）。故收齊全部讀不到
的路徑後以 AssertionError 給出可診斷訊息，而非裸 FileNotFoundError traceback
（原行為），也不是 `except OSError: continue` 的靜默跳過。

R70：掃描面已由 tracked-only 擴為 tracked ∪ untracked-not-ignored
（見 `_repo_py_files()`）；上兩段的 `git ls-files` 敘述與耗時實測皆為當時原文，
刻意保留為沿革。
```

### §42 行內 stdio 複本棘輪：R75 訂正（兩個各自宣稱 SSOT 的家）

原址：`tools/tests/test_platform_utils_dedup.py` `# R74：島模型對「行內語句複本」結構性全盲` 區段註解第二段。

```text
🔴 **R75 訂正（本段原文自己就是那個病）**：上一行原本逐字寫「`tools/_stdio_utf8.py`
**已經是 SSOT**」。那句話在寫下的當時就是假的——同一份知識當時有**兩個各自宣稱是
SSOT 的家**：`tools/_stdio_utf8.py::reconfigure_stdio_utf8`（`.reconfigure()` 就地改、
import 期生效）與 `tools/lib/platform_utils.py::init_utf8_streams`（`TextIOWrapper`
換掉串流、只在 `__main__` 呼叫），實作／啟用時機／對測試替身的行為三者皆不同，而
本檔的兩把鎖（`:335` 的 def 唯一性、下方這個行內複本棘輪）**都只守自己那一支**。
把「其中一支是 SSOT」寫成註解，正是讓那個衝突躲過複審的原因（同 R73「訂正註記逐字
引述假話＝製造新假話」）。R75 已真正去重（唯一實作＝`tools/lib/platform_utils.py`，
`_stdio_utf8` 逐字委派同一個函式物件），並補上
`TestR75StdioUtf8HasOneImplementation`——**兩把鎖從此看得見彼此**。
```

### §43 行內 stdio 複本棘輪：診斷階段轉述數字不複現的逐項實測（R74）

原址：`tools/tests/test_platform_utils_dedup.py` R74 區段註解「誠實劃界」第二點。

```text
  · 診斷階段曾以「43 份行內複本 vs 19 個 SSOT 消費者」描述本筆。**本輪以下方判準
    實測不複現**：`sys.std{out,err}.reconfigure(` 形態為 9 處／8 檔，`import
    _stdio_utf8` 消費者 15 支（`PYTHONUTF8` 字樣另有 46 處／19 檔，那是環境變數
    設定、不是本 SSOT 的行內複本，兩者不可混為一談）。故本棘輪釘的是**本輪實測值**，
    不是任何轉述的數字——這正是本檔一貫的「不寫死轉述來的量」紀律。
```

### §44 pre-commit dispatcher 鎖：行尾閘為何併進本檔（R74／R78 棘輪語意訂正）

原址：`tools/tests/test_pre_commit_dispatcher_sigpipe.py` 模組 docstring「為何 (2) 併進本檔」段。

```text
🔴 為何 (2) 併進本檔而非另立新檔：`tools/tests/` 有一道護欄層 shrink-only 棘輪
（`DEF-101-561③`；R74 當時量的是檔數。🔴 R78 ARCH-03 訂正：R77 起接手者是
`test_adr_xplat001_c1c2_lock.py::TestGuardLayerRatchet` 的逐檔行數表，現行語意是
**淨行數不得上升**、不是「禁止新增檔案」）。本檔是最貼近的家——它已經備好「真 git repo ＋ 真 commit
觸發 dispatcher」這套沙盒（行尾閘唯一能被行為級驗證的方式就是真的 commit 一次），
新開一支等於把同一套 fixture 抄第二份，還會撞上那條裁決。
```

### §45 pre-push dispatcher 鎖：指名鎖檔必須存在的 WHY（R67 round 2，QA-R67-03）

原址：`tools/tests/test_pre_push_dispatcher.py` `# ── 指名鎖檔必須存在` 區段註解第一段。

```text
WHY：本檔 setUp 與 `tools/git-hooks/pre-push` 的註解同時把
`test_integration_gate_local_carrier.py` 指名為「路徑觸發抓不到的另兩種腐爛」的
守門者，而那支檔案**從未存在**（`ls` rc=1、全庫 `find` 零命中；真正的守門依
`DEF-101-561③` 併進了 `test_find_git_bash_parity.py` 的既有姊妹鎖）。
實害是治理面：那段註解正是 DEF-101-639 修法正當性的核心論證，指向不存在的容器＝讀者
現查時無法驗證；更糟的是下一輪若有人執行「檔案不存在 ⇒ 這層守門沒落地」的推論，會誤判
本輪修復不完整並重做一次。本 repo 對「指名不存在的容器」已有明文硬規則
（`docs/06_quality/CrossPlatform_Scan_Dimensions.md` 硬規則③ 第一點：禁止寫「記入某某
帳本」而該帳本不是真實檔案路徑），本筆是同一形態發生在程式碼註解上。
```

### §46 PS 5.1 相容鎖：既有防護都驗不到 5.1 的三項逐條說明（R56／R57 訂正）

原址：`tools/tests/test_ps51_compat.py` 模組 docstring「WHY」後半（既有防護缺口三點）。

```text
- `root-infra-ci.yml` 第 2 道的 `Parser::ParseFile` 跑在 `runs-on: ubuntu-latest`
  ＝PowerShell 7 Core 的 parser，結構上驗的是 7 的文法，不是 5.1 的。
- `windows-compat-ci.yml` 在 windows-latest 上的**預設**引擎是 `shell: pwsh`
  （＝PowerShell 7 Core），少數刻意例外：windows-smoke 有走 `shell: bash` 的
  dispatcher hooks 步驟，windows-nightly-full 有走 `shell: powershell`（＝原生
  5.1）的步驟實跑 bootstrap.ps1／dev_start.ps1／install_post_commit.ps1。
  （**R57 QA-R57-04 訂正**了本段原文的過期宣稱；該訂正史料逐字遷至
  `docs/06_quality/CrossPlatform_R89_Closure_Evidence.md` §A-1。此處刻意不寫死
  各引擎的步驟支數，逐 job 的 shell 分佈一律以 workflow 檔本身為準。）
- 其餘只有 `windows-compat-ci.yml` 檔頭 R5 段落的**人工宣稱**（當時列名七支
  「均未見 PS7-only 語法」），該宣稱立於 2026-07-14、13+ 輪未複驗，實測 active
  `.ps1` 已 21 支＝涵蓋率 7/21，且會隨新增檔案靜默過期。
```

### §47 `python -c` 百分號 shim 鎖：真實事故經過（DEF-101-503）

原址：`tools/tests/test_python_c_percent_shim.py` 模組 docstring「WHY（真實事故）」段。

```text
該檔 `$script:PyExe` 解析到的 `python`，在裝了 pyenv-win 的機器上是 **python.bat**
shim（不是 python.exe）。batch 會先對命令列做百分號展開，把 `%s` 這種未定義的
`%x` 序列直接吃掉，送到 Python 手上時 `'...%s...' % (...)` 已變成 `'...'(...)`
＝字串後面直接接括號 → `SyntaxWarning: 'str' object is not callable` +
`TypeError`，rc=1。

危害不是「少印一行摘要」而是**訊號污染**：chaos 測試本身 34 支全過
（pytest_rc=0 sweep_rc=0），卻因 parse_rc=1 讓整個 stage 判 fail、nightly
exit=1；隔天早上 `tools/dev_start.py` 的心跳哨兵便報「上一輪 nightly 有失敗」，
把使用者導去追一個不存在的迴歸，真失敗反而被淹沒在常亮紅燈裡。
```

### §48 量不到原因表：第二個成員 `http-429-floor` 為何不登記進 `_UNMEASURABLE_REASONS`（R100）

原址：`tools/tests/test_quota_policy.py` `_NOT_A_FAILURE` 上方 `#:` 註解。

```text
🔴 R100 新增第二個成員 `http-429-floor`：它與 `ok` 同族（都**帶著讀數**回來），只是
那份讀數是一個 pct 下界 100 的單軸**地板**（`quota_meter.rate_limited_reading()`）。
把它登記進 `_UNMEASURABLE_REASONS` 會是一句假話——那張表的每一項都會被 `m9_problems()`
造成 `axes == ()` 的合成態去掃，而 429 這條路**結構上不可能** `axes == ()`，於是
「量不到不得等於不設限」那兩條不變量會對一個不存在的形狀成立，分母虛胖一項。
它不是漏登記：本例外由 `test_context_budget_guard.py::
RateLimitIsAFloorNotAnUnknownTest::test_a_429_lands_on_halt_and_not_on_unmeasured`
承接（斷言同一個字面回來時 `reading is not None` 且落在 halt 側）⇒ 兩表互斥即可，
見下方 `test_the_exemptions_are_not_also_registered_as_unmeasurable`。
```

### §49 `run_with_floor` 平台閘測試：patch 目標由行程全域 `os.name` 改為 windows_skip_tags 的判定（R72／R82 SA B-1／R100）

原址：`tools/tests/test_run_root_unittests.py` `test_*` 內 skip 標籤合成樹的 patch 註解。

```text
R72：`untagged_windows_like_skips` 已隨 skip 標籤家族搬進
`tools/lib/windows_skip_tags.py`（見該檔頭），平台閘讀的是**該模組**的判定。
🔴 R82（SA B-1）：這裡原本 patch 的是 `windows_skip_tags.os` 的 `name` ＝
**行程全域**的 `os.name`。pytest 載具下 `AssertionRewritingHook` 會對每一支
新 import 的模組呼叫 `Path()`，patch 期間那必定拋 `PosixPath` 例外 ⇒ 下面
合成出來的樹 import 失敗、塌成 `_FailedTest`、收集數低於下限 ⇒ **兩次**
`run_with_floor` 都回 1：紅的那一半理由是錯的，綠的那一半永遠綠不了。
R100：真表自本輪起非空，隔離它避免合成樹被 stale 自檢誤判 rc=1。
```

### §50 零相依探針子行程環境：強制序列的緣由（DEF-200-274 第九輪 P0，遞迴熱點 823s→3813s）

原址：`tools/tests/test_run_root_unittests.py` `_zero_dep_child_env()` docstring。

```text
"""斷『平行』遞迴（與既有 `_ZERO_DEP_PROBE_ENV` 斷『skip 掃描』遞迴的精神一致，
但是兩件獨立的事，不合併成同一個旗標）。DEF-200-274 第九輪 P0：D1 把
`AUTOSDD_PARALLEL_TESTS` 未設的語意從「序列」改成「auto（真實樹＋workers>1
即平行）」後，本探針子行程對 `R._TESTS_DIR`（貨真價實的真樹）整套重跑一次時
（`floor`／`main` 模式）會被新語意捲入、疊加在外層已在跑的 fan-out 之上
（DEF-101-803 遞迴熱點史料：823s→3813s 且仍逾時）。不管外層 `AUTOSDD_
PARALLEL_TESTS` 是什麼值（未設／"1"／zshrc 殘留），探針子行程一律強制序列
——退回 D1 之前的「未設＝序列」基準，不被新語意捲入。
```

### §51 外部可執行檔前置宣告 SSOT：WHY 與 SSOT 放測試檔的取捨（R69 終審 SD）

原址：`tools/tests/test_run_root_unittests.py` `_EXTERNAL_TOOL_PREREQS` 上方註解。

```text
WHY（R69 終審 SD 實測；與 `run_root_unittests._THIRD_PARTY_PREREQS` 是同一個病的
第二種形狀）：那份清單守的是「import 得到嗎」，對「PATH 上有沒有這支執行檔」結構性
盲目。R69 把 `ruff check tools/` 接進 `tools/git-hooks/pre-push` 快層第 ④ 段（缺 ruff
＝fail-loud，刻意不軟跳過），而 `test_pre_push_dispatcher.py` 有 5 支測試在 tmp repo
內**真跑**該 dispatcher 並斷言 rc==0 ⇒ 本目錄自此隱性要求 PATH 上有 ruff。當時三支跑
runner 的 workflow 只有 root-infra-ci.yml 裝 ruff ⇒ **同一批 tools/tests 在三個平台有
兩種結果**，原本綠著的 macos-compat-ci 會被打紅（SD 單變因 A/B：PATH 上放假 ruff →
Ran 17 OK；唯一差別拿掉 ruff → FAILED〔failures=5〕）。

🔴 為何解法是「三支 workflow 都補裝」而不是「缺 ruff 就 skip」：快層那道 fail-loud 是
本輪刻意訂的政策，軟跳過會讓它退回「宣告有、執行者無」的原病（見 tools/ruff.toml
檔頭）。落差在**環境**不在 dispatcher。

🔴 為何 SSOT 放在測試檔而非 `run_root_unittests.py`（誠實劃界）：該檔受
`AutoClaude/tools/check_loc_budget.py` 的 SPECIAL_FILES **shrink-only 行數棘輪**管制
（門檻＝納管當下行數 754，只准往下改），本包實測往該檔加 69 行當場撞紅（`[special<=754]
823 > 754`）。代價明說：因此**沒有** runner 開場 fail-fast 那一層，缺工具時仍會先看到
dispatcher 那 5 支紅字；補償是下方 `ExternalToolPrereqDeclarationTest` 會在同一次執行
裡多紅一支並**點名真正的原因**。要買回 fail-fast 就得先把該檔壓到 754 行以下——那是
另一個包的工作，見交件回報的帳本請求。
```

### §52 parallel 例外安全測試：mock Popen 漏 `returncode` 的既存 fixture 缺口（第四輪複審）

原址：`tools/tests/test_run_root_unittests.py` `ParallelShardRunParallelExceptionSafetyTest` 內 mock Popen 類別註解。

```text
🔴 第四輪複審發現的既存 fixture 缺口（非本輪引入）：本 mock 原本漏了
`returncode`，`_worker_thread_loop()` 對成功 Popen 的分支一定會存取它
（`results.put((module, proc.returncode, ...))`）——先前的舊版
`run_parallel()` 只取 `thread_errors` 第一筆例外就 raise，恰好讓
mod.b 那個「刻意」的 OSError 蓋過這個「意外」的 AttributeError，兩者
長得一樣（都是「有例外被攔下」），此測試因此從未真的獨立驗證過
mod.a 分支能走到 `results.put()` 那一步。修復後的 `run_parallel()`
會把兩條 worker thread 的例外都排空印出，讓這個潛在缺口第一次現形。
```

### §53 `save_live_cache()` merge-prune 回歸鎖：震盪機制鏈與父鍵回填補強（DEF-200-363 第十五輪）

原址：`tools/tests/test_run_root_unittests.py` `ParallelTimingCacheSaveLiveCacheMergePruneTest` class docstring。

```text
回歸的震盪機制鏈（見該函式 docstring）：模組級觀測寫入活體快取 → 下一輪
該模組被自動細分成多個 `module.Class` 鍵觀測 → 若整檔覆寫，活體快取不再
有模組鍵 → `load_hints()` 對模組鍵退回種子檔（可能是舊、偏低的數字）→
`auto_class_level_candidates()` 拿到偏低數字判定「不再需要細分」→ 下一輪
又整模組派工、耗時暴增 → 下下一輪又被觀測成細分鍵……如此震盪。

後續補強（同一份 DEF-200-363 修復的殘餘缺口）：初版只做到「父鍵不被剪掉」，
但父鍵本輪未被直接觀測時只是**原樣保留**上一輪的舊值（`kept_previous`），
從此凍結、不再刷新——這個凍結值拿去跟每輪都在變動的 fair_share 比較，會在
門檻附近造成同一棵樹、同一個 worker 數兩次重跑跑出不同拆分決策。修法：
父鍵改為每輪由其子鍵**回填**（加總），持續追蹤真實現況（見
`save_live_cache()` docstring〈WHY 父鍵需要每輪回填〉）。
```

### §54 過期 advisory 比對合併活體快取回歸鎖：場景與假時鐘取捨（DEF-200-386）

原址：`tools/tests/test_run_root_unittests.py` `RunParallelStalenessAdvisoryReadsMergedLiveCacheTest` class docstring「場景」段。

```text
場景：這一輪只派工 `pkgNN.Fresh`（20 個 class 級鍵）；活體快取裡預先放著
`pkgNN.Old`——與這一輪同前綴、但不會被這一輪重新觀測到的舊 class 鍵
（`save_live_cache()` 的 `kept_previous` 語意會把它原樣留下）。種子檔內容＝
這一輪「應該」合併出來的完整圖像（parent rollup `pkgNN` ＋ `Old` 舊鍵 ＋
`Fresh` 新鍵），數值刻意分兩層（`Old` 恆 0.0、`Fresh`／`pkgNN` 隨 `i` 遞減）
——用真實 `run_parallel()`（fake `Popen` ＋ 依 `i` 遞減量餵入 `elapsed`：
以執行緒區域（`threading.local()`）假時鐘 offset 取代真 `time.sleep()`
——macOS CI 3 核負載下 10ms 階梯曾被排程抖動打亂，重疊率 36%／43%
＜50% 門檻而假紅）讓兩邊排序同向，即使 tie-break 邊界受執行緒完成順序
影響也不礙事——兩個各恰 15 選的子集合，最壞情況下重疊率仍 ≥ 14/16
（遠高於 50% 門檻）。
```

### §55 `merge_results()` skip census parity 鎖：為何手造 per-worker payload（DEF-200-274 第十輪 SA-01）

原址：`tools/tests/test_run_root_unittests.py` `ParallelMergeResultSkipCensusParityTest` class docstring「現場事實」段。

```text
現場事實（先確認才動工）：`_worker_main()`（parallel_shard.py 第236~240行）
對 `start_dir` 有 `assert start_dir == tests_dir`——本 worker 目前只為真
tools/tests 設計，無法用真 subprocess 對合成暫存樹跑 `run_parallel()`（會在
assert 處讓 worker 以 rc=1 崩潰，變成 `shard_crashed` 而非真實 skip 語意）。
退回手造 per-worker payload：對同一批合成測試各自真跑一次
`unittest.TextTestRunner`（模擬 worker 在子行程內的真跑），用與
`_worker_main` 完全同款的 `parallel_shard._entries()` 序列化，再交
`merge_results()` 彙總——資料形狀因此與真實平行路徑保真，只是把「子行程」
換成「同一行程內的第二次真跑」。
```

### §56 排程能力對照契約：背景（DEF-101-233 五輪未落地的治理縫隙）

原址：`tools/tests/test_schedule_capability_parity.py` 模組 docstring「背景」段。

```text
背景：DEF-101-233（R16 Architect 架構檢視）建議補「排程能力對照契約」機械測試，
斷言 mac 支援子命令集合 ⊆ Windows 支援子命令集合；`tools/install_windows_nightly.ps1`
自 R19 建立後，五輪掃描/複審（R19~R22）皆確認此測試從未真正落地——
`tools/check_script_parity.py` 把這對腳本登記為 `_EXEMPT_PAIRS`（放棄字面比對），
註解暗示「行為對等由 test_install_windows_nightly.py 守門」，但該檔實際只驗證
Windows 腳本自身結構，從未跨檔比對 mac 側能力集合，形成「兩邊都以為對方在管」
的治理縫隙（R22 Architect 一審發現）。
```

### §57 排程能力對照契約：R60 DEF-101-539（pytest 風格被 discover 整檔零收集）

原址：`tools/tests/test_schedule_capability_parity.py` 模組 docstring 第五段。

```text
🔴 R60 DEF-101-539（Scan-C C-01）：本檔原以 **pytest 模組層函式風格**撰寫，而四道
執行 `tools/tests` 的閘門（`tools/git-hooks/pre-push` root-infra leg、
`.github/workflows/root-infra-ci.yml`、`windows-compat-ci.yml`、`macos-compat-ci.yml`）
全部走 `tools/run_root_unittests.py` 的 `unittest discover`——它只收 `TestCase` 子類，
模組層 `def test_*` **一支都不收**。實測 `python -m unittest tools.tests.
test_schedule_capability_parity` → `Ran 0 tests ... OK`，同一檔 pytest → 6 passed。
落地於 R22（0053f2a，2026-07-22），至 R59 之間帶「相容性 R」的收輪 commit 有 **34 支**，
這道鎖從未在任何閘門裡跑過一次。改寫為 `TestCase` 類別風格即真正被收集。
根因不只本檔一支寫錯——**「單檔貢獻 0 支測試」在現行守門下零訊號**（`MIN_TESTS`
下限只抓大規模消失；R60 實測下限值 661 與實況 661 相等＝缺席已被固化進下限），
故同時補 `TestUnittestDiscoverConformance` 這道 repo-wide 前瞻鎖，見該類別 docstring。
```

### §58 排程能力對照契約：`_SCAN_FLOOR` 取消第二個家的沿革（R85／訴求 2）

原址：`tools/tests/test_schedule_capability_parity.py` `_SCAN_FLOOR` 上方 `#:` 註解。

```text
🔴 R85／訴求 2：這裡原本自己寫一份 `_SCAN_FLOOR = <數字>`，並附著逐輪重釘的敘事；
而該常數的註記自己就寫著「兩者量的是**同一棵樹的同一件事**，兩個下限各自漂移才是
真正的問題形態」，同時承認「兩處必須相等這件事沒有任何機械物在守」（列入交棒）。
那道缺口本輪以**取消第二個家**收掉：兩處不可能不相等，因為只剩一處。
原先「刻意不 import 對方、避免兩道獨立的鎖共用失效點」的顧慮**不成立**——共用的是
一個純資料常數，不是判準；兩支測試的判準（本檔的兩向斷言、對方的三向斷言）各自獨立，
而讓兩個下限各自漂移的代價已經在 R78／R82／R83 連三輪的手動同步裡付過。
重釘方式不變：由下方 `test_scan_surface_is_not_silently_empty` 的第二向斷言逐字指示，
改在 SSOT 那一處填值（本檔不再需要跟著改）。
```

### §59 排程能力對照契約：R83 本地基底鏈判準（共用夾具子類別假紅）

原址：`tools/tests/test_schedule_capability_parity.py` `TestUnittestDiscoverConformance` 內 R83 註解。

```text
🔴 R83：先把**同一份檔案內**「基底鏈最終抵達 TestCase」的類別名收成一個
集合，再拿它當第二種合格基底。
立案是實測到的假陽性：`test_block_destructive_git_r83.py` 有一個共用夾具
`class _ForeignTreeCase(unittest.TestCase)`，其三個子類別
（`class TestStashIsBlockedInEveryTree(_ForeignTreeCase)` 等）被本鎖判為
「未繼承 TestCase」——而 unittest discover **確實收得到它們**（當回合實測那三類
貢獻 16 支真的在跑的測試）。⇒ 舊判準只比基底的**字面**，解析不了本地基底鏈。
為何非修不可、不能叫人把階層攤平：本鎖的立論是「unittest 不收 ⇒ 覆蓋靜默消失」，
而這裡覆蓋沒有消失 ⇒ 它報的不是那件事。逼人為了過鎖去複製共用夾具，等於用假紅
換來三份手抄夾具，正是本 repo 反覆判過的「同一份知識住多個家」。
🔴 刻意只解析**一份檔案內**的基底鏈（不跨檔）：跨檔要 import 解析，那會讓本鎖
從純 AST 掃描變成半個 import 系統，失效模式遠比它擋的東西更難看見。跨檔繼承的
測試基底在本 repo 目前是 0 個站點；真的出現時它會以假紅的形態被看見（fail-loud
方向），而不是靜默放行。
```

### §60 腳本掃描面 SSOT 鎖：R79 ARCH 取代 866 行對抗式正則錨的舊形狀與新形狀

原址：`tools/tests/test_script_scan_surface_ssot.py` `TestNonPythonSitesCallTheSsot` 上方註解。

```text
🔴 R79 ARCH：本檔第 2 件事（`TestNonPythonSitesCallTheSsot`）取代了 866 行機械。

舊形狀：`root-infra-ci.yml` 第 2 道與 `tools/windows_smoke_local.ps1` [1/9] 各自
用 `Get-ChildItem -Recurse -Filter *.ps1` 列舉同一份掃描面（＝SSOT 的第 2、第 3 份
複本）。因為兩者是 YAML／PowerShell、無法 import 本 SSOT，repo 改為「偵測三份是否
同步」——`tools/tests/_ci_scan_anchors.py`（154 行）三條對抗式正則錨 ＋
`tools/tests/test_ci_scan_anchors.py`（712 行，8 class／26 支）鎖那三條錨的鑑別力。
該路線已翻車兩次（R56 的 `-Path` 具名參數假設、R57 的大小寫敏感假設），且錨自己的
docstring 逐條寫著三種**已實測抓不到**的逃逸形態（`[System.IO.Directory]::GetFiles()`／
`Get-Item`／`Resolve-Path`）——軍備競賽結構上追不完。

新形狀：兩個非 Python 站點改為**呼叫**本 SSOT 的 `--list` CLI 取得掃描面。「三份
不同步」自此在結構上不可能發生（只剩一份），那 866 行連同三種已知逃逸一起退場。
```

### §61 腳本掃描面 SSOT 鎖：R79 四方複審補進 `--with-latest` 的實測

原址：`tools/tests/test_script_scan_surface_ssot.py` `_REQUIRED_SSOT_CALL` 上方 `#:` 註解第二段。

```text
🔴 R79 四方複審（ARCH blocking）補進 `--with-latest`：本表原先只有三格，而少一個
`--with-latest` 會讓 AISDLC_SDD LATEST 版整棵樹逸出掃描面。複審實測：掃描面由 20 支
縮成 16 支、LATEST 那一棵的 per-tree 下限**完全沒有被檢查**，而 CLI 回 **rc=0**、
本鎖兩支測試**全綠**。也就是說：本輪拿來取代 866 行對抗式錨的那句立論（「掃描面
靜默縮小必須 rc=1、複本不同步結構上不可能發生」）被這道替代鎖自己重新開了一個縫，
而 LATEST 樹正是 Copy-on-Evolve 每升一版就換路徑、最容易被人順手拿掉的那一格。
同輪落在 pre-push 的姊妹鎖（`tools/tests/test_pre_push_dispatcher.py`）對同一件事有守
——同一輪、同一件事、兩道鎖鑑別力不一致，弱的那道守的正是本次異動的兩個主站點。
```

### §62 skip 天花板共同變更鎖：立案（漏補第四層 M6 落款）與粒度由檔案級改剖面鍵值級（R115／R119）

原址：`tools/tests/test_skip_ceiling_ratchet_direction.py` `_CO_CHANGE_SOURCE_PATHS` 上方 `#:` 註解前兩段。

```text
WHY：R115 落地 `_RUNTIME_SKIP_CEILING`／`_RUNTIME_SKIP_CEILING_MAX`／本檔 round-label-ok
`_FROZEN_CEILING_MAX` 三張表的平台互補上修（commit `7f8c96a`）時漏補第四層
M6 落款 `docs/06_quality/skip_id_ledger.json`——直到下一個 commit `5d5dd37`
才補上。四層座標、已否決形態（層與層互相派生／「① 總和 vs ④ 列表長度」靜態
互查——後者判準是 `total_got > total_cap` 的上限語意，漏補只會讓 ④ 更小，對
目標痛點恆綠）逐項見 `docs/04_planning/R118_HANDOFF.md` 的 P1-6 節，此處不重複。round-label-ok

🔴 R119 修復包 round-label-ok：判準粒度由**檔案級**改為**剖面鍵值級**。原版寫成「①②③任一
檔案出現在變更清單即紅」，落地當回合就抓到了自己——本鎖自身的程式碼就住在
`_CO_CHANGE_SOURCE_PATHS` 其中一個檔案裡，commit `a1fbbba`（新增本節程式碼）
只是在幫這道鎖本身加程式碼，`_FROZEN_CEILING_MAX` 一個字元都沒有動過，檔案級
判準卻照樣要求同動 ④——往後任何對這兩個檔案的無關改動（加註解、加測試、修
typo）都會被誤擋，而「擋到讓人無法工作的守衛會被整個關掉，比沒有守衛更糟」
正是 `block_destructive_git.py` 檔頭自己講的道理，不該只在那一支鎖上算數。
```

### §63 示範指令單平台鎖：指引措辭加詞（`請設定`／`使用`）的逐筆實測（R83／W2-B）

原址：`tools/tests/test_skip_discoverability_r83.py` `_GUIDANCE_WORDS` 正則內註解。

```text
`請設定` 是本輪**實測補上**的：`AutoClaude/alembic/env.py` 缺 DSN 時的 fail-loud
訊息逐字寫「請設定環境變數 …／export …」，是使用者撞牆時唯一的指路，卻不含上面
任何一個詞 ⇒ 整支從掃描面漏掉。加詞的判準是「有沒有實際漏掉一個真站點」，不是憑想像加。

🔴 `使用` 是**獨立驗證階段**依同一條判準補上的（R83／W2-B 複驗）：本檔落地當回合，
把過濾器整個拿掉重掃全掃描面，全庫只多出 **4** 筆命中，逐筆看過之後——
  · 2 筆是**真站點**，且與本包已修的那一族逐字同形（`AutoClaude/scripts/
    migrate_file_to_pg.py` 的「使用：」與 `AutoClaude/tools/probe_minimax_embedding.py`
    的「使用方式：」，兩者都只給 `export …`，Windows 讀者無路可走）；
  · 2 筆是假紅（`test_embedder_contract.py` 在**描述**「開發者 shell export … 時本測試
    偽 fail」這個情境、`test_run_local_nightly_static.py` 拿 `$env:…` 字面去 index
    ps1 內容），兩者都**不含**「使用」二字。
⇒ 加 `使用` 這一個詞恰好收下那 2 筆真站點、一筆假紅都不帶進來（實測差集驗證過）。
這正是本檔自己寫的判準：**加詞要靠「實際漏掉一個真站點」，不是靠想像**；而只做合成
自證不會發現它——過濾器是**必要條件**，漏掉的東西結構上不會出現在任何一次綠燈裡。
```

### §64 subprocess 編碼鎖：`tools` 樹檔數下限逐輪重釘沿革（77→92→110→131→156→186）

原址：`tools/tests/test_subprocess_encoding_hygiene.py` `_tree_floors()` 內 `tools` 樹下限上方的逐輪重釘註解。

```text
🔴 R80 收尾單人窗口重釘 77 → 92（**方向是收緊**：下限拉高＝要求更大的掃描面）。
觸發＝本輪三支護欄層檔的判準本體下沉 `tools/lib/`（DEF-101-957／958），`tools` 樹
由 95 支長到 97 支，而 77 這個下限只還守得住 79% 的掃描面 ⇒ `tree_count_verdict()`
的腐化上界當場紅並直接給出該填的數字（92 ＝ 97 × 0.95），本列照填、不做加減推算。
🔴 R83 收輪單人窗口重釘 92 → 110（**方向是收緊**，同上一段語意）。觸發＝本輪
並行包在 `tools` 樹下新增四支檔（`tools/lib/schedule_backend.py` ＋ 三支回歸鎖
`tools/tests/test_block_destructive_git_r83.py`／`test_mac_endurance_r83.py`／
`test_skip_discoverability_r83.py`），該樹由 112 支長到 116 支，92 這個下限只
還守得住 79% 的掃描面 ⇒ `tree_count_verdict()` 的腐化上界（115）當場紅並直接
給出該填的數字（110 ＝ 116 × 0.95），本列照填、不做加減推算。
🔴 R97 追加當輪重釘 110 → 131（**方向是收緊**，同上一段語意）。觸發＝本輪  round-label-ok
新增 `tools/lib/worktree_paths.py`／`tools/lib/ledger_staleness.py`／
`tools/lib/failure_log_rotation.py` 三支模組，該樹由 130 支長到 138 支，
110 這個下限只還守得住 80% 的掃描面 ⇒ `tree_count_verdict()` 的腐化上界
（137）當場紅並直接給出該填的數字（131 ＝ 138 × 0.95），本列照填、不做加減推算。
🔴 DEF-200-274 落地當輪重釘 131 → 156（**方向是收緊**，同上一段語意）。觸發＝
本輪新增 `tools/lib/parallel_shard.py`，該樹由 163 支長到 164 支，131 這個下限
只還守得住 80% 的掃描面 ⇒ `tree_count_verdict()` 的腐化上界（163）當場紅並直接
給出該填的數字（156 ＝ 164 × 0.95），本列照填、不做加減推算。
🔴 2026-09-27 重釘 156 → 186（收緊）：新增 test_recovery_hint_passes_ps_lint.py 後
掃描檔數 196 > 腐化上界 195，判準逐字給出該填的數字（186 ＝ 196 × 0.95），照填。
```

### §65 Windows 禁用檔名交叉一致性鎖：R57 訂正（檔頭「三處」與檔身「四處」矛盾）

原址：`tools/tests/test_windows_forbidden_filename_parity.py` 模組 docstring 第三段。

```text
**R57 訂正（DEF-101-478／round 2 SA-R57R2-04）**：本段原文寫「三處」並只列前三處，
而同一輪的 R57 修復已把第 4 處（`component_sanitizer.py`）納入同一缺陷的修復範圍、
且在本檔新增了 `TestCrossSubprojectSampleParity` 跨子專案樣本鎖——**檔頭與檔身當場
矛盾**。這與本輪判為 P2 的 `windows-compat-ci.yml` 檔頭失實（DEF-101-486）是同一
缺陷類別（「宣稱與實況不符」），由 round 2 SA 抓出，一併訂正。第 4 處的行為鎖因
子專案邊界不可跨界 import 而置於
`AISDLC_SDD/scripts/tests/test_component_sanitizer_reserved_trailing_space.py`；
本檔只以 AST 讀檔比對其**樣本清單**（實作可以四份，樣本沒有理由分歧）。
```

### §66 Windows 禁用檔名鎖：repo-wide 前瞻枚舉鎖的 WHY 與三段式邊界宣稱（R59／R82 訂正）

原址：`tools/tests/test_windows_forbidden_filename_parity.py` `# repo-wide 前瞻枚舉鎖` 區段註解（WHY 前瞻性／等值而非下限／不照抄姊妹檔／邊界宣稱）。

```text
WHY 前瞻性：以上斷言全是**具名枚舉**（逐一 import 已知 4 份再兩兩比對），只驗白名單內
彼此一致，對「有人新增第 5 份較弱的獨立重寫」零訊號。而「新站點」正是本家族真實的復發
形狀：DEF-101-219／295／343／346／349／384／390／442／478（**R59 QA 複審逐筆撈帳本原文後訂正本句原先的過度宣稱**：這 9 筆**並非全是「新增獨立重寫」**——`478` 實為**白名單內四份實作的一致行為漂移**（保留名+尾隨空白+副檔名形態四處一起逃逸），`384`／`390`／`442` 則是**新的「漏淨化呼叫點」**，那類檔案的原始碼**根本不含**保留名清單或禁用字元集合字面值，**本鎖的兩個錨結構上看不到它們**。本鎖只覆蓋「新增第 N+1 份**獨立重寫**」這一類；漏淨化呼叫點需要 AST 前瞻掃描〔`442` 原文已明講此機制〕，本輪只把 AST 掃描器當一次性前提查核用過、未機械化，見下方【已實測不涵蓋】)。此前本句原寫「共 9 筆全是新站點，無一筆是
白名單內漂移。`docs/06_quality/CrossPlatform_Scan_Dimensions.md` 因此把「parity 鎖須確實
有前瞻性（抓得到第 N+1 份）」列為必要重複家族的常設要求（R43 曾為此翻修一次）。本節補上
該常設要求——動工時實測**零違規**，故非修現存 bug。

WHY 等值而非下限：下限只在「多一份」時說話，對「某道淨化閘被刪掉」完全沉默，且下限自身
會腐化（`run_root_unittests.MIN_TESTS` 連 11 輪沒人重釘的判例）。等值一次拿到兩個方向：
多一份＝可能有未經審的第 5 份；少一份＝某道閘消失了（stale 自檢）。等值另外免費得到
fail-open 防護——pathspec／排除清單被改壞而掃到 0 份時 hits=[] ≠ 註冊表必然翻紅，故刻意
**不設** `_MIN_SCANNED` 這類額外下限測試。

WHY 不照抄姊妹檔：`test_windowsapps_guard_cross_consistency.py` 同款掃描段 868 行、跨
R40→R57 翻修約 6 輪、至今掛一筆永久 open 的 P3，體積幾乎全花在「排除註解／字串內的假命中」
（三語言剝註解、heredoc、引號配對…），而 R46 已證明那是無底洞（繞過從整行註釋→no-op
前綴→heredoc 逐層復發）。本節刻意反向取捨：錨保持**粗粒度、不剝註解**。代價是註解提到
裝置名清單也會命中（過度觸發）——但過度觸發是 fail-loud（有人得看一眼並登記），漏報才是
fail-open。代價的**處理**方式（不只承認，見上方 R57「明文承認代價 ≠ 處理了代價」判例）＝
註冊表每筆必帶「角色」註記，逼登記者當場分診「是第 5 份實作，還是只是提及」。

邊界宣稱（三段式，見 CrossPlatform_Scan_Dimensions.md §「邊界宣稱必須實測」）：
  【已實測涵蓋】① 4 份權威實作全數命中；② 第 5 份實作的三語言形態皆命中——Python
    `set()`／`frozenset()`／`re.compile(r"^(CON|PRN|…)$")`、bash case glob（`*'<'*|*'>'*|…`
    與 `CON|PRN|AUX|NUL|COM[0-9]`）、PowerShell `@('CON','PRN',…)` 與 `'<>:"|?*'`；
    ③ 大小寫不敏感（`('con','prn','aux','nul')` 命中）；④ 無副檔名的 `tools/git-hooks/
    pre-commit` 在候選面內；⑤ `git ls-files` rc≠0 → AssertionError；⑥ 掃描面塌陷為 0 份
    → 等值斷言翻紅。
  【已實測不涵蓋】① 測試檔內的第 5 份實作（`_is_ntfs_test_file` 排除全部 `/tests/` 與
    `test_*.py`；測試檔出現清單是「對 SSOT 做斷言」，沿用姊妹檔 `_is_test_py` 同款判準）；
    ② 凍結版 v0.01~v0.29（Copy-on-Evolve 不回改）——實測當前凍結版內**零**錨命中，故該
    分支改以等價路徑實測：把 LATEST 傳成不存在的版本號後，v0.30 整棵樹 105 份候選（含真實
    錨命中的生產檔 `counterfactual_replay.py`）全數掉出候選面；③（R82 訂正，`DEF-101-752`：
    原「尚未 `git add` 的新檔——ls-files 固有性質」已改列入【已實測涵蓋】——`_ntfs_scan_candidates`
    現以 `-o --exclude-standard` 併掃 untracked-not-ignored，未 add 的新檔不再是盲區）；
    ④ 三種副檔名與三處 hook 目錄之外的檔案（`*.md`／`*.yml` 刻意不
    納入：帳本與文件遍地提及——實測 tracked `*.md`/`*.yml` 中錨命中 6 份，納入只製造偽陽性）。
    ⑤（R59 SD-R59-02 補，實測）**跨行排版與非正典順序的第 5 份實作**：兩錨都要求
    字面依序出現且間隙 ≤5 字元，故 PEP8 4 空白縮排的「一名一行」寫法必逃（間隙 8>5）、
    字母序 `{"AUX","CON","NUL","PRN"}` 必逃、Windows 檔案總管本身的字元順序
    `[\/:*?"<>|]` 必逃、每項帶行內註解必逃、PowerShell 多行陣列必逃。**現實意義不低**：
    真的第 5 份若含 COM1~9／LPT1~9，單行會超過 ruff line-length=100，幾乎必然寫成多行。
    ⑥（R59 QA-R59-01 補，實測）**新的「漏淨化呼叫點」**（DEF-101-384／390／442 的形狀）：
    那類檔案的原始碼根本不含任何錨字面值，兩錨結構上看不到；`442` 帳本原文已明講所需
    機制是 AST 前瞻掃描，本輪只把 AST 掃描器當一次性前提查核用過、**未機械化**。
  【未窮舉】**本清單並非窮舉**，只是本輪真正跑過的項目，不代表已列出全部繞過路徑：任何
    「錨字面值被改寫但語意等價」的寫法（`CON` 拆成 `"C" + "ON"`、`chr()` 組出字元集合、
    清單搬進 JSON/YAML 資料檔後讀取…）都在偵測範圍外。本段**不主張**殘餘風險只有某幾項。
```

### §67 Windows 禁用檔名鎖：R69 兩筆「AISDLC_SDD 側跨樹 import autoclaude」的收容背景

原址：`tools/tests/test_windows_forbidden_filename_parity.py` `# R69：兩筆…收容處` 區段註解。

```text
背景（DEF-101-6xx，`aisdlc-sdd-ci` run 30720156045 由綠轉紅）：R68 在
`AISDLC_SDD/scripts/tests/test_ntfs_length_gate.py` 與
`AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/tests/
 test_state_component_sanitizer_parity.py` 兩處直接 `from autoclaude...` import
AutoClaude 生產套件。AISDLC_SDD 的 CI 相依只鎖 `AISDLC_SDD_v0.01/
requirements-ci.txt`（pyyaml + pytest），而 `autoclaude.utils.__init__` 會連帶
拉進 pydantic ⇒ 前者在 CI 上硬 fail、後者以 `try/except ImportError` 收掉而**8 支
測試在 CI 上永遠 skip**（乾淨 venv 實測 `8 skipped`——正是 R68 抓過的「靜默不跑」
病，本機因裝了 AutoClaude 而兩者都測不出來）。

為何收容在**本檔**而非各自原地修：本檔就是本 repo 既定的「跨子專案一致性鎖歸屬根層
整合層」載體（見檔頭四處實作說明與 TestCrossSubprojectSampleParity），且本檔已合法
`from autoclaude.utils import logger`——根層 root-infra-ci 依
`tools/run_root_unittests.py::_THIRD_PARTY_PREREQS` 安裝第三方相依，pydantic 恆在。
搬過來之後：斷言一條沒少、且從「CI 上永遠 skip」變成「CI 上真的跑」。
復發防護＝`AISDLC_SDD/scripts/tests/test_cross_subproject_import_isolation.py`
的靜態掃描（禁止兩子專案互相 import）。
```

### §68 Windows nightly 錨點鎖：補在本檔而非 smoke 步驟的取捨與註解剝除沿革（R57）

原址：`tools/tests/test_windows_nightly_anchor_parity.py` 模組 docstring 後半（放置取捨三點、strip_ps_comments 收斂沿革）。

```text
**為何補在這裡而不是補一步 [10/10] 進 `windows_smoke_local.ps1`**：
  1. macOS [7/7] 自述「唯讀 grep 工作樹、平台無關」——它做的事根本不需要 pwsh，
     放在本機 smoke 只是歷史選擇（且 SA-R15-REV-6 已記載該組錨點刻意只入本地
     smoke、無 CI 對應，屬本地專屬防線）。
  2. 補成 Python unittest 者，四道守門（pre-push root-infra leg、root-infra-ci
     step 8、windows/macos smoke）**全部**都會跑到，覆蓋面嚴格大於只補進
     Windows 本機 smoke（後者只有真 Windows 機器上手動跑才生效——而本輪主題正是
     「Windows 專屬守門長期沒在 Windows 上跑過」，見 DEF-101-348）。
  3. 補進 `.ps1` 需連動 `$MinPass` 下限與 `test_smoke_ci_sync.py` 的步驟語意鎖，
     且在 macOS 上無法真跑驗證，收益/風險比不划算。

錨點只認**功能碼**（剝除 `<# … #>` 區塊註解、整行 `#` 註解與**尾隨行內註解**），
比照 macOS 側 QA-R15-REV-1 訂正：註解裡留著舊字樣會讓錨點假陽性。剝除範圍與
已知邊界以 `tools/tests/_platform_helpers.strip_ps_comments` 的 docstring 為準
（R57 QA-R57-03：初版漏剝尾隨行內註解，真刪 `-WakeToRun` 只要在註解留字樣即可讓
6 支全綠）。該函式與其鑑別力測試已於 R57 round 2（SA-R57R2-03）從本檔與
`test_find_git_bash_parity.py` 的兩份逐字複本收斂進 `_platform_helpers.py`，
一致性由 `test_find_git_bash_parity.py::TestPsCommentStripperSsotCallsiteLock`
機械守護（本檔不得再自帶同名定義）。
```

### §69 WindowsApps bash guard：`_CALLER_FILES` R56 補登記三支呼叫端與 LATEST 動態解析訂正

原址：`tools/tests/test_windowsapps_guard_bash_parity.py` `_CALLER_FILES` 內 R56 註解。

```text
R56 新增：三支「早已收斂、只是從未登記」的呼叫端（實測 grep 全庫命中 15 支、
本清單只有 12 支）。未登記的代價＝不受 `test_all_known_callers_source_shared_guard`
與 `test_no_raw_unguarded_python_check_remains` 兩道白名單斷言保護，只剩
repo-wide 前瞻掃描這層（該層對「已收斂→退化為裸判斷」有鑑別力，但對本檔
docstring 記載的兩種偽裝手法失明）。補登記不需改任何 shell 程式碼。
後兩筆一律以 `_LATEST_SDD_ROOT`（sdd_version.py SSOT 動態解析）組出，不可
寫死版本目錄名——R56 訂正：初版寫死 `AISDLC_SDD_v0.30`，與
`test_caller_files_matches_repo_wide_scan` 實掃側的動態解析結構性不對稱，
下一次 Copy-on-Evolve 建 v0.31 時 v0.30 淪為凍結版被實掃排除 →
`declared - actual` 出現這兩筆而打紅 CI，且 LATEST 新版的同名呼叫端反而
脫離三道白名單斷言保護。
```

### §70 WindowsApps bash guard：`_EXEMPT_SH_FILES` 豁免理由須自足的告示沿革（R43 二審／R56）

原址：`tools/tests/test_windowsapps_guard_bash_parity.py` `_EXEMPT_SH_FILES` 上方註解。

```text
R43 二審 Architect 一審複查揪出：TestBashCallersEnrollment 原本只驗證固定
白名單（_CALLER_FILES），不是真正的 repo-wide 前瞻鎖——同一類「防增生鎖只
蓋到已知案例」缺陷（R41 對 _sanitize_component 呼叫點也犯過一次）。改為對
git-tracked 全部 `*.sh` 做前瞻掃描；下列為明確判斷「WindowsApps 空殼排除
guard 不適用」而豁免的檔案，皆附理由，供未來覆核：
R56 修正（SA／SD 各自獨立回報同一根因）：本集合的豁免理由一律須**自足**證明
「該腳本不存在 Windows 執行情境」。禁止以「同上一筆」或「某平台 PATH 上不會有
WindowsApps」作為唯一依據——後者已於 R55 被判定論證方向錯誤（見下方
`_CALLER_FILES` 內 macos_smoke_local.sh 那一筆的 R55 註解：只證明「本平台 PATH
乾淨」不足以豁免，必須另證「本腳本無 Windows 執行情境」），該筆亦因此被移出本
集合。此告示存在的理由：同一錯誤論證已被複製兩次。
```

### §71 WindowsApps bash guard：`run_mutmut_in_docker.sh` 豁免的論證沿革（R44 新增／R56 訂正）

原址：`tools/tests/test_windowsapps_guard_bash_parity.py` `_EXEMPT_SH_FILES` 內 `run_mutmut_in_docker.sh` 註解。

```text
R44 Architect 深度架構評估新增：本檔docstring 第 2 行明文「由
tools/run_local_nightly.ps1 透過 `docker run python:3.11-slim bash
/workspace/tools/run_mutmut_in_docker.sh` 呼叫」——結構性只在 Linux
container 內執行（官方 python:3.11-slim image 為 base，python3 保證存在於
該映像檔），Windows Store App Execution Alias 空殼是 Windows 原生 PATH
專屬機制，Linux container 內不可能出現；且本腳本無任何 Windows 直接執行
情境——唯一呼叫端是 run_local_nightly.ps1 的 `docker run`，宿主端只負責啟
容器、腳本本體始終在容器內跑。
（R56 訂正：原文結尾援引「同 macos_smoke_local.sh／run_local_nightly.sh 的
『非 Windows 執行環境』豁免精神」，但 macos_smoke_local.sh 已於 R55 因該論證
方向錯誤被移出本集合、成為懸空且已被否決的先例引用。改為上述自足論證：
前半證「容器內 PATH 不可能有 WindowsApps」，後半證「無 Windows 執行情境」，
後者才是本集合的真正判準。）
```

### §72 WindowsApps bash guard：`_tracked_non_sh_shell_scripts()` 的存在理由（R67 B4 實測）

原址：`tools/tests/test_windowsapps_guard_bash_parity.py` `_tracked_non_sh_shell_scripts()` docstring 第二段。

```text
🔴 R67 B4（本函式的存在理由，取代原本的硬編目錄名冊）：git hook 依慣例沒有
副檔名，`_tracked_sh_files()`（`git ls-files -- "*.sh"`）天生掃不到——那是
DEF-101-381 的根因。R46 補的第一版用 `git ls-files -- tools/git-hooks/*
AutoClaude/tools/git-hooks/* AISDLC_SDD/.githooks/*` 三個**寫死的目錄**補洞，
於是掃描面本身變成一份人工名冊：本 monorepo 的 hooks 目錄數已從 1 長到 3，
第 4 個（新子專案／`.husky/`／Copy-on-Evolve 新版樹自帶 hooks）是可預期的
演進，而屆時在該目錄放一支裸 `command -v python` 的 hook，**全部 29 支測試
仍全綠、零訊號**（R67 實測：連根層 1139 支 unittest 也全數逃過）——正是
R60 對 `tools/_script_scan_surface.py` 治過的「名冊沒有完整性鎖」同一個病，
只是換了一條腿。
```

### §73 WindowsApps bash guard：R80 S5-07 刪除四支路徑段判準測試的逐案對照表

原址：`tools/tests/test_windowsapps_guard_bash_parity.py` `test_missing_candidate_rejected` docstring。

```text
· 「真直譯器路徑」`C:\\Python311\\python.exe`（expected_stub=False）承接「真候選接受」；
· 反斜線／正斜線／混用分隔符／MSYS 掛載路徑共 6 列（expected_stub=True）承接
  「`WindowsApps` 空殼拒絕」，且多守住本類**從未測過**的分隔符變體；
· 「大小寫變體」`…\\WINDOWSAPPS\\python.exe` 承接大小寫那支；
· 「誘餌：子字串非完整段」`C:\\Users\\me\\MyWindowsAppsBackup\\python.exe` 承接誘餌
  那支，樣本連目錄名都逐字相同。
```

### §74 WindowsApps guard 收斂鎖：背景（三份內嵌複本、復發四次、R37 抽出共用函式）

原址：`tools/tests/test_windowsapps_guard_cross_consistency.py` 模組 docstring「背景」兩段。

```text
背景：同一條規則（排除 WindowsApps 底下的 python.exe/python3.exe 空殼別名，
未真裝 Python 時 `Get-Command python` 仍會找到它，執行只會跳出 Microsoft Store
提示）過去在 `tools/bootstrap.ps1`（2 處）與 `tools/dev_start.ps1`（1 處）逐字
內嵌了三份獨立複製，互不相通，導致同一缺陷類別連續復發四次（DEF-101-273／
279／300／303）——其中 DEF-101-303（`$PyCand`/`$Py3Cand` 變數與 `Get-Command`
命令名稱錯配的手誤風險）正是「內嵌而非呼叫共用函式」才可能發生的錯配類型。

R37 抽出 `tools/lib/WindowsAppsGuard.ps1::Test-IsRealPython` 共用函式（比照
`tools/lib/Find-GitBash.ps1` 既有先例），三處呼叫端改為 dot-source 後呼叫該
函式，取代原本各自內嵌的判斷式。三份內嵌複製彼此語意一致的問題已隨之消失
（只剩 1 份實作），本檔的舊靜態 regex/文字交叉比對手法（鎖「三份複製彼此一致」）
不再有意義，重構為：
```

### §75 WindowsApps guard：④ repo-wide 前瞻防增生鎖的背景（R40）

原址：`tools/tests/test_windowsapps_guard_cross_consistency.py` `# ④ repo-wide 前瞻防增生鎖` 區段註解「背景」段。

```text
背景：本檔頂部 docstring 記載的復發模式（DEF-101-273/279/300/303）過去每次
都是「內嵌重寫」被人工掃描碰運氣抓到；R37 抽出 SSOT 後，①②節只鎖「3 個
已知具名檔案」的行為細節，若有人在 repo 別處新增第 4、5 個呼叫點卻忘記
dot-source SSOT（或乾脆內嵌重寫一份判斷式），①②節完全看不見——這正是本節
要收斂的缺口：repo-wide 掃描「有沒有經過 SSOT」，不管新檔案叫什麼名字、
放在哪裡。
```

### §76 WindowsApps guard：`_EXEMPT_PS1_FILES` 清空的經過（R44 兩輪對抗式複審）

原址：`tools/tests/test_windowsapps_guard_cross_consistency.py` `_EXEMPT_PS1_FILES` 上方註解。

```text
R44 Architect 深度架構評估找到的系統性缺口：`test_ps1_mentions_of_windowsapps_all_go_through_ssot`
只掃「檔案內文字提及 WindowsApps 字面值」者——若一支 .ps1 直接裸呼叫 python
卻從未提及 WindowsApps 這個字（例如只寫了 `Get-Command python` 或連
`Get-Command` 判斷都沒有、直接 `& python ...`），舊判準完全不會去檢查它，
是比「有判斷但沒 SSOT」更原始的繞過形狀。以下為此新掃描（不再要求先提及
WindowsApps 字面值）已知需要豁免的檔案，皆附理由：

R44 二審 Architect 對抗式複審揪出：本清單原本還登記 `AISDLC_SDD/scripts/
ci-gate.ps1`，理由引用 bash 側 `test_migrated_with_fallback_branch_is_not_flagged`
判例（guard 檔案物理缺席才降級用裸判斷）——但親自檢查 ci-gate.ps1 原始碼後
發現兩者並不對等：`tools/lib/WindowsAppsGuard.ps1` 在該情境下明明存在、可以
像本輪其他呼叫端一樣直接 dot-source 後判斷，只是先前選擇不接上，並非「做不
到」。既然可補救、成本又低（僅需 2 行），已直接補上 guard（見 ci-gate.ps1
fallback 分支開頭），故該檔已從本豁免清單移除——多出的 SSOT dot-source +
`Test-IsRealPython` 呼叫自然通過下方 repo-wide 掃描，成為新的回歸鎖。

R44 SA 另一位一審對抗式複審（同一輪、獨立於上一段的 Architect 二審）對僅存的
`AutoClaude/tools/g0_gate_check.ps1` 一筆豁免提出同款質疑：豁免理由（假設呼叫
者已透過 bootstrap.ps1／dev_start.ps1 整備過環境）本身只是「未強制的假設」——
沒有任何機制保證排程／人工執行這支腳本時，該次環境真的整備成功過，只要機器上
仍只有 WindowsApps 空殼，一樣會重現本輪要修的原始缺口。親自確認 `tools/lib/
WindowsAppsGuard.ps1` 在該情境下同樣物理存在、可補救、成本同樣低（同款 2 行）
——故已直接補上 guard（見 g0_gate_check.ps1 開頭，`$Log`／`W()` 定義好之後、
兩處裸 `python` 呼叫之前），該檔已從本豁免清單移除，目前無殘留豁免項。
```

### §77 WindowsApps guard：ps1 裸 python 呼叫點判準由檔案層級改呼叫點層級的證偽實測（R44 SA 一審）

原址：`tools/tests/test_windowsapps_guard_cross_consistency.py` `test_python_calls_in_ps1_all_go_through_ssot` 判準註解第一段。

```text
R44 SA 一審對抗式複審揪出：`test_python_calls_in_ps1_all_go_through_ssot` 舊版
只做「檔案層級」判斷——`if _has_real_dot_source_of_ssot(text) and
_has_real_test_is_real_python_call(text): continue` 只要檔案內某處存在真正
的 dot-source SSOT 陳述式、某處存在真正呼叫 Test-IsRealPython 的陳述式，
全檔即視為安全，不檢查每一個裸 python 呼叫點是否真的受該次判斷保護。實測：
把 `AutoClaude/tools/run_local_nightly.ps1` 改回「僅 1 處 guard、其餘 15+
處裸呼叫且與 guard 判斷結果無關」的狀態（bug-injection 對抗式驗證，改壞後
確認測試仍綠），該測試依舊全綠——因為判準只看「guard 是否存在」，不看
「guard 的判斷結果是否真的擋住了這些呼叫」。
```

### §78 WindowsApps guard：Python 側「零 guard 裸 python 名稱」repo-wide 前瞻掃描的 WHY 與三段式邊界（R60，B-01）

原址：`tools/tests/test_windowsapps_guard_cross_consistency.py` `# Python 側「零 guard 裸 python 名稱」repo-wide 前瞻掃描` 區段註解。

```text
WHY 這一層原本缺席：同一個 guard 家族在另兩種語言各有**兩條**前瞻掃描軸——
  .sh ：`test_repo_wide_scan_finds_no_unmigrated_sh_scripts`（有裸 `command -v` 判斷
        但沒接 SSOT）＋ `test_repo_wide_scan_finds_no_zero_guard_python_calls`
        （整支檔案零可用性判斷、直接裸呼叫）
  .ps1：`test_ps1_mentions_of_windowsapps_all_go_through_ssot`（有提及但沒走 SSOT）
        ＋ `test_python_calls_in_ps1_all_go_through_ssot`（有呼叫但沒 guard）
Python 側只有 `test_windows_apps_predicate_impls_are_all_registered` 一條，而它的兩個
錨（函式名 `def *windows*apps*` ∪ 引號界定 `"windowsapps"` 字面值）都長在「**判斷式
實作**」上。對於一支**從頭到尾不提 WindowsApps、只是把裸 `python` 名稱交給 OS 解析**
的新檔案，兩錨結構上完全看不到它——正是 `_has_zero_guard_python_call` 在 .sh 側處理的
那個形狀（R44 曾在該側掰出真實命中）。實測本檔既有 helper 對此形狀正反皆零訊號：
  bare subprocess / which() 無 guard → `_matches_stub_anchor` 皆 False；
  對照組（第二份 predicate 實作）→ True ⇒ 鎖沒壞，是掃描面缺這個形狀。

軸別澄清（R60 反駁者訂正 (1)，勿再混指）：本節補的是**呼叫端納管（enrollment）**，
不是 `CrossPlatform_Scan_Dimensions.md` §(2) 講的「三份實作之間的行為等價」。等價軸在
Python 側**已有**機械鎖（同檔 `test_bootstrap_core_py_has_symmetric_stub_detector`
＋ `tools/tests/test_bootstrap_core.py` 五支行為測試，含「拔掉 guard 就會挑到空殼」的
bug-injection）。把兩條軸說成同一條會導出錯誤的修法。

暴露面比另兩種語言**窄**（R60 反駁者訂正 (2)，本節不宣稱相反）：bootstrap 悖論的內容是
「guard 必須在 Python 可用之前就能運作」，故 Python 側這份本質上只在真直譯器已存在時才
跑（`sys.executable` 必然可用）。本節因此是**前瞻性**防護（動工時 repo 內 live 違規＝0，
由本輪獨立 AST 全掃確認），而不是「Python 側是最後也最容易被繞過的一環」。

WHY 判準刻意寬鬆（字面值而非呼叫語法）：窄判準（只認 `which("python")`／subprocess
argv[0] 字面值／`or "python3"` 兜底）對本 repo 自己的**正典形狀盲**——`tools/
bootstrap_core.py` 是把候選名放進 list literal（`["python", "python3", …]`）再以
`shutil.which(parts[0])` 解析，變數化之後窄判準看不到任何裸名。實測窄判準只命中 2 支、
且**不含** bootstrap_core.py 自己；再發明者最可能照抄的就是這個正典形狀。故比照 .sh 側
`_invokes_python_bare`（刻意用寬鬆全字比對，理由同款：R44 目標形狀就含變數預設值間接
呼叫）改採字面值判準。過度觸發是 fail-loud（有人得看一眼並登記角色），漏報才是 fail-open。

相對 .sh/.ps1 的一個結構性優勢（可正面主張）：本節走 **AST**，註解與 docstring 由語法
結構天然排除，不需要 `_strip_bash_comment` 那類逐字元剝註解——而 R46 已證明那條路是無底洞
（繞過從整行註釋 → no-op 前綴 → heredoc 逐層復發）。

邊界宣稱（三段式，見 CrossPlatform_Scan_Dimensions.md §「邊界宣稱必須實測」）：
  【已實測涵蓋】① `subprocess.run(["python", "x.py"])`；② `shutil.which("python3")`；
    ③ 正典多候選 list literal ＋ `which(變數)`（窄判準對此盲）；④ shell 字串形態
    `subprocess.run("python -m foo", shell=True)`；⑤ `sys.executable or "python3"` 兜底；
    ⑥ 帶 guard 的檔案（`_matches_stub_anchor`）不重複計入本軸；⑦ 掃描面塌陷為 0 份 →
    等值斷言翻紅；⑧ 無法 parse 的候選 `.py` → AssertionError（不靜默略過）。
  【已實測不涵蓋】① 註解／docstring 內的提及（AST 結構性排除，**刻意**如此，見上）；
    ② 測試檔（`_is_test_py`，同姊妹掃描判準）；③ 凍結版 v0.01~v0.29（Copy-on-Evolve）；
    ④ 尚未 `git add` 的新檔（`git ls-files` 固有性質）；⑤ 字面值被拆開或間接組出
    （`"pyth" + "on"`、f-string、`os.environ["PY"]`）——與 `_matches_stub_anchor` 的
    K／O 既知邊界同源，屬靜態掃描天花板；⑥ 首 token 非裸名者（`"py -3.11"`／
    `"python3.11"`／`"python:3.11-slim"`）——前者是 Windows py launcher（不經 PATH 撞
    WindowsApps，`bootstrap_core.py:141` 註解已論證），後兩者是版本化名稱/docker tag。
  【未窮舉】本清單只是本輪真正跑過的項目，不主張已列出全部繞過路徑。
```

### §79 workflow 許可／併發鎖聚落：R68 擴充四類別的事故說明與 R69 訂正（DEF-101-703）

原址：`tools/tests/test_workflow_permission_concurrency_lock.py` 模組 docstring「R68 擴充」四項。

```text
R68 擴充（Pkg-4「CI／nightly 死亡通道」；檔名雖仍稱 permission/concurrency，
實質已是「compat-CI／root-infra-ci 的 workflow YAML 機械鎖聚落」——依鎖檔數
棘輪紀律〔DEF-101-561③，tools/tests/ shrink-only〕不另開新檔，一律擴充既有檔）：
  1. `TestNightlyAlertConclusionWhitelist` — 兩支 `*-nightly-alert` 的結論判讀
     必須是 **success 白名單**（fail-closed）。修復前為黑名單（只有字面
     "failure" 算紅），cancelled／timed_out／skipped／conclusion 為 null／job
     顯示名被加前綴 五種情境全部 fail-open 成「綠燈」，進而**自動關閉**一張
     仍然有效的 P1 issue 並留言「已恢復綠燈」——告警器主動抹除紅燈證據。
  2. `TestNightlyJobNameSelectorInterlock` — alert 的 jq `startswith("…")`
     選擇子字串必須是 nightly-full `name:` 的前綴。兩者是兩份手寫字面值，
     本 repo 慣例會在 job 名後綴輪次註記，一改名選擇子就落空成 "unknown"。
     GitHub Actions 的 `jobs.<id>.name` 不支援 `env` context，無法用共用變數
     消滅漂移面，故只能用機械鎖互鎖。
  3. `TestRootInfraNightlyStalenessSentinel` — root-infra-ci.yml 第 15 道
     （nightly-full 排程陳舊度哨兵）必須存在、必須阻斷、必須同時查兩支
     workflow 的成功紀錄。此道是 R68 對「兩支 nightly-full 自 2026-07-14 起
     18 天零成功而三道既有哨兵結構上都偵測不到」的直接修復（誠實劃界見該
     workflow 檔頭第 15 道：本道與被偵測者同計費平面）。
     **R69 訂正（DEF-101-703）**：R68 版寫死 `--event schedule`，與它自己印出的
     處置指令（`gh workflow run` ⇒ `event=workflow_dispatch`）實證互斥、照做也
     解不開；且無 `if:`／無豁免途徑 ⇒ 對每一次 push 都必紅＝死鎖。現行判準改為
     「兩事件都計入」＋「帶到期日／理由／長度上限的顯式豁免」，本類別同步鎖住
     **反 fail-open 三道保險**，確保豁免不能退化成永久假綠。
  4. `TestCompatCiScriptTriggerSymmetry` — 兩支 compat-CI 的 `paths` 白名單
     對全部 tracked `*.sh`／`*.ps1` 的觸發面必須**完全對稱、零豁免**。
     windows 側逐一列舉 `.sh`、macos 側用 `**/*.sh` 兜底（反之亦然）的不對稱
     設計本身保留（改成兩側都通配會讓凍結版樹下的腳本也觸發，代價不成比例），
     但「列舉面漏一支」從此有機械訊號。
```

### §80 workflow concurrency repo-wide 枚舉：缺陷本體（R77-55，修站點不修判準）

原址：`tools/tests/test_workflow_permission_concurrency_lock.py` `# 本輪 R77-55：concurrency 的 repo-wide 枚舉` 區段註解第一段。

```text
🔴 缺陷本體：本檔上方全部 concurrency 斷言都綁在 `_ARCH_FITNESS`／`_AUTOCLAUDE_CI`／
兩支 compat-CI／`_ROOT_INFRA_CI` 這 5 個**具名常數**上，而且問的都是「那一段字面值
還在不在」。於是：
  ① 沒被具名的 workflow 上，同一類缺陷完全隱形——實查 11 支，有 3 支的 workflow 層
     group 只綁 `github.ref` 卻帶 `cancel-in-progress: true`，其中兩支同時被 schedule
     與 workflow_dispatch 觸發；
  ② 「group 分不分得出事件類型」這個**判準**本身，全 repo 沒有任何一支測試在問。
而這正是 R7／R15／R23 已經在 autoclaude-ci 與兩支 compat-CI 上各修過一次的缺陷——
修的是站點，不是判準，所以它在沒被具名的檔案上原封不動地活著。
```

### §81 schedule cron 同步鎖：R15 SCAN-C-9 整行註解剝除取捨

原址：`tools/tests/test_workflow_schedule_sync.py` 模組 docstring 末段。

```text
R15 SCAN-C-9：`_IF_REF_RE` 無行首錨定、掃全文——若未來刪 job 時留下含
`github.event.schedule == '...'` 字樣的整行註解（本檔 dormant cron 註記慣例正是
這種形態），集合仍相等、cron 白燒 runner 而零訊號。修法：比對前先剝除「整行註解」
（`\\s*#` 起頭的行）。取捨說明：只剝整行、不剝行尾註解——(1) 行尾註解形態在受掃
workflow 現況不存在，主要風險面（刪 job 留整行註解）已被覆蓋；(2) 行尾剝法需分辨
字串常值內的 `#`（如 cron 欄位雖不含 # 但 run 指令行可能含），保守整行剝除
零誤剝風險。若未來出現行尾註解含 schedule 字樣的形態，再擴充剝法。
```

### R190 收尾棒搬遷史料（續；逐字 append）
本節接續 `CrossPlatform_R190_FixRound_Evidence.md`〈九-F〉：證據檔因體積逼近治理文件上限，最後 12 段 docstring 尾段改搬到這裡。以下每一小節是從 `tools/tests/` 三支鎖檔（`test_block_destructive_git_r83.py`／`test_context_budget_guard.py`／`test_mac_endurance_r83.py`）搬出的 docstring 尾段**逐字原文**，原位留一行指針（`史料搬至 CrossPlatform_Guard_Line_History_2.md〈R190 收尾棒〉§k。`）；各小節標題的 `L起-迄` 皆指搬遷前快照的行號。剝 docstring 後 `ast.dump` 與搬遷前逐字相同。

#### §1　`test_block_destructive_git_r83.py`　FunctionDef:test_the_loop_condition_boundary_is_load_bearing docstring L1046-1052（搬出原 L1048-1052，5 行）
```text

        🔴 探針同樣是實測訂正過的：第一版拿 `pgrep … | while read p` 當探針，注入後仍
        放行——因為那條救它的是**位置順序**（pgrep 在 `while` 之前，本來就不在掃描區間內），
        不是條件邊界。真正只有邊界救得了的是「pgrep 在 `do` **之後**」這一族。
        """
```

#### §2　`test_block_destructive_git_r83.py`　FunctionDef:test_a_stash_the_guard_already_saw_is_not_reported docstring L1756-1762（搬出原 L1758-1762，5 行）
```text

        ack **不是**子字串判定，也**不含**「被擋」與 `stash create` 兩種（前者根本不會跑、
        後者一個字節都不動那個 ref ⇒ 都解釋不了任何變動）；被訂正掉的兩處假事實逐字＝
        `docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`。
        判準與紅綠自證見 `TestR84SentinelAckIsNotASubstring`。"""
```

#### §3　`test_block_destructive_git_r83.py`　ClassDef:TestR84TheWaitformDocstringIsTheSingleHome docstring L2253-2259（搬出原 L2255-2259，5 行）
```text

    這一條把「docstring 與實作逐字相符」做成機械物：docstring 自陳幾條，就必須真的有
    幾條判準各自能單獨命中。只斷言「docstring 裡有 ① ② ③」會恆綠——那正是本 repo
    反覆判紅的「鎖存在但沒有鑑別力」。
    """
```

#### §4　`test_block_destructive_git_r83.py`　ClassDef:TestGovernanceFilesAreReadOnlyWhenUnattended docstring L2387-2393（搬出原 L2389-2393，5 行）
```text

    六個方向對齊本檔既有慣例：①該擋的擋（無人值守 × 保護面 × 三種寫檔工具）；
    ②不該擋的放行（有人值守／保護面之外／專案根之外的同名檔）；③逃生口；
    ④開關不共用（**雙向**都驗）；⑤退化 payload fail-open；⑥判準本身可證偽。
    """
```

#### §5　`test_context_budget_guard.py`　FunctionDef:test_the_new_evidence_lines_do_not_break_the_next_run_time_credential docstring L2015-2021（搬出原 L2017-2021，5 行）
```text

        判準看的是**產出**：把新增的兩段輸出接在真實形態的取證輸出上，取回的值必須逐字
        不變。`LogonType`／`RunLevel`／`UserId` 三個欄名都不以 `nextruntime` 開頭，所以
        這件事在設計上就成立——但「設計上成立」正是需要被釘住的那種宣稱。
        """
```

#### §6　`test_context_budget_guard.py`　FunctionDef:test_the_guard_is_registered_on_both_events_that_the_sentinel_needs docstring L2644-2650（搬出原 L2646-2650，5 行）
```text

        🔴 R82／HELM-02 起是**兩個**事件，缺一即斷：SessionStart 清閂鎖（`claude -r`
        續接時能重新武裝）、PostToolUse 才是真正會註冊排程的那一個。此前只驗前者，
        而武裝已經搬到後者 ⇒ 只驗一個等於把接線的一半交給運氣。
        """
```

#### §7　`test_context_budget_guard.py`　ClassDef:PaceAutoDerivesActiveModelTest docstring L12786-12792（搬出原 L12788-12792，5 行）
```text
    `session_resume_planner.py` 現在補上 `harness_feed.active_model_of()`——與
    PreToolUse hook（`context_budget_guard.py` 的 `active_model = model_family(
    scanned[2]) if scanned and scanned[2] else None`）同一組轉換規則，讓 `--pace`
    與守衛看同一把尺。紅端：同一份快取下 `--pace` 與 `--pace --model fable`
    此前逐字不同（前者恆帶 `model-scoped-excluded`）。"""
```

#### §8　`test_context_budget_guard.py`　FunctionDef:test_a_single_session_climbing_the_warn_band_speaks_exactly_once docstring L13122-13128（搬出原 L13124-13128，5 行）
```text

        「每 5pp 重新武裝」提案的評估與代價逐字見證據檔 §I-6——該提案一落地必須
        先讓本條轉紅（它也會打紅 `LatchRearmTest::
        test_the_same_tier_and_window_still_only_fires_once`，與本案正交，另輪處理）。
        """
```

#### §9　`test_context_budget_guard.py`　FunctionDef:test_end_to_end_hook_reports_harness_source_and_appends_cross_check docstring L13975-13981（搬出原 L13977-13981，5 行）
```text

        `_isolated_env()` 把子行程的 `HOME` 蓋成 `home_dir`、且明確 pop 掉
        `AUTOSDD_CONTEXT_FEED_DIR`（見該函式 R+D32 補的隔離）⇒ feed 必須寫在
        `context_feed_path()` 沒有旗標時的預設位置：`$HOME/.autosdd/context_feed/`。
        """
```

#### §10　`test_mac_endurance_r83.py`　FunctionDef:test_the_launchd_only_exemptions_really_have_no_outside_consumer docstring L437-442（搬出原 L438-442，5 行）
```text

        少了這一條，下一個人只要把新方法加進 `_LAUNCHD_ONLY` 就能繞過整道鎖（實測：
        把 `evidence_hint` 塞進白名單，對稱判準當場轉綠）——那正是本 repo 判過的
        「有鎖在守假話」：檔案在、判準在、測試全綠。
        """
```

#### §11　`test_mac_endurance_r83.py`　FunctionDef:test_the_mac_credential_never_states_a_next_run_time docstring L724-729（搬出原 L725-729，5 行）
```text

        launchd 不報「下次幾點跑」（實測：print 輸出裡 next／fire／due 皆不存在），任何
        時刻都只能是我們自己推算的。憑證裡放一個推算時刻，就是把它偽裝成排程器的陳述
        ——而那正是 Windows 側 `NextRunTime` 之所以能當憑證的理由被掏空的方式。
        """
```

#### §12　`test_mac_endurance_r83.py`　FunctionDef:test_the_patrol_moment_deliberately_gets_no_calendar docstring L1201-1206（搬出原 L1202-1206，5 行）
```text

        這不是省事：寫了就代表下一個 tick 的回讀不符 ⇒ 每 15 分鐘 bootout+bootstrap 一輪，
        而 bootstrap 是整條鏈上唯一會讓哨兵消失的動作。憑證此時必須明說「只有巡邏觸發」
        ＋最壞死等秒數，不准留白（留白會讓它與「排到了確切時刻」看起來一樣）。
        """
```

## R194 淨減法搬遷

> 搬遷自 `tools/tests/*.py`（2026-10-03 R194 收尾單人窗口 Trim 棒，款(11) 淨額抵銷；原文全文保全、知識零刪除；僅去掉註解前綴與縮排）。原位各留一行指標，或壓成只剩現行行為說明的短註解。§82 起連號；§C 部分（devB／devC／devD 從 hook／lib 刪下的散文）無原位指標，僅供查證。

### §82 extras 引號鎖：`_UNQUOTED_EXTRAS_RE` 逐分支 (a)~(e) 的訂正沿革（R57 round 1 SD 複審、R59 新增三件）

原址：`tools/tests/test_extras_quoting_zsh_safety.py` `_UNQUOTED_EXTRAS_RE` 上方註解（`# R57 round 1 SD 複審訂正沿革` 起）（搬遷前 L87-L105）。含 `zsh-glob-ok` 豁免標記的三行病例樣本（原 L88／L98／L105）因本鎖的豁免預算（`_MIN_SELF_SAMPLES`／`_MAX_EXTERNAL_EXEMPTIONS`）而**必須留在原址**，下文以占位行標示。

```text
R57 round 1 SD 複審訂正沿革（皆經實測，見 DEF-101-479）：
（原 L88：含 zsh-glob-ok 豁免標記的病例樣本，未搬、仍在原址）
    這種帶 GNU 長旗標的寫法整條漏報（實測 old=False / new=True）。改為 `--?[A-Za-z][A-Za-z-]*`。
(b) 原有的前方 lookbehind `(?<!["'])` 是**死碼**：加引號版長成 `install -e '.[dev]'`，該位置
    的字元是 `'` 而 `\.\[` 本身就要求是 `.`，正則在此必然失配，lookbehind 沒有額外作用。
    實測 6 組樣本在「有 lookbehind／無 lookbehind」下結果完全相同，故移除並訂正註解。

R59 新增三件（DEF-101-507／508）：
(c) 裸 `.[` 分支前置一個 **選配的路徑前綴** `(?:[^\s'"]*[/\\])?`——R57 版的錨要求 `.[`
    緊接在旗標之後，故下列這種寫法整條漏報。POSIX `/` 與 Windows `\` 兩種分隔符都吃
    （`bootstrap_core.py` 用 `os.sep` 組路徑，兩者都會出現）：
（原 L98：含 zsh-glob-ok 豁免標記的病例樣本，未搬、仍在原址）
(d) **具名套件**分支 `[A-Za-z_][A-Za-z0-9_.-]*\[…\]`：DEF-101-507 的本體。名稱字元類
    刻意不含空白，故 `pip install foo   # 見 [附註]` 這種「同行後方另有方括號」不誤報。
(e) **插值 target**分支 `\$?\{[^}!]*\}`（R59 SD-R59-04 起排除 `!`，見下）：DEF-101-508 在原始碼裡的真實長相如下，方括號
    在字面上根本不存在，(a)~(d) 全都看不到它。無論插值進來的是什麼，你都無法保證它
    不含 glob 元字元或空白，故「印給使用者複製貼上的插值 target 一律要加引號」是這裡
    唯一站得住的規則：
（原 L105：含 zsh-glob-ok 豁免標記的病例樣本，未搬、仍在原址）
```

### §83 extras 引號鎖：已加引號形態下限（`_MIN_QUOTED_DOT`／`_MIN_QUOTED_NAMED`）的實測分解（R57／R59、二審 QA-R59-P3-2 訂正）

原址：`tools/tests/test_extras_quoting_zsh_safety.py` `_MIN_QUOTED_DOT` 上方註解第二段（搬遷前 L155-L161）。

```text
R57 修復後裸/路徑形態實測 30 處，R59 擴面後為 35；具名形態 R59 修復後實測 42 處。
42 的分解（二審 QA-R59-P3-2 訂正：初稿寫「41 處本輪新加引號 + ONBOARDING 1 處」，
41 這個數字對不上帳本 DEF-101-507 記的 40 處，差額是本鎖 docstring 自帶的正確樣本）：
  40 處＝本輪 DEF-101-507 實際新加引號的站點（與帳本一致）
+  1 處＝`ONBOARDING.md` 那處 R57 自己就寫對的 `'AutoClaude[dev,…]'`
+  1 處＝本鎖 docstring 內自帶的正確形態樣本（掃描面含本檔，故自己也被計入）
兩者各取約 6 成的保守下限。
```

### §84 extras 引號鎖：`_MAX_EXEMPTIONS` 由寫死的 10 改為衍生值（R59 二審 ARCH-R59-02-C1 訂正）

原址：`tools/tests/test_extras_quoting_zsh_safety.py` `_MAX_EXEMPTIONS` 上方註解（搬遷前 L195-L198）。

```text
R59 二審 ARCH-R59-02-C1 訂正：本常數原為寫死的 10，於是「自身樣本寬上限 20」在結構上
**不可達**——總帳先綁死，實際自身天花板是 `10 − external`（實測 7），headroom 只剩 1，
我要修的失效模式原封不動還在（下輪補 2 行病例樣本就翻紅，訊息仍把成因指錯人）。
改為**衍生值**：分帳成為權威，總帳降格為 sanity net（仍保留 fail-loud 網，不刪測試）。
```

### §85 extras 引號鎖：`_scan_targets()` 由 tracked-only 改為聯集掃描面的立案沿革（R69 真 fail-open、R70／DEF-101-752）

原址：`tools/tests/test_extras_quoting_zsh_safety.py` `_scan_targets()` docstring 第二段（搬遷前 L205-L212）。

```text
🔴 本函式原名 `_tracked_scan_targets`、只跑 `git ls-files`，而本檔 docstring
「已實測不涵蓋」節逐字寫著「未 tracked 的新檔在 `git add` 前掃不到（`git ls-files`
固有性質，**與 `test_platform_utils_dedup.py` 同政策**）」——R69 證明那個政策是
真 fail-open：`AutoClaude/autoclaude/utils/platform_caps.py` 全程 untracked，
使它與 dedup 鎖的衝突躲過四輪四方複審與多次全套實跑，直到 `git add -A` 才顯形。
該檔已於 R70 改為聯集掃描面，本檔同步（否則「同政策」這句話會指向一個已經不存在
的政策，讀者仍會以為盲區是刻意取捨）。`-o --exclude-standard` 尊重 `.gitignore`，
`_EXCLUDED_SUBSTRINGS` 過濾與 `_MIN_SCANNED` 下限皆不受影響。
```

### §86 extras 引號鎖：豁免總數上限的 R59 實測與單一總上限缺陷的訂正沿革（R57 的 5 調到 10、R59 二審再訂正）

原址：`tools/tests/test_extras_quoting_zsh_safety.py` `_MAX_EXEMPTIONS` 上方註解（`# 豁免總數上限` 段後半）（搬遷前 L173-L179）。

```text
R59 實測 9 行：`ONBOARDING.md` §5 雷區表 1 行 + 本檔 docstring／註解的病例樣本 8 行
（本檔是這道鎖的實作，且判準 (4) 的三段式**要求**逐項列出被涵蓋/不涵蓋的壞形態，
內含壞形態是本質需求；整檔排除才是 fail-open，故仍走逐行豁免）。上限自 R57 的 5
調到 10 即為此擴面所需，非放寬紀律。**R59 二審再訂正**：單一總上限本身就是缺陷來源
——它把「本鎖的規格文件有多長」與「有沒有人濫用豁免」混在同一個計數器裡，撞頂訊息
會把成因指錯人，最省力的反應就是再調高數字。現行權威已改為下方兩本分帳，
`_MAX_EXEMPTIONS` 為其衍生值（sanity net）。
```

### §87 交棒宣稱鎖：R82 Q4-01 的另一半——命中數加總使最新一份掉到 0 打不出來（R78 SD-03 同病在同檔復發）

原址：`tools/tests/test_doc_loc_baseline_freshness_r60.py` docstring（搬遷前 L6522-L6525）。

```text
🔴 R82 Q4-01 的另一半：上一版把每一份交棒書的命中數加總後才判 `>=1`，於是 R79
那 7 筆讓總量永遠 ≥1，**最新一份掉到 0 在結構上打不出來**（R81 交棒書就是這樣
整份 0 命中而全綠的）。這正是本檔 docstring 自己記載過的 R78 SD-03 錯誤——判準
建在只會單調增長的歷史總量上——在**同一支檔案內復發**。
```

### §88 退場判準／改派判準：R76-08 缺陷本體——綁字面 token 的判準讓「照規矩訂正文件」反而轉紅

原址：`tools/tests/test_doc_loc_baseline_freshness_r60.py` 註解（搬遷前 L5721-L5726）。

```text
🔴 缺陷本體（R76-08，「有鎖在守假話」的實例）：`CrossPlatform_Scan_Dimensions.md`
硬規則② 的「已實測不涵蓋」清單裡，**否定語意**（「無回執」「零改派」）自 R74 起已被
`_REASSIGN_NEGATED_RE` 涵蓋，那一項因此成了假話；而釘住它的判準是
`assertIn("否定語意", rule2)`——綁**字面 token**。兩件事合起來的方向是最壞的那個：
照本檔自訂的規矩去訂正文件，根層閘門反而會**轉紅**（該文件自陳的規矩是「被涵蓋時
翻紅、強迫改文件」，實況卻是「改文件才紅」）。
```

### §89 活文件掃描面納入 `AutoSDD_improving_*.md`：R81 QA B-3 的注入實測與存量成本

原址：`tools/tests/test_doc_loc_baseline_freshness_r60.py` `AutoSDD_improving_*.md` glob 條目上方註解（搬遷前 L3980-L3985）。

```text
🔴 R81 QA B-3：軌道① 的**唯一驅動器**（根 CLAUDE.md 明定），每輪最多人照著讀的
活文件——卻是本面上線時整片失明的一角。注入實測：同一句假路徑放進交棒書兩顆牙都
咬，放進 `AutoSDD_improving_105.md` 則 13 tests OK 直接放行，而四項誠實劃界一句
都沒提到它（「有鎖在守，但那一面不在射程」比沒有鎖更難看見）。收進來的存量成本
實測僅 3 筆（全在最新一份、且全是該檔自己聲明「本輪尚未建立」的產出目標），
遠低於程式碼面那 49 筆 ⇒ 沒有「製造大批假紅」的顧慮。
```

### §90 路徑宣稱判準：`path_claim_bases()` 兩個多出基準的實測筆數（7 筆／6 筆）與 R73 判例

原址：`tools/tests/test_doc_loc_baseline_freshness_r60.py` `path_claim_bases()` docstring（搬遷前 L3994-L4003）。

```text
解析基準。**衍生自** `_MECHANISM_PATH_BASES`，不另開一份清單——那份常數已寫明
「子專案段落的相對路徑相對於該子專案目錄」的理由，本面適用同一條。多的兩個都是
實測逼出來的，不是預防性擴面：
  · 套件根 `AutoClaude/autoclaude`——CLAUDE.md 架構大圖以 `execution/playbook_runner.py`
    這種**套件內**相對路徑指認模組（實測 7 筆），少了它會整批誤報。
  · SDD LATEST 版根——ADR 與 ONBOARDING 以 `tools/fsm_runtime/state_loader.py`、
    `cicd/SDD_CICD_BASE_LAYER.md` 這種**版內**相對路徑指路（實測 6 筆）。版名走既有
    SSOT `tools/lib/sdd_latest.py`，**不在本檔再寫一份版號 regex**（R73 判例）。
LATEST 解析失敗即 `AssertionError`（fail-loud，同 `read_adr_docs`：掃描邊界不得
靜默縮小——縮小的方向永遠是「看起來變乾淨」）。
```

### §91 雲端 nightly 紅燈判準（表③）：R76-03 立案——run 層 conclusion 通道零讀者，continue-on-error 讓紅 job 下 run 仍 success

原址：`tools/tests/test_doc_loc_baseline_freshness_r60.py` docstring（搬遷前 L4987-L4990）。

```text
WHY（R76-03）：表③ 記的是 run 層 `conclusion`，而 job 層 `continue-on-error: true`
讓那個 job 紅掉時 run 仍是 `success` ⇒ 表③ 六列全 ✅ 與「裡面有 job 是紅的」可以
同時為真。該通道在本 repo 已實測**零讀者**（唯一顯形處是一張沒人看的 GitHub issue），
一筆真實 P1 因此橫跨數輪的「雲端全綠」宣稱。
```

### §92 表① 受鎖欄欄頭鎖：WHY——平台中立的 MIN_TESTS 釘選掛在標示「Windows 11 實測」的欄頭底下（SA-R67-07、DEF-101-562 欄頭版）

原址：`tools/tests/test_doc_loc_baseline_freshness_r60.py` `test_table1_locked_column_header_does_not_speak_for_a_provenance` docstring 第二段（搬遷前 L1456-L1461）。

```text
WHY（成因是結構性的，不是筆誤）：`rootunit-baseline-live` 抽的 token 取自
`run_root_unittests.MIN_TESTS`，那是一個**平台中立**的下限釘選——誰在哪台機器重釘
都寫進同一格。而該格所在欄的欄頭長年寫著「Windows 11（R60 收尾實測）」，於是
R67 在 Darwin 真機重釘後，一個 macOS 量得的數字就靜靜掛在標示「Windows 11 實測」
的欄頭底下。**產生器把 token 洗新鮮了，欄頭卻沒有任何機械物在看**——與 DEF-101-562
（「只保證被抽取的 token 新鮮，不保證同一行的散文新鮮」）是同一個病灶的欄頭版。
```

### §93 表① macOS 欄鎖：WHY——macOS 欄是純散文、寫死的 `616（skipped=4；R57 量測）` 落後實況約九輪而無機械物看見（R60 ARCH-R60-03）

原址：`tools/tests/test_doc_loc_baseline_freshness_r60.py` docstring（搬遷前 L1428-L1431）。

```text
WHY：`rootunit-baseline-live` 鎖只抽**右欄**那個 `N tests OK` token，macOS 欄是純
散文。原本該格寫死 `616（skipped=4；R57 量測）`，落後實況約九輪而**任何機械物都
抓不到**——它根本不在鎖的取值範圍內；而該格與受鎖格同處一張標榜「live 格（有機械
鎖）」的表內，讀者會誤以為「有鎖所以可信」（R60 ARCH-R60-03 的原始成因）。
```

### §94 nightly_summary 有界讀取鎖：上一版是零鑑別力的死鎖（把 `f.seek` 整行刪掉仍 6/6 全綠；與 DEF-101-763 同構）

原址：`tools/tests/test_doc_loc_baseline_freshness_r60.py` docstring（搬遷前 L2646-L2650）。

```text
🔴 本支上一版是**零鑑別力的死鎖**（本批注入實測：把 `f.seek(…)` 整行刪掉、改成
`f.read()` 讀滿全檔，6/6 照樣全綠）。它斷言的是「檔頭誘餌不出現在**輸出那一行**」，
而 `nightly_summary()` 取的是 `hits[-1]`——檔尾的真彙總行**永遠**會蓋掉檔頭誘餌，
於是它證的其實是「取最後一筆命中」，跟有沒有界完全無關；docstring 卻宣稱後者。
「寫了鎖沒驗鎖」與 DEF-101-763 的 fallback 文案同構：看起來有守，實際一天沒守過。
```

### §95 幽靈路徑基線：R81 SA-B3 登記的 `CrossPlatform_R81_Review.md` 於本輪建立後被自清機制要求刪除（豁免不會永久化的活體證據）

原址：`tools/tests/test_doc_loc_baseline_freshness_r60.py` 註解（搬遷前 L4038-L4042）。

```text
── R81 SA-B3：上一格曾登記 `docs/06_quality/CrossPlatform_R81_Review.md`（計畫書 §6
把本輪產出目標逐份列出，而該檔在寫下那一行時尚未建立）。**該檔已於本輪建立**，
`stale_path_baseline_problems()` 的第一款當場轉紅並要求刪除該筆登記 ⇒ 已刪，天花板
同步下修。留這段註解是為了記下**這道鎖的自清機制真的動作過一次**：豁免不會永久化，
不是因為有人記得回來清，是因為清不掉就會紅。
```

### §96 subprocess 編碼鎖：per-tree 檔數下限「腐化偵測帶」的缺陷本體（R75 QA 實測 files=81 對 floor=18、DEF-101-800）

原址：`tools/tests/test_subprocess_encoding_hygiene.py` 註解（搬遷前 L72-L76）。

```text
🔴 缺陷本體：下限原本是**單邊**的，而單邊下限只會腐化——樹會長大、下限不會，
於是它實際守住的比例逐年下滑。R75 QA 實測：`tools` 樹 files=81 對 floor=18
⇒ 掉掉 63/81（78%）掃描面仍然全綠，而那個 18 的來源是 2026-07-19 首掃數
打八折，中間 R74 又是新增檔案最多的一輪。**「掃描面靜默縮小必紅」這個存在
理由當時已經不成立**，鎖還在，牙掉了。
```

### §97 dev_start ps1／sh 被 source 鎖：兩部分的立案沿革（DEF-101-304／R35 發現、R67-C17 併入既有鎖檔、CI 帳務停擺）

原址：`tools/tests/test_dev_start_ps1_lastexitcode.py` 模組 docstring 第二、三段（搬遷前 L4-L15）。

```text
第一部分（DEF-101-304）：`tools/dev_start.ps1` dot-source 失敗分支曾未對
`$LASTEXITCODE` 賦值（呼叫前殘值可能是 0 而誤判成功），對等的 `.sh` 用 `return 1`
正確傳遞失敗，兩邊曾不對稱（R35 發現）；本測試只驗證「找不到 Python 直譯器」這條
分支（PATH 清空即可穩定觸發）。

第二部分（R67-C17 併入既有鎖檔，非新開一支）：`source tools/dev_start.sh` 是使用者
每天開工的第一道指令，該檔的 zsh 專屬路徑（`ZSH_EVAL_CONTEXT`／`${(%):-%x}`）此前
全 repo 零活體驗證（CI 帳務停擺、`bash -n`/`zsh -n` 只做語法解析）。斷言刻意走
**行程外側通道**（證物寫進重導向檔、Python 端檢查）——同一 shell 內斷言在 sourced
偵測壞掉時會被 dev_start.sh 檔尾 `exit` 直接殺掉、後面斷言一行都不執行卻仍 rc=0；
「斷言被跳過」因此變成「證物檔不存在」＝當場紅，而不是靜默通過（史料見
CrossPlatform_DEF200275_Context_Metering_Evidence.md〈第七輪 史料搬遷〉）。
```

### §98 `_platform_helpers.py` `_PS_COMMENT_LEAD`：R57 round 3／4 補右括號類與引號類收尾字元、「為什麼安全」理由訂正與全語料實掃

原址：`tools/tests/_platform_helpers.py` `_PS_COMMENT_LEAD` 上方註解（搬遷前 L288-L296）。

```text
R57 round 3：原集合漏掉右括號類與引號類收尾字元，使「功能碼後緊接 `#`」的五種
真實 PowerShell 註解形態不被剝除（ground truth＝pwsh 7 parser 的 Comment token；
對照組 `c#`／`$#` 等現行設計要保護的情形不受影響，64 案差分實測 FAIL_CLOSED=0）。
round 4 訂正「為什麼安全」的理由：保護來源是 command/argument（bareword）解析
模式（bareword 本身可含 `#`），不是「前一字元是字母／`$`」——同一個 `$x#c` 在
expression 模式下 `#` 就是註解，原理由與 PowerShell 真實規則不等價。bug-injection
與全語料實掃（137 支 `.ps1`、2,847 個真 Comment token，現況洩漏數 0）等逐項量測
全文搬至 `docs/06_quality/CrossPlatform_R104_Scan_Findings.md`〈_PS_COMMENT_LEAD
沿革〉節；已知不涵蓋的第 5 條見 `strip_ps_comments` docstring。
```

### §99 wrapper thinness 鎖：R10 守門改制（黑名單軍備競賽三輪被繞過）與 R60 Scan-E E-A-02 關鍵字偵測由串聯改並聯

原址：`tools/tests/test_check_wrapper_thinness.py` 模組 docstring 第二、三段（搬遷前 L4-L13）。

```text
R10（DEF-101-134）守門改制：權威判定＝正規化內容 sha256 釘選（白名單化，
終結黑名單軍備競賽——曾三輪被 `for(`/`python3 -c`/`.ForEach(` 繞過）；
黑名單降級為非權威的補充訊號。既有關鍵字測試保留：fake root 內容
必然使 hash 紅燈，關鍵字診斷應伴隨出現（史料回歸鎖繼續有效）。

R60 Scan-E E-A-02：關鍵字偵測原本整段巢狀在「hash 已紅」分支內（＝兩道防線
串聯，更新 pin 即整組失效），已改為**並聯**。本檔下方 `TestKeywordDetectionParallel`
是該修復的回歸鎖（含「pin 已更新」的紅燈斷言＋兩個正控），10 個 forbidden 注入樣本
（R85 起收斂成單一表驅動判準，見 TestCheckWrapperThinness 內的注入表）全部走
`_make_fake_root()`＝必然 hash 紅燈態，對「pin 已更新」這條路徑天生零訊號，故必須另立。
```

### §100 PowerShell 引擎 SSOT 鎖：機器屬性寫成常數的立案（R69 原案、R73 擴射程 DEF-101-777、DEF-101-757 同型復發）

原址：`tools/tests/test_ps_engine_ssot.py` docstring（搬遷前 L646-L652）。

```text
WHY（R69 原案）：`_ps_engine.py` 曾把「這台機器缺 pwsh 7」寫成常數，那是撰寫
當輪那台 Windows 機器的屬性；平台／環境可用性是輪次屬性，治理文件與護欄程式
一律指向現查來源。R73 擴射程（`DEF-101-777`）：R69 的鎖只圈一個檔，這台機器
後來裝上 PowerShell 7 後射程外的同型句子同時變成假事實，實查命中 5 處（含
本檔自己 3 處）——`DEF-101-757`「已知的鎖射程缺口不得只以劃界結案」的同型
復發。判準刻意窄：只抓「本機 + 無/沒有/不存在 + 引擎名」斷言句，另有兩類
結構性豁免各有獨立鎖。史料見證據檔〈第七輪 史料搬遷（Dev-Trim8）〉。
```

### §101 PowerShell 引擎 SSOT 鎖：`_STALE_CLAIM_RE` 主語與否定詞視窗 8→16 字的經過（R74 DEF-101-777）與 R73 教訓

原址：`tools/tests/test_ps_engine_ssot.py` `_STALE_CLAIM_RE` 上方註解（搬遷前 L566-L573）。

```text
「把機器屬性寫成常數」的句型判準。**射程單位＝邏輯段，不是物理行**（R74 修
`DEF-101-777` 的漏抓面，見 `_logical_segments` 與 `stale_local_engine_claims`）。

🔴 R74 放寬主語與否定詞之間的視窗（8 → 16 字）：舊視窗是照最短句型的長度訂的，
主語後面只要插一段括號補述（實測逃掉的那個站點插了 11 字的機型括號）就超窗漏抓。
窗放寬不會讓判準失控——`[^。]` 仍把射程關在**同一個句子**內，這才是真正的邊界。
逐字樣本一律只放在下方 `test_detector_catches_*` 的樣本清單裡並帶行尾豁免標記，
不寫進說明散文（R73 教訓：訂正註記逐字引述假話＝在樹裡多留一句假話）。
```

### §102 排程能力對照契約：R75 訂正（SD 追加②）——寫死的下限 40 腐化、改與 skip_tag_policy 共用逐樹下限政策

原址：`tools/tests/test_schedule_capability_parity.py` docstring（搬遷前 L435-L440）。

```text
🔴 R75 訂正（SD 追加②）：下限原為寫死的 `40`、註解寫「R60 實測 43 份」，而 R75
實測已是 53 份 ⇒ 下限只剩實測的 75%，對「靜默縮面」的鑑別力被吃掉一截，而
**沒有任何東西會在它過期時說話**——這與 R74 自己踩到的 `MIN_TESTS` 腐化 11 輪
是同一種病。現改為與 `tools/lib/skip_tag_policy.py` 的逐樹下限**共用同一條政策**
（下限＝實測的 `TREE_FLOOR_RATIO`），並補上第二個方向的斷言：下限一旦跌破該比例
就是一筆失敗，逼人回來重釘。比例常數刻意 import 而非在此再寫一份 0.8。
```

### §103 WindowsApps guard 交叉一致性鎖：站點偵測三輪訂正逐步收斂鑑別力（函式名錨→雙錨→re.I、scoped_prefixes 縮面漏 16 支）

原址：`tools/tests/test_windowsapps_guard_cross_consistency.py` docstring（搬遷前 L1196-L1205）。

```text
三輪訂正逐步收斂鑑別力：①以函式名為錨曾被逐字相同、只改函式名的第二
實作完整逃過，改以判斷式內容為錨並比照 `_EXEMPT_PS1_FILES` 慣例登記
白名單；②函式名錨與運算式錨互補，改為 `_STUB_NAME_RE` ∪
`_STUB_PREDICATE_RE` 雙錨判定；③兩錨原大小寫敏感，補 `re.I` 收攏
（既知邊界：改名且嵌進更大字串或字串串接組出者仍逃得掉）。掃描面亦曾
因 `scoped_prefixes` 縮面漏掉 16 支生產 `.py`，改為與姊妹 `.ps1`／`.sh`
掃描同政策（只排凍結版與測試檔）。白名單有 stale 檢查（登記項不再命中
任一錨即翻紅），測試檔本身排除在外（同檔內出現字面值是斷言 SSOT 內容，
非第二實作）。逐輪實測數字與 bug-injection 案例史料見證據檔
〈第七輪 史料搬遷（Dev-Trim8）〉。
```

### §104 WindowsApps guard 交叉一致性鎖：R44 SA 一審追加揪出——初版判準是檔案層級（1 處 guard、15+ 處裸呼叫仍全綠）

原址：`tools/tests/test_windowsapps_guard_cross_consistency.py` docstring（搬遷前 L1139-L1144）。

```text
R44 SA 一審追加揪出：初版判準是檔案層級（只要檔案內某處存在 guard
陳述即視為全檔安全），實測構造「1 處 guard、其餘 15+ 處裸呼叫與判斷
結果無關」仍全綠。改用 `_all_python_invocations_are_ssot_protected`：
呼叫點層級，要求每個裸呼叫歸類到 (A) guard 失敗即 fail-fast 或
(B) guard 結果存變數、全呼叫點改用該變數，任一歸類不到即未受保護。
真實案例清單與逐輪追加史料見證據檔〈第七輪 史料搬遷（Dev-Trim8）〉。
```

### §105 dev_start 版本探測碼逐字相同鎖：R71（DEF-101-760）——上面那支鎖只看版本數字，單邊改掉探測碼時本檔與 CI 全綠

原址：`tools/tests/test_dev_start.py` 註解（搬遷前 L5414-L5419）。

```text
🔴 R71（DEF-101-760）：上面那支鎖**只看版本數字**，看不到探測碼本體。兩份
`.sh`／`.ps1` 的檔頭都白紙黑字寫「用**同一段**探測碼（同構，非各自發明）」，
但那是散文——實測（本輪動工前）單邊把探測碼改掉，本檔與 CI 全部照樣綠燈。
DEF-101-760 正是踩在這個縫上：`else ""` 在 bash 沒事、在 PowerShell 5.1 會被
吃掉一個雙引號而整條失效，於是「兩側寫法必須逐字相同」這個假設一旦破裂，
就只剩其中一個平台的使用者會炸，而且沒有任何機械物會出聲。
```

### §106 dev_start Mutex 鎖：R59 QA-R59-05——原為全檔 assertIn，Mutex 名在 .ps1 內出現兩次而被訊息字面滿足（DEF-101-504 保護歸零）

原址：`tools/tests/test_dev_start.py` 註解（搬遷前 L1003-L1007）。

```text
R59 QA-R59-05：原為全檔 assertIn，而該 Mutex 名在 .ps1 內出現兩次
（功能碼的 New-Object 與一行 Write-Output 訊息）。只改功能碼那一處、保留訊息
字面，本鎖與 AutoClaude 側同款全檔鎖都會照綠，而 `_nightly_running()` 對真的
在跑的 nightly 靜默回 False＝假「沒在跑」，DEF-101-504 的保護整體歸零。
改為鎖住**實際建立 Mutex 的那一句**。
```

### §107 dev_start 新四態 str 態：斷言不得寫死 POSIX 字面值 `/elsewhere`（R69 windows-compat-ci 實紅；改比對 `str(Path(...))`）

原址：`tools/tests/test_dev_start.py` `str` 態測試 docstring 第二段（搬遷前 L2909-L2913）。

```text
🔴 R69（windows-compat-ci 假紅）：斷言不得寫死 POSIX 字面值 `"/elsewhere"`——生產碼印的是
`Path` 物件，其 `str()` 在 Windows 是 `\\elsewhere\\AutoClaude\\…`，字面值必然
落空（windows-compat-ci 實紅）。改比對 `str(Path(self._ELSEWHERE))`：兩平台各自
正規化後仍要求**整條目標路徑**出現在訊息裡——比原本只找 `/elsewhere` 更嚴，
不是把斷言改弱。
```

### §108 WindowsApps bash guard：`_tracked_*` 掃描面擴為 tracked ∪ untracked 的 R82（DEF-101-752）立案與姊妹函式刻意不比照的理由

原址：`tools/tests/test_windowsapps_guard_bash_parity.py` docstring（搬遷前 L179-L187）。

```text
🔴 R82（`DEF-101-752`）：擴為 union 上 `-o --exclude-standard`——尚未 `git add`
的新 `.sh` 原本天生不可見（同 `test_platform_utils_dedup.py` 檔頭②事故形狀）。
本函式只餵「offender 必須為空」形態的掃描（`test_no_raw_unguarded_python_check_remains`
等），加寬掃描面只會多抓真違規，無副作用。**姊妹函式
`_tracked_non_sh_shell_scripts()`／`_tracked_files()` 刻意不比照**：它們餵的是
`test_hook_dir_roster_matches_repo_state` 這種「名冊 vs 實況」等值斷言，任何本機
未加入 git 的草稿 `.sh`（不論放在哪個目錄）都會被判成「名冊外的新 hooks 目錄」而
偽陽——那不是同一種掃描語意，需要拆成獨立判準才能安全擴面，非本輪處置範圍（見
帳本 `DEF-101-752` 該列）。
```

### §109 WindowsApps bash guard 行為測試：fixture 路徑由 bash 自身 `mktemp -d` 建立的緣由（R43 實測：磁碟機代號冒號腰斬 `$PATH`）

原址：`tools/tests/test_windowsapps_guard_bash_parity.py` docstring（搬遷前 L448-L455）。

```text
fixture 的暫存目錄與候選可執行檔全部由 **bash 自身**的 `mktemp -d` 建立，
不透過 Python `tempfile` 產生 Windows 樣式路徑（`C:\\Users\\...`）字面塞進
`$PATH`——R43 實測發現 `C:/...` 這類含磁碟機代號冒號的路徑塞進以 `:` 分隔的
`$PATH` 字串會被冒號本身腰斬（`C` 與 `/Users/...` 誤判為兩個獨立、皆不存在
的路徑片段），導致 fixture 目錄從未真正被搜尋到、`command -v python` 悄悄
改為命中繼承自呼叫端行程環境的其他 `python`（如已啟用的 `.venv`），使本測試
看似「跑過」卻完全沒驗證到目標邏輯——與本輪（R43 baseline agent）在真實
`test_bash_probe_spec_contract.py` 上踩到的路徑格式陷阱同一根因類別。
```

### §110 WindowsApps bash guard：`_CALLER_FILES` R55 新增一支——原登記於 `_EXEMPT_SH_FILES` 的豁免理由論證方向錯誤

原址：`tools/tests/test_windowsapps_guard_bash_parity.py` 註解（搬遷前 L104-L108）。

```text
R55 新增：原登記於 _EXEMPT_SH_FILES，豁免理由「WindowsApps 資料夾不可能
出現在 macOS PATH 上」論證方向錯誤——真正風險是本腳本是否會被跑在
Windows 上，而腳本自身檔頭（[2b] 段落註解、`-c core.longpaths=true`
註解）與根層 ONBOARDING.md 皆記載過 Windows Git Bash 實跑情境，已改用
共用 guard。
```

### §111 歸檔判準③：R68 改寫（DEF-101-676）——取代舊的 `assertNotIn(v["id"], claimed)`，改寫動機與代價量化

原址：`tools/tests/test_archive_defect_log.py` docstring（搬遷前 L635-L642）。

```text
判準③ 的 R68 改寫（DEF-101-676）：「被宣稱過」不再是 blocker，取而代之的義務是
「搬走後那句宣稱仍解析得到」。

取代舊的 `assertNotIn(v["id"], claimed)`：舊斷言把「被提過」永久等同「不可搬」，
危害其實是搬走後 `_scan_target()` 找不到；補上 `gate._load_archive_status()`
使帳本 SSOT 真正涵蓋主檔∪archive 家族後，兩者解耦。改寫動機與代價量化史料見
證據檔〈第七輪 史料搬遷（Dev-Trim8）〉。本條正向驗證新義務：對每一筆「被宣稱過
＆ 可搬」的列，斷言它在帳本家族內解析得到且狀態與宣稱一致。
```

### §112 歸檔樣本座標鎖：為何需要（那句話原本不寫樣本住哪一支檔，被以主檔為掃描面的複查讀成 stale）

原址：`tools/tests/test_archive_defect_log.py` docstring（搬遷前 L3355-L3357）。

```text
為何需要（本輪實證）：那句話原本只寫「實測家族內…」而不寫樣本住哪一支檔，
於是一次以**主檔**為掃描面的複查把它讀成 stale（樣本其實住 archive）。
一句對的話因為缺座標而被讀成錯的，下一次就可能被「順手訂正」成真的錯的。
```

### §113 root-infra 對等鎖：R56 立案——檔頭第 1 道敘述是被指定的真相源卻在掃描面擴張時漏改（R54 DEF-101-431／R55「9 支」同形狀）

原址：`tools/tests/test_root_infra_parity.py` docstring（搬遷前 L175-L182）。

```text
R56 新增（Architect 與 SA 各自獨立回報同一根因）：檔頭第 1 道敘述是
ONBOARDING.md §6 明文指定的權威來源（原文「詳細內容以 workflow 檔頭註解
為準，避免每次擴充都要同步改動兩處」）。R56 把該 step 的掃描面由
`find tools`（10 檔）擴為全庫 `git ls-files`（174 檔）時檔頭漏改，被指定
的真相源反而成了錯的一方；同形狀的「多站點敘述漂移」本 repo 已連踩四輪
（R54 DEF-101-431／R55「9 支」／本輪 pre-push「五支」）。故機械斷言：
step **非註解行**採用的掃描機制關鍵字，必須同時出現在檔頭第 1 道敘述裡
——未來任一方向擴面/縮面而檔頭沒跟上即紅。
```

### §114 帳本交叉參照鎖：R75 把指針樣式由「只認 R60 那一組檔名」放寬為任一輪的 `CrossPlatform_R<n>_*.md`（R60／R68／R75 兩層化）

原址：`tools/tests/test_check_defect_log_crossref.py` 註解（搬遷前 L1075-L1079）。

```text
🔴 R75：樣式由「只認 R60 那一組檔名」放寬為**任一輪的 `CrossPlatform_R<n>_*.md`**。
原因與 DEF-101-757 同型：兩層化（主檔留摘要＋指針、詳情外置）R60 用過、R68 用過、
R75 又用了一次（`CrossPlatform_R75_Review_Evidence.md`，20 個具名節指針），而本鎖的
樣式把輪號寫死 ⇒ 同一種指針換一輪就整批逸出，這正是本鎖要防的「指針靜默失實」。
放寬只擴**發現面**，判準（錨必須真的存在於被指名的那份檔）一字未改。
```

### §115 smoke ↔ CI 同步：`--workflow` 接上後第一次真跑踩到的假綠（act 對事件對不上的 workflow 不跑任何 job 卻回 rc=0；全庫 5/11 支 on: 不含 push）

原址：`tools/tests/test_smoke_ci_sync.py` docstring（搬遷前 L1199-L1203）。

```text
WHY 這條非有不可：本輪把 `--workflow` 接上之後，第一次真跑就踩到——act 對事件
對不上的 workflow 是「不跑任何 job 然後回 rc=0」，畫面上只有一行 `Using docker
host`。實測逐字：`--workflow …arch-fitness.yml --job pr-advisory` → ACT_RC=0、
零 job 執行。全庫 11 支裡有 5 支的 `on:` 不含 push ⇒ 把 workflow 指得到這件事
**本身**讓這個假綠第一次變得碰得到，兩者必須同批落地。
```

### §116 Windows 禁用檔名鎖：構造形判準的 WHY——R60 插入新裝置名使間隙由 ≤5 變 17，三處實作同時掉出錨①而註冊表等值斷言毫無反應

原址：`tools/tests/test_windows_forbidden_filename_parity.py` docstring（搬遷前 L733-L738）。

```text
WHY：姊妹鎖取兩錨聯集，只要禁用字元集合的錨②還命中，某份實作掉出錨①也
照樣全綠——R60 插入新裝置名到中間造成間隙從 ≤5 變 17 時，三處實作同時
掉出錨①，註冊表等值斷言毫無反應。改認構造形：管線分隔、四名之間不得有
任何其他字元。殘留 fail-open（如實揭露）：註解裡的偽裝字樣仍可滿足本鎖，
徹底根治需 AST 解析四種語言（R46 已證明無底洞），本鎖只攔「無意識插中間」
這個真實發生過的動作。史料見證據檔〈第七輪 史料搬遷（Dev-Trim8）〉。
```

### §117 Windows 禁用檔名鎖：logger.py 以 rsplit 剝副檔名而漏判多重副檔名保留名（R33 QA 二審、DEF-101-295 追加修復）

原址：`tools/tests/test_windows_forbidden_filename_parity.py` 註解（搬遷前 L313-L316）。

```text
R33 QA 二審發現：logger.py 原用 rsplit(".", 1) 剝副檔名（只切最後一個點），對多重
副檔名的保留名（如 lpt5.tar.gz）算出 stem="lpt5.tar" 而漏判；check_ntfs_paths.py／
bash 皆用「第一個點起」剝離（split(".", 1) / ${seg%%.*}），三者對此不對稱。已改
logger.py 為 split(".", 1) 與另兩處一致（DEF-101-295 追加修復）。
```

### §118 platform_utils 收斂止血鎖：模組 docstring 的立案沿革（R16 架構最佳化、R66 DEF-101-629、R70 DEF-101-751／752）

原址：`tools/tests/test_platform_utils_dedup.py` 模組 docstring（搬遷前 L4-L13）。

```text
本測試機械鎖住三件事：(1) `platform_utils` 模組本身 API 存在且行為正確（兩平台皆
`_init_utf8_streams()` 無條件包裝，見 `test_hooks_stdin_utf8.py`：POSIX 上不強制重新
包裝會讓阻斷級 hook 的中文錯誤訊息讀成亂碼）；(2) 8 個已知呼叫點不再各自定義
`_init_utf8_streams()`；(3) `resolve_latest_name`／`resolve_latest_root`／
`exclude_frozen_sdd_versions` 三函式 repo-wide 唯一定義鎖（R66 追加，DEF-101-629）。
不變量以「**每一個相依孤島內，各 helper 只准有一個定義點**」為界（R70／DEF-101-751：
`autoclaude` 為可獨立 pip 安裝套件，跨孤島各留一份＋以鎖釘住一致性），掃描面涵蓋
tracked ∪ untracked-not-ignored（R70／DEF-101-752：untracked 天然不可見曾讓衝突躲過
四輪複審）。史料見 CrossPlatform_DEF200275_Context_Metering_Evidence.md
〈第七輪 史料搬遷〉。
```

### §119 掃描面盲區封閉鎖：R85／QA-06 探針由 repo 根改造在拋棄式 git repo 內的緣由（pid 只讓自己的目錄唯一，擋不住別的行程掃到探針）

原址：`tools/tests/test_platform_utils_dedup.py` docstring（搬遷前 L676-L680）。

```text
🔴 R85／QA-06：探針改造在**測試專屬的拋棄式 git repo** 內，共用工作樹零足跡。
此前它造在 repo 根（`_scan_surface_probe_<pid>/`）——pid 只讓**自己**的目錄唯一，
擋不住「別的行程掃到我的探針」：探針依定義是一支違規檔，而本檔的掃描面是全 repo
⇒ 並行時互相污染（QA 實測 traceback 裡的 pid 不屬於報錯的那個行程，兩種載具的
失敗支數因此對不起來）。拋棄式 repo 讓污染在**結構上**不可能，不是靠清理得夠快。
```

### §120 掃描面盲區封閉鎖：事故本身——`platform_caps.py` 在 R69 全程 untracked 而躲過四輪四方複審與多次全套實跑（R70／DEF-101-752）

原址：`tools/tests/test_platform_utils_dedup.py` docstring（搬遷前 L666-L670）。

```text
事故本身：`platform_caps.py` 在 R69 全程是 untracked，而本檔的掃描面是
`git ls-files`（tracked-only）。於是它與 R17 不變量的衝突躲過了**四輪四方
複審**、以及收尾者多次 `run_root_unittests.py` 全套實跑（皆 `Ran 1581 … OK`），
直到 `git add -A` 讓它變成 tracked 的**那一刻**才在 pre-push 顯形。
⇒「驗證載具自己有盲區」的教科書級樣本：不是鎖寫錯，是鎖**看不到**該看的地方。
```

### §121 bootstrap_core pick_python() WindowsApps 空殼排除 guard 回歸鎖：WHY 全文（DEF-101-273/279 兩輪修復、R16 架構收斂後缺 guard、R31 補齊）

原址：`tools/tests/test_bootstrap_core.py` 模組 docstring（搬遷前 L4-L11）。

```text
WHY：`tools/bootstrap.ps1` 在 DEF-101-273/279 兩輪修復中，對 `python`/`python3`
裸名候選加了 WindowsApps 空殼別名靜態路徑排除 guard——全新 Windows 11 機器上這兩個
名字常被系統自動註冊為 App Execution Alias 空殼，`shutil.which()`/`Get-Command`
找得到、但實際執行只會跳出 Microsoft Store 安裝提示，不會執行任何 Python 碼；用
「執行結果」判斷（`_probe_ok()`）在此情境不可靠，正是 `.ps1` 改用靜態路徑比對的
原因。但作為「單一真相源」的 `bootstrap_core.py::pick_python()`（R16 架構收斂後
真正決定建立 `.venv` 用哪個直譯器的核心邏輯）此前完全沒有這道 guard，本測試鎖住
R31 補齊的對稱修復，防未來退化回舊版純執行探測判斷。
```

### §122 subprocess 編碼鎖：WHY 這道到 R74 才出現——判準一（parent 解碼）合規的那一行 hook 在 windows-latest（cp1252）把中文指引印成亂碼（DEF-101-789）

原址：`tools/tests/test_subprocess_encoding_hygiene.py` docstring（搬遷前 L657-L661）。

```text
WHY 這道到 R74 才出現：判準一（parent 解碼）2026-07-19 就上線了，而出事那一行
對它完全合規——`text=True` 有 `encoding="utf-8"`、有 `errors="replace"`。
repo 只守了一半，另一半連判準都沒有，於是 `.claude/hooks/block_bash_on_windows.py`
在無保護狀態下漂了一整輪，直到 GitHub windows-latest（en-US ＝ cp1252）把
整段中文指引印成 `\\uXXXX` 才被看見（DEF-101-789）。
```

### §123 hook 註冊普查：R79 由並行包新增的 PreToolUse 條目（`.claude/settings.json` 不在本包所有權內）的交接註記

原址：`tools/tests/test_check_hooks_liveness.py` 註解（搬遷前 L1830-L1834）。

```text
🔴 R79 由**並行的另一個包**新增的 PreToolUse 條目（`.claude/settings.json` 不在
本包的檔案所有權內，本包只負責讓帳對得上——同 `_SITE_CLASS_CENSUS` 的既有紀律）。
語意是「動手**之前**先看水位」，圈的是三個會一次吃掉大量 context 的工具。
收輪者請依當場實測重驗這一格：若那個包最後把條目撤掉，本列必須跟著撤，否則
棘輪會對著一個不存在的註冊喊紅。
```

### §124 Windows nightly 安裝器：R73（DEF-101-779）原本斷言 help 區塊含某個時刻字面值而把觸發時間釘進鎖裡（ADR-SD09-012 五項排程設定連兩輪沒人敢套）

原址：`tools/tests/test_install_windows_nightly.py` 註解（搬遷前 L233-L239）。

```text
🔴 R73（DEF-101-779）：原本斷言 help 區塊含某個時刻字面值，即把觸發時間**釘進鎖裡**
釘進鎖裡。那個字面值與本機實際排程（22:30）不符，而 install 路徑是
Unregister→Register ⇒ 「跑安裝器套設定」會靜默把時間改掉，於是 ADR-SD09-012
點名的五項排程設定連兩輪沒人敢套。時間改為參數後，鎖要釘的是**結構**：
兩個 trigger 都必須吃參數（不得再回頭寫死），且參數都要有格式驗證。
刻意**不**斷言預設值等於本機現行排程——那會把「這台機器排幾點」寫成鎖的常數，
正是 DEF-101-777 同一個病（見 test_ps_engine_ssot.py::TestNoStaleLocalEngineClaims）。
```

### §125 dev_start：DEF-101-762 在 LATEST 版 SDD 樹上的兩個同形態站點（以 `git rev-parse` 輸出反推路徑，cp950 下損毀）與 R71 參數化到第二支

原址：`tools/tests/test_dev_start.py` 註解（搬遷前 L5948-L5952）。

```text
DEF-101-762 在 LATEST 版 SDD 樹上的**兩個**同形態站點：都以 `git rev-parse` 的輸出反推
路徑，cp950 下損毀即整條路不可用。R71 落地時只鎖了 install_post_commit.ps1，run_tlc.ps1
雖已同法修好，卻只有 `check_script_parity._LATEST_PINNED_SHA256` 的 hash 釘選——那只證明
「內容沒被動過」，證明不了「釘選在讀取之前」，而後者正是本缺陷的形狀。「同棵樹、同形態、
只鎖一支」就是 DEF-101-757 入規要防的鎖射程缺口，故 R71 參數化到第二支（成本＝一個 case）。
```

### §126 check_script_parity 具名輪次正控樣本：E-05／R77-13 訂正——原本寫死一個不存在的輪號（與「未指派」等效的假承諾），改自帳本現查當前輪推導下一輪

原址：`tools/tests/test_check_script_parity.py` docstring（搬遷前 L1467-L1470）。

```text
🔴 本輪（E-05／R77-13）訂正：具名輪次的正控樣本原本寫死一個**不存在的輪號**，
於是這支「證明合法寫法會通過」的對照組，用的是一個與『未指派』等效（永遠不到
期）的假承諾當範例——判準的正控自己就是它該擋的東西。改為自帳本現查當前輪推導
下一輪，樣本因此永遠是「真的可能被排進來」的那一個，且不隨輪次推進而過期。
```

### §127 check_script_parity：R80 S5-05——原本逐一寫 `patches[0]…patches[5]` 六個索引（`_patched()` 少回一個元素時是 IndexError 而非有意義的紅燈），改用 ExitStack 依實際長度展開

原址：`tools/tests/test_check_script_parity.py` 註解（搬遷前 L140-L143）。

```text
🔴 R80 S5-05：原本逐一寫 `patches[0]…patches[5]` 六個索引。`_patched()` 少回一個
元素（本輪刪掉已死的 _MARKER_PAIRS 名冊）時，這裡是 IndexError 而不是有意義的
紅燈——索引數字是這個 helper 與它的生產者之間第二個必須手動同步的家。改用
ExitStack 依實際長度展開，數量從此只有一個家。
```

### §128 PS 5.1 相容鎖：R56 round 5 修正（QA B-3）——`keys_and_floors_pinned` 名實不符，只比 keys、`_floor` 從未進入斷言

原址：`tools/tests/test_ps51_compat.py` docstring（搬遷前 L408-L411）。

```text
R56 round 5 修正（QA B-3）：本方法名為 `keys_and_floors_pinned`，實作卻只
比 keys、`_floor` 從未進入斷言——名實不符會誤導後續審查員以為下限已受保護
（現況 8/7/2/4 與實數零餘裕，縮面雖仍會被上一支測試的 assertGreaterEqual
擋下，但「下限值本身被下修」這條路徑當時零訊號）。改為連 floor 一起釘。
```

### §129 claim provenance 第三判準：規格版紅綠自證（插入 4 小時前的『量測於』⇒ 回空清單）把事故寫成契約，「在場即抑制」型抑制器在整個母體上一次都沒做對過

原址：`tools/tests/test_claim_provenance_r86.py` docstring（搬遷前 L386-L389）。

```text
規格版寫的紅綠自證是「插入 4 小時前的『量測於』⇒ 回空清單」——那**把事故寫成契約**：
立案的事故形狀就是「把四小時前的 pace 區塊整塊貼上」，而那份規格會讓那個動作**變成
合法的靜音手法**。複審量到的代價：在整個母體上，「在場即抑制」型抑制器**一次都沒有
做對過** ⇒ 它不是逃生口，是隨機靜音器。
```

### §130 sanitize 凍結版鎖：R44 QA 一審發現的時序缺陷——初版用 `git show HEAD:<path>`，本輪修復一旦 commit 就對全部 7 個 subTest 恆紅，改錨定固定 SHA

原址：`tools/tests/test_sanitize_component_frozen_sdd_versions_lock.py` docstring（搬遷前 L209-L213）。

```text
R44 QA 一審發現並修正的時序缺陷：初版用 `git show HEAD:<path>` 而非固定
SHA，這個假設只在『本輪修復尚未 commit』的當下短暫成立——一旦本輪修復
（含本測試檔自身）被 commit，HEAD 就會變成『修復後』內容，導致
`test_every_target_file_pre_fix_head_content_fails_the_lock` 對全部 7 個
subTest 恆紅。改錨定固定 SHA 後，重放內容不再受後續任何 commit 影響。
```

### §131 sanitize 凍結版鎖：bug-injection「修復前」重放基準點固定錨定在 DEF-101-357 修復前的父提交（R43 收尾 commit），不用 `git show HEAD:<path>`

原址：`tools/tests/test_sanitize_component_frozen_sdd_versions_lock.py` 註解（搬遷前 L85-L93）。

```text
bug-injection 鑑別力鎖的「修復前」重放基準點——固定錨定在本輪 DEF-101-357
修復（29 版 × 7 檔 203 處改動）尚未提交前的父提交（R43 收尾 commit），刻意
不用 `git show HEAD:<path>`（R44 QA 一審發現：HEAD 會隨每次 commit 移動，
一旦本輪修復——含本測試檔自身——被 commit，HEAD 就變成『修復後』內容，
`TestExpectedSanitizeCallDiscriminatesRealHistoricalRegression` 會對全部 7
支檔案恆紅，而非只在本輪修復提交前這段短暫視窗內成立）。改用此固定 SHA 後，
該測試永遠重放同一段『修復前』真實歷史內容，不受後續任何 commit 影響；若此
commit 在未來因淺層 clone（CI `actions/checkout` 預設 fetch-depth=1）或歷史
重寫而不可達，`_pre_fix_baseline_text()` 會 skipTest（非 fail-red）。
```

### §132 dev_start mac nightly 鎖：R59 ARCH-R59-04——原寫 `.split("/")[-1]` 只鎖檔名不鎖目錄，鎖目錄搬走而檔名不變時本鎖照綠、DEF-101-504 復發且零訊號

原址：`tools/tests/test_dev_start.py` 註解（搬遷前 L996-L1000）。

```text
R59 ARCH-R59-04：原寫 `.split("/")[-1]`＝只鎖檔名 `.nightly_mac.lock`，
不鎖目錄。把 `.sh` 的鎖目錄從 AutoClaude/logs/ 搬到別處而檔名不變 → 本鎖照樣
綠，而 `_nightly_running()` 會永遠在錯的路徑找不到鎖、回 False＝假「沒在跑」，
DEF-101-504 原樣復發且零訊號。這是「鎖自己留了一個它宣稱要守的洞」，且與同一
測試 Windows 側鎖完整 Mutex 字面值的做法不對稱。改鎖完整相對路徑。
```

### §133 DEF-200-481：lint 規則①換成真機三條件判準——devB 從 `.claude/hooks/lint_powershell_command.py` 等檔刪除／改寫的原文（逐字，行號＝HEAD 版）

原址：`.claude/hooks/lint_powershell_command.py`／`tools/probe/audit_session.py`／`tools/lib/rc_after_pipe_real.py` 一帶（R194 五方迭代中該 Developer 從 hook／lib 刪下的散文，原樣保全；內文自帶的 `##`／`###` 小標與圍欄為原檔結構，故以長圍欄包住）。

``````text
# devB 刪除的原文（逐字；行號＝HEAD 版）

DEF-200-481：lint 規則①換成真機三條件判準。下列為被刪／被改寫的原文，供收尾者搬進沿革檔。

## .claude/hooks/lint_powershell_command.py

### E1 module docstring 指標（改寫處的原句只有一行，原樣保留在新文字內）（HEAD L22-L22）

````text
不必去動註冊面。
````

### E2 SHARED_PATTERN_SOURCE['pipe-cmdlets'] 條目（含 R78／SA-01 註解）（HEAD L164-L177）

````text
    # 管線接進這些 cmdlet 之後再讀 rc，才算命中（不是看到任何 `|` 都算）。
    # 🔴 R78／SA-01：**內建別名與全名同列**。上一版只列全名，實測 12 組「別名 vs
    # 全名、其餘字元逐字相同」的配對 **12/12 不對稱**（`| select -First 5` 放行、
    # `| Select-Object -First 5` 擋下）——而 `select` 正是「提前結束管線」最常見的
    # 寫法，等於這道鎖擋掉的剛好是沒人會寫的那一半。每個別名自帶右邊界
    # `(?![\w-])` 以免吃到 `selection`／`sortable`；`%` 與 `?` 另用 `(?=\s|\{|$)`，
    # 避免誤傷 `$_ % 2` 那類真正的運算子用法。
    "pipe-cmdlets": (
        r"(?:Select-Object|Select-String|Out-\w+|Format-\w+|Sort-Object"
        r"|Measure-Object|ForEach-Object|Where-Object|Tee-Object"
        r"|head|tail|findstr)(?![\w-])"
        r"|(?:select|sls|sort|measure|foreach|where|ft|fl|oh|tee)(?![\w-])"
        r"|[%?](?=\s|\{|$)"
    ),
````

### E3 _PIPE_INTO_RE／_RC_READ_RE／R79 偏向擋辯護／_statement_resets_rc（HEAD L202-L238）

````text
_PIPE_INTO_RE = re.compile(
    r"\|\s*(" + SHARED_PATTERN_SOURCE["pipe-cmdlets"] + r")", re.IGNORECASE
)
_RC_READ_RE = re.compile(r"\$LASTEXITCODE", re.IGNORECASE)
#: 「rc 已被重新建立」——**真的發起了一次呼叫**。用途見 `_rc_after_pipe()`：
#: 截斷管線造成的污染會**一直延續**，但 hint 教的正解 `& <exe> <args>; "rc=$LASTEXITCODE"`
#: 本來就會重設 rc，不該被前面某一句的管線牽連。
#:
#: 🔴 R79：上一版把「重設」判太寬，而寬的方向正是這條規則存在的唯一理由的反面
#: （放行一條會讓真 rc=7 被讀成 0 的指令）。兩個口子都是「提到」而非「執行」：
#:   · 呼叫運算子的左邊界只排除 `&` 與英數字 ⇒ `2>&1`／`1>&2` 的那個 `&`（左邊是 `>`）
#:     被當成呼叫。`2>&1` 在最近 12 支逐字稿的 547 條 unique 指令裡佔約一半，觸發面極大。
#:   · `.exe` 出現在**任何位置**都算 ⇒ `Get-Command python.exe`、`Test-Path …\cmd.exe`
#:     這種只是把路徑當資料的語句被當成執行。
#: pwsh 7.6.4 真機實測：這三種語句一個都沒有重設 `$LASTEXITCODE`（前值原樣保留）。
#: 修法是把兩個口子各自收到「命令位置」上：
#:   ① 呼叫運算子的左邊界加上 `>`，把重導向合併排除；
#:   ② `.exe`／`.cmd`／`.bat` 只在**語句的第一個 token** 才算數（`_NATIVE_HEAD_RE`）——
#:      那才是「這一句在跑一支外部執行檔」，寫在參數位置的同一個字面只是資料。
#: 仍然刻意窄：裸原生指令（`git status` 這種不帶 `&`、不帶副檔名者）**不算**重設，
#: 於是判定偏向擋。這個方向是刻意的——「同一個指令字串裡既有截斷管線又要讀 rc」
#: 本身就是這條規則要消滅的混寫，而行內豁免是它的出口。
#: 誠實劃界：偏向擋的代價已在真實語料上量過（見 `tools/tests/test_check_hooks_liveness.py`
#: 的 `TestLintPowerShellHookBehaviour` 兩向表），不是靠推測。
_RC_RESET_RE = re.compile(r"(?<![&\w>])&(?!&)\s*\S", re.IGNORECASE)
#: 語句**開頭**就是一支外部執行檔（`python.exe a.py`／`<venv>/bin/tool.cmd`）＝真的在跑東西。
#: 錨在開頭是關鍵：`Get-Command python.exe` 的第一個 token 是 cmdlet，`.exe` 只是參數。
_NATIVE_HEAD_RE = re.compile(r"^\s*[^\s;|&]*\.(?:exe|cmd|bat)(?![\w])", re.IGNORECASE)


def _statement_resets_rc(statement: str) -> bool:
    """這一句是否真的重新發起了一次呼叫（⇒ `$LASTEXITCODE` 被重寫）。

    純函式、吃**一句**（不是整條指令）：`.exe` 的「必須在開頭」這個條件只有在語句
    邊界上才判得準，用 `search(..., pos, endpos)` 是判不到的（`^` 不會錨在 `pos`）。
    """
    return bool(_RC_RESET_RE.search(statement) or _NATIVE_HEAD_RE.search(statement))
````

### E4a _RC_HINT（HEAD L251-L257）

````text
_RC_HINT = (
    "🔴 讀 rc 不要接管線。pwsh 7.x 提前中斷管線時**不更新** $LASTEXITCODE（保留前一個值，"
    "真 rc=3 可能讀成 0＝真紅被讀成綠）；PS 5.1 則寫入 -1；加 2>&1 又會翻轉。"
    "沒有方向可以憑記憶——就是不要接。\n"
    "  出口：& <exe> <args>; \"rc=$LASTEXITCODE\"   ← rc 自成一句，前面那一句不接任何管線\n"
    "  要篩輸出就先落檔或分兩次呼叫；要一支固定 rc 語意的載具走 tools/probe/。"
)
````

### E4b _HEADER／_FOOTER（HEAD L278-L286）

````text
_HEADER = (
    _SCOPE + "要就地寫出這個形態？加行內豁免 `# ps-lint-ok: <理由>`（理由必填）即放行——"
    "寫文件／寫探針／重現缺陷本來就會寫出違規形態，那不是違規。\n"
    "以下是本次命中的項目：\n\n"
)
_FOOTER = (
    "\n（刻意極窄：本守衛只擋這三件事，其餘一律放行——誤報讓機制被整個關掉，"
    "比漏擋更糟。回歸鎖：tools/tests/test_check_hooks_liveness.py）"
)
````

### E5 _rc_after_pipe（含 R78／R79 長 docstring）（HEAD L427-L455）

````text
def _rc_after_pipe(structural: str, expandable: str) -> bool:
    """規則①：**先後順序**與**跨語句污染**都算數。

    上一版兩個方向都錯：
    · 漏擋（SD-01）——只看「緊鄰的下一句」（`parts[index + 1]`），中間插任何一句
      就逃出視窗，而 `$x = 1` 這種句子根本不會重設 `$LASTEXITCODE`，rc 照樣是髒的。
      改成污染會**一直延續**到某一句真的重新發起呼叫（`_RC_RESET_RE`）為止。
    · 誤擋（QA-01）——`"rc=$LASTEXITCODE" | Out-File` 是先展開變數再進管線，
      rc 讀取發生在任何管線中斷**之前**，完全安全卻被硬擋，因為判準只問「同一句
      有沒有同時出現」不問先後。改成比位置：rc 在管線**之後**才算命中。

    🔴 R79：污染的**解除**條件改由 `_statement_resets_rc()` 判（吃一句、不吃座標）。
    上一版把「提到一支 exe」與「`2>&1` 裡的 `&`」都當成呼叫，於是一句話就能把污染
    旗標清掉——而清掉之後放行的，正是這條規則唯一要防的那件事。
    """
    contaminated = False
    for start, end in statement_spans(structural):
        pipe = _PIPE_INTO_RE.search(structural, start, end)
        pipe_pos = pipe.start() if pipe else -1
        for read in _RC_READ_RE.finditer(expandable[start:end]):
            if contaminated or (pipe_pos >= 0 and start + read.start() > pipe_pos):
                return True
        if pipe_pos >= 0:
            contaminated = True
        elif _statement_resets_rc(structural[start:end]):
            contaminated = False
    return False


````

## tools/lib/rc_after_pipe_real.py

### 舊檔頭 docstring（L1-L50）（HEAD L1-L50）

````text
"""`rc-after-pipe-real` 判準本體（R80／S7-01＋S7-09）——「真的會量到假 rc」的那一欄。

為何住在 `tools/lib/` 而不是 `tools/probe/audit_session.py` 裡（R80 收尾包移出）：
消費端受根層 `guardrail_cli<=750` 的 LOC 分級管，而該分級的合法出口逐字寫著
「先拆職責／抽共用模組（先例：tools/lib/ci_liveness.py），確認為不可壓縮的真實功能後
才具名調高」。本模組就是那個「拆職責」——它是一組**純函式＋一張實測語料表**，與逐字稿
掃描、報表、CLI 全無耦合，本來就該獨立。**不得**為了讓它留在原地而調高 LOC 上限。

依賴注入：兩支判準要用攔截端（`.claude/hooks/lint_powershell_command.py`）的純函式，
但那支 hook 只能是**被借的一方**（它由 `runpy.run_path` 起、`sys.path` 上沒有 `tools/`，
import 期爆掉會破壞它的 fail-open 契約）。故本模組**不自己載入 hook**——由呼叫端把已載入
的 hook 模組傳進來。這也避免了「同一份載入邏輯住兩個家」。

──────────────────────────────────────────────────────────────────────────
🔴 S7-01＋S7-09：把「攔截端會擋什麼」與「真的會量到假 rc 幾次」拆成兩欄
──────────────────────────────────────────────────────────────────────────
上一欄（`rc-after-pipe`）＝攔截端那支函式本身。R79 把它借過來，理由是「兩端不會
再漂移」——那件事達成了，但它同時把**攔截端刻意保守的偏擋**整批灌進了量測數字，
而那個數字正是拿來對根 CLAUDE.md 下結論用的。攔截端偏擋是對的（誤報有行內豁免
當出口，漏擋沒有）；量測器偏擋不是——它會讓「這條規則有多少真違規」整整高一個
數量級，而下結論的人看到的是量測器。

R80 pwsh 7.6.4 真機逐形態實測（腳本與逐字輸出見交件的證據檔），seed 一律先灌 7、
再看 `$LASTEXITCODE` 有沒有被寫成 git 的真 rc(0)：

  git log … | Select-Object -First 1   → after=7  ← STALE：真 rc 完全沒被寫入
  git log … | select      -First 1     → after=7  ← 同上（別名）
  git log … | Select-Object -Index 0   → after=7  ← 同上
  git log … | Select-String / Sort-Object / Measure-Object / ForEach-Object
            / Where-Object / Out-Null / Out-String / Format-Table / Tee-Object
            / % {…} / findstr           → after=0  ← 全部正確寫入，一個都不污染
  git log … | Select-Object -Last 1 / -Skip 1 / -First 1 -Wait / -First 999
                                       → after=0  ← 不提前結束管線就不污染
  $v = git log …; $v | Select-Object -First 1 → after=0 ← 左邊是變數不是原生指令

⇒ 真正會產生「真紅被讀成綠」的條件是三個**同時**成立，不是「看到管線就算」：
  ① 管線左段真的在跑一支**外部執行檔**（cmdlet 管線根本不碰 `$LASTEXITCODE`）；
  ② 管線接進的是**會提前結束**的元素（實測只有 `-First N`／`-Index N`，且 `-Wait`
     會取消提前結束、`-First N` 在 N 大於輸出筆數時也不會）；
  ③ 之後才讀 `$LASTEXITCODE`。

本 repo 逐字稿全母體實測（見報表的量測窗）：`rc-after-pipe` 152 命中裡有 139 筆
（91.4%）不滿足這三條 ⇒ 那一欄**不可**被引用成「違規次數」。誤報的大宗正好是根
CLAUDE.md 逐字教的正解形態（`& <exe> …; "rc=$LASTEXITCODE"` 之後另起一句用管線
篩輸出）——方向是「越遵守規則、違規率越高」，用它做的歸因符號相反。

🔴 兩欄都留、都印，不合併：`rc-after-pipe` 是**對拍錨**（`--parity` 與
`TestHookAndProbeShareOneCriterion` 靠它證明兩端沒漂移），`rc-after-pipe-real`
是**唯一可引用為「量到幾次真風險」的那一欄**。
"""
````

### 被刪的判準函式與舊自證語料註解（含 S7-09 史料）（HEAD L57-L160）

````text
#: 實測會提前結束管線的元素。`-Wait` 明確排除（實測 after=0）。
#: 刻意**不**收 `head`：pwsh 沒有這個指令，它只在 Bash 工具面成立而那一面另有鐵律一。
_TRUNCATING_PIPE_RE = re.compile(
    r"\|\s*(?:Select-Object|select)(?![\w-])"
    r"(?![^|;\n]*-Wait(?![\w-]))"
    r"[^|;\n]*?(?:-First|-Index)(?![\w-])",
    re.IGNORECASE,
)

#: 語句開頭若是這些字，那**不是**外部執行檔（PowerShell 內建別名／關鍵字）。
#: 這張表是「裸原生指令偵測」的偽陰性面：漏收一個別名就會把它誤判成原生呼叫、
#: 進而誤以為污染被清掉（＝漏報方向）。刻意只收**真的會出現在語句開頭**的那些。
_PS_ALIAS_HEADS = frozenset("""
echo ls dir cat type cd chdir sl rm del ren cp copy move mv pwd md mkdir rmdir
select sort where foreach measure sls gc sc gi gci gcm gm iwr irm man help cls
clear history kill ps sleep tee write ft fl oh popd pushd gal sal gp sp gv sv
rv ni ri mi ci gl gu nal compare diff group set get new test out format
""".split())
_PS_KEYWORD_HEADS = frozenset("""
if else elseif for foreach while do switch try catch finally function param
return throw break continue begin process end filter class enum using exit
trap data dynamicparam hidden static
""".split())
_STATEMENT_HEAD_RE = re.compile(r"^\s*(?:&\s*)?['\"]?([A-Za-z][\w.\\/:-]*)")


def head_is_native_invocation(statement: str) -> bool:
    """語句開頭是不是一支**外部執行檔**（⇒ 它會重寫 `$LASTEXITCODE`）。

    🔴 S7-09：攔截端的 `_statement_resets_rc()` 明文把「裸原生指令（`git status`
    這種不帶 `&`、不帶副檔名者）」判成**不算**重設，並自陳那是刻意偏擋。pwsh 7.6.4
    實測那句話是假的——`& cmd /c exit 7` 之後跑 `git status`，`$LASTEXITCODE` 由 7
    變成 0；`git nosuchsubcmd` 變成 1；`cmd /c exit 3` 變成 3。跨語句實測同樣成立：
    `git … | Select-Object -First 1` 造成的污染，被下一句裸 `git status` 清乾淨
    （after=0），被 `$x = 1` 清不掉（after=7）。
    ⇒ 攔截端偏擋的**代價方向**與它自陳的相反：它不是「多擋一點」，是把污染的存續
    區間算得比實際長，於是同一條指令後面所有的 rc 讀取都被判成違規。這個代價此前
    從未從量測數字裡扣掉，本函式就是扣掉它的地方。

    判準（誠實劃界）：帶 `.exe`／`.cmd`／`.bat` 副檔名 → 是；含 `-` 的 token 視為
    Verb-Noun cmdlet → 否；其餘裸字若不在內建別名／關鍵字表裡 → 視為外部執行檔。
    這是**啟發式**：使用者自訂函式（`function gp { … }` 之後寫 `gp`）會被誤判成原生
    呼叫（偽陽性、方向是漏報）。表本身是偽陰性面，見 `_PS_ALIAS_HEADS`。
    """
    match = _STATEMENT_HEAD_RE.match(statement)
    if not match:
        return False
    token = match.group(1)
    if re.search(r"\.(?:exe|cmd|bat|com)$", token, re.IGNORECASE):
        return True
    base = token.rsplit("\\", 1)[-1].rsplit("/", 1)[-1].lower()
    if "-" in base:  # Verb-Noun ＝ cmdlet，不是外部執行檔
        return False
    return base not in _PS_ALIAS_HEADS and base not in _PS_KEYWORD_HEADS


def statement_invokes_native(statement: str, hook: Any) -> bool:
    """這一句有沒有真的發起一次外部呼叫（＝`$LASTEXITCODE` 被重寫）。

    攔截端那兩個條件（呼叫運算子 `&`、`.exe` 開頭）**原樣沿用**，另補上實測證明
    會重設的第三種：裸原生指令。三者取聯集，不是另起一套。
    """
    return bool(
        hook._RC_RESET_RE.search(statement)
        or hook._NATIVE_HEAD_RE.search(statement)
        or head_is_native_invocation(statement)
    )


def rc_after_pipe_real(command: str, hook: Any) -> bool:
    """實測會產生**錯的 rc 讀數**的形態（上游原生 × 截斷型管線 × 之後讀 rc）。

    與 `rc-after-pipe`（＝攔截端那支函式）的差別只有兩處，兩處都由真機實測支撐
    （見本檔檔頭）：
      · 管線元素收窄到**實測會提前結束**的那兩個參數，其餘 14 種一律不算；
      · 管線左段必須真的在跑外部執行檔，且污染的解除認得裸原生指令。
    """
    structural = hook.mask_regions(command, keep_expandable=False)
    expandable = hook.mask_regions(command, keep_expandable=True)
    contaminated = False
    for start, end in hook.statement_spans(structural):
        segment = structural[start:end]
        truncating = _TRUNCATING_PIPE_RE.search(segment)
        pipe_pos = -1
        if truncating and statement_invokes_native(segment[:truncating.start()], hook):
            pipe_pos = start + truncating.start()
        for read in hook._RC_READ_RE.finditer(expandable[start:end]):
            if contaminated or (pipe_pos >= 0 and start + read.start() > pipe_pos):
                return True
        if pipe_pos >= 0:
            contaminated = True
        elif statement_invokes_native(segment, hook):
            contaminated = False
    return False


#: 🔴 `rc-after-pipe-real` 的紅綠自證語料（`--selftest`，可重跑）。
#:
#: 每一列的 `expect` **不是我認為它應該是什麼**，而是 pwsh 7.6.4 真機量出來的：先
#: `& cmd /c exit 7` 把 `$LASTEXITCODE` 灌成 7，跑該形態，再讀一次——讀到 7 表示
#: 真 rc 根本沒被寫入（＝STALE＝這條規則要防的「真紅被讀成綠」），讀到 0/3 表示
#: rc 被正確寫入（＝安全）。`after` 欄記的就是那個實測值，改判準時請連它一起重測，
#: 不要只改 `expect`。本 repo 的紀律 #4：驗證載具本身要被驗證——這張表就是這道判準的
#: 那一層，而它此前不存在（判準整支向 hook 借，沒有任何一組已知答案在守它）。
````

## tools/probe/audit_session.py

### pipe-cmdlets 條目（含 R78／SA-01 註解）（HEAD L88-L101）

````text
    # 管線接進這些 cmdlet 之後再讀 rc，才算命中（不是看到任何 `|` 都算）。
    # 🔴 R78／SA-01：**內建別名與全名同列**。上一版只列全名，實測 12 組「別名 vs
    # 全名、其餘字元逐字相同」的配對 **12/12 不對稱**（`| select -First 5` 放行、
    # `| Select-Object -First 5` 擋下）——而 `select` 正是「提前結束管線」最常見的
    # 寫法，等於這道鎖擋掉的剛好是沒人會寫的那一半。每個別名自帶右邊界
    # `(?![\w-])` 以免吃到 `selection`／`sortable`；`%` 與 `?` 另用 `(?=\s|\{|$)`，
    # 避免誤傷 `$_ % 2` 那類真正的運算子用法。
    "pipe-cmdlets": (
        r"(?:Select-Object|Select-String|Out-\w+|Format-\w+|Sort-Object"
        r"|Measure-Object|ForEach-Object|Where-Object|Tee-Object"
        r"|head|tail|findstr)(?![\w-])"
        r"|(?:select|sls|sort|measure|foreach|where|ft|fl|oh|tee)(?![\w-])"
        r"|[%?](?=\s|\{|$)"
    ),
````

### 兩支薄殼上方的過期註解（HEAD L132-L133）

````text
# 🔴 把「攔截端會擋什麼」與「真的會量到假 rc 幾次」拆成兩欄：判準本體、pwsh 實測表與紅綠自證語料
# 住 `tools/lib/rc_after_pipe_real.py`；下面兩支是薄殼，只把已載入的 hook 模組餵進去。
````

### 兩欄註解（對拍錨／唯一可引用欄）（HEAD L149-L154）

````text
    # 🔴 **對拍錨，不是違規次數**：逐字等於攔截端會擋的那件事（攔截端刻意偏擋，全母體實測 91.4% 是
    # 誤報），**不得**被引用成「違規了幾次」；存在的理由是讓 `--parity` 證明兩端沒漂移。
    "rc-after-pipe": _rc_after_pipe,
    # 🔴 **唯一可引用為「量到幾次真風險」的那一欄**：上游原生指令 × 實測會提前結束的管線元素 ×
    # 之後才讀 rc，三者同時成立才算（逐形態實測依據見 `tools/lib/rc_after_pipe_real.py`）。
    "rc-after-pipe-real": _rc_after_pipe_real,
````

## tools/tests/test_check_hooks_liveness.py

### import 行（新增 importlib.util）（HEAD L9-L10）

````text
import ast
import json
````

### MUST_BLOCK 末列「偏向擋的代價」（連同 R79 註解）（HEAD L822-L832）

````text
        # ── R79：偏向擋的**代價**就地記錄（不是漏，是刻意）──
        # 裸原生指令（`git`）確實會重設 rc，但本判準只認呼叫運算子與「語句開頭是
        # 執行檔」，認不得它 ⇒ 這一條會被擋。全史 913 條真實指令實測只有 1 條落在
        # 這一格（0.11%），出口是行內豁免（阻斷訊息第一行就寫著）。
        # 🔴 若日後補上「裸原生指令也算重設」的判準，本列會轉紅——那是正確行為：
        # 取捨變了就必須有人重新決定，不能靜默改掉。
        ("偏向擋的代價：裸原生指令 git 其實會重設 rc，但本判準認不得（出口＝行內豁免）",
         'git status | Measure-Object -Line\ngit commit -m x 2>&1\n'
         '"rc=$LASTEXITCODE"',
         "LASTEXITCODE"),
    )
````

### MUST_PASS 新增列（HEAD L884-L884）

````text
        ("一般指令", "git log --oneline -3"),
````

### 別名對稱測試 docstring（HEAD L888-L892）

````text
        """SA-01：別名與全名其餘字元逐字相同 ⇒ 判定必須相同，且必須是「擋」。

        不對稱本身就是缺陷：`select -First N` 是提前結束管線最常見的寫法，
        只認全名等於這道鎖擋掉的剛好是沒人會寫的那一半。
        """
````

### 別名對稱測試 assert（HEAD L899-L899）

````text
                self.assertEqual(rc_full, 2, f"全名版就沒擋；{err_f}")
````

### 第一行豁免出口測試（HEAD L955-L963）

````text
    def test_the_exemption_exit_is_on_the_first_line(self) -> None:
        """出口寫在頁尾等於沒有：第一次撞到的人先讀到三段責備才看到出路，而
        「窄守衛必須有出口」是這支 hook 的設計前提（SA-01 附帶）。"""
        _rc, err = self._lint("cd AutoClaude")
        first_line = (err.strip().splitlines() or [""])[0]
        self.assertIn(
            "ps-lint-ok", first_line,
            f"阻斷訊息第一行沒有豁免出口，讀者要翻到最後才看得到：{first_line!r}",
        )
````

### _PARITY_HITS 的 Tee-Object 列（Tee-Object 不截斷，移到 _PARITY_CLEAN）（HEAD L1579-L1579）

````text
    ("rc-after-pipe", "& git status | Tee-Object out.txt\n$LASTEXITCODE"),
````

### _PARITY_CLEAN 結尾（HEAD L1597-L1598）

````text
    "git log --oneline -3",
)
````
``````

### §134 DEF-200-477：SessionStart 簡報當第三判準錨點——devC 從 `.claude/hooks/check_claim_provenance.py` 改寫／刪除的散文（逐字，行號＝HEAD 7efc4c0）

原址：`.claude/hooks/check_claim_provenance.py`（R194 五方迭代中該 Developer 從 hook／lib 刪下的散文，原樣保全；內文自帶的 `##`／`###` 小標與圍欄為原檔結構，故以長圍欄包住）。

``````text
# devC 被改寫／刪除的散文（逐字；行號＝HEAD 7efc4c0 的原檔行號）

## `.claude/hooks/check_claim_provenance.py`

### 原 :111-112（檔頭第三個判準段；改為「`tool_result`（DEF-200-477 起另含 SessionStart 簡報，見 `_session_start_anchors`）」）
```
`量測於=<ISO>`（優先），否則往本場 `tool_result` 回溯找同一個「軸＋值」的錨點、取那筆
落款時刻。
```

### 原 :332-334（檔頭〈誠實劃界〉；改為「第五判準仍不算佐證（DEF-200-430）…第三判準自 DEF-200-477 起以簡報落款當錨點」）
```
· SessionStart 簡報不算佐證的代價：新視窗第一回合若只是轉述簡報裡的水位／額度字樣（沒跑
  `--check`／`--pace`），「被擋／水位」宣稱同樣會出聲——這是設計（簡報是啟動當下的快照、
  且每場都有），指路的兩條指令都是零 token 的一行。
```

### 原 :546（`_anchor_time` docstring）
```
    """本場工具輸出裡「這個軸綁這個值」最後一次出現的落款時刻（`None`＝全場無錨點）。"""
```

### 原 :558-560（`stale_pace_hits` docstring 第二段）
```
    純函式。`stamped`＝本場 `tool_result` 的 `[(落款時刻|None, 文字)]`（時序）；`now` 必須
    帶 tzinfo。回傳每筆帶 `kind`：`"stale"`＝真的過期（會出聲）／`"unanchored"`＝軸綁定
    讀數但全場找不到錨點（**登記的盲區：放行、不阻斷，但出一則 ℹ️ 並計數**，見檔頭 M7）。
```

### 原 :1117（`_pace_messages` 盲區訊息，一行）
```
            f"ℹ️ 另有 {len(blind)} 個軸綁定讀數在本場工具輸出裡**找不到任何錨點**"
```

## 非散文（程式碼行）被取代者，僅供對帳

- `.claude/hooks/check_claim_provenance.py` 原 :1195-1196：
  `messages += _pace_messages(` ／ `stale_pace_hits(claim, stamped, datetime.now(timezone.utc)))`
- `tools/tests/test_mac_endurance_r83.py` 原 :1901、:1942：
  `self.addCleanup(os.environ.pop, endurance_env.PLAN_DIR_ENV, None)`（各一行）
- `tools/tests/test_context_budget_guard.py` 原 :7412-7413、:7465-7466、:10292-10293：
  `os.environ[escalation.NOTIFY_ENV] = "1"` ＋ `self.addCleanup(os.environ.pop, escalation.NOTIFY_ENV, None)`（前兩處）；
  `os.environ.pop(escalation.NOTIFY_ENV, None)` ＋ `self.addCleanup(os.environ.pop, escalation.NOTIFY_ENV, None)`（第三處）
``````

### §135 DEF-200-479／481／482：`quota_gate.py`／`audit_session.py`——devD 被改寫／刪除的散文與被取代的程式碼（逐字）

原址：`tools/lib/quota_gate.py`／`tools/probe/audit_session.py`（R194 五方迭代中該 Developer 從 hook／lib 刪下的散文，原樣保全；內文自帶的 `##`／`###` 小標與圍欄為原檔結構，故以長圍欄包住）。

``````text
# devD 被改寫／刪除的散文與被取代的程式碼（逐字；行號＝動工前工作樹原檔行號）

行號說明：`tools/lib/quota_gate.py` 動工前＝HEAD 7efc4c0（git status 未列為修改）；`tools/probe/audit_session.py`
動工前＝devB 改後的工作樹版（1049 行）。

## `tools/lib/quota_gate.py`

### 原 :638-642（`degraded_posture` docstring 第二段「立案」；改為首行括號指標 `（PRD §4.1.5 R-4.1.5-2）`）
```
    🔴 立案（R100／PRD §4.1.5 R-4.1.5-2）：本函式取代的那一句逐字寫
    `⇒ 本次不節流，扇出照常放行。`，而同一支檔 `quota_gate()` 內的註解自述「量不到時
    `decide()` 回 `degraded_cap`（不是不設限、也永不 halt）」⇒ **同一個決策有兩份互相
    矛盾的敘述，而只有訊息那一份有讀者**（`decide()` 算出來的 cap 不會出現在畫面上）。
    兩個方向的誤判都真的會發生：operator 以為沒保護而過度手動收斂，或以為有保護而加派。
```
（其後一個空行一併刪；第三段「為什麼是**算**…」保留。）

### 原 :648-650（DEF-200-466 段；改寫為 DEF-200-466／479 合併段）
```
    DEF-200-466：`cap`＝呼叫端手上**實際要執法的值**（平穩機制之後），有給就直接印它；
    此前一律印上面那個未平穩的 `decide()` 值——持久 cap=0 時印「收到 2」而致動器擋在 0。
    沒給（降級通報的其他來源，還沒走到平穩機制）才自己算。
```

### 原 :948-949（`pace_report` 內 walrus 說明；「餘裕為 0（500/500）」已是假數字——動工前實為 488/500）
```
    # 用 walrus 而不是多一行 `live = …`：本檔 `guardrail_hub` tier 餘裕為 0（500/500），
    # 取數次數與時點逐字不變（同一次呼叫、同一個 `now`），只是把值留下來給第二個消費者。
```

### 非散文（程式碼行）被取代者，僅供對帳
- 原 :653-655（`degraded_posture` 自己算 cap 的三行）：
```
    if cap is None:
        cap = quota_policy.decide(_blank("posture-probe"), when,
                                  quota_policy.load_policy(policy_env())[0]).cap
```

## `tools/probe/audit_session.py`

### 原 :21-24（檔頭〈設計約束〉第一條；`NON_SHELL_TOOLS` 改指 params.json）
```
  · 崩塌判準必須**逐支**：合計面的歷史總量會蓋掉「今天起每一支都抽不到」的格式變更；只用過
    已知非 shell 工具（`NON_SHELL_TOOLS`）或根本沒用過工具的 session（純問答／活體探針）不入崩塌
    分母，否則 `--parity` 在真實窗口恆 rc=1——代價：這類 session 的格式變更不再被逐支抓到，只剩
    合計面 `shell_calls == 0` 兜底；叫過 shell 或認不得的工具、卻一條指令都抽不到者仍是崩塌訊號。
```

### 原 :118-119（`_rc_after_pipe_real` 上方註解；其內容已在 `_POWERSHELL_PATTERNS` 註解與函式 docstring）
```
# 🔴 DEF-200-481：兩欄同吃攔截端判準；pwsh 實測答案表與紅綠自證語料住
# `tools/lib/rc_after_pipe_real.py`，下面兩支是薄殼，只把已載入的 hook 模組餵進去。
```

### 原 :108-112（`_rc_after_pipe` docstring；壓縮為 2 行，保留「借攔截端函式／兩向失準／沿革指標」）
```
    """規則①的量測端＝**攔截端那支函式本身**（不再自寫第二份判準）。

    自寫的扁平正則與攔截端在兩個相反方向同時失準（多行指令低報、把正解形態高報），借過來之後
    這個欄位的語意才真的等於「攔截器會擋的那件事」。沿革見證據檔〈九〉。
    """
```

### 原 :127-129（`rc_selftest()` 整支刪除，改由 `run_selftest()` 自己逐列判）
```
def rc_selftest() -> list[str]:
    """`--selftest`：跑那張實測語料表，回傳失敗訊息清單（空＝全綠）。"""
    return _rc_real.selftest(_lint_ps_hook)
```

### 原 :180-187（`NON_SHELL_TOOLS` 註解＋常數；常數搬進 params.json 的 `parity_non_shell_tools`，註解併入 `_shell_capable` docstring）
```
#: 不會帶 shell command 的內建工具名：整支只用過這些（或 `mcp__*`）的 session 沒有「該抽到
#: command」的前提，不是崩塌訊號（例：只 Write 的活體探針、純讀檔）。名字不在這張表、也不在
#: `COMMAND_PATTERNS` ＝認不得的工具（改名／新增），仍可能是格式變更 ⇒ 照舊算崩塌候選。表是
#: 啟發式：新工具名出現前只會多報、不會漏報（報了就去看那一支）。
NON_SHELL_TOOLS = frozenset({
    "Read", "Write", "Edit", "MultiEdit", "NotebookEdit", "Glob", "Grep", "Agent", "Task",
    "TodoWrite", "Skill", "ToolSearch", "WebFetch", "WebSearch", "Workflow", "SendMessage",
    "AskUserQuestion"})
```

### 原 :518-526（`scan_transcript` 回傳 dict 內「collapsed」上方註解；壓縮為 6 行，刪「代價」句——與檔頭〈設計約束〉第一條重複）
```
        # 逐支崩塌訊號（見檔頭〈設計約束〉）：**有記錄**卻一支帶 command 的 shell 呼叫都抽不到。前提
        # 原用 `records`（連 tool_use 都認不出來正是最徹底的格式變更），現再要求本支叫過「可能帶
        # shell command、或認不得」的工具（`_shell_capable`）：零 tool_use（純問答）與只用過
        # Write／Read 等已知非 shell 工具（活體探針）的 session 不是崩塌，它們曾讓 `--parity` 在
        # 真實窗口恆 rc=1。代價：認不得 tool_use 時，工具名恰落在 `NON_SHELL_TOOLS` 者只剩合計面
        # `shell_calls == 0` 兜底。🔴 逐筆切片下前提改為「**shell 工具真的被叫過**、卻一條指令都
        # 抽不到」：子窗裡沒跑 shell 是正常狀態，沿用 `records>0` 會讓警報在分期用法下常響（常響
        # 的警報等於沒有）。誠實劃界：切片下連工具名都認不出來（`PowerShell` 被改名）時本判準
        # 看不到，由合計面兜底。
```

### 原 :943-946（`--selftest` argparse help）
```
                        help="對已知正解／已知違規各數組跑 `rc-after-pipe-real`"
                             "（答案來自 pwsh 真機實測），並同時印出舊判準對同一批"
                             "語料的判定當作紅的那一半。有任何一組不符即 rc=1")
```

### 原 :956-980（`main()` 內 `--selftest` 區塊；整段由 `run_selftest()` 取代。「舊判準」欄＝攔截端同一支函式，兩欄恆相等 ⇒ `old_wrong==0 ⇒ rc=1` 是結構必然）
```
    if args.selftest:
        failures, probe_bad = rc_selftest(), probe_selftest()  # ②′ 自證另計，不灌進「新判準判錯」
        print("### `rc-after-pipe-real` 紅綠自證"
              f"（{len(_rc_real._RC_SELFTEST)} 組，答案＝pwsh 7.6.4 真機實測值）")
        print("  🔴 綠的那一半：修正後的判準對每一組都要判對。")
        print("  🔴 紅的那一半：同一批語料餵給**舊判準**（＝攔截端那支借來的函式），"
              "看它錯在哪——\n     判準沒有鑑別力時，兩欄會一模一樣。")
        old_wrong = 0
        for command, expected, measured, why in _rc_real._RC_SELFTEST:
            new_verdict = _rc_after_pipe_real(command)
            old_verdict = _rc_after_pipe(command)
            old_wrong += int(old_verdict is not expected)
            print(f"  {'✅' if new_verdict is expected else '❌'} "
                  f"實測{measured:9s} 應判={str(expected):5s} "
                  f"新={str(new_verdict):5s} 舊={str(old_verdict):5s}  {why}")
        print(f"\n  新判準判錯 {len(failures)} / {len(_rc_real._RC_SELFTEST)}；"
              f"舊判準判錯 {old_wrong} / {len(_rc_real._RC_SELFTEST)}")
        print(f"  ②′ 量測自證（阻斷判準＋宣稱句型）判錯 {len(probe_bad)} 組")
        if old_wrong == 0:
            print("  ⚠️ 舊判準一組都沒判錯 ⇒ 這批語料對「修了什麼」沒有鑑別力，"
                  "自證是空的；請補進真的會分開兩者的形態。", file=sys.stderr)
        for line in failures + probe_bad:
            print(f"  ❌ {line}", file=sys.stderr)
        # 舊判準零錯誤也算紅：那表示這份語料證明不了本輪修了任何東西。
        return 1 if (failures or probe_bad or old_wrong == 0) else 0
```

### 非散文（程式碼行）被取代者，僅供對帳
- 原 :798-812 `feed_diffs`（簽章 `(pop, limit) -> list[int]`、無靜止閘、`fresh = datetime.fromisoformat(doc["ts"]) >= p["usage_ts"]`、`return out[:limit]`）。
- 原 :866-877 Q1′b 的 `show("Q1′b …", len(pop), 1, …)`（最小母體寫死 1）、Q1′c 區域變數 `hit5`（改 `hit_n`）。
``````

### §136 本輪新增測試的 docstring 壓縮前原文（逐字；Trim 棒壓成較短版本，保留 DEF 編號與 WHY）

原址：本輪新增測試的 docstring（Developer 當輪撰寫）。

`tools/tests/test_claim_provenance_r86.py` 搬遷前 L1542-L1546：

```text
DEF-200-482：Q3′ 量的是「兩個來源是否一致」，不是「逐字稿落盤落後 feed 一則」——在途
視窗的差值是一則訊息的增量（QA 實測 18767＝相鄰兩則的 used 增量），100 token 的容忍對它
無意義 ⇒ 只納入靜止配對。控制組＝閘門關掉（0 秒）時同一組輸入對在途窗 FAIL，證明是閘門
讓它不假紅。另釘「不舊於」的解析度：feed 的 ts 只到秒、逐字稿到毫秒，同一秒的配對不得
被當成過期而靜默消失。
```
