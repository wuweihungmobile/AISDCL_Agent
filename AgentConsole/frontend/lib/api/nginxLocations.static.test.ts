import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

/**
 * nginx location 與前端精確路徑的碰撞鎖（DEF-AC-034；`docker/nginx/conf.d/console-locations.inc`）：
 * 前綴 location 以「/」結尾且掛 proxy_pass 時，nginx 對「URI 等於該字串但少了尾斜線」的請求回 301 轉址到帶尾斜線的路徑，
 * 而 Spring 6 起不再把 `/x/` 對映到 `/x` ⇒ 經 nginx 的那個精確路徑一律 404（直連後端 200；2026-11-09 真機探針：`GET /api/v1/import`）。
 * 判準：每個尾斜線前綴 location 去掉尾斜線後的路徑，若被 `lib/api` 當精確路徑呼叫，就必須另有 `location = <該路徑>`。
 * 掃描器是純函式，附負控樣本；前端與 nginx 兩邊任一側新增碰撞即紅。
 */
const ROOT = process.cwd();
const NGINX_INC = path.join(ROOT, "..", "docker", "nginx", "conf.d", "console-locations.inc");
const API_DIR = path.join(ROOT, "lib", "api");

/** 純函式：抽出前綴 location（只取以「/」結尾者，`location /` 本身除外）與精確比對 location（`=`）；正規式 location（`~`）不在射程。 */
export function parseLocations(source: string): { slashPrefixes: string[]; exact: string[] } {
  const slashPrefixes: string[] = [];
  const exact: string[] = [];
  for (const line of source.split(/\r?\n/)) {
    const prefix = /^\s*location\s+(\/[^\s{=~]*\/)\s*\{/.exec(line);
    if (prefix && prefix[1] !== "/") slashPrefixes.push(prefix[1]);
    const eq = /^\s*location\s*=\s*(\/[^\s{]*)\s*\{/.exec(line);
    if (eq) exact.push(eq[1]);
  }
  return { slashPrefixes, exact };
}

/** 純函式：原始碼中以字串字面寫出的精確 API 路徑（排除含 `${…}` 的樣板字串與帶 query 的寫法）。 */
export function exactApiPaths(source: string): Set<string> {
  const out = new Set<string>();
  for (const m of source.matchAll(/["'`](\/api\/v1\/[^"'`\s?]*)["'`]/g)) {
    if (!m[1].includes("${")) out.add(m[1]);
  }
  return out;
}

/** 純函式：回傳「被當精確路徑呼叫、卻只有尾斜線前綴 location 而沒有 = location」的路徑。 */
export function collisions(nginxSource: string, apiPaths: Set<string>): string[] {
  const { slashPrefixes, exact } = parseLocations(nginxSource);
  const exactSet = new Set(exact);
  return slashPrefixes.map((p) => p.replace(/\/$/, "")).filter((base) => apiPaths.has(base) && !exactSet.has(base));
}

function apiSources(): string {
  if (!existsSync(API_DIR)) return "";
  return readdirSync(API_DIR)
    .filter((name) => /\.ts$/.test(name) && !/\.test\.ts$/.test(name) && !/\.d\.ts$/.test(name))
    .map((name) => readFileSync(path.join(API_DIR, name), "utf-8"))
    .join("\n");
}

describe("DEF-AC-034 nginx 尾斜線前綴 location 不得與前端精確路徑碰撞", () => {
  it("DEF_AC_034_1 console-locations.inc 的每個尾斜線前綴，去尾斜線後若被 lib/api 精確呼叫就必須另有 = location", () => {
    const nginx = readFileSync(NGINX_INC, "utf-8");
    const paths = exactApiPaths(apiSources());
    const { slashPrefixes } = parseLocations(nginx);
    expect(slashPrefixes.length, "防反空轉：nginx 檔要真的有尾斜線前綴 location").toBeGreaterThanOrEqual(3);
    expect(paths.size, "防反空轉：lib/api 要真的有精確路徑").toBeGreaterThanOrEqual(10);
    expect(collisions(nginx, paths), "碰撞路徑（經 nginx 會 301→帶尾斜線→Spring 404）").toEqual([]);
  });

  it("DEF_AC_034_2 匯入歷史清單 GET /api/v1/import 的 = location 在，且前端仍以精確路徑呼叫它", () => {
    const { exact, slashPrefixes } = parseLocations(readFileSync(NGINX_INC, "utf-8"));
    expect(exact).toContain("/api/v1/import");
    expect(slashPrefixes).toContain("/api/v1/import/");
    expect(exactApiPaths(apiSources()).has("/api/v1/import")).toBe(true);
  });

  it("DEF_AC_034_3 負控：解析器只收尾斜線前綴與 = location，排除 location /、正規式 location 與含 ${} 的樣板字串", () => {
    const sample = ["location / {", "location /api/v1/x/ {", "location = /api/v1/x {", "location ~ ^/y/ {", "location /api/v1/y/ {", "location /z {"].join("\n");
    expect(parseLocations(sample)).toEqual({ slashPrefixes: ["/api/v1/x/", "/api/v1/y/"], exact: ["/api/v1/x"] });
    const src = 'apiRequest("/api/v1/x", {}); apiRequest(`/api/v1/y/${id}`); apiRequest("/api/v1/y?page=0"); fetch(`/api/v1/z`)';
    expect([...exactApiPaths(src)].sort()).toEqual(["/api/v1/x", "/api/v1/z"]);
    expect(collisions(sample, exactApiPaths(src))).toEqual([]);
    expect(collisions(sample, new Set(["/api/v1/y"]))).toEqual(["/api/v1/y"]);
  });
});
