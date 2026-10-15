import { expect, test } from "@playwright/test";

import { API_URL } from "./helpers";
import { E2E_ROOT, NEEDS_BRIDGE, call, dataOf, ensureQuota, tokenOf } from "./realBackend";

/**
 * 契約 §0.4（CORS 暴露標頭、限流）與 E2E-11 的瀏覽器面：前端（origin 3000）跨來源呼叫後端（18080）時，
 * JavaScript 要能讀到 Retry-After 與 X-Trace-Id（Access-Control-Expose-Headers；契約只要求暴露 X-Follow-Up-Run-Id／Retry-After／Content-Disposition，
 * 另有 X-Trace-Id；X-RateLimit-* 沒有暴露，見 QA 報告 §11 觀察 O-01），而且超限的請求先得 429（早於授權判定）。
 * 本檔把 viewer 的額度打滿，所以放在 p 系列最後，結束前等視窗回滿，避免影響後面的 spec。
 */
test.skip(!E2E_ROOT, NEEDS_BRIDGE);

test.describe("跨來源標頭與限流（瀏覽器內 fetch）", () => {
  test.setTimeout(240_000);

  test("429 的 Retry-After 與 X-Trace-Id 在瀏覽器內可讀（X-RateLimit-* 契約未要求暴露）；超限先得 429 而不是 403；伺服器端 429 帶 X-RateLimit-Limit／Remaining；operator 不受影響", async ({ page, request }) => {
    await ensureQuota(request, "viewer", 95); // 視窗要夠新：後面要把 viewer 的 100 次打滿
    await page.goto("/login");
    const viewerToken = await tokenOf(request, "viewer");
    const seen = await page.evaluate(
      async ({ api, token }) => {
        let last: Response | null = null;
        for (let i = 0; i < 130; i += 1) {
          last = await fetch(`${api}/api/v1/projects?size=1`, { headers: { Authorization: `Bearer ${token}` } });
          if (last.status === 429) break;
        }
        const res = last as Response;
        // 超限者做「寫入」：viewer 本來是 403，限流 filter 在授權判定之前，所以先得 429
        const write = await fetch(`${api}/api/v1/import/text`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
          body: JSON.stringify({ content: "x" }),
        });
        return {
          status: res.status,
          retryAfter: res.headers.get("retry-after"),
          traceId: res.headers.get("x-trace-id"),
          // 契約 §0.4 第 3 點只要求暴露 X-Follow-Up-Run-Id／Retry-After／Content-Disposition（另有 X-Trace-Id）；X-RateLimit-* 沒有暴露（見 QA 報告 §11 觀察 O-01）
          limitReadable: res.headers.get("x-ratelimit-limit") !== null,
          body: (await res.json()) as { reason?: string; code?: number; traceId?: string; details?: { retryAfterSeconds?: number } },
          writeStatus: write.status,
        };
      },
      { api: API_URL, token: viewerToken },
    );
    expect(seen.status).toBe(429);
    expect(Number(seen.retryAfter), "Retry-After 在瀏覽器內必須可讀（Access-Control-Expose-Headers）").toBeGreaterThanOrEqual(1);
    expect(Number(seen.retryAfter)).toBeLessThanOrEqual(60);
    expect(seen.traceId, "X-Trace-Id 可讀（錯誤封包的 traceId 要等於它）").toBe(seen.body.traceId ?? "");
    expect(seen.body).toMatchObject({ code: 429, reason: "超過每分鐘 100 次請求上限" });
    expect(seen.body.details?.retryAfterSeconds).toBe(Number(seen.retryAfter));
    expect(seen.writeStatus, "超限者先得 429（早於授權）").toBe(429);
    // 伺服器端（Node，看得到全部標頭）：429 帶 X-RateLimit-Limit＝100、Remaining＝0
    const limited = await call(request, "viewer", "GET", "/api/v1/projects?size=1");
    expect(limited.status).toBe(429);
    expect([limited.headers["x-ratelimit-limit"], limited.headers["x-ratelimit-remaining"]]).toEqual(["100", "0"]);
    expect(Number(limited.headers["retry-after"])).toBeGreaterThanOrEqual(1);
    // 同一時間 operator（另一個使用者）不受影響；被限流的 viewer 打 /actuator/health 仍 200（不計入）
    expect((await call(request, "operator", "GET", "/api/v1/projects?size=1")).status).toBe(200);
    const health = await request.fetch(`${API_URL}/actuator/health`, { failOnStatusCode: false });
    expect(health.status()).toBe(200);
    // 等 Retry-After 秒後 viewer 再請求 → 200（契約 E2E-11 步驟 5）
    await new Promise((r) => setTimeout(r, (Number(seen.retryAfter) + 1) * 1000));
    const back = await call(request, "viewer", "GET", "/api/v1/projects?size=1");
    expect(back.status).toBe(200);
    expect(dataOf<{ totalElements: number }>(back).totalElements).toBeGreaterThanOrEqual(0);
  });
});
