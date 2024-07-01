from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import TOKEN
import logging
from db.alias_rediscli import RedisConnection
from utils.alias_timer import AliasTimerManager
from db.alias_mysql import MySQLPooling

#Bot configuration
storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)

#Logger configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('alias')

#Database instances
mysqlcli = MySQLPooling()
rediscli = RedisConnection()

mysql_pool = None

#Game timer
timer_manager = AliasTimerManager()