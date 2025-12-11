--  Command Gateway Schema 

CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(64) UNIQUE NOT NULL,
    api_key         VARCHAR(128) UNIQUE NOT NULL,
    role            VARCHAR(16) NOT NULL CHECK (role IN ('admin','member')),
    seniority       VARCHAR(32) NOT NULL DEFAULT 'standard',
    credits         INTEGER NOT NULL DEFAULT 100,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_api_key ON users(api_key);



CREATE TABLE rules (
    id              SERIAL PRIMARY KEY,
    pattern         TEXT NOT NULL,
    action          VARCHAR(32) NOT NULL CHECK (
                        action IN ('AUTO_ACCEPT','AUTO_REJECT','REQUIRE_APPROVAL')
                     ),
    priority        INTEGER NOT NULL DEFAULT 100,
    approval_threshold INTEGER NOT NULL DEFAULT 1,
    user_thresholds  JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rules_priority ON rules(priority, id);



CREATE TABLE commands (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    command_text    TEXT NOT NULL,
    matched_rule_id INTEGER REFERENCES rules(id),
    action_taken    VARCHAR(32) NOT NULL CHECK (
                        action_taken IN (
                           'PENDING','EXECUTED','REJECTED','FAILED','WAITING_APPROVAL'
                        )
                     ),
    cost            INTEGER NOT NULL DEFAULT 0,
     required_approvals INTEGER NOT NULL DEFAULT 0,
    result          TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    executed_at     TIMESTAMP
);

CREATE INDEX idx_commands_user_id ON commands(user_id);
CREATE INDEX idx_commands_rule_id ON commands(matched_rule_id);


CREATE TABLE approvals (
    id              SERIAL PRIMARY KEY,
    command_id      INTEGER NOT NULL REFERENCES commands(id) ON DELETE CASCADE,
    approver_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    decision        BOOLEAN,    -- TRUE = approved, FALSE = rejected
    decided_at      TIMESTAMP,
    CONSTRAINT uq_approval_per_admin UNIQUE (command_id, approver_id)
);

CREATE INDEX idx_approvals_command ON approvals(command_id);


