from service.dal.db_handler import OrdersDalHandler
from service.dal.dynamo_dal_handler import get_dal_handler
from service.dal.schemas.orders_db import OrderBase
from service.handlers.utils.observability import logger, tracer
from service.schemas.input import DeleteOrderRequest
from service.schemas.output import DeleteOrderOutput


@tracer.capture_method(capture_response=False)
def handle_delete_request(delete_request: DeleteOrderRequest, table_name: str) -> DeleteOrderOutput:
    logger.info('starting to handle delete request', extra={
        'order_id': delete_request.order_id,
    })

    dal_handler: OrdersDalHandler = get_dal_handler(table_name)
    order: OrderBase = dal_handler.delete_order_in_db(delete_request.order_id)
    # convert from db entry to output; might be already deleted or never existed
    return DeleteOrderOutput(order_id=order.order_id)
