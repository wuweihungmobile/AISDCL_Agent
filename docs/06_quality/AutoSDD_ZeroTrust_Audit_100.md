# AutoSDD ZeroTrust Audit 100 — C 軌 SD_09 W1 觀察期收斂

> 對應計畫書 [AutoSDD_improving_100.md](../04_planning/AutoSDD_improving_100.md)（§9 含同源摘要）。本檔留三鏡原始證據 + 假陽性駁回鐵證。

## 0　審查範圍與分工
- 本輪改動：純測試（+11）+ 文件，**零碰 autoclaude/ 源碼**。
- 序列化派發避 [[parallel-mutation-audit-collision]]：先 Architect + SA-SD 並行（唯讀靜態、不跑全套）→ 回報後 QA 獨佔（跑全套 + 受控突變）。
- 全程主樹派發（含 untracked 計畫書，遵 DEF-24-001 禁 worktree）。

## 1　階段一基線（硬閘通過）
| 項目 | 命令 | 實測 |
|------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | 3607 passed / 122 skipped / 0 failed |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken |

## 2　三鏡 Zero-Trust 結論

### 2.1 Architect（技術 PASS，P0=0/P1實=0/P2實=0）
- 零源碼改動：`git diff` token_guard byte-level 空；零新 plugin/port/God-object。
- ADR §11.6 合規：`should_lock`（`mutation_baseline_lock.py:313-383`）本輪未改、未 churn sha。
- 等價變異推導正確（L49 死分支）、#129-131/#71 真缺口判定正確。
- N/A①②鐵證、測試風格符規。

### 2.2 SA-SD（文件 vs 實況 PASS）
- §2.2 五點真相逐項磁碟核實全通過：tail7=3 unique sha、kill_rate 0.6956（96/138）、effective threshold 0.68（`0.75-0.05-0.02`）、ADR §11.6 源碼演進閘門、improving_79/80/84 git log 改 token_guard。
- 缺陷帳本 DEF-100-001（fixed@100）/002（routed）誠實；myPrompt Q2 回應充分；RTM 一致、N/A 兩型精確。

### 2.3 QA（對抗，OVERALL PASS P0=0/P1=0/P2=0）
- 獨佔清 cache 跑全套：**3618 passed / 122 skipped / 0 failed**。
- 受控突變回歸鎖真有牙（bytes 級替換保 LF）：

| 變異 | 目標測試 | 套用後 | 還原後 |
|------|---------|--------|--------|
| thresholds `max_tokens<=0`→`<=1` | test_max_tokens_one_is_valid… | FAIL | PASS |
| thresholds `autocompact<=0`→`<=1` | test_autocompact_one_is_valid… | FAIL | PASS |
| watcher `pct<=peak_pct`→`<` | test_pct_equals_peak_at_halt… | FAIL | PASS |

- 還原 byte-level 乾淨（`git diff --quiet autoclaude/plugins/token_guard/` rc=0）；新測試非空殼（實質 assert + Rule 9 docstring）。
- 等價變異實證：L49 套 #122/#123/#124 三變異 8 passed 不變、M_d（`autocompact<=0`→`<0`）套用後 token_guard slice 253 passed → 確認等價。
- kill_rate 96/138=0.6956 核算；帳本誠實（DEF-100-002 routed 非謊稱 fixed）。

## 3　🔴 假陽性駁回（finding 經親核複審）
**Architect 與 SA-SD 各報一個 P1「CLAUDE.md 單行超 800」**（Architect L176=892、SA-SD L158=872/L176=989）—— **經 parent 親核駁回為假陽性**：

| 證據 | 內容 |
|------|------|
| 權威定義 | `tests/contract/test_claude_md_no_long_lines.py:22`：「MAX_LINE_CHARS=800，codepoint 計，**非 UTF-8 byte 數**」 |
| 計法誤判 | 兩鏡把 UTF-8 byte（L176=989）誤當 codepoint；真 codepoint=`len(str)`=**705**（CJK 1cp≈3byte） |
| 權威裁決 | `test_claude_md_no_long_lines.py` **4 passed** + `loc_budget_check.py CLAUDE.md` **exit 0** |
| 反證 | L158 是本輪未改的 improving_07 段，若真 >800 早破 CI（基線綠）→ 證 byte 計法誤判 |
| 第三鏡複核 | QA 鏡以權威 contract test 獨立複核，確認無 P0/P1，與駁回一致 |

**教訓**（[[no-fabricated-tool-output]] 反向 + Nightly #17 家族）：audit agent 的 finding 本身須 zero-trust 親核；「codepoint vs byte」是 CJK 文件易踩計法陷阱，以權威測試裁決。

## 4　結案判定
三鏡技術面全 OVERALL PASS、唯二 P1 為計法假陽性已駁回、無真實未修缺陷 → **准予結案**（commit 8aca634、tag v2026.06.30-51）。
