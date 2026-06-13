"""跨平台 TLC 執行器 — 對 formal/SDD_FSM.tla 跑 TLC 完整窮舉驗證.

取代僅 pwsh 可用的 formal/run_tlc.ps1（在 Windows PowerShell 5.1 會 parse 失敗）。
純 Python + subprocess，任何有 `java` 與 `tla2tools.jar` 的環境皆可跑（Windows PS 5.1 /
PowerShell Core / Linux / macOS / CI）。與 formal/run_tlc.sh 等價。

搭配 `tests/test_tla_python_sync.py` 的離線可達性不變量（reachable=N/N，零 Java 依賴、
每次 pytest 強制）：本地常駐守門用 BFS；完整時序+計數器窮舉用本執行器（有 java 時）。

用法：
    python -m tools.fsm_runtime.tlc_runner            # 跑驗證（jar 需已在 formal/lib/）
    python -m tools.fsm_runtime.tlc_runner --download  # 缺 jar 時先下載
    python -m tools.fsm_runtime.tlc_runner --depth 50
退出碼：0 通過 / 1 invariant|liveness|deadlock 違反 / 2 環境錯誤（無 java/jar）
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

FORMAL_DIR = Path(__file__).resolve().parent / "formal"
LIB_DIR = FORMAL_DIR / "lib"
TLA_FILE = "SDD_FSM.tla"
CFG_FILE = "SDD_FSM.cfg"
DEFAULT_TLA_VERSION = "v1.8.0"


def find_java() -> str | None:
    return shutil.which("java")


def jar_path() -> Path:
    return LIB_DIR / "tla2tools.jar"


def download_jar(version: str = DEFAULT_TLA_VERSION) -> Path:
    LIB_DIR.mkdir(parents=True, exist_ok=True)
    url = (f"https://github.com/tlaplus/tlaplus/releases/download/"
           f"{version}/tla2tools.jar")
    dst = jar_path()
    print(f"[tlc_runner] 下載 {url} ...")
    urllib.request.urlretrieve(url, dst)
    print(f"[tlc_runner] 下載完成：{dst.stat().st_size / 1_048_576:.2f} MB")
    return dst


def run_tlc(depth: int = 50, *, jar: Path | None = None,
            tla: str = TLA_FILE, cfg: str = CFG_FILE) -> dict:
    """跑 TLC，回傳 {ok, exit, distinct, generated, depth, log_tail}。

    Phase L / ACT-090：新增 `tla`/`cfg` 參數，支援對 META_FSM.tla（自我改進元迴圈
    形式化）等獨立命名空間模組跑同一執行器（預設仍為單軌 SDD_FSM，向後相容）。
    """
    java = find_java()
    if java is None:
        return {"ok": False, "exit": 2, "error": "java not found"}
    jar = jar or jar_path()
    if not jar.exists():
        return {"ok": False, "exit": 2, "error": f"jar missing: {jar}"}
    cmd = [
        java, "-XX:+UseParallelGC", "-cp", str(jar), "tlc2.TLC",
        "-config", cfg, "-workers", "auto", "-depth", str(depth), tla,
    ]
    proc = subprocess.run(cmd, cwd=str(FORMAL_DIR), capture_output=True, text=True)
    out = proc.stdout + "\n" + proc.stderr

    def _grp(pat: str) -> int:
        m = re.search(pat, out)
        return int(m.group(1)) if m else 0

    no_error = "No error has been found" in out
    ok = proc.returncode == 0 and no_error
    return {
        "ok": ok,
        "exit": proc.returncode,
        "no_error": no_error,
        "distinct": _grp(r"(\d+)\s+distinct\s+states\s+found"),
        "generated": _grp(r"(\d+)\s+states\s+generated"),
        "depth": _grp(r"depth of the complete state graph search is\s+(\d+)"),
        "log_tail": "\n".join(out.splitlines()[-20:]),
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="跨平台 TLC 執行器（SDD_FSM / META_FSM 窮舉驗證）")
    ap.add_argument("--depth", type=int, default=50)
    ap.add_argument("--download", action="store_true", help="缺 jar 時先下載 tla2tools.jar")
    ap.add_argument("--module", default="SDD_FSM",
                    help="要驗證的模組（SDD_FSM | META_FSM | FLEET_FSM | COMPOSITION_FSM | OPTIMIZATION_FSM；預設 SDD_FSM）")
    args = ap.parse_args(argv[1:])
    tla = f"{args.module}.tla"
    cfg = f"{args.module}.cfg"

    if find_java() is None:
        print("ERROR: java 不存在，請安裝 JDK 11+。", file=sys.stderr)
        return 2
    if not jar_path().exists():
        if args.download:
            download_jar()
        else:
            print(f"ERROR: 缺 {jar_path()}；加 --download 或先放置 jar。", file=sys.stderr)
            return 2

    res = run_tlc(depth=args.depth, tla=tla, cfg=cfg)
    print(f"TLC_MODULE={args.module}")
    print(f"TLC_DISTINCT={res.get('distinct')}")
    print(f"TLC_GENERATED={res.get('generated')}")
    print(f"TLC_DEPTH={res.get('depth')}")
    if res["ok"]:
        print("[tlc_runner] OK — TLC 驗證通過（No error found）")
        return 0
    print("[tlc_runner] FAIL — TLC 驗證失敗：")
    print(res.get("log_tail", res.get("error", "")))
    return res.get("exit", 1) or 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
