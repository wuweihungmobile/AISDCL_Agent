# 跨平台啟動提示詞（macOS / Windows）

給 Claude Code 使用的完整提示詞，於**新開 session 的第一則訊息**直接複製貼上對應平台版本即可。核心依據：[tools/dev_start.py](tools/dev_start.py) 跨平台自動偵測啟動程序。

兩份提示詞的差異只在啟動指令、venv 路徑格式（`/` vs `\`、`bin/python` vs `Scripts\python.exe`）與平台健檢項目說明，核心紀律（不硬做、不自動 push/stash、先讀子專案 CLAUDE.md、繁體中文回覆）完全一致。

---

## 🍎 macOS 版

```
我現在在 macOS 上要開始開發/使用這個 monorepo（AISDCL_Agent，含 AutoClaude 與 AISDLC_SDD 兩個子專案）。請依序完成以下準備工作：

1. 一律先做一次 GitHub 同步（不要先判斷 tools/dev_start.sh 是否存在再決定要不要同步——本機可能落後 origin/main、或雖然檔案存在但版本過舊，兩種情況都該先同步再說）：
   git fetch origin
   git merge --ff-only origin/main
   若 --ff-only 失敗（本地領先或分叉），把 git status 和 git log main..origin/main 的結果列給我看，不要自動 rebase 或 reset --hard；先讓我看過再決定。同步完成後才繼續下一步（此時 tools/dev_start.sh 必定存在且是最新版）。

2. 用 Bash 工具在 repo 根目錄執行：
   source tools/dev_start.sh
   這是本專案的跨平台自動偵測啟動程序，會自動依序完成七件事：
   [1/7] 偵測目前環境（Developing vs Now）是否跨平台切換
   [2/7] GitHub 同步（fetch + fast-forward pull；髒工作樹/分叉/離線只會明示提醒，不會自動 stash/rebase/push）
   [3/7] 跨平台切換時清除失效快取
   [4/7] 整備/修復 .venv（含跨平台換手保留、依賴 hash 比對、必要時自動跑 bootstrap）
   [5/7] 檢查並修復 git hooks（core.hooksPath）
   [6/7] 平台健檢（Windows 專屬項目在 mac 上會跳過）
   [7/7] 狀態寫回

3. 檢查輸出的「dev_start 摘要」：
   - 若結尾是 ❌，先幫我排除錯誤，不要跳過或忽略，也不要自己嘗試用 --force-bootstrap 以外的手段硬做。
   - 若只有 ⚠️ 警告（尤其是「工作樹不乾淨」「與 origin 分叉」「領先 origin 未 push」這類），簡短列給我看，讓我自己決定要不要處理，不要自動 commit/stash/push 幫我決定。

4. 由於 shell 狀態不一定會在你之後每次呼叫工具時持續生效，之後所有 Python 相關指令（pytest、ruff、pip 等）請直接使用 `.venv/bin/python`（或先確認 `which python` 真的指向這個路徑）執行，不要誤用系統 Python。

5. 確認你已讀過根目錄 CLAUDE.md（monorepo 導覽），並在動手前先讀清楚本次工作屬於哪個子專案（AutoClaude 或 AISDLC_SDD），進去該子專案前務必先讀它自己的 CLAUDE.md ——兩份子 CLAUDE.md 都是 override 級規範，其目錄/命名/測試規則以子專案內部路徑為準，不要套用錯誤的相對路徑假設。

6. 回覆一律使用繁體中文。

完成以上準備後，跟我簡短回報目前環境狀態（是否首次執行、是否偵測到從 Windows 切換過來、.venv 是否有重建、hooks 是否正常、有沒有需要我處理的警告），然後等我下達實際的開發任務，不要自己先開始做事。
```

---

## 🪟 Windows 版

```
我現在在 Windows 上要開始開發/使用這個 monorepo（AISDCL_Agent，含 AutoClaude 與 AISDLC_SDD 兩個子專案）。請依序完成以下準備工作：

1. 一律先做一次 GitHub 同步（不要先判斷 tools/dev_start.ps1 是否存在再決定要不要同步——本機可能落後 origin/main、或雖然檔案存在但版本過舊，兩種情況都該先同步再說）。在 PowerShell 執行：
   git fetch origin
   git merge --ff-only origin/main
   若 --ff-only 失敗（本地領先或分叉），把 git status 和 git log main..origin/main 的結果列給我看，不要自動 rebase 或 reset --hard；先讓我看過再決定。同步完成後才繼續下一步（此時 tools/dev_start.ps1 必定存在且是最新版）。

2. 在 repo 根目錄的 PowerShell 環境中執行（dot-source，前面的點與空格不可省略）：
   . .\tools\dev_start.ps1
   若你目前執行指令的環境不是 PowerShell（例如透過 Git Bash 或 WSL），請改用：
   powershell -ExecutionPolicy Bypass -Command ". .\tools\dev_start.ps1"
   並注意：這種方式啟用的 .venv 只在該 PowerShell 子行程內生效，之後的指令請直接指定完整路徑 `.venv\Scripts\python.exe`，不要假設 `python` 這個指令已經指向正確的直譯器。

   這是本專案的跨平台自動偵測啟動程序，會自動依序完成七件事：
   [1/7] 偵測目前環境（Developing vs Now）是否跨平台切換（例如上次在 mac 開發、這次換到 Windows）
   [2/7] GitHub 同步（fetch + fast-forward pull；髒工作樹/分叉/離線只會明示提醒，不會自動 stash/rebase/push）
   [3/7] 跨平台切換時清除失效快取
   [4/7] 整備/修復 .venv（含跨平台換手保留、依賴 hash 比對、必要時自動跑 bootstrap）
   [5/7] 檢查並修復 git hooks（core.hooksPath）
   [6/7] 平台健檢（自動設定 core.longpaths=true，避免 MAX_PATH=260 限制炸掉深路徑）
   [7/7] 狀態寫回

3. 檢查輸出的「dev_start 摘要」：
   - 若結尾是 ❌，先幫我排除錯誤，不要跳過或忽略，也不要自己嘗試用 --force-bootstrap 以外的手段硬做。
   - 若只有 ⚠️ 警告（尤其是「工作樹不乾淨」「與 origin 分叉」「領先 origin 未 push」這類），簡短列給我看，讓我自己決定要不要處理，不要自動 commit/stash/push 幫我決定。
   - 若警告是「偵測不到 Git Bash（bash.exe）」：這在標準 Git for Windows 安裝下很常見（安裝程式預設只把 `Git\cmd` 加進 PATH，`Git\bin\bash.exe` 本來就不在 PATH，是官方建議設定，不代表沒裝 Git Bash）。先用 `git --version` 確認有裝 Git for Windows 就好，不必為此改 PATH；只有之後真的 commit/push 卡住才需要進一步處理。

4. 之後所有 Python 相關指令（pytest、ruff、pip 等）請直接使用 `.venv\Scripts\python.exe`，不要誤用系統 Python。

5. 確認你已讀過根目錄 CLAUDE.md（monorepo 導覽），並在動手前先讀清楚本次工作屬於哪個子專案（AutoClaude 或 AISDLC_SDD），進去該子專案前務必先讀它自己的 CLAUDE.md ——兩份子 CLAUDE.md 都是 override 級規範，其目錄/命名/測試規則以子專案內部路徑為準，不要套用錯誤的相對路徑假設。

6. 回覆一律使用繁體中文。

完成以上準備後，跟我簡短回報目前環境狀態（是否首次執行、是否偵測到從 mac 切換過來、.venv 是否有重建、hooks 是否正常、有沒有需要我處理的警告），然後等我下達實際的開發任務，不要自己先開始做事。
```

---

## 可選旗標

需要時可以在對應提示詞的第 2 步（dev_start 呼叫指令）後面追加，或另外請 Claude Code 加上：

- `--no-sync`：跳過 GitHub 同步（離線工作時使用）
- `--force-bootstrap`：強制重跑 bootstrap 重新整備依賴（懷疑 .venv 不完整時使用）
