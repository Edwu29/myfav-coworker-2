"""
Unit tests for health endpoint functionality.
"""
import json
from unittest.mock import patch, MagicMock

from src.app import lambda_handler, handle_health_check


class TestHealthEndpoint:
    """Test cases for health check endpoint."""

    def test_health_check_success(self):
        """Test successful health check response."""
        # Arrange
        event = {"path": "/health", "httpMethod": "GET"}
        context = MagicMock()

        # Act
        response = lambda_handler(event, context)

        # Assert
        assert response["statusCode"] == 200
        assert response["headers"]["Content-Type"] == "application/json"

        body = json.loads(response["body"])
        assert body["status"] == "healthy"
        assert body["service"] == "myfav-coworker"
        assert body["version"] == "1.0.0"

    def test_health_check_direct_handler(self):
        """Test direct health check handler function."""
        # Act
        response = handle_health_check()

        # Assert
        assert response["statusCode"] == 200
        assert response["headers"]["Content-Type"] == "application/json"

        body = json.loads(response["body"])
        assert body["status"] == "healthy"
        assert body["service"] == "myfav-coworker"
        assert body["version"] == "1.0.0"

    def test_not_found_path(self):
        """Test 404 response for unknown paths."""
        # Arrange
        event = {"path": "/unknown", "httpMethod": "GET"}
        context = MagicMock()

        # Act
        response = lambda_handler(event, context)

        # Assert
        assert response["statusCode"] == 404
        assert response["headers"]["Content-Type"] == "application/json"

        body = json.loads(response["body"])
        assert body["error"] == "Not Found"
        assert "/unknown" in body["message"]

    def test_wrong_method(self):
        """Test 404 response for wrong HTTP method."""
        # Arrange
        event = {"path": "/health", "httpMethod": "POST"}
        context = MagicMock()

        # Act
        response = lambda_handler(event, context)

        # Assert
        assert response["statusCode"] == 404
        assert response["headers"]["Content-Type"] == "application/json"

    @patch("src.app.handle_health_check")
    def test_exception_handling(self, mock_health_check):
        """Test exception handling in lambda handler."""
        # Arrange
        mock_health_check.side_effect = Exception("Test error")
        event = {"path": "/health", "httpMethod": "GET"}
        context = MagicMock()

        # Act
        response = lambda_handler(event, context)

        # Assert
        assert response["statusCode"] == 500
        assert response["headers"]["Content-Type"] == "application/json"

        body = json.loads(response["body"])
        assert body["error"] == "Internal Server Error"

    def test_missing_path_in_event(self):
        """Test handling of malformed event without path."""
        # Arrange
        event = {"httpMethod": "GET"}
        context = MagicMock()

        # Act
        response = lambda_handler(event, context)

        # Assert
        assert response["statusCode"] == 404

    def test_missing_method_in_event(self):
        """Test handling of malformed event without httpMethod."""
        # Arrange
        event = {"path": "/health"}
        context = MagicMock()

        # Act
        response = lambda_handler(event, context)

        # Assert
        assert response["statusCode"] == 404
