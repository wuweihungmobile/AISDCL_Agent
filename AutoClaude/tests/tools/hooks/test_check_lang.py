"""tools/hooks/check_lang.py 單元測試 — SD_09 W0 §4「驗證鏡子自身要被驗證」紀律。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
HOOK_SCRIPT = PROJECT_ROOT / "tools" / "hooks" / "check_lang.py"


def _make_transcript(tmp_path: Path, assistant_text: str) -> Path:
    """產一個最小 transcript.jsonl，含一則 assistant 訊息。"""
    transcript = tmp_path / "transcript.jsonl"
    events = [
        {"type": "user", "message": {"content": "你好"}},
        {
            "type": "assistant",
            "message": {
                "content": [{"type": "text", "text": assistant_text}],
            },
        },
    ]
    transcript.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events),
        encoding="utf-8",
    )
    return transcript


def _run(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )


def test_pure_traditional_chinese_passes(tmp_path):
    """純繁中應 exit 0 且無 stderr 警示。"""
    transcript = _make_transcript(tmp_path, "已完成 Phase A 路徑修正，所有連結改至 AISDLC_v0.09 目錄。")
    result = _run({"transcript_path": str(transcript)})
    assert result.returncode == 0, f"stderr={result.stderr}"


def test_korean_triggers_warning(tmp_path):
    """含韓文應 exit 1，stderr 含「韓文」標記。"""
    transcript = _make_transcript(tmp_path, "안녕하세요 — 修復完成。")
    result = _run({"transcript_path": str(transcript)})
    assert result.returncode == 1
    assert "韓文" in result.stderr


def test_simplified_chinese_triggers_warning(tmp_path):
    """含簡體高頻字（这个为）應 exit 1。"""
    transcript = _make_transcript(tmp_path, "这个修复方案为 SD_09 W0 设计。")
    result = _run({"transcript_path": str(transcript)})
    assert result.returncode == 1
    assert "簡體中文" in result.stderr


def test_no_transcript_path_fail_open(tmp_path):
    """payload 缺 transcript_path → fail-open exit 0。"""
    result = _run({})
    assert result.returncode == 0


def test_japanese_hiragana_triggers_warning(tmp_path):
    """含日文 hiragana 應 exit 1。"""
    transcript = _make_transcript(tmp_path, "ありがとう — 修復完成。")
    result = _run({"transcript_path": str(transcript)})
    assert result.returncode == 1
    assert "日文" in result.stderr
