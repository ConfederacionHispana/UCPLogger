from src.config import settings
import psycopg2
import psycopg2.extras
import os

db_connection = psycopg2.connect(os.environ['DATABASE_URL'])
db_cursor = db_connection.cursor(cursor_factory = psycopg2.extras.DictCursor)
