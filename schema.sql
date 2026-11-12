-- Smart Gram Panchayat Complaint Portal – Database Schema

DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS feedback;
DROP TABLE IF EXISTS duplicate_relationships;
DROP TABLE IF EXISTS complaint_history;
DROP TABLE IF EXISTS complaints;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    mobile          TEXT    NOT NULL UNIQUE,
    email           TEXT,
    password_hash   TEXT    NOT NULL,
    ward            TEXT,
    role            TEXT    NOT NULL DEFAULT 'citizen',
    department      TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE complaints (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_uid       TEXT    NOT NULL UNIQUE,
    user_id             INTEGER NOT NULL,
    title               TEXT    NOT NULL,
    description         TEXT    NOT NULL,
    category            TEXT    NOT NULL,
    ward                TEXT    NOT NULL,
    location_detail     TEXT,
    image_path          TEXT,
    status              TEXT    NOT NULL DEFAULT 'Submitted',
    assigned_officer_id INTEGER,
    parent_complaint_id INTEGER,
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)             REFERENCES users (id),
    FOREIGN KEY (assigned_officer_id) REFERENCES users (id),
    FOREIGN KEY (parent_complaint_id) REFERENCES complaints (id)
);

CREATE TABLE complaint_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id    INTEGER NOT NULL,
    old_status      TEXT,
    new_status      TEXT    NOT NULL,
    remarks         TEXT,
    updated_by      INTEGER,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (complaint_id) REFERENCES complaints (id),
    FOREIGN KEY (updated_by)   REFERENCES users (id)
);

CREATE TABLE duplicate_relationships (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_complaint_id     INTEGER NOT NULL,
    duplicate_complaint_id  INTEGER NOT NULL,
    similarity_score        REAL    NOT NULL,
    verification_status     TEXT    NOT NULL DEFAULT 'pending',
    verified_by             INTEGER,
    verified_at             TIMESTAMP,
    FOREIGN KEY (parent_complaint_id)    REFERENCES complaints (id),
    FOREIGN KEY (duplicate_complaint_id) REFERENCES complaints (id),
    FOREIGN KEY (verified_by)            REFERENCES users (id)
);

CREATE TABLE feedback (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id    INTEGER NOT NULL,
    user_id         INTEGER NOT NULL,
    rating          INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comments        TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (complaint_id) REFERENCES complaints (id),
    FOREIGN KEY (user_id)      REFERENCES users (id)
);

CREATE TABLE notifications (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    message     TEXT    NOT NULL,
    is_read     INTEGER NOT NULL DEFAULT 0,
    link        TEXT,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
