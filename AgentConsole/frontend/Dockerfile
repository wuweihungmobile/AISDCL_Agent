# frontend/Dockerfile —— PRD §11.4.1（build context＝AgentConsole/frontend）
# 與 PRD 逐字版本的差異（理由與驗證見 docs/02_architecture/ADR-002-Frontend-Design-System.md §Dockerfile）：
#  1. `npm ci` 不帶 --frozen-lockfile：那是 yarn 的旗標，npm ci 本來就嚴格依 package-lock.json。
#  2. HEALTHCHECK 改用 busybox wget：node:22-alpine 沒有 curl，PRD 的 curl 版會永遠 unhealthy；
#     位址用 127.0.0.1（alpine 的 localhost 可能先解析成 ::1，而 server 綁在 0.0.0.0）。
# 建置： docker build -t aisdlc-frontend:dev --build-arg NEXT_PUBLIC_API_URL=<後端 origin；全棧同源留空> .

# ── Stage 1: Dependencies ──
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# ── Stage 2: Build ──
FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# NEXT_PUBLIC_* 在 build 時內嵌進前端程式：語意＝後端 origin（不含 /api/v1），全棧經 nginx 同源時留空
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
RUN npm run build

# ── Stage 3: Production ──
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:3000/api/health || exit 1

CMD ["node", "server.js"]
