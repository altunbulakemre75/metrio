-- Hesap büyümesi: her gün kanal başına takipçi/abone sayısı (deals/stats.py).
CREATE TABLE IF NOT EXISTS account_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT NOT NULL,
    followers INTEGER NOT NULL,
    captured_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_account_stats_channel_time
    ON account_stats(channel, captured_at);
