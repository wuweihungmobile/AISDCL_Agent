// 由後端 OpenAPI 產生 TypeScript 型別（lib/api/schema.d.ts，入庫；建置不依賴後端在線）。
// 用法（跨平台，不用 shell 環境變數前綴）：
//   node scripts/gen-api.mjs [OpenAPI 位址]
//   位址預設 http://localhost:8080/v3/api-docs，也可由環境變數 OPENAPI_URL 提供（參數優先）。
import { writeFileSync } from "node:fs";
import { resolve } from "node:path";
import openapiTS, { astToString } from "openapi-typescript";

const url = process.argv[2] ?? process.env.OPENAPI_URL ?? "http://localhost:8080/v3/api-docs";
const out = resolve(import.meta.dirname, "..", "lib", "api", "schema.d.ts");

const ast = await openapiTS(new URL(url));
const banner =
  "/**\n" +
  " * 由 scripts/gen-api.mjs 依後端 /v3/api-docs 自動產生（openapi-typescript），請勿手改。\n" +
  " * 重新產生：npm run gen:api（後端需在線；位址見 scripts/gen-api.mjs）。\n" +
  " */\n\n";
writeFileSync(out, banner + astToString(ast), { encoding: "utf-8" });
console.log(`已產生 ${out}（來源 ${url}）`);
