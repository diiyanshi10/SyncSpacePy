"""
user_dao.py — handles user registration and login against MySQL.
Port of UserDAO.java.
"""
import mysql.connector
import secrets
from datetime import datetime, timedelta, timezone

from db import get_connection, DUPLICATE_ENTRY_ERRNO

_profile_schema_ready = False


def ensure_profile_schema() -> None:
    """Add account-profile columns to existing users tables once."""
    global _profile_schema_ready
    if _profile_schema_ready:
        return
    columns = {
        "full_name": "VARCHAR(120) NULL",
        "avatar": "LONGTEXT NULL",
        "bio": "VARCHAR(255) NULL",
        "status_message": "VARCHAR(120) NULL",
        "is_active": "TINYINT(1) NOT NULL DEFAULT 1",
        "reset_code": "VARCHAR(64) NULL",
        "reset_expires": "DATETIME NULL",
    }
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SHOW COLUMNS FROM users")
            existing = {row[0] for row in cur.fetchall()}
            for name, definition in columns.items():
                if name not in existing:
                    cur.execute(f"ALTER TABLE users ADD COLUMN {name} {definition}")
            conn.commit()
            _profile_schema_ready = True
    except mysql.connector.Error as e:
        print(e)


def get_profile(username: str) -> dict | None:
    ensure_profile_schema()
    sql = ("SELECT username, full_name, avatar, bio, status_message, is_active "
           "FROM users WHERE username = %s")
    try:
        with get_connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(sql, (username,))
            row = cur.fetchone()
            if row:
                row["is_active"] = bool(row["is_active"])
            return row
    except mysql.connector.Error as e:
        print(e)
        return None


def update_profile(username: str, full_name: str, avatar: str, bio: str, status_message: str) -> bool:
    ensure_profile_schema()
    sql = ("UPDATE users SET full_name = %s, avatar = %s, bio = %s, "
           "status_message = %s WHERE username = %s AND is_active = 1")
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (full_name, avatar, bio, status_message, username))
            conn.commit()
            return cur.rowcount == 1
    except mysql.connector.Error as e:
        print(e)
        return False


def create_reset_code(username: str) -> str | None:
    ensure_profile_schema()
    code = f"{secrets.randbelow(1_000_000):06d}"
    expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=15)
    sql = "UPDATE users SET reset_code = %s, reset_expires = %s WHERE username = %s AND is_active = 1"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (code, expires, username))
            conn.commit()
            return code if cur.rowcount == 1 else None
    except mysql.connector.Error as e:
        print(e)
        return None


def reset_password(username: str, code: str, new_password: str) -> bool:
    ensure_profile_schema()
    sql = ("UPDATE users SET password = %s, reset_code = NULL, reset_expires = NULL "
           "WHERE username = %s AND reset_code = %s AND reset_expires > UTC_TIMESTAMP() AND is_active = 1")
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (new_password, username, code))
            conn.commit()
            return cur.rowcount == 1
    except mysql.connector.Error as e:
        print(e)
        return False


def deactivate_account(username: str, password: str) -> bool:
    ensure_profile_schema()
    if not login_user(username, password):
        return False
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET is_active = 0 WHERE username = %s", (username,))
            conn.commit()
            return cur.rowcount == 1
    except mysql.connector.Error as e:
        print(e)
        return False


def register_user(username: str, password: str) -> bool:
    """Registers a new user. Returns True if successful, False if
    username already taken or on error."""
    ensure_profile_schema()
    sql = "INSERT INTO users (username, password, is_active) VALUES (%s, %s, 1)"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (username, password))
            conn.commit()
            return True
    except mysql.connector.Error as e:
        if e.errno == DUPLICATE_ENTRY_ERRNO:
            return False  # duplicate username
        print(e)
        return False


def login_user(username: str, password: str) -> bool:
    """Validates login credentials. Returns True if username + password
    match a record in the DB."""
    ensure_profile_schema()
    sql = "SELECT 1 FROM users WHERE username = %s AND password = %s AND is_active = 1"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (username, password))
            return cur.fetchone() is not None
    except mysql.connector.Error as e:
        print(e)
        return False


def change_password(username: str, old_password: str, new_password: str) -> bool:
    """Change password for an existing user. Returns True if successful."""
    if not login_user(username, old_password):
        return False

    sql = "UPDATE users SET password = %s WHERE username = %s"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (new_password, username))
            conn.commit()
            return cur.rowcount == 1
    except mysql.connector.Error as e:
        print(e)
        return False


def change_username(username: str, new_username: str) -> bool:
    """Change username for an existing user. Returns True if successful,
    False if the new username exists or on error."""
    sql = "UPDATE users SET username = %s WHERE username = %s"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (new_username, username))
            conn.commit()
            rows = cur.rowcount

            if rows == 1:
                # Cascade update: update all related tables.
                # Imported lazily to avoid circular imports.
                import dao.group_dao as group_dao
                import dao.message_dao as message_dao
                import dao.private_message_dao as private_message_dao
                import dao.reaction_dao as reaction_dao

                group_dao.on_username_change(username, new_username)
                message_dao.on_username_change(username, new_username)
                private_message_dao.on_username_change(username, new_username)
                reaction_dao.on_username_change(username, new_username)
                return True
            return False
    except mysql.connector.Error as e:
        if e.errno == DUPLICATE_ENTRY_ERRNO:  # duplicate username key
            return False
        print(e)
        return False
