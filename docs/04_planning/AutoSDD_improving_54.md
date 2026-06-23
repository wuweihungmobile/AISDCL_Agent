# AutoSDD improving_54 — B 軌設計探索：其他守門機制覆蓋度量（Governance Guard-Coverage Instrument）

> **軌道定位**：軌道① **B 軌**（手腳 AISLDC_SDD 框架本體 dogfooding，柱②）。本輪性質＝**SCG-0/1 設計探索**（非實作輪）。
> **標的**：DEF-19-001 於 improving_40 收尾（W-39-1 / DEF-39-001）時點名的後續 B 軌標的——「**其他守門機制覆蓋度量**」。FSM-escalation catch 機制已達結構天花板（7/7=100%），但其餘 **32 條** active 規則（hook / lint·TLC / meta-loop / manual 四類）的「守門機制是否真實存在且接線」**目前零度量**。
> **下一份**：實作輪 `AutoSDD_improving_55.md`（**俟本藍圖 🔴 掌舵者 signoff 後**）。
> **日期**：2026-06-24。
> **掌舵者裁定**：本輪以 AskUserQuestion 兩階段拍板——(1) 修正：先前誤列的 DEF-31-001/30-001/32-002 經 zero-trust 親讀皆已 fixed，帳本內無「乾淨可修且不違 Rule 2」的 in-repo 缺陷（穩態輪）；(2) 改派「**開新 B 軌設計探索**」推進 DEF-19-001 點名之後續標的。
> **結論先行**：本輪**不動實作**。產出＝守門機制覆蓋度量的 **SCG-0/1 設計藍圖 + 規格草案**，核心設計決策＝把「覆蓋」誠實重構為「**每條規則宣稱的守門機制是否真實存在且接線**」（靜態-結構覆蓋，抓 guard bit-rot），對 (E) 人工/憲法類**誠實排除於自動分母**。實作落點規劃為 Copy-on-Evolve **v0.21**，MVP 範圍 **不觸 `_HAPPY_PATH`/`*.tla`**（不觸發五軌 TLC）。**待 signoff。**

---

## 1. 本輪輸入（自上輪繼承）

- 上輪＝improving_53（B 軌；Copy-on-Evolve v0.20 清償 DEF-CLDREV-030，commit `f87f7dc`；歸檔 commit `22782fe`）。工作樹乾淨。
- 缺陷帳本 open/routed 盤點（**本輪 zero-trust 親讀各 DEF canonical 狀態欄**，糾正先前憑舊輪 prose 子字串的誤判）：

| 缺陷 | canonical 狀態 | 本輪處置 |
|---|---|---|
| DEF-31-001 / DEF-30-001 / DEF-32-002 / DEF-23-005 / DEF-41-001 | **fixed**（@improving_33/33/40/30/41） | 已交付，無動作 |
| DEF-17-001（fire）/ DEF-18-001（catch 契約） | **fixed**（@improving_18 / v0.10） | 已交付 |
| DEF-19-001（catch 覆蓋 7/39） | **closed@improving_40**（milestone，🔴 掌舵者拍板：FSM-escalation 7/7=100% 達結構天花板） | **本輪標的＝其點名之後續「其他守門機制覆蓋度量」** |
| DEF-53-001（hub_merge 未 cap） | **routed latent**（justified deferral：現修＝speculative 違 Rule 2，附觸發閘） | 維持 routed，不動（符合其 deferral 理由） |
| DEF-01-007（cc-switch） | **open**（環境工具缺裝，非倉內可修） | 維持 open，本輪不涉多後端 |
| DEF-01-009（LOC watch） | **open watch**（本輪零擴充不觸發） | 維持 |

- 上輪審計遺留：無 partial、無未竟修復。

## 2. 階段一：現況重偵察（Zero-Trust Re-Audit）

| 項目 | 命令 | 實測（parent 親跑，非沿用文件） |
|------|------|------|
| HEAD 真相 | `git status --short` + `git log --oneline -3` | HEAD=`22782fe`；工作樹乾淨 |
| **B 軌零退化主基線** | `bash scripts/ci-gate.sh` | **exit 0**；逐軌 **v0.01:1478 / v0.20:1646 / scripts:127**；arch_fitness 僅 advisory warn（FF-16 類，structural pass）；SSOT 全 lint 綠（skill-header v0.20 / skills-ssot 59 檔 / router hook 三 event 可達 / gitignore / agent template / collaboration / scenario frequency） |
| 與上輪比對 | — | 與 improving_53 紀錄逐軌零漂移 |
| invocation 形態（紀律 (f)） | — | 本輪純框架本體設計，無外部 CLI/GUI/API 依賴；headless 可驗證 |

**硬閘**：基線無 failed、未低於上輪 floor（v0.20 1646 == floor）→ 通過，進入階段二。

> **零信任修正紀錄（誠實揭露，[[no-fabricated-tool-output]] + 紀律#17）**：
> 1. 初次 AskUserQuestion 選項把 DEF-31-001/30-001/32-002 列為「B 軌 routed 待清」係**錯誤**——根因＝grep `open|routed` 命中各 DEF 長狀態欄的**舊輪歷史 prose 子字串**，未核對 canonical 末狀態。親讀後三者皆已 fixed，且 DEF-31-001 之 `_NEGATION_MARKER` 根本在 **AutoClaude 整合層**（`infra/adapters/sdd_to_playbook_adapter.py:75`）非 SDD 框架本體。已對掌舵者誠實上報並重新裁定。
> 2. 階段一基線曾由一個 Explore agent 回報「ci-gate exit 0 / 1478/1646/127」但該 agent **超 token 中途結束**、數字與文件完全一致、無親跑佐證 → **不採信**，由 parent 親跑取得上表數字。

## 3. 問題界定（zero-trust 親讀基質後）

### 3.1 W-39-1 五分類（improving_40 收尾之機械分類，**目前僅存於 archive prose**）

| 類 | 守門機制 | 規則數 | 代表 rule_id（待實作輪逐一複驗） |
|---|---|---|---|
| **A** | FSM escalation（`record_escalation` → `catch_count`） | 7 | R-9.1 / R-9.2 / R-9.3 / R-9.7 / R-9.21 / R-9.22 / R-SELF-STRIDE |
| **B** | hook 攔截（`.claude/hooks/` deny） | 3 | R-9.4 / R-9.6 / R-9.8 |
| **C** | lint · TLC · arch_fitness | 3 | R-9.5 / R-9.9 / R-9.18 |
| **D** | meta-loop guard（meta_halt / ChurnBounded / GraduationRatchet + META_FSM.tla） | 14 | R-9.24 ~ R-9.37 |
| **E** | manual · advisory · 憲法（人工簽核 / 純規範） | 12 | R-9.10 ~ R-9.20 部分 / R-9.23 / R-9.38 |
| | | **39** | |

> 出處：`docs/04_planning/Archive/AutoSDD_improving_39.md` §2（L69-82）、`AutoSDD_ZeroTrust_Audit_39.md` §2（L37-45）。現有 catch 度量器：`AISDLC_SDD_v0.20/tools/fsm_runtime/fsm_runtime.py:1741-1833`（`rule_fire_telemetry_stats`）；SSOT 常數 `_ESCALATION_ATTRIBUTABLE_RULE_IDS`（同檔 L231-233）。

### 3.2 誠實洞察：32 條並非全部可有意義「度量覆蓋」

| 類 | 「守門 runtime 是否有效」可自動度量？ | 「守門機制是否真實存在且接線」可自動度量？ |
|---|---|---|
| A（escalation） | ✅ 已有（catch_count，7/7） | ✅ escalation 落點存在 |
| B（hook） | ❌ 需埋 runtime fire 計數（**本輪延後**，speculative until consumer） | ✅ hook 已掛載 + event 可達（靜態） |
| C（lint·TLC） | ⚠️ R-9.18 TLC 有磁碟產出可量；R-9.9 chaos 須 nightly；R-9.5 lint 僅 pass/fail | ✅ 對應 check 存在且最近一次綠 |
| D（meta-loop） | ⚠️ 多為形式化證明（TLC）非 runtime 計數；churn 計數需新接線（**本輪延後**） | ✅ 對應 META_FSM property + 測試存在 |
| E（manual） | ❌ **本質不可自動度量**（＝人是否遵守簽核） | ❌ 無「機制接線」可驗（純人工） |

**結論**：硬做「全 32 條 runtime 有效性度量」＝過度工程 + 部分不可能（違 Rule 2、違 DEF-18-001「擅自映射比不做更糟」紀律）。**正確設計**＝把「覆蓋」重構為**靜態-結構覆蓋**：「每條 active 規則宣稱的守門機制，其守護構件（escalation 落點 / hook 接線 / lint·TLC check / META_FSM property+測試）是否真實存在」，並對 E 類**誠實標記、排除於自動分母**。此度量的真實價值＝**抓 guard bit-rot**（規則還在、但守門被誤刪/未接 → 假性受保護）。

## 4. 階段二：本輪增量設計（MVP，≤2 W 項；**設計層，待 signoff**）

### W-54-1：守門機制分類 SSOT（machine-readable taxonomy）
把 W-39-1 的 archive prose 分類**固化為機讀 SSOT**：為每條 active R-*.yaml 增 additive 欄 `enforcement_mechanism: escalation | hook | lint_tlc | meta_loop | manual`（或集中映射檔，二擇一見 §4.3 待決）。配 lint 斷言：**全部 active 規則恰分入五類之一、且 A 類成員 == 既有 `_ESCALATION_ATTRIBUTABLE_RULE_IDS`**（與既有 SSOT 交叉鎖、防漂移）。
- **介面 delta**：規則 YAML additive 欄（向後相容，舊讀取者忽略）；新 lint `tools/.../enforcement_mechanism_lint`（或併入 arch_fitness 一條 advisory→enforcing FF）。
- **價值**：消除「分類只存在於 archive 散文、無單一真相源」之框架摩擦（→ 新記 **DEF-54-001**）。

### W-54-2：誠實守門覆蓋證書（comprehensive guard-coverage certificate）
新增 API（規劃 `comprehensive_governance_coverage()`，與 `rule_fire_telemetry_stats` 並列或內含）回傳**每類「宣稱守門構件是否存在」之靜態驗證**：
- A：沿用既有 `catch_attribution_coverage`（7/7）。
- B：每條 hook 類規則 → 其指定 hook event 在 `.claude/settings.json`（root router ∩ 版本）可達（復用既有 router hook coverage lint 的判定）。
- C：每條 → 對應 lint/TLC check 存在（R-9.18 → `formal/*.tla` + cfg 存在；R-9.5/R-9.9 → 對應 test_ref 存在且非 skip）。
- D：每條 → META_FSM.tla 對應 property + test_ref 存在。
- E：**誠實排除**——標 `auto_measurable=false`、附 `denominator_note`（沿用 A 類既有誠實分母慣例），不灌假數字。
- 證書欄位 additive；fail-closed（度量失敗不阻塞 FSM、不偽綠）。
- **價值**：全 39 條治理面一眼可見「哪些守門構件真實在位、哪些本質人工」；bit-rot 偵測（規則宣稱 hook 守但 hook 被刪 → 該條覆蓋轉紅）。

### 明確延後（justified，[[no-defer-unless-justified]] 之「不做有優點/需設計決策」類）
- **B 類 hook runtime fire 計數**、**D 類 churn-per-rule runtime 計數**：屬「runtime 有效性度量」，需埋點且**目前無消費者**（無自動退役消費這些數字）→ speculative，違 Rule 2；且 D 類涉 meta_halt 可能動 META_FSM.tla（觸發五軌 TLC）。延後至「有消費者 + 與 wiring 同落點」之未來輪。
- **R-9.9 chaos 度量啟用**：屬 CI 配置（nightly），非框架本體；另案。

### LOC / 契約 / TLC 影響（MVP）
- 落點 `tools/fsm_runtime/`（非 AutoClaude `autoclaude/` 套件）→ **不受 AutoClaude `.importlinter` 8 contract 約束**；新 API 為 additive，無 God-object。
- **不碰 `transition_rules.py` / `_HAPPY_PATH` / `*.tla`** → **不觸發五軌 TLC**（MVP 純讀取既有 yaml/檔案存在性 + 既有 lint 判定）。
- checkpoint additive 欄位：無（不碰 PlaybookCheckpoint / FSM-STATE）。
- Copy-on-Evolve：v0.20 凍結 → 複製 **v0.21** 後修改 + `EVOLUTION_LOG.md` + `releases/CHANGELOG.md`。

### 4.3 待 signoff 決策點（呈掌舵者）
1. **分類落點**：(a) 每條 R-*.yaml 加 `enforcement_mechanism` 欄〔分散、與規則同源〕 vs (b) 集中映射檔 `governance/ENFORCEMENT_MECHANISM_MAP.yaml`〔單檔、易 review〕。**建議 (a)**（與規則 co-located、防漂移、與既有 `failure_mode` 欄一致）。
2. **本輪是否含實作**：本藍圖定位設計探索；建議 W-54-1/W-54-2 實作落**下一輪 improving_55**（signoff 後），本輪僅交付藍圖+規格。
3. **E 類呈現**：確認「誠實排除於自動分母 + 標 auto_measurable=false」之處理（而非強湊覆蓋率）符合掌舵者期待。

## 5. <Architecture_Design_Review>（寫任何實質 Python 前）

1. **架構純潔性**：新增為純讀取 helper + additive 證書欄 + lint，無 God-object；不動 FSM transition、不改 Thin Facade。✅（設計層）
2. **持久化相容**：不碰 PlaybookCheckpoint / FSM-STATE / DAL；證書為唯讀計算。✅
3. **安全防護網**：本輪不新增「從文件生成指令」路徑、不弱化 CONDITIONAL 三層防禦。✅
4. **對外 I/O 安全**：本輪不新增 `ToolInvocationPort` 外呼路徑（純本地檔案/yaml 讀取）。✅
5. **誠實性紅線**：E 類不可灌假覆蓋率（沿用 denominator_note 紀律）；度量失敗 fail-closed 不偽綠。✅

## 6. SCG-0/1 規格草案（供 signoff）

**SCG-0 需求凍結（候選）**
- R-54-1：全 39 條 active 規則具機讀守門機制分類，single source of truth，lint 機械守「全分類 + A 類與既有 escalation SSOT 一致」。
- R-54-2：提供誠實守門覆蓋證書，逐類報「宣稱守門構件是否真實在位」，E 類誠實排除、fail-closed、不偽綠。
- R-54-3（非功能）：零退化（ci-gate exit 0、≥ floor 1646）；不觸發五軌 TLC；Copy-on-Evolve v0.21 凍結本體不就地改。

**SCG-1 設計（候選）**：見 §4 W-54-1/W-54-2 介面 delta。

**DoD（草案）**
- 技術：v0.21 落地 taxonomy 欄 + lint + 覆蓋證書 API；39 條全分類；A 類交叉鎖綠。
- 形式化同構：MVP 不動 `*.tla` → 附「formal/ 與 transition_rules 對 v0.20 逐位元零差異」證據即免 TLC（沿用 improving_53 慣例）。
- 誠實性：E 類 auto_measurable=false + denominator_note；證書 fail-closed 測試。
- 回歸鎖：Rule 9 非空殼——受控突變（刪一條規則的守門構件 → 對應覆蓋轉紅；竄改分類 → lint 轉紅）。
- 零退化矩陣全綠（§見範本階段四）。
- 四鏡 zero-trust 全 PASS。

## 7. RTM（設計輪骨架，實作輪填證據）

| 需求 | 驗收標準 | 證據 | 狀態 |
|------|---------|------|------|
| R-54-1 守門機制分類 SSOT | 39 條全分類 + lint + A 類交叉鎖 | （improving_55 實作） | 🔵 設計待 signoff |
| R-54-2 誠實覆蓋證書 | 逐類靜態驗證 + E 類誠實排除 + fail-closed | （improving_55 實作） | 🔵 設計待 signoff |
| R-54-3 零退化 / Copy-on-Evolve v0.21 / 免 TLC | ci-gate exit 0 ≥1646；formal 零差異 | （improving_55 實作） | 🔵 設計待 signoff |

## 8. 結論（本輪交付）

本輪為 **B 軌設計探索**（非實作輪）。zero-trust 親讀確立帳本內無「乾淨可修且不違 Rule 2」之 in-repo 缺陷（穩態），改推 DEF-19-001 點名之「其他守門機制覆蓋度量」。核心設計決策＝把不可能的「守門 runtime 有效性度量」**誠實重構為可驗證的「守門機制存在性/接線」靜態覆蓋**，對 E 類誠實排除——直接回應 DEF-18-001/19-001 家族「寧缺勿濫、不灌假信號」紀律。MVP（W-54-1 taxonomy SSOT + W-54-2 誠實覆蓋證書）落 Copy-on-Evolve v0.21、**不觸發五軌 TLC**；runtime 計數類深度埋點明確延後（justified）。

**🔴 待掌舵者 signoff**（§4.3 三決策點）。核可後開 `AutoSDD_improving_55.md` 進入實作（階段三/四 + 四鏡）。

**本輪新記缺陷**：**DEF-54-001**（P3，框架治理摩擦）——守門機制五分類僅存於 archive 散文、無機讀 SSOT，本藍圖 W-54-1 即為其修復提案。詳見 Defect_Log。
