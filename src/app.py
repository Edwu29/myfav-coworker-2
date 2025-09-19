"""
Main Lambda handler for myfav-coworker API Gateway integration.
"""

import json
import logging
from typing import Dict, Any

# Configure structured logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for API Gateway events.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response format
    """
    try:
        # Extract path and method from event
        path = event.get("path", "")
        method = event.get("httpMethod", "")

        logger.info(f"Processing {method} request to {path}")

        # Route to appropriate handler
        if path == "/health" and method == "GET":
            return handle_health_check()

        # Default 404 response
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {"error": "Not Found", "message": f"Path {path} not found"}
            ),
        }

    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred",
                }
            ),
        }


def handle_health_check() -> Dict[str, Any]:
    """
    Handle health check endpoint.

    Returns:
        200 OK response with JSON health status
    """
    logger.info("Health check requested")

    response_body = {
        "status": "healthy",
        "service": "myfav-coworker",
        "version": "1.0.0",
    }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(response_body),
    }
