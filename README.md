# ninja order service

This is a ninja ordering service implemented with AWS Serverless.

## System Design
<img src="ninja_order_diagram.png" alt="Ninja Ordering System Diagram"/>

The system design is straightforward. The design for the OrdersService and UsersService are identical. Each service's functionaltity is exposed as REST APIs: POST, GET, and DELETE verbs for Create, Retrieve, and Delete actions respectively on entities. Each service is backed with a Dyanamo DB table.

The NotificationService sends notifications to users in response to events. In this instance, the notification is in response to an OrderCreated event. NotificationService consists simply of lambda functions that respond to events.

### On Scalability
The system is as scalable, in terms of spikes and drops in traffic, as Lambda functions, that being the only compute resource used. However, the limits of Lambda also apply, especially memory and execution duration. For example, these limits constrain the complexity of the ordering processes i.e. the processes cannot take longer than lambda's 15 minutes limit of execution. A simple solution would be to implement complex and long-running workflows using StepFunctions.

API Gateway is deployed as multi-AZ per region by default. The default VPC spans three AZ subnets. Further development of the system may isolate each service into its own VPCs/subnets, in which case the VPCs need to be designed carefully to maintain the availability of the API Gateways.

If further availability of a service is desired, its API Gateway may be deployed across multiple regions. This would require its backing databases to be synced across multiple regions e.g. DynamoDB's Global Tables.
