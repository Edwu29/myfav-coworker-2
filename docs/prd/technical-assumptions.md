# Technical Assumptions

## Repository Structure: Monorepo
* A single repository will contain all the code for the service.

## Service Architecture: Monolith
* The service will be built as a single, unified application (a monolith).

## Testing Requirements: Unit + Integration Tests
* The testing strategy will include both unit tests for individual components and integration tests to verify they work together.

## Additional Technical Assumptions and Requests
* The backend will be developed in **Python** using the **FastMCP** framework.
* The simulation engine will use a browser automation tool like **Playwright** or **Browserbase**.
* The architecture must support **asynchronous execution** for simulation tasks to run in the background.

---