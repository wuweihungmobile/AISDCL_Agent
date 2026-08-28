# ADR-XPLAT-011 — R99 已知邊界宣告彙編（四筆帳本觀察項的劃界紀錄）

- **狀態**：Accepted（劃界宣告，非新設計；逐項見下方各節裁決）
- **日期**：2026-08-21
- **平台**：平台中立（各節個別標註）
- **性質**：本文件把四筆帳本觀察項各自的「為何不現在修復／為何交由非工程角色裁決」收斂成一份具名文件，供帳本回指。**本文件不包含任何新程式碼或設定改動**；每節皆先以本輪（R99）現場重驗磁碟現況，再落裁決——凡重驗發現原始記載已與磁碟不符者，一併如實訂正。

---

## 1. 對應 DEF-101-235：R16 全面掃描殘留 P3 觀察項

**原始記載**（R16，2026-07-21）列出四項低優先殘留：
① `tools/dev_start.py` 的 `_pid_alive`/`_list_pid_ppid_pairs_windows` 呼叫 `ctypes.windll.kernel32.OpenProcess`/`CreateToolhelp32Snapshot` 未設定 `restype`；
② `tools/windows_smoke_local.ps1` 的 `Test-InstallRoundtrip` 假設 `.git` 是目錄，linked worktree 下會誤判；
③ `AutoClaude/tools/run_local_nightly.ps1` 的 `Copy-Item` 更新 `nightly_latest.log` 無重試；
④ PS 5.1 版本守衛在 `run_tlc.ps1`／`run_self_evolution.ps1` 兩處逐字重複，未抽出共用模組。

**🔴 R99 現場重驗（磁碟現況與原始記載已不一致，訂正如下）**：

| 子項 | 現場重驗結果 | 證據 |
|------|------------|------|
| ① restype 未設定 | **仍然成立**——`tools/dev_start.py` 全檔 `grep -n "restype\|argtypes"` 零命中，`OpenProcess`（974 行）與 `CreateToolhelp32Snapshot`（1054 行）呼叫點皆未設 `restype` | 本輪 `grep` 實測 |
| ② `.git` 目錄假設 | **已修復**（R9／R17）——`Test-InstallRoundtrip`（`tools/windows_smoke_local.ps1:353` 起）已改用 `git rev-parse --path-format=absolute --git-common-dir` 解析共享 config 位置，函式內註解逐字寫明「不硬編 `.git\config`（DEF-101-235②）」，一般 clone 與 linked worktree 皆正確解析 | 檔內 391-403 行區塊 |
| ③ `Copy-Item` 無重試 | **已修復**（R17）——`AutoClaude/tools/run_local_nightly.ps1:2163` 起改用 `Copy-ItemWithRetry`（比照既有 `Add-LogLineSafe` 退避重試機制），行內註解逐字寫「R17 DEF-101-235③ 修復」 | 檔內 2163-2165 行區塊 |
| ④ PS5.1 守衛重複 | **原始形狀已消失（非修復、是架構前提改變）**——LATEST（`AISDLC_SDD_v0.30`）的 `run_tlc.ps1` 於 R65 起薄殼化（委派 Python `tools.fsm_runtime.tlc_runner`），檔頭註解明載「原『需 pwsh 7+』限制…隨薄殼化解除——本檔不再自行對 java 做重定向，觸發條件已不存在」，`run_tlc.ps1` 內已無任何 `$PSVersionTable` 檢查；僅 `run_self_evolution.ps1` 仍保留該守衛（`AISDLC_SDD_v0.30/tools/arch_fitness/run_self_evolution.ps1:57-61`）。原始缺陷描述的「兩處逐字重複」在 LATEST 已不成立（只剩一處）；該守衛在 29 支凍結歷史版本裡仍逐版重複，但依 Copy-on-Evolve 鐵律凍結版不可回改，此為結構性、非本輪射程可解 | `run_tlc.ps1` 檔頭 1-11 行；`run_self_evolution.ps1:57-61` |

**裁決**：
- ①：**維持已知邊界**（不修復）。`OpenProcess`/`CreateToolhelp32Snapshot` 回傳值在 32-bit `restype` 預設下於 64-bit Windows 理論上會被截斷，但兩處呼叫點僅用回傳值做**布林式**存活判定（`handle != 0` / 迭代終止判斷），不做指標運算或跨呼叫傳遞，實際命中窗口需要一個恰好落在會被截斷 bit 範圍內、且恰好把「有效 handle」判斷成「無效」（或反之）的 PID/handle 值組合——理論殘留，無已知真實觸發路徑，且 `tools/dev_start.py` 已受 `AutoClaude/tools/check_loc_budget.py` 的 SPECIAL_FILES 行數棘輪管，貿然新增 `ctypes` 型別宣告前應先確認不會撞棘輪上限。**退場條件**：任何一次真實環境下量到判斷錯誤（非人工構造），或該檔下次因其他理由被大幅改寫時，順手補上 `restype = wintypes.HANDLE`。
- ②③：**訂正帳本記載為已修復**，不應繼續以「未修復、非本輪修復範圍」措辭留存。
- ④：**訂正帳本記載為「原始形狀已因架構前提改變而消失」**，不是「仍逐字重複、未抽共用模組」——LATEST 已由薄殼化附帶消除了跨檔重複；剩餘的重複只存在於 29 支凍結歷史版本內部（同一支 `run_self_evolution.ps1` 跨版本重複，而非同版本內 `run_tlc.ps1`/`run_self_evolution.ps1` 互相重複），此為 Copy-on-Evolve 政策下的既定結構，非本 ADR 射程。

**給帳本的建議狀態**：`partial`（非 `closed-by-decision`）——四項中兩項已修復、一項因架構改變而原始描述失效、僅一項仍為真實殘留並在此劃界；「四項皆為理論性/低機率殘留、非本輪修復範圍」這句原始狀態欄措辭已不準確，不應原樣沿用。

🔴 **R99 收尾時經覆核改採 `closed-by-decision`**（與本節上一段的建議不同詞）：帳本 `DEF-101-235` 實際落地的首詞是 `closed-by-decision`，override 理由見 `docs/06_quality/CrossPlatform_R99_Ledger_Closure.md:38`（P2 表覆驗結論：「ADR 對四個子項都給出明確裁決……這是『已充分審查並做出決定』而非『還沒處理』⇒ 裁決 `closed-by-decision`」）——覆核判定「四項皆已被本 ADR 逐一裁決」這件事本身已構成「已審視並決定」，比 `partial`（暗示還有審視動作待做）更準確反映帳本列的真實狀態；本段原始建議予以保留作為裁決過程記錄，不回頭抹除。

---

## 2. 對應 DEF-101-324：`state_loader._sanitize_component()` 多對一碰撞

**原始記載**（R39 起，R47 擴大範圍確認跨全部 30 個版本一致存在）：淨化函式把 `<>:"\|?*` 與控制字元統一替換為 `_`，`"AC:042"` 與 `"AC/042"` 淨化後皆為 `"AC_042"`；`production_to_fpl.py::generate_fpl_draft()` 因檔名不含時間戳，兩個自然可能同時存在的生產遙測識別碼會靜默覆蓋彼此的 advisory FPL 草案。

**🔴 R99 現場重驗**：`AISDLC_SDD/scripts/component_sanitizer.py`（R45 起 30 個版本共用的同一份實作）的 `sanitize_component()` 現況**未加入任何唯一性後綴或碰撞偵測機制**——多對一碰撞行為與原始記載一致，未被後續任何輪次修復。

**裁決**：**維持已知邊界，列入 backlog**。根本解需為碰撞情境加唯一性後綴（如短 hash）或偵測既存同名檔時提高門檻改名，這改變的是**產出檔名的生成規則**（下游消費者需同步識別新命名慣例），超出「檔名淨化」這個函式本身的單一職責範圍，貿然在本輪動手屬於範圍蔓延（scope creep）。四方複審已一致判定此為**測試鑑別力縫隙**（測試能觀察到碰撞可能性，但當前生產路徑的實際觸發門檻——需要兩個不同分隔符慣例的識別碼、且都不含時間戳緩衝——偏低機率），非阻擋性缺陷，依比例原則不在本輪投入根本解成本。**退場條件**：`production_to_fpl.py` 一旦觀察到真實碰撞事故（而非理論推演），或任何下游新增呼叫點同樣缺乏時間戳緩衝，優先權應上調並排入下一輪。

**給帳本的建議狀態**：維持 `open`（backlog，比例原則暫緩），或若帳本詞彙表傾向不再用 `open` 表達「已審視並決定暫緩」，可用 `closed-by-decision（backlog：本 ADR §2）`——**依帳本本身既有的 `open`（記事存證）/`closed-by-decision`（決策不修）判例慣例二擇一**，本 ADR 不代為決定用詞，只提供裁決依據。

---

## 3. 對應 DEF-101-399：`windows-compat-ci.yml`／`macos-compat-ci.yml` 手動鏡射維護

**原始記載**（R50，R81/R82 改派）：兩份 workflow（本輪重驗：現行 1782／1296 行，較 R50 當時 935／679 行持續成長）純手動鏡射維護，全庫 `grep workflow_call`／`composite` 零命中，現有機械鎖（`test_workflow_permission_concurrency_lock.py`／`test_smoke_ci_sync.py`）僅各自鎖檔內個別區塊字面值，未有測試比對兩份 workflow 彼此的 job/step 結構是否仍保持鏡射。

**🔴 R99 現場重驗**：
- 全庫 `grep -rn "workflow_call" .github/workflows/` 與 `grep -rln "composite" .github/workflows/` 仍**零命中**——未採用 reusable workflow。
- `tools/tests/test_check_script_parity.py` 存在，但其比對對象是**成對的 `.ps1`/`.sh` 安裝腳本**（如 `install_windows_nightly.ps1` ↔ `install_mac_nightly.sh`），**不是**兩份 compat-CI workflow 的 job/step 骨架——不滿足原始建議「新增一支類似 `check_script_parity.py` 的 YAML 結構 parity 測試」。
- `test_workflow_permission_concurrency_lock.py` 對兩份 workflow 各自的 permission／concurrency 區塊逐 job 錨定比對，但判準是**字面值比對**，不是「job/step 骨架是否仍鏡射」的結構性比對。
- 兩份 workflow 行數持續成長（935→1782／679→1296），驗證「長期人工鏡射維護成本隨框架演化線性增長」的原始論點依然成立。

**裁決**：**維持已知邊界，列為架構前瞻提案**。四方複審（SA/SD/QA）於 R50 當輪已一致 APPROVE 且未將此列為阻擋項，僅 Architect 提出作為新架構優化提案；本輪（R99）重驗確認提案本身仍然有效、且問題隨時間持續放大，但**抽出 reusable workflow 或新增 YAML 結構 parity 鎖屬淨新增機械物**，依根層 CLAUDE.md「防線預算制」紀律，新增守門需引用實證缺陷編號並走搭載優先序——本 ADR 即補齊「引用實證缺陷編號」這一步的正式落點，但**動手新增鎖或重構 workflow 本身不在本輪（帳本收斂輪）射程內**，留待下一個以此 ADR 為起點的實作輪次。**退場條件**：(a) 新增一支 YAML 結構 parity 測試機械鎖住兩份 workflow 的 job/step 骨架鏡射，或 (b) 抽出 `workflow_call` reusable workflow 以 `os`/`runs-on` 為輸入參數收斂重複結構——任一達成即可移除本節劃界。

**給帳本的建議狀態**：`closed-by-decision（本 ADR §3；架構前瞻提案已正式落點，非阻擋，退場條件見上）`。

---

## 4. 對應 DEF-101-559：AISDLC_SDD LATEST `hub-push.yml` sample 的 action 版本升級

**原始記載**（R60 round 2，自 `DEF-101-541` 拆出）：`tools/check_gha_action_versions.py` 掃描面邊界已載明「LATEST（`AISDLC_SDD_v0.30`）的 `hub-push.yml` sample 是否要升 action 版本，刻意不由 CI 工具鏈側代決」——真實待決事項是：升 LATEST 會讓「各版此檔為同一 git blob」這個目前可機械核對的不變量首次分裂。

**🔴 R99 現場重驗**：`AISDLC_SDD/AISDLC_SDD_v0.30/.github/workflows/hub-push.yml` 現況檔頭仍註明「This is a sample workflow for the Hub Registry repo, not for the AISDLC-SDD framework repo itself」「在 framework repo 內保留此檔僅作為治理範例——實際觸發於 Hub repo 端」，未發現任何後續輪次針對此檔的版本升級決策記錄。原始待決事項依然懸而未決。
【2026-08-28 訂正注：掌舵者已裁決**升版**（DEF-101-559 查證落「會被複製使用」分支——該 sample 明文供下游複製到 Hub repo 真實執行）；LATEST `hub-push.yml` 8 站點已升版對齊根層基準，「30 版同一 git blob」不變量隨之分裂並已記錄。詳 `AISDLC_SDD/AISDLC_SDD_v0.30/EVOLUTION_LOG.md`「LATEST 修改備忘」節。原文保留為 R99 當時現況。】

**裁決**：**本 ADR 不代為做出該項政策決定**——升不升版是 AISDLC_SDD 凍結／LATEST 版本政策擁有者的裁決權限，理由有二：(a) 這是**真實的取捨**（升版打破「30 版此檔同一 git blob」不變量 vs 不升版累積 action 版本落後），不是可由程式邏輯推導出唯一正解的工程問題；(b) 該檔屬 `AISDLC_SDD/` 子專案 scope，其凍結／LATEST 版本政策依 monorepo 根 CLAUDE.md「路徑陷阱」節載明的邊界，非本輪根層帳本收斂包的裁決權限範圍。本 ADR 的貢獻僅止於：把此前散落在帳本狀態欄的解鎖條件正式落地為可長期回指的文件，避免懸而未決的政策問題被誤讀為「無人知曉」或被靜默遺忘。

**具體解鎖條件（照錄，供政策擁有者直接執行）**：
① 決定 LATEST `AISDLC_SDD/AISDLC_SDD_v0.30/.github/workflows/hub-push.yml`（sample）是否隨根層一同升版；
② 若升，須同時接受「30 版此檔不再是同一 git blob」並在該版 `EVOLUTION_LOG.md` 記錄；
③ 若不升，把理由寫進該檔檔頭以免下一輪重複發現。

**給帳本的建議狀態**：`routed（承接輪次：未指派——待政策擁有者裁決；解鎖條件見本 ADR §4）`，不建議標記 `closed-by-decision`：政策問題尚未被實際裁決，只是被正式登記為「這是一個懸而未決的政策問題，不是工程缺陷」，若標記 `closed-by-decision` 容易被誤讀為「已經有人做了決定」。
【2026-08-28 訂正注：政策擁有者已實際裁決（升版），上方「不建議 closed-by-decision」的前提（尚未裁決）自此不再成立——§4 解鎖條件①②已履行、③不適用（升版分支），帳本該列據此改 `closed-by-decision`。裁決存證＝`AISDLC_SDD/AISDLC_SDD_v0.30/EVOLUTION_LOG.md`「LATEST 修改備忘」節。原文保留為裁決前史料。】

---

## 5. 誠實劃界（本 ADR 整體）

- 本文件是**帳本收斂輪**（R99）的產出，職責是把四筆觀察項的現況重新核實並收斂成可回指文件，**不包含任何程式碼修復**（第 1 節①除外情境未修復、②③已在更早輪次修復並於此訂正記載）。
- 第 1 節對 DEF-101-235 的重驗結果（②③已修、④原始形狀消失）意味著**原始帳本狀態欄措辭已經是過期資訊**——若帳本狀態欄未同步訂正，下一個讀者仍會誤以為「四項全部尚待處理」。本 ADR 明確建議書記在更新帳本時採 `partial` 而非直接沿用舊有措辭。
- 第 4 節刻意**不**幫政策擁有者做決定；把「需要人決定」偽裝成「已經決定」是本 ADR 極力避免的錯誤（同根 CLAUDE.md「不得以模型判斷推翻機械守衛」的精神：不得以模型判斷取代人類治理權限）。
