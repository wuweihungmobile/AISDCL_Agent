"""LLM Backend abstraction for multimodal Spec validation.

ACT-031 (Phase F M3 D-31.6).

Design:
  - Adapters call backend.extract_widget_tree() / compare_widgets_to_ac() etc.
  - Three concrete backends:
      * ClaudeCodeSessionBackend  — default; local parsing, zero LLM calls
      * ClaudeAPIBackend          — Anthropic vision API (opt-in)
      * MinimaxAPIBackend         — drop-in placeholder (OPEN-F.3 reserve)
  - Backend selection via env: SDD_MULTIMODAL_BACKEND ∈ {session, claude-api, minimax}
  - Default `session` (zero external dependency, OPEN-F.3 RESOLVED)

Public:
  ModalityBackend (Protocol)
  WidgetTree, WidgetSignature, ComparisonResult
  get_backend(name=None)  — factory; reads env if name omitted
"""
from __future__ import annotations

import dataclasses
import os
import re
from pathlib import Path
from typing import List, Optional, Protocol


# ─────────────────────────────────────────────
# Data structures (shared across all backends)
# ─────────────────────────────────────────────
@dataclasses.dataclass(frozen=True)
class WidgetSignature:
    kind: str   # button | input | label | link | table | image | form | other
    name: str   # accessible label / id
    role: str = ""  # ARIA-style role hint (optional)


@dataclasses.dataclass
class WidgetTree:
    source: str   # path or URL the tree was derived from
    widgets: List[WidgetSignature]

    def has_widget(self, *, kind: str, name: str) -> bool:
        target = name.strip().lower()
        for w in self.widgets:
            if w.kind == kind and w.name.strip().lower() == target:
                return True
        return False

    def names_of(self, kind: Optional[str] = None) -> List[str]:
        if kind is None:
            return [w.name for w in self.widgets]
        return [w.name for w in self.widgets if w.kind == kind]


@dataclasses.dataclass
class ComparisonResult:
    consistent: bool
    missing: List[str] = dataclasses.field(default_factory=list)
    extra: List[str] = dataclasses.field(default_factory=list)
    confidence: float = 1.0   # 1.0 for deterministic backends; LLM may lower
    backend_name: str = ""


# ─────────────────────────────────────────────
# Protocol — minimum surface every backend must support
# ─────────────────────────────────────────────
class ModalityBackend(Protocol):
    name: str

    def extract_widget_tree(self, artifact_path: Path) -> WidgetTree: ...

    def compare_widgets_to_ac(
        self,
        widgets: WidgetTree,
        ac_text: str,
    ) -> ComparisonResult: ...


# ─────────────────────────────────────────────
# 1. Claude Code Session backend (default, zero-cost)
# ─────────────────────────────────────────────
class ClaudeCodeSessionBackend:
    """Local-only backend — uses regex parsing, no external LLM call.

    Capabilities:
      - HTML / Markdown widget extraction (full)
      - PNG / SVG: only file existence check (no vision); marks confidence=0.5
        with a single placeholder widget so callers can still report a
        coverage gap without hard-failing.
    """
    name = "session"

    # widget tag → kind mapping for HTML extraction
    _HTML_TAG_KIND = {
        "button": "button",
        "input": "input",
        "textarea": "input",
        "select": "input",
        "label": "label",
        "a": "link",
        "table": "table",
        "img": "image",
        "form": "form",
    }

    # --- public API ---
    def extract_widget_tree(self, artifact_path: Path) -> WidgetTree:
        path = Path(artifact_path)
        if not path.exists():
            raise FileNotFoundError(f"artifact missing: {path}")
        suffix = path.suffix.lower()
        if suffix in {".html", ".htm"}:
            return self._extract_html(path)
        if suffix == ".md":
            return self._extract_markdown(path)
        if suffix in {".png", ".jpg", ".jpeg", ".svg", ".gif"}:
            # session backend can't see images → return placeholder
            return WidgetTree(
                source=str(path),
                widgets=[WidgetSignature(kind="image", name=path.stem, role="opaque")],
            )
        # Unknown — return empty tree but no error
        return WidgetTree(source=str(path), widgets=[])

    def compare_widgets_to_ac(
        self,
        widgets: WidgetTree,
        ac_text: str,
    ) -> ComparisonResult:
        keywords = _extract_keywords_from_ac(ac_text)
        missing: List[str] = []
        widget_names_lower = {w.name.strip().lower() for w in widgets.widgets}
        for kw in keywords:
            kw_lower = kw.strip().lower()
            if not kw_lower:
                continue
            if not any(kw_lower in name for name in widget_names_lower):
                missing.append(kw)
        confidence = 1.0
        # Heuristic dampening when artifact is opaque (image stub)
        if any(w.role == "opaque" for w in widgets.widgets):
            confidence = 0.5
        return ComparisonResult(
            consistent=not missing,
            missing=missing,
            confidence=confidence,
            backend_name=self.name,
        )

    # --- internals ---
    def _extract_html(self, path: Path) -> WidgetTree:
        text = path.read_text(encoding="utf-8", errors="replace")
        # Strip HTML comments before extraction — comments may carry text
        # that, if leaked into widget descriptors, falsely satisfies AC keywords
        # (e.g. `<!-- 登入 button intentionally omitted -->` would otherwise
        # make a button-less mockup look like it satisfies «登入»).
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        widgets: List[WidgetSignature] = []

        # Capture <tag ... attrs ...>name</tag> and self-closing <input>
        # We don't need a full HTML parser for our verification needs.
        for tag, kind in self._HTML_TAG_KIND.items():
            # opening tag with attrs
            for m in re.finditer(
                rf"<{tag}\b([^>]*)(?:/>|>(.*?)</{tag}>)",
                text, re.IGNORECASE | re.DOTALL,
            ):
                attrs = m.group(1) or ""
                inner = (m.group(2) or "").strip()
                # Emit one signature per *non-empty* descriptor — name attr,
                # inner text, placeholder/alt/aria-label — so the comparator
                # can match either the programmatic id (e.g. "login") or the
                # rendered label (e.g. "登入").
                role = _extract_attr(attrs, "role")
                seen_for_tag: set[str] = set()
                descriptors = [
                    _extract_attr(attrs, "name"),
                    _extract_attr(attrs, "aria-label"),
                    _extract_attr(attrs, "placeholder"),
                    _extract_attr(attrs, "alt"),
                    _strip_html(inner),
                    _extract_attr(attrs, "id"),
                ]
                for desc in descriptors:
                    desc = (desc or "").strip()
                    if not desc:
                        continue
                    key = desc.lower()
                    if key in seen_for_tag:
                        continue
                    seen_for_tag.add(key)
                    widgets.append(WidgetSignature(kind=kind, name=desc, role=role))
        return WidgetTree(source=str(path), widgets=widgets)

    def _extract_markdown(self, path: Path) -> WidgetTree:
        text = path.read_text(encoding="utf-8", errors="replace")
        widgets: List[WidgetSignature] = []
        # `[Login](#)` → link; `**Email**` → label; bullet lists treated as labels.
        for m in re.finditer(r"\[([^\]]+)\]\([^)]*\)", text):
            widgets.append(WidgetSignature(kind="link", name=m.group(1)))
        for m in re.finditer(r"`?\*\*([^*]+)\*\*`?\s*[:：]", text):
            widgets.append(WidgetSignature(kind="label", name=m.group(1)))
        for m in re.finditer(r"^\s*[-*]\s+(.+?)$", text, re.MULTILINE):
            line = m.group(1).strip()
            if line.lower().startswith("button"):
                widgets.append(WidgetSignature(kind="button", name=line.split(":", 1)[-1].strip()))
            elif line.lower().startswith("input"):
                widgets.append(WidgetSignature(kind="input", name=line.split(":", 1)[-1].strip()))
        return WidgetTree(source=str(path), widgets=widgets)


# ─────────────────────────────────────────────
# 2. Claude API backend (vision-capable, opt-in)
# ─────────────────────────────────────────────
class ClaudeAPIBackend:
    """Vision-capable backend (Anthropic Claude API).

    Status: stub — production wiring requires `anthropic` SDK and an API key.
    Adapters can ship without it; tests cover the abstraction's selection
    plumbing only.
    """
    name = "claude-api"

    def extract_widget_tree(self, artifact_path: Path) -> WidgetTree:
        raise NotImplementedError(
            "ClaudeAPIBackend is a stub — set SDD_CLAUDE_API_KEY and install "
            "anthropic SDK to enable. See cicd/SDD_HUB_SYNC §multimodal."
        )

    def compare_widgets_to_ac(
        self,
        widgets: WidgetTree,
        ac_text: str,
    ) -> ComparisonResult:
        raise NotImplementedError("see extract_widget_tree")


# ─────────────────────────────────────────────
# 3. Minimax backend (drop-in placeholder, OPEN-F.3)
# ─────────────────────────────────────────────
class MinimaxAPIBackend:
    """Drop-in placeholder backend reserved per OPEN-F.3 補述.

    Same Protocol contract as the others, but every method raises
    NotImplementedError — switching to it via env produces a clear error
    rather than silently degrading.
    """
    name = "minimax"

    def extract_widget_tree(self, artifact_path: Path) -> WidgetTree:
        raise NotImplementedError(
            "MinimaxAPIBackend is a reserved drop-in slot (OPEN-F.3). "
            "No SDK wired in M3/M4 — use SDD_MULTIMODAL_BACKEND=session for default."
        )

    def compare_widgets_to_ac(
        self,
        widgets: WidgetTree,
        ac_text: str,
    ) -> ComparisonResult:
        raise NotImplementedError("see extract_widget_tree")


# ─────────────────────────────────────────────
# 4. Mock backend (approach 4 — 高擬真本地 Mock，零外連)
# ─────────────────────────────────────────────
class MockBackend:
    """Deterministic mock backend — 給定固定回傳值測系統邏輯，零網路。

    用於地端把外部服務 Mock 起來（approach 4-1）：以 `set_canned()` 注入預期
    的 widget tree / 比對結果，讓測試只驗系統邏輯而不受外部波動影響。預設回
    傳空樹 + 一致結果。完全離線、確定性，適合單元 / 離線整合測試。
    """
    name = "mock"

    def __init__(self, canned_tree: Optional[WidgetTree] = None,
                 canned_result: Optional[ComparisonResult] = None):
        self._tree = canned_tree
        self._result = canned_result

    def set_canned(self, *, tree: Optional[WidgetTree] = None,
                   result: Optional[ComparisonResult] = None) -> "MockBackend":
        if tree is not None:
            self._tree = tree
        if result is not None:
            self._result = result
        return self

    def extract_widget_tree(self, artifact_path: Path) -> WidgetTree:
        if self._tree is not None:
            return self._tree
        return WidgetTree(source=str(artifact_path), widgets=[])

    def compare_widgets_to_ac(self, widgets: WidgetTree, ac_text: str) -> ComparisonResult:
        if self._result is not None:
            return self._result
        return ComparisonResult(consistent=True, confidence=1.0, backend_name=self.name)


# ─────────────────────────────────────────────
# 5. Local LLM backend (approach 4 — Ollama / vLLM，OpenAI 相容 /v1)
# ─────────────────────────────────────────────
class LocalOpenAIBackend:
    """地端 LLM 後端 — 指向 localhost 的 OpenAI 相容端點（approach 4-2）。

    用地端量化模型（如 Qwen GGUF）做 widget 抽取：Ollama 預設
    http://localhost:11434/v1、vLLM 預設 http://localhost:8000/v1。把應用端點
    指向 localhost，避免連正式環境 / 外部網路造成的成本與誤判。

    設計守則（維持 CI hermetic + 不碰 meta 自演化迴圈）：
      - 預設 OFF：唯有 SDD_MULTIMODAL_BACKEND=local 才啟用；CI 預設 session。
      - 僅 stdlib urllib，無新增 pip 相依。
      - 端點不可達 → 拋清楚 RuntimeError（不靜默退化）。
      - 僅服務 Phase F 多模態 Spec 驗證；未接入 META 自我演化 / 具身接地迴圈，
        故與 R-9.36 / R-9.37 對 meta-loop 的 OPEN 外聯限制無涉。
      - 抽取用 LLM，比對沿用 session 後端的確定性邏輯 ⇒ 結果可重現。
    """
    name = "local"

    def __init__(self, base_url: Optional[str] = None,
                 model: Optional[str] = None, timeout: Optional[float] = None):
        # 一律「明確參數 > env > 預設」，避免 env 覆蓋呼叫端明確傳值（反直覺）。
        self.base_url = (base_url or os.environ.get("SDD_LLM_BASE_URL")
                         or "http://localhost:11434/v1").rstrip("/")
        self.model = model or os.environ.get("SDD_LLM_MODEL") or "qwen2.5:7b-instruct"
        self.timeout = float(
            timeout if timeout is not None else os.environ.get("SDD_LLM_TIMEOUT", 30.0)
        )

    def _chat(self, prompt: str) -> str:
        import json
        import urllib.request
        import urllib.error
        payload = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "stream": False,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError) as e:
            raise RuntimeError(
                f"LocalOpenAIBackend 無法連線地端 LLM {self.base_url}（{e}）。"
                f" 請先 `docker compose --profile llm up -d local-llm` 並 "
                f"`ollama pull {self.model}`，或改用 SDD_MULTIMODAL_BACKEND=session。"
            ) from e
        return body["choices"][0]["message"]["content"]

    def extract_widget_tree(self, artifact_path: Path) -> WidgetTree:
        path = Path(artifact_path)
        if not path.exists():
            raise FileNotFoundError(f"artifact missing: {path}")
        content = path.read_text(encoding="utf-8", errors="replace")
        prompt = (
            "Extract UI widgets from the artifact below as a JSON array of "
            '{"kind","name"} objects. kind ∈ {button,input,label,link,table,'
            "image,form,other}. Return ONLY the JSON array.\n\n" + content[:6000]
        )
        widgets = _parse_widgets_json(self._chat(prompt))
        return WidgetTree(source=str(path), widgets=widgets)

    def compare_widgets_to_ac(self, widgets: WidgetTree, ac_text: str) -> ComparisonResult:
        # 沿用 session 後端的確定性比對，確保 LLM 抽取後結果仍可重現。
        result = ClaudeCodeSessionBackend().compare_widgets_to_ac(widgets, ac_text)
        return dataclasses.replace(result, backend_name=self.name)


# ─────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────
_REGISTRY = {
    "session": ClaudeCodeSessionBackend,
    "claude-api": ClaudeAPIBackend,
    "minimax": MinimaxAPIBackend,
    "mock": MockBackend,
    "local": LocalOpenAIBackend,
}


def get_backend(name: Optional[str] = None) -> ModalityBackend:
    """Return a backend instance.

    If `name` is None, read SDD_MULTIMODAL_BACKEND env (default "session").
    Unknown names raise ValueError listing valid choices.
    """
    chosen = (name or os.environ.get("SDD_MULTIMODAL_BACKEND") or "session").strip()
    if chosen not in _REGISTRY:
        raise ValueError(
            f"unknown backend {chosen!r}; valid choices: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[chosen]()


def list_backends() -> List[str]:
    return sorted(_REGISTRY)


# ─────────────────────────────────────────────
# Helpers shared with other adapters
# ─────────────────────────────────────────────
_STOP_WORDS = {
    "the", "a", "an", "to", "of", "for", "in", "on", "at", "by", "with",
    "and", "or", "but", "is", "are", "be", "as", "from", "into", "用戶",
    "輸入", "點擊", "按下", "顯示", "完成", "後", "讓", "可以", "並",
    "after", "click", "user", "users", "system", "show", "displayed",
}

# Latin identifier with at least 3 chars (Email, password, login, ...)
_ASCII_TOKEN_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_-]{2,30}\b")
# Spec ID prefixes (AC / FRD / US / NFR / TC / F / EPIC ...) — these aren't
# UI widgets even when they appear inside an AC sentence.
_SPEC_ID_PREFIXES = (
    "AC-", "AT-", "ADR-", "API-", "C4-", "EPIC-", "F-", "FRD-",
    "INV-", "NFR-", "PBS-", "PR-", "RTM-", "SCG-", "SLV-", "SRD-",
    "TC-", "TCS-", "TD-", "US-",
)


def _extract_keywords_from_ac(ac_text: str) -> List[str]:
    """Pull *explicit* UI-relevant labels from an AC sentence.

    Returned tokens drive the session backend's `compare_widgets_to_ac`. To
    keep noise low we only keep:
      1. Quoted strings (「X」 / 『X』 / "X" / 'X')      — UI labels
      2. ASCII identifiers ≥ 3 chars (Email, password) — likely field names
    We deliberately skip:
      - Backtick code spans — these usually name DB tables/columns or files,
        validated by db_schema_adapter, not UI.
      - Spec IDs (AC-010-1, US-100, NFR-XXX) — never UI widgets.
      - Bare Chinese phrases in flowing prose (action verbs).
    """
    if not ac_text:
        return []
    out: List[str] = []
    seen: set[str] = set()

    def _add(token: str) -> None:
        token = token.strip()
        if len(token) < 2:
            return
        # Strip out spec IDs like AC-010-1, NFR-PERF-001, US-100, F-XXX...
        upper = token.upper()
        if any(upper.startswith(p) for p in _SPEC_ID_PREFIXES):
            return
        key = token.lower()
        if key in _STOP_WORDS or key in seen:
            return
        seen.add(key)
        out.append(token)

    # 1. quoted strings (Chinese 「」 / 『』 + ASCII " ')
    for m in re.finditer(r"[「『\"']([^」』\"']{1,15})[」』\"']", ac_text):
        _add(m.group(1))
    # 2. plain ASCII identifiers (≥ 3 chars to skip "AC", "is", ...)
    for m in _ASCII_TOKEN_RE.finditer(ac_text):
        _add(m.group(0))
    return out


def _extract_attr(attrs: str, key: str) -> str:
    m = re.search(rf'{re.escape(key)}\s*=\s*"([^"]*)"', attrs, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(rf"{re.escape(key)}\s*=\s*'([^']*)'", attrs, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _parse_widgets_json(raw: str) -> List[WidgetSignature]:
    """Lenient parse of an LLM JSON reply into widget signatures.

    Tolerates code-fence wrapping and surrounding prose by extracting the first
    JSON array. Malformed output degrades to an empty list (caller reports the
    coverage gap rather than crashing).
    """
    import json
    text = (raw or "").strip()
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if m:
        text = m.group(0)
    try:
        data = json.loads(text)
    except Exception:
        return []
    out: List[WidgetSignature] = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get("name"):
                out.append(WidgetSignature(
                    kind=str(item.get("kind", "other")),
                    name=str(item["name"]),
                ))
    return out


# Re-export helpers so adapters can import from one place.
__all__ = [
    "ModalityBackend",
    "WidgetTree",
    "WidgetSignature",
    "ComparisonResult",
    "ClaudeCodeSessionBackend",
    "ClaudeAPIBackend",
    "MinimaxAPIBackend",
    "MockBackend",
    "LocalOpenAIBackend",
    "get_backend",
    "list_backends",
]
