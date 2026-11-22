"""假 `claude` 替身（RealVerify_SideEffect_Isolation DES §4.4，REQ-SE-27）。

WHY：到點 job 與 spawn 站點照樣會起 `claude`；真機驗證要能「讓產品走完 spawn 路徑」又**不**開真窗、
不燒額度。替身是 GUI 子系統執行檔（`CREATE_NEW_CONSOLE` 下不建主控台視窗），由 PowerShell 5.1 的
`Add-Type -OutputType WindowsApplication` 現場編出——Windows 內建、無需安裝。行為只由一張判定表決定，
`decide()` 是這張表的唯一真相源，C# 原始碼由**同一張表**產生（`csharp_source()`），AT 驗表、E2E 驗真執行檔。

設定檔都在 `<家>`（`bin/claude.exe` 的上一層）：`fakeclaude.mode`（`resume_ok`／`fresh_ok`／`fail`，缺席＝
`fail`）、`fakeclaude.sleep`（成功模式存活秒數，缺席＝20）、`fakeclaude.rc`（失敗模式結束碼，缺席＝1）、
`fakeclaude.projdir`（逐字稿目錄，缺席 ⇒ 一律 fail，不自行推 slug——slug 規則的 SSOT 留在 Python 端）；
每次被呼叫先在 `fakeclaude.jsonl` 追加一行 `{argv, cwd, at, mode}`（呼叫次數＝行數）。
"""  # noqa: E501

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import NamedTuple

from . import leases, sched

MODES = ("resume_ok", "fresh_ok", "fail")
DEFAULT_SLEEP_S = 20
DEFAULT_RC = 1
EXE_REL = Path("bin") / "claude.exe"
OUT_PREFIX = "AutoSDD_RVout_"  # 家外替身目錄前綴：刻意不含沙盒前綴，不在任何沙盒家目錄之下（D-18 驗證用）  # noqa: E501

#: 判定表（唯一真相源）：`(模式, argv 形狀, 動作)`，自上而下第一列命中即回；末列是兜底 fail。
#: 形狀 `resume`＝含 `-r <sid>` 且不含 `--fork-session`；`fresh`＝不含 `-r`，或含 `--fork-session`。
TABLE: tuple[tuple[str, str, str], ...] = (
    ("resume_ok", "resume", "append"),   # 往 <projdir>/<sid>.jsonl 追加一行，存活 sleep 秒後 rc 0
    ("fresh_ok", "fresh", "new"),        # 新建 <projdir>/<uuid4>.jsonl，存活 sleep 秒後 rc 0
    ("*", "*", "exit"),                  # fail／成功模式遇不適用 argv／projdir 缺席：立即以 rc 結束
)


class Action(NamedTuple):
    kind: str            # append／new／exit
    path: str = ""       # append／new 要寫的逐字稿檔
    sleep: int = 0       # 成功模式存活秒數
    rc: int = DEFAULT_RC  # exit 的結束碼；成功模式結束碼恆為 0


def shape_of(argv: list[str]) -> tuple[str, str]:
    """`(形狀, sid)`：`resume`（含 `-r <sid>` 且無 `--fork-session`）／`fresh`（無 `-r`，或含 fork）。"""  # noqa: E501
    args = list(argv)
    sid = ""
    for i, tok in enumerate(args):
        if tok == "-r" and i + 1 < len(args):
            sid = args[i + 1]
            break
    if sid and "--fork-session" not in args:
        return "resume", sid
    if not sid or "--fork-session" in args:
        return "fresh", sid
    return "other", sid


def decide(argv: list[str], cfg: dict) -> Action:
    """依 `cfg`（mode／sleep／rc／projdir，值皆字串或 None）與 argv 決定動作。純函式，C# 版與它同表。"""  # noqa: E501
    mode = (cfg.get("mode") or "fail").strip()
    rc = _int(cfg.get("rc"), DEFAULT_RC)
    sleep = _int(cfg.get("sleep"), DEFAULT_SLEEP_S)
    projdir = (cfg.get("projdir") or "").strip()
    shape, sid = shape_of(argv)
    for row_mode, row_shape, kind in TABLE:
        if row_mode not in ("*", mode) or row_shape not in ("*", shape):
            continue
        if kind == "exit" or not projdir:
            return Action("exit", rc=rc)
        name = f"{sid}.jsonl" if kind == "append" else f"{uuid.uuid4()}.jsonl"
        return Action(kind, str(Path(projdir) / name), sleep)
    return Action("exit", rc=rc)


def _int(value, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def csharp_source() -> str:
    """由 `TABLE` 逐列產生的 C# 原始碼（每一列都有對應分支與註解 `// ROW n`，AT-SE-46 逐列核對）。"""  # noqa: E501
    branches = []
    for n, (mode, shape, kind) in enumerate(TABLE):
        cond = " && ".join(c for c in (
            f'mode == "{mode}"' if mode != "*" else "",
            f'shape == "{shape}"' if shape != "*" else "") if c) or "true"
        body = ('Fin(rc); return 0;' if kind == "exit" else
                f'if (projdir == "") Fin(rc); Run("{kind}", projdir, sid, sleep); return 0;')
        branches.append(f"        // ROW {n}: mode={mode} shape={shape} action={kind}\n"
                        f"        if ({cond}) {{ {body} }}")
    return _CS_HEAD + "\n".join(branches) + _CS_TAIL


_CS_HEAD = r"""
using System; using System.IO; using System.Text; using System.Threading;
public static class P {
    static string home;
    static string Cfg(string n, string d) {
        string f = Path.Combine(home, "fakeclaude." + n);
        return File.Exists(f) ? File.ReadAllText(f).Trim() : d;
    }
    static string J(string s) {
        return "\"" + s.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\r", "\\r").Replace("\n", "\\n") + "\"";
    }
    static void Fin(int rc) { Environment.Exit(rc); }
    static void Run(string kind, string projdir, string sid, int sleep) {
        string name = kind == "append" ? sid + ".jsonl" : Guid.NewGuid().ToString() + ".jsonl";
        File.AppendAllText(Path.Combine(projdir, name),
            "{\"type\":\"fakeclaude\",\"at\":\"" + DateTime.UtcNow.ToString("o") + "\"}\n");
        Thread.Sleep(sleep * 1000);
        Environment.Exit(0);
    }
    public static int Main(string[] argv) {
        home = Directory.GetParent(Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().Location)).FullName;
        string mode = Cfg("mode", "fail");
        int rc; if (!int.TryParse(Cfg("rc", "1"), out rc)) rc = 1;
        int sleep; if (!int.TryParse(Cfg("sleep", "20"), out sleep)) sleep = 20;
        string projdir = Cfg("projdir", "");
        string sid = ""; bool fork = false;
        for (int i = 0; i < argv.Length; i++) {
            if (argv[i] == "--fork-session") fork = true;
            if (argv[i] == "-r" && sid == "" && i + 1 < argv.Length) sid = argv[i + 1];
        }
        string shape = (sid != "" && !fork) ? "resume" : "fresh";
        StringBuilder a = new StringBuilder("[");
        for (int i = 0; i < argv.Length; i++) a.Append(i > 0 ? "," : "").Append(J(argv[i]));
        a.Append("]");
        File.AppendAllText(Path.Combine(home, "fakeclaude.jsonl"),
            "{\"argv\":" + a + ",\"cwd\":" + J(Directory.GetCurrentDirectory()) + ",\"at\":\""
            + DateTime.UtcNow.ToString("o") + "\",\"mode\":" + J(mode) + "}\n");
"""  # noqa: E501
_CS_TAIL = "\n        Fin(rc);\n        return 0;\n    }\n}\n"


def home_of(exe: Path | str) -> Path:
    """替身執行檔所在 `bin` 目錄的上一層＝家（設定檔與呼叫記錄住這裡）。"""
    return Path(exe).resolve().parent.parent


def build(home: Path | str, *, runner=None) -> Path:
    """在 `<家>/bin/claude.exe` 編出替身（先登記 `temp_file` 帳列）；非 Windows／無 PowerShell 5.1 ⇒ EnvMissing。
    `runner(script) -> (rc, out)` 是縫（預設真 PowerShell 5.1 `powershell.exe`）。"""  # noqa: E501
    from .driver import (
        EnvMissing,  # noqa: PLC0415 — lazy：避免 driver↔sandbox↔leases 的 import 成環
    )
    home = Path(home)
    exe = home / EXE_REL
    leases.track_kind("temp_file", exe)
    exe.parent.mkdir(parents=True, exist_ok=True)
    src = home / "fakeclaude.src.cs"
    src.write_text(csharp_source(), encoding="utf-8", newline="\n")
    q = lambda p: str(p).replace("'", "''")  # noqa: E731
    script = (f"try {{ Add-Type -TypeDefinition ([IO.File]::ReadAllText('{q(src)}')) "
              f"-OutputType WindowsApplication -OutputAssembly '{q(exe)}' "
              "-IgnoreWarnings -ErrorAction Stop } "
              "catch { Write-Output $_.Exception.Message; exit 1 }")
    rc, out = (runner or (lambda s: sched._ps(s, 150)))(script)  # noqa: SLF001 — 同一支 PowerShell 載具
    src.unlink(missing_ok=True)
    if rc != 0 or not exe.is_file():
        raise EnvMissing(f"假 claude 產生失敗（Add-Type rc={rc}）：{out[:200]}")
    leases.made("temp_file", exe)
    return exe


def configure(home: Path | str, mode: str, *, sleep: int | None = None, rc: int | None = None,
              projdir: Path | str | None = None) -> None:
    """寫設定檔。`projdir` 給了：**先**登記 `transcript_dir` 帳列再寫檔（替身會往那裡寫逐字稿）。"""
    if mode not in MODES:
        raise ValueError(f"替身模式只有 {MODES}：{mode}")
    home = Path(home)
    (home / "fakeclaude.mode").write_text(mode, encoding="utf-8")
    for name, value in (("sleep", sleep), ("rc", rc)):
        if value is not None:
            (home / f"fakeclaude.{name}").write_text(str(value), encoding="utf-8")
    if projdir is not None:
        leases.track_kind("transcript_dir", projdir)
        Path(projdir).mkdir(parents=True, exist_ok=True)
        (home / "fakeclaude.projdir").write_text(str(projdir), encoding="utf-8")


def calls(home: Path | str) -> list[dict]:
    """替身被呼叫的記錄（呼叫次數＝長度）。"""
    import json  # noqa: PLC0415
    path = Path(home) / "fakeclaude.jsonl"
    if not path.is_file():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def outside_home(run_id: str | None = None) -> Path:
    """家外替身的「家」：`%TEMP%\\AutoSDD_RVout_<run_id>`（名稱不含沙盒前綴；先登記 `temp_file` 再建）。"""  # noqa: E501
    rid = run_id or leases.current_run_id()
    home = Path(tempfile.gettempdir()).resolve() / f"{OUT_PREFIX}{rid}"
    leases.track_kind("temp_file", home)
    home.mkdir(parents=True, exist_ok=True)
    return home
