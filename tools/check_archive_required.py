#!/usr/bin/env python3
"""缺陷帳本容量逼近輪替上限時，commit 期**阻斷式**強制觸發歸檔（掌舵者裁決，見交接）。

## 立案

`check_defect_log_crossref.py` 早就有 WARN／FAIL 兩道 bytes 門檻（`_LEDGER_WARN_BYTES`／
`_LEDGER_FAIL_BYTES`），`archive_defect_log.py` 也早有成熟的 `--plan`／`--apply`／`--check`
三模式。缺的是兩者之間的**接線**：主檔落在 WARN 帶時，現況只印一行 `⚠️` warning（且只有
`pre-push` 會跑到那一行，`pre-commit` 完全不碰這支檔），從未強制任何人真的去跑
`--apply`。「帳本歸檔」因此始終停在「等人手動想起來才做」，而人力記憶不是機械守門。

## 判準（本檔只做一件事：AND 兩個既有事實）

```
WARN 門檻 <= 主檔 bytes < FAIL 門檻   且   archive_defect_log.plan() 的 movable 非空
```

🔴 **為何是這個區間、不含兩端**（若合併判斷更合理可調整——本檔判斷不需要調整，理由如下）：
  - **不含尚未到 WARN 的安全區**（bytes < WARN）：離輪替上限還遠時擋下 commit 沒有任何
    急迫性，只會製造無謂摩擦——這正是本檔要避免復刻的「守衛擋到讓人關掉它」路數。
  - **不含已達 FAIL 的區間**（bytes >= FAIL）：那一段是`check_defect_log_crossref.main()`
    既有的**硬性**輪替上限（DEF-99-001，256KB＝Read 工具單次讀取上限，見該檔常數上方
    R68 WHY）——已經是「不可如常操作，必須先處理」的另一個量級，訊息也不同（不是「請先
    考慮歸檔」而是「已經超過 Read 工具能一次讀完的上限」）。把兩段合併成同一句訊息會讓
    讀者分不清「還有選擇餘地」與「已經沒有選擇餘地」，且該硬線目前掛在 `pre-push`
    （`check_defect_log_crossref.py` 本身），不是本檔的職責範圍——本檔不重覆、不弱化
    那道既有硬線，只補它前面「WARN 帶且有東西可搬」這一段commit 期原本零訊號的空隙。
  - **`movable` 必須非空才觸發**：光是「bytes 逼近上限」不足以構成「請去跑 --apply」的
    可執行指令——如果此刻一筆都搬不動（例如全部未結案，或全部帶交接字樣需要人工
    `--ack-handoff`），擋下 commit 只會逼使用者對著一個他當下解不開的閘門乾瞪眼，
    那正是「守衛擋到讓人失去信任」的來源。`movable` 非空才代表「這是一個**現在就可以
    執行**的動作」，訊息才配得上「請先跑 --apply」這句話。

## 為何另開一支檔（不是塞進 `check_defect_log_crossref.py` 或 `archive_defect_log.py`）

兩支既有檔皆已卡在 `AutoClaude/tools/check_loc_budget.py::SPECIAL_FILES` 的逐檔行數棘輪
（現查 `python AutoClaude/tools/check_loc_budget.py --json`）——落地當回合實測
`archive_defect_log.py` 餘裕**恰為 0**、`check_defect_log_crossref.py` 餘裕僅 5 行，
塞一個帶完整 docstring 的新判準進去，不靠「搬等量史料抵銷」（本輪範圍不含此重構）
不可能不撞棘輪。另開一支檔案落在 `guardrail_cli` tier（budget 遠高於本檔實際行數），
且與 `check_handoff_carriers.py` 同樣的既有先例——`import check_defect_log_crossref as
gate` 這條依賴方向本來就有多支既有檔在用，不是新模式。**不會造成循環引用**：
`check_defect_log_crossref.py` 從不 import 本檔或 `archive_defect_log.py`，依賴方向
單向（本檔 → 兩支既有檔），與 `archive_defect_log.py` 已經在用的
`import check_defect_log_crossref as gate` 同型、互不相依。

## 為何直接呼叫 `archive_defect_log.plan()` 而不是解析 `--plan` 的文字輸出

`plan()` 回傳結構化 `dict`（`movable`／`needs_ack`／`blocked`／`ledger_bytes` 等鍵），
是 `--plan` CLI 輸出的**資料來源**，不是反過來。解析 CLI 文字輸出屬於脆弱做法（欄位
順序、中文標點、bytes 單位字樣任一改動都會讓 regex 解析悄悄漏抓），而 `plan()` 本身
就是可直接 import 呼叫的 Python function，兩者是同一份程式碼、沒有「多一層轉譯」的
必要。

使用：
  python3 tools/check_archive_required.py   # 未觸發 rc=0；觸發（見上方判準）rc=1
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _cli_flags  # noqa: E402
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌) 防崩潰保護
import archive_defect_log as _archiver  # noqa: E402
import check_defect_log_crossref as _gate  # noqa: E402

#: 本工具零旗標——見 `tools/_cli_flags.py` 檔頭〈接線紀律〉，`cli()`/`main()` 分層。
_KNOWN_ARGV: tuple[str, ...] = ()


def archive_required_problems() -> list[str]:
    """帳本主檔落在 WARN~FAIL 帶**且**現在有非空可搬清單時，回傳非空問題清單。

    空清單＝安全區（bytes < WARN）、已達 FAIL 硬線（另案處理，見模組 docstring）、
    或此刻無可搬項（例如全部未結案／全部需要 `--ack-handoff` 人工承認）三種情況之一。

    刻意先判 bytes 門檻、成立才呼叫 `_archiver.plan()`：`plan()` 會讀四份 crossref
    掃描目標 ＋ 帳本家族 ＋ 全部具名治理文件，屬於相對昂貴的操作；bytes 遠低於 WARN
    的常態（本檔落地當下實測主檔 152042 bytes，WARN 線 245760）下第一行 `.stat()`
    就短路，本判準因此在 commit 的常態路徑上幾乎零成本。
    """
    if not _gate._DEFECT_LOG.exists():
        return []
    ledger_bytes = _gate._DEFECT_LOG.stat().st_size
    if not (_gate._LEDGER_WARN_BYTES <= ledger_bytes < _gate._LEDGER_FAIL_BYTES):
        return []
    movable = _archiver.plan()["movable"]
    if not movable:
        return []
    total = sum(v["bytes"] for v in movable)
    return [
        f"缺陷帳本主檔 {ledger_bytes} bytes 已逼近輪替上限 {_gate._LEDGER_FAIL_BYTES}"
        f"（DEF-99-001 政策），且現有 {len(movable)} 筆／{total} bytes 可搬遷"
        "（archive_defect_log.py 的 --plan 判準①②③⑤⑥全過，非交接待人工承認、"
        "亦非指針反向依賴阻擋）—— commit 前請先跑 "
        "`python3 tools/archive_defect_log.py --apply --archive-num <N>` "
        "完成歸檔騰出容量，再重試本次 commit"
        "（可先跑 `python3 tools/archive_defect_log.py --plan` 確認可搬清單與下一個"
        "archive 編號）"
    ]


def cli(argv: list[str]) -> int:
    """旗標分派。**刻意不寫進 `main()`**：理由與 `check_handoff_carriers.py::cli()`
    同型——`main()` 一碰 `sys.argv` 就會被程式化呼叫端（unittest／子行程探針）的
    引數污染，見 `tools/_cli_flags.py` 檔頭〈接線紀律〉。
    """
    rc = _cli_flags.reject_unknown_argv("check_archive_required.py", argv, _KNOWN_ARGV)
    if rc is not None:
        return rc
    return main()


def main() -> int:
    problems = archive_required_problems()
    if problems:
        print(f"❌ 帳本歸檔強制觸發（{len(problems)} 筆）：", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print("✅ 未觸發歸檔強制門檻（bytes 未進入 WARN~FAIL 帶，或此刻無可搬清單）")
    return 0


if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]))
