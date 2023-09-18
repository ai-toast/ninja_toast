from typing import Optional

from service.dal.dynamo_users_dal_handler import get_dal_handler
from service.dal.schemas.users_db import UserEntry
from service.dal.users_db_handler import UsersDalHandler
from service.handlers.utils.observability import logger, tracer
from service.schemas.input import GetUserRequest
from service.schemas.output import GetUserOutput


@tracer.capture_method(capture_response=False)
def handle_get_request(get_request: GetUserRequest, table_name: str) -> Optional[GetUserOutput]:
    logger.info('starting to handle get user request', extra={
        'user_id': get_request.user_id,
    })

    dal_handler: UsersDalHandler = get_dal_handler(table_name)
    user: Optional[UserEntry] = dal_handler.get_user_in_db(get_request.user_id)
    if user is not None:
        # convert from db entry to output;
        return GetUserOutput(user_name=user.user_name, email=user.email, user_id=user.user_id)
    else:
        return None
