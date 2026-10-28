/**
 * 把畫面包進假後端用的 Provider 外殼（TanStack Query ＋ 登入狀態 ＋ Toast）。
 *
 * 為什麼獨立成 .tsx：`Providers` 的 `children` 是必填 prop，夾具檔（TCS §5.6 規定的檔名 `backup.fixtures.ts`，不能改成 .tsx）裡沒有 JSX，
 * 改用 `createElement` 會兩邊都撞——子節點放第三參數，TypeScript 認為少了必填的 `children`（TS2769）；子節點放進 props 物件，eslint 的 `react/no-children-prop` 擋下。
 * 用 JSX 傳子節點才是 React 認可的形態，所以這支小工具用 JSX，夾具檔保持 .ts。
 * 放在 `tests/` 子目錄：設計系統與靜態守衛掃原始碼時都略過名為 tests 的目錄。
 */
import type { QueryClient } from "@tanstack/react-query";
import type { ReactElement } from "react";

import { Providers } from "@/tests/helpers/api";

export function withProviders(ui: ReactElement, client: QueryClient): ReactElement {
  return <Providers client={client}>{ui}</Providers>;
}
