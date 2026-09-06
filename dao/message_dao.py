"""
message_dao.py — handles group chat messages in MySQL.
Port of MessageDAO.java.

Required schema (run once):
  CREATE TABLE IF NOT EXISTS messages (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    group_name VARCHAR(255) NOT NULL,
    sender    VARCHAR(255) NOT NULL,
    message   LONGTEXT NOT NULL,
    sent_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
"""
import mysql.connector

from db import get_connection


def get_messages(group_name: str) -> list:
    """Fetches last 50 messages for a group, formatted as 'username: message'."""
    messages = []
    sql = (
        "SELECT sender, message FROM messages "
        "WHERE group_name = %s ORDER BY sent_at ASC LIMIT 50"
    )
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (group_name,))
            messages = [f"{sender}: {message}" for sender, message in cur.fetchall()]
    except mysql.connector.Error as e:
        print(e)
    return messages


def get_messages_with_ids(group_name: str) -> list:
    """Get messages with IDs for reaction mapping.
    Returns a list of dicts: [{"id": N, "sender": "user", "message": "text"}, ...]
    """
    result = []
    sql = (
        "SELECT id, sender, message FROM messages "
        "WHERE group_name = %s ORDER BY sent_at ASC LIMIT 50"
    )
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (group_name,))
            for msg_id, sender, message in cur.fetchall():
                result.append({"id": msg_id, "sender": sender, "message": message})
    except mysql.connector.Error as e:
        print(e)
    return result


def save_message(group_name: str, sender: str, message: str) -> None:
    """Saves a new message to the database."""
    sql = "INSERT INTO messages (group_name, sender, message) VALUES (%s, %s, %s)"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (group_name, sender, message))
            conn.commit()
    except mysql.connector.Error as e:
        print(e)


def on_username_change(old_username: str, new_username: str) -> None:
    """Handle username change in group messages."""
    sql = "UPDATE messages SET sender = %s WHERE sender = %s"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (new_username, old_username))
            conn.commit()
    except mysql.connector.Error as e:
        print(e)


def clear_group_messages(group_name: str) -> None:
    sql = "DELETE FROM messages WHERE group_name = %s"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (group_name,))
            conn.commit()
    except mysql.connector.Error as e:
        print(e)
