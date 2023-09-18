from service.dal.dynamo_users_dal_handler import get_dal_handler
from service.dal.schemas.users_db import UserBase
from service.dal.users_db_handler import UsersDalHandler
from service.handlers.utils.observability import logger, tracer
from service.schemas.input import DeleteUserRequest
from service.schemas.output import DeleteUserOutput


@tracer.capture_method(capture_response=False)
def handle_delete_request(delete_request: DeleteUserRequest, table_name: str) -> DeleteUserOutput:
    logger.info('starting to handle delete user request', extra={
        'user_id': delete_request.user_id,
    })

    dal_handler: UsersDalHandler = get_dal_handler(table_name)
    user: UserBase = dal_handler.delete_user_in_db(delete_request.user_id)
    # convert from db entry to output; might be already deleted or never existed
    return DeleteUserOutput(user_id=user.user_id)
