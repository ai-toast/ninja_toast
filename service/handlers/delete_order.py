from http import HTTPStatus
from typing import Any, Dict

from aws_lambda_env_modeler import get_environment_variables, init_environment_variables
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.feature_flags.exceptions import ConfigurationStoreError, SchemaValidationError
from aws_lambda_powertools.utilities.parser import ValidationError, parse
from aws_lambda_powertools.utilities.parser.envelopes import ApiGatewayEnvelope
from aws_lambda_powertools.utilities.typing import LambdaContext

from service.handlers.schemas.dynamic_configuration import MyConfiguration
from service.handlers.schemas.env_vars import MyHandlerEnvVars
from service.handlers.utils.dynamic_configuration import parse_configuration
from service.handlers.utils.http_responses import build_response
from service.handlers.utils.observability import logger, metrics, tracer
from service.logic.handle_delete_request import handle_delete_request
from service.schemas.exceptions import InternalServerException
from service.schemas.input import DeleteOrderRequest
from service.schemas.output import DeleteOrderOutput


@init_environment_variables(model=MyHandlerEnvVars)
@metrics.log_metrics
@tracer.capture_lambda_handler(capture_response=False)
def delete_order(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    logger.set_correlation_id(context.aws_request_id)

    env_vars: MyHandlerEnvVars = get_environment_variables(model=MyHandlerEnvVars)
    logger.debug('environment variables', extra=env_vars.model_dump())

    try:
        my_configuration: MyConfiguration = parse_configuration(model=MyConfiguration)  # type: ignore
        logger.debug('fetched dynamic configuration', extra={'configuration': my_configuration.model_dump()})
    except (SchemaValidationError, ConfigurationStoreError) as exc:  # pragma: no cover
        logger.exception(f'dynamic configuration error, error={str(exc)}')
        return build_response(http_status=HTTPStatus.INTERNAL_SERVER_ERROR, body={})

    try:
        # we want to extract and parse the HTTP body from the api gw envelope
        delete_input: DeleteOrderRequest = parse(event=event, model=DeleteOrderRequest, envelope=ApiGatewayEnvelope)
        logger.info('got delete order request', extra={'order_id': delete_input.order_id})
    except (ValidationError, TypeError) as exc:
        logger.error('event failed input validation', extra={'error': str(exc)})
        return build_response(http_status=HTTPStatus.BAD_REQUEST, body={})

    metrics.add_metric(name='ValidDeleteOrderEvents', unit=MetricUnit.Count, value=1)
    try:
        response: DeleteOrderOutput = handle_delete_request(
            delete_request=delete_input,
            table_name=env_vars.TABLE_NAME,
        )
    except InternalServerException:  # pragma: no cover
        logger.error('finished handling delete order request with internal error')
        return build_response(http_status=HTTPStatus.INTERNAL_SERVER_ERROR, body={})

    logger.info('finished handling delete order request')
    return build_response(http_status=HTTPStatus.OK, body=response.model_dump())
