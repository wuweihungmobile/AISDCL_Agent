# ADR-XPLAT-010 — 根層與子專案的邊界：跨子專案 import 隔離 ＋ 根層 ruff 政策

- **狀態**：Accepted（R68～R69 落地時已由當輪修復包實作並通過四方複審；本 ADR 為 R99 補寫的決策紀錄，追認既有決策、非新提案）
- **日期**：2026-08-21（ADR 補寫日；跨子專案 import 邊界機制落地於 R69，根層 ruff 政策落地於 R68-38／R69 P3）
- **平台**：平台中立（純 repo 結構／CI 相依政策，不涉作業系統差異）
- **回應帳本**：帳本記載此缺口見 `docs/06_quality/AutoSDD_Defect_Log.md` 對應列（R69 終審 Architect 發現：兩項決策只活在測試 docstring 與 toml 註解裡，下一個人改鎖時無從判斷是否在推翻一個決定）
- **改動面**：本 ADR 純新增文件，不改動任何程式碼或設定；下列兩項機制**已於各自落地輪次實作完成**，本文件只是把散落的理由收斂成一份可追的決策紀錄

---

## 1. 問題

本 repo 是雙專案 monorepo（`AutoClaude/` × `AISDLC_SDD/`）＋ 根層整合層。兩項會長期存續的架構決策，此前**只活在程式碼旁的散文裡**，沒有獨立的決策文件：

1. **跨子專案 import 邊界**：`autoclaude/` 不得 import 根層 `tools/lib/`（反之亦然，`AISDLC_SDD/` 不得 import `autoclaude.*`）——只寫在 `AISDLC_SDD/scripts/tests/test_cross_subproject_import_isolation.py` 的 docstring。
2. **根層 ruff 政策**：`tools/ruff.toml` 的 per-file-ignores 取捨、為何不帶 `--config` 執行——只寫在該 toml 檔頭註解與 `tools/tests/test_subprocess_encoding_hygiene.py::TestRootToolsLintPolicy` 的判定說明裡。

決策活在測試/設定檔的旁白裡，後果是**下一個人只看得到「有一道鎖」，看不到「為什麼是這條線」**：改鎖時無從判斷自己是在修一個 bug，還是在推翻一個經過權衡的決定。

## 2. 裁決

**維持現行兩項機制不變，把決策理由收斂進本 ADR，並在此登記為追認式決策（Accepted，非新設計）。**

### 2.1 跨子專案 import 邊界

**裁決**：`AutoClaude/` 與 `AISDLC_SDD/` 之間**禁止直接 import 對方的生產套件**（`autoclaude.*` ↮ `AISDLC_SDD` 版本目錄下的 `tools.fsm_runtime`／`tools.arch_fitness`／`AISDLC_SDD/scripts/*.py` 共用模組）。

**理由**（R68 兩起真實事故，非前瞻假設；🔴 事故當時的檔名見帳本原始記載，本節僅描述事件本身，不重述可能已因後續重構而失效的舊檔名——`AISDLC_SDD/scripts/tests/test_ntfs_length_gate.py` 為當時第一起事故仍存在的載體，第二起事故的原始測試檔已因 R45 元件淨化共用化重構而不復以原檔名存在，此處故意不引其舊路徑）：
- `AISDLC_SDD/scripts/tests/test_ntfs_length_gate.py` 曾硬 import `autoclaude.utils.logger`，連帶拉進 `pydantic`；而 `aisdlc-sdd-ci` 的 CI 相依只鎖 `AISDLC_SDD_v0.01/requirements-ci.txt`（`pyyaml` + `pytest`，不含 `pydantic`）⇒ 本機全綠、CI 由綠轉紅（`ModuleNotFoundError: No module named 'pydantic'`，run 30720156045）。
- LATEST 版本目錄下另一支測試同樣跨樹硬 import `autoclaude.*`，但外面包了 `try/except ImportError` + `@unittest.skipIf`——不會紅，而是 8 支測試在 CI 上**永遠 skip**，比紅更難察覺。

兩起事故的共同根因不是「忘了裝套件」，而是**跨子專案 import 這個動作本身**讓「本機能跑」與「CI 能跑」永久脫鉤，且脫鉤是靜默的。故裁決是**禁止該動作本身**，不管相依裝了沒。

**跨子專案一致性需求由誰承接**：需要兩樹行為一致（如檔名淨化邏輯）時，一致性斷言搬到 monorepo 根層整合層 `tools/tests/test_windows_forbidden_filename_parity.py`——它本就是「四處獨立實作漂移即知」的載體，且根層 root-infra-ci 依 `tools/run_root_unittests.py::_THIRD_PARTY_PREREQS` 安裝第三方相依，在該層 import AutoClaude 生產套件合法且真的會跑。

**機械執行者**：`AISDLC_SDD/scripts/tests/test_cross_subproject_import_isolation.py`（AST 掃描 `Import`/`ImportFrom` 節點，非 grep——subprocess 跨樹呼叫腳本的**正確**隔離手法會被字串常數誤判為違規，AST 天然排除字串與註解）。

### 2.2 根層 ruff 政策

**裁決**：根層護欄層（`tools/` 與 `tools/tests/`）用獨立的 `tools/ruff.toml`，規則集**逐字對齊** `AutoClaude/pyproject.toml` 的 `[tool.ruff]`（`select = ["E", "F", "I", "UP", "W"]`、`line-length = 100`、`target-version = "py311"`），但**兩邊各自維護一份設定檔**、CI 與 pre-push 執行時**刻意不帶 `--config`**。

**理由**：
1. **本 repo 此前全 monorepo 只有一份 ruff 設定**（`AutoClaude/pyproject.toml`）。ruff 是「由每個檔往上找最近的設定檔」，根層 `tools/` 上方一路到 repo 根都沒有任何 ruff 設定，於是它套用 ruff **出廠預設**（`E4,E7,E9,F`、line-length 88，預設 select 不含 `E501`）——`ruff check tools/` 印出的 `All checks passed!` 是**假綠**：換上本 repo 自己宣告的規則集當場 199 筆（R68-38 實測）。這與 `DEF-99-001`／`DEF-101-123` 同型：政策有宣告、卻沒有任何機械物在根層執行它。
2. **規則集逐字對齊、不自創第二套標準**：根層護欄層與 `AutoClaude/` 的 `tools/` 是同一批人、同一種程式碼，兩處各走各的門檻只會製造「同一個人在兩棵樹裡被兩套規則管」的漂移。
3. **刻意不放在 repo 根**：放根層 `pyproject.toml`／`ruff.toml` 會讓 `AISDLC_SDD/`（今日零 ruff 設定、零 ruff 閘門）一夜之間被納管並產生大批既有債紅燈——那是另一個授權面的決定，超出本裁決射程。
4. **刻意不帶 `--config`**：帶 `--config` 時 ruff 的 project root 變成 cwd，`[lint.per-file-ignores]` 的相對 pattern 與 isort src 判定全部錯位（同機實測：帶 `--config` 140 errors、不帶 0 errors）。

**機械執行者**：CI `root-infra-ci.yml` 第 16 道 `ruff check tools/`；本地 `tools/git-hooks/pre-push` root-infra 快層第 ④ 段；對齊性由 `tools/tests/test_subprocess_encoding_hygiene.py::TestRootToolsLintPolicy` 鎖住（規則集逐字相等、`.loc_baseline`-style 存量債棘輪只准縮小、豁免到期日機械核對）。

## 3. 誠實劃界

- **本 ADR 不新增任何機械鎖**，兩項機制本身已各自有完整的測試覆蓋（見上方「機械執行者」段）；本 ADR 純粹是**追認式決策紀錄**，把散落在 docstring／toml 註解裡的理由收斂成一份可被回指的文件。
- **雙向可追已達成**（DEF-101-748 收斂）：`AISDLC_SDD/scripts/tests/test_cross_subproject_import_isolation.py` 的 docstring 與 `tools/ruff.toml` 的檔頭註解已各自補上一行回指本 ADR 編號（`ADR-XPLAT-010` §2.1／§2.2），兩邊雙向可追。當回合實跑：`pytest AISDLC_SDD/scripts/tests/test_cross_subproject_import_isolation.py -q` → `24 passed`；`python -m unittest tools.tests.test_subprocess_encoding_hygiene.TestRootToolsLintPolicy` → `Ran 6 tests OK`。
- **是否需要合併成單一「根層與子專案邊界」ADR 或保留分節**：本 ADR 選擇**合併為一份**（帳本原文列出「兩項各補一份 ADR（或合併為一份）」為可接受的二擇一），因兩者本質上是同一類決策（根層 vs 子專案的治理邊界）在不同載體上的體現，分成兩份 ADR 反而會讓讀者需要交叉比對才能看到「這是同一條邊界原則」。
