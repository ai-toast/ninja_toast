from http import HTTPStatus
from typing import Any, Dict

from aws_lambda_env_modeler import get_environment_variables, init_environment_variables
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.feature_flags.exceptions import ConfigurationStoreError, SchemaValidationError
from aws_lambda_powertools.utilities.parser import ValidationError
from aws_lambda_powertools.utilities.typing import LambdaContext

from service.handlers.schemas.dynamic_configuration import MyConfiguration
from service.handlers.schemas.env_vars import OrderGetHandlerEnvVars
from service.handlers.utils.apigw_parser import ApiGatewayEnvelopeExt
from service.handlers.utils.dynamic_configuration import parse_configuration
from service.handlers.utils.http_responses import build_response
from service.handlers.utils.observability import logger, metrics, tracer
from service.logic.handle_get_request import handle_get_request
from service.schemas.exceptions import InternalServerException
from service.schemas.input import GetOrderRequest
from service.schemas.output import GetOrderOutput


@init_environment_variables(model=OrderGetHandlerEnvVars)
@metrics.log_metrics
@tracer.capture_lambda_handler(capture_response=False)
def get_order(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    logger.set_correlation_id(context.aws_request_id)

    env_vars: OrderGetHandlerEnvVars = get_environment_variables(model=OrderGetHandlerEnvVars)
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
        get_input: GetOrderRequest = envelope.parseHeader(data=event, model=GetOrderRequest)
        logger.info('got get order request', extra={'order_id': get_input.order_id})
    except (ValidationError, TypeError) as exc:
        logger.error('event failed input validation', extra={'error': str(exc)})
        return build_response(http_status=HTTPStatus.BAD_REQUEST, body={})

    metrics.add_metric(name='ValidDeleteOrderEvents', unit=MetricUnit.Count, value=1)
    try:
        response: GetOrderOutput = handle_get_request(
            get_request=get_input,
            table_name=env_vars.TABLE_NAME,
        )
    except InternalServerException:  # pragma: no cover
        logger.error('finished handling get order request with internal error')
        return build_response(http_status=HTTPStatus.INTERNAL_SERVER_ERROR, body={})

    logger.info('finished handling get order request')
    return build_response(http_status=HTTPStatus.OK, body=response.model_dump())
