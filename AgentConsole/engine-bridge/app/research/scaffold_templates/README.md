# 軌道 B 專案範本（ResearchToPRD；ADR-003 D14、D-32）

本目錄下每個**子目錄**是一個登記的範本（名稱只准 `[A-Za-z0-9_-]`、內含至少一個檔案；清單取自目錄掃描，
不是程式常數）。P1 只有 `python-fastapi`；`node`、`java` 不在 P1。

## 展開規則（`app/research/scaffold.py`；確定性、無網路、無子行程、不用 LLM）

- **佔位風格**：`{{變數名}}`（小寫英文與底線）；路徑片段也可用。變數值只准 `[A-Za-z0-9_-]`（不得含
  空白、點、斜線、括號）；未提供的變數、展開後仍殘留 `{{` 或 `}}` 一律失敗。
  可用變數：`project_name`、`slug`、`repo_name`、`owner`。
- **一律 `.tmpl` 後綴**：範本內每個檔案都以 `.tmpl` 結尾，展開時去掉後綴（`app/main.py.tmpl` →
  `app/main.py`）。理由：範本內的 Python 檔若以 `.py` 存放，會被 Bridge `app/` 全樹的 AST 鎖與能力登記
  掃到並要求登記。
- **選用檔**：`.github/workflows/ci.yml`（旗標 `ci`）與 `docker-compose.yml`（旗標 `docker_compose`）；
  旗標為假就不產生。
- **機密**：`.env.example` 只放 `<YOUR_…>` 佔位符；`.gitignore` 排除 `00_research/raw/`、
  `build/reports/`、`.env`（初始 commit 不含研究原檔、內環鍵狀態目錄與機密）。
- 展開後的最小 pytest（`tests/test_smoke.py`）只用標準庫與 pytest，供既有 evaluator 綁定 AT。
