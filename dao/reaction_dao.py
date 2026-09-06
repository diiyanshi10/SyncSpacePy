"""
reaction_dao.py — persistent emoji reactions for messages.
Port of ReactionDAO.java.

Required schema (run once in MySQL):
  CREATE TABLE IF NOT EXISTS message_reactions (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    group_name   VARCHAR(100) NOT NULL,
    message_id   INT NOT NULL,
    emoji        VARCHAR(50) NOT NULL,
    username     VARCHAR(100) NOT NULL,
    reacted_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_reaction (group_name, message_id, emoji, username)
  );

  CREATE TABLE IF NOT EXISTS dm_reactions (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    sender       VARCHAR(100) NOT NULL,
    receiver     VARCHAR(100) NOT NULL,
    message_id   INT NOT NULL,
    emoji        VARCHAR(50) NOT NULL,
    username     VARCHAR(100) NOT NULL,
    reacted_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_dm_reaction (sender, receiver, message_id, emoji, username)
  );
"""
import mysql.connector

from db import get_connection


def toggle_group_reaction(group_name: str, message_id: int, emoji: str, username: str) -> None:
    """Add or remove a reaction. Toggles based on existing row."""
    check_sql = (
        "SELECT 1 FROM message_reactions "
        "WHERE group_name = %s AND message_id = %s AND emoji = %s AND username = %s"
    )
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(check_sql, (group_name, message_id, emoji, username))
            exists = cur.fetchone() is not None

            if exists:
                delete_sql = (
                    "DELETE FROM message_reactions "
                    "WHERE group_name = %s AND message_id = %s AND emoji = %s AND username = %s"
                )
                cur.execute(delete_sql, (group_name, message_id, emoji, username))
            else:
                insert_sql = (
                    "INSERT INTO message_reactions (group_name, message_id, emoji, username) "
                    "VALUES (%s, %s, %s, %s)"
                )
                cur.execute(insert_sql, (group_name, message_id, emoji, username))
            conn.commit()
    except mysql.connector.Error as e:
        print(e)


def get_group_reactions(group_name: str) -> dict:
    """Get all reactions for group messages.
    Returns: {message_id: {emoji: [usernames]}}
    """
    result = {}
    sql = (
        "SELECT message_id, emoji, username FROM message_reactions "
        "WHERE group_name = %s ORDER BY reacted_at ASC"
    )
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (group_name,))
            for msg_id, emoji, user in cur.fetchall():
                result.setdefault(msg_id, {}).setdefault(emoji, []).append(user)
    except mysql.connector.Error as e:
        print(e)
    return result


def toggle_dm_reaction(user1: str, user2: str, message_id: int, emoji: str, username: str) -> None:
    """Toggle DM reaction. Normalizes sender/receiver order."""
    sender, receiver = (user1, user2) if user1 <= user2 else (user2, user1)

    check_sql = (
        "SELECT 1 FROM dm_reactions "
        "WHERE sender = %s AND receiver = %s AND message_id = %s AND emoji = %s AND username = %s"
    )
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(check_sql, (sender, receiver, message_id, emoji, username))
            exists = cur.fetchone() is not None

            if exists:
                delete_sql = (
                    "DELETE FROM dm_reactions "
                    "WHERE sender = %s AND receiver = %s AND message_id = %s AND emoji = %s AND username = %s"
                )
                cur.execute(delete_sql, (sender, receiver, message_id, emoji, username))
            else:
                insert_sql = (
                    "INSERT INTO dm_reactions (sender, receiver, message_id, emoji, username) "
                    "VALUES (%s, %s, %s, %s, %s)"
                )
                cur.execute(insert_sql, (sender, receiver, message_id, emoji, username))
            conn.commit()
    except mysql.connector.Error as e:
        print(e)


def get_dm_reactions(user1: str, user2: str) -> dict:
    """Get all reactions for a DM thread."""
    result = {}
    sender, receiver = (user1, user2) if user1 <= user2 else (user2, user1)

    sql = (
        "SELECT message_id, emoji, username FROM dm_reactions "
        "WHERE sender = %s AND receiver = %s ORDER BY reacted_at ASC"
    )
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (sender, receiver))
            for msg_id, emoji, user in cur.fetchall():
                result.setdefault(msg_id, {}).setdefault(emoji, []).append(user)
    except mysql.connector.Error as e:
        print(e)
    return result


def on_username_change(old_username: str, new_username: str) -> None:
    """Handle username change: update all reactions from old to new username."""
    sql1 = "UPDATE message_reactions SET username = %s WHERE username = %s"
    sql2 = "UPDATE dm_reactions SET username = %s WHERE username = %s"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql1, (new_username, old_username))
            cur.execute(sql2, (new_username, old_username))
            conn.commit()
    except mysql.connector.Error as e:
        print(e)


def clear_group_reactions(group_name: str) -> None:
    sql = "DELETE FROM message_reactions WHERE group_name = %s"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (group_name,))
            conn.commit()
    except mysql.connector.Error as e:
        print(e)


def clear_dm_reactions(user1: str, user2: str) -> None:
    sender, receiver = (user1, user2) if user1 <= user2 else (user2, user1)
    sql = "DELETE FROM dm_reactions WHERE sender = %s AND receiver = %s"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (sender, receiver))
            conn.commit()
    except mysql.connector.Error as e:
        print(e)
