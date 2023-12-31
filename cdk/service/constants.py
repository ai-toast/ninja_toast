# Orders Service
ORDERS_CREATE_LAMBDA = 'CreateOrder'
ORDERS_DELETE_LAMBDA = 'DeleteOrder'
ORDERS_GET_LAMBDA = 'GetOrder'
ORDERS_TABLE_NAME = 'orders'
ORDERS_TABLE_NAME_OUTPUT = 'OrdersDbOutput'
ORDERS_IDEMPOTENCY_TABLE_NAME = 'OrdersIdempotencyTable'
ORDERS_IDEMPOTENCY_TABLE_NAME_OUTPUT = 'OrdersIdempotencyDbOutput'
ORDERS_APIGATEWAY = 'OrdersApigateway'
ORDERS_GW_RESOURCE = 'orders'
ORDERS_ORDER_CREATED_TOPIC = 'NinjaOrderCreated'
ORDERS_ORDER_CREATED_TOPIC_OUTPUT = 'NinjaOrderCreatedSnsOutput'
ORDERS_DELAYED_ORDER_CREATE_ALARM_EMAIL_ADDRESS = 'nobody@example.com'
ORDERS_DELAYED_ORDER_CREATE_EMAIL_TOPIC_OUTPUT = 'NinjaDelayedOrderCreateEmailTopicOutput'

# Users Service
USERS_CREATE_LAMBDA = 'CreateUser'
USERS_DELETE_LAMBDA = 'DeleteUser'
USERS_GET_LAMBDA = 'GetUser'
USERS_TABLE_NAME = 'users'
USERS_TABLE_NAME_OUTPUT = 'UsersDbOutput'
USERS_IDEMPOTENCY_TABLE_NAME = 'UsersIdempotencyTable'
USERS_IDEMPOTENCY_TABLE_NAME_OUTPUT = 'UsersIdempotencyDbOutput'
USERS_APIGATEWAY = 'UsersApigateway'
USERS_GW_RESOURCE = 'users'

# Notification Service
NOTIFY_EMAIL_LAMBDA = 'NotifyEmail'

# Common Lambda
SERVICE_ROLE_ARN = 'ServiceRoleArn'
LAMBDA_BASIC_EXECUTION_ROLE = 'AWSLambdaBasicExecutionRole'
SERVICE_ROLE = 'ServiceRole'
COMMON_LAMBDA_LAYER_NAME = 'common'
API_HANDLER_LAMBDA_MEMORY_SIZE = 128  # MB
API_HANDLER_LAMBDA_TIMEOUT = 10  # seconds

# Common
POWERTOOLS_SERVICE_NAME = 'POWERTOOLS_SERVICE_NAME'
SERVICE_NAME = 'service'
METRICS_NAMESPACE = 'my_product_kpi'
POWERTOOLS_TRACE_DISABLED = 'POWERTOOLS_TRACE_DISABLED'
POWER_TOOLS_LOG_LEVEL = 'LOG_LEVEL'
BUILD_FOLDER = '.build/lambdas/'
COMMON_LAYER_BUILD_FOLDER = '.build/common_layer'
ENVIRONMENT = 'dev'
CONFIGURATION_NAME = 'my_conf'
CONFIGURATION_MAX_AGE_MINUTES = '5'  # time to store app config conf in the cache before refetching it
