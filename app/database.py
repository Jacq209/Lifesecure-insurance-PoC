import os
from contextlib import contextmanager

import pg8000.dbapi
from dotenv import load_dotenv

# Read the values from the .env file in the project root
load_dotenv()


@contextmanager
def get_postgres_connection():
    """Open a PostgreSQL connection for use in a 'with' block.

    - If the block finishes normally, the changes are committed.
    - If an error happens inside the block, the changes are rolled back.
    - The connection is always closed at the end.
    """
    conn = pg8000.dbapi.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def get_postgres_cursor():
    """Give a cursor inside a connection, and close both when done.

    A cursor is the object that sends SQL to the database and reads the results.
    """
    with get_postgres_connection() as conn:
        cur = conn.cursor()
        try:
            yield cur
        finally:
            cur.close()