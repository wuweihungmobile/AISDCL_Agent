# R123 交棒書（技術債總清償循環令第五投·第二棒；精準修復輪）

- **輪籤**：R123
- **主線**：掌舵者於上一棒收輪後裁「繼續修，再降 3 筆」。挑
  `docs/04_planning/AutoSDD_TechDebt_Paydown_Playbook.md` §A.1 標 `dev｜高信心` 且**鎖持有面
  互不重疊**的三筆（AutoClaude 子專案／quota 族／skip 族）並行派工。
- **帳本**：未結列 **41 → 40**（結 `DEF-200-200`／`DEF-200-205`；`DEF-200-183` 轉 `partial`；
  新立 `DEF-200-246` 承接 205 殘餘）⇒ 淨減 1。
- **護欄層**：<!-- guard-total:R123 --> 行數 `91668→91990`（淨額 +322）。款(10) 上限 559 未撞；
  上一棒 −125 已使款(11) streak 歸零，本棒為其後第一個正淨額輪。逐列與逐檔清單＝
  `docs/06_quality/CrossPlatform_R123_Scan_Findings.md` §1。

## 本棒已落地

1. **DEF-200-200 fixed**：「已過去的 `resets_at`」四層改共用一個述詞，且它把**時刻已過去**
   與**時鐘偏移**分流成兩個處置不同的回答（無參考時刻時退回「已過去」，不得指控時鐘——
   那正是原缺陷的病灶）。`row_of()` 落 `resets_at` 且舊列缺欄位仍可讀。
2. **DEF-200-205 fixed**：`boot_self_check`（PRD §6.2）接進 `main()` 啟動路徑（problems 非空
   即以非零 rc 停機）、`dirty_worktree_rescue`（§4.5.9）接進 halt 凍結點（存檔失敗即拒絕
   續跑、不 fail-open）。跨 core-purity 邊界故新增 port 走注入，九條 import contract 全 kept。
3. **DEF-200-183 partial**：鍵文法 SSOT（新檔 `tools/lib/skip_profile_key.py`）＋pgextras 軸
   ＋方向鎖 re-key 破洞已修；**生產者側四層住 `AutoClaude/` 持有面，依鐵律七單包做不完**。
   另上一道機械化的完成度棘輪（缺軸鍵數只准降，新增歧義鍵當場紅）。
4. **DEF-200-246 新立**：PRD §6.2 兩個半邊在生產上仍不可達（`dry_run` 判決未接執行器／
   `integration_queue` 零生產寫者），皆刻意未做並附理由。
5. **收尾重釘**：守衛線凍結表＋兩個稽核列＋指紋鏈＋prefix_len 同步，收斂為零漂移。

## 已驗證

- 帳本三支文件閘門：`check_defect_log_crossref.py` rc=0（帳本 175 列、具名治理文件 94 份
  皆已登記）、`check_archive_required.py` rc=0、`check_handoff_carriers.py` rc=0。
  未結列數現查 `python tools/check_defect_log_crossref.py --unresolved-count`。
- 守衛線 `--print-guard-lines`：淨額 `91990→91990 (+0)`、逐檔漂移 0 支（收斂）。
- `test_adr_xplat001_c1c2_lock`：`Ran 192 tests / OK`、rc=0。
- 三包各自的針對測試與突變驗紅＝`[他包回報]`，逐筆轉錄在
  `docs/06_quality/CrossPlatform_R123_Debt_Closure.md`。
- 全套與 push 前閘門的結論見本檔〈還沒做〉節或收輪報表。

## 還沒做（不塗綠）

1. **四方定點複審尚未執行**（循環令 §5 要求實作項過四方）
   <!-- absent-if: CrossPlatform_R123_Review -->——證偽錨＝四方複審結論轉錄檔名（同 R79／
   R80／R81 同名檔既有體例）：那個字面一旦在任何 tracked 檔裡搜得到，本條宣稱即為假並當場
   轉紅。依 M3「作者自證不計分」，本棒全部改動屬自證。現查本棒落地了哪幾個 commit：
   `git log --oneline -5`。
2. **`DEF-200-183` 的 re-key 主體仍未落地**：生產者側四層（`local_ci_gate._skip_profile()`／
   marker 傳輸鏈／`conftest.py` 發射端／`test_local_ci_gate.py` 回歸鎖）住 `AutoClaude/`
   持有面，需獨立的收尾單人窗口；其後才輪到八個鍵 re-key 與完成度棘輪降為 0。現查今天還
   缺幾個軸：`python -c "import sys; sys.path.insert(0,'tools/lib'); import skip_profile_key as k; print(k.keys_missing_axes())"`。
3. **帳本未結列仍未降到目標**：本棒 41→40，尚未接近循環令 §8 的 ≤30。逐筆分診結論＝
   `docs/06_quality/CrossPlatform_R122_Debt_Closure.md` §0（needs-dev 與 needs-adjudication
   兩類）。現查現值：`python tools/check_defect_log_crossref.py --unresolved-count`。
4. **上一棒的途中發現 F1 仍未入帳本**（Stop 稽核器把 hook 的 non-blocking 提醒誤判為
   「本平台載具失敗」，本棒再次復現）。全文＝
   `docs/06_quality/CrossPlatform_R122_Scan_Findings.md` §2。現查它有沒有被立列：
   `Select-String -Path docs/06_quality/AutoSDD_Defect_Log.md -Pattern "non-blocking"`。
5. **darwin／linux 剖面沒跑**（本機 Windows）：`DEF-200-183` 的兩份 census 只有 win32 側，
   帳本記的 darwin 數字本棒未覆核。現查本機平台：`python -c "import sys; print(sys.platform)"`。

## 下一步（下一個窗口二選一，掌舵者指定）

- **續降帳本（第三棒）**：照 §A.1 挑下一批 `dev｜高信心` 且持有面不重疊的。🔴 **派工前必先
  為守衛線淨額做預算**：本棒 +322 是 streak 歸零後的第一個正淨額輪，**再連續兩輪正就必須
  搬遷抵銷**（上一棒實測搬遷可換 −1029，但兩支最肥的鎖檔因是別的機械物的逐字比對面而整檔
  排除，理由見 `docs/06_quality/CrossPlatform_R122_Guard_Prose_Migration.md`）。
- **補跑四方定點複審**：對上一棒與本棒共六筆修復＋搬遷做一審全查、二審驗修復。

## 禁止事項

- 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`、push 不帶 `AUTOSDD_NET_RATCHET_OFF`。
- 不准為了讓護欄層轉綠而調高 `_REPIN_NET_CAP_SCHEDULE` 或
  `_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS`（兩者只准下修）；不准自行加註
  `_REPIN_APPROVED_ROUND_OVERAGE`（須四方複審核准）。
- **不准在生產者帶上第四軸之前 re-key `DEF-200-183` 的天花板表**——那會讓 AutoClaude 那一棵
  整批退回 advisory＝比今天更沒有牙。正確前置順序寫在
  `docs/06_quality/CrossPlatform_R123_Debt_Closure.md` §DEF-200-183。
- 結案 `closed-by-decision` 前必查「是否令他處前瞻交棒行失承接目標」（DEF-200-213 教訓）。
- 交棒書「還沒做」節每一筆都要帶詞表詞＋現查指令 code span，否定宣稱要帶 `absent-if` 錨
  ——附指令不算數（R81 §3.2 判例）。上一棒在這裡被 pre-push 擋下一次。
