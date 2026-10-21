"""P1b 的部署前置與文件連動的靜態檢查（TCS-SelfImprovingMirror-P1b：AT-932-4-4、AT-940-1-E-1、
AT-940-3-1、AT-940-3-E-1、AT-940-4-1、AT-940-4-E-1）。

只讀檔、不起 Docker：compose 的 engine-bridge 服務沒有對 host 發布任何埠（Architecture §12.1 L-6
的 P 型劃界補機械物）、唯讀掛載恰符合具名設計 A 或 B 其中之一、README 與 settings 檔頭已列
`SI_ROOT` 與端點、`agentconsole-ci.yml` 的 `paths` 兩處都涵蓋差分測試的根層輸入。每個檢查都是純
函式（輸入為解析後的結構或文字，輸出為問題清單），真檔必須回空、各壞變體必須逐一回非空。AT 內不引用
其他 AT 的 ID。
"""
from __future__ import annotations

import ast
import copy
import re
from collections.abc import Iterable
from typing import Any

import pytest
import yaml

from tests import si_repo_support as sup

CONSOLE_DIR = sup.MONOREPO / "AgentConsole"
COMPOSE = CONSOLE_DIR / "docker-compose.yml"
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


# ── compose 的 SI 掛載：恰符合設計 A 或 B ─────────────────────────────────────────────────────
EXISTING_MOUNTS = ("../AISDLC_SDD:/sdd:ro", "engine_workspace:/workspace", "app_logs:/app/logs")
COMMON = {("../tools", "/repo/tools"), ("../docs/06_quality", "/repo/docs/06_quality")}
DESIGN_A = COMMON | {("../.git/HEAD", "/repo/.git/HEAD"), ("../.git/refs", "/repo/.git/refs"),
                     ("../.git/objects", "/repo/.git/objects"),
                     ("../.git/packed-refs", "/repo/.git/packed-refs")}
DESIGN_B = COMMON | {("../.git", "/repo/.git"),
                     ("./docker/si/git-config.empty", "/repo/.git/config")}


def _short_target(raw: str) -> str:
    parts = raw.split(":")
    return parts[1] if len(parts) >= 2 else raw


def si_mount_problems(compose: dict[str, Any]) -> list[str]:
    svc = (compose.get("services") or {}).get("engine-bridge") or {}
    out: list[str] = []
    env = svc.get("environment") or {}
    if isinstance(env, list):
        env = dict(item.split("=", 1) for item in env)
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
    assert design_of(compose) in ("A", "B")
    for vol in compose["services"]["engine-bridge"]["volumes"]:
        if isinstance(vol, dict) and vol["target"].startswith("/repo"):
            assert vol["read_only"] is True and vol["type"] == "bind"
    if design_of(compose) == "A":
        for vol in compose["services"]["engine-bridge"]["volumes"]:
            if isinstance(vol, dict):
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


SI_INPUTS = (*sup.CLI_CLOSURE, sup.PARAMS_SRC)


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
              "tools/lib/selfimproving/**", "docs/06_quality/SelfImproving_Protocol/params.json"]


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
