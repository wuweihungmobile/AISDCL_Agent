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
