"""SelfImproving 的部署前置與文件連動的靜態檢查（TCS-SelfImprovingMirror-P1b：AT-932-4-4、
AT-940-1-E-1、AT-940-3-1、AT-940-3-E-1、AT-940-4-1、AT-940-4-E-1；TCS-SelfImprovingDecide-P2b：
AT-950-1-3、AT-950-11-1、AT-950-11-2、AT-950-11-E-1）。

只讀檔、不起 Docker：compose 的 engine-bridge 服務沒有對 host 發布任何埠（Architecture §12.1 L-6
的 P 型劃界補機械物）、唯讀掛載恰符合具名設計 A 或 B 其中之一**加上恰一條可寫的稽核目錄 bind**
（P2b）、README 與 settings 檔頭已列 `SI_ROOT`、端點與兩個新環境變數、`agentconsole-ci.yml` 的
`paths` 兩處都涵蓋寫入閉包的根層輸入。每個檢查都是純函式（輸入為解析後的結構或文字，輸出為問題
清單），真檔必須回空、各壞變體必須逐一回非空。AT 內不引用其他 AT 的 ID。
"""
from __future__ import annotations

import ast
import copy
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests import si_repo_support as sup

CONSOLE_DIR = sup.MONOREPO / "AgentConsole"
COMPOSE = CONSOLE_DIR / "docker-compose.yml"
ENV_EXAMPLE = CONSOLE_DIR / ".env.example"
WORKFLOW = sup.MONOREPO / ".github" / "workflows" / "agentconsole-ci.yml"
README = CONSOLE_DIR / "engine-bridge" / "README.md"
SETTINGS = CONSOLE_DIR / "engine-bridge" / "app" / "settings.py"
EMPTY_CONFIG = CONSOLE_DIR / "docker" / "si" / "git-config.empty"

pytestmark = pytest.mark.skipif(
    not COMPOSE.is_file(), reason="不在 monorepo 內（例如只有 engine-bridge 目錄的 checkout）")


def load_compose() -> dict[str, Any]:
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


# ── 無 ports、8081 只出現在三個鍵路徑 ────────────────────────────────────────────────────────
ALLOWED_8081 = frozenset({
    "services.backend.environment.ENGINE_BRIDGE_URL",
    "services.engine-bridge.environment.BRIDGE_PORT",
    "services.engine-bridge.healthcheck.test"})


def _scalars(node: Any, path: str) -> Iterable[tuple[str, str]]:
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _scalars(value, f"{path}.{key}")
    elif isinstance(node, list):
        for item in node:                      # 清單元素共用清單本身的鍵路徑
            yield from _scalars(item, path)
    elif node is not None:
        yield path, str(node)


def bridge_exposure_problems(compose: dict[str, Any]) -> list[str]:
    out: list[str] = []
    svc = (compose.get("services") or {}).get("engine-bridge")
    if svc is None:
        return ["compose 沒有 engine-bridge 服務"]
    if "ports" in svc:
        out.append("engine-bridge 不得有 ports（Bridge 無認證，只准 backend-net）")
    nets = svc.get("networks") or []
    names = set(nets if isinstance(nets, list) else nets)
    if names != {"backend-net", "db-net"}:
        out.append(f"engine-bridge 的網路必須恰為 backend-net 與 db-net，實際 {sorted(names)}")
    for path, text in _scalars(compose, "$"):
        path = path.removeprefix("$.")
        if "8081" in text and path not in ALLOWED_8081:
            out.append(f"{path} 含 8081（只准 {sorted(ALLOWED_8081)}）")
    for name, other in (compose.get("services") or {}).items():
        for entry in other.get("ports") or []:
            if "8081" in str(entry):
                out.append(f"服務 {name} 的 ports 發布了 8081：{entry}")
    return out


def test_AT_932_4_4_the_bridge_service_publishes_no_port_to_the_host() -> None:
    compose = load_compose()
    assert bridge_exposure_problems(compose) == []
    bridge = compose["services"]["engine-bridge"]
    assert "ports" not in bridge
    assert sorted(bridge["networks"]) == ["backend-net", "db-net"]
    # 負控一：加一條把 8081 對映到 host 的 ports
    published = copy.deepcopy(compose)
    published["services"]["engine-bridge"]["ports"] = ["8081:8081"]
    assert any("ports" in p for p in bridge_exposure_problems(published))
    # 負控二：白名單以外的鍵路徑含 8081
    leaked = copy.deepcopy(compose)
    leaked["services"]["frontend"]["environment"] = {"X": "http://engine-bridge:8081"}
    assert any("services.frontend.environment.X" in p for p in bridge_exposure_problems(leaked))
    # 負控三：網路多一個
    wider = copy.deepcopy(compose)
    wider["services"]["engine-bridge"]["networks"] = ["backend-net", "db-net", "frontend-net"]
    assert any("網路" in p for p in bridge_exposure_problems(wider))
    # 對照：只在 YAML 註解裡寫 8081 不算（註解不在解析結果內）
    commented = yaml.safe_load("services:\n  engine-bridge:\n    # 8081\n    networks: "
                               "[backend-net, db-net]\n")
    assert bridge_exposure_problems(commented) == []


# ── README 與 settings 檔頭註解 ───────────────────────────────────────────────────────────────
SI_ENDPOINTS = ("/si/status", "/si/observations", "/si/events", "/si/proposals",
                "/si/proposals/{id}", "/si/runs")


def doc_problems(readme: str, settings_doc: str) -> list[str]:
    out: list[str] = []
    if "SI_ROOT" not in settings_doc:
        out.append("settings.py 的檔頭註解沒有列 SI_ROOT")
    if "SI_ROOT" not in readme:
        out.append("README 沒有列 SI_ROOT")
    for needle in (*SI_ENDPOINTS, "si_unavailable", "si_not_found"):
        # `/si/proposals` 不能被 `/si/proposals/{id}` 頂替：後面不得再接 / 或字母數字
        if not re.search(re.escape(needle) + r"(?![\w/])", readme):
            out.append(f"README 沒有列 {needle}")
    return out


def test_AT_940_1_E_1_readme_and_settings_header_name_si_root_and_the_endpoints() -> None:
    header = ast.get_docstring(ast.parse(SETTINGS.read_text(encoding="utf-8"))) or ""
    assert doc_problems(README.read_text(encoding="utf-8"), header) == []
    good = " ".join(["SI_ROOT", *SI_ENDPOINTS, "si_unavailable", "si_not_found"])
    assert doc_problems(good, good) == []
    assert any("settings" in p for p in doc_problems(good, "沒有環境變數"))
    no_root = doc_problems(good.replace("SI_ROOT", ""), good)
    assert any("README 沒有列 SI_ROOT" in p for p in no_root)
    for missing in (*SI_ENDPOINTS, "si_unavailable", "si_not_found"):
        broken = good.replace(missing, "")
        if missing == "/si/proposals":                       # 兩個字串會互相頂替：全部換掉才算缺
            broken = " ".join(w for w in good.split() if w != "/si/proposals")
        problems = doc_problems(broken, good)
        assert any(missing in p for p in problems), f"缺 {missing} 沒有被指出：{problems}"


# P2b：兩個新環境變數（README 與 settings 檔頭都要列）、四個 POST 路徑與三個新 reason（README）
NEW_ENV_VARS = ("BRIDGE_SI_WRITE_TOKEN", "BRIDGE_SI_AUDIT_DIR")
POST_PATHS = ("POST /si/proposals/{id}:decide", "POST /si/observations",
              "POST /si/observations/{id}:close", "POST /si/observations:validate")
NEW_REASONS = ("si_write_disabled", "si_write_forbidden", "si_audit_exists")


def p2b_doc_problems(readme: str, settings_doc: str) -> list[str]:
    out: list[str] = []
    for name in NEW_ENV_VARS:
        if name not in settings_doc:
            out.append(f"settings.py 的檔頭註解沒有列 {name}")
        if name not in readme:
            out.append(f"README 沒有列 {name}")
    for needle in POST_PATHS:
        # `POST /si/observations` 不能被 `…:validate`、`…/{id}:close` 頂替：後面不得再接 : / 或字母
        if not re.search(re.escape(needle) + r"(?![\w/:])", readme):
            out.append(f"README 沒有列 {needle}")
    for reason in NEW_REASONS:
        if reason not in readme:
            out.append(f"README 沒有列 {reason}")
    return out


def test_AT_950_1_3_readme_and_settings_header_name_the_p2b_variables_paths_and_reasons() -> None:
    header = ast.get_docstring(ast.parse(SETTINGS.read_text(encoding="utf-8"))) or ""
    assert p2b_doc_problems(README.read_text(encoding="utf-8"), header) == []
    items = [*NEW_ENV_VARS, *POST_PATHS, *NEW_REASONS]

    def text_without(item: str) -> str:
        return "\n".join(line for line in items if line != item)

    good = "\n".join(items)
    assert p2b_doc_problems(good, good) == []
    for name in NEW_ENV_VARS:
        assert any(f"settings.py 的檔頭註解沒有列 {name}" in p
                   for p in p2b_doc_problems(good, text_without(name)))
        assert any(f"README 沒有列 {name}" in p
                   for p in p2b_doc_problems(text_without(name), good))
    # 注意 `POST /si/observations` 是其他兩條的字面前綴：缺它時另兩條仍在，也必須被指出缺的是它
    for needle in (*POST_PATHS, *NEW_REASONS):
        problems = p2b_doc_problems(text_without(needle), good)
        assert any(needle in p for p in problems), f"缺 {needle} 沒有被指出：{problems}"


# ── compose 的 SI 掛載：恰符合設計 A 或 B（＋P2b 恰一條可寫的稽核 bind）───────────────────────────
EXISTING_MOUNTS = ("../AISDLC_SDD:/sdd:ro", "engine_workspace:/workspace", "app_logs:/app/logs",
                   # ResearchToPRD 整合 P0（commit 04884296）：mock claude 研究劇本夾具的唯讀 bind
                   "./engine-bridge/tests/fixtures/research/scripts:/mock-research:ro")
COMMON = {("../tools", "/repo/tools"), ("../docs/06_quality", "/repo/docs/06_quality")}
DESIGN_A = COMMON | {("../.git/HEAD", "/repo/.git/HEAD"), ("../.git/refs", "/repo/.git/refs"),
                     ("../.git/objects", "/repo/.git/objects"),
                     ("../.git/packed-refs", "/repo/.git/packed-refs")}
DESIGN_B = COMMON | {("../.git", "/repo/.git"),
                     ("./docker/si/git-config.empty", "/repo/.git/config")}
AUDIT_ENV, TOKEN_ENV = "BRIDGE_SI_AUDIT_DIR", "BRIDGE_SI_WRITE_TOKEN"
BACKEND_ENVS = ("BRIDGE_SI_WRITE_TOKEN", "CONSOLE_SI_DECIDERS", "CONSOLE_SI_AUDIT_KEY")
#: 來源路徑寫死磁碟位置（Windows 磁碟機代號、macOS／Linux 常見的家目錄與掛載點）＝不可攜。
HARD_CODED_DISK = re.compile(r"^(?:[A-Za-z]:[\\/]|/Users/|/home/|/Volumes/|/mnt/)")


def _short_target(raw: str) -> str:
    parts = raw.split(":")
    return parts[1] if len(parts) >= 2 else raw


def _env_of(service: dict[str, Any]) -> dict[str, str]:
    env = service.get("environment") or {}
    if isinstance(env, list):
        env = dict(item.split("=", 1) for item in env)
    return {str(k): "" if v is None else str(v) for k, v in env.items()}


def _volume_target(vol: Any) -> str:
    """volumes 項目的容器內目標（長語法取 `target`；短語法取 `來源:目標[:模式]` 的目標——來源內的
    `${VAR:-…}` 含冒號，所以由右側以 `:/` 起頭的目標段取）。"""
    if isinstance(vol, dict):
        return str(vol.get("target", ""))
    match = re.match(r"^.*?:(/[^:]*)(?::\w+)*$", str(vol))
    return match.group(1) if match else ""


def _is_bind(vol: Any) -> bool:
    if isinstance(vol, dict):
        return vol.get("type") == "bind"
    source = str(vol).split(":")[0]
    return source.startswith((".", "/", "~", "$")) or "\\" in source


def _is_writable(vol: Any) -> bool:
    if isinstance(vol, dict):
        return vol.get("read_only") is not True
    modes = str(vol).split(":")[2:]
    return not any(mode.split(",")[0] == "ro" for mode in modes)


def audit_bind_problems(compose: dict[str, Any]) -> list[str]:
    """P2b 稽核目錄的部署前提：engine-bridge 的 `BRIDGE_SI_AUDIT_DIR`（容器內絕對路徑，不在 `/repo`
    下）恰對應一條長語法、非唯讀、`create_host_path: false`、來源以 `console_audit` 結尾且不含寫死
    磁碟路徑的 bind；它是 engine-bridge **唯一**可寫的 bind；權杖與 backend 的三個變數以預設為空的
    插值傳入。"""
    services = compose.get("services") or {}
    svc = services.get("engine-bridge") or {}
    backend = services.get("backend") or {}
    out: list[str] = []
    env = _env_of(svc)
    audit_dir = env.get(AUDIT_ENV, "")
    volumes = svc.get("volumes") or []
    audit: list[Any] = []
    if not audit_dir:
        out.append(f"engine-bridge 缺環境變數 {AUDIT_ENV}")
    else:
        if not audit_dir.startswith("/"):
            out.append(f"{AUDIT_ENV} 須為容器內的絕對路徑，實際 {audit_dir!r}")
        if audit_dir.startswith("/repo"):
            out.append(f"{AUDIT_ENV} 不得落在 /repo 之下（那是唯讀鏡像）")
        audit = [v for v in volumes if _volume_target(v).rstrip("/") == audit_dir.rstrip("/")]
        if len(audit) != 1:
            out.append(f"{AUDIT_ENV} 必須恰有一條對應的 bind，實際 {len(audit)}")
    for vol in audit[:1]:
        if not isinstance(vol, dict):
            out.append("稽核 bind 須用長語法（短語法會被來源路徑的冒號搞混，"
                       "且無法明寫 create_host_path）")
            continue
        if vol.get("type") != "bind":
            out.append("稽核 bind 的 type 必須是 bind")
        if vol.get("read_only") is True:
            out.append("稽核 bind 不得唯讀（Bridge 要寫稽核檔）")
        if (vol.get("bind") or {}).get("create_host_path") is not False:
            out.append("稽核 bind 的 create_host_path 必須明寫 false（缺席時要明確失敗）")
        source = str(vol.get("source", "")).replace("\\", "/").rstrip("/")
        if not source.endswith("console_audit"):
            out.append(f"稽核 bind 的 source 必須以 console_audit 結尾，實際 {source!r}"
                       "（不得掛整個家目錄或 repo 根）")
        if HARD_CODED_DISK.match(source):
            out.append(f"稽核 bind 的 source 不得寫死磁碟路徑：{source!r}")
    others = [v for v in volumes if _is_bind(v) and _is_writable(v) and v not in audit]
    if others:
        out.append(f"除稽核目錄外 engine-bridge 不得有可寫的 bind：{others}")
    if env.get(TOKEN_ENV) != "${BRIDGE_SI_WRITE_TOKEN:-}":
        out.append(f"engine-bridge 的 {TOKEN_ENV} 須以 ${{{TOKEN_ENV}:-}} 插值（預設空＝停用）")
    backend_env = _env_of(backend)
    for name in BACKEND_ENVS:
        if backend_env.get(name) != "${" + name + ":-}":
            out.append(f"backend 的 {name} 須以 ${{{name}:-}} 插值（預設空）")
    return out


def si_mount_problems(compose: dict[str, Any]) -> list[str]:
    svc = (compose.get("services") or {}).get("engine-bridge") or {}
    out: list[str] = []
    env = _env_of(svc)
    if env.get("SI_ROOT") != "/repo":
        out.append(f"SI_ROOT 必須是 /repo，實際 {env.get('SI_ROOT')!r}")
    volumes = svc.get("volumes") or []
    for existing in EXISTING_MOUNTS:
        if existing not in volumes:
            out.append(f"既有掛載 {existing} 不見了")
    pairs: set[tuple[str, str]] = set()
    for vol in volumes:
        if isinstance(vol, str):
            if _short_target(vol).startswith("/repo"):
                out.append(f"{vol} 是短語法（SI 掛載須用長語法並明寫 read_only）")
            continue
        target = str(vol.get("target", ""))
        if not target.startswith("/repo"):
            continue
        source = str(vol.get("source", ""))
        pairs.add((source, target))
        if vol.get("type") != "bind":
            out.append(f"{target} 的 type 必須是 bind")
        if vol.get("read_only") is not True:
            out.append(f"{target} 未設 read_only: true")
        create = (vol.get("bind") or {}).get("create_host_path")
        if create is True:
            out.append(f"{target} 的 bind.create_host_path 不得為 true")
        if source in ("..", "../", "."):
            out.append(f"掛了 repo 根（來源 {source}）")
        if source.replace("\\", "/").rstrip("/").endswith(".git/config"):
            out.append("掛了真的 .git/config（內含 remote 與憑證設定）")
    only_a, only_b = pairs & (DESIGN_A - DESIGN_B), pairs & (DESIGN_B - DESIGN_A)
    if only_a and only_b:
        out.append("設計 A 與 B 混用（兩個設計只能擇一）")
    elif pairs != DESIGN_A and pairs != DESIGN_B:
        near = DESIGN_B if only_b else DESIGN_A
        for source, target in sorted(near - pairs):
            out.append(f"缺少 {target}（{source}）")
        for source, target in sorted(pairs - near):
            out.append(f"多掛 {target}（{source}）")
    if pairs == DESIGN_B and not (EMPTY_CONFIG.is_file() and EMPTY_CONFIG.stat().st_size == 0):
        out.append("設計 B 需要入庫的空檔 docker/si/git-config.empty（長度 0）")
    return out


def design_of(compose: dict[str, Any]) -> str:
    vols = compose["services"]["engine-bridge"]["volumes"]
    pairs = {(v["source"], v["target"]) for v in vols
             if isinstance(v, dict) and str(v.get("target", "")).startswith("/repo")}
    return "A" if pairs == DESIGN_A else "B" if pairs == DESIGN_B else "?"


def test_AT_940_3_1_si_mounts_match_exactly_one_named_design() -> None:
    compose = load_compose()
    assert si_mount_problems(compose) == []
    assert audit_bind_problems(compose) == [], \
        "P2b：設計 A 或 B 的唯讀 SI bind 之外，恰一條可寫稽核 bind"
    assert design_of(compose) in ("A", "B")
    for vol in compose["services"]["engine-bridge"]["volumes"]:
        if isinstance(vol, dict) and vol["target"].startswith("/repo"):
            assert vol["read_only"] is True and vol["type"] == "bind"
    if design_of(compose) == "A":
        for vol in compose["services"]["engine-bridge"]["volumes"]:
            if isinstance(vol, dict) and vol["target"].startswith("/repo"):
                assert vol["bind"]["create_host_path"] is False, vol["target"]
    if design_of(compose) == "B":
        assert EMPTY_CONFIG.is_file() and EMPTY_CONFIG.stat().st_size == 0


def _volumes(compose: dict[str, Any]) -> list[Any]:
    return compose["services"]["engine-bridge"]["volumes"]


def _mutate(base: dict[str, Any], change: Any) -> dict[str, Any]:
    out = copy.deepcopy(base)
    change(out)
    return out


def _entry(compose: dict[str, Any], target: str) -> dict[str, Any]:
    return next(v for v in _volumes(compose) if isinstance(v, dict) and v["target"] == target)


def _long(source: str, target: str) -> dict[str, Any]:
    return {"type": "bind", "source": source, "target": target, "read_only": True,
            "bind": {"create_host_path": False}}


def test_AT_940_3_E_1_the_mount_checker_names_each_of_nine_broken_variants() -> None:
    base = load_compose()
    if design_of(base) != "A":
        pytest.fail("負控變體以設計 A 為底；改採設計 B 時須同步改這張表")
    variants: dict[str, tuple[Any, str]] = {
        "missing-read-only": (lambda c: _entry(c, "/repo/tools").pop("read_only"), "read_only"),
        "short-syntax": (lambda c: _volumes(c).__setitem__(
            _volumes(c).index(_entry(c, "/repo/tools")), "../tools:/repo/tools:ro"), "短語法"),
        "create-host-path-true": (lambda c: _entry(c, "/repo/tools")["bind"].update(
            create_host_path=True), "create_host_path"),
        "mounts-repo-root": (lambda c: _volumes(c).append(_long("..", "/repo")), "repo 根"),
        "mounts-real-git-config": (lambda c: _volumes(c).append(
            _long("../.git/config", "/repo/.git/config")), ".git/config"),
        "missing-packed-refs": (lambda c: _volumes(c).remove(
            _entry(c, "/repo/.git/packed-refs")), "packed-refs"),
        "extra-mount": (lambda c: _volumes(c).append(_long("../docs", "/repo/docs")), "多掛"),
        "wrong-si-root": (lambda c: c["services"]["engine-bridge"]["environment"].update(
            SI_ROOT="/srv"), "SI_ROOT"),
        "mixed-a-and-b": (lambda c: _volumes(c).append(_long("../.git", "/repo/.git")), "混用"),
    }
    assert len(variants) == 9
    for name, (change, needle) in variants.items():
        problems = si_mount_problems(_mutate(base, change))
        assert problems, f"{name}：壞變體沒有被指出"
        assert any(needle in p for p in problems), f"{name}：沒有指出 {needle!r}：{problems}"
    # P2b：多餘的**可寫** bind 另由稽核 bind 的檢查指出
    # （P1b 的「多掛一條」只指唯讀或非稽核的多餘 bind）
    writable_extra = _mutate(base, lambda c: _volumes(c).append(
        {**_long("../docs", "/repo/docs"), "read_only": False}))
    assert any("多掛" in p or "read_only" in p for p in si_mount_problems(writable_extra))
    assert any("可寫的 bind" in p for p in audit_bind_problems(writable_extra))


# ── P2b 的部署前提：稽核 bind、環境變數、.env.example（AT-950-11-1、AT-950-11-E-1）────────────────
def env_example_problems(text: str) -> list[str]:
    """`.env.example` 對三個新變數只准有 `<YOUR_…>` 佔位（可在註解行內，但每個都要出現），且全檔無
    機密形態字面（`sk-` 起頭 20 字元以上）。訊息不回印值本身。"""
    out: list[str] = []
    for name in BACKEND_ENVS:
        values = re.findall(rf"^#?[ \t]*{name}=(.*)$", text, re.M)
        if not values:
            out.append(f".env.example 缺 {name}")
        for value in values:
            if not re.fullmatch(r"<YOUR_[A-Z0-9_]+>", value.strip()):
                out.append(f".env.example 的 {name} 不是 <YOUR_…> 佔位")
    if re.search(r"sk-[A-Za-z0-9_\-]{20,}", text):
        out.append(".env.example 含機密形態字面（sk- 起頭 20 字元以上）")
    return out


def deploy_problems(compose: dict[str, Any], env_example: str) -> list[str]:
    return (bridge_exposure_problems(compose) + si_mount_problems(compose)
            + audit_bind_problems(compose) + env_example_problems(env_example))


def test_AT_950_11_1_compose_has_exactly_one_writable_audit_bind_and_the_new_variables() -> None:
    compose = load_compose()
    assert audit_bind_problems(compose) == []
    bridge, backend = (compose["services"][n] for n in ("engine-bridge", "backend"))
    env = _env_of(bridge)
    assert env[AUDIT_ENV].startswith("/") and not env[AUDIT_ENV].startswith("/repo")
    assert env[TOKEN_ENV] == "${BRIDGE_SI_WRITE_TOKEN:-}"
    audit = [v for v in bridge["volumes"] if _volume_target(v) == env[AUDIT_ENV]]
    assert len(audit) == 1 and isinstance(audit[0], dict)
    assert audit[0]["type"] == "bind" and audit[0].get("read_only") is not True
    assert audit[0]["bind"]["create_host_path"] is False
    assert str(audit[0]["source"]).rstrip("/").endswith("console_audit")
    assert not HARD_CODED_DISK.match(str(audit[0]["source"]))
    for name in BACKEND_ENVS:
        assert _env_of(backend)[name] == "${" + name + ":-}", name
    # 其餘 SI bind 仍全為唯讀、既有掛載保留
    assert si_mount_problems(compose) == []
    writable = [v for v in bridge["volumes"] if _is_bind(v) and _is_writable(v)]
    assert writable == audit, "engine-bridge 唯一可寫的 bind 就是稽核目錄"
    assert [v for v in bridge["volumes"] if isinstance(v, str)] == list(EXISTING_MOUNTS)
    assert bridge_exposure_problems(compose) == []


def test_AT_950_11_E_1_the_deploy_checker_names_each_of_nine_broken_variants() -> None:
    base, env_text = load_compose(), ENV_EXAMPLE.read_text(encoding="utf-8")
    assert deploy_problems(base, env_text) == []
    audit_target = _env_of(base["services"]["engine-bridge"])[AUDIT_ENV]
    plain = _entry(base, audit_target)

    def audit_entry(compose: dict[str, Any]) -> dict[str, Any]:
        return _entry(compose, audit_target)

    def replace_audit(compose: dict[str, Any], new: Any) -> None:
        vols = _volumes(compose)
        vols[vols.index(audit_entry(compose))] = new

    variants: dict[str, tuple[Any, str, str]] = {
        # 名稱: (變更 compose 的函式, 變更 .env.example 文字的函式〔識別碼〕, 期望問題字樣)
        "audit-bind-short-syntax": (lambda c: replace_audit(
            c, f"{plain['source']}:{audit_target}"), "", "長語法"),
        "audit-bind-read-only": (lambda c: audit_entry(c).update(read_only=True), "", "不得唯讀"),
        "second-writable-si-bind": (lambda c: _volumes(c).append(
            {**_long("../docs", "/repo/docs"), "read_only": False}), "", "可寫的 bind"),
        "writable-repo-root": (lambda c: _volumes(c).append(
            {**_long("..", "/repo"), "read_only": False}), "", "可寫的 bind"),
        "mounts-the-whole-home": (lambda c: audit_entry(c).update(
            source="${USERPROFILE:-${HOME}}"), "", "console_audit 結尾"),
        "create-host-path-true": (lambda c: audit_entry(c)["bind"].update(create_host_path=True),
                                  "", "create_host_path"),
        "bridge-publishes-ports": (lambda c: c["services"]["engine-bridge"].update(
            ports=["8081:8081"]), "", "ports"),
        "env-example-has-a-real-value": (lambda c: None, "real-value", "不是 <YOUR_"),
        "missing-audit-env": (lambda c: c["services"]["engine-bridge"]["environment"].pop(
            AUDIT_ENV), "", AUDIT_ENV),
    }
    assert len(variants) == 9
    for name, (change, env_change, needle) in variants.items():
        bad_env = env_text
        if env_change == "real-value":
            bad_env = re.sub(r"^# BRIDGE_SI_WRITE_TOKEN=.*$",
                             "BRIDGE_SI_WRITE_TOKEN=0123456789abcdef0123456789abcdef", env_text,
                             flags=re.M)
            assert bad_env != env_text
        problems = deploy_problems(_mutate(base, change), bad_env)
        assert problems, f"{name}：壞變體沒有被指出"
        assert any(needle in p for p in problems), f"{name}：沒有指出 {needle!r}：{problems}"
    # 補：寫死磁碟路徑、機密形態字面
    hard = _mutate(base, lambda c: audit_entry(c).update(
        source="C:\\Users\\someone\\.autosdd\\selfimproving\\console_audit"))
    assert any("寫死磁碟路徑" in p for p in audit_bind_problems(hard))
    secret = env_text + "\nSOME_KEY=sk-" + "a" * 24 + "\n"
    assert any("機密形態" in p for p in env_example_problems(secret))
    # 真檔：三個新變數只有 <YOUR_…> 佔位、全檔無機密形態
    for name in BACKEND_ENVS:
        values = re.findall(rf"^#?[ \t]*{name}=(.*)$", env_text, re.M)
        assert values and all(re.fullmatch(r"<YOUR_[A-Z0-9_]+>", v.strip()) for v in values), name
    assert not re.search(r"sk-[A-Za-z0-9_\-]{20,}", env_text)


# ── 稽核目錄的映像前提（AT-965-10-3；勘誤 E-11，DEF-AC-036）──────────────────────────────────────
DOCKERFILE = CONSOLE_DIR / "engine-bridge" / "Dockerfile"


def _run_commands(dockerfile_text: str) -> tuple[list[str], int]:
    """把續行（行尾反斜線）併成一行後，回傳 `USER bridge` 之前所有 RUN 以 `&&` 切出的子指令，與
    `USER bridge` 是否出現（0＝沒有）。`USER bridge` 之後的 RUN 不計入（已非 root，chown 無效）。"""
    joined = re.sub(r"\\\n", " ", dockerfile_text)
    before: list[str] = []
    seen_user = 0
    for line in joined.splitlines():
        stripped = line.strip()
        if re.match(r"USER\s+bridge\s*$", stripped):
            seen_user = 1
            continue
        if seen_user or not stripped.startswith("RUN "):
            continue
        before.extend(part.strip() for part in stripped[4:].split("&&"))
    return before, seen_user


def audit_dir_image_problems(dockerfile_text: str, compose: dict[str, Any]) -> list[str]:
    """具名卷首次掛載會繼承映像內該目錄的擁有者：compose 裡 engine-bridge 的 `BRIDGE_SI_AUDIT_DIR`
    必須在 `USER bridge` 之前同時出現在 `mkdir -p` 與 `chown bridge:bridge` 的目錄清單中，否則
    全新具名卷為 root 擁有，Bridge（uid 10001）寫稽核檔 EACCES ⇒ 同步 503。"""
    svc = (compose.get("services") or {}).get("engine-bridge") or {}
    audit_dir = _env_of(svc).get(AUDIT_ENV, "").rstrip("/")
    if not audit_dir:
        return [f"engine-bridge 缺環境變數 {AUDIT_ENV}"]
    commands, saw_user = _run_commands(dockerfile_text)
    out: list[str] = []
    if not saw_user:
        out.append("Dockerfile 沒有 USER bridge（chown 時序無從判定）")
    mkdirs = [c.split()[3:] for c in commands if re.match(r"mkdir\s+-p\s", c)]
    chowns = [c.split()[2:] for c in commands if re.match(r"chown\s+bridge:bridge\s", c)]
    if not any(audit_dir in (d.rstrip("/") for d in dirs) for dirs in mkdirs):
        out.append(f"Dockerfile 的 mkdir -p 沒有預建 {audit_dir}")
    if not any(audit_dir in (d.rstrip("/") for d in dirs) for dirs in chowns):
        out.append(f"Dockerfile 在 USER bridge 之前沒有 chown bridge:bridge {audit_dir}")
    return out


def test_AT_965_10_3_the_bridge_image_owns_the_audit_dir_for_named_volumes() -> None:
    compose = load_compose()
    text = DOCKERFILE.read_text(encoding="utf-8")
    assert audit_dir_image_problems(text, compose) == []
    audit_dir = _env_of(compose["services"]["engine-bridge"])[AUDIT_ENV]
    assert audit_dir == "/si-audit" and audit_dir in text
    # 負控一：mkdir 缺稽核目錄
    no_mkdir = text.replace("mkdir -p /workspace /app/logs /si-audit",
                            "mkdir -p /workspace /app/logs")
    assert no_mkdir != text
    assert any("mkdir" in p for p in audit_dir_image_problems(no_mkdir, compose))
    # 負控二：chown 缺稽核目錄
    no_chown = text.replace("chown bridge:bridge /workspace /app/logs /si-audit",
                            "chown bridge:bridge /workspace /app/logs")
    assert no_chown != text
    assert any("chown" in p for p in audit_dir_image_problems(no_chown, compose))
    # 負控三：chown 搬到 USER bridge 之後（已非 root，不算數）
    late = text.replace(" \\\n && chown bridge:bridge /workspace /app/logs /si-audit", "")
    assert late != text
    late = late.replace("USER bridge\n", "USER bridge\nRUN chown bridge:bridge /si-audit\n")
    assert any("chown" in p for p in audit_dir_image_problems(late, compose))
    # 負控四：compose 改路徑而 Dockerfile 沒跟上
    moved = _mutate(compose, lambda c: c["services"]["engine-bridge"]["environment"].update(
        {AUDIT_ENV: "/audit-v2"}))
    problems = audit_dir_image_problems(text, moved)
    assert any("mkdir" in p for p in problems) and any("chown" in p for p in problems)
    # 負控五：compose 缺該變數
    gone = _mutate(compose, lambda c: c["services"]["engine-bridge"]["environment"].pop(AUDIT_ENV))
    assert any(AUDIT_ENV in p for p in audit_dir_image_problems(text, gone))


# ── CI paths 兩處都涵蓋根層輸入 ────────────────────────────────────────────────────────────────
def glob_regex(glob: str) -> re.Pattern[str]:
    """GitHub paths 的 glob：`**` 比對零至多段（含斜線），`*` 只比對單段內任意字元。"""
    out: list[str] = []
    i = 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif glob[i] == "*":
            out.append("[^/]*")
            i += 1
        elif glob[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    return re.compile("".join(out))


def uncovered(paths: Iterable[str], inputs: Iterable[str]) -> list[str]:
    patterns = [glob_regex(p) for p in paths if not p.startswith("!")]
    missing = []
    for item in inputs:
        # 目錄型輸入要能涵蓋「任意深度的檔」：同一個 glob 必須同時涵蓋淺與深兩個探針
        probes = [item + "x.py", item + "sub/deep/x.py"] if item.endswith("/") else [item]
        if not any(all(rx.fullmatch(p) for p in probes) for rx in patterns):
            missing.append(item)
    return missing


def ci_path_problems(workflow: dict[str, Any], inputs: Iterable[str]) -> list[str]:
    triggers = workflow.get("on", workflow.get(True)) or {}          # PyYAML 把鍵 `on` 讀成 True
    out: list[str] = []
    for trigger in ("pull_request", "push"):
        paths = (triggers.get(trigger) or {}).get("paths") or []
        out += [f"{trigger}：缺 {item}" for item in uncovered(paths, inputs)]
        for must in ("AgentConsole/**", ".github/workflows/agentconsole-ci.yml"):
            if must not in paths:
                out.append(f"{trigger}：paths 不再含 {must}")
    return out


#: P2b 起差分測試與入帳測試的根層輸入＝寫入閉包加協定參數檔（D10：`agentconsole-ci.yml` 的 paths 由
#: 主控同 commit 補上 `tools/lib/apply_lock.py` 與 `tools/lib/sdd_latest.py`；補上之前下面兩個
#: 涵蓋 AT 為預期紅）。
SI_INPUTS = (*sup.WRITE_CLOSURE, sup.PARAMS_SRC)


def test_AT_940_4_1_ci_paths_cover_every_root_input_of_the_differential_tests() -> None:
    assert sup.CLI_CLOSURE, "CLI_CLOSURE 不得為空"
    assert sup.PARAMS_SRC == "docs/06_quality/SelfImproving_Protocol/params.json"
    for rel in SI_INPUTS:
        assert (sup.MONOREPO / rel.rstrip("/")).exists(), f"輸入在 monorepo 內不存在：{rel}"
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert ci_path_problems(workflow, SI_INPUTS) == [], \
        "agentconsole-ci.yml 的 on.pull_request.paths 與 on.push.paths 須兩處都涵蓋這些輸入（D11）"


def _workflow(paths: list[str], *, push_paths: list[str] | None = None) -> dict[str, Any]:
    keep = ["AgentConsole/**", ".github/workflows/agentconsole-ci.yml"]
    return {"on": {"pull_request": {"paths": [*keep, *paths]},
                   "push": {"paths": [*keep, *(paths if push_paths is None else push_paths)]}}}


FULL_PATHS = ["tools/selfimproving.py", "tools/_stdio_utf8.py", "tools/lib/platform_utils.py",
              "tools/lib/selfimproving/**", "tools/lib/apply_lock.py", "tools/lib/sdd_latest.py",
              "docs/06_quality/SelfImproving_Protocol/params.json",
              # P4 閉包（Console TCS D-CS-23）：sched.py 頂層 import transcript_activity 連鎖
              "tools/lib/transcript_activity.py", "tools/lib/quota_limits.py",
              "tools/lib/quota_messages.py", "tools/lib/model_roles.py",
              "tools/lib/quota_policy.py", "tools/lib/quota_policy_env.py",
              "tools/lib/quota_pace.py", "tools/lib/quota_burndown.py",
              "tools/lib/endurance_env.py", "tools/lib/unattended_authz.py"]


def test_AT_940_4_E_1_the_coverage_checker_names_what_is_missing_and_where() -> None:
    assert ci_path_problems(_workflow(FULL_PATHS), SI_INPUTS) == []
    no_dir = [p for p in FULL_PATHS if p != "tools/lib/selfimproving/**"]
    problems = ci_path_problems(_workflow(no_dir), SI_INPUTS)
    assert any("pull_request" in p and "tools/lib/selfimproving/" in p for p in problems)
    assert any("push" in p and "tools/lib/selfimproving/" in p for p in problems)
    no_file = [p for p in FULL_PATHS if p != "tools/selfimproving.py"]
    problems = ci_path_problems(_workflow(no_file), SI_INPUTS)
    assert problems and all("tools/selfimproving.py" in p for p in problems)
    only_pr = ci_path_problems(_workflow(FULL_PATHS, push_paths=[]), SI_INPUTS)
    assert only_pr and all(p.startswith("push") for p in only_pr), only_pr
    narrow = [("tools/lib/selfimproving/*" if p.endswith("selfimproving/**") else p)
              for p in FULL_PATHS]
    problems = ci_path_problems(_workflow(narrow), SI_INPUTS)
    assert any("tools/lib/selfimproving/" in p for p in problems), "glob 只涵蓋單層必須被指出"
    assert ci_path_problems(_workflow(["tools/**", "docs/06_quality/**"]), SI_INPUTS) == [], \
        "較寬的 glob 本來就涵蓋，不應被誤報"


# AT-950-11-2：寫入閉包新增的兩個根層檔（兩個觸發器）——真檔的涵蓋與負控樣本
WRITE_ONLY_INPUTS = sup.WRITE_ONLY_FILES


def test_AT_950_11_2_ci_paths_cover_the_write_closure_inputs_in_both_triggers() -> None:
    assert sup.WRITE_CLOSURE == (*sup.CLI_CLOSURE, *WRITE_ONLY_INPUTS)
    assert set(WRITE_ONLY_INPUTS) == {"tools/lib/apply_lock.py", "tools/lib/sdd_latest.py"}
    for rel in SI_INPUTS:
        assert (sup.MONOREPO / rel.rstrip("/")).exists(), f"輸入在 monorepo 內不存在：{rel}"
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert ci_path_problems(workflow, SI_INPUTS) == [], \
        "pull_request 與 push 兩處的 paths 都須涵蓋寫入閉包的每個根層輸入（D10 由主控補上）"
    # 負控樣本：各自回報缺哪一項
    for missing in WRITE_ONLY_INPUTS:
        problems = ci_path_problems(
            _workflow([p for p in FULL_PATHS if p != missing]), SI_INPUTS)
        assert any("pull_request" in p and missing in p for p in problems), (missing, problems)
        assert any(p.startswith("push") and missing in p for p in problems), (missing, problems)
    no_dir = [p for p in FULL_PATHS if p != "tools/lib/selfimproving/**"]
    assert any("tools/lib/selfimproving/" in p
               for p in ci_path_problems(_workflow(no_dir), SI_INPUTS)), "缺目錄 glob 必須被指出"
    only_pr = ci_path_problems(_workflow(FULL_PATHS, push_paths=[]), SI_INPUTS)
    assert only_pr and all(p.startswith("push") for p in only_pr), "只有一個觸發器必須被指出"
    narrow = ["tools/lib/selfimproving/*" if p.endswith("selfimproving/**") else p
              for p in FULL_PATHS]
    assert any("tools/lib/selfimproving/" in p
               for p in ci_path_problems(_workflow(narrow), SI_INPUTS)), "glob 只涵蓋單層必須被指出"


# ── 巡邏回報目錄（TCS-SiFlowVisibility-20261111：AT-966-2-1～2-5、2-E-1）──────────────
REPORT_ENV, REPORT_TARGET = "BRIDGE_SI_REPORT_DIR", "/si-report"
DOCKER_README = CONSOLE_DIR / "docker" / "README.md"
ARCHITECTURE = CONSOLE_DIR / "docs" / "02_architecture" / "Architecture.md"


def report_bind_problems(compose: dict[str, Any]) -> list[str]:
    """巡邏回報目錄的部署前提（W-F2）：engine-bridge 的 `BRIDGE_SI_REPORT_DIR` 等於 `/si-report`，
    不在 `/repo` 之下、不等於稽核目錄；恰一條 target 為該值的 bind，長語法、`type: bind`、
    `read_only: true`、`create_host_path: false`、來源以 `console_report` 結尾且不寫死
    磁碟路徑、與稽核 bind 的來源使用同一個 `${AUTOSDD_SI_DIR:-…}` 前綴運算式但不是同一個
    目錄；engine-bridge 唯一可寫的 bind 仍是稽核目錄。"""
    svc = (compose.get("services") or {}).get("engine-bridge") or {}
    env = _env_of(svc)
    volumes = svc.get("volumes") or []
    out: list[str] = []
    report_dir, audit_dir = env.get(REPORT_ENV, ""), env.get(AUDIT_ENV, "")
    audit = [v for v in volumes
             if audit_dir and _volume_target(v).rstrip("/") == audit_dir.rstrip("/")]
    report: list[Any] = []
    if not report_dir:
        out.append(f"engine-bridge 缺環境變數 {REPORT_ENV}")
    else:
        if report_dir != REPORT_TARGET:
            out.append(f"{REPORT_ENV} 須為 {REPORT_TARGET}，實際 {report_dir!r}")
        if report_dir.startswith("/repo"):
            out.append(f"{REPORT_ENV} 不得落在 /repo 之下（那是唯讀鏡像）")
        if report_dir.rstrip("/") == audit_dir.rstrip("/"):
            out.append(f"{REPORT_ENV} 不得等於 {AUDIT_ENV}")
        report = [v for v in volumes if _volume_target(v).rstrip("/") == report_dir.rstrip("/")]
        if len(report) != 1:
            out.append(f"{REPORT_ENV} 必須恰有一條對應的 bind，實際 {len(report)}")
    for vol in report[:1]:
        if not isinstance(vol, dict):
            out.append("巡邏回報 bind 須用長語法（才能明寫 read_only 與 create_host_path）")
            continue
        if vol.get("type") != "bind":
            out.append("巡邏回報 bind 的 type 必須是 bind")
        if vol.get("read_only") is not True:
            out.append("巡邏回報 bind 必須唯讀（read_only: true；Bridge 對快照只讀）")
        if (vol.get("bind") or {}).get("create_host_path") is not False:
            out.append("巡邏回報 bind 的 create_host_path 必須明寫 false（缺席時要明確失敗）")
        source = str(vol.get("source", ""))
        flat = source.replace("\\", "/").rstrip("/")
        if not flat.endswith("console_report"):
            out.append(f"巡邏回報 bind 的 source 必須以 console_report 結尾，實際 {flat!r}")
        if HARD_CODED_DISK.match(flat):
            out.append(f"巡邏回報 bind 的 source 不得寫死磁碟路徑：{flat!r}")
        for avol in audit[:1]:
            asrc = str(avol.get("source", "")) if isinstance(avol, dict) else ""
            if asrc and asrc == source:
                out.append("巡邏回報 bind 的 source 與稽核 bind 的 source 相同（須是兩個目錄）")
            elif (asrc.endswith("console_audit") and source.endswith("console_report")
                  and asrc[:-len("console_audit")] != source[:-len("console_report")]):
                out.append("巡邏回報 bind 與稽核 bind 的 AUTOSDD_SI_DIR 前綴運算式不一致")
    writable = [v for v in volumes if _is_bind(v) and _is_writable(v)]
    if writable != audit[:1]:
        out.append(f"engine-bridge 只能有一條可寫的 bind（稽核目錄），實際 {writable}")
    return out


def test_AT_966_2_1_compose_has_the_read_only_report_bind_and_the_env_var() -> None:
    compose = load_compose()
    assert report_bind_problems(compose) == []
    bridge = compose["services"]["engine-bridge"]
    env = _env_of(bridge)
    assert env[REPORT_ENV] == "/si-report" and not env[REPORT_ENV].startswith("/repo")
    assert env[REPORT_ENV] != env[AUDIT_ENV]
    mounts = [v for v in bridge["volumes"] if _volume_target(v) == "/si-report"]
    assert len(mounts) == 1 and isinstance(mounts[0], dict)
    assert mounts[0]["type"] == "bind" and mounts[0]["read_only"] is True
    assert mounts[0]["bind"]["create_host_path"] is False
    assert str(mounts[0]["source"]).endswith("console_report")
    assert not HARD_CODED_DISK.match(str(mounts[0]["source"]))
    audit = next(v for v in bridge["volumes"] if _volume_target(v) == env[AUDIT_ENV])
    assert str(audit["source"]).removesuffix("console_audit") == \
        str(mounts[0]["source"]).removesuffix("console_report"), "同一個 AUTOSDD_SI_DIR 前綴運算式"
    assert audit_bind_problems(compose) == [], "engine-bridge 唯一可寫的 bind 仍是稽核目錄"
    assert si_mount_problems(compose) == [], "既有六條 /repo 唯讀 bind 與設計 A 逐條不變"
    assert design_of(compose) == "A"
    writable = [v for v in bridge["volumes"] if _is_bind(v) and _is_writable(v)]
    assert writable == [audit]


def test_AT_966_2_2_settings_parse_the_report_dir_with_the_anchor_guard(tmp_path: Path) -> None:
    from app.settings import SettingsError, load_settings

    audit = tmp_path / "audit"
    report = tmp_path / "report"
    assert load_settings({}).si_report_dir is None
    assert load_settings({REPORT_ENV: "   "}).si_report_dir is None
    got = load_settings({REPORT_ENV: "/si-report"}).si_report_dir
    assert got == Path("/si-report").resolve()
    assert load_settings({REPORT_ENV: str(report)}).si_report_dir == report.resolve()
    assert not report.exists(), "設定解析不得建立目錄、不檢查存在性"
    for name, raw in {"relative": "relative/path", "disk-root": "/",
                      "anchor": str(Path(tmp_path.anchor))}.items():
        with pytest.raises(SettingsError) as caught:
            load_settings({REPORT_ENV: raw})
        assert REPORT_ENV in str(caught.value), name
    with pytest.raises(SettingsError) as same:
        load_settings({REPORT_ENV: str(audit), AUDIT_ENV: str(audit)})
    assert "BRIDGE_SI_AUDIT_DIR" in str(same.value) and REPORT_ENV in str(same.value)
    both = load_settings({REPORT_ENV: str(report), AUDIT_ENV: str(audit)})
    assert both.si_report_dir == report.resolve() and both.si_audit_dir == audit.resolve()
    # 既有稽核目錄與寫入面行為不變
    assert both.si_write_enabled is False
    assert load_settings({AUDIT_ENV: str(audit)}).si_audit_dir == audit.resolve()
    assert load_settings({AUDIT_ENV: str(audit)}).si_report_dir is None


def test_AT_966_2_3_the_report_checker_names_each_of_nine_broken_variants() -> None:
    base = load_compose()
    assert report_bind_problems(base) == []
    audit_target = _env_of(base["services"]["engine-bridge"])[AUDIT_ENV]
    audit_source = str(_entry(base, audit_target)["source"])

    def report_entry(compose: dict[str, Any]) -> dict[str, Any]:
        return _entry(compose, REPORT_TARGET)

    def short_syntax(compose: dict[str, Any]) -> None:
        vols = _volumes(compose)
        entry = report_entry(compose)
        vols[vols.index(entry)] = f"{entry['source']}:{REPORT_TARGET}:ro"

    def under_repo(compose: dict[str, Any]) -> None:
        compose["services"]["engine-bridge"]["environment"][REPORT_ENV] = "/repo/si-report"
        report_entry(compose)["target"] = "/repo/si-report"

    variants: dict[str, tuple[Any, str]] = {
        "report-writable": (lambda c: report_entry(c).pop("read_only"), "read_only"),
        "create-host-path-true": (lambda c: report_entry(c)["bind"].update(
            create_host_path=True), "create_host_path"),
        "short-syntax": (short_syntax, "長語法"),
        "under-repo": (under_repo, "/repo"),
        "missing-env": (lambda c: c["services"]["engine-bridge"]["environment"].pop(REPORT_ENV),
                        "缺環境變數"),
        "wrong-source-suffix": (lambda c: report_entry(c).update(
            source=str(report_entry(c)["source"]).replace("console_report", "console_audit")),
            "console_report"),
        "hard-coded-disk": (lambda c: report_entry(c).update(
            source="C:\\Users\\someone\\.autosdd\\selfimproving\\console_report"), "寫死磁碟路徑"),
        "same-as-audit": (lambda c: report_entry(c).update(source=audit_source),
                          "與稽核 bind 的 source 相同"),
        "second-writable-bind": (lambda c: _volumes(c).append(
            {**_long("../docs", "/repo/docs"), "read_only": False}), "可寫的 bind"),
    }
    assert len(variants) == 9
    for name, (change, needle) in variants.items():
        problems = report_bind_problems(_mutate(base, change))
        assert problems, f"{name}：壞變體沒有被指出"
        assert any(needle in p for p in problems), f"{name}：沒有指出 {needle!r}：{problems}"


def _section(text: str, heading: str) -> str:
    start = text.index(heading)
    nxt = text.find("\n## ", start + 1)
    return text[start:] if nxt < 0 else text[start:nxt]


def test_AT_966_2_4_env_example_readme_and_architecture_describe_the_report_dir() -> None:
    env_text = ENV_EXAMPLE.read_text(encoding="utf-8")
    assert env_example_problems(env_text) == [], ".env.example 只准有 <YOUR_…> 佔位、無真機密"
    lines = env_text.splitlines()
    ps = [ln for ln in lines
          if "New-Item -ItemType Directory -Force" in ln and "console_report" in ln]
    sh = [ln for ln in lines if "mkdir -p" in ln and "console_report" in ln]
    assert len(ps) == 1 and len(sh) == 1, "雙 shell 預建指令各一條"
    for ln in (*ps, *sh):
        assert "AUTOSDD_SI_DIR" in ln, "使用 AUTOSDD_SI_DIR 預設運算式的展開寫法"
        assert not re.search(r"[A-Za-z]:[\\/]|/Users/|/home/|/Volumes/|/mnt/", ln), "不寫死磁碟路徑"
    assert "docker compose up" in env_text and "console_report" in env_text

    readme = DOCKER_README.read_text(encoding="utf-8")
    section = _section(readme, "巡邏回報目錄")
    markers = ["console_report", "build engine-bridge backend frontend", "up -d",
               "/api/v1/si/patrol"]
    positions: list[int] = []
    cursor = 0
    for marker in markers:
        found = section.find(marker, cursor)
        assert found >= 0, f"README〈巡邏回報目錄〉缺少 {marker!r}（或順序不對）"
        positions.append(found)
        cursor = found + 1
    assert positions == sorted(positions), "順序須為 建目錄→重建映像→啟動→驗證"
    assert "mkdir -p" in section and "New-Item -ItemType Directory -Force" in section
    assert "report_missing" in section and "report_dir_unset" in section
    for heading in ("**失敗表徵**", "**退回**", "**未掛載時的畫面**"):
        assert heading in section, f"缺少 {heading} 一段"
    assert "bind source path does not exist" in section, "目錄未建時 compose 拒絕啟動的訊息"
    assert "漏了 backend" in section and "漏了 frontend" in section, "漏重建某映像的症狀"

    arch = ARCHITECTURE.read_text(encoding="utf-8")
    rows = [ln for ln in arch.splitlines() if ln.startswith("| `BRIDGE_SI_REPORT_DIR`")]
    assert len(rows) == 1, "Architecture §9.4 表須有 BRIDGE_SI_REPORT_DIR 一列"
    assert "report_dir_unset" in rows[0]
    three = {".env.example": env_text, "docker/README.md": readme, "§9.4 列": rows[0]}
    for name, text in three.items():
        assert "第二條可寫 bind" not in text, f"{name} 不得出現「第二條可寫 bind」字樣"


def test_AT_966_2_5_unset_report_dir_only_affects_the_patrol_endpoint(
        tmp_path: Path, settings: Any, make_bridge: Any) -> None:
    from dataclasses import replace

    from tests.fake_si import make_fake_si, proposal_item, set_control

    fake = make_fake_si(tmp_path)
    set_control(fake, items=[proposal_item(with_detail=False)])
    legacy = replace(settings, si_root=fake, si_report_dir=None)
    live = make_bridge(legacy)
    assert live.client.get("/si/status").status_code == 200
    assert live.client.get("/si/proposals").status_code == 200
    assert live.client.get("/health").status_code == 200
    deep_legacy = live.client.get("/health/deep")
    patrol = live.client.get("/si/patrol")
    assert patrol.status_code == 503 and patrol.json()["cause"] == "report_dir_unset"
    # 設了目錄的部署，深度探針的項目集合與未設者完全相同（巡邏回報目錄不進深度探針）
    configured = make_bridge(replace(legacy, si_report_dir=tmp_path / "console_report"))
    deep_configured = configured.client.get("/health/deep")
    assert set(deep_legacy.json()) == set(deep_configured.json())
    checks_a = set(deep_legacy.json().get("checks", {}))
    checks_b = set(deep_configured.json().get("checks", {}))
    assert checks_a == checks_b
    assert "patrol" not in deep_configured.text and "si-report" not in deep_configured.text


def test_AT_966_2_E_1_docker_compose_config_expands_the_read_only_report_volume(
        tmp_path: Path) -> None:
    import json
    import os
    import subprocess

    sentinel = {name: f"sentinel-{name.lower()}" for name in (
        "POSTGRES_PASSWORD", "JWT_SECRET", "CONSOLE_ENCRYPTION_KEY", "MINIMAX_API_KEY",
        "REPLICATION_PASSWORD", "PGBACKREST_CIPHER_PASS", "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY", "MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD", "PGADMIN_PASSWORD",
        "GRAFANA_PASSWORD")}
    env = {**os.environ, **sentinel, "AUTOSDD_SI_DIR": str(tmp_path)}
    proc = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE), "--profile", "db", "--profile", "app",
         "--profile", "full", "config", "--format", "json"],
        capture_output=True, env=env, timeout=120, check=False)
    rc = proc.returncode
    assert rc == 0, f"docker compose config rc={rc}：{proc.stderr.decode('utf-8', 'replace')[:400]}"
    expanded = json.loads(proc.stdout.decode("utf-8"))
    volumes = expanded["services"]["engine-bridge"]["volumes"]
    by_target = {v["target"]: v for v in volumes}
    report, audit = by_target["/si-report"], by_target["/si-audit"]
    assert report["type"] == "bind" and report["read_only"] is True
    # create_host_path 是否出現在展開結果隨 compose 版本而異（CI 版本省略該鍵）；它的 false 設定由
    # 上面的靜態檢查守，這裡只守展開後真的有效的唯讀掛載、來源與目標
    assert os.path.normcase(os.path.normpath(report["source"])) == os.path.normcase(
        os.path.normpath(str(tmp_path / "console_report")))
    assert audit.get("read_only", False) is False
    assert os.path.normcase(os.path.normpath(audit["source"])) == os.path.normcase(
        os.path.normpath(str(tmp_path / "console_audit")))
