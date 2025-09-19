# Core Workflows

## Workflow 1: User Authentication (One-Time Setup)
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

## Workflow 2: Simulation Request (Authenticated)
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