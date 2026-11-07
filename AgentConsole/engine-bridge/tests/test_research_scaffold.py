"""軌道 B 的範本展開（TCS AT-961-6-1、6-2、6-3、6-9）：確定性、無網路、無子行程、無 LLM。"""
from __future__ import annotations

import hashlib
import re
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from app.research import scaffold
from app.research import settings as research_settings

VARS = {"project_name": "demo-app", "slug": "demo", "repo_name": "demo-app", "owner": "octocat"}
REQUIRED = {"README.md", ".gitignore", "docker-compose.yml", ".env.example", "pyproject.toml",
            "app/main.py", "tests/test_smoke.py", ".github/workflows/ci.yml"}


def digest_tree(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


# ── AT-961-6-1 ─────────────────────────────────────────────────────────────────────────────
def test_AT_961_6_1_two_expansions_are_byte_identical_offline_and_subprocess_free(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sockets, spawns = [], []

    def no_socket(*a: object, **k: object) -> None:
        sockets.append(a)
        raise AssertionError("展開過程不得連網")

    monkeypatch.setattr(socket, "socket", no_socket)
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: spawns.append(a))
    first = scaffold.expand("python-fastapi", VARS, tmp_path / "one")
    second = scaffold.expand("python-fastapi", VARS, tmp_path / "two")
    assert first == second and REQUIRED <= set(first)
    assert digest_tree(tmp_path / "one") == digest_tree(tmp_path / "two")
    assert sockets == [] and spawns == []
    for rel in first:
        data = (tmp_path / "one" / rel).read_bytes()
        assert not rel.endswith(".tmpl") and b"{{" not in data and b"}}" not in data, rel
        assert b"\r" not in data, f"{rel} 必須是 LF 行尾"
    ignore = (tmp_path / "one" / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "00_research/raw/" in ignore and "build/reports/" in ignore and ".env" in ignore


def test_AT_961_6_1_the_optional_files_follow_their_flags(tmp_path: Path) -> None:
    files = scaffold.expand("python-fastapi", VARS, tmp_path / "x", ci=False, docker_compose=False)
    assert ".github/workflows/ci.yml" not in files and "docker-compose.yml" not in files
    assert "app/main.py" in files


# ── AT-961-6-2 ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("bad", ["a b", "a.b", "a/b", "a\\b", "a{b", "a}b", "a$b", "a;b",
                                 "a\x00b", "ａｂ", "", "../x"])
def test_AT_961_6_2_an_illegal_variable_value_is_refused_and_nothing_is_written(
        tmp_path: Path, bad: str) -> None:
    dest = tmp_path / "out"
    with pytest.raises(scaffold.ScaffoldError) as caught:
        scaffold.expand("python-fastapi", {**VARS, "project_name": bad}, dest)
    assert caught.value.rule == "invalid_variable"
    assert not dest.exists() or not list(dest.rglob("*"))


def test_AT_961_6_2_the_full_legal_character_set_is_accepted(tmp_path: Path) -> None:
    name = "Aa09_-" * 5
    files = scaffold.expand("python-fastapi", {**VARS, "project_name": name}, tmp_path / "ok")
    assert "app/main.py" in files
    assert name in (tmp_path / "ok" / "app" / "main.py").read_text(encoding="utf-8")


def test_AT_961_6_2_an_output_path_that_escapes_the_new_root_is_refused_with_no_residue(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ok = scaffold.PlannedFile("fine.txt", b"x")
    monkeypatch.setattr(scaffold, "plan_files", lambda *a, **k: [ok, scaffold.PlannedFile(
        "../escape.txt", b"y")])
    dest = tmp_path / "root"
    with pytest.raises(scaffold.ScaffoldError) as caught:
        scaffold.expand("python-fastapi", VARS, dest)
    assert caught.value.rule == "path_escape"
    assert not (tmp_path / "escape.txt").exists() and not dest.exists()


def test_AT_961_6_2_an_unknown_template_id_is_refused_without_normalisation(
        tmp_path: Path) -> None:
    for bad in ("node", "java", "../python-fastapi", "PYTHON-FASTAPI", ""):
        with pytest.raises(scaffold.ScaffoldError) as caught:
            scaffold.expand(bad, VARS, tmp_path / "x")
        assert caught.value.rule == "unknown_template", bad


def test_AT_961_6_2_a_template_file_without_the_tmpl_suffix_is_refused(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tree = tmp_path / "tpl"
    (tree / "t").mkdir(parents=True)
    (tree / "t" / "main.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(research_settings, "TEMPLATES_DIR", tree)
    with pytest.raises(scaffold.ScaffoldError) as caught:
        scaffold.expand("t", VARS, tmp_path / "dest")
    assert caught.value.rule == "untemplated_file"


# ── AT-961-6-3 ─────────────────────────────────────────────────────────────────────────────
SECRET_SHAPES = [re.compile(p) for p in (
    r"ghp_[A-Za-z0-9_]{8,}", r"github_pat_[A-Za-z0-9_]{8,}", r"AKIA[0-9A-Z]{8,}",
    r"sk-[A-Za-z0-9]{8,}", r"[0-9a-f]{32,}", r"BEGIN [A-Z ]*PRIVATE KEY")]


def secret_hits(root: Path) -> list[str]:
    hits = []
    for p in sorted(root.rglob("*")):
        if p.is_file():
            text = p.read_text(encoding="utf-8")
            hits += [f"{p.name}:{s.pattern}" for s in SECRET_SHAPES if s.search(text)]
    return hits


def test_AT_961_6_3_env_example_holds_only_placeholders_and_the_scanner_has_teeth(
        tmp_path: Path) -> None:
    scaffold.expand("python-fastapi", VARS, tmp_path / "x")
    root = tmp_path / "x"
    assert len(list(root.rglob("*"))) > 0 and secret_hits(root) == []
    pairs = [line.split("=", 1) for line in (root / ".env.example").read_text(
        encoding="utf-8").splitlines() if "=" in line and not line.startswith("#")]
    assert pairs and all(re.fullmatch(r"(<YOUR_[A-Z0-9_]+>)?", v) for _k, v in pairs)
    (root / "leak.txt").write_text("token ghp_FAKE_R2P1_TOKEN_000000000000000000\n",
                                   encoding="utf-8")
    assert secret_hits(root), "負控：樣本放入假 token 時掃描器必須回報命中"


# ── AT-961-6-9 ─────────────────────────────────────────────────────────────────────────────
def test_AT_961_6_9_the_expanded_project_runs_its_own_pytest_offline(tmp_path: Path) -> None:
    dest = tmp_path / "proj"
    scaffold.expand("python-fastapi", VARS, dest)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=str(dest),
        capture_output=True, text=True, encoding="utf-8", check=False,
        env={k: v for k, v in __import__("os").environ.items() if k != "PYTHONPATH"})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    match = re.search(r"(\d+) passed", proc.stdout)
    assert match and int(match.group(1)) >= 1 and "skipped" not in proc.stdout
    assert "failed" not in proc.stdout
    assert not (dest / ".pytest_cache").exists()


# ── 預測與複製（AT-961-6-4／6-5 的單元面）────────────────────────────────────────────────────────
def test_the_gitignore_predicate_mirrors_the_template_patterns() -> None:
    assert scaffold.is_ignored("00_research/raw/x.html") and scaffold.is_ignored(".env")
    assert scaffold.is_ignored("a/b/.env") and scaffold.is_ignored("build/reports/fsm/s.yaml")
    assert scaffold.is_ignored("x/__pycache__/m.pyc") and scaffold.is_ignored("m.pyc")
    assert not scaffold.is_ignored(".env.example") and not scaffold.is_ignored("00_research/a.md")
    assert not scaffold.is_ignored("app/raw/ok.py")
    assert not scaffold.is_ignored("sub/build/reports/x.txt"), "含斜線的樣式只相對根"
    assert scaffold.is_ignored("my-project/demo/00_research/raw/p.html"), "**/ 形態任何深度"


def test_copy_workspace_copies_every_numbered_dir_and_verifies(tmp_path: Path) -> None:
    src, dst = tmp_path / "ws", tmp_path / "dst"
    for rel in ("00_research/raw/x.html", "00_research/a.md", "01_specs/p.md",
                "02_governance/g.json", "03_execution/t.md", "build/reports/fsm/s.yaml"):
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        (src / rel).write_text(f"data {rel}\n", encoding="utf-8")
    copied = scaffold.copy_workspace(src, dst)
    assert {c.rel for c in copied} == {"00_research/raw/x.html", "00_research/a.md",
                                       "01_specs/p.md", "02_governance/g.json",
                                       "03_execution/t.md"}
    assert not (dst / "build").exists(), "只複製四個編號目錄"
    for c in copied:
        assert (dst / c.rel).read_bytes() == (src / c.rel).read_bytes()
