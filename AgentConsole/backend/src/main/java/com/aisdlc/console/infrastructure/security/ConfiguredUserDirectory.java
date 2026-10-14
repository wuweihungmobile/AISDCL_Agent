package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.application.port.out.UserDirectory;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

/** 以 application.yml 的 {@code console.auth.users[]} 為來源的使用者目錄（無使用者管理 UI）。 */
@Component
public class ConfiguredUserDirectory implements UserDirectory {

    private final Map<String, UserAccount> byUsername = new HashMap<>();

    public ConfiguredUserDirectory(ConsoleAuthProperties properties) {
        for (ConsoleAuthProperties.UserProperties user : properties.users()) {
            UserAccount previous = byUsername.put(user.username(),
                    new UserAccount(user.username(), user.passwordHash(), user.role()));
            if (previous != null) {
                throw new IllegalStateException("console.auth.users 有重複的 username：" + user.username());
            }
        }
    }

    @Override
    public Optional<UserAccount> findByUsername(String username) {
        return Optional.ofNullable(byUsername.get(username));
    }
}
