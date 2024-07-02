import aiomysql
import asyncio
from aiomysql.pool import Pool
from utils.alias_logger import logger

from config import MYSQLPORT, MYSQLDATABASE, MYSQLHOST, MYSQLPASSWORD, MYSQLUSER


class MySQLPooling:
    def __init__(self) -> None:
        pass

    async def mysql_connection_pool(self) -> Pool:
        pool = await aiomysql.create_pool(host=MYSQLHOST, port=int(MYSQLPORT), user=MYSQLUSER, password=MYSQLPASSWORD, db=MYSQLDATABASE,
                                          autocommit=False, 
                                          minsize=1, maxsize=10)
        return pool

    async def get_words(self, pool: Pool, offset: int, limit: int):
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(f"select `word` from `alias_schema`.`random_words` limit {limit} offset {offset}")
                    res = await cur.fetchall()
                res = [item[0] for item in res]
                return res
        except aiomysql.Error as e:
            logger.error(f"mysql failed on get words command: {e}")
            raise

mysqlcli = MySQLPooling()

async def main():
    pool = await mysqlcli.mysql_connection_pool()

    words = await mysqlcli.get_words(pool, 100, 100)
    # return print(words)
    return 

if __name__ == "__main__":
    asyncio.run(main())