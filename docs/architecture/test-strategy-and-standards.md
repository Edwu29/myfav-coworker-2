# Test Strategy and Standards

## Testing Philosophy
* **Approach**: A **pragmatic, test-after** approach for the MVP.
* **Coverage Goals**: Aim for **80% line coverage** for all new code, enforced by the CI/CD pipeline.
* **Test Pyramid**: Focus on **Unit Tests** and **Integration Tests**.

## Test Types and Organization
* **Unit Tests**: Using `pytest` with `unittest.mock`.
* **Integration Tests**: Using `moto` to mock AWS services locally.
* **End-to-End (E2E) Tests**: Not in scope for the MVP.

## Test Data Management
* **Strategy**: Use test **fixtures** managed by `pytest`.

## Continuous Testing
* **CI Integration**: The GitHub Actions pipeline will run all tests on every pull request to `main`.

---