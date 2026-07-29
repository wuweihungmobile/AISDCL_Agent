#!/usr/bin/env python3
# 🔴 本檔 docstring 必須維持 raw（`r"""`）：內文引述 Windows 路徑形態
# （`.\local_ci_gate.ps1`），非 raw 時 `\l` 是**非法轉義序列**——Python 3.11 印
# DeprecationWarning、3.12 起升為 SyntaxWarning、CPython 已宣告未來版本改為
# SyntaxError（屆時本檔＝本機 CI 閘門唯一核心將無法 import）。R60 QA-R60-05 實測：
# 本輪新增該行時 `pytest tests/ -q` 尾行就印出 `invalid escape sequence '\l'`，
# 而專案 ruff `select` 當時不含 `W` ⇒ 閘門結構上看不到（已同輪把 `W` 補進 select，
# 見 pyproject.toml）。改回非 raw 會讓 `ruff check --select W605` 與
# `python -W error::SyntaxWarning` 兩道都紅。
r"""local_ci_gate.py — 本機 CI 閘門單一核心（macOS / Linux / Windows 共用）。

DEF-101-070 ② 收斂案（R12 ARCH-R12-1）：原 tools/local_ci_gate.{sh,ps1} 為雙實作
（bash / PowerShell 各長一份業務邏輯，靠 tools/check_script_parity.py 事後比對防漂移），
本檔將全部 gate 語意收斂為單一 Python 核心，兩支同名 .sh / .ps1 降為「確認直譯器 →
轉呼叫本檔 → 傳遞 exit code」的薄殼——模式對齊 tools/dev_start.{py,sh,ps1} 既有範例。
薄殼本身由 monorepo 根 tools/check_wrapper_thinness.py 以正規化內容 hash 釘選守門
（釘選與 check_script_parity.py 的 _THINNESS_ENROLLED 登記均已接線，兩清單另有
鍵集合交叉鎖）。介面邊角揭露（R12 SD 一審 SD-1）：.ps1 薄殼 `-PytestArgs ''`
（空字串）現落回核心預設參數——舊版此邊角行為 host 相依（PS5.1 丟空元素、
pwsh 7.3+ 傳 '' 使 pytest 報錯），新行為為兩者之良性收斂；`-PytestArgs '--act'`
會被核心解析為 gate 旗標而非 pytest 參數（舊版傳給 pytest 報錯），正常用法不受影響。

R60 訂正（F-refuter-1）：上段「`-PytestArgs ''` 落回核心預設」曾是需要特別揭露的
**邊角**，因為 .ps1 的 `$PytestArgs` 預設值寫死著一份 `'tests/ -q --tb=short'`——
R59 在下方 DEFAULT_PYTEST_ARGS 加 `-rs` 時那份複本沒跟上，於是 Windows 側（含
nightly Stage L）**無參數呼叫**就被薄殼整批取代掉核心預設、`-rs` 靜默消失。現已把
.ps1 預設改為 `''`，「無參數」與「`-PytestArgs ''`」兩條路完全等價、都落回本檔的
單一真相源，上段揭露因此降為歷史註記。另訂正該段自身的一處不可達：以本檔
`.EXAMPLE` 示範的 `-File` 呼叫傳 `-PytestArgs ''`，PS 5.1 直接報
`Missing an argument for parameter 'PytestArgs'` 而中止（要走呼叫運算子
`& …\local_ci_gate.ps1 -PytestArgs ''` 才到得了該邊角）——即該邊角在文件自己示範的
載具上根本觸發不到。跨檔語意鎖：tests/tools/test_local_ci_gate_shell_arg_parity.py。

依序（全綠才建議 push；鏡像 monorepo 根層 .github/workflows/autoclaude-ci.yml push gating jobs）：
  0. editable 哨兵       （autoclaude 指向本 monorepo；in-process 動態比對，取證紀律 #19）
  1. LOC 預算
  2. CLAUDE.md <= 400 行
  2b. CLAUDE.md 單行 <= 800 codepoint（contract test）
  3. snapshot 可重現
  4. import-linter
  5. pytest
可選：
  --pg   額外起 docker-compose.ci.yml（pg17）跑 PG 契約測
  --act  額外用 act 在 Linux 容器跑 ci.yml（POSIX 走 run_act.sh；Windows 以 PowerShell
         載具 -File 呼叫 run_act.ps1，powershell 優先、pwsh 後備——對齊 tools/dev_start.py
         先例與 Local_CI_Parity_NextAction「pwsh→powershell（本機僅 PS5.1）」修正史料）

用法（一般經薄殼呼叫；直接呼叫亦可）：
  python tools/local_ci_gate.py
  python tools/local_ci_gate.py --act
  python tools/local_ci_gate.py --pg
  python tools/local_ci_gate.py -k test_foo -v   # 非 --act/--pg 參數整批取代預設 pytest 參數
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent  # AutoClaude repo 根
MONO_ROOT = REPO_ROOT.parent                        # monorepo 根 — 定位共用 tools/

# platform_utils 位於 monorepo 根 tools/lib/ 子目錄（非本檔同層），需顯式插入
# sys.path 才能 import——手法對齊本輪其他核心檔案既有慣例（R17 DEF-101-231 觀察點
# 1+2：收斂 is_windows/os_label/venv_python_path 平台判斷邏輯的第二次重複）。
sys.path.insert(0, str(MONO_ROOT / "tools" / "lib"))
import platform_utils  # noqa: E402

# `-rs`（R59 ARCH-R59-01）：印出每一支 skip 的理由。
# WHY：DEF-101-510 立的原則是「因為跑在某平台而失去的覆蓋不得只併成一個數字」，但那輪
# 只把機制補在根層 `tools/run_root_unittests.py`（unittest 沒有 `-rs` 這種內建能力，只好
# 自己寫）。真正的測試量體在 pytest 側（AutoClaude 3740/208），而本 repo 所有 pytest
# 呼叫端一律 `-q` 且從未加 `-rs`——`grep -rn '\-rs\b'` 全 repo 唯一命中曾是 run_root_unittests
# 的一句註解。也就是說「skip 可見度」只做在最小的那一面：DEF-101-515 之所以要人工考古才
# 解釋得出 v0.30 −4（`requires_docker_success` 硬排除 win／POSIX shebang `skipif(win)`），
# 正是因為 pytest 面把理由丟掉了。加 `-rs` 是這件事的最小修法（pytest 內建，零新程式碼）。
# 安全性已實測：`scripts/pytest_passed_count.sh` 以 `grep -oE '[0-9]+ passed' | tail -1`
# 取值，SKIPPED 行不含該樣式，加 `-rs` 後計數不變（R59 實測仍得正確值）。
DEFAULT_PYTEST_ARGS = ["tests/", "-q", "-rs", "--tb=short"]

_PG_DSN = "postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/autoclaude"
_PG_COMPOSE = ["docker", "compose", "-f", "docker-compose.ci.yml"]


def parse_args(argv: list[str]) -> tuple[bool, bool, list[str]]:
    """解析參數（語意照收斂前 .sh 逐參數迴圈）。

    --act / --pg 為旗標，可出現在任意位置；首個非旗標參數起「整批取代」預設
    pytest 參數（而非附加），其後的非旗標參數依序累積。
    """
    do_act = False
    do_pg = False
    pytest_args = list(DEFAULT_PYTEST_ARGS)
    overridden = False
    for arg in argv:
        if arg == "--act":
            do_act = True
        elif arg == "--pg":
            do_pg = True
        else:
            if not overridden:
                pytest_args = []
                overridden = True
            pytest_args.append(arg)
    return do_act, do_pg, pytest_args


def _stream(cmd: list[str]) -> int:
    """直通輸出執行子行程（繼承 stdio）；FileNotFoundError 等交由 run_gate 統一判 FAIL。"""
    return subprocess.run(cmd).returncode


def _run_quiet(cmd: list[str]) -> int:
    """靜音執行（對齊 .sh 的 `>/dev/null 2>&1 || true` 清理語意）；任何失敗都不外拋。"""
    try:
        return subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode
    except OSError:
        return 1


def _hooks_liveness_advisory() -> None:
    """git hooks liveness 偵測（警告不擋）。

    repo 搬移/改名或未安裝時 dispatcher hooks 會靜默失效（實證）；CI 環境（CI 有值）
    跳過（GitHub/act 環境無 hooks 屬正常）。偵測邏輯抽共用（S11）：見 monorepo 根
    tools/check_hooks_liveness.py（單一真相源）。advisory：任何探測失敗（含腳本
    自身 rc != 0 / 直譯器炸掉）都不得影響閘門本體——對齊 .ps1 的 try/catch 語意。
    """
    if os.environ.get("CI"):
        return
    script = MONO_ROOT / "tools" / "check_hooks_liveness.py"
    if not script.is_file():
        return
    try:
        subprocess.run([sys.executable, str(script)])
    except OSError:
        pass


# ---------------------------------------------------------------------------
# 各 gate（名稱字串與順序為凍結介面——由 tests/tools/test_local_ci_gate.py 的
# _BASE_GATES 精確等值測試機械凍結，文件（CLAUDE.md/Guide）亦引用這些字樣，勿改；
# 另一道獨立訊號＝根層 dispatcher pre-push AutoClaude leg 直跑 pytest，不經本檔）
# ---------------------------------------------------------------------------

def gate_editable() -> int:
    """0. editable 哨兵：autoclaude 套件須位於本 repo 根之下（取證紀律 #19）。

    動態比對 repo 根（勿硬編碼資料夾名——clone 到任何目錄名皆應 PASS）。in-process
    import 時 sys.path[0] 為 tools/（無 cwd 遮蔽），真正檢驗 editable 安裝指向，
    比舊 `python -c`（sys.path[0]=cwd，源碼樹恆遮蔽 site-packages）更貼近哨兵原意。
    """
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, encoding="utf-8", errors="replace",
        )
        top = proc.stdout.strip() if proc.returncode == 0 else ""
    except OSError:
        top = ""  # 對齊 .sh 的 `git rev-parse … || pwd` 回退
    if not top:
        top = os.getcwd()
    import autoclaude  # 延遲 import：未安裝（ImportError）由 run_gate 統一判 FAIL

    pkg = Path(autoclaude.__file__).resolve()
    root = Path(top).resolve()
    ok = root == pkg or root in pkg.parents
    print("autoclaude:", pkg)
    print("repo root :", root)
    return 0 if ok else 1


def gate_loc() -> int:
    """1. LOC 預算。"""
    return _stream([sys.executable, "tools/check_loc_budget.py"])


def gate_claudemd() -> int:
    """2. CLAUDE.md <= 400 行。

    行計數採 .ps1 的 ReadAllLines 語意（末行無換行符仍計 1 行）——為 wc -l
    （只數 \\n）的超集合，較保守；檔案以換行結尾時兩者相等。
    """
    with open(REPO_ROOT / "CLAUDE.md", encoding="utf-8", errors="replace") as fh:
        n = sum(1 for _ in fh)
    if n > 400:
        print(f"CLAUDE.md={n} > 400")
        return 1
    print(f"CLAUDE.md={n} lines OK")
    return 0


def gate_claudemd_line() -> int:
    """2b. CLAUDE.md 單行 <= 800 codepoint（contract test）。"""
    return _stream([
        sys.executable, "-m", "pytest",
        "tests/contract/test_claude_md_no_long_lines.py", "-q", "--tb=short",
    ])


def gate_snapshot() -> int:
    """3. snapshot 可重現。"""
    return _stream([sys.executable, "tools/snapshot_sync.py", "--check"])


def gate_importlinter() -> int:
    """4. import-linter（未安裝時同收斂前語意：印指引並判 FAIL）。"""
    exe = shutil.which("lint-imports")
    if exe is None:
        print("lint-imports 未安裝（pip install -e '.[lint]'）")
        return 1
    return _stream([exe])


def gate_pytest(pytest_args: list[str]) -> int:
    """5. pytest（參數可被位置參數整批取代，見 parse_args）。"""
    return _stream([sys.executable, "-m", "pytest", *pytest_args])


def gate_pg() -> int:
    """選配：PG 契約測 via docker-compose.ci.yml（pg17）。

    --wait：等 healthcheck 通過才回（慢機不會 PG 未 ready 就跑 alembic）。
    alembic rc 防吞：migration 失敗即清理容器並判 FAIL，不讓後續 pytest rc 蓋過。
    alembic 以 `python -m alembic` 執行（同 venv 同直譯器；bare `alembic` 缺裝時
    .sh 是 rc=127 判 FAIL，此處為 module not found rc != 0，殊途同歸且必經清理）。
    """
    if _stream([*_PG_COMPOSE, "up", "-d", "--wait"]) != 0:
        print("docker compose up --wait 失敗")
        return 1
    # 全程用 asyncpg DSN，與 CI 一致（alembic/env.py 會自動 strip +asyncpg 改 psycopg2）；
    # export 至行程環境（對齊 .sh export 語意——其後 gate 亦可見）
    os.environ["AUTOCLAUDE_DB_DSN"] = _PG_DSN
    os.environ["AUTOCLAUDE_TEST_PG_DSN"] = _PG_DSN
    os.environ["AUTOCLAUDE_ALLOW_INSECURE_DB"] = "1"
    if _stream([sys.executable, "-m", "alembic", "upgrade", "head"]) != 0:
        print("alembic upgrade head 失敗")
        _run_quiet([*_PG_COMPOSE, "down", "-v"])
        return 1
    rc = _stream([
        sys.executable, "-m", "pytest",
        "tests/contract/test_pg_state_repository_contract.py", "-q", "--tb=short",
    ])
    _run_quiet([*_PG_COMPOSE, "down", "-v"])
    return rc


def gate_act() -> int:
    """選配：act 在 Linux 容器跑真 CI（test job）。

    POSIX 走 bash 載具跑 run_act.sh；Windows 以 PowerShell 載具 `-File` 呼叫
    run_act.ps1（勿用 -Command 包裹——會吞 exit code 假綠，useMacWin 啟動提示詞
    修漏史料）。探測順序 powershell → pwsh：對齊 tools/dev_start.py 先例與
    Local_CI_Parity_NextAction「pwsh→powershell（本機僅 PS5.1）」修正。
    """
    if platform_utils.is_windows():
        shell = shutil.which("powershell") or shutil.which("pwsh")
        if shell is None:
            print("找不到 PowerShell（powershell / pwsh）— 無法執行 tools/run_act.ps1")
            return 1
        return _stream([
            shell, "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(REPO_ROOT / "tools" / "run_act.ps1"), "-Job", "test",
        ])
    return _stream(["bash", str(REPO_ROOT / "tools" / "run_act.sh"), "--job", "test"])


# ---------------------------------------------------------------------------
# 閘門編排
# ---------------------------------------------------------------------------

def build_gates(
    do_act: bool, do_pg: bool, pytest_args: list[str]
) -> list[tuple[str, Callable[[], int]]]:
    """組出 gate 清單（名稱與順序為凍結介面；--pg 先於 --act，照收斂前 .sh/.ps1）。"""
    gates: list[tuple[str, Callable[[], int]]] = [
        ("editable sentinel", gate_editable),
        ("LOC budget", gate_loc),
        ("CLAUDE.md <=400", gate_claudemd),
        ("CLAUDE.md line<=800", gate_claudemd_line),
        ("snapshot --check", gate_snapshot),
        ("import-linter", gate_importlinter),
        # 延遲查全域名（勿綁死 default）：測試 monkeypatch gate_pytest 後仍需生效
        ("pytest", lambda: gate_pytest(pytest_args)),
    ]
    if do_pg:
        gates.append(("PG contract (pg17)", gate_pg))
    if do_act:
        gates.append(("act CI (Linux test job)", gate_act))
    return gates


def run_gate(name: str, fn: Callable[[], int], results: list[tuple[str, str]]) -> None:
    """執行單一 gate 並收集結果（逐項收集不中斷，對齊 .ps1 Continue 語意）。

    gate 執行失敗（FileNotFoundError 等例外）判 FAIL 不炸——對齊 .ps1 try/catch。
    """
    print(f"\n===== [{name}] =====", flush=True)
    try:
        rc = int(fn() or 0)
    except Exception as exc:  # KeyboardInterrupt 不攔（BaseException 直接外拋）
        print(f"[{name}] 例外：{exc}", flush=True)
        rc = 1
    status = "PASS" if rc == 0 else "FAIL"
    print(f"[{name}] {status} (rc={rc})", flush=True)
    results.append((name, status))


def main(argv: list[str] | None = None) -> int:
    # 自身 stdout/stderr best-effort UTF-8（✅/❌ 於非 UTF-8 終端不崩潰）；
    # 子行程統一 PYTHONUTF8=1（薄殼已先設，此處兜底 direct 呼叫路徑）
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass
    os.environ["PYTHONUTF8"] = "1"
    os.chdir(REPO_ROOT)

    do_act, do_pg, pytest_args = parse_args(sys.argv[1:] if argv is None else argv)
    _hooks_liveness_advisory()

    results: list[tuple[str, str]] = []
    for name, fn in build_gates(do_act, do_pg, pytest_args):
        run_gate(name, fn, results)

    # ----- 總結（字樣為凍結介面）-----
    print("\n========== 本機 CI 閘門總結 ==========", flush=True)
    failed = 0
    for name, status in results:
        print(f"  {name:<22} {status}")
        if status == "FAIL":
            failed += 1
    if failed:
        print(f"\n❌ {failed} 項失敗 — 請於本機修復後再 push。")
        return 1
    print("\n✅ 全部通過 — 可安全 push。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
