import json
import uuid
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError
from cachetools import TTLCache, cached
from mypy_boto3_dynamodb import DynamoDBServiceResource
from mypy_boto3_dynamodb.service_resource import Table
from pydantic import ValidationError

from service.dal.db_handler import DalHandler
from service.dal.schemas.db import OrderBase, OrderEntry
from service.handlers.utils.observability import logger, tracer
from service.schemas.exceptions import InternalServerException


class DynamoDalHandler(DalHandler):

    def __init__(self, table_name: str):
        self.table_name = table_name

    # cache dynamodb connection data for no longer than 5 minutes
    @cached(cache=TTLCache(maxsize=1, ttl=300))
    def _get_db_handler(self) -> Table:
        dynamodb: DynamoDBServiceResource = boto3.resource('dynamodb')
        return dynamodb.Table(self.table_name)

    @tracer.capture_method(capture_response=False)
    def create_order_in_db(self, customer_name: str, order_item_count: int) -> OrderEntry:
        order_id = str(uuid.uuid4())
        logger.info('trying to save order', extra={'order_id': order_id})
        try:
            entry = OrderEntry(order_id=order_id, customer_name=customer_name, order_item_count=order_item_count)
            logger.info('opening connection to dynamodb table', extra={'table_name': self.table_name})
            table: Table = self._get_db_handler()
            table.put_item(Item=entry.model_dump())
        except (ClientError, ValidationError) as exc:
            error_msg = 'failed to create order'
            logger.exception(error_msg, extra={'exception': str(exc), 'customer_name': customer_name})
            raise InternalServerException(error_msg) from exc

        logger.info('finished create order', extra={'order_id': order_id, 'order_item_count': order_item_count, 'customer_name': customer_name})
        return entry

    @tracer.capture_method(capture_response=False)
    def delete_order_in_db(self, order_id: str) -> OrderEntry:
        logger.info('trying to delete order', extra={'order_id': order_id})
        try:
            entry = OrderBase(order_id=order_id)
            logger.info('opening connection to dynamodb table', extra={'table_name': self.table_name})
            table: Table = self._get_db_handler()
            response = table.delete_item(Key=entry.model_dump())
            rec = OrderEntry.model_validate_json(json.dumps(response['Attributes']))
        except (ClientError, ValidationError) as exc:
            error_msg = 'failed to delete order'
            logger.exception(error_msg, extra={'exception': str(exc), 'order_id': order_id})
            raise InternalServerException(error_msg) from exc

        logger.info('finished delete order', extra={'order_id': order_id})
        return rec

    @tracer.capture_method(capture_response=False)
    def get_order_in_db(self, order_id: str) -> OrderEntry:
        logger.info('trying to retrieve order', extra={'order_id': order_id})
        try:
            entry = OrderBase(order_id=order_id)
            logger.info('opening connection to dynamodb table', extra={'table_name': self.table_name})
            table: Table = self._get_db_handler()
            response = table.get_item(Key=entry.model_dump())
            rec = OrderEntry.model_validate_json(json.dumps(response['Item']))

        except (ClientError, ValidationError) as exc:
            error_msg = 'failed to get order'
            logger.exception(error_msg, extra={'exception': str(exc), 'order_id': order_id})
            raise InternalServerException(error_msg) from exc

        logger.info('finished get order', extra={
            'order_id': rec.order_id,
            'order_item_count': rec.order_item_count,
            'customer_name': rec.customer_name
        })
        return rec


@lru_cache
def get_dal_handler(table_name: str) -> DalHandler:
    return DynamoDalHandler(table_name)
