# Tech Stack

## Cloud Infrastructure
* **Provider**: AWS
* **Key Services**: API Gateway (for API endpoint), Lambda (to run Python service), SQS (for async task queue), DynamoDB (for job status/reports), S3 (for large report storage), IAM (for security).
* **Deployment Regions**: `us-west-2` (Oregon)

## Technology Stack Table
| Category | Technology | Version | Purpose | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Language** | Python | 3.11 | Primary development language | Modern, stable, excellent AWS support. |
| **Framework** | FastMCP | latest | Backend API framework | As required by PRD (NFR1). |
| **Task Queue** | **AWS SQS** | N/A | Asynchronous task processing | A simple, powerful queue that meets NFR3 without the overhead of Celery. |
| **Data Validation** | Pydantic | 2.7+ | Structuring data inputs | Ensures data integrity throughout the application. |
| **AI Agent Framework**| **Pydantic AI** | latest | GenAI Agent Framework for building production applications | The user's specified choice for creating reliable AI agents. |
| **Browser Automation**| Playwright | 1.40+ | Engine for running simulations | Powerful, modern, and can be self-hosted to meet budget constraints. |
| **Database** | AWS DynamoDB | N/A | Storing job status and report metadata | Fits the AWS ecosystem, massive free tier aligns with budget (NFR4). |
| **Authentication** | Authlib | 1.2+ | GitHub OAuth2 client library | Well-supported library for handling authentication flows (FR5). |
| **Testing** | pytest | 8.0+ | Unit and integration testing | De-facto standard for Python testing. |
| **IaC Tool** | AWS SAM CLI | 1.100+ | Infrastructure as Code | Simplifies deployment of serverless applications on AWS. |

---