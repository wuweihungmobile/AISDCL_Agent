"""備份控制面的部署靜態鎖（TCS-SysAdminBackup-20261027：S 包階一的 PY 載具）。

涵蓋 AT-BK-08-3-2、AT-BK-09-3-E-1、AT-BK-09-4-1、AT-BK-09-5-E-2、AT-BK-09-6-1、AT-BK-09-6-2、
AT-BK-09-6-E-1、AT-BK-09-7-2、AT-BK-09-7-E-1、AT-BK-10-4-2。

只讀檔、不起 Docker：compose 的卷與掛載旗標、sidecar 的 Dockerfile／entrypoint／crontab／腳本文字、
Prometheus 規則與其載入接線、README 的條數宣稱。每個檢查都是純函式（輸入為解析後的結構或文字，輸出為
問題清單）：真檔必須回空、各壞變體必須逐一回非空——鎖不得空過。先例：test_si_deploy_config.py 的
audit_bind_problems、test_deploy_config.py 的 slo 規則鎖。

🔴 階段說明（備份案實作期主控代決 2026-10-28 第 2 點）：兩個控制面卷在階一就一起掛上
（sidecar 與 backend 都掛 /backup-out 與 /backup-req），所以 compose 的頂層卷數在這裡釘 14
（TCS 字面的「階一 13、階二 14」以勘誤追認）；backend 映像的 /backup-req 目錄
（backend/Dockerfile）屬階二，本檔不查。
"""
from __future__ import annotations

import copy
import re
import shlex
from pathlib import Path
from typing import Any

import pytest
import yaml

CONSOLE_DIR = Path(__file__).resolve().parents[2]            # <monorepo>/AgentConsole
COMPOSE = CONSOLE_DIR / "docker-compose.yml"
PGBACKREST_DIR = CONSOLE_DIR / "docker" / "pgbackrest"
SCRIPTS_DIR = PGBACKREST_DIR / "scripts"
PROMETHEUS_DIR = CONSOLE_DIR / "docker" / "prometheus"
README = CONSOLE_DIR / "docker" / "README.md"

pytestmark = pytest.mark.skipif(
    not COMPOSE.is_file(), reason="不在 monorepo 內（例如只有 engine-bridge 目錄的 checkout）")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _compose() -> dict[str, Any]:
    return yaml.safe_load(_read(COMPOSE))


def _service_block(compose_text: str, name: str) -> str:
    """`  <name>:` 到下一個同層服務之前（先例：test_deploy_config.py）。"""
    match = re.search(
        rf"^  {re.escape(name)}:\n(.*?)(?=^  [A-Za-z0-9_-]+:\n|^[a-z#]|\Z)",
        compose_text, flags=re.S | re.M)
    assert match, f"docker-compose.yml 找不到服務 {name}"
    return match.group(1)


def _code_lines(text: str) -> list[str]:
    """去掉整行註解與空行（腳本與 Dockerfile 的靜態判準只看真的會執行的行）。"""
    return [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]


def _joined(text: str) -> str:
    """把行尾反斜線續行接成一行（Dockerfile 的 RUN 與 shell 指令都用它）。"""
    return re.sub(r"\\\n\s*", " ", text)


# ── compose 的卷與掛載旗標 ───────────────────────────────────────────────────────────────────
EXISTING_VOLUMES = frozenset({
    "pg_data", "pg_replica_data", "pg_wal_archive", "pg_backup", "pg_socket", "redis_data",
    "app_logs", "nginx_certs", "engine_workspace", "minio_data", "minio_certs", "prometheus_data"})
OUT_VOLUME, REQ_VOLUME = "backup_out", "backup_req"
OUT_DIR, REQ_DIR = "/backup-out", "/backup-req"
BACKUP_VOLUMES = frozenset({OUT_VOLUME, REQ_VOLUME})


def _mounts(service: dict[str, Any]) -> list[tuple[str, str, frozenset[str]]]:
    """服務的掛載 ＝ [(來源, 容器內目標, 旗標集合)]；短語法與長語法都認。旗標只取 ro、nocopy。"""
    out: list[tuple[str, str, frozenset[str]]] = []
    for vol in service.get("volumes") or []:
        if isinstance(vol, dict):
            flags = set()
            if vol.get("read_only") is True:
                flags.add("ro")
            if (vol.get("volume") or {}).get("nocopy") is True:
                flags.add("nocopy")
            out.append((str(vol.get("source", "")), str(vol.get("target", "")), frozenset(flags)))
            continue
        match = re.match(r"^(?P<src>.*?):(?P<tgt>/[^:]*)(?::(?P<modes>[\w,]+))?$", str(vol))
        if match:
            modes = {m for m in (match["modes"] or "").split(",") if m}
            out.append((match["src"], match["tgt"], frozenset(modes & {"ro", "nocopy"})))
    return out


def _env_of(service: dict[str, Any]) -> dict[str, str]:
    env = service.get("environment") or {}
    if isinstance(env, list):
        env = dict(item.split("=", 1) for item in env)
    return {str(k): "" if v is None else str(v) for k, v in env.items()}


#: (卷, 容器內目標, 服務, 必備旗標, 禁用旗標)
#: 寫入端不帶 ro／nocopy、讀取端一律 ro＋nocopy（README〈4.6〉）
MOUNT_RULES: tuple[tuple[str, str, str, frozenset[str], frozenset[str]], ...] = (
    (OUT_VOLUME, OUT_DIR, "pgbackrest", frozenset(), frozenset({"ro", "nocopy"})),
    (OUT_VOLUME, OUT_DIR, "backend", frozenset({"ro", "nocopy"}), frozenset()),
    (REQ_VOLUME, REQ_DIR, "backend", frozenset(), frozenset({"ro", "nocopy"})),
    (REQ_VOLUME, REQ_DIR, "pgbackrest", frozenset({"ro", "nocopy"}), frozenset()),
)
BACKEND_ENV = {"CONSOLE_BACKUP_OUT_DIR": OUT_DIR, "CONSOLE_BACKUP_REQ_DIR": REQ_DIR}


def backup_mount_problems(compose: dict[str, Any]) -> list[str]:
    """兩個控制面卷的部署前提（PRD §9.1 B′）：頂層宣告為 `driver: local` 的具名卷（不是 bind）；
    寫入端（sidecar 寫 backup_out、backend 寫 backup_req）不帶 ro、不帶 nocopy——卷根的擁有者
    由寫入端映像定義；讀取端一律 `ro,nocopy`；每個卷恰被這兩個服務掛載；backend 的兩個目錄
    環境變數是字面常數。"""
    services = compose.get("services") or {}
    out: list[str] = []
    declared = compose.get("volumes") or {}
    for volume in sorted(BACKUP_VOLUMES):
        if volume not in declared:
            out.append(f"頂層 volumes 沒有宣告 {volume}")
            continue
        body = declared[volume] or {}
        if body.get("driver") != "local":
            out.append(f"頂層 {volume} 必須是 driver: local，實際 {body.get('driver')!r}")
        if body.get("driver_opts"):
            out.append(f"頂層 {volume} 不得帶 driver_opts（不是 bind）：{body['driver_opts']}")
    for volume, target, service, required, forbidden in MOUNT_RULES:
        mounts = [m for m in _mounts(services.get(service) or {}) if m[0] == volume]
        if len(mounts) != 1 or mounts[0][1] != target:
            out.append(f"服務 {service} 必須恰掛一次 {volume}:{target}，實際 {mounts}")
            continue
        flags = mounts[0][2]
        for flag in sorted(required - flags):
            out.append(f"服務 {service} 的卷 {volume} 缺旗標 {flag}（讀取端一律 ro,nocopy）")
        for flag in sorted(forbidden & flags):
            out.append(f"服務 {service} 的卷 {volume} 不得帶 {flag}（寫入端；擁有者由其映像定義）")
    for volume in sorted(BACKUP_VOLUMES):
        holders = sorted(name for name, body in services.items()
                         if any(m[0] == volume for m in _mounts(body)))
        if holders != ["backend", "pgbackrest"]:
            out.append(f"卷 {volume} 只准 backend 與 pgbackrest 掛載，實際 {holders}")
    backend_env = _env_of(services.get("backend") or {})
    for key, value in BACKEND_ENV.items():
        if backend_env.get(key) != value:
            actual = backend_env.get(key)
            out.append(f"backend 的環境 {key} 必須是字面常數 {value!r}，實際 {actual!r}")
    return out


# AT-BK-08-3-2  對應 AC: AC-BK-08-3（PRD §5；R-BK-45）
# 測試類型: Static（PyYAML）  自動化工具: pytest
# 判定指令: python -m pytest tests/test_backup_ctl_deploy_config.py
#           -k AT_BK_08_3_2_ -q -p no:xdist -o addopts=
def test_AT_BK_08_3_2_the_top_level_volumes_are_the_existing_twelve_plus_the_two_control_volumes():
    volumes = _compose()["volumes"]
    assert set(volumes) == EXISTING_VOLUMES | BACKUP_VOLUMES
    assert len(volumes) == 14, "既有 12 卷加 backup_out、backup_req（階一就一起掛，見檔頭階段說明）"
    for name in BACKUP_VOLUMES:
        assert volumes[name] == {"driver": "local"}, f"{name} 必須是 driver: local 的具名卷"


# AT-BK-09-6-1  對應 AC: AC-BK-09-6（PRD §5；R-BK-52）
# 測試類型: Static（PyYAML）  自動化工具: pytest
# 判定指令: python -m pytest tests/test_backup_ctl_deploy_config.py
#           -k AT_BK_09_6_1_ -q -p no:xdist -o addopts=
def test_AT_BK_09_6_1_compose_mount_flags_and_backend_directory_variables():
    compose = _compose()
    assert backup_mount_problems(compose) == []
    services = compose["services"]
    assert ("backup_out", "/backup-out", frozenset()) in _mounts(services["pgbackrest"])
    reader = ("backup_out", "/backup-out", frozenset({"ro", "nocopy"}))
    assert reader in _mounts(services["backend"])
    # 既有的 nocopy 先例（app_logs）仍在：本案不得順手動它
    assert "- app_logs:/app/logs:nocopy" in _service_block(_read(COMPOSE), "backend")


def _mutate(base: dict[str, Any], change: Any) -> dict[str, Any]:
    out = copy.deepcopy(base)
    change(out)
    return out


def _replace_mount(compose: dict[str, Any], service: str, volume: str, new: str | None) -> None:
    vols = compose["services"][service]["volumes"]
    vols[:] = [v for v in vols if not str(v).startswith(f"{volume}:")]
    if new is not None:
        vols.append(new)


# AT-BK-09-6-E-1  對應 AC: AC-BK-09-6（PRD §5；R-BK-52）
# 測試類型: Static 負控（合成 compose）  自動化工具: pytest
# 判定指令: python -m pytest tests/test_backup_ctl_deploy_config.py
#           -k AT_BK_09_6_E_1_ -q -p no:xdist -o addopts=
def test_AT_BK_09_6_E_1_the_mount_checker_names_each_broken_variant():
    base = _compose()
    assert backup_mount_problems(base) == [], "真檔必須回空（鎖不得空過）"

    def third_service(c: dict[str, Any]) -> None:
        c["services"]["redis"].setdefault("volumes", []).append("backup_out:/x:ro,nocopy")

    def bind_declared(c: dict[str, Any]) -> None:
        c["volumes"]["backup_out"] = {
            "driver": "local", "driver_opts": {"type": "none", "o": "bind", "device": "/tmp"}}

    def env_missing(c: dict[str, Any]) -> None:
        del c["services"]["backend"]["environment"]["CONSOLE_BACKUP_OUT_DIR"]

    cases = [
        ("(a) backend 的 backup_out 少 ro",
         lambda c: _replace_mount(c, "backend", "backup_out", "backup_out:/backup-out:nocopy"),
         ("backend", "backup_out")),
        ("(b) backend 的 backup_out 少 nocopy",
         lambda c: _replace_mount(c, "backend", "backup_out", "backup_out:/backup-out:ro"),
         ("backend", "backup_out")),
        ("(c) pgbackrest 的 backup_req 少 ro",
         lambda c: _replace_mount(c, "pgbackrest", "backup_req", "backup_req:/backup-req:nocopy"),
         ("pgbackrest", "backup_req")),
        ("(d) 寫入端 pgbackrest 的 backup_out 帶 nocopy",
         lambda c: _replace_mount(c, "pgbackrest", "backup_out", "backup_out:/backup-out:nocopy"),
         ("pgbackrest", "backup_out")),
        ("(d') 寫入端 backend 的 backup_req 帶 nocopy",
         lambda c: _replace_mount(c, "backend", "backup_req", "backup_req:/backup-req:nocopy"),
         ("backend", "backup_req")),
        ("(e) 第三個服務也掛 backup_out", third_service, ("backup_out", "redis")),
        ("(f) 頂層 backup_out 宣告成 bind", bind_declared, ("backup_out", "driver_opts")),
        ("(g) backend 環境缺 CONSOLE_BACKUP_OUT_DIR", env_missing,
         ("backend", "CONSOLE_BACKUP_OUT_DIR")),
    ]
    for label, change, needles in cases:
        problems = backup_mount_problems(_mutate(base, change))
        assert problems, f"{label} 沒有被指出"
        blob = " ".join(problems)
        for needle in needles:
            assert needle in blob, f"{label}：問題清單沒點名 {needle}：{problems}"


# ── job-run.sh 的鎖：命令形 flock -o、鎖檔在 sidecar 本地 ─────────────────────────────────────────
DEFAULT_LOCK = "/run/backup-ctl/maintenance.lock"
_FLOCK_OPTS_WITH_ARG = frozenset({"-w", "-E", "--timeout", "--wait", "--conflict-exit-code"})
_LOOKUP_WORDS = frozenset({"-v", "command", "type", "which"})   # `command -v flock`：只是查存在
_FD_REDIRECT = re.compile(r"\bexec\s+\d+>>?\s*\S*lock")


def flock_calls(script: str) -> list[tuple[str, list[str], str | None]]:
    """腳本裡真正呼叫 flock 的地方 ＝ [(原行, 選項們, 鎖的運算元)]。選項的引數（-w 7200、
    -E 75）不當運算元；`command -v flock` 這種只查存在的不算呼叫。"""
    out: list[tuple[str, list[str], str | None]] = []
    for line in _code_lines(script):
        if "flock" not in line:
            continue
        try:
            tokens = shlex.split(line)
        except ValueError:
            tokens = line.split()
        for i, token in enumerate(tokens):
            if token != "flock" or (i and tokens[i - 1] in _LOOKUP_WORDS):
                continue
            options: list[str] = []
            operand: str | None = None
            j = i + 1
            while j < len(tokens):
                current = tokens[j]
                if current.startswith("-") and current != "-":
                    options.append(current)
                    j += 2 if current in _FLOCK_OPTS_WITH_ARG else 1
                    continue
                operand = current
                break
            out.append((line, options, operand))
    return out


def _closes_lock_fd(options: list[str]) -> bool:
    return any(o == "--close" or (not o.startswith("--") and "o" in o[1:]) for o in options)


def lock_form_problems(script: str) -> list[str]:
    """job-run.sh 的持鎖形態：預設鎖檔是 sidecar 本地路徑；每個 flock 呼叫都是命令形並帶 -o
    或 --close；不含 fd 形（exec 9>、flock 9）。fd 形持鎖時 /proc/locks 無列（PRD AC-BK-09-5
    實測），且會讓子行程（verify 起的暫存 PG）繼承鎖。"""
    out: list[str] = []
    code = _code_lines(script)
    if not any(f"BACKUP_CTL_LOCK_FILE:-{DEFAULT_LOCK}" in ln for ln in code):
        out.append(f"鎖檔預設值必須是 {DEFAULT_LOCK}")
    calls = flock_calls(script)
    if not calls:
        out.append("找不到任何 flock 呼叫")
    for line, options, operand in calls:
        if not _closes_lock_fd(options):
            out.append(f"flock 呼叫缺 -o／--close：{line.strip()}")
        if operand is not None and operand.isdigit():
            out.append(f"不得使用 fd 形持鎖（flock {operand}）：{line.strip()}")
    for line in code:
        if _FD_REDIRECT.search(line):
            out.append(f"不得使用 fd 形持鎖（exec N> 鎖檔）：{line.strip()}")
    return out


# AT-BK-09-3-E-1  對應 AC: AC-BK-09-3（PRD §5；R-BK-48）
# 測試類型: Static  自動化工具: pytest
# 判定指令: python -m pytest tests/test_backup_ctl_deploy_config.py
#           -k AT_BK_09_3_E_1_ -q -p no:xdist -o addopts=
def test_AT_BK_09_3_E_1_job_run_locks_in_command_form_on_a_local_lock_file():
    script = _read(SCRIPTS_DIR / "job-run.sh")
    assert lock_form_problems(script) == []
    # 負控：fd 形、缺 -o、預設鎖檔改位置，各自要被指出
    fd_form = script + '\nexec 9>"$lock"\nflock -n 9\n'
    problems = lock_form_problems(fd_form)
    assert any("flock 9" in p for p in problems) and any("exec N>" in p for p in problems)
    no_close = re.sub(r'\s-o\s+"\$lock_file"', ' "$lock_file"', script)
    assert no_close != script and any("缺 -o" in p for p in lock_form_problems(no_close))
    moved = script.replace(DEFAULT_LOCK, "/backup-out/maintenance.lock")
    assert any("預設值" in p for p in lock_form_problems(moved))
    # Dockerfile 建 /run/backup-ctl；compose 沒有任何服務把它掛成卷（鎖檔在 sidecar 本地）
    dockerfile = _joined(_read(PGBACKREST_DIR / "Dockerfile"))
    assert re.search(r"install -d [^\n]*/run/backup-ctl", dockerfile)
    for name, body in (_compose().get("services") or {}).items():
        for _src, target, _flags in _mounts(body):
            assert not target.startswith("/run/backup-ctl"), f"{name} 把鎖檔目錄掛成卷：{target}"


# ── crontab：四條工作改經 job-run.sh，其餘兩列逐字不變 ────────────────────────────────────────────
CRON_LOG = ">> /var/log/pgbackrest/cron.log 2>&1"
EXPECTED_CRON_FIELDS = {"full": "0 2 * * 0", "diff": "0 2 * * 1-6", "dump": "30 2 * * *",
                        "verify": "0 4 * * 3"}
#: 與 HEAD 逐字相同的兩列（expire、WAL 清理）：本案不動
UNCHANGED_CRON_LINES = (
    "0 3 * * *  pgbackrest --stanza=aisdlc expire " + CRON_LOG,
    "30 3 * * *  find /var/lib/postgresql/wal_archive -type f -mtime +7 -delete " + CRON_LOG,
)


def crontab_problems(text: str) -> list[str]:
    rows = _code_lines(text)
    out: list[str] = []
    if len(rows) != 6:
        out.append(f"非註解列必須恰 6 條，實際 {len(rows)}")
    wrapped = [r for r in rows if "job-run.sh" in r]
    jobs = [m[1] for m in (re.search(r"job-run\.sh (\w+) ", r) for r in wrapped) if m]
    if jobs != list(EXPECTED_CRON_FIELDS):
        out.append(f"經 job-run.sh 的列必須依序為 {list(EXPECTED_CRON_FIELDS)}：{wrapped}")
    for row, (job, fields) in zip(wrapped, EXPECTED_CRON_FIELDS.items(), strict=False):
        expected = f"{fields}  /usr/local/bin/job-run.sh {job} scheduled {CRON_LOG}"
        if row.split() != expected.split():
            out.append(f"{job} 列必須是 {expected!r}，實際 {row!r}")
    for direct in ("backup-full.sh", "backup-incr.sh", "pg_dump-offsite.sh", "verify-backup.sh"):
        if any(direct in r for r in rows):
            out.append(f"{direct} 仍被 crontab 直接呼叫（要經 job-run.sh）")
    for line in UNCHANGED_CRON_LINES:
        if line not in rows:
            out.append(f"與 HEAD 逐字相同的列不見了或被改動：{line!r}")
    return out


# AT-BK-09-4-1  對應 AC: AC-BK-09-4（PRD §5；R-BK-49）
# 測試類型: Static  自動化工具: pytest
# 判定指令: python -m pytest tests/test_backup_ctl_deploy_config.py
#           -k AT_BK_09_4_1_ -q -p no:xdist -o addopts=
def test_AT_BK_09_4_1_crontab_routes_the_four_jobs_through_job_run():
    text = _read(PGBACKREST_DIR / "crontab")
    assert crontab_problems(text) == []
    direct = text.replace("/usr/local/bin/job-run.sh full scheduled",
                          "/usr/local/bin/backup-full.sh")
    assert crontab_problems(direct), "某工作仍直接呼叫腳本必須被指出"
    no_log = text.replace("/usr/local/bin/job-run.sh dump scheduled " + CRON_LOG,
                          "/usr/local/bin/job-run.sh dump scheduled")
    assert crontab_problems(no_log), "漏掉 >> cron.log 必須被指出"
    assert crontab_problems(text.replace("0 4 * * 3 ", "0 5 * * 3 ")), "cron 時間欄被改要被指出"


# ── runner、export 不得以取鎖探測：對維護鎖零次 flock 呼叫 ────────────────────────────────────────
def flock_target_problems(script: str) -> list[str]:
    """runner 與 export 裡每一處 flock 呼叫都不以維護鎖為目標：不含 maintenance.lock、
    BACKUP_CTL_LOCK_FILE，且鎖的運算元必須是 export 的單一實例鎖（名稱含 export，例如
    "$export_lock_file"）——只比字串會被「換一個變數名」繞過。lock_held 只准讀 /proc/locks 比對鎖檔
    dev:ino——以 flock -n 探測會短暫持鎖，讓同時抵達的手動請求被誤判成 busy，且不能靠副作用偵測。"""
    out: list[str] = []
    for line, _options, operand in flock_calls(script):
        if re.search(r"maintenance\.lock|BACKUP_CTL_LOCK_FILE", line):
            out.append(f"flock 呼叫以維護鎖為目標：{line.strip()}")
        elif operand is None or "export" not in operand:
            out.append(f"flock 呼叫的目標不是 export 的單一實例鎖：{line.strip()}")
    return out


# AT-BK-09-5-E-2  對應 AC: AC-BK-09-5（PRD §5；R-BK-50、R-BK-51）
# 測試類型: Static  自動化工具: pytest
# 判定指令: python -m pytest tests/test_backup_ctl_deploy_config.py
#           -k AT_BK_09_5_E_2_ -q -p no:xdist -o addopts=
def test_AT_BK_09_5_E_2_runner_and_export_never_flock_the_maintenance_lock():
    runner = _read(SCRIPTS_DIR / "backup-ctl-runner.sh")
    export = _read(SCRIPTS_DIR / "backup-ctl-export.sh")
    assert flock_target_problems(runner) == []
    assert flock_target_problems(export) == []
    # export 的單一實例鎖用另一個檔（export.lock），且確實有 flock 呼叫以它為目標
    export_calls = [ln for ln in _code_lines(export) if re.search(r"\bflock\b", ln)]
    assert export_calls and all("export" in ln for ln in export_calls), export_calls
    assert re.search(r"export\.lock", "\n".join(_code_lines(export)))
    # 維護鎖只由 job-run.sh 以命令形 flock -o 持有
    job_run_code = "\n".join(_code_lines(_read(SCRIPTS_DIR / "job-run.sh")))
    assert re.search(r"\bflock\b[^\n]*-o\b", job_run_code)
    # 負控
    assert flock_target_problems('flock -n "$BACKUP_CTL_LOCK_FILE" true\n')
    assert flock_target_problems("flock -w 1 /run/backup-ctl/maintenance.lock cmd\n")
    assert flock_target_problems('flock -n "$lock_file" true\n'), "換個變數名也要被指出"
    assert flock_target_problems("# flock -n maintenance.lock 只是註解\n") == []
    assert flock_target_problems('flock -n -E 0 "$export_lock_file" bash x --locked\n') == []


# ── sidecar 映像與 entrypoint 的目錄權限（寫入端映像定義擁有者；0755，不照抄 0750） ───────────────
def dir_permission_problems(dockerfile: str, entrypoint: str) -> list[str]:
    out: list[str] = []
    run = _joined(dockerfile)
    image_dirs = re.search(
        r"install -d -o postgres -g postgres -m 0755(?P<paths>[^&\n]*?)(?:\s+&&|\s*$|\n)", run)
    if not image_dirs or not {"/backup-out", "/run/backup-ctl"} <= set(image_dirs["paths"].split()):
        out.append("Dockerfile 必須以 install -d -o postgres -g postgres -m 0755 建 /backup-out 與 "
                   "/run/backup-ctl（不得沿用 0750）")
    code = _joined("\n".join(_code_lines(entrypoint)))
    want = ("/backup-out/export", "/backup-out/export/jobs", "/backup-out/results")
    root_phase = code.split("gosu postgres", 1)[0]
    for path in want:
        pattern = rf"install -d [^\n]*-m 0755[^\n]*{re.escape(path)}(?=\s|$)"
        if not re.search(pattern, root_phase):
            out.append(f"entrypoint 必須在 root 階段（gosu 之前）以 install -d -m 0755 建 {path}")
    if "gosu postgres" not in code:
        out.append("entrypoint 找不到以 gosu 降權啟動 runner 的那一行")
    return out


# AT-BK-09-6-2  對應 AC: AC-BK-09-6（PRD §5；R-BK-52）
# 測試類型: Static  自動化工具: pytest
# 判定指令: python -m pytest tests/test_backup_ctl_deploy_config.py
#           -k AT_BK_09_6_2_ -q -p no:xdist -o addopts=
def test_AT_BK_09_6_2_the_sidecar_image_and_entrypoint_create_the_directories_with_0755():
    dockerfile = _read(PGBACKREST_DIR / "Dockerfile")
    entrypoint = _read(SCRIPTS_DIR / "pgbackrest-entrypoint.sh")
    assert dir_permission_problems(dockerfile, entrypoint) == []
    assert dir_permission_problems(dockerfile.replace("-m 0755 /backup-out", "-m 0750 /backup-out"),
                                   entrypoint), "Dockerfile 改成 0750 必須被指出"
    assert dir_permission_problems(dockerfile, entrypoint.replace("-m 0755", "-m 0750")), \
        "entrypoint 改成 0750 必須被指出"
    late = entrypoint.replace("install -d", "# install -d")
    assert dir_permission_problems(dockerfile, late), "entrypoint 沒有 install -d 必須被指出"
    # 階二才查 backend/Dockerfile 的 /backup-req（spring:spring 0755）：不在本檔範圍


# ── Prometheus：兩條新規則、規則檔被載入、新增規則名都在 promtool 測試檔 ──────────────────────────
LEGACY_RULES: tuple[tuple[str, str], ...] = (
    ("PostgresDown", "pg_up == 0"),
    ("PostgresReplicationLagHigh", 'pg_replication_lag_seconds{job="postgres-replica"} > 30'),
    ("PostgresConnectionsHigh",
     "sum by (job) (pg_stat_activity_count) > 0.9 * max by (job) (pg_settings_max_connections)"),
    ("PostgresDiskUsageHigh", 'aisdlc_storage_used_ratio{path="/var/lib/postgresql/data"} > 0.8'),
    ("PostgresBufferAllocSpike",
     "rate(pg_stat_bgwriter_buffers_alloc_total[5m]) > 10 and "
     "rate(pg_stat_bgwriter_buffers_alloc_total[5m]) > "
     "3 * rate(pg_stat_bgwriter_buffers_alloc_total[1h])"),
    ("PostgresLocksHigh", "sum by (job) (pg_locks_count) > 50"),
    ("PostgresSlowQueries",
     "max by (job, datname, queryid) (rate(pg_stat_statements_seconds_total[10m]) / "
     "rate(pg_stat_statements_calls_total[10m])) > 5"),
    ("PostgresWalArchiveFailing",
     'increase(pg_stat_archiver_failed_count{job="postgres-primary"}[15m]) > 0'),
    ("PgBackRestNoRecentFullBackup",
     "max by (stanza) (pgbackrest_backup_since_last_full_seconds) > 691200"),
    ("PgBackRestLastBackupFailed", "pgbackrest_backup_last_status != 0"),
    ("PgBackRestStanzaError", "pgbackrest_stanza_status > 2"),
    ("PgBackRestMetricsStale", "time() - pgbackrest_exporter_scrape_timestamp_seconds > 300"),
)
NEW_RULES: tuple[tuple[str, str, str, str], ...] = (
    ("PgBackRestJobFailed", 'aisdlc_backup_job_last_status{backup_job=~"dump|verify"} != 0',
     "1m", "critical"),
    ("PgBackRestControlHeartbeatStale",
     "time() - aisdlc_backup_ctl_heartbeat_timestamp_seconds > 120", "1m", "warning"),
)
BACKUP_GROUP = "aisdlc-backup"
ALERTS_MOUNT = "./docker/prometheus/alerts.yml:/etc/prometheus/alerts.yml:ro"


def _rules(alerts: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return [(g["name"], r) for g in alerts["groups"] for r in g["rules"]]


def alert_rule_problems(alerts: dict[str, Any]) -> list[str]:
    """alerts.yml 的規則形狀：總數 14；既有 12 條名稱與 expr 逐字不變；新增兩條位於群組
    aisdlc-backup 末尾，expr／for／severity 逐字。標籤名是 backup_job，不是 job（抓取目標標籤
    job="pgbackrest" 會把曝光的 job 改名成 exported_job，規則的 {job=~…} 永不匹配）。"""
    rules = _rules(alerts)
    out: list[str] = []
    if len(rules) != 14:
        out.append(f"規則總數必須 14，實際 {len(rules)}")
    by_name = {r["alert"]: (g, r) for g, r in rules}
    for name, expr in LEGACY_RULES:
        found = by_name.get(name)
        if not found or found[1]["expr"] != expr:
            out.append(f"既有規則 {name} 的名稱或 expr 被改動")
    group = next((g for g in alerts["groups"] if g["name"] == BACKUP_GROUP), None)
    tail = [r["alert"] for r in group["rules"]][-2:] if group else []
    if tail != [n[0] for n in NEW_RULES]:
        out.append(f"群組 {BACKUP_GROUP} 的末兩條必須是 {[n[0] for n in NEW_RULES]}，實際 {tail}")
    for name, expr, hold, severity in NEW_RULES:
        rule = by_name.get(name, (None, {}))[1]
        if rule.get("expr") != expr:
            out.append(f"{name} 的 expr 必須逐字是 {expr!r}，實際 {rule.get('expr')!r}")
        if rule.get("for") != hold:
            out.append(f"{name} 的 for 必須是 {hold}，實際 {rule.get('for')!r}")
        if (rule.get("labels") or {}).get("severity") != severity:
            out.append(f"{name} 的 severity 必須是 {severity}")
    return out


def rules_loaded_problems(alerts: dict[str, Any], prometheus_cfg: dict[str, Any],
                          compose: dict[str, Any], promtool_text: str | None) -> list[str]:
    """規則真的被載入、真的被測：Prometheus 對 rule_files 找不到的檔不報錯（少一行掛載＝規則整組消失
    而沒人知道）；每條**新增**規則名都在 promtool 測試檔（既有 12 條不要求，避免強迫本案替
    舊規則補測試）。"""
    out: list[str] = []
    if "/etc/prometheus/alerts.yml" not in (prometheus_cfg.get("rule_files") or []):
        out.append("prometheus.yml 的 rule_files 不含 /etc/prometheus/alerts.yml")
    prometheus = compose["services"]["prometheus"].get("volumes") or []
    if ALERTS_MOUNT not in prometheus:
        out.append(f"compose 的 prometheus 沒掛 {ALERTS_MOUNT}")
    if promtool_text is None:
        return [*out, "tests/backup_alerts_test.yml 不存在"]
    if yaml.safe_load(promtool_text).get("rule_files") != ["../alerts.yml"]:
        out.append('backup_alerts_test.yml 的 rule_files 必須是 ["../alerts.yml"]')
    legacy = {name for name, _expr in LEGACY_RULES}
    for _group, rule in _rules(alerts):
        if rule["alert"] not in legacy and rule["alert"] not in promtool_text:
            out.append(f"新增規則 {rule['alert']} 不在 promtool 測試檔")
    return out


def readme_rule_count_problems(readme: str) -> list[str]:
    section = readme.split("## 7. 監控", 1)[-1].split("\n## 8.", 1)[0]
    out = []
    if "共 14 條" not in section:
        out.append("README〈7〉必須寫「共 14 條」")
    if "共 12 條" in readme:
        out.append("README 不得再有「共 12 條」")
    return out


def _load_alerts() -> dict[str, Any]:
    return yaml.safe_load(_read(PROMETHEUS_DIR / "alerts.yml"))


def _promtool_text() -> str | None:
    path = PROMETHEUS_DIR / "tests" / "backup_alerts_test.yml"
    return _read(path) if path.is_file() else None


# AT-BK-09-7-2  對應 AC: AC-BK-09-7（PRD §5；R-BK-54）
# 測試類型: Static（PyYAML）  自動化工具: pytest
# 判定指令: python -m pytest tests/test_backup_ctl_deploy_config.py
#           -k AT_BK_09_7_2_ -q -p no:xdist -o addopts=
def test_AT_BK_09_7_2_two_new_rules_are_loaded_tested_and_counted_in_the_readme():
    alerts = _load_alerts()
    assert alert_rule_problems(alerts) == []
    prometheus_cfg = yaml.safe_load(_read(PROMETHEUS_DIR / "prometheus.yml"))
    assert rules_loaded_problems(alerts, prometheus_cfg, _compose(), _promtool_text()) == []
    assert readme_rule_count_problems(_read(README)) == []
    # 標籤名是 backup_job，不是 job
    for name, _expr, _hold, _sev in NEW_RULES:
        expr = next(r["expr"] for _g, r in _rules(alerts) if r["alert"] == name)
        assert "backup_job" in expr or "heartbeat" in expr
        assert not re.search(r'\{job=~', expr), f"{name} 不得用 job 標籤（會被改名成 exported_job）"


# AT-BK-09-7-E-1  對應 AC: AC-BK-09-7（PRD §5；R-BK-54）
# 測試類型: Static 負控  自動化工具: pytest
# 判定指令: python -m pytest tests/test_backup_ctl_deploy_config.py
#           -k AT_BK_09_7_E_1_ -q -p no:xdist -o addopts=
def test_AT_BK_09_7_E_1_the_rule_locks_name_each_broken_variant():
    alerts = _load_alerts()
    prometheus_cfg = yaml.safe_load(_read(PROMETHEUS_DIR / "prometheus.yml"))
    compose = _compose()
    text = _promtool_text()
    assert text is not None
    assert rules_loaded_problems(alerts, prometheus_cfg, compose, text) == [], "真檔必須回空"
    # (a) promtool 測試檔缺 PgBackRestJobFailed
    assert any("PgBackRestJobFailed" in p for p in rules_loaded_problems(
        alerts, prometheus_cfg, compose, text.replace("PgBackRestJobFailed", "Removed")))
    # (b) compose 的 prometheus 掛載少了 alerts.yml 那一行
    no_mount = _mutate(
        compose, lambda c: c["services"]["prometheus"]["volumes"].remove(ALERTS_MOUNT))
    assert any("沒掛" in p for p in rules_loaded_problems(alerts, prometheus_cfg, no_mount, text))
    # (c) prometheus.yml 的 rule_files 不含 alerts.yml
    no_rule_file = _mutate(
        prometheus_cfg, lambda c: c["rule_files"].remove("/etc/prometheus/alerts.yml"))
    assert any("rule_files" in p
               for p in rules_loaded_problems(alerts, no_rule_file, compose, text))
    # (d) alerts.yml 多一條新規則而 promtool 測試檔沒有它（既有 12 條不要求）
    new_rule = {"alert": "PgBackRestExtra", "expr": "vector(1)", "for": "1m",
                "labels": {"severity": "warning"}}
    extra = _mutate(alerts, lambda a: a["groups"][-1]["rules"].append(new_rule))
    assert any("PgBackRestExtra" in p for p in rules_loaded_problems(
        extra, prometheus_cfg, compose, text))
    # 形狀鎖本身也要能紅：少一條、expr 的標籤改回 job、README 仍寫共 12 條
    fewer = _mutate(alerts, lambda a: a["groups"][-1]["rules"].pop())
    assert alert_rule_problems(fewer)
    relabelled = _mutate(alerts, lambda a: a["groups"][-1]["rules"][-2].update(
        {"expr": 'aisdlc_backup_job_last_status{job=~"dump|verify"} != 0'}))
    assert alert_rule_problems(relabelled)
    assert readme_rule_count_problems("## 7. 監控\n共 12 條\n## 8. x\n")


# ── 機密不外洩：console-api 不持有 MinIO 金鑰與 cipher 密碼、不掛備份卷、沒有 docker.sock ─────────
FORBIDDEN_BACKEND_ENV_PREFIXES = ("PGBACKREST_", "AWS_", "OFFSITE_S3_", "MC_HOST")
FORBIDDEN_BACKEND_VOLUMES = ("pg_data", "pg_backup", "pg_wal_archive")


def secret_exposure_problems(compose: dict[str, Any], compose_text: str) -> list[str]:
    services = compose.get("services") or {}
    backend = services.get("backend") or {}
    out: list[str] = []
    for key in _env_of(backend):
        if key.startswith(FORBIDDEN_BACKEND_ENV_PREFIXES):
            out.append(f"backend 環境不得有 {key}（console-api 不持有 MinIO 金鑰與 cipher 密碼）")
    for source, target, _flags in _mounts(backend):
        if source in FORBIDDEN_BACKEND_VOLUMES:
            out.append(f"backend 不得掛 {source}（{target}）")
    count = compose_text.count("docker.sock")
    if count:
        out.append(f"compose 不得出現 docker.sock（出現 {count} 次）")
    control = _env_of(services.get("pgbackrest") or {})
    for key in ("PGBACKREST_REPO1_CIPHER_PASS", "AWS_ACCESS_KEY_ID"):
        if key not in control:
            out.append(f"對照組失效：pgbackrest 服務應持有 {key}（證明掃描器有在看）")
    return out


# AT-BK-10-4-2  對應 AC: AC-BK-10-4（PRD §5；R-BK-58）
# 測試類型: Static（PyYAML）  自動化工具: pytest
# 判定指令: python -m pytest tests/test_backup_ctl_deploy_config.py
#           -k AT_BK_10_4_2_ -q -p no:xdist -o addopts=
def test_AT_BK_10_4_2_the_backend_holds_no_backup_secrets_and_no_service_mounts_the_docker_socket():
    compose, text = _compose(), _read(COMPOSE)
    assert secret_exposure_problems(compose, text) == []
    leak_env = _mutate(compose, lambda c: c["services"]["backend"]["environment"].update(
        {"AWS_SECRET_ACCESS_KEY": "x"}))
    assert secret_exposure_problems(leak_env, text)
    leak_mount = _mutate(compose, lambda c: c["services"]["backend"].setdefault(
        "volumes", []).append("pg_backup:/var/lib/pgbackrest:ro"))
    assert secret_exposure_problems(leak_mount, text)
    assert secret_exposure_problems(compose, text + "\n  - /var/run/docker.sock:/x\n")
    blind = _mutate(compose, lambda c: c["services"]["pgbackrest"]["environment"].pop(
        "PGBACKREST_REPO1_CIPHER_PASS"))
    assert any("對照組失效" in p for p in secret_exposure_problems(blind, text))
