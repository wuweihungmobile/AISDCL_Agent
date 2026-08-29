"""ONBOARDING §7 表② 指紋檢查的 dev_start [6/7] 接線本體（Gap C）。

WHY：表② 指紋 stale 是 pre-push 的**阻斷項**，但此前只有兩個發現時點——人記得跑
`useMacWin.md` 第 7 步那一條、或 push 被擋當場才發現（後者在雙機交替拓撲下是常態：
主要漂移來源是 merge 拉進對面機器的 commit，發生在本輪寫任何程式碼之前）。dev_start
[6/7] 是每次開工必經之地，把毫秒級的 `--check-snapshot` 接進來，讓「本輪要回填」在
開工當下就可見，而不是 commit/push 之後才被 pre-push 擋回來。

形態照 `ci_run_status.py`（DEF-101-758 先例）：邏輯本體住本模組，`dev_start.py` 側
只留 module-level thin adapter（該檔為 SPECIAL_FILES raw-line 棘輪）。純 advisory：
任何無法判定（rc=2、工具缺席、逾時、OSError）一律回 None 靜默降級，不得影響呼叫端
流程或 exit code（同心跳哨兵契約）。

輸出紀律：工具 stdout 的 ℹ️ 段**結構上恆亮**（別平台欄提醒），轉印它只會把 [6/7]
訓練成背景噪音 ⇒ 不轉印；紅時只轉印 stderr 的 ❌ 條列（那才是本機平台欄的判決）。

🔴 葉節點模組：只被 `tools/dev_start.py` import，不 import 其他 tools/lib 模組。
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path


def check_onboarding_snapshot(
    root: Path,
    warn: Callable[[str], None],
) -> str | None:
    """回傳 summary 片段，None＝無法判定、靜默跳過。

    三態：rc=0 → 相符 note；rc=1 → stale note（_warn 出聲，advisory 不擋）；
    rc=2／FileNotFoundError／TimeoutExpired／OSError → None（無法判定：rc=2 是
    工具自身的模式錯誤或平台拒絕，不是指紋判決，轉述它只會誤導）。
    """
    try:
        r = subprocess.run(
            [sys.executable,
             str(root / "tools" / "sync_onboarding_baselines.py"),
             "--check-snapshot"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        # FileNotFoundError 是 OSError 子類；逾時／IO 抖動皆不得讓 dev_start 失敗
        return None
    if r.returncode == 0:
        print("    ✅ ONBOARDING §7 表② 指紋相符（--check-snapshot rc=0）")
        return "表② 指紋相符"
    if r.returncode == 1:
        for line in (r.stderr or "").splitlines():
            if line.strip():
                print(f"    {line}")
        warn("ONBOARDING §7 表② presumed stale——主因是 merge 拉進對面機器的 "
             "commit，見 useMacWin.md 第 7 步／B 段；它是 pre-push 阻斷項，"
             "回填要排在 commit/push 之前")
        return "表② 指紋 stale（見警告）"
    return None
