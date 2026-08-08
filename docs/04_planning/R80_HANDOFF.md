# R80 交棒書（跨平台輪，Windows 11 真機）

> 體例沿用 R78／R79：**凡述及「尚未做／還缺／已推送／已通過」這類狀態，一律附現查指令，不寫快照結論**
> （機械物：`tools/tests/test_doc_loc_baseline_freshness_r60.py::TestR78HandoffClaimsCarryLiveCommands`）。
> 本檔內出現的每一個數字都是「取得它的那個時點」的量測值，不是常數。
>
> 🔴 **成書時點**：本檔由 R80 **二審收斂包**（本輪最後一個執行者）在**單人窗口**寫成——
> 無任何 agent 在跑，所有 rc 可歸因。這是 R79 交棒書做不到的一件事（該檔 §1〜§3 寫於複審之前、
> 其後還有兩包改樹而沒有人回填），本輪刻意避開。**但這不讓本檔的數字變成常數**：R81 讀到它時，
> 舵手已經 commit／push 過，樹已經不同。

---

## §0 R81 開場必讀（照順序做，不要跳）

1. 🔴 **先處理缺陷帳本未結列——它已經越過 warn 線。**
   ```powershell
   $r='D:\CursorProject\AISDCL_Agent'; $p="$r\.venv\Scripts\python.exe"
   & $p "$r\tools\check_defect_log_crossref.py" --unresolved-count
   & $p "$r\tools\archive_defect_log.py" --check
   ```
   收輪當下的實測是 **88／warn 86／fail 98**（距 fail 線 10 筆）。
   🔴 **歸檔不會降低這個數**——工具自己每次都印這句：未結列在結構上不可歸檔，
   它們是主檔體積的**不可壓縮地板**。唯一出路是**結列**或**改派具名承接者**。
   R80 已把「零成本可結」那幾筆挑掉了（見 `improving_104` §1 Q5 結論），
   剩下的每一筆都需要真的做事或真的拍板。

2. **查雲端**（R73／R71 各付過一次「收輪不查雲端」的代價；R79 起訂為必做）。
   ```powershell
   gh run list --limit 12 --json workflowName,event,headSha,conclusion,status
   ```
   🔴 **R80 全程沒有雲端結論可用**：開場實測最近 3 個 commit 全 `failure`，但
   `gh run view <id> --json jobs` 回 `steps: 0` ⇒ **Actions 帳務停擺，不是程式碼紅**。
   R81 開場請先確認帳務是否恢復；沒恢復就沿用 R80 的做法（act ＋ Docker 本機驗證），
   並且**不得**把「本機／act 全綠」寫成「CI 全綠」。

3. **覆核本檔 §4 那份待辦**，逐項跑它自己帶的現查指令。**不要採信本檔任何「已修」字樣**
   （同 Nightly 取證紀律 #17 的 zero-trust 雙向：對上一輪的宣稱也要 zero-trust）。

4. **四方複審 R80 已跑兩審，R81 不需要補跑**——但要覆核二審收斂包（＝本檔作者）
   做的那五筆，因為**那一批修復沒有再被第三方看過**（M3「作者自證不計分」）。
   結論與逐筆處置的轉錄：
   ```powershell
   Get-Item "$r\docs\06_quality\CrossPlatform_R80_Review.md" | Select-Object Name,Length,LastWriteTime
   ```
   <!-- handoff-claim-verified: 四方複審是 agent 派工，全 repo 沒有任何會落 rc 的管道可現查「它跑過與否」；本檔只補得到結論的轉錄 -->

5. **重跑歸因，不要引用任何百分比**（先驗量測器符號，再跑歸因——順序是判準的一部分）：
   ```powershell
   & $p "$r\tools\probe\audit_session.py" --selftest
   & $p "$r\tools\probe\misstep_attribution.py"
   ```

---

## §1 收輪實測狀態（只給指令，不給 rc 快照）

**十三道閘門的現查指令**（本收斂包在單人窗口逐一實跑過；R81 請自己重跑一次）：

```powershell
$r='D:\CursorProject\AISDCL_Agent'; $p="$r\.venv\Scripts\python.exe"
$env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'
& $p "$r\tools\run_root_unittests.py"          ; "rootunit=$LASTEXITCODE"
& $p "$r\AutoClaude\tools\check_loc_budget.py" ; "loc=$LASTEXITCODE"
& $p "$r\tools\check_defect_log_crossref.py"   ; "xref=$LASTEXITCODE"
& $p "$r\tools\archive_defect_log.py" --check  ; "arch=$LASTEXITCODE"
& $p "$r\tools\check_script_parity.py"         ; "parity=$LASTEXITCODE"
& $p "$r\tools\check_wrapper_thinness.py"      ; "thin=$LASTEXITCODE"
& $p "$r\tools\check_hooks_liveness.py"        ; "hooks=$LASTEXITCODE"
& $p "$r\tools\check_pytest_baseline_sites.py" ; "sites=$LASTEXITCODE"
& $p "$r\tools\check_gha_action_versions.py"   ; "gha=$LASTEXITCODE"
& $p "$r\tools\check_ntfs_paths.py"            ; "ntfs=$LASTEXITCODE"
& $p "$r\tools\check_scheduled_task_drift.py"  ; "sched=$LASTEXITCODE"
& $p "$r\tools\check_defect_log_crossref.py" --unresolved-count
python -m ruff check "$r\tools" "$r\.claude\hooks" ; "ruff=$LASTEXITCODE"
```

🔴 **讀 rc 不要接管線**（pwsh 7.x 上截斷型管線會**保留前一個值**＝真紅讀成綠）。
要看輸出就 `*> 檔案` 再 `Get-Content`。

🔴 **算行數／搜尋一律不經 shell**：`Get-Content | Measure-Object -Line` 對 CJK 檔給假數字，
本輪踩過兩次。用 Read／Grep 工具，或 `python -c` 讀 utf-8。

### 本輪二審收斂包落地的機械物（附「故意弄壞→轉紅→還原→轉綠」的注入自證）

| 缺陷 | 機械物 | 現查／注入指令 |
|---|---|---|
| `NEW-SA2-01`＝`QA2-N2` 文件側引用的護欄層累積總量無人守（三處全錯撐過一整輪） | `test_adr_xplat001_c1c2_lock.py` 的 `doc_guard_total_problems()`（四款：`[未登記]`／`[形態不符]`／`[總量不符]`／`[淨額不符]`），掃描面＝計畫書＋掃描發現文件，以 `guard-total:<輪號>` 標記分「現行宣稱」與「史料」 | `& $p -m unittest test_adr_xplat001_c1c2_lock.TestGuardLayerRatchet`（於 `tools/tests/`） |

**注入自證的形狀**：磁碟上把真文件的總量改錯一位 → rc=1 且訊息指名檔案與行號 →
改回 → rc=0；另有四格在測試內以真文件內容做記憶體內注入（總量錯／算術錯／拿掉標記／
只留舊輪號），一格合成語料證明它**不是恆紅**。

---

## §2 掌舵者訴求逐條的本輪答案

🔴 **本節只給指針，不複製結論**——十二條（Q1~Q6／S1~S3／P7／a／b）的答案**逐條**寫在
[`AutoSDD_improving_104.md`](AutoSDD_improving_104.md) §1 那張表的 `↳ 結論` 列裡，
**那是唯一的家**。R80 二審 `NEW-SA2-02` 抓到的正是「§1 標題寫著不得漏答、12 條裡只有 5 條
有結論」，本輪已補齊七條；在本檔再抄一份就是替它製造第二個會漂移的家。

一句話總表（**判定，不含數字**；數字一律去 §1 現跑）：

| 訴求 | 本輪判定 |
|---|---|
| Q1 跨平台零相容缺陷 | ❌ 未達成——判準只量得到「有沒有人在守」；mac 側**未量** |
| Q2 架構簡潔、淨減法輪 | ❌ 未達成——本輪重釘三次，走的是款(9) 的**讓步條款** |
| Q3 兩平台不互相落差 | ❌ 未達成——對等性只驗到存在性與具名鎖，一般行為等價仍無判準 |
| Q4 Windows 低級錯誤根因 | ⚠️ **根因已改判**（最大桶＝宣稱先於查證），但未「徹底解決」——最大桶今天零機械物 |
| Q5 挖深＋清技術債 | ❌ 未達成（新增列 > 結案列）；方向由「相反」轉為「下降」 |
| Q6 成熟度 M1~M6 | ❌ **0 條達標**；門檻＝六條全達標且**連續三輪**，其中至少一輪是別人來查 |
| S1 context 不要爆 | ❌ 阻斷臂已修好（此前命中面為 0），但「壓縮實際發生」仍只是出聲 |
| S2 額度 reset 後續跑 | ⚠️ 前四段成立、**第五段的觸發條件設計錯了**（救 session，而死的是扇出） |
| S3 pytest skipped 歸零 | ❌ 未達成——本輪交付的是**治理**不是解決 |
| P7 哨兵彈視窗 | ✅ 類級修法＋掃描器已落地；⚠️ 射程只有根層 settings |
| a 額度水位用 % | ❌ 零交付（分母的口徑未定，單點校準解不開兩個未知數） |
| b 80% 少派／95% 停止 | ❌ 零交付（三方設計完成，ADR 合成與實作兩階段皆在額度上限陣亡） |

---

## §3 本輪最重要的一般化規則（三條，每條都有本輪實例）

1. 🔴 **一個數字只要住進「人會讀的散文」，就必須有判準看得到那份散文——否則它一定會過期，而且不會有人發現。**
   本輪實例：護欄層累積淨額在三份文件裡有三個說法，其中一個連算術都不對（1528＋595 寫成 2029），
   撐過一整輪零訊號。既有的款(4)`[未對帳]` 咬得到稽核痕跡，咬不到 `.md`。
   ⇒ 落地物是 `doc_guard_total_problems()`，但**它的射程只有那一個數字**；
   其餘文件宣稱今天仍是零觀測者（見 §4）。

2. 🔴 **訂正註記不得複述被推翻的原句——包括「我不會複述它」這句話本身也要兌現。**
   R73 立過「訂正註記逐字引述假話＝製造新假話」，R79 補過它的掃描器版本
   （「在被機械判讀的面上，解釋 X 的字面等於又用了一次 X」）。
   本輪 `NEW-ARCH-R80B-06` 是第三種形態：註記寫著「故不複述它」，**緊接四行把整句抄了出來**。
   ⇒ 一般化：寫訂正時先問「我是把假話搬到新的地方，還是真的只留了一個指標？」
   正確做法是**原句留在它的立案現場當史料**（本輪＝ADR-XPLAT-004 §2.6），別處只留指標。

3. 🔴 **「已修」與「射程涵蓋全部」是兩件事，而文件天生會把前者寫成後者。**
   本輪實例：exec form 轉換只做了根層那一份 settings（AutoClaude 那 6 條仍是 shell form），
   而文件一度寫成通則；`hook_wiring.py` 檔頭的消費者清單**在落地當輪就已過期**，
   且同一個支數在三個家有兩個值。
   ⇒ 一般化：**凡是「有幾個／哪幾個」都是量測值不是常數**，一律寫現查指令；
   凡是部分完成，射程要有一個**會轉紅的登記**（本輪＝`SHELL_FORM_CENSUS` 相等棘輪）。

---

## §4 交給 R81 的待辦（每一項都附現查指令）

### 4.1 🔴 三件必須先做的（順序有理由）

1. **未結列已越過 warn 線，尚未處理。**
   ```powershell
   & $p "$r\tools\check_defect_log_crossref.py" --unresolved-count
   ```
   收輪實測 88／warn 86／fail 98。撞 fail 線時能做的事跟現在一樣多，只是選擇更少。

2. **`MIN_TESTS` 仍釘在舊值、本輪刻意沒有重釘**（`NEW-SA2-07`）。
   ```powershell
   & $p "$r\tools\run_root_unittests.py"   # 末段印「發現 N 個測試（下限 M）」，N−M 就是可靜默蒸發的支數
   ```
   🔴 **收尾者的判斷與理由（照實寫，供 R81 覆核而不是照單全收）**：
   重釘判準本身**今天是滿足的**（四方二審全部 `APPROVE_WITH_CONDITIONS`、blocking 全收斂、
   本包是本輪最後一個工作者、單人窗口），方向也是**收緊**不是放寬——
   所以「不准調高門檻」那條禁令**不適用**（它禁的是放寬）。
   **仍然沒做的理由是機械耦合**：`ONBOARDING.md` §7 表① 的 `rootunit-baseline-live:` 格
   與 `MIN_TESTS` 由 `test_root_unittest_cell_agrees_with_min_tests_ssot` 綁死，
   重釘就**必須**同一次跑 `sync_onboarding_baselines.py --write`——而本收斂包的任務書
   逐字禁止跑它（那是舵手 push 前的最後一個動作）。⇒ 兩條規則直接對衝，本包選擇
   **不越界、留紅在檯面上**而不是偷偷做掉一半。
   R81（或舵手在 push 前那一步）要做的是**同一次變更**內兩件事一起：
   ```powershell
   # ①把 MIN_TESTS 改成 runner 當場印出的計數（直接填入，零加減推算）
   # ②同一次變更同步 ONBOARDING 那一格：
   & $p "$r\tools\sync_onboarding_baselines.py" --write
   & $p "$r\tools\run_root_unittests.py"   ; "rootunit=$LASTEXITCODE"
   ```

3. **act 那一步仍紅，本輪未修**（唯一已知仍紅的項目）。
   ```powershell
   & $p "$r\tools\check_defect_log_crossref.py" --unresolved-count   # 找 DEF-101-975
   ```
   內容＝ONBOARDING §7 表② 的 presumed-stale 觸發器，兩平台一致會紅。
   回填是 **repo 外**乾淨 venv（只裝 `.[dev,notifications]`）跑
   `sync_onboarding_baselines.py --write --with-slow`，且**必須是 push 前最後一個動作**。
   🔴 **不要走 `--allow-pg-extras`**——那會把表② 宣告的「出廠環境」語意靜默換掉（R79 同型判例）。

### 4.2 二審 non-blocking：本輪未做的那些

🔴 **誠實劃界（本節最重要的一句）**：二審 non-blocking 約 **20 筆**，
本收斂包收到的任務書裡**只有 6 筆的內容**（`NEW-SA2-04`／`NEW-SA2-07`／`NEW-SA2-08`／
`NEW-ARCH-R80B-03`／`-06`／`-07`），其中 5 筆已當輪做掉、1 筆（`NEW-SA2-07`）見 §4.1-2。
**其餘約 14 筆的標題與內容，收尾者從頭到尾沒有拿到過，repo 內也沒有任何載體可現查。**
⇒ 本檔**不列**一份看起來完整、實際憑空補齊的清單——那正是本輪在治的病。
R81 若要覆核它們，唯一的來源是二審那一輪 session 的交件回報。
```powershell
Get-Item "$r\docs\06_quality\CrossPlatform_R80_Review.md" | Select-Object Name,Length
```
<!-- handoff-claim-verified: 二審 non-blocking 的 finding 原件只存在於當輪 session 交件回報，派工不落 rc、repo 內零載體 -->

### 4.3 帳本裡明文承接 R81 的未結列（現查，不抄清單）

```powershell
& $p "$r\tools\check_defect_log_crossref.py" --unresolved-count
Select-String -Path "$r\docs\06_quality\AutoSDD_Defect_Log.md" -Pattern 'R81' -Encoding utf8
```
其中**方向性最強**的幾類（每一類都用上面那條指令查出當下的 ID，本檔不寫死清單）：
- **mac／POSIX 落差**（包 F 那一族）：Linux 容器永遠是 GNU coreutils，掃不到不等於 BSD 跑得過。
- **exec form 的射程**：`AutoClaude/.claude/settings.json` 的 6 條仍是 shell form。
  🔴 **R81 已處置**（`DEF-101-967` 結案）：該檔轉成 12 條 exec form、`SHELL_FORM_CENSUS` 兩格皆 0。
  **剩餘面**＝形態判準 A~F 與載具存在性判準的掃描面仍只有根檔（見 `CLAUDE.md`〈鐵律一之二〉末段誠實劃界）。
- **skip 的兩半**：`untagged` 那一群補一句標籤就結案；`platform` 那一群的目標**不是 0**，
  而是「互補剖面上真的有人跑到」——而 `AutoClaude/tests@linux+pg+solo` 至今沒有人量過。
- **對等性的行為面**（掃描 S8-05，**未落地**）：`tools/check_script_parity.py` 驗的是「存在性＋位元組釘選＋
  幾道具名鎖」，**不驗 13 對 `.sh`／`.ps1` 的一般行為等價**。
  🔴 **R81 已處置（本列的「未落地」是 R80 收輪狀態，非今日狀態）**：`tools/lib/script_interface_parity.py` 落地，
  補的是**可觀察介面**的表面集合比對（退出碼／外部執行檔／git 子指令），判準形狀＝與凍結基準**雙向相等**
  （新分歧紅、既有分歧修好卻沒除帳也紅）。**射程要照著讀，別當成它不是的東西**：行為等價不可判定（停機問題），
  該模組明文**不宣稱**驗行為等價；同碼不同條件、順序、訊息文字、動態構造的指令名一律抓不到。
  另外那 13 對裡**只有 3 對**是真的兩份獨立實作（`_BASELINE`／`_SCOPE_FLOOR` 現查皆為 3），
  其餘已收斂成「薄殼＋Python 單核心」⇒ 那些對根本沒有第二份實作可比，由 thinness hash 釘選守。
  ```powershell
  & $p "$r\tools\check_script_parity.py"      # 讀它印出的鎖清單，那就是它真正涵蓋的範圍
  Select-String -Path "$r\docs\06_quality\CrossPlatform_R80_Scan_Findings.md" -Pattern 'S8-05' -Encoding utf8
  ```
- **訴求 a／b**（額度用 %、80% 少派／95% 停止）：本輪零交付，唯一載體是帳本列與 `improving_104` §1。

### 4.4 需舵手拍板、agent 不得代決（沿用 R79，本輪仍未拍板）

```powershell
Select-String -Path "$r\docs\04_planning\R79_HANDOFF.md" -Pattern '4.4' -Encoding utf8
```
三筆：Windows smoke 排程退場 vs 降頻／四支子專案 hook 是否橋進根層／UEP 末階 PM signoff。
🔴 第三筆有具體阻塞：`ADR-XPLAT-002` §8.1 的 signoff 回執表**現查仍是空表**
（`Select-String -Path "$r\docs\04_planning\ADR\ADR-XPLAT-002-platform-surface-reduction.md" -Pattern '尚無回執' -Encoding utf8`），
而 M1 的 UEP 那一半以它為門檻 ⇒ **M1 的達標條件不在工程側**。

---

## §5 禁止事項

- ❌ **不准為了讓數字好看而調高任何門檻／棘輪／體積上限。合法出口有兩條**：
  ①同一次變更內刪等量以上的行（真淨減）；②走款(9)`[未附刪除清單]` 的**登記手續**
  （標 `[非淨減法輪]`＋指名逐檔清單的家）。②**不是及格線，是讓步條款**——走 ② 的輪次 Q2 一律判未達成。
  （🔴 R80 二審 `NEW-SA2-08`：R79 版寫「只有一條」，與同輪落地的款(9) 直接衝突。）
- ❌ **不准 `--no-verify`／`AUTOCLAUDE_SKIP_HOOKS=1`／跳過或註解掉失敗測試。**
- ❌ **不准把「已通過／已驗證／零損失」寫進任何文件**，除非同一則回覆貼得出當回合真跑的輸出。
- ❌ **不准在 Windows 用 Bash 工具**（PreToolUse hook 會擋）；不准裸 `cd`／`Set-Location` 相對路徑；
  **讀 rc 不接管線**；**算行數不經 shell**。
- ❌ **不准把本檔任何數字當常數引用。** 本檔刻意只給指令。
- ❌ **不准在多 agent 並行期間宣稱「全套閘門 rc=0」**——那個 rc 是別人鍵盤的函數。
- ❌ **不准以「act／Docker 本機全綠」代替 mac 真機結論**（Linux 綠不蘊含 mac 綠）。
- ❌ **不准以「閘門全綠」代替複審**（R75 實證：12 筆 blocking 有 8 筆是閘門自己沒有鑑別力）。

---

## §6 本輪自身的失誤紀錄（誠信擔保，不准空著）

二審收斂包（本檔作者）當回合實際犯下、並被自己的閘門或自查抓到的：

1. **新判準的第一版被自己的注入測試抓到射程太寬。**
   `guard-total:` 標記的比對式沒有前綴保護，於是注入測試把標記改寫成 `was-guard-total:R80`
   之後**仍然命中** ⇒ 「拿掉標記應該轉紅」那一格假綠。修法是加負向後查
   （前面不得是字元或連字號）。⇒ 一般化：**注入測試的價值就在它會抓到作者自己**，
   而這一次它真的抓到了；如果我只寫綠側對照組，這個縫會原封不動上線。

2. **一次順手的註解訂正打亂了已經收斂的重釘數字，來回三次才收斂。**
   我在重釘 `_FROZEN_GUARD_LINES` 之後才去修 `test_context_budget_guard.py` 的檔頭註解
   （`NEW-ARCH-R80B-07` 的第三個家），那支檔在護欄層掃描面內 ⇒ 總量從 65387 →65389 →65390
   連動改了三輪，逐次要重算 sha 與三份文件的數字。**正確順序是「先把所有會動到護欄層的編輯做完，
   最後才重釘一次」**——這正是本 repo 對 `MIN_TESTS` 早就寫下的紀律（重釘一律由收尾者
   在所有改動停工後做一次），我知道那條規則，卻在另一個棘輪上重犯。

3. **開場第一個工具呼叫就用了 Bash 工具**（被 PreToolUse hook 當場攔下，零副作用）。
   鐵律一在 session 開場就載入過，我仍然踩了——這是它**必須是機械物而不是自律**的又一次實證。
   R79 收斂包記過同一筆，本輪原樣復發。

4. **帳本新列第一版超出單列 bytes 上限兩次**（766 → 705 → 698，上限 700）。
   成因與 R79 收斂包記載的完全相同：把「當回合查證」的細節寫進了本該是**索引**的帳本列。
   兩次才收斂，代表我沒有在第一次被擋下之後就改變寫法，只是逐字砍。

5. **交棒書第一版引用了一個本輪剛被刪掉的符號**（`幽靈符號鎖` 當場抓下）。
   我寫「對等性的行為面是空清單」時，引用的是那份名冊常數的名字——而**本輪的架構減法包
   已經把它整個刪掉了**（它印「0 對」正是刪它的理由）。⇒ 我把一個「已被修掉的證據」
   寫成了「現況」。諷刺點：那一格談的正是**宣稱與實作對不上**。
   一般化：**談論某個缺陷時引用的證據，本身也可能已經被同一輪修掉了**——
   寫進文件前先現查一次。

6. **AutoClaude 那一棵的 pytest（M6 量測）與我的文件編輯有時間重疊。**
   雖然那次量測讀的是 AutoClaude 自己的 skip 標籤、與我改的 `docs/` 與根層 `tools/` 結構上無關，
   但**它不是在嚴格單人窗口取得的**，照本 repo 的紀律必須標出來。
   十三道閘門的 rc 則全部在**完全單人**的窗口取得。

---

## §7 取證邊界（誠實劃界）

- 🔴 **mac 真機零覆蓋。** 本輪全部量測都在 Windows 11 真機取得（工具側＝pwsh 7.x Core；
  凡 PS 5.1 語意的標的一律顯式 `powershell.exe -NoProfile` 外呼）。
  launchd 家族／bash 3.2／zsh／`macos_smoke_local.sh` 的**實際執行行為**本輪一次都沒跑過。
  凡本檔或程式碼裡出現「兩平台皆…」的字樣，mac 那一半是**推論**不是實測。
  🔴 **本輪最尖銳的一個實例**：hook 的 exec form 有 POSIX 半邊（`_hook_launcher.py` 靠 shebang
  ＋ exec bit 直接被 exec），而**那條路徑從未被任何 Claude Code 實例執行過**——
  今天守它的是靜態判準（存在／X_OK／shebang 解析／直譯器版本下限），不是一次真的觸發。
  ⇒ 「POSIX 側 hook 會動」在今天是**設計宣稱**，不是量測值。

- 🔴 **雲端結論本輪結構上取不到**：Actions 帳務停擺（job 的 steps 數為 0）。
  ⇒ 本輪所有「綠」的射程都是**本機＋act(ubuntu 容器)**。
  `gh run list --limit 12 --json workflowName,event,headSha,conclusion,status` 是 R81 的第一動作。

- 🔴 **第三方複審跑了兩審，但二審收斂包的修復沒有再被第三方看過。**
  ⇒ 證據強度分三層（由強到弱）：①經二審逐項比對過磁碟的部分；
  ②本收斂包在單人窗口取得的閘門 rc 與注入紅綠；③其餘「已修復」說法。
  ②③ 的共同上限是**作者自證**（M3「作者自證不計分」）。

- 🔴 **注入自證證明的是「判準會對那個形態轉紅」，不是「這類缺陷已經絕跡」。**
  `doc_guard_total_problems()` 只守**被標記的那一行**：它保證那一行講的是今天的數字、
  且算術自洽，**不保證作者把每一個該標的地方都標到了**（與款(4) 只保證有一列、
  不保證理由是好理由同型）。

- 🔴 **本檔 §2 那張一句話總表是判定，不是量測。** 判定背後的數字全部在
  `AutoSDD_improving_104.md` §1，而那些也是取得時點的量測值——每一格都附了現查指令，請重跑。
