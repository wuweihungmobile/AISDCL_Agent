# AutoSDD improving_56 — A 軌實作：spec_digest 閉環署名不變量 + 真實規模雙向 e2e 信號（協作橋接 L3→L4 進展）

> **軌道定位**：軌道① **A 軌**（雙向協作橋接，柱③；對齊北極星第 3 點「完美協調溝通機制」）。整合層 AutoClaude 側，**免 Copy-on-Evolve、免五軌 TLC**（未動 AISDLC_SDD 本體與 `*.tla`）。
> **掌舵者裁定**：本輪兩階段 AskUserQuestion——①「先看三軸成熟度實測」→②實測得 `L_合體=min(A=L3,B=L3,C=L5)=L3`、A 與 B 雙瓶頸 → 裁定「**A 軌 協作橋接 L3→L4（推薦）**」。
> **下一份**：`AutoSDD_improving_57.md`（按需）。**日期**：2026-06-24。
> **結論先行**：🟢 補齊 A 軸 L4 三缺口中的 **2 個**——W-56-1（真實規模**雙向**全鏈 e2e：逆向橋接 RtmCoverageReport 首次在 kernel 內以 3AC/6AT 真實規格跑過）+ W-56-2（**spec_digest 閉環署名不變量**，修復 DEF-56-001 雙重脆弱漂移）。**誠實標註**：本輪＝**progress toward L4（2/3）**，**非達成 L4**；第 3 缺口（goal/spec→playbook 端到端無人工 signoff）未做，且 B 軌仍 L3 → **合體仍 `min(A,B,C)=L3`**（須三軸並進方能推動）。**零退化**：AutoClaude pytest **3248→3255**（+7 新測試、0 failed）；lint-imports 8 kept/0 broken；LOC=0；snapshot fresh。

---

## 1. 本輪輸入（自上輪繼承）

- 上輪＝improving_55（B 軌實作，守門覆蓋度量，Copy-on-Evolve v0.21）。最新框架版 **v0.21**（本輪未動框架本體）。
- 缺陷帳本：穩態輪——無「乾淨可修且不違 Rule 2」之 in-repo 缺陷（improving_54 已親核）；DEF-53-001 routed latent、DEF-01-007/009 open。**本輪以三軸成熟度實測落後軸決定方向，於 A 軸實測中新發現 DEF-56-001（latent 正確性缺口）**。
- 上輪審計遺留：無 partial。

## 2. 階段一：現況重偵察（Zero-Trust Re-Audit，parent 親跑 + 三軸 Explore 實測）

### 2.1 零退化基線（硬閘）

| 項目 | 命令 | 實測 | floor | 結果 |
|------|------|------|-------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | **3248 passed / 122 skipped / 0 failed** | 3248 | ✅ 持平 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | — | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0（baseline 17032） | — | ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | OK | — | ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **exit 0**；v0.01:1478 / v0.21:**1654** / scripts:127 | 1654 | ✅ 零漂移 |

**硬閘**：無 failed、未低於 floor → 通過，准進階段二。

### 2.2 三軸成熟度實測（AutoSDD_Maturity_Rubric SSOT，三 Explore agent 引證據，zero-trust）

| 軸 | 實測級 | 關鍵證據（file:line） | 距上一級缺口 |
|----|--------|----------------------|------------|
| **C 引擎**（AutoClaude） | **L5**（相符宣稱） | 自演化真 wire 進 ESCALATION 閉環（`_escalation_handler.py:89-109`、`minimax_evolver.py:31-68`、`playbook_evolver.py:51-208`）；goal_decomposer 三閘 + 🔴 signoff（`goal_decomposer.py:125-145,158-217`）；DAL 三後端跨 session 持久化 + FailureKnowledgeBase 元學習（`knowledge_base.py:34-80`） | L6 需演化 rollback/fitness 追蹤 |
| **B 流程**（AISLDC_SDD） | **L3** | L4 骨架存在但**閘關著**：`AUTO_RECOVERY` 預設 OFF（`fsm_runtime.py:44` env 預設 False）；SLV 自演化提議真實但升 trust_level 必人工 review（`fsm_runtime.py:2636`）；每關卡 HUMAN_PENDING 強制人確認；五軌 TLC reachable 27/27 | L4 需 auto-recovery 常態化 + 自動修正免確認閾值（**動 FSM 行為、恐觸 TLC**） |
| **A 協作**（雙向橋接） | **L3** | 僅 smoke/合成 executor（`test_bridge_smoke.py` `_RegexExecutor`、`test_bridge_multi_ac.py` `_MapExecutor`）；**逆向橋接 RtmWritebackPlugin 僅單元測試、從未在 kernel e2e**；spec_digest 由 prompt 反解 + 8 字元截斷＝漂移風險（`rtm_writeback_plugin.py:86`） | L4 需真實規格 e2e 信號 + spec_digest 閉環不變量（**+ 無人工 FSM 凍結註冊**，第 3 缺口本輪不做） |

**上捲**：`L_合體 = min(L3, L3, L5) = **L3**`，A 與 B 雙瓶頸。掌舵者裁定本輪先攻 A（北極星第 3 點、additive 低風險、含真實 latent 缺口可修；B 的 AUTO_RECOVERY 翻轉動 FSM/TLC、風險高宜獨立成輪）。

### 2.3 invocation 形態（階段一 (f)）

純框架內整合層資料流（pydantic model 加欄 + 純函式 adapter + plugin getattr 讀屬性），**無外部 CLI/GUI/API**、無 `ToolInvocationPort` 外呼；headless 可全驗。

## 3. 階段二：增量設計（A 軌 ≤2 W 項）

### <Architecture_Design_Review>（實作前）

1. **架構純潔性**：`PlaybookTask` 加 additive `spec_digest: Optional[str]=None`（data tier ≤150）；forward adapter 多填一欄；rtm_writeback 改讀結構欄（prompt-parse 降 fallback）。無 God-object、playbook_runner thin facade 未動。✅
2. **持久化相容**：欄為 Optional 預設 None → YAML/checkpoint 向後相容；經 `sdd_compile` 序列化 round-trip 結構欄存活，反更穩固。不碰 PlaybookCheckpoint/DAL。✅
3. **plugin 隔離（importlinter Rule 1）**：rtm_writeback 讀 `ctx.playbook.tasks[i].spec_digest`（PlaybookTask 屬性），**非**跨 plugin import SddGovernancePlugin → 不破契約。digest 經 forward adapter 內嵌於 task 結構欄＝單一真相源傳遞。✅
4. **安全/對外 I/O**：不新增「文件生成指令」路徑、不弱化 CONDITIONAL、不新增 `ToolInvocationPort` 外呼。純本地資料流。✅
5. **誠實性/零退化**：既有 `test_writes_two_reports`（無結構欄、prompt 帶 digest）走 fallback 仍得 "abcdef12" → 不破；A 軸級別誠實標 progress toward L4。免 Copy-on-Evolve、免五軌 TLC。floor=3248。✅

### 設計 delta

- **W-56-2（DEF-56-001）spec_digest 閉環署名不變量**：
  - `models/playbook.py`：`PlaybookTask` 加 `spec_digest: Optional[str] = None`。
  - `sdd_to_playbook_adapter.py:compile_tasks`：對每個 SDD task 填 `spec_digest=spec.digest`（權威全 `sha256:...`）；prompt 內 `(digest {digest8})` 留作人類可讀提示（零行為變化）。
  - `rtm_writeback_plugin.py:_extract_digest`：優先讀結構化欄（首個非空），缺漏才回退 prompt 正則反解（向後相容、零退化）。
- **W-56-1 真實規模雙向 e2e 信號**：
  - 新 `tests/integration/test_sdd_bridge/test_bridge_rtm_e2e.py`：複用 multi_ac 3AC/6AT 真實規格 → sdd_compile → PlaybookKernel（真 SddGovernancePlugin + 真 RtmWritebackPlugin + 真 PlaybookToRtmAdapter + 捕獲 sink）→ 驗 kernel POST_RUN 觸發之**逆向覆蓋報告**。

## 4. 階段三：實作與雙重驗證

### W-56-2（修復 DEF-56-001）
3 處 surgical 改動如 §3 delta。新測 `test_rtm_writeback_plugin.py::TestDigestProvenanceInvariant` **4 case**：結構欄帶完整 sha256（非 8 字元截斷）／結構欄與 prompt 相異時結構欄勝出（杜絕漂移）／無結構欄回退 prompt（向後相容）／forward adapter 對 task 填全 digest。

### W-56-1（真實規模雙向 e2e）
新測 `test_bridge_rtm_e2e.py::TestBidirectionalChainE2E` **3 case**：正向 6 步全綠 + 逆向報告 3 AC 全覆蓋/6 AT 全通過／逆向報告帶權威全 digest（W-56-2 不變量於 e2e 脈絡成立）／部分覆蓋正確標記未覆蓋 AC（非 happy-path-only 空殼）。

### 受控突變實證非空殼（Rule 9）
- **M-W562**（停用結構欄讀取 `if False and structured`）→ `test_structured_field_carries_full_digest` + `test_structured_field_wins_over_divergent_prompt` 轉紅、其餘 2 維持綠，還原後 4 passed、grep `if False` 零殘留。
- **M-W561**（forward `spec_digest=None`）→ e2e `test_reverse_report_carries_full_authoritative_digest` 轉紅（`full_digest=None` 斷言失敗），還原後綠。
- 兩突變經 parent 與 QA 鏡**獨立各跑一次**、皆還原 git CLEAN。

## 5. 階段四：CI 平價收斂（零退化矩陣，parent 親跑）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3248 / 0 failed | ✅ **3255 passed / 122 skipped / 0 failed**（3248+7） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept / 0 broken | ✅ **8 kept / 0 broken** |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | ✅ violations=0（playbook.py data 74/150、adapter 342/400、plugin 107/250） |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | ✅ OK |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0 | ✅ **未動 AISDLC_SDD/ 任一檔 → 維持階段一 exit 0 / v0.21:1654**（git status 零 SDD 變更） |
| DAL 等價 | equivalence | 三後端等價 | ✅ 未動 DAL；spec_digest 為 additive Optional 欄 |
| 五軌 TLC | — | — | **N/A**（未動 FSM/`*.tla`/transition_rules） |

> 3255 = 3248 floor + 7 新測試（4 W-56-2 + 3 W-56-1，只增不減、0 failed＝零退化）。

## 6. RTM（本輪需求追溯）

| 需求 | 驗收標準 | 證據 | 狀態 |
|------|---------|------|------|
| R-56-1 真實規模雙向 e2e 信號 | 逆向橋接首次在 kernel e2e（3AC/6AT）+ 全綠/部分覆蓋兩態 | §4 W-56-1 + test_bridge_rtm_e2e 3 case | ✅ |
| R-56-2 spec_digest 閉環不變量（修復 DEF-56-001） | 逆向報告帶權威全 digest、非 prompt 截斷；結構欄勝出、fallback 相容 | §4 W-56-2 + TestDigestProvenanceInvariant 4 case | ✅ |
| R-56-3 零退化 / 免 Copy-on-Evolve / 免 TLC | pytest 3255≥3248 0 failed；未動 SDD 本體與 *.tla | §5 矩陣 | ✅ |
| R-56-4 回歸鎖非空殼 | M-W561/M-W562 受控突變轉紅、還原綠 | §4 突變實證 | ✅ |
| R-56-5 三鏡 zero-trust 全 PASS | Architect/SA-SD/QA 主樹獨立審查 | `AutoSDD_ZeroTrust_Audit_56.md` | ✅（見 §7） |
| R-56-6 A 軸級別誠實標註 | progress toward L4（2/3）、非達成；合體仍 L3 | 本文結論先行 + §2.2 + §8 | ✅ |

## 7. 三鏡 zero-trust 結果

**Architect / SA-SD / QA 全 OVERALL PASS、P0=P1=0**（詳見 `docs/06_quality/AutoSDD_ZeroTrust_Audit_56.md`）。標的含 1 untracked 新測試檔 → 依 **DEF-24-001「審 untracked 新檔走主樹」鐵律**，三鏡皆主樹派發、禁 worktree。SA-SD P2-1（誠實性標註）已於本文 §8 遵守；QA P2-001（數字 218 vs 106）經 parent 核實＝命令範圍差異（106 三路徑 + 112 yaml_import = 218 四路徑），**非虛假基線、非缺陷**，權威零退化數＝全套 3255。

## 8. 結論與誠實級別標註

三軸實測揭露 `L_合體=min(A=L3,B=L3,C=L5)=L3`，A 與 B 雙瓶頸；掌舵者裁定本輪先攻 A。本輪以 additive、整合層（免 Copy-on-Evolve）、免五軌 TLC 的低風險路徑，補齊 **A 軸 L4 三缺口中的 2 個**：

- **W-56-1**：逆向橋接（RtmWritebackPlugin → RtmCoverageReport）**首次在 PlaybookKernel 內以 3AC/6AT 真實規格 e2e 跑過**（含部分覆蓋態），把 A 軸從「smoke/合成 executor」提升至「真實規模雙向全鏈驗證」。
- **W-56-2（DEF-56-001 fixed）**：把逆向報告 spec_digest 從「全 sha256 截斷成 8 字元 + prompt 正則反解」雙重脆弱漂移，重構為「forward 填權威全 digest 至 PlaybookTask 結構化欄 → reverse 優先讀結構欄」單一真相源閉環（prompt 反解降為向後相容 fallback），承襲 DEF-31/41 負向斷言保真度家族紀律。

**🔴 誠實級別標註（遵 SA-SD 鏡 P2-1 + maturity rubric zero-trust）**：本輪＝**progress toward A-L4（補 2/3 缺口）**，**非達成 L4**——第 3 缺口（goal/spec→playbook 端到端**無人工 FSM 凍結 / signoff** 膠水）本輪未做（25% 人工膠水仍在）；且 B 軸仍卡 L3（AUTO_RECOVERY 預設 OFF）。故 **`L_合體` 維持 L3**，未推動北極星合體針。要把合體推到 L4 須 A（補第 3 缺口）+ B（auto-recovery 常態化，須審慎 signoff，恐觸 TLC）並進，屬後續多輪工程。

**延後（justified，維持原狀態）**：A 軸第 3 缺口「無人工 FSM 凍結註冊」（需新 port + 設計，宜獨立輪）、B 軸 AUTO_RECOVERY 常態化（動 FSM 行為恐觸 TLC、屬治理/安全政策翻轉須審慎 signoff）、DEF-53-001（latent）、DEF-01-007（cc-switch 環境）、DEF-01-009（LOC watch）。

**回流**：DEF-56-001 → fixed@improving_56（整合層就地修，免 Copy-on-Evolve；人工 signoff＝掌舵者 A 軌方向裁定）。
