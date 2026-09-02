# PRD 修訂案 R121：無人看管續跑的 commit／push 授權

- **Status**：Proposed（待掌舵者核准生效＋四方複審；核准後落款版號由 PRD 修訂表次序決定）
- **日期**：2026-09-02
- **提案人裁決依據**：`AutoSDD_Adjudication_Record_R121_AutoResume.md`（掌舵者 2026-09-02 選「全自動：連 commit/push 都自己來」）
- **修訂標的**：PRD `docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` §4.5.4（喚醒指令授權面）與 §13（安全紅線）
- **對應缺陷／設計**：DEF-200-231、[ADR-XPLAT-014](ADR/ADR-XPLAT-014-resume-chain-hardening.md) §3（本案**超出**該節建議案 B，故需修憲）

## 1. 為什麼要修憲（不是改一行就好）

ADR-XPLAT-014 §3.4 建議案 B（`--permission-mode acceptEdits`）**刻意保留** commit／push 封鎖：無人續跑那一跑能改檔，但 `AUTOSDD_UNATTENDED=1` 配 `lint_powershell_command.py`／`block_destructive_git.py` 擋住 git／gh 的寫入型子指令。PRD §4.5.4／§13 明文「移除完全跳過權限的預設」「只有隔離環境＋使用者明確設定才可跳過」。

掌舵者要的「連 commit/push 都自己來」＝解除該封鎖的一部分。這動到 PRD 最高法，故走修憲，不得以行內豁免或直接關 `AUTOSDD_UNATTENDED` 了事（那是方案 F 裸形態，PRD 禁）。

## 2. 提案條文（擬新增 PRD §4.5.11「無人續跑的受控 commit／push」）

無人看管續跑那一跑（`claude -p -r`，`AUTOSDD_UNATTENDED=1`）在**同時滿足下列全部護欄**時，得執行 `git commit` 與 `git push`；任一不成立則退回方案 B（可 commit 到本地、**不得 push**，留給人確認）：

- **G-a 綠燈前提**：該輪的本機全套閘門（`tools/run_root_unittests.py` 等對應閘門）本次執行 rc=0，且 pre-push 全套將自然再跑一次（不得帶 `--no-verify`／`AUTOCLAUDE_SKIP_HOOKS`／`AUTOSDD_*_GUARD_OFF`）。
- **G-b 複審前提**：該輪標的已通過四方定點複審且無未收斂 blocking（複審紀錄落磁碟、可稽核）；未過複審的變更**只 commit 不 push**。
- **G-c 毀滅性仍禁**：`block_destructive_git.py` 射程（reset --hard／clean／stash／checkout -- 等）與 `push --force`／`branch -D`／`git rm` **一律仍禁**，本案只解除「正常 commit＋非 force push 到 main」。
- **G-d 治理面仍唯讀**：PRD §15.5 紅線 10 的保護面（PRD／ADR／governance 規則檔）在無人看管下維持唯讀，本案不動。
- **G-e 出口可關且模型碰不到**：沿用環境變數形狀（新增 `AUTOSDD_UNATTENDED_PUSH_OFF`，須啟動前設；不新增旗標），設了即退回方案 B。
- **G-f 全程留痕**：每一次自動 commit／push 落稽核痕跡（sha、rc、觸發輪、複審紀錄座標），「自動推了什麼」事後必查得到。

## 3. 最壞情況與補救（掌舵者已於裁決簽收「可接受」的延伸）

- **最壞情況**：無人續跑把一批已過本機閘門＋四方複審的變更推上 main，而其中仍有複審與閘門都沒抓到的缺陷。
- **補救成本**：`git revert <sha>`（不改寫歷史）；雲端 CI 五支為第二道網（push 後仍會跑）。
- **與方案 B 的差別**：方案 B 最壞是「改錯檔、早上才看到」，本案多一層「推錯到 main」；G-a／G-b 兩道前提把它壓到「已通過閘門＋複審的變更」才會被自動推，風險面等同一次有人在場的正常 push。

## 4. 需掌舵者裁決

- **Q-A**：G-a～G-f 六道護欄是否足夠？是否要加碼（例：自動 push 僅限特定分支／僅限特定輪型）或放寬（例：免四方前提）？
- **Q-B**：`AUTOSDD_UNATTENDED_PUSH_OFF` 這個關閉出口的預設方向＝**預設允許自動 push（需護欄全綠）**，設變數才關。可否？
- **Q-C**：本案落地屬安全關鍵，是否同意「先落地方案 B（改檔不推）＋本案護欄程式，最後一步四方複審專審 commit/push 授權面」的順序？

## 5. 落地依賴

本案程式落地依賴 ADR-XPLAT-014 §7 的 ⓿→①③→② 先成立（醒得來、醒在對的時刻、能改檔），commit/push 授權是續跑鏈的**最後一段**；前段未成立時本案無作用點。
