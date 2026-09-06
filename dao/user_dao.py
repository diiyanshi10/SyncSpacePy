"""
user_dao.py — handles user registration and login against MySQL.
Port of UserDAO.java.
"""
import mysql.connector

from db import get_connection, DUPLICATE_ENTRY_ERRNO


def register_user(username: str, password: str) -> bool:
    """Registers a new user. Returns True if successful, False if
    username already taken or on error."""
    sql = "INSERT INTO users (username, password) VALUES (%s, %s)"
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
    sql = "SELECT 1 FROM users WHERE username = %s AND password = %s"
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
