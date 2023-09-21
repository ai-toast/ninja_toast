from typing import Any, Dict

from aws_lambda_env_modeler import get_environment_variables, init_environment_variables
from aws_lambda_powertools.utilities.feature_flags.exceptions import ConfigurationStoreError, SchemaValidationError
from aws_lambda_powertools.utilities.parser import ValidationError
from aws_lambda_powertools.utilities.typing import LambdaContext

from service.handlers.schemas.dynamic_configuration import MyConfiguration
from service.handlers.schemas.env_vars import NotifyEmailHandlerEnvVars
from service.handlers.utils.dynamic_configuration import parse_configuration
from service.handlers.utils.observability import logger, metrics, tracer


@init_environment_variables(model=NotifyEmailHandlerEnvVars)
@metrics.log_metrics
@tracer.capture_lambda_handler(capture_response=False)
def email_on_order_create(event: Dict[str, Any], context: LambdaContext) -> None:
    logger.set_correlation_id(context.aws_request_id)

    env_vars: NotifyEmailHandlerEnvVars = get_environment_variables(model=NotifyEmailHandlerEnvVars)
    logger.debug('environment variables', extra=env_vars.model_dump())

    try:
        my_configuration: MyConfiguration = parse_configuration(model=MyConfiguration)  # type: ignore
        logger.debug('fetched dynamic configuration', extra={'configuration': my_configuration.model_dump()})
    except (SchemaValidationError, ConfigurationStoreError) as exc:  # pragma: no cover
        logger.exception(f'dynamic configuration error, error={str(exc)}')

    try:
        logger.debug(f'Event from SNS: {event}')
    except (ValidationError, TypeError) as exc:
        logger.error('event failed input validation', extra={'error': str(exc)})

    logger.info('finished email notification of Order Creation event')
