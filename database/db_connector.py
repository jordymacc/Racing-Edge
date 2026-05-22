import os
import sqlite3
from pathlib import Path

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_connection():
    """Returns a database connection - PostgreSQL if available, SQLite fallback"""
    if DATABASE_URL:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        return conn, 'postgres'
    else:
        db_path = Path(__file__).resolve().parent / 'racing.db'
        conn = sqlite3.connect(str(db_path))
        return conn, 'sqlite'

def placeholder(n=1):
    """Returns correct placeholder for the DB type"""
    _, db_type = get_connection()
    if db_type == 'postgres':
        return ','.join(['%s'] * n)
    return ','.join(['?'] * n)
