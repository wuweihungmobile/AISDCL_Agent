# CrossPlatform R196 — 掌舵者五問系列第十八次四方覆核（Windows 11 第四輪；DEF-200-484 lint 規則①左值族封閉、DEF-200-479 第二段 R3 fail-open、DEF-200-465 互釘、DEF-200-246 closed-by-decision、權限姿態裁決；QA 零信任稽核 R195 文字）證據檔

> 主控 Fable 5.1（session 036ca691-7bb9-40e8-a936-545583b8efe3，auto mode 新視窗；Claude Code 2.1.289）；Architect／SA／SD／QA＋官方文件查證包＋Developer-A／B／C 皆 Sonnet。起點 HEAD `1a9564e`＝origin/main、工作樹乾淨。
> 掌舵者原話三問：(1) 新開終端視窗就說被擋不能寫檔／用工具、也不查真實數據；(2) 模型不用真實 /context 或 API 查真實數據；(3) 修復是否已收斂，請詳細評估。另要求：四方獨立審查「與現況比對，確認以上都已修好」、省去非必要文件、R195〈八〉四項裁決由主控依最佳化決策。

## 〇、一句話結論
Q1 我方 hook 層零誤擋（本窗＋SA 子視窗＋7 支 headless 探針皆第 1 個呼叫即現查、零阻斷），但三方獨立真機抓到 R195 修法的同根漏攔（**DEF-200-484**，P2：型別標註／`${}`／逗號列／成員／索引左值包住的原生上游、`${LASTEXITCODE}` 讀法、模組限定 `Select-Object`），本輪封閉整族並兩引擎重測；Q2 未見症狀；Q3 **未收斂**——同族 P2 連三輪（481→483→484），②′ 窗口內家族計數 3 ⇒ 最早宣告推到 R200。權限姿態裁決：auto 為常態、套 `.claude/` 批次時臨時 acceptEdits、被拒走 `/permissions`→Recently denied→`r`（已寫入根 CLAUDE.md）。

## 一、三問第十八次判定（Windows 11）
| 問 | 判定 | 依據（本場 tool_result 或 `[他包回報]`） |
|---|---|---|
| Q1 新視窗說被擋不能寫檔 | **hook 層已修（零誤擋）；殘餘兩條**：(a) lint 同根漏攔 DEF-200-484 本輪封閉；(b) harness auto mode 分類器對 `.claude/**` 的拒絕——我方碼結構上管不到，出口＝權限姿態（〈八〉裁決 1） | 本窗第 1、2 個呼叫即 `--check`／`--pace`，無權限詢問／hook 阻斷／分類器拒絕；QA 讀本窗逐字稿 `is_error 0`、結構 `toolDenialKind 0`、字樣命中皆為引述 `[他包回報]`；Architect 近 21 天 41 個互動視窗 6,613 次呼叫的 98 筆 `toolDenialKind`＝hook 90／路徑保護 6／分類器 2（皆主控改 `.claude/`）`[他包回報]`；主控本窗分類器拒絕 **0**（本輪 `.claude/` 兩次寫入皆放行，見〈六〉） |
| Q2 不查真實數據 | **未見症狀** | SA headless PA×3＋PN×2＋auto×2 第 1 個工具呼叫皆 `--check`／`--pace`、0 denial、數字皆有錨點；planner `used` 與逐字稿原始 usage 差 0 `[他包回報]`；Architect 簡報逐句可執行（4 條 allow 字面逐字在、2 個 Read 退路存在、欄位名一致）`[他包回報]` |
| Q3 是否已收斂 | **未收斂**（詳〈八〉Q5） | 本輪新 P2（484）；協定 sha 不動、窗口 R194～R196 家族 481／483／484 ⇒ 合計 3 > 2 |

## 二、主控親測事實（本場 tool_result 逐字）
- **開場**：`python tools/session_resume_planner.py --check` ⇒ 「新視窗：逐字稿還沒有任何帶 message.usage 的 assistant 記錄…harness 回報 used=86,639（feed）」；`--pace` ⇒ 「現在可派 4 個 agent（硬上限 cap=不設限）…band=free…weekly_scoped 36% 剩 7772 分鐘…量測於=2026-10-04T20:27:08+08:00」＋「⚠️ 落款樣本有斷層：最近 5 列間最大間隔 696.1 分鐘」。兩條皆無權限詢問、無 hook 阻斷。派工前四次 `--pace` 皆 `recommended=4 band=free`（量測於 20:27／20:57／21:00／21:06）。
- **DEF-200-484 修前親驗**：`& cmd /c "exit 5"; [string]$o = cmd /c "echo x & exit 7" | Select-Object -First 1; "helm_typed_assign_rc=$LASTEXITCODE"` ⇒ hook 放行、印 `helm_typed_assign_rc=5 out=x`（真 rc=7 沒被寫入）。
- **棘輪基線**：`--print-guard-lines` ⇒ `淨額 114140→114140 (+0)`、`逐檔漂移 0 支`、`_REPIN_LOG_HISTORY_SHA256 = "8f82574a3243…"`。
- **哨兵現查**：`Get-ScheduledTask … AutoSDD_Sentinel_*` 兩筆（本窗 036ca691… NextRunTime `2026/10/4 下午 09:07:33`；前輪 b1ac224c… `09:18:00`），LastTaskResult 0。
- 收尾親驗見〈六〉。

## 三、四方、查證包與各棒摘要 `[他包回報]`（token／呼叫數取自 harness 完成通知）
| 角色 | 判定 | 要點 | token／呼叫 |
|---|---|---|---|
| Architect | CONDITIONAL | ARCH-196-01 P2＝型別標註賦值漏攔（E7 live 重現 5 vs 7）；A4 權限三案比較（否決自動 allow hook／專案 defaultMode）；評估式四條件、可操作面六項（ARCH-196-02～04）；246 同意附條件；242 承接、199 拆半、193 分析半邊 | 379k／69 |
| SD | CONDITIONAL | SD-196-01 P2 同族（29 案原型 12→0）；SD-196-02 P3 假紅（括號內裸 git 實為重設）；D2 479 R3 規格＋原型；D3 SSOT 走 `quota_gate.quota_messages`；D4 465 互釘測試；459 增補列 1b 文字 | 393k／82 |
| SA | CONDITIONAL | S1 真機：483 四形態如宣稱，但 K1／K2／K3／K5／K9～K12／K13／K14／K16 共 11 形態 E2E 放行且 rc=7；S2 478 成立（bogus sid 回 unavailable、無 sid 短路）；S3 acceptEdits／auto 寫 `.claude/` 3/3 拒、`--add-dir` 外寫才成功；S4 7 支探針 Q2 全 PASS；headless 12 支 | 306k／64 |
| QA | CONDITIONAL | R195 機械宣稱全數重現（8 模組 191／120／192／11／281／333／99／796＝2023；crossref 184／19／147；selftest 0/29；parity 0）；QA-196-01 P2＝R195 稱「分類器樣本只有主控這一次」不實（R194 窗 seq129＋R195 窗 seq96）；②′ window_len=2、NOT-EVALUABLE(2/6)；收斂模擬 | 425k／80 |
| 文件查證（claude-code-guide） | — | 官方文件：auto 下受保護路徑交分類器、allow 不能預先放行、不可用＝拒絕非詢問；acceptEdits 對受保護路徑＝Prompted；專案 defaultMode 設 auto 不生效；`-p` 接受 `--permission-mode auto`；hook payload `permission_mode` 六值但 SessionStart 範例無、PreToolUse 有；`*` 尾綴被尊重 | 424k／64 |
| Developer-A | 交件 | DEF-200-484：hook +8 行（左值族正規化＋`${LASTEXITCODE}`／`$global:`／`Get-Variable` 讀法＋模組前綴＋括號重設）；答案表 29→43 兩引擎重測；83 案×2 不符 78→0；語料重放新擋 5（皆本場污染重現）新假紅 0 | 367k／79 |
| Developer-B | 交件 | 479 R3 fail-open（quota_stability +17／quota_gate +2／test_quota_policy +63，六種變異皆紅）；SSOT 句鎖＋staged hook diff；465 互釘測試（兩變異皆紅） | 265k／71 |
| Developer-C | 交件 | 459 列 1b＋指回句；199 (i) §6.1 (4d) 註記；246 PRD §6.2 標註＋AutoClaude tripwire 測試 6 passed；評估式邊界測試 +1（121）＋raw/可見加印（協定 sha 前後不變）；R195 證據檔套 QA 訂正 12 處 | 324k／82 |
合計約 288 萬 Sonnet token（八個完成通知加總）。

## 四、新發現、嚴重度裁決與修法
| ID | P | 一句話 | 裁決／修法 | 落點 |
|---|---|---|---|---|
| **DEF-200-484**（ARCH-196-01＝SD-196-01＝SA-196-01 左值部分） | **P2** | lint 規則①賦值前綴只認 `$name =`；`[string]$o =`／`${o} =`／`$a, $b =`／`$h.k =`／`$h['k'] =` 包住的原生上游接 `Select -First／-Index` 放行，兩引擎真 rc 未寫入；`${LASTEXITCODE}`／`$global:` 讀法與模組限定 `Select-Object` 不被認得 | 依 R195 對 483 的定級先例（已結案列的同根變體＝P2）計入 ②′ 家族。修法＝**正規化封閉**而非逐形態補 regex：`_ASSIGN_PREFIX_RE` 改 `_LVALUE`（型別標註／`${}`／成員／索引／逗號列）、`_ELEMENT_SPLIT_RE` 不把 `${` 當區塊起頭、`_RC_READ_RE` 吃 `${…}`／`$global:`／`$script:`／`Get-Variable`、`_TRUNCATING_PIPE_RE` 允許模組前綴、`_statement_resets_rc` 把括號／`$( )`／`@( )` 內裸原生視為重設（SD-196-02 假紅併修） | `.claude/hooks/lint_powershell_command.py`（+8；主控安裝）、`tools/lib/rc_after_pipe_real.py`（答案表 29→43，兩引擎 `measured` 重測；C08 `? { $_ }` 再截斷＝7/3 引擎分歧）、`tools/tests/test_check_hooks_liveness.py`（+63） |
| DEF-200-479 第二段 | P3 | 持久穩定檔分不出真長 halt 與殘值 | 主控裁 **R3 reset 感知＋fail-open**：`StabilityState` 加 `reset_at`／`confirmed_at` 選配欄（舊檔相容）；量不到時 reset 已知未到 ⇒ 撐住；已過或盲 >6h ⇒ 放到 degraded cap 並 `emit_to_model` 一次；下次量到即收緊；quota_gate 兩尺帶 `reset_at=halt_resets_at(decision)` | `tools/lib/quota_stability.py` +17、`tools/lib/quota_gate.py` +2（495／500）、`tools/tests/test_quota_policy.py` +63（333→339） |
| DEF-200-465 | P3 | 任務書位置三個家無鎖互釘 | 只加互釘測試（hook 餘裕 0 不做 SSOT 函式）：武裝端 `maybe_arm` 收到的 `plan_path`＝GC 預設 `gettempdir()` 同檔、`gc()` 判 reap=True；GC 側／武裝端改家兩變異皆紅 | `tools/tests/test_context_budget_guard.py` +25 |
| SD-195-05（ARCH-196-08） | P3 | `block_message()` 第三份手寫收斂清單缺 Write、寫死 PowerShell | SSOT 化：`convergent_tools_clause(windows=None)` 以 `_is_windows()` 現查；hook 一行改呼叫 `quota_gate.quota_messages.convergent_tools_clause()`（import 失敗退空字串、阻斷不受影響）；鎖 `assertIn(clause)`＋`assertNotIn("仍然放行")` | `tools/lib/quota_messages.py`（淨 0）、hook +1（1088→1089＝預算上限、餘裕 0）、cbg 測試 +6 |
| DEF-200-246 | P3 | PRD §6.2 兩半邊生產不可達 | 四方（Architect／SD／QA 附條件）同意 **closed-by-decision**：PRD §6.2 R-6.2-2 ③ 標註現交付＝桌面 loud＋自檢印 DRY_RUN、`integration_queue` 保留欄位零寫者、三條可偵測重開條件；反向存在鎖 `AutoClaude/tests/contract/test_def200246_integration_queue_tripwire.py`（6 passed，寫入變異皆紅） | PRD + AutoClaude 測試（非根層棘輪） |
| DEF-200-459 | P4 | PRD §8 列 1 字面與施工圖不一致 | 增補列 1b（遙測端點自身 429＝量不到、永不 halt；列 1 不改寫＝R191 裁決）＋ Pacing 引文後指回句 | PRD v2.1.md、PRD_Amendment_R108_Pacing.md |
| DEF-200-199 (i) | — | 施工圖 §6.1 加速臂例外註記 | 文件半邊落地（(4d) 註記 7 行，203／4096 照錄 R191〈四〉）；P16／舊律／L2／L3 承接 R198（與 242 同持有面、R197 須 ≤0） | PRD_Amendment_R108_Pacing.md |
| ARCH-196-03／04 | P3 | 評估式門檻寫死在碼無邊界測試；raw P≤2 與公式可見數不同 | 合成輪帳本邊界測試（和＝2 PASS／和＝3 FAIL／末輪非零 FAIL／p1=1 FAIL／列數 5 NOT-EVALUABLE）＋ `--protocol-status` 加印 raw／可見；`fivequestion_ledger.py` 不在 manifest（11 檔），協定 sha 前後同為 `c62fa4355d14…` | `tools/tests/test_claim_provenance_r86.py` +35（120→121）、`tools/probe/fivequestion_ledger.py` +5 |
| QA-196-01 | P2（文字） | R195 稱分類器樣本只有主控這一次；實為 2 筆（R194 窗 L820 seq129、R195 窗 L628 seq96），皆 `[Self-Modification]` | 套訂正（〈九〉） | R195 證據檔 |
| ARCH-196-07 → **DEF-200-485** | P3 | 指引↔allow 字面對不齊、缺全稱鎖 | 立列 open，承接 R197 | 帳本 |
| ARCH-196-09 → **DEF-200-486** | P4 | 簡報不知本窗 permission_mode；官方文件 SessionStart payload 無該欄、hook LOC 餘裕 0 ⇒ 須 PostToolUse 路徑由逐字稿導出 | 立列 open，承接 R197 | 帳本 |
| SA-196-02／03（SD-196-03） | P4 | docker／node／claude 詞彙表外：截斷後讀 rc 放行、其後跑 node 再讀 rc 誤擋 | 設計決定（hook :205-207 刻意排除機器專屬安裝名），登記殘餘不修 | hook 誠實劃界 |
| SA-196-07 | P3（harness） | auto mode 系統文字「優先用 Bash」在子視窗存在（n=1），Windows 與鐵律一衝突 | repo 對策已在（Bash 停用 hook＋簡報首句）；NOT-A-DEFECT（repo 側） | — |
| ARCH-196-02 | P2（提案層） | 照字面降頻會拿掉找到 483／484 的 SA 變體矩陣 | 採納：降頻附 T1～T7 觸發條件（〈八〉裁決 4） | 〈八〉 |

殘餘（本輪刻意不修，登記在 hook 檔頭〈誠實劃界〉與本節）：K1 字串內插 `"…$(git … ｜ select -First 1)"`（`mask_regions` 遮蔽字串內容，修法牽動遮罩層）、K8 反引號續行、K12 `iex '…'`（靜態不可判）、`{ }` 區塊內裸 git 仍假紅（納入會讓 `$sb = { … }` 漏擋）、連鎖賦值 `$x = $y = git …`、帶引號的 `gv 'LASTEXITCODE'`。

## 五、誠實劃界與未驗
- **Q1 母體仍小**：修法後真實互動視窗 n=2（R195 主控窗、本窗）皆為依 SOP 開場的主控；SA 子視窗與 12 支 headless 探針是 `sdk-cli`／子代理形態。分類器拒絕的真實樣本累計 2 筆（R194／R195 窗），本窗 0 筆——本窗兩次 `.claude/` 寫入（Edit hook 一行、Copy-Item 安裝 lint hook）皆放行，判定依據仍不可觀測。
- **PS 5.1**：K5 無賦值形態在 PS 5.1 讀值有競態（-1／0／3 皆出現），答案表採有賦值形態並註明 `[他包回報]`；主控本窗只在 pwsh 7 親驗。
- **語料重放**：`shell_command_corpus.py` 無 lint 判準，Dev-A 另寫腳本重放 9,544 種字面（新擋 5 皆本場探針）`[他包回報]`。
- **Mac 未驗**：本輪所有修法只在 Windows 實跑；lint 新判準的 darwin 路徑不受影響（PowerShell 工具只在 Windows）；Mac Q4′ 證據仍 `[前輪 R192]`，約 2026-10-17 過期。
- **`[他包回報]` 未親跑**：四方／查證包／Developer 的全部數字；主控親跑範圍＝〈二〉〈六〉〈七〉。
- **文件查證可靠度**：WebFetch 小模型轉述；permission-modes／permissions／settings／hooks-guide／changelog 五頁落原文檔逐行核對，settings-reference 兩次抓取矛盾已排除不採用 `[他包回報]`。
- **分母漂移**（QA-196-10）：全母體 76/110→74/108→74/99，最舊逐字稿 09-05，疑 30 天清理，未證。
- **工具呼叫**：Dev-C 82、SD 82、QA 80（含交件）皆達或略超 80 預算；SA headless 12 支（任務書 ≤8＋3）。

## 六、收尾親驗（主控親跑；本場 tool_result 逐字）
- **hook 一行 SSOT 句（Edit，分類器放行）**：`test_context_budget_guard.py` ⇒ `Ran 798 tests in 123.127s`／`OK (skipped=1)`／`CBG_RC=0`；`check_loc_budget --json` ⇒ `LOC_RC=0`、`absolute=0 tier=0 special=0 root_tools=0`、`context_budget_guard.py loc=1089 budget=1089 headroom=0`。
- **lint hook 安裝（Copy-Item，分類器放行）**：sha `before=FE46FB247ACF`→`after=122E78A8D1B9`（＝scratch 複本 `src=122E78A8D1B9`），`git diff --numstat` `14 6`；`test_check_hooks_liveness.py` ⇒ `Ran 191 tests in 24.753s OK` rc=0；`audit_session.py --selftest` ⇒ `判錯 0 / 43；expect=True 27 列、expect=False 16 列`、`②′ 量測自證…判錯 0 組` rc=0；`--parity --record-since 2026-10-04T10:05:00+08:00` ⇒ `攔截端 × 量測端對拍（2944 條 unique 指令）判定分歧 0 筆` rc=0。
- **真機端到端（PowerShell 工具）**：`& cmd /c "exit 5"; [string]$o = cmd /c "echo x & exit 7" | Select-Object -First 1; "e2e484_typed_rc=$LASTEXITCODE"` ⇒ `PreToolUse:PowerShell hook error … 🔴 先單獨跑 & <exe> <args>（不接管線），下一句再讀 rc`（修前放行印 5、修後擋下＝484 關閉）；`… "e2e484_brace_rc=${LASTEXITCODE}"` ⇒ 同樣擋下；安全形態 `$v = git … log --oneline -n 5; $v | Select-Object -First 1 | Out-Null; "e2e_safe_variable_rc=$LASTEXITCODE"` ⇒ `e2e_safe_variable_rc=0`（放行）。
- **Dev-C 受 Dev-A 在途影響的模組**：`test_claim_provenance_r86.py` ⇒ `Ran 121 tests in 1.941s OK` rc=0。
- **帳本與承接**：三列第一版超 700 bytes（242＝707、246＝745、484＝749；「存量列超標總量 14739 > 14638」＝三列超標量之和 101）各砍一～二次後 `check_defect_log_crossref.py` ⇒ `✅ 缺陷帳本跨文件狀態一致：帳本 187 筆有效狀態紀錄、19 份掃描目標皆無矛盾…具名治理文件 148 份皆已登記…未結存量 33 列` `CROSSREF_RC=0`；`check_handoff_carriers.py` ⇒ `✅ 每一筆前瞻延後宣稱都有帳本承接載體` `CARRIERS_RC=0`。
- **棘輪重釘（結構列→print→套表→填數→print→填 sha→接鏈列→print，四次收斂）**：起算 `114140→114140 (+0)`；三棒落地＋結構列（重釘列、回歸鎖軌同輪列、到期兌現列 (196, 519) 並重新武裝 198／518）後 `114140→114349 (+209)`、`逐檔漂移 5 支`；`apply_frozen_guard_lines.py` 套回 `列數 88→88，變動列 5`、填數 ⇒ `114349→114349 (+0)`；首跑鎖模組 `FAILED (failures=6)`＝guard-total 兩站點未補＋接鏈列未補 ⇒ 補兩站點後剩 1 紅 `[未接上現值] 帳本鏈路終點指紋 8f82574a3243 不等於現值 e2117559c41f` ⇒ 追加接鏈列 `("R196", "8f82574a3243", …, "DEF-200-484")`（鎖檔 8734→8735）⇒ 填數 `("R196", 114140, 114350, +210, …)`、主軌 59（＝210−151）≤ 519、PREFIX_LEN 326→327、sha 最終 `7c1d18c28c25…` ⇒ 最後一印 `114350→114350 (+0)`、`逐檔漂移 0 支`；`test_adr_xplat001_c1c2_lock` `Ran 192 tests OK` rc=0；E501 債棘輪首跑 `140 not less than or equal to 139`（鎖檔回歸鎖軌列與 Dev-C 一行東亞寬度 102／103）縮字後 `Ran 39 tests OK` rc=0；`git diff --check` rc=0；ruff 四檔 `All checks passed!`。guard-total 兩站點（`AutoSDD_improving_112.md`／`CrossPlatform_R145_Scan_Findings.md`）各一列 `114140 → 114350（+210）`。
- **ONBOARDING §7（乾淨 venv 載具 `tools/lib/clean_venv_carrier.py`，背景跑約 10 分鐘）**：`[3/5] 探針 psycopg2 ABSENT／sqlalchemy ABSENT`、`[4/5] sync_onboarding_baselines.py --write --with-slow rc=0`、回填 Windows 欄 `autoclaude-pytest-snapshot → {'passed': 4736, 'skipped': 172}`、`cigate-v001 1478／v030 1979／scripts 363`、`snapshot-fingerprints-win32 … 'autoclaude': '69fdad8c334d' … pgextras=absent`、`[5/5] 必刪乾淨 venv`、`CARRIER_RC=0`。

## 七、根層全套、push 與雲端驗收
（主修法 commit 後以 docs commit 回填，同 R194／R195 體例）

## 八、交棒／掌舵者側待辦

### Q5 評估（掌舵者原話：「是否修復已經收斂，不用再進行？請詳細回覆是否已經收斂？給我評估說明」）
- **症狀面**：(a) 我方 hook 層：本窗、SA 子視窗、7 支 headless 探針皆零誤擋、第 1 個呼叫即現查——掌舵者描述的「一開窗就說被擋、不查數據」在 R195／R196 兩個真實主控視窗都沒有重現。(b) 但 lint 規則①連三輪長出同根洞（481 過擋→483 漏攔→484 漏攔），本輪改「正規化封閉」一次封整族（83 案×2 不符 78→0、答案表 43 列兩引擎重測），殘餘已登記為靜態不可判或設計決定。(c) harness 分類器對 `.claude/**` 的拒絕：我方碼結構上無法再降，出口只有權限姿態（裁決 1 已寫入根 CLAUDE.md）。
- **量測面（②′）**：協定 sha `c62fa4355d14…` 不動；窗口 R194＝481、R195＝483、R196＝484（依 R195 定級先例計入）⇒ 任何含這三輪的六輪窗口合計 3 > 2。**最早宣告＝R200**（屆時 rows[-6:]＝R195～R200，須 R197～R200 全零且 R200 為 0）；R197～R199 再出任一 P≤2 即再順延。raw P≤2（481／482／483／484）＝4 vs 公式可見 3（482 excluded）。
- **結論：未收斂。** 但該繼續的不是每輪四方全開：採 Architect A5／ARCH-196-02——**R197 起降頻**（量測器出數＋QA 單方複核＋SA 探針），**附觸發條件 T1～T7**：T1 本輪 diff 動到守衛面（`.claude/hooks/**`、`.claude/settings*.json`、`tools/lib/{session_brief,quota_messages,harness_feed,quota_gate,quota_policy,quota_stability,sentinel_lifecycle}.py`、planner、permissions.allow）⇒ SA 必跑**變體矩陣**（兩引擎）而非只 PA×3；T2 量測器任一紅；T3 `claude --version` 與上輪不同；T4 降頻輪出現任何 P≤2 或「宣稱被擋而前面沒有真阻斷」；T5 主控視窗前 10 個呼叫出現阻斷／拒絕／詢問；T6 權限姿態或 permissions 內容變更；T7 任一平台 Q4′ 證據逼近 14 天；兜底＝連續 3 個降頻輪或距上次完整四方 14 天必開一輪。降頻輪**不追加輪帳本列**（只在觸發或兜底時追加完整輪列），代價＝window_len 前進較慢。
- **為什麼還不能說收斂**：(a) 同族 P2 連三輪；(b) 修法後真實主控視窗 n=2；(c) 分類器樣本 2 筆、本窗 0 筆、判定依據不可觀測；(d) Mac 全未驗；(e) 評估式本身可被「少查」操作（ARCH-196-02），降頻必須帶 T 條件。

### 主控裁決（掌舵者授權「依最佳化決策」；R195〈八〉四項）
1. **權限姿態**：常態 auto；套 `.claude/` 批次時 Shift+Tab 兩下切 acceptEdits、在 `.claude` 詢問框選整場授權、套完切回；auto 下被拒 ⇒ `/permissions`→Recently denied→`r`。否決自動 allow hook 與專案 defaultMode。已寫入根 CLAUDE.md〈權限姿態〉節。**不需掌舵者再動作**；若掌舵者偏好「開窗就 default 模式」亦可（代價＝每次寫檔都詢問、無人在就卡住）。
2. **SD-195-05**：採 SSOT 化（不抄第二份清單），主控親套，本窗分類器放行。完成。
3. **DEF-200-479 第二段**：fail-open（R3 reset 感知）。完成並結案。
4. **降頻**：R197 起降頻，附 T1～T7（上段）。本輪（R196）依掌舵者指示四方全開。

### 下輪的機械義務（主控記名）
- 護欄行數棘輪：本輪淨額（見〈六〉回填）為正＝款(11) 連升第 2 輪 ⇒ **R197 主軌必須 ≤ 0**（Trim 棒搬史料或零新測試）；`_REPIN_NET_CAP_DUE_ROUND=198`／`_TARGET=518`（本輪兌現 (196, 519) 並重新武裝）；Phase 2 `_PHASE2_REVIEW_LOG` 末列 (195, 維持觀察) ⇒ R200 到期且只剩 [提案]／[落地]；U9 `_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND=198` 不變。
- 承接列：DEF-200-485（全稱鎖）／DEF-200-486（permission_mode 條件句）→ R197；DEF-200-242／DEF-200-193／DEF-200-199 (ii) → R198（R197 須 ≤0 不落新碼；193 主控先一句話裁「超支」定義：建議採列級「列 pct 超過該軸 reset 前線性配額」）；DEF-200-207 維持 R117+ 開放式。
- ②′：協定 sha `c62fa4355d142d4900114109f657ffaa791a76d21a97ae993af7a0012da4b155` 不動；本輪登記的協定／量測器 P3（ARCH-196-03／04 已以測試與加印落地；QA-196-11 協定防線缺口）待下次必要重置時一併收。
- R197 第一件事：鏡稽核本檔＋本輪帳本列（DEF-200-484 新立；DEF-200-479／DEF-200-465／DEF-200-459 結案；DEF-200-246 closed-by-decision；DEF-200-193／DEF-200-199／DEF-200-242 承接 R198；DEF-200-485／DEF-200-486 新 open）。
- Mac：Q4′ 證據 2026-10-17 前重產；lint 新判準 darwin 無影響但 `rc_after_pipe_real` 答案表為 Windows 兩引擎量測，Mac 側只跑單元閘。

### 本輪未做（不塗綠）
- 199 (ii) P16／舊律／L2／L3；242；193 分析半邊（定義待裁）；DEF-200-485／486 落地；ARCH-196-05／06 文字（R195 文字已由 QA 訂正覆蓋 06 一半，人側出口已寫進根 CLAUDE.md）。
- 本檔文字未經鏡稽核；Mac 側一切未驗；Fable 模型探針未做。

## 九、QA 零信任稽核〈R195 證據檔與帳本〉訂正去向 `[他包回報]`
| ID | P | 位置 | 訂正 | 去向 |
|---|---|---|---|---|
| QA-196-01 | P2 | 〈八〉行85／〈五〉行57／〈四〉行54 | 「分類器樣本只有主控這一次」→ 2 筆（R194 窗 L820 seq129、R195 窗 L628 seq96），皆 `[Self-Modification]` | Dev-C 套用 |
| QA-196-02 | P3 | 〈五〉行57 | 「第 100 餘個」→ 第 96 個 | Dev-C 套用 |
| QA-196-03 | P3 | 〈八〉行83 | 評估式四條件（補 p1 全 0）；PASS 不含 Q1′～Q4′ | Dev-C 套用 |
| QA-196-04 | P3 | 〈二〉 | 「逐字」實為縮寫；`2 failures / 0 errors` 非 runner 原文 | Dev-C 套用 |
| QA-196-05 | P3 | 〈四〉478 列 | 「cbg 796 見〈六〉」〈六〉無 | Dev-C 套用 |
| QA-196-06 | P3 | 〈三〉 | 各 ID 無 REPORT 路徑不可覆核 → 如實寫「無持久座標」 | Dev-C 套用 |
| QA-196-07 | P3 | 〈五〉行61 | Q4′ JSON `repo_head=7efc4c06`、cc 2.1.288，只證新鮮度 | Dev-C 套用 |
| QA-196-08 | P3 | 〈三〉 | SD 51 次超上限未標 | Dev-C 套用 |
| QA-196-09 | P3 | 〈七〉 | 缺 HEAD 雲端（root-infra-ci 37169954685 success） | Dev-C 套用 |
| QA-196-10 | P3 | 母體 | 分母漂移 76/110→74/108→74/99（疑 30 天清理，未證） | 本檔〈五〉登記 |
| QA-196-11 | P3 | 協定 | P2→P3 無機械防線；excluded 無理由無 reset 亦 PASS；常數不在 manifest | ARCH-196-03／04 落地一半；餘待協定重置 |
帳本列：483 新立（R195）無訂正；478 fixed 無訂正；479 本輪結案。
