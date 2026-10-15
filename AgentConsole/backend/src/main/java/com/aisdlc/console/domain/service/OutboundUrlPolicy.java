package com.aisdlc.console.domain.service;

import java.net.InetAddress;
import java.net.UnknownHostException;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 外呼 URL 的 SSRF／allowlist 政策（NFR-SEC-04；契約 §1.5.7 的規則 1～6）。純 Java、不連網：
 * DNS 解析由呼叫端注入（{@link HostResolver}），政策只判定「解析結果能不能用」。
 *
 * <p>檢查順序固定（任一不過就丟 {@link Rejected}，且<b>此時尚未發出任何連線</b>）：
 * <ol>
 *   <li>{@code malformed_url}：URL 可解析；無空白／控制字元／反斜線；連接埠合法；host 只能是 ASCII
 *       （含非 ASCII 的 IDN 一律拒絕）；<b>IP 字面必須是標準寫法</b>（IPv4 點分十進位四段、IPv6 標準寫法）——
 *       十進位整數、十六進位、八進位、縮寫（如 {@code 127.1}）一律拒絕；</li>
 *   <li>{@code scheme}：只能 http／https；</li>
 *   <li>{@code userinfo}：不得含 {@code user:pass@}；</li>
 *   <li>IP 字面分類：{@code link_local}、{@code private_ip} <b>任何設定都拒絕，即使字面列在 allowlist</b>；
 *       {@code loopback} 預設拒絕，只有「{@code allowLoopback=true} 且該字面等於 allowlist 某項」才放行
 *       （只在 e2e／test／本機 profile 開啟，AR-10／D-47）；</li>
 *   <li>{@code not_in_allowlist}：host（小寫、去尾端 {@code .}）必須與 allowlist 某項完全相等；</li>
 *   <li>{@code dns_rebinding}（僅名稱 host、{@link #checkResolved}）：DNS 解析所有 A／AAAA，任一落在
 *       link-local／私網 → 拒絕（名稱解析到內網，即使該名稱在 allowlist 內）；落在 loopback 同樣拒絕，
 *       除非 {@code allowLoopback}。</li>
 * </ol>
 * 規則 1～5 不做 DNS，所以「儲存設定時」只跑 {@link #checkStatic}；實際連線前才跑 {@link #checkResolved}。
 */
public final class OutboundUrlPolicy {

    /** 違規碼（{@code details.violation} 的值域）。 */
    public enum Violation {
        MALFORMED_URL("malformed_url"),
        SCHEME("scheme"),
        USERINFO("userinfo"),
        LOOPBACK("loopback"),
        LINK_LOCAL("link_local"),
        PRIVATE_IP("private_ip"),
        NOT_IN_ALLOWLIST("not_in_allowlist"),
        DNS_REBINDING("dns_rebinding");

        private final String code;

        Violation(String code) {
            this.code = code;
        }

        public String code() {
            return code;
        }
    }

    /** 位址類別。 */
    public enum AddressClass { PUBLIC, LOOPBACK, LINK_LOCAL, PRIVATE }

    /** DNS 解析的注入點（測試以假 resolver 驗 rebinding；e2e 以 {@code test-dns-overrides} 讓結果可決定）。 */
    @FunctionalInterface
    public interface HostResolver {
        /** 解析所有 A／AAAA；解析不到丟 {@link UnknownHostException}。 */
        List<InetAddress> resolve(String host) throws UnknownHostException;
    }

    /**
     * 通過規則 1～5 的目標。
     *
     * @param host    小寫、去尾端 {@code .}、IPv6 不含方括號
     * @param port    URL 明示的連接埠；沒寫為 -1
     * @param literal host 是 IP 字面時的位址；名稱 host 為 null
     */
    public record Target(String url, String scheme, String host, int port, InetAddress literal) {
        public boolean isIpLiteral() {
            return literal != null;
        }

        /** 實際要連的連接埠（明示者，否則 http=80／https=443）。 */
        public int effectivePort() {
            return port > 0 ? port : "https".equals(scheme) ? 443 : 80;
        }
    }

    /** 政策拒絕。刻意不是 DomainException：HTTP 狀態依情境而異（儲存＝400、測試連線＝422、LLM＝brain_unsupported）。 */
    public static final class Rejected extends RuntimeException {

        private static final long serialVersionUID = 1L;

        private final Violation violation;
        private final String host;

        Rejected(Violation violation, String host) {
            super("目標位址未通過 SSRF／allowlist 檢查（" + violation.code() + "）");
            this.violation = violation;
            this.host = host;
        }

        public Violation violation() {
            return violation;
        }

        /** 已解析出的 host（絕不含 userinfo）；無法解析時為 null。 */
        public String host() {
            return host;
        }

        /** {@code {host?, violation}}（沒有 host 就省略該鍵：details 不輸出 null，契約 §0.2）。 */
        public Map<String, Object> details() {
            Map<String, Object> details = new LinkedHashMap<>();
            if (host != null) {
                details.put("host", host);
            }
            details.put("violation", violation.code());
            return details;
        }
    }

    private static final Pattern URL = Pattern.compile("^([A-Za-z][A-Za-z0-9+.\\-]*)://([^/?#]*)([/?#].*)?$");
    private static final Pattern NUMERIC_HOST =
            Pattern.compile("^(0[xX][0-9a-fA-F]*|[0-9]+)(\\.(0[xX][0-9a-fA-F]*|[0-9]+))*$");
    private static final Pattern STRICT_IPV4 = Pattern.compile("^(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})$");
    private static final Pattern HOSTNAME =
            Pattern.compile("^[a-z0-9]([a-z0-9_\\-]*[a-z0-9])?(\\.[a-z0-9]([a-z0-9_\\-]*[a-z0-9])?)*$");
    private static final Pattern IPV6_CHARS = Pattern.compile("^[0-9A-Fa-f:.]+$");

    private final Set<String> allowlist;
    private final Set<InetAddress> allowlistLiterals;
    private final boolean allowLoopback;

    /**
     * @param allowlist     host 白名單（精確比對；大小寫不拘、去尾端 {@code .}；IP 字面以位址相等比對）
     * @param allowLoopback 是否放行「列在 allowlist 內」的 loopback（只在 e2e／test／本機 profile 為 true）
     */
    public OutboundUrlPolicy(Collection<String> allowlist, boolean allowLoopback) {
        Set<String> names = new LinkedHashSet<>();
        Set<InetAddress> literals = new LinkedHashSet<>();
        for (String raw : allowlist == null ? List.<String>of() : allowlist) {
            String entry = normalizeHost(raw);
            if (entry.isEmpty()) {
                continue;
            }
            names.add(entry);
            InetAddress literal = tryParseLiteral(entry);
            if (literal != null) {
                literals.add(literal);
            }
        }
        this.allowlist = Set.copyOf(names);
        this.allowlistLiterals = Set.copyOf(literals);
        this.allowLoopback = allowLoopback;
    }

    public Set<String> allowlist() {
        return allowlist;
    }

    public boolean allowLoopback() {
        return allowLoopback;
    }

    // ── 規則 1～5（不做 DNS）────────────────────────────────────────────────────

    public Target checkStatic(String url) {
        if (url == null || url.isEmpty()) {
            throw new Rejected(Violation.MALFORMED_URL, null);
        }
        for (int i = 0; i < url.length(); i++) {
            char c = url.charAt(i);
            if (Character.isWhitespace(c) || Character.isISOControl(c) || c == '\\') {
                throw new Rejected(Violation.MALFORMED_URL, null);
            }
        }
        Matcher m = URL.matcher(url);
        if (!m.matches()) {
            throw new Rejected(Violation.MALFORMED_URL, null);
        }
        String scheme = m.group(1).toLowerCase(Locale.ROOT);
        String authority = m.group(2);
        int at = authority.lastIndexOf('@');
        String userinfo = at >= 0 ? authority.substring(0, at) : null;
        String hostPort = at >= 0 ? authority.substring(at + 1) : authority;

        String rawHost;
        String portText = null;
        boolean bracketed = hostPort.startsWith("[");
        if (bracketed) {
            int close = hostPort.indexOf(']');
            if (close < 0) {
                throw new Rejected(Violation.MALFORMED_URL, null);
            }
            rawHost = hostPort.substring(1, close);
            String rest = hostPort.substring(close + 1);
            if (!rest.isEmpty()) {
                if (!rest.startsWith(":")) {
                    throw new Rejected(Violation.MALFORMED_URL, null);
                }
                portText = rest.substring(1);
            }
        } else {
            int colon = hostPort.lastIndexOf(':');
            if (colon >= 0) {
                rawHost = hostPort.substring(0, colon);
                portText = hostPort.substring(colon + 1);
            } else {
                rawHost = hostPort;
            }
        }
        if (rawHost.isEmpty()) {
            throw new Rejected(Violation.MALFORMED_URL, null);
        }
        for (int i = 0; i < rawHost.length(); i++) {
            if (rawHost.charAt(i) > 127) {
                throw new Rejected(Violation.MALFORMED_URL, null);
            }
        }
        int port = parsePort(portText);

        String host = normalizeHost(rawHost);
        InetAddress literal = null;
        if (bracketed) {
            literal = parseIpv6(host);
            if (literal == null) {
                throw new Rejected(Violation.MALFORMED_URL, null);
            }
        } else if (host.indexOf(':') >= 0) {
            throw new Rejected(Violation.MALFORMED_URL, null);
        } else if (NUMERIC_HOST.matcher(host).matches()) {
            literal = parseStrictIpv4(host);
            if (literal == null) {
                throw new Rejected(Violation.MALFORMED_URL, null);
            }
        } else if (host.length() > 253 || !HOSTNAME.matcher(host).matches()) {
            throw new Rejected(Violation.MALFORMED_URL, null);
        }

        // 規則 2、3
        if (!scheme.equals("http") && !scheme.equals("https")) {
            throw new Rejected(Violation.SCHEME, host);
        }
        if (userinfo != null) {
            throw new Rejected(Violation.USERINFO, host);
        }

        // 規則 4：IP 字面分類
        if (literal != null) {
            switch (classify(literal)) {
                case LINK_LOCAL -> throw new Rejected(Violation.LINK_LOCAL, host);
                case PRIVATE -> throw new Rejected(Violation.PRIVATE_IP, host);
                case LOOPBACK -> {
                    if (!(allowLoopback && allowlistContains(host, literal))) {
                        throw new Rejected(Violation.LOOPBACK, host);
                    }
                }
                default -> {
                    // 公開位址：交給規則 5
                }
            }
        }

        // 規則 5
        if (!allowlistContains(host, literal)) {
            throw new Rejected(Violation.NOT_IN_ALLOWLIST, host);
        }
        return new Target(url, scheme, host, port, literal);
    }

    // ── 規則 6（僅名稱 host；DNS 結果）────────────────────────────────────────

    /** 名稱 host 的 DNS 解析結果檢查：任一位址落在 link-local／私網（或未放行的 loopback）→ {@code dns_rebinding}。 */
    public void checkResolved(Target target, List<InetAddress> resolved) {
        if (target.isIpLiteral()) {
            return;
        }
        for (InetAddress address : resolved) {
            AddressClass kind = classify(address);
            boolean bad = kind == AddressClass.LINK_LOCAL || kind == AddressClass.PRIVATE
                    || (kind == AddressClass.LOOPBACK && !allowLoopback);
            if (bad) {
                throw new Rejected(Violation.DNS_REBINDING, target.host());
            }
        }
    }

    // ── 位址分類 ──────────────────────────────────────────────────────────────

    /**
     * loopback：127.0.0.0/8、::1；link-local：169.254.0.0/16（含 169.254.169.254）、fe80::/10；
     * 私網：10/8、172.16/12、192.168/16、100.64/10、0.0.0.0/8、192.0.0.0/24、198.18/15、多播與保留（224/4、240/4）、
     * fc00::/7、fec0::/10、::、ff00::/8。IPv4-mapped IPv6 由 JDK 還原成 IPv4 後判定。
     */
    public static AddressClass classify(InetAddress address) {
        if (address.isLoopbackAddress()) {
            return AddressClass.LOOPBACK;
        }
        if (address.isLinkLocalAddress()) {
            return AddressClass.LINK_LOCAL;
        }
        byte[] b = address.getAddress();
        if (b.length == 4) {
            int b0 = b[0] & 0xFF;
            int b1 = b[1] & 0xFF;
            boolean privateRange = b0 == 0
                    || b0 == 10
                    || (b0 == 100 && (b1 & 0xC0) == 64)
                    || (b0 == 172 && (b1 & 0xF0) == 16)
                    || (b0 == 192 && b1 == 168)
                    || (b0 == 192 && b1 == 0 && (b[2] & 0xFF) == 0)
                    || (b0 == 198 && (b1 & 0xFE) == 18)
                    || b0 >= 224;
            return privateRange ? AddressClass.PRIVATE : AddressClass.PUBLIC;
        }
        int b0 = b[0] & 0xFF;
        boolean privateRange = address.isAnyLocalAddress()
                || address.isSiteLocalAddress()
                || (b0 & 0xFE) == 0xFC
                || b0 == 0xFF;
        return privateRange ? AddressClass.PRIVATE : AddressClass.PUBLIC;
    }

    // ── 內部 ──────────────────────────────────────────────────────────────────

    private boolean allowlistContains(String host, InetAddress literal) {
        if (allowlist.contains(host)) {
            return true;
        }
        return literal != null && allowlistLiterals.contains(literal);
    }

    private static String normalizeHost(String raw) {
        if (raw == null) {
            return "";
        }
        String host = raw.strip().toLowerCase(Locale.ROOT);
        if (host.startsWith("[") && host.endsWith("]")) {
            host = host.substring(1, host.length() - 1);
        }
        if (host.endsWith(".")) {
            host = host.substring(0, host.length() - 1);
        }
        return host;
    }

    private static int parsePort(String portText) {
        if (portText == null) {
            return -1;
        }
        if (portText.isEmpty() || portText.length() > 5) {
            throw new Rejected(Violation.MALFORMED_URL, null);
        }
        for (int i = 0; i < portText.length(); i++) {
            char c = portText.charAt(i);
            if (c < '0' || c > '9') {
                throw new Rejected(Violation.MALFORMED_URL, null);
            }
        }
        int port = Integer.parseInt(portText);
        if (port < 1 || port > 65535) {
            throw new Rejected(Violation.MALFORMED_URL, null);
        }
        return port;
    }

    /** 嚴格的點分十進位四段（每段 0～255、不得有前導零）；其餘一律 null。 */
    private static InetAddress parseStrictIpv4(String host) {
        Matcher m = STRICT_IPV4.matcher(host);
        if (!m.matches()) {
            return null;
        }
        byte[] bytes = new byte[4];
        for (int i = 0; i < 4; i++) {
            String part = m.group(i + 1);
            if (part.length() > 1 && part.charAt(0) == '0') {
                return null;
            }
            int value = Integer.parseInt(part);
            if (value > 255) {
                return null;
            }
            bytes[i] = (byte) value;
        }
        try {
            return InetAddress.getByAddress(bytes);
        } catch (UnknownHostException e) {
            return null;
        }
    }

    /** IPv6 字面（不含方括號與 zone id）；字元集驗過才交給 JDK 解析，所以不會觸發 DNS。 */
    private static InetAddress parseIpv6(String literal) {
        if (literal.indexOf(':') < 0 || !IPV6_CHARS.matcher(literal).matches()) {
            return null;
        }
        try {
            return InetAddress.getByName(literal);
        } catch (UnknownHostException e) {
            return null;
        }
    }

    private static InetAddress tryParseLiteral(String entry) {
        if (entry.indexOf(':') >= 0) {
            return parseIpv6(entry);
        }
        return STRICT_IPV4.matcher(entry).matches() ? parseStrictIpv4(entry) : null;
    }
}
