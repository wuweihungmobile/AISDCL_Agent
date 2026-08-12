# AutoSDD_improving_109（R85）— macOS 第三輪：**減法輪**

> 前一份＝[`AutoSDD_improving_108.md`](AutoSDD_improving_108.md)；交棒書＝[`R84_HANDOFF.md`](R84_HANDOFF.md)。
> 範本＝[`AutoSDD_Iteration_Prompt_Template.md`](AutoSDD_Iteration_Prompt_Template.md)。
>
> 🔴 **本檔體例**：會漂移的量測值一律不寫死，只寫「哪一支載具會印出它」。
> 凡寫出的 rc，都是**收尾單人窗口當回合真的跑過**的；沒跑的一律標明。

---

## §1 本輪定位：R85 是**減法輪**（與前八輪相反）

逐輪護欄層淨額實測 `[(77,3505),(78,2243),(79,3120),(80,2334),(81,3033),(82,5400),(83,5260),(84,2655)]`
——**連八輪都是加法**。兩件事在本輪同時到期：

| 到期物 | 居所 | 不做的後果 |
|---|---|---|
| `_REPIN_ROUND_NET_CAP` 5400 → **≤3200** | `tools/tests/test_adr_xplat001_c1c2_lock.py`（款(12)，`_REPIN_NET_CAP_DUE_ROUND = 85`） | 本輪重釘紀錄一旦出現 R85 列，款(12) 當場轉紅 ⇒ **擋 push** |
| 一次**淨額 ≤ 0** 的重釘 | ADR-XPLAT-002 §8.1 item 15（款(11)） | R86 前不兌現即轉紅 |

⇒ 掌舵者訴求 2（「**請拿掉不合理機制**，進行最佳化改善設計」）與 M1 在本輪合流。
R84 對訴求 2 的執行量經 Architect 實測為 **2.6%**（淨減法僅 −71 行）——本輪的成敗判準就是這個數字。

---

## §2 開場基線（收尾窗口 2026-08-12 當回合實跑，讀 rc 不接管線）

| # | 指令 | rc / 值 |
|---|---|---|
| 1 | `.venv/bin/python tools/run_root_unittests.py` | **0**；`[skip census] tools/tests@darwin 共 44 支：platform=44／tool-absence=0／env-disabled=0／structural-pair=0／debt=0／untagged=0` |
| 2 | `.venv/bin/python tools/check_defect_log_crossref.py` | **0**（三類 warning 全在線上：未結 88／warn 86、殘留待辦 40、時鐘 fail-open 7 筆） |
| 3 | `.venv/bin/python tools/check_hooks_liveness.py` | **0** |
| 4 | `.venv/bin/python tools/check_ntfs_paths.py` | **0** |
| 5 | `.venv/bin/python AutoClaude/tools/check_loc_budget.py --json` | **0** |
| 6 | `ls -l docs/06_quality/AutoSDD_Defect_Log.md` | **244,877 bytes**（`_LEDGER_WARN_BYTES = 245,760` ⇒ 餘裕 **883 B**） |
| 7 | `pg_autodetect()` | `(True, '已注入 … postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/autoclaude')` ⇒ PG 容器 up **且已 migrate** |
| 8 | `.venv/bin/python tools/session_resume_planner.py --pace` | `cap=4 recommended=4 band=notice binding=seven_day`（56%／剩 5411 分鐘） |

🔴 **第 1 列是本輪對「訴求 S1／系統問題 1（徹底解決 skipped）」的關鍵事實**：
根層 44 支 skip **全部**是 `platform`（`[WINDOWS-NATIVE-ONLY]`），`debt=0`、`untagged=0`
⇒ 在 macOS 上**結構性不可消除**，它們在 Windows 上會跑。
⇒ 正解不是「讓它們在 mac 上跑」，而是**證明 win32 剖面真的涵蓋它們**（M6 的真正門檻是
「從未在**任何**平台執行的測試歸零」，不是「單一平台零 skip」）。這一條本輪只能靜態推進。

---

## §3 派工（依鐵律七切持有面，pace cap=4）

| 包 | 主題 | 持有面（互不重疊） |
|---|---|---|
| **P1** | 帳本洩壓（bytes 死結治本 ＋ 未結 88→≤80 ＋ 殘留待辦 40） | `docs/06_quality/AutoSDD_Defect_Log.md`、`tools/check_defect_log_crossref.py`、新建證據檔 |
| **P2** | 護欄層淨減法 ＋ 款(12) net_cap 到期義務 ＋ 根層 skip 剖面 | `tools/tests/**`、`tools/lib/**`、`tools/*.py`（除 P1 那支）、`.claude/hooks/**` |
| **P3** | AutoClaude AC-(a)/(b)/(c) ＋ **QA 獨立驗收（掌舵者指定）** ＋ AC 側 skip | `AutoClaude/**` |
| **P4** | 跨平台深掃（訴求 1／3／4／5），**唯讀** | 只寫 `docs/06_quality/CrossPlatform_R85_Scan_Findings.md` ＋ 新建 `tools/probe/**` |

🔴 **鐵律七的落地**：每包的「常數／史料／消費端」三者都在同一持有面內
（例：P2 的 `_REPIN_ROUND_NET_CAP`（常數）、`_GUARD_LINES_REPIN_LOG`（史料）、
`repin_cost_ratchet_problems()`（消費端）同住 `test_adr_xplat001_c1c2_lock.py`）。
R84 的三個反例（切開後任一單包都做不完、只能回報 `not_done`）不得重演。

🔴 **本節 R85 收尾訂正（SA 複審 SA-04 抓到，判詞我完全接受）**：上一段寫的「未派、順延」
在寫下的當回合為真，其後扇出視窗回復即派出 **P5**（AISDLC_SDD Agents 精進，28 支盤點、
7 支已修、刪 102 條幽靈依賴）與 **P6**（判準擴面、幽靈依賴 199→1、4 支 fail-open 治本），
最終共派 **12 包**（P1~P12）。SA 逐字駁回「SDD Agents 未派」這句宣稱——**它是對的**，
本表未隨派工同步更新即是 M4「散文宣稱 ≠ 實作射程」的本輪實例之一。

### 3.1 🔴 訴求 8（Container 環境整理）——**本節補記，SA-04 的另一半**

SA 實測本輪 7 份 R85 文件 ＋ 全部新程式碼對訴求 8 命中 **0**（對照組 `Archive`=47、
`前沿`=22 證明取數管道有效），並判定「**它不在『未派、順延』的名單裡 ⇒ 不是延期，
是沒人記得它存在**」。這個判讀成立且重要——**做過但不落磁碟，等於沒發生**。

補記當回合實測（收尾單人窗口 2026-08-12 親跑，非派 agent）：

| 項目 | 量測 |
|---|---|
| `docker images` | **5 個**，合計 5.614 GB |
| 逐一稽核消費者 | `aisdcl-act/ubuntu:act-latest`＋`catthehacker/ubuntu:act-latest`＝`.actrc` 釘住（`-P ubuntu-latest=` 兩行）／`pgvector/pgvector:pg17`＝`autoclaude_ci_pg` 正在跑且已 migrate／`koalaman/shellcheck:stable`＝`tools/run_shellcheck.py` 消費／`busybox`＝僅 SDD 模板與規則檔的文字範例，**無可執行消費者** |
| `docker ps -a` | 1 個（`autoclaude_ci_pg`，healthy） |
| **處置** | `docker builder prune -f` ⇒ 回收 **407.8 MB**；build cache 24 項 → 8 項、3.01 GB → 2.602 GB、reclaimable 407.8 MB → **0** |
| **刻意未做** | **零 image 刪除**。5 個全部有消費者或有明確用途；`busybox` 僅 6.22 MB 且是 SDD 模板示範的對照物，刪它省不到 0.1% 卻可能讓框架文件的示範失去可驗證性 |

🔴 **誠實劃界**：R84 收輪時已「清掉唯一無引用的 image」，故本輪環境本來就接近乾淨
⇒ **訴求 8 在 R85 的真實工作量很小**，這一格不應被讀成一項重大交付。

---

## §4 掌舵者本輪的兩個直接指示（逐字承接）

1. **Windows 彈窗定位**：掌舵者回覆「**我不確定**」⇒ 本輪 Windows 側**仍無人可驗**。
   ⇒ 訴求 7 本輪一律標「已定位、未驗證」，不得升級為「已修復」。
2. **「AC-(c) 定位但真機未驗算不算交付」**：掌舵者裁決「**先請 QA 驗**」
   ⇒ 已派 P3 以 QA 身分獨立查證並給出裁決（含合成注入自證），**不採信 R84 交棒書的自陳**。

---

## §5 驗收條件（本輪要拿到才算收斂）

- [ ] 護欄層淨額 **≤ 0**（憑證＝`--print-guard-lines` 印 `(+0)` 且逐檔漂移 0）
- [ ] `_REPIN_ROUND_NET_CAP` ≤ 3200
- [ ] 帳本未結 ≤ 80、主檔 bytes 餘裕 ≥ 13 KB
- [ ] 四方複審（Architect／SA／SD／QA）全部 blocking 收斂（M2 分母不為空）
- [ ] 全樹閘門 rc=0：`run_root_unittests.py`／`check_defect_log_crossref.py`／
      `check_hooks_liveness.py`／`check_ntfs_paths.py`／`check_loc_budget.py`／
      `AutoClaude pytest`／`AISDLC_SDD ci-gate.sh`

---

## §6 禁止事項（沿用 R84 §8，並加一條）

1. 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`。
2. 🔴 不准任何毀滅性 git（`git stash` 全家族／`checkout -- <path>`／`restore <path>`／
   `reset --hard|--merge|--keep`／`clean`／`switch -f`）。並行包**連 `git stash create` 都不准**
   （R84 事故：一行 `git stash` 清空 91 檔）。
3. 不准為了讓紅變綠而刪測試／改成不比較／加 `skip`／放寬棘輪。
   本輪具體形態：`_REPIN_ROUND_NET_CAP`／`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS` **只准下修**。
4. 🔴 **本輪新增**：不准用「折行／刪空白行／刪註解」充當淨減法。
   減掉的必須是**機制**（重複判準、無鑑別力的鎖、同一份知識的第二個家），
   且每刪一條都要回答「它守的東西還有誰在守」（`DEF-101-757`：已知缺口不得只以劃界結案）。

<!-- guard-total:R85 --> **本輪護欄層累積淨額＝ 82838 → 83475（+637）** —— 🔴 **本輪有三列稽核痕跡，款(10) 判的是逐輪加總**：① P2 收工時 `82838→82838（+0）`；② 收尾單人窗口在十二包停工後 `82838→83320（+482）`；③ 四方複審收斂包 F1 停工後 `83320→83475（+155）`，來源全是複審點名的 blocking 修復（SD-B3 授權邊界安全回歸／ARCH-02 exe-argv 接線／樣本數鎖／QA-06 探針污染）。前兩列**不追溯修改**——每一列在寫下的那一刻都為真，就地改成後見之明正是款(7) append-only 指紋要防的形狀，三列並存即稽核痕跡。⇒ **R85 是加法輪，訴求 2「單輪淨額 ≤ 0」未達成**。🔴 **這是算術不是判斷**：需淨刪的量遠大於可用的去重面——兩份互相獨立的量測（機械 AST 普查 `tools/probe/guard_layer_dedup_census.py` ＋ 人工複核）與棘輪自陳的第三條出口（把 WHY／史料搬出護欄層，最集中處＝`_GUARD_LINES_REPIN_LOG` 自己）**全部用盡仍不足**。硬湊只能開始砍射程確有差異的對子＝真的挖洞。義務未消失：已具名為 `_NET_SUBTRACTION_DUE_ROUND`（**刻意不留延期參數**），到期未兌現即當場紅。逐筆量測與交棒＝`docs/06_quality/CrossPlatform_R85_Guard_Repin_Evidence.md` §4。`[收尾單人窗口當回合實測；憑證＝tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines 印 (+0) 且逐檔漂移 0 支]`
