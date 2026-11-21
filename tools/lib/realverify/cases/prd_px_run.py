"""prd_px 家族（真引擎＋可程式化 shim，載具 P／X）：RV-PX12／29。

每案都起真 `python -m autoclaude`（沙盒 cwd、沙盒 config／log／checkpoint）；shim 只決定「claude -p 回什麼」
（用量 JSON ⇒ 引擎真的走 TOKEN_HALT／checkpoint／髒污工作樹救援）。步驟輸出是 shim，其餘全部真跑。"""  # noqa: E501

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from ..sandbox import Sandbox
from . import CaseContext
from .prd_px_engine import (
    git_commit_all,
    git_porcelain,
    pct_json,
    run_engine,
    seed_queue,
    write_py_shim,
)
from .prd_px_lib import ev, px

_NW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _force_rm(func, path, _exc) -> None:
    os.chmod(path, stat.S_IWRITE)  # git 物件檔唯讀，Windows 需先解除才刪得掉
    func(path)


def playbook(n: int) -> str:
    steps = "".join(f'  - step_id: "T0{i}"\n    name: "n"\n    prompt: "hi"\n'
                    '    expected_output_regex: "\\\\[DONE\\\\]"\n' for i in range(1, n + 1))
    return f'version: "1.0"\nproject: "rv"\ntasks:\n{steps}'


def halt_script(*lead: float) -> list[dict]:
    """前幾步用量為 `lead`，之後每步都 95%（≥ halt 門檻 90 ⇒ TOKEN_HALT）。"""
    return [{"stdout": pct_json(p)} for p in (*lead, 95)]


def dirty_pre(sb: Sandbox) -> str:
    """基線 commit（`bin/` 以 .git/info/exclude 排除）＋一個 tracked 修改＋一個 untracked 新檔；回基線短 sha。"""  # noqa: E501
    (sb.root / ".git" / "info" / "exclude").write_text("bin/\n", encoding="utf-8")
    (sb.root / "a.txt").write_text("base\n", encoding="utf-8")
    sha = git_commit_all(sb)
    (sb.root / "a.txt").write_text("changed\n", encoding="utf-8")
    (sb.root / "u.txt").write_text("new\n", encoding="utf-8")
    return sha


@px("RV-PX12", "P", ("rescue_patch", "tree_untouched"), refs=("§4.5.9", "§8-8"))
def px12(ctx: CaseContext) -> None:
    """§4.5.9／§8-8：髒污工作樹＋真引擎 TOKEN_HALT ⇒ 救援 patch 存在且 `git apply --check` 通過、
    工作樹 `status --porcelain` 前後相同。步驟輸出為 shim（用量 JSON），救援序列是引擎真跑。"""
    sb = ctx.sandbox(probe_hooks=False)
    state: dict = {}

    def pre(s: Sandbox) -> None:
        dirty_pre(s)
        state["before"] = git_porcelain(s)

    r = run_engine(sb, command=str(write_py_shim(sb, halt_script(10))), playbook=playbook(3), pre=pre)  # noqa: E501
    after = git_porcelain(sb)
    ctx.check("TOKEN_HALT" in r.log, f"引擎應走 TOKEN_HALT：\n{r.text[-700:]}")
    patches = sorted((sb.root / "ckpt").glob("dirty-*.patch"))
    ctx.check(len(patches) == 1 and patches[0].stat().st_size > 0, f"應恰有 1 份非空救援 patch：{patches}")  # noqa: E501
    clone = Path(str(sb.root) + "_clone")
    try:
        subprocess.run(["git", "clone", "-q", str(sb.root), str(clone)], check=True,  # noqa: S603,S607
                       capture_output=True, creationflags=_NW)
        chk = subprocess.run(["git", "apply", "--check", str(patches[0])], cwd=str(clone),  # noqa: S603,S607
                             capture_output=True, text=True, encoding="utf-8", errors="replace",
                             creationflags=_NW)
    finally:
        shutil.rmtree(clone, onerror=_force_rm)
    ctx.check(chk.returncode == 0, f"git apply --check rc={chk.returncode} {chk.stderr[-300:]}")
    body = patches[0].read_text(encoding="utf-8", errors="replace")
    ctx.check("a.txt" in body and "u.txt" in body, "patch 應同時涵蓋 tracked 修改與 untracked 新檔")
    ev(ctx, "rescue_patch", f"{patches[0].name} bytes={patches[0].stat().st_size} "
                            "apply_check_rc=0 covers=a.txt,u.txt")
    ctx.check(after == state["before"], f"工作樹被改動：{state['before']!r} → {after!r}")
    ev(ctx, "tree_untouched", f"porcelain_before=={after!r}".replace("\n", "|"))


def _poison_tmp_names(sb: Sandbox, sha: str) -> int:
    """在 ckpt 內預先放與「未來 40 秒的救援暫存檔名」同名的**目錄**：引擎真的寫檔時 `tmp.open("wb")`
    必拋 OSError ⇒ 逐次失敗，引擎自己的重試迴圈照設定值重試（失敗是真的、重試是引擎真的）。"""
    ck = sb.root / "ckpt"
    ck.mkdir(exist_ok=True)
    now = datetime.now().astimezone()
    n = 0
    for sec in range(-2, 40):
        ts = (now + timedelta(seconds=sec)).strftime("%Y%m%dT%H%M%S%z")
        (ck / f"dirty-agent-{ts}-{sha}.patch.tmp").mkdir(exist_ok=True)
        n += 1
    return n


@px("RV-PX29", "P", ("conflict_policy", "retain_versions", "dirty_retries"),
    refs=("施工圖 A9",))
def px29(ctx: CaseContext) -> None:
    """施工圖 A9：三個 `AUTOCLAUDE_*` 環境鍵設成非預設值，真引擎三次，各自觀察被採用。
    · conflict_policy：checkpoint 內有待整合殘留項，ABORT ⇒ 拒絕啟動並列清單、
      RETRY_WITH_AGENT ⇒ 重排；
    · retain_versions=2：多次 halt 存檔後 checkpoint 版本檔恰 2 份；
    · dirty_retries=2：救援寫檔被真的擋住（同名目錄）⇒ 引擎記 attempts=3（1＋2 次重試）。"""
    # ① conflict_policy
    sb = ctx.sandbox(probe_hooks=False)
    cmd = str(write_py_shim(sb, halt_script(10)))
    run_engine(sb, command=cmd, playbook=playbook(3))
    seed_queue(sb, [{"branch": "feat/rv", "status": "PENDING_VERIFY"}])
    abort = run_engine(sb, command=cmd, playbook=playbook(3), env_extra={"AUTOCLAUDE_CONFLICT_POLICY": "ABORT"})  # noqa: E501
    ctx.check(abort.rc != 0 and "ABORT：feat/rv" in abort.text and "CONFLICT_POLICY=ABORT" in abort.text,  # noqa: E501
              f"ABORT 應拒絕啟動並列清單：rc={abort.rc}\n{abort.text[-700:]}")
    retry = run_engine(sb, command=cmd, playbook=playbook(3),
                       env_extra={"AUTOCLAUDE_CONFLICT_POLICY": "RETRY_WITH_AGENT"})
    ctx.check("重排：feat/rv" in retry.text, f"RETRY_WITH_AGENT 應重排：\n{retry.text[-700:]}")
    seed_queue(sb, [{"branch": "feat/rv", "status": "PENDING_VERIFY"}])  # 上一輪又 halt，重置排程與佇列  # noqa: E501
    default = run_engine(sb, command=cmd, playbook=playbook(3))
    ctx.check("只登記不重排（CONFLICT_POLICY=HUMAN_REVIEW）" in default.text, "未設時應為出廠 HUMAN_REVIEW")  # noqa: E501
    ev(ctx, "conflict_policy", f"ABORT⇒rc={abort.rc}+清單；RETRY_WITH_AGENT⇒重排；未設⇒HUMAN_REVIEW只登記")  # noqa: E501
    # ② retain_versions
    sb2 = ctx.sandbox(probe_hooks=False)
    cmd2 = str(write_py_shim(sb2, halt_script(10)))
    for _ in range(3):
        run_engine(sb2, command=cmd2, playbook=playbook(3), env_extra={"AUTOCLAUDE_STATE_RETAIN_VERSIONS": "2"})  # noqa: E501
        seed_queue(sb2, [], {"AUTOCLAUDE_STATE_RETAIN_VERSIONS": "2"})  # 清掉 scheduled_resume_at，下一輪才不會等喚醒時刻  # noqa: E501
    vers = sorted(p.name for p in (sb2.root / "ckpt").glob("pb.checkpoint.json.v*"))
    ctx.check(len(vers) == 2, f"RETAIN=2 應恰 2 份版本檔：{vers}")
    ev(ctx, "retain_versions", f"versions={vers} count=2（引擎 halt 存檔 ≥6 次）")
    # ③ dirty_retries
    sb3 = ctx.sandbox(probe_hooks=False)

    def pre(s: Sandbox) -> None:
        sha = dirty_pre(s)
        _poison_tmp_names(s, sha)

    r3 = run_engine(sb3, command=str(write_py_shim(sb3, halt_script(10))), playbook=playbook(3), pre=pre,  # noqa: E501
                    env_extra={"AUTOCLAUDE_DIRTY_SAVE_RETRIES": "2"})
    m = re.search(r"DIRTY_UNSAVED：髒污工作樹存檔失敗（base=\w+，attempts=(\d+)）", r3.text)
    ctx.check(bool(m) and m.group(1) == "3", f"retries=2 應 attempts=3：\n{r3.text[-900:]}")
    ev(ctx, "dirty_retries", f"retries_env=2 ⇒ engine attempts={m.group(1)}（每次皆被同名目錄擋住的真失敗）")  # noqa: E501
