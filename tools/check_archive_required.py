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

import fnmatch
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _cli_flags  # noqa: E402
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌) 防崩潰保護
import archive_defect_log as _archiver  # noqa: E402
import check_defect_log_crossref as _gate  # noqa: E402

#: 本工具零旗標——見 `tools/_cli_flags.py` 檔頭〈接線紀律〉，`cli()`/`main()` 分層。
_KNOWN_ARGV: tuple[str, ...] = ()


def _staged_paths() -> list[str] | None:
    """本次 commit 暫存區的檔名清單（git 慣用正斜線相對路徑）；取不到回 `None`。

    DEF-200-222 判準①：commit 期阻斷過去對**每一次** commit 都跑（含與帳本無關者），
    誤傷面過大。取得暫存清單是縮小阻斷面的前提——取不到（`git` 不存在、非 git 目錄、
    子行程失敗）一律回 `None`，呼叫端必須把它當「不明」而**維持既有阻斷判準**（fail-loud
    的其中一種形態：寧可多擋、不可靜默縮小阻斷面，見 `archive_required_problems()`）。
    """
    try:
        proc = subprocess.run(
            ["git", "-c", "core.quotepath=false", "diff", "--cached",
             "--name-only", "--no-renames"],
            cwd=_gate._REPO_ROOT, capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return [ln for ln in proc.stdout.splitlines() if ln]


def _touches_ledger_family(staged: list[str]) -> bool:
    """`staged` 內是否有任一檔屬於帳本家族（主檔／archive_NN／歸檔索引）。

    判準刻意只比對**檔名**、不比對所在目錄：家族成員名稱本身已具高度特徵性
    （`AutoSDD_Defect_Log*.md`），比對目錄會在既有測試沙箱慣例（`mock.patch.object(
    m, "_DEFECT_LOG", <repo 外的 tmp 路徑>)`）下對 `_REPO_ROOT` 做 `relative_to()`
    直接拋例外，反而製造新的脆弱點——本函式不重蹈。

    SSOT：主檔名、歸檔索引名、archive glob 樣式一律取自既有模組物件（`_gate`／
    `_archiver`），不得在此另寫一份判斷準則。
    """
    names = {Path(p).name for p in staged}
    if _gate._DEFECT_LOG.name in names:
        return True
    if _archiver._ledger_index.ARCHIVE_INDEX_NAME in names:
        return True
    return any(fnmatch.fnmatch(n, _archiver._ARCHIVE_GLOB) for n in names)


def archive_required_problems() -> list[str]:
    """帳本主檔落在 WARN~FAIL 帶**且**現在有非空可搬清單**且**本次 commit 有碰帳本家族時，
    回傳非空問題清單。

    空清單＝安全區（bytes < WARN）、已達 FAIL 硬線（另案處理，見模組 docstring）、
    此刻無可搬項（例如全部未結案／全部需要 `--ack-handoff` 人工承認），或（DEF-200-222
    判準①）本次 commit 的暫存清單**確定**未觸碰帳本家族（主檔／archive_NN／歸檔索引）
    四種情況之一。

    刻意先判 bytes 門檻、成立才呼叫 `_archiver.plan()`：`plan()` 會讀四份 crossref
    掃描目標 ＋ 帳本家族 ＋ 全部具名治理文件，屬於相對昂貴的操作；bytes 遠低於 WARN
    的常態（本檔落地當下實測主檔 152042 bytes，WARN 線 245760）下第一行 `.stat()`
    就短路，本判準因此在 commit 的常態路徑上幾乎零成本。

    🔴 DEF-200-222 判準①（縮小阻斷面）：過去每一次 commit（含與帳本無關者）都導向
    同一條 `--apply` 指令，誤傷面過大。取得暫存清單失敗（`_staged_paths()` 回 `None`）
    時**不**當成「未觸碰」放行——那是 fail-open，會讓縮小阻斷面的立意反過來變成新的
    漏洞。改為**維持既有阻斷判準**（bytes+movable 兩項照舊決定要不要擋）並在訊息內
    附一句 fail-loud 說明，讓「為什麼沒縮小」是看得見的，不是靜默的。
    """
    if not _gate._DEFECT_LOG.exists():
        return []
    ledger_bytes = _gate._DEFECT_LOG.stat().st_size
    if not (_gate._LEDGER_WARN_BYTES <= ledger_bytes < _gate._LEDGER_FAIL_BYTES):
        return []
    movable = _archiver.plan()["movable"]
    if not movable:
        return []
    staged = _staged_paths()
    narrowing_note = ""
    if staged is not None:
        if not _touches_ledger_family(staged):
            return []
    else:
        narrowing_note = (
            "⚠️ DEF-200-222：無法取得本次 commit 的暫存檔清單（git diff --cached "
            "失敗），無法判斷本次是否觸碰帳本家族 → 維持既有阻斷判準（不縮小阻斷面）。"
        )
    total = sum(v["bytes"] for v in movable)
    msg = (
        f"缺陷帳本主檔 {ledger_bytes} bytes 已逼近輪替上限 {_gate._LEDGER_FAIL_BYTES}"
        f"（DEF-99-001 政策），且現有 {len(movable)} 筆／{total} bytes 可搬遷"
        "（archive_defect_log.py 的 --plan 判準①②③⑤⑥全過，非交接待人工承認、"
        "亦非指針反向依賴阻擋）—— commit 前請先跑 "
        "`python3 tools/archive_apply_locked.py --archive-num <N>`"
        "（DEF-200-222 判準②：序列化保護版的 --apply 入口，多 agent 共用工作樹時"
        "請一律走此入口、不要直接呼叫 archive_defect_log.py --apply） "
        "完成歸檔騰出容量，再重試本次 commit"
        "（可先跑 `python3 tools/archive_defect_log.py --plan` 確認可搬清單與下一個"
        "archive 編號）"
    )
    if narrowing_note:
        msg = f"{msg}\n    {narrowing_note}"
    return [msg]


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
