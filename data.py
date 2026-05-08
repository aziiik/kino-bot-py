import sqlite3

DB_FILE = "data.db"


def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT NOT NULL, username TEXT);
            CREATE TABLE IF NOT EXISTS movies (code TEXT PRIMARY KEY, file_id TEXT NOT NULL, type TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS supports (user_id INTEGER PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS channels (channel_id TEXT PRIMARY KEY);
        """)

def user_exists(user_id): return get_conn().execute("SELECT 1 FROM users WHERE user_id=?", (user_id,)).fetchone() is not None
def add_user(user_id, name, username):
    with get_conn() as c: c.execute("INSERT OR IGNORE INTO users VALUES(?,?,?)", (user_id, name, username))
def get_all_user_ids():
    with get_conn() as c: return [r["user_id"] for r in c.execute("SELECT user_id FROM users").fetchall()]
def count_users():
    with get_conn() as c: return c.execute("SELECT COUNT(*) FROM users").fetchone()[0]

def movie_exists(code): return get_conn().execute("SELECT 1 FROM movies WHERE code=?", (code,)).fetchone() is not None
def get_movie(code):
    row = get_conn().execute("SELECT file_id, type FROM movies WHERE code=?", (code,)).fetchone()
    return dict(row) if row else None
def add_movie(code, file_id, file_type):
    with get_conn() as c: c.execute("INSERT OR REPLACE INTO movies VALUES(?,?,?)", (code, file_id, file_type))
def delete_movie(code):
    with get_conn() as c: return c.execute("DELETE FROM movies WHERE code=?", (code,)).rowcount > 0
def count_movies():
    with get_conn() as c: return c.execute("SELECT COUNT(*) FROM movies").fetchone()[0]

def is_admin(user_id): return get_conn().execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,)).fetchone() is not None
def add_admin(user_id):
    with get_conn() as c: c.execute("INSERT OR IGNORE INTO admins VALUES(?)", (user_id,))
def remove_admin(user_id):
    with get_conn() as c: return c.execute("DELETE FROM admins WHERE user_id=?", (user_id,)).rowcount > 0
def get_all_admins():
    with get_conn() as c: return [r["user_id"] for r in c.execute("SELECT user_id FROM admins").fetchall()]
def count_admins():
    with get_conn() as c: return c.execute("SELECT COUNT(*) FROM admins").fetchone()[0]

def is_support(user_id): return get_conn().execute("SELECT 1 FROM supports WHERE user_id=?", (user_id,)).fetchone() is not None
def add_support(user_id):
    with get_conn() as c: c.execute("INSERT OR IGNORE INTO supports VALUES(?)", (user_id,))
def remove_support(user_id):
    with get_conn() as c: return c.execute("DELETE FROM supports WHERE user_id=?", (user_id,)).rowcount > 0
def get_all_supports():
    with get_conn() as c: return [r["user_id"] for r in c.execute("SELECT user_id FROM supports").fetchall()]
def count_supports():
    with get_conn() as c: return c.execute("SELECT COUNT(*) FROM supports").fetchone()[0]

def get_all_channels():
    with get_conn() as c: return [r["channel_id"] for r in c.execute("SELECT channel_id FROM channels").fetchall()]
def channel_exists(channel_id): return get_conn().execute("SELECT 1 FROM channels WHERE channel_id=?", (channel_id,)).fetchone() is not None
def add_channel(channel_id):
    with get_conn() as c: c.execute("INSERT OR IGNORE INTO channels VALUES(?)", (channel_id,))
def remove_channel(channel_id):
    with get_conn() as c: return c.execute("DELETE FROM channels WHERE channel_id=?", (channel_id,)).rowcount > 0
def count_channels():
    with get_conn() as c: return c.execute("SELECT COUNT(*) FROM channels").fetchone()[0]