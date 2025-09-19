# myfav-coworker Product Requirements Document (PRD)

## Goals and Background Context

### Goals
* Increase overall developer velocity and improve team morale.
* Reduce the number of production bugs originating from pull requests.
* Decrease the time reviewers spend on each pull request.
* Increase reviewer confidence in the quality and correctness of the code they are approving.

### Background Context
With the rise of AI-assisted coding, developers are producing code at a much higher volume. This often places a significant burden on code reviewers who must validate large amounts of code of varying quality. This inefficiency creates a bottleneck, leading to longer review cycles, developer burnout, and a higher risk of bugs making it to production. Existing tools primarily assist the PR creator, not the reviewer, leaving a critical gap. This document outlines the requirements for "myfav-coworker," a tool designed to directly address this gap by providing powerful, automated assistance to the code reviewer.

### Change Log
| Date | Version | Description | Author |
| :--- | :--- | :--- | :--- |
| 2025-09-17 | 1.0 | Initial PRD draft | John (PM) |

---
## Requirements

### Functional
1.  **FR1**: The system must allow a user to trigger a test simulation against a specific GitHub pull request.
2.  **FR2**: The system must execute the test simulation within a local environment based on the PR's code.
3.  **FR3**: The system must use an AI agent to test a pre-defined user flow during the simulation.
4.  **FR4**: The system must generate a report summarizing the results of the agent's test run.
5.  **FR5**: The system must require robust GitHub authentication before a user can access any repository or PR information.

### Non-Functional
1.  **NFR1**: The system's backend must be written in Python, using the FastMCP framework.
2.  **NFR2**: The simulation engine must use browser automation (e.g., Playwright or Browserbase).
3.  **NFR3**: The system's architecture must support offloading the simulation task to an asynchronous background process.
4.  **NFR4**: All cloud service usage for the MVP must adhere to the $100-$500 budget, prioritizing free-tier services where possible.
5.  **NFR5**: The system must expose an API compatible with the MCP standard to be used by LLM chat clients.

---
## Technical Assumptions

### Repository Structure: Monorepo
* A single repository will contain all the code for the service.

### Service Architecture: Monolith
* The service will be built as a single, unified application (a monolith).

### Testing Requirements: Unit + Integration Tests
* The testing strategy will include both unit tests for individual components and integration tests to verify they work together.

### Additional Technical Assumptions and Requests
* The backend will be developed in **Python** using the **FastMCP** framework.
* The simulation engine will use a browser automation tool like **Playwright** or **Browserbase**.
* The architecture must support **asynchronous execution** for simulation tasks to run in the background.

---
## Epic List

**Epic 1: Core Simulation Engine MVP**
* **Goal**: Establish the core service, enable secure GitHub authentication, and deliver the end-to-end user flow of triggering a local simulation for a pull request and receiving a report.

---
## Epic 1 Details: Core Simulation Engine MVP

**Expanded Goal**: This epic covers all work required to deliver a functional MVP. It starts by establishing the basic service and its connection to GitHub, then implements the core logic for running a local, agent-driven simulation on a pull request. The final output is a tangible report that provides value to the code reviewer.

### Story 1.1: Foundational Service Setup
* **As a** solo developer, **I want** to set up a basic Python FastMCP project with a health-check endpoint, **so that** I have a running, verifiable foundation to build upon.
* **Acceptance Criteria**:
    1. A new Git repository is initialized.
    2. A Python project with FastMCP is created.
    3. A `/health` endpoint exists and returns a `200 OK` status with a simple JSON response.

### Story 1.2: Implement GitHub Authentication
* **As a** reviewer, **I want** to securely authenticate with my GitHub account, **so that** the application can access pull request data on my behalf.
* **Acceptance Criteria**:
    1. A user can initiate a GitHub OAuth flow from the service.
    2. After successful authentication, the service securely receives and stores an access token for the user.
    3. Unauthenticated requests to protected endpoints are rejected.

### Story 1.3: Fetch Pull Request Data
* **As a** reviewer, **I want** to provide a GitHub PR URL to the service, **so that** it can fetch the relevant code and metadata for the simulation.
* **Acceptance Criteria**:
    1. An authenticated user can submit a PR URL to a specific endpoint.
    2. The service uses the GitHub API to fetch details of the PR.
    3. Within a **persistent local clone** of the repository, the service successfully **checks out the specific branch** for the pull request.

### Story 1.4: Implement Local Simulation Runner
* **As a** reviewer, **I want** to trigger a simulation process, **so that** the checked-out PR code is executed in a controlled local environment.
* **Acceptance Criteria**:
    1. A new endpoint exists to start the simulation for a previously fetched PR.
    2. The service successfully launches the browser automation tool from the root of the **local repository clone, which is now on the correct PR branch**.
    3. The runner can execute a simple, predefined test script.
    4. The process runs asynchronously in the background.

### Story 1.5: AI Agent Diff-Based Test Execution
* **As a** developer, **I want** the AI agent to analyze the PR's code changes (the 'diff'), **so that** it can create and execute a targeted test plan relevant to those changes.
* **Acceptance Criteria**:
    1. The service calculates the code `diff` between the PR branch and the main branch.
    2. The AI agent receives the `diff` as input to generate a dynamic test plan.
    3. The agent executes this test plan using the browser automation tool.
    4. The agent determines a pass/fail result based on the outcome.

### Story 1.6: Generate and Retrieve Simulation Report
* **As a** reviewer, **I want** to receive a clear report of the simulation results, **so that** I can confidently assess the pull request.
* **Acceptance Criteria**:
    1. Upon completion of the AI agent test, a simple report (e.g., JSON or Markdown) is generated.
    2. The report contains the overall result (pass/fail) and a log of the agent's key actions.
    3. The user can retrieve the report via a separate endpoint using a job or simulation ID.