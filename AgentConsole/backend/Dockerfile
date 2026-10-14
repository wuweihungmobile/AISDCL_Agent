# backend/Dockerfile — PRD §11.4.2（多階段建置）；build context＝AgentConsole/backend
#
# 與 PRD 逐字版只有兩處差異，皆有實測理由（見 backend/README.md〈與 PRD 的差異〉）：
#   1. runner 階段加裝 curl：eclipse-temurin:21-jre-alpine 沒有 curl（實測 `which curl` rc=1），
#      PRD 的 HEALTHCHECK 以 curl 呼叫 /actuator/health，沒有 curl 會讓容器永遠 unhealthy。
#   2. runner 階段加 LOGGING_STRUCTURED_FORMAT_CONSOLE：容器內輸出結構化 JSON 日誌（PRD §9.4、NFR-9.4-04），
#      每行含 traceId。本機 bootRun 不受影響（維持人類可讀格式）。

# ── Stage 1: Build ──
FROM eclipse-temurin:21-jdk-alpine AS builder
WORKDIR /app

COPY gradlew .
COPY gradle gradle
COPY build.gradle.kts settings.gradle.kts ./
RUN chmod +x gradlew && ./gradlew dependencies --no-daemon

COPY src src
RUN ./gradlew bootJar --no-daemon -x test

# ── Stage 2: Production ──
FROM eclipse-temurin:21-jre-alpine AS runner
WORKDIR /app

RUN apk add --no-cache curl

RUN addgroup --system --gid 1001 spring && \
    adduser --system --uid 1001 spring

COPY --from=builder /app/build/libs/*.jar app.jar

RUN mkdir -p /app/logs && chown spring:spring /app/logs

USER spring
EXPOSE 8080

ENV JAVA_OPTS="-XX:+UseZGC \
  -XX:MaxRAMPercentage=75.0 \
  -XX:+UseStringDeduplication \
  -Djava.security.egd=file:/dev/./urandom"
ENV LOGGING_STRUCTURED_FORMAT_CONSOLE=logstash

HEALTHCHECK --interval=30s --timeout=10s --retries=5 --start-period=60s \
  CMD curl -f http://localhost:8080/actuator/health || exit 1

ENTRYPOINT ["sh", "-c", "java ${JAVA_OPTS} -jar app.jar"]
