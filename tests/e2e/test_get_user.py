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
    create_inputs = CreateUserRequest(user_name=user_name, email=email)
    response_create = requests.post(api_gw_url, data=create_inputs.model_dump_json())
    assert response_create.status_code == HTTPStatus.OK
    rec_created = json.loads(response_create.text)
    assert rec_created['user_id']
    assert rec_created['user_name'] == user_name
    assert rec_created['email'] == email

    # get the user
    user_id = rec_created['user_id']
    response = requests.get(api_gw_url, headers={'user_id': user_id})
    assert response.status_code == HTTPStatus.OK
    body = json.loads(response.text)
    assert body['user_id']
    assert body['user_name'] == user_name
    assert body['email'] == email


def test_handler_bad_request(api_gw_url):
    user_id = f'non-uuid-string-{generate_random_string()}'
    response = requests.get(api_gw_url, headers={'user_id': user_id})
    assert response.status_code == HTTPStatus.BAD_REQUEST
    body_dict = json.loads(response.text)
    assert body_dict == {}


def test_handler_not_found(api_gw_url):
    user_id = '1bc634f1-3a11-41e8-a0a2-58da4717fb7b'
    response = requests.get(api_gw_url, headers={'user_id': user_id})
    assert response.status_code == HTTPStatus.NOT_FOUND
    body_dict = json.loads(response.text)
    assert body_dict == {}
