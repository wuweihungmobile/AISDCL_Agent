# AutoSDD_improving_30 — B 軌 RFC 生命週期機械強制（DEF-23-005）

> **本輪主柱**：**B 軌（手腳框架 dogfooding + 缺陷回流）** — 推進 AISDLC-SDD 框架治理自動化成熟度（北極星第 2 點：自我修正動態工作流）。
> **下一份**：`AutoSDD_improving_31.md`（按需）。
> **防跨軌誤指**：本輪在 **B 柱（手腳框架）**，非 A 柱（雙向協作）亦非 C 柱（指揮官內部）。
> 本輪**零 Copy-on-Evolve（無 v0.15）、五軌 TLC 不觸發**——交付落 repo 根 shared infra `scripts/`（version-agnostic，DEF-02-001/DEF-03-001 先例），不觸任一 `AISDLC_SDD_v0.0X` 凍結本體。
>
> **角色**：Dr. Alan（L10 自治系統與微核心架構總監）
> **日期**：2026-06-18 ｜ **承上**：improving_29 結案（A 軌正向轉譯保真度/多引號斷言組合，tag `v2026.06.18-27` / commit `da3a929`）

---

## 0. 北極星對齊

對齊北極星**第 2 點「AI 規格驅動開發 — 自我修正動態工作流」**：本輪 B 軌 dogfooding v0.14 框架，發現並閉合其**治理自動化缺口**——框架明定 RFC 生命週期「active=待決 / archive=已決」卻**無任何機械強制**，已決 RFC 曾滯留 active/ 直到人工盤點才揪出。本輪把此人工紀律升級為 **ci-gate 硬閘 lint**（機械可驗），使框架向「自我修正」邁進一步。

成熟度三軸（`AutoSDD_Maturity_Rubric.md`，`L_合體 = min(A,B,C)`）：本輪推 **B 軌（流程自治）**。上輪 29 推 A 軌；依輪推紀律本輪轉 B。**禁宣稱 L 級躍升**：本輪僅補一條治理流程的機械閘門（read-only 純觀察者、零持久化、零框架本體變更），是流程自治的最小誠實一步，`L_合體` 仍受最弱軸卡住、不變。

---

## 1. 階段一：現況重偵察（Zero-Trust Re-Audit）— 實測事實

派背景 agent + 確定性命令親跑實測（**硬閘 PASS**，准入階段二）。所有數字來自當前回合真實 tool_result：

| 檢查 | 命令 | 實測 | 判定 |
|------|------|------|------|
| AutoClaude pytest | `python -m pytest tests/ -q` | **3196 passed / 122 skipped / 0 failed**（109.34s） | ✅ floor=3196 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | ✅ |
| LOC budget | `python tools/check_loc_budget.py` | total=18489 / cap=20438，violations=0 | ✅ |
| snapshot | `python tools/snapshot_sync.py --check` | OK（FRESH） | ✅ |
| AISDLC_SDD ci-gate | `bash scripts/ci-gate.sh` | exit 0（v0.01:1478 + v0.14:1593 + scripts:27） | ✅ |
| 最新框架版本 | — | **v0.14**（2026-06-17 凍結） | — |

**外部工具依賴（階段一 (f)）**：本輪純框架 shared infra lint（檔案掃描 + regex），無 A/B 後端切換、無外部 CLI/服務、無訊息平台——不適用。

**B 軌標的測繪（決定 W 項，zero-trust 親查）**：

| 缺陷 | 現況（file:line / 證據） | 本輪處置 |
|------|------------------------|---------|
| **DEF-23-005**（RFC 生命週期缺機械強制） | 框架明定 active/archive 生命週期但無 hook/lint 強制；**實證 v0.12/v0.13 的 `build/planning/active/` 至今凍結著已決的 _26/_27** | **本輪標的（W-30-1）** |
| DEF-19-001（catch 覆蓋 4/39） | 需逐條改 35 個凍結 `R-*.yaml` + 語意判斷 + Copy-on-Evolve v0.15 | 排除（非機械、量大、違 Rule 2 最小） |

> **scope 決策（Rule 2 最小）**：兩 B 軌候選中選 DEF-23-005——它自包含、可機械化、落 shared infra（免 Copy-on-Evolve / 不觸凍結本體 / 不觸 `*.tla`/TLC），是本輪最乾淨一步；DEF-19-001 涉 35 凍結規則 + 語意判斷 + v0.15，量大且非機械，留待後輪。

**已決標記慣例實證（決定偵測策略）**：37 個 archive RFC 中 `落地版本` 僅 1 檔、`結案` 2 檔、`狀態：已決` 0 檔、`決策` 區塊 25 檔（proposal 模板本有，**非**已決標記）。慣例不一致 → lint 採「最低誤報」雙信號鎖現有最強標記（標準化結案欄位本身另記 DEF-30-001 觀察項）。

---

## 2. 階段二：增量設計（🔴 掌舵者選定 B 軌）

### 2.1 scope 決策

🔴 掌舵者選定主柱＝**B 軌**。依 §1 標的測繪，鎖定 **DEF-23-005 RFC 生命週期機械強制** 為本輪 W 項。

### 2.2 本輪 W 項（單一 W，Rule 2 最小）

| W 項 | 構件 | 落點 | 形態 |
|------|------|------|------|
| **W-30-1** | `rfc_lifecycle_lint.py`（純函式 + thin CLI）+ 測試 + 接入 `ci-gate.sh` 硬閘 | repo 根 `scripts/` | shared infra（version-agnostic、**免 Copy-on-Evolve**、read-only 純觀察者） |

**零 Copy-on-Evolve、零 v0.15、零新 R-9.x、零 FSM/governance 變更、零 `_HAPPY_PATH`/`*.tla`**：純 shared infra lint（DEF-02-001 `cross_version_guard.py` / DEF-03-001 `ci-gate.sh` 同精神）。

### 2.3 介面 delta

```python
# scripts/rfc_lifecycle_lint.py（純函式）
def discover_frozen_versions(repo_root) -> set[str]   # 列 AISDLC_SDD_v0.0X 目錄
def latest_version(versions) -> str | None            # 語意版本最高（對齊 ci-gate sort -V）
def decided_reason(text, frozen_versions) -> str | None  # 雙信號判已決
def find_decided_rfcs_in_active(active_dir, frozen) -> list[(name, reason)]
def lint(repo_root) -> list[(name, reason)]           # 解析最新版 → 掃其 active/
def main(argv) -> int                                 # CLI：乾淨 0 / 違規 1
```

**偵測規則（最低誤報雙信號，錨定行首 header 欄位式）**：
- (a) `^\s*\**落地版本\**[:：]` 行含 `AISDLC_SDD_vX` 且該版**目錄已存在於磁碟**（已落地＝已決）；
- (b) `^\s*\**狀態\**[:：]\s*(已決|結案|archived|closed)`（顯式結案狀態）。
- 錨定行首 → 不誤配 inline-code 範例 / 句中提及（meta 文件防誤報，見 §3 dogfooding 揭露）。
- **只掃最新版** active/（舊凍結版 active/ 是 Copy-on-Evolve 歷史快照，掃描會誤報且違反不動凍結本體）。

### 2.4 `<Architecture_Design_Review>`（寫實質 Python 前自我驗證）

1. **架構純潔性**：新增 shared infra 純函式 + thin CLI，不碰任一凍結本體 / FSM runtime / governance。無 God-object，與 `cross_version_guard.py` 同層同精神。✅
2. **持久化相容**：零狀態、零 FSM-STATE 寫入（read-only lint）→ 不涉 DAL/checkpoint。✅
3. **安全防護網**：僅 `os.listdir` + 讀 `.md` + regex，無 shell/外呼/eval，不涉 CONDITIONAL/ToolInvocation。✅
4. **對外 I/O 安全**：未新增 `ToolInvocationPort` 外呼路徑。✅
5. **紅線守界**：只掃最新版；**不寫 FSM-STATE、不影響 churn/meta-loop**（R-9.37.4 read-only 純觀察者精神）；**不觸 meta-oracle、不增第六軌、零 `*.tla` 變更** → 五軌 TLC 不觸發。✅

### 2.5 B 軌 dogfooding — SCG 閘門 + 官方回流機制對應

| SCG | 載體 |
|-----|------|
| SCG-0/1（需求/規格凍結） | 本計畫書 §0~§2 + 🔴 掌舵者 scope 選定（B 軌 / W-30-1） |
| SCG-2（介面設計） | §2.3 介面 delta + §2.4 設計審查 |
| SCG-3（契約） | lint 雙信號偵測純函式契約（凍結後實作） |
| SCG-4（PR/實作） | §3 實作 + 11 單元測試全綠 + ci-gate 硬閘接入 |
| SCG-5（RTM 覆蓋） | §4 RTM（本輪 AT 100% 覆蓋） |

**官方回流機制**：框架程式/hook 缺陷 → RFC `build/planning/active/SDD_improving_Automation_28.md`（記錄提案 → 決策後 archive）。本輪 RFC 28 已建於 v0.14/active/（運行工作區，可寫）→ 決策後移入 archive/（dogfooding 完整生命週期，並以新 lint 自我驗證）。

---

## 3. 階段三：實作與雙重驗證

逐支開發-編譯-測試循環（絕不累積）。新增 **2 檔**（皆 shared infra）+ 改 1 檔 + RFC 1 檔：

- `scripts/rfc_lifecycle_lint.py`（新，~95 行純函式 + CLI）
- `scripts/tests/test_rfc_lifecycle_lint.py`（新，**11 case**）
- `scripts/ci-gate.sh`（改，+6 行：共享 infra 區塊後接 RFC lint 硬閘）
- `AISDLC_SDD_v0.14/build/planning/archive/SDD_improving_Automation_28.md`（RFC 帳本，決策後歸檔）

**開發循環當場攔截 2 次缺陷（均於本輪修復、未流出）**：
1. **regex 漏配真實格式**：初版 `落地版本[:：]` 未容忍 markdown 粗體 `**落地版本**：`（標籤與冒號間有 `**`）→ 3 fire 案例全紅；修為 `\**` 容忍。
2. **meta 文件誤報（dogfooding 揭露）**：lint 掃自己的 RFC 28 時，因 RFC 為「說明偵測規則」而含 `狀態：已決` 等 token 字面 → 誤報。修為**錨定行首 header 欄位式**（`^\s*\**label`），inline-code / 句中提及不誤配；補迴歸測試 `test_inline_marker_mentions_not_fired`。

**共 +11 測試 + ci-gate scripts/tests 27→38（+11）**，只增不減、0 failed。

---

## 4. RTM（需求追溯矩陣）— 本輪 AT 100% 覆蓋

| AC | AT | 測試 | 狀態 |
|----|----|------|------|
| AC-30-1（已決 RFC 滯留 active 偵測） | AT-30-1-1 落地版本＝已存在版→fire | `test_landed_version_existing_fires` | ✅ |
| AC-30-1 | AT-30-1-2 顯式結案狀態→fire | `test_closed_status_fires` | ✅ |
| AC-30-2（不誤報待決 RFC） | AT-30-2-1 genuinely-proposed→pass | `test_proposed_rfc_passes` | ✅ |
| AC-30-2 | AT-30-2-2 落地版本指向未存在版→pass（存在性閘） | `test_landed_version_nonexisting_passes` | ✅ |
| AC-30-2 | AT-30-2-3 meta 文件 inline 提及 token→pass（行首錨定） | `test_inline_marker_mentions_not_fired` | ✅ |
| AC-30-3（邊界/範圍正確） | AT-30-3-1 .gitkeep/非.md 略過 | `test_gitkeep_and_nonmd_ignored` | ✅ |
| AC-30-3 | AT-30-3-2 空 active→pass | `test_empty_active_passes` | ✅ |
| AC-30-3 | AT-30-3-3 只掃最新版（舊版滯留不 fire） | `test_scans_only_latest_version` | ✅ |
| AC-30-3 | AT-30-3-4 語意版本 v0.10>v0.9 | `test_latest_version_semantic` | ✅ |
| AC-30-4（CLI 硬閘語意） | AT-30-4-1 乾淨 exit0 / 違規 exit1 + DEF-23-005 訊息 | `test_main_exit_codes` | ✅ |
| AC-30-4 | AT-30-4-2 真實 v0.14 active 乾淨鎖 | `test_real_repo_v014_active_clean` | ✅ |

**覆蓋率**：本輪 4 AC / 全部 11 AT 100% 通過。真實資料健全性：lint 對 archive 的 RFC 27（落地 v0.12 存在）正確 fire、對 RFC 26（無標記）正確不 fire。

---

## 5. 階段四：CI 平價收斂（零退化驗證矩陣）

| 檢查 | 命令 | floor（improving_29 實測） | 本輪實測 | 判定 |
|------|------|------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3196 / 0 failed | **3196 passed / 122 skipped / 0 failed**（116.64s） | ✅ 持平（本輪零觸碰 AutoClaude） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | 8 kept / 0 broken（本輪零觸碰 AutoClaude） | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0 | total=18489 / violations=0（零觸碰） | ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | FRESH | OK（零觸碰 AutoClaude） | ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | 全綠（scripts:27） | exit 0（v0.01:1478 + v0.14:1593 + **scripts:38**，+11）+ RFC lint PASS | ✅ |
| DAL 等價 | equivalence | 三後端等價 | 零 checkpoint/repository 變更（純 shared infra lint），含於全套 | ✅ |
| 五軌 TLC | （僅 FSM 變更時） | — | **不觸發**（零 `_HAPPY_PATH`/`*.tla`/凍結本體變更） | N/A |

---

## 6. 缺陷分流

- **DEF-23-005 → fixed@improving_30**（RFC 生命週期機械強制落 shared infra）。
- **本輪新增觀察項 DEF-30-001**（P3）：RFC「已決」結案標記欄位無標準化（37 archive RFC 慣例不一致：落地版本 1 / 結案 2 / 狀態：已決 0）→ 未來輪可評估於 RFC 模板補標準 `狀態` 欄並回填。本輪 lint 先以「最低誤報」雙信號機械化現有最強標記，不阻擋。
- open/routed 既有缺陷複驗：DEF-19-001（catch 覆蓋 4/39，routed B 軌，本輪 scope 外）、DEF-01-007（cc-switch GUI，環境側）、DEF-01-009（LOC watch，本輪未動 sdd_governance plugin）、DEF-17-001（routed）——詳見 `AutoSDD_Defect_Log.md`。

**本輪新增防退化資產（非缺陷）**：`rfc_lifecycle_lint.py` 由 11 case 鎖定（雙信號 fire / 待決不誤報 / meta 文件防誤報 / 只掃最新版 / 語意版本 / CLI / 真實鎖），DEF-23-005 治理自動化缺口閉合並接入 ci-gate 硬閘。

---

## 7. 結案四件套

1. 本計畫書 `docs/04_planning/AutoSDD_improving_30.md`
2. `docs/06_quality/AutoSDD_ZeroTrust_Audit_30.md`（審計 + 三鏡複審證據）
3. `docs/06_quality/AutoSDD_Defect_Log.md`（DEF-23-005 → fixed；新增 DEF-30-001 觀察項）
4. 框架改進：RFC `SDD_improving_Automation_28.md`（archived）+ shared infra lint（**無 v0.15**，DEF-02-001 先例）
