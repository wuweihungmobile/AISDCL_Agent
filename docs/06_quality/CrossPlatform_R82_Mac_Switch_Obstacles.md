# CrossPlatform R82 — macOS 側切換障礙實錄（DEF-101-999 的唯一居所）

**建檔情境**：2026-08-10，R82 成果（Windows 側完成、`7975140`）第一次在 macOS 真機上照 [useMacWin.md](../../useMacWin.md) 的〈🔁 平台切換 SOP〉走完一次啟動。五處障礙**全部當場實測**，非推想。

**資格（為何登記為具名治理文件）**：本檔逐項寫出「某障礙的證據落在某檔某行／某實測輸出」的座標宣稱（⇒ 指針稽核），而 `DEF-101-999` 列已依 `ROW_MAX_BYTES=700` 瘦身成索引 ⇒ **唯一**還能重驗那五項判讀是否為真的地方就是本檔（⇒ 體積守門）。

> 🔴 本檔**不寫任何 pytest／ci-gate 基線數字**。全 repo 基線數字的唯一站點是 `ONBOARDING.md` §7（`tools/check_pytest_baseline_sites.py` 機械守門）。

---

## (a) 主 `.venv` 必然已被 pg extras 汙染，而提示詞第 7 點沒說

- **實測**：`.venv/bin/python -c "import importlib.util as u; ..."` → `psycopg2 PRESENT` / `sqlalchemy PRESENT`。
- **後果**：`tools/sync_onboarding_baselines.py --write --with-slow` 依設計 rc=2 拒跑（`sync_onboarding_baselines.py:1404`）。
- **文件缺口**：提示詞第 7 點原文只寫「必須在**不含 postgres/pgvector 選配的出廠環境 venv** 上跑」。讀者的預設理解是「本機 `.venv` 就是出廠環境」——實際上它幾乎必然不是，所以這一步**必然**要另建臨時乾淨 venv。原文把一個「必然要做的額外動作」寫成了「一個要滿足的條件」。
- **同形態復發**：同一件事已於 2026-08-01（8 天前）記入 memory `project_onboarding_baseline_needs_clean_venv`。memory 攔得住「同一個 session 的我」，攔不住「照文件做的下一個人」——**這是把它推進文件的理由**。
- **已修落點**：useMacWin.md mac／Windows 兩版第 7 點各補一句「那個 venv 不是本機 `.venv`」＋指向 B 段第 3 點的探針與建法。

## (b) B 段給的乾淨 venv 建法在本機不可執行（`uv` 不存在）

- **實測**：`command -v uv` 空；`.venv/bin/uv`、`~/.local/bin/uv`、`~/.cargo/bin/uv` 皆不存在。`uv` 只活在使用者 shell profile 裡，工具呼叫的非互動 shell 看不到它。
- **文件缺口**：B 段原文的建法是「全新臨時目錄 + `python3.11 -m venv` + `uv pip install -e '.[dev,notifications]'`」，且緊接著寫「**不要另編一套**」——於是照做的人卡在 `command not found`，而文件同時禁止他換做法。
- **正解本來就存在**：`python3.11 -m venv` 建的 venv **自帶 pip**，`python -m pip install -e '.[dev,notifications]'` 正是 `ONBOARDING.md` §7 的 R55／R56 校正註記走過的同一條路 ⇒ 用它**不算**另編一套。本次即以此建成乾淨 venv，探針兩行皆 `ABSENT` 後才回填。
- **已修落點**：B 段第 3 點前置① 補「`uv` 不一定在」與 pip 回退，並明說它不算另編一套。

## (c) zsh 載具兩個陷阱 —— 本輪實際產出過一次假紅

Claude Code 的 Bash 工具在 macOS 走 **zsh**（`Shell: zsh`），兩平台的 `.ps1`／CI／git hooks 都不受影響 ⇒ **只有在 mac 上用工具跑指令時才會踩到**，這也是它一直沒被記錄的原因。

1. **`${PIPESTATUS[0]}` 印空**：zsh 的陣列叫 `pipestatus` 且下標從 1 起（`$pipestatus[1]`）。本輪第一次跑 `run_root_unittests.py | tail` 時 rc 靜默消失，差一步就把紅讀成綠。
2. **未加引號的變數不做分詞**（zsh 預設無 `SH_WORD_SPLIT`）：`for g in "x.py --check"; do $PY $g; done` 把整串當**單一檔名**交給 python。`python` 對「開不了檔」的 rc **恰好也是 2**，與守門自己判紅在 rc 上無法區分 ⇒ 本輪三支帶子指令參數的根層守門（`archive_defect_log.py --check`、`sync_onboarding_baselines.py --check-snapshot`、`_script_scan_surface.py --list …`）全被誤報為紅，改 `bash -c '…'` 重驗全部 rc=0。

- **為何危險**：`pre-push` 本身是 bash，寫法正確；於是「hook 裡對、我在 mac 上手動重現時錯」，錯的那一邊看起來才像真相。
- **已修落點**：C 段雷區表 +2 條（症狀／根因／正確寫法三欄齊備），並各自標 DEF-101-999(c)。

## (d) nightly FAIL 判讀是二分法，涵蓋不了本輪實遇形態

- **現行 SOP**：比對失敗 stage 起訖時間與 `git reflog` 最近一次 merge/pull ——時間重疊＝假紅，否則真迴歸。
- **實遇**：nightly 這輪 11:00:35 起跑、11:06 收尾（`AutoClaude/logs/nightly_mac_20260810_110035.log`）；merge 落在 11:09:50（`git reflog --date=iso`）⇒ **不重疊，非假紅**。但那輪的失敗（2 支 skip 的理由講 Windows 語意卻沒帶 `[WINDOWS-NATIVE-ONLY]` 標籤）在 merge 後**已不復現**（重跑 skip census `untagged=0`），取而代之的是 10 支**全新**失敗。
- **結構根因**：**nightly 跑的是 merge 前的 code，它的紅綠對 merge 後的 HEAD 沒有推論力**。SOP 沒有這句，於是二分法的兩個答案都會誤導：答「假紅」→ 漏看新紅；答「真迴歸」→ 去追一個已經被 merge 修掉的舊紅。
- **已修落點**：mac／Windows 兩版第 3 步各補第三態，並明寫「不論時間有無重疊，都必須在**當前 HEAD** 上重跑一次」。

## (e) B 段步驟順序錯：回填排在全套閘門之前

- **機械事實**：回填寫的是 `ONBOARDING.md`＝**根層檔**；`tools/git-hooks/pre-push` 的慢層（`py_compile` ＋ `run_root_unittests.py`）**只在 push 範圍含根層檔時才跑**（`pre-push:33-51` 逐行 case 判定、`:326-345` 慢層本體）。純 `AutoClaude/`／`AISDLC_SDD/` 的 push 不觸發它。
- **實遇**：照 B 段原順序先回填、後跑閘門，才發現 `run_root_unittests.py` 在當前 HEAD 上 10 支紅 ⇒ 回填成果 `commit` 過得去（pre-commit 不跑這層）卻 **push 不出去**，被自己的紅鎖在本機。
- **附帶缺口（同段）**：回填前**未列 docker 前置**。本次 docker daemon 未啟動 ⇒ provenance 如實記 `docker=down`，而 Windows 欄是 `up`。ci-gate 逐軌計數對 docker 敏感（幅度見 `ONBOARDING.md` §7），兩欄從此**不同條件、依 §7 既定紀律不可相減**，只能等下次在該平台重量才恢復可比。
- **已修落點**：B 段開頭加順序鐵律＋原第 2/3 點互換（閘門先、回填後）；前置② 補 docker。

---

## Next Action —— 三支待補的機械鎖（本輪未落地，誠實劃界）

上述五項**全部只有散文守著、零機械物**。文件會被下一個人跳讀，所以以下三鎖是真正的治本解：

| # | 鎖 | 守哪一項 | 落點建議 |
|---|----|---------|---------|
| ① | `sync_onboarding_baselines.py` 的 rc=2 拒跑訊息**直接印出本機可執行的乾淨 venv 建法**（含 `uv` 缺席時的 pip 回退） | (a)(b) | 該檔 `pg_state == "present"` 分支；訊息內容以 `shutil.which("uv")` 實查結果分岔 |
| ② | `--write` 前置檢 docker 狀態，並在「本機平台欄與另一平台欄的 `docker` 值不一致」時 warn | (e) 附帶缺口 | 同檔 provenance 組裝處已量 `docker`，只差把兩欄比一次 |
| ③ | 機械斷言 useMacWin.md B 段「回填步驟號 > 全套閘門步驟號」 | (e) | `tools/tests/` 內比照既有文件結構鎖（如 `test_doc_loc_baseline_freshness_r60.py`）的寫法 |

(c) 的 zsh 面**無法**用 repo 內測試守（陷阱在 Claude Code 的工具載具，不在 repo 程式碼裡）⇒ 它的唯一防線就是 C 段雷區表那兩列，這是本輪刻意接受的殘餘。

**另一項獨立待辦（不屬本檔射程，僅記指路）**：`run_root_unittests.py` 在 `7975140` 上的 10 支紅是 R82 成果首次在 mac 真機曝出的跨平台缺口，尚未修；它同時是 (e) 的觸發源。
