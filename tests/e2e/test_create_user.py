import json
from http import HTTPStatus

import pytest
import requests

from cdk.service.constants import USERS_APIGATEWAY, USERS_GW_RESOURCE
from service.schemas.input import CreateUserRequest
from tests.utils import generate_random_string, get_stack_output


@pytest.fixture(scope='module', autouse=True)
def api_gw_url():
    return f'{get_stack_output(USERS_APIGATEWAY)}api/{USERS_GW_RESOURCE}'


def test_handler_200_ok(api_gw_url):
    user_name = f'{generate_random_string()}-RanTheBuilder'
    email = 'helo@world.com'
    body = CreateUserRequest(user_name=user_name, email=email)
    response = requests.post(api_gw_url, data=body.model_dump_json())
    assert response.status_code == HTTPStatus.OK
    body_dict = json.loads(response.text)
    assert body_dict['user_id']
    assert body_dict['user_name'] == user_name
    assert body_dict['email'] == email

    # check idempotency, send same request
    original_user_id = body_dict['user_id']
    response = requests.post(api_gw_url, data=body.model_dump_json())
    assert response.status_code == HTTPStatus.OK
    body_dict = json.loads(response.text)
    assert body_dict['user_id'] == original_user_id


def test_handler_bad_request(api_gw_url):
    body_str = json.dumps({'email': 'some dumb email'})
    response = requests.post(api_gw_url, data=body_str)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    body_dict = json.loads(response.text)
    assert body_dict == {}
