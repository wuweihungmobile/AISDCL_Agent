"""capabilities 與 /health/deep 在 P1 的實值（TCS AT-961-16-1～16-3、16-E-1；PKG-BR-D1）。

十三鍵不變；`scaffold_root`、`scaffold_templates`、`repo_writable` 取實值；`gh_cli.authenticated`
維持 `NOT-EVALUABLE`（探針不起子行程，D-98）。容器模式＝PATH 無 gh、repo 不可寫、未設 scaffold 根。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from app.research import settings as research_settings
from tests import research_git_support as rgs
from tests import test_research_router as rt

make_env = rt.make_env
route_db, real_tree, renv, fake_gh = rgs.route_db, rgs.real_tree, rgs.renv, rgs.fake_gh
THIRTEEN = research_settings.INFO_KEYS + research_settings.CAPABILITY_EXTRA_KEYS
EIGHT = ("mode", "root", "db", "claude_cli", "gh_cli", "git", "web_layer_enabled",
         "scaffold_templates")


def set_cfg(renv: rgs.RouteEnv, **fields: Any) -> None:
    live = renv.env.live
    live.app.state.settings = replace(renv.env.settings, **fields)
    live.app.state.research.cfg = live.app.state.settings


def caps(renv: rgs.RouteEnv) -> dict[str, Any]:
    resp = renv.env.get("/research/capabilities")
    assert resp.status_code == 200
    return resp.json()


def test_AT_961_16_1_five_keys_take_real_values_and_the_key_set_is_unchanged(
        renv: rgs.RouteEnv, tmp_path: Path) -> None:
    body = caps(renv)
    assert tuple(body) == THIRTEEN and len(body) == 13
    assert body["scaffold_root"] == str(renv.scaffold) and body["scaffold_templates"] == [
        "python-fastapi"]
    assert body["repo_writable"] is True
    assert body["gh_cli"] == {"ok": True, "authenticated": "NOT-EVALUABLE"}
    assert body["git"] == {"ok": True, "version": "NOT-EVALUABLE"}
    set_cfg(renv, research_scaffold_root=None)
    unset = caps(renv)
    assert unset["scaffold_root"] is None and unset["scaffold_templates"] == []
    assert tuple(unset) == THIRTEEN
    set_cfg(renv, research_repo_root=tmp_path / "not-a-writable-repo")
    assert caps(renv)["repo_writable"] is False


def test_AT_961_16_2_the_deep_health_research_object_keeps_its_eight_keys(
        renv: rgs.RouteEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    body = renv.env.get("/health/deep").json()["research"]
    assert tuple(body) == EIGHT and body["mode"] in ("local", "mock-only")
    assert body["scaffold_templates"] == ["python-fastapi"]
    assert body["gh_cli"]["authenticated"] == "NOT-EVALUABLE"
    real = research_settings.shutil.which
    monkeypatch.setattr(research_settings.shutil, "which",
                        lambda name, *a, **k: None if name == "claude" else real(name, *a, **k))
    assert renv.env.get("/health/deep").json()["research"]["mode"] == "mock-only"
    monkeypatch.setattr(research_settings.shutil, "which", lambda name, *a, **k: "/bin/x")
    assert renv.env.get("/health/deep").json()["research"]["mode"] == "local"


def test_AT_961_16_3_a_container_like_deployment_reports_honestly_and_refuses_routes(
        renv: rgs.RouteEnv, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rid = rgs.seed_gate0(renv)
    rgs.hide_gh(monkeypatch, tmp_path)
    set_cfg(renv, research_scaffold_root=None, research_repo_root=tmp_path / "ro-repo")
    body = caps(renv)
    assert body["gh_cli"]["ok"] is False and body["repo_writable"] is False
    assert body["scaffold_root"] is None and body["scaffold_templates"] == []
    a = rgs.preview(renv, rid, rgs.body_a(renv))
    b = rgs.preview(renv, rid, rgs.body_b(renv, create_github=True))
    assert a.status_code == 422 and b.status_code == 422
    assert {m["item"] for m in a.json()["details"]["missing"]} == {"repo_writable"}
    assert {m["item"] for m in b.json()["details"]["missing"]} == {"gh", "scaffold_root"}
    assert a.json()["reason"] == b.json()["reason"] == "route_unsupported_in_deployment"


def test_hide_gh_keeps_git_reachable_when_it_shares_a_directory_with_gh(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """夾具契約（CI 0af3a6bc 的教訓）：GitHub ubuntu runner 的 git 與 gh 同住 `/usr/bin`，整個
    目錄丟掉會把 git 一起藏掉（三個 AT 因 `FileNotFoundError: 'git'` 紅）。佈一個「兩者同住」且是
    PATH 唯一目錄的情境再藏 gh：gh 必須消失、git 必須仍可解析且真的能跑。"""
    real_git = shutil.which("git")
    assert real_git is not None, "TOOL-ABSENCE: git"
    shared = tmp_path / "shared"
    shared.mkdir()
    if sys.platform == "win32":
        (shared / "gh.cmd").write_bytes(b"@echo fake\r\n")
        (shared / "git.cmd").write_bytes(f'@"{real_git}" %*\r\n'.encode())
    else:
        (shared / "gh").write_text("#!/bin/sh\necho fake\n", encoding="utf-8")
        (shared / "git").write_text(f'#!/bin/sh\nexec "{real_git}" "$@"\n', encoding="utf-8")
        for name in ("gh", "git"):
            (shared / name).chmod(0o755)
    monkeypatch.setenv("PATH", str(shared))
    assert Path(shutil.which("git") or "").parent == shared, "佈置：git 只能從同住目錄解析"
    assert shutil.which("gh") is not None
    rgs.hide_gh(monkeypatch, tmp_path)
    assert shutil.which("gh") is None
    git_now = shutil.which("git")
    assert git_now is not None and Path(git_now).parent == tmp_path / "hidegh"
    out = subprocess.run([git_now, "--version"], capture_output=True, text=True, check=False,
                         env={**os.environ, "PATH": os.environ["PATH"]})
    assert out.returncode == 0 and out.stdout.startswith("git version"), out.stderr


def test_AT_961_16_E_1_template_scanning_accepts_only_valid_non_empty_directories(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tree = tmp_path / "tpl"
    for name in ("python-fastapi", "node", "Bad Name"):
        (tree / name).mkdir(parents=True)
        (tree / name / "x.tmpl").write_text("x\n", encoding="utf-8")
    (tree / "empty").mkdir()
    assert research_settings.list_template_ids(tree) == ["node", "python-fastapi"]
    (tree / "java").mkdir()
    (tree / "java" / "f.tmpl").write_text("x\n", encoding="utf-8")
    assert research_settings.list_template_ids(tree) == ["java", "node", "python-fastapi"]
    for file in (tree / "node").iterdir():
        file.unlink()
    assert research_settings.list_template_ids(tree) == ["java", "python-fastapi"]
    assert research_settings.list_template_ids(tmp_path / "missing") == []
