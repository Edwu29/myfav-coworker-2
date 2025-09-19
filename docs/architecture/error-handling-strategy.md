# Error Handling Strategy

## General Approach
* **Error Model**: Use custom exception classes. APIs will return a standardized JSON error object.
* **Exception Hierarchy**: A base `AppError` class will be used with specific exceptions inheriting from it.
* **Error Propagation**: Errors will be caught at service boundaries and mapped to appropriate responses.

## Logging Standards
* **Library**: Built-in Python `logging` module, configured to output **structured JSON logs**.
* **Required Context**: Every log entry must include a `correlation_id`.

## Error Handling Patterns
* **External API Errors (GitHub)**: Implement a simple retry mechanism.
* **Business Logic Errors**: Raise specific exceptions like `ValidationError` or `NotFoundError`.
* **Data Consistency (Worker)**: Use a Dead-Letter Queue (DLQ) for the SQS queue to capture and investigate failed jobs.

---