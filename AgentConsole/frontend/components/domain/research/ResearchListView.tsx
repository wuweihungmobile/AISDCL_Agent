"use client";

/**
 * 研究專案清單（`/research`，PRD 頁面 0；FR-R2P-01、03、21；TCS-ResearchToPRD-P0-20261102 AT-960-19-1、19-2）：
 * 標題「研發工作流」、動作「新建研究專案」（OPERATOR 以上；VIEWER 停用而不隱藏，`title` 為「權限不足（唯讀角色）」）、篩選與搜尋、每列一個研究專案
 * （`RP-NNNN`、命題摘要、迷你步驟列、狀態徽章、帶時區的更新時間、主連結「繼續（第 k 步：名稱）」、封存／復原）。
 *
 * 設計要點（為什麼這樣做）：
 *  - **零研究專案不自動跳轉、不退回他頁**（Console PRD §0.8 的靜默退回教訓）：顯示空狀態「還沒有任何研究專案」，新建入口只有頁首那一顆（空狀態內不再放第二顆同名按鈕）。
 *  - **迷你步驟列就是 `FlowStepper`**（`compact`）：全工作區只有一份五步列實作。
 *  - **新建對話框只收三件事**：命題、檢索深度、來源層（加代號，由命題自動產生、可改、建立後不可改）。其餘範圍欄位（納入／排除清單、技術棧、近年數、適用性軸）用預設
 *    （見 `toCreateRequest`）——框架模板要求 `inScope` 至少一項，所以預設取命題本身。`industry`（官方文獻與業界）是 Web 層，`capabilities.webLayerEnabled` 為假
 *    或探針失敗時勾選停用並說明（探針失敗時我們無從確認，寧可停用，伺服器端另有 `layer_unavailable` 擋一次）。
 *  - **已封存的專案另外請求**：後端的清單預設不含已封存的專案（TCS AT-960-4-6），所以狀態篩選選「已封存」時才以 `?archived=true` 另外抓那一份（才有得復原）；
 *    只有未封存的專案都沒有時篩選列不出現，空狀態另放「查看已封存的研究專案」進同一個篩選（否則封存了唯一的專案就找不回來）。
 *  - **「研究來源設定」等外部入口由頁殼以 `extraActions` 接入**（ADMIN 才看得到；本檔不認得它的內容，也不 import 它）。
 *  - 前端驗證（zod）只為更早給回饋；後端輸入閘與 Bridge 入口各再擋一次，後端的欄位錯誤與 `slug_in_use` 對應回欄位。
 */
import { Archive, ArchiveRestore, FlaskConical, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent, type ReactNode } from "react";

import { PageTitle } from "@/components/domain/PageHeader";
import { SortBar } from "@/components/domain/common/SortBar";
import { ConfirmDialog } from "@/components/domain/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogBody, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { useArchiveResearchProject, useCreateResearchProject, useResearchCapabilities, useResearchProjects, useRestoreResearchProject } from "@/lib/api/queries";
import type { ResearchDepthLevel, ResearchProjectSummary } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  DEPTH_OPTIONS,
  FLOW_STEP_IDS,
  FLOW_STEP_LABEL,
  LAYER_OPTIONS,
  PROJECT_BADGE_LABEL,
  READONLY_TITLE,
  continueLabel,
  createResearchErrors,
  createResearchSchema,
  deriveSteps,
  filterProjects,
  formatInstant,
  projectBadge,
  researchErrorText,
  slugFromTopic,
  toCreateRequest,
  type ProjectBadgeId,
  type ProjectFilter,
} from "@/lib/domain/research";
import { sortRows, type SortColumn, type SortState } from "@/lib/domain/sorting";
import { cn } from "@/lib/utils";

/**
 * 排序控制列（TCS-ConsoleUxSortHelp W-UX5／§2.2 L2）：API 回應序不變（更新時間新到舊），UI 預設依編號自然序升冪；欄位定義放元件內，`filterProjects` 不排序。
 * 排序與篩選各自獨立：切篩選不重置排序、搜尋縮小清單後仍依目前排序。
 */
const SORT_COLUMNS: ReadonlyArray<SortColumn<ResearchProjectSummary>> = [
  { key: "rpNo", kind: "id", get: (p) => p.rpNo },
  { key: "title", kind: "text", get: (p) => p.title },
  { key: "status", kind: "text", get: (p) => PROJECT_BADGE_LABEL[projectBadge(p)] },
  { key: "step", kind: "number", get: (p) => FLOW_STEP_IDS.indexOf(p.flowStep) },
  { key: "updatedAt", kind: "iso", get: (p) => p.updatedAt },
];
const SORT_OPTIONS = [
  { key: "rpNo", label: "編號" },
  { key: "title", label: "標題" },
  { key: "status", label: "狀態" },
  { key: "step", label: "步驟" },
  { key: "updatedAt", label: "最近更新" },
] as const;
const DEFAULT_SORT: NonNullable<SortState> = { key: "rpNo", dir: "asc" };
import { FlowStepper } from "./FlowStepper";

type FormErrors = Partial<Record<"topic" | "slug" | "depthLevel" | "layers", string>>;
type Layers = { academic: boolean; industry: boolean; oss: boolean; community: boolean };

/** 預設勾選（PRD §5.1.2 範例）：論文、開源 Repo、社群；官方文獻與業界（Web 層）預設關。 */
const DEFAULT_LAYERS: Layers = { academic: true, industry: false, oss: true, community: true };

/** 後端 400 的 `errors[].field` 對應回表單欄位（對不上的欄位名併入對話框頂端的說明）。 */
function fieldOf(name: string): keyof FormErrors | null {
  if (name.startsWith("topic")) return "topic";
  if (name.startsWith("slug")) return "slug";
  if (name.startsWith("depthLevel")) return "depthLevel";
  if (name.startsWith("scope")) return "layers";
  return null;
}

/** 新建研究專案對話框（只在開啟時渲染，所以每次開啟都是乾淨的表單）。 */
function CreateResearchDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {open ? (
        <DialogContent title="新建研究專案" description="輸入研究命題、檢索深度與來源層，建立後在工作區啟動深研">
          <CreateForm onClose={() => onOpenChange(false)} />
        </DialogContent>
      ) : null}
    </Dialog>
  );
}

function CreateForm({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const toast = useToast();
  const capabilities = useResearchCapabilities();
  const create = useCreateResearchProject();
  const webLayerEnabled = capabilities.data?.webLayerEnabled === true;
  const [topic, setTopic] = useState("");
  const [slugEdit, setSlugEdit] = useState<string | null>(null);
  const [depth, setDepth] = useState<ResearchDepthLevel>("STANDARD");
  const [layers, setLayers] = useState<Layers>(DEFAULT_LAYERS);
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);

  const slug = slugEdit ?? (topic.trim() === "" ? "" : slugFromTopic(topic));
  // Web 層未啟用（或探針失敗）時 industry 一律當作關閉，即使先前勾過
  const effectiveLayers: Layers = { ...layers, industry: layers.industry && webLayerEnabled };

  async function submit(event: FormEvent) {
    event.preventDefault();
    const form = { topic, slug, depthLevel: depth, layers: effectiveLayers };
    const found = createResearchErrors(form);
    setSubmitError(null);
    if (Object.keys(found).length > 0) {
      setErrors(found);
      return;
    }
    setErrors({});
    try {
      const created = await create.mutateAsync(toCreateRequest(createResearchSchema.parse(form)));
      toast.success(`已建立研究專案 ${created.rpNo}`);
      onClose();
      router.push(`/research/${created.id}`);
    } catch (e) {
      const mapped: FormErrors = {};
      const rest: string[] = [];
      if (e instanceof ApiError && e.reason === "slug_in_use") mapped.slug = researchErrorText(e);
      else if (e instanceof ApiError && e.errors.length > 0) {
        for (const item of e.errors) {
          const key = fieldOf(item.field);
          if (key === null) rest.push(`${item.field}：${item.message}`);
          else mapped[key] = mapped[key] ?? item.message;
        }
      } else rest.push(researchErrorText(e));
      setErrors(mapped);
      setSubmitError(rest.length > 0 ? rest.join("；") : null);
    }
  }

  return (
    <form onSubmit={submit} noValidate>
      <DialogBody>
        {submitError ? (
          <p role="alert" data-testid="create-error" className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm text-wg-accent">
            {submitError}
          </p>
        ) : null}
        <div className="flex flex-col gap-1">
          <Field label="研究命題" error={errors.topic}>
            <Textarea value={topic} onChange={(e) => setTopic(e.target.value)} aria-invalid={errors.topic ? true : undefined} placeholder="例：自架向量資料庫的選型與取捨" />
          </Field>
          <p className="text-xs text-wg-muted">必填，最多 500 字。</p>
        </div>
        <div className="flex flex-col gap-1">
          <Field label="網址代號" error={errors.slug}>
            <Input value={slug} onChange={(e) => setSlugEdit(e.target.value)} aria-invalid={errors.slug ? true : undefined} />
          </Field>
          <p className="text-xs text-wg-muted">小寫英數與連字號；由命題自動產生、可改，建立後不可改。</p>
        </div>
        <Field as="group" label="檢索深度" error={errors.depthLevel}>
          <div role="radiogroup" aria-label="檢索深度" className="flex flex-wrap gap-2">
            {DEPTH_OPTIONS.map((option) => (
              <label key={option.id} className={cn("flex cursor-pointer flex-col rounded-md border px-3 py-2 text-sm", depth === option.id ? "border-wg-primary bg-wg-base" : "border-wg-line")}>
                <span className="flex items-center gap-2 font-medium">
                  <input type="radio" name="depthLevel" value={option.id} checked={depth === option.id} onChange={() => setDepth(option.id)} />
                  {option.label}
                </span>
                <span className="text-xs text-wg-muted">{option.hint}</span>
              </label>
            ))}
          </div>
        </Field>
        <Field as="group" label="來源層" error={errors.layers}>
          <div className="flex flex-col gap-2">
            <p className="text-xs text-wg-muted">至少勾選一個。</p>
            {LAYER_OPTIONS.map((layer) => {
              const disabled = layer.id === "industry" && !webLayerEnabled;
              return (
                <label key={layer.id} className={cn("flex items-center gap-2 text-sm", disabled && "text-wg-muted")}>
                  <Checkbox checked={effectiveLayers[layer.id]} disabled={disabled} onCheckedChange={(v) => setLayers((current) => ({ ...current, [layer.id]: v === true }))} />
                  {layer.label}
                </label>
              );
            })}
            {!webLayerEnabled ? <p className="text-xs text-wg-muted">「官方文獻與業界」需要先啟用 Web 層（目前沒有任何網域在允許清單內），所以暫時不能勾選。</p> : null}
          </div>
        </Field>
      </DialogBody>
      <DialogFooter>
        <Button variant="ghost" onClick={onClose} disabled={create.isPending}>
          取消
        </Button>
        <Button type="submit" loading={create.isPending}>
          建立
        </Button>
      </DialogFooter>
    </form>
  );
}

const BADGE_CLASS: Readonly<Record<ProjectBadgeId, string>> = {
  // 主色字坐在 bg-base 上對比 4.21:1（axe color-contrast serious，FE-D 三寬度實測）；
  // 改用 primary-strong（同 FlowStepper DONE chip 與 tokens.console.css〈無障礙覆寫〉先例）
  active: "bg-wg-base text-wg-primary-strong",
  frozen: "bg-wg-base text-wg-primary-strong",
  delivered: "bg-wg-base text-wg-primary-strong",
  scr: "bg-wg-alert-bg text-wg-warning-text",
  // 階段失敗與取消（INT-14⑥）與初始化失敗同一組既有 token（accent 字坐在 draft-bg 上，對比 ≥ 4.5；FlowStepper 的「受阻」chip 同色）
  failed: "bg-wg-draft-bg text-wg-accent",
  init_failed: "bg-wg-draft-bg text-wg-accent",
  archived: "bg-wg-base text-wg-muted",
};

function ResearchRow({ project, canWrite, busy, onArchive, onRestore }: { project: ResearchProjectSummary; canWrite: boolean; busy: boolean; onArchive: () => void; onRestore: () => void }) {
  const badge = projectBadge(project);
  return (
    <li data-testid="research-row" data-research-id={project.id} data-badge={badge}>
      <Card className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3.5">
        <span className="font-mono text-sm text-wg-muted">{project.rpNo}</span>
        <span className="min-w-0 flex-1 truncate text-[17px] font-semibold text-wg-text" title={project.title}>
          {project.title}
        </span>
        <span data-testid="research-badge" className={cn("rounded-sm px-2 py-0.5 text-xs font-semibold", BADGE_CLASS[badge])}>
          {PROJECT_BADGE_LABEL[badge]}
        </span>
        <FlowStepper compact steps={deriveSteps(project.flowStep, project.flowStatus)} label={`${project.rpNo} 的步驟`} />
        <time dateTime={project.updatedAt} className="text-[13px] text-wg-muted">
          {formatInstant(project.updatedAt)}
        </time>
        <Link href={`/research/${project.id}`} className="text-sm font-medium text-wg-primary hover:underline">
          {continueLabel(project.flowStep)}
        </Link>
        {badge === "archived" ? (
          <Button
            size="sm"
            variant="ghost"
            iconLeft={ArchiveRestore}
            aria-label={`復原 ${project.rpNo}`}
            disabled={!canWrite || busy}
            title={canWrite ? undefined : READONLY_TITLE}
            onClick={onRestore}
          >
            復原
          </Button>
        ) : (
          <Button size="sm" variant="ghost" iconLeft={Archive} aria-label={`封存 ${project.rpNo}`} disabled={!canWrite} title={canWrite ? undefined : READONLY_TITLE} onClick={onArchive}>
            封存
          </Button>
        )}
      </Card>
    </li>
  );
}

const ALL_FILTER: ProjectFilter = { q: "", status: "all", step: "all" };

export function ResearchListView({ extraActions }: { extraActions?: ReactNode }) {
  const { canWrite } = useAuth();
  const toast = useToast();
  const archive = useArchiveResearchProject();
  const restore = useRestoreResearchProject();
  const [filter, setFilter] = useState<ProjectFilter>(ALL_FILTER);
  const [sort, setSort] = useState<NonNullable<SortState>>(DEFAULT_SORT);
  const [creating, setCreating] = useState(false);
  const [archiving, setArchiving] = useState<ResearchProjectSummary | null>(null);
  const [restoringId, setRestoringId] = useState<string | null>(null);
  // 後端的清單預設不含已封存的專案：狀態篩選選「已封存」時才另外請求已封存的那一份（才有得復原）；其餘時候只用預設那份
  const activeList = useResearchProjects();
  const archivedList = useResearchProjects({ archived: true, enabled: filter.status === "archived" });
  const list = filter.status === "archived" ? archivedList : activeList;
  const projects = list.data;
  const shown = projects === undefined ? [] : sortRows(filterProjects(projects, filter), SORT_COLUMNS, sort);
  const filtering = filter.q.trim() !== "" || filter.status !== "all" || filter.step !== "all";
  // 標題列的總數與篩選列的有無都看「未封存」那份：選到「已封存」時另一份才載入，篩選列不能跟著它消失（否則回不去）
  const activeCount = activeList.data?.length;

  async function onRestore(project: ResearchProjectSummary) {
    setRestoringId(project.id);
    try {
      await restore.mutateAsync(project.id);
      toast.success(`已復原研究專案 ${project.rpNo}`);
    } catch (e) {
      toast.error(`復原失敗：${researchErrorText(e)}`);
    } finally {
      setRestoringId(null);
    }
  }

  return (
    <div data-testid="research-list-view">
      <PageTitle
        className="mb-[18px]"
        icon={FlaskConical}
        title="研發工作流"
        subtitle={`從研究議題到凍結規格的單一工作流${activeCount === undefined ? "" : ` · 共 ${activeCount} 個研究專案`}`}
        actions={
          <>
            {extraActions}
            <Button iconLeft={Plus} disabled={!canWrite} title={canWrite ? undefined : READONLY_TITLE} onClick={() => setCreating(true)}>
              新建研究專案
            </Button>
          </>
        }
      />

      {(activeCount ?? 0) > 0 || filtering ? (
        <div className="mb-5 flex flex-wrap items-center gap-3 rounded-md border border-wg-line bg-wg-surface px-3.5 py-2.5">
          <Input
            aria-label="搜尋研究專案"
            placeholder="搜尋編號、名稱或代號"
            value={filter.q}
            onChange={(e) => setFilter((current) => ({ ...current, q: e.target.value }))}
            className="max-w-[280px] min-h-9 py-1.5 text-sm"
          />
          <Select size="sm" aria-label="狀態篩選" value={filter.status} onChange={(e) => setFilter((current) => ({ ...current, status: e.target.value as ProjectFilter["status"] }))}>
            <option value="all">全部狀態（不含已封存）</option>
            {(Object.keys(PROJECT_BADGE_LABEL) as ProjectBadgeId[]).map((id) => (
              <option key={id} value={id}>
                {PROJECT_BADGE_LABEL[id]}
              </option>
            ))}
          </Select>
          <Select size="sm" aria-label="步驟篩選" value={filter.step} onChange={(e) => setFilter((current) => ({ ...current, step: e.target.value as ProjectFilter["step"] }))}>
            <option value="all">全部步驟</option>
            {FLOW_STEP_IDS.map((id) => (
              <option key={id} value={id}>
                {FLOW_STEP_LABEL[id]}
              </option>
            ))}
          </Select>
          <SortBar options={SORT_OPTIONS} state={sort} onChange={setSort} label="研究專案排序" />
        </div>
      ) : null}

      {projects === undefined ? (
        list.isError ? (
          <ErrorState error={list.error} onRetry={() => void list.refetch()} title="無法載入研究專案清單" />
        ) : (
          <div className="flex flex-col gap-4" aria-busy="true" aria-label="研究專案清單載入中">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-[72px] rounded-lg" />
            ))}
          </div>
        )
      ) : shown.length === 0 ? (
        <Card>
          <EmptyState
            title={filtering ? "沒有符合條件的研究專案" : "還沒有任何研究專案"}
            description={filtering ? "調整篩選條件或清除搜尋看看。" : "按右上「新建研究專案」，輸入研究命題後開始。"}
            action={
              filtering ? undefined : (
                // 只有未封存的專案都沒有時，篩選列不出現：這顆鈕是通往「已封存」（可復原）的唯一入口，不然封存了唯一的專案就找不回來
                <Button size="sm" variant="ghost" onClick={() => setFilter({ ...ALL_FILTER, status: "archived" })}>
                  查看已封存的研究專案
                </Button>
              )
            }
          />
        </Card>
      ) : (
        <ul role="list" aria-label="研究專案清單" data-testid="research-list" className="flex flex-col gap-3">
          {shown.map((project) => (
            <ResearchRow key={project.id} project={project} canWrite={canWrite} busy={restoringId === project.id} onArchive={() => setArchiving(project)} onRestore={() => void onRestore(project)} />
          ))}
        </ul>
      )}

      <CreateResearchDialog open={creating} onOpenChange={setCreating} />
      <ConfirmDialog
        open={archiving !== null}
        title="封存研究專案"
        confirmLabel="封存"
        formatError={researchErrorText}
        onClose={() => setArchiving(null)}
        onConfirm={async () => {
          if (archiving === null) return;
          await archive.mutateAsync(archiving.id);
          toast.success(`已封存研究專案 ${archiving.rpNo}，30 天內可復原`);
          setArchiving(null);
        }}
      >
        封存「{archiving?.title}」後，它會從清單消失；30 天內可在狀態篩選選「已封存」後復原。
      </ConfirmDialog>
    </div>
  );
}
