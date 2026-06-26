-- A-31.5 positive fixture: users table with email, password, created_at.
CREATE TABLE users (
    id BIGINT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE login_attempts (
    id BIGINT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    success BOOLEAN NOT NULL,
    attempted_at TIMESTAMP NOT NULL
);
