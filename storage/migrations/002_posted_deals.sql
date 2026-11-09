CREATE TABLE IF NOT EXISTS posted_deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id),
    channel TEXT NOT NULL,
    post_ref TEXT,
    posted_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_posted_deals_time
    ON posted_deals(posted_at);
