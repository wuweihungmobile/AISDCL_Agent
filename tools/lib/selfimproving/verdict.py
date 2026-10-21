"""SelfImproving 三態判定（TCS-SelfImproving-P2 R89；PRD §9.4〈三態判定表〉）。

純函式：`verify` 與 `check` 的 `events.verdict` 共用。依層判、先中者定案，`reasons` 為**決定層**
的全部成立碼（不跨層）：⓪ 沙盒失敗 → ① 測量無效 → ② 基線不紅 → ③ 套用不綠 → ④ 突變不紅 → ⑤ PASS。
FAIL 只來自測得的失敗（`PATCHED-NOT-GREEN`、`ROLLBACK-DRYRUN-FAILED`），不來自逾時、不來自缺資料。
"""

from __future__ import annotations

_EXPORT_FAIL = ("SANDBOX-EXPORT-FAILED", "SANDBOX-APPLY-TIMEOUT")
# 這三碼無法由其他欄位導出：記錄的 `reasons` 含它即成立
RECORDED_ONLY = ("HELDOUT-EXPOSED", "EXPOSURE-UNKNOWN", "PROBE-TIMEOUT")


def sandbox_layer(sandbox: dict | None) -> tuple[str, list[str]] | None:
    """⓪ 沙盒失敗：三條各自判、全部列出，verdict 取第一個成立者；全無則回 None。"""
    sb = sandbox or {}
    out: list[tuple[str, str]] = []
    if sb.get("applied") is not True:
        fc = sb.get("fail_code")
        out.append(("NE", fc if fc in _EXPORT_FAIL else "SANDBOX-NOT-APPLIED"))
    if sb.get("touched_ok") is False:
        out.append(("NE", "TOUCHED-SUPERSET"))
    if sb.get("rollback_ok") is False:
        out.append(("FAIL", "ROLLBACK-DRYRUN-FAILED"))
    return (out[0][0], [c for _, c in out]) if out else None


def _measure_layer(verify: dict, freeze: dict | None, min_heldout) -> list[str]:
    """① 測量無效 ⇒ NE；`probes_n` 為 0 時只列 `NO-PROBES`。"""
    if verify.get("probes_n") == 0:
        return ["NO-PROBES"]
    recorded = verify.get("reasons") or []
    out = []
    if verify.get("carrier_proof") is not True:
        out.append("CARRIER-PROOF-FAILED")
    if verify.get("heldout_digest") != (freeze or {}).get("digest"):
        out.append("HELDOUT-DIGEST-MISMATCH")
    n = (freeze or {}).get("n")
    if isinstance(min_heldout, int) and (not isinstance(n, int) or n < min_heldout):
        out.append("HELDOUT-TOO-SMALL")
    return out + [c for c in RECORDED_ONLY if c in recorded]


def verdict_of(sandbox: dict | None, verify: dict, freeze: dict | None,
               min_heldout: int | None) -> tuple[str, list[str]]:
    """輸入為對應事件的 dict（`sandbox`＝`app.sandbox`、`verify`＝`app.verify`、`freeze`＝
    `heldout.freeze`），回 `(verdict, reasons)`。"""
    layer0 = sandbox_layer(sandbox)
    if layer0 is not None:
        return layer0
    measured = _measure_layer(verify, freeze, min_heldout)
    if measured:
        return "NE", measured
    if verify.get("baseline_red") is not True:
        return "NE", ["BASELINE-NOT-RED"]
    if verify.get("patched_green") is not True:
        return "FAIL", ["PATCHED-NOT-GREEN"]
    if verify.get("mutated_red") is not True:
        return "NE", ["MUTATION-NOT-RED" if verify.get("mutated_red") is False
                      else "MUTATION-ABSENT"]
    return "PASS", []
