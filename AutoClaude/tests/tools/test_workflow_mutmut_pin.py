"""tests/tools/test_workflow_mutmut_pin.py — DEF-200-356 mutmut CI 版本鎖回歸鎖。

WHY（Rule 9 測意圖非僅行為）：
`.github/workflows/*.yml` 內以裸 `pip install mutmut` 安裝、未鎖版；`AutoClaude/pyproject.toml`
的 `mutation` extra 已鎖 `mutmut==2.4.3` 並註明 mutmut 3.x 的 CLI 重寫拿掉了
`--paths-to-mutate` / `--tests-dir`（與 `tools/run_mutmut_in_docker.sh` 一致）。
2026-09-21 排程 run 35579774973（headSha ad88dbd7，job「Mutation Test - TokenGuardPlugin
(active pilot)」28 秒 success）log 逐字：
    Downloading mutmut-3.8.0-py3-none-any.whl
    ...
    FileNotFoundError: Could not figure out where the code to mutate is
被 `|| true` 吞掉、job 仍回 success；08-31 排程 run 同型 —— CI 的 mutation testing
至少自 08-31 起是假綠：改 token_guard 源碼即便真的沒被任何 mutant 殺掉，job 依然全綠。

本測試鎖：
  1. 每一個 workflow 內含 `pip install` 且含 `mutmut` 的非註解行，都必須含
     `mutmut==<SSOT 版本>`（SSOT＝`AutoClaude/pyproject.toml` 的
     `[project.optional-dependencies].mutation`，不手抄字面 2.4.3）。
  2. 命中數 >= 4 —— 若掃描形態日後改壞（例如 workflow 改寫成不含這兩個關鍵字的
     安裝方式）導致 0 命中，本測試仍必須是紅，不能因為「掃不到東西」而悄悄綠掉。
  3. `AutoClaude/tools/run_mutmut_in_docker.sh` 自身的鎖版與 SSOT 一致（該檔已鎖版，
     見其 `pip install --quiet ... "mutmut==2.4.3"` 行）。
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

_MUTMUT_PIN_RE = re.compile(r"mutmut==([0-9]+(?:\.[0-9]+)*)")


def _ssot_version() -> str:
    """SSOT：`AutoClaude/pyproject.toml` 的 `[project.optional-dependencies].mutation`。

    不手抄 2.4.3 常數——直接從 toml 抽出，SSOT 改版本時本測試的期望值同步改。
    """
    pyproject = _REPO_ROOT / "AutoClaude" / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    mutation_deps = data["project"]["optional-dependencies"]["mutation"]
    for dep in mutation_deps:
        m = _MUTMUT_PIN_RE.search(dep)
        if m:
            return m.group(1)
    raise AssertionError(
        "AutoClaude/pyproject.toml 的 `mutation` extra 找不到 `mutmut==<版本>` "
        f"字串（可能已改版或改名，需回頭改本測試的抽取邏輯）：{mutation_deps!r}"
    )


def _uncommented(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]


def test_ssot_version_is_parseable() -> None:
    """紀律 #4「驗證鏡子自身要被驗證」：SSOT 抽取本身要先能拿到合法版本字串。"""
    version = _ssot_version()
    assert re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", version), (
        f"抽出的 SSOT 版本格式不像合法版號：{version!r}"
    )


def test_every_workflow_pip_install_mutmut_line_is_pinned_to_ssot() -> None:
    """DEF-200-356 主斷言：所有 workflow 的 `pip install ... mutmut ...` 行皆鎖版。"""
    ssot = _ssot_version()
    workflows_dir = _REPO_ROOT / ".github" / "workflows"
    hits: list[str] = []
    unpinned: list[str] = []
    for wf in sorted(workflows_dir.glob("*.yml")):
        text = wf.read_text(encoding="utf-8")
        for lineno, ln in enumerate(text.splitlines(), start=1):
            if ln.lstrip().startswith("#"):
                continue
            if "pip install" not in ln or "mutmut" not in ln:
                continue
            coord = f"{wf.relative_to(_REPO_ROOT)}:{lineno}"
            hits.append(coord)
            if f"mutmut=={ssot}" not in ln:
                unpinned.append(f"{coord} -> {ln.strip()!r}")

    assert not unpinned, (
        "以下 workflow 行安裝 mutmut 卻未鎖版對齊 SSOT (mutmut=="
        f"{ssot})，DEF-200-356 復發：\n" + "\n".join(unpinned)
    )
    assert len(hits) >= 4, (
        "命中數 < 4 —— 掃描形態可能已失效（0 命中假綠會被誤判為『全部鎖好』），"
        f"現查座標：{hits}"
    )


def test_run_mutmut_in_docker_sh_is_pinned_to_ssot() -> None:
    """`tools/run_mutmut_in_docker.sh` 的隔離樹安裝行同樣要對齊 SSOT，不得各鎖各的版本。"""
    ssot = _ssot_version()
    script = _REPO_ROOT / "AutoClaude" / "tools" / "run_mutmut_in_docker.sh"
    assert script.is_file(), script
    pin_lines = [
        ln for ln in _uncommented(script.read_text(encoding="utf-8"))
        if "pip install" in ln and "mutmut==" in ln
    ]
    assert pin_lines, (
        "run_mutmut_in_docker.sh 找不到 `pip install ... mutmut==<版本>` 鎖版行"
        "——若該檔已改成不鎖版，需回頭改寫本測試（只保留 workflow 斷言），"
        "不可直接刪掉本測試"
    )
    for ln in pin_lines:
        assert f"mutmut=={ssot}" in ln, (
            f"run_mutmut_in_docker.sh 鎖版與 SSOT (mutmut=={ssot}) 不一致：{ln.strip()!r}"
        )
