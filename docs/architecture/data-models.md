# Data Models

## SimulationJob
* **Purpose**: To track the state, progress, and results of a single PR simulation request from start to finish.
* **Key Attributes**: `job_id`, `user_id`, `pr_url`, `status`, `report`, `created_at`, `completed_at`.
* **Relationships**: Belongs to a User.

## User
* **Purpose**: To store essential information about an authenticated user, including their GitHub identity and the encrypted access token required for API calls.
* **Key Attributes**: `user_id`, `github_id`, `github_username`, `encrypted_github_token`, `created_at`, `last_login_at`.
* **Relationships**: Has many `SimulationJob`s.

---