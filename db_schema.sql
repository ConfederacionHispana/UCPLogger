CREATE TABLE rcgcdw (
    id SERIAL,
    webhook  TEXT    NOT NULL
                     UNIQUE,
    wiki     TEXT    NOT NULL,
    lang     TEXT    NOT NULL
                     DEFAULT 'en',
    display  INTEGER NOT NULL
                     DEFAULT 0,
    rcid     INTEGER,
    postid   TEXT    DEFAULT '-1',
    UNIQUE (id)
);

CREATE INDEX idx_rcgcdw_wiki ON rcgcdw (
    wiki
);

CREATE INDEX idx_rcgcdw_webhook ON rcgcdw (
    webhook
);

CREATE INDEX idx_rcgcdw_config ON rcgcdw (
    id ASC
);