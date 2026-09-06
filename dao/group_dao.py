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

_schema_ready = False


def ensure_group_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return
    group_columns = {
        "visibility": "VARCHAR(20) NOT NULL DEFAULT 'private'",
        "description": "VARCHAR(255) NULL",
        "avatar": "VARCHAR(32) NULL",
        "archived": "TINYINT(1) NOT NULL DEFAULT 0",
    }
    member_columns = {"role": "VARCHAR(20) NOT NULL DEFAULT 'user'"}
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SHOW COLUMNS FROM groups_table")
            existing_groups = {row[0] for row in cur.fetchall()}
            for name, definition in group_columns.items():
                if name not in existing_groups:
                    cur.execute(f"ALTER TABLE groups_table ADD COLUMN {name} {definition}")
            cur.execute("SHOW COLUMNS FROM group_members")
            existing_members = {row[0] for row in cur.fetchall()}
            for name, definition in member_columns.items():
                if name not in existing_members:
                    cur.execute(f"ALTER TABLE group_members ADD COLUMN {name} {definition}")
            cur.execute("""UPDATE group_members gm
                JOIN groups_table gt ON gm.group_name = gt.group_name
                SET gm.role = 'admin' WHERE gm.username = gt.admin_username""")
            cur.execute("""CREATE TABLE IF NOT EXISTS group_join_requests (
                id INT AUTO_INCREMENT PRIMARY KEY,
                group_name VARCHAR(255) NOT NULL,
                username VARCHAR(255) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_request (group_name, username)
            )""")
            conn.commit()
            _schema_ready = True
    except mysql.connector.Error as e:
        print(e)


def create_group(group_name: str, passcode: str, admin_username: str, visibility="private", description="", avatar="") -> str:
    ensure_group_schema()
    sql = ("INSERT INTO groups_table (group_name, passcode, admin_username, visibility, description, avatar) "
           "VALUES (%s, %s, %s, %s, %s, %s)")
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (group_name, passcode, admin_username, visibility, description, avatar))
            conn.commit()
            add_member(group_name, admin_username)
            set_role(group_name, admin_username, "admin")
            return "success"
    except mysql.connector.Error as e:
        if e.errno == DUPLICATE_ENTRY_ERRNO:
            return "Group name already exists"
        print(e)
        return "Server error"


def verify_passcode(group_name: str, passcode: str) -> bool:
    ensure_group_schema()
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
    ensure_group_schema()
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
    ensure_group_schema()
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
    ensure_group_schema()
    result = []
    sql = "SELECT username, role FROM group_members WHERE group_name = %s ORDER BY joined_at ASC"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (group_name,))
            result = [{"username": row[0], "role": row[1]} for row in cur.fetchall()]
    except mysql.connector.Error as e:
        print(e)
    return result


def get_groups_for_user(username: str) -> list:
    ensure_group_schema()
    result = []
    sql = (
        "SELECT gm.group_name FROM group_members gm "
        "JOIN groups_table gt ON gm.group_name = gt.group_name "
        "WHERE gm.username = %s AND gt.archived = 0 ORDER BY gt.created_at ASC"
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
    ensure_group_schema()
    result = []
    sql = "SELECT group_name FROM groups_table WHERE archived = 0 AND visibility = 'public' ORDER BY created_at ASC"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            result = [row[0] for row in cur.fetchall()]
    except mysql.connector.Error as e:
        print(e)
    return result


def get_admin(group_name: str) -> str:
    ensure_group_schema()
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
    ensure_group_schema()
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


def get_group(group_name: str) -> dict | None:
    ensure_group_schema()
    try:
        with get_connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT group_name, admin_username, visibility, description, avatar, archived FROM groups_table WHERE group_name = %s", (group_name,))
            return cur.fetchone()
    except mysql.connector.Error as e:
        print(e)
        return None


def set_role(group_name: str, username: str, role: str) -> bool:
    ensure_group_schema()
    if role not in {"admin", "moderator", "user"}:
        return False
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE group_members SET role = %s WHERE group_name = %s AND username = %s", (role, group_name, username))
            conn.commit()
            return cur.rowcount == 1
    except mysql.connector.Error as e:
        print(e)
        return False


def can_manage(group_name: str, username: str) -> bool:
    if username == get_admin(group_name):
        return True
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT role FROM group_members WHERE group_name = %s AND username = %s", (group_name, username))
            row = cur.fetchone()
            return bool(row and row[0] in {"admin", "moderator"})
    except mysql.connector.Error as e:
        print(e)
        return False


def request_join(group_name: str, username: str) -> str:
    ensure_group_schema()
    if is_member(group_name, username):
        return "already_member"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO group_join_requests (group_name, username) VALUES (%s, %s) ON DUPLICATE KEY UPDATE status = 'pending'", (group_name, username))
            conn.commit()
            return "success"
    except mysql.connector.Error as e:
        print(e)
        return "error"


def get_join_requests(group_name: str) -> list:
    ensure_group_schema()
    try:
        with get_connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT username, requested_at FROM group_join_requests WHERE group_name = %s AND status = 'pending' ORDER BY requested_at ASC", (group_name,))
            return cur.fetchall()
    except mysql.connector.Error as e:
        print(e)
        return []


def approve_join(group_name: str, username: str, admin_username: str, approve: bool) -> str:
    if admin_username != get_admin(group_name):
        return "not_admin"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE group_join_requests SET status = %s WHERE group_name = %s AND username = %s AND status = 'pending'", ("approved" if approve else "rejected", group_name, username))
            if approve and cur.rowcount:
                cur.execute("INSERT IGNORE INTO group_members (group_name, username, role) VALUES (%s, %s, 'user')", (group_name, username))
            conn.commit()
            return "success" if cur.rowcount or approve else "not_found"
    except mysql.connector.Error as e:
        print(e)
        return "error"


def archive_group(group_name: str, admin_username: str, archived: bool) -> str:
    if admin_username != get_admin(group_name):
        return "not_admin"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE groups_table SET archived = %s WHERE group_name = %s", (1 if archived else 0, group_name))
            conn.commit()
            return "success" if cur.rowcount == 1 else "not_found"
    except mysql.connector.Error as e:
        print(e)
        return "error"


def delete_group(group_name: str, admin_username: str) -> str:
    if admin_username != get_admin(group_name):
        return "not_admin"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM group_join_requests WHERE group_name = %s", (group_name,))
            cur.execute("DELETE FROM group_members WHERE group_name = %s", (group_name,))
            cur.execute("DELETE FROM groups_table WHERE group_name = %s", (group_name,))
            conn.commit()
            return "success" if cur.rowcount == 1 else "not_found"
    except mysql.connector.Error as e:
        print(e)
        return "error"
