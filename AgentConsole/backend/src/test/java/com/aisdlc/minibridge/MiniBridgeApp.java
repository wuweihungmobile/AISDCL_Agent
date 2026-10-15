package com.aisdlc.minibridge;

import org.springframework.boot.autoconfigure.ImportAutoConfiguration;
import org.springframework.boot.http.converter.autoconfigure.HttpMessageConvertersAutoConfiguration;
import org.springframework.boot.jackson.autoconfigure.JacksonAutoConfiguration;
import org.springframework.boot.tomcat.autoconfigure.servlet.TomcatServletWebServerAutoConfiguration;
import org.springframework.boot.webmvc.autoconfigure.DispatcherServletAutoConfiguration;
import org.springframework.boot.webmvc.autoconfigure.WebMvcAutoConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 迷你 Bridge 的 Spring Boot 應用：只裝配 Web（嵌入式 Tomcat、DispatcherServlet、MVC、Jackson 訊息轉換器），
 * 刻意<b>不</b>用 {@code @EnableAutoConfiguration}——classpath 上有 Security／JPA／Flyway／Actuator，全開會要求資料庫與認證。
 */
@Configuration(proxyBeanMethods = false)
@ImportAutoConfiguration({TomcatServletWebServerAutoConfiguration.class, DispatcherServletAutoConfiguration.class,
        WebMvcAutoConfiguration.class, HttpMessageConvertersAutoConfiguration.class, JacksonAutoConfiguration.class})
class MiniBridgeApp {

    @Bean
    MiniBridgeController miniBridgeController(MiniBridge bridge) {
        return new MiniBridgeController(bridge);
    }
}
