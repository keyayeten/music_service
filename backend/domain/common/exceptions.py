class DomainError(Exception):
    """Base exception for domain-layer errors."""


class ValidationError(DomainError):
    """Input data does not satisfy business validation rules."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AuthenticationError(DomainError):
    """Authentication failed due to invalid credentials or token."""

    def __init__(self, message: str = "Authentication failed.") -> None:
        super().__init__(message)
        self.message = message


class ConflictError(DomainError):
    """Entity conflict, for example duplicate username or email."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AuthorizationError(DomainError):
    """Action is forbidden for current authenticated user."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
