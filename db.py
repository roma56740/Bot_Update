import sqlite3
from contextlib import closing


DB_NAME = 'bot.db'

def init_db():
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                name TEXT,
                username TEXT,
                role TEXT,
                hearts INTEGER DEFAULT 3,
                fine INTEGER DEFAULT 0
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                price REAL,
                description TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                user_id INTEGER PRIMARY KEY,
                day_plan REAL DEFAULT 0,
                month_plan REAL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS help_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER,
                to_user_id INTEGER,
                message TEXT,
                status TEXT DEFAULT 'pending'
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                user_id INTEGER PRIMARY KEY,
                day_sales REAL DEFAULT 0,
                month_sales REAL DEFAULT 0,
                orders_count INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """)



def register_user(telegram_id, name, username, role):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            conn.execute("""
            INSERT OR IGNORE INTO users (telegram_id, name, username, role)
            VALUES (?, ?, ?, ?)
            """, (telegram_id, name, username, role))


def get_all_users():
    with closing(sqlite3.connect(DB_NAME)) as conn:
        conn.row_factory = sqlite3.Row
        with conn:
            result = conn.execute("SELECT name, username, role FROM users").fetchall()
            return [dict(row) for row in result]

def delete_user_by_username(username):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            result = conn.execute("DELETE FROM users WHERE username = ?", (username,))
            return result.rowcount > 0


def get_all_managers_with_stats():
    with closing(sqlite3.connect(DB_NAME)) as conn:
        conn.row_factory = sqlite3.Row
        with conn:
            return [
                dict(row) for row in conn.execute("""
                SELECT 
                    u.name, u.username,
                    COALESCE(p.day_plan, 0) as day_plan,
                    COALESCE(p.month_plan, 0) as month_plan,
                    COALESCE(s.day_sales, 0) as day_sales,
                    COALESCE(s.orders_count, 0) as orders_count
                FROM users u
                LEFT JOIN plans p ON u.id = p.user_id
                LEFT JOIN stats s ON u.id = s.user_id
                WHERE u.role = 'менеджер'
                """).fetchall()
            ]


def get_user_by_username(username):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        conn.row_factory = sqlite3.Row
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(user) if user else None

def add_order(user_id, price, description):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            conn.execute("INSERT INTO orders (user_id, price, description) VALUES (?, ?, ?)",
                         (user_id, price, description))

def update_sales_stats(user_id, price):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            conn.execute("""
                INSERT INTO stats (user_id, day_sales, month_sales, orders_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(user_id) DO UPDATE SET
                    day_sales = day_sales + ?,
                    month_sales = month_sales + ?,
                    orders_count = orders_count + 1
            """, (user_id, price, price, price, price))

def get_telegram_id_by_user_id(user_id):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        result = conn.execute("SELECT telegram_id FROM users WHERE id = ?", (user_id,)).fetchone()
        return result[0] if result else None


def add_heart(user_id):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            conn.execute("UPDATE users SET hearts = MIN(3, hearts + 1) WHERE id = ?", (user_id,))

def set_user_fine(user_id, new_fine):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            conn.execute("UPDATE users SET fine = ? WHERE id = ?", (new_fine, user_id))


def remove_heart(user_id):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            conn.execute("UPDATE users SET hearts = MAX(0, hearts - 1) WHERE id = ?", (user_id,))

def add_fine(user_id, amount):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            conn.execute("UPDATE users SET fine = fine + ? WHERE id = ?", (amount, user_id))


def get_user_by_telegram_id(telegram_id):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        conn.row_factory = sqlite3.Row
        result = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
        return dict(result) if result else None

def get_user_stats(user_id):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        conn.row_factory = sqlite3.Row
        result = conn.execute("""
            SELECT 
                COALESCE(p.day_plan, 0) AS day_plan,
                COALESCE(p.month_plan, 0) AS month_plan,
                COALESCE(s.day_sales, 0) AS day_sales,
                COALESCE(s.orders_count, 0) AS orders_count
            FROM users u
            LEFT JOIN plans p ON u.id = p.user_id
            LEFT JOIN stats s ON u.id = s.user_id
            WHERE u.id = ?
        """, (user_id,)).fetchone()
        return dict(result) if result else None


def create_help_request(from_user_id, target_user_id, message):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            conn.execute("""
                INSERT INTO help_requests (from_user_id, to_user_id, message)
                VALUES (?, ?, ?)
            """, (from_user_id, target_user_id, message))




def delete_help_request_by_user(user_id):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            conn.execute("DELETE FROM help_requests WHERE from_user_id = ?", (user_id,))


def add_heart_by_telegram_id(tg_id):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        conn.execute("UPDATE users SET hearts = MIN(3, hearts + 1) WHERE telegram_id = ?", (tg_id,))


def get_all_users_full():
    with closing(sqlite3.connect(DB_NAME)) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute("SELECT * FROM users").fetchall()]


def set_plan_for_all(day, month):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            managers = conn.execute("SELECT id FROM users WHERE role = 'менеджер'").fetchall()
            for m in managers:
                user_id = m[0]
                conn.execute("""
                    INSERT INTO plans (user_id, day_plan, month_plan)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        day_plan = excluded.day_plan,
                        month_plan = excluded.month_plan
                """, (user_id, day, month))
