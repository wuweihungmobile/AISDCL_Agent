# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""sideeffect 家族（二）：副作用帳／sweep／快照的真機 E2E——RV-SE02（中途 taskkill）、RV-SE12（legacy 只列）、
RV-SE13（刻意外洩探針）、RV-SE15（F5 授權閘）、RV-SE18（拒跑出口）。

載具：父案例背景起子 runner（`RV-SE-SEED`／`RV-SE-LEAK`／`RV-SE-LOCK`，真行程）建好受害者後，由父案例
`taskkill /F /PID`（不帶 /T）殺掉它，再以真 `realverify.py run`／`sweep`／`snapshot` 與真 `sessionctl.py status`
驗收：L2 租約帳與發現式掃描真的把「主人死了留下的排程／行程／目錄」撤乾淨，且拒跑出口與外洩偵測真的會響。
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from ..interactive import NotTrusted
from ..sandbox import real_autosdd
from . import CaseContext, case
from .sessionctl_park import PY, get_task
from .sideeffect_lib import (
    control_dir,
    hash_tree,
    kill_pid,
    kills_runners,
    ledger_rows,
    new_box,
    pid_alive,
    plain_env,
    rmtree,
    run,
    spawn_runner,
    sweep_clean,
    wait_ready,
)

REPO_TOOLS = Path(__file__).resolve().parents[3]
_RV = [PY, str(REPO_TOOLS / "realverify.py")]


def _wait_dead(pid: int, seconds: float = 10.0) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if not pid_alive(pid):
            return True
        time.sleep(0.5)
    return not pid_alive(pid)


def _realverify(*args: str, env: dict | None = None, timeout: int = 600):
    return run([*_RV, *args], cwd=REPO_TOOLS.parent, env=env or plain_env(), timeout=timeout)


@case("RV-SE02", "sideeffect", refs=("E2E-SE-02",), sched=True)
@kills_runners
def rv_se02(ctx: CaseContext) -> None:
    """背景 `run --case RV-SE-SEED` 建受害者後被 `taskkill /F`：三支工作（帳上 RV 工作、產品 park 工作、未記帳的直登工作）、
    沙盒根、睡眠行程都還在；`sessionctl status` 印 `realverify 孤兒 n=1` 且**不撤**；再跑 `RV-SE-NOOP`：開頭列出 revoked 項，
    之後三支工作／沙盒根／睡眠行程／projects slug 全撤、帳檔 closed；兩次 `sweep` 皆 clean。"""
    info = wait_ready(ctx, spawn_runner(ctx, "RV-SE-SEED", {}))
    kill_pid(int(info["pid"]))
    ctx.check(_wait_dead(int(info["pid"])), "SEED 主人行程殺不掉")
    tasks = [info["rv_task"], info["park_task"], info["unaccounted_task"]]
    for t in tasks:
        ctx.check(get_task(t) is not None, f"kill 後工作 {t} 應仍在（孤兒尚未被撤）")
    ctx.check(Path(info["root"]).is_dir() and pid_alive(int(info["sleeper_pid"])), "kill 後沙盒根與睡眠行程應仍在")
    st = run([PY, str(REPO_TOOLS / "sessionctl.py"), "status"], cwd=REPO_TOOLS.parent, env=plain_env(), timeout=180)
    last = [ln for ln in st.stdout.splitlines() if ln.strip()][-1]
    ctx.check("realverify 孤兒 n=1" in last, f"status 末行應含 `realverify 孤兒 n=1`：{last!r}")
    for t in tasks:
        ctx.check(get_task(t) is not None, f"status 不得順手撤銷孤兒（MU-SE-14），但工作 {t} 不見了")
    r = _realverify("run", "--case", "RV-SE-NOOP")
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    ctx.check(lines and lines[0].startswith("↩"), f"NOOP 輸出開頭應列出 revoked 項（↩ …）：{lines[:3]}")
    ctx.check(r.returncode == 0 and "REALVERIFY_VERDICT=pass" in r.stdout, f"RV-SE-NOOP 應 PASS：rc={r.returncode} {r.stdout[-300:]}")
    ctx.evidence("NOOP 開頭：" + " | ".join(ln[:70] for ln in lines[:4]))
    for t in tasks:
        ctx.check(get_task(t) is None, f"NOOP 之後工作 {t} 應已撤")
    ctx.check(not Path(info["root"]).exists(), "NOOP 之後沙盒根應已不存在")
    ctx.check(_wait_dead(int(info["sleeper_pid"])), "NOOP 之後睡眠行程應已被撤（命令列含沙盒 sid ⇒ 驗得到身分才砍）")
    ctx.check(not Path(info["slug_dir"]).exists(), f"NOOP 之後 projects 沙盒 slug 應已不存在：{info['slug_dir']}")
    rows = ledger_rows(info["run_id"])
    ctx.check(bool(rows) and rows[-1].get("kind") == "run" and rows[-1].get("state") == "closed", f"帳檔應 closed：{rows[-1:] }")
    for i in (1, 2):
        ctx.check(sweep_clean(ctx) == "SWEEP_VERDICT=clean", f"第 {i} 次 sweep 應為 clean")
    ctx.evidence(f"kill→status n=1→NOOP 撤 {len(lines)} 行→三工作／根／睡眠行程／slug 全無→帳 closed→sweep×2 clean")


@case("RV-SE13", "sideeffect", refs=("E2E-SE-13",), sched=True)
@kills_runners
def rv_se13(ctx: CaseContext) -> None:
    """背景 `run --case RV-SE-LEAK`（刻意繞過圍籬：真 `~/.autosdd/handoff/<沙盒 sid>.probe`＋Action 含沙盒根的未記帳工作）：
    該案例 `fail`、detail 首行 `SIDE-EFFECT LEAK` 且列出兩項、批次 `reason=leak`；前後 `snapshot --diff --tokens` 也列出兩項；
    收尾刪探針檔、`sweep` 撤該工作後 `clean`。"""
    d = control_dir(ctx)
    before, after = d / "before.json", d / "after.json"
    r0 = _realverify("snapshot", "--out", str(before))
    ctx.check(r0.returncode == 0, f"snapshot --out rc={r0.returncode} {r0.stderr[-200:]}")
    runner = spawn_runner(ctx, "RV-SE-LEAK", {})
    runner.proc.wait(timeout=420)
    out = runner.out_path.read_text(encoding="utf-8", errors="replace")
    info = json.loads(runner.ready_path.read_text(encoding="utf-8"))
    ctx.extra_tokens += [info["sid"], info["root"], info["run_id"]]
    probe, task = Path(info["probe"]), info["task"]
    try:
        r1 = _realverify("snapshot", "--out", str(after))
        ctx.check(r1.returncode == 0, f"snapshot --out(after) rc={r1.returncode}")
        ctx.check(runner.proc.returncode == 1, f"RV-SE-LEAK 應 fail（rc 1），實得 rc={runner.proc.returncode}：{out[-400:]}")
        ctx.check("[FAIL] RV-SE-LEAK SIDE-EFFECT LEAK" in out, f"detail 首行應為 SIDE-EFFECT LEAK：{out[-400:]}")
        leaks = [ln for ln in out.splitlines() if "note: LEAK" in ln]
        ctx.check(len(leaks) == 2 and any(".probe" in ln for ln in leaks) and any(task in ln for ln in leaks), f"應列出兩項（探針檔與未記帳工作）：{leaks}")
        ctx.check("reason=leak" in out, f"批次末行應 reason=leak：{out[-300:]}")
        toks = d / "tokens.txt"
        toks.write_text("\n".join([info["sid"], info["root"], info["run_id"]]) + "\n", encoding="utf-8", newline="\n")
        r2 = _realverify("snapshot", "--diff", str(before), str(after), "--tokens", str(toks))
        shown = [ln for ln in r2.stdout.splitlines() if ".probe" in ln or task in ln]
        ctx.check(r2.returncode == 0 and len(shown) == 2, f"snapshot --diff 也應列出兩項：rc={r2.returncode} {r2.stdout[-400:]}")
        ctx.evidence("兩項外洩：" + " | ".join(ln[:90] for ln in leaks))
    finally:
        probe.unlink(missing_ok=True)
    first = sweep_clean(ctx)
    ctx.check(get_task(task) is None, f"sweep（{first}）應撤掉外洩探針的工作")
    ctx.check(sweep_clean(ctx) == "SWEEP_VERDICT=clean", "收尾 sweep 應 clean")


@case("RV-SE18", "sideeffect", refs=("E2E-SE-18",), sched=True)
@kills_runners
def rv_se18(ctx: CaseContext) -> None:
    """拒跑出口：RV-SE-LOCK 留下撤不掉的孤兒（行程 P1 驗不到身分、cwd 卡住沙盒根）⇒ 以居所＝H 的環境跑 `RV-SE-NOOP` 拒跑
    （rc 2、`reason=orphans`、H 的 handback 有檔且列 ident 與 `--abandon` 指令、H 的通知佇列無新增、P1 未被砍）；
    `sweep --abandon` 後帳 closed 且不動行程與檔；第二次 NOOP PASS；殺 P1 後 sweep 清掉 X 根；全程真 handback 檔名集合與
    真通知佇列位元組長度不變。"""
    h, _exe = new_box(ctx, tools=False)
    henv = h.env()
    real_hb, queue = real_autosdd("handback"), real_autosdd("traces") / "autosdd_notify_queue.json"
    hb0 = sorted(p.name for p in real_hb.iterdir()) if real_hb.is_dir() else []
    q0 = queue.stat().st_size if queue.is_file() else None
    info = wait_ready(ctx, spawn_runner(ctx, "RV-SE-LOCK", {}))
    kill_pid(int(info["pid"]))
    ctx.check(_wait_dead(int(info["pid"])), "LOCK 主人行程殺不掉")
    p1, x_root = int(info["p1_pid"]), Path(info["root"])
    r1 = _realverify("run", "--case", "RV-SE-NOOP", env=henv)
    ctx.check(r1.returncode == 2 and "reason=orphans" in r1.stdout, f"第一次 NOOP 應拒跑（rc 2、reason=orphans）：rc={r1.returncode} {r1.stdout[-400:]}")
    files = sorted((h.home / "handback").glob("realverify_orphans_*.md"))
    text = files[0].read_text(encoding="utf-8") if files else ""
    ctx.check(bool(files) and "--abandon" in text and str(x_root) in text, f"H 的 handback 應有 realverify_orphans_*.md 且列 ident 與 --abandon 指令：{files} {text[:300]}")
    ctx.check(not (h.home / "traces" / "autosdd_notify_queue.json").exists(), "H 的通知佇列不該有新增（通知關）")
    ctx.check(pid_alive(p1), "P1 驗不到身分，不得被砍（unverified）")
    r2 = _realverify("sweep", "--abandon", info["run_id"], "--why", "E2E-SE-18 驗人工出口", env=henv)
    ctx.check(r2.returncode == 0 and "SWEEP_ABANDON" in r2.stdout, f"--abandon rc={r2.returncode} {r2.stdout[-300:]}")
    ctx.check(pid_alive(p1) and x_root.is_dir(), "abandon 不動行程與檔：P1 與 X 根都應仍在")
    rows = ledger_rows(info["run_id"])
    ctx.check(rows[-1].get("kind") == "run" and rows[-1].get("state") == "closed", f"abandon 後帳應 closed：{rows[-1]}")
    r3 = _realverify("run", "--case", "RV-SE-NOOP", env=henv)
    ctx.check(r3.returncode == 0 and "REALVERIFY_VERDICT=pass" in r3.stdout, f"abandon 後第二次 NOOP 應 PASS：rc={r3.returncode} {r3.stdout[-400:]}")
    note_seen = "abandoned" in r3.stdout
    kill_pid(p1)
    ctx.check(_wait_dead(p1), "P1 殺不掉")
    first = _realverify("sweep", env=henv).stdout.strip().splitlines()[-1]
    gone = not x_root.exists()
    rmtree(x_root)  # 載具自己的暫存：無論產品是否刪掉，收尾一定清乾淨（下面再據實判）
    ctx.evidence(f"abandon 後 NOOP 的 note 行出現={note_seen}；殺 P1 後 sweep：{first}；X 根被產品刪除={gone}")
    hb1 =sorted(p.name for p in real_hb.iterdir()) if real_hb.is_dir() else []
    q1 = queue.stat().st_size if queue.is_file() else None
    ctx.check(hb1 == hb0, f"全程真 handback 檔名集合應不變：新增 {sorted(set(hb1) - set(hb0))}")
    ctx.check(q1 == q0, f"全程真通知佇列位元組長度應不變：{q0}→{q1}")
    ctx.check(gone, f"殺 P1 後 sweep 應刪除 X 根、abandon 後第二次 NOOP 應只記 note（TCS E2E-SE-18）：note={note_seen} sweep={first}；根因見報告（首次拒跑的 rmtree 已清空 X 內容含身分檔，空目錄在探索掃描被判 live，abandoned 之下又只記 note）")
    ctx.check(sweep_clean(ctx) == "SWEEP_VERDICT=clean", "收尾 sweep 應 clean")


@case("RV-SE12", "sideeffect", refs=("E2E-SE-12",))
def rv_se12(ctx: CaseContext) -> None:
    """真家目錄跑 `sweep --legacy`（不帶 --apply）：列出 DES §9 仍存在的 X 項、rc 0、`~/.autosdd` 全檔雜湊清單前後相同
    （略過共用只追加帳 `traces/*.jsonl`、租約帳與 rv_host——主控並行寫入的活檔，且正是 X6 的永不處置對象）、輸出不含 X6／X8 為刪除對象。"""
    root = real_autosdd()
    skip = ("traces", "realverify_leases", "rv_host", "realverify_kept")
    before = hash_tree(root, skip)
    r = _realverify("sweep", "--legacy")
    after = hash_tree(root, skip)
    ctx.check(r.returncode == 0, f"sweep --legacy rc={r.returncode} {r.stderr[-200:]}")
    ctx.check("SWEEP_LEGACY listed" in r.stdout and "未加 --apply" in r.stdout, f"應只列、不動：{r.stdout[-300:]}")
    listed = [ln for ln in r.stdout.splitlines() if ln.startswith("LEGACY ")]
    ctx.check(not any("claude.json" in ln or ".jsonl" in ln for ln in listed), f"不得把 X6／X8 列為處置對象：{listed}")
    removed = sorted(set(before) - set(after))
    ctx.check(not removed, f"`~/.autosdd` 不得有任何檔被刪（只列不動）：{removed[:5]}")
    legacy_rel = {Path(ln.split(" ", 2)[2]).resolve().relative_to(root.resolve()).as_posix() for ln in listed
                  if Path(ln.split(" ", 2)[2]).resolve().is_relative_to(root.resolve())}
    touched = sorted(k for k in legacy_rel if before.get(k) != after.get(k))
    ctx.check(not touched, f"legacy 列出的檔前後必須逐位元相同：{touched[:5]}")
    # 誠實劃界：主控／他視窗的 hook 並行寫 `~/.autosdd`（本 session 自己的 context_feed／handoff 檢查檔就在其中），
    # 「全檔雜湊逐位元相同」在活機上結構上不可能；改判「無刪除、legacy 項不動」，其餘並行寫入只入證據。
    changed = sorted(k for k in set(before) & set(after) if before[k] != after[k])
    ctx.evidence(f"legacy 列出 {len(listed)} 項；{len(before)} 檔無刪除、legacy 項不動（略過 {', '.join(skip)}）；並行寫入 {len(changed)} 檔：{changed[:3]}")


@case("RV-SE15", "sideeffect", refs=("E2E-SE-15",))
def rv_se15(ctx: CaseContext) -> None:
    """真 `Sandbox.create` 後呼叫 `grant_side_effects(window=True)`：拋 `NotTrusted`、身分檔 `allow_until` 仍 null、
    `window` 仍為假；不需要宿主信任（一般沙盒不是 worktree 沙盒，根本沒有信任確認）。"""
    sb = ctx.sandbox(probe_hooks=False)
    try:
        ctx.grant_side_effects(sb, minutes=10, window=True)
    except NotTrusted:
        pass
    else:
        raise AssertionError("一般沙盒 window=True 應拋 NotTrusted（MU-SE-13：不呼叫 assert_trusted 就會授權成功）")
    ident = json.loads((sb.home / ".autosdd_sandbox.json").read_text(encoding="utf-8"))
    ctx.check(ident["allow_until"] is None and ident["window"] is False, f"身分檔不得被授權：{ident}")
    ctx.evidence("NotTrusted；身分檔 allow_until=null window=false")
