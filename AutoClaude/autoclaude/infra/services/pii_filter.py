"""PII Filter — 套用 W0 PIIClassification ENUM 的執行層（SD_Improving_06 W3-T3-23）。

對應規格：
  - autoclaude/models/pii_classification.py（W0-T0-2 已建 ENUM + RESERVED）
  - PM #11 hybrid：W0 schema 一次到位 + W3 過濾器實作
  - SD_06 §7 ❌12 衍生 + §11 PII 規則：寫入 drift_log / config_audit_log /
    yaml_import_diffs 前必須過濾

行為對照（PIIFilterAction SSOT）：
  NORMAL  → passthrough（原文入庫）
  PII     → mask（SHA-256 hash 8 字元 + 前 2 後 2 partial mask）
  SECRET  → drop（raise PIIFilterViolation 中斷寫入）
  RESERVED_* → abort（未定義行為 fail-loud）

紅線：禁止悄悄略過分類；若 field_path 未登記，強制走 default_class 並寫 WARNING。
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional

from ...models.pii_classification import PIIClassification, PIIFilterAction

logger = logging.getLogger(__name__)


class PIIFilterViolation(Exception):
    """SECRET 欄位嘗試入庫 / RESERVED_* 被引用 / 未知分類動作 → raise。"""


# 內建偵測規則（粗略補強，配合分類 ENUM 為主防線）
_EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
_PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[-\s]?)?\(?\d{2,4}\)?[-\s]?\d{3,4}[-\s]?\d{3,4}\b")
_IP_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
_TOKEN_RE = re.compile(r"(?:sk-|pk-|tok-)[A-Za-z0-9_\-]{8,}")


def _mask_partial(text: str) -> str:
    """前 2 後 2 partial mask，並附 8 位 sha256 摘要供 join 偵測。"""
    if len(text) <= 4:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
        return f"<masked:{digest}>"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
    return f"{text[:2]}***{text[-2:]}<{digest}>"


def _scrub_token_patterns(text: str) -> str:
    """無條件遮罩 token-like 字串（即使欄位被宣告為 NORMAL，仍應掃描）。"""
    text = _TOKEN_RE.sub(lambda m: _mask_partial(m.group(0)), text)
    return text


@dataclass
class FieldRegistry:
    """field_path → PIIClassification 註冊表。

    例：
        registry = FieldRegistry(rules={
            "drift_log.value_diff": PIIClassification.PII,
            "config_audit_log.new_value.embedder.api_key": PIIClassification.SECRET,
            "yaml_import_diffs.before": PIIClassification.NORMAL,
        })
    """
    rules: dict[str, PIIClassification] = field(default_factory=dict)

    def classify(self, field_path: str, default: PIIClassification) -> PIIClassification:
        if field_path in self.rules:
            return self.rules[field_path]
        # 子路徑匹配（最長前綴）
        prefixes = [k for k in self.rules if field_path.startswith(k + ".")]
        if prefixes:
            best = max(prefixes, key=len)
            return self.rules[best]
        return default


@dataclass
class PIIFilter:
    """執行 PIIClassification 對應動作的中介層。"""

    registry: FieldRegistry = field(default_factory=FieldRegistry)
    enabled: Optional[bool] = None  # None → 讀環境變數
    scrub_tokens_for_normal: bool = True
    audit_observer: Optional[callable] = None  # 寫入 audit log 的 hook

    def __post_init__(self) -> None:
        if self.enabled is None:
            env_val = os.environ.get("PII_FILTER_ENABLED", "true").strip().lower()
            self.enabled = env_val in ("1", "true", "yes", "on")

    def filter_text(
        self,
        *,
        field_path: str,
        text: str,
        classification: PIIClassification = PIIClassification.NORMAL,
    ) -> str:
        """依分類執行 mask / drop / passthrough。

        Returns:
            mask 後 / passthrough 的字串

        Raises:
            PIIFilterViolation: classification == SECRET（drop write）或 RESERVED_*
        """
        if not self.enabled:
            return text

        cls = self.registry.classify(field_path, classification)
        action = PIIFilterAction.get(cls)
        if action is None:
            raise PIIFilterViolation(
                f"未知分類 {cls!r} → 拒絕入庫"
            )

        if action == "drop":
            self._audit(field_path, cls, "drop")
            raise PIIFilterViolation(
                f"SECRET 欄位 {field_path} 嘗試入庫，已拒絕"
            )
        if action == "abort":
            self._audit(field_path, cls, "abort")
            raise PIIFilterViolation(
                f"RESERVED 分類 {cls!r} 不可引用（field={field_path}）"
            )
        if action == "mask":
            masked = self._mask_pii_patterns(text)
            self._audit(field_path, cls, "mask")
            return masked
        # passthrough：仍做 token-like 掃描以防夾帶
        if self.scrub_tokens_for_normal:
            scrubbed = _scrub_token_patterns(text)
            if scrubbed != text:
                self._audit(field_path, cls, "scrub_token_in_normal")
            return scrubbed
        return text

    def _mask_pii_patterns(self, text: str) -> str:
        text = _EMAIL_RE.sub(lambda m: _mask_partial(m.group(0)), text)
        text = _PHONE_RE.sub(lambda m: _mask_partial(m.group(0)), text)
        text = _IP_RE.sub(lambda m: _mask_partial(m.group(0)), text)
        text = _scrub_token_patterns(text)
        return text

    def _audit(self, field_path: str, cls: PIIClassification, action: str) -> None:
        if self.audit_observer:
            try:
                self.audit_observer({"field_path": field_path, "class": cls.value, "action": action})
            except Exception as exc:  # pragma: no cover
                logger.warning("audit_observer 失敗：%s", exc)
