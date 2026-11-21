"""OIR 協定參數載入與型別驗證（DES §3.1；REQ-WP-02／06）。

`docs/06_quality/OpenItems_Protocol/params.json` 是唯一真相源（規格變更才改，人寫）；缺鍵或型別
不對一律 `ParamError`（fail loud，不偷補預設——預設值住在檔裡，不住在程式碼裡）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

LEDGER_REL = "docs/06_quality/OpenItems_Event_Ledger.jsonl"
PARAMS_REL = "docs/06_quality/OpenItems_Protocol/params.json"

_INT_KEYS = (
    "max_attempts", "max_deferrals", "human_cap", "retry_backoff_minutes", "start_grace_minutes",
    "run_budget_margin_minutes", "observe_timeout_minutes", "max_runs_per_window",
    "cap_window_minutes", "stagger_minutes", "busy_backoff_minutes", "sched_cache_ttl_seconds",
    "followup_grace_minutes",
)
_LIST_KEYS = ("scan_globs", "vocabulary_definers", "driver_own_prefixes", "source_prefixes")
_STR_KEYS = ("marker_regex", "task_prefix")


class ParamError(ValueError):
    """params.json 讀不到、不是 JSON 或欄位不合。"""


def params_path(root: Path) -> Path:
    return Path(root) / PARAMS_REL


def ledger_path(root: Path) -> Path:
    return Path(root) / LEDGER_REL


def load(root: Path) -> dict:
    path = params_path(root)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ParamError(f"{PARAMS_REL} 讀不到或不是 JSON：{exc}") from exc
    if not isinstance(data, dict):
        raise ParamError(f"{PARAMS_REL} 頂層必須是物件")
    for key in _INT_KEYS:
        value = data.get(key)
        if type(value) is not int or value < 0:
            raise ParamError(f"{PARAMS_REL} 缺 `{key}` 或不是非負整數")
    for key in _LIST_KEYS:
        value = data.get(key)
        if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
            raise ParamError(f"{PARAMS_REL} 缺 `{key}` 或不是非空字串清單")
    extra = data.get("immutable_records", [])
    if not isinstance(extra, list) or not all(isinstance(v, str) and v for v in extra):
        raise ParamError(f"{PARAMS_REL} 的 `immutable_records` 必須是字串清單（可省略）")
    for key in _STR_KEYS:
        if not isinstance(data.get(key), str) or not data[key]:
            raise ParamError(f"{PARAMS_REL} 缺 `{key}` 或不是非空字串")
    try:
        re.compile(data["marker_regex"])
    except re.error as exc:
        raise ParamError(f"{PARAMS_REL} 的 marker_regex 不是合法正規式：{exc}") from exc
    return data
