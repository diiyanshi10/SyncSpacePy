"""
private_message_dao.py — handles direct messages between two users.
Port of PrivateMessageDAO.java.

Required schema (run once):
  CREATE TABLE IF NOT EXISTS private_messages (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    sender    VARCHAR(255) NOT NULL,
    receiver  VARCHAR(255) NOT NULL,
    message   LONGTEXT NOT NULL,
    sent_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
"""
import mysql.connector

from db import get_connection


def save_private_message(sender: str, receiver: str, message: str) -> None:
    """Save a DM from sender to receiver."""
    sql = "INSERT INTO private_messages (sender, receiver, message) VALUES (%s, %s, %s)"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (sender, receiver, message))
            conn.commit()
    except mysql.connector.Error as e:
        print(e)


def get_private_messages(user1: str, user2: str) -> list:
    """Get full conversation between two users (both directions)."""
    messages = []
    sql = (
        "SELECT sender, message FROM private_messages "
        "WHERE (sender = %s AND receiver = %s) OR (sender = %s AND receiver = %s) "
        "ORDER BY sent_at ASC LIMIT 100"
    )
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (user1, user2, user2, user1))
            messages = [f"{sender}: {message}" for sender, message in cur.fetchall()]
    except mysql.connector.Error as e:
        print(e)
    return messages


def get_private_messages_with_ids(user1: str, user2: str) -> list:
    """Get messages with IDs for reaction mapping."""
    result = []
    sql = (
        "SELECT id, sender, message, sent_at FROM private_messages "
        "WHERE (sender = %s AND receiver = %s) OR (sender = %s AND receiver = %s) "
        "ORDER BY sent_at ASC LIMIT 100"
    )
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (user1, user2, user2, user1))
            for msg_id, sender, message, sent_at in cur.fetchall():
                result.append({"id": msg_id, "sender": sender, "message": message, "sent_at": sent_at.isoformat() if sent_at else None})
    except mysql.connector.Error as e:
        print(e)
    return result


def get_chat_contacts(username: str) -> list:
    """Get all users this person has had a conversation with."""
    contacts = []
    sql = (
        "SELECT DISTINCT CASE WHEN sender = %s THEN receiver ELSE sender END AS contact "
        "FROM private_messages WHERE sender = %s OR receiver = %s"
    )
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (username, username, username))
            contacts = [row[0] for row in cur.fetchall()]
    except mysql.connector.Error as e:
        print(e)
    return contacts


def get_all_users(except_username: str) -> list:
    """Get all registered users except the current user (for starting new DMs)."""
    users = []
    sql = "SELECT username FROM users WHERE username != %s ORDER BY username ASC"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (except_username,))
            users = [row[0] for row in cur.fetchall()]
    except mysql.connector.Error as e:
        print(e)
    return users


def on_username_change(old_username: str, new_username: str) -> None:
    """Handle username change: update sender and receiver fields."""
    sql1 = "UPDATE private_messages SET sender = %s WHERE sender = %s"
    sql2 = "UPDATE private_messages SET receiver = %s WHERE receiver = %s"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql1, (new_username, old_username))
            cur.execute(sql2, (new_username, old_username))
            conn.commit()
    except mysql.connector.Error as e:
        print(e)


def clear_direct_messages(user1: str, user2: str) -> None:
    sql = (
        "DELETE FROM private_messages "
        "WHERE (sender = %s AND receiver = %s) OR (sender = %s AND receiver = %s)"
    )
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (user1, user2, user2, user1))
            conn.commit()
    except mysql.connector.Error as e:
        print(e)


def get_dm_contacts(username: str) -> dict:
    contacts = {}
    sql = (
        "SELECT CASE WHEN sender = %s THEN receiver ELSE sender END AS contact, MAX(id) AS last_id "
        "FROM private_messages WHERE sender = %s OR receiver = %s GROUP BY contact"
    )
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (username, username, username))
            for contact, last_id in cur.fetchall():
                contacts[contact] = last_id
    except mysql.connector.Error as e:
        print(e)
    return contacts
