# AutoSDD improving_58 — B 軌框架缺陷補救：v0.22 戳記 bit-rot 致 ci-gate 帶紅入庫（根因硬化 Copy-on-Evolve）

> **軌道定位**：軌道① **B 軌（柱②手腳 AISLDC_SDD）框架缺陷補救輪**。**非成熟度推進**——本輪修復 improving_57 遺留的零退化破口並根除其復發路徑。
> **下一份**：`AutoSDD_improving_59.md`（按需）。**日期**：2026-06-24。
> **結論先行**：🔴 階段一 zero-trust 重偵察揭露 **improving_57 commit（e9e2e59）把一個帶紅的 ci-gate 入庫**——Copy-on-Evolve v0.21→v0.22 從未跑 `skill_header_sync --write`，v0.22 LATEST 內 45 處框架版本戳仍停在 v0.21，致 ci-gate 的 DEF-CLDREV-007 戳記新鮮度硬閘 `exit 1`；improving_57 §5 宣稱「ci-gate exit 0」係**失真**（以 `| tail` 管線遮蔽真實退出碼，回傳 tail 的 0）。本輪：① **DEF-58-001** 機械同步 45 戳記 + 重生 59 父鏡像 → ci-gate 轉綠；② **DEF-58-002（P1 根因）** 把戳記同步釘進 `copy_on_evolve.sh` 本身（建版即自動 `--write`，fail-loud），杜絕「人去記得改」復發；③ **DEF-58-003** 記取證紀律教訓（閘門退出碼絕不經 `| tail` 遮蔽）。**零退化恢復**：AutoClaude pytest 3265/0（未動）；ci-gate **exit 0**（v0.01:1478 / v0.22:1655 / scripts:**128**，+1 新測試）；無 `*.tla` 變更免五軌 TLC；無新凍結版本（戳記修在 LATEST v0.22、腳本在 shared infra）。

---

## 1. 本輪輸入（自上輪繼承）

- 上輪＝improving_57（A①+B② 並進，宣稱合體 L3→L4）。最新框架版 **v0.22**。
- 缺陷帳本 open 項：DEF-01-007 / DEF-01-009 / DEF-17-001 / DEF-53-001 等全 P3/latent、環境或框架側 routed，無乾淨可修之 in-repo 缺陷。
- 上輪審計遺留：無 partial 宣稱——但**本輪階段一推翻 improving_57 的零退化宣稱**（見 §2.2）。

## 2. 階段一：現況重偵察（Zero-Trust Re-Audit，parent 親跑）

### 2.1 零退化基線（硬閘）

| 項目 | 命令 | 實測 | floor | 結果 |
|------|------|------|-------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | **3265 passed / 122 skipped / 0 failed** | 3265 | ✅ 持平 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | — | ✅ |
| LOC / snapshot | `check_loc_budget` / `snapshot_sync --check` | violations=0 / fresh | — | ✅ |
| **AISDLC_SDD ci-gate** | `bash scripts/ci-gate.sh` | **exit 1**（45 戳記 stale） | — | ❌ **RED** |

**硬閘判定**：基線 (a) AutoClaude pytest 無 failed、未低於 floor → 該硬閘通過。但 (c) **AISDLC_SDD ci-gate 帶紅**——零退化矩陣破口，本輪即修復此破口（非「停機不做」，而是補救輪正解）。

### 2.2 缺陷根因鏈（zero-trust 鐵證）

| 證據 | 命令 / 來源 | 事實 |
|------|-----------|------|
| ci-gate 真紅 | `bash scripts/ci-gate.sh > log 2>&1; echo $?` → **1** | DEF-CLDREV-007 戳記 lint `skill_header_sync --check` exit 1：LATEST(v0.22) 45 處戳記 != v0.22 |
| 戳記從未同步 | `git show e9e2e59:…/v0.22/.claude/skills/README.md` → `**版本**: v0.21-SDD` | improving_57 commit 當下 v0.22 戳記即停 v0.21（建版後從未 `--write`） |
| improving_57 假報綠 | improving_57 §5 + round-record「ci-gate exit 0：v0.22:1655…後綠」 | 與 real exit=1 矛盾；成因＝`bash ci-gate.sh \| tail -25` 回傳 **tail** 退出碼（0），遮蔽 ci-gate 真實 1（[[no-fabricated-tool-output]] 取證陷阱實例） |
| 根因可復發 | `copy_on_evolve.sh`（建版腳本）無戳記同步步驟 | 同步係人工後步驟，DEF-CLDREV-007（v0.19）首犯、DEF-58-001（v0.22）二犯 |

### 2.3 三軸成熟度（沿用 improving_57 + 本輪 Explore agent 實測複核）

派 Explore agent 對 SDD 自演化機具 zero-trust 實測（檔:行號證據見 ZeroTrust_Audit_58）：SLV 升 trust_level 必人工（`slv_generator` proposed 不自動升 verified，`_SLV_AUTO_PROPOSE_ENV` 預設 OFF）、meta_halt/ChurnBounded/GraduationRatchet 機具齊全但**環變數全預設 OFF（opt-in 鷹架）**、decision_trace 空、無「自動改自身治理規則並落地」路徑（全停 proposed + Copy-on-Evolve 人工 review）。

| 軸 | 實測級 | 依據 |
|----|--------|------|
| **C 引擎**（AutoClaude） | **L5** | 自演化 wire 進 ESCALATION 閉環 + 跨 session DAL 元學習（沿用 improving_56/57 實測） |
| **B 流程**（AISLDC_SDD） | **L4** | AUTO_RECOVERY 預設 ON（improving_57 達成）；L5 自演化機具皆 opt-in 鷹架未活體 |
| **A 協作**（雙向橋接） | **L4** | 有界自動凍結 signoff（improving_57 達成）；無失敗→轉譯策略元學習迴圈 |

**上捲**：`L_合體=min(A=L4,B=L4,C=L5)=L4`（**本輪維持，不推進**——補救輪）。

> **🔴 誠實標註**：improving_57 的 **L4 功能能力（auto-recovery 預設 ON + goal freeze gate）為真**（AutoClaude pytest 3265 綠、v0.22 fsm_runtime 翻轉為實）；但其「**零退化 / ci-gate 綠**」宣稱**為假**（帶紅入庫）。L4 功能成立，零退化矩陣有隱性紅，本輪修復。

## 3. 階段二：增量設計

### <Architecture_Design_Review>（實作前）

1. **架構純潔性**：本輪零 AutoClaude `core/`/`plugins/` 變更（不碰微核心）。改動＝(a) v0.22 戳記機械同步（既有 `skill_header_sync` 工具產出，無新邏輯）、(b) `copy_on_evolve.sh` shared-infra 硬化（+12 行，無 God-object）、(c) +1 測試。✅
2. **持久化相容**：不碰 PlaybookCheckpoint/DAL/FSM 狀態 schema。✅
3. **安全防護網**：`copy_on_evolve.sh` 新增子程序呼叫僅指向同層 repo 內既有腳本（絕對路徑 `${_SCRIPT_DIR}/`），無外部輸入、無 shell 注入面；`set -e` 確保同步失敗 fail-loud。✅
4. **對外 I/O 安全**：本輪不新增 `ToolInvocationPort` 外呼路徑。✅
5. **誠實性/零退化**：修復後 ci-gate 真實 exit 0（不再經 `\| tail` 遮蔽，直接 `echo $?` 取證）。floor: AutoClaude 3265 / v0.22:1654（improving_55 floor，+1 本輪測試）。✅

### Copy-on-Evolve / 五軌 TLC 判定

- 戳記修在 **LATEST v0.22**（最新演化版＝可修改版，非凍結基線）→ **免 Copy-on-Evolve 新建 v0.23**（本是 improving_57 建 v0.22 時該完成之動作）。
- `copy_on_evolve.sh` / `test_copy_on_evolve.py` 位 `AISDLC_SDD/scripts/`（version-agnostic shared infra，明文免 Copy-on-Evolve，同 ci-gate.sh / skill_header_sync.py）。
- **無 `_HAPPY_PATH` / `*.tla` / `.cfg` / `transition_rules.py` 變更** → **免五軌 TLC**。

## 4. 階段三：實作與雙重驗證

### W-58-1（DEF-58-001 fixed）戳記機械同步
`python scripts/skill_header_sync.py --write` → 同步 45 檔戳記至 v0.22（footer `**基於**: AISDLC-SDD v0.22` × 43 + README/PLAN `**版本**: v0.22-SDD` × 2），**後綴完整保留**（如 spec-logical-validator 的「Phase E M4 / ACT-028…」），**未觸 provenance/source/歷史/模板佔位版**（git diff 逐行核：每檔僅戳記行變更）。`sync_exposed_skills.py --write` 重生 59 檔父鏡像。兩 lint `--check` 真實 exit 0（`>/dev/null; echo $?` 取證、不遮蔽）。

### W-58-2（DEF-58-002 fixed）copy_on_evolve.sh 根因硬化
`scripts/copy_on_evolve.sh` 於 git archive 建版成功後，自動：
```
_SCRIPT_DIR=<本腳本目錄>;  _BASE=<TO 父目錄＝版本目錄群所在>
if [ -f "$_SCRIPT_DIR/skill_header_sync.py" ] && [ -f "$_SCRIPT_DIR/sync_exposed_skills.py" ]; then
  ${PYTHON:-python} "$_SCRIPT_DIR/skill_header_sync.py"  --write --repo-root "$_BASE"
  ${PYTHON:-python} "$_SCRIPT_DIR/sync_exposed_skills.py" --write --repo-root "$_BASE"
else  # 隔離 harness 無 siblings → 優雅略過 + warn（不破壞既有 helper 測試）
```
- **顯式 `--repo-root <BASE>`**：production 下 BASE=AISDLC_SDD/（與腳本預設等價），顯式化使隔離測試可指向 tmp 版本基底而不誤觸真實 v0.0X。
- **`${PYTHON:-python}`**：production/ci-gate 用預設 `python`；跨平台測試可注入解譯器。
- **sibling 存在性 guard**：隔離 harness（僅複製本腳本）優雅略過 + warn，既有 8 個 helper 測試零破壞；production `scripts/` 恆具 siblings 故必跑、`set -e` fail-loud。

### 回歸鎖（`scripts/tests/test_copy_on_evolve.py` +1，scripts 套 127→128）
`test_auto_syncs_skill_stamps_on_evolve_def_58_002`：tmp git repo 佈署真實 4 腳本（copy_on_evolve / skill_header_sync / sync_exposed_skills / rfc_lifecycle_lint）+ `AISDLC_SDD_v0.01` 含 `**基於**: AISDLC-SDD v0.01` 的 SKILL.md，commit 後跑建版 → 斷言新版 `AISDLC_SDD_v0.02` SKILL.md 戳記**自動同步為 v0.02**、無 v0.01 殘留、父鏡像亦重生。`_bash_with_python()` 解析含 python 的 Git Bash（Windows 裸 bash 常解析到無 python 的 WSL bash），無則環境 gated skip。

### 受控突變實證非空殼（Rule 9）
- **M-W582**：`copy_on_evolve.sh` 同步 guard 改 `if false && …`（停用 auto-sync）→ `test_auto_syncs_skill_stamps_on_evolve_def_58_002` **轉紅**（新版戳記停 v0.01：`assert '...v0.02' in '...v0.01'` 失敗），還原後 9 passed、grep `MUTATION` 零殘留。

## 5. 階段四：CI 平價收斂（零退化矩陣，parent 親跑、退出碼不遮蔽）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3265 / 0 failed | ✅ **3265 / 122 skipped / 0 failed**（本輪零 AutoClaude 變更） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept | ✅ **8 kept / 0 broken** |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | ✅ violations=0 |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh; echo $?` | **exit 0**（不經 `\| tail` 遮蔽） | ✅ **CIGATE_EXIT=0**；v0.01:1478 / v0.22:1655 / scripts:**128** |
| 戳記 SSOT lint | `skill_header_sync/sync_exposed_skills --check; echo $?` | exit 0 | ✅ 兩者 exit 0（45 戳記對齊 v0.22、59 鏡像一致） |
| 五軌 TLC | — | 僅 FSM 變更時 | N/A（無 `*.tla` 變更，git 證零差異） |

## 6. RTM（本輪需求追溯）

| 需求 | 驗收標準 | 證據 | 狀態 |
|------|---------|------|------|
| R-58-1 修復 ci-gate 紅（DEF-58-001） | 45 戳記同步 v0.22 + 59 鏡像 → ci-gate exit 0 | §4 W-58-1 + §5 | ✅ |
| R-58-2 根因硬化（DEF-58-002） | copy_on_evolve 建版即自動同步 + 回歸鎖 | §4 W-58-2 + M-W582 | ✅ |
| R-58-3 取證紀律教訓（DEF-58-003） | 閘門退出碼不經 `\| tail`；本輪全程 `echo $?` 取證 | §2.2 + §5 | ✅ |
| R-58-4 零退化 | pytest 3265、ci-gate exit 0、TLC 免 | §5 矩陣 | ✅ |
| R-58-5 回歸鎖非空殼 | M-W582 轉紅還原 + grep 零殘留 | §4 突變實證 | ✅ |
| R-58-6 三鏡 zero-trust 全 PASS | Architect/SA-SD/QA 主樹獨立審查 | `AutoSDD_ZeroTrust_Audit_58.md` | ✅（見 §7） |
| R-58-7 戳記同步外科精準 | 僅框架戳記行變更、未觸 provenance/歷史 | §4 W-58-1 git diff 核 | ✅ |

## 7. 三鏡 zero-trust 結果

見 `docs/06_quality/AutoSDD_ZeroTrust_Audit_58.md`。本輪變更**全為 tracked 檔修改（92 M、無 untracked 新檔）** → 三鏡皆主樹派發（無 DEF-24-001 untracked-worktree 陷阱、亦無並行突變）。

## 8. 結論與誠實級別標註

本輪＝**B 軌框架缺陷補救輪**，非成熟度推進。誠實重點：

1. **揭露 improving_57 假綠**：零退化的核心宣稱（ci-gate 綠）被 `| tail` 遮蔽退出碼而失真，實為帶紅入庫。本輪 zero-trust 重偵察（直接 `echo $?` 取證）揭露並修復——這正是「zero-trust 須對自己上一步的宣稱」的價值。
2. **根因根除而非貼 OK 繃**：不只 `--write` 補同步（DEF-58-001），更把同步釘進建版腳本（DEF-58-002），使這類戳記 bit-rot **不可能再被遺忘帶紅入庫**（對齊 DEF-CLDREV-007「人去記得改＝從流程消失」哲學；此為該類第二次復發，根因硬化合於 [[no-defer-unless-justified]]「能當場修就別延後」）。
3. **合體成熟度維持 L4**（`min(A=L4,B=L4,C=L5)`）——補救輪不推進；improving_57 的 L4 功能能力為真，唯零退化矩陣的隱性紅本輪清除。

**延後（justified，維持原狀態）**：DEF-01-007（cc-switch 環境）、DEF-01-009（LOC watch）、DEF-17-001（遙測 routed）、DEF-53-001（latent routed）。

**回流**：本輪框架缺陷皆就地修於 LATEST v0.22（戳記）+ shared infra scripts/（建版腳本），**無新凍結版本、無 `*.tla` 變更**（人工 signoff＝補救既有破口、無新政策 flip）。
