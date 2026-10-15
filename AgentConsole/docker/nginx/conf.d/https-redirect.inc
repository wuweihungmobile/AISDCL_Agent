# docker/nginx/conf.d/https-redirect.inc — 啟用 HTTPS 後，80 埠的 server 區塊改 include 本檔（取代 console-locations.inc）
# 80 埠只做兩件事：
#   · /nginx-health：compose 的 nginx healthcheck 打 http://127.0.0.1/nginx-health（busybox wget），不能被轉址到 https
#   · 其餘一律 301 到 https（保留主機名稱與原始 URI；公開的 HTTPS 埠不是 443 時請自行改成 https://$host:<埠>$request_uri）
location = /nginx-health {
    access_log off;
    default_type text/plain;
    return 200 "ok\n";
}

location / {
    return 301 https://$host$request_uri;
}
