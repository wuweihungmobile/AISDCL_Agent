package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.service.OutboundUrlPolicy.AddressClass;
import com.aisdlc.console.domain.service.OutboundUrlPolicy.Rejected;
import com.aisdlc.console.domain.service.OutboundUrlPolicy.Target;
import com.aisdlc.console.domain.service.OutboundUrlPolicy.Violation;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;

import java.net.InetAddress;
import java.net.UnknownHostException;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * SSRF／allowlist 政策（NFR-SEC-04；契約 §1.5.7 規則 1～6）。為什麼重要：這是「使用者可設定的 URL」唯一的出站防線——
 * 十進位／十六進位／八進位／縮寫的 IP 寫法、userinfo、IDN、DNS rebinding、loopback 旗標的誤開，任何一個漏掉都是 SSRF 洞。
 */
class OutboundUrlPolicyTest {

    /** production／docker：loopback 不放行（即使字面誤列在 allowlist 內，D-47）。 */
    private final OutboundUrlPolicy production = new OutboundUrlPolicy(
            List.of("api.minimax.io", "api.minimax.chat", "127.0.0.1", "localhost", "10.0.0.5"), false);

    /** e2e／test：allow-loopback＝true，allowlist 內的 127.0.0.1／localhost 放行。 */
    private final OutboundUrlPolicy e2e = new OutboundUrlPolicy(
            List.of("api.minimax.io", "127.0.0.1", "localhost", "rebind.e2e.test"), true);

    private static Violation violationOf(OutboundUrlPolicy policy, String url) {
        return catchThrowableOfType(Rejected.class, () -> policy.checkStatic(url)).violation();
    }

    private static <T extends Throwable> T catchThrowableOfType(Class<T> type, Runnable action) {
        try {
            action.run();
        } catch (Throwable t) {
            if (type.isInstance(t)) {
                return type.cast(t);
            }
            throw new AssertionError("預期 " + type.getSimpleName() + "，實際是 " + t, t);
        }
        throw new AssertionError("預期丟出 " + type.getSimpleName() + "，但沒有例外");
    }

    private static InetAddress ip(String literal) {
        try {
            return InetAddress.getByName(literal);
        } catch (UnknownHostException e) {
            throw new IllegalArgumentException(e);
        }
    }

    // ── 規則 1：malformed_url ────────────────────────────────────────────────

    @ParameterizedTest(name = "{0} → malformed_url")
    @ValueSource(strings = {
            "", "not a url", "example.com", "http://", "http://:8080", "http:///path", "file:///etc/passwd",
            "http://0x7f.0.0.1", "http://0X7F.0.0.1/", "http://2130706433", "http://127.1", "http://127.0.1",
            "http://0177.0.0.1", "http://127.0.0.01", "http://1.2.3.4.5", "http://256.1.1.1", "http://1.2.3",
            "http://exämple.com/v1", "http://例え.jp/", "http://api.minimax.io:99999/", "http://api.minimax.io:0/",
            "http://api.minimax.io:/", "http://api.minimax.io:80a/", "http://api.minimax.io\\@evil.example/",
            "http://api.minimax.io/a b", "http://api.minimax.io/\n", "http://host:80:90/", "http://[::1/",
            "http://[zzz]/", "http://[::1]x/", "http://-bad.example/", "http://bad-.example/", "http://a..b/"})
    void nonStandardOrBrokenUrlsAreMalformed(String url) {
        assertThat(violationOf(e2e, url)).isEqualTo(Violation.MALFORMED_URL);
    }

    @Test
    void aNullUrlIsMalformedAndNeverLeaksAHost() {
        Rejected rejected = catchThrowableOfType(Rejected.class, () -> e2e.checkStatic(null));
        assertThat(rejected.violation()).isEqualTo(Violation.MALFORMED_URL);
        assertThat(rejected.host()).isNull();
        assertThat(rejected.details()).containsOnlyKeys("violation").containsEntry("violation", "malformed_url");
    }

    // ── 規則 2、3：scheme、userinfo ───────────────────────────────────────────

    @ParameterizedTest(name = "{0} → scheme")
    @ValueSource(strings = {"ftp://api.minimax.io/v1", "gopher://api.minimax.io/", "ws://api.minimax.io/",
            "FTP://api.minimax.io/"})
    void onlyHttpAndHttpsAreAllowed(String url) {
        assertThat(violationOf(e2e, url)).isEqualTo(Violation.SCHEME);
    }

    @ParameterizedTest(name = "{0} → userinfo")
    @ValueSource(strings = {
            "http://user:your_password_here@api.minimax.io/v1/text/chatcompletion_v2",
            "https://user@api.minimax.io/", "http://:pw@api.minimax.io/", "http://a@b@api.minimax.io/"})
    void userinfoIsAlwaysRefusedAndNeverReportedBack(String url) {
        Rejected rejected = catchThrowableOfType(Rejected.class, () -> e2e.checkStatic(url));
        assertThat(rejected.violation()).isEqualTo(Violation.USERINFO);
        assertThat(rejected.host()).isEqualTo("api.minimax.io");
        assertThat(rejected.details().toString()).doesNotContain("your_password_here").doesNotContain("pw");
    }

    // ── 規則 4：IP 字面分類 ──────────────────────────────────────────────────

    @ParameterizedTest(name = "{0} → {1}")
    @CsvSource(delimiter = '|', value = {
            "http://10.0.0.5:8080|private_ip", "http://192.168.1.1|private_ip", "http://172.16.0.9|private_ip",
            "http://172.31.255.255|private_ip", "http://100.64.0.1|private_ip", "http://0.0.0.0|private_ip",
            "http://198.18.0.1|private_ip", "http://224.0.0.1|private_ip", "http://255.255.255.255|private_ip",
            "http://169.254.169.254/latest/meta-data|link_local", "http://169.254.0.1|link_local",
            "http://[fe80::1]/|link_local", "http://[fd00::1]/|private_ip", "http://[fc00::1]/|private_ip",
            "http://[::]/|private_ip", "http://[ff02::1]/|private_ip", "http://[::ffff:10.0.0.5]/|private_ip",
            "http://[::ffff:169.254.169.254]/|link_local",
            "http://[::1]:8080|loopback", "http://127.0.0.3:9|loopback", "http://127.255.255.254|loopback"})
    void ipLiteralsInPrivateLinkLocalOrUnlistedLoopbackRangesAreRefused(String url, String expected) {
        assertThat(violationOf(e2e, url).code()).isEqualTo(expected);
    }

    @Test
    void anIpv4MappedLoopbackLiteralIsClassifiedByItsEmbeddedIpv4Address() {
        assertThat(violationOf(production, "http://[::ffff:127.0.0.1]/")).isEqualTo(Violation.LOOPBACK);
        assertThat(violationOf(production, "http://[::ffff:10.0.0.5]/")).isEqualTo(Violation.PRIVATE_IP);
    }

    @Test
    void privateAndLinkLocalAreRefusedEvenWhenTheLiteralIsListedInTheAllowlistInAnyProfile() {
        // production 的 allowlist 含 10.0.0.5：仍然 private_ip（沒有任何旗標能放行私網）
        assertThat(violationOf(production, "http://10.0.0.5/")).isEqualTo(Violation.PRIVATE_IP);
        OutboundUrlPolicy listedEverywhere = new OutboundUrlPolicy(
                List.of("10.0.0.5", "169.254.169.254", "192.168.1.1"), true);
        assertThat(violationOf(listedEverywhere, "http://10.0.0.5/")).isEqualTo(Violation.PRIVATE_IP);
        assertThat(violationOf(listedEverywhere, "http://169.254.169.254/")).isEqualTo(Violation.LINK_LOCAL);
        assertThat(violationOf(listedEverywhere, "http://192.168.1.1/")).isEqualTo(Violation.PRIVATE_IP);
    }

    @Test
    void loopbackIsOnlyAllowedWhenTheFlagIsOnAndTheLiteralIsListed() {
        // 旗標關：即使 127.0.0.1 在 allowlist 內也拒絕
        assertThat(violationOf(production, "http://127.0.0.1:9/v1")).isEqualTo(Violation.LOOPBACK);
        assertThat(violationOf(production, "http://[::1]:8080")).isEqualTo(Violation.LOOPBACK);
        // 旗標開、字面在 allowlist 內：放行
        Target target = e2e.checkStatic("http://127.0.0.1:9/v1/chat/completions");
        assertThat(target.host()).isEqualTo("127.0.0.1");
        assertThat(target.port()).isEqualTo(9);
        assertThat(target.isIpLiteral()).isTrue();
        // 旗標開但字面不在 allowlist 內（::1、127.0.0.2）：仍然 loopback
        assertThat(violationOf(e2e, "http://[::1]:8080")).isEqualTo(Violation.LOOPBACK);
        assertThat(violationOf(e2e, "http://127.0.0.2/")).isEqualTo(Violation.LOOPBACK);
    }

    @Test
    void anIpv6LiteralInTheAllowlistMatchesByAddressRegardlessOfNotation() {
        OutboundUrlPolicy policy = new OutboundUrlPolicy(List.of("[::1]"), true);
        assertThat(policy.checkStatic("http://[0:0:0:0:0:0:0:1]:9/x").host()).isEqualTo("0:0:0:0:0:0:0:1");
        assertThat(policy.checkStatic("http://[::1]:9/x").isIpLiteral()).isTrue();
    }

    @Test
    void aPublicIpLiteralMustBeListedInTheAllowlistToo() {
        assertThat(violationOf(e2e, "http://8.8.8.8/")).isEqualTo(Violation.NOT_IN_ALLOWLIST);
        OutboundUrlPolicy listed = new OutboundUrlPolicy(List.of("8.8.8.8"), false);
        assertThat(listed.checkStatic("https://8.8.8.8/v1").isIpLiteral()).isTrue();
    }

    // ── 規則 5：allowlist ────────────────────────────────────────────────────

    @ParameterizedTest(name = "{0} → not_in_allowlist")
    @ValueSource(strings = {"https://example.com", "http://localhost.evil.example", "https://api.minimax.io.evil.com/",
            "https://evil.api.minimax.io/", "https://minimax.io/"})
    void hostsOutsideTheAllowlistAreRefusedByExactMatchNotBySuffix(String url) {
        assertThat(violationOf(e2e, url)).isEqualTo(Violation.NOT_IN_ALLOWLIST);
    }

    @Test
    void theAllowlistMatchIsCaseInsensitiveAndIgnoresATrailingDot() {
        for (String url : List.of("HTTPS://API.MINIMAX.IO/v1/text/chatcompletion_v2", "https://api.minimax.io./v1",
                "https://Api.Minimax.Io:443/x")) {
            Target target = e2e.checkStatic(url);
            assertThat(target.host()).isEqualTo("api.minimax.io");
            assertThat(target.scheme()).isIn("http", "https");
        }
        assertThat(e2e.checkStatic("https://api.minimax.io/x").effectivePort()).isEqualTo(443);
        assertThat(e2e.checkStatic("http://localhost/x").effectivePort()).isEqualTo(80);
        assertThat(e2e.checkStatic("http://localhost:8123/x").effectivePort()).isEqualTo(8123);
    }

    @Test
    void theDefaultMiniMaxEndpointPassesTheStaticChecks() {
        Target target = new OutboundUrlPolicy(List.of("api.minimax.io", "api.minimax.chat"), false)
                .checkStatic("https://api.minimax.io/v1/text/chatcompletion_v2");
        assertThat(target.host()).isEqualTo("api.minimax.io");
        assertThat(target.isIpLiteral()).isFalse();
        assertThat(target.url()).isEqualTo("https://api.minimax.io/v1/text/chatcompletion_v2");
    }

    @Test
    void anEmptyAllowlistRefusesEverything() {
        assertThat(violationOf(new OutboundUrlPolicy(List.of(), true), "https://api.minimax.io/"))
                .isEqualTo(Violation.NOT_IN_ALLOWLIST);
        assertThat(violationOf(new OutboundUrlPolicy(null, true), "https://api.minimax.io/"))
                .isEqualTo(Violation.NOT_IN_ALLOWLIST);
    }

    // ── 規則 6：dns_rebinding ────────────────────────────────────────────────

    @Test
    void aNameResolvingToAPrivateOrLinkLocalAddressIsRefusedEvenWhenTheNameIsListed() {
        Target target = e2e.checkStatic("http://rebind.e2e.test/v1/chat/completions");
        assertThatThrownBy(() -> e2e.checkResolved(target, List.of(ip("10.0.0.5"))))
                .isInstanceOfSatisfying(Rejected.class, r -> {
                    assertThat(r.violation()).isEqualTo(Violation.DNS_REBINDING);
                    assertThat(r.host()).isEqualTo("rebind.e2e.test");
                });
        // 任一位址不合格就拒絕（多筆 A／AAAA 中混了一個內網位址）
        assertThatThrownBy(() -> e2e.checkResolved(target, List.of(ip("8.8.8.8"), ip("169.254.169.254"))))
                .isInstanceOfSatisfying(Rejected.class, r -> assertThat(r.violation()).isEqualTo(Violation.DNS_REBINDING));
        assertThatThrownBy(() -> e2e.checkResolved(target, List.of(ip("fd00::1"))))
                .isInstanceOf(Rejected.class);
        assertThatThrownBy(() -> e2e.checkResolved(target, List.of(ip("::ffff:192.168.0.1"))))
                .isInstanceOf(Rejected.class);
    }

    @Test
    void aNameResolvingToLoopbackIsRefusedUnlessTheLoopbackFlagIsOn() {
        Target listedName = production.checkStatic("http://localhost:8123/x");
        assertThatThrownBy(() -> production.checkResolved(listedName, List.of(ip("127.0.0.1"), ip("::1"))))
                .isInstanceOfSatisfying(Rejected.class, r -> assertThat(r.violation()).isEqualTo(Violation.DNS_REBINDING));
        // e2e：allow-loopback＝true，allowlist 內的 localhost 解析到 loopback 放行
        Target e2eName = e2e.checkStatic("http://localhost:8123/x");
        e2e.checkResolved(e2eName, List.of(ip("127.0.0.1"), ip("::1")));
        // 但 loopback 加上一個私網位址仍然拒絕
        assertThatThrownBy(() -> e2e.checkResolved(e2eName, List.of(ip("127.0.0.1"), ip("10.1.1.1"))))
                .isInstanceOf(Rejected.class);
    }

    @Test
    void publicResolutionPasses() {
        Target target = e2e.checkStatic("https://api.minimax.io/v1");
        e2e.checkResolved(target, List.of(ip("93.184.216.34"), ip("2606:2800:220:1:248:1893:25c8:1946")));
    }

    @Test
    void checkResolvedIsANoOpForIpLiterals() {
        Target literal = e2e.checkStatic("http://127.0.0.1:9/x");
        e2e.checkResolved(literal, List.of(ip("10.0.0.5")));
    }

    // ── 分類表 ───────────────────────────────────────────────────────────────

    @ParameterizedTest(name = "{0} → {1}")
    @CsvSource({
            "8.8.8.8,PUBLIC", "93.184.216.34,PUBLIC", "172.32.0.1,PUBLIC", "172.15.255.255,PUBLIC", "100.63.255.255,PUBLIC",
            "100.128.0.1,PUBLIC", "192.0.2.1,PUBLIC", "198.20.0.1,PUBLIC", "223.255.255.255,PUBLIC",
            "127.0.0.1,LOOPBACK", "::1,LOOPBACK", "169.254.1.1,LINK_LOCAL", "fe80::abcd,LINK_LOCAL",
            "10.255.255.255,PRIVATE", "172.16.0.0,PRIVATE", "192.168.255.255,PRIVATE", "100.64.0.0,PRIVATE",
            "100.127.255.255,PRIVATE", "0.1.2.3,PRIVATE", "192.0.0.8,PRIVATE", "198.19.255.255,PRIVATE",
            "240.0.0.1,PRIVATE", "fc00::,PRIVATE", "fdff:ffff::1,PRIVATE", "fec0::1,PRIVATE", "::,PRIVATE",
            "ff00::1,PRIVATE", "2001:db8::1,PUBLIC"})
    void addressClassification(String address, AddressClass expected) {
        assertThat(OutboundUrlPolicy.classify(ip(address))).isEqualTo(expected);
    }

    @Test
    void theViolationCodesAreTheContractLiterals() {
        assertThat(List.of(Violation.values())).extracting(Violation::code).containsExactly("malformed_url", "scheme",
                "userinfo", "loopback", "link_local", "private_ip", "not_in_allowlist", "dns_rebinding");
    }
}
