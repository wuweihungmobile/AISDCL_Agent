#!/usr/bin/env bash
# docker/minio/init-bucket.sh — 建立離站備份 bucket 與專用帳號（minio-init 一次性 job；ADR-001 D14-4）
#
# 在 pgsty/mc 映像內執行（compose：entrypoint bash /opt/minio/init-bucket.sh）。冪等：重跑不報錯。
#   1. 以 MinIO root 帳號連線（自簽憑證 ⇒ --insecure）
#   2. 建立 bucket S3_BUCKET（PRD §12.3.2：aisdlc-db-backup）
#   3. 建立只能存取該 bucket 的專用使用者 S3_ACCESS_KEY／S3_SECRET_KEY
#      （pgBackRest 的 repo2-s3-key 與 pg_dump-offsite.sh 都用這組，不用 root 金鑰）
#   4. 以專用帳號實際讀寫一次，確認權限真的對
set -euo pipefail

: "${MINIO_ENDPOINT:=https://minio:9000}"
: "${MINIO_ROOT_USER:?MINIO_ROOT_USER is required}"
: "${MINIO_ROOT_PASSWORD:?MINIO_ROOT_PASSWORD is required}"
: "${S3_BUCKET:?S3_BUCKET is required}"
: "${S3_ACCESS_KEY:?S3_ACCESS_KEY is required}"
: "${S3_SECRET_KEY:?S3_SECRET_KEY is required}"

export MC_CONFIG_DIR=/tmp/.mc
mc_cmd=(mc --insecure)
policy_name="aisdlc-backup"
policy_file="/tmp/${policy_name}-policy.json"

connected=0
for _ in $(seq 1 30); do
  if "${mc_cmd[@]}" alias set local "$MINIO_ENDPOINT" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" > /dev/null 2>&1; then
    connected=1
    break
  fi
  sleep 2
done
if [ "$connected" != "1" ]; then
  echo "init-bucket: 無法以 root 帳號連到 ${MINIO_ENDPOINT}" >&2
  exit 1
fi

"${mc_cmd[@]}" mb --ignore-existing "local/${S3_BUCKET}"

cat > "$policy_file" <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:*"],
      "Resource": ["arn:aws:s3:::${S3_BUCKET}", "arn:aws:s3:::${S3_BUCKET}/*"]
    }
  ]
}
JSON

# policy create／user add 對已存在的名稱是更新（覆寫），所以可重複執行
"${mc_cmd[@]}" admin policy create local "$policy_name" "$policy_file"
"${mc_cmd[@]}" admin user add local "$S3_ACCESS_KEY" "$S3_SECRET_KEY"
user_info="$("${mc_cmd[@]}" admin user info local "$S3_ACCESS_KEY")"
if [[ "$user_info" != *"$policy_name"* ]]; then
  "${mc_cmd[@]}" admin policy attach local "$policy_name" --user "$S3_ACCESS_KEY"
fi
rm -f "$policy_file"

# 以專用帳號驗證：寫、讀、刪一個探針物件
"${mc_cmd[@]}" alias set backupuser "$MINIO_ENDPOINT" "$S3_ACCESS_KEY" "$S3_SECRET_KEY" > /dev/null
probe="init-probe-$(date +%s)"
echo "ok" | "${mc_cmd[@]}" pipe "backupuser/${S3_BUCKET}/${probe}" > /dev/null
"${mc_cmd[@]}" cat "backupuser/${S3_BUCKET}/${probe}" > /dev/null
"${mc_cmd[@]}" rm "backupuser/${S3_BUCKET}/${probe}" > /dev/null

echo "init-bucket: bucket ${S3_BUCKET} 與專用帳號 ${S3_ACCESS_KEY} 就緒（已實際寫入／讀取／刪除驗證）"
