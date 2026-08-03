# AutoSDD_ZeroTrust_Audit_86 — per-step token% 可觀測性 emit + 真跑填值

> **本輪**：improving_86（A 軌 × C 軌）。三鏡 Architect / SA-SD / QA 主樹並行唯讀審查（含 untracked 新檔 → 依 DEF-24-001 禁 worktree；突變由主 agent 序列完成還原、審查鏡不就地突變，避開 [[parallel-mutation-audit-collision]]）。

## 1 階段一零信任重偵察（硬閘 PASS）
| 項目 | 實測 |
|------|------|
| AutoClaude pytest | 3493 / 0 / 122（floor 3488） |
| lint-imports | 8 kept / 0 broken |
| LOC | violations=0 |
| snapshot | OK |
| AISDLC_SDD ci-gate | exit 0（v0.01:1478 / v0.27:1665 / scripts:129） |
| git 工作樹 | 乾淨 |
| 上輪構件 | spec_format_version 欄 / load_spec 寫入 / sdd_compile 退碼 5 / v0.27 4 TCS 模板宣告 全存在 |

真跑探測（improving_77/81 紀律）：單輪 pty smoke `KernelResult.peak_token_pct=6.1566`、`TOKEN_COMPACT/HALT`=0、per-step token% 不存在 → 坐實「低負載 per-step token% 恆 0%」缺口，定本輪設計。

## 2 實作與雙重驗證
- **W-86-1**（kernel.py:197-201）：`STEP_TOKEN_PEAK` 可觀測標記，guard `observer.peak_pct>0`，observability-only。core 318 passed。
- **W-86-2**（ab_compare_backends.py）：`_RE_STEP_TOKEN_PEAK` + parse 進 per_step + StepAggregate + per_step_agg + aggregate_runs per-step 聚合 + format_step_aggregate_comparison。載具 65 passed。
- **8 新測**（RTM-86-1~5）；3 受控突變（MUT-86-1/2/3）全轉紅、Edit 還原無殘留（禁 git checkout）。

## 3 真跑取證（W-86-3）
- 單輪 pty：production log 印 `STEP_TOKEN_PEAK | step=S01/S02 pct=6.x`，整輪 peak = 各步 max（一致）。
- N=2 完整 A/B：per-step 多輪聚合首次有真值——S01/S02 各 **pty 6% vs sdk 2%（n=2）**（修前恆 0%）。

## 4 三鏡 zero-trust 複審結果

### Architect — OVERALL PASS（P0=0/P1=0）
(a) observability-only 確認（emit 在 execute 後/consult 前、無 return/raise/賦值、不改控制流）；(b) LOC violations=0；(c) 8 kept/0 broken、無新 import；(d) core 318 passed；(e) 零碰 AISLDC_SDD；(f) 無 checkpoint/DAL 改動。

### SA-SD — OVERALL PASS（P0=0/P1=0）
(a) 親跑端到端流動（S01 6.0580/S02 6.1726，整輪=各步 max 一致）；(b) 載具三來源（per_step / 整輪 marker peak / observer KernelResult）職責切分清楚無污染；(c) per-step 聚合 n 反映實際出現輪數正確；(d) 親驗 MUT 轉紅證新測非空殼；(e) 計畫書 §3/§4/§5 與現況相符。
- **非阻斷觀察**：真跑 pct 數值浮動 → 已於計畫書 §4.3 加「真跑浮動註記」當場閉環。

### QA — OVERALL PASS（P0=0/P1=0）
(a) 全套 3501/0/122（命中 floor 3488 + 基線 3493 +8）；(b) 8 具名新測存在且通過；(c) lint 8 kept、LOC 0；(d) RTM-86-2 對 guard 退化敏感（非空殼）；(e) 缺陷帳本誠實「無新 DEF」+ §8 誠實限制無誇大；(f) §5 數字與親跑一致、`args.max_steps` 無懸空引用。

## 5 零退化驗證矩陣（實測）
pytest 3501/0/122 ✅｜lint 8 kept ✅｜LOC 0 ✅｜snapshot OK ✅｜ci-gate N/A 類型①（零碰 AISLDC_SDD）✅｜DAL 等價 N/A 類型②✅｜五軌 TLC N/A 類型①✅

## 6 結論
三鏡全 OVERALL PASS、P0=0/P1=0；一個非阻斷觀察當場閉環。本輪無新增 DEF。`L_合體=L5` 維持。**結案放行**。
