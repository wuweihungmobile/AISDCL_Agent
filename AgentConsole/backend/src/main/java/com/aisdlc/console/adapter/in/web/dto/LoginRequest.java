package com.aisdlc.console.adapter.in.web.dto;

import jakarta.validation.constraints.NotBlank;

public record LoginRequest(
        @NotBlank(message = "username 不能為空") String username,
        @NotBlank(message = "password 不能為空") String password) {
}
