# AutoSDD_ZeroTrust_Audit_94 — 多專家 Zero-Trust 審查證據

> 對應 `docs/04_planning/AutoSDD_improving_94.md`（PRD→playbook 專職 agent + 三層橋接，A/B/C 三軌）。
> 審查方式：三鏡（Architect / SA-SD / QA）並行於**主樹**派發（本輪多為未 commit 的 untracked 新檔
> ——v0.28、compiler、新測——依 DEF-24-001 鐵律禁 worktree，否則看不到新檔產生假陰性）。

---

## §1 階段一基線（零退化硬閘，2026-06-27 實測）
- AutoClaude 全套：**3563 passed / 0 failed / 122 skipped**（68.68s）= 上輪 floor → 硬閘 PASS。
- lint-imports：8 kept / 0 broken；LOC：total=19885 / violations=0（cap 20438）；snapshot：OK。
- AISDLC_SDD ci-gate（基線）：exit 0；v0.01 1478 + v0.27 1665 + scripts 129 = 3272 passed / 0 failed。

## §2 三鏡初審結論

| 鏡 | OVERALL | P0 | P1 | P2 | P3 |
|----|---------|----|----|----|----|
| **QA**（親跑複核數字 / 攻防真實性 / 誠實性） | **PASS** | 0 | 0 | 0 | 0 |
| **Architect**（架構純潔 / 紅線 / 消毒 / 潔淨度） | **PASS** | 0 | 0 | 1 | 0 |
| **SA-SD**（設計 vs 實作一致 / RTM / 註冊一致） | **FAIL→修後 PASS** | 0 | 0 | 1 | 2 |

### 2.1 QA 鏡（PASS，親跑實測）
- 新 compiler 單測 `26 passed`；9 條 evaluator 注入攻防確認**非空殼**（parametrize 真展開 + `pytest.raises`）。
- 零退化全套親跑 **3589 passed / 0 failed / 122 skipped**（floor 3563 + 26 新測），skip 未暴增、無偷塞 skip。
- 安全攻防親自繞過測試檔直呼 `sanitize_evaluator`：8 注入字串全 BLOCKED、合法 `pytest`/`python -m` 放行。
- 向後相容三檔合跑 `166 passed / 15 skipped`（skip=PG-real）。
- 誠實性：五軌 TLC 標 N/A 第一種（`git diff` 證零碰 tracked `*.tla`/FSM；v0.28 內 5 個 .tla 為 Copy-on-Evolve
  整批複製的 untracked 新檔、非修改既有形式化規格，標註區分正確）；DAL 等價 N/A 第二種（無 repositories/checkpoint
  改動、equivalence 隨全套通過）。**無假數字、無空殼測試。**

### 2.2 Architect 鏡（PASS，1 P2 建議加固）
- additive 真實性 PASS：兩 model 新欄皆 `Optional=None`、不動既有欄位與建構子（git diff 逐位元確認）。
- 架構紅線 PASS：compiler 在 `tools/`（非 autoclaude/）不受 importlinter 約束；import autoclaude.models 合法單向；
  無 God-object；playbook_runner thin facade 未碰；**grep 全套確認 runner 不消費 goal_task_id**（純彙總用資料攜帶）。
- 不重複既有模型 PASS：Playbook 本體未加平行 goals[]，走「重用 three_tier + 攤平」路線。
- 消毒強度 PASS：對齊 `sdd_to_playbook_adapter._DENY` 且更嚴；實測 16 向量 fail-closed。
- Copy-on-Evolve 潔淨度 PASS：v0.28 runtime 產物（__pycache__/build/reports/formal/states/arch-fitness.json）
  雖在磁碟但 `git check-ignore` 確認全被 .gitignore 攔住，git tracked 零漏網。
- **P2（建議加固）**：`_EVAL_SAFE` 用 `\s` 含 tab → `python\t-c\t...` 可繞首 token 白名單塞任意旗標。

### 2.3 SA-SD 鏡（初審 FAIL，1 P2 + 2 P3）
- 設計 vs 實作 PASS（§3.3 攤平規則逐條對照實作命中）；RTM-94-1~7 全覆蓋；新 agent 與 Compily 防混淆清楚；
  規格先行成立（§1-3 事前設計、§4/5 回填分離）。
- **P2（真缺陷）**：`v0.28/agent/README.md:77` 與 `:246` 仍寫「19 個 Specialized / 5 系統級 runtime」，
  磁碟實為 20、INIT/EVOLUTION_LOG/CHANGELOG 皆已 20 → 四檔數字不一致（RTM-94-6「三處註冊一致」未達成）。
- **P3**：EVOLUTION_LOG/CHANGELOG/§3.2 稱新 agent 登記於 INIT「auto_load_config 表列」，實際在 Specialized
  清單表（auto_load_config 場景載入區未納，對 cross-scenario bridge 合理但措辭不實）。
- **P3**：§3.3 / docstring 寫 `name = title + " / " + action[:N]`，實作 `_name_for` 是對整串做 max_len=80
  截斷，語意等價但字面不符。

## §3 修復（當輪修完，遵「不要無謂延後」紀律，全 PASS 才結案）

| 缺陷 | 修復 | 證據 |
|------|------|------|
| **DEF-94-001**（P2，Architect）evaluator 消毒 `python -c`/tab 繞過 | `_EVAL_SAFE` `\s`→半形空格（擋 tab）；首 token=python 時禁 `-c`（任意碼）。只放行 `python -m` 形態 | `tools/three_tier_to_playbook.py:57-60,81-93`；新增 3 攻防 case + 1 放行 case，`test_sanitize_evaluator_rejects_injection` **13 passed**（含 `python\t-c`、`python -c "..."`、`python -c print(1)` 全 BLOCKED、`python -m pytest` 放行） |
| **DEF-94-002**（P2，SA-SD）README count 未同步 | `:77` `:246` 19→20 + 「4 runtime + 2 橋接 agent」措辭校正 | `v0.28/agent/README.md:77,246` 皆 20，與 INIT/EVOLUTION_LOG/CHANGELOG/磁碟一致 |
| **DEF-94-003**（P3，SA-SD）措辭不實 ×2 | ①「auto_load_config 表列」→「Specialized Agents 清單表列」+ 註明 bridge 不綁場景；②§3.3 name 截斷描述改「(title / action) 經 max_len=80 有界截斷」 | EVOLUTION_LOG / CHANGELOG / improving_94 §3.2/§3.3 |

> Architect 的 P2 雖評「可接受權衡（非阻擋）」，但屬「從文件生成指令」架構紅線範疇 + 修復成本低，依
> [[no-defer-unless-justified]] 當場修不延後，並補回歸鎖。

## §4 修復後複驗（2026-06-27）
- 新 compiler 單測：**30 passed**（26 + 3 注入 + 1 放行）；ruff E/F/I All checks passed。
- 注入測試逐 case：12 向量全 BLOCKED（含新 tab/python -c ×3）+ `python -m pytest` 放行 → 13 passed。
- README count：`:77` `:246` 兩處皆「20 個 Specialized」，四檔（README/INIT/EVOLUTION_LOG/CHANGELOG）+ 磁碟一致。
- 零退化全套（修復後最終態）：**3593 passed / 0 failed / 122 skipped**（70.90s；floor 3563 + 30 新 compiler 測）。
- ci-gate v0.28：exit 0；v0.01 1478 + v0.28 1665 + scripts 129 = 3272；LATEST 切 v0.28、skills SSOT 59 一致、router 覆蓋 OK。
- 入庫潔淨度：`git add -A -n` → v0.28 863 檔、零 runtime/stale 產物。

## §5 結論
- 三鏡 SA-SD 初審 FAIL 之 P2/P3 全數當輪修復並複驗；Architect P2 加固完成。**修復後三鏡判定全 PASS、P0=0/P1=0。**
- 本輪缺陷誠實入帳（DEF-94-001/002/003，皆 fixed@improving_94，由 zero-trust 三鏡抓出、commit 前修畢）——
  **非「零新缺陷」**，而是「審查閉環抓出本輪自身引入的 3 個問題並當輪修掉」。
- 上輪 open/routed 缺陷（DEF-19-001 / DEF-23-005 / DEF-01-007 / DEF-62-001 / DEF-01-009）皆 P3，本輪未觸碰其標的，維持原狀態。
