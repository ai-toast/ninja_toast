import logging
from typing import Any, Dict, Optional, Type, Union

from aws_lambda_powertools.utilities.parser.envelopes import ApiGatewayEnvelope
from aws_lambda_powertools.utilities.parser.exceptions import InvalidEnvelopeError
from aws_lambda_powertools.utilities.parser.models import APIGatewayProxyEventModel
from aws_lambda_powertools.utilities.parser.types import Model

logger = logging.getLogger(__name__)


class ApiGatewayEnvelopeExt(ApiGatewayEnvelope):
    """Extension to API Gateway envelope to extract data within body key OR header key"""

    def parseHeader(self, data: Optional[Union[Dict[str, Any], Any]], model: Type[Model]) -> Model:
        """Parses data found in envelope's header with model provided

        Parameters
        ----------
        data : Dict
            Lambda event to be parsed
        model : Type[Model]
            Data model provided to parse after extracting data using envelope

        Returns
        -------
        Any
            Parsed detail payload with model provided
        """
        try:
            logger.debug(f'Parsing and validating event model with envelope={self.__class__}')
            logger.debug(f'Parsing incoming data with Api Gateway model {APIGatewayProxyEventModel}')
            parsed_envelope: APIGatewayProxyEventModel = APIGatewayProxyEventModel.model_validate(data)
            logger.debug(f'Parsing event payload in `detail` with {model}')
            return model.model_validate(parsed_envelope.headers)
        except AttributeError:
            raise InvalidEnvelopeError(f'Envelope must implement BaseEnvelope, envelope={self.__class__}')
