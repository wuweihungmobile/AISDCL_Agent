"""sessionctl_converge 家族：RV-C1（封存閘）、RV-C2（冷叫醒閘）、RV-C3（事故重放 CR1）。

沙盒裝法與環境見 `sessionctl_handoff.py` 模組 docstring（被測碼逐位元組複製、hook 真跑）。
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from ..driver import EnvMissing
from ..sandbox import REPO, main_checkout_root, slug_of
from ..transcript import Transcript
from . import CaseContext, case
from .sessionctl_handoff import (
    blocking_texts,
    fill_main_layer,
    install_sessionctl,
    new_session,
    package_for,
    run_cli,
    sc_env,
    seal_session,
    spawn_trace,
)

_NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
#: 把硬線下修到沙盒一輪對話就會超過（方向鎖只准下修，所以這是合法用法；R216 起換窗只看硬線，R1 已退役）。  # noqa: E501
_LOW_R1 = {"AUTOSDD_SWITCH_HARD_CTX_TOKENS": "1000"}


@case("RV-C1", "sessionctl_converge", refs=("V5",))
def rv_c1(ctx: CaseContext) -> None:
    """封存閘：硬線下修 ⇒ Stop 被推回一次（內容含 `--finalize`）；第二次 Stop 放行；硬線出廠值 ⇒ 不推回。"""  # noqa: E501
    sb = ctx.sandbox()
    install_sessionctl(sb)
    # 暖身輪：第一輪 Stop 時逐字稿尚無 assistant usage（ctx 量不到 ⇒ 守衛依設計不判），真 session 都有前文  # noqa: E501
    r0 = ctx.run_claude(sb, "Reply with exactly: RV_C1_WARM", env_extra=sc_env(sb))
    ctx.check(r0.rc == 0, f"暖身輪 rc={r0.rc}")
    r = ctx.run_claude(sb, "Reply with exactly: RV_C1_OK", env_extra=sc_env(sb, **_LOW_R1))
    ctx.check(r.rc == 0 and not r.timed_out, f"claude -p rc={r.rc} timed_out={r.timed_out}")
    tr = ctx.transcript(sb)
    gate = [t for t in blocking_texts(tr, "Stop") if "封存閘" in t]
    ctx.check(len(gate) == 1, f"Stop 封存閘推回次數應恰為 1（第二次放行），實為 {len(gate)}")
    ctx.check("--finalize" in gate[0] and "硬線" in gate[0], f"推回內容缺 --finalize／硬線：{gate[0][:200]!r}")  # noqa: E501
    ev = tr.hook_blocking_errors("Stop", "封存閘")[0]
    ctx.check(any(e.get("sid") == sb.sid for e in spawn_trace(sb, "seal_stop_block")),
              "沒有 seal_stop_block 痕跡")
    ctx.check(len(tr.stop_hook_summaries()) >= 2, "Stop hook 沒有在推回後再跑第二次（放行那次）")
    # 反向對照：出廠硬線 ⇒ 同樣一輪對話不該被推回（斷言才不是恆真）
    s2 = new_session(sb)
    r2 = ctx.run_claude(s2, "Reply with exactly: RV_C1_CONTROL", env_extra=sc_env(sb))
    ctx.check(r2.rc == 0, f"對照組 rc={r2.rc}")
    t2 = Transcript.for_sid(s2.sid)
    ctx.check(not [t for t in blocking_texts(t2, "Stop") if "封存閘" in t], "出廠硬線卻被推回封存閘")  # noqa: E501
    ctx.evidence(f"RV-C1 {tr.coords(ev)} 封存閘推回；對照 {s2.sid[:8]} 無推回")


@case("RV-C2", "sessionctl_converge", refs=("DEF-200-588",))
def rv_c2(ctx: CaseContext) -> None:
    """冷叫醒閘：已封存的 session 還掛著背景 shell ⇒ Stop 推回並要求 TaskStop（含任務數）。"""
    sb = ctx.sandbox()
    seal_session(ctx, sb)
    prompt = ("Start exactly ONE background shell command by calling the shell tool with "
              "run_in_background=true and the command: ping -n 46 127.0.0.1 . "
              "Do NOT wait for it. Then end your turn immediately with the single word LAUNCHED.")
    r = ctx.run_claude(sb, prompt, env_extra=sc_env(sb), timeout_s=280,
                       extra_args=("--allowedTools=Bash,PowerShell",))
    ctx.check(r.rc == 0 and not r.timed_out, f"claude -p rc={r.rc} timed_out={r.timed_out} {r.stderr[:200]}")  # noqa: E501
    tr = ctx.transcript(sb)
    gate = tr.hook_blocking_errors("Stop", "冷叫醒閘")
    ctx.check(bool(gate), "已封存＋背景 shell 在跑，Stop 沒有冷叫醒閘推回；"
              f"Stop 推回：{[t[:60] for t in blocking_texts(tr, 'Stop')]}")
    text = gate[0].data["attachment"]["blockingError"]["blockingError"]
    ctx.check("TaskStop" in text and "背景任務" in text, f"推回內容缺 TaskStop／背景任務：{text[:200]!r}")  # noqa: E501
    ctx.check(len(gate) == 1, f"冷叫醒閘推回次數應恰為 1，實為 {len(gate)}")
    ctx.evidence(f"RV-C2 {tr.coords(gate[0])} 冷叫醒閘")


_BG_SHELL = ("Start exactly ONE background shell command by calling the shell tool with "
             "run_in_background=true and the command: ping -n 21 127.0.0.1 . "
             "Do NOT wait for it. Then end your turn immediately with the single word LAUNCHED.")


def _env_without_keepwarm_gate(sb) -> dict:
    """RV-C4 的 `claude -p` 回合關掉 Stop 保溫閘（只關保溫閘，不影響被測的冷叫醒閘）。

    WHY（R216 複審 P3-c，2026-11-19 保留證據重現 RV-C4 逾時 280 秒）：甲組是自續跑＝保溫閘「該掛」
    的情形，閘會在背景 shell 結束後推回「請掛 `sessionctl keepwarm`」；haiku 偶爾照做、掛上 45 分鐘
    的背景行程，`claude -p` 便停在「Waiting for background work to finish」直到牆鐘逾時（低頻，故
    多數次 pass）。保溫判決本來就由下面的 `_keepwarm_verdict` 真跑 CLI 驗，不需要讓模型掛。"""
    return sc_env(sb, AUTOSDD_KEEPWARM_OFF="1")


def _keepwarm_verdict(sb, transcript) -> tuple[int, str]:
    """真跑沙盒內安裝的 `sessionctl.py keepwarm --min 1`（小上下文門檻下修，額度不查）；回 (rc, 末行判決)。"""  # noqa: E501
    from .sessionctl_keepwarm import LOW_CTX, NO_QUOTA  # noqa: PLC0415 — 只有本案例需要
    r = subprocess.run(  # noqa: S603
        [sys.executable, str(sb.root / "tools" / "sessionctl.py"), "keepwarm", "--sid", sb.sid,
         "--projects-dir", str(transcript.parent), "--min", "1", "--poll-sec", "5"],
        cwd=str(sb.root), env=sb.env(sc_env(sb, **NO_QUOTA, **LOW_CTX)), capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=200, creationflags=_NOWIN)
    last = [ln for ln in r.stdout.splitlines() if ln.startswith("KEEPWARM_VERDICT=")]
    return r.returncode, (last[-1] if last else r.stdout[-200:])


@case("RV-C4", "sessionctl_converge", refs=("DEF-200-617", "DEF-200-619", "DEF-200-621"))
def rv_c4(ctx: CaseContext) -> None:
    """同一 session 自己續跑不算交棒（R216 QA P2-1；暴露證據 sid 31ea79d4）。

    甲（自續跑）：封存後由**同 sid** 跑真 CLI `handoff --ack` ⇒ 記為續跑（`.resumed`、無 `.ack`、封存作廢）；
    再用真 `claude -p`＋真 Stop hook 掛背景 shell ⇒ 冷叫醒閘**不推**；真 keepwarm ⇒ 不 skip（照常 ping）。
    乙（對照＝真交棒）：**別的 sid** ack ⇒ `.ack` 記下接手者；同樣的背景 shell ⇒ 冷叫醒閘照推恰一次；
    keepwarm ⇒ `skip reason=handed_over`。兩組同一套載具，差別只有 ack 者是誰，斷言才不是恆真。
    """  # noqa: E501
    sb = ctx.sandbox()
    pkg = seal_session(ctx, sb)
    rc, out, err = run_cli(sb, "handoff", "--ack", str(pkg), env_extra={"CLAUDE_CODE_SESSION_ID": sb.sid})  # noqa: E501
    ctx.check(rc == 0 and "續跑" in out, f"自己 --ack rc={rc} {out[:160]!r} {err[:160]!r}")
    ctx.check(pkg.with_suffix(".resumed").is_file() and not pkg.with_suffix(".ack").exists()
              and not pkg.with_suffix(".sealed").exists(), "自續跑後應有 .resumed、無 .ack、無 .sealed")  # noqa: E501
    r = ctx.run_claude(sb, _BG_SHELL, env_extra=_env_without_keepwarm_gate(sb), timeout_s=280,
                       extra_args=("--allowedTools=Bash,PowerShell",))
    ctx.check(r.rc == 0 and not r.timed_out, f"甲組 claude -p rc={r.rc} timed_out={r.timed_out}")
    tr = ctx.transcript(sb)
    ctx.check(not tr.hook_blocking_errors("Stop", "冷叫醒閘"), "同 sid 自續跑卻被冷叫醒閘推回（把自己當成已交棒）")  # noqa: E501
    ctx.check(len(tr.stop_hook_summaries()) >= 1, "Stop hook 沒跑（甲組斷言恆真）")
    rc_k, last = _keepwarm_verdict(sb, tr.path)
    ctx.check(rc_k == 0 and last.startswith("KEEPWARM_VERDICT=ping"), f"自續跑後 keepwarm 不該 skip：rc={rc_k} {last!r}")  # noqa: E501

    # 丙（P3-a，純 CLI）：舊格式（無 sid）`.ack` 無從分辨 ⇒ 原主人再 `--ack` 不刪、並印處置
    pkg.with_suffix(".ack").write_text("acked 2026-01-01T00:00:00+00:00\n", encoding="utf-8")
    rc, out, err = run_cli(sb, "handoff", "--ack", str(pkg), env_extra={"CLAUDE_CODE_SESSION_ID": sb.sid})  # noqa: E501
    ctx.check(rc == 0 and "舊格式 .ack" in out and pkg.with_suffix(".ack").exists(),
              f"舊格式 ack 應保留並提示：rc={rc} {out[:200]!r} {err[:120]!r}")

    sb2 = ctx.sandbox()
    pkg2 = seal_session(ctx, sb2)
    rc, out, err = run_cli(sb2, "handoff", "--ack", str(pkg2), env_extra={"CLAUDE_CODE_SESSION_ID": "newcomer-sid-0001"})  # noqa: E501
    ctx.check(rc == 0 and "sid=newcomer-sid-0001" in pkg2.with_suffix(".ack").read_text(encoding="utf-8"), f"別的 sid ack rc={rc} {err[:160]!r}")  # noqa: E501
    ctx.check(not pkg2.with_suffix(".resumed").exists(), "別的 sid ack 不該寫 .resumed")
    r2 = ctx.run_claude(sb2, _BG_SHELL, env_extra=_env_without_keepwarm_gate(sb2), timeout_s=280,
                        extra_args=("--allowedTools=Bash,PowerShell",))
    ctx.check(r2.rc == 0 and not r2.timed_out, f"乙組 claude -p rc={r2.rc} timed_out={r2.timed_out}")  # noqa: E501
    tr2 = ctx.transcript(sb2)
    gate = tr2.hook_blocking_errors("Stop", "冷叫醒閘")
    ctx.check(len(gate) == 1, f"真交棒（別的 sid ack）應被冷叫醒閘推回恰一次，實為 {len(gate)}")
    rc_k2, last2 = _keepwarm_verdict(sb2, tr2.path)
    ctx.check(rc_k2 == 0 and last2 == "KEEPWARM_VERDICT=skip reason=handed_over", f"真交棒後 keepwarm 應 skip：rc={rc_k2} {last2!r}")  # noqa: E501
    ctx.evidence(f"RV-C4 甲 {sb.sid[:8]} 自續跑 無冷叫醒閘＋{last}；乙 {sb2.sid[:8]} {tr2.coords(gate[0])} 推回＋{last2}")  # noqa: E501


def _census_base_args() -> list[str]:
    """真事故逐字稿母體的 `--base`：在 git worktree 內跑時，母體住**主 checkout** 的專案目錄，
    不是 worktree 路徑的 slug（否則重放找不到 290,000 事故而誤判紅＝載具問題）。
    非 worktree ⇒ 不帶參數（行為與舊版逐位元組相同）；worktree 且母體目錄不存在 ⇒
    明確報 `EnvMissing`（rc 2），**不默默 skip、不誤判成被測物壞掉**。"""
    main = main_checkout_root()
    if main == REPO:
        return []
    base = Path.home() / ".claude" / "projects" / slug_of(main)
    if not base.is_dir():
        raise EnvMissing(f"RV-C3 在 git worktree（{REPO}）內跑，事故逐字稿母體應在主 checkout 的專案目錄 {base}，但該目錄不存在")  # noqa: E501
    return ["--base", str(base)]


@case("RV-C3", "sessionctl_converge", refs=("CR1", "DEF-200-621"))
def rv_c3(ctx: CaseContext) -> None:
    """事故重放 CR1（2026-11-14 20:52）：大上下文＋無背景代理＋有交接包但沒 finalize ⇒ 結束回合被推回。

    ① 真實事故逐字稿重放（`waste_census --replay-hard-ctx`，重放表要同時列出舊 29 萬與新硬線 85 萬；舊線擋得到事故、新線依裁決不再擋＝事故形態改由封存閘在硬線以上負責，見 RV-CM1）。
    ② 沙盒重演事故形態：先 `handoff --build`（只有骨架、未 finalize）、硬線下修 ⇒ Stop 推回「未封存」並指向該包。
    """  # noqa: E501
    out = subprocess.run(  # noqa: S603
        [sys.executable, str(REPO / "tools" / "probe" / "waste_census.py"), "--replay-hard-ctx",
         "--since-days", "14", "--candidates", "290000,850000", *_census_base_args()],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=180, creationflags=_NOWIN)
    ctx.check(out.returncode == 0, f"waste_census 重放 rc={out.returncode}")
    row = next((ln for ln in out.stdout.splitlines() if re.match(r"\s*290,000\s", ln)), "")
    ctx.check(bool(row) and row.split()[-1] == "True",
              f"重放工具對 290,000 沒擋到真實事故（incident_blocked 非 True，重放本身壞了）：{row!r}")  # noqa: E501
    new = next((ln for ln in out.stdout.splitlines() if re.match(r"\s*850,000\s", ln)), "")
    ctx.check(bool(new) and new.split()[-1] == "False" and float(new.split()[2]) > float(row.split()[2]),  # noqa: E501
              f"出廠硬線 850,000 應不再擋該事故、且留給工作的空間（room_med）大於 29 萬線：{new!r} vs {row!r}")  # noqa: E501
    sb = ctx.sandbox()
    install_sessionctl(sb)
    r0 = ctx.run_claude(sb, "Reply with exactly: RV_C3_WORK", env_extra=sc_env(sb))
    ctx.check(r0.rc == 0, f"首輪 rc={r0.rc}")
    rc, _, err = run_cli(sb, "handoff", "--build", "--session-id", sb.sid)
    ctx.check(rc == 0, f"--build rc={rc} {err[:200]}")
    pkg = package_for(sb)
    ctx.check(not pkg.with_suffix(".sealed").exists(), "前置：不該已封存")
    r = ctx.run_claude(sb, "Reply with exactly: RV_C3_WAIT", env_extra=sc_env(sb, **_LOW_R1))
    ctx.check(r.rc == 0 and not r.timed_out, f"事故輪 rc={r.rc}")
    tr = ctx.transcript(sb)
    gate = [rec for rec in tr.hook_blocking_errors("Stop", "封存閘")]
    ctx.check(len(gate) == 1, f"事故形態的 Stop 應被封存閘推回恰一次，實為 {len(gate)}")
    text = gate[0].data["attachment"]["blockingError"]["blockingError"]
    ctx.check("未封存" in text and str(pkg) in text and "--finalize" in text,
              f"推回沒指向未 finalize 的交接包：{text[:240]!r}")
    # 對照：封存後同樣硬線下修 ⇒ 不再推回（封存是出口）
    fill_main_layer(pkg)
    rc, _, _ = run_cli(sb, "handoff", "--finalize", str(pkg))
    ctx.check(rc == 0, "finalize 失敗")
    r2 = ctx.run_claude(sb, "Reply with exactly: RV_C3_AFTER", env_extra=sc_env(sb, **_LOW_R1))
    ctx.check(r2.rc == 0, f"封存後對照輪 rc={r2.rc}")
    after = [t for t in blocking_texts(ctx.transcript(sb), "Stop") if "封存閘" in t]
    ctx.check(len(after) == 1, f"封存後不該再被推回封存閘（出口失效？），累計 {len(after)} 次")
    ctx.evidence(f"RV-C3 重放 290,000 擋、850,000 不擋（空間 {new.split()[2]} 回合）；沙盒 {tr.coords(gate[0])} 推回未封存包")  # noqa: E501
