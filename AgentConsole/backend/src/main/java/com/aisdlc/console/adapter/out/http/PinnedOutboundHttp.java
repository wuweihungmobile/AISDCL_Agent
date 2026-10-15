package com.aisdlc.console.adapter.out.http;

import com.aisdlc.console.application.port.out.OutboundHttp;
import com.aisdlc.console.domain.service.OutboundUrlPolicy;
import com.aisdlc.console.domain.service.OutboundUrlPolicy.HostResolver;
import com.aisdlc.console.domain.service.OutboundUrlPolicy.Target;
import org.apache.hc.client5.http.ConnectTimeoutException;
import org.apache.hc.client5.http.DnsResolver;
import org.apache.hc.client5.http.classic.methods.HttpPost;
import org.apache.hc.client5.http.config.ConnectionConfig;
import org.apache.hc.client5.http.config.RequestConfig;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.client5.http.impl.io.PoolingHttpClientConnectionManager;
import org.apache.hc.client5.http.impl.io.PoolingHttpClientConnectionManagerBuilder;
import org.apache.hc.core5.http.ContentType;
import org.apache.hc.core5.http.HttpEntity;
import org.apache.hc.core5.http.io.entity.StringEntity;
import org.apache.hc.core5.util.Timeout;
import org.springframework.stereotype.Component;

import javax.net.ssl.SSLException;
import java.io.IOException;
import java.io.InputStream;
import java.net.ConnectException;
import java.net.InetAddress;
import java.net.NoRouteToHostException;
import java.net.SocketTimeoutException;
import java.net.UnknownHostException;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * {@link OutboundHttp} 的 Apache HttpClient 5 實作（NFR-SEC-04；契約 §1.5.7「連線實作」、AR-10）。
 *
 * <p>為什麼不用 JDK {@code HttpClient}：它沒有 DNS resolver 注入點、{@code Host} 是受限標頭、改用 IP 字面 URL 又會讓
 * TLS 驗證對到 IP 而不是原 host——做不到「連線釘死在已驗證的 IP」。這裡的流程：
 * <ol>
 *   <li>{@link OutboundUrlPolicy#checkStatic}（規則 1～5）；</li>
 *   <li>名稱 host 只解析<b>一次</b>，{@link OutboundUrlPolicy#checkResolved} 驗全部 A／AAAA（規則 6：dns_rebinding）；</li>
 *   <li>以自訂 {@link DnsResolver} 把「這個 host」釘在剛驗過的位址上（沒有第二次 DNS 查詢，所以沒有解析競態）；
 *       請求 URI 保留原 host，所以 {@code Host} 標頭與 TLS SNI／主機名驗證都用原 host；</li>
 *   <li>關閉自動重導與重試：3xx 原樣回給呼叫端（不會被導向內網）。</li>
 * </ol>
 * 外呼量很低（測試連線、匯入解析），所以每次呼叫建一個專用的連線管理員與用戶端，用完即關。
 */
@Component
class PinnedOutboundHttp implements OutboundHttp {

    private static final int MAX_RESPONSE_BYTES = 4 * 1024 * 1024;

    private final OutboundUrlPolicy policy;
    private final HostResolver resolver;

    PinnedOutboundHttp(OutboundUrlPolicy policy, HostResolver resolver) {
        this.policy = policy;
        this.resolver = resolver;
    }

    @Override
    public HttpResult postJson(String url, Map<String, String> headers, String jsonBody, Duration connectTimeout,
                               Duration totalTimeout) {
        Target target = policy.checkStatic(url);
        List<InetAddress> addresses = resolve(target);
        policy.checkResolved(target, addresses);

        Timeout connect = Timeout.ofMilliseconds(connectTimeout.toMillis());
        Timeout total = Timeout.ofMilliseconds(totalTimeout.toMillis());
        PoolingHttpClientConnectionManager connections = PoolingHttpClientConnectionManagerBuilder.create()
                .setDnsResolver(new PinnedDns(target.host(), addresses))
                .setDefaultConnectionConfig(ConnectionConfig.custom().setConnectTimeout(connect)
                        .setSocketTimeout(total).build())
                .build();
        RequestConfig requestConfig = RequestConfig.custom().setRedirectsEnabled(false)
                .setConnectionRequestTimeout(connect).setResponseTimeout(total).build();
        try (CloseableHttpClient client = HttpClients.custom().setConnectionManager(connections)
                .setDefaultRequestConfig(requestConfig).disableRedirectHandling().disableAutomaticRetries()
                .disableCookieManagement().build()) {
            HttpPost post = new HttpPost(url);
            headers.forEach(post::setHeader);
            post.setEntity(new StringEntity(jsonBody, ContentType.APPLICATION_JSON));
            long started = System.nanoTime();
            return client.execute(post, response -> new HttpResult(response.getCode(), read(response.getEntity()),
                    (System.nanoTime() - started) / 1_000_000L, target.host()));
        } catch (IOException e) {
            throw translate(e);
        }
    }

    private List<InetAddress> resolve(Target target) {
        if (target.isIpLiteral()) {
            return List.of(target.literal());
        }
        try {
            return resolver.resolve(target.host());
        } catch (UnknownHostException e) {
            throw new OutboundIoException(OutboundIoException.Kind.CONNECT, "無法解析主機");
        }
    }

    /** 失敗原因只給「簡短類別」：不含 URL（可能帶 query）、不含金鑰。 */
    private static OutboundIoException translate(IOException e) {
        if (e instanceof SocketTimeoutException || e instanceof ConnectTimeoutException
                || e instanceof java.io.InterruptedIOException) {
            return new OutboundIoException(OutboundIoException.Kind.TIMEOUT, "逾時");
        }
        if (e instanceof ConnectException || e instanceof NoRouteToHostException) {
            return new OutboundIoException(OutboundIoException.Kind.CONNECT, "拒絕連線");
        }
        if (e instanceof UnknownHostException) {
            return new OutboundIoException(OutboundIoException.Kind.CONNECT, "無法解析主機");
        }
        if (e instanceof SSLException) {
            return new OutboundIoException(OutboundIoException.Kind.OTHER, "TLS 握手失敗");
        }
        return new OutboundIoException(OutboundIoException.Kind.OTHER, e.getClass().getSimpleName());
    }

    private static String read(HttpEntity entity) throws IOException {
        if (entity == null) {
            return "";
        }
        try (InputStream in = entity.getContent()) {
            return new String(in.readNBytes(MAX_RESPONSE_BYTES), StandardCharsets.UTF_8);
        }
    }

    /** 只回答「這個 host」的已驗證位址；其他 host（不該出現，例如被重導）一律解析失敗。 */
    private static final class PinnedDns implements DnsResolver {

        private final String host;
        private final InetAddress[] addresses;

        PinnedDns(String host, List<InetAddress> addresses) {
            this.host = normalize(host);
            this.addresses = addresses.toArray(new InetAddress[0]);
        }

        @Override
        public InetAddress[] resolve(String requested) throws UnknownHostException {
            if (!host.equals(normalize(requested))) {
                throw new UnknownHostException("未經驗證的 host：" + requested);
            }
            return addresses.clone();
        }

        @Override
        public String resolveCanonicalHostname(String requested) {
            return requested;
        }

        private static String normalize(String value) {
            String v = value.toLowerCase(Locale.ROOT);
            return v.startsWith("[") && v.endsWith("]") ? v.substring(1, v.length() - 1) : v;
        }
    }
}
