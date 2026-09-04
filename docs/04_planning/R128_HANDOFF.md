# R128 交棒書（落地輪；技術債總清償循環令 v2 第三投）

- **輪籤**：R128（2026-09-04，Windows 11；下一個窗口＝mac）
- **輪型**：**落地輪**——掌舵者對 R127 呈報單七項逐項回覆「同意建議」，本輪把七項落款成
  程式碼與帳本狀態，外加一筆落地候選（`DEF-200-264` 接線）。
- **帳本**：未結列 **34 → 31**（結 4：`DEF-200-259`／`DEF-200-255`／`DEF-200-256`／
  `DEF-200-264`；新立 1：`DEF-200-265`，途中發現，見〈本輪方法〉第 4 點）。
  `--unresolved-count` 實跑見〈已驗證〉。
- **護欄層**：<!-- guard-total:R128 --> 行數 `92268→92268`（淨額 **+0**）。本輪一支
  `_FROZEN_GUARD_LINES` 成員檔都沒動、逐檔漂移 0 支 ⇒ **零重釘**（在零漂移的輪次追加重釘列，
  那一列自己就是本輪唯一的淨額來源）。款(11) streak 維持 0；款(10)／款(12) 皆未觸發。
- **commit／push／雲端 CI**：本檔刻意**不寫死** commit sha／push_rc／雲端結論。現查
  `git log -3 --oneline`、`gh run list --branch main --limit 6 --json headSha,name,status,conclusion`；
  本輪結案回覆已逐支列出。
- **體例**：不使用「延後到R／交給R／留給R／承接輪次：R」等前瞻輪號句型；所有數字皆本
  session 親跑。

## 本輪方法

1. 三包唯讀勘查（`model: sonnet`，每包 schema 化問題清單）分別查 `DEF-200-255`／
   `DEF-101-856`／`DEF-200-182` 的落地面。帳本編修、程式碼與結案全部由本單一窗口序列完成。
2. 🔴 **三包的結論全部經主控親驗才採用**，其中兩包的結論導致「不照裁決落地」——見下方
   〈兩筆沒有照裁決結案〉。第三包（`DEF-200-255`）的關鍵史料（R82 自動打開實驗撞線後退回）
   經現查該檔登記註解逐字確認。
3. 額度取數本輪三次降級（`meter-unreachable`／`stale-cache`／`expired-window`），每次把扇出
   硬上限收到 2 ⇒ 全程逐一 `Agent`、實際只派 3 包。
4. 跑完 ONBOARDING 表② 回填後查 `git status --short`，發現兩個本輪沒碰過的檔被改寫：
   `.perf_baseline.toml`（量測值自然重播種，照舊入庫）與
   `tests/fixtures/pgvector_real_ground_truth.json`（每次 seed 重生的隨機 UUID，單檔
   `--numstat` 實測 1000／1000）⇒ 後者立列 `DEF-200-265`。🔴 **本輪初稿把寫入者歸因給
   ONBOARDING 回填，經查 mtime 為錯**：真凶是本機 `AutoClaude_Nightly` 排程（22:30:01 啟動，
   兩檔寫入時刻 22:51:52／22:52:14 皆在其後，而回填遠晚於 22:52 才啟動）。現查
   `Get-ScheduledTask -TaskName AutoClaude_Nightly | Get-ScheduledTaskInfo`。逐節在
   `CrossPlatform_R128_Scan_Findings.md` §3-a。
5. **四方定點複審**（Architect／SD／SA／QA，`model: sonnet`，全程唯讀且明令禁跑 pytest）：
   一審結果 Architect `APPROVE_WITH_CONDITIONS`（1 blocking）／SD `APPROVE_WITH_CONDITIONS`
   （2 blocking）／SA `APPROVE`（0）／QA `APPROVE_WITH_CONDITIONS`（3 blocking）。六筆 blocking
   逐筆親驗後全數成立、全數修畢（逐筆對照見證據檔〈四方複審〉節）。🔴 主控在審查期間動了
   工作樹（搶修 Architect 那筆），違反〈並行派工防互踩檢查表〉第 3 條，代價與兩個附帶觀察
   記在 `CrossPlatform_R128_Scan_Findings.md` §2 第 10 點。

## 呈報單七項的落款結果

| 項 | 裁決 | 落地 | 帳本 |
|---|---|---|---|
| ① R121 呈報單檔頭 | 改 Adopted | 已落款；同輪查出一筆推薦的前提為假，就地加訂正註記並明文劃界落款範圍 | 非帳本列 |
| ② `DEF-200-259` | wontfix | 已落款；另把 `ADR-XPLAT-002` 三處**仍生效的祈使指示**由行號錨改符號名錨 | wontfix |
| ③ `DEF-200-182` ① | 判準家歸 `check_handoff_carriers.py` | **未實作**（原設計對自己的立案案例失明）；②親驗結案 | 仍 open |
| ④ `DEF-200-256` | 維持不修 | 已落款（登記面與「不會被執行」皆現查確認） | wontfix |
| ⑤ `DEF-200-255` | opt-in 終態 | 已落款；另在 `skip_group_policy.py` 政策自述劃出「設計上永久 opt-in」例外 | wontfix |
| ⑥ `DEF-101-736` 子項 | `560` wontfix 落款 | 已落款（該列另有三筆子項未完） | 仍 open |
| ⑦ `DEF-101-856` ⑥ | 本機 Docker 算 staging | **未結案**（裁決的事實前提經現查不成立） | 仍 open |

### 🔴 兩筆沒有照裁決結案（理由都是「裁決依據的事實經現查不成立」）

- **`DEF-200-182` ①**：R121 呈報單〈方向 A〉把判準寫成「push 範圍含 `AutoClaude/` 或
  `AISDLC_SDD/` 時，〈驗證〉節必須列出那兩套閘門」。而立案案例 `ea304b2` 的 push 範圍**恰好
  不含**那兩個目錄（親驗 `git diff --name-only ba4599f ea304b2` 的子專案命中數 `count=0`）
  ⇒ 照該設計做出來的鎖對它自己的立案案例一次都不會出聲。真正的缺口是〈驗證〉節沒有交代
  某些 leg 為何沒跑，讀者因此分辨不出「路由未觸發」與「被繞過」。
- **`DEF-101-856` ⑥**：裁決理由是「功能正確性完全測得到」，但那三支測試的函式體現在是一句
  `pytest.skip`（其中一支末尾是 `assert True`），且 staging 的機械定義是「≥1000 列真實
  BGE-M3 向量」，而本機容器唯讀查得 `knowledge_entries` 共 100 列、真實 BGE-M3 為 0 列。
  ⇒ 讓它們跑起來等於寫測試實作，不是設環境變數。

**②（Windows 側查證）本輪親驗結案**：`pre-push` 設定 `run_autoclaude`／`run_sdd` 的那兩行純依
路徑路由 ⇒ 那兩個 leg 在該次 push 是**合法不觸發**，不是被繞過。連帶推翻 R121 對 ② 的
`closed-by-decision` 理由，已在該檔就地加訂正註記。

## 已驗證（本 session 實測；rc 皆自成一句讀取）

- 三本帳（收輪當下的最終值，非落款途中的中途值）：`check_defect_log_crossref.py` 不帶參數
  rc=0（**194** 筆有效狀態紀錄、逐列 ≤700 bytes、具名治理文件 **102** 份皆已登記）；
  `--unresolved-count` rc=0、未結列數 **31**／全部 **194** 列；`check_archive_required.py` rc=0；
  `check_handoff_carriers.py` rc=0。（🔴 本段初稿引用了落款**之前**的 193／100，且與同句的
  194 自相矛盾——QA 鏡實查抓到，現值為本輪最後一次重跑所得。）
- `DEF-200-264` 紅綠自證（複審修復後的最終值）：`pytest
  tests/integration/test_def_200_205_production_wiring.py -q -k Def200264` → `4 passed,
  22 deselected`；**兩次突變各自驗紅**——拔掉 `main.py` 兩個 kwarg → `2 failed, 1 passed`
  （訊息逐字「state 檔大小沒進到預估（收到 None）」）；把 `DualStateRepository.state_bytes`
  改名 → `1 failed, 3 passed`（只中新那一支）。還原後
  `pytest tests/integration/test_def_200_205_production_wiring.py tests/test_r100_boot_self_check.py -q`
  → `66 passed`。兩次突變還原皆走 `Edit` 工具就地改回，未用任何毀滅性 git 指令。
- lint：`ruff check` 四支改動檔（不帶 `--config`）→ `All checks passed!`；
  `AutoClaude/tools/check_loc_budget.py --json` rc=0（四類 violations 皆空）。
- 守衛線：`--print-guard-lines` rc=0、印出「淨額 92268→92268 (+0)」與「逐檔漂移 0 支」。
- 帳本列 bytes 逐列實量（上限 700）：`DEF-101-736` 674／`DEF-101-856` 669／`DEF-200-182` 596／
  `DEF-200-255` 692／`DEF-200-256` 653／`DEF-200-259` 565。
- ONBOARDING 表①②：以乾淨 venv `autoclaude_cleanvenv_20260904`（`pgextras=absent`）
  `--write --with-slow` 回填**兩次**（第二次因複審修復又新增一支測試）。最終值：
  `loc-baseline-live` `total=17306`、`rootunit-baseline-live` `tests=3895`、Windows 欄
  `autoclaude-pytest-snapshot` `4617 passed／175 skipped`、三軌 ci-gate `1478／1746／352`；
  `--check` 與 `--check-snapshot` 皆 rc=0。
- 根層全套：`python tools/run_root_unittests.py` 背景執行、親讀 log 尾端 →
  `Ran 3932 tests in 802.800s`、`OK (skipped=42)`、`full_rc=0`。
  🔴 **本輪跑了三次全套**：第一次紅 4 筆（全部同源＝LOC 基線 stale，複審修復讓行數又長）、
  第二次因文件變動而主動 `TaskStop`、第三次即上列綠燈。

## 還沒做（不塗綠；每筆帶現查指令）

1. **U9（四支 `[ROOT-TOOLS]` 檔舊尺債）真拆尚未執行**：`quota_gate.py`／`quota_meter.py` 的
   docstring 敘事可搬，`hook_wiring.py` 仍未有共用模組可抽。現查
   `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`。
   <!-- absent-if: _ROOT_TOOLS_OLD_SCALE_DEBT_RESOLVED = True -->
2. **`DEF-200-182` ① 的判準尚未實作**，且要重新拍板後才動工（呈報單第 1 項）。分母＝
   `tools/git-hooks/pre-push` 的六個 leg，其中兩個依路徑路由。現查
   `Select-String -Path tools/git-hooks/pre-push -Pattern "run_autoclaude=1|run_sdd=1"`。
   落地時的約定符號名見呈報單。
   <!-- absent-if: def leg_coverage_problems -->
3. **`DEF-101-856` ⑥ 的兩條路都改動護欄語意**（呈報單第 2 項）：(a) 用真實 BGE-M3 重新 seed
   ≥1000 列語料；(b) 放寬平台綁定欠債表探針對語料真實性的判準。現查
   `docker exec autoclaude_pg psql` 唯讀查 `knowledge_entries` 的 bge-m3 列數。
4. **剩餘 31 筆未結列**（現查 `python tools/check_defect_log_crossref.py --unresolved-count`）：
   - mac 真機或雙平台：`DEF-200-252`／`DEF-101-675`／`DEF-200-231`（mac 側 User 層值）／`DEF-200-165`。
   - 落地候選（裁決已在、只差實作）：`DEF-200-124`（M，prose 分桶棘輪；需四方）、
     `DEF-200-118`（M，PRD 層先定門檻）、`DEF-101-938`（M，shellcheck 接線；🔴 勘查已完成、
     座標與代價見 `CrossPlatform_R128_Scan_Findings.md` §2 第 12 點，但**接線層級待拍板**
     ——見呈報單第 3 項；🔴 其裁決卡指向的 `CrossPlatform_R121_Debt_Closure.md §DEF-101-938`
     **不存在**，設計權威出處只有裁決卡那段文字本身，動工時不要去找那個節）、
     `DEF-200-242`（M，先量 `quota_burn.jsonl` 翻頁後第一拍扇出）、`DEF-200-253`（S；🔴 與
     `DEF-200-183` 生產者側 pgextras 軸綁定，183 未修前 re-key 會讓 AutoClaude 天花板整批
     退回 advisory）、`DEF-200-265`（S，二擇一後接線）。
   - 多子項／結構性：`DEF-200-207`（U1~U4 四方審查）、`DEF-200-197`／`DEF-200-198`／
     `DEF-200-199`／`DEF-200-203`／`DEF-200-193`（配速修憲 Adopted 待落地批）、
     `DEF-101-736`（殘三子項）／`DEF-101-887`／`DEF-101-796`／`DEF-101-974`／`DEF-101-981`／
     `DEF-200-086`／`DEF-200-129`／`DEF-200-134`／`DEF-200-183`／`DEF-200-188`／`DEF-200-246`／
     `DEF-200-251`／`DEF-200-234`。
5. **側軌現況**（不計入分母）：外部阻塞軌 6 筆（`DEF-101-518`／`DEF-101-693`／`DEF-101-703`／
   `DEF-200-075`／`DEF-200-174`／`DEF-200-186`）、結構性長債軌 7 筆（`DEF-101-018`／
   `DEF-101-398`／`DEF-101-701`／`DEF-101-702`／`DEF-101-886`／`DEF-101-960`／`DEF-101-980`）。
   本輪照原樣承接、未逐筆複查；帳本閘門對複查日未出聲（rc=0）⇒ 尚在容忍窗內。現查
   `python tools/check_defect_log_crossref.py` 輸出末兩行。

## 呈報單（需掌舵者拍板；白話分析見本輪結案回覆）

1. **`DEF-200-182` ① 判準的新設計方向**：原方向 A 對立案案例失明（理由見上）。建議改判
   「交接載體的〈驗證〉節必須讓『哪些 leg 沒跑、為什麼沒跑』可判別」，家仍在
   `check_handoff_carriers.py`；落地時的判準函式名以〈還沒做〉第 2 點的 absent-if 錨為約定
   （該符號尚不存在，故錨裡是純文字、刻意不加反引號）。
   需拍板的是：判準要不要吃「變更範圍」這個新輸入面（吃了才知道該觸發哪些 leg，但也擴大
   假紅面），以及只判最新一份交接載體還是全部。
2. **`DEF-101-856` ⑥ 二擇一**：(a) 用真實 BGE-M3 重新 seed ≥1000 列語料，讓現行判準原封不動；
   (b) 放寬探針對語料真實性的判準，讓本機 Docker 算等價替代。(b) 較省事但會削弱一道現在
   有牙的鎖；(a) 較貴但不動判準。若兩者皆不採，第三條路是把本列遷外部阻塞軌
   （上一輪呈報單原文即列此為 fallback）。
3. **`DEF-101-938` 接線層級（裁決卡沒填的空格）**：該筆已有裁決（方向 A：shellcheck 接進
   `pre-push` root-infra leg，rc=2 載具缺席出聲不擋、rc=1 有差異才擋），但**沒說接快層還是
   慢層**。快層＝任何 push 都跑（覆蓋完整；缺 shellcheck／docker 的機器每次印 warn，本機實測
   `Get-Command shellcheck` 查無）；慢層＝只在根層檔變更時跑（噪音少；「只改子專案 `.sh`」的
   push 會漏）。**第三個選項**（本輪勘查提出、尚未拍板）：接快層但比照 CI 的 `paths:` 加一個
   路徑旗標，只在 push 範圍含 `.sh` 或 git-hooks 目錄時才跑——與 `run_autoclaude`／`run_sdd`
   的既有路由機制同構，同時解掉噪音與覆蓋的矛盾。勘查另查明：掃描面風險已由工具層消除
   （活躍 `.sh` 僅 18 支），新判準宜併入既有 `test_root_infra_parity.py` 以免付守衛線淨額。

## 證據位置

- 七項落款取證＋兩筆「前提不成立」的逐節證據＋`DEF-200-264` 紅綠自證：
  `docs/06_quality/CrossPlatform_R128_Debt_Closure.md`。
- 護欄層零重釘理由＋本輪動到的檔清單＋途中發現九點：
  `docs/06_quality/CrossPlatform_R128_Scan_Findings.md`。
- R121 呈報單的落款與訂正註記：`docs/04_planning/AutoSDD_Adjudication_Packet_R121.md`
  （檔頭 ＋ `§DEF-200-182` 的裁後動作之後）。
- 乾淨 venv：`C:\Users\wuwei\AppData\Local\Temp\autoclaude_cleanvenv_20260904`（表② 回填用）。

## 下一步（下一個窗口＝mac）

- mac 專屬列（`DEF-200-252`／`DEF-101-675`／`DEF-200-231` mac 側）在 mac 真機結案；Windows
  實測值不外推。
- 款(11) streak 為 0 ⇒ 可承受一輪正淨額（連續上升第 1 輪）。🔴 真表測試不吃回歸鎖軌分流
  （上一輪 Scan_Findings 已坐實），要抵銷就搬尚未搬過的鎖檔散文
  （`test_platform_neutral_paths.py`／`test_check_defect_log_crossref.py`）。
- **落款窗口的職責不只是把裁決抄進帳本**：本輪七項裡有兩項的事實前提在落款當回合就查出
  不成立。動筆前先重驗裁決依據，包括帳本自己「已結案」的宣告與呈報單引用的座標。
- 🔴 **降帳本的策略已無「純結案」這條路**：本輪對剩餘 31 筆做了全量唯讀快篩，
  `closeable-now`（重跑一個指令即可結案）**一筆都沒有**（逐筆分類與三筆疑點見
  `CrossPlatform_R128_Scan_Findings.md` §2 第 14 點）。⇒ 下一輪的有效槓桿只有兩個：
  **真的修**（建議序：`DEF-200-265` 範圍最小方案最清楚／`DEF-200-183` 大半已在 R123 完成、
  剩生產者側收尾／`DEF-200-129` 若查證屬實可能直接掉出 needs-dev）與**批量拍板**
  （本輪呈報單三項 ＋ 帳本裡其餘 `needs-decision` 各筆）。
- 🔴 **背景長任務的 `completed` 通知不是憑證**：本輪實測它先於行程真正結束抵達，當下 log 連
  測試摘要都還沒寫（半套輸出裡沒有 `FAILED` 字樣，看起來與全綠難以分辨）。憑證是 log 尾端
  同時出現 `Ran N tests` ＋ `OK`／`FAILED` ＋ `full_rc=`；缺一就用**精確 PID** 的 until-loop
  等它。逐節見 `CrossPlatform_R128_Scan_Findings.md` §2 第 13 點。

## 禁止事項

- 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`、push 不帶 `AUTOSDD_NET_RATCHET_OFF`。
- 不准把〈還沒做〉④ 的 30 筆順手改成已結——皆逐筆核實仍需動工、裁決或 mac 真機。
- 不准同時派多個 agent 平行編修帳本或同一鎖持有面（鐵律七檢查表）。
- 全套 `tools/run_root_unittests.py` 一律親讀 log 尾端 `rc=`；push 一律背景執行並讀 `push_rc=`；
  逾時（rc=143）先 `git fetch` ＋ `git log origin/main..HEAD` 判斷是否已送達。
- ONBOARDING 表② 回填一律乾淨 venv，禁 `--allow-pg-extras`。
- 🔴 落款一份裁決文件時，不准把「整體採用」寫成「每條理由都經覆核」——本輪親踩，見
  `CrossPlatform_R128_Scan_Findings.md` §2 第 7 點。
