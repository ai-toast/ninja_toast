from http import HTTPStatus
from typing import Any, Dict, Optional

from aws_lambda_env_modeler import get_environment_variables, init_environment_variables
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.feature_flags.exceptions import ConfigurationStoreError, SchemaValidationError
from aws_lambda_powertools.utilities.parser import ValidationError
from aws_lambda_powertools.utilities.typing import LambdaContext

from service.handlers.schemas.dynamic_configuration import MyConfiguration
from service.handlers.schemas.env_vars import UserGetHandlerEnvVars
from service.handlers.utils.apigw_parser import ApiGatewayEnvelopeExt
from service.handlers.utils.dynamic_configuration import parse_configuration
from service.handlers.utils.http_responses import build_response
from service.handlers.utils.observability import logger, metrics, tracer
from service.logic.users.handle_get_request import handle_get_request
from service.schemas.exceptions import InternalServerException
from service.schemas.input import GetUserRequest
from service.schemas.output import GetUserOutput


@init_environment_variables(model=UserGetHandlerEnvVars)
@metrics.log_metrics
@tracer.capture_lambda_handler(capture_response=False)
def get_user(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    logger.set_correlation_id(context.aws_request_id)

    env_vars: UserGetHandlerEnvVars = get_environment_variables(model=UserGetHandlerEnvVars)
    logger.debug('environment variables', extra=env_vars.model_dump())

    try:
        my_configuration: MyConfiguration = parse_configuration(model=MyConfiguration)  # type: ignore
        logger.debug('fetched dynamic configuration', extra={'configuration': my_configuration.model_dump()})
    except (SchemaValidationError, ConfigurationStoreError) as exc:  # pragma: no cover
        logger.exception(f'dynamic configuration error, error={str(exc)}')
        return build_response(http_status=HTTPStatus.INTERNAL_SERVER_ERROR, body={})

    try:
        # we want to extract and parse the HTTP header from the api gw envelope
        envelope = ApiGatewayEnvelopeExt()
        get_input: GetUserRequest = envelope.parseHeader(data=event, model=GetUserRequest)
        logger.info('got get user request', extra={'user_id': get_input.user_id})
    except (ValidationError, TypeError) as exc:
        logger.error('event failed input validation', extra={'error': str(exc)})
        return build_response(http_status=HTTPStatus.BAD_REQUEST, body={})

    metrics.add_metric(name='ValidDeleteUserEvents', unit=MetricUnit.Count, value=1)
    try:
        response: Optional[GetUserOutput] = handle_get_request(
            get_request=get_input,
            table_name=env_vars.TABLE_NAME,
        )
    except InternalServerException:  # pragma: no cover
        logger.error('finished handling get user request with internal error')
        return build_response(http_status=HTTPStatus.INTERNAL_SERVER_ERROR, body={})

    logger.info('finished handling get user request')
    if response is not None:
        return build_response(http_status=HTTPStatus.OK, body=response.model_dump())
    else:
        return build_response(http_status=HTTPStatus.NOT_FOUND, body={})
