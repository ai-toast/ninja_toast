from aws_cdk import Duration, RemovalPolicy
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as subs
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from aws_cdk.aws_logs import RetentionDays
from constructs import Construct

from cdk.service import constants
from cdk.service.orders_api_construct import OrdersApiConstruct


class NotificationServiceConstruct(Construct):

    def __init__(self, scope: Construct, id: str, appconfig_app_name: str, orders_api_construct: OrdersApiConstruct) -> None:
        super().__init__(scope, id)
        self.id = id
        self.common_layer = self._build_common_layer()
        role = self._build_lambda_role()
        handler = self._order_creation_handler(role=role, appconfig_app_name=appconfig_app_name)
        topic = orders_api_construct.order_created_topic
        self._subscribe_to_order_creation_topic(topic=topic, handler=handler)

    def _build_common_layer(self) -> PythonLayerVersion:
        return PythonLayerVersion(
            self,
            f'{self.id}{constants.COMMON_LAMBDA_LAYER_NAME}',
            entry=constants.COMMON_LAYER_BUILD_FOLDER,
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_11],
            removal_policy=RemovalPolicy.DESTROY,
        )

    def _subscribe_to_order_creation_topic(self, topic: sns.Topic, handler: _lambda.Function):
        # setup lambda to listen to sns topic
        topic.add_subscription(subs.LambdaSubscription(handler))

    def _order_creation_handler(self, role: iam.Role, appconfig_app_name: str) -> _lambda.Function:
        lambda_function = _lambda.Function(
            self,
            constants.NOTIFY_EMAIL_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler='service.handlers.notification.email_on_order_create',
            environment={
                constants.POWERTOOLS_SERVICE_NAME: constants.SERVICE_NAME,  # for logger, tracer and metrics
                constants.POWER_TOOLS_LOG_LEVEL: 'DEBUG',  # for logger
                'CONFIGURATION_APP': appconfig_app_name,  # for feature flags
                'CONFIGURATION_ENV': constants.ENVIRONMENT,  # for feature flags
                'CONFIGURATION_NAME': constants.CONFIGURATION_NAME,  # for feature flags
                'CONFIGURATION_MAX_AGE_MINUTES': constants.CONFIGURATION_MAX_AGE_MINUTES,  # for feature flags
                'REST_API': 'https://www.example.com/api',  # for env vars example
                'ROLE_ARN': 'arn:partition:service:region:account-id:resource-type:resource-id',  # for env vars example
            },
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            timeout=Duration.seconds(constants.API_HANDLER_LAMBDA_TIMEOUT),
            memory_size=constants.API_HANDLER_LAMBDA_MEMORY_SIZE,
            layers=[self.common_layer],
            role=role,
            log_retention=RetentionDays.ONE_DAY,
        )
        return lambda_function

    def _build_lambda_role(self) -> iam.Role:
        return iam.Role(
            self,
            constants.SERVICE_ROLE_ARN,
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            inline_policies={
                'dynamic_configuration':
                    iam.PolicyDocument(statements=[
                        iam.PolicyStatement(
                            actions=['appconfig:GetLatestConfiguration', 'appconfig:StartConfigurationSession'],
                            resources=['*'],
                            effect=iam.Effect.ALLOW,
                        )
                    ]),
            },
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(managed_policy_name=(f'service-role/{constants.LAMBDA_BASIC_EXECUTION_ROLE}')),
                iam.ManagedPolicy.from_managed_policy_arn(scope=self, id='sns_ro',
                                                          managed_policy_arn='arn:aws:iam::aws:policy/AmazonSNSReadOnlyAccess')
            ],
        )

    # apparently sns will invoke lambda
    # https://repost.aws/knowledge-center/lambda-subscribe-sns-topic-same-account
    def _build_lambda_role_4_sns(self) -> iam.Role:
        return iam.Role(
            self,
            constants.SERVICE_ROLE_ARN,
            assumed_by=iam.ServicePrincipal('sns.amazonaws.com'),
            inline_policies={
                'sns_same_acc':
                    iam.PolicyDocument(statements=[iam.PolicyStatement(
                        actions=['lambda:InvokeFunction'],
                        resources=['*'],
                        effect=iam.Effect.ALLOW,
                    )]),
            },
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(managed_policy_name=(f'service-role/{constants.LAMBDA_BASIC_EXECUTION_ROLE}')),
                iam.ManagedPolicy.from_managed_policy_arn(scope=self, id='sns_ro',
                                                          managed_policy_arn='arn:aws:iam::aws:policy/AmazonSNSReadOnlyAccess')
            ],
        )
