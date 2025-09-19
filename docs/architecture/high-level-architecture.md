# High Level Architecture

## Technical Summary
The architecture for myfav-coworker will be a pragmatic monolith, developed in Python using the FastMCP framework. The system is designed to handle user requests via a primary API, but its core functionality—running browser-based simulations—will be offloaded to an asynchronous background worker. This ensures the user-facing API remains responsive. The system will securely interact with the GitHub API for authentication and data retrieval and will utilize a browser automation tool like Playwright to execute AI-driven test flows.

## High Level Overview
The system follows the Monolith service architecture and Monorepo repository structure as defined in the PRD's technical assumptions. The conceptual flow is as follows: A user, via an LLM chat client, authenticates and submits a PR link to the service. The service validates the request, fetches the PR data, and places a simulation job onto a queue. An asynchronous worker picks up the job, checks out the specified PR branch, and invokes the AI agent and browser automation engine. Upon completion, the worker generates a report that the user can retrieve later.

## High Level Project Diagram
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

## Architectural and Design Patterns
* **Monolith Architecture**: The service will be built as a single, unified application. _Rationale:_ This is the simplest and fastest approach for a solo developer on a 1-2 week timeline, minimizing deployment and operational complexity for the MVP.
* **Asynchronous Task Queue**: Long-running simulation tasks will be handled by background workers. _Rationale:_ This is required by NFR3 and prevents the user-facing API from timing out. It ensures the system is responsive and scalable.
* **Repository Pattern**: Data access will be abstracted away from the core business logic. _Rationale:_ This improves testability and makes it easier to manage data persistence.

---