"""Tansive SDK Exception Types

Defines the exception hierarchy for the SDK, providing detailed error information
for proper error handling in client applications.
"""


class TansiveError(Exception):
    """Base exception class for all Tansive SDK errors.

    All SDK exceptions inherit from this class to enable catching all SDK-related
    errors with a single except clause.
    """

    pass


class TansiveConnectionError(TansiveError):
    """Exception raised for network connectivity issues.

    Covers socket connection failures, DNS resolution errors, and other
    network-related problems.
    """

    pass


class TansiveTimeoutError(TansiveError):
    """Exception raised when a request times out.

    Can occur during initial connection establishment or while waiting
    for a service response.
    """

    pass


class TansiveAPIError(TansiveError):
    """Exception raised when the API returns an error response.

    Attributes:
        status_code (Optional[int]): HTTP status code from the response.
        response_body (Optional[str]): Raw response body from the server.
    """

    def __init__(
        self, message: str, status_code: int = None, response_body: str = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class TansiveRetryError(TansiveError):
    """Exception raised when all retry attempts are exhausted.

    Attributes:
        last_error (Optional[Exception]): The exception from the final retry attempt.
    """

    def __init__(self, message: str, last_error: Exception = None):
        super().__init__(message)
        self.last_error = last_error


class TansiveValidationError(TansiveError):
    """Exception raised for input validation failures.

    Covers missing required parameters, invalid parameter types, and values
    that don't meet validation requirements.
    """

    pass
