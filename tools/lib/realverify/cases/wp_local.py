# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""workprogress 家族（A6e，本機純行程案例）：RV-IL1（陳舊 index.lock）、RV-BC1（啟動自檢不變式）、
RV-SC3（事件名常數）。全部真行程、真 git、真逐字稿；證據鍵走 `ev()`。"""  # noqa: E501

from __future__ import annotations

import json
import re
import subprocess
import sys
import time

from ..driver import EnvMissing
from ..sandbox import REPO, kill_tree
from . import CaseContext, case
from .prd_px_lib import ev
from .sessionctl_park import PY, run

NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _git_busy() -> bool:
    if sys.platform != "win32":
        return False  # tasklist 只在 Windows 存在；其他平台沒有 git.exe 行程這條判準（RV-IL1 在非 Windows 由 run 端另判）
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq git.exe", "/NH", "/FO", "CSV"],  # noqa: S603,S607
                         capture_output=True, encoding="utf-8", errors="replace", timeout=15, creationflags=NOWIN)
    return "git.exe" in (out.stdout or "").lower()


_IL_DRIVER = r'''
import json, sys, os
from datetime import datetime, timezone
sys.path.insert(0, os.path.join(sys.argv[1], "tools", "lib"))
sys.path.insert(0, os.path.join(sys.argv[1], "tools"))
from relay_machine import stale_index_lock
from pathlib import Path
r = stale_index_lock(Path(sys.argv[2]), datetime.now(timezone.utc).astimezone())
print("RESULT=" + json.dumps(r, ensure_ascii=False))
'''


def _il_call(sb) -> dict | None:
    p = sb.write_file("il_driver.py", _IL_DRIVER)
    out = run([PY, str(p), str(REPO), str(sb.root)], cwd=sb.root, env=sb.env(), timeout=60)
    m = re.search(r"^RESULT=(.*)$", out.stdout, re.M)
    if out.returncode != 0 or not m:
        raise AssertionError(f"stale_index_lock 子行程失敗 rc={out.returncode}\n{out.stdout[-400:]}{out.stderr[-400:]}")
    return json.loads(m.group(1))


def _make_lock(sb, age_s: int):
    import os
    lock = sb.root / ".git" / "index.lock"
    lock.write_text("", encoding="utf-8")
    old = time.time() - age_s
    os.utime(lock, (old, old))
    return lock


@case("RV-IL1", "workprogress", refs=("E2E-WP-12", "REQ-WP-47", "§8-3"))
def rv_il1(ctx: CaseContext) -> None:
    """沙盒真 git repo 造 `.git/index.lock`、mtime 回撥 700 秒，真跑 `relay_machine.stale_index_lock`
    （預設 `_git_running`＝Windows `tasklist` 分支）：無 git 行程 ⇒ 改名 `index.lock.stale-*`（removed）；
    另起真 `git` 行程佔住 ⇒ kept。機器上別處的 git.exe 會讓「無 git」變體判不出，故重試至乾淨為止，
    始終不乾淨＝環境忙碌（rc 2，不算綠）。"""
    sb = ctx.sandbox(probe_hooks=False)
    # 變體一：鎖齡 ≤ 600 ⇒ None（不動）
    young = _make_lock(sb, 100)
    ctx.check(_il_call(sb) is None and young.exists(), "鎖齡 100 秒不該被處置")
    young.unlink()
    # 變體二：有真 git 行程 ⇒ kept（git hash-object --stdin 讀 stdin 不返回）
    lock = _make_lock(sb, 700)
    holder = subprocess.Popen(["git", "hash-object", "--stdin"], cwd=str(sb.root), stdin=subprocess.PIPE,  # noqa: S603,S607
                              stdout=subprocess.PIPE, creationflags=NOWIN)
    sb.procs.append(holder)
    try:
        time.sleep(1.0)
        ctx.check(holder.poll() is None, "佔鎖用的真 git 行程應仍活著")
        kept = _il_call(sb)
    finally:
        kill_tree(holder)  # git.exe 外殼會再生真正的 mingw64 git：連子孫一起砍
        holder.wait(timeout=10)
        if holder.stdin:
            holder.stdin.close()
        holder.stdout.close()
    for _ in range(20):  # 等佔鎖者真的退出再進入「無 git」變體
        if not _git_busy():
            break
        time.sleep(1)
    ctx.check(kept is not None and kept["action"] == "kept" and lock.exists(), f"有 git 行程應 kept：{kept}")
    ev(ctx, "kept_with_git", f"action=kept reason={kept['reason']} age={kept['age_seconds']}")
    # 變體三：無 git 行程 ⇒ removed（改名可逆）；機器忙碌則重試
    res = None
    tried = 0
    for _ in range(30):
        if not _git_busy():
            tried += 1
            res = _il_call(sb)
            if res and res["action"] == "removed":
                break
            if res and res["action"] == "kept" and "有 git 行程" in res["reason"]:
                continue  # 判定當下別處剛好有 git：重試
            break
        time.sleep(2)
    if not tried or (res and res["action"] == "kept" and "有 git 行程" in res["reason"]):
        raise EnvMissing("機器上持續有別的 git.exe，無法造出「無 git 行程」前提（環境忙碌，非綠）")
    if not res or res["action"] != "removed":
        raise AssertionError(f"無 git 行程應 removed：{res}")
    aside = list((sb.root / ".git").glob("index.lock.stale-*"))
    ctx.check(len(aside) == 1 and not lock.exists(), f"應改名成 index.lock.stale-*（不 unlink）：{aside}")
    ev(ctx, "removed_no_git", f"action=removed moved_to={aside[0].name}")


_BC_DRIVER = r'''
import json, os, subprocess, sys
from pathlib import Path
from autoclaude.execution import boot_self_check as B
from autoclaude.core.ports.state_repository import CheckpointCorruptError
sb = Path(sys.argv[1])
out = {}
def rep(name, r):
    out[name] = {"ok": r.ok, "problems": list(r.problems), "lines": list(r.lines), "dry_run": r.dry_run}
good_cli = lambda argv: (0, "9.9.9 (Claude Code)")
rep("inv8_bypass_no_flag", B.boot_self_check(permission_mode="bypassPermissions", cli_runner=good_cli, environ={}))
rep("inv8_flag_no_container", B.boot_self_check(cli_runner=good_cli, environ={"ALLOW_PERMISSION_BYPASS": "true"}, isolation=B.IsolationEvidence()))
rep("inv9_not_ignored", B.boot_self_check(cli_runner=good_cli, environ={}, repo_root=sb, ignored_dirs=(".autoclaude",)))
(sb / ".gitignore").write_text(".autoclaude/\n", encoding="utf-8")
rep("inv9_ignored", B.boot_self_check(cli_runner=good_cli, environ={}, repo_root=sb, ignored_dirs=(".autoclaude",)))
class Corrupt:
    def load_latest_by_playbook(self, pid): raise CheckpointCorruptError("rv 壞檔")
rep("inv11_unreadable", B.boot_self_check(repo=Corrupt(), playbook_id="p", cli_runner=good_cli, environ={}))
class Cp: integration_queue = [{"status": "WAT", "branch": "b"}]
class Unk:
    def load_latest_by_playbook(self, pid): return Cp()
rep("inv11_unknown_status", B.boot_self_check(repo=Unk(), playbook_id="p", cli_runner=good_cli, environ={}))
rep("inv11_bad_policy", B.boot_self_check(conflict_policy="NOPE", cli_runner=good_cli, environ={}))
rep("inv12_cli_unreadable", B.boot_self_check(cli_runner=lambda a: (1, ""), environ={}))
rep("inv12_cli_real", B.boot_self_check(environ={}))
rep("inv13_space", B.boot_self_check(cli_runner=good_cli, environ={}, space_target=sb, estimate_bytes=10**18))
print("RESULT=" + json.dumps(out, ensure_ascii=False))
'''


@case("RV-BC1", "workprogress", refs=("E2E-WP-64", "REQ-WP-94", "§6.1"))
def rv_bc1(ctx: CaseContext) -> None:
    """真行程（根層 .venv、cwd＝AutoClaude）跑 `boot_self_check`，逐條斷言已機械化的不變式 8／9／11／12／13
    的判定輸出（含正反兩面）；不變式 5、10 屬量測值／環境探測的已知邊界，在證據標為邊界、不判綠。"""
    sb = ctx.sandbox(probe_hooks=False)
    p = sb.write_file("bc_driver.py", _BC_DRIVER)
    py = str(REPO / ".venv" / "Scripts" / "python.exe")
    out = run([py, str(p), str(sb.root)], cwd=REPO / "AutoClaude", env=sb.env(), timeout=180)
    m = re.search(r"^RESULT=(.*)$", out.stdout, re.M)
    ctx.check(out.returncode == 0 and bool(m), f"driver rc={out.returncode}\n{out.stdout[-500:]}{out.stderr[-600:]}")
    d = json.loads(m.group(1))

    def probs(k: str) -> str:
        return " | ".join(d[k]["problems"])

    ctx.check(not d["inv8_bypass_no_flag"]["ok"] and "ALLOW_PERMISSION_BYPASS" in probs("inv8_bypass_no_flag"), f"不變式 8（要求 bypass 無旗標）應拒絕：{d['inv8_bypass_no_flag']}")
    ctx.check(not d["inv8_flag_no_container"]["ok"] and "未偵測到容器" in probs("inv8_flag_no_container"), "不變式 8（旗標真但無容器）應拒絕")
    ev(ctx, "inv8", "bypass 無旗標⇒拒絕；旗標真無容器⇒拒絕")
    ctx.check(not d["inv9_not_ignored"]["ok"] and ".gitignore" in probs("inv9_not_ignored"), f"不變式 9 未 ignore 應拒絕：{d['inv9_not_ignored']}")
    ctx.check(d["inv9_ignored"]["ok"] and any("已在 .gitignore" in x for x in d["inv9_ignored"]["lines"]), "不變式 9 已 ignore 應通過")
    ev(ctx, "inv9", "未 ignore⇒問題；補 .gitignore 後⇒通過")
    ctx.check("佇列狀態不明" in " ".join(d["inv11_unreadable"]["lines"]), "讀不出佇列必須印「狀態不明」不得印 0 筆")
    ctx.check("佇列狀態不明" in " ".join(d["inv11_unknown_status"]["lines"]) and "未知 status" in " ".join(d["inv11_unknown_status"]["lines"]), "未知 status 視為讀不出來")
    ctx.check(not d["inv11_bad_policy"]["ok"] and "CONFLICT_POLICY" in probs("inv11_bad_policy"), "非法 CONFLICT_POLICY 應報 problem")
    ev(ctx, "inv11", "讀不出⇒狀態不明；未知 status⇒狀態不明；非法 policy⇒problem")
    ctx.check(d["inv12_cli_unreadable"]["dry_run"] and d["inv12_cli_unreadable"]["ok"], "CLI 版本讀不到⇒DRY_RUN 且不阻止啟動")
    real = d["inv12_cli_real"]
    ctx.check(real["ok"] and any("CLI" in x for x in real["lines"]), f"真 claude --version 應有 CLI 判定行：{real['lines']}")
    ev(ctx, "inv12", f"版本不可讀⇒DRY_RUN 不阻止；真 CLI 判定行={[x for x in real['lines'] if 'CLI' in x][0][:60]}")
    ctx.check(not d["inv13_space"]["ok"] and "可用空間不足" in probs("inv13_space"), "空間不足應 loud 並成 problem")
    ev(ctx, "inv13", "預估 10^18 位元組⇒可用空間不足 problem")
    ev(ctx, "boundary_inv5_inv10", "不變式 5（量測值 median）、10（遙測／防休眠來源探測）屬已知邊界：本案不判綠，由 PRD §6.1 邊界註記承接")  # noqa: E501


@case("RV-SC3", "workprogress", refs=("E2E-WP-65", "REQ-WP-95", "REQ-SS-21"))
def rv_sc3(ctx: CaseContext) -> None:
    """對本機真逐字稿真跑 `waste_census --switch-metrics`：輸出「機制自身痕跡」的事件名集合＝sessionctl 程式常數
    （keepwarm／longwait 兩家各自的常數）集合，且不含 `hold_set`（軟線／hold 依掌舵者裁決不實作）。"""
    sb = ctx.sandbox(probe_hooks=False)
    r = run([PY, str(REPO / "tools" / "probe" / "waste_census.py"), "--since-days", "14", "--switch-metrics"],
            cwd=sb.root, env=sb.env(), timeout=240)
    ctx.check(r.returncode == 0, f"rc={r.returncode} {r.stderr[-300:]}")
    m = re.search(r"機制自身痕跡：(\{.*?\})", r.stdout)
    ctx.check(bool(m), f"輸出缺「機制自身痕跡」：\n{r.stdout[-500:]}")
    names = set(re.findall(r"'([a-z_]+)':", m.group(1)))
    probe = (
        "import sys,json; sys.path.insert(0, sys.argv[1]+'/tools');"
        "from lib.sessionctl import keepwarm, longwait;"
        "print('C='+json.dumps(sorted([keepwarm.EV_VERDICT,keepwarm.EV_STOP_BLOCK,keepwarm.EV_QUOTA_LATCHED,longwait.EV_BLOCK])))")
    c = run([PY, "-c", probe, str(REPO)], cwd=sb.root, env=sb.env(), timeout=60)
    cm = re.search(r"^C=(.*)$", c.stdout, re.M)
    ctx.check(c.returncode == 0 and bool(cm), f"讀程式常數失敗：{c.stderr[-300:]}")
    consts = set(json.loads(cm.group(1)))
    ctx.check(names == consts, f"事件名集合應＝程式常數：輸出={sorted(names)} 常數={sorted(consts)}")
    ctx.check("hold_set" not in r.stdout and "hold_set" not in consts, "不得出現 hold_set")
    ev(ctx, "event_set_equal", f"{sorted(names)}")
    ev(ctx, "no_hold_set", "輸出與常數皆無 hold_set")
