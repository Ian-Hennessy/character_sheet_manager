DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS post;

CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);

CREATE TABLE post (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id INTEGER NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    FOREIGN KEY (author_id) REFERENCES user (id)
);

-- Characters table: one row per character, belongs to a user
CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    class TEXT NOT NULL,  -- Class name (e.g., 'Cleric') from API
    species TEXT NOT NULL,  -- Species name (e.g., 'Tiefling') from API
    level INTEGER DEFAULT 1,
    data TEXT NOT NULL, -- JSON-encoded character data
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user (id)
);

CREATE TABLE homebrew_classes (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    hit_die INTEGER,
    data TEXT NOT NULL,  -- JSON
    is_public BOOLEAN DEFAULT FALSE,
    version INTEGER DEFAULT 1,
    created TIMESTAMP,
    updated TIMESTAMP,
    UNIQUE(user_id, name),
    FOREIGN KEY (user_id) REFERENCES user (id)
);

CREATE TABLE homebrew_species (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    data TEXT NOT NULL,  -- JSON
    is_public BOOLEAN DEFAULT FALSE,
    version INTEGER DEFAULT 1,
    created TIMESTAMP,
    updated TIMESTAMP,
    UNIQUE(user_id, name),
    FOREIGN KEY (user_id) REFERENCES user (id)
);

CREATE TABLE homebrew_subclasses (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    class_name TEXT NOT NULL,
    subclass_name TEXT NOT NULL,
    data TEXT NOT NULL,  -- JSON
    is_public BOOLEAN DEFAULT FALSE,
    version INTEGER DEFAULT 1,
    created TIMESTAMP,
    updated TIMESTAMP,
    UNIQUE(user_id, class_name, subclass_name),
    FOREIGN KEY (user_id) REFERENCES user (id)
);

-- Track which homebrew content is used in characters
CREATE TABLE character_homebrew_links (
    id INTEGER PRIMARY KEY,
    character_id INTEGER NOT NULL,
    homebrew_class_id INTEGER,
    homebrew_species_id INTEGER,
    homebrew_subclass_id INTEGER,
    FOREIGN KEY (character_id) REFERENCES characters (id),
    FOREIGN KEY (homebrew_class_id) REFERENCES homebrew_classes (id),
    FOREIGN KEY (homebrew_species_id) REFERENCES homebrew_species (id),
    FOREIGN KEY (homebrew_subclass_id) REFERENCES homebrew_subclasses (id)
);
