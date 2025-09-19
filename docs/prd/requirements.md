# Requirements

## Functional
1.  **FR1**: The system must allow a user to trigger a test simulation against a specific GitHub pull request.
2.  **FR2**: The system must execute the test simulation within a local environment based on the PR's code.
3.  **FR3**: The system must use an AI agent to test a pre-defined user flow during the simulation.
4.  **FR4**: The system must generate a report summarizing the results of the agent's test run.
5.  **FR5**: The system must require robust GitHub authentication before a user can access any repository or PR information.

## Non-Functional
1.  **NFR1**: The system's backend must be written in Python, using the FastMCP framework.
2.  **NFR2**: The simulation engine must use browser automation (e.g., Playwright or Browserbase).
3.  **NFR3**: The system's architecture must support offloading the simulation task to an asynchronous background process.
4.  **NFR4**: All cloud service usage for the MVP must adhere to the $100-$500 budget, prioritizing free-tier services where possible.
5.  **NFR5**: The system must expose an API compatible with the MCP standard to be used by LLM chat clients.

---