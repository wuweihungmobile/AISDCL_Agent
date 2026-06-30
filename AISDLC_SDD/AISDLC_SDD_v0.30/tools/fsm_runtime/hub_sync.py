"""Hub Sync Client — pull/push/dry-run/diff/promote rules with the Cross-Project Learning Hub.

ACT-030 (Phase F M2 D-30.5).

Spec:
  knowledge/hub-registry.yaml         — endpoint allow-list + sync_policy
  knowledge/hub/trust-ladder.md       — promotion flow + 3-way merge
  docs/06_quality/HUB-GOVERNANCE-SPEC.md — governance rules (G-30.1~G-30.8)

Behaviour:
  - pull():     fetch rules from a registered endpoint into local cache; if
                cache fresh (<24h per sync_policy), no network call.
  - push():     scan + anonymize local rules, dry-run by default; only writes
                to endpoint when SDD_HUB_PUSH_CONFIRMED=<reason> env var set.
  - dry_run():  show what push() would do without touching anything.
  - diff():     compare local vs cached-hub vs (optional) live-hub artifact.
  - promote():  upgrade a local rule from `trust_level: external` to
                `verified` (helper that fills `reviewed_by` / `reviewed_at`).

Endpoint URL formats supported:
  file://<absolute-path>     — local directory (testing & local hub)
  git+https://github.com/... — git-based registry (production); cloned into
                               cache dir on first pull, fetched thereafter.

This implementation focuses on the file:// path (testable without network).
git+https paths shell out to `git clone` / `git fetch`; the operation is
idempotent and respects sync_policy.timeout_seconds.

Public API:
  HubSyncClient(registry_path=None) — defaults to knowledge/hub-registry.yaml
  HubSyncClient.pull(endpoint_id=None, *, force=False) -> PullResult
  HubSyncClient.push(artifacts: List[Path], endpoint_id=None) -> PushResult
  HubSyncClient.dry_run(artifacts) -> PushResult (writes nothing, ever)
  HubSyncClient.diff(rule_id, endpoint_id=None) -> DiffResult
  HubSyncClient.promote(rule_path, *, reviewer, notes=None) -> PromoteResult

CLI: python -m tools.fsm_runtime.hub_sync {pull|push|dry-run|diff|promote} ...
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as _dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML required: pip install pyyaml") from exc

from .anonymizer import anonymize, load_rules as load_anon_config, AnonymizerConfig
from .pii_scanner import load_l2_rules, scan, write_quarantine, ScanResult
from .state_loader import REPO_ROOT


DEFAULT_REGISTRY_PATH = REPO_ROOT / "knowledge" / "hub-registry.yaml"

# DEF-CLDREV-030: hard memory ceiling for reading EXTERNAL / cached hub content
# before yaml.safe_load. safe_load already rejects `!!python/object` RCE, but
# PyYAML has no document-size / alias-expansion limit — a hostile (or
# misconfigured) hub could ship an oversized or deeply-nested YAML and blow up
# memory during parse. SLV rule yaml is KB-sized, so 1 MiB is ~1000x headroom.
# Overridable per-deployment via registry `sync_policy.pull.max_file_bytes`.
# NOTE: applies ONLY to untrusted external/cached reads (pulled hub rules,
# diff against cached hub, promote of a possibly-cached path). The PR-gated
# local registry and the self-written, by-design-accumulating audit/cache-meta
# ledgers are trusted and deliberately left uncapped.
MAX_HUB_FILE_BYTES = 1024 * 1024  # 1 MiB


class HubConfigError(RuntimeError):
    """Raised when registry / endpoint config is invalid or rejected."""


class HubContentTooLarge(HubConfigError):
    """Raised when an external/cached file exceeds the read size cap (DEF-CLDREV-030)."""


class HubPushBlocked(RuntimeError):
    """Raised when a push attempt fails policy gates (PII / opt-in)."""


@dataclasses.dataclass
class EndpointConfig:
    id: str
    url: str
    protocol: str
    branch: str = "main"
    gpg_fingerprint: Optional[str] = None
    description: str = ""


@dataclasses.dataclass
class PullResult:
    endpoint_id: str
    cache_path: Path
    cache_was_fresh: bool
    pulled_files: List[str]   # relative paths
    error: Optional[str] = None


@dataclasses.dataclass
class PushItem:
    artifact_path: Path
    scan_clean: bool
    quarantine_path: Optional[Path]
    anonymized_text: Optional[str]
    substitutions: int
    would_push: bool          # False if scan dirty or env not confirmed


@dataclasses.dataclass
class PushResult:
    endpoint_id: Optional[str]
    items: List[PushItem]
    confirmed: bool           # SDD_HUB_PUSH_CONFIRMED present?
    audit_log_path: Optional[Path] = None

    @property
    def all_clean(self) -> bool:
        return all(it.scan_clean for it in self.items)


@dataclasses.dataclass
class DiffResult:
    rule_id: str
    local_path: Optional[Path]
    cached_hub_path: Optional[Path]
    differs: bool
    diff_text: str = ""


@dataclasses.dataclass
class PromoteResult:
    rule_path: Path
    from_trust: str
    to_trust: str
    reviewer: str


class HubSyncClient:
    def __init__(
        self,
        registry_path: Optional[Path] = None,
        *,
        anon_config: Optional[AnonymizerConfig] = None,
    ):
        self.registry_path = Path(registry_path) if registry_path else DEFAULT_REGISTRY_PATH
        if not self.registry_path.exists():
            raise HubConfigError(f"hub registry not found: {self.registry_path}")
        # Trusted PR-gated local config (tiny) — intentionally uncapped (DEF-CLDREV-030).
        self.registry: Dict = yaml.safe_load(self.registry_path.read_text(encoding="utf-8")) or {}

        # DEF-CLDREV-030: external/cached read size ceiling (constant default,
        # overridable via registry sync_policy.pull.max_file_bytes).
        try:
            self._max_file_bytes = int(
                self.registry.get("sync_policy", {}).get("pull", {}).get(
                    "max_file_bytes", MAX_HUB_FILE_BYTES
                )
            )
        except (TypeError, ValueError):
            self._max_file_bytes = MAX_HUB_FILE_BYTES
        if self._max_file_bytes <= 0:
            self._max_file_bytes = MAX_HUB_FILE_BYTES

        # Hard-coded deny_unlisted — cannot be relaxed via YAML.
        # Override only via SDD_HUB_ALLOWLIST_OVERRIDE env (audit-logged).
        self._deny_unlisted = True

        self.endpoints: Dict[str, EndpointConfig] = {}
        for ep in self.registry.get("allowed_endpoints", []) or []:
            ep_id = str(ep.get("id", "")).strip()
            url = str(ep.get("url", "")).strip()
            if not ep_id or not url:
                continue
            self.endpoints[ep_id] = EndpointConfig(
                id=ep_id,
                url=url,
                protocol=str(ep.get("protocol", "git+https")),
                branch=str(ep.get("branch", "main")),
                gpg_fingerprint=ep.get("gpg_fingerprint"),
                description=str(ep.get("description", "")),
            )

        self.anon_config = anon_config or load_anon_config()

        # Cache / audit / quarantine paths from registry.
        self.cache_root = REPO_ROOT / self.registry.get("pull_cache", {}).get(
            "path", "build/reports/hub/pull-cache"
        )
        self.cache_meta_path = REPO_ROOT / self.registry.get("pull_cache", {}).get(
            "metadata", "build/reports/hub/pull-cache/META.yaml"
        )
        self.quarantine_dir = REPO_ROOT / self.registry.get(
            "quarantine_dir", "build/reports/hub"
        )
        self.audit_log_path = REPO_ROOT / self.registry.get(
            "push_audit_log", "build/reports/hub/PUSH-AUDIT.yaml"
        )

    # ─────────── helpers ───────────
    def _read_text_bounded(self, path: Path) -> str:
        """Read text from an untrusted external/cached file under the size cap.

        DEF-CLDREV-030: bound memory before reading hub-sourced content into
        memory (and before yaml.safe_load), guarding against an oversized /
        deeply-nested document from a hostile or misconfigured hub. Raises
        HubContentTooLarge when the file exceeds self._max_file_bytes.
        """
        size = path.stat().st_size
        if size > self._max_file_bytes:
            raise HubContentTooLarge(
                f"external file exceeds max read size "
                f"({size} > {self._max_file_bytes} bytes): {path}"
            )
        return path.read_text(encoding="utf-8")

    def _resolve_endpoint(self, endpoint_id: Optional[str]) -> EndpointConfig:
        # SDD_HUB_ALLOWLIST_OVERRIDE bypass (one-shot audited override).
        override = os.environ.get("SDD_HUB_ALLOWLIST_OVERRIDE", "").strip()
        if override and endpoint_id and endpoint_id not in self.endpoints:
            self._record_audit({
                "event": "allowlist_override",
                "reason": override,
                "endpoint_id": endpoint_id,
            })
            # Construct minimal config; URL inferred from endpoint_id (best-effort)
            # or fail if it's not a URL-looking string.
            if "://" in endpoint_id:
                return EndpointConfig(id=endpoint_id, url=endpoint_id, protocol="override")
            raise HubConfigError(
                f"override endpoint must be a URL when not in registry: {endpoint_id!r}"
            )

        if not self.endpoints:
            raise HubConfigError(
                "hub-registry has no allowed_endpoints; populate it before pull/push"
            )
        if endpoint_id is None:
            if len(self.endpoints) == 1:
                return next(iter(self.endpoints.values()))
            raise HubConfigError(
                f"multiple endpoints configured ({list(self.endpoints)}); "
                "pass --endpoint to disambiguate"
            )
        if endpoint_id not in self.endpoints:
            raise HubConfigError(
                f"endpoint {endpoint_id!r} not in registry allow-list (deny_unlisted=true)"
            )
        return self.endpoints[endpoint_id]

    def _endpoint_cache_dir(self, ep: EndpointConfig) -> Path:
        return self.cache_root / ep.id

    def _read_cache_meta(self) -> Dict:
        if not self.cache_meta_path.exists():
            return {}
        return yaml.safe_load(self.cache_meta_path.read_text(encoding="utf-8")) or {}

    def _write_cache_meta(self, meta: Dict) -> None:
        self.cache_meta_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_meta_path.write_text(
            yaml.safe_dump(meta, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    def _is_cache_fresh(self, ep: EndpointConfig, *, ttl_hours: int = 24) -> bool:
        meta = self._read_cache_meta().get(ep.id, {})
        ts = meta.get("last_pulled_at")
        if not ts:
            return False
        try:
            last = _dt.datetime.fromisoformat(ts)
            if last.tzinfo is None:
                last = last.replace(tzinfo=_dt.timezone.utc)
        except (TypeError, ValueError):
            return False
        delta = _dt.datetime.now(_dt.timezone.utc) - last
        return delta.total_seconds() < ttl_hours * 3600

    def _record_audit(self, event: Dict) -> Path:
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        existing: Dict = {}
        if self.audit_log_path.exists():
            # Self-written ledger that accumulates push events by design — must
            # stay uncapped (a size cap here would break legitimate growth).
            existing = yaml.safe_load(self.audit_log_path.read_text(encoding="utf-8")) or {}
        events = existing.setdefault("events", [])
        event_with_ts = dict(event)
        event_with_ts.setdefault(
            "timestamp",
            _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        )
        events.append(event_with_ts)
        self.audit_log_path.write_text(
            yaml.safe_dump(existing, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return self.audit_log_path

    # ─────────── pull ───────────
    def pull(
        self,
        endpoint_id: Optional[str] = None,
        *,
        force: bool = False,
    ) -> PullResult:
        ep = self._resolve_endpoint(endpoint_id)
        cache_dir = self._endpoint_cache_dir(ep)
        cache_dir.mkdir(parents=True, exist_ok=True)

        ttl = int(self.registry.get("sync_policy", {}).get("pull", {}).get("cache_ttl_hours", 24))
        if not force and self._is_cache_fresh(ep, ttl_hours=ttl):
            existing = self._list_rules(cache_dir)
            return PullResult(
                endpoint_id=ep.id,
                cache_path=cache_dir,
                cache_was_fresh=True,
                pulled_files=existing,
            )

        try:
            pulled = self._fetch_endpoint(ep, cache_dir)
        except Exception as exc:  # noqa: BLE001 — non-blocking failure
            return PullResult(
                endpoint_id=ep.id,
                cache_path=cache_dir,
                cache_was_fresh=False,
                pulled_files=[],
                error=f"{type(exc).__name__}: {exc}",
            )

        # QA Round-2 P1: enforce G-30.4 — every cached rule MUST carry
        # `trust_level: external` regardless of what the upstream hub wrote.
        # This is the runtime gate that prevents a misconfigured (or hostile)
        # hub from shipping `trust_level: verified` and skipping the human
        # review ladder. Behaviour is non-fatal: stamping errors are logged
        # to the audit ledger but do not abort the pull.
        stamped = self._stamp_external_trust_level(cache_dir)

        meta = self._read_cache_meta()
        meta[ep.id] = {
            "last_pulled_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "url": ep.url,
            "branch": ep.branch,
            "file_count": len(pulled),
            "trust_level_stamped": stamped,
        }
        self._write_cache_meta(meta)
        return PullResult(
            endpoint_id=ep.id,
            cache_path=cache_dir,
            cache_was_fresh=False,
            pulled_files=pulled,
        )

    def _stamp_external_trust_level(self, cache_dir: Path) -> int:
        """Force-overwrite `trust_level: external` on every YAML rule in cache.

        Returns the number of files whose trust_level was rewritten (verified
        or proposed → external). Files already at `external` or without a
        `trust_level` key are left untouched but still count if they had a
        non-external value beforehand. Non-YAML files (e.g. FPL markdown) are
        skipped — the trust ladder applies to SLV rule yaml only.
        """
        rewritten = 0
        for p in cache_dir.rglob("*.yaml"):
            if not p.is_file():
                continue
            rel = p.relative_to(cache_dir)
            # SLV rules live under rules/ subtree per REGISTRY-SPEC §參.
            if not str(rel).startswith("rules" + os.sep) and not str(rel).startswith("rules/"):
                continue
            try:
                # DEF-CLDREV-030: bounded read of untrusted pulled hub yaml.
                # Oversize → HubContentTooLarge, caught below → fail-soft skip
                # + audit (honours pull failure_mode=non_blocking). A skipped
                # file is never stamped external and (being uncapped-promotable
                # no longer) cannot be promoted into the trust ladder either,
                # since promote() reads via the same bounded helper.
                doc = yaml.safe_load(self._read_text_bounded(p))
            except Exception as exc:  # noqa: BLE001
                self._record_audit({
                    "kind": "hub_pull_stamp_error",
                    "file": str(rel),
                    "error": f"{type(exc).__name__}: {exc}",
                })
                continue
            if not isinstance(doc, dict):
                continue
            current = doc.get("trust_level")
            if current == "external":
                continue
            doc["trust_level"] = "external"
            doc.setdefault("hub_origin", {})
            doc["hub_origin"]["original_trust_level"] = current
            doc["hub_origin"]["stamped_at"] = _dt.datetime.now(
                _dt.timezone.utc
            ).isoformat(timespec="seconds")
            try:
                p.write_text(
                    yaml.safe_dump(doc, sort_keys=False, allow_unicode=True),
                    encoding="utf-8",
                )
                rewritten += 1
            except Exception as exc:  # noqa: BLE001
                self._record_audit({
                    "kind": "hub_pull_stamp_error",
                    "file": str(rel),
                    "error": f"{type(exc).__name__}: {exc}",
                })
        return rewritten

    def _fetch_endpoint(self, ep: EndpointConfig, cache_dir: Path) -> List[str]:
        """Resolve URL scheme and copy/clone into cache_dir.

        file://     — direct rsync-like copy of `rules/` and `failure-patterns/`.
        git+https   — clone or pull the repo into cache_dir/.git_clone, then
                      mirror selected subtrees into cache_dir.
        """
        if ep.url.startswith("file://"):
            # urlparse on Windows mishandles file://C:\... — strip prefix manually.
            raw = ep.url[len("file://"):]
            # Some authors write "file:///C:/foo" or "file://C:/foo"; both should
            # resolve to the actual filesystem path.
            if raw.startswith("/") and len(raw) >= 3 and raw[2] == ":":
                raw = raw[1:]   # "/C:/foo" → "C:/foo"
            src = Path(raw)
            return self._mirror_local(src, cache_dir)
        if ep.url.startswith("git+https://") or ep.url.startswith("git+ssh://") or ep.url.startswith("https://"):
            return self._mirror_git(ep, cache_dir)
        raise HubConfigError(f"unsupported endpoint URL scheme: {ep.url}")

    def _mirror_local(self, src: Path, cache_dir: Path) -> List[str]:
        if not src.exists():
            raise HubConfigError(f"file:// source does not exist: {src}")
        files: List[str] = []
        # Mirror rules/ and failure-patterns/ subtrees only (per HUB-GOVERNANCE).
        for sub in ("rules", "failure-patterns"):
            src_sub = src / sub
            if not src_sub.exists():
                continue
            dst_sub = cache_dir / sub
            if dst_sub.exists():
                shutil.rmtree(dst_sub)
            shutil.copytree(src_sub, dst_sub)
            for p in dst_sub.rglob("*"):
                if p.is_file():
                    files.append(str(p.relative_to(cache_dir)))
        return files

    def _mirror_git(self, ep: EndpointConfig, cache_dir: Path) -> List[str]:
        url = ep.url[len("git+"):] if ep.url.startswith("git+") else ep.url
        clone_dir = cache_dir / ".git_clone"
        timeout = int(
            self.registry.get("sync_policy", {}).get("pull", {}).get("timeout_seconds", 30)
        )
        if (clone_dir / ".git").exists():
            cmd = ["git", "-C", str(clone_dir), "fetch", "origin", ep.branch, "--depth", "1"]
            subprocess.run(cmd, check=True, timeout=timeout, capture_output=True)
            cmd = ["git", "-C", str(clone_dir), "reset", "--hard", f"origin/{ep.branch}"]
            subprocess.run(cmd, check=True, timeout=timeout, capture_output=True)
        else:
            cmd = ["git", "clone", "--depth", "1", "--branch", ep.branch, url, str(clone_dir)]
            subprocess.run(cmd, check=True, timeout=timeout, capture_output=True)
        # Mirror after clone.
        return self._mirror_local(clone_dir, cache_dir)

    @staticmethod
    def _list_rules(cache_dir: Path) -> List[str]:
        files: List[str] = []
        for p in cache_dir.rglob("*"):
            if p.is_file() and not p.name.startswith("."):
                rel = p.relative_to(cache_dir)
                if str(rel).startswith(".git_clone"):
                    continue
                files.append(str(rel))
        return sorted(files)

    # ─────────── push (dry-run / real) ───────────
    def dry_run(self, artifacts: Iterable[Path]) -> PushResult:
        return self._prepare_push(artifacts, force_dry=True)

    def push(
        self,
        artifacts: Iterable[Path],
        endpoint_id: Optional[str] = None,
    ) -> PushResult:
        confirmed_reason = os.environ.get("SDD_HUB_PUSH_CONFIRMED", "").strip()
        confirmed = bool(confirmed_reason)
        result = self._prepare_push(artifacts, force_dry=not confirmed)
        result.endpoint_id = endpoint_id
        result.confirmed = confirmed

        # Audit-log every push attempt (even dry-run when confirmed=False).
        result.audit_log_path = self._record_audit({
            "event": "push_attempt",
            "endpoint_id": endpoint_id,
            "confirmed": confirmed,
            "confirmed_reason": confirmed_reason or None,
            "items": [
                {
                    "artifact": str(it.artifact_path),
                    "scan_clean": it.scan_clean,
                    "quarantine_path": str(it.quarantine_path) if it.quarantine_path else None,
                    "would_push": it.would_push,
                    "substitutions": it.substitutions,
                } for it in result.items
            ],
        })

        if not confirmed:
            return result   # dry-run, nothing transmitted

        # G-30.1 / G-30.2: any L2 hit aborts the entire batch.
        if not result.all_clean:
            raise HubPushBlocked(
                f"push aborted — {sum(1 for it in result.items if not it.scan_clean)} "
                "artifact(s) hit PII/secret patterns; see quarantine YAML(s)"
            )
        # Real push: write anonymized text under endpoint-specific outbox.
        ep = self._resolve_endpoint(endpoint_id) if endpoint_id else None
        if ep is None:
            raise HubConfigError("real push requires --endpoint to be specified")
        outbox = REPO_ROOT / "build" / "reports" / "hub" / "push-outbox" / ep.id
        outbox.mkdir(parents=True, exist_ok=True)
        for it in result.items:
            if it.would_push and it.anonymized_text is not None:
                target = outbox / it.artifact_path.name
                target.write_text(it.anonymized_text, encoding="utf-8")
        return result

    def _prepare_push(self, artifacts: Iterable[Path], *, force_dry: bool) -> PushResult:
        rules_tuple, _ = load_l2_rules(self.anon_config.rules_path)
        items: List[PushItem] = []
        for artifact in artifacts:
            apath = Path(artifact)
            if not apath.exists():
                raise FileNotFoundError(f"artifact not found: {apath}")
            text = apath.read_text(encoding="utf-8", errors="replace")

            # Step 1 — L2 scan
            scan_res: ScanResult = scan(text, rules=rules_tuple)
            qpath: Optional[Path] = None
            if not scan_res.clean:
                qpath = write_quarantine(
                    apath, scan_res,
                    quarantine_dir=self.quarantine_dir,
                    trigger="pre_push_pii_scan",
                )
                items.append(PushItem(
                    artifact_path=apath,
                    scan_clean=False,
                    quarantine_path=qpath,
                    anonymized_text=None,
                    substitutions=0,
                    would_push=False,
                ))
                continue

            # Step 2 — anonymize L1
            anon_res = anonymize(text, config=self.anon_config)

            # Step 3 — re-scan to catch leakage anonymizer might have missed (G-30.7)
            scan_after = scan(anon_res.text, rules=rules_tuple)
            if not scan_after.clean:
                qpath = write_quarantine(
                    apath, scan_after,
                    quarantine_dir=self.quarantine_dir,
                    trigger="post_anonymize_scan",
                )
                items.append(PushItem(
                    artifact_path=apath,
                    scan_clean=False,
                    quarantine_path=qpath,
                    anonymized_text=anon_res.text,
                    substitutions=sum(s.count for s in anon_res.substitutions),
                    would_push=False,
                ))
                continue

            items.append(PushItem(
                artifact_path=apath,
                scan_clean=True,
                quarantine_path=None,
                anonymized_text=anon_res.text,
                substitutions=sum(s.count for s in anon_res.substitutions),
                would_push=not force_dry,
            ))
        return PushResult(endpoint_id=None, items=items, confirmed=not force_dry)

    # ─────────── diff ───────────
    def diff(self, rule_id: str, endpoint_id: Optional[str] = None) -> DiffResult:
        ep = self._resolve_endpoint(endpoint_id)
        cache_dir = self._endpoint_cache_dir(ep)
        # Locate the rule in cache (may be under rules/ or failure-patterns/)
        cached_path: Optional[Path] = None
        for candidate in cache_dir.rglob(f"{rule_id}.*"):
            cached_path = candidate
            break
        # Locate same id locally (rules/SLV-XXX.yaml or knowledge/failure-patterns/FPL-XXX.md)
        local_paths = [
            REPO_ROOT / ".claude" / "skills" / "spec-logical-validator" / "rules" / f"{rule_id}.yaml",
            REPO_ROOT / "knowledge" / "failure-patterns" / f"{rule_id}.md",
        ]
        local_path = next((p for p in local_paths if p.exists()), None)

        differs = True
        diff_text = ""
        if local_path and cached_path:
            local_text = local_path.read_text(encoding="utf-8")
            # DEF-CLDREV-030: cached_path holds untrusted hub content → bounded.
            cached_text = self._read_text_bounded(cached_path)
            differs = local_text != cached_text
            if differs:
                import difflib
                diff_text = "".join(difflib.unified_diff(
                    cached_text.splitlines(keepends=True),
                    local_text.splitlines(keepends=True),
                    fromfile=f"hub:{cached_path.name}",
                    tofile=f"local:{local_path.name}",
                ))
        return DiffResult(
            rule_id=rule_id,
            local_path=local_path,
            cached_hub_path=cached_path,
            differs=differs,
            diff_text=diff_text,
        )

    # ─────────── promote ───────────
    def promote(
        self,
        rule_path: Path,
        *,
        reviewer: str,
        notes: Optional[str] = None,
    ) -> PromoteResult:
        if not rule_path.exists():
            raise FileNotFoundError(f"rule not found: {rule_path}")
        if not reviewer or not reviewer.strip():
            raise ValueError("reviewer must be a non-empty string")
        # DEF-CLDREV-030: rule_path may be a cached external file → bounded read.
        doc = yaml.safe_load(self._read_text_bounded(rule_path)) or {}
        from_trust = str(doc.get("trust_level", ""))
        if from_trust != "external":
            raise ValueError(
                f"refuse to promote rule with trust_level={from_trust!r}; expected 'external'"
            )
        now = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        doc["trust_level"] = "verified"
        doc["reviewed_by"] = reviewer.strip()
        doc["reviewed_at"] = now
        # Append review_history entry per trust-ladder.md §4.2
        history = doc.setdefault("review_history", [])
        history.append({
            "reviewer": reviewer.strip(),
            "reviewed_at": now,
            "decision": "approve",
            "notes": notes,
        })
        # Update review_status if present
        if "review_status" in doc:
            doc["review_status"] = "reviewed"
        rule_path.write_text(
            yaml.safe_dump(doc, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return PromoteResult(
            rule_path=rule_path,
            from_trust=from_trust,
            to_trust="verified",
            reviewer=reviewer.strip(),
        )


# ─────────── CLI ───────────
def _cli() -> int:
    parser = argparse.ArgumentParser(description="Hub Sync Client (ACT-030)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_pull = sub.add_parser("pull")
    p_pull.add_argument("--endpoint", help="endpoint id (default: only one in registry)")
    p_pull.add_argument("--force", action="store_true")

    p_push = sub.add_parser("push")
    p_push.add_argument("--endpoint")
    p_push.add_argument("artifacts", nargs="+")

    p_dry = sub.add_parser("dry-run")
    p_dry.add_argument("artifacts", nargs="+")

    p_diff = sub.add_parser("diff")
    p_diff.add_argument("--endpoint")
    p_diff.add_argument("rule_id")

    p_prom = sub.add_parser("promote")
    p_prom.add_argument("rule_path")
    p_prom.add_argument("--reviewer", required=True)
    p_prom.add_argument("--notes")

    args = parser.parse_args()
    client = HubSyncClient()

    def emit(payload):
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2, default=str))

    try:
        if args.cmd == "pull":
            res = client.pull(args.endpoint, force=args.force)
            emit(dataclasses.asdict(res))
            return 0 if res.error is None else 2
        if args.cmd == "push":
            res = client.push([Path(p) for p in args.artifacts], endpoint_id=args.endpoint)
            emit({
                "endpoint_id": res.endpoint_id,
                "confirmed": res.confirmed,
                "all_clean": res.all_clean,
                "items": [dataclasses.asdict(it) for it in res.items],
                "audit_log_path": str(res.audit_log_path) if res.audit_log_path else None,
            })
            return 0 if res.all_clean else 1
        if args.cmd == "dry-run":
            res = client.dry_run([Path(p) for p in args.artifacts])
            emit({
                "all_clean": res.all_clean,
                "items": [dataclasses.asdict(it) for it in res.items],
            })
            return 0 if res.all_clean else 1
        if args.cmd == "diff":
            res = client.diff(args.rule_id, endpoint_id=args.endpoint)
            emit(dataclasses.asdict(res))
            return 0
        if args.cmd == "promote":
            res = client.promote(Path(args.rule_path), reviewer=args.reviewer, notes=args.notes)
            emit(dataclasses.asdict(res))
            return 0
    except (HubConfigError, HubPushBlocked, FileNotFoundError, ValueError) as exc:
        sys.stderr.write(f"[hub-sync][ERROR] {type(exc).__name__}: {exc}\n")
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(_cli())
