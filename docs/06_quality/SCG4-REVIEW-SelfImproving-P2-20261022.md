# SCG-4 實作審查報告：SelfImproving P2（鍵 `monorepo-si-p2-gate-apply`）

| 項目 | 值 |
|------|----|
| 審查對象 | 工作樹（P2 主體＋修復棒一／二；commit 前，HEAD `28298bee`）；落地 commit 見〈§L 主控處置〉 |
| 凍結基準 | P2 TCS `docs/03_testing/contracts/TCS-SelfImproving-P2-20261021.md`（Stage-2 digest `c261740974adb1d3839e87f05c558e79f4df119d5fae08de2896ae2148b5b8ca`；勘誤一後重凍 digest 見 §L）；PRD v0.10（`1d26dbf8…`）；Operations SOP——QA 以 CRLF→LF 位元組重算 TCS／PRD，皆相符 |
| 審查者 | QA（Sonnet 子代理，唯讀審查；突變、複本、探針全在 scratchpad `si_p2\qa_p2\`；審查前後 `git status --short` 逐位元相同） |
| 一審判定 | **FAIL**——P1／P2／P3／P4 ＝ 0／1／5／4（D-01 `test_apply_lock.py` 腳本入口不在檔尾） |
| 二審判定 | 見 §M |
| 落檔說明 | §A～§H 由主控自 QA 的文字交卷（`qa_p2_scg4_verdict.md`）逐字落檔（harness 規則：子代理不得寫 docs），§M 同自 `qa_p2_scg4_verdict2.md`；QA 的稽核腳本、複本與原始輸出住 scratchpad，收輪即刪，本檔是唯一留存的證據 |
| 主控處置 | 見〈§L 主控處置〉（修復棒一／二、護欄層重釘、勘誤一、gate 走向） |

> 數字口徑：§A～§H、§M 所有量化數字皆為 QA 子代理當回合真跑的輸出（主控未逐一重跑，標 `[他包回報]`）；主控親驗的數字只寫在 §L。



> 審查範圍：實作（工作樹＋index，未 commit）對凍結 TCS `docs/03_testing/contracts/TCS-SelfImproving-P2-20261021.md`、PRD v0.10、Operations SOP。
> 全部數字為本窗口 2026-10-22 真跑所得（指令與 rc 見 §D）；Developer／主控的回報一律當 `[他包回報]`，已重跑或重算。
> 審查用的突變、複本、探針全在 `…\scratchpad\si_p2\qa_p2\`（repo 一檔未動，見 §G）。

## §A 摘要與判定

**總判決：FAIL**（P1＝0、**P2＝1**、P3＝5、P4＝4 筆〔D-07～D-10，D-09、D-10 各為小項彙整〕）。任一 P2 即 FAIL；修法皆小，不需動規格。

| 嚴重度 | 筆數 | 一句話 |
|---|---|---|
| P1 | 0 | 安全不變量（UNATTENDED、K=1 真人引言、HMAC、晉升前提、回滾還原、沙盒隔離、held-out 盲性）讀碼加突變皆成立 |
| **P2** | **1** | **D-01**：`tools/tests/test_apply_lock.py` 的 `if __name__ == "__main__": unittest.main()` 不在檔尾，違反 TCS NFR-P2-10 (14)／V4 判準；腳本模式只跑 7／14 個測試（新增的 7 個 AT-240-8-* 全被靜默略過、`-k AT_240_8_1_` 得 `Ran 0 tests … OK`） |
| P3 | 5 | D-02 目錄項債 37→43 的規格依據不實且 `verify.py:143` 無轉碼、`sandbox.py:269-270` 半換入失敗不還原；D-03／D-04 兩個 AT 有未釘住的 Then（突變存活）；D-05 交卷缺〈流程摩擦〉節；D-06 測試內字面 `PROP-SI-999` 不在真帳本 |
| P4 | 4 | 文件漂移與字面層小項（D-07 SOP 第 65 行、D-08 rc 3 預檢先於無人值守、D-09 弱斷言彙整、D-10 流程與框架缺口） |

**必查項一覽**：1 PASS（附 D-03／D-04）｜2 PASS｜3 PASS（附 D-08）｜4 PASS（存活突變 3 筆：2 組等價、1 組真缺口＝D-04）｜5 PASS（D-01 與其同檔，但屬腳本入口，不影響 R100 判準）｜**6 FAIL（P3：D-02）**｜7 PASS（附 D-07）｜8 完成（〈勘誤〉建議 20 條＋1 條備選，見 §E）｜9 PASS（A、B、C）｜10 PASS。

**放行條件**（重審範圍）：修 D-01（把 `unittest.main()` 守衛移到 `test_apply_lock.py` 檔尾）後，僅需重跑 §D 的 D-01 驗證三行與 SI 全測；D-02～D-06 可同輪一併收（建議），也可由主控裁量降為帳本承接。D-02 若選「保持 43」則須改正 `test_platform_neutral_paths.py:3701` 的規格出處註解。

## §B 必查項逐項

### B-1 AT 覆蓋對帳：PASS（附兩筆 P3 鑑別力缺口）

- Developer 的 `at_missing.py` 只比 `def test_<AT 底線形>` 子字串，會被前綴相同的兄弟 AT 遮住缺口，我不採信；重跑得 `137 ATs; 0 missing`（rc 0）僅作對照。
- **自建的錨定計數**（`qa_p2\qa_at_anchor.py`：對 TCS 每個 AT 的 `-k` 值，以各測試檔 `--collect-only` 的節點 id 做不分大小寫子字串比對，並驗 `-k` 值＝AT 底線形接結尾底線）：137 條**全部恰命中 1**，0 條不合（R102 (c)(d)）；各檔 AT 數 apply_lock 7／capability 3／console_obs 23／decide 18／events_p2 24／p2_meta 12／promote 13／research_scan 5／sandbox 11／verify 21＝137。TCS 無兩位序號 AT（R102 (e) 空集）。
- **逐條字面實跑**（`qa_p2\qa_k_literal.py`，`python -m pytest tools/tests/<檔> --collect-only -q -k <值> -p no:xdist -o addopts=`）：137 次全部 rc 0 且恰收 1 個函式（62 s）——超出任務書要求的 30 條抽樣，涵蓋每個 D 項與含 `E_1`…兩位 AC 號（`AT-240-10`～`AT-240-15`）者。
- **讀測試本體 25 條**（分佈：D5 `AT-215-1-E-2`、`AT-215-1-E-3`；D6 `AT-219-1-E-2`、`AT-219-1-E-1`、`AT-219-2-E-1`、`AT-217-1-E-2`、`AT-220-4-1`；D7 `AT-216-1-E-2`、`AT-240-7-1`；D8 `AT-235-2-E-2`、`AT-233-1-E-3`；D9 `AT-240-3-E-1`；D10 `AT-240-5-E-1`；D11 `AT-240-8-1`、`-2`、`-3`、`-E-1`、`-E-2`、`-E-3`、`-E-4`；D12 `AT-213-2-E-1`；D13 `AT-240-4-E-1`；D15 `AT-240-13-E-1`；D14／D16 `AT-240-14-1`；修復棒一 `AT-240-2-E-3`）。判定：
  - 逐字釘住 TCS Then 者 23 條（其中 4 條附 P4 小弱點，見 D-09；例：`AT-215-1-E-2` 的 (a)～(n) 碼表、rc、`keep.txt`、競態；`AT-216-1-E-2` 的八情境加還原對照組加 `check` NE；`AT-235-2-E-2` 的 `os.replace` 恰 1 次、tmp 清、鎖釋放、無 `time.sleep`；`AT-240-8-E-1`～`E-3` 的「其他 `OSError` 不被吞」）。
  - **無「只有 rc 0 而不看輸出／事件」型**（任務書的 P3／P2 閾值型）：0 條。
  - 另有兩條 Then 子句未全釘（**突變實證存活**）：`AT-217-1-E-2`（D-03）、`AT-240-3-E-1`（D-04）。同型數 2＜3，不升 P2。
  - 小弱點（P4，D-09）：`AT-240-13-E-1` 的 `REQ-2` 前綴過鬆、`AT-240-8-E-4` (c) 未斷言「持鎖者資訊」、`AT-215-1-E-3` 未記錄危害見證、`AT-217-1-E-2`／`AT-219-2-E-1` 未斷言 PROP 態與 `obs-draft:`。

### B-2 閘門重跑：PASS（全部 rc 0，輸出見 §D）

- SI 全測：`332 passed, 1085 subtests passed in 273.74s (0:04:33)`，rc 0（`-n 4 --dist worksteal`，14 檔）。
- `check --json`：`overall=PASS rc=0 items=32`；`events.dec_quote`／`events.dec_console`／`events.verdict`／`obs.console_audit`／`params.keys` 皆 PASS（真 repo 無 Console 事件，故 `dec_console`、`console_audit` 為空 PASS，符合 R98 (d) 末句）；`ref.carrier_families` 為 nonblocking NE（`families=DEC-SI count=2`，R104 (a)）；三次牆鐘各 2.5 s（V2 ＜30 s）。
- `check_loc_budget.py --json` rc 0（total 18633／cap 20438、`total_violation=false`）；ruff（lib 全樹＋入口＋apply_lock＋全部 SI 測試與夾具）`All checks passed!` rc 0；`git diff --check`、`git diff --cached --check` 皆 rc 0、零輸出；`sync_onboarding_baselines.py --check-snapshot` rc 0。

### B-3 安全不變量：PASS（逐項讀碼加對應 AT／突變；唯 (a) 附 P4 D-08）

| 項 | R | 證據（檔案:行號） | 判定 |
|---|---|---|---|
| (a) 無人值守 | R70、R81 | `decwrite.py:64-69` `refuse_unattended`（值非空含 `0`）；九個動詞皆呼叫：`decwrite.py:203`（decide）、`369`（card --issue）、`obswrite.py:47`（obs-add／obs-close）、`promote.py:66`（promote／rollback）、`sandbox.py:218`（sandbox）、`sandbox.py:337`（heldout-freeze）、`verify.py:158`；`obs-add --dry-run` 不經此（CLI `_obs_dry_run`，`tools/selfimproving.py:291-311`）。AT-215-1-E-2 (h) 斷言家目錄逐檔位元組不變 | PASS（rc 3 預檢先於拒收：D-08） |
| (b) K=1 只認真人 | R77～R79、R80 | `transcript.py:107-134` `human_of`：`type=user` 須頂層 `origin.kind=human` 且非 `isMeta`、無 `origin` 的 `tool_result` 拒；`attachment` 須 `queued_command` 且 `attachment.origin.kind=human`；`origin` 缺＝NE `ORIGIN-MISSING`；`decgrammar.py:89-103` 唯一合法決定行；`decverify.py:117-134`、`169-178` fail-closed（`ne` 非 `TRANSCRIPT-UNAVAILABLE`／`CONSOLE-*` 者亦轉 `DEC-VERIFY-FAILED`）；`decwrite.py:200-254` 不收引言文字、`--reason` | PASS |
| (c) 沙盒隔離與預檢 | R84、R85 | `sandbox.py:52-88`（`..`、絕對、`:`、控制字元、尾點空白、非一般檔與目錄、重名、路徑過長；`tarfile.data_filter` 缺＝rc 3 不降級）、`172-183`（根不得在 repo 樹內或 `.claude/worktrees/`；清理目標不得為連結）、`241-252`（暫名在 `<si>/sandbox/`、tar 在旁）；`manifest.py:19-55`（位元組序排序、原始式與 LF 式、`absent`、259 邊界）。突變 D5-M1（`touched_ok` 恆真）被 `AT-215-4-1` 抓到 | PASS |
| (d) held-out、三態、參數鍵 | R83、R88、R89、R106 | `sandbox.py:305-379` `heldout_freeze`（`FROZEN-BY-PROPOSER`、`HELDOUT-EXISTS`、`-AFTER-SANDBOX`、`-FROM-INSIDE`、`-LINK`；暫名目錄換入）；`heldout.py:114-142`；`verdict.py:45-62`（⓪→①→②→③→④→⑤、FAIL 只來自測得失敗）；`verify.py:107-123`（`VERIFY-RUNS-EXCEEDED`）；`params.json` 只多 `"probe_timeout_seconds": 600`、`"verify_runs_max": 2`（`git diff` 兩行）；`params.py` `PARAM_SPECS` 兩鍵 `int1` | PASS |
| (e) promote／rollback | R91、R92 | `promote.py:154-185`（`head_sha`＝`Git.head()`、`pre_sha256`／`post_sha256`＝LF 式 manifest、`unverified_ack`＝所消費 `dec(promote)` 的 `flags`、鎖內重驗、事件失敗 `cleanups` 反向套用、不 commit）；`206-244`（`TREE-CHANGED` 外層加鎖內雙驗、`ROLLBACK-NOT-EXACT` 還原回去）；`AT-240-7-1` 三種（改既有檔／新增檔／M 類）逐位元還原 | PASS |
| (f) Console HMAC 與 STALE-CARD | R94、R95 | `consoleaudit.py:142-151`（`hmac.compare_digest`、空環＝`AUDIT-KEY-MISSING` 不降 NE）、`101-131`（驗證順序同 R94）；`decwrite.py:277-320`、`307-308`（`STALE-CARD`）；`decheck.py:80-93`（回查：欄位不符先於金鑰缺席）。突變 D8-M1／M2／M5 被抓到 | PASS |
| (g) 冷卻與 `unblock` | R82 | `cooldown.py:68-113`（最嚴「未說明」只能 `unblock`、(b-2) 三條件）、`decwrite.py:86-87`（`NOT-IN-COOLDOWN`）、`fold.py:218-219`。突變 D3-M1 被 `AT-213-2-E-1` 抓到 | PASS |
| (h) CAPABILITY 40 鍵 | R105 | 登記表 40 鍵＝29 ro／7 rw／2 net／2 exec，與磁碟 `tools/lib/selfimproving/*.py` 40 檔逐一對應（registry-only／disk-only 皆空）；`exec`＝`runner.py`、`verify.py`；`capability_problems(真套件)`＝`[]`；突變 D10-M1 被抓到 | PASS |
| (i) `non_evolvable_globs` | R106、R109 | `params.json` 的 `non_evolvable_globs`、`spec_body_globs` 與 HEAD 逐值相同（`json.dumps(sort_keys)` 比對 True） | PASS |
| (j) `subprocess`／`socket` 範圍 | R87、R105 | `subprocess` 只在 `git.py:12,59-66`（ro）與 `runner.py:15,62,86`（exec）；`socket`／`urllib`／`http` 只在 `fetch.py`（net）；`runner.py:20-56` 環境白名單（無 `AUTOSDD_*`）、`PYTHONPATH` 只有沙盒根、不帶 `-I`／`-P`；`runner.py:59-69` 兩條殺行程樹各在 `sys.platform` 分支內 | PASS |

### B-4 突變自證複核：PASS

**做法**：`mut.py` 直接改寫真實樹（`REPO=D:\…`，`finally` 還原），審查唯讀規則下**不跑**；改以 `qa_p2\qa_mut.py`（同邏輯，`REPO` 指向 scratchpad 複本 `repo_copy1\`，並補拷夾具依賴的 `AISDLC_SDD/scripts/sdd_version.py`）重做。複本基線 `AT_216_1_E_1_` 綠（`1 passed, 15 subtests`）。每筆都附「突變後 rc／還原後 rc」。

| D 項 | 突變 | 對應 AT | 突變後 | 還原後 |
|---|---|---|---|---|
| D7 | M1 拿掉晉升式與 verdict 比對 | AT-216-1-E-1 | rc 1（`SUBFAILED[d]`、`[e]`、`[f]`） | rc 0 |
| D7 | M2 只拿掉 `TREE-CHANGED` 外層預檢 | AT-240-7-E-1 | **rc 0（存活）＝等價突變**：鎖內有同判準的重驗，外層只是較早回傳 | rc 0 |
| D7 | M2′ 外層加鎖內同拿掉 | AT-240-7-E-1 | rc 1（`SUBFAILED[e]`） | rc 0 |
| D7 | M3 `NON-EVOLVABLE-NOW` 恆放行 | AT-220-3-E-1 | rc 1（4 failed） | rc 0 |
| D7 | M4 拿掉晉升前提再驗 | AT-216-2-E-1 | rc 1（`a2`、`b2`、`c2`） | rc 0 |
| D7 | M5 拿掉 `ROLLBACK-NOT-EXACT` 比對 | AT-240-7-E-1 | rc 1（`SUBFAILED[f]`） | rc 0 |
| D8 | M1 不比 HMAC | AT-233-1-E-3 | rc 1 | rc 0 |
| D8 | M2 拿掉 `STALE-CARD` | AT-233-1-E-2 | rc 1（`SUBFAILED[f]`） | rc 0 |
| D8 | M3 改錯欄（只換 `seg` 的取法） | AT-235-2-1 | **rc 0（存活）＝等價突變**：`seg` 只用來取前後空白，回傳切片未變 | rc 0 |
| D8 | M3′ 改寫處置時吃掉第 7 欄 | AT-235-2-1 | rc 1 | rc 0 |
| D8 | M4 不擋欄位內 `\|` | AT-235-1-E-1 | rc 1（`SUBFAILED[a]`） | rc 0 |
| D8 | M5 回查不驗 HMAC | AT-233-2-E-1 | rc 1（`nokey`、`otherkey`） | rc 0 |
| D6 | M1 載具自證恆真 | AT-219-1-E-2 | rc 1 | rc 0 |
| D6 | M2 不判 `PATCHED-NOT-GREEN` | AT-219-2-1 | rc 1 | rc 0 |
| D10 | M1 平台守衛判準失效 | AT-240-5-E-1 | rc 1（`SUBFAILED[i]`、`[j]`） | rc 0 |
| D5 | M1 `touched_ok` 恆真 | AT-215-4-1 | rc 1（`SUBFAILED[stray]`） | rc 0 |
| **修復棒一 A** | CLI 端 `decide` 內 `preconditions` 短路、測試端 seam 不變 | AT-240-2-E-3 | rc 1（`7 failed`；`SUBFAILED[proposed-handoff/approve/rc=1]`、`[approved/reject/rc=1]`、`[verified-ne-noprobes/return/rc=1]`…） | rc 0（`1 passed, 133 subtests`） |
| **補充（Developer 未涵蓋的 D 項）** | | | | |
| D1 | `dec.flags` 元素不限 `unverified_ack` | AT-240-1-E-1 | rc 1（`SUBFAILED[dec flags x]`） | rc 0 |
| D1 | `dec(promote)` 不看 `rollback_ok`／`touched_ok`（寫入端與重放端同變） | AT-240-2-* | rc 1（`TestStateMachine …E_1 [c][d]`） | rc 0 |
| D2 | 不拒引用卡面 | AT-212-1-E-1 | rc 1（`GRAMMAR-CARD-QUOTED` 兩格） | rc 0 |
| D3 | 「未說明」不再是最嚴冷卻 | AT-213-2-E-1 | rc 1 | rc 0 |
| D4 | 凍結者可等於提案者 | AT-220-1-E-1 | rc 1 | rc 0 |
| D9 | ⓪ 成立而 `probes_n≠0` 不判 | AT-240-3-E-1 (d) | rc 1 | rc 0 |
| D9 | `obs.close` 指向仍 open 的列不判 | AT-240-3-E-1 (f) | rc 1 | rc 0 |
| D9 | verdict 重算不比 `reasons` 子集（R98 (c)(ii)） | AT-240-3-E-1 | **rc 0（存活）→ D-04** | rc 0 |
| D11 | 取鎖不把 `PermissionError` 當忙碌 | AT-240-8-1 | rc 1 | rc 0 |
| D11 | 釋放少重試一次 | AT-240-8-3 | rc 1 | rc 0 |
| D11（V6） | 以 HEAD 版（修復前）`apply_lock.py` 換入 | AT-240-8-1～E-4 七條 | 七條**各自 rc 1**（修前紅）；修後七條皆 rc 0 | 複本內檔案已還原（位元組相同 True） |
| D12 | 全形字元 host 不再被拒 | AT-230-2-E-1 | rc 1（5 failed） | rc 0 |
| D13 | `verify_runs_max` 不在 `PARAM_SPECS` | AT-240-4-E-1 | rc 1 | rc 0 |
| D15 | SOP `verify` 列改成「rc 0 表示通過」 | AT-240-13-1／E-1 | rc 1（2 failed） | rc 0 |
| D16 | 入口少 `rollback` 動詞 | AT-140-1-1 | rc 1 | rc 0 |
| **補充（AT 缺口實證）** | | | | |
| D6 | 逾時步驟的 `baseline_red` 記 `False`（TCS 要 `null`） | AT-217-1-E-2 | **rc 0（存活）→ D-03** | rc 0 |
| D6 | baseline 逾時後仍跑 patched 步 | AT-217-1-E-2 | rc 1（`SUBFAILED[a]`） | rc 0 |

D14（夾具）以 D1／D16 的紅字與 `AT-240-14-1`、`AT-240-1-1` 間接涵蓋；D14 沒有獨立的行為突變（夾具是測試資產）。三筆存活突變中兩筆為等價突變（D7-M2、D8-M3，Developer 已用 M2′／M3′ 補強並自述），一筆是真缺口（D9，記 D-04）。

### B-5 DEF-200-559（`tools/lib/apply_lock.py`）：PASS

- 三站點（R100）：`_try_acquire`（`apply_lock.py:72-84`，`:77` `except (FileExistsError, PermissionError)`，其他 `OSError` 立即穿出）；`_reap_if_stale`（`:87-98`，`:97` 的 `unlink` 吞 `FileNotFoundError`、`PermissionError`）；`_release`（`:101-116`，`RELEASE_RETRIES = 5`＠`:56`，初次加最多 5 次重試共 6 次嘗試、重試間 `poll_interval`、用盡後 stderr 警告不拋）；`acquire`（`:119-140`）逾時時 `PermissionError` 拋 `raise busy`（`:128`，原始例外），`FileExistsError` 仍 `LockBusyError` 加持鎖者資訊；公開面簽名不變。
- 其他 `OSError` 不被吞：`AT-240-8-E-1` (e)（取鎖拋 `OSError(5)` 立即穿出）、`AT-240-8-E-2` (b)（回收拋 `OSError(5)` 立即穿出）皆實測綠；釋放路徑只吞 `FileNotFoundError` 與 `PermissionError`。
- 唯一超出 R100 字面處：`_reap_if_stale` 的 `stat()`（`:91`）也吞 `PermissionError`（Windows 刪除待決時 `os.stat` 同樣回 `PermissionError`，成因同類）→ 列勘誤 E-20，不列缺陷。
- AT-240-8-1～E-4 七條全綠（SI 全測內）；修前版本使七條各自轉紅（B-4 V6 列）；`test_apply_lock.py` diff＝`308 insertions, 0 deletions`（既有測試未動）。**但該檔腳本入口位置錯誤，見 D-01（P2）。**

### B-6 目錄項原語債 37→43：FAIL（P3 → D-02）

TCS 原文（`grep` 單次嘗試｜不重試｜`os.replace`）：「單次嘗試不重試」**只**出現在 R97（TCS 第 189 行，`obs-close` 的原子改寫）與 AT-235-2-E-2（TCS 2292–2305）；**R84（第 166 行，manifest）與 R94（第 186 行，稽核檔與 HMAC）沒有此規定**。沙盒與 held-out 只有「先在暫名目錄組裝完成才換入」（R71 第 96 行、R83 (c)、R86）而無 OSError 契約。套件靜態禁字樣（R105 ④，`time.sleep`／`while True`）給了「不重試」的結構保證，但不是轉碼規定。`test_platform_neutral_paths.py:3701` 的註解把依據寫成「TCS R84／R94」，不實。

| # | 站點 | 呼叫端轉碼 |
|---|---|---|
| 1 | `obswrite.py:40` `_atomic_write` 的 `os.replace(tmp, path)`（目標是**repo 內** OBS 帳本，不是家目錄） | **有**：`obswrite.py:139-140`、`214-215` `except OSError → evwrite.Reject([("LEDGER-WRITE-FAILED", 類名)])` ⇒ rc 1、零殘留（AT-235-2-E-2 釘住）；`_orphan_guard.restore`（`:80-90`）的回退寫入由 `evwrite.py:115-121` 的 `except OSError: pass` 吞掉。碼 `LEDGER-WRITE-FAILED` 不在 TCS〈P2 拒收碼表〉（TCS 245–246）→ E-17 |
| 2 | `sandbox.py:269` `os.replace(final, backup)` | 無詞法處置；OSError 穿出 `build` → `writeverbs.py:105-106` `raise UsageError("事件追加失敗（…），帳本未變動")` ⇒ rc 3 泛用訊息（非規格碼）；此時舊沙盒未動 |
| 3 | `sandbox.py:270` `os.replace(tmp, final)` | 同上；**且 `state.cleanups.append(_undo)` 在 `:271`（兩次 replace 之後）**：第二次失敗時舊沙盒已被搬到 `.old-<PROP>-<pid>`、`<si>/sandbox/<PROP>` 不存在，沒有任何還原 ⇒ 違反 R71「呼叫前已存在則維持呼叫前的狀態」 |
| 4 | `sandbox.py:299` `_undo` 的 `os.replace(backup, final)` | 在 cleanup：被 `evwrite.py:117-120` 吞（盡力而為）；可接受 |
| 5 | `sandbox.py:367` `heldout_freeze.build` 的 `os.replace(tmp, final)` | 穿出 → `writeverbs.py:105-106` rc 3 泛用訊息；`finally` 刪暫名目錄（`sandbox.py:378-379`）零殘留 |
| 6 | `verify.py:143` `_tree_ok` 的 `os.replace(tmp, tree)` | **無**：`_tree_ok`（`verify.py:126-148`）只有 `try/finally`，`_measure`／`run` 無 `except OSError`，`tools/selfimproving.py:335-347` 的 `main` 只接 `SystemExit`／`check.InputError` ⇒ 未捕捉例外（Python traceback、rc 1，無規格碼、無 OBS 草稿列） |

結論：規定只支持 1／6、轉碼缺 1 處（#6）加 1 處半換入未還原（#3）⇒ 依主控裁決列 P3（不接受為規格化設計決策）。修法見 D-02。

### B-7 文件一致：PASS（附 P4 D-07）

- `tools/selfimproving.py --help` 列 21 個動詞（`check status scan card export run-open run-close attr attr-confirm attr-reject prop-new prop-revise decide heldout-freeze sandbox verify promote rollback obs-add obs-close research`）；SOP 兩張 rc 契約表（P1 十列、〈P2 動詞〉九列）共點名 21 個動詞（`qa_p2\sop_verbs.py`：help 有而 SOP 無＝空、SOP 有而 help 無＝空）。〈P2 動詞〉九列＝`decide`、`heldout-freeze`、`sandbox`、`verify`、`promote`、`rollback`、`card --issue`、`obs-add`、`obs-close`（TCS R108 (a)）；`verify` 列含「rc 0 不論 verdict」、`sandbox` 列含「rc 0 涵蓋 applied=false」、`VERIFY-RUNS-EXCEEDED` 須升級人工。
- 〈審查者〉五項（SOP 第 103–107 行，REQ-24～28）；第 105 行 `審查者不得自起背景長任務；…`（與 PRD AC-SI-18-1 第 348 行「不得自起背景長任務」一致）；`params.json` +2 鍵（600、2）。
- SOP／PRD「測試摘要字樣＋4 位數字」同行：SOP 0 筆；PRD 6 筆皆為埠號與行號（非測試摘要，且 PRD 未被改）。
- PRD digest `sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406` 重算相符；TCS digest `sha256:c261740974adb1d3839e87f05c558e79f4df119d5fae08de2896ae2148b5b8ca`（CRLF→LF 位元組重算＝原檔）相符。

### B-8 ⚖／勘誤建議審定：完成（§E，20 條）

PROGRESS 9 條、報告 §5 六條、修復棒一 B 條、加 PROGRESS 其他段落的 ⚖（R72⇔、`ls-files`、`verify1.json`、`evwrite` 探針名、`heldout_freeze` 搬遷、R91 順序、`stat` 吞 `PermissionError`）逐條審定：**語意皆與 PRD 一致，無一條需改 PRD**；全部走 TCS 〈勘誤〉。對照表：PROGRESS 9 條＝E-03、E-02、E-04、E-05、E-06、E-07、E-08、E-09、E-10（依序）；報告 §5 六條＝①CLI 16 格已由修復棒一 A 結案（無勘誤）、②E-01、③E-11、④E-15、⑤E-18、⑥「反測試鎖約束」是實作遷就現行根層鎖、非規格（不立勘誤）；修復棒一 B＝E-01；PROGRESS 其他段 ⚖＝E-12（R72⇔）、E-13（`ls-files`）、E-14（`verify1.json`）、E-16（`evwrite`）、E-19（`heldout_freeze` 搬遷）、E-11（R91／R92 順序）、E-20（`stat` 吞 `PermissionError`）。凡「實作偏離 TCS 而不該改 TCS」者已列缺陷：D-01（腳本入口）、D-02（轉碼缺席／半換入）、D-06（字面 ID）、D-08（rc 3 預檢順序）。

### B-9 修復棒一驗收：PASS

- **A**：`-k AT_240_2_E_3_` 恰收 1 個函式（`test_AT_240_2_E_3_decide_and_fold_agree`，B-1 錨定計數）；`CLI_SAMPLE`＝16 格（`test_selfimproving_events_p2.py:692-709`：8 個 dkind 各一格接受（rc 0）、一格拒絕（rc 1），`promote` 的前式接受、後式拒絕）；`cli_sample`（`:818-845`）對每格真跑 CLI `decide`（`fx2.decide_say`）、斷言 rc 與前提判定一致、rc 1 者 `set(seam) ⊆ codes_of(out)` 且 `decs(R) == before`（無新 `dec`）、rc 0 者恰多一筆 `(prop, dkind)`；結尾斷言 `len(CLI_SAMPLE)==16` 與每個 dkind 的 `{True, False}` 覆蓋；格點迴圈 13 態×9 形態另加 `allowed` 七碼斷言（`:795-812`，TCS Then 第三句，原先沒人斷言）。突變驗證見 B-4（CLI 端短路被抓，7 failed）。真跑 `1 passed … 133 subtests` 為 SI 全測的一部分。
- **B**：`test_selfimproving_p2_meta.py:166` 為 `("REQ-26", ["不得自起背景長任務"])`；SOP 第 105 行如上；整個 repo 只剩 TCS 三處（203、2787、3322）寫「不自起背景長任務」→ E-01。
- **C**：`export.py` 於 patch 讀不到時追加 `ne` 項 `{"field": "proposals.<id>.touched", "reason": "PATCH-UNREADABLE"｜"PATCH-INVALID"}`（unstaged diff＝`3 insertions, 1 deletion`）；`touched`／`touched_count` 仍為 `null`（契約不變）；新測試 `test_obs_si_261_export_names_the_unmeasurable_touched`（`test_selfimproving_events_p2.py:1155-1171`）三段（正常／壞 patch／缺 patch）斷言恰一項；`test_selfimproving_events_p2.py` 的 unstaged diff＝`98 insertions, 0 deletions`（＝報告的 A 78＋C 17＋allowed 3），**沒有任何既有 AT 被改**；`test_selfimproving_p2_meta.py` 為 `1/1`（B 的字面）；SI 全測 332 全綠故無 AT 因 C 轉紅。與凍結 AT 無衝突，OBS-SI-261 可依主控裁決結案。

### B-10 根層鎖：PASS（只讀 log）

`root_full_p2c.log`（檔時 2026-10-22 02:33:33，晚於修復棒一報告 02:25:27，故涵蓋 C 項新測試）：`✅ unittest 數量下限釘選通過：發現 5756 個測試（下限 5755）`、`ROOT rc=0`（第 115 行）；skip census `tools/tests@win32 共 46 支…欠債型 4 支（env-disabled，symlink 權限，與本鍵無關）`。重釘（R214 列、E501、guard-total）屬主控持有面，未審。

## §C 缺陷清單

### D-01 [P2] `test_apply_lock.py` 的腳本入口不在檔尾（NFR-P2-10 (14)、V4）

- 位置：`tools/tests/test_apply_lock.py:166-167`（`if __name__ == "__main__": unittest.main()`）；其後仍有 12 個頂層敘述（`:174-178` 的 `import`、`:226` `class TestWindowsDeletePending`、`:391` `class TestWriteVerbsAbsorbLockFix`…）。HEAD 版此守衛在檔末（167 行檔），Developer 把 308 行新測試**附加在守衛之後**。
- TCS 依據：NFR-P2-10 (14)（TCS 第 318 行）「測試檔的腳本入口必須在檔尾（… 為該檔最後一個頂層敘述；… 以腳本模式跑其任一 AT 的 `-k`，須收到至少 1 個測試）」；V4（第 3568 行）「腳本模式 `python tools/tests/<檔> -k <該檔任一 AT 的底線形>_` 收到至少 1 個測試、不是 `Ran 0 tests`」。
- 實證（本窗口）：`python tools/tests/test_apply_lock.py -k AT_240_8_1_` → `Ran 0 tests … OK` rc 0；`-k AT_240_8_E_4_` 同；`python tools/tests/test_apply_lock.py`（無 `-k`）→ `Ran 7 tests … OK`，而 `pytest --collect-only` 與 `unittest discover` 皆 14。其餘 13 個 SI 測試檔守衛皆在檔尾（`qa_p2\qa_main_last.py`），腳本模式抽跑 18／18 通過。
- 嚴重度理由：TCS 明文列為「缺一即不得交卷」的閘門與 V4 通過判準；後果是 D11 的 7 個 AT 在腳本模式被**靜默略過且仍印 OK**（Rule 12 fail loud 的反面）。pytest、discover、根層全套都不觸發 `__main__`，所以根層全套 rc 0 看不到它（無機械鎖）。
- 建議修法（消除成因）：把 `if __name__ == "__main__": unittest.main()` 移到 `test_apply_lock.py` 檔尾，使其成為最後一個頂層敘述；順手把 `:174-178` 的後置 `import` 併回檔頭匯入區（目前靠 `# noqa: E402`）。驗證三行：`python tools/tests/test_apply_lock.py -k AT_240_8_1_`＝`Ran 1 test`；`python tools/tests/test_apply_lock.py`＝`Ran 14 tests`；`python qa_p2\qa_main_last.py` 全 OK。框架層缺口（無機械鎖）建議另立根層靜態守門：AST 判 `tools/tests/test_*.py` 的 `__main__` 守衛須為最後一個頂層敘述（P4 建議，見 D-10）。

### D-02 [P3] 目錄項原語債 43 的依據不實；`verify.py:143` 無轉碼；`sandbox.py:269-270` 半換入失敗不還原

- 位置與原文：`tools/tests/test_platform_neutral_paths.py:3701`「# 37→43：SelfImproving P2 六處家目錄 os.replace（單次嘗試不重試，TCS R84／R94；錯誤由呼叫端轉碼）」；站點表見 B-6。
- TCS 依據：R84（TCS 166）、R94（TCS 186）無此規定；只有 R97（189）與 AT-235-2-E-2 涵蓋 `obswrite.py:40` 一處；R71（96）要求 `sandbox`／`heldout-freeze` 「若呼叫前已存在則維持呼叫前的狀態」。任務書裁決：規定不存在或轉碼缺席 ⇒ P3。
- 建議修法（優先，消除成因＝債不增）：六處的 `os.replace` 各自詞法內 `try/except OSError`（`_DIRENT_UNGUARDED_DEBT` 守衛看的是祖先 `ast.Try` 的 handler，見 `test_platform_neutral_paths.py:3727-3737`），債維持 37、撤掉 +6 與該註解：(1) `sandbox.py` 新增 `_swap_dir(src, dst)` 包 `os.replace`，失敗拋 `SandboxError("SANDBOX-SWAP-FAILED", 類名)`，`_commit.build` 轉成 `evwrite.Reject`（rc 1＋OBS 草稿）、`heldout_freeze.build` 同，`verify._tree_ok` 轉成 rc 1 `SANDBOX-TREE-DRIFT`（detail 帶類名）；(2) `sandbox.py:269-271` 把 `state.cleanups.append(lambda: _undo(final, backup))` 移到 `os.replace(final, backup)` 之後、`os.replace(tmp, final)` 之前（`_undo` 對 `final` 不存在已容忍）；(3) `obswrite._atomic_write` 自身加 `except OSError`（把 `LEDGER-WRITE-FAILED` 的轉碼就地）；(4) 新碼名列入〈勘誤〉E-17。**最小替代**（若主控堅持保留 43）：改正 `test_platform_neutral_paths.py:3701` 註解的出處（obswrite 一處依 R97；其餘五處改寫為有文件依據的設計決策並寫 WHY），並補 (2) 與 `verify.py:143` 的轉碼。

### D-03 [P3] `AT-217-1-E-2` 未釘住 TCS 的步驟欄位（突變存活）

- 位置：`tools/tests/test_selfimproving_verify.py:274-304`。TCS 第 1500-1501 行 Then：逾時步驟「(a) `baseline_red` 為 `null`、`steps.patched` 為空清單、`steps.mutated` 為 `null`；(b) …`patched_green` 為 `null`…；(c) …`mutated_red` 為 `null`」，並要求 PROP 態為 `verified`、stdout 末尾 `obs-draft:`＋恰一行草稿列。測試只斷言 verdict／reasons、逾時 `rec` 為 `(True, None)`、心跳不增長、沙盒樹還原。
- 實證：複本突變「逾時步驟的 `baseline_red` 記 `False`」`AT_217_1_E_2_` 仍 `1 passed, 3 subtests`（存活）；「baseline 逾時後仍跑 patched 步」則被抓到。
- 建議修法：在 `for label` 迴圈內讀 `verify1.json` 與事件，補三組 `(baseline_red, patched_green, mutated_red)`＝(a)`(None,None,None)`／(b)`(True,None,None)`／(c)`(True,True,None)`、`steps.patched==[]`／`steps.mutated is None`、`fold` 態 `verified`、`obs_draft` 含 `si verify` 與 `PROBE-TIMEOUT`。

### D-04 [P3] `AT-240-3-E-1` 子情形 (b) 未隔離 R98 (c)(ii)，且缺「合規對照」

- 位置：`tools/tests/test_selfimproving_events_p2.py:885-944`。TCS Given (b)：「`verdict` 為 `NE` 而 `reasons` 缺重算得出的碼」；測試 (b) 卻把 `reasons` 設成 `["MUTATION-ABSENT"]`（多出一個無法導出的碼），因此由 R98 (c)(iii) 抓到，(ii)「重算碼不是記錄碼子集」從未獨立被測。TCS And「每個子情形的合規對照（改正後）該項為 PASS」與 `_NONBLOCKING` 三碼，測試亦未斷言；(i) 的「含 `dec` 與 `helmsman` 免掃」只測了 helmsman 一半。
- 實證：複本突變 `decheck.py` 的 `if not set(want_r) <= set(rec):` → `if False:`，`AT_240_3_E_1_` 仍綠（存活）；其餘 D9 突變（⓪ 與 `obs.close`）被抓到。
- 建議修法：(b) 的 `reasons` 改為 `[]`（verdict `NE`、`baseline_red=False`，記錄缺 `BASELINE-NOT-RED`）；各 `broken(...)` 之後把同一情境改正並斷言該項 `PASS`；(i) 加一筆 `dec` 後斷言 `QUOTE-VERIFIER-NOT-ESTABLISHED` 不出現。

### D-05 [P3] Developer 交卷缺〈流程摩擦〉節（NFR-P2-10 (10)）

- 位置：`…\si_p2\dev_p2_report.md`、`dev_p2_fix1_report.md` 皆無「流程摩擦」字樣（grep 0 筆）；TCS 第 318 行 (10)、R108 (g)、V12。
- 建議修法：主控自 PROGRESS／報告補一節（候選項見 §H），於 SCG-4 收尾前入帳。

### D-06 [P3] 測試內字面 `PROP-SI-999` 不存在於真帳本（NFR-P2-10 (16)、V5）

- 位置：`tools/tests/test_selfimproving_verify.py:733`（`AT-220-4-1` 的「他 PROP 的 held-out 路徑」，`self.home / "heldout" / "PROP-SI-999"`）。25 個字面 ID 中僅此一個不在真 OBS／缺陷／事件帳本（`qa_p2\qa_literal_ids.py`）；同檔他處皆以 `"PROP-SI-" + "998"` 或 `f"…{n:03d}"` 組出以避開字面，可見此處是漏網。
- 建議修法：改成動態組出（例：`"PROP-SI-" + f"{int(p.rsplit('-', 1)[1]) + 900:03d}"`，同 `AT-215-1-E-2`）。

### D-07 [P4] SOP 第 65 行未同步 R110

- `docs/05_development/SelfImproving_Operations_SOP.md:65`「`--type link` 記復發連結，`--reopens` 須是已結列」；R110（TCS 205）已把目標擴為「已結列∪處置首詞為 `deferred` 的列」。TCS 未要求改 SOP，但連動面不同 commit 收齊（根 CLAUDE.md 共通紀律第 5 條）。建議改為「`--reopens` 須是已結列，或處置首詞為 `deferred` 的列（P2 R110）」。

### D-08 [P4] rc 3 預檢先於 `UNATTENDED-REFUSED`（R70「先於全部其他前置檢查」）

- `decwrite.py:201-203`（`_usage`、`params_for` 先於 `refuse_unattended`）；`sandbox.py:331-337`（`valid_by`、`is_dir`、`params_for` 先於 `refuse_unattended`）。無人值守下遇到壞旗標會得 rc 3 而非 rc 1，皆零寫入。`decide` 有 R80 (a)(b) 的明文順序支持；`heldout-freeze` 沒有。建議把 `refuse_unattended` 提到 `params_for`／`is_dir` 之前，或在 R70 補一句「用法錯誤（rc 3）先於無人值守拒收」（E-21 備選）。

### D-09 [P4] 弱斷言小項（未造成突變存活，僅記錄）

- `AT-240-13-E-1`（`test_selfimproving_p2_meta.py:256-286`）對「〈審查者〉整段移入圍欄」只斷言問題以 `REQ-2` 起頭（涵蓋 REQ-20～29），應收窄為 `REQ-24`～`REQ-28`。
- `AT-240-8-E-4` (c)（`test_apply_lock.py:427-475`）未斷言 detail 含持鎖者資訊（TCS 第 2560 行）。
- `AT-215-1-E-3` 未做 TCS 的「危害見證」記錄（只記錄、不當通過條件，故無影響）。
- `AT-217-1-E-2`、`AT-219-2-E-1` 未斷言 PROP 態與 `obs-draft:`（D-03 一併補）。

### D-10 [P4] 流程與框架缺口

- NFR-P2-8／TCS 第 74 行「實作者不碰鎖檔」：報告 §2 自述 Developer 改了 `test_adr_xplat001_c1c2_lock.py`、`skip_tag_policy.py`、`run_root_unittests.py`、`ONBOARDING.md`、`test_platform_neutral_paths.py` 與兩支 compat-ci workflow（皆主控收尾面）；主控後續全套 rc 0 已接受，僅記錄，不要求還原。
- `evwrite.py` 被改（探針檔名加執行緒識別）而 §5.7（TCS 3370）列為「不動，須動則登勘誤」，報告 §5 漏列（只在 PROGRESS）→ E-16。
- D-01 的框架層缺口：建議另立根層靜態守門（AST：`tools/tests/test_*.py` 的 `__main__` 守衛須為最後一個頂層敘述），使 NFR-P2-10 (14) 不再靠人記得。

## §D 重跑指令與 rc 表（`$env:PYTHONUTF8='1'`；rc 先存變數再印）

| # | 指令 | rc | 關鍵輸出 |
|---|---|---|---|
| 1 | `python qa_p2\digest.py <TCS> <PRD>`（CRLF→LF 位元組重算） | 0 | TCS `c261740974ad…b8ca`、PRD `1d26dbf8b349…8406` 皆相符 |
| 2 | `python …\si_p2\at_missing.py` | 0 | `137 ATs; 0 missing`（對照用） |
| 3 | `python qa_p2\qa_at_anchor.py` | 0 | 137 條錨定 `-k` 恰命中 1；0 bad |
| 4 | `python qa_p2\qa_k_literal.py`（137 次字面 `--collect-only -k`） | 0 | `not-exactly-one: 0`，62 s |
| 5 | `python -m pytest <13 個 test_selfimproving_*.py＋test_apply_lock.py> -q -n 4 --dist worksteal -p no:cacheprovider` | 0 | `332 passed, 1085 subtests passed in 273.74s (0:04:33)` |
| 6 | `python tools/selfimproving.py check --json`（×4，含 3 次計時） | 0 | `overall=PASS items=32`；2.5 s／次 |
| 7 | `python AutoClaude/tools/check_loc_budget.py --json` | 0 | `total=18633 cap=20438 total_violation=false` |
| 8 | `.venv\Scripts\ruff.exe check tools/lib/selfimproving tools/selfimproving.py tools/lib/apply_lock.py tools/tests/test_selfimproving_*.py tools/tests/_selfimproving_*.py` | 0 | `All checks passed!` |
| 9 | `git diff --check`／`git diff --cached --check` | 0／0 | 零輸出 |
| 10 | `python tools/sync_onboarding_baselines.py --check-snapshot` | 0 | `cigate-v030 passed 2250／scripts 425` |
| 11 | 讀 `…\si_p2\root_full_p2c.log` | 0（log 內 `ROOT rc=0`） | `發現 5756 個測試（下限 5755）` |
| 12 | `python qa_p2\qa_mut.py base／d7／d8／d8b／fix1a`；`qa_mut_extra.py`、`qa_mut_extra2.py`、`qa_mut_extra3.py`；`qa_prefix_applylock.py`（複本） | 0 | 見 B-4；輸出存 `qa_p2\mut_*_out.txt`、`prefix_applylock_out.txt` |
| 13 | `python qa_p2\cap_count.py` | 0 | 40 鍵 29／7／2／2；disk 40；`capability_problems=[]` |
| 14 | `python qa_p2\sop_verbs.py` | 0 | help 21 動詞；SOP 缺 0／多 0 |
| 15 | `python qa_p2\qa_script_mode.py`（20 次腳本模式）；`qa_main_last.py`；`python tools/tests/test_apply_lock.py` | 0 | **2 BAD**（`test_apply_lock.py` `Ran 0 tests`）；13／14 檔守衛在檔尾；腳本模式 `Ran 7 tests`（pytest／discover＝14）→ **D-01** |
| 16 | `python qa_p2\qa_literal_ids.py`；`doc_count_scan.py` | 0 | 25 個字面 ID 僅 `PROP-SI-999`（`test_selfimproving_verify.py:733`）不在真帳本；SOP 測試摘要同行 0 筆 |
| 17 | `python qa_p2\sync_sites.py`（P1 既有測試被改動的函式清單） | 0 | 供 E-03 |

## §E 〈勘誤〉建議表（供主控於 RELEASE_READY 後 `spec-refreeze` 登記；QA 不改 TCS）

體例沿 P1 TCS 勘誤節：**既有 AT 的 id 與判定碼名稱一字不改、一個 AT 也不刪**（下列各條皆為字面補強或釘清優先序；新增碼名 `LEDGER-WRITE-FAILED`、`SANDBOX-SWAP-FAILED`〔僅 D-02 採建議修法時〕為純新增）。語意與 PRD 一致性欄：「一致」＝實作語意與 PRD v0.10 不衝突，PRD 不必動。

| # | 事由（來源） | 被改的 R／AT（TCS 行） | 原字面 → 新字面 | PRD |
|---|---|---|---|---|
| E-01 | REQ-26 字面（修復棒一 B、報告 §5） | R108 (d)（203）、AT-218-1-1 Then（2787）、§5.6 REQ-24～28 列（3322） | 「不自起背景長任務」→「不得自起背景長任務」（三處）；第 263 行已是「不得」 | 一致（AC-SI-18-1：「不得自起背景長任務」） |
| E-02 | `dec promote` 式與 verdict（PROGRESS 勘誤 2） | R75 表 `dec` `promote` 列（129） | 「`verdict` 為 `PASS`，或 `verdict` 為 `NE` 且 `flags` 含 `unverified_ack`」→「(`verdict` 為 `PASS` 且 `flags` 不含 `unverified_ack`)，或 (`verdict` 為 `NE` 且 `flags` 含 `unverified_ack`)；式與 verdict 不符者非法，與 R80 (e) `PROMOTE-FORM-MISMATCH`、R91 同判準」 | 一致（PRD §7.2 晉升列：「式與 verdict 不符＝拒絕」） |
| E-03 | R107 (c) 同步站點不完整（PROGRESS 勘誤 1；`sync_sites.py` 實測） | R107 (c)（202） | 於站點清單補：`test_selfimproving_events.py` 的 `TestCheckReplay.test_AT_108_4_1_transitions_replay`、`test_AT_108_4_E_2_structure_floor_and_dec_note`、`TestValueDomains.test_AT_108_4_E_5_quote_verifier_warn_boundary`、`TestInterface.test_AT_140_1_1_thirteen_verbs`（更名 `…twenty_one_verbs`，`-k AT_140_1_1` 與 AT-240-14-1 底線形子字串判準不受影響）、`WEIRD_STATUS_KEYS`、`TestProposalNumberingAndLock.test_AT_141_2_E_3_home_exists_but_is_not_writable`、`corrupt_cases`（K01～K03 的 `dec` 基底改 `promote`，R72 `flags` 只准 promote；K18 `card` 缺 `prop`＝`EVENT-KEY-MISSING`）、`CorruptLedgerTestCase.case_repo`、`TestDecFlagsAndConsumedKeys.test_AT_108_4_E_6…`、`…E_7…`；`test_selfimproving_props.py::TestBodyAndDelta.test_AT_110_1_1_budget_and_duplicates`（`unblock`＋`reject_response`）；`test_selfimproving_research_scan.py::TestResearchEvents.test_AT_130_1_E_1_skip_reasons_and_rejections`、`TestScan.test_AT_131_2_1_candidate_rows`、`test_AT_131_3_1_zero_candidates`；`test_selfimproving_export_status.py` 的 `test_AT_103_1_1_status_summary`、`test_AT_132_5_1_five_kinds`、`test_AT_132_5_E_2_differential_and_isolation`；並註明清單中 `test_AT_003_1_1_no_resident_mechanism`、`test_AT_030_1_E_1_usage_errors` 實測無須改動 | 無關 |
| E-04 | `decide` 的 `digest8`（PROGRESS 勘誤 3） | R69（94） | 「`digest8`（`resume` 無此欄）」→「`digest8`（取該 PROP **當下** digest 的前 8 碼；`rollback`、`unblock` 的 `dec` 事件無 `digest` 欄仍印；`resume` 無此欄）」 | 無關 |
| E-05 | `CARD-CHANGED` 判準（PROGRESS 勘誤 4） | R80 (f)（159） | 「`CARD-CHANGED`（最近一筆 `card` 的 `card_sha256` 不等於當下重算的卡面雜湊）」→「`CARD-CHANGED`（最近一筆 `card` 的 `card_sha256` 不等於以該 `card` 事件之前的前綴重建的卡面雜湊，或卡面核心區〔`--- 以下不計入核心區 ---` 之前各行〕與當下重算者不同；核心區之外的尾段〔冷卻狀態等〕不納入，AT-212-1-E-3 (k)）」 | 一致（AC-SI-12-4 ③ 只要求核心區送達） |
| E-06 | `核准 PROP-SI-*` 落碼（PROGRESS 勘誤 5） | R78 (c)（157）、AT-212-3-E-1（706-719） | 於 R78 (c) 補「首詞含 `*` 的整批用語（例：`核准 PROP-SI-*`）不是決定行，落 `GRAMMAR-NO-DECISION`，不落 `GRAMMAR-ID-FORMAT`」；AT-212-3-E-1 的期望碼不變 | 一致（AC-SI-12-3 沒有「全部核准」） |
| E-07 | `verify_runs_max` 無效時的 NE 位置（PROGRESS 勘誤 6） | R74 (e)（116）、R98 (c)（190）、AT-240-4-E-1（1013-1026） | R74 (e)「鍵無效則該判準不判並印 `SOURCE-UNAVAILABLE` 的 NE」→「…（於 `events.transitions` 與 `events.verdict` 兩項皆印）」 | 無關 |
| E-08 | `_NONBLOCKING` 碼數（PROGRESS 勘誤 7） | R98 首段（190）與〈判定碼表〉（216） | 「`_NONBLOCKING` 增三碼：`CONSOLE-AUDIT-MISSING`、`CONSOLE-KEY-MISSING`、`TRANSCRIPT-UNAVAILABLE`」→「增五碼：…加 `ORIGIN-MISSING`、`ATTACHMENT-TIME-UNKNOWN`」；AT-240-3-E-1 末段「三碼」同改「五碼」 | 無關 |
| E-09 | AT-213-3-E-1 的 rc（PROGRESS 勘誤 8） | AT-213-3-E-1 Then（1081-1094） | 「該項狀態仍為 `PASS`、rc 為 `0`（warn 不影響 rc）」→「該項狀態仍為 `PASS`（warn 不影響該項狀態）；手寫 `prop` 事件無 `rN.patch`／`rN.md` 時 `events.prop_files` 另紅，`check` 的 rc 不在本 AT 斷言內」 | 無關 |
| E-10 | AT-213-2-E-1 (d) 的 sources（PROGRESS 勘誤 9） | AT-213-2-E-1 Given (d)（1047-1060） | 「(d) 新證據是缺陷帳本新立的 DEF 列（證據不相交、根因無）」→「(d) 新提案的 `sources` 為（與 `A` 同證據的 OBS 列、缺陷帳本新立的 DEF 列）；同型由該 OBS 列的證據座標成立，DEF 列不相交、無根因而不構成 (b-2)」 | 一致（R82 (d) 只認 OBS 列） |
| E-11 | 判定碼優先序：純帳本類先於引言回查（報告 §5、PROGRESS 第四段） | R91（180）、R86（168）、R92（181） | R91：把「`DEC-VERIFY-FAILED`、`TRANSCRIPT-UNAVAILABLE`、`CONSOLE-AUDIT-MISSING`、`CONSOLE-KEY-MISSING`（…回查）」整段移到 `NON-EVOLVABLE-NOW` 之後、`MEMORY-DIR-MISSING` 之前（順序＝`PROMOTE-FORM-MISMATCH`→`DIGEST-MISMATCH`→`PROMOTE-PREMISE-*`→`NON-EVOLVABLE-NOW`→DEC 回查→`MEMORY-DIR-MISSING`→`PREIMAGE-MISMATCH`／`APPLY-FAILED`）並註明理由「卡面重建依賴同一份事件前綴，AT-216-1-E-1 (g)、AT-216-2-E-1 (a2)」；R86：`HELDOUT-NOT-FROZEN`→`MEMORY-DIR-MISSING`→`DIGEST-MISMATCH`（階段二收集）→其後才回查；R92：`MEMORY-DIR-MISSING` 置於 `TREE-CHANGED` 之前 | 一致 |
| E-12 | `probes_n`⇔`verify_sha256` 與 AT-219-2-E-1（PROGRESS 第六段 ⚖1） | AT-219-2-E-1 最後一個 And（1595-1609） | 「把 `probes_n` 改為 `2`」→「把 `probes_n` 改為 `2` 並同時把 `verify_sha256` 改為合法 `sha256:` 值（R72：`probes_n` 為 0 ⇔ `verify_sha256` 為 `null`，只改 `probes_n` 的事件於 `events.structure` 即被排除，R98 (c)(iv) 不可達）」 | 無關 |
| E-13 | git 子命令允許集合（PROGRESS 第六段 ⚖2） | AT-215-2-1 Given（1363-1376）、R105 禁用集合說明 | 允許集合「`apply`、`archive`、`status`、`rev-parse`、`log`、`show`、`grep`、`merge-base`」→ 加 `ls-files`（`lib.sdd_latest` 經 `sdd_version.py` 發出，唯讀） | 一致（鐵律五不涉 `ls-files`） |
| E-14 | `verify1.json` 與 surface 不變（PROGRESS 第六段 ⚖3） | AT-215-2-1 第一個 And（1363-1376） | 「沙盒與驗證兩個動詞呼叫前後 `surface(R)` 不變」→「…不變（`verify` 於 `SelfImproving_Proposals/<PROP>/verify<K>.json` 落地一個新檔屬 R90 (a) 的預期產物，不在比對內）」 | 無關 |
| E-15 | `obs.console_audit` 於事件帳本缺席時（報告 §5） | R98 首段（190） | 「載體缺席（事件帳本或 OBS 帳本不存在）一律 nonblocking NE」→ 補「`obs.console_audit` 例外：OBS 帳本存在而事件帳本缺席時仍評估帶 `carrier=console` 標記的列（無對應 `obs.add`＝FAIL `CONSOLE-EVENT-MISSING`，孤列不得被 NE 遮住）」 | 一致（AC-SI-35-1） |
| E-16 | `evwrite.ensure_home` 探針檔名（PROGRESS 第五段）；報告 §5 漏列 | §5.7（3370）、R107 (c)（202） | §5.7「`evwrite.py` … 不動」→「`evwrite.py` 只改 `ensure_home` 的探針檔名（加 `threading.get_ident()`，AT-235-1-E-2 (c) 同行程執行緒競態）」；R107 (c) 補 `test_AT_141_2_E_3_home_exists_but_is_not_writable` 的探針名同步 | 無關 |
| E-17 | `LEDGER-WRITE-FAILED`（D-02 #1） | R97（189）、〈P2 拒收碼表〉`obs-add`／`obs-close` 列（245-246） | R97「寫 tmp 或 `os.replace` 失敗＝rc 1」→「…＝rc 1、碼 `LEDGER-WRITE-FAILED`」；兩列加該碼 | 無關 |
| E-18 | 驗證 `app.verify` 態不符只回單碼（報告 §5） | R88（170） | 「前置（rc 1，碼）：`STATE-NOT-VERIFIABLE`…」→ 補「態不符時只回 `STATE-NOT-VERIFIABLE`（其後各碼對該態無意義，不收集）」 | 無關 |
| E-19 | `heldout_freeze` 住 `sandbox.py`（LOC 守衛；PROGRESS 第五、七段） | D4 列（55）、R83 (c)（165）、§5.7（3364） | 「`decwrite.py`」→「`sandbox.py`（`rw`；`decwrite.py` 因 LOC 上限不再含 `heldout_freeze`）」；R83 (c) 「`heldout.py` ro、`decwrite.py` rw」→「`heldout.py` ro、`sandbox.py` rw」。能力類別與 40 鍵計數不變 | 無關 |
| E-20 | `_reap_if_stale` 的 `stat()` 也吞 `PermissionError` | R100 (2)（195） | 「`_reap_if_stale` 的 `unlink` 遇 `PermissionError`＝『這輪沒收成』」→「`_reap_if_stale` 的 `stat()` 與 `unlink` 遇 `PermissionError`＝『這輪沒收成』（Windows 刪除待決時 `os.stat` 同樣回 `PermissionError`）」；其他 `OSError` 仍立即穿出 | 無關 |
| E-21（備選） | rc 3 預檢與無人值守的順序（D-08） | R70（95） | 若主控不採 D-08 的程式修法：補「用法錯誤（rc 3）先於 `UNATTENDED-REFUSED`」 | 無關 |

**逐條審定摘要**：E-02、E-05、E-06、E-10、E-15 為「實作採較嚴或較明確的語意」，皆與 PRD 一致；E-03、E-04、E-07～E-09、E-11～E-14、E-16～E-20 為 TCS 內部字面互相衝突或漏列的訂正；E-01 為 TCS 與 PRD 的字面差（以 PRD 為準）；**沒有任何一條需要改 PRD**。

## §F 未驗項（需主控真實樹或他平台執行；QA 結構上不得構造）

- V8、V15、V9：真實運轉（PROP-SI-004 的 M 類與 D 類確定性探針、掌舵者真人打字、`origin.kind=human` 的真逐字稿座標回取、暴露窗口現查、`COOLDOWN` 於真實否決後的拒收）——未驗。
- 真實 Claude Code 逐字稿格式：`user`／`attachment(queued_command)` 的 `origin.kind`、`attachment.timestamp` 是「觀察所得、非官方契約」（R77），本審查只用合成逐字稿；真機行為由 V8 驗。
- V7：根層全套連跑三次與 `apply_lock` 真機壓力——主控；本窗口只讀 `root_full_p2c.log` 一份（rc 0）。
- V10：真 repo 上 `obs-add --dry-run --body-file <§5.5 V3>` 與 tmp 複本的 `decide --carrier console`／`obs-add`／`obs-close` 煙霧——未另跑（對應 AT 與突變已涵蓋）；`export`／`status` 的真 repo 輸出鍵未現查。
- V13：macOS／Linux 未驗（`runner.py` 的 `os.killpg` 分支、`tarfile.data_filter` 缺席的直譯器、POSIX 路徑長度不判皆只靠替身或讀碼）。
- V14：`SddToPlaybookAdapter._parse_contracts`／`_unmapped_at_ids` 對本檔的計數未跑（本窗口以自建解析＋R102 錨定計數替代：137／0 bad）。
- V6 的缺陷帳本列（DEF-200-559 為 `fixed@<sha>`）與 V1 的「Developer 棒起點..HEAD」diff：工作樹未 commit，無 `HEAD` 差；改以 `git status`／`numstat` 比對範圍（§G）。
- AgentConsole 側（Bridge `/si/*`、backend、frontend）對 `export` 新 `ne` 項（C）與 `console_pending`／`buckets[]` 的消費；HMAC 向量的 Java 側逐字一致（P2b）。
- 根層棘輪重釘（R214 列、E501、guard-total）：主控持有面，未審。

## §G 審查前後 `git status --short` 相同的證據

- 審查前：`qa_p2\git_status_before.txt`（63 行）；審查後：`qa_p2\git_status_after.txt`（63 行）。`Compare-Object` 差異 0；兩檔 SHA256 同為 `4545B10CBFABD0BF2CDC2D7A3DDD8943E2362D27DEB4EAC9B72CCEA2C9400969`。
- 另以 `git diff --numstat`（unstaged 19 檔、staged 40 檔）審查前後逐列相同（例：`test_apply_lock.py 308/0`、`apply_lock.py 46/14`、`test_selfimproving_events_p2.py 98/0`、`export.py 3/1`），`git diff --stat` 尾行 `26 files changed, 1247 insertions(+), 145 deletions(-)`（unstaged）、`40 files changed, 10654 insertions(+), 119 deletions(-)`（staged）。
- 所有突變、複本、探針皆在 `qa_p2\repo_copy1\`；未做任何 git 寫入、未派子代理、未連網、未起背景任務。

## §H 〈流程摩擦〉（QA 棒交卷；SCG-4 收尾前由主控入帳；一句症狀加一個座標）

1. Developer 交卷缺 NFR-P2-10 (10) 要求的〈流程摩擦〉節 — `…\si_p2\dev_p2_report.md`（全檔）。
2. `test_apply_lock.py` 把新測試附加在 `unittest.main()` 之後，腳本模式只跑 7／14 且仍印 OK — `tools/tests/test_apply_lock.py:166`。
3. Developer 的 `at_missing.py` 以 `def test_<AT 底線形>` 子字串比對，會被前綴相同的兄弟 AT 遮住缺口；錨定計數才是 R102 判準 — `…\si_p2\at_missing.py:13`。
4. `mut.py` 直接改寫真實樹（`finally` 還原），在唯讀審查下不可用；複本需補拷夾具從 ROOT 取的 `sdd_version.py` — `…\si_p2\mut.py:9`、`tools/tests/_selfimproving_fixtures.py:480`。
5. TCS 的 NFR-P2-10 (14) 沒有對應的機械鎖，根層全套 rc 0 仍漏 D-01 — TCS 第 318 行。

## §L 主控處置（逐段追加；本節數字為主控本窗口親跑）

1. **審前**：Developer（headless hooks-ON，兩段）交卷後主控親驗（`selfimproving check` overall=PASS rc=0、`check_loc_budget --json` rc=0、`git diff --check` rc=0），發現交卷自報與實測不符（ruff 4 筆、E501 +2 行；OBS-SI-263），由主控就地改行；另派**修復棒一**（Sonnet）補 AT-240-2-E-3 的 CLI 16 格抽樣、REQ-26 字面對齊 PRD、OBS-SI-261 的 export `ne` 項，再送一審。
2. **一審 FAIL（D-01 P2）→ 修復棒二**（Sonnet）：D-01 守衛移檔尾；D-02 採「消除成因」——六處 `os.replace` 收斂為三個站點、各自詞法內 `except OSError` 轉碼（`SANDBOX-SWAP-FAILED`／`LEDGER-WRITE-FAILED`）、半換入還原登記提前，目錄項原語債 43→37；D-03／D-04／D-06／D-09 補斷言；D-07 SOP 同步 R110；D-08 `heldout-freeze` 先拒收；D-10 新機械鎖 `TestMainGuardIsTheLastTopLevelStatement`（首跑另抓到 `test_smoke_ci_sync.py`、`test_schedule_capability_parity.py` 兩支既有違反檔，已一併移檔尾）；追加 `verify --json` 拒收 JSON 化（`test_d11_*`）。
3. **二審 PASS**（§M）；殘留 P4 處置：R-05 由主控就地把 AT-240-3-E-1 的 `_NONBLOCKING` 斷言擴為五碼（E-08）；R-04 本檔落檔即解；R-03 於 §N 謄寫時修正座標；R-01／R-02／R-06 登 `SelfImproving_Observation_Ledger.md`（OBS-SI-269～271）。
4. **護欄層記帳（收尾單人窗口）**：`test_adr_xplat001_c1c2_lock.py` R214 第四～六列（136807→137312；第四列 +24 主控行修與名冊、第五列 +110 修復棒一、第六列 +371 修復棒二與追加項），一次性例外名冊 R214 列精確主軌淨額 8800（名冊上限 5→6 可見上修，主控依凍結常態規則裁定）；`guard_bucket_policy.py` 的 `guard_self` 3149→3197 帶 WHY（同 DEF-200-476 圍籬鎖判例：守測試衛生＝只能是 guard_self）；E501 存量回到天花板 136（三行真成因改行，不調天花板）；兩站點 `guard-total:R214` 同步。最終 `--print-guard-lines`：淨額 137312→137312（+0）、逐檔漂移 0 支。
5. **主控親驗（gate 依據）**：根層全套 `tools/run_root_unittests.py` rc=0、發現 5767 個測試（下限 5755）；`test_adr_xplat001_c1c2_lock.py` 單檔 `Ran 187 tests … OK`；ruff 改動檔 rc=0；`git diff --check` rc=0；`selfimproving check` rc=0。
6. **勘誤一**：TCS 尾端登記 E-01～E-27（QA §E 的 E-01～E-21、修復棒二 §6 的 E-22～E-26、追加 E-27）；凍結本文位元組未動（二審 §B-9 比對），RELEASE_READY 後 `spec-refreeze` 重記 digest（見 §L-7）。
7. **gate 走向**：`transition PR_REVIEW` → `gate PR_REVIEW PASS` → `gate RTM_VERIFY PASS` → RELEASE_READY → `spec-refreeze --doc TCS`（新 digest：`sha256:8ae8269a0adaa3eb8bfe1ec5cf87730da504738405e64a50a8da8f9f4fca8cc4`，supersedes 2026-10-21T11:04:13+00:00）→ `transition RELEASE`（鍵已 RELEASE）；approver 字串＝凍結常態規則（掌舵者 2026-10-20，sid d6dfce97 line 13；主控執行）。commit：本檔所在的實作 commit（實作＋測試＋守衛重釘＋本檔＋勘誤一）、其後的帳本 commit（DEF-200-559 翻 fixed、OBS-SI-261／266 結案、OBS-SI-263～265／267～271 新列）。
8. **未驗項（承接 V 系列；不阻擋 RELEASE，RELEASE 後另排）**：V7 根層全套連跑三次與 `apply_lock` 真機壓力；V8／V9／V15 真實運轉（掌舵者真人打字核准、`origin.kind=human` 真逐字稿座標、D 類探針晉升）；V10 真 repo `obs-add --dry-run` 煙霧；V13 macOS／Linux；V14 `SddToPlaybookAdapter` 對本檔計數；AgentConsole 側對 export 新 `ne` 項與 `console_pending`／`buckets[]` 的消費（P2b）。

## §M 二審（QA 同一代理續審；文字交卷由主控謄寫；數字皆 [他包回報]）


> 範圍：一審 FAIL 後修復棒二對 D-01～D-10 的修復，加追加的 `verify --json` 拒收 JSON 化；並對照主控寫入 TCS 尾端的〈勘誤一〉27 條。
> 全部數字為本窗口 2026-10-22 真跑所得；fix2 報告與主控親驗一律當 `[他包回報]`，已重跑或重算。突變與複本全在 `…\si_p2\qa_p2\repo_copy2\`（真實樹一檔未動，見 §E）。
> 一審判決：`…\si_p2\qa_p2_scg4_verdict.md`（P1／P2／P3／P4＝0／1／5／4）。

### §A 總判決

**PASS**。D-01～D-10 與追加項全部 PASS；無新 P1／P2；殘留 P3＝0、P4＝6（§C，皆不阻擋 RELEASE_READY，可由主控裁量併入收尾或登帳）。

| 項 | 判定 | 關鍵證據 |
|---|---|---|
| D-01 [P2] | PASS | 三行驗證 `Ran 1 test`／`Ran 14 tests`／`14 passed`；14 支 SI 檔守衛皆在檔尾 |
| D-02 [P3] | PASS | 六處 `os.replace` 收斂為 3 個詞法內 `except OSError` 站點；`-k DirEntry` `Ran 7 tests OK`、債 37；`test_platform_neutral_paths.py` 與 HEAD 位元組相同；4 筆突變皆紅 |
| D-03 [P3] | PASS | 逐格釘住 `(baseline_red, patched_green, mutated_red)`、步驟筆數、PROP 態、草稿列；一審存活突變現已轉紅 |
| D-04 [P3] | PASS | (b) 偏離字面但**仍只隔離 R98 (c)(ii)**；一審存活突變現已轉紅（恰紅在 `SUBFAILED[b]`）；各子情形補合規對照 |
| D-05 [P3] | PASS（附 P4 R-03） | fix2 §5 共 12 條、涵蓋整個 P2、每條一句症狀加座標 |
| D-06 [P3] | PASS | 24 個字面 ID 皆在真帳本；`PROP-SI-999` 已動態組出 |
| D-07 [P4] | PASS | SOP 第 65 行字面同步 R110；行數 268 不變 |
| D-08 [P4] | PASS（附 P4 R-06） | `heldout-freeze` 的 `refuse_unattended` 提到最前；`decide` 未動；回歸鎖綠且順序突變紅 |
| D-09 [P4] | PASS | `AT-240-13-E-1` 收窄為恰 `REQ-24`～`REQ-28`；`AT-240-8-E-4` (c) 釘持鎖者資訊；`AT-219-2-E-1` 釘態與草稿列 |
| D-10 [P4] | PASS | `TestMainGuardIsTheLastTopLevelStatement` 四測綠；守衛搬回中段即紅；兩支既有違反檔已移到檔尾 |
| 追加項 | PASS | `test_d11_verify_json_rejection_is_json` 綠；`as_json` 寫回 `False` 即紅 |
| 〈勘誤一〉對照 | PASS（附 P4 R-04、R-05） | 27 條齊全、字面對得上、未動既有 AT id／判定碼、未刪 AT |
| 閘門與根層鎖 | PASS | SI 全測 `339 passed, 1090 subtests`；`root_full_p2d.log`：發現 5767 個測試、`ROOT rc=0` |

### §B 逐項

### B-1 D-01：PASS

- `python tools/tests/test_apply_lock.py -k AT_240_8_1_` ⇒ rc 0、`Ran 1 test … OK`；`python tools/tests/test_apply_lock.py` ⇒ rc 0、`Ran 14 tests … OK`；`python -m pytest tools/tests/test_apply_lock.py -q -p no:xdist -o addopts=` ⇒ rc 0、`14 passed in 6.41s`（一審實測：`Ran 0 tests`／`Ran 7 tests`）。
- `qa_p2\qa_main_last.py` 重跑：14 支 SI 測試檔（13 支 `test_selfimproving_*.py`＋`test_apply_lock.py`）的 `if __name__ == "__main__":` 後皆 0 個頂層敘述（`test_apply_lock.py` 守衛現於第 474 行＝檔尾）。
- 突變（複本，`qa_mut2.py d08d10d11`）：把 `test_apply_lock.py` 守衛搬回中段 ⇒ 腳本模式 `-k AT_240_8_1_` 回到 `Ran 0 tests … OK`（即原缺陷），且 D-10 的鎖紅：`test_apply_lock.py:221 腳本入口之後還有 2 個頂層敘述（首個在第 225 行）`；還原後綠、位元組相同。

### B-2 D-02：PASS

- **讀碼**：
  - `sandbox.py:172-178` `swap_dir`：`os.replace` 在詞法內 `try/except OSError` ⇒ `SandboxError("SANDBOX-SWAP-FAILED", 例外類名)`，單次嘗試；三個站點的普查（`qa_p2\qa_census.py`，匯入真測試模組的 `dirent_primitive_sites`）：`sandbox.py:176`（swap_dir）、`sandbox.py:313`（`_undo`，就地 `except OSError`）、`obswrite.py:43`（`_atomic_write`）皆「已處置」，`verify.py` 0 站點（改走 `swap_dir`）；SI 套件未處置站點 0。
  - `sandbox.py:266-288` `_commit.build`：兩次換入包在同一個 `try/except SandboxError → evwrite.Reject`；`state.cleanups.append(_undo)`（`:281`）**在第一次換入之後、第二次之前**；`_undo`（`:308-315`）先丟新樹、再把 `.old-*` 搬回，失敗盡力而為。
  - `sandbox.py:375-389` `heldout_freeze.build`：換入轉 `Reject`、成功後才登記 `rmtree` 還原；`finally` 刪暫名目錄（`:395-398`）。
  - `verify.py:126-154` `_tree_problems`（原 `_tree_ok`）：換入失敗回 `[("SANDBOX-SWAP-FAILED", 類名)]`（不借 `SANDBOX-TREE-DRIFT`），`_measure`（`:198-200`）以 `wv.reject(repo, "verify", bad, as_json)` 輸出。
  - `obswrite.py:33-47` `_atomic_write`：外層 `except OSError → evwrite.Reject([("LEDGER-WRITE-FAILED", 類名)])`（含 fsync、tmp 清理）；`_orphan_guard.restore`（`:85-97`）內補 `except evwrite.Reject: pass`。
- **債**：`python -m unittest discover -s tools/tests -p test_platform_neutral_paths.py -k DirEntry` ⇒ rc 0、`Ran 7 tests … OK`（census 37）；`_DIRENT_UNGUARDED_DEBT = {'live': 37}`；該檔 sha256 與 `git show HEAD:` 相同（`fbc429f6…4ed2`），`git status` 不列它。
- **突變（複本 `repo_copy2`；每筆皆「突變後 rc 1、還原後 rc 0、位元組還原」）**：
  - D02-a 登記退回第二次換入之後（＝一審原缺陷）⇒ `SUBFAILED[second] … test_d02_sandbox_swap_failure_restores_the_old_box` 紅。
  - D02-b `_tree_problems` 拿掉 handler ⇒ `test_d02_verify_swap_failure_is_a_coded_reject_without_traceback` 紅。
  - D02-c `_atomic_write` 拿掉 `OSError` 轉碼 ⇒ `test_d02_obs_add_write_failure_is_a_coded_reject` 紅。
  - D02-d `heldout_freeze.build` 拿掉換入 handler ⇒ `test_d02_heldout_freeze_swap_failure_leaves_no_residue` 紅。
  - 記憶體內突變（`qa_census.py`）：`swap_dir` 不包 try ⇒ 未處置站點 +1（census 38≠37，債鎖會紅）；`_atomic_write` handler 改別的例外 ⇒ 未處置 +1。
- 新測試（`test_selfimproving_sandbox.py:689-808`）斷言：三格（第二次換入失敗／第一次失敗／無舊沙盒）rc 1、碼 `SANDBOX-SWAP-FAILED`、單次嘗試、舊沙盒位元組相同、無 `.old-*`／`.tmp-*`、事件帳本與正式面不變、鎖已釋放、草稿列合規；`verify` 無 `Traceback`、無 verify 檔；`obs-add` 帳本位元組不變、無 `.tmp`。

### B-3 D-03／D-04／D-06／D-09：PASS

- **D-03**（`test_selfimproving_verify.py:283-338`）：每格斷言 JSON 與 `app.verify` 事件的 `(baseline_red, patched_green, mutated_red)`＝(a)`(None,None,None)`／(b)`(True,None,None)`／(c)`(True,True,None)`、`verify_sha256` 非 null、`steps.patched` 筆數 0／1／1、`steps.mutated` None／None／1 筆、PROP 態 `verified`、`obs_draft` 恰一列含 `si verify` 與 `PROBE-TIMEOUT`，(a) 另測文字形態 `obs-draft:`＋一行——逐字對上 TCS 第 1500-1501 行。**一審存活突變**（逾時步驟 `baseline_red` 記 `False`）複本重做 ⇒ `SUBFAILED[a]` 紅，還原綠。
- **D-04**（`test_selfimproving_events_p2.py:885-983`）：(b) 偏離任務書字面（`reasons` 非空）——事由成立：R72「空陣列⇔PASS」使 `reasons=[]` 的事件在 `events.structure` 即被排除、到不了 verdict 重算（`events.py:376`）。改用「⓪ 層 `touched_ok`、`rollback_ok` 皆假（重算 NE、`[TOUCHED-SUPERSET, ROLLBACK-DRYRUN-FAILED]`），記錄 NE 而 `reasons` 只留 `["TOUCHED-SUPERSET"]`」：verdict 同為 NE ⇒ (i) 不觸發；記錄碼皆可導出 ⇒ (iii) 不觸發；`probes_n`／`verify_sha256` 取預設空值 ⇒ (iv) 不觸發；只剩 (ii)。**實證**：複本把 `decheck.py` 的 `if not set(want_r) <= set(rec):` 改 `if False:` ⇒ 紅且**恰紅在 `SUBFAILED[b]`**（一審同突變存活），還原綠。另補：每個 `broken(...)` 的合規對照（改正後該項 PASS）、(e)(f) 走真實 CLI 入帳後 PASS、(g)(i) 帳本含 `prop／card／dec` 且所有項目無 `QUOTE-VERIFIER-NOT-ESTABLISHED`、`_NONBLOCKING` 超集斷言。
- **D-06**：`qa_literal_ids.py` ⇒ `distinct literal IDs: 24 not in real ledgers: 0`（一審 25／1）；`PROP-SI-999` 已改為 `"PROP-SI-" + f"{int(p.rsplit('-', 1)[1]) + 900:03d}"`。
- **D-09**：`AT-240-13-E-1`：`flagged = {p[:6] for p in sop_p2_problems(wrapped)}`，`assertEqual(flagged, {f"REQ-{n}" for n in range(24, 29)})`（恰五項）；`AT-240-8-E-4` (c)：`assertIn(f"持鎖者資訊（pid / 取得時間）：{os.getpid()} / now", out)`；`AT-219-2-E-1`：`state_of(...) == "verified"` 與 `len(draft_rows(obj["obs_draft"])) == 1`；`AT-215-1-E-3` 的危害見證依 TCS「只記錄、不當通過條件」不做，可接受。

### B-4 D-05：PASS（附 P4 R-03）

fix2 §5 共 12 條：每條一句症狀加座標，涵蓋整個 P2（第 1～5 條 Developer 一審後發現的流程摩擦、第 6～8 條標 `[他包回報]` 取自 `dev_p2_report.md` §4、第 9～12 條本棒）；抽驗座標 `events.py:376`、`tools/ruff.toml:82`、`test_doc_loc_baseline_freshness_r60.py:7038`、`_E501_DEBT_CEILING` 皆存在；符合 NFR-P2-10 (10)。

### B-5 D-07／D-08：PASS（附 P4 R-06）

- SOP 第 65 行：「`--type link` 記復發連結，`--reopens` 須是已結列，或處置首詞為 `deferred` 的列（P2 R110）」；SOP 仍 268 行。
- `sandbox.py:345-358`：`refuse_unattended(repo, "heldout-freeze", as_json)` 在 `valid_by`、`is_dir`、`params_for` 之前；回歸鎖 `test_d08_heldout_freeze_unattended_precedes_usage_checks`（壞 `--by`＋不存在的 `--from`＋無人值守 ⇒ rc 1 `UNATTENDED-REFUSED`、事件帳本不變；對照組未設 ⇒ rc 3）。**突變**（複本把順序改回用法檢查在前）⇒ 紅，還原綠。
- `decide` 未動：`decwrite.py` 的 index 版與工作樹零差異（`git diff` 0 行），`def decide`／`_usage`／`params_for`／`refuse_unattended` 仍在 200／201／202／203 行（與一審相同）。

### B-6 D-10：PASS

- `python -m unittest discover -s tools/tests -p test_doc_loc_baseline_freshness_r60.py -k MainGuard -v` ⇒ rc 0、四測 ok（`test_every_test_file_keeps_its_script_entry_last`、`test_a_guard_followed_by_statements_is_flagged`、`test_a_guard_at_the_tail_or_no_guard_is_clean`、`test_the_scan_goes_red_on_a_real_file_with_the_guard_in_the_middle`）。
- 紅綠自證：複本把 `main_guard_problems` 改成恆回 `[]` ⇒ `test_a_guard_followed_by_statements_is_flagged` 紅（`AssertionError: 0 != 1 : []`）；守衛搬回中段 ⇒ 真檔掃描紅（見 B-1）。還原後皆綠、位元組相同。
- 兩支既有違反檔：`test_smoke_ci_sync.py`（現守衛第 1569 行）、`test_schedule_capability_parity.py`；git diff 僅守衛搬移；腳本模式收集數＝pytest 收集數：42／42（`OK (skipped=1)`）、16／16。

### B-7 追加項（`verify` 拒收 JSON 化）：PASS

`verify.py:188-200` `_measure` 增 `as_json` 參數並傳給 `wv.reject`；`test_selfimproving_verify.py:475-505` `test_d11_verify_json_rejection_is_json` 對 `SANDBOX-TREE-DRIFT`、`SANDBOX-SWAP-FAILED` 各斷言 `json.loads` 成功、`ok false`、`rc 1`、`verb verify`、`codes` 恰為該碼、鍵序同閘門拒收、`obs_draft` 恰一列、無 `Traceback`，並以文字模式對照（首行 `reject `、不以 `{` 起頭）。**突變**：`wv.reject(repo, "verify", bad, False)` ⇒ 兩個子測皆紅，還原綠。

### B-8 閘門重跑：PASS

見 §D（SI 全測 `339 passed, 1090 subtests passed in 275.45s (0:04:35)` rc 0；`check` rc 0；`check_loc_budget` rc 0；ruff rc 0；`git diff --check` rc 0）。

### B-9 TCS〈勘誤一〉對照：PASS（附 P4 R-04、R-05）

- **範圍**：`git diff HEAD` ＝ `33 insertions, 1 deletion`；以 LF 位元組比對，**勘誤標題之前的全部本文與 HEAD 凍結版位元組相同**（sha256 `c261740974ad…`，即凍結 digest），變動只在尾端（舊 287 位元組的「（無。…）」替換為 9341 位元組）⇒ 沒有任何既有 AT 的 id、判定碼名稱被改，也沒有刪 AT。標題自述與實況一致。
- **逐條對照**：
  - 事由行「P1／P2／P3／P4＝0／1／5／4」與一審相符。
  - **E-01～E-20**：與我一審 §E 逐條同字面同落點（E-01 REQ-26 三處、E-02 R75、E-03 R107 (c) 站點清單、E-04 digest8、E-05 CARD-CHANGED、E-06 `*` 整批用語、E-07 SOURCE-UNAVAILABLE 兩項、E-08 五碼、E-09、E-10、E-11 優先序、E-12 `probes_n`、E-13 `ls-files`、E-14 `verify<K>.json`、E-15 孤列、E-16 `evwrite` 探針名、E-17、E-18、E-19、E-20）；沒有漏條、沒有字面錯置。
  - **E-21**：不是我的「備選」字面，而是較強版——`decide` 依 R80 明文（用法錯誤 rc 3 先）、`heldout-freeze` 依 R70（拒收先）並指向回歸鎖；與實作與 D-08 一致，接受（細節見 R-06）。
  - **E-22～E-26** 與 fix2 §6 同；E-22 併入兩條 OBS 回歸鎖名、E-17 併入 fix2 對 R96 (c) 與「還原寫入失敗＝盡力而為」的補述，皆與實作（`obswrite.py:90-94`）一致。
  - **E-27**（R69 補註）與 fix2 §9 ③ 一致，並登記 `test_d11_verify_json_rejection_is_json`。
- 差異只有兩處小項，見 R-04（引用的報告檔尚不存在）與 R-05（E-08 已改五碼而 AT-240-3-E-1 的測試仍只釘三碼）。

### B-10 根層鎖：PASS（只讀 log）

`root_full_p2d.log`（檔時 2026-10-22 04:16:27，晚於 fix2 報告 04:08:15，故涵蓋追加項）：`✅ unittest 數量下限釘選通過：發現 5767 個測試（下限 5755）`、`ROOT rc=0`。5767＝一審 5756＋fix2 新增 11 支（sandbox 檔 +6、`MainGuard` +4、`d11` +1），與 fix2 預估相符。護欄重釘（第六列、`guard_self` 桶）屬主控持有面，未審。

### §C 殘留缺陷（皆 P4；無 P1／P2／P3）

### R-01 [P4] `obswrite._orphan_guard.restore` 雙重失敗時靜默吞掉
- `tools/lib/selfimproving/obswrite.py:90-94`：事件追加失敗後的還原寫入若也失敗（`except evwrite.Reject: pass`），stderr 沒有 `OBS-ORPHAN`，而 `wv.append` 的泛用訊息仍寫「事件追加失敗（OSError），帳本未變動」（對事件帳本為真、對 OBS 帳本為假）。TCS〈P2 拒收碼表〉`obs-add` 列把 `OBS-ORPHAN` 列為 stderr 碼。
- 建議：該 `except` 分支也寫與 `:96-97` 同一則 `OBS-ORPHAN …` 到 stderr，並在 `test_d02_obs_restore_failure_does_not_mask_the_append_failure`（`test_selfimproving_sandbox.py:786`）補 `assertIn("OBS-ORPHAN", err)`。孤列仍由 `check` 的 `obs.console_audit` 標紅（已有測試釘住），故不阻擋。

### R-02 [P4] 同族原語 `rmtree` 仍可能讓 `verify` 以 traceback 穿出
- `tools/lib/selfimproving/verify.py:144-145`：`if tree.exists(): si_sandbox.rmtree(tree)` 在 `swap_dir` 的 handler 之外；Windows 上沙盒樹內檔案被佔用時 `rmtree` 的 `OSError` 仍穿出（同型但不是 `os.replace`，不在 D-02 債表與 E-22 範圍）。
- 建議：把 `rmtree` 併入同一個 `try`（轉 `SANDBOX-SWAP-FAILED`，detail 帶類名）；`sandbox.run` 的 `rmtree(stale)`（`sandbox.py:253`）同型，可一併檢視。

### R-03 [P4] fix2 §5〈流程摩擦〉座標品質
- 第 11 條「任務書 §2 第 1 項指令」不是可定位座標（SOP〈擷取者〉要求 `檔:行`、DEF 號或 sid＋line）；第 2 條一次列三個座標且 `test_apply_lock.py:166`、`test_smoke_ci_sync.py:967`、`test_schedule_capability_parity.py:536` 已因修復失效（守衛現在分別在 474、1569、597）。
- 建議：入帳時第 11 條改指 `…\si_p2\dev_p2_fix2_brief.md` 的 §2 行號；第 2 條改指現行鎖 `tools/tests/test_doc_loc_baseline_freshness_r60.py:7145`（`TestMainGuardIsTheLastTopLevelStatement`）。

### R-04 [P4] 〈勘誤一〉引用的審查報告檔尚不存在
- TCS 尾端〈勘誤一〉事由行引用 `docs/06_quality/SCG4-REVIEW-SelfImproving-P2-20261022.md`；`Test-Path` 為 False（`docs/06_quality/` 只有 P0、P1 同名檔）。落檔前為懸空引用（根層全套 rc 0，無鎖看它）。
- 建議：主控於 RELEASE_READY 落該報告（以一審、二審判決檔為素材）後再 `spec-refreeze`，或先把事由行改指兩份 scratchpad 判決的收錄位置。

### R-05 [P4] E-08 改五碼而測試仍只釘三碼
- 〈勘誤一〉E-08 把 `_NONBLOCKING`「增三碼」改「增五碼」並註明 AT-240-3-E-1 末段同改；`check.py:31-34` 實有五碼，但 `test_selfimproving_events_p2.py:981-983` 仍只斷言 `⊇ {CONSOLE-AUDIT-MISSING, CONSOLE-KEY-MISSING, TRANSCRIPT-UNAVAILABLE}`。
- 建議：該超集補 `ORIGIN-MISSING`、`ATTACHMENT-TIME-UNKNOWN` 兩碼。

### R-06 [P4] 無人值守與 rc 3 預檢的順序在寫入動詞間不一致（E-21 只釘清兩個）
- `heldout-freeze` 現先拒收（`sandbox.py:347`）；其餘皆先做 rc 3 用法檢查：`sandbox`（`sandbox.py:223` 先於 `:227`）、`verify`（`verify.py:158` 先於 `:164`）、`promote`／`rollback`（`promote.py:65` `_usage` 先於 `:66`）、`card --issue`（`decwrite.py:368` 先於 `:369`）、`decide`（R80 (a)(b) 明文，`decwrite.py:201` 先於 `:203`）。
- 建議：E-21 補一句涵蓋其餘動詞（「R70 的『先於全部其他前置檢查』指 rc 1 的前置碼；rc 3 用法檢查先於拒收，`heldout-freeze` 為例外並以回歸鎖釘住」），或之後統一；不影響零寫入保證。

### §D 指令與 rc 表（`$env:PYTHONUTF8='1'`；rc 先存變數再印）

| # | 指令 | rc | 關鍵輸出 |
|---|---|---|---|
| 1 | `python tools/tests/test_apply_lock.py -k AT_240_8_1_`／`python tools/tests/test_apply_lock.py`／`python -m pytest tools/tests/test_apply_lock.py -q -p no:xdist -o addopts=` | 0／0／0 | `Ran 1 test`／`Ran 14 tests`／`14 passed in 6.41s` |
| 2 | `python qa_p2\qa_main_last.py` | 0 | 14 支 SI 檔守衛後 0 個頂層敘述 |
| 3 | `python -m unittest discover -s tools/tests -p test_platform_neutral_paths.py -k DirEntry` | 0 | `Ran 7 tests OK`；`_DIRENT_UNGUARDED_DEBT={'live': 37}` |
| 4 | `git show HEAD:tools/tests/test_platform_neutral_paths.py` 對工作樹 sha256 | — | 皆 `fbc429f6…4ed2`；`git status` 無該檔 |
| 5 | `python -B qa_p2\qa_census.py` | 0 | SI 套件 3 站點皆已處置、未處置 0；兩個記憶體突變各 +1 |
| 6 | `python -m unittest discover -s tools/tests -p test_doc_loc_baseline_freshness_r60.py -k MainGuard -v` | 0 | `Ran 4 tests OK` |
| 7 | `python tools/tests/test_smoke_ci_sync.py`／`test_schedule_capability_parity.py`（腳本模式）與 `pytest --collect-only` | 0／0 | 42／42（skipped=1）、16／16 |
| 8 | `python qa_p2\qa_mut2.py base`（複本基線） | 0 | d02／d08 六測 passed；`MainGuard` 4 OK；`d11` passed |
| 9 | `python qa_p2\qa_mut2.py d02`（4 突變） | 0 | 4／4 紅、還原綠、位元組還原 True |
| 10 | `python qa_p2\qa_mut2.py d03d04`（2 突變） | 0 | D03 `SUBFAILED[a]` 紅；D04 `SUBFAILED[b]` 紅；還原綠 |
| 11 | `python qa_p2\qa_mut2.py d08d10d11`（5 突變） | 0 | D08、D10a（真檔掃描與腳本模式 `Ran 0`）、D10b、D11 皆紅；還原綠 |
| 12 | `python -m pytest <13 個 test_selfimproving_*.py＋test_apply_lock.py> -q -n 4 --dist worksteal -p no:cacheprovider` | 0 | `339 passed, 1090 subtests passed in 275.45s (0:04:35)` |
| 13 | `python tools/selfimproving.py check --json` | 0 | `overall=PASS items=32`；`events.dec_quote`／`dec_console`／`verdict`／`obs.console_audit`／`params.keys`／`prop_files` 皆 PASS |
| 14 | `python AutoClaude/tools/check_loc_budget.py --json` | 0 | `total=18633 cap=20438 total_violation=false` |
| 15 | `.venv\Scripts\ruff.exe check tools/lib/selfimproving tools/selfimproving.py tools/lib/apply_lock.py tools/tests/test_selfimproving_*.py tools/tests/_selfimproving_*.py tools/tests/test_doc_loc_baseline_freshness_r60.py tools/tests/test_schedule_capability_parity.py tools/tests/test_smoke_ci_sync.py tools/tests/test_platform_neutral_paths.py` | 0 | `All checks passed!` |
| 16 | `git diff --check`／`git diff --cached --check` | 0／0 | 零輸出 |
| 17 | `python qa_p2\qa_literal_ids.py` | 0 | `distinct literal IDs: 24 not in real ledgers: 0` |
| 18 | `python qa_p2\tcs_cmp.py`（TCS 工作樹對 HEAD） | 0 | 勘誤標題前本文位元組相同；尾端 287→9341 位元組；`git diff --numstat` 33／1 |
| 19 | 讀 `…\si_p2\root_full_p2d.log` | 0（log 內 `ROOT rc=0`） | `發現 5767 個測試（下限 5755）` |

### §E 審查前後 `git status --short` 相同的證據

- 審查前 `qa_p2\git_status2_before.txt`（67 行）；審查後 `qa_p2\git_status2_after.txt`（67 行）；兩檔 SHA256 同為 `A24A061C80C5B4743F68604770F478E978CC076CE635D0DE21305F4D951C6D4E`。
- `git diff --numstat`（unstaged 35 列）與 `git diff --cached --numstat`（staged 40 列）審查前後逐列相同。
- 所有突變、複本、探針皆在 `qa_p2\repo_copy2\`；未做任何 git 寫入、未派子代理、未連網、未起背景任務、未跑 `run_root_unittests.py`。

### §F 〈流程摩擦〉（QA 二審；一句症狀加一個座標）

1. 〈勘誤一〉事由行引用尚未落檔的審查報告，無鎖能看見懸空引用 — `docs/03_testing/contracts/TCS-SelfImproving-P2-20261021.md`（尾端〈勘誤一〉第 5 行）。
2. 複本做突變要先補拷夾具從 ROOT 取的 `AISDLC_SDD/scripts/sdd_version.py`，否則基線就假紅 — `tools/tests/_selfimproving_fixtures.py:480`。
3. 記憶體內匯入 `test_platform_neutral_paths` 才能對突變原始碼驗債鎖，整檔 `unittest -k DirEntry` 在殘缺複本上會因 census 對不上而假紅 — `tools/tests/test_platform_neutral_paths.py:3705`。

## §N Developer〈流程摩擦〉（NFR-P2-10 (10)；整個 P2；修復棒二交卷 §5 由主控謄寫，R-03 座標已修正）

1. Developer 交卷缺 NFR-P2-10 (10) 要求的〈流程摩擦〉節 — 第二段交卷報告（全檔；修復棒二補上）。
2. `test_apply_lock.py` 把新測試附加在 `unittest.main()` 之後，腳本模式只跑 7／14 仍印 OK；同型另藏在兩個既有檔 — `tools/tests/test_apply_lock.py`（修前第 166 行）、`tools/tests/test_smoke_ci_sync.py`（修前第 967 行）、`tools/tests/test_schedule_capability_parity.py`（修前第 536 行）；現由 `TestMainGuardIsTheLastTopLevelStatement` 鎖住。
3. NFR-P2-10 (14) 無機械物，根層全套 rc 0 仍漏 D-01 — TCS 第 318 行（D-10 已落機械物）。
4. Developer 的 `at_missing.py` 以 `def test_<底線形>` 子字串比對，被前綴相同的兄弟 AT 遮住缺口，錨定計數才是 R102 判準 — OBS-SI-265。
5. `mut.py` 直接改寫真實樹，在唯讀審查下不可用，複本還要補拷夾具從 ROOT 取的 `sdd_version.py` — `tools/tests/_selfimproving_fixtures.py:480`。
6. 護欄層一輪重釘淨增遠超每輪上限 515，只能走一次性例外名冊 — `tools/tests/test_adr_xplat001_c1c2_lock.py`（R214 列、`_REPIN_APPROVED_ROUND_OVERAGE`）。
7. 新檔未 `git add` 使「已追蹤檔 import 未追蹤檔」連鎖紅，commit 前無法讓根層全套 rc 0 — `tools/tests/test_doc_loc_baseline_freshness_r60.py`（`TestDef200133TrackedImportsDoNotPointAtUntrackedFiles`）。
8. `_E501_DEBT_CEILING`（136）在 HEAD 本身已是 137，與 Developer 無關卻擋住全套 — `tools/tests/test_subprocess_encoding_hygiene.py`（`_E501_DEBT_CEILING`；成因＝哨兵修復棒 QA 複審 R2 一格，主控改行）。
9. TCS 內部字面互相衝突需靠 ⚖ 繞行：R72「reasons 空⇔PASS」「probes_n 0⇔verify_sha256 null」使 AT-219-2-E-1、AT-240-3-E-1 (b) 的 Given 字面不可執行 — TCS AT-240-3-E-1 Given (b)、`tools/lib/selfimproving/events.py:376`（勘誤一 E-12、E-23）。
10. `ruff --isolated --select E501` 與 repo 設定結果不同（`tests/*.py` 被豁免、lib 檔不豁免），只量一邊會漏 lib 檔 — `tools/ruff.toml`（per-file-ignores）。
11. PowerShell 工具不展開 `tools/tests/test_selfimproving_*.py` 這種萬用字元引數，直接餵 pytest 得 `no tests ran` rc 5 — 任何 PowerShell 呼叫 `python -m pytest <萬用字元>` 的形態（OBS-SI-267；先 `Get-ChildItem` 展開）。
12. 任務書的修法字面（D-04 (b) `reasons=[]`）未先對規格自洽性預跑，照做會得到「FAIL 變 PASS」的反效果 — 主控修復棒二任務書 D-04 一行（OBS-SI-268；勘誤一 E-23）。
