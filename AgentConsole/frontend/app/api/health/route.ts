/**
 * 前端健康檢查（API-HLT-03；PRD §11.3）：Docker HEALTHCHECK 與 compose 用。
 * 不依賴後端，只回「這個 Next 行程活著」。
 */
export const dynamic = "force-static";

export function GET() {
  return Response.json({ status: "ok" });
}
