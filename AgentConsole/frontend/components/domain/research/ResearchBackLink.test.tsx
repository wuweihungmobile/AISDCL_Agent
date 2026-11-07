import { render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import path from "node:path";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResearchBackLink, ResearchBackLinkFromQuery } from "./ResearchBackLink";

/**
 * ResearchBackLink（TCS-ResearchToPRD-P2-20261107 AT-962-16-1、16-E-2、16-E-3；AC-R2P-01-5；D-138 Q-11）：
 * 只收標準 UUID（不分大小寫）才渲染「回到研發工作流」，其餘 DOM 為空；零後端、零儲存。
 * 判定指令：npx vitest run components/domain/research/ResearchBackLink.test.tsx -t "<AT 底線形>"
 */
const nav = vi.hoisted(() => ({ search: "" }));
vi.mock("next/navigation", () => ({ useSearchParams: () => new URLSearchParams(nav.search) }));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const UUID = "3f2b8c1e-5a47-4d09-9e61-0c7a1b2d3e4f";
const ROOT = process.cwd();

afterEach(() => {
  nav.search = "";
  vi.restoreAllMocks();
});

describe("AT_962_16_1 ResearchBackLink：UUID 顯示回到研發工作流，href 固定；null 不渲染", () => {
  it("AT_962_16_1 UUID：<a> 文字為「回到研發工作流」、href 為 /research/<id>?step=build", () => {
    render(<ResearchBackLink researchId={UUID} />);
    const link = screen.getByRole("link", { name: "回到研發工作流" });
    expect(link).toHaveAttribute("href", `/research/${UUID}?step=build`);
  });

  it("AT_962_16_1 null：DOM 為空", () => {
    const { container } = render(<ResearchBackLink researchId={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("AT_962_16_1 ResearchBackLinkFromQuery 讀網址的 researchId；無參數不渲染", () => {
    nav.search = `researchId=${UUID}`;
    const first = render(<ResearchBackLinkFromQuery />);
    expect(screen.getByRole("link", { name: "回到研發工作流" })).toHaveAttribute("href", `/research/${UUID}?step=build`);
    first.unmount();
    nav.search = "";
    const second = render(<ResearchBackLinkFromQuery />);
    expect(second.container).toBeEmptyDOMElement();
  });
});

describe("AT_962_16_E_2 非 UUID 一律忽略", () => {
  const BAD = ["../x", "<script>alert(1)</script>", "3f2b8c1e-5a47-4d09-9e61-0c7a1b2d3e4", "3f2b8c1e-5a47-4d09-9e61-0c7a1b2d3e4g", "", "3f2b8c1e5a474d099e610c7a1b2d3e4f0000"];

  it.each(BAD.map((value) => [value] as const))("AT_962_16_E_2 researchId=%j：不渲染", (value) => {
    const { container } = render(<ResearchBackLink researchId={value} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("AT_962_16_E_2 35 字元與含 g 的 36 字元確實是長度不符／非十六進位（防測資自己寫錯）", () => {
    expect(BAD[2]).toHaveLength(35);
    expect(BAD[3]).toHaveLength(36);
    expect(BAD[3]).toMatch(/g/);
  });

  it("AT_962_16_E_2 合法大小寫混合 UUID 渲染（比對不分大小寫）；href 原樣帶入", () => {
    const mixed = "3F2b8C1e-5A47-4d09-9E61-0c7A1b2D3e4F";
    render(<ResearchBackLink researchId={mixed} />);
    expect(screen.getByRole("link", { name: "回到研發工作流" })).toHaveAttribute("href", `/research/${mixed}?step=build`);
  });

  it("AT_962_16_E_2 網址 query 帶路徑穿越時 FromQuery 也不渲染", () => {
    nav.search = `researchId=${encodeURIComponent("../x")}`;
    const { container } = render(<ResearchBackLinkFromQuery />);
    expect(container).toBeEmptyDOMElement();
  });
});

/** 剝掉區塊與單行註解後的原始碼（只判程式，不被說明文字誤判）。 */
function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/.*$/gm, "$1");
}

describe("AT_962_16_E_3 零後端、零儲存；頁面殼零差異", () => {
  it("AT_962_16_E_3 渲染 BackLink（有值、null、FromQuery）時 fetch、localStorage、sessionStorage 呼叫 0", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const proto = Storage.prototype;
    const spies = [vi.spyOn(proto, "getItem"), vi.spyOn(proto, "setItem"), vi.spyOn(proto, "removeItem"), vi.spyOn(proto, "clear")];
    nav.search = `researchId=${UUID}`;
    render(
      <>
        <ResearchBackLink researchId={UUID} />
        <ResearchBackLink researchId={null} />
        <ResearchBackLinkFromQuery />
      </>,
    );
    expect(fetchSpy).not.toHaveBeenCalled();
    for (const spy of spies) expect(spy).not.toHaveBeenCalled();
  });

  it("AT_962_16_E_3 原始碼（剝註解後）沒有 fetch(、localStorage、sessionStorage、document.cookie", () => {
    const code = stripComments(readFileSync(path.join(ROOT, "components/domain/research/ResearchBackLink.tsx"), "utf8"));
    expect(code.length).toBeGreaterThan(200); // 防反空轉：確實讀到程式
    for (const banned of ["fetch(", "localStorage", "sessionStorage", "document.cookie"]) expect(code, banned).not.toContain(banned);
    // 負控：同一支剝註解函式確實抓得到違規字樣
    expect(stripComments("const a = localStorage.getItem('x'); // 註解")).toContain("localStorage");
  });

  it("AT_962_16_E_3 兩個頁殼 page.tsx 沒有 Suspense 與回連（Suspense 住在 ResearchBackLink；頁殼零差異，git diff 為空由交卷另證）", () => {
    for (const center of ["execute", "monitor"]) {
      const page = readFileSync(path.join(ROOT, `app/projects/[projectId]/${center}/page.tsx`), "utf8");
      expect(page, center).not.toMatch(/Suspense|ResearchBackLink/);
    }
  });
});
