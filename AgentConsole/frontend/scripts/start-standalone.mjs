// 以 `output: "standalone"` 的產物啟動前端（跨平台，不依賴 shell 的 cp／env 前綴語法）：
//   node scripts/start-standalone.mjs        （PORT、HOSTNAME 由環境變數決定，預設 3000／0.0.0.0）
// standalone 不含 .next/static 與 public，官方做法是自行複製到 standalone 目錄旁；這裡一併做掉。
import { spawn } from "node:child_process";
import { cpSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const standalone = join(root, ".next", "standalone");
const server = join(standalone, "server.js");

if (!existsSync(server)) {
  console.error("找不到 .next/standalone/server.js，請先執行 npm run build");
  process.exit(1);
}
cpSync(join(root, ".next", "static"), join(standalone, ".next", "static"), { recursive: true });
if (existsSync(join(root, "public"))) {
  cpSync(join(root, "public"), join(standalone, "public"), { recursive: true });
}

const child = spawn(process.execPath, [server], {
  cwd: standalone,
  stdio: "inherit",
  env: { ...process.env, HOSTNAME: process.env.HOSTNAME ?? "0.0.0.0", PORT: process.env.PORT ?? "3000" },
});
// Windows 沒有 POSIX 信號：SIGINT／SIGBREAK 由 Node 轉成事件，terminate 用 child.kill()（portable）
for (const sig of ["SIGINT", "SIGTERM", "SIGBREAK"]) {
  process.on(sig, () => child.kill());
}
child.on("exit", (code) => process.exit(code ?? 0));
