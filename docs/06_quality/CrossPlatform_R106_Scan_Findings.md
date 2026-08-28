# R106 掃描發現 — Windows 11 交接兩筆跨平台真缺陷收斂

<!-- guard-total:R106 --> **本輪護欄層累積淨額（稽核痕跡合計，同輪多列合併）＝ 88656 → 89125（+469）**

<!-- guard-total:R107 --> **R107（帳本結案輪，寄居本檔＝R103 寄居 R102 檔的既有判例）護欄層累積淨額＝ 89125 → 89124（-1）** —— 結案包 #3（DEF-200-166／171／225、DEF-101-950）四筆判準落地，抵銷＝八段散文搬遷 `CrossPlatform_Guard_Line_History.md`〈站點級守衛四種罩法 WHY〉至〈SC-2/3/5 射程收窄 WHY〉八節；同輪兌現 (107, 630) 到期義務並重新武裝 (109, 610)。

<!-- guard-total:R108 --> **R108（架構輪，寄居本檔＝R107 寄居本檔的既有判例）護欄層累積淨額＝ 89124 → 89314（+190）** —— ①DEF-200-230 回歸鎖落地：`test_quota_policy.py` 新增「額度取數端點字面只准住一個家」判準（3071→3152，+81）＋鎖檔自身稽核列與凍結前綴延伸（+13）；②DEF-200-233 修復（macos-compat-ci 連續紅）：`test_run_root_unittests.py` 豁免表 stale 面方向鎖＋消失面補位鎖（2201→2283，+82）＋鎖檔自身（+14）。逐檔清單見 `CrossPlatform_R108_Review.md`〈護欄層重釘逐檔清單〉節。

## 附記（DEF-101-752 收斂）

本輪稍後又追加一筆與上述兩項 Windows 11 真機修復無關的獨立收斂：`DEF-101-752`
（驗證載具掃描面 untracked 盲區）的殘餘承接站點本輪收斂，多支 `tools/tests/` 掃描面
函式由 tracked-only 改為 tracked ∪ untracked-not-ignored。逐站點紅綠實測與跳過站點
理由見 `docs/06_quality/CrossPlatform_R82_DEF101752_Untracked_Scan_Closure.md`；護欄層淨額
88698 → 88817（+119，含本檔自身逐檔漂移與凍結前綴延伸，逐筆重釘過程已收斂合併為
單列）已併入上方總量。

## 附記二（帳本結案輪修復包補 DEF-101-752 問題 3）

帳本結案輪的四方複審修復包為 `DEF-101-752` 殘餘站點（見上一節）逐一補上永久回歸測試
類別（驗證 untracked 探針真的被掃描面看見），落地時未同步重釘護欄層行數棘輪，讓
淨額 +287 一度不出現在任何地方（ARCH-01 同型復發）。逐檔更動：
`test_windowsapps_guard_cross_consistency.py` +38、`test_ps1_bom.py` +36、
`test_bash32_compat.py` +35、`test_ps51_compat.py` +35、
`test_windows_forbidden_filename_parity.py` +40、`test_find_git_bash_parity.py` +25、
`test_workflow_permission_concurrency_lock.py` +37、
`test_windowsapps_guard_bash_parity.py` +41。合法出口逐條實查：刪死碼不適用（新增的是
此前不存在的永久回歸鎖，無等量舊邏輯可退場）、抽共用層不適用（逐站各自守自己站點的
既有 union 掃描面，測試形狀各異無法合併）。本輪就地重釘後護欄層淨額
88817 → 89125（+308，含本檔自身逐檔漂移與凍結前綴延伸，逐筆重釘過程已收斂合併為
三列）已併入上方總量。

## 背景

R105 交接留給 Windows 11 輪的兩個獨立問題（見 R105 收尾備忘錄「三方 CI 連續紅」段）：
`root-infra-ci`（windows 標籤跨平台驗證矛盾）與 `windows-compat-ci`
（`test_check_hooks_liveness.py` 真機斷言問題）。本輪在 Windows 11 真機上逐一重現、
診斷根因並修復，兩者皆非假紅。

## 發現一：root-infra-ci — `_WINDOWS_SKIP_TAG_EXEMPT` 豁免表結構性為空

`tools/lib/skip_tag_policy.py` 的 `_WINDOWS_SKIP_TAG_EXEMPT: dict[str, str] = {}` 自建立
以來從未被使用（檔頭註記「現況為空集合」），導致 7 支測試（`test_dev_start.py` 的 zsh／
tool-absence 系列、`test_dev_start_ps1_lastexitcode.py` 的 zsh 系列、
`test_smoke_ci_sync.py` 的 zsh 系列）的 skip 理由只是**比較性提到** `Windows`
（例如「在 Windows 上把 zsh 裝起來也跑不出有意義的結果」），就被
`report_untagged_windows_like_skips()` 的關鍵詞啟發式誤判成「該貼
`[WINDOWS-NATIVE-ONLY]` 卻沒貼」，讓 `tools/run_root_unittests.py` 在 Linux（root-infra-ci
runner）上恆紅。

修復：把這 7 支測試 id 具名加入 `_WINDOWS_SKIP_TAG_EXEMPT`（每筆附精確理由）。連帶
修正 `tools/tests/test_run_root_unittests.py` 兩支既有測試（`test_real_run_with_floor_
reds_on_an_untagged_windows_skip`／`test_the_check_is_wired_into_the_runner_and_reds_
the_run`）原本寫死「豁免表是空的」的假設——改用 `mock.patch.dict(...,clear=True)` 正確
隔離活體全域表，否則合成樹測試會被真表的 7 筆豁免污染而誤判 rc=1。

## 發現二：windows-compat-ci — Stop guard 的 native／alien 分類測試沒有平台感知

`.claude/hooks/check_claim_provenance.py` 的 Stop guard 透過 `tools/lib/hook_wiring.py`
的 `runtime_carrier_verdict()` 判斷逐字稿裡哪個 hook 載具失敗是「本平台自己那條」
（native，真缺陷）、哪個是「跨平台配對刻意的 fail-open」（by-design，該安靜）；該函式
正確地依真實 `os.name` 決定方向。但 `tools/tests/test_check_hooks_liveness.py` 的
`TestTheStopGuardIsTheAutomaticReaderOfThatEvidence` 兩支測試跑的是**真子行程**（無
`on_windows` 注入接縫），卻寫死「POSIX 那條該說話、named block_destructive_git.py」——
這在 mac 上是對的，但在 Windows 真機上兩者判準本就會反過來（`pythonw.exe` 才是
Windows 原生載具，`_hook_launcher.py` 裸路徑在 Windows 上反而是「跨平台配對」的那條）。

修復：兩支測試改依真實 `os.name` 動態選擇 `_SPEAKS_FIXTURE`／`_SILENT_FIXTURE`／
`_SPEAKS_TARGET`，與同檔 `TestRuntimeCarrierEvidenceIsRead` 早已用
`on_windows=True/False` 顯式驗過的兩個方向一致。已在 Windows 11 真機重現原始失敗、
驗證修復後兩支測試皆綠。

## 逐檔淨行數

- `tools/lib/skip_tag_policy.py`：+38（不受護欄層管轄，非本輪淨額計算對象）
- `tools/tests/test_check_hooks_liveness.py`：+6（護欄層管轄，Stop guard 平台感知修正）
- `tools/tests/test_run_root_unittests.py`：+3（護欄層管轄，兩處合成樹測試隔離活體表）
- `tools/tests/test_adr_xplat001_c1c2_lock.py`：+9（護欄層管轄，本稽核列自身）

合法出口逐條實查：無死碼可刪、抽共用層不適用——上列三支護欄層檔案的修正皆是既有測試
方法內針對真實平台差異／真表非空的必要修正，無等量舊邏輯可退場。
