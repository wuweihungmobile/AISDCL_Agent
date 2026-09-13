"""DEF-200-274 第十輪批評缺口 2 — `ci-gate.sh` xdist 判準必須是「允許清單」而非
「排除清單」，回歸鎖。

WHY（測意圖非僅行為，Rule 9）：`tools/fsm_runtime/snapshot.py::save_abort_report()`
的 `_atomic_write_text` 競態修法**僅存在於 LATEST**（`AISDLC_SDD_v0.30`）；凍結基線
`AISDLC_SDD_v0.01` 與其後到 LATEST 之間的每一個中間歷史版，其 `snapshot.py` 仍是舊版
固定檔名 `.tmp`，與 v0.01 同型競態尚未修好——而依 `AISDLC_SDD/CLAUDE.md`〈版本狀態〉表，
中間歷史版**不可原地改**，無法就地補上這個修法。

若 `ci-gate.sh` 的 `XDIST_ARGS` 判準寫成排除清單（`"${VER}" != "${FROZEN_BASELINE}"`
就開 xdist），`SDD_FW_VERSION` debug 逃生口一旦指到任一中間歷史版，就會誤幫一支
未修競態的版本開多 worker，把「這支版本本來就會競態失敗」誤判成「這輪改動造成的
回歸」——這正是第十輪批評缺口 2 指出、且第九輪一度發生過的判準退化形態。本鎖把
判準釘死為允許清單（`"${VER}" == "${LATEST}"` 才開 xdist），並反向鎖死排除清單
寫法不得復發：只有 LATEST 這一版保證帶著已修好的 `_atomic_write_text`，凍結基線與
全部中間歷史版一律序列執行。

另附一道姊妹鎖：`scripts/tests/`（共享 CI infra，版本無關、不含 FSM runtime 那段
共享 tmp 檔競態）的 pytest 呼叫，必須**無條件**帶 `-n auto --dist worksteal`
——它不受上述版本判準約束，是與 FSM runtime 段落刻意不同的另一段。

安家位置：本鎖原生於 `AISDLC_SDD/scripts/tests/`，因該樹是 ONBOARDING 指紋樹（多一
檔即需重做乾淨 venv 回填）而遷入根層 `tools/tests/`——比照 test_bash32_compat.py
既有的「根層測試讀 AISDLC_SDD 腳本」先例，不影響 ci-gate.sh 的凍結／可改邊界判斷。
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

# tools/tests → tools → 根目錄（REPO_ROOT）；ci-gate.sh 位於 AISDLC_SDD/scripts/ 下。
REPO_ROOT = Path(__file__).resolve().parents[2]
CI_GATE = REPO_ROOT / "AISDLC_SDD" / "scripts" / "ci-gate.sh"

# 只認允許清單這一種寫法；排除清單（無論寫成 `!=` 或反過來的 `not ==`）都不合格。
_ALLOWLIST_CONDITION = '"${VER}" == "${LATEST}"'
_EXCLUDELIST_CONDITION = '"${VER}" != "${FROZEN_BASELINE}"'


def _ci_gate_text() -> str:
    assert CI_GATE.is_file(), f"ci-gate.sh 不存在：{CI_GATE}"
    return CI_GATE.read_text(encoding="utf-8")


def _xdist_args_block(text: str) -> str:
    """擷取「宣告 XDIST_ARGS → if 判準 → 賦值成多 worker 旗標」這一整塊原文。

    以 `local XDIST_ARGS=""` 為起點、`XDIST_ARGS="-n auto --dist worksteal"` 為訖點，
    中間必須恰好是一句 `if [[ <條件> ]]; then`——比對嵌入本檔而非重新發明正則，
    是為了讓斷言貼著 ci-gate.sh 的真實原文，結構一旦被改寫（例如拆成多個 if/elif）
    本鎖會直接找不到區塊而 fail-loud，不會誤判為「條件仍合格」。
    """
    m = re.search(
        r'local XDIST_ARGS=""\s*\n'
        r'\s*if \[\[ (?P<cond>.*?) \]\]; then\s*\n'
        r'\s*XDIST_ARGS="-n auto --dist worksteal"\s*\n'
        r'\s*fi',
        text,
    )
    assert m, (
        "ci-gate.sh 找不到 FSM runtime 段落的 XDIST_ARGS 判準區塊——結構已變動，"
        "請同步本鎖"
    )
    return m.group("cond")


class CiGateXdistAllowlistTest(unittest.TestCase):
    """`ci-gate.sh` xdist 判準必須是允許清單，且姊妹段落必須無條件帶 xdist。"""

    def test_xdist_allowlist_condition_gates_on_latest_only(self) -> None:
        """FSM runtime 段落的 XDIST_ARGS 判準必須逐字是允許清單 `VER == LATEST`。"""
        cond = _xdist_args_block(_ci_gate_text())
        self.assertEqual(
            cond, _ALLOWLIST_CONDITION,
            f"ci-gate.sh 的 XDIST_ARGS 判準應為允許清單 {_ALLOWLIST_CONDITION!r}"
            f"（只有 LATEST 保證帶 _atomic_write_text 修法），實得 {cond!r}——"
            "疑似退回排除清單寫法，會誤幫未修競態的中間歷史版開多 worker（判準退化復發）",
        )

    def test_xdist_excludelist_condition_does_not_reappear(self) -> None:
        """反向鎖：舊排除清單條件字面值不得出現在 XDIST_ARGS 判準區塊內。

        刻意只掃區塊本身、不對整份 ci-gate.sh 做全文禁字——`"${LATEST}" != "${FROZEN_
        BASELINE}"` 是版本迴圈另一段（決定 FW_VERSIONS 是否納入 LATEST）的合法既有寫法，
        對整檔禁字會誤傷那一句無關的既有邏輯。
        """
        block_cond = _xdist_args_block(_ci_gate_text())
        self.assertNotIn(
            _EXCLUDELIST_CONDITION, block_cond,
            f"XDIST_ARGS 判準區塊內出現排除清單字面值 {_EXCLUDELIST_CONDITION!r}"
            "——即使不是唯一條件，只要排除清單重新混入判準就已是同型缺陷復發",
        )

    def test_shared_infra_pytest_call_always_carries_xdist(self) -> None:
        """`scripts/tests/`（共享 CI infra）呼叫端必須無條件帶 `-n auto --dist worksteal`。

        與 FSM runtime 段落不同：`scripts/tests/` 不含 `snapshot.py` 那段共享 tmp 檔
        競態（ci-gate.sh 本檔第三個呼叫端註解已現查記載），版本無關，故不套用上面的
        允許清單判準——它應恆帶 xdist 旗標，不因 VER/LATEST 而異。
        """
        text = _ci_gate_text()
        calls = [
            ln for ln in text.splitlines()
            if "python -m pytest scripts/tests/" in ln and not ln.lstrip().startswith("#")
        ]
        self.assertTrue(calls, "ci-gate.sh 找不到呼叫 scripts/tests/ 的 pytest 陳述式——結構已變動")
        self.assertEqual(
            len(calls), 1,
            f"預期恰有 1 處呼叫 scripts/tests/ 的 pytest（本鎖的姊妹段落假設），實得 "
            f"{len(calls)} 處：{calls}",
        )
        self.assertIn(
            "-n auto --dist worksteal", calls[0],
            f"scripts/tests/ 的 pytest 呼叫應無條件帶 `-n auto --dist worksteal`，"
            f"實得：{calls[0].strip()!r}",
        )


if __name__ == "__main__":
    unittest.main()
