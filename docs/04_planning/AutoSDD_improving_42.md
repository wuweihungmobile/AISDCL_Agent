# AutoSDD_improving_42 — A 軌整合橋接：But 續行斷言保真度修復（DEF-42-002）

> **軌道①整合迭代 第 42 輪**。本輪主柱＝**A 軌（雙向協作橋接 SDD→Playbook）**。
> 🔴 掌舵者 AskUserQuestion 兩問拍板：(Q1) 主柱＝**A 軌·續偵察 adapter 保真度缺口**；(Q2) 推進幅度＝**≤3 W 項**。
> 本輪改 AutoClaude `sdd_to_playbook_adapter.py`（A 軌整合橋接入口），**零 Copy-on-Evolve、零框架 v0.0X 變更、TLC 不觸發**。
> 北極星對齊：A 協作自治（規格驅動轉譯保真度——把標準 Gherkin 關鍵字 `But` 續行斷言「整條丟棄」之 under-specify 漏放修正，提升 SDD→Playbook 轉譯契約的端到端可信度）。

---

## §0 本輪定位（防跨軌誤指）

| 項目 | 內容 |
|------|------|
| 軌道 | ① 整合迭代，**A 柱（雙向協作橋接）** |
| 活標的 | **DEF-42-002**（But 續行斷言被靜默丟棄 under-specify，P3，本輪新開→fixed） |
| 為何非 C 軌 | C 軌 SD_09 **W1 因 06-26 G0 閘門未開而 blocked**（今 2026-06-21），不啟 W1/不跑 mutmut/不偽造 nightly |
| 為何 A 軌 | 🔴 掌舵者 Q1 拍板；DEF-41-001 fixed@improving_41 後續偵察 SddToPlaybookAdapter 揭露 But 關鍵字未支援之新缺口 DEF-42-002 |
| 下一份 | improving_43（按需） |
| 框架版本 | **無變更**（A 軌純改 AutoClaude，非框架 dogfooding，無 Copy-on-Evolve）；最新框架版實測 **v0.17** |

---

## §1 階段一：現況重偵察（Zero-Trust Re-Audit，實測）

六項基線 HARD GATE PASS：

| 項目 | 實測值 | 判定 |
|------|--------|------|
| AutoClaude `pytest tests/ -q`（基線） | **3229 passed / 122 skipped / 0 failed** | ✅ = floor，0 failed |
| `lint-imports` | 8 kept / 0 broken | ✅ |
| `check_loc_budget.py` | violations=0（total 18518 < cap 20438） | ✅ |
| `snapshot_sync.py --check` | OK / FRESH | ✅ |
| git 工作樹（root） | porcelain 空（乾淨） | ✅ |
| 框架最新版 | **v0.17**（`sort -V` 實證） | ✅ |

- **階段一 (f) 外部工具依賴**：本輪 A 軌純改 AutoClaude Python adapter，**不涉外部 CLI/GUI/服務**，N/A。
- **zero-trust 雙向糾正**（對 Explore 兵宣稱亦複核）：
  - **(k) DEF-01-009 誤報糾正**：Explore 兵以 raw `wc -l`=277 判「>250 上限超標」，但 DEF-01-009 受控指標為 **count_loc（非空行）**；主 agent 親跑 `check_loc_budget` violations=0（tier=0，權威閘門）→ 維持 **open watch**（未違規），raw 277≠count_loc。
  - **(e) ci-gate v0.17 flaky 判定**：Explore 兵報 `test_parallel_writes_do_not_lose_increments` 失敗致 ci-gate exit 1；主 agent 親跑隔離 **3/3 全綠**、工作樹乾淨、本輪未動框架 → 確認 **Windows 並行負載 flaky 非回歸**，記 **DEF-42-001**（routed）。硬閘鎖定 (a) AutoClaude 基線（綠），ci-gate flaky 非回歸不阻擋。
- **DEF-42-002 根因實測**（親跑 repro 證明，非僅讀碼）：[sdd_to_playbook_adapter.py](../../AutoClaude/autoclaude/infra/adapters/sdd_to_playbook_adapter.py) `_then_assertions` 僅認 `Then`/`And` 續行，**完全不認標準 Gherkin 關鍵字 `But`**（grep 全檔零處理）。實證三例：
  - `Then 回傳 200` + `But 不應回傳 500` → `_then_assertions` 只抽 `['Then 回傳 200']`、regex `(?i)(200)`；含 500 輸出 `re.search==True`＝漏放（負向 500 整條丟棄）。
  - `Then 顯示「成功」` + `But 不應顯示「錯誤」` → 只抽正向、regex `成功`；含「錯誤」輸出漏放。
  - 英文 `Then the API returns 200` + `But must not return 500` → 同樣丟棄負向。

---

## §2 階段二：本輪增量設計（1 實作 W 項 + 1 測試 W 項 + 1 帳本，含 1 surface 缺陷）

### <Architecture_Design_Review>

1. **架構純潔性**：僅在既有純函式 `_then_assertions` 的續行關鍵字判斷加入 `But`（語意同 And）。不新增方法/類別、不改控制流外型、Thin Facade 不受影響、無 God-object。But 行納入後自然走既有 W-31/W-41 引號/狀態碼聚合邏輯，零新增轉譯分支。
2. **持久化相容**：零 FSM-STATE / checkpoint 寫入，純函式，DAL 三後端零影響。
3. **安全防護網**：But 行斷言沿用既有 `re.escape(...)`／`_sanitize`／白名單模板／CONDITIONAL 三層防禦；regex 僅 evaluator 比對、非指令生成路徑。
4. **對外 I/O 安全**：不新增 `ToolInvocationPort` 外呼路徑，N/A。
5. **零退化（關鍵·哨兵鎖定）**：純 And 路徑逐位元維持（`test_and_only_path_unchanged_sentinel`）；But-before-Then 不污染（`test_but_before_then_not_assertion_sentinel`，鏡 `test_and_before_then`）；既有 72 case 全綠。僅「Then/And 之後的 But 續行」改變行為（先前整條丟棄＝缺口）。
6. **對稱性**：`But` 與 `And` 在 (a) 續行納入判斷、(b) in_then 結束判斷 兩處同步加入，負正對稱可審。
7. **紅線**：純轉譯保真度修復、不碰 maturity/meta、不提 Token 上限、零 Copy-on-Evolve、TLC 不觸發。

### W-42-1 — But 續行斷言支援（DEF-42-002 修復）

| 項目 | 內容 |
|------|------|
| 落點 | `sdd_to_playbook_adapter.py` `_then_assertions`：續行判斷 `("And",)`→`("And", "But")`；in_then 結束判斷 `("#", "And")`→`("#", "And", "But")` |
| 介面 delta | But 行與 And 同等視為 Then 續行斷言；納入後走既有引號/狀態碼正負聚合邏輯（無新分支） |
| 零退化 | 純 And 路徑、But-before-Then、既有 72 case 逐位元維持（哨兵鎖定） |
| LOC 影響 | adapter 334→339 行（+5，<400 adapter tier） |
| `.importlinter` 影響 | 無（同函式內，無新跨層 import） |
| TLC | 不觸發（純 AutoClaude，零框架/FSM 變更） |

### W-42-2 — 測試：新增 But 續行 case + 哨兵 + M1 突變實證

- 新增 `TestButContinuationFidelity` 6 case：
  - `test_but_negative_status_aggregated`（核心：But 負向狀態碼納入，`(?s)\A(?=.*(?:200))(?!.*500)`，500 擋下）；
  - `test_but_negative_quoted_aggregated`（But 負向引號，`(?s)\A(?=.*成功)(?!.*錯誤)`）；
  - `test_but_english_keyword`（英文 But must not）；
  - `test_but_before_then_not_assertion_sentinel`（防退化哨兵，But 在 Then 前不污染，→ `(?i)(201)`）；
  - `test_and_only_path_unchanged_sentinel`（防退化哨兵，純 And 逐位元維持）；
  - `test_end_to_end_but_regex`（端到端經 `_BUT_SPEC` 凍結載入）。
- **M1 突變**（續行判斷退回只認 `("And",)`）實證 **4 紅（But 負向狀態碼/負向引號/英文 But/端到端）/ 2 綠（And-only 哨兵、But-before-Then 哨兵）**；in-memory 反向 Edit 還原，`grep M1-MUTANT`=0 無殘留（DEF-32-001 紀律）。

### W-42-3 — 缺陷帳本：DEF-42-001 routed / DEF-42-002 open→fixed / DEF-42-003 surface wontfix

- **DEF-42-001（P3, routed）**：v0.17 並行寫 flaky 測試（階段一發現，非回歸）。
- **DEF-42-002（P3, open → fixed@improving_42）**：見 §5。
- **DEF-42-003（P3, wontfix/by-design surfaced）**：引號+負向狀態碼共存丟負向之 under-specify，撞 W-32-1 刻意哨兵，誠實 surface（見 §5、§7 紀律事件）。

### A 軌 SCG 對應（整合橋接 brownfield）

- SCG-0/1（需求/設計凍結）＝本計畫書 §1/§2（活標的＝But 續行斷言保真度）；SCG-2 架構＝<Architecture_Design_Review>（純轉譯邏輯、零拓樸變更）；SCG-3 契約＝But 與 And 同等續行之斷言納入契約；SCG-4 實作 PR＝§3；SCG-5 RTM＝§6。

---

## §3 階段三：實作與雙重驗證

逐項實作即測（開發-編譯-測試循環）：

1. **W-42-1**：`_then_assertions` 加入 But 續行支援。
2. **即測（首測）**：repro 三例皆正確擋下、focused 72 既有測試零退化。
3. **W-42-2**：新增 `TestButContinuationFidelity` 6 case → **78 passed**（72+6）。
4. **M1 突變**：續行退回只認 And → 4 But 內容 case 轉紅 / 2 哨兵維持綠；反向 Edit 還原後 78 passed、`grep M1-MUTANT`=0 無殘留。
5. **Rule 7/8/11 紀律事件**：初版誤把「引號+負向狀態碼丟負向」當缺口跨路徑搶救，撞既有刻意哨兵 `test_quoted_wins_over_negative_status`（440-446）1 failed → `git checkout` 還原回綠、改走零衝突之 But 缺口、誠實記 DEF-42-003。

---

## §4 階段四：CI 平價收斂（零退化驗證矩陣，全項實測）

| 檢查 | 命令 | 通過條件（floor=improving_41 實測） | 本輪實測 | 判定 |
|------|------|------|------|------|
| AutoClaude 全套 | `pytest tests/ -q` | ≥ 3229 passed / 0 failed | **3235 passed / 122 skipped / 0 failed**（+6 新 case） | ✅ |
| 架構契約 | `lint-imports` | 全 kept / 0 broken | 8 kept / 0 broken | ✅ |
| LOC 分級 | `check_loc_budget.py` | 全過 | violations=0（adapter 339<400；total 18522） | ✅ |
| Snapshot | `snapshot_sync.py --check` | 新鮮 | FRESH | ✅ |
| AISDLC_SDD 閘門 | `ci-gate.sh` | not-chaos 全綠 + arch_fitness exit<2 | 本輪零碰框架；v0.17 偶 flaky（DEF-42-001，隔離 3/3 綠＝非回歸） | ⚠️ 記帳非阻擋 |
| DAL 等價 | equivalence | 三後端等價 | AutoClaude DAL 未動，N/A | ✅ |
| 五軌 TLC | （僅 FSM 變更時） | 5 軌 0 violation | 不觸發（零框架變更） | ✅ |

> - AutoClaude 3235 = floor 3229 + 6（W-42-2 淨增 6 新 case）。
> - 本輪零碰 AISLDC_SDD 框架本體、零 Copy-on-Evolve、零 v0.0X 變更。
> - ci-gate v0.17 flaky（DEF-42-001）為環境 Windows 並行負載偽紅，主 agent 親跑隔離 3/3 綠證非回歸；A 軌主鏈零退化基線 AutoClaude 3235/0 不受影響。

---

## §5 缺陷處置

- **DEF-42-002（P3）→ fixed@improving_42**（A 軌；But 續行斷言保真度，與 And 同等處理、零退化、M1 突變實證；見帳本狀態欄）。
- **DEF-42-001（P3）→ routed**（v0.17 並行寫 flaky 測試，非回歸；待 B 軌未來輪 Copy-on-Evolve 處置）。
- **DEF-42-003（P3）→ wontfix+理由（by-design surfaced）**（引號+負向狀態碼共存丟負向之 under-specify，係 W-32-1 刻意決策＋哨兵鎖定；推翻需 🔴 掌舵者拍板，surface 供未來輪評估）。
- 未推進（維持原狀態）：DEF-01-007（open，cc-switch GUI 環境缺裝）、DEF-01-009（open watch，本輪未擴充 sdd_governance_plugin、violations=0 不觸發；raw 277≠count_loc）、DEF-37-001（routed，Copy-on-Evolve gitignore 自動偵測）、DEF-17-001（routed，遙測）。

---

## §6 RTM（需求可追溯矩陣）

| 需求 | 設計 | 實作 | 驗收 |
|------|------|------|------|
| But 續行斷言納入（DEF-42-002 核心）| §2 W-42-1 | `_then_assertions` `("And","But")` 續行 | `test_but_negative_status_aggregated`（regex==`(?s)\A(?=.*(?:200))(?!.*500)`，500 擋下）|
| But 負向引號納入 | §2 W-42-1 | But 行走既有引號正負聚合 | `test_but_negative_quoted_aggregated`（regex==`(?s)\A(?=.*成功)(?!.*錯誤)`）|
| 英文 But 關鍵字 | §2 W-42-1 | startswith("But") case-insensitive 由 _NEGATION_MARKER 處理否定 | `test_but_english_keyword` |
| 零退化（純 And 路徑）| §2 設計#5 | And 續行邏輯不變 | `test_and_only_path_unchanged_sentinel` + 既有 72 case |
| 零退化（But-before-Then）| §2 設計#5 | in_then 守門 | `test_but_before_then_not_assertion_sentinel` |
| 修復有效性 | §2 W-42-2 | M1 突變 | M1 續行退回只認 And→4 But case 轉紅、2 哨兵綠 |
| 端到端凍結載入 | §2 W-42-2 | `_BUT_SPEC` | `test_end_to_end_but_regex` |

---

## §7 結案證據契約（closure-evidence，反幻覺機械閘門 DEF-20-001）

```yaml
closure-evidence:
  base_sha: b4d69d9  # 本輪所建之上的 HEAD（improving_41 回填收尾後）
  claimed_commits:
    - <主 commit sha：回填時填入>
  claimed_tag: v2026.06.21-42
  pytest:
    autoclaude: "3235 passed / 122 skipped / 0 failed（floor 3229 +6）"
    adapter_focused: "78 passed（test_sdd_to_playbook_adapter.py + test_gherkin_to_regex.py）"
  lint_imports: "8 kept / 0 broken"
  loc: "violations=0; adapter 339<400; total 18522"
  snapshot: "FRESH"
  ci_gate: "本輪零碰框架；v0.17 偶 flaky（DEF-42-001，隔離 3/3 綠＝非回歸）"
  tlc: "N/A — 零框架/FSM 變更"
  copy_on_evolve: "N/A — A 軌純改 AutoClaude，無 v0.0X 變更"
  mutation_m1: "_then_assertions 續行退回只認 And → 4 But 內容 case 轉紅 / 2 哨兵綠；in-memory 反向 Edit 還原，grep M1-MUTANT=0"
  discipline_event: "Rule 7/8/11：初版誤修撞既有刻意哨兵 test_quoted_wins_over_negative_status 1 failed → git checkout 還原、改走零衝突 But 缺口、誠實記 DEF-42-003 wontfix/by-design"
```
