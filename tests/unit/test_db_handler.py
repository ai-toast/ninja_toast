import pytest
from botocore.stub import Stubber

from service.dal.dynamo_orders_dal_handler import DynamoOrdersDalHandler
from service.schemas.exceptions import InternalServerException


def test_raise_exception():
    db_handler: DynamoOrdersDalHandler = DynamoOrdersDalHandler('table')
    table = db_handler._get_db_handler()
    stubber = Stubber(table.meta.client)
    stubber.add_client_error(method='put_item', service_error_code='ValidationException')
    stubber.activate()
    with pytest.raises(InternalServerException):
        db_handler.create_order_in_db(customer_name='customer', order_item_count=5)
    stubber.deactivate()
    DynamoOrdersDalHandler._instances = {}
