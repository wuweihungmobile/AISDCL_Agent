"""FilePreferenceStore — IPreferenceStore File 後端（F-C1 / ADR-AGT-003 L3）。

storage.mode == 'yaml_only' 路由（factory.build_preference_store）。
落地：`{checkpoint_dir}/preferences.jsonl`（append-only + load 時 last-wins；
與 FailureKnowledgeBase JSONL 同哲學，寫入失敗 warning 不中斷主流程）。

JSONL 行格式：{"scope": "...", "key": "...", "value": "...", "ts": "<ISO8601 UTC>"}
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger("autoclaude.infra.adapters.file_preference_store")

_MAX_LINES_BEFORE_COMPACT = 1000  # append 行數超過時重寫去重（防無限增長）


class FilePreferenceStore:
    """File 後端：JSONL append + 記憶體 last-wins 快取。"""

    def __init__(self, path: str):
        self._path = Path(path)
        self._cache: dict[tuple[str, str], str] = {}  # (scope, key) -> value
        self._line_count = 0
        self._load()

    # ── IPreferenceStore Protocol ────────────────────────────
    def get(self, key: str, scope: str = "global") -> str | None:
        return self._cache.get((scope, key))

    def set(self, key: str, value: str, scope: str = "global") -> None:
        self._cache[(scope, key)] = value
        self._append({"scope": scope, "key": key, "value": value,
                      "ts": datetime.now(UTC).isoformat()})

    def list(self, scope: str | None = None) -> dict[str, str]:
        if scope is not None:
            return {k: v for (s, k), v in self._cache.items() if s == scope}
        # 合併視圖：global 先鋪底，playbook:* 覆寫同名鍵
        merged = {k: v for (s, k), v in self._cache.items() if s == "global"}
        for (s, k), v in self._cache.items():
            if s != "global":
                merged[k] = v
        return merged

    # ── 內部 ─────────────────────────────────────────────────
    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            with self._path.open(encoding="utf-8") as f:
                for raw in f:
                    raw = raw.strip()
                    if not raw:
                        continue
                    row = json.loads(raw)
                    self._cache[(row["scope"], row["key"])] = row["value"]
                    self._line_count += 1
        except (OSError, ValueError, KeyError) as exc:
            logger.warning("偏好載入失敗（以空庫啟動）: %s", exc)

    def _append(self, row: dict) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            if self._line_count >= _MAX_LINES_BEFORE_COMPACT:
                self._rewrite()
            else:
                with self._path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                self._line_count += 1
        except OSError as exc:
            logger.warning("偏好寫入失敗（warning，繼續主流程）: %s", exc)

    def _rewrite(self) -> None:
        ts = datetime.now(UTC).isoformat()
        with self._path.open("w", encoding="utf-8") as f:
            for (scope, key), value in self._cache.items():
                f.write(json.dumps(
                    {"scope": scope, "key": key, "value": value, "ts": ts},
                    ensure_ascii=False,
                ) + "\n")
        self._line_count = len(self._cache)


__all__ = ["FilePreferenceStore"]
