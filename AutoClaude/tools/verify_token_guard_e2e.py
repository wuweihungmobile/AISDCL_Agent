"""token-guard compact/halt 編排「端到端真跑」驗證載具（AutoSDD improving_84 W-84-2，C 軌）。

背景（improving_84 §2.5 缺口）：improving_78/79 已把 compact/halt 編排接進 production
Kernel（core/kernel.py:_consult_token_guard / _handle_compact），improving_81-83 已修通
訊號源（真跑 token% 峰值 PTY 6.2 / SDK 2.0%），但**從來沒有一次真跑讓 `TOKEN_COMPACT` /
`TOKEN_HALT` marker 真的出現**——因真跑觀測峰值（~6%）遠低於預設門檻（80/90%）。compact/
halt 編排在真跑中觸發至今只有單元測試（mock 事件/門檻）證明，無真跑鐵證。

本載具補上這最後一哩：搭配調低門檻 config（scripts/ab_configs/lowthr_{compact,halt}_config
.yaml）跑一次真實 playbook，斷言 production 編排真的觸發（marker 出現 / KernelResult.halted）。
**零行為變更**——重用 ab_compare_backends 的 parse_run_metrics / run_backend，只讀 log 斷言。

fail-loud（工程紀律第 12 條）：log 不存在 / marker 缺席 → 明確 exit 非 0，不靜默回 0。

用法（於 AutoClaude/ 目錄）：
  # 離線斷言既有 log（零 token，回歸重驗）
  python tools/verify_token_guard_e2e.py --parse-log <log> --expect compact
  python tools/verify_token_guard_e2e.py --parse-log <log> --expect halt
  # 真跑（需授權 token）
  python tools/verify_token_guard_e2e.py --run-compact scripts/sdd_bridge_smoke.yaml \\
      --config scripts/ab_configs/lowthr_compact_config.yaml --workdir <tmp>
  python tools/verify_token_guard_e2e.py --run-halt scripts/sdd_bridge_smoke.yaml \\
      --config scripts/ab_configs/lowthr_halt_config.yaml --workdir <tmp>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# repo 根（AutoClaude/）入 sys.path，使 `tools.` namespace import 在 script / 測試模組兩境皆成立。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.ab_compare_backends import (  # noqa: E402
    RunMetrics,
    parse_run_metrics,
    run_backend,
)


def assert_compact_fired(m: RunMetrics) -> tuple[bool, str]:
    """斷言 compact 編排在本次 run 端到端觸發過（`TOKEN_COMPACT` marker 出現 ≥1 次）。

    judge：m.compact_count >= 1（載具自 TOKEN_COMPACT 行計數，core/kernel.py:_handle_compact
    送 /compact 時印）。0 → fail-loud（compact 編排未觸發＝這次真跑沒撞 compact 門檻，
    或編排斷線）。本斷言與「門檻數值」無關，只問「compact 編排是否走到」。
    """
    if m.compact_count >= 1:
        return True, (
            f"compact 編排已端到端觸發：TOKEN_COMPACT marker 出現 {m.compact_count} 次"
            f"（peak={m.effective_peak_token_pct:.1f}%）"
        )
    return False, (
        f"compact 編排未觸發：compact_count=0（peak={m.effective_peak_token_pct:.1f}%、"
        f"halted={m.halted}）。真跑未撞 compact 門檻或編排斷線。"
    )


def assert_halt_fired(m: RunMetrics) -> tuple[bool, str]:
    """斷言 halt 編排在本次 run 端到端觸發過（KernelResult.halted=True）。

    judge：m.halted is True（解析自最終 KernelResult 行的 halted 欄；core/kernel.py:
    _consult_token_guard 判 ≥halt 門檻回 StepOutcome(HALT)、印 TOKEN_HALT marker → run()
    匯為 KernelResult.halted=True）。False → fail-loud（halt 編排未觸發）。halted 是端到端
    權威落地訊號（marker 出現只是中途，halted=True 才證 run 真的因 token 而停）。
    """
    if m.halted is True:
        return True, (
            f"halt 編排已端到端觸發：KernelResult(halted=True)"
            f"（peak={m.effective_peak_token_pct:.1f}%）"
        )
    return False, (
        f"halt 編排未觸發：halted={m.halted}（peak={m.effective_peak_token_pct:.1f}%、"
        f"compact_count={m.compact_count}）。真跑未撞 halt 門檻或編排斷線。"
    )


_EXPECT = {"compact": assert_compact_fired, "halt": assert_halt_fired}


def _load_log_or_raise(log_file: Path) -> str:
    """讀 log 檔；不存在＝fail-loud（不靜默回空字串騙過斷言）。"""
    if not log_file.exists():
        raise RuntimeError(f"log 檔不存在：{log_file}（真跑啟動即失敗？fail-loud，不靜默回 0）")
    return log_file.read_text(encoding="utf-8", errors="replace")


def _run_and_assert(playbook: str, config: str | None, workdir: str, expect: str) -> int:
    """真跑一次 playbook（需授權 token）→ 解析 log → 依 expect 斷言；fail-loud 回 exit 碼。"""
    abs_pb = str(Path(playbook).resolve())
    abs_cfg = str(Path(config).resolve()) if config else None
    log_text, m = run_backend(abs_pb, "pty", Path(workdir), abs_cfg)
    return _emit_verdict(m, expect, log_text)


def _parse_and_assert(log_file: str, expect: str) -> int:
    """離線斷言既有 log（零 token）→ exit 碼。"""
    log_text = _load_log_or_raise(Path(log_file))
    m = parse_run_metrics(log_text, backend="pty")
    return _emit_verdict(m, expect, log_text)


def _emit_verdict(m: RunMetrics, expect: str, log_text: str) -> int:
    ok, reason = _EXPECT[expect](m)
    marker = "TOKEN_COMPACT" if expect == "compact" else "TOKEN_HALT"
    present = sum(1 for ln in log_text.splitlines() if marker in ln)
    status = "PASS" if ok else "FAIL"
    print(f"[verify_token_guard_e2e] expect={expect} → {status}")
    print(f"  {reason}")
    print(f"  ({marker} 行數={present}; KernelResult: halted={m.halted} "
          f"completed={m.completed_steps}/{m.total_steps})")
    return 0 if ok else 1


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="token-guard compact/halt 端到端真跑驗證")
    p.add_argument("--run-compact", metavar="PLAYBOOK", help="真跑模式：驗 compact 觸發")
    p.add_argument("--run-halt", metavar="PLAYBOOK", help="真跑模式：驗 halt 觸發")
    p.add_argument("--config", help="真跑 config（含調低 token_guard 門檻）")
    p.add_argument("--workdir", help="真跑工作目錄")
    p.add_argument("--parse-log", metavar="LOGFILE", help="離線模式：對既有 log 斷言（零 token）")
    p.add_argument("--expect", choices=["compact", "halt"], help="離線模式預期觸發類型")
    return p


def main(argv: list[str] | None = None) -> int:
    # DEF-82-001 紀律：報表/用法訊息含中文，Windows cp950 console 直接 print 會
    # UnicodeEncodeError 中斷；stdout（verdict）+ stderr（fail-loud 用法）皆強制 utf-8。
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, OSError):
            pass
    args = _build_argparser().parse_args(argv)
    if args.parse_log:
        if not args.expect:
            print("--parse-log 需搭配 --expect {compact,halt}", file=sys.stderr)
            return 2
        return _parse_and_assert(args.parse_log, args.expect)
    if args.run_compact and args.workdir:
        return _run_and_assert(args.run_compact, args.config, args.workdir, "compact")
    if args.run_halt and args.workdir:
        return _run_and_assert(args.run_halt, args.config, args.workdir, "halt")
    print("需 --parse-log+--expect（離線）或 --run-compact/--run-halt+--workdir（真跑）",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
