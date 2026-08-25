# CrossPlatform R105 — 掃描發現與逐檔清單（tools/tests/ 護欄層行數棘輪維護輪）

<!-- guard-total:R105 --> **本輪護欄層累積淨額（稽核痕跡合計，同輪多列合併）＝ 88556 → 88656（+100）**
——本檔僅記錄本輪第一列（+0，逐檔清單見下方〈§A 逐檔清單〉；搬遷散文見〈§B
`strip_ps_comments` 已知不涵蓋沿革〉）；同輪後續追加（四方複審 REJECT 修復
DEF-200-202 三批：+49／+12／+28）見 `docs/06_quality/CrossPlatform_R105_FourParty_Fix.md`。

- **輪次**：R105（治理維護輪：另一批修復為 `tools/tests/` 四支檔新增回歸測試，
  觸發護欄層行數棘輪；本輪只處理棘輪重釘本身，未動任何測試判準的實質內容）。
- **本檔性質**：`_GUARD_LINES_REPIN_LOG` R105 那一列指名的「逐檔清單的家」，
  同 R104 既有體例。

## §A 逐檔清單

| 檔案 | 舊值 | 新值 | 淨額 | 說明 |
| :---- | ---: | ---: | ---: | :---- |
| `tools/tests/test_block_destructive_git_r83.py` | 2187 | 2195 | +8 | 新增 `test_the_background_amp_exclusions_are_load_bearing` 對 DEF-200-158（段首 `&` PowerShell call operator 誤判）的回歸斷言 |
| `tools/tests/test_context_budget_guard.py` | 8092 | 8108 | +16 | 新增 DEF-200-012（`TMPDIR` 漂移不得改變 `cache_path()`）與 DEF-200-196（`Retry-After: 0` 不得讀成「現在」）兩組回歸測試 |
| `tools/tests/test_defect_id_reference_integrity.py` | 261 | 262 | +1 | DEF-200-015：`_REF_RE`／`_git_grep` 的引用形態由僅 `DEF-101-*` 擴大為納管 `DEF-200-*` 家族 |
| `tools/tests/test_mac_endurance_r83.py` | 1780 | 1789 | +9 | DEF-200-173：新增 `_DenyMkdirPath` 子類，收窄 `mkdir` 權限錯誤注入到受測模組（不再打 `pathlib.Path` 本尊） |
| `tools/tests/_platform_helpers.py` | 446 | 403 | -43 | `strip_ps_comments()` docstring 的「已知不涵蓋」逐版沿革（R57 round 3／4 差分實測數據）搬遷至〈§B〉，判準本體與 WHY 理由未搬動——只搬逐版量測記錄 |
| `tools/tests/test_adr_xplat001_c1c2_lock.py` | 6190 | 6199 | +9 | 本檔自身編修：新增本列稽核列 ＋ DEF-200-224 到期義務兌現（`_REPIN_NET_CAP_SCHEDULE` 追加 `(105, 660)` 一列並重新武裝下一段 `_REPIN_NET_CAP_DUE_ROUND=107`／`_REPIN_NET_CAP_DUE_TARGET=630`）＋凍結前綴延伸（`_REPIN_LOG_FROZEN_PREFIX_LEN` 62→63，`_REPIN_LOG_HISTORY_SHA256` 隨之改變，`_FROZEN_PREFIX_REWRITE_LEDGER` 追加一列＝DEF-200-224） |
| **合計** | 88556 | 88556 | **+0** | 四檔新增回歸測試 +34、`_platform_helpers.py` 搬遷散文 -43、本檔自身編修 +9：34-43+9=0 |

## §B `strip_ps_comments` 已知不涵蓋沿革（搬遷自 `_platform_helpers.py` docstring）

判準本體（涵蓋清單本身）與 WHY 理由留在 `_platform_helpers.py` 原處只是**精簡**，
不是刪除；以下為搬遷前的完整逐版沿革與量測記錄，供日後追溯。

### 第 2 條（`--%` stop-parsing 符號）

stop-parsing 符號 `--%`：其後所有內容原樣傳給原生指令、`#` 不是註解，本函式仍會
剝除（R57 A-R57R2-04）。**刻意不修**：`--%` 之後不剝＝多留一段「其實是註解」的
文字當功能碼，等於在鎖上開一條新的 fail-open（R57 round 2 的 A-R57R2-02／
R57R2-QA-01 修的正是這一類）；反之現行的多剝只會造成假紅（fail-closed）。真出現
`--%` 用法時再連同回歸測試一起處理。

### 第 5 條（`_PS_COMMENT_LEAD` 外前導字元）——本節最重的一段沿革

**不在 `_PS_COMMENT_LEAD` 內的前導字元**後的 `#` 一律不視為註解起點。**這不是
「未來可能」的風險，而是現行、已量測的結構性限制**（R57 round 4 Architect／SD
交叉實測後改述）：真實規則是 tokenizer 的 command/argument 對 expression **模式
相依**，前導字元白名單原理上不可能完備——expression 模式下 `#` 幾乎恆為 token
終止＋註解起點，前導字元可以是任意數字／識別字／`::`／`]$var`…。

Architect 以 pwsh 7.6.3 真 parser 對 64 個實務形態差分得 **FAIL_OPEN=27**（其中
**20 案 parseErrors=0** ＝完全合法的日常寫法，如 `$a = 1#c`、`$env:PATH#c`、
`$a = [int]$b#c`、`$a = $b?.Length#c`）、**FAIL_CLOSED=0**；SD 另以約 130 條探針
得 FAIL_OPEN=37，並實證仍可用 `$note = $x#  -WakeToRun` 繞過
`test_windows_nightly_anchor_parity.py`（round 3 修掉的
`Write-Output "note"#…` 手法已確認關閉）。**方向為 fail-open**（漏剝＝註解冒充
功能碼），故必須明確揭露而非淡化。

**不在 R57 修的理由**：全語料實測洩漏數為 **0**（137 支 `.ps1`／2,847 個真
Comment token，Architect 與 SD 各自獨立差分皆得 0），屬 latent；真正的修法是換
模型——建議（R59 改派：原寫「R58 建議」，R58 整輪作廢故無承接者；改派為 R60 起
未指派 backlog，見帳本 DEF-101-521）把 pwsh parser 對全語料的 Comment token
凍結成 golden fixture 做離線差分，可在 CI 不裝 pwsh 的前提下把 ground truth
機械化，一次消掉整個天花板（同法亦可解 `_ci_scan_anchors.py` 判例第 (3) 條的同型
天花板）。**切勿再往集合裡補字元**——那是 whack-a-mole，本條存在正是為了阻止它。

### 第 6 條（`_PS_HERE_STRING_LEAD`）

`_PS_HERE_STRING_LEAD`（`" \t=(,;|{"`）同樣未含 `]`／`)`，故 `[string]@"` 這類
以 `]` 收尾的 here-string 起始不被辨識。方向為多剝（fail-closed，不影響鎖的正確
性），本輪一併登記不修（SD-R57R3-01 第 4 點）。
