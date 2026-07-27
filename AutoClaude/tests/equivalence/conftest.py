"""equivalence 測試共用 fixture。

R56（跨平台複審）：原本掛在本檔的 `_interpreter_dir_on_path` autouse fixture 已上移至
`tests/conftest.py`（頂層），作用域改為涵蓋整個 `tests/`。理由：同一根因（macOS 與多數
現代 Linux distro 的乾淨 PATH 上只有 `python3`、無裸 `python`）並非 equivalence 專屬，
實測至少 6 個目錄的測試在「未 activate venv 直接以 `<repo>/.venv/bin/python -m pytest`
呼叫」時會踩到；且保留兩份實作必然漂移（本 repo 反覆處理的 DEF-101-238 同款類別），
故本檔不再保留副本，請一律改動頂層那一份。
"""
from __future__ import annotations
