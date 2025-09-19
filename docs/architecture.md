# myfav-coworker Architecture Document

## Introduction
This document outlines the overall project architecture for myfav-coworker, including backend systems, shared services, and non-UI specific concerns. Its primary goal is to serve as the guiding architectural blueprint for AI-driven development, ensuring consistency and adherence to chosen patterns and technologies.

### Starter Template or Existing Project
N/A - This is a greenfield project that will be built from scratch as per the PRD.

### Change Log
| Date | Version | Description | Author |
| :--- | :--- | :--- | :--- |
| 2025-09-17 | 1.0 | Initial architecture draft | Winston (Architect) |

---
## High Level Architecture

### Technical Summary
The architecture for myfav-coworker will be a pragmatic monolith, developed in Python using the FastMCP framework. The system is designed to handle user requests via a primary API, but its core functionality—running browser-based simulations—will be offloaded to an asynchronous background worker. This ensures the user-facing API remains responsive. The system will securely interact with the GitHub API for authentication and data retrieval and will utilize a browser automation tool like Playwright to execute AI-driven test flows.

### High Level Overview
The system follows the Monolith service architecture and Monorepo repository structure as defined in the PRD's technical assumptions. The conceptual flow is as follows: A user, via an LLM chat client, authenticates and submits a PR link to the service. The service validates the request, fetches the PR data, and places a simulation job onto a queue. An asynchronous worker picks up the job, checks out the specified PR branch, and invokes the AI agent and browser automation engine. Upon completion, the worker generates a report that the user can retrieve later.

### High Level Project Diagram
```
graph TD
    A[User via LLM Client] -->|Submits PR URL| B(myfav-coworker Service);
    B -->|OAuth Flow| C[GitHub API];
    B -->|Fetches PR Data| C;
    B -->|Enqueues Job| D[Async Task Queue];
    E[Async Worker] -->|Dequeues Job| D;
    E -->|Git Checkout| F[Local Repo Clone];
    E -->|Runs Simulation| G[Browser Automation Engine];
    G -->|Prompts| H[LLM Agent];
    E -->|Saves Report| I[Report Storage];
    A -->|Retrieves Report| B;
    B -->|Reads Report| I;
```

### Architectural and Design Patterns
* **Monolith Architecture**: The service will be built as a single, unified application. _Rationale:_ This is the simplest and fastest approach for a solo developer on a 1-2 week timeline, minimizing deployment and operational complexity for the MVP.
* **Asynchronous Task Queue**: Long-running simulation tasks will be handled by background workers. _Rationale:_ This is required by NFR3 and prevents the user-facing API from timing out. It ensures the system is responsive and scalable.
* **Repository Pattern**: Data access will be abstracted away from the core business logic. _Rationale:_ This improves testability and makes it easier to manage data persistence.

---
## Tech Stack

### Cloud Infrastructure
* **Provider**: AWS
* **Key Services**: API Gateway (for API endpoint), Lambda (to run Python service), SQS (for async task queue), DynamoDB (for job status/reports), S3 (for large report storage), IAM (for security).
* **Deployment Regions**: `us-west-2` (Oregon)

### Technology Stack Table
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
## Data Models

### SimulationJob
* **Purpose**: To track the state, progress, and results of a single PR simulation request from start to finish.
* **Key Attributes**: `job_id`, `user_id`, `pr_url`, `status`, `report`, `created_at`, `completed_at`.
* **Relationships**: Belongs to a User.

### User
* **Purpose**: To store essential information about an authenticated user, including their GitHub identity and the encrypted access token required for API calls.
* **Key Attributes**: `user_id`, `github_id`, `github_username`, `encrypted_github_token`, `created_at`, `last_login_at`.
* **Relationships**: Has many `SimulationJob`s.

---
## Components

### 1. API Server
* **Responsibility**: To handle all incoming user requests from LLM clients via the MCP standard. It's responsible for validating requests, handling GitHub authentication, and enqueuing simulation jobs.
* **Key Interfaces**: Exposes the primary API endpoints (e.g., `/simulations`, `/simulations/{jobId}/status`, `/reports/{reportId}`).
* **Dependencies**: `GitHub Service`, `Job Queue`, `Persistence Service`.
* **Technology**: Python, FastMCP.

### 2. Job Queue
* **Responsibility**: To decouple the API Server from the Simulation Worker. It reliably holds simulation job requests until a worker is available.
* **Key Interfaces**: `enqueue(job)` and `dequeue()` operations.
* **Dependencies**: None.
* **Technology**: AWS SQS.

### 3. Simulation Worker
* **Responsibility**: The engine of the application. It pulls jobs from the queue, performs the Git checkout, orchestrates the Simulation Engine, and saves the final report.
* **Key Interfaces**: Listens for messages on the `Job Queue`.
* **Dependencies**: `Job Queue`, `GitHub Service`, `Simulation Engine`, `Persistence Service`.
* **Technology**: Python, running in a background process.

### 4. GitHub Service
* **Responsibility**: To encapsulate all interactions with the external GitHub API. This includes managing the OAuth flow and using the user's token to fetch PR data.
* **Key Interfaces**: Methods like `get_pr_details(url)` and `checkout_pr_branch(repo_url, branch_name)`.
* **Dependencies**: `Persistence Service` (to retrieve the user's token).
* **Technology**: Python, Authlib.

### 5. Simulation Engine
* **Responsibility**: To perform the actual browser automation and AI-driven testing.
* **Key Interfaces**: A `run_test(diff)` method that returns a report.
* **Dependencies**: None.
* **Technology**: Playwright, Pydantic AI.

### 6. Persistence Service
* **Responsibility**: To handle all data storage and retrieval, abstracting the database from the rest of the application (Repository Pattern).
* **Key Interfaces**: Methods like `get_user(id)`, `save_job(job)`, `get_job(job_id)`.
* **Dependencies**: None.
* **Technology**: AWS DynamoDB.

### Component Interaction Diagram
```
graph TD
    subgraph "Monolith Application"
        API[API Server] --> Q[Job Queue];
        W[Simulation Worker] --> Q;
        W --> GS[GitHub Service];
        W --> SE[Simulation Engine];
        W --> PS[Persistence Service];
        API --> GS;
        API --> PS;
    end
    
    User[User via Client] --> API;
    GS --> GAPI[External GitHub API];
    PS --> DB[(Database)];
```

---
## External APIs

### GitHub API
* **Purpose**: To handle user authentication via OAuth2 and to fetch repository and pull request data on behalf of the authenticated user.
* **Documentation**: `https://docs.github.com/en/rest`
* **Base URL**: `https://api.github.com`
* **Authentication**: OAuth2. We will use the user's access token obtained via the server-side flow. This will require the `repo` scope to access private repository data.
* **Rate Limits**: The standard authenticated rate limit is 5,000 requests per hour, which is more than sufficient for the MVP.
* **Key Endpoints Used**:
    * `POST /login/oauth/access_token`: To exchange the temporary code for an access token.
    * `GET /user`: To fetch the authenticated user's profile information.
    * `GET /repos/{owner}/{repo}/pulls/{pull_number}`: To fetch the details for a specific pull request.
* **Integration Notes**: All interactions with this API will be encapsulated within the **GitHub Service** component to ensure a clean separation of concerns.

---
## Core Workflows

### Workflow 1: User Authentication (One-Time Setup)
```
sequenceDiagram
    participant Client
    participant API Server
    participant GitHub API
    participant Persistence

    Client->>API Server: 1. Request to log in
    API Server-->>Client: 2. Provide GitHub OAuth URL
    Client->>GitHub API: 3. User authenticates and approves
    GitHub API-->>API Server: 4. Redirect with temporary auth `code`
    API Server->>GitHub API: 5. Exchange `code` for access token
    GitHub API-->>API Server: 6. Return access token
    API Server->>Persistence: 7. Encrypt and save user's token
    API Server-->>Client: 8. Return our service's session token (e.g., JWT)
```

### Workflow 2: Simulation Request (Authenticated)
```
sequenceDiagram
    participant Client
    participant API Server
    participant Job Queue
    participant Worker
    participant Persistence

    Client->>API Server: 1. Request Simulation(PR URL)<br/>(includes session token)
    API Server->>API Server: 2. Validate session token
    API Server->>Job Queue: 3. Enqueue Job
    API Server-->>Client: 4. Acknowledge with jobId

    Note right of Client: Worker processes job asynchronously...

    loop User Polling for Result
        Client->>API Server: 5. Get Status? (GET /simulations/{jobId})
        API Server->>Persistence: 6. Check Job Status
        Persistence-->>API Server: 7. Status is "complete"
        API Server-->>Client: 8. Return Final Report
    end
```

---
## REST API Spec
```
openapi: 3.0.1
info:
  title: "myfav-coworker API"
  description: "API for submitting and tracking PR simulation jobs."
  version: "1.0.0"
servers:
  - url: "https://api.myfav-coworker.com/v1"
    description: "Production Server"

components:
  schemas:
    SimulationJob:
      type: object
      properties:
        job_id:
          type: string
          description: "Unique identifier for the job."
        status:
          type: string
          enum: [pending, running, completed, failed]
        report:
          type: object
          properties:
            result:
              type: string
              enum: [pass, fail]
            summary:
              type: string
            
  securitySchemes:
    SessionAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

security:
  - SessionAuth: []

paths:
  /auth/github:
    get:
      summary: "Initiate GitHub Login"
      description: "Redirects the user to GitHub to start the OAuth2 flow."
      responses:
        '302':
          description: "Redirect to GitHub for authorization."

  /auth/github/callback:
    get:
      summary: "GitHub OAuth Callback"
      description: "The callback URL for GitHub to redirect to after authorization. The service exchanges the code for a token and returns a session JWT."
      responses:
        '200':
          description: "Authentication successful, returns a session JWT."
        '400':
          description: "Error during authentication."
          
  /simulations:
    post:
      summary: "Submit a new simulation job"
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                pr_url:
                  type: string
                  example: "https://github.com/owner/repo/pull/123"
      responses:
        '202':
          description: "Job accepted for processing."
          content:
            application/json:
              schema:
                type: object
                properties:
                  job_id:
                    type: string
                    
  /simulations/{jobId}:
    get:
      summary: "Get simulation job status and result"
      parameters:
        - in: path
          name: jobId
          required: true
          schema:
            type: string
      responses:
        '200':
          description: "Job status and report."
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SimulationJob'
        '404':
          description: "Job not found."
```

---
## Database Schema

### Table: `myfav-coworker-main`
* **Primary Key Schema**:
    * **Partition Key (PK)**: A composite key to uniquely identify an item (e.g., `USER#{github_id}` or `JOB#{job_id}`).
    * **Sort Key (SK)**: For this simple schema, we'll use a static value like `METADATA` for the main record.
* **Item Structures**: JSON structures for User and SimulationJob items are defined.
* **Secondary Indexes**: A Global Secondary Index (GSI) is defined to query jobs by user.

---
## Source Tree
```
myfav-coworker/
├── README.md                  # Project overview and setup instructions
├── template.yaml              # AWS SAM template defining all cloud resources (IaC)
├── src/                       # Main application source code
│   ├── app.py                 # API Gateway -> Lambda handler
│   ├── worker.py              # SQS -> Lambda handler
│   ├── api/
│   ├── services/
│   ├── models/
│   └── utils/
├── tests/
│   ├── unit/
│   └── integration/
└── requirements.txt           # Python package dependencies
```

---
## Infrastructure and Deployment

### Infrastructure as Code
* **Tool**: AWS SAM CLI `1.100+`.
* **Location**: The infrastructure will be defined in the `template.yaml` file at the project's root directory.
* **Approach**: A single SAM template will define all AWS resources.

### Deployment Strategy
* **Strategy**: Continuous Deployment. Every merge to the `main` branch will automatically trigger a deployment to production.
* **CI/CD Platform**: **GitHub Actions**.
* **Pipeline Configuration**: The deployment workflow will be defined in a file located at `.github/workflows/deploy.yml`.

### Environments
* **Development**: The developer's local machine, using the `sam local` command suite for testing.
* **Production**: The live environment hosted on AWS.

### Environment Promotion Flow
Code is developed on a feature branch. Upon merging the PR to `main`, the GitHub Actions pipeline automatically builds, packages, and deploys the application to the `prod` environment.

### Rollback Strategy
* **Primary Method**: Re-deploying the previous stable version via AWS CloudFormation.

---
## Error Handling Strategy

### General Approach
* **Error Model**: Use custom exception classes. APIs will return a standardized JSON error object.
* **Exception Hierarchy**: A base `AppError` class will be used with specific exceptions inheriting from it.
* **Error Propagation**: Errors will be caught at service boundaries and mapped to appropriate responses.

### Logging Standards
* **Library**: Built-in Python `logging` module, configured to output **structured JSON logs**.
* **Required Context**: Every log entry must include a `correlation_id`.

### Error Handling Patterns
* **External API Errors (GitHub)**: Implement a simple retry mechanism.
* **Business Logic Errors**: Raise specific exceptions like `ValidationError` or `NotFoundError`.
* **Data Consistency (Worker)**: Use a Dead-Letter Queue (DLQ) for the SQS queue to capture and investigate failed jobs.

---
## Coding Standards

### Core Standards
* **Style & Linting**: All Python code will be formatted with **Black** and linted with **Flake8**.
* **Test Organization**: Test files will be located in the `tests/` directory and mirror the `src/` directory structure.

### Naming Conventions
* Adherence to standard **PEP 8** naming conventions.

### Critical Rules
1.  **Use Structured Logging**: Never use `print()`.
2.  **Use Service Layers**: All external I/O must be performed through the designated service component.
3.  **Handle Secrets Securely**: Never hardcode secrets.
4.  **Raise Custom Exceptions**: API endpoints must handle errors by raising specific custom exceptions.

---
## Test Strategy and Standards

### Testing Philosophy
* **Approach**: A **pragmatic, test-after** approach for the MVP.
* **Coverage Goals**: Aim for **80% line coverage** for all new code, enforced by the CI/CD pipeline.
* **Test Pyramid**: Focus on **Unit Tests** and **Integration Tests**.

### Test Types and Organization
* **Unit Tests**: Using `pytest` with `unittest.mock`.
* **Integration Tests**: Using `moto` to mock AWS services locally.
* **End-to-End (E2E) Tests**: Not in scope for the MVP.

### Test Data Management
* **Strategy**: Use test **fixtures** managed by `pytest`.

### Continuous Testing
* **CI Integration**: The GitHub Actions pipeline will run all tests on every pull request to `main`.

---
## Security

### Input Validation
* **Validation Library**: **Pydantic** will be used for all input validation at the API boundary.

### Authentication & Authorization
* **Auth Method**: **Server-side GitHub OAuth2 flow**.

### Secrets Management
* **Production**: Secrets will be managed using **AWS Systems Manager Parameter Store**.

### API Security
* **Rate Limiting**: The AWS API Gateway will be configured with a basic rate limit.
* **HTTPS Enforcement**: Default API Gateway endpoint is HTTPS-only.

### Data Protection
* **Encryption at Rest**: Data in DynamoDB and S3 will be encrypted at rest using AWS-managed keys.
* **PII Handling**: The **GitHub access token** will be encrypted in the database before being stored.

### Dependency Security
* **Scanning Tool**: **GitHub's Dependabot** will be used for vulnerability scanning.