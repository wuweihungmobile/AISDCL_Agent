"""離線刷新 `data/known_model_windows.json`——真的打 Anthropic Models API（DEF-200-275 第四輪）。

WHY 是一支獨立腳本而不是 hook 內查：hook 每次工具呼叫都跑、環境沒有 API key（Claude Code 用
OAuth）、離線也得能跑 ⇒ hook 路徑**永不** import 本檔、永不打網路（`context_window.py` 只讀表）。
表值的來源是 `GET /v1/models` 每個 model 物件的 `max_input_tokens`（＝context window）；只用官方
`anthropic` SDK（`Anthropic()` 零參數：讀 `ANTHROPIC_API_KEY` 或 `ant auth login` 的 profile）。

用法（在 AISDLC_SDD/<LATEST>/ 下）：
    python -m tools.fsm_runtime.refresh_known_model_windows [--path <json>]
rc：0 已刷新並寫檔；2 SDK 未安裝；3 API 呼叫失敗（無憑證／離線）；4 API 回的 model 物件沒有
`max_input_tokens`（SDK 太舊）。非 0 一律**不寫檔**——半套的表比舊表更糟。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from pathlib import Path
from typing import Iterable

if __package__ in (None, ""):  # 直跑檔案時補 sys.path，讓 `tools.fsm_runtime` 可 import
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.fsm_runtime.context_window import KNOWN_MODEL_WINDOWS_PATH, normalize_model_id  # noqa: E402


def _field(model: object, name: str) -> object:
    if isinstance(model, dict):
        return model.get(name)
    return getattr(model, name, None)


def apply_models(table: dict, models: Iterable[object]) -> dict:
    """純函式：把 Models API 回的 model 物件（或 dict）併進表；只收正整數 `max_input_tokens`。"""
    out = {str(k): int(v) for k, v in dict(table).items()}
    for model in models:
        model_id = _field(model, "id")
        window = _field(model, "max_input_tokens")
        if not isinstance(model_id, str) or not model_id:
            continue
        if isinstance(window, bool) or not isinstance(window, int) or window <= 0:
            continue
        out[normalize_model_id(model_id)] = window
    return dict(sorted(out.items()))


def _load_doc(path: Path) -> dict:
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        doc = {}
    if not isinstance(doc, dict):
        doc = {}
    doc.setdefault("schema", 1)
    doc.setdefault("source", "Anthropic Models API GET /v1/models/{id} -> max_input_tokens")
    doc.setdefault("models", {})
    return doc


def main(argv: list[str] | None = None) -> int:
    # 本腳本的 console 輸出刻意全 ASCII：離線工具在 zh-TW cp950 console 下印中文會 UnicodeEncodeError，
    # 而島內「強制 stdio-UTF-8 複本」受根層 test_platform_utils_dedup 的 shrink-only 棘輪管（不得再長一處）。
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--path", default=str(KNOWN_MODEL_WINDOWS_PATH))
    args = parser.parse_args(argv)
    path = Path(args.path)

    try:
        import anthropic  # type: ignore  # noqa: PLC0415
    except ImportError:
        print(
            "ERROR: official SDK not installed -> uv pip install anthropic "
            "(this script only uses the official SDK; no raw HTTP)",
            file=sys.stderr,
        )
        return 2
    try:
        client = anthropic.Anthropic()
        models = list(client.models.list())
    except Exception as exc:  # noqa: BLE001 — 任何失敗一律 fail-loud、不寫檔
        print(
            f"ERROR: Models API call failed: {exc!r}\n"
            "   run `ant auth login` first, or set ANTHROPIC_API_KEY, then retry",
            file=sys.stderr,
        )
        return 3

    doc = _load_doc(path)
    before = dict(doc.get("models") or {})
    merged = apply_models(before, models)
    if merged == {normalize_model_id(k): v for k, v in before.items()} and not any(
        isinstance(_field(m, "max_input_tokens"), int) for m in models
    ):
        print(
            "ERROR: Models API returned no max_input_tokens (SDK too old?) -- nothing written",
            file=sys.stderr,
        )
        return 4
    doc["models"] = merged
    doc["refreshed_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    doc["seeded_from"] = None
    tmp = path.with_name(path.name + f".part.{os.getpid()}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    print(f"OK: refreshed {path}: {len(merged)} models (refreshed_at={doc['refreshed_at']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
