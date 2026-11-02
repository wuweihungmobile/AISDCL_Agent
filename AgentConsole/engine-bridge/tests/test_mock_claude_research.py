"""mock_claude 研究劇本模式與 FC（TCS AT-960-22-1；AC-R2P-04-11；ADR-003 D10）。

三件事：(1) 未設 `MOCK_CLAUDE_RESEARCH_SCRIPT` 時行為與此前逐位元組相同（黃金輸出）；
(2) 設了就依 prompt 內的 `.prompts/<role>.md` 與 `round=<k>` 把劇本指定的檔案原樣寫進工作區；
(3) 壞劇本、缺步驟、越界路徑一律非 0 rc 並在 stderr 說明（不靜默成功）。FC
（`fixtures/research/fake_claude.py`）共用同一份劇本格式與寫檔函式，另加故障注入，這裡一併
鎖住——orchestrator 的測試依賴它。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app import mock_claude
from tests.fixtures.research import fake_claude

SCRIPTS = Path(__file__).resolve().parent / "fixtures" / "research" / "scripts"
APP_DIR = Path(__file__).resolve().parents[1] / "app"
PROMPT = "請完成 [INIT_DONE] 與 [PONG] 以及 [INIT_DONE]"
#: 改動前（git HEAD）的 `aisdlc-mock-claude -p PROMPT` 單行輸出（不含平台換行）。
GOLDEN_LINE = (
    '{"type": "result", "subtype": "success", "is_error": false, "num_turns": 1, '
    '"result": "mock claude 完成。[INIT_DONE] [PONG]", "session_id": "mock-session", '
    '"total_cost_usd": 0.0, "usage": {"input_tokens": 1200, "cache_read_input_tokens": 0, '
    '"cache_creation_input_tokens": 0, "output_tokens": 40}, '
    '"modelUsage": {"mock-model": {"contextWindow": 200000}}}')


def research_prompt(role: str, round_no: int) -> str:
    return (f"先 Read `.prompts/{role}.md`，完全依其內容執行本步驟。 "
            f"stage=X round={round_no} role={role}。")


def spawn(argv: list[str], env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess[bytes]:
    clean = {k: v for k, v in os.environ.items()
             if not k.startswith(("MOCK_CLAUDE", "FAKE_CLAUDE"))}
    return subprocess.run([sys.executable, "-m", "app.mock_claude", *argv], capture_output=True,
                          env={**clean, "MOCK_CLAUDE_DELAY": "0", **env}, cwd=cwd, check=False)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(os.environ):
        if name.startswith(("MOCK_CLAUDE", "FAKE_CLAUDE")):
            monkeypatch.delenv(name)
    monkeypatch.setenv("MOCK_CLAUDE_DELAY", "0")


# ── (1) 預設行為逐位元組不變 ───────────────────────────────────────────────────────────
def test_AT_960_22_1_default_mode_output_is_byte_identical_to_the_golden(
        tmp_path: Path, clean_env: None) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    done = spawn(["-p", PROMPT], {}, workspace)
    assert done.returncode == 0 and done.stderr == b""
    text = done.stdout.decode("utf-8")
    assert text.rstrip("\r\n") == GOLDEN_LINE and text.endswith("\n")
    assert list(workspace.iterdir()) == []                # 預設模式不寫任何檔案
    version = spawn(["--version"], {}, workspace)
    assert version.stdout.decode("utf-8").strip() == "0.0.0-mock (mock claude)"


def test_AT_960_22_1_default_mode_trace_line_keeps_its_exact_shape(
        tmp_path: Path, clean_env: None) -> None:
    trace = tmp_path / "trace.jsonl"
    spawn(["-p", PROMPT], {"MOCK_CLAUDE_TRACE": str(trace)}, tmp_path)
    entry = json.loads(trace.read_text(encoding="utf-8"))
    assert list(entry) == ["pid", "ts", "prompt_head", "prompt_tail", "keywords", "sdd_env"]
    assert entry["keywords"] == ["[INIT_DONE]", "[PONG]", "[INIT_DONE]"]
    assert entry["sdd_env"] == {"SDD_PROJECT": None, "SDD_STATE_DIR": None,
                                "has_write_token": False}


def test_AT_960_22_1_the_fail_regex_switch_still_works_without_the_script(
        tmp_path: Path, clean_env: None) -> None:
    done = spawn(["-p", PROMPT], {"MOCK_CLAUDE_FAIL_REGEX": "PONG"}, tmp_path)
    assert json.loads(done.stdout)["result"] == "mock claude 完成。"


# ── (2) 劇本模式：依角色與輪次寫出劇本檔 ─────────────────────────────────────────────────
@pytest.mark.parametrize("script_name", ["mock_claude_script_fail3.json",
                                         "mock_claude_script_pass.json"])
def test_AT_960_22_1_every_scripted_step_writes_exactly_its_fixture_bytes(
        script_name: str, tmp_path: Path, clean_env: None, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    script = SCRIPTS / script_name
    doc = json.loads(script.read_text(encoding="utf-8"))
    monkeypatch.setenv("MOCK_CLAUDE_RESEARCH_SCRIPT", str(script))
    monkeypatch.chdir(tmp_path)
    assert len(doc["steps"]) >= 11
    for step in doc["steps"]:
        rc = mock_claude.run(["--permission-mode", "acceptEdits", "-p",
                              research_prompt(step["role"], step["round"])])
        out = capsys.readouterr().out
        assert rc == 0 and out.count("\n") == 1
        payload = json.loads(out)
        assert list(payload) == list(json.loads(GOLDEN_LINE))        # 形狀同現行
        for write in step["writes"]:
            written = (tmp_path / write["path"]).read_bytes()
            assert written == (SCRIPTS / write["from"]).read_bytes(), write["path"]
            assert b"\r" not in written


def test_AT_960_22_1_script_mode_runs_through_a_real_process_and_records_env_keys(
        tmp_path: Path, clean_env: None) -> None:
    trace = tmp_path / "trace.jsonl"
    env = {"MOCK_CLAUDE_RESEARCH_SCRIPT": str(SCRIPTS / "mock_claude_script_pass.json"),
           "MOCK_CLAUDE_TRACE": str(trace), "BRIDGE_SECRET_SENTINEL": "x"}
    done = spawn(["-p", research_prompt("research", 0)], env, tmp_path)
    assert done.returncode == 0, done.stderr
    assert (tmp_path / "00_research" / "evidence_items.json").is_file()
    entry = json.loads(trace.read_text(encoding="utf-8"))
    assert "BRIDGE_SECRET_SENTINEL" in entry["env_keys"]          # 只記鍵名，不記值
    assert "x" not in json.dumps(entry["sdd_env"])


# ── (3) 壞劇本、缺步驟、越界路徑：非 0 rc、stderr 說明、不寫檔 ─────────────────────────────
def write_script(tmp_path: Path, steps: object, schema: object = 1, name: str = "s.json") -> Path:
    path = tmp_path / "script" / name
    path.parent.mkdir(exist_ok=True)
    (path.parent / "a.txt").write_text("A", encoding="utf-8")
    path.write_text(json.dumps({"schema": schema, "steps": steps}), encoding="utf-8")
    return path


BAD_WRITES = [
    {"path": "/etc/passwd", "from": "a.txt"},
    {"path": "C:/Windows/x.txt", "from": "a.txt"},
    {"path": "../escape.txt", "from": "a.txt"},
    {"path": "ok/../../escape.txt", "from": "a.txt"},
    {"path": "ok.txt", "from": "../a.txt"},
    {"path": "ok.txt", "from": "/abs/a.txt"},
    {"path": "ok.txt", "from": "missing.txt"},
    {"path": "", "from": "a.txt"},
    "not-an-object",
]


@pytest.mark.parametrize("bad", BAD_WRITES, ids=[str(i) for i in range(len(BAD_WRITES))])
def test_AT_960_22_1_out_of_bounds_or_broken_writes_fail_loudly_and_write_nothing(
        bad: object, tmp_path: Path, clean_env: None, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    script = write_script(tmp_path, [{"role": "draft", "round": 0, "writes": [bad]}])
    monkeypatch.setenv("MOCK_CLAUDE_RESEARCH_SCRIPT", str(script))
    monkeypatch.chdir(workspace)
    rc = mock_claude.run(["-p", research_prompt("draft", 0)])
    captured = capsys.readouterr()
    assert rc == 2 and captured.out == "" and "mock claude 研究劇本" in captured.err
    assert list(workspace.iterdir()) == [] and not (tmp_path / "escape.txt").exists()


def test_AT_960_22_1_missing_step_missing_file_and_malformed_script_are_all_nonzero(
        tmp_path: Path, clean_env: None, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    steps = [{"role": "draft", "round": 0, "writes": []}]
    good = write_script(tmp_path, steps, name="good.json")
    cases = {
        "no step for (role, round)": (good, "review-qa", 2, "沒有 (role"),
        "wrong round": (good, "draft", 5, "round=5"),
        "script file missing": (tmp_path / "nope.json", "draft", 0, "讀不到劇本檔"),
        "bad schema number": (write_script(tmp_path, steps, 2, "schema2.json"), "draft", 0,
                              "劇本格式錯誤"),
        "steps not a list": (write_script(tmp_path, {"a": 1}, 1, "dict.json"), "draft", 0,
                             "劇本格式錯誤"),
    }
    for label, (script, role, round_no, message) in cases.items():
        monkeypatch.setenv("MOCK_CLAUDE_RESEARCH_SCRIPT", str(script))
        rc = mock_claude.run(["-p", research_prompt(role, round_no)])
        err = capsys.readouterr().err
        assert rc == 2 and message in err, (label, err)
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    monkeypatch.setenv("MOCK_CLAUDE_RESEARCH_SCRIPT", str(broken))
    assert mock_claude.run(["-p", research_prompt("draft", 0)]) == 2
    assert "不是 JSON" in capsys.readouterr().err
    monkeypatch.setenv("MOCK_CLAUDE_RESEARCH_SCRIPT", str(write_script(tmp_path, steps)))
    assert mock_claude.run(["-p", "沒有任何角色參照 round=0"]) == 2
    assert "缺 .prompts/<role>.md" in capsys.readouterr().err


def test_AT_960_22_1_the_product_mock_embeds_no_scoring_or_evidence_constants() -> None:
    text = (APP_DIR / "mock_claude.py").read_text(encoding="utf-8")
    for token in ("W100", "weighted", "weight", "threshold", "ARCHITECTURE", "PRODUCT",
                  "SECURITY", "7990", "8500", "evidence_items", "rubric", "defects"):
        assert token not in text, token


# ── FC：共用劇本格式、另加故障注入 ──────────────────────────────────────────────────────
def fc_script(tmp_path: Path, step: dict[str, object]) -> Path:
    path = tmp_path / "script" / "fc.json"
    path.parent.mkdir(exist_ok=True)
    for name in ("good.txt", "bad.txt"):
        (path.parent / name).write_text(name, encoding="utf-8")
    path.write_text(json.dumps({"schema": 1, "steps": [
        {"role": "review-qa", "round": 2, **step}]}), encoding="utf-8")
    return path


def fc_run(tmp_path: Path, script: Path, monkeypatch: pytest.MonkeyPatch,
           capsys: pytest.CaptureFixture[str]) -> tuple[int, dict[str, object]]:
    monkeypatch.setenv("MOCK_CLAUDE_RESEARCH_SCRIPT", str(script))
    monkeypatch.setenv("FAKE_CLAUDE_STATE", str(tmp_path / "state.json"))
    rc = fake_claude.run(["-p", research_prompt("review-qa", 2)])
    out = capsys.readouterr().out
    return rc, json.loads(out) if out else {}


def test_fc_attempts_override_writes_per_invocation_and_count_through_the_state_file(
        tmp_path: Path, clean_env: None, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    monkeypatch.chdir(ws)
    script = fc_script(tmp_path, {"attempts": [
        {"writes": [{"path": "out.txt", "from": "bad.txt"}]},
        {"writes": [{"path": "out.txt", "from": "bad.txt"}]},
        {"writes": [{"path": "out.txt", "from": "good.txt"}]}]})
    seen = []
    for _ in range(4):                                    # 第 4 次沿用最後一項
        rc, payload = fc_run(tmp_path, script, monkeypatch, capsys)
        seen.append((rc, (ws / "out.txt").read_text(encoding="utf-8"), "attempt=" in str(payload)))
    assert [s[1] for s in seen] == ["bad.txt", "bad.txt", "good.txt", "good.txt"]
    assert all(s[0] == 0 for s in seen)
    assert json.loads((tmp_path / "state.json").read_text(encoding="utf-8")) == {"review-qa:2": 4}


def test_fc_fault_keys_shape_the_result_usage_exit_code_and_delay(
        tmp_path: Path, clean_env: None, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.chdir(tmp_path)
    naps: list[float] = []
    monkeypatch.setattr(fake_claude.time, "sleep", naps.append)
    script = fc_script(tmp_path, {"writes": [], "delay": 1.5, "usage_input_tokens": 190000,
                                  "result": "Claude usage limit reached|1760000000",
                                  "exit_code": 3})
    rc, payload = fc_run(tmp_path, script, monkeypatch, capsys)
    assert rc == 3 and naps == [1.5]
    assert payload["result"] == "Claude usage limit reached|1760000000"
    assert payload["usage"]["input_tokens"] == 190000
    assert payload["modelUsage"] == {"mock-model": {"contextWindow": 200000}}


def test_fc_missing_script_or_step_exits_2_and_says_why(
        tmp_path: Path, clean_env: None, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MOCK_CLAUDE_RESEARCH_SCRIPT", str(tmp_path / "none.json"))
    assert fake_claude.run(["-p", research_prompt("draft", 0)]) == 2
    assert "fake claude" in capsys.readouterr().err
    assert fake_claude.run(["--version"]) == 0


def test_fc_launcher_runs_as_a_single_executable_and_traces_env_keys_and_watch_hits(
        tmp_path: Path, clean_env: None) -> None:
    launcher = fake_claude.make_launcher(tmp_path / "bin")
    ws = tmp_path / "ws"
    ws.mkdir()
    script = fc_script(tmp_path, {"writes": [{"path": "a/b.txt", "from": "good.txt"}]})
    trace = tmp_path / "trace.jsonl"
    env = {**os.environ, "MOCK_CLAUDE_RESEARCH_SCRIPT": str(script),
           "MOCK_CLAUDE_TRACE": str(trace),
           "FAKE_CLAUDE_WATCH": json.dumps(["SENTINEL-SECRET", "not-there"]),
           "SOME_LEAK": "prefix-SENTINEL-SECRET-suffix"}
    argv = [launcher, "--output-format", "json", "-p", research_prompt("review-qa", 2)]
    done = subprocess.run(argv, capture_output=True, env=env, cwd=ws, check=False)
    assert done.returncode == 0, done.stderr
    assert (ws / "a" / "b.txt").read_text(encoding="utf-8") == "good.txt"
    entry = json.loads(trace.read_text(encoding="utf-8"))
    assert entry["role"] == "review-qa" and entry["round"] == 2 and entry["attempt"] == 1
    assert "SOME_LEAK" in entry["env_keys"] and entry["watch_hits"] == ["SENTINEL-SECRET"]
