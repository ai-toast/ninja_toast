from service.dal.db_handler import DalHandler
from service.dal.dynamo_dal_handler import get_dal_handler
from service.dal.schemas.db import OrderEntry
from service.handlers.utils.observability import logger, tracer
from service.schemas.input import DeleteOrderRequest
from service.schemas.output import DeleteOrderOutput


@tracer.capture_method(capture_response=False)
def handle_delete_request(delete_request: DeleteOrderRequest, table_name: str) -> DeleteOrderOutput:
    logger.info('starting to handle delete request', extra={
        'order_id': delete_request.order_id,
    })

    dal_handler: DalHandler = get_dal_handler(table_name)
    order: OrderEntry = dal_handler.delete_order_in_db(delete_request.order_id)
    # convert from db entry to output; might be already deleted or never existed
    return DeleteOrderOutput(customer_name=order.customer_name, order_item_count=order.order_item_count, order_id=order.order_id)
