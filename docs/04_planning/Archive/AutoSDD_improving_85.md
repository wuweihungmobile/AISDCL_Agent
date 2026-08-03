# AutoSDD_improving_85 — A 軌：spec-format-version「生產端」閃閉（Copy-on-Evolve v0.27）+ 消費端收尾

> **軌道**：① 整合迭代 / **A 柱（雙向協作橋接 — 北極星第 3 點）**，連動 B 柱（框架 Copy-on-Evolve v0.27）
> **下一份**：`AutoSDD_improving_86.md`
> **驅動器**：`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md`
> **狀態**：階段二設計落地（§1-§3 先寫）→ 階段三/四回填（§4 實作/真跑、§5 驗證矩陣實測欄）
> **規格先行聲明**：本檔於動任何 code / Copy-on-Evolve 前先落地（§1 輸入 / §2 階段一實測 / §3 增量設計含 `<Architecture_Design_Review>`、介面 delta、RTM）。§4 實作紀錄、§5「本輪實測」欄為階段三/四回填，非事後補寫。

---

## §1 本輪輸入（自上輪繼承）

### 1.1 上輪（improving_84）已完成 W 項
- **W-84-1/2/3**：token-guard compact/halt 編排「端到端真跑」首證 + 可重跑驗證載具（C 軌）。
- **W-84-4**：修 DEF-84-001（compact decay floor=65 默夾 config 低門檻）。
- 結案實測 3488 passed / 0 failed / 122 skipped、framework v0.26、L_合體 L5。

### 1.2 上輪交棒（improving_84 結論明示的 85 候選）
> 「其餘候選見記憶檔：SD_09 W1 時間閘 ~6/29、**A 軌 spec-format-version producer**。」掌舵者本輪拍板鎖定 **A 軌 spec-format-version producer**（見 §1.4）。

### 1.3 缺陷帳本（`AutoSDD_Defect_Log.md`）open/routed 複驗（階段一）
- **DEF-01-007**（cc-switch GUI，P3）：open，本輪不涉多後端 A/B profile 切換，未觸發。
- **DEF-01-009**（`sdd_governance_plugin.py` LOC watch，P3）：open watch，本輪零碰該檔，不觸發。
- **DEF-19-001**（catch 漸進覆蓋，routed）/ **DEF-17-001**（fire 側遙測，routed）/ **DEF-23-005**（RFC 生命週期自動化，P3）/ **DEF-35-001**（goal_synthesis mutmut 目錄，P2，C 軌 SD_09）/ **DEF-62-001**（auto_recovery 註解滯後，P3）：皆非本輪 scope，未推進，維持原狀態。

### 1.4 掌舵者本輪拍板（AskUserQuestion 紀錄）
1. **本輪 scope（哪一柱）**：**A 軌 spec-format-version producer**——推進雙向協作橋接（北極星第 3 點 / 成熟度量表綁定約束 `L_合體=min(A,B,C)`、`A≤min(B,C)`，三軸須一起升）。
2. **生產端策略**：**Copy-on-Evolve v0.27（閃閉端到端）**——讓 SDD 框架的 TCS 模板真的宣告 `spec-format-version`（生產端），配合 AutoClaude 消費端收尾，首次讓 improving_67 的防漂移閘端到端可驗證。

---

## §2 階段一：現況重偵察（Zero-Trust Re-Audit，實測）

### 2.1 基線實測（硬閘：無 failed、≥ 上輪 floor 3488）
| 檢查 | 命令 | 本輪實測 | 結果 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | **3488 passed / 0 failed / 122 skipped** | ✅ = floor |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | **violations=0**（total=19768 / cap=20438） | ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | **OK** | ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **PASS**（exit 0；v0.01 1478 + v0.26 1665 + scripts 129；arch_fitness fail=0 / 3 advisory warn） | ✅ |
| git 工作樹 | `git status` | **clean** | ✅ |

> 硬閘通過：基線等於上輪 floor 3488、零 failed，准進階段二。

### 2.2 A 軌橋接現況勘查（zero-trust，親查 file:line）
- **消費端 validator 已存在**（improving_67 W-67-2）：`infra/adapters/sdd_to_playbook_adapter.py:181-205` `_check_spec_format_version`——擷取 `spec-format-version`、缺欄預設 1.0 放行、宣告值不在 `_SUPPORTED_SPEC_FORMAT_VERSIONS={"1.0"}` 則 raise `SpecFormatVersionError`，無論放行/拒絕皆經 IObservabilityPort 留痕。
- **錨定 regex**：`sdd_to_playbook_adapter.py:94` `_SPEC_VERSION_RE = re.compile(r"spec[-_ ]format[-_ ]version\D{0,4}(\d+\.\d+)", re.I)`。
- **port 契約**：`core/ports/spec_source.py:35-40` `SpecFormatVersionError`；`SddSpec`（:56-63）含 spec_path/digest/scenario/contracts，**無 spec_format_version 欄**。

### 2.3 缺口認定（本輪存在理由 — A 軌橋接單邊性）
improving_67 建了**消費端 validator**，但生產↔消費契約是**單邊的**：
1. **生產端缺席**：SDD 框架的 TCS 模板（`AISDLC_SDD_v0.26/docs_template/sdd/testing/*CONTRACT*SPEC*.md`）**完全不宣告** `spec-format-version`（實測 grep v0.26 docs_template 零命中）。故框架產出的每份 spec 都缺欄 → 消費端只能靜默 fallback 預設 1.0。
2. **防漂移閘端到端從未真正被觸發**：因生產端從不戳版本，`_check_spec_format_version` 對真實框架 spec 永遠走「缺欄→預設」分支（`declared=False`），版本漂移偵測對真實 spec 是**死碼**（只有手工編造 `2.0` 才會 fire）。
3. **消費端已驗證的版本被丟棄**：`load_spec`（`sdd_to_playbook_adapter.py:121-131`）呼叫 `_check_spec_format_version(text)` 但**未接回傳值**，版本驗證後即丟，未存入 `SddSpec`。
4. **消費端 CLI 漏接版本錯誤**：`autoclaude/tools/sdd_compile.py:85-93` `main()` 的 except 子句接 `SpecNotFrozenError`/`SpecTaintedError`/`FileNotFoundError`/`ValueError`，**未接 `SpecFormatVersionError`** → 版本漂移時噴未捕捉 traceback + exit 1（非乾淨退碼）。

**本輪閃閉這條協作橋接**：生產端（框架模板宣告版本，Copy-on-Evolve v0.27）+ 消費端收尾（版本表面化到 SddSpec + CLI 乾淨退碼），使防漂移閘首次端到端可驗證（真實框架 spec 帶 `declared=True`）。

---

## §3 階段二：本輪增量設計

### 3.1 本輪 W 項（≤3）
| W 項 | 內容 | 類型 | 觸碰面 |
|------|------|------|--------|
| **W-85-1**（B 柱／生產端） | Copy-on-Evolve v0.26→v0.27；在 4 份 `*CONTRACT*SPEC*` 模板宣告 `spec-format-version: 1.0`；EVOLUTION_LOG + CHANGELOG；重生 FRAMEWORK_STATUS | 框架本體（Copy-on-Evolve） | `AISDLC_SDD/AISDLC_SDD_v0.27/`（新凍結版） |
| **W-85-2**（A 柱／消費端收尾） | `SddSpec` additive `spec_format_version` 欄（default "1.0"）；`load_spec` 接回驗證版本不再丟棄；`sdd_compile.main()` 接 `SpecFormatVersionError` 乾淨退碼 | production（additive） | `core/ports/spec_source.py` + `infra/adapters/sdd_to_playbook_adapter.py` + `autoclaude/tools/sdd_compile.py` |
| **W-85-3**（測試 / 端到端契約） | 生產→消費 round-trip 測試（宣告版本 spec → SddSpec.spec_format_version + declared=True）；向後相容（缺欄→1.0）；不支援版本→CLI 乾淨退碼；受控突變 | 測試 | `tests/infra/` + `tests/tools/` |

### 3.2 W-85-1 介面 delta — 生產端模板宣告（Copy-on-Evolve v0.27）
- 工具：官方 `scripts/copy_on_evolve.sh AISDLC_SDD_v0.26 AISDLC_SDD_v0.27`（git archive 純 tracked，結構性排除 runtime bloat；自動跑 skill_header_sync --write 升戳記 v0.27 + sync_exposed_skills --write 重生父層鏡像 + 補 .gitignore block）。
- 模板宣告（4 份，皆為 adapter glob `("CONTRACT" in name and "SPEC" in name) or TCS-*` 命中、會被 `load_spec` 讀取的 spec 生產來源）：
  - `docs_template/sdd/testing/TEST-CONTRACT-SPEC-TEMPLATE.md`（主 TCS）
  - `docs_template/sdd/testing/CONTRACT-TEST-SPEC-INTEGRATION-TEMPLATE.md`
  - `docs_template/sdd/testing/CONTRACT-TEST-SPEC-MIGRATION-TEMPLATE.md`
  - `docs_template/sdd/testing/ENV-CONTRACT-SPEC-TEMPLATE.md`
- 宣告格式（已以 adapter `_SPEC_VERSION_RE` 實測驗證匹配 → `1.0`；table cell / backtick 格式經實測不匹配故避開）：
  ```
  **spec-format-version**: 1.0  <!-- AutoClaude SddToPlaybookAdapter 防漂移閘讀取（_SUPPORTED_SPEC_FORMAT_VERSIONS）；框架 AT 表/Gherkin 格式跨版不相容演進時 bump 並同步 adapter 支援集 -->
  ```
  置於各模板「文件資訊」段（標頭之後、AC→AT 映射表之前），與既有 metadata 欄並列。
- 手動補（helper 未涵蓋）：`v0.27/EVOLUTION_LOG.md` 追加條目 + `v0.27/releases/CHANGELOG.md` 條目 + `python scripts/framework_status_snapshot.py --write`（重生版本 SSOT，使 ci-gate `--check` 新鮮）。

### 3.3 W-85-2 介面 delta — 消費端收尾（AutoClaude，additive 零退化）
1. `core/ports/spec_source.py` — `SddSpec` 加 additive 欄（接在 `contracts` 後，皆有 default 故合法）：
   ```python
   spec_format_version: str = "1.0"  # W-85-2：消費端表面化已驗證版本（生產↔消費橋接閉合）；缺欄 spec 維持 1.0 向後相容
   ```
2. `infra/adapters/sdd_to_playbook_adapter.py:121-131` — `load_spec` 接回驗證版本：
   ```python
   version = self._check_spec_format_version(text)  # 原本丟棄回傳值，本輪接回
   return SddSpec(..., spec_format_version=version)
   ```
   `_check_spec_format_version` 邏輯不變（已 return version；本輪只是讓 caller 接住）。
3. `autoclaude/tools/sdd_compile.py` — `main()` 加 `except SpecFormatVersionError`（import 自 spec_source）→ 乾淨退碼（新 code 5，與既有 2/3/4 不衝突）：
   ```python
   except SpecFormatVersionError as exc:
       print(f"[sdd_compile] 規格格式版本不受支援（防漂移 fail-closed）：{exc}", file=sys.stderr)
       return 5
   ```

### 3.4 `<Architecture_Design_Review>`
```
<Architecture_Design_Review>
1. 架構純潔性：消費端三處皆 surgical additive——SddSpec +1 frozen 欄（default）、load_spec +1
   賦值、sdd_compile +1 except 分支 + 1 import。無 God-object、無新狀態機、無新依賴。
   `_check_spec_format_version` 既有邏輯零改（只讓 caller 接回它早已 return 的值）。Thin Facade
   （playbook_runner）不受影響。生產端純文件（模板宣告 + log），不碰任何 Python 執行碼。
2. 持久化相容：SddSpec 是凍結後規格快照（記憶體 dataclass），非 PlaybookCheckpoint/DAL 持久層；
   新欄 additive 且有 default，不影響任何序列化/三後端。零碰 checkpoint schema。
3. 安全防護網：本輪不新增「從文件生成指令」路徑。版本宣告是被動 metadata 行（被 regex 讀取，
   不進 evaluator 模板、不入 command）。CONDITIONAL 白名單與 _DENY 消毒不受影響。模板宣告值
   "1.0" 為純數字版本，不含黑名單字元。
4. 對外 I/O 安全：本輪零新增 ToolInvocationPort 外呼路徑（無 Web/HTTP/訊息）。
5. LOC：spec_source.py（contract tier ≤400，現 ~97 行）+1；sdd_to_playbook_adapter.py
   （adapter ≤400）+1；sdd_compile.py（plugin_entry ≤250）+3。皆遠低於 tier 上限，violations 維持 0。
6. importlinter：SddSpec 欄新增不改 import 結構；sdd_compile 新增 import 來自既有同模組
   spec_source（已 import SpecNotFrozenError/SpecTaintedError），不觸 8 條 contract 任一。
7. 零退化：新欄有 default "1.0"，既有所有 SddSpec 建構（4 位置參數）與既有缺欄 spec 行為
   逐位元不變（仍 1.0）；既有 sdd_compile 既有退碼 2/3/4 路徑不變（5 為新增分支）。新增測試
   只增不減。B 柱 Copy-on-Evolve：v0.26 凍結唯讀不改，新增 v0.27（git archive 純 tracked，
   ci-gate 雙軌 v0.01+LATEST 自動納入 v0.27 並跑全套 + 全 SSOT lint）。
8. B 軌紅線：v0.26 凍結本體零改（git status 證）；模板修改一律落 v0.27（Copy-on-Evolve）；
   無 _HAPPY_PATH/*.tla 變更（純模板 metadata 行，五軌 TLC 不觸發）。
</Architecture_Design_Review>
```

### 3.5 RTM 需求列（階段三/四回填實測欄）
| RTM ID | 需求 | 驗證方式 | 狀態 |
|--------|------|---------|------|
| RTM-85-1 | v0.27 4 份 TCS 模板宣告 `spec-format-version: 1.0`，且被 adapter `_SPEC_VERSION_RE` 解析為 "1.0" | 模板 grep + adapter 解析測試 | 階段三回填 |
| RTM-85-2 | `SddSpec.spec_format_version` 表面化已驗證版本；宣告版本 spec → declared 路徑 accepted=True | round-trip 測試（fixture spec 含宣告） | 階段三回填 |
| RTM-85-3 | 向後相容：缺欄 spec → spec_format_version=="1.0"、既有行為逐位元不變 | 既有 spec fixture 測試 + 全套零退化 | 階段三回填 |
| RTM-85-4 | 不支援版本（如 "2.0"）→ `sdd_compile.main()` 乾淨退碼 5（非 traceback） | CLI 測試（fixture spec 宣告 2.0） | 階段三回填 |
| RTM-85-5 | 零退化：全套 pytest ≥ 3488 / 0 failed；lint 8 kept；LOC 0；snapshot OK；ci-gate PASS（含 v0.27 雙軌） | 階段四矩陣 | 階段四回填 |
| RTM-85-6 | 受控突變證測試非空殼（Rule 9） | MUT-85-* 轉紅 + Edit 還原 | 階段三回填 |

---

## §4 階段三：實作與雙重驗證

### 4.1 實作逐項紀錄（每項完成即跑單測）
- **W-85-2（消費端收尾，先做純 additive）**：① `core/ports/spec_source.py` `SddSpec` 加 `spec_format_version: str = "1.0"`（接在 contracts 後，皆有 default 故合法）；② `infra/adapters/sdd_to_playbook_adapter.py:121-132` `load_spec` 接回 `version = self._check_spec_format_version(text)` 並 `spec_format_version=version`（`_check_spec_format_version` 邏輯零改，本已 return version）；③ `autoclaude/tools/sdd_compile.py` import `SpecFormatVersionError` + `main()` 加 `except SpecFormatVersionError → return 5`。`tests/infra/test_sdd_to_playbook_adapter.py` + `tests/tools/test_sdd_compile_cli.py` **88 passed**。
- **W-85-1（生產端 Copy-on-Evolve v0.27）**：① `bash scripts/copy_on_evolve.sh AISDLC_SDD_v0.26 AISDLC_SDD_v0.27`（git archive 純 tracked 862 檔；自動 skill_header_sync --write 升戳記 v0.27〔45 檔〕 + sync_exposed_skills --write 重生父層鏡像〔59 檔〕 + 補 .gitignore block）；② 4 份 `*CONTRACT*SPEC*` 模板各加 `**spec-format-version**: 1.0`；③ EVOLUTION_LOG + CHANGELOG 條目；④ `framework_status_snapshot.py --write` 重生 SSOT（`--check` exit 0 新鮮）。
- **生產↔消費 round-trip 鐵證**：4 份 v0.27 模板宣告皆經**真實 adapter `_SPEC_VERSION_RE`** 解析為 "1.0"（`verify_producer.py` 實測 ALL_OK）。

### 4.2 受控突變（Rule 9 證測試非空殼）
- **MUT-85-1**：`load_spec` 的 `spec_format_version=version` → 寫死 `"1.0"`（模擬還原成丟棄解析值）→ `test_surfaced_version_reflects_parsed_value_not_default` 轉紅（`1.1 != 1.0`）。Edit 還原。
- **MUT-85-2**：`sdd_compile` 的 `return 5` → `return 4`（模擬漏接版本錯誤退碼）→ `test_unsupported_spec_version_exit_code_5` 轉紅（`4 != 5`）。Edit 還原。
- 兩突變皆以 Edit 還原（非 git checkout），還原後 88 passed、無殘留。

## §5 階段四：零退化驗證矩陣（實測）

| 檢查 | 命令 | 通過條件（floor=上輪實測） | 本輪實測 | 結果 |
|------|------|------------------------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 3488 passed / 0 failed | **3492–3493 passed / 0 failed / 122–123 skipped**（+5 新測：4 adapter + 1 CLI；**同一支 PG-DSN 條件測試 passed↔skipped 浮動**——parent 跑 3493/122、QA 鏡跑 3492/123，**總收集數 3615 穩定、0 failed、皆 ≥ floor 3488**） | ✅ |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept / 0 broken | **8 kept / 0 broken** | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | **violations=0**（total=19778 / cap=20438） | ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **OK** | ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | not-chaos 全綠 + arch_fitness exit<2 | **PASS**（exit 0；雙軌 v0.01:1478 + **v0.27:1665** + scripts:129；含 v0.27 router/skill 戳記/FRAMEWORK_STATUS 新鮮度 SSOT lint 全過） | ✅ |
| DAL 等價 | equivalence job | 三後端等價 | **既有 `tests/equivalence/` 隨全套 pytest 通過；本輪零 DAL/repositories/checkpoint 改動**（改動限 spec_source.py + sdd_to_playbook_adapter.py + sdd_compile.py + tests + v0.27 模板） | ✅（N/A 類型②：既有隨全套通過） |
| 五軌 TLC | `bash scripts/ci-gate.sh --full-tlc` | 五軌 0 violation | **N/A 類型①：本輪零碰 `*.tla`/FSM/`_HAPPY_PATH`**（v0.27 對 v0.26 差異僅 docs_template metadata 行 + EVOLUTION/CHANGELOG/FRAMEWORK_STATUS；AutoClaude 改動為 additive 非 FSM；TLC 不在 pytest 全套、需 Java，未跑） | N/A① |

## §6 缺陷處置

- **上輪 open/routed 複驗**：DEF-01-007 / DEF-01-009 / DEF-19-001 / DEF-17-001 / DEF-23-005 / DEF-35-001 / DEF-62-001 皆非本輪 scope，未觸發/未推進，維持原狀態（見 §1.3）。
- 本輪新發現缺陷（若有）階段三/四回填。

## §7 結案契約

```yaml
closure-evidence:
  round: improving_85
  track: A  # 雙向協作橋接（spec-format-version 生產端閃閉），連動 B 柱 Copy-on-Evolve v0.27
  pytest: "3492–3493 passed / 0 failed / 122–123 skipped"   # floor 3488 + 5 新測；PG-DSN 條件測試 passed↔skipped 浮動（總收集 3615 穩定、0 failed）
  lint_imports: "8 kept / 0 broken"
  loc_violations: 0   # total 19778
  snapshot: fresh
  aisdlc_sdd_cigate: PASS  # 雙軌 v0.01:1478 + v0.27:1665 + scripts:129
  producer_round_trip: {templates: 4, parsed_version: "1.0", via: "真實 adapter _SPEC_VERSION_RE"}
  mutations: "MUT-85-1/2 全轉紅 + Edit 還原無殘留"
  new_tests: 5  # 4 adapter（含 monkeypatch surfacing 反空殼）+ 1 CLI exit-5
  production_files_touched: 3   # spec_source.py + sdd_to_playbook_adapter.py + sdd_compile.py（皆 additive）
  framework_copy_on_evolve: v0.27  # 自 v0.26（git archive 862 檔；4 模板宣告 + EVOLUTION/CHANGELOG/FRAMEWORK_STATUS）
  cleanliness_dryrun: "git add -A -n 915 檔，零 build/reports|arch-fitness|chaos-report|__pycache__|.pyc|formal/states（DEF-11-002）"
  framework_version: v0.27  # 自 v0.26（Copy-on-Evolve）
  maturity: L5  # L_合體=min(A=L5,B=L5,C=L5) 不變（橋接契約閉合，不新增自治能力）
  defects:
    - none  # 本輪 dogfooding 未發現新框架缺陷（生產端純 metadata 宣告）
```

## §8 誠實限制
1. **生產端「閃閉」的忠實度邊界**：本輪驗證的是「生產端宣告 → adapter 解析 → SddSpec 表面化 + declared=True 留痕」這條生產↔消費契約端到端走通（以**真實 adapter regex** 對 4 份 v0.27 模板實測解析、加消費端 round-trip 單測）。它**閉合**了 improving_67 防漂移閘對「真實框架 spec」從未被觸發的死碼狀態（過去框架從不戳版本 → 永走靜默預設）。誠實標記：完整的「跨版**不相容**格式漂移實際被擋」需待框架真出現 v2.0 格式 spec 才會在 production 觸發 fail-closed；本輪以單測（宣告 2.0 → CLI 退碼 5 / 宣告 9.9 → SpecFormatVersionError）證該分支行為，未在真實跨版 spec 上端到端跑（現支援集只有 "1.0"，無真實 2.0 框架 spec 存在）。
2. **`spec_format_version` 表面化欄現階段值域**：因 `_SUPPORTED_SPEC_FORMAT_VERSIONS={"1.0"}`，load_spec 成功時該欄恆為 "1.0"（宣告或預設）；此欄為**前瞻結構化攜帶**——當框架未來 bump（如支援 {1.0, 1.1}）時，它會攜帶各 spec 實際使用的版本。為避免「永遠回預設」的空殼測試，`test_surfaced_version_reflects_parsed_value_not_default` 以 monkeypatch 暫擴支援集納 "1.1"、宣告 1.1、斷言表面化為 "1.1"（MUT-85-1 證其非空殼）。
3. **Copy-on-Evolve 潔淨度查證**：依 DEF-11-002 紀律跑 `git add -A -n` 全量 dry-run（915 would-add 檔），grep `build/reports/|arch-fitness.json|chaos-report.json|__pycache__|.pyc|formal/states/|.mutmut|.pytest_cache` **零命中**（git archive 純 tracked 結構性排除 runtime bloat）；非僅憑 .pyc 計數。
4. **規格先行遵循**：§1-§3（含 W 項設計 + `<Architecture_Design_Review>` + RTM）於階段二先落地、才動碼 / Copy-on-Evolve；§4/§5/§7 為階段三/四回填，非事後結案報告。
5. **pytest 數字環境條件浮動（Nightly 紀律 #16）**：parent 親跑 3493/122、QA 鏡親跑 3492/123——同一支 **PG-DSN 條件測試**（`AUTOCLAUDE_DB_DSN`/alembic contract 測試）依執行時 DSN 環境變數狀態在 passed↔skipped 間浮動；**總收集數 3615 穩定、0 failed、passed 皆 ≥ floor 3488**，非退化。pytest-randomly 未啟用、順序由 collection 固定。
6. **B 軌紅線遵循**：v0.26 凍結本體零改（git status 證 v0.27 為新增目錄、未動 v0.0X≤26）；模板修改一律落 v0.27（Copy-on-Evolve）；無 `_HAPPY_PATH`/`*.tla` 變更故五軌 TLC 不觸發；本輪純文件生產端 + AutoClaude additive 消費端，無 🔴 人工確認閘門被自動跳過（Copy-on-Evolve 經掌舵者 AskUserQuestion signoff）。
</content>
</invoke>
