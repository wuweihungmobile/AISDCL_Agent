# CrossPlatform R104 — 掃描發現與逐檔清單（PRD §4.2.5／§4.2.1 BURSTING/EWMA，只算不接線）

<!-- guard-total:R104 --> **本輪護欄層累積淨額（稽核痕跡合計）＝ 88574 → 88556（-18）**
——逐檔清單見下方〈§A 逐檔清單〉；三段搬遷散文見〈§B `_platform_helpers.py` 沿革〉。

- **輪次**：R104（實作 `tools/lib/quota_pace.py::bursting_ok()`／`ewma_burn_rate()`，
  PRD `docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` §4.2.5／§4.2.1）
- **範圍**：只算不接線——兩支函式不進 `quota_gate.py` 的 `decide()`／`pace_report()`
  決策鏈，是否接線留待四方複審裁決（見 `docs/04_planning/R104_HANDOFF.md`）。
- **本檔性質**：`_GUARD_LINES_REPIN_LOG` R104 那一列指名的「逐檔清單的家」（款(9)
  雖不強制——本輪淨額 ≤0——仍比照既有體例留存）。

---

## §A 逐檔清單

| 檔案 | 舊值 | 新值 | 淨額 | 說明 |
| :---- | ---: | ---: | ---: | :---- |
| `tools/tests/test_quota_policy.py` | 2993 | 3055 | +62 | 新增 `TestR104BurstingOkAndEwmaBurnRate`（4 個測試方法、table-driven subTest 涵蓋 19+ 案例，含 T_rem=30.0 邊界恰好通過、四項 telemetry 輸入 `None` fail-closed、佇列/旗標參數不傳預設不放寬、EWMA 翻頁後 cold-start 不回報舊值） |
| `tools/tests/_platform_helpers.py` | 537 | 446 | -91 | 三段 forensic 歷史敘事搬遷（見〈§B〉），判準與其 WHY 理由本體**未搬動**——只搬「逐版沿革／位元組級量測記錄」 |
| `tools/tests/test_adr_xplat001_c1c2_lock.py` | 6179 | 6190 | +11 | 本檔自身編修：新增 R104 稽核列＋兩處 `_FROZEN_GUARD_LINES` 數字更新＋凍結前綴延伸（`_REPIN_LOG_FROZEN_PREFIX_LEN` 61→62、`_REPIN_LOG_HISTORY_SHA256` 重釘、`_FROZEN_PREFIX_REWRITE_LEDGER` 追加一列＝DEF-200-223） |
| **合計** | 88574 | 88556 | **-18** | 三檔相抵：62-91+11=-18，連續上升 streak（R102/R103）於本輪歸零 |

`tools/lib/quota_pace.py`（570→662，+92）不在本量測面（`tools/tests/` 之外），故不列入上表。

## §B `_platform_helpers.py` 沿革（搬遷自 `usable_bash_for_fixture`／`PS_UTF8_PRELUDE`／`_PS_COMMENT_LEAD` 三處 docstring／註解）

判準本體與其存在理由（WHY）留在 `_platform_helpers.py` 原處只是**精簡**，不是刪除；
以下為搬遷前的完整逐版沿革與量測記錄，供日後追溯。

### usable_bash_for_fixture 沿革

🔴 凡測試需要「真的把某支 .sh 跑起來」，一律用本函式取得直譯器，不得直接把字面值
`"bash"` 當 argv[0] 交給 `subprocess`（`test_bash_probe_spec_contract.py::
TestNoBareBashInvocationInToolsTests` 機械掃描守護）。理由**不是**「PATH 順序可能讓
WSL 排在前面」，而是更硬的一條：Windows 上 `subprocess` 以
`CreateProcess(lpApplicationName=NULL)` 解析裸名，其搜尋順序是「應用程式目錄 →
當前目錄 → **System32** → Windows 目錄 → **PATH**」——**System32 排在 PATH 之前**。
於是只要 argv[0] 是裸名，`C:\Windows\System32\bash.exe`（WSL 啟動器）就**必定**先
命中，PATH 上排多前面的 Git Bash 都救不了。未安裝發行版時它以 **UTF-16LE** 印
`Windows Subsystem for Linux has no installed distributions.` 並 `exit 1`，受測腳本
一行都沒被執行，測試看到的卻是「腳本回了非預期 rc」＝**歸因完全錯誤**的紅燈
（DEF-101-753：R69 收輪 push 後由雲端 windows-compat-ci 抓到）。**裝了發行版的機器
上不會是紅燈，會更糟**：它不再 `exit 1`，而是把 repo 的腳本丟進 Linux **真的跑起
來**——沒有錯誤訊息、沒有非零 rc，只有語意悄悄換了一個作業系統。

**同一次 CI run 內就有對照組可證此機制**（run 30739865214）：
`test_dev_start.TestPickPythonGeMin` 用的是 `shutil.which("bash")`（只查 PATH）
⇒ 拿到真 Git Bash、全數通過；`test_smoke_ci_sync` 用的是字面值 `"bash"`
⇒ 拿到 WSL、三支全紅。**同一台機器、同一個 PATH，兩種解析路徑結果相反**，這排除
了「PATH 上沒有 Git Bash」這個解釋。推論：唯一安全的用法是 argv[0] 給**絕對路
徑**——這正是本函式的回傳值。`shutil.which("bash")` 雖能避開 CreateProcess 的
System32 優先，但它沒有 System32 段排除，在「WSL 佔位版確實排在 Git Bash 之前」
的開發機（DEF-101-617 已記載該機型）仍會回 WSL，故一併不用。

**為何住在本檔**：本函式是第①類收納物（測試 fixture 對開發者本機環境的隱性假
設）。收斂前 `tools/tests/` 內有兩份 fixture 用途的複本
（`test_bash_probe_spec_contract._probe_a_real_usable_bash_for_fixture` 與
`test_macos_smoke_skip_honesty._usable_bash`），且**兩份的排除規則並不一致**——
後者對裸 bash 完全沒有 System32 排除。故比照 R57 `strip_ps_comments` 判例收斂為
一份。

🔴 **R71 訂正：本段原本的因果宣稱是錯的，且把風險等級講低了一整級。** 原文寫
「後者只是恰好因為驗活會失敗才沒出事（fail-closed 的僥倖，不是設計）」。
2026-08-02 於 Windows 11 真機（WSL **已裝**發行版）逐項實測，該僥倖並不存在：

```
C:\Windows\System32\bash.exe   -c PROBE_CMD
  → rc=0, stdout == b'probe_ok\n/tmp/probe_dir\n'
C:\Program Files\Git\bin\bash.exe -c PROBE_CMD
  → rc=0, stdout == b'probe_ok\n/tmp/probe_dir\n'   ← 與上一行逐位元組相同
shutil.which("bash")           → C:\WINDOWS\system32\bash.EXE
```

也就是說**驗活對 WSL 佔位版的鑑別力是 0**：兩支 bash 的 rc 與 stdout 完全無法區
分，唯一擋得住的是 System32 路徑規則。`test_bash_probe_spec_contract.
TestWslStubIsNeverAcceptedAsRealBash` 讓 stub 驗活成功因此不是假想情境，是照著
本機現況造的。⚠️ 同型的舊敘述另有一份留在 `test_macos_smoke_skip_honesty.py`
（該檔開頭「fail-closed 的僥倖」註解），R71 本輪射程外未訂正。

🔴 **R80 S5-03：原本「刻意不收斂的兩份」已經收斂進本函式**（連同第三份）。原文的
理由是「它們是生產端探針的**獨立重寫**回歸鎖，獨立性本身就是鑑別力來源」。當回合
實測推翻了那個前提：`test_pre_push_dispatcher._usable_bash()`、
`test_git_hooks_install_common._usable_bash()`、
`test_windows_forbidden_filename_parity._usable_bash()` 三份在**剝除 docstring 後
的 AST 逐字相同**（正規化雜湊皆 `9797b0251822`；量法與輸出見
`docs/06_quality/CrossPlatform_R80_Subtraction_Evidence.md`）。複製貼上不是獨立
重寫——逐字相同的三份共享 100% 盲點，沒有任何一份會在另外兩份漏掉時轉紅，所以
它們付的是三份維護成本、換到的鑑別力是零。

真正的「獨立重寫」仍然在，而且是本 repo 唯一守得住的那一份：
`AISDLC_SDD/scripts/bash_probe.py::usable_bash()`（生產端，跨子專案邊界故不可
import 本檔）與 `tools/integration_gate_core.py::find_git_bash()`——兩者的正規化
雜湊與本函式互不相同（`91fa22dca19e`／`bd83a4f6bb68`／`ed3d027ac8d8`），是真的
各自寫成的。生產端那一份的行為鎖仍在
`AISDLC_SDD/scripts/tests/test_bash_probe.py::TestUsableBashSystem32Guard`，不受
本次收斂影響。⇒「獨立重寫維持鑑別力」的正當射程是**硬邊界隔開的真獨立實作**
（語言邊界、子專案邊界），不是同一棵樹裡的純函式複本。

### PS_UTF8_PRELUDE 沿革

WHY 需要它：PowerShell 寫進 pipe 的位元組編碼＝`[Console]::OutputEncoding`，預設
值是**主控台 output code page**（繁中 Windows＝950/Big5），不是 UTF-8。於是含中文
或 `❌`（U+274C）的輸出在 Python 端以 `encoding="utf-8"` 解碼即成亂碼／`?`，斷言
假紅。而 `chcp` 是**整個 console 共用**的行程外狀態 ⇒ 全套跑時只要有較早的測試
把它換成 65001，後面所有 PowerShell 呼叫就跟著沾光：那種綠不是自己掙來的、會隨
測試順序漂移（DEF-101-760 的形狀）。每個呼叫端自帶前置才是自足的。

WHY 只准有一種寫法（R71，第①類收納物）：本 repo 自 R42／DEF-101-350 起把這串行
內抄寫在多個姊妹鎖裡，R71 又抄了第 4 份、且寫法不同
（`$OutputEncoding = [Console]::OutputEncoding = New-Object
System.Text.UTF8Encoding $false`），理由寫的是「避免 `[System.Text.Encoding]::UTF8`
帶 preamble、某些構造會在 stdout 開頭吐 BOM」。2026-08-02 於 Windows 11 真機、
Windows PowerShell 5.1 單變因實測（先把 `[Console]::OutputEncoding` 打成 cp950
造出「未被污染的 console」，再套各寫法跑 `WindowsAppsGuard.ps1` 的
`Write-PythonGeMinRemediation`，比對 stdout 原始位元組）：

```
（列名為寫法的簡稱；「本常數」即 PS_UTF8_PRELUDE）
    A 無前置（缺陷基準）        → b'? \xa7\xe4\xa4\xa3'  ，U+274C 遺失、中文亂碼
    B 本常數（既有多數寫法）    → b'\xe2\x9d\x8c \xe6\x89'，BOM=False
    C R71 第 4 種（$OutputEncoding + UTF8Encoding $false）
                                → b'\xe2\x9d\x8c \xe6\x89'，BOM=False
    D 只設 Console + UTF8Encoding $false
                                → b'\xe2\x9d\x8c \xe6\x89'，BOM=False
```

B/C/D 三種前置**輸出逐位元組相同、BOM 一次都沒出現**（.NET 的
`Console.OutputEncoding` setter 本來就會剝掉 preamble）⇒「BOM」這個分歧理由不成
立。`$OutputEncoding` 管的是另一件事——PowerShell 經管線把文字餵給**原生子行程
stdin** 的編碼；本 repo 的呼叫端一個都沒有這種用法（同一實測的 native-child 情境
四種寫法亦全同）。故取**既有多數寫法**為唯一形態（Rule 11 從眾，且此舉讓尚未收
斂的行內複本與本常數逐字相等），不引入第 4 種。

### _PS_COMMENT_LEAD 沿革

R57 round 3 SD-R57R3-01：原集合 `" \t;|({,"` **漏掉右括號類與引號類收尾字元**，
使「以 `)`／`}`／`]`／`"`／`'` 結尾的功能碼後緊接的 `#`」不被視為註解起點而原樣
保留——「錨點只認功能碼」的鎖因此 fail-open。SD 以本機 pwsh 7 的真 PowerShell
parser（`[System.Management.Automation.Language.Parser]::ParseInput` 取 Comment
token）取得 ground truth，逐條確認這五種形態在 PowerShell 中**確實都是註解**：
`Write-Host (1)#c`、`if ($true) { }#c`、`$a[0]#c`、`Write-Host "a"#c`、
`Write-Host 'a'#c`。對照組 `c#`／`$#`／`Write-Host $a#b` 的 Comment token 為空，
即現行 lead-char 設計要保護的情形——補上這五個字元不會傷到它們（Architect round 4
以 64 案差分實測 FAIL_CLOSED=0，零退化）。

**R57 round 4 SD-R57R4-01 訂正「為什麼安全」的理由**（原寫「其前一字元是字母／
`$`，仍不在集合內」——該理由與 PowerShell 真實規則**不等價**，被後人採信會導向
錯誤修法）：真正的保護來源是 PowerShell 的 **command/argument（bareword）解析模
式**——bareword 本身可含 `#`，與前導字元無關。同一個 `$x#c` 在 **expression 模
式**下 `#` 就**是**註解（pwsh 7.6.3 實測：`$c#zz` → Comment@2；
`$v = $x#  -WakeToRun` → Comment@7）。換言之 `$` 不構成「保護類別」，lead-char
白名單只是對 parse-mode 的近似。**R59 改派**：原寫「R58 修法方向」，而 R58 整輪
作廢＝指向不存在的輪次；改派為 R60 起未指派 backlog，見帳本 DEF-101-521。

SD 並以 bug-injection 實證可繞過：把 `tools/install_windows_nightly.ps1` 的功能
碼 `-WakeToRun` 刪除、只在 `Write-Output "note"#…-WakeToRun…` 註解裡留下字樣後，
`test_windows_nightly_anchor_parity.py` 6 支測試**全數 OK**（負對照：不留註解則
正常翻紅）。全語料實掃 137 支 `.ps1` 的 2,847 個真 Comment token，現況洩漏數為
0 ⇒ 屬 latent fail-open，與 round 2 的 A-R57R2-02（here-string 誤判）同級同型。
