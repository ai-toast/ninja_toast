from aws_cdk import CfnOutput, Duration, RemovalPolicy, aws_apigateway
from aws_cdk import aws_cloudwatch as cw
from aws_cdk import aws_cloudwatch_actions as cw_actions
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as sns_subs
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from aws_cdk.aws_logs import RetentionDays
from constructs import Construct

import cdk.service.constants as constants
from cdk.service.orders_api_db_construct import OrdersApiDbConstruct


class OrdersApiConstruct(Construct):

    def __init__(self, scope: Construct, id_: str, appconfig_app_name: str) -> None:
        super().__init__(scope, id_)
        self.id_ = id_
        self.api_db = OrdersApiDbConstruct(self, f'{id_}db')
        self.lambda_role = self._build_lambda_role(self.api_db.db, self.api_db.idempotency_db)
        self.common_layer = self._build_common_layer()
        self.sns_key = self._build_kms_managed_key(self.lambda_role)

        topic_name = constants.ORDERS_ORDER_CREATED_TOPIC
        self.order_created_topic = self._build_order_created_topic(topic_name=topic_name, role=self.lambda_role, key=self.sns_key)

        self.rest_api = self._build_api_gw()
        api_resource: aws_apigateway.Resource = self.rest_api.root.add_resource('api').add_resource(constants.ORDERS_GW_RESOURCE)
        self._add_post_lambda_integration(api_resource, self.lambda_role, self.api_db.db, appconfig_app_name, self.api_db.idempotency_db,
                                          self.order_created_topic)

    def _build_api_gw(self) -> aws_apigateway.RestApi:
        rest_api: aws_apigateway.RestApi = aws_apigateway.RestApi(
            self,
            'orders-rest-api',
            rest_api_name='Ninja Orders Rest API',
            description='This service handles /api/orders requests',
            deploy_options=aws_apigateway.StageOptions(throttling_rate_limit=2, throttling_burst_limit=10),
            cloud_watch_role=False,
        )

        CfnOutput(self, id=constants.ORDERS_APIGATEWAY, value=rest_api.url).override_logical_id(constants.ORDERS_APIGATEWAY)
        return rest_api

    def _build_kms_managed_key(self, role: iam.Role) -> kms.Key:
        key = kms.Key(self, 'SNSOrderCreatedKey', enable_key_rotation=True)
        key.grant_encrypt_decrypt(role)
        return key

    def _build_order_created_topic(self, topic_name: str, role: iam.Role, key: kms.Key) -> sns.Topic:
        sns_topic = sns.Topic(self, id='ninja_order_created_topic', topic_name=topic_name, master_key=key)
        sns_topic.grant_publish(grantee=role)
        sns_topic.add_to_resource_policy(
            statement=iam.PolicyStatement(actions=['sns:Publish'], resources=[sns_topic.topic_arn], effect=iam.Effect.DENY,
                                          principals=[iam.AnyPrincipal()], conditions={'Bool': {
                                              'aws:SecureTransport': False
                                          }}))

        CfnOutput(self, id=constants.ORDERS_ORDER_CREATED_TOPIC_OUTPUT, value=sns_topic.topic_arn).override_logical_id(
            constants.ORDERS_ORDER_CREATED_TOPIC_OUTPUT)  # so can be referenced in integ test conftest.py
        return sns_topic

    def _build_delayed_order_create_email_topic(self, topic_name: str, role: iam.Role, key: kms.Key) -> sns.Topic:
        sns_topic = sns.Topic(self, id='ninja_delayed_order_create_email_topic', topic_name=topic_name, master_key=key)
        sns_topic.grant_publish(grantee=role)
        sns_topic.add_to_resource_policy(
            statement=iam.PolicyStatement(actions=['sns:Publish'], resources=[sns_topic.topic_arn], effect=iam.Effect.DENY,
                                          principals=[iam.AnyPrincipal()], conditions={'Bool': {
                                              'aws:SecureTransport': False
                                          }}))

        CfnOutput(self, id=constants.ORDERS_DELAYED_ORDER_CREATE_EMAIL_TOPIC_OUTPUT, value=sns_topic.topic_arn).override_logical_id(
            constants.ORDERS_DELAYED_ORDER_CREATE_EMAIL_TOPIC_OUTPUT)  # so can be referenced in integ test conftest.py
        return sns_topic

    # shared role for Create, Get, and Delete lambdas. Better to have separate for each.
    def _build_lambda_role(self, db: dynamodb.Table, idempotency_table: dynamodb.Table) -> iam.Role:
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
                'dynamodb_db':
                    iam.PolicyDocument(statements=[
                        iam.PolicyStatement(
                            actions=['dynamodb:PutItem', 'dynamodb:GetItem', 'dynamodb:DeleteItem'],
                            resources=[db.table_arn],
                            effect=iam.Effect.ALLOW,
                        )
                    ]),
                'idempotency_table':
                    iam.PolicyDocument(statements=[
                        iam.PolicyStatement(
                            actions=['dynamodb:PutItem', 'dynamodb:GetItem', 'dynamodb:UpdateItem', 'dynamodb:DeleteItem'],
                            resources=[idempotency_table.table_arn],
                            effect=iam.Effect.ALLOW,
                        )
                    ]),
            },
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(managed_policy_name=(f'service-role/{constants.LAMBDA_BASIC_EXECUTION_ROLE}'))
            ],
        )

    def _build_common_layer(self) -> PythonLayerVersion:
        return PythonLayerVersion(
            self,
            f'{self.id_}{constants.COMMON_LAMBDA_LAYER_NAME}',
            entry=constants.COMMON_LAYER_BUILD_FOLDER,
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_11],
            removal_policy=RemovalPolicy.DESTROY,
        )

    def _build_create_order_lambda(self, role: iam.Role, db: dynamodb.Table, appconfig_app_name: str, idempotency_table: dynamodb.Table,
                                   topic: sns.Topic):
        lambda_function = _lambda.Function(
            self,
            constants.ORDERS_CREATE_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler='service.handlers.create_order.create_order',
            environment={
                constants.POWERTOOLS_SERVICE_NAME: constants.SERVICE_NAME,  # for logger, tracer and metrics
                constants.POWER_TOOLS_LOG_LEVEL: 'DEBUG',  # for logger
                'CONFIGURATION_APP': appconfig_app_name,  # for feature flags
                'CONFIGURATION_ENV': constants.ENVIRONMENT,  # for feature flags
                'CONFIGURATION_NAME': constants.CONFIGURATION_NAME,  # for feature flags
                'CONFIGURATION_MAX_AGE_MINUTES': constants.CONFIGURATION_MAX_AGE_MINUTES,  # for feature flags
                'REST_API': 'https://www.ranthebuilder.cloud/api',  # for env vars example
                'ROLE_ARN': 'arn:partition:service:region:account-id:resource-type:resource-id',  # for env vars example
                'TABLE_NAME': db.table_name,
                'IDEMPOTENCY_TABLE_NAME': idempotency_table.table_name,
                'ORDER_CREATED_TOPIC_ARN': topic.topic_arn,
            },
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            timeout=Duration.seconds(constants.API_HANDLER_LAMBDA_TIMEOUT),
            memory_size=constants.API_HANDLER_LAMBDA_MEMORY_SIZE,
            layers=[self.common_layer],
            role=role,
            log_retention=RetentionDays.ONE_DAY,
        )
        self._build_late_order_creation_alarm(lambda_function.function_name)
        return lambda_function

    def _build_delete_order_lambda(self, role: iam.Role, db: dynamodb.Table, appconfig_app_name: str):
        lambda_function = _lambda.Function(
            self,
            constants.ORDERS_DELETE_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler='service.handlers.delete_order.delete_order',
            environment={
                constants.POWERTOOLS_SERVICE_NAME: constants.SERVICE_NAME,  # for logger, tracer and metrics
                constants.POWER_TOOLS_LOG_LEVEL: 'DEBUG',  # for logger
                'CONFIGURATION_APP': appconfig_app_name,  # for feature flags
                'CONFIGURATION_ENV': constants.ENVIRONMENT,  # for feature flags
                'CONFIGURATION_NAME': constants.CONFIGURATION_NAME,  # for feature flags
                'CONFIGURATION_MAX_AGE_MINUTES': constants.CONFIGURATION_MAX_AGE_MINUTES,  # for feature flags
                'REST_API': 'https://www.ranthebuilder.cloud/api',  # for env vars example
                'ROLE_ARN': 'arn:partition:service:region:account-id:resource-type:resource-id',  # for env vars example
                'TABLE_NAME': db.table_name,
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

    def _build_get_order_lambda(self, role: iam.Role, db: dynamodb.Table, appconfig_app_name: str):
        lambda_function = _lambda.Function(
            self,
            constants.ORDERS_GET_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler='service.handlers.get_order.get_order',
            environment={
                constants.POWERTOOLS_SERVICE_NAME: constants.SERVICE_NAME,  # for logger, tracer and metrics
                constants.POWER_TOOLS_LOG_LEVEL: 'DEBUG',  # for logger
                'CONFIGURATION_APP': appconfig_app_name,  # for feature flags
                'CONFIGURATION_ENV': constants.ENVIRONMENT,  # for feature flags
                'CONFIGURATION_NAME': constants.CONFIGURATION_NAME,  # for feature flags
                'CONFIGURATION_MAX_AGE_MINUTES': constants.CONFIGURATION_MAX_AGE_MINUTES,  # for feature flags
                'REST_API': 'https://www.ranthebuilder.cloud/api',  # for env vars example
                'ROLE_ARN': 'arn:partition:service:region:account-id:resource-type:resource-id',  # for env vars example
                'TABLE_NAME': db.table_name,
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

    def _add_post_lambda_integration(self, api_name: aws_apigateway.Resource, role: iam.Role, db: dynamodb.Table, appconfig_app_name: str,
                                     idempotency_table: dynamodb.Table, order_created_topic: sns.Topic):

        # POST /api/orders/
        api_name.add_method(
            http_method='POST', integration=aws_apigateway.LambdaIntegration(
                handler=self._build_create_order_lambda(role, db, appconfig_app_name, idempotency_table, topic=order_created_topic)))

        # DELETE /api/orders/
        api_name.add_method(http_method='DELETE',
                            integration=aws_apigateway.LambdaIntegration(handler=self._build_delete_order_lambda(role, db, appconfig_app_name)))

        # GET /api/orders/
        api_name.add_method(http_method='GET',
                            integration=aws_apigateway.LambdaIntegration(handler=self._build_get_order_lambda(role, db, appconfig_app_name)))

    def _build_late_order_creation_alarm(self, lambda_function_name: str):
        # create a cloudwatch alarm for create order events taking longer than 1 minute
        duration_metric = cw.Metric(namespace='AWS/Lambda', metric_name='Duration', statistic='Maximum',
                                    dimensions_map={'FunctionName': lambda_function_name}, period=Duration.minutes(1))
        delayed_order_create_alarm = cw.Alarm(
            self,
            'DelayedOrderCreateAlarm',
            metric=duration_metric,
            threshold=60_000,  # 60k ms = 1 minute
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            evaluation_periods=1,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING)

        # alarm_email_topic = sns.Topic(self, 'AlarmEmail', topic_name='delayed-order-create-alarm')
        alarm_email_topic = self._build_delayed_order_create_email_topic(topic_name='delayed-order-create-alarm', role=self.lambda_role,
                                                                         key=self.sns_key)
        alarm_email_topic.add_subscription(sns_subs.EmailSubscription(constants.ORDERS_DELAYED_ORDER_CREATE_ALARM_EMAIL_ADDRESS))
        delayed_order_create_alarm.add_alarm_action(cw_actions.SnsAction(alarm_email_topic))

        return delayed_order_create_alarm
