"""prd_px 家族（雜項真行程面）：RV-PX20／30／48。

PX20＝載具 P＋E（假憑證不落痕跡）、PX30＝P＋F＋R（statusLine feed 真 producer＋真 feed 樣本）、
PX48＝P＋H（env 四層載入鏈＋真 hook 載具）。證據一律 `ev(ctx, 鍵, 實測值)`。"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

from ..sandbox import REPO
from . import CaseContext
from .prd_px_engine import run_engine, write_py_shim
from .prd_px_lib import FAKE_TOKEN, ev, ok_responder, px, t5, t5_sandbox_env, usage_payload
from .prd_px_pace import pace, scan_files
from .prd_px_run import halt_script, playbook
from .sessionctl_park import PY, run


def run_in(argv: list[str], *, cwd, env: dict, timeout: int, input: str) -> subprocess.CompletedProcess:  # noqa: E501
    """帶 stdin 的 subprocess（`sessionctl_park.run` 固定 stdin=DEVNULL）。"""
    return subprocess.run(argv, cwd=str(cwd), env=env, capture_output=True, timeout=timeout, input=input,  # noqa: S603,E501
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), encoding="utf-8", errors="replace")  # noqa: E501


@px("RV-PX20", "P＋E", ("token_absent", "cred_unmodified"), refs=("§12-憑證",))
def px20(ctx: CaseContext) -> None:
    """§12-憑證：沙盒假憑證，`--pace` 一次（真打替身端點、帶 Authorization）
    ＋真引擎一步（TOKEN_HALT 寫 checkpoint）⇒ 假 token 在 trace_dir／state／checkpoint／log 命中 0；
    憑證檔 mtime 與雜湊前後相同。"""
    sb = ctx.sandbox(probe_hooks=False)
    with t5(sb, ok_responder(lambda: usage_payload(five_hour=(30, 200), seven_day=(20, 5000)))) as stub:  # noqa: E501
        env = t5_sandbox_env(sb, stub)
        cred = sb.root / "claude_home" / ".credentials.json"
        h0, m0 = hashlib.sha256(cred.read_bytes()).hexdigest(), cred.stat().st_mtime_ns
        out = pace(sb, env)
        ctx.check(out.returncode == 0 and stub.requests and stub.requests[0]["has_auth"],
                  "--pace 應帶憑證打替身端點")
        r = run_engine(sb, command=str(write_py_shim(sb, halt_script(10))), playbook=playbook(3), env_extra=env)  # noqa: E501
        ctx.check("TOKEN_HALT" in r.log, "引擎應走 TOKEN_HALT 以寫出 checkpoint／log")
    hits = scan_files(sb.root, FAKE_TOKEN, skip=("claude_home", "t5stub", ".git"))
    hits += [s for s, t in (("pace_stdout", out.stdout + out.stderr), ("engine_out", r.text)) if FAKE_TOKEN in t]  # noqa: E501
    ctx.check(not hits, f"假 token 出現在：{hits}")
    scanned = [p.name for p in sb.root.rglob("*") if p.is_file() and "claude_home" not in p.parts]
    ev(ctx, "token_absent", f"token_hits=0 scanned_files={len(scanned)}（含 traces／ckpt／logs／qcache）")  # noqa: E501
    ctx.check(hashlib.sha256(cred.read_bytes()).hexdigest() == h0 and cred.stat().st_mtime_ns == m0,
              "憑證檔被改動")
    ev(ctx, "cred_unmodified", f"sha256={h0[:16]} mtime_ns={m0} 前後相同")


def _feed_sample() -> dict:
    """本機真 feed 樣本（最近一份，取其 rate_limits／model／context_window 組成 statusLine payload）。"""  # noqa: E501
    d = Path(os.path.expanduser("~")) / ".autosdd" / "context_feed"
    files = sorted(d.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True) if d.is_dir() else []  # noqa: E501
    for p in files:
        doc = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(doc.get("rate_limits"), dict) and len(doc["rate_limits"]) >= 2:
            return doc
    raise AssertionError("本機沒有帶 rate_limits 的真 feed 樣本（不得以不可得通過）")


@px("RV-PX30", "P＋F＋R", ("feed_rate_limits", "fallback_statusline", "stale_ignored"), refs=("§4.1.1 T3",))  # noqa: E501
def px30(ctx: CaseContext) -> None:
    """§4.1.1 T3：真 producer `statusline_context_feed.py` 吃本機真 feed 樣本
    ⇒ feed 檔含兩窗 `rate_limits`；沙盒無憑證跑 `--pace` ⇒ reason＝statusline-fallback；
    feed `ts` 改成逾 TTL ⇒ 不採用。"""
    sb = ctx.sandbox(probe_hooks=False)
    sample = _feed_sample()
    now = time.time()
    rl = {}
    for k, v in sample["rate_limits"].items():  # 真讀數的百分比；resets_at 若已過去則平移到未來（維持同一視窗長度）  # noqa: E501
        v = dict(v)
        if isinstance(v.get("resets_at"), (int, float)) and v["resets_at"] <= now + 600:
            v["resets_at"] = int(now + 3600)
        rl[k] = v
    payload = {"session_id": sb.sid, "model": sample.get("model", {}), "context_window": sample.get("context_window", {}),  # noqa: E501
               "version": sample.get("version"), "rate_limits": rl}
    feeds = sb.root / "feeds"
    env = t5_sandbox_env(sb, None, creds=False, AUTOSDD_CONTEXT_FEED_DIR=str(feeds), CLAUDE_CODE_SESSION_ID=sb.sid)  # noqa: E501
    prod = run_in([PY, str(REPO / "tools" / "statusline_context_feed.py")], cwd=sb.root, env=env, timeout=60,  # noqa: E501
               input=json.dumps(payload))
    ctx.check(prod.returncode == 0, f"producer rc={prod.returncode} {prod.stderr[-300:]}")
    fp = feeds / f"{sb.sid}.json"
    doc = json.loads(fp.read_text(encoding="utf-8"))
    ctx.check(len(doc.get("rate_limits", {})) >= 2, f"feed 應含兩窗 rate_limits：{doc.get('rate_limits')}")  # noqa: E501
    ev(ctx, "feed_rate_limits", f"windows={sorted(doc['rate_limits'])} sample_from=本機真 feed（session {sample['session_id'][:8]}）")  # noqa: E501
    out = pace(sb, env)
    ctx.check("statusline-fallback" in out.stdout, f"--pace 應採 statusline 後備：\n{out.stdout[:700]}")  # noqa: E501
    ev(ctx, "fallback_statusline", "reason=statusline-fallback（沙盒無憑證、T5 讀不到）")
    old = datetime.fromtimestamp(now - 3600).astimezone().isoformat(timespec="seconds")
    doc["ts"] = old
    fp.write_text(json.dumps(doc), encoding="utf-8")
    shutil_cache = sb.root / "qcache"
    for p in shutil_cache.glob("*"):
        p.unlink()  # 清掉上一輪的額度快取，逼 --pace 重新取數
    out2 = pace(sb, env)
    ctx.check("statusline-fallback" not in out2.stdout, f"逾 TTL 的 feed 不得採用：\n{out2.stdout[:700]}")  # noqa: E501
    ev(ctx, "stale_ignored", f"feed ts={old} 逾 TTL ⇒ --pace 不再出現 statusline-fallback")


LAYER_KEY = "AUTOSDD_QUOTA_HALT_PCT"


@px("RV-PX48", "P＋H", ("layer_order", "doctor_reports", "gov_protected"), refs=("§16.6 2026-10-11",))  # noqa: E501
def px48(ctx: CaseContext) -> None:
    """§16.6 2026-10-11：沙盒四層（行程 env／AutoClaude/.env／根 .env／env.shared）放同一鍵不同值，
    真跑 `quota_policy.py --env-doctor --root <沙盒>`：生效值依鏈序（逐層移除，看下一層接手）、doctor 報衝突；
    `AUTOSDD_UNATTENDED=1` 下真 hook（block_destructive_git）對寫 `env.shared` 的 PreToolUse 回 rc 2。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    r = sb.root
    (r / "AutoClaude").mkdir(exist_ok=True)
    layers = {"env.shared": 91, ".env": 92, "AutoClaude/.env": 93}
    for rel, v in layers.items():
        (r / rel).write_text(f"{LAYER_KEY}={v}\n", encoding="utf-8")
    doctor = str(REPO / "tools" / "lib" / "quota_policy.py")

    def effective(extra: dict | None) -> tuple[str, str]:
        e = sb.env(extra)
        o = run([PY, doctor, "--env-doctor", "--root", str(r)], cwd=r, env=e, timeout=60)
        m = re.search(rf"{LAYER_KEY}\s*=\s*(\S+)〔([^〕]*)〕", o.stdout)
        ctx.check(bool(m), f"doctor 輸出缺 {LAYER_KEY} 行：\n{o.stdout[:600]}")
        return m.group(1), m.group(2)

    seq = [effective({LAYER_KEY: "94"})]
    seq.append(effective(None))
    (r / ".env").unlink()
    seq.append(effective(None))
    ctx.check([s[0] for s in seq][0] == "94" and len({s[0] for s in seq}) == 3, f"生效值應逐層不同：{seq}")  # noqa: E501
    ev(ctx, "layer_order", " → ".join(f"{v}〔{layer}〕" for v, layer in seq))
    (r / ".env").write_text(f"{LAYER_KEY}=92\n", encoding="utf-8")
    full = run([PY, doctor, "--env-doctor", "--root", str(r)], cwd=r, env=sb.env({LAYER_KEY: "94"}), timeout=60)  # noqa: E501
    ctx.check(full.returncode == 1 and "[shadows-shared]" in full.stdout and "[engine≠harness]" in full.stdout,  # noqa: E501
              f"doctor 應列出衝突：rc={full.returncode}\n{full.stdout[-700:]}")
    ev(ctx, "doctor_reports", "rc=1 findings=[shadows-shared, engine≠harness] key=" + LAYER_KEY)
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Write", "session_id": sb.sid, "cwd": str(REPO),  # noqa: E501
               "tool_input": {"file_path": str(REPO / "env.shared"), "content": "x"}}
    h = run_in([str(REPO / ".venv" / "Scripts" / "python.exe"), str(REPO / ".claude" / "hooks" / "block_destructive_git.py")],  # noqa: E501
            cwd=REPO, env=sb.env({"AUTOSDD_UNATTENDED": "1"}), timeout=60, input=json.dumps(payload))  # noqa: E501
    ctx.check(h.returncode == 2 and "env.shared" in h.stderr, f"hook 應 rc 2：rc={h.returncode} {h.stderr[:300]}")  # noqa: E501
    ev(ctx, "gov_protected", f"UNATTENDED=1 寫 env.shared ⇒ hook rc={h.returncode}（只問 hook、未寫任何檔）")  # noqa: E501
