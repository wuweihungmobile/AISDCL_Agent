# CrossPlatform R213 第四窗（姊妹檔）：掌舵者三問的零信任重驗、乾淨樹 nightly 真跑、兩鏡判決

> 主檔 `CrossPlatform_R213_DebtZero_FourParty_Evidence.md` 於本窗開始時 258,346 bytes，距 `check_defect_log_crossref` 的 fail 線 262,144 只剩 3,798 bytes（warn 線 245,760 已越）⇒ 依 `DEF-101-587` 姊妹檔體例，本窗全部內容落本檔；主檔只套用 P3 文字訂正與〈十一〉末一行指針。登記＝`tools/lib/governance_docs.py`。
> 視窗：2026-10-14 07:4x 起（+08:00），sid `a4b1c822-e0a9-4aec-ab4d-4236250ea11e`；主控＝Fable 5.1、審查鏡＝Sonnet ×2（零信任、對工作樹唯讀、禁跑全套）、開發者＝Sonnet ×1（DEV-F01）。

## 十二-1 掌舵者原文（逐字）與範本〈🏁〉判定

> 1.請徹底完成以上任務，找到沒法完成收斂的根因，徹底解決？請想盡所有辦法完成收斂任務！ ==> 我的完成的定義是沒有積欠技術債與解決已知的所有ＢＵＧ！
> 2.完成實作AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md裡面所有功能！==> 請檢視驗證每個功能都已經完成 E to E 全功能驗證！
> 3.如何將兩邊的 .env同步，哪邊才是正確完整的？這個參數檔該如何維護？ 幫我設計自動同步機制！==> 下次在Windows執行時，幫我自動同步！請進行驗證功能是否ＯＫ？
> 「我的問題(若以下問題，下此不用再重複，請跟我說，我會拿掉，不然就是繼續迭代，直到解決)」「因為Fable Token實在花太兇…請派Subagent時, 使用Sonnet 5！你當主控Agent還是使用Fable 5.1」

判定：T1 成立（同三項；第九次響應，本窗的問法＝「做完了就說，我拿掉」）；T2（新立 P≤2）／T3（CI／nightly 轉紅）／T4（⏸ 再開症狀）皆不成立 ⇒ 不開軌道① 輪、不產四件套；T1 最小響應＝重驗＋commit。

## 十二-2 主控親跑的零信任重驗（量測於 2026-10-14 07:45～08:00 +08:00；每格都是當場輸出）

| 項 | 指令 | 輸出（逐字） | 判定 |
|---|---|---|---|
| 工作樹 | `git status --porcelain`、`git fetch`、`git status -sb` | 0 行；HEAD `3bad16fed5a409c711759b25d1c2505bd7bcc906`；`## main...origin/main` | 乾淨、與遠端一致 |
| 三本帳 | `python tools/check_defect_log_crossref.py --unresolved-count`／完整版 | `未結列數＝0／全部 232 列｜warn=86 fail=98`；完整版 rc=0 且 `外部阻塞軌…：0 筆`、`結構性長債軌…：0 筆` | 0／0／0 |
| 交接載體 | `python tools/check_handoff_carriers.py` | rc=0；`[census] 當前輪＝R213`；commit 訊息 767 則與 tracked 載體 212 份皆無前瞻宣告 | 無延後宣稱 |
| HEAD CI | `gh run list --commit 3bad16fe…` | macos-compat-ci `38458936503`／root-infra-ci `38458935992`／windows-compat-ci `38458936161` 皆 `completed success`（push，2026-10-13T19:57:15Z） | 全綠；AutoClaude CI／aisdlc-sdd-ci／shellcheck-ci 因 `paths:` 過濾未觸發，上一個碰到其路徑的 7fd45b8a 皆 success |
| .env（mac） | `python tools/lib/quota_policy.py --env-doctor` | `[empty-local] .env 已無任何有值的行（只剩註解／空白鍵）⇒ 可直接刪除該檔`；`結論：0 個問題 ⇒ rc=0` | 乾淨（註：`tools/lib/quota_env_layers.py` 無 CLI，直接呼叫它會靜默 rc=0——主控本窗先踩了一次） |
| nightly 錨 | `python tools/refresh_nightly_anchor.py --check-head` | rc=0 `✅ nightly 錨判準通過（HEAD）…（1 天前，上限 14 天）nightly-red=none` | 新鮮 |
| 02:00 排程 nightly | `AutoClaude/logs/nightly_mac_launchd.log` 末行 | `今日已有心跳（2026-10-14）——RunAtLoad 補跑去重，跳過本輪（手動重跑：--force）` | 設計行為（R15 當日去重）；00:00:25 那次是上一窗手動 kickstart、在編修中的髒樹跑出 `PASS=4 FAIL=1`（失敗 stage root_unittests） |

### 十二-2b 乾淨樹（HEAD）mac nightly 真跑（本窗主控 `--force`）

- 指令：`env -u AUTOSDD_PARALLEL_TESTS /bin/bash AutoClaude/tools/run_local_nightly.sh --force`（Bash 工具 `run_in_background`、阻塞到結束；2026-10-13T23:49:54Z 起、23:54:43Z 止；rc=0）。跑的期間主控不動工作樹（log 自證 `SAMPLE VALIDITY: tree_state=clean dirty_entries=0 … head=3bad16fe`）。
- RunId log `AutoClaude/logs/nightly_mac_20261014_074954.log`：`--- [1/5] macos_smoke PASS（28s）---`、`--- [2/5] root_unittests PASS（125s）---`、`--- [3/5] autoclaude_gate PASS（46s）---`、`--- [4/5] sdd_ci_gate PASS（47s）---`、`--- [5/5] nightly_anchor PASS（8s）---`、`===== nightly 彙總：PASS=5 FAIL=0 =====`。
- PG 真起真收：`[nightly][docker] daemon 不可達 ⇒ 已 open -a /Applications/Docker.app` → `[nightly][pg] alembic current: 0018_version_kind_discriminator (head)` → `[skip census] AutoClaude/tests@darwin+pg+nested+pgext 共 56 支：platform=53／tool-absence=0／env-disabled=2／structural-pair=1／debt=0／untagged=0` → `[nightly][pg] 已收容器（docker compose down -v）` → `[nightly][docker] 已收 Docker Desktop（pgrep -f Docker.app 為空；osascript rc=0/0；約 15s）`。剖面為 `+nested`（自 Claude Code session 內啟動，CLAUDECODE=1）；launchd 排程跑的是 `+solo`；兩剖面皆已入 `tools/lib/skip_group_policy.py`。
- 00:00:25 那次 `失敗 stage： root_unittests`（log 內 `Traceback` 3／`===== FAIL:` 3）在本次全部消失（工作樹內容相同，差別只在上一窗的編修已 commit）。
- 副作用：nightly 第 5 階段回填 ONBOARDING.md 錨（表③-b 列改指 `38450031413`／`7fd45b8a`；錨 `nightly-run=38279403926 nightly-checked-at=2026-10-12T16:43:36+00:00`；`--check` 工作樹 rc=0），隨本窗 commit 入庫。

## 十二-3 兩鏡判決（Sonnet；任務書與報告備份＝`~/.autosdd/r213_window4_scratch/`）

- **mirrorB（.env 同步 E2E；隔離複本 bare＋old_machine＋pusher＋pre_hook＋pristine）：CONDITIONAL，P1=0 P2=0 P3=4 P4=6。** 成立項：舊機器 `.env`＝`.env.example` 複本＋3 遮蔽行＋2 `# override-ok:` 行＋機密行＋註解 ⇒ pusher 改 `env.shared` HALT 98→97 push、old_machine `git pull --ff-only` rc=0 後印 `[post-merge dispatcher] env.shared 同步：已自動修復，備份＝.env.bak.20261013T235842Z（…）；刪除 21 行（…）`，備份 sha256 等於 pull 前快照（cmp rc=0）、遮蔽／冗餘 21 行全刪、`override-ok`／機密／註解位元組不動、事後 doctor `結論：0 個問題 ⇒ rc=0`、`AUTOSDD_QUOTA_HALT_PCT = 97〔env.shared〕`；負控「已是最新」只印 `Already up to date.`＝git 不跑 post-merge（hook 檔頭與 ONBOARDING:123 既寫，不是缺陷），新 commit＋乾淨 `.env` 才印 `env.shared 同步：0 個問題`；五條旁路（`AUTOCLAUDE_SKIP_HOOKS=1`／`AUTOSDD_UNATTENDED`／`[unknown]` 混入／無 `.venv`／未設 `core.hooksPath`）各印預期字樣且 `.env` 不變；hook 與參數檔同一次 pull 帶進（複本停 035746ba、pull 29 個 commit）當次即生效；`AutoClaude/.env` 機密兩行保留、pull 輸出 0 次洩漏；CRLF 檔修復後仍 CR 結尾；cp950／BOM 檔判人處理不動；雲端 run `38450031413` job log 行 2636 `已自動修復`、行 2683 `env-sync-e2e: PASS`，run `38440002419` 同；`git log 7fd45b8a..HEAD -- <hook 與相關五檔>` 為空＝雲端證據適用 HEAD；單測 `tools/tests/test_quota_env_layers.py` 38 項 OK、13 個突變殺 11（倖存 M4＝`--fix` 連 override-ok 行一起刪、M7＝修復後複驗失敗仍印已修復；兩者現行為皆正確，登 W4-1）。
- **mirrorA（結案稽核）：CONDITIONAL，P1=0 P2=0 P3=9 P4=10。** 成立項：主帳本獨立解析（不用 `_classify`）232 列＝fixed 181／closed-by-decision 50／no_action_needed 1，open／routed／partial 皆 0；儀器靈敏度＝隔離複本把 DEF-200-531 改 open ⇒ `未結列數＝1…未結列 ID：DEF-200-531`、完整版 rc=1（「0」不是儀器失明）；第三窗 7 列（693／313／253／856／075／960／531）所引 run 皆 success 且 headSha 吻合（38440002419＝4ce2d1ff、38450031413＝7fd45b8a、38454229981 attempt 2＝39690c53）、#9～#14 step 皆 success、census／orphan-probe／smoke-local／env-sync-e2e 字樣逐字對上；程式碼座標（`parallel_shard.py:330 adopt_kill_on_close_job`、`_PLATFORM_BOUND_DEBTS … = {}`、`pytest_skip_census.py`）皆在，`ParallelShardKillOnCloseJobTest` 4 項 OK、釘值突變 36/36 RED；DEF-200-531 job `runner_id=0`＋annotation「The job was not acquired by Runner of type hosted even after multiple attempts」＝runner 層事件；4ce2d1ff→HEAD 非文件改動只有 4 檔且不含結案關鍵碼 ⇒ 雲端證據適用 HEAD。PRD §16 以狀態欄解析：§16.2 表 25 列＝✅23／⏸2／📎0／未分類 0，矩陣 ✅ 29 個 ID 與 R211 矩陣逐字相同，活躍 54＝✅52／⏸2／📎0，§16.7 ➖47，29＋25＋47＝101；⏸ 兩列再開症狀可觀測；重跑 10 列（§11.1 `zero_token_patrol_sim --selftest` rc=0、§11.3 `wakechain_e2e --judge` rc=0 S14-core 8/8 tail 7/7 WARN 2、§11.8 `day_long_relay_sim --selftest` rc=0 工作佔比 0.875、§8 列 1 三個突變各紅 1 項、§4.3 PreCompact trace 20:45:44→compact_boundary 20:47:05、A4 `quota_burndown --status` rc=0 等）全符；無法重跑＝§13 帳號端通知、§4.5.2 真機掛拆、真 6h／24h 牆鐘。`RESULT: PASS` 無任何 repo 程式碼會印。殘留警告定性：3 份治理文件逼近上限＝設計上 just-in-time 守門（`check_defect_log_crossref.py:1138-1157` 硬線＝Read 工具 256 KiB；DEF-101-587 姊妹檔慣例），不是債；3 筆已結列殘留待辦字（DEF-101-060／200-129／200-277）皆非活待辦。對掌舵者的 E2E 措辭：54 座標 PASS 51／JUDGED 3／FAIL 0；⏸ 2（法務、A7）；§11.1／§11.8 為模擬時鐘、§4.5.2 自標待真機；QA-B U1～U7 與〈十一-11〉理論洞未驗。

## 十二-4 文件訂正（本窗已套用；全部 P3，機制不動）

| # | 檔案:行 | 原文（節錄） | 改成 | 來源 |
|---|---|---|---|---|
| 1 | 主檔 :107、:250 | `--env-doctor` 看 `RESULT: PASS` | 看 `結論：0 個問題 ⇒ rc=0`（程式從不印 `RESULT: PASS`；`grep -rn` tools/ 零命中）；(2)(4)(5) 已由 windows-compat-ci nightly-full #12／#14 在 windows-latest 實跑 | B-02／A F-03 |
| 2 | 主檔 :307 | 看到 `env.shared 同步：已自動修復` 或 `結論：0 個問題` 即成功 | 乾淨路徑只印 `[post-merge dispatcher] env.shared 同步：0 個問題`（不印「結論：」）；`Already up to date.`＝這次沒跑 hook，改手動 doctor；cp950 主控台認 ASCII 片段 | B-01／B-04／A F-02 |
| 3 | 主檔 :297 | `override-ok` 行保留由 `test_quota_env_layers.py` 單測鎖守 | 該保留目前無單測鎖（只鎖 diagnose 層 `[override]`；突變 M4 存活），由 E2E 實測與 `quota_env_layers.py:172-175` 保證 | B-03 |
| 4 | ONBOARDING.md:110 | 沒有標記的行…自動刪掉 | 與下一層相同或遮住 `env.shared` 的行才刪；`env.shared` 沒有的鍵且值異於出廠者保留（`[local]`），日後 `env.shared` 新增該鍵即成遮蔽 ⇒ 一律加標記最安全 | B-07 |
| 5 | 主檔 :5、:99、:109 | 「四方審查尚未執行…weekly reset 後第一件事」（第一窗狀態、日期型） | 標為第一窗狀態；現況見〈十-7〉〈十一-7〉〈十二-3〉 | A F-09 |
| 6 | 主檔 :341、:352；External :52 | 「31 步全 success」 | 30 success＋1 略過（`if: failure()` 上傳步） | A F-04 |
| 7 | PRD :2687 | 本表 23 列＋29＝52 | 本表 25 列〔✅23／⏸2〕＋29＝54（✅52／⏸2／📎0 不變；不改條文） | A F-05 |
| 8 | 主檔 :363；R213_RESUME.md:4 | tag `r213-w3-wip-preserved` | tag 實際未建；stash commit 8430bf53，內容已隨 A～D 入庫 | A F-06 |
| 9 | External :80 | 856 退役的人工 gate 引文 | 補：未點名 RTO<60s 與 ≥1k 列 BGE-M3 recall、退役後無承接、掌舵者可以 T1 立案 | A F-07 |
| 10 | 主檔 :295 | §11.3 judge 結果 | 補 WARN 2（S6b／C8） | A P4(1) |
| 11 | PRD :2715 | 表格內未跳脫 `\|` | `launchctl list \| grep` | A P4(2) |
| 12 | R213_RESUME.md:1 下 | 「還沒做」四項以待辦語氣留 tracked | 加史料標記（四項已於 A～D 完成） | A F-08 |
| 13 | `tools/tests/test_check_defect_log_crossref.py:2486` | 「ID 數＝未結列數」在 0 列時恆真（突變存活） | 補合成帳本斷言（DEV-F01；同檔等行數，結果見十二-3b） | A F-01 |

### 十二-3b DEV-F01（Sonnet）結果

- **STATUS: DONE**（Sonnet，64 次工具呼叫）。只改 `tools/tests/test_check_defect_log_crossref.py` 一支：`wc -l` 改前／改後 3954／3954（逐檔行數凍結表 `test_adr_xplat001_c1c2_lock.py:629` 的 3954 不動）；新增 7 行合成帳本斷言（`contextlib.redirect_stdout` 擷取 `report_unresolved({"DEF-1-1": "open", "DEF-1-2": "fixed"})` ⇒ 斷言 `未結列數＝1／`、`未結列 ID：` 之後含 `DEF-1-1` 不含 `DEF-1-2`），以同檔 7 段 docstring 收尾 `"""` 併行抵銷（文字一字未動，whitespace-stripped 相等 True）；原有斷言一條未刪。
- 驗證（逐字）：`ruff check` rc=0 `All checks passed!`；單檔 `Ran 276 tests`／`OK`（主控親驗亦 `Ran 276 tests in 9.681s`／`OK`）；隔離複本突變（`report_unresolved` 改成不印逐筆 ID）：HEAD 版測試 rc=0 OK（突變存活＝重現 mirrorA F-01）、新版測試 rc=1 `AssertionError: 'DEF-1-1' not found in '\n'`（突變被殺）；加映「印出全部帳本 ID」「計數行改用總列數」兩突變亦各被精準擊殺；主樹根層全套 `tools/run_root_unittests.py` rc=0（`發現 5375 個測試（下限 5326）`、無紅字、`[skip census] tools/tests@darwin 共 47 支…欠債型 0 支`、真實 TEMP 圍籬零變動）；分桶棘輪 `measure_shrink_only` 改前改後皆 `{'prose': 4303, 'guard_self': 3149}`（+0）；`sync_onboarding_baselines.py --check-snapshot` rc=0 `§7 表② 指紋相符 macOS 欄`（指紋只涵蓋四棵樹、不含 `tools/tests` ⇒ 本改動不需回填表②）。
- 誠實揭露：加映突變第一輪吃到舊 `.pyc`、第二輪 env 參數順序寫錯（rc=127），皆以 `PYTHONDONTWRITEBYTECODE=1`＋清 `__pycache__` 重做，舊 log 標作廢；必要的 no_ids 突變不受影響。

## 十二-5 理論洞清單（P4；只登記、不修、不立輪；再開＝症狀驅動；口徑同〈十一-11〉）

| # | 洞 | 暴露度（三取一） | 一句可觀測再開症狀 |
|---|---|---|---|
| W4-1 | `--fix` 保留 `# override-ok:` 行無單測（突變 M4 存活）；`post-merge:107-114`「修復後仍有問題」分支亦無鎖（M7 存活） | 構造性（隔離複本突變）；真實語料 0 命中 | 某次 pull 後 `.env` 的 `override-ok` 行消失（備份檔仍有） |
| W4-2 | UTF-16LE `.env`（PS 5.1 `>` 寫出）⇒ hook 印「0 個問題」、本機覆寫被默默忽略（ONBOARDING 編碼段已自陳） | 構造性 | Windows 上 `.env` 有值但 doctor 顯示該鍵來源非 `.env` |
| W4-3 | 修復路徑把 doctor 全文印 4 次才出摘要；非 UTF-8 時 🔴 行不提編碼，真因在上方 `[錯誤]` 行 | 理論 | 掌舵者回報 pull 畫面看不懂哪一行是結論 |
| W4-4 | windows-compat-ci 步驟 #13 fixture 只有 3 行 LF（未覆蓋 CRLF／override-ok／UNATTENDED／乾淨路徑）；NTFS 行為仍為 mac 位元組級推論 | 理論 | Windows 實機 pull 後 `.env` 行尾或 override-ok 行與 mac 結果不同 |
| W4-5 | `.env.bak.*` 無輪替（皆 gitignored） | 理論 | repo 根累積 ≥20 個 `.env.bak.*` |
| W4-6 | 693／075／960 的凍結歸檔列仍是結案前字樣（`fixed` 只在散文） | 理論 | 歸檔列被引用為「現況」 |
| W4-7 | 856 刪 stub 後 pg-e2e-nightly 尚未跑過排程 | 理論（排程通道） | 下一次 pg-e2e-nightly 排程 run 非 success |
| W4-8 | carriers 只認「延後到 R＋數字」句型；症狀型待驗（QA-B U1～U7、理論洞、Windows 該機清單）不在任何計數器 | 設計邊界 | 某症狀型待驗項實際發生卻無人入帳（附 sid） |
| W4-9 | 未結列 fail 線＝98 列、warn 86；「0」由掌舵者定義而非機械強制 | 設計 | 未結列 >0 卻超過一個視窗無人察覺 |
| W4-10 | 07:49 nightly 為 `+nested` 剖面（R90 舊鍵鬆 6 格）；`+solo` 乾淨樹全綠由下一次 launchd 排程自動產出（機器時鐘、非待辦） | 量測邊界 | 排程 nightly 的 `失敗 stage` 非空 |

## 十二-6 掌舵者該機專屬清單（Windows；依範本〈🏁〉＝非再開事件；本節取代〈十-9〉(1) 的字樣）

1. repo 根 PowerShell：`git pull --ff-only`。成功＝看到 `[post-merge dispatcher] env.shared 同步：0 個問題` 或 `…env.shared 同步：已自動修復，備份＝.env.bak.<UTC戳>…`。只有 `Already up to date.`＝這次 git 沒跑 hook（已是最新），改跑 `python tools\lib\quota_policy.py --env-doctor` 看 `結論：0 個問題 ⇒ rc=0`。確有新 commit 拉進來卻完全沒有 `env.shared` 字樣 ⇒ `core.hooksPath` 沒指到 `tools/git-hooks`（R212 證據檔〈八-1b〉）。主控台若是 cp950 中文會亂碼，認 ASCII 片段 `[post-merge dispatcher] env.shared`、`.env.bak.`、`rc=0`。
2. 同〈十-9〉(2)～(5)：`tools\windows_smoke_local.ps1` 預期 `PASS=13 FAIL=0`；`python tools\dev_start.py`；`tools/lib/engine_resume_job.py` schtasks 分支；`python tools\lib\quota_burndown.py --status` 預期 rc=1。(2)(4)(5) 已由雲端 windows-latest 實跑，殘留只剩掌舵者實機特異性（cp950／Defender／排程帳號）。

## 十二-7 開了→收了

- Sonnet 鏡 2 支（mirrorA／mirrorB）皆收工：mirrorB 的 5 個複本＋3 條 `.venv` 符號連結已刪（保留 log）；mirrorA 的 scratchpad clone 已刪、主樹 `.venv` 完好、repo 零寫入。DEV-F01：暫存 git clone＋其 `.venv` 符號連結已先刪連結再刪目錄（主樹 `.venv` 完好）；無背景行程、無網路、未跑 `--pace`、未做任何 git 寫入。
- Docker Desktop：nightly 自開自收（`pgrep -f Docker.app` 空）。背景 Bash 1 條（nightly）已結束 rc=0。無 launchd／schtasks／Monitor／CronCreate 新增。
- 子代理任務書與報告備份：`~/.autosdd/r213_window4_scratch/`。

## 十二-8 結論（給掌舵者）

三問在 HEAD 成立且經本窗獨立重驗（含乾淨樹 nightly 五 stage PASS）；可自提示詞移除。殘留＝該機專屬清單（十二-6；非再開事件）與 P4 理論洞（十二-5 與〈十一-11〉；只登記）。
