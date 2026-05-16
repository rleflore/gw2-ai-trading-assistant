-- GW2 Trading Assistant — Database Schema

-- Reference data for tracked items
CREATE TABLE IF NOT EXISTS items (
    item_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    rarity TEXT,
    type TEXT,
    level INTEGER DEFAULT 0,
    icon_url TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Historical price snapshots from /v2/commerce/prices
CREATE TABLE IF NOT EXISTS price_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    buy_price INTEGER NOT NULL,
    sell_price INTEGER NOT NULL,
    buy_quantity INTEGER NOT NULL,
    sell_quantity INTEGER NOT NULL,
    FOREIGN KEY (item_id) REFERENCES items(item_id)
);

CREATE INDEX IF NOT EXISTS idx_price_snapshots_item_time
    ON price_snapshots(item_id, timestamp);

-- Patch notes from GW2 Wiki (MediaWiki API)
CREATE TABLE IF NOT EXISTS patch_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    title TEXT NOT NULL,
    full_text TEXT NOT NULL,
    source_url TEXT,
    affected_systems TEXT,
    fetched_at TEXT DEFAULT (datetime('now')),
    UNIQUE(date, title)
);

-- Reddit posts from r/Guildwars2
CREATE TABLE IF NOT EXISTS reddit_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    body TEXT,
    upvotes INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    timestamp TEXT NOT NULL,
    url TEXT,
    fetched_at TEXT DEFAULT (datetime('now'))
);
