# AutoSDD R112 落地輪前置品質收輪證據檔（mac 側）

- **日期**：2026-08-30
- **建立者**：R112 前置品質收輪（mac 側）文件撰寫包；實測數字來源＝同輪三個並行驗證包
  （root／autoclaude／sdd）的結構化回報與主控當日 `gh run list` 現查。
- **定位**：R112 落地輪（將於 Windows 11 執行）之前的 mac 側品質收輪。本檔＝
  「本機三面閘門 ＋ 雲端 CI 全綠」的**取證快照**——所有數字皆為 2026-08-30 當回合實測，
  讀者的第一動作是**重量，不是採信**。
- **基準點**：HEAD＝`3f0be3b`，工作樹 clean、與 `origin/main` 同步（主控實查）。
- **命名說明**：本檔刻意不取 `CrossPlatform_*`／`Quota_*` 前綴（那兩個前綴＝
  `tools/lib/governance_docs.py` 具名治理文件登記面的命名慣例，取用即須登記）；本檔屬
  單輪取證快照，不承擔帳本指針義務。

---

## 1. 雲端 CI 全綠表（主控 2026-08-30 `gh run list` 現查，各 workflow 最新一次 run）

| Workflow | 結論 | 完成時間（UTC） | 分支 |
|----------|------|----------------|------|
| AutoClaude CI | success | 2026-08-30T01:45:42Z | main |
| aisdlc-sdd-ci | success | 2026-08-28T21:39:59Z | main |
| artifact-cleanup | success | 2026-08-30T09:01:22Z | main |
| drift-daily | success | 2026-08-30T08:28:41Z | main |
| fsm-chaos-nightly | success | 2026-08-30T07:57:22Z | main |
| macos-compat-ci | success | 2026-08-30T06:47:58Z | main |
| root-infra-ci | success | 2026-08-30T06:47:58Z | main |
| shellcheck-ci | success | 2026-08-30T01:45:42Z | main |
| windows-compat-ci | success | 2026-08-30T06:47:58Z | main |

9 支 workflow 逐支 success，無一缺席；對應 HEAD＝`3f0be3b`。

---

## 2. 本機三面閘門逐字結果（皆 mac 側；每格附 rc）

### 2.1 根層（root 驗證包）

**`python tools/run_root_unittests.py`（cwd＝repo 根）→ rc=0**，逐字尾段：

```
Ran 3726 tests in 577.267s

OK (skipped=44)

✅ 整合閘門通過（2 PASS / 1 SKIP）
[skip census] tools/tests@darwin 共 44 支：platform=44／tool-absence=0／env-disabled=0／structural-pair=0／debt=0／untagged=0／欠債型 0 支（目標 0）
[M6 id 集合] tools/tests@darwin：✅ 集合關係成立（本次 skip 44 支）
```

- 驗證包註記：上輪宣稱 3726 OK 本次重量結果一致：Ran 3726 tests, OK (skipped=44)。
- 驗證包註記：測試輸出中間出現的 ❌ 行（actions 版本不一致、NextRunTime 取不到等）皆為
  測試自身紅路徑劇本的 stdout，非失敗；unittest 摘要無任何 FAIL，rc=0。

**`ruff check tools/ .claude/hooks/ --no-cache`（cwd＝repo 根）→ rc=0**，逐字：

```
All checks passed!
```

**`python tools/check_defect_log_crossref.py` → rc=0**，逐字尾段：

```
✅ 缺陷帳本跨文件狀態一致：帳本 165 筆有效狀態紀錄、18 份掃描目標皆無矛盾；……未結存量 61 列（唯一量測入口＝`--unresolved-count`；warn 86／fail 98 列）且皆二擇一（承接輪次／字面「未指派」，存量豁免 0 筆／棘輪上限 0，只准變小）；另 3 筆已結列殘留待辦，見 warning。
外部阻塞軌（AutoSDD_External_Blocked_Log.md，不計入未結列 warn/fail 分母）：8 筆｜DEF-101-518、DEF-101-693、DEF-101-703、DEF-200-063、DEF-200-075、DEF-200-147、DEF-200-174、DEF-200-186
```

### 2.2 AutoClaude 面（autoclaude 驗證包；指令 cwd＝`AutoClaude/`）

**`python -m pytest tests/ -q` → rc=0**，逐字尾段：

```
AUTOCLAUDE-PG-DSN-IN-EFFECT=1 AUTOCLAUDE-NESTED-SESSION=1
[PG autodetect] 已注入 AUTOCLAUDE_DB_DSN／AUTOCLAUDE_TEST_PG_DSN = postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/autoclaude
4739 passed, 62 skipped in 157.54s (0:02:37)
```

> DSN 性質註明：`autoclaude:autoclaude@localhost` 為 `AutoClaude/docker-compose.ci.yml`
> 已公開的 CI 本地假憑證（tmpfs 容器、僅本機迴路），非任何真實環境憑證。
> 全套 pytest 由 conftest 的 PG autodetect 自動注入 DSN，即本格是在 **PG 可用剖面**下跑的。

**`PYTHONUTF8=1 lint-imports` → rc=0**，逐字：

```
Contracts: 9 kept, 0 broken.
```

**PG 面（依 SOP 順序）**：

| 指令 | rc | 逐字尾行 |
|------|----|---------|
| `docker compose -f docker-compose.ci.yml up -d` | 0 | ` Container autoclaude_ci_pg Running` |
| `python -m alembic upgrade head`（帶上述 DSN） | 0 | （無輸出——DB 已在 head；佐證見下一列 alembic current） |
| `python -m alembic current`（帶上述 DSN） | 0 | `0018_version_kind_discriminator (head)` |
| `SD07_REAL_PG_E2E_ENABLED=true … python -m pytest tests/ -m pg_real` | 0 | `================ 3 passed, 2 skipped, 4796 deselected in 3.58s =================` |
| 同上加 `-rs` 取 skip 理由 | 0 | `================ 3 passed, 2 skipped, 4796 deselected in 2.92s =================` |
| `docker compose -f docker-compose.ci.yml down` | 0 | ` Container autoclaude_ci_pg Removed `／` Network autoclaude_autoclaude_ci_net Removed` |

### 2.3 AISDLC_SDD 面（sdd 驗證包）

**`bash scripts/ci-gate.sh`（cwd＝`AISDLC_SDD/`）→ rc=0（`CI_GATE_RC=0`）**，逐字尾段：

```
✅ router hook 覆蓋 lint：最新版 AISDLC_SDD_v0.30 宣告之 CC hook event ['PostToolUse', 'PreToolUse', 'SessionStart'] 全部可達（router ∩ 根 settings）
✅ 本機 CI 閘門全數通過（版本：AISDLC_SDD_v0.01 AISDLC_SDD_v0.30）
   逐軌計數：AISDLC_SDD_v0.01:1478 AISDLC_SDD_v0.30:1747 scripts/tests:348
CI_GATE_RC=0
```

三軌逐字 pytest 摘要行：

```
AISDLC_SDD_v0.01: 1478 passed, 4 skipped, 34 deselected, 14 subtests passed in 12.99s
AISDLC_SDD_v0.30: 1747 passed, 5 skipped, 34 deselected, 14 subtests passed in 22.87s
scripts/tests: 348 passed, 2 skipped, 31 subtests passed in 50.14s
```

arch_fitness `--strict` 逐字判決（兩軌皆同）：

```
加權缺陷分數（越低越健康）：**3**　｜ 🔴 fail=0　🟡 warn=3
```

（arch_fitness advisory warn——不阻擋；warn 內容見 §3.6。）

---

## 3. 不塗綠劃界（skip／deselect／warning 逐項；「量到零」與「未量測」分開寫）

**量到零的**：三面閘門 FAIL＝0、lint-imports broken＝0、arch_fitness fail＝0、
crossref 矛盾＝0——皆為當回合真跑後量到的零。以下各項則是**未量測或制度性登記**，
不得混入「全綠」敘事。

### 3.1 根層 44 skip

skip census 逐字分類：`platform=44／tool-absence=0／env-disabled=0／structural-pair=0／debt=0／untagged=0／欠債型 0 支（目標 0）`。
全數為 platform 標籤（`[WINDOWS-NATIVE-ONLY]` 等）——darwin 上此為預期行為，非覆蓋損失；
M6 id 集合關係成立。

### 3.2 AutoClaude 62 skip（含 53 支 WINDOWS-NATIVE-ONLY）

62 skipped 中 53 支為 WINDOWS-NATIVE-ONLY，pytest 摘要逐字標頭：
「53 個 Windows 專屬測試本次『未在原生 Windows 環境驗證』（非一般 skip，見 DEF-101-348/R44）」
——本輪在 macOS 執行，此為**制度性登記面**（未量測，非量到零）；其餘 skip 依既有標籤制度登記。

### 3.3 pg_real 2 skip

- skip #1（`AutoClaude/tests/integration/test_pgvector_real_recall.py:264`）：`[DEBT]`
  雙 adapter failover fixture 缺失（DUAL_ADAPTER_FAILOVER_RIG；本機無 BGE-M3 權重／
  真實 staging／Minimax 憑證，理由文字自述「量不到即不得轉綠」）——已登記欠債，
  本機**結構上無法驗**（未量測）。
- skip #2（`AutoClaude/tests/perf/test_pgvector_recall_perf.py:71`）：`[ENV-DISABLED]`
  pgvector recall 延遲 SLA 刻意 opt-in（需 `PG_REAL_ENABLED=1`；對機器負載敏感、
  預設開會 flaky）——本輪任務書未要求，**未執行**（未量測）。

### 3.4 SDD 面 skip／deselect／未跑軌

- v0.01 軌 4 skipped：`tools/fsm_runtime/tests/test_meta_halt.py:321`、`test_phase_m.py:502`、
  `test_phase_n.py:300`、`test_tla_python_sync.py:290`——皆為 set `SDD_RUN_TLC=1` to run
  full TLC，離線可達性不變量已常駐守門。
- v0.30 軌 5 skipped：同上四支 TLC（`[ENV-DISABLED]`）＋
  `tools/fsm_runtime/tests/test_file_lock.py:129`（`[WINDOWS-NATIVE-ONLY]` 真 handle
  佔用語意只在 Windows 成立，mac 上結構性不可跑）。
- scripts/tests 2 skipped：`test_install_post_commit_windowsapps_guard.py:510`、`:525`
  （`[WINDOWS-NATIVE-ONLY]` 依賴 Windows PATHEXT／App Execution Alias 解析語意）。
- chaos 測試面：兩軌各 34 deselected（`-m "not chaos"` 為 PR 閘門設計，chaos 屬
  nightly，非本閘門範圍——未在本輪量測）。
- `--full-tlc` **未跑**（任務書指定不帶；stage [3/3] 逐字：
  `==> [3/3] 跳過完整 TLC（offline reachability 已隨 pytest 驗證）；--full-tlc 可啟用`）。

### 3.5 crossref 1 則 warning（rc 仍 0，非失敗）

已結列殘留待辦 3 筆——`:83` DEF-101-338（closed-by-decision）＝下一輪、
`:93` DEF-101-559（closed-by-decision）＝未指派、`:228` DEF-200-228（fixed）＝下輪。
此 3 筆屬結案輪收斂面的既有殘留（載體＝`docs/06_quality/AutoSDD_Defect_Log.md` 各該列），
本輪只登記不處置。

### 3.6 arch_fitness 3 個 advisory warn（既有項，非本輪引入）

FF-5：CLAUDE.md §9 約 5.6 頁 > 1.2 頁目標；FF-16 GAP-X1：元迴圈 3 生成器模組零引用
具身評估器工具鏈；FF-16 GAP-X2：鷹架代謝 GC 從未產出退役 ROI 提案——兩軌
（v0.01/v0.30）內容相同，皆 warn 非 FAIL、不阻擋。

---

## 4. 下輪（R112，Windows 11）開工已知地雷與待辦（皆引用既有載體，本檔不新立列）

1. **Phase 2 觀察時效**：`_PHASE2_REVIEW_LOG` 末列＝(106, [維持觀察])、視窗 5、判準
   `live > due`；live_round（重釘表最大輪號）現＝111 恰好貼線仍綠，**一旦因 R112 重釘
   推進即撞 `[時效逾期]` 紅**。出口＝往 `_PHASE2_REVIEW_LOG` 追加一列 §6 決議
   （`[提案]`／`[維持觀察]`（連續第 2 次會撞 `[連續空轉]`）／`[退場]`），屬四方／掌舵者
   裁決面。載體＝`docs/04_planning/R111_HANDOFF.md` §一（條文＝ADR-XPLAT-012 條文五 §6）；
   現查 `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`。
2. **PG 容器已 down**：`autoclaude_ci_pg` 於本輪驗證完成後已依任務書 `docker compose down`
   移除（§2.2 末列）；PG 為 tmpfs，**Windows 側要跑 PG 面須重新
   `docker compose -f docker-compose.ci.yml up -d` ＋ `python -m alembic upgrade head`**
   （容器 healthy ≠ DB 已 migrate，憑證＝`local_ci_gate.pg_autodetect()` 回出 DSN）。
   另註：本輪 down 之前該容器已 Up 34 hours；若曾有其他並行 session 依賴此長駐容器，
   已被本次 down 中斷。
3. **53 支 WINDOWS-NATIVE-ONLY 測試將在 Windows 側首次真驗**（§3.2 的制度性登記面在
   Windows 上轉為實測面；根層 44 支 platform skip 同理部分轉實測）。
4. **R111_HANDOFF §三 的未接線項照舊**：129 自列出口尚未接線、212① 閘門尚未接線、
   217-E2／E5 與 191 仍未處置、S102（ruff S 系列）尚未納入 select、帳本七列狀態欄整格
   替換的原文指針尚未補存——逐項載體與現查指令見 `docs/04_planning/R111_HANDOFF.md` §三，
   本檔不複寫、不改其承接。

---

## 5. 本檔取數劃界

- 本機三面數字全數逐字轉錄自三個驗證包的結構化回報（rc 與 verbatim 尾段原樣，未重組）；
  雲端 CI 表轉錄自主控同日 `gh run list` 現查。本檔撰寫包**自身未重跑**三面閘門
  （落檔後僅預跑 crossref／handoff-carriers／根層 unittest 三道受影響判準，結果由
  收輪回報附上，不寫進本檔以免自我引用）。
- 指令原文中的本機工作目錄一律改寫為 repo 相對描述（repo 已 Public，本檔不落任何
  本機絕對路徑／帳號／機器名）。
