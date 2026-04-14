CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    platform_product_id TEXT NOT NULL,
    name TEXT NOT NULL,
    brand TEXT,
    category TEXT NOT NULL,
    product_url TEXT NOT NULL,
    image_url TEXT,
    first_seen_at TIMESTAMP NOT NULL,
    last_seen_at TIMESTAMP NOT NULL,
    UNIQUE(platform, platform_product_id)
);

CREATE INDEX IF NOT EXISTS idx_products_platform_category
    ON products(platform, category);

CREATE TABLE IF NOT EXISTS price_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id),
    price REAL NOT NULL,
    original_price REAL,
    discount_rate REAL,
    seller_name TEXT,
    seller_rating REAL,
    in_stock INTEGER NOT NULL DEFAULT 1,
    captured_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_snapshots_product_time
    ON price_snapshots(product_id, captured_at DESC);

CREATE TABLE IF NOT EXISTS run_stats (
    run_id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    category TEXT NOT NULL,
    products_found INTEGER,
    products_saved INTEGER,
    products_failed INTEGER,
    duration_seconds INTEGER,
    status TEXT NOT NULL,
    error_message TEXT,
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP
);
