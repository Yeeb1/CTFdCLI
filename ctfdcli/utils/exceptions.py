"""Custom exceptions for CTFd CLI."""


class CTFdCLIError(Exception):
    """Base exception for CTFd CLI errors."""
    pass


class ProfileNotFoundError(CTFdCLIError):
    """Raised when a profile is not found."""
    pass


class ConnectionError(CTFdCLIError):
    """Raised when connection to CTFd fails."""
    pass


class APIError(CTFdCLIError):
    """Raised when CTFd API returns an error."""
    pass


class ConfigurationError(CTFdCLIError):
    """Raised when there's a configuration issue."""
    pass


class ValidationError(CTFdCLIError):
    """Raised when input validation fails."""
    pass