"""
db.py — equivalent of DBConnection.java

Opens a fresh MySQL connection per call, mirroring the original
Java DAO pattern of "open connection -> run query -> close".
"""
import mysql.connector
from mysql.connector import errorcode

import config


def get_connection():
    """Returns a new MySQL connection. Caller is responsible for closing it
    (use as a context manager: `with get_connection() as conn:`)."""
    return mysql.connector.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )


# MySQL error code for "duplicate entry" (unique constraint violation).
# Matches e.getErrorCode() == 1062 checks in the original Java code.
DUPLICATE_ENTRY_ERRNO = errorcode.ER_DUP_ENTRY  # 1062
