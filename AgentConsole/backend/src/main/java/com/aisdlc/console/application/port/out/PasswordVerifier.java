package com.aisdlc.console.application.port.out;

/** 密碼雜湊比對埠（實作：BCrypt）。 */
public interface PasswordVerifier {

    boolean matches(String rawPassword, String passwordHash);
}
