import json
from http import HTTPStatus

import pytest
import requests

from cdk.service.constants import ORDERS_APIGATEWAY, ORDERS_GW_RESOURCE
from service.schemas.input import CreateOrderRequest, DeleteOrderRequest
from tests.utils import generate_random_string, get_stack_output


@pytest.fixture(scope='module', autouse=True)
def api_gw_url():
    return f'{get_stack_output(ORDERS_APIGATEWAY)}api/{ORDERS_GW_RESOURCE}'


def test_handler_200_ok(api_gw_url):
    customer_name = f'{generate_random_string()}-RanTheBuilder'
    create_inputs = CreateOrderRequest(customer_name=customer_name, order_item_count=5)
    response_create = requests.post(api_gw_url, data=create_inputs.model_dump_json())
    assert response_create.status_code == HTTPStatus.OK
    rec_created = json.loads(response_create.text)
    assert rec_created['order_id']
    assert rec_created['customer_name'] == customer_name
    assert rec_created['order_item_count'] == 5

    # delete the order
    order_id = rec_created['order_id']
    inputs = DeleteOrderRequest(order_id=order_id)
    response = requests.delete(api_gw_url, data=inputs.model_dump_json())
    assert response.status_code == HTTPStatus.OK
    body = json.loads(response.text)
    assert body['order_id']
    assert body['order_id'] == order_id

    # assert failing to get the order
    response_get = requests.get(api_gw_url, headers={'order_id': order_id})
    assert response_get.status_code == HTTPStatus.NOT_FOUND


def test_handler_bad_request(api_gw_url):
    order_id = f'non-uuid-string-{generate_random_string()}'
    response = requests.post(api_gw_url, data=json.dumps({'order_id': order_id}))
    assert response.status_code == HTTPStatus.BAD_REQUEST
    body_dict = json.loads(response.text)
    assert body_dict == {}
