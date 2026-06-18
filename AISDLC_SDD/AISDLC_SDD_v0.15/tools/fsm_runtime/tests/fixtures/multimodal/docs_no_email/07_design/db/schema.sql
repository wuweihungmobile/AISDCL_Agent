-- A-31.5 negative fixture: users table missing `email` column.
CREATE TABLE users (
    id BIGINT PRIMARY KEY,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
