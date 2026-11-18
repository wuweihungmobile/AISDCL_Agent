"""sessionctl_handoff 家族：RV-H1～H5（handoff build／finalize／spawn／ack／交接包足以接續）。

沙盒怎麼「裝」被測物（不 monkeypatch、不改判準）：把 repo 的 `tools/lib`、`tools/sessionctl.py`、
`.claude/hooks/sessionctl_guard.py`（與 SessionStart 公告用的 `context_budget_guard.py`）**逐位元組**
複製進沙盒專案，等同「把 sessionctl 裝進另一個專案」。被測碼以 `Path(__file__)` 推 repo 根，所以
複本會把沙盒當作它的 repo：git HEAD／工作樹／專案逐字稿目錄全指向沙盒，真視窗只會開在沙盒內，
不會碰到主 repo（主 repo 工作樹髒時 spawn 前置會拒絕，也不會污染主 slug）。
`install_sessionctl` 會比對複本與原檔 sha256，證明跑的是同一份碼。
交接包目錄用 `AUTOSDD_HANDOFF_DIR` 指到沙盒內（環境變數是被測碼自帶的逃生口、不是新增守衛面），
所以全程不碰 `~/.autosdd/handoff`。
"""  # noqa: E501

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from ..driver import EnvMissing
from ..sandbox import REPO, Sandbox
from ..transcript import Transcript
from . import CaseContext, case

CLOSE_HINT = "舊視窗可以關閉"
_NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_SKIP_DIRS = {"__pycache__", "realverify"}
#: 沙盒 git 忽略的執行期產物（工作樹乾淨是 spawn／轉送前置，不可被這些弄髒）。
_GITIGNORE = "hook_events.jsonl\ndebug_*.log\ntraces/\nhandoff/\n__pycache__/\n*.pyc\n"
_HOOKS_REL = ".claude/hooks"


# ───────────────────────────────────────────────────────────── 安裝／環境
def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _copy_tree(src: Path, dst: Path) -> int:
    n = 0
    for p in src.rglob("*"):
        rel = p.relative_to(src)
        if p.is_dir() or any(part in _SKIP_DIRS for part in rel.parts) or p.suffix == ".pyc":
            continue
        t = dst / rel
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, t)
        n += 1
    return n


def _git(sb: Sandbox, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(sb.root), capture_output=True, text=True,  # noqa: S603,S607
                       encoding="utf-8", errors="replace", creationflags=_NOWIN)
    return r.stdout


def _make_removable(root: Path) -> None:
    """git 物件檔是唯讀，沙盒 commit 之後 `shutil.rmtree` 在 Windows 會留殘渣：先全部解除唯讀。"""
    for dirpath, dirnames, filenames in os.walk(root):
        for name in (*dirnames, *filenames):
            try:
                os.chmod(os.path.join(dirpath, name), stat.S_IWRITE | stat.S_IREAD)
            except OSError:
                pass


def install_sessionctl(sb: Sandbox, *, announce: bool = False, guard_events: tuple[str, ...] = ("UserPromptSubmit", "Stop")) -> None:  # noqa: E501
    """把 sessionctl 裝進沙盒（複本與原檔逐位元組相同，已驗），掛 hook，commit 成乾淨工作樹。"""
    _copy_tree(REPO / "tools" / "lib", sb.root / "tools" / "lib")
    for rel in ("tools/sessionctl.py", "tools/_stdio_utf8.py", f"{_HOOKS_REL}/sessionctl_guard.py"):
        (sb.root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, sb.root / rel)
    scripts = [f"{_HOOKS_REL}/sessionctl_guard.py", "tools/lib/sessionctl/handoff.py"]
    if announce:
        shutil.copy2(REPO / _HOOKS_REL / "context_budget_guard.py", sb.root / _HOOKS_REL / "context_budget_guard.py")  # noqa: E501
        scripts.append(f"{_HOOKS_REL}/context_budget_guard.py")
    for rel in scripts:
        if _sha(REPO / rel) != _sha(sb.root / rel):
            raise AssertionError(f"沙盒複本與 repo 原檔不同（不是同一份被測碼）：{rel}")
    guard = sb.root / _HOOKS_REL / "sessionctl_guard.py"
    for ev in guard_events:
        sb.add_hook(ev, guard, timeout=50 if ev == "UserPromptSubmit" else 30)
    if announce:
        sb.add_hook("SessionStart", sb.root / _HOOKS_REL / "context_budget_guard.py", timeout=30)
    (sb.root / ".gitignore").write_text(_GITIGNORE, encoding="utf-8", newline="\n")
    orig_cleanup = sb.cleanup  # 只包這個沙盒實例的清理（先解唯讀），不動被測模組
    sb.cleanup = lambda: (_make_removable(sb.root), orig_cleanup())[1]  # type: ignore[method-assign]
    _git(sb, "add", "-A")
    _git(sb, "commit", "-q", "-m", "rv: install sessionctl")
    left = _git(sb, "status", "--short").strip()
    if left:
        raise AssertionError(f"沙盒安裝後工作樹不乾淨：{left[:200]}")


def sc_env(sb: Sandbox, **extra: str) -> dict:
    """被測碼與其 hook 需要的環境：交接包目錄＋痕跡目錄都在沙盒內；視窗用 haiku。"""
    # PARK_GUARD_OFF：真實額度讀數會讓 park 推回隨機出現，與被測的封存／轉送閘無關（逃生口只關 park 分支）  # noqa: E501
    e = {"AUTOSDD_HANDOFF_DIR": str(sb.root / "handoff"), "ANTHROPIC_MODEL": "haiku",
         "AUTOSDD_PARK_GUARD_OFF": "1"}
    e.update(extra)
    return e


def handoff_dir(sb: Sandbox) -> Path:
    return sb.root / "handoff"


def run_cli(sb: Sandbox, *args: str, env_extra: dict | None = None, timeout: int = 120) -> tuple[int, str, str]:  # noqa: E501
    """跑沙盒內安裝的真 `tools/sessionctl.py`（cwd＝沙盒）。"""
    env = sb.env(sc_env(sb, **(env_extra or {})))
    r = subprocess.run([sys.executable, str(sb.root / "tools" / "sessionctl.py"), *args],  # noqa: S603
                       cwd=str(sb.root), env=env, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout, creationflags=_NOWIN)
    return r.returncode, r.stdout, r.stderr


def packages(sb: Sandbox) -> list[Path]:
    d = handoff_dir(sb)
    return sorted(d.glob(f"{sb.sid}_*.md"), key=lambda p: p.name) if d.is_dir() else []


def package_for(sb: Sandbox) -> Path:
    ps = [p for p in packages(sb) if not p.name.endswith(".prompts.md") and ".forward-" not in p.name]  # noqa: E501
    if not ps:
        raise AssertionError("沙盒交接包目錄沒有該 sid 的交接包")
    return ps[-1]


def fill_main_layer(path: Path, *, drop: str | None = None, next_step: str = "回報完成。") -> None:
    """把交接包主控層骨架的 `TODO:` 填成真內容；`drop` 指定的節標題（如「## 禁止事項」）整節刪除。"""  # noqa: E501
    text = path.read_text(encoding="utf-8")
    body = {"## 已驗證": "RV 沙盒：build 已跑、機械層含真 HEAD。", "## 未完成": "無（realverify 案例）。",  # noqa: E501
            "## 下一步確切指令": next_step, "## 禁止事項": "不准 --no-verify；不准動沙盒以外的檔。",
            "## 已代決事項與 WHY": "（無）", "## 待掌舵者決定": "（無）"}
    head, mark, main = text.partition("## 主控層")
    out = []
    for h, b in body.items():
        if h == drop:
            continue
        out.append(f"{h}\n{b}")
    path.write_text(head + mark + "\n\n" + "\n\n".join(out) + "\n", encoding="utf-8", newline="\n")


# ───────────────────────────────────────────────────────────── 行程身分／收窗
def cmdline_of(pid: int) -> str:
    if os.name != "nt":  # 行程身分驗證只在 Windows（Get-CimInstance）；他平台＝環境缺件 rc 2
        raise EnvMissing("cmdline_of 只在 Windows 可跑")
    r = subprocess.run(  # noqa: S603
        ["powershell.exe", "-NoProfile", "-Command",
         f"(Get-CimInstance Win32_Process -Filter 'ProcessId={int(pid)}').CommandLine"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=_NOWIN)
    return (r.stdout or "").strip()


def pid_alive(pid: int) -> bool:
    return bool(cmdline_of(pid))


def kill_verified(pid: int, needle: str) -> bool:
    """只在 pid 的命令列含 `needle`（沙盒 sid）且是 claude 行程時才收；驗不到就不砍。"""
    if os.name != "nt":
        raise EnvMissing("kill_verified 只在 Windows 可跑")
    cl = cmdline_of(pid)
    if not cl or needle not in cl or "claude" not in cl.lower():
        return False
    subprocess.run(["taskkill", "/PID", str(int(pid)), "/T", "/F"], capture_output=True,  # noqa: S603,S607
                   creationflags=_NOWIN)
    return True


def spawn_trace(sb: Sandbox, event: str) -> list[dict]:
    p = sb.root / "traces" / "autosdd_session_switch.jsonl"
    if not p.is_file():
        return []
    out = []
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("event") == event:
            out.append(d)
    return out


def other_transcripts(sb: Sandbox) -> list[Path]:
    """沙盒 slug 目錄裡 sid 不等於沙盒主 sid 的逐字稿（＝spawn／轉送開出的新視窗）。"""
    out = []
    for d in sb.transcript_dirs():
        out += [p for p in d.glob("*.jsonl") if p.stem != sb.sid]
    return out


def backdate_transcript(path: Path, hours: float) -> int:
    """只改**沙盒自己逐字稿**每筆記錄的 timestamp（往前推 N 小時）＝模擬快取已冷；回改了幾筆。"""
    n = 0
    lines = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(ln)
        except ValueError:
            lines.append(ln)
            continue
        ts = d.get("timestamp") if isinstance(d, dict) else None
        if isinstance(ts, str):
            t = datetime.fromisoformat(ts.replace("Z", "+00:00")) - timedelta(hours=hours)
            d["timestamp"] = t.isoformat().replace("+00:00", "Z")
            n += 1
        lines.append(json.dumps(d, ensure_ascii=False))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return n


def set_ctx(path: Path, ctx: int) -> int:
    """把沙盒自己逐字稿裡**所有**帶 usage 的 assistant 記錄改成上下文 `ctx`（input 1＋
    cache_read ctx-1）；回改了幾筆。只動沙盒自己的檔、只動 usage 三欄，其餘欄位原樣。"""
    n, lines = 0, []
    for ln in path.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(ln)
        except ValueError:
            lines.append(ln)
            continue
        msg = d.get("message") if isinstance(d, dict) else None
        use = msg.get("usage") if isinstance(msg, dict) else None
        if d.get("type") == "assistant" and isinstance(use, dict) and msg.get("model") != "<synthetic>":  # noqa: E501
            use.update(input_tokens=1, cache_read_input_tokens=ctx - 1, cache_creation_input_tokens=0)  # noqa: E501
            n += 1
        lines.append(json.dumps(d, ensure_ascii=False))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return n


def wait_for(cond, timeout_s: float, step: float = 1.0):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        v = cond()
        if v:
            return v
        time.sleep(step)
    return cond()


def new_session(sb: Sandbox) -> Sandbox:
    """同沙盒根、全新 sid 的第二個 session（不登記進 ctx：根目錄由原沙盒清）。"""
    return Sandbox(root=sb.root, sid=str(uuid.uuid4()))


def blocking_texts(tr, hook_event: str) -> list[str]:
    return [r.data["attachment"]["blockingError"]["blockingError"]
            for r in tr.hook_blocking_errors(hook_event)]


def seal_session(ctx: CaseContext, sb: Sandbox, *, announce: bool = False, first_prompt: str = "Reply with exactly: ok",  # noqa: E501
                 next_step: str = "回報完成。") -> Path:
    """裝 sessionctl → 真 `claude -p` 產逐字稿 → 真 CLI build → 填主控層 → 真 CLI finalize（封存）。"""  # noqa: E501
    install_sessionctl(sb, announce=announce)
    r = ctx.run_claude(sb, first_prompt, env_extra=sc_env(sb))
    ctx.check(r.rc == 0, f"首輪 claude -p rc={r.rc} {r.stderr[:200]}")
    rc, out, err = run_cli(sb, "handoff", "--build", "--session-id", sb.sid)
    ctx.check(rc == 0, f"handoff --build rc={rc} {err[:200]}")
    pkg = package_for(sb)
    fill_main_layer(pkg, next_step=next_step)
    rc, out, err = run_cli(sb, "handoff", "--finalize", str(pkg))
    ctx.check(rc == 0, f"handoff --finalize rc={rc} {out[:200]} {err[:200]}")
    return pkg


# ───────────────────────────────────────────────────────────── RV-H1～H5
@case("RV-H1", "sessionctl_handoff", refs=("V3",))
def rv_h1(ctx: CaseContext) -> None:
    """真逐字稿 → 真 CLI `handoff --build`：機械層含沙盒真 HEAD、真逐字稿路徑與真 assistant 收尾。"""  # noqa: E501
    sb = ctx.sandbox()
    install_sessionctl(sb)
    r = ctx.run_claude(sb, "Reply with exactly: RV_H1_REPLY", env_extra=sc_env(sb))
    ctx.check(r.rc == 0, f"claude -p rc={r.rc}")
    head = _git(sb, "rev-parse", "HEAD").strip()
    ctx.check(len(head) == 40, "沙盒 HEAD 取不到")
    rc, out, err = run_cli(sb, "handoff", "--build", "--session-id", sb.sid)
    ctx.check(rc == 0, f"--build rc={rc} {err[:200]}")
    pkg = package_for(sb)
    ctx.check(out.strip() == str(pkg), f"--build 輸出的路徑與交接包不符：{out.strip()!r}")
    text = pkg.read_text(encoding="utf-8")
    ctx.check(head in text, "機械層沒有沙盒真 HEAD（拿到別的 repo 的 HEAD？）")
    ctx.check(sb.sid in text and str(sb.root) in text, "機械層沒有沙盒 sid／repo 根")
    ctx.check("RV_H1_REPLY" in text, "機械層「最近 assistant 收尾」沒有真逐字稿的回覆")
    tp = ctx.transcript(sb).path
    ctx.check(str(tp) in text, "機械層「逐字稿路徑」不是沙盒真逐字稿")
    ctx.check("## 主控層" in text and "TODO:" in text, "沒有主控層骨架")
    ctx.check(not pkg.with_suffix(".sealed").exists(), "build 不該產生封存戳")
    rc2, out2, _ = run_cli(sb, "handoff", "--build", "--session-id", sb.sid)
    ctx.check(rc2 == 0 and out2.strip() == str(pkg), "同 sid 再 build 應沿用未過期的包（不重複產生）")  # noqa: E501
    ctx.evidence(f"RV-H1 {sb.sid[:8]} 交接包機械層含 HEAD {head[:8]}")
    ctx.notes.append("限制：-p 逐字稿的 user 記錄沒有 origin.kind=human，真人提示欄在 -p 下為「量不到」；"  # noqa: E501
                     "提示全文由互動 session 的記錄形態決定")


@case("RV-H2", "sessionctl_handoff", refs=("V3",))
def rv_h2(ctx: CaseContext) -> None:
    """`--finalize`：主控層有 TODO／缺節 ⇒ rc≠0 且不寫 `.sealed`；補齊 ⇒ `.sealed`＋`.prompts.md`。"""  # noqa: E501
    sb = ctx.sandbox()
    install_sessionctl(sb)
    r = ctx.run_claude(sb, "Reply with exactly: RV_H2_REPLY", env_extra=sc_env(sb))
    ctx.check(r.rc == 0, f"claude -p rc={r.rc}")
    rc, _, err = run_cli(sb, "handoff", "--build", "--session-id", sb.sid)
    ctx.check(rc == 0, f"--build rc={rc} {err[:200]}")
    pkg = package_for(sb)
    sealed, side = pkg.with_suffix(".sealed"), pkg.with_name(f"{pkg.stem}.prompts.md")
    rc, out, _ = run_cli(sb, "handoff", "--finalize", str(pkg))
    ctx.check(rc != 0 and "TODO" in out, f"骨架未填卻通過／沒說 TODO：rc={rc} {out[:200]}")
    ctx.check(not sealed.exists() and not side.exists(), "驗不過卻寫了 .sealed／.prompts.md")
    fill_main_layer(pkg, drop="## 禁止事項")
    rc, out, _ = run_cli(sb, "handoff", "--finalize", str(pkg))
    ctx.check(rc != 0 and "禁止事項" in out, f"缺節卻通過／沒指出缺項：rc={rc} {out[:200]}")
    ctx.check(not sealed.exists() and not side.exists(), "缺節卻寫了 .sealed／.prompts.md")
    fill_main_layer(pkg)
    rc, out, err = run_cli(sb, "handoff", "--finalize", str(pkg))
    ctx.check(rc == 0, f"補齊後 finalize rc={rc} {out[:200]} {err[:200]}")
    ctx.check(sealed.is_file() and side.is_file(), "補齊後沒有 .sealed／.prompts.md")
    stamp = datetime.fromisoformat(sealed.read_text(encoding="utf-8").strip())
    ctx.check(stamp.tzinfo is not None, "封存戳沒有時區 offset")
    ctx.check("RV 沙盒：build 已跑" in pkg.read_text(encoding="utf-8"), "封存重建後主控層原文沒逐字保留")  # noqa: E501
    ctx.evidence(f"RV-H2 {sb.sid[:8]} 封存戳 {stamp.isoformat()}")


@case("RV-H3", "sessionctl_handoff", refs=("V3", "V-PK2"))
def rv_h3(ctx: CaseContext) -> None:
    """`--spawn`：真的開出互動視窗行程（命令列含交接包路徑）。

    限制（掌舵者 2026-11-18 指示）：新沙盒目錄的互動 claude 會卡在資料夾信任對話框，不得改
    使用者層設定繞過 ⇒ 不等新逐字稿／SessionStart；`--spawn` 因「未見逐字稿」回 rc 1 是預期。
    本案例整棒唯二會開真視窗的案例之一，視窗在 finally 依 pid＋命令列驗身分後 60 秒內收掉。
    """
    sb = ctx.sandbox()
    pkg = seal_session(ctx, sb)
    pids: list[int] = []
    try:
        rc, out, err = run_cli(sb, "handoff", "--spawn", str(pkg), timeout=90)
        rows = spawn_trace(sb, "session_switch_spawned")
        ctx.check(bool(rows), f"沒有 session_switch_spawned 痕跡：rc={rc} {err[:300]}")
        row = rows[-1]
        pids = [int(x["pid"]) for x in rows if isinstance(x.get("pid"), int)]
        pid = row.get("pid")
        ctx.check(isinstance(pid, int) and pid > 0, f"痕跡沒有 pid：{row}")
        ctx.check(row.get("handoff") == str(pkg) and row.get("sid") == sb.sid, "痕跡的交接包／sid 不符")  # noqa: E501
        cl = cmdline_of(pid)
        if rc == 0:
            ctx.check(CLOSE_HINT in out, "spawn 成功輸出沒有「舊視窗可以關閉」")
        else:
            ctx.check("未見逐字稿" in err or "行程已不在" in err, f"rc≠0 卻不是預期的原因：{err[:300]}")  # noqa: E501
        ctx.check(bool(cl) and "claude" in cl.lower() and str(pkg) in cl,
                  f"視窗行程命令列不含交接包路徑（沒開出正確視窗）：{cl[:200]!r}")
        # （命令列的中文字樣經主控台字碼頁往返會失真，不拿來斷言；路徑與 sid 是 ASCII，已驗）
        rc2, _, err2 = run_cli(sb, "handoff", "--spawn", str(pkg), timeout=60)
        ctx.check(rc2 != 0 and "已 spawn 過" in err2, f"同一包重複 spawn 沒被拒：rc={rc2} {err2[:200]}")  # noqa: E501
        ctx.evidence(f"RV-H3 {sb.sid[:8]} pid={pid} rc={rc}（信任對話框限制：不等新逐字稿）")
    finally:
        pids = sorted({*pids, *(int(x["pid"]) for x in spawn_trace(sb, "session_switch_spawned")
                                if isinstance(x.get("pid"), int))})
        for p in pids:
            kill_verified(p, sb.sid)
        time.sleep(2)
        left = [p for p in pids if pid_alive(p)]
        ctx.check(not left, f"開出的視窗沒收乾淨：{left}")


@case("RV-H4", "sessionctl_handoff", refs=("V3",))
def rv_h4(ctx: CaseContext) -> None:
    """新 session 的 SessionStart 公告交接包 → `--ack` 寫 `.ack`（輸出含「舊視窗可以關閉」）→ 再起不再公告。"""  # noqa: E501
    sb = ctx.sandbox()
    pkg = seal_session(ctx, sb, announce=True)
    s2 = new_session(sb)
    r2 = ctx.run_claude(s2, "Reply with exactly: RV_H4_B", env_extra=sc_env(sb))
    ctx.check(r2.rc == 0, f"新 session rc={r2.rc} {r2.stderr[:200]}")
    t2 = Transcript.for_sid(s2.sid)
    ann = [r for r in t2.recs if pkg.name in json.dumps(r.data, ensure_ascii=False)
           and "未接手的交接包" in json.dumps(r.data, ensure_ascii=False)]
    ctx.check(bool(ann), "新 session 的逐字稿沒有 SessionStart 公告（未接手的交接包）")
    ctx.check(not pkg.with_suffix(".ack").exists(), "公告階段不該寫 .ack（只有 --ack 會寫）")
    rc, out, err = run_cli(sb, "handoff", "--ack", str(pkg))
    ctx.check(rc == 0 and pkg.with_suffix(".ack").is_file(), f"--ack rc={rc} {err[:200]}")
    ctx.check(CLOSE_HINT in out, f"ack 輸出沒有「舊視窗可以關閉」：{out[:200]!r}")
    rc_bad, _, _ = run_cli(sb, "handoff", "--ack", str(pkg.with_name("nope.md")))
    ctx.check(rc_bad != 0, "ack 不存在的包應 rc≠0")
    s3 = new_session(sb)
    n_before = len([e for e in sb.events() if e["ev"] == "SessionStart"])
    r3 = ctx.run_claude(s3, "Reply with exactly: RV_H4_C", env_extra=sc_env(sb))
    ctx.check(r3.rc == 0, f"第三個 session rc={r3.rc}")
    ctx.check(len([e for e in sb.events() if e["ev"] == "SessionStart"]) > n_before,
              "第三個 session 的 SessionStart 沒跑（對照組無效）")
    t3 = Transcript.for_sid(s3.sid)
    ctx.check(not any(pkg.name in json.dumps(r.data, ensure_ascii=False) for r in t3.recs),
              "已 ack 的包又被公告了")
    ctx.evidence(f"RV-H4 公告 {t2.coords(ann[0])}；ack 後 {s3.sid[:8]} 無公告")


@case("RV-H5", "sessionctl_handoff", refs=("AT-HV2-9",))
def rv_h5(ctx: CaseContext) -> None:
    """交接包足以接續：新 claude -p 只憑包內「下一步確切指令」做出可驗證的小事。"""
    sb = ctx.sandbox()
    token = "RV_H5_TOKEN_7731"
    step = f"在沙盒根目錄建立檔案 rv_h5_done.txt，內容恰為 {token}（Write 工具；做完回覆 DONE）。"
    pkg = seal_session(ctx, sb, next_step=step)
    s2 = new_session(sb)
    prompt = (f"按交接包繼續：讀 {pkg}（只讀這一個檔）。照其中「下一步確切指令」做，"
              "做完回覆 DONE，其他事都不要做。")
    r = ctx.run_claude(s2, prompt, env_extra=sc_env(sb), timeout_s=200,
                       extra_args=("--allowedTools=Read,Write",))
    ctx.check(r.rc == 0, f"接手 session rc={r.rc} {r.stderr[:200]}")
    done = sb.root / "rv_h5_done.txt"
    ctx.check(done.is_file(), f"接手 session 沒做出指定檔；stdout={r.stdout[:200]!r}")
    ctx.check(token in done.read_text(encoding="utf-8"), "檔案內容不是交接包指定的 token")
    ctx.evidence(f"RV-H5 接手 {s2.sid[:8]} 依包建出 rv_h5_done.txt")
