"""假 SelfImproving CLI 樹：暫存目錄內放一支只用標準庫的替身腳本（TCS-SelfImprovingMirror-P1b
§5.2）。

用途：Bridge 的 `si_cli`／`/si/*` 測試以它真起子行程，斷言 argv、cwd、環境集合、逾時殺樹、輸出
上限與各種失敗形態，不依賴真 CLI（真 CLI 的差分在 test_si_export_differential.py）。

每次呼叫把 argv、cwd、直譯器、`sys.flags.safe_path`、pid、stdin 是否立即 EOF 與**全部環境變數的
名稱與值**追加到 `<R>/fake_calls.jsonl`（測試用 `read_calls` 取回）；`<R>/fake_control.json`
（測試用 `set_control` 寫）決定它怎麼表現：
  rc          離開碼（預設 0）
  stderr      要寫到 stderr 的文字（原樣、不加換行）
  sleep       先睡這麼多秒
  raw_stdout  原樣輸出的字串（優先於 export、dry_run）
  huge        持續寫出無換行資料，並把累計位元組數逐行追加進 `<R>/fake_written.txt`
  grandchild  先啟動一個睡 30 秒的孫行程，把兩個 pid 寫進 `<R>/fake_pids.json`
  export      要輸出的物件（預設：對請求 kind 合法的最小 export 物件）
  schema_rev／kind／items  覆寫預設物件的對應鍵（`schema_rev` 給 null＝不輸出該鍵）
  by_id       `--id` 值 → 該次輸出的 `items`（沒列到的 id 輸出空 `items`）
  dry_run     `obs-add --dry-run` 要輸出的物件（預設最小合法物件；P2b）。argv 含 `--body-file` 時
              整份 stdin 以位元組讀完並以 base64 記進呼叫紀錄的 `stdin_b64`（其餘呼叫該欄為空字串）

議題中心（TCS-IssueCenter-20261027）：旗標解析另認 `--status=<值>`、`--source=<值>`（單一 argv
元素，值取 `=` 之後的全部）；`--kind issues` 且無 `--id` 的預設物件另帶罐頭的 `legend`、`summary`
（單筆沒有這兩個鍵，與真 CLI 同形；內容只是占位，不是真輸出）。

這支檔本身不是測試（檔名不以 test_ 開頭）；它被測試 import 來造樹與讀紀錄。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_FAKE_CLI = r'''
"""fake SelfImproving CLI（測試替身）。"""
import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CALLS = ROOT / "fake_calls.jsonl"
CONTROL = ROOT / "fake_control.json"
DEFAULT_DRY_RUN = {"ok": True, "row": "| fake dry-run row |", "row_bytes": 20,
                   "row_max_bytes": 700, "findings": []}

args = sys.argv[1:]
flags = {}
for i, tok in enumerate(args):
    if tok in ("--kind", "--since", "--limit", "--id") and i + 1 < len(args):
        flags[tok] = args[i + 1]
    elif tok.startswith(("--status=", "--source=")):
        name, _, value = tok.partition("=")
        flags[name] = value
kind = flags.get("--kind", "")
is_dry_run = "--dry-run" in args

stdin_b64 = ""
try:
    if "--body-file" in args:
        stdin_b64 = base64.b64encode(sys.stdin.buffer.read()).decode("ascii")
        stdin_eof = True
    else:
        stdin_eof = sys.stdin.read(1) == ""
except (OSError, ValueError):
    stdin_eof = True

with CALLS.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps({
        "args": args, "script": str(Path(sys.argv[0]).resolve()), "cwd": os.getcwd(),
        "executable": sys.executable, "safe_path": bool(sys.flags.safe_path), "pid": os.getpid(),
        "stdin_eof": stdin_eof, "stdin_b64": stdin_b64, "env": dict(os.environ)},
        ensure_ascii=False) + "\n")

control = json.loads(CONTROL.read_text(encoding="utf-8")) if CONTROL.is_file() else {}

if control.get("grandchild"):
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    (ROOT / "fake_pids.json").write_text(
        json.dumps({"child": os.getpid(), "grandchild": child.pid}), encoding="utf-8")
if control.get("sleep"):
    time.sleep(float(control["sleep"]))
if control.get("stderr"):
    sys.stderr.write(control["stderr"])
    sys.stderr.flush()
if control.get("huge"):
    written = 0
    block = b"x" * 65536
    while True:
        sys.stdout.buffer.write(block)
        sys.stdout.buffer.flush()
        written += len(block)
        with (ROOT / "fake_written.txt").open("a", encoding="utf-8") as mark:
            mark.write(str(written) + "\n")
if "raw_stdout" in control:
    sys.stdout.buffer.write(control["raw_stdout"].encode("utf-8"))
    sys.stdout.buffer.flush()
    sys.exit(int(control.get("rc", 0)))
if is_dry_run:
    if "dry_run" in control or int(control.get("rc", 0)) in (0, 1):
        obj = control["dry_run"] if "dry_run" in control else DEFAULT_DRY_RUN
        sys.stdout.buffer.write((json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))
        sys.stdout.buffer.flush()
    sys.exit(int(control.get("rc", 0)))
if "export" in control:
    obj = control["export"]
else:
    items = control.get("by_id", {}).get(flags.get("--id"), []) if "--id" in flags \
        else control.get("items", [])
    obj = {"schema_rev": control.get("schema_rev", 1), "kind": control.get("kind", kind),
           "generated_at": "2026-10-21T00:00:00+08:00", "head_sha": None, "items": items,
           "next_since": None, "truncated": False, "ne": [], "problems": []}
    if kind == "issues" and "--id" not in flags:
        obj["legend"] = {"statuses": [], "unmapped_label": "未歸類"}
        obj["summary"] = {"total": len(items), "unmapped": 0}
    if obj["schema_rev"] is None:
        del obj["schema_rev"]
if control.get("rc", 0) == 0 or "export" in control:
    sys.stdout.buffer.write((json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))
    sys.stdout.buffer.flush()
sys.exit(int(control.get("rc", 0)))
'''


#: 固定的快照時間（TCS-SiFlowVisibility §5.1 的 NOW；`generated_at` 為其前 3 分鐘）。
PATROL_NOW = "2026-11-11T14:00:00+08:00"
PATROL_GENERATED_AT = "2026-11-11T13:57:00+08:00"


def patrol_report(**over: Any) -> dict[str, Any]:
    """`PR(over)`：C-1 的 `report` 基準夾具（Bridge／backend 層＝snake_case；逐鍵覆寫）。測試號一律
    `PROP-SI-901` 起（不存在於真帳本）。鍵序刻意讓 `generated_at` 在 `schema_rev` 之後。"""
    base: dict[str, Any] = {
        "schema_rev": 1, "generated_at": PATROL_GENERATED_AT, "off": False,
        "heartbeat_minutes": 15, "ledger_seq": 130, "truncated": False,
        "steps": [{"step": name, "result": "完成"}
                  for name in ("巡視", "入帳", "到期", "運轉", "推進")],
        "schedule": {"enabled": True,
                     "current": {"code": "SCHED-CELL-RAN", "text": "本期已經跑過一次，等下一期"},
                     "last_skip": None},
        "ingest": [],
        "props": [{"id": "PROP-SI-901", "state": "verified", "code": "WAIT-PROMOTE-DECISION",
                   "who": "掌舵者", "text": "驗證通過，等你決定是否晉升"}],
        "runs": {"live": [], "waiting": [], "queued": []},
        "push": {"enabled": True, "state": "idle", "code": "PUSH-NOT-AHEAD",
                 "text": "沒有待推送的提交", "retry": None, "sha": None, "ahead": 0,
                 "attempts": 0, "finished_at": None, "tick_at": None},
    }
    base.update(over)
    return base


def detail_full(**over: Any) -> dict[str, Any]:
    """`DETAIL(over)`：C-3 的 `detail` 基準夾具（根層以 camelCase 輸出；八欄俱全，含 `heldout` 八鍵
    與 `sandbox.failText`）。`patch.text` 含 `\\r\\n`、Tab、U+2028、emoji、中文與一行字面
    `+++ b/x`，結尾無換行。"""
    patch_text = ("diff --git a/x b/x\r\n--- a/x\r\n+++ b/x\r\n@@ -1,2 +1,2 @@\r\n"
                  "-舊行\t含 Tab\r\n+新行 \U0001F600 與 U+2028   之後\r\n+++ b/x")
    base: dict[str, Any] = {
        "patch": {"rel": "docs/06_quality/SelfImproving_Proposals/PROP-SI-901/r2.patch",
                  "bytes": len(patch_text.encode("utf-8")), "text": patch_text, "truncated": False},
        "body": {"rel": "docs/06_quality/SelfImproving_Proposals/PROP-SI-901/r2.md",
                 "bytes": 28, "text": "# 提案 901\n\n症狀…\n", "truncated": False},
        "sourceObs": [{"id": "OBS-SI-001", "context": "巡邏日誌", "symptom": "提案卡了三天沒人處理",
                       "severity": "P2", "disposition": "proposed"}],
        "heldout": {"frozen": True, "seq": 60, "n": 7, "min": 5, "belowMin": False,
                    "frozenBy": "凍結者甲", "digest8": "0a1b2c3d", "neNote": None},
        "sandbox": {"seq": 61, "id": "APP-SI-901", "applied": True, "touchedOk": True,
                    "rollbackOk": True, "failCode": None, "failText": "（無失敗）"},
        "verify": {"seq": 62, "id": "APP-SI-901", "verdict": "PASS", "baselineRed": True,
                   "patchedGreen": True, "mutatedRed": True, "probesN": 6, "carrierProof": True,
                   "reasons": [{"code": "VERIFY-OK", "text": "三步證據齊全，驗證通過"}]},
        "next": {"code": "WAIT-PROMOTE-DECISION", "who": "掌舵者",
                 "text": "驗證通過，等你決定是否晉升"},
        "timeline": [{"seq": 12, "t": "2026-11-10T09:00:00+08:00", "by": "巡邏器",
                      "kind": "prop", "action": "提出提案"}],
    }
    base.update(over)
    return base


#: `proposal_item` 的 `detail` 預設值哨兵（None 是合法的 detail 值：null）。
DEFAULT_DETAIL: Any = object()


def proposal_item(detail: Any = DEFAULT_DETAIL, *, with_detail: bool = True,
                  **over: Any) -> dict[str, Any]:
    """單筆提案 `items[0]`：既有的卡面鍵加 `detail`（`with_detail=False`＝舊根層，沒有該鍵）。"""
    item: dict[str, Any] = {"id": "PROP-SI-901", "state": "verified", "rev": 2, "lastSeq": 120,
                            "sources": ["OBS-SI-001"], "card": None}
    if with_detail:
        item["detail"] = detail_full() if detail is DEFAULT_DETAIL else detail
    item.update(over)
    return item


def make_fake_si(tmp_path: Path) -> Path:
    """在 `tmp_path` 造假 CLI 樹（`<R>/tools/selfimproving.py`），回傳樹根 `R`。"""
    root = tmp_path / "fake-si"
    cli_dir = root / "tools"
    cli_dir.mkdir(parents=True, exist_ok=True)
    (cli_dir / "selfimproving.py").write_text(_FAKE_CLI, encoding="utf-8", newline="\n")
    return root


def read_calls(root: Path) -> list[dict[str, Any]]:
    path = root / "fake_calls.jsonl"
    if not path.is_file():
        return []
    # 只以 "\n" 切行：`str.splitlines()` 也會在 U+0085、U+2028 等字元處斷行，而紀錄裡的 argv 可能
    # 帶有這類字元（議題中心的篩選值測試，TCS-IssueCenter-20261027 AT-IC-07-2-1）。
    return [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line]


def set_control(root: Path, **control: Any) -> None:
    """換一組旋鈕（整份取代；不帶參數＝恢復預設表現）。"""
    (root / "fake_control.json").write_text(json.dumps(control), encoding="utf-8")
