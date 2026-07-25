"""Phase H M1 / ACT-046 — Sandbox Runner（執行接地抽象層）.

賦予 Evaluator「在隔離環境實際運行 App、捕捉客觀錯誤」的能力（Anthropic
[cite:100,137] Playwright 級實體操作）。落實 SDD_improving_Automation_08.md §G1。

後端抽象（沿用 Phase F M3 LLM Backend 的 Protocol 慣例）：
  - "local"  : LocalStubBackend — 回空觀測，OQS 判 inconclusive（防 false-green）
  - "docker" : DockerBackend — **真實**容器執行（docker run + exit/stderr 捕捉 +
               測試摘要解析 + 硬 timeout 有界停機）；docker 不可用時 raise NotImplementedError
  - "playwright": 瀏覽器 UI driver（stub — node 不在本機，真實執行交 CI/runtime host）

env `SDD_SANDBOX_BACKEND` 切換（預設 "local"）。未配置的遠端後端 raise
NotImplementedError 而非靜默降級（與 multimodal_validator 一致）。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Protocol

from .output_quality_scorer import ExecutionObservation, OQSResult, score
from .state_loader import _sanitize_component

class SandboxPolicyViolation(RuntimeError):
    """Phase I M1 / ACT-060 — 容器安全政策違反（image 不在 allow-list 等）。

    對應 DiagnosticAgent sub_type=sandbox_policy_violation（structural，不可 auto-recover）。
    """


# Phase I M1 / ACT-059：hermetic 重跑硬上限（避免重跑本身變無界 — Rule 9.21）。
FLAKY_RERUN_N = 5

# Phase I M1 / ACT-060：執行器自身安全硬化（PI-4）。預設 image allow-list；
# 可由 env SDD_SANDBOX_IMAGE_ALLOWLIST（逗號分隔）覆寫/擴充。
_DEFAULT_IMAGE_ALLOWLIST = (
    "busybox", "alpine", "python", "python:3.11-slim", "python:3.12-slim",
    "node", "node:20-slim", "node:22-slim", "golang", "ubuntu",
)


def default_image_allowlist() -> tuple:
    raw = os.environ.get("SDD_SANDBOX_IMAGE_ALLOWLIST", "").strip()
    if raw:
        return tuple(x.strip() for x in raw.split(",") if x.strip())
    return _DEFAULT_IMAGE_ALLOWLIST


def _image_base(image: str) -> str:
    """取 image 的 repo 名（去 tag/digest）以比對 allow-list。"""
    name = image.split("@", 1)[0]
    # 保留 repo:tag 形式整體比對，同時也允許純 repo 比對
    return name


def image_allowed(image: Optional[str], *, allowlist: Optional[tuple] = None) -> bool:
    if not image:
        return False
    allow = allowlist if allowlist is not None else default_image_allowlist()
    base_repo = image.split("@", 1)[0].split(":", 1)[0]
    full = image.split("@", 1)[0]
    return full in allow or base_repo in allow


@dataclass
class SecurityProfile:
    """Phase I M1 / ACT-060 — DockerBackend 容器隔離硬化參數（PI-4 self-STRIDE）。

    預設 profile 對「執行自己生成的不可信碼」施加 OS 級 jail：斷網 / 去權限 /
    唯讀 rootfs + 受控 tmpfs / 非 root / 資源上限 / no-new-privileges。
    `network="none"` 為預設；需網路的 UI/integration e2e 由 caller 顯式放寬
    （egress-allowlist 內部橋接），且應走 WAIVER 人工 gate（§8 風險表）。

    **seccomp（syscall 過濾）**：Docker 在非 `--privileged` 下**預設已自動套用**內建
    seccomp profile（封鎖 ~44 個危險 syscall），本框架**不停用之**（從不發出
    `--security-opt seccomp=unconfined`），故預設安全行為已涵蓋 syscall 過濾。
    `seccomp_profile` 欄位僅供需要**自訂**更嚴格 profile 的場景使用：當設定為
    某 json 路徑（或 "default"）時，`docker_args()` 會發出
    `--security-opt seccomp=<profile>`；預設 `None` 表示沿用 Docker 內建 default
    seccomp，不額外發出旗標（向後相容，不改變既有行為）。
    """
    network: str = "none"           # --network none
    cap_drop_all: bool = True       # --cap-drop ALL
    read_only: bool = True          # --read-only + --tmpfs /tmp
    tmpfs: str = "/tmp"
    user: str = "65534:65534"       # nobody:nogroup（非 root）
    memory: str = "512m"            # --memory
    pids_limit: int = 256           # --pids-limit
    cpus: str = "1.0"               # --cpus
    no_new_privileges: bool = True  # --security-opt no-new-privileges
    enforce_image_allowlist: bool = True
    # ACT-060：自訂 seccomp profile（None=沿用 Docker 內建 default seccomp，
    # 已啟用且不被本框架停用）；設定 json 路徑或 "default" 時才發出旗標。
    seccomp_profile: Optional[str] = None

    def docker_args(self) -> List[str]:
        args: List[str] = []
        if self.network:
            args += ["--network", self.network]
        if self.cap_drop_all:
            args += ["--cap-drop", "ALL"]
        if self.read_only:
            args += ["--read-only", "--tmpfs", self.tmpfs]
        if self.user:
            args += ["--user", self.user]
        if self.memory:
            args += ["--memory", self.memory]
        if self.pids_limit:
            args += ["--pids-limit", str(self.pids_limit)]
        if self.cpus:
            args += ["--cpus", self.cpus]
        if self.no_new_privileges:
            args += ["--security-opt", "no-new-privileges"]
        # ACT-060：自訂 seccomp 才顯式發旗標；預設 None 沿用 Docker 內建 default
        # seccomp profile（已啟用），不發出 --security-opt seccomp=unconfined。
        if self.seccomp_profile:
            args += ["--security-opt", f"seccomp={self.seccomp_profile}"]
        return args


DEFAULT_SECURITY_PROFILE = SecurityProfile()

# 測試摘要解析（pytest / 通用 "N passed, M failed"）
_PASSED_RE = re.compile(r"(\d+)\s+passed")
_FAILED_RE = re.compile(r"(\d+)\s+failed")
_ERROR_LINE_RE = re.compile(r"\b(error|exception|traceback|panic|fatal)\b", re.IGNORECASE)


def parse_test_output(stdout: str, stderr: str, returncode: int) -> ExecutionObservation:
    """從容器真實輸出解析客觀觀測（純函式，可單測，不依賴 docker）。"""
    blob = f"{stdout}\n{stderr}"
    passed_m = _PASSED_RE.search(blob)
    failed_m = _FAILED_RE.search(blob)
    passed = int(passed_m.group(1)) if passed_m else 0
    failed = int(failed_m.group(1)) if failed_m else 0
    total = passed + failed
    # runtime_errors：stderr 中錯誤關鍵字行數（exit!=0 至少記 1）
    err_lines = sum(1 for ln in stderr.splitlines() if _ERROR_LINE_RE.search(ln))
    if returncode != 0 and err_lines == 0:
        err_lines = 1
    return ExecutionObservation(
        tests_total=total,
        tests_passed=passed,
        runtime_errors=err_lines,
        nonzero_exit=(returncode != 0),
    )


@dataclass
class SandboxSpec:
    """要在沙箱中執行的目標描述（由 Test-Contract 推導）。"""
    app_id: str
    start_cmd: Optional[str] = None          # e.g. "docker compose up" / "python app.py"
    health_url: Optional[str] = None
    ui_steps: List[str] = field(default_factory=list)   # Playwright 操作腳本步驟
    perf_pbs_ref: Optional[str] = None
    timeout_sec: int = 120                    # 硬 timeout — 保有界停機
    # Phase H ACT-046 docker 後端：實跑容器所需
    image: Optional[str] = None              # e.g. "busybox" / "myapp:test"
    test_cmd: Optional[List[str]] = None     # 容器內測試命令（list 形式，傳給 docker run）
    # Phase I M5 / ACT-070：艦隊並行的 container/port namespacing（N 軌同跑不撞）
    track_id: Optional[str] = None
    base_port: int = 8000                    # 軌道 port 起點；實際 port = base_port + track 偏移


def track_port(base_port: int, track_id: Optional[str]) -> int:
    """ACT-070：由 track_id 決定性映射到唯一 port 偏移（避免 N 軌撞 port）。"""
    if not track_id:
        return base_port
    # 確定性雜湊（不依賴 PYTHONHASHSEED）→ 0..99 偏移
    h = 0
    for ch in str(track_id):
        h = (h * 131 + ord(ch)) % 100
    return base_port + h


def track_container_name(app_id: str, track_id: Optional[str]) -> str:
    """ACT-070：軌道專屬容器名（--name），N 軌並行不撞名。"""
    base = f"sdd-{app_id}".replace("/", "-")
    return f"{base}-{track_id}" if track_id else base


class SandboxBackend(Protocol):
    name: str
    def run(self, spec: SandboxSpec) -> ExecutionObservation: ...


class LocalStubBackend:
    """預設後端。在缺 docker/playwright 的環境下回傳「中性觀測」，

    讓上層流程（FSM、OQS）可端到端測試而不依賴外部執行器。真實執行由
    CI / runtime host 注入 record_observation() 的觀測覆寫（見 SandboxRunner）。
    """
    name = "local-stub"

    def run(self, spec: SandboxSpec) -> ExecutionObservation:
        # 回傳「空觀測」（無任何正向/失敗訊號）。OQS 對此一律判 verdict=inconclusive
        # （passed=False），絕不放行 pass — Evaluator 必須注入真實觀測才能裁決
        # （H-1 修：防 stub 零觀測 false green，守 Phase H 執行接地契約）。
        return ExecutionObservation()


def docker_available() -> bool:
    """docker CLI 存在且 daemon 可連線。"""
    if shutil.which("docker") is None:
        return False
    try:
        r = subprocess.run(
            ["docker", "info"], capture_output=True, timeout=10, check=False,
        )
        return r.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


class DockerBackend:
    """Phase H ACT-046 真實執行接地後端 — 在隔離容器中實跑 App 並捕捉客觀錯誤。

    `docker run --rm <hardened-profile> <image> <test_cmd>`：真實啟動容器、
    捕捉 exit code / stderr，解析測試摘要為 ExecutionObservation。硬 timeout
    （spec.timeout_sec）保有界停機。

    Phase I M1 / ACT-060：預設套用 DEFAULT_SECURITY_PROFILE（斷網 / 去權限 /
    唯讀 / 非 root / 資源上限），並對 image 做 allow-list 檢查。
    `profile` 可注入以放寬（如 UI e2e 需網路），但放寬應走 WAIVER 人工 gate。
    """
    name = "docker"

    def __init__(self, profile: Optional[SecurityProfile] = None):
        self.profile = profile or DEFAULT_SECURITY_PROFILE

    def run(self, spec: SandboxSpec) -> ExecutionObservation:
        if not spec.image:
            raise ValueError("DockerBackend 需要 spec.image（要實跑的容器映像）")
        if self.profile.enforce_image_allowlist and not image_allowed(spec.image):
            raise SandboxPolicyViolation(
                f"image {spec.image!r} 不在 allow-list {default_image_allowlist()}；"
                "拒絕執行不可信映像（ACT-060 PI-4）"
            )
        cmd = ["docker", "run", "--rm"]
        # Phase I M5 / ACT-070：軌道專屬容器名（N 軌並行不撞名）。
        cmd += ["--name", track_container_name(spec.app_id, spec.track_id)]
        cmd += self.profile.docker_args() + [spec.image]
        if spec.test_cmd:
            cmd += list(spec.test_cmd)
        elif spec.start_cmd:
            cmd += ["sh", "-c", spec.start_cmd]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=spec.timeout_sec, check=False,
            )
        except subprocess.TimeoutExpired:
            # 逾時 = runtime 故障（保有界停機，不無限等待）
            return ExecutionObservation(
                tests_total=0, tests_passed=0, runtime_errors=1, nonzero_exit=True,
            )
        return parse_test_output(proc.stdout or "", proc.stderr or "", proc.returncode)


def _docker_factory():
    if not docker_available():
        raise NotImplementedError(
            "sandbox backend 'docker' 不可用（docker CLI 缺失或 daemon 未運行）；"
            "真實執行須在已啟動 docker 的環境，或注入 observation 覆寫。"
        )
    return DockerBackend()


class _UnconfiguredRemoteBackend:
    def __init__(self, name: str):
        self.name = name

    def run(self, spec: SandboxSpec) -> ExecutionObservation:
        raise NotImplementedError(
            f"sandbox backend '{self.name}' 未配置執行器（playwright 不在此環境）；"
            "真實執行須在 CI / runtime host 進行，或注入 observation 覆寫。"
        )


_BACKENDS = {
    "local": LocalStubBackend,
    "docker": _docker_factory,
    "playwright": lambda: _UnconfiguredRemoteBackend("playwright"),
}


def get_backend(name: Optional[str] = None) -> SandboxBackend:
    key = (name or os.environ.get("SDD_SANDBOX_BACKEND", "local")).strip().lower()
    factory = _BACKENDS.get(key)
    if factory is None:
        raise ValueError(f"unknown sandbox backend: {key!r}; expected one of {sorted(_BACKENDS)}")
    return factory()


@dataclass
class SandboxResult:
    backend: str
    observation: ExecutionObservation
    oqs: OQSResult
    logs_path: Optional[str] = None


def evaluate(
    spec: SandboxSpec,
    *,
    backend: Optional[str] = None,
    observation_override: Optional[ExecutionObservation] = None,
    spec_defect: bool = False,
) -> SandboxResult:
    """執行沙箱並計算 OQS。

    `observation_override` 允許 CI / runtime host 注入真實觀測（取代 stub）。
    `spec_defect=True` 代表執行已證明規格矛盾 → OQS verdict 強制 spec_defect。
    """
    be = get_backend(backend)
    obs = observation_override if observation_override is not None else be.run(spec)
    oqs = score(obs, spec_defect=spec_defect)
    return SandboxResult(backend=be.name, observation=obs, oqs=oqs)


# ===================== Phase I M1 / ACT-059 — Hermetic 重跑取共識 =====================
# 真實執行是非確定的（flaky test / 時間相依 / 並發 race）。單發執行會讓
# EXECUTION_EVALUATION 的 retry budget 被「本質隨機的訊號」消耗，且
# TrajectoryPredictor 的 S1（同 pattern 連續失敗）會誤判 flaky 為穩定失敗。
# 解法：同輸入重跑 N 次取共識 —— 全 pass=PASS / 全 fail=FAIL / 混合=FLAKY
# （第三 verdict，隔離不計分、不進 retry 迴圈、不污染 OQS 校準）。
import datetime as _dt  # noqa: E402


def _flaky_report_dir() -> Path:
    from .state_loader import REPO_ROOT
    return REPO_ROOT / "build" / "reports" / "eval"


@dataclass
class HermeticResult:
    """同輸入重跑 N 次的共識結果。

    verdict ∈ {"PASS", "FAIL", "FLAKY"}：
      - PASS  → 全部 run 均 OQS pass（確定性成功 → 交 OQS 正式裁決）
      - FAIL  → 全部 run 均非 pass（確定性失敗）
      - FLAKY → 混合（非確定）→ 隔離，第三 verdict，不計分、不進 retry
    """
    verdict: str
    runs: int
    pass_count: int
    fail_count: int
    observations: List[ExecutionObservation] = field(default_factory=list)
    oqs: Optional[OQSResult] = None      # 僅 PASS/FAIL 時填（共識觀測的 OQS）
    flaky_report_path: Optional[str] = None

    @property
    def is_flaky(self) -> bool:
        return self.verdict == "FLAKY"

    def to_exec_verdict(self) -> str:
        """映射到 EXECUTION_EVALUATION 出口 verdict（FLAKY 不在此 — 由 caller 隔離處理）。"""
        if self.verdict == "PASS":
            return self.oqs.verdict if self.oqs else "pass"
        if self.verdict == "FAIL":
            return self.oqs.verdict if self.oqs else "runtime_fail"
        raise ValueError("FLAKY verdict 不可映射為 exec verdict；應隔離（不進 retry 迴圈）")


def _run_passed(obs: ExecutionObservation, *, spec_defect: bool) -> bool:
    return score(obs, spec_defect=spec_defect).passed


def evaluate_hermetic(
    spec: SandboxSpec,
    *,
    backend: Optional[str] = None,
    n: int = FLAKY_RERUN_N,
    observation_overrides: Optional[List[ExecutionObservation]] = None,
    spec_defect: bool = False,
    write_report: bool = True,
    today: Optional[str] = None,
    report_dir: Optional[Path] = None,
) -> HermeticResult:
    """同 SandboxSpec 重跑 n 次取共識（hermetic）。

    `observation_overrides`（長度需 = n）允許注入每次 run 的觀測供確定性測試
    （避免依賴真實 flaky 容器）。否則呼叫 backend.run() n 次。

    硬上限 n ≤ FLAKY_RERUN_N（避免重跑本身變無界，守有界停機）。
    """
    if n < 1:
        raise ValueError("n 必須 ≥ 1")
    if n > FLAKY_RERUN_N:
        n = FLAKY_RERUN_N  # 硬上限封頂（Rule 9.21）

    observations: List[ExecutionObservation] = []
    if observation_overrides is not None:
        if len(observation_overrides) < n:
            raise ValueError(f"observation_overrides 長度 {len(observation_overrides)} < n={n}")
        observations = list(observation_overrides[:n])
    else:
        be = get_backend(backend)
        for _ in range(n):
            observations.append(be.run(spec))

    passes = [_run_passed(o, spec_defect=spec_defect) for o in observations]
    pass_count = sum(1 for p in passes if p)
    fail_count = n - pass_count

    if pass_count == n:
        verdict = "PASS"
    elif pass_count == 0:
        verdict = "FAIL"
    else:
        verdict = "FLAKY"

    result = HermeticResult(
        verdict=verdict, runs=n, pass_count=pass_count, fail_count=fail_count,
        observations=observations,
    )

    if verdict in {"PASS", "FAIL"}:
        # 共識觀測：PASS 取第一筆（皆 pass）；FAIL 取第一筆（皆 fail）。
        result.oqs = score(observations[0], spec_defect=spec_defect)
    else:
        # FLAKY：隔離不計分；寫報告供人工取得確定性 repro。
        if write_report:
            result.flaky_report_path = _write_flaky_report(
                spec, result, today=today, report_dir=report_dir
            )
    return result


def _write_flaky_report(
    spec: SandboxSpec,
    result: HermeticResult,
    *,
    today: Optional[str] = None,
    report_dir: Optional[Path] = None,
) -> Optional[str]:
    try:
        import yaml  # type: ignore
    except Exception:  # noqa: BLE001
        return None
    target = report_dir or _flaky_report_dir()
    target.mkdir(parents=True, exist_ok=True)
    date = today or _dt.date.today().isoformat()
    # Path traversal defence: spec.app_id is externally-controlled (R44
    # cross-platform review fix; see state_loader.py _sanitize_component()).
    path = target / f"FLAKY-{date}-{_sanitize_component(spec.app_id)}.yaml"
    doc = {
        "app_id": spec.app_id,
        "image": spec.image,
        "test_cmd": spec.test_cmd,
        "runs": result.runs,
        "pass_count": result.pass_count,
        "fail_count": result.fail_count,
        "verdict": "FLAKY",
        "note": (
            "同輸入重跑取共識為非確定（flaky）。已隔離、不計入 OQS、不消耗 "
            "EXECUTION_EVALUATION retry budget。請提供確定性 repro 或修復隨機性後重試。"
        ),
        "recorded_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)
    tmp.replace(path)
    return str(path)
