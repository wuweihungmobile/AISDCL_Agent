"""根層守門工具的 CLI 引數契約 SSOT：**未知旗標一律 rc=2 fail-loud**。

═══════════════════════════════════════════════════════════════════════════════
🔴 為何需要這個模組（R67-D20 的鎖射程缺口，本輪擴張）
═══════════════════════════════════════════════════════════════════════════════
R67-D20 在 `tools/sync_onboarding_baselines.py` 上治好一個具體的假綠：該工具以
`"--flag" in argv` 手搓解析，**未知旗標靜默掉進 default 分支並 rc=0**——於是
`--check-snapsho`（少一個字母）在表② 確實過期的工作樹上回 rc=0，而正確拼法同時
rc=1。當時的修法（argparse ＋ `allow_abbrev=False`）只落在**那一支**，另有
`bootstrap_core.py`／smoke-CI 同步器兩處各自另修一份，共三個站點。

本輪唯讀實測（同一台機器、同一批指令）：根層 `tools/check_*.py` 守門工具中
**多數仍是同一個洞**——`python tools/check_wrapper_thinness.py --bogus-flag-xyz`
rc=0 並印綠燈。也就是說「已知的缺陷類只圈了三個站點」，正是 `DEF-101-757`
「已知的鎖射程缺口不得只以劃界結案」的形態，而且發生在護欄層自己身上。

**射程判準改為行為級、由測試枚舉現查**（`tools/tests/test_check_wrapper_thinness.py`
的 `TestRootGateToolsRejectUnknownFlags`）：任何 `tools/check_*.py` 拿到不在其
宣告集合內的引數就必須 rc≠0。新加一支守門工具若忘了接本模組，該鎖當場紅——
**不靠任何人記得**，這是與「再寫一遍請遵守」的關鍵差別。

刻意**不**在此改用 argparse：本層工具多是「零旗標或一兩個報表旗標」的形狀，
argparse 會逼每支各寫一份 parser 宣告（又是複本），而真正要守的性質只有一條
——**沒被宣告的引數不得被靜默忽略**。本模組只提供那一條。
"""
from __future__ import annotations

import sys
from collections.abc import Sequence

#: 未知旗標的退出碼。取 2 對齊 argparse 慣例（1 保留給「檢查真的不通過」，
#: 兩者混用會讓呼叫端無法分辨「工具拒收引數」與「守門發現違規」）。
UNKNOWN_FLAG_RC = 2


def unknown_argv(args: Sequence[str], known: Sequence[str]) -> tuple[str, ...]:
    """回傳不在 `known` 內的引數（空 tuple＝全部合法）。

    刻意做**精確字串比對**、不接受前綴縮寫：`allow_abbrev` 那條路正是 R67-D20
    實測到 `--check-snapsho` 被「好心地」補全成 `--check-snapshot` 的來源。
    """
    return tuple(a for a in args if a not in known)


def reject_unknown_argv(prog: str, args: Sequence[str],
                        known: Sequence[str]) -> int | None:
    """`None`＝引數全部合法；否則**已印出點名訊息**並回傳呼叫端應直接 `return` 的 rc。

    回 `None` 而不是 `0` 是刻意的：`0` 會與「檢查通過」撞語意，呼叫端一個
    `if rc:` 就把合法路徑吃掉——那又是一個靜默分支。
    """
    bad = unknown_argv(args, known)
    if not bad:
        return None
    accepted = "／".join(known) if known else "（本工具不接受任何旗標）"
    print(
        f"❌ {prog}：未知引數 {' '.join(bad)}——本工具**不會**靜默忽略它並改跑預設"
        f"路徑（那正是 rc=0 假綠的來源，見 R67-D20）。可用引數：{accepted}",
        file=sys.stderr,
    )
    return UNKNOWN_FLAG_RC
