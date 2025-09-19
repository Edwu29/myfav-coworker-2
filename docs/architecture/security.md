# Security

## Input Validation
* **Validation Library**: **Pydantic** will be used for all input validation at the API boundary.

## Authentication & Authorization
* **Auth Method**: **Server-side GitHub OAuth2 flow**.

## Secrets Management
* **Production**: Secrets will be managed using **AWS Systems Manager Parameter Store**.

## API Security
* **Rate Limiting**: The AWS API Gateway will be configured with a basic rate limit.
* **HTTPS Enforcement**: Default API Gateway endpoint is HTTPS-only.

## Data Protection
* **Encryption at Rest**: Data in DynamoDB and S3 will be encrypted at rest using AWS-managed keys.
* **PII Handling**: The **GitHub access token** will be encrypted in the database before being stored.

## Dependency Security
* **Scanning Tool**: **GitHub's Dependabot** will be used for vulnerability scanning.