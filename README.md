# myfav-coworker

A FastMCP-based service for automated PR simulation and testing to assist code reviewers.

## Overview

myfav-coworker helps code reviewers by automatically running AI-driven simulations on pull requests, providing detailed reports on code changes and their potential impact.

## Architecture

- **Language**: Python 3.11
- **Framework**: FastMCP
- **Infrastructure**: AWS (Lambda, API Gateway, SQS, DynamoDB)
- **Testing**: pytest with 80% coverage target

## Project Structure

```
myfav-coworker/
├── README.md                  # Project overview and setup instructions
├── template.yaml              # AWS SAM template defining all cloud resources (IaC)
├── src/                       # Main application source code
│   ├── app.py                 # API Gateway -> Lambda handler
│   ├── worker.py              # SQS -> Lambda handler
│   ├── api/
│   ├── services/
│   ├── models/
│   └── utils/
├── tests/
│   ├── unit/
│   └── integration/
└── requirements.txt           # Python package dependencies
```

## Development Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run tests:
   ```bash
   pytest tests/ --cov=src --cov-report=html
   ```

3. Format code:
   ```bash
   black src/ tests/
   flake8 src/ tests/
   ```

4. Local development:
   ```bash
   sam local start-api
   ```

## API Endpoints

- `GET /health` - Health check endpoint

## Deployment

This project uses AWS SAM for infrastructure as code. Deploy with:

```bash
sam build
sam deploy --guided
```

## Contributing

- Follow PEP 8 naming conventions
- Use structured logging (no print statements)
- Maintain 80% test coverage
- Format with Black and lint with Flake8
