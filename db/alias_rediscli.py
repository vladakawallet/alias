from typing import Any
import redis.asyncio
import redis.client
import redis.asyncio as redis
import json
import logging
from redis.exceptions import RedisError
from utils.alias_logger import logger

class RedisConnection:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(RedisConnection, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.pool = redis.ConnectionPool(max_connections=100).from_url("redis://localhost")
        self.redis_logger = logging.getLogger(__name__)
        self.redis_logger.setLevel(logging.INFO)

    async def get_redis_connection(self) -> redis.Redis:
        try:
            self.r = redis.Redis(connection_pool=self.pool)
            return self.r
        except RedisError as e:
            logger.error(f"failed to get RedisClient: {e}")
            raise
        
    def encode_data(self, data: dict):
        return {k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in data.items()}

    def decode_data(self, data: dict):
        return {k.decode('utf-8'): json.loads(v) if k.decode('utf-8') in ['players', 'teams', 'words'] else v.decode('utf-8') for k, v in data.items()}

 
    async def init_session(self, chat_id):
        try:
            r = await self.get_redis_connection()
            session_data = {
                'session_id': chat_id,
                'players': [],
                'teams': {},
                'words': [],
                'main_state': '',
                'result_message': '',
                'start_message': '',
                'teams_message': '',
                'timer_message': '',
                'string': "",
                'timer_state': '',
                'timer_task': '',
                'timer': 90,
                'win_score': 15,
                'turn': 0,
                'offset': 0
            }
            
            for k, v in session_data.items():
                if isinstance(v, (dict, list)):
                    v = json.dumps(v)
                await r.hset(chat_id, k, v)
        # except Exception as e:
            # self.redis_logger.error(e)
            # raise RedisError(f"Failed to init a session on {chat_id}")
        except RedisError as e:
            logger.error(f"failed to init a session: {e}")
            raise

    async def check_existed_session(self, chat_id: str | int):
        r = await self.get_redis_connection()
        try:
            existing = await r.hexists(chat_id, "session_id")
            return existing
        except RedisError as e:
            logger.error(f"failed to check existing session: {e}")
            raise
        
    async def delete_session(self, chat_id: int | str):
        r = await self.get_redis_connection()
        try:
            await r.delete(chat_id)
        except RedisError as e:
            logger.error(f"failed to delete a session: {e}")
            raise

    async def get_session_data(self, chat_id: str | int):
        r = await self.get_redis_connection()
        try:
            data = await r.hgetall(chat_id)
            return self.decode_data(data)
        # except Exception as e:
            # self.redis_logger.error(e)
            # raise RedisError(f"Failed to get session data on {chat_id}")
        except RedisError as e:
            logger.error(f"failed to get session data: {e}")
            raise

        
    async def get_session_field(self, chat_id: str | int, field: str):
        r = await self.get_redis_connection()
        try:
            field_data = await r.hget(chat_id, field)
            if field_data:
                try: 
                    return json.loads(field_data) if field in ['players', 'teams', 'words'] else field_data.decode('utf-8')
                except AttributeError:
                    return field_data
            else:
                return ''
        # except Exception as e:
            # self.redis_logger.error(e)
            # raise RedisError(f"Failed to get session field on {chat_id}")
        except RedisError as e:
            logger.error(f"failed to get session field: {e}")
            raise


    async def update_session_data(self, chat_id: str | int, data: dict):
        r = await self.get_redis_connection()
        encoded_data = self.encode_data(data)
        try:
            await r.hset(chat_id, mapping=encoded_data)
        # except Exception as e:
            # self.redis_logger.error(e)
            # raise RedisError(f"Failed to update session data on {chat_id}")
        except RedisError as e:
            logger.error(f"failed to update session data: {e}")
            raise

    async def update_session_field(self, chat_id: str | int, field: str, value: Any):
        r = await self.get_redis_connection()
        encoded_value = json.loads(value) if isinstance(value, (dict, list)) else value
        try:
            await r.hset(chat_id, field, encoded_value)
        # except Exception as e:
            # self.redis_logger.error(e)
            # raise RedisError(f"Failed to update session field on {chat_id}")
        except RedisError as e:
            logger.error(f"failed to update session field: {e}")
            raise


    async def add_session_player(self, chat_id: str | int, player: list):
        session_data = await self.get_session_data(chat_id)
        session_data["players"].append(player)
        await self.update_session_data(chat_id, session_data)

    async def add_session_team(self, chat_id: str | int, team: str):
        session_data = await self.get_session_data(chat_id)
        session_data["teams"][team] = {
            "members": [],
            "score": 0
        }
        await self.update_session_data(chat_id, session_data)

    async def redis_set_pipeline(self, chat_id: str | int, data: dict):
        try:
            r = await self.get_redis_connection()
            async with r.pipeline() as pipe:
                for key, value in data.items():
                    if isinstance(value, (list, dict)):
                        value = json.dumps(value)
                    await pipe.hset(chat_id, key, value)
                await pipe.execute()
        except RedisError as e:
            logger.error(f"failed to set a pipeline: {e}")
            raise

    async def redis_get_pipeline(self, chat_id: str | int, fields: list):
        try:
            r = await self.get_redis_connection()
            async with r.pipeline() as pipe:
                for field in fields:
                    await pipe.hget(chat_id, field)
                    
                results = await pipe.execute()
            res = {}
            for field, field_data in zip(fields, results):
                if field_data:
                    try:
                        decoded_data = json.loads(field_data) if field in ['players', 'teams', 'words'] else field_data.decode('utf-8')
                    except AttributeError:
                        decoded_data = field_data
                    res[field] = decoded_data
                else:
                    res[field] = ''
            return res
        except RedisError as e:
            logger.error(f"failed to get a pipeline: {e}")
            raise
