# AutoSDD_ZeroTrust_Audit_78 — improving_78 W-78-1（DEF-78-001 halt 接線）零信任審計

> 對應計畫書 [docs/04_planning/AutoSDD_improving_78.md](../04_planning/AutoSDD_improving_78.md)。本輪＝C 軌指揮官 AutoClaude 缺陷修復輪（production Kernel token-guard halt 編排接線）。

## 1. 階段一硬閘（parent 親跑）

| 項目 | 命令 | 實測 | 證據 |
|------|------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | **3407 passed / 122 skipped / 0 failed**（70.18s, exit 0） | bg task bqki2gkuy；= improving_77 floor |
| lint-imports | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** | bg task bj3x6ctjy |

硬閘 PASS（基線無退化、無 failed）。

## 2. 階段二零信任揭露 DEF-78-001（直讀生產碼，非採信 agent）

掌舵者核准「DEF-76-001 production marker」後，parent 零信任直讀生產碼坐實 marker 補點時，揪出更根本的缺陷：

| 事實 | 鐵證 |
|------|------|
| Kernel 呼叫 executor 不傳 on_event | `core/kernel.py`（改前 `_run_step` execute 無 on_event 參數） |
| POST_ATTEMPT payload 無 token_pct | `kernel.py:238-242` → `token_guard/policy.py:158` token_pct=0.0 → should_halt/compact 恆 False |
| Kernel 零消費 request_compact | kernel.py 改前僅 :248 消費 request_halt |
| 全 codebase 零 ON_TOKEN_USAGE emit 端 | grep 僅 4 subscriber（含死碼 `save_token_halt`），改前無 emitter |
| compact/halt 真實邏輯在棄用路徑 | `prompt_dispatcher.py`(取 PlaybookRunner) / `_impl.py:233`(TOKEN_COMPACT) / `_token_halt.py:46`(TOKEN_HALT) |
| production 主路徑 | `main.py:138` AutoResumeService.run → kernel.run（無 path） |

**結論**：production Kernel 路徑從未接 token-guard 編排（compact/halt 死碼），token 壓力全交 executor act-first + CLI autocompact。經三段 AskUserQuestion 重新切分：B 完整接線 / 路徑層+純 Kernel / halt 先行。

## 3. 三鏡複審結論（皆主樹派發，DEF-24-001：本輪有 untracked 新檔禁 worktree）

| 鏡 | 結論 | 重點 |
|----|------|------|
| **Architect** | OVERALL PASS（P0=0/P1=0） | Kernel 維持純 DAG（新增屬既有 emit-phase + honor-request_halt 角色，無 /compact 誤入）；8 kept；LOC 0；無雙寫（Kernel emit payload 不帶 request_halt → 舊 save_token_halt 不觸發）；playbook_runner 未碰 |
| **SA-SD** | OVERALL PASS（P0=0/P1=0；親跑 3421/0） | 根因屬實（grep 證改前零 emit）；halt 接線正確（92→HALT/50→前進/85→compact 區間誠實不動作無 overclaim）；零退化機制 peak=0 不 emit 成立；防退化 gate 無漏洞；測試用真 TokenGuardPlugin 驗意圖 |
| **QA** | OVERALL PASS（P0=0/P1=0） | 獨立全套 **3421/122/0**；8 kept；LOC 0；snapshot OK；獨立突變 (a)(b) 轉紅 Edit 還原無殘留；零碰 AISDLC_SDD；無 skip/xfail；退化點 multi_halt 綠 |

### P2 處置（皆已修或記錄，遵 [[no-defer-unless-justified]]）
- SA-SD P2-1（計畫 §3「CheckpointPlugin public API」措辭不精確）→ **已修**：訂正為「直走注入之 IStateRepository.save_checkpoint，非經 CheckpointPlugin」並補無雙寫說明。
- SA-SD/Architect P2-2（舊 `save_token_halt` ON_TOKEN_USAGE handler 接線後仍死碼）→ **已於計畫 §3.2 註明**由 AutoResumeService 路徑取代其職責。
- Architect P2（最小 checkpoint 不持久化跨 session 計數器 / SDK pct float 防禦）→ 限制已於帳本+docstring 揭露；float 防禦由 executor adapter callback 邊界 try/except 兜底（Rule 2：不加 speculative dead defensive code）。

## 4. 受控突變實證（非空殼）

| 突變 | 對應測試轉紅 | 還原 |
|------|------------|------|
| MUT-78-1 kernel `if tu.request_halt:`→`and False` | test_kernel_token_halt（halt 不發生） | Edit 還原復綠 |
| MUT-78-2 observer `if pct>peak`→`and False` | test_token_observer（peak 不更新 2 紅） | Edit 還原復綠 |
| MUT-78-3 auto_resume `step_idx=…else 0`→`=0` | test_auto_resume_halt_persist（step_idx 2 紅） | Edit 還原復綠 |

全程 Edit 還原（禁 git checkout，本輪有 untracked 新檔，遵 [[git-checkout-mutation-revert-hazard]]）；`grep MUT-78` 無殘留；QA 鏡獨立重做 (a)(b) 亦轉紅還原。

## 5. 退化修復誠實記錄

首次全套 **2 failed**（test_kernel_resume_multi_halt）——`_persist_halt_checkpoint` 原對所有 halted 觸發，`halt_step_idx is None`（既有 halt 路徑已自存 checkpoint）退回 step_idx=0 覆蓋正確 checkpoint。修復＝gate `halt_step_idx is not None`（只對本輪新接線 token-observer halt 生效）+ 補回歸測。修後全套復綠 3421/0。

## 6. 結案四件套

1. `docs/04_planning/AutoSDD_improving_78.md`（計畫/設計/RTM/實測）
2. 本檔 `docs/06_quality/AutoSDD_ZeroTrust_Audit_78.md`
3. `docs/06_quality/AutoSDD_Defect_Log.md`（DEF-78-001 partially-fixed + DEF-76-001 framing 澄清，跨輪累積）
4. 生產碼 + 測試（`autoclaude/core/_token_observer.py`、kernel.py、kernel_state.py、auto_resume.py + 3 新測檔 + fake on_event 一致性）

全閉環 PASS，准結案。
