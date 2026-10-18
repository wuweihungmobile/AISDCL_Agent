"""sdd_env.py 測試（TCS-SddEnv-20261018 §2；每個 AT 一個測試函式，tmp_path 隔離）。"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import sdd_env  # isort: skip
from scripts import sdd_version  # isort: skip

ENV_KEYS = [
    "SDD_ACTIVE_VERSION",
    "SDD_PROJECT",
    "SDD_STATE_DIR",
    "SDD_ENABLE_RULE_FIRE_TELEMETRY",
    "SDD_ENABLE_RULE_CATCH_TELEMETRY",
]


def _disk_scan(monkeypatch) -> None:
    monkeypatch.setattr(sdd_env.sdd_version, "tracked_version_dirs", lambda _root: None)


def _fake_root(base: Path, name: str = "fake_root", versions=("0.30",)) -> Path:
    root = base / name
    for v in versions:
        (root / "AISDLC_SDD" / f"AISDLC_SDD_v{v}").mkdir(parents=True)
    return root


def _tree(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)) for p in root.rglob("*"))


def test_AT_001_1_1_default_root_and_json_shell(capsys):
    rc1 = sdd_env.main(["--sub", "monorepo", "--slug", "demo-feature"])
    out1 = capsys.readouterr().out
    rc2 = sdd_env.main(["--sub", "monorepo", "--slug", "demo-feature", "--shell", "json"])
    out2 = capsys.readouterr().out
    assert rc1 == 0 and rc2 == 0
    assert out1 == out2
    data = json.loads(out1)
    assert list(data) == ENV_KEYS
    assert all(isinstance(v, str) for v in data.values())
    assert data["SDD_PROJECT"] == "monorepo-demo-feature"
    assert data["SDD_ENABLE_RULE_FIRE_TELEMETRY"] == "0"
    assert data["SDD_ENABLE_RULE_CATCH_TELEMETRY"] == "0"
    root = str(Path(sdd_env.__file__).resolve().parents[2])
    assert data["SDD_STATE_DIR"] == os.path.join(root, "build", "reports", "fsm")
    assert os.path.isabs(data["SDD_STATE_DIR"])
    latest = sdd_version.latest_version_name(Path(root) / "AISDLC_SDD")
    assert data["SDD_ACTIVE_VERSION"] == latest.removeprefix("AISDLC_SDD_v")
    assert re.fullmatch(r"\d+\.\d+", data["SDD_ACTIVE_VERSION"])


@pytest.mark.parametrize("sub", ["autoclaude", "agentconsole", "monorepo", "sdd"])
def test_AT_001_1_2_state_dir_table_for_each_sub(sub, tmp_path, monkeypatch, capsys):
    _disk_scan(monkeypatch)
    root = _fake_root(tmp_path, versions=("0.9", "0.10"))
    before = _tree(root)
    rc = sdd_env.main(
        ["--sub", sub, "--slug", "my-feature", "--root", str(root), "--shell", "json"]
    )
    data = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert data["SDD_ACTIVE_VERSION"] == "0.10"
    assert data["SDD_PROJECT"] == f"{sub}-my-feature"
    expected = {
        "autoclaude": os.path.join(str(root), "AutoClaude", "build", "reports", "fsm"),
        "agentconsole": os.path.join(str(root), "AgentConsole", "build", "reports", "fsm"),
        "monorepo": os.path.join(str(root), "build", "reports", "fsm"),
        "sdd": os.path.join(
            str(root), "AISDLC_SDD", "AISDLC_SDD_v0.10", "build", "reports", "sdd-dogfood"
        ),
    }[sub]
    assert data["SDD_STATE_DIR"] == expected
    assert os.path.isabs(data["SDD_STATE_DIR"])
    assert _tree(root) == before


def test_AT_001_1_2_relative_and_non_ascii_root(tmp_path, monkeypatch, capsys):
    _disk_scan(monkeypatch)
    _fake_root(tmp_path, versions=("0.9", "0.10"))
    monkeypatch.chdir(tmp_path)
    values = []
    for rel in ("fake_root", "fake_root" + os.sep):
        rc = sdd_env.main(
            ["--sub", "autoclaude", "--slug", "my-feature", "--root", rel, "--shell", "json"]
        )
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert os.path.isabs(data["SDD_STATE_DIR"])
        assert data["SDD_STATE_DIR"] == os.path.join(
            os.path.abspath(rel), "AutoClaude", "build", "reports", "fsm"
        )
        values.append(data["SDD_STATE_DIR"])
    assert values[0] == values[1]

    cjk = _fake_root(tmp_path, name="根目錄", versions=("0.10",))
    rc = sdd_env.main(
        ["--sub", "autoclaude", "--slug", "my-feature", "--root", str(cjk), "--shell", "json"]
    )
    raw = capsys.readouterr().out
    assert rc == 0
    assert "根目錄" in json.loads(raw)["SDD_STATE_DIR"]
    assert "根目錄" in raw
    assert "\\u" not in raw


def _quoted_root(tmp_path: Path) -> Path:
    return _fake_root(tmp_path, name="o'brien")


def test_AT_001_2_1_powershell_lines_and_quote_escaping(tmp_path, monkeypatch, capsys):
    _disk_scan(monkeypatch)
    root = _quoted_root(tmp_path)
    rc = sdd_env.main(
        ["--sub", "autoclaude", "--slug", "webhook", "--root", str(root), "--shell", "powershell"]
    )
    lines = [ln for ln in capsys.readouterr().out.split("\n") if ln]
    assert rc == 0 and len(lines) == 5
    for ln, key in zip(lines, ENV_KEYS):
        assert ln.startswith(f"$env:{key} = ")
    vals = [ln.split(" = ", 1)[1] for ln in lines]
    for idx, want in ((0, "0.30"), (1, "autoclaude-webhook"), (3, "0"), (4, "0")):
        assert vals[idx] == f"'{want}'"
    assert vals[2].startswith("'") and vals[2].endswith("'")
    state = vals[2][1:-1].replace("''", "'")
    assert state == os.path.join(
        os.path.abspath(str(root)), "AutoClaude", "build", "reports", "fsm"
    )
    assert "''" in vals[2]


def test_AT_001_2_2_bash_lines_and_quote_escaping(tmp_path, monkeypatch, capsys):
    _disk_scan(monkeypatch)
    root = _quoted_root(tmp_path)
    rc = sdd_env.main(
        ["--sub", "agentconsole", "--slug", "fsm-trail", "--root", str(root), "--shell", "bash"]
    )
    lines = [ln for ln in capsys.readouterr().out.split("\n") if ln]
    assert rc == 0 and len(lines) == 5
    for ln, key in zip(lines, ENV_KEYS):
        assert ln.startswith(f"export {key}=")
    vals = [ln.split("=", 1)[1] for ln in lines]
    for idx, want in ((0, "0.30"), (1, "agentconsole-fsm-trail"), (3, "0"), (4, "0")):
        assert vals[idx] == f"'{want}'"
    assert vals[2].startswith("'") and vals[2].endswith("'")
    state = vals[2][1:-1].replace("'\\''", "'")
    assert state == os.path.join(
        os.path.abspath(str(root)), "AgentConsole", "build", "reports", "fsm"
    )
    assert "'\\''" in vals[2]


@pytest.mark.parametrize("shell", ["bash", "powershell", "json"])
def test_AT_001_2_2_raw_stdout_bytes_carry_no_cr(shell):
    """SCG-4 F-03（NFR-001-3）：輸出形態由 --shell 決定、不由平台決定。capsys 看不到文字層
    把 LF 翻成 CRLF 的那一步，所以取子行程的原始位元組：任何平台都不得出現 CR。"""
    proc = subprocess.run(
        [sys.executable, str(Path(sdd_env.__file__).resolve()),
         "--sub", "monorepo", "--slug", "f03", "--shell", shell],
        capture_output=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert b"\r" not in proc.stdout
    assert proc.stdout.endswith(b"\n")


@pytest.mark.parametrize(
    "slug", ["", "-a", "a-", "a--b", "A", "a_b", "a b", "a.b", "中文", "A" * 31]
)
def test_AT_001_3_1_bad_slugs_are_rejected_with_rc_2(slug, capsys):
    rc = sdd_env.main(["--sub", "monorepo", "--slug=" + slug])
    cap = capsys.readouterr()
    assert rc == 2
    assert cap.out == ""
    assert "格式" in cap.err


def test_AT_001_3_1_overlong_slug_is_rejected_with_rc_2(capsys):
    rc = sdd_env.main(["--sub", "monorepo", "--slug=" + "a" * 31])
    cap = capsys.readouterr()
    assert rc == 2
    assert cap.out == ""
    assert "30" in cap.err


def test_AT_001_3_2_reserved_words_and_length_boundaries(tmp_path, monkeypatch, capsys):
    _disk_scan(monkeypatch)
    root = _fake_root(tmp_path)
    for slug in ("AISDLC_SDD", "aisdlc_sdd", "Aisdlc_Sdd"):
        rc = sdd_env.main(["--sub", "monorepo", "--slug=" + slug])
        cap = capsys.readouterr()
        assert rc == 2 and cap.out == "" and "保留字" in cap.err
    for slug in ("a" * 30, "a", "a-b-c-1"):
        rc = sdd_env.main(
            ["--sub", "monorepo", "--slug=" + slug, "--root", str(root), "--shell", "json"]
        )
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["SDD_PROJECT"] == "monorepo-" + slug


def test_AT_001_4_1_check_reports_an_existing_state_file(tmp_path, monkeypatch, capsys):
    _disk_scan(monkeypatch)
    root = _fake_root(tmp_path)
    state_dir = root / "AutoClaude" / "build" / "reports" / "fsm"
    state_dir.mkdir(parents=True)
    state_file = state_dir / "FSM-STATE-autoclaude-webhook.yaml"
    state_file.write_text("x: 1\n", encoding="utf-8")
    before = _tree(root)
    rc = sdd_env.main(
        ["--sub", "autoclaude", "--slug", "webhook", "--root", str(root), "--check"]
    )
    out = capsys.readouterr().out
    lines = [ln for ln in out.split("\n") if ln]
    assert rc == 0 and len(lines) == 1
    assert lines[0].startswith("OK ") and str(state_file) in lines[0]
    assert "SDD_PROJECT" not in out
    assert _tree(root) == before
    assert state_file.read_text(encoding="utf-8") == "x: 1\n"


def test_AT_001_4_2_check_reports_a_missing_state_file_without_creating_anything(
    tmp_path, monkeypatch, capsys
):
    _disk_scan(monkeypatch)
    root1 = _fake_root(tmp_path, name="root1")
    (root1 / "AgentConsole" / "build" / "reports" / "fsm").mkdir(parents=True)
    root2 = _fake_root(tmp_path, name="root2")
    for root in (root1, root2):
        before = _tree(root)
        rc = sdd_env.main(
            ["--sub", "agentconsole", "--slug", "fsm-trail", "--root", str(root), "--check"]
        )
        cap = capsys.readouterr()
        expected = os.path.join(
            str(root), "AgentConsole", "build", "reports", "fsm",
            "FSM-STATE-agentconsole-fsm-trail.yaml",
        )
        assert rc == 5 and cap.out == ""
        assert "state_not_found" in cap.err and expected in cap.err
        assert _tree(root) == before
    assert not (root2 / "AgentConsole").exists()
    assert not (root2 / "build").exists()


def test_AT_001_5_1_failure_boundaries_and_zero_side_effects(tmp_path, monkeypatch, capsys):
    _disk_scan(monkeypatch)
    # 情境一：版本不可解
    empty = tmp_path / "empty_root"
    (empty / "AISDLC_SDD").mkdir(parents=True)
    rc = sdd_env.main(["--sub", "monorepo", "--slug", "demo", "--root", str(empty)])
    cap = capsys.readouterr()
    assert rc == 1 and cap.out == "" and "AISDLC_SDD_v" in cap.err
    # 情境二：root 不是目錄
    a_file = tmp_path / "plain.txt"
    a_file.write_text("x", encoding="utf-8")
    for bad in (tmp_path / "missing", a_file):
        rc = sdd_env.main(["--sub", "monorepo", "--slug", "demo", "--root", str(bad)])
        cap = capsys.readouterr()
        assert rc == 2 and cap.out == "" and "root" in cap.err
    # 情境三：用法錯誤
    for argv in (
        ["--sub", "monorepo"],
        ["--sub", "bogus", "--slug", "demo"],
        ["--sub", "monorepo", "--slug", "demo", "--shell", "zsh"],
    ):
        rc = sdd_env.main(argv)
        cap = capsys.readouterr()
        assert rc == 2 and cap.out == ""
    # 情境四：成功呼叫零副作用
    root = _fake_root(tmp_path, name="ok_root")
    env_before = dict(os.environ)
    tree_before = _tree(root)
    calls = []
    monkeypatch.setattr(sdd_env, "force_utf8_stdio", lambda: calls.append(1))
    rc = sdd_env.main(
        ["--sub", "autoclaude", "--slug", "demo", "--root", str(root), "--shell", "bash"]
    )
    capsys.readouterr()
    assert rc == 0
    assert calls == [1]
    assert dict(os.environ) == env_before
    assert _tree(root) == tree_before
    # 情境五：--help
    rc = sdd_env.main(["--help"])
    out = capsys.readouterr().out
    assert rc == 0 and "--sub" in out and "--slug" in out
