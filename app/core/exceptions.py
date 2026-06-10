"""Custom exceptions for the application."""


class AppException(Exception):
    """Base exception for application errors."""
    pass


class DataLoadError(AppException):
    """Raised when data loading fails."""
    pass


class LLMError(AppException):
    """Raised when LLM service encounters an error."""
    pass


class QueryExecutionError(AppException):
    """Raised when query execution fails."""
    pass


class InvalidQueryIntentError(AppException):
    """Raised when LLM returns invalid query intent."""
    pass
