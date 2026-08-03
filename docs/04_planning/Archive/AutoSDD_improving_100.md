# AutoSDD_improving_100 — C 軌：SD_09 W1 觀察期收斂（mutation pilot 真缺口補測 + 取證校準）

> **柱別**：C 軌（指揮官 AutoClaude 自身能力 / SD_09 工作流帳本）。
> **檔名**：improving_100（improving_99 已結案，tag v2026.06.30-50）。
> **框架版**：v0.30 不變（本輪零碰 AISLDC_SDD 框架本體與 *.tla，預期 ci-gate/五軌 TLC N/A①）。
> **掌舵者裁定**：AskUserQuestion 兩問 →（1）本輪柱別＝C 軌 SD_09 W1 觀察期收斂；（2）收斂路徑＝「品質補強：殺新增 survived mutant＋文件校準」（churn sha／放寬 should_lock 守門均已被 ADR-SD09-009 §11 封死，不採）。

---

## §1　本輪輸入（自上輪繼承）

### 1.1 improving_99 RTM / 實作順序遺留
- improving_99＝B 軌缺陷帳本瘦身，純 monorepo 根 docs/ markdown 重組，零碰程式/框架。無程式遺留 W 項。
- 下一份候選清單（improving_99 §8）：(a) bridge 補 Archy SOP〔A軌〕；(b) **SD_09 W1 觀察期到期、TG 鎖定/退出前置〔C軌〕**；(c) myPrompt Q2 SD_09 推進。→ 掌舵者本輪選 (b)/(c) 合流。

### 1.2 myPrompt.md 待辦（掌舵者本輪輸入來源）
- **Q2**：`SD_Improving_09.md` 是否執行完畢／可否續推？（W1~W6 觀察期閘門）← 本輪正面回應。
- Q1（Nightly 是否續跑）：本輪附帶實證 nightly 仍在跑（`.mutation_history.jsonl` 末筆 2026-06-29、`mutation_backlog_token_guard.md` 2026-06-30 02:03 產出），非本輪主標的。

### 1.3 缺陷帳本 open/routed（階段一複驗）
- 5 個未結追蹤項（DEF-25-001/42-001/42-003/52-006/53-001）與本輪 C 軌 SD_09 標的無直接關聯，非本輪 scope；不重現於本輪變更路徑。

---

## §2　階段一：現況重偵察（Zero-Trust Re-Audit 實測）

### 2.1 基線（硬閘通過）
| 項目 | 命令 | 實測 |
|------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | **3607 passed / 122 skipped / 0 failed**（76.29s，與 improving_99 基線一致，無退化） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** |

### 2.2 SD_09 W1 觀察期真相（zero-trust 親核，推翻記憶與 Explore agent 摘要）
1. **「~6/29 到期」是錯誤心智模型**。ADR-SD09-009 §11.6（PM 拍板 v1.2，2026-05-29）：unique source_sha256 條件是**源碼演進閘門、非時間閘門**——**無日曆到期日**。
2. **觀察期未死鎖、正自然推進**：git log 證 `improving_79`(318c965,6/26)、`improving_80`(ad334c2,6/26)、`improving_84`(a16e591,6/27) 真改了 `token_guard/` 源碼 → unique sha 已從 2 自然長到 **3**（`20940e1b`→`4af78567`→`55013d0a`）。即 §11.6 設計的「W1 active 開發合法改動源碼」路徑。
3. **🔴 mutation pilot 抓到真實風險訊號**：上述改動使 token_guard mutation kill_rate **0.7651 → 0.6956**（survived 35→42，**+7 個未被測試殺死的變異**），距 0.68 effective threshold（`0.75-0.05-0.02`，`mutation_baseline_lock.py:334-335`）僅剩 **1.56pp**。再有一次降覆蓋改動即失守 kill_rate 閘。這正是 mutation pilot 的設計目的。
4. **`should_lock()` 真實判定**（`mutation_baseline_lock.py:313-379`，對 tail 7＝`.mutation_history.jsonl` line 24-30）：
   - kill_rate 閘 `all(≥0.68)`：tail7 最小 0.6956 ≥ 0.68 → **✅ 通過**（Explore agent 誤判「跌破 70%」；門檻是 0.68 非 0.70）。
   - unique sha 閘：tail7 僅 **3 unique** < 7 → `reject reason=sha_not_unique_full` → **❌ 卡關**。
   - 結論：`should_lock=False`，**懸停中**（kill_rate 過、sha 3/7 不過）。
5. **ADR 已封死兩條 Explore agent 建議路徑**（§11 line 231/240）：❌ 禁為衝 sha 而 churn 源碼；❌ 禁放寬 `should_lock` unique sha 守門。
6. **文件 stale（真缺陷 DEF-100-001）**：`AutoClaude/CLAUDE.md` SD_09 摘要停在 R51（2026-06-01）、`G0 最遲 2026-06-26` 已逾期未更新；`.mutation_history.jsonl` 30 筆（非 Explore 報的 31）。

### 2.3 survived mutant 精確定位（查 `.mutmut-cache` sqlite，6/30 02:03）
- 總計 138 mutant（`ok_killed=96 / bad_survived=42`），kill_rate 96/138=0.6956 與 jsonl 吻合。
- **backlog hunk 行號（L47/L72）是 diff 起點，sqlite line_number 才是真實行**（L49/L74）。
- 可殺真缺口（本輪 W-100-1 標的）：
  - **thresholds.py `verify_act_first_ordering` L74**：`if max_tokens <= 0 or autocompact_threshold_tokens <= 0:`（#129-131）。fail-closed 防呆；`max_tokens==0/==1`、`autocompact==0/==1`、`or` 各變異結果可區分 → **可殺**。
  - **watcher.py `observe_token_line` L31**：`if pct is None or pct <= peak_pct:`（#71）。`pct==peak_pct` 且 `pct>=halt_threshold` 時 `<=`→`<` 變異誤觸 halt 更新 → 結果可區分 → **可殺**。
- 等價變異（本輪 W-100-2 誠實標記、不硬殺）：
  - **thresholds.py `should_compact_decision` L49**：`if in_correction_loop and correction_history_len <= 1: return token_pct >= threshold`（#122-124）。到 L49 時 `token_pct>=threshold` 已恆為 True（L48 已 return False 攔掉 `<`），故該分支 ≡ `return True` ≡ 下方 `return True`；`and/or`、`<=/<`、`1/2` 任一變異皆不改最終回傳 → **3 個全為死分支造成的等價變異**，補測試殺不掉。
  - policy.py 30 個（多為 `int/float/bool(payload.get(k, N))` default 常數）+ git_verifier 5 個（log 字串 string_literal）：本輪不碰（Rule 2），列 backlog。

---

## §3　階段二：本輪增量設計

### 3.1 設計主張（一句話）
回應 mutation pilot 抓到的真實覆蓋缺口——補 targeted boundary 測試**殺掉 improving_79/80/84 引入的真缺口 survived mutant**（kill_rate 回升、遠離 0.68 危險線），同時**誠實標記等價變異**並**校正所有 stale 觀察期文件**到 6/30 現況。全程**不改 token_guard 源碼**（保 sha 純淨、零退化、不違 ADR §11.6）。

### 3.2 W 項（≤3，Rule 2）
#### W-100-1：補 boundary 測試殺 4 個真缺口 survived mutant
- 新增測試殺 thresholds `verify_act_first_ordering` #129-131（L74）+ watcher `observe_token_line` #71（L31）。
- 落點：`tests/plugins/token_guard/test_thresholds_mutation.py`、`test_watcher_mutation.py`（既有 mutation 補測檔，additive 追加）。
- **受控突變驗牙**（MUT-100-x）：對每個 mutant 手動套用變異於源碼 → 確認新測試轉紅 → **Edit 還原**（禁 git checkout，[[git-checkout-mutation-revert-hazard]]）。
- **限制誠實標記**：Windows 無法本機跑 mutmut（需 WSL），真實 kill_rate 回升由 nightly（docker）重跑確認；本輪以受控突變證明測試有牙（不阻塞）。

#### W-100-2：觀察期取證校準 + 缺陷帳本
- 校正 `AutoClaude/CLAUDE.md` SD_09 摘要段到 6/30 現況（tail7=3 unique sha、kill_rate 0.6956 仍≥0.68、G0 6/26 已逾期、source-sha＝源碼演進閘門無日曆到期日）；控行數守 CLAUDE.md ≤400 行預算。
- 缺陷帳本 `docs/06_quality/AutoSDD_Defect_Log.md`：
  - **DEF-100-001**（P3 文件，fixed@100）：SD_09 觀察期文件 stale。
  - **DEF-100-002**（P3 品質/設計，routed）：thresholds `should_compact_decision` L49 死分支造成 3 個等價變異；建議下輪評估重構移除冗餘分支（改源碼需驗證對齊 `_should_compact_now` 契約，本輪守 Rule 2/3 不動）。

### 3.3 介面 delta / LOC / importlinter 影響
- **零源碼改動**：只新增測試 + 改文件。token_guard/*.py、core/、ports/、plugins/ 一律不動。
- LOC：測試檔不在 `check_loc_budget.py` 的 SCAN_ROOT（`autoclaude/`）→ 0 影響。
- importlinter：零 import 結構變更 → 8 kept 不變。
- snapshot：零 plugin/port 增減 → 新鮮不變。

### 3.4 <Architecture_Design_Review>
1. **架構純潔性**：無新增模組/God-object；純測試 + 文件，Thin Facade 不受影響。✅
2. **持久化相容**：零 checkpoint/DAL 改動，三後端零停機不受影響。✅
3. **安全防護網**：未新增任何指令生成/CONDITIONAL/對外 I/O 路徑 → 攻防面零變化。✅
4. **對外 I/O 安全**：本輪零新增 `ToolInvocationPort` 外呼路徑。✅
5. **ADR 合規**：不 churn 源碼、不放寬 should_lock → 不違 ADR-SD09-009 §11.6/§11 反作弊。✅

### 3.5 RTM 需求列（實測欄階段三/四回填）
| RTM | 需求 | 測試 | 受控突變 | 實測 |
|-----|------|------|---------|------|
| RTM-100-1 | `verify_act_first_ordering` max_tokens==0 邊界（fail-closed）被精準斷言 | test_thresholds_mutation | MUT-100-1（`<=`→`<`） | 階段三回填 |
| RTM-100-2 | 同上 autocompact_threshold_tokens==0 / ==1 邊界 | test_thresholds_mutation | MUT-100-2（`0`→`1` / `<=`→`<`） | 階段三回填 |
| RTM-100-3 | `or`→`and` 變異被殺（單邊 ≤0 即 fail-closed） | test_thresholds_mutation | MUT-100-3（`or`→`and`） | 階段三回填 |
| RTM-100-4 | `observe_token_line` pct==peak_pct 不重複觸發 halt（boundary） | test_watcher_mutation | MUT-100-4（`<=`→`<`） | 階段三回填 |
| RTM-100-5 | （誠實）`should_compact_decision` L49 分支對結果無影響＝等價變異實證 | test_thresholds（參數化證明） | — | 階段三回填 |

---

## §4　階段三：實作與雙重驗證（已完成）

### 4.1 W-100-1 測試新增（+11，純測試、零源碼改動）
- `tests/plugins/token_guard/test_thresholds_mutation.py`：
  - `TestVerifyActFirstOrderingFailClosedBoundary`（+2）：`test_max_tokens_one_is_valid_not_clamped_to_le_one`、`test_autocompact_one_is_valid_not_clamped_to_le_one` — 殺 #129-131 中 max_tokens/autocompact 的 `0`→`1` boundary（M_b/M_e）。
  - `TestShouldCompactL49DeadBranchEquivalence`（+8，parametrize 2×4）：`test_at_or_above_threshold_always_compacts_regardless_of_correction` — pin 住 L49 死分支等價性（RTM-100-5、DEF-100-002）。
- `tests/plugins/token_guard/test_watcher_mutation.py`（+1）：`test_pct_equals_peak_at_halt_threshold_no_reupdate` — 殺 #71（pct==peak==halt_threshold 邊界，既有測試用 pct=70<門檻殺不掉）。

### 4.2 受控突變驗牙（MUT-100-x，記憶體保留原文 try/finally 還原，遵禁 git checkout 突變還原紀律）
| 突變 | 變異 | 結果 | 判定 |
|------|------|------|------|
| MUT-100-1 | thresholds L74 `max_tokens<=0`→`<=1` | 🔴 RED（test_max_tokens_one 轉紅） | 真缺口被殺 |
| MUT-100-2 | thresholds L74 `autocompact<=0`→`<=1` | 🔴 RED（test_autocompact_one 轉紅） | 真缺口被殺 |
| MUT-100-3 | watcher L31 `pct<=peak_pct`→`<` | 🔴 RED（test_pct_equals_peak_at_halt 轉紅） | 真缺口被殺 |
| EQUIV-CHECK | thresholds L74 `autocompact<=0`→`<0`（M_d） | 🟢 GREEN（38 passed） | **證實等價變異**（殺不掉=非缺口） |
| 還原後複跑 | — | 🟢 34 passed | 源碼乾淨還原 |

→ 證 3 個新測試有牙、殺 #129-131 中 2 真缺口（M_b/M_e）+ watcher #71；M_d 與 L49 #122-124 為等價變異（誠實標記 DEF-100-002）。

### 4.3 行尾還原插曲（§8 誠實記）
受控突變腳本以 Python `write_text` 還原源碼時把原 CRLF 寫成 LF（內容 byte 相同、`git diff -w`/`--stat` 零行變更，但 git 標 modified）。token_guard 源碼本輪**完全不應改動** → 以 `git checkout --` 還原至 HEAD（CRLF），byte-level 乾淨；`git status` 確認 token_guard 源碼消失。教訓：受控突變還原須保留原行尾（binary mode 或 `newline=''`）。

---

## §5　階段四：CI 平價收斂 — 零退化驗證矩陣（floor＝improving_99 實測 3607）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 3607 passed / 0 failed（新測只增不減） | ✅ **3618 passed / 122 skipped / 0 failed**（fresh 清 cache，+11） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | ✅ **8 kept / 0 broken**（零 import 結構變更） |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | ✅ **violations=0**（total=19947 < cap 20438；測試不在 SCAN_ROOT） |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | ✅ **OK**（零 plugin/port 增減） |
| CLAUDE.md 預算 | `tests/contract/test_claude_md_no_long_lines.py` + `loc_budget_check.py` hook | ≤400 行 / 單行 ≤800 **codepoint**（`len(str)`，非 byte） | ✅ **400 行 / max 721cp@L158、L176=705cp**（權威 contract test **4 passed** + hook **exit 0**；注意 L176 utf-8 byte=989，codepoint≠byte，CJK 1cp≈3byte，易被誤判超標——見 §9 假陽性駁回） |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **N/A①** | ✅ N/A①（`git status` 證零碰 AISLDC_SDD/、僅 tests/+docs/+CLAUDE.md） |
| DAL 等價 | equivalence job | **N/A②** | ✅ N/A②（`tests/equivalence/` 隨全套 3618 通過、本輪無新 DAL/checkpoint 改動） |
| 五軌 TLC | `bash scripts/ci-gate.sh --full-tlc` | **N/A①** | ✅ N/A①（`git status` 證零碰 *.tla/*.cfg/FSM/_HAPPY_PATH） |

---

## §6　缺陷帳本本輪處置
- DEF-100-001（P3，文件 stale，fixed@100）；DEF-100-002（P3，等價變異/死分支，routed 下輪重構評估）。
- 上輪 routed 項進度：本輪不觸及，維持原狀態。

---

## §7　Copy-on-Evolve / 版本演化
- 本輪零碰 AISLDC_SDD 框架本體 → **不觸發 Copy-on-Evolve**，框架版維持 v0.30。

---

## §8　誠實性標記
1. **Windows 無法本機跑 mutmut（需 WSL）**：真實 kill_rate 回升由 nightly（docker `run_mutmut_in_docker.sh`）下次重跑確認；本輪以**受控突變 MUT-100-1~3 全紅**證明新測試確能殺對應變異（不阻塞、機制等價）。預期下次 nightly 同 sha（55013，測試不算入 plugin 目錄 sha）下 killed 96→99、kill_rate 0.6956→~0.7174，遠離 0.68 危險線；unique sha 仍 3/7（本輪不改源碼、不衝 sha，符 ADR §11.6）。
2. **N/A 兩型精確區分**（誠實紀律）：
   - **類型①「條件未觸發、本輪確實未跑」**：ci-gate / 五軌 TLC — `git status` 鐵證零碰 `AISDLC_SDD/`、`*.tla`、`*.cfg`、FSM、`_HAPPY_PATH`；TLC 不在 pytest 全套、需 Java。
   - **類型②「既有測試隨全套已跑通過、本輪無新契約」**：DAL 等價 — `tests/equivalence/` 諸測試隨全套 3618 passed 通過，本輪無新 DAL/checkpoint 改動故無新增 round-trip 契約。
3. **行尾還原插曲**（見 §4.3）：受控突變腳本 Python `write_text` 還原把 CRLF→LF，已以 `git checkout --` byte-level 還原至 HEAD，`git status` 確認 token_guard 源碼零殘留 → 「零碰源碼、sha 不變」成立。
4. **本輪未讓觀察期「結束」**：只提升 kill_rate 安全邊際 + 校準文件，unique sha 仍待未來 token_guard 源碼自然演進（或 PM 拍板 TG 退出降 SD_10）。觀察期收斂的**最終出口仍需 PM 決策**（HUMAN_PENDING，不可自動跳過）——本輪把狀態變誠實可見、為該決策提供乾淨依據。

## §9　多專家 Zero-Trust 審查閉環（三鏡全 OVERALL PASS）

序列化派發避互踩：先 Architect + SA-SD 並行（唯讀靜態、不跑全套），回報後再 QA 獨佔（跑全套 + 受控突變）。全程主樹派發（含 untracked 計畫書，遵 DEF-24-001 禁 worktree）。

### 9.1 Architect（技術 PASS）
零源碼改動（`git diff` token_guard byte-level 空）、零新 plugin/port/God-object；ADR §11.6 合規（`should_lock` 未改、未 churn sha）；L49 死分支等價變異推導正確、#129-131/#71 真缺口判定正確；N/A①② 鐵證；測試風格符規。

### 9.2 SA-SD（文件 vs 實況 PASS）
§2.2 五點真相逐項磁碟核實全通過（tail7=3 unique sha、kill_rate 0.6956≥0.68、threshold 0.68、ADR §11.6 源碼演進閘門、improving_79/80/84 git log）；缺陷帳本 DEF-100-001/002 誠實；myPrompt Q2 回應充分；RTM 一致、N/A 兩型精確。

### 9.3 QA（對抗，OVERALL PASS P0=P1=P2=0）
獨佔清 cache 跑全套 **3618 passed / 122 skipped / 0 failed**；受控突變三測試真有牙（套變異→FAIL、還原→PASS，**byte-level 乾淨無殘留**）；新測試非空殼（實質 assert + Rule 9 docstring）；等價變異實證正確（L49 #122-124 套 and→or/<=/</1→2 皆維持綠、M_d 等價確認）；kill_rate 96/138 核算；帳本 DEF-100-002 routed 非謊稱 fixed。

### 9.4 🔴 假陽性駁回（findings 經親核複審）
**Architect 與 SA-SD 各報一個 P1「CLAUDE.md 單行超 800」**（Architect L176=892、SA-SD L158=872/L176=989）——**經 parent 親核駁回為假陽性**：
- 兩鏡把 **UTF-8 byte 數誤當 codepoint**（L176 utf-8 byte=989、codepoint=`len(str)`=**705**；CJK 1cp≈3byte）。
- 權威判準＝`tests/contract/test_claude_md_no_long_lines.py:22` 明文「**MAX_LINE_CHARS=800，codepoint 計，非 UTF-8 byte 數**」。實跑：contract test **4 passed** + `loc_budget_check.py CLAUDE.md` **exit 0**。
- 反證：L158 是本輪未改的 improving_07 段，若真 >800 早破 CI（基線綠）→ 證 byte 計法誤判。
- QA 鏡（第三鏡）獨立以權威 contract test 複核，確認**無 P0/P1**，與駁回一致。
- **教訓**（[[no-fabricated-tool-output]] 反向 + Nightly #17 家族）：audit agent 的 finding 本身須 zero-trust 親核；「codepoint vs byte」是 CJK 文件易踩的計法陷阱，務必以權威測試裁決、勿信 agent 自數的 byte。
- 連帶校正：計畫書 §5 原估「L176 775cp」校正為實測 **705cp**（結論「<800」不變，估值偏高已訂正）。

### 9.5 結案判定
三鏡技術面全 PASS、唯二 P1 為計法假陽性已駁回、無真實未修缺陷 → **准予結案**。
