"""結果帳本：每次 run 追加一列到 docs/06_quality/RealVerify_Result_Ledger.md。"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from .sandbox import REPO

LEDGER = REPO / "docs" / "06_quality" / "RealVerify_Result_Ledger.md"
HEADER = """# RealVerify 結果帳本

每次 `python tools/realverify.py run …` 追加一列（程式寫入，勿手改既有列）。
證據座標＝`<sid 前 8 碼>:<逐字稿行號>`；沙盒逐字稿於案例結束後即刪，座標用於當下對照。
rc 0＝全過、1＝有失敗、2＝環境缺件（不算綠）。

| 時間（UTC） | 選取 | 結果 | n | 失敗案例 | 證據座標／備註 | 秒數 |
|---|---|---|---|---|---|---|
"""


def _cell(s: str) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def append_row(selection: str, verdict: str, n: int, failed: list[str], evidence: list[str], seconds: float,  # noqa: E501
               path: Path | None = None) -> str:
    p = path or LEDGER
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.is_file():
        p.write_text(HEADER, encoding="utf-8", newline="\n")
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    row = (f"| {ts} | {_cell(selection)} | {verdict} | {n} | {_cell(','.join(failed) or '-')} | "
           f"{_cell('; '.join(evidence) or '-')} | {seconds:.0f} |\n")
    with p.open("a", encoding="utf-8", newline="\n") as f:
        f.write(row)
    return row
