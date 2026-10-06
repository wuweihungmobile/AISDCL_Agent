# CrossPlatform R204 — 宣告收斂後首個守衛面輪：修 DEF-200-501（SA-201-01 Stop hook 否定句「沒被擋」誤報；套 params.json 既有否定語意、不養第二份詞表；r86 四句紅→綠且行數不變；hook 史料搬附錄、守衛面 numstat ±19 淨 0；Developer＋QA 皆 Sonnet、主控 Fable 5.1；本輪在 Windows 完成、不需交棒 Mac）證據檔

> 位置：`docs/06_quality/`（軌道 R 系列證據檔；上一份 R203 證據檔 `CrossPlatform_R203_FiveQuestion_WinEval_Streak2_Converged_Evidence.md`）。
> 載體：缺陷帳本 DEF-200-501（本輪結案）；規格＝R201 證據檔 §4.2；准入依根 CLAUDE.md〈守衛面准入〉（暴露證據 (b) 探針 1 筆，R201 已成立）。

## 〇、一句話結論
Stop hook 第五個判準此前把「沒被擋」這類否定句當成「被擋」宣稱（Mac 探針 PC1 真實發生、sid 84bc2a3b）；本輪把量測端 params.json 既有的否定語意逐字套進 hook（中文 lookbehind 字元類＋句級否定排除；英文 `not\s` 是唯一自加），r86 三支新測試對舊 hook 紅、對新 hook 綠，PC1 原句走真實子行程不再出聲；r86 恰維持 2001 行（棘輪零重釘）、hook 1272→1272 行（史料逐字搬本檔附錄）、守衛面 numstat `19 19` 淨 0。本輪全程在 Windows 完成；修法是平台中性的 Python 字串比對，**不需交棒 Mac**。

## 一、准入、觸發條件觀測與角色
- **准入**：守衛面要動（`.claude/hooks/check_claim_provenance.py`）⇒ 依〈守衛面准入〉先附暴露證據：R201 §4.2 已判 (b) 成立（症狀探針 PC1 自然任務中實際發生、非構造），R203 入帳 DEF-200-501 承接本輪。本輪**不擴大搜尋**（T1 反轉）：零 SA 變體矩陣、零新詞表。
- **T 條件觀測（只登記，不自動開輪）**：`claude --version` 本場現查 `2.1.291 (Claude Code)`；R203 證據檔記 2.1.290 `[前輪]` ⇒ R196 T3「版本與上輪不同」成立。宣告後規則（README〈窗口規則與收斂判定〉）＝再評只由准入觸發條件決定；是否開一輪只量不審由掌舵者裁決（〈八〉）；義務的機械載體＝帳本 DEF-200-503（〈四〉4.2 #5）。
- **角色（省去非必要文件，只留本證據檔＋帳本列）**：主控 Fable 5.1 兼 Architect／SA（規格已由 R201 SA 寫定，本輪只做設計裁決 D1～D4）；Developer（Sonnet，兼 SD 細部設計；harness 完成通知：386,147 token／61 次工具呼叫／1,273 秒）；QA（Sonnet，唯讀獨立審查，〈三〉）。任務書住 scratchpad，不入 repo。

## 二、主控親測事實（本場 tool_result 逐字或摘錄；Windows 11 Koala-MSI）
- **開場**：`--check` 為本窗第 1 個工具呼叫（新視窗、harness used=85,429）；`--pace`：「現在可派 2 個 agent（硬上限 cap=2…）｜band=converge｜最緊的一條＝weekly_scoped 84%…量測於=2026-10-06T12:48:39+08:00」（降級建議 sonnet，照辦）。本機＝origin/main＝`835ac5b`（`git status --short --branch` 乾淨）。R203〈七〉回填 commit `835ac5b` 雲端對帳：`gh run list --commit 835ac5b989983417f0d6aac74bce19aa888276b9` ⇒ root-infra-ci 37398377744 success（createdAt 2026-10-06T01:17:07Z）；其餘 workflow 依 paths 白名單未觸發（缺席＝未驗證、非通過）。
- **三支基線（HEAD 狀態）**：`check_defect_log_crossref.py` rc=0、`check_handoff_carriers.py` rc=0（「✅ 每一筆前瞻延後宣稱都有帳本承接載體」；commit 訊息 727 則、前瞻延後宣告 36 筆）、`tools/check_hooks_liveness.py` rc=0。
- **安裝 Developer 成品**：`Copy-Item` 鏡像 → `.claude/hooks/check_claim_provenance.py`（auto mode 分類器放行，無詢問）；src／dst sha256 皆 `D1167CF3BC668E213A3EABD8B7C02F40DB4D1454A76125D239573716255BAEB8`；dst 1272 行、無 CR；r86 2001 行、無 CR；`git status --short` 恰兩檔 `M`。
- **r86 正式跑**（`python -m unittest discover -s tools\tests -p test_claim_provenance_r86.py -v`，`AUTOSDD_SENTINEL_OFF=1`）：`Ran 124 tests in 1.906s` `OK` `R86_RC=0`；-v 清單含三支新測試 `test_a_negated_block_phrase_is_not_a_claim`、`test_the_negation_semantics_are_params_json_s_not_a_second_vocabulary`、`test_the_pc1_negated_sentence_is_silent_end_to_end`。
- **lint／棘輪／閘**：`ruff check tools/tests/test_claim_provenance_r86.py` ⇒ `All checks passed!` `RUFF_R86_RC=0`；`ruff check .claude/hooks/check_claim_provenance.py` ⇒ `All checks passed!` `RUFF_HOOK_RC=0`；`test_adr_xplat001_c1c2_lock.py --print-guard-lines` 首兩行 `# 淨額 114350→114350 (+0)`／`# 逐檔漂移 0 支` `GUARD_RC=0`；`AutoClaude/tools/check_loc_budget.py --json` `LOC_RC=0`；E501 存量（`--isolated --select E501 --line-length 100`）舊版 `1751:79` 1 筆、新版同一筆 1 筆 ⇒ 新增 0。
- **守衛面量具**：`git diff --numstat -- .claude/hooks .claude/settings.json .claude/settings.local.json tools/lib/{session_brief,quota_messages,harness_feed,quota_gate,quota_policy,quota_stability,sentinel_lifecycle}.py tools/session_resume_planner.py` ⇒ 恰一行 `19 19 .claude/hooks/check_claim_provenance.py`（淨 0）。
- **搬史料逐字核對**（腳本：兩檔 `git diff -U0` 的全部 `-` 行去前綴、trim，逐行在 `appendix_moved_history.md` 找子字串）：`removed_nonblank=44`、`missing_in_appendix=1`，唯一缺的是被改寫的程式碼行 `r"(被擋|被阻擋|擋下|…"`（它不是史料，是 `BLOCK_CLAIM_RE` 加前綴後的舊字面）⇒ 43 行史料全部逐字在附錄。
- **headless 真機現查**（新 hook 裝好後、Claude Code 2.1.291；`claude -p --model haiku --debug hooks --debug-file <log> "<prompt>"`，三窗 rc 皆 0）：(1) 「ok」窗：`Hook SessionStart:startup (SessionStart) success` 2 筆（SDD-ROUTER、SDD-CTX-GUARD 簡報皆注入），無 `"Hook Stop` 行（回覆無任何宣稱）；(2) **正控制**窗（請模型逐字回覆「收工：99991 passed。」）：`"Hook Stop` 行 **2** 筆——第一筆 `Hook Stop (Stop) success: stdout: {"hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": "🔴 這一則有 1 個量化判決數字（99991）在本場自己的工具輸出裡找不到出處…`、第二筆只剩 stderr（`stop_hook_active` 夾具＝恰好一個額外回合），模型最終回覆改為要求出處 ⇒ Stop 載具在 2.1.291 headless 下活著、新版 hook 在跑；(3) **否定句**窗（請模型逐字回覆「能。兩步都沒被擋。」）：模型回覆逐字 `能。兩步都沒被擋。`、`"Hook Stop` 行 **0** 筆、SessionStart success 2 筆、`Hook .*(error|fail)` 0 筆 ⇒ PC1 原句在真實載具上靜音（正控制與否定句窗相隔 13 秒、同一載具）。三窗皆零 tool_use，不入五問真實窗母體（`uses` 非空才計）。

## 三、Developer／QA 摘要 `[他包回報]`
- **Developer（Sonnet）**：舊鏡像 `-k Unbacked` ⇒ `Ran 16 tests; failures=5 errors=1` rc=1（舊 hook 對 PC1 逐字回覆真的唸出「被擋／水位」）；新鏡像 `-k Unbacked` ⇒ `Ran 16 tests` ok rc=0；新鏡像整檔 `Ran 124 tests` OK rc=0；舊鏡像整檔紅只來自三支新測試。E501 前後同 1 筆；hook 新舊同 2 筆既有 UP017。鄰近鎖（RoundLabel／TestRootToolsLintPolicy／Bucket／taxonomy）皆綠；分桶 `{'prose': 4261, 'guard_self': 3176}` 前後不變。工具呼叫 61 次（預算 70）。
- **Developer 登記的風險（皆承自 params.json 逐字、本輪刻意不擴詞表）**：「我並不能用工具。」（真宣稱、`並` 在 lookbehind 類內）會被吞；含 `不是`／`不會`／`不算` 的整句靜音（句級排除）；`I wasn't blocked.` 仍命中（英文只加 `not\s`）。
- **QA（Sonnet，唯讀；harness 完成通知：305,003 token／46 次工具呼叫／1,355 秒）**：`VERDICT: APPROVE`、`NEW_P_LE_2: 0`；任務書十項皆 ✓（r86 -v `Ran 124 tests in 1.870s` OK rc=0；四句否定子行程 rc=0、stderr 0 字元，三條正控制 stderr 皆含「被擋／水位」；舊 HEAD blob 鏡像對跑 OLD 四句全出聲／NEW 全靜音／NEW 正控制仍出聲；params 對帳 ✓、協定目錄 diff 空；r86 2001／hook 1272 行皆 LF；`--print-guard-lines` +0；搬史料 44 行僅 1 行＝改寫的程式碼字面；E501 1→1；ruff 三檔綠；帳本 501＝700 bytes／503＝505 bytes；crossref／carriers／LOC rc=0）；加量單模組 c1c2_lock 192 OK、r60 281 OK、subprocess_encoding_hygiene 39 OK、liveness 191 OK；真實語料重放 E／F 見〈五〉。P4 八條 QA-204-01～08 全數本輪處置（〈五〉與 4.3）；〈理論洞〉四條構造性計 0（`startswith` 弱預言機、`_SENTENCE_RE` 切句粒度、`not\s` 單一空白、英文 `wasn't`／`never`）。被守衛擋下 0 次；一次空洞對跑（hook 放一般目錄找不到 `tools/lib` 而 fail-open 全靜音）自行作廢、改鏡像樹重跑。

## 四、裁決與落地
### 4.1 設計裁決（主控；Developer 照做）
- **D1 不 import、不讀 params.json**：hook 檔頭明文 import 面只准三個「有就用、沒有就退化」借用，多一個相依就多一條 fail-open 路徑；採「字面＋對帳測試」（同檔先例 `PACE_AXES` 對 `quota_policy.KNOWN_KINDS`）。「不另養第二份詞表」的機械保證＝r86 `test_the_negation_semantics_are_params_json_s_not_a_second_vocabulary`：以 params.json 的值當 oracle，斷言 `BLOCK_NEGATION_LOOKBEHIND == <claim_re 開頭 lookbehind> + "(?<!not\s)"`、`claim_exc_re.startswith(BLOCK_NEGATION_EXC_RE.pattern)`。
- **D2 hook 最小改法**：`BLOCK_NEGATION_LOOKBEHIND = r"(?<![沒未不無非並])(?<!not\s)"` 前綴到 `BLOCK_CLAIM_RE`；`BLOCK_NEGATION_EXC_RE = (沒有|並未|未)(被|受|遭|阻|擋|拒|鎖|封|禁)|不是|不會|不算` 於 `unbacked_block_claim_hits()` 句迴圈整句略過；`_is_quoted` 不動；量測端（`audit_session.py` L829／L837）句級「claim 命中且 exc 不命中才計」同形。
- **D3 搬史料抵銷**：hook +16 行（常數 2、註解 5、docstring 4＋2、句迴圈 2、regex 1）以檔頭 L84–L101「兩個更直覺的形狀已被同一份普查逐一證偽」18 行逐字搬本檔〈附錄 A〉、原位留 2 行指標 ⇒ 1272→1272。
- **D4 r86 行數不變**：`_FROZEN_GUARD_LINES` 總量棘輪＋`_FROZEN_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS = 2` 已被 R195（+138）／R196（+210）用滿 ⇒ 任何淨增即紅；三支新測試 +23 行＋六處指標 +6 行（新增 29／移除 29）以六處 docstring／註解敘事逐字搬〈附錄 B〉§1～§6 抵銷（原位各留 1 行指標、零斷言刪除）⇒ 2001→2001、`--print-guard-lines` `+0`／零漂移、零重釘儀式。

### 4.2 裁決表
| # | 裁決 | 落地 |
|---|------|------|
| 1 | **DEF-200-501 fixed**（紅→綠雙向自證、PC1 原句子行程重放靜音、對帳鎖釘住 params.json 同源） | 帳本 501 列狀態欄 |
| 2 | **不需交棒 Mac**：修法為平台中性 Python 字串比對；驗證面＝r86 子行程測試（兩平台 CI 皆跑 `tools/tests/**`）＋ Windows headless 真機；Mac 側只需下次切換時 ff-only 拉進本 commit（hook 隨 repo 走） | 〈八〉 |
| 3 | **T3 觀測登記、不自動開輪**：CC 2.1.290→2.1.291；再評（只量不審）由掌舵者裁決 | 〈八〉決策卡 |
| 4 | **零新詞表、零守衛面淨增**：守衛面 numstat `19 19`；params.json 與協定 manifest 未動（`git diff` 無 `FiveQuestion_Audit_Protocol/`） | 〈二〉 |
| 5 | **DEF-200-503 open（承接輪次 R205）**：T3 再評義務的機械載體；同時承接 carriers 判準① 對 commit `db4a542`「承接 R198」段落的要求——結案 501 後未結列最大承接輪號掉到 117 ⇒ `check_handoff_carriers.py` rc=1（R199 已知鏈型：結案載體列必同輪補下一棒）；淨額棘輪 新增 1／結案 1＝0，不走 `AUTOSDD_NET_RATCHET_OFF` | 帳本新列 503 |

### 4.3 登記不修清單（P4；本輪只登記）
| ID | 嚴重度 | 形態 | 暴露度 | 處置 |
|----|--------|------|--------|------|
| DEV-204-01 | P4 | `並` 在 lookbehind 類內 ⇒ 「我並不能用工具。」真宣稱被吞；自然連接詞「並擋下／並被擋」同型 | 真實語料 1 句（sid 888b2ff4 `並擋下 Workflow`＝描述已發生的阻斷；該則訊息層仍出聲、無漏攔後果）`[他包回報]`（QA-204-01 訂正：原記「構造」） | 承自 params.json 逐字；改它＝改協定凍結檔，不在本輪；已入 hook〈誠實劃界〉 |
| DEV-204-02 | P4 | 句級排除對含 `不是`／`不會`／`不算` 的真宣稱整句靜音 | 構造 | 規格刻意接受的假陰性（只出聲守衛，可滿足性優先） |
| DEV-204-03 | P4 | 英文否定只收 `not\s`：`wasn't blocked`／`never blocked` 仍命中 | 構造 | params.json 英文側無否定形；擴之即第二份詞表 |

## 五、誠實劃界與未驗（不塗綠）
- **Mac 真機未重放 PC1**：原逐字稿（sid 84bc2a3b）住 Mac；本輪以 r86 合成同句（`能。兩步都沒被擋。`）走真實子行程替代。平台中性但「Mac 預設直譯器載入本 hook」那一條只由 macos-compat-ci 與下次 Mac 切換的 SessionStart 簡報覆蓋。
- **召回率只量到一部分**（QA-204-01 訂正主控原寫的「無從量測」）：R201 普查「否定句被誤報」探針 1 筆；QA 真實語料重放 F（本機 134 份頂層逐字稿、14 次真實「被擋／水位」出聲）新 hook 訊息層 14/14 仍出聲（KEPT 12／PARTIAL 2／SILENCED 0）、句級 20→16（丟 3 句症狀提及／否定＋1 句 `並擋下 Workflow`）；重放 E（1648 個獨特助理文字塊、證據設空）句級 170→144、新增 0 `[他包回報]`。合成注入紅綠自證仍是主要憑證。
- **headless 證據的邊界**：三窗皆 `--model haiku`、零工具呼叫；正控制證明「Stop 載具會跑、新版 hook 第一個判準會發射」，否定句窗的靜音由同一載具背靠背的對照支撐（開窗時刻差 13.55 秒、正控制收尾到否定窗開窗 0.6 秒 `[他包回報]`；不是只靠「沒出聲」）；但 headless 的 `stop_hook_active` 時序與互動視窗是否完全同形，本輪沒有量（既有 M1 實測母體是互動窗）。
- **輪號字面在程式碼指標內**（QA-204-06）：hook 1 處、r86 6 處的 `CrossPlatform_R204_…` 檔名指標含輪號，輪號字面鎖對 `_R204_` 形態豁免（與 r86:8 既有 `CrossPlatform_R86_…` 同慣例）；任務書「無 R204 字樣」字面不成立、實質無害。
- **帳本 501 列恰 700 bytes**（QA-204-07）：餘裕 0，日後任何增補須先縮。hook 檔頭〈誠實劃界〉已補收否定處理的三個已知假陰性（QA-204-02；以壓縮同檔兩段新增文字抵銷，行數仍 1272）。
- **Developer 數字未逐筆重跑**：〈三〉標 `[他包回報]`；主控親跑的正式 r86／ruff／棘輪／LOC／numstat 數字在〈二〉。
- **週額度**：主控 Fable weekly_scoped 開場 84%（converge）、headless 窗簡報已見 87%（prepare、cap=1）；本輪只派兩個 Sonnet、零 Fable 子代理。

## 六、收尾親驗（主控親跑；本場 tool_result；QA 回報後補記）
- **QA 回報後 P4 落地**：hook 檔頭〈誠實劃界〉+2 行（否定處理的三個已知假陰性）、第五判準新段 3→2 行、`BLOCK_NEGATION_*` 註解 5→4 行 ⇒ 仍 1272 行、無 CR；過程 ruff 兩次紅（W605：docstring 內 `\s` 改 `\\s`；E501：101>100 縮字）後 `ruff check` 三檔（hook／r86／governance_docs）`All checks passed!` `RUFF_ALL_RC=0`；`ast.parse` 在 `-W error::SyntaxWarning` 下 `ast_ok` `AST_RC=0`；`test_no_invalid_escape_sequences.py` `Ran 12 tests` OK `ESCAPE_RC=0`；r86 最後一次 `Ran 124 tests in 1.883s` OK `R86_RC=0`；hook 最終 sha256 `706959C0B50C282F94BD8AF87C1C9C66C4D469A04C1BD9DFDA334DC25ED1079C`（安裝當下為 Developer 成品 `D1167CF3…`，之後兩次 P4 修改）。
- **帳本與閘**：501 列 700 bytes（餘裕 0）、503 列 594 bytes；`check_defect_log_crossref.py` rc=0（帳本 204 筆有效狀態紀錄、具名治理文件 156 份、未結存量 29 列；warning 組成同 R203：兩份治理文件逼近 262144、外部阻塞 3／結構性長債 7 複查逾 14 天、已結列殘留待辦 2、帳本未 commit 提醒）；`check_handoff_carriers.py` 補 503 前 rc=1（逐字：`commit db4a542：訊息宣告把工作延後到 **R198**（[承接輪次／承接者] …），但帳本家族內**沒有任何未結案列**的承接輪次 ≥ R198（現有未結承接輪號＝[81, 83, 95, 98, 101, 112, 117]）`）、補後 rc=0「✅ 每一筆前瞻延後宣稱都有帳本承接載體」（tracked 交接載體 192 份、前瞻延後行 100 筆；commit 727 則、含前瞻延後宣告 36 筆）；`check_loc_budget.py --json` `LOC_RC=0`；`--print-guard-lines` `# 淨額 114350→114350 (+0)`／`# 逐檔漂移 0 支` `GUARD_RC=0`。
- **`git add -A` 後 `git diff --cached --numstat`**（本節補記前）：`19 19 .claude/hooks/check_claim_provenance.py`／`2 1 docs/06_quality/AutoSDD_Defect_Log.md`／`197 0 docs/06_quality/CrossPlatform_R204_StopHook_Negation_FalsePositive_Fix_Evidence.md`／`5 0 tools/lib/governance_docs.py`／`29 29 tools/tests/test_claim_provenance_r86.py`；守衛面量具恰一行 `19 19`（淨 0）；本檔以 Add-Content 貼附錄時寫入 115 個 CRLF（git 警告「CRLF will be replaced by LF」）已正規化為 LF。
- 根層全套、commit、push、雲端見〈七〉。

## 七、根層全套、push 與雲端驗收（主控親跑；本場 tool_result）
- 根層全套（〈六〉補記後、commit 前；`tools/run_root_unittests.py`、`AUTOSDD_SENTINEL_OFF=1`，背景阻塞、log 落 scratchpad、rc 寫檔不接管線；14:03:48～14:05:58）：一跑即綠 `ROOT_RC=0`「✅ unittest 數量下限釘選通過：發現 5179 個測試（下限 5101）」（＝R203 的 5176 ＋ 本輪 3 支）「[M6 id 集合] tools/tests@win32：✅ 集合關係成立（本次 skip 46 支）」「✅ 真實 TEMP 圍籬 … 零變動（前 4／後 4 份）」「✅ 孤兒 console 普查：零增長（前 0／後 0）」；log 內 `^(FAIL|ERROR):` 行 0。
- commit／push／雲端 run：以 docs-only 回填 commit 補記本節（同 R197～R203 慣例）。

## 八、交棒／掌舵者側待辦
### 掌舵者提問「下輪是否需要交棒到 Mac 執行？」——主控答：**不需要**
1. 本輪（守衛面修法）已在 Windows 完成並由兩平台 CI 的 `tools/tests/**` 路徑覆蓋；hook 是 tracked 檔，Mac 下次切換照 `useMacWin.md` §B ff-only 拉進即生效，不必為它開 Mac 輪。
2. DEF-200-499 維持 closed-by-decision：Mac 行為面重評只在掌舵者 Mac 真機看到症狀（「被擋」字樣、不查水位、假收斂）並回報 sid／畫面時重開；本輪沒有新增任何 Mac 專屬義務。
3. 若掌舵者要親眼確認 PC1 不再誤報：在 Mac 一般視窗（第一個工具呼叫＝`--check`）打一句含「沒被擋」的回覆即可；不需要四方、不需要排輪。

### 掌舵者決策卡（已由主控依「最理想」代決；無人看管時維持現狀）
1. **T3（CC 2.1.291）**：帳本載體 DEF-200-503（承接輪次 R205）：主控建議在評估機（Windows）開一輪只量不審（三條指令零 token、順便看修法後 Q1′b 母體），不派 Developer；掌舵者若裁定不開，把 503 結成 closed-by-decision 並寫明理由即可（宣告後規則只說「再評由准入觸發條件決定」，未強制）。
2. **DEV-204-01～03（P4）**：不修、不立輪；任一出現暴露證據（真實窗命中或掌舵者回報 sid）再依〈守衛面准入〉升 P2。
3. **Windows／Mac 新視窗照舊**：第一個工具呼叫＝`--check`；看到「被擋」字樣當下貼畫面原文＋session id＋機器。

### 日曆鎖 `[前輪]`
- Mac JSON 效期 2026-10-19T21:38:15+08:00；Windows JSON 效期 2026-10-17T22:16:53+08:00（再評輪開場先 `tools\session_gate_acceptance.py` 重產）。
- ONBOARDING nightly 錨首個紅燈 2026-10-20T09:57:51+08:00；ruff E501 豁免 11-03 起紅；棘輪 `live_repin_round()`＝196、款(12) due 198、Phase 2 due 200（本輪零重釘，不觸發）。

## 附錄（搬遷史料，逐字；來源行號＝搬出前；由 Developer 交件檔 appendix_moved_history.md 貼入——除其檔頭標題與規則句 2 行換成本標題外逐字；QA-204-04）


## 〈附錄 A〉hook 檔頭 docstring：兩個更直覺的形狀已被同一份普查逐一證偽

- 來源：`.claude/hooks/check_claim_provenance.py` 原 L84–L101（18 行，整段搬出）。
- 原位：檔頭「第二個判準」節末留 2 行指標（指向本附錄）。

~~~~text
🔴 **兩個更直覺的形狀已被同一份普查逐一證偽，不要再走一次**（數字皆現跑
`--shape a`／`--shape b`）：
  · **「因果宣稱裡的具名量在本場觀測值全同」**（＝直接把「常數不可能是變因」寫成判準）
    → 命中 3 筆，逐筆判讀 **1 真 2 假**（33%）。假紅的成因是結構性的：判準只知道那個識別
    字**出現在句子裡**，不知道它是不是被當成原因（兩筆假紅分別是「`arm_reset` 全是 0 ⇒
    兩個痕跡不一致」與「跟 `five_hour`、`seven_day` 平起平坐 ⇒ 它 100% ⇒ 一票否決」，
    命中的識別字都只是**被順帶提到**）。這件事在散文平面上沒有解——要判斷誰是主詞就要
    理解語意，而那正是判準不該做的事。
  · **「因果宣稱裡的具名量在本場沒有兩個相異觀測值」**（含 0 次觀測）→ 命中 **153 筆**，
    隨機抽 12 筆逐筆判讀 **0 真 12 假**（0%）：命中的全部是 `condition_evaluator`／
    `last_log_path`／`enable_kernel_brain`／某支測試的名字這種**程式符號**，它們根本不是
    「量」，本來就不會有觀測值 ⇒ 這個形狀等於對「句子裡出現 snake_case」發警報。
⇒ **常數／變因這條軸在散文平面上做不出鑑別力**，它只在**落款平面**上是精確的（那裡欄位
與值都是結構化的，不必猜主詞）。所以那一半刻意**不做成警報**，改做成一支**正向工具**
`tools/probe/variate_contrast.py`：餵它一份 JSONL 落款，逐欄印出「觀測數／相異值數／
是不是常數」，並可 `--split-at` 切成兩組看哪些欄位真的區分得開兩組。本事故用它是一行的事
——`spend`／`extra_usage` 會直接印成 `CONSTANT`＝不可能是變因。本判準的訊息因此**指著它**，
讓查證比宣稱便宜（判準治形態、工具治內容，兩者刻意分工，不是同一份知識住兩個家）。
~~~~

## 〈附錄 B〉`tools/tests/test_claim_provenance_r86.py`

### §1 模組層註解塊（刻意不在本檔驗「hook 檔存在」與「Stop 兩個載具都在」）

- 來源：原 L83–L87。
- 原位：L83 保留；L84–L87 換成 1 行指標。

~~~~text
# 🔴 **刻意不在本檔驗「hook 檔存在」與「Stop 兩個載具都在」**（本批以雙向注入實測後移除）。
# 兩者都已有既有鎖在守，重寫一份就是同一份知識住兩個家、而只有一個家會被改：
# 實測紀錄見 R86 護欄重釘證據檔 §D。
# 那兩道鎖的分母是**現查磁碟的註冊集合**，本檔新增的條目自動落進它們的射程，
# 所以本檔只需守「判準本體」與「程序層契約」——註冊面不是本檔的職責。
~~~~

### §2 `TestTheR89ErrorLiteralMechanismJudgement` 類別 docstring

- 來源：原 L289–L294。
- 原位：L289／L290／L293／L294 保留；L291–L292 換成 1 行指標。

~~~~text
    """`DEF-200-123`：把**錯誤訊息的字面**當成機制結論。

    守的是什麼：那句假前提被寫進交棒書、多個 commit，還當成前提餵給 Architect ⇒ 整段
    分析建立在假前提上；而真相是那個量**連續 15 列都是 100.0＝常數**，不可能是變因。
    本判準治**形態**，內容那一半治在 `tools/probe/variate_contrast.py`。
    """
~~~~

### §3 `TestAPercentBindsToItsOwnAxisNotToOneAcrossAnotherAxis` 類別 docstring

- 來源：原 L522–L529。
- 原位：L522 保留；L523–L529 換成 1 行指標（帶結尾引號）。

~~~~text
    """軸名與百分比之間夾著**另一個軸名**時，那個百分比屬於後者（跨軸誤綁定）。

    成因：原判準是「軸名＋至多 40 個任意字元＋百分比」，軸名會綁到其後**第一個**百分比，
    不管中間隔了誰——`（seven_day，剩 988 分鐘；session 是 13%）` 被綁成 `seven_day=13`，找不到
    錨點，對**正確引述**誤報「找不到任何錨點」並逼模型多跑一回合（離線重現：探針 3 支中 2 支；
    本機 28 筆軸綁定讀數中 4 筆跨度含另一軸名）。測意圖：被處罰的是照實引述，而且同一個
    綁定錯誤還會讓**真的過期**的讀數被當成 unanchored 漏掉（第四格）。
    """
~~~~

### §4 `TestTheModelChannelIsClampedOnStopHookActive` 類別 docstring

- 來源：原 L615–L620。
- 原位：L615 保留；L616–L620 換成 1 行指標（帶結尾引號）。

~~~~text
    """M1：這個夾具**不是優化**——沒有它，守衛會在額度吃緊的那一刻自己燒額度。

    複審實測：不夾 ⇒ 一個 prompt 9 次 Stop、9 則零內容 assistant 訊息；夾了 ⇒ 2 次 Stop、
    1 次發射、恰好 1 個額外回合。而 stderr 那條**送不到模型**（`DEF-200-135`：exit 0 的
    stderr 不進 context，實測 1h49m／45 turns 零訊號）⇒ 唯一有效通道就是會迴圈的那一條。
    """
~~~~

### §5 `TestTheNakedVerdictWithNoEvidenceIsFlagged` 類別 docstring

- 來源：原 L806–L812。
- 原位：L806 保留；L807–L812 換成 1 行指標（帶結尾引號）。

~~~~text
    """規則 8 的破洞本體：**不帶值**的完工判決 ＋ 本場一次工具輸出都沒有。

    守的是什麼（Rule 9）：前三個判準全部收在「值」上 ⇒ 這一型結構上看不見，而
    `commit b1ef81f` 的誇大宣稱正是走這個盲區溜過去的。判準與第一個的異同：第一個問
    「這個**數字**的出處在哪」（值域比對）；本判準的宣稱不帶值，改問「本場**有沒有任何
    工具輸出**」＋「這句話是不是**堆疊**了判決詞」——兩者都是字串比對，不理解語意。
    """
~~~~

### §6 `TestTheTurnBoundaryIgnoresHarnessGeneratedUserRecords` 類別 docstring

- 來源：原 L1167–L1172。
- 原位：L1167 保留；L1168–L1172 換成 1 行指標（帶結尾引號）。

~~~~text
    """DEF-200-423：回合邊界只認操作者輸入（數字與判準全文見 `_is_genuine_user_turn`）。

    背景 agent 收工通知、peer 訊息、slash／skill 展開也以 role=user 落盤；把它們當『回合』，
    邊界就滑到最近一則通知，兩則真人訊息之間的 hook 阻斷被擠出窗口 ⇒ 收尾摘要一提
    『被擋』就假紅。另守：本 hook 自己的 Stop 警報不得當佐證（否則自己洗白自己）。
    """
~~~~
