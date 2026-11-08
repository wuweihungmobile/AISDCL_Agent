import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { SortableHeader } from "@/components/domain/common/SortableHeader";
import { nextSort, type SortState } from "@/lib/domain/sorting";

function Table({ state, onSort, defaultSort }: { state: SortState; onSort: (k: string) => void; defaultSort?: SortState }) {
  return (
    <table>
      <thead>
        <tr>
          <SortableHeader column="A" label="欄A" state={state} onSort={onSort} defaultSort={defaultSort} />
          <SortableHeader column="B" label="欄B" state={state} onSort={onSort} defaultSort={defaultSort} />
          <SortableHeader column="C" label="欄C" state={state} onSort={onSort} defaultSort={defaultSort} />
          <th scope="col">操作</th>
        </tr>
      </thead>
    </table>
  );
}

const sorts = () => screen.getAllByRole("columnheader").map((h) => h.getAttribute("aria-sort"));

describe("SortableHeader", () => {
  it("AT_963_2_1 aria-sort 依 state 與 defaultSort", () => {
    const { rerender } = render(<Table state={{ key: "B", dir: "asc" }} onSort={() => {}} />);
    expect(sorts().slice(0, 3)).toEqual(["none", "ascending", "none"]);
    rerender(<Table state={{ key: "B", dir: "desc" }} onSort={() => {}} />);
    expect(sorts().slice(0, 3)).toEqual(["none", "descending", "none"]);
    rerender(<Table state={null} defaultSort={{ key: "A", dir: "asc" }} onSort={() => {}} />);
    expect(sorts().slice(0, 3)).toEqual(["ascending", "none", "none"]);
  });

  it("AT_963_2_2 原生按鈕 Enter／Space 可觸發 onSort", async () => {
    const onSort = vi.fn();
    render(<Table state={null} onSort={onSort} />);
    const btn = screen.getByRole("button", { name: "欄B" });
    expect(btn).toHaveAttribute("type", "button");
    btn.focus();
    await userEvent.keyboard("{Enter}");
    expect(onSort).toHaveBeenCalledTimes(1);
    await userEvent.keyboard(" ");
    expect(onSort).toHaveBeenCalledTimes(2);
    expect(onSort).toHaveBeenCalledWith("B");
  });

  it("AT_963_2_3 th 的 textContent 嚴格等於欄名；圖示 aria-hidden；沒有 aria-label；兩鍵欄", () => {
    const { container } = render(
      <table>
        <thead>
          <tr>
            <SortableHeader column="A" label="欄A" state={null} onSort={() => {}} />
            <SortableHeader column="aiModel" label="AI 模型" second={{ column: "tokenUsed", label: "Token" }} state={null} onSort={() => {}} />
          </tr>
        </thead>
      </table>,
    );
    const ths = screen.getAllByRole("columnheader");
    expect(ths[0].textContent).toBe("欄A");
    expect(ths[1].textContent).toBe("AI 模型 · Token");
    expect(ths[1].querySelectorAll("button")).toHaveLength(2);
    const svgs = container.querySelectorAll("th svg");
    expect(svgs.length).toBe(3);
    svgs.forEach((s) => expect(s.getAttribute("aria-hidden")).toBe("true"));
    container.querySelectorAll("th, th *").forEach((el) => expect(el.hasAttribute("aria-label")).toBe(false));
  });

  it("AT_963_2_4 不可排欄沒有 button、沒有 aria-sort", () => {
    render(<Table state={null} onSort={() => {}} />);
    const th = screen.getByRole("columnheader", { name: "操作" });
    expect(th.querySelector("button")).toBeNull();
    expect(th.hasAttribute("aria-sort")).toBe(false);
  });

  it("AT_963_2_E_1 受控連點：asc→desc→asc；點另一欄後前者回 none", async () => {
    function Controlled() {
      const [s, setS] = useState<SortState>(null);
      return <Table state={s} onSort={(k) => setS((p) => nextSort(p, k))} />;
    }
    render(<Controlled />);
    await userEvent.click(screen.getByRole("button", { name: "欄A" }));
    expect(sorts().slice(0, 3)).toEqual(["ascending", "none", "none"]);
    await userEvent.click(screen.getByRole("button", { name: "欄A" }));
    expect(sorts().slice(0, 3)).toEqual(["descending", "none", "none"]);
    await userEvent.click(screen.getByRole("button", { name: "欄A" }));
    expect(sorts().slice(0, 3)).toEqual(["ascending", "none", "none"]);
    await userEvent.click(screen.getByRole("button", { name: "欄B" }));
    expect(sorts().slice(0, 3)).toEqual(["none", "ascending", "none"]);
  });
});
