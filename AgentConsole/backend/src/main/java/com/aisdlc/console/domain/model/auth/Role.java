package com.aisdlc.console.domain.model.auth;

/**
 * RBAC 角色（PRD §9.2；Architecture §8.2）。
 * VIEWER 只能讀；OPERATOR 可建立／編輯／刪除／signoff／執行；ADMIN 另可改系統參數。
 */
public enum Role {
    ADMIN,
    OPERATOR,
    VIEWER
}
