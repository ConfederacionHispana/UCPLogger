from src.config import settings
from urllib.parse import urlparse
import pymysql
import os

db_conf = urlparse(os.environ['DATABASE_URL'])

db_connection = pymysql.connect(
    host=db_conf.hostname,
    user=db_conf.username,
    password=db_conf.password,
    database=db_conf.path[1:]
)

db_cursor = db_connection.cursor(pymysql.cursors.DictCursor)
