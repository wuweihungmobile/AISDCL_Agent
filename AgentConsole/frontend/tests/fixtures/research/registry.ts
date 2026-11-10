/**
 * 研究來源單一化的前端夾具（TCS-ResearchRegistry-20261110 §5.2）：17 列種子追蹤來源（啟用 10、停用 7）與同步狀態夾具 `REGISTRY_STATUS(state)`。
 * 不被 vitest 收集（沿 tests/fixtures/research 先例）；元件測試與 `stubResearchApi` 共用。
 */
import type { RegistrySyncResult, RegistrySyncStatus, WatchSource } from "@/lib/api/types";

const T = "2026-11-10T08:00:00Z";

const seed = (slug: string, host: string, path: string, enabled: boolean, over: Partial<WatchSource> = {}): WatchSource => ({
  slug,
  url: `https://${host}${path}`,
  host,
  kind: "blog",
  extract: `逐字保留 ${slug} 的最新條目`,
  layer: "INDUSTRY",
  expand: null,
  enabled,
  hostAllowed: true,
  addedBy: "system",
  addedAt: T,
  disabledBy: enabled ? null : "admin",
  disabledAt: enabled ? null : T,
  ...over,
});

/** 17 列：前 10 列啟用、後 7 列停用（依 slug 位元組序）。 */
export const WATCH_SOURCES_17 = (): WatchSource[] => [
  seed("anthropic-engineering", "www.anthropic.com", "/engineering", true, { expand: { mode: "links", prefix: "/engineering/", max: 3 } }),
  seed("anthropic-sitemap", "www.anthropic.com", "/sitemap.xml", true, { kind: "sitemap" }),
  seed("arxiv-agent-memory", "export.arxiv.org", "/api/query?search_query=agent", true, { kind: "search", layer: "ACADEMIC" }),
  seed("claude-code-changelog", "raw.githubusercontent.com", "/anthropics/claude-code/main/CHANGELOG.md", true, { kind: "changelog", layer: "OSS" }),
  seed("claude-code-hooks", "code.claude.com", "/docs/en/hooks-guide", true, { kind: "docs" }),
  seed("claude-code-memory", "code.claude.com", "/docs/en/memory", true, { kind: "docs" }),
  seed("claude-code-releases", "github.com", "/anthropics/claude-code/releases.atom", true, { kind: "release", layer: "OSS" }),
  seed("claude-code-skills", "code.claude.com", "/docs/en/skills", true, { kind: "docs" }),
  seed("openai-agents-releases", "github.com", "/openai/openai-agents-python/releases.atom", true, { kind: "release", layer: "OSS" }),
  seed("openai-changelog", "platform.openai.com", "/docs/changelog", true, { kind: "changelog" }),
  seed("anthropic-sdk-releases", "github.com", "/anthropics/anthropic-sdk-python/releases.atom", false, { kind: "release", layer: "OSS" }),
  seed("claude-code-hooks-md", "code.claude.com", "/docs/en/hooks-guide.md", false, { kind: "docs" }),
  seed("claude-code-llms", "code.claude.com", "/docs/llms.txt", false, { kind: "docs" }),
  seed("claude-code-memory-md", "code.claude.com", "/docs/en/memory.md", false, { kind: "docs" }),
  seed("claude-code-skills-md", "code.claude.com", "/docs/en/skills.md", false, { kind: "docs" }),
  seed("openai-agents-tags", "github.com", "/openai/openai-agents-python/tags.atom", false, { kind: "release", layer: "OSS" }),
  seed("openai-changelog-md", "developers.openai.com", "/api/docs/changelog.md", false, { kind: "changelog", hostAllowed: false }),
];

const SHA_A = `sha256:${"a".repeat(64)}`;
const SHA_B = `sha256:${"b".repeat(64)}`;
const UUID = "11111111-1111-4111-8111-111111111111";

export type RegistryStatusKind =
  "synced" | "unsynced" | "unsynced-never" | "pending" | "unknown-si_unavailable" | "unknown-scan_cap_exceeded" | "unknown-bridge_unreachable" | "unknown-bridge_timeout";

/** 同步狀態夾具；`researchFetchMax` 預設 10（可覆寫為 8 或 null）。 */
export const REGISTRY_STATUS = (kind: RegistryStatusKind = "unsynced", over: Partial<RegistrySyncStatus> = {}): RegistrySyncStatus => {
  const base: RegistrySyncStatus = {
    state: "unsynced",
    unknownCause: null,
    currentSha256: SHA_B,
    ingestedSha256: SHA_A,
    ingestedAuditRef: UUID,
    pendingAuditRef: null,
    pendingTime: null,
    researchFetchMax: 10,
  };
  const byKind: Partial<RegistrySyncStatus> =
    kind === "synced"
      ? { state: "synced", ingestedSha256: SHA_B }
      : kind === "unsynced-never"
        ? { state: "unsynced", ingestedSha256: null, ingestedAuditRef: null }
        : kind === "pending"
          ? { state: "pending", pendingAuditRef: "22222222-2222-4222-8222-222222222222", pendingTime: "2026-11-10T16:05:00+08:00" }
          : kind.startsWith("unknown-")
            ? { state: "unknown", unknownCause: kind.slice("unknown-".length) as RegistrySyncStatus["unknownCause"] }
            : {};
  return { ...base, ...byKind, ...over };
};

export const SYNC_WRITTEN: RegistrySyncResult = {
  outcome: "written",
  state: "pending",
  registrySha256: SHA_B,
  auditRef: "22222222-2222-4222-8222-222222222222",
  kind: "src-registry",
  time: "2026-11-10T16:05:00+08:00",
  keyId: "abcd1234",
};
export const SYNC_UNCHANGED: RegistrySyncResult = { ...SYNC_WRITTEN, outcome: "unchanged", state: "synced" };
