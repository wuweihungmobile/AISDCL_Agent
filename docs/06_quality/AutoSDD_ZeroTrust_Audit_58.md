# AutoSDD ZeroTrust Audit 58 — B 軌框架缺陷補救（ci-gate 帶紅入庫修復 + 根因硬化）

> **日期**：2026-06-24 ｜ **對應計畫**：`docs/04_planning/AutoSDD_improving_58.md`
> **審查範圍**：improving_57 遺留的 ci-gate 紅破口（DEF-58-001）、`copy_on_evolve.sh` 根因硬化（DEF-58-002）、取證紀律教訓（DEF-58-003）。
> **取證紀律**：全程退出碼以 `; echo $?` / `>/dev/null 2>&1; echo $?` 取，**絕不經 `| tail` 等管線遮蔽**（本輪即因 improving_57 用 `| tail` 遮蔽退出碼假報綠而起）。

---

## 1. 階段一 zero-trust 重偵察（parent 親跑，退出碼不遮蔽）

| 項目 | 命令 | 實測 | 結果 |
|------|------|------|------|
| git 完整性 | `git status / log` | 工作區乾淨、HEAD=e9e2e59、自 improving_57 位元級零變更 | ✅ |
| AutoClaude 全套 | `python -m pytest tests/ -q` | 3265 passed / 122 skipped / 0 failed | ✅ |
| lint-imports | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | ✅ |
| LOC / snapshot | `check_loc_budget` / `snapshot_sync --check` | violations=0 / fresh | ✅ |
| **AISDLC_SDD ci-gate** | `bash scripts/ci-gate.sh > log 2>&1; echo $?` | **1** | ❌ **RED** |
| 戳記 lint 直驗 | `skill_header_sync.py --check; echo $?` | **1**（45 處 v0.22 戳記停 v0.21） | ❌ |

### 根因鐵證鏈
1. `git show e9e2e59:AISLDC_SDD/AISDLC_SDD_v0.22/.claude/skills/README.md` → `**版本**: v0.21-SDD`：improving_57 commit 當下 v0.22 戳記即停 v0.21（建版後從未 `skill_header_sync --write`）。45 處 v0.21 戳記。
2. `copy_on_evolve.sh`（建版腳本）無戳記同步步驟 → 同步係人工後步驟，DEF-CLDREV-007（v0.19）首犯、本輪 DEF-58-001（v0.22）二犯。
3. improving_57 §5 第 91 行宣稱「ci-gate exit 0」與真實 exit=1 矛盾；成因＝`bash ci-gate.sh | tail`（§77 可見）回傳 tail 退出碼遮蔽 ci-gate 真實 1（[[no-fabricated-tool-output]] 取證陷阱）。

### 三軸成熟度（Explore agent 實測複核）
SLV 升 trust_level 必人工（`_SLV_AUTO_PROPOSE_ENV` 預設 OFF）、meta_halt/ChurnBounded/GraduationRatchet 機具齊全但環變數全預設 OFF（opt-in 鷹架）、decision_trace 空、無自動改自身治理規則並落地之路徑。**C=L5 / B=L4 / A=L4 → `L_合體=L4`，本輪維持（補救輪不推進）**。

## 2. 修復摘要

| 缺陷 | 修復 | 證據 |
|------|------|------|
| DEF-58-001（P2） | `skill_header_sync --write`（45 戳記→v0.22）+ `sync_exposed_skills --write`（59 鏡像重生） | 兩 lint `--check` exit 0；git diff 每檔僅戳記行變更 |
| DEF-58-002（P1 根因） | `copy_on_evolve.sh` 建版後自動 `--write`（fail-loud + sibling guard + 顯式 --repo-root） | §3 三鏡 + M-W582 突變 |
| DEF-58-003（P2 流程） | 取證教訓：閘門退出碼絕不經 `\| tail`；本輪全程 `echo $?` | 計畫書 §2.2/§5 |

## 3. 三鏡 zero-trust 複審結果（主樹並行，全為 tracked 檔修改、無 untracked 新檔 → 無 DEF-24-001 worktree 陷阱）

| 鏡 | OVERALL | P0 | P1 | P2/P3（advisory，非阻擋） |
|----|---------|----|----|--------------------------|
| **QA** | ✅ PASS | 0 | 0 | P3：修復尚未 commit（流程提醒）。**獨立重做 M-W582 突變（紅→還原 9 passed、grep 零殘留）、重跑 ci-gate EXIT=0、AutoClaude 3265/0、核實 improving_57 假綠屬實（45 處 + §91 矛盾）** |
| **SA-SD** | ✅ PASS | 0 | 0 | P2-1：同步失敗留半成品目錄（fail-loud + 拒覆蓋 guard 保護，安全）；P2-2：guard 未檢 rfc_lifecycle_lint.py 相依（缺則 ImportError 仍 fail-loud 非假綠）。確認注入面零、`set -e` 不遮蔽、--repo-root 等價且更穩健、guard 雙向正確無假陰性 |
| **Architect** | ✅ PASS | 0 | 0 | 無（CRLF 警告為 Windows 換行慣例、無關）。確認就地修 LATEST v0.22 合規（不該新建 v0.23）、v0.01~v0.21 凍結零污染、scripts/ shared infra 免規、無 `*.tla` 變更免 TLC、92 M 清單純淨無 runtime/stale 誤入 |

**三鏡一致 OVERALL PASS、P0=P1=0**；P2/P3 皆 advisory（fail-loud 安全權衡 / 流程提醒），**無需本輪修復**。

## 4. 階段四零退化矩陣（parent 親跑，退出碼不遮蔽）

| 檢查 | 實測 | 結果 |
|------|------|------|
| AutoClaude 全套 | 3265 passed / 122 skipped / 0 failed（本輪零 AutoClaude 變更） | ✅ |
| lint-imports | 8 kept / 0 broken | ✅ |
| LOC / snapshot | violations=0 / fresh | ✅ |
| **AISDLC_SDD ci-gate** | `CIGATE_EXIT=0`；v0.01:1478 / v0.22:1655 / scripts:**128**（+1 新測試） | ✅ |
| 戳記/鏡像 lint | `skill_header_sync --check`=0、`sync_exposed_skills --check`=0 | ✅ |
| copy_on_evolve 測試 | 9 passed（8 既有 + 1 新 auto-sync 意圖鎖） | ✅ |
| 五軌 TLC | 免（無 `*.tla`/`_HAPPY_PATH`/transition_rules 變更，git 證零差異） | N/A |

## 5. 受控突變實證（Rule 9 非空殼）

- **M-W582**：`copy_on_evolve.sh` auto-sync guard 改 `if false && …`（停用同步）→ `test_auto_syncs_skill_stamps_on_evolve_def_58_002` 轉紅（新版戳記停 v0.01：`assert '...v0.02' in '...v0.01'` 失敗）→ 還原後 9 passed、`grep MUTATION` 零殘留。**QA 鏡獨立重做確認**。

## 6. 結論

improving_58 = **B 軌框架缺陷補救輪，OVERALL PASS**。誠實揭露 improving_57 以 `| tail` 遮蔽退出碼假報 ci-gate 綟、實為帶紅入庫；本輪 (1) 修復 45 戳記 + 59 鏡像使 ci-gate 真實轉綠、(2) 根因硬化建版腳本杜絕復發、(3) 立取證教訓。零退化恢復、無凍結本體被誤動、無 `*.tla` 變更。合體成熟度維持 L4（補救輪不推進）。
