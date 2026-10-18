#!/usr/bin/env python3
"""SDD 外部專案模式三件組產生器（整合輪 116 G-116-12／D-116-15）。

依 ``--sub`` 與 ``--slug`` 一次印出 hooks-ON 視窗要設的五個變數
（``SDD_ACTIVE_VERSION``／``SDD_PROJECT``／``SDD_STATE_DIR`` 加兩個遙測旗標），
形態可選 powershell／bash／json；``--check`` 只驗證狀態檔存在。

不寫 ``$PROFILE``、不啟動 ``claude``、不建任何狀態檔、不改 ``os.environ``。
規格＝``docs/03_testing/contracts/TCS-SddEnv-20261018.md``（FRD-lite R1～R10）。

rc：0 成功；1 版本不可解；2 引數不合法；5 ``--check`` 狀態檔不存在。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sdd_version  # noqa: E402
from rfc_lifecycle_lint import force_utf8_stdio  # noqa: E402  島內唯一的 stdio UTF-8 實作（根層 dedup 棘輪）

VERSION_PREFIX = "AISDLC_SDD_v"
SLUG_RE = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
SLUG_MAX = 30
SUBS = ("autoclaude", "agentconsole", "monorepo", "sdd")
SHELLS = ("powershell", "bash", "json")


def validate_slug(slug: str) -> str | None:
    """合規回 None，否則回一行理由（順序：保留字、格式、長度）。"""
    if slug.lower() == "aisdlc_sdd":
        return f"slug 不可使用保留字 {slug!r}"
    if not SLUG_RE.fullmatch(slug):
        return f"slug 格式不合：須為小寫英數字以單一連字號分隔（{slug!r}）"
    if len(slug) > SLUG_MAX:
        return f"slug 長度超過 {SLUG_MAX} 個字元（{len(slug)}）"
    return None


def state_dir_for(sub: str, root: str, version: str) -> str:
    if sub == "autoclaude":
        return os.path.join(root, "AutoClaude", "build", "reports", "fsm")
    if sub == "agentconsole":
        return os.path.join(root, "AgentConsole", "build", "reports", "fsm")
    if sub == "monorepo":
        return os.path.join(root, "build", "reports", "fsm")
    return os.path.join(
        root, "AISDLC_SDD", f"{VERSION_PREFIX}{version}", "build", "reports", "sdd-dogfood"
    )


def render(env: dict[str, str], shell: str) -> str:
    if shell == "json":
        return json.dumps(env, ensure_ascii=False) + "\n"
    lines = []
    for name, value in env.items():
        if shell == "powershell":
            quoted = "'" + value.replace("'", "''") + "'"
            lines.append(f"$env:{name} = {quoted}")
        else:
            quoted = "'" + value.replace("'", "'\\''") + "'"
            lines.append(f"export {name}={quoted}")
    return "\n".join(lines) + "\n"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="產生 SDD 外部專案模式三件組與遙測旗標")
    parser.add_argument("--sub", required=True, choices=SUBS, help="子專案")
    parser.add_argument("--slug", required=True, help="功能代號（小寫英數與連字號，≤30 字元）")
    parser.add_argument("--shell", default="json", choices=SHELLS, help="輸出形態（預設 json）")
    parser.add_argument("--root", default=None, help="monorepo 根（預設：本腳本所在 repo 根）")
    parser.add_argument("--check", action="store_true", help="只驗證狀態檔存在")
    return parser


def main(argv: list[str] | None = None) -> int:
    # R1 的 stdio UTF-8 重設走島內共用入口（`rfc_lifecycle_lint.force_utf8_stdio`），不自帶第 11 份
    # 行內 reconfigure：根層 `tools/tests/test_platform_utils_dedup.py` 對 `AISDLC_SDD/scripts`
    # 的實作數是 shrink-only 棘輪（實測第一次全套即紅 10→11）。
    force_utf8_stdio()
    try:
        args = _build_parser().parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else (0 if code is None else 2)

    reason = validate_slug(args.slug)
    if reason is not None:
        print(f"[sdd_env] ❌ {reason}", file=sys.stderr)
        return 2

    if args.root is None:
        root = str(Path(__file__).resolve().parents[2])
    else:
        root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"[sdd_env] ❌ root 不是目錄：{root}", file=sys.stderr)
        return 2

    latest = sdd_version.latest_version_name(Path(root) / "AISDLC_SDD")
    if latest is None:
        print(f"[sdd_env] ❌ 於 {root} 找不到任何 {VERSION_PREFIX}* 版本目錄", file=sys.stderr)
        return 1
    version = latest[len(VERSION_PREFIX):]

    project = f"{args.sub}-{args.slug}"
    state_dir = state_dir_for(args.sub, root, version)

    if args.check:
        state_file = os.path.join(state_dir, f"FSM-STATE-{project}.yaml")
        if os.path.isfile(state_file):
            print(f"OK {state_file}")
            return 0
        print(f"state_not_found {state_file}", file=sys.stderr)
        return 5

    env = {
        "SDD_ACTIVE_VERSION": version,
        "SDD_PROJECT": project,
        "SDD_STATE_DIR": state_dir,
        "SDD_ENABLE_RULE_FIRE_TELEMETRY": "0",
        "SDD_ENABLE_RULE_CATCH_TELEMETRY": "0",
    }
    text = render(env, args.shell)
    # SCG-4 F-03／NFR-001-3：輸出形態由 --shell 決定、不由平台決定。Windows 文字模式預設把 \n
    # 翻成 \r\n（eval "$(… --shell bash)" 會把 \r 黏進值）⇒ 繞過文字層直接寫 UTF-8 位元組；
    # 串流沒有 .buffer（極少數替身）才退回文字寫入。
    sys.stdout.flush()
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is None:
        sys.stdout.write(text)
    else:
        buffer.write(text.encode("utf-8"))
        buffer.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
