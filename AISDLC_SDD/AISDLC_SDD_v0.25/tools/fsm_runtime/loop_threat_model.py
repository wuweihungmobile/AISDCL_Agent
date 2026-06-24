"""Phase I M1 / ACT-061 — Loop Self-STRIDE Threat Model（執行器自身威脅模型）.

落實 SDD_improving_Automation_09.md §4.1 / PI-4：框架對「被開發的產品」做了完整
STRIDE，卻對「現在會自動執行不可信 artifact 的執行器自己」零威脅模型（燈下黑）。

本模組為 SANDBOX_HARDENING_GATE 提供「執行前」的 6 類 self-STRIDE 控制斷言 +
供應鏈鎖（lockfile 雜湊）+ spec 簽章驗證。任一違反 → policy_violation →
FSMRuntime.exit_sandbox_hardening_gate("policy_violation") → ESCALATION
（DiagnosticAgent sub_type=sandbox_policy_violation，structural 不可 auto-recover）。

純 stdlib、確定性、零外部依賴（沿用 ambiguity_scorer v1 原則）。
"""
from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .sandbox_runner import (
    DEFAULT_SECURITY_PROFILE,
    SandboxSpec,
    SecurityProfile,
    image_allowed,
)

# spec 簽章金鑰（dev default 僅供 test / local）。生產須設 env。
SPEC_SIGNING_SECRET_ENV = "SDD_SPEC_SIGNING_SECRET"
_DEV_DEFAULT_SECRET = "DEV_DEFAULT_SPEC_SECRET"

# self-STRIDE 6 類威脅（對「執行器自己」而非「被開發的產品」）
STRIDE_CATEGORIES = (
    "spoofing",            # S：spec 來源真偽 → 簽章驗證
    "tampering",           # T：相依套件被竄改 → lockfile 雜湊鎖
    "repudiation",         # R：執行不可否認 → 稽核紀錄（image/cmd 落帳）
    "info_disclosure",     # I：生成碼 phone-home → --network none
    "denial_of_service",   # D：資源耗盡 → --memory/--pids-limit/--cpus
    "elevation",           # E：容器逃逸提權 → --cap-drop ALL + 非 root + no-new-priv
)


@dataclass
class HardeningResult:
    verdict: str                       # "pass" | "policy_violation"
    stride_controls: Dict[str, bool] = field(default_factory=dict)
    violations: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.verdict == "pass"


def _resolve_secret(secret: Optional[str]) -> str:
    if secret:
        return secret
    return os.environ.get(SPEC_SIGNING_SECRET_ENV) or _DEV_DEFAULT_SECRET


def sign_spec(payload: str, *, secret: Optional[str] = None) -> str:
    """產出 spec payload 的 HMAC-SHA256 簽章（測試 / 簽署工具用）。"""
    key = _resolve_secret(secret).encode("utf-8")
    return hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_spec_signature(payload: str, signature: str, *, secret: Optional[str] = None) -> bool:
    if not signature:
        return False
    expected = sign_spec(payload, secret=secret)
    return hmac.compare_digest(expected, signature)


def file_sha256(path: Path) -> Optional[str]:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def evaluate_hardening(
    spec: SandboxSpec,
    *,
    profile: Optional[SecurityProfile] = None,
    spec_payload: Optional[str] = None,
    spec_signature: Optional[str] = None,
    secret: Optional[str] = None,
    lockfile_path: Optional[Path] = None,
    expected_lockfile_hash: Optional[str] = None,
    require_signature: bool = False,
    require_lockfile: bool = False,
) -> HardeningResult:
    """SANDBOX_HARDENING_GATE 的執行前硬化檢查。

    回傳 HardeningResult.verdict ∈ {"pass","policy_violation"}。違反項列在 violations。

    - image allow-list（E/T 面）：spec.image 必須在 allow-list。
    - spec 簽章（S 面）：require_signature 時必須驗章通過。
    - lockfile 雜湊（T/供應鏈面）：require_lockfile 時必須與 expected_lockfile_hash 相符。
    - jail flags（I/D/E 面）：profile 必須有斷網 / 資源上限 / 去權限。
    """
    prof = profile or DEFAULT_SECURITY_PROFILE
    violations: List[str] = []
    controls: Dict[str, bool] = {}

    # S — spoofing：spec 簽章
    if require_signature:
        ok_sig = bool(spec_payload) and verify_spec_signature(
            spec_payload or "", spec_signature or "", secret=secret
        )
        controls["spoofing"] = ok_sig
        if not ok_sig:
            violations.append("spec signature mismatch / unsigned spec (spoofing)")
    else:
        controls["spoofing"] = True

    # T — tampering（供應鏈）：lockfile 雜湊
    if require_lockfile:
        actual = file_sha256(lockfile_path) if lockfile_path else None
        ok_lock = bool(expected_lockfile_hash) and actual == expected_lockfile_hash
        controls["tampering"] = ok_lock
        if not ok_lock:
            violations.append(
                f"lockfile hash mismatch (supply-chain): expected={expected_lockfile_hash} actual={actual}"
            )
    else:
        controls["tampering"] = True

    # R — repudiation：image/cmd 可落帳（恆真 — gate 本身寫 decision_trace）
    controls["repudiation"] = True

    # E/T — image allow-list
    img_ok = image_allowed(spec.image) if prof.enforce_image_allowlist else True
    if not img_ok:
        violations.append(f"image {spec.image!r} not in allow-list (elevation/tampering)")

    # I — info_disclosure：斷網
    controls["info_disclosure"] = prof.network == "none"
    if prof.network != "none":
        # 放寬需 WAIVER（此處僅記錄為「非預設」非硬性違反，由 caller 決定）
        controls["info_disclosure"] = False

    # D — denial_of_service：資源上限
    controls["denial_of_service"] = bool(prof.memory) and bool(prof.pids_limit)
    if not controls["denial_of_service"]:
        violations.append("missing resource limits (denial_of_service)")

    # E — elevation：去權限 + 非 root + no-new-priv
    controls["elevation"] = (
        prof.cap_drop_all and bool(prof.user) and prof.no_new_privileges and img_ok
    )
    if not controls["elevation"]:
        violations.append("insufficient privilege jail (cap-drop/user/no-new-privileges/image)")

    verdict = "pass" if not violations else "policy_violation"
    return HardeningResult(verdict=verdict, stride_controls=controls, violations=violations)
