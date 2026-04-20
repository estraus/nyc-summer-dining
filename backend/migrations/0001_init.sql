CREATE TABLE IF NOT EXISTS restaurants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT,
    neighborhood TEXT,
    borough TEXT CHECK (borough IN ('Manhattan','Brooklyn','Queens','Bronx','Staten Island') OR borough IS NULL),
    latitude REAL,
    longitude REAL,
    price_tier INTEGER CHECK (price_tier BETWEEN 1 AND 4),
    booking_platform TEXT CHECK (booking_platform IN ('resy','opentable','tock','walk_in','other')),
    booking_url TEXT,
    resy_venue_id TEXT,
    website_url TEXT,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','closed','needs_review')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_restaurants_status ON restaurants(status);
CREATE INDEX IF NOT EXISTS idx_restaurants_neighborhood ON restaurants(neighborhood);

CREATE TABLE IF NOT EXISTS restaurant_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id TEXT NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    publication TEXT NOT NULL,
    list_name TEXT,
    source_url TEXT,
    blurb TEXT,
    source_date DATE
);
CREATE INDEX IF NOT EXISTS idx_sources_restaurant ON restaurant_sources(restaurant_id);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL CHECK (kind IN ('cuisine','vibe','feature'))
);

CREATE TABLE IF NOT EXISTS restaurant_tags (
    restaurant_id TEXT NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (restaurant_id, tag_id)
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS personal_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    restaurant_id TEXT NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('want_to_try','tried','loved','skip')),
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    note TEXT,
    visited_date DATE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, restaurant_id)
);
CREATE INDEX IF NOT EXISTS idx_notes_restaurant ON personal_notes(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_notes_user ON personal_notes(user_id);
