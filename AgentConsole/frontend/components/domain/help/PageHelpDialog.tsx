"use client";

/**
 * 「本頁說明」對話框（TCS-PageHelp-20261027 D-PH-3、D-PH-5～D-PH-8、C4；PRD §7、FR-PH-02、FR-PH-04）：建於共用的 `DialogContent`（焦點鎖、Esc、焦點歸還、尺寸與捲動都沿用，不自刻、不傳 `onCloseAutoFocus`），
 * 標題「<固定頁名>・本頁說明」，由上而下四段——這頁做什麼、怎麼用（`ol`）、欄位說明（三欄表）、狀態說明（每張狀態表一個 h4 小標題與一張三欄表；議題中心頁改為 API 詞表四群）——
 * 其後是預設收合的「全站共通」（`details`）。全對話框 h3 恰四個，小標題與群組標題一律 h4。
 *  - 純文字：登記的每一段文字都以 React 文字節點渲染，不經 HTML 或 Markdown；
 *  - 沒有第二份說明：對話框內除登記內容（頁、狀態、全站共通、狀態名稱來源）外，只有固定的標題、欄標題與空狀態句；狀態名稱一律取自 `content.sources`（現讀既有常數表），這裡不寫死任何狀態詞；
 *  - 測試縫：`content` 參數是唯一的注入縫（缺省取真登記，以模組常數作預設值、不在每次渲染重建）；合成頁、哨兵內容與 raw 模式的測試都只經它與 `page`，不換掉登記模組；
 *  - 表格：每個 `td` 帶 `data-label`＝欄標題；窄螢幕（< 768）表格改逐列堆疊，欄標題由 CSS 以 `data-label` 當列內小標（文字不進 DOM，所以 textContent 與欄位文字逐字相同）。
 * 狀態表的列序＝登記表的鍵序（`content.states[表 id]`）；「狀態」欄在 label 模式印 `labelOf(key)`、raw 模式印鍵本身（欄標題改「畫面上的原值」）。
 */
import type { ReactNode } from "react";

import { Dialog, DialogBody, DialogContent } from "@/components/ui/dialog";
import { HELP_COMMON } from "@/lib/help/common";
import { STATE_HELP } from "@/lib/help/states";
import type { CommonHelp, HelpField, HelpStateGroup, PageHelp, StateRow, StateTableId } from "@/lib/help/types";
import { IssuesLegendGroups } from "./IssuesLegendGroups";
import { STATE_SOURCES, type StateSource } from "./stateSources";

// StateSource 先由 stateSources.ts 定義（輪 1a），對話框的公共面在此再匯出（TCS 公共面表）
export type { StateSource };

/** 對話框要用的全部登記內容；缺省取真登記，測試經 `content` 參數換成哨兵或合成內容（D-PH-3）。 */
export type HelpContent = {
  common: CommonHelp;
  states: Readonly<Record<StateTableId, Readonly<Record<string, StateRow>>>>;
  sources: Readonly<Record<StateTableId, StateSource>>;
};

const DEFAULT_CONTENT: HelpContent = { common: HELP_COMMON, states: STATE_HELP, sources: STATE_SOURCES };

const FIELD_HEADS = ["欄位", "意思", "資料來源"] as const;
const STATE_HEADS = ["狀態", "意思", "通常的下一步"] as const;
const RAW_HEADS = ["畫面上的原值", "意思", "通常的下一步"] as const;

// 窄螢幕（< 768）：table／tbody／tr／td 都改 block 逐列堆疊，thead 只留給螢幕閱讀器；欄標題以 ::before 取 data-label 當列內小標
const TABLE = "w-full border-collapse text-left text-sm max-md:block";
const THEAD = "max-md:sr-only";
const TBODY = "max-md:block";
const ROW = "border-t border-wg-line max-md:block max-md:py-2";
const HEAD = "px-2 py-1.5 font-medium text-wg-muted";
const CELL =
  "px-2 py-2 align-top break-words max-md:block max-md:px-0 max-md:py-0.5 max-md:before:mb-0.5 max-md:before:block max-md:before:text-xs max-md:before:font-medium max-md:before:text-wg-muted max-md:before:content-[attr(data-label)]";

type TableRow = { key: string; cells: readonly ReactNode[] };

/** 三欄表：`aria-label` 名稱、`th scope="col"` 欄標題、每個 `td` 帶 `data-label`＝對應欄標題。 */
function HelpTable({ label, heads, rows }: { label: string; heads: readonly string[]; rows: readonly TableRow[] }) {
  return (
    <table aria-label={label} className={TABLE}>
      <thead className={THEAD}>
        <tr>
          {heads.map((head) => (
            <th key={head} scope="col" className={HEAD}>
              {head}
            </th>
          ))}
        </tr>
      </thead>
      <tbody className={TBODY}>
        {rows.map((row) => (
          <tr key={row.key} className={ROW}>
            {row.cells.map((cell, i) => (
              <td key={heads[i]} data-label={heads[i]} className={CELL}>
                {cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** 欄位表：欄位名、意思、資料來源（有補充說明者同一格再列一行）。 */
function FieldsTable({ label, fields }: { label: string; fields: readonly HelpField[] }) {
  const rows = fields.map((field, i) => ({
    key: `${i}-${field.name}`,
    cells: [
      field.name,
      field.meaning,
      <>
        {field.source}
        {field.sourceNote !== undefined ? <span className="block text-xs text-wg-muted">{field.sourceNote}</span> : null}
      </>,
    ],
  }));
  return <HelpTable label={label} heads={FIELD_HEADS} rows={rows} />;
}

/** 一張狀態表：h4 小標題（取自名稱來源）加三欄表；名稱模式見檔頭。 */
function StateTable({ id, name, content, testId }: { id: StateTableId; name: "label" | "raw"; content: HelpContent; testId: string }) {
  const source = content.sources[id];
  const labelOf = name === "label" ? source.labelOf : undefined;
  const rows = Object.entries(content.states[id]).map(([key, row]) => ({ key, cells: [labelOf !== undefined ? labelOf(key) : key, row.meaning, row.next] }));
  return (
    <div data-testid={testId} className="flex flex-col gap-1.5">
      <h4 className="text-sm font-semibold">{source.title}</h4>
      <HelpTable label={source.title} heads={labelOf !== undefined ? STATE_HEADS : RAW_HEADS} rows={rows} />
    </div>
  );
}

function Section({ testId, heading, children }: { testId: string; heading: string; children: ReactNode }) {
  return (
    <section data-testid={testId} className="flex flex-col gap-2">
      <h3 className="text-base font-semibold">{heading}</h3>
      {children}
    </section>
  );
}

/** 狀態說明段：沒有狀態的頁只有固定一句；議題中心的 API 詞表四群；其餘是每張狀態表一個群。 */
function StatesSection({ groups, content }: { groups: readonly HelpStateGroup[]; content: HelpContent }) {
  if (groups.length === 0) return <p className="text-sm">這一頁沒有會變動的狀態。</p>;
  return (
    <>
      {groups.map((group, i) =>
        "legend" in group ? (
          <IssuesLegendGroups key={`${i}-legend`} />
        ) : (
          <StateTable key={`${i}-${group.table}`} id={group.table} name={group.name ?? "label"} content={content} testId={`page-help-states-${group.table}`} />
        ),
      )}
    </>
  );
}

export function PageHelpDialog({ page, open, onOpenChange, content = DEFAULT_CONTENT }: { page: PageHelp; open: boolean; onOpenChange: (open: boolean) => void; content?: HelpContent }) {
  const common = content.common;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="page-help-dialog" title={`${page.title}・本頁說明`}>
        <DialogBody>
          <Section testId="page-help-purpose" heading="這頁做什麼">
            {page.purpose.map((text, i) => (
              <p key={`${i}-${text}`} className="text-sm">
                {text}
              </p>
            ))}
          </Section>
          <Section testId="page-help-steps" heading="怎麼用">
            <ol className="list-decimal space-y-1 pl-5 text-sm">
              {page.steps.map((text, i) => (
                <li key={`${i}-${text}`}>{text}</li>
              ))}
            </ol>
          </Section>
          <Section testId="page-help-fields" heading="欄位說明">
            <FieldsTable label="欄位說明" fields={page.fields} />
          </Section>
          <Section testId="page-help-states" heading="狀態說明">
            <StatesSection groups={page.states} content={content} />
          </Section>
          <details data-testid="page-help-common" className="rounded-md border border-wg-line">
            <summary className="cursor-pointer px-3 py-2 text-sm font-medium">全站共通</summary>
            <div className="flex flex-col gap-3 px-3 pt-1 pb-3">
              <FieldsTable label="全站共通" fields={common.fields} />
              {common.states.map((group, i) =>
                "table" in group ? <StateTable key={`${i}-${group.table}`} id={group.table} name={group.name ?? "label"} content={content} testId={`page-help-common-states-${group.table}`} /> : null,
              )}
            </div>
          </details>
        </DialogBody>
      </DialogContent>
    </Dialog>
  );
}
