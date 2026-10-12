VERDICT: APPROVE
一審 P3 的程式面八項（C1～C8）與 SA 四條補牙皆已真的修好且各有會紅的測試（我的 32 個隔離突變殺 30 個、存活 2 個皆非 P≤2）；不下令時 decide／describe／pace_line 對 HEAD 逐字不變（800 組隨機＋2658 筆真實燃燒帳重放＋12 份 pace_report 全數零差異）；根層全套兩輪 rc=0；新發現無 P≤2，P3 共 7 條（1 條是 C5 替代句帶進的新措辭誤差、6 條是文件措辭）、P4 兩條。

# CrossPlatform R212 第五列 QA 二審鏡（修復包 Dev-2 驗證；唯讀）

> 角色：QA 二審鏡（唯讀；model=sonnet）。範圍：一審四份 findings 的 P3 是否真的被修好、修復有沒有破壞別的東西；不重做一審。紀律：未改任何 tracked 檔；未跑 `--pace`；未碰網路（渲染腳本把 `quota_meter` 取數原語與 `urlopen`／`create_connection` 換成必拋例外，全程未觸發）；`--issue`／`--revoke` 只對沙箱執行（`AUTOSDD_TRACE_DIR`／`AUTOSDD_QUOTA_CACHE_DIR` 指向 scratchpad，輸出的檔案路徑逐字可證），真實落款 45c49b8e35 未動；突變一律在 scratchpad 複本。未做構造性對抗搜尋：本檔的新 P3 來自「量既有修法的條件在真實燃燒帳上的吻合度」，不是造輸入找洞。
> 重現腳本與逐字輸出都在 `/private/tmp/claude-501/-Users-wuweihong-Antigravity-AISDCL-Agent/ed1c9022-22cc-4974-a8b3-9d4ebfa5f6bd/scratchpad/qa2/`（`scripts/`、`*.out`、`mutlogs/`；不入庫）。
> 本檔新檔名符合 `docs/06_quality/CrossPlatform_*.md` 發現面，須由主控登記到 `tools/lib/governance_docs.py`（本鏡唯讀、未改）；登記前 `check_defect_log_crossref.py` 會因本檔而紅。

## 〈一〉C1～C8＋SA 四條逐項驗證表

### 一-A 逐項

| 項 | 我驗到的（座標／指令／輸出） | 判定 |
|---|---|---|
| C1 清倉段只印一次 | 零網路真渲染 `pace_report`（`qa2/render_pace.out`；真實形狀：週 78%／短窗 29%、點名 weekly_all）：第 0 行尾 `｜🔥清倉 6d842cc58b：放寬 2 軸／未放寬 4 軸`（30 字，≤40）；第 1 行（`describe(burndown=False)`）不含「清倉」；第 2 行為全文；`report.count('清倉模式生效中')＝1`。`describe(d)` 預設仍帶全文：突變 E2b（預設不帶）被 `test_naming_the_long_window…` 殺；`describe(` 的其餘呼叫端（`quota_messages.py` 的 halt／節流／prepare 訊息、`quota_gate.py` 的 `quota_throttle_message`）皆用預設，hook 阻斷訊息仍看得到全文。突變 E1（標題行印全文）／E2（忽略 `burndown=False`）／E3（`full_line` 恆空）／E3b（第二行忘了 `burndown=False`）皆殺。 | 通過 |
| C2 四句理由 | `qa2/c2_reasons.out`：①08-28 立案原型（r=5.2）model=fable ⇒ five_hour 印 `攤提供給軸 kind=weekly_scoped 不 qualifying（model-scoped／fallback／不同窗）`、weekly_all 印 `視野已不在 far，無遠期減速可收回`；model=sonnet ⇒ five_hour 印 `攤提在此帶未收緊（無可放寬）`（SD 一審情形 1／2）。②派工 hook 形狀（無換算比；週 78%／短窗 29%）⇒ session／five_hour 印 `本軸無攤提上調可暫停（Q-cross 不享視野地板）`，不再有「與被點名軸不同窗」（SD 情形 3）。③Architect 一審 E4（週軸 55%／65%、短窗 8%、r=5.0）⇒ session／five_hour 改印 `攤提在此帶未收緊（無可放寬）`（修前＝`已在放寬上限，無可再放`）。④3000 組隨機形狀×3 個點名軸：舊兩句殘留 0；以真實燃燒帳 206 列×4 變體重放（824 筆決策）：舊兩句殘留 0，`攤提供給軸` 句 52 次且全部指名 `weekly_scoped`（與真實供給軸一致）。⑤第②句真偽量測（`qa2/c2_truth.out`）：4000 組隨機形狀中該句印出 1592 次，該軸無授權下的 horizon 皆為 near／mid、0 次為 far，句子為真。突變 E4（③句改回舊字樣）、E5b（①句移除）皆殺；E5（拿掉 `and not held`）存活，見〈四〉P4-A。 | 通過（附 P4-A） |
| C3 幽靈鍵鎖 | `test_context_budget_guard.py:9882` consumers 元組含 `_REPO_ROOT / "tools" / "lib" / "quota_burndown.py"`；`grep -n -F AUTOSDD_QUOTA_BURNDOWN_OFF` 在原五支消費者（`quota_gate.py`、hook 主檔、`session_resume_planner.py`、`relay_machine.py`、`model_roles.py`）GREP_ORIG5_RC=1（零命中），只剩 `quota_burndown.py` 第 12／62 行。突變 E18（把 `quota_burndown.py` 內鍵名全改）⇒ `QuotaEnvFileIsActuallyLoadedTest.test_every_key_in_the_example_is_one_the_code_reads` 轉紅（7 支中 1 支）。 | 通過 |
| C4 事件列 `decided_cap` | `quota_burndown.py:259-260` 欄名 `decided_cap`／`decided_rec`，附註「早於 quota_stability 穩定化」；測試斷言 `assertLessEqual({"decided_cap","decided_rec"}, row.keys())`；突變 E6（欄名改回 cap／rec）殺。全 repo 讀端：`grep EVENTS_NAME／autosdd_burndown_events` 只有寫端與測試（零讀端）。真實事件檔 `~/.autosdd/traces/autosdd_burndown_events.jsonl` 首列仍是舊鍵（19:34:35，未改寫），第二列（21:15:55，主控 `--pace` 寫入）已是 `decided_cap: 2, decided_rec: 1`。 | 通過 |
| C5 清倉生效時不再勸退 | 渲染（real 形狀）：期程行改印 `…（清倉模式生效：cap 不隨 reset 逼近再放寬（遠期減速已由 BD-1 收回））。`、無「改做不吃額度的工作」；降級建議行尾 `（清倉模式下僅供參考，不影響 cap）`。halt 帶維持原句（`test_bd3` 斷言 `停止帶不隨時間放寬`）。突變 E7（分支移除）、E8（halt 也被替換）、E9（hint 尾句移除）皆殺。**但替換條件是「授權在場」而非「binding 軸被放寬」，見〈四〉P3-1。** | 修好原症狀；帶進新措辭誤差（P3-1） |
| C6(a) 派工 hook kill-switch | `hook_ids()` 以 spy 抓 `decide` 的 `burndown` kwarg；無 env 斷言 `[ident]`、`policy_env` 設 OFF 斷言 `[None]`。突變 R1（`quota_gate()` 內 `active(state, now, env, …)` 的 env 換 `{}`）⇒ `AssertionError: Lists differ: ['7cb9bfaea1'] != [None]`；突變 E16（hook 完全不帶落款）亦殺。 | 通過 |
| C6(b) 寫入端 QB4 | `put_cache` 補 `weekly_scoped`（`scope_model="Fable"`）與 `spend`；`test_refusals_never_leave_a_file` 對二者斷言 rc=1＋訊息含 `QB4`、`nope` 含「沒有 kind=nope」、最後檔案不存在。突變 R2（`issue()` 的 QB4 拒絕改 `if False:`）⇒ weekly_scoped 落款成功（rc=0）被抓。沙箱 CLI 實跑：`--issue spend` 與 `--issue weekly_scoped` 皆 rc=1、訊息 `拒絕：kind=… 屬付費保險軸或模型分軌軸（底線②③；QB4：指令不得點名）`、`ls` 無落款檔；`--issue nope` rc=1＋`快取沒有 kind=nope 這一軸（現有：…）`。 | 通過 |
| C6(c) 底線合取項 | `test_every_floor_conjunct_is_load_bearing` 尾段 `five_hour_x`（文法解出 300 分窗、reset 為負）在 decide 層 `pair` 兩格相等＋對照 `five_hour` 兩格不等；另直測 `B._eligible` 五個違規案例＋一個正例。突變 E11（`_eligible` 拿掉 `minutes >= 0`）、E11b（`hold` 去掉 `ok`，即 Dev 的 M34）皆殺。 | 通過 |
| C6(d) `--status` OFF 行 | `B.status(NOW, {OFF:"1"}, path)[1]` 斷言含 `✗ AUTOSDD_QUOTA_BURNDOWN_OFF`。突變 E12（OFF 步驟恆 ✓）殺。 | 通過 |
| C6(e) 裝飾性斷言 | `grep -n "assertGreater(max(d.cap\|assertIsNone(Q._cap_for\|swapped\|wrong\|assertLess(\|split(\"⇒\")\|def loose\|loose("` 於 `test_quota_burndown.py` GREP_DECORATIVE_RC=1（零命中）。 | 通過 |
| SA#1 `issued_at` 帶 offset | `test_issue_status_revoke_roundtrip…` 斷言 `datetime.fromisoformat(rec["issued_at"]).utcoffset()` 非 None。突變 R3（`now.replace(tzinfo=None).isoformat()`）、R3b（`strftime` 無 offset）皆殺：`AssertionError: unexpectedly None : 須帶 offset`。 | 通過 |
| SA#2 `named_resets_at` | `test_valid_then_each_conjunct_breaks_it` 以 `assertEqual(self.active(), burn(), …)` 比整個 `Burn` 六欄。突變 R4（`active()` 的 `named.resets_at` 改 `None`）⇒ `Burn([109 chars]left=7663.0, named_resets_at=None) != Burn(…named_resets_at='2026-10-17T18:20:00+00:00')`。 | 通過 |
| SA#3 needle 四字串 | `test_naming_the_long_window…` needle 含 `發令`／`作用至`／`效期剩`／`must-finish 門檻`。突變 E13／E13b／E13c／E13d（逐一拿掉）皆殺。 | 通過 |
| SA#4 BD-2 拆分量 | `test_bd2…` 的 cap 分量（None 最寬的字典序）與 rec 分量各自 `assertGreaterEqual`。突變 E14（rec 夾層允許下降）、E14c（cap 夾層整體少 1）、E14d（把「不設限」收成 0）皆殺；E14b（`max(b.cap, …)` 去掉 `max`）存活，隨機 59,921 組決策零差異＝等價防禦，見〈四〉P4-B。 | 通過 |
| C7 棘輪列理由 | `_GUARD_LINES_REPIN_LOG` R213 列理由為事實句：`以 R213 標籤記帳（兩鐘關係見證據檔〈三-2〉），R212 主軌餘裕 29`，以八個前瞻／拆輪／日期義務詞的正則掃描，命中 0。「29」我以鎖自己的函式實算：`repin_round_nets` R212＝796、`regression_lane_round_nets` R212＝309、`net_cap_for_round(212)`＝516 ⇒ 516−(796−309)＝29；R213 主表淨額 308＝軌 308（≤ 軌上限 309）、主−軌＝0。 | 通過 |
| C8 逾 TTL 警示 | `quota_burndown.py:320-322`：`age > quota_gate.QUOTA_CACHE_TTL_SECONDS` 時多一行 `⚠️ 快取已逾 TTL（N 秒），落款以快取內的 resets_at 為準`；`issue()` docstring 說明「刻意不改行為」。沙箱 CLI 實跑（快取量測於 30 分鐘前）：rc=0、印 `⚠️ 快取已逾 TTL（1800 秒），落款以快取內的 resets_at 為準`；快取新鮮時無該行。突變 E10（警示永不出現）、E10b（恆出現）皆殺。 | 通過 |

### 一-B 突變總表（複本 `qa2/mut/base`＝`cp -c -R` 自工作樹的 `tools/`、`.claude/hooks/`、`env.shared`、`.env.example`；純文字替換、old 必須恰出現預期次數；每次跑完必還原，終了檢查 6 個被變異檔對工作樹逐位元相同）

驅動器 `qa2/scripts/mut_driver.py`；共 32 個突變：**殺 30、存活 2**。測試指令＝`cd <複本>/tools/tests && AUTOSDD_SENTINEL_OFF=1 python -B -m unittest test_quota_burndown`（`Ran 13 tests`；E18 改跑 `test_context_budget_guard.QuotaEnvFileIsActuallyLoadedTest`）。基準線在複本先跑：13 支與 7 支皆 OK。

| 突變 | 內容 | 結果 | 殺它的測試（逐字檔 `qa2/mutlogs/<id>.log`） |
|---|---|---|---|
| R1 | hook 路徑 kill-switch 的 env 換成 `{}` | 殺 | `test_pace_and_the_dispatch_hook_both_carry_the_directive` |
| R2 | `issue()` 的 QB4 拒絕改 `if False:` | 殺 | `test_refusals_never_leave_a_file` |
| R3／R3b | `issued_at` 去 offset（兩種寫法） | 殺 | `test_issue_status_revoke_roundtrip_and_argument_errors` |
| R4 | `active()` 不帶 named_resets_at | 殺 | `test_valid_then_each_conjunct_breaks_it` |
| E1 | `pace_line` 標題行印全文 | 殺 | `test_naming_the_long_window…`、`test_pace_and_the_dispatch_hook…` |
| E2 | `describe` 忽略 `burndown=False` | 殺 | 同上兩支 |
| E2b | `describe` 預設不帶全文 | 殺 | `test_naming_the_long_window…` |
| E3／E3b | `full_line` 恆空／第二行忘了 `burndown=False` | 殺 | `test_pace_and_the_dispatch_hook…` |
| E4 | ③句理由改回「與被點名軸不同窗」 | 殺 | `test_bd9_authorised_but_inert_says_so_with_reasons` |
| E5 | `_why` 拿掉 `and not held` | **存活** | 無（見〈四〉P4-A） |
| E5b | 「攤提供給軸」句整個移除 | 殺 | `test_bd9…` |
| E6 | 事件列欄名回到 `cap`／`rec` | 殺 | `test_pace_and_the_dispatch_hook…` |
| E7／E8／E9 | 期程行勸退句復活／halt 也被替換／降級建議尾句移除 | 殺 | `test_naming_the_long_window…`（E7、E9）、`test_bd3…`（E8） |
| E10／E10b | 逾 TTL 警示永不出現／恆出現 | 殺 | `test_issue_status_revoke_roundtrip…` |
| E11／E11b | `_eligible` 拿掉 `minutes>=0`／`hold` 去掉 `ok` | 殺 | `test_every_floor_conjunct_is_load_bearing` |
| E12 | `--status` 的 kill-switch 行恆 ✓ | 殺 | `test_issue_status_revoke_roundtrip…` |
| E13／E13b／E13c／E13d | 全文拿掉 發令／作用至／效期剩／must-finish 門檻 | 殺 | `test_naming_the_long_window…` |
| E14 | `_merge` 的 rec 夾層允許下降 | 殺 | `test_bd2…`、`test_bd9…` |
| E14b | `_merge` 的 cap 夾層去掉 `max(b.cap, …)` | **存活（等價）** | 無（見〈四〉P4-B） |
| E14c／E14d | cap 夾層整體少 1／把「不設限」收成 0 | 殺 | `test_bd2…`（E14c 另被三支殺） |
| E16 | hook 路徑完全不帶落款 | 殺 | `test_pace_and_the_dispatch_hook…` |
| E18 | `quota_burndown.py` 內 kill-switch 鍵名全改 | 殺 | `test_every_key_in_the_example_is_one_the_code_reads` |

等價性實測（`qa2/scripts/mut_sweep.py`＋`sweep.py`，同一組種子、59,921 筆決策）：E14b 與原版零差異；E5 有 554 筆文字不同（只差未放寬理由字面，cap／rec 全同）。

### 一-C 不下令時對 HEAD 逐字不變

HEAD 版本＝`git archive HEAD tools/lib` 匯出到 `qa2/head/`，與工作樹版各以獨立行程載入、同一組種子。

| 比對面 | 母體 | 結果 |
|---|---|---|
| `decide` 欄位（cap／rec／band／binding／reason／model_hint／amort／per_axis）、`describe`、`pace_line`、`throttle_horizon_line`、`model_hint_line`、`axes_of` | 800 組隨機狀態（含 halt／unmeasured／畸形 reset／model 三種；amort 非空 61 組） | 零差異；HEAD 無 `burndown` 屬性、工作樹為 `()` |
| 同上六個面 | 真實燃燒帳 `~/.autosdd/traces/quota_burn.jsonl` 443 列×6 變體＝2658 筆（amort 非空 612 筆；唯讀） | `cmp` rc=0，兩份 JSON 逐位元相同 |
| `pace_report` 全文 | 4 個形狀（real／proto／halt／low）×3 個 model（無／fable／sonnet）＝12 份，固定 now、每份全新隔離痕跡目錄 | 零差異 |
| 燃燒帳列 `row_of()` | 單列 | **有差異**：工作樹每列多 `"bd": null`（無授權也有）。附錄注⑤已承認「row_of() 加 bd 欄」；見〈四〉P3-4 |

## 〈二〉閘門指令與 rc 逐字

工作目錄 `/Users/wuweihong/Antigravity/AISDCL_Agent`；每條 rc 單獨印、輸出先導檔再讀；`TMPDIR` 指向 scratchpad 以免全套期間的真實 TEMP 被我自己動到。

| 指令 | 結果 |
|---|---|
| `cd tools/tests && AUTOSDD_SENTINEL_OFF=1 python -B -m unittest test_quota_burndown test_quota_policy test_quota_env_layers test_context_budget_guard test_adr_xplat001_c1c2_lock` | `B1_RC=0`；`Ran 1387 tests in 77.657s`／`OK`（11 項略過）；`[Scan-H triplet] UEP=5 AC=47 GLC_FILES=93 GLC_LINES=116737` |
| `unset AUTOSDD_PARALLEL_TESTS; AUTOSDD_SENTINEL_OFF=1 python tools/run_root_unittests.py > <log> 2>&1; echo RC=$?`（背景跑到真的結束，兩輪；第一輪 21:18:00～21:20:05，第二輪 21:39:31～21:41:31；皆在本檔落地前的樹上） | 兩輪皆 `RC=0`；`✅ unittest 數量下限釘選通過：發現 5351 個測試（下限 5326）`；`[cpu_budget] root-unittest workers=9`；`[skip census] tools/tests@darwin 共 47 支：platform=47／tool-absence=0／env-disabled=0／structural-pair=0／debt=0／untagged=0／欠債型 0 支（目標 0）`；`✅ 真實 TEMP 圍籬：…零變動`。套件自己的 leak-fence 列（`~/.autosdd/traces/autosdd_leak_fence.jsonl`）：`{"at": "2026-10-12T21:20:05+0800", "rc": 0, "new_temp_files": 0, "carrier": "launchd", "jobs_before": 2, "jobs_after": 2, "leaked_jobs": [], "fence_rc": 0}` 與 21:41:31 同形。第二輪前後樹指紋相同（`git diff HEAD` 雜湊前綴 9c2f1594709609dd；改動檔 mtime 清單雜湊前綴 71e28dd44eaf87b7）。第一輪視窗內證據檔 mtime 為 21:18:46，故再跑第二輪以確認現樹 |
| `cd AutoClaude && python -m pytest tests/test_r86_pace_contract.py tests/test_model_roles.py tests/test_r100_boot_self_check.py -q -p no:cacheprovider`（照任務書原樣） | `AC_AS_GIVEN_RC=5`、`no tests ran`：任務書點名的 `tests/test_model_roles.py` 不在 `AutoClaude/tests/`（實際位置 `tools/tests/test_model_roles.py`，是 unittest 模組），路徑筆誤、不是產品問題 |
| 同上、拿掉不存在的那個路徑 | `AC_EXISTING_RC=0`；`147 項通過 in 1.79s` |
| `cd tools/tests && python -B -m unittest test_model_roles`（含 `ModelHintLineTest`，Dev-2 自報曾因 `SimpleNamespace` 替身無 `.burndown` 造成 4 個 ERROR） | `MODEL_ROLES_RC=0`；`Ran 60 tests`／`OK`：已修好（`model_hint_line` 以 `getattr(decision, "burndown", None)` 取值） |
| `ruff check tools/` | `RUFF_RC=0`；`All checks passed!` |
| `python AutoClaude/tools/check_loc_budget.py --json` | `LOC_RC=0`；`root_tools_violations []`／`tier_violations []`／`special_violations []`／`absolute_violations []`／`total_violation False`；以檢查器自己的 `count_loc` 量：`quota_gate.py` 499（hub 上限 500，餘 1）、`quota_messages.py` 391（lib 上限 400，餘 9）、`quota_burndown.py` 260、`quota_policy.py` 301、`quota_pace.py` 368 |
| `python tools/check_pytest_baseline_sites.py` | `BASELINE_SITES_RC=0` |
| `python tools/check_defect_log_crossref.py` | `CROSSREF_RC=0`；`具名治理文件 172 份皆已登記且未逾體積上限`（**本檔寫入前**；本檔落地後需登記） |
| `python tools/check_handoff_carriers.py` | `CARRIERS_RC=0`；`commit 訊息＝757 則；其中含前瞻延後宣告 0 筆` |
| `python tools/check_ntfs_paths.py` | `NTFS_RC=0`；`NTFS 檔名檢查通過（28002 個 tracked 路徑，0 違規；最長 142 字元）` |
| `python tools/lib/quota_policy.py --env-doctor` | `ENV_DOCTOR_RC=0`；清單含 `AUTOSDD_QUOTA_BURNDOWN_OFF = （空）〔factory〕`；提示 `[empty-local] .env 已無任何有值的行`（本機既有狀態，與本列無關） |
| `python tools/lib/quota_burndown.py --status`（真實環境，唯讀） | `STATUS_REAL_RC=0`；落款 45c49b8e35、六項判準全 ✓、效期剩 7465 分鐘；本機當下週軸已 86%：`本次放寬：kind=session band prepare→converge cap 2→4 rec 1→2、kind=weekly_all cap 1→2 rec 1→1、kind=five_hour …、kind=seven_day cap 1→2 rec 1→1`（＝一審 SA P3-1 預告的「效果帶之外」形狀）。指令前後 `~/.autosdd` 檔案快照 diff rc=0（零寫入） |
| `launchctl list \| grep -c AutoSDD_Sentinel_`（開工前／第一輪全套後／第二輪全套前後／收尾） | 皆 `2` |

## 〈三〉文件面抽驗

### 三-A 一審各鏡「必改」項對帳

| 一審項 | 對應改動（我讀到的座標） | 判定 |
|---|---|---|
| Architect P3-01 驗收定義歸屬 | 主檔 `CrossPlatform_R212_WakeChain_EnvLayer_Evidence.md` 〈二-0〉第 3 點追記「定義歸屬…未經掌舵者明示追認」；本列證據檔〈六-1〉第三層根因＋〈六-5〉題一 | 已改 |
| Architect P3-02／QA P3-3／SA P3-2 A4「cap 由 1 升至 cap_converge」 | PRD A4 列：`決策 cap 1→cap_converge（=4）；--pace 標題 cap 1→2（quota_stability 遲滯，每 ≥300 秒 +1 至軸值）、現在可派 1→2（rec 封頂 cap_prepare，不是放到 8）`；v2.1.19 列同 | 已改 |
| Architect P3-03 完成字樣先於審查結論 | v2.1.19 列改為「4×APPROVE、無 P≤2、P3 全數於同批處置」；〈五-3〉〈八-2〉仍是佔位列（尚未填寫）——提交前必須填，見〈四〉P3-7 | 部分（佔位列是預期狀態） |
| Architect P3-04／SA P3-9 §6.1／§11.2／§11.3／§15.5 列 | PRD diff：§6.1 列追記「【2026-10-12 第五列訂正】殘存再開症狀…」；§11.2 加「📎 定義下交付物由 decide＋性質測試承接」；§11.3 改寫並引用既有 `AutoClaude/tests/integration/test_sigint_checkpoint.py`（我核對：檔存在、`_SLA_SECONDS = 2.0`、量真實落盤路徑）；§15.5 改成「唯一資料殘留＝紅線 11 清單」 | 已改 |
| Architect P3-06／07／08（附錄） | 附錄〈落地訂正注〉①～⑤：③建構順序（§5④ 字面作廢）、②BD-2′ 定義、④`resets_at` 前提與真實語料不符。我以真實燃燒帳重算：weekly_all 206 列 206 個相異字串；> 1 小時的跳動只有 168 小時（週翻頁）與一次 −20 小時、一次 +20 小時（＝「1 次提前 20 小時、1 次後移 20 小時」屬實）；同窗鄰軸字串全等 weekly_all＝seven_day 206／206、session＝five_hour 204／204、weekly_all＝weekly_scoped 0／205（注④屬實） | 已改且屬實 |
| Architect P3-09 `BURNDOWN_CAP_CEILING` 未做 | 證據〈三-1〉(e)、附錄注①、PRD A4 劃界句 | 已改 |
| Architect P3-11／SD P3-6 棘輪標籤記載 | 證據〈三-2〉後果 (i)～(iv)：餘 1 行、R213 為最後未觸發到期義務標籤、單輪內 +796＋308＝+1104（我驗：796＋308＝1104）、理由欄改事實句（C7） | 已改 |
| Architect P3-14／QA P3-11／SA P3-3 暴露證據時序 | 〈二-1〉改寫為「畫面為主控自跑、先於指令約 3 分鐘…暴露證據的主體＝掌舵者指令＋sid」；〈三-3〉判讀 (1)「不是同一組讀數；同讀數反事實由兩鏡以 readings_at_issue 重算」；PRD v2.1.19／A4 同 | 已改 |
| SD P3-1～5、Architect P3-05／10／12／13、QA P3-6／7／8 | 程式面 C1～C8，見〈一〉 | 已改且驗證 |
| QA P3-4 §16.3 (b) 快照時點 | PRD diff：`（合計 101；v2.1.17 當日快照，其後轉格見修訂表 v2.1.18／v2.1.19，本格不重算）`。我獨立重數 §16.2 表：72 列＝➖33／⏸29／📎8／✅2，加矩陣原判 ✅29 列＝✅31／➖33／⏸29／📎8＝101，與證據〈六-2〉相符 | 已改 |
| QA P3-10 新檔登記 | `governance_docs.py` 新增 5 筆；`CROSSREF_RC=0`（172 份皆已登記） | 已改（本檔另需登記） |
| SA P3-1（必改）效果帶 | PRD A4 列「效果帶＝被點名軸低於 prepare 錨點（出廠 85%）；≥ 錨點時授權只把該軸 cap 1→2、現在可派維持 1」；證據〈三-3〉(2′)、〈三-4〉（真機 21:14 週軸 86% 的逐字畫面）、〈六-5〉題二向掌舵者提問 | 已改 |
| SA P3-4／5／7／8／10 | PRD A4 劃界（§7 草案文字不在本版射程、操作入口三條指令＋kill-switch）；測試四條補牙；〈六-2〉逐機制 E2E 分級表＋白話結論；〈一〉(c) 改 T1＋T4 同時成立 | 已改 |

### 三-B 〈六〉措辭有無過度樂觀

- 〈六-2〉「每個功能都已 E to E 驗證不成立；成立的是喚醒鏈尾段在 Mac 整段走過…」：不樂觀，與一審 SA 的分級一致。
- 〈六-5〉兩題交掌舵者裁決、主控各給建議：未代決，措辭合規。
- PRD A4 轉 ✅：列內以「效果帶」限定，且〈三-4〉如實貼出真機現況（週 86%、現在可派 1）。觀察（不改判）：該列的字面再開症狀是「下清倉指令而 `--pace` 仍壓在 cap≤2」，在效果帶之外（本機現況）仍然成立；文件已誠實限定並把 prepare 帶放寬交由〈六-5〉題二，因此我把 ✅ 讀作「效果帶內 ✅」。回覆掌舵者時不宜只說「清倉模式已解決」。
- 〈六-2〉表「清倉模式」列尾寫「14 項」是修復前的測試數，現為 13 項：見〈四〉P3-2。

### 三-C 掃描

- 新文件（證據檔、附錄注、PRD diff、四份一審 findings）對「數字緊接通過／略過的英文字面」（pytest 摘要行寫法）掃描 rc=1（零命中）。
- 前瞻與拆輪句型掃描（九個詞的正則）：證據檔 2 處（見〈四〉P3-3），附錄與 PRD diff 零命中。
- 「某平台零真機」型：SC-9 機械鎖綠；寬鬆掃描（平台名＋零／0 筆／未驗＋真機／樣本／量測、整行無輪次界定）在證據檔命中 2 行（見〈四〉P3-5）。

## 〈四〉新 P3／P4

### P≤2

**無。** 我評估過、判為不升級的一項：C5 替代句條件過寬（P3-1）。依 `severity.md`，P3＝「訊息誤導，但一次呼叫內即可恢復」，且 cap／rec 不受影響；不是錯誤決策／漏攔／誤擋。

### P3

**P3-1 C5 替代句以「授權在場」為條件，而不是「binding 軸被放寬」。**
- 座標：`tools/lib/quota_messages.py:577-579`（`throttle_horizon_line` 內 `if decision.burndown and not halted:`）、`tools/lib/quota_burndown.py:73`（`NOTE_HORIZON`）。
- 重現：`qa2/scripts/c5_inert.py`（純函式）。形狀一：週 78%／短窗 29%＋Fable 分軌軸 90%，model=fable，點名 weekly_all。有、無授權的決策皆 `cap=1 rec=1 binding=weekly_scoped`（授權只把 weekly_all 放寬 cap 2→4；binding 的分軌軸逐格不動），期程行卻印 `清倉模式生效：cap 不隨 reset 逼近再放寬（遠期減速已由 BD-1 收回）`、並省略「改做不吃額度的工作，或降扇出／切小模型」。該 binding 軸在 far 視野（cap 階梯 prepare：far 1／mid 2），cap 其實會隨 reset 逼近放寬，無授權時的原句才是真話。形狀二：08-28 原型（effect＝inert，`qa2/render_pace.out` 的 proto／fable 段）同一份輸出第 2 行寫「本次未放寬任何軸」、第 6 行寫「遠期減速已由 BD-1 收回」，自相矛盾。
- 真實語料（`qa2/scripts/c5_real.py`，唯讀）：真實燃燒帳 206 列×4 變體（r 無／5.0×model 無／fable，點名 weekly_all）中，期程行被替換的 251 筆決策裡，binding 軸確實被放寬 88 筆、**沒有被放寬 163 筆（65%）**。已有真實語料命中，依〈守衛面准入〉可當輪改字、不必降 P4。
- 判準：`severity.md` P3（訊息誤導、一次呼叫內可恢復、cap／rec 不變）。這是一審 SD P3-5（勸退句）的修法帶進的新誤差：觸發條件寫成授權在場，涵蓋了授權對 binding 軸沒有作用的情形。誠實限定：163 筆是「真實讀數＋我造的授權」的反事實重放，不是某次真實 `--pace` 的逐字輸出；主控 21:14 的真實 `--pace`（證據〈三-4〉）binding 軸 seven_day 有被放寬，那一次句子為真。
- 建議處置（擇一）：(A) 替換條件改為「binding 軸 kind 在本次已放寬的軸集合內」（`Applied` 加一欄已放寬 kind 的元組，或由渲染端另取），不成立時沿用原句含勸退句；這是修正本批自己新增的文字、仍在 DEF-200-528 的准入證據之下，成本 `quota_burndown.py` 餘裕足、`quota_messages.py` 餘 9 行、補測併進既有斷言行（回歸鎖軌餘 1 行）。(B) 若主控判定這已觸及〈守衛面准入〉（重放含造出來的授權），改在證據檔〈七〉登記為 P4 並註明「期程行替代句只在 binding 軸被放寬時為真」，不動碼。兩者都不影響本檔判決。

**P3-2 〈六-2〉表「清倉模式」列的測試數過期。** 座標：證據檔〈六-2〉表「清倉模式（A4，本列轉 ✅）」列尾「14 項」。重現：`Ran 13 tests`（複本基準與工作樹皆是；Dev-2 報告 §3 也寫 14→13）。處置：改「13 項（修復包後）」。

**P3-3 前瞻拆輪字樣殘留在證據檔。** 座標：證據檔〈三-2〉轉述鎖的三個出口時，第②項的名稱帶前瞻拆輪字樣，〈三-2〉末段關於再動 `tools/tests` 須重釘的句子是操作規則、不計。一審 SD P3-6 的意旨是去掉此類字樣（鎖列理由欄已改事實句，我驗過）。處置：第②項改寫為「②改記在新標籤名下」，或加引號標明是鎖的原文。

**P3-4 PRD v2.1.19「不下令時輸出逐位元不變」範圍過寬。** 座標：PRD 修訂表 v2.1.19 列「共 8 處預設不生效的簽章／欄位…不下令時輸出逐位元不變〔SD 鏡 6000 組隨機狀態〕」。重現：HEAD 與工作樹的 `quota_pace.row_of(...)` 單列輸出，工作樹多 `"bd": null`（我印出兩行對照）；SD 鏡的 6000 組只涵蓋 `decide`／`describe`／`pace_line`／`axes_of`。附錄注⑤已承認「row_of() 加 bd 欄」。處置：PRD 該句限定為「decide／describe／pace_line／axes_of 的輸出」，並寫明燃燒帳每列多 `bd: null`。

**P3-5 「某平台零真機」型措辭兩處無輪次界定。** 座標：證據檔〈六-3〉「Windows 仍 0 筆真機樣本（主檔〈八-4〉六項）」、〈六-6〉「收斂是症狀驅動、Windows 零量測、…」。SC-9 的正則（`_SC9_CLAIM_RE`：零／無／沒有… 後接 真機／實機）抓不到這兩種寫法，語意同型；〈六-2〉同節另一處已寫「R212 範圍內 0 筆樣本」。處置：兩行各加「（R212 範圍內）」。

**P3-6 〈四〉表頭「判決首行（逐字）」與 Architect／QA 兩格不符。** 座標：證據檔〈四〉表 Architect 列「VERDICT: APPROVE（無 P≤2；14 項 P3…」、QA 列「VERDICT: APPROVE（無 P≤2；P3 共 11 條、P4 共 8 條）」。重現：兩檔第一行都只有 `VERDICT: APPROVE`，括號內是第二行理由或轉述。另〈四〉QA 列「65 個突變殺 53」：QA 檔〈五-4〉寫共 65 個、1 個無效、有效 64 個殺 53。處置：欄名改「判決（首行＋理由摘要）」，QA 列改「有效 64 個突變殺 53」。

**P3-7 佔位列尚未填寫（程序項）。** 座標：證據檔〈五-3〉QA 二審、〈八-2〉commit／push／雲端對帳兩處仍是佔位。處置：本檔落地、主控填妥兩處並登記本檔後再提交（Architect P3-03 原意）；填〈五-3〉時請用本檔第 1 行的判決與〈一〉～〈四〉的數字。

### P4 理論洞（只登記；各附一句可觀測再開症狀）

| # | 洞 | 暴露度 | 再開症狀 |
|---|---|---|---|
| P4-A | `_why` 第①句（`攤提供給軸 kind=X 不 qualifying`）與第③句（`攤提在此帶未收緊`）的分界 `and not held`（`quota_burndown.py:162`）沒有測試釘住：突變 E5 存活，59,921 組隨機決策中 554 組文字不同、cap／rec 全同（只差未放寬理由字面）。已有的 `test_bd9` 只釘住原型 fable／sonnet 兩個形狀，兩者的基準讀數都沒有 `amortized` 註記，碰不到這條邊 | 突變量測；真實燃燒帳重放 824 筆中 0 筆舊句殘留，本邊的真實命中未量 | 清倉全文的「未放寬」理由出現「攤提供給軸 kind=X 不 qualifying」，而 X 其實屬被點名軸的同窗集合（附 `--pace` 畫面） |
| P4-B | `_merge` 的 cap 夾層 `max(b.cap, min(top, p.cap_notice))` 的 `max(b.cap, …)` 在放寬只上行、Policy 不變式（cap_notice ≥ 各階 cap）成立時不可達：突變 E14b 存活，59,921 組隨機決策零差異＝等價防禦 | 突變量測（等價） | 無（不是缺陷）；日後簡化或放寬 Policy 不變式時才需要重做等價證明 |

## 〈五〉開了→收了

| 開了 | 收了 |
|---|---|
| 根層全套兩輪（背景指令，前台等到結束；各產出 `qa2/qa2_root.log`、`qa2/qa2_root2.log`） | 兩輪皆已退出；`pgrep -f 'run_root[_]unittests'` rc=1（無殘留行程） |
| 全套自測的紅路徑落檔 `tools/.last_failure_8395affa_20261012T13*.log` 六份（gitignored；內容為 runner 自測故意失敗的 `test_p8fx8` ImportError；時間戳全在我兩輪全套視窗內） | 已逐一 `rm`；`ls tools/.last_failure_*` 已清空；`git status --short` 前後皆 23 行、與開工快照相同；未改任何 tracked 檔 |
| scratchpad 複本 `qa2/mut/base`（`cp -c -R`）、`qa2/head`（`git archive HEAD tools/lib`）、`qa2/sbx_cli`（CLI 沙箱）、`qa2/tmp`（`TMPDIR`） | 不入庫、留作重現；突變後終了檢查 6 個被變異檔對工作樹逐位元相同；session 結束隨 scratchpad 清除 |
| 沙箱內的 `--issue`／`--revoke` | 只寫 `qa2/sbx_cli` 與渲染腳本的圍籬隔離根；真實落款檔 `~/.autosdd/traces/autosdd_burndown_directive.json` mtime 19:34 未變、`--status` 仍回 45c49b8e35 |
| launchd 哨兵 | 2→2→2→2；套件 leak-fence 兩列皆 `leaked_jobs []` |
| `~/.autosdd` 整段期間差異 | 我的指令內容零寫入（我的程序全程用隔離環境變數或圍籬、網路原語必拋）。差異來自：套件自己的 leak-fence 列（`autosdd_leak_fence.jsonl` 兩列）；harness 的 hook 對每次工具呼叫（含本子 agent 的）觸發的自身寫入與哨兵巡邏自己的寫入（`context_feed/<sid>.json`、`autosdd_quota_availability.json`、`autosdd_quota_stability_fable.json`、兩份 `autosdd_sentinel_launchd_*.log`），以及真實 `~/autosdd_quota.json` 在 TTL 到期時由 hook 自己刷新（同一檔案大小、mtime 前進）。落款檔、事件檔、燃燒帳在我的視窗內零變動 |
| 網路 | 零：渲染腳本把 `quota_meter` 取數原語與 `urlopen`／`create_connection` 換成必拋例外，未觸發 |

未做：Windows 面（cp950 主控台、`quota_gate.py` 直接 import `quota_burndown` 的載入）；真實 `--pace`；AutoClaude 全套 pytest（只跑契約兩檔）；pre-push 全套（只跑根層全套與靜態閘）；Dev-2 自報的 97 個突變未重跑（我另做 32 個，涵蓋任務書點名的四個與各 C 項）。
