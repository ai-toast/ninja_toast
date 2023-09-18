from service.dal.dynamo_users_dal_handler import get_dal_handler
from service.dal.schemas.users_db import UserEntry
from service.dal.users_db_handler import UsersDalHandler
from service.handlers.utils.observability import logger, tracer
from service.schemas.input import CreateUserRequest
from service.schemas.output import CreateUserOutput


@tracer.capture_method(capture_response=False)
def handle_create_request(user_request: CreateUserRequest, table_name: str) -> CreateUserOutput:
    logger.info('starting to handle create user request', extra={
        'user_name': user_request.user_name,
        'email': user_request.email,
    })

    dal_handler: UsersDalHandler = get_dal_handler(table_name)
    user: UserEntry = dal_handler.create_user_in_db(user_name=user_request.user_name, email=user_request.email)
    # convert from db entry to output, they won't always be the same
    return CreateUserOutput(user_name=user.user_name, email=user.email, user_id=user.user_id)
