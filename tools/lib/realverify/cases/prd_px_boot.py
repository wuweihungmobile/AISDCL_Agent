"""prd_px 家族（真引擎開機自檢面，載具 P／X）：RV-PX13／34／38／47。

每案都起真 `python -m autoclaude`（沙盒 cwd、沙盒 config／log／checkpoint），證據取自引擎自己的輸出與 log。"""  # noqa: E501

from __future__ import annotations

import re
import shutil
import subprocess

from ..sandbox import Sandbox
from . import CaseContext
from .prd_px_engine import REAL_EXTRA_ARGS, REAL_PLAYBOOK, real_claude, run_engine, write_shim
from .prd_px_lib import ev, px

DRY = "本次以 DRY_RUN 執行"
NOTIFY_TRACE = "[NOTIFY-disabled] AutoClaude — 開機自檢"


def _dry_count(r) -> tuple[bool, int]:
    return DRY in r.text, r.text.count(NOTIFY_TRACE)


@px("RV-PX13", "P", ("free_is_real", "pass_line"), refs=("§6.2-3", "§8-14"))
def px13(ctx: CaseContext) -> None:
    """§6.2-3／§8-14：真引擎開機自檢印出的可用空間是真磁碟值（與同時 shutil.disk_usage 相差 ≤1%）。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    before = shutil.disk_usage(sb.root).free
    # 真 CLI：`--version` 與步驟都走真 claude（haiku、一句話），沒有 shim
    r = run_engine(sb, command=real_claude(), playbook=REAL_PLAYBOOK, extra_args=REAL_EXTRA_ARGS, timeout=300)  # noqa: E501
    after = shutil.disk_usage(sb.root).free
    ctx.check(r.rc == 0, f"引擎 rc={r.rc}\n{r.text[-800:]}")
    m = re.search(r"可用空間 (\d+) ≥ 需求 (\d+) bytes", r.text)
    ctx.check(bool(m), f"自檢輸出缺「可用空間 … ≥ 需求 … bytes」：\n{r.text[-800:]}")
    free = int(m.group(1))
    ref = max(before, after)
    ctx.check(abs(free - ref) <= ref * 0.01, f"自檢 free={free} 與 disk_usage={before}/{after} 相差逾 1%")  # noqa: E501
    ev(ctx, "free_is_real", f"engine_free={free} disk_usage_before={before} after={after} "
                           f"diff_pct={abs(free - ref) * 100.0 / ref:.4f}<=1")
    ev(ctx, "pass_line", m.group(0) + " real_cli=True（拒絕分支由既有單元測試承接，見 TCS §10.3 分支例外）")  # noqa: E501


def _version_pair(ctx: CaseContext, sb_ok: Sandbox, sb_bad: Sandbox, ok_run, bad_run, ok_key: str, bad_key: str,  # noqa: E501
                  ok_real: bool) -> None:
    dry_ok, n_ok = _dry_count(ok_run)
    ctx.check(ok_run.rc == 0, f"同家族引擎 rc={ok_run.rc}\n{ok_run.text[-600:]}")
    ctx.check(not dry_ok and n_ok == 0, f"已知家族不得 DRY_RUN／通知：dry={dry_ok} notify={n_ok}")
    ev(ctx, ok_key, f"dry_run={dry_ok} notify_traces={n_ok} real_cli={ok_real}")
    dry_bad, n_bad = _dry_count(bad_run)
    ctx.check(dry_bad and n_bad == 1, f"未知 minor 應 DRY_RUN 且通知痕跡恰 1 筆：dry={dry_bad} notify={n_bad}\n{bad_run.text[-600:]}")  # noqa: E501
    ev(ctx, bad_key, f"dry_run={dry_bad} notify_traces={n_bad}")


def _real_version() -> str:
    exe = shutil.which("claude")
    out = subprocess.run(  # noqa: S603
        [exe, "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace",
                         timeout=60, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.strip()  # noqa: E501
    return out


@px("RV-PX34", "P＋X", ("known_family", "unknown_minor_dryrun"), refs=("§6.2 R-6.2-2", "§8 列 13"))
def px34(ctx: CaseContext) -> None:
    """§6.2 R-6.2-2／§8 列 13：真 `claude --version` 已知家族不 DRY_RUN；shim 回未知 minor ⇒ DRY_RUN＋通知痕跡。"""  # noqa: E501
    # 變體 1：真 CLI（`--version` 與步驟皆真，步驟走 haiku 一句話）。變體 2 的「未知 minor」真 CLI 給不出，  # noqa: E501
    # 故只有該變體以 shim 假裝版號 9.9.0（引擎在 DRY_RUN 下不呼叫 claude -p，shim 只回 --version）。  # noqa: E501
    real = _real_version()
    m = re.match(r"(\d+\.\d+\.\d+)", real)
    ctx.check(bool(m), f"真 claude --version 讀不到版號：{real!r}")
    sb1 = ctx.sandbox(probe_hooks=False)
    r1 = run_engine(sb1, command=real_claude(), playbook=REAL_PLAYBOOK, extra_args=REAL_EXTRA_ARGS, timeout=300)  # noqa: E501
    sb2 = ctx.sandbox(probe_hooks=False)
    r2 = run_engine(sb2, command=str(write_shim(sb2, version="9.9.0")))
    ev(ctx, "real_cli_version", real)
    _version_pair(ctx, sb1, sb2, r1, r2, "known_family", "unknown_minor_dryrun", True)


@px("RV-PX47", "P＋X", ("patch_family_ok", "new_minor_dryrun"), refs=("§16.6 2026-10-10",))
def px47(ctx: CaseContext) -> None:
    """§16.6 2026-10-10：shim 同家族較高 patch 不 DRY_RUN；新 minor ⇒ DRY_RUN＋通知。

    版號必須「比真 CLI 高」（2.1.999／2.77.0），真 CLI 給不出，故兩個變體都用 shim 假裝版號（附錄載具 P＋X 本就如此）；  # noqa: E501
    變體 1 的步驟輸出由 shim 回 `[DONE]`——這一步是 shim（evidence `shim_step=True`），引擎面與 log 全是真的。"""  # noqa: E501
    sb1 = ctx.sandbox(probe_hooks=False)
    r1 = run_engine(sb1, command=str(write_shim(sb1, version="2.1.999")))
    ctx.check("同家族 2.1.x" in r1.text, f"應走家族判定：\n{r1.text[-600:]}")
    sb2 = ctx.sandbox(probe_hooks=False)
    r2 = run_engine(sb2, command=str(write_shim(sb2, version="2.77.0")))
    _version_pair(ctx, sb1, sb2, r1, r2, "patch_family_ok", "new_minor_dryrun", False)
    ev(ctx, "shim_step", "variant1_step=shim variant2=DRY_RUN（無步驟呼叫）")


@px("RV-PX38", "P", ("bypass_refused", "default_not_bypass"), refs=("§12 權限旗標",))
def px38(ctx: CaseContext) -> None:
    """§12 權限旗標：config 要 bypassPermissions（非容器）⇒ 開機自檢拒絕；出廠 config 的 spawn 命令列不含 bypass。"""  # noqa: E501
    sb1 = ctx.sandbox(probe_hooks=False)
    # bypass 被拒＝開機自檢即終止，引擎只呼叫 `--version` ⇒ 真 CLI；出廠 config 那次要跑步驟，亦用真 CLI（haiku）  # noqa: E501
    r1 = run_engine(sb1, command=real_claude(), extra_cfg="executor:\n  permission_mode: bypassPermissions\n",  # noqa: E501
                    env_extra={"ALLOW_PERMISSION_BYPASS": ""})
    ctx.check(r1.rc != 0 and "拒絕啟動" in r1.text and "bypassPermissions" in r1.text,
              f"要求 bypass 應被拒絕（rc≠0＋拒絕啟動）：rc={r1.rc}\n{r1.text[-700:]}")
    ev(ctx, "bypass_refused", f"real_cli=True rc={r1.rc} refused_line_present=True 步驟未執行={'subprocess 模式啟動' not in r1.log}")  # noqa: E501
    sb2 = ctx.sandbox(probe_hooks=False)
    r2 = run_engine(sb2, command=real_claude(), playbook=REAL_PLAYBOOK, extra_args=REAL_EXTRA_ARGS, timeout=300)  # noqa: E501
    spawn = re.search(r"subprocess 模式啟動：(.*)", r2.text)
    ctx.check(r2.rc == 0 and bool(spawn), f"出廠 config 應正常 spawn：rc={r2.rc}\n{r2.text[-600:]}")
    ctx.check("bypass" not in spawn.group(1).lower() and "skip-permissions" not in spawn.group(1),
              f"出廠命令列含 bypass：{spawn.group(1)}")
    ev(ctx, "default_not_bypass", f"real_cli=True spawn_cmd={spawn.group(1)[:200]}")
