import uuid
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError
from cachetools import TTLCache, cached
from mypy_boto3_dynamodb import DynamoDBServiceResource
from mypy_boto3_dynamodb.service_resource import Table
from pydantic import ValidationError

from service.dal.schemas.users_db import UserBase, UserEntry
from service.dal.users_db_handler import UsersDalHandler
from service.handlers.utils.observability import logger, tracer
from service.schemas.exceptions import InternalServerException


class DynamoUsersDalHandler(UsersDalHandler):

    def __init__(self, table_name: str):
        self.table_name = table_name

    # cache dynamodb connection data for no longer than 5 minutes
    @cached(cache=TTLCache(maxsize=1, ttl=300))
    def _get_db_handler(self) -> Table:
        dynamodb: DynamoDBServiceResource = boto3.resource('dynamodb')
        return dynamodb.Table(self.table_name)

    @tracer.capture_method(capture_response=False)
    def create_user_in_db(self, user_name: str, email: str) -> UserEntry:
        user_id = str(uuid.uuid4())
        logger.info('trying to save user', extra={'user_id': user_id})
        try:
            entry = UserEntry(user_id=user_id, user_name=user_name, email=email)
            logger.info('opening connection to dynamodb table', extra={'table_name': self.table_name})
            table: Table = self._get_db_handler()
            table.put_item(Item=entry.model_dump())
        except (ClientError, ValidationError) as exc:
            error_msg = 'failed to create user'
            logger.exception(error_msg, extra={'exception': str(exc), 'user_name': user_name})
            raise InternalServerException(error_msg) from exc

        logger.info('finished create user', extra={'user_id': user_id, 'user_name': user_name, 'email': email})
        return entry

    @tracer.capture_method(capture_response=False)
    def delete_user_in_db(self, user_id: str) -> UserBase:
        logger.info('trying to delete user', extra={'user_id': user_id})
        try:
            entry = UserBase(user_id=user_id)
            logger.info('opening connection to dynamodb table', extra={'table_name': self.table_name})
            table: Table = self._get_db_handler()

            key = entry.model_dump()
            logger.debug('DDB user Key', extra={'key': key})
            response = table.delete_item(Key=key)
            logger.debug('DELETE user ddb Response', extra={'response': response})
            rec = UserBase(user_id=user_id)

        except (ClientError, ValidationError) as exc:
            error_msg = 'failed to delete user'
            logger.exception(error_msg, extra={'exception': str(exc), 'user_id': user_id})
            raise InternalServerException(error_msg) from exc

        logger.info('finished delete user', extra={'user_id': user_id})
        return rec

    @tracer.capture_method(capture_response=False)
    def get_user_in_db(self, user_id: str) -> UserEntry:
        logger.info('trying to retrieve user', extra={'user_id': user_id})
        try:
            entry = UserBase(user_id=user_id)
            logger.info('opening connection to dynamodb table', extra={'table_name': self.table_name})
            table: Table = self._get_db_handler()
            key = entry.model_dump()
            logger.debug('DDB user Key', extra={'key': key})
            response = table.get_item(Key=key)
            logger.debug('GET user ddb Response', extra={'response': response})
            if 'Item' in response:
                logger.debug('GET user ddb Response.Item', extra={'item': response['Item']})
                rec = UserEntry.model_validate(response['Item'])
                logger.info('finished get user', extra={'user_id': rec.user_id, 'email': rec.email, 'customer_name': rec.user_name})
            else:
                logger.info(f'user {user_id} not found')
                rec = None

        except (ClientError, ValidationError) as exc:
            error_msg = 'failed to get user'
            logger.exception(error_msg, extra={'exception': str(exc), 'user_id': user_id})
            raise InternalServerException(error_msg) from exc

        return rec


@lru_cache
def get_dal_handler(table_name: str) -> UsersDalHandler:
    return DynamoUsersDalHandler(table_name)
