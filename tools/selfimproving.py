"""SelfImproving 命令列入口（P0 只有 `check`：唯讀檢查觀察帳本與協定參數）。

用法：python tools/selfimproving.py check [--repo DIR] [--ledger FILE] [--params FILE] [--json]
rc：0＝無 FAIL 且無 blocking NE；1＝至少一項 FAIL；2＝無 FAIL、至少一項 blocking NE（未判）；
3＝檢查器無法執行（用法錯誤、讀不到輸入）。規格＝docs/03_testing/contracts/TCS-SelfImproving-P0-20261019.md。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _stdio_utf8  # noqa: F401  # stdout／stderr 強制 UTF-8 的唯一實作，本檔不另寫
from lib.selfimproving import check

_REPO = Path(__file__).resolve().parents[1]
_USAGE_ERROR_RC = 3


class _Parser(argparse.ArgumentParser):
    def error(self, message: str):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"selfimproving: 用法錯誤：{message}\n")
        sys.exit(_USAGE_ERROR_RC)


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="selfimproving", description="SelfImproving 觀察帳本唯讀檢查器")
    sub = parser.add_subparsers(dest="verb", required=True, metavar="check")
    chk = sub.add_parser("check", help="檢查觀察帳本、協定參數與歷史（唯讀）")
    chk.add_argument("--repo", help="repo 根目錄（預設為本檔所在 repo）")
    chk.add_argument("--ledger", help="觀察帳本檔（相對路徑相對於 repo）")
    chk.add_argument("--params", help="params.json（相對路徑相對於 repo）")
    chk.add_argument("--json", action="store_true", help="輸出 JSON")
    return parser


def _emit(text: str) -> None:
    buf = getattr(sys.stdout, "buffer", None)
    if buf is None:
        sys.stdout.write(text)
        return
    sys.stdout.flush()
    buf.write(text.encode("utf-8"))  # 位元組直寫：Windows 文字模式不把 LF 變 CRLF
    buf.flush()


def _under(repo: Path, value: str | None, default_rel: str) -> Path:
    p = Path(value) if value else Path(default_rel)
    return p if p.is_absolute() else repo / p


def _check(args: argparse.Namespace) -> int:
    repo = Path(args.repo) if args.repo else _REPO
    if not repo.is_dir():
        raise check.InputError(f"--repo 不是目錄：{repo}")
    ledger = _under(repo, args.ledger, check.LEDGER_REL)
    params_path = _under(repo, args.params, check.PARAMS_REL)
    text, size = check.read_text(ledger, "ledger")
    params = check.load_params(params_path)
    res = check.run_check(repo, ledger, params, text, size)
    _emit(check.render_json(res) if args.json else check.render_text(res))
    return res.rc


def main(argv: list[str] | None = None) -> int:
    try:
        args = _build_parser().parse_args(argv)
        return _check(args)
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else (0 if code is None else _USAGE_ERROR_RC)
    except check.InputError as exc:
        sys.stderr.write(f"selfimproving: {exc}\n")
        return _USAGE_ERROR_RC


if __name__ == "__main__":
    sys.exit(main())
