package com.aisdlc.console.adapter.out.bridge;

import org.springframework.http.client.ClientHttpRequestFactory;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.stereotype.Component;

import java.net.http.HttpClient;
import java.time.Duration;

/**
 * 正式環境的請求工廠：JDK {@link HttpClient}（強制 HTTP/1.1——uvicorn 不需要 h2c 升級握手）。
 * 每次呼叫建一個新的（Bridge 呼叫量很低；逾時各自獨立）。
 */
@Component
class JdkRequestFactoryProvider implements RequestFactoryProvider {

    @Override
    public ClientHttpRequestFactory create(Duration connectTimeout, Duration readTimeout) {
        HttpClient client = HttpClient.newBuilder().version(HttpClient.Version.HTTP_1_1)
                .connectTimeout(connectTimeout).build();
        JdkClientHttpRequestFactory factory = new JdkClientHttpRequestFactory(client);
        factory.setReadTimeout(readTimeout);
        return factory;
    }
}
