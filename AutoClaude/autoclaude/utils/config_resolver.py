"""ConfigResolver — SD_Improving_06 W5-T5-11 / T5-12 / T5-13。

4 層 hierarchical config merge：
    global (config.yaml) → workflow (PlaybookTask.token_guard / playbook 層級)
        → step (PlaybookTask.token_guard per step) → runtime (CLI/env overrides)

設計原則：
  - merge 規則：右側覆蓋左側；dict 遞迴 merge；list / scalar 整體覆寫
  - Pydantic v2 nested model：TokenGuardConfig 已有 model_validator 保證 invariants
  - 自動 promote flat → nested：將 `compact_threshold_pct: 80` 自動 promote 為
    `token_guard: {compact_threshold_pct: 80}` 並 emit DeprecationWarning
  - RBAC 保護欄位（T5-17）：embedder.api_key / minimax.api_key 等
    不可由 runtime layer override（raise PermissionError）
  - audit hook（T5-16/T5-19）：可注入 callable 紀錄每個 effective 變更至 config_audit_log

對應規格：
  - SD_Improving_06.md §6.5 AC6-1（4 層 ConfigResolver）
  - SD_Improving_06.md §6.5 AC6-2（Pydantic v2 + invariants）
  - SD_Improving_06.md §6.5 AC6-3（OpenAPI 3.1 schema GET /api/config/schema）
  - SD_Improving_06.md §9.2 #11 hybrid（PII filter 應用至 config_audit_log）
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Literal

from pydantic import BaseModel

from .config import AppConfig, TokenGuardConfig

ConfigLayer = Literal["global", "workflow", "step", "runtime"]
_LAYER_ORDER: tuple[ConfigLayer, ...] = ("global", "workflow", "step", "runtime")

# T5-13：flat → nested promotion mapping
# 舊版 flat config 欄位可能位於 AppConfig 頂層；新版要求落入 nested 子模型
_FLAT_TO_NESTED_PROMOTIONS: dict[str, tuple[str, str]] = {
    # flat_key                       (nested_section, nested_key)
    "compact_threshold_pct":         ("token_guard", "compact_threshold_pct"),
    "halt_threshold_pct":            ("token_guard", "halt_threshold_pct"),
    "auto_resume":                   ("token_guard", "auto_resume"),
    "resume_delay_minutes":          ("token_guard", "resume_delay_minutes"),
    "max_auto_resumes":              ("token_guard", "max_auto_resumes"),
}

# T5-17：RBAC 保護欄位（runtime layer 嘗試覆寫 → raise PermissionError）
_PROTECTED_FIELDS: frozenset[str] = frozenset({
    "minimax.api_key",
    "embedder.api_key",
    "storage.db_dsn",
})


@dataclass
class ConfigAuditRecord:
    """T5-16/T5-19：每筆 effective 變更紀錄。

    SD_06 W5-T5-20：寫入 config_audit_log 前必呼叫 apply_pii_filter。
    """
    layer: ConfigLayer
    field_path: str
    old_value: Any = None
    new_value: Any = None
    action: str = "update"  # insert / update / delete / reject
    reason: Optional[str] = None

    def apply_pii_filter(self, pii_filter) -> "ConfigAuditRecord":
        """SD_06 W5-T5-20：將 old_value / new_value 經 PIIFilter 過濾。

        - SECRET 欄位（minimax.api_key 等）→ filter 內部 raise PIIFilterViolation
          中斷寫入（呼叫端應 catch 並改寫 action='reject'）
        - PII / NORMAL 欄位 → 過濾後回新 ConfigAuditRecord
        """
        import json as _json

        def _filter(v: Any, path: str) -> Any:
            if v is None:
                return None
            text = v if isinstance(v, str) else _json.dumps(v, ensure_ascii=False)
            return pii_filter.filter_text(
                field_path=path, text=text,
            )

        full_old = f"config_audit_log.old_value.{self.field_path}"
        full_new = f"config_audit_log.new_value.{self.field_path}"
        return ConfigAuditRecord(
            layer=self.layer,
            field_path=self.field_path,
            old_value=_filter(self.old_value, full_old),
            new_value=_filter(self.new_value, full_new),
            action=self.action,
            reason=self.reason,
        )


class ProtectedFieldError(PermissionError):
    """T5-17：嘗試由 runtime layer 覆寫 RBAC 保護欄位時 raise。"""


def _deep_merge(left: dict, right: dict) -> dict:
    """遞迴 dict merge：右側覆蓋左側；scalar / list 整體覆寫。"""
    out = dict(left)
    for k, v in right.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _flatten_paths(data: dict, prefix: str = "") -> dict[str, Any]:
    """產生 field_path → value mapping（巢狀 dict 用 . 連接 key）。"""
    out: dict[str, Any] = {}
    for k, v in data.items():
        path = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(_flatten_paths(v, path))
        else:
            out[path] = v
    return out


def promote_flat_to_nested(
    raw: dict, *, warn: bool = True,
) -> dict:
    """T5-13：將 flat config keys 自動 promote 至 nested 子模型。

    例：
        {"compact_threshold_pct": 75} → {"token_guard": {"compact_threshold_pct": 75}}

    Warn=True 時對每個 promotion emit DeprecationWarning。
    """
    out = dict(raw)
    for flat_key, (section, nested_key) in _FLAT_TO_NESTED_PROMOTIONS.items():
        if flat_key in out:
            if warn:
                warnings.warn(
                    f"Flat config field '{flat_key}' is deprecated since SD_06 W5; "
                    f"use nested '{section}.{nested_key}' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
            section_dict = out.get(section, {}) or {}
            if not isinstance(section_dict, dict):
                continue
            # nested 已明確指定則不覆寫（nested 優先）
            section_dict.setdefault(nested_key, out.pop(flat_key))
            out[section] = section_dict
    return out


class ConfigResolver:
    """SD_06 W5-T5-11：4 層 hierarchical config 解析器。

    使用範例：
        resolver = ConfigResolver(global_cfg=load_config("config.yaml"))
        resolver.set_workflow_overrides({"token_guard": {"compact_threshold_pct": 75}})
        resolver.set_step_overrides({"token_guard": {"halt_threshold_pct": 95}})
        effective = resolver.effective()
        # effective.token_guard.compact_threshold_pct == 75
        # effective.token_guard.halt_threshold_pct == 95
    """

    def __init__(
        self,
        global_cfg: AppConfig,
        *,
        workflow_overrides: Optional[dict] = None,
        step_overrides: Optional[dict] = None,
        runtime_overrides: Optional[dict] = None,
        audit_observer: Optional[Callable[[ConfigAuditRecord], None]] = None,
    ):
        self._global_cfg = global_cfg
        self._layers: dict[ConfigLayer, dict] = {
            "global": global_cfg.model_dump(),
            "workflow": workflow_overrides or {},
            "step": step_overrides or {},
            "runtime": runtime_overrides or {},
        }
        self._audit_observer = audit_observer

    def set_workflow_overrides(self, overrides: dict) -> None:
        self._layers["workflow"] = promote_flat_to_nested(overrides)

    def set_step_overrides(self, overrides: dict) -> None:
        self._layers["step"] = promote_flat_to_nested(overrides)

    def set_runtime_overrides(self, overrides: dict) -> None:
        """T5-17 enforce：runtime layer 不可覆寫 RBAC 保護欄位。"""
        promoted = promote_flat_to_nested(overrides)
        flat = _flatten_paths(promoted)
        violations = [k for k in flat if k in _PROTECTED_FIELDS]
        if violations:
            raise ProtectedFieldError(
                f"Runtime layer 不可覆寫 RBAC 保護欄位：{violations}"
            )
        self._layers["runtime"] = promoted

    def merged(self) -> dict:
        """4 層 merge 為單一 dict：global → workflow → step → runtime。"""
        out: dict = {}
        for layer in _LAYER_ORDER:
            out = _deep_merge(out, self._layers[layer])
        return out

    def effective(self) -> AppConfig:
        """以 merged dict 重建 AppConfig；Pydantic v2 invariants 自動執行。"""
        return AppConfig.model_validate(self.merged())

    def audit_changes(self) -> list[ConfigAuditRecord]:
        """T5-16/T5-19：產生 per-field audit 紀錄。

        以 global layer 為 baseline，逐層比對 workflow / step / runtime
        對應 field 是否變更，產生 ConfigAuditRecord。
        """
        records: list[ConfigAuditRecord] = []
        baseline = _flatten_paths(self._layers["global"])
        running = dict(baseline)
        for layer in ("workflow", "step", "runtime"):
            overlay = _flatten_paths(self._layers[layer])
            for path, new_value in overlay.items():
                old_value = running.get(path)
                if old_value == new_value:
                    continue
                rec = ConfigAuditRecord(
                    layer=layer,  # type: ignore[arg-type]
                    field_path=path,
                    old_value=old_value,
                    new_value=new_value,
                    action="update" if path in running else "insert",
                )
                records.append(rec)
                if self._audit_observer is not None:
                    try:
                        self._audit_observer(rec)
                    except Exception:  # pragma: no cover
                        pass
                running[path] = new_value
        return records

    # ──────────────────────────────────────────────
    # T5-18：OpenAPI 3.1 schema export
    # ──────────────────────────────────────────────
    @staticmethod
    def openapi_schema() -> dict:
        """產生 OpenAPI 3.1 相容的 AppConfig schema。

        Pydantic v2 model_json_schema 已產生 JSON Schema draft 2020-12
        （OpenAPI 3.1 完全相容）。本方法套 OpenAPI 3.1 wrapper。
        """
        components = {"AppConfig": AppConfig.model_json_schema()}
        return {
            "openapi": "3.1.0",
            "info": {
                "title": "AutoClaude Config Schema",
                "version": "1.0.0",
                "description": "SD_06 W5-T5-18：ConfigResolver effective schema",
            },
            "paths": {
                "/api/config/schema": {
                    "get": {
                        "summary": "Retrieve current AppConfig schema",
                        "responses": {
                            "200": {
                                "description": "OpenAPI 3.1 compatible AppConfig schema",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/AppConfig"},
                                    }
                                },
                            }
                        },
                    }
                }
            },
            "components": {"schemas": components},
        }


__all__ = [
    "ConfigResolver",
    "ConfigAuditRecord",
    "ProtectedFieldError",
    "promote_flat_to_nested",
]
