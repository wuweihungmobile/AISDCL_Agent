"""交接包機械層（ADR-XPLAT-004 §2.13.4）：程式產生、零 token；每欄取不到寫「量不到：<原因>」。

WHY 獨立一檔：`handoff.py`（公告、ack、finalize、spawn、CLI）已近 LOC 上限；本檔只負責
「把量得到的事實寫成 Markdown」，不判斷、不寫檔、不 spawn（外部指令一律經注入的 `runner`）。

🔴 縫：`runner(argv, *, cwd=None, env=None, creationflags=0, wait=True) -> (rc, stdout, pid)`
是整個套件唯一的外部指令出口（git／排程查詢／互動 spawn 共用）；`wait=False` 時回 `(0, "", pid)`。
13 欄標題＝`MECH_HEADINGS`（TCS AT-SC-34 逐欄斷言；第 12／13 欄 Control_Handover W4 追加於末尾，
欄 1～11 編號不變）。第 12 欄邏輯在 `agentbrief`、第 13 欄在 `promptchain`，本檔只呼叫。
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import sandbox_scope
import transcript_activity

from . import agentbrief, promptchain

#: 交接包機械層的 13 個欄位標題（順序即輸出順序；測試逐一斷言它們都在）。
MECH_HEADINGS = (
    "來源與時刻", "Git 分支與 HEAD", "工作樹狀態", "wip-preserved 標籤", "最近真人提示",
    "最近 assistant 收尾", "背景代理名冊", "排程與 NextRunTime", "額度各軸", "舊 scratchpad 檔案",
    "逐字稿路徑", "在飛／被切代理", "鏈上前幾棒")
#: scratchpad 檔名含這些字樣者標 ★（第 10 欄與第 13 欄共用辨識）。
STAR_MARKS = ("BRIEF", "RESTART_POINT", "HB_", "_report")
STATUS_LIMIT = 40  # `git status --short` 最多列幾行（其餘只報總數）
WIP_SUFFIX = "-wip-preserved"
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_SCHED_PS = ("[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);"
             "Get-ScheduledTask | Where-Object { $_.TaskName -like 'AutoSDD_*' -or "
             "$_.TaskName -like 'AutoClaude*' } | ForEach-Object { "
             "$i = $_ | Get-ScheduledTaskInfo; \"$($_.TaskName)`t$($i.NextRunTime)\" }")


def default_runner(argv, *, cwd=None, env=None, creationflags=0, wait=True):
    """預設 runner（測試一律注入假的）；失敗不拋，回 `(rc≠0, 錯誤文字, None)`。"""
    try:
        if not wait:
            proc = subprocess.Popen(argv, cwd=cwd, env=env, creationflags=creationflags)
            return 0, "", proc.pid
        done = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=60, check=False,
                              creationflags=creationflags or _NO_WINDOW)
        return done.returncode, done.stdout, None
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, f"{type(exc).__name__}: {exc}", None


def git_lines(runner, repo: Path, *args: str) -> tuple[list[str] | None, str]:
    """跑一條 git：回 `(非空行 | None, 原因)`；rc≠0 一律 None（呼叫端寫「量不到：…」）。"""
    argv = ["git", "-c", "core.quotepath=false", "-C", str(repo), *args]
    rc, out, _ = runner(argv, cwd=str(repo))
    if rc != 0:
        return None, f"git {' '.join(args)} rc={rc}"
    return [ln for ln in str(out).splitlines() if ln.strip()], ""


def wip_tags(runner, repo: Path) -> tuple[list[str] | None, str]:
    """HEAD 上的 `*-wip-preserved` 標籤（〈可重啟點四條件〉第 1 條的保全手法）。"""
    lines, why = git_lines(runner, repo, "tag", "--points-at", "HEAD")
    return (None if lines is None else [t.strip() for t in lines if t.strip().endswith(WIP_SUFFIX)],
            why)


def owner_tags(runner, repo: Path, sid: str, head: str | None) -> tuple[list[str] | None, str]:
    """本 owner session 的保全標籤（WP-SW REQ-CTL-54）：`<sid 前 8 碼>-*` 中以 `-halfwork` 或
    `-wip-preserved` 結尾者，附目標 SHA 前 12 碼；目標不是 HEAD 者標「不在 HEAD」（`git stash create` 的 commit
    不在 HEAD，只活在手寫層時新主控不知道半成品在哪）。`git tag` 失敗 ⇒ `(None, 原因)`。"""  # noqa: E501
    if len(sid) < 8:
        return [], ""
    names, why = git_lines(runner, repo, "tag", "--list", f"{sid[:8]}-*")
    if names is None:
        return None, why
    rows = []
    for name in (n.strip() for n in names):
        if not name.endswith(("-halfwork", WIP_SUFFIX)):
            continue
        sha, _ = git_lines(runner, repo, "rev-parse", f"{name}^{{commit}}")
        full = sha[0] if sha else ""
        rows.append(f"{name} → {full[:12] or '量不到 SHA'}" + ("" if full and full == head else "（不在 HEAD）"))  # noqa: E501
    return rows, ""


def _unknown(why: str) -> str:    return f"量不到：{why}"


def _quote(text: str) -> str:
    """引文逐行加 `> `：真人提示可能含 `## 已驗證` 之類的標題行，不得被當成主控層標題。"""
    return "\n".join(f"> {ln}" for ln in text.splitlines()) or ">"


def _git_sections(runner, repo: Path, sid: str = "") -> tuple[str, str, str]:
    branch, why_b = git_lines(runner, repo, "rev-parse", "--abbrev-ref", "HEAD")
    head, why_h = git_lines(runner, repo, "rev-parse", "HEAD")
    sync, why_s = git_lines(runner, repo, "rev-list", "--left-right", "--count", "@{u}...HEAD")
    parts = [f"- branch：{branch[0] if branch else _unknown(why_b)}",
             f"- HEAD：{head[0] if head else _unknown(why_h)}"]
    behind_ahead = sync[0].split() if sync else []
    parts.append("- 落後／領先上游：" + (f"落後 {behind_ahead[0]}／領先 {behind_ahead[1]}"
                                       if len(behind_ahead) == 2 else _unknown(why_s or "無上游")))
    status, why_t = git_lines(runner, repo, "status", "--short")
    if status is None:
        tree = _unknown(why_t)
    elif not status:
        tree = "（乾淨）"
    else:
        cut = f"（僅列前 {STATUS_LIMIT} 行）" if len(status) > STATUS_LIMIT else ""
        tree = "```\n" + "\n".join(status[:STATUS_LIMIT]) + f"\n```\n共 {len(status)} 行{cut}"
    trees, why_wt = git_lines(runner, repo, "worktree", "list")
    tree += "\n- worktree（`git worktree list`）：" + (
        _unknown(why_wt) if trees is None else "\n" + "\n".join(f"  - {t}" for t in trees))
    tags, why_w = wip_tags(runner, repo)
    own, why_o = owner_tags(runner, repo, sid, head[0] if head else None)
    tag_text = (_unknown(why_w) if tags is None
                else "\n".join(f"- {t}" for t in tags) or "（HEAD 上無）")
    extra = [f"- 本 owner 保全標籤：{_unknown(why_o)}"] if own is None else [
        f"- 本 owner 保全標籤：{t}" for t in own]
    tag_text = "\n".join([tag_text, *extra])
    return "\n".join(parts), tree, tag_text


def _schedule_rows(runner, platform_name: str) -> str:
    """排程與 NextRunTime：憑證是**值**（空值寫「NextRunTime 量不到」，不寫成已排程）。"""
    if platform_name != "win32":
        return _unknown(f"平台 {platform_name} 未實作排程列舉（launchd 無下次時刻，憑證是 rc）")
    rc, out, _ = runner(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _SCHED_PS])
    if rc != 0:
        return _unknown(f"排程查詢 rc={rc}")
    rows = []
    for line in str(out).splitlines():
        name, _, moment = line.partition("\t")
        if name.strip():
            shown = moment.strip() or "NextRunTime 量不到（不可視為已排程）"
            rows.append(f"- {name.strip()}：{shown}")
    return "\n".join(rows) or "（沒有 AutoSDD_／AutoClaude 排程）"


def _quota_text(now: datetime, quota_fn, sid: str = "") -> str:
    """交接包額度欄（QVD §3.5 C14）：首行＝判決行（`--ack` 時一律重算，§4 第 3 點），其後逐軸讀數
    為診斷。縫 `quota_fn(now)->QuotaState`；缺＝單一權威判決取數（`ruling_io`）。"""
    try:
        from . import ruling_io  # noqa: PLC0415 — lazy：只有真的要讀額度時才載入

        snap = ruling_io.current(sid, None, None, now, read_quota=quota_fn)
        state = snap.state
        axes = "\n".join(f"- {a.kind}：{a.pct:g}%（reset {a.resets_at or '量不到'}）"
                         for a in state.axes) or "（無軸）"
        return (f"{snap.ruling.line()}\n（診斷）量測時刻 {state.measured_at}（來源 {state.source}）"
                f"\n{axes}")
    except Exception as exc:  # noqa: BLE001 — 取不到寫「量不到」，不拋
        return _unknown(f"{type(exc).__name__}: {exc}")

def _pad_files(sid: str, temp_root: Path | None) -> tuple[list[Path] | None, str]:
    """該 sid 的 scratchpad 檔案（排序）；`(None, 原因)`＝找不到／讀不動。"""
    root = Path(temp_root) if temp_root is not None else Path(tempfile.gettempdir())
    try:
        pads = sorted(root.glob(f"claude/*/{sid}/scratchpad"))
        files = sorted(p for pad in pads for p in pad.rglob("*") if p.is_file())
    except OSError as exc:
        return None, f"scratchpad 讀不動（{type(exc).__name__}）"
    return (files, "") if pads else (None, f"找不到 {root}/claude/*/{sid}/scratchpad")


def star_files(sid: str, temp_root: Path | None) -> tuple[list[Path] | None, str]:
    """該 sid scratchpad 內的 ★檔（`STAR_MARKS`），最近修改者在前（第 13 欄用）。"""
    files, why = _pad_files(sid, temp_root)
    if files is None:
        return None, why

    def _mtime(path: Path) -> float:
        try:
            return path.stat().st_mtime
        except OSError:
            return 0.0

    return sorted((p for p in files if any(m in p.name for m in STAR_MARKS)),
                  key=_mtime, reverse=True), ""


def _scratchpad_text(sid: str, temp_root: Path | None) -> str:
    files, why = _pad_files(sid, temp_root)
    if files is None:
        return _unknown(why)
    return "\n".join(f"- {'★ ' if any(m in p.name for m in STAR_MARKS) else ''}{p}"
                     for p in files[:60]) or "（scratchpad 內沒有檔案）"


def build_mechanical(session_id: str, transcript: Path | None, *, repo: Path, now: datetime,
                     runner=None, roster_mod=None, quota_fn=None, temp_root: Path | None = None,
                     platform_name: str = "", package: Path | None = None, oi_fn=None,
                     chain_base: Path | None = None) -> str:
    """交接包機械層全文（只含 `### ` 欄位，不含主控層）。`now` 須帶 offset。
    `package` 給了就在「最近真人提示」欄末指向全文 sidecar（該欄只留 3 則摘錄，全文在 sidecar）。
    第 13 欄的交接包目錄＝`chain_base`，缺則取 `package` 所在目錄（W4）；`oi_fn`＝OI 摘要注入縫。"""
    runner = runner or default_runner
    plat = platform_name or sys.platform
    branch_head, tree, tags = _git_sections(runner, repo, session_id)
    humans = transcript_activity.human_prompts(transcript)
    tail = transcript_activity.assistant_tail(transcript)
    agents, why_roster = None, ""
    try:
        if roster_mod is None:
            from . import roster as roster_mod  # noqa: PLC0415 — lazy（Dev-2b 的模組）
        snap = roster_mod.snapshot(session_id)
        roster_text, agents = roster_mod.render_snapshot(snap), snap.get("agents") or []
    except Exception as exc:  # noqa: BLE001
        roster_text = _unknown(f"名冊不可用（{type(exc).__name__}）")
        why_roster = f"名冊不可用（{type(exc).__name__}）"
    model = agentbrief.main_model(transcript) or _unknown("逐字稿無 assistant 記錄或讀不到")
    base = chain_base if chain_base is not None else (package.parent if package else None)
    body = (
        f"- 來源 session：{session_id}\n- 產生時刻：{now.isoformat()}\n"
        f"- {sandbox_scope.PKG_REPO_LABEL}{repo}\n- 主控模型：{model}",
        branch_head, tree, tags,
        ("\n\n".join(_quote(t) for t in humans) or _unknown("逐字稿無真人提示或讀不到"))
        + (f"\n\n全文見 {package.stem}.prompts.md" if package is not None else ""),
        "\n\n".join(_quote(t) for t in tail) or _unknown("逐字稿無 assistant 文字或讀不到"),
        roster_text, _schedule_rows(runner, plat), _quota_text(now, quota_fn, session_id),
        _scratchpad_text(session_id, temp_root),
        str(transcript) if transcript else _unknown("逐字稿路徑未知"),
        agentbrief.column12(agents, session_id, transcript, why=why_roster, oi_fn=oi_fn),
        promptchain.column13(session_id, base, lambda sid: star_files(sid, temp_root)))
    return "\n\n".join(f"### {i} {title}\n{text}"
                       for i, (title, text) in enumerate(zip(MECH_HEADINGS, body), 1))
