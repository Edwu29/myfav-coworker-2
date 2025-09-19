# Components

## 1. API Server
* **Responsibility**: To handle all incoming user requests from LLM clients via the MCP standard. It's responsible for validating requests, handling GitHub authentication, and enqueuing simulation jobs.
* **Key Interfaces**: Exposes the primary API endpoints (e.g., `/simulations`, `/simulations/{jobId}/status`, `/reports/{reportId}`).
* **Dependencies**: `GitHub Service`, `Job Queue`, `Persistence Service`.
* **Technology**: Python, FastMCP.

## 2. Job Queue
* **Responsibility**: To decouple the API Server from the Simulation Worker. It reliably holds simulation job requests until a worker is available.
* **Key Interfaces**: `enqueue(job)` and `dequeue()` operations.
* **Dependencies**: None.
* **Technology**: AWS SQS.

## 3. Simulation Worker
* **Responsibility**: The engine of the application. It pulls jobs from the queue, performs the Git checkout, orchestrates the Simulation Engine, and saves the final report.
* **Key Interfaces**: Listens for messages on the `Job Queue`.
* **Dependencies**: `Job Queue`, `GitHub Service`, `Simulation Engine`, `Persistence Service`.
* **Technology**: Python, running in a background process.

## 4. GitHub Service
* **Responsibility**: To encapsulate all interactions with the external GitHub API. This includes managing the OAuth flow and using the user's token to fetch PR data.
* **Key Interfaces**: Methods like `get_pr_details(url)` and `checkout_pr_branch(repo_url, branch_name)`.
* **Dependencies**: `Persistence Service` (to retrieve the user's token).
* **Technology**: Python, Authlib.

## 5. Simulation Engine
* **Responsibility**: To perform the actual browser automation and AI-driven testing.
* **Key Interfaces**: A `run_test(diff)` method that returns a report.
* **Dependencies**: None.
* **Technology**: Playwright, Pydantic AI.

## 6. Persistence Service
* **Responsibility**: To handle all data storage and retrieval, abstracting the database from the rest of the application (Repository Pattern).
* **Key Interfaces**: Methods like `get_user(id)`, `save_job(job)`, `get_job(job_id)`.
* **Dependencies**: None.
* **Technology**: AWS DynamoDB.

## Component Interaction Diagram
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