# docker/nginx/conf.d/console-locations.inc — Console 的全部 location（由 server 區塊 include）
#
# 為什麼獨立成檔：HTTP（80，default.conf）與 HTTPS（443，https.conf.example）兩個 server 必須有完全相同的路由，
# 抽成 include 才不會兩份各自漂移。副檔名刻意不是 .conf：nginx.conf 的 `include conf.d/*.conf` 在 http 層級載入，
# location 出現在那一層是語法錯誤；本檔只能放在 server 區塊內 include。
#
# 通則：proxy_set_header 不會從別的 location 繼承，每個 location 必須重複 Host／X-Real-IP／X-Forwarded-For／
# X-Forwarded-Proto；proxy_pass 不帶 URI，才會保留原始請求 URI（含 ?access_token=）。

# nginx 自身健康檢查（compose healthcheck 用）
location = /nginx-health {
    access_log off;
    default_type text/plain;
    return 200 "ok\n";
}

# Frontend (Next.js)
location / {
    proxy_pass http://frontend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_cache_bypass $http_upgrade;
}

# BRD/PRD 匯入（契約 §0.7 第 1 項）：10MB 檔案加 multipart 封裝 ≤ 11MB（nginx 預設只有 1m，10MB 上傳必被擋成 413）；
# 解析是同步呼叫，最長約 model.timeout＋15 秒，所以讀取逾時放寬到 180 秒（部署時建議 model.timeout ≤ 150）。
location /api/v1/import/ {
    client_max_body_size 11m;
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Connection '';
    proxy_read_timeout 180s;
}

# 設定檔匯入（契約 §0.7 第 2 項）：≤ 1MB 的 JSON 加 multipart 封裝
location = /api/v1/settings/import {
    client_max_body_size 2m;
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Connection '';
}

# SSE（契約 §0.7 第 3 項、§2.1）：/api/v1/stream/executions/{runId}/logs｜metrics，EventSource 以 ?access_token= 認證。
# proxy_buffering 一旦開著，框架會卡在 nginx 直到緩衝滿，前端就「收不到即時事件」；讀取逾時 3600 秒只是兜底
# （後端每 15 秒送一次 keep-alive 註解；斷線由前端用 Last-Event-ID 重連）。access log 的 token 遮罩在 nginx.conf 的 log_format；
# error_log 的 token 洩漏則靠 nginx.conf 把 error_log 降到 crit 擋住（契約 §0.7 第 5 項）。
location /api/v1/stream/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Connection '';
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 3600s;
}

# 前端自己的健康路由（QA O-08、契約 §0.7 第 6 項）：Next.js 的 /api/health 與後端的 /api/ 同前綴，
# 不能被下面的 /api/ 反代到 backend（它沒有這個路徑，會回 401）。精確比對（=）本來就優先於前綴比對，
# 放在 /api/ 之前只是讓讀的人一眼看懂順序。
location = /api/health {
    proxy_pass http://frontend;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Backend API
location /api/ {
    proxy_pass http://backend/api/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # SSE 支援
    proxy_set_header Connection '';
    proxy_buffering off;
    proxy_cache off;
    chunked_transfer_encoding off;
    proxy_read_timeout 86400s;
}

# Actuator (內部存取)
location /actuator/ {
    deny all;
}

# 靜態資源快取（QA O-09、契約 §0.7 第 6 項：Cache-Control 只留一份）：Next 對 /_next/static/ 自己也會回
# `Cache-Control: public, max-age=31536000, immutable`，nginx 再 add_header 一次就出現兩份。
# 作法：proxy_hide_header 丟掉上游那份，由 nginx 這份當唯一來源（檔名帶內容雜湊，immutable 安全）。
# add_header 刻意不加 always：只有 2xx／3xx 才會帶，404 不會被標成「一年內不必重驗」。
location /_next/static/ {
    proxy_pass http://frontend;
    proxy_cache_valid 200 365d;
    proxy_hide_header Cache-Control;
    add_header Cache-Control "public, max-age=31536000, immutable";
}
