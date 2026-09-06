"""
db.py — equivalent of DBConnection.java

Opens a fresh MySQL connection per call, mirroring the original
Java DAO pattern of "open connection -> run query -> close".
"""
import mysql.connector
from mysql.connector import errorcode
from mysql.connector import pooling

import config

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="syncspace_pool",
            pool_size=8,
            pool_reset_session=True,
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
        )
    return _pool


def get_connection():
    """Returns a new MySQL connection. Caller is responsible for closing it
    (use as a context manager: `with get_connection() as conn:`)."""
    return _get_pool().get_connection()


# MySQL error code for "duplicate entry" (unique constraint violation).
# Matches e.getErrorCode() == 1062 checks in the original Java code.
DUPLICATE_ENTRY_ERRNO = errorcode.ER_DUP_ENTRY  # 1062
