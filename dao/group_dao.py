"""
group_dao.py — group operations + membership management.
Port of GroupDAO.java.

Run this SQL ONCE in MySQL before first run:

  CREATE TABLE IF NOT EXISTS group_members (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    group_name VARCHAR(255) NOT NULL,
    username   VARCHAR(255) NOT NULL,
    joined_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_member (group_name, username)
  );
"""
import mysql.connector

from db import get_connection, DUPLICATE_ENTRY_ERRNO


def create_group(group_name: str, passcode: str, admin_username: str) -> str:
    sql = "INSERT INTO groups_table (group_name, passcode, admin_username) VALUES (%s, %s, %s)"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (group_name, passcode, admin_username))
            conn.commit()
            add_member(group_name, admin_username)
            return "success"
    except mysql.connector.Error as e:
        if e.errno == DUPLICATE_ENTRY_ERRNO:
            return "Group name already exists"
        print(e)
        return "Server error"


def verify_passcode(group_name: str, passcode: str) -> bool:
    sql = "SELECT 1 FROM groups_table WHERE group_name = %s AND passcode = %s"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (group_name, passcode))
            return cur.fetchone() is not None
    except mysql.connector.Error as e:
        print(e)
        return False


def is_member(group_name: str, username: str) -> bool:
    sql = "SELECT 1 FROM group_members WHERE group_name = %s AND username = %s"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (group_name, username))
            return cur.fetchone() is not None
    except mysql.connector.Error as e:
        print(e)
        return False


def add_member(group_name: str, username: str) -> None:
    sql = "INSERT IGNORE INTO group_members (group_name, username) VALUES (%s, %s)"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (group_name, username))
            conn.commit()
    except mysql.connector.Error as e:
        print(e)


def leave_group(group_name: str, username: str) -> str:
    if username == get_admin(group_name):
        return "admin_cannot_leave"
    sql = "DELETE FROM group_members WHERE group_name = %s AND username = %s"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (group_name, username))
            conn.commit()
            return "success"
    except mysql.connector.Error as e:
        print(e)
        return "error"


def remove_member(group_name: str, admin_username: str, target_username: str) -> str:
    if admin_username != get_admin(group_name):
        return "not_admin"
    if admin_username == target_username:
        return "cannot_remove_self"
    sql = "DELETE FROM group_members WHERE group_name = %s AND username = %s"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (group_name, target_username))
            conn.commit()
            return "success"
    except mysql.connector.Error as e:
        print(e)
        return "error"


def get_members(group_name: str) -> list:
    result = []
    sql = "SELECT username FROM group_members WHERE group_name = %s ORDER BY joined_at ASC"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (group_name,))
            result = [row[0] for row in cur.fetchall()]
    except mysql.connector.Error as e:
        print(e)
    return result


def get_groups_for_user(username: str) -> list:
    result = []
    sql = (
        "SELECT gm.group_name FROM group_members gm "
        "JOIN groups_table gt ON gm.group_name = gt.group_name "
        "WHERE gm.username = %s ORDER BY gt.created_at ASC"
    )
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (username,))
            result = [row[0] for row in cur.fetchall()]
    except mysql.connector.Error as e:
        print(e)
    return result


def get_all_groups() -> list:
    result = []
    sql = "SELECT group_name FROM groups_table ORDER BY created_at ASC"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            result = [row[0] for row in cur.fetchall()]
    except mysql.connector.Error as e:
        print(e)
    return result


def get_admin(group_name: str) -> str:
    sql = "SELECT admin_username FROM groups_table WHERE group_name = %s"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (group_name,))
            row = cur.fetchone()
            if row:
                return row[0]
    except mysql.connector.Error as e:
        print(e)
    return ""


def rename_group(old_name: str, new_name: str, admin_username: str) -> str:
    if admin_username != get_admin(old_name):
        return "not_admin"
    sql1 = "UPDATE groups_table SET group_name = %s WHERE group_name = %s"
    sql2 = "UPDATE group_members SET group_name = %s WHERE group_name = %s"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql1, (new_name, old_name))
            cur.execute(sql2, (new_name, old_name))
            conn.commit()
            return "success"
    except mysql.connector.Error as e:
        if e.errno == DUPLICATE_ENTRY_ERRNO:
            return "Group name already exists"
        print(e)
        return "error"


def on_username_change(old_username: str, new_username: str) -> None:
    sql_members = "UPDATE group_members SET username = %s WHERE username = %s"
    sql_admin = "UPDATE groups_table SET admin_username = %s WHERE admin_username = %s"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql_members, (new_username, old_username))
            cur.execute(sql_admin, (new_username, old_username))
            conn.commit()
    except mysql.connector.Error as e:
        print(e)
