"""研究面的部署接線鎖（TCS AT-960-2-E-2；AC-R2P-10-3、AC-R2P-04-11）。

檢查函式 `deploy_problems(compose, env_example, dockerfile)` 只吃文字、回問題清單，所以能對真檔
實跑（零問題），也能對各缺陷變體驗證「該回報的各自回報」。判準：
  · 持有 `BRIDGE_RESEARCH_WRITE_TOKEN` 的 compose 服務恰為 backend（發送）與 engine-bridge
    （驗證），值逐字為 `${BRIDGE_RESEARCH_WRITE_TOKEN:-}`（預設空＝停用）；任何地方都不得是 `:?`
    必填（研究面是選用功能，必填會讓不用它的部署起不來）；
  · engine-bridge 另固定 `BRIDGE_RESEARCH_ROOT: /workspace/my-project`（唯一可寫卷之下）與
    `BRIDGE_RESEARCH_CLAUDE_COMMAND: aisdlc-mock-claude`（全棧 E2E 只跑確定性替身）；
  · `.env.example` 的權杖列只有佔位，且 `load_settings` 逐字拒絕（原樣取消註解照抄＝啟動即失敗）；
  · Bridge 的 Dockerfile 沒有安裝 `claude` 或 `gh` 的指令（TCS 寫「docker/ 下」，實際檔在
    `AgentConsole/engine-bridge/Dockerfile`）。

只做靜態檢查（讀檔、不起 Docker）；同型的 SDD 權杖鎖在 `test_deploy_config.py`。
"""
from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.settings import SettingsError, load_settings

CONSOLE_DIR = Path(__file__).resolve().parents[2]            # <monorepo>/AgentConsole
COMPOSE = CONSOLE_DIR / "docker-compose.yml"
ENV_EXAMPLE = CONSOLE_DIR / ".env.example"
DOCKERFILE = CONSOLE_DIR / "engine-bridge" / "Dockerfile"

TOKEN = "BRIDGE_RESEARCH_WRITE_TOKEN"
TOKEN_VALUE = "${BRIDGE_RESEARCH_WRITE_TOKEN:-}"
PLACEHOLDER = "<YOUR_BRIDGE_RESEARCH_WRITE_TOKEN_MIN_32_CHARS>"
HOLDERS = ["backend", "engine-bridge"]
BRIDGE_CONSTANTS = {"BRIDGE_RESEARCH_ROOT": "/workspace/my-project",
                    "BRIDGE_RESEARCH_CLAUDE_COMMAND": "aisdlc-mock-claude"}
#: 指令內「獨立的 claude／gh」與兩者的常見安裝來源；`aisdlc-mock-claude`、`AutoClaude`、
#: `GH_TOKEN`、`ghcr.io` 都因前後有詞字元或連字號而不命中。
CLI_INSTALL = re.compile(
    r"(?<![\w.-])(?:claude|gh)(?![\w-])|claude-code|github-cli|cli\.github\.com"
    r"|github\.com/cli/cli|claude\.ai/install", re.IGNORECASE)
INSTALLING = frozenset({"RUN", "COPY", "ADD"})
Loader = Callable[[Mapping[str, str]], Any]


# ══ 檢查函式 ═════════════════════════════════════════════════════════════════════════════
def service_env(body: Mapping[str, Any]) -> dict[str, str]:
    """compose 服務的 environment（映射或 `KEY=value` 清單兩種寫法都認）。"""
    env = body.get("environment") or {}
    if isinstance(env, list):
        return {key: value for key, _, value in (str(item).partition("=") for item in env)}
    return {str(key): "" if value is None else str(value) for key, value in env.items()}


def instruction_lines(dockerfile: str) -> list[str]:
    """Dockerfile 的指令：行尾反斜線接續合併，去掉註解行與空行。"""
    out: list[str] = []
    buf: list[str] = []
    for raw in dockerfile.splitlines():
        text = raw.strip()
        if not text or text.startswith("#"):
            continue
        continued = text.endswith("\\")
        buf.append(text[:-1].strip() if continued else text)
        if not continued:
            out.append(" ".join(buf))
            buf = []
    return out + ([" ".join(buf)] if buf else [])


def cli_install_lines(dockerfile: str) -> list[str]:
    return [line for line in instruction_lines(dockerfile)
            if line.split(None, 1)[0].upper() in INSTALLING and CLI_INSTALL.search(line)]


def refuses(loader: Loader, value: str) -> bool:
    """Bridge 對這個權杖值啟動失敗，且錯誤訊息指出變數名（不是因為別的原因失敗）。"""
    try:
        loader({TOKEN: value})
    except SettingsError as exc:
        return TOKEN in str(exc)
    return False


def deploy_problems(compose: str, env_example: str, dockerfile: str, *,
                    loader: Loader = load_settings) -> list[str]:
    out: list[str] = []
    services = (yaml.safe_load(compose) or {}).get("services") or {}
    holders = sorted(name for name, body in services.items() if TOKEN in service_env(body))
    if holders != HOLDERS:
        out.append(f"持有 {TOKEN} 的服務應恰為 {HOLDERS}，實際 {holders}")
    for name in HOLDERS:
        value = service_env(services.get(name) or {}).get(TOKEN)
        if value is not None and value != TOKEN_VALUE:
            out.append(f"{name}：{TOKEN} 必須逐字為 {TOKEN_VALUE}（預設空），實際 {value!r}")
    if re.search(rf"{TOKEN}:\?", compose):
        out.append(f"{TOKEN} 不得是 `:?` 必填形態（不用研究面的部署會起不來）")
    bridge = service_env(services.get("engine-bridge") or {})
    out += [f"engine-bridge：{key} 應為 {want}，實際 {bridge.get(key)!r}"
            for key, want in BRIDGE_CONSTANTS.items() if bridge.get(key) != want]
    entries = re.findall(rf"^\s*#?\s*{TOKEN}=(.*)$", env_example, flags=re.MULTILINE)
    if entries != [PLACEHOLDER]:
        out.append(f".env.example：{TOKEN} 只准有一列佔位，實際 {len(entries)} 列、"
                   f"長度 {[len(entry) for entry in entries]}")
    elif not refuses(loader, entries[0]):
        out.append(f".env.example：佔位字串沒有被 Bridge 的設定載入逐字拒絕（{TOKEN}）")
    out += [f"Dockerfile：映像不得安裝 claude 或 gh，卻有指令 {line!r}"
            for line in cli_install_lines(dockerfile)]
    return out


# ══ 真檔 ═════════════════════════════════════════════════════════════════════════════════
def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_AT_960_2_E_2_the_real_deployment_files_pass_every_check() -> None:
    compose, env_example, dockerfile = read(COMPOSE), read(ENV_EXAMPLE), read(DOCKERFILE)
    assert deploy_problems(compose, env_example, dockerfile) == []


def test_AT_960_2_E_2_the_real_compose_has_the_two_holders_and_the_bridge_constants() -> None:
    compose = read(COMPOSE)
    services = yaml.safe_load(compose)["services"]
    assert sorted(name for name, body in services.items()
                  if TOKEN in service_env(body)) == HOLDERS
    assert all(service_env(services[name])[TOKEN] == TOKEN_VALUE for name in HOLDERS)
    assert f"{TOKEN}:?" not in compose, "必填會讓不用研究面的部署起不來"
    bridge = service_env(services["engine-bridge"])
    assert {key: bridge[key] for key in BRIDGE_CONSTANTS} == BRIDGE_CONSTANTS


def test_AT_960_2_E_2_the_env_example_holds_only_the_placeholder_and_load_settings_refuses_it(
        tmp_path: Path) -> None:
    text = read(ENV_EXAMPLE)
    entries = re.findall(rf"^\s*#?\s*{TOKEN}=(.*)$", text, flags=re.MULTILINE)
    assert entries == [PLACEHOLDER], "範例檔只准放佔位，不放任何真值"
    with pytest.raises(SettingsError) as caught:       # 原樣取消註解照抄＝啟動即失敗
        load_settings({"ENGINE_WORKSPACE": str(tmp_path), TOKEN: entries[0]})
    assert TOKEN in str(caught.value) and entries[0] not in str(caught.value)


def test_AT_960_2_E_2_the_real_dockerfile_installs_neither_claude_nor_gh() -> None:
    lines = instruction_lines(read(DOCKERFILE))
    assert any("apt-get install" in line and " git " in f" {line} " for line in lines), \
        "非空證明：掃描器讀得到真正的安裝指令（git 與 ca-certificates）"
    assert cli_install_lines(read(DOCKERFILE)) == []


# ══ 缺陷變體：檢查函式必須各自回報 ═══════════════════════════════════════════════════════════
GOOD_COMPOSE = f"""\
services:
  frontend:
    environment:
      NEXT_PUBLIC_API_URL: ""
  backend:
    environment:
      BRIDGE_SDD_WRITE_TOKEN: ${{BRIDGE_SDD_WRITE_TOKEN:-}}
      {TOKEN}: {TOKEN_VALUE}
  engine-bridge:
    environment:
      BRIDGE_RESEARCH_ROOT: /workspace/my-project
      {TOKEN}: {TOKEN_VALUE}
      BRIDGE_RESEARCH_CLAUDE_COMMAND: aisdlc-mock-claude
"""
GOOD_ENV = f"# 研究寫入面\n# {TOKEN}={PLACEHOLDER}\nJWT_SECRET=<YOUR_JWT_SECRET_MIN_32_CHARS>\n"
GOOD_DOCKERFILE = """\
# 映像不含 Claude Code CLI（`claude`）與 gh；E2E 用 `aisdlc-mock-claude`。
FROM python:3.11-slim
ENV AUTOCLAUDE_ROOT=/opt/AutoClaude \\
    BRIDGE_RESEARCH_CLAUDE_COMMAND=aisdlc-mock-claude
RUN apt-get update \\
 && apt-get install -y --no-install-recommends git ca-certificates \\
 && rm -rf /var/lib/apt/lists/*
COPY AutoClaude/ /opt/AutoClaude/
RUN pip install /opt/AutoClaude /opt/engine-bridge
"""
BASES = {"compose": GOOD_COMPOSE, "env": GOOD_ENV, "docker": GOOD_DOCKERFILE}
REAL_TOKEN_LINE = f"{TOKEN}: {TOKEN_VALUE}"
EXTRA_ENV = f'NEXT_PUBLIC_API_URL: ""\n      {REAL_TOKEN_LINE}'
FRONTEND_ENV = '    environment:\n      NEXT_PUBLIC_API_URL: ""'
CLAUDE_CMD = "BRIDGE_RESEARCH_CLAUDE_COMMAND"
MOCK_CMD = f"{CLAUDE_CMD}: aisdlc-mock-claude"
LIST_OLD = ("    environment:\n      BRIDGE_RESEARCH_ROOT: /workspace/my-project\n"
            f"      {REAL_TOKEN_LINE}\n      {MOCK_CMD}\n")
LIST_NEW = ("    environment:\n      - BRIDGE_RESEARCH_ROOT=/workspace/my-project\n"
            f"      - {TOKEN}={TOKEN_VALUE}\n      - {CLAUDE_CMD}=aisdlc-mock-claude\n")


def accepts_everything(_env: Mapping[str, str]) -> None:
    return None


# (id, 文件, 被換掉的字串或 None＝附加在檔尾, 換成什麼, 問題必含的字樣)
DEFECTS: list[tuple[str, str, str | None, str, str]] = [
    ("an-extra-service-holds-the-token", "compose", 'NEXT_PUBLIC_API_URL: ""', EXTRA_ENV, "持有"),
    ("the-extra-holder-uses-the-list-form", "compose", FRONTEND_ENV,
     f"    environment:\n      - {TOKEN}={TOKEN_VALUE}", "持有"),
    ("backend-lost-the-token", "compose", f"      {REAL_TOKEN_LINE}\n  engine-bridge:",
     "      JWT_SECRET: x\n  engine-bridge:", "持有"),
    ("engine-bridge-lost-the-token", "compose", f"      {REAL_TOKEN_LINE}\n      {CLAUDE_CMD}",
     f"      {CLAUDE_CMD}", "持有"),
    ("the-empty-default-is-missing", "compose", f"{REAL_TOKEN_LINE}\n  engine-bridge:",
     f"{TOKEN}: ${{{TOKEN}}}\n  engine-bridge:", "預設空"),
    ("the-token-is-hard-coded", "compose", f"{REAL_TOKEN_LINE}\n      {CLAUDE_CMD}",
     f"{TOKEN}: {'k' * 40}\n      {CLAUDE_CMD}", "預設空"),
    ("the-token-is-required", "compose", f"{REAL_TOKEN_LINE}\n  engine-bridge:",
     f"{TOKEN}: ${{{TOKEN}:?必填}}\n  engine-bridge:", "必填形態"),
    ("the-research-root-moved", "compose", "/workspace/my-project", "/data/research",
     "BRIDGE_RESEARCH_ROOT"),
    ("the-claude-command-is-the-real-cli", "compose", MOCK_CMD, f"{CLAUDE_CMD}: claude",
     CLAUDE_CMD),
    ("the-claude-command-is-gone", "compose", f"      {MOCK_CMD}\n", "", CLAUDE_CMD),
    ("the-placeholder-became-a-real-looking-value", "env", PLACEHOLDER, "k" * 40, ".env.example"),
    ("the-token-line-is-duplicated", "env", "JWT_SECRET=<YOUR_JWT_SECRET_MIN_32_CHARS>",
     f"{TOKEN}={PLACEHOLDER}\nJWT_SECRET=<YOUR_JWT_SECRET_MIN_32_CHARS>", ".env.example"),
    ("the-token-line-is-gone", "env", f"# {TOKEN}={PLACEHOLDER}\n", "", ".env.example"),
    ("apt-installs-gh", "docker", None, "RUN apt-get install -y gh\n", "Dockerfile"),
    ("apt-installs-gh-next-to-git", "docker", "git ca-certificates", "git gh ca-certificates",
     "Dockerfile"),
    ("npm-installs-the-claude-cli", "docker", None,
     "RUN npm install -g @anthropic-ai/claude-code\n", "Dockerfile"),
    ("curl-installs-the-claude-cli", "docker", None,
     "RUN curl -fsSL https://claude.ai/install.sh | bash\n", "Dockerfile"),
    ("github-cli-from-its-apt-source", "docker", None,
     "RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg -o /k\n",
     "Dockerfile"),
    ("a-claude-binary-is-copied-in", "docker", None, "COPY claude /usr/local/bin/claude\n",
     "Dockerfile"),
]
BENIGN: list[tuple[str, str, str | None, str]] = [
    ("comments-may-mention-the-clis", "docker", None, "# 不安裝 claude、gh，也不裝 github-cli\n"),
    ("a-comment-inside-a-continued-run", "docker", None,
     "RUN apt-get install -y git \\\n# gh and claude are not installed\n    ca-certificates\n"),
    ("autoclaude-paths-are-not-the-cli", "docker", None,
     "COPY AutoClaude/ /opt/AutoClaude/\nRUN ls /opt/AutoClaude\n"),
    ("the-mock-claude-entry-point-is-not-the-cli", "docker", None,
     "RUN pip install aisdlc-mock-claude\nENV GH_TOKEN_FILE=/x\n"),
    ("the-list-form-is-read-too", "compose", LIST_OLD, LIST_NEW),
]


def patched(doc: str, old: str | None, new: str) -> str:
    base = BASES[doc]
    if old is None:
        return base + new
    assert old in base, f"變體的目標字串不在基底文件裡：{old!r}"
    return base.replace(old, new, 1)


def problems_for(doc: str, old: str | None, new: str) -> list[str]:
    texts = {**BASES, doc: patched(doc, old, new)}
    return deploy_problems(texts["compose"], texts["env"], texts["docker"])


def test_AT_960_2_E_2_the_good_base_documents_have_no_problems() -> None:
    assert deploy_problems(GOOD_COMPOSE, GOOD_ENV, GOOD_DOCKERFILE) == []


@pytest.mark.parametrize(
    ("doc", "old", "new", "expect"),
    [pytest.param(doc, old, new, expect, id=case_id)
     for case_id, doc, old, new, expect in DEFECTS])
def test_AT_960_2_E_2_each_defect_variant_is_reported(
        doc: str, old: str | None, new: str, expect: str) -> None:
    problems = problems_for(doc, old, new)
    assert any(expect in problem for problem in problems), (expect, problems)


def test_AT_960_2_E_2_a_bridge_that_accepts_the_placeholder_is_reported() -> None:
    problems = deploy_problems(GOOD_COMPOSE, GOOD_ENV, GOOD_DOCKERFILE, loader=accepts_everything)
    assert any("逐字拒絕" in problem for problem in problems), problems


@pytest.mark.parametrize(
    ("doc", "old", "new"),
    [pytest.param(doc, old, new, id=case_id) for case_id, doc, old, new in BENIGN])
def test_AT_960_2_E_2_benign_variants_are_not_reported(
        doc: str, old: str | None, new: str) -> None:
    assert problems_for(doc, old, new) == []
