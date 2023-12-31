from typing import Optional

from service.dal.dynamo_orders_dal_handler import get_dal_handler
from service.dal.orders_db_handler import OrdersDalHandler
from service.dal.schemas.orders_db import OrderEntry
from service.handlers.utils.observability import logger, tracer
from service.schemas.input import GetOrderRequest
from service.schemas.output import GetOrderOutput


@tracer.capture_method(capture_response=False)
def handle_get_request(get_request: GetOrderRequest, table_name: str) -> Optional[GetOrderOutput]:
    logger.info('starting to handle get request', extra={
        'order_id': get_request.order_id,
    })

    dal_handler: OrdersDalHandler = get_dal_handler(table_name)
    order: Optional[OrderEntry] = dal_handler.get_order_in_db(get_request.order_id)
    if order is not None:
        # convert from db entry to output;
        return GetOrderOutput(customer_name=order.customer_name, order_item_count=order.order_item_count, order_id=order.order_id)
    else:
        return None
