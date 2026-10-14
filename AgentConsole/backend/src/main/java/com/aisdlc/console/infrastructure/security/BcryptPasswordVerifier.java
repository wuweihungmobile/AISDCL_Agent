package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.application.port.out.PasswordVerifier;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

/** 以 Spring Security 的 BCrypt {@link PasswordEncoder} 比對密碼。 */
@Component
public class BcryptPasswordVerifier implements PasswordVerifier {

    private final PasswordEncoder encoder;

    public BcryptPasswordVerifier(PasswordEncoder encoder) {
        this.encoder = encoder;
    }

    @Override
    public boolean matches(String rawPassword, String passwordHash) {
        return encoder.matches(rawPassword, passwordHash);
    }
}
