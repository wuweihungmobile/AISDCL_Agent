"""跨平台 TLC 執行器 — 對 formal/SDD_FSM.tla 跑 TLC 完整窮舉驗證.

取代僅 pwsh 可用的 formal/run_tlc.ps1（在 Windows PowerShell 5.1 會 parse 失敗）。
純 Python + subprocess，任何有 `java` 與 `tla2tools.jar` 的環境皆可跑（Windows PS 5.1 /
PowerShell Core / Linux / macOS / CI）。R65（ADR-XPLAT-002 §5 Phase 2-A）起，
formal/run_tlc.sh／run_tlc.ps1 已改寫為委派本模組的薄殼（不再自行實作 TLC 呼叫/
摘要解析/jar 下載），本模組是唯一真相源。

搭配 `tests/test_tla_python_sync.py` 的離線可達性不變量（reachable=N/N，零 Java 依賴、
每次 pytest 強制）：本地常駐守門用 BFS；完整時序+計數器窮舉用本執行器（有 java 時）。

用法：
    python -m tools.fsm_runtime.tlc_runner                       # 跑驗證（jar 需已在 formal/lib/）
    python -m tools.fsm_runtime.tlc_runner --download             # 缺 jar 時先下載
    python -m tools.fsm_runtime.tlc_runner --install-only         # 僅下載 jar 後退出，不跑 TLC
    python -m tools.fsm_runtime.tlc_runner --depth 50
    python -m tools.fsm_runtime.tlc_runner --module FLEET_FSM --cfg FLEET_FSM_LIVENESS.cfg
    python -m tools.fsm_runtime.tlc_runner --download --tla-version v1.8.1  # 下載指定版本 jar
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


def parse_tlc_summary(out: str) -> dict:
    """從 TLC 完整輸出解析最終 summary 計數（distinct / generated / depth）。

    DEF-02-002（v0.04 修正）：取**最後一個**匹配＝最終 summary 行，而非舊版
    `re.search` 取到的中途 progress 行（TLC 執行中會多次印
    "N states generated, M distinct states found..."，首個匹配為早期 progress，
    計數不可靠且可能 distinct > generated）。並以 fail-closed 斷言守 TLC 恆等不變量
    `generated >= distinct`（窮舉先生成後去重）。僅在兩值皆非零且違反時 raise
    （避免 META/FLEET 等小模型零值/邊界誤報）；正常 summary 零影響。
    """
    def _last(pat: str) -> int:
        ms = re.findall(pat, out)
        return int(ms[-1]) if ms else 0

    distinct = _last(r"(\d+)\s+distinct\s+states\s+found")
    generated = _last(r"(\d+)\s+states\s+generated")
    depth = _last(r"depth of the complete state graph search is\s+(\d+)")
    if generated and distinct and generated < distinct:
        raise RuntimeError(
            f"TLC 計數不變量違反：generated({generated}) < distinct({distinct})；"
            f"疑似 parser 抓到非最終 summary 行（DEF-02-002）。")
    return {"distinct": distinct, "generated": generated, "depth": depth}


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
    proc = subprocess.run(cmd, cwd=str(FORMAL_DIR), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    out = proc.stdout + "\n" + proc.stderr

    no_error = "No error has been found" in out
    counts = parse_tlc_summary(out)  # DEF-02-002：last-match + generated>=distinct 斷言
    ok = proc.returncode == 0 and no_error
    return {
        "ok": ok,
        "exit": proc.returncode,
        "no_error": no_error,
        "distinct": counts["distinct"],
        "generated": counts["generated"],
        "depth": counts["depth"],
        "log_tail": "\n".join(out.splitlines()[-20:]),
    }


def main(argv: list[str]) -> int:
    # Windows 主控台預設 cp950/cp1252 無法輸出中文/— — 強制 UTF-8（R11，對齊
    # scripts/gitignore_coverage_lint.py 慣例，防 CLI 輸出反以 UnicodeEncodeError 炸掉）。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - 舊版 / 非 TextIO
            pass
    ap = argparse.ArgumentParser(description="跨平台 TLC 執行器（SDD_FSM / META_FSM 窮舉驗證）")
    ap.add_argument("--depth", type=int, default=50)
    ap.add_argument("--download", action="store_true", help="缺 jar 時先下載 tla2tools.jar")
    ap.add_argument("--install-only", action="store_true",
                    help="僅下載 tla2tools.jar（若不存在）後退出，不執行 TLC（R65 ADR-XPLAT-002 "
                         "§5 Phase 2-A：run_tlc.{sh,ps1} 薄殼委派用，取代兩份各自的 curl/wget/"
                         "Invoke-WebRequest 下載邏輯）")
    ap.add_argument("--module", default="SDD_FSM",
                    help="要驗證的模組（SDD_FSM | META_FSM | FLEET_FSM | COMPOSITION_FSM | OPTIMIZATION_FSM；預設 SDD_FSM）")
    ap.add_argument("--cfg", default=None,
                    help="覆寫由 --module 推導的 .cfg 檔名（預設 None 時沿用 <module>.cfg；"
                         "例：--module FLEET_FSM --cfg FLEET_FSM_LIVENESS.cfg 跑無 SYMMETRY 的"
                         "liveness 窮舉，R65 新增，供 run_tlc.{sh,ps1} 薄殼的 5b 步委派）")
    ap.add_argument("--tla-version", default=None,
                    help="覆寫下載 tla2tools.jar 的版本（預設 None 時沿用 DEFAULT_TLA_VERSION "
                         f"常數＝{DEFAULT_TLA_VERSION!r}；例：--tla-version v1.8.1。R65 item4 恢復"
                         "薄殼化前 TLA_VERSION 環境變數／-TlaVersion 參數的等價覆寫能力，僅在"
                         "使用者顯式帶值時才影響 download_jar()，沒帶值行為不變）")
    args = ap.parse_args(argv[1:])
    tla = f"{args.module}.tla"
    cfg = args.cfg if args.cfg else f"{args.module}.cfg"

    if find_java() is None:
        print("ERROR: java 不存在，請安裝 JDK 11+。", file=sys.stderr)
        return 2

    tla_version = args.tla_version or DEFAULT_TLA_VERSION

    if args.install_only:
        if jar_path().exists():
            print(f"[tlc_runner] jar 已存在：{jar_path()}")
        else:
            download_jar(tla_version)
        print("[tlc_runner] --install-only：完成。")
        return 0

    if not jar_path().exists():
        if args.download:
            download_jar(tla_version)
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
