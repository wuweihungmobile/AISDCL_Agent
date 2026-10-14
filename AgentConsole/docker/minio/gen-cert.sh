#!/usr/bin/env bash
# docker/minio/gen-cert.sh — 為本機 MinIO 產生自簽 TLS 憑證（minio-certs 一次性 job；ADR-001 D14-4）
#
# 為什麼需要：pgBackRest 的 S3 連線一律走 HTTPS（沒有明文模式），MinIO 沒有憑證就只講 HTTP。
# pgBackRest 以 repo2-storage-verify-tls=n 連線（不驗憑證），mc 以 --insecure；
# 真正的 S3（PGBACKREST_S3_ENDPOINT=s3.amazonaws.com）不使用這張憑證。
#
# 冪等：憑證與私鑰都已存在就什麼都不做（不覆寫，避免 MinIO 重啟前後憑證不同）。
# 在 aisdlc-pgbackrest 映像內執行（該映像有 openssl）；輸出到 CERT_DIR（預設 /certs，MinIO 的 --certs-dir）。
set -euo pipefail

dir="${CERT_DIR:-/certs}"
mkdir -p "$dir"

if [ -s "${dir}/public.crt" ] && [ -s "${dir}/private.key" ]; then
  echo "gen-cert: 憑證已存在，略過（${dir}/public.crt）"
  exit 0
fi

openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -days 3650 \
  -keyout "${dir}/private.key" -out "${dir}/public.crt" \
  -subj "/CN=minio" \
  -addext "subjectAltName=DNS:minio,DNS:localhost,IP:127.0.0.1"
chmod 0600 "${dir}/private.key"
chmod 0644 "${dir}/public.crt"
echo "gen-cert: 已產生自簽憑證 ${dir}/public.crt（SAN: minio, localhost, 127.0.0.1；有效 10 年）"
