#!/usr/bin/env python3
"""pytest `-rs` 輸出 → skip 分群普查的通用入口（DEF-101-960 題 1 接線）。

誰呼叫：`AISDLC_SDD/scripts/ci-gate.sh` 在 LATEST 軌 pytest 之後，把 tee 下來的 `-rs` 輸出
**檔案路徑**交給本入口（`--tree AISDLC_SDD/fsm_runtime <檔>`；不收 stdin，理由見
`AutoClaude/tools/local_ci_gate.census_only`〈DEF-200-293〉）。判準全住 `skip_group_policy`
（分群／量測完整性／天花板／剖面登記）與 `skip_profile_key`（剖面鍵文法），本檔只組裝它們、
印出與 `local_ci_gate` 同格式的 `[skip census]` 一行；不重寫任何判準。

離開碼三態（同 `local_ci_gate --census-only`）：0 健康／1 真問題（量測塌掉、天花板被突破）／
3 剖面未登記（量測正常，但這個平台沒有人量過健康值＝沒有天花板可比，永遠只出聲）。
另：2＝呼叫端接線錯（未知旗標、樹名不被剖面鍵文法接受）——不降級、一律阻斷。

🔴 D5（掌舵者授權代決）：本機（`CI`／`GITHUB_ACTIONS` 皆未設）一律只出聲不阻斷——rc=1 降為 0
並加印一行；雲端執行者 rc=1 才阻斷。理由：docker 可用性是疑似能力軸、**尚未編碼進剖面鍵**，
開發機與雲端執行者量到的 skip 數未必是同一個母體，拿雲端量到的天花板去管開發機會假紅。
環境變數只在 CLI 邊界（`main`）讀一次，判準函式 `census_verdict` 是純函式。
單測：`AutoClaude/tests/tools/test_local_ci_gate.py`（刻意不放根層 tools/tests）。
"""
from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping
from pathlib import Path

import skip_group_policy
import skip_profile_key

CENSUS_OK = 0
CENSUS_FAIL = 1
CENSUS_PROFILE_UNREGISTERED = 3
CENSUS_WIRING_ERROR = 2

#: 任一有值即視為雲端執行者（GitHub Actions 兩者皆設；本機互動 shell 兩者皆無）。
_CLOUD_ENV_KEYS = ("CI", "GITHUB_ACTIONS")


def census_verdict(
    tree: str, text: str, platform: str | None = None,
) -> tuple[int, list[str]]:
    """純函式：回 `(三態離開碼, 要印的行)`。

    順序是判準的一部分：**量測完整性先於天花板**——塌掉的量測給出的 0 小於任何上限，
    先比天花板等於先給自己蓋一個綠章。樹名／軸不合文法時 `census_profile` 拋 `ValueError`。
    """
    profile = skip_profile_key.census_profile(tree, platform or sys.platform)
    reasons = skip_group_policy.skipped_reasons(text)
    census = skip_group_policy.skip_group_census(reasons)
    lines = [f"[skip census] {profile} 共 {len(reasons)} 支："
             + "／".join(f"{g}={n}" for g, n in census.items())
             + f"／欠債型 {skip_group_policy.open_debt(census)} 支（目標 0）"]
    collapsed = skip_group_policy.skip_measurement_problems(text, len(reasons))
    if collapsed:
        lines.append("❌ skip 量測塌掉——這一份輸出量不到 skip 數，上面那行普查不可信：")
        lines += [f"   - {msg}" for msg in collapsed]
        return CENSUS_FAIL, lines
    problems = skip_group_policy.skip_group_census_problems(profile, census, reasons=reasons)
    if not problems:
        lines += [f"ℹ️ [skip target] {line}"
                  for line in skip_group_policy.skip_target_report(profile, census)]
        return CENSUS_OK, lines
    if not skip_group_policy.profile_registered(profile):
        lines.append("⚠️ 剖面未登記——量測本身正常，但這個平台從來沒有人量過健康值，沒有天花板"
                     "可比（把上面那行的實測值逐格入表即可登記）：")
        lines += [f"   - {msg}" for msg in problems]
        return CENSUS_PROFILE_UNREGISTERED, lines
    lines.append("❌ skip 分群天花板不合格（S3：skipped 數必須有人管）：")
    lines += [f"   - {msg}" for msg in problems]
    return CENSUS_FAIL, lines


def is_cloud_runner(environ: Mapping[str, str]) -> bool:
    return any(environ.get(key) for key in _CLOUD_ENV_KEYS)


def main(argv: list[str] | None = None, environ: Mapping[str, str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pytest_skip_census.py",
        description="pytest -rs 輸出 → skip 分群普查（三態離開碼：0 健康／1 真問題／3 剖面未登記）")
    parser.add_argument("--tree", required=True, help="剖面樹名，例：AISDLC_SDD/fsm_runtime")
    parser.add_argument("log", help="pytest -rs 輸出檔的路徑（不收 stdin）")
    args = parser.parse_args(argv)
    try:
        text = Path(args.log).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        rc, lines = CENSUS_FAIL, [f"❌ [skip census] 讀不到 pytest 輸出檔 {args.log}：{exc}"
                                  "——通道自己壞了，不得當成「沒有 skip」"]
    else:
        try:
            rc, lines = census_verdict(args.tree, text)
        except ValueError as exc:
            print(f"❌ [skip census] 接線錯誤：{exc}", file=sys.stderr)
            return CENSUS_WIRING_ERROR
    print("\n".join(lines))
    if rc == CENSUS_FAIL and not is_cloud_runner(os.environ if environ is None else environ):
        print("ℹ️ [skip census] 本機（CI／GITHUB_ACTIONS 皆未設）只出聲不阻斷（D5）："
              "上面的紅是量測事實、不是放行；雲端執行者才以 rc=1 阻斷")
        return CENSUS_OK
    return rc


if __name__ == "__main__":  # pragma: no cover
    # 本檔的 CLI 印中文與 emoji：非 UTF-8 locale 下 stdout 直接 UnicodeEncodeError。
    from platform_utils import init_utf8_streams

    init_utf8_streams()
    raise SystemExit(main(sys.argv[1:]))
