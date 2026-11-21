"""prd_px 家族（checkpoint 寫入韌性，載具 P＋K）：RV-PX15／42。

PX15：真產品 `FileStateRepository` 在子行程裡連續存檔、以 `taskkill /F` 在隨機時刻結束它（寫入各階段
都有機會被打斷）；另對三種撕裂形態（半截主檔／空主檔／tmp 殘檔）逐一驗證新行程拒用撕裂版、退回上一份
checksum 正確版本。PX42：真引擎 halt ⇒ checkpoint 凍結 ≤5 s（外部量）、撕裂後回上一份有效版、
resumed 窗後 `resume_cost` 落帳（真 `claude -p`）。"""

from __future__ import annotations

import json
import random
import subprocess
import sys
import time

from ..sandbox import REPO
from . import CaseContext
from .autoresume import _find_transcript, _first_assistant_midpoint, _run_py
from .prd_px_engine import run_engine, shim_calls, write_py_shim
from .prd_px_lib import ev, px
from .prd_px_run import halt_script, playbook

_NW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_AC = str(REPO / "AutoClaude")
_PY = str(REPO / ".venv" / "Scripts" / "python.exe")

_PRE = (
    "import sys, json, logging\nsys.path.insert(0, r'{ac}')\nlogging.basicConfig(stream=sys.stderr, level=logging.INFO)\n"  # noqa: E501
    "import autoclaude.infra.repositories.file_state_repository as m\n"
    "import autoclaude.infra.repositories.factory as fa\n"
    "R, PID = m.FileStateRepository(r'{ck}'), fa.canonical_playbook_id('pb.yaml', mode='yaml_only')\n"  # noqa: E501
)
_SAVE_LOOP = _PRE + (
    "i = 0\nwhile True:\n    i += 1\n"
    "    R.save_checkpoint(PID, m.PlaybookCheckpoint(playbook_path='pb.yaml', step_idx=i, step_id=f'T{{i}}', total_steps=9999))\n"  # noqa: E501
    "    if i == 2:\n        print('READY', flush=True)\n"
)
_LOAD = _PRE + (
    "try:\n    cp = R.load_latest_by_playbook(PID)\n"
    "    print(json.dumps({{'ok': True, 'step_idx': None if cp is None else cp.step_idx}}))\n"
    "except Exception as e:\n    print(json.dumps({{'ok': False, 'err': type(e).__name__}}))\n"
)


def _py(code: str, ck, **kw) -> subprocess.CompletedProcess:
    return subprocess.run([_PY, "-c", code.format(ac=_AC, ck=ck)], capture_output=True, text=True,  # noqa: S603
                          encoding="utf-8", errors="replace", creationflags=_NW, timeout=60, **kw)


def _load(ck) -> tuple[dict, str]:
    r = _py(_LOAD, ck)
    return json.loads(r.stdout.strip().splitlines()[-1]), r.stderr


def _seed_two(ck) -> None:
    code = _PRE + ("for i in (1, 2):\n    R.save_checkpoint(PID, m.PlaybookCheckpoint("
                   "playbook_path='pb.yaml', step_idx=i, step_id=f'T{{i}}', total_steps=9))\n")
    r = _py(code, ck)
    if r.returncode != 0:
        raise AssertionError(f"seed 失敗：{r.stderr[-300:]}")


@px("RV-PX15", "P", ("torn_rejected", "fallback_valid"), refs=("§8-4",))
def px15(ctx: CaseContext) -> None:
    """§8-4：斷電／checksum 回退。① 三種撕裂形態（半截主檔、空主檔、tmp 殘檔）⇒ 新行程拒用撕裂版、
    退回 step_idx=1 的有效保留版；② 真產品存檔迴圈 20 次以 `taskkill /F` 在隨機時刻打斷 ⇒ 每次新行程
    載入的都是 checksum 正確的版本（絕不載入撕裂版、不崩潰）。

    WHY 與 TCS:599 對應（主控裁決接受）：附錄要求「寫 checkpoint 時在三個寫入階段各以 `taskkill /F` 結束一次」。
    `taskkill` 落在哪個階段是毫秒級競態、單次無法指定階段，所以 ① 以決定性構造三個寫入階段被殺後的磁碟狀態
    （主檔寫到一半＝半截、主檔剛建尚未寫＝空檔、tmp 寫好尚未換名＝殘檔），確保三階段各驗一次；② 再以 20 次
    隨機時刻真 `taskkill /F` 驗真行程被殺後不論落在哪個階段，載入結果皆正確。兩者合起來才等價於附錄三階段。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    ck = sb.root / "ckpt"
    ck.mkdir()
    main = ck / "pb.checkpoint.json"
    shapes: list[str] = []
    for name, tear in (("half", lambda b: b[: len(b) // 2]), ("empty", lambda b: b""), ("tmp_orphan", None)):  # noqa: E501
        for p in ck.glob("*"):
            p.unlink()
        _seed_two(ck)
        good = main.read_bytes()
        if tear is None:  # 寫 tmp 途中被砍：主檔完好、遺留半截 tmp ⇒ 新行程仍載入主檔且清掉孤兒 tmp
            (ck / "pb.1234.deadbeef.tmp").write_bytes(good[: len(good) // 2])
            res, err = _load(ck)
            ctx.check(res == {"ok": True, "step_idx": 2}, f"tmp 殘檔不應影響主檔：{res}")
            shapes.append("tmp_orphan⇒主檔 step_idx=2 照載")
            continue
        main.write_bytes(tear(good))
        res, err = _load(ck)
        ctx.check(res == {"ok": True, "step_idx": 1} and "已退回保留版本" in err,
                  f"{name} 撕裂應拒用並退回 step_idx=1：{res}\n{err[-400:]}")
        shapes.append(f"{name}⇒拒用、退回 step_idx=1（log 含「已退回保留版本」）")
    ev(ctx, "torn_rejected", "；".join(shapes))
    for p in ck.glob("*"):
        p.unlink()
    rng = random.Random(20261120)
    outcomes = {"latest": 0, "fallback": 0}
    for _ in range(20):
        proc = subprocess.Popen([_PY, "-c", _SAVE_LOOP.format(ac=_AC, ck=ck)], stdout=subprocess.PIPE,  # noqa: S603,E501
                                stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",  # noqa: E501
                                creationflags=_NW)
        sb.procs.append(proc)
        ctx.check(proc.stdout.readline().strip() == "READY", "存檔迴圈沒起來")
        time.sleep(rng.uniform(0.0, 0.08))
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, creationflags=_NW)  # noqa: S603,S607,E501
        else:
            proc.kill()  # POSIX：SIGKILL，同為不給收尾機會的強制結束
        proc.wait(timeout=30)
        res, err = _load(ck)
        ctx.check(res["ok"] and res["step_idx"] is not None and res["step_idx"] >= 1,
                  f"被砍後載入必須得到有效版本：{res}\n{err[-300:]}")
        outcomes["fallback" if "已退回保留版本" in err else "latest"] += 1
    ev(ctx, "fallback_valid", f"taskkill /F 隨機打斷存檔迴圈 20 次：載入皆為有效版（最新 {outcomes['latest']}、"  # noqa: E501
                              f"退回保留版 {outcomes['fallback']}）、0 次載入撕裂版／崩潰")


@px("RV-PX42", "P＋K", ("freeze_le_5s", "kill9_fallback", "resume_cost_row"), refs=("§11.3",))
def px42(ctx: CaseContext) -> None:
    """§11.3：真引擎 TOKEN_HALT ⇒ checkpoint 凍結（外部量：halt 步驟輸出到 checkpoint 檔落盤）≤5 s；
    變體：主檔被撕裂（等同寫入中 kill -9）⇒ 回上一份有效版；resumed 窗後 `resume_cost` 落一行
    （沙盒真 `claude -p` 兩次、取真逐字稿首請求 usage）。"""
    sb = ctx.sandbox(probe_hooks=False)
    r = run_engine(sb, command=str(write_py_shim(sb, halt_script(10))), playbook=playbook(3))
    calls = shim_calls(sb)
    main = sb.root / "ckpt" / "pb.checkpoint.json"
    ctx.check("TOKEN_HALT" in r.log and main.is_file(), f"引擎應 halt 並落 checkpoint：\n{r.log[-500:]}")  # noqa: E501
    halt_out = calls[-1]["t1"]  # halt 那一步的輸出完成時刻（外部時鐘）
    lag = main.stat().st_mtime - halt_out
    ctx.check(0 <= lag <= 5.0, f"halt→checkpoint 落盤 {lag:.2f}s 不在 [0,5]")
    ev(ctx, "freeze_le_5s", f"halt_output→checkpoint_on_disk={lag:.2f}s <=5（外部以檔案 mtime 與 shim 時戳量）")  # noqa: E501
    good_step = json.loads(main.read_text(encoding="utf-8"))["step_idx"]
    prev = sorted((sb.root / "ckpt").glob("pb.checkpoint.json.v*"))
    ctx.check(bool(prev), "應有保留版本可退")
    prev_step = json.loads(prev[0].read_text(encoding="utf-8"))["step_idx"]
    main.write_bytes(main.read_bytes()[:40])  # 寫入中被 kill -9 的殘骸
    res, err = _load(sb.root / "ckpt")
    ctx.check(res["ok"] and res["step_idx"] == prev_step and "已退回保留版本" in err, f"撕裂應退回有效版：{res}")  # noqa: E501
    ev(ctx, "kill9_fallback", f"主檔撕裂（40 bytes）⇒ 載入保留版 step_idx={res['step_idx']}（最新版本為 {good_step}）")  # noqa: E501
    rr = ctx.run_claude(sb, "Reply with exactly: ok")
    rr2 = ctx.run_claude(sb, "Reply with exactly: again")
    ctx.check(rr.rc == 0 and rr2.rc == 0, f"沙盒 claude -p rc={rr.rc}/{rr2.rc}")
    tpath = _find_transcript(sb)
    rec = sb.root / "traces" / "resume_cost.jsonl"
    code = ("import sys,json;sys.path.insert(0,sys.argv[1]);import resume_cost as rc;from pathlib import Path;"  # noqa: E501
            "s=json.loads(sys.argv[2]);print(json.dumps(rc.record_window(s,Path(sys.argv[3]))))")
    state = {"session_id": sb.sid, "relay_seq": 0, "transcript": str(tpath),
             "reset_at": _first_assistant_midpoint(tpath)}
    out = _run_py(code, str(REPO / "tools" / "lib"), json.dumps(state), str(rec), env=sb.env())
    ctx.check(out.get("measured") is True and rec.is_file(), f"resume_cost 應量到並落帳：{out}")
    rows = [ln for ln in rec.read_text(encoding="utf-8").splitlines() if ln.strip()]
    ev(ctx, "resume_cost_row", f"rows={len(rows)} measured=True model={out.get('model')} "
                               f"input_tokens={out.get('input_tokens')} cache_read={out.get('cache_read_input_tokens')}")  # noqa: E501
