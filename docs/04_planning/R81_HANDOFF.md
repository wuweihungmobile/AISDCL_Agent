# R81 交棒書（跨平台輪，Windows 11 真機）

> 體例沿用 R78／R79／R80：**凡述及「尚未做／還缺／已推送／已通過」這類狀態，一律附現查指令，不寫快照結論**
> （機械物：`tools/tests/test_doc_loc_baseline_freshness_r60.py`，類別 `TestR78HandoffClaimsCarryLiveCommands`）。
> 本檔內出現的每一個數字都是「取得它的那個時點」的量測值，不是常數。
>
> 🔴 **成書時點（誠實劃界，影響本檔每一個 rc 的可歸因性）**：本檔由 **QA 複審收斂包**寫成，
> 而寫成的當下 **SA／SD 兩位複審者仍在唯讀審查同一棵樹**。⇒ 本檔的閘門 rc 不是在嚴格單人窗口取得的。
> 唯讀者理論上不改樹，但本 repo 已有三次「並行改樹造成假紅」的判例，所以這一點必須寫在最前面：
> **R82 讀到本檔時務必自己重跑一次**，不要採信本檔任何 rc。
>
> 🔴 **本輪定位**：本檔是 R81 的交棒，承接輪次為 **R82**。記號約定：`$r`＝repo 根，`$p`＝`$r\.venv\Scripts\python.exe`。

---

## §0 R82 開場必讀（照順序做，不要跳）

1. 🔴 **第一動作是「先結列」，不是開新戰場——未結列離 warn 線只剩個位數。**
   ```powershell
   $r='D:\CursorProject\AISDCL_Agent'; $p="$r\.venv\Scripts\python.exe"
   & $p "$r\tools\check_defect_log_crossref.py" --unresolved-count
   & $p "$r\tools\archive_defect_log.py" --check
   ```
   R81 收輪當下的實測是 **84／warn 86／fail 98** ⇒ 距 warn 線只有 **2 筆**、距 fail 線 14 筆。
   🔴 **歸檔不會降低這個數**（工具自己每次都印這句）：未結列在結構上不可搬，體積那條線的洩壓閥
   對這一條完全無效。唯一出路是**真的把列結掉**或**改派給具名承接者**。
   ⇒ R82 若照 R80／R81 的節奏開場就登記三、五筆新列，**開場即越 warn 線**。

2. **查雲端**（R71／R73 各付過一次「收輪不查雲端」的代價，R79 起訂為必做）。
   ```powershell
   gh run list --limit 12 --json workflowName,event,headSha,conclusion,status
   ```
   R80 全程沒有雲端結論可用（Actions 帳務停擺，job 的 steps 數為 0）。R82 開場請先確認帳務是否恢復；
   沒恢復就沿用 act ＋ Docker 本機驗證，並且**不得**把「本機／act 全綠」寫成「CI 全綠」。

3. **覆核本檔 §3 那份待辦**，逐項跑它自己帶的現查指令。
   **不要採信本檔任何「已修」字樣**（同 Nightly 取證紀律 #17 的 zero-trust 雙向）。
   ```powershell
   & $p "$r\tools\run_root_unittests.py"   ; "rootunit=$LASTEXITCODE"
   ```

4. **重跑歸因，不要引用任何百分比**（先驗量測器符號、再跑歸因——順序是判準的一部分）：
   ```powershell
   & $p "$r\tools\probe\audit_session.py" --selftest
   & $p "$r\tools\probe\misstep_attribution.py"
   ```

---

## §1 收輪實測狀態（只給指令，不給 rc 快照）

```powershell
$r='D:\CursorProject\AISDCL_Agent'; $p="$r\.venv\Scripts\python.exe"
$env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'
& $p "$r\tools\run_root_unittests.py"          ; "rootunit=$LASTEXITCODE"
& $p "$r\AutoClaude\tools\check_loc_budget.py" ; "loc=$LASTEXITCODE"
& $p "$r\tools\check_defect_log_crossref.py"   ; "xref=$LASTEXITCODE"
& $p "$r\tools\archive_defect_log.py" --check  ; "arch=$LASTEXITCODE"
& $p "$r\tools\check_script_parity.py"         ; "parity=$LASTEXITCODE"
& $p "$r\tools\check_hooks_liveness.py"        ; "hooks=$LASTEXITCODE"
& $p "$r\tools\check_defect_log_crossref.py" --unresolved-count
```

🔴 **讀 rc 不要接管線**（pwsh 7.x 上截斷型管線會**保留前一個值**＝真紅被讀成綠）。
🔴 **算行數／搜尋一律不經 shell**（`Get-Content | Measure-Object -Line` 對 CJK 檔給假數字）。

### 🔴 本輪最尖銳的一筆訂正：`check_hooks_liveness.py` 對 P7 的改動**零鑑別力**

QA 複審注入實測（把一條 shell form 條目注回 `AutoClaude/.claude/settings.json`，等於退掉 P7 的一部分）：

| 載具 | 注入後的表現 |
|---|---|
| `tools/check_hooks_liveness.py` | **rc=0**（仍然綠——它只驗**載具存在性**，形態判準不在它射程內） |
| 於 `tools/tests/`：`& $p -m unittest test_check_hooks_liveness` | **FAILED (failures=1)**，訊息逐字指名「shell form 條目實測 1、基準 0——退回 shell form」 |

⇒ **拿 `check_hooks_liveness.py` 的 rc 當「exec form 沒有被退回」的憑證是假綠**，而那個誤用已經真的
寫進 `docs/04_planning/AutoSDD_improving_105.md` §3 的 P7 列（本輪已訂正）。
本輪同時在該工具的檔頭與 CLI 輸出各補一句射程告示，讓下一個人不必重踩一次。
形態那一面的唯一憑證是 `tools/tests/test_check_hooks_liveness.py`。

### 護欄層累積淨額

本輪走的是款(9) 的**登記手續**（`[非淨減法輪]`），依禁止事項第一條 **Q2 一律判未達成**。
現值與逐次重釘的稽核痕跡一律現查，本檔刻意不寫死數字：

```powershell
Push-Location "$r\tools\tests"; & $p test_adr_xplat001_c1c2_lock.py --print-guard-lines; Pop-Location
```

---

## §2 本輪各訴求的達成判定

🔴 **本節只給判定與指針，不複製數字**——十二條（Q1~Q6／S1~S3／P7／a／b）的逐條結論寫在
`docs/04_planning/AutoSDD_improving_105.md` §1 那張表，**那是唯一的家**；本輪三份掃描證據檔
（`docs/06_quality/CrossPlatform_R81_Scan_Findings.md`／`docs/06_quality/CrossPlatform_R81_Quota_Review.md`／
`docs/06_quality/CrossPlatform_R81_Ledger_Triage.md`）是它們的詳情面。

```powershell
Select-String -Path "$r\docs\04_planning\AutoSDD_improving_105.md" -Pattern '結論' -Encoding utf8
```

| 訴求 | 本輪判定（**判定不是量測**，數字一律回 §1 現跑） |
|---|---|
| P7 哨兵／hook 彈窗 | ✅ `AutoClaude/.claude/settings.json` 的 6 條轉成 12 條 exec form，`SHELL_FORM_CENSUS` 兩格皆 0；⚠️ 憑證換過（見 §1 那張表） |
| Q2 架構簡潔、淨減法輪 | ❌ 未達成——走款(9) 讓步條款，成長全在護欄層 |
| Q4 Windows 低級錯誤根因 | ⚠️ 最大桶（宣稱先於查證）本輪落地**第一個**通用機械物＝幽靈路徑判準；⚠️ 它不宣稱涵蓋整桶 |
| Q5 挖深＋清技術債 | ⚠️ 未結列由開場 87／88 收到 84，方向對，但仍在 warn 線邊緣 |
| 其餘九條 | 一律以 `AutoSDD_improving_105.md` §1 為準，本檔不轉錄 |

---

## §3 交給 R82 的待辦（每一項都附現查指令）

### 3.1 `context_budget_guard.py` 的體積：本輪只納入治理，**當下沒有任何東西變小**

R81 把它收進 shrink-only 的治理面，但那是「不准再長大」，**不是「已經拆好了」**——
R81 收輪那一刻它仍是單檔 1,634 行。

🔴 **R82 訂正**：本節原句斷言拆分還沒有動工（原措辭不逐字複述），並登記 `tools/lib/quota_gate.py` 當證偽
標的——而 R82 的 Q2-02 就把額度水位那一整段拆了出去，該檔今天在磁碟上（當回合實測：
`quota_gate.py` 615 行、`context_budget_guard.py` 由 1,634 降到 **952** 行）。
原句不逐字留著當現行說法（複述假話等於製造新假話）。**這一筆是判準自己抓到的**：
`test_negative_existence_claims_r82` 用它自己登記的 `absent-if:` 標的打了自己的臉——
那正是那道判準存在的理由，也是本節不再需要 `absent-if:` 標記的原因（宣稱已經沒有了）。
**尚未做完的那一半**：952 行仍是絕對紅線 750 的 1.27 倍，還要再拆。

```powershell
& $p -c "from pathlib import Path; print(len(Path(r'$r\.claude\hooks\context_budget_guard.py').read_text(encoding='utf-8').splitlines()))"
```

🔴 拆的時候注意：`.claude/hooks/` 是 hook 的家，拆出去的模組若被 hook 直接 import，
**載具解析失敗時 CC 是 fail-open**（只記一行 ERROR 就放行）⇒ 拆錯的表徵與「修好了」一模一樣。

### 3.2 L4「真的量不到」：閂鎖**已落地**，未關的是**出聲通道**與**跨平台憑證來源**

🔴 **本節連續兩輪自我打臉，兩層的成因不同，所以兩層都記**（原句一律不逐字複述當現行說法
——複述假話等於製造新假話）。

**第一層（R82 訂正，L4-01）**：本節最初斷言那道降級閂鎖還沒被寫出來，而它在**寫下它的
同一個 commit**（`692753e`）裡就已落地。逃得掉的原因是原附的現查指令 grep 的是 **ADR**，
而 ADR 只證明「設計存在」，不證明「實作不存在」——錨與宣稱不同軸，於是永遠打不臉。
代價與根 CLAUDE.md 判過的「低報分子」同型：它會讓下一輪去補一支**已經存在**的鎖。

**第二層（R82 收尾二次訂正）**：修第一層的那次重寫，把現查指令的錨釘死在
`.claude/hooks/context_budget_guard.py` 這**一個檔名**上；而同一輪的另一包把
`note_degraded()` 與出聲通道整段搬進 `tools/lib/quota_gate.py`（＝ Q2 帳上那筆
「hook 1451→952 是搬家不是減法」的同一次搬家）⇒ **訂正文在同一輪內把自己變成假話**。
收尾當回合實測（2026-08-09）：對 `context_budget_guard.py` 下 `def note_degraded`
與 `additionalContext` 兩個 pattern 皆 **0 命中**；同回合對照組
（`quota_meter.py` 的 `KEYCHAIN_SERVICE|REASON_NO_CREDENTIALS_DARWIN`）**5 命中**
⇒ 不是指令寫壞，是錨釘錯地方。

🔴 **這一次換掉的是錨的形狀，不只是錨的值**：現查改成掃「hook ＋ `tools/` 整個活躍
Python 面」找**符號**，不指名任何一個檔——檔案在 repo 內搬家不會讓它變假，只有符號真的
消失才會。單檔錨在版面上與整面錨長得一模一樣，這正是它兩輪都逃掉的原因。

現查指令（錨在**符號**不在檔案；跑不出命中就是本節在說謊）：

```powershell
$r = 'D:\CursorProject\AISDCL_Agent'
Get-ChildItem -Path "$r\.claude\hooks","$r\tools" -Recurse -Filter *.py |
  Select-String -Pattern 'def note_degraded|hookSpecificOutput' -Encoding utf8 |
  ForEach-Object { "$($_.Path.Substring($r.Length+1)):$($_.LineNumber)" }
Select-String -Path "$r\tools\lib\quota_meter.py" -Pattern 'KEYCHAIN_SERVICE|REASON_NO_CREDENTIALS_DARWIN' -Encoding utf8
```

🔴 **`git grep` 不可以拿來當本節的現查管道**：`tools/lib/quota_gate.py` 目前 untracked，
`git grep -F 'def note_degraded'` 當回合只命中**本檔自己這段指令文字**——取數管道回的是
文件自己的迴音而不是實作，那與 0 命中同樣沒有鑑別力。同一個陷阱在
`tools/tests/test_negative_existence_claims_r82.py` 的合成注入自證上也發生過一次
（已改為在臨時 git repo 內就地構造證據，見該檔該測的 docstring）。

🔴 **上面那段指令刻意排在現況清單「之前」**：本節的每一個小節都受
`test_doc_loc_baseline_freshness_r60.py::TestR78HandoffClaimsCarryLiveCommands` 管，
而它的區塊語意是「標題到第一個條目為止算一塊」——把現查指令寫在條目**之後**，
標題那一塊就等於沒附指令（實測轉紅）。順序在這裡是語意，不是排版偏好。

現況（R82 收尾當回合逐條實查，2026-08-09）：
- **已落地，但住在 `tools/lib/quota_gate.py`**（不在 hook 檔裡）：`note_degraded()`（`:354`）
  ＋ per-source TTL 閂鎖／痕跡檔／`unmeasurable` 狀態字，以及 L4-02 補的
  `hookSpecificOutput` → `additionalContext` 出聲通道（`:386-387`；exit 0 下唯一送得進
  模型上下文的通道，不動 rc）。hook 端以 `import quota_gate` 消費
  （`context_budget_guard.py:227`），能力不可達時該軸退化成「量不到」。
- **L4-03 的 mac 分支已落地**：`quota_meter.py` 的 `KEYCHAIN_SERVICE`（`:79`）／
  `REASON_NO_CREDENTIALS_DARWIN`（`:100`）／`darwin` → login Keychain（`:149`、`:157`、`:327`）。
  🔴 **mac 真機仍零覆蓋**：判定邏輯可注入且已測，`security` 的 service 名與輸出形態
  未在 mac 上驗過，交 R83（指令見 `quota_meter.KEYCHAIN_SERVICE` 註解）。
  <!-- handoff-claim-verified: 「有沒有在 mac 真機上跑過」不落磁碟，repo 內零載體可現查；能查的只有「有沒有 mac 專屬的判定分支」，而那不是同一件事 -->

### 3.3 ADR §2.4 的**載體二**（AutoClaude 側 quota 軸）本輪**零交付**

設計在 ADR 裡，repo 內**沒跑**過任何一行對應實作。
<!-- absent-if: QuotaAwarePlugin -->
🔴 R82 補：上面那個 `absent-if:` 標的是**交付時必然出現的類名**，不是完整涵蓋——
換個類名交付它就抓不到。標記的用途是「這句話有辦法被打臉」，不是「窮舉所有交付形態」。

```powershell
Select-String -Path "$r\docs\04_planning\ADR\ADR-XPLAT-005-quota-aware-throttling-and-fanout-resume.md" -Pattern '載體二' -Encoding utf8
```

### 3.4 mac 真機**零覆蓋**（本輪一次都沒跑過）
<!-- handoff-claim-verified: 「有沒有在 mac 真機上跑過」不落磁碟，repo 內零載體可現查——CI 沒有 macOS runner 的執行痕跡進 repo，本機也沒有 -->

R81 全部量測都在 Windows 11 真機取得（工具側＝pwsh 7.x Core）。launchd 家族／bash 3.2／zsh／
mac smoke 的**實際執行行為**本輪**沒跑**。act 的 ubuntu 容器**不是** mac 的替代品。

```powershell
Select-String -Path "$r\docs\06_quality\CrossPlatform_Maturity_Criteria.md" -Pattern 'mac' -Encoding utf8
```

🔴 act 那一跑的 `MAC-NATIVE-ONLY = 0` **不代表 mac 有覆蓋**——它只說明那棵樹裡沒有 mac-only 標籤的測試。
詳見 `docs/06_quality/CrossPlatform_R81_Scan_Findings.md` 的 act 憑證節。

### 3.5 兩筆工作樹行尾漂移：本輪**刻意未修**

兩支檔在工作樹是 CRLF，而 `.gitattributes` 對它們宣告 `text eol=lf`：
`AutoClaude/.perf_baseline.toml`（當回合實測 27 個 CRLF、0 個裸 LF）與
`AutoClaude/tests/integration/test_dry_run_kernel_path.py`（266 個 CRLF、0 個裸 LF）。

**刻意不修的理由**：兩支都在 ONBOARDING 指紋的涵蓋面內，改它們會讓指紋失準，
而回填指紋必須是 push 前的最後一個動作（見 §4 禁止事項最後一條）。

```powershell
& $p -c "from pathlib import Path
for rel in ['AutoClaude/.perf_baseline.toml','AutoClaude/tests/integration/test_dry_run_kernel_path.py']:
    raw = Path(r'$r').joinpath(rel).read_bytes(); crlf = raw.count(b'\r\n')
    print(rel, 'CRLF=', crlf, 'LFonly=', raw.count(b'\n') - crlf)"
```

🔴 這種漂移 `git status` 結構上看不見（正規化只作用於 index），雲端也看不見
（`actions/checkout` 必定重新 smudge）⇒ 只有本機工作樹那一欄看得到。

### 3.6 四方複審轉錄檔 `docs/06_quality/CrossPlatform_R81_Review.md`：**已建立**（R82 訂正）

🔴 **R82 訂正（Q4-02 的第二個真實案例）**：本節原本斷言該檔還沒有被建出來。R82 開場實查
`git ls-files` 命中它、`Test-Path` 為 True ⇒ 那句話已為假。它逃得掉的原因與 §3.2 同型：
本節附的現查指令跑的是**幽靈路徑判準那支測試**，而該判準只回答「基線登記得對不對」，
不回答「這個檔今天在不在」——又一次錨與宣稱不同軸。

它是 `AutoSDD_improving_105.md` §6 明訂的收輪產物之一。原設計把它登記進幽靈路徑判準的具名
基線（形態＝「刻意不存在的宣稱」），**而那筆登記會自己清掉自己**：檔案一旦建立，基線的
stale 自檢當場轉紅並要求刪掉該筆登記 ⇒ 交棒給 R82 的動作是**去把那筆登記刪掉**。

```powershell
Push-Location "$r\tools\tests"; & $p -m unittest test_doc_loc_baseline_freshness_r60.TestR81GhostPathClaims; Pop-Location
```

### 3.7 帳本裡明文承接 R82 的未結列（現查，不抄清單）

```powershell
& $p "$r\tools\check_defect_log_crossref.py" --unresolved-count
Select-String -Path "$r\docs\06_quality\AutoSDD_Defect_Log.md" -Pattern 'R82' -Encoding utf8
```

---

## §4 禁止事項（沿用 R80 §5，不放寬，另加本輪兩條）

- ❌ **不准設 `AUTOSDD_QUOTA_GUARD_OFF=1` 繞過節流守衛。** 那個開關是給「守衛自己壞掉」用的逃生口，
  不是給「這一批扇出我想開大一點」用的。R80 一輪撞額度四次，全部是扇出開太大造成的。
- ❌ **不准 `--no-verify`／`AUTOCLAUDE_SKIP_HOOKS=1`／跳過或註解掉失敗測試。**
- ❌ **不准把「N 方複審」講成「四方通過」。** 跑了幾方就寫幾方；沒跑的那幾方要具名寫出來。
  R81 的複審方數與各方結論，以各方交件回報為準，本檔不代為宣稱。
- ❌ **跑完 `& $p "$r\tools\sync_onboarding_baselines.py" --write` 之後，不准再動被指紋涵蓋的任何檔。**
  回填必須是 push 前的最後一個動作；回填後再改一個字，指紋就與磁碟不符了。
- ❌ **不准為了讓數字好看而調高任何門檻／棘輪／體積上限。** 合法出口只有兩條：
  ①同一次變更內刪等量以上的行（真淨減）；②走款(9) 的**登記手續**（`[非淨減法輪]` ＋ 指名逐檔清單的家）。
  ② **不是及格線，是讓步條款**——走 ② 的輪次 Q2 一律判未達成。
- ❌ **不准在 Windows 用 Bash 工具**（PreToolUse hook 會擋）；不准裸 `cd`／`Set-Location` 帶相對路徑；
  **讀 rc 不接管線**；**算行數不經 shell**。
- ❌ **不准在多 agent 並行期間宣稱「全套閘門 rc=0」**——那個 rc 是別人鍵盤的函數。
- ❌ **不准以「act／Docker 本機全綠」代替 mac 真機結論**（Linux 綠不蘊含 mac 綠；BSD 與 GNU coreutils
  的差異結構上不在 ubuntu 容器的射程內）。
- ❌ **不准以「閘門全綠」代替複審**（R75 實證：12 筆 blocking 有 8 筆是閘門自己沒有鑑別力）。
- ❌ **不准把本檔任何數字當常數引用。** 本檔的每一個數字都附了現查指令，請重跑。

---

## §5 取證邊界（誠實劃界）

- 🔴 **本檔不是在單人窗口寫成的**（見檔頭）。§1 的閘門指令是本包實跑過的，但同時段有兩位唯讀複審者在場
  ⇒ 照本 repo 的紀律必須標出來，不能寫成「單人窗口取得、rc 完全可歸因」。

- 🔴 **注入自證證明的是「判準會對那個形態轉紅」，不是「這類缺陷已經絕跡」。**
  本輪擴出去的幽靈路徑判準只保證「治理活文件裡以反引號寫出的 repo 路徑真的存在」，
  它明文**不保證**那些路徑上的檔在守文件說它在守的東西（見該判準自己的誠實劃界測試）。

- 🔴 **`MAC-NATIVE-ONLY = 0` 是「那棵樹裡沒有 mac-only 測試」，不是「mac 有覆蓋」。**
  這兩句話在螢幕上長得很像，而它們的差別正是 §3.4 那一整條待辦。

- 🔴 **act 跑的是 ubuntu 容器，不是 CI，也不是 mac。** 它證明得了「Linux 剖面上這批測試會過」，
  證明不了「GitHub Actions 上會過」（環境不同）也證明不了「mac 上會過」。
