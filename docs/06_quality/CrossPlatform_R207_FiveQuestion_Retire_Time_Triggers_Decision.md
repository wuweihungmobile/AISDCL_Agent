# CrossPlatform R207 — 五問再評觸發修憲：退役時間型觸發、改症狀驅動（決策檔）

> R 系列治理文件（根 CLAUDE.md〈三條改進軌道〉附列）之決策檔，刻意不套證據檔模板。協定 `docs/06_quality/FiveQuestion_Audit_Protocol/`（README 改字 ⇒ `--protocol-status` 印 PROTOCOL-CHANGED、輪帳本 +1 重置列）；上輪證據檔 `docs/06_quality/CrossPlatform_R206_FiveQuestion_MacRound_Q4Regen_CarriersQuoteFilter_Evidence.md`。標記：`[主控提供]`＝主控本場 tool_result；`[SA 讀碼]`＝作者讀檔、未跑；〈四〉空格由 Developer 親跑後填。行號皆 HEAD 9192cd0b。

## 〇、一句話結論
收斂宣告後的再評只由症狀驅動（S1～S6；唯一真相源＝協定 README）；以版本號、證據效期、14 天兜底計時的 T3／T7／兜底明文退役，Q4′ 重產降為再評輪開場步驟、不再是日曆義務。
裁決來源：掌舵者 2026-10-07 明示「除非必要不要有特定日期的義務；再評只由症狀驅動」`[主控提供]`；本檔記錄主控（Architect）據此做的 A1～A3 與帳本、CLAUDE.md 連動裁決。

## 一、事實與理由
1. **T3 已再度成立，而上一次再評無退化** `[主控提供]`：`claude --version`＝2.1.292；R205 的再評做在 2.1.291（commit 3a7e590c 訊息）、[前輪]三項量測全 PASS、不升級、零守衛碼（`docs/06_quality/CrossPlatform_R205_FiveQuestion_WinEval_T3_Recheck_Evidence.md`〈〇〉）。時間型觸發＝無症狀也開輪，再評永遠做不完。
2. **三個 14 天計時器各住哪裡** `[SA 讀碼]`：
   - 兜底與 T7：舊清單只在 `docs/06_quality/CrossPlatform_R196_FiveQuestion_Lvalue_Closure_Evidence.md:85`（單行），根 CLAUDE.md:81 以「沿用 R196 T1～T7」間接引用；README 原本沒有它們。
   - Q4′ 效期（T7 的量尺）：`docs/06_quality/FiveQuestion_Audit_Protocol/params.json:21` 的 `q4_max_age_days`＝14（README:53／:63／:68 引用；`tools/probe/fivequestion_ledger.py:200` 只讀、不寫死）；現況 win32 JSON 2026-10-17T22:16:53+08:00、darwin 新檔 2026-10-20T23:46:47+08:00 到期，到期不再是義務。
   - ONBOARDING 表③ nightly 錨：`tools/tests/test_doc_loc_baseline_freshness_r60.py:4958` 的 `_NIGHTLY_MAX_AGE_DAYS`＝14；這是 CI 錨過期帶、不是再評觸發。
3. **症狀驅動接得住同一批風險**：版本變更若改了權限姿態由 S6 接住、若造成症狀由 S1／S3 接住；Q4′ 效期只在再評輪開場才有意義——量測碼不變（過期仍印 FAIL），故 S2 明文排除「僅因過期」的 FAIL，否則時間型觸發會從後門回來。
4. **A3 推翻 R206〈四〉D1 的讀法 R2、採 R1′ 的擴大版（他機輪次一切結果只入 note；他機看到的 Q4′ 非過期 ✗ 由主控在 note 裁定是否視同 S2）**：他機條款（不計次、streak 沿用）與計次條款（任一機任一輪任一行 FAIL ⇒ 0）字面互撞，R206 採 R2（他機 FAIL 歸零）並登記 P3「下次 PROTOCOL-CHANGED 視窗一併修」。本輪既開修憲窗就一併消歧：R206 D1 當時已記 R1′「字面同樣成立，且與宣告範圍（評估機行為面＋兩平台 Q4′、Mac 行為面未驗）更自洽」（逐字）——他機行為面不在宣告範圍內，其 FAIL 不該歸零評估機累積的 streak。這是在沒有 FAIL 待判的修憲窗做的一般性消歧、不是為了保住某個 streak 值：本輪為重置列、`symptom_streak` 本來就寫 0，對最終值零影響；R203 的收斂宣告為歷史事實，協定重置不撤回。附帶效果：R206〈四〉4.x #2 的排程風險（35be7e5b 離開保留期前，Mac 他機輪次的指令 2 恆 FAIL 並歸零 streak）隨之解除。R206 列的 `symptom_streak` 0 依新讀法本應為 3；輪帳本 append-only、不改既有列，本輪重置列從 0 起算。

## 二、改了什麼（逐檔逐句）
- `docs/06_quality/FiveQuestion_Audit_Protocol/README.md`（協定 sha `5c9aadf2…`→`97bbef35…`，僅此一檔）：
  - A1：〈窗口規則與收斂判定〉「之後只在根 CLAUDE.md〈守衛面准入〉的觸發條件成立時再評」→「之後只在下列再評觸發 S1～S6 成立時再評」；其後新增觸發清單 S1～S6、明文退役句與 WHY。
  - A2：Q4′ 攜回段「效期自 `generated_at` 起 `q4_max_age_days` 天」後補「過期不構成日曆義務，只在再評輪開場檢查，過期者該輪開場先重產／攜回」。
  - A3：他機條款補「含 FAIL：他機輪次的 FAIL 只入 `note`、不歸零」；計次句「任一機任一輪任一行 FAIL」→「評估機輪次任一行 FAIL」。
- 根 `CLAUDE.md`〈守衛面准入〉第 3 條，只改一句：「沿用 R196 T1～T7（R196 證據檔〈八〉）」→ 以 README S1～S6 為唯一真相源、T3／T7／兜底已退役、T1 反轉照舊。
- `docs/06_quality/AutoSDD_Defect_Log.md`：DEF-200-504 → `closed-by-decision（2026-10-07）`（欄 4／6 瘦成索引）；新增 DEF-200-506（open P4，表③ nightly 錨機械回填）；淨額＝結案 1／新增 1＝0。
  - DEF-200-504 原載義務的去向：Q4′ 兩份 JSON 效期→A2 開場步驟；表③ nightly 錨→本輪回填＋DEF-200-506；R206 決策卡（35be7e5b 離開保留期前不排 Mac 他機輪次）→A3 解除；9192cd0b 回填 commit 的雲端對帳（其訊息載明由本輪開場對帳）→〈四〉末列。
  - DEF-200-499 的重開條件（Mac 一般窗指令 1／2 FAIL）不動：依 A3 該 FAIL 先入 note、由主控裁定是否重開 499，不自動歸零 streak。
- `docs/06_quality/FiveQuestion_Round_Ledger.jsonl`：+1 列（`window_reset: true`、`symptom_streak: 0`、18 鍵含 `reset_reason`、理由寫 `reset_reason`）。`tools/lib/governance_docs.py`：登記本檔。
- DEF-200-504 原列逐字（HEAD，688 bytes）：
```text
| DEF-200-504 | 2026-10-06 | 五問再評輪主控（本欄刻意零輪號） | **宣告收斂後有期限的維護義務**：Q4′ 兩份 JSON 效期（win32 2026-10-17T22:16:53+08:00／darwin 2026-10-20T23:46:47+08:00），過期後任何再評先重產、darwin 份須 Mac 產出攜回；ONBOARDING §7 表③ nightly 錨 `nightly-checked-at=2026-10-05T09:57:51+08:00` 的 14 天過期帶自 2026-10-20T09:57:51+08:00 起轉紅，須在此前依 SOP 第 6 步回填 | P4 | 下一次 T 觸發再評前（且不晚於各效期）重產 JSON；10-20 前回填表③；carriers 承接義務已解除 | open（承接輪次：R207；流程義務、非缺陷、無暴露軸；DEF-200-504） |
```

## 三、不改什麼
- 守衛面零改動；量測器（`tools/probe/audit_session.py`、`tools/probe/fivequestion_ledger.py`）零改動；`tools/tests` 零改動；`params.json` 一字不動（`q4_max_age_days` 仍是再評輪開場的效期量尺）。
- `_NIGHTLY_MAX_AGE_DAYS` 不動（CI 錨過期帶；機械回填見〈五〉）；README 的「相鄰兩次達標相距不得超過 `q4_max_age_days` 天」規則不動、僅加註「宣告前的計次連續性規則；宣告後不再數 streak」（它不是再評觸發）。
- 不新增第二個 open 列（淨額棘輪）；除 DEF-200-504 外不改任何既有帳本列。

### 理論洞清單（只登記、不修）
依根 CLAUDE.md〈守衛面准入〉「量、不挖」：無暴露證據、未構造實驗，只登記、不立列、不同輪修。
| # | 嚴重度 | 形態與座標 | 來源 | 暴露度 | 修法方向（給下一位） |
|---|---|---|---|---|---|
| 1 | P4 | `_nightly_provenance_problems` 以 `run_id not in onboarding_text` 判「`nightly-run` 必須出現在表③-b」，但 `onboarding_text` 是整份 ONBOARDING.md、含錨那一行本身（錨自帶 `nightly-run=<id>`，`fields` 即取自該行）⇒ 判斷恆真，「錨 ↔ 表③-b 綁定」實際不成立（`tools/tests/test_doc_loc_baseline_freshness_r60.py:5008`；`fields` 取自 :5118、呼叫鏈 :5141→:5069） | Developer 讀碼回報 `[他包回報]`；SA 讀同檔複核形態成立 `[SA 讀碼]` | 無；未構造實驗 | 比對面改成只取表③-b 那幾列，或先剝掉錨那一行再比對 |
| 2 | P4 | README 的 S1～S6 與 `charter_sa.md` 的章節名 S1～S4 同名異義 | QA 讀碼 `[他包回報]` | 無 | 下次 PROTOCOL-CHANGED 窗改名（例如 E1～E6） |

## 四、驗證（Developer 親跑後填；逐字貼 rc 與輸出，轉述標 `[他包回報]`）
| 指令 | 預期 | 實得 |
|---|---|---|
| `python tools/probe/audit_session.py --protocol-status`（套 README 後、追加輪帳本列前） | 印 `PROTOCOL-CHANGED` | rc=0；「protocol_sha256=97bbef35f0d58c8fdbe04088d56a790951eaea1c01b78bd8c0f94d56a446fed4（manifest 11 檔）」「輪帳本 14 列；window_len=6；評估: PROTOCOL-CHANGED（需新列帶 window_reset:true＋理由）」 |
| 同上（追加列後） | 新 sha `97bbef35…`、`window_len=1`、`評估: NOT-EVALUABLE(1/6)`、`完整性閘 ✓` | rc=0；「protocol_sha256=97bbef35f0d58c8fdbe04088d56a790951eaea1c01b78bd8c0f94d56a446fed4（manifest 11 檔）」「輪帳本 15 列；window_len=1；評估: NOT-EVALUABLE(1/6)」「完整性閘 ✓」 |
| `python tools/check_defect_log_crossref.py`；`--unresolved-count` | rc=0；未結 29 列 | crossref rc=0：「帳本 207 筆有效狀態紀錄、19 份掃描目標皆無矛盾」「具名治理文件 159 份皆已登記且未逾體積上限」「未結存量 29 列（唯一量測入口＝`--unresolved-count`；warn 86／fail 98 列）」；stderr 14 行 ⚠️（皆為警告、無 ❌）：與補丁前基線 13 行逐行相同、另多 1 行「AutoSDD_Defect_Log.md 相對 git HEAD 有未 commit 的修改」（commit 後消失）`[他包回報：SA 的補丁前基線檔，Developer 逐行 diff 比對]`；`--unresolved-count` rc=0：「未結列數＝29／全部 207 列｜warn=86 fail=98」，未結 ID 清單含 DEF-200-506、不含 DEF-200-504 |
| `python tools/check_handoff_carriers.py` | rc=0 | rc=0：「✅ 每一筆前瞻延後宣稱都有帳本承接載體」；census：tracked 交接載體 195 份（前瞻延後行 91 筆）、commit 訊息 734 則（含前瞻延後宣告 36 筆）；`--self-test` rc=0：34 行 PASS、0 行 FAIL，末行「[self-test] ✅ 全部通過」 |
| `ruff check tools/lib/governance_docs.py` | All checks passed | rc=0：「All checks passed!」（另跑 `ruff check tools/ .claude/hooks/ --no-cache` rc=0：「All checks passed!」） |
| `cd tools/tests` 後 `python -m unittest test_claim_provenance_r86 test_check_defect_log_crossref test_doc_loc_baseline_freshness_r60` | OK | 各模組各開一個行程分別跑（`cd tools/tests`、`AUTOSDD_SENTINEL_OFF=1`；非單一指令合跑）：`test_claim_provenance_r86` rc=0「Ran 124 tests in 1.495s」「OK」；`test_check_defect_log_crossref` rc=0「Ran 269 tests in 10.518s」「OK」；`test_doc_loc_baseline_freshness_r60` rc=0「Ran 281 tests in 102.828s」「OK」；另跑 `test_adr_xplat001_c1c2_lock` rc=0「Ran 192 tests in 13.415s」「OK」、`test_archive_defect_log` rc=0「Ran 188 tests in 31.804s」「OK」、`test_defect_id_reference_integrity` rc=0「Ran 11 tests in 3.645s」「OK」 |
| `python tools/run_root_unittests.py`（收尾單人窗口、背景阻塞） | ROOT_RC=0 | 第一次（QA 前樹）ROOT_RC=0：發現 5180 個測試（下限 5101）、M6 skip 47、TEMP 圍籬零變動 `[主控提供]`；QA 訂正後的最終樹由 pre-push 慢層全套重驗、結果不回填本檔 |
| push 後雲端 run（以 paths 白名單實際觸發者為準；缺席＝未驗證、非通過） | 觸發者全 success | push 後由主控 `gh run watch` 查核；結果記在 R208 開場對帳（帳本載體 DEF-200-506） |
| 開場對帳：HEAD 9192cd0b（上輪〈七〉回填 commit）的雲端 run，載體原為 DEF-200-504：`gh run list --commit 9192cd0b0f7fdd980b7ea524e8c7c174f5457279 --json databaseId,name,conclusion`（短 sha 回空陣列） | 觸發者全 success（docs-only，通常僅 root-infra-ci） | rc=0（實跑欄位 databaseId,name,status,conclusion,event,createdAt）：`[{"conclusion":"success","createdAt":"2026-10-06T18:21:56Z","databaseId":37510737235,"event":"push","name":"root-infra-ci","status":"completed"}]`；回傳僅此一筆，未列出的 workflow 缺席＝未驗證、非通過 |

## 五、交棒
- 表③ nightly 錨改機械回填（排程 workflow 以 bot 回寫，或本機 nightly 把現查結果寫回工作樹）：承接輪次 R208，帳本載體 DEF-200-506（open P4）；DEF-200-504 已 closed-by-decision。
- 本輪回填的錨值見 DEF-200-504 列狀態欄；回填步驟沿用 ONBOARDING §7 SOP 第 6 步。
- 本輪回填的錨依 `_NIGHTLY_MAX_AGE_DAYS` 首次轉紅時刻＝2026-10-22T08:50:29+08:00（DEF-200-506 落地期限的參考值，不是再評觸發）。
