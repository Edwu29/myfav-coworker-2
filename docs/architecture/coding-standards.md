# Coding Standards

## Core Standards
* **Style & Linting**: All Python code will be formatted with **Black** and linted with **Flake8**.
* **Test Organization**: Test files will be located in the `tests/` directory and mirror the `src/` directory structure.

## Naming Conventions
* Adherence to standard **PEP 8** naming conventions.

## Critical Rules
1.  **Use Structured Logging**: Never use `print()`.
2.  **Use Service Layers**: All external I/O must be performed through the designated service component.
3.  **Handle Secrets Securely**: Never hardcode secrets.
4.  **Raise Custom Exceptions**: API endpoints must handle errors by raising specific custom exceptions.

---