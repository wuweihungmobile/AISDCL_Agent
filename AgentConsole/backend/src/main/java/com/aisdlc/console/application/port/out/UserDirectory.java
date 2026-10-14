package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.auth.Role;

import java.util.Optional;

/** 使用者目錄埠：目前實作＝application.yml 的 console.auth.users[]（無使用者管理 UI）。 */
public interface UserDirectory {

    record UserAccount(String username, String passwordHash, Role role) {
    }

    Optional<UserAccount> findByUsername(String username);
}
