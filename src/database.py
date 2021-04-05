import asyncpg
import logging
from typing import Optional
from urllib.parse import urlparse
import os

db_conf = urlparse(os.environ['DATABASE'])

logger = logging.getLogger("rcgcdb.database")
# connection: Optional[asyncpg.Connection] = None


class db_connection:
    connection: Optional[asyncpg.Pool] = None

    async def setup_connection(self):
        # Establish a connection to an existing database named "test"
        # as a "postgres" user.
        logger.debug("Setting up the Database connection...")
        self.connection = await asyncpg.create_pool(user=db_conf.username, host=db_conf.hostname,
                                     database=db_conf.path[1:], password=db_conf.password,
                                                    port=5432)
        logger.debug("Database connection established! Connection: {}".format(self.connection))

    async def shutdown_connection(self):
        logger.debug("Shutting down database connection...")
        await self.connection.close()

    def pool(self) -> asyncpg.Pool:
        return self.connection

    # Tried to make it a decorator but tbh won't probably work
    # async def in_transaction(self, func):
    #     async def single_transaction():
    #         async with self.connection.acquire() as connection:
    #             async with connection.transaction():
    #                 await func()
    #     return single_transaction

    # async def query(self, string, *arg):
    #     async with self.connection.acquire() as connection:
    #         async with connection.transaction():
    #             return connection.cursor(string, *arg)


db = db_connection()
