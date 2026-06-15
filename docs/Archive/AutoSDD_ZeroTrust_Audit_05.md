# AutoSDD_ZeroTrust_Audit_05 — 第 5 輪審計與複審證據

> **輪次**：05｜**日期**：2026-06-14｜**對象**：DEF-02-001 跨版 pytest 同跑 fail-loud guard（W1）
> **絕對前提**：零退化（floor = AutoClaude 3069 passed，本輪實測錨定）。
> **方法**：階段一 Explore agent 重偵察 + 主 agent 沙箱實證 + 收尾獨立審計 agent（Architect/SA-SD/QA 三鏡）親跑複核。所有數字以**實測**為準，非引用文件。

---

## 1. 階段一 Zero-Trust 重偵察（實測基線）

| 項目 | 實測 | 判定 |
|------|------|------|
| AutoClaude 全套 | **3069 passed / 122 skipped / 0 failed**（99.58s→100.46s 兩次一致） | ✅ = 上輪 floor，硬閘通過 |
| lint-imports | **8 kept / 0 broken** | ✅ |
| check_loc_budget | violations=0（17511 ≤ cap 20438） | ✅ |
| snapshot_sync --check | 新鮮 | ✅ |
| AISDLC_SDD ci-gate（雙軌） | exit 0（v0.01: 1478 passed / v0.04: 1494 passed） | ✅ DEF-03-001 修復屬實 |
| DEF-03-001 構件 | `ci-gate.sh` 雙軌 + `test_ci_gate_version_resolution.py` 4 case | ✅ 上輪交付屬實 |

**open 缺陷複驗**：DEF-01-007（cc-switch 仍未裝，續 open）；DEF-01-009（224 非空行<250，已自癒→watch）；DEF-02-001（仍重現，本輪修）。

**硬閘**：0 failed 且 3069 = floor → 通過。

---

## 2. DEF-02-001 根因實證（主 agent 沙箱，非臆測）

| 證據 | 內容 |
|------|------|
| R1 碰撞重現 | `cd AISDLC_SDD && pytest v0.03/.../tests v0.04/.../tests` → `ImportPathMismatchError: ('tools.fsm_runtime.tests.conftest', '...v0.03...', '...v0.04...')` |
| R2 根因 | `__init__.py` 鏈（tools/→fsm_runtime/→tests/）使各版 conftest/test dotted name 完全相同 + prepend → sys.modules 同名衝突 |
| R3 importlib 排除 | `import_mode=importlib` dotted name 仍同名→不解；`consider_namespace_packages` 反打斷生產 import |
| **R4 更深真相（決定性）** | 即便最新版改 iso（移除 `__init__.py`+importlib），跨版同跑仍壞——各版**生產套件 `tools.fsm_runtime.*` 同名**，單一 process sys.modules 只能裝一版 → A 版測試實際載到 B 版生產模組（沙箱情境3 `assert 'vA'=='vB'` 失敗）。**∴ 單一 process 跨版同跑結構性不可支援；唯一隔離＝每版獨立 process（官方 gate `cd vX` 本就正確）** |

**修法定調**：非徒勞「讓跨版能跑」，而是 Rule 12 Fail-Loud + 鎖定隔離不變量。落**共享 infra**（`AISDLC_SDD/conftest.py` + `scripts/`，versioned 目錄外），**免 v0.05 Copy-on-Evolve**（同 DEF-03-001 精神）。

---

## 3. W1 交付與雙重驗證（階段三）

**交付構件**（git diff 證實，無任一 v0.0X 源碼變更）：
- `AISDLC_SDD/scripts/cross_version_guard.py` — 純函式 `versions_touched`/`build_guard_message`（read-only，無副作用）。
- `AISDLC_SDD/conftest.py` — 薄包裝，`pytest_configure` 偵測觸及 >1 版 → `raise pytest.UsageError`。
- `AISDLC_SDD/scripts/tests/test_cross_version_guard.py` — 8 case（7 純函式測意圖 + 1 subprocess 整合）。

**hook 選擇實證（DEF-05-001）**：原 `pytest_load_initial_conftests` 有 chicken-and-egg（rootdir conftest 在該 hook default 實作內才載入、自身實作不被回呼，真 repo 不 fire）→ 改 `pytest_configure`（configure 時必已註冊，碰撞在其後 collection → configure 先 raise）即正確。

**覆蓋矩陣（誠實標示殘留）**：

| 情境 | 呼叫 | guard | 實測 |
|------|------|-------|------|
| T1 | `cd vX && pytest`（官方 gate） | 不干擾 | ci-gate 雙軌 exit 0；`cd v0.04 && pytest test_md_python_sync.py` 5 passed |
| T3 | 從根單版顯式路徑 | 不 fire | `--co` 正常收集 |
| **T4** | 從根 bare `pytest`（**最常見 footgun**） | **fail-loud** | exit=4 + 訊息含 DEF-02-001 |
| T2（殘留） | 從根顯式 `pytest vX/ vY/` | 攔不到 | version `pytest.ini` 捕獲 confcutdir、根 conftest 不載入；**文件化已知限制**（原生錯誤已具名兩版可診斷） |

---

## 4. 階段四 — 零退化驗證矩陣（全項實測）

| 檢查 | 命令 | 結果 | 判定 |
|------|------|------|------|
| AutoClaude 全套 | `pytest tests/ -q` | **3069 passed / 122 skipped / 0 failed**（100.46s） | ✅ = floor |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | ✅ |
| LOC 分級 | `check_loc_budget.py` | violations=0 | ✅ |
| Snapshot | `snapshot_sync.py --check` | 新鮮 | ✅ |
| AISDLC_SDD 雙軌閘門 | `bash scripts/ci-gate.sh` | exit 0（v0.01+v0.04） | ✅ 證 guard 對 `cd vX` 零干擾 |
| guard 回歸測試 | `pytest scripts/tests/test_cross_version_guard.py` | 8 passed | ✅ |
| 五軌 TLC | 不觸發（無 `_HAPPY_PATH`/`.tla` 改動） | N/A | — |

---

## 5. 多專家 Zero-Trust 複審（獨立審計 agent 親跑，2026-06-14）

獨立 Explore 審計 agent（Architect/SA-SD/QA 三鏡）裁決摘要：

| 鏡 | 項目 | 裁決 |
|----|------|------|
| Architect | conftest 用 `pytest_configure`；helper 純函式無副作用；無任一 v0.0X 源碼變更（git status 佐證） | ✅ PASS |
| QA（親跑） | guard 回歸 8 passed；bare 誤用 fire（exit=4+DEF-02-001）；單版不誤觸；`cd v0.04` 官方 gate 5 passed 零干擾 | ✅ PASS |
| QA（零退化） | lint 8 kept / LOC 0 / snapshot 新鮮 / 雙軌 exit 0 | ✅ PASS |
| SA-SD（文件誠實） | §2.5 誠實標 T2 殘留（不虛報全覆蓋）；DEF-02-001→fixed@improving_05 附證；DEF-05-001 誠實入帳；AutoClaude 零改 git diff 佐證 | ✅ PASS |

**獨立裁決**：✅ 可結案 — 無基線退化／無契約 broken／無凍結本體被改／無帳本不誠實／無文件虛報。

---

## 6. 結案判定

✅ **第 5 輪（DEF-02-001 fail-loud guard）通過全 PASS，可結案。**

- 零退化：AutoClaude 3069 持平 / 0 failed；lint 8 kept；LOC 0；snapshot 新鮮。
- AISDLC_SDD 雙軌閘門 exit 0（guard 對官方 `cd vX` 零干擾）。
- guard 真實有效（bare footgun exit 4 + 可行動訊息），殘留誠實標示。
- 凍結本體零改、AutoClaude 零改（git diff 佐證）；本修復免 Copy-on-Evolve。
- 帳本誠實：DEF-02-001 fixed（含更深根因 R4）、DEF-05-001 行進中即記。

**git 變更全貌**（本輪實體 diff）：
```
 M docs/06_quality/AutoSDD_Defect_Log.md
?? AISDLC_SDD/conftest.py
?? AISDLC_SDD/scripts/cross_version_guard.py
?? AISDLC_SDD/scripts/tests/test_cross_version_guard.py
?? docs/04_planning/AutoSDD_improving_05.md
?? docs/06_quality/AutoSDD_ZeroTrust_Audit_05.md
```
（ci-gate 運行副作用產物 build/reports + arch-fitness.json 已 `git checkout` 還原，保持 diff surgical。）
