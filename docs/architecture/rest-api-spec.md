# REST API Spec
```
openapi: 3.0.1
info:
  title: "myfav-coworker API"
  description: "API for submitting and tracking PR simulation jobs."
  version: "1.0.0"
servers:
  - url: "https://api.myfav-coworker.com/v1"
    description: "Production Server"

components:
  schemas:
    SimulationJob:
      type: object
      properties:
        job_id:
          type: string
          description: "Unique identifier for the job."
        status:
          type: string
          enum: [pending, running, completed, failed]
        report:
          type: object
          properties:
            result:
              type: string
              enum: [pass, fail]
            summary:
              type: string
            
  securitySchemes:
    SessionAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

security:
  - SessionAuth: []

paths:
  /auth/github:
    get:
      summary: "Initiate GitHub Login"
      description: "Redirects the user to GitHub to start the OAuth2 flow."
      responses:
        '302':
          description: "Redirect to GitHub for authorization."

  /auth/github/callback:
    get:
      summary: "GitHub OAuth Callback"
      description: "The callback URL for GitHub to redirect to after authorization. The service exchanges the code for a token and returns a session JWT."
      responses:
        '200':
          description: "Authentication successful, returns a session JWT."
        '400':
          description: "Error during authentication."
          
  /simulations:
    post:
      summary: "Submit a new simulation job"
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                pr_url:
                  type: string
                  example: "https://github.com/owner/repo/pull/123"
      responses:
        '202':
          description: "Job accepted for processing."
          content:
            application/json:
              schema:
                type: object
                properties:
                  job_id:
                    type: string
                    
  /simulations/{jobId}:
    get:
      summary: "Get simulation job status and result"
      parameters:
        - in: path
          name: jobId
          required: true
          schema:
            type: string
      responses:
        '200':
          description: "Job status and report."
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SimulationJob'
        '404':
          description: "Job not found."
```

---