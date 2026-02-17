import sqlite3
import hashlib
import os
from datetime import datetime

DB_NAME = "stressguard.db"

# =====================================================
# CONNECTION
# =====================================================

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# =====================================================
# INITIALIZE DATABASE
# =====================================================

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # USERS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # STRESS LOGS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stress_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            user_text TEXT NOT NULL,
            stress_score INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # CHAT HISTORY TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # MANAGER TEAM TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS manager_team (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manager_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL,
            FOREIGN KEY (manager_id) REFERENCES users(id),
            FOREIGN KEY (employee_id) REFERENCES users(id),
            UNIQUE(manager_id, employee_id)
        )
    """)

    # ALERTS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            stress_score INTEGER NOT NULL,
            resolved INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # AUDIT LOG TABLE (STEP 8)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            username TEXT NOT NULL,
            action TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# =====================================================
# PASSWORD HASHING
# =====================================================

def generate_salt():
    return os.urandom(16).hex()

def hash_password(password, salt):
    return hashlib.sha256((password + salt).encode()).hexdigest()


# =====================================================
# AUDIT LOGGING
# =====================================================

def log_action(username, action):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO audit_logs (timestamp, username, action)
        VALUES (?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        username,
        action
    ))

    conn.commit()
    conn.close()


# =====================================================
# AUTH FUNCTIONS
# =====================================================

def register_user(username, password, role):
    conn = get_connection()
    cursor = conn.cursor()

    salt = generate_salt()
    hashed_password = hash_password(password, salt)

    try:
        cursor.execute("""
            INSERT INTO users (username, password, salt, role)
            VALUES (?, ?, ?, ?)
        """, (username, hashed_password, salt, role))
        conn.commit()
        log_action(username, "User registered")
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def login_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, password, salt, role
        FROM users
        WHERE username = ?
    """, (username,))

    user = cursor.fetchone()
    conn.close()

    if user:
        hashed_input = hash_password(password, user["salt"])
        if hashed_input == user["password"]:
            log_action(username, "User logged in")
            return {
                "id": user["id"],
                "username": username,
                "role": user["role"]
            }

    return None


# =====================================================
# STRESS LOGGING
# =====================================================

def save_stress_log(user_id, user_text, stress_score):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO stress_logs (timestamp, user_id, user_text, stress_score)
        VALUES (?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        user_id,
        user_text,
        stress_score
    ))

    conn.commit()
    conn.close()


def create_alert(user_id, stress_score):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO alerts (timestamp, user_id, stress_score)
        VALUES (?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        user_id,
        stress_score
    ))

    conn.commit()
    conn.close()


# =====================================================
# FETCH FUNCTIONS
# =====================================================

def get_user_logs(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT timestamp, user_text, stress_score
        FROM stress_logs
        WHERE user_id = ?
        ORDER BY timestamp DESC
    """, (user_id,))

    logs = cursor.fetchall()
    conn.close()
    return logs


def fetch_all_logs():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.timestamp, u.username, s.user_text, s.stress_score
        FROM stress_logs s
        JOIN users u ON s.user_id = u.id
        ORDER BY s.timestamp DESC
    """)

    logs = cursor.fetchall()
    conn.close()
    return logs


def get_manager_team_logs(manager_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.username, s.timestamp, s.stress_score
        FROM stress_logs s
        JOIN manager_team m ON s.user_id = m.employee_id
        JOIN users u ON s.user_id = u.id
        WHERE m.manager_id = ?
        ORDER BY s.timestamp DESC
    """, (manager_id,))

    logs = cursor.fetchall()
    conn.close()
    return logs


def get_unassigned_employees():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, username
        FROM users
        WHERE role = 'employee'
        AND id NOT IN (SELECT employee_id FROM manager_team)
    """)

    users = cursor.fetchall()
    conn.close()
    return users


def assign_employee(manager_id, employee_id):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO manager_team (manager_id, employee_id)
            VALUES (?, ?)
        """, (manager_id, employee_id))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()


# =====================================================
# ALERT FETCHING
# =====================================================

def get_manager_team_alerts(manager_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.username, a.timestamp, a.stress_score
        FROM alerts a
        JOIN manager_team m ON a.user_id = m.employee_id
        JOIN users u ON a.user_id = u.id
        WHERE m.manager_id = ? AND a.resolved = 0
        ORDER BY a.timestamp DESC
    """, (manager_id,))

    alerts = cursor.fetchall()
    conn.close()
    return alerts


def get_all_alerts():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.username, a.timestamp, a.stress_score
        FROM alerts a
        JOIN users u ON a.user_id = u.id
        WHERE a.resolved = 0
        ORDER BY a.timestamp DESC
    """)

    alerts = cursor.fetchall()
    conn.close()
    return alerts


# =====================================================
# ANALYTICS
# =====================================================

def get_weekly_stress():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT strftime('%Y-%W', timestamp) as week,
               AVG(stress_score) as avg_stress
        FROM stress_logs
        GROUP BY week
        ORDER BY week DESC
    """)

    data = cursor.fetchall()
    conn.close()
    return data


def get_monthly_stress():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT strftime('%Y-%m', timestamp) as month,
               AVG(stress_score) as avg_stress
        FROM stress_logs
        GROUP BY month
        ORDER BY month DESC
    """)

    data = cursor.fetchall()
    conn.close()
    return data


def get_burnout_risk_users():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.username,
               AVG(s.stress_score) as avg_stress
        FROM stress_logs s
        JOIN users u ON s.user_id = u.id
        GROUP BY s.user_id
        HAVING avg_stress >= 70
        ORDER BY avg_stress DESC
    """)

    data = cursor.fetchall()
    conn.close()
    return data


