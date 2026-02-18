import sqlite3
import hashlib
import os
from datetime import datetime


DB_NAME = os.path.join(os.getcwd(), "stressguard.db")


# =====================================================
# CONNECTION
# =====================================================

def get_connection():
    # Persistent path for Streamlit Cloud
    if os.path.exists("/mount/data"):
        db_path = "/mount/data/stressguard.db"
    else:
        db_path = "stressguard.db"

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row  
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# =====================================================
# INITIALIZE DATABASE
# =====================================================

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # USERS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('employee','manager','admin'))
        )
    """)

    # STRESS LOGS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stress_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            user_text TEXT NOT NULL,
            stress_score INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # CHAT HISTORY
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # MANAGER TEAM
    cursor.execute("""
         CREATE TABLE IF NOT EXISTS manager_team (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             manager_id INTEGER NOT NULL,
              employee_id INTEGER NOT NULL,
              UNIQUE(manager_id, employee_id),
             FOREIGN KEY(manager_id) REFERENCES users(id) ON DELETE CASCADE,
             FOREIGN KEY(employee_id) REFERENCES users(id) ON DELETE CASCADE
         )
     """)

    # ALERTS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            stress_score INTEGER NOT NULL,
            severity TEXT NOT NULL,
            escalation_level INTEGER DEFAULT 1,
            resolved INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # AUDIT LOGS
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
# PASSWORD SECURITY
# =====================================================

def generate_salt():
    return os.urandom(16).hex()

def hash_password(password, salt):
    return hashlib.sha256((password + salt).encode()).hexdigest()

# =====================================================
# AUTH
# =====================================================

def register_user(username, password, role):
    conn = get_connection()
    cursor = conn.cursor()
    role = role.strip().lower() 
    salt = generate_salt()
    hashed = hash_password(password, salt)

    try:
        cursor.execute("""
            INSERT INTO users (username, password, salt, role)
            VALUES (?, ?, ?, ?)
        """, (username, hashed, salt, role))
        conn.commit()
        log_action(username, "User Registered")
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user and hash_password(password, user["salt"]) == user["password"]:
        log_action(username, "User Logged In")
        return {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"].strip().lower()
        }

    return None

# =====================================================
# AUDIT
# =====================================================

def log_action(username, action):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO audit_logs (timestamp, username, action)
        VALUES (?, ?, ?)
    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), username, action))

    conn.commit()
    conn.close()

# =====================================================
# CHAT SYSTEM
# =====================================================

def save_chat_message(user_id, role, message):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO chat_history (timestamp, user_id, role, message)
        VALUES (?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        user_id,
        role,
        message
    ))

    conn.commit()
    conn.close()

def get_chat_history(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT role, message
        FROM chat_history
        WHERE user_id=?
        ORDER BY timestamp ASC
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    return [
    {"role": row["role"], "message": row["message"]}
    for row in rows
    ]

# =====================================================
# STRESS & ALERTS
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

    # Determine severity
    if stress_score >= 90:
        severity = "CRITICAL"
        escalation = 3
    elif stress_score >= 80:
        severity = "HIGH"
        escalation = 2
    elif stress_score >= 70:
        severity = "MEDIUM"
        escalation = 1
    else:
        severity = "LOW"
        escalation = 1

    cursor.execute("""
        INSERT INTO alerts (timestamp, user_id, stress_score, severity, escalation_level)
        VALUES (?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        user_id,
        stress_score,
        severity,
        escalation
    ))

    conn.commit()
    conn.close()
# =====================================================
# ANALYTICS
# =====================================================

def get_user_logs(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT timestamp, stress_score
        FROM stress_logs
        WHERE user_id=?
        ORDER BY timestamp DESC
    """, (user_id,))

    logs = cursor.fetchall()
    conn.close()
    return logs

def fetch_all_logs():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.timestamp,
               u.username,
               s.user_text,
               s.stress_score
        FROM stress_logs s
        JOIN users u ON s.user_id = u.id
        ORDER BY s.timestamp DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows

def get_weekly_stress(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT AVG(stress_score)
        FROM stress_logs
        WHERE user_id=?
        AND timestamp >= datetime('now','-7 days')
    """, (user_id,))

    result = cursor.fetchone()[0]
    conn.close()
    return round(result, 1) if result else None

def get_monthly_stress(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT AVG(stress_score)
        FROM stress_logs
        WHERE user_id=?
        AND timestamp >= datetime('now','-30 days')
    """, (user_id,))

    result = cursor.fetchone()[0]
    conn.close()
    return round(result, 1) if result else None

def get_burnout_risk_users():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.username, AVG(s.stress_score) as avg_stress
        FROM stress_logs s
        JOIN users u ON s.user_id = u.id
        GROUP BY s.user_id
        HAVING avg_stress >= 70
    """)

    data = cursor.fetchall()
    conn.close()
    return data

# =====================================================
# MANAGER
# =====================================================
def get_manager_team_members(manager_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.id, u.username
        FROM users u
        JOIN manager_team m
        ON u.id = m.employee_id
        WHERE m.manager_id = ?
    """, (manager_id,))

    rows = cursor.fetchall()
    conn.close()
    return rows

def get_available_employees(manager_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
         SELECT id, username
        FROM users
        WHERE role = 'employee'
        AND id NOT IN (
            SELECT employee_id
            FROM manager_team
            WHERE manager_id = ?
        )
    """, (manager_id,))

    rows = cursor.fetchall()
    conn.close()
    return rows

def assign_employee(employee_id, manager_id):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO manager_team (manager_id, employee_id)
            VALUES (?, ?)
        """, (manager_id, employee_id))

        conn.commit()
        return True

    except sqlite3.IntegrityError as e:
        conn.rollback()
        raise Exception(f"DB ERROR: {e}")

    finally:
        conn.close()

def get_manager_team_logs(manager_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.username, s.timestamp, s.stress_score
        FROM stress_logs s
        JOIN manager_team m ON s.user_id = m.employee_id
        JOIN users u ON u.id = s.user_id
        WHERE m.manager_id=?
        ORDER BY s.timestamp DESC
    """, (manager_id,))

    logs = cursor.fetchall()
    conn.close()
    return logs

def get_manager_team_alerts(manager_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.username, a.timestamp, a.stress_score, a.severity, a.escalation_level
        FROM alerts a
        JOIN manager_team m ON a.user_id = m.employee_id
        JOIN users u ON u.id = a.user_id
        WHERE m.manager_id=? AND a.resolved=0
    """, (manager_id,))

    data = cursor.fetchall()
    conn.close()
    return data

def get_all_alerts():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.username, a.timestamp, a.stress_score
        FROM alerts a
        JOIN users u ON u.id = a.user_id
        WHERE a.resolved=0
    """)

    data = cursor.fetchall()
    conn.close()
    return data

